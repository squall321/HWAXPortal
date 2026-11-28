# §1b 배포 전 백업의 AIDataHub 덤프 시간 줄이기(docs/request-1125 SE-2) — 뒤에서 뜨기 · 여러 코어 gzip · 배포 전 백업과 병합 전 덤프는 새 둘만
"""왜 — §1b 가 28분 남짓 걸렸고 그중 AIDataHub 덤프가 27 ~ 28분이었다(11 GB). 03:30 일일 백업 2시간 뒤 같은 DB 를 다시 떴고 WAL 은 51 kB 였다.
① AIDataHub 덤프를 뒤에서 뜨고 deploy-all 의 AIDataHub 재기동(alembic 이행) 앞과 update-all 끝에서 기다린다 — 실패하면 다시 띄우지 않는다.
② 압축을 여러 코어로 — 같은 .sql.gz 꼴(lib/pgzip.py)이라 복원 · 대조 스크립트는 그대로다.
④ update-all 이 뜬 것(-pre)과 AIDataHub 병합 전 덤프는 7일 보관과 따로 가장 새 둘만 남긴다.
③ 사용자 결정 11-28 — 그날 일일 덤프가 온전하고(sha256 짝이 맞고) 받을 AIDataHub 판에 alembic 이관이 없으면 새로 뜨지 않고 그것을 롤백 지점으로 적는다.
   이관이 있거나 일일 덤프가 없 · 낡 · 깨졌거나 볼 수 없으면(모름) 새로 뜬다. 판정은 lib/predeploy-dump.sh — 끝 코드는 늘 0(set -e 아래 상태 반환 함정).

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


# ── ③ 그날 일일 덤프를 배포 전 롤백 지점으로 다시 쓴다(사용자 결정 11-28 · SYNCEFF-4) ─────────────────────────────────────────────────
LIB = ROOT / "infra/scripts/lib/predeploy-dump.sh"
_GENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
         "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


def _git(cwd: Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, timeout=60, env={"PATH": os.environ["PATH"], **_GENV})
    assert r.returncode == 0, r.stderr
    return r.stdout


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d")      # 시험은 TZ=UTC 로 돌린다 — 함수의 date 와 같은 날


@pytest.fixture()
def pd(tmp_path):
    """받을 판(origin)과 그것을 받은 AIDataHub 리포 · 비어 있는 일일 덤프 폴더."""
    origin = tmp_path / "origin.git"; _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "AIDataHub"; _git(tmp_path, "clone", "-q", str(origin), str(repo))
    (repo / "api_server/alembic/versions").mkdir(parents=True)
    (repo / "api_server/alembic/versions/0001_a.py").write_text("revision = '0001'\n")
    (repo / "README").write_text("x\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "a"); _git(repo, "push", "-q", "origin", "HEAD:main")
    daily = tmp_path / "backups/hwax/t/aidh/daily"; daily.mkdir(parents=True)
    return {"tmp": tmp_path, "origin": origin, "repo": repo, "daily": daily}


def _push_upstream(pd, rel: str, body: str = "x\n") -> None:
    """다른 곳에서 origin 에 한 커밋 올린다 — 이 리포의 HEAD 는 그대로(이번에 '받을' 판)."""
    other = pd["tmp"] / "other"
    if not other.exists():
        _git(pd["tmp"], "clone", "-q", str(pd["origin"]), str(other))
    (other / rel).parent.mkdir(parents=True, exist_ok=True)
    (other / rel).write_text(body)
    _git(other, "add", "-A"); _git(other, "commit", "-qm", rel); _git(other, "push", "-q", "origin", "HEAD:main")


def _dump(pd, stamp: str, body: bytes = b"dump", sha: str | None = "ok") -> Path:
    f = pd["daily"] / f"aidh-t-{stamp}.sql.gz"; f.write_bytes(body)
    if sha == "ok":
        import hashlib
        (pd["daily"] / (f.name + ".sha256")).write_text(hashlib.sha256(body).hexdigest() + "\n")
    elif sha is not None:
        (pd["daily"] / (f.name + ".sha256")).write_text(sha)
    return f


def _decide(pd, knob: str = "", strict: bool = False) -> list[str]:
    body = (("set -euo pipefail\n" if strict else "") + f'. "{LIB}"\n'
            f'v="$(hwax_predeploy_dump_decide "{pd["repo"]}" "{pd["daily"]}" t "{knob}")"\nprintf "%s\\n" "$v"\necho AFTER\n')
    r = subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=120,
                       env={"PATH": os.environ["PATH"], "TZ": "UTC", "HOME": str(pd["tmp"]), **_GENV})
    assert r.returncode == 0 and r.stdout.endswith("AFTER\n"), r.stdout + r.stderr
    lines = r.stdout.splitlines()
    assert len(lines) == 2, lines
    return lines[0].split("\t")


def test_SE2_3_그날_덤프가_온전하고_이관이_없으면_다시_쓴다(pd):
    _dump(pd, f"{_today()}-033001")
    old = _dump(pd, "20200101-033001")                       # 옛 일일 덤프 · 그날의 -pre · 병합 전 덤프는 고르지 않는다
    (pd["daily"] / f"aidh-t-{_today()}-090000-pre.sql.gz").write_bytes(b"p")
    (pd["daily"] / "pre-merge-20991231.sql.gz").write_bytes(b"m")
    _push_upstream(pd, "README", "y\n")                       # 받을 판이 앞섰어도 이관 파일이 아니면 다시 쓴다
    v = _decide(pd)
    t = _today()
    assert v[0] == "reuse" and v[1] == str(pd["daily"] / f"aidh-t-{t}-033001.sql.gz"), v
    assert v[2] == f"{t[:4]}-{t[4:6]}-{t[6:]} 03:30:01" and "이관 없음" in v[3] and "origin/main" in v[3], v
    assert old.exists()


@pytest.mark.parametrize("case", ["이관_새_파일", "이관_고친_파일"])
def test_SE2_3_받을_판에_이관이_있으면_새로_뜬다(pd, case):
    _dump(pd, f"{_today()}-033001")
    if case == "이관_새_파일":
        _push_upstream(pd, "api_server/alembic/versions/0002_b.py")
    else:
        _push_upstream(pd, "api_server/alembic/versions/0001_a.py", "revision = '0001'\n# changed\n")
    v = _decide(pd)
    assert v[:2] == ["fresh", "migration"] and ("0002_b.py" if case == "이관_새_파일" else "0001_a.py") in v[2], v


def test_SE2_3_일일_덤프가_없거나_낡았으면_새로_뜬다(pd):
    (pd["daily"] / f"aidh-t-{_today()}-090000-pre.sql.gz").write_bytes(b"p")    # 이 실행이 뜬 -pre 는 일일 덤프가 아니다
    assert _decide(pd)[:2] == ["fresh", "none"]
    _dump(pd, "20200101-033001")
    v = _decide(pd)
    assert v[:2] == ["fresh", "stale"] and "2020-01-01" in v[2], v
    _dump(pd, f"{_today()}-033001", sha=None)
    v = _decide(pd)
    assert v[:2] == ["fresh", "nosha"] and "아직 뜨는 중이거나" in v[2], v


@pytest.mark.parametrize("case", ["다른_해시", "꼴이_아님", "영바이트"])
def test_SE2_3_깨진_일일_덤프는_쓰지_않는다(pd, case):
    if case == "다른_해시":
        _dump(pd, f"{_today()}-033001", sha="0" * 64 + "\n")
    elif case == "꼴이_아님":
        _dump(pd, f"{_today()}-033001", sha="not-a-hash\n")
    else:
        _dump(pd, f"{_today()}-033001", body=b"")
    v = _decide(pd)
    assert v[:2] == ["fresh", "broken"], v


@pytest.mark.parametrize("knob,word", [("fresh", "늘 새로 뜬다"), ("always", "모른다")])
def test_SE2_3_손잡이로_늘_새로_뜬다(pd, knob, word):
    _dump(pd, f"{_today()}-033001")
    v = _decide(pd, knob=knob)
    assert v[:2] == ["fresh", "knob"] and word in v[2], v
    assert _decide(pd, knob="auto")[0] == "reuse", "auto 는 빈 값과 같다"


def test_SE2_3_볼_수_없으면_모름이고_새로_뜬다(pd):
    """fetch 가 실패하거나 가지 위에 있지 않으면 이관이 있는지 모른다 — 없음으로 읽지 않는다."""
    _dump(pd, f"{_today()}-033001")
    shutil.rmtree(pd["origin"])
    v = _decide(pd)
    assert v[:2] == ["fresh", "unknown"] and "git fetch 실패" in v[2], v
    _git(pd["repo"], "checkout", "-q", "--detach")
    v = _decide(pd)
    assert v[:2] == ["fresh", "unknown"] and "가지를 모른다" in v[2], v


@pytest.mark.parametrize("case", ["reuse", "migration", "none", "knob"])
def test_SE2_3_판정은_set_e_아래서도_끝_코드_0(pd, case):
    """판정을 끝 코드로 주면 `x="$(f)"` 가 set -e 아래서 조용히 끝난다 — 어느 갈래든 다음 줄(AFTER)까지 간다."""
    if case != "none":
        _dump(pd, f"{_today()}-033001")
    if case == "migration":
        _push_upstream(pd, "api_server/alembic/versions/0002_b.py")
    v = _decide(pd, knob="fresh" if case == "knob" else "", strict=True)
    assert v[0] == ("reuse" if case == "reuse" else "fresh"), v


# update-all §1b 의 판정 블록을 떼어 진짜 lib · 임시 리포로 돌린다
def _pd_block() -> str:
    a = UA.index('  _aidh_reused=""\n')
    return UA[a:UA.index('  if [ -z "$_bk_skip" ] && [ "${HWAX_AIDH_BACKUP_BG:-1}" = 1 ]', a)]


def _run_block(pd, infra_env: str = "", **env) -> tuple[str, Path]:
    self_repo = pd["tmp"] / "HWAXPortal"
    (self_repo / "infra/scripts/lib").mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIB, self_repo / "infra/scripts/lib/predeploy-dump.sh")
    (self_repo / "infra/.env").write_text(infra_env)
    body = ("set -uo pipefail\n"
            f'SELF_REPO="{self_repo}"\nfind_repo() {{ printf %s "{pd["repo"]}"; }}\n'
            "ok() { printf '  OK %s\\n' \"$*\"; }\nbad() { printf '  BAD %s\\n' \"$*\"; }\n"
            "hwax_skip() { printf '  SKIP %s — %s | %s\\n' \"$1\" \"$2\" \"$3\"; }\n"
            '_bk_skip=""\n' + _pd_block() + 'echo "SKIP=[$_bk_skip] REUSED=[$_aidh_reused]"\n')
    r = subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=120,
                       env={"PATH": os.environ["PATH"], "TZ": "UTC", "HOME": str(pd["tmp"]), "HWAX_BOX": "t",
                            "BACKUP_ROOT": str(pd["tmp"] / "backups"), **_GENV, **env})
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, pd["daily"].parent / "predeploy-rollback.log"


def test_update_all_1b_는_다시_쓸_때_새로_뜨지_않고_적는다(pd):
    f = _dump(pd, f"{_today()}-033001")
    out, rec = _run_block(pd)
    assert f"OK AIDataHub 배포 전 롤백 지점 — 일일 덤프 재사용 — {f.name} · " in out, out
    assert "SKIP=[aidh]" in out and f"REUSED=[{f.name} · " in out, "뒤에서 뜨지도 · 앞에서 뜨지도 않는다(backup-local 에서 뺀다)"
    line = rec.read_text(encoding="utf-8").splitlines()
    assert len(line) == 1 and f"\t일일 덤프 재사용\t{f}\t덤프 시각 " in line[0], line
    _run_block(pd)
    assert len(rec.read_text(encoding="utf-8").splitlines()) == 2, "실행마다 한 줄씩 덧붙인다"


def test_update_all_1b_는_이관이_있으면_지금처럼_새로_뜬다(pd):
    _dump(pd, f"{_today()}-033001")
    _push_upstream(pd, "api_server/alembic/versions/0002_b.py")
    out, rec = _run_block(pd)
    assert "· AIDataHub 배포 전 덤프를 새로 뜬다 — 받을 AIDataHub 판에 이관 파일 1개(0002_b.py)" in out and "SKIP=[]" in out, out
    assert not rec.exists()


@pytest.mark.parametrize("where", ["env", "infra_env"])
def test_update_all_1b_손잡이는_안_켠_것으로_남는다(pd, where):
    _dump(pd, f"{_today()}-033001")
    if where == "env":
        out, _rec = _run_block(pd, HWAX_PREDEPLOY_DUMP="fresh")
    else:
        out, _rec = _run_block(pd, infra_env="HWAX_PREDEPLOY_DUMP=fresh  # 늘 새로\n")
    assert "SKIP AIDataHub 일일 덤프 재사용 — HWAX_PREDEPLOY_DUMP=fresh — 늘 새로 뜬다 | " in out and "SKIP=[]" in out, out


def test_update_all_1b_는_깨진_일일_덤프를_경고로_센다(pd):
    _dump(pd, f"{_today()}-033001", sha="0" * 64)
    out, _rec = _run_block(pd)
    assert "BAD AIDataHub 일일 덤프를 다시 쓰지 않는다 — " in out and "SKIP=[]" in out, out


def _end_block() -> str:
    a = UA.index("# §1b 가 뒤에서 뜬 AIDataHub 덤프 — 끝나기를 기다려")
    return UA[a:UA.index("# ○ 옵션·설정이 없어 안 켠 기능은", a)]


@pytest.mark.parametrize("case", ["뜬_덤프", "다시_씀"])
def test_update_all_끝_요약이_롤백_지점_파일을_말한다(tmp_path, case):
    """뜬 덤프는 backup-local 의 색 글자 줄에서 파일을 읽는다(종전엔 '✓ aidh →' 로 찾아 늘 비었다) · 다시 쓴 것은 그 파일을."""
    pre = "ok() { printf 'OK %s\\n' \"$*\"; }\nbad() { printf 'BAD %s\\n' \"$*\"; }\n"
    env = {"PATH": os.environ["PATH"]}
    if case == "뜬_덤프":
        (tmp_path / "rc").write_text("0\n")
        (tmp_path / "log").write_text("\n── AIDataHub ──\n  \033[1;32m✓\033[0m aidh → aidh-t-20261128-140000-pre.sql.gz (11G)\n")
        env.update(HWAX_AIDH_BACKUP_RC=str(tmp_path / "rc"), HWAX_AIDH_BACKUP_LOG=str(tmp_path / "log"))
    else:
        pre += '_aidh_reused="aidh-t-20261128-033001.sql.gz · 2026-11-28 03:30:01"\n'
    r = subprocess.run(["bash", "-c", "set -uo pipefail\n" + pre + _end_block()], capture_output=True, text=True, timeout=30, env=env)
    assert r.returncode == 0, r.stderr
    want = ("OK AIDataHub 사전 덤프 — aidh-t-20261128-140000-pre.sql.gz (11G)" if case == "뜬_덤프"
            else "OK AIDataHub 배포 전 롤백 지점 — 일일 덤프 재사용 — aidh-t-20261128-033001.sql.gz · 2026-11-28 03:30:01")
    assert want in r.stdout, r.stdout
