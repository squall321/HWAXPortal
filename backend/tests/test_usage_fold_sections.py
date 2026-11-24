# 이용 통계 M2 — 접어 둔 표에서 읽는 칸: 원천을 가로지른 쓴 사람 · MCP 도구 · MCP 심의 · RA 초안 · 정문 · 날마다 찍은 수 · 접기 상태(docs/ops-dashboard)
#
# 한 장면(원장 · 게이트웨이 감사 · 잡 원장 · 정문 로그)을 임시 폴더에 만들고 실제 접기로 접은 뒤 관리자 통계 한 판을 지어 본다. 계정은 example.com 만 쓴다.
import json
from contextlib import closing
from datetime import date

import pytest
from tests.test_usage_fold import (
    NOW,
    TOKEN,
    Remote,
    _at,
    _audit_line,
    _box,
    _conv,
    _fold,
    _folds,
    _nginx_log,
    _ngx,
    _q,
)

from app import usage_fold

A, B, C = "a@example.com", "b@example.com", "c@example.com"
D17, D18, D19, D20 = (date(2026, 11, d) for d in (17, 18, 19, 20))


def _iso(day: date, h: int, mi: int = 0, s: int = 0) -> str:
    return f"{day.isoformat()}T{h:02d}:{mi:02d}:{s:02d}+09:00"


@pytest.fixture()
def scene(tmp_path):
    """11-17 ~ 11-20(오늘 — 금요일 12:00)의 쓰임. A 는 로그인 · 챗 · 타일 · MCP · 정문, B 는 로그인 없이 MCP · 심의 · RA, C 는 심의만."""
    box = _box(tmp_path)
    box.user(A, affiliation="CAEG")
    box.user(B, affiliation="LAB")
    box.sql("audit", "INSERT INTO access_log (ts, email, event, service, uid, detail) VALUES (?, ?, ?, ?, ?, ?)",
            [(int(_at(D17, 9)), A, "login", "portal", "uid-aaaa", "sso"), (int(_at(D18, 9)), A, "launch", "heax-hub", None, None)])
    box.audit((int(_at(D18, 10)), A, "chat_start"), (int(_at(D18, 10, 5)), A, "chat_start"))
    _conv(box, "c1", A, int(_at(D17, 10)))
    _conv(box, "c2", A, int(_at(D18, 10)), "deliberation", "mcp")
    box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked) VALUES ('p1', ?, ?, 'n', '[]', '[]', ?, ?, 0)",
            [(A, A, int(_at(D17, 11)), int(_at(D17, 11)) + 86400 * 90)])
    rem = Remote(tmp_path)
    rem.audit.write_text(
        _audit_line(_iso(D18, 11, 0, 0), "search_cards", "ai-data-hub", via="pat", caller=A, ms=20, chars=500)
        + _audit_line(_iso(D18, 11, 0, 1), "search_cards", "ai-data-hub", via="pat", caller=A, ms=40, chars=200000)
        + _audit_line(_iso(D18, 11, 0, 2), "search_cards", "ai-data-hub", via="pat", caller=A, ms=900)
        + _audit_line(_iso(D18, 11, 0, 3), "search_cards", "ai-data-hub", via="pat", caller=A, ok=False, error="upstream: boom")
        + _audit_line(_iso(D18, 11, 0, 4), "search_cards", "ai-data-hub", via="pat", caller=A, ms=0, note="cache-hit")
        + _audit_line(_iso(D18, 11, 1, 0), "deliberate_status", "hwax-deliberation", via="pat", caller=A)
        + _audit_line(_iso(D18, 11, 1, 1), "deliberate_status", "hwax-deliberation", via="pat", caller=A)
        + _audit_line(_iso(D18, 11, 2, 0), "search_cards", "ai-data-hub", via="pat", caller=B, ms=30)
        + _audit_line(_iso(D18, 11, 3, 0), "delete_report", "reportarchive", via="pat", caller=B, ok=False, error="read-only")
        + _audit_line(_iso(D19, 9, 0, 0), "create_report_draft", "reportarchive", via="chat", caller=B)
        + _audit_line(_iso(D19, 9, 0, 1), "create_report_draft", "reportarchive", via="gw-token")
        + _audit_line(_iso(D19, 9, 0, 2), "create_report_draft", "reportarchive", via="chat", caller=A, ok=False, error="upstream: 500")
        + _audit_line(_iso(D19, 9, 1, 0), "POST /mcp", None, ok=False, ms=0, error="unauthorized: expired")
        + _audit_line(_iso(D19, 9, 1, 1), "GET /mcp", None, ok=False, ms=0, error="unauthorized: expired"), encoding="utf-8")
    rem.jobs += [
        {"id": "j1", "job": "default", "status": "done", "started_at": _at(D19, 13), "finished_at": _at(D19, 13, 30), "user": B, "owner_aff": "LAB",
         "seats": [{"key": "x"}, {"key": "y"}, {"key": "z"}], "round": 2, "report_id": 41},
        {"id": "j2", "job": "sim-plan", "status": "error", "started_at": _at(D19, 14), "finished_at": _at(D19, 14, 10), "user": C,
         "seats": [{"key": "x"}], "round": 1}]
    _nginx_log(box, _ngx(_at(D19, 15), "/apps/step_forge/", "uid-aaaa"), _ngx(_at(D19, 15, 1), "/apps/step_forge/api", "uid-aaaa"),
               _ngx(_at(D19, 15, 2), "/robots.txt"), _ngx(_at(D20, 9), "/agent/chat", "uid-aaaa"))
    out = _fold(box, handler=rem)
    assert not [v for v in out.values() if isinstance(v, dict)], out
    return box, rem


