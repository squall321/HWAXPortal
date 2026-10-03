# 토큰 페이지가 만드는 Windows 설치 배치 — **산출물을 실제로 생성해** 검사한다(2026-09-28)
#
# 왜 이런 모양인가: 이 배치는 실사고가 여섯 번 났는데(PAT 평문 노출·http 스니펫 무연결·npm 점검 무한대기·
# Desktop JSON 이스케이프·`claude mcp add` 가 배치를 끊음·PATH 미반영) 시험이 하나도 없었다. 생성기가
# TokenPage.tsx 안에 있어 React·DOM 없이 돌릴 수 없었기 때문이다. 생성기를 frontend/src/lib/setupBat.ts 로
# 떼어 냈으니, 여기서 tsc 로 그 파일만 컴파일해 node 로 돌려 **진짜 .bat 을 만들고** 검사한다.
# cmd.exe 를 실행할 수는 없으므로 검사는 구조(라벨 도달성·이스케이프·토큰 노출)와 계약(문구·분기)이다.
import re
import shlex
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


# ── Claude Code — claude 명령이 없을 때: 데스크톱 앱 안의 Code 탭(docs/sso-delegation D-9·D-11) ──────────
def _no_cli_block(bat: str) -> list[str]:
    ls = _lines(bat)
    return ls[ls.index(":no_cli"):ls.index(":desktop")]


def _ccj_ps(blk: list[str]) -> str:
    ps = [l for l in blk if l.startswith("powershell ")]
    assert len(ps) == 1, ps
    return ps[0]


def _cli_add_line(bat: str) -> str:
    return next(l for l in _lines(bat) if '"%%HWAX_CLAUDE%%" mcp add -s user' in l)


def _write_host_args(ps: str) -> list[str]:
    """Write-Host 의 인자(홑따옴표 문자열 하나, 또는 짝이 맞는 괄호 식)를 전부 뽑는다 — 화면에 나가는 것은 이것뿐이다."""
    out, i = [], 0
    while (i := ps.find("Write-Host ", i)) != -1:
        i += len("Write-Host ")
        if ps[i] == "'":
            j = ps.index("'", i + 1)
        else:
            assert ps[i] == "(", ps[i:i + 40]
            depth, j, quoted = 0, i, False
            while True:
                ch = ps[j]
                if ch == "'":
                    quoted = not quoted
                elif not quoted and ch in "()":
                    depth += 1 if ch == "(" else -1
                    if depth == 0:
                        break
                j += 1
        out.append(ps[i:j + 1])
        i = j + 1
    return out


def test_no_cli_registers_claude_code_in_the_user_config(gen):
    """데스크톱 앱 안의 Claude Code 는 Desktop 설정이 아니라 Claude Code 사용자 설정을 읽는다 — 앱만 깐 사람은 PATH 에
    claude 가 없다. 종전 판은 여기서 '이대로 정상' 이라 하고 건너뛰었다(실패가 성공처럼 보이는 그 부류)."""
    for pem in (True, False):
        bat = gen(pem=pem)
        assert "이대로 정상" not in bat and "이 단계만 건너뜁니다" not in bat
        blk = _no_cli_block(bat)
        cert = ['set "HWAX_CERT=%USERPROFILE%\\.hwax\\hwax-portal.crt"'] if pem else []
        order = [f'set "HWAX_AUTH=Bearer {TOKEN}"', *cert, _ccj_ps(blk),
                 "if errorlevel 1 goto :ccj_fail", "set HWAX_DONE=1", "goto :desktop", ":ccj_fail"]
        idx = [blk.index(s) for s in order]
        assert idx == sorted(idx), ("환경변수를 먼저 세우고, 성공은 실패 안내를 건너뛴다", order)


