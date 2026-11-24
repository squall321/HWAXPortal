# 상호작용 기록의 박스 배선(docs/interaction-data) — update-all ○ 줄 · 상태판 줄 · 데이터 레지스트리 · start.sh 넘김 · 백업 · env 예시를 실물 스크립트로
"""스위치 둘(포털 INTERACTIONS_ENABLED · 게이트웨이 GATEWAY_INTERACTION_CAPTURE)은 기본 꺼짐이고 켜는 것은 사람이다(회사 규정 확인 뒤).
update-all 은 고쳐 쓰지 않고 안 켠 것을 ○ 로 남긴다. 원문은 이 박스 안에만 — 레지스트리 클래스는 sync: none, 백업은 backup-local portal 이다."""
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.test_status_board import Lay, _free_port, _svc

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
LEDGER_LIB = ROOT / "infra/scripts/lib/skip-ledger.sh"
PORTAL_NAME = "상호작용 기록 — 포털 원장 · 수집기(INTERACTIONS_ENABLED)"
GW_NAME = "상호작용 기록 — 게이트웨이 원문 수집(GATEWAY_INTERACTION_CAPTURE)"


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{[^\n]*\n.*?^\}}\n", UA)
    assert m, name
    return m.group(0)


def _block() -> str:
    i = UA.index("# ── 3.5i) 상호작용 기록")
    return UA[i:UA.index("# ── 3.5e) 서버 LLM 에 일 맡기기", i)]


def _run(tmp_path: Path, infra: str | None, prov: str | None, *, gw: bool = True) -> tuple[str, list[str]]:
    repo, g = tmp_path / "portal", tmp_path / "gw"
    (repo / "infra").mkdir(parents=True, exist_ok=True)
    g.mkdir(exist_ok=True)
    if infra is not None:
        (repo / "infra/.env").write_text(infra, encoding="utf-8")
    if prov is not None:
        (g / "provision.env").write_text(prov, encoding="utf-8")
    led = tmp_path / "ledger"
    led.write_text("")
    script = (f"set -uo pipefail\n{_fn('_envfile_value')}. '{LEDGER_LIB}'\nHWAX_SKIP_LEDGER='{led}'\n"
              f"SELF_REPO='{repo}'\nGW_DIR='{g if gw else ''}'\n{_block()}\necho '-- 요약'\nhwax_skip_summary\n")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, [ln.split("\t")[0] for ln in led.read_text(encoding="utf-8").splitlines()]


def test_update_all_안_켠_박스는_둘을_안_켠_줄로_남긴다(tmp_path):
    out, led = _run(tmp_path, "PUBLIC_BASE_URL=x\n", "RAT_TOKEN=x\n")
    assert led == [PORTAL_NAME, GW_NAME]
    head, summary = out.split("-- 요약")
    for n in (PORTAL_NAME, GW_NAME):
        assert n in head and n in summary, "즉시 한 줄 + 끝 요약에 다시"
    assert head.count("켜려면:") == 2 and "INTERACTIONS_ENABLED=1" in head and "GATEWAY_INTERACTION_CAPTURE=1" in head
    assert "회사 개인정보 · 보안 규정 확인" in head and "docs/interaction-data/contract.md" in head


def test_update_all_켠_것은_말하지_않고_파일이_없으면_꺼짐이다(tmp_path):
    out, led = _run(tmp_path, 'export INTERACTIONS_ENABLED="true"  # 켬\n', "GATEWAY_INTERACTION_CAPTURE=On\n")
    assert led == [] and out.strip() == "-- 요약", out
    _, led = _run(tmp_path / "b", None, None)
    assert led == [PORTAL_NAME, GW_NAME]


@pytest.mark.parametrize("line", ["INTERACTIONS_ENABLED=0", "INTERACTIONS_ENABLED=", "# INTERACTIONS_ENABLED=1",
                                  "INTERACTIONS_ENABLED=1\nINTERACTIONS_ENABLED=0"])
