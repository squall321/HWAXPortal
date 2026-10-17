# 상시 상태판 2단계 — 스크립트 검사(외부 끝점 · 밀어 넣는 쪽) · 기록 보존 · update-all 동안 경보 멈춤이 계약대로 도는가
"""docs/improvement-1015/status-board.md '2단계' · 결정 context-notes IM-D24~IM-D29.

  · 생성기 — 돌 수 있는 검사만 외부 끝점으로 싣고(heartbeat · 경보 문턱 2) push.json(600)에 토큰을 쓴다. 토큰은 다시 쓴다(같은 내용이면
    다시 쓰지 않는다를 지킨다). 기록은 sqlite.
  · 멈춤 — --pause 는 maintenance 칸만 넣고(UTC · 영어 요일), --unpause 는 글자까지 일반 생성과 같게 되돌린다. 시한이 지난 것만
    --unpause-if-expired 가 걷는다. 일반 생성은 늘 푼다(손잡이가 틀려 못 만들어도).
  · 밀어 넣는 쪽 — 가짜 스모크 · 가짜 rclone · 가짜 Gatus 로 판정과 밀어 넣기(쿼리 · 토큰 · 프록시를 안 탄다 · 401 은 다시 안 함),
    loop 의 수명(부모가 사라지면 · TERM 이면 끝, 시한 지난 멈춤을 걷는다).
  · 띄우는 스크립트 — 밀어 넣는 쪽을 부모 pid 와 함께 띄우고 Gatus 가 끝나면 TERM 으로 내린다.
  · 스모크 — 주기 판 허용 목록.
  · update-all — 1b2 가 걸고 5b · § 머리 정지 · 완주 끝이 푼다.
실 Gatus · 실 Drive · 실 게이트웨이는 두드리지 않는다(Gatus 동작은 2026-10-17 dev 에서 v5.37.0 으로 따로 쟀다 — IM-D25).
"""
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "infra" / "scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
SMTP = ("MAIL_BACKEND=smtp\nMAIL_FROM=sender@mail.test\nSMTP_HOST=smtp.mail.test\nSMTP_PORT=2525\n"
        "SMTP_USERNAME=robot\nSMTP_PASSWORD=pw\nSMTP_STARTTLS=true\n")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeGatus:
    """외부 끝점 밀어 넣기만 받는 가짜 — (경로, 쿼리, Authorization) 를 적고 code 로 답한다."""

    def __init__(self):
        self.got: list[tuple[str, dict, str | None]] = []
        self.code = 200
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                u = urlsplit(self.path)
                outer.got.append((u.path, {k: v[0] for k, v in parse_qs(u.query).items()}, self.headers.get("Authorization")))
                self.send_response(outer.code)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture()
def gatus():
    g = FakeGatus()
    yield g
    g.close()


FAKE_RCLONE = r'''#!/usr/bin/env python3
import json, os, sys
fx = json.load(open(os.environ["FAKE_RCLONE"]))
with open(os.environ["FAKE_RCLONE"] + ".calls", "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
if fx.get("fail"):
    sys.stderr.write("Failed to create file system: couldn't connect\n")
    sys.exit(1)
target = sys.argv[-1].rstrip("/")
if sys.argv[1] == "lsf":
    print("\n".join(d + "/" for d in fx["dirs"].get(target, [])))
elif sys.argv[1] == "lsjson":
    print(json.dumps(fx["files"].get(target, [])))
else:
    sys.exit(2)
'''

FAKE_SMOKE = r'''#!/usr/bin/env bash
printf '%s\n' "$@" > "$FAKE_SMOKE_DIR/args"
printf '%s\n' "${NO_PROXY:-}" > "$FAKE_SMOKE_DIR/no_proxy"
[ -n "${FAKE_SMOKE_SLEEP:-}" ] && sleep "$FAKE_SMOKE_SLEEP"
cat "$FAKE_SMOKE_DIR/out.json" 2>/dev/null
cat "$FAKE_SMOKE_DIR/err.txt" >&2 2>/dev/null
exit "$(cat "$FAKE_SMOKE_DIR/rc" 2>/dev/null || echo 0)"
'''


