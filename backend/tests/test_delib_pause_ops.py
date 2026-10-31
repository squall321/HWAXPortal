# 에이전트 서버 재기동 앞의 새 심의 멈춤 · 줄을 넘기는 엔진의 재기동 판정 · 다시 선 줄 수(docs/delib-ops O1 · O2 · R2')
"""왜 — 10-22 새벽 한도 하나를 바꾸려는 재기동을 심의가 돌아 미뤘고, 사람이 비는 때를 기다리는 사이 줄 선 잡이 빈자리에 들어가
'잡아 두고 재기동' 할 때를 놓쳤다. 엔진(HWAXAgentServer)이 새 심의 멈춤(R1)과 재기동을 넘기는 줄(R2)을 갖춘 뒤로, update-sites 는 도는
심의가 있으면 멈춤을 세우고 끝나기를 기다린 뒤 재기동하고(O1), update-all 은 끝에서 그 멈춤을 내리고 다시 선 줄 수를 찍는다(O2).

lib · update-sites · update-all 의 그 구획을 **원문 그대로 떼어** 지어낸 에이전트 서버(GET /health · POST /drain)에 돌린다. 실물 9009 는 건드리지
않는다(주소는 커널이 고른 빈 포트다).
"""
import http.server
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
BUSY_LIB = LIBDIR / "delib-busy.sh"
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
LIBS = f'. "{LIBDIR}/change-detect.sh"\n. "{LIBDIR}/skip-ledger.sh"\n. "{BUSY_LIB}"\n'


@pytest.fixture()
def agent():
    """지어낸 에이전트 서버. GET /health 는 state 로 답한다 — active 는 정수 또는 차례로 꺼낼 목록(마지막 값을 되풀이),
    queued · durable · requeued, paused/by(멈춤), new(False 면 멈춤을 모르는 옛 판 — delib_paused 칸이 없다). POST /drain 은 본문을
    posts 에 적고 drain_mode 로 답한다 — ok(200 · 멈춤 상태를 바꾼다) · owned(409 다른 주체) · held(409 고정) · bad(422)."""
    st = {"active": 0, "queued": 0, "durable": True, "requeued": 0, "paused": False, "by": None, "new": True,
          "drain_mode": "ok", "posts": [], "gets": 0}

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
            h = {"status": "ok", "delib_active": a, "delib_queued": st["queued"]}
            if st["new"]:
                h.update(delib_paused=st["paused"], delib_queue_durable=st["durable"], delib_requeued=st["requeued"],
                         delib_pause={"on": st["paused"], "by": st["by"], "scope": "delib" if st["paused"] else None})
            self._send(200, h)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            st["posts"].append(body)
            mode = st["drain_mode"]
            if mode == "owned":
                return self._send(409, {"code": "drain_owned", "drain": {"by": "운영", "hold": False, "scope": "delib"}})
            if mode == "held":
                return self._send(409, {"code": "drain_held", "drain": {"by": "운영", "hold": True, "scope": "delib"}})
            if mode == "bad":
                return self._send(422, {"code": "bad_request", "message": "scope 는 all·panels 가운데 하나다"})
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


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120,
                          env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), **env})


def _lib(call: str, **env) -> tuple[int, str]:
    r = _sh(f'set -uo pipefail\n. "{BUSY_LIB}"\nout="$({call})"; echo "rc=$?"; echo "out=[$out]"', **env)
    assert not r.stderr, r.stderr
    lines = r.stdout.strip().splitlines()
    return int(lines[-2][3:]), "\n".join(lines[-1:])[5:-1]


# ── R2' 줄을 넘기는 엔진이면 줄 선 수는 막지 않는다 ─────────────────────────────────────────────
@pytest.mark.parametrize("active,queued,durable,want", [
    (0, 3, True, (1, "")),               # 줄만 서 있고 넘긴다 — 재기동해도 된다
    (1, 3, True, (0, "1 3")),            # 도는 것이 있다 — 막는다(수는 둘 다 찍는다)
    (0, 3, False, (0, "0 3")),           # 못 넘기는 줄(하나라도 시작 인자 파일이 없다) — 종전대로 막는다
    (0, 3, "true", (0, "0 3")),          # 모양이 다르면 모르는 것이다 — 넘긴다고 읽지 않는다
])
def test_줄을_넘기는_엔진이면_줄_선_수로는_막지_않는다(agent, active, queued, durable, want):
    agent.update(active=active, queued=queued, durable=durable)
    assert _lib(f'hwax_delib_busy "{agent["url"]}"') == want


