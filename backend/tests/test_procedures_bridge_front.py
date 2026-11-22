# 절차 실행 화면의 넘기기 단추 둘(심의로 넘기기 · 챗으로 가져가기)이 서버 계약대로 배선됐는지 — 프론트 원문으로 본다
"""화면은 **실행 id 만** 넘긴다(docs/procedures W-114 · W-115). 근거를 화면이 지어 보내면 서버가 그 내용을 보증할 수 없다 — 가려진 값이 풀리거나
실패 · 실행 여부 모름 표지가 빠져도 모른다. 그래서 여기서 보는 것은 셋이다.
  · 실행 상세는 미리보기(`runHandoff`)의 수만 들고 심의 화면으로 간다 — 근거 본문을 만들지 않는다.
  · 심의 화면은 그 실행 id 를 `procedure_run` 칸으로만 싣는다(포털 DelibOpts 에 선언된 칸 — 계약 시험이 같이 본다).
  · 심의 유형 메뉴에 리스크 심사가 없다(입구는 리스크 앱 하나 — 10-31 A17). 서버도 거절한다(tests/test_procedures_delib_bridge.py).
"""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.routes import DelibOpts

_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _read(rel: str) -> str:
    return (_SRC / rel).read_text(encoding="utf-8")


def test_실행_상세는_실행_id_와_수만_넘기고_근거를_짓지_않는다():
    page = _read("pages/procedures/ProceduresPage.tsx")
    assert "runHandoff(watched.id)" in page and "runToChat(watched.id)" in page
    go = page[page.index("runHandoff(watched.id)"):]
    go = go[:go.index("심의로 넘기기")]
    assert "nav('/deliberate'" in go and "procedureRun" in go and "run_id: h.run_id" in go
    assert "evidence" not in go.replace("evidence_count", ""), "화면이 근거를 지어 넘기면 서버가 그 내용을 보증하지 못한다"
    assert "stepResult" not in page[page.index("function RunDetailView"):], "실행 상세가 단계 결과를 읽어 근거로 옮기지 않는다"
    api = _read("api/procedures.api.ts")
    assert "`/runs/${runId}/handoff`" in api and "`/runs/${runId}/chat`" in api


def test_심의_화면은_실행_id_를_procedure_run_칸으로만_싣는다():
    page = _read("pages/DeliberatePage.tsx")
    assert "procedure_run" in DelibOpts.model_fields
    sends = re.findall(r"procedure_run:\s*([A-Za-z_.]+)", page)
    assert sends == ["fromRun.run_id"], sends
    # 실행 id 의 꼴은 서버 칸의 꼴과 같다 — 다른 꼴은 화면이 싣지 않는다
    assert "/^[0-9a-f]{32}$/" in page
    assert DelibOpts(procedure_run="0123456789abcdef" * 2).procedure_run
    with pytest.raises(ValidationError):
        DelibOpts(procedure_run="0123456789ABCDEF" * 2)
    # 주소의 상태를 비운다 — 새로고침이 같은 실행을 다시 붙이지 않게
    assert "navigate('.', { replace: true, state: null })" in page


def test_심의_유형_메뉴에_리스크_심사가_없다():
    tax = _read("components/chat/delibTaxonomy.ts")
    ids = set(re.findall(r"id:\s*'([a-z-]+)'", tax))
    assert ids and "default" in ids, f"유형 추출이 깨졌다: {sorted(ids)}"
    assert not {i for i in ids if i.startswith("risk")}, "리스크 심사의 입구는 리스크 앱 하나다(10-31 A17) — 메뉴에 두지 않는다"
    assert "risk-review" not in re.sub(r"//.*", "", tax), "주석 밖에 risk-review 가 있다"


def test_챗으로_가져간_대화는_챗_목록의_거름에_걸리는_종류다():
    """챗 목록은 종류로 거른다(kind === serverKind). 다른 종류로 만든 대화는 어느 탭에도 안 보인다(LO-D2)."""
    from app.procedures import routes as R

    ctx = _read("state/ChatContext.tsx")
    assert "list.filter((m) => m.kind === serverKind)" in ctx
    assert re.search(r"<ChatProvider serverKind=\"chat\">", _read("App.tsx"))
    assert R.CHAT_KIND == "chat"
