# 이용 통계 M2 — 날마다 접는 표(usage_daily · usage_actor_daily)와 접기 작업: 언제 접고 닫는가 · 원천마다 무엇을 접는가 · 실패가 무엇을 막지 않는가(docs/ops-dashboard)
#
# 계정은 example.com 시험 신원만, 주소는 문서용 예약 대역(TEST-NET)만 쓴다. 원장 · 정문 로그는 모두 임시 폴더에 만들고, 게이트웨이 · 에이전트 서버는
# HTTP 대역(httpx.MockTransport)이다 — 떠 있는 서비스를 부르지 않는다. 창구의 답은 형제 리포의 실제 셈 모듈로 지어 계약이 어긋나면 붉어진다.
import asyncio
import gc
import gzip
import importlib.util
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from tests.test_usage_stats import Box, _kst

from app import usage_fold, usage_stats
from app.usage_stats import KST

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 11, 20)
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=KST).timestamp()
APP = SimpleNamespace(state=SimpleNamespace(catalog=SimpleNamespace(all=lambda: [SimpleNamespace(id="heax-hub"), SimpleNamespace(id="spdm")])))
TOKEN = "s3cr3t-shared-token"


def _sibling(repo: str, name: str):
    """형제 리포의 창구 셈 모듈(표준 라이브러리만 읽는다) — 없으면(그 리포가 이 판보다 낡았다) 그 시험만 건너뛴다."""
    path = ROOT.parent / repo / "usage_rollup.py"
    if not path.exists():
        pytest.skip(f"형제 리포 {repo} 에 usage_rollup.py 가 없다")
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # 형제 리포에 __pycache__ 를 남기지 않는다
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = keep
    return mod


def _box(tmp_path, **kw) -> Box:
    base = {"mcp_gateway_url": "http://gateway.test", "agent_server_url": "http://agent.test", "gateway_shared_token": TOKEN,
            "nginx_access_log_path": str(tmp_path / "nginx" / "nginx-access.log"), "usage_fold_s": 0}
    return Box(tmp_path, **{**base, **kw})


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


def _fold(box: Box, now: float = NOW, handler=_down) -> dict:
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            return await usage_fold.run_once(APP, box.s, now=now, client=cli)
    return asyncio.run(go())


def _q(box: Box, sql: str, args=()) -> list:
    with closing(sqlite3.connect(box.paths["audit"])) as c:
        return c.execute(sql, args).fetchall()


def _daily(box: Box, source: str, metric: str | None = None) -> dict:
    """{(날, 지표, 칸 글자): 값}."""
    rows = _q(box, "SELECT day, metric, dims, value FROM usage_daily WHERE source = ?", (source,))
    return {(d, m, x): v for d, m, x, v in rows if metric is None or m == metric}


def _actors(box: Box, like: str = "%") -> list:
    return _q(box, "SELECT day, email, source, n, affiliation FROM usage_actor_daily WHERE source LIKE ? ORDER BY day, email, source", (like,))


def _folds(box: Box, source: str) -> dict:
    return {d: (fin, ex, note) for d, fin, ex, note in _q(box, "SELECT day, final, ex, note FROM usage_fold WHERE source = ?", (source,))}


def _at(day: date, h=12, mi=0) -> float:
    return datetime(day.year, day.month, day.day, h, mi, tzinfo=KST).timestamp()


def _conv(box: Box, cid: str, who: str, ts: int, kind="chat", source="web") -> None:
    box.sql("conv", "INSERT INTO conversations (id, owner_sub, title, kind, source, created_at, updated_at) VALUES (?, ?, 't', ?, ?, ?, ?)",
            [(cid, who, kind, source, ts, ts)])


