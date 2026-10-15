# LLM 서버 풀 lib(infra/scripts/lib/llm-pool.sh)의 규칙 — 목록 검사 · 라우터 주소 · /health 읽기 · 지금 써야 할 주소 · 사본 목록 · 사본 바꾸기
"""왜 — LLM 주소는 정본(infra/.env 의 LLM_BASE_URL) 하나와 서비스마다의 사본(.env)으로 흩어져 있고, 설정 킷은 없는 키만 더한다. 풀을 켜고
끌 때 사본을 함께 바꾸는 규칙이 이 lib 한 곳에 있다(docs/llm-pool LP-D4). 사본은 운영 박스의 비밀 파일이다 — 관리하는 값만 바꾸고,
바꾸기 전에 백업하고, 값의 글자 말고는 한 바이트도 건드리지 않는지 실제로 돌려 본다.

⚠ 실물을 건드리면 안 된다 — 사본은 형제 리포의 .env 다. lib 는 리포를 <포털 상위>/ → ~/Projects/ → ~/claude/ 순으로 찾으므로 하네스는
HOME 을 임시 디렉터리로 바꾸고, 포털 사본을 임시 디렉터리에 두고, 돌린 뒤 결과의 리포 경로가 전부 임시 디렉터리 안인지 단언한다.
주소는 TEST-NET(203.0.113.x · 198.51.100.x)과 지어낸 이름만 쓴다 — 내부 IP 는 추적 파일 금지.
"""
import http.server
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/llm-pool.sh"
KITS = ROOT / "infra/env-kits"
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
NOT_ROOT = pytest.mark.skipif(os.geteuid() == 0, reason="root 는 파일 권한을 무시한다 — chmod 로 쓰기 실패를 만들 수 없다")

S1, S2 = "http://203.0.113.11:10000/v1", "http://203.0.113.12:10000/v1"     # 두 서버(같은 모델)
DIRECT = "http://203.0.113.11:10000/v1"                                     # 지금 직접 주소(= 서버 1)


def _dead_port() -> int:
    """아무것도 듣지 않는 포트 — 잠깐 열었다 닫는다(실물 9130 을 두드리지 않게)."""
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


@pytest.fixture()
def router():
    """지어낸 라우터 /health — state['body'](dict·문자열, None 이면 404)를 state['code'] 로 답하고 요청 수를 센다."""
    state = {"body": {"status": "ok", "upstreams_total": 2, "upstreams_up": 2, "inflight": 0,
                      "models": {"match": True, "ids": ["glm"], "max_model_len": 1048576}, "config_mtime": 1.0},
             "code": 200, "hits": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            state["hits"] += 1
            body = state["body"]
            if body is None or self.path != "/health":
                self.send_response(404); self.end_headers(); return
            raw = (body if isinstance(body, str) else json.dumps(body)).encode()
            self.send_response(state["code"]); self.send_header("content-type", "application/json"); self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["port"] = srv.server_address[1]
    state["url"] = f"http://127.0.0.1:{state['port']}/health"
    yield state
    srv.shutdown(); srv.server_close()


def _sh(script: str, home: Path, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8", **env})


def _fn(src: str, name: str) -> str:
    s = src[src.index(f"{name}() {{"):]
    return s[:s.index("\n}\n") + 3]


# ── 값 읽기 — update-all 의 _envfile_value 와 글자 단위로 같다 ─────────────────────────────────────────
TRICKY = ["K=a", "K=  a  ", "K=a   # 설명", "K=   # 값 없이 주석만", 'K="a b"', "K='a'", "export K=a", "  export   K=a",
          "K=a\r", "K=a#b", "K=a\nK=b", "K=a\n# K=b", "#K=a", "K=", "OTHER=x", 'K="http://x/v1"   # 한글 주석']


@pytest.mark.parametrize("text", TRICKY)
def test_값_읽기가_update_all_의_독자와_같다(tmp_path, text):
    """라우터·update-all·services.py 가 같은 파일을 같은 규칙으로 읽어야 한다 — 둘이 다르게 읽으면 한쪽은 '켜짐' 다른 쪽은 '꺼짐' 이 된다
    (RA_HOST 에서 실제로 났던 일 — docs/ra-reconnect). 정본(bash 의 _envfile_value)을 오라클로 쓴다."""
    f = tmp_path / "e.env"; f.write_text(text + "\n", encoding="utf-8")
    ours = _sh(f'. "{LIB}"; printf "[%s]" "$(hwax_llm_envv "{f}" K)"', tmp_path).stdout
    oracle = _sh(f'{_fn(UA, "_envfile_value")}\nprintf "[%s]" "$(_envfile_value "{f}" K)"', tmp_path).stdout
    assert ours == oracle, (text, ours, oracle)


# ── 목록 검사 ────────────────────────────────────────────────────────────────────────────────────────
def _ups(tmp_path: Path, env_text: str) -> tuple[int, list[str]]:
    f = tmp_path / "infra.env"; f.write_text(env_text, encoding="utf-8")
    r = _sh(f'. "{LIB}"\nout="$(hwax_llm_pool_upstreams "{f}")"; rc=$?; echo "rc=$rc"; printf "%s\\n" "$out"', tmp_path)
    assert not r.stderr, r.stderr
    lines = r.stdout.splitlines()
    return int(lines[0][3:]), [ln for ln in lines[1:] if ln]


@pytest.mark.parametrize("text,want", [
    (f"LLM_UPSTREAMS={S1},{S2}\n", [S1, S2]),
    (f"LLM_UPSTREAMS={S1}/,{S2}//\n", [S1, S2]),                                    # 끝 / 를 뗀다
    (f'LLM_UPSTREAMS="{S1} {S2}"\n', [S1, S2]),                                     # 공백은 따옴표 안에서만
    (f'LLM_UPSTREAMS="{S1}, {S2}"   # 두 서버\n', [S1, S2]),
    (f"export LLM_UPSTREAMS={S1}\n", [S1]),                                          # 하나여도 켜짐이다(라우터만 앞에 선다)
    ("LLM_UPSTREAMS=https://llm-a.example/v1,http://llm-b.example:8000/v1\n",
     ["https://llm-a.example/v1", "http://llm-b.example:8000/v1"]),
    (f"LLM_UPSTREAMS=http://127.0.0.1:8000/v1\nLLM_ROUTER_PORT=9555\n", ["http://127.0.0.1:8000/v1"]),   # 같은 박스의 vLLM 도 서버다
    (f"LLM_UPSTREAMS=x\nLLM_UPSTREAMS={S2}\n", [S2]),                                 # 마지막 줄이 이긴다
])
def test_맞는_목록은_서버_주소를_한_줄에_하나_낸다(tmp_path, text, want):
    assert _ups(tmp_path, text) == (0, want)


@pytest.mark.parametrize("text", ["", "OTHER=1\n", "# LLM_UPSTREAMS=\n", "LLM_UPSTREAMS=\n", "LLM_UPSTREAMS=   # ⚠ 값을 운영자가 정해야 한다\n",
                                  f"# LLM_UPSTREAMS={S1}\n"])
def test_없거나_빈_값이면_꺼짐이다(tmp_path, text):
    assert _ups(tmp_path, text) == (1, [])


@pytest.mark.parametrize("text,why", [
    (f"LLM_UPSTREAMS={S1}, {S2}\n", "따옴표 밖"),                 # 포털 start.sh 가 이 파일을 bash 로 소싱한다 — 공백 뒤가 명령이 된다
    (f"LLM_UPSTREAMS={S1} {S2}\n", "따옴표 밖"),
    ("LLM_UPSTREAMS=http://203.0.113.11:10000\n", "/v1"),        # /v1 이 없으면 OpenAI 클라이언트가 틀린 경로를 부른다
    ("LLM_UPSTREAMS=203.0.113.11:10000/v1\n", "/v1"),            # 스킴 없음
    ("LLM_UPSTREAMS=ftp://203.0.113.11/v1\n", "/v1"),
    ("LLM_UPSTREAMS=http://[::1]:8000/v1\n", "IPv6"),
    ("LLM_UPSTREAMS=http://u:p@203.0.113.11:10000/v1\n", "계정"),
    ("LLM_UPSTREAMS=http://203.0.113.11:10000/v1?x=1\n", "/v1"),
    ("LLM_UPSTREAMS=https://llm-a.example/openai/v1\n", "/v1"),  # 경로는 정확히 /v1 — 라우터가 /metrics·/v1/models 를 그 호스트의 뿌리에서 본다
    ("LLM_UPSTREAMS=http://<서버1 주소>:<포트>/v1,http://<서버2 주소>:<포트>/v1\n", "따옴표 밖"),   # .env.example 의 예시를 그대로 풀었다
    ("LLM_UPSTREAMS=http://<서버1>:<포트>/v1\n", "/v1"),
    ("LLM_UPSTREAMS=http://203.0.113.11:70000/v1\n", "1~65535"),
    (f"LLM_UPSTREAMS={S1},{S1}/\n", "두 번"),
    ("LLM_UPSTREAMS=http://127.0.0.1:9130/v1\n", "라우터 자신"),
    ("LLM_UPSTREAMS=http://localhost:9555/v1\nLLM_ROUTER_PORT=9555\n", "라우터 자신"),
    ("LLM_UPSTREAMS=,,\n", "하나도"),
    (f"LLM_UPSTREAMS={S1},http://-bad-.example/v1\n", "/v1"),     # 하나라도 틀리면 줄 전체를 버린다
])
def test_틀린_목록은_사유와_함께_통째로_버린다(tmp_path, text, why):
    rc, out = _ups(tmp_path, text)
    assert rc == 2 and len(out) == 1 and why in out[0], (rc, out)
    assert not any(x.startswith("http") and x == S1 for x in out), "맞는 앞 주소만 골라 내면 반만 맞는 풀이 뜬다"


# ── 라우터 주소 ──────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,rc,out", [
    ("", 0, "http://127.0.0.1:9130/v1"), ("LLM_ROUTER_PORT=9555\n", 0, "http://127.0.0.1:9555/v1"),
    ("LLM_ROUTER_PORT=09555   # 앞 0\n", 0, "http://127.0.0.1:9555/v1"), ("LLM_ROUTER_PORT=\n", 0, "http://127.0.0.1:9130/v1"),
    ("LLM_ROUTER_PORT=abc\n", 2, "LLM_ROUTER_PORT"), ("LLM_ROUTER_PORT=0\n", 2, "LLM_ROUTER_PORT"),
    ("LLM_ROUTER_PORT=70000\n", 2, "LLM_ROUTER_PORT"),
])
def test_라우터_주소는_포트에서_나온다(tmp_path, text, rc, out):
    f = tmp_path / "infra.env"; f.write_text(text)
    r = _sh(f'. "{LIB}"\nu="$(hwax_llm_router_url "{f}")"; echo "rc=$? [$u]"; hwax_llm_router_health_url "{f}"', tmp_path)
    got_rc, got = r.stdout.splitlines()[0].split(" ", 1)
    assert int(got_rc[3:]) == rc and out in got, r.stdout
    if rc == 0:
        assert r.stdout.splitlines()[1] == out[: -len("/v1")] + "/health"


