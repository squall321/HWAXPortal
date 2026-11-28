#!/usr/bin/env python3
# 표준 입력을 여러 코어로 gzip 해 표준 출력에 낸다 — 블록마다 따로 압축한 gzip 멤버를 차례대로 잇는다(gunzip · zcat · python gzip 이 그대로 읽는다)
"""왜 — §1b 배포 전 백업의 AIDataHub 덤프가 27 ~ 28분 걸렸고(11 GB) 그 대부분이 한 코어 gzip 이었다(docs/request-1125 SE-2). 운영 서버는 16코어인데
pigz 가 없다. 형식(.sql.gz)을 바꾸면 복원 · 대조 스크립트(restore-rehearsal · dbsync · update-all)가 모두 따라 바뀌어야 해서, 같은 gzip 꼴을
여러 코어로 짓는다. 여러 멤버를 이은 gzip 은 RFC 1952 그대로다(pigz 와 같은 꼴 — 멤버마다 머리 · CRC 가 있다).

  pg_dump … | python3 infra/scripts/lib/pgzip.py > out.sql.gz
손잡이(환경) — HWAX_GZIP_LEVEL(1 ~ 9, 기본 6 — gzip 기본과 같다) · HWAX_GZIP_THREADS(기본 코어 수) · HWAX_GZIP_BLOCK_MB(기본 16).
"""
from __future__ import annotations

import collections
import concurrent.futures as cf
import os
import sys
import zlib


def _int(name: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(os.environ.get(name) or default)
    except ValueError:
        return default
    return v if lo <= v <= hi else default


def _member(block: bytes, level: int) -> bytes:
    c = zlib.compressobj(level, zlib.DEFLATED, 31)          # wbits 31 — gzip 머리 · 꼬리(CRC32 · 길이)
    return c.compress(block) + c.flush()


def main() -> int:
    level = _int("HWAX_GZIP_LEVEL", 6, 1, 9)
    threads = _int("HWAX_GZIP_THREADS", os.cpu_count() or 1, 1, 256)
    block = _int("HWAX_GZIP_BLOCK_MB", 16, 1, 256) * 1024 * 1024
    src, dst = sys.stdin.buffer, sys.stdout.buffer
    pending: collections.deque = collections.deque()
    with cf.ThreadPoolExecutor(max_workers=threads) as ex:   # zlib 은 압축 중 GIL 을 놓는다 — 스레드가 코어마다 돈다
        while True:
            b = src.read(block)
            if not b:
                break
            pending.append(ex.submit(_member, b, level))
            while len(pending) > threads * 2:                # 차례를 지키며 메모리를 블록 2 × 스레드 수로 묶는다
                dst.write(pending.popleft().result())
        while pending:
            dst.write(pending.popleft().result())
    dst.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
