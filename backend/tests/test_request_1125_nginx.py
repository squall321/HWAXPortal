# cae00 운영 요청(11-24) nginx 셋 — 라우트별 업스트림 Host(HP-72) · *-mcp 끝 슬래시 308(HP-74) · 평문 포트에서 루프백만(HP-75)
"""왜 —
HP-72  loc_block 이 모든 location 에 Host $host 를 박아, 루프백에 묶은 FastMCP 앱(데이터허브 셋 · MX 백서)이 DNS rebinding 막이로 포털 도메인
       Host 를 421 로 거절했다. 박스가 Host 만 바꾸는 nginx 중계를 따로 띄웠고 그것이 죽으면 네 경로가 같이 끊긴다. 손잡이로 고른 라우트만 $proxy_host.
HP-74  앱 MCP 는 '/mcp/' 에 '/mcp' 로 307 을 내는데 Location 이 포털 접두를 몰라 포털 루트로 샜고, 셋은 http:// 로 내려갔다. 접두를 아는 308.
HP-75  *-mcp 가 평문 8088 에서도 답해, http 주소를 등록한 MCP 클라이언트의 개인 토큰이 사내망에 평문으로 흘렀다. 고른 라우트는 평문 서버에서 루프백만.
       기본은 '*-mcp'(사용자 결정 11-28 — 기본 켬), 박스가 끄는 값은 'none'.

생성기를 임시 리포에서 실제로 돌린다(test_request_1123_nginx 와 같은 하네스). 띄운 nginx 시험은 nginx SIF 가 있는 박스에서만 돈다.
"""
import http.server
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

import pytest

from tests.test_request_1123_nginx import ROOT, _apptainer, _generate


def _servers(conf: str) -> list[str]:
    return re.split(r"^    server \{\n", conf, flags=re.M)[1:]


def _loc(server: str, rid: str) -> str:
    m = re.search(r"^        location /" + re.escape(rid) + r"/ \{\n(.*?)^        \}\n", server, re.S | re.M)
    assert m, rid
    return m.group(1)


@pytest.mark.parametrize("tls", [False, True], ids=["http", "tls"])
def test_HP72_기본은_받은_Host_고른_라우트만_업스트림_Host(tmp_path, tls):
    _repo, conf, _out = _generate(tmp_path, tls=tls)
    for srv in _servers(conf):
        if "location /kooremapper-mcp/" in srv:
            assert "proxy_set_header Host              $host;" in _loc(srv, "kooremapper-mcp")
    _repo, conf, out = _generate(tmp_path / "on", tls=tls, infra_env="NGINX_UPSTREAM_HOST_ROUTES=kooremapper-mcp,nope-mcp\n")
    srvs = [s for s in _servers(conf) if "location /kooremapper-mcp/" in s]
    assert len(srvs) == (2 if tls else 1)
    for srv in srvs:
        blk = _loc(srv, "kooremapper-mcp")
        assert "proxy_set_header Host              $proxy_host;" in blk and "X-Forwarded-Host  $http_host" in blk, blk
        assert "proxy_set_header Host              $host;" in _loc(srv, "failuretrace"), "고르지 않은 라우트는 그대로"
    assert "NGINX_UPSTREAM_HOST_ROUTES 의 'nope-mcp' 는 라우트에 없다" in out


LOOPBACK = "            allow 127.0.0.1;\n            allow ::1;\n            deny all;\n"


@pytest.mark.parametrize("tls", [False, True], ids=["http", "tls"])
def test_HP74_mcp_라우트의_끝_슬래시는_접두를_아는_308(tmp_path, tls):
    _repo, conf, _out = _generate(tmp_path, tls=tls)
    for i, srv in enumerate(_servers(conf)):
        if "location /kooremapper-mcp/" not in srv:
            continue
        lb = LOOPBACK if tls and i == 0 else ""     # TLS 박스의 평문 서버는 기본(HP-75 — 11-28 사용자 결정)으로 루프백만
        assert f"        location = /kooremapper-mcp/mcp/ {{\n{lb}            return 308 /kooremapper-mcp/mcp;\n        }}\n" in srv
        assert "location = /failuretrace/mcp/" not in srv and "location = /report-archive/mcp/" not in srv, "-mcp 라우트만"


