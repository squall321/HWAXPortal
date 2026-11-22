# 과제 인사이트 다시 쓰기(M3) — 웹 일반 심의 시작에 같은 (과제, 차수)의 앞선 인사이트를 근거로 깔기 · 범위 이어받기(docs/project-insight-graph PLAN §7.1)
"""고정하는 것.
  · 깔기는 확인된 주제 · 같은 (과제, 차수) 칸 · 산출물 범위 안(시작한 사람의 소속 · 조직 — plat 이 붙은 것 · 주인만 보는 것은 아니다)의 카드만이다.
    다른 차수 · 차수 모름은 그 사람의 화면에 수만 알린다(근거에 싣지 않는다). RA 작업 공간의 범위를 모르면 조직에 연 카드만 깐다.
  · 주제가 없거나 · 확인되지 않았거나 · 볼 수 있는 카드가 없으면 에이전트 서버로 가는 요청이 종전과 **바이트까지** 같다. 깔기가 터져도 같다.
  · 리스크 심사 계열(의장 risk-review* · 앱이 띄운 패널)에는 깔지 않는다(D-18) — 확인도 부르지 않는다.
  · 누설 — 남의 초안 · 다른 소속의 카드 · 관리자의 범위 밖 읽기는 깔리지도 세어지지도 않는다. 과제 인사이트 권한이 없으면 깔지 않는다.
  · 앞선 인사이트를 근거로 쓴 카드의 확인 범위는 읽은 카드들의 범위를 다 담는다(PLAN §6.2 최소 범위) — 모르면 주인만 본다.
  · 엔진과 같은 수 · 같은 이름 규칙은 형제 리포의 원본과 맞댄다.
계정은 example.com 시험 신원만 쓴다."""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import routes as R
from app.agent import upload as U
from app.auth.errors import AuthError
from app.insights import cards as C
from app.insights import intake as I
from app.insights import lineage as L
from app.insights import reuse as X
from app.main import app

from test_insights import CARD, CONFIRMED, KEY, _login, _relay, env  # noqa: F401 — env 는 픽스처다

_ROOT = Path(__file__).resolve().parents[2]
_AGENT = _ROOT.parent / "HWAXAgentServer"
MSG = "/심의 힌지 크랙의 원인을 규명한다"
ASK = {"sp_task": KEY, "round": "dv1", "text": "알파 1차"}
FRAMES = [("delib", {"kind": "decision", "text": "결정문"}), ("done", {})]


def _v(email="me@example.com", aff="CAEG", groups=("feat:insights",), admin=False):
    return C.Viewer(email=email, sub=email, aff=aff, groups=frozenset(groups), admin=admin)


def _row(i, *, owner="peer@example.com", status="confirmed", scope=("aff:CAEG",), rnd="dv1", at=100, claim="리브를 보강한다", **kw):
    return {"id": f"ins:web:c{i}:r:default", "path": "web", "source_id": f"c{i}", "stage": "default", "owner_email": owner, "status": status,
            "scope": list(scope), "round": rnd, "sp_task": KEY, "created_at": at, "claim": claim,
            "subject": {"sp_task": KEY, "round": rnd, "artifacts": []}, "card": dict(CARD), **kw}


_RA_MEMBERS = (("personal-7", "personal"), ("dept-a", "org"), ("tf-x", "tf"), ("sys-1", "system"), ("old-ra", None))


def _ra_me(home, members=_RA_MEMBERS) -> dict:
    """RA /api/me 의 답 꼴 — 머리 없이 물은 것이라 workspace_slug 는 None 이다(RA 는 그 칸에 받은 X-Workspace-Slug 를 되돌린다)."""
    return {"user": {"id": 7, "email": "me@example.com"}, "workspace_slug": None, "role": None, "public_view": False, "home_workspace_slug": home,
            "memberships": [{"workspace_slug": s, "role": "user", "workspace_name": s, "workspace_kind": k} for s, k in members],
            "is_system_admin": False}


# ── 고르기(단위) ─────────────────────────────────────────────────────────────────────────────────────────
def test_같은_칸의_공유_카드만_깔고_나머지는_센다():
    rows = [_row(1, at=5), _row(2, rnd="pv1"), _row(3, rnd=None), _row(4, scope=("aff:CAEG", "plat:risk")),
            _row(5, owner="me@example.com", status="draft", scope=("user:me@example.com",)), _row(6, scope=("org",), at=9),
            _row(7, scope=("aff:OTHER",)), _row(8, status="draft", scope=("user:peer@example.com",)),
            _row(9, owner="me@example.com", status="waiting", scope=("user:me@example.com",))]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff")
    assert [r["id"] for r in got] == ["ins:web:c6:r:default", "ins:web:c1:r:default"], "최근 것부터 — 소속 · 조직 범위의 확인 카드"
    assert n == {"laid": 2, "other_round": 1, "unknown_round": 1, "no_round": 0, "out_of_scope": 1, "over": 0, "after_as_of": 0,
                 "already": 0}, \
        "플랫폼 범위(4)는 그 권한이 없어 보이지도 않는다 · 내 초안(5)만 범위 밖 · 다른 소속(7) · 남의 초안(8) · 기다림(9)은 세지 않는다"
    got, n = X.pick(rows, viewer=_v(groups=("feat:insights", "plat:risk")), round_code="dv1", audience="aff")
    assert len(got) == 2 and n["out_of_scope"] == 2, "플랫폼 권한이 있어 보여도 plat 이 붙은 카드는 깔지 않는다 — 산출물의 독자는 그 권한으로 걸러지지 않는다"
    odd = [_row(10, owner="me@example.com", status="draft", scope=("org",))]
    got, n = X.pick(odd, viewer=_v(), round_code="dv1", audience="aff")
    assert got == [] and n["out_of_scope"] == 1, "범위 토큰이 어떻든 확인 · 반박 상태가 아닌 카드는 깔지 않는다"


def test_이_대화의_앞_회차가_낳은_카드는_깔지도_세지도_않는다():
    """이어하기는 앞 회차의 결정문을 요약으로 이미 넘긴다 — 같은 대화의 카드를 '앞선 인사이트' 로 또 깔면 제 결론을 독립 근거처럼 되읽는다."""
    rows = [_row(1), _row(2, source_id="conv-now"), _row(3, source_id="conv-now", path="mcp-job"),
            _row(4, source_id="conv-now", path="mcp-workflow")]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", skip_source="conv-now")
    assert [r["id"] for r in got] == ["ins:web:c1:r:default", "ins:web:c3:r:default"] and n["laid"] == 2 and sum(n.values()) == 2, \
        "같은 대화가 낳은 웹 · 워크플로 카드를 뺀다(MCP 잡의 source_id 는 잡 id 라 대화 id 와 겹쳐도 다른 것이다 — 반대 검토 11-22 M4)"


def test_RA_작업_공간의_범위를_모르면_조직에_연_카드만_깐다():
    rows = [_row(1), _row(2, scope=("org",))]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="org")
    assert [r["id"] for r in got] == ["ins:web:c2:r:default"] and n["out_of_scope"] == 1
    got, _n = X.pick(rows, viewer=_v(aff=""), round_code="dv1", audience="aff")
    assert [r["id"] for r in got] == ["ins:web:c2:r:default"], "소속이 없는 사람에게는 조직에 연 카드뿐이다"


def test_이_심의의_차수를_모르면_아무것도_깔지_않고_수만_센다():
    got, n = X.pick([_row(1), _row(2, rnd=None), _row(3, rnd="pv1")], viewer=_v(), round_code=None, audience="aff")
    assert got == [] and n["no_round"] == 3 and n["laid"] == 0


def test_관리자의_범위_밖_읽기로는_깔지도_세지도_않는다():
    rows = [_row(1, scope=("aff:OTHER",)), _row(2, status="draft", scope=("user:peer@example.com",))]
    got, n = X.pick(rows, viewer=_v("boss@example.com", admin=True), round_code="dv1", audience="aff")
    assert got == [] and not any(n.values())