class Lay:
    """임시 포털 리포 + 형제 에이전트 서버(가짜 venv python = 가짜 스모크) + PATH 앞의 가짜 rclone."""

    def __init__(self, tmp: Path, gatus_port: int):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts").mkdir(parents=True)
        (self.repo / "infra/apptainer").mkdir()
        (self.repo / "backend/.venv/bin").mkdir(parents=True)
        os.symlink(sys.executable, self.repo / "backend/.venv/bin/python")      # 생성기(yaml)를 부르는 venv — 밀어 넣는 쪽의 걷어내기가 쓴다
        for n in ("services.py", "gen-status-config.py", "status-board.sh", "status-push.py", "mcp-smoke.py"):
            shutil.copy(SCRIPTS / n, self.repo / "infra/scripts" / n)
        self.state = self.repo / "infra/.state/status"
        self.out = self.state / "config.yaml"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "rclone").write_text(FAKE_RCLONE, encoding="utf-8")
        (self.bin / "rclone").chmod(0o755)
        self.smoke_dir = self.tmp / "smoke"
        self.smoke_dir.mkdir()
        self.smoke_py = self.tmp / "HWAXAgentServer/.venv/bin/python"
        self.smoke_py.parent.mkdir(parents=True)
        self.smoke_py.write_text(FAKE_SMOKE, encoding="utf-8")
        self.smoke_py.chmod(0o755)
        self.rclone_fx = self.tmp / "rclone.json"
        self.drive({"dirs": {}, "files": {}})
        self.manifest(["portal", "mcp-gateway"])
        self.infra_env(f"STATUS_BOARD_PORT={gatus_port}\nHWAX_DRIVE_REMOTE=fake:HWAXPortal\n")

    def manifest(self, names: list[str]) -> None:
        svcs = [{"name": n, "host": "local", "dir": ".", "start": "true", "health": f"http://127.0.0.1:{_free_port()}/health",
                 "tier": 10} for n in names]
        (self.repo / "infra/services.yaml").write_text(yaml.safe_dump({"services": svcs}), encoding="utf-8")

    def infra_env(self, text: str) -> None:
        (self.repo / "infra/.env").write_text(text, encoding="utf-8")

    def drive(self, fx: dict) -> None:
        self.rclone_fx.write_text(json.dumps(fx), encoding="utf-8")

    def smoke(self, out: dict | str | None, rc: int = 0, err: str = "") -> None:
        (self.smoke_dir / "out.json").write_text(out if isinstance(out, str) else json.dumps(out or {}), encoding="utf-8")
        (self.smoke_dir / "rc").write_text(str(rc))
        (self.smoke_dir / "err.txt").write_text(err, encoding="utf-8")

    def env(self, **kw) -> dict:
        return {"PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.tmp), "LANG": "C.UTF-8",
                "FAKE_RCLONE": str(self.rclone_fx), "FAKE_SMOKE_DIR": str(self.smoke_dir), **kw}

    def gen(self, *args: str, **env) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(self.repo / "infra/scripts/gen-status-config.py"), *args],
                              capture_output=True, text=True, timeout=60, env=self.env(**env))

    def push_cmd(self, *args: str, **env) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(self.repo / "infra/scripts/status-push.py"), *args],
                              capture_output=True, text=True, timeout=90, env=self.env(**env))

    def doc(self) -> dict:
        return yaml.safe_load(self.out.read_text(encoding="utf-8"))

    def push_json(self) -> dict:
        return json.loads((self.state / "push.json").read_text(encoding="utf-8"))

    def module(self, name: str):
        spec = importlib.util.spec_from_file_location(f"{name.replace('-', '_')}_{id(self)}", self.repo / "infra/scripts" / f"{name}.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m


@pytest.fixture()
def lay(tmp_path, gatus):
    return Lay(tmp_path, gatus.port)


# ── 생성기 — 외부 끝점 · push.json · 기록 보존 ─────────────────────────────────────────────────────────────
def test_생성기는_돌_수_있는_검사만_외부_끝점으로_싣고_push_json_에_토큰을_600_으로_쓴다(lay):
    lay.infra_env(lay.repo.joinpath("infra/.env").read_text() + "STATUS_ALERT_TO=team@mail.test\n")
    (lay.repo / "backend/.env").write_text(SMTP, encoding="utf-8")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    doc = lay.doc()
    assert doc["storage"] == {"type": "sqlite", "path": "/data/gatus.db"}, "기록은 sqlite — 다시 읽기·재기동에 경보 상태가 남는다"
    ext = {e["name"]: e for e in doc["external-endpoints"]}
    assert sorted(ext) == ["drive-latest", "mcp-smoke"] and {e["group"] for e in ext.values()} == {"checks"}
    assert ext["mcp-smoke"]["heartbeat"] == {"interval": "45m"} and ext["drive-latest"]["heartbeat"] == {"interval": "70m"}
    for e in ext.values():
        a = e["alerts"][0]
        assert a["type"] == "email" and a["failure-threshold"] == 2 and a["success-threshold"] == 1
        assert "status-push.py once" in a["description"], "메일 본문에는 밀어 넣은 사유가 없다 — 설명이 사유를 보는 곳을 말한다"
    push = lay.push_json()
    assert oct((lay.state / "push.json").stat().st_mode & 0o777) == "0o600"
    assert push["url"] == f"http://127.0.0.1:{doc['web']['port']}" and push["token"] == ext["mcp-smoke"]["token"] == ext["drive-latest"]["token"]
    kinds = {c["kind"]: c for c in push["checks"]}
    assert kinds["mcp-smoke"]["key"] == "checks_mcp-smoke" and kinds["mcp-smoke"]["python"] == str(lay.smoke_py)
    assert kinds["drive-latest"]["key"] == "checks_drive-latest"
    assert kinds["drive-latest"]["remotes"] == [{"label": "포털", "remote": "fake:HWAXPortal", "prefix": "images-"}]
    assert push["token"] not in r.stdout + r.stderr, "토큰을 찍지 않는다"
    assert "스크립트 검사 MCP 실호출(30분마다" in r.stdout and "Drive latest/(60분마다 · 리모트 1곳: 포털)" in r.stdout, r.stdout
    tok, m0 = push["token"], lay.out.stat().st_mtime_ns
    r = lay.gen()
    assert r.returncode == 0 and "설정 그대로" in r.stdout and lay.out.stat().st_mtime_ns == m0, "토큰을 다시 쓴다 — 매번 바뀌면 매 update-all 에 다시 뜬다"
    assert lay.push_json()["token"] == tok


def test_돌_수_없는_검사는_싣지_않고_까닭을_말한다(lay, tmp_path):
    shutil.rmtree(lay.tmp / "HWAXAgentServer")
    lay.infra_env("STATUS_BOARD_PORT=18790\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external-endpoints" not in lay.doc() and lay.push_json()["checks"] == []
    assert "스크립트 검사 안 함: MCP 실호출(mcp 모듈이 있는 에이전트 서버 venv 를 못 찾았다" in r.stdout, r.stdout
    assert "Drive latest/(Drive 리모트가 하나도 없다" in r.stdout, r.stdout
    lay.manifest(["portal"])
    lay.infra_env("STATUS_BOARD_PORT=18790\nHWAX_DRIVE_REMOTE=fake:HWAXPortal\n")
    empty = tmp_path / "nobin"
    empty.mkdir()
    r = lay.gen(PATH=str(empty))
    assert "MCP 실호출(게이트웨이가 이 박스 대상이 아니다)" in r.stdout and "Drive latest/(rclone 이 없다)" in r.stdout, r.stdout


def test_HEAXHub_KooRemapper_리모트는_그_리포의_env_에서_읽는다(lay):
    (lay.tmp / "HEAXHub").mkdir()
    (lay.tmp / "HEAXHub/.env").write_text("HEAX_DRIVE_REMOTE='fake:HEAXHub/dist/'\n", encoding="utf-8")
    (lay.tmp / "KooRemapper/platform").mkdir(parents=True)
    (lay.tmp / "KooRemapper/platform/.env").write_text("KOORM_DRIVE_REMOTE=old\nKOORM_DRIVE_REMOTE=fake:KooRemapper/dist\n", encoding="utf-8")
    assert lay.gen().returncode == 0
    rem = next(c for c in lay.push_json()["checks"] if c["kind"] == "drive-latest")["remotes"]
    assert rem == [{"label": "포털", "remote": "fake:HWAXPortal", "prefix": "images-"},
                   {"label": "HEAXHub", "remote": "fake:HEAXHub/dist", "prefix": "dist-"},
                   {"label": "KooRemapper", "remote": "fake:KooRemapper/dist", "prefix": "dist-"}], "drive-drift 의 env_get 과 같은 규칙(마지막 줄 · 따옴표)"


# ── 생성기 — 경보 멈춤 ─────────────────────────────────────────────────────────────────────────────────
def test_멈춤은_maintenance_칸만_넣고_로캘이_한국어여도_요일은_영어다_풀면_글자까지_같다(lay):
    lay.infra_env(lay.repo.joinpath("infra/.env").read_text() + "STATUS_ALERT_TO=team@mail.test\n")
    (lay.repo / "backend/.env").write_text(SMTP.replace("SMTP_PASSWORD=pw", "SMTP_PASSWORD='p$w$$d'"), encoding="utf-8")
    assert lay.gen().returncode == 0
    before = lay.out.read_text(encoding="utf-8")
    assert "p$$w$$$$d" in before
    t0 = int(time.time())
    r = lay.gen("--pause", "60", LANG="ko_KR.UTF-8", LC_ALL="ko_KR.UTF-8")
    assert r.returncode == 0 and "✓ 경보를 멈췄다 — 60분" in r.stdout, r.stdout + r.stderr
    m = lay.doc()["maintenance"]
    start = t0 - t0 % 60
    assert m["timezone"] == "UTC" and m["every"] in ([WEEKDAYS[time.gmtime(start).tm_wday]], [WEEKDAYS[time.gmtime(start + 60).tm_wday]])
    assert m["every"][0] in WEEKDAYS, "로캘 요일('토요일')이면 Gatus 가 설정을 거부한다"
    assert m["duration"] in ("60m", "61m") and len(m["start"]) == 5 and m["start"][2] == ":"
    rec = json.loads((lay.state / "pause.json").read_text())
    assert abs(rec["until"] - (t0 + 3600)) <= 5 and oct((lay.state / "pause.json").stat().st_mode & 0o777) == "0o600"
    assert lay.doc()["alerting"]["email"]["password"] == "p$$w$$$$d", "걸기는 읽은 문서를 다시 적는다 — `$` 를 또 겹쳐 적지 않는다"
    r = lay.gen("--unpause")
    assert r.returncode == 0 and "✓ 경보 멈춤을 풀었다" in r.stdout
    assert lay.out.read_text(encoding="utf-8") == before, "푼 설정은 일반 생성과 글자까지 같다 — 지문이 그대로라 update-sites 가 다시 띄우지 않는다"
    assert not (lay.state / "pause.json").exists()
    assert "걸려 있지 않다" in lay.gen("--unpause").stdout


def test_시한이_지난_멈춤만_걷어낸다(lay):
    assert lay.gen().returncode == 0
    assert lay.gen("--pause", "30").returncode == 0
    r = lay.gen("--unpause-if-expired")
    assert r.returncode == 0 and r.stdout == "" and "maintenance" in lay.doc(), "시한 안이면 조용히 둔다"
    rec = json.loads((lay.state / "pause.json").read_text())
    (lay.state / "pause.json").write_text(json.dumps({**rec, "until": time.time() - 1}))
    r = lay.gen("--unpause-if-expired")
    assert r.returncode == 0 and "시한이 지났다" in r.stdout and "maintenance" not in lay.doc() and not (lay.state / "pause.json").exists()
    assert lay.gen("--pause", "30").returncode == 0
    (lay.state / "pause.json").unlink()                         # 시한 기록 없이 창만 남았다
    assert "시한이 지났다" in lay.gen("--unpause-if-expired").stdout and "maintenance" not in lay.doc()


def test_일반_생성은_멈춤을_늘_풀고_손잡이가_틀려_못_만들어도_푼다(lay):
    assert lay.gen().returncode == 0
    before = lay.out.read_text(encoding="utf-8")
    assert lay.gen("--pause", "60").returncode == 0
    r = lay.gen()
    assert r.returncode == 0 and "✓ 경보 멈춤을 풀었다" in r.stdout and "maintenance" not in lay.doc(), r.stdout
    assert lay.out.read_text(encoding="utf-8") == before and not (lay.state / "pause.json").exists()
    assert lay.gen("--pause", "60").returncode == 0
    port = lay.doc()["web"]["port"]
    lay.infra_env("STATUS_BOARD_PORT=abc\n")
    r = lay.gen()
    assert r.returncode == 2 and "maintenance" not in lay.doc() and lay.doc()["web"]["port"] == port, r.stdout
    assert lay.out.read_text(encoding="utf-8") == before, "옛 설정은 그대로 돌고 멈춤만 걷혔다"


def test_멈출_설정이_없거나_범위_밖이면(lay):
    r = lay.gen("--pause", "60")
    assert r.returncode == 0 and "멈출 경보가 없다" in r.stdout and not lay.out.exists()
    assert lay.gen().returncode == 0
    for bad in ("0", "241"):
        r = lay.gen("--pause", bad)
        assert r.returncode == 2 and "maintenance" not in lay.doc(), r.stdout


# ── 밀어 넣는 쪽 — 판정 ───────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("out,rc,err,ok,needle", [
    ({"backends": {"a": {"ok": 1, "probed": ["x"]}, "ste": {"unprobed": True}}, "dead": [], "drift": {}}, 0, "", True,
     "백엔드 1곳 호출 성공 · 검사 못 함 1곳"),
    ({"backends": {"ra": {"ok": 0, "probed": ["x"], "why": "토큰이 유효하지 않거나 만료되었습니다"}}, "dead": ["ra"], "drift": {}}, 1, "", False,
     "호출 0성공 — ra: 토큰이 유효하지 않거나 만료되었습니다"),
    ({"backends": {"dyna": {"ok": 1, "probed": ["x"]}}, "dead": [], "drift": {"dyna": {"app": 36, "gateway": 22}}}, 3, "", False,
     "배포본이 코드보다 오래됐다 — dyna(앱 36 · 게이트웨이 22)"),
    ("", 2, "✗ 게이트웨이(http://127.0.0.1:9110/mcp)에 붙지 못함: ConnectError\n", False, "판정 못 함 — ✗ 게이트웨이"),
    ("not json", 0, "", False, "스모크 출력을 읽지 못했다(rc 0)"),
])
def test_스모크_결과를_판정한다(lay, monkeypatch, out, rc, err, ok, needle):
    monkeypatch.setenv("FAKE_SMOKE_DIR", str(lay.smoke_dir))
    lay.smoke(out, rc, err)
    m = lay.module("status-push")
    got = m.check_mcp_smoke({"python": str(lay.smoke_py), "timeout_s": 30})
    assert got[0] is ok and needle in got[1], got