def test_HP74_길이_있는_업스트림은_건드리지_않는다(tmp_path):
    repo, _conf, _out = _generate(tmp_path, tls=False)
    (repo / "backend/config/routes.local.env").write_text("x-mcp=http://203.0.113.40:9000/mcp/\ny-mcp=http://203.0.113.41:9000\n")
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stderr
    conf = (repo / "infra/nginx/hwax.conf").read_text(encoding="utf-8")
    assert "location = /x-mcp/mcp/" not in conf, "…/mcp/ 를 적은 라우트는 이미 그 길로 간다"
    assert "location = /y-mcp/mcp/" in conf, "맨 호스트는 생성기가 '/' 를 붙여 루트를 가리킨다"


@pytest.mark.parametrize("env", ["", "NGINX_TLS_ONLY_ROUTES=\n", "NGINX_TLS_ONLY_ROUTES=*-mcp\n"], ids=["기본", "빈값", "적음"])
def test_HP75_평문_서버에서만_루프백으로_좁힌다(tmp_path, env):
    """기본이 '*-mcp' 다(사용자 결정 11-28) — 줄이 없거나 비어도 -mcp 라우트는 평문 서버에서 루프백만. 몇 개에 붙었는지 한 줄로 알린다."""
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env=env)
    plain, tls_srv = _servers(conf)
    blk = _loc(plain, "kooremapper-mcp")
    assert blk.startswith(LOOPBACK), blk
    assert re.search(r"평문 서버\(:8088\)에서 루프백만 받는 라우트 1개 — 밖에서는 https 로만\(NGINX_TLS_ONLY_ROUTES=\*-mcp"
                     + (" — 기본" if "*-mcp" not in env else r" ·"), out), out
    assert "deny all" not in _loc(tls_srv, "kooremapper-mcp"), "TLS 서버는 그대로"
    assert "deny all" not in _loc(plain, "failuretrace"), "-mcp 가 아닌 라우트는 그대로"
    assert re.search(r"location = /kooremapper-mcp/mcp/ \{\n            allow 127.0.0.1;\n            allow ::1;\n            deny all;\n"
                     r"            return 308", plain), "끝 슬래시 308 도 평문에서는 루프백만"
    _repo, conf, _out = _generate(tmp_path / "one", tls=True, infra_env="NGINX_TLS_ONLY_ROUTES=failuretrace\n")
    plain, _t = _servers(conf)
    assert "deny all" in _loc(plain, "failuretrace") and "deny all" not in _loc(plain, "kooremapper-mcp")


def test_HP75_TLS_가_꺼진_박스에서는_쓰지_않는다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env="NGINX_TLS_ONLY_ROUTES=*-mcp\n")
    assert "deny all" not in conf and "NGINX_TLS_ONLY_ROUTES 를 쓰지 않는다 — TLS 가 꺼진 박스다" in out
    # 기본값이면 ⚠ 가 아니라 알리기만 — TLS 를 안 켠 박스(dev)가 생성할 때마다 경고를 받지 않게
    _repo, conf, out = _generate(tmp_path / "d", tls=False)
    assert "deny all" not in conf and "⚠ NGINX_TLS_ONLY_ROUTES" not in out
    assert "· 평문 막기(NGINX_TLS_ONLY_ROUTES 기본 *-mcp)는 쓰지 않는다 — TLS 가 꺼진 박스다(ENABLE_TLS)" in out, out


def test_HP75_none_이면_끈다(tmp_path):
    """박스가 끄는 값은 'none' — 평문 서버도 종전처럼 받고, 알림 줄 · 이름 꼴 경고가 없다."""
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env="NGINX_TLS_ONLY_ROUTES=none\n")
    assert "deny all" not in conf and "루프백만 받는 라우트" not in out and "NGINX_TLS_ONLY_ROUTES 의" not in out, out


