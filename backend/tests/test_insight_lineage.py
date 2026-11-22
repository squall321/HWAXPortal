# 과제 인사이트의 읽을 때 셈(M4) — 설계 판의 뒤 판 · 뒤 판의 리스크 변경 심사 · 과제 key 의 이력 · 같은 결론 묶기 · 검토 줄(docs/project-insight-graph PLAN §8)
"""고정하는 것.
  · 낡음은 읽을 때 셈하고 저장하지 않는다. 기구 CAD(StepForge)의 개정 줄에 뒤 판이 있거나 내용 지문이 바뀌었으면 '낡았을 수 있다', 못 읽으면 '모름'
    (낡았다고도 그대로라고도 하지 않는다). 회로 보드 · 해석 리포트는 셈하지 않는다.
  · 뒤 판의 리스크 변경 심사(diff:)는 읽는 사람의 리스크 앱 시야로만, 그 비교의 앞 판은 확인하지 않았다고 적어 보인다.
  · 옛 key(이름 바뀜 · 합쳐짐)로 남은 카드는 지금 과제에 모으되, 옛 key 가 지금 다른 산 과제의 key 면 모으지 않는다. 못 읽으면 모으지 않는다.
  · 같은 결론은 묶어 보일 뿐 합치지 않고, 읽는 사람이 볼 수 있는 같은 칸의 카드만 센다.
  · 검토 줄은 그 사람이 손댈 카드와 까닭이다 — 남의 것은 관리자의 반박 카드뿐이고 감사에 남는다.
StepForge 의 가짜는 그 리포의 도구를 돌려 받은 실제 응답이다(tests/fixtures/insights/stepforge.json). 계정은 example.com 시험 신원만 쓴다."""
import asyncio
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import upload as U
from app.auth.errors import AuthError
from app.insights import cards as C
from app.insights import lineage as L

from test_insights import CARD, CLAIMED, CONFIRMED, KEY, _login, _relay, env  # noqa: F401 — env 는 픽스처다

_ROOT = Path(__file__).resolve().parents[2]
_STEPFORGE = _ROOT.parent / "StepForge"
_RISK = _ROOT.parent / "HWAXRisk"
_FIX = Path(__file__).resolve().parent / "fixtures" / "insights"
SF = json.loads((_FIX / "stepforge.json").read_text(encoding="utf-8"))
RK = json.loads((_FIX / "risk.json").read_text(encoding="utf-8"))
OLD, NEW, LOOSE = SF["ids"]["old"], SF["ids"]["latest"], SF["ids"]["undecided"]
FP = {OLD: SF["meta_old_with_next"]["revision"]["content_fp"], NEW: SF["meta_latest"]["revision"]["content_fp"],
      LOOSE: SF["meta_undecided"]["revision"]["content_fp"]}
OLD_KEY, NEW_KEY = "알파 개발_C1", "알파 개발_C2"
assert NEW_KEY == KEY, "시험 자료의 지금 key 가 다른 시험의 과제 key 와 같아야 한다"


def _meta(args):
    for k in ("meta_old_with_next", "meta_latest", "meta_undecided"):
        if SF[k]["id"] == args["project_id"]:
            return {"id": SF[k]["id"], "revision": SF[k]["revision"]}
    raise AuthError(f"{L.STEPFORGE_META}: 프로젝트를 찾을 수 없다", status_code=502)


def _gateway(table: dict, log: list | None = None):
    async def call(tool: str, args: dict) -> dict:
        if log is not None:
            log.append((tool, args))
        if tool not in table:
            raise AuthError(f"{tool}: unknown tool: {tool}", status_code=502)
        return table[tool](args)
    return call


def _subject(*arts):
    return {"sp_task": KEY, "round": "dv1", "artifacts": [dict(zip(("kind", "id", "rev"), a, strict=False)) for a in arts]}


