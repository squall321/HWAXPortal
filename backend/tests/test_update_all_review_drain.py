# update-all 1h 리스크 검토 비우기 — 깃발을 §2 앞에 세우고 § 머리마다 늘리고 끝에서 장부대로 정리하는지, 남의 깃발·옛 엔진·거절을 가르는지
"""왜 — 카드 대조는 delib_active 에 들지 않아 재기동을 막지 않고, 끊긴 호출은 리스크 앱이 차감 없이 다시 낸다. 그래도 그 LLM 시간은
버려진다. 비우기는 update-all 동안 새 카드 대조·새 패널을 멈추고, 도는 것을 잠깐 기다리고, 재기동을 미뤘으면 심의가 끝난 뒤 다음 배포
창을 연다(docs/risk-review-redesign/reference/m3-engine-ops.md '비우기 의미'·P3-2, M3.md 4.7).

짝 — 에이전트 서버의 POST/GET /drain 과 /health 의 review_active·draining·drain·load.chat(HWAXAgentServer review_gate.DrainState).
여기서는 그 규칙을 지어낸 서버로 대신하고(빈 포트), update-all 의 구획을 **원문 그대로** 떼어 임시 포털 리포에서 돌린다.
⚠ 실물을 건드리면 안 된다 — 상대경로 하네스가 실 apptainer 로 dev nginx 를 내린 사고가 있었다(2026-09-28).
  · 경로는 전부 절대경로다. 하네스는 임시 디렉터리에서 돌고 apptainer·systemctl 이 대역으로 잡히는지 먼저 확인한다(아니면 97).
  · lib 는 사본을 소싱한다 — 기본 주소(127.0.0.1:9009)를 지어낸 서버로 바꾼 사본이다. 돌리는 본문에 실물 주소가 남으면 시험이 그
    자리에서 실패한다(P-16). 환경변수 HWAX_AGENT_URL 이 새지 않아도 실물 엔진에 깃발이 서지 않는다.
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
SCRIPTS = ROOT / "infra/scripts"
LIBDIR = SCRIPTS / "lib"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
DRAIN_LIB = (LIBDIR / "review-drain.sh").read_text(encoding="utf-8")
WRAPPER = (SCRIPTS / "review-drain.sh").read_text(encoding="utf-8")
REAL = "http://127.0.0.1:9009"
DEAD = "http://127.0.0.1:9"
FORBIDDEN = ("127.0.0.1:9009", "127.0.0.1:8723", "127.0.0.1:9110")
TTL_CAP = 21600
DEFERRED_NAMES = ("포털·nginx 재기동 건너뜀", "nginx 재기동 건너뜀", "heax 재기동 건너뜀", "agent-server 재기동 건너뜀",
                  "게이트웨이 재프로비저닝 건너뜀")


# ── 지어낸 에이전트 서버 — /health · GET/POST /drain ───────────────────────────────────────────────
def _view(flag: dict | None) -> dict:
    if flag is None:
        return {"on": False, "scope": None, "until": None, "until_idle": None, "hold": False, "by": None, "reason": None,
                "set_at": None}
    return {"on": True, **{k: flag.get(k) for k in ("scope", "until", "until_idle", "hold", "by", "reason", "set_at")}}


@pytest.fixture()
def agent():
    """엔진 규칙(review_gate.DrainState + 단계 B 뒤의 계약)을 줄여 흉내 낸다 — 사람의 고정은 hold 아닌 요청에 409 drain_held,
    살아 있는 깃발의 주인이 아닌 by 의 hold 아닌 요청은 409 drain_owned(본문은 drain 없이 owner·scope·until — 두 모양을 다 읽는지 본다),
    요청 하나의 ttl_s 는 21,600 까지(넘으면 422). state['review_seq'] 는 /health 마다 앞에서 하나씩 꺼낸다(비면 마지막 값).
    state['old'] = 옛 엔진(/drain 404, /health 에 review_active·drain 없음) · state['force_status'] = /drain 이 그 상태로 답한다.
    고정 아닌 깃발은 until 이 지나면 요청마다 풀린다(state['expired'] 가 센다). state['off_after_health'] = N 이면 N 번째 /health 에서
    깃발을 내린다(1h 의 기다림 중에 사람이 내린 것)."""
    state = {"flag": None, "review": 0, "review_seq": [], "delib": (0, 0), "old": False, "force_status": None,
             "slow": False, "calls": [], "delay": [], "expired": 0, "off_after_health": None, "health_n": 0}
    lock = threading.Lock()

    def _expire():
        f = state["flag"]
        if f and not f.get("hold") and f.get("until_idle") is None and f.get("until") is not None and f["until"] <= time.time():
            state["flag"] = None; state["expired"] += 1

    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code: int, body):
            raw = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("content-type", "application/json"); self.end_headers()
            self.wfile.write(raw)

        def _counts(self) -> dict:
            return {"review_active": state["review"], "delib_active": state["delib"][0], "delib_queued": state["delib"][1]}

        def do_GET(self):
            if state["delay"]:
                time.sleep(state["delay"].pop(0))
            with lock:
                _expire()
                state["calls"].append(("GET", self.path, None))
                if self.path == "/health":
                    if state["review_seq"]:
                        state["review"] = state["review_seq"].pop(0)
                    state["health_n"] += 1
                    if state["off_after_health"] == state["health_n"]:
                        state["flag"] = None
                    a, q = state["delib"]
                    if state["old"]:
                        return self._send(200, {"status": "ok", "delib_active": a, "delib_queued": q})
                    f = state["flag"]
                    idle = {"n": 30, "p50": 2000, "p95": 5000}
                    rev = {"n": 30, "p50": 5000 if state["slow"] else 2500, "p95": 9000}
                    return self._send(200, {"status": "ok", "delib_active": a, "delib_queued": q, "review_active": state["review"],
                                            "draining": bool(f and f["scope"] == "all"), "drain": _view(f),
                                            "capabilities": ["card_review", "drain"], "card_review": {"limit": 8},
                                            "load": {"chat": {"ttft_ms": {"idle": idle, "review": rev}, "slow": state["slow"],
                                                              "slow_since": "2026-10-14T01:00:00" if state["slow"] else None}}})
                if self.path == "/drain":
                    if state["old"]:
                        return self._send(404, {"detail": "Not Found"})
                    if state["force_status"]:
                        return self._send(state["force_status"], {"code": "drain_unavailable", "message": "지어낸 거절"})
                    return self._send(200, {**_view(state["flag"]), **self._counts()})
                return self._send(404, {"detail": "Not Found"})

        def do_POST(self):
            if state["delay"]:
                time.sleep(state["delay"].pop(0))
            body = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)) or b"{}")
            with lock:
                _expire()
                state["calls"].append(("POST", self.path, body))
                if self.path != "/drain" or state["old"]:
                    return self._send(404, {"detail": "Not Found"})
                if state["force_status"]:
                    code = {422: "bad_request", 503: "drain_unavailable"}.get(state["force_status"], "x")
                    return self._send(state["force_status"], {"code": code, "message": "지어낸 거절"})
                cur, now = state["flag"], time.time()
                if body["on"]:
                    hold = bool(body.get("hold"))
                    if cur and cur["hold"] and not hold:
                        return self._send(409, {"code": "drain_held", "message": "사람이 고정했다", "drain": _view(cur)})
                    if cur and cur["by"] != body["by"] and not hold:
                        return self._send(409, {"code": "drain_owned", "message": "주인이 아니다", "owner": cur["by"],
                                                "scope": cur["scope"], "until": cur.get("until")})
                    ttl = body.get("ttl_s")
                    if ttl is not None and not hold and ttl > TTL_CAP:
                        return self._send(422, {"code": "bad_request", "message": "ttl_s 는 21600초까지다"})
                    new = dict(cur or {"set_at": now, "until": None, "until_idle": None})
                    new.update(scope=body["scope"], by=body["by"], reason=body.get("reason"), hold=hold or bool((cur or {}).get("hold")))
                    if ttl is not None:
                        new["until"] = max(new.get("until") or 0, now + ttl)
                    if body.get("until_idle"):
                        new["until_idle"] = {**body["until_idle"], "idle_since": None, "max_until": now + body["until_idle"]["max_s"]}
                    state["flag"] = new
                    return self._send(200, {**_view(new), **self._counts()})
                if cur is None:
                    return self._send(200, {**_view(None), **self._counts()})
                if (cur["hold"] or cur["by"] != body.get("by")) and not body.get("force"):
                    return self._send(409, {"code": "drain_held", "message": "남의 깃발", "drain": _view(cur)})
                state["flag"] = None
                return self._send(200, {**_view(None), **self._counts()})

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{srv.server_address[1]}"
    yield state
    srv.shutdown(); srv.server_close()


def _posts(agent) -> list[dict]:
    return [b for m, p, b in agent["calls"] if m == "POST"]


def _last(agent) -> dict:
    posts = _posts(agent)
    assert posts, "POST /drain 이 한 번도 오지 않았다"
    return posts[-1]


def _at(text: str, needle: str) -> int:
    """자리 — 없으면 단언으로 실패한다(str.index 의 ValueError 로 붉어지지 않게)."""
    assert needle in text, f"`{needle}` 가 없다"
    return text.index(needle)


def _health_hits(agent) -> int:
    return sum(1 for m, p, _ in agent["calls"] if m == "GET" and p == "/health")


def _line(out: str, *needles: str) -> str:
    """needles 를 전부 품은 첫 줄 — 없으면 단언으로 실패한다(StopIteration 같은 우연한 예외로 붉어지지 않게)."""
    for ln in out.splitlines():
        if all(x in ln for x in needles):
            return ln
    raise AssertionError(f"{needles} 를 품은 줄이 없다:\n{out}")


ON = {"on": True, "scope": "all", "ttl_s": 1800, "by": "update-all"}
OFF = {"on": False, "by": "update-all"}


def _strip_reason(b: dict) -> dict:
    return {k: v for k, v in b.items() if k != "reason"}


# ── 임시 포털 리포 — lib 사본(기본 주소를 바꾼 것)과 대역 ─────────────────────────────────────────────
def _portal(tmp_path: Path, default_url: str) -> Path:
    repo = tmp_path / "portal"; lib = repo / "infra/scripts/lib"; lib.mkdir(parents=True, exist_ok=True)
    assert REAL in DRAIN_LIB, "lib 의 기본 주소가 바뀌었다 — 하네스가 바꿔 끼울 자리를 다시 찾는다"
    (lib / "review-drain.sh").write_text(DRAIN_LIB.replace(REAL, default_url), encoding="utf-8")
    for name in ("skip-ledger.sh", "delib-busy.sh", "llm-pool.sh"):   # update-all 머리가 적재하는 lib 전부(llm-pool 은 정의만 — 1i 는 아래에서 뺀다)
        (lib / name).write_text((LIBDIR / name).read_text(encoding="utf-8").replace(REAL, default_url), encoding="utf-8")
    (repo / "infra/scripts/review-drain.sh").write_text(WRAPPER.replace(REAL, default_url), encoding="utf-8")
    (repo / "infra/scripts/review-drain.sh").chmod(0o755)
    for f in lib.iterdir():
        assert not any(x in f.read_text(encoding="utf-8") for x in FORBIDDEN), f"{f.name} 사본에 실물 주소가 남았다"
    return repo


def _stubbin(tmp_path: Path) -> Path:
    stub = tmp_path / "bin"; stub.mkdir(exist_ok=True)
    for name in ("apptainer", "systemctl"):
        (stub / name).write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "{tmp_path}/real-calls"\nexit 97\n')
        (stub / name).chmod(0o755)
    return stub


def _sh(script: str, tmp_path: Path, **env) -> subprocess.CompletedProcess:
    stub = _stubbin(tmp_path)
    base = {"PATH": f'{stub}:{os.environ["PATH"]}', "HOME": os.environ.get("HOME", "/tmp"), "TMPDIR": str(tmp_path),
            "LANG": "C.UTF-8"}
    guard = (f'[ "$(command -v apptainer)" = "{stub}/apptainer" ] && [ "$(command -v systemctl)" = "{stub}/systemctl" ] '
             '|| { echo "HARNESS: 실물 명령이 대역이 아니다" >&2; exit 97; }\n')
    return subprocess.run(["bash", "-c", guard + script], capture_output=True, text=True, timeout=120, env={**base, **env})


def _region(start: str, end: str) -> str:
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


def _head() -> str:
    """hr·ok·bad·fail 와 lib 적재·_hwax_drain_finish — hr() 머리부터 http_code 앞까지(lib 는 $SELF_REPO 사본을 소싱한다)."""
    return _region('hr() { if [ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ]; then', "# HTTP 코드 프로브")


def _drain_and_deploy() -> str:
    """1h 와 §2(deploy-all 부르기와 rc 판정) — 1h 머리부터 §3 주석 앞까지. 사이의 1i(LLM 라우터 — 풀이 없으면 ○ 한 줄)는 뺀다 —
    그 구획은 test_llm_pool_update_all 이 따로 돌린다. 여기 두면 이 파일의 '○·⚠ 가 없다' 단언이 비우기와 무관한 줄에 걸린다."""
    return _region("# ── 1h) 리스크 검토 비우기", "# ── 1i) LLM 라우터") + _region("# ── 2) 전 서비스 배포", "# ── 3) AIDataHub 데이터 동기화")


def _tail() -> str:
    return UA[UA.index('[ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ] && echo "  · 종료 요청이 있었지만'):]


def _ua(tmp_path: Path, agent, *, deploy_rc: int = 0, deploy_ledger: tuple[str, ...] = (),
        sections: tuple[tuple[str, str], ...] | None = None, url: str | None = None, **env):
    """update-all 의 머리(hr·lib)·1h·§2·대역 §들·끝을 이어 돌린다 → (rc, 화면, §2 동안 본 깃발).
    deploy_ledger = deploy-all 대역이 장부에 적는 ○ 이름들 · sections = (§ 머리, 그 § 에서 도는 셸 한 줄)."""
    sections = SECTIONS if sections is None else sections
    repo = _portal(tmp_path, agent["url"])
    seen = tmp_path / "flag-during-deploy"
    lines = "".join(f'hwax_skip "{n}" "심의 1건 진행 중, 0건 대기 — 지어낸 미룸" "심의가 끝난 뒤 update-all 을 다시 돌린다"\n'
                    for n in deploy_ledger)
    da = repo / "infra/scripts/deploy-all-from-drive.sh"
    da.write_text(f'#!/usr/bin/env bash\ncurl -s --noproxy "*" -m 4 "$HWAX_AGENT_URL/drain" > "{seen}"\n'
                  f'. "{repo}/infra/scripts/lib/skip-ledger.sh"\n{lines}exit {deploy_rc}\n')
    da.chmod(0o755)
    stubs = "".join(f'hr "{h}"\n{act}\n' for h, act in sections)
    body = f'SELF_REPO="{repo}"\n{_head()}\n{_drain_and_deploy()}\n{stubs}FAIL="${{FAIL:-0}}"\n{_tail()}'
    for x in FORBIDDEN:
        assert x not in body, f"돌리는 본문에 실물 주소 {x} 가 남았다 — 하네스가 떠 있는 서비스를 두드린다(P-16)"
    script = f'set -uo pipefail\ncd "{tmp_path}"\n{body}\n'
    r = _sh(script, tmp_path, HWAX_AGENT_URL=url or agent["url"], **env)
    assert r.returncode != 97, r.stdout + r.stderr
    assert not (tmp_path / "real-calls").exists(), "실물 명령이 불렸다"
    return r.returncode, r.stdout + r.stderr, (json.loads(seen.read_text()) if seen.exists() and seen.read_text() else None)


# 대역 §들 — update-all 의 §3~§7 자리(머리만 있고 하는 일은 그 § 의 셸 한 줄)
SECTIONS = (("3) 동기화", ""), ("4) update-sites", ""), ("5) 정합", ""), ("6) 헬스게이트", ""), ("7) 스모크", ""))


def _n_heads(sections) -> int:
    """1h 뒤의 § 머리 수 — §2 하나 + 대역 §들."""
    return 1 + len(sections)


# ── 셀만 도는 실행 ───────────────────────────────────────────────────────────────────────────────
def test_셀만_도는_실행은_2장_앞에_세우고_머리마다_늘리고_끝에서_내린다(tmp_path, agent):
    """**이 시험이 이 파일의 이유다** — on 이 §2 앞에 한 번(§2 동안 깃발이 scope all 로 서 있다), 수명 늘리기가 § 머리 수만큼, 끝에 off 한 번.
    심의가 없으니 '재기동 건너뜀' 줄이 없다(깃발이 재기동을 막지 않는다)."""
    rc, out, seen = _ua(tmp_path, agent)
    assert rc == 0, out
    posts = [_strip_reason(b) for b in _posts(agent)]
    assert posts == [ON] * (1 + _n_heads(SECTIONS)) + [OFF], posts
    assert seen and seen["on"] is True and seen["scope"] == "all" and seen["by"] == "update-all", seen
    assert "재기동 건너뜀" not in out and "재프로비저닝 건너뜀" not in out
    assert "· 세웠다 — 깃발 on(scope all · by update-all" in out and "깃발을 내렸다" in out
    assert agent["flag"] is None, "끝에서 내렸어야 한다"
    assert "⚠" not in out and "○" not in out, out


def test_머리마다_늘리기는_대역_머리_수를_따라간다(tmp_path, agent):
    """늘리기는 hr() 안에 있다 — § 수가 바뀌어도 머리마다 한 번이다(셈을 하드코딩한 것이 아니다)."""
    sections = (("3) a", ""), ("4) b", ""))
    rc, out, _ = _ua(tmp_path, agent, sections=sections)
    assert rc == 0, out
    assert [_strip_reason(b) for b in _posts(agent)] == [ON] * (1 + _n_heads(sections)) + [OFF]


# ── 미룬 재기동 → 새 패널만 멈추는 창 ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", DEFERRED_NAMES)
def test_재기동을_미룬_실행은_새_패널만_멈추는_창으로_끝난다(tmp_path, agent, name):
    """X2-04 의 가장 흔한 경우(포털만 미뤘고 에이전트 서버는 무변경)를 포함해 미룸 줄 다섯 이름 모두 — 끝이 off 가 아니라 until-idle 이다.
    카드 대조는 다시 받고(scope panels) 새 패널만 집지 않는다. 미룬 사실은 종료코드가 아니라 장부에서 읽는다."""
    agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=(name,))
    assert rc == 0, out
    last = _last(agent)
    assert _strip_reason(last) == {"on": True, "scope": "panels", "until_idle": {"grace_s": 1800, "max_s": 46800}, "by": "update-all"}
    assert name in last.get("reason", ""), "깃발 사유에 무엇을 미뤘는지 싣는다"
    assert OFF not in [_strip_reason(b) for b in _posts(agent)], "미룬 실행이 깃발을 내렸다 — 쟁점 패널이 새로 집힌다"
    line = _line(out, "○", "리스크 검토 비우기 유지")
    assert "도는 심의가 끝나면 30분 창이 열린다" in line, line
    summary = out[_at(out, "있는데 안 켠 것"):]
    assert "리스크 검토 비우기 유지" in summary and "update-all 을 다시 돌리면" in summary, "끝 요약에도 다시 나온다"
    assert agent["flag"]["scope"] == "panels" and agent["flag"]["until_idle"]["grace_s"] == 1800


def test_창의_길이는_손잡이를_따른다(tmp_path, agent):
    agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=("heax 재기동 건너뜀",), HWAX_DRAIN_GRACE_S="600", HWAX_DRAIN_MAX_S="7200")
    assert rc == 0
    assert _last(agent).get("until_idle") == {"grace_s": 600, "max_s": 7200}, _last(agent)
    assert "도는 심의가 끝나면 10분 창이 열린다" in out


def test_git_실패만_있는_실행은_내린다(tmp_path, agent):
    """_DA_RC=3 은 git 실패지 미룸이 아니다 — 재기동을 미룬 줄이 장부에 없으면 내린다. 다른 ○(안 켠 기능)는 미룸이 아니다."""
    rc, out, _ = _ua(tmp_path, agent, deploy_rc=3, deploy_ledger=("AIDataHub 동기화", "ste 라우트 자동 기록"))
    assert rc == 1 and "소스 갱신 실패" in out, out
    assert _strip_reason(_last(agent)) == OFF
    assert "until_idle" not in json.dumps(_posts(agent)) and agent["flag"] is None


# ── 남의 깃발(409 — 사람의 고정·다른 주인) ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("hold,kind", [(True, "사람이 고정한 깃발"), (False, "다른 주체가 세운 깃발")])
def test_남의_깃발이면_세운_것으로_치지_않고_끝에서도_건드리지_않는다(tmp_path, agent, hold, kind):
    """고친 판을 올리는 update-all 이 사람의 멈춤을 풀지 않는다(P-05). 다른 주인의 깃발도 같다 — 409 면 어느 모양이든 그 깃발을 바꾸지
    않는다. 미룬 재기동이 있어도 창으로 바꾸지 않는다(그 깃발은 우리 것이 아니다). 고정 아닌 남의 깃발이면 § 머리마다 제 깃발을 세워
    보지만(풀리면 세운다 — 아래 시험) 살아 있는 동안은 409 라 아무것도 바뀌지 않는다. 사람의 고정이면 세워 보지도 않는다."""
    flag = {"scope": "all", "by": "human:kim", "hold": hold, "until": None if hold else time.time() + 600,
            "until_idle": None, "reason": "점검", "set_at": time.time()}
    agent["flag"] = dict(flag); agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=("포털·nginx 재기동 건너뜀",))
    assert rc == 0, out
    tries = 1 if hold else 1 + _n_heads(SECTIONS)
    assert [_strip_reason(b) for b in _posts(agent)] == [ON] * tries, f"409 뒤에 내리거나 창으로 바꿨다 — {_posts(agent)}"
    line = _line(out, "○", "리스크 검토 비우기")
    assert kind in line and "건드리지 않는다" in line and "human:kim" in line, line
    assert agent["flag"] == flag, "남의 깃발이 바뀌었다"
    assert "· 세웠다 — " not in out and "⚠" not in out


def _human(body: dict) -> str:
    """대역 § 에서 사람이 review-drain.sh 로 하는 일 — POST /drain 한 번(셸 한 줄)."""
    return (f'curl -s --noproxy "*" -m 4 -X POST -H "content-type: application/json" '
            f"--data '{json.dumps(body, ensure_ascii=False)}' \"$HWAX_AGENT_URL/drain\" >/dev/null")


def _ours(agent) -> list[dict]:
    """update-all 이 보낸 것만(대역 § 의 사람 요청은 뺀다)."""
    return [_strip_reason(b) for b in _posts(agent) if b.get("by") == "update-all"]


def test_도중에_사람이_고정하면_더_늘리지_않고_끝에서도_건드리지_않는다(tmp_path, agent):
    """update-all 이 세운 깃발을 사람이 도는 중에 고정으로 바꿨다 — 다음 § 머리가 GET 으로 보고(우리 수명 안인데 남의 것) 늘리기를 멈춘다.
    끝맺음은 off 를 보내지 않는다. ○ 한 줄이 누구의 깃발인지 말한다."""
    rc, out, _ = _ua(tmp_path, agent, sections=(("3) a", _human({"on": True, "scope": "all", "hold": True, "by": "human:lee",
                                                                  "reason": "x"})), ("4) b", ""), ("5) c", "")))
    assert rc == 0, out
    assert _ours(agent) == [ON] * 3, f"고정한 뒤에도 늘리거나 내렸다 — {_ours(agent)}"
    assert agent["flag"] and agent["flag"]["hold"] is True and agent["flag"]["by"] == "human:lee"
    line = _line(out, "○", "리스크 검토 비우기")
    assert "수명 전에 다른 주체(by human:lee)의 것이 됐다" in line and "끝에서도 건드리지 않는다" in line, line
    assert "⚠" not in out


def test_마지막_절에서_사람이_고정하면_끝맺음이_내리지_않는다(tmp_path, agent):
    """뒤에 § 머리가 없으면 끝맺음이 처음 본다 — off 가 409 를 받고 내리지 않는다(○ 한 줄, ⚠ 없음)."""
    rc, out, _ = _ua(tmp_path, agent, sections=(("3) a", _human({"on": True, "scope": "all", "hold": True, "by": "human:lee",
                                                                  "reason": "x"})),))
    assert rc == 0, out
    assert _ours(agent)[-1] == OFF and agent["flag"] and agent["flag"]["by"] == "human:lee"
    line = _line(out, "○", "리스크 검토 비우기")
    assert "사람이 고정한 깃발" in line and "건드리지 않는다(내리지 않았다)" in line and "⚠" not in out, line


def test_남의_깃발이_풀리면_그_머리에서_제_깃발을_세운다(tmp_path, agent):
    """#7 — 사람이 review-drain.sh on(고정 아님)으로 세운 깃발 때문에 1h 가 409 drain_owned 를 받았다. 종전엔 그 뒤로 아무것도 안 해,
    그 깃발이 도중에 풀리면 §4 재기동 동안 카드 대조가 돌고 끝의 until-idle 도 없었다. 이제 § 머리마다 세워 보고(409 면 조용히), 그 깃발이
    없어진 머리에서 세운다(· 한 줄). 그때부터는 늘리기·끝맺음이 종전대로다. 1h 의 ○ 는 끝 요약에 다시 나오지 않는다(이제 사실이 아니다)."""
    agent["flag"] = {"scope": "all", "by": "human:lee", "hold": False, "until": time.time() + 600, "until_idle": None,
                     "reason": "점검", "set_at": time.time()}
    agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=("포털·nginx 재기동 건너뜀",),
                     sections=(("3) a", _human({"on": False, "by": "human:lee"})), ("4) b", ""), ("5) c", "")))
    assert rc == 0, out
    ours = _ours(agent)
    assert ours[:4] == [ON] * 4 and len(ours) == 6, ours       # 1h · §2 · §3 머리(409) · §4 머리(세웠다) · §5 머리(늘림) · 끝맺음
    assert ours[-1]["scope"] == "panels" and "until_idle" in ours[-1], "세운 뒤로는 끝맺음이 종전대로(미룬 재기동 → 창)"
    line = _line(out, "· 리스크 검토 비우기 — 다른 주체의 깃발이 없어져 update-all 이 깃발을 세웠다")
    assert "깃발 on(scope all · by update-all" in line, line
    assert out.count("다른 주체가 세운 깃발") == 1, "1h 의 ○ 가 끝 요약에 다시 나왔다 — 세운 뒤에는 사실이 아니다"
    assert agent["flag"]["by"] == "update-all" and agent["flag"]["scope"] == "panels"


def test_사람이_도중에_내리면_되살리지_않는다(tmp_path, agent):
    """#8 — update-all 의 깃발을 사람이 review-drain.sh off --force 로 내렸다. 종전엔 다음 § 머리의 늘리기가 그 깃발을 다시 세웠다. 이제
    늘리기 전에 GET 으로 보고, 우리 수명(마지막으로 늘린 때 + TTL − 30초) 안인데 꺼져 있으면 사람이 내린 것이다 — 멈추고 끝에서도
    건드리지 않는다. TTL 40 에 12초를 쉬어 마지막으로 늘린 때가 1h 가 아니라 § 머리의 늘리기임을 본다(1h 로 셈하면 수명이 지난 것으로 읽는다)."""
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_TTL_S="40",
                     sections=(("3) a", "sleep 12"), ("4) b", _human({"on": False, "by": "human:kim", "force": True})),
                               ("5) c", ""), ("6) d", "")))
    assert rc == 0, out
    on40 = {**ON, "ttl_s": 40}
    assert _ours(agent) == [on40] * 4, f"사람이 내린 깃발을 되살렸거나 끝에서 건드렸다 — {_ours(agent)}"
    assert agent["flag"] is None
    line = _line(out, "○", "리스크 검토 비우기")
    assert "update-all 의 깃발이 수명 전에 내려갔다(누군가 내렸다)" in line and "다시 세우지 않고" in line, line
    assert "다른 주체의 깃발이 없어져" not in out, "사람이 내린 뒤에 #7 이 끼어들었다"


def test_사람이_도중에_넘겨받으면_그_깃발이_풀린_뒤_다시_세운다(tmp_path, agent):
    """D-42 F(#4) — 사람이 off --force 뒤 on(고정 아님, 10초)으로 깃발을 넘겨받았다. 종전엔 '다른 주체의 것이 됐다' 를 찍고 멈춰, 그 깃발이
    풀린 뒤의 §4 재기동이 비우기 없이 돌았다. 이제 고정 아닌 남의 깃발이면 기다렸다가(FOREIGN) 풀린 머리에서 다시 세운다. 끝까지 영영 멈추는
    것은 꺼짐과 고정뿐이다."""
    take = (_human({"on": False, "by": "human:erin", "force": True}) + "; "
            + _human({"on": True, "scope": "all", "ttl_s": 3, "by": "human:erin", "reason": "x"}))
    rc, out, _ = _ua(tmp_path, agent, sections=(("3) a", take), ("4) b", "sleep 4"), ("5) c", ""), ("6) d", "")))
    assert rc == 0, out
    assert _ours(agent) == [ON] * 5 + [OFF], _ours(agent)   # 1h · §2 · §3 · (§4 는 GET 만) · §5 다시 세움 · §6 늘림 · 끝
    line = _line(out, "○", "리스크 검토 비우기")
    assert "수명 전에 다른 주체(by human:erin)의 것이 됐다(고정 아님)" in line and "풀리면 § 머리에서 다시 세운다" in line, line
    assert "· 리스크 검토 비우기 — 다른 주체의 깃발이 없어져 update-all 이 깃발을 세웠다" in out
    assert agent["flag"] is None and agent["expired"] >= 1


@pytest.mark.parametrize("hold", [True, False])
def test_늘리기가_409_를_받으면_조용히_멈추지_않는다(tmp_path, agent, hold):
    """D-42 F(E2) — 우리 수명 여유(30초) 밖이라 GET 으로는 사람 탓을 가르지 못하고 늘렸는데 409 다. 종전엔 아무 줄 없이 멈췄다. 이제 ○ 한
    줄을 낸다 — 고정이면 멈추고, 고정 아닌 남의 깃발이면 그 깃발이 풀리기를 기다린다(다음 머리에서 다시 세워 본다)."""
    if hold:
        take = _human({"on": True, "scope": "all", "hold": True, "by": "human:lee", "reason": "x"})
    else:
        take = (_human({"on": False, "by": "human:erin", "force": True}) + "; "
                + _human({"on": True, "scope": "all", "ttl_s": 600, "by": "human:erin", "reason": "x"}))
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_TTL_S="2", sections=(("3) a", take), ("4) b", ""), ("5) c", "")))
    assert rc == 0, out
    on2 = {**ON, "ttl_s": 2}
    assert _ours(agent) == [on2] * (4 if hold else 5), _ours(agent)   # 고정 아님이면 §5 머리가 다시 세워 본다(409, 조용히)
    line = _line(out, "○", "늘리려다")
    if hold:
        assert "사람이 고정한 깃발(by human:lee" in line and "더 늘리지 않고 끝에서도 건드리지 않는다" in line, line
    else:
        assert "다른 주체가 세운 깃발(by human:erin" in line and "풀리면 § 머리에서 다시 세운다" in line, line
    assert out.count("○") == 1 and "⚠" not in out, out


def test_남의_깃발을_기다리다_고정을_만나면_한_줄을_내고_멈춘다(tmp_path, agent):
    """1h 가 다른 주인의 깃발(고정 아님)을 만나 기다리는데 그 주인이 고정으로 바꿨다 — 세우려던 것을 멈추고 ○ 한 줄. 그 뒤로는 세워 보지 않는다."""
    agent["flag"] = {"scope": "all", "by": "human:lee", "hold": False, "until": time.time() + 600, "until_idle": None,
                     "reason": "점검", "set_at": time.time()}
    take = _human({"on": True, "scope": "all", "hold": True, "by": "human:lee", "reason": "x"})
    rc, out, _ = _ua(tmp_path, agent, sections=(("3) a", take), ("4) b", ""), ("5) c", "")))
    assert rc == 0, out
    assert _ours(agent) == [ON] * 4, _ours(agent)       # 1h · §2 · §3 · §4(고정을 만남) — §5 는 세워 보지 않는다
    line = _line(out, "○", "세우려다")
    assert "사람이 고정한 깃발(by human:lee" in line and "더 세우지 않고 끝에서도 건드리지 않는다" in line, line
    assert agent["flag"]["hold"] is True
    # 끝 요약이 머리의 줄과 어긋나지 않는다 — 1h 의 '풀리면 세운다' ○ 는 고정 문구로 바뀌었다(D-43 #5).
    summary = out[_at(out, "있는데 안 켠 것"):]
    assert "풀리면 § 머리에서 update-all 이 제 깃발을 세운다" not in summary, summary
    assert "리스크 검토 비우기 — 세우려다 사람이 고정한 깃발(by human:lee" in summary and "더 세우지 않고" in summary, summary
    assert summary.count("리스크 검토 비우기") == 1, summary


def test_1h_의_기다림_중에_사람이_내려도_되살리지_않는다(tmp_path, agent):
    """1h 가 세운 때가 첫 기준이다 — §2 머리 전에(도는 카드 대조를 기다리는 동안) 사람이 내렸으면 §2 머리가 그것을 본다."""
    agent["review_seq"] = [2, 0]; agent["off_after_health"] = 2
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_WAIT_S="60")
    assert rc == 0, out
    assert _ours(agent) == [ON], _ours(agent)
    assert "수명 전에 내려갔다" in out and agent["flag"] is None


def test_긴_절에서_수명이_지났으면_다시_세운다(tmp_path, agent):
    """§ 하나가 TTL 보다 길었다(cae00 의 deploy-all 은 30분을 넘길 수 있다) — 깃발은 수명에 풀렸고 사람 탓이 아니다. 다음 머리가 다시
    세우고, 끝맺음은 종전대로 내린다. ○ 를 찍지 않는다."""
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_TTL_S="2", sections=(("3) a", "sleep 3"), ("4) b", "")))
    assert rc == 0, out
    assert agent["expired"] >= 1, "깃발이 풀리지 않았다 — 시험이 수명 경과를 만들지 못했다"
    on2 = {**ON, "ttl_s": 2}
    assert _ours(agent) == [on2] * 4 + [OFF], _ours(agent)
    assert "수명 전에" not in out and "○" not in out, out
    assert agent["flag"] is None


# ── 옛 엔진 · 거절 · 내려간 서버 · 매달린 서버 ──────────────────────────────────────────────────────────
def test_옛_엔진이면_건너뜀_한_줄이고_실패가_아니다(tmp_path, agent):
    agent["old"] = True
    rc, out, _ = _ua(tmp_path, agent)
    assert rc == 0, out
    lines = [ln for ln in out.splitlines() if "○" in ln and "리스크 검토 비우기" in ln]
    assert lines and "/drain 을 모른다(옛 판)" in lines[0], out
    assert len(_posts(agent)) == 1, "옛 판에 늘리거나 내리려 했다"
    assert "⚠" not in out and "✗" not in out


@pytest.mark.parametrize("status", [422, 503])
def test_거절은_옛_판이_아니라_경고다(tmp_path, agent, status):
    """422·503 은 진짜 실패다 — '옛 판' ○ 와 섞으면 깃발 파일이 못 쓰이는 박스를 '엔진만 올리면 된다' 로 읽는다. 배포는 그대로 간다."""
    agent["force_status"] = status
    rc, out, _ = _ua(tmp_path, agent)
    assert rc == 0, out
    line = _line(out, "⚠", "리스크 검토 비우기")
    assert "거절" in line and f"HTTP {status}" in line and "/drain 을 모른다" not in out, line
    assert len(_posts(agent)) == 1, "세우지 못했는데 늘리거나 내렸다"
    assert "경고 1건" in out, "끝의 경고 요약에도 다시 나온다"


def test_내려간_서버는_건너뜀이다(tmp_path, agent):
    rc, out, _ = _ua(tmp_path, agent, url=DEAD)
    assert rc == 0, out
    line = _line(out, "○", "리스크 검토 비우기")
    assert "받지 않는다" in line and "⚠" not in out


def test_매달린_서버는_경고하고_간다(tmp_path, agent):
    agent["delay"] = [5]
    rc, out, _ = _ua(tmp_path, agent, sections=())
    assert rc == 0, out
    line = _line(out, "⚠", "리스크 검토 비우기")
    assert "4초 안에 답하지 않았다" in line and "옛 판" not in line, line


# ── 기다림 ───────────────────────────────────────────────────────────────────────────────────────
def test_도는_카드_대조가_비면_그_자리에서_간다(tmp_path, agent):
    agent["review_seq"] = [2, 2, 0]
    t0 = time.monotonic()
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_WAIT_S="60")
    took = time.monotonic() - t0
    assert rc == 0, out
    assert "도는 카드 대조 2건 — 끝나기를 최대 60초 기다린다" in out and "카드 대조가 비었다" in out, out
    assert took < 20, f"비었는데 한도까지 기다렸다({took:.1f}초)"
    assert _health_hits(agent) == 3


def test_끝나지_않으면_한도_뒤에_경고_없이_간다(tmp_path, agent):
    agent["review"] = 2
    t0 = time.monotonic()
    rc, out, _ = _ua(tmp_path, agent, HWAX_DRAIN_WAIT_S="3")
    took = time.monotonic() - t0
    assert rc == 0, out
    # 기다림은 bash $SECONDS(정수 초)로 잰다 — 한도 3초는 시작한 초 안의 자리에 따라 실제 2초 남짓에 끝날 수 있다(전체 시험에서 2.39초로
    # 실패했다, 2026-10-16). 그래서 하한은 한도 - 1 이다.
    assert 2 <= took < 25, took
    assert "3초 안에 끝나지 않은 카드 대조 2건" in out and "⚠" not in out, out
    assert _strip_reason(_last(agent)) == OFF


@pytest.mark.parametrize("env,said", [({"AGENT_RESTART_FORCE": "1", "HWAX_DRAIN_WAIT_S": "20"}, "AGENT_RESTART_FORCE=1 — 도는 카드 대조를 기다리지 않는다"),
                                      ({"HWAX_DRAIN_WAIT_S": "0"}, "HWAX_DRAIN_WAIT_S=0 — 도는 카드 대조 2건을 기다리지 않는다")])
def test_강행이나_0_이면_세우되_기다리지_않는다(tmp_path, agent, env, said):
    agent["review"] = 2
    t0 = time.monotonic()
    rc, out, _ = _ua(tmp_path, agent, **env)
    assert rc == 0 and time.monotonic() - t0 < 15, out
    assert said in out, out
    posts = [_strip_reason(b) for b in _posts(agent)]
    assert posts and posts[0] == ON and posts[-1] == OFF, "강행이어도 세우고 끝에서 내린다"
    if "AGENT_RESTART_FORCE" in env:
        assert _health_hits(agent) == 0, "강행이면 묻지도 않는다"


def test_TTL_손잡이는_21600_에서_자른다(tmp_path, agent):
    """엔진은 요청 하나의 ttl_s 를 21,600 까지만 받는다(422) — 큰 값을 적은 박스에서 깃발이 아예 안 서면 안 된다."""
    rc, out, _ = _ua(tmp_path, agent, sections=(("3) a", ""),), HWAX_DRAIN_TTL_S="99999")
    assert rc == 0, out
    assert {b.get("ttl_s") for b in _posts(agent) if b["on"]} == {TTL_CAP}, _posts(agent)
    assert "⚠" not in out


# ── 정지 신호 ─────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("deferred", [True, False])
def test_정지_신호로_멈춰도_끝맺음이_장부를_지우기_전에_돈다(tmp_path, agent, deferred):
    """§ 머리에서 멈추는 경로(HWAX_UPDATE_ALL_STOP=1)에서도 끝맺음이 돈다 — 미룬 줄을 읽어야 하므로 장부를 지우기 전이다. 멈춘 뒤로는
    늘리지 않는다(끝맺음이 늘리기를 멈춘다)."""
    agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=("포털·nginx 재기동 건너뜀",) if deferred else (),
                     sections=(("3) a", "export HWAX_UPDATE_ALL_STOP=1"), ("4) b", ""), ("5) c", "")))
    assert rc == 143, out
    assert "종료 요청을 받아 여기서 멈춘다" in out and "전체 최신화 완료" not in out
    posts = [_strip_reason(b) for b in _posts(agent)]
    assert posts[:3] == [ON] * 3, "1h · §2 · §3 머리 — 멈춘 머리(§4)에서는 늘리지 않는다"
    assert len(posts) == 4, posts
    if deferred:
        assert posts[-1].get("scope") == "panels" and "until_idle" in posts[-1], posts[-1]
        stop = out[_at(out, "종료 요청을 받아 여기서 멈춘다"):]
        assert "리스크 검토 비우기 유지" in stop[_at(stop, "있는데 안 켠 것"):], "정지 요약에 창이 나온다 — 장부를 지우기 전에 돌았다"
    else:
        assert posts[-1] == OFF and agent["flag"] is None


def test_끝맺음_뒤의_머리는_깃발을_늘리지_않는다(tmp_path, agent):
    """늘리기는 주인의 요청이라 scope 를 all 로 되돌린다 — 끝맺음(새 패널만 멈추는 창) 뒤에 § 머리가 하나라도 늘리면 카드 대조가 다시
    멈춘다. 지금은 끝맺음 뒤에 머리가 없지만, 순서를 바꾼 판이 생겨도 끝맺음이 늘리기를 멈춘다."""
    agent["delib"] = (1, 0)
    rc, out, _ = _ua(tmp_path, agent, deploy_ledger=("포털·nginx 재기동 건너뜀",),
                     sections=(("3) a", "_hwax_drain_finish"), ("4) b", ""), ("5) c", "")))
    assert rc == 0, out
    posts = _posts(agent)
    first = next((i for i, b in enumerate(posts) if "until_idle" in b), None)
    assert first is not None and posts[first].get("scope") == "panels", posts
    assert posts[first + 1:] == [], f"끝맺음 뒤에 또 보냈다(늘리기는 scope 를 all 로 되돌린다) — {posts[first + 1:]}"
    assert agent["flag"]["scope"] == "panels"


# ── 배선 — 자리와 순서 ─────────────────────────────────────────────────────────────────────────────
def test_update_all_배선():
    import re

    assert _at(UA, '. "$SELF_REPO/infra/scripts/lib/delib-busy.sh"') < _at(UA, '. "$SELF_REPO/infra/scripts/lib/review-drain.sh"') \
        < _at(UA, 'hr "1) 포털 레포 최신화"'), "lib 는 첫 § 머리 전에 적재한다(정지 경로가 끝맺음을 부른다)"
    one_h = _at(UA, 'hr "1h) 리스크 검토 비우기"')
    two = _at(UA, 'hr "2) deploy-all-from-drive')
    between = re.findall(r'hr "([^"]*)"', UA[one_h + 5:two])
    assert one_h < two and all(h.startswith("1i) LLM 라우터") for h in between), \
        f"1h 와 §2 사이에는 1i(LLM 라우터 — 라우터 재기동도 비우기 창 안에서 한다)뿐이다: {between}"
    assert _at(UA, "# ── 1g)") < one_h, "1g(NO_PROXY) 뒤 — 1h 의 curl 은 루프백이라 상관없지만 차례를 지킨다"
    hr = _region('hr() { if [ "${HWAX_UPDATE_ALL_STOP:-0}" = 1 ]; then', "\nok() {")
    stop = hr[:_at(hr, "exit 143")]
    assert _at(stop, "_hwax_drain_finish") < _at(stop, "hwax_skip_summary") < _at(stop, 'rm -f "${HWAX_SKIP_LEDGER'), \
        "정지 경로 — 끝맺음 → 요약 → 장부 지우기"
    assert "_hwax_drain_tick" in hr[_at(hr, "exit 143"):], "깃발 돌보기는 정지 판정 뒤다"
    tail = _tail()
    assert _at(tail, "_hwax_drain_finish") < _at(tail, "hwax_skip_summary") < _at(tail, 'rm -f "$HWAX_SKIP_LEDGER"')
    head = UA[:UA.index("set -uo pipefail")]
    for knob in ("HWAX_DRAIN_TTL_S=1800", "HWAX_DRAIN_WAIT_S=300", "HWAX_DRAIN_GRACE_S=1800", "HWAX_DRAIN_MAX_S=46800",
                 "HWAX_AGENT_URL=http://127.0.0.1:9009", "review-drain.sh", "21600"):
        assert knob in head, f"머리 주석에 {knob} 가 없다"
    for line in (_drain_and_deploy() + _region("_hwax_drain_finish() {", "\n}\n")
                 + _region("_hwax_drain_tick() {", "\n}\n")).splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"


def test_lib_의_0_아닌_값은_받아서_쓴다():
    """3·5 를 정상으로 돌려준다 — set -e 스크립트에서 맨 문장으로 부르면 조용히 끝난다(f1958af). 부르는 곳은 전부 || _rc=$? 다."""
    import re

    for src in (_drain_and_deploy(), _region("_hwax_drain_finish() {", "\n}\n"), _region("_hwax_drain_tick() {", "\n}\n"), WRAPPER):
        for m in re.finditer(r"\$\((hwax_drain|hwax_drain_owner|hwax_review_state|hwax_review_wait|hwax_review_brief)\b[^\n]*", src):
            assert "|| _" in m.group(0) or "|| rc=$?" in m.group(0), m.group(0)
    assert "|| _rc=$?" in DRAIN_LIB[:DRAIN_LIB.index("HWAX_DRAIN_TTL_CAP=")], "머리 주석이 받는 법을 말한다"


# ── lib — 묻는 함수 ────────────────────────────────────────────────────────────────────────────────
def _lib(tmp_path: Path, agent_url: str, call: str, **env) -> tuple[int, str]:
    repo = _portal(tmp_path, DEAD)
    r = _sh(f'set -uo pipefail\n. "{repo}/infra/scripts/lib/review-drain.sh"\nrc=0; out="$({call})" || rc=$?\necho "rc=$rc out=[$out]"',
            tmp_path, HWAX_AGENT_URL=agent_url, **env)
    assert not r.stderr, r.stderr
    rc, out = r.stdout.strip().split(" ", 1)
    return int(rc[3:]), out[5:-1]


def test_상태는_다섯_수다(tmp_path, agent):
    agent["review"] = 3; agent["delib"] = (2, 1)
    agent["flag"] = {"scope": "all", "by": "update-all", "hold": False, "until": time.time() + 60, "until_idle": None, "set_at": 1}
    assert _lib(tmp_path, agent["url"], "hwax_review_state") == (0, "3 1 1 2 1")
    agent["flag"]["scope"] = "panels"
    assert _lib(tmp_path, agent["url"], "hwax_review_state") == (0, "3 0 1 2 1"), "draining 은 scope all 일 때만이다"
    agent["old"] = True
    assert _lib(tmp_path, agent["url"], "hwax_review_state") == (3, "")
    assert _lib(tmp_path, DEAD, "hwax_review_state") == (2, "")


def test_운영자_셸의_프록시를_타지_않는다(tmp_path, agent):
    dead = "http://127.0.0.1:9"
    rc, out = _lib(tmp_path, agent["url"], "hwax_drain on all 1800 update-all x", http_proxy=dead, HTTP_PROXY=dead, no_proxy="",
                   NO_PROXY="")
    assert rc == 0 and "깃발 on(scope all · by update-all" in out, out


@pytest.mark.parametrize("given,sent", [("99999", TTL_CAP), ("21600", TTL_CAP), ("600", 600), ("0", 1800), ("많이", 1800), ("", 1800)])
def test_TTL_은_양의_정수로_읽고_상한에서_자른다(tmp_path, agent, given, sent):
    assert _lib(tmp_path, agent["url"], f'hwax_drain on all "{given}" update-all x')[0] == 0
    assert _last(agent).get("ttl_s") == sent, _last(agent)


def test_사유의_따옴표가_요청을_깨지_않는다(tmp_path, agent):
    rc, _ = _lib(tmp_path, agent["url"], "hwax_drain on all 60 'human:o\"k' 'a \"b\" \\\\ c'")
    assert rc == 0 and _last(agent).get("by") == 'human:o"k' and _last(agent).get("reason") == r'a "b" \\ c'


def test_기다림_함수는_마지막에_본_수를_돌려준다(tmp_path, agent):
    agent["review"] = 4
    assert _lib(tmp_path, agent["url"], "hwax_review_wait 0") == (1, "4")
    agent["review"] = 0
    assert _lib(tmp_path, agent["url"], "hwax_review_wait 0") == (0, "0")
    assert _lib(tmp_path, DEAD, "hwax_review_wait 30") == (0, "0"), "내려간 서버에는 기다릴 카드 대조가 없다"


# ── §6 헬스게이트 한 줄 ─────────────────────────────────────────────────────────────────────────────
def _gate6(tmp_path: Path, url: str) -> str:
    i = UA.index('_rb_rc=0; _rb="$(hwax_review_brief)"')
    block = UA[i:UA.index("esac\n", i) + 5]
    repo = _portal(tmp_path, DEAD)
    r = _sh(f'set -uo pipefail\n. "{repo}/infra/scripts/lib/review-drain.sh"\nok() {{ echo "OK:$*"; }}; bad() {{ echo "BAD:$*"; }}\n'
            f'{block}\necho end', tmp_path, HWAX_AGENT_URL=url)
    assert r.returncode == 0 and not r.stderr and "end" in r.stdout, r.stderr
    return r.stdout


def test_헬스게이트가_깃발과_카드_대조를_한_줄로_낸다(tmp_path, agent):
    agent["review"] = 2
    agent["flag"] = {"scope": "all", "by": "update-all", "hold": False, "until": time.time() + 900, "until_idle": None, "set_at": 1}
    out = _gate6(tmp_path, agent["url"])
    assert out.startswith("OK:리스크 검토") and "비우기 깃발 on(scope all · by update-all · 남은" in out and "도는 카드 대조 2건" in out, out
    agent["flag"] = None
    assert "OK:리스크 검토      비우기 깃발 꺼짐 · 도는 카드 대조 2건" in _gate6(tmp_path, agent["url"])


def test_챗이_느리면_헬스게이트가_경고한다(tmp_path, agent):
    """D-34 '알린다' — 카드 대조 중 챗 첫 조각 p50 이 평소의 2배를 넘으면 ⚠ 와 낮추는 손잡이."""
    agent["slow"] = True
    out = _gate6(tmp_path, agent["url"])
    assert out.startswith("BAD:") and "2배" in out and "CARD_REVIEW_CONCURRENCY" in out and "./start.sh -d" in out, out


def test_헬스게이트는_옛_판과_못_읽음을_가른다(tmp_path, agent):
    agent["old"] = True
    assert "옛 판" in _gate6(tmp_path, agent["url"])
    out = _gate6(tmp_path, DEAD)
    assert "읽지 못했다" in out and "OK:" not in out and "BAD:" not in out


# ── 사람이 쓰는 감싸개 ──────────────────────────────────────────────────────────────────────────────
def _wrap(tmp_path: Path, agent_url: str, *args: str) -> subprocess.CompletedProcess:
    repo = _portal(tmp_path, DEAD)
    quoted = " ".join(f"'{a}'" for a in args)
    return _sh(f'"{repo}/infra/scripts/review-drain.sh" {quoted}', tmp_path, HWAX_AGENT_URL=agent_url, USER="kim")


def test_감싸개로_세우고_보고_내린다(tmp_path, agent):
    r = _wrap(tmp_path, agent["url"], "on")
    assert r.returncode == 0 and "✓ 깃발 on(scope all · by human:kim" in r.stdout, r.stdout + r.stderr
    assert _strip_reason(_last(agent)) == {"on": True, "scope": "all", "ttl_s": 1800, "by": "human:kim"}
    r = _wrap(tmp_path, agent["url"])
    assert r.returncode == 0 and "by human:kim" in r.stdout and "카드 대조 0건" in r.stdout
    r = _wrap(tmp_path, agent["url"], "off")
    assert r.returncode == 0 and "깃발 꺼짐" in r.stdout and agent["flag"] is None


def test_감싸개의_고정과_강제_내리기(tmp_path, agent):
    assert _wrap(tmp_path, agent["url"], "on", "--hold").returncode == 0
    assert _strip_reason(_last(agent)) == {"on": True, "scope": "all", "hold": True, "by": "human:kim"}
    agent["flag"]["by"] = "human:lee"
    r = _wrap(tmp_path, agent["url"], "off")
    assert r.returncode == 5 and "건드리지 않았다" in r.stderr and "off --force" in r.stderr, r.stderr
    r = _wrap(tmp_path, agent["url"], "off", "--force")
    assert r.returncode == 0 and _last(agent) == {"on": False, "by": "human:kim", "force": True} and agent["flag"] is None


def test_감싸개의_TTL_은_상한에서_자르고_말한다(tmp_path, agent):
    r = _wrap(tmp_path, agent["url"], "on", "--ttl", "99999")
    assert r.returncode == 0 and "21600초로 자른다" in r.stdout and _last(agent).get("ttl_s") == TTL_CAP
    assert _wrap(tmp_path, agent["url"], "on", "--ttl", "0").returncode == 64 and len(_posts(agent)) == 1


@pytest.mark.parametrize("case,rc,said", [("old", 3, "옛 판"), ("dead", 2, "떠 있는지"), ("refuse", 6, "거절")])
def test_감싸개는_실패를_가른다(tmp_path, agent, case, rc, said):
    agent["old"] = case == "old"
    agent["force_status"] = 503 if case == "refuse" else None
    r = _wrap(tmp_path, DEAD if case == "dead" else agent["url"], "on")
    assert r.returncode == rc and said in r.stderr, r.stderr
