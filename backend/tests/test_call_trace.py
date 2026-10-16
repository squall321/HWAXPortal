# 호출 추적(Phoenix) — 이미지 굽기 · 띄우는 스크립트 · gRPC 수신기를 끄는 셈 · 매니페스트 항목 · 상태판 · Drive 운반을 실물 스크립트로 시험한다
"""왜 — 호출 추적은 기본 꺼짐이고(infra/.env 의 CALL_TRACE 한 줄), 켜면 인증 없는 화면·수신이 하나의 루프백 포트에만 떠야 한다
(docs/improvement-1015/call-trace.md · IM-D6 ③). Phoenix 의 gRPC 수신기는 PHOENIX_HOST 를 보지 않고 모든 인터페이스에 열리므로 띄우는 셈이
끄고, 판이 바뀌어 끌 자리가 없으면 띄우지 않는다. cae00 은 인터넷이 없어 dev 가 구운 이미지를 Drive 로 받는다.

⚠ 실물을 건드리지 않는다. 스크립트는 임시 포털 리포에 복사해 절대경로로 돌리고, apptainer 는 받은 인자만 적는 대역이다(셈이 정말 쓰이는지
APPTAINER 로 넘겨 확인한다). 리스너 시험은 이 시험이 빈 포트에 띄운 파이썬 프로세스만 내린다. 가짜 phoenix 꾸러미로 띄우는 셈을 돌린다.
"""
import importlib.util
import os
import shutil
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/scripts"
SERVE = ROOT / "infra/call-trace/phoenix_serve.py"
MANIFEST = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stub(tmp: Path, body: str) -> Path:
    p = tmp / "apptainer"
    p.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    p.chmod(0o755)
    return p


@pytest.fixture
def repo(tmp_path):
    """임시 포털 리포 — 띄우는 스크립트·굽는 스크립트·띄우는 셈의 사본."""
    r = (tmp_path / "HWAXPortal").resolve()
    (r / "infra/scripts").mkdir(parents=True)
    (r / "infra/apptainer").mkdir()
    (r / "infra/call-trace").mkdir()
    for n in ("call-trace.sh", "build-phoenix.sh"):
        shutil.copy(SCRIPTS / n, r / "infra/scripts" / n)
    shutil.copy(SERVE, r / "infra/call-trace/phoenix_serve.py")
    return r


