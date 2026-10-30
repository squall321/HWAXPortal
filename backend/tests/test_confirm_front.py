# 확인 카드(10-30 HA-29) · 짚기만 한 자기검증(HA-27)이 웹 챗에 그려지는지 — SSE confirm 받기 · 단추 · 카드 상태 · 영속 · 두 리포 계약
"""에이전트서버가 사람이 시키지 않은 잡 · 쓰기를 보내지 않고 확인 카드로 멈춘다(HA-29). 본문 끝의 카드 글(서버 사본 · 다른 기기)과 함께
SSE `confirm` 을 내고, 화면은 그 카드에 '실행' · '취소' 단추를 단다 — 단추는 서버가 준 승인 · 거절 글을 다음 말로 보낸다. 자기검증은
검토자의 고침이 원문과 어긋나면 넣지 않고 짚기만 한다(HA-27 `flagged`).

순수 함수(카드 상태 confirm.ts · 브라우저 사본 chatStore.ts)는 옮겨 적어 node 로 돌리고(tests/test_front_window_payload.py 의 _node), 단추를
누르는 것은 tests/test_confirm_card_in_browser.py 가 실제 화면으로 본다. 사건 칸은 형제 리포 에이전트서버의 `_sse("confirm"` 과 맞댄다
(design-ha29 9절 33 — 칸 이름이 바뀌면 화면의 받기 가드가 그 사건을 말없이 버려 단추가 사라진다).
"""
import ast
import re
import shutil
from pathlib import Path

import pytest

from tests.test_front_window_payload import _FE, _msg, _node

_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
_AGENT = Path(__file__).resolve().parents[3] / "HWAXAgentServer" / "app.py"

_need_node = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)


def _read(rel: str) -> str:
    return (_SRC / rel).read_text("utf-8")


def test_SSE_confirm_을_받아_메시지에_카드를_단다():
    api = _read("api/chat.api.ts")
    assert "onConfirm?: (e: ConfirmCard) => void;" in api
    assert "    case 'confirm':\n      h.onConfirm?.(payload as ConfirmCard);\n      break;" in api, "모르는 이벤트는 조용히 버려진다 — 자리가 있어야 한다"
    ctx = _read("state/ChatContext.tsx")
    blk = ctx[ctx.index("onConfirm: (e) =>"):]
    blk = blk[:blk.index("},") + 2]
    assert "patch(cid, botId, (m) => ({ ...m, confirm: e }))" in blk and "Array.isArray(e.calls)" in blk


def test_카드_단추는_켜_둔_루틴을_싣지_않고_답할_수_없는_카드는_잠근다():
    """단추가 셋째 인자 없이 보내면 켜 둔 분석 루틴이 실린다 — 에이전트 chat() 은 루틴 가지를 카드 판정보다 먼저 보므로 카드가 승인되지 않고
    루틴이 단추 글을 덧붙인 말로 돈다(10-30 반대 검토). 동작은 브라우저 시험이 보고, 여기는 그 자리를 글자로 묶는다."""
    src = _read("components/chat/ConfirmCard.tsx")
    assert "onClick={() => sendMessage(card.approve_text, undefined, null)}" in src
    assert "onClick={() => sendMessage(card.decline_text, undefined, null)}" in src, "단추 글을 화면이 지어내면 서버의 답 판정(_confirm_reply)과 어긋난다"
    assert "const off = state !== 'open' || streaming || busy;" in src and src.count("disabled={off}") == 2
    lst = _read("components/chat/MessageList.tsx")
    assert "card={m.confirm ? confirmState(messages, i, now) : undefined}" in lst
    assert "lastIndexOf('user')" not in lst, "뒤에 사람 말이 있나만 보면 보내기 알림이 붙은 카드의 단추가 살아 있다"


def _states(cases: list[tuple[list[dict], int, int]]) -> list[str]:
    """(메시지들, 카드 자리, 지금) 마다 confirmState — node 한 번에."""
    return _node(["components/chat/confirm.ts"],
                 "const { confirmState } = require('./components/chat/confirm.js');"
                 " out(input.map(([ms, i, now]) => confirmState(ms, i, now)));", [list(c) for c in cases])


CID = "cf-7f3a9c2e41d0"
CARD = {"id": CID, "expires_at": 2_000, "approve_text": f"실행 — 확인 번호 {CID}", "decline_text": f"취소 — 확인 번호 {CID} 는 실행하지 않음",
        "calls": [{"tool": "run_job", "app": "StepForge", "kind": "job", "args_text": "kind=graph", "again": False}]}
CARD_TEXT = f"그래프 잡을 걸려 했습니다.\n\n---\n**확인이 필요합니다** — …\n(확인 번호 `{CID}` · 30분)"


