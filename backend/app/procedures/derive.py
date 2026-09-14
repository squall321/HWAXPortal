# 실행 기록 → 절차 **초안** (PLAN §9-2·§9-9)
#
# 한 고리의 마지막 칸이다. 챗에서 한 일이 원장에 남았으면, 그것을 절차로 펴 본다 —
# **안 펴지는 칸이 곧 결손이다.**
#
# 어려운 것은 "어느 인자가 변수인가" 다. 키워드 목록으로 정하면 그게 하드코딩이다.
# 대신 **값이 어디서 왔는지**를 찾는다.
#
#   · 앞 단계 **결과 안에** 그 값이 있다 → 그건 변수가 아니라 **체인**이다(`save` → `{{}}`)
#   · 사람이 쓴 말 **안에** 있다        → 사람이 준 값이다 → **변수**
#   · 둘 다 아니다                      → 모른다. **상수로 두고 사람에게 묻는다**
#
# 세 번째가 중요하다. 모르면 모른다고 한다 — 지어낸 변수는 절차를 조용히 망친다
# (그 칸이 매번 물어보는 칸이 되거나, 반대로 남의 값이 상수로 굳는다).
#
# ⚠ **자동 저장하지 않는다.** 이 모듈은 초안과 **그 근거**를 낸다. 확정은 사람이 한다.
from __future__ import annotations

import json
import re
from typing import Any

from app.procedures import template

# 값이 너무 짧으면 우연히 일치한다("1"·"ok"·"mm"). 경로를 못 믿는다.
MIN_MATCH_LEN = 3
# 훑을 결과 깊이 — 너무 깊으면 느리고, 얕으면 체인을 놓친다.
MAX_DEPTH = 8
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ── 값이 어디서 왔나 ─────────────────────────────────────────────────────
def find_path(obj: Any, value: Any, *, depth: int = 0) -> str | None:
    """`obj` 안에서 `value` 와 같은 값의 경로를 찾는다 — `template.extract` 의 역이다.

    찾으면 `"a.b[0].c"` 를 돌려준다. **찾은 경로는 실제로 풀린다**(호출부가 대조한다).
    못 찾으면 None — 짐작해서 비슷한 경로를 주지 않는다.
    """
    if depth > MAX_DEPTH:
        return None
    if _same(obj, value):
        return ""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str) or not _IDENT.match(k):
                continue
            sub = find_path(v, value, depth=depth + 1)
            if sub is not None:
                return k if sub == "" else f"{k}.{sub}" if not sub.startswith("[") else k + sub
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:200]):
            sub = find_path(v, value, depth=depth + 1)
            if sub is not None:
                return f"[{i}]" if sub == "" else (f"[{i}]{sub}" if sub.startswith("[")
                                                   else f"[{i}].{sub}")
    return None


def _same(a: Any, b: Any) -> bool:
    """같은 값인가. 형이 달라도 사람이 보기에 같은 것은 같게 본다(화면은 문자열만 보낸다)."""
    if a is b:
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    if isinstance(a, (dict, list)) and isinstance(b, (dict, list)):
        return a == b
    sa, sb = (a if isinstance(a, str) else None), (b if isinstance(b, str) else None)
    if sa is not None and isinstance(b, (int, float)):
        try:
            return float(sa) == float(b)
        except ValueError:
            return False
    if sb is not None and isinstance(a, (int, float)):
        try:
            return float(sb) == float(a)
        except ValueError:
            return False
    return sa is not None and sb is not None and sa == sb


def _too_short(v: Any) -> bool:
    """짧은 값은 우연히 일치한다 — 경로를 못 믿는다."""
    if isinstance(v, (dict, list)):
        return not v
    return len(str(v)) < MIN_MATCH_LEN


