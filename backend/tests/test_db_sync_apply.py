# db-sync 적용 verbs(push · pull · mirror · rollback · ssh-check) — 미리보기는 아무것도 안 바꾸고, --apply 만 rsync → 사전 백업 → 기존 병합 · 복원 → 원장을 돈다
"""왜 — docs/data-migration D5. 사용자 결정(11-24)으로 짓기만 했다(10-31 A2 의 보류를 뒤집음 — 실제로 돌릴지는 사람이 정한다).
그래서 '돌리지 않으면 아무 일도 없다' 와 '돌리면 정해진 차례로만 간다' 를 시험이 못박는다.

박스 셋(a=dev · b=staging · p=prod)을 임시 폴더에 세운다. 박스마다 포털 사본(진짜 db-sync · dbsync.py · services.py ·
backup-local.sh · services.yaml)과 가짜 AIDataHub(진짜와 같은 입구의 병합 · 복원 스크립트)가 있다. ssh · rsync · apptainer 는
진짜 꼴의 가짜다 — ssh 는 'user@<박스>.example.invalid 명령' 을 그 박스 환경의 bash 로 돌리고, rsync 는 원격 지정을 그 박스의
로컬 경로로 바꿔 진짜 rsync 를 부르고, apptainer 는 instance list · exec pg_dump 를 흉내 낸다. 진짜 /data · 형제 리포 · ssh 는 건드리지 않는다.
"""
import fcntl
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SVC = "ai-data-hub"

FAKE_SSH = r"""#!/usr/bin/env bash
# 가짜 ssh — 진짜처럼 [옵션…] user@host 명령… 을 받아 명령을 그 박스 환경의 bash 로 돌린다. host '<x>.example.invalid' = $FAKE_ROOT/<x>.
echo "ssh $*" >> "$FAKE_ROOT/calls.log"
while [ $# -gt 0 ]; do case "$1" in -o|-p|-i|-l) shift 2 ;; -*) shift ;; *) break ;; esac; done
dest="$1"; shift
host="${dest#*@}"; box="${host%%.*}"
[ -f "$FAKE_ROOT/$box.denied" ] && { echo "$dest: Permission denied (publickey)." >&2; exit 255; }
[ -d "$FAKE_ROOT/$box/HWAXPortal" ] || { echo "ssh: Could not resolve hostname $host: Name or service not known" >&2; exit 255; }
cd "$FAKE_ROOT/$box"
exec env -u HWAX_BOX -u HWAX_BOX_ROLE -u HWAX_DATA_ROOT HOME="$FAKE_ROOT/$box" BACKUP_ROOT="$FAKE_ROOT/$box/backups" bash -c "$*"
"""

FAKE_RSYNC = r"""#!/usr/bin/env bash
# 가짜 rsync — 원격 지정 'user@<x>.example.invalid:/경로' 를 로컬 경로로 바꾸고 -e 를 뺀 뒤 진짜 rsync 를 부른다.
echo "rsync $*" >> "$FAKE_ROOT/calls.log"
[ -f "$FAKE_ROOT/rsync.fail" ] && { echo "rsync: connection unexpectedly closed (0 bytes received so far) [sender]" >&2; exit 12; }
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    -e) shift 2; continue ;;
    *@*.example.invalid:*) args+=("${1#*:}") ;;
    *) args+=("$1") ;;
  esac
  shift
done
exec /usr/bin/rsync "${args[@]}"
"""

# 진짜 apptainer 처럼 — instance list 는 머리줄 + 이름 열, exec … pg_dump 는 표준출력으로 SQL. 어느 박스의 덤프인지 첫 줄에 남긴다.
FAKE_APPTAINER = r"""#!/usr/bin/env bash
echo "apptainer $* box=$(basename "$(dirname "$BACKUP_ROOT")")" >> "$FAKE_ROOT/calls.log"
case "$1" in
  instance) printf 'INSTANCE NAME    PID      IP    IMAGE\naidh_postgres    4242           /x/postgres.sif\n' ;;
  exec) printf -- '-- PostgreSQL database dump from %s %s\nSELECT 1;\n' "$(basename "$(dirname "$BACKUP_ROOT")")" "$(date +%s%N)" ;;
  *) exit 2 ;;
esac
"""