# ── lib — 멈춤 세우기 · 내리기 ───────────────────────────────────────────────────────────────
def test_멈춤을_세우고_내린다(agent):
    rc, out = _lib(f'hwax_delib_pause on "{agent["url"]}" update-all 2400 "재기동"')
    assert rc == 0 and "새 심의 멈춤 on(by update-all" in out, out
    assert agent["posts"][-1] == {"on": True, "scope": "delib", "by": "update-all", "ttl_s": 2400, "reason": "재기동"}
    assert _lib(f'hwax_delib_pause_state "{agent["url"]}"') == (0, "1 update-all")
    rc, out = _lib(f'hwax_delib_pause off "{agent["url"]}" update-all')
    assert rc == 0 and agent["posts"][-1] == {"on": False, "scope": "delib", "by": "update-all"}, out
    assert _lib(f'hwax_delib_pause_state "{agent["url"]}"') == (0, "0 ")


@pytest.mark.parametrize("mode,want_rc", [("owned", 7), ("held", 5), ("bad", 6)])
def test_남의_멈춤과_거절을_가른다(agent, mode, want_rc):
    agent["drain_mode"] = mode
    rc, out = _lib(f'hwax_delib_pause on "{agent["url"]}" update-all')
    assert rc == want_rc, (rc, out)


def test_멈춤을_모르는_옛_엔진에는_보내지_않는다(agent):
    """옛 엔진의 /drain 은 scope 를 보지 않는다 — {on:false, scope:"delib", by:"update-all"} 을 보내면 update-all 이 세운 카드 대조
    깃발을 내린다. 묻기만 하고 보내지 않는다."""
    agent["new"] = False
    for op in ("on", "off"):
        rc, out = _lib(f'hwax_delib_pause {op} "{agent["url"]}" update-all')
        assert rc == 3 and "옛 판" in out, (op, rc, out)
    assert agent["posts"] == [], "옛 엔진에 scope delib 을 보냈다 — 카드 대조 깃발을 내린다"


def test_내려간_서버는_2다():
    assert _lib('hwax_delib_pause on "http://127.0.0.1:9/health" update-all')[0] == 2


def test_수명은_엔진의_상한_안이다(agent):
    for ttl, want in (("abc", 1800), ("0", 1800), ("99999", 21600)):
        _lib(f'hwax_delib_pause on "{agent["url"]}" u {ttl}')
        assert agent["posts"][-1]["ttl_s"] == want, ttl


# ── lib — 도는 심의 기다리기 ─────────────────────────────────────────────────────────────────
def test_도는_심의가_끝나면_기다리기를_멈춘다(agent):
    agent["active"] = [2, 1, 0]
    rc, out = _lib(f'hwax_delib_wait "{agent["url"]}" 30', HWAX_DELIB_WAIT_POLL_S="1")
    assert rc == 0 and agent["gets"] == 3, (rc, out, agent["gets"])


def test_시간이_다_되면_마지막_수를_찍고_1(agent):
    agent["active"] = 2
    rc, out = _lib(f'hwax_delib_wait "{agent["url"]}" 2', HWAX_DELIB_WAIT_POLL_S="1")
    assert (rc, out) == (1, "2 0")


# ── O1 update-sites — 재기동할 에이전트 서버에 도는 심의가 있으면 멈추고 기다린다 ──────────────────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    return UPDATE_SITES[i:UPDATE_SITES.index("# 1) 포털 먼저", i)]