# ── 표 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_접는_표는_감사_원장_파일_안에_생기고_새_파일을_만들지_않는다(tmp_path):
    box = _box(tmp_path)
    gc.collect()                                        # 원장을 만든 저장소 객체의 연결을 닫는다 — 전체 회귀에서 벌어지는 차례를 여기서도 만든다
    before = {p.name for p in tmp_path.iterdir()}
    _fold(box)
    names = {r[0] for r in _q(box, "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"usage_daily", "usage_actor_daily", "usage_fold", "agent_audit", "access_log"} <= names
    grown = {p.name for p in tmp_path.iterdir()} - before
    # sqlite 의 곁 파일(-wal · -shm · -journal)은 새 저장소가 아니다 — 대화 원장은 WAL 이라, 쥐고 있던 연결이 닫힌 뒤 읽기 전용으로 열면 곁 파일이 다시
    # 생긴다(M1 의 읽기도 같다 · 떠 있는 포털은 그 연결을 늘 쥐고 있다). 전체 회귀에서만 붉던 까닭이다(11-21 — 연결이 닫히는 때가 달라진다).
    new = {n for n in grown if not n.startswith("audit.sqlite") and not n.endswith(("-wal", "-shm", "-journal"))}
    assert not new, f"감사 원장 밖에 새 파일이 생겼다 — {new}"


def test_사람_줄_표에는_이메일_날_갈래_수_소속만_있다(tmp_path):
    box = _box(tmp_path)
    _fold(box)
    assert [r[1] for r in _q(box, "PRAGMA table_info(usage_actor_daily)")] == ["day", "email", "source", "n", "affiliation"]
    assert [r[1] for r in _q(box, "PRAGMA table_info(usage_daily)")] == ["day", "source", "metric", "dims", "value"]


# ── 언제 접나 ──────────────────────────────────────────────────────────────────────────────────────────────
def test_다시_접을_날은_오늘과_닫히지_않은_날과_빈_날이다():
    fp = "abc"
    start = usage_fold._midnight(TODAY)
    done = {"2026-11-16": (start - 90000, 1, fp, ""),         # 닫혔다
            "2026-11-17": (start - 100, 1, "old", ""),        # 닫혔지만 다른 목록으로 접었다
            "2026-11-18": (start - 100, 0, fp, ""),           # 안 닫혔고 어제 접었다
            "2026-11-19": (start + 100, 0, fp, ""),           # 안 닫혔고 오늘 이미 접었다
            "2026-11-20": (start + 100, 0, fp, "")}           # 오늘 — 늘 다시
    assert usage_fold.due_days(done, "2026-11-14", TODAY, fp, refold_ex=False) == ["2026-11-14", "2026-11-15", "2026-11-18", "2026-11-20"]
    assert usage_fold.due_days(done, "2026-11-14", TODAY, fp, refold_ex=True)[:3] == ["2026-11-14", "2026-11-15", "2026-11-17"]
    assert usage_fold.due_days(done, None, TODAY, fp, refold_ex=True) == [], "원천의 첫 날을 모르면 접을 날도 없다"
    far = usage_fold.due_days({}, "2020-01-01", TODAY, fp, refold_ex=False)
    assert len(far) == 400 and far[-1] == "2026-11-20", "되채우기는 400일 안에서만"


def test_끝난_날은_사흘째에_닫고_닫힌_날은_지워진_줄로_줄지_않는다(tmp_path):
    """사라지는 원천(지운 대화)을 접어 두는 까닭이다 — 닫히기 전에는 다시 세고, 닫힌 뒤에는 그 수를 지킨다."""
    box = _box(tmp_path)
    day = date(2026, 11, 17)
    for i in range(3):
        _conv(box, f"c{i}", "a@example.com", int(_at(day, 9)) + i)
    key = ("2026-11-17", "conversations", '{"kind":"chat","source":"web"}')
    _fold(box, _at(date(2026, 11, 18)))
    assert _daily(box, "portal", "conversations")[key] == 3 and _folds(box, "portal")["2026-11-17"][0] == 0
    box.sql("conv", "DELETE FROM conversations WHERE id = ?", [("c0",)])
    _fold(box, _at(date(2026, 11, 19)))
    assert _daily(box, "portal", "conversations")[key] == 2, "닫히기 전에는 다시 센다"
    _fold(box, _at(date(2026, 11, 20)))
    assert _folds(box, "portal")["2026-11-17"][0] == 1, "사흘째(끝난 날 + 앞 이틀)에 닫는다"
    box.sql("conv", "DELETE FROM conversations WHERE id = ?", [("c1",)])
    _fold(box, _at(date(2026, 11, 21)))
    _fold(box, _at(date(2026, 11, 25)))
    assert _daily(box, "portal", "conversations")[key] == 2, "닫힌 날은 다시 세지 않는다"


def test_다시_접어도_같은_줄이다(tmp_path):
    box = _box(tmp_path)
    t = int(_at(date(2026, 11, 19), 9))
    box.access((t, "a@example.com", "login", "portal", "local"), (t + 5, "a@example.com", "launch", "heax-hub", None))
    box.audit((t + 9, "a@example.com", "chat_start"))
    _conv(box, "c1", "a@example.com", t)
    _fold(box)
    dump = lambda: (_q(box, "SELECT * FROM usage_daily ORDER BY 1, 2, 3, 4"), _q(box, "SELECT * FROM usage_actor_daily ORDER BY 1, 2, 3"))  # noqa: E731
    first = dump()
    _fold(box)
    _fold(box, NOW + 600)
    assert dump() == first and first[1], "같은 원장을 다시 접으면 줄이 늘지도 바뀌지도 않는다"


def test_기동_때_밀린_날은_원장의_첫_날부터_채운다(tmp_path):
    box = _box(tmp_path)
    for d in (date(2026, 11, 3), date(2026, 11, 10), date(2026, 11, 19)):
        box.access((int(_at(d)), "a@example.com", "login", "portal", "local"))
    assert _fold(box)["portal"] == 18, "11-03 ~ 11-20"
    f = _folds(box, "portal")
    assert min(f) == "*" and sorted(f)[1] == "2026-11-03" and f["2026-11-17"][0] == 1 and f["2026-11-18"][0] == 0
    assert [(d, n) for d, _e, s, n, _a in _actors(box, "login")] == [("2026-11-03", 1), ("2026-11-10", 1), ("2026-11-19", 1)]
    assert _fold(box)["portal"] == 1, "오늘은 돌 때마다 다시 접는다 — 닫히지 않은 어제 · 그제는 오늘 이미 접었다"
    assert _fold(box, _at(date(2026, 11, 21), 0, 30))["portal"] == 4, "날이 바뀐 첫 접기 — 오늘과 닫히지 않은 사흘(11-18 ~ 11-20)"


# ── portal · snapshot ──────────────────────────────────────────────────────────────────────────────────────
def test_포털_원장의_사람_줄은_KST_날로_가르고_예열은_빼고_그때의_소속을_적는다(tmp_path):
    box = _box(tmp_path)
    box.user("a@example.com", affiliation="CAEG")
    late, early = _kst(2026, 11, 18, 23, 59, 59), _kst(2026, 11, 19, 0, 30)
    box.access((late, "A@Example.com", "login", "portal", "sso"), (early, "a@example.com", "login", "portal", "sso"),
               (early + 1, "a@example.com", "launch", "heax-hub", "primer"), (early + 2, "a@example.com", "launch", "heax-hub", None),
               (early + 3, "b@example.com", "open", "spdm", None), (early + 4, "c@example.com", "login_fail", "portal", "local:bad"))
    box.audit((early + 5, "a@example.com", "chat_start"), (early + 6, "a@example.com", "chat_start"), (early + 7, "a@example.com", "chat_done", "ok"),
              (early + 8, "svc-no-email", "chat_start"))
    _fold(box)
    assert _actors(box) == [("2026-11-18", "a@example.com", "login", 1, "CAEG"), ("2026-11-19", "a@example.com", "chat", 2, "CAEG"),
                            ("2026-11-19", "a@example.com", "login", 1, "CAEG"), ("2026-11-19", "a@example.com", "tile", 1, "CAEG"),
                            ("2026-11-19", "b@example.com", "tile", 1, "")]


def test_새_대화와_낸_PAT_은_접을_때_뺄_계정을_빼고_사람_줄은_그대로_둔다(tmp_path):
    box = _box(tmp_path, usage_exclude_accounts="tester@example.com")
    t = int(_at(date(2026, 11, 19), 9))
    for who in ("tester@example.com", "real@example.com"):
        box.access((t, who, "login", "portal", "local"))
        _conv(box, f"c-{who}", who, t, "deliberation", "mcp")
        box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked, parent_jti) VALUES (?, ?, ?, 'n', '[]', '[]', ?, ?, 0, ?)",
                [(f"p-{who}", who, who, t, t + 86400 * 90, None), (f"x-{who}", who, who, t, t + 86400, f"p-{who}")])
    _fold(box)
    got = _daily(box, "portal")
    assert got[("2026-11-19", "conversations", '{"kind":"deliberation","source":"mcp"}')] == 1
    assert got[("2026-11-19", "conv_owners", '{"kind":"deliberation","source":"mcp"}')] == 1
    assert (got[("2026-11-19", "pat_issued", '{"kind":"personal"}')], got[("2026-11-19", "pat_issued", '{"kind":"exchanged"}')]) == (1, 1)
    assert [e for _d, e, _s, _n, _a in _actors(box, "login")] == ["real@example.com", "tester@example.com"], "사람 줄은 읽을 때 뺀다"
    assert _folds(box, "portal")["2026-11-19"][1] == usage_fold.fingerprint(["tester@example.com"])


