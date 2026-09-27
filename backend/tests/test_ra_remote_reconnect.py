# Report Archive 재연결 — RA_HOST 하나로 라우트·RA_BASE_URL·RA_MCP_URL 이 유도되고, 로컬 RA 항목이 꺼지고,
# LLM 정본이 포털로 옮겨지는지(docs/ra-reconnect). 주소는 TEST-NET(203.0.113.x)만 쓴다 — 내부 IP 는 추적 파일 금지.
import importlib.util
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
GEN = (ROOT / "infra/scripts/gen-nginx-conf.sh").read_text(encoding="utf-8")
APPLY = (ROOT / "infra/env-kits/apply-envs.sh").read_text(encoding="utf-8")
A = "203.0.113.10"


def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# ── 3-1 구 RA 를 되살리지 않는다 — 박스 이름이 아니라 설정(RA_HOST)으로 가른다 ────────────────
def test_unless_env_disables_local_ra_only_where_ra_is_remote(monkeypatch, tmp_path):
    """⚠ 파일 경로를 **실제로** 탄다 — 첫 판은 _infra_env 를 {} 로 패치하고 setenv 만 써서, infra/.env 에만 적은 RA_HOST 를
    services.py 가 절대 못 보는 결함(_infra_env 가 HWAX_* 만 파싱)을 놓쳤다(2라운드 검토). 부팅 유닛·services.sh 는 env 를 안 넘긴다."""
    m = _services_mod()
    (tmp_path / "infra").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    monkeypatch.delenv("RA_HOST", raising=False)
    svc = {"name": "report-archive", "unless_env": "RA_HOST"}
    (tmp_path / "infra/.env").write_text("HWAX_BOX=x\n# RA_HOST=\n")
    assert m.enabled_here(svc) is True, "주석 선언·없음 = dev, 종전대로 로컬 RA"
    (tmp_path / "infra/.env").write_text(f"HWAX_BOX=x\nRA_HOST={A}   # RA 주(A)\n")
    assert m.enabled_here(svc) is False, "파일에만 적은 RA_HOST 로도 꺼져야 한다(env 없이 — 부팅 유닛 경로)"
    (tmp_path / "infra/.env").write_text("RA_HOST=   \n")
    assert m.enabled_here(svc) is True, "빈 값은 미설정과 같다"
    monkeypatch.setenv("RA_HOST", A)
    assert m.enabled_here(svc) is False, "환경변수도 그대로 먹는다"


def test_services_cli_reads_ra_host_from_the_file_like_the_boot_unit(tmp_path):
    """systemd 유닛과 같은 환경(env -i, infra/.env 파일만)에서 `services.py enabled report-archive` 가 1 을 내야 한다 —
    cae00 가이드의 확인 명령이 바로 이것이다."""
    import shutil
    lay = tmp_path / "HWAXPortal"; (lay / "infra/scripts").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/services.py", lay / "infra/scripts/services.py")
    shutil.copy(ROOT / "infra/services.yaml", lay / "infra/services.yaml")
    py = str(ROOT / "backend/.venv/bin/python")
    def rc(env_text):
        (lay / "infra/.env").write_text(env_text)
        return subprocess.run(["env", "-i", f"PATH={os.environ['PATH']}", py, str(lay / "infra/scripts/services.py"), "enabled", "report-archive"],
                              capture_output=True, text=True).returncode
    assert rc("HWAX_BOX=x\n") == 0
    assert rc(f"HWAX_BOX=x\nRA_HOST={A}   # 주석\n") == 1


def test_services_yaml_marks_both_ra_entries():
    svcs = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}
    for n in ("report-archive", "reportarchive-mcp"):
        assert svcs[n].get("unless_env") == "RA_HOST", n
    m = _services_mod()
    os.environ["RA_HOST"] = A
    try:
        assert not m.enabled_here(svcs["report-archive"]) and not m.enabled_here(svcs["reportarchive-mcp"])
    finally:
        del os.environ["RA_HOST"]