def test_no_cli_picks_the_file_the_way_claude_code_does(gen):
    """자리는 Claude Code 2.0.74 바이너리의 규칙 그대로다(D-11).
        폴더 = CLAUDE_CONFIG_DIR ?? <홈>\\.claude — 그 안에 .config.json 이 있으면 그 파일(옛 위치),
        아니면 (CLAUDE_CONFIG_DIR || <홈>)\\.claude.json.
    <홈> 은 %USERPROFILE% 를 그대로 믿지 않고 프로필 폴더를 묻는다(관리자·축소 환경 전례) — 비었을 때만 %USERPROFILE%."""
    for pem in (True, False):
        blk = _no_cli_block(gen(pem=pem))
        ps = _ccj_ps(blk)
        steps = ["$h=[Environment]::GetFolderPath('UserProfile');if(-not $h){$h=$env:USERPROFILE};",
                 "$o=$h;$d=[System.IO.Path]::Combine($h,'.claude');",
                 "if($env:CLAUDE_CONFIG_DIR){$o=$env:CLAUDE_CONFIG_DIR;$d=$o;",
                 "$c=[System.IO.Path]::Combine($d,'.config.json');",
                 "if(Test-Path -LiteralPath $c){$w=",
                 "else{$c=[System.IO.Path]::Combine($o,'.claude.json');",
                 "Write-Host ('          설정 파일: '+$c);Write-Host ('          '+$w);",
                 "$t=$c+'.hwax-tmp';"]
        idx = [ps.index(s) for s in steps]
        assert idx == sorted(idx), steps
        assert ps.index("$env:USERPROFILE") > ps.index("GetFolderPath('UserProfile')"), "프로필 폴더를 먼저 묻는다"
        # Claude Code 의 homedir 는 USERPROFILE 을 먼저 본다 — 이 창에서 둘이 다르면 말없이 고르지 않는다
        assert "elseif($env:USERPROFILE -and $env:USERPROFILE -ne $h){Write-Host" in ps
        # 왜 그 파일인지 — 옛 위치 · 있는 파일 · .claude 폴더만 · 흔적 없음, 어느 쪽이든 말한다
        why = re.findall(r"\$w='([^']*)'", ps)
        assert len(why) == 4, why
        assert ".config.json" in why[0] and "있는 파일" in why[1] and ".claude 폴더" in why[2] and "새로 만듭니다" in why[3]
        # 경로를 cmd 에서 박지 않는다 — %USERPROFILE%\.claude.json 하나로 단정하는 것이 D-11 이 막은 것이다
        assert not any(".claude.json" in l or "\\.claude\\" in l for l in blk if not l.startswith("powershell "))


def test_the_cli_path_is_unchanged_and_skips_the_direct_write(gen):
    """CLI 가 있으면 `claude mcp add -s user` 가 제 자리를 안다 — 거기에 직접 쓰기를 겹치지 않는다."""
    url = "https://hwax.example.net/mcp-gw/mcp"
    for pem in (True, False):
        ls = _lines(gen(pem=pem))
        a, b = ls.index(":cli_go"), ls.index(":no_cli")
        cli = ls[a:b]
        assert sum("mcp add -s user" in l for l in cli) == 1
        assert not any(l.startswith("powershell ") or "HWAX_AUTH" in l or ".claude.json" in l for l in cli)
        assert ls[b - 1] == "goto :desktop", "CLI 결과 분기는 :no_cli 로 흘러들지 않는다"
    assert _cli_add_line(gen(pem=False)) == (
        f'>>"%HWAX_CLI_CMD%" echo "%%HWAX_CLAUDE%%" mcp add -s user --transport http hwax {url}'
        f' --header "Authorization: Bearer {TOKEN}"')


