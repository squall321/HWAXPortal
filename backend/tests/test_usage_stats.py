# 이용 통계 M1 — 포털 안 원장을 읽을 때 세는 관리자 통계와 그 밑의 agent_audit ts 색인(docs/ops-dashboard)
#
# 계정은 example.com 시험 신원만, 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
import sqlite3

from app.agent.audit import AuditLog
from app.config import Settings

# 색인이 생기기 전 판의 agent_audit 표 — 운영 박스의 원장은 이 꼴로 이미 있다(CREATE TABLE IF NOT EXISTS 는 고치지 않는다)
_OLD_AUDIT_DDL = (
    "CREATE TABLE agent_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, principal TEXT NOT NULL,"
    " chat_id TEXT, event TEXT NOT NULL, tool TEXT, status TEXT, meta TEXT)"
)


def _indexes(path, table: str) -> set[str]:
    with sqlite3.connect(path) as c:
        return {r[1] for r in c.execute(f"PRAGMA index_list({table})")}


def test_옛_원장을_열면_agent_audit_에_ts_색인이_생기고_줄은_그대로다(tmp_path):
    db = tmp_path / "agent_audit.sqlite"
    with sqlite3.connect(db) as c:
        c.execute(_OLD_AUDIT_DDL)
        c.executemany("INSERT INTO agent_audit (ts, principal, event) VALUES (?, ?, ?)",
                      [(1_700_000_000 + i, "a@example.com", "chat_start") for i in range(50)])
    assert "agent_audit_ts" not in _indexes(db, "agent_audit"), "전제 — 옛 원장에는 색인이 없다"
    s = Settings(agent_audit_log_path=str(db))
    AuditLog(s).close()
    assert "agent_audit_ts" in _indexes(db, "agent_audit")
    AuditLog(s).close()                                   # 다시 열어도(재기동마다) 그대로 — IF NOT EXISTS
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM agent_audit").fetchone()[0] == 50
        plan = " ".join(str(r) for r in c.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM agent_audit WHERE ts >= ? AND ts < ?", (0, 1)))
    assert "agent_audit_ts" in plan, f"기간으로 자르는 읽기가 색인을 타지 않는다 — {plan}"
