# MCP 로 연 심의 ↔ 포털 대화(WD-03) — 엔진의 진짜 꼴로 본다
"""docs/request-1125 WD-03 의 포털 몫(app/agent/mcp_delib.py).

고정하는 것.
  · 계약 — 엔진 delib_jobs.CONV_CONTRACT · 창구 GET /delib/conversations(since · limit)가 포털이 부르는 것과 같다. 대화 거리 항목은 엔진의
    _conv_item · conv_root 를 AST 로 떼어 만든다.
  · 당기기 — 공유 비밀만 싣는다 · 포털 계정만 · 주인 키는 그 이메일로 낸 사람 PAT 의 sub(없으면 이메일) · 같은 뿌리 잡은 한 대화 · job_id 로 한 번 ·
    제자리 이어하기로 더 늦게 끝난 판은 그 잡의 줄만 바꾼다 · 지운 대화를 되살리지 않는다 · 대화 시각은 잡이 끝난 때 · 결정문 없는 잡은 표지 · 실패는 까닭.
"""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import mcp_delib as M
from app.agent.conv_store import ConversationStore
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
PW = "pw123456"
OWNER, OUT = "me@example.com", "stranger@example.com"


def _src(name: str) -> str:
    p = _AGENT / name
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    return p.read_text(encoding="utf-8")


# ── 엔진의 진짜 꼴 ───────────────────────────────────────────────────────────────────────────────────────
def _engine_conv():
    """엔진 delib_jobs 의 _conv_item · conv_root 만 떼어 실행한다(엔진 모듈 전체를 읽지 않는다). get 은 시험의 원장이다."""
    tree = ast.parse(_src("delib_jobs.py"))
    want = {"_conv_item", "conv_root"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
    consts = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CONV_ROOT_HOPS" for t in n.targets)]
    assert {n.name for n in nodes} == want and consts, "엔진 delib_jobs 에서 _conv_item · conv_root · CONV_ROOT_HOPS 를 찾지 못했다"
    ledger: dict = {}
    ns: dict = {"get": lambda jid: ledger.get(jid)}
    exec(compile(ast.Module(body=consts + nodes, type_ignores=[]), "delib_jobs_conv", "exec"), ns)  # noqa: S102 — 형제 리포의 코드
    return ns["_conv_item"], ledger


def _job(jid: str, *, user=OWNER, q="힌지 크랙 원인", turns=2, decision="결론 — 리브 보강", fin=1_700_000_000.0, **kw) -> dict:
    return {"id": jid, "user": user, "owner_aff": "CAEG", "question": q, "status": kw.pop("status", "done"), "job": "diagnosis",
            "chair_template": "diagnosis", "started_at": fin - 100, "finished_at": fin, "started_by": "user",
            "turns": [{"persona": f"seat{i}", "round": 1 + i // 2, "say": f"짧은 {i}", "say_full": f"발언 전문 {i}"} for i in range(turns)],
            "decision": decision, "opts": {"evidence": [{"source": "StepForge", "tool": "part_stack", "key": "P1", "result": "x" * 1200}]},
            "evidence_refs": [], "subject": None, "report_id": kw.pop("report_id", None), "report_url": kw.pop("report_url", ""), **kw}


def test_계약은_엔진과_같다():
    jobs, appsrc = _src("delib_jobs.py"), _src("app.py")
    assert f'CONV_CONTRACT = "{M.CONTRACT}"' in jobs
    assert '@app.get("/delib/conversations")\ndef delib_conversations(request: Request, since: float = 0.0, limit: int = 20):' in appsrc
    engine_max = int(next(ln.split("=")[1] for ln in jobs.splitlines() if ln.startswith("CONV_LIMIT_MAX")))
    assert engine_max >= M.PAGE_LIMIT


def test_엔진_항목이_대화_메시지가_된다():
    conv_item, ledger = _engine_conv()
    root = _job("diagnosis-20261128-040000-abc123", report_id=7, report_url="/w/a/reports/7",
                subject={"sp_task": "알파", "sp_state": "confirmed", "round": "dv1", "text": "알파 1차", "artifacts": []})
    ledger[root["id"]] = root
    nxt = _job("diagnosis-20261128-050000-def456", continues=root["id"], fin=1_700_000_500.0)
    item = conv_item(nxt)
    assert item["root_job_id"] == root["id"], "이어하기 잡의 뿌리는 앞 잡이다"
    msgs = M.messages_of(conv_item(root))
    assert [m["role"] for m in msgs] == ["user", "persona", "persona", "assistant"]
    assert msgs[1]["persona"] == "seat0" and msgs[1]["round"] == 1 and msgs[1]["content"] == "발언 전문 0", "줄이지 않은 발언(say_full)"
    d = msgs[-1]["meta"]
    assert d["mcp_delib"]["job_id"] == root["id"] and d["mcp_delib"]["root_job_id"] == root["id"] and d["mcp_delib"]["status"] == "done"
    assert d["delib_outcome"] == {"report_id": 7, "url": "/w/a/reports/7", "title": ""}
    assert d["subject"]["sp_task"] == "알파" and d["subject"]["sp_state"] == "confirmed"
    assert d["delib_evidence"][0]["included"] is True and "1,200자" in d["delib_evidence"][0]["text"], "근거는 본문 없이 표지만"
    # 결정문 없이 끝난 잡 — 끝 줄의 표지
    cut = M.messages_of(conv_item(_job("diagnosis-20261128-060000-aaaaaa", status="error", decision=None)))
    assert cut[-1]["meta"]["delib_undecided"] is True and "결정문 없이" in cut[-1]["content"]


# ── 당기기 ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def box(tmp_path):
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"), token_store_path=str(tmp_path / "tok.sqlite"),
                 conv_store_path=str(tmp_path / "conv.sqlite"), gateway_shared_token="sekret", agent_server_url="http://agent.invalid",
                 delib_conv_sync_s=0)
    users, tokens = UserStore(s), TokenStore(s)
    users.signup(email=OWNER, name="me", password=PW, bootstrap_admins=[])
    users.approve(OWNER, by="boss@example.com", groups=[])
    tokens.record_pat(jti="j1", sub="sub-me-77", email=OWNER, name="claude", aud=["mcp-gateway"], scopes=["api"], created=10, exp=99)
    a = SimpleNamespace(state=SimpleNamespace(conv_store=ConversationStore(s), user_store=users, token_store=tokens))
    return a, s


class _Engine:
    """엔진 GET /delib/conversations 대역 — since 이상인 항목을 finished_at 오름차순으로(엔진 conversation_items 와 같은 셈)."""

    def __init__(self, items: list, *, status=200, contract=M.CONTRACT):
        self.items, self.status, self.contract, self.seen = items, status, contract, []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.seen.append(req)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "x"})
        since, lim = float(req.url.params["since"]), int(req.url.params["limit"])
        got = sorted((i for i in self.items if i["finished_at"] >= since), key=lambda i: i["finished_at"])
        page = got[:lim]
        return httpx.Response(200, json={"contract": self.contract, "items": page,
                                         "next_since": max((i["finished_at"] for i in page), default=since), "complete": len(got) <= lim})


