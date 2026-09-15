# 절차 계약 — 치환·추출·저장 시점 거절·저장소 격리·기동 회복(docs/procedures/checklist.md S1)
import json

import pytest

from app.config import Settings
from app.procedures import template
from app.procedures.models import (
    DRY_RUN_TOOLS,
    MUST_GATE,
    ProcedureSpec,
    Step,
    Var,
    check_against_schemas,
    schema_fingerprint,
    validate_spec,
)
from app.procedures.store import ProceduresStore


# ── 기계장치 ① 치환 ─────────────────────────────────────────────────────
def test_whole_leaf_keeps_type():
    """인자 값이 정확히 "{{var}}" 하나면 형이 보존된다 — 숫자가 문자열이 되면 안 된다."""
    scope = {"r": 50.0, "loads": {"N": [1, 2, 3], "M": [0, 0, 0]}, "on": True}
    out = template.substitute(
        {"bend_radius": "{{r}}", "loads": "{{loads}}", "flag": "{{on}}"}, scope)
    assert out["bend_radius"] == 50.0 and isinstance(out["bend_radius"], float)
    assert out["loads"] == scope["loads"]
    assert out["flag"] is True


def test_inline_becomes_string():
    out = template.substitute({"title": "R{{r}} 굽힘", "n": "{{r}}"}, {"r": 50})
    assert out["title"] == "R50 굽힘"
    assert out["n"] == 50  # 섞이지 않은 쪽은 형 그대로


def test_substitute_walks_nested_and_lists():
    out = template.substitute(
        {"sample": {"ap_cx": "{{x}}", "tags": ["{{t}}", "고정"]}}, {"x": 1.5, "t": "WLP"})
    assert out["sample"]["ap_cx"] == 1.5
    assert out["sample"]["tags"] == ["WLP", "고정"]


def test_missing_var_raises():
    with pytest.raises(template.TemplateError):
        template.substitute({"a": "{{nope}}"}, {})


def test_refs_collects_in_order():
    assert template.refs({"a": "{{x}}", "b": ["{{y}}", "{{x}}"]}) == ["x", "y"]


# ── 기계장치 ② 추출 ─────────────────────────────────────────────────────
def test_extract_dot_and_index():
    data = {"ap": {"x": 12.32}, "items": [{"id": "a"}, {"id": "b"}]}
    assert template.extract(data, "ap.x") == 12.32
    assert template.extract(data, "items[1].id") == "b"
    assert template.extract(data, "$.ap.x") == 12.32  # 흔한 표기 허용


def test_extract_unresolved_says_where():
    with pytest.raises(template.TemplateError) as e:
        template.extract({"ap": {}}, "ap.x.y")
    assert "ap.x" in str(e.value)


def test_empty_values_stop_the_step():
    """RA 는 0행 표를 오류 없이 만든다 — 빈 값을 다음 단계로 넘기면 그 사고가 난다."""
    assert all(template.is_empty(v) for v in (None, "", [], {}))
    assert not template.is_empty(0) and not template.is_empty(False)


# ── 저장 시점 거절 ───────────────────────────────────────────────────────
def _spec(steps, vars_=None):
    return ProcedureSpec(title="t", vars=vars_ or [], steps=[Step(**s) for s in steps])


def _hard(errs):
    return [e for e in errs if not e.startswith("warn:")]


def test_must_gate_is_enforced_not_chosen():
    """되돌리기 어려운 도구는 작성자가 게이트를 끌 수 없다."""
    for tool in sorted(MUST_GATE):
        errs = _hard(validate_spec(_spec([{"backend": "reportarchive", "tool": tool}])))
        assert any("gate: human" in e for e in errs), tool
        ok = validate_spec(_spec([{"backend": "reportarchive", "tool": tool,
                                   "gate": "human"}]))
        assert not any("gate: human" in e for e in _hard(ok)), tool


def test_gateway_denied_names_rejected_at_save():
    errs = _hard(validate_spec(_spec([{"backend": "x", "tool": "delete_report"}])))
    assert any("invoke_tool" in e for e in errs)
    errs = _hard(validate_spec(_spec([{"backend": "x", "tool": "slurm_node_set_state"}])))
    assert any("invoke_tool" in e for e in errs)


def test_dry_run_on_unsupported_tool_is_rejected():
    """게이트웨이에 dry_run 처리가 없다 — 없는 도구에 얹으면 조용히 진짜 실행된다."""
    errs = _hard(validate_spec(_spec([
        {"backend": "heax-step_forge", "tool": "list_parts", "args": {"dry_run": True}}])))
    assert any("dry_run" in e for e in errs)
    # 스키마에 있는 도구는 통과한다
    ok = _hard(validate_spec(_spec([
        {"backend": "smart-twin-cluster", "tool": "smarttwin_submit", "gate": "human",
         "args": {"dry_run": True}}])))
    assert not any("dry_run" in e for e in ok)
    assert "smarttwin_submit" in DRY_RUN_TOOLS