# ── 형제 리포의 도구가 이 꼴을 낸다 ───────────────────────────────────────────────────────────────────────────
def test_부르는_도구와_읽는_칸이_형제_리포에_있다():
    sf = _STEPFORGE / "app" / "mcp_server.py"
    if sf.exists():
        src = sf.read_text(encoding="utf-8")
        assert L.STEPFORGE_META == "heaxstep_forge_get_project_meta" and re.search(r"^async def get_project_meta\(project_id: str\)", src, re.M)
        assert L.STEPFORGE_OBJECT == "heaxstep_forge_onto_object" and re.search(r"^async def onto_object\(focus: str, .*history: bool = True", src, re.M)
        assert '"next": [{"project_id": k["project_id"]' in src and '"content_fp": row["content_fp"]' in src
        graph = (_STEPFORGE / "core" / "onto_graph.py").read_text(encoding="utf-8")
        assert 'card["keys"] = {"previous_keys": prev, "merged_from": losers' in graph
        assert re.search(rf'^TASK_TYPE, MODEL_TYPE, PROJECT_TYPE = "{L.TASK_TYPE}"', (_STEPFORGE / "core" / "sp_core.py").read_text(encoding="utf-8"), re.M)
    rk = _RISK / "backend" / "app"
    if rk.exists():
        mcp = (rk / "mcp_server.py").read_text(encoding="utf-8")
        assert L.RISK_FIND.endswith("_risk_find_projects_by_subject") and L.RISK_DIFF.endswith("_risk_get_diff")
        assert re.search(r"^def risk_get_diff\(diff_id: ", mcp, re.M) and "def risk_find_projects_by_subject(" in mcp
        routes = (rk / "routes.py").read_text(encoding="utf-8")
        assert '"SELECT target_key, kind, level, verdict_candidate, verdict_final, created_at FROM rr_targets"' in routes
        assert '"targets": targets' in routes, "찾기 도구의 과제 줄에 대상(target_key · kind)이 실린다"
        brief = (rk / "brief.py").read_text(encoding="utf-8")
        assert '"by_kind": counts["by_kind"]' in brief and '"lines": "\\n".join(page)' in brief and '"truncated": start + len(page) < len(matched)' in brief
    if not sf.exists() and not rk.exists():
        pytest.skip("형제 리포 없음")


# ── 기구 CAD 의 개정 줄(단위) ─────────────────────────────────────────────────────────────────────────────────
def test_개정_정보는_뒤_판과_내용_지문을_읽는다():
    old = L.revision_of(_meta({"project_id": OLD}))
    assert old["state"] == "ok" and old["decided"] is True and old["content_changed"] is False and old["rev_label"] == "A1"
    assert old["next"] == [{"project_id": NEW, "rev_label": "A2"}] and old["content_fp"] == FP[OLD]
    new = L.revision_of(_meta({"project_id": NEW}))
    assert new["next"] == [] and new["decided"] is True
    loose = L.revision_of(_meta({"project_id": LOOSE}))
    assert loose["decided"] is False and loose["next"] == [] and loose["content_fp"] == FP[LOOSE] and loose["content_changed"] is None
    assert L.revision_of({"id": "x"})["state"] == "unknown" and L.revision_of(None)["state"] == "unknown"


def _revs(*ids, **over):
    out = asyncio.run(L.mcad_revisions(_gateway({L.STEPFORGE_META: _meta}), list(ids)))
    for k, v in over.items():
        out[k] = {**out[k], **v}
    return out


def test_뒤_판이_있거나_내용이_바뀌었으면_낡았을_수_있다고_하고_못_읽으면_모른다고_한다():
    revs = _revs(OLD, NEW, LOOSE)
    s = L.card_stale(_subject(("mcad", OLD, FP[OLD])), revs)
    assert s["state"] == "stale" and s["items"][0]["reasons"] == ["newer"] and "뒤 판이 있다" in s["say"] and "A2" in s["say"]
    assert L.next_ids(s) == [NEW]
    assert L.card_stale(_subject(("mcad", NEW, FP[NEW])), revs)["state"] == "current"
    s = L.card_stale(_subject(("mcad", NEW, "0" * 16)), revs)
    assert s["state"] == "stale" and s["items"][0]["reasons"] == ["fp_changed"] and s["items"][0]["now_rev"] == FP[NEW]
    assert L.card_stale(_subject(("mcad", NEW, "C2")), revs)["state"] == "current", "사람이 적은 판 표지는 지문과 견주지 않는다"
    assert L.card_stale(_subject(("mcad", NEW)), revs)["state"] == "current", "그때의 판 표지가 없으면 뒤 판만 본다"
    drift = L.card_stale(_subject(("mcad", NEW, FP[NEW])), {NEW: {**revs[NEW], "content_changed": True}})
    assert drift["state"] == "stale" and drift["items"][0]["reasons"] == ["content_changed"]
    s = L.card_stale(_subject(("mcad", "f" * 23, "aa11")), _revs("f" * 23))
    assert s["state"] == "unknown" and "모른다" in s["say"] and s["items"][0]["why"]
    both = L.card_stale(_subject(("mcad", "f" * 23), ("mcad", OLD, FP[OLD])), _revs("f" * 23, OLD))
    assert both["state"] == "stale", "하나라도 낡았으면 낡았을 수 있다"
    mixed = L.card_stale(_subject(("mcad", "f" * 23), ("mcad", NEW, FP[NEW])), _revs("f" * 23, NEW))
    assert mixed["state"] == "unknown", "못 읽은 것이 있으면 그대로라고 하지 않는다"


