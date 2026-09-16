# 단계 판정 — 실패 다섯 모양 중 셋이 isError=false 다(docs/procedures/PLAN.md §5-6)
#
# ⚠ 여기 쓰인 응답 문자열은 **실물**이다 — 2026-09-14 dev 게이트웨이를 실제로 불러 받은 것.
#    합성 예시로 재현되는 결함은 결함이 아니다. 실물에 있느냐가 가른다.
import json

from app.procedures.judge import (
    Verdict,
    collect_notes,
    join_content,
    judge,
    short_error,
    warn_labels,
)

# ── 실물 응답 ────────────────────────────────────────────────────────────
# ② pydantic 평문 — get_report_outline(report_id="no-such-report") 실호출
REAL_PYDANTIC = (
    "_MCPToolExecutionError: Error executing tool get_report_outline: 1 validation error "
    "for get_report_outlineArguments\nreport_id\n  Input should be a valid integer, unable "
    "to parse string as an integer [type=int_parsing, input_value='no-such-report', "
    "input_type=str]\n    For further information visit "
    "https://errors.pydantic.dev/2.13/v/int_parsing"
)
# ③ 앱 봉투 — ThermalShock _guarded(app/mcp_server.py:80-92)
REAL_THERMAL = json.dumps({
    "ok": False, "data": None,
    "errors": [{"code": "E100", "field": "sample",
                "message": "extra fields not permitted: layer"}],
}, ensure_ascii=False)
# ④ error 키 — ReportArchive
REAL_RA = json.dumps({"error": "report not found: 999"}, ensure_ascii=False)


def test_gateway_plaintext_is_classified_by_prefix():
    """권한·부재·불통은 재시도 판단이 다르다 — 실행 기록에 따로 남는다."""
    a = judge(is_error=True, text="unknown tool: odb_list_components")
    assert (a.ok, a.kind, a.retriable) == (False, "unknown_tool", False)

    b = judge(is_error=True, text="forbidden: risk_add_finding")
    assert (b.ok, b.kind, b.retriable) == (False, "forbidden", False)

    c = judge(is_error=True, text="backend odb-hub unavailable: timeout after 120s")
    assert (c.ok, c.kind) == (False, "unavailable")
    assert c.retriable is True  # 불통만 재시도가 의미 있다

    # ⚠ **실물 문구다**(게이트웨이 실호출에서 줄인 것). 손으로 지어낸 `invoke-denied` 는
    # 감사 로그에만 있어, 그걸 단언하던 동안 이 갈래는 프로덕션에서 죽어 있었다.
    d = judge(is_error=True, text=(
        "invoke_tool: 'delete_report' 은 파괴·제어성 도구라 범용 실행기로 부를 수 "
        "없습니다. 직접 바인딩된 도구로만 호출하세요."))
    assert d.kind == "denied" and d.retriable is False


def test_pydantic_plaintext_is_a_failure_not_a_result():
    v = judge(is_error=True, text=REAL_PYDANTIC)
    assert v.ok is False and v.layer == "mcp" and v.kind == "tool_error"


def test_app_envelope_fails_while_is_error_is_false():
    """③ — ThermalShock 은 실패도 ok:false 봉투로 온다. isError 만 보면 성공으로 기록된다."""
    v = judge(is_error=False, text=REAL_THERMAL)
    assert v.ok is False and v.layer == "envelope" and v.kind == "app_envelope"
    assert "E100" in v.error and "sample" in v.error


def test_error_key_fails_while_is_error_is_false():
    v = judge(is_error=False, text=REAL_RA)
    assert v.ok is False and v.kind == "error_key"
    assert "report not found" in v.error


def test_empty_body_is_not_success():
    """⑤ — DynaForge list_sessions 가 빈 본문을 준다. 0건인지 실패인지 구분되지 않는다."""
    v = judge(is_error=False, text="")
    assert v.ok is False and v.kind == "empty"
    # raw 를 선언한 단계만 빈 본문을 받아들인다
    assert judge(is_error=False, text="", raw=True).ok is True


