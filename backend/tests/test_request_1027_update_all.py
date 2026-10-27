# 10-27 수정 요청(docs/request-1027)의 update-all 항목 — heax 재검증(HP-09) · 자동 복구 앞 심의 확인(HP-08) · 도구 지도를 파일로(HP-06)
"""update-all 은 dev 에서 통째로 돌리지 않는다(리포 리셋 · 재기동). 고친 구획을 원문 그대로 떼어, 바깥 의존(curl · 게이트웨이 · ss · kill)은
함수로 가로막고 돌린다.

  · HP-09 — 사람별 위임만 있는 heax_registry(토큰 · 앱 목록 주소 없음)는 재프로비저닝 대상이다. §6 은 HEAX Hub 앱 0개를 집계에 넣는다
    (레지스트리 없음 + 허브 있음 = ✗, 레지스트리는 있는데 앱 0개 = ⚠).
  · HP-08 — 심의가 돌면 자동 복구는 ○ 로 미루고(1) 재프로비저닝 · 재기동을 부르지 않는다. 아니면 종전대로 고친다(0).
  · HP-06 — 128 KiB 를 넘는 도구 지도도 세 곳(heax 앱 수 · 갱신 전후 비교 · MCP_COUNTS)이 읽는다. 환경 변수로 넘기는 곳이 남지 않았다.
"""
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
LIB = ROOT / "infra/scripts/lib"
MAX_ARG_STRLEN = 131072


def _region(start: str, end: str, *, include_end: bool = True) -> str:
    assert start in UA, start
    i = UA.index(start)
    j = UA.index(end, i)
    return UA[i:j + (len(end) if include_end else 0)]


def _run(body: str, tmp: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    script = "\n".join([
        "set -uo pipefail",
        'ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
        # 바깥을 건드리는 명령은 함수로 막는다 — 시험이 실 게이트웨이 · 에이전트를 두드리거나 죽이지 않게
        'ss() { :; }; kill() { echo "KILL $*" >> "$CALLS"; }; sleep() { :; }',
        f'export HWAX_SKIP_LEDGER="{tmp}/ledger"; : > "$HWAX_SKIP_LEDGER"',
        f'. "{LIB}/skip-ledger.sh"',
        body, "echo END",
    ])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp), "CALLS": str(tmp / "calls"), **(env or {})})
    assert "END" in r.stdout, r.stdout + r.stderr
    assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
    return r


# ── HP-09 §5 — 재프로비저닝 대상 판정 ────────────────────────────────────────────────────────────────
_S5 = _region("  # heax_registry는 /health에 안 나오는 config 전용 항목", 'MISSING="heax_registry${MISSING:+ $MISSING}"\n  fi\n')


def _s5(tmp: Path, cfg) -> str:
    gw = tmp / "gw"; gw.mkdir(exist_ok=True)
    (gw / "gateway_config.json").write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    r = _run(f'GW_DIR="{gw}"; HEAX_MCP_TOKEN=x; MISSING=""\nfind_repo() {{ :; }}\n{_S5}\necho "MISSING=[$MISSING]"', tmp)
    return re.search(r"MISSING=\[(.*)\]", r.stdout).group(1)


def test_HP09_위임만_있는_heax_registry_는_재프로비저닝_대상이다(tmp_path):
    assert _s5(tmp_path, {"heax_registry": {"per_user_sso": {"ste": {"secret": "s"}}}}) == "heax_registry", "키만 있으면 ✓ 였다"
    assert _s5(tmp_path, {"heax_registry": {"token": "heax_x"}}) == "heax_registry", "앱 목록 주소가 없으면 탐지가 안 돈다"
    assert _s5(tmp_path, {"heax_registry": {"token": "heax_x", "servers_url": "http://hub/api"}}) == ""
    assert _s5(tmp_path, "깨진 설정") == "heax_registry"


# ── HP-09 §6 — HEAX Hub 앱 0개는 집계에 든다 ─────────────────────────────────────────────────────────
_S6 = _region("  # HEAX Hub 앱 0개는 집계에 든다", "  esac\n")


def _s6(tmp: Path, backends: dict, hub: bool) -> str:
    h = json.dumps({"tools": 3, "backends": backends})
    fr = f'find_repo() {{ echo "{tmp}/HEAXHub"; }}' if hub else "find_repo() { :; }"
    return _run(f"{fr}\nH='{h}'\n{_S6}", tmp).stdout


