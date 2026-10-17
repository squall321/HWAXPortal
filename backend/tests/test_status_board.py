# 상시 상태판(Gatus) — 설정 생성기 · 띄우는 스크립트 · 매니페스트 항목 · update-all 5b · Drive 운반을 실물 스크립트로 시험한다
"""왜 — 2026-10-16 dev 아침, 포털 인스턴스는 '떠 있음' 인데 안의 백엔드만 죽어 start.sh 가 그냥 지나갔다(docs/improvement-1015 IM-D4).
상태판은 인스턴스가 아니라 **리스너의 응답**을 보고, 경보는 포털에 맡기지 않고 포털의 SMTP 설정으로 직접 보낸다(IM-D3 · IM-D6).

⚠ 실물을 건드리지 않는다. 생성기·띄우는 스크립트는 임시 포털 리포에 복사해 절대경로로 돌리고, apptainer 는 받은 인자만 적는 대역이다.
게이트웨이는 지어낸 HTTP 서버다(빈 포트). 리스너 시험은 이 시험이 빈 포트에 띄운 파이썬 프로세스만 내린다. 매니페스트의 url 은 전부
빈 포트·지어낸 서버를 가리킨다 — 생성기가 게이트웨이 /health 를 실제로 부르기 때문이다(이 박스의 9110 을 두드리지 않게).
"""
import http.server
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
MANIFEST = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}
FULL_SMTP = ("MAIL_BACKEND=smtp\nMAIL_FROM=sender@mail.test\nSMTP_HOST=smtp.mail.test\nSMTP_PORT=2525\n"
             "SMTP_USERNAME=robot\nSMTP_PASSWORD='p@ss$word #1'\nSMTP_STARTTLS=true\n")
ALERT_TO = "STATUS_ALERT_TO=team@mail.test\n"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _svc(name: str, health: str, *, tier: int = 10, **kw) -> dict:
    return {"name": name, "host": "local", "dir": ".", "start": "true", "health": health, "tier": tier, **kw}


class Lay:
    """임시 포털 리포 — services.py · 생성기 · 띄우는 스크립트 사본 + 지어낸 매니페스트·infra/.env·backend/.env."""

    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts").mkdir(parents=True)
        (self.repo / "infra/apptainer").mkdir()
        (self.repo / "backend").mkdir()
        for n in ("services.py", "gen-status-config.py", "status-board.sh"):
            shutil.copy(SCRIPTS / n, self.repo / "infra/scripts" / n)
        self.out = self.repo / "infra/.state/status/config.yaml"
        self.manifest([_svc("portal", f"http://127.0.0.1:{_free_port()}/health", tier=0)])

    def manifest(self, services: list[dict]) -> None:
        (self.repo / "infra/services.yaml").write_text(yaml.safe_dump({"services": services}, allow_unicode=True), encoding="utf-8")

    def infra_env(self, text: str) -> None:
        (self.repo / "infra/.env").write_text(text, encoding="utf-8")

    def backend_env(self, text: str) -> None:
        (self.repo / "backend/.env").write_text(text, encoding="utf-8")

    def gen(self, **env) -> subprocess.CompletedProcess:
        base = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        return subprocess.run([sys.executable, "-B", str(self.repo / "infra/scripts/gen-status-config.py")],
                              capture_output=True, text=True, timeout=60, env={**base, **env})

    def text(self) -> str:
        return self.out.read_text(encoding="utf-8")

    def config(self) -> dict:
        # Gatus 가 읽는 대로 — 값의 `$$` 는 `$` 다(생성기는 `$` 를 전부 `$$` 로 적는다)
        return yaml.safe_load(self.text().replace("$$", "$"))

    def endpoints(self) -> dict[str, dict]:
        return {e["url"]: e for e in self.config()["endpoints"]}


@pytest.fixture()
def lay(tmp_path):
    return Lay(tmp_path)


@pytest.fixture()
def gateway():
    """지어낸 게이트웨이 /health — state['body'] 를 낸다."""
    state = {"body": {"status": "ok", "tools": 5, "backends": {}}}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            raw = json.dumps(state["body"]).encode()
            self.send_response(200 if self.path == "/health" else 404)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{srv.server_address[1]}/health"
    yield state
    srv.shutdown()
    srv.server_close()