# ── 초안 ─────────────────────────────────────────────────────────────────
def draft(steps: list[dict], *, tool_backend: dict[str, str] | None = None,
          asked: str = "") -> dict:
    """원장의 단계 목록 → 절차 초안 + **왜 그렇게 판단했나**.

    `steps` 는 `{tool, args, result}` 목록이다(`args`·`result` 는 파싱된 값이거나 원문 문자열).
    `tool_backend` 는 도구 → 앱. 없으면 그 단계는 `backend` 가 비고 **결손으로 잡힌다** —
    지어내지 않는다.
    """
    tb = tool_backend or {}
    parsed = [{"tool": s.get("tool") or "", "args": _obj(s.get("args")),
               "result": _obj(s.get("result"))} for s in steps]

    out_steps: list[dict] = []
    reasons: list[dict] = []
    gaps: list[dict] = []
    variables: dict[str, dict] = {}
    # 변수와 save 는 **같은 이름 공간**을 쓴다(둘 다 `{{이름}}` 으로 불린다).
    # 따로 세면 `part` 변수와 `part` save 가 겹쳐 뒤엣것이 앞엣것을 조용히 덮는다.
    names: dict[str, str] = {}

    for ix, st in enumerate(parsed):
        backend = tb.get(st["tool"]) or ""
        if not backend:
            gaps.append({"step": ix + 1, "tool": st["tool"], "kind": "backend_unknown",
                         "why": "이 도구가 어느 앱 것인지 기록에 없다 — 도구 지도에서 못 찾았다"})
        args_out: dict[str, Any] = {}

        if not isinstance(st["args"], dict):
            gaps.append({"step": ix + 1, "tool": st["tool"], "kind": "args_not_structured",
                         "why": "인자가 구조가 아니라 글이다 — 잘린 미리보기일 수 있다"})
        for key, val in (st["args"] if isinstance(st["args"], dict) else {}).items():
            src = _where_from(val, parsed[:ix], asked)
            if src["kind"] == "chain":
                name = _save_name(src["from_step"], src["path"], names)
                names[name] = "save"
                out_steps[src["from_step"]].setdefault("save", {})[name] = src["path"]
                args_out[key] = "{{%s}}" % name
            elif src["kind"] == "asked":
                name = _var_name(key, names)
                names[name] = "var"
                variables[name] = {"key": name, "label": key, "type": _type_of(val),
                                   "why": "사람이 이번 대화에서 준 값이다"}
                args_out[key] = "{{%s}}" % name
            else:
                args_out[key] = val
            reasons.append({"step": ix + 1, "tool": st["tool"], "arg": key, **src})

        out_steps.append({"backend": backend, "tool": st["tool"], "args": args_out})

    return {
        "spec": {"title": (asked or "챗에서 뽑은 절차")[:80],
                 "vars": list(variables.values()), "steps": out_steps},
        "reasons": reasons,
        "gaps": gaps,
        # ⚠ 사람이 확정해야 하는 자리. 자동 저장하지 않는다.
        "needs_human": [r for r in reasons if r["kind"] == "constant"],
    }


def _where_from(val: Any, before: list[dict], asked: str) -> dict:
    """이 값이 어디서 왔나 — chain(앞 결과) · asked(사람 말) · constant(모른다)."""
    if _too_short(val):
        return {"kind": "constant", "why": f"값이 너무 짧아 출처를 못 믿는다({val!r})"}
    for back, st in enumerate(reversed(before)):
        ix = len(before) - 1 - back
        path = find_path(st["result"], val)
        if path:
            # ⚠ 찾은 경로가 **실제로 풀리는지** 대조한다. 안 그러면 못 도는 절차가 나온다.
            try:
                if _same(template.extract(st["result"], path), val):
                    return {"kind": "chain", "from_step": ix, "path": path,
                            "why": f"{ix + 1}단계 결과의 `{path}` 에 같은 값이 있다"}
            except Exception:  # noqa: BLE001 — 경로가 안 풀리면 체인이 아니다
                pass
    if asked and isinstance(val, (str, int, float)) and str(val) in asked:
        return {"kind": "asked", "why": "사람이 쓴 말 안에 이 값이 있다"}
    return {"kind": "constant",
            "why": "앞 결과에도 사람 말에도 없다 — 상수로 두었다. 변수인지 사람이 정한다"}


def _obj(v: Any) -> Any:
    """원문 문자열이면 JSON 으로 풀어 본다. 안 풀리면 그대로 둔다(글일 수 있다)."""
    if not isinstance(v, str):
        return v
    t = v.strip()
    if not t or t[0] not in "{[":
        return v
    try:
        return json.loads(t)
    except ValueError:
        return v


def _type_of(v: Any) -> str:
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, (dict, list)):
        return "json"
    return "string"


def _var_name(key: str, seen: dict) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", str(key).lower()).strip("_") or "arg"
    if not re.match(r"^[a-z_]", base):
        base = "v_" + base
    name, n = base, 2
    while name in seen:
        name, n = f"{base}_{n}", n + 1
    return name


def _save_name(from_step: int, path: str, seen: dict) -> str:
    tail = re.split(r"[.\[]", path)[-1].strip("]") or "value"
    return _var_name(f"s{from_step + 1}_{tail}", seen)
