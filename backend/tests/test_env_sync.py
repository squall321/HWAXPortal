# 새 설정이 **이미 있는 .env** 에 자동으로 들어오는가 — 그리고 위험한 것은 자동으로 안 켜지는가
"""왜 — 코드에 옵션이 늘면 `.env.example` 에는 적히지만 배포된 박스의 `.env` 는 그대로다.
그 차이는 조용하다. 09-19 에 StepForge 공개주소가 dev 에만 있고 cae00 에 없어 앱이 자리표시자
URL 을 냈다. 사람이 문서를 보고 손으로 넣는 방식은 박스가 늘수록 반드시 어긋난다.

이 시험은 `infra/scripts/env-sync.sh` 를 **그대로 실행**한다(가짜 리포를 만들어 인자로 준다). 스크립트는 임시 포털에 복사해 돌린다 —
백업은 스크립트가 든 포털의 infra/.state/env-sync-backups 에 쌓이므로 실물 리포에서 돌리면 체크아웃의 상태 디렉터리에 시험 찌꺼기가 남는다.
"""
import datetime
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra" / "scripts" / "env-sync.sh"


def portal_copy(tmp_path: Path) -> Path:
    """임시 포털에 env-sync.sh(+ 장부 lib)를 복사해 그 경로를 낸다 — 다른 시험 파일도 이것으로 돌린다."""
    scripts = tmp_path / "HWAXPortal" / "infra" / "scripts"
    (scripts / "lib").mkdir(parents=True, exist_ok=True)
    shutil.copy(SCRIPT, scripts / "env-sync.sh")
    shutil.copy(ROOT / "infra/scripts/lib/skip-ledger.sh", scripts / "lib/skip-ledger.sh")
    return scripts / "env-sync.sh"


def _repo(tmp_path, example: str, env: str) -> Path:
    d = tmp_path / "repo"
    d.mkdir(exist_ok=True)
    (d / ".env.example").write_text(example, encoding="utf-8")
    (d / ".env").write_text(env, encoding="utf-8")
    return d


def _run(d: Path, *args, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(portal_copy(d.parent)), str(d), *args],
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(d.parent), **env})


def _baks(d: Path) -> list[Path]:
    """repo 의 백업 — 임시 포털의 infra/.state/env-sync-backups/<리포 이름>/.env.<UTC>[-n]."""
    bk = d.parent / "HWAXPortal/infra/.state/env-sync-backups" / d.name
    return sorted(bk.glob(".env.*")) if bk.is_dir() else []


