# 과제 인사이트 다시 쓰기 — 웹 일반 심의 시작에 같은 (과제, 차수)의 앞선 인사이트를 근거 항목으로 깐다(docs/project-insight-graph PLAN §7.1 · M3)
"""포털이 심의 시작을 중계할 때(/agent/chat) 한 번 돈다. 엔진은 포털을 사람 대신 읽지 않는다(PG-8) — 웹은 그 사람을 아는 포털이 깐다.

  · 확인된 주제만 — 브라우저가 고른 주제를 에이전트 서버의 같은 풀이(POST /deliberate/subject/confirm — 확인하는 쪽은 그 서버 하나, PG-19)로 그 사람
    PAT 로 먼저 확인한다. 주제가 없거나 · 확인되지 않았거나 · 볼 수 있는 카드가 없으면 아무것도 넣지 않는다(에이전트 서버로 가는 요청이 종전과
    바이트까지 같다). 볼 수 있는 카드가 없는 과제는 확인도 부르지 않는다.
  · 같은 (과제, 차수) 칸만 — 차수 코드가 글자 그대로 같은 카드만 깐다. 다른 차수 · 차수 모름 칸의 것은 깔지 않고 그 사람에게 수만 알린다. 이 심의의
    차수를 모르면 아무것도 깔지 않는다(차수 모름 칸은 여러 차수가 섞인 칸이다 — PG-17).
  · 산출물 범위 안의 것만 — 깐 근거는 새 심의의 산출물(RA 보고서 · 위키 원천)로 다시 퍼진다. 그 독자가 모두 볼 수 있는 카드만 깐다 — 확인 · 반박
    상태이고 범위 토큰이 시작한 사람의 소속(aff:) · 조직(org)뿐인 것. 보고서가 저장될 RA 작업 공간이 개인 공간 · **부서**면 독자를 같은 소속으로
    본다(사용자 결정 11-22 — docs/leftovers-1121 L21-17 ③, RA 위임 박스의 기본 부서 포함 — ra_workspace_kind). TF · 시스템 · 가상 공간이거나 알 수 없으면 조직으로
    친다(조직 공개 카드만). plat: 가 붙은 카드 · 주인만 보는 카드는 깔지 않는다. 관리자의 '범위 밖 읽기' 로는 깔지 않는다.
  · 리스크 심사 계열(의장 risk-review* · 앱이 띄운 패널)에는 깔지 않는다(D-18 — 엔진도 한 번 더 뺀다). 봉인 심의(sealed)에도 깔지 않는다 —
    호출자가 준 자료만으로 도는 심의다. 기준일(as_of)이 있으면 그 날 뒤에 생기거나 주장이 고쳐진 카드는 깔지 않고 수를 알린다.
  · 표지 — 항목마다 '앞선 인사이트 — 검증 대상, 독립 근거 아님' 과 출처 · 상태 · 판. 도구 칸은 insight_get, 인자는 카드 id 다 — 새 심의가 낳는 카드가
    그 id 로 원래 카드들의 범위를 이어받는다(cards.inherit_scope).
알림(깐 수 · 깔지 않은 수)은 시작한 사람의 화면에만 간다 — 근거에 싣지 않는다(좁은 카드가 있다는 것이 넓은 산출물로 가지 않게, PLAN §6.3)."""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from datetime import datetime, timedelta, timezone

from app.insights import cards as C
from app.insights import intake, lineage

logger = logging.getLogger(__name__)