def test_예시_파일이_두_손잡이를_주석으로_선언한다():
    example = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    for key in ("NGINX_UPSTREAM_HOST_ROUTES", "NGINX_TLS_ONLY_ROUTES"):
        lines = [ln for ln in example.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln)]
        assert len(lines) == 1 and lines[0].startswith(f"# {key}="), f"{key}: {lines}"


def _lan_ip() -> str | None:
    """루프백이 아닌 이 박스 주소 — 그리로 붙으면 출발 주소도 그것이라 nginx 의 $remote_addr 가 루프백이 아니다."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("203.0.113.1", 9))          # 보내지 않는다 — 고른 출발 주소만 본다
            ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


@pytest.mark.skipif(not (ROOT / "infra/apptainer/nginx.sif").is_file() or not _apptainer(), reason="nginx SIF · apptainer 없음")
def test_띄운_nginx_가_업스트림_Host_와_308_과_평문_막기를_지킨다(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("openssl 없음 — TLS 블록용 임시 인증서를 못 만든다")
    ports = []
    for _ in range(2):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); ports.append(s.getsockname()[1])

    class Up(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"HOST=" + (self.headers.get("Host") or "").encode())

        def log_message(self, *a):
            pass
    up = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Up)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    upport = up.server_address[1]
    repo, _conf, _out = _generate(tmp_path, tls=True, infra_env="NGINX_UPSTREAM_HOST_ROUTES=a-mcp\n")   # 평문 막기는 기본(11-28)
    (repo / "backend/config/routes.local.env").write_text(f"a-mcp=http://127.0.0.1:{upport}/\nb-mcp=http://127.0.0.1:{upport}/\n")
    (repo / "infra/.env").write_text((repo / "infra/.env").read_text().replace(
        "HTTP_PORT=8088\n", f"HTTP_PORT={ports[0]}\nHTTPS_PORT={ports[1]}\n"))
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
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
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx), NoRedirect())

    def get(url: str, host: str = "portal.example") -> tuple[int, bytes, str]:
        req = urllib.request.Request(url, headers={"Host": host})
        try:
            with opener.open(req, timeout=10) as resp:
                return resp.status, resp.read(), resp.headers.get("Location") or ""
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Location") or ""
    try:
        plain, tls = f"http://127.0.0.1:{ports[0]}", f"https://127.0.0.1:{ports[1]}"
        for _ in range(100):
            if ng.poll() is not None:
                pytest.fail("nginx 가 뜨지 못했다: " + ng.stderr.read().decode("utf-8", "replace"))
            try:
                get(tls + "/a-mcp/x")
                break
            except OSError:
                time.sleep(0.2)
        assert get(tls + "/a-mcp/mcp")[:2] == (200, f"HOST=127.0.0.1:{upport}".encode()), "고른 라우트는 업스트림 Host(HP-72)"
        assert get(tls + "/b-mcp/mcp")[:2] == (200, b"HOST=portal.example"), "고르지 않은 라우트는 받은 Host"
        code, _b, loc = get(tls + "/b-mcp/mcp/")
        # nginx 가 상대 주소를 받은 요청의 scheme · Host · 포트로 절대 주소로 만든다(absolute_redirect) — https 그대로 · 접두 그대로
        assert code == 308 and loc == f"https://portal.example:{ports[1]}/b-mcp/mcp", (code, loc)
        assert get(plain + "/b-mcp/mcp")[0] == 200, "루프백은 평문으로도 받는다(이 박스의 게이트웨이 · 점검)"
        lan = _lan_ip()
        if lan:
            code, _b, _l = get(f"http://{lan}:{ports[0]}/b-mcp/mcp")
            assert code == 403, f"루프백이 아닌 출발 주소는 평문 서버에서 막는다(HP-75) — {code}"
            assert get(f"https://{lan}:{ports[1]}/b-mcp/mcp")[0] == 200, "TLS 서버는 그대로"
    finally:
        ng.terminate()
        try:
            ng.wait(timeout=10)
        except subprocess.TimeoutExpired:
            ng.kill()
        up.shutdown(); up.server_close()
