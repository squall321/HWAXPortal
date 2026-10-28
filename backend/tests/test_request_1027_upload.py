# 10-27 수정 요청 — 챗 업로드 · RA 보내기(HP-02 크기 한도 · 거절 사유 · HP-03 실패 감사 · HP-32 마지막 도구 지도)
"""왜 —
HP-02  'Report Archive 로' 가 크기 한도를 미리 알리지 않고 RA 가 밝힌 사유를 버렸다(10-23 116쪽 · 45 MB 가 업로드를 다 한 뒤 400 '파일이 너무 큽니다.').
HP-03  RA 400 처럼 {"stage": "failed"} 로 돌려준 실패는 200 으로 끝나 감사에 upload_stage 두 줄만 남았다.
HP-32  게이트웨이 재기동 중 도구 지도를 못 읽으면 None(숨기지 않음)이 되어 지금 없는 '정밀 변환' 이 다시 보였다.
RA 는 MockTransport 로만 부른다(test_ra_sso 와 같은 장치).
"""
import logging
from types import SimpleNamespace

import httpx
import pytest

from app.auth import ra_sso
from app.auth.errors import AuthError
from app.auth.provider import Principal
from tests.test_ra_sso import PPTX_OK, _Audit, _mock_ra, _ra_handler, _settings, _Store


@pytest.fixture(autouse=True)
def _fresh_cache():
    ra_sso._CACHE.clear()
    yield
    ra_sso._CACHE.clear()


def _box(monkeypatch, tmp_path, size: int, slides: int = 3):
    """스테이징 파일 하나(진짜 zip — 쪽 수를 셀 수 있게) · 권한 · 챗 PAT · 게이트웨이 호출을 가짜로 둔 판."""
    import zipfile
    from app.agent import routes as R
    f = tmp_path / "deck.pptx"
    with zipfile.ZipFile(f, "w") as z:
        for i in range(1, slides + 1):
            z.writestr(f"ppt/slides/slide{i}.xml", "<p/>")
        z.writestr("ppt/media/pad.bin", b"\0" * max(0, size))
    calls = []

    async def _mcp(url, pat, tool, args, timeout=90.0):
        calls.append(tool)
        return {"report_id": 7, "title": "t", "url": "/w/x/reports/7", "warnings": []}
    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    audit = _Audit()
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(user_store=_Store(None), agent_audit=audit, keystore=None)))
    body = R.UploadDispatchReq(staging_id="s1", filename="deck.pptx", destination="reportarchive")
    principal = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수")
    return R, req, body, principal, audit, calls, f


def test_HP02_목적지_목록이_RA_크기_한도를_싣고_0_이면_끈다():
    from app.agent import upload as U
    s = _settings(upload_allowed_groups="g")
    by = {d["id"]: d for d in U.allowed_destinations(s, ["g"], "pptx")}
    assert by["reportarchive"]["max_bytes"] == 25 * 1024 * 1024
    assert all("max_bytes" not in d for k, d in by.items() if k != "reportarchive"), "한도 없는 목적지에는 칸이 없다"
    off = {d["id"]: d for d in U.allowed_destinations(_settings(upload_allowed_groups="g", ra_import_max_mb=0), ["g"], "pptx")}
    assert "max_bytes" not in off["reportarchive"]


@pytest.mark.anyio
async def test_HP02_한도를_넘으면_RA_를_부르지_않고_413_과_안내를_돌려준다(monkeypatch, tmp_path):
    seen = _mock_ra(monkeypatch, _ra_handler())
    R, req, body, principal, audit, calls, _f = _box(monkeypatch, tmp_path, size=1_600_000)
    with pytest.raises(AuthError) as ei:
        await R._dispatch_audited(req, body, principal, _settings(ra_import_max_mb=1))
    assert ei.value.status_code == 413 and "한도 1 MB" in ei.value.message and "AI 데이터 허브" in ei.value.message
    assert seen == [] and calls == [], "RA(위임 발급 포함)를 부르지 않는다"
    assert audit.rows[-1]["status"] == "failed" and "413" not in str(audit.rows[-1]["meta"].get("ra_status", ""))