def test_스모크는_주기_판으로_부르고_루프백은_프록시를_비키게_한다(lay, monkeypatch):
    monkeypatch.setenv("FAKE_SMOKE_DIR", str(lay.smoke_dir))
    monkeypatch.setenv("NO_PROXY", "corp.example")
    lay.smoke({"backends": {}, "dead": [], "drift": {}})
    m = lay.module("status-push")
    assert m.check_mcp_smoke({"python": str(lay.smoke_py), "timeout_s": 30})[0]
    assert (lay.smoke_dir / "args").read_text().split() == [str(lay.repo / "infra/scripts/mcp-smoke.py"), "--periodic", "--json"]
    assert (lay.smoke_dir / "no_proxy").read_text().strip() == "corp.example,127.0.0.1,localhost"
    assert m.check_mcp_smoke({"python": str(lay.tmp / "nope"), "timeout_s": 30}) [1].startswith("mcp 모듈이 있는 python 이 없다")


def test_스모크가_끝나지_않으면_시간_초과로_묶음째_내린다(lay, monkeypatch):
    monkeypatch.setenv("FAKE_SMOKE_DIR", str(lay.smoke_dir))
    monkeypatch.setenv("FAKE_SMOKE_SLEEP", "30")
    lay.smoke({"backends": {}, "dead": [], "drift": {}})
    m = lay.module("status-push")
    t0 = time.monotonic()
    ok, why = m.check_mcp_smoke({"python": str(lay.smoke_py), "timeout_s": 1})
    assert not ok and why.startswith("시간 초과(1초)") and time.monotonic() - t0 < 10, why


