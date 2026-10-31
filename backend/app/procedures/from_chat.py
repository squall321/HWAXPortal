# 챗·심의가 한 도구 호출을 **절차 원장**에 남긴다 (PLAN §9-9)
#
# 왜 새 원장을 안 만드나. `run_steps` 가 이미 정확한 모양이다 — 인자 원본 · 결과 · 양쪽
# sha256 · 성패 · 소요 · 순서. 챗과 심의가 **안 쓸 뿐**이었다. 하나의 원장에 세 생산자가
# 쓰면, 절차 도출이 "챗 기록을 해석하는 일" 이 아니라 **"이미 절차 모양인 기록을 읽는 일"**
# 이 된다.
#
# 규율 셋 — 챗은 운영 경로다.
#   ① **기록만 더한다.** 읽는 쪽(활동 패널·핸드오프)은 안 건드린다.
#   ② **실패해도 챗을 막지 않는다.** 게이트웨이 `_audit` 와 같은 자세다.
#   ③ **모른다와 틀렸다를 섞지 않는다.** 성패를 못 받았으면 `ok` 를 비워 둔다.
from __future__ import annotations

import logging

from app.procedures.models import PUBLISH_TOKEN
from app.procedures.runner import _TOKEN_FIELD, _mask_publish_token, _redact

logger = logging.getLogger(__name__)

# 한 턴에서 원장에 남길 호출 수 상한. 활동 스냅샷(60)과 같은 자리에서 잘린다.
MAX_STEPS = 60
# 칸에서 찾은 확인 토큰을 **글자 그대로** 다른 글에서도 가리는 값의 최소 길이. RA 토큰은 `<만료초>.<서명 43자>` 54자다
# (ReportArchive mounts/confirm.py). 모델이 지어낸 짧은 값('1' · 'yes')은 RA 가 거절해 살아 있지 않고, 글자 그대로 가리면
# 같은 글자가 든 숫자 · 낱말까지 지워진다 — 그런 값은 칸만 가린다.
TOKEN_ECHO_MIN = 20


def pair(activity: list[dict]) -> list[dict]:
    """활동 이벤트 목록 → **호출 단위**로 접는다.

    시작 이벤트가 인자를, 완료 이벤트가 결과를 싣고 둘은 `call` 로 이어진다.
    `call` 이 없는 낡은 이벤트는 **접지 않는다** — 도구 이름으로 묶으면 같은 도구를
    N번 부른 턴에서 마지막 인자와 마지막 결과가 붙어 **서로 다른 호출이 한 줄이 된다**
    (화면이 그렇게 하고 있고, 그래서 §5-5 가 났다). 원장은 그 거짓을 물려받지 않는다.
    """
    by_call: dict[str, dict] = {}
    order: list[str] = []
    for ev in activity or []:
        cid = ev.get("call")
        if not cid or not ev.get("tool"):
            continue
        cur = by_call.get(cid)
        if cur is None:
            cur = {"call": cid, "tool": str(ev["tool"]), "args_text": None,
                   "result_text": None, "ok": None, "ms": None, "step": ev.get("step")}
            by_call[cid] = cur
            order.append(cid)
        # 날것이 있으면 그것을 쓴다 — 미리보기로 만든 절차는 **인자가 손상돼 있다**
        got_args = ev.get("detail_full") or ev.get("detail")
        if got_args and cur["args_text"] is None:
            cur["args_text"] = str(got_args)
        got = ev.get("result_full") or ev.get("result_preview")
        if got and cur["result_text"] is None:
            cur["result_text"] = str(got)
        if isinstance(ev.get("ok"), bool):
            cur["ok"] = ev["ok"]
        if isinstance(ev.get("ms"), int) and cur["ms"] is None:
            cur["ms"] = ev["ms"]
    out = [by_call[c] for c in order[:MAX_STEPS]]
    if len(order) > MAX_STEPS:
        # ⚠ **잘렸다는 것을 남긴다.** 조용히 끊으면 70번 부른 턴이 원장에서는 **완전한**
        # 60단계로 보이고, 거기서 뽑은 절차는 뒷부분이 통째로 없는 채 "이대로 하면 된다"
        # 가 된다. 마지막 칸을 표식으로 쓴다.
        out[-1] = {**out[-1], "truncated": len(order) - MAX_STEPS}
    return out