# ── 생성기 — 무엇을 보나 ─────────────────────────────────────────────────────────────────────────────────
def test_이_박스가_다루는_서비스의_리스너_전부를_싣고_대상_아닌_것과_자기_자신은_뺀다(lay):
    p = [_free_port() for _ in range(7)]
    lay.manifest([
        _svc("portal", f"http://127.0.0.1:{p[0]}/health", tier=0, urls=["http://127.0.0.1:${HTTP_PORT:-1}/health"]),   # 포트는 infra/.env 에서
        _svc("pool", f"http://127.0.0.1:{p[2]}/health", tier=5, if_env="POOL_ON"),
        _svc("site", f"http://127.0.0.1:{p[3]}/api", expect=200, urls=[f"http://127.0.0.1:{p[4]}/"]),
        _svc("moved", f"http://127.0.0.1:{p[5]}/x", unless_env="MOVED_HOST"),
        _svc("devonly", f"http://127.0.0.1:{p[6]}/y", tier=20, only_on="no-such-host-for-status-test"),
        MANIFEST["status-board"],
    ])
    lay.infra_env(f"HTTP_PORT={p[1]}\nMOVED_HOST=elsewhere.test\nSTATUS_BOARD=1\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    eps = lay.config()["endpoints"]
    assert [e["url"] for e in eps] == [f"http://127.0.0.1:{p[0]}/health", f"http://127.0.0.1:{p[1]}/health",
                                       f"http://127.0.0.1:{p[3]}/api", f"http://127.0.0.1:{p[4]}/"], eps
    assert [e["group"] for e in eps] == ["portal", "portal", "site", "site"]
    assert all(e["name"] == e["url"].removeprefix("http://") for e in eps), "이름은 호스트:포트/경로"
    assert "status-board" not in {e["group"] for e in eps}, "상태판은 자기 자신을 보지 않는다(STATUS_BOARD 가 있어도)"
    skip = next(ln for ln in r.stdout.splitlines() if "이 박스 대상 아님" in ln)
    assert "pool(if_env=POOL_ON" in skip and "moved(unless_env=MOVED_HOST" in skip and "devonly(only_on=" in skip, skip
    assert "검사 4개 — 서비스 2곳" in r.stdout, r.stdout
    lay.infra_env(f"HTTP_PORT={p[1]}\nMOVED_HOST=elsewhere.test\nPOOL_ON=1\n")
    assert lay.gen().returncode == 0
    assert f"http://127.0.0.1:{p[2]}/health" in lay.endpoints(), "if_env 키가 생기면 그 서비스도 본다"


def test_조건은_연결이_먼저고_expect_가_있으면_그_코드_없으면_5xx_가_아니다(lay):
    p = [_free_port() for _ in range(4)]
    lay.manifest([_svc("a", f"http://127.0.0.1:{p[0]}/health", urls=[f"http://127.0.0.1:{p[1]}/"]),
                  _svc("b", f"http://127.0.0.1:{p[2]}/api", expect=200, urls=[f"http://127.0.0.1:{p[3]}/mcp"]),
                  _svc("c", f"http://127.0.0.1:{_free_port()}/", expect=[200, 302])])
    assert lay.gen().returncode == 0
    conds = {e["url"]: e["conditions"] for e in lay.config()["endpoints"]}
    for url, c in conds.items():
        # 연결 조건이 없으면 연결 실패(상태 0)가 '[STATUS] < 500' 으로 초록이 된다 — Gatus 는 호출 오류만으로 실패로 치지 않는다
        assert c[0] == "[CONNECTED] == true", (url, c)
    assert conds[f"http://127.0.0.1:{p[0]}/health"] == ["[CONNECTED] == true", "[STATUS] < 500"]
    assert conds[f"http://127.0.0.1:{p[1]}/"] == ["[CONNECTED] == true", "[STATUS] < 500"]
    assert conds[f"http://127.0.0.1:{p[2]}/api"] == ["[CONNECTED] == true", "[STATUS] == 200"]
    assert conds[f"http://127.0.0.1:{p[3]}/mcp"] == ["[CONNECTED] == true", "[STATUS] < 500"], "expect 는 health(첫 url)에만"
    assert any(c[1] == "[STATUS] == any(200, 302)" for c in conds.values()), conds
    cfg = lay.config()
    assert cfg["web"] == {"address": "127.0.0.1", "port": 8740}, "기본 포트 · 루프백(Gatus 기본은 0.0.0.0)"
    assert cfg["skip-invalid-config-update"] is True
    assert {e["interval"] for e in cfg["endpoints"]} == {"1m"}
    assert all(e["ui"] == {"resolve-successful-conditions": True} for e in cfg["endpoints"])
    lay.infra_env("STATUS_BOARD_PORT=18742\nSTATUS_BOARD_INTERVAL=30s\n")
    assert lay.gen().returncode == 0
    cfg = lay.config()
    assert cfg["web"]["port"] == 18742 and {e["interval"] for e in cfg["endpoints"]} == {"30s"}


def test_게이트웨이는_백엔드마다_이름이_든_조건을_싣고_하나라도_false_면_실패한다(lay, gateway):
    gateway["body"] = {"status": "ok", "tools": 7, "backends": {"ai-data-hub": True, "heax-x_y": False, "odd.name": True}}
    lay.manifest([_svc("mcp-gateway", gateway["url"], tier=16)])
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    c = lay.endpoints()[gateway["url"]]["conditions"]
    assert c == ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok", "[BODY].tools >= 1",
                 "[BODY].backends.ai-data-hub != false", "[BODY].backends.heax-x_y != false",
                 "[BODY].backends != pat(*:false*)"], c
    assert "백엔드 2곳" in r.stdout and "1곳은 아래 한 줄로만" in r.stdout, r.stdout
    # 게이트웨이가 답하지 않으면 이름을 모른다 — '하나라도 false' 한 줄만, 그 사실을 말한다
    dead = f"http://127.0.0.1:{_free_port()}/health"
    lay.manifest([_svc("mcp-gateway", dead, tier=16)])
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    c = lay.endpoints()[dead]["conditions"]
    assert c == ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok", "[BODY].tools >= 1",
                 "[BODY].backends != pat(*:false*)"], c
    assert "답하지 않아" in r.stdout, r.stdout


def test_에이전트_서버는_도는_심의_칸을_보고_LLM_라우터는_풀을_켠_박스에서만_본다(lay):
    agent = _svc("agent-server", f"http://127.0.0.1:{_free_port()}/health", tier=20)
    router = {**MANIFEST["llm-router"]}
    lay.manifest([router, agent])
    lay.infra_env("LLM_ROUTER_PORT=19131\n")
    assert lay.gen().returncode == 0
    eps = lay.endpoints()
    assert "http://127.0.0.1:19131/health" not in eps, "풀(LLM_UPSTREAMS)이 없으면 라우터를 보지 않는다"
    assert eps[agent["health"]]["conditions"] == [
        "[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok",
        "has([BODY].delib_active) == true", "[BODY].delib_active > -1", "[BODY].delib_queued > -1"]
    lay.infra_env("LLM_UPSTREAMS=http://203.0.113.5:8000/v1,http://203.0.113.6:8000/v1\nLLM_ROUTER_PORT=19131\n")
    assert lay.gen().returncode == 0
    assert lay.endpoints()["http://127.0.0.1:19131/health"]["conditions"] == [
        "[CONNECTED] == true", "[STATUS] == 200", "[BODY].status == ok", "[BODY].models.match == true",
        "[BODY].upstreams_up == [BODY].upstreams_total"]


