# update-all 이 바뀌지 않은 서비스를 받지도 재기동하지도 않는지 — 기준은 '마지막으로 띄운 시점의 지문'(docs/update-all-skip-unchanged, 2026-09-27)
import importlib.util
import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/change-detect.sh"
DEPLOY_ALL = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UPDATE_ALL = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
IMAGES = (ROOT / "infra/scripts/images-from-drive.sh").read_text(encoding="utf-8")
NOT_ROOT = pytest.mark.skipif(os.geteuid() == 0, reason="root 는 권한을 무시한다")


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'. "{LIB}"\n{script}'], capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], **env})


def _git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


# ── 지문 ──────────────────────────────────────────────────────────────────────
def test_fp_changes_on_size_or_mtime_and_is_stable_otherwise(tmp_path):
    d = tmp_path / "art"; d.mkdir(); (d / "a.sif").write_bytes(b"x" * 100); os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000))
    env = tmp_path / ".env"; env.write_text("A=1\n")
    a = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip(); b = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip()
    assert a == b and len(a) == 12
    os.utime(d / "a.sif", (1_700_000_100, 1_700_000_100))
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a
    os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000)); env.write_text("A=2\n")
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a, "작은 파일은 내용"
    env.write_text("A=1\n"); assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() == a
    m1 = _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip(); m2 = _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip()
    assert m1 != a and m1 == m2, "없는 경로는 'missing' 으로 지문에 들어가고 안정적이다"


def test_fp_uses_size_and_mtime_not_content_for_big_files(tmp_path):
    big = tmp_path / "big.sif"
    with open(big, "wb") as f: f.truncate(40 * 1024 * 1024)
    os.utime(big, (1_700_000_000, 1_700_000_000))
    t0 = time.time(); a = _sh(f'hwax_fp "{big}"').stdout.strip(); dt = time.time() - t0
    assert dt < 1.0, f"큰 파일 지문이 {dt:.2f}s — 내용을 읽고 있다"
    with open(big, "r+b") as f: f.seek(0); f.write(b"changed")
    os.utime(big, (1_700_000_000, 1_700_000_000))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() == a, "같은 크기·mtime 이면 같다(의도된 한계 — 설치가 cp -p·cmp 라 실제론 안 생긴다)"
    os.utime(big, (1_700_000_001, 1_700_000_001))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() != a


def test_install_if_changed_returns_installed_same_or_failed(tmp_path):
    src = tmp_path / "cache/x.sif"; src.parent.mkdir(); src.write_bytes(b"abc"); os.utime(src, (1_600_000_000, 1_600_000_000))
    dst = tmp_path / "live/x.sif"; dst.parent.mkdir()
    assert "rc=0" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and int(dst.stat().st_mtime) == 1_600_000_000
    ino = dst.stat().st_ino; os.utime(dst, (1_650_000_000, 1_650_000_000))
    assert "rc=1" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and dst.stat().st_ino == ino, "같은 내용은 손대지 않는다"
    src.write_bytes(b"abcd"); assert "rc=0" in _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?').stdout and dst.read_bytes() == b"abcd"


@NOT_ROOT
def test_install_if_changed_reports_a_failed_copy_loudly(tmp_path):
    """검토: cp 실패가 '같음 — 그대로' 로 찍히고 rc 0 이었다 — 옛 SIF 가 조용히 남는다."""
    src = tmp_path / "x.sif"; src.write_bytes(b"new"); dst = tmp_path / "x-live.sif"; dst.write_bytes(b"old"); dst.chmod(0o444)   # 쓸 수 없는 대상(다른 소유자와 같다)
    try:
        r = _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?')
        assert "rc=2" in r.stdout and "설치 실패" in r.stderr and dst.read_bytes() == b"old", r.stdout + r.stderr
    finally:
        dst.chmod(0o644)


# ── 판정 — 마지막 기동 지문 기준 ────────────────────────────────────────────────────
def _decide(tmp_path, cur, alive=(True,), env=None, state=None):
    urls = " ".join(f"http://127.0.0.1:{i}/h" for i in range(len(alive)))
    curl = "curl() { case \"$*\" in " + " ".join(f'*127.0.0.1:{i}/*) printf {"200" if a else "000"};;' for i, a in enumerate(alive)) + " esac; }"
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    if state is not None: (st / "svc").write_text(state + "\n")
    e = {"HWAX_RESTART_STATE_DIR": str(st), "HWAX_RESTART_SKIPPED_FILE": str(tmp_path / "skipped"), **(env or {})}
    r = _sh(f'{curl}\nif hwax_restart_needed svc "{cur}" {urls}; then echo NEED; else echo SKIP; fi', **e)
    return r.stdout


