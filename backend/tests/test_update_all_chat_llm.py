# update-all 3.5c — infra/.env 의 CHAT_LLM_* 를 에이전트 서버 .env 로 맞추는가(없으면 ○ · 적으면 맞추고 기록 · 빈 값이나 지운 줄이면 끔)
"""왜 — 챗만 stcx GPU LLM 으로 보내는 설정(docs/chat-llm-stcx)의 정본은 포털 infra/.env 다. 설정 킷은 없는 키만 더하므로 그대로면 바꾸거나
끈 값이 에이전트 서버 사본에 닿지 않는다(LLM 풀 LP-D4 와 같은 꼴). 3.5c 가 매 실행 맞춘다.

  · infra/.env 에 키가 없으면 ○ 로 남기고 에이전트 서버 .env 를 건드리지 않는다(사람이 직접 적은 값은 그대로).
  · 적으면 주소 · 모델(· 키)을 맞추고, 적은 주소를 infra/.state/chat-llm.url 에 남긴다. 그 서버가 모델을 내는지 본다(못 닿으면 ⚠ 만).
  · 빈 값이면 끈다. 줄을 지웠으면 3.5c 가 적었던 값일 때만 끈다.
  · 모양이 틀리거나 모델이 없으면 ✗ 이고 바꾸지 않는다. 키는 출력에 싣지 않는다.

update-all 원문의 구획과 도우미를 그대로 임시 포털에서 돌린다(test_call_trace 의 5c 와 같은 방식).
"""
import json
import os
import shutil
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "infra" / "scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")


def _region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Models(BaseHTTPRequestHandler):
    served: list = []
    seen_auth: list = []

    def do_GET(self):  # noqa: N802
        type(self).seen_auth.append(self.headers.get("Authorization"))
        body = json.dumps({"data": [{"id": m, "max_model_len": 262_144} for m in type(self).served]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def models_server():
    """/v1/models 만 내는 작은 서버 — served 에 넣은 모델을 낸다. → (주소, 처리기 클래스)."""
    handler = type("_M", (_Models,), {"served": ["qwen3.8-flash-next"], "seen_auth": []})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1", handler
    srv.shutdown()
    srv.server_close()


class _Box:
    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts/lib").mkdir(parents=True)
        shutil.copy(SCRIPTS / "lib/skip-ledger.sh", self.repo / "infra/scripts/lib/skip-ledger.sh")
        self.agent_env = self.tmp / "agent.env"
        self.ledger = self.tmp / "ledger"
        self.ledger.write_text("")
        self.rec = self.repo / "infra/.state/chat-llm.url"

    def run(self, infra_env: str, agent_env: str | None = None) -> str:
        (self.repo / "infra/.env").write_text(infra_env, encoding="utf-8")
        if agent_env is not None:
            self.agent_env.write_text(agent_env, encoding="utf-8")
        helpers = "\n".join([_region("_envfile_value() {", "\n}\n") + "\n}",
                             _region("_ra_envv() {", "\n"),
                             _region("_upsert_kv() {", "\n}\n") + "\n}"])
        body = _region("# ── 3.5c) 챗 전용 LLM", "# ── 3.5c 끝")
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'SELF_REPO="{self.repo}"', f'AGENT_ENV="{self.agent_env}"',
            f'[ "$(cd "$SELF_REPO" && pwd)" = "{self.repo}" ] || exit 97',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"', f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"',
            helpers, body, "echo END",
        ])
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env=env)
        assert r.returncode != 97 and "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def agent(self, key: str) -> str | None:
        for ln in reversed(self.agent_env.read_text(encoding="utf-8").splitlines()):
            if ln.startswith(f"{key}="):
                return ln.split("=", 1)[1]
        return None


@pytest.fixture()
def box(tmp_path):
    return _Box(tmp_path)