FEAT = "feat:insights"
TOOL = C.INSIGHT_GET
SOURCE = "앞선 인사이트 — 검증 대상, 독립 근거 아님"
LAY_MAX = 20            # 한 심의에 까는 카드 수(최근 것부터) — 넘는 것은 수만 알린다
EVID_ITEMS = 120        # 호출자 근거 항목 상한 — DelibOpts.evidence 의 상한 · 엔진 _EVID_ITEMS 와 같다(시험이 견준다)
CALL_TIMEOUT_S = lineage.CALL_TIMEOUT_S   # 깔기의 게이트웨이 호출 하나(옛 key · 개정 줄) — 갈래 기한(lineage.READ_BUDGET_S) 안에서 먼저 걸린다
LAY_TIMEOUT_S = 60.0    # 깔기 전체 — 넘기면 깔지 않고 심의를 연다(중계가 lineage.bounded 로 건다 — 늦은 호출의 뒤처리를 기다리지 않는다)
_KST = timezone(timedelta(hours=9))
_PATH = {"web": "웹 심의", "mcp-job": "MCP 심의", "mcp-workflow": "Claude 워크플로"}
_STATUS = {"confirmed": "확인", "disputed": "반박 있음"}
_NOTES_MAX, _NOTE_CHARS = 3, 200


@dataclasses.dataclass(frozen=True)
class Laid:
    """깔 근거 항목 · 깐 카드 id · 그 사람에게 보일 알림 글 · 수."""
    evidence: list
    ids: list
    notice: str
    counts: dict


# 독자를 같은 소속으로 보는 RA 작업 공간의 종류(RA workspaces.models.WorkspaceKind) — 개인 공간과 부서(조직도의 본부 · 팀 — kind org). TF(부서를
# 가로질러 뽑은 사람들) · 시스템(조직 단위로 여는 게시판) · 가상(모아 보기) 공간은 조직으로 친다.
RA_AFF_KINDS = ("personal", "org")


def output_audience(*, save_report, append_to_report_id, ra_kind: str | None) -> str:
    """새 심의의 산출물을 읽을 사람의 윗한계 — 'aff'(시작한 사람의 소속 안) · 'org'(조직으로 친다, PLAN §7.1). ra_kind 는 새 보고서가 저장될 RA 작업
    공간의 종류다(못 알아냈으면 None). 보고서를 저장하지 않거나(save_report=0), 그 작업 공간이 개인 공간 · 부서면 소속 안이다 — **부서 작업 공간의
    독자는 같은 소속으로 본다**(사용자 결정 11-22 · L21-17 ③ — RA 부서는 포털 소속에서 매핑된다. 감수한 것 — RA 부서 구성이 포털 소속과 어긋난
    사람은 소속 범위 인사이트의 요약을 보고서에서 볼 수 있다). TF · 시스템 · 가상 공간, 종류를 모르는 공간, 있는 보고서에 덧붙이기
    (append_to_report_id — 그 보고서가 어느 공간에 있는지 모른다)는 조직으로 친다."""
    if save_report == 0:
        return "aff"
    if append_to_report_id:
        return "org"
    return "aff" if ra_kind in RA_AFF_KINDS else "org"


def ra_workspace_kind(me, chosen: str = "", *, sso: bool = False) -> str | None:
    """새 심의의 보고서가 갈 수 있는 RA 작업 공간의 종류 — RA /api/me 의 답(memberships 마다 workspace_kind · home_workspace_slug)에서. 알 수 없으면
    None 이다(깔기는 조직으로 친다). 보고서가 갈 수 있는 공간은 둘이다.
      · chosen — 그 사람이 포털 'Report Archive 연결' 에 저장한 공간. 등록한 토큰으로 부르는 박스는 게이트웨이 · 포털이 이것을 X-Workspace-Slug 로 싣는다.
      · RA 의 기본 공간 — 부서 머리 없이 온 개인 토큰에 RA 가 고른다(RA shared/auth.py _default_workspace_for_token — 홈 부서 → 첫 조직 멤버십 →
        개인 공간). chosen 이 비었을 때와, 위임 박스(sso — RA_SSO_SECRET: 게이트웨이가 부서 머리를 떼고 부른다)의 엔진 저장이 이 공간으로 간다.
    위임 박스에서 chosen 이 남아 있으면 포털이 직접 부르는 저장은 그 공간으로 간다 — 두 공간을 다 보고, 부서 · 개인(RA_AFF_KINDS)이 아닌 것이 하나라도
    있으면 그 종류(모르면 None)를 낸다. 기본 공간은 /api/me 가 주는 것만으로 다 알 수 없다(멤버십의 차례 · 보관 여부가 없다) — 홈 부서가 멤버십에
    있으면 그 종류, 홈이 없으면 개인 · 가상이 아닌 멤버십이 없을 때 개인, 전부 부서일 때 부서이고, 그 밖(TF · 시스템이 섞였다 · 홈이 멤버십에 없다)은
    모른다."""
    ms = me.get("memberships") if isinstance(me, dict) else None
    if not isinstance(ms, list):
        return None
    kinds: dict = {}
    for m in ms:
        slug = str(m.get("workspace_slug") or "").strip() if isinstance(m, dict) else ""
        if slug:
            kinds[slug] = str(m.get("workspace_kind") or "").strip() or ("personal" if slug.startswith("personal-") else "")
    chosen = (chosen or "").strip()
    got: list = []
    if sso or not chosen:
        home = str(me.get("home_workspace_slug") or "").strip()
        rest = [k for k in kinds.values() if k not in ("personal", "virtual")]
        got.append((kinds.get(home) or None) if home else "personal" if not rest else "org" if all(k == "org" for k in rest) else None)
    if chosen:
        got.append(kinds.get(chosen) or None)
    return next((k for k in got if k not in RA_AFF_KINDS), got[-1])


