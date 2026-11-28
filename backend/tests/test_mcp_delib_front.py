# MCP 심의 대화의 화면 되살리기 — 포털이 들인 엔진 잡(WD-03)과 게이트웨이 save_conversation 의 도구 활동(WD-04)을 서버 사본에서 그대로 되살린다
"""docs/request-1125 WD-03 · WD-04 의 화면 몫(frontend api/conversations.api.ts serverMessagesToLocal · serverConvToLocal · components/chat/history.ts).

서버 사본은 진짜 꼴로 만든다 — 엔진 잡은 엔진 _conv_item(AST) → 포털 messages_of → 대화 저장소에 쓰고 읽은 그대로, 활동은 게이트웨이 _conv_activity(AST)가
meta.activity 에 싣는 그대로다. 프론트에 단위 시험 러너가 없어 TypeScript 를 옮겨 적어 node 로 부른다(test_subject_front 와 같은 길).

  · 들인 엔진 잡 — 대화의 출처 mcp · 결정문 칸의 mcpJob(잡 id · 뿌리 · 상태 · 앞 잡) · 결과 카드 · 주제 · 근거 표지. 결정문 없이 끝난 잡은 결정문이 없다.
  · 활동 — 좌석 발언과 결정문의 meta.activity 를 결정문 칸의 activity 로 모은다. 다음 턴 이력의 근거(buildHistory evidence)가 원문 결과를 싣는다 —
    'MCP 로 저장한 대화를 웹에서 열고 원 도구 결과가 있니? 라고 물으면 원문 그대로 인용' 의 화면 쪽 절반.
"""
import ast
import json
import shutil
from pathlib import Path

import pytest

from app.agent import mcp_delib as M
from app.agent.conv_store import ConversationStore
from app.config import Settings
from tests.test_front_window_payload import _node as _fe_node
from tests.test_mcp_delib import _engine_conv, _job

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
GATEWAY = ROOT.parent / "HWAXMcpGateway" / "gateway.py"
_CONV = ["api/conversations.api.ts", "state/chatStore.ts", "components/chat/history.ts"]

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 함수를 돌려 볼 수 없다",
)


def _gateway_activity():
    """게이트웨이 gateway.py 의 _conv_activity 와 그 상수만 떼어 실행한다(게이트웨이 모듈 전체를 읽지 않는다)."""
    if not GATEWAY.exists():
        pytest.skip(f"형제 리포 없음: {GATEWAY}")
    tree = ast.parse(GATEWAY.read_text(encoding="utf-8"))
    names = {"CONV_ACTIVITY_MAX", "CONV_ACTIVITY_CHARS", "CONV_ACTIVITY_PREVIEW", "CONV_ACTIVITY_DETAIL"}
    consts = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") in names for t in n.targets)]
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_conv_activity"]
    assert len(consts) == 4 and fn, "게이트웨이에서 _conv_activity 와 상수를 찾지 못했다"
    ns: dict = {"json": json}
    exec(compile(ast.Module(body=consts + fn, type_ignores=[]), "gateway_conv_activity", "exec"), ns)  # noqa: S102 — 형제 리포의 코드
    return ns["_conv_activity"]


def _stored(tmp_path, items: list[dict]) -> dict:
    """포털이 들인 대로 대화 저장소에 쓰고 읽은 서버 대화 하나."""
    store = ConversationStore(Settings(_env_file=None, conv_store_path=str(tmp_path / "conv.sqlite")))
    for it in items:
        store.ingest_mcp_delib(owner_sub="me@example.com", job_id=it["job_id"], root_job_id=it["root_job_id"], title=M._title(it["question"]),
                               messages=M.messages_of(it), finished_at=it["finished_at"])
    (conv,) = store.list_for_owner("me@example.com")
    return store.get(conv["id"], "me@example.com")


