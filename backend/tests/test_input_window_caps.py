# 포털 입력 상한이 1백만 토큰 창보다 먼저 묶이지 않는지 — 작은 창 시절의 고정 상한이 받을 수 있는 글을 422 로 막았다
"""포털은 에이전트 서버·엔진 앞의 입구다. 여기 상한은 폭주 방지선이어야 하는데, 몇 칸은 16K·128K 창 시절에 그 창에 맞춰
박은 값이었다 — 챗 이력 한 건 24,000자 · 메시지 65,536자 · 이어하기 요약 24,000자 · 사람 의견 8,000자 · 심의 전 도우미(좌석 추천·
되묻기·VOC) 화두 8,192자 · 서버 대화 한 칸 20,000자 · 양보 불가 조항 12건. 운영 모델(GLM-5.2)의 창은 1,048,576 토큰이다
(docs/risk-review-redesign D-20·D-21). 심의 결정문 하나가 13,000~75,000자라, 결정문이 든 대화를 이어가거나 그 결정문을
이어하기에 실으면 이 칸들이 먼저 422 를 냈다(프론트는 그 전에 조용히 잘라 보냈다).

이제 글 칸의 상한은 창 하나에 들어갈 수 있는 가장 긴 글(1,048,576 토큰 × 4자)에서 유도한다. 창에 넣을 길이는 창을 아는 쪽
(에이전트 서버 이력 예산·엔진 _resolve_opts)이 정하고 줄였으면 알린다 — 포털은 넘는 것을 422 로 소리 내 막을 뿐 자르지 않는다.
"""
import json

import httpx
import pytest
from pydantic import ValidationError

from app.agent import routes as R


def _cap(model, field: str) -> int:
    caps = [m.max_length for m in model.model_fields[field].metadata if getattr(m, "max_length", None) is not None]
    assert caps, f"{model.__name__}.{field} 에 max_length 가 없다 — 폭주 방지선이 없다"
    return caps[0]


# ── 특성화 — 고치기 전 코드에서도 초록이어야 한다 ─────────────────────────────────────────────
def test_종전_한도_안의_요청은_그대로_받는다():
    body = R.ChatRequest(message="가" * 65_536, history=[{"role": "assistant", "content": "나" * 24_000}] * 3,
                         delib_opts={"human_note": "다" * 8_000, "continue_summary": "라" * 24_000,
                                     "non_negotiables": ["조항"] * 12})
    assert len(body.message) == 65_536 and len(body.history) == 3
    assert body.delib_opts.model_dump(exclude_none=True)["continue_summary"] == "라" * 24_000


def test_항목_수_상한은_그대로다():
    """건수 상한 가운데 엔진·프론트와 계약한 것(좌석 20·사전 근거 120·이력 160)은 이 걸음에서 바꾸지 않는다."""
    assert _cap(R.ChatRequest, "history") == 160
    assert _cap(R.DelibOpts, "personas") == 20
    assert _cap(R.DelibOpts, "evidence") == 120


# ── 재현 — 고치기 전 코드에서 붉다 ───────────────────────────────────────────────────────────
def test_글_칸의_상한은_1M_창에서_유도한다():
    assert R._WINDOW_CHARS == 1_048_576 * 4
    for model, field in ((R.ChatHistoryMessage, "content"), (R.ChatRequest, "message"),
                         (R.DelibOpts, "human_note"), (R.DelibOpts, "continue_summary"),
                         (R.ExpertsRequest, "message"), (R.ClarifyRequest, "message"),
                         (R.VocPreviewRequest, "message"), (R.TopicRequest, "fallback"),
                         (R.ConvMessageIn, "content")):
        assert _cap(model, field) == R._WINDOW_CHARS, f"{model.__name__}.{field} 가 창에서 유도되지 않았다"


def test_결정문이_든_대화를_이어간다():
    """**이 시험이 이 파일의 이유다** — 75,000자 결정문 한 건이 이력에 있으면 종전엔 422 였다(프론트가 24,000자로 잘라 보내 숨었다)."""
    decision = "(1) 결론 — " + "브래킷 두께 0.6 mm 에서 힌지 응력이 항복을 넘는다. " * 2500
    assert len(decision) > 75_000
    body = R.ChatRequest(message="이어서 (7) 신뢰도를 다시 봐 줘", history=[{"role": "user", "content": "/심의 x"},
                                                                      {"role": "assistant", "content": decision}])
    assert body.history[-1].content == decision