@pytest.mark.anyio
@pytest.mark.parametrize("ra_body, want_code, want_msg", [
    ({"detail": "파일이 너무 큽니다."}, None, "파일이 너무 큽니다."),
    ({"detail": {"code": "TOO_MANY_PAGES", "message": "쪽 수가 200 을 넘습니다"}}, "TOO_MANY_PAGES", "쪽 수가 200 을 넘습니다"),
])
async def test_HP02_HP03_RA_가_거절한_사유를_보이고_실패를_감사와_로그에_본문_없이_남긴다(monkeypatch, tmp_path, caplog, ra_body, want_code,
                                                                       want_msg):
    _mock_ra(monkeypatch, _ra_handler(pptx=lambda r: httpx.Response(400, json=ra_body)))
    R, req, body, principal, audit, calls, f = _box(monkeypatch, tmp_path, size=2048, slides=4)
    with caplog.at_level(logging.WARNING, logger=R.logger.name):
        out = await R._dispatch_audited(req, body, principal, _settings())
    assert out["stage"] == "failed" and want_msg in out["error"] and "HTTP 400" in out["error"]
    assert out["hint"].startswith("사진을 압축하거나 나눠 보내거나"), "크기 · 쪽 수 사유에는 다른 길을 함께 안내한다"
    if want_code:
        assert want_code in out["error"]
    row = audit.rows[-1]
    assert (row["event"], row["status"]) == ("upload_dispatch", "failed")
    m = row["meta"]
    assert (m["ra_status"], m.get("ra_code"), m["slides"], m["size"]) == (400, want_code, 4, f.stat().st_size)
    assert want_msg not in str({k: v for k, v in m.items() if k != "error"}), "RA 본문(detail)은 감사 칸에 싣지 않는다"
    line = [r.getMessage() for r in caplog.records if "upload dispatch failed" in r.getMessage()]
    assert line and "ra_status=400" in line[0] and "slides=4" in line[0] and "deck.pptx" not in line[0]
    assert calls == [], "보고서를 만들지 않았다"


@pytest.mark.anyio
async def test_HP03_성공은_종전대로_한_줄이고_실패_줄이_더해지지_않는다(monkeypatch, tmp_path):
    _mock_ra(monkeypatch, _ra_handler(pptx=lambda r: httpx.Response(201, json=PPTX_OK)))
    R, req, body, principal, audit, calls, _f = _box(monkeypatch, tmp_path, size=10)
    out = await R._dispatch_audited(req, body, principal, _settings())
    assert out["stage"] == "done" and [r.get("status", "ok") for r in audit.rows] == ["ok"]


@pytest.mark.anyio
async def test_HP32_도구_지도를_못_읽으면_마지막으로_읽은_지도를_쓴다(monkeypatch):
    from app.agent import upload as U
    state = {"up": True}
    real = httpx.AsyncClient

    def handler(req):
        if not state["up"]:
            raise httpx.ConnectError("게이트웨이 재기동 중")
        return httpx.Response(200, json={"map": {"list_parts": "heax-step_forge"}})
    monkeypatch.setattr(U._httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(U, "_GW_TOOLS", {"at": float("-inf"), "names": None})
    s = _settings(mcp_gateway_url="http://gw.test")
    assert await U.gateway_tool_names(s) == frozenset({"list_parts"})
    state["up"] = False
    U._GW_TOOLS["at"] = float("-inf")
    assert await U.gateway_tool_names(s) == frozenset({"list_parts"}), "None(숨기지 않음)으로 돌아가지 않는다"
    monkeypatch.setattr(U, "_GW_TOOLS", {"at": float("-inf"), "names": None})
    assert await U.gateway_tool_names(s) is None, "한 번도 못 읽었으면 종전대로 모른다"


# ── HP-29 · HP-30 — AI 데이터 허브 inbox 사본 · 칩 제목 ─────────────────────────────────────────────────────────────
def _aidh_box(monkeypatch, tmp_path, destination: str, record_title=None):
    from app.agent import routes as R
    inbox = tmp_path / "inbox"
    monkeypatch.setenv("AIDH_CONVERT_INBOX", str(inbox))
    f = tmp_path / "설계검토.pptx"
    f.write_bytes(b"PK\x03\x04 pptx")
    calls = []

    async def _mcp(url, pat, tool, args, timeout=90.0):
        calls.append((tool, dict(args)))
        assert (inbox / args["file"]).exists(), "변환기가 읽을 때 inbox 에 있어야 한다"
        title = Path(args["file"]).stem if record_title == "inbox" else record_title
        return {"status": "converted", "record": {"meta": {"title": title, "source_format": "pptx"},
                                                    "sections": [{"title": "s1", "blocks": [{"type": "paragraph", "text": "낙하 1.5 m"}]}]}}
    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R._upload, "mcp_call", _mcp)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(user_store=_Store(None), agent_audit=_Audit(), keystore=None)))
    body = R.UploadDispatchReq(staging_id="s1", filename=f.name, destination=destination)
    principal = Principal(subject="koo.park@corp.com", email="koo.park@corp.com", display_name="박구")
    settings = _settings(upload_staging_dir=str(tmp_path / "staging"))
    return R, req, body, principal, settings, inbox, calls