def test_Gatus_키가_겹치는_두_리스너는_번호로_가른다(lay):
    port = _free_port()
    lay.manifest([_svc("x", f"http://127.0.0.1:{port}/a_b", urls=[f"http://127.0.0.1:{port}/a.b"])])
    assert lay.gen().returncode == 0
    names = [e["name"] for e in lay.config()["endpoints"]]
    assert names == [f"127.0.0.1:{port}/a_b", f"127.0.0.1:{port}/a.b (2)"], names


# ── 생성기 — 경보 ──────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("infra,backend,rc,needle", [
    ("", FULL_SMTP, 0, "경보 꺼짐 — infra/.env 에 STATUS_ALERT_TO 가 없다"),
    (ALERT_TO, None, 3, "backend/.env 가 없어"),
    (ALERT_TO, FULL_SMTP.replace("MAIL_BACKEND=smtp", "MAIL_BACKEND=console"), 3, "smtp 가 아니라 'console' 다"),
    (ALERT_TO, FULL_SMTP.replace("MAIL_BACKEND=smtp", "MAIL_BACKEND=graph"), 3, "Graph"),
    (ALERT_TO, FULL_SMTP.replace("MAIL_BACKEND=smtp\n", ""), 3, "console(기본)"),
    (ALERT_TO, FULL_SMTP.replace("SMTP_HOST=smtp.mail.test", "SMTP_HOST="), 3, "SMTP_HOST 가 없다"),
    (ALERT_TO, FULL_SMTP.replace("MAIL_FROM=sender@mail.test\n", ""), 3, "MAIL_FROM 이 없다"),
    (ALERT_TO, FULL_SMTP.replace("SMTP_PORT=2525", "SMTP_PORT=abc"), 3, "SMTP_PORT"),
    (ALERT_TO, FULL_SMTP.replace("SMTP_STARTTLS=true", "SMTP_STARTTLS=maybe"), 3, "SMTP_STARTTLS"),
])
def test_경보는_받는_곳과_포털_SMTP_설정이_다_있을_때만_싣는다(lay, infra, backend, rc, needle):
    lay.infra_env(infra)
    if backend is not None:
        lay.backend_env(backend)
    r = lay.gen()
    assert r.returncode == rc and needle in r.stdout, (rc, r.returncode, r.stdout + r.stderr)
    cfg = lay.config()
    assert "alerting" not in cfg and not any("alerts" in e for e in cfg["endpoints"]), "메일을 못 꾸리면 경보 덩이를 싣지 않는다"
    if rc == 3:
        assert any(ln.startswith("⚠") and needle in ln for ln in r.stdout.splitlines()), r.stdout


def test_경보가_켜지면_포털_SMTP_값_그대로_싣고_끝점마다_메일_경보를_건다(lay):
    lay.infra_env("STATUS_ALERT_TO=team@mail.test,oncall@mail.test\n")
    lay.backend_env(FULL_SMTP)
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    email = lay.config()["alerting"]["email"]
    assert email == {"from": "sender@mail.test", "host": "smtp.mail.test", "port": 2525, "to": "team@mail.test,oncall@mail.test",
                     "username": "robot", "password": "p@ss$word #1",
                     "default-alert": {"enabled": True, "failure-threshold": 5, "success-threshold": 2, "send-on-resolved": True}}, email
    eps = lay.config()["endpoints"]
    assert all(e["alerts"][0]["type"] == "email" and "services.sh status portal" in e["alerts"][0]["description"] for e in eps)
    assert "경보 켜짐 — 받는 곳 2곳" in r.stdout and "STARTTLS 는 서버가 내밀면 쓰고 인증서를 검증한다" in r.stdout, r.stdout
    # SMTP_STARTTLS=false — Gatus 는 STARTTLS 를 끌 수 없다(내밀면 쓴다) — 포털이 평문으로 보내는 박스에서 검증에 막히지 않게 검증을 끈다
    lay.backend_env(FULL_SMTP.replace("SMTP_STARTTLS=true", "SMTP_STARTTLS=False"))
    assert lay.gen().returncode == 0
    assert lay.config()["alerting"]["email"]["client"] == {"insecure": True}
    # 로그인 없는 릴레이 — 사용자·비밀번호 칸을 싣지 않는다(Gatus 는 비밀번호가 없으면 인증 없이 보낸다)
    lay.backend_env("MAIL_BACKEND=smtp\nMAIL_FROM=sender@mail.test\nSMTP_HOST=relay.mail.test\n")
    assert lay.gen().returncode == 0
    email = lay.config()["alerting"]["email"]
    assert email["port"] == 587 and "username" not in email and "password" not in email and "client" not in email, email


def test_비밀은_생성_파일에만_600_으로_있고_화면에_찍지_않는다(lay):
    lay.infra_env(ALERT_TO)
    lay.backend_env(FULL_SMTP)
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    for secret in ("p@ss", "team@mail.test", "smtp.mail.test", "robot"):
        assert secret not in r.stdout + r.stderr, f"화면에 찍었다: {secret}"
    assert stat.S_IMODE(lay.out.stat().st_mode) == 0o600 and stat.S_IMODE(lay.out.parent.stat().st_mode) == 0o700
    # Gatus 는 설정 글 전체에서 `$이름` 을 환경변수로 푼다 — `$` 를 두 번 적지 않으면 `$word` 가 빈 값이 되어 비밀번호가 조용히 잘린다
    assert "p@ss$$word #1" in lay.text() and "p@ss$word" not in lay.text().replace("$$", ""), lay.text()
    # 이미 있는 파일·디렉터리의 권한이 풀려 있어도 다시 조인다(내용이 같아 다시 쓰지 않을 때도)
    lay.out.chmod(0o644)
    lay.out.parent.chmod(0o755)
    assert lay.gen().returncode == 0
    assert stat.S_IMODE(lay.out.stat().st_mode) == 0o600 and stat.S_IMODE(lay.out.parent.stat().st_mode) == 0o700
    # 생성 파일은 추적되지 않는다(infra/.state/ 는 gitignore — 비밀이 공개 리포로 가지 않는다)
    ign = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "infra/.state/status/config.yaml"])
    assert ign.returncode == 0, "infra/.state/status/config.yaml 이 gitignore 되지 않는다"


