# 10-27 수정 요청 백업 셋(HP-04 · HP-17 · HP-18) — 크론의 빈 환경 · 비밀 묶음의 자리와 박스 파일 · crontab 을 못 읽으면 쓰지 않는다
"""왜 — 셋 다 '조용히 잃는' 결함이다(docs/request-1027/01-HWAXPortal.md).

HP-04  크론은 XDG_RUNTIME_DIR · DBUS_SESSION_BUS_ADDRESS 없이 돌아 `apptainer exec instance://` 가 rc 255 — KooRemapper 덤프가 매일 실패.
HP-17  비밀 묶음에서 infra/.env 와 backend/.env 가 같은 자리(portal/.env)라 앞의 것이 사라졌고, 박스 파일 · crontab 이 빠졌다.
HP-18  `crontab -l 2>/dev/null` 이 일시 실패를 빈 목록으로 읽어, 줄 하나를 고치려다 백업 · 감시 · 터널 줄을 통째로 지운다.

스크립트는 임시 리포 트리에 복사해 돌린다 — 형제 리포 · 진짜 crontab · 진짜 apptainer 를 건드리지 않는다(가짜를 PATH 앞에 둔다).
"""
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

FAKE_CRONTAB = r"""#!/usr/bin/env bash
# 가짜 crontab — $CT_STATE 가 지금 목록, $CT_MODE 가 -l 의 꼴(ok · none · fail). 쓰기 · 지우기는 $CT_STATE.log 에 한 줄씩.
case "$1" in
  -l) case "${CT_MODE:-ok}" in
        none) echo "no crontab for $(id -un)" >&2; exit 1 ;;
        fail) echo "crontab: cannot open crontab file for reading: Resource temporarily unavailable" >&2; exit 1 ;;
        *) cat "$CT_STATE" ;;
      esac ;;
  -) cat > "$CT_STATE.new" && mv "$CT_STATE.new" "$CT_STATE"; echo write >> "$CT_STATE.log" ;;
  -r) : > "$CT_STATE"; echo remove >> "$CT_STATE.log" ;;
  *) echo "가짜 crontab: 모르는 인자 $*" >&2; exit 2 ;;
esac
"""

# 진짜 apptainer 처럼 — 두 변수가 없으면 instance exec 가 255 로 끝난다(10-16 실측). 본 값은 $AP_ENV_LOG 에 적는다.
FAKE_APPTAINER = r"""#!/usr/bin/env bash
case "$1" in
  instance) printf 'INSTANCE NAME    PID    IP    IMAGE\nkoorm_postgres   1234          /x.sif\n' ;;
  exec)
    printf 'XDG=%s\nDBUS=%s\n' "${XDG_RUNTIME_DIR:-}" "${DBUS_SESSION_BUS_ADDRESS:-}" > "$AP_ENV_LOG"
    [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || { echo "FATAL: DBUS_SESSION_BUS_ADDRESS is not set" >&2; exit 255; }
    echo "-- PostgreSQL database dump" ;;
  *) exit 2 ;;
esac
"""

FAKE_LOGROTATE = """#!/usr/bin/env bash
echo "considering log /tmp/x.log"
"""


def _exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture()
def tree(tmp_path):
    """임시 형제 리포 트리 — HWAXPortal(스크립트 사본) · 가짜 bin · HOME · 백업 자리."""
    portal = tmp_path / "HWAXPortal"
    for rel in ("infra/scripts/backup-local.sh", "infra/scripts/install-watchdog.sh", "infra/scripts/install-logrotate.sh",
                "infra/scripts/lib/crontab-safe.sh", "infra/logrotate/hwax.conf.tmpl"):
        (portal / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, portal / rel)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    _exe(bin_ / "crontab", FAKE_CRONTAB)
    _exe(bin_ / "apptainer", FAKE_APPTAINER)
    _exe(bin_ / "logrotate", FAKE_LOGROTATE)
    home = tmp_path / "home"
    home.mkdir()
    ct = tmp_path / "crontab.state"
    env = {"HOME": str(home), "PATH": f"{bin_}:/usr/bin:/bin", "USER": "tester", "LOGNAME": "tester", "LANG": "C.UTF-8",
           "BACKUP_ROOT": str(tmp_path / "backups"), "HWAX_BOX": "t", "CT_STATE": str(ct),
           "AP_ENV_LOG": str(tmp_path / "apptainer.env")}
    return {"tmp": tmp_path, "portal": portal, "ct": ct, "env": env}


def _run(tree, argv, **extra):
    env = {**tree["env"], **extra}
    return subprocess.run(["bash", *argv], cwd=tree["tmp"], env=env, capture_output=True, text=True, timeout=60)


def _writes(tree) -> list[str]:
    log = Path(str(tree["ct"]) + ".log")
    return log.read_text().split() if log.exists() else []


# ── HP-18 — crontab 을 못 읽으면 쓰지 않는다 ─────────────────────────────

def _installers(tree):
    s = tree["portal"] / "infra/scripts"
    return {
        "backup": ([str(s / "backup-local.sh"), "--install-cron"], str(s / "backup-local.sh")),
        "watchdog": ([str(s / "install-watchdog.sh")], "# hwax-watchdog"),
        "logrotate": ([str(s / "install-logrotate.sh")], "# hwax-logrotate"),
    }


@pytest.mark.parametrize("which", ["backup", "watchdog", "logrotate"])
def test_HP18_읽기_실패면_쓰지_않고_1로_끝난다(tree, which):
    argv, _mark = _installers(tree)[which]
    tree["ct"].write_text("KEEP_A\nKEEP_B\n")
    r = _run(tree, argv, CT_MODE="fail")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "✗" in r.stdout + r.stderr
    assert _writes(tree) == [], "못 읽었는데 썼다 — 백업 · 감시 · 터널 줄이 지워진다"
    assert tree["ct"].read_text() == "KEEP_A\nKEEP_B\n"