def test_들인_엔진_잡은_출처_mcp_와_잡_열쇠로_되살아난다(tmp_path):
    conv_item, ledger = _engine_conv()
    root = _job("diagnosis-20261128-040000-abc123", report_id=7, report_url="/w/a/reports/7",
                subject={"sp_task": "알파", "sp_state": "confirmed", "round": "dv1", "text": "알파 1차", "artifacts": []})
    ledger[root["id"]] = root
    cut = _job("diagnosis-20261128-050000-def456", continues=root["id"], status="interrupted", decision=None, fin=1_700_000_500.0)
    server = _stored(tmp_path, [conv_item(root), conv_item(cut)])
    script = ("const c = require('./api/conversations.api.js'); const v = c.serverConvToLocal(input);"
              " out({ source: v.source ?? null, delib: v.messages.filter((m) => m.delib).map((m) => ({ job: m.delib.mcpJob ?? null,"
              " decision: m.delib.decision ?? null, outcome: m.delib.outcome ?? null, subject: m.delib.subject ?? null,"
              " ev: (m.delib.evidence ?? []).length, turns: m.delib.turns.length })) });")
    got = _fe_node(_CONV, script, server)
    assert got["source"] == "mcp"
    first, second = got["delib"]
    assert first["job"] == {"jobId": root["id"], "rootJobId": root["id"], "job": "diagnosis", "chairTemplate": "diagnosis", "status": "done"}
    assert first["decision"] == "결론 — 리브 보강" and first["outcome"]["report_id"] == 7 and first["outcome"]["url"] == "/w/a/reports/7"
    assert first["subject"]["sp_task"] == "알파" and first["ev"] == 1 and first["turns"] == 2
    assert second["job"]["status"] == "interrupted" and second["job"]["continues"] == root["id"]
    assert second["decision"] is None, "결정문 없이 끝난 잡의 끝 줄(상태 글)은 결정문이 아니다"


def test_save_conversation_의_도구_활동이_결정문_칸에_모여_다음_턴_근거가_된다():
    act = _gateway_activity()
    seat, _ = act([{"tool": "stepforge_part_stack", "args": {"part": "P1"}, "result": "적층 원문 " * 80 + "끝", "ok": True}], 1, 1_700_000_000_000)
    chair, _ = act([{"tool": "aidatahub_search", "args": "{\"q\":\"힌지\"}", "result": "카드 원문 " * 60}], 2, 1_700_000_000_000)
    server = {"id": "c1", "title": "t", "kind": "deliberation", "source": "mcp", "created_at": 1, "updated_at": 2, "messages": [
        {"role": "user", "content": "힌지 크랙 원인", "persona": None, "round": None, "meta": None, "ts": 1},
        {"role": "persona", "content": "발언", "persona": "mech-a", "round": 1, "meta": {"activity": seat}, "ts": 2},
        {"role": "assistant", "content": "결정문", "persona": None, "round": None, "meta": {"activity": chair}, "ts": 3},
        {"role": "user", "content": "원 도구 결과가 있니?", "persona": None, "round": None, "meta": None, "ts": 4}]}
    script = ("const c = require('./api/conversations.api.js'); const h = require('./components/chat/history.js');"
              " const v = c.serverConvToLocal(input); const d = v.messages.find((m) => m.delib);"
              " out({ tools: (d.activity ?? []).map((a) => a.tool), history: h.buildHistory(v.messages.slice(0, -1), { evidence: true }) });")
    got = _fe_node(_CONV, script, server)
    assert got["tools"] == ["stepforge_part_stack", "aidatahub_search"], "좌석 발언과 결정문의 활동을 결정문 칸에 모은다"
    (ev_turn,) = [x for x in got["history"] if x.get("evidence")]
    assert [e["tool"] for e in ev_turn["evidence"]] == ["stepforge_part_stack", "aidatahub_search"]
    assert ev_turn["evidence"][0]["result"] == "적층 원문 " * 80 + "끝", "미리보기(220자)가 아니라 원문 그대로"
    assert ev_turn["evidence"][0]["args"] == '{"part":"P1"}'
