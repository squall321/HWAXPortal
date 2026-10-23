# 이 대화에서 분석 — AI 데이터 허브 변환 결과를 .hwax.md 로 옮겨 돌려주고, inbox 사본은 남기지 않는다(docs/chat-ppt PP-D17)
"""왜 — PPT · Word · PDF · Excel 을 올리면 'Report Archive 로 · AI 데이터 허브로' 둘뿐이라, 평문 문서를 이 챗에서 읽고 묻는 길이 없었다.
셋째 목적지 chat 은 허브 변환기를 그 사람 명의로 빌려 글 · 목록 · 표 · 차트 데이터 · 발표자 노트를 손 추출과 같은 꼴(.hwax.md)로 옮긴다.
어디에도 저장하지 않는다 — 변환기가 inbox 하위만 읽어 잠시 두고, 변환이 끝나면(실패해도) 지운다.
"""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import routes as R
from app.agent import upload as U
from app.auth.provider import Principal
from app.config import Settings

# AI 데이터 허브 변환기(convert_file)가 실제로 낸 record 의 칸 — AIDH venv 로 만든 PPTX 를 읽기 전용으로 변환해 뽑았다(제목 · 글머리 둘 ·
# 발표자 노트 / 표 + 차트(데이터 표) / 그림 한 장, 세 슬라이드)
AIDH_PPTX_RECORD = {'meta': {'title': '설계검토', 'source_format': 'pptx', 'source_file': '설계검토.pptx', 'doc_type': 'slide'},
                    'sections': [{'id': '1',
                                  'level': 1,
                                  'title': '낙하 시험 요약',
                                  'blocks': [{'type': 'list_item', 'text': '높이 1.5 m 에서 45° 낙하', 'marker': '•'},
                                             {'type': 'list_item', 'text': '최대 응력 432 MPa (힌지)', 'marker': '  •'},
                                             {'type': 'paragraph', 'text': '[Speaker Notes]'},
                                             {'type': 'paragraph', 'text': '힌지 보강안 B 를 다음 회의에서 결정'}],
                                  'figure_refs': [],
                                  'table_refs': [],
                                  'children': []},
                                 {'id': '2',
                                  'level': 1,
                                  'title': '조건별 결과',
                                  'blocks': [{'type': 'table', 'ref': 'DOC-TBD-TBD-2026-0000000001-T001'},
                                             {'type': 'figure', 'ref': 'DOC-TBD-TBD-2026-0000000001-F001'},
                                             {'type': 'table', 'ref': 'DOC-TBD-TBD-2026-0000000001-T002'}],
                                  'figure_refs': ['DOC-TBD-TBD-2026-0000000001-F001'],
                                  'table_refs': ['DOC-TBD-TBD-2026-0000000001-T001', 'DOC-TBD-TBD-2026-0000000001-T002'],
                                  'children': []},
                                 {'id': '3',
                                  'level': 1,
                                  'title': '응력 지도',
                                  'blocks': [{'type': 'figure', 'ref': 'DOC-TBD-TBD-2026-0000000001-F002'}],
                                  'figure_refs': ['DOC-TBD-TBD-2026-0000000001-F002'],
                                  'table_refs': [],
                                  'children': []}],
                    'tables': [{'id': 'DOC-TBD-TBD-2026-0000000001-T001',
                                'number': 1,
                                'caption': 'Table 1: 슬라이드 2 표',
                                'section_ref': '2',
                                'headers': ['조건', '응력(MPa)', '판정'],
                                'rows': [['A', 432, '불합격'], ['B', 310, '합격']]},
                               {'id': 'DOC-TBD-TBD-2026-0000000001-T002',
                                'number': 2,
                                'caption': 'Table 2: 차트 데이터 — 제목없음',
                                'section_ref': '2',
                                'headers': ['category', '응력'],
                                'rows': [['A', 432.0], ['B', 310.0]]}],
                    'figures': [{'id': 'DOC-TBD-TBD-2026-0000000001-F001', 'number': 1, 'caption': 'Figure 1: 차트', 'section_ref': '2'},
                                {'id': 'DOC-TBD-TBD-2026-0000000001-F002',
                                 'number': 2,
                                 'caption': 'Figure 2: 슬라이드 3 이미지',
                                 'section_ref': '3',
                                 'image_path': 'DOC-TBD-TBD-2026-0000000001/F002.png'}]}