def test_update_all_켬_낱말이_아니면_꺼짐이다(tmp_path, line):
    _, led = _run(tmp_path, line + "\n", "GATEWAY_INTERACTION_CAPTURE=1\n")
    assert led == [PORTAL_NAME]


def test_update_all_게이트웨이를_모르는_박스는_포털만_말하고_고쳐_쓰지_않는다(tmp_path):
    _, led = _run(tmp_path, "INTERACTIONS_ENABLED=0\n", "RAT_TOKEN=x\n", gw=False)
    assert led == [PORTAL_NAME]
    assert (tmp_path / "portal/infra/.env").read_text(encoding="utf-8") == "INTERACTIONS_ENABLED=0\n"
    blk = _block()
    assert "_upsert_kv" not in blk and "sed -i" not in blk and ">>" not in blk, "읽기만 한다"
    i = UA.index(blk)
    assert UA.index("_envfile_value() {") < i < UA.index('hr "4) update-sites') and UA.index('GW_DIR="$(find_repo HWAXMcpGateway)"') < i


# ── 상태판 줄 ────────────────────────────────────────────────────────────────
def test_상태판은_켠_박스에서만_포털_상호작용_수집_줄을_싣는다(tmp_path):
    lay = Lay(tmp_path)
    port = _free_port()
    lay.manifest([_svc("portal", f"http://127.0.0.1:{port}/health", tier=0)])
    url = f"http://127.0.0.1:{port}/health/interactions"
    lay.infra_env("STATUS_BOARD=1\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    assert url not in lay.endpoints() and "상호작용 기록을 켜지 않았다" in r.stdout
    lay.infra_env("STATUS_BOARD=1\nINTERACTIONS_ENABLED=1\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    ep = lay.endpoints()[url]
    assert ep["group"] == "portal" and ep["conditions"] == ["[CONNECTED] == true", "[STATUS] == 200", "[BODY].ok == true"]


# ── 데이터 레지스트리 · start.sh · 백업 · env 예시 ─────────────────────────────────
def test_원장은_레지스트리에_sync_none_으로_있고_start_sh_가_경로와_스위치를_값이_있을_때만_넘긴다():
    man = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}
    cls = man["portal"]["data"]["classes"]["interactions"]
    assert cls == {"kind": "sqlite", "path": "svc/portal/interactions.sqlite", "current": "backend/data/interactions.sqlite",
                   "env": "INTERACTIONS_STORE_PATH", "fs": "local", "sync": "none", "needs_bind": True}, "원문은 박스 사이로 옮기지 않는다"
    start = (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8")
    assert re.search(r"for k in USER_STORE_PATH[^;]*INTERACTIONS_STORE_PATH; do\n\s+\[ -n \"\$\{!k:-\}\" \] && DATA_ENVS\+=", start)
    assert re.search(r"for k in INTERACTIONS_ENABLED INTERACTIONS_INGEST_S; do\n\s+\[ -n \"\$\{!k:-\}\" \] && IX_ENVS\+=", start)
    assert '${IX_ENVS[@]+"${IX_ENVS[@]}"}' in start.split('"$APPTAINER" instance start', 1)[1].split('"$PORTAL_SIF"', 1)[0]


def test_백업은_portal_대상에_상호작용_원장을_담는다():
    b = (ROOT / "infra/scripts/backup-local.sh").read_text(encoding="utf-8")
    blk = b[b.index("if want portal; then"):b.index("if want gateway; then")]
    assert '"${INTERACTIONS_STORE_PATH:-}"' in blk and '"data/interactions.sqlite")' in blk and "sys.argv[3:9]" in blk


def test_env_예시는_스위치를_주석으로만_적는다():
    ex = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    assert "# INTERACTIONS_ENABLED=1" in ex and "# INTERACTIONS_INGEST_S=60" in ex
    assert not re.search(r"(?m)^INTERACTIONS_", ex), "env-sync 가 박스의 .env 로 옮겨 적지 않게 — 기본 꺼짐"
