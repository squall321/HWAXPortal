# 연결 토큰 암호화 · sqlite 0600(docs/request-1027 HP-05 · 사용자 결정 D-5) — 원장에는 암호문, 읽으면 평문, 옛 평문 행은 기동 때 바꾼다
"""왜 — 사람이 등록한 외부 토큰(RA · TestScope · FMEA · MatNexus …)이 users.sqlite `connections` 에 평문이었고, 포털 sqlite 넷이 644 였다.
키를 잃은 박스에서도 포털은 떠야 한다 — 풀 수 없는 연결은 '등록 없음' 으로 읽히고 기동 로그가 몇 건인지 말한다.
"""
import logging
import os
import sqlite3

import pytest

from app.auth.conn_crypt import PREFIX, ConnCipher
from app.auth.user_store import UserStore
from app.config import Settings


def _settings(tmp_path, **kw) -> Settings:
    return Settings(_env_file=None, user_store_path=str(tmp_path / "data/users.sqlite"),
                    conn_key_path=str(tmp_path / "secrets/conn.key"), **kw)


def _raw(tmp_path) -> list[tuple[str, str, str]]:
    with sqlite3.connect(tmp_path / "data/users.sqlite") as c:
        return c.execute("SELECT email, service, token FROM connections ORDER BY service").fetchall()


def test_등록은_암호문으로_쓰고_읽을_때_푼다(tmp_path):
    st = UserStore(_settings(tmp_path))
    st.set_connection(email="Kim@Corp.com", service="fmea", token="fmea_secret_token_1234", workspace="mx")
    (email, service, stored), = _raw(tmp_path)
    assert stored.startswith(PREFIX) and "fmea_secret_token_1234" not in stored, "원장에는 평문이 없다"
    assert st.get_connection(email="kim@corp.com", service="fmea") == {"token": "fmea_secret_token_1234", "workspace": "mx"}
    meta = st.connection_meta(email="kim@corp.com", service="fmea")
    assert meta["tail"] == "1234" and "unreadable" not in meta, "꼬리 4자는 평문의 꼬리다"
    key = tmp_path / "secrets/conn.key"
    assert key.stat().st_mode & 0o777 == 0o600 and (tmp_path / "secrets").stat().st_mode & 0o777 == 0o700


def test_옛_평문_행은_기동_때_제자리에서_바뀐다(tmp_path, caplog):
    UserStore(_settings(tmp_path))                               # 표를 만든다(행 없음)
    with sqlite3.connect(tmp_path / "data/users.sqlite") as c:   # 암호화 이전 판이 쓴 모양 그대로
        c.execute("INSERT OR REPLACE INTO connections (email, service, token, workspace, created_at) VALUES (?,?,?,?,?)",
                  ("lee@corp.com", "reportarchive", "rat_plain_9999", "", 1))
    with caplog.at_level(logging.INFO, logger="hwax.user_store"):
        st = UserStore(_settings(tmp_path))
    (_e, _s, stored), = _raw(tmp_path)
    assert stored.startswith(PREFIX) and "rat_plain_9999" not in stored
    assert st.get_connection(email="lee@corp.com", service="reportarchive")["token"] == "rat_plain_9999"
    assert any("1건을 암호문으로 바꿨다" in r.getMessage() for r in caplog.records)
    assert not any("rat_plain_9999" in r.getMessage() for r in caplog.records), "값은 찍지 않는다"


def test_키를_잃으면_등록이_없는_것으로_읽히고_기동_로그가_몇_건인지_말한다(tmp_path, caplog):
    st = UserStore(_settings(tmp_path))
    st.set_connection(email="kim@corp.com", service="matnexus", token="mnx_pat_abcdefgh")
    (tmp_path / "secrets/conn.key").unlink()                     # 키를 잃었다(비밀 묶음에서 되살리지 않았다)
    with caplog.at_level(logging.WARNING, logger="hwax.user_store"):
        st2 = UserStore(_settings(tmp_path))
    assert any("1건을 풀 수 없다" in r.getMessage() and "conn.key" in r.getMessage() for r in caplog.records), \
        [r.getMessage() for r in caplog.records]
    assert st2.get_connection(email="kim@corp.com", service="matnexus") is None, "풀 수 없는 것은 '등록 없음' — 다시 등록하게"
    assert st2.connection_meta(email="kim@corp.com", service="matnexus")["unreadable"] is True
    st2.set_connection(email="kim@corp.com", service="matnexus", token="mnx_pat_new_0001")
    assert st2.get_connection(email="kim@corp.com", service="matnexus")["token"] == "mnx_pat_new_0001", "다시 등록하면 새 키로 선다"


def test_키는_두_번째_기동에서도_같은_것을_쓴다(tmp_path):
    a = ConnCipher(tmp_path / "k/conn.key")
    b = ConnCipher(tmp_path / "k/conn.key")
    assert a.created and not b.created and b.decrypt(a.encrypt("t")) == "t"
    assert b.decrypt("plain-legacy") == "plain-legacy" and b.decrypt(PREFIX + "깨진값") is None


def test_기동이_포털_sqlite_를_0600_으로_맞춘다(tmp_path):
    from app.main import _tighten_sqlite
    files = {}
    for attr, rel in (("user_store_path", "data/users.sqlite"), ("conv_store_path", "data/conversations.sqlite"),
                      ("token_store_path", "secrets/token_store.sqlite"), ("agent_audit_log_path", "secrets/agent_audit.sqlite"),
                      ("procedures_store_path", "data/procedures.sqlite")):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")
        os.chmod(p, 0o644)
        files[attr] = str(p)
    real = tmp_path / "svc/agent_audit.sqlite"                    # /data 이관 — 심볼릭 링크의 대상을 맞춘다
    real.parent.mkdir()
    real.write_bytes(b"")
    os.chmod(real, 0o644)
    (tmp_path / "secrets/agent_audit.sqlite").unlink()
    (tmp_path / "secrets/agent_audit.sqlite").symlink_to(real)
    (tmp_path / "data/users.sqlite-wal").write_bytes(b"")
    os.chmod(tmp_path / "data/users.sqlite-wal", 0o644)
    real_wal = real.parent / "agent_audit.sqlite-wal"              # 링크된 DB 의 -wal 은 대상 옆에 생긴다(sqlite 가 링크를 따라간다)
    real_wal.write_bytes(b"")
    os.chmod(real_wal, 0o644)
    s = Settings(_env_file=None, **files)
    changed = _tighten_sqlite(s)
    for p in [*files.values(), str(real), str(tmp_path / "data/users.sqlite-wal"), str(real_wal)]:
        assert os.stat(p).st_mode & 0o777 == 0o600, p
    assert changed and _tighten_sqlite(s) == [], "이미 맞으면 건드리지 않는다"


@pytest.mark.parametrize("raw", ["", "plain", PREFIX])
def test_is_enc_는_머리만_본다(raw):
    assert ConnCipher.is_enc(raw) is raw.startswith(PREFIX)
