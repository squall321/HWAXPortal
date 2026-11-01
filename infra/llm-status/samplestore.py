# LLM/GPU 현황 수집기의 sqlite 표본 저장소 — 15초 표본 48시간 · 5분 접기 35일 · 지우기 · 그래프용 시계열(docs/ops-dashboard PLAN §3.3)
"""표준 라이브러리만 쓴다. 쓰는 것은 수집기 하나다(상태 디렉터리 잠금 — collector.py). 연결 하나를 잠금으로 나눠 쓴다(쓰기는 주기마다 작다).

표 셋.
  series(id, target, metric)       — 대상 · 지표 짝의 번호. 대상 id 는 설정의 이름이다(주소가 아니다 — 서버를 옮겨도 기록이 이어진다).
  raw(sid, ts, v)                  — 표본. ts 는 초(정수). 값이 없던 때(빈칸)는 줄이 없다 — 채워 넣지 않는다.
  rollup(sid, ts, n, avg, mn, mx)  — 5분 칸(ts 는 칸의 시작). 다 찬 칸만 접는다 — 늦게 끝난 읽기가 들어올 틈(ROLLUP_GRACE_S)을 둔다.
지우기는 대상 · 지표마다 기본 키의 앞부분으로 한다(ts 만의 색인을 두지 않는다 — 쓰기마다 색인이 하나 더 는다).
"""
import math
import sqlite3
import threading
import time
from pathlib import Path

RAW_KEEP_S = 48 * 3600
ROLLUP_S = 300
ROLLUP_KEEP_S = 35 * 86400
ROLLUP_GRACE_S = 60            # 칸이 끝나고 이만큼 지난 뒤에 접는다 — 한 대상의 읽기는 연결 3초 · 읽기 5초 × 넷까지 걸린다
MAINTAIN_EVERY_S = 300         # 접기 · 지우기를 보는 간격
# 범위 → (원천, 점 하나의 폭 초). 1h 는 표본 그대로, 24h 는 5분 칸(아직 안 접은 끝은 표본으로 같은 폭에 맞춘다), 그보다 길면 칸을 다시 묶는다.
RANGES = {"1h": ("raw", 3600, 15), "24h": ("rollup", 86400, ROLLUP_S), "7d": ("rollup", 7 * 86400, 1800),
          "35d": ("rollup", 35 * 86400, 7200)}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS series(id INTEGER PRIMARY KEY, target TEXT NOT NULL, metric TEXT NOT NULL, UNIQUE(target, metric));