def test_restart_needed_compares_with_the_last_start_not_with_block_entry(tmp_path):
    """검토(1라운드, high): '블록 전/후' 기준은 §1 의 git reset·§1c/1d/1e 의 .env·routes 기록·운영자 편집이 전부 블록 밖이라 안 보여
    백엔드 커밋과 설정 변경이 재기동을 영원히 못 일으켰다. 기준은 마지막으로 띄운 시점의 지문이다."""
    assert "NEED" in _decide(tmp_path, "aaa") and "기록이 없다" in _decide(tmp_path, "aaa"), "기록이 없으면 재기동"
    out = _decide(tmp_path, "aaa", state="aaa"); assert "SKIP" in out and "재기동 생략" in out and (tmp_path / "skipped").read_text().strip() == "svc"
    out = _decide(tmp_path, "bbb", state="aaa"); assert "NEED" in out and "마지막 기동 뒤 변경 있음" in out, "블록 안에서 전후가 같아도 마지막 기동과 다르면 재기동"
    out = _decide(tmp_path, "aaa", alive=(False,), state="aaa"); assert "NEED" in out and "답하지 않는다" in out
    out = _decide(tmp_path, "aaa", alive=(True, False), state="aaa"); assert "NEED" in out, "인스턴스가 여럿이면 하나라도 죽었으면 띄운다"
    out = _decide(tmp_path, "aaa", state="aaa", env={"HWAX_RESTART_ALL": "1"}); assert "NEED" in out and "HWAX_RESTART_ALL=1" in out


def test_mark_started_writes_the_state_file(tmp_path):
    st = tmp_path / "s"
    r = _sh('hwax_mark_started portal "abc|def"; hwax_last_fp portal', HWAX_RESTART_STATE_DIR=str(st))
    assert r.stdout.strip() == "abc|def" and (st / "portal").read_text() == "abc|def\n"


# ── deploy-all 포털 블록 — 실 git 리포 + 스텁으로 통째로 돈다 ─────────────────────────────
def _portal_block() -> str:
    i = DEPLOY_ALL.index('  ( cd "$PORTAL_DIR"\n    git_update'); j = DEPLOY_ALL.index('skip "portal failed (see above)"', i) + len('skip "portal failed (see above)"')
    return DEPLOY_ALL[i:j]


def _portal_harness(tmp_path):
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "backend/app").mkdir(parents=True); (origin / "backend/app/main.py").write_text("VERSION=1\n")
    (origin / ".gitignore").write_text("infra/.env\nbackend/.env\nbackend/config/routes.local.env\ninfra/apptainer/\nfrontend/dist/\ninfra/.state/\n")
    _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    repo = tmp_path / "portal"; _git("clone", "-q", str(origin), str(repo), cwd=tmp_path)
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/apptainer").mkdir(); (repo / "frontend/dist").mkdir(parents=True); (repo / "backend/config").mkdir(parents=True)
    (repo / "infra/.env").write_text("HTTP_PORT=8088\n"); (repo / "backend/.env").write_text("RA_BASE_URL=http://127.0.0.1:3000\n"); (repo / "infra/apptainer/portal.sif").write_bytes(b"sif"); (repo / "frontend/dist/index.html").write_text("x")
    calls = tmp_path / "calls.log"
    for name in ("images-from-drive.sh", "stop.sh", "start.sh"):
        f = repo / "infra/scripts" / name; f.write_text(f'#!/usr/bin/env bash\necho {name} >> "{calls}"\n'); f.chmod(0o755)
    shim = tmp_path / "bin"; shim.mkdir(); (shim / "curl").write_text("#!/usr/bin/env bash\nprintf 200\n"); (shim / "curl").chmod(0o755)
    fp_git = DEPLOY_ALL[DEPLOY_ALL.index("_fp_git() {"):]; fp_git = fp_git[:fp_git.index("\n") + 1]
    ngfp = DEPLOY_ALL[DEPLOY_ALL.index("_ngfp() {"):]; ngfp = ngfp[:ngfp.index("\n}\n") + 3]
    def run():
        script = (f'set -uo pipefail\nPORTAL_DIR="{repo}"; RESTART=0\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{tmp_path}/state" HWAX_RESTART_SKIPPED_FILE="{tmp_path}/skipped"\n'
                  f'ok() {{ echo "OK:$*"; }}; skip() {{ echo "SKIP:$*"; }}; set_remote() {{ :; }}\n'
                  f'git_update() {{ git fetch -q origin main && git reset -q --hard origin/main; }}\n{fp_git}{ngfp}\n{_portal_block()}')
        calls.unlink(missing_ok=True)
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(tmp_path)})
        return r.stdout + r.stderr, (calls.read_text().split() if calls.exists() else [])
    return origin, repo, run


