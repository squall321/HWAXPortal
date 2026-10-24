# PC 도우미(추출기 -Url 모드)가 로그인 없이 올리는 일회용 표 — 발급 · 도우미 열림 · 받기 · 취소 · 상태(docs/chat-ppt PP-D8)
"""DRM 문서는 그 PC 의 Office 만 연다. 웹 챗의 단추가 표를 받아 `hwax-doc://` 로 PC 도우미를 깨우고, 도우미가 PowerPoint 로 뽑은
글(.hwax.md)과 고르면 슬라이드 그림을 이 표로 올린다. 화면은 표의 상태를 보다가 받은 글을 문서 칩으로 붙인다(서버는 대화에 쓰지 않는다).

표는 무작위 32바이트이고 디스크에는 SHA-256 만 남는다 — 상태 파일을 읽어도 올릴 수 없다. 수명 10분 · 한 번(받음 · 실패 · 취소 ·
만료로 닫힌다) · 한 사람의 열린 표는 OPEN_MAX 개까지(넘으면 가장 오래된 것을 닫는다). 포털은 uvicorn 한 프로세스라 잠금은 스레드
잠금 하나로 충분하고, 상태는 스테이징 아래 파일이라 재기동을 넘긴다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from pathlib import Path

from app.agent.upload import _user_dir
from app.config import Settings

TICKET_TTL_S = 600
OPEN_MAX = 5
DOC_MAX_BYTES = 8 * 1024 * 1024
SLIDES_MAX = 12                         # 에이전트 서버 그림 상한(VISION_MAX_IMAGES 기본 12)과 같다
SLIDE_MAX_BYTES = 8 * 1024 * 1024       # 에이전트 서버 VISION_MAX_BYTES 기본값과 같다
PROTOCOL = 1                            # 도우미와 주고받는 꼴의 판
HELPER_MIN = 1                          # 이보다 낮은 판의 도우미는 '설치 배치를 다시 받으라' 로 멈춘다(추출기 HWAX_DOC_HELPER)
_KEEP_S = 3600                          # 닫힌 표의 기록을 남겨 두는 시간 — 화면이 '만료 · 받음' 을 볼 수 있게
# 스테이징 루트 아래 표 폴더. 사용자 폴더 이름(_user_dir — 영숫자 · -_@. 만)과 겹칠 수 없는 이름이다. 기존 청소(sweep_expired —
# <루트>/*/* 의 6시간 지난 것)가 남은 표 파일도 같이 지운다.
_DIR_NAME = "#pc-tickets"
# 받은 글 상자 → 그 슬라이드 그림 상자(정밀 변환이 글과 그림을 zip 하나로 묶어 DocForge 에 넘긴다, docs/doc-to-ra DF-D18). 글 상자 안에 두지 않는다 —
# staged_path 가 상자의 첫 파일을 집으므로 다른 파일이 끼면 글 대신 그것이 간다. 같은 청소가 6시간 뒤 지운다.
_SLIDES_DIR = "#pc-slides"
_BOX_RE = re.compile(r"^[0-9a-f]{32}$")
_TICKET_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_OPEN = ("waiting", "opened")
_LOCK = threading.Lock()


class TicketError(Exception):
    """표가 없거나 · 닫혔거나 · 만료됐다(status 는 HTTP 코드)."""

    def __init__(self, message: str, status: int = 410):
        super().__init__(message)
        self.message, self.status = message, status


def _root(settings: Settings) -> Path:
    d = Path(settings.upload_staging_dir) / _DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file(settings: Settings, ticket: str) -> Path | None:
    if not isinstance(ticket, str) or not _TICKET_RE.fullmatch(ticket):
        return None
    return _root(settings) / f"{hashlib.sha256(ticket.encode()).hexdigest()}.json"


def _read(p: Path) -> dict | None:
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) else None


def _write(p: Path, rec: dict) -> None:
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _expired(rec: dict, now: float) -> bool:
    return rec.get("state") in _OPEN and now >= float(rec.get("expires") or 0)


def expires_in(rec: dict, now: float | None = None) -> int:
    """남은 초 — 닫힌 표는 0."""
    now = time.time() if now is None else now
    return max(0, int(float(rec.get("expires") or 0) - now)) if rec.get("state") in _OPEN else 0


def sweep(settings: Settings, now: float | None = None) -> list[dict]:
    """열린 채 수명이 다한 표를 '만료' 로 닫고(감사용으로 돌려준다), 닫힌 지 _KEEP_S 지난 기록을 지운다."""
    now = time.time() if now is None else now
    gone: list[dict] = []
    with _LOCK:
        for p in _root(settings).glob("*.json"):
            rec = _read(p)
            if rec is None:
                continue
            if _expired(rec, now):
                rec.update(state="expired", closed=now)
                _write(p, rec)
                gone.append(rec)
            elif rec.get("state") not in _OPEN and now - float(rec.get("closed") or rec.get("created") or 0) > _KEEP_S:
                try:
                    p.unlink()
                except OSError:
                    pass
    return gone


def issue(settings: Settings, *, owner_sub: str, owner_email: str, owner_name: str, conversation_id: str,
          filename: str, slides: bool, now: float | None = None) -> tuple[str, dict, list[dict]]:
    """새 표 — (표, 기록, 닫은 옛 표들). 이 사람의 열린 표가 OPEN_MAX 개면 가장 오래된 것부터 닫는다(재시도가 표를 쌓지 않게)."""
    now = time.time() if now is None else now
    closed: list[dict] = []
    with _LOCK:
        mine = []
        for p in _root(settings).glob("*.json"):
            rec = _read(p)
            if rec and rec.get("owner_sub") == owner_sub and rec.get("state") in _OPEN and not _expired(rec, now):
                mine.append((float(rec.get("created") or 0), p, rec))
        mine.sort(key=lambda x: x[0])
        while len(mine) >= OPEN_MAX:
            _c, p, rec = mine.pop(0)
            rec.update(state="closed", closed=now, error="같은 사람이 새 표를 받아 닫았다")
            _write(p, rec)
            closed.append(rec)
        ticket = secrets.token_urlsafe(32)
        rec = {"owner_sub": owner_sub, "owner_email": owner_email, "owner_name": owner_name,
               "conversation_id": conversation_id, "filename": filename, "slides": bool(slides),
               "state": "waiting", "created": now, "expires": now + TICKET_TTL_S}
        p = _file(settings, ticket)
        assert p is not None
        _write(p, rec)
    return ticket, rec, closed


def _open_rec(settings: Settings, ticket: str, now: float) -> tuple[Path, dict]:
    p = _file(settings, ticket)
    rec = _read(p) if p is not None and p.exists() else None
    if p is None or rec is None:
        raise TicketError("없는 표입니다 — 포털 화면에서 단추를 다시 누르세요.", 404)
    if _expired(rec, now):
        # '만료' 로 적는 것은 청소(sweep) 한 곳이다 — 거기서 감사에 한 번 남긴다. 여기서는 막기만 한다.
        raise TicketError("표가 만료됐습니다(10분) — 포털 화면에서 단추를 다시 누르세요.", 410)
    if rec.get("state") not in _OPEN:
        raise TicketError("이미 쓴 표입니다 — 포털 화면에서 단추를 다시 누르세요.", 410)
    return p, rec


def helper_open(settings: Settings, ticket: str, now: float | None = None) -> tuple[dict, bool]:
    """도우미가 처음 묻는 자리 — 받는 계정 · 파일 이름 · 상한을 돌려주고 '열림' 으로 바꾼다. (기록, 이번에 처음 열었나)."""
    now = time.time() if now is None else now
    with _LOCK:
        p, rec = _open_rec(settings, ticket, now)
        first = rec.get("state") == "waiting"
        if first:
            rec.update(state="opened", opened=now)
            _write(p, rec)
    return rec, first


def helper_cancel(settings: Settings, ticket: str, reason: str = "", now: float | None = None) -> dict:
    now = time.time() if now is None else now
    with _LOCK:
        p, rec = _open_rec(settings, ticket, now)
        rec.update(state="cancelled", closed=now, error=(reason or "PC 에서 취소했다")[:200])
        _write(p, rec)
    return rec


def claim(settings: Settings, ticket: str, now: float | None = None) -> dict:
    """받기 직전에 표를 닫는다 — 같은 표로 두 번 올리지 못한다(받는 동안의 두 번째 요청도 여기서 막힌다)."""
    now = time.time() if now is None else now
    with _LOCK:
        p, rec = _open_rec(settings, ticket, now)
        rec.update(state="receiving", claimed=now)
        _write(p, rec)
    return rec


def finish(settings: Settings, ticket: str, *, ok: bool, error: str = "", received: dict | None = None,
           now: float | None = None) -> dict:
    now = time.time() if now is None else now
    p = _file(settings, ticket)
    with _LOCK:
        rec = _read(p) if p is not None else None
        if p is None or rec is None:
            raise TicketError("없는 표입니다.", 404)
        rec.update(state="received" if ok else "failed", closed=now)
        if ok:
            rec["received"] = received or {}
        else:
            rec["error"] = error[:300]
        _write(p, rec)
    return rec


def source_name(text: str) -> str:
    """추출기 머리말의 source(원본 파일 이름). 없으면 빈 글."""
    head, _body = _front_matter(text) or ("", "")
    m = re.search(r"^source:\s*(.+)$", head, re.M)
    return m.group(1).strip() if m else ""


def _front_matter(text: str) -> tuple[str, str] | None:
    """(머리말, 본문). 머리말이 없으면 None — 추출기는 '---' 줄로 열고 닫는다(줄끝 CRLF 도 받는다)."""
    t = text.replace("\r\n", "\n")
    if not t.startswith("---\n"):
        return None
    end = t.find("\n---", 3)
    return (t[4:end], t[end + 4:]) if end > 0 else None


def check_doc(raw: bytes) -> str:
    """받은 글을 확인한다 — UTF-8 · 추출기 머리말(schema: hwax-doc/1). 맞으면 글을, 아니면 ValueError(사람이 읽을 까닭)."""
    if len(raw) > DOC_MAX_BYTES:
        raise ValueError(f"글이 {DOC_MAX_BYTES // (1024 * 1024)}MB 를 넘습니다({len(raw):,}바이트).")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("글이 UTF-8 이 아닙니다 — 추출기가 만든 .hwax.md 만 받습니다.") from exc
    text = text.removeprefix("﻿")
    fm = _front_matter(text)
    if fm is None or not re.search(r"^schema:\s*hwax-doc/1\s*$", fm[0], re.M):
        raise ValueError("추출기 머리말(schema: hwax-doc/1)이 없습니다 — 추출기가 만든 .hwax.md 만 받습니다.")
    if not fm[1].strip():
        raise ValueError("머리말 뒤에 글이 없습니다.")
    return text


def check_slide(raw: bytes, n: int) -> None:
    if len(raw) > SLIDE_MAX_BYTES:
        raise ValueError(f"슬라이드 그림 {n} 이 {SLIDE_MAX_BYTES // (1024 * 1024)}MB 를 넘습니다.")
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError(f"슬라이드 그림 {n} 이 PNG 가 아닙니다.")


def _safe_stem(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    stem = base.rsplit(".", 1)[0] if "." in base else base
    stem = "".join(c for c in stem if c.isprintable() and c not in '/\\:*?"<>|').strip(" .")
    return stem[:120] or "문서"


def store(settings: Settings, rec: dict, text: str, slides: list[bytes]) -> dict:
    """그 사람 스테이징에 둔다 — 글은 상자 하나에 .md 하나(AIDH 로 보낼 때 그 상자를 그대로 쓴다), 그림은 다른 상자. 받은 것의 요약."""
    user = _user_dir(settings, rec["owner_sub"])
    stem = _safe_stem(source_name(text) or rec.get("filename") or "")
    doc_id = uuid.uuid4().hex
    (user / doc_id).mkdir(parents=True, exist_ok=True)
    doc_name = f"{stem}.hwax.md"
    raw = text.encode("utf-8")
    (user / doc_id / doc_name).write_bytes(raw)
    out = {"doc_staging_id": doc_id, "doc_name": doc_name, "bytes": len(raw), "chars": len(text), "slides": len(slides)}
    if slides:
        sid = uuid.uuid4().hex
        (user / sid).mkdir(parents=True, exist_ok=True)
        for i, b in enumerate(slides, start=1):
            (user / sid / f"slide-{i:02d}.png").write_bytes(b)
        out["slides_staging_id"] = sid
        idx = Path(settings.upload_staging_dir) / _SLIDES_DIR
        idx.mkdir(parents=True, exist_ok=True)
        _write(idx / f"{doc_id}.json", {"owner_sub": rec["owner_sub"], "slides_staging_id": sid, "slides": len(slides)})
    return out


def slides_of(settings: Settings, owner_sub: str, doc_staging_id: str) -> list[Path]:
    """받은 글 상자에 딸린 슬라이드 그림(1번부터). 없거나 · 남의 것이거나 · 청소됐으면 빈 목록 — 부르는 쪽이 글만 보낸다."""
    if not isinstance(doc_staging_id, str) or not _BOX_RE.fullmatch(doc_staging_id):
        return []
    p = Path(settings.upload_staging_dir) / _SLIDES_DIR / f"{doc_staging_id}.json"
    rec = _read(p) if p.exists() else None
    sid = (rec or {}).get("slides_staging_id")
    if not rec or rec.get("owner_sub") != owner_sub or not isinstance(sid, str) or not _BOX_RE.fullmatch(sid):
        return []
    box = _user_dir(settings, owner_sub) / sid
    return [f for i in range(1, int(rec.get("slides") or 0) + 1) if (f := box / f"slide-{i:02d}.png").is_file()]


def view(settings: Settings, ticket: str, owner_sub: str, now: float | None = None) -> dict:
    """화면이 보는 상태(주인만). 없거나 남의 표면 TicketError(404 — 있는지조차 말하지 않는다)."""
    now = time.time() if now is None else now
    p = _file(settings, ticket)
    rec = _read(p) if p is not None and p.exists() else None
    if rec is None or rec.get("owner_sub") != owner_sub:
        raise TicketError("없는 표입니다.", 404)
    out = {"state": "expired" if _expired(rec, now) else rec["state"], "filename": rec.get("filename") or "",
           "expires_in_s": expires_in(rec, now)}
    if rec.get("error"):
        out["error"] = rec["error"]
    if rec["state"] == "received":
        r = rec.get("received") or {}
        out["received"] = {k: r[k] for k in ("doc_name", "chars", "bytes", "slides", "doc_staging_id") if k in r}
    return out


def received_doc(settings: Settings, ticket: str, owner_sub: str) -> Path:
    rec = _owned_received(settings, ticket, owner_sub)
    r = rec["received"]
    p = _user_dir(settings, owner_sub) / r["doc_staging_id"] / r["doc_name"]
    if not p.is_file():
        raise TicketError("받은 글이 스테이징에 없습니다(청소됐을 수 있다 — 다시 가져오세요).", 410)
    return p


def received_slide(settings: Settings, ticket: str, owner_sub: str, n: int) -> Path:
    rec = _owned_received(settings, ticket, owner_sub)
    r = rec["received"]
    if not r.get("slides_staging_id") or not 1 <= n <= int(r.get("slides") or 0):
        raise TicketError("없는 슬라이드 그림입니다.", 404)
    p = _user_dir(settings, owner_sub) / r["slides_staging_id"] / f"slide-{n:02d}.png"
    if not p.is_file():
        raise TicketError("받은 그림이 스테이징에 없습니다(청소됐을 수 있다 — 다시 가져오세요).", 410)
    return p


def _owned_received(settings: Settings, ticket: str, owner_sub: str) -> dict:
    p = _file(settings, ticket)
    rec = _read(p) if p is not None and p.exists() else None
    if rec is None or rec.get("owner_sub") != owner_sub:
        raise TicketError("없는 표입니다.", 404)
    if rec.get("state") != "received" or not isinstance(rec.get("received"), dict):
        raise TicketError("아직 받은 것이 없습니다.", 409)
    return rec
