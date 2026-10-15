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
        # 대역 — 부른 사실(llm-router.sh 는 받은 LLM_ROUTER_PORT 까지)만 적는다. update-sites 는 STUB_US_RC, 그중 llm-router 만 STUB_US_LR_RC 로.
        stubs = {"update-sites.sh": 'rc="${STUB_US_RC:-0}"; [ "$*" = llm-router ] && rc="${STUB_US_LR_RC:-$rc}"',
                 "llm-router.sh": 'rc="${STUB_LR_RC:-0}"'}
        for name, rc_line in stubs.items():
            p = self.repo / "infra/scripts" / name
            p.write_text(f'#!/usr/bin/env bash\necho "{name} $*${{LLM_ROUTER_PORT:+ port=$LLM_ROUTER_PORT}}" >> "{self.calls}"\n'
                         f'echo "  (대역) {name} $*"\n{rc_line}\nexit "$rc"\n')
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

    def backups(self) -> list[Path]:
        """포털의 infra/.state/llm-pool-backups 아래 백업 파일 — 서비스 리포 안이 아니다(H1)."""
        d = self.repo / "infra/.state/llm-pool-backups"
        return sorted(p for p in d.rglob("*") if p.is_file()) if d.is_dir() else []

    def strays(self) -> list[Path]:
        """형제 리포에 생긴 .env 아닌 파일(옛 `.env.bak-*` · 남은 임시 파일)."""
        return sorted(p for p in self.tmp.rglob("*") if p.is_file() and p.parts[len(self.tmp.parts)] not in ("HWAXPortal", "home")
                      and p.name != ".env" and p not in (self.calls, self.ledger))

    def record(self) -> str | None:
        f = self.repo / "infra/.state/llm-pool.router"
        return f.read_text().strip() if f.exists() else None

    def run(self, *, first: bool = True, retire: bool = False, s6: bool = False, pre: str = "", post: str = "",
            blocks: tuple[str, ...] = (), **env) -> str:
        """구획을 원문 그대로 잇는다 — first(1i) → pre(그 사이 일어난 일 — §2·§4 의 결과) → blocks(다른 구획) → retire(§4 뒤 라우터 내리기) → s6."""
        body = (_block_1i() + "\necho \"RETIRE=[$_LLM_RETIRE]\"\n" if first else "") + pre + "".join(blocks)
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
    assert len([ln for ln in _lines(out, "OK:") if f"→ {rurl}" in ln]) == 6, out
    # 백업 — 파일마다 한 줄(AIDataHub 의 키 둘은 백업 하나), 포털 infra/.state 아래 전체 경로와 그 경로로 되돌리는 명령(H1)
    bak_lines = [ln.strip() for ln in out.splitlines() if ln.startswith("    · 백업 ")]
    assert len(bak_lines) == 5 and len(box.backups()) == 5, (bak_lines, box.backups())
    for b in box.backups():
        assert any(f"· 백업 {b} — 파일째 되돌리려면 cp '{b}' '" in ln for ln in bak_lines), (b, bak_lines)
    assert box.strays() == [], f"형제 리포에 백업·임시 파일이 남았다 — {box.strays()}"
    assert "되돌리기 — infra/.env 의 LLM_UPSTREAMS 줄을 지우고" in out
    assert "apply-envs 몫" not in out, "키 없는 사본을 3.5 가 더한다는 말은 다섯 사본에서 거짓이다(L6)"
    assert "· agent-server — §4 update-sites" in out and "· ai-data-hub — §2 deploy-all" in out
    assert "· signalforge — §2" in out and "· mx-white-paper — §2" in out
    pi = [ln for ln in _lines(out, "BAD:") if ln.startswith("BAD:paper-ingest")]
    assert len(pi) == 1 and "다시 띄우지 않는다" in pi[0] and "바꾸기 전 주소를 쓴다" in pi[0], "이번 실행이 안 띄우는 사본은 따로 말한다"
    assert "RETIRE=[]" in out
    assert box.record() == rurl, "1i 가 사본에 적은 라우터 주소를 기록한다(M4)"


@pytest.mark.parametrize("models,needle", [
    ({"match": False, "ids": {"a": ["glm"], "b": ["other"]}, "max_model_len": {}}, "모델·창이 다르다"),
    ({}, "모델 대조 전"),
    ({"match": None, "ids": [], "max_model_len": None}, "모델 대조 전"),
])
def test_모델이_같다고_답하지_않으면_사본을_건드리지_않고_실패로_센다(box, router, models, needle):
    """**M5 회귀** — 다른 모델로 재기동한 서버는 요청마다 빨리 실패해 한가해 보이고 요청을 다 받는다. 올라온 서버가 있어도 모델이 같다고
    답할 때만 사본을 바꾼다. 다르면 ✗, 기다려도 대조 전이면 ✗('모델 대조 전'). 기록도 하지 않는다."""
    router["body"] = _ok_body(models=models, status="degraded" if models.get("match") is False else "ok")
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put(ALL_DIRECT)
    before = box.snapshot()
    out = box.run()
    assert box.snapshot() == before and box.backups() == [] and box.record() is None, out
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and needle in fails[0] and "사본을 라우터로 바꾸지 않았다" in fails[0], out