# ── /health 읽기 · 도는 요청 ───────────────────────────────────────────────────────────────────────────
def _health(tmp_path: Path, url: str, fn: str = "hwax_llm_router_health", **env) -> tuple[int, str]:
    r = _sh(f'. "{LIB}"\nout="$({fn} "{url}")"; echo "rc=$? out=[$out]"', tmp_path, **env)
    assert not r.stderr, r.stderr
    rc, out = r.stdout.strip().split(" ", 1)
    return int(rc[3:]), out[5:-1]


def test_라우터의_답을_한_줄로_읽는다(tmp_path, router):
    router["body"].update(inflight=3)
    assert _health(tmp_path, router["url"]) == (0, "ok 2 2 3 true")


def test_down_의_503_도_답이다(tmp_path, router):
    router["code"] = 503
    router["body"].update(status="down", upstreams_up=0, inflight=0)
    assert _health(tmp_path, router["url"]) == (0, "down 0 2 0 true")


@pytest.mark.parametrize("body", [{"status": "ok"}, "<html>502</html>", "", [1, 2], None])
def test_라우터의_답이_아니면_모른다(tmp_path, router, body):
    """같은 포트에 다른 것이 떠 있으면(upstreams_total 이 없다) 라우터로 치지 않는다 — 그것을 내리거나 그것으로 사본을 바꾸지 않게."""
    router["body"] = body
    assert _health(tmp_path, router["url"])[0] == 2


def test_수가_아닌_칸은_물음표다(tmp_path, router):
    router["body"].update(upstreams_up=True, inflight=-1, models="x", status="weird")
    assert _health(tmp_path, router["url"]) == (0, "? ? 2 ? ?")


def test_답이_없으면_모른다(tmp_path):
    assert _health(tmp_path, f"http://127.0.0.1:{_dead_port()}/health")[0] == 2


@pytest.mark.parametrize("inflight,want", [(3, (0, "3")), (1, (0, "1")), (0, (1, ""))])
def test_도는_요청이_확실히_있을_때만_바쁘다(tmp_path, router, inflight, want):
    router["body"].update(inflight=inflight)
    assert _health(tmp_path, router["url"], "hwax_llm_router_busy") == want


@pytest.mark.parametrize("patch", [{"inflight": "많음"}, {"inflight": True}, {"inflight": -2}, {"inflight": None}])
def test_도는_요청을_모르면_바쁘지_않다고_하지도_않는다(tmp_path, router, patch):
    """모름은 2 다 — 부르는 쪽은 0 일 때만 미룬다(모르는데 미루면 죽은·매달린 라우터를 영영 못 띄운다)."""
    router["body"].update(patch)
    if patch["inflight"] is None:
        del router["body"]["inflight"]
    assert _health(tmp_path, router["url"], "hwax_llm_router_busy") == (2, "")


def test_내려간_라우터는_모른다(tmp_path):
    assert _health(tmp_path, f"http://127.0.0.1:{_dead_port()}/health", "hwax_llm_router_busy") == (2, "")


def test_강행하면_묻지도_않는다(tmp_path, router):
    router["body"].update(inflight=5)
    assert _health(tmp_path, router["url"], "hwax_llm_router_busy", LLM_ROUTER_RESTART_FORCE="1") == (1, "")
    assert router["hits"] == 0
    assert _health(tmp_path, router["url"], "hwax_llm_router_busy", LLM_ROUTER_RESTART_FORCE="0") == (0, "5"), "1 만 강행이다"


