# 챗의 저장된 턴을 MX 백서 LLM 위키 원천(mxwp-source/1 · kind qa)으로 보낸다 — '위키에 남기기' · '해결됨'(docs/mxwp-wiki P6 · P7)
"""포털은 위임 비밀을 더 쥐지 않는다 — 그 사람의 챗 PAT 로 게이트웨이 `wiki_submit_source` 를 부르고, 사람 명의 위임은 게이트웨이가 한다
(MW-D2). 봉투는 **저장된 턴**으로 짓는다 — 화면이 보낸 본문은 짝을 찾는 열쇠로만 쓰고 질문 · 답 · 근거는 대화 저장소의 것이다(MW-D5).

범위(audience) — MX 백서는 보낸 사람이 가진 토큰만 받는다(`["org"]` 는 관리자 · 서비스 계정만, `user:` 는 MXWP 쪽 id 라 포털이 모른다).
그래서 그 사람의 포털 소속 `aff:<소속>` 으로 보낸다. 소속이 없으면 바로 남기기(button)는 막고, '해결됨'(candidate)은 MX 백서를 쓰는
사람 모두(`plat:mxwhitepaper`)를 **제안 범위**로 보낸다 — 후보는 주인만 보고, 주인이 MX 백서 '내 후보' 에서 범위를 다시 고른다.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.auth.errors import AuthError

EVIDENCE_MAX = 20     # 근거 줄 수 상한 — 한 턴의 도구 호출이 많아도 원천 하나가 근거로 넘치지 않게
EXCERPT_MAX = 300     # 근거 발췌 상한 — MX 백서 규칙서의 인용 상한(V10)과 같은 값
TITLE_MAX = 120
PLAT_KEY = "plat:mxwhitepaper"
# 위키 켜짐 신호 — MX 백서는 위키가 꺼진 박스에서 wiki_* 도구를 게이트웨이에 싣지 않는다(MXWP MW-01 — 기동 때 /api/v1/wiki/health 가
# wiki_disabled 면). 그래서 게이트웨이 도구 지도에 이 도구가 있으면 켜짐이다(에이전트 서버 HA-08 과 같은 근원, docs/request-1027 HP-16).
WIKI_TOOL = "wiki_submit_source"


def wiki_on(tool_names) -> bool | None:
    """도구 이름들(게이트웨이 /tools-map) → 켜짐(True) · 꺼짐(False) · 모름(None — 지도를 한 번도 못 읽었다). 충돌 접두가 붙은 이름도 본다."""
    if tool_names is None:
        return None
    return any(n == WIKI_TOOL or n.endswith("_" + WIKI_TOOL) for n in tool_names)


def known_affiliation(request: Any) -> str:
    """이번 요청의 소속 id — 권한표에 없는 id 는 빈 값(진입 토큰 `routes/launch.py` · 게이트웨이용 entitlements 와 같은 규칙)."""
    ents = getattr(request.state, "entitlements", None)
    aff = str(getattr(ents, "affiliation", "") or "")
    access = getattr(request.app.state, "access", None)
    if not aff or access is None:
        return ""
    return aff if aff in access.get().affiliations else ""


def pick_turn(messages: list[dict], text: str) -> tuple[int, str, dict] | None:
    """화면이 보낸 본문과 **글자 그대로 같은** 저장된 답(마지막 것)과 그 앞의 가장 가까운 사람 질문 → (답의 순번, 질문, 답 메시지).

    업로드 알림(meta.upload — 사람이 올려 보낸 결과)은 답이 아니다. 같은 본문의 답이 여럿이면 가장 최근 것을 고른다. 앞에 질문이 없으면
    문답이 아니므로 None."""
    want = (text or "").strip()
    if not want:
        return None
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if m.get("role") != "assistant" or (m.get("meta") or {}).get("upload"):
            continue
        if str(m.get("content") or "").strip() != want:
            continue
        for j in range(i - 1, -1, -1):
            q = str(messages[j].get("content") or "").strip()
            if messages[j].get("role") == "user" and q:
                return i, q, m
        return None
    return None


def _evidence(activity: Any) -> list[dict]:
    """답 메시지의 활동 기록 → 근거 줄. 끝난 호출(결과 미리보기가 있는 줄)만, 같은 것은 한 번. 사람이 올린 문서는 doc, 도구는 tool."""
    out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for a in activity if isinstance(activity, list) else []:
        if not isinstance(a, dict):
            continue
        tool = str(a.get("tool") or "").strip()
        excerpt = " ".join(str(a.get("result_preview") or "").split())
        if not tool or not excerpt:
            continue
        kind, ref = "tool", tool
        if a.get("origin") == "upload":
            kind = "doc"
            try:
                ref = str((json.loads(a.get("detail") or "{}") or {}).get("file") or tool)
            except (ValueError, TypeError, AttributeError):
                ref = tool
        key = (kind, ref, excerpt[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append({"kind": kind, "ref": ref[:200], "excerpt": excerpt[:EXCERPT_MAX]})
        if len(out) >= EVIDENCE_MAX:
            break
    return out


def _iso(ts: Any, now: datetime) -> str:
    """저장소의 시각(초 · 밀리초 · ISO) → 시간대가 있는 ISO. 못 읽으면 지금 — MX 백서는 시간대 없는 시각을 받지 않는다."""
    if isinstance(ts, (int, float)) and ts > 0:
        return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=UTC).isoformat()
    if isinstance(ts, str) and ts.strip():
        try:
            d = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
            return (d if d.tzinfo else d.replace(tzinfo=UTC)).isoformat()
        except ValueError:
            pass
    return now.isoformat()


def qa_envelope(*, cid: str, index: int, question: str, message: dict, owner_email: str, audience: list[str],
                mode: str, outcome: str, model: str | None, now: datetime) -> dict:
    """MX 백서 원천 봉투(mxwp-source/1 · qa) — 모르는 칸은 MX 백서가 거부하므로 계약에 있는 칸만 싣는다.
    질문자 이름은 본문에 넣지 않는다(주인은 owner 칸으로만 — MXWP request §6-3)."""
    return {
        "schema": "mxwp-source/1",
        "kind": "qa",
        "origin": {"system": "hwax-portal", "ref": f"conv:{cid}:{index}"},
        "title": " ".join(question.split())[:TITLE_MAX] or "포털 챗 문답",
        "captured_at": _iso(message.get("ts"), now),
        "owner": {"email": owner_email},
        "audience": audience,
        "sensitivity": "internal",
        "consent": {"by": owner_email, "at": now.isoformat(), "mode": mode},
        "body": {"question": question,
                 "answer": str(message.get("content") or "").strip(),
                 "evidence": _evidence((message.get("meta") or {}).get("activity")),
                 "model": (model or "").strip()[:TITLE_MAX] or "포털 챗",
                 "outcome": outcome},
    }


def audience_for(affiliation: str, mode: str) -> list[str]:
    """보낼 범위 — 소속이 있으면 그 소속, 없으면 후보만 `plat:mxwhitepaper` 를 제안으로(모듈 머리말)."""
    if affiliation:
        return [f"aff:{affiliation}"]
    if mode == "candidate":
        return [PLAT_KEY]
    raise AuthError("소속이 없어 바로 남길 수 없습니다 — '해결됨' 으로 후보를 만들면 MX 백서 '내 후보' 에서 범위를 골라 들일 수 있습니다",
                    status_code=409)


def result_of(out: Any) -> dict:
    """`mcp_call` 의 돌려준 값 → 원천 요약. 게이트웨이 도구는 그대로의 dict 또는 {"result": …} 로 온다."""
    d = out.get("result") if isinstance(out, dict) and isinstance(out.get("result"), dict) else out
    d = d if isinstance(d, dict) else {}
    if not d.get("id"):
        raise AuthError("MX 백서가 원천 번호를 돌려주지 않았습니다 — 들어갔는지 MX 백서 위키에서 확인하세요", status_code=502)
    return {k: d.get(k) for k in ("id", "short", "dedup", "doc_slug", "ingest_state")}
