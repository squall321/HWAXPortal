# update-all 1i(LLM 라우터) · §4 뒤 라우터 내리기 · §6 라우터 한 줄 — LLM_UPSTREAMS 한 줄이 라우터와 사본 주소로 이어지고 지우면 되돌아가는지
"""왜 — 사람이 적는 것은 infra/.env 의 LLM_UPSTREAMS 한 줄이다(docs/llm-pool PLAN §4). 그 줄이 있으면 라우터를 띄우고 라우터가 서버를
올렸다고 답할 때만 사본을 라우터로 바꾸고, 지우면 라우터를 가리키는 사본만 직접 주소로 되돌리고 라우터를 내린다. 사본은 운영 박스의
.env 다 — 라우터가 죽어 있는데 사본을 바꾸면 그 순간 챗·심의의 LLM 이 전부 끊긴다.

update-all 의 구획을 **원문 그대로** 떼어 임시 포털 리포에서 돌린다. update-sites.sh·llm-router.sh 는 부른 사실만 적는 대역이고, 라우터
/health 는 지어낸 서버다(빈 포트 — infra/.env 의 LLM_ROUTER_PORT 로 가리킨다).
⚠ 실물을 건드리면 안 된다 — 상대경로 하네스가 실 apptainer 로 dev nginx 를 내린 사고가 있었다(2026-09-28).
  · 경로는 전부 절대경로다. 하네스는 임시 디렉터리에서 돌고, 부르는 스크립트가 임시 리포의 대역인지 먼저 확인한다(아니면 97).
  · HOME 을 임시 디렉터리로 바꾼다 — lib 는 형제 리포를 ~/claude 에서도 찾는다(실물 .env 를 고치지 않게). 시험마다 LLM_ROUTER_PORT 를
    적는다(실물 9130 을 두드리지 않게).
"""
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
S1, S2 = "http://203.0.113.11:10000/v1", "http://203.0.113.12:10000/v1"
DIRECT = S1
FOREIGN = "http://198.51.100.40:8000/v1"
SIBLINGS = {"agent-server": ("HWAXAgentServer", ".env", "VLLM_BASE_URL"),
            "aidh-openai": ("AIDataHub", "deploy/apptainer/.env", "OPENAI_BASE_URL"),
            "aidh-llm": ("AIDataHub", "deploy/apptainer/.env", "LLM_BASE_URL"),
            "heax-hub": ("HEAXHub", ".env", "HEAX_APP_LLM_BASE_URL"),
            "signalforge": ("SignalForge", ".env", "OPENAI_BASE_URL"),
            "mx-white-paper": ("MXWhitePaper", ".env", "LLM_BASE_URL"),
            "paper-ingest": ("PaperIngest", ".env", "GLM_BASE_URL")}


def _region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    assert end in UA[i:], f"`{end}` 가 `{start}` 뒤에 없다"
    return UA[i:UA.index(end, i)]


def _block_1i() -> str:
    return _region("# ── 1i) LLM 라우터", "# ── 2) 전 서비스 배포")


def _block_retire() -> str:
    return _region("# 1i 의 뒤처리", "# ste 를 이 박스가 쓰는가")


def _block_s6() -> str:
    return _region("# LLM 라우터 — 풀이 켜진 박스만", "# 리스크 검토 — 비우기 깃발")


def _dead_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _ok_body(**kw) -> dict:
    b = {"status": "ok", "upstreams_total": 2, "upstreams_up": 2, "inflight": 0,
         "models": {"match": True, "ids": ["glm"], "max_model_len": 1048576}, "config_mtime": 1.0}
    b.update(kw)
    return b


