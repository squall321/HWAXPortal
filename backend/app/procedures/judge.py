"""단계 성공 판정 — **실패 다섯 모양 중 셋은 `isError=false` 로 온다**(PLAN §5-6).

이 스택의 반복 사고가 "실패가 정상 응답과 똑같이 생겼다" 이고, 도구 호출은 그 사고가
가장 자주 나는 자리다. 그래서 판정을 **순수 함수로 떼어** 게이트웨이 없이 시험한다.

실측으로 확인한 다섯.

| 모양 | `isError` | 실례 |
|---|---|---|
| ① 게이트웨이 평문 | true  | `unknown tool:` · `forbidden:` · `backend … unavailable:` |
| ② pydantic 평문   | true  | `Error executing tool …` |
| ③ 앱 봉투         | **false** | `{ok:false, data:null, errors:[…]}` (ThermalShock `_guarded`) |
| ④ `{error: …}`    | **false** | ReportArchive · HWAXRisk `cites_required` |
| ⑤ 빈 본문         | **false** | DynaForge `list_sessions` |

리포의 유일한 게이트웨이 호출 선례 `agent/upload.py:mcp_call` 은 `isError` 를 버리고
`content[0]` 만 보며 파싱 실패를 `{"raw": …}` 로 **정상 반환**한다 — 베끼면 안 되는 이유다.
"""

import json
import re
from dataclasses import dataclass, field

# 게이트웨이가 직접 만드는 평문. 재시도 판단이 셋 다 다르다.
GW_UNKNOWN = "unknown tool:"          # 이름이 틀렸거나 그 앱이 안 붙어 있다 → 재시도 무의미
GW_FORBIDDEN = "forbidden:"           # 권한 부족 → 재시도 무의미, 사람이 권한을 받아야 한다
GW_DENIED = "invoke-denied"           # 파괴 도구 관문 → 재시도 무의미
GW_UNAVAILABLE = "unavailable:"       # 백엔드 불통·타임아웃 → 재시도가 의미 있을 수 있다

# 앱 봉투가 실패를 말하는 키들.
ENVELOPE_FAIL_KEYS = ("error", "errors")


@dataclass
class Verdict:
    ok: bool
    layer: str            # mcp | parse | envelope | save — 어디서 갈렸나
    kind: str             # unknown_tool | forbidden | denied | unavailable | tool_error |
                          # not_json | app_envelope | error_key | refused | empty | ok
    parsed: object = None  # 파싱된 JSON(또는 raw 단계의 원문)
    error: str | None = None
    retriable: bool = False
    notes: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        """실행 기록에 남기는 세 층. 권한·부재·불통은 재시도 판단이 다르다."""
        return {"layer": self.layer, "kind": self.kind, "retriable": self.retriable}


def join_content(content: list) -> tuple[str, list]:
    """`content[]` 의 text 를 **전부** 이어 붙인다. 비텍스트 항목은 따로 돌려준다.

    `content[0]` 만 보면 항목마다 TextContent 로 오는 목록형 도구가 첫 항목만 남는다 —
    `list_agents` 는 TextContent 가 796개다(실측).
    """
    texts, other = [], []
    for b in content or []:
        if isinstance(b, dict):
            if b.get("type") == "text":
                texts.append(b.get("text") or "")
            else:
                other.append(b)
        elif isinstance(b, str):
            texts.append(b)
        else:
            other.append(b)
    return "\n".join(texts), other


def _gw_kind(text: str) -> tuple[str, bool] | None:
    low = (text or "").lower()
    if low.startswith(GW_UNKNOWN):
        return "unknown_tool", False
    if low.startswith(GW_FORBIDDEN):
        return "forbidden", False
    if GW_DENIED in low:
        return "denied", False
    if GW_UNAVAILABLE in low and low.startswith("backend"):
        return "unavailable", True
    return None


def judge(*, is_error: bool, text: str, raw: bool = False,
          unwrap: str | None = None) -> Verdict:
    """한 단계의 성공 여부. 네 조건이 **모두** 성립해야 성공이다.

    `raw=True` 는 결과가 JSON 이 아니라고 단계가 선언한 경우다(옵션 카탈로그 등) — 그때만
    파싱 실패를 성공으로 본다.
    """
    # ① ② MCP 층
    if is_error:
        g = _gw_kind(text)
        if g:
            kind, retriable = g
            return Verdict(False, "mcp", kind, error=text, retriable=retriable)
        return Verdict(False, "mcp", "tool_error", error=text, retriable=False)

    # ⑤ 빈 본문 — 0건과 실패가 같은 모양이다
    if text is None or text.strip() == "":
        if raw:
            return Verdict(True, "parse", "ok", parsed="")
        return Verdict(False, "parse", "empty",
                       error="빈 본문 — 0건인지 실패인지 구분되지 않는다. raw 를 선언하거나 "
                             "도구를 바꾼다", retriable=False)

    # 파싱 층
    try:
        parsed = json.loads(text)
    except ValueError:
        if raw:
            return Verdict(True, "parse", "ok", parsed=text)
        return Verdict(False, "parse", "not_json",
                       error=f"JSON 이 아니다(앞 200자): {text[:200]}", retriable=False)

    # SmartTwin 류 이중 포장 — stdout 문자열 안에 JSON 이 또 있다
    if unwrap and isinstance(parsed, dict) and isinstance(parsed.get(unwrap), str):
        try:
            parsed = json.loads(parsed[unwrap])
        except ValueError:
            return Verdict(False, "parse", "not_json",
                           error=f"{unwrap} 안이 JSON 이 아니다", retriable=False)

    # ③ ④ 앱 봉투 층 — 여기가 isError=false 인데 실패인 자리다
    if isinstance(parsed, dict):
        # `status` 를 쓰는 앱이 있다(적층 해석기는 ok|warning|error 를 낸다 — 실측).
        # error 면 대개 errors[] 도 차 있지만, 비어 있어도 실패로 친다.
        if str(parsed.get("status") or "").lower() in ("error", "failed", "failure"):
            return Verdict(False, "envelope", "app_envelope", parsed=parsed,
                           error=_envelope_msg(parsed) or f"status={parsed.get('status')}",
                           retriable=False)
        if parsed.get("ok") is False:
            return Verdict(False, "envelope", "app_envelope", parsed=parsed,
                           error=_envelope_msg(parsed), retriable=False)
        if parsed.get("refused") is True:
            # 허브 관례 — '자료가 없다' 가 아니라 '근거 점수가 임계 밑' 이다
            return Verdict(False, "envelope", "refused", parsed=parsed,
                           error=_envelope_msg(parsed) or "refused: 근거 점수가 임계 밑",
                           retriable=False)
        if isinstance(parsed.get("error"), (str, dict)) and parsed.get("error"):
            return Verdict(False, "envelope", "error_key", parsed=parsed,
                           error=_envelope_msg(parsed), retriable=False)
        errs = parsed.get("errors")
        if isinstance(errs, list) and errs:
            return Verdict(False, "envelope", "app_envelope", parsed=parsed,
                           error=_envelope_msg(parsed), retriable=False)

    return Verdict(True, "envelope", "ok", parsed=parsed, notes=collect_notes(parsed))


