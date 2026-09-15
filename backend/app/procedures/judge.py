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
# 파괴 도구 관문 → 재시도 무의미. ⚠ **호출자가 실제로 받는 문구**여야 한다 —
# `invoke-denied` 는 게이트웨이 **감사 로그**에만 쓰이고 응답 본문에는 없다
# (gateway.py:1854 vs :1856). 그것만 보던 동안 이 갈래는 **죽은 코드**였고, 관문에 막힌
# 호출이 `tool_error`(그냥 에러)로 기록됐다. 테스트가 손으로 지어낸 문자열을 단언해
# 초록이었다 — 4차가 적은 "인공 고정물" 그 패턴이 같은 파일에 하나 더 있었다(5차 감사).
GW_DENIED = "파괴·제어성 도구라"
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
    if GW_DENIED in text or "invoke-denied" in low:
        return "denied", False
    if GW_UNAVAILABLE in low and low.startswith("backend"):
        return "unavailable", True
    return None


# 이어 붙인 텍스트에서 JSON 값을 몇 개까지 훑을까. `list_agents` 는 796개가 온다.
_MULTI_MAX = 2000
_DECODER = json.JSONDecoder()


def _notes_of_rows(rows: list) -> dict:
    """여러 값에서 **경고만** 모은다. `collect_notes` 는 dict 만 보므로 리스트면 늘 비었다 —
    그러면 W120 같은 표식이 이 경로에서만 사라진다(경고 칸이 있는 이유가 없어진다).

    ⚠ 둘을 고쳤다(2026-09-15 5차 감사).
    ① **행 수로 자르지 않는다.** 처음에 `rows[:200]` 으로 뒀는데 실물이 그보다 길다 —
       `list_agents` 796행 · `list_property_definitions` 275행. 241번째 행의 경고가
       조용히 사라졌다. 이 함수가 존재하는 이유를 이 함수가 되돌린 셈이다. 대신
       **모은 개수**로 멈춘다.
    ② **경고가 아닌 노트는 안 모은다.** 행마다 다른 값(`status: healthy`)을 첫 행 것으로
       대표시키면 거짓이다 — `site_health` 101행이 healthy 57 / no_data_ever 44 인데
       `status: "healthy"` 하나만 남았다. 전체를 대표하지 않는 것은 안 싣는다.
    """
    out: dict[str, list] = {}
    n = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        for k in _WARN_KEYS:
            v = r.get(k)
            if v in (None, "", [], {}, False):
                continue
            got = v if isinstance(v, list) else [v]
            cur = out.setdefault(k, [])
            for item in got:
                if item not in cur:
                    cur.append(item)
                    n += 1
        if n >= 50:
            out["truncated"] = True
            break
    return out


