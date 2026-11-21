# 과제 인사이트 카드의 순수 규칙 — 차수 정규화 · 주장 뽑기 · 카드 id · 리스크 심사 계열 · 범위 판정(docs/project-insight-graph contracts §1 · §4 · §6)
"""여기의 차수 · 주장 · 리스크 심사 계열 규칙은 에이전트 서버(delib_subject.norm_round · risk_family · deliberation.insight_claim)와 같아야 한다 —
시험(tests/test_insights.py)이 형제 리포의 원본과 글자마다 견준다. 확인(SP key 다시 풀기)은 여기 없다 — 에이전트 서버 하나가 한다(PG-19)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# 차수 — 개발 단계 코드 열한 개(사용자 결정 11-02 PG-17). 에이전트 delib_subject.STAGES 와 같다.
STAGES = ("pre", "dv1", "dv2", "dv3", "dvr", "pv1", "pv2", "pv3", "pvr", "pra", "mp")
ROUND_UNKNOWN = "unknown"
# 차수 정규화가 빼는 공백 — 유니코드 White_Space 글자 그대로(에이전트 delib_subject._SPACE_RE · 화면 subject.ts 와 같은 묶음).
_SPACE_RE = re.compile("[\u0009-\u000d \u0085   -     　]+")

PATHS = ("web", "mcp-job", "mcp-workflow")
STATUSES = ("waiting", "draft", "confirmed", "disputed", "withdrawn")
SHARED = ("confirmed", "disputed")          # 범위 토큰으로 남에게 열리는 상태 — 나머지는 주인만
SP_STATES_CARD = ("confirmed", "claimed")   # 카드(또는 기다림 줄)가 되는 주제 상태 — none 은 들이지 않는다(PLAN §3.4)
CLAIM_MAX = 500


def norm_round(v) -> str | None:
    """차수 글 → 코드 · 아니면 None(차수 모름). NFKC · 공백 빼기 · 소문자만 하고 글자 그대로 견준다(PLAN §4.6)."""
    if not isinstance(v, str):
        return None
    s = _SPACE_RE.sub("", unicodedata.normalize("NFKC", v)).lower()
    return s if s in STAGES else None


def risk_family(chair_template, started_by=None) -> bool:
    """리스크 심사가 낳은 심의인가 — 의장 틀 risk-review*(봉인 포함) · 앱이 띄운 패널(started_by=app). 인사이트로 들이지 않는다(PLAN §3.1)."""
    chair = str(chair_template or "").strip().lower()
    return chair.startswith("risk-review") or str(started_by or "").strip().lower() == "app"


# ── 주장 — 에이전트 deliberation.insight_claim(결정문만 줬을 때)과 같은 규칙 ─────────────────────────────────────────────
_SUMMARY_HEAD = "■ 핵심 요약\n"
_PLAIN_HEAD = "■ 쉬운 설명"
_PLAIN_ONE = "### 한마디로"
_BULLET_RE = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s+")


def _clip(text: str, cap: int = CLAIM_MAX) -> str:
    t = (text or "").strip()
    if len(t) <= cap:
        return t
    cut = t.rfind("\n", 0, cap - 1)
    return (t[:cut] if cut >= cap // 2 else t[:cap - 1]).rstrip() + "…"


def _summary_of(decision: str) -> str:
    d = decision or ""
    i = 0
    while d.startswith("■ ", i) and not d.startswith(_SUMMARY_HEAD, i):
        j = d.find("\n\n", i)
        if j < 0:
            return ""
        i = j + 2
    if not d.startswith(_SUMMARY_HEAD, i):
        return ""
    lines = d[i + len(_SUMMARY_HEAD):].split("\n")
    out: list = []
    for k, ln in enumerate(lines):
        if ln.strip():
            out.append(ln.strip())
            continue
        nxt = next((x for x in lines[k + 1:] if x.strip()), "")
        if not out or not _BULLET_RE.match(nxt):
            break
    return "\n".join(out)


def _plain_one(text: str) -> str:
    t = text or ""
    k = t.rfind(_PLAIN_HEAD)
    if k >= 0:
        t = t[k:]
    j = t.find(_PLAIN_ONE)
    if j < 0:
        return ""
    for ln in t[j + len(_PLAIN_ONE):].split("\n")[1:]:
        s = ln.strip()
        if s.startswith("#"):
            return ""
        if s:
            return _BULLET_RE.sub("", s).strip("() ").strip()
    return ""


def claim_of(decision: str) -> tuple[str, str]:
    """결정문 → (주장, 출처 summary · plain · ""). '■ 핵심 요약' 불릿(맨 위 — 코드 표지 문단만 건너뛴다), 없으면 '■ 쉬운 설명' 의 '### 한마디로' 첫 줄.
    결정문 머리를 결론으로 짐작하지 않는다. Claude 워크플로 결정문에는 요약이 없어 쉬운 설명 줄이 된다(contracts §5)."""
    s = _summary_of(decision)
    if s:
        return _clip(s), "summary"
    p = _plain_one(decision)
    if p:
        return _clip(p), "plain"
    return "", ""


# 대화 저장이 긴 글을 나눌 때 다는 머리 — 워크플로(hwax-deliberate.js convChunks · save-delib-conversation.py _chunks)의 '(결정문 i/N)' 와 게이트웨이
# save_conversation 의 '(긴 발언 나눔 k/N)'. 이어 붙이기 전에 뗀다.
_CHUNK_HEAD_RE = re.compile(r"^\((?:결정문|긴 발언 나눔) \d+/\d+\)\n")


def workflow_decision(messages: list) -> str:
    """저장된 워크플로 대화 → 결정문(assistant 메시지를 차례로 이어 붙인다 — 나눈 머리를 떼고)."""
    return "".join(_CHUNK_HEAD_RE.sub("", str(m.get("content") or "")) for m in messages or ()
                   if isinstance(m, dict) and m.get("role") == "assistant")


# ── id — 같은 원천은 같은 id(멱등) ────────────────────────────────────────────────────────────────────────────────
def web_id(cid: str, run_key: str, stage: str) -> str:
    return f"ins:web:{cid}:{run_key}:{stage}"


def job_card_id(job_id: str, stage: str) -> str:
    return f"ins:delib:{job_id}:{stage}"


def wf_id(cid: str) -> str:
    return f"ins:wf:{cid}"


# ── 시야 ───────────────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Viewer:
    """읽는 사람 — 메일(소문자) · 포털 subject · 지금 포털 원장 소속(권한표에 없는 값은 빈 값) · 지금 권한 그룹 · 관리자."""
    email: str
    sub: str = ""
    aff: str = ""
    groups: frozenset = field(default_factory=frozenset)
    admin: bool = False


def owner_of(row: dict, v: Viewer) -> bool:
    return bool(v.email) and str(row.get("owner_email") or "").lower() == v.email


def scope_ok(tokens: list, v: Viewer) -> bool:
    """범위 토큰의 그리고(AND) — user:<메일> · aff:<소속> · plat:<플랫폼> · org. 모르는 토큰이 하나라도 있으면 닫힌 쪽(False)이다. 빈 범위도 닫힌다."""
    toks = [str(t) for t in tokens or ()]
    if not toks or not v.email:
        return False
    for t in toks:
        if t == "org":
            continue
        kind, _, val = t.partition(":")
        if kind == "user" and val.lower() == v.email:
            continue
        if kind == "aff" and val and val == v.aff:
            continue
        if kind == "plat" and val and f"plat:{val}" in v.groups:
            continue
        return False
    return True


def visible(row: dict, v: Viewer) -> tuple[bool, bool]:
    """(보이나, 관리자라서만 보이나). 거둔 카드는 아무에게도(관리자에게도) 안 보인다 — 묘비만 남는다. 주인은 제 카드 전부, 남은 공유 상태 · 범위가
    맞을 때만, 관리자는 그 밖도(범위 밖 읽기 — 부르는 쪽이 감사에 남긴다)."""
    st = row.get("status")
    if st == "withdrawn" or not v.email:
        return False, False
    if owner_of(row, v):
        return True, False
    if st in SHARED and scope_ok(row.get("scope") or [], v):
        return True, False
    if v.admin:
        return True, True
    return False, False


def visible_tasks(scopes: list[dict], v: Viewer) -> set[str]:
    """그 사람에게 보이는 카드가 있는 과제 key 들 — store.task_scopes 의 줄을 시야 규칙(visible)으로 거른다. 관리자 표지는 보지 않는다(범위 밖
    읽기는 과제를 모으거나 근거로 까는 데 쓰지 않는다)."""
    plain = Viewer(email=v.email, sub=v.sub, aff=v.aff, groups=v.groups, admin=False)
    return {str(r["sp_task"]) for r in scopes if r.get("sp_task") and visible(r, plain)[0]}


def plat_tokens(apps: list, policy) -> list:
    """근거 앱(게이트웨이 백엔드 키) → 범위의 plat 토큰. 포털 권한표(gateway: 칸)로 풀고 plat: 키만 단다 — 표에 없는 백엔드 · 게이트웨이 자체(_gateway)는
    토큰이 없다(권한표의 '표에 없는 백엔드는 공개' 와 같다)."""
    keys = policy.keys_for_gateway([a for a in apps or () if a and a != "_gateway"]) if policy is not None else []
    return sorted({k for k in keys if k.startswith("plat:")})


def evidence_known(row: dict) -> bool:
    """근거 범위를 다 아는가 — 조직 공개(org)의 문(PLAN §6.2 '한 칸 다른 자리'). 이 판에서는 근거 표지 · 근거 도구가 없고 앱을 모르는 도구가 없고
    범위를 모르는 입력(도구 없는 근거 글 · 사람 의견 · 앞 회차 요약 · 그림 — 카드 untracked)이 없고 워크플로가 아닌 카드뿐이다(남의 RA 보고서 ·
    리포트 같은 근거의 범위를 알 길이 없다)."""
    card = row.get("card") or {}
    return (row.get("path") != "mcp-workflow" and not card.get("calls") and not card.get("tools")
            and not card.get("apps_unknown") and not card.get("untracked"))


# 앞선 인사이트를 읽는 게이트웨이 도구(insight_find · insight_get)의 머리 — 그 도구를 근거로 쓴 카드는 원래 카드들의 범위를 이어받는다(PLAN §6.2
# 최소 범위 · M3 — 아래 insight_sources · inherit_scope). 어느 카드를 읽었는지 모르면 확인해도 주인만 본다(반대 검토 11-02 의 3).
INSIGHT_TOOL_HEAD = "insight_"
INSIGHT_GET = "insight_get"
CALLS_MAX = 60      # 근거 표지 수 상한 — 엔진 deliberation._INSIGHT_CALLS_MAX 와 같다(시험이 견준다). 차면 뒤 표지가 끊겼을 수 있다
# 호출자가 도구 칸에 적는 꼴(맨 이름 · mcp__<서버>__<도구> · <앱>.<도구> · <앱>:<도구>) — 엔진 deliberation._INSIGHT_EV_TOOL_RE 와 같다(시험이 견준다)
_INSIGHT_NAME_RE = re.compile(r"(?:^|__|[.:/])" + INSIGHT_TOOL_HEAD)
_INSIGHT_GET_RE = re.compile(r"(?:^|__|[.:/])" + INSIGHT_GET + "$")
# 근거 표지의 인자에서 카드 id — JSON 글('{"id": "ins:…"}')과 엔진이 사전을 글로 옮긴 꼴("{'id': 'ins:…'}") 둘 다 읽는다
_INSIGHT_ID_RE = re.compile(r"""^\s*\{\s*['"]id['"]\s*:\s*(['"])(ins:(?:web|delib|wf):[^'"\\]{1,290})\1\s*\}\s*$""")


def insight_tool(name) -> bool:
    """도구 이름이 과제 인사이트 도구인가(머리 insight_ — 호출자가 적는 여러 꼴)."""
    return isinstance(name, str) and bool(_INSIGHT_NAME_RE.search(name.strip().lower()))


def insight_derived(row: dict) -> bool:
    """앞선 인사이트를 근거로 썼나 — 근거 도구 · 표지에 insight_ 도구가 있다."""
    card = row.get("card") or {}
    names = [*(card.get("tools") or ()), *(c.get("tool") for c in card.get("calls") or () if isinstance(c, dict))]
    return any(insight_tool(n) for n in names)


def insight_sources(row: dict) -> tuple[list[str] | None, str]:
    """앞선 인사이트를 근거로 쓴 카드가 읽은 카드 id 들 — (id 목록, "") 또는 (None, 까닭). 읽은 카드를 **다** 알 때만 목록을 낸다(틀릴 거면 닫힌
    쪽으로) — 인사이트 표지가 전부 insight_get 이고 인자가 카드 id 하나일 때다. 찾기 결과를 묶음째 넘겼거나(insight_find) · 표지가 상한에서
    끊겼거나 · 도구 이름만 있고 표지가 없으면(같은 심의의 앞 단이 넘긴 것) 모른다."""
    card = row.get("card") or {}
    calls = [c for c in card.get("calls") or () if isinstance(c, dict)]
    if len(calls) >= CALLS_MAX:
        return None, f"근거 표지가 상한({CALLS_MAX}건)에 차 읽은 카드를 다 알 수 없다"
    ids: list[str] = []
    for c in calls:
        if not insight_tool(c.get("tool")):
            continue
        m = _INSIGHT_ID_RE.match(str(c.get("args") or ""))
        if m is None or not _INSIGHT_GET_RE.search(str(c.get("tool")).strip().lower()):
            return None, "앞선 인사이트를 카드 하나씩(insight_get + 카드 id)이 아닌 꼴로 넘겨 어느 카드를 읽었는지 알 수 없다"
        if m.group(2) not in ids:
            ids.append(m.group(2))
    if not ids:
        return None, "앞선 인사이트를 근거로 썼다는 표지만 있고 어느 카드인지 적힌 근거 표지가 없다"
    return ids, ""


def inherit_scope(base: list, sources: list[dict | None], owner_email: str) -> tuple[list, str]:
    """앞선 인사이트를 근거로 쓴 카드의 확인 범위 — (범위 토큰, 까닭). base 는 그 카드 제 범위([aff:<주인의 지금 소속>] + 근거 앱의 plat 토큰),
    sources 는 읽은 카드들의 원장 행이다(없는 id 는 None). PLAN §6.2 최소 범위 — 범위는 기댄 근거들의 범위 토큰을 다 담는다(org 는 그리고에서
    아무것도 더하지 않는다). 읽은 카드가 없어졌거나 거뒀거나 아직 주인만 보는 것이면, 또는 서로 다른 소속 · 사람이 섞여 만족할 사람이 없으면 넓히지
    못하고 주인만 본다."""
    mine = [f"user:{owner_email}"]
    toks: set = {str(t) for t in base or ()}
    if not toks or any(t.startswith("user:") for t in toks):
        return mine, ""          # 제 범위부터 주인만이다(소속 없음) — 부른 쪽이 그 까닭을 단다
    for r in sources:
        if r is None or r.get("status") not in SHARED:
            return mine, "근거로 쓴 앞선 인사이트 가운데 지금은 없거나(거둠) 주인만 보는 카드가 있어 그 범위를 이어받지 못한다 — 주인만 본다"
        got = {str(t) for t in r.get("scope") or ()}
        if not got:
            return mine, "근거로 쓴 앞선 인사이트의 범위를 읽지 못해 주인만 본다"
        toks |= got
    toks.discard("org")
    affs = sorted(t for t in toks if t.startswith("aff:"))
    if len(affs) != 1 or any(t.startswith("user:") for t in toks):
        return mine, "근거로 쓴 앞선 인사이트의 범위(소속 · 사람)가 이 카드의 범위와 섞여 함께 볼 수 있는 사람이 없다 — 주인만 본다"
    return [affs[0], *sorted(t for t in toks if not t.startswith("aff:"))], ""


# ── 같은 결론 묶기(PLAN §8 중복) — 같은 (과제, 차수) 칸에서 정규화한 주장 글이 같은 카드. 묶어 보일 뿐 합치지 않는다 ──────────────────────────
def claim_key(claim) -> str:
    """주장 글의 견줄 꼴 — NFKC · 소문자 · 공백 덩어리 하나로. 빈 글은 빈 꼴(묶지 않는다)."""
    if not isinstance(claim, str):
        return ""
    return " ".join(_SPACE_RE.sub(" ", unicodedata.normalize("NFKC", claim)).lower().split())


def same_claims(rows: list[dict]) -> dict[str, list[str]]:
    """{카드 id: 같은 결론인 다른 카드 id 들} — 받은 행들(읽는 사람이 볼 수 있는 같은 칸의 카드) 안에서만 센다. 둘 이상일 때만 싣는다."""
    by: dict[str, list[str]] = {}
    for r in rows:
        k = claim_key(r.get("claim"))
        if k:
            by.setdefault(k, []).append(r["id"])
    return {i: [x for x in ids if x != i] for ids in by.values() if len(ids) > 1 for i in ids}