def test_non_json_fails_unless_raw_declared():
    """smarttwin_scenario_options 는 텍스트 카탈로그다 — 그 단계만 raw 를 선언한다."""
    cat = "━━ 전각도 낙하 scenario.json 옵션 카탈로그 ━━\n단위계 ★필수 확인★ …"
    assert judge(is_error=False, text=cat).ok is False
    assert judge(is_error=False, text=cat).kind == "not_json"

    v = judge(is_error=False, text=cat, raw=True)
    assert v.ok is True and v.parsed == cat


def test_refused_is_not_no_data():
    """허브 관례 — refused 는 '자료가 없다' 가 아니라 '근거 점수가 임계 밑' 이다."""
    v = judge(is_error=False, text=json.dumps({"refused": True, "hits": []}))
    assert v.ok is False and v.kind == "refused"


def test_plain_success_passes():
    v = judge(is_error=False, text=json.dumps({"projects": [{"id": "a"}]}))
    assert v.ok is True and v.parsed["projects"][0]["id"] == "a"


def test_ok_true_envelope_is_success():
    v = judge(is_error=False, text=json.dumps({"ok": True, "data": {"sed_pred": 1.2}}))
    assert v.ok is True and v.parsed["data"]["sed_pred"] == 1.2


def test_error_key_present_but_empty_is_not_a_failure():
    """빈 error 키까지 실패로 치면 정상 응답이 막힌다."""
    assert judge(is_error=False, text=json.dumps({"error": None, "x": 1})).ok is True
    assert judge(is_error=False, text=json.dumps({"errors": [], "x": 1})).ok is True


def test_unwrap_handles_double_packaging():
    """SmartTwin 류는 결과가 stdout 문자열 안에 또 JSON 으로 들어 있다."""
    outer = json.dumps({"tool": "t", "ok": True, "exit_code": 0,
                        "stdout": json.dumps({"jobs": [1, 2]})})
    assert judge(is_error=False, text=outer).parsed["stdout"]  # 안 풀면 문자열 그대로
    v = judge(is_error=False, text=outer, unwrap="stdout")
    assert v.ok is True and v.parsed == {"jobs": [1, 2]}


def test_unwrap_failure_is_reported():
    outer = json.dumps({"stdout": "not json at all"})
    v = judge(is_error=False, text=outer, unwrap="stdout")
    assert v.ok is False and v.kind == "not_json"


# ── content[] 이어붙이기 ────────────────────────────────────────────────
def test_all_text_blocks_are_joined_not_just_the_first():
    """list_agents 는 TextContent 가 796개다 — content[0] 만 보면 첫 항목만 남는다."""
    blocks = [{"type": "text", "text": json.dumps({"i": i})} for i in range(796)]
    text, other = join_content(blocks)
    assert text.count("\n") == 795 and other == []


def test_non_text_blocks_are_kept_apart():
    """이미지는 sqlite 가 아니라 파일로 내린다 — 여기서 갈라 둔다."""
    blocks = [{"type": "text", "text": "{}"},
              {"type": "image", "data": "AAAA", "mimeType": "image/png"}]
    text, other = join_content(blocks)
    assert text == "{}" and len(other) == 1 and other[0]["type"] == "image"


def test_join_handles_empty():
    assert join_content([]) == ("", [])
    assert join_content(None) == ("", [])


# ── 경고 수집 ────────────────────────────────────────────────────────────
def test_w120_warning_is_lifted_to_notes():
    """물성 없는 ply 를 조용히 제외한다 — 경고를 안 올리면 과대평가가 그대로 남는다."""
    body = json.dumps({
        "life_cycles": 3.39e7, "critical_ply": 2,
        "warnings": ["W120: ply 3 은 strength 가 없어 제외됨"],
    })
    v = judge(is_error=False, text=body)
    assert v.ok is True
    assert "W120" in v.notes["warnings"][0]


def test_model_provenance_is_lifted():
    """pcb_warpage_surrogate 의 합성 데이터 경고가 이 길로 남는다."""
    n = collect_notes({"data": {"model_version": "v20260719_112422",
                                "out_of_domain": ["pad_size"]}})
    assert n["model_version"] == "v20260719_112422"
    assert n["out_of_domain"] == ["pad_size"]