def test_expect_job_must_be_split():
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "some_tool", "expect": "job"}])))
    assert any("제출·회수" in e for e in errs)


def test_token_cannot_be_saved_forward():
    """save 로 confirm_token 을 넘기면 RA 2단 확인이 그대로 자동화된다."""
    errs = _hard(validate_spec(_spec([
        {"backend": "reportarchive", "tool": "preview_publish",
         "save": {"confirm_token": "confirm_token"}}])))
    assert any("2단 확인" in e for e in errs)


def test_secret_constant_rejected_but_variable_allowed():
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "some_tool", "args": {"api_key": "AKIA-real-secret"}}])))
    assert any("비밀" in e for e in errs)

    ok = _hard(validate_spec(_spec(
        [{"backend": "b", "tool": "some_tool", "args": {"api_key": "{{k}}"}}],
        [Var(key="k", label="키", type="string")])))
    assert not any("비밀" in e for e in ok)


def test_url_with_userinfo_rejected():
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "some_tool", "args": {"u": "https://a:b@h/x"}}])))
    assert any("계정" in e for e in errs)


def test_unknown_variable_is_caught():
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "some_tool", "args": {"a": "{{ghost}}"}}])))
    assert any("ghost" in e for e in errs)


def test_save_output_feeds_next_step():
    """앞 단계가 만든 값은 뒤 단계가 쓸 수 있다 — 이게 체인의 전부다."""
    errs = _hard(validate_spec(_spec([
        {"backend": "heax-laminate_analyzer_mcp", "tool": "solve_prescribed_curvature",
         "args": {"bend_radius": "{{r}}"}, "save": {"loads": "equivalent_loads"}},
        {"backend": "heax-laminate_analyzer_mcp", "tool": "recover_ply_stresses",
         "args": {"loads": "{{loads}}"}},
    ], [Var(key="r", label="R", type="number")])))
    assert errs == []


def test_reverse_order_is_caught():
    """뒤 단계 산출을 앞 단계가 쓰면 안 된다."""
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "a_tool", "args": {"x": "{{later}}"}},
        {"backend": "b", "tool": "b_tool", "save": {"later": "v"}},
    ])))
    assert any("later" in e for e in errs)


def test_reserved_vars_need_no_declaration():
    errs = _hard(validate_spec(_spec([
        {"backend": "b", "tool": "some_tool",
         "args": {"owner": "{{me.email}}", "t": "{{run_id}}"}}])))
    assert errs == []


def test_raw_step_cannot_save():
    errs = _hard(validate_spec(_spec([
        {"backend": "smart-twin-cluster", "tool": "smarttwin_scenario_options",
         "raw": True, "save": {"x": "a"}}])))
    assert any("raw" in e for e in errs)


def test_max_steps():
    many = [{"backend": "b", "tool": f"t{i}"} for i in range(5)]
    assert any("상한" in e for e in _hard(validate_spec(_spec(many), max_steps=3)))


def test_enum_var_requires_values():
    with pytest.raises(ValueError):
        Var(key="k", label="l", type="enum")


def test_var_coerce_guards_types():
    from app.procedures.models import SpecError

    v = Var(key="pkg_type", label="분류", type="enum", values=["WLP", "FX", "DIG"])
    assert v.coerce("WLP") == "WLP"
    with pytest.raises(SpecError):
        v.coerce("XLP")
    n = Var(key="r", label="R", type="number")
    assert n.coerce("50") == 50.0
    with pytest.raises(SpecError):
        n.coerce(True)  # 불리언은 수치가 아니다


def test_alias_is_what_gets_called():
    """노출 이름은 다른 앱의 가동 여부로 뒤집힌다 — 별칭은 항상 부를 수 있다."""
    st = Step(backend="heax-step_forge", tool="list_parts")
    assert st.alias == "heaxstep_forge_list_parts"
    assert st.cacheable is True
    assert Step(backend="b", tool="job_status").cacheable is False


# ── 스키마 대조 ──────────────────────────────────────────────────────────
def test_unknown_arg_caught_against_schema():
    """게이트웨이는 validate_input=False 라 오타 인자를 백엔드가 조용히 버린다."""
    spec = _spec([{"backend": "heax-step_forge", "tool": "list_parts",
                   "args": {"project_id": "p", "limitt": 5}}])
    schemas = {"heaxstep_forge_list_parts": {
        "properties": {"project_id": {}, "limit": {}}, "required": ["project_id"]}}
    errs = check_against_schemas(spec, schemas)
    assert any("limitt" in e for e in errs)