@pytest.mark.parametrize("which", ["backup", "watchdog", "logrotate"])
def test_HP18_no_crontab_은_빈_목록이다(tree, which):
    argv, mark = _installers(tree)[which]
    r = _run(tree, argv, CT_MODE="none")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = tree["ct"].read_text().splitlines()
    assert len(lines) == 1 and mark in lines[0], lines
    assert _writes(tree) == ["write"]


@pytest.mark.parametrize("which", ["backup", "watchdog", "logrotate"])
def test_HP18_남의_줄은_두고_내_옛_줄만_바꾼다(tree, which):
    argv, mark = _installers(tree)[which]
    tree["ct"].write_text(f"KEEP_A\n0 0 * * * old {mark}\nKEEP_B\n")
    r = _run(tree, argv, CT_MODE="ok")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = tree["ct"].read_text().splitlines()
    assert lines[:2] == ["KEEP_A", "KEEP_B"] and len(lines) == 3 and mark in lines[2] and "old" not in lines[2], lines
    r = _run(tree, argv, CT_MODE="ok")
    assert r.returncode == 0 and "최신" in r.stdout, r.stdout + r.stderr
    assert _writes(tree) == ["write"], "이미 최신인데 다시 썼다"


@pytest.mark.parametrize("which", ["watchdog", "logrotate"])
def test_HP18_지우기도_읽기_실패면_쓰지_않는다(tree, which):
    argv, mark = _installers(tree)[which]
    tree["ct"].write_text(f"KEEP_A\n* * * * * x {mark}\n")
    r = _run(tree, [*argv, "--remove"], CT_MODE="fail")
    assert r.returncode == 1 and _writes(tree) == [], r.stdout + r.stderr
    r = _run(tree, [*argv, "--remove"], CT_MODE="ok")
    assert r.returncode == 0, r.stdout + r.stderr
    assert tree["ct"].read_text().splitlines() == ["KEEP_A"]


def test_HP18_빈_표지는_거절한다(tree):
    tree["ct"].write_text("KEEP_A\n")
    lib = tree["portal"] / "infra/scripts/lib/crontab-safe.sh"
    r = _run(tree, ["-c", f'. "{lib}"; hwax_crontab_replace ""'], CT_MODE="ok")
    assert r.returncode == 1 and _writes(tree) == [] and tree["ct"].read_text() == "KEEP_A\n"


def test_HP18_datamigrate_는_못_읽으면_크론을_지우지_않는다(tree, monkeypatch):
    scripts = str(ROOT / "infra/scripts")
    sys.path.insert(0, scripts)
    try:
        import datamigrate as D
    finally:
        while scripts in sys.path:            # datamigrate 도 제 자리를 넣는다 — 뒤 시험에 services.py 가 비치지 않게 모두 뺀다
            sys.path.remove(scripts)
    st = tree["tmp"] / "dm-state"
    st.mkdir()
    monkeypatch.setattr(D, "state_dir", lambda: st)
    for k, v in tree["env"].items():
        monkeypatch.setenv(k, v)
    tree["ct"].write_text("KEEP_A\n")
    monkeypatch.setenv("CT_MODE", "fail")
    with pytest.raises(SystemExit):
        D.pause_crons()
    assert _writes(tree) == [] and tree["ct"].read_text() == "KEEP_A\n", "못 읽은 채 crontab -r 로 갔다"
    assert not (st / "crontab.paused").exists()
    monkeypatch.setenv("CT_MODE", "ok")
    D.pause_crons()
    assert (st / "crontab.paused").read_text() == "KEEP_A\n" and _writes(tree) == ["remove"]


def test_HP18_update_all_은_설치기_실패를_삼키지_않는다():
    s = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    for name in ("backup-local.sh\" --install-cron", "install-logrotate.sh\"", "install-watchdog.sh\""):
        i = s.index(name + " 2>&1 | sed")
        tail = s[i:s.index("\n", s.index("\n", i) + 1)]
        assert "|| true" not in tail and "|| bad " in tail, tail


# ── HP-04 — 크론의 빈 환경에서도 instance exec 가 된다 ───────────────────

def _kooremapper(tree):
    (tree["tmp"] / "KooRemapper/platform").mkdir(parents=True)


def test_HP04_비어_있으면_사용자_런타임_폴더로_채운다(tree):
    uid = os.getuid()
    if not Path(f"/run/user/{uid}/bus").is_socket():
        pytest.skip(f"/run/user/{uid}/bus 없음 — 채울 원천이 없는 박스")
    _kooremapper(tree)
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"])
    assert r.returncode == 0 and "kooremapper → kooremapper-t-" in r.stdout, r.stdout + r.stderr
    seen = Path(tree["env"]["AP_ENV_LOG"]).read_text().splitlines()
    assert seen == [f"XDG=/run/user/{uid}", f"DBUS=unix:path=/run/user/{uid}/bus"], seen


def test_HP04_준_값은_그대로_둔다(tree):
    _kooremapper(tree)
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"],
             XDG_RUNTIME_DIR="/given", DBUS_SESSION_BUS_ADDRESS="unix:path=/given/bus")
    assert r.returncode == 0, r.stdout + r.stderr
    assert Path(tree["env"]["AP_ENV_LOG"]).read_text().splitlines() == ["XDG=/given", "DBUS=unix:path=/given/bus"]
