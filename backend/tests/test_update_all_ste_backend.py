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
import json
import os
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


# ── ste 자격 중계 판정 — **가짜 초록을 냈던 자리** ──────────────────────────
#
# 처음엔 "401 이면 설정됨" 으로 읽었다. 그런데 dev 의 옛 ste 는 그 경로를 몰라서 **인증
# 미들웨어**가 401 을 냈고, 겉모습이 핸들러의 401 과 똑같았다 — 아직 배포도 안 된 상태를
# "양쪽 설정됨" 초록으로 보고할 참이었다. 이 세션에서 내내 잡아 온 바로 그 모양이다.
#
# 가르는 근거는 `www-authenticate` 헤더다(실측: 미들웨어는 붙이고, HTTPException 은 안 붙인다).
def _verdict(code: str, mw: str, *, secret: str = "s3cr3t", verify: str = "204") -> str:
    """update-all 의 case 문을 **원문 그대로** 떼어 돌린다(복제하면 뜻이 갈린다).

    2차 verify 가 curl 로 루프백을 치므로 `curl` 을 셸 함수로 가짜화한다 — 시험이 실물 포털을 치면 안 된다.
    """
    i = SRC.index('  case "${_ste_sso_code:-000}/$_ste_sso_mw" in')
    block = SRC[i:SRC.index("\n  esac", i) + len("\n  esac")]
    script = "\n".join([
        'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }', 'fail() { echo "FAIL:$*"; }',
        f'curl() {{ printf "%s" "{verify}"; }}',
        f'STE_SSO_SECRET="{secret}"', f'_ste_sso_code="{code}"', f'_ste_sso_mw="{mw}"', block,
    ])
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout.splitlines()[0].split(":", 1)[0]


def test_only_a_handler_401_counts_as_configured():
    """핸들러가 낸 401(헤더 없음)이고 **verify 가 204** 여야 초록이다."""
    assert _verdict("401", "0", verify="204") == "OK"


# ── 2차 verify — "설정됨" 과 "같은 값" 은 다르다 ─────────────────────────────
# 포털 start.sh 와 헤드 installer 가 각자 난수를 만든다. 둘이 다르면 로그인은 되는데 ste 만 401 인데,
# 1차 프로브(아무 값 → 401)는 그 상태를 "설정됨" 초록으로 읽었다(2026-09-24 적대 검토).
def test_mismatched_secret_is_a_hard_fail():
    """**이 시험이 그 가짜 초록을 막는다** — 핸들러 401 이어도 verify 401 이면 fail."""
    assert _verdict("401", "0", verify="401") == "FAIL"


def test_old_head_without_verify_is_not_green():
    """verify 를 모르는 옛 판(404)은 일치 여부를 모른다 — 초록이 아니라 경고다."""
    assert _verdict("401", "0", verify="404") == "BAD"


def test_empty_portal_secret_cannot_be_green():
    assert _verdict("401", "0", secret="", verify="204") == "BAD"


def test_the_verify_step_sends_the_real_secret_to_loopback_only():
    """실제 값은 verify 호출에만, 그리고 127.0.0.1 로만 간다 — 박스 밖으로 안 나간다."""
    i = SRC.index("_ste_vfy=")
    block = SRC[i:SRC.index('case "$_ste_vfy"', i)]
    assert "$STE_SSO_SECRET" in block and "127.0.0.1:8088/ste/api/auth/sso/verify" in block


# ── 게이트웨이 ste 세션·15812·권한 정책 — "죽어도 초록" 이던 자리 ─────────────────
def _run_block(start_marker: str, end_marker: str, *, env_lines: list[str], health: dict, curl_code: str = "000") -> str:
    i = SRC.index(start_marker)
    block = SRC[i:SRC.index(end_marker, i)]
    script = "\n".join([
        'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }', 'fail() { echo "FAIL:$*"; }',
        f'curl() {{ printf "%s" "{curl_code}"; }}',
        "H='" + json.dumps(health) + "'", *env_lines, block,
    ])
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout


def _ste_gw(health: dict, curl_code: str = "000", routed: str = "1") -> str:
    out = _run_block("  # ── ste 가 이 박스에서 쓰이면(STE_ROUTED=1)", "  # ── 포털 권한 정책이",
                     env_lines=[f'STE_ROUTED="{routed}"', 'STE_MCP_URL="http://127.0.0.1:15812/mcp"'],
                     health=health, curl_code=curl_code)
    return out.splitlines()[0].split(":", 1)[0] if out.strip() else ""


def test_gateway_ste_down_is_a_fail_when_routed():
    """/health 는 DOWN 이어도 키를 남긴다 — 값을 봐야 한다(§5 는 키 유무만 본다)."""
    assert _ste_gw({"backends": {"ste": True}}) == "OK"
    assert _ste_gw({"backends": {"ste": False}}) == "FAIL"
    assert _ste_gw({"backends": {}}) == "FAIL"                     # 아예 없어도 fail


def test_gateway_ste_down_hint_points_at_the_tunnel_port():
    """15812 가 안 열려 있으면 ste-tunnel 을 가리켜야 한다 — '매핑된 서비스 없음' 이 아니라."""
    out = _run_block("  # ── ste 가 이 박스에서 쓰이면(STE_ROUTED=1)", "  # ── 포털 권한 정책이",
                     env_lines=['STE_ROUTED="1"', 'STE_MCP_URL="http://127.0.0.1:15812/mcp"'],
                     health={"backends": {"ste": False}}, curl_code="000")
    assert "FAIL" in out and "15812" in out and "ste-tunnel" in out
    # 포트는 살아 있는데 게이트웨이만 못 붙었으면 재기동을 가리킨다(dev 실측: 살아 있으면 406)
    out = _run_block("  # ── ste 가 이 박스에서 쓰이면(STE_ROUTED=1)", "  # ── 포털 권한 정책이",
                     env_lines=['STE_ROUTED="1"', 'STE_MCP_URL="http://127.0.0.1:15812/mcp"'],
                     health={"backends": {"ste": False}}, curl_code="406")
    assert "FAIL" in out and "재기동" in out