def test_모델_대조가_끝나기를_기다렸다가_같으면_바꾼다(box, router):
    """막 뜬 라우터는 서버가 올라온 뒤에도 잠깐 모델을 모른다 — 그 동안은 기다린다(대조 전을 '다르다' 로 읽지 않는다)."""
    unknown = _ok_body(models={"match": None, "ids": [], "max_model_len": None})
    router["seq"] = [unknown, unknown]
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT})
    out = box.run(HWAX_LLM_ROUTER_WAIT_S="10")
    assert box.value("agent-server") == f"http://127.0.0.1:{router['port']}/v1" and router["hits"] >= 3, out
    assert not _lines(out, "FAIL:")


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
    snap, baks = box.snapshot(), box.backups()
    out = box.run()
    assert box.snapshot() == snap and box.backups() == baks, "두 번째 실행이 파일을 쓰거나 백업을 늘렸다"
    assert "바꿈 0 · 이미 그 주소 7" in out and "되돌리기" not in out, out


def test_사본_바꾸기가_도중에_죽으면_실패로_센다(box, router):
    """**L4 회귀** — lib 의 종료코드를 보지 않아, 사본을 바꾸다 죽어도 1i 가 초록으로 지나갔다. 줄을 낸 앞 파일은 ✓ 로 말하고, 끝까지 못
    간 사실은 ✗ 로 센다. 두 번째 파일의 이름 바꾸기에서 죽는 python3 를 PATH 앞에 세운다."""
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT, "aidh-openai": DIRECT})
    shim = box.home / "shim"; shim.mkdir()
    (shim / "python3").write_text(
        "#!/usr/bin/env bash\n"
        f'exec "{shutil.which("python3")}" -c \'import os, sys\n'
        "real = os.replace; n = [0]\n"
        "def flaky(a, b):\n"
        "    n[0] += 1\n"
        "    if n[0] == 2: raise RuntimeError(\"boom\")\n"
        "    return real(a, b)\n"
        "os.replace = flaky\n"
        "exec(compile(sys.stdin.read(), \"<lib>\", \"exec\"), {\"__name__\": \"__main__\"})\n"
        "' \"${@:2}\"\n")
    (shim / "python3").chmod(0o755)
    out = box.run(PATH=f"{shim}:{os.environ['PATH']}")
    assert "RuntimeError" in out, "대역이 죽지 않았다 — 시험이 헛돈다"
    assert any(ln.startswith("OK:HWAXAgentServer/.env  VLLM_BASE_URL") for ln in _lines(out, "OK:")), "죽기 전에 바꾼 사본은 말한다"
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "끝까지 가지 못했다" in fails[0], out


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
    assert f"RETIRE=[{rurl}]" in out and box.called() == [f"llm-router.sh stop port={router['port']}"], (box.called(), out)
    assert not _lines(out, "BAD:HEAXHub"), "끌 때는 관리 밖 사본을 다시 알리지 않는다(풀과 무관하다)"
    assert any("LLM 라우터(:" in ln and "내렸다" in ln for ln in _lines(out, "OK:")) and not _lines(out, "FAIL:"), out
    assert out.index(f"RETIRE=[{rurl}]") < out.index("(대역) llm-router.sh stop"), "내리는 것은 1i 가 아니라 §4 뒤다"
    assert rurl not in "".join(p.read_text() for p in box.snapshot())
    assert box.strays() == [] and len(box.backups()) == 2, "되돌릴 때도 백업은 포털 infra/.state 에만"


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
    assert box.called() == [f"llm-router.sh stop port={router['port']}"], out


