# update-all 이 바뀌지 않은 서비스를 받지도 재기동하지도 않는지 — docs/update-all-skip-unchanged (2026-09-27)
import importlib.util
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/change-detect.sh"
DEPLOY_ALL = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UPDATE_ALL = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
IMAGES = (ROOT / "infra/scripts/images-from-drive.sh").read_text(encoding="utf-8")


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'. "{LIB}"\n{script}'], capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], **env})


# ── 지문 ──────────────────────────────────────────────────────────────────────
def test_fp_changes_on_size_or_mtime_and_is_stable_otherwise(tmp_path):
    d = tmp_path / "art"; d.mkdir(); (d / "a.sif").write_bytes(b"x" * 100); os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000))
    env = tmp_path / ".env"; env.write_text("A=1\n")
    a = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip(); b = _sh(f'hwax_fp "{d}" "{env}"').stdout.strip()
    assert a == b and len(a) == 12
    os.utime(d / "a.sif", (1_700_000_100, 1_700_000_100))          # cp 없는 mtime 변화 = 새 아티팩트
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a
    os.utime(d / "a.sif", (1_700_000_000, 1_700_000_000)); env.write_text("A=2\n")   # 작은 파일은 내용
    assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() != a
    env.write_text("A=1\n"); assert _sh(f'hwax_fp "{d}" "{env}"').stdout.strip() == a
    assert _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip() != a, "없는 경로는 'missing' 으로 지문에 들어간다"
    assert _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip() == _sh(f'hwax_fp "{d}" "{tmp_path}/nope"').stdout.strip()


def test_fp_uses_size_and_mtime_not_content_for_big_files(tmp_path):
    """SIF 는 수백 MB — 내용 해시는 전/후 두 번이면 heax 에서 수십 초다. 32MB 넘는 파일은 크기·mtime 으로."""
    big = tmp_path / "big.sif"
    with open(big, "wb") as f: f.truncate(40 * 1024 * 1024)
    os.utime(big, (1_700_000_000, 1_700_000_000))
    t0 = time.time(); a = _sh(f'hwax_fp "{big}"').stdout.strip(); dt = time.time() - t0
    assert dt < 1.0, f"큰 파일 지문이 {dt:.2f}s — 내용을 읽고 있다"
    with open(big, "r+b") as f: f.seek(0); f.write(b"changed")          # 같은 크기·같은 mtime 으로 내용만 바꾸면 — 지문은 같다(의도된 한계)
    os.utime(big, (1_700_000_000, 1_700_000_000))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() == a
    os.utime(big, (1_700_000_001, 1_700_000_001))
    assert _sh(f'hwax_fp "{big}"').stdout.strip() != a, "설치(cp -p)가 mtime 을 바꾸면 지문이 바뀐다"


def test_install_if_changed_leaves_identical_files_alone_and_preserves_mtime(tmp_path):
    src = tmp_path / "cache/x.sif"; src.parent.mkdir(); src.write_bytes(b"abc"); os.utime(src, (1_600_000_000, 1_600_000_000))
    dst = tmp_path / "live/x.sif"; dst.parent.mkdir()
    r = _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?')
    assert "rc=0" in r.stdout and dst.read_bytes() == b"abc" and int(dst.stat().st_mtime) == 1_600_000_000, "cp -p — 원격 modtime 이 살아 지문이 안정된다"
    dst_ino = dst.stat().st_ino; os.utime(dst, (1_650_000_000, 1_650_000_000))
    r = _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?')
    assert "rc=1" in r.stdout and dst.stat().st_ino == dst_ino and int(dst.stat().st_mtime) == 1_650_000_000, "같은 내용은 손대지 않는다(살아 있는 인스턴스 밑을 덮어쓰지 않는다)"
    src.write_bytes(b"abcd")
    r = _sh(f'hwax_install_if_changed "{src}" "{dst}"; echo rc=$?')
    assert "rc=0" in r.stdout and dst.read_bytes() == b"abcd"


