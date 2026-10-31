# update-all 의 심의 기다림 하나가 에이전트 서버 · 게이트웨이 · SignalForge 재기동을 함께 덮는다(docs/delib-ops O1 · 10-31 A25, 사용자 결정 (가))
"""왜 — 10-22 O1 은 에이전트 서버를 다시 띄우기 전에만 새 심의를 멈추고 도는 심의가 끝나기를 기다렸다. 그런데 update-all 은 그보다 먼저 §2 에서
SignalForge(그 down.sh 는 MCP 까지 내린다)를, §4 에서 signalforge-mcp 와 게이트웨이를 묻지 않고 다시 띄웠다. 도는 좌석은 게이트웨이로 도구를
부른다 — 심의 중에 내리면 그 순간의 호출이 실패한다(8·9·10차 server-setup §6 '심의 보호가 닿지 않는 재기동'). 사용자 결정 (가) — 기다림을 그 둘의
재기동 앞으로 당긴다. 기다림은 한 실행에 하나다 — 처음 재기동할 것에서 기다리고, 끝나면 멈춤을 세워 둔 채 셋을 다 재기동하고, 못 끝나면 셋 다 미룬다.
AIDataHub · KooRemapper · 자기치유는 그대로다((다)가 아니다).

update-sites 와 deploy-all 의 구획을 **원문 그대로 떼어** 지어낸 에이전트 서버(GET /health · POST /drain)와 지어낸 서비스에 돌린다. 실물 9009 ·
9110 · 18000 · 17370 은 건드리지 않는다(주소는 커널이 고른 빈 포트다 — 하네스가 실물 주소가 남았는지 본다).
"""
import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
BUSY_LIB = LIBDIR / "delib-busy.sh"
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
LIBS = f'. "{LIBDIR}/change-detect.sh"\n. "{LIBDIR}/skip-ledger.sh"\n. "{BUSY_LIB}"\n'
REAL = ("127.0.0.1:9009", "localhost:9009", "127.0.0.1:18000", "127.0.0.1:17370", "localhost:9110")
DEAD = "http://127.0.0.1:9/health"


@pytest.fixture()
def agent(tmp_path):
    """지어낸 에이전트 서버. GET /health 는 state 로 답한다 — active 는 정수 또는 차례로 꺼낼 목록(마지막 값을 되풀이), queued · durable ·
    paused/by. POST /drain 은 본문을 posts 에 적고 사건 파일(events)에 'POST on|off' 를 덧붙인다 — 대역 services.sh · down.sh 도 같은 파일에 적어
    '멈춤을 세운 뒤에 내렸나' 를 차례로 본다."""
    st = {"active": 0, "queued": 0, "durable": True, "paused": False, "by": None, "posts": [], "gets": 0,
          "events": tmp_path / "events"}
    st["events"].write_text("")

    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code, obj):
            raw = json.dumps(obj).encode()
            self.send_response(code); self.send_header("content-type", "application/json"); self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != "/health":
                self.send_response(404); self.end_headers(); return
            st["gets"] += 1
            a = st["active"]
            if isinstance(a, list):
                a = a.pop(0) if len(a) > 1 else a[0]
            self._send(200, {"status": "ok", "delib_active": a, "delib_queued": st["queued"], "delib_paused": st["paused"],
                             "delib_queue_durable": st["durable"], "delib_requeued": 0,
                             "delib_pause": {"on": st["paused"], "by": st["by"], "scope": "delib" if st["paused"] else None}})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            st["posts"].append(body)
            with st["events"].open("a", encoding="utf-8") as fh:
                fh.write(f"POST {'on' if body.get('on') else 'off'}\n")
            st["paused"], st["by"] = bool(body.get("on")), (body.get("by") if body.get("on") else None)
            self._send(200, {"on": st["paused"], "scope": "delib" if st["paused"] else None, "by": st["by"],
                             "until": 1e12 if st["paused"] else None, "hold": False})

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    st["url"] = f"http://127.0.0.1:{srv.server_address[1]}/health"
    st["base"] = st["url"][: -len("/health")]
    yield st
    srv.shutdown(); srv.server_close()