@pytest.mark.parametrize("case", ["미룬 재기동", "§2 실패", "§4 미룸"])
def test_강행은_도는_요청_검사만_넘는다(box, router, case):
    """**L2 회귀** — 강행이 미룬 재기동 검사까지 넘어, 심의 때문에 재기동을 미룬 옛 에이전트 서버가 아직 쓰는 라우터를 내렸다. 강행은 도는
    요청(스트림) 검사 하나만 넘는다 — 나머지는 옛 주소를 쥔 프로세스가 아직 있다는 뜻이다."""
    _off(box, router)
    pre = {"미룬 재기동": '_DA_RC=0; _us_rc=3\nhwax_skip_record "agent-server 재기동 건너뜀" "심의 2건 진행 중" "끝난 뒤"\n',
           "§2 실패": "_DA_RC=4; _us_rc=0\n", "§4 미룸": "_DA_RC=0; _us_rc=3\n"}[case]
    out = box.run(retire=True, pre=pre, LLM_ROUTER_RESTART_FORCE="1")
    assert box.value("agent-server") == DIRECT and box.called() == [], (box.called(), out)
    skip = [ln for ln in box.ledger.read_text().splitlines() if ln.startswith("LLM 라우터 내리기 미룸")]
    assert len(skip) == 1 and "LLM_ROUTER_RESTART_FORCE" not in skip[0], "강행으로 풀리지 않는 미룸에 강행을 권하지 않는다"
    assert f"LLM_ROUTER_PORT={router['port']} ./infra/scripts/llm-router.sh stop" in skip[0], "손으로 내리는 명령(그 포트)"


def test_사용법이_강행의_범위를_말한다():
    head = UA[:UA.index("set -uo pipefail")]
    i = head.index("LLM_ROUTER_RESTART_FORCE=1")
    usage = head[i:i + 600]
    assert "도는 요청 검사 하나뿐" in usage and "재기동을 미룬 서비스" in usage and "사본이 아직 라우터를 가리키면 미룬다" in usage, usage


def test_라우터를_가리키는_사본이_남으면_강행해도_내리지_않는다(box, router):
    _off(box, router)
    pre = f'_DA_RC=0; _us_rc=0\nprintf "VLLM_BASE_URL=http://127.0.0.1:{router["port"]}/v1\\n" >> "{box.copy("agent-server")}"\n'
    out = box.run(retire=True, pre=pre, LLM_ROUTER_RESTART_FORCE="1")
    assert box.called() == [] and "사본 1곳이 아직 이 라우터를 가리킨다" in box.ledger.read_text(), out


def test_끌_때_이번_실행이_안_띄우는_사본은_라우터가_내려가면_끊긴다고_말한다(box, router):
    """**L6 회귀** — PaperIngest 를 손으로 띄운 프로세스는 이번 실행이 다시 띄우지 않는다. 라우터를 §4 뒤에 내리므로 '라우터 주소를 계속
    쓴다' 고만 말하면 거짓이다 — 그 뒤로 그 호출은 실패한다."""
    rurl = _off(box, router, values={"paper-ingest": f"http://127.0.0.1:{router['port']}/v1"})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    pi = [ln for ln in _lines(out, "BAD:") if ln.startswith("BAD:paper-ingest")]
    assert len(pi) == 1 and "§4 뒤에 내리므로" in pi[0] and "실패한다" in pi[0], out
    assert box.value("paper-ingest") == DIRECT and box.called() == [f"llm-router.sh stop port={router['port']}"], rurl