CREATE TABLE IF NOT EXISTS raw(sid INTEGER NOT NULL, ts INTEGER NOT NULL, v REAL NOT NULL, PRIMARY KEY(sid, ts)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS rollup(sid INTEGER NOT NULL, ts INTEGER NOT NULL, n INTEGER NOT NULL, avg REAL NOT NULL, mn REAL NOT NULL,
                                  mx REAL NOT NULL, PRIMARY KEY(sid, ts)) WITHOUT ROWID;
"""


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._sids: dict[tuple[str, str], int] = {}
        self._last_maint = 0.0
        self.error: str | None = None
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None, timeout=5.0)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(_SCHEMA)
        for sid, target, metric in self.conn.execute("SELECT id, target, metric FROM series"):
            self._sids[(target, metric)] = sid

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def _meta(self, k: str) -> str | None:
        row = self.conn.execute("SELECT v FROM meta WHERE k = ?", (k,)).fetchone()
        return row[0] if row else None

    def _sid(self, target: str, metric: str) -> int:
        key = (target, metric)
        sid = self._sids.get(key)
        if sid is None:
            self.conn.execute("INSERT OR IGNORE INTO series(target, metric) VALUES(?, ?)", key)
            sid = self.conn.execute("SELECT id FROM series WHERE target = ? AND metric = ?", key).fetchone()[0]
            self._sids[key] = sid
        return sid

    def add(self, target: str, ts: float, values: dict[str, float | None]) -> None:
        """한 대상의 한 표본 — 값이 None · 유한하지 않은 지표는 적지 않는다(빈칸). 같은 초에 다시 오면 나중 것이 이긴다."""
        rows = [(m, float(v)) for m, v in values.items() if v is not None and isinstance(v, (int, float)) and math.isfinite(v)]
        if not rows:
            return
        with self._lock:
            try:
                self.conn.execute("BEGIN")
                self.conn.executemany("INSERT OR REPLACE INTO raw(sid, ts, v) VALUES(?, ?, ?)",
                                      [(self._sid(target, m), int(ts), v) for m, v in rows])
                self.conn.execute("COMMIT")
                self.error = None
            except sqlite3.Error as exc:
                self._rollback()
                self.error = f"쓰기 실패 — {type(exc).__name__}: {exc}"[:200]

    def _rollback(self) -> None:
        try:
            self.conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass

    def maintain(self, now: float, *, force: bool = False) -> None:
        """다 찬 5분 칸을 접고, 48시간 넘은 표본 · 35일 넘은 칸을 지운다. MAINTAIN_EVERY_S 마다 한 번(force 면 곧바로)."""
        if not force and now - self._last_maint < MAINTAIN_EVERY_S:
            return
        self._last_maint = now
        upto = int(now - ROLLUP_GRACE_S) // ROLLUP_S * ROLLUP_S
        with self._lock:
            try:
                self.conn.execute("BEGIN")
                done = self._meta("rolled_until")
                start = int(done) if done is not None else None
                if start is None:
                    first = self.conn.execute("SELECT MIN(ts) FROM raw").fetchone()[0]
                    start = None if first is None else int(first) // ROLLUP_S * ROLLUP_S
                if start is not None and start < upto:
                    for sid in list(self._sids.values()):
                        self.conn.execute(
                            "INSERT OR REPLACE INTO rollup(sid, ts, n, avg, mn, mx) "
                            "SELECT sid, (ts / ?) * ?, COUNT(*), AVG(v), MIN(v), MAX(v) FROM raw "
                            "WHERE sid = ? AND ts >= ? AND ts < ? GROUP BY sid, ts / ?",
                            (ROLLUP_S, ROLLUP_S, sid, start, upto, ROLLUP_S))
                if start is None or start < upto:
                    self.conn.execute("INSERT OR REPLACE INTO meta(k, v) VALUES('rolled_until', ?)", (str(upto),))
                raw_cut, roll_cut = int(now - RAW_KEEP_S), int(now - ROLLUP_KEEP_S)
                for sid in list(self._sids.values()):
                    self.conn.execute("DELETE FROM raw WHERE sid = ? AND ts < ?", (sid, raw_cut))
                    self.conn.execute("DELETE FROM rollup WHERE sid = ? AND ts < ?", (sid, roll_cut))
                self.conn.execute("COMMIT")
                self.error = None
            except sqlite3.Error as exc:
                self._rollback()
                self.error = f"접기 · 지우기 실패 — {type(exc).__name__}: {exc}"[:200]

    def series(self, target: str, metric: str, rng: str, now: float | None = None) -> dict:
        """{range, step_s, source, points} — raw 는 [ts, 값], 접은 것은 [ts, 평균, 최대]. 그 대상 · 지표를 적은 적이 없으면 points 가 빈다."""
        now = time.time() if now is None else now
        src, span, step = RANGES[rng]
        since = int(now - span)
        out = {"range": rng, "step_s": step, "source": src if src == "raw" else f"rollup:{ROLLUP_S // 60}m", "points": []}
        with self._lock:
            sid = self._sids.get((target, metric))
            if sid is None:
                return out
            if src == "raw":
                out["points"] = [[ts, v] for ts, v in self.conn.execute(
                    "SELECT ts, v FROM raw WHERE sid = ? AND ts >= ? ORDER BY ts", (sid, since))]
                return out
            done = self._meta("rolled_until")
            rolled = int(done) if done is not None else since
            if step == ROLLUP_S:
                pts = [[ts, a, mx] for ts, a, mx in self.conn.execute(
                    "SELECT ts, avg, mx FROM rollup WHERE sid = ? AND ts >= ? ORDER BY ts", (sid, since))]
            else:
                pts = [[ts, (s / n) if n else None, mx] for ts, s, n, mx in self.conn.execute(
                    "SELECT (ts / ?) * ?, SUM(avg * n), SUM(n), MAX(mx) FROM rollup WHERE sid = ? AND ts >= ? "
                    "GROUP BY ts / ? ORDER BY 1", (step, step, sid, since, step))]
            # 아직 접지 않은 끝(마지막 칸 ~ 지금)은 표본을 같은 폭으로 묶어 잇는다 — 24시간 그래프의 끝이 5 ~ 6분 늦지 않게
            tail: dict[int, list[float]] = {}
            for ts, v in self.conn.execute("SELECT ts, v FROM raw WHERE sid = ? AND ts >= ? ORDER BY ts",
                                           (sid, max(since, rolled))):
                tail.setdefault(ts // step * step, []).append(v)
        last = pts[-1][0] if pts else None
        for b, vs in sorted(tail.items()):
            if last is not None and b <= last:
                continue
            pts.append([b, sum(vs) / len(vs), max(vs)])
        out["points"] = pts
        return out

    def stats(self) -> dict:
        """화면 머리용 — 파일 크기와 마지막 오류. 줄 수는 세지 않는다(백만 줄을 훑는다)."""
        size = 0
        for p in (self.path, self.path.with_name(self.path.name + "-wal")):
            try:
                size += p.stat().st_size
            except OSError:
                pass
        return {"bytes": size, "series": len(self._sids), "error": self.error}