@pytest.fixture()
def router():
    """지어낸 라우터 /health — state['seq'] 가 있으면 요청마다 앞에서 하나씩 꺼내고(비면 state['body']), 503 은 status down 일 때."""
    state = {"body": _ok_body(), "seq": [], "hits": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            body = state["seq"].pop(0) if state["seq"] else state["body"]
            if self.path != "/health" or body is None:
                self.send_response(404); self.end_headers(); return
            raw = json.dumps(body).encode()
            self.send_response(503 if body.get("status") == "down" else 200)
            self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["port"] = srv.server_address[1]
    yield state
    srv.shutdown(); srv.server_close()


class Box:
    """임시 박스 — 포털(lib·킷·대역 스크립트 사본) + 형제 리포 + 빈 HOME."""

    def __init__(self, tmp: Path):
        self.tmp, self.repo, self.home = tmp, tmp / "HWAXPortal", tmp / "home"
        (self.repo / "infra/scripts/lib").mkdir(parents=True); self.home.mkdir()
        for name in ("llm-pool.sh", "skip-ledger.sh"):
            shutil.copy(SCRIPTS / "lib" / name, self.repo / "infra/scripts/lib" / name)
        shutil.copytree(ROOT / "infra/env-kits", self.repo / "infra/env-kits")
        self.calls, self.ledger = tmp / "calls.log", tmp / "ledger"
        self.calls.write_text(""); self.ledger.write_text("")
        for name, rc_var in (("update-sites.sh", "STUB_US_RC"), ("llm-router.sh", "STUB_LR_RC")):
            p = self.repo / "infra/scripts" / name
            p.write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "{self.calls}"\necho "  (대역) {name} $*"\nexit ${{{rc_var}:-0}}\n')
            p.chmod(0o755)

    def env(self, text: str):
        assert "LLM_ROUTER_PORT=" in text, "시험마다 라우터 포트를 적는다 — 실물 9130 을 두드리지 않게"
        (self.repo / "infra/.env").write_text(text, encoding="utf-8")

    def copy(self, which: str) -> Path:
        repo, rel, _ = SIBLINGS[which]
        p = self.tmp / repo / rel; p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, values: dict[str, str]):
        """사본 값 — {사본: 값}. 같은 파일의 키는 한 파일에 모은다."""
        files: dict[Path, str] = {}
        for which, val in values.items():
            p = self.copy(which); key = SIBLINGS[which][2]
            files[p] = files.get(p, "") + f"{key}={val}\n"
        for p, text in files.items():
            p.write_text("# 박스 설정\n" + text + "OTHER=1\n", encoding="utf-8")

    def value(self, which: str) -> str | None:
        p = self.copy(which); key = SIBLINGS[which][2]
        if not p.exists():
            return None
        m = re.findall(rf"^{key}=(.*)$", p.read_text(encoding="utf-8"), re.M)
        return m[-1] if m else None

    def snapshot(self) -> dict[Path, bytes]:
        return {p: p.read_bytes() for p in self.tmp.rglob(".env*") if p.is_file() and "HWAXPortal" not in p.parts}

    def run(self, *, first: bool = True, retire: bool = False, s6: bool = False, pre: str = "", post: str = "", **env) -> str:
        """구획을 원문 그대로 잇는다 — first(1i) → pre(그 사이 일어난 일 — §2·§4 의 결과) → retire(§4 뒤 라우터 내리기) → s6."""
        body = (_block_1i() + "\necho \"RETIRE=[$_LLM_RETIRE]\"\n" if first else "") + pre
        if retire:
            body += _block_retire()
        if s6:
            body += _block_s6()
        for real in ("/home/", "127.0.0.1:9130"):
            assert real not in body, f"돌리는 구획에 {real} 가 박혀 있다 — 하네스가 실물을 건드린다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"',
            f'SELF_REPO="{self.repo}"',
            f'[ "$(cd "$SELF_REPO" && pwd)" = "{self.repo}" ] || {{ echo "HARNESS: 임시 리포가 아니다" >&2; exit 97; }}',
            f'grep -q "(대역) update-sites.sh" "$SELF_REPO/infra/scripts/update-sites.sh" || exit 97',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"',
            f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"', f'. "{self.repo}/infra/scripts/lib/llm-pool.sh"',
            body, post, "echo END",
        ])
        base = {"PATH": os.environ["PATH"], "HOME": str(self.home), "LANG": "C.UTF-8", "HWAX_LLM_ROUTER_WAIT_S": "0"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120, env={**base, **env})
        assert r.returncode != 97, r.stdout + r.stderr
        assert "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def called(self) -> list[str]:
        return self.calls.read_text().splitlines()


@pytest.fixture()
def box(tmp_path):
    return Box(tmp_path)