# ── 포트를 바꾸거나 함께 지웠을 때 — 1i 가 기록한 라우터 주소(M4) ────────────────────────────────────────
@pytest.fixture()
def old_router():
    """옛 포트에 떠 있는 라우터(사본이 가리키는 곳) — 지어낸 /health."""
    state = {"body": _ok_body(), "hits": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            body = state["body"]
            if self.path != "/health" or body is None:
                self.send_response(404); self.end_headers(); return
            raw = json.dumps(body).encode()
            self.send_response(503 if body.get("status") == "down" else 200)
            self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["port"] = srv.server_address[1]; state["url"] = f"http://127.0.0.1:{state['port']}/v1"
    yield state
    srv.shutdown(); srv.server_close()


def _recorded(box: Box, url: str):
    f = box.repo / "infra/.state/llm-pool.router"; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(url + "\n")


def test_풀과_포트_줄을_함께_지우면_기록한_옛_포트의_사본을_되돌리고_그_라우터를_내린다(box, old_router):
    """**M4 회귀** — 사용자 포트 A 로 켠 풀을 줄 둘 다 지워 끄면 포트가 9130 으로 돌아가, 옛 포트 A 의 사본을 못 찾고(○ '직접 주소를 본다'
    — 거짓) 라우터도 안 내렸다. 재부팅 뒤 그 사본들은 죽은 포트를 보는데 검사는 전부 초록이었다. 기록한 주소까지 관리 값이다."""
    _recorded(box, old_router["url"])
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")   # 지운 자리 — 기본 포트(아무도 안 듣는다)의 대역
    box.put({"agent-server": old_router["url"], "signalforge": old_router["url"], "aidh-openai": DIRECT})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.value("agent-server") == DIRECT and box.value("signalforge") == DIRECT and box.value("aidh-openai") == DIRECT, out
    assert f"RETIRE=[{old_router['url']}]" in out
    assert box.called() == [f"llm-router.sh stop port={old_router['port']}"], box.called()
    assert not _lines(out, "FAIL:") and "LLM 서버 풀(라우터)" not in box.ledger.read_text(), "아무것도 없다는 ○ 는 거짓이다"


def test_끄기를_미룬_옛_포트의_라우터는_다음_실행이_다시_본다(box, old_router):
    _recorded(box, old_router["url"])
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")
    box.put({"agent-server": old_router["url"]})
    old_router["body"] = _ok_body(inflight=1)
    box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.called() == [] and box.value("agent-server") == DIRECT and box.record() == old_router["url"], "기록은 끈 뒤에도 남는다"
    old_router["body"] = _ok_body(inflight=0)
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.called() == [f"llm-router.sh stop port={old_router['port']}"], out


def test_풀이_켜진_채_포트를_바꾸면_옛_포트의_사본을_새_라우터로_옮긴다(box, router, old_router):
    """**M4 회귀** — 포트를 바꾸면 옛 포트를 가리키는 사본은 ⚠ 만 받고 §6 도 세지 않았다. 기록한 옛 주소도 관리 값이라 새 라우터로 옮기고,
    기록을 새 주소로 바꾼다. 옛 라우터는 이 실행이 내리지 않는다 — 손으로 내리는 명령을 ⚠ 로 남긴다."""
    _recorded(box, old_router["url"])
    new = f"http://127.0.0.1:{router['port']}/v1"
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": old_router["url"], "signalforge": DIRECT, "heax-hub": FOREIGN})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.value("agent-server") == new and box.value("signalforge") == new and box.value("heax-hub") == FOREIGN, out
    assert not [ln for ln in _lines(out, "BAD:") if old_router["url"] in ln and "관리하는 주소가 아니다" in ln]
    assert box.record() == new and box.called() == ["update-sites.sh llm-router"], box.called()
    warn = [ln for ln in _lines(out, "BAD:") if "옛 포트" in ln]
    assert len(warn) == 1 and f"LLM_ROUTER_PORT={old_router['port']} ./infra/scripts/llm-router.sh stop" in warn[0], out


def test_포트를_바꿨는데_옛_라우터가_없으면_말하지_않는다(box, router):
    _recorded(box, f"http://127.0.0.1:{_dead_port()}/v1")
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT})
    out = box.run()
    assert not [ln for ln in _lines(out, "BAD:") if "옛 포트" in ln] and box.record() == f"http://127.0.0.1:{router['port']}/v1"


@pytest.mark.skipif(os.geteuid() == 0, reason="root 는 파일 권한을 무시한다")
def test_옛_주소의_사본을_못_옮기면_기록을_그대로_둔다(box, router, old_router):
    """옛 주소는 이 기록에만 있다 — 그 사본이 남았는데 기록을 새 주소로 바꾸면 그 사본을 영영 못 찾는다(끌 때도 되돌리지 못한다)."""
    _recorded(box, old_router["url"])
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": old_router["url"]})
    box.copy("agent-server").chmod(0o444)
    try:
        out = box.run()
    finally:
        box.copy("agent-server").chmod(0o644)
    assert box.value("agent-server") == old_router["url"] and box.record() == old_router["url"], out
    assert any("기록은 옛 주소 그대로" in ln for ln in _lines(out, "BAD:")) and _lines(out, "FAIL:"), out


def test_되돌릴_직접_주소가_없으면_사본도_라우터도_그대로(box, router):
    rurl = _off(box, router, direct=None)
    before = box.snapshot()
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert box.snapshot() == before and box.called() == [] and "RETIRE=[]" in out
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "LLM_BASE_URL" in fails[0] and box.value("agent-server") == rurl


def test_사본은_되돌렸고_라우터만_남았으면_다음_실행이_내린다(box, router):
    """미룬 뒤의 실행 — 사본은 이미 직접 주소다. 라우터가 아직 떠 있으면 내린다."""
    _off(box, router, values={"agent-server": DIRECT})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert "HR:1i) LLM 라우터 — 풀 꺼짐" in out and box.called() == [f"llm-router.sh stop port={router['port']}"]


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
    assert box.called() == [] and "RETIRE=[]" in out and "LLM 서버 풀(라우터)" in out