def _sec(box, name, days=7, **kw):
    return box.build(days=days, now=NOW, **kw)["sections"][name]


def _by(sec, key):
    return {r[key]: r for r in sec["rows"]}


# ── 접기 전 ────────────────────────────────────────────────────────────────────────────────────────────────
def test_접어_둔_표가_없으면_그_칸들은_pending_이고_M1_칸은_그대로_낸다(tmp_path):
    box = _box(tmp_path)
    box.access((int(_at(D19, 9)), A, "login", "portal", "local"))
    sec = box.build(days=7, now=NOW)["sections"]
    for name in ("fold_status", "active_daily", "active_weekly", "active_monthly", "mcp_daily", "mcp_via", "mcp_apps", "mcp_tools", "mcp_auth",
                 "mcp_personal_weekly", "delib_jobs", "ra_drafts", "front_door", "snapshots", "conversations_kept"):
        assert sec[name]["pending"] is True and sec[name]["rows"] == [] and "접은 적이 없다" in sec[name]["note"] and not sec[name].get("error"), name
    assert sec["logins_daily"]["totals"]["logins"] == 1


# ── 쓴 사람 ────────────────────────────────────────────────────────────────────────────────────────────────
def test_쓴_사람은_원천을_가로질러_서로_다른_계정이다(scene):
    box, _ = scene
    sec = _sec(box, "active_daily")
    rows = _by(sec, "day")
    assert [rows[d.isoformat()]["people"] for d in (date(2026, 11, 16), D17, D18, D19, D20)] == [None, 1, 2, 3, 1], \
        "접어 둔 첫 날(11-17) 전은 기록 전(null) — B 는 로그인한 적이 없어도 MCP 로 쓴 날에 든다"
    d18 = rows["2026-11-18"]
    assert (d18["login"], d18["chat"], d18["tile"], d18["mcp"], d18["delib"], d18["nginx"]) == (0, 1, 1, 2, 0, 0)
    d19 = rows["2026-11-19"]
    assert (d19["mcp"], d19["delib"], d19["nginx"]) == (2, 2, 1)
    assert sec["totals"] == {"people": 3, "login": 1, "chat": 1, "tile": 1, "mcp": 2, "engine": 0, "delib": 2, "nginx": 1}
    assert sec["first_day"] == "2026-11-17"
    assert _sec(box, "logins_daily")["totals"]["accounts"] == 1, "로그인 기준(M1)은 A 하나뿐이다 — 그 차이가 이 칸의 까닭이다"
    assert "12:00 에 접은 데까지" in sec["note"]


