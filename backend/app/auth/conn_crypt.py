# 사람이 등록한 외부 연결 토큰을 박스 고유 키로 암호화한다 — 쓸 때 잠그고 읽을 때 푼다(docs/request-1027 HP-05 · 사용자 결정 D-5)
"""왜 — RA · TestScope · FMEA · MatNexus … 사람마다 등록한 토큰이 users.sqlite `connections` 표에 평문으로 있었고, 파일은 644 였다.
플랫폼이 늘 때마다 한 사람에 토큰이 하나씩 더 쌓인다.

  · 키 — `backend/secrets/conn.key`(Settings.conn_key_path, 0600 · 폴더 0700). 없으면 처음 열 때 만든다. 키는 **비밀 묶음**(backup-local
    secrets — 박스 밖으로 나가지 않는다)에 들고, DB 를 담는 포털 묶음에는 넣지 않는다 — 둘이 한 묶음이면 암호화가 백업에서 뜻을 잃는다.
  · 꼴 — 저장값은 `enc:v1:<Fernet>`. 머리가 없는 값은 옛 평문이다 — 기동 때 제자리에서 바꾼다(UserStore).
  · 키를 잃으면 — 옛 암호문은 풀 수 없다. 그 연결은 '등록 없음' 으로 읽히고(사람마다 다시 등록), 기동 로그가 몇 건인지 말한다.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("hwax.conn_crypt")

PREFIX = "enc:v1:"


def _load_or_create(path: Path) -> tuple[bytes, bool]:
    """(키, 이번에 만들었나). 만들 때는 O_EXCL 로 — 두 프로세스가 동시에 떠도 한쪽 키만 남는다."""
    try:
        return path.read_bytes().strip(), False
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    key = Fernet.generate_key()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        try:
            return path.read_bytes().strip(), False       # 동시에 뜬 다른 프로세스가 먼저 만들었다
        except OSError as exc:                             # 깨진 심볼릭 링크 등 — 새 키로 덮지 않고 멈춘다(옛 암호문을 버리게 된다)
            raise RuntimeError(f"연결 토큰 암호 키 {path} 를 읽지 못했다({exc}) — 링크 대상을 되살리거나 비밀 묶음에서 복원한다") from exc
    with os.fdopen(fd, "wb") as f:
        f.write(key + b"\n")
    return key, True


class ConnCipher:
    def __init__(self, key_path: str | Path) -> None:
        self.path = Path(key_path)
        key, self.created = _load_or_create(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        self._f = Fernet(key)

    @staticmethod
    def is_enc(stored: str) -> bool:
        return isinstance(stored, str) and stored.startswith(PREFIX)

    def encrypt(self, token: str) -> str:
        return PREFIX + self._f.encrypt(token.encode("utf-8")).decode("ascii")

    def decrypt(self, stored: str) -> str | None:
        """저장값 → 평문. 옛 평문은 그대로, 풀 수 없으면(키가 다르다 · 깨졌다) None."""
        if not self.is_enc(stored):
            return stored
        try:
            return self._f.decrypt(stored[len(PREFIX):].encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return None