@pytest.fixture()
def svc():
    """지어낸 서비스(게이트웨이 · signalforge-mcp · SignalForge API 자리) — 무엇을 물어도 200 이다(살아 있다)."""
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown(); srv.server_close()


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    assert env.get("HWAX_AGENT_URL"), "에이전트 주소를 지어낸 서버로 준다 — 안 주면 lib 기본값(실물 9009)을 두드린다"
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "HWAX_DELIB_WAIT_POLL_S": "1", **env})


def _under_update_all(tmp_path: Path) -> dict:
    """update-all 머리가 물려주는 셋(멈춤 주인 · 표지 · 한 번 기다리기의 판정 파일)."""
    return {"HWAX_DELIB_GATE": str(tmp_path / "ledger.delib-gate"), "HWAX_DELIB_PAUSE_BY": "update-all",
            "HWAX_DELIB_PAUSE_MARK": str(tmp_path / "ledger.delib-pause")}


def _events(agent) -> list[str]:
    return agent["events"].read_text(encoding="utf-8").splitlines()


def _gate_state(tmp_path: Path) -> str | None:
    f = tmp_path / "ledger.delib-gate"
    return f.read_text().strip() if f.exists() else None


# ── §4 update-sites — signalforge-mcp · 게이트웨이 · 에이전트 서버 ──────────────────────────────────────────────
def _sites(tmp_path: Path, agent, svc_url: str, names: str, *, under: bool = True, last_fp: dict | None = None, **env):
    """update-sites 의 restart_svc 부터 끝까지(요약 · 종료코드 포함)를 대역 services.sh 로 돌린다 → (결과, 걸린 초, 장부).
    대역은 health 로 agent-server 엔 지어낸 에이전트 서버를, 나머지엔 svc_url 을 답하고 down · up 을 사건 파일에 적는다."""
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    for n, fp in (last_fp or {}).items():
        (st / n).write_text(fp + "\n")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    stub = tmp_path / "svc.sh"
    stub.write_text('#!/usr/bin/env bash\n'
                    'case "$1" in update) echo "  · $2  updated: a → b";; fp) echo f-new;; status) echo "  ✓ up  $2";;\n'
                    f'  health) if [ "$2" = agent-server ]; then echo {agent["url"]}; else echo {svc_url}; fi;;\n'
                    f'  enabled) exit 0;;\n  down|up) echo "$1 $2" >> "{agent["events"]}";;\nesac\nexit 0\n')
    stub.chmod(0o755)
    body = UPDATE_SITES[UPDATE_SITES.index('SKIPPED_RESTART=""'):]
    assert not any(x in body for x in REAL), "update-sites 의 그 구획에 실물 주소가 박혔다 — 하네스가 떠 있는 서비스를 두드린다"
    script = (f'set -uo pipefail\nSVC="{stub}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nHAS_PORTAL=0; PORTAL=portal; REST="{names}"; TARGETS="{names}"\nshow_cause() {{ :; }}\n{body}')
    t0 = time.monotonic()
    r = _sh(script, HWAX_AGENT_URL=agent["base"], **(_under_update_all(tmp_path) if under else {}), **env)
    return r, time.monotonic() - t0, ledger.read_text()


