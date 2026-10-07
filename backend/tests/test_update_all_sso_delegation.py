# update-all 이 RA·TestScope 사람별 위임(ste 방식) 값을 infra/.env 에서 읽어 게이트웨이 프로비저닝까지 나르는지(+ TestScope 기대 여부)
"""docs/sso-delegation PLAN §2-2. 운영자가 할 일은 infra/.env 에 비밀 한 줄뿐이어야 한다.
그 한 줄이 조용히 안 닿는 길이 셋 있었다 — 그것을 고정한다.

  1. 읽기 — update-all 은 infra/.env 를 통째로 소싱하지 않는다. 키를 하나씩 읽어야 한다.
  2. 방아쇠 — 위임은 heax_registry 안의 항목이라 /health 에 안 나온다. 빠진 백엔드가 없으면 재프로비저닝이 안 돌아
     비밀을 넣어도 위임이 영영 안 켜진다(ste 는 ste-gateway-check deleg 이 그 자리를 본다).
  3. 전달 — provision.env 는 소싱만 되므로 자식이 못 본다. 대입어 사슬로 하나씩 넘긴다(백틱 주석 금지 — 3라운드 실사고).

그리고 **만들지 않는다**(start.sh 2d) — RA 쪽이 준비되기 전에 비밀이 생기면 게이트웨이가 RA 호출을 전부 거부한다.
TestScope 도 RA 와 같은 두 갈래다 — TESTSCOPE_SSO_SECRET 이 비면 토큰 등록, 있으면 위임(주소는 backend/.env 의 TESTSCOPE_BASE_URL 에서).
백엔드 기대 신호는 위임과 따로, 게이트웨이 provision.env 의 TESTSCOPE_MCP_URL 이다.
블록은 원문 그대로 떼어 돌린다(복제하면 뜻이 갈린다).
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
START = (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8")
SECRET = "ra-secret-0123456789abcdef0123456789"


def _fn(name: str) -> str:
    s = UA[UA.index(f"{name}() {{"):]
    return s[:s.index("\n}\n") + 3]


def _derive_block() -> str:
    i = UA.index("# RA 사람별 위임(ste 방식, docs/sso-delegation) — 같은 자리에서 읽되")
    return UA[i:UA.index("\n# ── 5) 게이트웨이 config 정합", i)]


def _derive(tmp_path: Path, *, infra_env: str = "", backend_env: str | None = None,
            local: str | None = None, base: str | None = None, pre: str = "", gw_env: str | None = None) -> dict:
    repo = tmp_path / "repo"
    (repo / "infra").mkdir(parents=True, exist_ok=True)
    (repo / "backend/config").mkdir(parents=True, exist_ok=True)
    (repo / "infra/.env").write_text(infra_env, encoding="utf-8")
    if backend_env is not None:
        (repo / "backend/.env").write_text(backend_env, encoding="utf-8")
    if local is not None:
        (repo / "backend/config/routes.local.env").write_text(local, encoding="utf-8")
    base_f = repo / "backend/config/routes.env"
    base_f.write_text(base or "", encoding="utf-8")
    gw = ""                                      # 게이트웨이 리포를 못 찾은 박스(update-all 의 find_repo 가 빈 값)
    if gw_env is not None:
        (tmp_path / "gw").mkdir(exist_ok=True)
        (tmp_path / "gw/provision.env").write_text(gw_env, encoding="utf-8")
        gw = str(tmp_path / "gw")
    keys = ("RA_SSO_SECRET", "RA_SSO_URL", "TESTSCOPE_MCP_URL", "TESTSCOPE_EXPECTED",
            "TESTSCOPE_SSO_SECRET", "TESTSCOPE_SSO_URL")
    script = "\n".join([
        "set -uo pipefail",                      # update-all 과 같은 셸 옵션 — 미정의 변수가 터지는지도 함께 본다
        f'SELF_REPO="{repo}"; ROUTES_ENV="{base_f}"; GW_DIR="{gw}"', pre,
        "hwax_skip() { printf '○ %s — %s\\n' \"$1\" \"$2\"; }",   # lib/skip-ledger.sh 대역 — 즉시 한 줄만 본다
        _fn("_envfile_value"), _fn("_ra_envv"), _derive_block(),
        *[f'printf "%s=%s\\n" {k} "${{{k}:-}}"' for k in keys],
    ])
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    out = dict(ln.split("=", 1) for ln in p.stdout.splitlines() if re.match(r"^[A-Z_]+=", ln))
    out["_log"] = p.stdout
    return out


# ── 1. 읽기 ──────────────────────────────────────────────────────────────────
def test_secrets_are_read_from_infra_env_with_bash_rules(tmp_path):
    """인라인 주석·따옴표는 벗기고(1e 의 _ra_envv — bash 가 소싱해 보는 값), env-sync 가 넣은 주석 줄은 빈 값이다."""
    got = _derive(tmp_path, infra_env=f'RA_SSO_SECRET="{SECRET}"   # RA 담당과 같은 값\n')
    assert got["RA_SSO_SECRET"] == SECRET
    got = _derive(tmp_path / "commented", infra_env="# RA_SSO_SECRET=   # ⚠ 값을 정해야 한다\n")
    assert got["RA_SSO_SECRET"] == ""


def test_an_exported_secret_wins_over_the_file(tmp_path):
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n", pre='RA_SSO_SECRET="from-env"')
    assert got["RA_SSO_SECRET"] == "from-env"


def test_secrets_use_explicit_ifs_not_default_expansion():
    """`${SECRET:-값}` 이 허용되면 다음 사람의 리터럴 기본값이 통과한다 — test_no_tracked_secrets 와 같은 이유."""
    blk = _derive_block()
    assert 'if [ -z "${RA_SSO_SECRET:-}" ]; then RA_SSO_SECRET="$(_ra_envv RA_SSO_SECRET)"; fi' in blk
    assert not re.search(r"\$\{RA_SSO_SECRET:-[^}]", UA)


# ── RA 주소 유도 ─────────────────────────────────────────────────────────────
def test_ra_sso_url_comes_from_the_ra_base_url_1e_set(tmp_path):
    """RA 가 원격인 박스(cae00) — 비워 두면 게이트웨이 기본값(같은 박스 :3000)으로 가서 틀린 곳을 부른다."""
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n", backend_env="RA_BASE_URL=http://old:3000\n",
                  pre='RA_BASE_URL="http://ra-a.example:3000"')
    assert got["RA_SSO_URL"] == "http://ra-a.example:3000/api/auth/sso"


def test_ra_sso_url_falls_back_to_backend_env(tmp_path):
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n", backend_env="RA_BASE_URL=http://127.0.0.1:3000/\n")
    assert got["RA_SSO_URL"] == "http://127.0.0.1:3000/api/auth/sso"


def test_ra_sso_url_is_left_alone_when_set_or_when_off(tmp_path):
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n", backend_env="RA_BASE_URL=http://b:3000\n",
                  pre='RA_SSO_URL="http://given/sso"')
    assert got["RA_SSO_URL"] == "http://given/sso", "명시한 값이 이긴다"
    got = _derive(tmp_path / "off", backend_env="RA_BASE_URL=http://b:3000\n")
    assert got["RA_SSO_URL"] == "", "비밀이 없으면 유도하지 않는다"
    got = _derive(tmp_path / "none", infra_env=f"RA_SSO_SECRET={SECRET}\n")
    assert got["RA_SSO_URL"] == "", "주소를 모르면 비워 둔다 — 게이트웨이가 직전 config 를 잇는다"


# ── TestScope 기대 — 위임이 아니라 토큰 등록, 신호는 게이트웨이 provision.env 의 TESTSCOPE_MCP_URL ────────────
def test_testscope_is_expected_when_the_gateway_has_its_mcp_url(tmp_path):
    got = _derive(tmp_path, gw_env='TESTSCOPE_MCP_URL="http://ts.example:8022/mcp"   # 그쪽 MCP\n')
    assert got["TESTSCOPE_MCP_URL"] == "http://ts.example:8022/mcp", "provision.env 를 bash 규칙으로 읽는다(주석·따옴표)"
    assert got["TESTSCOPE_EXPECTED"] == "1"
    assert "TestScope" not in got["_log"]


def test_an_exported_testscope_mcp_url_wins(tmp_path):
    got = _derive(tmp_path, gw_env="TESTSCOPE_MCP_URL=http://file/mcp\n", pre='TESTSCOPE_MCP_URL="http://given/mcp"')
    assert got["TESTSCOPE_MCP_URL"] == "http://given/mcp" and got["TESTSCOPE_EXPECTED"] == "1"


def test_testscope_is_not_expected_without_its_mcp_url_and_says_so(tmp_path):
    """안 쓰는 박스가 보통이다 — 그래도 '안 켠 기능' 으로 한 줄 남긴다(켜려면 무엇). 위임 비밀·라우트는 백엔드 기대 신호가 아니다."""
    off = _derive(tmp_path / "a", infra_env="TESTSCOPE_SSO_SECRET=x\n", local="testscope=http://ts:8020/\n",
                  gw_env="# TESTSCOPE_MCP_URL=\n")
    assert off["TESTSCOPE_EXPECTED"] == "0" and off["TESTSCOPE_MCP_URL"] == ""
    assert "○ TestScope MCP 도구" in off["_log"] and "TESTSCOPE_MCP_URL" in off["_log"]
    no_gw = _derive(tmp_path / "b")
    assert no_gw["TESTSCOPE_EXPECTED"] == "0", "게이트웨이 리포가 없어도 set -u 아래 안 터진다"


# ── TestScope 위임(두 갈래) — RA 와 같은 독자, 주소는 backend/.env 의 TESTSCOPE_BASE_URL ─────────────────
TS_SECRET = "ts-secret-0123456789abcdef0123456789"


def test_testscope_secret_is_read_like_the_ra_one(tmp_path):
    got = _derive(tmp_path, infra_env=f'TESTSCOPE_SSO_SECRET="{TS_SECRET}"   # TestScope 운영과 같은 값\n')
    assert got["TESTSCOPE_SSO_SECRET"] == TS_SECRET
    got = _derive(tmp_path / "commented", infra_env="# TESTSCOPE_SSO_SECRET=   # ⚠ 값을 정해야 한다\n")
    assert got["TESTSCOPE_SSO_SECRET"] == ""
    got = _derive(tmp_path / "env", infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n", pre='TESTSCOPE_SSO_SECRET="from-env"')
    assert got["TESTSCOPE_SSO_SECRET"] == "from-env", "내보낸 값이 이긴다"
    blk = _derive_block()
    assert ('if [ -z "${TESTSCOPE_SSO_SECRET:-}" ]; then TESTSCOPE_SSO_SECRET="$(_ra_envv TESTSCOPE_SSO_SECRET)"; fi'
            in blk)
    assert not re.search(r"\$\{TESTSCOPE_SSO_SECRET:-[^}]", UA), "리터럴 기본값 금지 — 만들지 않는다"


def test_testscope_sso_url_comes_from_its_base_url(tmp_path):
    got = _derive(tmp_path, infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n",
                  backend_env='TESTSCOPE_BASE_URL="http://ts.example:8020/"   # 그쪽 웹\n')
    assert got["TESTSCOPE_SSO_URL"] == "http://ts.example:8020/api/auth/sso", "주석·따옴표·끝 / 를 벗긴다"
    assert "TestScope 위임 주소 유도" in got["_log"]
    got = _derive(tmp_path / "exp", infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n",
                  backend_env="TESTSCOPE_BASE_URL=http://file:8020\n", pre='TESTSCOPE_BASE_URL="http://env:8020"')
    assert got["TESTSCOPE_SSO_URL"] == "http://env:8020/api/auth/sso", "내보낸 TESTSCOPE_BASE_URL 이 이긴다(RA_BASE_URL 과 같다)"


def test_testscope_sso_url_is_left_alone_when_set_or_when_off(tmp_path):
    got = _derive(tmp_path, infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n", backend_env="TESTSCOPE_BASE_URL=http://b:8020\n",
                  pre='TESTSCOPE_SSO_URL="http://given/sso"')
    assert got["TESTSCOPE_SSO_URL"] == "http://given/sso", "명시한 값이 이긴다"
    got = _derive(tmp_path / "off", backend_env="TESTSCOPE_BASE_URL=http://b:8020\n")
    assert got["TESTSCOPE_SSO_URL"] == "", "비밀이 없으면 유도하지 않는다 — 토큰 등록 그대로"
    assert "TestScope 위임" not in got["_log"]


def test_testscope_secret_without_an_address_says_so(tmp_path):
    """게이트웨이에 TestScope 기본 호스트가 없다 — 조용히 비워 두면 위임이 안 생긴 채 초록으로 보인다."""
    got = _derive(tmp_path, infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n", backend_env="TESTSCOPE_BASE_URL=\n")
    assert got["TESTSCOPE_SSO_URL"] == ""
    assert "⚠ TESTSCOPE_SSO_SECRET" in got["_log"] and "TESTSCOPE_BASE_URL" in got["_log"]
    said = [ln for ln in got["_log"].splitlines() if not re.match(r"^[A-Z_]+=", ln)]   # 시험이 덧붙인 값 덤프는 뺀다
    assert said and not any(TS_SECRET in ln for ln in said), "비밀은 출력에 안 남는다"


def test_ra_and_testscope_delegation_do_not_mix(tmp_path):
    """서비스마다 따로 — 한쪽 비밀이 다른 쪽 주소를 유도하거나 기대 여부를 바꾸지 않는다."""
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n",
                  backend_env="RA_BASE_URL=http://ra:3000\nTESTSCOPE_BASE_URL=http://ts:8020\n")
    assert got["RA_SSO_URL"] == "http://ra:3000/api/auth/sso"
    assert got["TESTSCOPE_SSO_SECRET"] == "" and got["TESTSCOPE_SSO_URL"] == ""
    got = _derive(tmp_path / "ts", infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n",
                  backend_env="RA_BASE_URL=http://ra:3000\nTESTSCOPE_BASE_URL=http://ts:8020\n")
    assert got["RA_SSO_SECRET"] == "" and got["RA_SSO_URL"] == ""
    assert got["TESTSCOPE_SSO_URL"] == "http://ts:8020/api/auth/sso"
    assert got["TESTSCOPE_EXPECTED"] == "0", "위임 비밀은 백엔드 기대 신호가 아니다(백엔드는 TESTSCOPE_MCP_URL)"


def _calc_missing(have: list[str], env: dict) -> list[str]:
    body = UA[UA.index("import json, os\nh = json.loads"):]
    body = body[:body.index("\nPY\n")]
    payload = json.dumps({"backends": dict.fromkeys(have, True)})
    p = subprocess.run(["python3", "-c", body], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "H": payload, "RAT": "", "ODB": "", "ARP": "",
                            "MXWP_UP": "0", "STE_ROUTED": "0", **env})
    assert p.returncode == 0, p.stderr
    return p.stdout.split()


def test_calc_missing_expects_testscope_only_when_flagged():
    base = ["ai-data-hub", "signalforge", "hwax-deliberation"]
    assert "testscope" in _calc_missing(base, {"TESTSCOPE_EXPECTED": "1"})
    assert "testscope" not in _calc_missing(base + ["testscope"], {"TESTSCOPE_EXPECTED": "1"})
    for env in ({"TESTSCOPE_EXPECTED": "0"}, {}):
        assert "testscope" not in _calc_missing(base, env)
    assert 'TESTSCOPE_EXPECTED="${TESTSCOPE_EXPECTED:-0}" python3 - <<' in UA, "판정 파이썬에 플래그가 넘어간다"


# ── 2. 방아쇠 — config 에 위임이 없거나 비밀이 다르면 재프로비저닝 ───────────────
def _generic_fns() -> str:
    """일반 앱(PER_USER_SSO_APPS) 목록을 읽는 세 함수 — 방아쇠·끄기 목록·전달이 같이 쓴다."""
    return _fn("_sso_generic_pairs") + _fn("_sso_generic_names") + _fn("_sso_generic_unlisted")


def _drift(tmp_path: Path, cfg, *, ra="", ts="", ts_x="1", box: str = "") -> str:
    """box = provision.env 를 소싱한 뒤의 셸 변수(일반 앱의 목록·비밀·주소). export 하지 않는다 — update-all 도 소싱만 한다."""
    f = tmp_path / "gateway_config.json"
    f.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    script = (f'set -uo pipefail\nRA_SSO_SECRET="{ra}"; TESTSCOPE_SSO_SECRET="{ts}"; TESTSCOPE_EXPECTED="{ts_x}"\n{box}\n'
              f'{_generic_fns()}{_fn("_sso_deleg_drift")}\n_sso_deleg_drift "{f}"')
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout.strip()


def _cfg(**pu) -> dict:
    return {"heax_registry": {"per_user_sso": {k: {"sso_url": "http://x/sso", "secret": v} for k, v in pu.items()}}}


def test_missing_or_stale_ra_delegation_triggers_reprovisioning(tmp_path):
    assert _drift(tmp_path, {}, ra=SECRET) == "reportarchive_sso", "비밀을 넣었는데 config 에 위임이 없다"
    assert _drift(tmp_path, _cfg(reportarchive="old"), ra=SECRET) == "reportarchive_sso", "비밀을 바꿨다"
    assert _drift(tmp_path, _cfg(reportarchive=SECRET), ra=SECRET) == ""
    assert _drift(tmp_path, {}, ra="") == "", "안 켠 박스는 조용하다"


def test_testscope_delegation_drift_when_its_secret_is_set(tmp_path):
    TS = "ts-secret-0123456789abcdef0123456789"
    assert _drift(tmp_path, {}, ts=TS) == "testscope_sso", "비밀을 넣었는데 config 에 위임이 없다"
    assert _drift(tmp_path, _cfg(testscope="old"), ts=TS) == "testscope_sso", "비밀을 바꿨다"
    assert _drift(tmp_path, _cfg(testscope=TS), ts=TS) == ""
    assert _drift(tmp_path, {}, ra=SECRET, ts=TS) == "reportarchive_sso testscope_sso", "둘 다 — 키 이름만, 정렬"
    assert _drift(tmp_path, _cfg(reportarchive=SECRET), ra=SECRET) == "", "비밀이 없으면 토큰 등록이다 — 보지 않는다"


def test_testscope_delegation_is_not_checked_without_its_backend(tmp_path):
    """백엔드를 기대하지 않는 박스(TESTSCOPE_MCP_URL 없음) — 위임이 할 일이 없고, 보면 매 실행 헛된 재프로비저닝을 돈다."""
    TS = "ts-secret-0123456789abcdef0123456789"
    assert _drift(tmp_path, {}, ts=TS, ts_x="0") == ""
    assert _drift(tmp_path, {}, ra=SECRET, ts=TS, ts_x="0") == "reportarchive_sso", "RA 는 그대로 본다"
    assert 'TS_X="${TESTSCOPE_EXPECTED:-0}"' in _fn("_sso_deleg_drift")


def test_emptied_secret_with_a_leftover_delegation_triggers_turning_it_off(tmp_path):
    """되돌리기 — infra/.env 에서 비밀을 비우면 포털 화면은 바로 '토큰 등록' 인데, 게이트웨이 위임은 provision 이 이어받아 남았다.
    남은 위임이 재프로비저닝의 방아쇠다(provision 이 PER_USER_SSO_OFF 로 지운다). 안 켠 박스는 여전히 조용하다."""
    TS = "ts-secret-0123456789abcdef0123456789"
    assert _drift(tmp_path, _cfg(reportarchive="old")) == "reportarchive_sso_off"
    assert _drift(tmp_path, _cfg(testscope="old")) == "testscope_sso_off"
    assert _drift(tmp_path, _cfg(testscope="old"), ts_x="0") == "testscope_sso_off", "백엔드가 없어도 남은 위임은 지운다"
    assert _drift(tmp_path, _cfg(reportarchive=SECRET, testscope="old"), ra=SECRET) == "testscope_sso_off", "하나만 끈다"
    assert _drift(tmp_path, _cfg(reportarchive="old"), ts=TS) == "reportarchive_sso_off testscope_sso"
    assert _drift(tmp_path, _cfg(ste="x")) == "", "ste 등 다른 위임은 이 점검의 대상이 아니다"
    i = UA.index('for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do')
    assert "*_sso_off)" in UA[i:UA.index("done", i)], "끄기는 끄기라고 알린다"


def test_drift_check_survives_odd_configs_and_keeps_secrets_off_argv(tmp_path):
    assert _drift(tmp_path, "{not json", ra=SECRET) == ""
    assert _drift(tmp_path, {"heax_registry": {"per_user_sso": {"reportarchive": "str"}}}, ra=SECRET) == "reportarchive_sso"
    fn = _fn("_sso_deleg_drift")
    argv = fn.split("python3", 1)[1].splitlines()[0]
    assert 'python3 - "$1"' in fn and "$RA_SSO_SECRET\"" not in argv and "TESTSCOPE_SSO_SECRET" not in argv
    assert 'TS_S="${TESTSCOPE_SSO_SECRET:-}"' in fn.split("python3", 1)[0], "비밀은 환경변수로만 넘긴다"


def test_drift_feeds_missing_and_the_post_check():
    i = UA.index('for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do')
    assert UA.index("calc_missing \"$H\")\"") < i < UA.index('if [ -n "$MISSING" ]; then', i)
    assert 'MISSING="${MISSING:+$MISSING }$_k"' in UA[i:UA.index("done", i)]
    post = UA[UA.index('STILL="$(calc_missing "$H")"'):UA.index("주소 드리프트 해소")]
    assert '_sso_left="$(_sso_deleg_drift "$GW_DIR/gateway_config.json")"' in post, "재프로비저닝 뒤에도 어긋나면 ✗ 다"


# ── 3. 전달 ──────────────────────────────────────────────────────────────────
def _reprovision_cmd() -> str:
    i = UA.index('( cd "$GW_DIR" && export PER_USER_SSO_APPS ')
    return _generic_fns() + UA[i:UA.index("--force )", i) + len("--force )")]


def test_the_provisioner_actually_receives_the_values(tmp_path):
    """텍스트가 아니라 **실행**으로 본다 — 대입어 사슬이 깨지면 provision 이 아예 안 돈다(3라운드 실사고)."""
    gw = tmp_path / "gw"
    gw.mkdir()
    keys = ("RA_SSO_SECRET", "RA_SSO_URL", "TESTSCOPE_MCP_URL", "TESTSCOPE_SSO_SECRET", "TESTSCOPE_SSO_URL")
    (gw / "provision-config.sh").write_text(
        "#!/usr/bin/env bash\n" + "".join(f'printf "%s=%s\\n" {k} "${k}" >> "$PWD/ran.marker"\n' for k in keys))
    cmd = _reprovision_cmd()
    assert not any(ln.lstrip().startswith("`") for ln in cmd.splitlines())
    assert '&& RAT_TOKEN="${RAT_TOKEN:-}"' in cmd, "대입어 사슬은 export 뒤에 그대로 이어진다"
    vals = {"RA_SSO_SECRET": SECRET, "RA_SSO_URL": "http://ra/api/auth/sso", "TESTSCOPE_MCP_URL": "http://ts:8022/mcp",
            "TESTSCOPE_SSO_SECRET": "ts-secret-xyz", "TESTSCOPE_SSO_URL": "http://ts:8020/api/auth/sso"}
    # 부모 셸 변수일 뿐 export 하지 않는다 — update-all 도 export 하지 않는다(사슬이 넘겨야 자식이 본다)
    script = f'set -u; GW_DIR="{gw}"\n' + "".join(f'{k}="{v}"\n' for k, v in vals.items()) + f"{cmd}\necho rc=$?"
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert "rc=0" in r.stdout, r.stderr
    got = dict(ln.split("=", 1) for ln in (gw / "ran.marker").read_text().splitlines())
    assert got == vals


def _sso_off_lines() -> str:
    """끌 위임 목록을 세우는 줄들 — RA·TestScope 한 줄, 비밀을 비운 일반 앱 한 줄, 목록에서 뺀 일반 앱 한 줄."""
    i = UA.index('_sso_off="$(')
    j = UA.rindex('_sso_off="$_sso_off$(', i, UA.index('if ( cd "$GW_DIR" && export PER_USER_SSO_APPS ', i))
    return UA[i:UA.index("\n", j)]


def test_the_provisioner_is_told_which_delegations_to_turn_off(tmp_path):
    """비밀이 빈 서비스만 PER_USER_SSO_OFF 로 — 실행으로 본다(대입어 사슬)."""
    gw = tmp_path / "gw"
    gw.mkdir()
    (gw / "provision-config.sh").write_text('#!/usr/bin/env bash\nprintf "%s" "$PER_USER_SSO_OFF" > "$PWD/off.marker"\n')
    pre = _generic_fns() + _sso_off_lines()
    cmd = _reprovision_cmd()
    for ra, ts, want in (("", "", "reportarchive testscope"), (SECRET, "", "testscope"),
                         ("", "ts-s", "reportarchive "), (SECRET, "ts-s", "")):
        script = f'set -u; GW_DIR="{gw}"; RA_SSO_SECRET="{ra}"; TESTSCOPE_SSO_SECRET="{ts}"\n{pre}\n{cmd}\necho rc=$?'
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        assert "rc=0" in r.stdout, r.stderr
        assert (gw / "off.marker").read_text() == want, (ra, ts)


# ── 일반 앱 — 게이트웨이 PER_USER_SSO_APPS="<per_user 키>:<ENV 접두> …"(8차 요청 §4-(2)) ─────────────────────────────
# 게이트웨이는 여섯 번째 앱부터 provision-config.sh 를 고치지 않고 이 목록으로 위임을 만든다. 그 값들은 게이트웨이 provision.env 에
# 있고 update-all 은 그 파일을 소싱만 한다 — 접두가 박스마다 달라 대입어 사슬에 이름을 적을 수 없으므로, 넘기지 않으면
# '적었는데 손으로 돌릴 때만 켜지는' 설정이 된다. 방아쇠(없거나 비밀이 다르다)·끄기(비밀을 비웠다)도 RA·TestScope 와 같은 규칙이다.
GEN_APPS = 'PER_USER_SSO_APPS="newapp:NEWAPP other:OTHER_APP"'
GEN_SECRET = "newapp-secret-0123456789abcdef"


def test_generic_apps_reach_the_provisioner_and_nothing_else_does(tmp_path):
    """**이 시험이 이 구획의 이유다** — 목록과, 목록의 접두마다 비밀·주소가 자식(provision)에게 간다. 실행으로 본다."""
    gw = tmp_path / "gw"; gw.mkdir()
    seen = ("PER_USER_SSO_APPS", "NEWAPP_SSO_SECRET", "NEWAPP_SSO_URL", "OTHER_APP_SSO_SECRET", "OTHER_APP_SSO_URL",
            "UNLISTED_SSO_SECRET")
    (gw / "provision-config.sh").write_text(
        "#!/usr/bin/env bash\n" + "".join(f'printf "%s=%s\\n" {k} "${{{k}-<unset>}}" >> "$PWD/ran.marker"\n' for k in seen)
        + 'printf "ARGV=%s\\n" "$*" >> "$PWD/ran.marker"\n')
    box = (f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\nNEWAPP_SSO_URL="http://newapp.example:8300/api/auth/sso"\n'
           'OTHER_APP_SSO_SECRET="other-secret"\nUNLISTED_SSO_SECRET="목록에 없는 앱"\n')
    script = (f'set -uo pipefail; GW_DIR="{gw}"\n{box}{_reprovision_cmd()}\necho rc=$?\n'
              """bash -c 'printf "AFTER=%s\\n" "${NEWAPP_SSO_SECRET-<unset>}"'""")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert "rc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
    got = dict(ln.split("=", 1) for ln in (gw / "ran.marker").read_text().splitlines())
    assert got == {"PER_USER_SSO_APPS": "newapp:NEWAPP other:OTHER_APP", "NEWAPP_SSO_SECRET": GEN_SECRET,
                   "NEWAPP_SSO_URL": "http://newapp.example:8300/api/auth/sso", "OTHER_APP_SSO_SECRET": "other-secret",
                   "OTHER_APP_SSO_URL": "<unset>", "UNLISTED_SSO_SECRET": "<unset>", "ARGV": "--force"}, \
        "목록의 값만, 환경으로만(비밀이 argv 에 실리면 ps 에 보인다)"
    assert "AFTER=<unset>" in r.stdout, "export 는 재프로비저닝 서브셸 안에서만 — 뒤에 뜨는 서비스가 남의 비밀을 물려받지 않는다"


def test_no_generic_list_means_nothing_extra_is_exported(tmp_path):
    """목록이 없는 박스(지금 전부) — 종전과 같다. bare `export` 로 떨어지면 환경 전체(비밀 포함)가 로그에 찍힌다."""
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "provision-config.sh").write_text('#!/usr/bin/env bash\nprintf "%s" "${PER_USER_SSO_APPS-<unset>}" > "$PWD/apps.marker"\n')
    script = f'set -uo pipefail; GW_DIR="{gw}"; RAT_TOKEN="rat-test-token"\n{_reprovision_cmd()}\necho rc=$?'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert "rc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
    assert (gw / "apps.marker").read_text() == "<unset>"
    assert "declare -x" not in r.stdout and "rat-test-token" not in r.stdout


@pytest.mark.parametrize("apps,names", [
    ("newapp:NEWAPP", "NEWAPP_SSO_SECRET NEWAPP_SSO_URL"),
    ("  newapp:NEWAPP\tother:OTHER_APP ", "NEWAPP_SSO_SECRET NEWAPP_SSO_URL OTHER_APP_SSO_SECRET OTHER_APP_SSO_URL"),
    ("콜론없음 :NOKEY nopfx: bad:9X bad2:A-B bad3:A:B ok:OK_1", "OK_1_SSO_SECRET OK_1_SSO_URL"),
    ("reportarchive:RA testscope:TS ste:STE hwax_risk:HR kooremapper_mcp:KR", ""),   # 게이트웨이가 직접 만드는 다섯 — 순회로 덮지 않는다
    ("*:STAR 'q:Q $(id):X", ""),                                                      # 키가 이름 꼴이 아니면 다루지 않는다
    ("dup:FOO dup:BAR", "FOO_SSO_SECRET FOO_SSO_URL"),                                # 한 키를 두 번 — 먼저 적힌 쌍만
    ("dup:9X dup:FOO other:O dup:BAR", "FOO_SSO_SECRET FOO_SSO_URL O_SSO_SECRET O_SSO_URL"),   # 못 읽은 쌍은 '먼저' 가 아니다
    ("", ""),
])
def test_generic_pairs_are_read_with_the_gateway_rule(tmp_path, apps, names):
    (tmp_path / "cwd").mkdir(); (tmp_path / "cwd/어떤파일").write_text("x")     # 글롭이 풀리면 이 이름이 섞인다
    script = f"set -uo pipefail\n{_generic_fns()}_sso_generic_names"
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, cwd=str(tmp_path / "cwd"),
                       env={"PATH": "/usr/bin:/bin", "PER_USER_SSO_APPS": apps})      # 값을 글자 그대로(탭·따옴표·$ 포함) 준다
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert r.stdout.split() == names.split()


def test_generic_delegation_drift_follows_the_ra_rule(tmp_path):
    on = f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\nNEWAPP_SSO_URL="http://x/sso"\n'      # 주소는 _cfg 가 쓰는 것과 같다
    assert _drift(tmp_path, {}, box=on) == "newapp_sso", "비밀을 넣었는데 config 에 위임이 없다 — 재프로비저닝해야 켜진다"
    assert _drift(tmp_path, _cfg(newapp="old"), box=on) == "newapp_sso", "비밀을 바꿨다"
    assert _drift(tmp_path, _cfg(newapp=GEN_SECRET), box=on) == ""
    assert _drift(tmp_path, _cfg(newapp=GEN_SECRET), box=on.replace("http://x/sso", "http://moved.example/sso")) == "newapp_sso", \
        "주소를 옮겼다 — 게이트웨이는 env 의 주소로 고쳐 쓴다"
    assert _drift(tmp_path, _cfg(newapp=GEN_SECRET), box=f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\n') == "", \
        "주소를 안 적은 박스 — config 의 주소를 잇는다"
    assert _drift(tmp_path, _cfg(newapp="old"), box=GEN_APPS) == "newapp_sso_off", "비밀을 비웠는데 위임이 남았다"
    assert _drift(tmp_path, {}, box=GEN_APPS) == "", "목록에만 있고 켜지 않은 앱은 조용하다"
    assert _drift(tmp_path, _cfg(newapp="old")) == "", "목록에 없는 앱의 위임은 이 점검의 대상이 아니다(어느 변수가 그 비밀인지 모른다)"
    assert _drift(tmp_path, _cfg(reportarchive=SECRET, newapp="old"), ra=SECRET, box=on) == "newapp_sso"
    assert _drift(tmp_path, {}, ra=SECRET, box=on) == "reportarchive_sso newapp_sso", "RA·TestScope 가 먼저, 일반 앱은 뒤에"
    assert GEN_SECRET not in _fn("_sso_deleg_drift")


def test_a_generic_secret_without_an_address_is_reported_not_reprovisioned(tmp_path):
    """게이트웨이는 주소가 없으면 위임을 만들지 않는다(기본 호스트가 없다). 그 앱을 방아쇠로 삼으면 매 실행 재프로비저닝이
    헛돌고 그때마다 게이트웨이·에이전트서버가 내려갔다 올라온다 — 따로 표지해 알리기만 한다."""
    box = f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\n'
    assert _drift(tmp_path, {}, box=box) == "newapp_sso_nourl"
    # 주소는 지금 config 에 남은 것을 게이트웨이가 이어받는다 — 그때는 만들 수 있으니 방아쇠다
    assert _drift(tmp_path, _cfg(newapp="old"), box=box) == "newapp_sso"
    i = UA.index('for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do')
    loop = UA[i:UA.index("\n    done\n", i)]
    script = "\n".join([
        "set -uo pipefail", 'bad() { echo "BAD:$*"; }', "MISSING=''",
        '_sso_deleg_drift() { echo "reportarchive_sso newapp_sso_nourl other_sso_off"; }', 'GW_DIR="/nonexistent"',
        loop, "    done", 'echo "MISSING=[$MISSING]"'])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert "MISSING=[reportarchive_sso other_sso_off]" in r.stdout, "주소 없는 앱은 재프로비저닝 방아쇠가 아니다"
    assert "BAD:" in r.stdout and "newapp" in r.stdout and "_SSO_URL" in r.stdout, "무엇을 적으면 켜지는지와 함께 알린다"
    post = UA[UA.index('_sso_left="$(_sso_deleg_drift "$GW_DIR/gateway_config.json")"'):UA.index("주소 드리프트 해소")]
    script = "\n".join([
        "set -uo pipefail", '_sso_deleg_drift() { echo "newapp_sso_nourl testscope_sso other_sso_nourl"; }', 'GW_DIR="/nonexistent"',
        post[:post.index("\n", post.index('STILL="${STILL:+$STILL }$_sso_left"'))].replace("        ", "", 1), 'echo "STILL=[${STILL:-}]"'])
    r = subprocess.run(["bash", "-c", "STILL=''\n" + script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and not r.stderr, r.stderr
    assert "STILL=[testscope_sso]" in r.stdout, "재프로비저닝이 고칠 수 없는 것을 '재프로비저닝 후에도 누락' 으로 다시 세지 않는다"


def test_an_emptied_generic_secret_is_passed_as_off(tmp_path):
    """되돌리기 — 목록에 남기고 비밀만 비운 앱은 PER_USER_SSO_OFF 로 간다(게이트웨이는 목록에 있는 앱만 끈다)."""
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "provision-config.sh").write_text('#!/usr/bin/env bash\nprintf "%s" "$PER_USER_SSO_OFF" > "$PWD/off.marker"\n')
    for box, want in ((f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\n', ["other"]),
                      (f'{GEN_APPS}\n', ["newapp", "other"]),
                      (f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\nOTHER_APP_SSO_SECRET="o"\n', [])):
        script = (f'set -uo pipefail; GW_DIR="{gw}"; RA_SSO_SECRET="{SECRET}"; TESTSCOPE_SSO_SECRET="ts-s"\n{box}'
                  f'{_generic_fns()}{_sso_off_lines()}\n{_reprovision_cmd()}\necho rc=$?')
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        assert "rc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
        assert (gw / "off.marker").read_text().split() == want, box


def _gateway_generic_loop():
    """게이트웨이 프로비저너의 일반 앱 순회(`_GENERIC_SSO = {}` 부터 끄기 주석 앞까지)를 원문에서 꺼낸다. 아직 없는 판이면 None."""
    prov = ROOT.parent / "HWAXMcpGateway" / "provision-config.sh"
    if not prov.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    src = prov.read_text(encoding="utf-8")
    if "_GENERIC_SSO = {}" not in src:
        return None
    i = src.index("_GENERIC_SSO = {}")
    return src[i:src.index("\n# 끄기 —", i)]


@pytest.mark.parametrize("apps,env,prev", [
    ("newapp:NEWAPP", {"NEWAPP_SSO_SECRET": "s1", "NEWAPP_SSO_URL": "http://n/sso"}, {}),
    ("newapp:NEWAPP", {"NEWAPP_SSO_SECRET": "s1"}, {}),                                         # 주소 없음 — 만들지 못한다
    ("newapp:NEWAPP", {"NEWAPP_SSO_SECRET": "s1"}, {"newapp": {"sso_url": "http://n/sso", "secret": "old", "client": "gateway"}}),
    ("newapp:NEWAPP", {"NEWAPP_SSO_SECRET": "s1"}, {"newapp": {"sso_url": "http://n/sso", "secret": "s1", "client": "gateway"}}),
    ("newapp:NEWAPP", {"NEWAPP_SSO_SECRET": "s1", "NEWAPP_SSO_URL": "http://moved/sso"},      # 주소만 바꿨다 — 아래 주석
     {"newapp": {"sso_url": "http://n/sso", "secret": "s1", "client": "gateway"}}),
    ("newapp:NEWAPP", {}, {"newapp": {"sso_url": "http://n/sso", "secret": "old", "client": "gateway"}}),   # 비밀 없는 실행 — 이어받는다(끄기는 따로)
    ("newapp:NEWAPP other:OTHER_APP", {"OTHER_APP_SSO_SECRET": "o", "OTHER_APP_SSO_URL": "http://o/sso"}, {}),
    ("reportarchive:NEWAPP bad:9X nocolon ok:OK_1", {"NEWAPP_SSO_SECRET": "s1", "NEWAPP_SSO_URL": "http://n/sso",
                                                     "OK_1_SSO_SECRET": "k", "OK_1_SSO_URL": "http://k/sso"}, {}),
])
def test_the_trigger_agrees_with_what_the_gateway_would_build(tmp_path, apps, env, prev):
    """**정본은 게이트웨이다** — 그 순회를 원문에서 꺼내 같은 입력으로 돌린다. update-all 이 '어긋났다' 고 보는 앱은 정확히
    게이트웨이가 재프로비저닝으로 **바꿔 놓을** 앱이어야 한다 — 더 넓으면 매 실행 헛돌고, 더 좁으면 적어도 안 켜진다."""
    loop = _gateway_generic_loop()
    if loop is None:
        pytest.skip("옆의 게이트웨이가 아직 PER_USER_SSO_APPS 를 모르는 판이다")
    e = {"PER_USER_SSO_APPS": apps, **env}
    per_user = json.loads(json.dumps(prev))
    exec(loop, {"e": e, "per_user": per_user, "re": re, "print": lambda *a, **k: None})  # noqa: S102 — 옆 리포의 추적 파일 발췌
    # 게이트웨이는 순회가 쓴 항목에 `managed_by` 표지를 남긴다(HWAXMcpGateway cff32c3 — 목록에서 뺀 앱을 끄는 데 쓴다. 동작에는
    # 영향이 없다). 표지만 새로 붙는 것은 '바뀜' 이 아니다 — 그것 하나로 재프로비저닝을 돌리면 표지 없는 옛 항목이 있는 박스가
    # 게이트웨이·에이전트서버를 한 번 괜히 내렸다 올린다. 표지는 다음에 비밀과 함께 도는 실행에서 붙는다.
    def _wo_mark(v):
        return {k: x for k, x in v.items() if k != "managed_by"} if isinstance(v, dict) else v

    changed = sorted(k for k in per_user if _wo_mark(per_user[k]) != _wo_mark(prev.get(k)))
    box = f"PER_USER_SSO_APPS={json.dumps(apps)}\n" + "".join(f'{k}="{v}"\n' for k, v in env.items())
    cfg = {"heax_registry": {"per_user_sso": prev}}
    flagged = sorted(t[:-len("_sso")] for t in _drift(tmp_path, cfg, box=box).split() if t.endswith("_sso"))
    assert flagged == changed, (apps, env, prev)
    # 재프로비저닝 뒤에는 조용해야 한다(수렴) — 게이트웨이가 만든 config 로 다시 본다
    after = _drift(tmp_path, {"heax_registry": {"per_user_sso": per_user}}, box=box).split()
    assert [t for t in after if t.endswith("_sso")] == [], after


# ── 한 키를 두 번 적은 목록 ──────────────────────────────────────────────────────
# per_user 키 하나에 위임은 하나다. `dup:FOO dup:BAR` 처럼 두 번 적으면 쌍마다 따로 판정해 서로 맞을 수가 없었다 — 비밀이 한쪽에만
# 있으면 방아쇠(dup_sso)와 끄기(PER_USER_SSO_OFF=dup)가 한 실행에서 같이 나가, 게이트웨이는 위임을 만들고 곧바로 지운다. 다음
# 실행도 같다: 매 실행 재프로비저닝 → 게이트웨이·에이전트서버 재기동 → '재프로비저닝 후에도 누락: dup_sso (mxwp 토큰 민팅 실패 등…)'.
def _gateway_sso_block():
    """게이트웨이 프로비저너의 일반 앱 순회 **와 끄기**(`_GENERIC_SSO = {}` 부터 per_user 를 config 에 싣기 직전까지)."""
    prov = ROOT.parent / "HWAXMcpGateway" / "provision-config.sh"
    if not prov.exists():
        pytest.skip("게이트웨이 리포가 옆에 없다")
    src = prov.read_text(encoding="utf-8")
    if "_GENERIC_SSO = {}" not in src:
        pytest.skip("옆의 게이트웨이가 아직 PER_USER_SSO_APPS 를 모르는 판이다")
    i = src.index("_GENERIC_SSO = {}")
    return src[i:src.index("\nif per_user:", i)]


def _one_run(tmp_path: Path, box: str, prev: dict) -> dict:
    """update-all 한 번 — 어긋났다고 보면 끌 목록을 세워 게이트웨이의 순회·끄기(원문)를 **update-all 이 넘기는 값만으로** 돌린다.
    돌려주는 것은 그 뒤의 per_user_sso(재프로비저닝이 안 돌았으면 그대로)."""
    cfg = {"heax_registry": {"per_user_sso": prev}}
    if not any(t.endswith(("_sso", "_sso_off")) for t in _drift(tmp_path, cfg, box=box).split()):
        return prev
    # 끌 목록은 지금 config 도 읽는다(목록에서 뺀 앱) — 위 _drift 가 같은 자리에 적어 둔 그 파일이다
    script = (f'set -uo pipefail; GW_DIR="{tmp_path}"; RA_SSO_SECRET="{SECRET}"; TESTSCOPE_SSO_SECRET="ts-s"\n{box}\n{_generic_fns()}{_sso_off_lines()}\n'
              'printf "OFF=%s\n" "$_sso_off"\nfor n in PER_USER_SSO_APPS $(_sso_generic_names); do printf "ENV=%s=%s\n" "$n" "${!n:-}"; done')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and not r.stderr, r.stderr
    e = {"PER_USER_SSO_OFF": next(ln[4:] for ln in r.stdout.splitlines() if ln.startswith("OFF="))}
    e.update(ln[4:].split("=", 1) for ln in r.stdout.splitlines() if ln.startswith("ENV="))
    per_user = json.loads(json.dumps(prev))
    exec(_gateway_sso_block(), {"e": {k: v for k, v in e.items() if v}, "per_user": per_user, "re": re,  # noqa: S102 — 옆 리포의 추적 파일 발췌
                                "print": lambda *a, **k: None})
    return per_user


@pytest.mark.parametrize("apps,env,want_secret", [
    ("dup:FOO dup:BAR", {"FOO_SSO_SECRET": "s-foo", "FOO_SSO_URL": "http://f/sso"}, "s-foo"),     # 비밀이 앞 쌍에만
    ("dup:BAR dup:FOO", {"FOO_SSO_SECRET": "s-foo", "FOO_SSO_URL": "http://f/sso"}, None),        # 비밀이 뒤 쌍에만 — 앞 쌍이 이긴다
    ("dup:FOO dup:BAR", {"FOO_SSO_SECRET": "s-foo", "FOO_SSO_URL": "http://f/sso",
                         "BAR_SSO_SECRET": "s-bar", "BAR_SSO_URL": "http://b/sso"}, "s-foo"),       # 둘 다 있고 서로 다르다
    ("dup:FOO dup:FOO", {"FOO_SSO_SECRET": "s-foo", "FOO_SSO_URL": "http://f/sso"}, "s-foo"),     # 같은 쌍을 두 번(대조)
    ("dup:FOO", {"FOO_SSO_SECRET": "s-foo", "FOO_SSO_URL": "http://f/sso"}, "s-foo"),             # 한 번(대조)
])
def test_a_key_listed_twice_converges_after_one_reprovision(tmp_path, apps, env, want_secret):
    """**이 구획의 이유다** — 재프로비저닝이 한 번 돈 뒤에는 조용해야 한다. 종전엔 앞의 세 경우가 실행마다 다시 어긋났다."""
    box = f"PER_USER_SSO_APPS={json.dumps(apps)}\n" + "".join(f'{k}="{v}"\n' for k, v in env.items())
    after = _one_run(tmp_path, box, {})
    assert (after.get("dup") or {}).get("secret") == want_secret, after
    left = [t for t in _drift(tmp_path, {"heax_registry": {"per_user_sso": after}}, box=box).split()
            if t.endswith(("_sso", "_sso_off"))]
    assert left == [], f"한 번 돈 뒤에도 어긋나 있다 — 매 실행 재프로비저닝이 돈다: {left}"
    assert _one_run(tmp_path, box, after) == after, "두 번째 실행은 아무것도 바꾸지 않는다"


def test_a_key_listed_twice_is_reported_and_is_not_a_trigger(tmp_path):
    """앞 쌍에 비밀이 없으면 위임이 안 만들어지고 재프로비저닝도 안 돈다 — 조용하면 '적었는데 왜 안 켜지나' 를 찾을 길이 없다.
    §5 의 그 줄들을 원문 그대로 돌린다. 쌍점 뒤(접두)는 찍지 않는다 — 비밀을 잘못 적었을 수 있다(D-10 #8)."""
    i = UA.index("  # 한 키를 두 번 적은 PER_USER_SSO_APPS")
    block = UA[i:UA.index("\n  done\n", i) + len("\n  done\n")]
    for apps, want in (("dup:FOO dup:BAR other:O dup:BAZ two:A two:B", ["dup", "two"]), ("dup:FOO other:O", []), ("", [])):
        script = (f'set -uo pipefail; MISSING="signalforge"; PER_USER_SSO_APPS={json.dumps(apps)}\n'
                  f'bad() {{ echo "BAD:$*"; }}\n{_generic_fns()}{block}\nprintf "MISSING=[%s]\n" "$MISSING"')
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        assert r.returncode == 0 and not r.stderr, r.stderr
        bads = [ln for ln in r.stdout.splitlines() if ln.startswith("BAD:")]
        assert [b.split()[2].rstrip(":") for b in bads] == want, r.stdout
        assert all("PER_USER_SSO_APPS" in b and "provision.env" in b for b in bads)
        assert not any(x in r.stdout for x in ("FOO", "BAR", "BAZ")), "접두는 찍지 않는다"
        assert "MISSING=[signalforge]" in r.stdout, "알리기만 한다 — 방아쇠가 아니다"


# ── 목록에서 뺀 일반 앱 ─────────────────────────────────────────────────────────
# 앱을 걷을 때 사람은 PER_USER_SSO_APPS 의 쌍과 <접두>_SSO_* 줄을 지운다. 그러면 그 앱은 쌍 목록에 없어 방아쇠도 끄기도 그 위임을
# 보지 못했고(위 test_generic_delegation_drift_follows_the_ra_rule 의 마지막 줄들), 게이트웨이는 옛 비밀로 그 앱에 계속 사람별 토큰을
# 청했다. 게이트웨이는 순회가 쓴 항목에 `"managed_by": "PER_USER_SSO_APPS"` 표지를 남기고(HWAXMcpGateway cff32c3), 표지가 있고 이번
# 목록의 어느 쌍도 그 이름이 아닌 항목은 PER_USER_SSO_OFF 에 이름이 오면 지운다 — 그 이름을 넘기는 것이 update-all 의 몫이다.
STAMP = "PER_USER_SSO_APPS"


def _pu(**entries) -> dict:
    """per_user_sso 를 지어낸다 — 값이 True 면 순회가 쓴 항목(표지 있음), False 면 표지 없는 항목, 그 밖은 그대로."""
    def one(v):
        if isinstance(v, bool):
            return {"sso_url": "http://x/sso", "secret": "old", "client": "gateway", **({"managed_by": STAMP} if v else {})}
        return v
    return {"heax_registry": {"per_user_sso": {k: one(v) for k, v in entries.items()}}}


def _unlisted(tmp_path: Path, cfg, apps: str) -> list[str]:
    f = tmp_path / "gateway_config.json"
    f.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    r = subprocess.run(["bash", "-c", f'set -uo pipefail\n{_generic_fns()}_sso_generic_unlisted "{f}"'], capture_output=True,
                       text=True, env={"PATH": "/usr/bin:/bin", "PER_USER_SSO_APPS": apps})
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout.split()


@pytest.mark.parametrize("apps,want", [
    ("", ["gone"]),                                   # 목록을 통째로 비웠다
    ("other:OTHER_APP", ["gone"]),                    # 다른 앱만 남겼다
    ("gone:GONE", []),                                # 아직 목록에 있다 — 비밀을 비운 것이면 쌍 목록 쪽이 끈다
    ("gone:9X", []),                                  # 접두를 잘못 적었다 — '뺐다' 가 아니다(이름은 콜론 앞)
    ("gone", []),                                     # 콜론을 빠뜨렸다 — 마찬가지
    ("x:X\tgone:GONE\nother:O", []),                  # 탭·줄바꿈으로 갈라 적어도 쌍이다
    ("gone2:GONE", ["gone"]),                         # 앞부분만 같은 이름은 다른 앱이다
])
def test_표지가_있고_목록에_없는_위임만_낸다(tmp_path, apps, want):
    """**이 구획의 이유다** — 게이트웨이가 끄는 조건과 글자까지 같아야 한다. 더 넓으면 매 실행 재프로비저닝이 헛돌고(게이트웨이가
    안 지운다), 더 좁으면 걷어낸 앱의 위임이 옛 비밀로 남는다."""
    assert _unlisted(tmp_path, _pu(gone=True, ste=False, hwax_risk=False), apps) == want


def test_표지_없는_위임과_이름_꼴이_아닌_키는_내지_않는다(tmp_path):
    """표지 없는 위임(ste·hwax_risk·손으로 붙인 것)은 비밀 출처를 이 실행이 모른다. 이름 꼴이 아닌 키는 따옴표 없이 도는 목록과
    공백으로 가르는 PER_USER_SSO_OFF 에 실을 수 없다 — 글롭이 풀리거나 다른 이름으로 쪼개진다."""
    cfg = _pu(ste=False, manual=False, **{"a b": True, "x;y": True, "별표*": True, "ok-1.app_2": True, "str": "문자열",
                                          "other_mark": {"secret": "s", "managed_by": "손으로"}})
    assert _unlisted(tmp_path, cfg, "") == ["ok-1.app_2"]
    for odd in ("{not json", json.dumps({"heax_registry": {"per_user_sso": ["목록"]}}), json.dumps([1, 2]), "{}"):
        assert _unlisted(tmp_path, odd, "") == [], odd


def test_목록에서_뺀_앱의_남은_위임이_끄기_방아쇠다(tmp_path):
    cfg = _pu(gone=True, ste=False)
    assert _drift(tmp_path, cfg) == "gone_sso_off", "목록이 없는 박스 — 종전에는 조용했다(끌 길이 없었다)"
    assert _drift(tmp_path, cfg, box='PER_USER_SSO_APPS="other:OTHER_APP"') == "gone_sso_off"
    assert _drift(tmp_path, cfg, box='PER_USER_SSO_APPS="gone:9X"') == "", "접두를 잘못 적은 것은 뺀 것이 아니다"
    assert _drift(tmp_path, _pu(gone=False)) == "", "표지 없는 항목은 이 점검의 대상이 아니다(표지는 비밀과 함께 한 번 돌면 붙는다)"
    on = f'{GEN_APPS}\nNEWAPP_SSO_SECRET="{GEN_SECRET}"\nNEWAPP_SSO_URL="http://x/sso"\n'
    assert _drift(tmp_path, _pu(gone=True), ra=SECRET, box=on) == "reportarchive_sso newapp_sso gone_sso_off", \
        "RA·TestScope → 목록의 일반 앱 → 목록에서 뺀 앱 순서"
    listed_empty = _pu(newapp=True)        # 목록에 남기고 비밀만 비운 앱 — 한 번만 낸다
    assert _drift(tmp_path, listed_empty, box=GEN_APPS) == "newapp_sso_off"


def test_목록에서_뺀_앱의_이름이_끌_목록에_실려_간다(tmp_path):
    """실행으로 본다 — 게이트웨이는 **이름이 와야** 끈다(목록이 비었다고 스스로 지우지 않는다)."""
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "provision-config.sh").write_text('#!/usr/bin/env bash\nprintf "%s" "$PER_USER_SSO_OFF" > "$PWD/off.marker"\n')
    for cfg, box, want in ((_pu(gone=True, ste=False), "", ["gone"]),
                           (_pu(gone=True, also=True), 'PER_USER_SSO_APPS="other:OTHER_APP"\n', ["other", "also", "gone"]),
                           (_pu(gone=True), 'PER_USER_SSO_APPS="gone:GONE"\nGONE_SSO_SECRET="s"\n', []),
                           (_pu(ste=False), "", [])):
        (gw / "gateway_config.json").write_text(json.dumps(cfg))
        script = (f'set -uo pipefail; GW_DIR="{gw}"; RA_SSO_SECRET="{SECRET}"; TESTSCOPE_SSO_SECRET="ts-s"\n{box}'
                  f'{_generic_fns()}{_sso_off_lines()}\n{_reprovision_cmd()}\necho rc=$?')
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        assert "rc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
        assert (gw / "off.marker").read_text().split() == want, (cfg, box)