def test_상한을_넘는_카드는_수만_센다():
    rows = [_row(i, at=i) for i in range(X.LAY_MAX + 3)]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff")
    assert len(got) == X.LAY_MAX and n["over"] == 3 and got[0]["created_at"] == X.LAY_MAX + 2
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", room=0)
    assert got == [] and n["over"] == X.LAY_MAX + 3, "호출자 근거가 이미 상한이면 하나도 깔지 않는다"


@pytest.mark.parametrize("kw, want", [
    ({"save_report": 0, "append_to_report_id": None, "ra_kind": "system"}, "aff"),       # 보고서를 저장하지 않는다
    ({"save_report": None, "append_to_report_id": None, "ra_kind": "personal"}, "aff"),
    ({"save_report": 1, "append_to_report_id": None, "ra_kind": "org"}, "aff"),          # 부서 — 사용자 결정 11-22(L21-17 ③)
    ({"save_report": None, "append_to_report_id": None, "ra_kind": "tf"}, "org"),        # 부서를 가로지른 TF
    ({"save_report": None, "append_to_report_id": None, "ra_kind": "system"}, "org"),
    ({"save_report": None, "append_to_report_id": None, "ra_kind": "virtual"}, "org"),
    ({"save_report": None, "append_to_report_id": None, "ra_kind": ""}, "org"),          # 종류를 모른다
    ({"save_report": None, "append_to_report_id": None, "ra_kind": None}, "org"),        # RA 에 묻지 못했다
    ({"save_report": None, "append_to_report_id": 12, "ra_kind": "org"}, "org"),         # 있는 보고서에 덧붙인다 — 어느 공간인지 모른다
    ({"save_report": None, "append_to_report_id": 12, "ra_kind": "personal"}, "org"),
])
def test_산출물의_독자는_보고서가_저장될_작업_공간의_종류로_정한다(kw, want):
    assert X.output_audience(**kw) == want


_P, _D, _D2, _T, _S = ("personal-7", "personal"), ("dept-a", "org"), ("dept-b", "org"), ("tf-x", "tf"), ("sys-1", "system")


@pytest.mark.parametrize("home, members, chosen, sso, want", [
    # 등록한 토큰 — 고른 공간이 있으면 그 공간의 종류다(기본 공간은 보지 않는다)
    ("sys-1", (_P, _D, _T, _S), "dept-a", False, "org"),
    (None, (_P, _D, _T), "personal-7", False, "personal"),
    ("dept-a", (_P, _D, _T), "tf-x", False, "tf"),
    ("dept-a", (_P, _D, _S), "sys-1", False, "system"),
    ("dept-a", (_P, _D), "없는-공간", False, None),                       # 멤버십에 없는 공간
    ("dept-a", (_P, _D, ("old-ra", None)), "old-ra", False, None),        # 종류를 주지 않는 옛 RA
    ("dept-a", (("personal-7", None), _D), "personal-7", False, "personal"),   # 옛 RA 의 개인 공간은 이름으로
    # 고른 공간이 없다 — RA 가 고르는 기본 공간(홈 부서 → 첫 조직 멤버십 → 개인 공간)
    ("dept-a", (_P, _D, _T), "", False, "org"),
    ("personal-7", (_P, _D), "", False, "personal"),                       # 홈이 개인 공간인 계정
    ("tf-x", (_P, _D, _T), "", False, "tf"),
    ("dept-z", (_P, _D), "", False, None),                                 # 홈이 멤버십에 없다(윗부서 멤버십 · 없어진 부서) — 모른다
    (None, (_P,), "", False, "personal"),                                  # 부서 배정을 기다리는 사람
    (None, (), "", False, "personal"),
    (None, (_P, _D, _D2), "", False, "org"),                               # 어느 것이 첫째든 부서다
    (None, (_P, _D, _T), "", False, None),                                 # 부서와 TF 가 섞였다 — 어느 것이 첫째인지 모른다
    (None, (_P, ("v", "virtual"), _D), "", False, "org"),                  # 가상 공간은 RA 가 건너뛴다
    # 위임 박스 — 엔진 저장은 기본 공간으로, 포털이 직접 부르는 저장은 남아 있는 고른 공간으로 간다(둘 다 본다)
    ("dept-a", (_P, _D, _T), "", True, "org"),
    ("dept-a", (_P, _D, _T), "personal-7", True, "personal"),
    ("dept-a", (_P, _D, _T), "tf-x", True, "tf"),
    ("sys-1", (_P, _D, _S), "dept-a", True, "system"),
    (None, (_P, _D, _T), "dept-a", True, None),
])
def test_보고서가_갈_RA_작업_공간의_종류는_고른_공간과_RA_의_기본_공간에서_읽는다(home, members, chosen, sso, want):
    assert X.ra_workspace_kind(_ra_me(home, members), chosen, sso=sso) == want
    assert X.output_audience(save_report=None, append_to_report_id=None, ra_kind=want) == ("aff" if want in ("personal", "org") else "org")


def test_RA_의_답이_꼴이_아니면_작업_공간의_종류를_모른다():
    for me in (None, "글", [], {}, {"memberships": None}, {"memberships": "x"}, {"home_workspace_slug": "dept-a"}):
        assert X.ra_workspace_kind(me) is None and X.ra_workspace_kind(me, "dept-a") is None, me
    assert X.ra_workspace_kind({"memberships": [None, 3, {"workspace_kind": "org"}, {"workspace_slug": "dept-a", "workspace_kind": "org"}]},
                               "dept-a") == "org", "꼴이 아닌 줄은 건너뛴다"


def test_RA_기본_공간의_차례와_프로필의_꼴이_RA_의_것과_같다():
    """RA 가 부서 머리 없는 개인 토큰에 고르는 공간 — 홈 부서 → 첫 조직 멤버십(개인 · 가상 · 보관 제외) → 개인 공간. RA 가 차례를 바꾸면 이 셈도 바꾼다."""
    src = _ROOT.parent / "ReportArchive" / "backend" / "app" / "shared" / "auth.py"
    if not src.exists():
        pytest.skip(f"형제 리포 없음: {src}")
    body = src.read_text(encoding="utf-8").split("def _default_workspace_for_token", 1)[1].split("\ndef ", 1)[0]
    order = [body.index(w) for w in ("return user.home_workspace_slug", "Workspace.kind != WorkspaceKind.personal",
                                     "Workspace.kind != WorkspaceKind.virtual", 'return first_org or f"personal-{user.id}"')]
    assert order == sorted(order)
    me = (_ROOT.parent / "ReportArchive" / "backend" / "app" / "modules" / "users" / "routes.py").read_text(encoding="utf-8")
    assert "workspace_slug=active_slug" in me and "home_workspace_slug=user.home_workspace_slug" in me and "workspace_kind=(" in me, \
        "/api/me 는 받은 부서 머리만 workspace_slug 로 되돌리고 홈 부서 · 멤버십의 종류를 준다"


def test_범위가_빈_카드는_깔지_않는다():
    assert X.layable_scope([], _v(), "aff") is False and X.layable_scope(None, _v(), "org") is False
    assert X.layable_scope(["org"], _v(), "org") and X.layable_scope(["aff:CAEG", "org"], _v(), "aff")
    assert not X.layable_scope(["aff:CAEG"], _v(), "org") and not X.layable_scope(["aff:CAEG", "plat:risk"], _v(groups=("plat:risk",)), "aff")


def test_기준일이_있으면_그_날_뒤에_생기거나_고쳐진_카드는_깔지_않고_센다():
    cut = X.as_of_cutoff("2026-11-21")
    from datetime import datetime, timedelta, timezone
    kst = timezone(timedelta(hours=9))
    assert cut == int(datetime(2026, 11, 22, tzinfo=kst).timestamp()) - 1, "그 날의 끝(KST)"
    assert X.as_of_cutoff(None) is None and X.as_of_cutoff("") is None and X.as_of_cutoff("11월 21일") == 0, "못 읽는 값은 어느 카드도 그 앞이 아니다"
    rows = [_row(1, at=cut), _row(2, at=cut + 1), _row(3, at=cut - 10, claim_edited_at=cut + 5), _row(4, at=cut + 1, rnd="pv1")]
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", cutoff=cut)
    assert [r["id"] for r in got] == ["ins:web:c1:r:default"] and n["after_as_of"] == 3 and n["other_round"] == 0
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff", cutoff=0)
    assert got == [] and n["after_as_of"] == 4
    got, n = X.pick(rows, viewer=_v(), round_code="dv1", audience="aff")
    assert len(got) == 3 and n["after_as_of"] == 0, "기준일이 없으면 가르지 않는다"