def test_회로_보드와_해석_리포트는_셈하지_않고_설계_자료가_없으면_표지가_없다():
    s = L.card_stale(_subject(("ecad", "abcdef0123456789", "B"), ("cae", "01HZX")), {})
    assert s["state"] == "not_checked" and [i["state"] for i in s["items"]] == ["not_checked", "not_checked"]
    assert "ODB 허브" in s["items"][0]["why"]
    assert L.card_stale(_subject(), {}) is None and L.card_stale({}, {}) is None
    with_board = L.card_stale(_subject(("ecad", "abcdef0123456789", "B"), ("mcad", OLD, FP[OLD])), _revs(OLD))
    assert with_board["state"] == "stale"


def test_개정_줄은_같은_과제를_한_번만_묻고_상한을_넘는_것은_모른다고_한다():
    log: list = []
    ids = [f"{i:023x}" for i in range(L.PROJECTS_MAX + 2)]
    out = asyncio.run(L.mcad_revisions(_gateway({L.STEPFORGE_META: lambda a: {"revision": {"decided": False, "content_fp": "ab" * 8}}}, log),
                                       [*ids, ids[0], "", None]))
    assert len(log) == L.PROJECTS_MAX and len(out) == L.PROJECTS_MAX + 2
    assert out[ids[0]]["state"] == "ok" and out[ids[-1]]["state"] == "unknown" and "넘어" in out[ids[-1]]["why"]

    async def down(tool, args):
        raise ConnectionError("gateway down")
    assert asyncio.run(L.mcad_revisions(down, [OLD]))[OLD] == {"state": "unknown", "why": "게이트웨이에 닿지 못했다(ConnectionError)"}


# ── 과제 key 의 이력(단위) ────────────────────────────────────────────────────────────────────────────────────
def test_옛_key_는_이력에_있고_지금_다른_산_과제의_key_가_아닐_때만_모은다():
    log: list = []
    gw = _gateway({L.STEPFORGE_OBJECT: lambda a: SF["object_renamed"], L._subject.RESOLVER_CALL: lambda a: SF["find_old_key"]}, log)
    assert asyncio.run(L.old_keys(gw, NEW_KEY, {NEW_KEY, OLD_KEY, "다른 과제"})) == ([OLD_KEY], "")
    assert log[0] == (L.STEPFORGE_OBJECT, {"focus": f"plm_task:{NEW_KEY}", "history": False})
    assert log[1][0] == L._subject.RESOLVER_CALL and log[1][1]["query"] == OLD_KEY and len(log) == 2, "카드가 있는 옛 key 만 살아 있는지 본다"
    # 옛 key 를 지금 다른 산 과제가 쓴다 — 풀이 결과에 글자 그대로 같은 활성 행이 하나
    taken = {"query": OLD_KEY, "tasks": [{"key": OLD_KEY, "label": "새로 선 다른 과제", "active": True}]}
    got, why = asyncio.run(L.old_keys(_gateway({L.STEPFORGE_OBJECT: lambda a: SF["object_renamed"], L._subject.RESOLVER_CALL: lambda a: taken}),
                                      NEW_KEY, {OLD_KEY}))
    assert got == [] and "다른 과제의 key" in why and OLD_KEY not in why
    # 풀이에 못 닿으면 모으지 않는다(닫힌 쪽)
    got, why = asyncio.run(L.old_keys(_gateway({L.STEPFORGE_OBJECT: lambda a: SF["object_renamed"]}), NEW_KEY, {OLD_KEY}))
    assert got == [] and "확인하지 못해" in why


def test_이력을_못_읽거나_물을_것이_없으면_모으지_않는다():
    log: list = []
    assert asyncio.run(L.old_keys(_gateway({}, log), NEW_KEY, {NEW_KEY})) == ([], "") and log == [], "다른 key 의 카드가 없으면 부르지 않는다"
    got, why = asyncio.run(L.old_keys(_gateway({}), NEW_KEY, {OLD_KEY}))
    assert got == [] and "이력을 읽지 못했다" in why
    other = {**SF["object_renamed"], "key": "엉뚱한 과제"}
    got, why = asyncio.run(L.old_keys(_gateway({L.STEPFORGE_OBJECT: lambda a: other}), NEW_KEY, {OLD_KEY}))
    assert got == [] and "그 과제가 아니다" in why
    plain = asyncio.run(L.old_keys(_gateway({L.STEPFORGE_OBJECT: lambda a: SF["object_plain"]}), OLD_KEY, {NEW_KEY}))
    assert plain == ([], ""), "이력이 빈 과제"