# ── 3-3 대용량·장시간 ──────────────────────────────────────────────────────────
def test_nginx_extras_cover_report_archive():
    fn = GEN[GEN.index("loc_extras() {"):]
    fn = fn[:fn.index("\n}\n") + 3]
    out = subprocess.run(["bash", "-c", fn + '\nloc_extras report-archive'], capture_output=True, text=True).stdout
    assert "client_max_body_size 2048m" in out and "proxy_read_timeout 600s" in out and "proxy_buffering off" in out


# ── 4-1 타일 세 줄 ────────────────────────────────────────────────────────────
def test_ra_tile_is_jwt_handoff_like_the_other_apps():
    tiles = {t["id"]: t for t in yaml.safe_load((ROOT / "backend/config/systems.yaml").read_text(encoding="utf-8"))["systems"]}
    ra = tiles["report-archive"]
    assert ra["integration_type"] == "jwt-handoff" and ra["audience"] == "report-archive"
    assert ra["url"] == "/report-archive/api/auth/portal-callback"
    assert "{host}" not in str(ra.get("url")), "옛 external-url 직결이 남아 있다"


# ── 3-5 LLM 정본은 포털 infra/.env, RA .env 는 폴백 ─────────────────────────────
def test_apply_envs_prefers_portal_env_over_ra_env(tmp_path):
    portal = tmp_path / "HWAXPortal"; (portal / "infra").mkdir(parents=True)
    ra = tmp_path / "ReportArchive"; ra.mkdir()
    (ra / ".env").write_text("LLM_BASE_URL=http://ra.example/v1\nLLM_MODEL=ra-model\n")
    fn = APPLY[APPLY.index("ra_env_value() {"):]
    fn = fn[:fn.index("\n}\n") + 3]
    def run(portal_env: str | None):
        f = portal / "infra/.env"
        f.unlink(missing_ok=True)
        if portal_env is not None:
            f.write_text(portal_env)
        script = f'ROOT="{portal}"\nfind_repo() {{ printf "%s" "{ra}"; }}\n{fn}\nra_env_value LLM_BASE_URL; echo " rc=$?"'
        # 폴백 경로는 grep|cut 이라 개행이 붙는다 — 실제 소비처 $(...) 는 그것을 벗기므로 토큰으로 비교한다
        return " ".join(subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.split())
    assert run("LLM_BASE_URL=http://portal.example/v1\n") == "http://portal.example/v1 rc=0"
    assert run("OTHER=1\n") == "http://ra.example/v1 rc=0", "포털에 없으면 RA .env(레거시)"
    (ra / ".env").unlink()
    assert run(None).endswith("rc=1")


# ── 1e 자동 재연결 — 실행으로 ────────────────────────────────────────────────
def _block():
    i = UA.index("_ra_envv() {")
    return UA[i:UA.index("# ── 2) 전 서비스 배포", i)]


def _run_1e(tmp_path, infra_env: str, ra_env: str | None = None, gw: bool = True):
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True, exist_ok=True); (repo / "infra").mkdir(exist_ok=True)
    (repo / "infra/.env").write_text(infra_env)
    if ra_env is not None:
        (tmp_path / "ReportArchive").mkdir(exist_ok=True); (tmp_path / "ReportArchive/.env").write_text(ra_env)
    gwdir = tmp_path / "HWAXMcpGateway"; gwdir.mkdir(exist_ok=True)
    stubs = ('hr() { :; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; }\n'
             'hwax_skip() { echo "SKIP:$1"; }; http_code() { echo 200; }\n')
    script = f'SELF_REPO="{repo}"\nGW_DIR="{gwdir if gw else ""}"\n{stubs}{_block()}\necho "RA_MCP_URL=$RA_MCP_URL"'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    return p.stdout, repo, gwdir