from pathlib import Path  # noqa: E402


@pytest.mark.anyio
async def test_HP29_AIDH_사본은_바로_지우지_않고_장부에_적어_기한_뒤에_포털이_넣은_것만_지운다(monkeypatch, tmp_path):
    import os
    import time as _t
    from app.agent import upload as U
    R, req, body, principal, settings, inbox, calls = _aidh_box(monkeypatch, tmp_path, "aidatahub", record_title="설계검토")
    out = await R._dispatch_inner(req, body, principal, settings)
    name = out["inbox_name"]
    assert (inbox / name).exists(), "모델이 그 이름으로 convert_file 을 다시 부를 수 있다 — 바로 지우지 않는다"
    foreign = inbox / "someone-else.pptx"
    foreign.write_bytes(b"x")
    old = _t.time() - 25 * 3600
    os.utime(foreign, (old, old))
    assert U.sweep_aidh_inbox(settings) == 0, "기한 전에는 지우지 않는다"
    import json
    led = U._aidh_ledger(settings)
    data = json.loads(led.read_text(encoding="utf-8"))
    data[name] = old
    led.write_text(json.dumps(data), encoding="utf-8")
    assert U.sweep_aidh_inbox(settings) == 1
    assert not (inbox / name).exists() and foreign.exists(), "장부에 없는 것(남이 둔 파일)은 건드리지 않는다"
    assert json.loads(led.read_text(encoding="utf-8")) == {}


@pytest.mark.anyio
@pytest.mark.parametrize("title, want", [("inbox", "# 설계검토"), ("설계 검토 회의", "# 설계 검토 회의")], ids=["임시이름", "진짜제목"])
async def test_HP30_이_대화에서_분석은_inbox_임시_이름을_칩_제목으로_쓰지_않는다(monkeypatch, tmp_path, title, want):
    R, req, body, principal, settings, inbox, calls = _aidh_box(monkeypatch, tmp_path, "chat", record_title=title)
    out = await R._dispatch_inner(req, body, principal, settings)
    text = out["doc"]["text"]
    assert want in text.splitlines() and "koo.park" not in text, text[:300]
    assert list(inbox.iterdir()) == [], "이 대화에서 분석은 종전대로 바로 지운다"


# ── HP-14 · HP-31 — 화면 순수 함수(node 로 돌린다) ────────────────────────────────────────────────────────────────
def _fe_ok():
    import shutil
    from tests.test_front_window_payload import _FE
    return shutil.which("node") and (_FE / "node_modules" / "typescript").exists()


@pytest.mark.skipif(not _fe_ok(), reason="node 또는 frontend node_modules(typescript) 가 없다")
def test_HP14_사내_DRM_머리를_암호로_보고_HP31_서버_변환은_aidh_convert_로_적는다():
    from tests.test_front_window_payload import _node
    script = (
        "const d = require('./components/chat/docAttach.js');"
        "(async () => {"
        "  const mk = (bytes) => new File([new Uint8Array(bytes)], 'x.pptx');"
        "  const drm = [0x3c,0x23,0x23,0x20,0x4e,0x41,0x53,0x43,0x41,0x20,0x44,0x52,0x4d];"
        "  const r = { drm: await d.isEncryptedOffice(mk(drm)), pk: await d.isEncryptedOffice(mk([0x50,0x4b,3,4,0,0,0,0])),"
        "              ole: await d.isEncryptedOffice(mk([0xd0,0xcf,0x11,0xe0,0,0,0,0])),"
        "              near: await d.isEncryptedOffice(mk([0x3c,0x23,0x23,0x20,0x4e,0x41,0x53,0x43,0x42])) };"
        "  const ev = d.docsAsEvidence(input.map((m) => ({ name: 'a.md', text: 't', chars: 1, truncated: false, meta: m })));"
        "  out({ ...r, tools: ev.map((e) => e.tool) });"
        "})();")
    got = _node(["components/chat/docAttach.ts"], script,
                [{"extractedBy": "AI 데이터 허브 변환기(서버 — 저장하지 않음)"}, {"extractedBy": "office-com(PowerPoint)"}, {}])
    assert (got["drm"], got["pk"], got["ole"], got["near"]) == (True, False, True, None), got
    assert got["tools"] == ["aidh-convert", "office-com-extract", "text-attach"], got
