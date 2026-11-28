# 업로드 수신 응답의 문서 표지 — 잠김(DRM · OLE, WD-11)과 차트 · 노트 · 그림 수(IR-06)를 화면이 고르기 전에 받는가(docs/request-1125)
"""진짜 앱(TestClient)으로 /agent/upload 에 올린다 — 하네스는 test_admin_ledger_only 의 box(임시 원장 · 관리자 PAT)다."""
import io
import zipfile

from tests.test_admin_ledger_only import _old_pat, box  # noqa: F401 — box 는 픽스처


def _pptx() -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n in ("ppt/slides/slide1.xml", "ppt/charts/chart1.xml", "ppt/notesSlides/notesSlide1.xml", "ppt/media/image1.png"):
            z.writestr(n, "x")
    return b.getvalue()


def test_발표자료면_차트_노트_그림_수를_싣고_잠겼으면_locked(box):
    c, s = box
    c.cookies.clear()
    pat = {"Authorization": "Bearer " + _old_pat(s, "boss@corp.com", [])}
    r = c.post("/agent/upload", files={"file": ("a.pptx", _pptx(), "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
               headers=pat)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["doc_features"] == {"charts": 1, "notes": 1, "pictures": 1} and "locked" not in j and "path" not in j
    drm = bytes((0x3C, 0x23, 0x23, 0x20, 0x4E, 0x41, 0x53, 0x43, 0x41)) + b" body"
    j = c.post("/agent/upload", files={"file": ("b.pptx", drm, "application/octet-stream")}, headers=pat).json()
    assert j["locked"] == "drm" and "doc_features" not in j
    j = c.post("/agent/upload", files={"file": ("t.csv", b"a,b\n1,2\n", "text/csv")}, headers=pat).json()
    assert "locked" not in j and "doc_features" not in j, "문서가 아니면 칸이 없다 — 응답이 종전 그대로"