# ── 굽기 ──────────────────────────────────────────────────────────────────────────────────────────
def _build(repo: Path, label: str) -> tuple[subprocess.CompletedProcess, Path]:
    log = repo.parent / "pull.log"
    stub = _stub(repo.parent, 'case "$1" in\n'
                              '  pull) echo "$*" >> "$STUB_LOG"; printf sif > "$3" ;;\n'
                              '  inspect) echo "org.opencontainers.image.version: $STUB_LABEL" ;;\n'
                              'esac\n')
    r = subprocess.run(["bash", str(repo / "infra/scripts/build-phoenix.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(repo.parent), "APPTAINER": str(stub),
                            "STUB_LOG": str(log), "STUB_LABEL": label})
    return r, log


def test_굽기는_다이제스트로_받고_판_라벨이_다르면_내려놓지_않는다(repo):
    src = (SCRIPTS / "build-phoenix.sh").read_text(encoding="utf-8")
    assert 'PHOENIX_VERSION="20.19.0"' in src
    digest = 'sha256:d240d8d4e364ee3483ed2de41ec12b760cc90bb0d4c6e2f190388772aba6fe1f'
    assert f'PHOENIX_DIGEST="{digest}"' in src
    r, log = _build(repo, "arize-phoenix-v20.19.0")
    sif = repo / "infra/apptainer/phoenix.sif"
    assert r.returncode == 0 and sif.read_text() == "sif", r.stdout + r.stderr
    assert log.read_text().split()[:2] == ["pull", "--force"] and log.read_text().split()[-1] == f"docker://arizephoenix/phoenix@{digest}"
    assert not [p for p in sif.parent.iterdir() if p.name != "phoenix.sif"], "임시 파일이 남았다"
    sif.unlink()
    r, _ = _build(repo, "arize-phoenix-v20.20.0")
    assert r.returncode == 1 and "판이 'arize-phoenix-v20.20.0'" in r.stderr and not sif.exists(), r.stdout + r.stderr
    assert not list(sif.parent.iterdir()), "판이 틀리면 임시 파일도 남지 않는다"


# ── 띄우는 스크립트 ───────────────────────────────────────────────────────────────────────────────
def _launch(repo: Path, *args: str, env: dict | None = None) -> tuple[subprocess.CompletedProcess, Path]:
    out = repo.parent / "argv.txt"
    stub = _stub(repo.parent, 'printf "%s\\n" "$@" > "$STUB_OUT"\n')
    e = {"PATH": os.environ["PATH"], "HOME": str(repo.parent), "APPTAINER": str(stub), "STUB_OUT": str(out), **(env or {})}
    return subprocess.run(["bash", str(repo / "infra/scripts/call-trace.sh"), *args], capture_output=True, text=True,
                          env=e, timeout=60), out


def test_run_은_이미지가_없거나_손잡이가_틀리면_띄우지_않는다(repo):
    r, out = _launch(repo, "run")
    assert r.returncode == 1 and "이미지가 없다" in r.stderr and "images-from-drive" in r.stderr and "build-phoenix.sh" in r.stderr
    (repo / "infra/apptainer/phoenix.sif").write_text("")
    for line, rc, needle in (("CALL_TRACE_PORT=87x0\n", 2, "CALL_TRACE_PORT='87x0'"),
                             ("CALL_TRACE_PORT=70000\n", 2, "1~65535"),
                             ("CALL_TRACE_RETENTION_DAYS=-1\n", 2, "CALL_TRACE_RETENTION_DAYS='-1'"),
                             ("CALL_TRACE_RETENTION_DAYS=30d\n", 2, "날 수")):
        (repo / "infra/.env").write_text(line, encoding="utf-8")
        r, _ = _launch(repo, "run")
        assert r.returncode == rc and needle in r.stderr, (line, r.stderr)
    assert not out.exists(), "apptainer 를 부르지 않는다"


def test_run_은_루프백_한_포트로_환경을_비우고_홈_없이_띄우는_셈으로_띄운다(repo):
    (repo / "infra/apptainer/phoenix.sif").write_text("")
    (repo / "infra/.env").write_text("CALL_TRACE=1\nCALL_TRACE_PORT=18755\nCALL_TRACE_RETENTION_DAYS=14\n", encoding="utf-8")
    r, out = _launch(repo, "run", env={"CALL_TRACE_PORT": "9999", "SMTP_PASSWORD": "from-shell", "http_proxy": "http://proxy.test:3128"})
    assert r.returncode == 0, r.stderr
    assert "CALL_TRACE_PORT=9999 는 run 에서 쓰지 않는다" in r.stderr, "환경의 포트는 쓰지 않고 알린다"
    argv = out.read_text().splitlines()
    state = repo / "infra/.state/call-trace"
    assert argv[:7] == ["exec", "--cleanenv", "--no-home", "--bind", f"{state}:/state", "--bind", f"{repo}/infra/call-trace:/hwax:ro"], argv
    assert argv[-4:] == [str(repo / "infra/apptainer/phoenix.sif"), "/usr/bin/python3.13", "/hwax/phoenix_serve.py", "serve"], argv
    envs = [argv[i + 1] for i, a in enumerate(argv[:-4]) if a == "--env"]
    assert len(envs) * 2 == len(argv) - 11, f"--env 쌍 밖의 인자가 끼었다: {argv}"
    got = dict(e.split("=", 1) for e in envs)
    assert got == {"PHOENIX_HOST": "127.0.0.1", "PHOENIX_PORT": "18755", "PHOENIX_WORKING_DIR": "/state",
                   "PHOENIX_DEFAULT_RETENTION_POLICY_DAYS": "14", "PHOENIX_ALLOW_EXTERNAL_RESOURCES": "false",
                   "PHOENIX_TELEMETRY_ENABLED": "false", "PHOENIX_DISABLE_AGENT_ASSISTANT": "true",
                   "PHOENIX_AGENTS_DISABLE_BASH": "true", "PHOENIX_ENABLE_MCP_SERVER": "false",
                   "PHOENIX_ALLOWED_SANDBOX_PROVIDERS": "NONE", "PHOENIX_LOGGING_LEVEL": "warning",
                   "PHOENIX_LOG_MIGRATIONS": "false", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"}, got
    assert not any("from-shell" in a or "proxy.test" in a for a in argv), "띄운 셸의 값은 argv 로 넘기지 않는다"
    assert stat.S_IMODE(state.stat().st_mode) == 0o700
    ign = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "infra/.state/call-trace/phoenix.db"])
    assert ign.returncode == 0, "저장 자리가 gitignore 되지 않는다"
    (repo / "infra/.env").write_text("CALL_TRACE=1\n", encoding="utf-8")
    r, out = _launch(repo, "run")
    got = dict(a.split("=", 1) for a in out.read_text().splitlines() if a.startswith("PHOENIX_"))
    assert r.returncode == 0 and got["PHOENIX_PORT"] == "8750" and got["PHOENIX_DEFAULT_RETENTION_POLICY_DAYS"] == "30", got


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


