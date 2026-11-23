# cae00 11-23 요청 nginx 넷(HP-79 · HP-80 · HP-73 · HP-81) — 기본 시간 한도 · worker 열린 파일 한도 · *-mcp 스트리밍 · 큰 응답 버퍼(기본 끔)
"""왜 — cae00 은 생성된 hwax.conf 에 이 값들을 손으로 넣었는데 conf 를 다시 만들 때마다(start.sh · update-all · deploy-all) 지워졌다.

HP-79  http 레벨에 시간 한도가 없어 loc_extras 에 이름이 없는 라우트(데이터허브 웹 경로 등)가 nginx 기본 60s 에 504(7일 42건).
HP-80  worker 의 열린 파일 한도가 박스 기본 soft 1024 — 프록시는 손님 하나에 연결 둘이라 worker 하나가 500 명 남짓에서 막힌다.
HP-73  플랫폼마다의 MCP 입구(*-mcp)에 스트리밍 묶음이 없어 전역 gzip · 버퍼링이 SSE 를 붙잡았다.
HP-81  큰 JSON 응답이 /tmp 임시 파일에 쓰였다 — 고른 라우트에만 버퍼를 키운다(기본 끔).

생성기를 임시 리포에서 실제로 돌려 만들어진 conf 를 본다(test_request_1027_nginx 와 같은 꼴). 주소는 문서용 예약 대역(TEST-NET)만 쓴다.
"""
import os
import re
import resource
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ROUTES = """\
ai-data-hub=http://127.0.0.1:8001/
apps=http://127.0.0.1:4040/apps/
report-archive=http://203.0.113.10:9000/
"""
ROUTES_LOCAL = """\
ste=http://127.0.0.1:15810/
failuretrace=http://203.0.113.20:8101/
kooremapper-mcp=http://203.0.113.30:8701/
"""


def _generate(tmp_path: Path, *, tls: bool, infra_env: str = "", nofile_hard: int | None = None) -> tuple[Path, str, str]:
    """(임시 리포, 만들어진 conf, 화면 출력). nofile_hard 를 주면 생성기를 그 hard 한도로 낮춘 셸에서 돌린다."""
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/nginx").mkdir(); (repo / "backend/config").mkdir(parents=True)
    for f in ("gen-nginx-conf.sh", "_common.sh"):
        shutil.copy(ROOT / "infra/scripts" / f, repo / "infra/scripts" / f)
    shutil.copy(ROOT / "infra/nginx/hwax.conf.tmpl", repo / "infra/nginx/hwax.conf.tmpl")
    (repo / "infra/.env").write_text("HTTP_PORT=8088\nPORTAL_PORT=8723\n"
                                     + ("ENABLE_TLS=true\nTLS_SERVER_NAME=hwax.example\n" if tls else "") + infra_env)
    (repo / "backend/config/routes.env").write_text(ROUTES)
    (repo / "backend/config/routes.local.env").write_text(ROUTES_LOCAL)

    def _lower():
        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(soft, nofile_hard), nofile_hard))

    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)}, preexec_fn=_lower if nofile_hard else None)
    assert r.returncode == 0, r.stdout + r.stderr
    return repo, (repo / "infra/nginx/hwax.conf").read_text(encoding="utf-8"), r.stdout + r.stderr


def _locations(conf: str, rid: str) -> list[str]:
    return re.findall(r"^        location /" + re.escape(rid) + r"/ \{\n(.*?)^        \}\n", conf, re.S | re.M)


def _directives(conf: str) -> str:
    """주석을 뺀 conf — 템플릿 주석에 지시문 이름이 나와도 걸리지 않게."""
    return "\n".join(ln for ln in conf.splitlines() if not ln.lstrip().startswith("#"))


def _http_level(conf: str, name: str) -> list[str]:
    """http 블록 바로 아래(들여쓰기 넷) 지시문의 값들 — server · location 안의 것은 들여쓰기가 더 깊다."""
    return re.findall(rf"^    {name} ([^;]+);", conf, re.M)


