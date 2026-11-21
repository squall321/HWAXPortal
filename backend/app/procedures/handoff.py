# 절차 실행의 단계 기록을 심의 근거 · 챗 대화로 옮기는 다리(docs/procedures W-114 · W-115)
"""실행 원장(`run_steps`)의 글을 **읽기만** 한다 — 새로 가리거나 풀지 않는다. 원장은 넣을 때 이미 확인 토큰 · 보내기만 한 값을 가렸으므로
(runner `_mask_publish_token` · `_redact`, from_chat) 여기서 나가는 글도 가려진 채다.

근거는 도구가 낸 날것이다 — 결론을 지어 넣지 않는다(심의 헌법 P1). 다만 **그 호출이 어떻게 끝났는지**는 날것의 일부다. 실패한 단계 · 실행 여부를
모르는 단계를 빼거나 표지 없이 실으면 좌석은 그 절차가 통째로 된 것으로 읽는다. 그래서 결과 머리에 한 줄로 적는다.

상한은 계획서(S8) 그대로다 — 40건 · 결과 150,000자 · 인자 1,200자. 넘친 것은 조용히 버리지 않고 근거 안에서 말한다(엔진은 받은 것만 안다).
"""
import json

from app.auth.errors import AuthError
from app.procedures import judge as J
from app.procedures.store import PREVIEW

EVID_ITEMS = 40
EVID_RESULT_MAX = 150_000
EVID_ARGS_MAX = 1_200
# 챗으로 가져가는 대화의 결과는 줄인 판이다(사용자 결정 10-31 A15 (B) — 전문은 실행 원장에 있다). 대화 한 건의 meta 가 브라우저 사본 · 다음 턴
# 이력으로 통째로 오간다.
CHAT_RESULT_MAX = 20_000
CHAT_PREVIEW = 220          # 활동 패널의 미리보기 길이(에이전트 서버가 내는 것과 같은 몫)
SOURCE_TITLE_MAX = 120
NOTICE_SOURCE = "절차 실행 근거 건수 초과"

_STATE_KO = {"done": "완료", "failed": "실패", "unknown": "실행 여부 모름", "pending": "대기", "running": "도는 중",
             "skipped": "건너뜀"}


def _clip(text: str, limit: int, what: str) -> str:
    """상한을 넘으면 앞을 남기고 **줄였다고 말한다** — 꼬리 글까지 합쳐 상한 안이다."""
    if len(text) <= limit:
        return text
    tail = f"\n…[{what} 원문 {len(text):,}자 가운데 앞부분만 실었다 — 전문은 절차 실행 원장에 있다]"
    return text[:max(0, limit - len(tail))] + tail


def _args_text(args) -> str:
    """단계 인자 — 챗 기록에서 온 실행은 글(`_text`), 실행기가 돌린 실행은 치환된 JSON 이다."""
    if isinstance(args, dict) and set(args) == {"_text"}:
        return str(args["_text"] or "")
    if not args:
        return ""
    return json.dumps(args, ensure_ascii=False, sort_keys=True)


def _title(run: dict) -> str:
    return (str(run.get("title") or "").strip() or f"실행 {str(run.get('id') or '')[:8]}")[:SOURCE_TITLE_MAX]


def _records(store, run: dict, result_max: int) -> tuple[list[dict], list[dict]]:
    """(부른 단계들, 부르지 않은 단계들). 부른 단계 = 결과가 원장에 있거나 실패 · 실행 여부 모름으로 끝난 단계다.
    계획 모드의 단계(안 불렀다) · 확인 카드에서 멈춘 단계(아직 안 나갔다) · 도는 단계는 조회 결과가 아니다."""
    called, not_called = [], []
    title = _title(run)
    for s in run.get("steps") or []:
        ix, state = s["ix"], s["state"]
        body = store.step_result(run["id"], ix) if s.get("result_bytes") is not None else None
        if body is None and state not in ("failed", "unknown"):
            not_called.append({"ix": ix, "tool": s["tool"], "state": state, "stage": s.get("stage")})
            continue
        head = []
        tag = ""
        if s.get("truncated") and body is not None:
            # 이 결과는 전문이 아니다 — 원장이 2MB 를 넘는 결과는 앞머리만 쥔다(store RESULT_MAX)
            head.append(f"[원장에 앞 {PREVIEW:,}자만 남은 결과 — 원문 {int(s.get('result_bytes') or 0):,}바이트]")
        if state == "failed":
            head.append(f"[실패한 단계 — {s.get('error') or s.get('stage') or '사유를 못 받았다'}]")
            tag = "(실패)"
        elif state == "unknown":
            head.append(f"[실행 여부를 모르는 단계 — {s.get('error') or s.get('stage') or '성패를 못 받았다'}]")
            tag = "(실행 여부 모름)"
        elif state == "pending":
            head.append("[사람의 고르기 · 확인을 기다리는 단계]")
        elif state == "skipped":
            head.append(f"[건너뛴 단계 — {(s.get('notes') or {}).get('select') or s.get('stage') or '사유 없음'}]")
        warns = J.warn_labels(s.get("notes"))
        if warns:
            head.append(f"[경고 — {' · '.join(warns)}]")
        text = "\n".join([*head, body or ""]).strip("\n") if head else (body or "")
        called.append({
            "ix": ix, "state": state, "ok": True if state == "done" else False if state == "failed" else None,
            "source": f"절차 실행 {title}#{ix + 1}{tag}",
            "tool": str(s["tool"])[:80],
            "args": _clip(_args_text(s.get("args")), EVID_ARGS_MAX, "인자"),
            "result": _clip(text, result_max, "결과"),
            "ms": s.get("duration_ms"), "started_at": s.get("started_at"),
        })
    return called, not_called


