# 챗 도구 호출이 **절차 원장**에 제대로 남는가 (PLAN §9-9)
#
# 새 원장을 만들지 않았다. `run_steps` 가 이미 정확한 모양이고 챗이 안 쓸 뿐이었다.
# 여기서 거는 것은 **접는 규칙**이다 — 짝 키가 없으면 접지 않는다. 이름으로 묶으면
# 같은 도구를 N번 부른 턴에서 마지막 인자와 마지막 결과가 붙어 서로 다른 호출이
# 한 줄이 된다(화면이 그렇게 하고 있고, 그래서 §5-5 가 났다).
import pytest

from app.config import Settings
from app.procedures import from_chat
from app.procedures.store import ProceduresStore


@pytest.fixture
def store(tmp_path):
    return ProceduresStore(Settings(procedures_store_path=str(tmp_path / "p.sqlite")))


def _start(call, tool, detail):
    return {"step": f"도구 호출: {tool}", "tool": tool, "call": call, "detail": detail}


def _end(call, tool, result, ok=True):
    return {"step": f"도구 완료: {tool}", "tool": tool, "call": call,
            "ok": ok, "result_preview": result}


# ── 접기 ─────────────────────────────────────────────────────────────────
def test_인자와_결과가_짝_키로_붙는다():
    got = from_chat.pair([_start("r1", "search_voc", '{"keyword":"발열"}'),
                          _end("r1", "search_voc", "[12건]")])
    assert len(got) == 1
    assert got[0]["args_text"] == '{"keyword":"발열"}'
    assert got[0]["result_text"] == "[12건]" and got[0]["ok"] is True


def test_같은_도구를_여러_번_불러도_섞이지_않는다():
    """**이것이 요점이다.** 이름으로 묶으면 다섯 호출이 한 줄이 되고 마지막 인자와
    마지막 결과만 남는다 — 그 둘이 서로 다른 호출일 수 있다(§5-5 predict_sed)."""
    acts = []
    for i in range(5):
        acts.append(_start(f"r{i}", "predict_sed", f'{{"ap_cx":50.{i}}}'))
    for i in range(5):
        acts.append(_end(f"r{i}", "predict_sed", f"SED={i}"))
    got = from_chat.pair(acts)
    assert len(got) == 5, f"{len(got)}줄로 접혔다 — 호출이 섞였다"
    assert [g["args_text"] for g in got] == [f'{{"ap_cx":50.{i}}}' for i in range(5)]
    assert [g["result_text"] for g in got] == [f"SED={i}" for i in range(5)]


def test_짝_키가_없으면_아예_접지_않는다():
    """낡은 이벤트를 이름으로 묶는 것은 **거짓을 물려받는 일**이다. 안 남기는 편이 낫다."""
    acts = [{"step": "도구 호출: x", "tool": "x", "detail": "{}"},
            {"step": "도구 완료: x", "tool": "x", "result_preview": "r"}]
    assert from_chat.pair(acts) == []


def test_성패를_못_받으면_비워_둔다():
    """모른다와 실패했다를 섞으면 안 된다."""
    got = from_chat.pair([_start("r1", "t", "{}"),
                          {"step": "도구 완료: t", "tool": "t", "call": "r1",
                           "result_preview": "r"}])
    assert got[0]["ok"] is None


def test_result_full_이_있으면_그것을_쓴다():
    got = from_chat.pair([_start("r1", "t", "{}"),
                          {"tool": "t", "call": "r1", "ok": True,
                           "result_preview": "짧게", "result_full": "길게" * 100}])
    assert got[0]["result_text"].startswith("길게길게")


# ── 원장에 남기기 ────────────────────────────────────────────────────────
def test_챗_턴이_원장에_실행으로_남는다(store):
    rid = from_chat.record(store, owner_sub="u", conversation_id="c1", title="발열 문의",
                           activity=[_start("r1", "search_voc", '{"keyword":"발열"}'),
                                     _end("r1", "search_voc", "[12건]")])
    assert rid
    run = store.get_run(rid, owner_sub="u")
    assert run["origin"] == "chat" and run["state"] == "done"
    assert run["trigger_kind"] == "conversation" and run["trigger_ref"] == "c1"
    st = run["steps"][0]
    assert st["tool"] == "search_voc" and st["ok"] == 1
    assert store.step_result(rid, 0) == "[12건]", "결과 원문이 원장에 없다"


def test_실패한_호출은_실패로_남는다(store):
    rid = from_chat.record(store, owner_sub="u", conversation_id="c1",
                           activity=[_start("r1", "t", "{}"),
                                     _end("r1", "t", "✖ 호출 실패", ok=False)])
    st = store.get_run(rid, owner_sub="u")["steps"][0]
    assert st["ok"] == 0 and st["error"], "실패가 성공처럼 남았다"


def test_남길_것이_없으면_실행을_안_만든다(store):
    assert from_chat.record(store, owner_sub="u", conversation_id="c1", activity=[]) is None
    assert store.list_runs(owner_sub="u") == []