def as_of_cutoff(as_of) -> int | None:
    """기준일('YYYY-MM-DD') → 그 날의 끝(KST) epoch 초 · 기준일이 없으면 None. 못 읽는 값은 0 이다 — 어느 카드도 그 앞이 아니다(닫힌 쪽)."""
    if not as_of:
        return None
    try:
        day = datetime.strptime(str(as_of), "%Y-%m-%d").replace(tzinfo=_KST)
    except ValueError:
        return 0
    return int((day + timedelta(days=1)).timestamp()) - 1


def evidence_marks(evidence) -> tuple[set, set]:
    """호출자가 이미 넣은 근거에서 (카드 하나를 읽은 항목의 카드 id 들, 쓰인 key 들) — 같은 카드를 또 깔지 않고 key 가 겹치지 않게 한다."""
    ids, keys = set(), set()
    for e in evidence or ():
        if not isinstance(e, dict):
            continue
        if isinstance(e.get("key"), str) and e["key"]:
            keys.add(e["key"])
        cid = C.insight_card_id(e.get("tool"), e.get("args"))
        if cid:
            ids.add(cid)
    return ids, keys


def layable_scope(tokens: list, viewer: C.Viewer, audience: str) -> bool:
    """카드의 범위 토큰이 산출물의 독자 안인가 — 조직(org), 그리고 독자가 소속 안일 때의 그 소속(aff:<시작한 사람의 소속>)뿐이어야 한다."""
    toks = [str(t) for t in tokens or ()]
    allowed = {"org"} | ({f"aff:{viewer.aff}"} if audience == "aff" and viewer.aff else set())
    return bool(toks) and all(t in allowed for t in toks)


_COUNTS = ("laid", "other_round", "unknown_round", "no_round", "out_of_scope", "over", "after_as_of", "already")
_SAME_TALK_PATHS = ("web", "mcp-workflow")      # source_id 가 포털 대화 id 인 길(MCP 잡의 source_id 는 잡 id 다)