def _restart(tmp_path: Path, url: str, tail: str = "", **env):
    """restart_svc agent-server 를 대역 services.sh 로 돌린다(필요하면 뒤에 tail 을 잇는다) → (화면, services.sh 가 받은 호출, 장부)."""
    log = tmp_path / "svc.log"; st = tmp_path / "state"; st.mkdir(exist_ok=True); ledger = tmp_path / "ledger"
    log.unlink(missing_ok=True); ledger.write_text("")
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                   f'case "$1" in update) echo "  · x  updated: abc → def";; fp) echo f-new;; status) echo "  ✓ up x";;\n'
                   f'  health) echo {url};; enabled) exit 0;; esac\nexit 0\n')
    svc.chmod(0o755)
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}export HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1 '
              f'HWAX_SKIP_LEDGER="{ledger}"\nshow_cause() {{ :; }}\n{_restart_svc_block()}\n'
              f'restart_svc agent-server; echo "rc=$?"; echo "DEFERRED=[$DEFERRED_RESTART] RAISED=[${{HWAX_DELIB_PAUSE_RAISED:-0}}]"\n{tail}')
    r = _sh(script, HWAX_DELIB_WAIT_POLL_S="1", **env)
    return r.stdout + r.stderr, (log.read_text().splitlines() if log.exists() else []), ledger.read_text()


def test_도는_심의가_끝나기를_멈춘_채_기다린_뒤_재기동한다(tmp_path, agent):
    """**이 시험이 O1 의 이유다** — 곧바로 미루지 않는다. 멈춤을 세우고(줄 선 것은 다시 서니 세지 않는다) 끝나면 재기동한다."""
    agent.update(active=[2, 2, 1, 0], queued=3, durable=True)
    out, calls, ledger = _restart(tmp_path, agent["url"], HWAX_DELIB_WAIT_S="30")
    assert agent["posts"][0] == {"on": True, "scope": "delib", "by": "update-sites", "ttl_s": 1830,
                                 "reason": "에이전트 서버 재기동 — 도는 심의가 끝나기를 기다린다(update-sites)"}, agent["posts"]
    assert "down agent-server" in calls and "up agent-server" in calls, (calls, out)
    assert "도는 심의가 끝났다" in out and "DEFERRED=[]" in out and ledger == "", out
    assert "RAISED=[1]" in out and len(agent["posts"]) == 1, "재기동 직후 멈춤을 내렸다 — 내리는 것은 실행의 끝이다"


def test_혼자_돈_update_sites_는_끝에서_내리고_update_all_아래면_남겨_둔다(tmp_path, agent):
    tail = '[ "$DELIB_PAUSE_BY" = update-all ] || delib_pause_lower\necho "END"\n'
    assert tail.split("\n")[0] in UPDATE_SITES, "update-sites 의 끝맺음 줄이 바뀌었다 — 이 시험의 tail 을 맞춘다"
    agent.update(active=[1, 0], queued=0)
    out, _, _ = _restart(tmp_path, agent["url"], tail=tail, HWAX_DELIB_WAIT_S="30")
    assert agent["posts"][-1] == {"on": False, "scope": "delib", "by": "update-sites"} and "멈춤을 내렸다" in out, out
    agent.update(active=[1, 0], posts=[])
    under = tmp_path / "under"; under.mkdir()
    out, _, _ = _restart(under, agent["url"], tail=tail, HWAX_DELIB_WAIT_S="30", HWAX_DELIB_PAUSE_BY="update-all")
    assert [p["on"] for p in agent["posts"]] == [True] and agent["posts"][0]["by"] == "update-all", agent["posts"]


def test_update_all_아래서_세운_멈춤은_표지로_넘긴다(tmp_path, agent):
    agent.update(active=[1, 0], queued=0)
    mark = tmp_path / "ledger.delib-pause"
    _restart(tmp_path, agent["url"], HWAX_DELIB_WAIT_S="30", HWAX_DELIB_PAUSE_BY="update-all", HWAX_DELIB_PAUSE_MARK=str(mark))
    assert mark.read_text().strip() == agent["url"], "update-all 끝맺음이 내릴 멈춤의 표지를 남기지 않았다"


