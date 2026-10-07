# update-all §5 의 기대 백엔드 — 게이트웨이가 그 박스에서 등재하는 것만, 등재하는 것은 빠짐없이 기대하는지(8·9·10차 요청 #9)
"""왜 — `gateway_config.json` 은 gitignore 라 pull 로 오지 않는다. update-all 의 기대 목록에 없는 백엔드는 config 에서 빠져도
"빠진 백엔드 없음" 초록이고, 거꾸로 게이트웨이가 등재하지 않을 백엔드를 기대하면 매 실행 재프로비저닝을 헛돌린다
(게이트웨이·에이전트서버가 그때마다 내려갔다 올라온다). 두 방향을 모두 고정한다.

판정 블록·`calc_missing`·provision.env 소싱 줄을 **원문 그대로** 떼어 임시 박스(형제 리포·게이트웨이 디렉터리는 지어낸 것)에서
돌린다. 실물 gateway_config.json·provision.env 는 읽지 않는다.
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
BASE = ["ai-data-hub", "signalforge", "hwax-deliberation"]


def _fn(name: str) -> str:
    i = UA.index(f"{name}() {{")
    return UA[i:UA.index("\n}\n", i) + 3]


def _between(start: str, end: str) -> str:
    i = UA.index(start)
    return UA[i:UA.index(end, i) + len(end)]


def _expect(tmp_path: Path, *, have: list[str], siblings: dict | None = None, prov_env: str | None = None,
            pre: str = "") -> tuple[list[str], str]:
    """update-all 이 하는 순서 그대로 — 형제 리포 찾기 → 판정 블록 → (§5) provision.env 소싱 → calc_missing.
    돌려주는 것은 (빠졌다고 본 백엔드, 화면 출력)."""
    parent = tmp_path / "box"
    repo = parent / "HWAXPortal"; (repo / "infra").mkdir(parents=True, exist_ok=True)
    (repo / "backend/config").mkdir(parents=True, exist_ok=True)
    (repo / "infra/.env").write_text("")
    (repo / "backend/config/routes.env").write_text("")
    gw = parent / "HWAXMcpGateway"; gw.mkdir(exist_ok=True)
    if prov_env is not None:
        (gw / "provision.env").write_text(prov_env)
    for rel, text in (siblings or {}).items():
        f = parent / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)
    h = json.dumps({"backends": dict.fromkeys(have, True)})
    script = "\n".join([
        "set -uo pipefail",                      # update-all 과 같은 셸 옵션
        f'SELF_REPO="{repo}"; PARENT="{parent}"; ROUTES_ENV="{repo}/backend/config/routes.env"; GW_DIR="{gw}"',
        "hwax_skip() { printf '○ %s — %s / 켜려면: %s\\n' \"$1\" \"$2\" \"$3\"; }",
        _between("find_repo() {", "done; }\n"),
        _between('KNOX_DIR="$(find_repo HWAXKnoxBridge)"', "\n"),
        _fn("_envfile_value"), _fn("_ra_envv"), pre,
        _between("# RA 사람별 위임(ste 방식, docs/sso-delegation) — 같은 자리에서 읽되", "\n# ── 5) 게이트웨이 config 정합"),
        _between('  PROV_ENV="${GW_DIR:+$GW_DIR/provision.env}"', '. "$PROV_ENV"\n'),
        _fn("calc_missing"),
        "MXWP_UP=0; STE_ROUTED=0",
        f"printf 'MISSING=[%s]\\n' \"$(calc_missing '{h}')\"",
    ])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path / "home")})
    assert r.returncode == 0 and "unbound variable" not in r.stderr, r.stderr
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("MISSING=[")]
    assert len(line) == 1, r.stdout + r.stderr
    return line[0][len("MISSING=["):-1].split(), r.stdout


def test_아무것도_없는_박스의_기대_목록은_종전_그대로다(tmp_path):
    """넓히면 소음이 되고 소음은 묻힌다 — dev(형제 리포·토큰 없음)에서 기대가 늘지 않는다."""
    missing, _ = _expect(tmp_path, have=[])
    assert missing == sorted(BASE)
    assert _expect(tmp_path, have=BASE)[0] == []


# ── #9 Knox 브리지 ───────────────────────────────────────────────────────────
KNOX = {"HWAXKnoxBridge/config/secrets.yaml": "# 지어낸 설정\n"}


def test_knox_브리지가_있는_박스에서_빠지면_빠졌다고_한다(tmp_path):
    """**이 시험이 #9 의 이유다** — 기대 목록에 없으면 챗의 메일·메신저 도구 6개가 통째로 사라져도 초록이다."""
    missing, out = _expect(tmp_path, have=BASE, siblings=KNOX)
    assert missing == ["knox-bridge"]
    assert "Knox 브리지" not in out, "기대하는 박스에서는 '안 켠 기능' 으로 적지 않는다"
    assert _expect(tmp_path, have=BASE + ["knox-bridge"], siblings=KNOX)[0] == []


def test_knox_리포나_설정이_없는_박스에서는_기대하지_않고_안_켠_기능으로_남긴다(tmp_path):
    """무조건 기대하면 브리지가 없는 박스(dev)가 매 실행 헛된 재프로비저닝을 돈다."""
    missing, out = _expect(tmp_path / "none", have=BASE)
    assert missing == [] and "○ Knox 브리지" in out and "켜려면" in out
    missing, out = _expect(tmp_path / "nocfg", have=BASE, siblings={"HWAXKnoxBridge/README.md": "x"})
    assert missing == [] and "○ Knox 브리지" in out, "리포만 있고 config/secrets.yaml 이 없으면 아직 안 쓰는 박스다"
