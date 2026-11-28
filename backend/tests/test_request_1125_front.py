# 문서 붙이기 화면 넷(docs/request-1125) — 그림 · 판독 · 읽지 못한 것 셈(IR-03) · 새 대화에서 칩 비우기(IR-05) · 두 RA 길의 차이(IR-06) · 잠긴 문서(WD-11)
"""셈 함수는 진짜 docAttach.ts 를 esbuild 로 옮겨 node 로 돌린다(esbuild · node 가 없으면 건너뛴다). 화면 배선은 소스를 맞댄다 — 바뀌면 같이 고친다."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
CHAT = FE / "src/components/chat"
# esbuild 는 vite 가 딸고 온 것을 쓴다(test_delib_stop_in_browser 와 같은 길 — pnpm 은 .bin 에 esbuild 를 두지 않는다)
_TRANSFORM = r"""
const { createRequire } = require('module');
const path = require('path');
const fs = require('fs');
const [FE, SRC] = process.argv.slice(1);
const fe = createRequire(path.join(FE, 'package.json'));
const esbuild = createRequire(fe.resolve('vite/package.json'))('esbuild');
const js = esbuild.transformSync(fs.readFileSync(SRC, 'utf8'), { loader: 'ts', format: 'cjs' }).code;
const m = { exports: {} };
new Function('module', 'exports', 'require', js)(m, m.exports, require);
const f = m.exports.figureStats(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify({ ...f, label: m.exports.figureLabel(f) }));
"""

DF_DOC = """---
schema: hwax-doc/1
source: a.pptx
kind: ppt
units: 2
---

# 검토

> **변환 경고**
> - s.2 연결선 3개 — 도형 사이 흐름을 글로 옮기지 못했다
> - s.2 그림 채움 도형 1개

## [s.1] 결과

[그림 1] 막대 차트
> 모델 판독: 막대 4개 — B 가 82

[그림 2] 사진

## [s.2] 흐름
"""
AIDH_DOC = "---\nschema: hwax-doc/1\nsource: a.pptx\nkind: ppt\n---\n\n# t\n\n[그림 1] 사진 — 그림 내용은 글로 옮기지 않았다\n"


def _stats(text: str) -> dict:
    if shutil.which("node") is None or not (FE / "node_modules").exists():
        pytest.skip("node · frontend/node_modules 없음")
    r = subprocess.run(["node", "-e", _TRANSFORM, str(FE), str(CHAT / "docAttach.ts")], input=text, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_DocForge_글의_그림_판독_읽지_못한_것을_센다():
    s = _stats(DF_DOC)
    assert (s["figures"], s["read"]) == (2, 1) and len(s["missed"]) == 2 and s["missed"][1] == "s.2 그림 채움 도형 1개", s
    assert s["label"] == "그림 2 · 판독 1 · 읽지 못한 것 2"


def test_AI_데이터_허브_글은_판독_0_이고_그림이_없으면_칸이_없다():
    s = _stats(AIDH_DOC)
    assert (s["figures"], s["read"], s["missed"], s["label"]) == (1, 0, [], "그림 1 · 판독 0")
    assert _stats("---\nschema: hwax-doc/1\n---\n\n# t\n\n글만\n")["label"] == ""


def test_완료_문구와_칩이_셈을_보이고_판독_0_이면_안내한다():
    panel = (CHAT / "DocDispatchPanel.tsx").read_text(encoding="utf-8")
    assert "const figs = figureStats(done.doc?.text ?? '');" in panel and "figs.figures > 0 && figs.read === 0" in panel
    assert "FIGURES_UNREAD_NOTE" in panel
    att = (CHAT / "docAttach.ts").read_text(encoding="utf-8")
    assert "그림은 읽지 않았습니다 — 그림이 중요하면 슬라이드 캡처를 붙이거나 정밀 변환으로 보내세요." in att
    assert "figs: figureStats(text)" in att, "붙일 때 한 번 센다(칩이 그릴 때마다 2백만 자를 다시 훑지 않게)"
    comp = (CHAT / "Composer.tsx").read_text(encoding="utf-8")
    assert "figureLabel(d.figs)" in comp


def test_새_대화를_열면_붙인_문서와_그림을_비운다():
    ctx = (FE / "src/state/ChatContext.tsx").read_text(encoding="utf-8")
    body = ctx.split("const newConversation = useCallback(() => {", 1)[1].split("}, [", 1)[0]
    assert "setAttachedDocs([]);" in body and "setAttachedImages([]);" in body


def test_두_RA_길의_차이를_보이고_그림_차트_노트가_있으면_정밀_변환을_권한다():
    router = (CHAT / "UploadRouter.tsx").read_text(encoding="utf-8")
    assert "const recRich = rich && both ? 'reportarchive_precise' : undefined;" in router and "두 Report Archive 길의 차이" in router
    panel = (CHAT / "DocDispatchPanel.tsx").read_text(encoding="utf-8")
    ra = panel.split("reportarchive: {", 1)[1].split("},", 1)[0]
    assert "차트 개체 · 발표자 노트 · 그림으로 채운 도형은 빠집니다" in ra and "제목·본문·표·그림이 위젯으로 들어갑니다" not in ra


def test_잠긴_문서는_이_대화에서_분석을_보내지_않는다():
    panel = (CHAT / "DocDispatchPanel.tsx").read_text(encoding="utf-8")
    go = panel.split("const go = async () => {", 1)[1].split("const r = await dispatchUpload", 1)[0]
    assert "destination === 'chat' && staged.locked" in go and "DRM" in go
    api = (FE / "src/api/upload.api.ts").read_text(encoding="utf-8")
    assert "locked?: 'drm' | 'ole';" in api and "doc_features?: { charts: number; notes: number; pictures: number };" in api
