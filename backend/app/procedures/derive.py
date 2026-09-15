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
        # ⚠ `float(a) == float(b)` 로 보면 2^53 위의 서로 다른 정수가 같아진다.
        # 파이썬의 `==` 는 int·float 을 정확히 비교한다 — 그대로 쓴다.
        return a == b
    if isinstance(a, (dict, list)) and isinstance(b, (dict, list)):
        return a == b
    sa, sb = (a if isinstance(a, str) else None), (b if isinstance(b, str) else None)
    if sa is not None and isinstance(b, (int, float)):
        return _num_text(b) is not None and sa in _num_text(b)
    if sb is not None and isinstance(a, (int, float)):
        return _num_text(a) is not None and sb in _num_text(a)
    return sa is not None and sb is not None and sa == sb


def _num_text(n) -> set[str] | None:
    """그 수를 **그대로 적은** 문자열들. 이 집합 밖은 같은 값이 아니다.

    ⚠ 예전엔 `float(s) == float(n)` 로 봤다. 그러면 `"0012"` 와 `12` 가 같아진다 —
    앞의 0 이 뜻을 갖는 자리가 있다(로트·도면·파트 번호). 유도기가 "앞 결과의 `count` 에
    같은 값이 있다" 며 체인을 만들고, 재생 때 정수 `12` 를 넣어 **다른 대상**을 부른다.
    게다가 이유 문구는 "값이 같다" 고 단언한다. `MIN_MATCH_LEN` 이 우연한 일치를 막으려고
    있는데, 이 경로가 그 밑을 뚫고 있었다.
    """
    if isinstance(n, bool):
        return None
    if isinstance(n, int):
        # ⚠ **float 를 거치지 않는다.** `str(int(float(n)))` 은 2^53 위에서 **다른 수**다 —
        # 9007199254740993 을 넣으면 9007199254740992 가 "같은 표기" 로 끼어들어,
        # 서로 다른 id 둘이 한 변수로 합쳐진다(이 함수가 막으려던 바로 그 사고다).
        return {str(n), f"{n}.0"}
    try:
        f = float(n)
    except (TypeError, ValueError, OverflowError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return {str(f), str(int(f))} if f.is_integer() else {str(f)}


def _too_short(v: Any) -> bool:
    """짧은 값은 우연히 일치한다 — 경로를 못 믿는다."""
    if isinstance(v, (dict, list)):
        return not v
    return len(str(v)) < MIN_MATCH_LEN


# ── 초안 ─────────────────────────────────────────────────────────────────
def draft(steps: list[dict], *, tool_backend: dict[str, str] | None = None,
          asked: str = "", tool_schemas: dict[str, dict] | None = None,
          tool_desc: dict[str, str] | None = None) -> dict:
    """원장의 단계 목록 → 절차 초안 + **왜 그렇게 판단했나**.

    `steps` 는 `{tool, args, result}` 목록이다(`args`·`result` 는 파싱된 값이거나 원문 문자열).
    `tool_backend` 는 도구 → 앱. 없으면 그 단계는 `backend` 가 비고 **결손으로 잡힌다** —
    지어내지 않는다.
    """
    tb = tool_backend or {}
    ts = tool_schemas or {}
    td = tool_desc or {}
    parsed = [{"tool": s.get("tool") or "", "args": _obj(s.get("args")),
               "result": _obj(s.get("result"))} for s in steps]

    out_steps: list[dict] = []
    reasons: list[dict] = []
    gaps: list[dict] = []
    variables: dict[str, dict] = {}
    undocumented: list[str] = []
    # 변수와 save 는 **같은 이름 공간**을 쓴다(둘 다 `{{이름}}` 으로 불린다).
    # 따로 세면 `part` 변수와 `part` save 가 겹쳐 뒤엣것이 앞엣것을 조용히 덮는다.
    names: dict[str, str] = {}
    # ⚠ 같은 인자에 같은 값이 여러 단계에 쓰이면 **변수는 하나여야 한다.** 갈라 두면
    # 사람이 같은 값을 두 번 채우게 되고, 한쪽만 바꾸면 절차가 조용히 어긋난다.
    by_value: dict[tuple, str] = {}

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
                seen_at = by_value.get((key, _vkey(val)))
                if seen_at:
                    args_out[key] = "{{%s}}" % seen_at
                    reasons.append({"step": ix + 1, "tool": st["tool"], "arg": key,
                                    "kind": "asked", "why": f"`{seen_at}` 와 같은 값이다"})
                    continue
                name = _var_name(key, names)
                names[name] = "var"
                by_value[(key, _vkey(val))] = name
                variables[name] = describe_var(
                    name, key, val, tool=st["tool"], step=ix + 1,
                    prop=_prop(ts.get(st["tool"]), key), tool_desc=td.get(st["tool"], ""))
                if variables[name].pop("_undocumented", False):
                    undocumented.append(f"{ix + 1}단계 `{st['tool']}` 의 `{key}`")
                args_out[key] = "{{%s}}" % name
            else:
                args_out[key] = val
            reasons.append({"step": ix + 1, "tool": st["tool"], "arg": key, **src})

        out_steps.append({"backend": backend, "tool": st["tool"], "args": args_out})

    # 같은 값이 여러 단계에 쓰였으면 **어디 어디에 쓰이는지**를 설명에 모은다 —
    # 한 칸이 세 단계를 움직이는데 한 단계만 적혀 있으면 사람이 영향 범위를 오해한다.
    _spread(variables, out_steps, parsed, ts)

    # ⚠ **99%에서 울리는 검출기는 검출기가 아니다.** 이 허브의 인자 설명은 1,348개 중
    # 15개뿐이다(실측). 인자마다 결손을 올리면 목록이 그것으로 덮여 진짜 결손이 묻힌다.
    # 한 줄로 모아 **얼마나인지**만 말한다 — 고칠 자리는 각 앱의 도구 설명이다.
    if undocumented:
        gaps.append({"step": 0, "tool": "", "kind": "args_undocumented",
                     "count": len(undocumented), "where": undocumented[:12],
                     "why": f"변수 {len(undocumented)}개가 **인자 설명 없이** 만들어졌다. "
                            "스키마에 없으면 도구 산문에서 인용하지만, 그것도 없으면 "
                            "그 칸의 뜻을 아무도 모른다 — 고칠 자리는 그 앱의 도구 설명이다"})

    return {
        "spec": {"title": (asked or "챗에서 뽑은 절차")[:80],
                 "vars": list(variables.values()), "steps": out_steps},
        "reasons": reasons,
        "gaps": gaps,
        # ⚠ 사람이 확정해야 하는 자리. 자동 저장하지 않는다.
        "needs_human": [r for r in reasons if r["kind"] == "constant"],
    }


def _in_prose(needle: str, prose: str) -> bool:
    """사람이 쓴 말 **안에 그 값이 통째로** 있나.

    ⚠ 맨 `in` 은 조각 일치를 부른다 — `12.5` 가 `"2012.5월"` 안에서 잡힌다. 그러면
    "사람이 쓴 말 안에 이 값이 있다" 는 이유가 거짓이 되고, 사람은 그 말을 믿고 변수로
    올린다. 앞뒤가 숫자·문자로 이어지지 않는 자리에서만 인정한다.
    """
    if not needle:
        return False
    # 경계는 **ASCII 기준**이다. 한국어는 조사를 값에 붙여 쓰므로(`PANEL_1을`·`BRKT부품`),
    # "뒤에 글자가 오면 다른 이름" 이라는 규칙을 그대로 쓰면 한국어 문장에서 거의 다
    # 놓친다. 반대로 영문·숫자·`._-` 가 이어지면 그건 **더 긴 식별자**의 일부다.
    ident = "._-"

    def _ascii_alnum(ch: str) -> bool:
        return ch.isascii() and ch.isalnum()

    tail_is_digit = needle[-1].isdigit()
    for m in re.finditer(re.escape(needle), prose):
        lo, hi = m.start(), m.end()
        if lo and (_ascii_alnum(prose[lo - 1]) or prose[lo - 1] in ident):
            continue
        if hi < len(prose):
            nxt = prose[hi]
            # 숫자로 끝나면 **단위가 붙는 것**을 허용한다(`12.5mm`). 다만 숫자·소수점이
            # 이어지면 다른 수이고(`2012.5`), `._-` 가 이어지면 다른 식별자다(`12_ASSY`).
            bad = (nxt.isdigit() or nxt in ident) if tail_is_digit else (
                _ascii_alnum(nxt) or nxt in ident)
            if bad:
                continue
        return True
    return False


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
    if asked and isinstance(val, (str, int, float)) and _in_prose(str(val), asked):
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


# ── 변수의 뜻은 **도구 스키마에서 온다** ─────────────────────────────────
# 절차는 사실상 도구다 — 변수가 그 입력 스키마다. 그러니 변수 설명도 MCP 도구 인자처럼
# 갖춰져야 한다(형·허용값·단위·왜 필요한가). 그런데 **지어낼 필요가 없다.** 그 인자를 받는
# 도구의 `inputSchema` 에 이미 있다. 거기서 끌어오고, 없으면 **없다고 말한다**(결손).
def _prop(schema: dict | None, key: str) -> dict:
    if not isinstance(schema, dict):
        return {}
    got = (schema.get("properties") or {}).get(key)
    return got if isinstance(got, dict) else {}


_SCHEMA_TYPE = {"string": "string", "integer": "number", "number": "number",
                "boolean": "boolean", "object": "json", "array": "json"}


def from_prose(desc: str, arg: str) -> str:
    """도구 **전체 설명**에서 그 인자를 말하는 문장을 찾아 인용한다.

    이 허브의 도구는 인자 설명이 거의 없다(실측 2026-09-15 — 1,348개 중 15개, **1%**).
    대신 그 내용이 도구 산문에 있다. `find_parts` 의 `name` 이 글롭이라는 사실은
    *"`name` 은 글롭이다(`bolt_*`)"* 라는 문장에만 있다.

    ⚠ **지어내지 않는다 — 인용이다.** 그 인자 이름이 실제로 나오는 문장만 가져오고,
    없으면 빈 문자열이다. 그리고 인용이라는 사실을 호출부가 밝힌다.
    """
    if not desc or not arg:
        return ""
    for line in re.split(r"(?<=[.。])\s+|\n", desc):
        t = line.strip(" -*`\t")
        if not t or len(t) > 300:
            continue
        if re.search(r"[`'\"]?\b" + re.escape(arg) + r"\b[`'\"]?", t):
            return t[:300]
    return ""


def describe_var(name: str, key: str, val: Any, *, tool: str, step: int, prop: dict,
                 tool_desc: str = "") -> dict:
    """변수 하나를 **읽을 수 있게** 만든다 — 형·허용값·설명·쓰이는 자리.

    `_undocumented` 는 호출부가 결손으로 올리고 지운다.
    """
    enum = [str(x) for x in (prop.get("enum") or []) if x is not None]
    kind = _SCHEMA_TYPE.get(_first_type(prop), "") or _type_of(val)
    desc = str(prop.get("description") or "").strip()

    out: dict[str, Any] = {"key": name, "label": _label(key, desc), "type": kind}
    if enum:
        out["type"] = "enum"
        out["values"] = enum
    used = f"{step}단계 `{tool}` 의 `{key}`"
    if desc:
        out["why"] = f"{used} — {desc[:400]}"
    else:
        quoted = from_prose(tool_desc, key)
        if quoted:
            # 스키마에는 없지만 도구 산문이 말한다 — **인용이라는 사실을 밝힌다.**
            out["why"] = f"{used} — (도구 설명에서) {quoted}"
        else:
            out["why"] = f"{used}. ⚠ 이 인자를 설명하는 글이 도구 어디에도 없다."
        out["_undocumented"] = True
    if prop.get("default") is not None:
        out["why"] += f" (도구 기본값: {prop['default']})"
    # 실제로 쓰인 값을 예시로 둔다 — **기본값이 아니다**(사람이 눌러야 들어간다).
    if not _too_short(val) or isinstance(val, (int, float)):
        out["example"] = val
    return out


def _first_type(prop: dict) -> str:
    t = prop.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "")
    if not t:
        for a in prop.get("anyOf") or []:
            if isinstance(a, dict) and a.get("type") and a["type"] != "null":
                return str(a["type"])
    return str(t or "")