def test_HP09_레지스트리가_없으면_허브가_있는_박스에서_실패로_센다(tmp_path):
    out = _s6(tmp_path, {"aidatahub": True}, hub=True)
    assert "FAIL:HEAX Hub 앱 0개 — heax_registry 미구성" in out, out
    out = _s6(tmp_path, {"aidatahub": True}, hub=False)
    assert "BAD:HEAX Hub 앱 0개 — heax_registry 미구성(이 박스엔 HEAXHub 가 없다)" in out and "FAIL:" not in out, out


def test_HP09_레지스트리는_있는데_앱이_0개면_경고다(tmp_path):
    out = _s6(tmp_path, {"heax_registry": True}, hub=True)
    assert "BAD:HEAX Hub 앱 0개 발견" in out and "FAIL:" not in out, out
    out = _s6(tmp_path, {"heax_registry": True, "heax-step_forge": True}, hub=True)
    assert "HEAX Hub 앱 발견: heax-step_forge=up" in out and "BAD:" not in out and "FAIL:" not in out, out


# ── HP-08 — 자동 복구 앞 심의 확인 ────────────────────────────────────────────────────────────────────
_REPAIR = _region("repair_mcp() {", "\n}\n")


def _repair(tmp: Path, busy_rc: int) -> tuple[subprocess.CompletedProcess, list[str]]:
    gw = tmp / "gw"; gw.mkdir(exist_ok=True)
    port = 1                                                   # 듣는 것이 없는 자리 — ss 도 막았지만 겹으로
    (gw / "gateway_config.json").write_text(json.dumps({"_gateway": {"port": port}}), encoding="utf-8")
    for name in ("sync-provision-env.sh", "provision-config.sh", "start.sh"):
        (gw / name).write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "$CALLS"\n')
        (gw / name).chmod(0o755)
    stub = f'hwax_delib_busy() {{ echo "2 1"; return {busy_rc}; }}'
    r = _run(f'GW_DIR="{gw}"\n{stub}\n{_REPAIR}\nrc=0; repair_mcp || rc=$?\necho "RC=$rc"', tmp)
    calls = (tmp / "calls").read_text().splitlines() if (tmp / "calls").exists() else []
    return r, calls


def test_HP08_심의가_돌면_복구를_미루고_아무것도_부르지_않는다(tmp_path):
    r, calls = _repair(tmp_path, busy_rc=0)
    assert "RC=1" in r.stdout and calls == [], (r.stdout, calls)
    ledger = (tmp_path / "ledger").read_text()
    assert "MCP 자동 복구" in ledger and "AGENT_RESTART_FORCE=1" in ledger, ledger


def test_HP08_심의가_없거나_모르면_종전대로_고친다(tmp_path):
    for rc in (1, 2):                                          # 1 = 없다 · 2 = 모른다(에이전트가 답하지 않음)
        (tmp_path / "calls").unlink(missing_ok=True)
        r, calls = _repair(tmp_path, busy_rc=rc)
        assert "RC=0" in r.stdout, r.stdout + r.stderr
        assert [c.split()[0] for c in calls] == ["sync-provision-env.sh", "provision-config.sh", "start.sh"], calls


def test_HP08_미룬_복구는_실패가_아니라_경고다():
    i = UA.index('elif [ "$rc" = 1 ] && ! repair_mcp; then')
    assert UA[i:i + 300].count('bad "MCP 백엔드 중 호출이 전량 실패하는 것이 있다') == 1


# ── HP-06 — 도구 지도를 파일로 ──────────────────────────────────────────────────────────────────────
def _big_map(n_tools: int, apps: list[tuple[str, int]]) -> str:
    m = {"map": {f"tool_{i:05d}_{'x' * 40}": "heax-big" for i in range(n_tools)},
         "apps": [{"app": a, "tool_count": c, "reachable": True} for a, c in apps]}
    s = json.dumps(m)
    assert len(s) > MAX_ARG_STRLEN, "시험 지도는 환경 변수 한 줄 상한보다 커야 한다"
    return s


def test_HP06_환경_변수로_도구_지도를_넘기는_곳이_없다():
    assert not re.search(r'\b[A-Z_]*TM="\$TM(_BEFORE)?"\s', UA), "TM 을 환경 변수로 넘기는 곳이 남았다"
    assert 'environ["TM"]' not in UA and 'environ["AFTER_TM"]' not in UA