def test_missing_tool_is_reported():
    """만드는 화면에서는 **안 보인다**고 알려 준다."""
    spec = _spec([{"backend": "odb-hub", "tool": "odb_list_components"}])
    errs = check_against_schemas(spec, {})
    assert any("안 보인다" in e and not e.startswith("warn:") for e in errs), errs


def test_안_보이는_도구는_저장을_막지_않는다():
    """⚠ **없는 것과 내 권한 밖인 것은 다르다.** 카탈로그는 부르는 사람의 권한으로
    필터된다 — 남이 쓸 절차를 만드는 사람이 그 도구를 못 볼 수 있고, 그 앱이 잠깐 안
    붙어 있을 수도 있다. 저장을 막으면 그 셋을 "없다" 로 뭉개는 것이다.

    실제로 이것 때문에 걸렸다 — 테스트가 살아 있는 게이트웨이를 부르는데 그 신원의
    시야에는 step_forge 도구가 없어서, 멀쩡한 씨앗이 저장 거절됐다."""
    spec = _spec([{"backend": "odb-hub", "tool": "odb_list_components"}])
    errs = check_against_schemas(spec, {}, missing_is_error=False)
    assert all(e.startswith("warn:") for e in errs), errs
    assert any("안 보인다" in e for e in errs)


def test_보이는_도구의_인자_오타는_저장에서도_막는다():
    """안 보이는 것은 봐주되, **보이는 도구에서 확실한 것**은 막는다."""
    spec = _spec([{"backend": "heax-step_forge", "tool": "list_parts",
                   "args": {"project_idd": "x"}}])
    gw = {"heaxstep_forge_list_parts": {"properties": {"project_id": {"type": "string"}},
                                        "required": ["project_id"]}}
    errs = check_against_schemas(spec, gw, missing_is_error=False)
    hard = [e for e in errs if not e.startswith("warn:")]
    assert any("project_idd" in e for e in hard), hard
    assert any("project_id" in e and "빠졌다" in e for e in hard), hard


def test_fingerprint_changes_with_schema():
    a = schema_fingerprint("설명", {"properties": {"x": {"type": "string"}}})
    b = schema_fingerprint("설명", {"properties": {"x": {"type": "number"}}})
    assert a != b and len(a) == 16


# ── 저장소 ───────────────────────────────────────────────────────────────
@pytest.fixture
def store(tmp_path):
    s = Settings(procedures_store_path=str(tmp_path / "wb.sqlite"))
    st = ProceduresStore(s)
    yield st
    st.close()


def test_wal_is_on(store):
    """포털 sqlite 4곳은 디스크 실측이 전부 journal_mode=delete 다. 여기는 아니어야 한다."""
    assert store.health()["journal_mode"].lower() == "wal"


def test_run_records_version_and_inputs(store):
    r = store.create_procedure(owner_sub="u1", spec={"title": "t", "steps": []}, title="t")
    run = store.create_run(owner_sub="u1", procedure_version_id=r["version_id"],
                           inputs={"r_min": 50}, origin="replay", mode="live")
    got = store.get_run(run, owner_sub="u1")
    assert got["procedure_version_id"] == r["version_id"]
    assert got["inputs"] == {"r_min": 50}
    assert got["origin"] == "replay"


def test_new_version_bumps_and_keeps_old(store):
    r = store.create_procedure(owner_sub="u1", spec={"n": 1}, title="t")
    v2 = store.add_version(procedure_id=r["id"], author_sub="u1", spec={"n": 2})
    assert v2["version_no"] == 2
    assert store.get_version(r["version_id"])["spec"] == {"n": 1}  # 판본은 불변
    assert store.latest_version_of(r["id"])["spec"] == {"n": 2}


def test_판본은_주인만_덧붙인다(store):
    """**공유는 읽기까지다.** 이 테스트는 원래 `author_sub="u2"` 로 남의 절차에 판본을
    얹고 통과했다 — 게이트가 없다는 뜻이었고, 그대로 라우트까지 뚫려 있었다.
    """
    r = store.create_procedure(owner_sub="u1", spec={"n": 1}, title="t")
    with pytest.raises(KeyError):
        store.add_version(procedure_id=r["id"], author_sub="u2", spec={"n": 9})
    assert store.latest_version_of(r["id"])["spec"] == {"n": 1}, "남이 얹은 것이 최신이 됐다"


