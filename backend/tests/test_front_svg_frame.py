# 챗의 같은 출처 SVG 그림을 격리 iframe 으로 — 어떤 주소를 iframe 으로 그리는지 · 칸 맞춤 배율 · iframe 이 스크립트도 같은 출처도 막는지(docs/report-figures RF-36)
"""사용자 결정 11-05 — StepForge a81 의 `format="svg_live"` 는 파트 위 이름 · 경로 풍선과 간극 치수를 SVG 안의 CSS(`:has()`)로만 띄운다. 챗은 그림을
`<img>` 로 그려 호버가 죽었다. 같은 출처 `.svg` 는 `<iframe sandbox="">` 로 그리고, SVG 문서가 자기 크기로 그려지므로 원래 크기의 iframe 을 배율로 줄인다.

판정 셈은 화면 코드를 CommonJS 로 옮겨 node 로 돌린다(tests/test_front_window_payload.py 의 _node). 격리(빈 sandbox)는 소스로 단언한다 — 화면 부품은 node
로 그려 보지 않는다.
"""
import re
import shutil

import pytest

from tests.test_front_window_payload import _FE, _SRC, _node

pytestmark = pytest.mark.skipif(
    not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_MOD = "components/chat/renderers/svgFrame.ts"


def _run(script: str, data=None):
    return _node([_MOD], "const m = require('./components/chat/renderers/svgFrame.js');" + script, data)


def test_같은_출처의_svg_주소만_iframe_으로_그린다():
    cases = ["/agent/artifacts/0a1b2c3d4e5f60718293.svg", "/agent/artifacts/X.SVG?v=2#top", "/agent/artifacts/a.png",
             "https://other.example/x.svg", "//other.example/x.svg", "data:image/svg+xml;base64,AAAA", "x.svg", "/a.svg.png", ""]
    got = _run("out(input.map(m.isSvgFrameSrc));", cases)
    assert got == [True, True, False, False, False, False, False, False, False], list(zip(cases, got))


def test_칸_맞춤은_넘칠_때만_줄이고_한참_넓으면_줄이지_않고_가로_스크롤이다():
    got = _run("out([m.svgFrameFit(760, 400, 900, 1.5), m.svgFrameFit(1000, 500, 800, 1.5), m.svgFrameFit(1520, 400, 800, 1.5),"
               " m.svgFrameFit(760, 400, 0, 1.5), m.svgFrameFit(0, 0, 800, 1.5)]);")
    assert got == [{"scale": 1, "wide": False},        # 칸 안 — 키우지 않는다
                   {"scale": 0.8, "wide": False},      # 조금 넘침 — 칸에 맞춰 줄인다
                   {"scale": 1, "wide": True},         # 1.9배 — 줄이면 글자가 뭉개진다, 가로 스크롤
                   {"scale": 1, "wide": False},        # 칸 폭을 아직 모름
                   {"scale": 1, "wide": False}], got   # 크기를 모름


def test_확대_화면_맞춤은_무대_안으로_줄이기만_한다():
    got = _run("out([m.svgFrameStageScale(1520, 800, 1200, 700), m.svgFrameStageScale(400, 300, 1200, 700), m.svgFrameStageScale(400, 300, 0, 0)]);")
    assert got == [0.7894736842105263, 1, 1], got


def _iframes(src: str) -> list[str]:
    return re.findall(r"<iframe\b[^>]*?/>", src, flags=re.S)


def test_그림_칸과_확대_화면의_svg_iframe_은_빈_sandbox_다():
    """스크립트(allow-scripts)도 같은 출처(allow-same-origin)도 열지 않는다 — 호버는 SVG 안의 CSS 라 필요 없다. 같은 출처를 열면 SVG 가 포털 화면을 만질 수 있다."""
    fig = (_SRC / "components/chat/renderers/Figure.tsx").read_text(encoding="utf-8")
    lb = (_SRC / "components/chat/renderers/Lightbox.tsx").read_text(encoding="utf-8")
    svg_frames = [f for f in _iframes(fig) + _iframes(lb) if "md-svgframe" in f or "lb-svgframe" in f]
    assert len(svg_frames) == 2, svg_frames
    for f in svg_frames:
        assert 'sandbox=""' in f and "allow-" not in f, f
        assert 'referrerPolicy="no-referrer"' in f, f
    # 그림 칸은 같은 출처 SVG 에서만 iframe — 판정 하나로 가른다.
    assert "isSvgFrameSrc(src) ? <SvgFrameFigure" in fig, "판정이 바뀌면 이 시험도 바꾼다"


def test_iframe_그림의_확대_아이콘은_눌린다():
    """iframe 안의 누름은 바깥으로 오지 않는다 — 확대 아이콘(평소 pointer-events: none)을 iframe 그림에서만 눌리게 한다."""
    css = (_SRC / "styles/chat.css").read_text(encoding="utf-8")
    rule = re.search(r"\.md-figure-frame\.is-frame \.md-figure-zoom \{([^}]*)\}", css)
    assert rule and "pointer-events: auto" in rule.group(1), rule
    assert re.search(r"\.md-figure-zoom \{[^}]*pointer-events: none", css), "그림(<img>)의 아이콘은 그대로 — 껍데기 전체가 눌린다"