@pytest.mark.parametrize("apps,env,gone_after", [
    ("", {}, False),                                                                  # 목록을 통째로 비웠다
    ("other:OTHER_APP", {"OTHER_APP_SSO_SECRET": "o", "OTHER_APP_SSO_URL": "http://o/sso"}, False),
    ("gone:9X", {}, True),                                                            # 접두 오타 — 게이트웨이도 끄지 않는다
    ("gone:GONE", {"GONE_SSO_SECRET": "old"}, True),                                  # 그대로 쓰는 앱(대조)
])
def test_목록에서_뺀_앱은_한_번의_재프로비저닝으로_꺼지고_그_뒤에는_조용하다(tmp_path, apps, env, gone_after):
    """**정본은 게이트웨이다** — 그 순회와 끄기를 원문에서 꺼내 update-all 이 넘기는 값만으로 돌린다(_one_run). 걷어낸 앱은 꺼지고,
    표지 없는 위임(ste)은 그대로이며, 두 번째 실행은 아무것도 하지 않는다 — 수렴하지 않으면 매 실행 게이트웨이·에이전트서버가 내려간다."""
    prev = _pu(gone=True, ste=False)["heax_registry"]["per_user_sso"]
    box = f"PER_USER_SSO_APPS={json.dumps(apps)}\n" + "".join(f'{k}="{v}"\n' for k, v in env.items())
    after = _one_run(tmp_path, box, json.loads(json.dumps(prev)))
    assert ("gone" in after) is gone_after, after
    assert after["ste"] == prev["ste"], "표지 없는 위임은 건드리지 않는다"
    left = [t for t in _drift(tmp_path, {"heax_registry": {"per_user_sso": after}}, box=box).split()
            if t.endswith(("_sso", "_sso_off"))]
    assert left == [], f"한 번 돈 뒤에도 어긋나 있다 — 매 실행 재프로비저닝이 돈다: {left}"
    assert _one_run(tmp_path, box, after) == after, "두 번째 실행은 아무것도 바꾸지 않는다"


