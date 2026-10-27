# 10-27 수정 요청 nginx 셋(HP-12 · HP-13 · HP-47) — /ste/ 읽기 시한 손잡이 · simflow · stcx-llm 갈래 · /ste/ 결과 파일 제한(기본 끔)
"""왜 — 라우트별 지시문은 gen-nginx-conf.sh 의 loc_extras 에 이름이 있어야 붙고, conf 는 start.sh · deploy-all · update-all 이 다시 만든다.

HP-12  /ste/ 의 proxy_read_timeout 이 conf 를 다시 만들 때마다 600s 로 돌아갔다 — cae00 은 3600s 를 손으로 다시 넣고 있었다.
HP-13  simflow(600MB 업로드 · MCP 스트리밍) · stcx-llm(60초 넘는 생성 · 수십 MB 본문) 갈래가 없어 임시 디스크에 쌓이고 60초에 끊겼다.
HP-47  사내 클라이언트 한 대가 수 GB 결과를 되풀이해 받는다 — 제한 손잡이는 두되 기본은 끈다(사용자 결정 D-6). 켜도 결과 파일에만 건다.

생성기를 임시 리포에서 실제로 돌려 만들어진 conf 를 본다(스크립트 · 템플릿은 사본). 주소는 문서용 예약 대역(TEST-NET)만 쓴다.
nginx SIF 가 있는 박스에서는 만들어진 conf 를 `nginx -t` 로도 본다(/tmp 는 임시 폴더로 바꿔 끼운다 — 떠 있는 nginx 의 파일을 건드리지 않게).
"""
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ROUTES = """\
ai-data-hub=http://127.0.0.1:8001/
apps=http://127.0.0.1:4040/apps/
"""
ROUTES_LOCAL = """\
ste=http://127.0.0.1:15810/
simflow=http://203.0.113.40:8600/
stcx-llm=http://203.0.113.50:8000/
"""


def _generate(tmp_path: Path, *, tls: bool, infra_env: str = "") -> tuple[Path, str, str]:
    """(임시 리포, 만들어진 conf, 화면 출력)."""
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/nginx").mkdir(); (repo / "backend/config").mkdir(parents=True)
    for f in ("gen-nginx-conf.sh", "_common.sh"):
        shutil.copy(ROOT / "infra/scripts" / f, repo / "infra/scripts" / f)
    shutil.copy(ROOT / "infra/nginx/hwax.conf.tmpl", repo / "infra/nginx/hwax.conf.tmpl")
    (repo / "infra/.env").write_text("HTTP_PORT=8088\nPORTAL_PORT=8723\n"
                                     + ("ENABLE_TLS=true\nTLS_SERVER_NAME=hwax.example\n" if tls else "") + infra_env)
    (repo / "backend/config/routes.env").write_text(ROUTES)
    (repo / "backend/config/routes.local.env").write_text(ROUTES_LOCAL)
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    return repo, (repo / "infra/nginx/hwax.conf").read_text(encoding="utf-8"), r.stdout + r.stderr


def _locations(conf: str, rid: str) -> list[str]:
    return re.findall(r"^        location /" + re.escape(rid) + r"/ \{\n(.*?)^        \}\n", conf, re.S | re.M)


def _directives(conf: str) -> str:
    """주석을 뺀 conf — 템플릿 주석에 지시문 이름이 나와도 걸리지 않게."""
    return "\n".join(ln for ln in conf.splitlines() if not ln.lstrip().startswith("#"))


def _read_timeout(block: str) -> str:
    return re.search(r"proxy_read_timeout ([^;]+);", block).group(1)


@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_HP12_비우면_600s_고_적으면_두_서버의_ste_가_같이_바뀐다(tmp_path, tls):
    servers = 2 if tls else 1
    _repo, conf, out = _generate(tmp_path / "a", tls=tls)
    assert [_read_timeout(b) for b in _locations(conf, "ste")] == ["600s"] * servers
    assert "{{" not in conf and "✗" not in out, out
    _repo, conf, out = _generate(tmp_path / "b", tls=tls, infra_env="NGINX_STE_READ_TIMEOUT=3600s\n")
    assert [_read_timeout(b) for b in _locations(conf, "ste")] == ["3600s"] * servers
    assert [_read_timeout(b) for b in _locations(conf, "apps")] == ["600s"] * servers, "묶음의 다른 갈래까지 바뀌었다"