def pick(rows: list[dict], *, viewer: C.Viewer, round_code: str | None, audience: str, room: int = LAY_MAX,
         skip_source: str | None = None, skip_ids=(), cutoff: int | None = None) -> tuple[list[dict], dict]:
    """(깔 카드들 — 최근 것부터, 수). rows 는 그 과제(옛 key 포함)의 원장 행이다. 읽는 사람이 관리자가 아니라고 보고 거른 뒤에 센다 — 보이지 않는
    카드는 수에도 없다. 수 — laid · other_round(다른 차수) · unknown_round(차수 모름 칸) · no_round(이 심의에 차수가 없어 깔지 않은 것) ·
    out_of_scope(같은 칸이지만 초안 · 주인만 · 플랫폼 범위 · 산출물 독자 밖) · already(호출자가 이미 근거로 넣은 카드 — skip_ids) · over(같은 칸이고
    깔 수 있지만 상한 밖) · after_as_of(기준일 cutoff 뒤에 생기거나 주장이 고쳐진 카드). skip_source 는 이 심의의 대화 id 다 — 같은 대화가 낳은
    카드(웹 심의의 앞 회차 · 그 대화로 저장된 워크플로 심의)는 깔지도 세지도 않는다(이어하기가 앞 결정문을 요약으로 이미 넘긴다 — 제 결론을 앞선
    인사이트로 되읽지 않게)."""
    v = dataclasses.replace(viewer, admin=False)
    n = dict.fromkeys(_COUNTS, 0)
    out: list[dict] = []
    for r in sorted(rows, key=lambda x: (-int(x.get("created_at") or 0), str(x.get("id")))):
        if r.get("status") == "waiting" or not C.visible(r, v)[0]:
            continue
        if skip_source and r.get("path") in _SAME_TALK_PATHS and r.get("source_id") == skip_source:
            continue
        rnd = r.get("round") if r.get("round") in C.STAGES else None
        if cutoff is not None and max(int(r.get("created_at") or 0), int(r.get("claim_edited_at") or 0)) > cutoff:
            n["after_as_of"] += 1
        elif round_code is None:
            n["no_round"] += 1
        elif rnd is None:
            n["unknown_round"] += 1
        elif rnd != round_code:
            n["other_round"] += 1
        elif r.get("status") not in C.SHARED or not layable_scope(r.get("scope") or [], v, audience):
            n["out_of_scope"] += 1
        elif r["id"] in skip_ids:
            n["already"] += 1
        elif len(out) >= max(0, room):
            n["over"] += 1
        else:
            out.append(r)
    n["laid"] = len(out)
    return out, n


def _versions(card_subject: dict, now_subject: dict) -> str:
    """판 줄 — 카드의 설계 자료(그때의 판)를 이 심의의 주제와 견준다. 같은 열쇠가 둘 다에 있을 때만 같다 · 다르다를 말한다."""
    now = {(a.get("kind"), a.get("id")): a.get("rev") for a in (now_subject or {}).get("artifacts") or () if isinstance(a, dict)}
    parts = []
    for a in (card_subject or {}).get("artifacts") or ():
        if not isinstance(a, dict) or not a.get("id"):
            continue
        k, rev = (a.get("kind"), a.get("id")), a.get("rev")
        head = f"{a.get('kind')} {a.get('id')}" + (f"(그때의 판 {rev})" if rev else "(판 표지 없음)")
        if k not in now:
            parts.append(head + " — 이 심의의 주제에 없는 설계 자료")
        elif rev and now[k]:
            parts.append(head + (" — 이 심의와 같은 판" if rev == now[k] else f" — 이 심의의 판({now[k]})과 다르다"))
        else:
            parts.append(head + " — 판을 견줄 수 없다")
    return " · ".join(parts) if parts else "설계 자료 없음"