def test_지금_상태는_오늘_날에만_적고_지난_날의_것을_덮지_않는다(tmp_path):
    box = _box(tmp_path)
    t = int(_at(date(2026, 11, 19), 9))
    box.user("a@example.com", created=t)
    box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked) VALUES ('p1', 'a@example.com', 'a@example.com', 'n', '[]', '[]', ?, ?, 0)",
            [(t, t + 86400 * 90)])
    box.sql("users", "INSERT INTO connections (email, service, token, created_at) VALUES ('a@example.com', 'reportarchive', 'x', ?)", [(t,)])
    box.user("b@example.com", created=t, status="disabled")
    box.sql("users", "UPDATE users SET grants = ? WHERE email = ?", [('["feat:routines", "plat:spdm"]', "a@example.com"), ('["feat:routines"]', "b@example.com")])
    _fold(box, _at(date(2026, 11, 19)))
    box.sql("tokens", "INSERT INTO pat (jti, sub, email, name, aud, scopes, created, exp, revoked) VALUES ('p2', 'a@example.com', 'a@example.com', 'n', '[]', '[]', ?, ?, 0)",
            [(t + 86400, t + 86400 * 90)])
    _fold(box, _at(date(2026, 11, 20)))
    got = _daily(box, "snapshot")
    assert (got[("2026-11-19", "pats_live", '{"kind":"personal"}')], got[("2026-11-20", "pats_live", '{"kind":"personal"}')]) == (1, 2)
    assert got[("2026-11-20", "connections", '{"service":"reportarchive"}')] == 1 and got[("2026-11-20", "accounts", '{"status":"active"}')] == 1
    assert (got[("2026-11-20", "grants", '{"key":"feat:routines"}')], got[("2026-11-20", "grants", '{"key":"plat:spdm"}')]) == (1, 1), \
        "개별 허가는 쓰는 계정의 것만 센다(정지 계정의 허가는 뺀다)"
    assert {d for d, _m, _x in got} == {"2026-11-19", "2026-11-20"}, "되채우기는 지난 날의 '지금 상태' 를 지어내지 않는다"


