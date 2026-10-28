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


# ── HP-15 SimFlow 업로드 목적지 ─────────────────────────────────────────────────────────────────────────────────
# 게이트웨이 REST 다리(/api/simflow/api/v1/mcp-uploads)는 MockTransport 로만 부른다. 사이트 PAT 은 진짜 RSA 키로 찍고 풀어 본다.
_SF_URL = "http://gw.test/api/simflow/api/v1/mcp-uploads"
_KEYS: dict = {}


def _keystore():
    if not _KEYS:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _KEYS["ks"] = SimpleNamespace(private_pem=k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                                  serialization.NoEncryption()), active_kid="t1")
        _KEYS["pub"] = k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return _KEYS["ks"], _KEYS["pub"]


def _sf_box(monkeypatch, tmp_path, size: int = 64, name: str = "part.x_t"):
    from app.agent import routes as R
    f = tmp_path / name
    f.write_bytes(b"\x01" * size)
    monkeypatch.setattr(R._upload, "require_destination_group", lambda *a, **k: None)
    monkeypatch.setattr(R._upload, "staged_path", lambda *a, **k: f)
    monkeypatch.setattr(R, "_chat_user_pat", lambda *a, **k: "chat-pat")
    sleeps: list[float] = []

    async def _no_sleep(s):
        sleeps.append(s)
    monkeypatch.setattr(R.asyncio, "sleep", _no_sleep)
    audit = _Audit()
    ks, _pub = _keystore()
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(agent_audit=audit, keystore=ks)))
    body = R.UploadDispatchReq(staging_id="s1", filename=name, destination="simflow")
    principal = Principal(subject="kim@corp.com", email="kim@corp.com", display_name="김철수")
    return R, req, body, principal, audit, sleeps


def _sf_settings(**kw):
    return _settings(mcp_gateway_url="http://gw.test", **kw)


def test_HP15_SimFlow_목적지는_설정_확장자_권한_게이트웨이_도구가_있어야_보인다():
    from app.agent import upload as U
    s = _sf_settings(upload_allowed_groups="g")
    ids = lambda st, ext, tools: [d["id"] for d in U.allowed_destinations(st, ["g"], ext, tools)]  # noqa: E731
    assert ids(s, "x_t", frozenset({"run_workflow"})) == ["simflow"]
    assert ids(s, "x_t", frozenset({"simflow_run_workflow"})) == ["simflow"], "다른 앱과 겹쳐 접두로 나와도 SimFlow 가 붙어 있다"
    assert ids(s, "x_t", frozenset({"create_report_draft"})) == [], "SimFlow 도구가 없는 게이트웨이(dev)에서는 고를 수 없다"
    assert ids(s, "x_t", None) == ["simflow"], "도구 지도를 모르면 숨기지 않는다(종전 규칙)"
    assert ids(_sf_settings(upload_allowed_groups="g", simflow_upload_exts=".X_T, x_b"), "x_b", None) == ["simflow"], "설정 확장자"
    assert ids(_sf_settings(upload_allowed_groups="g", simflow_upload_exts="x_b"), "x_t", None) == []
    (d,) = U.allowed_destinations(s, ["g"], "x_t", None)
    assert d["max_bytes"] == 500 * 1024 * 1024 and d["label"] == "SimFlow — 워크플로우 입력 파일"
    assert "x_t" in U.upload_exts(s, ["g"], None) and "x_t" not in U.upload_exts(s, ["g"], frozenset({"x"}))
    assert U.upload_exts(s, [], None) == [], "보낼 곳이 없으면 빈 목록"
    assert not U._dest_ok(s, ["feat:upload"], "simflow") and U._dest_ok(s, ["feat:upload", "plat:simflow"], "simflow")


@pytest.mark.anyio
async def test_HP15_보내기는_다리로_사이트_PAT_와_함께_흘려_보내고_받은_id_를_돌려준다(monkeypatch, tmp_path):
    import jwt as _jwt
    seen = _mock_ra(monkeypatch, lambda r: httpx.Response(200, json={"id": "up-1", "status": "ready"}))
    R, req, body, principal, audit, _sl = _sf_box(monkeypatch, tmp_path)
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert out == {"stage": "done", "destination": "simflow", "upload_id": "up-1", "upload_status": "ready", "size": 64,
                   "result": {"id": "up-1", "status": "ready"}}
    (r,) = seen
    assert r.method == "POST" and str(r.url) == _SF_URL
    claims = _jwt.decode(r.headers["authorization"].removeprefix("Bearer "), _keystore()[1], algorithms=["RS256"], audience="simflow")
    assert claims["aud"] == ["simflow"] and claims["email"] == "kim@corp.com" and claims["scope"] == "api", \
        "청중은 SimFlow 하나 — 챗 PAT(게이트웨이 청중)은 다리가 거절한다"
    assert claims["exp"] - claims["iat"] <= 600 + 120 + 300, "짧다"
    raw = r.read()
    assert b'filename="part.x_t"' in raw and b"\x01" * 64 in raw, "원본 그대로(DRM 원본도 풀지 않고)"
    assert audit.rows[-1]["meta"] == {"destination": "simflow", "upload_id": "up-1", "status": "ready", "size": 64}


@pytest.mark.anyio
async def test_HP15_위층_401_로_캐시를_버렸으면_한_번_다시_보내고_게이트웨이_401_은_다시_보내지_않는다(monkeypatch, tmp_path):
    answers = [httpx.Response(401, headers={"X-Gateway-Token-Evicted": "1"}, json={"detail": "expired"}),
               httpx.Response(200, json={"data": {"upload_id": "up-2", "state": "ready"}})]
    seen = _mock_ra(monkeypatch, lambda r: answers.pop(0))
    R, req, body, principal, audit, _sl = _sf_box(monkeypatch, tmp_path)
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert out["stage"] == "done" and out["upload_id"] == "up-2" and len(seen) == 2, "감싼 꼴(data · upload_id · state)도 받는다"
    seen = _mock_ra(monkeypatch, lambda r: httpx.Response(401, json={"detail": "bad aud"}))
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert len(seen) == 1 and out["stage"] == "failed" and "다시 로그인" in out["error"] and out["sf_status"] == 401
    assert audit.rows[-1]["status"] == "failed" and audit.rows[-1]["meta"]["sf_status"] == 401
    seen = _mock_ra(monkeypatch, lambda r: httpx.Response(401, headers={"X-Gateway-Token-Evicted": "1"}))
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert len(seen) == 2 and "새로 받은 토큰도 거절" in out["error"], "두 번째도 위층 401 이면 다시 보내지 않고 알린다"


@pytest.mark.anyio
async def test_HP15_drm_pending_이면_ready_까지_보고_기다림이_끝나면_그대로_알린다(monkeypatch, tmp_path):
    states = ["drm_pending", "drm_pending", "ready"]

    def _h(r):
        if r.method == "POST":
            return httpx.Response(201, json={"id": "up-3", "status": "drm_pending"})
        assert str(r.url) == f"{_SF_URL}/up-3"
        return httpx.Response(200, json={"id": "up-3", "status": states.pop(0)})
    seen = _mock_ra(monkeypatch, _h)
    R, req, body, principal, _audit, sleeps = _sf_box(monkeypatch, tmp_path)
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert out["upload_status"] == "ready" and "note" not in out and [r.method for r in seen] == ["POST", "GET", "GET", "GET"]
    assert sleeps == [2, 2, 2]
    seen = _mock_ra(monkeypatch, lambda r: httpx.Response(200, json={"id": "up-4", "status": "drm_pending"}))
    out = await R._dispatch_audited(req, body, principal, _sf_settings(simflow_ready_wait_s=0))
    assert out["stage"] == "done" and out["upload_status"] == "drm_pending" and "run_workflow" in out["note"] and len(seen) == 1


@pytest.mark.anyio
async def test_HP15_한도를_넘으면_부르지_않고_거절_사유는_알아듣게(monkeypatch, tmp_path):
    seen = _mock_ra(monkeypatch, lambda r: httpx.Response(200, json={"id": "x", "status": "ready"}))
    R, req, body, principal, audit, _sl = _sf_box(monkeypatch, tmp_path, size=1_200_000)
    with pytest.raises(AuthError) as ei:
        await R._dispatch_audited(req, body, principal, _sf_settings(simflow_upload_max_mb=1))
    assert ei.value.status_code == 413 and "SimFlow 업로드 한도 1 MB" in ei.value.message and seen == []
    for code, want in ((413, "크기 한도"), (404, "재프로비저닝"), (403, "권한이 없습니다"), (500, "HTTP 500")):
        _mock_ra(monkeypatch, lambda r, c=code: httpx.Response(c, json={"detail": "사유 문구"}))
        out = await R._dispatch_audited(req, body, principal, _sf_settings())
        assert out["stage"] == "failed" and want in out["error"] and out["sf_status"] == code, (code, out)
        assert code in (404,) or "사유 문구" in out["error"], "상대가 밝힌 사유를 붙인다"
    for resp in (httpx.Response(413), httpx.Response(413, json={"code": "TOO_BIG"})):
        _mock_ra(monkeypatch, lambda r, x=resp: x)
        out = await R._dispatch_audited(req, body, principal, _sf_settings())
        assert out["error"] == "SimFlow 가 크기 한도로 받지 않았습니다(HTTP 413)." and out["hint"], "사유가 없으면 사유 칸을 지어내지 않는다(null 도)"
    _mock_ra(monkeypatch, lambda r: httpx.Response(200, json={"status": "ready"}))
    out = await R._dispatch_audited(req, body, principal, _sf_settings())
    assert out["stage"] == "failed" and "업로드 id 를 돌려주지 않았습니다" in out["error"]