def test_주_달마다_쓴_사람은_날을_건너_한_번만_세고_기록_전은_null_이다(scene):
    box, _ = scene
    weeks = _sec(box, "active_weekly", days=14)["rows"]
    assert weeks == [{"week": "2026-11-02", "people": None, "partial": False}, {"week": "2026-11-09", "people": None, "partial": False},
                     {"week": "2026-11-16", "people": 3, "partial": True}], "A 는 나흘 썼어도 그 주에 한 번 — 아직 안 끝난 주라 partial"
    assert _sec(box, "active_monthly", days=40)["rows"] == [{"month": "2026-10", "people": None, "partial": False},
                                                           {"month": "2026-11", "people": 3, "partial": True}]


def test_사람_줄의_뺄_계정은_다시_접지_않아도_읽을_때_빠진다(scene):
    box, _ = scene
    box.s = box.s.model_copy(update={"usage_exclude_accounts": B})
    sec = _sec(box, "active_daily")
    assert sec["totals"]["people"] == 2 and _by(sec, "day")["2026-11-18"]["people"] == 1
    assert _sec(box, "mcp_daily")["totals"]["people"] == 1 and _sec(box, "ra_drafts")["totals"]["people"] == 0
    status = _by(_sec(box, "fold_status"), "source")
    assert status["gateway"]["other_list_days"] == 3 and status["portal"]["other_list_days"] == 4, "어느 목록으로 접었는지 화면이 안다"
    assert "접을 때의 목록" in box.build(days=7, now=NOW)["excluded"]["note"]


def test_이메일은_사람별_표_하나에만_실린다(scene):
    """사람별 표(사용자 결정 2026-11-22 · OD-55)만 이메일을 낸다 — 합계 칸은 서로 다른 계정의 수만. 비밀 · 주소도 어디에도 없다."""
    box, _ = scene
    rep = box.build(days=30, now=NOW)
    people = rep["sections"].pop("people")
    blob = json.dumps(rep, ensure_ascii=False)
    for leak in (A, B, C, "uid-aaaa", TOKEN, "gateway.test"):
        assert leak not in blob, leak
    assert {r["email"] for r in people["rows"]} == {A, B, C}
    assert TOKEN not in json.dumps(people) and "uid-aaaa" not in json.dumps(people)


# ── MCP 도구 ───────────────────────────────────────────────────────────────────────────────────────────────
def test_MCP_호출은_날마다_상태_묻기를_따로_세고_기록_전은_null_이다(scene):
    box, _ = scene
    sec = _sec(box, "mcp_daily")
    rows = _by(sec, "day")
    assert rows["2026-11-17"]["calls"] is None, "감사 원장의 첫 날(11-18) 전"
    d18 = rows["2026-11-18"]
    assert (d18["calls"], d18["status_calls"], d18["errors"], d18["people"]) == (7, 2, 2, 2)
    assert (rows["2026-11-19"]["calls"], rows["2026-11-19"]["errors"], rows["2026-11-20"]["calls"]) == (3, 1, 0)
    assert sec["totals"] == {"calls": 10, "status_calls": 2, "errors_app": 2, "errors_gate": 1, "cache": 1, "big": 1, "people": 2, "anon_calls": 1,
                             "for_calls": 0, "people_for": 0}
    assert sec["first_day"] == "2026-11-18" and "상태 묻기" in sec["note"]