def _lines(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


ALL_DIRECT = {"agent-server": DIRECT, "aidh-openai": DIRECT, "aidh-llm": f"{DIRECT}/", "heax-hub": S2,
              "signalforge": DIRECT, "mx-white-paper": DIRECT, "paper-ingest": DIRECT}


# ── 풀 켜기 ─────────────────────────────────────────────────────────────────────────────────────────
def test_라우터가_답하면_사본을_라우터로_바꾸고_무엇이_언제_반영되는지_말한다(box, router):
    """**이 시험이 이 파일의 이유다** — 한 줄로 라우터를 띄우고(update-sites), 서버가 올라왔다고 답하면 관리하는 사본을 전부 라우터로."""
    rurl = f"http://127.0.0.1:{router['port']}/v1"
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({**ALL_DIRECT, "heax-hub": FOREIGN})
    out = box.run()
    assert box.called() == ["update-sites.sh llm-router"], box.called()
    assert not _lines(out, "FAIL:"), out
    for which in SIBLINGS:
        want = FOREIGN if which == "heax-hub" else rurl
        assert box.value(which) == want, (which, box.value(which), out)
    assert any("HEAX_APP_LLM_BASE_URL 는 관리하는 주소가 아니다" in ln for ln in _lines(out, "BAD:")), "관리 밖 사본은 ⚠ 로 말한다"
    assert len([ln for ln in _lines(out, "OK:") if "백업" in ln]) == 6, out
    assert "되돌리기 — infra/.env 의 LLM_UPSTREAMS 줄을 지우고" in out
    assert "· agent-server — §4 update-sites" in out and "· ai-data-hub — §2 deploy-all" in out
    assert "· signalforge — §2" in out and "· mx-white-paper — §2" in out
    pi = [ln for ln in _lines(out, "BAD:") if ln.startswith("BAD:paper-ingest")]
    assert len(pi) == 1 and "다시 띄우지 않는다" in pi[0] and "직접 주소를 쓴다" in pi[0], "이번 실행이 안 띄우는 사본은 따로 말한다"
    assert "RETIRE=[0]" in out


def test_막_뜬_라우터가_서버를_올릴_때까지_기다린다(box, router):
    down = _ok_body(status="down", upstreams_up=0)
    router["seq"] = [down, down]
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT})
    out = box.run(HWAX_LLM_ROUTER_WAIT_S="10")
    assert box.value("agent-server") == f"http://127.0.0.1:{router['port']}/v1", out
    assert router["hits"] >= 3 and not _lines(out, "FAIL:")


@pytest.mark.parametrize("case", ["올라온 서버 0", "답이 없다", "라우터의 답이 아니다"])
def test_라우터가_쓸_수_없으면_사본을_건드리지_않고_실패로_센다(box, router, case):
    port = router["port"]
    if case == "올라온 서버 0":
        router["body"] = _ok_body(status="down", upstreams_up=0)
    elif case == "답이 없다":
        port = _dead_port()
    else:
        router["body"] = {"status": "ok"}
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={port}\n")
    box.put(ALL_DIRECT)
    before = box.snapshot()
    out = box.run()
    assert box.snapshot() == before, "라우터가 쓸 수 없는데 사본을 바꿨다 — 그 순간 LLM 이 끊긴다"
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "사본을 라우터로 바꾸지 않았다" in fails[0], out
    assert box.called() == ["update-sites.sh llm-router"]


def test_이미_라우터를_가리키는_사본이_있으면_그_사실을_말한다(box, router):
    router["body"] = _ok_body(status="down", upstreams_up=0)
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": f"http://127.0.0.1:{router['port']}/v1", "signalforge": DIRECT})
    out = box.run()
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "사본 1곳은 그대로" in fails[0] and "지금 실패한다" in fails[0], out


def test_라우터를_못_띄웠으면_실패는_한_번만_센다(box):
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1}\nLLM_ROUTER_PORT={_dead_port()}\n")
    box.put({"agent-server": DIRECT})
    out = box.run(STUB_US_RC="1")
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "update-sites llm-router rc 1" in fails[0], "원인 하나에 ✗ 하나"
    assert "사본은 라우터로 바꾸지 않았다" in out and box.value("agent-server") == DIRECT


def test_재기동을_미룬_라우터가_답하면_그대로_바꾼다(box, router):
    """update-sites 의 3 은 미룸이지 실패가 아니다 — 옛 라우터가 돌고 있고 서버를 올렸다고 답하면 사본은 라우터로 간다."""
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT})
    out = box.run(STUB_US_RC="3")
    assert not _lines(out, "FAIL:") and box.value("agent-server") == f"http://127.0.0.1:{router['port']}/v1", out