# ── 물려받은 라우터 포트(2라운드 LOW 6 · LP-D14) ──────────────────────────────────────────────────────────
def test_물려받은_라우터_포트를_버린다():
    """**2라운드 LOW 6** — 운영자 셸에 export 된 LLM_ROUTER_PORT 가 update-sites → services.py down → llm-router.sh stop 으로 흘러, 옛 포트의
    라우터를 내리고 지금 포트의 라우터는 못 내릴 수 있었다(stop 은 환경의 포트가 먼저다). update-all 머리가 버린다 — 손으로 내릴 때의
    한 번짜리 `LLM_ROUTER_PORT=<포트> … stop` 은 그대로 된다."""
    head = UA[:UA.index('SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"')]
    script = head + ('\necho "[${LLM_ROUTER_PORT-없음}]"\nbash -c \'echo "[${LLM_ROUTER_PORT-없음}]"\'\n'
                     'LLM_ROUTER_PORT=7777 bash -c \'echo "[$LLM_ROUTER_PORT]"\'\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                       env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "LLM_ROUTER_PORT": "9555"})
    assert r.stdout.split() == ["[없음]", "[없음]", "[7777]"], r.stdout + r.stderr


# ── 이름 바꾸기 대신 제자리에 쓴 사본(2라운드 LOW 4 · LP-D14) ─────────────────────────────────────────────
def test_제자리에_쓴_사본은_그렇게_말한다(box, router):
    """하드 링크가 둘인 사본은 이름 바꾸기 대신 제자리에 쓴다(LOW 4) — ✓ 줄이 그 사실과 까닭을 말한다(다른 이름도 함께 바뀐다)."""
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT})
    agent = box.copy("agent-server"); other = box.home / "agent-shared.env"; os.link(agent, other)
    out = box.run()
    mine = [ln for ln in _lines(out, "OK:") if ln.startswith("OK:HWAXAgentServer/.env  VLLM_BASE_URL")]
    assert len(mine) == 1 and "제자리에 썼다" in mine[0] and "하드 링크" in mine[0], out
    assert other.read_text() == agent.read_text() and f"http://127.0.0.1:{router['port']}/v1" in other.read_text()


# ── 사본을 셀 수 없을 때(2라운드 M-D · LP-D14) — 어느 자리든 '가리킬 수 있다' 로 읽는다 ─────────────────────────────────────
def _dry_fails(box: Box) -> str:
    """사본 lib 의 dry(세기)만 죽는 python3 를 PATH 앞에 세운다 — write(바꾸기)와 /health 읽기는 그대로 돈다. 세기가 실패한 자리마다 0 이 아니라
    '모른다' 로 읽는지 본다."""
    shim = box.home / "shim-dry"; shim.mkdir(exist_ok=True)
    (shim / "python3").write_text("#!/usr/bin/env bash\n"
                                  'if [ "${HWAX_LLM_MODE:-}" = dry ]; then echo "(대역) 세기 실패" >&2; exit 7; fi\n'
                                  f'exec "{shutil.which("python3")}" "$@"\n')
    (shim / "python3").chmod(0o755)
    return f"{shim}:{os.environ['PATH']}"


def test_임시_파일을_못_만드는_박스에서_풀을_꺼도_라우터를_내리지_않는다(box, router):
    """**2라운드 M-D 회귀(검토 탐침 probe_count_failopen 그대로)** — /tmp 가 차 bash 가 lib 의 파이썬 here-doc 임시 파일을 못 만들면(ulimit -f 1)
    사본 수가 0 으로 읽혀, 1i 는 사본을 안 되돌리고 ✗ 도 없었고, 뒤처리는 '✓ … 사본은 직접 주소다' 를 찍고 사본 둘이 아직 가리키는 라우터를
    내렸다. 이제 1i 와 뒤처리가 각각 ✗ 와 사유를 내고 라우터는 그대로다."""
    rurl = f"http://127.0.0.1:{router['port']}/v1"
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": DIRECT, "signalforge": DIRECT})
    box.run()
    assert box.value("agent-server") == rurl and box.value("signalforge") == rurl
    box.env(f"LLM_ROUTER_PORT={router['port']}\nLLM_BASE_URL={DIRECT}\n")              # 풀을 끈다
    out = box.run(first=False, pre="ulimit -f 1\n" + _block_1i() + '\necho "RETIRE=[$_LLM_RETIRE]"\n_DA_RC=0; _us_rc=0\n', retire=True)
    assert "here-document" in out, "lib 이 실패하지 않았다 — 시험이 헛돈다"
    assert [c for c in box.called() if c.startswith("llm-router.sh stop")] == [], f"사본이 가리키는데 라우터를 내렸다 — {box.called()}"
    assert not [ln for ln in _lines(out, "OK:") if "내렸다" in ln], out
    fails = _lines(out, "FAIL:")
    assert any("라우터를 가리키는 LLM 주소 사본을 세지 못했다" in ln for ln in fails), out
    assert any(f"LLM 라우터(:{router['port']})를 내리지 않았다" in ln and "세지 못했다" in ln for ln in fails), out
    assert "LLM 서버 풀(라우터)" not in box.ledger.read_text(), "'사본들이 직접 본다' ○ 는 거짓일 수 있다"