def test_1e_derives_route_base_url_and_mcp_url_from_ra_host_idempotently(tmp_path):
    out, repo, gw = _run_1e(tmp_path, f"RA_HOST={A}\n", ra_env="LLM_BASE_URL=http://llm.example/v1\nLLM_MODEL=glm\nLLM_API_KEY=k1\n")
    rl = (repo / "backend/config/routes.local.env").read_text()
    assert rl.count(f"report-archive=http://{A}:3000/") == 1, rl
    assert f"RA_BASE_URL=http://{A}:3000" in (repo / "backend/.env").read_text()
    assert f"RA_MCP_URL=http://{A}:3002/mcp" in (gw / "provision.env").read_text()
    inf = (repo / "infra/.env").read_text()
    assert "LLM_BASE_URL=http://llm.example/v1" in inf and "LLM_API_KEY=k1" in inf, "RA .env 에서 정본 이관"
    assert "JWKS" in out and "jwks.json" in out, "RA 담당에게 줄 JWKS 후보를 찍는다"
    # 두 번째 실행 — 같은 값으로 바꿀 뿐 줄이 늘지 않고, LLM 은 다시 옮기지 않는다
    (tmp_path / "ReportArchive/.env").write_text("LLM_BASE_URL=http://changed.example/v1\n")
    out2, _, _ = _run_1e(tmp_path, (repo / "infra/.env").read_text())
    assert (repo / "backend/config/routes.local.env").read_text().count("report-archive=") == 1
    assert (repo / "backend/.env").read_text().count("RA_BASE_URL=") == 1
    assert (gw / "provision.env").read_text().count("RA_MCP_URL=") == 1
    assert "http://llm.example/v1" in (repo / "infra/.env").read_text(), "이미 있는 정본은 건드리지 않는다"


def test_1e_replaces_a_commented_or_stale_line_instead_of_appending(tmp_path):
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True)
    (repo / "backend/config/routes.local.env").write_text("# report-archive=http://127.0.0.1:3000/\nste=http://127.0.0.1:15810/\n")
    (repo / "backend/.env").write_text("RA_BASE_URL=http://127.0.0.1:3000\nOTHER=1\n")
    _, repo, _ = _run_1e(tmp_path, f"RA_HOST={A}\nLLM_BASE_URL=x\n")
    rl = (repo / "backend/config/routes.local.env").read_text()
    assert rl.count("report-archive=") == 1 and f"report-archive=http://{A}:3000/" in rl and "ste=http://127.0.0.1:15810/" in rl
    be = (repo / "backend/.env").read_text()
    assert be.count("RA_BASE_URL=") == 1 and f"RA_BASE_URL=http://{A}:3000" in be and "OTHER=1" in be


def test_1e_without_ra_host_touches_nothing_and_records_the_skip(tmp_path):
    out, repo, gw = _run_1e(tmp_path, "OTHER=1\n")
    assert "SKIP:Report Archive 원격 재연결" in out
    assert not (repo / "backend/config/routes.local.env").exists() and not (repo / "backend/.env").exists()
    assert not (gw / "provision.env").exists()


def test_1e_rejects_a_scheme_or_port_in_ra_host(tmp_path):
    out, repo, _ = _run_1e(tmp_path, f"RA_HOST=http://{A}:3000\n")
    assert "FAIL:RA_HOST" in out and not (repo / "backend/config/routes.local.env").exists()


def test_1e_says_so_when_llm_source_is_missing(tmp_path):
    out, repo, _ = _run_1e(tmp_path, f"RA_HOST={A}\n")     # RA .env 없음, infra/.env 에도 LLM 없음
    assert "SKIP:LLM 설정 정본" in out and "LLM_BASE_URL" not in (repo / "infra/.env").read_text()


# ── §5 — 게이트웨이 쪽 ────────────────────────────────────────────────────────
def test_update_all_passes_ra_mcp_url_to_provision_and_reprovisions_on_host_drift():
    assert 'RA_MCP_URL="${RA_MCP_URL:-}" RA_WORKSPACE_SLUG="${RA_WORKSPACE_SLUG:-}"' in UA, "전엔 안 넘겨 첫 --force 가 127.0.0.1 로 덮었다"
    assert "_ra_cfg_host" in UA and 'MISSING="${MISSING:+$MISSING }reportarchive"' in UA
    assert UA.index('hr "1e)') < UA.index('hr "2)'), "1e 는 nginx 재생성(§2)·apply-envs(3.5) 앞이어야 한다"