def test_틀린_목록이면_아무것도_하지_않는다(box, router):
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1}, {S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put(ALL_DIRECT)
    before = box.snapshot()
    out = box.run()
    assert box.called() == [] and box.snapshot() == before and router["hits"] == 0
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "따옴표 밖" in fails[0] and "아무것도 바꾸지 않았다" in fails[0]


def test_두_번째_실행은_아무것도_바꾸지_않는다(box, router):
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put(ALL_DIRECT)
    box.run()
    snap = box.snapshot()
    out = box.run()
    assert box.snapshot() == snap, "두 번째 실행이 파일을 쓰거나 백업을 늘렸다"
    assert "바꿈 0 · 이미 그 주소 7" in out and "되돌리기" not in out, out


# ── 풀 끄기 ─────────────────────────────────────────────────────────────────────────────────────────
def _off(box: Box, router, *, direct: str | None = DIRECT, values: dict | None = None):
    rurl = f"http://127.0.0.1:{router['port']}/v1"
    box.env((f"LLM_BASE_URL={direct}\n" if direct else "") + f"LLM_ROUTER_PORT={router['port']}\n")
    box.put(values if values is not None else {"agent-server": rurl, "aidh-openai": rurl, "signalforge": DIRECT, "heax-hub": FOREIGN})
    return rurl


def test_줄을_지우면_라우터를_가리키는_사본만_되돌리고_라우터는_4장_뒤에_내린다(box, router):
    rurl = _off(box, router)
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.value("agent-server") == DIRECT and box.value("aidh-openai") == DIRECT
    assert box.value("signalforge") == DIRECT and box.value("heax-hub") == FOREIGN, "라우터를 안 가리키던 사본은 그대로"
    assert "RETIRE=[1]" in out and box.called() == ["llm-router.sh stop"], (box.called(), out)
    assert not _lines(out, "BAD:HEAXHub"), "끌 때는 관리 밖 사본을 다시 알리지 않는다(풀과 무관하다)"
    assert any("LLM 라우터를 내렸다" in ln for ln in _lines(out, "OK:")) and not _lines(out, "FAIL:"), out
    assert out.index("RETIRE=[1]") < out.index("(대역) llm-router.sh stop"), "내리는 것은 1i 가 아니라 §4 뒤다"
    assert rurl not in "".join(p.read_text() for p in box.snapshot() if not p.name.startswith(".env.bak"))


@pytest.mark.parametrize("case", ["도는 요청", "미룬 재기동", "§2 실패"])
def test_아직_라우터를_쓰는_것이_있으면_내리지_않는다(box, router, case):
    _off(box, router)
    pre = "_DA_RC=0; _us_rc=0\n"
    if case == "도는 요청":
        router["body"] = _ok_body(inflight=2)
    elif case == "미룬 재기동":
        pre += 'hwax_skip_record "agent-server 재기동 건너뜀" "심의 1건 진행 중" "끝난 뒤 다시"\n'
    else:
        pre = "_DA_RC=4; _us_rc=0\n"
    out = box.run(retire=True, pre=pre)
    assert box.value("agent-server") == DIRECT, "사본은 되돌렸다"
    assert box.called() == [], f"아직 라우터를 쓰는 것이 있는데 내렸다 — {box.called()}"
    assert "LLM 라우터 내리기 미룸" in box.ledger.read_text() and "○" in out
    assert not re.search(r"(재기동|재프로비저닝) 건너뜀$", box.ledger.read_text().splitlines()[-1].split("\t")[0]), \
        "1h 끝맺음이 '미룬 재기동' 으로 읽는 이름이면 안 된다"


def test_강행하면_도는_요청이_있어도_내린다(box, router):
    _off(box, router)
    router["body"] = _ok_body(inflight=2)
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n", LLM_ROUTER_RESTART_FORCE="1")
    assert box.called() == ["llm-router.sh stop"], out


def test_라우터를_가리키는_사본이_남으면_강행해도_내리지_않는다(box, router):
    _off(box, router)
    pre = f'_DA_RC=0; _us_rc=0\nprintf "VLLM_BASE_URL=http://127.0.0.1:{router["port"]}/v1\\n" >> "{box.copy("agent-server")}"\n'
    out = box.run(retire=True, pre=pre, LLM_ROUTER_RESTART_FORCE="1")
    assert box.called() == [] and "사본 1곳이 아직 라우터를 가리킨다" in box.ledger.read_text(), out


def test_되돌릴_직접_주소가_없으면_사본도_라우터도_그대로(box, router):
    rurl = _off(box, router, direct=None)
    before = box.snapshot()
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.snapshot() == before and box.called() == [] and "RETIRE=[0]" in out
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "LLM_BASE_URL" in fails[0] and box.value("agent-server") == rurl


def test_사본은_되돌렸고_라우터만_남았으면_다음_실행이_내린다(box, router):
    """미룬 뒤의 실행 — 사본은 이미 직접 주소다. 라우터가 아직 떠 있으면 내린다."""
    _off(box, router, values={"agent-server": DIRECT})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert "HR:1i) LLM 라우터 — 풀 꺼짐" in out and box.called() == ["llm-router.sh stop"]


def test_아무것도_없으면_안_켠_기능으로만_남긴다(box):
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")
    box.put(ALL_DIRECT)
    before = box.snapshot()
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.snapshot() == before and box.called() == [] and not _lines(out, "HR:"), out
    assert "LLM 서버 풀(라우터)" in out and "LLM_UPSTREAMS=<서버1 /v1 주소>,<서버2 /v1 주소>" in out
    assert box.ledger.read_text().startswith("LLM 서버 풀(라우터)\t"), "끝 요약에도 다시 나온다"
    assert not _lines(out, "FAIL:") and not _lines(out, "BAD:")


def test_같은_포트의_다른_것은_라우터로_치지_않는다(box, router):
    router["body"] = {"status": "ok", "service": "다른 앱"}
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put(ALL_DIRECT)
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.called() == [] and "RETIRE=[0]" in out and "LLM 서버 풀(라우터)" in out


# ── §6 한 줄 ───────────────────────────────────────────────────────────────────────────────────────
def _s6(box: Box, router, body: dict | None, values: dict, *, pool: bool = True) -> str:
    port = router["port"] if body is not None else _dead_port()
    if body is not None:
        router["body"] = body
    box.env((f"LLM_UPSTREAMS={S1},{S2}\n" if pool else "") + f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={port}\n")
    box.put({k: v.replace("ROUTER", f"http://127.0.0.1:{port}/v1") for k, v in values.items()})
    return box.run(first=False, s6=True)


def test_6장_은_서버와_모델과_도는_요청을_한_줄로(box, router):
    out = _s6(box, router, _ok_body(inflight=3), {"agent-server": "ROUTER"})
    assert "OK:LLM 라우터      서버 2/2 올라옴 · 모델 같음 · 도는 요청 3" in out, out


@pytest.mark.parametrize("body,needle", [
    (_ok_body(status="degraded", upstreams_up=1), "내려간 서버"),
    (_ok_body(models={"match": False, "ids": ["a", "b"], "max_model_len": 1}), "모델·창이 다르다"),
    (_ok_body(models={}), "아직 대조하지 못했다"),
])
def test_6장_반쯤_성한_라우터는_경고다(box, router, body, needle):
    out = _s6(box, router, body, {"agent-server": "ROUTER"})
    bads = [ln for ln in _lines(out, "BAD:") if "LLM 라우터" in ln]
    assert len(bads) == 1 and needle in bads[0] and not _lines(out, "FAIL:LLM"), out


def test_6장_라우터가_못_쓰는데_사본이_가리키면_실패다(box, router):
    out = _s6(box, router, _ok_body(status="down", upstreams_up=0), {"agent-server": "ROUTER", "signalforge": "ROUTER"})
    fails = [ln for ln in _lines(out, "FAIL:") if "LLM 라우터" in ln]
    assert len(fails) == 1 and "사본 2곳이 라우터를 가리킨다" in fails[0], out


def test_6장_사본이_직접_주소면_경고에_그친다(box, router):
    out = _s6(box, router, None, {"agent-server": DIRECT})
    bads = [ln for ln in _lines(out, "BAD:") if "LLM 라우터" in ln]
    assert len(bads) == 1 and "LLM 은 돈다" in bads[0] and not [ln for ln in _lines(out, "FAIL:") if "LLM 라우터" in ln], out


def test_6장_풀이_꺼져_있으면_말하지_않는다(box, router):
    out = _s6(box, router, _ok_body(), {"agent-server": DIRECT}, pool=False)
    assert "LLM 라우터" not in "\n".join(_lines(out, "OK:") + _lines(out, "BAD:") + _lines(out, "FAIL:")), out


# ── 배선 — 자리와 순서 ─────────────────────────────────────────────────────────────────────────────
def _at(needle: str) -> int:
    assert needle in UA, f"`{needle}` 가 없다"
    return UA.index(needle)


def test_update_all_배선():
    assert _at('. "$SELF_REPO/infra/scripts/lib/llm-pool.sh"') < _at('hr "1) 포털 레포 최신화"'), "lib 는 첫 § 머리 전에 적재한다"
    assert _at('hr "1h) 리스크 검토 비우기"') < _at("# ── 1i) LLM 라우터") < _at('hr "2) deploy-all-from-drive'), \
        "1i 는 1h(비우기 창 안) 뒤, §2(사본을 읽는 재기동) 앞이다"
    us4 = _at('"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server; _us_rc=$?')
    assert us4 < _at("# 1i 의 뒤처리") < _at('hr "5) 게이트웨이 config 정합'), "라우터 내리기는 §4 의 재기동 뒤다"
    assert _at('hr "6) 헬스게이트"') < _at("# LLM 라우터 — 풀이 켜진 박스만") < _at('hr "6b)'), "라우터 한 줄은 §6 안이다"
    head = UA[:UA.index("set -uo pipefail")]
    assert "LLM_ROUTER_RESTART_FORCE=1" in head and "LLM_UPSTREAMS" in head, "강행 손잡이와 켜는 줄이 사용법에 있다"
    for line in (_block_1i() + _block_retire() + _block_s6()).splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"


def test_다시_띄우는_자리라고_말한_곳의_지문에_그_env_가_들어_있다():
    """1i 는 '§2·§4 가 다시 띄우며 읽는다' 고 말한다 — 그 자리들이 그 .env 를 재기동 지문에 넣고 있어야 참이다(넣지 않으면 사본만 바뀌고
    서비스는 '변경 없음' 으로 재기동을 생략해 옛 주소로 돈다 — LP-D4 의 무음 결함이 그대로 돌아온다)."""
    deploy = (SCRIPTS / "deploy-all-from-drive.sh").read_text(encoding="utf-8")
    for fp in ("hwax_fp infra/apptainer/*.sif .env)",                     # mxwp — MXWhitePaper/.env
               "hwax_fp frontend/dist var/sifs .env ",                    # heax — HEAXHub/.env(HEAX_APP_LLM_BASE_URL)
               "hwax_fp apptainer/sif .env)",                             # signalforge — SignalForge/.env
               "hwax_fp deploy/apptainer/.env)"):                         # aidh — AIDataHub/deploy/apptainer/.env
        assert fp in deploy, f"deploy-all 의 지문이 바뀌었다 — 1i 의 _llm_restart_by 가 거짓말을 할 수 있다: {fp}"
    services = (SCRIPTS / "services.py").read_text(encoding="utf-8")
    assert 'for rel in dict.fromkeys([".env", *idents, *fps]):' in services, "update-sites 지문(services.py fp)이 <dir>/.env 를 넣는다"
    assert '"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server' in UA
    script = "\n".join([_region("_llm_restart_by() {", "\n}\n") + "\n}\n",
                        'for s in agent-server ai-data-hub heax-hub signalforge mx-white-paper paper-ingest new-kit; do',
                        '  if _llm_restart_by "$s" >/dev/null; then echo "$s 0"; else echo "$s 1"; fi; done'])
    got = dict(ln.split() for ln in subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.splitlines())
    assert got == {"agent-server": "0", "ai-data-hub": "0", "heax-hub": "0", "signalforge": "0", "mx-white-paper": "0",
                   "paper-ingest": "1", "new-kit": "1"}, got


def test_lib_의_0_아닌_값은_받아서_쓴다():
    """lib 는 1·2 를 정상으로 돌려준다 — set -e 로 바뀌어도 맨 문장으로 받지 않게, 값을 받는 자리는 전부 `|| _x=$?` 또는 조건문이다."""
    pat = re.compile(r"\$\((hwax_llm_pool_upstreams|hwax_llm_router_url|hwax_llm_router_health|hwax_llm_router_busy)\b")
    seen = 0
    for line in (_block_1i() + _block_retire() + _block_s6()).splitlines():
        if pat.search(line) and not line.lstrip().startswith("#"):
            seen += 1
            assert "|| _" in line or line.lstrip().startswith(("elif ", "if ")), line
    assert seen >= 5, "받는 자리를 거의 못 찾았다 — 검사가 헛돈다"