@_need_node
def test_카드_상태는_서버의_답_판정과_같은_조건이다():
    """서버(_confirm_reply)는 이력의 **마지막 항목**이 그 카드 번호를 실은 어시스턴트 글일 때만 다음 말을 답으로 받는다(design-ha29 9절 31).
    오류가 난 답 · 빈 답은 이력에 실리지 않는다(history.buildHistory)."""
    q, bot = _msg("user", "그래프 다시 봐줘"), _msg("assistant", CARD_TEXT, confirm=CARD)
    notice = _msg("assistant", "Report Archive 에 보냈습니다 — 「점검 결과」", n=3)
    got = _states([([q, bot], 1, 1_000),
                   ([q, bot], 1, 3_000),
                   ([q, bot, _msg("user", "실행", n=2)], 1, 1_000),
                   ([q, bot, notice], 1, 1_000),                          # 보내기 알림이 이력 끝이면 서버는 단추 글을 카드의 답으로 받지 않는다
                   ([q, {**bot, "error": "stream_cut"}], 1, 1_000),     # 오류가 난 답은 이력에 실리지 않는다
                   ([q, {**bot, "text": "그래프 잡을 걸려"}], 1, 1_000),  # 본문에 카드 번호가 없으면 서버가 찾을 카드가 없다(받던 중 멈춤)
                   ([q, _msg("assistant", "네")], 1, 1_000)])
    assert got == ["open", "expired", "answered", "closed", "closed", "closed", "closed"], got


@_need_node
def test_카드는_브라우저_사본에_남고_꼴이_틀린_카드는_버린다():
    """새로고침 뒤에도 30분 안이면 단추가 산다 — 저장 → 되살리기 왕복(design-ha29 9절 32)."""
    conv = {"id": "c1", "title": "t", "createdAt": 1, "updatedAt": 2,
            "messages": [_msg("user", "그래프 다시 봐줘"), _msg("assistant", CARD_TEXT, confirm=CARD)]}
    bad = {"role": "assistant", "content": CARD_TEXT, "ts": 3, "confirm": {**CARD, "calls": "run_job"}}
    got = _node(["state/chatStore.ts"],
                "const S = require('./state/chatStore.js'); S.saveConversations([input.conv]);"
                " const back = S.loadConversations()[0].messages[1];"
                " const raw = JSON.parse(localStorage.getItem('hwax.chat.conversations'));"
                " raw[0].messages[1] = input.bad; localStorage.setItem('hwax.chat.conversations', JSON.stringify(raw));"
                " out({ back: back.confirm || null, bad: S.loadConversations()[0].messages[1].confirm || null });",
                {"conv": conv, "bad": bad})
    assert got["back"] == CARD, got
    assert got["bad"] is None, "calls 가 배열이 아닌 카드는 버린다(단추가 깨진 카드를 그리지 않게)"


@_need_node
def test_자기검증의_버린_고침과_관문_수는_사본에_남기지_않는다():
    """dropped · gate 는 QA 용이라 화면에 보이지 않는다 — 브라우저 사본에도 남기지 않는다(쿼터). 화면이 쥔 메시지는 고치지 않는다."""
    sc = {"status": "flagged", "fixes": ["a — 반영 안 함: x"], "flags": ["a — 반영 안 함: x"], "dropped": ["b — 버림: y"],
          "gate": {"applied": 0, "reviewer_flags": 1}, "reason": "짚기만 했다", "ms": 2100}
    conv = {"id": "c1", "title": "t", "createdAt": 1, "updatedAt": 2,
            "messages": [_msg("user", "토크?"), _msg("assistant", "12.5 N·m", meta={"models": {"q": 1}, "self_check": sc})]}
    got = _node(["state/chatStore.ts"],
                "const S = require('./state/chatStore.js'); S.saveConversations([input]);"
                " const raw = JSON.parse(localStorage.getItem('hwax.chat.conversations'));"
                " out({ stored: raw[0].messages[1].meta, live: input.messages[1].meta.self_check,"
                "       loaded: S.loadConversations()[0].messages[1].meta });", conv)
    assert got["stored"]["self_check"] == {k: sc[k] for k in ("status", "fixes", "flags", "reason", "ms")}, got["stored"]
    assert got["stored"]["models"] == {"q": 1}, "meta 의 다른 칸은 그대로"
    assert got["live"] == sc, "저장이 화면이 쥔 메시지의 칸을 지우면 안 된다"
    assert got["loaded"] == got["stored"]


