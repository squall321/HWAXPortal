# 업데이트 이력 — 파싱·정렬·'안 본 것만' 고르기, 손상 파일에서 안 죽는지
import datetime as dt

import yaml

from app import changelog
from app.config import Settings


_RAW = {
    "entries": [
        {"date": dt.date(2026, 9, 7), "title": "먼저", "tag": "챗", "items": ["가", " "]},
        {"date": dt.date(2026, 9, 9), "title": "나중", "items": []},
        {"date": dt.date(2026, 9, 9), "title": "같은 날 두 번째"},
    ]
}


# ── 파싱 ─────────────────────────────────────────────────────────────────────
def test_parse_sorts_newest_first_and_keeps_file_order_within_a_day():
    out = changelog.parse_entries(_RAW)
    assert [e["title"] for e in out] == ["나중", "같은 날 두 번째", "먼저"]


def test_parse_normalises_yaml_date_to_iso():
    assert changelog.parse_entries(_RAW)[0]["date"] == "2026-09-09"


def test_parse_drops_blank_items_but_keeps_the_entry():
    first = [e for e in changelog.parse_entries(_RAW) if e["title"] == "먼저"][0]
    assert first["items"] == ["가"]      # 공백만 있던 항목은 빠진다
    assert first["tag"] == "챗"


def test_parse_skips_entries_without_date_or_title():
    raw = {"entries": [{"title": "날짜 없음"}, {"date": "2026-01-01"}, "문자열", None]}
    assert changelog.parse_entries(raw) == []


def test_parse_tolerates_garbage_top_level():
    assert changelog.parse_entries(None) == []
    assert changelog.parse_entries(["목록이 왔다"]) == []
    assert changelog.parse_entries({"다른키": 1}) == []


# ── 고르기 ───────────────────────────────────────────────────────────────────
def test_select_returns_only_entries_after_since():
    out, total = changelog.select(changelog.parse_entries(_RAW), "2026-09-07", 10)
    assert [e["title"] for e in out] == ["나중", "같은 날 두 번째"]   # 07일 것은 이미 봤다
    assert total == 2


def test_select_without_since_caps_at_limit():
    out, total = changelog.select(changelog.parse_entries(_RAW), None, 2)
    assert len(out) == 2            # 처음 로그인한 사람에게 이력을 통째로 쏟지 않는다
    assert total == 3               # 총수는 자르기 **전** 기준이라 '더 보기'가 맞는다


def test_select_returns_nothing_when_already_current():
    assert changelog.select(changelog.parse_entries(_RAW), "2026-09-09", 10) == ([], 0)


# ── 이력 페이지(페이징·분류) ──────────────────────────────────────────────────
def test_select_pages_with_offset():
    entries = changelog.parse_entries(_RAW)
    first, total = changelog.select(entries, None, 2, 0)
    second, total2 = changelog.select(entries, None, 2, 2)
    assert [e["title"] for e in first] == ["나중", "같은 날 두 번째"]
    assert [e["title"] for e in second] == ["먼저"]
    assert total == total2 == 3     # 총수는 페이지마다 흔들리지 않는다


def test_select_offset_past_the_end_is_empty_not_an_error():
    out, total = changelog.select(changelog.parse_entries(_RAW), None, 5, 99)
    assert out == [] and total == 3


def test_select_filters_by_tag_and_counts_the_filtered_set():
    out, total = changelog.select(changelog.parse_entries(_RAW), None, 10, 0, "챗")
    assert [e["title"] for e in out] == ["먼저"]
    assert total == 1               # 분류를 건 총수라 '더 보기' 판정이 맞는다


def test_select_unknown_tag_is_empty():
    assert changelog.select(changelog.parse_entries(_RAW), None, 10, 0, "없는분류") == ([], 0)


# ── 파일 로드 ─────────────────────────────────────────────────────────────────
def test_load_missing_file_is_empty_not_an_error(tmp_path):
    changelog._cache["mtime"] = None
    assert changelog.load_entries(tmp_path / "없다.yaml") == []