def record(store, *, owner_sub: str, conversation_id: str, activity: list[dict],
           title: str | None = None, origin: str = "chat") -> str | None:
    """이 턴의 도구 호출을 원장에 남긴다. 남긴 실행 id 를 돌려준다(없으면 None).

    ⚠ 이 실행은 **재생용이 아니다.** `procedure_version_id` 가 없는 '빈 실행' 으로 남고,
    사람이 보고 절차로 뽑을 때 비로소 판본이 생긴다(자동 저장 금지 — PLAN §7).
    """
    steps = pair(activity)
    if not steps:
        return None
    run_id = None
    try:
        # ⚠ **게시 확인 토큰을 남기지 않는다**(남은 일 B3 ③ — 원장에 토큰 0). 챗이 RA 에 게시하면 미리보기 결과(토큰을 준다)와
        # 게시 인자(토큰을 받는다)가 이 턴에 같이 오고, 그 값은 600초 동안 그 보고서를 그 게시판에 올릴 수 있다. 실행기 `_one` 과
        # 같은 가림을 쓴다 — 칸을 가리고(`_mask_publish_token`), 그렇게 찾은 값이 다른 꼴로 되비친 곳(검증 오류가 받은 인자를 파이썬
        # 꼴 `'confirm_token': '…'` 로 싣는다 — `_redact` 를 둔 까닭과 같다)도 가린다. 도구 이름은 보지 않는다 — 챗 기록의 이름은
        # 게이트웨이 노출 이름이라 앱 접두가 붙어 올 수 있고, `confirm_token` 칸은 RA 게시 확인뿐이다(형제 리포 대조 10-31).
        # 가리기 전에는 아무것도 쓰지 않는다 — 여기서 터지면 아래 except 가 받아 아무것도 남기지 않는다.
        seen = {m.group(2) for st in steps for t in (st["args_text"], st["result_text"]) if t
                for m in _TOKEN_FIELD.finditer(t)}
        for st in steps:
            for k in ("args_text", "result_text"):
                if st[k]:
                    t = _mask_publish_token(st[k])
                    for tok in seen:
                        if len(tok) >= TOKEN_ECHO_MIN:
                            t = _redact(t, {PUBLISH_TOKEN: tok})
                    st[k] = t
        run_id = store.create_run(
            owner_sub=owner_sub, run_by=owner_sub, procedure_version_id=None,
            inputs={}, origin=origin, mode="live", title=title,
            trigger_kind="conversation", trigger_ref=conversation_id)
        for ix, st in enumerate(steps):
            # 챗은 게이트웨이를 거치므로 **어느 앱인지 기록에 없다**(PLAN §9-8). 지어내지
            # 않고 비워 둔다 — 나중에 도구 지도로 채우는 것은 읽는 쪽의 일이다.
            store.begin_step(run_id, ix, backend="", tool=st["tool"],
                             args={"_text": st["args_text"]} if st["args_text"] else {},
                             expect="fast", mode="live")
            # ⚠ 규율 ③ 이 여기서 깨져 있었다. `ok` 가 None(성패를 못 받았다)이면
            # `None is not False` → True 라 **성공으로** 적혔다. 그러면 `/runs` 에 성공으로
            # 뜨고, 절차로 뽑을 때 `state == "done"` 필터를 통과해 **검증된 단계인 양**
            # 굳는다. 원장에는 `unknown` 이라는 칸이 이미 있다 — 그걸 쓴다.
            if st["ok"] is None:
                store.finish_step(run_id, ix, ok=False, state="unknown", stage="no_outcome",
                                  result_text=st["result_text"], duration_ms=st.get("ms"),
                                  error="성패를 못 받았다 — 실행 여부를 모른다")
            else:
                store.finish_step(run_id, ix, ok=st["ok"],
                                  result_text=st["result_text"], duration_ms=st.get("ms"),
                                  error=None if st["ok"] else (st["step"] or "실패"))
            if st.get("truncated"):
                # 노트만 더한다 — `finish_step` 을 다시 부르면 바로 위에서 적은 성패·사유가
                # 지워진다(그쪽은 state·ok·error·stage 를 항상 쓴다).
                store.annotate_step(
                    run_id, ix,
                    {"truncated": st["truncated"],
                     "why": f"이 턴은 호출이 더 있었는데 {MAX_STEPS}개에서 잘렸다 — "
                            f"{st['truncated']}개가 원장에 없다"})
        store.set_run_state(run_id, "done", ended=True)
        return run_id
    except Exception:  # noqa: BLE001 — ② 기록 실패가 챗을 막지 않는다
        logger.info("챗 턴을 절차 원장에 남기지 못했다 conv=%s", conversation_id, exc_info=True)
        # ⚠ **반쯤 쓴 실행을 `queued` 로 두지 않는다.** `create_run` 은 됐는데 단계 쓰기가
        # 중간에 터지면, 부르는 쪽은 None("남긴 게 없다")을 받는데 사용자 `/runs` 목록에는
        # 잘린 실행이 **도는 중**으로 남는다. 끝난 것으로 표시하고 이유를 남긴다.
        try:
            if run_id:
                store.set_run_state(run_id, "failed", stage="record_failed", ended=True)
        except Exception:  # noqa: BLE001
            logger.info("잘린 챗 실행을 마감하지도 못했다 run=%s", run_id, exc_info=True)
        return None