def test_호출자가_이미_근거로_넣은_카드는_다시_깔지_않고_key_가_겹치지_않는다():
    ev = [{"key": "ins-1", "tool": "insight_get", "args": '{"id": "ins:web:c1:r:default"}', "result": "가"},
          {"key": "E7", "tool": "mcp__hwax__insight_get", "args": {"id": "ins:web:c2:r:default"}, "result": "나"},
          {"tool": "mcp__hwax__invoke_tool", "args": {"name": "insight_get", "arguments": {"id": "ins:web:c3:r:default"}}, "result": "다"},
          {"tool": "insight_find", "args": {"id": "ins:web:c4:r:default"}, "result": "찾기는 카드 하나가 아니다"},
          {"tool": "find_part", "args": {"id": "ins:web:c5:r:default"}, "result": "다른 도구"}, "글"]
    ids, keys = X.evidence_marks(ev)
    assert ids == {"ins:web:c1:r:default", "ins:web:c2:r:default", "ins:web:c3:r:default"} and keys == {"ins-1", "E7"}
    assert X.evidence_marks(None) == (set(), set())
    got, n = X.pick([_row(1), _row(2), _row(6)], viewer=_v(), round_code="dv1", audience="aff", skip_ids=ids)
    assert [r["id"] for r in got] == ["ins:web:c6:r:default"] and n["already"] == 2 and n["laid"] == 1


@pytest.mark.parametrize("viewer, pat, opts, want", [
    (_v(), "pat", {"subject": {"sp_task": f" {KEY} "}}, KEY),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "diagnosis", "started_by": "human"}, KEY),
    (_v(groups=("feat:deliberation",)), "pat", {"subject": {"sp_task": KEY}}, ""),          # 과제 인사이트 권한이 없다
    (_v(), "", {"subject": {"sp_task": KEY}}, ""),                                           # 사람 자격이 없다
    (_v(), None, {"subject": {"sp_task": KEY}}, ""),
    (_v(email=""), "pat", {"subject": {"sp_task": KEY}}, ""),
    (None, "pat", {"subject": {"sp_task": KEY}}, ""),
    (_v(), "pat", {"subject": {"text": "과제 없이 글만"}}, ""),
    (_v(), "pat", {"subject": {"sp_task": "  "}}, ""),
    (_v(), "pat", {}, ""),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "risk-review"}, ""),       # D-18
    (_v(), "pat", {"subject": {"sp_task": KEY}, "chair_template": "risk-review-sealed"}, ""),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "started_by": "app"}, ""),
    (_v(), "pat", {"subject": {"sp_task": KEY}, "sealed": 1}, ""),                           # 봉인 — 호출자가 준 자료만으로 돈다
    (_v(), "pat", {"subject": {"sp_task": KEY}, "sealed": 0, "as_of": "2026-11-21"}, KEY),   # 기준일은 대상이다(그 날 뒤의 카드만 뺀다)
])
def test_깔기의_대상은_과제를_단_일반_심의이고_권한과_사람_자격이_있을_때뿐이다(viewer, pat, opts, want):
    assert X.subject_key(viewer, pat, opts) == want