def _envelope_msg(parsed: dict) -> str:
    e = parsed.get("error")
    if isinstance(e, dict):
        return f"{e.get('code') or ''} {e.get('message') or ''}".strip() or json.dumps(
            e, ensure_ascii=False)[:300]
    if isinstance(e, str) and e:
        return e
    errs = parsed.get("errors")
    if isinstance(errs, list) and errs:
        out = []
        for x in errs[:5]:
            if isinstance(x, dict):
                # 코드와 필드를 **둘 다** 남긴다 — E100(미지 키 거부)과 범위 위반은 대응이
                # 다른데, 한 줄에 코드가 없으면 사람이 그걸 구분할 수 없다.
                code = x.get("code") or x.get("type") or ""
                where = x.get("field") or x.get("loc") or ""
                msg = x.get("message") or x.get("msg") or ""
                head = f"[{code}]" if code else ""
                part = " ".join(p for p in (head, str(where), str(msg)) if p)
                out.append(part.strip())
            else:
                out.append(str(x))
        return " · ".join(p for p in out if p)[:500]
    return ""


# 결과 속에 도구가 넣어 준 경고를 뽑아 올린다. 안 올리면 보존기간 뒤 본문과 함께 사라진다.
_NOTE_KEYS = ("warnings", "warning", "notes", "caveats", "status", "assumptions",
              "model_version", "model",
              "provenance", "out_of_domain", "extrapolation", "quality_flags",
              "suspect_shared_values", "degenerate")
_NOTE_MAX = 4096


def collect_notes(parsed: object) -> dict:
    """`notes` 칸에 올릴 경고·출처. W120(ply 제외)·합성 데이터 경고가 이 길로 남는다."""
    out: dict = {}
    if not isinstance(parsed, dict):
        return out
    for k in _NOTE_KEYS:
        v = parsed.get(k)
        if v in (None, "", [], {}, False):
            continue
        out[k] = v
    data = parsed.get("data")
    if isinstance(data, dict):
        for k in _NOTE_KEYS:
            v = data.get(k)
            if v not in (None, "", [], {}, False) and k not in out:
                out[k] = v
    if out and len(json.dumps(out, ensure_ascii=False)) > _NOTE_MAX:
        out = {"truncated": True,
               "keys": sorted(out)[:20],
               "head": json.dumps(out, ensure_ascii=False)[:_NOTE_MAX - 200]}
    return out


# "…Error executing tool <tool>: 1 validation error for <tool>Arguments" — 앞머리는 버린다.
_PYD_HEAD = re.compile(r"Error executing tool ([A-Za-z0-9_]+)\s*:", re.I)
# "[type=int_parsing, input_value='no-such-report', input_type=str]" — 값이 실린다.
_PYD_TAIL = re.compile(r"\s*\[type=[^\]]*\]\s*$")


def short_error(verdict: Verdict) -> str:
    """실패 카드 한 줄 — 포털 관례(`client.ts:47-60` errorDetail)를 따른다.

    규칙 둘. **`msg` 만 추리고 `input` 은 절대 쓰지 않는다**(사용자가 넣은 값이 화면·로그에
    번지지 않게), 그리고 `errors.pydantic.dev` URL 을 띄우지 않는다. 원문은 실행 기록에
    그대로 남고 화면은 접이식으로 연다.
    """
    msg = (verdict.error or "").strip()
    if not msg:
        return verdict.kind

    lines = [ln.strip() for ln in msg.splitlines()]
    lines = [ln for ln in lines
             if ln and not ln.startswith("For further information")
             and not ln.startswith("http")]
    if not lines:
        return verdict.kind

    head = _PYD_HEAD.search(lines[0])
    if head and len(lines) > 1:
        # pydantic 평문 — 앞머리는 버리고 '필드 · 무엇이 틀렸나' 만 남긴다.
        body = " · ".join(_PYD_TAIL.sub("", ln) for ln in lines[1:3])
        return f"{head.group(1)} — {body}"[:220]

    if len(lines) > 1 and len(lines[0]) < 90:
        return f"{lines[0]} — {lines[1]}"[:220]
    return _PYD_TAIL.sub("", lines[0])[:220]