# ── 뒤 판의 리스크 변경 심사(단위) ──────────────────────────────────────────────────────────────────────────────
def test_뒤_판의_리스크_변경_심사는_diff_대상의_줄만_싣는다():
    log: list = []
    gw = _gateway({L.RISK_FIND: lambda a: RK["find_by_mcad"], L.RISK_DIFF: lambda a: RK["diff_lines"]}, log)
    out, why = asyncio.run(L.risk_diffs(gw, [NEW]))
    assert why == "" and len(out) == 1, out
    d = out[0]
    assert d["target_key"] == "diff:d-0102" and d["mcad_project_id"] == NEW and d["risk_project"]["code"] == "ALPHA-A2"
    assert d["total"] == 3 and d["by_kind"] == {"geometry": 2, "material": 1} and len(d["lines"]) == 3 and d["truncated"] is False
    assert log == [(L.RISK_FIND, {"artifact_kind": "mcad", "artifact_id": NEW, "limit": 5}),
                   (L.RISK_DIFF, {"diff_id": "d-0102", "part": "lines", "limit": L.DIFF_LINES})], "스냅샷 대상(snap:)은 묻지 않는다"
    out, why = asyncio.run(L.risk_diffs(_gateway({L.RISK_FIND: lambda a: RK["find_by_mcad"]}), [NEW]))
    assert out[0]["target_key"] == "diff:d-0102" and "unknown tool" in out[0]["error"] and "lines" not in out[0]
    out, why = asyncio.run(L.risk_diffs(_gateway({}), [NEW, OLD, LOOSE]))
    assert out == [] and "리스크 앱을 읽지 못했다" in why
    assert asyncio.run(L.risk_diffs(gw, [])) == ([], "")


# ── API ───────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def api(env, monkeypatch):  # noqa: F811
    c, st, s = env
    calls: list = []
    table: dict = {}

    async def fake_mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        if tool not in table:
            raise AuthError(f"{tool}: unknown tool: {tool}", status_code=502)
        return table[tool](args)
    monkeypatch.setattr(U, "mcp_call", fake_mcp)

    def login(who: str) -> dict:
        from app.auth.routes.local import _rl
        _rl.clear()
        return _login(c, who)

    def confirmed(who: str, cid: str, **kw) -> str:
        _relay(st, owner=who, cid=cid, **kw)
        iid = f"ins:web:{cid}:r1:default"
        assert c.post(f"/insights-api/cards/{iid}/confirm", headers=login(who)).status_code == 200
        return iid
    return SimpleNamespace(c=c, st=st, s=s, calls=calls, table=table, login=login, confirmed=confirmed)


def _cards(body: dict) -> dict:
    return {x["id"]: x for cell in body["rounds"] for x in cell["cards"]}


def test_과제_보기는_기구_CAD_가_든_카드의_판_표지를_읽을_때_셈한다(api):
    a = api.confirmed("me@example.com", "a", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    b = api.confirmed("me@example.com", "b", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": NEW, "rev": FP[NEW]}]})
    e = api.confirmed("me@example.com", "e")                                                    # ecad 뿐
    n = api.confirmed("me@example.com", "n", subject={**CONFIRMED, "artifacts": []})
    api.login("peer@example.com")
    api.calls.clear()
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}).json())
    assert got[a]["stale"]["state"] == "unknown" and got[b]["stale"]["state"] == "unknown", "StepForge 에 못 닿으면 모른다"
    api.table[L.STEPFORGE_META] = _meta
    api.calls.clear()
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}).json())
    assert got[a]["stale"]["state"] == "stale" and "뒤 판이 있다" in got[a]["stale"]["say"]
    assert got[b]["stale"]["state"] == "current" and got[e]["stale"]["state"] == "not_checked" and "stale" not in got[n]
    assert sorted(x[1]["project_id"] for x in api.calls if x[0] == L.STEPFORGE_META) == sorted([OLD, NEW]), "과제마다 한 번"
    assert "stale" not in json.dumps(api.st.get(a), ensure_ascii=False), "원장에 저장하지 않는다"


def test_카드_하나는_뒤_판의_리스크_변경_심사를_그_사람의_리스크_시야로_싣는다(api):
    a = api.confirmed("me@example.com", "a", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    api.table.update({L.STEPFORGE_META: _meta, L.RISK_FIND: lambda q: RK["find_by_mcad"], L.RISK_DIFF: lambda q: RK["diff_lines"]})
    api.login("peer@example.com")
    api.calls.clear()
    r = api.c.get(f"/insights-api/cards/{a}").json()
    assert r["stale"]["state"] == "stale" and r["stale"]["risk_note"] == L.RISK_DIFF_NOTE
    assert [d["target_key"] for d in r["stale"]["risk_diffs"]] == ["diff:d-0102"] and len(r["stale"]["risk_diffs"][0]["lines"]) == 3
    assert (L.RISK_FIND, {"artifact_kind": "mcad", "artifact_id": NEW, "limit": 5}) in api.calls
    # 과제 보기(목록)는 리스크 변경 심사를 싣지 않는다 — 카드를 열 때만 부른다
    api.calls.clear()
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}).json())
    assert "risk_diffs" not in got[a]["stale"] and not [x for x in api.calls if x[0] == L.RISK_DIFF]


