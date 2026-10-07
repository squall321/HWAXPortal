# nginx 라우트별 추가 지시문(loc_extras) — odb-hub·aireadyportal 의 큰 업로드·긴 요청이 포털 정문에서 잘리지 않는지(ARP·ODB 작업지시 7-2)
"""왜 — 라우트는 routes(.local).env 한 줄로 생기지만 업로드 상한·버퍼링·읽기 시한은 gen-nginx-conf.sh 의 loc_extras 에 이름이
있어야 붙는다. 없으면 ODB++ 수백 MB 가 버퍼링돼 /tmp 에 쌓이고, ARP 의 6GB 해석결과는 전역 상한 2048m 에서 413 이 난다.

전역 상한(hwax.conf.tmpl 의 http 레벨 2048m)은 **그대로** 둔다(7-1 은 하지 않는다 — docs/change-request-8-10 D-6). 전역을 풀면
버퍼링이 켜진 다른 경로의 본문이 크기 제한 없이 /tmp 에 쌓인다. 그래서 aireadyportal location 안에서만 0 으로 푼다.

생성기를 임시 리포에서 **실제로 돌려** 만들어진 conf 를 본다(스크립트·템플릿은 사본, 라우트·infra/.env 는 지어낸 값).
주소는 문서용 예약 대역(TEST-NET)만 쓴다.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ROUTES = """\
# 추적 파일 — 예시
ai-data-hub=http://127.0.0.1:8001/
signalforge/api=http://127.0.0.1:18000/api/
heax-hub=http://127.0.0.1:4040/
apps=http://127.0.0.1:4040/apps/
"""
ROUTES_LOCAL = """\
# 이 박스 전용
ste=http://127.0.0.1:15810/
report-archive=http://203.0.113.10:3000/
odb-hub=http://203.0.113.30:8000/
aireadyportal=http://203.0.113.20:3001
knox-bridge=http://127.0.0.1:9120/
"""


def _generate(tmp_path: Path, *, tls: bool) -> str:
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/nginx").mkdir(); (repo / "backend/config").mkdir(parents=True)
    for f in ("gen-nginx-conf.sh", "_common.sh"):
        shutil.copy(ROOT / "infra/scripts" / f, repo / "infra/scripts" / f)
    shutil.copy(ROOT / "infra/nginx/hwax.conf.tmpl", repo / "infra/nginx/hwax.conf.tmpl")
    (repo / "infra/.env").write_text("HTTP_PORT=8088\nPORTAL_PORT=8723\n" + ("ENABLE_TLS=true\nTLS_SERVER_NAME=hwax.example\n" if tls else ""))
    (repo / "backend/config/routes.env").write_text(ROUTES)
    (repo / "backend/config/routes.local.env").write_text(ROUTES_LOCAL)
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "9 system route(s)" in r.stdout, r.stdout
    return (repo / "infra/nginx/hwax.conf").read_text(encoding="utf-8")


def _locations(conf: str, rid: str) -> list[str]:
    """`location /<id>/ { … }` 블록 본문 전부(HTTP 서버 하나, TLS 를 켜면 둘)."""
    return re.findall(r"^        location /" + re.escape(rid) + r"/ \{\n(.*?)^        \}\n", conf, re.S | re.M)


@pytest.fixture(scope="module", params=[False, True], ids=["http", "http+tls"])
def conf(request, tmp_path_factory):
    return _generate(tmp_path_factory.mktemp("nginx"), tls=request.param), (2 if request.param else 1)


def test_aireadyportal_은_상한을_풀고_스트리밍으로_넘긴다(conf):
    """해석결과 업로드 최대 6GB · Abaqus 추출 동기 요청 최대 40분."""
    text, servers = conf
    blocks = _locations(text, "aireadyportal")
    assert len(blocks) == servers, "라우트가 서버 블록마다 하나씩 생겨야 한다"
    for b in blocks:
        assert "client_max_body_size 0;" in b
        assert "proxy_request_buffering off;" in b, "이 줄이 없으면 6GB 가 /tmp 에 쌓여 디스크를 채운다"
        assert "proxy_buffering off;" in b and "proxy_read_timeout 3600s;" in b
        assert "proxy_pass http://203.0.113.20:3001/;" in b


def test_odb_hub_는_기존_큰_업로드_묶음에_든다(conf):
    """ODB++ 수십~수백 MB · MCP streamable-http 스트리밍 · 뷰어 기하 요청 수십 초."""
    text, servers = conf
    blocks = _locations(text, "odb-hub")
    assert len(blocks) == servers
    for b in blocks:
        assert "client_max_body_size 2048m;" in b and "proxy_request_buffering off;" in b
        assert "proxy_buffering off;" in b and "proxy_read_timeout 600s;" in b


def test_기존_묶음은_그대로다(conf):
    text, servers = conf
    for rid in ("ste", "apps", "heax-hub", "report-archive"):
        blocks = _locations(text, rid)
        assert len(blocks) == servers, rid
        for b in blocks:
            assert "client_max_body_size 2048m;" in b and "proxy_read_timeout 600s;" in b, rid


def test_상한이_풀린_곳은_aireadyportal_뿐이고_전역_상한은_2048m_그대로다(conf):
    """**7-1 을 하지 않았다는 보증** — 전역이 0 이 되면 버퍼링이 켜진 /agent/·/mcp-gw/·포털 `/` 의 본문이 제한 없이 /tmp 에 쌓인다."""
    text, servers = conf
    assert text.count("client_max_body_size 0;") == servers, "aireadyportal location 밖에서 상한이 풀렸다"
    http_level = [ln for ln in text.splitlines() if ln.startswith("    client_max_body_size")]
    assert http_level == ["    client_max_body_size 2048m;"], "http 레벨 전역 상한이 바뀌었다"
    for rid in ("ai-data-hub", "signalforge/api", "knox-bridge"):
        blocks = _locations(text, rid)
        assert len(blocks) == servers, rid
        for b in blocks:
            assert "client_max_body_size" not in b and "proxy_request_buffering" not in b, f"{rid} 는 전역 상한(2048m)을 물려받는다"
    for fixed in ("location /agent/ {", "location /mcp-gw/ {", "location / {"):
        i = text.index(fixed)
        assert "client_max_body_size" not in text[i:text.index("}", i)], fixed
