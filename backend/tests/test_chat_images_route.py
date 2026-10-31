# 챗에 올린 그림 — 포털이 받고(꼴 · 크기 · 장수) 에이전트 서버로 넘기고, 이력 항목의 그림 주소는 에이전트 서버 아티팩트 꼴만 받는지
"""왜 — 사용자 지시(10-18) "이전 대화나 심의에 넘기는 게 챗 이력뿐 아니라 올린 이미지나 디지털워커가 조회한 데이터의 이미지들도 들어가야
한다 — 자료를 기반으로 판단해야 한다"(docs/chat-depth-context T5).

  · 이 발화의 그림 — [{name, mime, data(base64)}], 장수 · 크기는 에이전트 서버 vision.MAX_IMAGES · MAX_BYTES 와 같은 수(넘으면 422).
  · 이력 항목의 그림 — 에이전트 서버가 돌려준 /agent/artifacts/<해시>.<확장자> 만. 다른 주소(첨부 · 바깥 · 경로 거슬러 오르기)는 막는다.
  · 심의 전 도우미(전문가 고르기 · 되묻기 · 화두)에는 근거와 같이 그림도 넘기지 않는다.
  · 서버 대화 사본 — 돌려받은 그림 주소를 답의 meta(user_images)에 남긴다(다른 기기에서 열어도 이력에 그림이 실린다).
"""
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent import routes as R

SRC = Path(R.__file__).read_text(encoding="utf-8")
_ROOT = Path(__file__).resolve().parents[2]
_VISION = _ROOT.parent / "HWAXAgentServer" / "vision.py"
_FRONT = _ROOT / "frontend" / "src" / "components" / "chat" / "imageAttach.ts"
PNG_B64 = "iVBORw0KGgo="


def _req(**kw):
    return R.ChatRequest(message="이 그림 봐", **kw)


def test_올린_그림을_받고_에이전트_서버로_넘긴다():
    req = _req(images=[{"name": "s.png", "mime": "image/png", "data": PNG_B64}])
    assert req.images[0].mime == "image/png"
    assert 'payload["images"] = [i.model_dump() for i in body.images]' in SRC


def test_꼴_장수_크기가_틀린_그림은_막는다():
    with pytest.raises(ValidationError):
        _req(images=[{"name": "a.svg", "mime": "image/svg+xml", "data": PNG_B64}])
    with pytest.raises(ValidationError):
        _req(images=[{"mime": "image/png", "data": PNG_B64}] * (R._IMAGES_MAX + 1))
    with pytest.raises(ValidationError):
        _req(images=[{"mime": "image/png", "data": "A" * (R._IMAGE_B64_MAX + 1)}])
    assert R._IMAGE_B64_MAX >= (R._IMAGE_BYTES_MAX * 4 + 2) // 3, "8MiB 그림의 base64 가 들어가야 한다"


def test_이력의_그림_주소는_에이전트_서버_아티팩트_꼴만():
    ok = _req(history=[{"role": "user", "content": "앞 그림", "images": ["/agent/artifacts/0a1b2c3d4e5f60718293.png"]}])
    assert ok.history[0].to_agent() == {"role": "user", "content": "앞 그림", "images": ["/agent/artifacts/0a1b2c3d4e5f60718293.png"]}
    assert _req(history=[{"role": "user", "content": "q"}]).history[0].to_agent() == {"role": "user", "content": "q"}, \
        "그림 없는 항목은 종전 모양 그대로"
    for bad in ("/ai-data-hub/attachments/r1/A001.png", "http://evil.example/x.png", "/agent/artifacts/../x.png",
                "/agent/artifacts/x.svg", "/agent/artifacts/x.png?y=1"):
        with pytest.raises(ValidationError):
            _req(history=[{"role": "user", "content": "q", "images": [bad]}])


def test_심의_전_도우미에는_그림도_넘기지_않는다():
    assert SRC.count('[m.model_dump(exclude={"evidence", "images"}) for m in body.history]') == 3


def test_서버_대화_사본은_돌려받은_그림_주소를_답의_meta_에_남긴다():
    assert 'elif evt == "user_images" and isinstance(data.get("urls"), list):' in SRC
    # 답 meta 묶음(_am) 안에 있으면 된다 — 뒤에 칸이 더 붙어도(패널 포인터 panels, docs/request-1027 HP-42) 그림 주소는 그대로 남는다
    start = SRC.index("_am = {k: v for k, v in (")
    assert '("user_images", user_images)' in SRC[start:SRC.index(") if v}", start)]
    assert R._ARTIFACT_IMAGE_RE.fullmatch("/agent/artifacts/abc.webp") and not R._ARTIFACT_IMAGE_RE.fullmatch("/x/abc.webp")


def test_장수_크기는_에이전트_서버_화면과_같은_수다():
    """세 곳이 같은 수여야 한다 — 화면이 더 받으면 포털 422, 포털이 더 받으면 에이전트 서버가 건너뛴다(알리지만 사람은 왜인지 모른다)."""
    if not _VISION.exists():
        pytest.skip("형제 리포 HWAXAgentServer 가 없다")
    v = _VISION.read_text(encoding="utf-8")
    m_n = re.search(r'MAX_IMAGES = int\(os\.environ\.get\("VISION_MAX_IMAGES", "(\d+)"\)\)', v)
    m_b = re.search(r'MAX_BYTES = int\(os\.environ\.get\("VISION_MAX_BYTES", str\((\d+) \* 1024 \* 1024\)\)\)', v)
    assert m_n and m_b, "vision.py 의 상한 줄 꼴이 바뀌었다 — 이 시험도 고쳐라"
    assert R._IMAGES_MAX == int(m_n.group(1)) and R._IMAGE_BYTES_MAX == int(m_b.group(1)) * 1024 * 1024
    f = _FRONT.read_text(encoding="utf-8")
    assert re.search(rf"^export const IMAGES_MAX = {R._IMAGES_MAX};", f, re.M)
    assert re.search(r"^export const IMAGE_BYTES_MAX = (\d+) \* 1024 \* 1024;", f, re.M).group(1) == m_b.group(1)
