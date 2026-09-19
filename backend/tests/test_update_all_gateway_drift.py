# update-all 5단계 — 키는 있는데 주소가 틀려서 계속 죽는 게이트웨이 백엔드를 잡는가(2026-09-19 cae00 SignalForge)
#
# update-all.sh 는 실행하면 스택 전체를 만지므로 통째로 돌릴 수 없다. **그 블록의 실제 텍스트**를
# 떼어 가짜 게이트웨이 디렉터리에서 돌린다 — 블록을 고치면 이 시험이 그 고친 것을 돈다.
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UPDATE_ALL = ROOT / "infra" / "scripts" / "update-all.sh"
GW_REPO = ROOT.parent / "HWAXMcpGateway"


def _block(start_marker: str, end_marker: str) -> str:
    src = UPDATE_ALL.read_text(encoding="utf-8")
    i = src.index(start_marker)
    j = src.index(end_marker, i)
    return src[i:j]


@pytest.fixture()
def fake(tmp_path):
    if not (GW_REPO / "provision_urls.py").exists():
        pytest.skip("형제 리포 HWAXMcpGateway 가 이 박스에 없다")
    gw = tmp_path / "HWAXMcpGateway"
    gw.mkdir()
    shutil.copy(GW_REPO / "provision_urls.py", gw / "provision_urls.py")
    (tmp_path / "SignalForge").mkdir()
    return tmp_path, gw


def _run(script: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", **env})


def test_주소가_선언과_어긋나면_재프로비저닝_대상에_든다(fake):
    """cae00 그대로 — config 8013, SignalForge/.env 8008. 키는 있으니 calc_missing 은 못 본다."""
    root, gw = fake
    (root / "SignalForge" / ".env").write_text("MCP_PORT=8008\n", encoding="utf-8")
    (gw / "gateway_config.json").write_text(
        '{"signalforge": {"url": "http://127.0.0.1:8013/mcp", "headers": {"Authorization": "Bearer s3cret"}}}',
        encoding="utf-8")
    blk = _block("  DRIFT=\"\"", "  if [ -n \"$MISSING\" ]; then")
    r = _run(blk + '\necho "MISSING=[$MISSING]"', {"GW_DIR": str(gw), "MISSING": ""})
    assert r.returncode == 0, r.stderr
    assert "MISSING=[signalforge]" in r.stdout, r.stdout
    assert "8013" in r.stdout and "8008" in r.stdout, "무엇이 어긋났는지 사람이 볼 수 있어야 한다"
    assert "s3cret" not in r.stdout + r.stderr, "토큰이 운영 출력에 새면 안 된다"


def test_어긋나지_않으면_아무것도_안_한다(fake):
    """dev 그대로 — 8013 = 8013. 여기서 재프로비저닝을 부르면 매 실행 게이트웨이를 재기동한다."""
    root, gw = fake
    (root / "SignalForge" / ".env").write_text("MCP_PORT=8013\n", encoding="utf-8")
    (gw / "gateway_config.json").write_text('{"signalforge": {"url": "http://127.0.0.1:8013/mcp"}}',
                                            encoding="utf-8")
    blk = _block("  DRIFT=\"\"", "  if [ -n \"$MISSING\" ]; then")
    r = _run(blk + '\necho "MISSING=[$MISSING]"', {"GW_DIR": str(gw), "MISSING": "ai-data-hub"})
    assert "MISSING=[ai-data-hub]" in r.stdout, r.stdout


def test_재기동해도_주소에_아무것도_없으면_크게_말한다(fake):
    """서비스를 띄워도 게이트웨이가 아는 주소에 아무것도 없으면 주소가 틀린 것이다 — 재기동은 답이 아니다."""
    root, gw = fake
    (gw / "gateway_config.json").write_text(
        '{"signalforge": {"url": "http://127.0.0.1:1/mcp"}, "ai-data-hub": {"url": "http://127.0.0.1:2/mcp"}}',
        encoding="utf-8")
    blk = _block("    # 서비스를 띄운 뒤에도 **게이트웨이가 아는 주소**", "  fi\nfi\n")
    stubs = ('http_code() { curl -sk -m "${2:-4}" -o /dev/null -w \'%{http_code}\' "$1" 2>/dev/null; }\n'
             'bad() { echo "BAD $*"; }\n')
    r = _run(stubs + blk, {"GW_DIR": str(gw), "DOWN": "signalforge heax-foo"})
    assert r.returncode == 0, r.stderr
    assert "BAD signalforge: 게이트웨이 설정 주소 http://127.0.0.1:1/mcp 에 아무것도 없다" in r.stdout, r.stdout
    assert "ai-data-hub" not in r.stdout, "다운 목록에 없는 백엔드는 보지 않는다"
    assert "heax-foo" not in r.stdout, "heax 앱은 최상위 키가 아니다 — 건너뛴다"