def test_근거_항목은_표지_출처_상태_판을_달고_도구_칸에_카드_id_를_싣는다():
    row = _row(1, owner="peer@example.com", at=1_795_000_000, status="disputed", claim_edited_by="peer@example.com",
               subject={"sp_task": KEY, "round": "dv1", "artifacts": [{"kind": "mcad", "id": "0" * 23, "rev": "aa11"},
                                                                       {"kind": "ecad", "id": "abcdef0123456789", "rev": "B"},
                                                                       {"kind": "cae", "id": "R1"}]})
    now = {"artifacts": [{"kind": "mcad", "id": "0" * 23, "rev": "bb22"}, {"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}
    it = X.evidence_item(row, 3, now_subject=now, stale={"say": "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다"}, dispute_notes=["응력 근거가 틀렸다"])
    assert it["tool"] == "insight_get" and json.loads(it["args"]) == {"id": row["id"]} and it["key"] == "ins-3"
    assert it["source"] == X.SOURCE == "앞선 인사이트 — 검증 대상, 독립 근거 아님"
    body = it["result"]
    assert body.startswith("[앞선 인사이트 — 검증 대상, 독립 근거 아님]\n출처: peer@example.com · ")
    for want in ("웹 심의", "단 default", "RA 보고서 #7", f"카드 {row['id']}", "상태: 반박 있음 · 주장은 사람이 고쳤다", "반박 메모: 응력 근거가 틀렸다",
                 "이 심의의 판(bb22)과 다르다", "이 심의와 같은 판", "이 심의의 주제에 없는 설계 자료", "낡았을 수 있다", "표결: 동의 2 · 조건부 0 · 반대 1",
                 "주장:\n리브를 보강한다"):
        assert want in body, want
    mark = {"tool": it["tool"], "args": it["args"], "ok": True}        # 엔진이 근거 표지에 적는 꼴(_insight_calls — ok 는 결과 글의 성패다)
    assert C.insight_sources({"card": {"calls": [mark]}}) == ([row["id"]], ""), "깐 항목이 낳는 근거 표지에서 읽은 카드 id 를 되찾는다"
    for bad in ({**mark, "ok": False}, {"tool": it["tool"], "args": it["args"]}, {**mark, "ok": 1}):
        assert C.insight_sources({"card": {"calls": [mark, bad]}})[0] is None, "실패했거나 성패를 모르는 표지는 그 카드를 읽었다는 증거가 아니다(L2)"


def test_근거_항목의_꼴과_상한은_엔진과_맞는다():
    eng = _AGENT / "deliberation.py"
    if not eng.exists():
        pytest.skip(f"형제 리포 없음: {eng}")
    src = eng.read_text(encoding="utf-8")
    assert re.search(rf'^_EVID_ITEMS = _env_int\("DELIB_EVID_ITEMS", {X.EVID_ITEMS}\)', src, re.M)
    assert R.DelibOpts.model_fields["evidence"].metadata[0].max_length == X.EVID_ITEMS
    assert re.search(rf"^_INSIGHT_CALLS_MAX = {C.CALLS_MAX}\b", src, re.M)
    assert f'_INSIGHT_TOOL_HEAD = "{C.INSIGHT_TOOL_HEAD}"' in src and X.TOOL.startswith(C.INSIGHT_TOOL_HEAD)
    m = re.search(r'^_INSIGHT_EV_TOOL_RE = re\.compile\(r"([^"]+)" \+ _INSIGHT_TOOL_HEAD, re\.I \| re\.A\)$', src, re.M)
    assert m and m.group(1) + C.INSIGHT_TOOL_HEAD == C._INSIGHT_NAME_RE.pattern, "리스크 심사의 받침과 같은 이름 규칙"
    assert C._INSIGHT_NAME_RE.flags & re.I and C._INSIGHT_NAME_RE.flags & re.A, "같은 깃발(같은 입력에 같은 답은 test_insight_workflows 가 맞댄다)"
    key_max = int(re.search(r"^_EVID_KEY_MAX = (\d+)$", src, re.M).group(1))
    assert len(f"ins-{X.LAY_MAX}") <= key_max and re.fullmatch(r"[A-Za-z0-9_.-]+", f"ins-{X.LAY_MAX}")
    args_max = int(re.search(r'^_EVID_ARGS_MAX = _env_int\("DELIB_EVID_ARGS_MAX", (\d+)\)', src, re.M).group(1))
    assert len(json.dumps({"id": "ins:web:" + "c" * 64 + ":" + "r" * 64 + ":" + "s" * 40})) <= args_max, "카드 id 가 인자 표기 상한에서 잘리지 않는다"


# ── 중계 — 실제 로그인 · 에이전트 서버 자리의 대역 ────────────────────────────────────────────────────────────
def _sse(frames) -> bytes:
    return "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames).encode()


class _Body(httpx.AsyncByteStream):
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    async def __aiter__(self):
        yield self.raw


@pytest.fixture()
def web(env, monkeypatch):  # noqa: F811
    """/agent/chat 를 세션으로 부르고 에이전트 서버로 간 요청 본문(바이트)과 브라우저가 받은 글을 본다. 주제 확인(에이전트 서버) · 게이트웨이 도구는
    대역이다 — 부른 것을 적는다. 기본은 '받은 주제를 그대로 확인' 이고 게이트웨이 도구는 없다(unknown tool)."""
    c, st, s = env
    sent, confirms, calls = [], [], []
    state = SimpleNamespace(confirm=lambda subj: {**CONFIRMED, "sp_task": subj["sp_task"], "round": C.norm_round(subj.get("round") or ""),
                                                  "round_by": "person" if C.norm_round(subj.get("round") or "") else None,
                                                  "artifacts": subj.get("artifacts") or []}, gateway={})

    def handler(req: httpx.Request) -> httpx.Response:
        sent.append(req.content)
        return httpx.Response(200, stream=_Body(_sse(FRAMES)), headers={"content-type": "text/event-stream"})

    async def fake_confirm(settings, *, subject, principal, pat, chair_template):
        confirms.append({"subject": subject, "email": principal.email, "pat": bool(pat), "chair": chair_template})
        rec = state.confirm(subject)
        return (rec, "") if rec is not None else (None, "주제를 다시 풀지 못했다")

    async def fake_mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, args))
        if tool not in state.gateway:
            raise AuthError(f"{tool}: unknown tool: {tool}", status_code=502)
        return state.gateway[tool](args)

    async def fake_ra_profile(settings, token):
        """RA /api/me 의 대역(RA modules/users/routes.py get_me 의 꼴) — 부서 머리 없이 물으므로 workspace_slug · role 은 비어 오고, 멤버십마다
        종류와 홈 부서가 온다. 실제 RA 를 부르지 않는다."""
        ra_asked.append(token)
        if state.ra is None:
            raise AuthError("Report Archive 에 연결하지 못했습니다(ConnectError).", status_code=502)
        return state.ra

    state.ra = _ra_me("dept-a")
    ra_asked: list = []
    from app.auth.routes import connections as conn_routes
    monkeypatch.setattr(conn_routes, "_ra_profile", fake_ra_profile)
    monkeypatch.setattr(I, "confirm_async", fake_confirm)
    monkeypatch.setattr(U, "mcp_call", fake_mcp)
    real = app.state.agent_client
    app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    def login(who: str) -> dict:
        from app.auth.routes.local import _rl
        _rl.clear()                      # 한 시험이 여러 번 갈아 로그인한다 — 로그인 횟수 제한은 이 시험이 보는 것이 아니다
        return _login(c, who)

    def go(who: str, body: dict) -> tuple[bytes, str]:
        r = c.post("/agent/chat", json=body, headers=login(who))
        assert r.status_code == 200, r.text
        return sent[-1], r.text

    def confirmed(who: str, cid: str, **kw) -> str:
        """그 사람의 확인한 카드 하나(소속 범위) — 웹 길로 들이고 화면의 확인을 누른다."""
        _relay(st, owner=who, cid=cid, **kw)
        iid = f"ins:web:{cid}:r1:default"
        assert c.post(f"/insights-api/cards/{iid}/confirm", headers=login(who)).status_code == 200
        return iid

    try:
        yield SimpleNamespace(c=c, st=st, s=s, go=go, login=login, confirmed=confirmed, sent=sent, confirms=confirms, calls=calls, state=state,
                              ra_asked=ra_asked)
    finally:
        app.state.agent_client = real


def _workspace(slug: str, email="me@example.com"):
    """그 사람의 RA 연결(등록한 토큰)과 고른 작업 공간 — 종류는 web 픽스처의 RA 대역이 답한다(personal-7 개인 · dept-a 부서 · tf-x · sys-1)."""
    app.state.user_store.set_connection(email=email, service="reportarchive", token="rat_test", workspace=slug)


def _personal(email="me@example.com"):
    _workspace("personal-7", email)


def _body(**opts):
    return {"message": MSG, "delib_opts": {"subject": dict(ASK), **opts}}


def _ev(payload: bytes) -> list:
    return (json.loads(payload).get("delib_opts") or {}).get("evidence") or []


def test_같은_과제_차수의_확인된_카드를_근거로_깔고_그_사람에게_알린다(web):
    a = web.confirmed("peer@example.com", "a")
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "round": "pv1"})
    web.confirmed("peer@example.com", "d", subject={**CONFIRMED, "round": None, "round_by": None})
    _relay(web.st, owner="me@example.com", cid="mine")              # 내 초안 — 같은 칸이지만 깔지 않는다
    _personal()
    mine = {"source": "StepForge", "tool": "find_part", "args": "{}", "result": "힌지 2종"}
    payload, text = web.go("me@example.com", _body(evidence=[mine]))
    ev = _ev(payload)
    assert ev[0] == mine and len(ev) == 2, "그 사람이 고른 근거가 앞이고 깐 것이 뒤다"
    assert ev[1]["tool"] == "insight_get" and json.loads(ev[1]["args"]) == {"id": a} and ev[1]["source"] == X.SOURCE
    assert "출처: peer@example.com" in ev[1]["result"] and "상태: 확인" in ev[1]["result"]
    assert json.loads(payload)["delib_opts"]["subject"] == ASK, "주제는 그대로 넘긴다(에이전트 서버가 다시 확인한다)"
    assert "앞선 인사이트 1건을 근거로 실었다" in text and "다른 차수 1건" in text and "차수 모름 1건" in text and "범위 밖 1건" in text
    assert "pv1" not in json.dumps(ev, ensure_ascii=False), "다른 차수의 카드는 근거에 없다"
    assert "다른 차수" not in json.dumps(ev, ensure_ascii=False), "수는 화면에만 알린다 — 근거(산출물)에 싣지 않는다"
    assert web.confirms == [{"subject": ASK, "email": "me@example.com", "pat": True, "chair": None}]
    with closing(sqlite3.connect(web.s.agent_audit_log_path)) as db:
        meta = json.loads(db.execute("SELECT meta FROM agent_audit WHERE event='insight_laid'").fetchall()[-1][0])
    assert meta["ids"] == [a] and meta["laid"] == 1 and meta["sp_task"] == KEY


def test_이어하는_심의에는_그_대화의_앞_카드를_깔지_않는다(web):
    web.login("me@example.com")
    conv = web.c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}, headers=web.login("me@example.com")).json()["id"]
    mine = web.confirmed("me@example.com", conv)            # 이 대화의 앞 회차가 낳은 카드(웹 길의 source_id 는 대화 id 다)
    other = web.confirmed("peer@example.com", "a")
    _personal()
    got, text = web.go("me@example.com", {**_body(), "conversation_id": conv})
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [other] and mine not in got.decode() and "1건을 근거로 실었다" in text
    got, _t = web.go("me@example.com", _body())             # 다른(새) 대화에서는 그 카드도 앞선 인사이트다
    assert sorted(json.loads(e["args"])["id"] for e in _ev(got)) == sorted([mine, other])