@pytest.mark.parametrize("infra,key", [
    ("STATUS_BOARD_PORT=70000\n", "STATUS_BOARD_PORT"), ("STATUS_BOARD_PORT=87x0\n", "STATUS_BOARD_PORT"),
    ("STATUS_BOARD_INTERVAL=5\n", "STATUS_BOARD_INTERVAL"), ("STATUS_BOARD_INTERVAL=1d\n", "STATUS_BOARD_INTERVAL"),
    ("STATUS_ALERT_TO=<팀 공용 주소>\n", "STATUS_ALERT_TO"), ("STATUS_ALERT_TO=team@mail.test,oops\n", "2번째"),
])
def test_손잡이_값이_틀리면_쓰지_않고_옛_설정을_그대로_둔다(lay, infra, key):
    assert lay.gen().returncode == 0
    before = lay.text()
    lay.infra_env(infra)
    lay.backend_env(FULL_SMTP)
    r = lay.gen()
    assert r.returncode == 2 and key in r.stdout and "쓰지 않았다" in r.stdout, r.stdout + r.stderr
    assert lay.text() == before
    assert "<팀" not in r.stdout and "oops" not in r.stdout, "틀린 값(자리표시·주소)을 그대로 찍지 않는다"


def test_같은_내용이면_다시_쓰지_않는다(lay):
    assert lay.gen().returncode == 0
    m0 = lay.out.stat().st_mtime_ns
    time.sleep(0.02)
    r = lay.gen()
    assert r.returncode == 0 and "설정 그대로" in r.stdout and lay.out.stat().st_mtime_ns == m0, r.stdout
    lay.infra_env("STATUS_BOARD_INTERVAL=2m\n")
    r = lay.gen()
    assert r.returncode == 0 and "설정을 새로 썼다" in r.stdout and lay.out.stat().st_mtime_ns != m0, r.stdout
    left = sorted(p.name for p in lay.out.parent.iterdir())
    assert left == [".gen.lock", "config.yaml", "data", "push.json"], f"임시 파일이 남았거나 모르는 파일이 생겼다: {left}"


def test_볼_리스너가_하나도_없으면_쓰지_않는다(lay):
    lay.manifest([MANIFEST["status-board"]])
    lay.infra_env("STATUS_BOARD=1\n")
    r = lay.gen()
    assert r.returncode == 1 and "하나도 없다" in r.stdout and not lay.out.exists(), r.stdout + r.stderr


# ── backend/.env 읽기 — 포털(pydantic-settings → python-dotenv)과 같은가(정본을 오라클로) ─────────────────────────────
_DOTENV_CASES = [
    "SMTP_HOST=smtp.example\n",
    "SMTP_HOST=smtp.example # 주석\n",
    "SMTP_HOST=smtp.example#붙은글\n",
    "export SMTP_HOST=smtp.example\n",
    "  SMTP_HOST = smtp.example  \n",
    "SMTP_PASSWORD='a b #c'\n",
    'SMTP_PASSWORD="a\\"b \\n c" # 주석\n',
    "SMTP_PASSWORD='it\\'s'\n",
    'SMTP_PASSWORD="x" 꼬리\n',
    "SMTP_PASSWORD=ab$cd\n",
    "BASE=pre\nSMTP_PASSWORD=${BASE}-x-${NOPE:-dflt}\n",
    "smtp_host=lower\nSMTP_HOST=upper\n",
    "SMTP_HOST=first\nSMTP_HOST=\n",
    "# SMTP_HOST=commented\nMAIL_FROM= #only-comment\n",
    "SMTP_HOST\nMAIL_BACKEND=smtp\r\n",
]