def test_stop_은_그_포트를_듣는_phoenix_만_내린다(repo):
    port = _free_port()
    (repo / "infra/.env").write_text(f"CALL_TRACE_PORT={port}\n", encoding="utf-8")
    r, _ = _launch(repo, "stop")
    assert r.returncode == 0 and "이미 내려가 있다" in r.stdout, r.stdout + r.stderr
    other = _listener(port)
    try:
        r, _ = _launch(repo, "stop")
        assert r.returncode == 1 and "호출 추적(phoenix)이 아니다" in r.stderr and other.poll() is None, "남의 리스너는 건드리지 않는다"
    finally:
        other.kill()
        other.wait(10)
    mine = _listener(port, "/hwax/phoenix_serve.py", "serve")
    try:
        r, _ = _launch(repo, "stop")
        assert r.returncode == 0 and "내려갔다" in r.stdout and mine.wait(10) is not None, r.stdout + r.stderr
    finally:
        if mine.poll() is None:
            mine.kill()
    old = _listener(port, "/hwax/phoenix_serve.py", "serve")
    try:
        (repo / "infra/.env").write_text(f"CALL_TRACE_PORT={_free_port()}\n", encoding="utf-8")
        r, _ = _launch(repo, "stop", env={"CALL_TRACE_PORT": str(port)})
        assert r.returncode == 0 and f":{port}" in r.stdout and old.wait(10) is not None, r.stdout + r.stderr
    finally:
        if old.poll() is None:
            old.kill()


# ── 띄우는 셈(gRPC 수신기 끄기) ──────────────────────────────────────────────────────────────────
_FAKE_GRPC = '''
class GrpcServer:
    def __init__(self):
        self._server = None

    async def __aenter__(self):
        print("GRPC-LISTEN [::]:4317", flush=True)
        self._server = object()

    async def __aexit__(self, *a):
        if self._server is None:
            return
        print("GRPC-STOP", flush=True)
'''
_FAKE_MAIN = '''
import asyncio, json, sys
from phoenix.server.grpc_server import GrpcServer


def main():
    async def lifespan():
        g = GrpcServer()
        await g.__aenter__()
        await g.__aexit__(None, None, None)
    asyncio.run(lifespan())
    print("MAIN", json.dumps(sys.argv[1:]), flush=True)
'''


def _fake_phoenix(base: Path, *, grpc: bool = True) -> Path:
    pkg = base / "site"
    (pkg / "phoenix/server").mkdir(parents=True)
    (pkg / "phoenix/__init__.py").write_text("")
    (pkg / "phoenix/server/__init__.py").write_text("")
    if grpc:
        (pkg / "phoenix/server/grpc_server.py").write_text(_FAKE_GRPC)
    (pkg / "phoenix/server/main.py").write_text(_FAKE_MAIN)
    return pkg