def test_MCP_호출을_자격_앱_도구로_가르고_지연은_어림이다(scene):
    box, _ = scene
    via = _by(_sec(box, "mcp_via"), "via")
    assert (via["pat"]["calls"], via["pat"]["status_calls"], via["pat"]["people"], via["pat"]["errors_app"], via["pat"]["errors_gate"]) == (7, 2, 2, 1, 1)
    assert (via["chat"]["calls"], via["chat"]["people"], via["gw-token"]["anon_calls"], via["gw-token"]["people"]) == (2, 2, 1, 0)
    assert _sec(box, "mcp_via")["via_since"] == "2026-11-18" and "2026-11-18 부터" in _sec(box, "mcp_via")["note"]
    apps = _sec(box, "mcp_apps")
    hub = _by(apps, "app")["ai-data-hub"]
    assert (hub["calls"], hub["errors_app"], hub["errors_gate"], hub["cache"], hub["big"], hub["tools"], hub["error_rate"]) == (6, 1, 0, 1, 1, 1, 0.167)
    assert 25 < hub["ms_p50"] <= 50 and 500 < hub["ms_p95"] <= 1000 and apps["approx"] is True, hub
    assert [r["app"] for r in apps["rows"]][0] == "ai-data-hub", "많이 불린 앱이 먼저"
    tools = _sec(box, "mcp_tools")
    first = tools["rows"][0]
    assert (first["app"], first["tool"], first["calls"], first["status"]) == ("ai-data-hub", "search_cards", 6, False)
    status = next(r for r in tools["rows"] if r["tool"] == "deliberate_status")
    assert status["status"] is True and status["calls"] == 2 and tools["total_tools"] == 4
    assert _sec(box, "mcp_auth")["rows"] == [{"reason": "expired", "n": 2}]


def test_개인_Claude_를_쓴_사람은_주마다_센다(scene):
    box, _ = scene
    rows = _sec(box, "mcp_personal_weekly", days=14)["rows"]
    assert rows[-1] == {"week": "2026-11-16", "people": 2, "partial": True} and rows[0]["people"] is None


# ── 심의 · RA ──────────────────────────────────────────────────────────────────────────────────────────────
def test_MCP_심의_잡은_종류마다_세고_웹_심의가_빠진다고_말한다(scene):
    box, _ = scene
    sec = _sec(box, "delib_jobs")
    rows = _by(sec, "kind")
    assert rows["default"] == {"kind": "default", "n": 1, "done": 1, "states": {"done": 1}, "external": 0, "with_report": 1, "seats_avg": 3.0,
                               "rounds_avg": 2.0, "minutes_avg": 30.0}
    assert (rows["sim-plan"]["done"], rows["sim-plan"]["states"], rows["sim-plan"]["minutes_avg"]) == (0, {"error": 1}, 10.0)
    assert sec["totals"] == {"jobs": 2, "with_report": 1, "people": 2, "anon_jobs": 0}
    assert sec["daily"][-3:] == [None, 2, 0] and sec["first_day"] == "2026-11-19", "잡 원장의 첫 날(11-19) 전은 기록 전이다"
    assert "웹 챗에서 연 심의" in sec["note"]


def test_RA_초안은_성공한_호출만_세고_이름_없는_초안을_따로_말한다(scene):
    box, _ = scene
    box.sql("procedures", "INSERT INTO routine_runs (id, owner_sub, routine_id, version_id, version_no, title, inputs_json, plan_json, executor, state,"
                          " started_at, deadline, ra_report_id) VALUES (?, ?, 'x', 'v', 1, 't', '{}', '{}', 'chat', 'done', ?, ?, ?)",
            [("r1", A, int(_at(D19, 9)), int(_at(D19, 10)), "55"), ("r2", A, int(_at(D19, 9)), int(_at(D19, 10)), None)])
    sec = _sec(box, "ra_drafts")
    assert {r["day"]: r["n"] for r in sec["rows"] if r["n"]} == {"2026-11-19": 2}, "실패한 호출은 초안이 아니다"
    assert sec["by_via"] == [{"via": "chat", "n": 1}, {"via": "gw-token", "n": 1}]
    assert sec["totals"] == {"drafts": 2, "people": 1, "named": 1, "named_for": 0, "people_for": 0, "unnamed": 1, "delib_reports": 1}
    assert _sec(box, "routine_runs")["ra_drafts"] == 1


# ── 정문 · 찍어 둔 수 ──────────────────────────────────────────────────────────────────────────────────────
def test_정문_요청은_서비스마다_세고_허브_앱이_보인다(scene):
    box, _ = scene
    sec = _sec(box, "front_door", labels={"service": {"heax-hub": "HEAX 허브"}})
    rows = _by(sec, "service")
    app = rows["apps/step_forge"]
    assert (app["requests"], app["people_max"], app["days"], app["daily"][-2:]) == (2, 1, 1, [2, 0])
    assert rows["portal"]["daily"][-1] == 1 and sec["totals"] == {"requests": 3, "unattributed": 1, "people": 1}
    assert sec["first_day"] == "2026-11-19" and app["daily"][0] is None, "정문 로그가 덮지 않는 날은 기록 전이다"


