# services.py 로 띄우는 서비스가 infra/.env 의 NO_PROXY 를 받는다(docs/request-1027 HP-11) — 감시 · 부팅 유닛 · 손 기동 모두 이 길이다
"""왜 — 포털은 start.sh 가 NO_PROXY 를 명시해 넘기는데, services.py 로 뜨는 서비스(게이트웨이 등)는 부모 환경만 물려받았다. 운영자 셸에
프록시만 있고 NO_PROXY 가 없으면 내부 호출이 사내 프록시를 탄다(게이트웨이는 기동 때 스스로 보정해 가려져 있었다). 합집합 규칙은 start.sh 와 같다.
"""
import importlib.util
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def m(monkeypatch):
    spec = importlib.util.spec_from_file_location("hwax_services_np", ROOT / "infra/scripts/services.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for k in ("NO_PROXY", "no_proxy", "APPTAINERENV_NO_PROXY", "APPTAINERENV_no_proxy", "RA_HOST", "ARP_HOST"):
        monkeypatch.delenv(k, raising=False)
    return mod


def _infra(monkeypatch, m, values: dict):
    monkeypatch.setattr(m, "_infra_value", lambda k: values.get(k))


def test_infra_env_의_값이_두_철자에_문자_그대로_들어간다(m, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example:8080")
    _infra(monkeypatch, m, {"NO_PROXY": "192.0.2.3,ra.example", "RA_HOST": "198.51.100.7"})
    env = m.child_env()
    assert env["NO_PROXY"] == env["no_proxy"] == "127.0.0.1,localhost,::1,192.0.2.3,ra.example,198.51.100.7"
    assert env["HTTP_PROXY"] == "http://proxy.example:8080", "다른 변수는 그대로 물려준다"


def test_부모_값과_합치고_펼쳐지지_않은_참조와_모양이_틀린_주소는_뺀다(m, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "corp.local, 198.51.100.0/24")
    monkeypatch.setenv("APPTAINERENV_no_proxy", "localhost,svc.internal")
    _infra(monkeypatch, m, {"NO_PROXY": "${NO_PROXY},192.0.2.99", "no_proxy": "corp.local",
                            "RA_HOST": "http://203.0.113.5:3000", "ARP_HOST": "arp.example"})
    v = m.child_env()["NO_PROXY"].split(",")
    assert v == ["127.0.0.1", "localhost", "::1", "svc.internal", "corp.local", "198.51.100.0/24", "192.0.2.99", "arp.example"], v
    assert not any("$" in x for x in v), "펼쳐지지 않은 참조가 그대로 넘어가면 httpx 가 클라이언트를 못 만든다"


def test_infra_env_를_못_읽어도_부모_값으로_띄운다(m, monkeypatch):
    def boom(_k):
        raise m.InfraEnvUnreadable("권한 없음")
    monkeypatch.setattr(m, "_infra_value", boom)
    monkeypatch.setenv("no_proxy", "corp.local")
    monkeypatch.setenv("RA_HOST", "198.51.100.7")
    assert m.child_env()["no_proxy"] == "127.0.0.1,localhost,::1,corp.local,198.51.100.7"


def test_띄운_서비스가_실제로_그_값을_본다(m, monkeypatch, tmp_path):
    """start_one 의 로컬 기동 — 부모에 NO_PROXY 가 없어도 서비스 안에서 infra/.env 값이 보인다(크론 · systemd 와 같은 꼴)."""
    _infra(monkeypatch, m, {"NO_PROXY": "192.0.2.3"})
    out = tmp_path / "np.txt"
    svc = {"name": "t-np", "dir": str(tmp_path), "log": "svc.log",
           "start": f"printf '%s|%s' \"$NO_PROXY\" \"$no_proxy\" > {out}"}
    assert m.start_one(svc) == "started (no health url)"
    end = time.monotonic() + 10
    while time.monotonic() < end and not (out.exists() and out.read_text()):
        time.sleep(0.05)
    assert out.read_text() == "127.0.0.1,localhost,::1,192.0.2.3|127.0.0.1,localhost,::1,192.0.2.3"