def _label(key: str, desc: str) -> str:
    """사람이 읽는 이름 — 설명 첫 조각이 있으면 그걸 쓴다(없으면 인자 이름)."""
    head = re.split(r"[.\n—(]", desc)[0].strip() if desc else ""
    return f"{head[:40]} ({key})" if 2 < len(head) <= 60 else key


def _spread(variables: dict, out_steps: list[dict], parsed: list[dict],
            ts: dict[str, dict]) -> None:
    """한 변수가 여러 단계를 움직이면 **그 자리를 전부** 설명에 적는다.

    한 칸이 세 단계에 물려 있는데 한 단계만 적혀 있으면 사람이 영향 범위를 오해한다 —
    값을 바꿨을 때 무엇이 함께 바뀌는지가 절차의 요점이다.
    """
    for name, var in variables.items():
        token = "{{%s}}" % name
        where = [f"{i + 1}단계 `{st['tool']}` 의 `{k}`"
                 for i, st in enumerate(out_steps)
                 for k, v in (st.get("args") or {}).items() if v == token]
        if len(where) > 1:
            var["why"] = f"{', '.join(where)} 에 함께 들어간다. " + var["why"].split(" — ", 1)[-1]


def to_input_schema(spec: dict) -> dict:
    """절차 변수 → **MCP 도구 입력 스키마**. 절차를 도구로 등록하는 다리다.

    절차는 사실상 도구다. 그 계약을 도구와 같은 모양으로 내면, 챗·심의가 절차를
    부르는 것과 도구를 부르는 것이 같아진다.
    """
    props: dict[str, Any] = {}
    required: list[str] = []
    for v in spec.get("vars") or []:
        key = v.get("key")
        if not key:
            continue
        t = v.get("type") or "string"
        p: dict[str, Any] = {"type": {"number": "number", "boolean": "boolean",
                                      "json": "object"}.get(t, "string")}
        if t == "enum" and v.get("values"):
            p = {"type": "string", "enum": list(v["values"])}
        if v.get("why"):
            p["description"] = str(v["why"])[:600]
        elif v.get("label"):
            p["description"] = str(v["label"])[:600]
        if v.get("example") is not None:
            p["examples"] = [v["example"]]
        props[key] = p
        if v.get("required", True):
            required.append(key)
    return {"type": "object", "properties": props, "required": required,
            "additionalProperties": False}


