# 새 설정이 **이미 있는 .env** 에 자동으로 들어오는가 — 그리고 위험한 것은 자동으로 안 켜지는가
"""왜 — 코드에 옵션이 늘면 `.env.example` 에는 적히지만 배포된 박스의 `.env` 는 그대로다.
그 차이는 조용하다. 09-19 에 StepForge 공개주소가 dev 에만 있고 cae00 에 없어 앱이 자리표시자
URL 을 냈다. 사람이 문서를 보고 손으로 넣는 방식은 박스가 늘수록 반드시 어긋난다.

이 시험은 `infra/scripts/env-sync.sh` 를 **그대로 실행**한다(가짜 리포를 만들어 인자로 준다).
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra" / "scripts" / "env-sync.sh"


def _repo(tmp_path, example: str, env: str) -> Path:
    d = tmp_path / "repo"
    d.mkdir(exist_ok=True)
    (d / ".env.example").write_text(example, encoding="utf-8")
    (d / ".env").write_text(env, encoding="utf-8")
    return d


def _run(d: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), str(d), *args],
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(d.parent)})


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
    assert not list(d.glob(".env.bak-*")), "--check 인데 백업을 만들었다"


def test_a_backup_is_made_before_writing(tmp_path):
    d = _repo(tmp_path, "NEW=1\n", "OLD=1\n")
    _run(d)
    baks = list(d.glob(".env.bak-*"))
    assert len(baks) == 1 and baks[0].read_text(encoding="utf-8") == "OLD=1\n"


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
    r2 = subprocess.run(["bash", str(SCRIPT), str(d)], capture_output=True, text=True,
                        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
                             "HWAX_ENV_SYNC_MAX": "50"})
    assert "OPT14=14" in (d / ".env").read_text(encoding="utf-8"), r2.stdout