def test_update_all_down_ra_branch_does_not_start_local_mcp_when_remote():
    i = UA.index("        reportarchive)\n")
    branch = UA[i:UA.index("        smart-twin-cluster)", i)]
    assert 'if [ -n "${RA_HOST:-}" ]' in branch
    remote, local = branch.split("\n          else\n", 1)          # 바깥 else(공백 10) — 안쪽 else(공백 12)와 가른다
    assert "UP_SVCS" not in remote and "reportarchive-mcp" in local


def test_env_example_declares_the_operator_keys():
    ex = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    for k in ("# RA_HOST=", "# LLM_BASE_URL=", "# LLM_MODEL=", "# LLM_API_KEY="):
        assert k in ex, k
    assert not re.search(r"^RA_HOST=\S", ex, re.M), "예시에 주소를 박지 않는다"


# ── 4-1 회귀 보호 — jwt-handoff 타일은 라우트가 있어도 콜백 url·타입을 지킨다(메모리 hwax-sso-downstream 교차 함정 4) ──
def _ra_tile(tmp_path, routes: str, local: str | None = None):
    from app.catalog.registry import CatalogRegistry
    from app.config import Settings
    base = tmp_path / "routes.env"; base.write_text(routes, encoding="utf-8")
    if local is not None:
        (tmp_path / "routes.local.env").write_text(local, encoding="utf-8")
    reg = CatalogRegistry(Settings(routes_path=str(base)))
    return next(s for s in reg.all() if s.id == "report-archive")


def test_ra_tile_keeps_callback_when_routed_and_when_not(tmp_path):
    with_route = _ra_tile(tmp_path, "report-archive=http://127.0.0.1:3000/\n")
    assert (with_route.integration_type, with_route.url, with_route.status) == (
        "jwt-handoff", "/report-archive/api/auth/portal-callback", "available"), "라우트가 콜백 url 을 덮거나 proxy 로 강등하면 SSO 가 통째로 꺼진다"
    overlay = _ra_tile(tmp_path, "# base 에 없음\n", local=f"report-archive=http://{A}:3000/\n")
    assert (overlay.integration_type, overlay.url) == ("jwt-handoff", "/report-archive/api/auth/portal-callback")
    unrouted = _ra_tile(tmp_path, "\n")
    assert unrouted.integration_type == "jwt-handoff" and unrouted.url.endswith("/portal-callback")


def test_launch_token_contract_for_ra_matches_the_request():
    """요청서 §4: RS256 · aud=report-archive · scope=launch · 90초 · jti. 발행기는 systems.yaml 의 audience 를 그대로 쓴다."""
    from app.auth.downstream import JwtDownstreamIssuer
    from app.auth.keystore import KeyStore
    from app.config import Settings
    import inspect
    src = inspect.getsource(JwtDownstreamIssuer.mint)
    assert '"aud": audience' in src and '"scope": "launch"' in src and '"jti"' in src
    assert Settings.model_fields["jwt_launch_ttl"].default == 90, "코드 기본값이 계약이다 — 이 박스 backend/.env 가 아니라"


# ── HTTPS 위생 ─────────────────────────────────────────────────────────────────
def test_startup_warns_when_public_scheme_and_cookie_secure_disagree():
    from app.config import Settings, startup_warnings
    codes = lambda **kw: [c for c, _ in startup_warnings(Settings(**kw))]
    assert "cookie_scheme" in codes(public_base_url="https://hwax.example", cookie_secure=False)
    assert "cookie_scheme" in codes(public_base_url="http://127.0.0.1:8088", cookie_secure=True)
    assert "cookie_scheme" not in codes(public_base_url="https://hwax.example", cookie_secure=True)
    assert "cookie_scheme" not in codes(public_base_url="http://127.0.0.1:8088", cookie_secure=False)