# ── 판정 ──────────────────────────────────────────────────────────────────────
def _decide(before, after, alive: bool, env=None, tmp_path=None):
    url = "http://127.0.0.1:1/x"
    stub = 'curl() { printf 200; }' if alive else 'curl() { printf 000; return 7; }'
    ledger = tmp_path / "skipped" if tmp_path else None
    e = {**(env or {})}
    if ledger: e["HWAX_RESTART_SKIPPED_FILE"] = str(ledger)
    r = _sh(f'{stub}\nif hwax_restart_needed svc "{before}" "{after}" {url}; then echo NEED; else echo SKIP; fi', **e)
    return r.stdout, (ledger.read_text() if ledger and ledger.exists() else "")


def test_restart_needed_skips_only_when_unchanged_and_alive(tmp_path):
    out, led = _decide("aaa", "aaa", True, tmp_path=tmp_path)
    assert "SKIP" in out and "재기동 생략" in out and led.strip() == "svc"
    out, _ = _decide("aaa", "bbb", True, tmp_path=tmp_path); assert "NEED" in out and "변경 있음" in out
    out, _ = _decide("aaa", "aaa", False, tmp_path=tmp_path); assert "NEED" in out and "살아 있지 않다" in out
    out, _ = _decide("aaa", "aaa", True, env={"HWAX_RESTART_ALL": "1"}, tmp_path=tmp_path); assert "NEED" in out and "HWAX_RESTART_ALL=1" in out


# ── deploy-all 이 여섯 블록·nginx 에서 판정을 부르고, 생략을 끝에 모아 낸다 ───────────────────────
def test_deploy_all_decides_per_service_and_reports_skips():
    for svc, url in (("portal", "http://127.0.0.1:8723/health"), ("mxwp", "http://127.0.0.1:8800/api/v1/healthz"), ("heax", "http://localhost:4180/health"),
                     ("signalforge", "http://127.0.0.1:18000/health"), ("aidh", "http://localhost:8001/"), ("kooremapper", "http://127.0.0.1:8700/api/health")):
        assert f'hwax_restart_needed {svc} "$_fp0" ' in DEPLOY_ALL and url in DEPLOY_ALL, svc
    assert "hwax_restart_needed nginx" in DEPLOY_ALL and 'hwax_fp "$PORTAL_DIR/infra/nginx/hwax.conf"' in DEPLOY_ALL
    assert "HWAX_RESTART_SKIPPED_FILE" in DEPLOY_ALL and "재기동 생략(변경 없음·살아 있음)" in DEPLOY_ALL
    # 지문은 git HEAD 를 앞에 붙이고(코드 변경), stop/start 는 판정 안에서만
    assert "_fp_git() {" in DEPLOY_ALL
    for tail in ('./infra/scripts/stop.sh 2>/dev/null || true   # stop → start', "bash deploy/apptainer/stop.sh 2>/dev/null || true", "bash scripts/down.sh 2>/dev/null || true", "bash platform/infra/scripts/stop.sh 2>/dev/null || true"):
        i = DEPLOY_ALL.index(tail); assert "hwax_restart_needed" in DEPLOY_ALL[i-400:i], tail


def test_images_from_drive_uses_a_persistent_cache_and_does_not_rewrite_identical_sifs():
    assert 'STAGE="${HWAX_DRIVE_CACHE:-$APPT_DIR/.drive-cache}"' in IMAGES and "mktemp -d" not in IMAGES
    assert 'hwax_install_if_changed "$STAGE/$_f" "$APPT_DIR/$_f"' in IMAGES
    assert ".drive-cache/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


# ── services.py: 갱신 결과를 커밋으로 말한다 ──────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"})