def test_풀을_끌_때_셀_수_없으면_되돌릴_수_있는_사본은_되돌리되_라우터는_내리지_않는다(box, router):
    rurl = _off(box, router)
    _recorded(box, rurl)          # 기록이 있다(지금 라우터) — 기록 없음의 루프백 점검(LOW 7)이 이 세기 실패를 대신 잡지 않게
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n", PATH=_dry_fails(box))
    assert "(대역) 세기 실패" in out, "세기가 죽지 않았다 — 시험이 헛돈다"
    assert box.value("agent-server") == DIRECT and box.value("aidh-openai") == DIRECT, "가리킬 수 있으면 되돌리기는 한다"
    assert box.called() == [], f"셀 수 없는데 라우터를 내렸다 — {box.called()}"
    assert f"RETIRE=[{rurl}]" in out
    fails = _lines(out, "FAIL:")
    assert len(fails) == 2 and "세지 못했다" in fails[0] and f"(:{router['port']})를 내리지 않았다" in fails[1], out
    assert "LLM 서버 풀(라우터)" not in box.ledger.read_text() and "LLM 라우터 내리기 미룸" not in box.ledger.read_text(), \
        "셀 수 없는 것은 미룸(○)이 아니라 실패(✗)다"


def test_옛_주소의_사본을_셀_수_없으면_기록을_덮지_않는다(box, router, old_router):
    """옛 라우터 주소는 이 기록에만 있다 — 그 주소의 사본이 남았는지 모르는데 기록을 새 주소로 바꾸면 그 사본을 영영 못 찾는다(M-D)."""
    _recorded(box, old_router["url"])
    new = f"http://127.0.0.1:{router['port']}/v1"
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": old_router["url"]})
    out = box.run(PATH=_dry_fails(box))
    assert "(대역) 세기 실패" in out and box.value("agent-server") == new, out
    assert box.record() == old_router["url"], "셀 수 없는데 기록을 새 주소로 덮었다"
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and old_router["url"] in fails[0] and "세지 못했다" in fails[0] and "기록은 옛 주소 그대로" in fails[0], out


def test_라우터가_쓸_수_없을_때_사본을_셀_수_없으면_그렇게_말한다(box, router):
    router["body"] = _ok_body(status="down", upstreams_up=0)
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1}\nLLM_ROUTER_PORT={router['port']}\n")
    box.put({"agent-server": f"http://127.0.0.1:{router['port']}/v1"})
    out = box.run(PATH=_dry_fails(box))
    fails = _lines(out, "FAIL:")
    assert len(fails) == 1 and "라우터를 가리키는 사본을 세지 못했다" in fails[0] and "지금 실패한다" in fails[0], out


@pytest.mark.parametrize("which", ["지금 라우터", "옛 라우터"])
def test_6장_은_사본을_셀_수_없으면_직접_주소라고_말하지_않는다(box, router, old_router, which):
    """**2라운드 M-D 회귀** — §6 은 세기가 실패해도 0 으로 읽어 '사본은 직접 주소 그대로라 LLM 은 돈다' 고 말했다. 이제 ✗ 와 사유다."""
    if which == "지금 라우터":
        router["body"] = _ok_body(status="down", upstreams_up=0)
        box.env(f"LLM_UPSTREAMS={S1},{S2}\nLLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={router['port']}\n")
        box.put({"agent-server": f"http://127.0.0.1:{router['port']}/v1"})
    else:
        _recorded(box, old_router["url"])
        box.env(f"LLM_UPSTREAMS={S1},{S2}\nLLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")
        box.put({"agent-server": old_router["url"]})
    out = box.run(first=False, s6=True, PATH=_dry_fails(box))
    assert not [ln for ln in _lines(out, "BAD:") if "직접 주소 그대로라" in ln], out
    mine = [ln for ln in _lines(out, "FAIL:") if "LLM 라우터" in ln and "세지 못했다" in ln]
    want = "옛 라우터(" if which == "옛 라우터" else "라우터를 가리키는 사본을 세지 못했다"
    assert any(want in ln for ln in mine), out


# ── 풀이 꺼졌는데 라우터 기록이 없을 때(2라운드 LOW 7 · LP-D14) ────────────────────────────────────────────
@pytest.mark.parametrize("record", ["없다", "모양이 틀렸다",
                                    pytest.param("못 읽는다", marks=pytest.mark.skipif(os.geteuid() == 0, reason="root 는 권한을 무시한다"))])