def evidence_item(row: dict, n: int, *, now_subject: dict, stale: dict | None = None, dispute_notes: list | None = None) -> dict:
    """카드 하나 → 호출자 근거 항목 하나({key, source, tool, args, result}). 표지 · 출처 · 상태 · 판 · 표결 · 주장."""
    card, subj = row.get("card") or {}, row.get("subject") or {}
    t = card.get("tally") or {}
    when = datetime.fromtimestamp(int(row.get("created_at") or 0), tz=_KST).strftime("%Y-%m-%d")
    origin = [str(row.get("owner_email") or ""), when, _PATH.get(row.get("path"), str(row.get("path"))), f"단 {row.get('stage')}"]
    if card.get("report_id") is not None:
        origin.append(f"RA 보고서 #{card['report_id']}")
    state = _STATUS.get(row.get("status"), str(row.get("status")))
    if row.get("claim_edited_by"):
        state += " · 주장은 사람이 고쳤다"
    lines = [f"[{SOURCE}]", "출처: " + " · ".join(origin) + f" · 카드 {row['id']}", f"상태: {state}"]
    for note in (dispute_notes or [])[:_NOTES_MAX]:
        if note:
            lines.append(f"반박 메모: {str(note)[:_NOTE_CHARS]}")
    lines.append("판: " + _versions(subj, now_subject) + (f" · {stale['say']}" if stale else ""))
    lines.append(f"표결: 동의 {int(t.get('agree') or 0)} · 조건부 {int(t.get('conditional') or 0)} · 반대 {int(t.get('oppose') or 0)} · "
                 f"미표명 {int(t.get('abstain') or 0)}")
    lines.append("주장:\n" + (row.get("claim") or "(주장 글이 없다 — 결정문은 RA 보고서 · 원래 심의에 있다)"))
    return {"key": f"ins-{n}", "source": SOURCE, "tool": TOOL, "args": json.dumps({"id": row["id"]}, ensure_ascii=False),
            "result": "\n".join(lines)}


def notice_of(n: dict, *, key: str, round_code: str | None, audience: str) -> str:
    """그 사람의 화면에 보일 한 줄 — 깐 수와 깔지 않은 수. 볼 수 있는 것만 센 수다."""
    cell = f"과제 「{key}」 · 차수 {round_code or '모름'}"
    skipped = []
    if n["no_round"]:
        skipped.append(f"이 심의에 차수가 없어 {n['no_round']}건(차수 모름 칸은 어느 차수에도 섞지 않는다)")
    if n["other_round"]:
        skipped.append(f"다른 차수 {n['other_round']}건")
    if n["unknown_round"]:
        skipped.append(f"차수 모름 {n['unknown_round']}건")
    if n["out_of_scope"]:
        skipped.append(f"같은 칸이지만 범위 밖 {n['out_of_scope']}건(초안 · 주인만 · 플랫폼 권한이 붙은 것"
                       + (" · 이 심의의 보고서가 저장될 Report Archive 작업 공간이 부서 · 개인 공간이 아니거나 알 수 없어 조직에 연 것만 깐다"
                          if audience == "org" else "")
                       + ")")
    if n["after_as_of"]:
        skipped.append(f"기준일 뒤에 생기거나 고쳐진 {n['after_as_of']}건")
    if n["already"]:
        skipped.append(f"이미 근거에 든 {n['already']}건")
    if n["over"]:
        skipped.append(f"상한 밖 {n['over']}건")
    head = (f"앞선 인사이트 {n['laid']}건을 근거로 실었다({cell} — 검증 대상이고 독립 근거가 아니다)" if n["laid"]
            else f"앞선 인사이트를 근거로 싣지 않았다({cell})")
    return head + (" · 싣지 않은 것 — " + " · ".join(skipped) + " — 과제 인사이트 화면에서 본다" if skipped else "")


def subject_key(viewer: C.Viewer | None, pat: str | None, opts: dict) -> str:
    """이 심의 시작이 깔기의 대상이면 그 주제의 과제 key, 아니면 빈 글 — 원장도 망도 보지 않는 판정이다. 과제를 단 일반 심의이고, 그 사람에게
    과제 인사이트 권한과 사람 자격(PAT)이 있을 때만이다. 리스크 심사 계열은 대상이 아니다(D-18). 봉인 심의(sealed)도 대상이 아니다 — 호출자가 준
    자료만으로 도는 소급 검증에 오늘의 원장을 깔지 않는다(반대 검토 11-22 M2)."""
    subj = opts.get("subject") if isinstance(opts.get("subject"), dict) else None
    key = str((subj or {}).get("sp_task") or "").strip()
    if (viewer is None or not key or not pat or not viewer.email or FEAT not in viewer.groups or opts.get("sealed")
            or C.risk_family(opts.get("chair_template"), opts.get("started_by"))):
        return ""
    return key


