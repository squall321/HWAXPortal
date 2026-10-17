# update-all 1절의 자동 stash — 비밀 든 손 백업은 쓸어 가지 않고, 쓸어 간 것은 추적 안 되던 파일까지 보인다(10-17 cae00 리뷰 P4 · D7)
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = ROOT / "infra" / "scripts" / "update-all.sh"


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{\n.*?^\}}\n", UA.read_text(encoding="utf-8"))
    assert m, f"update-all 에 {name} 가 없다"
    return m.group(0)


@pytest.mark.parametrize("rel", ["infra/.env.bak-20261017", "infra/.env.bak", "backend/config/routes.local.env.bak_20261016_pre_stcxllm",
                                 "infra/.env.20261017-062446.bak"])
def test_비밀_든_설정의_손_백업은_git_이_무시한다(rel):
    """무시하지 않으면 update-all 의 `git stash push -u` 가 쓸어 가 비밀이 stash 의 git 객체로 남는다 — cae00 옛 자동 stash 셋에
    infra/.env 백업이 있었다(리뷰 D7)."""
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", rel], capture_output=True, text=True)
    assert r.returncode == 0, f"{rel} 가 무시되지 않는다"


def test_예제_파일은_무시되지_않는다():
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--no-index", "infra/.env.example"], capture_output=True, text=True)
    assert r.returncode == 1


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True, env={**env, "PATH": "/usr/bin:/bin"})  # noqa: E731
    run("init", "-q")
    (repo / "tracked.txt").write_text("a\n")
    run("add", "tracked.txt")
    run("commit", "-qm", "init")
    (repo / "tracked.txt").write_text("b\n")
    (repo / "loose-note.txt").write_text("untracked\n")
    run("stash", "push", "-u", "-q", "-m", "update-all auto-stash")
    return repo


@pytest.mark.parametrize("old_git", [False, True])
def test_stash_대상에_추적_안_되던_파일도_보인다(tmp_path, old_git):
    """`git stash show --name-only` 만으로는 -u 로 쓸어 간 파일이 안 보여 알림의 '대상:' 뒤가 비었다(P4). git 2.32 보다 옛것이면
    --include-untracked 가 없어 세 번째 부모(^3)를 직접 읽는다."""
    repo = _repo(tmp_path)
    shim = ('git() { case " $* " in *" --include-untracked "*) return 129 ;; esac; command git "$@"; }\n' if old_git else "")
    r = subprocess.run(["bash", "-c", shim + _fn("_stash_names") + "_stash_names | sort -u"], cwd=repo,
                       capture_output=True, text=True, timeout=30)
    assert r.stdout.split() == ["loose-note.txt", "tracked.txt"], (r.stdout, r.stderr)


def test_비밀_경고_무늬는_env_와_secret_을_잡고_평범한_파일은_안_잡는다():
    pat = re.search(r"grep -qE '([^']+)'; then\n\s+echo \"  ⚠ 비밀이 든 듯한", UA.read_text(encoding="utf-8"))
    assert pat, "update-all 의 비밀 경고 줄을 못 찾았다"
    hit = lambda name: subprocess.run(["grep", "-qE", pat.group(1)], input=name + "\n", text=True).returncode == 0  # noqa: E731
    for name in ("infra/.env", "infra/.env.bak-1", "backend/config/routes.local.env.bak_x", "secrets.json", "x/.env.local"):
        assert hit(name), name
    for name in ("README.md", "frontend/src/environment.ts", "docs/envelope.md"):
        assert not hit(name), name
