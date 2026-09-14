# 단계 판정 — 실패 다섯 모양 중 셋이 isError=false 다(docs/workbench/PLAN.md §5-6)
#
# ⚠ 여기 쓰인 응답 문자열은 **실물**이다 — 2026-09-14 dev 게이트웨이를 실제로 불러 받은 것.
#    합성 예시로 재현되는 결함은 결함이 아니다. 실물에 있느냐가 가른다.
import json

from app.workbench.judge import (
    Verdict,
    collect_notes,
    join_content,
    judge,
    short_error,
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
    """권한·부재·불통은 재시도 판단이 다르다 — 런 기록에 따로 남는다."""
    a = judge(is_error=True, text="unknown tool: odb_list_components")
    assert (a.ok, a.kind, a.retriable) == (False, "unknown_tool", False)

    b = judge(is_error=True, text="forbidden: risk_add_finding")
    assert (b.ok, b.kind, b.retriable) == (False, "forbidden", False)

    c = judge(is_error=True, text="backend odb-hub unavailable: timeout after 120s")
    assert (c.ok, c.kind) == (False, "unavailable")
    assert c.retriable is True  # 불통만 재시도가 의미 있다

    d = judge(is_error=True, text="invoke-denied: delete_report")
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
