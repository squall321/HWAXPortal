# 동결한 허브 앱 SIF — deploy-all §2 의 Drive 받기가 그 앱의 SIF 를 바꾸지 않고 ○ 장부에 사유를 남기는지(lib/heax-frozen.sh · cae00 11-23 라운드)
"""cae00 은 StepForge 를 운영 노드에서 돌리고 이 박스의 var/sifs/step_forge.sif 는 되돌림용 사본이다. update-all §2 가 HEAXHub dist-from-drive 로
Drive 의 새 판을 그 위에 받았다(11-23). 동결 목록(포털 infra/.env 의 HEAX_FROZEN_SIFS)의 앱은 받기 앞에 쥐고 뒤에 되돌린다.

받기는 HEAXHub 의 실제 설치 함수(_install_if_changed — 임시 파일에 받아 이름 바꾸기)와 해시의 cp -p 그대로 흉내 낸다 — 하드 링크로 쥐는 것이
이름 바꾸기 설치에서만 옛 내용을 지키므로, 가짜가 진짜와 다르면 이 시험은 아무것도 증명하지 못한다.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest
from tests.test_update_all_delib_restart_gate import _deploy_heax, health  # noqa: F401 — health 는 fixture 다

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib"
DEPLOY = (ROOT / "infra/scripts/deploy-all-from-drive.sh").read_text(encoding="utf-8")
HUB_DIST = ROOT.parent / "HEAXHub" / "deploy" / "apptainer" / "dist-from-drive.sh"
OLD_T = 1_700_000_000                       # 옛 사본의 바뀐 시각 — 되돌린 뒤에도 같아야 허브 재기동 지문이 그대로다


def _real_install() -> str:
    """HEAXHub dist-from-drive.sh 의 설치 함수 원문 — 없으면(형제 리포가 없다) 그 시험만 건너뛴다."""
    if not HUB_DIST.is_file():
        pytest.skip(f"형제 리포 HEAXHub 가 없다: {HUB_DIST}")
    m = re.search(r"^_install_if_changed\(\) \{.*?^\}\n", HUB_DIST.read_text(encoding="utf-8"), re.S | re.M)
    assert m, "HEAXHub 의 설치 함수가 바뀌었다 — 이 흉내를 다시 본다"
    assert "mv -fT" in m.group(0), "이름 바꾸기 설치가 아니면 하드 링크로 쥔 사본도 덮인다 — lib/heax-frozen.sh 를 다시 본다"
    return m.group(0)


def _drive(names_contents: dict[str, str]) -> str:
    """Drive 에서 받은 것처럼 — 캐시에 놓고 진짜 설치 함수로 var/sifs 에 들인 뒤 해시를 cp -p 로(dist-from-drive 의 앱 SIF 고리)."""
    lines = [_real_install(), "mkdir -p var/sifs .stage"]
    for n, c in names_contents.items():
        lines += [f"printf '%s' '{c}' > .stage/{n}.sif; printf '%s' 'hash-{c}' > .stage/{n}.sif.hash",
                  f'_install_if_changed .stage/{n}.sif "var/sifs/{n}.sif"', f'cp -p .stage/{n}.sif.hash var/sifs/']
    return "\n".join(lines)


def _old(root: Path, *names: str) -> dict[str, tuple]:
    sifs = root / "var" / "sifs"
    sifs.mkdir(parents=True, exist_ok=True)
    for n in names:
        for f, c in ((sifs / f"{n}.sif", f"OLD-{n}"), (sifs / f"{n}.sif.hash", f"hash-OLD-{n}")):
            f.write_text(c)
            os.utime(f, (OLD_T, OLD_T))
    return {n: (sifs / f"{n}.sif").stat().st_ino for n in names}


def _lib(root: Path, script: str) -> subprocess.CompletedProcess:
    ledger = root / "ledger"
    ledger.touch()
    return subprocess.run(["bash", "-c", f'set -euo pipefail\n. "{LIB}/skip-ledger.sh"\n. "{LIB}/heax-frozen.sh"\n{script}'],
                          capture_output=True, text=True, timeout=60, cwd=root,
                          env={"PATH": os.environ["PATH"], "HOME": str(root), "HWAX_SKIP_LEDGER": str(ledger)})


def _is_old(root: Path, n: str, ino: int) -> bool:
    f = root / "var/sifs" / f"{n}.sif"
    h = root / "var/sifs" / f"{n}.sif.hash"
    return (f.read_text() == f"OLD-{n}" and f.stat().st_ino == ino and int(f.stat().st_mtime) == OLD_T
            and h.read_text() == f"hash-OLD-{n}" and int(h.stat().st_mtime) == OLD_T)


HOLD = "hwax_frozen_hold var/sifs var/sifs/.frozen-hold"
# 화면 줄 — 같은 §2 의 HEAXHub 받기가 먼저 찍는 「✓ app SIF step_forge.sif → var/sifs/」 와 어긋나 보이지 않게 되돌렸다는 것 · 바뀐 시각의 결을 말한다
# (cae00 11-24 넘김 3 — ✓ 줄과 ○ 줄이 서로 어긋나 보였고 동결 사본의 ctime 이 바뀌었다, 설계대로다).
SKIPPED = ("○ 허브 앱 SIF step_forge — 동결 — Drive 받기가 놓은 새 판을 되돌렸다(위 '✓ app SIF step_forge.sif' 줄은 받기 단계의 것이다) — "
           "var/sifs/step_forge.sif · .sif.hash 의 내용 · mtime 은 동결 판 그대로이고 ctime 은 바뀐다(infra/.env 의 HEAX_FROZEN_SIFS)")
# 장부 줄(끝 요약)은 짧게
LEDGER = ("허브 앱 SIF step_forge — 동결\tinfra/.env 의 HEAX_FROZEN_SIFS — Drive 의 새 판을 받은 뒤 동결 판으로 되돌렸다(내용 · mtime 그대로)\t"
          "동결을 풀 때 — infra/.env 의 HEAX_FROZEN_SIFS 에서 step_forge 을 빼고 update-all(또는 deploy-all-from-drive.sh heax)을 다시 돌린다\n")


def _plain(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)
BACK = "hwax_frozen_restore var/sifs var/sifs/.frozen-hold"


# ── lib ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_동결한_앱은_받기가_바꾼_SIF_와_해시를_되돌리고_장부에_남긴다(tmp_path):
    ino = _old(tmp_path, "step_forge", "doc_forge")
    ctime0 = (tmp_path / "var/sifs/step_forge.sif").stat().st_ctime_ns
    r = _lib(tmp_path, f"{HOLD} step_forge\n{_drive({'step_forge': 'NEW', 'doc_forge': 'NEW'})}\n{BACK}\necho END")
    assert r.returncode == 0 and "END" in r.stdout, r.stdout + r.stderr
    assert _is_old(tmp_path, "step_forge", ino["step_forge"]), "같은 파일(inode) · 내용 · 바뀐 시각이 옛 사본 그대로다"
    assert (tmp_path / "var/sifs/step_forge.sif").stat().st_ctime_ns != ctime0, "ctime 은 바뀐다 — 화면 줄이 그렇다고 말하는 그대로다"
    assert (tmp_path / "var/sifs/doc_forge.sif").read_text() == "NEW", "동결하지 않은 앱은 종전대로 받는다"
    assert SKIPPED in _plain(r.stdout) and "켜려면: 동결을 풀 때 — infra/.env 의 HEAX_FROZEN_SIFS 에서 step_forge 을 빼고" in r.stdout, r.stdout
    led = (tmp_path / "ledger").read_text()
    assert led == LEDGER, "끝 요약 줄은 짧게 — 화면 줄의 ✓ · ctime 설명은 싣지 않는다"
    assert not (tmp_path / "var/sifs/.frozen-hold").exists(), "쥘 폴더를 남기지 않는다"


def test_받은_판이_같으면_말이_없다(tmp_path):
    """이미 최신이면 건너뛴 것이 없다 — ○ 장부는 '안 한 것' 만 싣는다."""
    ino = _old(tmp_path, "step_forge")
    r = _lib(tmp_path, f"{HOLD} step_forge\n{_drive({'step_forge': 'OLD-step_forge'})}\n{BACK}")
    assert r.returncode == 0 and "○" not in r.stdout and (tmp_path / "ledger").read_text() == "", r.stdout + r.stderr
    f = tmp_path / "var/sifs/step_forge.sif"
    assert f.stat().st_ino == ino["step_forge"] and int((tmp_path / "var/sifs/step_forge.sif.hash").stat().st_mtime) == OLD_T, \
        "받기의 cp -p 가 바꾼 해시의 바뀐 시각도 되돌린다(허브 재기동 지문)"


def test_없던_SIF_는_받아도_들이지_않는다(tmp_path):
    (tmp_path / "var/sifs").mkdir(parents=True)
    r = _lib(tmp_path, f"{HOLD} step_forge\n{_drive({'step_forge': 'NEW'})}\n{BACK}")
    assert r.returncode == 0 and SKIPPED in _plain(r.stdout), r.stdout + r.stderr
    assert not list((tmp_path / "var/sifs").iterdir()), "동결은 이 박스의 그 앱 SIF 를 바꾸지 않는다 — 없던 것은 없다"


def test_끊긴_실행이_남긴_쥔_사본은_다음_실행이_먼저_되돌린다(tmp_path):
    ino = _old(tmp_path, "step_forge")
    r = _lib(tmp_path, f"{HOLD} step_forge\n{_drive({'step_forge': 'NEW'})}\necho CUT")      # 되돌리기 전에 끊겼다
    assert r.returncode == 0 and (tmp_path / "var/sifs/step_forge.sif").read_text() == "NEW"
    assert (tmp_path / "var/sifs/.frozen-hold/step_forge/sif").read_text() == "OLD-step_forge", "옛 내용은 쥔 링크에 살아 있다"
    r = _lib(tmp_path, f"{HOLD} step_forge\n{BACK}")                                          # 다음 실행 — 받기 앞에 먼저 되돌린다
    assert r.returncode == 0, r.stdout + r.stderr
    assert _is_old(tmp_path, "step_forge", ino["step_forge"]) and not (tmp_path / "var/sifs/.frozen-hold").exists()


def test_앱_이름_꼴이_아니면_버리고_알린다(tmp_path):
    ino = _old(tmp_path, "step_forge")
    r = _lib(tmp_path, f'{HOLD} "../x" "*" step_forge\n{_drive({"step_forge": "NEW"})}\n{BACK}')
    assert r.returncode == 0, r.stdout + r.stderr
    assert "'../x' 은 앱 이름 꼴이 아니라 버렸다" in r.stderr and "'*' 은 앱 이름 꼴이 아니라 버렸다" in r.stderr, r.stderr
    assert _is_old(tmp_path, "step_forge", ino["step_forge"])


def test_쥐지_못하면_1_이다(tmp_path):
    _old(tmp_path, "step_forge")
    sifs = tmp_path / "var/sifs"
    sifs.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        r = _lib(tmp_path, f"{HOLD} step_forge && echo HELD || echo NOT")
    finally:
        sifs.chmod(0o755)
    assert "NOT" in r.stdout and "HELD" not in r.stdout, r.stdout + r.stderr


# ── deploy-all heax 구획 ────────────────────────────────────────────────────────────────────────────────────────
def _hub_sifs(tmp_path: Path) -> dict[str, int]:
    return _old(tmp_path / "heax", "step_forge", "doc_forge")


@pytest.mark.parametrize("where", ["infra/.env", "환경"])
def test_deploy_all_은_동결한_앱의_SIF_를_받지_않고_장부에_남긴다(tmp_path, health, where):
    health["body"] = {"status": "ok", "delib_active": 0, "delib_queued": 0}
    ino = _hub_sifs(tmp_path)
    env = {}
    if where == "infra/.env":
        (tmp_path / "portal/infra").mkdir(parents=True)
        (tmp_path / "portal/infra/.env").write_text("HEAX_FROZEN_SIFS=step_forge   # 운영 노드로 넘긴 앱의 되돌림용 사본\n")
    else:
        env["HEAX_FROZEN_SIFS"] = "step_forge"
    out, calls, _state, ledger, _failed = _deploy_heax(tmp_path, health["url"], health["url"], {"heax": "old-fp"},
                                                       during={"dist-from-drive.sh": _drive({"step_forge": "NEW", "doc_forge": "NEW"})}, **env)
    assert calls == ["appdata-merge-from-drive.sh", "dist-from-drive.sh", "stop.sh", "start.sh"], (calls, out)
    assert _is_old(tmp_path / "heax", "step_forge", ino["step_forge"]), out
    assert (tmp_path / "heax/var/sifs/doc_forge.sif").read_text() == "NEW"
    assert SKIPPED in _plain(out) and ledger == LEDGER, (out, ledger)
    assert not (tmp_path / "heax/var/sifs/.frozen-hold").exists()
    # 하네스의 허브 재기동은 대역 health 가 늘 답해 성공으로 끝나지 않는다(기존 하네스 시험도 그것을 보지 않는다) — 받기 · 되돌리기만 본다


def test_deploy_all_은_동결이_없으면_종전대로_받는다(tmp_path, health):
    health["body"] = {"status": "ok", "delib_active": 0, "delib_queued": 0}
    _hub_sifs(tmp_path)
    out, calls, _state, ledger, _failed = _deploy_heax(tmp_path, health["url"], health["url"], {"heax": "old-fp"},
                                                       during={"dist-from-drive.sh": _drive({"step_forge": "NEW", "doc_forge": "NEW"})})
    assert calls == ["appdata-merge-from-drive.sh", "dist-from-drive.sh", "stop.sh", "start.sh"], (calls, out)
    assert {n: (tmp_path / f"heax/var/sifs/{n}.sif").read_text() for n in ("step_forge", "doc_forge")} == {"step_forge": "NEW", "doc_forge": "NEW"}
    assert "○" not in out and ledger == "", out


def test_deploy_all_은_받기가_실패해도_동결한_SIF_를_되돌리고_실패로_센다(tmp_path, health):
    health["body"] = {"status": "ok", "delib_active": 0, "delib_queued": 0}
    ino = _hub_sifs(tmp_path)
    out, calls, state, _ledger, failed = _deploy_heax(tmp_path, health["url"], health["url"], {"heax": "old-fp"}, dist_rc=1,
                                                      during={"dist-from-drive.sh": _drive({"step_forge": "NEW"})}, HEAX_FROZEN_SIFS="step_forge")
    assert calls == ["appdata-merge-from-drive.sh", "dist-from-drive.sh"], (calls, out)
    assert _is_old(tmp_path / "heax", "step_forge", ino["step_forge"]) and "SKIP:heax failed" in out and failed.count("\n") == 1, out
    assert state == {"heax": "old-fp"}


def test_deploy_all_은_쥐지_못하면_받지_않고_실패로_센다(tmp_path, health):
    health["body"] = {"status": "ok", "delib_active": 0, "delib_queued": 0}
    _hub_sifs(tmp_path)
    sifs = tmp_path / "heax/var/sifs"
    sifs.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        out, calls, _state, _ledger, _failed = _deploy_heax(tmp_path, health["url"], health["url"], {"heax": "old-fp"}, HEAX_FROZEN_SIFS="step_forge")
    finally:
        sifs.chmod(0o755)
    assert calls == ["appdata-merge-from-drive.sh"], (calls, out)
    assert "동결한 앱 SIF(HEAX_FROZEN_SIFS)를 쥐지 못해 Drive 받기를 하지 않았다" in out and "SKIP:heax failed" in out, out


def test_deploy_all_은_lib_를_들이고_받기_바로_앞뒤에서_쥐고_되돌린다():
    assert '. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/heax-frozen.sh"' in DEPLOY
    i = DEPLOY.index("if want heax; then\n")
    hb = DEPLOY[i:DEPLOY.index("# ── 3b. SignalForge", i)]
    hold, dist = hb.index("hwax_frozen_hold var/sifs"), hb.index("./deploy/apptainer/dist-from-drive.sh || _ddrc=$?")
    back = hb.index("hwax_frozen_restore var/sifs", dist)
    assert hb.rindex("_delib_hold ", 0, dist) < hold < dist < back < hb.index('[ "$_ddrc" = 0 ] || exit 1') < hb.index("hwax_restart_cycle heax ")
    assert "HEAX_FROZEN_SIFS" in (ROOT / "infra/.env.example").read_text(encoding="utf-8"), "박스 설정 자리를 예시에 적어 둔다"