def test_게이트웨이도_도는_심의가_끝나기를_멈춘_채_기다린_뒤_재기동한다(tmp_path, agent, svc):
    """**이 파일의 이유다** — 종전엔 게이트웨이를 묻지 않고 내렸다(그 순간 좌석의 도구 호출이 실패한다). 멈춤을 먼저 세우고 끝나기를 기다린다."""
    agent.update(active=[1, 1, 1, 0], queued=0)
    r, _, ledger = _sites(tmp_path, agent, svc, "mcp-gateway", HWAX_DELIB_WAIT_S="30")
    ev = _events(agent)
    assert ev[:2] == ["POST on", "down mcp-gateway"] and "up mcp-gateway" in ev, (ev, r.stdout + r.stderr)
    assert agent["posts"][0] == {"on": True, "scope": "delib", "by": "update-all", "ttl_s": 1830,
                                 "reason": "게이트웨이 재기동 — 도는 심의가 끝나기를 기다린다(update-all)"}, agent["posts"]
    assert "· mcp-gateway: 도는 심의가 끝났다" in r.stdout and ledger == "", r.stdout
    assert _gate_state(tmp_path) == "waited" and (tmp_path / "ledger.delib-pause").read_text().strip() == agent["url"], \
        "멈춤은 남겨 두고(끝맺음이 내린다) 표지 · 판정을 남긴다"


def test_게이트웨이도_못_기다리면_미루고_멈춤을_그_자리에서_내린다(tmp_path, agent, svc):
    agent.update(active=1, queued=0)
    r, _, ledger = _sites(tmp_path, agent, svc, "mcp-gateway", HWAX_DELIB_WAIT_S="2")
    ev = _events(agent)
    assert ev == ["POST on", "POST off"], (ev, r.stdout + r.stderr)
    assert r.returncode == 3 and "▶ ○ 재기동 미룸" in r.stdout and "mcp-gateway" in r.stdout, r.stdout + r.stderr
    line = next(ln for ln in ledger.splitlines() if ln.startswith("mcp-gateway 재기동 건너뜀"))
    assert "심의 1건 진행 중, 0건 대기" in line and "도구 호출이 그 순간 실패한다" in line and "AGENT_RESTART_FORCE=1" in line, line
    assert _gate_state(tmp_path) == "deferred" and not (tmp_path / "ledger.delib-pause").exists()


def test_기다림_하나가_셋을_덮는다_끝나면_셋_다_멈춤_아래서_재기동한다(tmp_path, agent, svc):
    """처음 재기동할 것(signalforge-mcp)에서 한 번 기다린다 — 뒤의 둘은 다시 기다리지 않고 멈춤 아래서 재기동한다."""
    agent.update(active=[1, 1, 1, 0], queued=0)
    r, _, ledger = _sites(tmp_path, agent, svc, "signalforge-mcp mcp-gateway agent-server", HWAX_DELIB_WAIT_S="30")
    ev = _events(agent)
    downs = [e for e in ev if e.startswith("down ")]
    assert ev[0] == "POST on" and downs == ["down signalforge-mcp", "down mcp-gateway", "down agent-server"], (ev, r.stdout + r.stderr)
    assert ev.count("POST on") == 1 and "POST off" not in ev, "기다림은 한 번이고 멈춤은 끝맺음이 내린다"
    assert r.stdout.count("기다린 뒤 재기동한다") == 1 and ledger == "", r.stdout


def test_기다림_하나가_셋을_덮는다_못_끝나면_셋_다_미룬다(tmp_path, agent, svc):
    """못 끝나면 셋 다 미룬다 — 뒤의 둘은 다시 기다리지 않는다(기다림이 셋으로 늘지 않는다)."""
    agent.update(active=1, queued=0)
    r, took, ledger = _sites(tmp_path, agent, svc, "signalforge-mcp mcp-gateway agent-server", HWAX_DELIB_WAIT_S="3")
    ev = _events(agent)
    assert ev == ["POST on", "POST off"], (ev, r.stdout + r.stderr)
    names = [ln.split("\t", 1)[0] for ln in ledger.splitlines()]
    assert names == ["signalforge-mcp 재기동 건너뜀", "mcp-gateway 재기동 건너뜀", "agent-server 재기동 건너뜀"], ledger
    assert r.returncode == 3 and took < 3 * 3, f"기다림이 한 번이 아니다({took:.1f}초)"
    assert r.stdout.count("다시 기다리지 않고 재기동을 미룬다") == 2, r.stdout