def test_변환_결과는_손_추출과_같은_꼴의_문서가_된다():
    md = U.record_markdown(AIDH_PPTX_RECORD, "설계검토.pptx")
    head = md.split("\n---\n", 1)[0].splitlines()
    assert head[:5] == ["---", "schema: hwax-doc/1", "source: 설계검토.pptx", "kind: ppt", "units: 3"], head
    assert head[6] == "extracted_by: AI 데이터 허브 변환기(서버 — 저장하지 않음)"
    assert "\n# 설계검토\n\n## [s.1] 낙하 시험 요약\n\n• 높이 1.5 m 에서 45° 낙하\n  • 최대 응력 432 MPa (힌지)\n\n" in md
    assert "> 발표자 노트: 힌지 보강안 B 를 다음 회의에서 결정" in md, "발표자 노트는 노트로 — 본문과 갈린다"
    assert "[표 1] 슬라이드 2 표\n| 조건 | 응력(MPa) | 판정 |\n| --- | --- | --- |\n| A | 432 | 불합격 |\n| B | 310 | 합격 |" in md
    assert "[표 2] 차트 데이터 — 제목없음\n| category | 응력 |" in md, "차트는 데이터 표로"
    assert "[그림 2] 슬라이드 3 이미지 — 그림 내용은 글로 옮기지 않았다" in md, "그림은 자리만 — 읽지 않았다고 적는다"
    assert "Table 1:" not in md and "Figure 1:" not in md, "변환기의 영어 머리는 뗀다"


def test_머리말의_글자_수는_본문_길이다():
    md = U.record_markdown(AIDH_PPTX_RECORD, "설계검토.pptx")
    chars = int([line for line in md.splitlines() if line.startswith("chars: ")][0].split(": ")[1])
    body = md.split("\n---\n", 1)[1].split("\n", 3)[3]          # 머리말 뒤 '\n# 제목\n\n' 다음부터
    assert chars == len(body)


def test_슬라이드가_아닌_문서는_쪽_표지도_장_수도_없다():
    rec = {"meta": {"title": "보고서", "source_format": "docx"},
           "sections": [{"id": "1", "level": 1, "title": "개요", "blocks": [{"type": "paragraph", "text": "본문"}],
                         "children": [{"id": "1.1", "level": 2, "title": "세부", "blocks": [{"type": "paragraph", "text": "더"}]}]}]}
    md = U.record_markdown(rec, "보고서.docx")
    assert "kind: word" in md and "units:" not in md and "[s." not in md
    assert "## 개요\n\n본문\n\n### 세부\n\n더" in md, "하위 절은 한 단계 아래 머리로"


def test_모양이_틀린_칸은_건너뛴다():
    rec = {"sections": [{"title": "s", "blocks": ["글", None, {"type": "table", "ref": "없음"}, {"type": "figure", "ref": "없음"},
                                                 {"type": "paragraph", "text": "  "}, {"type": "list_item", "text": "항목"}]},
                        "절 아님"], "tables": ["표 아님"], "figures": [None]}
    md = U.record_markdown(rec, "a.pptx")
    assert "## [s.1] s\n\n• 항목" in md and "[표" not in md and "[그림" not in md


def test_표_칸의_세로줄과_줄바꿈은_표를_깨지_않게():
    rec = {"sections": [{"title": "t", "blocks": [{"type": "table", "ref": "T"}]}],
           "tables": [{"id": "T", "number": 1, "caption": "", "headers": ["a|b"], "rows": [["x\ny", None, 3]]}]}
    md = U.record_markdown(rec, "a.pptx")
    assert "| a\\|b |  |  |\n| --- | --- | --- |\n| x y |  | 3 |" in md, md


