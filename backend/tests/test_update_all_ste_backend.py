# ste 백엔드가 게이트웨이 config 에서 빠져도 **초록이 뜨던** 구멍을 막는다
"""왜 — `gateway_config.json` 은 gitignore 라 git pull 로 안 온다. 그래서 박스마다
`provision-config.sh` 가 만드는데, update-all 의 **기대 백엔드 목록**에 없는 백엔드는
빠져 있어도 "빠진 백엔드 없음" 초록을 받고 재프로비저닝이 안 돈다.

그러면 도구 목록에서 ste 가 통째로 사라지는데 게이트는 전부 초록이다 — 이 스택이 이미
같은 이유로 `hwax-deliberation` 을 기대 목록에 넣었다(그때는 심의 진입점이 0개가 됐다).

⚠ 그렇다고 **무조건** 기대하면 ste 를 안 쓰는 박스에서 가짜 경보가 나고, 매 실행마다
헛된 재프로비저닝이 돈다. 그래서 `ARP_BASE` 와 같은 방식을 쓴다 — **`ste=` 라우트가
설정돼 있으면 이 박스가 쓴다**는 신호로 본다.

두 번째 구멍도 같이 막는다. `provision.env` 는 `. ` 로 소싱만 하므로 자식 프로세스가 못
본다 — 그래서 update-all 이 키를 하나씩 명시해 넘기는데, 거기 `STE_SSO_SECRET` 이 없었다.
없으면 `per_user_sso["ste"]` 가 아예 안 생기고 ste 호출이 **서비스 계정**으로 나가,
잡 소유자가 한 명으로 뭉친다.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPDATE_ALL = ROOT / "infra" / "scripts" / "update-all.sh"
SRC = UPDATE_ALL.read_text(encoding="utf-8")


def _calc_missing(have: list[str], env: dict) -> list[str]:
    """update-all 의 판정 파이썬을 **원문 그대로** 떼어 돌린다(복제하면 뜻이 갈린다)."""
    body = SRC[SRC.index("import json, os\nh = json.loads"):]
    body = body[:body.index("\nPY\n")]
    payload = '{"backends": {' + ", ".join(f'"{b}": {{}}' for b in have) + "}}"
    p = subprocess.run(["python3", "-c", body], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "H": payload,
                            "RAT": "", "ODB": "", "ARP": "", "MXWP_UP": "0", **env})
    assert p.returncode == 0, p.stderr
    return p.stdout.split()


BASE = ["ai-data-hub", "signalforge", "hwax-deliberation"]


def test_ste_is_expected_when_the_box_routes_it():
    """이 시험이 이 파일의 이유다 — 없으면 빠져 있어도 초록이 뜬다."""
    assert "ste" in _calc_missing(BASE, {"STE_ROUTED": "1"})
    assert "ste" not in _calc_missing(BASE + ["ste"], {"STE_ROUTED": "1"})


def test_ste_is_not_expected_on_a_box_that_does_not_route_it():
    """**반대쪽도 고정한다.** 무조건 기대하면 안 쓰는 박스가 매 실행 헛된 재프로비저닝을 돈다."""
    for env in ({"STE_ROUTED": "0"}, {"STE_ROUTED": ""}, {}):
        assert "ste" not in _calc_missing(BASE, env), env


def test_the_baseline_expectations_did_not_change():
    """ste 를 더하면서 다른 기대가 흔들리지 않았는지 — 넓히면 소음이 되고 소음은 묻힌다."""
    assert _calc_missing([], {"STE_ROUTED": "0"}) == sorted(BASE)


# ── 라우트 신호 ─────────────────────────────────────────────────────────────
def _ste_routed(tmp_path: Path, local: str | None, base: str | None) -> str:
    """스크립트의 `_ste_routed` 를 원문 그대로 떼어 가짜 라우트 파일에 물린다."""
    fn = SRC[SRC.index("_ste_routed() {"):]
    fn = fn[:fn.index("\n}\n") + 3]
    cfg = tmp_path / "backend" / "config"
    cfg.mkdir(parents=True)
    if local is not None:
        (cfg / "routes.local.env").write_text(local, encoding="utf-8")
    base_f = tmp_path / "routes.env"
    if base is not None:
        base_f.write_text(base, encoding="utf-8")
    script = f'SELF_REPO="{tmp_path}"; ROUTES_ENV="{base_f}"\n{fn}\n_ste_routed'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def test_an_active_route_counts(tmp_path):
    assert _ste_routed(tmp_path, "ste=http://x:15810/\n", None) == "1"
    assert _ste_routed(tmp_path / "b", None, "ste=http://x:15810/\n") == "1"


def test_a_commented_route_does_not_count(tmp_path):
    """예시로 적어 둔 주석을 '쓴다' 로 읽으면 모든 박스가 ste 를 기대하게 된다 —
    routes.env 에는 실제로 `#ste=` 예시 줄이 들어 있다."""
    assert _ste_routed(tmp_path, "#ste=http://x:15810/\n", None) == "0"
    assert _ste_routed(tmp_path / "b", None, "  # ste=http://x:15810/\n") == "0"


def test_an_empty_value_does_not_count(tmp_path):
    assert _ste_routed(tmp_path, "ste=\n", None) == "0"


def test_no_routes_file_at_all(tmp_path):
    assert _ste_routed(tmp_path, None, None) == "0"


def test_the_real_routes_file_has_the_commented_example():
    """위 시험이 진짜 상황을 본다는 근거 — 이 리포의 routes.env 에 주석 예시가 있다."""
    txt = (ROOT / "backend" / "config" / "routes.env").read_text(encoding="utf-8")
    assert re.search(r"^\s*#\s*ste=", txt, re.M), "주석 예시가 없다면 이 시험의 전제가 바뀐 것이다"


# ── 프로비저너로 넘어가는 값 ────────────────────────────────────────────────
def test_the_secret_is_passed_to_the_provisioner():
    """provision.env 는 소싱만 되므로 자식이 못 본다 — 여기서 명시해 넘겨야 한다."""
    call = SRC[SRC.index("bash provision-config.sh --force"):]
    block = SRC[:SRC.index("bash provision-config.sh --force")]
    block = block[block.rindex("( cd \"$GW_DIR\""):]
    assert "STE_SSO_SECRET=" in block, (
        "provision-config.sh 에 STE_SSO_SECRET 이 안 넘어간다 — per_user_sso['ste'] 가 안 생기고 "
        "ste 호출이 서비스 계정으로 나간다")
    assert "STE_MCP_URL=" in block
    assert call  # 호출 자체가 남아 있는지


def test_the_secret_is_read_from_infra_env():
    """update-all 은 infra/.env 를 통째로 소싱하지 않는다 — 필요한 키만 읽어 온다."""
    assert re.search(r"sed -n 's/\^STE_SSO_SECRET=//p'", SRC), "infra/.env 에서 읽어 오는 줄이 없다"


def test_the_secret_is_not_read_with_a_default_expansion():
    """`${SECRET:-…}` 관용구를 쓰지 않는다 — 허용하면 다음 사람의 **리터럴 기본값**이 통과하고,
    비어 있는 박스가 공개값으로 뜬다. 이 리포의 비밀 가드가 그래서 그 꼴을 통째로 막는다."""
    assert "${STE_SSO_SECRET:-$" not in SRC, "비밀에 기본값 확장을 썼다"
    assert re.search(r'if \[ -z "\$\{STE_SSO_SECRET:-\}" \]', SRC), \
        "빈 값 검사는 명시적 if 로 한다"
