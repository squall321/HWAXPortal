"""레시피의 기계장치 둘 — 변수 치환 `{{var}}` 과 결과 추출 `save`. 이 둘뿐이다.

의미는 v1 에서 **고정**한다(PLAN §2). 레시피는 판본화·공유되는 자산이라 뒤에 바꾸면
이미 저장된 레시피의 뜻이 바뀐다.

- 치환 — 인자 값이 정확히 `"{{var}}"` 하나면 저장된 JSON 값을 **형 그대로** 넣는다.
  문자열 안에 섞이면 문자열 치환. 파싱된 JSON 의 **문자열 리프에서만** 하고 문서 전체를
  문자열 템플릿으로 다루지 않는다.
- 추출 — `a.b[0].c` 꼴 점·인덱스 표기만 푼다. jsonpath 의존성을 쓰지 않는다(새 pip 0).
"""

import re

# "{{ var }}" 하나로만 이뤄진 문자열 — 형을 보존해 주입한다.
_WHOLE = re.compile(r"^\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}$")
# 문자열 안에 섞인 자리 — 문자열로 치환한다.
_INLINE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")
# a.b[0].c
_SEG = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


class TemplateError(ValueError):
    """치환·추출이 값을 못 찾았거나 표기가 틀렸다."""


def refs(value):
    """이 인자 트리가 참조하는 변수 이름을 모은다(순서 보존, 중복 제거)."""
    out: list[str] = []

    def walk(v):
        if isinstance(v, str):
            for m in _INLINE.finditer(v):
                name = m.group(1)
                if name not in out:
                    out.append(name)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(value)
    return out


def substitute(value, scope: dict):
    """인자 트리의 문자열 리프에 `scope` 를 채운다. 없는 변수는 TemplateError."""
    if isinstance(value, str):
        whole = _WHOLE.match(value)
        if whole:
            name = whole.group(1)
            if name not in scope:
                raise TemplateError(f"변수 없음: {name}")
            return scope[name]  # ← 형 그대로. 숫자·객체·배열이 문자열이 되지 않는다.

        def one(m):
            name = m.group(1)
            if name not in scope:
                raise TemplateError(f"변수 없음: {name}")
            v = scope[name]
            return v if isinstance(v, str) else _compact(v)

        return _INLINE.sub(one, value)
    if isinstance(value, dict):
        return {k: substitute(v, scope) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, scope) for v in value]
    return value  # 숫자·불리언·None 은 그대로


def _compact(v):
    import json

    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def extract(data, path: str):
    """`a.b[0].c` 로 값을 꺼낸다. 경로가 안 풀리면 TemplateError.

    v1 은 선행 `$.` 을 허용만 하고 의미는 없다 — 레시피를 옮겨 적을 때 흔한 표기라서다.
    """
    p = path.strip()
    if p.startswith("$."):
        p = p[2:]
    elif p == "$":
        return data
    if not p:
        raise TemplateError("빈 경로")

    pos, cur = 0, data
    seen = ""
    while pos < len(p):
        if p[pos] == ".":
            pos += 1
            continue
        m = _SEG.match(p, pos)
        if not m:
            raise TemplateError(f"경로 표기 오류: {path} ({pos}번째 글자)")
        pos = m.end()
        if m.group(1) is not None:
            key = m.group(1)
            seen = f"{seen}.{key}" if seen else key
            if not isinstance(cur, dict) or key not in cur:
                raise TemplateError(f"경로가 안 풀린다: {path} — {seen} 에서 멈춤")
            cur = cur[key]
        else:
            ix = int(m.group(2))
            seen = f"{seen}[{ix}]"
            if not isinstance(cur, list) or ix >= len(cur):
                raise TemplateError(f"경로가 안 풀린다: {path} — {seen} 에서 멈춤")
            cur = cur[ix]
    return cur


def is_empty(v) -> bool:
    """`save` 가 뽑은 값이 비었나 — 비었으면 그 단계에서 정지한다(PLAN §5-6).

    RA 는 0행 표를 오류 없이 만든다. 빈 값을 다음 단계에 치환하면 그 사고가 난다.
    """
    return v is None or v == "" or v == [] or v == {}