def test_notes_are_capped():
    n = collect_notes({"warnings": ["x" * 500 for _ in range(50)]})
    assert n["truncated"] is True and len(json.dumps(n)) < 5000


def test_notes_skip_empty_and_false():
    assert collect_notes({"warnings": [], "degenerate": False, "notes": ""}) == {}


# ── 실패 카드 한 줄 ─────────────────────────────────────────────────────
def test_short_error_trims_the_pydantic_dump():
    """포털 관례 — msg 만 추리고 **input 은 절대 안 쓴다**. URL 도 안 띄운다."""
    line = short_error(judge(is_error=True, text=REAL_PYDANTIC))
    assert "errors.pydantic.dev" not in line
    assert len(line) <= 220 and "\n" not in line
    # 앞머리 보일러플레이트는 버리고 쓸모 있는 것만 남는다
    assert "1 validation error" not in line
    assert "get_report_outline" in line          # 어느 도구인지
    assert "report_id" in line                   # 어느 필드인지
    assert "valid integer" in line               # 무엇이 틀렸는지
    # 사용자가 넣은 값이 화면·로그로 번지면 안 된다
    assert "no-such-report" not in line and "input_value" not in line


def test_short_error_of_envelope_names_the_field():
    line = short_error(judge(is_error=False, text=REAL_THERMAL))
    assert "sample" in line and "E100" in line


def test_verdict_row_carries_the_three_layers():
    row = judge(is_error=False, text=REAL_THERMAL).as_row()
    assert row == {"layer": "envelope", "kind": "app_envelope", "retriable": False}


# ── 회귀 방어 ────────────────────────────────────────────────────────────
def test_upload_mcp_call_behaviour_would_have_passed_all_three():
    """리포의 유일한 선례를 베꼈다면 어떻게 됐는지 — 셋 다 성공으로 기록된다.

    `upload.mcp_call` 은 JSON-RPC error 만 보고 result.isError 를 버리며, 파싱 실패를
    {"raw": …} 로 정상 반환한다. 이 테스트는 그 동작을 모사해 **우리 판정이 다르다**는 것을
    못 박는다.
    """
    def like_mcp_call(is_error, text):           # 선례의 동작
        try:
            return {"ok": True, "body": json.loads(text)}
        except ValueError:
            return {"ok": True, "body": {"raw": text}}

    cases = [(True, "unknown tool: x"), (False, REAL_THERMAL), (False, REAL_RA)]
    assert all(like_mcp_call(*c)["ok"] for c in cases)          # 선례는 전부 성공
    assert not any(judge(is_error=c[0], text=c[1]).ok for c in cases)  # 우리는 전부 실패


def test_verdict_is_a_dataclass_not_a_dict():
    v = judge(is_error=False, text="{}")
    assert isinstance(v, Verdict) and v.ok is True


# ── 3차 감사(2026-09-15) — 실호출로 드러난 둘 ─────────────────────────────
def test_항목마다_TextContent_로_오는_목록을_읽는다():
    """`join_content` 가 줄바꿈으로 잇는데 한 덩이로 파싱하니 `{…}\\n{…}` 라 당연히
    실패했다. 실호출 확인: `list_operations` 47 · `list_agent_domains` 23 ·
    `list_agents` 408 블록이 전부 `not_json` 이었다 — 그러면 2단 항목 목록이 **빈 칸**이
    되고, 화면은 "이 도구 뒤에 아무것도 없다" 와 똑같이 보인다."""
    # ⚠ **`indent=2` 가 요점이다.** 처음에 compact 로 고정물을 만들어 검사는 초록인데
    # 프로덕션에서는 한 번도 안 걸렸다 — 게이트웨이 블록은 pretty-print 라 `{` 한 줄이
    # JSON 이 아니기 때문이다. 인공 모양으로 고정하면 고친 줄 알고 넘어간다(4차 감사).
    for kw in ({"indent": 2}, {}):
        blocks = [{"type": "text", "text": json.dumps({"name": f"op{i}"}, **kw)}
                  for i in range(47)]
        text, _other = join_content(blocks)
        v = judge(is_error=False, text=text)
        assert v.ok and v.kind == "ok", f"{kw}: {v.kind} {v.error}"
        assert isinstance(v.parsed, list) and len(v.parsed) == 47, kw
        assert v.parsed[0]["name"] == "op0"


