# update-all 이 RA·TestScope 사람별 위임(ste 방식) 값을 infra/.env 에서 읽어 게이트웨이 프로비저닝까지 나르는지
"""docs/sso-delegation PLAN §2-2. 운영자가 할 일은 infra/.env 에 비밀 한 줄(+ TestScope 는 `testscope=` 라우트)뿐이어야 한다.
그 한 줄이 조용히 안 닿는 길이 셋 있었다 — 그것을 고정한다.

  1. 읽기 — update-all 은 infra/.env 를 통째로 소싱하지 않는다. 키를 하나씩 읽어야 한다.
  2. 방아쇠 — 위임은 heax_registry 안의 항목이라 /health 에 안 나온다. 빠진 백엔드가 없으면 재프로비저닝이 안 돌아
     비밀을 넣어도 위임이 영영 안 켜진다(ste 는 ste-gateway-check deleg 이 그 자리를 본다).
  3. 전달 — provision.env 는 소싱만 되므로 자식이 못 본다. 대입어 사슬로 하나씩 넘긴다(백틱 주석 금지 — 3라운드 실사고).

그리고 **만들지 않는다**(start.sh 2d) — 서비스 쪽이 준비되기 전에 비밀이 생기면 게이트웨이가 그 서비스 호출을 전부 거부한다.
블록은 원문 그대로 떼어 돌린다(복제하면 뜻이 갈린다).
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
START = (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8")
SECRET = "ra-secret-0123456789abcdef0123456789"
TS_SECRET = "ts-secret-0123456789abcdef0123456789"


def _fn(name: str) -> str:
    s = UA[UA.index(f"{name}() {{"):]
    return s[:s.index("\n}\n") + 3]


def _derive_block() -> str:
    i = UA.index("# RA·TestScope 사람별 위임(ste 방식, docs/sso-delegation) — 같은 자리에서 읽되")
    return UA[i:UA.index("\n# ── 5) 게이트웨이 config 정합", i)]


def _derive(tmp_path: Path, *, infra_env: str = "", backend_env: str | None = None,
            local: str | None = None, base: str | None = None, pre: str = "") -> dict:
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
    keys = ("RA_SSO_SECRET", "RA_SSO_URL", "TESTSCOPE_SSO_SECRET", "TESTSCOPE_SSO_URL", "TESTSCOPE_MCP_URL", "TESTSCOPE_EXPECTED")
    script = "\n".join([
        "set -uo pipefail",                      # update-all 과 같은 셸 옵션 — 미정의 변수가 터지는지도 함께 본다
        f'SELF_REPO="{repo}"; ROUTES_ENV="{base_f}"', pre,
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
    got = _derive(tmp_path, infra_env=f'RA_SSO_SECRET="{SECRET}"   # RA 담당과 같은 값\n# TESTSCOPE_SSO_SECRET=   # ⚠ 값을 정해야 한다\n')
    assert got["RA_SSO_SECRET"] == SECRET and got["TESTSCOPE_SSO_SECRET"] == ""


def test_an_exported_secret_wins_over_the_file(tmp_path):
    got = _derive(tmp_path, infra_env=f"RA_SSO_SECRET={SECRET}\n", pre='RA_SSO_SECRET="from-env"')
    assert got["RA_SSO_SECRET"] == "from-env"


def test_secrets_use_explicit_ifs_not_default_expansion():
    """`${SECRET:-값}` 이 허용되면 다음 사람의 리터럴 기본값이 통과한다 — test_no_tracked_secrets 와 같은 이유."""
    blk = _derive_block()
    assert 'if [ -z "${RA_SSO_SECRET:-}" ]; then RA_SSO_SECRET="$(_ra_envv RA_SSO_SECRET)"; fi' in blk
    assert 'if [ -z "${TESTSCOPE_SSO_SECRET:-}" ]; then TESTSCOPE_SSO_SECRET="$(_ra_envv TESTSCOPE_SSO_SECRET)"; fi' in blk
    assert not re.search(r"\$\{(RA|TESTSCOPE)_SSO_SECRET:-[^}]", UA)


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


# ── TestScope 주소 유도·기대 ─────────────────────────────────────────────────
def test_testscope_urls_come_from_the_route(tmp_path):
    got = _derive(tmp_path, infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n",
                  local="testscope=http://ts.example:8020/\n", base="testscope=http://wrong:8020/\n")
    assert got["TESTSCOPE_SSO_URL"] == "http://ts.example:8020/api/auth/sso", "local 오버레이가 먼저다"
    assert got["TESTSCOPE_MCP_URL"] == "http://ts.example:8022/mcp"
    assert got["TESTSCOPE_EXPECTED"] == "1"


def test_testscope_given_urls_win(tmp_path):
    got = _derive(tmp_path, infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n", base="testscope=http://ts:8020/\n",
                  pre='TESTSCOPE_MCP_URL="http://ts:9999/mcp"')
    assert got["TESTSCOPE_MCP_URL"] == "http://ts:9999/mcp" and got["TESTSCOPE_SSO_URL"] == "http://ts:8020/api/auth/sso"


def test_testscope_is_not_expected_without_both_secret_and_route(tmp_path):
    """비밀만 보고 기대하면 라우트 없는 박스가 매 실행 헛된 재프로비저닝을 돈다. 라우트만 있으면(타일만 쓰는 박스) 위임이 없다."""
    no_route = _derive(tmp_path / "a", infra_env=f"TESTSCOPE_SSO_SECRET={TS_SECRET}\n", local="#testscope=http://ts:8020/\n")
    assert no_route["TESTSCOPE_EXPECTED"] == "0" and no_route["TESTSCOPE_MCP_URL"] == ""
    assert "`testscope=` 라우트가 없다" in no_route["_log"], "비밀만 있고 라우트가 없으면 말한다"
    no_secret = _derive(tmp_path / "b", local="testscope=http://ts:8020/\n")
    assert no_secret["TESTSCOPE_EXPECTED"] == "0" and no_secret["TESTSCOPE_SSO_URL"] == ""
    assert "testscope" not in no_secret["_log"], "안 켠 박스에서는 조용하다"


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
def _drift(tmp_path: Path, cfg, *, ra="", ts="", ts_x="0") -> str:
    f = tmp_path / "gateway_config.json"
    f.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    script = f'RA_SSO_SECRET="{ra}"; TESTSCOPE_SSO_SECRET="{ts}"; TESTSCOPE_EXPECTED="{ts_x}"\n{_fn("_sso_deleg_drift")}\n_sso_deleg_drift "{f}"'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def _cfg(**pu) -> dict:
    return {"heax_registry": {"per_user_sso": {k: {"sso_url": "http://x/sso", "secret": v} for k, v in pu.items()}}}


def test_missing_or_stale_ra_delegation_triggers_reprovisioning(tmp_path):
    assert _drift(tmp_path, {}, ra=SECRET) == "reportarchive_sso", "비밀을 넣었는데 config 에 위임이 없다"
    assert _drift(tmp_path, _cfg(reportarchive="old"), ra=SECRET) == "reportarchive_sso", "비밀을 바꿨다"
    assert _drift(tmp_path, _cfg(reportarchive=SECRET), ra=SECRET) == ""
    assert _drift(tmp_path, {}, ra="") == "", "안 켠 박스는 조용하다"


def test_testscope_delegation_is_checked_only_when_expected(tmp_path):
    """라우트가 없으면 provision 이 주소를 몰라 위임을 못 만든다 — 그때 기대하면 매 실행 다시 돈다."""
    assert _drift(tmp_path, {}, ts=TS_SECRET, ts_x="0") == ""
    assert _drift(tmp_path, {}, ts=TS_SECRET, ts_x="1") == "testscope_sso"
    assert _drift(tmp_path, _cfg(testscope=TS_SECRET, reportarchive=SECRET), ra=SECRET, ts=TS_SECRET, ts_x="1") == ""
    assert _drift(tmp_path, {}, ra=SECRET, ts=TS_SECRET, ts_x="1") == "reportarchive_sso testscope_sso"


def test_drift_check_survives_odd_configs_and_keeps_secrets_off_argv(tmp_path):
    assert _drift(tmp_path, "{not json", ra=SECRET) == ""
    assert _drift(tmp_path, {"heax_registry": {"per_user_sso": {"reportarchive": "str"}}}, ra=SECRET) == "reportarchive_sso"
    fn = _fn("_sso_deleg_drift")
    assert 'python3 - "$1"' in fn and "$RA_SSO_SECRET\"" not in fn.split("python3", 1)[1].splitlines()[0]


def test_drift_feeds_missing_and_the_post_check():
    i = UA.index('for _k in $(_sso_deleg_drift "$GW_DIR/gateway_config.json"); do')
    assert UA.index("calc_missing \"$H\")\"") < i < UA.index('if [ -n "$MISSING" ]; then', i)
    assert 'MISSING="${MISSING:+$MISSING }$_k"' in UA[i:i + 400]
    post = UA[UA.index('STILL="$(calc_missing "$H")"'):UA.index("주소 드리프트 해소")]
    assert '_sso_left="$(_sso_deleg_drift "$GW_DIR/gateway_config.json")"' in post, "재프로비저닝 뒤에도 어긋나면 ✗ 다"


# ── 3. 전달 ──────────────────────────────────────────────────────────────────
def _reprovision_cmd() -> str:
    i = UA.index('( cd "$GW_DIR" && RAT_TOKEN=')
    return UA[i:UA.index("--force )", i) + len("--force )")]


def test_the_provisioner_actually_receives_the_values(tmp_path):
    """텍스트가 아니라 **실행**으로 본다 — 대입어 사슬이 깨지면 provision 이 아예 안 돈다(3라운드 실사고)."""
    gw = tmp_path / "gw"
    gw.mkdir()
    keys = ("RA_SSO_SECRET", "RA_SSO_URL", "TESTSCOPE_SSO_SECRET", "TESTSCOPE_SSO_URL", "TESTSCOPE_MCP_URL")
    (gw / "provision-config.sh").write_text(
        "#!/usr/bin/env bash\n" + "".join(f'printf "%s=%s\\n" {k} "${k}" >> "$PWD/ran.marker"\n' for k in keys))
    cmd = _reprovision_cmd()
    assert not any(ln.lstrip().startswith("`") for ln in cmd.splitlines())
    vals = {"RA_SSO_SECRET": SECRET, "RA_SSO_URL": "http://ra/api/auth/sso", "TESTSCOPE_SSO_SECRET": TS_SECRET,
            "TESTSCOPE_SSO_URL": "http://ts:8020/api/auth/sso", "TESTSCOPE_MCP_URL": "http://ts:8022/mcp"}
    # 부모 셸 변수일 뿐 export 하지 않는다 — update-all 도 export 하지 않는다(사슬이 넘겨야 자식이 본다)
    script = f'set -u; GW_DIR="{gw}"\n' + "".join(f'{k}="{v}"\n' for k, v in vals.items()) + f"{cmd}\necho rc=$?"
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert "rc=0" in r.stdout, r.stderr
    got = dict(ln.split("=", 1) for ln in (gw / "ran.marker").read_text().splitlines())
    assert got == vals


# ── 만들지 않는다 ────────────────────────────────────────────────────────────
def test_start_sh_passes_the_ra_secret_but_never_generates_either():
    """RA·TestScope 는 남의 서버라 포털이 값을 심을 수 없다 — 먼저 생기면 게이트웨이가 그 서비스 호출을 전부 거부한다."""
    assert '--env "RA_SSO_SECRET=${RA_SSO_SECRET:-}"' in START
    for k in ("RA_SSO_SECRET", "TESTSCOPE_SSO_SECRET"):
        assert not re.search(rf"^\s*{k}=\"\$\(", START, re.M), f"{k} 를 만들지 않는다"
        assert not re.search(rf"printf '{k}=", START) and f"s|^{k}=" not in START, f"{k} 를 infra/.env 에 쓰지 않는다"
    assert "TESTSCOPE_SSO_SECRET=" not in START.split("# 3. Portal", 1)[1], "포털 프로세스는 TestScope 비밀을 쓰지 않는다"


def test_env_example_declares_both_secrets_empty():
    lines = (ROOT / "infra/.env.example").read_text(encoding="utf-8").splitlines()
    assert "RA_SSO_SECRET=" in lines and "TESTSCOPE_SSO_SECRET=" in lines