def test_nginx_generator_refuses_absolute_tls_paths():
    """nginx 컨테이너에는 리포(/workspace)만 바인드된다 — 절대경로 인증서는 열리지 않아 즉사한다."""
    assert 'case "$_tp" in /*|*../*)' in GEN and "상대경로" in GEN
    guard = GEN[GEN.index('for _tp in "${TLS_CERT_PATH:-}" "${TLS_KEY_PATH:-}"'):]
    guard = guard[:guard.index("done") + 4]
    r = subprocess.run(["bash", "-c", f'TLS_CERT_PATH=/etc/ssl/x.crt TLS_KEY_PATH=infra/tls/x.key; {guard}; echo alive'],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "alive" not in r.stdout and "상대경로" in r.stderr
    r2 = subprocess.run(["bash", "-c", f'TLS_CERT_PATH=infra/tls/x.crt TLS_KEY_PATH=infra/tls/x.key; {guard}; echo alive'],
                        capture_output=True, text=True)
    assert r2.returncode == 0 and "alive" in r2.stdout


def test_doctor_judges_https_termination_not_only_cert_kind():
    doc = (ROOT / "infra/scripts/ste-doctor.sh").read_text(encoding="utf-8")
    assert "4c) 공개 https 종단" in doc and 'ok https' in doc and 'bad https' in doc and 'warn https' in doc
    assert "COOKIE_SECURE" in doc and "PUBLIC_BASE_URL" in doc


def test_routes_prod_env_no_longer_carries_a_stale_ra_address():
    rp = (ROOT / "backend/config/routes.prod.env").read_text(encoding="utf-8")
    assert "report.sec.samsung.net" not in rp and "RA_HOST" in rp


def test_1e_upsert_edits_the_line_the_reader_reads(tmp_path):
    """주석 선언(`# RA_BASE_URL=`, env-sync 가 넣는다)과 활성 줄이 공존하면 읽기(tail -1)와 쓰기가 같은 줄을 봐야 한다 —
    첫 일치(주석)를 바꾸면 활성 줄이 둘 남고 어느 쪽이 이기는지 도구마다 달라진다."""
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True)
    (repo / "backend/.env").write_text("# RA_BASE_URL=\nOTHER=1\nRA_BASE_URL=http://old.example:3000\n")
    _, repo, _ = _run_1e(tmp_path, f"RA_HOST={A}\nLLM_BASE_URL=x\n")
    be = (repo / "backend/.env").read_text()
    assert be.count("RA_BASE_URL=") == 2 and be.count(f"RA_BASE_URL=http://{A}:3000") == 1, be
    assert be.startswith("# RA_BASE_URL=\n"), "주석 선언은 그대로, 활성 줄만 바뀐다"
    assert "old.example" not in be


# ── 2라운드 검토가 잡은 것들 ────────────────────────────────────────────────────
def test_1e_strips_inline_comments_like_bash_does(tmp_path):
    """env-sync 가 넣은 `# RA_HOST=   # ⚠ …` 의 `# ` 만 지우는 자연스러운 편집 — 종전엔 `x#⚠…` 이 세 파일에 ✓ 로 적혔다."""
    out, repo, gw = _run_1e(tmp_path, f"RA_HOST={A}   # ⚠ 값을 운영자가 정해야 한다\nLLM_BASE_URL=x\n")
    assert f"report-archive=http://{A}:3000/" in (repo / "backend/config/routes.local.env").read_text()
    assert f"RA_MCP_URL=http://{A}:3002/mcp\n" in (gw / "provision.env").read_text()
    assert "#" not in (repo / "backend/.env").read_text().split("RA_BASE_URL=")[1].splitlines()[0]


def test_1e_rejects_anything_but_a_hostname_or_ipv4(tmp_path):
    for bad in (f"{A}#x", f"{A}:3000", "http://ra", "ra host", "2001:db8::1"):
        out, repo, _ = _run_1e(tmp_path, f"RA_HOST={bad}\n")
        assert "FAIL:RA_HOST" in out and not (repo / "backend/config/routes.local.env").exists(), bad
    out, repo, _ = _run_1e(tmp_path, "RA_HOST=ra-a.example.test\nLLM_BASE_URL=x\n")
    assert "FAIL" not in out and "report-archive=http://ra-a.example.test:3000/" in (repo / "backend/config/routes.local.env").read_text()


