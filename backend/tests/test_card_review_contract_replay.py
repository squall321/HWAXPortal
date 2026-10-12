# 에이전트 서버가 만든 카드 대조 계약 예제(run SSE·거절·팩 오류)를 포털 중계에 그대로 흘려 바이트·상태·본문이 바뀌지 않는지 본다
"""리스크 심사 재설계 M2 — 반대 검토 RB-10. 중계 시험(test_card_review_relay.py)은 손으로 쓴 SSE 로만 돌아, 엔진이 실제로 내는
프레임과 오류 본문이 중계를 지나는지 아무도 보지 않았다. 예제는 형제 리포 HWAXAgentServer 의
`tests/fixtures/card_review/contract/` 에 있고 엔진의 실제 라우트가 가짜 LLM 으로 만든 것이다. 형제 리포가 곁에 없으면 건너뛰고,
곁에 있는데 예제를 못 읽으면 건너뛰지 않고 실패한다(P-22 — 조용한 skip 이 계약 어긋남을 숨긴다).
"""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.provider import Principal
from app.deps import principal_pat_or_session
from app.main import app

_SIBLING = Path(__file__).resolve().parents[3] / "HWAXAgentServer"
_CONTRACT = _SIBLING / "tests" / "fixtures" / "card_review" / "contract"
_WHO = Principal(subject="u1", email="u1@hwax.local", display_name="U",
                 groups=["eng-team", "feat:deliberation", "plat:aidatahub"])

pytestmark = pytest.mark.skipif(not _SIBLING.is_dir(), reason="형제 리포 HWAXAgentServer 가 곁에 없다")


class _Audit:
    def record(self, **kw) -> None:
        pass


def _contract() -> Path:
    assert _CONTRACT.is_dir(), f"형제 리포는 있는데 계약 예제가 없다 — {_CONTRACT}"
    return _CONTRACT


def _scenes() -> list[Path]:
    files = sorted(_contract().glob("run_*.sse")) if _SIBLING.is_dir() else []
    return files


def _bodies(name: str) -> list[tuple[str, dict]]:
    if not _SIBLING.is_dir():
        return []
    data = json.loads((_contract() / name).read_text(encoding="utf-8"))
    return [(k, v) for k, v in data.items() if not k.startswith("_")]


@pytest.fixture
def portal():
    app.dependency_overrides[principal_pat_or_session] = lambda: _WHO
    try:
        with TestClient(app) as c:
            keep = ("card_review_client", "agent_audit")
            saved = {k: getattr(app.state, k) for k in keep}
            app.state.agent_audit = _Audit()
            try:
                yield c
            finally:
                for k, v in saved.items():
                    setattr(app.state, k, v)
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


class _Chunks(httpx.AsyncByteStream):
    """상류 SSE 본문 — 프레임 경계와 맞지 않는 크기로 나눠 흘린다(중계는 경계와 무관하게 바이트를 그대로 넘겨야 한다)."""

    def __init__(self, raw: bytes, size: int = 97) -> None:
        self.raw, self.size = raw, size

    async def __aiter__(self):
        for i in range(0, len(self.raw), self.size):
            yield self.raw[i:i + self.size]

    async def aclose(self) -> None:
        pass


def _wire(answer) -> None:
    app.state.card_review_client = httpx.AsyncClient(transport=httpx.MockTransport(answer),
                                                     timeout=httpx.Timeout(30.0, read=60.0))


def _run_body() -> bytes:
    return (_contract() / "req_verdict_fwd.json").read_bytes()


def test_예제가_빠짐없이_있다():
    names = [p.name for p in _scenes()]
    assert len(names) >= 20, f"run 예제가 {len(names)}장이다 — 엔진이 장면을 줄였거나 경로가 바뀌었다"
    assert _bodies("rejects.json") and _bodies("pack_errors.json")


@pytest.mark.parametrize("scene", _scenes(), ids=lambda p: p.stem)
def test_엔진의_run_프레임이_바이트_그대로_지난다(portal, scene):
    raw = scene.read_bytes()
    _wire(lambda req: httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=_Chunks(raw)))
    r = portal.post("/agent/card-review/run", content=_run_body(), headers={"content-type": "application/json"})
    assert r.status_code == 200
    assert r.content == raw, "중계가 엔진 프레임을 바꿨다 — 앱이 읽는 바이트가 엔진의 것과 다르다"


@pytest.mark.parametrize("code,case", _bodies("rejects.json"), ids=lambda v: v if isinstance(v, str) else "")
def test_엔진의_스트림_전_거절이_상태와_본문_그대로_간다(portal, code, case):
    _wire(lambda req: httpx.Response(case["status"], json=case["body"]))
    r = portal.post("/agent/card-review/run", content=_run_body(), headers={"content-type": "application/json"})
    assert (r.status_code, r.json()) == (case["status"], case["body"]), code


@pytest.mark.parametrize("code,case", _bodies("pack_errors.json"), ids=lambda v: v if isinstance(v, str) else "")
def test_엔진의_팩_오류가_상태와_본문_그대로_간다(portal, code, case):
    _wire(lambda req: httpx.Response(case["status"], json=case["body"]))
    r = portal.post("/agent/card-review/pack", json={"agent_key": "mech-a"})
    assert (r.status_code, r.json()) == (case["status"], case["body"]), code