def test_못_기다리면_종전대로_미루고_멈춤은_그_자리에서_내린다(tmp_path, agent):
    agent.update(active=2, queued=1, durable=True)
    mark = tmp_path / "ledger.delib-pause"
    out, calls, ledger = _restart(tmp_path, agent["url"], HWAX_DELIB_WAIT_S="2", HWAX_DELIB_PAUSE_BY="update-all",
                                  HWAX_DELIB_PAUSE_MARK=str(mark))
    assert not mark.exists(), "그 자리에서 내린 멈춤의 표지가 남았다 — 끝맺음이 남의 멈춤을 찾아 나선다"
    assert "down agent-server" not in calls and "DEFERRED=[ agent-server]" in out, (calls, out)
    assert "agent-server 재기동 건너뜀" in ledger and "2초 안에 끝나지 않았다" in out
    assert [p["on"] for p in agent["posts"]] == [True, False], "미뤘는데 멈춤을 남겼다 — 이번에 재기동하지 않으니 새 심의를 막을 까닭이 없다"
    assert "RAISED=[0]" in out


@pytest.mark.parametrize("case", ["wait0", "queue_not_durable", "old_engine", "old_engine_no_queue"])
def test_기다릴_수_없으면_멈추지_않고_종전대로_곧바로_미룬다(tmp_path, agent, case):
    """기다림 0 · 못 넘기는 줄(기다려도 빠지지 않는다 — 멈춤 동안 줄은 그대로 선다) · 멈춤을 모르는 엔진(줄이 비어 기다릴 수 있어 보여도)."""
    agent.update(active=1, queued=0 if case == "old_engine_no_queue" else 2, durable=case != "queue_not_durable",
                 new=not case.startswith("old_engine"))
    out, calls, ledger = _restart(tmp_path, agent["url"], HWAX_DELIB_WAIT_S="0" if case == "wait0" else "30")
    assert agent["posts"] == [], (case, agent["posts"])
    assert "down agent-server" not in calls and "agent-server 재기동 건너뜀" in ledger, (case, out)


def test_남의_멈춤이_서_있으면_그_아래서_기다리기만_하고_내리지_않는다(tmp_path, agent):
    agent.update(active=[1, 0], queued=0, drain_mode="owned")
    tail = '[ "$DELIB_PAUSE_BY" = update-all ] || delib_pause_lower\n'
    out, calls, _ = _restart(tmp_path, agent["url"], tail=tail, HWAX_DELIB_WAIT_S="30")
    assert "down agent-server" in calls and "다른 주체가 세운 새 심의 멈춤" in out, (calls, out)
    assert [p["on"] for p in agent["posts"]] == [True], "남의 멈춤을 내렸다"


# ── update-all — 끝에서 제 멈춤을 내린다 · 다시 선 줄 수(O2) ────────────────────────────────────────
def _finish_fn() -> str:
    i = UA.index("_hwax_delib_pause_finish() {")
    return UA[i:UA.index("\n}\n", i) + 3]


def _finish(tmp_path: Path, agent, mark: bool = True) -> subprocess.CompletedProcess:
    m = tmp_path / "ledger.delib-pause"
    if mark:
        m.write_text(agent["url"] + "\n")                # update-sites 가 멈춤을 세우며 남긴 표지(그 주소)
    # 표지가 있으면 그 주소를 쓴다(기본 주소는 죽은 곳 — 표지를 안 읽으면 드러난다). 표지가 없으면 기본 주소를 이 서버로 둔다 — 묻지 말아야
    # 하는데 물으면 여기 닿아 드러난다.
    r = _sh(f'set -uo pipefail\n. "{BUSY_LIB}"\nbad() {{ echo "BAD:$*"; }}\n{_finish_fn()}\n_hwax_delib_pause_finish; echo "rc=$?"',
            HWAX_AGENT_URL="http://127.0.0.1:9" if mark else agent["base"], HWAX_DELIB_PAUSE_MARK=str(m))
    assert "rc=0" in r.stdout and not m.exists(), r.stdout + r.stderr
    return r


