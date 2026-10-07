# 활성 관리자가 0명인 박스가 조용히 뜨지 않는지 — 기동 로그 · /health/ready · update-all §6 이 같은 사실을 말하는가
"""관리자는 원장의 표지와 고정 목록(PORTAL_ADMIN_EMAILS)만 본다(docs/change-request-8-10 D-3). 관리자를 IdP 그룹으로 받던 박스
(mock·oidc — start.sh 는 지금도 MOCK_USER_GROUPS=portal-admin 을 넘긴다)는 그 판정으로 올라온 순간 관리자 화면을 열 사람이
없어진다. SSO 가 만든 원장 행은 groups 가 [] 이다. 그런데 기동 로그·/health/ready·update-all 어디에도 흔적이 없었고, 배선 설정은
관리자에게만 보인다 — 첫 증상이 '메뉴가 사라졌다' 였다. 본인·마지막 관리자 보호는 화면의 동작만 막고 이 승격 경로는 못 막는다.

원장은 임시 폴더에 만든다. 주소는 지어낸 값이다.
"""
import logging
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth.user_store import UserStore
from app.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
WHO = "someone@corp.example"


def _settings(tmp_path, **kw) -> Settings:
    return Settings(_env_file=None, auth_provider="mock", mock_user_email=WHO, mock_user_groups="portal-admin",
                    user_store_path=str(tmp_path / "users.sqlite"), **kw)


def test_세는_법은_마지막_관리자_보호와_같다(tmp_path):
    st = UserStore(_settings(tmp_path))
    assert st.no_active_admin() is False, "빈 원장은 처음 뜬 박스다 — 아직 아무도 들어오지 않았다"
    st.note_sso_login(email=WHO, name="아무개")                       # SSO 가 만든 행 — groups 는 []
    assert st.no_active_admin() is True
    assert st.no_active_admin(frozenset({WHO})) is False, "고정 목록의 활성 행은 관리자다"
    assert st.no_active_admin(frozenset({"typo@corp.example"})) is True, "원장에 행이 없는 고정 주소는 세지 않는다(set_admin 과 같다)"
    assert st.set_admin(WHO, True) == "set" and st.no_active_admin() is False
    st.set_status(WHO, "disabled")
    assert st.no_active_admin() is True and st.no_active_admin(frozenset({WHO})) is True, "정지된 관리자는 세지 않는다"


@pytest.mark.parametrize("pinned,expect", [("", True), (WHO, False)])
def test_기동_로그와_ready_에_보이고_고치면_재기동_없이_사라진다(tmp_path, monkeypatch, caplog, pinned, expect):
    """**이 파일의 이유다** — 종전엔 이 박스가 아무 표시 없이 떴다. /health/ready 는 무인증이라 코드만 싣는다."""
    s = _settings(tmp_path, portal_admin_emails=pinned)
    UserStore(s).note_sso_login(email=WHO, name="아무개")              # 올라오기 전부터 있던 행(관리자를 IdP 그룹으로 받던 사람)
    monkeypatch.setattr(main, "settings", s)
    main.app.dependency_overrides[get_settings] = lambda: s
    try:
        with caplog.at_level(logging.WARNING), TestClient(main.app) as c:
            got = c.get("/health/ready").json()
            assert got["status"] == "ready" and ("no_active_admin" in got["temporary"]) is expect, got
            assert c.get("/health").status_code == 200, "막지는 않는다 — 로그인·챗은 된다"
            if expect:      # 원장에 관리자가 생기면(고정 목록의 사람이 처음 들어오거나 부트스트랩 가입) 다음 요청부터 사라진다
                main.app.state.user_store.set_admin(WHO, True)
                assert "no_active_admin" not in c.get("/health/ready").json()["temporary"]
    finally:
        main.app.dependency_overrides.pop(get_settings, None)
    said = [r.getMessage() for r in caplog.records if r.levelno == logging.CRITICAL and "no_active_admin" in r.getMessage()]
    assert bool(said) is expect, [r.getMessage() for r in caplog.records]
    if expect:
        assert "PORTAL_ADMIN_EMAILS" in said[0] and WHO not in said[0], "무엇을 적으면 되는지 말하고, 주소는 싣지 않는다"