def test_1e_append_never_glues_onto_a_line_without_newline(tmp_path):
    """provision.env 끝에 개행이 없으면 `RAT_TOKEN=…RA_MCP_URL=…` 한 줄이 되고 §5 가 그 토큰을 소싱한다."""
    gw = tmp_path / "HWAXMcpGateway"; gw.mkdir()
    (gw / "provision.env").write_text("RAT_TOKEN=rat_secret")          # 개행 없음
    _, _, gw = _run_1e(tmp_path, f"RA_HOST={A}\nLLM_BASE_URL=x\n")
    lines = (gw / "provision.env").read_text().splitlines()
    assert lines[0] == "RAT_TOKEN=rat_secret" and lines[1] == f"RA_MCP_URL=http://{A}:3002/mcp"


def test_1e_new_secret_files_are_created_0600(tmp_path):
    _, repo, gw = _run_1e(tmp_path, f"RA_HOST={A}\nLLM_BASE_URL=x\n")
    assert oct((repo / "backend/.env").stat().st_mode & 0o777) == "0o600"
    assert oct((gw / "provision.env").stat().st_mode & 0o777) == "0o600"
    assert oct((repo / "backend/config/routes.local.env").stat().st_mode & 0o777) == "0o644"


def test_1e_write_failure_is_a_fail_not_a_checkmark(tmp_path):
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True)
    (repo / "backend/.env").write_text("OTHER=1\n"); (repo / "backend/.env").chmod(0o444)
    try:
        out, _, _ = _run_1e(tmp_path, f"RA_HOST={A}\nLLM_BASE_URL=x\n")
    finally:
        (repo / "backend/.env").chmod(0o644)
    assert "FAIL:backend/.env" in out and "OK:backend/.env" not in out


def test_1e_partial_llm_migration_is_reported_not_celebrated(tmp_path):
    out, repo, _ = _run_1e(tmp_path, f"RA_HOST={A}\n", ra_env="LLM_BASE_URL=http://llm.example/v1\n")
    assert "BAD:LLM 설정 일부만 옮겼다" in out and "OK:LLM 설정을 RA .env 에서" not in out
    assert "LLM_BASE_URL=http://llm.example/v1" in (repo / "infra/.env").read_text()


def test_update_all_remote_ra_down_is_fatal_like_ste_mcp():
    i = UA.index("        reportarchive)\n")
    branch = UA[i:UA.index("        smart-twin-cluster)", i)]
    remote = branch.split("\n          else\n", 1)[0]
    assert remote.count("fail ") == 2 and "bad " not in remote


def test_doctor_envv_strips_inline_comment(tmp_path):
    doc = (ROOT / "infra/scripts/ste-doctor.sh").read_text(encoding="utf-8")
    fn = doc[doc.index("envv() {"):]; fn = fn[:fn.index("\n") + 1]
    f = tmp_path / "e"; f.write_text('COOKIE_SECURE=true      # true for an https domain\nENABLE_TLS="true"\n')
    out = subprocess.run(["bash", "-c", fn + f'echo "[$(envv COOKIE_SECURE {f})][$(envv ENABLE_TLS {f})]"'], capture_output=True, text=True).stdout.strip()
    assert out == "[true][true]"


def test_tls_guard_also_refuses_parent_traversal():
    guard = GEN[GEN.index('for _tp in "${TLS_CERT_PATH:-}" "${TLS_KEY_PATH:-}"'):]
    guard = guard[:guard.index("done") + 4]
    r = subprocess.run(["bash", "-c", f'TLS_CERT_PATH=infra/../../etc/x.crt TLS_KEY_PATH=infra/tls/x.key; {guard}; echo alive'], capture_output=True, text=True)
    assert r.returncode == 1 and "alive" not in r.stdout


def test_apply_envs_dry_run_masks_secret_values():
    assert '(dry-run) + $key=****(가림)' in APPLY
