# apply-envs 의 @FROM_RA:LLM_BASE_URL@ 이 지금 써야 할 주소(풀이 켜져 있고 라우터가 답하면 라우터)로 풀리는지 — 다른 마커는 종전 그대로
"""왜 — 1i 가 사본을 라우터로 바꾼 뒤 3.5 의 apply-envs 가 더하는 키(새 .env · 킷에 새로 생긴 키)가 직접 주소로 남으면, 그 서비스만 조용히
풀 밖에서 돈다(docs/llm-pool PLAN §4 '새 키'). 거꾸로 라우터가 서버를 올렸다고 답하지 않는데 새 키를 라우터로 적으면 그 키만 죽은
라우터를 본다 — 1i 가 사본을 바꾸는 조건과 같은 조건으로 푼다(lib/llm-pool.sh 의 hwax_llm_effective_url).

apply-envs.sh 를 임시 박스에서 **실제로 돌린다** — HOME 을 임시 디렉터리로 바꿔 형제 리포를 ~/claude 에서 찾지 못하게 한다(실물 .env 를
고치지 않게). 라우터 /health 는 지어낸 서버다(infra/.env 의 LLM_ROUTER_PORT 로 가리킨다).
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
DIRECT, S2 = "http://203.0.113.11:10000/v1", "http://203.0.113.12:10000/v1"


@pytest.fixture()
def router():
    state = {"body": {"status": "ok", "upstreams_total": 2, "upstreams_up": 2, "inflight": 0, "models": {"match": True}}}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = state["body"]
            self.send_response(503 if body.get("status") == "down" else 200); self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["port"] = srv.server_address[1]
    yield state
    srv.shutdown(); srv.server_close()


def _dead_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _apply(tmp_path: Path, infra_env: str, svc: str = "agent-server", existing: str | None = None) -> tuple[str, str, str]:
    """임시 박스에서 apply-envs.sh <svc> 를 돌린다 → (대상 .env, 화면, stderr)."""
    portal = tmp_path / "HWAXPortal"
    shutil.copytree(ROOT / "infra/env-kits", portal / "infra/env-kits")
    (portal / "infra/scripts/lib").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/lib/llm-pool.sh", portal / "infra/scripts/lib/llm-pool.sh")
    (portal / "infra/.env").write_text(infra_env, encoding="utf-8")
    home = tmp_path / "home"; home.mkdir()
    target = {"agent-server": tmp_path / "HWAXAgentServer/.env", "ai-data-hub": tmp_path / "AIDataHub/deploy/apptainer/.env"}[svc]
    target.parent.mkdir(parents=True)
    if existing is not None:
        target.write_text(existing, encoding="utf-8")
    r = subprocess.run(["bash", str(portal / "infra/env-kits/apply-envs.sh"), svc], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"→ {target}" in r.stdout, "임시 박스의 형제 리포가 아닌 곳에 적었다"
    return target.read_text(encoding="utf-8"), r.stdout, r.stderr


def _v(env: str, key: str) -> list[str]:
    return re.findall(rf"^{key}=(.*)$", env, re.M)


def test_풀이_꺼져_있으면_직접_주소(tmp_path):
    env, out, err = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_MODEL=glm\nLLM_ROUTER_PORT={_dead_port()}\n")
    assert _v(env, "VLLM_BASE_URL") == [DIRECT] and _v(env, "VLLM_MODEL") == ["glm"]
    assert "라우터" not in out + err


def test_풀이_켜져_있고_라우터가_답하면_라우터_주소(tmp_path, router):
    """**이 시험이 이 파일의 이유다** — 1i 뒤 3.5 에서 더해진 키가 직접 주소로 남지 않는다. 다른 마커(모델·키)는 종전 그대로다."""
    env, out, _ = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_MODEL=glm\nLLM_API_KEY=k1\n"
                                    f"LLM_UPSTREAMS={DIRECT},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    assert _v(env, "VLLM_BASE_URL") == [f"http://127.0.0.1:{router['port']}/v1"], env
    assert _v(env, "VLLM_MODEL") == ["glm"] and _v(env, "VLLM_API_KEY") == ["k1"], "모델·키는 그대로 정본에서 온다"
    assert "VLLM_BASE_URL: LLM 풀이 켜져 있다 — 라우터 주소로 적는다" in out


def test_다른_킷의_LLM_주소도_같다(tmp_path, router):
    env, _, _ = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={DIRECT},{S2}\nLLM_ROUTER_PORT={router['port']}\n",
                       svc="ai-data-hub")
    assert _v(env, "OPENAI_BASE_URL") == [f"http://127.0.0.1:{router['port']}/v1"]


@pytest.mark.parametrize("case", ["올라온 서버 0", "답 없음", "모델 다름", "모델 대조 전"])
def test_라우터가_쓸_수_없으면_직접_주소와_한_줄(tmp_path, router, case):
    """1i 가 사본을 바꾸는 조건과 같다 — 서버 하나 이상이 올라왔고 **모델이 같다**고 답할 때만 라우터(반대 검토 M5)."""
    port = router["port"]
    if case == "답 없음":
        port = _dead_port()
    elif case == "모델 다름":
        router["body"] = {**router["body"], "status": "degraded", "models": {"match": False}}
    elif case == "모델 대조 전":
        router["body"] = {**router["body"], "models": {"match": None}}
    else:
        router["body"] = {"status": "down", "upstreams_total": 2, "upstreams_up": 0, "inflight": 0}
    env, _, err = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={DIRECT},{S2}\nLLM_ROUTER_PORT={port}\n")
    assert _v(env, "VLLM_BASE_URL") == [DIRECT], "라우터가 쓸 수 없는데 새 키를 라우터로 적었다 — 그 서비스만 LLM 을 잃는다"
    assert "라우터" in err and "직접 주소" in err


def test_직접_주소가_없어도_라우터가_답하면_라우터(tmp_path, router):
    env, _, _ = _apply(tmp_path, f"LLM_UPSTREAMS={DIRECT},{S2}\nLLM_ROUTER_PORT={router['port']}\n")
    assert _v(env, "VLLM_BASE_URL") == [f"http://127.0.0.1:{router['port']}/v1"]


def test_있는_키는_건드리지_않는다(tmp_path, router):
    """'없는 키만 더한다' 계약 그대로다 — 있는 사본을 바꾸는 것은 1i 의 일이다(관리하는 값만 · 백업 먼저)."""
    env, _, _ = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={DIRECT},{S2}\nLLM_ROUTER_PORT={router['port']}\n",
                       existing=f"VLLM_BASE_URL={DIRECT}\n")
    assert _v(env, "VLLM_BASE_URL") == [DIRECT]


def test_틀린_목록이면_직접_주소(tmp_path, router):
    env, _, _ = _apply(tmp_path, f"LLM_BASE_URL={DIRECT}\nLLM_UPSTREAMS={DIRECT}, {S2}\nLLM_ROUTER_PORT={router['port']}\n")
    assert _v(env, "VLLM_BASE_URL") == [DIRECT]


def test_LLM_이_아무데도_없으면_종전처럼_건너뛴다(tmp_path):
    env, out, _ = _apply(tmp_path, f"OTHER=1\nLLM_ROUTER_PORT={_dead_port()}\n")
    assert _v(env, "VLLM_BASE_URL") == [] and "VLLM_BASE_URL: RA .env 에 LLM_BASE_URL 없음 → 건너뜀" in out