def _tick(a, s, eng) -> dict:
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(eng)) as cli:
            return await M.tick(a, s, client=cli)
    return asyncio.run(go())


def test_당기기는_공유_비밀만_싣고_주인_대화에_뿌리별로_한_번_쓴다(box):
    a, s = box
    conv_item, ledger = _engine_conv()
    root = _job("diagnosis-20261128-040000-abc123")
    ledger[root["id"]] = root
    nxt = _job("diagnosis-20261128-050000-def456", continues=root["id"], q="힌지 크랙 원인 — 이어서", fin=1_700_000_500.0)
    stranger = _job("default-20261128-040500-bbbbbb", user=OUT, fin=1_700_000_100.0)
    items = [conv_item(root), conv_item(stranger), conv_item(nxt), {"job_id": "x y", "rows": [], "finished_at": 1_700_000_200.0}]
    for it in items[:3]:
        it["user"] = it["user"].replace("@", "%40") if it["job_id"].startswith("diag") else it["user"]   # 게이트웨이가 %-인코딩해 실은 값도
    eng = _Engine(items)
    out = _tick(a, s, eng)
    assert out.get("error") is None, out
    assert (out["new"], out["appended"], out["no_account"], out["bad"]) == (1, 1, 1, 1), out
    (req,) = eng.seen
    assert req.headers["authorization"] == "Bearer sekret" and "x-hwax-user" not in req.headers, "사람 신원 머리를 실으면 엔진이 403"
    store = a.state.conv_store
    assert store.list_for_owner(OWNER) == [], "주인 키는 이메일이 아니라 그 사람 PAT 의 sub 다"
    (conv,) = store.list_for_owner("sub-me-77")
    assert (conv["kind"], conv["source"], conv["title"]) == ("deliberation", "mcp", "힌지 크랙 원인")
    assert conv["created_at"] == int(root["finished_at"]) and conv["updated_at"] == int(nxt["finished_at"]), "대화 시각은 잡이 끝난 때"
    msgs = store.get(conv["id"], "sub-me-77")["messages"]
    assert [m["role"] for m in msgs] == ["user", "persona", "persona", "assistant"] * 2
    assert msgs[3]["meta"]["mcp_delib"]["job_id"] == root["id"] and msgs[7]["meta"]["mcp_delib"]["continues"] == root["id"]
    assert store.mcp_delib_jobs_in(conv["id"], "sub-me-77") == [root["id"], nxt["id"]]
    # 경계의 잡이 다시 나와도 하나다 — 커서는 앞으로만
    assert out["since"] == nxt["finished_at"]
    again = _tick(a, s, eng)
    assert again["already"] >= 1 and again["new"] == again["appended"] == 0, again
    assert len(store.get(conv["id"], "sub-me-77")["messages"]) == 8