def test_리스크_권한이_없으면_변경_심사를_부르지_않고_까닭을_단다(api, monkeypatch):
    from app.insights import routes as IR
    a = api.confirmed("me@example.com", "a", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    api.table.update({L.STEPFORGE_META: _meta, L.RISK_FIND: lambda q: RK["find_by_mcad"], L.RISK_DIFF: lambda q: RK["diff_lines"]})
    monkeypatch.setattr(IR, "RISK_PLAT", "plat:없는-권한")
    api.login("me@example.com")
    api.calls.clear()
    r = api.c.get(f"/insights-api/cards/{a}").json()
    assert r["stale"]["state"] == "stale" and "risk_diffs" not in r["stale"] and "리스크 앱 권한" in r["stale"]["risk_note"]
    assert not [x for x in api.calls if x[0] in (L.RISK_FIND, L.RISK_DIFF)]


def test_옛_key_로_남은_카드를_지금_과제의_보기와_찾기에_모은다(api):
    old = api.confirmed("me@example.com", "o", subject={**CONFIRMED, "sp_task": OLD_KEY})
    new = api.confirmed("me@example.com", "n")
    reused = api.confirmed("me@example.com", "x", subject={**CONFIRMED, "sp_task": "재사용된 옛 이름"})
    api.login("peer@example.com")
    body = api.c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert sorted(_cards(body)) == [new] and "previous_keys" not in body and "이력을 읽지 못했다" in body["keys_note"], "못 읽으면 모으지 않고 그렇다고 말한다"
    renamed = {**SF["object_renamed"], "keys": {**SF["object_renamed"]["keys"], "previous_keys": [OLD_KEY, "재사용된 옛 이름"]}}
    api.table[L.STEPFORGE_OBJECT] = lambda q: renamed
    api.table[L._subject.RESOLVER_CALL] = lambda q: ({"query": q["query"], "tasks": [{"key": q["query"], "label": "다른 과제", "active": True}]}
                                                     if q["query"] == "재사용된 옛 이름" else SF["find_old_key"])
    body = api.c.get("/insights-api/project", params={"sp_task": KEY}).json()
    cards = _cards(body)
    assert sorted(cards) == sorted([old, new]) and body["previous_keys"] == [OLD_KEY] and reused not in cards
    assert cards[old]["subject"]["sp_task"] == OLD_KEY, "카드의 key 는 그때의 것을 그대로 보인다"
    assert "다른 과제의 key" in body["keys_note"]
    found = api.c.get("/insights-api/find", params={"sp_task": KEY}).json()
    assert sorted(x["id"] for x in found["items"]) == sorted([old, new]) and found["previous_keys"] == [OLD_KEY]
    # 옛 key 로 열면 그 key 의 카드만이다(앞으로 푸는 길은 없다)
    assert sorted(_cards(api.c.get("/insights-api/project", params={"sp_task": OLD_KEY}).json())) == [old]


def test_볼_수_있는_카드가_그_과제뿐이면_이력을_부르지_않는다(api):
    new = api.confirmed("me@example.com", "n")
    _relay(api.st, owner="peer@example.com", cid="hidden", subject={**CONFIRMED, "sp_task": OLD_KEY})   # 남의 초안 — 나에게는 없는 key 다
    # 소속 없는 사람이 확인한 카드(범위가 그 사람뿐) — 상태는 공유지만 나에게는 보이지 않는다. 그 key 로도 이력을 부르지 않는다
    api.confirmed("out@example.com", "theirs", subject={**CONFIRMED, "sp_task": OLD_KEY})
    api.login("me@example.com")
    api.calls.clear()
    body = api.c.get("/insights-api/project", params={"sp_task": KEY}).json()
    assert sorted(_cards(body)) == [new] and "keys_note" not in body
    assert not [x for x in api.calls if x[0] == L.STEPFORGE_OBJECT]


def test_같은_결론은_볼_수_있는_같은_칸의_카드끼리만_묶어_센다(api):
    a = api.confirmed("me@example.com", "a")
    b = api.confirmed("peer@example.com", "b", cards=({**CARD, "claim": "- 리브를  1.2 MM 로 보강한다\n- 근거: 응력 412 MPa "},))
    api.confirmed("peer@example.com", "c", cards=({**CARD, "claim": "다른 결론"},))
    d = api.confirmed("peer@example.com", "d", subject={**CONFIRMED, "round": "pv1"})           # 같은 글이지만 다른 차수
    _relay(api.st, owner="peer@example.com", cid="draft")                                        # 같은 글 — 남의 초안
    api.confirmed("out@example.com", "o")                                                        # 같은 글 — 확인했지만 범위가 그 사람뿐(소속 없음)
    api.login("me@example.com")
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}).json())
    assert got[a]["same"] == {"n": 2, "ids": [b]} and got[b]["same"] == {"n": 2, "ids": [a]}, "남의 초안 · 다른 차수는 세지 않는다"
    assert "same" not in got["ins:web:c:r1:default"] and "same" not in got[d]
    assert api.st.get(a)["claim"] != api.st.get(b)["claim"], "묶어 보일 뿐 합치지 않는다"
    one = api.c.get(f"/insights-api/cards/{a}").json()
    assert one["same"] == {"n": 2, "ids": [b]}
    api.login("peer@example.com")
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}).json())
    assert got[b]["same"]["n"] == 3 and sorted(got[b]["same"]["ids"]) == sorted([a, "ins:web:draft:r1:default"]), "제 초안은 제 눈에 센다"