def test_부서_작업_공간은_소속_안으로_보고_TF_시스템_공간과_모르는_공간은_조직으로_친다(web):
    """사용자 결정 11-22(docs/leftovers-1121 L21-17 ③) — 보고서가 저장될 RA 작업 공간이 부서면 독자를 같은 소속으로 보고 소속 범위 카드도 깐다."""
    a = web.confirmed("peer@example.com", "a")                          # 소속 범위
    b = web.confirmed("peer@example.com", "b")
    assert web.c.post(f"/insights-api/cards/{b}/widen", json={"to": "org"}, headers=web.login("peer@example.com")).status_code == 200

    def laid(body=None) -> list:
        return sorted(json.loads(e["args"])["id"] for e in _ev(web.go("me@example.com", body or _body())[0]))
    assert laid() == [b], "RA 연결이 없다 — 어느 공간인지 모른다"
    for slug, want in (("dept-a", [a, b]), ("personal-7", [a, b]), ("tf-x", [b]), ("sys-1", [b]), ("old-ra", [b]), ("없는-공간", [b]), ("", [a, b])):
        _workspace(slug)
        assert laid() == sorted(want), slug        # "" 는 '지정 안 함' — RA 가 고르는 기본 공간(대역의 홈 부서 dept-a)이다
    assert web.ra_asked and set(web.ra_asked) == {"rat_test"}, "그 사람이 등록한 토큰으로 묻는다"
    web.state.ra = _ra_me("tf-x")                                       # 홈이 TF 인 계정 — 지정 안 함이면 거기로 간다
    assert laid() == [b]
    web.state.ra = _ra_me(None)                                         # 홈이 없고 부서와 TF 가 섞였다 — 첫 조직 멤버십이 어느 것인지 모른다
    assert laid() == [b]
    web.state.ra = _ra_me("dept-a")
    _workspace("tf-x")
    payload, text = web.go("me@example.com", _body())
    assert "범위 밖 1건" in text and "부서 · 개인 공간이 아니거나 알 수 없어" in text
    assert laid(_body(save_report=0)) == sorted([a, b]), "보고서를 저장하지 않으면 공간을 묻지 않고 소속 범위까지 깐다"
    n = len(web.ra_asked)
    assert laid(_body(save_report=0)) == sorted([a, b]) and len(web.ra_asked) == n, "저장하지 않으면 RA 에 묻지 않는다"
    # 있는 보고서에 덧붙이면 그 보고서가 어느 공간에 있는지 모른다 — 부서 공간이어도 조직에 연 것만
    _workspace("dept-a")
    assert laid(_body(append_to_report_id=12)) == [b] and len(web.ra_asked) == n
    web.state.ra = None                                                 # RA 에 닿지 못한다
    assert laid() == [b], "작업 공간의 종류를 알아내지 못하면 조직으로 친다"


def test_RA_위임_박스는_기본_부서를_소속_안으로_본다(web, monkeypatch):
    """RA_SSO_SECRET 이 있는 박스 — 게이트웨이가 그 사람 토큰을 위임으로 받고 부서 머리를 떼고 부른다. 엔진이 저장하는 보고서는 RA 가 고르는 기본
    공간(홈 부서 → 첫 조직 멤버십 → 개인 공간)으로 간다. 그것이 부서면 소속 범위 카드도 깐다. 연결에 저장된 공간이 남아 있으면 포털이 직접 부르는
    저장은 그리로 간다 — 그 공간까지 부서 · 개인일 때만이다."""
    a = web.confirmed("peer@example.com", "a")
    monkeypatch.setattr(web.s, "ra_sso_secret", "sso-secret")
    asked = []

    async def fake_sso(settings, *, email, name):
        asked.append(email)
        return "rat_from_sso"
    monkeypatch.setattr(R.ra_sso, "ra_user_token", fake_sso)

    def laid() -> list:
        return [json.loads(e["args"])["id"] for e in _ev(web.go("me@example.com", _body())[0])]
    assert laid() == [a], "등록한 연결이 없어도 위임 토큰으로 묻는다 — 홈 부서"
    assert asked == ["me@example.com"] and web.ra_asked[-1] == "rat_from_sso"
    _workspace("dept-a")
    assert laid() == [a]
    _workspace("tf-x")                                                  # 등록 토큰 시절에 고른 TF 가 남아 있다
    assert laid() == [], "포털이 직접 부르는 저장은 남아 있는 공간으로 간다 — 조직으로 친다"
    _workspace("")
    web.state.ra = _ra_me("sys-1")                                      # 기본 공간이 시스템 공간인 사람
    assert laid() == [], "기본 공간이 부서 · 개인이 아니면 조직으로 친다"
    web.state.ra = _ra_me(None, (("personal-7", "personal"),))          # 부서 배정을 기다리는 사람 — 개인 공간
    assert laid() == [a]


def _baseline(web, who: str, body: dict) -> bytes:
    """깔기를 통째로 뺀 중계가 보내는 요청 — '종전' 이다."""
    keep = R._insight_ctx
    R._insight_ctx = lambda *_a, **_k: None
    try:
        return web.go(who, body)[0]
    finally:
        R._insight_ctx = keep


def test_주제가_없거나_확인되지_않았으면_요청이_종전과_바이트까지_같다(web):
    web.confirmed("peer@example.com", "a")
    _personal()
    plain = {"message": MSG, "delib_opts": {"rounds": 3, "evidence": [{"source": "메모", "result": "글"}]}}
    for body in (plain, {"message": MSG}, {"message": "힌지 크랙이 뭐야", "delib_opts": {"subject": dict(ASK)}},
                 {"message": MSG, "delib_opts": {"subject": {"text": "과제 없이 글만"}}}):
        base = _baseline(web, "me@example.com", body)
        n = len(web.confirms)
        got, text = web.go("me@example.com", body)
        assert got == base, body
        assert len(web.confirms) == n and "앞선 인사이트" not in text, "주제가 없으면 확인도 부르지 않고 알림도 없다"
    # 주제를 줬지만 서버가 확인하지 못했다(주장) · 다른 key 로 확인됐다 · 확인 창구에 닿지 못했다
    for rec in (lambda s: {**CONFIRMED, "sp_state": "claimed", "sp_task": s["sp_task"]}, lambda s: {**CONFIRMED, "sp_task": "다른 과제"},
                lambda s: None):
        web.state.confirm = rec
        body = _body(rounds=3)
        got, text = web.go("me@example.com", body)
        assert got == _baseline(web, "me@example.com", body) and "근거로 실었다" not in text


def test_볼_수_있는_카드가_없으면_확인도_부르지_않고_요청이_같다(web):
    _relay(web.st, owner="peer@example.com", cid="a")                 # 남의 초안뿐 — 나에게는 없는 것과 같다
    _personal()
    got, text = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()) and web.confirms == [] and web.calls == [] and "앞선 인사이트" not in text
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "sp_task": "다른 과제"})
    got, _t = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()) and web.confirms == [], "다른 과제의 카드만 있으면 확인하지 않는다"


def test_같은_칸에_깔_것이_없어도_확인된_주제면_수만_알리고_요청은_같다(web):
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "round": "pv1"})
    _personal()
    got, text = web.go("me@example.com", _body())
    assert got == _baseline(web, "me@example.com", _body()), "깐 것이 없으면 근거 칸을 만들지 않는다"
    assert "앞선 인사이트를 근거로 싣지 않았다" in text and "다른 차수 1건" in text


@pytest.mark.parametrize("opts", [{"chair_template": "risk-review"}, {"chair_template": "risk-review-sealed"}, {"started_by": "app"}])
def test_리스크_심사_계열에는_깔지_않고_확인도_부르지_않는다(web, opts):
    web.confirmed("peer@example.com", "a")
    _personal()
    got, text = web.go("me@example.com", _body(**opts))
    assert got == _baseline(web, "me@example.com", _body(**opts)) and web.confirms == [] and web.calls == []
    assert "insight_get" not in got.decode() and "앞선 인사이트" not in text