def test_긴_메시지와_이어하기_요약과_사람_의견을_받는다():
    body = R.ChatRequest(message="가" * 100_000,
                         delib_opts={"continue_summary": "라" * 31_000, "human_note": "다" * 9_000,
                                     "non_negotiables": [f"조항 {i}" for i in range(21)]})
    got = body.delib_opts.model_dump(exclude_none=True)
    assert len(got["continue_summary"]) == 31_000 and len(got["human_note"]) == 9_000
    assert len(got["non_negotiables"]) == 21, "21석 패널(20석 + 지정 반대석)의 조항이 422 로 막혔다"


def test_조항_건수는_한_회차가_낼_수_있는_수까지다():
    """조항은 수렴 라운드 좌석마다 하나다 — 좌석 상한 × 라운드 상한이면 한 회차가 낼 수 있는 전부다."""
    cap = _cap(R.DelibOpts, "non_negotiables")
    assert cap == _cap(R.DelibOpts, "personas") * 8
    R.DelibOpts(non_negotiables=["조항"] * cap)
    with pytest.raises(ValidationError):
        R.DelibOpts(non_negotiables=["조항"] * (cap + 1))


def test_심의_전_도우미는_챗_화두를_그대로_받는다():
    """좌석 추천·되묻기·VOC 는 화두를 8,192자까지만 받았다 — 챗 메시지(65,536)보다 작아 긴 화두에서 422 → 빈 추천이 됐다."""
    q = "화두 " * 6_000
    for model in (R.ExpertsRequest, R.ClarifyRequest, R.VocPreviewRequest):
        assert model(message=q).message == q


def test_이력_합계가_창_하나를_넘으면_소리_내_막는다():
    """항목 상한을 창에서 유도하면 160건 × 그 값이 된다 — 합계는 창 하나로 묶는다. 넘으면 자르지 않고 422 다."""
    big = R._WINDOW_CHARS // 2 + 1
    with pytest.raises(ValidationError, match="이력"):
        R.ChatRequest(message="x", history=[{"role": "user", "content": "가" * big}, {"role": "assistant", "content": "나" * big}])
    R.ChatRequest(message="x", history=[{"role": "user", "content": "가" * (big - 1)},
                                        {"role": "assistant", "content": "나" * (big - 1)}])


def test_서버_대화_한_칸은_2만자에서_막지_않는다():
    """MCP·리스크 앱·JS 파이프라인이 발언을 넣는 입구다. 2만 자를 넘는 발언 하나가 일괄 생성 전체를 422 로 떨어뜨렸다."""
    m = R.ConvMessageIn(role="persona", content="가" * 30_000)
    assert len(m.content) == 30_000


def test_게이트웨이가_읽는_줄_모양을_지킨다():
    """게이트웨이 시험(test_대화_저장_상한은_포털_입력_모델의_한도를_넘지_않는다)이 이 줄을 `max_length=숫자` 로 읽는다 — 이름으로 바꾸면
    그쪽이 '못 읽었다' 로 붉다. 숫자는 창에서 유도한 값과 같아야 한다."""
    import inspect
    import re

    src = inspect.getsource(R.ConvMessageIn)
    m = re.search(r"^\s+content:[^\n]*max_length=(\d+)", src, re.M)
    assert m and int(m.group(1)) == R._WINDOW_CHARS


def test_에이전트_서버_오류_사유를_자르면_원래_길이를_감사에_남긴다():
    """에이전트 서버가 422 등을 내면 포털은 사유를 감사에만 남긴다. 200자에서 표식 없이 잘라 어느 칸이 넘었는지가 사라졌다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    detail = json.dumps({"detail": [{"loc": ["body", "message"], "msg": "too long " + "x" * 5000}]})
    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u-audit", email="u@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app) as c:
            real = app.state.agent_client
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(422, content=detail.encode())))
            try:
                r = c.post("/agent/chat", json={"message": "x"})
            finally:
                app.state.agent_client = real
            row = app.state.agent_audit._conn.execute(
                "SELECT meta FROM agent_audit WHERE principal = 'u-audit' AND event = 'chat_error' ORDER BY id DESC LIMIT 1"
            ).fetchone()
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert r.status_code == 200 and "agent_422" in r.text
    meta = json.loads(row[0])
    assert meta["upstream"] == 422 and meta["detail"].startswith('{"detail": [{"loc": ["body", "message"]')
    assert f"원문 {len(detail):,}자" in meta["detail"], "잘랐으면 원래 길이를 남긴다"
