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

logger = logging.getLogger(__name__)

# 한 턴에서 원장에 남길 호출 수 상한. 활동 스냅샷(60)과 같은 자리에서 잘린다.
MAX_STEPS = 60


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
    return [by_call[c] for c in order[:MAX_STEPS]]


def record(store, *, owner_sub: str, conversation_id: str, activity: list[dict],
           title: str | None = None, origin: str = "chat") -> str | None:
    """이 턴의 도구 호출을 원장에 남긴다. 남긴 실행 id 를 돌려준다(없으면 None).

    ⚠ 이 실행은 **재생용이 아니다.** `procedure_version_id` 가 없는 '빈 실행' 으로 남고,
    사람이 보고 절차로 뽑을 때 비로소 판본이 생긴다(자동 저장 금지 — PLAN §7).
    """
    steps = pair(activity)
    if not steps:
        return None
    try:
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
            store.finish_step(run_id, ix, ok=(st["ok"] is not False),
                              result_text=st["result_text"], duration_ms=st.get("ms"),
                              error=None if st["ok"] is not False else (st["step"] or "실패"))
        store.set_run_state(run_id, "done", ended=True)
        return run_id
    except Exception:  # noqa: BLE001 — ② 기록 실패가 챗을 막지 않는다
        logger.info("챗 턴을 절차 원장에 남기지 못했다 conv=%s", conversation_id, exc_info=True)
        return None
