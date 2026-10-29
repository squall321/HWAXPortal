#!/usr/bin/env python3
# 게이트웨이에 새로 붙은 앱을 점검한다 — 영역 · 권한 행 · 이름 겹침 · 인자 설명(update-all §6, docs/request-1029 E-6)
"""update-all 이 게이트웨이 /tools-map(파일) · 포털 권한 정책(파일, 읽었으면) · 기록 파일을 주고 부른다.

처음 본 앱을 기록(infra/.state/app-checks.json — gitignore)에 적고, 붙은 지 NEW_DAYS(14)일 동안 실행마다 넷을 본다. 기록이 없던 첫
실행은 지금 앱을 '전부터 있던 것' 으로 적기만 한다 — 옛 앱마다 경고를 쏟지 않는다(인자 설명은 거의 모든 앱이 기준 아래다).

  · 영역 — /tools-map 의 unclassified 에 든 그 앱 도구. 게이트웨이 리포 tool_areas.json 의 apps 에 한 줄을 넣는다.
  · 권한 행 — 포털 권한 정책의 backends 에 그 앱 키가 있나. 없으면 위 '권한 표 구멍'(✗)이 이미 막는다 — 여기서는 앱 쪽에서 다시 짚는다.
  · 이름 겹침 — 원래 이름이 다른 앱과 같아 접두가 붙은 도구. 맨 이름으로 부르던 절차 · 핀 · 클라이언트가 unknown tool 이 될 수 있다.
  · 인자 설명 — /tools-map 의 arg_scores 에서 설명 있는 인자 비율이 기준(threshold, 0 이면 끔) 미만.

출력은 줄마다 '<ok|warn|info>\\t<글>' 이다. update-all 이 ok → ✓ · warn → ⚠(비치명) · info → · 로 찍는다. 막지도 숨기지도 않는다.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

NEW_DAYS = 14          # 붙은 지 이 날수 동안 실행마다 본다 — 한 번 놓친 경고가 다음 실행에도 보이게
NAME_SHOW = 5          # 이름 겹침을 몇 개까지 적나


def _orig(exposed: str, backend: str) -> str:
    """노출 이름 → 원래 이름. 겹치면 '<백엔드 키에서 하이픈 뺀 것>_<원래 이름>' 이 노출 이름이다(게이트웨이 _aggregate)."""
    p = backend.replace("-", "") + "_"
    return exposed[len(p):] if exposed.startswith(p) else exposed


def _load_state(path: Path) -> tuple[dict | None, str]:
    """기록 → ({앱: 처음 본 시각(0 = 기록 전부터 있던 앱)} 또는 None(없음 · 못 읽음), 까닭)."""
    if not path.exists():
        return None, ""
    try:
        apps = json.loads(path.read_text(encoding="utf-8"))["apps"]
        if not isinstance(apps, dict):
            raise ValueError("apps 가 표가 아니다")
        return {str(k): int(v) for k, v in apps.items()}, ""
    except (OSError, ValueError, KeyError, TypeError) as e:
        return None, f"{type(e).__name__}"


def _save_state(path: Path, apps: dict) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"version": 1, "apps": apps}, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
        return ""
    except OSError as e:
        return f"{type(e).__name__}: {e}"


def check(tmap: dict, policy: dict | None, state: dict | None, now: int, why_state: str = "") -> tuple[list, dict]:
    """→ ([(종류, 글)], 새 기록)."""
    out: list = []
    labels = {a.get("app"): a.get("label") or a.get("app") for a in tmap.get("apps") or []}
    apps = sorted(k for k in labels if k and k != "_gateway")
    if why_state:
        out.append(("warn", f"새 앱 점검 — 기록을 못 읽었다({why_state}) · 지금 앱 {len(apps)}개를 전부터 있던 것으로 다시 적는다"))
    if state is None:
        if not why_state:
            out.append(("info", f"새 앱 점검 — 기록이 없어 지금 앱 {len(apps)}개를 전부터 있던 것으로 적었다(다음 실행부터 새로 붙는 앱을 본다)"))
        return out, {a: 0 for a in apps}
    new_state = dict(state)
    for a in apps:
        new_state.setdefault(a, now)
    targets = [a for a in apps if new_state[a] and now - new_state[a] < NEW_DAYS * 86400]
    if not targets:
        out.append(("ok", f"새 앱 점검 — 붙은 지 {NEW_DAYS}일 안의 앱이 없다(앱 {len(apps)}개)"))
        return out, new_state
    out.append(("info", f"새 앱 점검 — 붙은 지 {NEW_DAYS}일 안의 앱 {len(targets)}개(앱 {len(apps)}개 중)"))
    tmapping = tmap.get("map") or {}
    unclassified = set(tmap.get("unclassified") or [])
    owners: dict = {}
    for name, bk in tmapping.items():
        if bk and bk != "_gateway":
            owners.setdefault(_orig(name, bk), set()).add(bk)
    scores = tmap.get("arg_scores") or {}
    threshold = float(scores.get("threshold") or 0)
    rows = {r.get("app"): r for r in scores.get("apps") or []}
    pol = (policy or {}).get("backends") if isinstance(policy, dict) else None
    for a in targets:
        who = f"새 앱 {labels[a]}({a}, 붙은 지 {(now - new_state[a]) // 86400}일)"
        tools = sorted(n for n, bk in tmapping.items() if bk == a)
        if not tools:
            out.append(("info", f"{who} — 도구가 아직 없다(불통이거나 막 붙었다) · 다음 실행에 다시 본다"))
            continue
        warns = []
        nu = sum(1 for n in tools if n in unclassified)
        if nu:
            warns.append(f"영역 없는 도구 {nu}/{len(tools)}개 — 게이트웨이 리포 tool_areas.json 의 apps 에 \"{a}\": \"<영역>\" 한 줄"
                         "(영역 키는 같은 파일의 areas)")
        if isinstance(pol, dict) and a not in pol:
            warns.append("포털 권한표에 행이 없다(위 '권한 표 구멍') — backend/config/access.yaml 의 플랫폼 gateway: 또는 박스의 access.local.yaml")
        clash = sorted({_orig(n, a) for n in tools if len(owners.get(_orig(n, a), ())) > 1})
        if clash:
            shown = " · ".join(f"{o}({', '.join(sorted(owners[o] - {a}))})" for o in clash[:NAME_SHOW])
            more = f" 외 {len(clash) - NAME_SHOW}개" if len(clash) > NAME_SHOW else ""
            warns.append(f"이름 겹침 {len(clash)}개 — {shown}{more}. 겹친 이름에는 접두가 붙어, 맨 이름으로 부르던 절차 · 핀 · 클라이언트가 "
                         "unknown tool 이 될 수 있다 — 앱 쪽 도구 이름을 바꾸는 것이 낫다")
        row = rows.get(a) or {}
        n, d = int(row.get("args") or 0), int(row.get("described") or 0)
        if threshold > 0 and n and d / n < threshold:
            w = (row.get("worst") or [{}])[0]
            worst = f" · 가장 나쁜 도구 {w.get('tool')}(인자 {w.get('args')}개 중 설명 {w.get('described')}개)" if w.get("tool") else ""
            warns.append(f"인자 설명 {d}/{n}개({100 * d / n:.0f}%) — 기준 {100 * threshold:.0f}% 미만{worst}. "
                         "앱이 inputSchema.properties[].description 을 채우면 오른다")
        if warns:
            out += [("warn", f"{who} — {w}") for w in warns]
        else:
            out.append(("ok", f"{who} — 도구 {len(tools)}개 · 영역 · 권한 행 · 이름 · 인자 설명 이상 없음"))
    return out, new_state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="게이트웨이에 새로 붙은 앱 점검(영역 · 권한 행 · 이름 겹침 · 인자 설명)")
    ap.add_argument("--tools-map", required=True, help="게이트웨이 /tools-map JSON 파일")
    ap.add_argument("--policy", help="포털 /internal/access/policy JSON 파일(못 읽었으면 주지 않는다 — 권한 행은 건너뛴다)")
    ap.add_argument("--state", required=True, help="기록 파일(update-all 은 infra/.state/app-checks.json)")
    ap.add_argument("--now", type=int, help=argparse.SUPPRESS)          # 시험용 — 기준 시각(epoch 초)
    a = ap.parse_args(argv)
    try:
        tmap = json.loads(Path(a.tools_map).read_text(encoding="utf-8"))
        policy = json.loads(Path(a.policy).read_text(encoding="utf-8")) if a.policy else None
    except (OSError, ValueError) as e:
        print(f"warn\t새 앱 점검 — 입력을 읽지 못했다({type(e).__name__})")
        return 2
    state_path = Path(a.state)
    state, why = _load_state(state_path)
    lines, new_state = check(tmap, policy, state, a.now if a.now is not None else int(time.time()), why)
    if new_state != state:
        err = _save_state(state_path, new_state)
        if err:
            lines.append(("warn", f"새 앱 점검 — 기록을 쓰지 못했다({err}) · 다음 실행은 이번 기록 없이 돈다(infra/.state 의 권한 · 소유자를 본다)"))
    for kind, text in lines:
        print(f"{kind}\t{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