def test_a_new_safe_option_is_filled_in(tmp_path):
    d = _repo(tmp_path, "OLD=1\nNEW_TIMEOUT=30\n", "OLD=1\n")
    r = _run(d)
    body = (d / ".env").read_text(encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "\nNEW_TIMEOUT=30\n" in body, body
    assert body.startswith("OLD=1\n"), "기존 내용·순서가 보존돼야 한다"


def test_secrets_and_placeholders_are_never_activated(tmp_path):
    d = _repo(tmp_path,
              "API_TOKEN=paste-me\nDB_PASSWORD=CHANGE_ME_x\nPUBLIC_BASE=http://<호스트>\nSAFE=2\n",
              "OLD=1\n")
    r = _run(d)
    body = (d / ".env").read_text(encoding="utf-8")
    for k in ("API_TOKEN", "DB_PASSWORD", "PUBLIC_BASE"):
        assert f"\n# {k}=" in body, f"{k} 를 활성으로 넣었다 — 그럴듯하게 틀린 설정이 된다\n{body}"
    assert "\nSAFE=2\n" in body, "안전한 값은 켜져야 한다"
    assert "값을 운영자가 정해야 한다" in body
    assert "값을 정해야 한다" in r.stdout, "무엇을 채워야 하는지 사람에게 말해야 한다"


def test_an_option_declared_only_as_a_comment_is_still_surfaced(tmp_path):
    """예시에 주석으로만 적힌 옵션이 **바로 cae00 에서 빠졌던 그 값**이다(StepForge 공개주소)."""
    d = _repo(tmp_path, "# APPTAINERENV_STEPFORGE_PUBLIC_BASE=http://<포털>\nSAFE=1\n", "OLD=1\n")
    _run(d)
    body = (d / ".env").read_text(encoding="utf-8")
    assert "# APPTAINERENV_STEPFORGE_PUBLIC_BASE=" in body, f"주석 선언을 못 봤다\n{body}"


def test_it_is_idempotent(tmp_path):
    d = _repo(tmp_path, "NEW=1\nTOKEN_X=fill-me\n", "OLD=1\n")
    _run(d)
    first = (d / ".env").read_text(encoding="utf-8")
    _run(d)
    assert (d / ".env").read_text(encoding="utf-8") == first, "두 번째 실행이 또 붙였다"


def test_a_declared_key_is_never_added_again_however_long_the_env_is(tmp_path):
    """**박스가 정한 값이 예시 기본값으로 뒤집히던 자리.** 선언 여부를 `printf … | grep -qx` 로 봤다 — bash 의 printf 는 줄마다
    따로 쓰고 grep -q 는 첫 일치에서 닫으므로, 목록이 길면 printf 가 SIGPIPE(141)로 죽고 pipefail 이 그것을 '선언 안 됨' 으로
    읽는다. 그러면 이미 있는 키를 예시 값으로 **끝에 한 번 더** 붙인다 — 소싱하면 뒤의 줄이 이겨 박스의 값이 조용히 바뀐다.
    실측(2026-10-07 dev): 키 50개에 40회 중 1회, 5,000개에 40회 중 40회. 여기서는 늘 터지는 크기로 본다."""
    env = "AAA_FIRST=box-value\n" + "".join(f"K{i:05d}=1\n" for i in range(5000))
    d = _repo(tmp_path, "AAA_FIRST=example-default\n", env)
    r = _run(d)
    assert r.returncode == 0, r.stdout + r.stderr
    body = (d / ".env").read_text(encoding="utf-8")
    assert "AAA_FIRST=example-default" not in body, "선언된 키를 예시 값으로 또 붙였다 — 뒤의 줄이 이긴다"
    assert body == env, "빠진 설정이 없으면 아무것도 쓰지 않는다"
    assert "자동 추가 0" in r.stdout


def test_existing_values_are_never_touched(tmp_path):
    d = _repo(tmp_path, "PORT=8080\n", "PORT=9999\n")
    _run(d)
    body = (d / ".env").read_text(encoding="utf-8")
    assert "PORT=9999" in body and "PORT=8080" not in body, "박스가 정한 값을 예시로 덮었다"


def test_check_mode_writes_nothing_and_fails_loudly(tmp_path):
    d = _repo(tmp_path, "NEW=1\n", "OLD=1\n")
    before = (d / ".env").read_text(encoding="utf-8")
    r = _run(d, "--check")
    assert r.returncode == 1, "빠진 것이 있는데 0 으로 끝났다"
    assert (d / ".env").read_text(encoding="utf-8") == before
    assert not list(d.glob(".env.bak-*")) and not _baks(d), "--check 인데 백업을 만들었다"


def test_a_backup_is_made_before_writing(tmp_path):
    d = _repo(tmp_path, "NEW=1\n", "OLD=1\n")
    r = _run(d)
    baks = _baks(d)
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "OLD=1\n"
    assert f"백업 {baks[0]}" in r.stdout, "백업의 전체 경로를 말한다(이름만으로는 포털 infra/.state 아래를 못 찾는다)"


def test_backups_never_land_in_the_service_repo(tmp_path):
    """**LLM 풀 반대 검토 H1 회귀** — `.env.bak-*` 가 서비스 리포 안(gitignore 밖)에 비밀째 남았고, deploy-all 의 `git stash push -u` 가
    그 가운데 셋을 stash 로 쓸어 갔다(HEAXHub 에 셋이 남아 있었다). 백업은 포털의 gitignore 된 infra/.state/env-sync-backups 에만 —
    디렉터리 700 · 파일 600(원본이 644 여도). 시각은 UTC(`Z`)다."""
    d = _repo(tmp_path, "NEW=1\n", "SECRET_TOKEN=s3cr3t\n"); (d / ".env").chmod(0o644)
    _run(d)
    assert sorted(p.name for p in d.iterdir()) == [".env", ".env.example"], "서비스 리포에 백업이 남았다"
    baks = _baks(d)
    assert len(baks) == 1 and stat.S_IMODE(baks[0].stat().st_mode) == 0o600
    m = re.fullmatch(r"\.env\.(\d{8}T\d{6})Z", baks[0].name)
    assert m, baks[0].name
    stamp = datetime.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=datetime.timezone.utc)
    assert abs((datetime.datetime.now(datetime.timezone.utc) - stamp).total_seconds()) < 600, "UTC 가 아니다(박스 시각에 Z 를 붙였다)"
    bkroot = tmp_path / "HWAXPortal/infra/.state/env-sync-backups"
    for p in (bkroot, bkroot / d.name):
        assert stat.S_IMODE(p.stat().st_mode) == 0o700, p


def test_a_sub_directory_env_keeps_its_path_in_the_backup(tmp_path):
    """infra/.env · platform/.env 는 리포 안 경로 그대로 — 같은 리포의 두 .env 가 섞이지 않는다. 같은 초에 다시 써도 앞 백업을 덮지 않는다."""
    d = tmp_path / "repo"; (d / "infra").mkdir(parents=True)
    (d / "infra/.env.example").write_text("NEW=1\n"); (d / "infra/.env").write_text("OLD=1\n")
    _run(d)
    bk = tmp_path / "HWAXPortal/infra/.state/env-sync-backups/repo/infra"
    assert [p.read_text() for p in bk.glob(".env.*")] == ["OLD=1\n"]
    (d / "infra/.env.example").write_text("NEW=1\nNEWER=2\n")
    _run(d)
    assert len(list(bk.glob(".env.*"))) == 2, "두 번째 실행의 백업이 앞 백업을 덮었다"