def test_다른_소속_과제_인사이트_권한이_없는_사람에게는_깔리지_않는다(web):
    web.confirmed("peer@example.com", "a")
    grants = ["feat:chat", "feat:deliberation"]
    assert web.c.patch("/auth/access/users/out@example.com", json={"grants": grants}, headers=web.login("boss@example.com")).status_code == 200
    body = _body(save_report=0)
    got, text = web.go("out@example.com", body)
    assert got == _baseline(web, "out@example.com", body) and web.confirms == [], "과제 인사이트 권한이 없다"
    assert web.c.patch("/auth/access/users/out@example.com", json={"grants": [*grants, "feat:insights"]},
                       headers=web.login("boss@example.com")).status_code == 200
    got, text = web.go("out@example.com", body)
    assert got == _baseline(web, "out@example.com", body) and web.confirms == [] and "앞선 인사이트" not in text, \
        "권한이 있어도 다른(없는) 소속에게 CAEG 범위의 카드는 없는 것과 같다 — 수도 알리지 않는다"
    got, _t = web.go("boss@example.com", body)
    assert _ev(got) == [], "관리자도 제 소속 밖의 카드는 깔리지 않는다(범위 밖 읽기는 화면에서만 · 감사에 남는다)"


def test_깔기가_터지거나_늦어도_심의는_종전_요청_그대로_열린다(web, monkeypatch):
    web.confirmed("peer@example.com", "a")
    _personal()
    base = _baseline(web, "me@example.com", _body())

    async def boom(**_k):
        raise RuntimeError("원장이 잠겼다")
    monkeypatch.setattr(X, "lay", boom)
    got, text = web.go("me@example.com", _body())
    assert got == base and "결정문" in text

    async def slow(**_k):
        import asyncio
        try:
            await asyncio.sleep(5)
        finally:
            await asyncio.sleep(3)       # 취소된 게이트웨이 호출의 뒤처리(세션 닫기) — 호출 기한만큼 더 걸린다
    monkeypatch.setattr(X, "lay", slow)
    monkeypatch.setattr(X, "LAY_TIMEOUT_S", 0.05)
    web.login("me@example.com")
    import time
    t0 = time.monotonic()
    got, text = web.go("me@example.com", _body())
    took = time.monotonic() - t0
    assert got == base and "결정문" in text
    assert took < 2.5, f"상한은 늦은 호출의 뒤처리를 기다리지 않는다(반대 검토 11-22 L5) — {took:.1f}초"


def test_호출자_근거가_상한이면_깔지_않고_수만_알린다(web):
    web.confirmed("peer@example.com", "a")
    _personal()
    full = [{"source": f"E{i}", "result": "글"} for i in range(X.EVID_ITEMS)]
    got, text = web.go("me@example.com", _body(evidence=full))
    assert len(_ev(got)) == X.EVID_ITEMS and "상한 밖 1건" in text


def test_옛_key_로_남은_카드도_지금_과제의_같은_칸으로_깐다(web):
    old = web.confirmed("peer@example.com", "a", subject={**CONFIRMED, "sp_task": "알파 개발_C1"})
    web.confirmed("peer@example.com", "b", subject={**CONFIRMED, "sp_task": "재사용된 옛 이름"})
    _personal()
    web.state.gateway[L.STEPFORGE_OBJECT] = lambda a: {"node": a["focus"], "type": "plm_task", "key": KEY,
                                                       "keys": {"previous_keys": ["알파 개발_C1", "재사용된 옛 이름"], "merged_from": []}}
    # 풀이 — '재사용된 옛 이름' 은 지금 다른 산 과제의 key 다(글자 그대로 같은 활성 행 하나). '알파 개발_C1' 은 풀이에 없다.
    web.state.gateway[L._subject.RESOLVER_CALL] = lambda a: {"query": a["query"], "tasks": (
        [{"key": a["query"], "label": a["query"], "active": True}] if a["query"] == "재사용된 옛 이름" else [])}
    got, text = web.go("me@example.com", _body())
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [old] and "1건을 근거로 실었다" in text
    assert (L.STEPFORGE_OBJECT, {"focus": f"plm_task:{KEY}", "history": False}) in web.calls


# ── 반대 검토 11-22 의 고침 — 봉인 · 기준일 · 워크플로 대화 · 겹침 · 판 줄 · 반박 메모 ──────────────────────────────────
def test_봉인_심의에는_깔지_않고_기준일_심의에는_그_날_뒤의_카드를_뺀다(web, monkeypatch):
    """M2 — 봉인 심의는 호출자가 준 자료만으로 돈다(오늘의 원장을 깔지 않는다 · 확인도 부르지 않는다). 기준일 심의에는 그 날 뒤에 생기거나 고쳐진
    카드를 빼고 그 수를 알린다."""
    a = web.confirmed("peer@example.com", "a")
    _personal()
    body = _body(sealed=1)
    base = _baseline(web, "me@example.com", body)
    n = len(web.confirms)
    got, text = web.go("me@example.com", body)
    assert got == base and len(web.confirms) == n and web.calls == [] and "앞선 인사이트" not in text

    async def takes(*_a, **_k):
        return True
    monkeypatch.setattr(R, "_engine_takes_as_of", takes)
    body = _body(as_of="2020-01-01")
    got, text = web.go("me@example.com", body)
    assert got == _baseline(web, "me@example.com", body) and "기준일 뒤에 생기거나 고쳐진 1건" in text and "근거로 싣지 않았다" in text
    got, text = web.go("me@example.com", _body(as_of="2099-12-31"))
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [a] and "기준일" not in text


def test_워크플로_대화를_웹에서_이어가면_그_대화가_낳은_카드를_깔지_않는다(web, monkeypatch):
    """M4 — 워크플로 대화의 카드(ins:wf:<대화 id>)도 그 대화의 앞 회차다. 같은 대화를 웹에서 이어가면 깔지 않는다(다른 대화에서는 앞선 인사이트다)."""
    from test_insights import _principal
    monkeypatch.setattr(I, "confirm_sync", lambda settings, **kw: (dict(CONFIRMED), ""))
    web.login("me@example.com")
    pat = R._chat_user_pat(app.state.keystore, web.s, _principal("me@example.com"))
    web.c.cookies.clear()
    conv = web.c.post("/agent/conversations", json={"title": "심의 — 알파", "kind": "deliberation", "source": "mcp", "subject": {"sp_task": KEY},
                                                    "messages": [{"role": "user", "content": "q"}]},
                      headers={"Authorization": f"Bearer {pat}"}).json()
    wf = conv["insight"]["id"]
    assert wf == f"ins:wf:{conv['id']}" and web.st.get(wf)["path"] == "mcp-workflow" and web.st.get(wf)["source_id"] == conv["id"]
    assert web.c.post(f"/insights-api/cards/{wf}/confirm", headers=web.login("me@example.com")).status_code == 200
    other = web.confirmed("peer@example.com", "a")
    _personal()
    got, text = web.go("me@example.com", {**_body(), "conversation_id": conv["id"]})
    assert [json.loads(e["args"])["id"] for e in _ev(got)] == [other] and wf not in got.decode() and "1건을 근거로 실었다" in text
    got, _t = web.go("me@example.com", _body())
    assert sorted(json.loads(e["args"])["id"] for e in _ev(got)) == sorted([wf, other]), "다른(새) 대화에서는 그 카드도 앞선 인사이트다"


def test_사람이_이미_근거로_넣은_카드는_다시_깔지_않고_깐_항목의_key_는_겹치지_않는다(web):
    """L7 — '심의로 넘기기' 로 이미 근거에 든 카드(insight_get + 카드 id)는 또 깔지 않는다. 깐 항목의 key 는 호출자가 쓴 key 를 피한다."""
    a = web.confirmed("peer@example.com", "a")
    b = web.confirmed("peer@example.com", "b")
    _personal()
    mine = [{"key": "ins-1", "source": "앞 대화", "tool": "mcp__hwax__insight_get", "args": json.dumps({"id": a}), "result": "앞에서 읽은 카드"},
            {"key": "ins-2", "source": "메모", "result": "글"}]
    got, text = web.go("me@example.com", _body(evidence=mine))
    ev = _ev(got)
    assert ev[:2] == mine and [json.loads(e["args"])["id"] for e in ev[2:]] == [b], "이미 든 카드는 다시 싣지 않는다"
    assert [e["key"] for e in ev] == ["ins-1", "ins-2", "ins-3"] and "이미 근거에 든 1건" in text and "1건을 근거로 실었다" in text
    both = [*mine, {"tool": "invoke_tool", "args": {"name": "insight_get", "arguments": {"id": b}}, "result": "범용 실행기로 읽은 카드"}]
    got, text = web.go("me@example.com", _body(evidence=both))
    assert _ev(got) == both or [e.get("tool") for e in _ev(got)] == [x.get("tool") for x in both], "둘 다 이미 들었다 — 더 깔지 않는다"
    assert len(_ev(got)) == 3 and "이미 근거에 든 2건" in text and "근거로 싣지 않았다" in text