def _serve(tmp: Path, pkg: Path) -> subprocess.CompletedProcess:
    cwd = tmp / "cwd"
    cwd.mkdir(exist_ok=True)
    # 이미지의 PYTHONPATH 처럼 끝이 ':' 다(띄운 자리가 import 경로에 든다) — 그 자리에 표준 모듈 이름의 덫을 둔다
    (cwd / "json.py").write_text("raise ImportError('띄운 자리의 json.py 가 표준 json 을 가렸다')\n")
    return subprocess.run([sys.executable, "-S", str(SERVE), "serve"], cwd=cwd, capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], "PYTHONPATH": f"{pkg}:", "PYTHONNOUSERSITE": "1"})


def test_띄우는_셈은_gRPC_수신기를_끄고_Phoenix_를_그대로_부른다(tmp_path):
    r = _serve(tmp_path, _fake_phoenix(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "GRPC-LISTEN" not in r.stdout and "GRPC-STOP" not in r.stdout, "모든 인터페이스의 수신기가 열렸다"
    assert 'MAIN ["serve"]' in r.stdout, r.stdout


def test_끌_자리가_없는_판이면_띄우지_않는다(tmp_path):
    r = _serve(tmp_path, _fake_phoenix(tmp_path, grpc=False))
    assert r.returncode == 3 and "gRPC 수신기 자리" in r.stderr and "MAIN" not in r.stdout, r.stdout + r.stderr


# ── 매니페스트 · 상태판 ───────────────────────────────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("svc_for_call_trace", SCRIPTS / "services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_매니페스트_항목은_CALL_TRACE_가_있는_박스에서만_다루고_이미지와_스크립트로_지문을_잡는다(tmp_path, monkeypatch):
    entry = MANIFEST["call-trace"]
    assert {k: entry[k] for k in ("dir", "if_env", "update", "fp_git", "fp", "start", "stop", "expect", "health", "tier")} == {
        "dir": ".", "if_env": "CALL_TRACE", "update": False, "fp_git": False,
        "fp": ["infra/apptainer/phoenix.sif", "infra/scripts/call-trace.sh", "infra/call-trace/phoenix_serve.py"],
        "start": "./infra/scripts/call-trace.sh run", "stop": "./infra/scripts/call-trace.sh stop", "expect": 200,
        "health": "http://127.0.0.1:${CALL_TRACE_PORT:-8750}/healthz", "tier": 5}
    assert entry["tier"] < MANIFEST["agent-server"]["tier"], "보내는 쪽(에이전트 서버)보다 먼저 뜬다"
    m = _services_mod()
    (tmp_path / "infra").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    monkeypatch.delenv("CALL_TRACE", raising=False)
    (tmp_path / "infra/.env").write_text("CALL_TRACE_PORT=18756\n", encoding="utf-8")
    assert m.enabled_here(entry) is False and "if_env=CALL_TRACE" in m.skip_reason(entry)
    assert m.health_url(entry) == "http://127.0.0.1:18756/healthz", "포트는 infra/.env 를 따른다(띄우는 스크립트와 같은 값)"
    (tmp_path / "infra/.env").write_text("CALL_TRACE=1\n", encoding="utf-8")
    assert m.enabled_here(entry) is True and m.health_url(entry) == "http://127.0.0.1:8750/healthz"
    (tmp_path / "infra/apptainer").mkdir()
    (tmp_path / "infra/apptainer/phoenix.sif").write_bytes(b"v1")
    f1 = m.service_fp(entry)
    (tmp_path / ".env").write_text("NEW_KEY=1\n")
    assert m.service_fp(entry) == f1, "포털 루트 .env 는 호출 추적 지문이 아니다"
    (tmp_path / "infra/apptainer/phoenix.sif").write_bytes(b"v2")
    assert m.service_fp(entry) != f1, "이미지를 갈아 끼우면 다시 띄운다"


def test_services_cli_는_파일의_CALL_TRACE_로만_켠다(tmp_path):
    """부팅 유닛과 같은 환경(env -i, infra/.env 파일만)에서 실제 매니페스트의 call-trace 항목을 묻는다."""
    lay = tmp_path / "HWAXPortal"
    (lay / "infra/scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS / "services.py", lay / "infra/scripts/services.py")
    shutil.copy(ROOT / "infra/services.yaml", lay / "infra/services.yaml")

    def run(env_text, *args):
        (lay / "infra/.env").write_text(env_text)
        return subprocess.run(["env", "-i", f"PATH={os.environ['PATH']}", sys.executable, str(lay / "infra/scripts/services.py"), *args],
                              capture_output=True, text=True, timeout=60)
    assert run("HWAX_BOX=x\n", "enabled", "call-trace").returncode == 1
    assert run("CALL_TRACE=1   # 켠다\n", "enabled", "call-trace").returncode == 0
    assert run("CALL_TRACE=1\nCALL_TRACE_PORT=18757\n", "health", "call-trace").stdout.strip() == "http://127.0.0.1:18757/healthz"


def test_상태판은_켠_박스에서_호출_추적의_healthz_를_200_으로_본다(tmp_path):
    from test_status_board import Lay  # noqa: PLC0415 — 상태판 시험의 임시 리포(생성기를 실제로 돌린다)
    lay = Lay(tmp_path)
    lay.manifest([MANIFEST["call-trace"]])
    lay.infra_env("CALL_TRACE=1\nCALL_TRACE_PORT=18758\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    assert lay.endpoints()["http://127.0.0.1:18758/healthz"]["conditions"] == ["[CONNECTED] == true", "[STATUS] == 200"]


# ── Drive 운반 ───────────────────────────────────────────────────────────────────────────────────
def test_이미지는_Drive_로_간다_올리고_받고_어긋남을_본다(tmp_path):
    src = (SCRIPTS / "images-to-drive.sh").read_text(encoding="utf-8")
    i = src.index("# SearxNG(일반 웹 검색 공급자) SIF")
    block = src[i:src.index('echo "→ uploading', i)]
    rp, stage = tmp_path / "repo", tmp_path / "stage"
    (rp / "infra/apptainer").mkdir(parents=True)
    stage.mkdir()
    for n in ("portal.sif", "nginx.sif"):
        (stage / n).write_text(n)

    def run() -> subprocess.CompletedProcess:
        script = "\n".join(["set -euo pipefail", f"REPO_ROOT='{rp}'", f"APPT_DIR='{rp}/infra/apptainer'", f"STAGE='{stage}'",
                            f"HOME='{tmp_path}'", block, "echo DONE"])
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                              env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    r = run()
    assert r.returncode == 0 and "DONE" in r.stdout and not (stage / "phoenix.sif").exists(), r.stdout + r.stderr
    (rp / "infra/apptainer/phoenix.sif").write_text("phoenix-image")
    r = run()
    assert r.returncode == 0 and "included phoenix.sif" in r.stdout, r.stdout + r.stderr
    assert (stage / "phoenix.sif").read_text() == "phoenix-image" and "  phoenix.sif" in (stage / "SHA256SUMS").read_text()
    down = (SCRIPTS / "images-from-drive.sh").read_text(encoding="utf-8")
    assert 'hwax_install_if_changed "$STAGE/phoenix.sif" "$APPT_DIR/phoenix.sif"' in down
    drift = (SCRIPTS / "drive-drift.sh").read_text(encoding="utf-8")
    loops = [ln.split(" in ", 1)[1].split(";")[0].split() for ln in drift.splitlines() if ln.strip().startswith("for _sif in ")]
    assert len(loops) == 1 and "phoenix" in loops[0], loops


# ── update-all 5c — 켜면 띄우고, 끄면 ○ 와 함께 떠 있는 것을 내리고, 두 줄이 어긋나면 알린다 ─────────────────────────────
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")


def _ua_region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


class _Box5c:
    """update-all 5c 를 원문 그대로 임시 포털에서 돌린다 — services.sh enabled · update-sites · call-trace.sh stop 은 부른 사실만 적는 대역이고
    http_code 도 대역이다(실 포트를 두드리지 않는다). AGENT_ENV 는 임시 에이전트 서버 .env 다(없으면 대조하지 않는 박스)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts/lib").mkdir(parents=True)
        (self.repo / "infra/apptainer").mkdir()
        shutil.copy(SCRIPTS / "lib/skip-ledger.sh", self.repo / "infra/scripts/lib/skip-ledger.sh")
        self.calls, self.ledger = self.tmp / "calls.log", self.tmp / "ledger"
        self.calls.write_text("")
        self.ledger.write_text("")
        self.agent_env = self.tmp / "agent.env"
        sh = {"services.sh": 'echo "services.sh $*" >> "{c}"; [ "$1" = enabled ] && exit "${{STUB_EN:-1}}"; exit 0',
              "update-sites.sh": 'echo "update-sites.sh $*" >> "{c}"; echo "  (대역) update-sites $*"; exit "${{STUB_US:-0}}"',
              "call-trace.sh": 'echo "call-trace.sh $*" >> "{c}"; echo "  (대역) call-trace $*"; exit "${{STUB_STOP:-0}}"'}
        for name, body in sh.items():
            p = self.repo / "infra/scripts" / name
            p.write_text("#!/usr/bin/env bash\n" + body.format(c=self.calls) + "\n", encoding="utf-8")
            p.chmod(0o755)

    def run(self, infra_env: str = "", *, sif: bool = True, agent_env: str | None = "", **env) -> str:
        (self.repo / "infra/.env").write_text(infra_env, encoding="utf-8")
        if sif:
            (self.repo / "infra/apptainer/phoenix.sif").write_text("")
        if agent_env is None:
            agent_line = "unset AGENT_ENV"
        else:
            self.agent_env.write_text(agent_env, encoding="utf-8")
            agent_line = f'AGENT_ENV="{self.agent_env}"'
        envfile = _ua_region("_envfile_value() {", "\n}\n") + "\n}\n"
        body = _ua_region("# ── 5c) 호출 추적(Phoenix)", "# ── 6) 헬스게이트")
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'SELF_REPO="{self.repo}"', f'SVC="{self.repo}/infra/scripts/services.sh"', agent_line,
            f'[ "$(cd "$SELF_REPO" && pwd)" = "{self.repo}" ] || exit 97',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            'http_code() { echo "${STUB_HTTP:-000}"; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"', f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"',
            envfile, body, "echo END",
        ])
        base = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env={**base, **env})
        assert r.returncode != 97 and "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def called(self) -> list[str]:
        return self.calls.read_text().splitlines()


@pytest.fixture()
def box5c(tmp_path):
    return _Box5c(tmp_path)


def _tagged(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


def test_5c_꺼져_있으면_안_켠_기능으로_남기고_아무것도_띄우지_않는다(box5c):
    out = box5c.run("OTHER=1\n", STUB_EN="1")
    assert box5c.called() == ["services.sh enabled call-trace"], box5c.called()
    assert not _tagged(out, "HR:") and not _tagged(out, "FAIL:") and not _tagged(out, "BAD:"), out
    led = box5c.ledger.read_text()
    assert led.startswith("호출 추적(Phoenix)\t") and "CALL_TRACE=1" in led and "CALL_TRACE_URL" in led and "call-trace.md" in led, led


def test_5c_꺼졌는데_Phoenix_가_떠_있으면_내린다(box5c):
    out = box5c.run("CALL_TRACE_PORT=18752\n", STUB_EN="1", STUB_HTTP="200")
    assert box5c.called() == ["services.sh enabled call-trace", "call-trace.sh stop"], box5c.called()
    assert any(":18752" in ln and "내렸다" in ln for ln in _tagged(out, "OK:")), out
    out = box5c.run("", STUB_EN="1", STUB_HTTP="200", STUB_STOP="1")
    assert any("내리지 못했다" in ln for ln in _tagged(out, "BAD:")) and not _tagged(out, "FAIL:"), out


def test_5c_꺼졌는데_보내는_쪽이_남아_있으면_알린다(box5c):
    out = box5c.run("", STUB_EN="1", agent_env="CALL_TRACE_URL=http://127.0.0.1:8750\n")
    assert any("CALL_TRACE_URL 이 남아 있다" in ln for ln in _tagged(out, "BAD:")), out
    assert box5c.agent_env.read_text() == "CALL_TRACE_URL=http://127.0.0.1:8750\n", "에이전트 서버 .env 는 고쳐 쓰지 않는다"
    assert box5c.ledger.read_text().startswith("호출 추적(Phoenix)\t"), "꺼짐은 그대로 ○ 다"


def test_5c_켜져_있으면_update_sites_로_띄우고_보내는_쪽이_있으면_조용하다(box5c):
    out = box5c.run("CALL_TRACE=1\n", STUB_EN="0", agent_env="CALL_TRACE_URL=http://127.0.0.1:8750\n")
    assert box5c.called() == ["services.sh enabled call-trace", "update-sites.sh call-trace"], box5c.called()
    assert _tagged(out, "HR:5c)") and any("http://127.0.0.1:8750" in ln for ln in _tagged(out, "OK:")), out
    assert not _tagged(out, "FAIL:") and not _tagged(out, "BAD:") and not box5c.ledger.read_text(), out


def test_5c_받는_쪽만_켜졌으면_보내는_줄을_알린다(box5c):
    out = box5c.run("CALL_TRACE=1\nCALL_TRACE_PORT=18753\n", STUB_EN="0", agent_env="VLLM_MODEL=x\n")
    assert any("받는 쪽(Phoenix)만 켜졌다" in ln and "CALL_TRACE_URL=http://127.0.0.1:18753" in ln for ln in _tagged(out, "BAD:")), out
    assert box5c.agent_env.read_text() == "VLLM_MODEL=x\n", "에이전트 서버 .env 는 고쳐 쓰지 않는다"


def test_5c_에이전트_서버_env_를_모르면_대조하지_않는다(box5c):
    out = box5c.run("CALL_TRACE=1\n", STUB_EN="0", agent_env=None)
    assert not _tagged(out, "BAD:"), out
    out = box5c.run("", STUB_EN="1", agent_env=None)
    assert not _tagged(out, "BAD:"), out


def test_5c_이미지가_없으면_기다리지_않고_실패로_센다(box5c):
    out = box5c.run("CALL_TRACE=1\n", sif=False, STUB_EN="0", agent_env="CALL_TRACE_URL=http://127.0.0.1:8750\n")
    assert "update-sites.sh call-trace" not in box5c.called(), "health 를 기다리지 않는다"
    assert any("이미지가 없다" in ln and "build-phoenix.sh" in ln for ln in _tagged(out, "FAIL:")), out


def test_5c_띄우지_못하면_실패로_센다(box5c):
    out = box5c.run("CALL_TRACE=1\n", STUB_EN="0", STUB_US="1", agent_env="CALL_TRACE_URL=http://127.0.0.1:8750\n")
    assert any("띄우지 못했다" in ln and "rc 1" in ln for ln in _tagged(out, "FAIL:")), out


def test_5c_CALL_TRACE_0_은_켜짐이라고_알린다(box5c):
    out = box5c.run("CALL_TRACE=0\n", STUB_EN="0", agent_env="CALL_TRACE_URL=http://127.0.0.1:8750\n")
    assert any("켜짐으로 읽힌다" in ln for ln in _tagged(out, "BAD:")), out


def test_5c_update_all_배선():
    i5b, i5c, i6 = UA.index("# ── 5b) 상시 상태판(Gatus)"), UA.index("# ── 5c) 호출 추적(Phoenix)"), UA.index('hr "6) 헬스게이트"')
    assert i5b < i5c < i6, "5c 는 5b 뒤 · §6 앞이다"
    head = UA[:UA.index("set -uo pipefail")]
    assert "5c) 호출 추적" in head and "CALL_TRACE" in head, "사용법의 순서 목록에 있다"
    for line in _ua_region("# ── 5c) 호출 추적(Phoenix)", "# ── 6) 헬스게이트").splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"


def test_물려받은_호출_추적_포트를_버린다():
    """call-trace.sh stop 은 환경의 CALL_TRACE_PORT 를 먼저 본다 — 운영자 셸에 export 된 옛 포트가 update-sites → services.py down 으로 흘러
    지금 Phoenix 대신 옛 포트를 내리지 않게 update-all·update-sites 머리가 버린다(상태판 · LLM 라우터와 같다)."""
    us = (SCRIPTS / "update-sites.sh").read_text(encoding="utf-8")
    heads = (UA[:UA.index('SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"')],
             us[:us.index('ROOT="$(cd "$(dirname "$0")/../.." && pwd)"')])
    for head in heads:
        r = subprocess.run(["bash", "-c", head + '\necho "[${CALL_TRACE_PORT-없음}]"\n'], capture_output=True, text=True, timeout=30,
                           env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "CALL_TRACE_PORT": "9555"})
        assert r.stdout.split()[-1:] == ["[없음]"], r.stdout + r.stderr


# ── 반대 검토(10-16) 뒤 — 정지 판정 · 상태 디렉터리 잠금 · 보내는 줄 대조 ──────────────────────────────────────────────
def test_stop_은_인자에_phoenix_가_들었을_뿐인_리스너는_건드리지_않는다(repo):
    """`*phoenix*` 로 맞추면 인자 어딘가에 phoenix 가 든 남의 프로세스를 죽였다(반대 검토 LOW-6 — http.server --directory …/phoenix-notes)."""
    port = _free_port()
    (repo / "infra/.env").write_text(f"CALL_TRACE_PORT={port}\n", encoding="utf-8")
    other = _listener(port, "--directory", "/tmp/phoenix-notes", "phoenix_serve.py.bak")
    try:
        r, _ = _launch(repo, "stop")
        assert r.returncode == 1 and "호출 추적(phoenix)이 아니다" in r.stderr and other.poll() is None, r.stdout + r.stderr
    finally:
        other.kill()
        other.wait(10)


def test_run_은_상태_디렉터리를_다른_Phoenix_가_쓰면_띄우지_않는다(repo):
    """포트를 바꾸고 옛 것을 안 내리면 둘째 Phoenix 가 같은 SQLite 를 쓴다(반대 검토 LOW-5) — 잠금이 쥐어져 있으면 apptainer 를 부르지 않는다."""
    import fcntl
    (repo / "infra/apptainer/phoenix.sif").write_text("")
    state = repo / "infra/.state/call-trace"
    state.mkdir(parents=True)
    with open(state / ".lock", "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r, argv_file = _launch(repo, "run")
        assert r.returncode == 1 and "다른 Phoenix 가 이 상태 디렉터리" in r.stderr and "call-trace.sh stop" in r.stderr, r.stdout + r.stderr
        assert not argv_file.exists() or not argv_file.read_text().strip(), "apptainer 를 부르지 않는다"
    r, argv_file = _launch(repo, "run")
    assert r.returncode == 0 and argv_file.read_text().strip(), "잠금이 풀리면 띄운다"


def test_5c_꺼진_박스는_200_이_아니면_내리지_않는다(box5c):
    out = box5c.run("", STUB_EN="1", STUB_HTTP="404")
    assert box5c.called() == ["services.sh enabled call-trace"], box5c.called()
    assert not _tagged(out, "BAD:"), out


@pytest.mark.parametrize("line,ok", [
    ("CALL_TRACE_URL=http://127.0.0.1:8750\n", True),
    ('CALL_TRACE_URL="http://127.0.0.1:8750"\n', True),
    ("CALL_TRACE_URL=http://localhost:8750/\n", True),
    ("export CALL_TRACE_URL=http://127.0.0.1:8750/v1/traces\n", True),
    ("CALL_TRACE_URL=http://127.0.0.1:8752\n", False),
    ("CALL_TRACE_URL=http://127.0.0.1:8750   # 설명\n", False),
    ("CALL_TRACE_URL=127.0.0.1:8750\n", False),
])
def test_5c_보내는_줄이_받는_쪽과_맞지_않으면_알린다(box5c, line, ok):
    """있기만 하고 다르면 기록이 조용히 버려진다 — 다른 포트 · 줄 끝 설명(에이전트 서버는 설명을 떼지 않아 주소로 못 읽고 꺼진다) · 스킴 없음."""
    out = box5c.run("CALL_TRACE=1\n", STUB_EN="0", agent_env=line)
    bads = [ln for ln in _tagged(out, "BAD:") if "맞지 않는다" in ln]
    assert (not bads) == ok, out
    assert box5c.agent_env.read_text() == line, "에이전트 서버 .env 는 고쳐 쓰지 않는다"


def test_5c_켜려면의_포트는_설정된_포트다(box5c):
    box5c.run("CALL_TRACE_PORT=18755\n", STUB_EN="1")
    assert "CALL_TRACE_URL=http://127.0.0.1:18755" in box5c.ledger.read_text(), box5c.ledger.read_text()