def _top_level(conf: str, name: str) -> list[str]:
    return re.findall(rf"^{name} ([^;]+);", conf, re.M)


def _value(block: str, name: str) -> str | None:
    m = re.search(rf"{name} ([^;]+);", block)
    return m.group(1) if m else None


def _expected_nofile(want: int) -> int:
    hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    return want if hard == resource.RLIM_INFINITY else min(want, hard)


# ── HP-79 ──

@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_HP79_http_레벨에_기본_시간_한도가_한_번_있다(tmp_path, tls):
    _repo, conf, out = _generate(tmp_path, tls=tls)
    assert _http_level(conf, "proxy_read_timeout") == ["600s"], "http 레벨 기본값은 한 번 — TLS server 에 따로 박으면 손잡이가 둘로 갈린다"
    assert _http_level(conf, "proxy_send_timeout") == ["600s"]
    assert "{{" not in conf and "✗" not in out, out


def test_HP79_손잡이를_적으면_그_값이다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env="NGINX_PROXY_READ_TIMEOUT=900s\n")
    assert _http_level(conf, "proxy_read_timeout") == ["900s"] and _http_level(conf, "proxy_send_timeout") == ["900s"]
    assert "✗" not in out, out


@pytest.mark.parametrize("bad", ["0", "abc", "10 m", "1/2"])
def test_HP79_모양이_틀린_값은_버리고_기본값이다(tmp_path, bad):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env=f"NGINX_PROXY_READ_TIMEOUT='{bad}'\n")
    assert _http_level(conf, "proxy_read_timeout") == ["600s"]
    assert "✗ NGINX_PROXY_READ_TIMEOUT" in out, out


@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_HP79_라우트가_정한_값은_그대로다(tmp_path, tls):
    """location 이 정한 값이 앞선다 — 기본값을 올려도 /ste/ · /apps/ · /report-archive/ · /agent/ · /mcp-gw/ 는 지금 값 그대로."""
    servers = 2 if tls else 1
    _repo, conf, _out = _generate(tmp_path, tls=tls, infra_env="NGINX_PROXY_READ_TIMEOUT=900s\nNGINX_STE_READ_TIMEOUT=3600s\n")
    assert [_value(b, "proxy_read_timeout") for b in _locations(conf, "ste")] == ["3600s"] * servers
    for rid in ("apps", "report-archive"):
        assert [_value(b, "proxy_read_timeout") for b in _locations(conf, rid)] == ["600s"] * servers, rid
    for loc, want in (("agent", "50400s"), ("mcp-gw", "1h")):
        blocks = re.findall(r"location /" + loc + r"/ \{(.*?)\}", conf, re.S)
        assert len(blocks) == servers and all(_value(b, "proxy_read_timeout") == want for b in blocks), loc
    # 이름이 없는 라우트는 location 에 시간 한도가 없다 — http 레벨 값을 물려받는다
    for rid in ("ai-data-hub", "failuretrace"):
        assert all(_value(b, "proxy_read_timeout") is None for b in _locations(conf, rid)), rid


# ── HP-80 ──

def test_HP80_맨_위에_worker_열린_파일_한도가_있다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=True)
    assert _top_level(conf, "worker_rlimit_nofile") == [str(_expected_nofile(65536))]
    lines = conf.splitlines()
    assert lines.index(f"worker_rlimit_nofile {_expected_nofile(65536)};") == lines.index("worker_processes auto;") + 4, "worker_processes 바로 아래(주석 셋 뒤)"


def test_HP80_hard_한도보다_크면_hard_로_낮추고_알린다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=False, nofile_hard=4096)
    assert _top_level(conf, "worker_rlimit_nofile") == ["4096"]
    assert "⚠ NGINX_WORKER_RLIMIT_NOFILE(65536)" in out and "hard 한도(4096)" in out, out


def test_HP80_hard_한도_안의_값은_그대로다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env="NGINX_WORKER_RLIMIT_NOFILE=2048\n", nofile_hard=4096)
    assert _top_level(conf, "worker_rlimit_nofile") == ["2048"] and "⚠ NGINX_WORKER" not in out, out