def test_깐_근거의_판_줄은_판정_낱말만_싣고_뒤_판의_이름과_id_는_싣지_않는다(web):
    """M1 — 뒤 판의 CAD 과제 id · 개정 이름은 읽는 사람의 StepForge 권한으로 읽은 것이다. 근거(산출물 · 다음 카드의 근거)로 퍼지는 자리에는 판정
    낱말만 싣는다. 낡음 셈이 빠지면(L8) 이 줄이 없다."""
    from test_insight_lineage import FP, NEW, OLD, SF, _meta
    a = web.confirmed("peer@example.com", "a", subject={**CONFIRMED, "artifacts": [{"kind": "mcad", "id": OLD, "rev": FP[OLD]}]})
    _personal()
    web.state.gateway[L.STEPFORGE_META] = _meta
    got, _t = web.go("me@example.com", _body())
    (item,) = _ev(got)
    assert json.loads(item["args"]) == {"id": a} and "낡았을 수 있다 — 기구 CAD: 뒤 판이 있다" in item["result"]
    nxt = SF["meta_old_with_next"]["revision"]["next"][0]
    sent = got.decode()
    assert nxt["project_id"] == NEW and NEW not in sent and f"뒤 판 {nxt['rev_label']}" not in sent and nxt["project_name"] not in sent
    assert (L.STEPFORGE_META, {"project_id": OLD}) in web.calls
    # 같은 표지를 화면(세션)의 그 사람은 자세히 본다 — 낱말만 내는 것은 퍼지는 자리뿐이다
    web.login("me@example.com")
    full = web.c.get(f"/insights-api/cards/{a}").json()["stale"]
    assert f"뒤 판 {nxt['rev_label']}" in full["say"] and full["items"][0]["next"][0]["project_id"] == NEW


def test_반박_메모는_반박_받은_카드의_근거에만_달린다(web):
    """L8 — 잇기의 끝(to_id)이 반박 받은 카드다. 반박한 카드(from_id)나 다른 종류의 잇기에는 메모를 달지 않는다."""
    a = web.confirmed("peer@example.com", "a")
    b = web.confirmed("peer@example.com", "b", cards=({**CARD, "claim": "리브를 두지 않는다"},))
    h = web.login("peer@example.com")
    assert web.c.post(f"/insights-api/cards/{a}/dispute", json={"by_card": b, "note": "응력 근거가 틀렸다"}, headers=h).status_code == 200
    web.st.link(a, b, kind="continues", by="peer@example.com", note="이어하기의 메모는 반박이 아니다")
    _personal()
    got, _t = web.go("me@example.com", _body())
    body = {json.loads(e["args"])["id"]: e["result"] for e in _ev(got)}
    assert set(body) == {a, b}
    assert "반박 메모: 응력 근거가 틀렸다" in body[a] and "상태: 반박 있음" in body[a]
    assert "반박 메모" not in body[b] and "이어하기의 메모" not in got.decode()


def test_확인이_읽었다는_카드가_내게_안_보이면_까닭을_가르지_않고_주인만_본다(web):
    """L2 — 근거 표지의 카드 id 는 호출자가 적는다. 내게 없는 카드(없는 id · 남의 초안 · 다른 소속 · 내게 없는 플랫폼 권한이 붙은 것)의 범위를 읽어
    내 카드에 찍으면 그 카드가 있는지 · 범위가 무엇인지가 드러난다. 어느 경우든 같은 글로 주인만 본다."""
    c, st = web.c, web.st
    _relay(st, owner="peer@example.com", cid="dr")                                           # 남의 초안
    far = web.confirmed("peer@example.com", "far")
    assert st.update(far, scope=["aff:OTHER", "plat:secret"])                                # 다른 소속 · 내게 없는 권한
    solo = web.confirmed("out@example.com", "solo")                                          # 확인했지만 그 사람만(소속 없음)
    gone = web.confirmed("peer@example.com", "gone")
    assert c.post(f"/insights-api/cards/{gone}/withdraw", headers=web.login("peer@example.com")).status_code == 200
    seen = {}
    for i, src in enumerate(("ins:web:dr:r1:default", far, solo, gone, "ins:web:nothing-here:r1:default")):
        _relay(st, owner="me@example.com", cid=f"n{i}", cards=({**_derived([src])},))
        r = c.post(f"/insights-api/cards/ins:web:n{i}:r1:default/confirm", headers=web.login("me@example.com")).json()
        assert r["status"] == "confirmed" and r["scope"] == ["user:me@example.com"], src
        seen[src] = r["scope_note"]
    assert len(set(seen.values())) == 1 and "이어받지 못해 주인만 본다" in next(iter(seen.values())), seen
    assert not any(w in json.dumps(seen, ensure_ascii=False) for w in ("OTHER", "plat:secret", "거둠", "초안", "소속")), "까닭을 가르지 않는다"
    # 보이는 카드와 섞여도 같다 — 안 보이는 것이 하나라도 있으면 보이는 것의 범위도 찍지 않는다
    ok = web.confirmed("peer@example.com", "ok")
    _relay(st, owner="me@example.com", cid="mix", cards=({**_derived([ok, far])},))
    r = c.post("/insights-api/cards/ins:web:mix:r1:default/confirm", headers=web.login("me@example.com")).json()
    assert r["scope"] == ["user:me@example.com"] and r["scope_note"] == next(iter(seen.values()))
    # 관리자의 범위 밖 읽기로도 이어받지 않는다
    _relay(st, owner="boss@example.com", cid="adm", cards=({**_derived([far])},))
    assert c.patch("/auth/access/users/boss@example.com", json={"affiliation": "CAEG"}, headers=web.login("boss@example.com")).status_code == 200
    r = c.post("/insights-api/cards/ins:web:adm:r1:default/confirm", headers=web.login("boss@example.com")).json()
    assert r["scope"] == ["user:boss@example.com"] and "plat:secret" not in json.dumps(r, ensure_ascii=False)


# ── 범위 이어받기 — 앞선 인사이트를 근거로 쓴 카드의 확인 ─────────────────────────────────────────────────────────
def _derived(ids, *, tool="insight_get", extra_calls=(), args=None):
    calls = [{"ref": f"call:{i:016x}", "tool": tool, "app": "_gateway", "args": args or json.dumps({"id": x}), "sha256": "0" * 64, "ok": True}
             for i, x in enumerate(ids)]
    return {**CARD, "calls": [*calls, *extra_calls], "tools": sorted({tool, *(c["tool"] for c in extra_calls)}), "apps": ["_gateway"]}


def test_읽은_카드를_다_알_때만_id_를_낸다():
    assert C.insight_sources({"card": _derived(["ins:web:a:r1:default", "ins:delib:j:default"])})[0] == ["ins:web:a:r1:default", "ins:delib:j:default"]
    assert C.insight_sources({"card": _derived(["ins:wf:z"], tool="mcp__hwax__insight_get", args="{'id': 'ins:wf:z'}")})[0] == ["ins:wf:z"], \
        "엔진이 사전 인자를 글로 옮긴 꼴도 읽는다"
    for card in (_derived(["x"], tool="insight_find", args='{"sp_task": "알파"}'), _derived(["x"], args='{"id": "남의 글"}'),
                 _derived(["x"], tool="insight_find", args='{"id": "ins:web:a:r1:default"}'),     # 찾기 도구에 id 를 적어도 카드 하나가 아니다
                 _derived(["x"], args='{"id": "ins:web:a:r1:default", "also": 1}'), {**CARD, "tools": ["insight_get"], "calls": []},
                 _derived(["ins:wf:z"], extra_calls=[{"tool": "find_part", "args": "{}"}] * (C.CALLS_MAX - 1))):
        ids, why = C.insight_sources({"card": card})
        assert ids is None and why, card["tools"]
    assert C.insight_derived({"card": {"tools": ["mcp__hwax__insight_find"]}}) and not C.insight_derived({"card": {"tools": ["getinsight_x"]}})
    assert C.insight_derived({"card": {"tools": ["get_insight_x"]}}), "낱말 경계 — 앞이 영숫자가 아니면 인사이트 도구로 본다(닫힌 쪽)"