def test_운영자_셸의_프록시를_타지_않는다(tmp_path, router):
    dead = f"http://127.0.0.1:{_dead_port()}"
    assert _health(tmp_path, router["url"], http_proxy=dead, HTTP_PROXY=dead, no_proxy="", NO_PROXY="")[0] == 0


# ── 지금 써야 할 주소 ─────────────────────────────────────────────────────────────────────────────────
def _eff(tmp_path: Path, env_text: str, *direct: str) -> tuple[int, str, str]:
    f = tmp_path / "infra.env"; f.write_text(env_text, encoding="utf-8")
    args = " ".join(f'"{d}"' for d in direct)
    r = _sh(f'. "{LIB}"\nout="$(hwax_llm_effective_url "{f}" {args})"; echo "rc=$? out=[$out]"', tmp_path)
    rc, out = r.stdout.strip().split(" ", 1)
    return int(rc[3:]), out[5:-1], r.stderr


def test_풀이_꺼져_있으면_직접_주소(tmp_path):
    assert _eff(tmp_path, f"LLM_BASE_URL={DIRECT}\n")[:2] == (0, DIRECT)
    assert _eff(tmp_path, f"LLM_BASE_URL={DIRECT}\n", "http://198.51.100.9:1/v1")[:2] == (0, "http://198.51.100.9:1/v1"), "준 직접 주소가 이긴다"
    assert _eff(tmp_path, "OTHER=1\n")[:2] == (1, "")


def test_풀이_켜져_있고_라우터가_서버를_올렸으면_라우터(tmp_path, router):
    env = f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={router['port']}\n"
    assert _eff(tmp_path, env) == (0, f"http://127.0.0.1:{router['port']}/v1", "")
    assert _eff(tmp_path, f"LLM_UPSTREAMS={S1}\nLLM_ROUTER_PORT={router['port']}\n")[:2] == (0, f"http://127.0.0.1:{router['port']}/v1"), \
        "직접 주소가 없어도 라우터가 쓸 만하면 라우터다"


@pytest.mark.parametrize("case", ["올라온 서버 0", "답 없음", "모델 다름", "모델 대조 전"])
def test_라우터가_쓸_수_없으면_직접_주소와_한_줄(tmp_path, router, case):
    """1i 가 사본을 안 바꾸는 바로 그 조건 — 새로 더한 키만 라우터를 보면 안 된다. 모델이 다르거나 아직 대조 전이면 1i 도 바꾸지
    않는다(반대 검토 M5 — 다른 모델로 재기동한 서버는 빨리 실패해 한가해 보이고 요청을 다 받는다)."""
    port = router["port"]
    if case == "답 없음":
        port = _dead_port()
    elif case == "모델 다름":
        router["body"]["models"] = {"match": False, "ids": {"a": ["x"], "b": ["y"]}, "max_model_len": {}}
    elif case == "모델 대조 전":
        router["body"]["models"] = {"match": None, "ids": [], "max_model_len": None}
    else:
        router["code"] = 503; router["body"].update(status="down", upstreams_up=0)
    rc, out, err = _eff(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1},{S2}\nLLM_ROUTER_PORT={port}\n")
    assert (rc, out) == (0, DIRECT) and "라우터" in err and "직접 주소" in err


