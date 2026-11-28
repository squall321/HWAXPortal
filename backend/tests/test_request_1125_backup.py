# §1b 배포 전 백업의 AIDataHub 덤프 시간 줄이기(docs/request-1125 SE-2) — 뒤에서 뜨기 · 여러 코어 gzip · 배포 전 백업과 병합 전 덤프는 새 둘만
"""왜 — §1b 가 28분 남짓 걸렸고 그중 AIDataHub 덤프가 27 ~ 28분이었다(11 GB). 03:30 일일 백업 2시간 뒤 같은 DB 를 다시 떴고 WAL 은 51 kB 였다.
① AIDataHub 덤프를 뒤에서 뜨고 deploy-all 의 AIDataHub 재기동(alembic 이행) 앞과 update-all 끝에서 기다린다 — 실패하면 다시 띄우지 않는다.
② 압축을 여러 코어로 — 같은 .sql.gz 꼴(lib/pgzip.py)이라 복원 · 대조 스크립트는 그대로다.
④ update-all 이 뜬 것(-pre)과 AIDataHub 병합 전 덤프는 7일 보관과 따로 가장 새 둘만 남긴다. ③(03:30 덤프를 롤백 지점으로 쓸지)은 사용자 결정 — 짓지 않았다.

백업 스크립트는 10-27 하네스(가짜 apptainer · 임시 트리 — test_request_1027_backup)로 그대로 돌린다.
"""
import gzip
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests.test_request_1027_backup import ROOT, _run, tree  # noqa: F401 — tree 는 픽스처

UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
DA = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")


def _prep(tree):
    (tree["tmp"] / "KooRemapper/platform").mkdir(parents=True)
    lib = tree["portal"] / "infra/scripts/lib"
    for f in ("pgzip.py", "skip-ledger.sh", "koorm-parked.sh"):
        shutil.copy2(ROOT / "infra/scripts/lib" / f, lib / f)
    return Path(tree["env"]["BACKUP_ROOT"]) / "hwax/t/kooremapper/daily"


def _age(p: Path, days: float) -> None:
    t = time.time() - days * 86400
    os.utime(p, (t, t))


def test_배포_전_백업은_이름_끝에_pre_이고_여러_코어_gzip_이_같은_꼴이다(tree):
    daily = _prep(tree)
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"], HWAX_BACKUP_PRE="1",
             DBUS_SESSION_BUS_ADDRESS="unix:path=/x", XDG_RUNTIME_DIR="/x")
    assert r.returncode == 0, r.stdout + r.stderr
    files = sorted(daily.glob("*.sql.gz"))
    assert len(files) == 1 and files[0].name.startswith("kooremapper-t-") and files[0].name.endswith("-pre.sql.gz"), files
    assert gzip.open(files[0]).read() == b"-- PostgreSQL database dump\n", "gunzip 이 그대로 읽는 gzip 이다"
    assert (daily / (files[0].name + ".sha256")).is_file()


def test_pre_는_새_둘만_남기고_일일_백업은_7일_규칙_그대로(tree):
    daily = _prep(tree)
    daily.mkdir(parents=True)
    for i in range(4):
        f = daily / f"kooremapper-t-2026110{i}-010000-pre.sql.gz"; f.write_bytes(b"x"); _age(f, 1 + i)
    for i in range(2):
        f = daily / f"kooremapper-t-2026100{i}-033000.sql.gz"; f.write_bytes(b"x"); _age(f, 2 + i)   # 7일 안 — 그대로
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"], HWAX_BACKUP_PRE="1",
             DBUS_SESSION_BUS_ADDRESS="unix:path=/x", XDG_RUNTIME_DIR="/x")
    assert r.returncode == 0, r.stdout + r.stderr
    left = sorted(p.name for p in daily.glob("*.sql.gz"))
    pre = [n for n in left if n.endswith("-pre.sql.gz")]
    assert len(pre) == 2 and "kooremapper-t-20261100-010000-pre.sql.gz" in pre, left   # 방금 뜬 것 + 가장 새 옛 것
    assert [n for n in left if not n.endswith("-pre.sql.gz")] == ["kooremapper-t-20261000-033000.sql.gz", "kooremapper-t-20261001-033000.sql.gz"]
    assert "삭제(배포 전 백업 — 새 2개 밖)" in r.stdout


def test_AIDataHub_병합_전_덤프도_새_둘만(tree):
    _prep(tree)
    aidh = Path(tree["env"]["BACKUP_ROOT"]) / "aidh"; aidh.mkdir(parents=True)
    for i in range(4):
        f = aidh / f"pre-merge-2026112{i}.sql.gz"; f.write_bytes(b"x"); _age(f, 4 - i)
        (aidh / (f.name + ".sha256")).write_text("h")
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"],
             DBUS_SESSION_BUS_ADDRESS="unix:path=/x", XDG_RUNTIME_DIR="/x")
    assert r.returncode == 0, r.stdout + r.stderr
    # '편입' 이 $BACKUP_ROOT/aidh 의 *.sql.gz 를 hwax/<박스>/aidh/daily 로 옮긴다(pre-merge 포함) — 옮겨 간 자리에서 둘만 남는다
    daily = Path(tree["env"]["BACKUP_ROOT"]) / "hwax/t/aidh/daily"
    assert sorted(p.name for p in daily.glob("pre-merge-*.sql.gz")) == ["pre-merge-20261122.sql.gz", "pre-merge-20261123.sql.gz"], r.stdout
    assert sorted(p.name for p in daily.glob("*.sha256")) == ["pre-merge-20261122.sql.gz.sha256", "pre-merge-20261123.sql.gz.sha256"]
    assert "삭제(병합 전 덤프 — 새 2개 밖)" in r.stdout


