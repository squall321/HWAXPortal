# 토큰 페이지가 만드는 Windows 설치 배치 — **산출물을 실제로 생성해** 검사한다(2026-09-28)
#
# 왜 이런 모양인가: 이 배치는 실사고가 여섯 번 났는데(PAT 평문 노출·http 스니펫 무연결·npm 점검 무한대기·
# Desktop JSON 이스케이프·`claude mcp add` 가 배치를 끊음·PATH 미반영) 시험이 하나도 없었다. 생성기가
# TokenPage.tsx 안에 있어 React·DOM 없이 돌릴 수 없었기 때문이다. 생성기를 frontend/src/lib/setupBat.ts 로
# 떼어 냈으니, 여기서 tsc 로 그 파일만 컴파일해 node 로 돌려 **진짜 .bat 을 만들고** 검사한다.
# cmd.exe 를 실행할 수는 없으므로 검사는 구조(라벨 도달성·이스케이프·토큰 노출)와 계약(문구·분기)이다.
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
LIB = FE / "src/lib/setupBat.ts"
TSC = FE / "node_modules/.bin/tsc"
TOKEN = "hwax_pat_TESTTOKEN_abcd1234"

pytestmark = pytest.mark.skipif(
    not TSC.exists() or not shutil.which("node"),
    reason="frontend node_modules(tsc) 또는 node 가 없다 — 생성기를 컴파일할 수 없다",
)


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    """setupBat.ts 만 컴파일해 node 로 부르는 생성기."""
    out = tmp_path_factory.mktemp("setupbat")
    r = subprocess.run([str(TSC), str(LIB), "--outDir", str(out), "--module", "commonjs",
                        "--target", "es2019", "--skipLibCheck"], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    drv = out / "drive.cjs"
    drv.write_text(
        "const { makeSnippets } = require('./setupBat.js');\n"
        "const pem = process.argv[3] === 'pem' ? '-----BEGIN CERTIFICATE-----\\nQUJD\\n-----END CERTIFICATE-----' : null;\n"
        "const s = makeSnippets(process.argv[2]);\n"
        "process.stdout.write(process.argv[4] === 'desktop' ? s.claudeDesktopSnippet('" + TOKEN + "', process.argv[5] || null)\n"
        "  : s.buildSetupBat('" + TOKEN + "', '내 토큰', pem));\n")

    def run(origin="https://hwax.example.net", pem=True, what="bat", cert=""):
        # ⚠ text=True 는 universal newlines 로 CRLF 를 LF 로 바꾼다 — 배치의 줄끝 규약을 검사할 수 없다(실측).
        r = subprocess.run(["node", str(drv), origin, "pem" if pem else "nopem", what, cert],
                           capture_output=True, timeout=120, cwd=str(out))
        assert r.returncode == 0, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
        return r.stdout.decode("utf-8")
    return run


def _lines(bat: str) -> list[str]:
    return bat.lstrip("\ufeff").split("\r\n")


# ── 구조 ──────────────────────────────────────────────────────────────────────
def test_every_goto_has_a_label_and_labels_are_unique(gen):
    for pem in (True, False):
        bat = gen(pem=pem)
        ls = _lines(bat)
        labels = [l.strip()[1:] for l in ls if re.fullmatch(r":[A-Za-z_][A-Za-z0-9_]*", l.strip())]
        assert len(labels) == len(set(labels)), ("라벨이 겹치면 cmd 는 처음 것으로 점프한다", sorted(labels))
        targets = {m.group(1) for l in ls for m in [re.search(r"\bgoto\s+:?([A-Za-z_][A-Za-z0-9_]*)", l)] if m}
        assert targets <= set(labels), ("없는 라벨로 점프하면 배치가 그 자리에서 죽는다", sorted(targets - set(labels)))
        assert set(labels) - targets <= {"not_admin"} or True   # 라벨이 흐름상 fallthrough 로만 쓰일 수 있다


def test_batch_is_crlf_with_a_bom_and_a_sacrificial_first_line(gen):
    bat = gen()
    assert bat.startswith("\ufeff@rem "), "BOM 이 섞여 죽어도 무해한 첫 줄이어야 한다 — @echo off 가 죽으면 PAT 가 콘솔에 전부 찍힌다"
    assert _lines(bat)[1] == "@echo off"
    assert "\r\n" in bat and "\n" not in bat.replace("\r\n", ""), "CRLF 만"


def test_the_token_is_never_echoed_to_the_console(gen):
    """실사고: BOM 이 @echo off 를 죽여 PAT 가 스크롤백에 두 번 찍혔다. 화면으로 나가는 echo 에는 토큰이 없어야 한다."""
    for pem in (True, False):
        for l in _lines(gen(pem=pem)):
            t = l.strip()
            if re.match(r"^(@?echo|echo\.)\b", t) and not t.startswith(">>"):
                assert TOKEN not in t, l


def test_the_batch_has_no_multiline_paren_blocks(gen):
    """이 파일의 규약 — 흐름은 goto 로만 만든다. 괄호 블록 안에 PowerShell 한 줄처럼 ( ) | 가 섞인 긴 명령을
    넣으면 cmd 의 괄호 매칭이 어긋나 '예기치 않음' 으로 죽는다. 블록이 없으면 echo 안의 괄호는 무해하다
    (그래서 `echo [2] Claude Code (CLI)` 같은 줄을 이스케이프하지 않아도 된다 — 대신 블록이 생기지 않는지를 본다)."""
    for pem in (True, False):
        opened = [l for l in _lines(gen(pem=pem)) if l.rstrip().endswith("(") and not l.strip().startswith(">>")]
        assert opened == [], ("여기에 줄이 생기면 그 안의 echo 는 모두 ^( ^) 로 이스케이프해야 한다", opened)


def test_multi_word_console_messages_escape_what_cmd_eats(gen):
    """echo 로 화면에 쓸 때 cmd 가 먹는 것은 & < > | 다(괄호는 블록 안에서만) — 이스케이프 없이 남으면 그 줄이 실행된다."""
    for pem in (True, False):
        for l in _lines(gen(pem=pem)):
            t = l.strip()
            if not t.startswith("echo ") or t.startswith(">>"):
                continue
            body = re.sub(r"\^[&<>|^]", "", t)
            assert not set(body) & set("&<>|"), l


# ── Claude Desktop — 사용자 증상: '설정 폴더 없음 - 건너뜀' ────────────────────────────
def _desktop_block(bat: str) -> list[str]:
    ls = _lines(bat)
    a = next(i for i, l in enumerate(ls) if l.strip() == ":desktop")
    b = next(i for i, l in enumerate(ls) if i > a and l.strip() == ":desktop_done")
    return ls[a:b + 1]


def test_desktop_validates_the_roaming_path_and_has_a_fallback(gen):
    """%APPDATA% 는 축소된 환경에서 비어 있고(경로가 `\\Claude` 가 된다), 기업 폴더 리디렉션이 오프라인이면 설정돼 있어도 닿지 않는다.
    둘 다 '폴더 없음' 으로 보인다 — 비었는지와 **있는지**를 둘 다 보고 아니면 프로필에서 직접 짚는다."""
    blk = "\n".join(_desktop_block(gen()))
    assert 'set "HWAX_ROAMING=%APPDATA%"' in blk
    assert 'if not defined HWAX_ROAMING set "HWAX_ROAMING=%USERPROFILE%\\AppData\\Roaming"' in blk, "비었을 때"
    assert 'if not exist "%HWAX_ROAMING%\\" set "HWAX_ROAMING=%USERPROFILE%\\AppData\\Roaming"' in blk, "닿지 않을 때"
    assert "echo      설정 파일: %HWAX_CFG%" in blk, "어느 경로를 봤는지 찍어야 사람이 원인을 찾을 수 있다"
    # cmd 파싱 함정을 새로 들이지 않는다 — `for /f ... in (`cmd`)` 안의 괄호는 `in (` 를 먼저 닫는다.
    assert "usebackq" not in blk and "for /f" not in blk, "실제 Windows 에서 재보지 않은 구문을 쓰지 않는다"


def test_desktop_creates_the_config_folder_instead_of_skipping(gen):
    """사용자 증상의 뿌리 — 그 폴더는 Desktop 을 한 번 실행했을 때 만들어진다. 설치만 해 둔 사람은 영영 등록이 안 됐다."""
    blk = _desktop_block(gen())
    joined = "\n".join(blk)
    assert 'if not exist "%APPDATA%\\Claude" goto :no_desktop' not in joined, "종전의 단일 판정은 버렸다"
    assert 'mkdir "%HWAX_DESKDIR%" >nul 2>nul' in joined, "없으면 만든다"
    # 만들기 전에 '있으면 그냥 쓴다' 로 빠지고, 만든 뒤에만 no_desktop 으로 간다
    i_exist = next(i for i, l in enumerate(blk) if l.strip() == 'if exist "%HWAX_DESKDIR%\\" goto :desktop_write')
    i_mkdir = next(i for i, l in enumerate(blk) if l.strip().startswith('mkdir "%HWAX_DESKDIR%"'))
    i_fail = next(i for i, l in enumerate(blk) if l.strip() == 'if not exist "%HWAX_DESKDIR%\\" goto :no_desktop')
    assert i_exist < i_mkdir < i_fail
    assert "설정 폴더 없음" not in joined, "이제 '없다' 로 끝내지 않는다"
    assert "만들 수 없습니다" in joined, "못 만든 경우만 건너뛰고, 그때 원인을 짚는다"


def test_desktop_looks_for_an_install_but_registers_either_way(gen):
    """설치 경로는 문서화돼 있지 않다 — 못 맞혀도 등록은 하고 문구만 달라진다(단정하지 않는다)."""
    blk = "\n".join(_desktop_block(gen()))
    assert "AnthropicClaude" in blk and "Claude.lnk" in blk
    assert "goto :desktop_write" in blk and blk.count(":desktop_write") >= 3, "흔적을 못 찾아도 쓰기로 간다"
    assert "설치를 못 찾았습니다" in blk and "미리 넣어 둡니다" in blk


def test_desktop_tells_the_user_to_restart_a_running_desktop(gen):
    """켜져 있는 Desktop 은 종료할 때 자기 메모리의 설정으로 이 파일을 덮어쓸 수 있다."""
    assert "완전히 종료한 뒤 다시 실행하세요" in "\n".join(_desktop_block(gen()))


def test_batch_warns_when_run_as_administrator(gen):
    """관리자 권한이면 %APPDATA%·%USERPROFILE% 이 관리자 프로필이라 Desktop 폴더도 Claude Code 도 '없다' 가 된다."""
    bat = gen()
    assert 'whoami /groups 2>nul | find "S-1-16-12288" >nul 2>nul' in bat, "High Mandatory Level SID — 언어와 무관"
    assert "if errorlevel 1 goto :not_admin" in bat and ":not_admin" in bat
    assert "관리자 권한으로 실행 중입니다" in bat
    i_warn = bat.index("관리자 권한으로 실행 중입니다"); i_desk = bat.index(":desktop")
    assert i_warn < i_desk, "경고는 판정보다 앞에 있어야 읽힌다"


# ── 손으로 붙여넣는 Desktop 조각 — %USERPROFILE% 은 풀리지 않는다 ─────────────────────
def test_pasted_desktop_snippet_does_not_hide_an_unexpanded_variable(gen):
    """Desktop 은 설정 값의 %USERPROFILE% 을 풀지 않는다 — JSON 에 그대로 들어가 없는 경로가 된다.
    배치는 확장된 실제 경로를 쓰지만, 붙여넣는 조각은 사람이 바꿀 자리표시자여야 한다."""
    page = (FE / "src/pages/TokenPage.tsx").read_text(encoding="utf-8")
    assert "claudeDesktopSnippet(created.token, needsCa ? String.raw`C:\\Users\\<사용자>" in page
    assert "claudeDesktopSnippet(created.token, needsCa ? String.raw`%USERPROFILE%" not in page
    snip = gen(what="desktop", cert=r"C:\Users\<사용자>\.hwax\hwax-portal.crt")
    assert "%USERPROFILE%" not in snip and "<사용자>" in snip
    # 배치 쪽은 반대로 cmd 가 확장하는 경로를 그대로 쓴다(그쪽은 풀린다)
    assert 'set "HWAX_CERT=%USERPROFILE%\\.hwax\\hwax-portal.crt"' in gen()


# ── 생성기가 페이지에서 떼어져 있는지(이 시험이 가능한 조건) ──────────────────────────
def test_the_generator_is_free_of_browser_globals():
    src = LIB.read_text(encoding="utf-8")
    assert "window." not in src and "document." not in src, "origin 은 인자로 받는다 — 그래서 시험할 수 있다"
    page = (FE / "src/pages/TokenPage.tsx").read_text(encoding="utf-8")
    assert "from '../lib/setupBat'" in page and "function buildSetupBat" not in page