# ── nginx ──────────────────────────────────────────────────────────────────────────────────────────────────
def _ngx(ts: float, path: str, uid: str = "-", status=200, ip="203.0.113.5") -> str:
    t = datetime.fromtimestamp(ts, KST).isoformat(timespec="seconds")
    return f'{ip} "-" [{t}] "GET {path} HTTP/1.1" {status} 512 "Mozilla/5.0" "{uid}"\n'


def _nginx_log(box: Box, *lines: str, name="nginx-access.log", gz=False, mtime: float = NOW, mode="a") -> Path:
    """정문 로그 파일(회전본은 .gz)에 줄을 적는다. 접기는 파일의 mtime 으로 창 안의 파일을 고르므로 그 시각도 박는다(시험이 벽시계에 기대지 않게)."""
    p = Path(box.s.nginx_access_log_path).parent / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with (gzip.open(p, mode + "t", encoding="utf-8") if gz else open(p, mode, encoding="utf-8")) as f:
        f.writelines(lines)
    os.utime(p, (mtime, mtime))
    return p


def test_정문_로그는_연결_ID_로_사람에게_잇고_서비스마다_센다(tmp_path):
    box = _box(tmp_path, usage_exclude_accounts="tester@example.com")
    box.user("a@example.com", affiliation="CAEG")
    d = date(2026, 11, 19)
    box.sql("audit", "INSERT INTO access_log (ts, email, event, service, uid, detail) VALUES (?, ?, 'login', 'portal', ?, 'sso')",
            [(int(_at(d, 8)), "a@example.com", "uid-aaaa"), (int(_at(d, 8)), "tester@example.com", "uid-test"),
             (int(_at(date(2026, 11, 1))), "b@example.com", "uid-bbbb")])
    _nginx_log(box, _ngx(_at(date(2026, 11, 18), 23), "/apps/step_forge/", "uid-bbbb"), name="nginx-access.log-20261119.gz", gz=True)
    _nginx_log(box, _ngx(_at(d, 9), "/apps/step_forge/view", "uid-aaaa"), _ngx(_at(d, 9, 1), "/apps/step_forge/api/x?q=1", "uid-aaaa"),
               _ngx(_at(d, 9, 2), "/apps/step_forge/", "uid-bbbb"), _ngx(_at(d, 9, 3), "/agent/chat", "uid-aaaa"),
               _ngx(_at(d, 9, 4), "/heax-hub/", "uid-aaaa"), _ngx(_at(d, 9, 5), "/apps/step_forge/", "uid-test"),
               _ngx(_at(d, 9, 6), "/wp-login.php", "-", 404), _ngx(_at(d, 9, 7), "/", "uid-unknown"), "깨진 줄\n")
    _fold(box)
    got = {(day, m, x): v for (day, m, x), v in _daily(box, "nginx").items() if day == "2026-11-19"}
    assert got == {("2026-11-19", "requests", '{"service":"apps/step_forge"}'): 3, ("2026-11-19", "people", '{"service":"apps/step_forge"}'): 2,
                   ("2026-11-19", "requests", '{"service":"portal"}'): 1, ("2026-11-19", "people", '{"service":"portal"}'): 1,
                   ("2026-11-19", "requests", '{"service":"heax-hub"}'): 1, ("2026-11-19", "people", '{"service":"heax-hub"}'): 1,
                   ("2026-11-19", "unattributed", ""): 2}
    assert [(day, e, n, a) for day, e, _s, n, a in _actors(box, "nginx") if day == "2026-11-19"] == [
        ("2026-11-19", "a@example.com", 4, "CAEG"), ("2026-11-19", "b@example.com", 1, ""), ("2026-11-19", "tester@example.com", 1, "")]
    blob = json.dumps(_q(box, "SELECT * FROM usage_daily") + _q(box, "SELECT * FROM usage_actor_daily"), ensure_ascii=False)
    for leak in ("203.0.113.5", "uid-aaaa", "Mozilla", "q=1", "wp-login"):
        assert leak not in blob, leak


def test_정문_로그가_덮지_않는_날은_값_없이_그렇다고만_적고_접어_둔_날은_지키지_않은_로그로_줄이지_않는다(tmp_path):
    box = _box(tmp_path)
    box.sql("audit", "INSERT INTO access_log (ts, email, event, service, uid, detail) VALUES (?, 'a@example.com', 'login', 'portal', 'uid-aaaa', 'sso')",
            [(int(_at(date(2026, 11, 1))),)])
    _nginx_log(box, _ngx(_at(date(2026, 11, 18), 15), "/", "uid-aaaa"), _ngx(_at(date(2026, 11, 19), 9), "/", "uid-aaaa"),
               _ngx(_at(date(2026, 11, 19), 10), "/", "uid-aaaa"))
    _fold(box)
    f = _folds(box, "nginx")
    assert f["2026-11-17"][2] == usage_fold.NOCOVER and f["2026-11-10"][2] == usage_fold.NOCOVER, "로그의 첫 줄보다 앞선 날"
    assert "일부만" in f["2026-11-18"][2] and f["2026-11-19"][2] == ""
    key = ("2026-11-19", "requests", '{"service":"portal"}')
    assert _daily(box, "nginx")[key] == 2
    _nginx_log(box, _ngx(_at(date(2026, 11, 19), 10), "/", "uid-aaaa"), _ngx(_at(date(2026, 11, 21), 9), "/", "uid-aaaa"), mode="w",
               mtime=_at(date(2026, 11, 21)))
    _fold(box, _at(date(2026, 11, 21)))                                 # 회전으로 11-19 의 앞 줄이 사라졌다
    assert _daily(box, "nginx")[key] == 2, "앞이 잘린 로그로 다시 세어 줄이지 않는다"
    assert _daily(box, "nginx")[("2026-11-21", "requests", '{"service":"portal"}')] == 1