def _tagged(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


def test_infra_env_에_없으면_안_켠_기능으로_남기고_사람이_적은_값은_그대로다(box):
    out = box.run("OTHER=1\n", "VLLM_BASE_URL=http://glm/v1\nCHAT_LLM_BASE_URL=http://manual:1/v1\n")
    assert not _tagged(out, "OK:") and not _tagged(out, "FAIL:") and not _tagged(out, "BAD:"), out
    assert box.ledger.read_text().startswith("챗 전용 LLM\t") and "server-setup.md" in box.ledger.read_text()
    assert box.agent("CHAT_LLM_BASE_URL") == "http://manual:1/v1", "사람이 직접 적은 값 — 3.5c 가 적은 기록이 없다"


def test_적으면_맞추고_기록하며_그_서버가_모델을_내는지_본다(box, models_server):
    url, h = models_server
    out = box.run(f"CHAT_LLM_BASE_URL={url}\nCHAT_LLM_MODEL=qwen3.8-flash-next\n", "VLLM_BASE_URL=http://glm/v1\n")
    assert box.agent("CHAT_LLM_BASE_URL") == url and box.agent("CHAT_LLM_MODEL") == "qwen3.8-flash-next"
    assert box.agent("VLLM_BASE_URL") == "http://glm/v1", "심의 LLM 은 그대로"
    assert box.rec.read_text().strip() == url and oct(box.rec.stat().st_mode & 0o777) == "0o600"
    assert any("챗 전용 LLM:" in ln for ln in _tagged(out, "OK:")), out
    assert any("낸다(창 262144" in ln for ln in _tagged(out, "OK:")), out
    assert oct(box.agent_env.stat().st_mode & 0o777) in ("0o600", "0o644")


def test_모델이_없거나_닿지_않으면_경고만_하고_적기는_한다(box, models_server):
    url, h = models_server
    h.served = ["other-model"]
    out = box.run(f"CHAT_LLM_BASE_URL={url}\nCHAT_LLM_MODEL=qwen3.8-flash-next\n", "")
    assert any("qwen3.8-flash-next 이 없다" in ln and "other-model" in ln for ln in _tagged(out, "BAD:")), out
    assert box.agent("CHAT_LLM_BASE_URL") == url and not _tagged(out, "FAIL:")
    dead = f"http://127.0.0.1:{_free_port()}/v1"
    out = box.run(f"CHAT_LLM_BASE_URL={dead}\nCHAT_LLM_MODEL=q\n")
    assert any("닿지 않는다" in ln and "GLM 으로 넘겨" in ln for ln in _tagged(out, "BAD:")), out
    assert box.agent("CHAT_LLM_BASE_URL") == dead and not _tagged(out, "FAIL:")


def test_빈_값이면_끄고_줄을_지우면_3_5c_가_적었던_값일_때만_끈다(box, models_server):
    url, _ = models_server
    on = f"CHAT_LLM_BASE_URL={url}\nCHAT_LLM_MODEL=qwen3.8-flash-next\n"
    box.run(on, "")
    out = box.run("CHAT_LLM_BASE_URL=\n")
    assert box.agent("CHAT_LLM_BASE_URL") == "" and not box.rec.exists(), out
    assert any("껐다" in ln for ln in _tagged(out, "OK:")), out
    out = box.run("CHAT_LLM_BASE_URL=\n")
    assert any("꺼짐" in ln for ln in _tagged(out, "OK:")), "이미 꺼져 있으면 그렇다고만"
    box.run(on)
    out = box.run("OTHER=1\n")                                   # 줄을 지웠다 — 3.5c 가 적었던 값이다
    assert box.agent("CHAT_LLM_BASE_URL") == "" and not box.rec.exists()
    assert any("줄이 빠졌다" in ln for ln in _tagged(out, "OK:")), out
    box.run(on)
    box.agent_env.write_text(box.agent_env.read_text().replace(url, "http://hand:9/v1"))   # 사람이 바꿨다
    out = box.run("OTHER=1\n")
    assert box.agent("CHAT_LLM_BASE_URL") == "http://hand:9/v1" and box.ledger.read_text().count("챗 전용 LLM\t") >= 1


@pytest.mark.parametrize("infra", ["CHAT_LLM_BASE_URL=http://u:p@host/v1\nCHAT_LLM_MODEL=q\n",
                                   "CHAT_LLM_BASE_URL=ftp://host/v1\nCHAT_LLM_MODEL=q\n",
                                   "CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\n"])
def test_모양이_틀리거나_모델이_없으면_실패하고_바꾸지_않는다(box, infra):
    out = box.run(infra, "VLLM_BASE_URL=http://glm/v1\n")
    assert _tagged(out, "FAIL:") and box.agent("CHAT_LLM_BASE_URL") is None and not box.rec.exists(), out


def test_키는_출력에_싣지_않고_서버에는_보낸다(box, models_server):
    url, h = models_server
    out = box.run(f"CHAT_LLM_BASE_URL={url}\nCHAT_LLM_MODEL=qwen3.8-flash-next\nCHAT_LLM_API_KEY=s3cr3t-chat-key\n", "")
    assert "s3cr3t-chat-key" not in out, "키가 화면에 찍혔다"
    assert h.seen_auth == ["Bearer s3cr3t-chat-key"] and box.agent("CHAT_LLM_API_KEY") == "s3cr3t-chat-key"