def test_검토_줄은_내가_손댈_카드와_까닭이다(api):
    _relay(api.st, owner="me@example.com", cid="w", subject=CLAIMED)                             # 주제 확인 기다림
    _relay(api.st, owner="me@example.com", cid="dr")                                             # 초안
    nr = api.confirmed("me@example.com", "nr", subject={**CONFIRMED, "round": None, "round_by": None})   # 차수 모름
    st = api.confirmed("me@example.com", "st", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    ok = api.confirmed("me@example.com", "ok")
    dp = api.confirmed("me@example.com", "dp")
    assert api.c.post(f"/insights-api/cards/{dp}/dispute", json={"note": "틀렸다"}, headers=api.login("me@example.com")).status_code == 200
    theirs = api.confirmed("peer@example.com", "p")
    assert api.c.post(f"/insights-api/cards/{theirs}/dispute", json={"note": "남의 반박"}, headers=api.login("peer@example.com")).status_code == 200
    api.table[L.STEPFORGE_META] = _meta
    api.login("me@example.com")
    body = api.c.get("/insights-api/review").json()
    got = {x["card"]["id"]: x["reasons"] for x in body["items"]}
    assert got == {"ins:web:w:r1:default": ["waiting"], dp: ["disputed"], st: ["stale"], "ins:web:dr:r1:default": ["draft"], nr: ["round_unknown"]}, got
    assert [x["card"]["id"] for x in body["items"]][:2] == ["ins:web:w:r1:default", dp], "기다림 · 반박이 먼저다"
    assert ok not in got and theirs not in got, "손댈 것이 없는 카드 · 남의 카드는 없다"
    assert body["counts"] == {"waiting": 1, "disputed": 1, "stale": 1, "draft": 1, "round_unknown": 1}
    assert all(x["say"] for x in body["items"])
    # 사람이 고른 '차수 모름' 은 줄에 서지 않는다
    assert api.c.post(f"/insights-api/cards/{nr}/round", json={"round": "unknown"}, headers=api.login("me@example.com")).status_code == 200
    assert nr not in {x["card"]["id"] for x in api.c.get("/insights-api/review").json()["items"]}


def test_관리자의_검토_줄에는_남의_반박_카드가_서고_범위_밖_읽기는_감사에_남는다(api):
    theirs = api.confirmed("peer@example.com", "p")
    assert api.c.post(f"/insights-api/cards/{theirs}/dispute", json={"note": "틀렸다"}, headers=api.login("peer@example.com")).status_code == 200
    _relay(api.st, owner="peer@example.com", cid="dr")
    api.login("out@example.com")
    assert api.c.get("/insights-api/review").json()["items"] == [], "남에게는 아무것도 없다"
    api.login("boss@example.com")
    body = api.c.get("/insights-api/review").json()
    assert [(x["card"]["id"], x["reasons"]) for x in body["items"]] == [(theirs, ["admin_disputed"])], "남의 초안은 관리자의 줄에도 없다"
    with closing(sqlite3.connect(api.s.agent_audit_log_path)) as db:
        metas = [json.loads(m) for (m,) in db.execute("SELECT meta FROM agent_audit WHERE event='insight_admin_read'").fetchall()]
    assert any(m["where"] == "review" and m["ids"] == [theirs] for m in metas)
    assert C.claim_key(" A  b\n") == "a b" and C.claim_key(None) == ""


# ── 반대 검토 11-22 — 퍼지는 자리에는 판정 낱말만 · 기한 · 관리자의 같은 결론 ──────────────────────────────────────────
def _pat_of(api, who: str) -> dict:
    """그 사람의 PAT 머리(게이트웨이 insight_get 이 포털을 부르는 꼴) — 쿠키는 지운다."""
    from app.agent import routes as R
    from app.main import app
    from test_insights import _principal
    api.login(who)
    pat = R._chat_user_pat(app.state.keystore, api.s, _principal(who))
    api.c.cookies.clear()
    return {"Authorization": f"Bearer {pat}"}


def test_판정_낱말만_내는_표지에는_뒤_판의_이름과_id_가_없다():
    full = L.card_stale(_subject(("mcad", OLD, FP[OLD])), _revs(OLD))
    assert full["state"] == "stale" and "(뒤 판 A2)" in full["say"] and L.next_ids(full) == [NEW]
    pub = L.public(full)
    assert pub == {"state": "stale", "say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"} and set(pub) == {"state", "say"}
    assert NEW not in json.dumps(pub, ensure_ascii=False) and L.public(None) is None
    for state in ("unknown", "current", "not_checked"):
        assert L.public({"state": state, "say": "x", "items": [{"state": state, "why": "StepForge 의 자세한 까닭"}]}) == \
            {"state": state, "say": L.stale_say(state, [], detail=False)}


def test_사람_PAT_로_읽은_답의_판_표지는_판정_낱말만이고_리스크_변경_심사는_부르지_않는다(api):
    """M1 — 게이트웨이 insight_get · insight_find 의 답은 근거로 다시 퍼질 수 있다(그 답을 근거로 쓴 카드의 범위에는 StepForge · 리스크 앱 토큰이
    없다). 뒤 판의 id · 이름 · 리스크 변경 줄은 포털 화면(세션)의 그 사람에게만 낸다."""
    a = api.confirmed("me@example.com", "a", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    api.table.update({L.STEPFORGE_META: _meta, L.RISK_FIND: lambda q: RK["find_by_mcad"], L.RISK_DIFF: lambda q: RK["diff_lines"]})
    auth = _pat_of(api, "peer@example.com")
    api.calls.clear()
    r = api.c.get(f"/insights-api/cards/{a}", headers=auth)
    assert r.status_code == 200 and r.json()["stale"] == {"state": "stale", "say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"}
    assert not [x for x in api.calls if x[0] in (L.RISK_FIND, L.RISK_DIFF)], "리스크 앱은 부르지도 않는다"
    text = r.text
    assert NEW not in text and "risk_diffs" not in text and "diff:d-0102" not in text and "(뒤 판" not in text
    for path, params in (("/insights-api/project", {"sp_task": KEY}), ("/insights-api/review", None)):
        got = api.c.get(path, params=params, headers=auth)
        assert got.status_code == 200 and NEW not in got.text and "(뒤 판" not in got.text, path
    got = _cards(api.c.get("/insights-api/project", params={"sp_task": KEY}, headers=auth).json())
    assert got[a]["stale"] == {"state": "stale", "say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"}
    # 같은 사람이 화면(세션)에서 읽으면 자세히 본다
    api.login("peer@example.com")
    full = api.c.get(f"/insights-api/cards/{a}").json()["stale"]
    assert "(뒤 판 A2)" in full["say"] and full["items"][0]["next"][0]["project_id"] == NEW and full["risk_diffs"]
    api.login("me@example.com")
    mine = api.c.get("/insights-api/review", headers=_pat_of(api, "me@example.com")).json()
    assert [x["card"]["stale"] for x in mine["items"]] == [{"state": "stale", "say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"}]


def test_관리자가_카드_하나를_볼_때_같은_결론에_남의_초안_id_를_싣지_않는다(api):
    """L3 — 같은 결론 표지(same.ids)는 읽는 사람이 볼 수 있는 카드만 센다. 관리자의 범위 밖 읽기로 본 남의 초안 id 가 감사 없이 실리지 않는다."""
    a = api.confirmed("peer@example.com", "a")
    b = api.confirmed("me@example.com", "b")
    _relay(api.st, owner="peer@example.com", cid="draft")                                        # 같은 글 — 남의 초안
    solo = api.confirmed("out@example.com", "o")                                                 # 같은 글 — 그 사람만(소속 없음)
    api.login("boss@example.com")                                                                # 관리자 — 소속 없음: 다 범위 밖 읽기다
    one = api.c.get(f"/insights-api/cards/{a}").json()
    assert "same" not in one, "관리자 표지 없이는 같은 칸에 볼 수 있는 다른 카드가 없다"
    assert "ins:web:draft:r1:default" not in json.dumps(one, ensure_ascii=False) and solo not in json.dumps(one, ensure_ascii=False)
    assert api.c.patch("/auth/access/users/boss@example.com", json={"affiliation": "CAEG"}, headers=api.login("boss@example.com")).status_code == 200
    api.login("boss@example.com")
    one = api.c.get(f"/insights-api/cards/{a}").json()
    assert one["same"] == {"n": 2, "ids": [b]}, "제 소속으로 보이는 것만 센다 — 남의 초안 · 그 사람만 보는 카드는 뺀다"
    # 범위 밖 카드를 볼 때도 그 카드 자신과 견줄 것은 내 시야의 카드뿐이다
    one = api.c.get(f"/insights-api/cards/{solo}").json()
    assert sorted(one["same"]["ids"]) == sorted([a, b]) and one["same"]["n"] == 3
    with closing(sqlite3.connect(api.s.agent_audit_log_path)) as db:
        metas = [json.loads(m) for (m,) in db.execute("SELECT meta FROM agent_audit WHERE event='insight_admin_read'").fetchall()]
    assert any(m["where"] == "card" and m["ids"] == [solo] for m in metas), "범위 밖으로 연 카드 자신은 감사에 남는다"


def test_기한을_넘긴_일은_취소만_걸고_뒤처리를_기다리지_않는다():
    """L5 — 게이트웨이 호출은 취소된 뒤에도 세션 닫기를 보내느라 호출 기한만큼 더 걸린다. 그것을 기다리면 상한이 그만큼 늘어난다."""
    import time
    state = {"cleaned": False}

    async def slow():
        try:
            await asyncio.sleep(5)
        finally:
            await asyncio.sleep(0.6)
            state["cleaned"] = True

    async def run():
        t0 = time.monotonic()
        with pytest.raises(TimeoutError):
            await L.bounded(slow(), 0.05)
        took = time.monotonic() - t0
        assert not state["cleaned"], "뒤처리가 끝나기를 기다리지 않았다"
        await asyncio.sleep(0.8)
        return took
    took = asyncio.run(run())
    assert took < 0.4 and state["cleaned"], f"{took:.2f}초 — 취소는 걸렸고 뒤처리는 뒤에서 끝난다"

    async def quick():
        return 7

    async def boom():
        raise ValueError("x")
    assert asyncio.run(L.bounded(quick(), 1)) == 7
    with pytest.raises(ValueError):
        asyncio.run(L.bounded(boom(), 1))


def test_갈래마다_기한_안에서_답하고_못_들은_것은_모른다고_한다():
    """L6 — 개정 줄 · 리스크 변경 심사 · key 이력은 저마다 기한(READ_BUDGET_S) 안에서 끝난다. 늦은 호출은 '모름' 으로 답한다."""
    import time

    async def late(tool, args):
        if tool == L.STEPFORGE_META and args["project_id"] == OLD:
            return {"id": OLD, "revision": SF["meta_old_with_next"]["revision"]}
        await asyncio.sleep(5)
        return {}
    t0 = time.monotonic()
    out = asyncio.run(L.mcad_revisions(late, [OLD, NEW], budget_s=0.1))
    assert time.monotonic() - t0 < 1.0
    assert out[OLD]["state"] == "ok" and out[NEW]["state"] == "unknown" and "기한" in out[NEW]["why"], "답한 것은 쓰고 늦은 것만 모른다"
    t0 = time.monotonic()
    diffs, why = asyncio.run(L.risk_diffs(late, [NEW], budget_s=0.1))
    assert time.monotonic() - t0 < 1.0 and diffs == [] and "기한" in why
    t0 = time.monotonic()
    old, why = asyncio.run(L.old_keys(late, KEY, {KEY, OLD_KEY}, budget_s=0.1))
    assert time.monotonic() - t0 < 1.0 and old == [] and "기한" in why, "이력을 못 읽으면 모으지 않는다(닫힌 쪽)"


def test_안쪽_기한의_합이_게이트웨이_인사이트_도구의_기한보다_짧다():
    """L6 — 안쪽이 먼저 걸려야 한다. 호출 하나 ≤ 갈래 하나, 한 창구가 차례로 도는 갈래 둘(과제 보기 — key 이력 + 개정 줄 · 카드 하나의 화면 —
    개정 줄 + 리스크 변경 심사)의 합이 게이트웨이 insight_find · insight_get 의 기한보다 짧다."""
    from app.insights import reuse as X
    gw = _ROOT.parent / "HWAXMcpGateway" / "gateway.py"
    if not gw.exists():
        pytest.skip(f"형제 리포 없음: {gw}")
    m = re.search(r'^INSIGHT_TIMEOUT_S = float\(os\.environ\.get\("GATEWAY_INSIGHT_TIMEOUT_S", "(\d+)"\) or (\d+)\)$', gw.read_text(encoding="utf-8"), re.M)
    assert m and m.group(1) == m.group(2)
    outer = float(m.group(1))
    assert 0 < L.CALL_TIMEOUT_S < L.READ_BUDGET_S and 2 * L.READ_BUDGET_S + 5 <= outer, (L.CALL_TIMEOUT_S, L.READ_BUDGET_S, outer)
    assert X.LAY_TIMEOUT_S >= 2 * L.READ_BUDGET_S