def test_끝까지_못_먹으면_포기한다():
    """반만 읽고 성공이라고 하지 않는다."""
    assert judge(is_error=False, text='{"a":1}\n이건 글이다\n{"b":2}').kind == "not_json"
    # 스칼라가 줄줄이 있는 **글**을 리스트로 읽으면 없던 성공을 만든다
    assert judge(is_error=False, text="1\n2\n3").kind == "not_json"
    assert judge(is_error=False, text='"a"\n"b"').kind == "not_json"


def test_다중_블록도_봉투와_unwrap_을_건너뛰지_않는다():
    """다중 경로가 바로 성공으로 나가서, 같은 커밋이 고친 둘(봉투 먼저·`unwrap` 존중)이
    **이 경로에서만** 통째로 무효였다 — 죽은 잡이 블록 둘로 오면 `done` 이 됐다."""
    dead = json.dumps({"ok": False, "exit_code": 2, "stdout": "{}"}, indent=2)
    text, _o = join_content([{"type": "text", "text": dead}] * 2)
    assert judge(is_error=False, text=text).kind == "app_envelope"
    # `unwrap` 을 선언했는데 값이 여럿이면 모양이 바뀐 것이다 — 조용히 리스트를 쓰지 않는다
    assert judge(is_error=False, text=text, unwrap="stdout").kind == "unwrap_missing"


def test_다중_블록의_경고도_모은다():
    """`collect_notes` 는 dict 만 보므로 리스트면 늘 비었다 — 그러면 W120 같은 표식이
    이 경로에서만 사라진다(경고 칸이 있는 이유가 없어진다)."""
    blocks = [{"type": "text", "text": json.dumps({"id": 1, "warnings": ["W120: 제외"]},
                                                  indent=2)},
              {"type": "text", "text": json.dumps({"id": 2}, indent=2)}]
    text, _o = join_content(blocks)
    v = judge(is_error=False, text=text)
    assert v.ok and warn_labels(v.notes) == ["W120: 제외"], v.notes


def test_이중_포장은_바깥_봉투를_먼저_본다():
    """SmartTwin 계열은 **실패해도 `stdout` 이 채워져 온다.** 먼저 벗기면 바깥의
    `ok:false`·`errors[]`·`exit_code` 가 통째로 사라지고, **잡이 죽었는데 부분 결과가
    성공으로** 기록된다 — PLAN §79 가 `unwrap: stdout` 을 지정한 바로 그 조합이다."""
    dead = json.dumps({"ok": False, "exit_code": 2, "stderr": "죽었다",
                       "stdout": json.dumps({"peak_stress": None, "rows": []})})
    v = judge(is_error=False, text=dead, unwrap="stdout")
    assert not v.ok and v.kind == "app_envelope", f"{v.ok} {v.kind}"

    # 종료 코드만으로도 실패를 안다 — 프로세스를 돌리는 앱은 그것으로 말한다
    v2 = judge(is_error=False, text=json.dumps({"exit_code": 3, "stdout": "{}"}),
                 unwrap="stdout")
    assert not v2.ok

    # 정상은 그대로 벗긴다
    good = json.dumps({"ok": True, "exit_code": 0, "stdout": json.dumps({"peak": 12.3})})
    v3 = judge(is_error=False, text=good, unwrap="stdout")
    assert v3.ok and v3.parsed == {"peak": 12.3}


def test_벗길_칸이_없으면_조용히_바깥을_쓰지_않는다():
    """응답 모양이 바뀐 것인데 그걸 모른 채 바깥을 결과로 쓰면 `save` 가 엉뚱한 곳을 판다."""
    v = judge(is_error=False, text=json.dumps({"ok": True, "rows": [1]}), unwrap="stdout")
    assert not v.ok and v.kind == "unwrap_missing"
    assert "stdout" in v.error and "rows" in v.error
    # 이미 풀려 온 모양은 그대로 쓴다
    v2 = judge(is_error=False, text=json.dumps({"ok": True, "stdout": {"peak": 1}}),
                 unwrap="stdout")
    assert v2.ok and v2.parsed == {"peak": 1}