@pytest.mark.parametrize("paused,by,want_off", [(True, "update-all", True), (True, "운영", False), (False, None, False)])
def test_update_all_은_끝에서_제_멈춤만_내린다(tmp_path, agent, paused, by, want_off):
    agent.update(paused=paused, by=by)
    r = _finish(tmp_path, agent)
    assert (agent["posts"] == [{"on": False, "scope": "delib", "by": "update-all"}]) is want_off, agent["posts"]
    assert ("멈춤을 내렸다" in r.stdout) is want_off


def test_표지가_없으면_묻지도_않는다(tmp_path, agent):
    """update-all 은 매번 끝맺음을 부른다 — 이번 실행이 멈춤을 세우지 않았으면 엔진을 두드릴 까닭이 없다(비우기 시험이 /health 수를 센다)."""
    agent.update(paused=True, by="update-all")
    _finish(tmp_path, agent, mark=False)
    assert agent["gets"] == 0 and agent["posts"] == []


def test_update_all_끝맺음은_옛_엔진에_보내지_않는다(tmp_path, agent):
    agent.update(new=False)
    _finish(tmp_path, agent)
    assert agent["posts"] == []


def test_완주_끝과_정지_경로_모두_멈춤을_내린다():
    assert UA.count("_hwax_delib_pause_finish") >= 3, "정의 · hr() 정지 경로 · 완주 끝"
    hr = UA[UA.index("hr() {"):UA.index("ok() {")]
    assert "_hwax_delib_pause_finish" in hr, "§ 머리에서 멈춘 실행이 멈춤을 남긴다(수명까지 새 심의를 거절한다)"


def test_리스너_판정은_듣는_프로세스를_가르고_없으면_물음표다(agent):
    rc, out = _lib(f'hwax_agent_ident "{agent["url"]}"')
    pid, _, start = out.partition(":")
    assert rc == 0 and pid == str(os.getpid()) and start.isdigit(), (out, os.getpid())     # 지어낸 서버는 이 시험 프로세스 안에서 듣는다
    assert _lib('hwax_agent_ident "http://127.0.0.1:9/health"') == (0, "?")
    # 명령 치환 안에서는 bash 가 set -e 를 물려주지 않는다 — 그대로(치환 없이) 불러야 '듣는 것이 없는 포트' 에서 끝나는지 드러난다
    r = _sh(f'set -euo pipefail\n. "{BUSY_LIB}"\nhwax_agent_ident "http://127.0.0.1:9/health"\necho "after"')
    assert r.returncode == 0 and r.stdout.split() == ["?", "after"], ("set -e 로 부르는 쪽이 듣는 것이 없는 포트에서 끝났다", r.stdout, r.stderr)


def test_다시_선_줄_수는_옛_엔진이면_3(agent):
    agent["requeued"] = 4
    assert _lib(f'hwax_delib_requeued "{agent["url"]}"') == (0, "4 0")
    agent["new"] = False
    assert _lib(f'hwax_delib_requeued "{agent["url"]}"')[0] == 3


def test_4장_블록은_lib_없이도_조용히_지나간다(tmp_path):
    """§4 를 떼어 도는 다른 시험(LLM 풀)의 사본은 delib-busy.sh 를 읽지 않는다 — O2 가 'command not found' 를 내지 않고 건너뛴다."""
    repo = tmp_path / "repo"; (repo / "infra/scripts").mkdir(parents=True)
    (repo / "infra/scripts/update-sites.sh").write_text("#!/usr/bin/env bash\nexit 0\n"); (repo / "infra/scripts/update-sites.sh").chmod(0o755)
    r = _sh(f'set -uo pipefail\nfail() {{ echo "FAIL:$*"; }}\nSELF_REPO="{repo}"\n{_o2_block()}\necho END',
            HWAX_SKIP_LEDGER=str(tmp_path / "ledger"))
    assert r.stderr == "" and "END" in r.stdout and "다시 선 줄" not in r.stdout, r.stdout + r.stderr
    assert "127.0.0.1:9009" not in _o2_block(), "§4 블록에 실물 주소가 박혔다 — 떼어 도는 하네스가 실물을 두드린다(기본 주소는 lib 에)"