def _nkey(n) -> str:
    """수의 동일성 키. 정수로 떨어지면 **정수 표기**로 모은다.

    ⚠ `float(v)` 로 키를 만들면 2^53 위에서 서로 다른 정수가 같은 키가 된다. 정수는
    정수로 두고, 정수로 떨어지는 실수만 정수 표기로 맞춘다(`10` 과 `10.0` 은 같은 값이다).
    """
    if isinstance(n, int):
        return f"n:{n}"
    return f"n:{int(n)}" if n.is_integer() else f"n:{n}"


def _vkey(v: Any) -> str:
    """값의 동일성 키. 화면이 문자열로 보낸 숫자도 같게 본다(`"6.0"` == `6.0`)."""
    if isinstance(v, bool):
        return f"b:{v}"
    if isinstance(v, (int, float)):
        return _nkey(v)
    if isinstance(v, str):
        # `_same` 과 **같은 잣대**여야 한다 — 여기만 느슨하면 `"0012"` 와 `12` 가 한
        # 변수로 합쳐져, 사람이 한 번 채운 값이 원래 다르던 두 단계로 같이 간다.
        try:
            f = float(v)
        except ValueError:
            return f"s:{v}"
        return _nkey(f) if v in (_num_text(f) or set()) else f"s:{v}"
    return "j:" + json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