def test_뺀_대상은_뜨지도_정리하지도_않는다(tree):
    """update-all §1b 가 AIDataHub 를 뒤에서 뜨는 동안 나머지를 뜬다 — 뺀 대상의 daily 는 뒤에서 도는 쪽이 쓰는 중이라 이 실행이 정리하지 않는다."""
    daily = _prep(tree)
    daily.mkdir(parents=True)
    old = daily / "kooremapper-t-20250101-033000.sql.gz"; old.write_bytes(b"x"); _age(old, 400)
    for i in range(3):
        f = daily / f"kooremapper-t-2026110{i}-033000.sql.gz"; f.write_bytes(b"x"); _age(f, 1 + i)
    r = _run(tree, [str(tree["portal"] / "infra/scripts/backup-local.sh"), "kooremapper"], HWAX_BACKUP_SKIP="kooremapper",
             DBUS_SESSION_BUS_ADDRESS="unix:path=/x", XDG_RUNTIME_DIR="/x")
    assert r.returncode == 0, r.stdout + r.stderr
    assert old.exists() and len(list(daily.glob("*.sql.gz"))) == 4, "뺀 대상은 이 실행에서 손대지 않는다"
    assert "보존:" in r.stdout and "kooremapper →" not in r.stdout


# ── ① 뒤에서 뜨고 기다린다 ───────────────────────────────────────────────────────────────────────────────────
def _wait_block() -> str:
    a = DA.index('      if [ -n "${HWAX_AIDH_BACKUP_RC:-}" ] && [ "${RESTART:-0}" != 1 ]')
    return DA[a:DA.index("\n      fi\n", DA.index("exit 1\n        fi", a)) + 10]


@pytest.mark.parametrize("case", ["끝남", "실패", "늦게_끝남", "시한"])
def test_deploy_all_은_AIDataHub_재기동_앞에서_덤프를_기다린다(tmp_path, case):
    rc = tmp_path / "rc"
    if case == "끝남":
        rc.write_text("0\n")
    elif case == "실패":
        rc.write_text("1\n")
    pre = 'hwax_restart_needed() { return 0; }\nRESTART=0\n_cur=x\n'
    if case == "늦게_끝남":
        pre += f'( sleep 2; echo 0 > "{rc}" ) &\n'
    body = "set -euo pipefail\n" + pre + "( " + _wait_block() + "\n echo RESTARTED )\necho \"rc=$?\"\n"
    env = {"PATH": "/usr/bin:/bin", "HWAX_AIDH_BACKUP_RC": str(rc), "HWAX_AIDH_BACKUP_LOG": str(tmp_path / "log"),
           "HWAX_AIDH_BACKUP_WAIT_S": "1" if case == "시한" else "30"}
    r = subprocess.run(["bash", "-c", body + "true"], capture_output=True, text=True, env=env, timeout=60)
    out = r.stdout + r.stderr
    if case in ("끝남", "늦게_끝남"):
        assert "RESTARTED" in out, out
    else:
        assert "RESTARTED" not in out and "다시 띄우지 않았다" in out, out
        assert ("실패했다(rc 1)" in out) is (case == "실패") and ("안에 끝나지 않았다" in out) is (case == "시한"), out


def test_재기동이_필요_없으면_기다리지_않는다(tmp_path):
    body = ("set -euo pipefail\nhwax_restart_needed() { return 1; }\nRESTART=0\n_cur=x\n" + _wait_block() + "\necho GO\n")
    r = subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=20,
                       env={"PATH": "/usr/bin:/bin", "HWAX_AIDH_BACKUP_RC": str(tmp_path / "없음"), "HWAX_AIDH_BACKUP_WAIT_S": "30"})
    assert "GO" in r.stdout, r.stdout + r.stderr


def test_update_all_1b_가_AIDataHub_를_뒤에서_뜨고_나머지는_빼고_뜬다():
    i = UA.index('hr "1b) 배포 전 로컬 백업')
    blk = UA[i:UA.index('hr "1b2)', i)]
    assert "nohup env HWAX_BACKUP_PRE=1" in blk and '"$1" aidh > "$2" 2>&1' in blk and "</dev/null >/dev/null 2>&1 &" in blk, \
        "뒤의 실행은 출력을 파일로만 — 호출자를 붙들지 않는다"
    assert 'HWAX_BACKUP_PRE=1 HWAX_BACKUP_SKIP="$_bk_skip" "$SELF_REPO/infra/scripts/backup-local.sh"' in blk
    assert 'HWAX_AIDH_BACKUP_BG:-1' in blk, "끄는 손잡이"
    end = UA[UA.index("# §1b 가 뒤에서 뜬 AIDataHub 덤프 — 끝나기를 기다려"):UA.index("# ○ 옵션·설정이 없어 안 켠 기능은")]
    assert "HWAX_AIDH_BACKUP_WAIT_S" in end and 'bad "AIDataHub 사전 덤프 실패' in end, "끝에서 기다려 결과를 센다(비치명)"
    assert UA.index("# §1b 가 뒤에서 뜬 AIDataHub 덤프") < UA.rindex("hwax_skip_summary\n")