def test_일반_앱의_끄기는_infra_env_와_토큰_등록을_말하지_않는다():
    """일반 앱의 비밀은 게이트웨이 provision.env 에 있고, 포털 등록 토큰 길이 없어 끄면 서비스 계정으로 나간다. RA·TestScope 의
    문구('infra/.env 의 비밀이 비었는데 … 토큰 등록으로 되돌린다')를 그대로 찍으면 없는 값을 infra/.env 에서 찾게 한다."""
    i = UA.index('for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do')
    loop = UA[i:UA.index("\n    done\n", i)]
    script = "\n".join([
        "set -uo pipefail", 'bad() { echo "BAD:$*"; }', "MISSING=''", 'GW_DIR="/nonexistent"',
        '_sso_deleg_drift() { echo "reportarchive_sso_off testscope_sso_off gone_sso_off"; }',
        loop, "    done", 'echo "MISSING=[$MISSING]"'])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 0 and not r.stderr, r.stderr
    said = {ln.split("끄기: ")[1].split(" ")[0]: ln for ln in r.stdout.splitlines() if "사람별 위임 끄기" in ln}
    assert set(said) == {"reportarchive", "testscope", "gone"}, r.stdout
    for k in ("reportarchive", "testscope"):
        assert "infra/.env" in said[k] and "토큰 등록" in said[k]
    assert "infra/.env" not in said["gone"] and "토큰 등록" not in said["gone"], said["gone"]
    assert "provision.env" in said["gone"] and "PER_USER_SSO_APPS" in said["gone"] and "서비스 계정" in said["gone"]
    assert "MISSING=[reportarchive_sso_off testscope_sso_off gone_sso_off]" in r.stdout, "셋 다 재프로비저닝 방아쇠다"