def test_portal_block_restarts_on_first_run_then_skips_then_restarts_on_code_or_env_change(tmp_path):
    origin, repo, run = _portal_harness(tmp_path)
    out, calls = run(); assert calls == ["images-from-drive.sh", "stop.sh", "start.sh"] and "기록이 없다" in out, (out, calls)
    out, calls = run(); assert calls == ["images-from-drive.sh"] and "재기동 생략" in out, "두 번째: 받기만 하고 재기동은 생략"
    # §1 이 먼저 당긴 것처럼 — 블록 밖에서 리포가 새 커밋으로 옮겨진다
    (origin / "backend/app/main.py").write_text("VERSION=2\n"); _git("commit", "-qam", "B", cwd=origin)
    _git("fetch", "-q", "origin", cwd=repo); _git("reset", "-q", "--hard", "origin/main", cwd=repo)
    out, calls = run(); assert "stop.sh" in calls and "start.sh" in calls and "변경 있음" in out, "백엔드 커밋(§1 이 이미 당김)이 재기동을 일으킨다"
    out, calls = run(); assert calls == ["images-from-drive.sh"], "다시 안정"
    (repo / "backend/.env").write_text("RA_BASE_URL=http://ra.example:3000\n")     # §1e 가 블록 전에 적은 것과 같다
    out, calls = run(); assert "start.sh" in calls, ".env 변경(블록 밖)이 재기동을 일으킨다"
    (repo / "backend/config/routes.local.env").write_text("ste=http://127.0.0.1:15810/\n")   # §1d
    out, calls = run(); assert "start.sh" in calls, "routes.local.env 변경이 재기동을 일으킨다"
    out, calls = run(); assert calls == ["images-from-drive.sh"]


def test_portal_block_does_not_record_a_start_that_failed(tmp_path):
    origin, repo, run = _portal_harness(tmp_path)
    (repo / "infra/scripts/start.sh").write_text('#!/usr/bin/env bash\necho start.sh >> "$(dirname "$0")/../../../calls.log"\nexit 1\n')
    out, calls = run(); assert "SKIP:portal failed" in out and not (tmp_path / "state/portal").exists(), "실패한 기동은 기준이 되지 않는다 — 다음 실행이 다시 시도한다"


def test_deploy_all_wires_every_service_and_nginx_to_the_last_start_baseline():
    for svc in ("portal", "mxwp", "heax", "signalforge", "aidh", "kooremapper"):
        assert f'hwax_restart_needed {svc} "$_cur"' in DEPLOY_ALL and f'hwax_mark_started {svc} "$_cur"' in DEPLOY_ALL, svc
    assert 'hwax_restart_needed nginx "$_ngcur"' in DEPLOY_ALL and 'hwax_mark_started nginx "$_ngcur"' in DEPLOY_ALL and "_ngfp() {" in DEPLOY_ALL
    assert 'HWAX_RESTART_STATE_DIR="${HWAX_RESTART_STATE_DIR:-$PORTAL_DIR/infra/.state/restart-fp}"' in DEPLOY_ALL
    assert '"$HWAX_RESTART_SKIPPED_FILE"\' EXIT' in DEPLOY_ALL, "끊긴 실행이 장부 파일을 /tmp 에 남기지 않는다"
    for two in ("http://127.0.0.1:8800/api/v1/healthz http://127.0.0.1:5173/", "http://127.0.0.1:18000/health http://127.0.0.1:17370/", "http://127.0.0.1:8700/api/health http://127.0.0.1:8701/"):
        assert two in DEPLOY_ALL, "인스턴스가 여럿인 서비스는 둘 다 답해야 생략"
    assert "_fp0" not in DEPLOY_ALL, "블록 진입 시점 기준은 버렸다"
    assert "infra/.state/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_images_from_drive_syncs_a_persistent_cache_and_fails_loudly():
    assert '"$RCLONE" sync --progress "$SRC/" "$STAGE/"' in IMAGES and 'STAGE="${HWAX_DRIVE_CACHE:-$APPT_DIR/.drive-cache}"' in IMAGES and "mktemp -d" not in IMAGES
    assert 'case $_rc in 0) echo "  ✓ staged $_f' in IMAGES and "설치 실패 — 위 사유\"; exit 1" in IMAGES
    assert '[ -f "$REPO_ROOT/frontend/dist/index.html" ] && [ -f "$APPT_DIR/.frontend-dist.applied.tar.gz" ]' in IMAGES, "dist 가 지워졌으면 같은 tar 라도 다시 푼다"