# ── 사람이 확정한다 — 상수를 변수로 올린다 ───────────────────────────────
def promote(spec: dict, picks: list[dict], *, tool_schemas: dict[str, dict] | None = None,
            tool_desc: dict[str, str] | None = None) -> tuple[dict, list[str]]:
    """초안의 **상수 몇 개를 변수로** 올린다. 확정은 사람이 하고 이 함수는 그 결정을 적용한다.

    `picks` 는 `[{step, arg, key?, label?, why?}]` — `step` 은 1부터다(화면이 보는 번호).

    ⚠ **같은 인자·같은 값은 전부 함께 올린다.** 한 자리만 바꾸면 나머지는 상수로 남아,
    사람이 값을 바꿔도 그 단계들은 옛 값으로 돈다 — 절차가 조용히 어긋나는 자리다.
    도출이 변수를 하나로 묶는 것(`by_value`)과 같은 규율이다.

    돌려주는 것은 `(새 spec, 경고)` 다. 못 올린 것은 경고로 말한다 — 조용히 건너뛰지 않는다.
    """
    ts = tool_schemas or {}
    td = tool_desc or {}
    out = json.loads(json.dumps(spec, ensure_ascii=False, default=str))  # 원본을 안 건드린다
    steps = out.get("steps") or []
    names = {v.get("key") for v in (out.get("vars") or [])}
    warns: list[str] = []

    for pick in picks or []:
        ix = int(pick.get("step") or 0) - 1
        arg = str(pick.get("arg") or "")
        if not (0 <= ix < len(steps)) or arg not in (steps[ix].get("args") or {}):
            warns.append(f"{pick.get('step')}단계의 `{arg}` 를 못 찾았다 — 건너뛰었다")
            continue
        val = steps[ix]["args"][arg]
        if isinstance(val, str) and val.startswith("{{"):
            warns.append(f"{pick.get('step')}단계의 `{arg}` 는 이미 변수다 — 건너뛰었다")
            continue

        # ⚠ 변수 이름은 소문자·숫자·밑줄만 된다(`Var._key`). 사람이 적은 이름이 그대로
        # 안 되는 경우가 셋인데, 여태 **첫째만** 말하고 나머지는 조용했다.
        #   ① 쓸 글자가 하나도 안 남는다(`지그`) → 인자 이름으로 대체
        #   ② 일부만 남는다(`지그2` → `v_2`) — 사람이 고른 이름이 흔적도 없이 사라진다
        #   ③ 이미 있는 이름이다(`lot` → `lot_2`) — 같은 변수로 묶으려던 것이 두 칸이 된다
        # 규칙을 뒤집는다. **요청한 이름과 달라지면 무조건 말한다** — 이유를 붙여서.
        want = str(pick.get("key") or arg)
        taken = {n: 1 for n in names}
        key = _var_name(want, taken)
        if pick.get("key") and key != want:
            if not re.search(r"[a-z0-9]", want.lower()):
                key = _var_name(arg, taken)
                warns.append(f"`{want}` 는 변수 이름으로 못 쓴다(소문자·숫자·밑줄만) — "
                             f"`{key}` 로 저장했다. 보이는 이름은 그대로 쓴다")
            elif want in names:
                warns.append(f"`{want}` 는 이미 있는 변수라 `{key}` 로 따로 만들었다 — "
                             f"같은 값으로 묶으려던 것이면 이 자리를 지우고 "
                             f"`{{{{{want}}}}}` 를 직접 쓴다")
            else:
                warns.append(f"`{want}` 에서 쓸 수 있는 글자만 남겨 `{key}` 로 저장했다 — "
                             f"보이는 이름은 그대로 쓴다")
        names.add(key)
        token = "{{%s}}" % key
        hit = 0
        for st in steps:
            for k, v in list((st.get("args") or {}).items()):
                if k == arg and _same(v, val):
                    st["args"][k] = token
                    hit += 1
        var = describe_var(key, arg, val, tool=steps[ix].get("tool") or "", step=ix + 1,
                           prop=_prop(ts.get(steps[ix].get("tool")), arg),
                           tool_desc=td.get(steps[ix].get("tool"), ""))
        var.pop("_undocumented", None)
        if pick.get("label"):
            var["label"] = str(pick["label"])[:80]
        if pick.get("why"):
            var["why"] = str(pick["why"])[:600]
        out.setdefault("vars", []).append(var)
        if hit > 1:
            warns.append(f"`{key}` 는 {hit}곳에 함께 들어간다 — 값을 바꾸면 그 전부가 바뀐다")

    _spread({v["key"]: v for v in out.get("vars") or []}, steps, [], ts)
    return out, warns