def test_틀린_목록이면_라우터를_묻지도_않는다(tmp_path, router):
    rc, out, err = _eff(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={S1}, {S2}\nLLM_ROUTER_PORT={router['port']}\n")
    assert (rc, out, err) == (0, DIRECT, "") and router["hits"] == 0


# ── 사본 목록 — 킷과 MAP 에서 유도한다 ──────────────────────────────────────────────────────────────────
EXPECTED = {
    ("agent-server", "HWAXAgentServer", ".env", "VLLM_BASE_URL"),
    ("ai-data-hub", "AIDataHub", "deploy/apptainer/.env", "OPENAI_BASE_URL"),
    ("ai-data-hub", "AIDataHub", "deploy/apptainer/.env", "LLM_BASE_URL"),
    ("heax-hub", "HEAXHub", ".env", "HEAX_APP_LLM_BASE_URL"),
    ("mx-white-paper", "MXWhitePaper", ".env", "LLM_BASE_URL"),
    ("paper-ingest", "PaperIngest", ".env", "GLM_BASE_URL"),
    ("signalforge", "SignalForge", ".env", "OPENAI_BASE_URL"),
}


def _copies(root: Path, home: Path) -> set[tuple[str, ...]]:
    r = _sh(f'. "{LIB}"; hwax_llm_pool_copies "{root}"', home)
    assert not r.stderr, r.stderr
    return {tuple(ln.split("\t")) for ln in r.stdout.splitlines()}


def test_사본_목록은_PLAN_의_일곱_곳이다(tmp_path):
    """PLAN §1 의 사본 목록과 같다 — 킷의 @FROM_RA:LLM_BASE_URL@ 다섯(+PaperIngest) 과 코드가 직접 읽는 LLM_BASE_URL 둘."""
    assert _copies(ROOT, tmp_path) == EXPECTED


def test_킷에_줄이_늘면_사본이_저절로_따라온다(tmp_path):
    """목록을 손으로 적어 두면 킷에 새 LLM 키가 생겨도 1i 가 그 사본을 모른다(LP-D4 가 막으려는 바로 그 무음 결함)."""
    root = tmp_path / "HWAXPortal"; shutil.copytree(KITS, root / "infra/env-kits")
    with open(root / "infra/env-kits/mx-white-paper.env", "a", encoding="utf-8") as f:
        f.write("CHAT_LLM_URL=@FROM_RA:LLM_BASE_URL@\nCHAT_LLM_MODEL=@FROM_RA:LLM_MODEL@\n")
    got = _copies(root, tmp_path)
    assert got - EXPECTED == {("mx-white-paper", "MXWhitePaper", ".env", "CHAT_LLM_URL")}, got - EXPECTED


def test_코드가_직접_읽는_사본은_MAP_의_그_파일이다():
    """_HWAX_LLM_EXTRA 의 리포·경로는 apply-envs MAP 의 것과 같아야 한다 — 어긋나면 1i 가 엉뚱한 파일을 보거나 아무것도 안 본다."""
    apply = (KITS / "apply-envs.sh").read_text(encoding="utf-8")
    for svc, repo, rel, _ in [c for c in EXPECTED if c[3] == "LLM_BASE_URL"]:
        assert f'[{svc}]="{repo}:{rel}"' in apply, (svc, repo, rel)


# ── 사본 바꾸기 ──────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def box(tmp_path):
    """임시 박스 — 포털(킷·apply-envs 사본) + 형제 리포 + 빈 HOME. 실물 리포는 이 경로 밖이라 lib 가 찾을 수 없다."""
    root = tmp_path / "HWAXPortal"; shutil.copytree(KITS, root / "infra/env-kits")
    home = tmp_path / "home"; home.mkdir()
    sib = {}
    for repo, rel in (("HWAXAgentServer", ".env"), ("AIDataHub", "deploy/apptainer/.env"), ("HEAXHub", ".env"),
                      ("SignalForge", ".env"), ("MXWhitePaper", ".env"), ("PaperIngest", ".env")):
        p = tmp_path / repo / rel; p.parent.mkdir(parents=True, exist_ok=True); sib[repo] = p
    return root, home, sib


def _rewrite(box, mode: str, new: str, *managed: str) -> list[list[str]]:
    root, home, _ = box
    args = " ".join(f'"{m}"' for m in managed)
    r = _sh(f'. "{LIB}"; hwax_llm_pool_rewrite "{root}" {mode} "{new}" {args}; echo "rc=$?"', home)
    assert r.stdout.rstrip().endswith("rc=0"), r.stdout + r.stderr
    rows = [ln.split("\t") for ln in r.stdout.splitlines()[:-1]]
    for row in rows:
        assert Path(row[2]).resolve().is_relative_to(root.parent.resolve()), f"임시 박스 밖의 리포를 봤다 — {row[2]}"
    return rows


def _row(rows, repo: str, key: str) -> list[str]:
    hit = [r for r in rows if r[2].endswith("/" + repo) and r[4] == key]
    assert len(hit) == 1, (repo, key, rows)
    return hit[0]


def _bk_root(p: Path) -> Path:
    """사본 p(<임시>/<리포>/<상대경로>)의 백업 자리 — 포털의 infra/.state/llm-pool-backups/<리포>/<상대경로>(사본 옆이 아니다)."""
    top = next(a for a in p.parents if (a / "HWAXPortal").is_dir())
    return top / "HWAXPortal/infra/.state/llm-pool-backups" / p.relative_to(top)


def _baks(p: Path) -> list[Path]:
    bk = _bk_root(p)
    return sorted(bk.parent.glob(bk.name + ".*")) if bk.parent.is_dir() else []


def _strays(p: Path) -> list[str]:
    """사본 디렉터리에 사본 말고 생긴 것 — 옛 `.env.bak-*` 나 남은 임시 파일. 서비스 리포 안에는 아무것도 남기지 않는다(H1)."""
    return sorted(x.name for x in p.parent.iterdir() if x.name != p.name) if p.parent.is_dir() else []


ROUTER = "http://127.0.0.1:9130/v1"


def test_관리하는_값만_바꾸고_나머지는_한_바이트도_안_바꾼다(box):
    """**이 시험이 이 파일의 이유다** — 직접 주소·목록의 서버인 사본은 라우터로, 사람이 일부러 적은 다른 주소는 그대로."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    before = (f"# 에이전트 서버\nVLLM_MODEL=glm\nVLLM_BASE_URL={DIRECT}/\nVLLM_API_KEY=k\n"
              "NO_PROXY=127.0.0.1,localhost\n").encode()
    agent.write_bytes(before); agent.chmod(0o600)
    sf = sib["SignalForge"]; sf.write_text(f"OPENAI_BASE_URL={S2}\nOPENAI_MODEL=glm\n"); sf.chmod(0o644)
    heax = sib["HEAXHub"]; heax.write_text("HEAX_APP_LLM_BASE_URL=http://198.51.100.40:8000/v1\nX=1\n")   # 사람이 일부러 적은 다른 주소
    heax_before = heax.read_bytes()
    rows = _rewrite(box, "write", ROUTER, DIRECT, S1, S2, ROUTER)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[:1] == ["changed"]
    assert _row(rows, "SignalForge", "OPENAI_BASE_URL")[0] == "changed", "목록의 서버 주소도 관리하는 값이다"
    foreign = _row(rows, "HEAXHub", "HEAX_APP_LLM_BASE_URL")
    assert foreign[0] == "foreign" and foreign[5] == "http://198.51.100.40:8000/v1"
    assert heax.read_bytes() == heax_before and not _baks(heax), "관리 밖 사본의 파일은 건드리지도 백업하지도 않는다"
    assert agent.read_bytes() == before.replace(f"VLLM_BASE_URL={DIRECT}/".encode(), f"VLLM_BASE_URL={ROUTER}".encode())
    assert sf.read_text() == f"OPENAI_BASE_URL={ROUTER}\nOPENAI_MODEL=glm\n"


def test_백업은_포털_상태_디렉터리에만_600_으로_남고_서비스_리포에는_아무것도_없다(box):
    """**H1 회귀** — 백업이 사본 옆(`.env.bak-*`)에 남으면 서비스 리포 다섯 곳에서 gitignore 밖의 비밀 파일이 되고, deploy-all 의
    `git stash push -u` 가 그 비밀째 stash 로 쓸어 가 되돌리기 안내가 가리키는 파일이 사라진다. 백업은 포털의 gitignore 된
    infra/.state/llm-pool-backups/<리포>/<상대경로>.<UTC> 에 — 디렉터리 700 · 파일 600(원본이 644 여도) — 둔다."""
    root, _, sib = box
    agent, sf, aidh = sib["HWAXAgentServer"], sib["SignalForge"], sib["AIDataHub"]
    agent.write_text(f"VLLM_BASE_URL={DIRECT}\nVLLM_API_KEY=secret\n"); agent.chmod(0o600)
    sf.write_text(f"OPENAI_BASE_URL={DIRECT}\n"); sf.chmod(0o644)
    aidh.write_text(f"OPENAI_BASE_URL={DIRECT}\nLLM_BASE_URL={DIRECT}\n"); aidh.chmod(0o640)
    orig = {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode), p.stat().st_uid, p.stat().st_gid) for p in (agent, sf, aidh)}
    rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    bkroot = root / "infra/.state/llm-pool-backups"
    for p, (data, mode, uid, gid) in orig.items():
        repo = p.relative_to(root.parent).parts[0]
        baks = _baks(p)
        assert len(baks) == 1 and baks[0].read_bytes() == data, "백업은 바꾸기 전 내용이다 — 파일마다 한 번"
        assert re.fullmatch(r"\.env\.\d{8}T\d{6}Z", baks[0].name), baks[0].name
        assert stat.S_IMODE(baks[0].stat().st_mode) == 0o600, "백업은 원본 권한과 무관하게 600 이다(비밀 사본)"
        assert stat.S_IMODE(p.stat().st_mode) == mode and (p.stat().st_uid, p.stat().st_gid) == (uid, gid), "권한·소유자 그대로"
        assert _strays(p) == [], f"서비스 리포에 남은 것이 있다 — {_strays(p)}"
        for d in [a for a in baks[0].parents if a == bkroot or a.is_relative_to(bkroot)]:
            assert stat.S_IMODE(d.stat().st_mode) == 0o700, f"백업 디렉터리는 700 — {d}"
        mine = [r for r in rows if r[2].endswith("/" + repo) and r[0] == "changed"]
        assert mine and all(r[6] == str(baks[0]) and Path(r[6]).is_absolute() for r in mine), "바꾼 줄은 백업의 전체 경로를 낸다(되돌리기)"
    assert (bkroot / "AIDataHub/deploy/apptainer").is_dir(), "리포 안 경로를 그대로 따른다"


def test_같은_초에_다시_돌아도_앞_백업을_덮지_않는다(box):
    _, _, sib = box
    agent = sib["HWAXAgentServer"]; agent.write_text(f"VLLM_BASE_URL={DIRECT}\n")
    for new, old in ((ROUTER, DIRECT), (DIRECT, ROUTER), (ROUTER, DIRECT)):
        _rewrite(box, "write", new, old)
    names = [p.name for p in _baks(agent)]
    assert len(names) == 3 and len(set(names)) == 3, names
    assert sorted(p.read_text() for p in _baks(agent)) == sorted([f"VLLM_BASE_URL={DIRECT}\n", f"VLLM_BASE_URL={ROUTER}\n",
                                                                  f"VLLM_BASE_URL={DIRECT}\n"])


def test_따옴표_export_줄끝_주석_CRLF_를_그대로_둔다(box):
    _, _, sib = box
    aidh = sib["AIDataHub"]
    raw = (f'OPENAI_BASE_URL="{DIRECT}"   # 미리보기\r\n'
           f"export LLM_BASE_URL='{S1}/'\r\n"
           "OPENAI_API_KEY=k\r\n").encode()
    aidh.write_bytes(raw)
    rows = _rewrite(box, "write", ROUTER, DIRECT, S1, ROUTER)
    assert [r[0] for r in rows if "AIDataHub" in r[2]] == ["changed", "changed"]
    want = (f'OPENAI_BASE_URL="{ROUTER}"   # 미리보기\r\n'
            f"export LLM_BASE_URL='{ROUTER}'\r\n"
            "OPENAI_API_KEY=k\r\n").encode()
    assert aidh.read_bytes() == want
    assert len(_baks(aidh)) == 1, "한 파일의 키 둘 — 백업은 한 번이다"


def test_읽는_줄과_같은_줄만_고친다(box):
    """같은 키가 두 번이면 읽는 쪽(마지막 활성 줄)을 고친다 — 앞 줄을 고치면 바꾼 값이 안 먹는다."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    agent.write_text(f"VLLM_BASE_URL=http://198.51.100.1:1/v1\n# VLLM_BASE_URL={DIRECT}\nVLLM_BASE_URL={DIRECT}\n")
    _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    assert agent.read_text() == f"VLLM_BASE_URL=http://198.51.100.1:1/v1\n# VLLM_BASE_URL={DIRECT}\nVLLM_BASE_URL={ROUTER}\n"


@pytest.mark.parametrize("content", [None, "OTHER=1\n", f"# VLLM_BASE_URL={DIRECT}\n"])
def test_키가_없으면_건드리지_않는다(box, content):
    """없는 키는 apply-envs 몫이다(3.5) — 여기서 더하면 '없는 키만 더한다' 와 '관리하는 값만 바꾼다' 두 규칙이 섞인다."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    if content is not None:
        agent.write_text(content)
    rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "absent"
    assert (agent.read_text() if agent.exists() else None) == content and not _baks(agent)


def test_빈_값도_관리하는_값이_아니다(box):
    _, _, sib = box
    sib["HWAXAgentServer"].write_text("VLLM_BASE_URL=\n")
    rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "foreign"
    assert sib["HWAXAgentServer"].read_text() == "VLLM_BASE_URL=\n"


def test_풀을_끄면_라우터를_가리키는_사본만_직접_주소로(box):
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}\n")
    sib["SignalForge"].write_text(f"OPENAI_BASE_URL={DIRECT}\n")                   # 이미 직접 주소
    sib["HEAXHub"].write_text("HEAX_APP_LLM_BASE_URL=http://198.51.100.40:8000/v1\n")
    rows = _rewrite(box, "write", DIRECT, ROUTER)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "changed"
    assert _row(rows, "SignalForge", "OPENAI_BASE_URL")[0] == "same"
    assert _row(rows, "HEAXHub", "HEAX_APP_LLM_BASE_URL")[0] == "foreign"
    assert sib["HWAXAgentServer"].read_text() == f"VLLM_BASE_URL={DIRECT}\n"
    assert not _baks(sib["SignalForge"]) and not _baks(sib["HEAXHub"])


def test_두_번째_실행은_아무것도_바꾸지_않는다(box):
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={DIRECT}\n")
    sib["MXWhitePaper"].write_text(f"LLM_BASE_URL={S2}\n")
    first = _rewrite(box, "write", ROUTER, DIRECT, S1, S2, ROUTER)
    assert sorted(r[0] for r in first if r[0] != "absent") == ["changed", "changed"]
    snap = {p: (p.read_bytes(), len(_baks(p))) for p in sib.values() if p.exists()}
    second = _rewrite(box, "write", ROUTER, DIRECT, S1, S2, ROUTER)
    assert sorted(r[0] for r in second if r[0] != "absent") == ["same", "same"]
    assert {p: (p.read_bytes(), len(_baks(p))) for p in snap} == snap, "두 번째 실행이 파일을 쓰거나 백업을 늘렸다"


def test_dry_는_보고만_한다(box):
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={DIRECT}\n")
    rows = _rewrite(box, "dry", ROUTER, DIRECT, ROUTER)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "would"
    assert sib["HWAXAgentServer"].read_text() == f"VLLM_BASE_URL={DIRECT}\n" and not _baks(sib["HWAXAgentServer"])


def test_가리키는_사본_수(box):
    root, home, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}/\n")
    sib["AIDataHub"].write_text(f"OPENAI_BASE_URL={ROUTER}\nLLM_BASE_URL={DIRECT}\n")
    r = _sh(f'. "{LIB}"; hwax_llm_pool_at "{root}" "{ROUTER}"; echo "rc=$?"', home)
    assert r.stdout.split() == ["2", "rc=0"], r.stdout + r.stderr


def _at(box, *, pre: str = "", **env) -> tuple[int, str, str]:
    root, home, _ = box
    r = _sh(f'{pre}. "{LIB}"; out="$(hwax_llm_pool_at "{root}" "{ROUTER}")"; rc=$?; echo "rc=$rc"; printf "[%s]\\n" "$out"', home, **env)
    lines = r.stdout.splitlines()
    return int(lines[0][3:]), lines[1], r.stderr


def test_셀_수_없으면_0_이_아니라_모른다(box):
    """**2라운드 M-D 회귀** — `rewrite dry | awk 'END { print n + 0 }'` 는 lib 이 실패해도 0 이었다. /tmp 가 차 bash 가 파이썬 here-doc 의 임시
    파일을 못 만들면(ulimit -f 1 로 흉내) 1i 는 사본을 안 되돌리고, 뒤처리는 '사본은 직접 주소다' 를 찍고 사본 둘이 아직 가리키는 라우터를
    내렸다. 이제 2 와 사유 한 줄이다 — 부르는 쪽이 '가리킬 수 있다' 로 읽는다."""
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}\n")
    rc, out, err = _at(box, pre="ulimit -f 1; ")
    assert "here-document" in err, "lib 이 실패하지 않았다 — 시험이 헛돈다"
    assert rc == 2 and out.startswith("[사본을 세지 못했다") and "rc 1" in out, (rc, out, err)


@NOT_ROOT
def test_읽지_못한_사본이_있으면_모른다(box):
    """읽지 못한 사본(error 줄)은 그 주소를 가리킬 수 있다 — 세지 않고 0 으로 치면 같은 결함이다. 자리와 사유를 함께 낸다."""
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}\n")
    sib["SignalForge"].write_text(f"OPENAI_BASE_URL={ROUTER}\n"); sib["SignalForge"].chmod(0o000)
    try:
        rc, out, _ = _at(box)
    finally:
        sib["SignalForge"].chmod(0o644)
    assert rc == 2 and "1곳을 읽지 못했다" in out and "SignalForge/.env OPENAI_BASE_URL" in out, out


def test_파이썬이_죽어도_모른다(box, tmp_path):
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}\n")
    shim = tmp_path / "shim"; shim.mkdir()
    (shim / "python3").write_text("#!/usr/bin/env bash\necho '(대역) python3 죽음' >&2\nexit 9\n"); (shim / "python3").chmod(0o755)
    rc, out, err = _at(box, PATH=f"{shim}:{os.environ['PATH']}")
    assert "(대역) python3 죽음" in err and rc == 2 and "rc 9" in out, (rc, out, err)


@pytest.fixture()
def listener():
    """무언가 듣는 루프백 포트(답은 아무래도 좋다 — 연결만 받는다)."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown(); srv.server_close()


def test_아무것도_듣지_않는_루프백_사본을_찾되_고치지_않는다(box, listener):
    """**2라운드 LOW 7** — 라우터 기록을 잃으면 옛 라우터 주소를 모른다. 루프백 /v1 인데 그 포트에 아무것도 듣지 않는 사본만 낸다 — 듣고
    있는 루프백(로컬 vLLM)·원격 주소·뺄 주소(지금 라우터 · 직접 주소)는 내지 않는다. 파일은 한 바이트도 안 바뀐다."""
    root, home, sib = box
    dead, dead2 = f"http://127.0.0.1:{_dead_port()}/v1", f"http://localhost:{_dead_port()}/v1/"
    excluded = f"http://127.0.0.1:{_dead_port()}/v1"
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={dead}\n")
    sib["AIDataHub"].write_text(f"OPENAI_BASE_URL=http://127.0.0.1:{listener}/v1\nLLM_BASE_URL={DIRECT}\n")
    sib["SignalForge"].write_text(f"OPENAI_BASE_URL={excluded}\n")
    sib["MXWhitePaper"].write_text(f"LLM_BASE_URL={dead2}\n")
    sib["HEAXHub"].write_text(f"HEAX_APP_LLM_BASE_URL=http://127.0.0.1:{_dead_port()}/openai\n")   # /v1 이 아니다 — LLM 주소 모양이 아니다
    before = {p: p.read_bytes() for p in sib.values() if p.exists()}
    r = _sh(f'. "{LIB}"; out="$(hwax_llm_pool_loopback_dead "{root}" "{excluded}/" "{DIRECT}")"; echo "rc=$?"; printf "%s" "$out"', home)
    lines = r.stdout.splitlines()
    assert lines[0] == "rc=0", r.stdout + r.stderr
    got = sorted((Path(a).name, b, c, d) for a, b, c, d in (ln.split("\t") for ln in lines[1:]))
    assert got == [("HWAXAgentServer", ".env", "VLLM_BASE_URL", dead), ("MXWhitePaper", ".env", "LLM_BASE_URL", dead2)], got
    assert {p: p.read_bytes() for p in before} == before


@NOT_ROOT
def test_루프백_점검도_읽지_못하면_모른다(box):
    root, home, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL=http://127.0.0.1:{_dead_port()}/v1\n"); sib["HWAXAgentServer"].chmod(0o000)
    try:
        r = _sh(f'. "{LIB}"; out="$(hwax_llm_pool_loopback_dead "{root}")"; echo "rc=$?"; printf "%s" "$out"', home)
    finally:
        sib["HWAXAgentServer"].chmod(0o644)
    assert r.stdout.startswith("rc=2") and "읽지 못했다" in r.stdout, r.stdout


def test_리포가_없는_사본은_줄을_내지_않는다(box):
    _, _, sib = box
    shutil.rmtree(sib["PaperIngest"].parent)
    rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    assert not any(r[2].endswith("/PaperIngest") for r in rows)


def test_새_값이_비면_아무것도_하지_않는다(box):
    root, home, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={ROUTER}\n")
    r = _sh(f'. "{LIB}"; hwax_llm_pool_rewrite "{root}" write "" "{ROUTER}"; echo "rc=$?"', home)
    assert "rc=2" in r.stdout and r.stdout.count("\t") == 0
    assert sib["HWAXAgentServer"].read_text() == f"VLLM_BASE_URL={ROUTER}\n"


@NOT_ROOT
def test_백업을_못_만들면_바꾸지_않는다(box):
    """백업이 먼저다 — 포털의 상태 디렉터리에 쓸 수 없으면(백업을 못 만든다) 사본은 쓸 수 있어도 바꾸지 않는다."""
    root, _, sib = box
    agent = sib["HWAXAgentServer"]
    agent.write_text(f"VLLM_BASE_URL={DIRECT}\n"); agent.chmod(0o644)
    state = root / "infra/.state"; state.mkdir(parents=True); state.chmod(0o555)
    try:
        rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    finally:
        state.chmod(0o755)
    row = _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")
    assert row[0] == "error" and "백업을 만들지 못했다" in row[5] and "그대로다" in row[5], row
    assert agent.read_text() == f"VLLM_BASE_URL={DIRECT}\n" and not _baks(agent) and _strays(agent) == []


@NOT_ROOT
def test_사본_디렉터리에_쓸_수_없으면_백업_뒤_제자리에_쓰고_그렇게_말한다(box):
    """**2라운드 LOW 4 회귀**(LP-D14) — 이름 바꾸기는 디렉터리에 써야 한다. 종전(제자리 쓰기)에는 되던 읽기 전용 리포 디렉터리에서 ✗ 가 됐다.
    파일은 쓸 수 있으면 백업 뒤 **제자리에** 쓰고(같은 inode) 줄의 여덟째 칸에 그 사실과 까닭을 적는다. 디렉터리에는 아무것도 생기지 않는다."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    agent.write_text(f"VLLM_BASE_URL={DIRECT}\nK=1\n"); agent.chmod(0o600)
    ino = agent.stat().st_ino
    agent.parent.chmod(0o555)
    try:
        rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
        listing = sorted(x.name for x in agent.parent.iterdir())
    finally:
        agent.parent.chmod(0o755)
    row = _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")
    assert row[0] == "changed" and len(row) == 8 and "제자리에 썼다" in row[7] and "디렉터리에 쓸 수 없다" in row[7], row
    assert agent.read_text() == f"VLLM_BASE_URL={ROUTER}\nK=1\n" and agent.stat().st_ino == ino
    assert stat.S_IMODE(agent.stat().st_mode) == 0o600 and listing == [".env"]
    assert len(_baks(agent)) == 1 and row[6] == str(_baks(agent)[0]), "제자리 쓰기도 백업이 먼저다"


@NOT_ROOT
def test_제자리_쓰기가_디스크에_막히면_원래_내용으로_되돌리고_백업도_지운다(box):
    """제자리 쓰기가 도중에 막히면(디스크가 찼다 — RLIMIT_FSIZE 로 흉내, 한도를 넘는 데서 끊긴다) 원래 내용을 다시 쓴다. 반쯤 쓴 .env 를
    남기지 않고, 결과가 원래와 같으니 백업도 지운다(파일은 그대로다)."""
    root, home, sib = box
    agent = sib["HWAXAgentServer"]
    old, new = "http://198.51.100.7/v1", "http://127.0.0.1:9130/v1/" + "a" * 700
    agent.write_text(f"VLLM_BASE_URL={old}\nPAD={'x' * 64900}\n")
    before = agent.read_bytes()
    assert len(before) < 65536 < len(before) + 700
    agent.parent.chmod(0o555)                                     # 제자리 쓰기 길로
    try:
        r = _sh(f'ulimit -f 64; . "{LIB}"; hwax_llm_pool_rewrite "{root}" write "{new}" "{old}"; echo "rc=$?"', home)
    finally:
        agent.parent.chmod(0o755)
    row = [ln.split("\t") for ln in r.stdout.splitlines() if "HWAXAgentServer" in ln]
    assert len(row) == 1 and row[0][0] == "error" and "쓰지 못했다" in row[0][5] and "그대로다" in row[0][5], r.stdout + r.stderr
    assert "백업은 지웠다" in row[0][5] and agent.read_bytes() == before and not _baks(agent) and _strays(agent) == []


def test_하드_링크_사본은_제자리에_써서_다른_이름도_함께_바뀐다(box):
    """**2라운드 LOW 4 회귀** — 이름 바꾸기는 하드 링크를 끊었다(다른 이름이 옛 주소에 남는다 — 그 이름으로 읽는 서비스는 옛 주소로 돈다)."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    shared = agent.parent.parent / "shared/agent.env"; shared.parent.mkdir()
    shared.write_text(f"VLLM_BASE_URL={DIRECT}\nK=1\n"); agent.hardlink_to(shared)
    rows = _rewrite(box, "write", ROUTER, DIRECT)
    row = _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")
    assert row[0] == "changed" and len(row) == 8 and "하드 링크" in row[7], row
    assert agent.stat().st_nlink == 2 and agent.stat().st_ino == shared.stat().st_ino, "링크가 끊겼다"
    assert shared.read_text() == f"VLLM_BASE_URL={ROUTER}\nK=1\n", "다른 이름이 옛 주소에 남았다"
    assert _strays(agent) == [] and sorted(x.name for x in shared.parent.iterdir()) == ["agent.env"]


def _acl(p: Path) -> str:
    return subprocess.run(["getfacl", "-c", "-p", str(p)], capture_output=True, text=True).stdout


@pytest.mark.skipif(shutil.which("setfacl") is None or shutil.which("getfacl") is None, reason="setfacl·getfacl 이 없다 — ACL 을 만들 수 없다")
def test_ACL_이_있는_사본은_제자리에_써서_ACL_을_지킨다(box):
    """**2라운드 LOW 4 회귀** — 새 파일은 모드만 받는다(S_IMODE 의 그룹 칸은 ACL 마스크다). `group::---` + `user:nobody:r` 이던 비밀 파일이
    `group::r--` 가 되고 이름 붙은 사용자는 사라졌다 — 그룹의 읽기 권한이 넓어졌다. ACL 이 있으면 제자리에 써서 그대로 둔다."""
    _, _, sib = box
    sf = sib["SignalForge"]
    sf.write_text(f"OPENAI_BASE_URL={DIRECT}\nOPENAI_API_KEY=secret\n"); sf.chmod(0o600)
    r = subprocess.run(["setfacl", "-m", "u:nobody:r", str(sf)], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"이 파일 시스템은 ACL 을 받지 않는다 — {r.stderr.strip()}")
    before = _acl(sf)
    assert "user:nobody:r--" in before and "group::---" in before, before
    rows = _rewrite(box, "write", ROUTER, DIRECT)
    row = _row(rows, "SignalForge", "OPENAI_BASE_URL")
    assert row[0] == "changed" and len(row) == 8 and "ACL" in row[7], row
    assert _acl(sf) == before, (before, _acl(sf))
    assert sf.read_text() == f"OPENAI_BASE_URL={ROUTER}\nOPENAI_API_KEY=secret\n" and _strays(sf) == []


def test_이름_바꾸기로_바꾼_줄은_여덟째_칸이_없다(box):
    """제자리에 쓴 줄만 그 사실을 적는다 — 보통 사본(링크 하나 · ACL 없음 · 디렉터리에 쓸 수 있다)은 종전대로 일곱 칸이다."""
    _, _, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={DIRECT}\n")
    row = _row(_rewrite(box, "write", ROUTER, DIRECT), "HWAXAgentServer", "VLLM_BASE_URL")
    assert row[0] == "changed" and len(row) == 7, row


@NOT_ROOT
def test_읽기_전용_사본은_그대로_두고_백업도_만들지_않는다(box):
    """이름 바꾸기는 디렉터리 권한만 본다 — 읽기 전용 파일도 갈아 끼울 수 있어 먼저 본다(사람이 일부러 잠근 파일이다)."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    agent.write_text(f"VLLM_BASE_URL={DIRECT}\n"); agent.chmod(0o444)
    ino = agent.stat().st_ino
    try:
        rows = _rewrite(box, "write", ROUTER, DIRECT, ROUTER)
    finally:
        mode = stat.S_IMODE(agent.stat().st_mode); agent.chmod(0o644)
    row = _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")
    assert row[0] == "error" and "쓸 수 없는 파일" in row[5] and "되돌린다" not in row[5], row
    assert agent.read_text() == f"VLLM_BASE_URL={DIRECT}\n" and agent.stat().st_ino == ino and mode == 0o444
    assert not _baks(agent) and _strays(agent) == []


def test_디스크가_차도_반쯤_잘린_사본을_남기지_않는다(box):
    """**L3 회귀** — 제자리 쓰기는 쓰다 막히면(디스크 참 — 여기서는 RLIMIT_FSIZE 로 흉내) 잘린 .env 를 남겼다. 임시 파일에 쓰고 이름을
    바꾸므로 사본은 한 바이트도 안 바뀌고, 임시 파일도 막 만든 백업도 남지 않는다. 한도는 lib 의 here-doc(bash 임시 파일)보다 커야 한다."""
    root, home, sib = box
    agent = sib["HWAXAgentServer"]
    old, new = "http://198.51.100.7/v1", "http://127.0.0.1:9130/v1/" + "a" * 700
    agent.write_text(f"VLLM_BASE_URL={old}\nPAD={'x' * 64900}\n")
    before = agent.read_bytes()
    assert len(before) < 65536 < len(before) + 700, "원본은 한도 안 · 바꾼 것은 한도 밖"
    r = _sh(f'ulimit -f 64; . "{LIB}"; hwax_llm_pool_rewrite "{root}" write "{new}" "{old}"; echo "rc=$?"', home)
    row = [ln.split("\t") for ln in r.stdout.splitlines() if "HWAXAgentServer" in ln]
    assert len(row) == 1 and row[0][0] == "error" and "쓰지 못했다" in row[0][5], r.stdout + r.stderr
    assert agent.read_bytes() == before, "사본이 잘렸다"
    assert _strays(agent) == [] and not _baks(agent), "임시 파일·백업이 남았다"


def test_심링크_사본은_링크를_두고_가리키는_파일을_바꾼다(box):
    """/data 이관의 심링크 브리지 모양 — 이름 바꾸기를 링크에 하면 링크가 파일로 바뀌어 브리지가 끊긴다."""
    _, _, sib = box
    agent = sib["HWAXAgentServer"]
    target = agent.parent.parent / "data/agent/agent.env"; target.parent.mkdir(parents=True)
    target.write_text(f"VLLM_BASE_URL={DIRECT}\nK=secret\n"); target.chmod(0o600)
    agent.symlink_to(target)
    rows = _rewrite(box, "write", ROUTER, DIRECT)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "changed"
    assert agent.is_symlink() and agent.resolve() == target.resolve(), "링크가 그대로다"
    assert target.read_text() == f"VLLM_BASE_URL={ROUTER}\nK=secret\n" and stat.S_IMODE(target.stat().st_mode) == 0o600
    assert len(_baks(agent)) == 1 and _baks(agent)[0].read_text() == f"VLLM_BASE_URL={DIRECT}\nK=secret\n"
    assert sorted(x.name for x in target.parent.iterdir()) == ["agent.env"], "가리키는 파일 옆에도 남은 것이 없다"


@pytest.mark.parametrize("lang", ["C.UTF-8", "ko_KR.UTF-8"])
def test_UTF8_이_아닌_값이_있어도_죽지_않고_줄을_낸다(box, lang):
    """**L4 회귀** — 사본 하나에 UTF-8 이 아닌 값이 있으면 ko_KR.UTF-8 에서 줄을 찍다 UnicodeEncodeError 로 죽었다(파일은 이미 다 쓴 뒤라
    바꾼 사본의 ✓ · 재기동 안내가 하나도 안 나왔다). 값은 바이트 그대로 지나간다."""
    root, home, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={DIRECT}\n")
    sib["SignalForge"].write_bytes(b"OPENAI_BASE_URL=http://caf\xe9.example/v1\n")      # Latin-1 한 바이트 — 관리 밖 값
    r = subprocess.run(["bash", "-c", f'. "{LIB}"; hwax_llm_pool_rewrite "{root}" write "{ROUTER}" "{DIRECT}"'], capture_output=True,
                       timeout=60, env={"PATH": os.environ["PATH"], "HOME": str(home), "LANG": lang, "LC_ALL": lang})
    assert r.returncode == 0 and not r.stderr, r.stderr
    rows = {ln.split(b"\t")[1]: ln.split(b"\t") for ln in r.stdout.splitlines()}
    assert rows[b"agent-server"][0] == b"changed" and sib["HWAXAgentServer"].read_text() == f"VLLM_BASE_URL={ROUTER}\n"
    assert rows[b"signalforge"][0] == b"foreign" and rows[b"signalforge"][5] == b"http://caf\xe9.example/v1", "값은 바이트 그대로 보인다"
    assert sib["SignalForge"].read_bytes() == b"OPENAI_BASE_URL=http://caf\xe9.example/v1\n"


def test_줄은_파일마다_처리하는_대로_낸다(box, tmp_path):
    """뒤 파일에서 예상 밖으로 죽어도 앞 파일의 결과(바꿨다 · 백업 경로)는 부르는 쪽에 남는다 — 부르는 쪽(update-all _llm_apply)은 종료코드로
    '끝까지 못 갔다' 를 안다. 두 번째 파일의 이름 바꾸기에서 죽는 python3 를 PATH 앞에 세운다(lib 의 python3 - <<'PY' 를 그대로 받는다)."""
    root, home, sib = box
    sib["HWAXAgentServer"].write_text(f"VLLM_BASE_URL={DIRECT}\n")                 # 첫 파일(사본 목록은 정렬 — agent-server 가 앞)
    sib["AIDataHub"].write_text(f"OPENAI_BASE_URL={DIRECT}\n")
    shim = tmp_path / "shim"; shim.mkdir()
    real_py = shutil.which("python3")
    (shim / "python3").write_text(
        "#!/usr/bin/env bash\n"
        f'exec "{real_py}" -c \'import os, sys\n'
        "real = os.replace; n = [0]\n"
        "def flaky(a, b):\n"
        "    n[0] += 1\n"
        "    if n[0] == 2: raise RuntimeError(\"boom\")\n"
        "    return real(a, b)\n"
        "os.replace = flaky\n"
        "exec(compile(sys.stdin.read(), \"<lib>\", \"exec\"), {\"__name__\": \"__main__\"})\n"
        "' \"${@:2}\"\n")
    (shim / "python3").chmod(0o755)
    r = subprocess.run(["bash", "-c", f'. "{LIB}"; hwax_llm_pool_rewrite "{root}" write "{ROUTER}" "{DIRECT}"; echo "rc=$?"'],
                       capture_output=True, text=True, timeout=60,
                       env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(home), "LANG": "C.UTF-8"})
    assert "RuntimeError" in r.stderr, "대역이 죽지 않았다 — 시험이 헛돈다"
    first = [ln.split("\t") for ln in r.stdout.splitlines() if ln.startswith("changed\tagent-server")]
    assert len(first) == 1 and Path(first[0][6]).is_file(), r.stdout
    assert "rc=1" in r.stdout and "ai-data-hub" not in r.stdout


def test_홀로_선_CR_은_줄바꿈이_아니다(box):
    """**L5 회귀** — 읽는 쪽(sed)은 `\\n` 으로만 줄을 나눈다. bytes.splitlines 는 홀로 선 `\\r` 에서도 나눠, 읽는 쪽이 보지 않는 줄(앞
    키의 값 꼬리)을 고쳤다. CRLF 는 그대로 된다(위 시험)."""
    root, home, sib = box
    agent = sib["HWAXAgentServer"]
    raw = f"A=1\rVLLM_BASE_URL={DIRECT}\nB=2\n".encode()
    agent.write_bytes(raw)
    reader = _sh(f'. "{LIB}"; printf "[%s]" "$(hwax_llm_envv "{agent}" VLLM_BASE_URL)"', home).stdout
    assert reader == "[]", "읽는 쪽에는 그 키가 없다"
    rows = _rewrite(box, "write", ROUTER, DIRECT)
    assert _row(rows, "HWAXAgentServer", "VLLM_BASE_URL")[0] == "absent"
    assert agent.read_bytes() == raw and not _baks(agent)


def test_라우터_주소_기록(tmp_path):
    """1i 가 사본에 적은 라우터 주소를 infra/.state 에 적고 읽는다 — 루프백 /v1 주소 모양이 아니면 없는 것으로 본다(M4)."""
    root = tmp_path / "HWAXPortal"; root.mkdir()
    rd = f'. "{LIB}"; v="$(hwax_llm_router_recorded "{root}")"; echo "rc=$? [$v]"'
    assert _sh(rd, tmp_path).stdout.strip() == "rc=1 []", "기록이 없으면 1"
    w = _sh(f'. "{LIB}"; hwax_llm_router_record "{root}" "http://127.0.0.1:9555/v1"; echo "rc=$?"', tmp_path)
    assert w.stdout.strip() == "rc=0" and (root / "infra/.state/llm-pool.router").read_text() == "http://127.0.0.1:9555/v1\n"
    assert _sh(rd, tmp_path).stdout.strip() == "rc=0 [http://127.0.0.1:9555/v1]"
    assert [p.name for p in (root / "infra/.state").iterdir()] == ["llm-pool.router"], "임시 파일이 남지 않는다"
    for junk in ("", "http://198.51.100.1:9555/v1\n", "http://127.0.0.1:9555/v1/x\n", "garbage\n"):
        (root / "infra/.state/llm-pool.router").write_text(junk)
        assert _sh(rd, tmp_path).stdout.strip() == "rc=1 []", junk


def test_lib_는_소싱만으로는_아무것도_하지_않는다(tmp_path):
    r = _sh(f'. "{LIB}"; echo ok', tmp_path)
    assert r.stdout == "ok\n" and not r.stderr
    assert LIB.read_text(encoding="utf-8").splitlines()[1].startswith("# "), "새 파일 첫 줄 아래에 역할 한 줄(한국어)"