# AIDataHub deploy/apptainer/merge-from-drive.sh 의 입구 — AIDH_MERGE_DUMP 가 비었거나 그 파일이 없으면 Drive 최신을 받는다(진짜와 같다).
FAKE_MERGE = r"""#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BOX="$(basename "$(cd "$HERE/../../.." && pwd)")"
DUMP="${AIDH_MERGE_DUMP:-}"
if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "merge $BOX DRIVE" >> "$FAKE_ROOT/calls.log"; echo "[ERROR] AIDH_DRIVE_REMOTE 미설정"; exit 1
fi
echo "merge $BOX $(gunzip -c "$DUMP" | head -1)" >> "$FAKE_ROOT/calls.log"
echo "→ merge 소스: $DUMP"
[ -f "$FAKE_ROOT/$BOX.merge.fail" ] && { echo "[ERROR] staging 덤프 로드 실패"; exit 1; }
echo "  agents: +1 ~0"
"""

# AIDataHub deploy/apptainer/restore-db.sh 의 입구 — 인자 아무 자리의 --yes, 나머지 하나가 덤프. --yes 없으면 묻는다.
FAKE_RESTORE = r"""#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BOX="$(basename "$(cd "$HERE/../../.." && pwd)")"
YES=0; DUMP=""
for a in "$@"; do case "$a" in --yes|-y) YES=1 ;; *) DUMP="$a" ;; esac; done
[ -n "$DUMP" ] && [ -f "$DUMP" ] || { echo "usage: $0 [--yes] <dump.sql.gz>" >&2; exit 2; }
if [ "$YES" -ne 1 ]; then read -r -p "계속하시겠습니까? [y/N] " REPLY; [[ "$REPLY" =~ ^[Yy]$ ]] || { echo "취소됨."; exit 0; }; fi
echo "restore $BOX $DUMP $(gunzip -c "$DUMP" | head -1)" >> "$FAKE_ROOT/calls.log"
"""

# 이 판 앞(D0)의 db-sync 꼴 — 읽기 전용 셋만 알고 적용 verbs 는 3, 모르는 verb(_ping 등)는 사용법과 2 로 끝난다.
OLD_DBSYNC = r"""#!/usr/bin/env bash
set -uo pipefail
VERB="${1:-}"; shift || true
case "$VERB" in
  status|keys-check|verify) echo "  box=b role=staging" ;;
  push|pull|mirror|rollback|prune|apply|snapshot|stage) echo "✗ '$VERB' 는 D5 에서 배선된다(PLAN §8)" >&2; exit 3 ;;
  *) echo "박스 간 데이터 동기화 래퍼 — 사용법"; exit 2 ;;
esac
"""

ROLES = {"a": "dev", "b": "staging", "p": "prod"}
COPY = ["infra/scripts/db-sync.sh", "infra/scripts/dbsync.py", "infra/scripts/services.py",
        "infra/scripts/backup-local.sh", "infra/services.yaml"]


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _boxes_yaml(*names: str, roles: dict | None = None) -> str:
    roles = {**ROLES, **(roles or {})}
    out = ["boxes:"]
    for n in names:
        out += [f"  {n}:", f"    host: {n}.example.invalid", "    user: tester", f"    role: {roles[n]}", "    repo: ~/HWAXPortal"]
    return "\n".join(out) + "\n"