def _parse_json_multi(text: str) -> list | None:
    """JSON 값이 **연달아** 붙어 온 모양이면 리스트로 돌려준다. 아니면 None.

    이어 붙인 한 덩이를 한 번만 파싱하면 목록형 도구가 전부 `not_json` 이 된다
    (PLAN §79 가 "다중 text 항목은 각각 파싱해 리스트로" 라고 적은 자리다).

    ⚠ **줄 단위로 쪼개면 안 된다.** 처음에 그렇게 짰다가 프로덕션에서 한 번도 안 걸렸다 —
    게이트웨이 블록은 **pretty-print** 라 `{` 한 줄이 JSON 이 아니기 때문이다. 테스트는
    compact 로 만든 인공 모양이라 초록이었다(2026-09-15 4차 감사). `join_content` 가
    블록 경계를 지워 버리므로, 여기서 **값 단위로** 이어 훑는 수밖에 없다.

    끝까지 다 먹지 못하면 **포기한다** — 반만 읽고 성공이라고 하지 않는다.
    """
    src = (text or "").strip()
    if not src:
        return None
    out: list = []
    i = 0
    n = len(src)
    while i < n:
        try:
            val, end = _DECODER.raw_decode(src, i)
        except (ValueError, RecursionError):
            # ⚠ 깊은 중첩은 `ValueError` 가 아니라 `RecursionError` 다. 저장 경로에는
            # 깊이 가드가 있지만 **판정 경로에는 없다** — 여기서 안 받으면 라우트 밖으로
            # 새어 500 이 된다. 고장난 백엔드가 그런 본문을 낼 수 있다(5차 감사).
            return None
        out.append(val)
        if len(out) > _MULTI_MAX:
            return None
        i = end
        while i < n and src[i].isspace():
            i += 1
    if len(out) < 2:
        return None
    # ⚠ **스칼라만 늘어선 것은 다중 블록이 아니다.** 도구가 항목마다 보내는 것은 레코드
    # (객체·배열)다. 숫자·따옴표 문자열이 줄줄이 있는 글(수치 덤프·로그)을 리스트로
    # 읽어 버리면, JSON 이 아닌 응답이 **성공**이 된다 — 없던 성공을 만드는 쪽이다.
    if not all(isinstance(x, (dict, list)) for x in out):
        return None
    return out


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
    except RecursionError:
        # 깊이는 '모양이 이상하다' 이지 우리 고장이 아니다 — 500 이 아니라 판정으로 낸다.
        return Verdict(False, "parse", "too_deep",
                       error="결과가 너무 깊게 중첩됐다 — 읽을 수 없다", retriable=False)
    except ValueError:
        # ⚠ **줄마다 JSON 인 모양을 본다.** 목록형 도구는 항목마다 TextContent 로 오고
        # (`list_agents` 는 796개 — 실측), `join_content` 가 그것을 줄바꿈으로 잇는다.
        # 한 덩이로 파싱하면 `{…}\n{…}` 라 당연히 실패한다. 실호출로 확인한 것만
        # `list_operations` 47 · `list_agent_domains` 23 · `list_agents` 408 블록이고
        # 셋 다 `not_json` 이었다 — 그러면 2단 항목 목록이 **빈 칸**으로 보인다
        # ("이 도구 뒤에 아무것도 없다" 와 같은 모양이다).
        rows = _parse_json_multi(text)
        if rows is not None:
            # ⚠ **여기서 바로 성공으로 나가면 안 된다.** 예전엔 그랬고, 그래서 같은
            # 커밋이 고친 두 가지(봉투 먼저 보기·`unwrap` 존중)가 **이 경로에서만**
            # 통째로 무효였다 — 죽은 잡이 블록 두 개로 오면 `done` 이 됐다.
            if unwrap:
                # 사람이 "이 도구는 한 겹 싸여 온다" 고 선언했는데 값이 여럿 왔다.
                # 모양이 바뀐 것이고, 그걸 모른 채 리스트를 결과로 쓰면 `save` 가
                # 엉뚱한 곳을 판다.
                return Verdict(False, "parse", "unwrap_missing", parsed=rows,
                               error=f"`{unwrap}` 로 벗기라고 했는데 값이 {len(rows)}개 왔다",
                               retriable=False)
            for row in rows:
                bad = _envelope_fail(row)
                if bad is not None:
                    return bad
            return Verdict(True, "parse", "ok", parsed=rows, notes=_notes_of_rows(rows))
        if raw:
            return Verdict(True, "parse", "ok", parsed=text)
        return Verdict(False, "parse", "not_json",
                       error=f"JSON 이 아니다(앞 200자): {text[:200]}", retriable=False)

    # ③ ④ 앱 봉투 층 — 여기가 isError=false 인데 실패인 자리다.
    #
    # ⚠ **unwrap 보다 먼저 본다.** 예전엔 순서가 반대였는데, SmartTwin 계열은 실패해도
    # `stdout` 이 채워져 온다(`{ok:false, exit_code:2, stderr:…, stdout:"{…}"}`).
    # 먼저 벗기면 바깥의 `ok:false`·`errors[]`·`exit_code` 가 통째로 사라지고 **잡이
    # 죽었는데 부분 결과가 성공으로** 기록됐다(실측). PLAN §79 가 `unwrap: stdout` 을
    # 지정한 바로 그 조합이다.
    bad = _envelope_fail(parsed)
    if bad is not None:
        return bad

    # SmartTwin 류 이중 포장 — 바깥이 성공이라고 한 **뒤에** 속을 연다
    if unwrap and isinstance(parsed, dict):
        inner = parsed.get(unwrap)
        if isinstance(inner, str):
            try:
                parsed = json.loads(inner)
            except ValueError:
                return Verdict(False, "parse", "not_json",
                               error=f"{unwrap} 안이 JSON 이 아니다", retriable=False)
        elif isinstance(inner, (dict, list)):
            parsed = inner          # 이미 풀려 온 모양 — 그대로 쓴다
        else:
            # ⚠ **조용히 바깥 dict 로 성공하지 않는다.** 벗기라고 적힌 칸이 없거나 다른
            # 형이면 응답 모양이 바뀐 것이고, 그걸 모른 채 바깥을 결과로 쓰면
            # `save` 경로가 엉뚱한 곳을 판다.
            return Verdict(False, "parse", "unwrap_missing", parsed=parsed,
                           error=f"`{unwrap}` 칸이 없거나 문자열이 아니다 — "
                                 f"있는 칸: {sorted(parsed)[:12]}", retriable=False)
        # 속에도 봉투가 있을 수 있다(바깥은 러너, 속은 앱)
        bad = _envelope_fail(parsed)
        if bad is not None:
            return bad

    return Verdict(True, "envelope", "ok", parsed=parsed, notes=collect_notes(parsed))