def test_기록_실패가_챗을_막지_않는다(caplog):
    """챗은 운영 경로다. 원장 쓰기가 터져도 예외가 올라가면 안 된다.

    ⚠ `record` 가 None 을 내는 길은 **둘**이다 — 남길 것이 없거나, 예외를 삼켰거나.
    `is None` 만 보면 그 둘을 못 가른다. 실제로 `pair()` 가 빈 목록을 내면 저장소는
    아예 안 불리는데도 이 검사는 통과했다. **삼켰다는 것까지** 확인한다.
    """
    class Broken:
        called = False

        def create_run(self, **kw):
            Broken.called = True
            raise RuntimeError("디스크 꽉 참")

    with caplog.at_level("INFO"):
        got = from_chat.record(Broken(), owner_sub="u", conversation_id="c",
                               activity=[_start("r1", "t", "{}"), _end("r1", "t", "x")])
    assert got is None
    assert Broken.called, "저장소에 닿지도 않았다 — 다른 이유로 None 이다"
    assert any("남기지 못했다" in r.message for r in caplog.records), \
        "조용히 삼키면 운영에서 원장이 비는 이유를 알 길이 없다"


def test_챗_실행은_재생용_판본이_없다(store):
    """자동으로 절차가 되면 안 된다 — 사람이 보고 뽑을 때 판본이 생긴다."""
    rid = from_chat.record(store, owner_sub="u", conversation_id="c1",
                           activity=[_start("r1", "t", "{}"), _end("r1", "t", "x")])
    assert store.get_run(rid, owner_sub="u")["procedure_version_id"] is None


def test_소요가_원장에_남는다(store):
    """원장에는 duration_ms 칸이 있는데 챗이 안 채우고 있었다(PLAN §9-8)."""
    rid = from_chat.record(store, owner_sub="u", conversation_id="c1",
                           activity=[_start("r1", "t", "{}"),
                                     {"tool": "t", "call": "r1", "ok": True,
                                      "result_preview": "r", "ms": 1234, "ts": 1789}])
    st = store.get_run(rid, owner_sub="u")["steps"][0]
    assert st["duration_ms"] == 1234


def test_성패를_못_받았으면_성공으로_적지_않는다(tmp_path):
    """규율 ③ 이 여기서 깨져 있었다 — `None is not False` 라 **성공**으로 적혔다.

    그러면 `/runs` 에 성공으로 뜨고, 절차로 뽑을 때 `state == "done"` 필터를 통과해
    **검증된 단계인 양** 굳는다. 원장에는 `unknown` 이라는 칸이 이미 있다.
    """
    from app.config import Settings
    from app.procedures.store import ProceduresStore

    st = ProceduresStore(Settings(procedures_store_path=str(tmp_path / "w.sqlite")))
    rid = from_chat.record(st, owner_sub="u1", conversation_id="c1", activity=[
        {"tool": "a", "call": "1", "detail": "{}", "step": "도구 시작"},
        {"tool": "a", "call": "1", "result_preview": "결과", "step": "도구 완료"},   # ok 없음
        {"tool": "b", "call": "2", "detail": "{}", "step": "도구 시작", "ok": True},
        {"tool": "b", "call": "2", "result_preview": "결과", "step": "도구 완료", "ok": True},
    ])
    steps = {s["tool"]: s for s in st.get_run(rid)["steps"]}
    assert steps["a"]["state"] == "unknown", "성패를 모르는 것을 성공으로 적었다"
    assert steps["a"]["error"], "왜 모르는지도 남겨야 한다"
    assert steps["b"]["state"] == "done"
    # 결과는 둘 다 남는다 — 모르는 것은 성패이지 결과가 아니다
    assert st.step_result(rid, steps["a"]["ix"]) == "결과"


def test_잘렸으면_잘렸다고_남긴다(tmp_path):
    """조용히 끊으면 70번 부른 턴이 원장에서는 **완전한** 60단계로 보이고, 거기서 뽑은
    절차는 뒷부분이 통째로 없는 채 '이대로 하면 된다' 가 된다."""
    from app.config import Settings
    from app.procedures.store import ProceduresStore

    acts = []
    for i in range(70):
        acts += [_start(f"c{i}", "t", "{}"), _end(f"c{i}", "t", "x")]
    folded = from_chat.pair(acts)
    assert len(folded) == from_chat.MAX_STEPS
    assert folded[-1].get("truncated") == 10, folded[-1]

    st = ProceduresStore(Settings(procedures_store_path=str(tmp_path / "w.sqlite")))
    rid = from_chat.record(st, owner_sub="u", conversation_id="c", activity=acts)
    last = st.get_run(rid)["steps"][-1]
    assert (last.get("notes") or {}).get("truncated") == 10, last
    # 잘렸어도 그 단계의 결과는 남는다 — 모르는 것은 뒷부분이지 이 단계가 아니다
    assert st.step_result(rid, last["ix"]) == "x"


def test_반쯤_쓴_실행을_도는_중으로_두지_않는다(tmp_path):
    """`create_run` 은 됐는데 단계 쓰기가 터지면, 부르는 쪽은 None('남긴 게 없다')을 받는데
    사용자 `/runs` 에는 잘린 실행이 **도는 중**으로 남았다."""
    from app.config import Settings
    from app.procedures.store import ProceduresStore

    real = ProceduresStore(Settings(procedures_store_path=str(tmp_path / "w.sqlite")))

    class HalfBroken:
        def __init__(self):
            self.rid = None

        def create_run(self, **kw):
            self.rid = real.create_run(**kw)
            return self.rid

        def begin_step(self, *a, **kw):
            raise RuntimeError("디스크 꽉 참")

        def set_run_state(self, *a, **kw):
            return real.set_run_state(*a, **kw)

    s = HalfBroken()
    assert from_chat.record(s, owner_sub="u", conversation_id="c",
                            activity=[_start("r1", "t", "{}"), _end("r1", "t", "x")]) is None
    got = real.get_run(s.rid)
    assert got["state"] == "failed" and got["ended_at"], got