# ── 보내기 갈래 chat ──────────────────────────────────────────────────────────────────────────
class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)


async def _chat(monkeypatch, tmp_path, mcp):
    inbox = tmp_path / "inbox"
    monkeypatch.setenv("AIDH_CONVERT_INBOX", str(inbox))
    f = tmp_path / "설계검토.pptx"
    f.write_bytes(b"PK\x03\x04 fake")
    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R._upload, "mcp_call", mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    audit = _Audit()
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(agent_audit=audit, keystore=None)))
    body = R.UploadDispatchReq(staging_id="s1", filename="설계검토.pptx", destination="chat")
    principal = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수")
    out = await R._dispatch_inner(req, body, principal, Settings(_env_file=None))
    return out, inbox, audit


@pytest.mark.anyio
async def test_이_대화에서_분석은_글을_돌려주고_inbox_에_아무것도_남기지_않는다(monkeypatch, tmp_path):
    seen = {}

    async def mcp(url, pat, tool, args, timeout=90.0):
        seen.update(tool=tool, args=args, there=(Path(os.environ["AIDH_CONVERT_INBOX"]) / args["file"]).exists())
        return {"status": "converted", "format": "pptx", "record": AIDH_PPTX_RECORD}

    out, inbox, audit = await _chat(monkeypatch, tmp_path, mcp)
    assert seen["tool"] == "convert_file" and seen["there"], "변환기는 inbox 하위만 읽는다 — 부를 때는 거기 있다"
    assert seen["args"]["file"].startswith("kim-chat-") and seen["args"]["file"].endswith("-설계검토.pptx"), \
        "AI 데이터 허브로 보낸 같은 이름의 파일과 겹치지 않게 이름을 가른다"
    assert list(inbox.iterdir()) == [], "어디에도 저장하지 않는다 — inbox 사본은 변환 뒤 지운다"
    md = U.record_markdown(AIDH_PPTX_RECORD, "설계검토.pptx")
    assert out == {"stage": "done", "destination": "chat", "doc": {"name": "설계검토.hwax.md", "text": md, "chars": len(md)}}
    (row,) = audit.rows
    assert row["event"] == "upload_dispatch" and row["meta"]["destination"] == "chat" and "text" not in row["meta"], \
        "감사에 본문을 남기지 않는다"


@pytest.mark.anyio
async def test_변환이_실패해도_inbox_사본은_지운다(monkeypatch, tmp_path):
    async def mcp(url, pat, tool, args, timeout=90.0):
        raise RuntimeError("허브가 죽었다")

    with pytest.raises(RuntimeError):
        await _chat(monkeypatch, tmp_path, mcp)
    assert list((tmp_path / "inbox").iterdir()) == []


@pytest.mark.anyio
async def test_읽을_절이_없으면_실패로_알린다(monkeypatch, tmp_path):
    async def mcp(url, pat, tool, args, timeout=90.0):
        return {"status": "converted", "record": {"sections": []}}

    out, _inbox, _a = await _chat(monkeypatch, tmp_path, mcp)
    assert out["stage"] == "failed" and "읽을 내용을 찾지 못했습니다" in out["error"]


def test_문서를_올리면_이_대화에서_분석이_맨_앞이고_허브를_쓸_수_있는_사람에게만_뜬다():
    s = Settings(_env_file=None, upload_allowed_groups="nobody")
    full = ["feat:upload", "plat:aidatahub", "plat:reportarchive"]
    assert [d["id"] for d in U.allowed_destinations(s, full, "pptx")] == ["chat", "reportarchive", "aidatahub"]
    assert [d["id"] for d in U.allowed_destinations(s, full, "docx")] == ["chat", "aidatahub"]
    assert "chat" not in [d["id"] for d in U.allowed_destinations(s, ["feat:upload", "plat:reportarchive"], "pptx")], \
        "허브 변환기를 그 사람 명의로 빌린다 — 허브를 못 쓰면 뜨지 않는다"
    assert "chat" not in [d["id"] for d in U.allowed_destinations(s, full, "md")], "글 파일은 브라우저가 직접 읽는다"