def test_no_write_without_a_backup(tmp_path):
    """백업을 못 만들면(포털 상태 디렉터리에 쓸 수 없다) 건드리지 않는다 — 그리고 **채웠다고 말하지 않는다**(LLM 풀 반대 검토 2라운드 LOW 5).
    종전엔 세고 나서 백업이 실패해, 하나도 못 채운 실행이 '✓ env-sync … 자동 추가 1' · 종료코드 0 으로 끝났다 — update-all 1c 가 초록으로
    지나갔다. 이제 그 리포는 ✗ 이고 끝 줄도 ✗(✓ 아님) · 자동 추가 0 · 종료코드 2 다. 장부에도 '들어갔다' 를 적지 않는다."""
    if os.geteuid() == 0:
        return
    d = _repo(tmp_path, "NEW=1\nOPT_SECRET=\n", "OLD=1\n")
    state = tmp_path / "HWAXPortal/infra/.state"; state.mkdir(parents=True); state.chmod(0o555)
    ledger = tmp_path / "ledger"; ledger.write_text("")
    try:
        r = _run(d, HWAX_SKIP_LEDGER=str(ledger))
    finally:
        state.chmod(0o755)
    assert (d / ".env").read_text(encoding="utf-8") == "OLD=1\n" and "백업 실패" in r.stderr, r.stdout + r.stderr
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    last = r.stdout.strip().splitlines()[-1]
    assert last.startswith("✗ env-sync:") and "자동 추가 0" in last and "사람이 정할 것 0" in last and d.name in last, r.stdout
    assert "✓ env-sync" not in r.stdout, "못 채운 실행을 ✓ 로 끝냈다"
    assert ledger.read_text() == "", "들어가지 않은 주석 줄을 장부에 '들어갔다' 로 적었다"


@pytest.mark.parametrize("rc,want_fail", [(2, True), (0, False)])
def test_update_all_counts_a_failed_env_sync(tmp_path, rc, want_fail):
    """env-sync 의 0 아닌 값을 update-all 1c 가 버리지 않는다 — 종전엔 `|| true` 로 버려 못 채운 실행이 초록으로 지나갔다. 1c 구획을 원문
    그대로 떼어 임시 포털의 대역 env-sync.sh 로 돌린다(실물 env-sync 는 형제 리포의 .env 를 고친다)."""
    ua = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    i = ua.index('hr "1c) .env 옵션 동기화"')
    block = ua[i:ua.index("# ── 1d)", i)]
    portal = tmp_path / "HWAXPortal"; (portal / "infra/scripts").mkdir(parents=True)
    stub = portal / "infra/scripts/env-sync.sh"
    stub.write_text(f'#!/usr/bin/env bash\necho "(대역) env-sync"\necho "  ✗ 대역 리포 — 백업 실패" >&2\nexit {rc}\n'); stub.chmod(0o755)
    script = "\n".join(["set -uo pipefail", f'SELF_REPO="{portal}"',
                        f'grep -q "(대역) env-sync" "$SELF_REPO/infra/scripts/env-sync.sh" || exit 97',
                        'hr() { :; }; hwax_skip() { echo "SKIP:$*"; }; fail() { echo "FAIL:$*"; }', block, "echo END"])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert r.returncode != 97 and "END" in r.stdout and "(대역) env-sync" in r.stdout, r.stdout + r.stderr
    fails = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    assert bool(fails) == want_fail and (not fails or f"env-sync rc {rc}" in fails[0]), r.stdout


def test_a_big_backlog_goes_to_a_human_instead_of_flipping_switches(tmp_path):
    """평상시 드리프트는 한두 개다. 수십 개가 한꺼번이면 '이 박스가 오래 안 맞춰졌다' 이고,
    그때 기본값을 통째로 켜면 **도는 서비스의 동작이 한 번에 바뀐다**."""
    ex = "".join(f"OPT{i}={i}\n" for i in range(15))
    d = _repo(tmp_path, ex, "OLD=1\n")
    r = _run(d)
    body = (d / ".env").read_text(encoding="utf-8")
    assert body == "OLD=1\n", "상한을 넘겼는데 활성화했다"
    assert "사람이 봐야 한다" in r.stdout
    # 상한을 올리면 적용된다 — 막는 것이 아니라 **사람의 결정을 요구**하는 것이다
    r2 = _run(d, HWAX_ENV_SYNC_MAX="50")
    assert "OPT14=14" in (d / ".env").read_text(encoding="utf-8"), r2.stdout
