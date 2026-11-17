# 머리줄 알림 화면의 순수 함수 · 창구 경로 — 링크 거르기가 서버와 같고, 화면이 부르는 경로가 포털에 있다(docs/request-1117 contracts §7)
"""화면 코드를 CommonJS 로 옮겨 node 로 돌린다(test_front_window_payload 와 같은 길 — 도구가 없으면 같이 건너뛴다)."""
import re
from pathlib import Path

import pytest
from tests.test_front_window_payload import _node, pytestmark  # noqa: F401

from app.main import app
from app.notices.store import safe_link

_API = ["api/notices.api.ts"]
_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
LINKS = ["/deliberate", "/deliberate?x=1#y", " /a ", "https://evil.example/x", "//evil.example", "/\\evil", "javascript:alert(1)",
         "deliberate", "/a\nb", "/a\tb", "", None, 7]


def test_화면의_링크_거르기는_서버와_같다():
    got = _node(_API, "const m = require('./api/notices.api.js'); out(input.map(m.safeNoticeLink));", LINKS)
    assert got == [safe_link(v) for v in LINKS]


@pytest.mark.parametrize(("n", "label"), [(0, ""), (-1, ""), (1, "1"), (99, "99"), (100, "99+")])
def test_안_읽은_수_표지(n, label):
    assert _node(_API, "const m = require('./api/notices.api.js'); out(m.unreadLabel(input));", n) == label


def test_화면이_부르는_경로가_포털에_있다():
    src = (_SRC / "api" / "notices.api.ts").read_text(encoding="utf-8")
    called = {re.sub(r"\$\{[^}]+\}", "{nid}", p).split("?")[0] for p in re.findall(r"apiFetch\(\s*[`'](/[^`'?]+[^`']*)[`']", src)}
    routes = {(getattr(r, "path", ""), m) for r in app.routes for m in (getattr(r, "methods", None) or ())}
    assert called == {"/notices-api", "/notices-api/{nid}/read", "/notices-api/read-all"}
    assert ("/notices-api", "GET") in routes and ("/notices-api/{nid}/read", "POST") in routes and ("/notices-api/read-all", "POST") in routes


def test_머리줄에_알림_표지가_선다():
    header = (_SRC / "components" / "layout" / "AppHeader.tsx").read_text(encoding="utf-8")
    assert "<NoticeBell />" in header and header.index("<NoticeBell />") < header.index('className="hdr-account"')