def test_services_update_reports_unchanged_or_the_commit_range(tmp_path, monkeypatch):
    origin = tmp_path / "origin"; origin.mkdir(); _git("init", "-q", "-b", "main", cwd=origin)
    (origin / "f").write_text("1\n"); _git("add", ".", cwd=origin); _git("commit", "-qm", "A", cwd=origin)
    work = tmp_path / "work"; _git("clone", "-q", str(origin), str(work), cwd=tmp_path)
    m = _services_mod(); monkeypatch.setattr(m, "LOG_DIR", tmp_path / "logs")
    svc = {"name": "x", "dir": str(work)}
    r = m.update_one(svc); assert r.startswith("updated: unchanged ("), r
    (origin / "f").write_text("2\n"); _git("commit", "-qam", "B", cwd=origin)
    r = m.update_one(svc); assert "→" in r and "unchanged" not in r, r
    r = m.update_one(svc); assert r.startswith("updated: unchanged ("), r


# ── update-sites: unchanged·살아 있음이면 down/up 을 건너뛴다 ──────────────────────────
def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""'); j = UPDATE_SITES.index("# 1) 포털 먼저", i)
    return UPDATE_SITES[i:j]


def _run_restart(tmp_path, update_line: str, status_line: str, env=None):
    log = tmp_path / "svc.log"; log.unlink(missing_ok=True)     # 시나리오마다 새 기록 — 이어 쓰면 앞 시나리오의 호출이 섞인다
    svc = tmp_path / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\ncase "$1" in update) echo "  · x  {update_line}";; status) echo "  {status_line} x";; esac\nexit 0\n'); svc.chmod(0o755)
    script = f'SVC="{svc}"\nshow_cause() {{ :; }}\n{_restart_svc_block()}\nrestart_svc x; echo "rc=$?"; echo "SKIPPED=[$SKIPPED_RESTART]"'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30, env={"PATH": os.environ["PATH"], **(env or {})})
    return r.stdout, (log.read_text().splitlines() if log.exists() else [])


def test_update_sites_skips_down_up_when_unchanged_and_alive(tmp_path):
    out, calls = _run_restart(tmp_path, "updated: unchanged (abc1234)", "✓ up")
    assert "재기동 생략" in out and "SKIPPED=[ x]" in out and calls == ["update x", "status x"], (out, calls)
    out, calls = _run_restart(tmp_path, "updated: abc1234→def5678", "✓ up")
    assert "재기동 생략" not in out and calls == ["update x", "down x", "up x"], (out, calls)
    out, calls = _run_restart(tmp_path, "updated: unchanged (abc1234)", "✗ down")
    assert calls == ["update x", "status x", "down x", "up x"], "죽어 있으면 띄운다"
    out, calls = _run_restart(tmp_path, "updated: unchanged (abc1234)", "✓ up", env={"HWAX_FORCE_RESTART": "agent-server x"})
    assert calls == ["update x", "down x", "up x"], "§3.5 가 .env 를 고친 서비스는 강제"
    out, calls = _run_restart(tmp_path, "updated: unchanged (abc1234)", "✓ up", env={"HWAX_RESTART_ALL": "1"})
    assert calls == ["update x", "down x", "up x"], "HWAX_RESTART_ALL=1 은 종전 동작"
    out, calls = _run_restart(tmp_path, "✗ x  FAIL: pull", "✓ up")
    assert "rc=1" in out and calls == ["update x", "down x", "up x"], "갱신 실패는 종료코드로 올리되 기동은 한다"


def test_update_all_forces_agent_server_restart_when_apply_envs_changed_its_env():
    i = UPDATE_ALL.index('_ae0="$(sha256sum "${AGENT_DIR:-/nonexistent}/.env"'); j = UPDATE_ALL.index('hr "4) update-sites', i)
    blk = UPDATE_ALL[i:j]
    assert 'hr "3.5)' in blk and '_ae1="$(sha256sum' in blk and 'export HWAX_FORCE_RESTART="${HWAX_FORCE_RESTART:+$HWAX_FORCE_RESTART }agent-server"' in blk
