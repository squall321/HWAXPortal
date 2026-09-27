# 공용 배포 게이트·ste 자동 라우트·--with 플래그·잠금·지문 범위 — 셋업/갱신 분리의 기계 가드
"""왜 — "update-all 로 바로 셋업" 과 "routine 에 에어갭 실배포 안 섞임" 은 같은 실행에 두 뜻을 실으면
충돌한다. 셋업(명시 1회)과 갱신(routine)을 가르고, 갱신은 **사람 호출 ∧ 신선도 ∧ 전제조건** 세 신호가
모두 참일 때만 배포한다. 종전 `STE_DEPLOY=1` 게이트는 존재하지 않는 크론을 막느라 요구를 깼다
(2026-09-24 조사). 규칙은 lib 하나에 있고 ste 가 첫 사용처다(사용자 결정 D-13: 새 옵션에도 쓴다).
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/deploy-gate.sh"
UPDATE_ALL = ROOT / "infra/scripts/update-all.sh"
DEPLOY_STE = (ROOT / "infra/scripts/deploy-ste.sh").read_text(encoding="utf-8")
UA_SRC = UPDATE_ALL.read_text(encoding="utf-8")


def _gate(name="ste", *, fresh="true", precond="true", env=None, tty=False):
    """lib 을 그대로 source 해 hwax_gate 를 부른다. stdin 이 터미널이 아니므로 기본은 '사람 아님' 이다."""
    script = f'. "{LIB}"; if hwax_gate {name} --fresh "{fresh}" --precond "{precond}"; then echo GO; else echo NO; fi; echo "R=$HWAX_GATE_REASON"'
    if tty:
        script = "script -qec " + repr("bash -c " + repr(script)) + " /dev/null"
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], **(env or {})}, stdin=subprocess.DEVNULL, timeout=30)
    assert p.returncode == 0, p.stderr
    out = p.stdout.replace("\r", "")
    return ("GO" in out.split("R=")[0]), out.split("R=", 1)[1].strip() if "R=" in out else ""


def test_routine_never_deploys():
    """터미널도 --with 도 없으면(크론·파이프) 무조건 멈춘다 — 신선도·전제가 다 참이어도."""
    go, why = _gate(fresh="true", precond="true")
    assert go is False and "사람이 부른 실행이 아니다" in why


def test_with_flag_forces_even_when_up_to_date():
    """`update-all --with-ste` = 사람이 "지금 이거 해라" — 신선도가 같음이어도 간다."""
    go, _ = _gate(fresh="exit 1", precond="true", env={"HWAX_WITH": "ste"})
    assert go is True


def test_legacy_env_flag_still_forces():
    go, _ = _gate(fresh="exit 1", precond="true", env={"STE_DEPLOY": "1"})
    assert go is True


def test_forced_still_needs_the_precondition():
    """강제라도 전제(예: Teleport 세션)가 죽어 있으면 간 척하지 않는다."""
    go, why = _gate(fresh="true", precond="exit 1", env={"HWAX_WITH": "ste"})
    assert go is False and "전제조건 실패" in why


def test_interactive_but_unchanged_skips():
    """사람이 불렀어도 바뀐 게 없으면(신선도 1) 건너뛴다 — 재기동이 돌던 잡을 끊는다."""
    go, why = _gate(fresh="exit 1", precond="true", env={"UPDATE_ALL_INTERACTIVE": "1"})
    assert go is False and "이미 최신" in why


def test_unknown_freshness_is_not_treated_as_up_to_date():
    """**모름은 같음이 아니다.** 못 잰 것을 같다고 읽으면 낡은 박스를 영원히 건너뛴다.
    사람이 불렀으면 진행하고, 그 사실을 사유로 남긴다."""
    go, why = _gate(fresh="exit 2", precond="true", env={"UPDATE_ALL_INTERACTIVE": "1"})
    assert go is True and "모름" in why


def test_gate_name_is_generic():
    """ste 전용이 아니다 — 다른 이름도 같은 규칙으로 돈다(사용자 결정: 새 옵션에도 유용해야 한다)."""
    go, _ = _gate("stcx", fresh="true", precond="true", env={"HWAX_WITH": "ste stcx"})
    assert go is True
    go, _ = _gate("stcx", fresh="true", precond="true", env={"STCX_DEPLOY": "1"})
    assert go is True


# ── update-all 의 --with-<name> 파싱과 잠금 ──────────────────────────────────
def test_update_all_parses_with_flags_generically():
    assert re.search(r'--with-\*\)\s+HWAX_WITH=', UA_SRC), "--with-<name> 을 이름 무관하게 HWAX_WITH 에 모아야 한다"
    assert "export HWAX_WITH" in UA_SRC


def _lock_block() -> str:
    i = UA_SRC.index('_LOCK="${TMPDIR:-/tmp}/hwax-update-all.')
    return UA_SRC[i:UA_SRC.index("# ── 0) git 자격증명", i)]


def _fake_update_all(tmp_path, body: str, name: str = "update-all.sh"):
    """0b 블록 + 본문으로 된 가짜 update-all — 파일로 둔다(0b 가 `bash "${BASH_SOURCE[0]}"` 로 자기를 다시 돈다)."""
    f = tmp_path / name
    f.write_text(f'#!/usr/bin/env bash\nSELF_REPO="{tmp_path}"; export TMPDIR="{tmp_path}"\n{_lock_block()}\n{body}\n')
    return f


def _lock_of(tmp_path):
    import hashlib
    return tmp_path / f"hwax-update-all.{hashlib.md5(str(tmp_path).encode()).hexdigest()[:8]}.lock"


def _kill(pidfile):
    import signal
    try:
        os.kill(int(pidfile.read_text().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass


def _free(lock) -> bool:
    return subprocess.run(["flock", "-n", str(lock), "true"]).returncode == 0


def test_update_all_refuses_to_overlap(tmp_path):
    """두 개가 겹치면 2c 배포 중 재기동·provision --force·게이트웨이 down/up 이 동시에 돈다."""
    f = _fake_update_all(tmp_path, 'echo HELD; sleep 3')
    first = subprocess.Popen(["bash", str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    import time; time.sleep(0.8)
    second = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=20)
    first.wait(timeout=20)
    assert "HELD" in first.stdout.read()
    assert second.returncode == 3 and "이미 돌고 있다" in second.stderr and "HELD" not in second.stdout


def test_update_all_lock_is_not_inherited_by_daemons_it_starts(tmp_path):
    """cae00 실측(2026-09-27): 첫 update-all 이 띄운 데몬이 잠금 fd 를 물려받아, 끝난 뒤에도 모든 실행이 '이미 돌고 있다' 였다."""
    pidfile = tmp_path / "daemon.pid"
    f = _fake_update_all(tmp_path, f'( sleep 20 >/dev/null 2>&1 & echo $! > "{pidfile}" ); echo BODY; exit 0')
    try:
        r = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=20)
        assert r.returncode == 0 and "BODY" in r.stdout, r.stdout + r.stderr
        assert _free(_lock_of(tmp_path)), "데몬(sleep)이 살아 있어도 잠금은 자유여야 한다"
        r2 = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=20)
        assert r2.returncode == 0 and "BODY" in r2.stdout and "이미 돌고 있다" not in r2.stderr
    finally:
        _kill(pidfile)


def _orphan_holder(lock, pidfile):
    """옛 판(exec 9>lock; flock -n 9) 모양 — fd 9 를 물려받은 sleep 만 잠금을 쥔다."""
    old = lock.parent / "old-holder.sh"
    old.write_text(f'exec 9>"{lock}"; flock -n 9 || exit 9\n( sleep 20 >/dev/null 2>&1 & echo $! > "{pidfile}" )\nexit 0\n')
    assert subprocess.run(["bash", str(old)]).returncode == 0
    assert not _free(lock), "옛 판 모양이면 데몬이 잠금을 쥔다(재현)"


def test_update_all_replaces_a_lock_held_only_by_an_orphaned_fd(tmp_path):
    """옛 판이 fd 를 물려준 데몬만 잠금을 쥐고 있으면 — 진짜 update-all 은 없다 — 잠금 파일을 새로 만들어 진행한다."""
    lock = _lock_of(tmp_path); pidfile = tmp_path / "daemon.pid"
    try:
        _orphan_holder(lock, pidfile)
        f = _fake_update_all(tmp_path, 'echo BODY; exit 0')
        r = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=30)
        assert r.returncode == 0 and "BODY" in r.stdout, r.stdout + r.stderr
        assert "옛 판이 fd 를 물려준 데몬이다" in r.stdout and "(sleep)" in r.stdout and "진행한다" in r.stdout and "이미 돌고 있다" not in r.stderr
        assert _free(lock), "새 잠금 파일은 자유다"
    finally:
        _kill(pidfile)


def test_update_all_self_heal_never_lets_two_runs_through(tmp_path):
    """검토 실측: 고아 fd 상태에서 둘을 10ms 차로 띄우면 둘 다 stale 판정 → 서로의 새 잠금 파일을 지우고 **둘 다 진행**했다(8회 중 6회).
    스캔→rm 을 .heal 잠금 아래 하나씩 하면 정확히 하나만 진행한다."""
    import time
    lock = _lock_of(tmp_path); pidfile = tmp_path / "daemon.pid"; ran = tmp_path / "ran.log"
    f = _fake_update_all(tmp_path, f'echo "RUN:$1" >> "{ran}"; sleep 0.6; exit 0')
    for offset in (0.0, 0.005, 0.01, 0.02, 0.05):
        for _ in range(3):
            ran.unlink(missing_ok=True)
            try:
                _orphan_holder(lock, pidfile)
                a = subprocess.Popen(["bash", str(f), "A"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                time.sleep(offset)
                b = subprocess.Popen(["bash", str(f), "B"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                oa, ea = a.communicate(timeout=40); ob, eb = b.communicate(timeout=40)
            finally:
                _kill(pidfile)
            runs = ran.read_text().splitlines() if ran.exists() else []
            assert len(runs) == 1, (offset, runs, oa, ea, ob, eb)
            assert sorted([a.returncode, b.returncode]) == [0, 3], (offset, a.returncode, b.returncode, ea, eb)


def test_update_all_kill_of_the_visible_pid_stops_the_run_and_frees_the_lock(tmp_path):
    """검토: 잠금을 flock(1) 부모가 쥐면 `kill <pid>` 는 바깥만 죽여 본문이 떨어져 끝까지 돌았고 잠금은 BUSY 였다.
    바깥 bash 가 쥐고 신호를 넘기면 본문이 멈추고, 자식이 끝난 뒤에 잠금이 풀린다."""
    import time, signal
    f = _fake_update_all(tmp_path, 'for i in $(seq 1 30); do echo "step $i"; sleep 0.2; done; echo FINISHED')
    p = subprocess.Popen(["bash", str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(1.0)
    os.kill(p.pid, signal.SIGTERM)
    out, err = p.communicate(timeout=20)
    assert "FINISHED" not in out and out.count("step") < 12, out
    assert p.returncode == 143, (p.returncode, err)
    time.sleep(0.3)
    assert _free(_lock_of(tmp_path)), "본문이 죽었으면 잠금도 풀려야 한다"
    assert not subprocess.run(["pgrep", "-f", str(f)], capture_output=True).stdout, "떨어져 도는 본문이 없어야 한다"


def test_update_all_ctrl_c_keeps_the_lock_while_the_body_still_runs(tmp_path):
    """검토: 자식이 INT 를 삼키고 정상 종료하면(rclone 류) bash 본문은 계속 도는데 flock 부모는 죽어 잠금이 풀렸고,
    프롬프트가 돌아와 바로 재실행하면 겹쳤다. 바깥 bash 가 쥐면 본문이 도는 동안 잠금은 BUSY 이고 바깥도 기다린다."""
    import time, signal
    marker = tmp_path / "after"
    # `sleep 5; true` — sleep 이 마지막 명령이면 bash -c 가 exec 최적화로 sleep 자체가 되어 trap 이 사라진다(실측: 트리에 bash -c 가 없었다).
    # preexec_fn — 이 시험을 띄운 셸이 SIGINT 를 무시(SIG_IGN)하고 있으면 자식 전부가 물려받아 Ctrl-C 가 아무 데도 닿지 않는다(비대화 셸의 & 규칙).
    f = _fake_update_all(tmp_path, f'bash -c \'trap "exit 0" INT; sleep 5; true\'; echo AFTER > "{marker}"; sleep 1.5; echo DONE')
    p = subprocess.Popen(["bash", str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                         preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
    time.sleep(1.0)
    os.killpg(p.pid, signal.SIGINT)          # 터미널의 Ctrl-C 와 같다 — 그룹 전체에 INT
    time.sleep(0.8)
    assert marker.exists(), "INT 를 삼킨 자식 뒤로 본문이 이어서 돈다(재현 조건)"
    assert p.poll() is None, "바깥은 본문이 끝날 때까지 살아 있어야 한다(프롬프트가 돌아오지 않는다)"
    assert not _free(_lock_of(tmp_path)), "본문이 도는 동안 잠금은 잡혀 있어야 한다"
    out, _ = p.communicate(timeout=20)
    assert "DONE" in out and _free(_lock_of(tmp_path))


def test_update_all_ctrl_c_stops_the_body_when_its_child_dies_of_int(tmp_path):
    """`&` 로 띄운 자식은 INT 를 무시로 물려받는다(POSIX) — 그대로면 Ctrl-C 가 본문에 안 닿아 sleep 이 살아남았다(실측). 되돌려 놓았는지 본다."""
    import time, signal
    marker = tmp_path / "after"
    f = _fake_update_all(tmp_path, f'sleep 5; echo AFTER > "{marker}"; echo DONE')
    p = subprocess.Popen(["bash", str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
                         preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
    time.sleep(1.0)
    os.killpg(p.pid, signal.SIGINT)
    out, _ = p.communicate(timeout=10)
    assert not marker.exists() and "DONE" not in out, "sleep 이 INT 로 죽었으면 본문도 거기서 멈춰야 한다"
    assert p.returncode == 130, p.returncode
    assert _free(_lock_of(tmp_path))


def test_update_all_refuses_when_the_holder_is_invisible_and_does_not_delete_the_lock(tmp_path):
    """'보유자가 안 보이면 거부' 조항은 시험 보호가 0 이었다(검토) — find 가 아무 보유자도 못 보는 상황을 만든다."""
    lock = _lock_of(tmp_path); pidfile = tmp_path / "daemon.pid"
    shim = tmp_path / "shim"; shim.mkdir()
    (shim / "find").write_text("#!/usr/bin/env bash\nexit 0\n"); (shim / "find").chmod(0o755)
    try:
        _orphan_holder(lock, pidfile); ino = lock.stat().st_ino
        f = _fake_update_all(tmp_path, 'echo BODY; exit 0')
        r = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=30, env={**os.environ, "PATH": f"{shim}:{os.environ['PATH']}"})
        assert r.returncode == 3 and "BODY" not in r.stdout, r.stdout + r.stderr
        assert "보이지 않는다" in r.stderr and "이미 돌고 있다" not in r.stderr, r.stderr
        assert lock.stat().st_ino == ino, "보이지 않는 잠금은 지우지 않는다"
    finally:
        _kill(pidfile)


def test_update_all_leaked_guard_variable_does_not_bypass_the_lock(tmp_path):
    """가드 변수는 데몬으로 새어 나간다(검토) — 값에 바깥 PID 가 들어가 PPID 가 다르면 잠금을 정상으로 잡는다."""
    lock = _lock_of(tmp_path)
    f = _fake_update_all(tmp_path, 'echo HELD; sleep 2')
    first = subprocess.Popen(["bash", str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    import time; time.sleep(0.8)
    r = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=20, env={**os.environ, "HWAX_UPDATE_ALL_LOCKED": f"{lock}:1"})
    first.wait(timeout=20)
    assert r.returncode == 3 and "이미 돌고 있다" in r.stderr and "HELD" not in r.stdout


def test_update_all_without_flock_warns_and_runs_unlocked(tmp_path):
    """flock 이 없는 박스는 잠금 없이 경고만 하고 진행한다 — 종전엔 command not found(rc 127) 를 '이미 돌고 있다' 로 읽었다. 시험 보호가 0 이었다(검토)."""
    import shutil
    shim = tmp_path / "bin"; shim.mkdir()
    for tool in ("bash", "sed", "md5sum", "cut", "printf", "readlink", "find", "cat", "tr", "sort", "rm", "mktemp", "sleep", "echo", "kill", "pgrep", "seq"):
        src = shutil.which(tool)
        if src:
            (shim / tool).symlink_to(src)
    f = _fake_update_all(tmp_path, 'echo BODY; exit 0')
    r = subprocess.run(["bash", str(f)], capture_output=True, text=True, timeout=20, env={"PATH": str(shim), "HOME": os.environ.get("HOME", "/tmp")})
    assert r.returncode == 0 and "BODY" in r.stdout, r.stdout + r.stderr
    assert "flock(util-linux) 이 없어" in r.stderr


def test_update_all_lock_survives_the_upgrade_from_the_old_fd9_style(tmp_path):
    """옛 판(exec 9>lock; flock -n 9)이 §1 에서 새 판으로 exec 재실행하는 첫 회 — 같은 PID 가 옛 fd 를 쥔 채 새 0b 가 돌면 자기 자신과
    충돌해 '이미 돌고 있다'(rc 3) 가 된다. 옛 fd 를 닫고 다시 잡아야 하고, 그 뒤 띄운 데몬은 잠금을 물려받지 않아야 한다."""
    lock = _lock_of(tmp_path); pidfile = tmp_path / "daemon.pid"
    # 이름이 update-all.sh 여야 한다 — 자가치유는 보유자 cmdline 의 'update-all' 로 진짜를 가르므로, 다른 이름이면 자기 자신을 고아 fd 로 보고
    # 잠금을 지워 통과해 버린다(첫 시험판이 그랬다: fd 닫기를 빼도 초록).
    new = _fake_update_all(tmp_path, f'( sleep 20 >/dev/null 2>&1 & echo $! > "{pidfile}" ); echo "BODY:$*"; exit 0')
    old = tmp_path / "old.sh"
    old.write_text(f'exec 9>"{lock}"; flock -n 9 || exit 9\nexec env UPDATE_ALL_REEXEC=1 bash "{new}" "$@"\n')
    try:
        r = subprocess.run(["bash", str(old), "--with-ste"], capture_output=True, text=True, timeout=20)
        assert r.returncode == 0 and "BODY:--with-ste" in r.stdout and "이미 돌고 있다" not in r.stderr, r.stdout + r.stderr
        assert _free(lock), "옛 fd 를 닫고 다시 잡았으면 데몬은 잠금을 못 쥔다"
    finally:
        _kill(pidfile)


def test_update_all_lock_passes_args_exit_code_and_survives_self_reexec(tmp_path):
    """§1 이 새 버전으로 exec 재실행해도(같은 PID) 잠금은 이어지고 다시 잡으려 들지 않는다. 인자와 종료코드는 그대로 나온다. stdin 도 본문에 닿는다."""
    f = _fake_update_all(tmp_path, 'if [ "${UPDATE_ALL_REEXEC:-0}" != 1 ]; then exec env UPDATE_ALL_REEXEC=1 bash "$0" "$@"; fi\nread -r line; echo "REEXEC_OK:$*:$line"; exit 7')
    r = subprocess.run(["bash", str(f), "--with-ste"], input="from-stdin\n", capture_output=True, text=True, timeout=20)
    assert r.returncode == 7 and r.stdout.count("REEXEC_OK:--with-ste:from-stdin") == 1 and "이미 돌고 있다" not in r.stderr, r.stdout + r.stderr


# ── 1d 자동 라우트 ────────────────────────────────────────────────────────────
def _run_1d(tmp_path, *, mode: str | None, routes_local: str | None, env=None) -> tuple[str, str]:
    i = UA_SRC.index('_ste_repo_dir() {')
    block = UA_SRC[i:UA_SRC.index("# ── 2) 전 서비스 배포", i)]
    repo = tmp_path / "HWAXPortal"; (repo / "backend/config").mkdir(parents=True, exist_ok=True)
    ste = tmp_path / "SmartTwinExplorer/deploy"; ste.mkdir(parents=True, exist_ok=True)
    tenv = ste / "transport.env"; tenv.unlink(missing_ok=True)
    if mode is not None:
        tenv.write_text(f"TRANSPORT_MODE={mode}\n", encoding="utf-8")
    rl = repo / "backend/config/routes.local.env"; rl.unlink(missing_ok=True)
    if routes_local is not None:
        rl.write_text(routes_local, encoding="utf-8")
    script = f'SELF_REPO="{repo}"\nhr() {{ :; }}; ok() {{ echo "OK:$*"; }}; hwax_skip() {{ echo "SKIP:$1"; }}\n{block}'
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], **(env or {})}, timeout=20)
    assert p.returncode == 0, p.stderr
    return p.stdout, (rl.read_text(encoding="utf-8") if rl.exists() else "")


def test_autoroute_writes_the_tunnel_route_on_a_fresh_teleport_box(tmp_path):
    out, rl = _run_1d(tmp_path, mode="teleport", routes_local=None)
    assert "OK:" in out and "ste=http://127.0.0.1:15810/" in rl


def test_autoroute_never_touches_direct_boxes_or_existing_lines(tmp_path):
    _, rl = _run_1d(tmp_path, mode="direct", routes_local=None)
    assert "ste=" not in rl                                   # direct 는 주소가 박스마다 다르다
    _, rl = _run_1d(tmp_path, mode="teleport", routes_local="ste=http://203.0.113.9:15810/\n")
    assert rl.count("ste=") == 1 and "203.0.113.9" in rl          # 있으면 절대 안 건드린다
    _, rl = _run_1d(tmp_path, mode="teleport", routes_local="ste=\n")
    assert rl.strip() == "ste="                                # 빈 값 = "서빙 안 함" 명시 — 존중


def test_autoroute_can_be_switched_off(tmp_path):
    out, rl = _run_1d(tmp_path, mode="teleport", routes_local=None, env={"HWAX_STE_AUTOROUTE": "0"})
    assert rl == ""
    assert "SKIP:ste 라우트 자동 기록" in out, "껐으면 껐다고 장부에 남는다 — 조용히 지나가지 않는다"


# ── --if-stale 지문 범위 ──────────────────────────────────────────────────────
def test_fingerprint_covers_every_tree_the_deploy_ships():
    """backend/src·web 만 보면 MCP 서버·앱 정의가 낡아도 '이미 최신' 이다."""
    for d in ("backend/src", "backend/mcp_server", "apps", "frontend/dist"):
        assert d in DEPLOY_STE.split("_lman=")[1].split("\n")[0], d
    for d in ("/opt/ste/backend/src", "/opt/ste/backend/mcp_server", "/opt/ste/apps", "/opt/ste/web"):
        assert d in DEPLOY_STE, d


def test_teleport_branch_uses_the_shared_gate():
    assert "deploy-gate.sh" in DEPLOY_STE and "hwax_gate ste" in DEPLOY_STE
    assert 'STE_DEPLOY:-0}" != 1 ]; then' not in DEPLOY_STE, "옛 단일 플래그 게이트가 남아 있다"


# ── update-forges 의 ste 는 "이름을 댔는가" 로 갈린다 ─────────────────────────────
UPDATE_FORGES = (ROOT / "infra/scripts/update-forges.sh").read_text(encoding="utf-8")


def test_update_forges_routes_implicit_ste_through_the_gate():
    """문서 감사(2026-09-26)에서 잡혔다 — '경량 표적 갱신(수 분)' 을 부른 사람이 기본 대상에 딸려 온
    ste 때문에 에어갭 헤드 재배포·재기동을 무조건 받았다(게이트는 --if-stale 일 때만 켜진다).
    이름을 댔으면(`update-forges.sh ste`) 종전대로 전면 갱신, 딸려 왔으면 게이트 경유."""
    assert 'STE_NAMED=0' in UPDATE_FORGES and 'case "$_a" in ste) STE_NAMED=1' in UPDATE_FORGES
    assert '[ "${STE_NAMED:-0}" = 1 ] || _stale="--if-stale"' in UPDATE_FORGES
    assert 'deploy-ste.sh" $_stale' in UPDATE_FORGES


def test_update_forges_ste_named_and_default_differ(tmp_path):
    """실행으로 가른다 — 가짜 deploy-ste.sh 가 받은 인자를 적게 하고 두 경로를 비교한다."""
    fake = tmp_path / "infra/scripts"
    fake.mkdir(parents=True)
    (fake / "deploy-ste.sh").write_text('#!/usr/bin/env bash\nprintf "%s\\n" "args=[$*]" >> "$ARGLOG"\n')
    (fake / "deploy-ste.sh").chmod(0o755)
    body = re.search(r"^do_ste\(\) \{.*?^\}", UPDATE_FORGES, re.S | re.M).group(0)
    log = tmp_path / "args.log"
    for args, want in ((["ste"], "args=[]"), ([], "args=[--if-stale]")):
        log.write_text("")
        named = "1" if "ste" in args else "0"
        # ARGLOG 는 **export** 해야 한다 — 가짜 deploy-ste.sh 는 자식 bash 라 안 그러면 못 본다.
        script = (f'ROOT="{tmp_path}"; export ARGLOG="{log}"; STE_NAMED={named}; FAIL=0\n'
                  'hr() { :; }\ncurl() { echo 200; }\n' + body + '\ndo_ste >/dev/null 2>&1 || true\n')
        subprocess.run(["bash", "-c", script], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        assert log.read_text().strip() == want, (args, log.read_text())
