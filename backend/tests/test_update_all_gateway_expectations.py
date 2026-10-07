# update-all §5 의 기대 백엔드 — 게이트웨이가 그 박스에서 등재하는 것만, 등재하는 것은 빠짐없이 기대하는지(8·9·10차 요청 #9·#10·#11)
"""왜 — `gateway_config.json` 은 gitignore 라 pull 로 오지 않는다. update-all 의 기대 목록에 없는 백엔드는 config 에서 빠져도
"빠진 백엔드 없음" 초록이고, 거꾸로 게이트웨이가 등재하지 않을 백엔드를 기대하면 매 실행 재프로비저닝을 헛돌린다
(게이트웨이·에이전트서버가 그때마다 내려갔다 올라온다). 두 방향을 모두 고정한다.

판정 블록·`calc_missing`·provision.env 소싱 줄을 **원문 그대로** 떼어 임시 박스(형제 리포·게이트웨이 디렉터리는 지어낸 것)에서
돌린다. 실물 gateway_config.json·provision.env 는 읽지 않는다.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

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
            gw_config: dict | None = None, pre: str = "") -> tuple[list[str], str]:
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
    if gw_config is not None:
        (gw / "gateway_config.json").write_text(json.dumps(gw_config))
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


# ── #10 ARP — 인증이 켜진 뒤(2026-10-01)로는 주소와 토큰이 **둘 다** 있어야 게이트웨이가 등재한다 ─────────────
ARP_ENV = "ARP_BASE=http://203.0.113.20:3001\nARP_TOKEN=arp-test-token\n"


def test_arp_는_주소와_토큰이_둘_다_있는_박스에서만_기대한다(tmp_path):
    missing, out = _expect(tmp_path / "both", have=BASE, prov_env=ARP_ENV)
    assert missing == ["arp"]
    assert "arp-test-token" not in out, "토큰은 화면에 남지 않는다"
    assert _expect(tmp_path / "have", have=BASE + ["arp"], prov_env=ARP_ENV)[0] == []


def test_arp_토큰이_없으면_기대하지_않는다(tmp_path):
    """**짝이 어긋나던 자리** — 게이트웨이는 토큰 없이는 arp 를 등재하지 않는다. 주소만 보고 기대하면 ARP_BASE 가 있는 박스가
    매 실행 arp 를 '빠짐' 으로 보고 재프로비저닝을 헛돌린다(게이트웨이·에이전트서버가 그때마다 내려갔다 올라온다)."""
    assert _expect(tmp_path / "base", have=BASE, prov_env="ARP_BASE=http://203.0.113.20:3001\n")[0] == []
    assert _expect(tmp_path / "token", have=BASE, prov_env="ARP_TOKEN=arp-test-token\n")[0] == [], "주소가 없어도 등재하지 않는다"
    assert _expect(tmp_path / "empty", have=BASE, prov_env="ARP_BASE=http://203.0.113.20:3001\nARP_TOKEN=\n")[0] == []


def test_arp_주소만_있고_토큰이_없으면_안_켠_기능으로_남긴다(tmp_path):
    """토큰이 없으면 arp 백엔드가 조용히 빠진다 — 무엇을 적으면 켜지는지와 함께 장부에 남는다(RA 의 RAT_TOKEN 과 같다)."""
    _, out = _expect(tmp_path / "base", have=BASE, prov_env="ARP_BASE=http://203.0.113.20:3001\n")
    assert "○ ARP MCP 도구" in out and "ARP_TOKEN=<값>" in out
    _, out = _expect(tmp_path / "1f", have=BASE, pre='ARP_BASE="http://203.0.113.20:3001"')
    assert "○ ARP MCP 도구" in out, "1f 가 ARP_HOST 로 주소를 세운 박스도 같다"
    for name, env in (("both", ARP_ENV), ("none", ""), ("token", "ARP_TOKEN=arp-test-token\n")):
        _, out = _expect(tmp_path / name, have=BASE, prov_env=env)
        assert "ARP MCP 도구" not in out, name


def test_arp_주소는_1f_가_ARP_HOST_로_정한_값이어도_된다(tmp_path):
    """1f 는 ARP_BASE 를 셸 변수로 세운다(provision.env 에 못 적은 박스에서도 남는다). 토큰은 provision.env 에서 온다."""
    missing, _ = _expect(tmp_path, have=BASE, prov_env="ARP_TOKEN=arp-test-token\n", pre='ARP_BASE="http://203.0.113.20:3001"')
    assert missing == ["arp"]


def _reprovision_cmd() -> str:
    i = UA.index('( cd "$GW_DIR" && export PER_USER_SSO_APPS ')
    return UA[i:UA.index("--force )", i) + len("--force )")]


def _provisioner_sees(tmp_path: Path, vals: dict) -> dict:
    """§5 의 재프로비저닝 호출을 원문 그대로 돌려, 대역 provision-config.sh 가 **자식 프로세스로서** 본 값을 돌려준다."""
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "provision-config.sh").write_text(
        "#!/usr/bin/env bash\n" + "".join(f'printf "%s=%s\\n" {k} "${{{k}-<unset>}}" >> "$PWD/ran.marker"\n' for k in vals))
    # 부모 셸 변수일 뿐 export 하지 않는다 — provision.env 는 소싱만 되므로 사슬이 넘겨야 자식이 본다
    script = f'set -u; GW_DIR="{gw}"\n' + "".join(f'{k}="{v}"\n' for k, v in vals.items()) + f"{_reprovision_cmd()}\necho rc=$?"
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert "rc=0" in r.stdout, r.stderr
    return dict(ln.split("=", 1) for ln in (gw / "ran.marker").read_text().splitlines())


def test_재프로비저닝이_ARP_토큰을_게이트웨이에_넘긴다(tmp_path):
    """provision-config.sh 는 provision.env 를 스스로 읽지 않는다. 넘기지 않으면 토큰을 적어도 arp 가 등재되지 않고,
    update-all 은 기대하므로 매 실행 재프로비저닝 → '재프로비저닝 후에도 누락' 이 된다(ODB_HUB_TOKEN 이 그렇게 빠졌었다)."""
    vals = {"ARP_BASE": "http://203.0.113.20:3001", "ARP_TOKEN": "arp-test-token"}
    assert _provisioner_sees(tmp_path, vals) == vals


# ── #11 SmartTwinMCP — 게이트웨이는 주소가 **설정된** 박스에서만 등재한다(docs/change-request-8-10 D-4) ─────────────
# 등재 조건: provision.env 의 SMARTTWIN_MCP_URL, 또는 지금 config 에 든 기본값이 아닌 주소. 기본값은 옛 프로비저너가 무조건 박던 값이다.
ST_DEFAULT = "http://127.0.0.1:5013/mcp"
ST_NAME = "smart-twin-mcp"


def test_smarttwin_주소를_적은_박스에서_빠지면_빠졌다고_한다(tmp_path):
    """dev 의 모양 — 같은 박스 :5013 에서 듣고 있고 provision.env 에 그 주소를 적었다. 기대하지 않으면 config 에서 빠져도
    (도구 18종이 통째로 사라져도) 초록이다."""
    env = f"SMARTTWIN_MCP_URL={ST_DEFAULT}\n"
    missing, out = _expect(tmp_path / "gone", have=BASE, prov_env=env)
    assert missing == [ST_NAME] and "SmartTwinMCP" not in out
    assert _expect(tmp_path / "have", have=BASE + [ST_NAME], prov_env=env, gw_config={ST_NAME: {"url": ST_DEFAULT}})[0] == []


def test_smarttwin_옛_기본_주소로만_남은_박스에서는_기대하지_않는다(tmp_path):
    """cae00 의 모양 — 띄운 적이 없는데 옛 프로비저너가 기본 주소로 등재해 가짜 DOWN 이 떠 있었다. 게이트웨이는 다음
    재프로비저닝에서 이 항목을 뺀다. 여기서 기대하면 그 뒤로 매 실행 '빠짐' → 재프로비저닝이 헛돈다."""
    cfg = {ST_NAME: {"url": ST_DEFAULT, "transport": "streamable_http"}}
    missing, out = _expect(tmp_path / "before", have=BASE + [ST_NAME], gw_config=cfg)
    assert missing == []
    assert "○ SmartTwinMCP" in out and "다음 재프로비저닝에서" in out and "SMARTTWIN_MCP_URL=" in out, "빠질 것을 미리, 켜는 법과 함께 알린다"
    missing, _ = _expect(tmp_path / "after", have=BASE, gw_config={})      # 게이트웨이가 뺀 뒤
    assert missing == []


def test_smarttwin_config_에_기본값이_아닌_주소가_있으면_기대한다(tmp_path):
    """사람이 config 에 직접 옮겨 적은 주소는 게이트웨이가 이어받는다 — 그 박스에서 빠지면 빠졌다고 해야 한다."""
    cfg = {ST_NAME: {"url": "http://203.0.113.40:5013/mcp"}}
    missing, out = _expect(tmp_path, have=BASE, gw_config=cfg)
    assert missing == [ST_NAME] and "SmartTwinMCP" not in out


def test_smarttwin_설정이_전혀_없는_박스는_안_켠_기능으로_남긴다(tmp_path):
    for name, cfg in (("nocfg", None), ("empty", {}), ("broken", None)):
        if name == "broken":
            d = tmp_path / name / "box/HWAXMcpGateway"; d.mkdir(parents=True); (d / "gateway_config.json").write_text("{깨진 json")
        missing, out = _expect(tmp_path / name, have=BASE, gw_config=cfg)
        assert missing == [] and "○ SmartTwinMCP" in out and "켜려면" in out, name


def test_재프로비저닝이_SmartTwinMCP_주소를_게이트웨이에_넘긴다(tmp_path):
    """넘기지 않으면 provision.env 에 적어도 게이트웨이는 못 보고(직전 config 의 기본 주소는 이어받지 않는다) 백엔드를 뺀다 —
    update-all 은 기대하므로 매 실행 재프로비저닝이 헛돈다."""
    vals = {"SMARTTWIN_MCP_URL": ST_DEFAULT}
    assert _provisioner_sees(tmp_path, vals) == vals


def test_기본_주소는_게이트웨이_프로비저너가_아는_그_값이다():
    """두 리포가 같은 글자를 '기본값' 으로 봐야 조건이 같다 — 한쪽만 바뀌면 기대와 등재가 갈린다."""
    assert f'_ST_DEFAULT="{ST_DEFAULT}"' in UA
    prov = ROOT.parent / "HWAXMcpGateway" / "provision-config.sh"
    if not prov.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    near = [ln for ln in prov.read_text(encoding="utf-8").splitlines() if re.search(r"smart-twin-mcp|SMARTTWIN_MCP_URL|_ST_", ln)]
    assert any(ST_DEFAULT in ln for ln in near), "게이트웨이 프로비저너의 smart-twin-mcp 기본 주소가 바뀌었다 — update-all 의 _ST_DEFAULT 와 맞춘다"


def _gateway_rule():
    """게이트웨이 프로비저너의 등재 조건 두 줄(`_ST_DEFAULT = …` · `_ST_URL = …`)을 원문에서 꺼낸다. 아직 조건부 등재가 아닌 판이면 None."""
    prov = ROOT.parent / "HWAXMcpGateway" / "provision-config.sh"
    if not prov.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    src = prov.read_text(encoding="utf-8")
    default = re.search(r'^_ST_DEFAULT = "([^"]+)"$', src, re.M)
    rule = re.search(r"^_ST_URL = (.+)$", src, re.M)
    if not (default and rule):
        return None
    return default.group(1), rule.group(1)


@pytest.mark.parametrize("env_url,prev_url", [
    (None, None), (None, ""), (None, ST_DEFAULT), (None, "http://203.0.113.40:5013/mcp"),
    (ST_DEFAULT, None), (ST_DEFAULT, ST_DEFAULT), ("http://203.0.113.40:5013/mcp", ST_DEFAULT),
    (None, ST_DEFAULT + "/"),                    # 글자가 다르면 두 쪽 모두 '설정한 주소' 로 본다
])
def test_기대_조건이_게이트웨이의_등재_조건과_같다(tmp_path, env_url, prev_url):
    """**정본은 게이트웨이다** — 그 조건식을 원문에서 꺼내 같은 입력으로 돌려, update-all 의 셸 판정과 맞춰 본다.
    한쪽만 기대하면 매 실행 재프로비저닝이 헛돌고, 한쪽만 등재하면 빠져도 초록이다."""
    got = _gateway_rule()
    if got is None:
        pytest.skip("옆의 게이트웨이가 아직 smart-twin-mcp 를 무조건 등재하는 판이다")
    default, expr = got
    assert default == ST_DEFAULT
    env = {"SMARTTWIN_MCP_URL": env_url} if env_url is not None else {}
    registers = bool(eval(expr, {"__builtins__": {}}, {"e": env, "_ST_PREV": prev_url, "_ST_DEFAULT": default}))  # noqa: S307
    cfg = None if prev_url is None else {ST_NAME: {"url": prev_url}}
    missing, _ = _expect(tmp_path, have=BASE, gw_config=cfg,
                         prov_env=None if env_url is None else f"SMARTTWIN_MCP_URL={env_url}\n")
    assert (ST_NAME in missing) is registers, (env_url, prev_url, expr)