def test_기록이_없으면_아무것도_듣지_않는_루프백_사본을_알리되_고치지_않는다(box, record):
    """**2라운드 LOW 7 회귀(검토 탐침 corrupt)** — 기록을 잃으면(지웠다 · 손으로 고쳤다 · 못 읽는다) 옛 라우터 주소를 몰라, 죽은 라우터를
    가리키는 사본을 두고 ○ '사본들이 LLM_BASE_URL 을 직접 본다' 였다. 이제 루프백 /v1 인데 아무것도 듣지 않는 사본을 ⚠ 로 하나씩 알린다 —
    고치지 않는다(이 박스의 로컬 vLLM 일 수 있다). 되돌리는 길(그 주소를 기록에 적고 재실행)을 함께 말한다."""
    dead = f"http://127.0.0.1:{_dead_port()}/v1"
    f = box.repo / "infra/.state/llm-pool.router"
    if record == "모양이 틀렸다":
        _recorded(box, dead.replace("127.0.0.1", "localhost"))
    elif record == "못 읽는다":
        _recorded(box, dead); f.chmod(0)
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")
    box.put({"agent-server": dead, "signalforge": DIRECT, "heax-hub": FOREIGN})
    before = box.snapshot()
    try:
        out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    finally:
        if f.exists():
            f.chmod(0o644)
    assert box.snapshot() == before and box.called() == [], "알리기만 한다 — 옛 라우터인지 로컬 vLLM 인지 모른다"
    warns = [ln for ln in _lines(out, "BAD:") if "아무것도 듣지 않는다" in ln]
    assert len(warns) == 1 and f"HWAXAgentServer/.env  VLLM_BASE_URL={dead} " in warns[0], out
    assert f"'{dead}' > '{box.repo}/infra/.state/llm-pool.router'" in warns[0] and "고치지 않는다" in warns[0], warns[0]
    first = box.ledger.read_text().splitlines()[0]
    assert first.startswith("LLM 서버 풀(라우터)\t") and "직접 본다" not in first and "위 ⚠" in first, first
    assert not _lines(out, "FAIL:"), out


def test_듣고_있는_루프백과_직접_주소는_알리지_않는다(box, router):
    """로컬 vLLM 을 루프백으로 쓰는 dev 박스 — 그 포트에 무언가 들으면 ⚠ 가 없다. 직접 주소(LLM_BASE_URL)와 같은 값은 풀과 무관하다(꺼져
    있어도 — 그것은 LLM 자체의 일이다)."""
    direct = f"http://127.0.0.1:{_dead_port()}/v1"
    box.env(f"LLM_BASE_URL={direct}\nLLM_ROUTER_PORT={_dead_port()}\n")
    box.put({"agent-server": direct, "signalforge": f"http://127.0.0.1:{router['port']}/v1"})
    out = box.run(retire=True, pre="_DA_RC=0; _us_rc=0\n")
    assert not [ln for ln in _lines(out, "BAD:") if "듣지 않는다" in ln] and not _lines(out, "HR:"), out
    assert "직접 본다" in box.ledger.read_text().splitlines()[0]


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


@pytest.mark.parametrize("old_alive", [True, False])
def test_6장_은_옛_라우터를_가리키는_사본도_센다(box, router, old_router, old_alive):
    """**M4 회귀** — 포트를 바꿨는데 새 라우터가 쓸 만하지 않아 1i 가 사본을 못 옮기면, §6 은 지금 포트만 세어 '사본은 직접 주소 그대로라
    LLM 은 돈다' 고 말했다(거짓). 기록한 옛 주소의 사본도 센다 — 옛 라우터가 답하면 ⚠, 아니면 그 서비스들의 LLM 이 실패한다 ✗."""
    _recorded(box, old_router["url"])
    if not old_alive:
        old_router["body"] = None
    box.env(f"LLM_UPSTREAMS={S1},{S2}\nLLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={_dead_port()}\n")   # 새 포트에는 아무도 없다
    box.put({"agent-server": old_router["url"], "signalforge": old_router["url"]})
    out = box.run(first=False, s6=True)
    mine = [ln for ln in _lines(out, "BAD:") + _lines(out, "FAIL:") if "곳이 옛 라우터(" in ln]
    assert len(mine) == 1 and "사본 2곳" in mine[0], out
    assert mine[0].startswith("BAD:" if old_alive else "FAIL:"), mine
    assert not [ln for ln in _lines(out, "BAD:") if "직접 주소 그대로라 LLM 은 돈다" in ln], "옛 라우터의 사본을 직접 주소로 읽었다"