@pytest.mark.parametrize("state,active,restarted", [("deferred", 1, False), ("waited", 1, False), ("waited", 0, True), ("deferred", 0, True)])
def test_앞에서_쓴_기다림의_판정을_따른다(tmp_path, agent, svc, state, active, restarted):
    """§2 의 SignalForge 가 기다림을 썼으면 §4 는 다시 기다리지 않는다 — 묻는 순간 비었으면 재기동하고 돌면 미룬다."""
    agent.update(active=active, queued=0)
    (tmp_path / "ledger.delib-gate").write_text(state + "\n")
    r, took, ledger = _sites(tmp_path, agent, svc, "mcp-gateway", HWAX_DELIB_WAIT_S="30")
    assert agent["posts"] == [] and took < 10, (agent["posts"], took)
    assert ("down mcp-gateway" in _events(agent)) is restarted, r.stdout + r.stderr
    assert ("mcp-gateway 재기동 건너뜀" in ledger) is (not restarted)


@pytest.mark.parametrize("case", ["혼자_돈_update_sites", "게이트웨이가_내려가_있다", "강행", "바뀌지_않았다"])
def test_묻지_않는_갈래(tmp_path, agent, svc, case):
    """혼자 돈 update-sites(손으로 게이트웨이만) · 내려간 게이트웨이(끊을 호출이 없다) · 강행 · 바뀌지 않아 생략하는 실행은 에이전트 서버에 묻지 않는다."""
    agent.update(active=1, queued=0)
    r, _, ledger = _sites(tmp_path, agent, DEAD if case == "게이트웨이가_내려가_있다" else svc, "mcp-gateway",
                          under=case != "혼자_돈_update_sites", last_fp={"mcp-gateway": "f-new"} if case == "바뀌지_않았다" else None,
                          **({"AGENT_RESTART_FORCE": "1"} if case == "강행" else {}), HWAX_DELIB_WAIT_S="30")
    assert agent["gets"] == 0 and agent["posts"] == [] and ledger == "", (case, agent["gets"], r.stdout + r.stderr)
    assert ("down mcp-gateway" in _events(agent)) is (case != "바뀌지_않았다"), (case, r.stdout)


def test_에이전트_서버가_매달렸으면_게이트웨이는_모른다고_말하고_재기동한다(tmp_path, svc):
    """심의 수를 모르면(2 · 4) 종전대로 재기동한다 — 조용하면 물은 줄 안다. 매달림(4)은 그 사실을 말한다."""
    class Slow(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(5)
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"delib_active": 1, "delib_queued": 0}')

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        slow = {"url": f"http://127.0.0.1:{srv.server_address[1]}/health", "events": tmp_path / "events"}
        slow["base"] = slow["url"][: -len("/health")]
        slow["events"].write_text("")
        r, _, ledger = _sites(tmp_path, slow, svc, "mcp-gateway", HWAX_DELIB_WAIT_S="30", HWAX_DELIB_PROBE_STRIKES="1")
    finally:
        srv.shutdown(); srv.server_close()
    assert "down mcp-gateway" in slow["events"].read_text() and ledger == "", r.stdout + r.stderr
    assert "· mcp-gateway: 에이전트 서버 /health 가 연속으로 4초 안에 답하지 않았다" in r.stdout, r.stdout


# ── §2 deploy-all — SignalForge(down.sh 는 MCP 까지 내린다) ───────────────────────────────────────────────
_SF_API, _SF_WEB, _AGENT_HEALTH = "http://127.0.0.1:18000/health", "http://127.0.0.1:17370/", "http://127.0.0.1:9009/health"


def _deploy_common() -> str:
    i = DEPLOY.index('HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-')
    return DEPLOY[i:DEPLOY.index("# ── 1. Portal (the hub)", i)]


