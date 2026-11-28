# 내 엔진 심의 잡 목록 · 결정문 전문(WD-08) — 그 사람의 PAT 로 deliberate_list · deliberate_result 를 부르고 쪽을 이어 원문 그대로 · 더 보기 시각
"""docs/request-1125 WD-08 의 포털 몫(GET /agent/engine-delib/jobs · /jobs/{job_id}/decision — app/agent/mcp_delib.py).

엔진(HWAXAgentServer b1007bf)의 deliberate_list 는 since · until · query 를 받고 limit 100 까지 · 쪽 번호가 없다. 결과 칸 고르기(7e744d9)는
deliberate_result(fields) 다. 고정하는 것.
  · 계약 — 포털이 싣는 인자(since · until · query · limit · fields)가 엔진 도구의 인자다.
  · 목록 — 거름은 엔진에 그대로(글은 빈칸을 하나로 · 200자) · 쪽을 이어 행이 모두 · 종류 · 제 잡(mine)은 받은 행에서 · 포털이 들인 대화 id · 더 보기는
    가장 옛 행의 잡 id 시각(엔진 박스 현지 시각 — 엔진 until 이 같은 시각으로 읽는다) · 틀린 날짜는 422.
  · 결정문 — 고른 칸만 받고 쪽을 이어 자르지 않는다 · 심의 권한이 있어야 한다.
"""
import ast
from pathlib import Path

import pytest

from app.agent import mcp_delib as M
from tests.test_job_card import env, ingested, login, paged  # noqa: F401  (env · paged 는 픽스처)
from tests.test_mcp_delib import OUT, OWNER

_AGENT = Path(__file__).resolve().parents[3] / "HWAXAgentServer"


def test_포털이_싣는_인자는_엔진_도구의_인자다():
    p = _AGENT / "mcp_server.py"
    if not p.exists():
        pytest.skip(f"형제 리포 없음: {p}")
    tree = ast.parse(p.read_text(encoding="utf-8"))
    args = {n.name: {a.arg for a in n.args.args + n.args.kwonlyargs} for n in tree.body if isinstance(n, ast.AsyncFunctionDef)}
    assert {"limit", "since", "until", "query", "part"} <= args["deliberate_list"]
    assert {"job_id", "fields", "part"} <= args["deliberate_result"]
    assert {"job_id", "brief", "part"} <= args["deliberate_status"]


def test_목록은_쪽을_잇고_종류_제_잡으로_거르고_더_보기_시각을_준다(env, paged):
    cid, jid = ingested(env)
    h = login(env.c, OWNER)
    rows = [{"job_id": f"{'diagnosis' if i % 2 else 'default'}-202611{10 + i:02d}-120000-abc{i:03d}", "job": "diagnosis" if i % 2 else "default",
             "label": "x", "status": "done", "question": "긴 화두 " * 200, "mine": i != 5, "owner": OWNER if i != 5 else "peer@example.com",
             "report_id": i or None} for i in range(9, 0, -1)]
    rows.append({"job_id": jid, "job": "diagnosis", "status": "done", "question": "힌지", "mine": True, "owner": OWNER})
    full = {"jobs": rows, "running": 0, "queued": 0, "running_max": 3, "running_max_per_user": 1, "queue_max": 10, "truncated": True,
            "filter": {"since": "2026-11-01"}, "window": {"max": 5000, "complete": True, "note": "n"}}
    ids = ("running", "queued", "running_max", "running_max_per_user", "queue_max", "filter", "window")
    env.replies["deliberate_list"] = lambda a: paged.paged(full, part=int(a.get("part") or 1), again={"limit": a["limit"]}, ids=ids)
    r = env.c.get("/agent/engine-delib/jobs", params={"since": "2026-11-01", "query": "  힌지   크랙 ", "limit": 10}, headers=h)
    assert r.status_code == 200, r.text
    lists = [c for c in env.calls if c[0] == "deliberate_list"]
    assert lists[0][1] == {"limit": 10, "since": "2026-11-01", "query": "힌지 크랙"} and len(lists) > 1, "거름은 그대로 · 쪽을 넘겨 받는다"
    got = r.json()
    assert [x["job_id"] for x in got["jobs"]] == [x["job_id"] for x in rows if x["mine"]], "기본은 제 잡만"
    assert got["jobs"][0]["question_chars"] == len(rows[0]["question"]) and len(got["jobs"][0]["question"]) == 400
    assert got["jobs"][-1]["conversation_id"] == cid and got["jobs"][0]["conversation_id"] is None
    assert got["more"] is True and got["next_until"] == "2026-11-28T04:00:00", "가장 옛 행(거르기 전)의 시작 시각"
    assert got["jobs"][0]["created"] == "2026-11-19T12:00:00"
    allr = env.c.get("/agent/engine-delib/jobs", params={"scope": "all"}, headers=h).json()
    assert len(allr["jobs"]) == len(rows) and any(x["owner"] == "peer@example.com" for x in allr["jobs"])
    only = env.c.get("/agent/engine-delib/jobs", params={"job": "default"}, headers=h).json()
    assert {x["job"] for x in only["jobs"]} == {"default"}
    assert env.c.get("/agent/engine-delib/jobs", params={"since": "11월"}, headers=h).status_code == 422


def test_결정문_전문은_고른_칸만_받아_쪽을_잇는다(env, paged):
    _cid, jid = ingested(env)
    h = login(env.c, OWNER)
    dec = "".join(f"{i:04d} 결정문 문단 — 근거\n" for i in range(2000))
    full = {"job_id": jid, "status": "done", "decision": dec, "question": "힌지", "fields_all": ["decision"], "fields_unknown": []}
    env.replies["deliberate_result"] = lambda a: paged.paged(full, part=int(a.get("part") or 1), again={"job_id": jid, "fields": a["fields"]},
                                                             ids=("job_id", "status"))
    r = env.c.get(f"/agent/engine-delib/jobs/{jid}/decision", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["decision"] == dec, "자르지 않는다"
    assert env.calls[0][1]["fields"] == M._DECISION_FIELDS and r.json()["conversation_id"]


def test_목록과_결정문은_심의_권한이_있어야_한다(env):
    login(env.c, OUT)
    assert env.c.get("/agent/engine-delib/jobs").status_code == 403
    assert env.c.get("/agent/engine-delib/jobs/diagnosis-20261128-040000-abc123/decision").status_code == 403


def test_이_대화에_싣기는_결정문_원문을_사람이_가져온_근거로_싣는다():
    from tests.test_front_window_payload import _node
    dec = "## 결론\n리브를 1.2 mm 로 보강한다 [e:1]\n" * 50
    got = _node(["components/chat/uploadNotice.ts", "components/chat/history.ts"],
                "const u = require('./components/chat/uploadNotice.js'); const h = require('./components/chat/history.js');"
                " const n = u.decisionNotice(input, 5); const m = { id: 'a', role: 'assistant', text: n.text, activity: n.activity };"
                " out({ n, ev: h.turnEvidence(m) });",
                {"job_id": "diagnosis-20261128-040000-abc123", "label": "원인 규명", "question": "힌지 크랙 원인", "decision": dec})
    (a,) = got["n"]["activity"]
    assert a["origin"] == "upload" and a["tool"] == "deliberate_result" and a["result_full"] == dec
    assert "diagnosis-20261128-040000-abc123" in got["n"]["text"] and got["n"]["title"].startswith("심의 결정문")
    (ev,) = got["ev"]
    assert ev["kind"] == "upload" and ev["result"] == dec.strip() and ev["args"] == '{"job_id":"diagnosis-20261128-040000-abc123"}'