def _files(**md5: str) -> list[dict]:
    return [{"Name": n, "Size": 10, "Hashes": {"md5": h}} for n, h in md5.items()]


@pytest.mark.parametrize("fx,ok,needle", [
    ({"dirs": {"fake:P": ["images-20261016-0100Z", "images-20261017-0200Z", "latest"]},
      "files": {"fake:P/images-20261017-0200Z": _files(**{"portal.sif": "aa", "SHA256SUMS": "bb"}),
                "fake:P/latest": _files(**{"portal.sif": "aa", "SHA256SUMS": "bb", "old.sif": "cc"})}}, True, "리모트 1곳"),
    ({"dirs": {"fake:P": ["images-20261016-0100Z", "images-20261017-0200Z", "latest"]},
      "files": {"fake:P/images-20261017-0200Z": _files(**{"portal.sif": "aa", "SHA256SUMS": "bb"}),
                "fake:P/latest": _files(**{"portal.sif": "zz", "SHA256SUMS": "bb"})}}, False,
     "포털: latest/ 가 images-20261017-0200Z/ 보다 낡았다 — portal.sif"),
    ({"dirs": {"fake:P": ["images-20261017-0200Z", "latest"]},
      "files": {"fake:P/images-20261017-0200Z": _files(**{"gatus.sif": "aa"}), "fake:P/latest": []}}, False, "gatus.sif(latest/ 에 없다)"),
    ({"dirs": {"fake:P": ["images-20261017-0200Z", "latest"]},
      "files": {"fake:P/images-20261017-0200Z": [{"Name": "a.sif", "Size": 5}], "fake:P/latest": [{"Name": "a.sif", "Size": 6}]}}, False,
     "— a.sif"),
    ({"dirs": {"fake:P": ["images-20261017-0200Z"]}, "files": {}}, False, "latest/ 가 없다"),
    ({"dirs": {"fake:P": ["latest"]}, "files": {}}, True, "리모트 1곳"),
    ({"fail": True}, False, "포털: Drive 에 닿지 못했다(rclone rc 1 — Failed to create file system"),
])
def test_Drive_latest_가_가장_새_업로드를_따라왔는지_본다(lay, monkeypatch, fx, ok, needle):
    monkeypatch.setenv("PATH", f"{lay.bin}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_RCLONE", str(lay.rclone_fx))
    lay.drive(fx)
    m = lay.module("status-push")
    got = m.check_drive_latest({"timeout_s": 60, "remotes": [{"label": "포털", "remote": "fake:P", "prefix": "images-"}]})
    assert got[0] is ok and needle in got[1], got
    if not fx.get("fail"):
        calls = (lay.rclone_fx.parent / (lay.rclone_fx.name + ".calls")).read_text()
        assert "lsf --dirs-only fake:P/" in calls and ("--hash-type md5" in calls or "lsjson" not in calls), calls