@pytest.fixture()
def world(tmp_path):
    bin_ = tmp_path / "bin"
    _exe(bin_ / "ssh", FAKE_SSH)
    _exe(bin_ / "rsync", FAKE_RSYNC)
    _exe(bin_ / "apptainer", FAKE_APPTAINER)
    for box, role in ROLES.items():
        portal = tmp_path / box / "HWAXPortal"
        for rel in COPY:
            (portal / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, portal / rel)
        shutil.copytree(ROOT / "infra/scripts/lib", portal / "infra/scripts/lib",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (portal / "infra/.env").write_text(
            f"HWAX_BOX={box}\nHWAX_BOX_ROLE={role}\nHWAX_DATA_ROOT={tmp_path / box / 'data'}\n", encoding="utf-8")
        others = [n for n in ROLES if n != box]
        (portal / "infra/boxes.yaml").write_text(_boxes_yaml(*others), encoding="utf-8")
        appt = tmp_path / box / "AIDataHub" / "deploy" / "apptainer"
        _exe(appt / "merge-from-drive.sh", FAKE_MERGE)
        _exe(appt / "restore-db.sh", FAKE_RESTORE)
        (appt / ".env").write_text("INST_POSTGRES=aidh_postgres\nPOSTGRES_USER=aidh\nPOSTGRES_PORT=5435\nPOSTGRES_DB=aidh\n",
                                   encoding="utf-8")
    return tmp_path


def _env(world: Path, box: str) -> dict:
    return {"HOME": str(world / box), "PATH": f"{world / 'bin'}:/usr/bin:/bin", "LANG": "C.UTF-8", "USER": "tester",
            "LOGNAME": "tester", "BACKUP_ROOT": str(world / box / "backups"), "FAKE_ROOT": str(world),
            "PYTHONDONTWRITEBYTECODE": "1"}


def run(world: Path, box: str, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(world / box / "HWAXPortal/infra/scripts/db-sync.sh"), *args],
                          cwd=world / box, env=_env(world, box), input=stdin, capture_output=True, text=True, timeout=120)