def _o2_block() -> str:
    i = UA.index('_ag0=""; command -v hwax_agent_ident')
    j = UA.index("\n# 1i 의 뒤처리", i)
    return UA[i:j]


def _head_export() -> str:
    """멈춤 주인 · 표지 · 판정 파일을 물려주는 머리의 export 한 줄(10-31 A25 — §2 의 SignalForge 도 쓰게 §4 에서 머리로 옮겼다)."""
    return next(ln for ln in UA.splitlines() if ln.startswith("export HWAX_DELIB_GATE="))


def test_멈춤_주인과_표지는_2장_앞에서_물려준다():
    """§2 의 SignalForge 가 세운 멈춤도 끝맺음이 내려야 한다 — 표지가 §4 에서야 정해지면 §2 가 세운 멈춤은 수명(기다림 + 30분)까지 새 심의를 막는다."""
    line = _head_export()
    assert "HWAX_DELIB_PAUSE_BY=update-all" in line and 'HWAX_DELIB_PAUSE_MARK="${HWAX_SKIP_LEDGER}.delib-pause"' in line, line
    at = UA.index(line)
    assert UA.index('HWAX_SKIP_LEDGER="$(mktemp)"; export HWAX_SKIP_LEDGER') < at, "장부 옆 파일이다 — 장부를 만든 뒤에 정한다"
    assert at < UA.index('"$SELF_REPO/infra/scripts/deploy-all-from-drive.sh"') < UA.index(
        '"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server')
    code = [ln for ln in UA.splitlines() if not ln.lstrip().startswith("#")]
    assert sum("HWAX_DELIB_PAUSE_BY=" in ln for ln in code) == 1, "주인을 두 곳에서 정하면 한쪽만 고쳐진다"


@pytest.mark.parametrize("restarted,requeued,paused,want", [
    (True, 3, True, "다시 선 줄 3건(처음 줄 선 차례 그대로 · 새 심의 멈춤이 풀리면 차례로 든다)"),
    (True, 2, False, "다시 선 줄 2건(처음 줄 선 차례 그대로 · 자리가 나는 대로 든다)"),
    (True, 0, False, "다시 선 줄 0건"),
    (False, 3, False, None),                                     # 이번에 다시 뜨지 않았다 — 그 수는 앞 기동의 것이다
])
def test_에이전트가_다시_떴으면_다시_선_줄_수를_찍는다(tmp_path, agent, restarted, requeued, paused, want):
    agent.update(requeued=requeued, paused=paused)
    repo = tmp_path / "repo"; (repo / "infra/scripts").mkdir(parents=True)
    us = repo / "infra/scripts/update-sites.sh"
    us.write_text(f'#!/usr/bin/env bash\necho "PAUSE_BY=$HWAX_DELIB_PAUSE_BY"\n'
                  f'{"echo after > " + str(tmp_path / "flip") if restarted else ":"}\nexit 0\n')
    us.chmod(0o755)
    # 리스너 판정만 대역 — update-sites 가 다시 띄웠으면(flip) 다른 pid 를 답한다. 다시 선 줄 수는 진짜 lib 가 지어낸 서버에 묻는다.
    stub = f'hwax_agent_ident() {{ if [ -f "{tmp_path / "flip"}" ]; then echo "222:900"; else echo "111:100"; fi; }}\n'
    r = _sh(f'set -uo pipefail\n. "{BUSY_LIB}"\n{stub}fail() {{ echo "FAIL:$*"; }}\nSELF_REPO="{repo}"\n{_head_export()}\n{_o2_block()}\necho END',
            HWAX_AGENT_URL=agent["base"], HWAX_SKIP_LEDGER=str(tmp_path / "ledger"))
    assert not r.stderr and "PAUSE_BY=update-all" in r.stdout and "END" in r.stdout, r.stdout + r.stderr
    if want is None:
        assert "다시 선 줄" not in r.stdout, r.stdout
    else:
        assert f"에이전트 서버가 다시 떴다 — 재기동을 넘겨 {want}" in r.stdout, r.stdout