def test_날마다_찍은_수는_찍은_날만_있고_닫힌_날의_낸_PAT_은_지워져도_남는다(scene):
    box, rem = scene
    rows = _by(_sec(box, "snapshots"), "day")
    assert rows["2026-11-19"]["pats_live"] is None, "찍지 못한 날 — 지난 날의 상태는 지어내지 않는다"
    today = rows["2026-11-20"]
    assert (today["pats_live"], today["pats_personal"], today["accounts_active"], today["connections"], today["grants"]) == (1, 1, 2, 0, 0)
    assert (rows["2026-11-17"]["pats_issued"], rows["2026-11-18"]["pats_issued"], rows["2026-11-16"]["pats_issued"]) == (1, 0, None)
    box.sql("tokens", "DELETE FROM pat WHERE jti = ?", [("p1",)])            # 만료 PAT 은 원장에서 지워진다
    box.sql("conv", "DELETE FROM conversations WHERE id = ?", [("c1",)])     # 주인이 대화를 지웠다
    _fold(box, _at(date(2026, 11, 21)), rem)
    assert _by(_sec(box, "snapshots"), "day")["2026-11-17"]["pats_issued"] == 1, "11-17 은 11-20 에 닫혔다"
    kept = {(r["kind"], r["source"]): r["n"] for r in _sec(box, "conversations_kept")["rows"]}
    assert kept == {("chat", "web"): 1, ("deliberation", "mcp"): 1}
    assert _sec(box, "conversations")["totals"] == [{"kind": "deliberation", "source": "mcp", "n": 1, "owners": 1}], "지금 남은 대화(M1)에는 없다"


# ── 접기 상태 ──────────────────────────────────────────────────────────────────────────────────────────────
def test_접기_상태는_원천마다_범위와_실패_까닭을_낸다(scene):
    box, rem = scene
    rows = _by(_sec(box, "fold_status"), "source")
    assert list(rows) == ["portal", "snapshot", "nginx", "gateway", "agent"]
    assert (rows["portal"]["first_day"], rows["portal"]["last_day"], rows["portal"]["closed_through"], rows["portal"]["error"]) == \
        ("2026-11-17", "2026-11-20", "2026-11-17", None)
    assert (rows["nginx"]["first_day"], rows["gateway"]["first_day"], rows["agent"]["first_day"]) == ("2026-11-19", "2026-11-18", "2026-11-19")
    assert rows["gateway"]["attempt_at"] == int(NOW) and rows["gateway"]["other_list_days"] == 0
    rem.status["gateway.test"] = 404
    _fold(box, NOW + 3600, rem)
    gw = _by(_sec(box, "fold_status"), "source")["gateway"]
    assert "판이 낡았다" in gw["error"] and gw["last_day"] == "2026-11-20", "앞서 접은 데까지는 그대로 보인다"
    assert "마지막 접기가 실패했다" in _sec(box, "mcp_daily")["note"] and _sec(box, "mcp_daily")["totals"]["calls"] == 10
    assert "판이 낡았다" in _folds(box, "gateway")["*"][2]


# ── 사용자 결정 2026-11-22 — 누구의 일 · 사람별 LLM 토큰 · 사람별 표(OD-52 · OD-53 · OD-55) ──────────────────────────────────
def _tok(day, user, kind, model, calls, unknown=0, tin=0, tout=0, cache=0):
    return {"day": day.isoformat(), "user": user, "kind": kind, "model": model, "calls": calls, "unknown": unknown, "tokens_in": tin,
            "tokens_out": tout, "cache_read": cache}