@pytest.mark.parametrize("bad", ["0", "abc", "10x", "1/2"])
def test_HP12_모양이_틀린_값은_버리고_기본값이다(tmp_path, bad):
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env=f"NGINX_STE_READ_TIMEOUT={bad}\n")
    assert [_read_timeout(b) for b in _locations(conf, "ste")] == ["600s"] * 2
    assert "✗ NGINX_STE_READ_TIMEOUT" in out, out


@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_HP13_simflow_와_stcx_llm_은_흘리고_오래_기다린다(tmp_path, tls):
    servers = 2 if tls else 1
    _repo, conf, _out = _generate(tmp_path, tls=tls)
    simflow = _locations(conf, "simflow")
    assert len(simflow) == servers
    for b in simflow:
        for line in ("client_max_body_size 600m;", "proxy_request_buffering off;", "proxy_buffering off;", "proxy_read_timeout 3600s;"):
            assert line in b, line
    llm = _locations(conf, "stcx-llm")
    assert len(llm) == servers
    for b in llm:
        for line in ("client_max_body_size 200m;", "proxy_buffering off;", "proxy_read_timeout 3600s;"):
            assert line in b, line


def test_HP47_기본은_끔이다(tmp_path):
    _repo, conf, _out = _generate(tmp_path, tls=True)
    d = _directives(conf)
    assert "limit_rate" not in d and "limit_conn" not in d and "ste_result" not in d


def test_HP47_켜면_결과_파일에만_건다(tmp_path):
    _repo, conf, out = _generate(tmp_path, tls=True, infra_env="NGINX_STE_RESULT_RATE=20m\nNGINX_STE_RESULT_CONN=2\n")
    assert "✗" not in out, out
    http_level = [ln for ln in conf.splitlines() if ln.startswith("    map $uri $ste_result") or ln.startswith("    limit_conn_zone")]
    assert http_level == [
        '    map $uri $ste_result_rate { "~^/ste/api/jobs/[^/]+/result(\\.zip|/file/)" 20m; default 0; }',
        '    map $uri $ste_result_key { "~^/ste/api/jobs/[^/]+/result(\\.zip|/file/)" $binary_remote_addr; default ""; }',
        "    limit_conn_zone $ste_result_key zone=ste_result:10m;",
    ], http_level
    for b in _locations(conf, "ste"):
        assert "limit_rate $ste_result_rate;" in b and "limit_conn ste_result 2;" in b and "limit_conn_status 429;" in b
    for rid in ("apps", "simflow", "stcx-llm", "ai-data-hub"):
        for b in _locations(conf, rid):
            assert "limit_" not in b, rid
    # 결과 파일 경로만 고른다 — 목록(JSON) · 화면 · 업로드는 키가 비어 세지 않는다
    rx = re.compile(r"^/ste/api/jobs/[^/]+/result(\.zip|/file/)")
    assert rx.match("/ste/api/jobs/j1/result/file/d3hsp") and rx.match("/ste/api/jobs/j1/result.zip")
    assert not rx.match("/ste/api/jobs/j1/result") and not rx.match("/ste/api/jobs") and not rx.match("/ste/")


@pytest.mark.parametrize("env, name", [("NGINX_STE_RESULT_RATE=fast\n", "NGINX_STE_RESULT_RATE"),
                                       ("NGINX_STE_RESULT_CONN=0\n", "NGINX_STE_RESULT_CONN")])
def test_HP47_모양이_틀린_값은_끔으로_만든다(tmp_path, env, name):
    _repo, conf, out = _generate(tmp_path, tls=False, infra_env=env)
    d = _directives(conf)
    assert f"✗ {name}" in out and "limit_" not in d and "ste_result" not in d


def test_예시_파일이_세_손잡이를_주석으로_선언한다():
    example = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    for key, val in (("NGINX_STE_READ_TIMEOUT", "600s"), ("NGINX_STE_RESULT_RATE", "20m"), ("NGINX_STE_RESULT_CONN", "2")):
        lines = [ln for ln in example.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln)]
        assert lines == [f"# {key}={val}"], f"{key}: {lines}"


def _apptainer() -> str | None:
    for c in sorted((ROOT / "infra/apptainer").glob("bin-*/usr/bin/apptainer")):
        if os.access(c, os.X_OK):
            return str(c)
    return shutil.which("apptainer")


@pytest.mark.skipif(not (ROOT / "infra/apptainer/nginx.sif").is_file() or not _apptainer(), reason="nginx SIF · apptainer 없음")
@pytest.mark.parametrize("infra_env", ["", "NGINX_STE_READ_TIMEOUT=3600s\nNGINX_STE_RESULT_RATE=20m\nNGINX_STE_RESULT_CONN=2\n"],
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