def test_정문_로그가_없으면_그_원천만_까닭을_남기고_다른_원천은_접는다(tmp_path):
    box = _box(tmp_path)
    box.access((int(_at(date(2026, 11, 19))), "a@example.com", "login", "portal", "local"))
    out = _fold(box)
    assert "정문 접근 로그가 없다" in out["nginx"]["error"] and out["portal"] == 2
    assert "정문 접근 로그가 없다" in _folds(box, "nginx")["*"][2] and _folds(box, "portal")["*"][2] == ""


# ── gateway · agent ────────────────────────────────────────────────────────────────────────────────────────
def _audit_line(ts: str, tool: str, backend, ok=True, ms=10, **kw) -> str:
    return json.dumps({"ts": ts, "tool": tool, "backend": backend, "ok": ok, "ms": ms, **kw}, ensure_ascii=False) + "\n"


class Remote:
    """형제 리포의 실제 셈 모듈로 답하는 창구 둘 — 받은 물음을 적어 둔다."""

    def __init__(self, tmp_path, *, gateway_status=200, agent_status=200):
        self.gw = _sibling("HWAXMcpGateway", "sibling_gateway_usage_rollup")
        self.ag = _sibling("HWAXAgentServer", "sibling_agent_usage_rollup")
        self.audit, self.db = tmp_path / "gw-audit.jsonl", tmp_path / "gw-usage-rollup.sqlite"
        self.jobs: list[dict] = []
        self.asked: list[tuple[str, dict]] = []
        self.status = {"gateway.test": gateway_status, "agent.test": agent_status}
        self.budget = 20.0
        self.today = TODAY.isoformat()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, body = request.url.host, json.loads(request.content or b"{}")
        assert request.url.path == "/usage-rollup" and request.method == "POST"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        self.asked.append((host, body))
        if self.status[host] != 200:
            return httpx.Response(self.status[host], json={"error": "x"})
        if host == "gateway.test":
            return httpx.Response(200, json=self.gw.view(self.db, self.audit, body, budget_s=self.budget, today=self.today))
        p = self.ag.params(body, self.today)
        first = min((datetime.fromtimestamp(j["started_at"], KST).date().isoformat() for j in self.jobs), default=None)
        return httpx.Response(200, json={**self.ag.fold(self.jobs, p), "ledger": {"first_day": first, "scanned": len(self.jobs)}})


def test_게이트웨이_창구의_답을_날마다_접는다(tmp_path):
    box = _box(tmp_path)
    box.user("a@example.com", affiliation="CAEG")
    rem = Remote(tmp_path)
    rem.audit.write_text(
        _audit_line("2026-11-18T01:00:00+00:00", "search_cards", "ai-data-hub", via="pat", caller="a@example.com", ms=120, chars=900)
        + _audit_line("2026-11-18T01:00:01+00:00", "aidatahub_search_cards", "ai-data-hub", via="pat", caller="a@example.com", ms=0, note="cache-hit")
        + _audit_line("2026-11-18T01:00:02+00:00", "search_cards", "ai-data-hub", ok=False, error="forbidden", via="chat", caller="b@example.com")
        + _audit_line("2026-11-18T01:00:03+00:00", "deliberate_status", "hwax-deliberation", via="pat", caller="a@example.com")
        + _audit_line("2026-11-18T01:00:04+00:00", "create_report_draft", "reportarchive", via="chat", caller="b@example.com")
        + _audit_line("2026-11-18T01:00:05+00:00", "create_report_draft", "reportarchive", via="gw-token")
        + _audit_line("2026-11-18T01:00:06+00:00", "POST /mcp", None, ok=False, ms=0, error="unauthorized: expired")
        + _audit_line("2026-11-18T01:00:07+00:00", "t", "app", via="service", caller="system:corelink"), encoding="utf-8")
    assert _fold(box, handler=rem)["gateway"] == 3, "원장의 첫 날(11-18)부터 오늘까지"
    got = {(m, x): v for (d, m, x), v in _daily(box, "gateway").items() if d == "2026-11-18"}
    hub = '{"app":"ai-data-hub","tool":"search_cards","via":"pat"}'
    assert got[("calls", hub)] == 2 and got[("cache", hub)] == 1 and got[("chars", hub)] == 900, "접두 이름은 원래 이름으로 접혀 온다"
    assert got[("err_gate", '{"app":"ai-data-hub","tool":"search_cards","via":"chat"}')] == 1
    assert got[("calls", '{"app":"hwax-deliberation","st":1,"tool":"deliberate_status","via":"pat"}')] == 1, "상태 묻기는 표지를 단다"
    assert got[("lat", '{"app":"ai-data-hub","le":5,"tool":"search_cards"}')] == 1, "캐시 적중은 지연에 들지 않는다"
    assert got[("auth_fail", '{"reason":"expired"}')] == 1 and got[("anon_calls", '{"via":"gw-token"}')] == 1
    assert _actors(box, "mcp%") + _actors(box, "ra") == [
        ("2026-11-18", "a@example.com", "mcp-pat", 3, "CAEG"), ("2026-11-18", "b@example.com", "mcp-chat", 2, ""),
        ("2026-11-18", "b@example.com", "ra", 1, "")], "메일이 아닌 호출자(system:…)는 사람 줄에 넣지 않는다"
    (host, probe), (_, body) = rem.asked[0], rem.asked[1]
    assert host == "gateway.test" and body["actor_tools"] == ["create_report_draft"] and body["exclude"] == []
    assert (probe["since"], probe["until"]) == ("2026-11-20", "2026-11-20"), "처음에는 오늘 하루를 물어 그쪽 원장의 첫 날을 안다"
    assert (body["since"], body["until"]) == ("2026-11-18", "2026-11-20")


