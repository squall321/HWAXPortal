# 웹 심의가 끝난 뒤 서버 대화에 남기는 사본이 줄이지 않은 발언·조항·도구 활동·알림 카드를 담는지 — 원장은 하나다
"""웹 심의(포털 /agent/chat → 에이전트 서버)는 스트림이 끝나면 발언·결정문을 서버 대화 저장소에 쓴다. 이 사본이
다른 기기에서 여는 심의, Claude(MCP)와 GLM 이어가기, 새로고침 뒤 이어하기의 유일한 서버 정본이다(docs/risk-review-redesign
D-21·D-23 — 1백만 토큰 창을 가정하고 잘라내지 않는다, 입구는 둘이고 원장은 하나다).

종전 사본은 이렇게 줄어 있었다.
  - 좌석 발언이 엔진의 **회의 버블용 say**(라운드별 수백 자)였다. 엔진은 줄였을 때 줄이지 않은 글(say_full)을 같은 이벤트에
    따로 싣는데 포털이 읽지 않았다. 그 위에 20,000자에서 표식 없이 한 번 더 잘랐다.
  - 발언 199건을 넘으면 앞쪽을 버렸다(로그 한 줄뿐).
  - 이어하기가 승계하는 조항(non_negotiable)을 1,200자, 반박을 4건·인용 80자에서 조용히 잘랐다.
  - 도구 활동을 60건에서 버리고, 에이전트가 이미 표식을 붙여 보낸 날것(result_full)을 4,000자에서 다시 잘라 표식을 바꿔 달았다.
  - 엔진이 '줄였다·뺐다·유실됐다' 를 알리는 카드(근거 이벤트, notice)를 하나도 남기지 않았다.

입력은 손으로 쓰지 않는다 — 엔진이 실제 스트림에서 뜬 프레임(HWAXAgentServer tests/fixtures/risk_contract/panel_frames.jsonl)을
그대로 흘리고, 길이·건수만 키운 것은 그 프레임을 본떠 만든다.
"""
import json
from pathlib import Path

import httpx
import pytest

_FIXTURE = (Path(__file__).resolve().parents[2].parent / "HWAXAgentServer" / "tests" / "fixtures"
            / "risk_contract" / "panel_frames.jsonl")


def _engine_frames() -> list[tuple[str, dict]]:
    if not _FIXTURE.exists():
        pytest.skip(f"형제 리포의 엔진 프레임 예제가 없다: {_FIXTURE}")
    out = []
    for line in _FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            out.append((f["event"], f["data"]))
    return out


def _turn_template() -> dict:
    """엔진이 실제로 낸 turn 프레임 하나 — 버블(say)과 줄이지 않은 글(say_full)이 갈린 것."""
    for ev, d in _engine_frames():
        if ev == "delib" and d.get("kind") == "turn" and d.get("say_full"):
            return dict(d)
    pytest.fail("엔진 예제에 say_full 이 있는 turn 프레임이 없다 — 예제를 다시 떴으면 이 시험을 고쳐라")


def _sse(frames: list[tuple[str, dict]]) -> bytes:
    body = "".join(f"event: {ev}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n" for ev, d in frames)
    return (body + 'event: delib\ndata: {"kind": "decision", "text": "결정문"}\n\nevent: done\ndata: {}\n\n').encode()


class _Body(httpx.AsyncByteStream):
    def __init__(self, raw: bytes, step: int = 7001) -> None:
        self.raw, self.step = raw, step

    async def __aiter__(self):
        # 청크를 프레임 경계와 어긋나게 쪼갠다 — 릴레이는 완결 프레임만 파싱한다
        for i in range(0, len(self.raw), self.step):
            yield self.raw[i:i + self.step]