# ── services.py fp ────────────────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_services_fp_tracks_head_and_env_and_does_not_break_on_non_git(tmp_path):
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "f").write_text("1\n"); _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    work = tmp_path / "work"; _git("clone", "-q", str(origin), str(work), cwd=tmp_path)
    m = _services_mod(); svc = {"name": "x", "dir": str(work)}
    a = m.service_fp(svc); assert len(a) == 16
    (work / ".env").write_text("K=1\n"); b = m.service_fp(svc); assert b != a
    (origin / "f").write_text("2\n"); _git("commit", "-qam", "B", cwd=origin); _git("fetch", "-q", "origin", cwd=work); _git("reset", "-q", "--hard", "origin/main", cwd=work)
    c = m.service_fp(svc); assert c not in (a, b), "블록 밖에서 옮겨진 HEAD 도 지문에 든다"
    plain = tmp_path / "plain"; plain.mkdir(); assert len(m.service_fp({"name": "y", "dir": str(plain)})) == 16
    assert m.service_fp({"name": "z", "dir": str(tmp_path / "nope")}) == m.service_fp({"name": "z", "dir": str(tmp_path / "nope")})


# ── update-sites — 마지막 기동 지문·살아 있음·강제 아님이면 down/up 생략 ─────────────────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""'); j = UPDATE_SITES.index("# 1) 포털 먼저", i)
    return UPDATE_SITES[i:j]


def _run_restart(tmp_path, fp: str, status_line: str, update_line: str = "  · x  updated: unchanged (abc1234)", env=None, keep_state=False):
    log = tmp_path / "svc.log"; log.unlink(missing_ok=True)
    st = tmp_path / "state"; st.mkdir(exist_ok=True)
    if not keep_state:
        for f in st.glob("*"): f.unlink()
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\ncase "$1" in update) echo "{update_line}";; fp) echo "{fp}";; status) echo "  {status_line} x";; esac\nexit 0\n'); svc.chmod(0o755)
    script = f'SVC="{svc}"\n. "{LIB}"\nexport HWAX_RESTART_STATE_DIR="{st}"\nshow_cause() {{ :; }}\n{_restart_svc_block()}\nrestart_svc x; echo "rc=$?"; echo "SKIPPED=[$SKIPPED_RESTART]"'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env={"PATH": os.environ["PATH"], **(env or {})})
    return r.stdout, (log.read_text().splitlines() if log.exists() else []), ((st / "x").read_text().strip() if (st / "x").exists() else None)


def test_update_sites_uses_the_last_start_fingerprint(tmp_path):
    out, calls, state = _run_restart(tmp_path, "f1", "✓ up")
    assert calls == ["update x", "fp x", "down x", "up x"] and state == "f1", ("처음(기록 없음)은 재기동하고 기록한다", out, calls)
    out, calls, state = _run_restart(tmp_path, "f1", "✓ up", keep_state=True)
    assert "재기동 생략" in out and calls == ["update x", "fp x", "status x"] and "SKIPPED=[ x]" in out, (out, calls)
    out, calls, state = _run_restart(tmp_path, "f2", "✓ up", keep_state=True)
    assert calls == ["update x", "fp x", "down x", "up x"] and state == "f2", "지문이 달라졌으면(코드·.env — §2 가 미리 당겼어도) 재기동"
    out, calls, _ = _run_restart(tmp_path, "f2", "✗ down", keep_state=True)
    assert calls == ["update x", "fp x", "status x", "down x", "up x"], "죽어 있으면 띄운다"
    out, calls, _ = _run_restart(tmp_path, "f2", "✓ up", keep_state=True, env={"HWAX_FORCE_RESTART": "agent-server x"})
    assert calls == ["update x", "fp x", "down x", "up x"], "강제 목록"
    out, calls, _ = _run_restart(tmp_path, "f2", "✓ up", keep_state=True, env={"HWAX_RESTART_ALL": "1"})
    assert calls == ["update x", "fp x", "down x", "up x"], "HWAX_RESTART_ALL=1 은 종전 동작"
    out, calls, _ = _run_restart(tmp_path, "f2", "✓ up", update_line="  ✗ x  FAIL: pull", keep_state=True)
    assert "rc=1" in out and calls == ["update x", "fp x", "down x", "up x"], "갱신 실패는 종료코드로 올리되 기동은 한다"
    out, calls, _ = _run_restart(tmp_path, "", "✓ up", keep_state=True)
    assert calls == ["update x", "fp x", "down x", "up x"], "지문을 못 구하면(빈 값) 모름 → 재기동"


def test_update_all_no_longer_hand_wires_the_env_window():
    assert "_ae0" not in UPDATE_ALL and "_ae1" not in UPDATE_ALL, "§3.5 전/후 창은 §1c·운영자 편집을 못 봤다 — 상태 기준으로 대체"