# ── 만들지 않는다 ────────────────────────────────────────────────────────────
def test_start_sh_passes_the_secrets_but_never_generates_them():
    """RA·TestScope 는 남의 서버라 포털이 값을 심을 수 없다 — 먼저 생기면 게이트웨이가 그 서비스 호출을 전부 거부한다.
    포털은 TestScope 쪽 비밀을 화면 갈래(testscope_mode)로만 쓰지만, 넘기지 않으면 카드가 늘 '토큰 등록' 으로 보인다."""
    for k in ("RA_SSO_SECRET", "TESTSCOPE_SSO_SECRET"):
        assert f'--env "{k}=${{{k}:-}}"' in START
        assert not re.search(rf"^\s*{k}=\"\$\(", START, re.M), f"{k} 를 만들지 않는다"
        assert not re.search(rf"printf '{k}=", START) and f"s|^{k}=" not in START, f"{k} 를 infra/.env 에 쓰지 않는다"


def test_env_example_declares_both_secrets_empty():
    lines = (ROOT / "infra/.env.example").read_text(encoding="utf-8").splitlines()
    assert "RA_SSO_SECRET=" in lines
    assert "TESTSCOPE_SSO_SECRET=" in lines
    assert not [ln for ln in lines if re.match(r"^(RA|TESTSCOPE)_SSO_SECRET=.", ln)], "값을 적어 두지 않는다"