def _envelope_fail(parsed) -> Verdict | None:
    """앱이 `isError=false` 로 돌려준 **실패**인가. 아니면 None."""
    if not isinstance(parsed, dict):
        return None
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
    # 프로세스를 돌리는 앱은 성패를 **종료 코드**로도 말한다 — 0 이 아니면 실패다.
    code = parsed.get("exit_code")
    if isinstance(code, int) and not isinstance(code, bool) and code != 0:
        return Verdict(False, "envelope", "app_envelope", parsed=parsed,
                       error=_envelope_msg(parsed) or f"exit_code={code}", retriable=False)
    return None


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

# 그중 **경고로 읽어야 할 것들.** 표의 경고 칸은 여기서 나온다.
_WARN_KEYS = ("warnings", "warning", "caveats", "quality_flags",
              "out_of_domain", "extrapolation", "degenerate")


def warn_labels(notes: dict | None, *, limit: int = 8) -> list[str]:
    """단계 노트에서 **사람이 볼 짧은 표식**을 모은다.

    ⚠ 예전엔 `notes["warnings"]` 안의 dict 에서 `code` 만 봤다. 그런데 흔한 모양은
    **문자열 목록**(`["W120: ply 제외"]`)이라 하나도 안 걸렸고, 값이 문자열 하나면
    글자를 돌아 역시 0건이었다. 표의 경고 칸이 비면 사람은 '깨끗하다' 로 읽는다 —
    '못 읽었다' 가 아니라. 이 칸이 있는 이유가 **결과는 정상인데 경고만이 유일한
    신호인 자리**(W120)를 보이는 것이므로, 못 읽는 모양이 있으면 칸의 뜻이 없어진다.
    `warnings` 말고 `quality_flags`·`out_of_domain` 처럼 같은 뜻인 칸도 함께 본다.
    """
    out: list[str] = []
    for k in _WARN_KEYS:
        v = (notes or {}).get(k)
        if v in (None, "", [], {}, False):
            continue
        items = v if isinstance(v, list) else [v]
        for it in items:
            if isinstance(it, dict):
                lab = str(it.get("code") or it.get("id") or it.get("name")
                          or it.get("message") or json.dumps(it, ensure_ascii=False))
            elif isinstance(it, bool):
                lab = k          # `degenerate: true` 는 플래그 자체가 표식이다
            else:
                lab = str(it)
            lab = lab.strip()[:60]
            if lab and lab not in out:
                out.append(lab)
            if len(out) >= limit:
                return out
    return out



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
        # ⚠ **경고 칸은 살린다.** 절단본으로 통째로 바꾸면 W120 같은 표식이 사라지고,
        # 배치 비교표의 경고 칸이 빈다 — 사람은 그것을 '깨끗하다' 로 읽는다. 그 칸이
        # 있는 이유가 **결과는 정상인데 경고만이 유일한 신호**인 자리를 보이는 것이므로,
        # 무관한 노트(출처 60건 같은 것)가 커졌다고 경고가 밀려나면 안 된다.
        keys = sorted(out)[:20]
        warn = {k: out[k] for k in _WARN_KEYS if k in out}
        if len(json.dumps(warn, ensure_ascii=False)) > _NOTE_MAX // 2:
            warn = {"warnings": warn_labels(out)}   # 경고 자체가 크면 **표식만** 남긴다
        rest = json.dumps({k: v for k, v in out.items() if k not in warn},
                          ensure_ascii=False)
        room = _NOTE_MAX - 200 - len(json.dumps(warn, ensure_ascii=False))
        out = {**warn, "truncated": True, "keys": keys, "head": rest[:max(room, 0)]}
    return out


# "…Error executing tool <tool>: 1 validation error for <tool>Arguments" — 앞머리는 버린다.
_PYD_HEAD = re.compile(r"Error executing tool ([A-Za-z0-9_]+)\s*:", re.I)
# "[type=int_parsing, input_value='no-such-report', input_type=str]" — 값이 실린다.
# ⚠ `[^\]]*` 로 두면 **값 안에 `]` 가 있을 때** 꼬리를 못 떼고 통째로 남긴다 —
# 리스트 인자가 가장 흔하다(`input_value=['0','45']`). 그러면 이 함수의 첫 번째 규칙
# ("`input` 은 절대 쓰지 않는다")이 깨지고 사용자가 넣은 값이 실패 카드와 `run_steps.error`
# 에 그대로 저장된다. pydantic 은 이 꼬리를 **줄 끝에** 붙이므로 `[type=` 부터 끝까지 버린다.
_PYD_TAIL = re.compile(r"\s*\[type=.*$")


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
