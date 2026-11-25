# 비밀 가림 — 칸 이름과 글 안의 꼴로 토큰 · 키를 지우고 <가림:종류> 를 남긴다(contract §4 — 게이트웨이와 같은 규칙 · 같은 시험 벡터)
"""원문을 예외 없이 남기는 원장(IX-2)의 전제다 — 비밀이 원장에 들어가면 원문 열람 권한이 곧 남의 자격을 얻는 길이 된다(IX-8).

두 갈래다.
  · 구조 — dict 의 칸 이름(대소문자 무시)이 목록의 말이거나 그 말로 끝나면 값을 `<가림:칸이름(소문자)>` 로 바꾼다.
  · 글 — PEM 비밀 키 덩어리 → `<가림:pem>` · `Bearer <글>` → `Bearer <가림:bearer>` · JWT(eyJ… 세 마디) → `<가림:jwt>`, 그리고 글 속 JSON 의
    `"칸": "값"` 꼴(구조로 풀지 못한 JSON 글 — 도구 결과 · 기록 파일 줄)도 같은 칸 이름 규칙으로.
두 번 걸어도 같은 글이 나온다(가린 자리는 다시 맞지 않는다) — 게이트웨이가 가린 것을 포털이 한 번 더 건다."""
from __future__ import annotations

import re

SECRET_KEYS = ("authorization", "token", "access_token", "refresh_token", "api_key", "apikey", "x-api-key", "secret",
               "client_secret", "password", "passwd", "cookie", "set-cookie", "session", "private_key")

_KEYS_ALT = "|".join(re.escape(k) for k in sorted(SECRET_KEYS, key=len, reverse=True))
# PEM — 시작 표지부터 끝 표지까지. 끝 표지가 없으면(잘린 글) 글 끝까지 — 반쪽 키를 남기지 않는다.
_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----(?:.*?-----END [A-Z0-9 ]*PRIVATE KEY-----|.*\Z)", re.S)
_BEARER = re.compile(r"\b([Bb][Ee][Aa][Rr][Ee][Rr])[ \t]+[A-Za-z0-9\-._~+/]+=*")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
# 글 속 JSON 의 "칸": "값" — 칸 이름이 목록의 말로 끝날 때만(그 말 자체 포함). 값은 따옴표 안의 글(이스케이프 포함)만 — 수 · 객체는 구조 갈래 몫이다.
_KV = re.compile(r'"((?:[^"\\]|\\.)*?(?:' + _KEYS_ALT + r'))"(\s*:\s*)"(?:[^"\\]|\\.)*"', re.I)


def secret_key(name: object) -> bool:
    """칸 이름이 가릴 칸인가 — 목록의 말이거나 그 말로 끝난다(대소문자 무시)."""
    n = str(name).lower()
    return any(n == k or n.endswith(k) for k in SECRET_KEYS)


def redact_text(s: str) -> str:
    if not s:
        return s
    s = _PEM.sub("<가림:pem>", s)
    s = _KV.sub(lambda m: f'"{m.group(1)}"{m.group(2)}"<가림:{m.group(1).lower()}>"', s)
    s = _BEARER.sub(lambda m: f"{m.group(1)} <가림:bearer>", s)
    return _JWT.sub("<가림:jwt>", s)


def redact(obj):
    """JSON 값 하나 — dict 의 가릴 칸은 값째 바꾸고(값이 None 이면 그대로 — 감출 것이 없다), 글은 redact_text, 목록 · dict 는 안으로."""
    if isinstance(obj, dict):
        return {k: (f"<가림:{str(k).lower()}>" if secret_key(k) and v is not None else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj
