# PC 도우미 업로드 — 표 발급(세션 + CSRF) · 도우미 열림 · 받기(표만 · 한 번) · 취소 · 만료 · 주인 · 크기 · 첫 바이트 · 감사(docs/chat-ppt PP-D8)
"""DRM 문서는 그 PC 의 Office 만 연다. 웹 챗 단추가 표를 받아 PC 도우미(추출기 -Url 모드)를 깨우고, 도우미가 뽑은 글(.hwax.md)과 고르면
슬라이드 그림을 그 표로 **로그인 없이** 올린다. 그래서 표가 곧 자격이다 — 여기서 고정하는 것.

  · 발급은 브라우저 세션 + CSRF 로만, 업로드 게이트(/upload 와 같다)를 지난 사람만. 디스크에는 표의 해시만.
  · 도우미 자리는 표만 보고, 받는 계정(이름 · 메일)을 돌려준다 — 도우미가 사람에게 묻는 근거.
  · 받기는 표를 먼저 닫고 본문을 읽는다 — 두 번 못 올리고, 틀린 본문도 표를 닫는다. 머리말 · UTF-8 · PNG 첫 바이트 · 크기.
  · 상태 · 글 · 그림은 주인만(남의 표는 없는 표). 만료 · 취소 · 넘친 표 닫기. 감사에는 본문이 없다.
"""
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import pc_upload as pc
from app.agent import upload as up
from app.auth.cookies import CSRF_COOKIE
from app.auth.token_store import TokenStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app

PW = "pw123456"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000100e221bc330000000049454e44ae426082")
MD = ("---\nschema: hwax-doc/1\nsource: 설계검토.pptx\nkind: ppt\nunits: 2\nchars: 20\n---\n\n# 설계검토\n\n"
      "## [s.1] 개요\n\n낙하 높이 1.5 m\n\n## [s.2] 결과\n\n최대 응력 432 MPa\n")


@pytest.fixture()
def box(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTAL_ADMIN_EMAILS", raising=False)
    s = Settings(_env_file=None, user_store_path=str(tmp_path / "users.sqlite"),
                 token_store_path=str(tmp_path / "tokens.sqlite"), upload_staging_dir=str(tmp_path / "staging"),
                 local_bootstrap_admins="boss@corp.com")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = (app.state.user_store, app.state.token_store)
        app.state.user_store, app.state.token_store = UserStore(s), TokenStore(s)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "Boss", "password": PW})   # 부트스트랩 = 모든 권한
        c.post("/auth/local/signup", json={"email": "user@corp.com", "name": "User", "password": PW})
        assert app.state.user_store.approve("user@corp.com", by="boss@corp.com", groups=[])
        _SINCE["rowid"] = app.state.agent_audit._conn.execute("SELECT COALESCE(MAX(rowid), 0) FROM agent_audit").fetchone()[0]
        yield c, s
        app.state.user_store, app.state.token_store = keep
    app.dependency_overrides.pop(get_settings, None)


def _login(c, email) -> dict:
    c.cookies.clear()
    assert c.post("/auth/local/login", json={"email": email, "password": PW}).status_code == 200
    return {"X-CSRF-Token": c.cookies.get(CSRF_COOKIE)}


def _issue(c, h, **body) -> dict:
    r = c.post("/agent/upload/pc-ticket", json={"filename": "설계검토.pptx", "conversation_id": "conv-1", **body}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _send(c, t, doc=MD, slides=(), headers=None):
    files = [("doc", ("doc.hwax.md", doc.encode("utf-8") if isinstance(doc, str) else doc, "text/markdown"))]
    files += [("slides", (f"slide-{i:02d}.png", b, "image/png")) for i, b in enumerate(slides, start=1)]
    return c.post(f"/agent/upload/pc/{t}", files=files, data={"helper": "1"}, headers=headers or {})


# 감사 원장은 시험 세션 하나에 하나다(conftest) — 이 시험이 쓴 줄만 본다(box 가 시작할 때의 마지막 줄 번호).
_SINCE = {"rowid": 0}


def _audit_rows(event: str) -> list[dict]:
    cur = app.state.agent_audit._conn.execute(
        "SELECT principal, chat_id, status, meta FROM agent_audit WHERE event = ? AND rowid > ? ORDER BY rowid",
        (event, _SINCE["rowid"]))
    return [{"principal": p, "chat_id": ch, "status": st, "meta": json.loads(m) if m else {}} for p, ch, st, m in cur.fetchall()]


def test_발급은_세션과_CSRF_와_업로드_게이트를_지나야_한다(box):
    c, s = box
    c.cookies.clear()
    assert c.post("/agent/upload/pc-ticket", json={}).status_code == 401, "로그인 없이는 못 낸다"
    h = _login(c, "boss@corp.com")
    assert c.post("/agent/upload/pc-ticket", json={}).status_code == 403, "CSRF 없이는 못 낸다"
    hu = _login(c, "user@corp.com")
    assert c.post("/agent/upload/pc-ticket", json={}, headers=hu).status_code == 403, "업로드 권한이 없으면 못 낸다(/upload 와 같다)"
    h = _login(c, "boss@corp.com")
    out = _issue(c, h)
    t = out["ticket"]
    assert len(t) == 43 and out["expires_in_s"] == pc.TICKET_TTL_S and out["protocol"] == pc.PROTOCOL
    assert out["helper_url"] == f"hwax-doc://extract?t={t}&name=%EC%84%A4%EA%B3%84%EA%B2%80%ED%86%A0.pptx&slides=0"
    files = list((Path(s.upload_staging_dir) / "#pc-tickets").glob("*.json"))
    assert [f.name for f in files] == [hashlib.sha256(t.encode()).hexdigest() + ".json"], "디스크에는 표의 해시만"
    assert t not in files[0].read_text(encoding="utf-8")
    assert oct(files[0].stat().st_mode & 0o777) == "0o600"
    (row,) = _audit_rows("pc_ticket_issue")
    assert row["principal"] == "boss@corp.com" and row["chat_id"] == "conv-1" and row["meta"]["filename"] == "설계검토.pptx"


def test_PAT_로는_표를_못_낸다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    pat = c.post("/auth/pat", json={"name": "t", "ttl_days": 1}, headers=h).json().get("token")
    assert pat, "PAT 발급(시험 준비)"
    c.cookies.clear()
    r = c.post("/agent/upload/pc-ticket", json={}, headers={"Authorization": f"Bearer {pat}"})
    assert r.status_code == 401, "PC 에 포털 토큰을 두지 않는다 — 표는 브라우저 세션으로만"


def test_도우미는_표만으로_받는_계정을_보고_한_번_올린다(box):
    c, s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    c.cookies.clear()                                   # 도우미는 쿠키가 없다
    info = c.get(f"/agent/upload/pc/{t}", headers={"X-HWAX-Helper": "1"}).json()
    assert info["owner_email"] == "boss@corp.com" and info["owner_name"] == "Boss" and info["filename"] == "설계검토.pptx"
    assert info["helper_min"] == pc.HELPER_MIN and info["slides"] is False and info["slides_max"] == pc.SLIDES_MAX
    assert c.get(f"/agent/upload/pc/{t}").status_code == 200, "두 번 물어도 된다(열림은 한 번만 적는다)"
    assert len(_audit_rows("pc_ticket_open")) == 1
    r = _send(c, t)
    assert r.status_code == 200 and r.json() == {"ok": True, "chars": len(MD), "slides": 0}, r.text
    assert _send(c, t).status_code == 410, "같은 표로 두 번 못 올린다"
    h = _login(c, "boss@corp.com")
    v = c.get(f"/agent/upload/pc-ticket/{t}").json()
    assert v["state"] == "received" and v["received"]["doc_name"] == "설계검토.hwax.md" and v["received"]["chars"] == len(MD)
    st = v["staged"]
    assert st["ext"] == "md" and [d["id"] for d in st["destinations"]] == ["reportarchive_precise", "aidatahub"], \
        "다음 단계는 RA 정밀 변환(DocForge PC 묶음 — DF-D18) · AI 데이터 허브(PP-D11)"
    assert up.staged_path(s, "boss@corp.com", st["staging_id"], st["filename"]).read_text(encoding="utf-8") == MD, \
        "보내기(dispatch)가 그 상자를 그대로 집는다 — 상자에 .md 하나"
    d = c.get(f"/agent/upload/pc-ticket/{t}/doc")
    assert d.status_code == 200 and d.text == MD and d.headers["content-type"].startswith("text/markdown")
    (ok,) = [x for x in _audit_rows("pc_upload") if x["status"] == "ok"]
    assert ok["meta"]["chars"] == len(MD) and ok["meta"]["doc"] == "설계검토.hwax.md" and ok["meta"]["helper"] == "1"
    assert "432 MPa" not in json.dumps(ok, ensure_ascii=False), "감사에 본문을 남기지 않는다"


def test_받는_동안_표는_이미_닫혀_있어_두_번째가_끼지_못한다(box, monkeypatch):
    """끝난 뒤의 '이미 쓴 표' 만으로는 모자라다 — 본문을 읽고 두는 동안 같은 표의 두 번째 요청이 끼면 둘 다 받는다."""
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    seen: dict = {}
    real = pc.store

    def spy(settings, rec, text, slides):
        seen["state"] = pc._read(pc._file(settings, t))["state"]
        try:
            pc.claim(settings, t)
            seen["second"] = "claimed"
        except pc.TicketError as exc:
            seen["second"] = exc.status
        return real(settings, rec, text, slides)

    monkeypatch.setattr(pc, "store", spy)
    assert _send(c, t).status_code == 200
    assert seen == {"state": "receiving", "second": 410}


def test_틀린_글은_표를_닫고_까닭을_남긴다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    for bad, why in [("머리말 없는 글", "머리말"), ("---\nschema: other/1\n---\n본문", "머리말"),
                     ("---\nschema: hwax-doc/1\n---\n   \n", "글이 없습니다"), ("가".encode("cp949"), "UTF-8")]:
        t = _issue(c, h)["ticket"]
        r = _send(c, t, doc=bad)
        assert r.status_code == 422 and why in r.json()["detail"], (bad, r.text)
        assert c.get(f"/agent/upload/pc-ticket/{t}").json()["state"] == "failed"
        assert _send(c, t).status_code == 410, "틀린 본문도 표를 닫는다 — 다시 누르면 새 표"
    assert len([x for x in _audit_rows("pc_upload") if x["status"] == "failed"]) == 4


def test_BOM_과_CRLF_는_받고_원본_이름은_머리말에서_안전하게(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    doc = "﻿" + MD.replace("source: 설계검토.pptx", "source: ../../etc/pa:ss*wd.pptx").replace("\n", "\r\n")
    assert _send(c, t, doc=doc).status_code == 200
    assert c.get(f"/agent/upload/pc-ticket/{t}").json()["received"]["doc_name"] == "passwd.hwax.md", "경로 · 금지 글자를 뺀다"


def test_슬라이드_그림은_표가_청했을_때만_PNG_만_받는다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h, slides=True)["ticket"]
    assert _send(c, t, slides=[PNG, PNG + b"x"]).json()["slides"] == 2
    g = c.get(f"/agent/upload/pc-ticket/{t}/slides/2")
    assert g.status_code == 200 and g.content == PNG + b"x" and g.headers["content-type"] == "image/png"
    assert c.get(f"/agent/upload/pc-ticket/{t}/slides/3").status_code == 404
    assert c.get(f"/agent/upload/pc-ticket/{t}/slides/0").status_code == 404

    t2 = _issue(c, h, slides=True)["ticket"]
    r = _send(c, t2, slides=[PNG, b"GIF89a..."])
    assert r.status_code == 422 and "PNG 가 아닙니다" in r.json()["detail"]

    t3 = _issue(c, h)["ticket"]                       # 그림을 청하지 않은 표
    assert _send(c, t3, slides=[PNG]).json()["slides"] == 0, "청하지 않은 그림은 두지 않는다"


def test_상한을_넘는_본문은_표를_보기도_전에_막는다(box, monkeypatch):
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    monkeypatch.setattr(pc, "DOC_MAX_BYTES", 200)
    monkeypatch.setattr(pc, "SLIDES_MAX", 0)
    r = _send(c, t, doc=MD + "가" * 400_000)
    assert r.status_code == 413
    assert c.get(f"/agent/upload/pc-ticket/{t}").json()["state"] == "waiting", "표를 닫기 전에 막았다 — 그 표는 아직 쓸 수 있다"
    monkeypatch.setattr(pc, "DOC_MAX_BYTES", len(MD.encode()) - 1)
    monkeypatch.setattr(pc, "SLIDES_MAX", 12)
    r = _send(c, t)
    assert r.status_code == 422 and "MB 를 넘습니다" in r.json()["detail"]


def test_상태_글_그림은_주인만_본다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    assert _send(c, t).status_code == 200
    _login(c, "user@corp.com")
    for path in (f"/agent/upload/pc-ticket/{t}", f"/agent/upload/pc-ticket/{t}/doc", f"/agent/upload/pc-ticket/{t}/slides/1"):
        assert c.get(path).status_code == 404, path
    c.cookies.clear()
    assert c.get(f"/agent/upload/pc-ticket/{t}").status_code == 401


def test_만료된_표는_도우미도_받기도_막고_만료는_감사에_한_번만_적는다(box, monkeypatch):
    c, _s = box
    h = _login(c, "boss@corp.com")
    monkeypatch.setattr(pc, "TICKET_TTL_S", 0)
    t = _issue(c, h)["ticket"]
    monkeypatch.setattr(pc, "TICKET_TTL_S", 600)
    # 청소가 끼기 전에 — 표의 판정만으로 막는다
    assert c.get(f"/agent/upload/pc/{t}").status_code == 410
    assert _send(c, t).status_code == 410
    assert not [x for x in _audit_rows("pc_upload") if x["status"] == "expired"]
    v = c.get(f"/agent/upload/pc-ticket/{t}").json()
    assert v["state"] == "expired" and v["expires_in_s"] == 0
    exp = [x for x in _audit_rows("pc_upload") if x["status"] == "expired"]
    assert len(exp) == 1 and exp[0]["meta"]["filename"] == "설계검토.pptx", "상태를 묻는 김에 닫고 적는다"
    t_live = _issue(c, h, filename="살아 있는.pptx")["ticket"]
    c.get(f"/agent/upload/pc-ticket/{t}")
    assert len([x for x in _audit_rows("pc_upload") if x["status"] == "expired"]) == 1, "물을 때마다 · 발급마다 청소해도 만료는 한 번"
    assert c.get(f"/agent/upload/pc-ticket/{t_live}").json()["state"] == "waiting"


def test_열린_표가_넘치면_가장_오래된_것을_닫는다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    ts = [_issue(c, h)["ticket"] for _ in range(pc.OPEN_MAX + 1)]
    assert c.get(f"/agent/upload/pc-ticket/{ts[0]}").json()["state"] == "closed"
    assert all(c.get(f"/agent/upload/pc-ticket/{t}").json()["state"] == "waiting" for t in ts[1:])
    assert [x["status"] for x in _audit_rows("pc_upload")] == ["closed"]


def test_도우미에서_취소하면_화면이_곧바로_안다(box):
    c, _s = box
    h = _login(c, "boss@corp.com")
    t = _issue(c, h)["ticket"]
    assert c.post(f"/agent/upload/pc/{t}/cancel", json={"reason": "파일 고르기를 취소했다"}).json() == {"ok": True}
    v = c.get(f"/agent/upload/pc-ticket/{t}").json()
    assert v["state"] == "cancelled" and v["error"] == "파일 고르기를 취소했다"
    assert _send(c, t).status_code == 410
    assert c.post(f"/agent/upload/pc/{t}/cancel").status_code == 410


def test_표_꼴이_아니면_없는_표다(box):
    c, _s = box
    for bad in ("abc", "x" * 44, "a" * 42 + "!"):
        assert c.get(f"/agent/upload/pc/{bad}").status_code == 404, bad
    assert _send(c, "a" * 43).status_code == 404
