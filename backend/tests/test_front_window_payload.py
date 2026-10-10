# 웹이 엔진·에이전트 서버에 보내는 글을 프론트에서 먼저 자르지 않는지 — 이력·이어하기 요약·조항·근거·브라우저 사본
"""포털 프론트는 엔진에 보낼 글을 만드는 곳이다. 1백만 토큰 창을 가정하면(docs/risk-review-redesign D-21) 여기서 먼저
자르는 자리가 가장 조용하다 — 엔진의 절단 알림은 엔진이 받은 것만 말할 수 있다. 종전 자리는 이렇다.

  - 챗 이력: 메시지마다 머리 24,000자 · 합계 600,000자(ChatContext.buildHistory). 결정문(13,000~75,000자)이 든 대화를
    이어가면 결정문 뒤쪽이 이력에서 빠졌다. 심의 브리프의 화두·좌석 추천은 40건 × 4,000자였다(HandoffBrief).
  - 이어하기: 이전 결정문을 머리 8,000자, 조항을 12건에서 잘라 보내 엔진의 '요청 값 상한 초과' 카드가 영영 안 떴다.
  - 근거: 대화 근거·이어하기 승계 근거를 120건에서 말없이 끊었다.
  - 도구 활동을 메시지당 60건에서 버렸다.
  - 브라우저 사본(localStorage)은 쿼터 때문에 줄인다(활동 60건·날것 14,000자·발언 45건·근거 4건). 그건 남기되 줄였다는 표식을
    남기고, 서버 정본이 있으면 열 때 줄인 칸을 되채운다.

프론트에는 단위 시험 러너가 없다 — 함수가 있는 TS 파일을 옮겨 적어(transpile) node 로 부른다. React 컴포넌트 안의 자리는 소스에서
그 자리만 읽는다(이 리포의 다른 프론트 시험과 같은 방식).
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.agent import routes as R

_FE = Path(__file__).resolve().parents[2] / "frontend"
_SRC = _FE / "src"

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 함수를 돌려 볼 수 없다",
)


def _node(files: list[str], script: str, data) -> object:
    """files(src 기준 경로)를 CommonJS 로 옮겨 적고 script 를 돌린다. script 는 `input` 을 읽고 `out(값)` 으로 돌려준다."""
    out_dir = Path(tempfile.mkdtemp(prefix="fe-window-"))
    try:
        (out_dir / "api").mkdir()
        (out_dir / "api" / "client.js").write_text("exports.apiFetch = async () => { throw new Error('시험에서 부르지 않는다'); };\n")
        (out_dir / "in.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        (out_dir / "run.cjs").write_text(
            "const ts = require('typescript'); const fs = require('fs'); const path = require('path');\n"
            f"const src = {json.dumps(str(_SRC))};\n"
            f"for (const rel of {json.dumps(files)}) {{\n"
            "  const js = ts.transpileModule(fs.readFileSync(src + '/' + rel, 'utf8'),\n"
            "    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });\n"
            "  const to = path.join(__dirname, rel.replace(/\\.tsx?$/, '.js'));\n"
            "  fs.mkdirSync(path.dirname(to), { recursive: true }); fs.writeFileSync(to, js.outputText);\n"
            "}\n"
            "const store = {}; global.localStorage = { getItem: k => (k in store ? store[k] : null),\n"
            "  setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };\n"
            "const input = JSON.parse(fs.readFileSync(path.join(__dirname, 'in.json'), 'utf8'));\n"
            "const out = v => process.stdout.write(JSON.stringify(v));\n"
            + script, encoding="utf-8")
        r = subprocess.run(["node", "run.cjs"], cwd=str(out_dir), capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(_FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def _msg(role: str, text: str, **kw) -> dict:
    return {"id": f"{role}-{len(text)}-{kw.get('n', 0)}", "role": role, "text": text, **{k: v for k, v in kw.items() if k != "n"}}


# ── 챗 이력 ──────────────────────────────────────────────────────────────────────────────
def _history(messages: list[dict]) -> list[dict]:
    return _node(["components/chat/history.ts"],
                 "const { buildHistory } = require('./components/chat/history.js'); out(buildHistory(input));", messages)


def test_이력은_결정문을_자르지_않는다():
    """**이 구획의 이유다** — 75,000자 결정문이 든 대화를 이어가면 결정문 뒤쪽((5)뒤집힘·(7)신뢰도·risk_spec)이 빠졌다."""
    decision = "(1) 결론 " + "가" * 75_000 + " (7) 신뢰도 — 끝"
    got = _history([_msg("user", "/심의 x"), _msg("assistant", decision), _msg("user", "", error="실패")])
    assert got == [{"role": "user", "content": "/심의 x"}, {"role": "assistant", "content": decision}]


def test_이력_상한은_포털과_같은_수다():
    """항목 수는 포털 ChatRequest.history 와, 합계는 포털 _WINDOW_CHARS 와 같아야 한다 — 크면 422, 작으면 조용히 버린다."""
    src = (_SRC / "components/chat/history.ts").read_text(encoding="utf-8")
    items = int(re.search(r"^export const HISTORY_MAX_ITEMS = ([\d_]+);", src, re.M).group(1).replace("_", ""))
    total = int(re.search(r"^export const HISTORY_MAX_TOTAL_CHARS = ([\d_]+);", src, re.M).group(1).replace("_", ""))
    cap = [m.max_length for m in R.ChatRequest.model_fields["history"].metadata if getattr(m, "max_length", None)][0]
    assert items == cap and total == R._WINDOW_CHARS


def test_이력_합계를_넘는_오래된_턴만_뺀다():
    big = "가" * (R._WINDOW_CHARS // 2)
    got = _history([_msg("user", "아주 오래된 질문", n=1), _msg("assistant", big, n=2), _msg("user", big, n=3)])
    assert [len(m["content"]) for m in got] == [len(big), len(big)], "가장 오래된 턴만 빠져야 한다(포털 422 를 피한다)"


def test_챗과_브리프가_같은_이력_함수를_쓴다():
    ctx = (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")
    brief = (_SRC / "components/chat/HandoffBrief.tsx").read_text(encoding="utf-8")
    assert "from '../components/chat/history'" in ctx and "function buildHistory" not in ctx
    assert "buildHistory(conv.messages)" in brief
    assert not re.search(r"\.slice\(-40\)", brief) and "m.text.slice(0, 4000)" not in brief, "브리프가 이력을 따로 자른다"


# ── 이어하기 ─────────────────────────────────────────────────────────────────────────────
def _continue_block() -> str:
    ctx = (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")
    blk = ctx[ctx.index("const continueDeliberation = useCallback("):]
    return blk[:blk.index("const startHandoff = useCallback(")]


def test_이어하기는_결정문과_조항을_프론트에서_자르지_않는다():
    """엔진이 상한에서 줄이고 카드로 알린다(req_cut). 프론트가 정확히 그 수로 미리 자르면 그 카드가 영영 안 뜬다."""
    blk = _continue_block()
    assert "slice(0, 8000)" not in blk and "8000 -" not in blk, "이어하기 요약을 8,000자에서 자른다"
    assert ".slice(0, 12)" not in blk, "조항을 12건에서 자른다"
    assert "continue_summary: (prior.decision ?? '') + priorIssueBlock(prior.turns)" in blk


# ── 근거 ─────────────────────────────────────────────────────────────────────────────────
def _conv_evidence(n: int) -> dict:
    acts = [{"ts": i, "step": f"조회 {i}", "tool": "list_materials", "result_full": f"결과 {i} " + "가" * 10}
            for i in range(n)]
    return {"id": "c", "title": "t", "createdAt": 0, "updatedAt": 0, "messages": [_msg("assistant", "답", activity=acts)]}


def test_대화_근거는_120건에서_말없이_끊지_않는다():
    """상한은 보내기 직전 한 자리(sendMessage)에서 걸고, 넘친 수를 그 답의 알림 카드로 남긴다."""
    got = _node(["components/chat/handoff.ts"],
                "const h = require('./components/chat/handoff.js'); out(h.conversationEvidence(input).length);",
                _conv_evidence(130))
    assert got == 130
    ctx = (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")
    assert "사전 근거 건수 초과" in ctx and "notice: true" in ctx, "넘친 근거를 알리는 카드가 없다"


def test_이어하기_승계_근거도_말없이_끊지_않는다():
    ev = [{"source": f"mech-a · list_materials", "text": f"결과 {i}", "included": True} for i in range(130)]
    got = _node(["components/chat/handoff.ts"],
                "const h = require('./components/chat/handoff.js'); out(h.priorGatheredEvidence(input).length);", ev)
    assert got == 130


def test_도구_활동을_메시지당_60건에서_버리지_않는다():
    ctx = (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")
    assert "prev.slice(-59)" not in ctx


# ── 브라우저 사본 — 줄이되 표식을 남기고, 서버 정본으로 되채운다 ───────────────────────────────
def test_브라우저_사본을_줄였으면_표식을_남긴다():
    acts = [{"ts": i, "step": f"s{i}", "tool": "t", "result_full": "가" * 400} for i in range(70)]
    turns = [{"round": 1, "persona": f"p{i}", "say": "버블", "sayFull": "전체", "ts": 0} for i in range(50)]
    convs = [
        {"id": "big", "title": "t", "createdAt": 0, "updatedAt": 0, "serverId": "s-big",
         "messages": [_msg("user", "q"), _msg("assistant", "d", activity=acts, delib={"turns": turns})]},
        {"id": "small", "title": "t", "createdAt": 0, "updatedAt": 0, "serverId": "s-small",
         "messages": [_msg("user", "q"), _msg("assistant", "d")]},
    ]
    got = _node(["state/chatStore.ts"],
                "const s = require('./state/chatStore.js'); s.saveConversations(input);"
                " out(s.loadConversations().map(c => [c.id, !!c.cacheTrimmed]));", convs)
    assert got == [["big", True], ["small", False]]


def test_열면_줄인_칸을_서버_정본으로_되채운다():
    local = [_msg("user", "q"), _msg("assistant", "결정문", activity=[{"ts": 1, "step": "s", "tool": "t"}],
                                    delib={"turns": [{"round": 1, "persona": "p", "say": "버블", "ts": 0}],
                                           "outcome": {"report_id": 7, "title": "보고서"}})]
    fresh = [_msg("user", "q"), _msg("assistant", "결정문",
                                    activity=[{"ts": 1, "step": "s", "tool": "t", "result_full": "날것 전체"}],
                                    delib={"turns": [{"round": 1, "persona": "p", "say": "버블", "sayFull": "전체", "ts": 0}],
                                           "evidence": [{"source": "좌석 유실", "text": "x", "included": False, "notice": True}]})]
    got = _node(["api/conversations.api.ts", "state/chatStore.ts"],
                "const a = require('./api/conversations.api.js'); out(a.fillTrimmed(input[0], input[1]));", [local, fresh])
    assert got[1]["activity"][0]["result_full"] == "날것 전체"
    assert got[1]["delib"]["turns"][0]["sayFull"] == "전체" and got[1]["delib"]["evidence"][0]["notice"] is True
    assert got[1]["delib"]["outcome"]["report_id"] == 7, "서버 사본에 없는 칸(보고서 번호)은 브라우저 사본을 둔다"
    mismatch = _node(["api/conversations.api.ts", "state/chatStore.ts"],
                     "const a = require('./api/conversations.api.js'); out(a.fillTrimmed(input[0], input[1]));",
                     [local, fresh[:1]])
    assert mismatch is None, "모양이 다르면 손대지 않는다"
    ctx = (_SRC / "state/ChatContext.tsx").read_text(encoding="utf-8")
    assert "conv.cacheTrimmed" in ctx and "fillTrimmed(" in ctx, "열 때 되채우는 자리가 없다"


def test_근거_곁_필드를_프론트에서_미리_자르지_않는다():
    """출처·도구·인자는 엔진이 같은 상한(200·80·1,200)에서 끊고 원문 길이를 남긴다 — 프론트가 같은 값으로 먼저 끊으면 그 표식이 영영 안 붙는다."""
    step = "조회 — " + "가" * 300
    conv = {"id": "c", "title": "t", "createdAt": 0, "updatedAt": 0,
            "messages": [_msg("assistant", "답", activity=[{"ts": 0, "step": step, "tool": "list_materials",
                                                          "detail": "인자 " * 700, "result_full": "결과"}])]}
    got = _node(["components/chat/handoff.ts"],
                "const h = require('./components/chat/handoff.js'); out(h.conversationEvidence(input));", conv)
    assert got[0]["source"] == step and len(got[0]["args"]) == len(("인자 " * 700).strip())