@pytest.fixture()
def run():
    """프레임 목록을 에이전트 서버 자리에서 흘리고, 저장된 서버 대화의 메시지를 돌려준다."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])

    def go(frames: list[tuple[str, dict]], step: int = 7001) -> list[dict]:
        with TestClient(app) as c:
            real = app.state.agent_client
            raw = _sse(frames)
            app.state.agent_client = httpx.AsyncClient(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, stream=_Body(raw, step), headers={"content-type": "text/event-stream"})))
            try:
                cid = c.post("/agent/conversations", json={"title": "t", "kind": "deliberation"}).json()["id"]
                r = c.post("/agent/chat", json={"message": "/심의 x", "conversation_id": cid})
                assert r.status_code == 200 and "결정문" in r.text
                return c.get(f"/agent/conversations/{cid}").json()["messages"]
            finally:
                app.state.agent_client = real

    try:
        yield go
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)


def _personas(msgs: list[dict]) -> list[dict]:
    return [m for m in msgs if m["role"] == "persona"]


# ── 특성화 — 고치기 전 코드에서도 초록이어야 한다 ─────────────────────────────────────────────
def test_줄이지_않은_짧은_발언은_종전대로_say_그대로다(run):
    t = {k: v for k, v in _turn_template().items() if k not in ("say_full", "say_full_chars")}
    msgs = run([("delib", t)])
    (p,) = _personas(msgs)
    assert p["content"] == t["say"] and p["persona"] == t["persona"] and p["round"] == t["display_round"]
    assert "say" not in (p["meta"] or {}), "버블과 본문이 같으면 따로 적지 않는다"
    assert [m["role"] for m in msgs] == ["user", "persona", "assistant"] and msgs[-1]["content"] == "결정문"


# ── 재현 — 고치기 전 코드에서 붉다 ───────────────────────────────────────────────────────────
def test_엔진이_버블로_줄인_발언은_줄이지_않은_글로_남긴다(run):
    """**이 시험이 이 파일의 이유다** — 엔진이 실제로 낸 프레임 그대로다. 버블은 meta.say 로 남겨 화면이 쓴다."""
    frames = _engine_frames()
    turns = [d for ev, d in frames if ev == "delib" and d.get("kind") == "turn"]
    msgs = run(frames)
    got = _personas(msgs)
    assert [p["content"] for p in got] == [t["say_full"] for t in turns], "서버 사본이 회의 버블(say)이다"
    assert [p["meta"]["say"] for p in got] == [t["say"] for t in turns], "버블을 잃으면 화면이 원문 전체를 버블에 그린다"


def test_발언을_2만자에서_자르지_않는다(run):
    t = _turn_template()
    long = (t["say_full"] + "\n") * 60
    assert len(long) > 25_000
    msgs = run([("delib", {**t, "say_full": long, "say_full_chars": len(long)})])
    (p,) = _personas(msgs)
    assert p["content"] == long, f"{len(long):,}자 발언이 {len(p['content']):,}자로 남았다"
    assert "say_full_chars" not in p["meta"], "엔진이 줄이지 않았으면 원래 길이 표식은 없다"


def test_엔진이_줄이지_않은_글마저_줄였으면_원래_길이를_남긴다(run):
    """엔진은 say_full 을 DELIB_TRANSCRIPT_CLIP 에서 자르고 원래 길이(say_full_chars)를 같이 싣는다 — 그 표식을 버리면 조용한 절단이다."""
    t = _turn_template()
    msgs = run([("delib", {**t, "say_full_chars": len(t["say_full"]) + 5000})])
    (p,) = _personas(msgs)
    assert p["meta"]["say_full_chars"] == len(t["say_full"]) + 5000


def test_발언이_199건을_넘어도_앞쪽을_버리지_않는다(run):
    t = _turn_template()
    frames = [("delib", {**t, "persona": f"seat-{i:03d}", "round": 1 + i // 21, "display_round": 1 + i // 21})
              for i in range(230)]
    got = _personas(run(frames))
    assert len(got) == 230 and got[0]["persona"] == "seat-000", f"{len(got)}건만 남았다(첫 좌석 {got[0]['persona']})"


def test_조항과_반박을_자르지_않는다(run):
    """조항은 이어하기가 승계한다(웹 continueDeliberation 이 서버 사본의 meta 에서 되살린다) — 1,200자에서 끊으면 승계된 조항이 반쪽이다."""
    t = _turn_template()
    nn = "양보 불가 — " + "힌지 간극 0.2 mm 이하에서는 반드시 마모 시험을 먼저 한다. " * 60
    rebut = [{"target": f"seat-{i}", "quote": "브래킷 두께 0.6 mm 는 충분하다는 주장 " * 8,
              "counter": "낙하 시 힌지 응력이 항복을 넘는다는 해석 결과가 있다 " * 8, "basis": "[e:3] 해석 " * 10}
             for i in range(6)]
    msgs = run([("delib", {**t, "round": 3, "display_round": 3, "stance": "조건부 찬성", "non_negotiable": nn,
                           "rebut": rebut})])
    (p,) = _personas(msgs)
    assert p["meta"]["non_negotiable"] == nn, f"조항 {len(nn):,}자가 {len(p['meta']['non_negotiable']):,}자로 남았다"
    assert p["meta"]["rebut"] == rebut, "반박의 건수나 글이 줄었다"
    assert p["meta"]["stance"] == "조건부 찬성"


def test_도구_활동을_60건에서_자르지_않고_에이전트가_보낸_날것을_다시_자르지_않는다(run):
    """에이전트는 날것을 HANDOFF_RESULT_CHARS 에서 자르고 `…#sha6` 표식을 붙여 보낸다. 포털이 4,000자에서 한 번 더 자르면
    그 표식이 떨어지고 제 표식이 붙는다 — 에이전트 손잡이를 올려도 서버 사본은 4,000자에 묶여 있었다."""
    status = next(d for ev, d in _engine_frames() if ev == "status" and d.get("tool"))
    full = '{"rows": [' + ", ".join(f'{{"id": {i}, "E_GPa": 2.{i % 10}}}' for i in range(600)) + "]}"
    sent = full[:4000] + "…#a1b2c3"                       # 에이전트 _tool_preview 의 모양
    frames = [("status", {**status, "call": f"call-{i}", "step": f"조회 {i}", "detail_full": '{"q": "' + "P" * 4500 + '"}',
                          "result_full": sent if i == 0 else f"결과 {i}"})
              for i in range(75)]
    msgs = run(frames)
    act = msgs[-1]["meta"]["activity"]
    assert len(act) == 75, f"도구 활동 75건 중 {len(act)}건만 남았다"
    assert act[0]["result_full"] == sent, "에이전트가 보낸 날것과 표식이 그대로여야 한다"
    assert act[0]["detail_full"].endswith('"}') and len(act[0]["detail_full"]) > 4500


def test_근거와_알림_카드를_서버_사본에_남긴다(run):
    """엔진이 '줄였다·뺐다' 를 알리는 길은 근거 이벤트(included=false · notice) 하나다 — 서버 사본에 없으면 다른 기기와
    새로고침 뒤에는 그 알림이 사라진다. 좌석이 조회한 근거(included=true)는 이어하기가 승계한다(priorGatheredEvidence)."""
    frames = _engine_frames()
    notice = {"kind": "evidence", "source": "요청 값 상한 초과", "included": False, "notice": True,
              "text": "continue_summary 31,000자 중 앞 8,000자만 실었다."}
    frames = frames + [("delib", notice)]
    msgs = run(frames)
    want = [{k: v for k, v in d.items() if k != "kind"} for ev, d in frames
            if ev == "delib" and d.get("kind") == "evidence"]
    assert msgs[-1]["role"] == "assistant"
    assert msgs[-1]["meta"]["delib_evidence"] == want


def test_글자_경계에서_갈린_청크도_깨지지_않는다(run):
    """에이전트 서버의 청크는 글자 경계를 모른다. 청크마다 따로 풀면 갈린 한글 한 자가 '�' 로 서버 사본에 들어간다 —
    줄이지 않은 발언(수만 자)을 남기게 되면서 거의 매번 걸린다. 2바이트씩 흘려 모든 경계를 지나게 한다."""
    t = _turn_template()
    got = _personas(run([("delib", t)], step=2))
    assert got[0]["content"] == t["say_full"] and "\ufffd" not in got[0]["content"]


# ── 소비자 — 웹이 서버 사본을 되살리는 자리(conversations.api.ts serverMessagesToLocal) ─────────────────────
# 입력은 위와 같은 길로 만든다(엔진 프레임 → 포털 저장 → GET). 프론트에는 단위 시험 러너가 없어 그 파일을 옮겨 적어 node 로 부른다.
_FE = Path(__file__).resolve().parents[2] / "frontend"


def _restore(server_messages: list[dict]) -> list[dict]:
    import shutil
    import subprocess
    import tempfile

    if not (_FE / "node_modules/typescript").exists() or not shutil.which("node"):
        pytest.skip("frontend node_modules(typescript) 또는 node 가 없다")
    out = Path(tempfile.mkdtemp(prefix="conv-restore-"))
    (out / "api").mkdir()
    (out / "state").mkdir()
    (out / "api" / "client.js").write_text("exports.apiFetch = async () => { throw new Error('시험에서 부르지 않는다'); };\n")
    (out / "in.json").write_text(json.dumps(server_messages, ensure_ascii=False), encoding="utf-8")
    (out / "build.cjs").write_text(
        "const ts = require('typescript'); const fs = require('fs');\n"
        f"const src = {json.dumps(str(_FE / 'src'))};\n"
        "for (const [from, to] of [['api/conversations.api.ts', 'api/conversations.api.js'], ['state/chatStore.ts', 'state/chatStore.js']]) {\n"
        "  const js = ts.transpileModule(fs.readFileSync(src + '/' + from, 'utf8'),\n"
        "    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });\n"
        "  fs.writeFileSync(__dirname + '/' + to, js.outputText);\n"
        "}\n"
        "const { serverMessagesToLocal } = require('./api/conversations.api.js');\n"
        "const msgs = JSON.parse(fs.readFileSync(__dirname + '/in.json', 'utf8'));\n"
        "process.stdout.write(JSON.stringify(serverMessagesToLocal(msgs)));\n", encoding="utf-8")
    r = subprocess.run(["node", "build.cjs"], cwd=str(out), capture_output=True, text=True, timeout=120,
                       env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                            "NODE_PATH": str(_FE / "node_modules")})
    shutil.rmtree(out, ignore_errors=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def test_웹은_되살린_심의에서_버블을_그리고_줄이지_않은_글과_알림을_쥔다(run):
    frames = _engine_frames() + [("delib", {"kind": "evidence", "source": "좌석 유실", "included": False, "notice": True,
                                            "text": "therm-c 좌석이 응답하지 않았다."})]
    turns = [d for ev, d in frames if ev == "delib" and d.get("kind") == "turn"]
    local = _restore(run(frames))
    delib = local[-1]["delib"]
    assert [t["say"] for t in delib["turns"]] == [t["say"] for t in turns], "화면 버블은 라이브와 같아야 한다"
    assert [t.get("sayFull") for t in delib["turns"]] == [t["say_full"] for t in turns]
    notes = [e for e in delib["evidence"] if e.get("notice")]
    assert notes == [{"source": "좌석 유실", "text": "therm-c 좌석이 응답하지 않았다.", "included": False, "notice": True}]
    assert any(e["included"] and " · " in e["source"] for e in delib["evidence"]), "좌석이 조회한 근거 — 이어하기가 승계한다"


def test_MCP_가_저장한_발언은_종전대로_본문이_버블이다():
    """MCP(게이트웨이 save_conversation·JS 파이프라인)는 버블을 따로 두지 않는다 — 본문을 그대로 그린다(종전)."""
    local = _restore([{"role": "persona", "persona": "mech-a", "round": 1, "content": "발언 본문", "meta": None, "ts": 1},
                      {"role": "assistant", "persona": None, "round": None, "content": "결정문", "meta": None, "ts": 2}])
    (t,) = local[-1]["delib"]["turns"]
    assert t["say"] == "발언 본문" and "sayFull" not in t and "evidence" not in local[-1]["delib"]