def test_노트가_잘려도_경고_표식은_남는다():
    """절단본이 `{truncated,keys,head}` 로 바뀌면서 경고 키가 통째로 사라졌다.
    **무관한 노트**(출처 60건 같은 것)가 커졌다고 W120 이 밀려나면, 표의 경고 칸이 비고
    사람은 그것을 '깨끗하다' 로 읽는다 — 이 칸이 있는 이유가 정반대다."""
    from app.procedures.judge import collect_notes, warn_labels

    n = collect_notes({"warnings": ["W120: ply 3 은 strength 가 없어 제외됨"],
                       "provenance": [{"src": f"긴 출처 {i}" * 8} for i in range(60)]})
    assert n.get("truncated") is True, "고정물 전제가 바뀌었다(안 잘렸다)"
    assert warn_labels(n) == ["W120: ply 3 은 strength 가 없어 제외됨"], n

    # 경고 자체가 아주 크면 **표식만** 남긴다 — 그래도 0건은 아니다
    big = collect_notes({"warnings": [f"W{i}: " + "긴 문구 " * 20 for i in range(60)]})
    assert big.get("truncated") is True and warn_labels(big), big
    assert len(json.dumps(big, ensure_ascii=False)) < 6000


def test_실패_문구가_사용자_입력을_흘리지_않는다():
    """`[^\\]]*` 는 **값 안에 `]` 가 있으면** 꼬리를 못 뗀다 — 리스트 인자가 가장 흔하다.
    그러면 이 함수의 첫 규칙("`input` 은 절대 쓰지 않는다")이 깨지고, 사용자가 넣은 값이
    실패 카드와 `run_steps.error` 에 그대로 저장된다."""
    msg = ("1 validation error for X\nplies\n  Input should be a dict "
           "[type=dict_type, input_value=['0','45','-45'], input_type=list]")
    out = short_error(Verdict(False, "mcp", "tool_error", error=msg))
    assert "input_value" not in out and "'45'" not in out, out
    assert "plies" in out, "무엇이 틀렸는지는 남아야 한다"


def test_검사기가_찾아낸_문제는_고장이_아니다():
    """`errors[]` 는 **실패 채널일 수도, 산출물일 수도** 있다. 검사기의 계약이
    `{valid, errors:[{path,message}…]}` 인 자리가 있고(실호출: `validate_block` →
    `{"valid": false, "errors":[…]}`, isError=false), 거기서 errors 는 **찾아낸 문제**다.
    그걸 실패로 적으면 화면에 빨간 배지가 붙고 절차 원장에서 그 단계가 빠진다 —
    도구는 제대로 일했는데(6차 감사)."""
    ok_shapes = [
        {"valid": False, "errors": [{"path": "type", "message": "알 수 없는 type"}]},
        {"errors": 12, "warnings": 3, "checked": 40},     # 개수는 실패가 아니다
        {"errors": {"E1": 2}, "ok": True},                 # 집계도 아니다
    ]
    for obj in ok_shapes:
        v = judge(is_error=False, text=json.dumps(obj, ensure_ascii=False))
        assert v.ok, f"{obj} → {v.kind}: {v.error}"

    # ⚠ **완화는 `errors`(복수)에만이다.** `error`(단수)는 관례상 오류 채널이라 덮으면
    # `{"valid": true, "error": "백엔드 불통"}` 이 성공이 된다 — 검사기가 제대로 못 돌았는데
    # "검사 통과" 로 읽힌다. 완화를 넣고 나서 스스로 다시 본 자리다(7차).
    for obj in ({"valid": True, "error": "백엔드 불통"},
                {"ok": True, "error": "timeout"}):
        v = judge(is_error=False, text=json.dumps(obj, ensure_ascii=False))
        assert not v.ok, f"단수 error 를 덮었다: {obj}"

    # 진짜 실패는 그대로 잡는다 — 너무 풀면 5차가 고친 것이 되돌아간다
    for obj in ({"status": "error", "data": None, "errors": [{"code": "E101"}]},
                {"error": "not_visible", "message": "볼 수 없는 id"},
                {"ok": False, "error": "args validation failed"},
                {"refused": True}, {"exit_code": 2}):
        v = judge(is_error=False, text=json.dumps(obj, ensure_ascii=False))
        assert not v.ok, obj