def _sf_block() -> str:
    i = DEPLOY.index("if want signalforge; then\n")
    return DEPLOY[i:DEPLOY.index("# ── 4. AI Data Hub", i)]


def _deploy_sf(tmp_path: Path, agent, api: str, *, under: bool = True, sif_change: bool = False, **env):
    """deploy-all 의 SignalForge 구획을 임시 SignalForge 리포에서 돌린다 → (화면, 장부, skip 으로 센 줄). 받기 · down · up · DB 병합은 사건 파일에
    적는 대역이다. sif_change 면 받기 대역이 SIF 를 바꾼다(떠 있는 인스턴스 밑을 덮었다)."""
    sf = tmp_path / "SignalForge"
    (sf / "scripts/drive-sync").mkdir(parents=True)
    (sf / "apptainer/sif").mkdir(parents=True)
    (sf / "apptainer/sif/backend.sif").write_bytes(b"x")
    ev = agent["events"]
    for rel, extra in (("scripts/down.sh", ""), ("scripts/up.sh", ""), ("scripts/drive-sync/merge-from-drive.sh", ""),
                       ("scripts/sync-from-drive.sh", 'echo y >> apptainer/sif/backend.sif\n' if sif_change else "")):
        p = sf / rel
        p.write_text(f'#!/usr/bin/env bash\necho "{Path(rel).name}" >> "{ev}"\n{extra}exit 0\n'); p.chmod(0o755)
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    (st / "signalforge").write_text("old-fp\n")
    ledger = tmp_path / "ledger"; ledger.write_text("")
    failed = tmp_path / "failed"; failed.write_text("")
    stubbin = tmp_path / "bin"; stubbin.mkdir(exist_ok=True)
    (stubbin / "apptainer").write_text(f'#!/usr/bin/env bash\necho "apptainer $*" >> "{ev}"\nexit 0\n'); (stubbin / "apptainer").chmod(0o755)
    body = _deploy_common() + 'RESTART="${NO_RESTART:-0}"\n' + _sf_block()
    assert _SF_API in body and _SF_WEB in body and _AGENT_HEALTH in body, "주소가 바뀌었다 — 하네스가 바꿔 끼울 자리를 다시 찾는다"
    body = body.replace(_SF_API, f"{api}/health").replace(_SF_WEB, f"{api}/").replace(_AGENT_HEALTH, agent["url"])
    assert not any(x in body for x in REAL), "실물 주소가 남았다 — 하네스가 떠 있는 서비스를 두드린다"
    script = (f'set -euo pipefail\ncd "{tmp_path}"\n'
              f'[ "$(command -v apptainer)" = "{stubbin}/apptainer" ] || {{ echo "HARNESS: apptainer 가 대역이 아니다" >&2; exit 97; }}\n'
              f'SF_DIR="{sf}"; PORTAL_DIR="{tmp_path}/portal"; DEPLOY_FAILED_FILE="{failed}"\n'
              f'[ "$(cd "$SF_DIR" && pwd)" = "{sf}" ] || {{ echo "HARNESS: 임시 리포로 못 들어간다" >&2; exit 97; }}\n'
              'want() { true; }; hr() { echo "── $*"; }; ok() { echo "OK:$*"; }\n'
              'skip() { echo "SKIP:$*"; printf "%s\\n" "$*" >> "$DEPLOY_FAILED_FILE"; }\n'
              'git_update() { echo "  · git: aaa → bbb (reset to origin/main)"; }; set_remote() { :; }\n'
              f'{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_SKIP_LEDGER="{ledger}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1\n'
              f'{body}\necho "END"\n')
    r = _sh(script, PATH=f'{stubbin}:{os.environ["PATH"]}', HWAX_AGENT_URL=agent["base"],
            **(_under_update_all(tmp_path) if under else {}), **env)
    assert r.returncode != 97, r.stderr
    assert "END" in r.stdout, r.stdout + r.stderr
    return r.stdout + r.stderr, ledger.read_text(), failed.read_text()


