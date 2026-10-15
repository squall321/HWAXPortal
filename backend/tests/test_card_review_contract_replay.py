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


# ── 외부 응답자(X-3a) — 엔진의 외부 길 계약 예제(tests/fixtures/external_llm/contract/)를 중계에 흘린다 ─────────────────────
# GLM 예제와 따로 둔 디렉터리다(엔진 X-1 — 리스크 앱이 GLM 예제를 바이트째 복사한다). limits 는 질의 문자열(?llm=external)로, plan·run 은
# 본문의 llm·consent_external 로 외부 길을 고른다. 중계는 질의에서 엔진이 읽는 이름만 옮기고 본문은 신원 칸 넷만 덮어쓴다.
_EXT_CONTRACT = _SIBLING / "tests" / "fixtures" / "external_llm" / "contract"
_IDENT = ("groups", "user_email", "user_pat", "entitlements")


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _IDENT}


def _ext() -> Path:
    assert _EXT_CONTRACT.is_dir(), f"형제 리포는 있는데 외부 응답자 계약 예제가 없다 — {_EXT_CONTRACT}"
    return _EXT_CONTRACT


def _ext_rejects() -> list[tuple[str, dict]]:
    if not _SIBLING.is_dir():
        return []
    data = json.loads((_ext() / "rejects.json").read_text(encoding="utf-8"))
    return [(k, v) for k, v in data.items() if not k.startswith("_")]


def test_외부_예제가_빠짐없이_있다():
    names = {k for k, _ in _ext_rejects()}
    want = {"external_llm_disabled.limits", "bad_request.limits", "external_consent_required.run"}
    assert want <= names, sorted(names)
    for name in ("limits_external.json", "plan_external_req.json", "req_verdict_ok.json"):
        assert (_ext() / name).is_file(), name


def test_외부_limits_는_질의를_지나_엔진의_외부_예산이_그대로_오고_질의가_없으면_GLM_예산이다(portal):
    """종전 중계는 질의 문자열을 버려 ?llm=external 에도 GLM 예산(1M 창)이 왔다. 엔진 대역은 엔진처럼 질의의 llm 으로 가른다."""
    ext = json.loads((_ext() / "limits_external.json").read_text(encoding="utf-8"))
    glm = json.loads((_contract() / "limits_1m.json").read_text(encoding="utf-8"))
    assert ext["limits_rev"] != glm["limits_rev"], "두 길의 판이 같으면 이 시험이 가르지 못한다"
    _wire(lambda req: httpx.Response(200, json=ext if req.url.params.get("llm") == "external" else glm))
    assert portal.get("/agent/card-review/limits?llm=external").json() == ext, "외부 길을 물었는데 GLM 판이 왔다"
    assert portal.get("/agent/card-review/limits").json() == glm, "질의가 없으면 종전 그대로 GLM 예산이다"
    assert portal.get("/agent/card-review/limits?llm=glm").json() == glm


@pytest.mark.parametrize("code,case", _ext_rejects(), ids=lambda v: v if isinstance(v, str) else "")
def test_외부_길의_거절이_limits_plan_run_에서_상태와_본문_그대로_간다(portal, code, case):
    seen: list[httpx.Request] = []
    _wire(lambda req: seen.append(req) or httpx.Response(case["status"], json=case["body"]))
    route = code.rsplit(".", 1)[1]
    if route == "limits":
        llm = "claude" if code.startswith("bad_request.") else "external"     # 예제의 _how — 모르는 값은 'claude'
        r = portal.get(f"/agent/card-review/limits?llm={llm}")
        assert seen[0].url.query == f"llm={llm}".encode(), "엔진이 거절할 값을 포털이 고치거나 버렸다"
    else:
        name = "plan_external_req.json" if route == "plan" else "req_verdict_ok.json"
        r = portal.post(f"/agent/card-review/{route}", content=(_ext() / name).read_bytes(),
                        headers={"content-type": "application/json"})
    assert (r.status_code, r.json()) == (case["status"], case["body"]), code


@pytest.mark.parametrize("route,name", [("plan", "plan_external_req.json"), ("run", "req_verdict_ok.json")])
def test_외부_길의_plan_run_본문은_llm_과_동의를_그대로_싣고_신원_칸만_바뀐다(portal, route, name):
    raw = (_ext() / name).read_bytes()
    sent: list[dict] = []

    def answer(req: httpx.Request) -> httpx.Response:
        sent.append(json.loads(req.content))
        if route == "run":
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  stream=_Chunks((_ext() / "run_verdict_ok.sse").read_bytes()))
        return httpx.Response(200, json=json.loads((_ext() / "plan_external.json").read_text(encoding="utf-8")))

    _wire(answer)
    r = portal.post(f"/agent/card-review/{route}", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 200
    body = json.loads(raw)
    assert body["llm"] == "external"
    assert _strip(sent[0]) == _strip(body), "신원 칸 말고는 한 칸도 바뀌거나 빠지면 안 된다"
    if route == "run":
        assert sent[0]["consent_external"] is True, "반출 동의는 JSON true 그대로 가야 엔진이 연다"
        assert sent[0]["user_email"] == "u1@hwax.local", "과제 주인은 포털이 덮어쓴 신원이다"


def test_limits_가_옮기는_질의_이름은_엔진이_읽는_이름과_같다():
    """엔진 GET /card-review/limits 가 질의에서 읽는 이름(소스)과 중계의 _CR_LIMITS_QUERY 를 견준다. 엔진이 새 이름을 읽게 됐는데 중계가
    모르면 그 이름은 포털을 거치는 길(리스크 앱)에서만 말없이 사라진다 — X-3a 의 llm 이 그렇게 사라졌다."""
    import re

    from app.agent.routes import _CR_LIMITS_QUERY

    src = (_SIBLING / "card_review.py").read_text(encoding="utf-8")
    body = src[src.index('@router.get("/limits")'):]
    body = body[: body.index("\n@router.")]
    names = set(re.findall(r'request\.query_params\.get\("([a-z_]+)"\)', body))
    assert names, "엔진 limits 가 질의에서 읽는 이름을 못 찾았다 — 모양이 바뀌었으면 이 추출도 고쳐라"
    assert names == set(_CR_LIMITS_QUERY), (
        f"엔진이 읽는 질의 이름 {sorted(names)} 과 중계가 옮기는 이름 {sorted(_CR_LIMITS_QUERY)} 이 다르다 — "
        "routes._CR_LIMITS_QUERY 를 고친다")