def test_긴_되채우기는_예순_날씩_나눠_묻는다(tmp_path):
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.audit.write_text(_audit_line("2026-06-25T01:00:00+00:00", "t", "app") + _audit_line("2026-11-19T01:00:00+00:00", "t", "app"), encoding="utf-8")
    assert _fold(box, handler=rem)["gateway"] == 149, "06-25 ~ 11-20"
    spans = [(b["since"], b["until"]) for h, b in rem.asked if h == "gateway.test"]
    assert spans == [("2026-11-20", "2026-11-20"), ("2026-06-25", "2026-08-23"), ("2026-08-24", "2026-10-22"), ("2026-10-23", "2026-11-20")]
    got = _daily(box, "gateway", "calls")
    assert {d for d, _m, _x in got} == {"2026-06-25", "2026-11-19"} and len(_folds(box, "gateway")) == 150


def test_뺄_계정_목록이_바뀌면_게이트웨이는_닫힌_날도_다시_접고_포털_쪽은_닫힌_날을_다시_세지_않는다(tmp_path):
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.audit.write_text("".join(_audit_line("2026-11-10T01:00:00+00:00", "t", "app", via="pat", caller=who)
                                 for who in ("tester@example.com", "real@example.com")), encoding="utf-8")
    _conv(box, "c1", "tester@example.com", int(_at(date(2026, 11, 10))))
    _fold(box, handler=rem)
    key, conv = ("2026-11-10", "calls", '{"app":"app","tool":"t","via":"pat"}'), ("2026-11-10", "conversations", '{"kind":"chat","source":"web"}')
    assert _daily(box, "gateway")[key] == 2 and _daily(box, "portal")[conv] == 1 and _folds(box, "gateway")["2026-11-10"][0] == 1
    box.s = box.s.model_copy(update={"usage_exclude_accounts": "tester@example.com"})
    rem.asked.clear()
    _fold(box, handler=rem)
    assert _daily(box, "gateway")[key] == 1, "게이트웨이 원장은 무기한이라 다시 물어 다시 접는다"
    assert rem.asked[0][1]["exclude"] == ["tester@example.com"] and rem.asked[0][1]["since"] == "2026-11-10"
    assert _daily(box, "portal")[conv] == 1, "포털 쪽 닫힌 날은 그대로다(사라진 줄을 잃지 않게)"
    assert _folds(box, "gateway")["2026-11-10"][1] == usage_fold.fingerprint(["tester@example.com"])
    assert [e for _d, e, _s, _n, _a in _actors(box, "mcp%")] == ["real@example.com"]


def test_게이트웨이가_원장을_다_못_접었으면_그_답은_쓰지_않고_다_접을_때까지_다시_묻는다(tmp_path):
    """덜 접은 답의 수는 모자란다 — 접어 두면 닫힌 날이 모자란 채 굳는다. 물을 때마다 게이트웨이가 이어 접으므로 다시 묻는다."""
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.gw.CHUNK_LINES, rem.budget = 2, 0.0             # 한 물음에 두 줄씩만 접는다
    rem.audit.write_text("".join(_audit_line(f"2026-11-{d}T01:00:0{i}+00:00", "t", "app") for d in (17, 18, 19) for i in range(2)),
                         encoding="utf-8")
    out = _fold(box, handler=rem)
    assert out["gateway"] == 4 and len([h for h, _ in rem.asked if h == "gateway.test"]) == 5, "세 번 덜 접고 · 첫 날을 알고 · 다섯 번째에 채웠다"
    got = _daily(box, "gateway", "calls")
    assert {d: v for (d, _m, _x), v in got.items()} == {"2026-11-17": 2, "2026-11-18": 2, "2026-11-19": 2}