@pytest.mark.parametrize("text", _DOTENV_CASES)
def test_backend_env_는_포털이_읽는_규칙으로_읽는다(tmp_path, text):
    dotenv = pytest.importorskip("dotenv")
    spec = importlib.util.spec_from_file_location("gen_status_for_test", SCRIPTS / "gen-status-config.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    p = tmp_path / ".env"
    p.write_bytes(text.encode("utf-8"))
    want = {k.lower(): v for k, v in dotenv.dotenv_values(p).items() if v is not None}
    assert gen._dotenv(p) == want, text


# ── 띄우는 스크립트 ────────────────────────────────────────────────────────────────────────────────────
def _stub(lay: Lay) -> tuple[Path, Path]:
    stub = lay.tmp / "apptainer"
    stub.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$STUB_OUT"\n', encoding="utf-8")
    stub.chmod(0o755)
    return stub, lay.tmp / "argv.txt"


def _launch(lay: Lay, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    stub, out = _stub(lay)
    e = {"PATH": os.environ["PATH"], "HOME": str(lay.tmp), "APPTAINER": str(stub), "STUB_OUT": str(out), **(env or {})}
    return subprocess.run(["bash", str(lay.repo / "infra/scripts/status-board.sh"), *args], capture_output=True, text=True, env=e, timeout=60)


def test_run_은_설정이_없거나_루프백_그_포트가_아니거나_이미지가_없으면_띄우지_않는다(lay):
    argv = lay.tmp / "argv.txt"
    (lay.repo / "infra/apptainer/gatus.sif").write_text("")
    r = _launch(lay, "run")
    assert r.returncode == 2 and "설정이 없다" in r.stderr and "gen-status-config.py" in r.stderr, r.stderr
    lay.infra_env("STATUS_BOARD_PORT=18751\n")
    assert lay.gen().returncode == 0
    lay.infra_env("STATUS_BOARD_PORT=18752\n")                    # 포트를 바꾸고 설정을 다시 만들지 않았다
    r = _launch(lay, "run")
    assert r.returncode == 2 and "127.0.0.1:18752 가 아니다" in r.stderr and "port='18751'" in r.stderr, r.stderr
    lay.infra_env("STATUS_BOARD_PORT=18751\n")
    lay.out.write_text(lay.text().replace("address: 127.0.0.1", "address: 0.0.0.0"), encoding="utf-8")
    r = _launch(lay, "run")
    assert r.returncode == 2 and "address='0.0.0.0'" in r.stderr, "인증 없는 화면을 모든 인터페이스에 띄우지 않는다"
    assert lay.gen().returncode == 0                                # 다시 만들면 루프백으로 돌아온다
    lay.infra_env("STATUS_BOARD_PORT=abc\n")
    r = _launch(lay, "run")
    assert r.returncode == 2 and "STATUS_BOARD_PORT='abc'" in r.stderr, r.stderr
    lay.infra_env("STATUS_BOARD_PORT=18751\n")
    (lay.repo / "infra/apptainer/gatus.sif").unlink()
    r = _launch(lay, "run")
    assert r.returncode == 1 and "이미지가 없다" in r.stderr and "images-from-drive" in r.stderr, r.stderr
    assert not argv.exists(), "apptainer 를 부르지 않는다"


def test_run_은_설정_디렉터리를_읽기_전용으로_바인드하고_환경을_비우고_gatus_를_띄운다(lay):
    lay.infra_env("STATUS_BOARD_PORT=18753\n" + ALERT_TO)
    lay.backend_env(FULL_SMTP)
    assert lay.gen().returncode == 0
    sif = lay.repo / "infra/apptainer/gatus.sif"
    sif.write_text("")
    r = _launch(lay, "run", env={"STATUS_BOARD_PORT": "9999", "SMTP_PASSWORD": "from-shell"})
    assert r.returncode == 0, r.stderr
    assert "STATUS_BOARD_PORT=9999 는 run 에서 쓰지 않는다" in r.stderr, "환경의 포트는 쓰지 않고 알린다"
    argv = (lay.tmp / "argv.txt").read_text().splitlines()
    assert argv[:4] == ["exec", "--cleanenv", "--bind", f"{lay.repo}/infra/.state/status:/config:ro"], argv
    assert argv[-6:] == ["--env", "GATUS_CONFIG_PATH=/config/config.yaml", "--env", "GATUS_LOG_LEVEL=WARN", str(sif), "/gatus"], argv
    middle = argv[4:-6]
    assert middle[:2] == ["--bind", f"{lay.repo}/infra/.state/status/data:/data"], f"기록(sqlite)만 쓰기 바인드로 온다: {middle}"
    assert (lay.repo / "infra/.state/status/data").is_dir() and oct((lay.repo / "infra/.state/status/data").stat().st_mode & 0o777) == "0o700"
    rest = middle[2:]
    assert rest == [] or (len(rest) == 2 and rest[0] == "--bind" and rest[1].endswith(":/etc/ssl/certs/ca-certificates.crt:ro")), \
        f"그 뒤에는 호스트 CA 묶음 덧바인드 하나만 온다: {rest}"
    assert not any("p@ss" in a or "from-shell" in a for a in argv), "비밀은 argv 로 넘기지 않는다"


def _listener(port: int, *tag: str) -> subprocess.Popen:
    code = ("import socket,sys,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
            "s.bind(('127.0.0.1',int(sys.argv[1]))); s.listen(); time.sleep(120)")
    p = subprocess.Popen([sys.executable, "-c", code, str(port), *tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    deadline = time.monotonic() + 10
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            if time.monotonic() > deadline:
                p.kill()
                raise
            time.sleep(0.05)


def _listener_as(argv0: str, port: int) -> subprocess.Popen:
    """명령줄 첫 인자가 argv0 인 리스너 — 진짜 Gatus 의 명령줄은 `/gatus` 하나다(앞에 다른 인자가 없다). 위 `_listener(port, "/gatus")` 는
    `python -c … /gatus` 라 판정 패턴 `* /gatus *` 와 맞았지만 진짜는 안 맞아, 정지가 진짜 상태판을 '상태판이 아니다' 로 거부했다(2026-10-17 dev 실측)."""
    code = ("import socket,sys,time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); "
            "s.bind(('127.0.0.1',int(sys.argv[1]))); s.listen(); time.sleep(120)")
    p = subprocess.Popen([argv0, "-c", code, str(port)], executable=sys.executable, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + 10
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            if time.monotonic() > deadline:
                p.kill()
                raise
            time.sleep(0.05)


def test_stop_은_명령줄_첫_인자가_gatus_인_진짜_상태판을_내린다(lay):
    port = _free_port()
    lay.infra_env(f"STATUS_BOARD_PORT={port}\n")
    real = _listener_as("/gatus", port)
    try:
        assert open(f"/proc/{real.pid}/cmdline", "rb").read().split(b"\0")[0] == b"/gatus"
        r = _launch(lay, "stop")
        assert r.returncode == 0 and "내려갔다" in r.stdout, r.stdout + r.stderr
        assert real.wait(10) is not None
    finally:
        if real.poll() is None:
            real.kill()
    other = _listener_as("/usr/bin/gatus-notes", port)            # 첫 인자가 /gatus 로 끝나기만 하는 남의 것
    try:
        r = _launch(lay, "stop")
        assert r.returncode == 1 and "상태판(gatus)이 아니다" in r.stderr and other.poll() is None, r.stdout + r.stderr
    finally:
        other.kill()
        other.wait(10)


def test_stop_은_그_포트를_듣는_gatus_만_내린다(lay):
    port = _free_port()
    lay.infra_env(f"STATUS_BOARD_PORT={port}\n")
    r = _launch(lay, "stop")
    assert r.returncode == 0 and "이미 내려가 있다" in r.stdout, r.stdout + r.stderr
    other = _listener(port)
    try:
        r = _launch(lay, "stop")
        assert r.returncode == 1 and "상태판(gatus)이 아니다" in r.stderr and other.poll() is None, "남의 리스너는 건드리지 않는다"
    finally:
        other.kill()
        other.wait(10)
    mine = _listener(port, "/gatus")
    try:
        r = _launch(lay, "stop")
        assert r.returncode == 0 and "내려갔다" in r.stdout, r.stdout + r.stderr
        assert mine.wait(10) is not None
    finally:
        if mine.poll() is None:
            mine.kill()
    # 포트를 바꾼 뒤 옛 포트의 상태판 — stop 만 환경의 포트를 먼저 본다
    old = _listener(port, "/gatus")
    try:
        lay.infra_env(f"STATUS_BOARD_PORT={_free_port()}\n")
        r = _launch(lay, "stop", env={"STATUS_BOARD_PORT": str(port)})
        assert r.returncode == 0 and f":{port}" in r.stdout and old.wait(10) is not None, r.stdout + r.stderr
    finally:
        if old.poll() is None:
            old.kill()


# ── 매니페스트 항목 ────────────────────────────────────────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("svc_for_status_board", SCRIPTS / "services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_매니페스트_항목은_STATUS_BOARD_가_있는_박스에서만_다루고_생성_설정으로_지문을_잡는다(tmp_path, monkeypatch):
    entry = MANIFEST["status-board"]
    assert {k: entry[k] for k in ("dir", "if_env", "update", "fp_git", "fp", "start", "stop", "expect", "health", "tier")} == {
        "dir": ".", "if_env": "STATUS_BOARD", "update": False, "fp_git": False,
        "fp": ["infra/apptainer/gatus.sif", "infra/scripts/status-board.sh", "infra/scripts/gen-status-config.py",
               "infra/scripts/status-push.py", "infra/.state/status/config.yaml"],
        "start": "./infra/scripts/status-board.sh run", "stop": "./infra/scripts/status-board.sh stop", "expect": 200,
        "health": "http://127.0.0.1:${STATUS_BOARD_PORT:-8740}/health", "tier": 30}
    assert entry["tier"] > max(s.get("tier", 10) for n, s in MANIFEST.items() if n != "status-board"), "지켜보는 서비스들보다 뒤에 뜬다"
    m = _services_mod()
    (tmp_path / "infra").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    monkeypatch.delenv("STATUS_BOARD", raising=False)
    (tmp_path / "infra/.env").write_text("STATUS_BOARD_PORT=18761\n", encoding="utf-8")
    assert m.enabled_here(entry) is False and "if_env=STATUS_BOARD" in m.skip_reason(entry)
    assert m.health_url(entry) == "http://127.0.0.1:18761/health", "포트는 infra/.env 를 따른다(생성기·띄우는 스크립트와 같은 값)"
    (tmp_path / "infra/.env").write_text("STATUS_BOARD=1\n", encoding="utf-8")
    assert m.enabled_here(entry) is True and m.health_url(entry) == "http://127.0.0.1:8740/health"
    # 지문 — 생성 설정·이미지가 바뀌면 다시 띄우고, 포털 루트 .env 나 커밋은 보지 않는다(fp_git: false)
    (tmp_path / "infra/.state/status").mkdir(parents=True)
    (tmp_path / "infra/apptainer").mkdir()
    conf = tmp_path / "infra/.state/status/config.yaml"
    conf.write_text("endpoints: [a]\n")
    (tmp_path / "infra/apptainer/gatus.sif").write_bytes(b"v1")
    f1 = m.service_fp(entry)
    (tmp_path / ".env").write_text("NEW_KEY=1\n")
    assert m.service_fp(entry) == f1, "포털 루트 .env 는 상태판 지문이 아니다"
    conf.write_text("endpoints: [a, b]\n")
    f2 = m.service_fp(entry)
    assert f2 != f1, "생성 설정이 바뀌면 다시 띄운다"
    (tmp_path / "infra/apptainer/gatus.sif").write_bytes(b"v2")
    assert m.service_fp(entry) != f2, "이미지를 갈아 끼우면 다시 띄운다"


def test_services_cli_는_파일의_STATUS_BOARD_로만_켠다(tmp_path):
    """부팅 유닛과 같은 환경(env -i, infra/.env 파일만)에서 실제 매니페스트의 status-board 항목을 묻는다."""
    lay = tmp_path / "HWAXPortal"
    (lay / "infra/scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS / "services.py", lay / "infra/scripts/services.py")
    shutil.copy(ROOT / "infra/services.yaml", lay / "infra/services.yaml")

    def run(env_text, *args):
        (lay / "infra/.env").write_text(env_text)
        return subprocess.run(["env", "-i", f"PATH={os.environ['PATH']}", sys.executable, str(lay / "infra/scripts/services.py"), *args],
                              capture_output=True, text=True, timeout=60)
    assert run("HWAX_BOX=x\n", "enabled", "status-board").returncode == 1
    assert run("STATUS_BOARD=1   # 켠다\n", "enabled", "status-board").returncode == 0
    assert run("STATUS_BOARD=1\nSTATUS_BOARD_PORT=18762\n", "health", "status-board").stdout.strip() == "http://127.0.0.1:18762/health"


# ── update-all 5b ────────────────────────────────────────────────────────────────────────────────────
def _region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


def _block_5b() -> str:
    return _region("# ── 5b) 상시 상태판(Gatus)", "# ── 5c) 호출 추적(Phoenix)")      # 5b 다음은 5c(호출 추적)다 — test_call_trace 가 본다


class Box:
    """update-all 5b 를 원문 그대로 임시 포털에서 돌린다 — services.sh enabled · 생성기 · update-sites · status-board.sh stop 은 부른 사실만 적는
    대역이고 http_code 도 대역이다(실 포트를 두드리지 않는다)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts/lib").mkdir(parents=True)
        (self.repo / "infra/apptainer").mkdir()
        shutil.copy(SCRIPTS / "lib/skip-ledger.sh", self.repo / "infra/scripts/lib/skip-ledger.sh")
        self.calls, self.ledger = self.tmp / "calls.log", self.tmp / "ledger"
        self.calls.write_text("")
        self.ledger.write_text("")
        sh = {"services.sh": 'echo "services.sh $*" >> "{c}"; [ "$1" = enabled ] && exit "${{STUB_EN:-1}}"; exit 0',
              "update-sites.sh": 'echo "update-sites.sh $*" >> "{c}"; echo "  (대역) update-sites $*"; exit "${{STUB_US:-0}}"',
              "status-board.sh": 'echo "status-board.sh $*" >> "{c}"; echo "  (대역) status-board $*"; exit "${{STUB_STOP:-0}}"'}
        for name, body in sh.items():
            p = self.repo / "infra/scripts" / name
            p.write_text("#!/usr/bin/env bash\n" + body.format(c=self.calls) + "\n", encoding="utf-8")
            p.chmod(0o755)
        gen = self.repo / "infra/scripts/gen-status-config.py"
        gen.write_text("import os, pathlib, sys\n"
                       f"open({str(self.calls)!r}, 'a').write('gen-status-config.py\\n')\n"
                       "print('· (대역) 생성기')\n"
                       "if os.environ.get('STUB_GEN_WRITES') == '1':\n"
                       "    d = pathlib.Path(sys.argv[0]).resolve().parents[2] / 'infra/.state/status'; d.mkdir(parents=True, exist_ok=True)\n"
                       "    (d / 'config.yaml').write_text('endpoints: []\\n')\n"
                       "sys.exit(int(os.environ.get('STUB_GEN_RC', '0')))\n", encoding="utf-8")

    def run(self, infra_env: str = "", *, sif: bool = True, pre: str = "", post: str = "", **env) -> str:
        (self.repo / "infra/.env").write_text(infra_env, encoding="utf-8")
        if sif:
            (self.repo / "infra/apptainer/gatus.sif").write_text("")
        envfile = _region("_envfile_value() {", "\n}\n") + "\n}\n"
        body = _block_5b()
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'SELF_REPO="{self.repo}"', f'SVC="{self.repo}/infra/scripts/services.sh"',
            f'[ "$(cd "$SELF_REPO" && pwd)" = "{self.repo}" ] || exit 97',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            'http_code() { echo "${STUB_HTTP:-000}"; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"', f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"',
            envfile, pre, body, post, "echo END",
        ])
        base = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env={**base, **env})
        assert r.returncode != 97 and "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def called(self) -> list[str]:
        return self.calls.read_text().splitlines()


@pytest.fixture()
def box(tmp_path):
    return Box(tmp_path)


def _tag(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


def test_5b_꺼져_있으면_안_켠_기능으로_남기고_아무것도_띄우지_않는다(box):
    out = box.run("OTHER=1\n", STUB_EN="1")
    assert box.called() == ["services.sh enabled status-board"], box.called()
    assert "상시 상태판(Gatus)" in out and "STATUS_BOARD=1" in out and not _tag(out, "HR:") and not _tag(out, "FAIL:"), out
    led = box.ledger.read_text()
    assert led.startswith("상시 상태판(Gatus)\t") and "docs/improvement-1015/status-board.md" in led, led


def test_5b_꺼졌는데_상태판이_떠_있으면_내린다(box):
    out = box.run("STATUS_BOARD_PORT=18771\n", STUB_EN="1", STUB_HTTP="200")
    assert box.called() == ["services.sh enabled status-board", "status-board.sh stop"], box.called()
    assert any(":18771" in ln and "내렸다" in ln for ln in _tag(out, "OK:")), out
    out = box.run("", STUB_EN="1", STUB_HTTP="200", STUB_STOP="1")
    assert any("내리지 못했다" in ln for ln in _tag(out, "BAD:")) and not _tag(out, "FAIL:"), out


def test_5b_켜져_있으면_설정을_만든_뒤_update_sites_로_띄운다(box):
    out = box.run("STATUS_BOARD=1\n", STUB_EN="0", STUB_GEN_WRITES="1")
    assert box.called() == ["services.sh enabled status-board", "gen-status-config.py", "update-sites.sh status-board"], box.called()
    assert _tag(out, "HR:5b)") and any("http://127.0.0.1:8740" in ln for ln in _tag(out, "OK:")), out
    assert "  · (대역) 생성기" in out, "생성기 출력을 들여 보인다"
    assert not _tag(out, "FAIL:") and not _tag(out, "BAD:") and not box.ledger.read_text(), out


@pytest.mark.parametrize("gen_rc", ["0", "2"])
def test_5b_의_일반_생성은_1b2_의_경보_멈춤을_풀었다고_적는다(box, gen_rc):
    """1b2 가 건 경보 멈춤 — 생성기의 일반 생성은 늘 푼다(못 만들어도 — 옛 설정의 창을 걷는다). 그래서 완주 끝 · 정지 경로가 다시 부르지 않는다."""
    out = box.run("STATUS_BOARD=1\n", STUB_EN="0", STUB_GEN_WRITES="1", STUB_GEN_RC=gen_rc,
                  pre="HWAX_BOARD_PAUSED=1", post='echo "PAUSED=$HWAX_BOARD_PAUSED"')
    assert "PAUSED=0" in out.splitlines(), out


@pytest.mark.parametrize("env,want_calls,tag,needle", [
    ({"STUB_GEN_RC": "3", "STUB_GEN_WRITES": "1"}, True, "BAD:", "경보를 켜지 못했다"),
    ({"STUB_GEN_RC": "2"}, False, "FAIL:", "설정을 만들지 못했다"),
    ({"STUB_GEN_RC": "2", "STUB_GEN_WRITES": "1"}, True, "FAIL:", "옛 설정이 있으면 그 설정으로 돈다"),
    ({"STUB_GEN_WRITES": "1", "STUB_US": "1"}, True, "FAIL:", "띄우지 못했다"),
])
def test_5b_실패는_자리마다_가른다(box, env, want_calls, tag, needle):
    out = box.run("STATUS_BOARD=1\n", STUB_EN="0", **env)
    assert ("update-sites.sh status-board" in box.called()) == want_calls, box.called()
    assert any(needle in ln for ln in _tag(out, tag)), out


def test_5b_이미지가_없으면_기다리지_않고_실패로_센다(box):
    out = box.run("STATUS_BOARD=1\n", sif=False, STUB_EN="0", STUB_GEN_WRITES="1")
    assert "update-sites.sh status-board" not in box.called(), "health 를 120초 기다리지 않는다"
    assert any("이미지가 없다" in ln and "build-gatus.sh" in ln for ln in _tag(out, "FAIL:")), out


def test_5b_STATUS_BOARD_0_은_켜짐이라고_알린다(box):
    out = box.run("STATUS_BOARD=0\n", STUB_EN="0", STUB_GEN_WRITES="1")
    assert any("켜짐으로 읽힌다" in ln for ln in _tag(out, "BAD:")), out


def test_물려받은_상태판_포트를_버린다():
    """status-board.sh stop 은 환경의 STATUS_BOARD_PORT 를 먼저 본다 — 운영자 셸에 export 된 옛 포트가 update-sites → services.py down 으로
    흘러 지금 상태판 대신 옛 포트를 내리지 않게 update-all·update-sites 머리가 버린다(LLM 라우터 LP-D14 와 같다)."""
    us = (SCRIPTS / "update-sites.sh").read_text(encoding="utf-8")
    heads = (UA[:UA.index('SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"')],
             us[:us.index('ROOT="$(cd "$(dirname "$0")/../.." && pwd)"')])
    for head in heads:
        r = subprocess.run(["bash", "-c", head + '\necho "[${STATUS_BOARD_PORT-없음}]"\n'], capture_output=True, text=True, timeout=30,
                           env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "STATUS_BOARD_PORT": "9555"})
        assert r.stdout.split()[-1:] == ["[없음]"], r.stdout + r.stderr


def test_update_all_배선():
    i5, i5b, i6 = UA.index('hr "5) 게이트웨이 config 정합'), UA.index("# ── 5b) 상시 상태판(Gatus)"), UA.index('hr "6) 헬스게이트"')
    assert i5 < i5b < i6, "5b 는 §5(게이트웨이 재프로비저닝) 뒤 · §6 앞이다"
    # 다른 시험이 떼어 돌리는 구획(§5 의 드리프트 끝 · 3.5 · §4 · 1i)에 끼어들지 않는다
    assert UA.index("# ── 5b)") > UA.index('    # 서비스를 띄운 뒤에도 **게이트웨이가 아는 주소**'), "§5 끝 뒤"
    head = UA[:UA.index("set -uo pipefail")]
    assert "5b) 상시 상태판" in head and "STATUS_BOARD" in head, "사용법의 순서 목록에 있다"
    for line in _block_5b().splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"


# ── Drive 운반 ───────────────────────────────────────────────────────────────────────────────────────
def test_images_to_drive_는_gatus_sif_를_함께_싣고_체크섬에_넣는다(tmp_path):
    src = (SCRIPTS / "images-to-drive.sh").read_text(encoding="utf-8")
    i = src.index("# SearxNG(일반 웹 검색 공급자) SIF")
    block = src[i:src.index('echo "→ uploading', i)]
    repo, stage = tmp_path / "repo", tmp_path / "stage"
    (repo / "infra/apptainer").mkdir(parents=True)
    stage.mkdir()
    for n in ("portal.sif", "nginx.sif"):
        (stage / n).write_text(n)

    def run() -> subprocess.CompletedProcess:
        script = "\n".join(["set -euo pipefail", f"REPO_ROOT='{repo}'", f"APPT_DIR='{repo}/infra/apptainer'", f"STAGE='{stage}'",
                            f"HOME='{tmp_path}'", block, "echo DONE"])
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                              env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    r = run()
    assert r.returncode == 0 and "DONE" in r.stdout and not (stage / "gatus.sif").exists(), r.stdout + r.stderr
    assert "gatus.sif" not in (stage / "SHA256SUMS").read_text(), "없으면 싣지 않는다"
    (repo / "infra/apptainer/gatus.sif").write_text("gatus-image")
    r = run()
    assert r.returncode == 0 and "included gatus.sif" in r.stdout, r.stdout + r.stderr
    assert (stage / "gatus.sif").read_text() == "gatus-image" and "  gatus.sif" in (stage / "SHA256SUMS").read_text()


def test_stop_은_인자에_gatus_가_들었을_뿐인_리스너는_건드리지_않는다(lay):
    """`*gatus*` 로 맞추면 인자 어딘가에 gatus 가 든 남의 프로세스도 죽였다(호출 추적 반대 검토 LOW-6 과 같은 꼴)."""
    port = _free_port()
    lay.infra_env(f"STATUS_BOARD_PORT={port}\n")
    other = _listener(port, "--directory", "/tmp/gatus-notes", "/gatus.yaml")
    try:
        r = _launch(lay, "stop")
        assert r.returncode == 1 and "상태판(gatus)이 아니다" in r.stderr and other.poll() is None, r.stdout + r.stderr
    finally:
        other.kill()
        other.wait(10)


def test_5b_꺼진_박스는_200_이_아니면_내리지_않는다(box):
    out = box.run("", STUB_EN="1", STUB_HTTP="404")
    assert box.called() == ["services.sh enabled status-board"], box.called()
    assert not _tag(out, "BAD:"), out