def test_SignalForge_도_못_기다리면_내리지_않고_받은_것도_병합하지_않는다(tmp_path, agent, svc):
    """**§2 의 이유다** — 종전엔 SignalForge 를 묻지 않고 내렸다(down.sh 가 MCP 까지 내려 좌석의 VOC 도구 호출이 실패한다). 미룬 것은 ○ 한 줄이고
    실패가 아니다 — skip 으로 세면 심의가 도는 동안의 update-all 이 deploy-all 4 를 받아 ✗ 로 끝난다."""
    agent.update(active=1, queued=0)
    out, ledger, failed = _deploy_sf(tmp_path, agent, svc, HWAX_DELIB_WAIT_S="2")
    assert _events(agent) == ["sync-from-drive.sh", "POST on", "POST off"], (_events(agent), out)
    line = next(ln for ln in ledger.splitlines() if ln.startswith("signalforge 재기동 건너뜀"))
    assert "심의 1건 진행 중, 0건 대기" in line and "VOC 도구 호출" in line and "DB 병합도 하지 않았다" in line and "AGENT_RESTART_FORCE=1" in line, line
    assert "OK:signalforge up" not in out and "SKIP:" not in out and failed == "", out
    assert _gate_state(tmp_path) == "deferred"


def test_SignalForge_는_기다려_끝나면_멈춤_아래서_재기동한다(tmp_path, agent, svc):
    agent.update(active=[1, 1, 1, 0], queued=0)
    out, ledger, _ = _deploy_sf(tmp_path, agent, svc, HWAX_DELIB_WAIT_S="30")
    ev = _events(agent)
    assert ev[:3] == ["sync-from-drive.sh", "POST on", "down.sh"] and "up.sh" in ev and "POST off" not in ev, (ev, out)
    assert agent["posts"][0]["reason"] == "SignalForge 재기동 — 도는 심의가 끝나기를 기다린다(update-all)" and ledger == ""
    assert _gate_state(tmp_path) == "waited" and (tmp_path / "ledger.delib-pause").read_text().strip() == agent["url"]


@pytest.mark.parametrize("case", ["혼자_돈_deploy_all", "받기가_SIF_를_갈았다", "SignalForge_가_내려가_있다", "강행", "NO_RESTART"])
def test_SignalForge_도_묻지_않는_갈래(tmp_path, agent, svc, case):
    """받기가 SIF 를 갈았으면 묻지 않는다 — 떠 있는 인스턴스 밑을 이미 덮어, 기다리거나 미루면 깨진 마운트로 돈다."""
    agent.update(active=1, queued=0)
    env = {"강행": {"AGENT_RESTART_FORCE": "1"}, "NO_RESTART": {"NO_RESTART": "1"}}.get(case, {})
    out, ledger, _ = _deploy_sf(tmp_path, agent, "http://127.0.0.1:9" if case == "SignalForge_가_내려가_있다" else svc,
                                under=case != "혼자_돈_deploy_all", sif_change=case == "받기가_SIF_를_갈았다", HWAX_DELIB_WAIT_S="30", **env)
    assert agent["gets"] == 0 and agent["posts"] == [] and ledger == "", (case, agent["gets"], out)
    assert "up.sh" in _events(agent), (case, out)
    assert ("down.sh" in _events(agent)) is (case != "NO_RESTART"), (case, out)
    assert ("받기가 떠 있는 인스턴스 밑의 SIF 를 갈았다" in out) is (case == "받기가_SIF_를_갈았다"), out