def test_안_자른_것을_잘랐다고_하지_않는다():
    from app.procedures.judge import _notes_of_rows

    assert "truncated" not in _notes_of_rows([{"warnings": [f"W{i}" for i in range(50)]}])
    assert _notes_of_rows([{"warnings": [f"W{i}" for i in range(50)]},
                           {"warnings": ["W99"]}]).get("truncated") is True


# ── 평문 결과(raw) — 실패도 평문으로 온다 (2026-09-16) ─────────────────────────────────────
# KooSlurm(smarttwin_*·slurm_*)은 성공도 실패도 평문이고 isError=false 다. raw 단계가 파싱 실패를
# 무조건 성공으로 보던 탓에 `"error: 제출 실패(status=500)"` 가 **제출 성공으로** 기록될 자리였다.
import json as _json
from pathlib import Path as _Path

_SMT = _json.loads((_Path(__file__).parent / "fixtures" / "procedures"
                    / "smarttwin_text_responses.json").read_text(encoding="utf-8"))
_SUBMIT_OK = r"(\[DRY-RUN\]|✅ 제출 완료)"


def test_raw_단계도_평문_error_머리는_실패다():
    for key in ("error_real", "submit_http_fail"):
        v = judge(is_error=False, text=_SMT[key], raw=True)
        assert not v.ok and v.kind == "text_error", (key, v)
        assert v.error.startswith("error:")
    # raw 가 아니어도 not_json 이 아니라 **실제 사유**로 실패한다
    v = judge(is_error=False, text=_SMT["error_real"])
    assert not v.ok and v.kind == "text_error"


def test_raw_단계의_정상_평문은_여전히_성공이다():
    for key in ("dry_run_fullangle", "dry_run_impact", "submit_ok"):
        assert judge(is_error=False, text=_SMT[key], raw=True).ok, key


def test_ok_text_는_머리_없는_실패_문구를_잡는다():
    """`제출 응답 파싱 실패` 는 `error:` 머리가 없다 — 성공 표식으로만 가를 수 있다."""
    assert judge(is_error=False, text=_SMT["submit_parse_fail"], raw=True).ok  # 표식 없으면 못 잡는다
    v = judge(is_error=False, text=_SMT["submit_parse_fail"], raw=True, ok_text=_SUBMIT_OK)
    assert not v.ok and v.kind == "text_unexpected"
    for key in ("dry_run_fullangle", "dry_run_impact", "submit_ok"):
        assert judge(is_error=False, text=_SMT[key], raw=True, ok_text=_SUBMIT_OK).ok, key
    # 빈 본문도 표식이 있으면 성공이 아니다
    assert not judge(is_error=False, text="", raw=True, ok_text=_SUBMIT_OK).ok


def test_본문_중간의_error_는_실패로_보지_않는다():
    """첫 줄만 본다 — 카탈로그·로그 인용 안의 'error:' 로 멀쩡한 결과를 버리지 않게."""
    text = "━━ 옵션 카탈로그 ━━\n- on_fail: error: 로 시작하는 줄을 남긴다"
    assert judge(is_error=False, text=text, raw=True).ok


def test_ok_text_는_저장_시점에_검사한다():
    from app.procedures.models import ProcedureSpec, validate_spec
    base = {"title": "t", "vars": [], "steps": [
        {"backend": "smart-twin-cluster", "tool": "smarttwin_scenario_options",
         "args": {"sim_type": "fullangle_drop"}, "raw": True, "ok_text": "("}]}
    errs = validate_spec(ProcedureSpec.model_validate(base))
    assert any("정규식이 깨졌다" in e for e in errs), errs
    base["steps"][0].update(raw=False, ok_text="x")
    errs = validate_spec(ProcedureSpec.model_validate(base))
    assert any("raw 단계에만" in e for e in errs), errs