# ── §3.5 — 라우터 주소는 원격 LLM 이다(M3) ─────────────────────────────────────────────────────────────
def _block_35() -> str:
    return _region("# ── 3.5) agent-server .env 자동 보정", "# ── 4) 챗 스택만")


@pytest.mark.parametrize("vb,tm,want", [
    ("ROUTER", None, "0"), ("ROUTER", "40", "0"), ("ROUTER", "0", "0"), ("ROUTER/", None, "0"), ('"ROUTER"', None, "0"),
    ("RECORDED", None, "0"),                                   # 1i 가 기록한 라우터 주소도 라우터다
    (DIRECT, None, "0"), (DIRECT, "40", "0"),                   # 원격 GLM 직접 — 종전 그대로
    ("http://127.0.0.1:8000/v1", "40", None), ("http://127.0.0.1:8000/v1", None, None),   # 로컬 vLLM — 종전 그대로(기본 80)
])
def test_3장5_는_라우터_주소를_원격_LLM_으로_읽는다(box, router, old_router, vb, tm, want):
    """**M3 회귀** — 라우터 주소(127.0.0.1)를 로컬 LLM 으로 읽어, 사본이 라우터로 가는 순간 원격 GLM 의 TOOL_MAX=0 이 빠지고(없으면 안 더하고
    40 은 지워 기본 80) TOOL_MAX=0 이 있어도 '미설정 → 기본 80' 이라고 찍었다. 3.5 구획을 원문 그대로 돌린다(apply-envs 는 임시 박스의 사본)."""
    _recorded(box, old_router["url"])
    box.env(f"LLM_BASE_URL={DIRECT}\nLLM_ROUTER_PORT={router['port']}\n")
    val = vb.replace("RECORDED", old_router["url"]).replace("ROUTER", f"http://127.0.0.1:{router['port']}/v1")
    agent = box.copy("agent-server")
    agent.write_text(f"VLLM_BASE_URL={val}\n" + (f"TOOL_MAX={tm}\n" if tm is not None else ""))
    out = box.run(first=False, pre=f'AGENT_DIR="{agent.parent}"\n', blocks=(_block_35(),))
    got = re.findall(r"^TOOL_MAX=(.*)$", agent.read_text(), re.M)
    assert got == ([want] if want is not None else []), (got, out)
    assert "TOOL_MAX 미설정" not in out or want is None, "TOOL_MAX=0 이 있는데 '미설정 → 기본 80' 이라고 말했다"


# ── §4 — §2 뒤에 라우터를 한 번 더 본다(M2) ────────────────────────────────────────────────────────────
def _block_4() -> str:
    return _region('hr "4) update-sites', "# 1i 의 뒤처리")


@pytest.mark.parametrize("pool,lr_rc,want_fail", [(True, "0", False), (True, "3", False), (True, "1", True), (False, "0", False)])
def test_4장_은_풀이_켜져_있으면_라우터부터_한_번_더_본다(box, pool, lr_rc, want_fail):
    """**M2 회귀** — 라우터는 portal.sif 로 도는데 §2 가 그 SIF 를 바꿔도 라우터는 그 실행에서 다시 뜨지 않았다(1i 의 update-sites 는 §2 앞).
    §4 머리에서 챗 스택보다 먼저 update-sites llm-router 를 한 번 더 부른다(지문에 portal.sif 가 들어 바뀌었으면 다시 뜬다 — 미룸 규율 그대로).
    실패는 ✗ 로 세고 챗 스택은 그대로 간다. 풀이 꺼져 있으면 부르지 않는다."""
    pre = ("_llm_ups_rc=0; _llm_router_rc=0\n" if pool else "_llm_ups_rc=1; _llm_router_rc=0\n")
    out = box.run(first=False, pre=pre, blocks=(_block_4(),), STUB_US_LR_RC=lr_rc)
    chat = "update-sites.sh signalforge-mcp mcp-gateway agent-server"
    assert box.called() == (["update-sites.sh llm-router", chat] if pool else [chat]), box.called()
    fails = [ln for ln in _lines(out, "FAIL:") if "LLM 라우터" in ln]
    assert bool(fails) == want_fail and (not fails or "§2 뒤에" in fails[0]), out


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
    lr4 = _at('"$SELF_REPO/infra/scripts/update-sites.sh" llm-router; _llm_us4_rc=$?')
    assert _at('hr "2) deploy-all-from-drive') < _at('hr "4) update-sites') < lr4 < us4, \
        "라우터를 한 번 더 보는 것은 §2(portal.sif 를 바꾼다) 뒤 · §4 머리 · 챗 스택 앞이다(M2)"
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