def backup(world: Path, box: str) -> None:
    r = subprocess.run(["bash", str(world / box / "HWAXPortal/infra/scripts/backup-local.sh"), "aidh"],
                       cwd=world / box, env=_env(world, box), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


def calls(world: Path) -> list[str]:
    p = world / "calls.log"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def remote(line: str, verb: str) -> bool:
    """ssh 로 부른 원격 db-sync verb 인가 — 시험 폴더 이름(test_push_apply…)이 경로에 섞여 있어 낱말로 본다."""
    return line.startswith("ssh ") and f"db-sync.sh {verb} " in line


def journal(world: Path, box: str) -> list[dict]:
    p = world / box / "data/hwax/state/db-sync/journal.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def tree(world: Path) -> list[tuple]:
    out = []
    for dp, dns, fns in os.walk(world):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for n in dns + fns:
            p = Path(dp) / n
            st = p.lstat()
            out.append((str(p.relative_to(world)), st.st_size if p.is_file() else -1, st.st_mtime_ns))
    return sorted(out)


def out(r: subprocess.CompletedProcess) -> str:
    return r.stdout + r.stderr


# ── 미리보기는 아무것도 바꾸지 않는다 ─────────────────────────────────────────────────────────────────────────────

def _seed_rollback_row(world: Path) -> None:
    """b 의 원장에 사전 백업 한 줄(진짜 꼴)을 미리 둔다 — 롤백 미리보기용."""
    pre = world / "b/backups/hwax/b/aidh/pre-sync/20261124-010101-000001-ai-data-hub"
    pre.mkdir(parents=True)
    (pre / "aidh-b-20261124-010101.sql.gz").write_bytes(b"x")
    sd = world / "b/data/hwax/state/db-sync"
    (sd / "last-applied").mkdir(parents=True)
    (sd / "journal.jsonl").write_text(json.dumps({"id": "20261124-010101-000001-ai-data-hub", "svc": SVC, "class": "pg",
                                                  "mode": "publish", "from": "a", "result": "applied",
                                                  "pre_sync": str(pre / "aidh-b-20261124-010101.sql.gz")}) + "\n")


@pytest.mark.parametrize("box,args", [
    ("a", ["push", "--svc", SVC, "--to", "b"]),
    ("b", ["pull", "--svc", SVC, "--from", "a"]),
    ("b", ["mirror", "--svc", SVC, "--from", "p"]),
    ("b", ["mirror", "--svc", SVC, "--from", "p", "--confirm", f"b/{SVC}"]),   # 이름을 쳐도 --apply 없이는 미리보기
    ("b", ["rollback", "--svc", SVC]),
])
def test_previews_change_nothing(world, box, args):
    backup(world, "a")
    _seed_rollback_row(world)
    before_calls, before_tree = calls(world), tree(world)
    r = run(world, box, *args, stdin=f"b/{SVC}\n")
    assert r.returncode == 0, out(r)
    assert "미리보기다 — 아무것도 바꾸지 않았다" in r.stdout
    assert calls(world) == before_calls, "미리보기가 ssh · rsync · apptainer · 병합 · 복원 가운데 하나를 불렀다"
    assert tree(world) == before_tree, "미리보기가 파일 · 폴더를 만들거나 바꿨다"


# ── 적용 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_push_apply_runs_remote_presync_merge_and_journal(world):
    backup(world, "a")
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 0, out(r)
    c = calls(world)
    order = [i for i, x in enumerate(c) if remote(x, "_inbound")] + [i for i, x in enumerate(c) if x.startswith("rsync ")] \
        + [i for i, x in enumerate(c) if remote(x, "_apply")] \
        + [i for i, x in enumerate(c) if x.startswith("apptainer exec") and "box=b" in x] \
        + [i for i, x in enumerate(c) if x.startswith("merge b")]
    assert len(order) == 5 and order == sorted(order), c        # 받는 자리 → rsync → 원격 적용 → 사전 백업 → 병합
    assert any(x.startswith("merge b -- PostgreSQL database dump from a ") for x in c), c   # a 의 덤프를 b 가 병합
    assert not any("DRIVE" in x for x in c)
    rows = journal(world, "b")
    assert len(rows) == 1 and rows[0]["result"] == "applied" and rows[0]["mode"] == "publish"
    assert rows[0]["from"] == "a" and rows[0]["to"] == "b" and rows[0]["rc"] == 0
    pre = Path(rows[0]["pre_sync"])
    assert pre.is_file() and Path(f"{pre}.sha256").is_file()
    assert pre.parent == world / "b/backups/hwax/b/aidh/pre-sync" / rows[0]["id"]
    assert (world / "b/data/hwax/state/db-sync/last-applied" / f"{SVC}.pg").read_text().split()[1] == "publish"
    assert not any((world / "b/data/hwax/.staging/inbound" / SVC).iterdir())   # 됐으면 받은 자리를 비운다
    assert not (world / "a/data").exists()                                     # 보낸 쪽에는 원장을 만들지 않는다


def test_pull_apply_merges_on_this_box(world):
    backup(world, "a")
    r = run(world, "b", "pull", "--svc", SVC, "--from", "a", "--apply")
    assert r.returncode == 0, out(r)
    assert any(x.startswith("merge b -- PostgreSQL database dump from a ") for x in calls(world))
    assert [x["mode"] for x in journal(world, "b")] == ["publish"]


def test_mirror_needs_the_typed_name(world):
    backup(world, "p")
    for extra, stdin in (([], ""), (["--confirm", "b/kooremapper"], ""), (["--confirm", f"a/{SVC}"], ""), ([], "b\n")):
        r = run(world, "b", "mirror", "--svc", SVC, "--from", "p", "--apply", *extra, stdin=stdin)
        assert r.returncode == 3 and "확인 이름이 다르다" in out(r), out(r)
    assert not any(x.startswith(("ssh ", "rsync ", "restore ")) for x in calls(world))
    r = run(world, "b", "mirror", "--svc", SVC, "--from", "p", "--apply", stdin=f"b/{SVC}\n")
    assert r.returncode == 0, out(r)
    rest = [x for x in calls(world) if x.startswith("restore b ")]
    assert len(rest) == 1 and "dump from p " in rest[0], calls(world)   # p 의 덤프로 b 를 통째 복원
    assert [x["mode"] for x in journal(world, "b")] == ["mirror"]


def test_rollback_restores_the_recorded_presync(world):
    backup(world, "a")
    assert run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply").returncode == 0
    first = journal(world, "b")[0]
    r = run(world, "b", "rollback", "--svc", SVC, "--apply")
    assert r.returncode == 3 and not any(x.startswith("restore ") for x in calls(world)), out(r)   # 이름 없이는 안 한다
    r = run(world, "b", "rollback", "--svc", SVC, "--apply", "--confirm", f"b/{SVC}")
    assert r.returncode == 0, out(r)
    rest = [x for x in calls(world) if x.startswith("restore b ")]
    assert len(rest) == 1 and rest[0].split()[2] == first["pre_sync"], rest
    rows = journal(world, "b")
    assert rows[-1]["mode"] == "rollback" and rows[-1]["ref"] == first["id"] and rows[-1]["result"] == "applied"
    assert Path(rows[-1]["pre_sync"]).is_file() and rows[-1]["pre_sync"] != first["pre_sync"]   # 되돌리기도 되돌릴 수 있게


# ── 실패 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_merge_failure_keeps_presync_and_does_not_restore(world):
    backup(world, "a")
    (world / "b.merge.fail").touch()
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 1, out(r)
    rows = journal(world, "b")
    assert rows[-1]["result"] == "failed" and rows[-1]["stage"] == "tool" and Path(rows[-1]["pre_sync"]).is_file()
    assert f"rollback --svc {SVC} --id {rows[-1]['id']}" in r.stdout
    assert not any(x.startswith("restore ") for x in calls(world))   # 자동으로 되돌리지 않는다(D7)
    assert any((world / "b/data/hwax/.staging/inbound" / SVC).iterdir())   # 실패면 받은 파일을 남긴다


def test_sha256_mismatch_refuses_before_presync(world):
    backup(world, "a")
    for s in (world / "a/backups/hwax/a/aidh/daily").glob("*.sha256"):
        s.write_text("0" * 64 + "\n")
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 3 and "sha256" in out(r), out(r)
    c = calls(world)
    assert not any(x.startswith("apptainer exec") and "box=b" in x for x in c) and not any(x.startswith("merge ") for x in c)
    assert journal(world, "b") == []


def test_rsync_failure_stops_before_remote_apply(world):
    backup(world, "a")
    (world / "rsync.fail").touch()
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 1 and "rsync 실패" in out(r), out(r)
    assert not any(remote(x, "_apply") for x in calls(world)) and not any(x.startswith("merge ") for x in calls(world))


def test_ssh_key_missing(world):
    backup(world, "a")
    (world / "b.denied").touch()
    r = run(world, "a", "ssh-check")
    assert r.returncode == 1, out(r)
    assert "✗ b" in r.stdout and "ssh 실패" in r.stdout and "BatchMode" in r.stdout and "✓ p" in r.stdout
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 1 and "ssh 실패" in out(r), out(r)
    assert not any(x.startswith("rsync ") for x in calls(world))


def test_ssh_check_reports_role_mismatch_and_old_remote(world):
    assert run(world, "a", "ssh-check").returncode == 0
    (world / "a/HWAXPortal/infra/boxes.yaml").write_text(_boxes_yaml("b", "p", roles={"b": "prod"}))
    r = run(world, "a", "ssh-check", "b")
    assert r.returncode == 1 and "원격 역할 staging ≠ boxes.yaml prod" in r.stdout, out(r)
    _exe(world / "b/HWAXPortal/infra/scripts/db-sync.sh", OLD_DBSYNC)   # 이 판 앞의 db-sync(D0)
    r = run(world, "a", "ssh-check", "b")
    assert r.returncode == 1 and "이 판이 아니다" in r.stdout, out(r)


# ── 거부 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_direction_and_role_refusals(world):
    backup(world, "a")
    backup(world, "b")
    cases = [("b", ["push", "--svc", SVC, "--to", "a"], "publish 는"),       # staging → dev
             ("a", ["pull", "--svc", SVC, "--from", "b"], "publish 는"),     # 받는 쪽이 dev
             ("a", ["mirror", "--svc", SVC, "--from", "p"], "mirror 는"),     # dev 는 mirror 를 받지 않는다
             ("p", ["mirror", "--svc", SVC, "--from", "b"], "mirror 는")]     # prod 는 mirror 를 받지 않는다
    for box, args, msg in cases:
        confirm = ["--confirm", f"{box}/{SVC}"] if args[0] == "mirror" else []   # 이름까지 쳐도 방향이 먼저 막는다
        for extra in ([], ["--apply", *confirm]):
            r = run(world, box, *args, *extra)
            assert r.returncode == 3 and msg in out(r), (box, args, extra, out(r))
    env = world / "a/HWAXPortal/infra/.env"
    env.write_text(env.read_text().replace("HWAX_BOX_ROLE=dev\n", ""))
    r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 3 and "역할" in out(r), out(r)
    assert calls(world) and not any(x.startswith(("ssh ", "rsync ", "merge ", "restore ")) for x in calls(world))


def test_remote_real_role_must_match_boxes_file(world):
    backup(world, "a")
    env = world / "a/HWAXPortal/infra/.env"
    env.write_text(env.read_text().replace("HWAX_BOX_ROLE=dev", "HWAX_BOX_ROLE=staging"))   # b 의 boxes.yaml 은 a 를 dev 로 안다
    backup(world, "a")
    r = run(world, "b", "pull", "--svc", SVC, "--from", "a", "--apply")
    assert r.returncode == 3 and "실제 역할 staging" in out(r), out(r)
    assert not any(x.startswith(("rsync ", "merge ")) for x in calls(world))


def test_unwired_services_are_refused(world):
    r = run(world, "a", "push", "--svc", "mx-white-paper", "--to", "b")
    assert r.returncode == 3 and "merge_input" in out(r), out(r)
    r = run(world, "b", "mirror", "--svc", "kooremapper", "--from", "p")
    assert r.returncode == 3 and "restore_tool" in out(r), out(r)
    assert calls(world) == []


def test_merge_script_that_ignores_the_input_is_never_called(world):
    """입구 변수를 모르는 병합 스크립트에 변수만 주면 Drive 최신을 받아 다른 덤프를 병합한다 — 부르지 않는다."""
    backup(world, "a")
    m = world / "b/AIDataHub/deploy/apptainer/merge-from-drive.sh"
    m.write_text(m.read_text().replace("AIDH_MERGE_DUMP", "SOME_OTHER_VAR"))
    for extra in ([], ["--apply"]):
        r = run(world, "b", "pull", "--svc", SVC, "--from", "a", *extra)
        assert r.returncode == 3 and "Drive" in out(r), out(r)
    assert not any(x.startswith(("ssh ", "rsync ", "merge ")) for x in calls(world))


def test_busy_lock_refuses(world):
    backup(world, "a")
    sd = world / "b/data/hwax/state/db-sync"
    (sd / "last-applied").mkdir(parents=True)
    with open(sd / "db-sync.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        r = run(world, "a", "push", "--svc", SVC, "--to", "b", "--apply")
    assert r.returncode == 3 and "도는 중" in out(r), out(r)
    assert not any(x.startswith("merge ") for x in calls(world))


# ── 공개 리포 · 위험한 길 ────────────────────────────────────────────────────────────────────────────────────────

def test_boxes_file_is_ignored_and_example_holds_placeholders_only():
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "infra/boxes.yaml"])
    assert r.returncode == 0, "infra/boxes.yaml 이 gitignore 에 없다 — 주소 · 계정이 공개 리포에 실린다"
    import yaml
    boxes = yaml.safe_load((ROOT / "infra/boxes.yaml.example").read_text(encoding="utf-8"))["boxes"]
    assert boxes and all(b["host"].endswith(".example.invalid") and b["user"] == "someone" for b in boxes.values())
    assert {b["role"] for b in boxes.values()} <= {"dev", "staging", "prod"}


def test_wrapper_never_reaches_update_all_or_deploy_all():
    """dev 에서 deploy-all 은 리포를 리셋한다(docs/gotchas 3) — 래퍼는 그 길을 부르지 않는다."""
    for rel in ("infra/scripts/db-sync.sh", "infra/scripts/dbsync.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "deploy-all" not in src and "update-all.sh" not in src and "update-all-" not in src, rel