def test_볼_수_있는_판본만_내준다(store):
    """`visibility` 는 목록에서만 걸리고 있었다 — id 만 알면 남의 private 이 열렸다."""
    pub = store.create_procedure(owner_sub="u1", spec={"n": 1}, title="공개")
    prv = store.create_procedure(owner_sub="u1", spec={"n": 2}, title="비공개",
                                 visibility="private")
    for who, want_pub, want_prv in (("u1", True, True), ("u2", True, False)):
        assert bool(store.readable_version(sub=who, procedure_id=pub["id"])) is want_pub
        assert bool(store.readable_version(sub=who, procedure_id=prv["id"])) is want_prv
        # 판본 id 로 들어와도 같다 — 게이트는 절차 행에 있고 거슬러 올라가 확인한다
        assert bool(store.readable_version(sub=who, version_id=prv["version_id"])) is want_prv


def test_runs_are_owner_only(store):
    run = store.create_run(owner_sub="u1")
    assert store.get_run(run, owner_sub="u2") is None
    assert store.list_runs(owner_sub="u2") == []


def test_gated_runs_float_to_top(store):
    a = store.create_run(owner_sub="u1", title="a")
    b = store.create_run(owner_sub="u1", title="b")
    store.set_run_state(b, "gated")
    assert store.list_runs(owner_sub="u1")[0]["id"] == b
    assert a in [r["id"] for r in store.list_runs(owner_sub="u1")]


def test_step_result_roundtrip_and_truncation(store):
    run = store.create_run(owner_sub="u1")
    store.begin_step(run, 1, backend="b", tool="t", args={"a": 1})
    store.finish_step(run, 1, ok=True, result_text='{"x":1}', duration_ms=12)
    assert json.loads(store.step_result(run, 1)) == {"x": 1}
    step = store.list_steps(run)[0]
    assert step["state"] == "done" and step["duration_ms"] == 12
    assert step["args"] == {"a": 1} and len(step["args_sha256"]) == 64

    store.begin_step(run, 2, backend="b", tool="t", args={})
    store.finish_step(run, 2, ok=True, result_text="x" * (3 * 1024 * 1024))
    big = store.list_steps(run)[1]
    assert big["truncated"] == 1 and big["result_bytes"] == 3 * 1024 * 1024
    assert len(store.step_result(run, 2)) == 4096  # 프리뷰만 남는다


def test_notes_carry_the_warning(store):
    """W120·합성 데이터 경고가 사라지지 않게 하는 칸이다."""
    run = store.create_run(owner_sub="u1")
    store.begin_step(run, 1, backend="b", tool="estimate_fatigue_life", args={})
    store.finish_step(run, 1, ok=True, result_text="{}",
                      notes={"warnings": ["W120: ply 2 제외"]})
    assert store.list_steps(run)[0]["notes"]["warnings"] == ["W120: ply 2 제외"]


def test_gate_ack_is_bound_to_args(store):
    run = store.create_run(owner_sub="u1")
    store.begin_step(run, 1, backend="reportarchive", tool="publish_report", args={"id": 1})
    sha = store.list_steps(run)[0]["args_sha256"]
    store.ack_gate(run, 1, by="u1", args_sha256=sha)
    assert store.gate_ack(run, 1)["args_sha256"] == sha


def test_restart_marks_unknown_not_failed(store):
    """쓰기가 뒤늦게 완료됐을 수 있다 — 재실행 전에 사람이 본다."""
    run = store.create_run(owner_sub="u1")
    store.set_run_state(run, "running")
    store.begin_step(run, 1, backend="b", tool="create_report_draft", args={})
    assert store.close_stale() == 1
    assert store.list_steps(run)[0]["state"] == "unknown"
    assert store.list_steps(run)[0]["stage"] == "restart"
    assert store.get_run(run, owner_sub="u1")["state"] == "failed"


def test_stats_needs_fields_that_cannot_be_recovered_later(store):
    """§6-1 판정에 쓰는 네 수 — created_by·run_by·origin 이 없으면 영영 못 센다."""
    r = store.create_procedure(owner_sub="author", spec={}, title="t")
    mine = store.create_run(owner_sub="author", procedure_version_id=r["version_id"],
                            origin="replay")
    store.set_run_state(mine, "done", ended=True)
    other = store.create_run(owner_sub="someone", run_by="someone",
                             procedure_version_id=r["version_id"], origin="replay")
    store.set_run_state(other, "done", ended=True)
    s = store.stats()
    assert s["procedures"] == 1 and s["replays"] == 2
    assert s["replays_by_others"] == 1
    assert s["replay_completion"] == 1.0