def test_원장을_못_세어도_ready_는_답하고_0명이라고_하지_않는다(tmp_path, monkeypatch):
    """모름을 0명으로 읽지 않는다 — 원장이 잠깐 안 읽힌다고 배포 로그에 '관리자 0명' 이 뜨면 거짓 경보다."""
    s = _settings(tmp_path)
    UserStore(s).note_sso_login(email=WHO, name="아무개")
    monkeypatch.setattr(main, "settings", s)
    main.app.dependency_overrides[get_settings] = lambda: s
    try:
        with TestClient(main.app) as c:
            def broken(_pinned=frozenset()):
                raise RuntimeError("원장 고장")

            monkeypatch.setattr(main.app.state.user_store, "no_active_admin", broken)
            got = c.get("/health/ready")
            assert got.status_code == 200 and "no_active_admin" not in got.json()["temporary"]
    finally:
        main.app.dependency_overrides.pop(get_settings, None)


# ── update-all §6 — /health/ready 를 읽어 배포 로그에 올린다 ───────────────────────────────────────────
def _gate(tmp_path: Path, ready_body: str) -> str:
    """§6 의 '포털 관리자' 블록을 원문 그대로 돌린다. curl 은 대역이다 — 떠 있는 포털을 부르지 않는다."""
    shim = tmp_path / "shim"; shim.mkdir(exist_ok=True)
    (shim / "curl").write_text(f"#!/usr/bin/env bash\nprintf '%s ' \"$@\" >> '{tmp_path}/curl.calls'\ncat <<'JSON'\n{ready_body}\nJSON\n")
    (shim / "curl").chmod(0o755)
    i = UA.index("# ── 관리자 화면을 열 사람이 있는가")
    block = UA[i:UA.index("# ── 내부 목적지가 프록시를 타지 않는가", i)]
    script = "\n".join(["set -uo pipefail", "FAIL=0",
                        'ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
                        '[ "$(command -v curl)" = "' + str(shim / "curl") + '" ] || { echo "대역 curl 이 아니다"; exit 9; }',
                        block, 'echo "FAIL=$FAIL"'])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                       env={"PATH": f"{shim}:{os.environ['PATH']}"})
    assert r.returncode == 0 and "unbound variable" not in r.stderr, r.stdout + r.stderr
    assert "/health/ready" in (tmp_path / "curl.calls").read_text(), "포털의 /health/ready 를 읽는다"
    return r.stdout


def test_update_all_은_관리자가_0명이면_경고로_말하고_실패로_세지_않는다(tmp_path):
    out = _gate(tmp_path, '{"status":"ready","temporary":["prod_mock","no_active_admin"]}')
    (line,) = [ln for ln in out.splitlines() if ln.startswith("BAD:")]
    assert "관리자" in line and "PORTAL_ADMIN_EMAILS" in line, out
    assert "FAIL=0" in out and "FAIL:" not in out, "경고다 — 로그인·챗은 되는 박스의 배포 판정을 세우지 않는다"


@pytest.mark.parametrize("body", ['{"status":"ready","temporary":[]}', '{"status":"ready","temporary":["prod_mock"]}', "",
                                  "<html>502</html>", '{"detail":"no_active_admin 이라는 글자가 있을 뿐인 다른 응답"}'])
def test_update_all_은_관리자가_있거나_판정할_수_없으면_조용하다(tmp_path, body):
    """포털이 안 떴으면 바로 위 프로브가 이미 ✗ 로 말했다 — 여기서 '0명' 을 지어내지 않는다."""
    out = _gate(tmp_path, body)
    assert "BAD:" not in out and "FAIL:" not in out and "FAIL=0" in out, out