def test_HP06_큰_지도도_heax_앱_수를_읽는다(tmp_path):
    f = tmp_path / "tm.json"; f.write_text(_big_map(4000, [("heax-a", 3), ("heax-b", 0)]), encoding="utf-8")
    site1 = _region('TM="$(curl -s -m 6 http://127.0.0.1:9110/tools-map', '  rm -f "$_tmf"\nfi\n')
    r = _run(f'curl() {{ cat "{f}"; }}\n{site1}', tmp_path)
    assert "heax MCP 앱 2개 중 도구 노출 1개" in r.stdout and "BAD:" not in r.stdout, r.stdout + r.stderr
    assert "Argument list too long" not in r.stderr


def test_HP06_큰_지도도_전후_비교와_MCP_COUNTS_가_돈다(tmp_path):
    before, after = tmp_path / "b.json", tmp_path / "a.json"
    big = json.loads(_big_map(4000, [("heax-a", 3)]))
    before.write_text(json.dumps(big), encoding="utf-8")
    big["map"]["new_tool"] = "heax-a"; del big["map"]["tool_00000_" + "x" * 40]
    after.write_text(json.dumps(big), encoding="utf-8")
    jok = re.search(r"^json_ok\(\) \{.*\}$", UA, re.M).group(0)
    block = _region('TM="$(_tm_snapshot)"\n', 'fail "게이트웨이 /tools-map 을 읽지 못함', include_end=False)
    block = block + 'fi\n'
    pre = f'{jok}\n_tm_snapshot() {{ cat "{after}"; }}\nTM_BEFORE="$(cat "{before}")"\n'
    r = _run(pre + block + 'echo "COUNTS=[$MCP_COUNTS]" "TM_OK=$TM_OK"', tmp_path)
    assert "· 도구 변화:" in r.stdout and "+new_tool" in r.stdout and "-tool_00000_" in r.stdout, r.stdout + r.stderr
    assert "COUNTS=[a 3 1]" in r.stdout and "TM_OK=1" in r.stdout, r.stdout
    assert "BAD:" not in r.stdout and "FAIL:" not in r.stdout and "Argument list too long" not in r.stderr, r.stdout + r.stderr


# ── HP-01 — KooRemapper 재기동 동안 배포 표지 ────────────────────────────────────────────────────────
_DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")


def _koorm_marker_block() -> str:
    i = _DEPLOY.index('      _dl="platform/infra/data/deploy.lock.d"')
    j = _DEPLOY.index("\n", _DEPLOY.index("      _start() {", i)) + 1
    return _DEPLOY[i:j]


def _koorm(tmp: Path, start_rc: int, tail: str) -> tuple[subprocess.CompletedProcess, Path]:
    repo = tmp / "KooRemapper"
    (repo / "platform/infra/scripts").mkdir(parents=True, exist_ok=True)
    (repo / "platform/infra/data").mkdir(parents=True, exist_ok=True)
    for name, body in (("stop.sh", 'echo "stop marker=$(cat platform/infra/data/deploy.lock.d/pid 2>/dev/null)" >> "$CALLS"'),
                       ("start.sh", f'echo "start marker=$([ -d platform/infra/data/deploy.lock.d ] && echo yes || echo no)" >> "$CALLS"; exit {start_rc}')):
        (repo / "platform/infra/scripts" / name).write_text(f"#!/usr/bin/env bash\n{body}\n")
    body = f'( cd "{repo}"\n{_koorm_marker_block()}\n{tail}\n) ; echo "SUB=$?"\n'
    return _run(body, tmp), repo / "platform/infra/data/deploy.lock.d"


def test_HP01_표지는_내린_뒤_올리는_동안만_있다(tmp_path):
    r, marker = _koorm(tmp_path, 0, '_stop; _start; echo "START_RC=$?"')
    calls = (tmp_path / "calls").read_text().splitlines()
    assert calls[0].startswith("stop marker=") and calls[0].endswith(" deploy-all"), ("내리기 전에 pid · 시각 · 주체를 적는다", calls)
    assert calls[1] == "start marker=yes", "start.sh 가 도는 동안은 표지가 있다 — 감시가 비킨다"
    assert "START_RC=0" in r.stdout and not marker.exists(), "올린 뒤 지운다"


def test_HP01_실패해도_미뤄도_표지는_남지_않는다(tmp_path):
    r, marker = _koorm(tmp_path, 1, '_stop; _start; echo "START_RC=$?"')
    assert "START_RC=1" in r.stdout and not marker.exists(), ("start 실패는 rc 를 그대로 돌려주고 표지는 지운다", r.stdout)
    (tmp_path / "calls").unlink()
    r, marker = _koorm(tmp_path, 0, "_stop; exit 3")                 # 내린 뒤 서브셸이 끝나도(미룸 · 예외) EXIT 가 지운다
    assert "SUB=3" in r.stdout and not marker.exists(), r.stdout
