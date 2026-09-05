#!/usr/bin/env python3
# SQLite 원자 스냅샷·무결성 검사 헬퍼 — 박스에 sqlite3 CLI 가 없어(실측) 파이썬 sqlite3 모듈로 통일한다.
"""
사용:
  sqlite_backup.py backup <src.db> <dst.db>     # 온라인 .backup (WAL 미반영분 포함 일관 사본). cp 금지 — WAL 손실
  sqlite_backup.py check  <db>                  # PRAGMA integrity_check → 'ok' 면 0
  sqlite_backup.py counts <db>                  # 표별 행수(JSON) — 이관 전후 대조용

주의: 소스를 읽기 전용(mode=ro)으로 열어도 WAL 모드 DB 옆에 -wal(0B)·-shm 이 생길 수 있다.
그 파일들은 **지우지 않는다** — 열린 연결이 있으면 손상된다(사전점검). backup-local.sh·
appdata-to-drive.sh 가 이미 같은 방식(sqlite3 모듈 backup)을 쓴다.
"""
import json
import sqlite3
import sys


def backup(src: str, dst: str) -> int:
    s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()
    return 0 if check(dst, quiet=True) == 0 else 1


def check(db: str, quiet: bool = False) -> int:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        r = c.execute("pragma integrity_check").fetchone()[0]
    finally:
        c.close()
    if not quiet:
        print(r)
    return 0 if r == "ok" else 1


def counts(db: str) -> int:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [t for (t,) in c.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by 1")]
        out = {t: c.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tables}
    finally:
        c.close()
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    verb = argv[1]
    if verb == "backup" and len(argv) == 4:
        return backup(argv[2], argv[3])
    if verb == "check":
        return check(argv[2])
    if verb == "counts":
        return counts(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
