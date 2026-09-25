# 공용 배포 게이트·ste 자동 라우트·--with 플래그·잠금·지문 범위 — 셋업/갱신 분리의 기계 가드
"""왜 — "update-all 로 바로 셋업" 과 "routine 에 에어갭 실배포 안 섞임" 은 같은 실행에 두 뜻을 실으면
충돌한다. 셋업(명시 1회)과 갱신(routine)을 가르고, 갱신은 **사람 호출 ∧ 신선도 ∧ 전제조건** 세 신호가
모두 참일 때만 배포한다. 종전 `STE_DEPLOY=1` 게이트는 존재하지 않는 크론을 막느라 요구를 깼다
(2026-09-24 조사). 규칙은 lib 하나에 있고 ste 가 첫 사용처다(사용자 결정 D-13: 새 옵션에도 쓴다).
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/deploy-gate.sh"
UPDATE_ALL = ROOT / "infra/scripts/update-all.sh"
DEPLOY_STE = (ROOT / "infra/scripts/deploy-ste.sh").read_text(encoding="utf-8")
UA_SRC = UPDATE_ALL.read_text(encoding="utf-8")


def _gate(name="ste", *, fresh="true", precond="true", env=None, tty=False):
    """lib 을 그대로 source 해 hwax_gate 를 부른다. stdin 이 터미널이 아니므로 기본은 '사람 아님' 이다."""
    script = f'. "{LIB}"; if hwax_gate {name} --fresh "{fresh}" --precond "{precond}"; then echo GO; else echo NO; fi; echo "R=$HWAX_GATE_REASON"'
    if tty:
        script = "script -qec " + repr("bash -c " + repr(script)) + " /dev/null"
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], **(env or {})}, stdin=subprocess.DEVNULL, timeout=30)
    assert p.returncode == 0, p.stderr
    out = p.stdout.replace("\r", "")
    return ("GO" in out.split("R=")[0]), out.split("R=", 1)[1].strip() if "R=" in out else ""


def test_routine_never_deploys():
    """터미널도 --with 도 없으면(크론·파이프) 무조건 멈춘다 — 신선도·전제가 다 참이어도."""
    go, why = _gate(fresh="true", precond="true")
    assert go is False and "사람이 부른 실행이 아니다" in why


def test_with_flag_forces_even_when_up_to_date():
    """`update-all --with-ste` = 사람이 "지금 이거 해라" — 신선도가 같음이어도 간다."""
    go, _ = _gate(fresh="exit 1", precond="true", env={"HWAX_WITH": "ste"})
    assert go is True


def test_legacy_env_flag_still_forces():
    go, _ = _gate(fresh="exit 1", precond="true", env={"STE_DEPLOY": "1"})
    assert go is True


def test_forced_still_needs_the_precondition():
    """강제라도 전제(예: Teleport 세션)가 죽어 있으면 간 척하지 않는다."""
    go, why = _gate(fresh="true", precond="exit 1", env={"HWAX_WITH": "ste"})
    assert go is False and "전제조건 실패" in why


def test_interactive_but_unchanged_skips():
    """사람이 불렀어도 바뀐 게 없으면(신선도 1) 건너뛴다 — 재기동이 돌던 잡을 끊는다."""
    go, why = _gate(fresh="exit 1", precond="true", env={"UPDATE_ALL_INTERACTIVE": "1"})
    assert go is False and "이미 최신" in why


def test_unknown_freshness_is_not_treated_as_up_to_date():
    """**모름은 같음이 아니다.** 못 잰 것을 같다고 읽으면 낡은 박스를 영원히 건너뛴다.
    사람이 불렀으면 진행하고, 그 사실을 사유로 남긴다."""
    go, why = _gate(fresh="exit 2", precond="true", env={"UPDATE_ALL_INTERACTIVE": "1"})
    assert go is True and "모름" in why


def test_gate_name_is_generic():
    """ste 전용이 아니다 — 다른 이름도 같은 규칙으로 돈다(사용자 결정: 새 옵션에도 유용해야 한다)."""
    go, _ = _gate("stcx", fresh="true", precond="true", env={"HWAX_WITH": "ste stcx"})
    assert go is True
    go, _ = _gate("stcx", fresh="true", precond="true", env={"STCX_DEPLOY": "1"})
    assert go is True


# ── update-all 의 --with-<name> 파싱과 잠금 ──────────────────────────────────
def test_update_all_parses_with_flags_generically():
    assert re.search(r'--with-\*\)\s+HWAX_WITH=', UA_SRC), "--with-<name> 을 이름 무관하게 HWAX_WITH 에 모아야 한다"
    assert "export HWAX_WITH" in UA_SRC


def test_update_all_refuses_to_overlap(tmp_path):
    """두 개가 겹치면 2c 배포 중 재기동·provision --force·게이트웨이 down/up 이 동시에 돈다."""
    i = UA_SRC.index('_LOCK="${TMPDIR:-/tmp}/hwax-update-all.')
    block = UA_SRC[i:UA_SRC.index("\nfi\n", i) + 4]
    script = f'SELF_REPO="{tmp_path}"; TMPDIR="{tmp_path}"\n{block}\necho HELD; sleep 3'
    first = subprocess.Popen(["bash", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    import time; time.sleep(0.8)
    second = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=20)
    first.wait(timeout=20)
    assert "HELD" in first.stdout.read()
    assert second.returncode == 3 and "이미 돌고 있다" in second.stderr


# ── 1d 자동 라우트 ────────────────────────────────────────────────────────────
def _run_1d(tmp_path, *, mode: str | None, routes_local: str | None, env=None) -> tuple[str, str]:
    i = UA_SRC.index('_STE_TENV="$SELF_REPO/../SmartTwinExplorer/deploy/transport.env"')
    block = UA_SRC[i:UA_SRC.index("# ── 2) 전 서비스 배포", i)]
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True, exist_ok=True)
    ste = tmp_path / "SmartTwinExplorer/deploy"; ste.mkdir(parents=True, exist_ok=True)
    tenv = ste / "transport.env"; tenv.unlink(missing_ok=True)
    if mode is not None:
        tenv.write_text(f"TRANSPORT_MODE={mode}\n", encoding="utf-8")
    rl = repo / "backend/config/routes.local.env"; rl.unlink(missing_ok=True)
    if routes_local is not None:
        rl.write_text(routes_local, encoding="utf-8")
    script = f'SELF_REPO="{repo}"\nhr() {{ :; }}; ok() {{ echo "OK:$*"; }}\n{block}'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], **(env or {})}, timeout=20)
    assert p.returncode == 0, p.stderr
    return p.stdout, (rl.read_text(encoding="utf-8") if rl.exists() else "")


def test_autoroute_writes_the_tunnel_route_on_a_fresh_teleport_box(tmp_path):
    out, rl = _run_1d(tmp_path, mode="teleport", routes_local=None)
    assert "OK:" in out and "ste=http://127.0.0.1:15810/" in rl


def test_autoroute_never_touches_direct_boxes_or_existing_lines(tmp_path):
    _, rl = _run_1d(tmp_path, mode="direct", routes_local=None)
    assert "ste=" not in rl                                   # direct 는 주소가 박스마다 다르다
    _, rl = _run_1d(tmp_path, mode="teleport", routes_local="ste=http://203.0.113.9:15810/\n")
    assert rl.count("ste=") == 1 and "203.0.113.9" in rl          # 있으면 절대 안 건드린다
    _, rl = _run_1d(tmp_path, mode="teleport", routes_local="ste=\n")
    assert rl.strip() == "ste="                                # 빈 값 = "서빙 안 함" 명시 — 존중


def test_autoroute_can_be_switched_off(tmp_path):
    _, rl = _run_1d(tmp_path, mode="teleport", routes_local=None, env={"HWAX_STE_AUTOROUTE": "0"})
    assert rl == ""


# ── --if-stale 지문 범위 ──────────────────────────────────────────────────────
def test_fingerprint_covers_every_tree_the_deploy_ships():
    """backend/src·web 만 보면 MCP 서버·앱 정의가 낡아도 '이미 최신' 이다."""
    for d in ("backend/src", "backend/mcp_server", "apps", "frontend/dist"):
        assert d in DEPLOY_STE.split("_lman=")[1].split("\n")[0], d
    for d in ("/opt/ste/backend/src", "/opt/ste/backend/mcp_server", "/opt/ste/apps", "/opt/ste/web"):
        assert d in DEPLOY_STE, d


def test_teleport_branch_uses_the_shared_gate():
    assert "deploy-gate.sh" in DEPLOY_STE and "hwax_gate ste" in DEPLOY_STE
    assert 'STE_DEPLOY:-0}" != 1 ]; then' not in DEPLOY_STE, "옛 단일 플래그 게이트가 남아 있다"