def test_제자리_이어하기로_늦게_끝난_판은_그_잡의_줄만_바꾸고_지운_대화는_되살리지_않는다(box):
    a, s = box
    conv_item, ledger = _engine_conv()
    cut = _job("diagnosis-20261128-040000-abc123", status="interrupted", decision=None, turns=1)
    ledger[cut["id"]] = cut
    _tick(a, s, _Engine([conv_item(cut)]))
    store = a.state.conv_store
    (conv,) = store.list_for_owner("sub-me-77")
    first = store.get(conv["id"], "sub-me-77")["messages"]
    assert first[-1]["meta"]["delib_undecided"] is True
    done = {**cut, "status": "done", "decision": "결론 — 끝까지", "turns": cut["turns"] * 3, "finished_at": cut["finished_at"] + 900}
    out = _tick(a, s, _Engine([conv_item(done)]))
    assert out["replaced"] == 1, out
    msgs = store.get(conv["id"], "sub-me-77")["messages"]
    assert msgs[-1]["content"] == "결론 — 끝까지" and sum(m["role"] == "user" for m in msgs) == 1, "그 잡의 옛 줄은 걷혔다"
    # 지운 대화 — 더 늦은 판이 와도 되살리지 않는다. 그 뿌리의 이어하기는 새 대화로 선다
    assert store.delete(conv["id"], "sub-me-77")
    later = {**done, "finished_at": done["finished_at"] + 60}
    out = _tick(a, s, _Engine([conv_item(later)]))
    assert out["deleted"] == 1 and store.list_for_owner("sub-me-77") == [], out
    nxt = _job("diagnosis-20261128-070000-cccccc", continues=cut["id"], fin=later["finished_at"] + 60)
    _tick(a, s, _Engine([conv_item(nxt)]))
    assert len(store.list_for_owner("sub-me-77")) == 1


def test_PAT_원장에_없으면_이메일이_주인_키다(box):
    a, s = box
    a.state.token_store = None
    conv_item, ledger = _engine_conv()
    j = _job("diagnosis-20261128-040000-abc123")
    ledger[j["id"]] = j
    _tick(a, s, _Engine([conv_item(j)]))
    assert len(a.state.conv_store.list_for_owner(OWNER)) == 1


@pytest.mark.parametrize(("eng", "word"), [
    (_Engine([], status=404), "WD-03"), (_Engine([], status=401), "공유 비밀"), (_Engine([], contract="delib-conversations/0"), "계약"),
])
def test_당기기_실패는_까닭을_말하고_커서를_옮기지_않는다(box, eng, word):
    a, s = box
    out = _tick(a, s, eng)
    assert word in out["error"] and out["since"] == 0.0, out


def test_비밀이_없으면_부르지_않는다(box):
    a, s = box
    eng = _Engine([])
    out = _tick(a, s.model_copy(update={"gateway_shared_token": ""}), eng)
    assert "GATEWAY_SHARED_TOKEN" in out["error"] and eng.seen == []