def test_gateway_ste_is_not_judged_when_not_routed():
    assert _ste_gw({"backends": {"ste": False}}, routed="0") == ""


def test_unloaded_access_policy_is_a_fail():
    """정책이 안 실리면 전 백엔드가 전원에게 열린다 — 초록으로 지나가면 안 된다."""
    def pol(loaded):
        return _run_block("  # ── 포털 권한 정책이", "\nfi\n",
                          env_lines=[], health={"access_policy_loaded": loaded}).splitlines()[0].split(":", 1)[0]
    assert pol(0) == "FAIL"
    assert pol(7) == "OK"


def test_a_middleware_401_is_not_green():
    """**이 시험이 그 가짜 초록을 막는다** — 옛 판이 떠 있는 것을 설정됨으로 읽으면 안 된다."""
    assert _verdict("401", "1") == "FAIL"


def test_404_means_the_secret_is_unset_on_the_ste_side():
    assert _verdict("404", "0") == "FAIL"
    assert _verdict("404", "1") == "FAIL"


def test_no_response_is_unknown_not_a_failure_of_this_feature():
    """프록시가 죽은 것과 시크릿이 없는 것은 다르다 — 뭉개면 엉뚱한 곳을 고치게 된다."""
    assert _verdict("000", "0") == "BAD"


def test_an_unexpected_code_is_never_green():
    for code in ("200", "403", "500"):
        assert _verdict(code, "0") != "OK", code


def test_the_probe_sends_no_real_secret():
    """비밀을 알 필요도, 로그에 남길 필요도 없다 — 아무 값이나 보내 상태로만 판정한다."""
    i = SRC.index("_ste_sso_hdr=")
    block = SRC[i:SRC.index("_ste_sso_code=", i)]
    assert "probe-not-a-secret" in block
    assert "$STE_SSO_SECRET" not in block, "프로브에 실제 시크릿을 싣지 않는다"


# ── ste 주소를 라우트에서 유도한다 — 손으로 export 하지 않아도 위임이 안 깨지게 ─────────
# 종전에는 STE_SSO_URL 을 환경변수로만 받았다. 그래서 export 없이 update-all 을 돌리면 provision 이
# `127.0.0.1:15810` 기본값으로 **멀쩡하던 VM 주소를 덮어썼다**(dev 실측 2026-09-24 — 그 순간
# ste 위임과 REST 다리가 함께 죽는다). 정본은 이 박스의 `ste=` 라우트 하나다.
def _run_route_derivation(tmp_path, routes_local: str | None, env: dict) -> dict:
    """update-all 에서 `_ste_route_url` + 유도 블록만 **그대로 떼어** 돌린다(사본을 시험하지 않는다)."""
    m = re.search(r"(_ste_route_url\(\) \{.*?\n  fi\nfi\n)", SRC, re.S)
    assert m, "update-all 에서 ste 주소 유도 블록을 못 찾았다 — 이 시험이 낡았다"
    repo = tmp_path / "repo"
    (repo / "backend/config").mkdir(parents=True, exist_ok=True)
    if routes_local is not None:
        (repo / "backend/config/routes.local.env").write_text(routes_local, encoding="utf-8")
    script = (f'SELF_REPO="{repo}"; ROUTES_ENV="{repo}/backend/config/routes.env"\n'
              + m.group(1)
              + '\nprintf "SSO=%s\\nMCP=%s\\n" "${STE_SSO_URL:-}" "${STE_MCP_URL:-}"\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], **env}, timeout=30)
    assert r.returncode == 0, r.stderr
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def test_ste_주소는_라우트에서_유도된다(tmp_path):
    out = _run_route_derivation(tmp_path, "ste=http://203.0.113.10:15810/\n", {})
    assert out["SSO"] == "http://203.0.113.10:15810/api/auth/sso"
    assert out["MCP"] == "http://203.0.113.10:15812/mcp"          # 같은 호스트, MCP 기본 포트


def test_provision_env_가_명시한_값이_유도보다_이긴다(tmp_path):
    """포트를 바꾼 박스는 provision.env 가 정본이다 — 유도가 그것을 덮으면 안 된다."""
    out = _run_route_derivation(tmp_path, "ste=http://203.0.113.10:15810/\n",
                                {"STE_MCP_URL": "http://203.0.113.10:25812/mcp"})
    assert out["MCP"] == "http://203.0.113.10:25812/mcp"
    assert out["SSO"] == "http://203.0.113.10:15810/api/auth/sso"  # 이건 비어 있었으니 유도


def test_라우트가_없으면_아무것도_채우지_않는다(tmp_path):
    """비워 두면 provision 이 자기 규칙(직전값 → 기본값)으로 간다. 여기서 localhost 를 지어내면 안 된다."""
    out = _run_route_derivation(tmp_path, None, {})
    assert out.get("SSO", "") == "" and out.get("MCP", "") == ""
    out = _run_route_derivation(tmp_path, "#ste=http://x/\n", {})       # 주석은 라우트가 아니다
    assert out.get("SSO", "") == ""


def test_접속_설정은_있는데_라우트가_없으면_말한다():
    """VM 은 최신인데 포털 /ste 가 비어 있는 상태를 '안 쓰는 박스' 로 조용히 넘기지 않는다."""
    assert "ste 접속 설정은 있는데" in SRC and "routes.local.env 에" in SRC
