# update-all 받은 편지함 알림 — 이 박스에 마지막으로 알린 뒤 새로 들었거나 바뀐 docs/cae00-inbox/*.md 만 찍는다(사용자 지시 10-31, docs/request-1030 C-20)
"""바깥 답이 필요한 물음은 마크다운으로 이 리포에 실어 보내고 cae00 이 읽는다. update-all 출력은 수백 줄이라 새 글이 왔다는 것을 알리는 줄이 없으면
아무도 폴더를 열지 않는다. 함수를 원문 그대로 떼어 진짜 git 리포에서 돌린다.

기준은 '받기 전 판' 이 아니라 이 박스에 알린 판(infra/.state/inbox-head — 끝 요약을 낸 뒤 _inbox_mark 가 적는다)이다. 받기 전 판으로 가리면 배포
가이드의 받는 길(`git pull && update-all`)에서는 pull 이 이미 옮긴 판이 '받기 전' 이 되어 새 글이 말없이 빠졌다(반대 검토 10-31 — 아래 git pull 시험)."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin"}
STATE = Path("infra") / ".state" / "inbox-head"


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{\n.*?^\}}\n", SRC)
    assert m, f"update-all 에 {name} 가 없다"
    return m.group(0)


def _git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env={**GIT_ENV, "HOME": str(repo)})
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    """c1 → c2. c2 는 편지함 글 하나를 새로 들이고 · 하나를 고치고 · 하나를 지우고, 읽는 법(README.md) · 편지함 밖 글 · .md 가 아닌 파일도 바꾼다."""
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
    (inbox / "2026-10-30.md").write_text("fixed\n")
    (inbox / "2026-10-31.md").write_text("new\n")
    (inbox / "gone.md").unlink()
    (inbox / "note.txt").write_text("t\n")
    (repo / "docs" / "other.md").write_text("p\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c2")
    return repo, c1, _git(repo, "rev-parse", "HEAD")


def _mark(repo: Path, commit: str) -> None:
    """앞 실행이 끝 요약 뒤에 적은 '알린 판' 꼴 그대로 둔다(_inbox_mark 가 적는 자리 · 한 줄)."""
    (repo / STATE).parent.mkdir(parents=True, exist_ok=True)
    (repo / STATE).write_text(commit + "\n")


def _run(repo: Path, *, mark: bool = False, **env: str) -> subprocess.CompletedProcess:
    body = (f'set -uo pipefail\nSELF_REPO="{repo}"\n{_fn("_inbox_notice")}{_fn("_inbox_mark")}_inbox_notice\n'
            + ("_inbox_mark\n" if mark else "") + 'echo "END[${INBOX_NOTE:-}]"\n')
    return subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=30,
                          env={**GIT_ENV, "HOME": str(repo), **env})


def _listed(out: str) -> list[str]:
    return sorted(ln.strip() for ln in out.split("END[", 1)[0].splitlines()[1:] if ln.strip())


def test_마지막으로_알린_판_뒤에_새로_들었거나_바뀐_편지함_글만_찍는다(tmp_path):
    repo, c1, c2 = _repo(tmp_path)
    _mark(repo, c1)
    r = _run(repo)
    assert r.returncode == 0, r.stderr
    head = r.stdout.split("END[", 1)[0]
    assert "cae00 받은 편지함" in head and "글 2개" in head and c1[:7] in head and c2[:7] in head, head
    assert _listed(r.stdout) == ["docs/cae00-inbox/2026-10-30.md", "docs/cae00-inbox/2026-10-31.md"], head
    assert "README.md" not in "".join(_listed(r.stdout)), "읽는 법은 글로 세지 않는다 — 표가 바뀔 때마다 '글 N개' 가 부풀었다"
    assert "2026-10-31.md" in r.stdout.split("END[", 1)[1], "끝 요약이 다시 낼 줄(INBOX_NOTE)에도 같은 목록이 든다"


def test_알린_판이_지금_판이면_아무것도_찍지_않는다(tmp_path):
    repo, _, c2 = _repo(tmp_path)
    _mark(repo, c2)
    r = _run(repo)
    assert r.returncode == 0 and r.stdout == "END[]\n", r.stdout + r.stderr


def test_알린_판을_git_이_모르면_없다고_하지_않고_가리지_못했다고_한다(tmp_path):
    """모름을 '없음' 으로 찍으면 새 글이 와도 아무도 모른다 — 판정 파이프 교훈과 같은 갈래(조회 실패 ≠ 부재)."""
    repo, _, c2 = _repo(tmp_path)
    _mark(repo, "0123456789abcdef0123456789abcdef01234567")
    r = _run(repo, mark=True)
    assert r.returncode == 0, r.stderr
    assert "가리지 못했다" in r.stdout and "docs/cae00-inbox/" in r.stdout and "ls -t" in r.stdout, r.stdout
    assert (repo / STATE).read_text().strip() == c2, "모르는 판에 매여 실행마다 '가리지 못했다' 가 되지 않게 지금 판을 적는다"

    bare = tmp_path / "not-a-repo"                    # 지금 판조차 못 읽는다 — 역시 '없다' 가 아니고, 적을 판도 없다
    bare.mkdir()
    r = _run(bare, mark=True, GIT_CEILING_DIRECTORIES=str(tmp_path))   # 위쪽 디렉터리의 리포를 찾아 올라가지 않게
    assert r.returncode == 0 and "가리지 못했다" in r.stdout and not (bare / STATE).exists(), r.stdout + r.stderr


def test_알린_기록이_없으면_편지함_글을_모두_찍는다(tmp_path):
    """기록이 없으면(처음 도는 박스 · 기록을 지운 박스) 이 박스에 알린 글이 없다 — 지금 판의 글을 모두 찍는다. 처음 드는 판은 배포 가이드대로
    git pull 뒤에 돌아 '받기 전 판' 으로는 새 글이 하나도 안 보였다."""
    repo, _, _ = _repo(tmp_path)
    r = _run(repo, HWAX_UA_HEAD_BEFORE=_git(repo, "rev-parse", "HEAD"))
    assert r.returncode == 0, r.stderr
    assert "알린 기록이 없어" in r.stdout and "글 2개" in r.stdout, r.stdout
    assert _listed(r.stdout) == ["docs/cae00-inbox/2026-10-30.md", "docs/cae00-inbox/2026-10-31.md"], r.stdout


def test_git_pull_뒤에_update_all_을_돌려도_새_글을_찍는다(tmp_path):
    """cae00 의 받는 길 — `git pull && update-all`. pull 이 이미 새 판으로 옮겨 §1 의 받기 · reset 은 할 일이 없고(ORIG_HEAD 도 새 판이 된다),
    받기 전 판으로 가리던 때는 알림이 비었다. 진짜 origin · 박스 클론에서 그 차례 그대로 돈다."""
    origin, dev, box = tmp_path / "origin.git", tmp_path / "dev", tmp_path / "box"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env={**GIT_ENV, "HOME": str(tmp_path)})
    subprocess.run(["git", "clone", "-q", str(origin), str(dev)], check=True, capture_output=True, env={**GIT_ENV, "HOME": str(tmp_path)})
    _git(dev, "checkout", "-q", "-b", "main")
    (dev / "docs" / "cae00-inbox").mkdir(parents=True)
    (dev / "docs" / "cae00-inbox" / "2026-10-30.md").write_text("q\n")
    _git(dev, "add", "-A")
    _git(dev, "commit", "-qm", "c1")
    _git(dev, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", "-b", "main", str(origin), str(box)], check=True, capture_output=True,
                   env={**GIT_ENV, "HOME": str(tmp_path)})
    first = _run(box, mark=True)                       # 앞 실행 — 그때의 글을 알리고 끝에서 판을 적었다
    assert _listed(first.stdout) == ["docs/cae00-inbox/2026-10-30.md"], first.stdout
    (dev / "docs" / "cae00-inbox" / "2026-10-31.md").write_text("new\n")
    _git(dev, "add", "-A")
    _git(dev, "commit", "-qm", "c2")
    _git(dev, "push", "-q", "origin", "main")
    _git(box, "pull", "-q", "--ff-only")              # 사람이 먼저 받는다
    _git(box, "fetch", "-q", "origin", "main")        # §1 — 받을 것이 없다
    _git(box, "reset", "-q", "--hard", "origin/main")
    now = _git(box, "rev-parse", "HEAD")
    assert _git(box, "rev-parse", "ORIG_HEAD") == now, "§1 의 reset 이 ORIG_HEAD 를 새 판으로 덮는다 — 그 길로는 가릴 수 없다"
    r = _run(box, HWAX_UA_HEAD_BEFORE=now)            # 옛 §1 이 재실행에 넘기던 '받기 전 판' 은 이미 새 판이다
    assert r.returncode == 0, r.stderr
    assert _listed(r.stdout) == ["docs/cae00-inbox/2026-10-31.md"], r.stdout


def test_끊긴_실행은_다음에_다시_알리고_끝까지_간_실행만_판을_적는다(tmp_path):
    repo, c1, c2 = _repo(tmp_path)
    _mark(repo, c1)
    a1, a2 = _run(repo), _run(repo)                   # 끝 요약 앞에서 끊겼다 — 적지 않는다
    assert _listed(a1.stdout) == _listed(a2.stdout) == ["docs/cae00-inbox/2026-10-30.md", "docs/cae00-inbox/2026-10-31.md"]
    assert (repo / STATE).read_text().strip() == c1
    done = _run(repo, mark=True)
    assert _listed(done.stdout) and (repo / STATE).read_text().strip() == c2, done.stdout + done.stderr
    assert _run(repo).stdout == "END[]\n", "끝까지 간 실행 뒤에는 같은 글을 다시 알리지 않는다"


def test_기록_자리가_없어도_만들어_적고_못_적으면_한_줄로_말한다(tmp_path):
    repo, _, c2 = _repo(tmp_path)
    r = _run(repo, mark=True)
    assert r.returncode == 0 and (repo / STATE).read_text().strip() == c2, r.stdout + r.stderr
    (repo / STATE).unlink()
    (repo / STATE).mkdir()                            # 그 자리에 파일을 쓸 수 없다
    r = _run(repo, mark=True)
    assert r.returncode == 0 and "적지 못했다" in r.stdout, r.stdout + r.stderr


def test_update_all_이_받은_뒤_찍고_끝_요약_뒤에만_판을_적는다():
    s1 = SRC.index('hr "1) 포털 레포 최신화"')
    exec_line = SRC[SRC.index("exec env UPDATE_ALL_REEXEC=1", s1):].split("\n", 1)[0]
    after = SRC.index('ok "포털 레포 최신 (재실행 완료)"\n_inbox_notice\n', s1)
    assert after > SRC.index(exec_line), "재실행(새 판)이 받은 뒤에 찍는다 — 옛 판이 받아도 새 판의 함수가 돈다"
    assert "HWAX_UA_HEAD_BEFORE" not in SRC, "받기 전 판은 기준이 아니다 — 넘기는 줄이 남으면 다시 기준으로 쓰기 쉽다"
    end = SRC.index('[ -z "${INBOX_NOTE:-}" ] || printf \'%s\' "$INBOX_NOTE"\n_inbox_mark\n')
    assert SRC.index('hwax_skip_summary\nrm -f "$HWAX_SKIP_LEDGER"') < end < SRC.index("# ⚠ 경고 요약"), "끝 요약은 경고 요약 앞에서 다시 낸다"
    assert end < SRC.index('if [ "$FAIL" = 1 ]; then', end), "실패로 끝나는 실행도 끝 요약을 냈으면 판을 적는다"
    assert len(re.findall(r"(?m)^_inbox_mark$", SRC)) == 1, "판을 적는 곳은 끝 요약 뒤 하나뿐이다"


def test_알림은_경고로_세지_않는다():
    """새 글은 할 일이지 결함이 아니다 — bad 로 내면 경고 수에 들어 진짜 경고와 섞인다(5차 요청 §5)."""
    for name in ("_inbox_notice", "_inbox_mark"):
        fn = _fn(name)
        assert "bad " not in fn and "fail " not in fn and "WARN_ITEMS" not in fn, fn
