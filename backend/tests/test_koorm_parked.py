# 멈춰 둔 KooRemapper 되돌림 사본(포털 infra/.env 의 KOORM_LOCAL_PARKED) — 배치들이 한 규칙으로 읽고 그 스택을 띄우지 · 재지 · 덤프하지 않는지(cae00 11-23 HP-66 · HP-67)
"""왜 — cae00 은 11-12 에 DynaForge 를 운영 노드로 옮겼고 이 박스의 KooRemapper 스택은 일부러 멈춰 둔 되돌림 사본이다. 11-23 라운드에 deploy-all 의
기본 목록이 그 스택을 21:31 에 다시 띄우고 이관 · 감시 · 백업 크론을 걸었다(박스 뒤처리가 22:04 에 내렸다). §1b 사전 백업은 내려간 DB 를 ✗ 로 셌다.

배치(deploy-all)는 dev 에서 돌리면 리포를 리셋하므로(docs/gotchas) 구역을 떼어 가짜 리포 · 가짜 스크립트로 돌린다. 사전 백업은 스크립트를 임시
포털로 옮겨 가짜 KooRemapper · 가짜 apptainer 로 돌린다 — 실 인스턴스 · 실 크론 · 실 :8700 에 닿지 않는다.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from tests.test_update_all_delib_restart_gate import DEAD, _deploy_common

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib"
DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
KEY = "KOORM_LOCAL_PARKED"
NAME = "DynaForge(KooRemapper) 로컬 스택 — 멈춰 둠"
WHY = "포털 infra/.env 의 KOORM_LOCAL_PARKED 가 이 박스의 스택을 멈춰 둔 되돌림 사본으로 표시했다"


def _plain(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _bash(script: str, *, cwd: Path | None = None, **env) -> subprocess.CompletedProcess:
    base = {"PATH": os.environ["PATH"], "HOME": str(cwd or "/nonexistent")}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=90, cwd=cwd, env={**base, **env})


def _func(text: str, head: str) -> str:
    i = text.index(head)
    return text[i:text.index("\n}\n", i) + 3]


# ── 한 규칙 — 값 읽기 · 차례 ──────────────────────────────────────────────────────────────────────────────────
TEXTS = [
    ("KOORM_LOCAL_PARKED=1\n", "1"),
    ("export KOORM_LOCAL_PARKED=1\n", "1"),
    ("  KOORM_LOCAL_PARKED=1   # 운영 노드로 옮긴 되돌림 사본\n", "1"),
    ('KOORM_LOCAL_PARKED="yes"\n', "yes"),
    ("KOORM_LOCAL_PARKED='0'\r\n", "0"),
    ("KOORM_LOCAL_PARKED=   # 설명만\n", ""),
    ("KOORM_LOCAL_PARKED=1\nKOORM_LOCAL_PARKED=\n", ""),                               # 마지막 줄이 이긴다
    ("# KOORM_LOCAL_PARKED=1   # 선택 — 필요하면 주석을 풀고 값을 정한다\n", ""),          # env-sync 가 넣는 주석 줄
    ("KOORM_LOCAL_PARKED_X=1\nXKOORM_LOCAL_PARKED=1\n", ""),
    ("", ""),
]


def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services_parked", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


def test_값_읽기는_lib_와_update_all_deploy_all_services_py_가_글자_단위로_같다(tmp_path, monkeypatch):
    """한 키를 네 독자가 읽는다 — 하나라도 다르게 읽으면 services.sh up 은 '대상 아님' 인데 deploy-all 은 띄우는 박스가 생긴다."""
    svc = _services_mod()
    portal = tmp_path / "portal"
    (portal / "infra").mkdir(parents=True)
    monkeypatch.setattr(svc, "PORTAL_ROOT", portal)
    monkeypatch.delenv(KEY, raising=False)
    readers = (_func(UA, "_envfile_value() {") + _func(DEPLOY, "_envv() {")
               + f'. "{LIB}/koorm-parked.sh"\n')
    for text, want in TEXTS:
        (portal / "infra/.env").write_text(text, encoding="utf-8")
        f = portal / "infra/.env"
        r = _bash(f'set -euo pipefail\n{readers}'
                  f'printf "%s|%s|%s" "$(_hwax_koorm_parked_value "{f}")" "$(_envfile_value "{f}" {KEY})" "$(_envv "{f}" {KEY})"')
        assert r.returncode == 0, r.stderr
        assert r.stdout == f"{want}|{want}|{want}", (text, r.stdout)
        assert (svc._infra_value(KEY) or "") == want, (text, svc._infra_value(KEY))


@pytest.mark.parametrize("file_text,env_val,parked", [
    (None, None, False),                     # 파일이 없다 — set -e · pipefail 에서도 죽지 않고 '아니다'
    ("HTTP_PORT=8088\n", None, False),       # 키가 없다 — 종전 동작
    ("KOORM_LOCAL_PARKED=1\n", None, True),
    ("KOORM_LOCAL_PARKED=0\n", None, True),  # unless_env 와 같은 뜻 — 값이 있으면(0 도) 멈춤
    ("", "1", True),                         # 환경이 이긴다
    ("KOORM_LOCAL_PARKED=1\n", "  ", True),  # 빈칸뿐인 환경은 없는 것 — 파일을 본다(services.py 와 같은 차례)
    (None, "  ", False),
])
def test_멈춤_판정은_services_py_의_unless_env_와_같다(tmp_path, monkeypatch, file_text, env_val, parked):
    portal = tmp_path / "portal"
    (portal / "infra").mkdir(parents=True)
    if file_text is not None:
        (portal / "infra/.env").write_text(file_text)
    env = {} if env_val is None else {KEY: env_val}
    r = _bash(f'set -euo pipefail\n. "{LIB}/koorm-parked.sh"\nif hwax_koorm_parked "{portal}"; then echo PARKED; else echo NO; fi\necho END', **env)
    assert r.returncode == 0 and r.stdout == ("PARKED" if parked else "NO") + "\nEND\n", r.stdout + r.stderr
    svc = _services_mod()
    monkeypatch.setattr(svc, "PORTAL_ROOT", portal)
    monkeypatch.delenv(KEY, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    koorm = next(s for s in svc.load() if s["name"] == "kooremapper")
    assert svc.enabled_here(koorm) is (not parked), "services.sh up · update · 상태판이 같은 판정을 쓴다(services.yaml unless_env)"
    if parked:
        assert f"unless_env={KEY}" in svc.skip_reason(koorm)


# ── deploy-all KooRemapper 구역 ───────────────────────────────────────────────────────────────────────────────
def _koorm_block() -> str:
    i = DEPLOY.index("if want kooremapper; then\n")
    return DEPLOY[i:DEPLOY.index("# ── Always refresh the portal routing", i)]


def _deploy_koorm(tmp_path: Path, env_text: str | None, **env):
    """deploy-all 의 KooRemapper 구역을 가짜 리포에서 돌린다 → (화면, 대역이 받은 호출, 남은 기준 지문, 장부, skip 으로 센 줄)."""
    portal = tmp_path / "portal"
    (portal / "infra").mkdir(parents=True)
    if env_text is not None:
        (portal / "infra/.env").write_text(env_text)
    repo = tmp_path / "KooRemapper"
    sc = repo / "platform/infra/scripts"
    sc.mkdir(parents=True)
    log = tmp_path / "calls.log"; log.write_text("")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    failed = tmp_path / "failed"; failed.write_text("")
    st = tmp_path / "state"; st.mkdir()
    for name in ("dist-from-drive.sh", "stop.sh", "start.sh", "install-autostart.sh"):
        (sc / name).write_text(f'#!/usr/bin/env bash\necho "{name}" >> "{log}"\nexit 0\n')
    stubbin = tmp_path / "bin"; stubbin.mkdir()
    (stubbin / "apptainer").write_text(f'#!/usr/bin/env bash\necho "apptainer $*" >> "{log}"\nexit 1\n'); (stubbin / "apptainer").chmod(0o755)
    block = _koorm_block()
    for real in ("http://127.0.0.1:8700/api/health", "http://127.0.0.1:8701/mcp", 'http://127.0.0.1:$_p/'):
        assert real in block, "업스트림 주소가 바뀌었다 — 하네스가 바꿔 끼울 자리를 다시 찾는다"
    block = (block.replace("http://127.0.0.1:8700/api/health", DEAD).replace("http://127.0.0.1:8701/mcp", DEAD)
             .replace('http://127.0.0.1:$_p/', "http://127.0.0.1:9/"))
    body = (_deploy_common() + 'RESTART="${NO_RESTART:-0}"\n' + block).replace("http://127.0.0.1:9009/health", DEAD)
    assert "127.0.0.1:870" not in body and "127.0.0.1:9009" not in body, "실물 주소가 남았다"
    script = (f'set -euo pipefail\ncd "{tmp_path}"\n'
              f'PORTAL_DIR="{portal}"; KOOR_DIR="{repo}"; PARENT="{tmp_path}"; DEPLOY_FAILED_FILE="{failed}"\n'
              'want() { true; }; hr() { echo "── $*"; }; ok() { echo "OK:$*"; }\n'
              'skip() { echo "SKIP:$*"; printf "%s\\n" "$*" >> "$DEPLOY_FAILED_FILE"; }\n'
              'git_update() { echo "  · git: aaa → bbb (reset to origin/main)"; }; set_remote() { :; }\n'
              + "".join(f'. "{LIB}/{n}"\n' for n in ("change-detect.sh", "skip-ledger.sh", "delib-busy.sh", "koorm-busy.sh", "koorm-parked.sh"))
              + f'export HWAX_RESTART_STATE_DIR="{st}" HWAX_SKIP_LEDGER="{ledger}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1\n'
              f'{body}\necho "END"\n')
    r = _bash(script, cwd=tmp_path, PATH=f'{stubbin}:{os.environ["PATH"]}', **env)
    assert "END" in r.stdout, r.stdout + r.stderr
    return r.stdout + r.stderr, log.read_text().splitlines(), sorted(p.name for p in st.iterdir()), ledger.read_text(), failed.read_text()


@pytest.mark.parametrize("where", ["infra/.env", "환경"])
def test_멈춰_둔_사본은_코드와_배포물만_받고_띄우지_않는다(tmp_path, where):
    """**이 시험이 HP-66 · HP-67 의 이유다** — start.sh(이관 포함) · install-autostart.sh(감시 · 백업 크론)를 부르지 않고 :8700 · :8701 도 보지 않는다.
    미룸과 같은 꼴로 실패가 아니다 — skip 으로 세면 deploy-all 이 4 로 끝나고 update-all 이 실패로 적는다."""
    env_text, env = ("KOORM_LOCAL_PARKED=1   # 운영 노드로 옮겼다(11-12)\n", {}) if where == "infra/.env" else (None, {KEY: "1"})
    out, calls, state, ledger, failed = _deploy_koorm(tmp_path, env_text, **env)
    assert calls == ["dist-from-drive.sh"], (calls, out)
    assert "· git: aaa → bbb" in out, "코드는 받는다(점검 문서를 HEAD 로 읽는다)"
    assert f"○ {NAME} — {WHY}" in _plain(out) and "켜려면: 이 박스의 스택을 다시 쓸 때 — infra/.env 의 KOORM_LOCAL_PARKED 줄을 지우고" in out, out
    assert ledger.startswith(NAME + "\t") and ledger.count("\n") == 1, ledger
    assert "SKIP:" not in out and failed == "" and "OK:kooremapper up" not in out, out
    assert "DynaForge 업스트림" not in out and state == [], "업스트림을 보지 않고 기동 지문도 적지 않는다(다시 쓸 때 첫 실행이 띄운다)"


@pytest.mark.parametrize("env_text", [None, "HTTP_PORT=8088\n", "# KOORM_LOCAL_PARKED=1   # 선택 — 필요하면 주석을 풀고 값을 정한다\n"])
def test_표시가_없으면_종전대로_띄운다(tmp_path, env_text):
    out, calls, _state, ledger, _failed = _deploy_koorm(tmp_path, env_text)
    assert calls[:3] == ["dist-from-drive.sh", "stop.sh", "start.sh"], (calls, out)
    assert NAME not in out and ledger == "", out
    assert "DynaForge 업스트림 :8700" in out, "업스트림 확인도 종전대로 한다(이 하네스에선 무응답)"


def test_끝의_Health_도_멈춰_둔_사본을_보지_않는다():
    line = next(ln for ln in DEPLOY.splitlines() if 'probe "koorm  /api/health"' in ln)
    for parked, want in (("1", ""), ("0", "PROBE\n")):
        r = _bash(f'set -euo pipefail\nwant() {{ true; }}; probe() {{ echo PROBE; }}\n_KPARK={parked}\n{line}\necho END')
        assert r.returncode == 0 and r.stdout == want + "END\n", (parked, r.stdout, r.stderr)
    r = _bash(f'set -euo pipefail\nwant() {{ true; }}; probe() {{ echo PROBE; }}\n{line}\necho END')
    assert r.stdout == "PROBE\nEND\n", "kooremapper 를 고르지 않은 실행(_KPARK 미정)에서도 set -u 로 죽지 않는다"


# ── §1b 사전 백업 ─────────────────────────────────────────────────────────────────────────────────────────────
def _backup(tmp_path: Path, env_text: str):
    home = tmp_path / "home"
    portal = home / "claude" / "HWAXPortal"
    (portal / "infra/scripts/lib").mkdir(parents=True)
    shutil.copy2(ROOT / "infra/scripts/backup-local.sh", portal / "infra/scripts/backup-local.sh")
    for n in ("skip-ledger.sh", "koorm-parked.sh"):
        shutil.copy2(LIB / n, portal / "infra/scripts/lib" / n)
    (portal / "infra/.env").write_text(env_text)
    (home / "claude" / "KooRemapper" / "platform").mkdir(parents=True)
    log = tmp_path / "appt.log"; log.write_text("")
    stubbin = tmp_path / "bin"; stubbin.mkdir()
    (stubbin / "apptainer").write_text(f'#!/usr/bin/env bash\necho "apptainer $*" >> "{log}"\n'
                                       '[ "$1 $2" = "instance list" ] && echo "INSTANCE NAME    PID    IP    IMAGE"\nexit 0\n')
    (stubbin / "apptainer").chmod(0o755)
    daily = tmp_path / "backups/hwax/t1/kooremapper/daily"
    daily.mkdir(parents=True)
    old = daily / "kooremapper-t1-20261101-033001.sql.gz"
    old.write_text("old")
    t = time.time() - 30 * 86400
    os.utime(old, (t, t))
    ledger = tmp_path / "ledger"; ledger.write_text("")
    r = _bash(f'bash "{portal}/infra/scripts/backup-local.sh" kooremapper', cwd=tmp_path,
              PATH=f'{stubbin}:{os.environ["PATH"]}', HOME=str(home), BACKUP_ROOT=str(tmp_path / "backups"), HWAX_BOX="t1",
              KEEP_MIN="0", HWAX_SKIP_LEDGER=str(ledger))
    return r, ledger.read_text(), log.read_text(), old.exists()


def test_사전_백업은_멈춰_둔_사본을_실패가_아니라_안_켬으로_넘기고_마지막_덤프를_지킨다(tmp_path):
    r, ledger, appt, kept = _backup(tmp_path, "KOORM_LOCAL_PARKED=1\n")
    out = _plain(r.stdout + r.stderr)
    assert r.returncode == 0, out
    assert "○ kooremapper: 멈춰 둔 되돌림 사본(포털 infra/.env 의 KOORM_LOCAL_PARKED)이라 덤프를 뜨지 않았다" in out and "✗" not in out, out
    assert appt == "", "인스턴스를 묻지도 않는다"
    assert kept and "· 보존:" in out, "멈춰 둔 사본의 마지막 덤프는 세대 정리에서 지킨다(HP-76)"
    assert ledger.startswith(NAME + "\t") and ledger.count("\n") == 1, "deploy-all 의 ○ 와 같은 줄이라 끝 요약에는 한 번만 남는다"


def test_사전_백업은_표시가_없으면_종전대로_인스턴스를_보고_실패로_센다(tmp_path):
    """cae00 11-23 의 그 ✗ 다 — 표시가 없으면 바뀌지 않는다."""
    r, ledger, appt, kept = _backup(tmp_path, "HTTP_PORT=8088\n")
    out = _plain(r.stdout + r.stderr)
    assert r.returncode == 1 and "✗ kooremapper: 인스턴스 koorm_postgres 미동작 — skip" in out and "✗ 백업 1건 실패" in out, out
    assert "instance list" in appt and ledger == "" and "○" not in out


def test_update_all_1b_는_백업_로그의_안_켬_줄을_보인다():
    i = UA.index('hr "1b) 배포 전 로컬 백업')
    b = UA[i:UA.index('rm -f "$BK_LOG"', i)]
    assert b.count("grep '○' \"$BK_LOG\"") == 2, "성공 · 실패 두 갈래 모두 — 꼬리 넷에 들지 않는다"


# ── update-all §5 kr_ PAT 점검 · 내려간 백엔드 살리기 ─────────────────────────────────────────────────────────
def _kr_block() -> str:
    i = UA.index("  # kr_ PAT 는 백엔드가 아니라 heax_registry 안의 예외표라")
    return UA[i:UA.index("  # heax_registry는 /health에 안 나오는", i)]


@pytest.mark.parametrize("parked,base,want", [
    (True, None, "MISSING=[arp]"),                                       # 재지 않는다 — 재면 늘 '만료' 로 읽고 실행마다 재프로비저닝
    (True, "http://127.0.0.1:9", "MISSING=[kr_pat(DynaForge:만료·취소) arp]"),   # 다른 서버로 재라고 주면 종전대로 잰다
    (False, "http://127.0.0.1:9", "MISSING=[kr_pat(DynaForge:만료·취소) arp]"),  # 표시가 없으면 종전대로
])
def test_5_는_멈춰_둔_사본의_로컬_8700_으로_kr_PAT_를_재지_않는다(tmp_path, parked, base, want):
    portal = tmp_path / "portal"; (portal / "infra").mkdir(parents=True)
    (portal / "infra/.env").write_text("KOORM_LOCAL_PARKED=1\n" if parked else "")
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "gateway_config.json").write_text('{"heax_registry": {"app_tokens": {"kooremapper_mcp": "kr_test"}}}')
    env = {} if base is None else {"KOORM_BASE": base}
    r = _bash(f'set -uo pipefail\n. "{LIB}/koorm-parked.sh"\nSELF_REPO="{portal}"; GW_DIR="{gw}"; MISSING="arp"\n'
              f'find_repo() {{ printf %s "{tmp_path}"; }}\n{_kr_block()}\nprintf "MISSING=[%s]\\n" "$MISSING"', **env)
    assert r.returncode == 0 and want in r.stdout, r.stdout + r.stderr
    assert ("○ DynaForge kr_ PAT 점검 건너뜀" in r.stdout) is (parked and base is None), r.stdout


def _heal_arm() -> str:
    i = UA.index("        heax-kooremapper_mcp)\n")
    return UA[i:UA.index("        heax-*)\n", i)]


@pytest.mark.parametrize("parked", [True, False])
def test_내려간_백엔드_살리기는_멈춰_둔_사본을_띄우지_않는다(tmp_path, parked):
    portal = tmp_path / "portal"; (portal / "infra").mkdir(parents=True)
    (portal / "infra/.env").write_text("KOORM_LOCAL_PARKED=1\n" if parked else "")
    r = _bash(f'set -uo pipefail\n. "{LIB}/koorm-parked.sh"\nSELF_REPO="{portal}"; HEAX_DIR=""; UP_SVCS=""; b=heax-kooremapper_mcp\n'
              'http_code() { echo 000; }; bad() { echo "BAD:$*"; }\n'
              f'case "$b" in\n{_heal_arm()}esac\nprintf "UP=[%s]\\n" "$UP_SVCS"')
    assert r.returncode == 0, r.stderr
    assert ("UP=[]" if parked else "UP=[ kooremapper]") in r.stdout, r.stdout
    assert ("멈춰 둔 되돌림 사본이다" in r.stdout) is parked and ("kooremapper 를 함께 띄운다" in r.stdout) is (not parked), r.stdout


# ── 끝의 박스 훅(--hooks-when-idle) · 사전 점검 ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("parked", [True, False])
def test_훅의_바쁨_셈은_멈춰_둔_사본을_모름으로_세지_않는다(tmp_path, parked):
    """DB 가 일부러 내려가 있어 세면 '모름' 이 되고 --hooks-when-idle 이 훅을 늘 건너뛴다."""
    portal = tmp_path / "portal"; (portal / "infra").mkdir(parents=True)
    (portal / "infra/.env").write_text("KOORM_LOCAL_PARKED=1\n" if parked else "")
    sc = tmp_path / "KooRemapper/platform/infra/scripts"; sc.mkdir(parents=True)
    (sc / "_common.sh").write_text("exit 1\n")                       # 인스턴스 · DB 가 없다 — 세지 못한다
    r = _bash(f'. "{LIB}/post-update-hooks.sh"\nhwax_box_busy "{portal}"; echo "rc=$?"', cwd=tmp_path,
              HWAX_AGENT_URL="http://127.0.0.1:9")
    assert ("DynaForge 멈춰 둠" in r.stdout) is parked and ("DynaForge 작업" in r.stdout) is (not parked), r.stdout + r.stderr


def _preflight():
    spec = importlib.util.spec_from_file_location("hwax_preflight_parked", ROOT / "infra/scripts/update-preflight.py")
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


@pytest.mark.parametrize("parked", [True, False])
def test_사전_점검은_멈춰_둔_사본을_셀_수_없다고_하지_않는다(tmp_path, monkeypatch, parked):
    pf = _preflight()
    portal = tmp_path / "portal"; (portal / "infra").mkdir(parents=True)
    (portal / "infra/.env").write_text("KOORM_LOCAL_PARKED=1\n" if parked else "")
    koor = tmp_path / "KooRemapper"; (koor / "platform/infra/scripts").mkdir(parents=True)
    (koor / "platform/infra/scripts/_common.sh").write_text("exit 1\n")
    monkeypatch.delenv(KEY, raising=False)
    monkeypatch.setattr(pf, "ROOT", portal)
    monkeypatch.setattr(pf, "get_json", lambda *_a, **_k: (0, None))
    monkeypatch.setattr(pf, "wiki_health", lambda: {})
    monkeypatch.setattr(pf, "find_repo", lambda n: koor if n == "KooRemapper" else None)
    monkeypatch.setattr(pf, "_koorm_running", (lambda _r: pytest.fail("멈춰 둔 사본을 세려 했다")) if parked else (lambda _r: None))
    pf.RESULTS.clear()
    pf.check_running()
    msgs = [f"{k} {m}" for k, m in pf.RESULTS if "DynaForge" in m]
    assert msgs == (["· DynaForge 로컬 스택은 멈춰 둔 되돌림 사본이다(infra/.env 의 KOORM_LOCAL_PARKED) — update-all 이 코드 · 배포물만 받고 띄우지 않는다"]
                    if parked else ["? DynaForge 도는 로컬 작업을 셀 수 없다(인스턴스 · DB 를 못 물었다)"]), msgs


def test_예시와_안내서에_자리를_적는다():
    assert f"# {KEY}=1" in (ROOT / "infra/.env.example").read_text(encoding="utf-8"), "주석으로만 — env-sync 가 켜지 않는다"
    assert f"unless_env: {KEY}" in (ROOT / "infra/services.yaml").read_text(encoding="utf-8")
    assert KEY in (ROOT / "docs/cae00-deploy-guide.md").read_text(encoding="utf-8")
    assert '. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/koorm-parked.sh"' in DEPLOY
    assert '. "$SELF_REPO/infra/scripts/lib/koorm-parked.sh"' in UA


# ── 장애 안내 문구(docs/request-1125 HP-68) — 멈춰 둔 사본이면 로컬 :8700 · :8701 · deploy-all kooremapper 를 권하지 않는다 ─────────────────
def _hint_fns() -> str:
    src = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    a = src.index("_caddy_dial_of() {")
    b = src.index("\n}\n", src.index("_koorm_where() {")) + 3
    return src[a:b]


def _branch_502() -> str:
    src = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    a = src.index('    elif [ "$code" = "502" ] || [ "$code" = "503" ] || [ "$code" = "504" ]; then')
    b = src.index("\n    elif ", a + 10)
    return "if false; then :\n" + src[a + 4:b] + "\nfi\n"


@pytest.mark.parametrize("parked", [True, False])
def test_502_안내가_멈춰_둔_사본이면_실제_업스트림을_적는다(tmp_path, parked):
    portal = tmp_path / "portal"; (portal / "infra").mkdir(parents=True)
    (portal / "infra/.env").write_text("KOORM_LOCAL_PARKED=1\n" if parked else "")
    lib = (ROOT / "infra/scripts/lib/koorm-parked.sh").read_text(encoding="utf-8")
    body = (lib + "\n" + _hint_fns() + "\n_caddy_dial_of() { echo node-a:8701; }\n"
            'app_bad() { echo "BAD $2"; }\nSELF_REPO="' + str(portal) + '"\ncode=502\napp=kooremapper_mcp\n' + _branch_502())
    r = subprocess.run(["bash", "-c", body], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "KOORM_BASE": "https://node-a/kr"} if parked else {"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0, r.stderr
    if parked:
        assert ":8700" not in r.stdout and ":8701 MCP" not in r.stdout and "deploy-all-from-drive.sh kooremapper" not in r.stdout, r.stdout
        assert "웹 https://node-a/kr · MCP node-a:8701" in r.stdout and "운영 노드 쪽" in r.stdout, r.stdout
    else:
        assert ":8700 웹 / :8701 MCP" in r.stdout and "deploy-all-from-drive.sh kooremapper" in r.stdout, "종전 문구 그대로"


def test_장애_안내_세_자리가_모두_멈춤을_본다():
    src = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    for line in ("(DynaForge=kooremapper_mcp → :8701).", "DynaForge(kooremapper/kooremapper_mcp) → :8700 웹 / :8701 MCP.",
                 "apptainer instance stop koorm_mcp && bash platform/infra/scripts/start.sh"):
        i = src.index(line)
        before = src[max(0, i - 400):i]
        assert "if _koorm_elsewhere; then" in before and "else" in before, line
