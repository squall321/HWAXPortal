# 웹 핸드오프(챗 → 심의)가 근거를 포털 상한보다 먼저 자르지 않는지 — 고른 VOC 와 대화 근거를 합치는 자리
"""왜 — 근거 칸은 세 계층이 같은 값이어야 한다(포털 DelibOpts.evidence · 프론트 EVID_ITEMS · 엔진 _EVID_ITEMS). 하나만 작으면
거기서 잘린다. 엔진 요청 4-1 이 셋을 120 으로 올렸는데 **네 번째 자리**가 있었다 — 브리프에서 고른 VOC 와 대화 근거를 합치는
`mergeEvidence` 가 기본값 12 로 잘랐다. 그 12 는 정책이 아니라 포털 상한이 12 이던 때의 값을 따로 적어 둔 것이다(주석이 그렇게
말한다 — "DelibOpts.evidence 가 max_length=12 라"). 상한이 40 · 120 으로 오르는 동안 웹 핸드오프 길만 12건에서 잘렸고,
이어하기 길은 같은 파일에서 이미 EVID_ITEMS 를 쓴다. 엔진은 넘치는 근거를 버릴 때 카드로 알리므로(건수·예산 초과) 여기서 미리
자를 까닭이 없다.

함수를 실제로 돌린다 — 프론트에 단위 시험 러너가 없어 TypeScript 를 한 파일씩 옮겨 적어(transpile) node 로 부른다.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.agent.routes import DelibOpts

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
CHAT = FE / "src/components/chat"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 함수를 돌려 볼 수 없다",
)


@pytest.fixture(scope="module")
def merge(tmp_path_factory):
    """vocEvidence.ts 와 그것이 값으로 끌어오는 handoff.ts 를 CommonJS 로 옮겨 적고 mergeEvidence 를 부른다."""
    out = tmp_path_factory.mktemp("voc")
    (out / "build.cjs").write_text(
        "const ts = require('typescript'); const fs = require('fs');\n"
        "for (const name of ['vocEvidence', 'handoff']) {\n"
        f"  const src = fs.readFileSync({json.dumps(str(CHAT))} + '/' + name + '.ts', 'utf8');\n"
        "  const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } });\n"
        "  fs.writeFileSync(__dirname + '/' + name + '.js', js.outputText);\n"
        "}\n"
        "const { mergeEvidence } = require('./vocEvidence.js'); const { EVID_ITEMS } = require('./handoff.js');\n"
        "const [voc, conv] = process.argv.slice(2).map(Number);\n"
        "const r = mergeEvidence(Array.from({ length: voc }, (_, i) => 'v' + i), Array.from({ length: conv }, (_, i) => 'c' + i));\n"
        "process.stdout.write(JSON.stringify({ ...r, cap: EVID_ITEMS }));\n")

    def run(voc: int, conv: int) -> dict:
        r = subprocess.run(["node", "build.cjs", str(voc), str(conv)], cwd=str(out), capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return run


def test_합친_근거를_12건에서_자르지_않는다(merge):
    """**이 시험이 이 파일의 이유다** — 대화에서 도구를 열세 번 넘게 부른 뒤 심의로 넘기면 열세 번째부터 사라졌다."""
    got = merge(3, 20)
    assert len(got["merged"]) == 23 and got["droppedConv"] == 0
    assert got["merged"][:3] == ["v0", "v1", "v2"], "사람이 고른 VOC 가 앞이다"


def test_합친_근거의_상한은_포털_상한이다(merge):
    cap = DelibOpts.model_fields["evidence"].metadata[0].max_length
    got = merge(5, cap)
    assert got["cap"] == cap, "프론트 상수와 포털 스키마가 갈렸다(test_continue_evidence 가 같은 것을 본다)"
    assert len(got["merged"]) == cap, "포털 상한을 넘기면 422 로 심의가 시작조차 안 된다"
    assert got["droppedConv"] == 5 and got["merged"][4] == "v4" and got["merged"][-1] == f"c{cap - 6}", "넘치면 대화 근거의 뒤쪽이 빠진다"
    assert merge(0, cap)["droppedConv"] == 0 and merge(0, 0)["merged"] == []


def test_화면이_보이는_수와_실리는_수가_같은_상수를_쓴다():
    """브리프는 '원천 근거 N건' · '대화 근거 M건은 상한으로 빠집니다' 를 보인다 — 실리는 수는 mergeEvidence 가 정한다.
    화면만 옛 숫자를 따로 들고 있으면 120건을 싣고 12건이라고 말한다."""
    brief = (CHAT / "HandoffBrief.tsx").read_text(encoding="utf-8")
    assert "Math.min(EVID_ITEMS, vocEv.length + evidence.length)" in brief
    assert not re.search(r"Math\.min\(\s*12\s*,", brief) and "12건" not in brief
    for path in (CHAT / "vocEvidence.ts", FE / "src/state/ChatContext.tsx"):
        src = path.read_text(encoding="utf-8")
        assert "max_length=12" not in src and "합쳐 12건" not in src and "합쳐서 12건" not in src, f"{path.name} 의 주석이 옛 상한을 말한다"