# ── 밀어 넣는 쪽 — 밀어 넣기 ──────────────────────────────────────────────────────────────────────────
def test_밀어_넣기는_루프백_Gatus_에_토큰과_함께_프록시_없이_간다(lay, gatus, monkeypatch):
    dead = _free_port()
    for k in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy"):
        monkeypatch.setenv(k, f"http://127.0.0.1:{dead}")
    m = lay.module("status-push")
    cfg = {"url": f"http://127.0.0.1:{gatus.port}", "token": "tok-123"}
    assert m.push(cfg, "checks_mcp-smoke", False, "호출 0성공 — ra: 만료", 2.6) == (True, "")
    assert m.push(cfg, "checks_drive-latest", True, "무시된다", 0.2) == (True, "")
    (p1, q1, a1), (p2, q2, a2) = gatus.got
    assert p1 == "/api/v1/endpoints/checks_mcp-smoke/external" and a1 == "Bearer tok-123"
    assert q1 == {"success": "false", "error": "호출 0성공 — ra: 만료", "duration": "3s"}
    assert q2 == {"success": "true", "duration": "0s"}, "성공에는 오류 칸을 싣지 않는다"


def test_401_은_다시_하지_않고_그_밖의_실패는_세_번까지(lay, gatus, monkeypatch):
    m = lay.module("status-push")
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    cfg = {"url": f"http://127.0.0.1:{gatus.port}", "token": "t"}
    gatus.code = 401
    ok, why = m.push(cfg, "checks_x", True, "", 1)
    assert not ok and "어긋났다" in why and len(gatus.got) == 1
    gatus.code = 503
    ok, why = m.push(cfg, "checks_x", True, "", 1)
    assert not ok and why == "HTTP 503" and len(gatus.got) == 4