def test_게이트웨이가_끝내_다_못_접으면_아무_날도_쓰지_않고_어디까지_접었는지_남긴다(tmp_path, monkeypatch):
    box = _box(tmp_path)
    rem = Remote(tmp_path)
    rem.gw.CHUNK_LINES, rem.budget = 1, 0.0
    monkeypatch.setattr(usage_fold, "REMOTE_ASKS", 2)
    rem.audit.write_text("".join(_audit_line(f"2026-11-{d}T01:00:00+00:00", "t", "app") for d in (16, 17, 18, 19)), encoding="utf-8")
    out = _fold(box, handler=rem)
    assert "아직 접는 중" in out["gateway"]["error"] and "2026-11-17 10:00 까지" in _folds(box, "gateway")["*"][2]
    assert _daily(box, "gateway") == {} and set(_folds(box, "gateway")) == {"*"}, "덜 접은 수를 접어 두지 않는다"
    monkeypatch.setattr(usage_fold, "REMOTE_ASKS", 12)
    assert _fold(box, handler=rem)["gateway"] == 5, "다음에 이어 — 11-16 ~ 11-20"


@pytest.mark.parametrize(("status", "why"), [(404, "판이 낡았다"), (401, "공유 비밀"), (500, "HTTP 500")])
def test_게이트웨이가_낡았거나_거절해도_까닭만_남기고_나머지는_접는다(tmp_path, status, why):
    box = _box(tmp_path)
    box.access((int(_at(date(2026, 11, 19))), "a@example.com", "login", "portal", "local"))
    rem = Remote(tmp_path, gateway_status=status)
    rem.jobs.append({"id": "j1", "job": "default", "status": "done", "started_at": _at(date(2026, 11, 19)), "finished_at": _at(date(2026, 11, 19), 13),
                     "user": "a@example.com", "owner_aff": "LAB", "seats": [{"key": "x"}], "round": 2, "report_id": 9})
    out = _fold(box, handler=rem)
    assert why in out["gateway"]["error"] and out["portal"] == 2 and out["agent"] == 2
    note = _folds(box, "gateway")["*"][2]
    assert why in note and TOKEN not in note and "gateway.test" not in note, "비밀 · 주소는 까닭에 싣지 않는다"
    assert _folds(box, "agent")["*"][2] == ""


def test_닿지_않거나_비밀이_없어도_예외_없이_까닭을_남긴다(tmp_path):
    box = _box(tmp_path, gateway_shared_token="")
    out = _fold(box)
    assert "공유 비밀" in out["gateway"]["error"] and "공유 비밀" in out["agent"]["error"]
    box.s = box.s.model_copy(update={"gateway_shared_token": TOKEN})
    out = _fold(box)
    assert "닿지 못했다" in out["gateway"]["error"] and "닿지 못했다" in out["agent"]["error"]
    box.s = box.s.model_copy(update={"mcp_gateway_url": ""})
    assert "주소가 없다" in _fold(box)["gateway"]["error"]


def test_답의_꼴이_다르면_그_원천만_못_접는다(tmp_path):
    box = _box(tmp_path)

    def handler(request):
        if request.url.host == "gateway.test":
            return httpx.Response(200, json={"contract": 1, "complete": True, "audit": {"first_day": "2026-11-19"}, "calls": [{"day": "2026-11-19"}],
                                             "actors": [], "rules": {"lat_le_ms": list(usage_stats.LAT_LE_MS)}})
        return httpx.Response(200, json={"contract": 2})
    out = _fold(box, handler=handler)
    assert "꼴이 다르다" in out["gateway"]["error"] and "꼴이 다르다" in out["agent"]["error"]
    assert _daily(box, "gateway") == {} and "2026-11-19" not in _folds(box, "gateway")


def test_지연_칸이_게이트웨이와_다르면_접지_않는다(tmp_path):
    """포털은 칸의 번호만 접어 두고 위 끝은 제 표로 읽는다 — 두 리포의 표가 어긋난 채 접으면 분위수가 조용히 틀린다."""
    assert list(_sibling("HWAXMcpGateway", "sibling_gateway_usage_rollup").LAT_LE_MS) == list(usage_stats.LAT_LE_MS)
    assert _sibling("HWAXMcpGateway", "sibling_gateway_usage_rollup").quantile([3, 0, 0, 2] + [0] * 13, 0.95) == \
        usage_stats.quantile([3, 0, 0, 2] + [0] * 13, 0.95), "분위수 셈도 같다"
    box = _box(tmp_path)

    def handler(request):
        if request.url.host != "gateway.test":
            return httpx.Response(404)
        return httpx.Response(200, json={"contract": 1, "complete": True, "audit": {"first_day": "2026-11-19"}, "calls": [], "actors": [],
                                         "rules": {"lat_le_ms": [1, 2, 3]}})
    out = _fold(box, handler=handler)
    assert "지연 칸" in out["gateway"]["error"] and "2026-11-19" not in _folds(box, "gateway")