def test_load_broken_yaml_is_empty_not_an_error(tmp_path):
    p = tmp_path / "changelog.yaml"
    p.write_text("entries: [\n  - 닫히지 않음", encoding="utf-8")
    changelog._cache["mtime"] = None
    assert changelog.load_entries(p) == []


def test_load_rereads_after_the_file_changes(tmp_path):
    p = tmp_path / "changelog.yaml"
    p.write_text(yaml.safe_dump({"entries": [{"date": "2026-09-01", "title": "처음"}]}), encoding="utf-8")
    changelog._cache["mtime"] = None
    assert [e["title"] for e in changelog.load_entries(p)] == ["처음"]
    # mtime 이 바뀌면 재기동 없이 반영된다 — 운영자가 항목을 적는 즉시 보여야 한다.
    p.write_text(yaml.safe_dump({"entries": [{"date": "2026-09-02", "title": "고침"}]}), encoding="utf-8")
    import os
    os.utime(p, (0, 0))
    assert [e["title"] for e in changelog.load_entries(p)] == ["고침"]


# ── 실제로 배포되는 파일 ───────────────────────────────────────────────────────
def test_shipped_changelog_parses_and_has_entries():
    """config/changelog.yaml 이 깨지면 팝업이 조용히 안 뜬다 — 여기서 잡는다."""
    changelog._cache["mtime"] = None
    entries = changelog.load_entries(__import__("pathlib").Path(Settings().resolve("config/changelog.yaml")))
    assert entries, "배포되는 changelog.yaml 이 비었거나 파싱되지 않는다"
    assert all(e["date"] and e["title"] for e in entries)


# ── 라우트 ───────────────────────────────────────────────────────────────────
def test_route_requires_login_and_filters_by_since(tmp_path):
    """비로그인은 401, 로그인하면 since 이후만. latest 는 **전체**의 최신이다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.config import get_settings
    from app.deps import get_current_principal
    from app.main import app

    p = tmp_path / "changelog.yaml"
    p.write_text(
        yaml.safe_dump({"entries": [
            {"date": "2026-09-01", "title": "옛것"},
            {"date": "2026-09-09", "title": "새것"},
        ]}, allow_unicode=True),
        encoding="utf-8",
    )
    s = Settings(changelog_path=str(p))
    app.dependency_overrides[get_settings] = lambda: s
    changelog._cache["mtime"] = None
    try:
        with TestClient(app) as c:
            assert c.get("/changelog").status_code == 401     # 세션 쿠키 없음
            app.dependency_overrides[get_current_principal] = lambda: Principal(
                subject="u1", email="u1@hwax.local", display_name="U", groups=[]
            )
            body = c.get("/changelog", params={"since": "2026-09-01"}).json()
            assert [e["title"] for e in body["entries"]] == ["새것"]
            assert body["latest"] == "2026-09-09"
            # 다 본 사람에게는 아무것도 안 준다 — 팝업이 안 뜬다.
            assert c.get("/changelog", params={"since": "2026-09-09"}).json()["entries"] == []
            # 이력 페이지 — since 없이 넘겨 본다.
            page1 = c.get("/changelog", params={"limit": 1, "offset": 0}).json()
            assert [e["title"] for e in page1["entries"]] == ["새것"]
            assert page1["total"] == 2 and page1["has_more"] is True
            page2 = c.get("/changelog", params={"limit": 1, "offset": 1}).json()
            assert [e["title"] for e in page2["entries"]] == ["옛것"]
            assert page2["has_more"] is False
            # latest 는 **전체**의 최신이다 — 분류를 걸어 봐도 흔들리면 안 된다.
            assert c.get("/changelog", params={"tag": "없음"}).json()["latest"] == "2026-09-09"
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_principal, None)
        changelog._cache["mtime"] = None