def test_once_는_검사마다_결과를_찍고_밀어_넣는다(lay, gatus):
    assert lay.gen().returncode == 0
    lay.smoke({"backends": {"a": {"ok": 1, "probed": ["x"]}}, "dead": [], "drift": {}})
    lay.drive({"dirs": {"fake:HWAXPortal": ["images-20261017-0200Z", "latest"]},
               "files": {"fake:HWAXPortal/images-20261017-0200Z": _files(a="1"), "fake:HWAXPortal/latest": _files(a="2")}})
    r = lay.push_cmd("once")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "✓ mcp-smoke — 백엔드 1곳 호출 성공" in r.stdout and "✗ drive-latest — 포털: latest/ 가 images-20261017-0200Z/ 보다 낡았다" in r.stdout
    assert [g[0] for g in gatus.got] == ["/api/v1/endpoints/checks_mcp-smoke/external", "/api/v1/endpoints/checks_drive-latest/external"]
    assert {g[2] for g in gatus.got} == {f"Bearer {lay.push_json()['token']}"} and lay.push_json()["token"] not in r.stdout
    gatus.got.clear()
    r = lay.push_cmd("once", "mcp-smoke", "--no-push")
    assert r.returncode == 0 and not gatus.got
    (lay.state / "push.json").unlink()
    r = lay.push_cmd("once")
    assert r.returncode == 2 and "push.json 이 없다" in r.stdout


