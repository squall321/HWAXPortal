# 절차 실행기와 대화 목록이 목록을 말없이 끊지 않는지 — 사람이 고를 후보·뒤 항목 이름·대화 목록의 총수를 함께 싣는다
"""절차 실행기는 LLM 을 쓰지 않는다 — 여기 상한은 창이 아니라 사람이 훑는 목록의 크기다. 그래서 값은 두되 **끊었다는 사실**을
남긴다(docs/risk-review-redesign D-21 — 남는 절단은 조용하지 않게).

  - 고르기(ask·ask_many)는 후보를 50개만 보여 주는데 총수를 싣지 않아, 51번째부터는 있는 줄도 모른 채 고를 수 없었다
    (on_many=fail 만 '룰이 N개를 골랐다' 로 총수를 말했다).
  - 2단 도구 뒤 항목 이름(dispatcher_items)을 200개에서 말없이 끊었다 — 이름 목록이라 가볍다. 끊지 않는다.
  - 서버 대화 목록(GET /agent/conversations)은 최근 100건만 주는데 총수가 없어, Claude(MCP)·다른 기기에서 101번째부터는
    없는 대화로 보였다.
"""
from tests.test_procedures_select import _MULTI, _pick


def _rows(n: int) -> list[dict]:
    return [{"name": f"PART_{i:03d}", "id": i, "value": f"V{i}"} for i in range(n)]


def test_고르기_후보는_종전대로_보여_준다():
    out, _scope, store = _pick(_rows(3))
    assert out["kind"] == "select_ask" and len(out["candidates"]) == 3
    assert out["candidates_total"] == 3 and store.finished[-1]["notes"]["candidates_total"] == 3


def test_고르기_후보를_끊으면_총수를_싣는다():
    out, _scope, store = _pick(_rows(60))
    assert len(out["candidates"]) == 50 and out["candidates_total"] == 60
    assert store.finished[-1]["notes"]["candidates_total"] == 60, "실행 기록(원장)에도 남아야 화면이 '60개 중 50개' 를 말한다"
    out, _scope, store = _pick(_rows(60), **_MULTI)
    assert out["kind"] == "select_ask_many" and out["candidates_total"] == 60
    assert store.finished[-1]["notes"]["candidates_total"] == 60


def test_뒤_항목_이름을_200개에서_끊지_않는다():
    from app.procedures.runner import _names_of

    got = _names_of({"operations": [{"name": f"op_{i}", "summary": "한 줄"} for i in range(250)]})
    assert len(got) == 250 and got[-1]["name"] == "op_249"


def test_대화_목록은_총수와_끊었는지를_싣는다():
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u-conv-list", email="u@hwax.local", display_name="U", groups=[])
    try:
        with TestClient(app) as c:
            store = app.state.conv_store
            for i in range(103):
                store.create(owner_sub="u-conv-list", title=f"대화 {i}", kind="chat")
            body = c.get("/agent/conversations").json()
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert len(body["conversations"]) == 100
    assert body["total"] == 103 and body["truncated"] is True