async def lay(*, store, settings, principal, viewer: C.Viewer, pat: str, opts: dict, tasks: set, ra_kind,
              conversation_id: str | None = None) -> Laid | None:
    """웹 심의 시작의 깔기 — 깔 것 · 알릴 것이 없으면 None(요청은 종전 그대로다). opts 는 delib_opts 를 옮긴 사전(None 인 칸은 빠진 것), tasks 는
    그 사람에게 보이는 카드가 있는 과제 key 들(cards.visible_tasks — 비면 부르지 않는다), ra_kind 는 새 보고서가 저장될 RA 작업 공간의 종류를 읽는
    비동기 함수다(확인된 주제에 볼 수 있는 카드가 있을 때만 부른다 · 못 알아내면 None). subject_key 가 참인 요청에만 부른다."""
    subj = opts["subject"]
    key = subject_key(viewer, pat, opts)
    if store is None or not key or not tasks:
        return None
    call = lineage.caller(settings, pat, timeout=CALL_TIMEOUT_S)
    old, _why = await lineage.old_keys(call, key, tasks)
    fam = [key, *old]
    if not tasks.intersection(fam):
        return None                      # 이 과제(옛 key 포함)에는 볼 수 있는 카드가 없다 — 확인도 부르지 않는다
    rec, _why = await intake.confirm_async(settings, subject=subj, principal=principal, pat=pat, chair_template=opts.get("chair_template"))
    if not isinstance(rec, dict) or rec.get("sp_state") != "confirmed" or rec.get("sp_task") != key:
        return None                      # 확인되지 않은 주제 — 깔지 않는다(에이전트 서버도 같은 풀이로 주장으로 둔다)
    round_code = C.norm_round(rec.get("round") or "")
    rows = [r for k in fam for r in await asyncio.to_thread(store.rows, sp_task=k, viewer=viewer.email)]
    # RA 는 보고서를 새로 저장할 때만 묻는다 — 저장하지 않거나 있는 보고서에 덧붙이면 그 공간의 종류가 판정을 바꾸지 않는다
    asks_ra = opts.get("save_report") != 0 and not opts.get("append_to_report_id")
    audience = output_audience(save_report=opts.get("save_report"), append_to_report_id=opts.get("append_to_report_id"),
                               ra_kind=(await ra_kind()) if asks_ra else None)
    have_ids, have_keys = evidence_marks(opts.get("evidence"))
    room = min(LAY_MAX, EVID_ITEMS - len(opts.get("evidence") or []))
    picked, n = pick(rows, viewer=viewer, round_code=round_code, audience=audience, room=room, skip_source=conversation_id,
                     skip_ids=have_ids, cutoff=as_of_cutoff(opts.get("as_of")))
    if not any(n.values()):
        return None
    stale: dict = {}
    notes: dict = {}
    if picked:
        ids = lineage.mcad_ids(picked)
        revs = await lineage.mcad_revisions(call, ids) if ids else {}
        # 판 줄에는 판정 낱말만 싣는다(lineage.public) — 뒤 판의 이름 · id 는 StepForge 권한으로 읽은 것이라 근거로 퍼뜨리지 않는다
        stale = {r["id"]: lineage.public(lineage.card_stale(r.get("subject") or {}, revs)) for r in picked}
        for lk in await asyncio.to_thread(store.links, [r["id"] for r in picked]):
            if lk.get("kind") == "disputes" and lk.get("note"):
                notes.setdefault(lk["to_id"], []).append(lk["note"])
    free = (k for k in range(1, EVID_ITEMS + LAY_MAX + 2) if f"ins-{k}" not in have_keys)     # 호출자가 쓴 key 와 겹치지 않는 번호
    items = [evidence_item(r, next(free), now_subject=rec, stale=stale.get(r["id"]), dispute_notes=notes.get(r["id"])) for r in picked]
    return Laid(evidence=items, ids=[r["id"] for r in picked],
                notice=notice_of(n, key=key, round_code=round_code, audience=audience), counts=n)