def test_에이전트_서버_창구의_답을_날마다_접는다(tmp_path):
    box = _box(tmp_path)
    box.user("b@example.com", affiliation="CAEG")
    rem = Remote(tmp_path)
    d = date(2026, 11, 19)
    rem.jobs += [
        {"id": "j1", "job": "default", "status": "done", "started_at": _at(d, 9), "finished_at": _at(d, 9, 30), "user": "a@example.com",
         "owner_aff": "LAB", "seats": [{"key": "x"}, {"key": "y"}], "round": 3, "report_id": 9},
        {"id": "j2", "job": "sim-plan", "status": "error", "started_at": _at(d, 10), "finished_at": _at(d, 10, 10), "user": "b%40example.com",
         "owner_aff": "", "seats": [{"key": "x"}], "round": 1},
        {"id": "j3", "job": "default", "status": "done", "started_at": _at(d, 11), "finished_at": _at(d, 11, 10), "user": "", "seats": [], "round": 0,
         "opts": {"llm": "external"}}]
    assert _fold(box, handler=rem)["agent"] == 2
    got = {(m, x): v for (day, m, x), v in _daily(box, "agent").items() if day == "2026-11-19"}
    assert got[("jobs", '{"kind":"default","llm":"glm","status":"done"}')] == 1 and got[("jobs", '{"kind":"default","llm":"external","status":"done"}')] == 1
    assert got[("jobs", '{"kind":"sim-plan","llm":"glm","status":"error"}')] == 1 and got[("jobs_report", '{"kind":"default"}')] == 1
    assert (got[("seats", '{"kind":"default"}')], got[("seated", '{"kind":"default"}')], got[("rounds", '{"kind":"default"}')]) == (2, 1, 3)
    assert (got[("dur_s", '{"kind":"default"}')], got[("dur_n", '{"kind":"default"}')]) == (2400.0, 2) and got[("anon_jobs", "")] == 1
    assert _actors(box, "delib") == [("2026-11-19", "a@example.com", "delib", 1, "LAB"), ("2026-11-19", "b@example.com", "delib", 1, "CAEG")], \
        "소속은 잡을 연 때의 값, 없으면 지금 원장의 값"


# ── 보존 · 루프 밖 · 기동 ──────────────────────────────────────────────────────────────────────────────────
def test_사람_줄은_400일_뒤에_지우고_합계_줄은_둔다(tmp_path):
    box = _box(tmp_path)
    with closing(usage_fold.connect(box.s)) as c:
        c.executemany("INSERT INTO usage_actor_daily VALUES (?, 'a@example.com', 'login', 1, '')", [("2025-10-16",), ("2025-10-17",), ("2026-11-19",)])
        c.execute("INSERT INTO usage_daily VALUES ('2025-01-01', 'gateway', 'calls', '', 5)")
    _fold(box)
    assert [d for d, *_ in _actors(box)] == ["2025-10-17", "2026-11-19"], "오늘(11-20)까지 400일(10-17 부터)만 둔다"
    assert _daily(box, "gateway") == {("2025-01-01", "calls", ""): 5}


def test_원장_일은_이벤트_루프_밖에서_한다(tmp_path, monkeypatch):
    box = _box(tmp_path)
    seen, real = [], usage_fold.connect

    def probe(settings):
        try:
            asyncio.get_running_loop()
            seen.append("loop")
        except RuntimeError:
            seen.append("thread")
        return real(settings)
    monkeypatch.setattr(usage_fold, "connect", probe)
    _fold(box, handler=Remote(tmp_path))
    assert seen and set(seen) == {"thread"}, seen


def test_손잡이가_0_이면_띄우지_않고_켜면_작업이_돌다가_멈춘다(tmp_path, monkeypatch):
    box = _box(tmp_path)
    ran = []

    async def fake_once(app, settings, **kw):
        ran.append(1)
        return {"gateway": {"error": "닿지 못했다"}}
    monkeypatch.setattr(usage_fold, "run_once", fake_once)
    monkeypatch.setattr(usage_fold, "FIRST_DELAY_S", 0.0)

    async def go():
        assert usage_fold.start(APP, box.s) is None, "USAGE_FOLD_S=0 — 띄우지 않는다"
        task = usage_fold.start(APP, box.s.model_copy(update={"usage_fold_s": 1}))
        assert task is not None and task.get_name() == "usage-fold"
        for _ in range(100):
            await asyncio.sleep(0.01)
            if ran:
                break
        await usage_fold.stop(task)
        assert task.cancelled() and len(ran) == 1 and APP.state.usage_fold_last["result"] == {"gateway": {"error": "닿지 못했다"}}
        await usage_fold.stop(None)
    asyncio.run(go())


def test_접기를_띄우지_못해도_포털은_뜬다(monkeypatch):
    from app.main import app

    def boom(*a, **kw):
        raise RuntimeError("접기 기동 실패")
    monkeypatch.setattr(usage_fold, "start", boom)
    with TestClient(app) as c:
        assert app.state.usage_fold is None and c.get("/health").status_code == 200


def test_시험_기동은_접기를_띄우지_않는다():
    """conftest 가 USAGE_FOLD_S=0 으로 둔다 — 안 그러면 포털을 띄우는 시험마다 이 박스의 게이트웨이 · 에이전트 서버 · 정문 로그를 읽는다."""
    from app.main import app
    with TestClient(app):
        assert app.state.usage_fold is None