def test_이름만_있는_인사이트_도구가_섞이면_읽은_카드를_다_안다고_하지_않는다():
    """반대 검토 11-22 L1 — 근거 표지(calls)는 카드 하나를 읽은 것뿐인데 도구 이름(tools)에 표지 없는 인사이트 도구가 더 있으면(같은 심의의 앞 단이
    찾기 결과를 넘겼다) 그 도구가 무엇을 읽었는지 모른다. 계약 §10.3 — 이름만 있으면 모른다(주인만)."""
    one = _derived(["ins:web:a:r1:default"])
    assert C.insight_sources({"card": one})[0] == ["ins:web:a:r1:default"]
    for more in (["insight_find"], ["mcp__hwax__insight_find"], ["mcp__hwax__insight_get"], ["hwax-insight_get"]):
        ids, why = C.insight_sources({"card": {**one, "tools": [*one["tools"], *more]}})
        assert ids is None and "도구 이름만" in why, more
    assert C.insight_sources({"card": {**one, "tools": [*one["tools"], "find_part", "risk_get_diff"]}})[0] == ["ins:web:a:r1:default"], \
        "인사이트 도구가 아닌 이름은 따지지 않는다"
    assert C.insight_sources({"card": {**one, "tools": []}})[0] == ["ins:web:a:r1:default"], "도구 이름 칸이 비면 표지만 본다"


def test_범용_실행기로_부른_표지는_앞선_인사이트를_쓴_것으로_치되_읽은_카드는_모른다():
    """반대 검토 11-22 M3 — invoke_tool 껍데기에 든 insight_get 도 앞선 인사이트를 근거로 쓴 것이다(확인이 주인만으로 닫힌다). 엔진은 껍데기를 벗겨
    안쪽 이름 · 인자로 표지를 적으므로(deliberation._ev_unwrap) 껍데기째 남은 표지는 풀지 못한 것이다 — 읽은 카드를 안다고 하지 않는다."""
    wrapped = {**CARD, "tools": ["mcp__hwax__invoke_tool"], "apps": ["_gateway"],
               "calls": [{"ref": "call:1", "tool": "mcp__hwax__invoke_tool", "ok": True, "sha256": "0" * 64,
                          "args": '{"name": "insight_get", "arguments": {"id": "ins:web:a:r1:default"}}'}]}
    assert C.insight_derived({"card": wrapped}) and C.insight_sources({"card": wrapped})[0] is None
    other = {**wrapped, "calls": [{**wrapped["calls"][0], "args": '{"name": "find_part", "arguments": {"q": "insight_get"}}'}]}
    assert not C.insight_derived({"card": other}), "껍데기 안의 도구가 인사이트가 아니면 아니다"


@pytest.mark.parametrize("base, sources, want", [
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["aff:CAEG"]}], ["aff:CAEG"]),
    (["aff:CAEG", "plat:stepforge"], [{"status": "disputed", "scope": ["org", "plat:risk"]}], ["aff:CAEG", "plat:risk", "plat:stepforge"]),
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["org"]}, {"status": "confirmed", "scope": ["aff:CAEG"]}], ["aff:CAEG"]),
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["aff:OTHER"]}], None),          # 서로 다른 소속 — 함께 볼 사람이 없다
    (["aff:CAEG"], [{"status": "confirmed", "scope": ["user:peer@example.com"]}], None),
    (["aff:CAEG"], [{"status": "draft", "scope": ["user:peer@example.com"]}], None),   # 아직 주인만 보는 카드
    (["aff:CAEG"], [{"status": "withdrawn", "scope": []}], None),
    (["aff:CAEG"], [{"status": "draft", "scope": ["aff:CAEG"]}], None),                # 범위 토큰이 어떻든 공유 상태가 아니면 이어받지 않는다
    (["aff:CAEG"], [None], None),                                                       # 원장에 없는 id
    (["aff:CAEG"], [{"status": "confirmed", "scope": []}], None),
    (["user:me@example.com"], [{"status": "confirmed", "scope": ["org"]}], None),       # 제 범위부터 주인만(소속 없음)
])
def test_확인_범위는_읽은_카드들의_범위를_다_담고_못_담으면_주인만이다(base, sources, want):
    scope, why = C.inherit_scope(base, sources, "me@example.com")
    assert scope == (want or ["user:me@example.com"])
    assert bool(why) == (want is None and base != ["user:me@example.com"])


def test_앞선_인사이트를_근거로_쓴_카드는_확인하면_읽은_카드의_범위를_이어받는다(web):
    c, st = web.c, web.st
    a = web.confirmed("peer@example.com", "a")                                         # [aff:CAEG]
    _relay(st, owner="me@example.com", cid="n1", cards=({**_derived([a])},))
    h = web.login("me@example.com")
    r = c.post("/insights-api/cards/ins:web:n1:r1:default/confirm", headers=h).json()
    assert r["status"] == "confirmed" and r["scope"] == ["aff:CAEG"] and not r["scope_note"], r
    # 읽은 카드가 플랫폼 범위면 그 권한까지 담는다(MCP 호출자가 넘긴 경우)
    _relay(st, owner="peer@example.com", cid="p", cards=({**CARD, "tools": ["risk_get_diff"], "apps": ["heax-hwax_risk"]},))
    assert c.post("/insights-api/cards/ins:web:p:r1:default/confirm", headers=web.login("peer@example.com")).json()["scope"] == \
        ["aff:CAEG", "plat:risk"]
    _relay(st, owner="me@example.com", cid="n2", cards=({**_derived([a, "ins:web:p:r1:default"])},))
    r = c.post("/insights-api/cards/ins:web:n2:r1:default/confirm", headers=web.login("me@example.com")).json()
    assert r["scope"] == ["aff:CAEG", "plat:risk"], "읽은 카드의 플랫폼 권한을 이어받는다 — 그 권한 없는 같은 소속에 열리지 않는다"
    # 읽은 카드를 모르거나(찾기 묶음) · 거뒀거나 · 초안이면 주인만
    _relay(st, owner="me@example.com", cid="n3", cards=({**_derived(["x"], tool="insight_find", args='{"sp_task": "알파"}')},))
    _relay(st, owner="peer@example.com", cid="dr")
    _relay(st, owner="me@example.com", cid="n4", cards=({**_derived(["ins:web:dr:r1:default"])},))
    _relay(st, owner="me@example.com", cid="n5", cards=({**_derived(["ins:web:gone:r1:default"])},))
    for cid in ("n3", "n4", "n5"):
        r = c.post(f"/insights-api/cards/ins:web:{cid}:r1:default/confirm", headers=web.login("me@example.com")).json()
        assert r["status"] == "confirmed" and r["scope"] == ["user:me@example.com"] and r["scope_note"], cid
    web.login("peer@example.com")
    assert c.get("/insights-api/cards/ins:web:n1:r1:default").status_code == 200
    assert c.get("/insights-api/cards/ins:web:n3:r1:default").status_code == 404
    assert c.post("/insights-api/cards/ins:web:n1:r1:default/widen", json={"to": "org"}, headers=web.login("me@example.com")).status_code == 409, \
        "앞선 인사이트에 기댄 카드는 조직에 열지 않는다(근거 범위를 다 알지 못한다)"