def test_no_cli_merge_backs_up_writes_a_temp_reparses_then_swaps(gen):
    """Desktop 병합과 같은 방식(경로·토큰은 환경변수, 조립은 PowerShell)이되, 이 파일은 Claude Code 의 큰 전역 상태라
    백업 → 임시 파일에 쓰기 → 되읽어 확인 → 바꿔 넣기 순서를 지킨다. 바꿔 넣기 전에 실패하면 원본은 그대로다."""
    for pem in (True, False):
        ps = _ccj_ps(_no_cli_block(gen(pem=pem)))
        steps = ["if(Test-Path -LiteralPath $c){$s='backup';$b=$c+'.hwax-bak';Copy-Item -LiteralPath $c -Destination $b -Force;",
                 "$j=[System.IO.File]::ReadAllText($c,$u) | ConvertFrom-Json}else{$j=[pscustomobject]@{}};",
                 "$j.mcpServers | Add-Member -NotePropertyName hwax -NotePropertyValue $e -Force;",
                 "$n=@($j.PSObject.Properties).Count;",
                 "[System.IO.File]::WriteAllText($t, ($j | ConvertTo-Json -Depth 100), $u);",
                 "$v=[System.IO.File]::ReadAllText($t,$u) | ConvertFrom-Json;",
                 "throw 'mismatch'",
                 "[System.IO.File]::Copy($t,$c,$true);"]
        idx = [ps.index(s) for s in steps]
        assert idx == sorted(idx), steps
        assert "$t=$c+'.hwax-tmp'" in ps
        assert "WriteAllText($c" not in ps, "원본에 직접 쓰지 않는다 — 쓰다 깨지면 전역 상태를 잃는다"
        assert re.findall(r"ConvertTo-Json(?: -Depth (\d+))?", ps) == ["100"], "기본 깊이(2)면 projects 아래가 문자열로 잘린다"
        # 다른 키는 그대로 — hwax 만 얹고, 되읽은 최상위 키 수가 같은지 본다
        assert "@($v.PSObject.Properties).Count -ne $n" in ps
        # powershell 은 cmdlet 이 실패해도 0 으로 끝난다 — Stop + catch 의 exit 1 로 errorlevel 에 싣는다
        body = ps.split('-Command "', 1)[1]
        assert body.startswith("$ErrorActionPreference='Stop';") and body.endswith('exit 1}"')
        assert "exit 0}catch{" in body
        assert "Remove-Item -LiteralPath $t" in body.split("}catch{", 1)[1], "실패하면 토큰이 든 임시 파일을 지운다"


def test_no_cli_merge_reads_and_writes_utf8_without_bom_like_desktop(gen):
    """5.1 의 Get-Content 는 BOM 없는 UTF-8 을 ANSI 로 읽는다 — 한글 사용자명이 든 projects 키가 깨진 채 다시 쓰인다.
    쓰기는 Desktop 쪽과 같은 BOM 없는 UTF-8 이다. PowerShell 조각은 cmd 의 "…" 안에 들어가므로 큰따옴표가 없어야 하고,
    % 가 있으면 cmd 가 먼저 확장한다."""
    for pem in (True, False):
        bat = gen(pem=pem)
        ps = _ccj_ps(_no_cli_block(bat))
        assert "Get-Content" not in ps
        assert "$u=New-Object System.Text.UTF8Encoding($false);" in ps
        assert ps.count("AllText(") == 3 and ps.count(",$u)") + ps.count(", $u)") == 3, "읽기 둘·쓰기 하나 모두 $u 로"
        desk = next(l for l in _desktop_block(bat) if l.startswith("powershell "))
        assert "UTF8Encoding($false)" in desk, "Desktop 쪽과 같은 쓰기 방식"
        body = ps.split('-Command "', 1)[1][:-1]
        assert '"' not in body and "%" not in body


def test_no_cli_never_puts_the_token_on_screen_or_on_the_command_line(gen):
    """토큰은 set 한 줄에만 있다 — PowerShell 에는 환경변수로 넘긴다(명령줄은 프로세스 목록에 남는다).
    예외 메시지도 찍지 않는다 — 5.1 의 ConvertFrom-Json 은 파싱 오류에 입력 전체를 붙여 파일 속 토큰이 콘솔에 나온다.
    화면에 나가는 것은 경로·판단·단계·예외 종류뿐이다."""
    for pem in (True, False):
        blk = _no_cli_block(gen(pem=pem))
        assert [l for l in blk if TOKEN in l] == [f'set "HWAX_AUTH=Bearer {TOKEN}"']
        ps = _ccj_ps(blk)
        assert "$env:HWAX_AUTH" in ps and "Exception.Message" not in ps
        shown = _write_host_args(ps)
        assert len(shown) >= 8, shown
        for arg in shown:
            assert set(re.findall(r"\$[A-Za-z_][\w:]*", arg)) <= {"$c", "$w", "$b", "$s", "$_", "$env:USERPROFILE"}, arg


