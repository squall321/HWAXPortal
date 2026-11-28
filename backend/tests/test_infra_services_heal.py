# 서비스 감시(services.py heal) — 포트 연결 거부가 세 번일 때만 down · up, 느린 응답은 죽음이 아니다, 백오프 · update-all 동안 건너뜀(FU-D22)
"""왜 — 10-18 07:11 UTC dev 의 earlyoom 이 포털(인스턴스는 남고 앱만) · 게이트웨이 · mxwp-mcp · searxng 를 내렸고 14시간 아무도 다시 띄우지
않았다. 사용자 결정 10-19 '감시 보강만'. 판정이 헐거우면 바쁜 에이전트 서버를 다시 띄워 도는 심의를 끊으므로 연결 거부만 죽음으로 본다.

매니페스트(load)는 가짜 목록으로, down · up 은 기록만 하게 바꾼다. 판정은 진짜 소켓(듣는 포트 · 닫힌 포트)으로 본다.
"""
import importlib.util
import json
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location("hwax_services_heal", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def heal(tmp_path, monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "WATCH_STATE", tmp_path / "watchdog")
    monkeypatch.setattr(m, "WATCH_RECHECK_S", 0)
    monkeypatch.setattr(m, "_update_all_running", lambda: False)
    monkeypatch.setattr(m, "_stack_script_running", lambda: None)
    monkeypatch.setattr(m, "MAINT_MARK", tmp_path / "maintenance")
    monkeypatch.setattr(m, "enabled_here", lambda s: True)
    calls = []
    monkeypatch.setattr(m, "cmd_down", lambda names: calls.append(("down", *names)) or 0)
    monkeypatch.setattr(m, "cmd_up", lambda names: calls.append(("up", *names)) or 0)
    svcs = []
    monkeypatch.setattr(m, "load", lambda: svcs)
    return m, svcs, calls


def test_연결_거부_세_번이면_down_up_하고_백오프_안에서는_기다린다(heal, capsys):
    m, svcs, calls = heal
    port = _closed_port()
    svcs.append({"name": "gw", "watch": True, "health": f"http://127.0.0.1:{port}/health"})
    assert m.cmd_heal([]) == 0
    assert calls == [("down", "gw"), ("up", "gw")]
    assert "gw 죽었다" in capsys.readouterr().out
    calls.clear()
    m.cmd_heal([])
    assert calls == [] and "백오프" in capsys.readouterr().out, "직전 복구 10분 안에는 다시 손대지 않는다"


def test_살아_있으면_손대지_않고_백오프를_푼다(heal, capsys):
    m, svcs, calls = heal
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    try:
        svcs.append({"name": "gw", "watch": True, "health": f"http://127.0.0.1:{srv.getsockname()[1]}/health"})
        m.WATCH_STATE.mkdir(parents=True)
        (m.WATCH_STATE / "gw.json").write_text(json.dumps({"count": 2, "last": 0}))
        m.cmd_heal([])
    finally:
        srv.close()
    assert calls == [] and capsys.readouterr().out == "", "아무 일 없으면 아무것도 찍지 않는다(크론 로그가 매분 쌓이지 않게)"
    assert not (m.WATCH_STATE / "gw.json").exists(), "산 것을 보면 백오프를 푼다"


def test_시간_초과_같은_모름은_죽음이_아니다(heal, monkeypatch):
    m, svcs, calls = heal
    svcs.append({"name": "agent", "watch": True, "health": "http://127.0.0.1:9/health"})
    monkeypatch.setattr(m, "_refused", lambda url: None)
    m.cmd_heal([])
    assert calls == [], "바쁜 서비스(시간 초과)를 다시 띄우면 도는 심의가 끊긴다"


def test_한_번의_깜박임으로는_손대지_않는다(heal, monkeypatch):
    m, svcs, calls = heal
    svcs.append({"name": "gw", "watch": True, "health": "http://127.0.0.1:9/health"})
    seq = iter([True, False])
    monkeypatch.setattr(m, "_refused", lambda url: next(seq))
    m.cmd_heal([])
    assert calls == []


def test_watch_가_없거나_update_all_이_돌면_건너뛴다(heal, monkeypatch):
    m, svcs, calls = heal
    port = _closed_port()
    svcs.append({"name": "ra", "health": f"http://127.0.0.1:{port}/health"})          # watch 없음 — dev 에서 원래 꺼진 것
    m.cmd_heal([])
    assert calls == []
    svcs.append({"name": "gw", "watch": True, "health": f"http://127.0.0.1:{port}/health"})
    monkeypatch.setattr(m, "_update_all_running", lambda: True)
    m.cmd_heal([])
    assert calls == [], "update-all 이 다시 띄우는 동안 끼어들지 않는다"


def test_매니페스트의_감시_대상():
    m = _mod()
    watched = {s["name"] for s in m.load() if s.get("watch")}
    assert watched == {"portal", "mcp-gateway", "agent-server", "mxwp-mcp", "searxng", "llm-status"}, watched
    portal = next(s for s in m.load() if s["name"] == "portal")
    assert "instance stop" in portal.get("stop", ""), "포털은 인스턴스만 남고 앱이 죽는다 — down 이 인스턴스를 내려야 up 이 새로 띄운다"


def test_llm_status_감시는_LLM_STATUS_를_켠_박스에서만이다(tmp_path, monkeypatch):
    """llm-status 는 기본 꺼짐(if_env: LLM_STATUS)이다. 감시는 enabled_here 를 거치므로 끈 박스에서는 그 포트가 죽어 있어도 띄우지 않고(꺼진 것은
    꺼진 채로), 켠 박스에서는 죽은 수집기를 다음 update-all 전에 다시 띄운다(반대 검토 11-02 INFO · docs/ops-dashboard OD-38)."""
    m = _mod()
    entry = next(s for s in m.load() if s["name"] == "llm-status")
    assert entry.get("watch") is True and entry.get("if_env") == "LLM_STATUS"
    port = _closed_port()
    (tmp_path / "infra").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    for k in ("LLM_STATUS", "LLM_STATUS_PORT"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(m, "WATCH_STATE", tmp_path / "watchdog")
    monkeypatch.setattr(m, "WATCH_RECHECK_S", 0)
    monkeypatch.setattr(m, "_update_all_running", lambda: False)
    monkeypatch.setattr(m, "_stack_script_running", lambda: None)
    monkeypatch.setattr(m, "MAINT_MARK", tmp_path / "maintenance")
    calls = []
    monkeypatch.setattr(m, "cmd_down", lambda names: calls.append(("down", *names)) or 0)
    monkeypatch.setattr(m, "cmd_up", lambda names: calls.append(("up", *names)) or 0)
    monkeypatch.setattr(m, "load", lambda: [entry])
    (tmp_path / "infra/.env").write_text(f"LLM_STATUS_PORT={port}\n")
    assert m.health_url(entry) == f"http://127.0.0.1:{port}/health"
    assert m.cmd_heal([]) == 0 and calls == [], "끈 박스 — 그 포트가 죽어 있어도 띄우지 않는다"
    (tmp_path / "infra/.env").write_text(f"LLM_STATUS=1\nLLM_STATUS_PORT={port}\n")
    m.cmd_heal([])
    assert calls == [("down", "llm-status"), ("up", "llm-status")], "켠 박스 — 죽은 수집기를 다시 띄운다"


# ── 비켜서기(docs/request-1125 HP-57) — update-collab · start · restart · stop · 손 down 중에도 다시 띄우던 것 ─────────────────────────


def test_표지_파일이_있으면_건너뛰고_지우면_다시_돈다(heal):
    m, svcs, calls = heal
    port = _closed_port()
    svcs.append({"name": "gw", "watch": True, "health": f"http://127.0.0.1:{port}/health"})
    m.MAINT_MARK.write_text("")
    assert m.cmd_heal([]) == 0 and calls == [], "손으로 내려 둔 동안(표지) 다시 띄우지 않는다"
    m.MAINT_MARK.unlink()
    m.cmd_heal([])
    assert calls == [("down", "gw"), ("up", "gw")], "표지를 거두면 다시 돈다"


def test_스택_명령이_돌면_건너뛴다(heal, monkeypatch):
    m, svcs, calls = heal
    port = _closed_port()
    svcs.append({"name": "gw", "watch": True, "health": f"http://127.0.0.1:{port}/health"})
    monkeypatch.setattr(m, "_stack_script_running", lambda: "update-collab.sh")
    m.cmd_heal([])
    assert calls == []


def _spawn(cmd, cwd):
    import subprocess
    import time
    p = subprocess.Popen(cmd, cwd=str(cwd))
    time.sleep(0.3)   # exec 가 끝나 /proc/<pid>/cmdline 이 새 명령줄이 될 때까지
    return p


@pytest.mark.parametrize("name", ["start.sh", "restart.sh", "stop.sh", "update-all.sh", "deploy-all-from-drive.sh"])
def test_이_리포의_스택_스크립트를_상대_경로로_띄워도_알아본다(tmp_path, monkeypatch, name):
    """진짜 프로세스로 본다 — `cd infra/scripts && ./stop.sh` 처럼 띄우면 명령줄은 './stop.sh' 뿐이라 cwd 로 풀어야 한다."""
    m = _mod()
    scripts = tmp_path / "repo/infra/scripts"
    scripts.mkdir(parents=True)
    (scripts / name).write_text("sleep 30\n")
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path / "repo")
    assert m._stack_script_running() is None
    p = _spawn(["bash", f"./{name}"], scripts)
    try:
        assert m._stack_script_running() == name
    finally:
        p.kill()
        p.wait()
    assert m._stack_script_running() is None


def test_다른_리포의_같은_이름_스크립트로는_비켜서지_않는다(tmp_path, monkeypatch):
    """에이전트 서버 ./start.sh 같은 다른 리포의 start.sh 가 돌 때마다 감시가 멈추면 안 된다."""
    m = _mod()
    (tmp_path / "repo/infra/scripts").mkdir(parents=True)
    other = tmp_path / "HWAXAgentServer"
    other.mkdir()
    (other / "start.sh").write_text("sleep 30\n")
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path / "repo")
    p = _spawn(["bash", "./start.sh"], other)
    try:
        assert m._stack_script_running() is None
    finally:
        p.kill()
        p.wait()


def test_update_collab_은_자리를_몰라_이름으로_본다(tmp_path, monkeypatch):
    m = _mod()
    (tmp_path / "repo/infra/scripts").mkdir(parents=True)
    ops = tmp_path / "ops"
    ops.mkdir()
    (ops / "update-collab.sh").write_text("sleep 30\n")
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path / "repo")
    p = _spawn(["bash", str(ops / "update-collab.sh")], ops)
    try:
        assert m._stack_script_running() == "update-collab.sh"
    finally:
        p.kill()
        p.wait()


def test_db_sync_적용을_막는_판정은_update_all_만이다():
    """표지 · start.sh 를 _update_all_running 에 섞으면 db-sync 적용이 손 점검 중에 막힌다 — 판정을 둘로 둔다."""
    import ast
    src = (ROOT / "infra/scripts/services.py").read_text()
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_update_all_running")
    body = ast.get_source_segment(src, fn)
    assert "MAINT_MARK" not in body and "_stack_script_running" not in body