@pytest.fixture()
def decided(tmp_path):
    """C 는 로그인 없이 심의 준비만 했다 — 엔진이 C 의 일로 서비스 자격 도구를 불렀고(누구의 일 머리) C 의 일로 RA 초안이 하나 생겼다. LLM 토큰은 A · C ·
    시스템(사람 없음)의 것이 있다."""
    box = _box(tmp_path)
    box.user(A, affiliation="CAEG")
    box.user(C, affiliation="LAB")
    box.sql("audit", "INSERT INTO access_log (ts, email, event, service, uid, detail) VALUES (?, ?, 'login', 'portal', 'uid-aaaa', 'sso')",
            [(int(_at(D18, 9)), A)])
    box.audit((int(_at(D19, 10)), A, "chat_start"))
    rem = Remote(tmp_path)
    rem.audit.write_text(
        _audit_line(_iso(D19, 11, 0, 0), "recommend_agents", "ai-data-hub", via="gw-token", audit_for=C)
        + _audit_line(_iso(D19, 11, 0, 1), "agent_search", "ai-data-hub", via="gw-token", audit_for=C)
        + _audit_line(_iso(D19, 11, 0, 2), "create_report_draft", "reportarchive", via="gw-token", audit_for=C)
        + _audit_line(_iso(D19, 11, 0, 3), "list_agents", "ai-data-hub", via="gw-token")
        + _audit_line(_iso(D19, 11, 0, 4), "search_cards", "ai-data-hub", via="pat", caller=A), encoding="utf-8")
    rem.llm_since = D18.isoformat()
    rem.llm += [_tok(D19, A, "chat", "qwen-chat", 3, unknown=1, tin=900, tout=100, cache=500),
                _tok(D19, A, "delib", "glm-5", 2, tin=4000, tout=600),
                _tok(D20, C, "delib", "glm-5", 1, tin=1000, tout=200),
                _tok(D20, "", "card_review", "glm-5", 4, tin=8000, tout=400)]
    out = _fold(box, handler=rem)
    assert not [v for k, v in out.items() if isinstance(v, dict) and k != "nginx"], out     # 정문 로그는 이 장면에 없다
    return box, rem


def test_잡이_없어도_토큰을_적기_시작한_날부터_접는다(tmp_path):
    """에이전트 서버 원장의 첫 날은 잡 원장과 토큰 기록 가운데 이른 쪽이다 — 잡이 하나도 없는 박스에서 토큰 칸이 영영 비지 않게."""
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.llm_since, rem.llm = D19.isoformat(), [_tok(D19, A, "chat", "qwen-chat", 1, tin=10, tout=2)]
    assert _fold(box, handler=rem)["agent"] == 2 and _folds(box, "agent")["2026-11-19"][0] == 0
    assert box.build(days=7, now=NOW)["sections"]["llm_tokens"]["totals"]["tokens_in"] == 10


def test_누구의_일로_이은_엔진_호출은_엔진_갈래이고_이름_없는_줄에서_빠진다(decided):
    box, _ = decided
    sec = box.build(days=7, now=NOW)["sections"]
    assert sec["mcp_daily"]["totals"]["for_calls"] == 3 and sec["mcp_daily"]["totals"]["people_for"] == 1
    assert sec["mcp_daily"]["totals"]["anon_calls"] == 1 and sec["mcp_daily"]["totals"]["people"] == 1, "엔진 줄은 본인이 부른 도구가 아니다"
    gw = _by(sec["mcp_via"], "via")["gw-token"]
    assert (gw["for_calls"], gw["people_for"], gw["anon_calls"], gw["people"]) == (3, 1, 1, 0)
    assert sec["active_daily"]["totals"]["engine"] == 1 and _by(sec["active_daily"], "day")["2026-11-19"]["engine"] == 1
    assert sec["ra_drafts"]["totals"] == {"drafts": 1, "people": 0, "named": 0, "named_for": 1, "people_for": 1, "unnamed": 0, "delib_reports": 0}


