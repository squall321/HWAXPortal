# 관리자용 서비스 접속 이력 — 포털 원장(로그인·진입)과 정문 nginx 로그의 계정별 요청 요약(docs/access-history)
"""두 원천을 따로 낸다.

- 원장(`GET /auth/admin/access`): 로그인·타일 진입. 무기한. **들어간 순간**만 있다.
- 정문 요청(`GET /auth/admin/access/requests?email=`): nginx 가 요청마다 적는 로그인 연결 ID(`hwax_uid`)를 원장의 login 행과
  이어, 그 사람이 정문을 지나 부른 모든 서비스를 서비스별로 요약한다. nginx 로그 보존(14일)만큼만 거슬러 간다.
  연결 ID 는 쿠키라 **귀속이지 증명이 아니다**(D-5).
"""

import gzip
import re
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request

from app.access.policy import ADMIN_GROUP
from app.auth.provider import Principal
from app.config import Settings, get_settings
from app.deps import require_role

router = APIRouter(prefix="/auth/admin/access", tags=["access-history"])

MAX_ROWS = 2000
NGINX_KEEP_DAYS = 14          # logrotate daily ×14 (infra/logrotate/hwax.conf.tmpl)
RECENT = 100
# hwax.conf.tmpl 의 log_format hwax_access — 끝 칸이 연결 ID 다. 그 칸이 없는 옛 줄은 안 맞는다(그래야 한다).
_LINE = re.compile(r'^(\S+) "[^"]*" \[([^\]]+)\] "(\S+) ([^"]*)" (\d{3}) \d+ "[^"]*" "([^"]*)"\s*$')


@router.get("")
def ledger(
    request: Request,
    email: str | None = None,
    service: str | None = None,
    event: str | None = None,
    days: int = Query(7, ge=1, le=3650),
    limit: int = Query(500, ge=1, le=MAX_ROWS),
    include_auto: bool = False,
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    since = int(time.time()) - days * 86400
    rows = request.app.state.agent_audit.query_access(
        email=email or None, service=service or None, event=event or None, since=since,
        include_auto=include_auto, limit=limit + 1)
    return {"rows": rows[:limit], "truncated": len(rows) > limit, "days": days}


def _service_of(path: str, ids: set[str]) -> str:
    seg = path.lstrip("/").split("/", 2)
    if seg[0] == "apps" and len(seg) > 1 and seg[1]:
        return f"apps/{seg[1]}"                      # HEAX 에 올라간 앱 하나하나
    return seg[0] if seg[0] in ids else "portal"


def _log_files(log: Path, since: float) -> list[Path]:
    """현재 파일과 회전본(.gz 포함) 중 창 안에 쓰인 것."""
    out = []
    for f in log.parent.glob(log.name + "*"):
        try:
            if f.is_file() and f.stat().st_mtime >= since:
                out.append(f)
        except OSError:
            continue
    return sorted(out)


@router.get("/requests")
def requests_for(
    request: Request,
    email: str,
    days: int = Query(7, ge=1, le=NGINX_KEEP_DAYS),
    settings: Settings = Depends(get_settings),
    _admin: Principal = Depends(require_role(ADMIN_GROUP)),
) -> dict:
    now = time.time()
    since = now - days * 86400
    # 창 시작 전에 로그인한 연결 ID 도 창 안에서 쓰일 수 있다 — 로그인 하나의 수명만큼 더 거슬러 찾는다.
    uids = request.app.state.agent_audit.uids_for(email, int(since - settings.jwt_refresh_ttl))
    files = _log_files(Path(settings.resolve(settings.nginx_access_log_path)), since)
    ids = {s.id for s in request.app.state.catalog.all()} | {"mcp-gw"}
    svc: dict[str, dict] = {}
    recent: list[dict] = []
    uid_column = False                                # 정문 로그에 연결 ID 칸이 있기는 한가(nginx 재기동 전이면 없다)
    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        try:
            with opener(f, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = _LINE.match(line)
                    if not m:
                        continue
                    uid_column = True
                    ip, t, method, path, status, uid = m.groups()
                    if uid not in uids:
                        continue
                    try:
                        ts = datetime.fromisoformat(t).timestamp()
                    except ValueError:
                        continue
                    if ts < since:
                        continue
                    name = _service_of(path, ids)
                    row = svc.setdefault(name, {"service": name, "requests": 0, "first": ts, "last": ts, "ips": set()})
                    row["requests"] += 1
                    row["first"], row["last"] = min(row["first"], ts), max(row["last"], ts)
                    row["ips"].add(ip)
                    recent.append({"ts": int(ts), "ip": ip, "method": method, "path": path[:200],
                                   "status": int(status), "service": name})
        except OSError:
            continue
    recent.sort(key=lambda r: r["ts"], reverse=True)
    services = sorted(svc.values(), key=lambda r: r["requests"], reverse=True)
    for r in services:
        r["first"], r["last"] = int(r["first"]), int(r["last"])
        r["ips"] = sorted(r["ips"])[:20]
    note = ""
    if not uids:
        note = "이 기간에 이 계정의 로그인 기록(연결 ID)이 없다 — 원장이 생기기 전이거나 PAT·MCP 로만 썼다."
    elif not uid_column:
        note = "정문 로그에 연결 ID 칸이 아직 없다 — nginx 가 새 설정으로 재기동되기 전이다."
    return {"email": email.strip().lower(), "days": days, "services": services, "recent": recent[:RECENT],
            "logins": len(uids), "files": len(files), "uid_column": uid_column, "note": note}
