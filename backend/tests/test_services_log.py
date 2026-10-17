# 서비스 로그 — 기동마다 지우지 않고 덧붙이며, 디렉터리 700 · 파일 600 · 큰 로그는 한 벌 회전(10-17 cae00 리뷰 P1)
import importlib.util
import os
import stat
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services_log", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def m(tmp_path, monkeypatch):
    mod = _services_mod()
    logdir = tmp_path / "hwax-services"
    logdir.mkdir(mode=0o775)
    os.chmod(logdir, 0o775)                       # dev 박스의 실제 모양(drwxrwxr-x)
    monkeypatch.setattr(mod, "LOG_DIR", logdir)
    return mod


def _wait_for(path: Path, text: str, timeout: float = 10.0) -> str:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        if text in body:
            return body
        time.sleep(0.1)
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def test_기동은_앞_기록을_지우지_않고_덧붙이며_남이_못_읽게_한다(m, tmp_path):
    svc = {"name": "t-svc", "dir": str(tmp_path), "start": "echo second-run", "tier": 1}
    log = m.LOG_DIR / "t-svc.log"
    log.write_text("first-run 의 기록\n", encoding="utf-8")
    os.chmod(log, 0o664)
    assert m.start_one(svc) == "started (no health url)"
    body = _wait_for(log, "second-run")
    assert "first-run 의 기록" in body, "기동이 앞 기록을 지웠다"
    assert "=== start " in body and "second-run" in body
    assert _mode(log) == 0o600 and _mode(m.LOG_DIR) == 0o700, (oct(_mode(log)), oct(_mode(m.LOG_DIR)))


def test_갱신_단계의_출력이_바로_뒤_기동에_지워지지_않는다(m, tmp_path):
    """update_one 이 덧붙인 git 출력을 start_one 이 'wb' 로 열어 지워 왔다 — 갱신이 무엇을 했는지 로그에 안 남았다."""
    svc = {"name": "t-upd", "dir": str(tmp_path), "start": "echo started-now", "update": "echo pulled-something", "tier": 1}
    assert not m.update_one(svc).startswith("FAIL")
    m.start_one(svc)
    body = _wait_for(m.LOG_DIR / "t-upd.log", "started-now")
    assert "pulled-something" in body and "started-now" in body, body


def test_log_칸이_있으면_서비스_디렉터리의_그_파일에_쓴다(m, tmp_path):
    os.chmod(tmp_path, 0o755)                     # pytest 임시 디렉터리는 원래 700 이라 '안 건드렸다' 를 못 본다
    svc = {"name": "gw", "dir": str(tmp_path), "start": "echo gw-up", "log": "gateway.log", "tier": 1}
    assert m.svc_log(svc) == tmp_path / "gateway.log"
    m.start_one(svc)
    assert "gw-up" in _wait_for(tmp_path / "gateway.log", "gw-up")
    assert not (m.LOG_DIR / "gw.log").exists(), "두 곳에 나눠 쓰면 안 된다"
    assert _mode(tmp_path / "gateway.log") == 0o600
    assert _mode(tmp_path) == 0o755, "서비스 디렉터리(리포) 권한은 건드리지 않는다"


def test_실제_매니페스트의_게이트웨이는_gateway_log_한_곳이다():
    mod = _services_mod()
    gw = next(s for s in mod.load() if s["name"] == "mcp-gateway")
    assert gw.get("log") == "gateway.log"


def test_큰_로그는_한_벌만_넘기고_새로_연다(m, monkeypatch):
    monkeypatch.setattr(m, "LOG_ROTATE_BYTES", 10)
    log = m.LOG_DIR / "big.log"
    log.write_text("x" * 50, encoding="utf-8")
    (m.LOG_DIR / "big.log.1").write_text("older", encoding="utf-8")
    m.prep_log(log)
    assert log.stat().st_size == 0 and (m.LOG_DIR / "big.log.1").read_text() == "x" * 50
    m.prep_log(log)
    assert (m.LOG_DIR / "big.log.1").read_text() == "x" * 50, "작으면 넘기지 않는다"


def test_기동_대기의_로그_꼬리는_이번_기동이_쓴_줄만_보인다(m):
    log = m.LOG_DIR / "tail.log"
    log.write_text("앞 기동의 마지막 줄\n", encoding="utf-8")
    start = log.stat().st_size
    assert m._log_tail(log, start) == "", "앞 기동의 줄을 이번 진행으로 보였다"
    with open(log, "a", encoding="utf-8") as f:
        f.write("이번 기동 줄\n\n")
    assert m._log_tail(log, start) == "이번 기동 줄"