def test_사람별_LLM_토큰은_종류와_모델로_합치고_적기_전은_null_이다(decided):
    box, _ = decided
    sec = box.build(days=7, now=NOW)["sections"]["llm_tokens"]
    assert sec["since"] == "2026-11-18" and sec["daily"][-4:] == [None, 0, 5600, 9600] and sec["daily"][0] is None
    rows = {(r["kind"], r["model"]): r for r in sec["rows"]}
    assert rows[("chat", "qwen-chat")] == {"kind": "chat", "model": "qwen-chat", "calls": 3, "unknown": 1, "tokens_in": 900, "tokens_out": 100,
                                           "cache_read": 500}
    assert rows[("delib", "glm-5")]["tokens_in"] == 5000 and rows[("card_review", "glm-5")]["calls"] == 4
    assert [r["kind"] for r in sec["rows"]] == ["chat", "delib", "card_review"], "종류는 정해진 차례로"
    assert sec["totals"] == {"calls": 10, "unknown": 1, "tokens_in": 13900, "tokens_out": 1300, "cache_read": 500, "people": 2}
    assert "모른다" in sec["note"] and "LLM_STREAM_USAGE" in sec["note"]


def test_서버에_맡긴_일은_종류_offload_로_접고_모르는_종류는_그_밖이다(tmp_path):
    """토큰 절감 2판(docs/token-saving TS-16) — 에이전트 서버가 offload 로 단 줄은 offload 로 접는다(그 밖으로 뭉개지 않는다). 모르는 종류는 종전처럼
    그 밖이다. 옛 기록의 other 는 다시 쓰지 않는다 — 접을 때 받은 종류 그대로다."""
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.llm_since = D19.isoformat()
    rem.llm = [_tok(D19, A, "offload", "qwen-chat", 2, tin=700, tout=70), _tok(D19, A, "other", "glm-5", 1, tin=50, tout=5),
               _tok(D19, A, "새-종류", "glm-5", 1, tin=30, tout=3), _tok(D20, A, "chat", "qwen-chat", 1, tin=10, tout=1)]
    _fold(box, handler=rem)
    assert sorted({k for _d, _e, k, *_r in _q(box, "SELECT * FROM usage_llm_daily")}) == ["chat", "offload", "other"]
    sec = box.build(days=7, now=NOW)["sections"]["llm_tokens"]
    rows = {(r["kind"], r["model"]): r for r in sec["rows"]}
    assert rows[("offload", "qwen-chat")]["tokens_in"] == 700 and rows[("other", "glm-5")]["tokens_in"] == 80, "모르는 종류는 그 밖에 더한다"
    assert [r["kind"] for r in sec["rows"]] == ["chat", "offload", "other"], "offload 는 카드 대조 뒤 · 그 밖 앞"
    assert "서버에 맡긴 일" in sec["note"]


def test_LLM_종류는_접기_통계_화면_에이전트_서버가_같은_목록이다():
    """종류 목록은 네 곳에 있다 — 에이전트 서버 usage_tokens.KINDS(단다) · usage_fold(접는다) · usage_stats(차례) · 화면 이름표. 하나만 더하면 그 종류가 그 밖으로
    뭉개지거나 화면에 날것으로 뜬다. 에이전트 서버 쪽은 형제 리포 원문(AST)으로 본다."""
    import ast
    import re
    from pathlib import Path

    from app import usage_stats
    root = Path(__file__).resolve().parents[2]
    assert usage_fold.LLM_KINDS == usage_stats.LLM_KINDS and usage_fold.LLM_KINDS[-1] == "other"
    tsx = (root / "frontend" / "src" / "components" / "usage" / "UsageFoldCards.tsx").read_text(encoding="utf-8")
    block = re.search(r"const LLM_KIND: Record<string, string> = \{(.*?)\};", tsx, re.S).group(1)
    assert set(re.findall(r"^\s*(\w+):", block, re.M)) == set(usage_fold.LLM_KINDS), "화면 이름표"
    ag = root.parent / "HWAXAgentServer" / "usage_tokens.py"
    if not ag.exists():
        pytest.skip("형제 리포 HWAXAgentServer 가 없다")
    kinds = next(ast.literal_eval(n.value) for n in ast.parse(ag.read_text(encoding="utf-8")).body
                 if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "KINDS" for t in n.targets))
    assert tuple(kinds) == usage_fold.LLM_KINDS, f"에이전트 서버 KINDS {kinds} 와 포털이 다르다 — 함께 고친다"


