# update-all 이 ste 코드를 **실제로 최신화**하는지 — 힌트만 찍고 끝내지 않는다
"""왜 — ste 웹은 이 리포가 배포하는 사이트가 아니라 형제 리포가 자기 헤드노드에 배포한다.
그래서 update-all 은 힌트 한 줄만 찍었고, 그 결과 **소스에는 있는데 박스에는 없는** 상태가
조용히 생겼다. 배포된 빌드에 `/api/auth/sso` 가 아예 없어서 포털→ste 자격 중계가 시크릿을
맞게 줘도 401 이었다(2026-09-23 실측). 게이트웨이의 ste per_user 위임도 같은 엔드포인트라
함께 죽어 있었는데, 게이트는 전부 초록이었다.

여기서 못박는 것은 넷이다.
  ① update-all 이 deploy-ste.sh 를 **--if-stale 로 부른다**(힌트가 아니라 호출).
  ② 실패해도 update-all 전체를 죽이지 않는다 — 다른 서비스 갱신까지 막을 이유가 없다.
  ③ 에어갭(teleport)은 **명시 opt-in 없이 안 돈다** — 실배포가 routine·크론에 섞이면 안 된다.
  ④ 자동 호출이 **Drive 부트스트랩을 발화시키지 않는다** — 리포가 없는 박스에서 update-all
     한 번이 22MB 다운로드와 git clone 을 시작하던 것을 실측으로 잡았다.
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPDATE_ALL = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
DEPLOY_STE = ROOT / "infra/scripts/deploy-ste.sh"
SRC = DEPLOY_STE.read_text(encoding="utf-8")


def test_update_all_이_ste_를_힌트가_아니라_호출로_최신화한다():
    assert "2c) ste 코드 최신화" in UPDATE_ALL, "ste 최신화 단계가 사라졌다"
    assert "deploy-ste.sh\" --if-stale" in UPDATE_ALL, (
        "update-all 이 deploy-ste.sh 를 --if-stale 로 불러야 한다 — 힌트만 찍으면 낡은 채로 남는다")


def test_ste_최신화_실패가_update_all_전체를_죽이지_않는다():
    """다른 서비스 갱신까지 막을 이유가 없다. 최종 판정은 §6 ste 게이트가 한다."""
    i = UPDATE_ALL.index("2c) ste 코드 최신화")
    block = UPDATE_ALL[i:i + 1400]
    assert "bad \"ste 최신화 실패" in block, "실패를 말하지 않으면 조용히 낡은 채로 지나간다"
    assert "exit 1" not in block, "이 단계는 전체를 끊지 않는다"


def test_에어갭은_공용_게이트를_통과할_때만_돈다():
    """옛 단일 플래그(STE_DEPLOY=1 필수)는 존재하지 않는 크론을 막느라 "update-all 한 번에 셋업" 을
    깼다(2026-09-24 조사, 사용자 결정 D-13). 지금은 공용 게이트(사람 호출 ∧ 신선도 ∧ 세션)다 —
    routine 에서는 여전히 안 돌고, --with-ste 나 STE_DEPLOY=1 은 강제다. 규칙 자체는 test_deploy_gate 가 본다."""
    assert "deploy-gate.sh" in SRC and "hwax_gate ste" in SRC
    assert 'STE_DEPLOY:-0}" != 1 ]; then' not in SRC, "옛 단일 플래그 게이트가 남아 있으면 두 규칙이 겹친다"
    # 게이트는 자동 호출(--if-stale)에서만 걸린다 — 사람이 직접 부르면 종전대로 곧장 간다.
    i = SRC.index("hwax_gate ste")
    assert 'if [ "$IF_STALE" = 1 ]; then' in SRC[i - 2500:i]


def _run(env_extra, *args, timeout=60):
    # 상한을 짧게 둔다 — 상한 가드가 회귀하면 **빨리** 깨져야 한다. 120초로 두면 회귀할 때마다
    # 시험이 2분씩 매달린다(실제로 그랬다).
    env = {**os.environ, **env_extra}
    return subprocess.run(["bash", str(DEPLOY_STE), *args],
                          capture_output=True, text=True, env=env, timeout=timeout)


# ⚠ 출력에 담기는 것은 **경로**이므로 "부트스트랩" 한 단어로 판정하면 tmp 경로에 시험 이름이
#   들어가 스스로 걸린다(실제로 한 번 걸렸다). Drive 경로가 실제로 시작될 때만 나오는 문구를 본다.
_BOOTSTRAP = "Drive 스테이징에서 부트스트랩"


def test_리포가_없으면_Drive_부트스트랩을_발화시키지_않는다(tmp_path):
    """update-all 한 번이 22MB 다운로드를 시작하던 것 — 실측으로 잡았다.

    ⚠ "건너뛴다" 만 보면 **약하다.** 리포 부재 가드를 떼도 뒤의 접속설정 가드가 같은 말을
    찍어서 시험이 통과한다(변이 검사에서 실제로 그랬다). 그래서 이 가드만 내는 문구를 본다.
    """
    r = _run({"STE_REPO": str(tmp_path / "nope")}, "--if-stale")
    assert r.returncode == 0, r.stderr
    assert "ste 리포가 이 박스에 없다" in r.stdout, "리포 부재를 그 사유로 말해야 한다"
    assert _BOOTSTRAP not in r.stdout, "자동 호출이 Drive 부트스트랩으로 넘어갔다"


def test_사람이_직접_부르면_부트스트랩을_막지_않는다(tmp_path):
    """--if-stale 이 없으면 최초 반입 경로다 — 그건 그대로 살아 있어야 한다."""
    r = _run({"STE_REPO": str(tmp_path / "nope"), "STE_DRIVE_REMOTE": "없는리모트:"}, )
    # 리모트가 없어 곧 죽지만, **부트스트랩으로 들어갔다는 사실**이 확인되면 된다.
    assert _BOOTSTRAP in r.stdout + r.stderr, "직접 호출에서도 최초 반입 경로가 막혔다"


def test_접속_설정이_없으면_건너뛴다(tmp_path):
    repo = tmp_path / "ste"
    (repo / "deploy").mkdir(parents=True)
    rc = repo / "deploy/refresh-code.sh"
    rc.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    rc.chmod(0o755)
    r = _run({"STE_REPO": str(repo)}, "--if-stale")
    assert r.returncode == 0, r.stderr
    assert "접속 설정이 없다" in r.stdout, "접속설정 부재를 그 사유로 말해야 한다"
    assert "ste 리포가 이 박스에 없다" not in r.stdout, "리포는 있다 — 사유가 뒤바뀌었다"
    assert _BOOTSTRAP not in r.stdout


def test_원격을_못_읽으면_같다고_보지_않는다(tmp_path):
    """모름을 같음으로 읽으면 낡은 박스를 영원히 건너뛰면서 초록을 낸다.

    그리고 **바운드돼야 한다** — update-all 이 매 실행 이 경로를 타므로, 헤드가 죽은 박스에서
    무한정 매달리면 갱신 전체가 멈춘다(ConnectTimeout 이 없을 때 40초에도 안 끝났다).
    """
    import time
    ste = ROOT.parent / "SmartTwinExplorer"
    if not (ste / "deploy/deploy-backend.sh").exists():
        import pytest
        pytest.skip("ste 리포가 옆에 없다")
    tenv = tmp_path / "dead.env"
    tenv.write_text(
        "TRANSPORT_MODE=direct\nREMOTE_USER=nobody\nHEAD_HOST=192.0.2.1\n"
        "SSH_KEY=~/.ssh/ste_cluster_ed25519\nREMOTE_APP=/opt/ste\n", encoding="utf-8")
    t0 = time.monotonic()
    r = _run({"STE_TRANSPORT_ENV": str(tenv), "STE_CONNECT_TIMEOUT": "3"}, "--if-stale")
    elapsed = time.monotonic() - t0
    assert "이미 최신" not in r.stdout, "닿지도 못했는데 '최신' 이라고 했다 — 가짜 초록이다"
    assert r.returncode != 0, "닿지 못한 것은 실패로 알려야 한다"
    assert elapsed < 45, f"닿지 않는 헤드에 {elapsed:.0f}초 매달렸다 — 상한이 안 걸렸다"
