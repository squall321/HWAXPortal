# update-all §1 뒤 받은 편지함 알림 — 이번 git 받기로 새로 들었거나 바뀐 docs/cae00-inbox/*.md 만 찍는다(사용자 지시 10-31, docs/request-1030 C-20)
"""바깥 답이 필요한 물음은 마크다운으로 이 리포에 실어 보내고 cae00 이 읽는다. update-all 출력은 수백 줄이라 새 글이 왔다는 것을 알리는 줄이 없으면
아무도 폴더를 열지 않는다. 함수를 원문 그대로 떼어 진짜 git 리포에서 돌린다 — 받기 전 판을 §1 이 넘기는 길과, 옛 판의 §1 이 받은 첫 실행에서
git reset 이 남긴 ORIG_HEAD 로 가리는 길 둘 다."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin"}


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{\n.*?^\}}\n", SRC)
    assert m, f"update-all 에 {name} 가 없다"
    return m.group(0)


def _git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env={**GIT_ENV, "HOME": str(repo)})
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    """c1 → c2. c2 는 편지함 글 하나를 새로 들이고 · 하나를 고치고 · 하나를 지우고, 편지함 밖 글과 .md 가 아닌 파일도 바꾼다."""
    repo = tmp_path / "r"
    inbox = repo / "docs" / "cae00-inbox"
    inbox.mkdir(parents=True)
    _git(repo, "init", "-q")
    (inbox / "README.md").write_text("a\n")
    (inbox / "2026-10-30.md").write_text("old\n")
    (inbox / "gone.md").write_text("x\n")
    (repo / "docs" / "other.md").write_text("o\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c1")
    c1 = _git(repo, "rev-parse", "HEAD")
    (inbox / "README.md").write_text("b\n")
    (inbox / "2026-10-31.md").write_text("new\n")
    (inbox / "gone.md").unlink()
    (inbox / "note.txt").write_text("t\n")
    (repo / "docs" / "other.md").write_text("p\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c2")
    return repo, c1, _git(repo, "rev-parse", "HEAD")


def _run(repo: Path, **env: str) -> subprocess.CompletedProcess:
    body = f'set -uo pipefail\nSELF_REPO="{repo}"\n{_fn("_inbox_notice")}_inbox_notice\necho "END[${{INBOX_NOTE:-}}]"\n'
    return subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=30,
                          env={**GIT_ENV, "HOME": str(repo), **env})


def test_새로_들었거나_바뀐_편지함_글만_찍는다(tmp_path):
    repo, c1, _ = _repo(tmp_path)
    r = _run(repo, HWAX_UA_HEAD_BEFORE=c1)
    assert r.returncode == 0, r.stderr
    head = r.stdout.split("END[", 1)[0]
    assert "cae00 받은 편지함" in head and "글 2개" in head and c1[:7] in head, head
    listed = sorted(ln.strip() for ln in head.splitlines()[1:] if ln.strip())
    assert listed == ["docs/cae00-inbox/2026-10-31.md", "docs/cae00-inbox/README.md"], head
    assert "README.md" in r.stdout.split("END[", 1)[1], "끝 요약이 다시 낼 줄(INBOX_NOTE)에도 같은 목록이 든다"


def test_받은_글이_없으면_아무것도_찍지_않는다(tmp_path):
    repo, _, c2 = _repo(tmp_path)
    r = _run(repo, HWAX_UA_HEAD_BEFORE=c2)
    assert r.returncode == 0 and r.stdout == "END[]\n", r.stdout + r.stderr


def test_앞_판을_모르면_없다고_하지_않고_가리지_못했다고_한다(tmp_path):
    """모름을 '없음' 으로 찍으면 새 글이 와도 아무도 모른다 — 판정 파이프 교훈과 같은 갈래(조회 실패 ≠ 부재)."""
    repo, _, _ = _repo(tmp_path)
    r = _run(repo, HWAX_UA_HEAD_BEFORE="0123456789abcdef0123456789abcdef01234567")
    assert r.returncode == 0, r.stderr
    assert "가리지 못했다" in r.stdout and "docs/cae00-inbox/ 를 직접 본다" in r.stdout, r.stdout


def test_재실행_칸이_없으면_git_reset_이_남긴_ORIG_HEAD_로_가린다(tmp_path):
    """이 함수가 처음 드는 판은 옛 판의 §1 이 git 을 받는다 — 옛 §1 은 HWAX_UA_HEAD_BEFORE 를 넘기지 않지만 `git reset --hard origin/<가지>` 가
    ORIG_HEAD 에 받기 전 판을 남긴다. 그 꼴을 그대로 만든다(c1 에 있던 체크아웃을 c2 로 되돌려 맞춘다)."""
    repo, c1, c2 = _repo(tmp_path)
    _git(repo, "reset", "-q", "--hard", c1)
    _git(repo, "reset", "-q", "--hard", c2)
    assert _git(repo, "rev-parse", "ORIG_HEAD") == c1
    r = _run(repo)
    assert r.returncode == 0, r.stderr
    assert "글 2개" in r.stdout and "docs/cae00-inbox/2026-10-31.md" in r.stdout, r.stdout


def test_update_all_이_받기_전_판을_넘기고_받은_뒤와_끝에서_찍는다():
    s1 = SRC.index('hr "1) 포털 레포 최신화"')
    sub = SRC.index('( cd "$SELF_REPO"', s1)
    before = SRC.index('_ua_before="$(git -C "$SELF_REPO" rev-parse HEAD', s1)
    assert before < sub, "받기 전 판은 git 을 받는 서브셸보다 먼저 잰다"
    exec_line = SRC[SRC.index("exec env UPDATE_ALL_REEXEC=1", s1):].split("\n", 1)[0]
    assert 'HWAX_UA_HEAD_BEFORE="$_ua_before"' in exec_line, exec_line
    after = SRC.index('ok "포털 레포 최신 (재실행 완료)"\n_inbox_notice\nunset HWAX_UA_HEAD_BEFORE', s1)
    assert after > SRC.index(exec_line), "재실행(새 판)이 받은 뒤에 찍는다 — 옛 판이 받아도 새 판의 함수가 돈다"
    end = SRC.index('[ -z "${INBOX_NOTE:-}" ] || printf \'%s\' "$INBOX_NOTE"')
    assert SRC.index('hwax_skip_summary\nrm -f "$HWAX_SKIP_LEDGER"') < end < SRC.index("# ⚠ 경고 요약"), "끝 요약은 경고 요약 앞에서 다시 낸다"


def test_알림은_경고로_세지_않는다():
    """새 글은 할 일이지 결함이 아니다 — bad 로 내면 경고 수에 들어 진짜 경고와 섞인다(5차 요청 §5)."""
    fn = _fn("_inbox_notice")
    assert "bad " not in fn and "fail " not in fn and "WARN_ITEMS" not in fn, fn