# ── 밀어 넣는 쪽 — loop 의 수명 ──────────────────────────────────────────────────────────────────────────
def _loop(lay: Lay, parent: int) -> subprocess.Popen:
    """첫 검사 · 틱을 줄여 loop 를 띄운다(운영 값은 120초 · 15초)."""
    code = ("import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location('sp', {str(lay.repo / 'infra/scripts/status-push.py')!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "m.FIRST_DELAY_S = 0; m.TICK_S = 1\n"
            f"sys.exit(m.loop({parent}))\n")
    return subprocess.Popen([sys.executable, "-B", "-c", code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env=lay.env())


def _until(cond, timeout: float = 15.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def test_loop_는_밀어_넣고_시한_지난_멈춤을_걷고_TERM_에_끝난다(lay, gatus):
    assert lay.gen().returncode == 0
    lay.smoke({"backends": {}, "dead": [], "drift": {}})
    lay.drive({"dirs": {"fake:HWAXPortal": ["latest"]}, "files": {}})
    assert lay.gen("--pause", "30").returncode == 0
    rec = json.loads((lay.state / "pause.json").read_text())
    (lay.state / "pause.json").write_text(json.dumps({**rec, "until": time.time() - 1}))   # update-all 이 5b 전에 죽었다
    p = _loop(lay, os.getpid())
    try:
        assert _until(lambda: len(gatus.got) >= 2), "두 검사를 밀어 넣는다"
        assert _until(lambda: "maintenance" not in lay.doc()), "시한이 지난 멈춤을 걷는다"
        assert not (lay.state / "pause.json").exists()
        p.send_signal(signal.SIGTERM)
        assert p.wait(15) == 0
    finally:
        if p.poll() is None:
            p.kill()
    out = p.stdout.read()
    assert "✓ mcp-smoke" in out and "✓ drive-latest" in out and "경보 멈춤을 풀었다" in out and "TERM — 끝낸다" in out, out
    assert lay.push_json()["token"] not in out


def test_밀어_넣는_쪽은_시한이_지났거나_기록_없이_창만_남았을_때_걷어낸다(lay):
    m = lay.module("status-push")
    now = time.time()
    assert m._needs_unpause(now) is False, "멈춤이 없다"
    lay.state.mkdir(parents=True, exist_ok=True)
    (lay.state / "pause.json").write_text(json.dumps({"since": now - 60, "until": now + 600}))
    assert m._needs_unpause(now) is False, "시한 안"
    (lay.state / "pause.json").write_text(json.dumps({"since": now - 60, "until": now - 1}))
    assert m._needs_unpause(now) is True, "시한이 지났다"
    (lay.state / "pause.json").write_text("{깨짐")
    assert m._needs_unpause(now) is True, "기록을 못 읽으면 걷는다(남겨 두면 다음 주 같은 시각에 또 멈춘다)"
    (lay.state / "pause.json").unlink()
    (lay.state / "config.yaml").write_text("web: {}\nmaintenance:\n  start: '01:00'\n")
    assert m._needs_unpause(now) is True, "시한 기록 없이 창만 남았다"
    (lay.state / "config.yaml").write_text("web: {}\nendpoints:\n- name: x\n  maintenance-windows: []\n")
    assert m._needs_unpause(now) is False, "끝점 칸의 같은 낱말은 아니다"


def test_loop_는_부모가_사라지면_끝난다(lay):
    assert lay.gen().returncode == 0
    p = _loop(lay, 1)                 # 부모가 1 이 아니다 — 띄운 셸이 이미 사라진 것과 같다
    assert p.wait(15) == 0 and "부모(status-board.sh)가 사라졌다" in p.stdout.read()


# ── 띄우는 스크립트 — 밀어 넣는 쪽의 수명 ────────────────────────────────────────────────────────────────
APPTAINER_STUB = '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$STUB_OUT"\nfor i in $(seq 1 50); do [ -f "$STUB_PY_READY" ] && break; sleep 0.1; done\nexit 0\n'
# 가짜 python3 는 TERM 을 받으면 적고 끝난다. 못 받아도 20초 뒤 스스로 끝난다 — 띄우는 스크립트가 exec 로 되돌아간 변이에서 고아로 남았다.
PYTHON_STUB = ('#!/usr/bin/env bash\ntrap \'echo term >> "$STUB_PY_OUT"; exit 0\' TERM\n'
               'printf "%s\\n" "$@" "ppid=$PPID" > "$STUB_PY_OUT"\ntouch "$STUB_PY_READY"\nfor i in $(seq 1 200); do sleep 0.1; done\n')


def _launch(lay: Lay) -> tuple[subprocess.CompletedProcess, Path]:
    stubs = lay.tmp / "stubs"
    stubs.mkdir(exist_ok=True)
    (stubs / "apptainer").write_text(APPTAINER_STUB, encoding="utf-8")
    (stubs / "python3").write_text(PYTHON_STUB, encoding="utf-8")
    for n in ("apptainer", "python3"):
        (stubs / n).chmod(0o755)
    py_out = lay.tmp / "py.out"
    env = {"PATH": f"{stubs}:{os.environ['PATH']}", "HOME": str(lay.tmp), "APPTAINER": str(stubs / "apptainer"),
           "STUB_OUT": str(lay.tmp / "argv.txt"), "STUB_PY_OUT": str(py_out), "STUB_PY_READY": str(lay.tmp / "py.ready")}
    (lay.repo / "infra/apptainer/gatus.sif").write_text("")
    r = subprocess.run(["bash", str(lay.repo / "infra/scripts/status-board.sh"), "run"], capture_output=True, text=True, env=env, timeout=60)
    return r, py_out


def test_띄우는_스크립트는_밀어_넣는_쪽을_부모_pid_와_함께_띄우고_Gatus_가_끝나면_내린다(lay):
    assert lay.gen().returncode == 0
    r, py_out = _launch(lay)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = py_out.read_text().splitlines()
    assert lines[:3] == [str(lay.repo / "infra/scripts/status-push.py"), "loop", "--parent"], lines
    assert lines[4] == f"ppid={lines[3]}", "부모 pid 는 띄운 셸 자신이다 — 그 셸이 사라지면 밀어 넣는 쪽이 끝난다"
    assert lines[-1] == "term", "Gatus 가 끝나면 밀어 넣는 쪽을 TERM 으로 내린다"
    argv = (lay.tmp / "argv.txt").read_text().splitlines()
    assert "/gatus" == argv[-1] and f"{lay.state}/data:/data" in argv


def test_push_json_이_없으면_밀어_넣는_쪽을_띄우지_않는다(lay):
    assert lay.gen().returncode == 0
    (lay.state / "push.json").unlink()
    r, py_out = _launch(lay)
    assert r.returncode == 0 and not py_out.exists(), r.stdout + r.stderr


# ── 스모크 — 주기 판 허용 목록(신원 전용 백엔드는 test_update_all_health_gate) ──────────────────────────────────────────────
def _smoke_mod():
    spec = importlib.util.spec_from_file_location("smoke_for_push", SCRIPTS / "mcp-smoke.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("name,probe", [
    ("list_agents", True), ("risk_list_projects", True), ("heaxstep_forge_system_status", True), ("inbox_status", True),
    ("get_server_info", True), ("describe_search_status", True), ("catalog_search", True), ("cluster_info", True),
    ("query_voc", True), ("risk_taxonomy", True),
    # 2026-10-17 dev 목록에서 '무인자 · 쓰기 낱말 아님' 으로 스모크 후보였던 것 — 주기 판은 부르지 않는다
    ("fullangle_drop_simulation", False), ("daily_briefing", False), ("alert_check", False), ("discover", False),
    ("echo", False), ("part_history", False), ("deliberate_jobs", False),
])
def test_주기_판은_읽기_낱말_허용_목록의_도구만_부른다(name, probe):
    m = _smoke_mod()
    allowed = bool(m.READ.search(name)) and not (m.WRITE.match(name) or m.WRITE_ANY.search(name))
    assert allowed is probe, name


# ── update-all — 1b2 가 걸고 5b · § 머리 정지 · 완주 끝이 푼다 ────────────────────────────────────────────────
def _region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


class Box:
    """update-all 의 1b2 구획 · _hwax_board_resume 을 원문 그대로 — services.sh enabled 와 생성기는 인자를 적는 대역이다."""

    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts").mkdir(parents=True)
        self.calls = self.tmp / "calls.log"
        self.calls.write_text("")
        svc = self.repo / "infra/scripts/services.sh"
        svc.write_text(f'#!/usr/bin/env bash\necho "services.sh $*" >> "{self.calls}"; exit "${{STUB_EN:-1}}"\n', encoding="utf-8")
        svc.chmod(0o755)
        (self.repo / "infra/scripts/gen-status-config.py").write_text(
            "import os, sys\n"
            f"open({str(self.calls)!r}, 'a').write('gen ' + ' '.join(sys.argv[1:]) + '\\n')\n"
            "print('✓ (대역) 생성기 ' + ' '.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ.get('STUB_GEN_RC', '0')))\n", encoding="utf-8")

    def run(self, body: str, tail: str = "", **env) -> str:
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'SELF_REPO="{self.repo}"', f'SVC="{self.repo}/infra/scripts/services.sh"',
            'hr() { echo "HR:$*"; }; bad() { echo "BAD:$*"; }',
            body, tail, 'echo "PAUSED=${HWAX_BOARD_PAUSED:-unset}"; echo END'])
        base = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env={**base, **env})
        assert "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout

    def called(self) -> list[str]:
        return self.calls.read_text().splitlines()