@pytest.mark.parametrize("bad", ["0", "abc", "-5", "64k", "99999999999"])
def test_HP80_모양이_틀린_값은_버리고_기본값이다(tmp_path, bad):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env=f"NGINX_WORKER_RLIMIT_NOFILE={bad}\n")
    assert _top_level(conf, "worker_rlimit_nofile") == [str(_expected_nofile(65536))]
    assert "✗ NGINX_WORKER_RLIMIT_NOFILE" in out, out


# ── HP-73 ──

@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_HP73_mcp_라우트는_두_서버에서_흘리고_오래_기다린다(tmp_path, tls):
    servers = 2 if tls else 1
    _repo, conf, _out = _generate(tmp_path, tls=tls)
    blocks = _locations(conf, "kooremapper-mcp")
    assert len(blocks) == servers
    for b in blocks:
        for line in ("proxy_buffering off;", "proxy_cache off;", "gzip off;", "proxy_read_timeout 1h;", "proxy_send_timeout 1h;"):
            assert line in b, line
        assert b.index("gzip off;") < b.index("proxy_pass"), "지시문은 proxy_pass 앞 묶음 자리에"


def test_HP73_침묵_한도는_mcp_gw_와_같은_손잡이다(tmp_path):
    _repo, conf, _out = _generate(tmp_path, tls=True, infra_env="NGINX_MCP_READ_TIMEOUT=2h\n")
    for b in _locations(conf, "kooremapper-mcp"):
        assert _value(b, "proxy_read_timeout") == "2h" and _value(b, "proxy_send_timeout") == "2h"
    assert all(_value(b, "proxy_read_timeout") == "2h" for b in re.findall(r"location /mcp-gw/ \{(.*?)\}", conf, re.S))


def test_HP73_이름이_mcp_로_끝나지_않으면_묶음이_없다(tmp_path):
    _repo, conf, _out = _generate(tmp_path, tls=True)
    for rid in ("ai-data-hub", "failuretrace"):
        for b in _locations(conf, rid):
            assert "gzip off;" not in b and "proxy_buffering off;" not in b, rid


# ── HP-81 ──

def test_HP81_기본은_끔이다(tmp_path):
    _repo, conf, _out = _generate(tmp_path, tls=True)
    d = _directives(conf)
    assert "proxy_buffers" not in d and "proxy_buffer_size" not in d and "proxy_busy_buffers_size" not in d


@pytest.mark.parametrize("val", ["failuretrace,ai-data-hub", "'failuretrace ai-data-hub'", "' failuretrace , ai-data-hub '"])
def test_HP81_적은_라우트에만_두_서버_모두_붙는다(tmp_path, val):
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env=f"NGINX_LARGE_BUFFER_ROUTES={val}\n")
    assert "✗" not in out and "⚠ NGINX_LARGE" not in out, out
    for rid in ("failuretrace", "ai-data-hub"):
        blocks = _locations(conf, rid)
        assert len(blocks) == 2
        for b in blocks:
            assert ("proxy_buffer_size 64k;" in b and "proxy_buffers 32 64k;" in b and "proxy_busy_buffers_size 128k;" in b), rid
    for rid in ("apps", "report-archive", "ste", "kooremapper-mcp"):
        assert all("proxy_buffers" not in b for b in _locations(conf, rid)), rid


def test_HP81_라우트에_없는_이름과_틀린_꼴은_알린다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env="NGINX_LARGE_BUFFER_ROUTES='failuretrace,nosuch,bad!id'\n")
    assert "⚠ NGINX_LARGE_BUFFER_ROUTES 의 'nosuch'" in out, out
    assert "✗ NGINX_LARGE_BUFFER_ROUTES 의 'bad!id'" in out, out
    assert "proxy_buffers 32 64k;" in _locations(conf, "failuretrace")[0]