def test_사람별_표는_사람마다_갈래_수와_토큰을_더하고_뺄_계정은_읽을_때_뺀다(decided):
    box, _ = decided
    sec = box.build(days=7, now=NOW, labels={"affiliation": {"CAEG": "CAE그룹"}})["sections"]["people"]
    rows = {r["email"]: r for r in sec["rows"]}
    a, c = rows[A], rows[C]
    assert (a["login"], a["chat"], a["mcp"], a["engine"], a["llm_calls"], a["llm_tokens_in"], a["llm_unknown"]) == (1, 1, 1, 0, 5, 4900, 1)
    assert (a["affiliation"], a["affiliation_label"], a["active_days"], a["first_day"], a["last_day"]) == ("CAEG", "CAE그룹", 2, "2026-11-18",
                                                                                                         "2026-11-19")
    assert (c["login"], c["engine"], c["ra"], c["llm_calls"], c["llm_tokens_out"], c["affiliation"]) == (0, 3, 1, 1, 200, "LAB")
    assert "" not in rows and sec["total"] == 2 and sec["truncated"] is False, "사람이 없는 일(시스템)은 사람별 표에 없다"
    assert [r["email"] for r in sec["rows"]] == [A, C], "쓴 날이 많은 사람이 먼저"
    box.s = box.s.model_copy(update={"usage_exclude_accounts": C})
    assert [r["email"] for r in box.build(days=7, now=NOW)["sections"]["people"]["rows"]] == [A]
    assert box.build(days=7, now=NOW)["sections"]["llm_tokens"]["totals"]["people"] == 1


def test_토큰_줄은_다시_접어도_같고_400일_뒤_지운다(decided):
    box, rem = decided
    dump = lambda: _q(box, "SELECT * FROM usage_llm_daily ORDER BY 1, 2, 3, 4")  # noqa: E731
    first = dump()
    assert [(d, e, k, m, calls) for d, e, k, m, calls, *_ in first] == [
        ("2026-11-19", A, "chat", "qwen-chat", 3), ("2026-11-19", A, "delib", "glm-5", 2), ("2026-11-20", "", "card_review", "glm-5", 4),
        ("2026-11-20", C, "delib", "glm-5", 1)]
    assert {r[-1] for r in first if r[1]} == {"CAEG", "LAB"}, "그때의 소속"
    _fold(box, NOW + 600, rem)
    assert dump() == first
    rem.llm = [r for r in rem.llm if r["user"] != A]              # 다시 접은 날의 줄은 지우고 넣는다(늘지 않는다)
    rem.today = "2026-11-21"
    _fold(box, _at(date(2026, 11, 21)), rem)                       # 날이 바뀐 첫 접기 — 닫히지 않은 11-19 · 11-20 을 다시 접는다
    assert [r[1] for r in dump()] == ["", C]
    with closing(usage_fold.connect(box.s)) as conn:
        conn.execute("INSERT INTO usage_llm_daily VALUES ('2025-10-16', 'old@example.com', 'chat', 'm', 1, 0, 1, 1, 0, '')")
    _fold(box, _at(date(2026, 11, 21), 13), rem)
    assert "old@example.com" not in json.dumps(dump())


def test_무기한_합계_표에는_이메일이_없다(decided):
    """이메일은 사람 줄 · 사람별 토큰(400일)에만 있다 — 합계(usage_daily)와 접기 기록(usage_fold)은 무기한이라 사람을 싣지 않는다."""
    box, _ = decided
    assert _q(box, "SELECT COUNT(*) FROM usage_llm_daily WHERE email != ''")[0][0] > 0
    assert _q(box, "SELECT COUNT(*) FROM usage_actor_daily WHERE source LIKE '%-for%'")[0][0] > 0
    for table in ("usage_daily", "usage_fold"):
        assert "@" not in json.dumps(_q(box, f"SELECT * FROM {table}"), ensure_ascii=False), table  # noqa: S608 — 고정 글자


def test_옛_에이전트_서버는_토큰_칸이_없어도_접고_토큰_카드는_적기_전이다(tmp_path):
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.agent_old = True
    out = _fold(box, handler=rem)
    assert not isinstance(out["agent"], dict), out
    sec = box.build(days=7, now=NOW)["sections"]["llm_tokens"]
    assert sec["since"] is None and set(sec["daily"]) == {None} and "아직 토큰을 내지 않았다" in sec["note"]