def test_짚기만_한_답은_고친_답과_다르게_보인다():
    types = _read("types/chat.ts")
    assert "status: 'ok' | 'fixed' | 'flagged' | 'skipped' | 'suspect' | 'failed' | 'unreadable';" in types
    assert "  flags?: string[];" in types and "  dropped?: string[];" in types
    lst = _read("components/chat/MessageList.tsx")
    note = lst[lst.index("function CheckNote({ check }: { check: SelfCheck }) {"):]
    note = note[:note.index("\nfunction ", 10)]
    assert "if (check.status === 'flagged') {" in note
    assert "짚었습니다 — 답은 고치지 않았습니다" in note, "짚기만 한 답을 '고쳤습니다' 로 보이면 사람이 고친 답으로 읽는다"
    assert "dropped" not in note, "버린 고침은 QA 용 — 화면에 보이지 않는다"


# ── 두 리포 계약 — 에이전트서버가 내는 confirm 사건의 칸 = 화면의 ConfirmCard 형(design-ha29 9절 33) ─────────────────────────────────
def _ts_body(src: str, name: str) -> str:
    body = re.search(rf"^export interface {name} \{{\n(.*?)\n\}}", src, re.S | re.M)
    assert body, f"types/chat.ts 에서 {name} 를 못 찾았다"
    return body.group(1)


def _ts_fields(src: str, name: str) -> dict[str, bool]:
    """types/chat.ts 의 interface → {칸: 늘 있나(? 가 없나)}."""
    return {m.group(1): not m.group(2) for m in re.finditer(r"^  (\w+)(\?)?:", _ts_body(src, name), re.M)}


def _agent_confirm_event(src: str) -> ast.Dict:
    hits = [n for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_sse" and len(n.args) == 2
            and isinstance(n.args[0], ast.Constant) and n.args[0].value == "confirm" and isinstance(n.args[1], ast.Dict)]
    assert len(hits) == 1, f'에이전트서버 app.py 에서 _sse("confirm", {{…}}) 를 {len(hits)}개 찾았다 — 하나여야 한다'
    return hits[0].args[1]


def _dict_fields(d: ast.Dict) -> dict[str, bool]:
    """{칸: 늘 싣나} — `**({"app": …} if … else {})` 처럼 펼친 조건부 칸은 늘 싣지 않는다."""
    out: dict[str, bool] = {}
    for k, v in zip(d.keys, d.values):
        if isinstance(k, ast.Constant):
            out[k.value] = True
        else:
            for sub in ast.walk(v):
                if isinstance(sub, ast.Dict):
                    out.update({x.value: False for x in sub.keys if isinstance(x, ast.Constant)})
    return out


def test_에이전트서버의_confirm_사건_칸이_화면의_형과_같다():
    if not _AGENT.exists():
        pytest.skip(f"형제 리포 없음: {_AGENT}")
    src = _AGENT.read_text(encoding="utf-8")
    if "_confirm_" not in src:
        # 두 리포를 나란히 고치는 동안 — 에이전트 main 에 HA-29 가 들기 전 판이다(design-integration 6절 — 포털 화면 가지는 그 뒤에 합친다)
        pytest.skip("형제 에이전트서버가 확인 관문(HA-29) 전 판이다 — 그 판이 든 뒤 이 시험이 사건 칸을 맞댄다")
    ev = _agent_confirm_event(src)
    types = _read("types/chat.ts")
    sent = _dict_fields(ev)
    assert sent == _ts_fields(types, "ConfirmCard"), (sent, _ts_fields(types, "ConfirmCard"))
    calls = ev.values[[k.value for k in ev.keys].index("calls")]
    assert isinstance(calls, ast.ListComp) and isinstance(calls.elt, ast.Dict), "calls 는 호출마다 dict 하나인 목록이다"
    assert _dict_fields(calls.elt) == _ts_fields(types, "ConfirmCall"), (_dict_fields(calls.elt), _ts_fields(types, "ConfirmCall"))
    # expires_at 은 epoch 밀리초다 — 화면은 Date.now() 와 그대로 견준다(초로 오면 카드가 늘 지난 것으로 잠긴다)
    exp = ev.values[[k.value for k in ev.keys].index("expires_at")]
    assert "* 1000" in ast.unparse(exp), ast.unparse(exp)
    # 부류 이름 — 화면은 kind 로 '잡 · 쓰기 · 되돌리기 어려움' 을 적는다(ConfirmCard KIND). 에이전트서버의 부류 판정(_confirm_class)과 같은 셋이다
    kinds = set(re.findall(r"'(\w+)'", re.search(r"^  kind: (.+);$", _ts_body(types, "ConfirmCall"), re.M).group(1)))
    cls = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "_confirm_class")
    said = {t.elts[0].value for t in ast.walk(cls)
            if isinstance(t, ast.Tuple) and len(t.elts) == 2 and isinstance(t.elts[0], ast.Constant) and isinstance(t.elts[0].value, str)}
    assert kinds == said == {"job", "write", "confirm"}, (kinds, said)