def test_예시_파일이_세_손잡이를_주석으로_선언한다():
    example = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    for key, val in (("NGINX_PROXY_READ_TIMEOUT", "600s"), ("NGINX_WORKER_RLIMIT_NOFILE", "65536"),
                     ("NGINX_LARGE_BUFFER_ROUTES", "failuretrace,rootdesign")):
        lines = [ln for ln in example.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln)]
        assert lines == [f"# {key}={val}"], f"{key}: {lines}"


def _apptainer() -> str | None:
    for c in sorted((ROOT / "infra/apptainer").glob("bin-*/usr/bin/apptainer")):
        if os.access(c, os.X_OK):
            return str(c)
    return shutil.which("apptainer")


@pytest.mark.skipif(not (ROOT / "infra/apptainer/nginx.sif").is_file() or not _apptainer(), reason="nginx SIF · apptainer 없음")
@pytest.mark.parametrize("infra_env", ["", "NGINX_PROXY_READ_TIMEOUT=900s\nNGINX_WORKER_RLIMIT_NOFILE=8192\nNGINX_LARGE_BUFFER_ROUTES=failuretrace,ai-data-hub\n"],
                         ids=["default", "knobs-on"])
def test_만들어진_conf_가_nginx_t_를_통과한다(tmp_path, infra_env):
    if not shutil.which("openssl"):
        pytest.skip("openssl 없음 — TLS 블록용 임시 인증서를 못 만든다")
    ports = []
    for _ in range(2):                      # nginx -t 는 listen 포트도 잡아 본다 — 비어 있는 높은 포트를 준다
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); ports.append(s.getsockname()[1])
    repo, _conf, _out = _generate(tmp_path, tls=True, infra_env=infra_env)
    env = (repo / "infra/.env").read_text().replace("HTTP_PORT=8088\n", f"HTTP_PORT={ports[0]}\nHTTPS_PORT={ports[1]}\n")
    (repo / "infra/.env").write_text(env)
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    tls = repo / "infra/tls"
    tls.mkdir()
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=hwax.example",
                    "-keyout", str(tls / "hwax.key"), "-out", str(tls / "hwax.crt")], check=True, capture_output=True, timeout=60)
    scratch_tmp = tmp_path / "nginx-tmp"
    scratch_tmp.mkdir()
    r = subprocess.run([_apptainer(), "exec", "--bind", f"{repo}:/workspace", "--bind", f"{scratch_tmp}:/tmp",
                        str(ROOT / "infra/apptainer/nginx.sif"), "nginx", "-c", "/workspace/infra/nginx/hwax.conf", "-t"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "test is successful" in r.stderr, r.stdout + r.stderr


# ── 게이트웨이 내부 창구(/internal/result/<ref> — 토큰 절감 2판 docs/token-saving/offload-v2.md 3-3)도 문 앞에서 막는다 ─────────────────
# 서비스 자격 전용 창구다 — 게이트웨이가 X-Forwarded-* 가 실린 요청을 거절하지만 겹쳐 막는다. 무인증 진단 길(health · tools-map · refresh ·
# conn-invalidate)과 같은 404 자리이고, 템플릿(HTTP 서버)과 생성기(TLS 서버)의 사본 둘 다다.
_GW_BLOCKED = ("/mcp-gw/internal/result/abc123", "/mcp-gw/internal/", "/mcp-gw/health", "/mcp-gw/tools-map",
               "/mcp-gw/refresh", "/mcp-gw/conn-invalidate")
_GW_OPEN = ("/mcp-gw/mcp", "/mcp-gw/api/x", "/mcp-gw/fig/abc")


@pytest.mark.parametrize("tls", [False, True], ids=["http", "tls"])
def test_게이트웨이_내부_창구와_진단_길은_서버마다_404_다(tmp_path, tls):
    _repo, conf, _out = _generate(tmp_path, tls=tls)
    servers = [s for s in re.split(r"^    server \{\n", conf, flags=re.M)[1:] if re.search(r"^        location /mcp-gw/ \{", s, re.M)]
    assert len(servers) == (2 if tls else 1), "게이트웨이를 내는 서버 블록마다 본다(TLS 사본 포함)"
    for srv in servers:
        deny = re.findall(r"^        location ~ (\^/mcp-gw/\S+) \{\n            return 404;\n        \}", srv, re.M)
        assert len(deny) == 1, deny
        rx = re.compile(deny[0])
        assert [p for p in _GW_BLOCKED if not rx.search(p)] == [], "막을 길"
        assert [p for p in _GW_OPEN if rx.search(p)] == [], "인증을 지나는 길은 연다"
        assert "location ^~ /mcp-gw/" not in srv, "^~ 접두 위치는 정규식 위치를 건너뛴다 — 차단이 무력해진다"


@pytest.mark.skipif(not (ROOT / "infra/apptainer/nginx.sif").is_file() or not _apptainer(), reason="nginx SIF · apptainer 없음")
def test_띄운_nginx_가_내부_창구를_404_로_막고_인증_길은_흘려보낸다(tmp_path):
    """생성한 conf 로 nginx 를 실제로 띄워 묻는다 — 게이트웨이 자리에는 무엇이든 200 'UPSTREAM' 을 내는 가짜를 둔다(404 가 nginx 의 것인지 가른다)."""
    import http.server
    import ssl
    import threading
    import time
    import urllib.error
    import urllib.request
    if not shutil.which("openssl"):
        pytest.skip("openssl 없음 — TLS 블록용 임시 인증서를 못 만든다")
    ports = []
    for _ in range(2):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); ports.append(s.getsockname()[1])

    class Up(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"UPSTREAM")

        def log_message(self, *a):
            pass
    up = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Up)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    repo, _conf, _out = _generate(tmp_path, tls=True)
    (repo / "infra/.env").write_text((repo / "infra/.env").read_text().replace(
        "HTTP_PORT=8088\n", f"HTTP_PORT={ports[0]}\nHTTPS_PORT={ports[1]}\n"))
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    conf_p = repo / "infra/nginx/hwax.conf"
    conf = conf_p.read_text(encoding="utf-8")
    assert conf.count("proxy_pass http://127.0.0.1:9110/;") == 2
    conf_p.write_text(conf.replace("proxy_pass http://127.0.0.1:9110/;", f"proxy_pass http://127.0.0.1:{up.server_address[1]}/;"))
    (repo / "infra/tls").mkdir()
    (repo / "infra/data").mkdir(exist_ok=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=hwax.example",
                    "-keyout", str(repo / "infra/tls/hwax.key"), "-out", str(repo / "infra/tls/hwax.crt")],
                   check=True, capture_output=True, timeout=60)
    scratch_tmp = tmp_path / "nginx-tmp"
    scratch_tmp.mkdir()
    ng = subprocess.Popen([_apptainer(), "exec", "--bind", f"{repo}:/workspace", "--bind", f"{scratch_tmp}:/tmp",
                           str(ROOT / "infra/apptainer/nginx.sif"), "nginx", "-c", "/workspace/infra/nginx/hwax.conf",
                           "-g", "daemon off;"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))

    def get(url: str) -> tuple[int, bytes]:
        try:
            with opener.open(url, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
    try:
        bases = (f"http://127.0.0.1:{ports[0]}", f"https://127.0.0.1:{ports[1]}")
        for _ in range(100):
            if ng.poll() is not None:
                pytest.fail("nginx 가 뜨지 못했다: " + ng.stderr.read().decode("utf-8", "replace"))
            try:
                get(bases[0] + "/mcp-gw/mcp")
                break
            except OSError:
                time.sleep(0.2)
        for base in bases:
            for path in _GW_BLOCKED:
                code, body = get(base + path)
                assert code == 404 and b"UPSTREAM" not in body, (base, path, code)
            for path in ("/mcp-gw/mcp", "/mcp-gw/api/x"):
                assert get(base + path) == (200, b"UPSTREAM"), (base, path)
    finally:
        ng.terminate()
        try:
            ng.wait(timeout=10)
        except subprocess.TimeoutExpired:
            ng.kill()
        up.shutdown(); up.server_close()