def test_2장에서_쓴_기다림을_4장이_다시_쓰지_않는다(tmp_path, agent, svc):
    """한 실행 안 두 자식(deploy-all · update-sites)이 판정 파일 하나를 나눠 쓴다 — §2 에서 못 끝났으면 §4 는 다시 기다리지 않고 미룬다."""
    agent.update(active=1, queued=0)
    _deploy_sf(tmp_path, agent, svc, HWAX_DELIB_WAIT_S="2")
    r, took, ledger = _sites(tmp_path, agent, svc, "mcp-gateway agent-server", HWAX_DELIB_WAIT_S="30")
    assert [p["on"] for p in agent["posts"]] == [True, False] and took < 10, (agent["posts"], took)
    assert [ln.split("\t", 1)[0] for ln in ledger.splitlines()] == ["mcp-gateway 재기동 건너뜀", "agent-server 재기동 건너뜀"], ledger
    assert r.returncode == 3, r.stdout + r.stderr


# ── lib · 원문 — 기다릴 수 없으면 판정을 남기지 않는다 · 세 자리가 모두 문을 지난다 ────────────────────────────────
def test_기다릴_수_없으면_판정을_남기지_않아_뒤의_재기동이_다시_본다(tmp_path, agent):
    """못 넘기는 줄(멈춤 동안 빠지지 않는다)이라 곧바로 미뤘으면 기다림을 쓴 것이 아니다 — 뒤의 재기동은 그때 다시 본다."""
    agent.update(active=1, queued=2, durable=False)
    gate = tmp_path / "gate"
    r = _sh(f'set -uo pipefail\n. "{BUSY_LIB}"\nrc=0; hwax_delib_gate mcp-gateway "" update-all || rc=$?\necho "rc=$rc busy=[$HWAX_DELIB_GATE_BUSY]"',
            HWAX_AGENT_URL=agent["base"], HWAX_DELIB_GATE=str(gate), HWAX_DELIB_WAIT_S="30")
    assert "rc=3 busy=[1 2]" in r.stdout and not gate.exists() and agent["posts"] == [], r.stdout + r.stderr


def test_세_재기동_자리가_모두_한_번_기다리기를_지난다():
    import re

    case = UPDATE_SITES[UPDATE_SITES.index('  case "$name" in\n    agent-server)'):]
    case = case[:case.index("  esac\n") + 7]
    assert "mcp-gateway|signalforge-mcp)" in case and 'HWAX_DELIB_GATE:-' in case, "§4 의 둘이 update-all 아래에서 문을 지난다"
    assert re.search(r'\n    _grc=0; hwax_delib_gate "\$name" ', UPDATE_SITES), "명령 치환 없이 부른다(셸 변수를 남긴다)"
    sf = _sf_block()
    assert sf.index("hwax_delib_gate signalforge") < sf.index("hwax_restart_cycle signalforge"), "§2 SignalForge 는 내리기 전에 묻는다"
    assert "$(hwax_delib_gate" not in UPDATE_SITES + DEPLOY
    head = UA[:UA.index("set -uo pipefail")]
    assert "HWAX_DELIB_WAIT_S=600" in head and "게이트웨이" in head and "SignalForge" in head, "머리 주석이 넓힌 범위를 말한다"


def test_판정_파일은_완주_끝과_정지_경로에서_지운다():
    """장부 옆 판정 파일이 /tmp 에 남지 않게 — 완주 끝(요약 뒤)과 § 머리 정지 경로 둘 다. 비어 있으면 rm 에 빈 인자를 주지 않는다."""
    tail = UA[UA.index("hwax_skip_summary\nrm -f \"$HWAX_SKIP_LEDGER\""):]
    assert tail.split("\n")[1].startswith('rm -f "$HWAX_SKIP_LEDGER" ${HWAX_DELIB_GATE:+"$HWAX_DELIB_GATE"}'), tail[:200]
    hr = UA[UA.index("hr() {"):UA.index("ok() {")]
    stop = hr[:hr.index("exit 143")]
    assert '${HWAX_DELIB_GATE:+"$HWAX_DELIB_GATE"}' in stop.splitlines()[-1], stop[-300:]