def _block_1b2() -> str:
    return _region("# ── 1b2) 상시 상태판 경보 멈춤", "# ── 1c) .env 옵션 동기화")


def _resume_fn() -> str:
    return _region("_hwax_board_resume() {", "\n}\n") + "\n}\n"


def test_1b2_는_상태판이_켜진_박스에서만_60분_멈춤을_건다(tmp_path):
    box = Box(tmp_path)
    out = box.run(_block_1b2(), STUB_EN="1")
    assert box.called() == ["services.sh enabled status-board"] and "PAUSED=0" in out and "HR:" not in out, out
    out = box.run(_block_1b2(), STUB_EN="0")
    assert box.called()[-1] == "gen --pause 60" and "PAUSED=1" in out and "✓ (대역) 생성기 --pause 60" in out, out
    out = box.run(_block_1b2(), STUB_EN="0", STUB_GEN_RC="1")
    assert "PAUSED=0" in out and any("경보 멈춤을 걸지 못했다" in ln and "비치명" in ln for ln in out.splitlines() if ln.startswith("BAD:")), out


def test_풀기는_걸었을_때만_한_번_부른다(tmp_path):
    box = Box(tmp_path)
    out = box.run(_resume_fn(), "HWAX_BOARD_PAUSED=1; _hwax_board_resume; _hwax_board_resume")
    assert [c for c in box.called() if c.startswith("gen")] == ["gen --unpause"] and "PAUSED=0" in out, out
    box.calls.write_text("")
    box.run(_resume_fn(), "HWAX_BOARD_PAUSED=0; _hwax_board_resume")
    assert box.called() == []


def test_update_all_배선_1b2_는_1b_뒤_1c_앞이고_5b_와_정지_경로와_완주_끝이_푼다():
    i1b, i1b2, i1c = UA.index('hr "1b) 배포 전 로컬 백업'), UA.index("# ── 1b2) 상시 상태판 경보 멈춤"), UA.index("# ── 1c) .env 옵션 동기화")
    assert i1b < i1b2 < i1c, "사전 백업(서비스를 멈추지 않는다) 뒤 · 1c~§5 의 재기동 앞에서 건다"
    # 다른 시험이 원문을 떼어 돌리는 구획(1d~1h · 1e~2 · 1f~1h · 1h~1i · 1i~2) 밖이어야 한다 — 끼면 그 하네스에 없는 $SVC 로 죽는다
    # (1h~1i 에 두었다가 비우기 시험 35개가 깨졌다). 그 구획들의 가장 이른 시작이 1d 의 _ste_repo_dir 이다.
    assert i1b2 < UA.index("_ste_repo_dir() {") < UA.index("_envfile_value() {"), "떼어 돌리는 구획보다 앞이다"
    hr_fn = _region("hr() { if", "return 0; }")
    assert "_hwax_board_resume" in hr_fn and hr_fn.index("_hwax_drain_finish") < hr_fn.index("_hwax_board_resume") < hr_fn.index("exit 143")
    b5 = _region("# ── 5b) 상시 상태판(Gatus)", "# ── 5c) 호출 추적(Phoenix)")
    gen_at = b5.index('gen-status-config.py" 2>&1)" || _sb_rc=$?')
    assert b5.index("HWAX_BOARD_PAUSED=0", gen_at) - gen_at < 80, "5b 의 일반 생성 바로 뒤에서 '풀었다' 로 적는다"
    tail = UA[UA.index("# 1h 비우기 끝맺음 — 장부(미룬 재기동 줄)를"):]
    assert tail.index("_hwax_drain_finish") < tail.index("_hwax_board_resume") < tail.index("hwax_skip_summary")
    for line in _block_1b2().splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"