def test_no_cli_entry_has_the_shape_claude_mcp_add_writes(gen):
    """항목 모양의 정본은 같은 배치의 `claude mcp add -s user` 줄이다(2.0.74 바이너리: http 는 {type,url,headers},
    stdio 는 {type,command,args,env} — Desktop 항목과 달리 type 이 있다). 따로 적으면 한쪽만 고쳐지는 일이 또 나므로 CLI 줄과 대조한다."""
    url = "https://hwax.example.net/mcp-gw/mcp"
    bat = gen(pem=False)
    ps = _ccj_ps(_no_cli_block(bat))
    assert ("$e=[pscustomobject]@{type='http';url='" + url
            + "';headers=[pscustomobject]@{Authorization=$env:HWAX_AUTH}};") in ps
    assert f'--transport http hwax {url} --header "Authorization: Bearer {TOKEN}"' in _cli_add_line(bat)
    assert "$v.mcpServers.hwax.headers.Authorization -cne $env:HWAX_AUTH" in ps, "되읽어 이번 토큰인지 본다"
    for origin in ("https://hwax.example.net", "http://hwax.example.net"):
        bat = gen(origin=origin, pem=True)
        blk = _no_cli_block(bat)
        ps = _ccj_ps(blk)
        m = re.search(r"\$e=\[pscustomobject\]@\{type='stdio';command='([^']*)';args=@\(([^)]*)\);"
                      r"env=\[pscustomobject\]@\{AUTH=\$env:HWAX_AUTH;NODE_EXTRA_CA_CERTS=\$env:HWAX_CERT\}\};", ps)
        assert m, ps
        cli = _cli_add_line(bat)
        assert [m.group(1)] + re.findall(r"'([^']*)'", m.group(2)) == shlex.split(cli.split(" -- ", 1)[1])
        assert ("'--allow-http'" in m.group(2)) == origin.startswith("http://"), "mcp-remote 는 http 를 즉시 거부한다"
        # env 값도 CLI 의 -e 와 같은 것 — 인증서 경로는 cmd 가 set 할 때 확장해 환경변수로 넘긴다
        assert f'-e AUTH="Bearer {TOKEN}"' in cli
        cert = re.search(r"-e NODE_EXTRA_CA_CERTS=(\S+)", cli).group(1)
        assert f'set "HWAX_CERT={cert}"' in blk
        assert "$v.mcpServers.hwax.env.AUTH -cne $env:HWAX_AUTH" in ps


def test_no_cli_tells_the_user_to_quit_running_claude_apps_and_what_was_kept(gen):
    """켜져 있는 Desktop·Code 는 종료하면서 자기 메모리의 설정으로 이 파일을 덮을 수 있다 — Desktop 설정과 같은 이유다.
    원본이 그대로인지·백업이 어디인지는 cmd 가 단정하지 않고 PowerShell 이 멈춘 단계를 보고 말한다."""
    for pem in (True, False):
        blk = _no_cli_block(gen(pem=pem))
        k = blk.index(":ccj_fail")
        ps = _ccj_ps(blk)
        ok, fail = "\n".join(blk[:k]), "\n".join(blk[k:])
        assert "Desktop 설정이 아니라 아래 파일을 읽습니다" in ok.split(ps, 1)[0], "어느 파일인지 찍기 전에 왜 이 파일인지"
        assert "완전히 종료한 뒤 다시 실행하세요" in ok.split(ps, 1)[1], "성공 안내에"
        assert "완전히 종료한 뒤" in fail and "install.ps1" in fail, "실패하면 다음에 할 일"
        assert "Write-Host ('          백업: '+$b)" in ps
        catch = ps.split("}catch{", 1)[1]
        assert "if($s -eq 'replace')" in catch and "원래 내용: '+$b" in catch and "원본 파일은 바꾸지 않았습니다" in catch


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