def run_evidence(store, run: dict) -> dict:
    """실행 → `{evidence: [{source, tool, args, result}], brief, called, dropped, not_called}`. `brief` 는 실은 단계마다의 상태 · 결과 길이다
    (화면의 미리보기 — 결과 본문은 없다).

    `evidence` 는 심의의 사전 근거 칸(`delib_opts.evidence`)에 그대로 들어가는 꼴이다. 40건을 넘으면 앞 39건과 '넘쳤다' 는 알림 한 건이다 —
    뒤쪽을 말없이 버리면 좌석은 앞 단계만 보고 절차 전체를 본 줄 안다.
    """
    called, not_called = _records(store, run, EVID_RESULT_MAX)
    items = [{k: r[k] for k in ("source", "tool", "args", "result")} for r in called]
    dropped = 0
    if len(items) > EVID_ITEMS:
        keep = EVID_ITEMS - 1
        dropped = len(items) - keep
        left = ", ".join(f"{r['ix'] + 1}단계 {r['tool']}" for r in called[keep:keep + 8])
        items = items[:keep] + [{
            "source": NOTICE_SOURCE, "tool": "", "args": "",
            "result": (f"이 절차 실행의 단계 기록 {len(called)}건 가운데 앞 {keep}건만 실었다 — 뒤 {dropped}건({left}"
                       f"{' …' if dropped > 8 else ''})은 상한({EVID_ITEMS}건)을 넘겨 싣지 않았다. 전문은 절차 실행 원장에 있다.")}]
    brief = [{"ix": r["ix"], "tool": r["tool"], "state": r["state"], "chars": len(r["result"])}
             for r in called[:len(called) - dropped]]
    return {"evidence": items, "brief": brief, "called": len(called), "dropped": dropped, "not_called": not_called}


def refuse_unfinished(run: dict) -> None:
    """도는 실행은 넘기지 않는다 — 원장이 아직 바뀐다. 끝나거나 멈춘(확인 대기 · 실패 · 중단) 실행만 넘긴다."""
    if run.get("state") in ("queued", "running"):
        raise AuthError("아직 도는 실행입니다 — 끝나거나 멈춘 뒤에 넘깁니다", status_code=409)


def evidence_or_refuse(store, run: dict) -> dict:
    """`run_evidence` + 넘길 수 없는 실행의 거절(도는 실행 409 · 부른 단계가 없는 실행 422). 심의 다리와 미리보기가 같은 판정을 쓴다."""
    refuse_unfinished(run)
    got = run_evidence(store, run)
    if not got["evidence"]:
        raise AuthError("넘길 근거가 없습니다 — 이 실행은 부른 단계가 없습니다(계획 모드이거나 첫 단계 전에 멈췄습니다)", status_code=422)
    return got


def chat_messages(store, run: dict) -> tuple[str, list[dict]]:
    """실행 → (대화 제목, 메시지 둘). 사람 한 줄 + 단계 요약(어시스턴트)이고, 요약의 meta.activity 가 다음 턴의 조회 근거다
    (화면 `turnEvidence` · '심의로 넘기기' 가 활동 기록에서 근거를 모은다). 결과는 줄인 판이다."""
    called, not_called = _records(store, run, CHAT_RESULT_MAX)
    title = _title(run)
    rid = str(run["id"])
    by_ix = {r["ix"]: r for r in called}
    lines = [f"절차 실행 «{title}» 의 단계 기록이다(실행 `{rid}` · {run.get('mode') or 'live'} · 상태 {run.get('state')}).", ""]
    for s in run.get("steps") or []:
        r = by_ix.get(s["ix"])
        lab = _STATE_KO.get(s["state"], s["state"])
        if r is None:
            lines.append(f"{s['ix'] + 1}. `{s['tool']}` — 부르지 않았다({lab}{' · ' + str(s['stage']) if s.get('stage') else ''})")
            continue
        why = f" — {s['error']}" if s["state"] in ("failed", "unknown") and s.get("error") else ""
        ms = f" · {r['ms']}ms" if isinstance(r.get("ms"), int) else ""
        lines.append(f"{s['ix'] + 1}. `{s['tool']}` — {lab}{ms}{why}")
    if not_called:
        lines += ["", f"부르지 않은 단계 {len(not_called)}개는 조회 결과가 없다."]
    lines += ["", "단계의 인자 · 결과는 이 답의 조회 근거로 실려 있다 — 이어서 물으면 그 값으로 답한다. 결과는 줄인 판이고 전문은 "
                  "절차 실행 화면에 있다."]
    activity = []
    for r in called:
        res = r["result"]
        activity.append({
            "ts": int(r["started_at"] or run.get("started_at") or 0) * 1000,
            "step": r["source"], "tool": r["tool"], "call": f"proc-{rid[:12]}-{r['ix']}",
            **({"detail": r["args"]} if r["args"] else {}),
            "result_preview": res[:CHAT_PREVIEW],
            **({"result_full": res} if len(res) > CHAT_PREVIEW else {}),     # 미리보기보다 길 때만(활동 항목의 계약)
            **({"ok": r["ok"]} if r["ok"] is not None else {}),
        })
    msgs = [
        {"role": "user", "content": f"절차 실행 «{title}» 을 챗으로 가져왔다."},
        {"role": "assistant", "content": "\n".join(lines),
         "meta": {"activity": activity,
                  "procedure_run": {"run_id": rid, "state": run.get("state"), "mode": run.get("mode")}}},
    ]
    return f"절차 실행 — {title}", msgs