def test_threads_get_their_own_connection(store):
    """단일 연결을 스레드풀이 나눠 쓰면 트랜잭션 경계가 섞인다 — S5 에서 바로 난다."""
    import threading

    errs: list[Exception] = []

    def work(i):
        try:
            rid = store.create_run(owner_sub=f"u{i}")
            store.begin_step(rid, 1, backend="b", tool="t", args={"i": i})
            store.finish_step(rid, 1, ok=True, result_text=json.dumps({"i": i}))
            assert json.loads(store.step_result(rid, 1))["i"] == i
        except Exception as exc:  # noqa: BLE001
            errs.append(exc)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errs


# ── example 은 기본값이 아니다 ───────────────────────────────────────────────
def test_example_은_형에_맞는지_저장_시점에_본다():
    """예시가 형에 안 맞으면 사람이 버튼을 누른 **뒤** 실행에서야 터진다."""
    from app.procedures.models import Var

    ok = Var(key="laminate", label="적층", type="json", example={"unit_system": "SI_mm"})
    assert ok.example["unit_system"] == "SI_mm"

    with pytest.raises(ValueError, match="example"):
        Var(key="r", label="R", type="number", example="여섯")
    with pytest.raises(ValueError, match="example"):
        Var(key="ax", label="축", type="enum", values=["x", "y"], example="z")


def test_example_이_없으면_아무것도_안_바뀐다():
    """예시는 선택이다 — 안 적은 절차가 달라지면 안 된다."""
    from app.procedures.models import Var

    assert Var(key="p", label="과제").example is None


def test_example_는_required_를_풀어_주지_않는다():
    """**예시는 기본값이 아니다.** 미리 채워 두면 남의 값이 자기 값처럼 보인 채 돌아간다.

    사람이 넣지 않으면 여전히 비어 있고, 필수면 시작에서 걸린다.
    """
    from app.procedures.models import ProcedureSpec, SpecError, coerce_inputs

    spec = ProcedureSpec.model_validate({
        "title": "t",
        "vars": [{"key": "laminate", "label": "적층", "type": "json",
                  "required": True, "example": {"unit_system": "SI_mm"}}],
        "steps": [{"backend": "heax-laminate_analyzer_mcp", "tool": "analyze_laminate",
                   "args": {"laminate": "{{laminate}}"}}],
    })
    with pytest.raises(SpecError, match="적층"):
        coerce_inputs(spec, {})            # 예시가 있어도 자동으로 안 들어간다
    got = coerce_inputs(spec, {"laminate": '{"unit_system": "SI"}'})
    assert got["laminate"] == {"unit_system": "SI"}


# ── 경고 표식 — 모양이 여럿인데 하나만 읽고 있었다(2026-09-15 감사) ─────────
def test_경고가_문자열이어도_읽는다():
    """흔한 모양은 **문자열 목록**인데 dict 의 `code` 만 봤다 — 표의 경고 칸이 늘 비었고,
    빈 칸은 '깨끗하다' 로 읽힌다. '못 읽었다' 가 아니라."""
    from app.procedures.judge import warn_labels

    assert warn_labels({"warnings": ["W120: ply 제외", "W7"]}) == ["W120: ply 제외", "W7"]
    assert warn_labels({"warnings": "W120 하나"}) == ["W120 하나"], "글자를 돌면 0건이 된다"
    assert warn_labels({"warnings": [{"code": "W120"}]}) == ["W120"]
    # `warnings` 말고도 같은 뜻인 칸이 있다
    assert warn_labels({"quality_flags": ["synthetic"]}) == ["synthetic"]
    assert warn_labels({"degenerate": True}) == ["degenerate"]
    # 경고가 아닌 것을 경고로 만들지는 않는다
    assert warn_labels({"notes": "그냥 메모"}) == []
    assert warn_labels(None) == [] and warn_labels({"warnings": []}) == []


def test_비밀_검사가_목록_안도_본다():
    """검사 자리가 dict 를 도는 곳이라, 값이 **목록이면 키를 잃어** 아무 검사도 안 받았다.
    `visibility` 기본이 `all`(공유)이라 그대로 유출이다."""
    from app.procedures.models import _scan_args

    assert _scan_args({"headers": {"Authorization": ["Bearer sk-live-abc"]}}, "1단계")
    assert _scan_args({"urls": ["https://u:p@h/x"]}, "1단계")
    assert _scan_args({"token": "{{tok}}"}, "1단계") == [], "변수는 비밀이 아니다"
    assert _scan_args({"note": "평범한 값"}, "1단계") == []
