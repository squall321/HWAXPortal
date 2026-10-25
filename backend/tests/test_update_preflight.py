# update-all 사전 점검(update-preflight.py) — 가짜 리포 · 가짜 rclone 으로 판정 하나하나를 본다(실서비스 · 실 Drive 에 닿지 않는다)
"""왜 — cae00 에서 update-all 전에 '무엇이 끊기고 무엇이 사라지나' 를 보려고 만든 읽기 전용 점검이다(10-25 cae00 업데이트 점검).
틀린 ✓ 는 사람을 안심시켜 데이터를 잃게 하고, 틀린 ✗ 는 점검을 안 믿게 만든다. 그래서 판정마다 그 조건을 실제로 만들어 본다.

  · 설정(.env)이 가리키는 파일을 git 이 모르면 ✗ — update-all 첫 stash 가 치운다(cae00 의 타일 목록 systems.cae00.yaml 이 그 꼴이다).
    알려 준 제외 명령을 따르면 ✗ 가 사라진다. 무시된 파일 · 그 밖의 파일은 ✗ 가 아니다.
  · reset 하는 리포의 로컬 커밋은 ✗(reset --hard 가 버린다). pull 하는 리포는 들어올 변경과 겹치는 로컬 파일만 ✗.
  · 포털 카탈로그 — 파일이 없으면 ✗, mx-white-paper 항목에 claims_affiliation 이 없으면 ⚠(다음 항목의 값을 빌려 보지 않는다).
  · MX 백서 위임 비밀 — 다르면 ✗ 이고 비밀 원문은 어디에도 찍히지 않는다.
  · LLM_CONTEXT_TOKENS 가 서버 창보다 작으면 ⚠ — 에이전트 /health 의 서버 답, 없으면 에이전트와 같은 /models 길.
  · 허브 Drive 대조 목록이 latest/ 와 어긋나면 ✗(받는 쪽 sha256sum -c 가 멈춘다).
  · 원격 판을 표준입력으로(`git show … | python3 -`) 돌리면 지금 자리를 포털 리포 루트로 쓴다.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "infra/scripts/update-preflight.py"
_GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env={**os.environ, **_GIT_ENV})
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout


def _repo(base: Path, name: str, files: dict[str, str]) -> Path:
    """base/<name> — 처음 커밋을 base/remotes/<name>.git 에 올리고 그것을 upstream 으로 둔다."""
    bare = base / "remotes" / f"{name}.git"
    bare.mkdir(parents=True)
    _git(bare, "init", "--bare", "-q", "-b", "main")
    r = base / name
    r.mkdir(parents=True)
    _git(r, "init", "-q", "-b", "main")
    for k, v in files.items():
        (r / k).parent.mkdir(parents=True, exist_ok=True)
        (r / k).write_text(v)
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "init")
    _git(r, "remote", "add", "origin", str(bare))
    _git(r, "push", "-q", "-u", "origin", "main")
    return r


@pytest.fixture()
def pf(tmp_path, monkeypatch):
    """점검 모듈 — ROOT 는 tmp/HWAXPortal(형제 리포는 tmp 아래), 원격은 묻지 않고, 루프백은 닫힌 포트."""
    monkeypatch.setenv("HWAX_PREFLIGHT_AGENT", "http://127.0.0.1:9")
    monkeypatch.setenv("HWAX_PREFLIGHT_MXWP", "http://127.0.0.1:9")
    for k, v in _GIT_ENV.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location("update_preflight_t", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "ROOT", tmp_path / "HWAXPortal")
    monkeypatch.setattr(m, "HOME", tmp_path / "home")
    monkeypatch.setattr(m, "FETCH", False)
    m.RESULTS.clear()
    return m


def _lines(m, kind: str | None = None) -> list[str]:
    return [msg for k, msg in m.RESULTS if kind is None or k == kind]


# ── stash 가 치울 파일 ──────────────────────────────────────────────────────────────────────────
def test_설정이_가리키는_git_이_모르는_파일은_실패_이고_알려_준_제외를_따르면_사라진다(tmp_path, pf):
    repo = _repo(tmp_path, "HWAXPortal", {".gitignore": "backend/.env\nbackend/config/systems.local.yaml\n",
                                          "backend/config/systems.yaml": "systems: []\n"})
    (repo / "backend/.env").write_text("CATALOG_PATH=config/systems.cae00.yaml\nMCP_GATEWAY_URL=http://127.0.0.1:9110\n")
    (repo / "backend/config/systems.cae00.yaml").write_text("systems: []\n")
    (repo / "backend/config/systems.local.yaml").write_text("x: {}\n")      # 무시된 파일 — stash 가 안 건드린다
    (repo / "notes.txt").write_text("메모\n")
    pf._reset_repo("HWAXPortal", repo, ("backend/.env", "infra/.env"))
    bad = _lines(pf, "✗")
    assert len(bad) == 1 and "backend/config/systems.cae00.yaml" in bad[0], pf.RESULTS
    cmd = f"echo 'backend/config/systems.cae00.yaml' >> {repo}/.git/info/exclude"
    assert cmd in bad[0]
    warn = " ".join(_lines(pf, "⚠"))
    assert "notes.txt" in warn and "systems.cae00" not in warn, "가리키는 파일은 ✗ 줄에만"
    assert "systems.local.yaml" not in " ".join(_lines(pf)) and "backend/.env" not in " ".join(_lines(pf)), "무시된 파일은 치워지지 않는다"

    subprocess.run(["bash", "-c", cmd], check=True)          # 알려 준 대로 따른다
    pf.RESULTS.clear()
    pf._reset_repo("HWAXPortal", repo, ("backend/.env", "infra/.env"))
    assert not _lines(pf, "✗"), pf.RESULTS


def test_설정이_가리키는_폴더_안의_모르는_파일도_실패_이고_리포_밖_주소는_보지_않는다(tmp_path, pf):
    repo = _repo(tmp_path, "HEAXHub", {"README": "x\n"})
    (repo / ".env").write_text("HEAX_EXTRA_DIR=var/extra\nHWAX_DATA_ROOT=/data\nROOT=.\nSITE=http://a/b\n")
    (repo / "var/extra").mkdir(parents=True)
    (repo / "var/extra/apps.yaml").write_text("a: 1\n")
    pf._reset_repo("HEAXHub", repo, (".env",))
    bad = _lines(pf, "✗")
    assert len(bad) == 1 and "var/extra/apps.yaml" in bad[0], pf.RESULTS
    assert ".env" not in bad[0].split("—")[1].split("(")[1], ".env 자체(리포 루트 '.')는 가리킨 것으로 치지 않는다"


def test_reset_리포의_로컬_커밋은_버려진다고_실패(tmp_path, pf):
    repo = _repo(tmp_path, "MXWhitePaper", {"a.txt": "1\n"})
    (repo / "a.txt").write_text("2\n")
    _git(repo, "commit", "-qam", "local")
    pf._reset_repo("MXWhitePaper", repo, (".env",))
    assert any("origin 에 없는 로컬 커밋 1개" in b and "reset --hard" in b for b in _lines(pf, "✗")), pf.RESULTS


def test_pull_리포는_들어올_변경과_겹치는_로컬_파일만_실패(tmp_path, pf, monkeypatch):
    repo = _repo(tmp_path, "HWAXAgentServer", {"a.py": "a = 1\n", "b.py": "b = 1\n"})
    other = tmp_path / "clone2"
    _git(tmp_path, "clone", "-q", str(tmp_path / "remotes/HWAXAgentServer.git"), str(other))
    (other / "a.py").write_text("a = 2\n")
    _git(other, "commit", "-qam", "upstream")
    _git(other, "push", "-q", "origin", "main")
    monkeypatch.setattr(pf, "FETCH", True)
    (repo / "b.py").write_text("b = 2\n")                    # 겹치지 않는 수정 — 그대로 남는다
    pf._pull_repo("HWAXAgentServer", repo)
    assert not _lines(pf, "✗") and any("겹치지 않아 그대로 남는다" in x for x in _lines(pf, "·")), pf.RESULTS
    pf.RESULTS.clear()
    (repo / "a.py").write_text("a = 3\n")                    # 들어올 변경과 겹친다 — pull --ff-only 가 막힌다
    pf._pull_repo("HWAXAgentServer", repo)
    assert any("겹치는 로컬 파일 1개" in b and "a.py" in b for b in _lines(pf, "✗")), pf.RESULTS


# ── 포털 카탈로그 ────────────────────────────────────────────────────────────────────────────────
def _portal(tmp_path: Path, catalog: str | None, cat_path: str = "config/systems.cae00.yaml") -> Path:
    root = tmp_path / "HWAXPortal"
    (root / "backend/config").mkdir(parents=True, exist_ok=True)
    (root / "backend/.env").write_text(f"CATALOG_PATH={cat_path}\n")
    if catalog is not None:
        (root / "backend" / cat_path).write_text(catalog)
    return root


def test_카탈로그_파일이_없으면_실패(tmp_path, pf):
    _portal(tmp_path, None)
    pf._portal()
    assert any("CATALOG_PATH 의 파일이 없다" in b for b in _lines(pf, "✗")), pf.RESULTS


def test_mx_백서_항목에_소속_싣기가_없으면_경고_이고_다음_항목의_값을_빌려_보지_않는다(tmp_path, pf):
    _portal(tmp_path, "systems:\n  - id: mx-white-paper\n    name: MX\n  - id: other\n    claims_affiliation: true\n")
    pf._portal()
    assert any("claims_affiliation: true 가 없다" in w for w in _lines(pf, "⚠")), pf.RESULTS
    pf.RESULTS.clear()
    _portal(tmp_path, "systems:\n  - id: mx-white-paper\n    name: MX\n    claims_affiliation: true\n  - id: other\n")
    pf._portal()
    assert not any("claims_affiliation" in x for x in _lines(pf)), pf.RESULTS


# ── MX 백서 위임 비밀 ────────────────────────────────────────────────────────────────────────────
def _deleg(tmp_path: Path, gw: str, mx: str) -> Path:
    (tmp_path / "HWAXMcpGateway").mkdir(exist_ok=True)
    (tmp_path / "MXWhitePaper").mkdir(exist_ok=True)
    penv = tmp_path / "HWAXMcpGateway/provision.env"
    penv.write_text(gw)
    (tmp_path / "MXWhitePaper/.env").write_text(mx)
    return penv


def test_위임_비밀이_다르면_실패_이고_원문은_찍지_않는다(tmp_path, pf, capsys):
    penv = _deleg(tmp_path, 'PER_USER_SSO_APPS="mx-white-paper:MXWP"\nMXWP_SSO_SECRET=gw-secret-AAA\n', "MXWP_SSO_SECRET=mx-secret-BBB\n")
    pf._mxwp_delegation(penv)
    out = capsys.readouterr().out + " ".join(_lines(pf))
    assert any("두 곳에서 다르다" in b and "≠" in b for b in _lines(pf, "✗")), pf.RESULTS
    assert "gw-secret-AAA" not in out and "mx-secret-BBB" not in out


def test_위임_비밀이_같으면_주소_plat_싣기를_본다(tmp_path, pf):
    penv = _deleg(tmp_path, 'PER_USER_SSO_APPS="mx-white-paper:MXWP"\nMXWP_SSO_SECRET=s\n', "MXWP_SSO_SECRET=s\n")
    pf._mxwp_delegation(penv)
    assert any("같다" in x for x in _lines(pf, "✓"))
    assert any("MXWP_SSO_URL 이 없다" in b for b in _lines(pf, "✗")) and any("MXWP_SEND_PLAT" in w for w in _lines(pf, "⚠")), pf.RESULTS


# ── 창 상한 ──────────────────────────────────────────────────────────────────────────────────────
def test_창_상한이_서버_창보다_작으면_경고(tmp_path, pf, monkeypatch):
    aenv = tmp_path / "agent.env"
    aenv.write_text("LLM_CONTEXT_TOKENS=200000\nVLLM_BASE_URL=http://llm.example/v1\nVLLM_MODEL=glm\n")
    monkeypatch.setattr(pf, "get_json", lambda url, **k: (200, {"context": {"server": 1048576, "source": "env", "tokens": 200000}}))
    pf._context_cap(aenv)
    assert any("200000" in w and "1048576" in w for w in _lines(pf, "⚠")), pf.RESULTS


def test_에이전트가_서버_창을_모르면_에이전트와_같은_길로_묻는다(tmp_path, pf, monkeypatch):
    aenv = tmp_path / "agent.env"
    aenv.write_text("LLM_CONTEXT_TOKENS=200000\nVLLM_BASE_URL=http://llm.example/v1/\nVLLM_API_KEY=k\nVLLM_MODEL=glm\n")
    asked = []

    def fake(url, **k):
        asked.append((url, k.get("headers"), k.get("loopback", True)))
        if url.endswith("/health"):
            return 200, {"context_tokens": 128000}                  # 옛 엔진 — context 칸이 없다
        return 200, {"data": [{"id": "other", "max_model_len": 4096}, {"id": "glm", "max_model_len": 300000}]}
    monkeypatch.setattr(pf, "get_json", fake)
    pf._context_cap(aenv)
    assert any("200000" in w and "300000" in w for w in _lines(pf, "⚠")), pf.RESULTS
    models = [a for a in asked if a[0].endswith("/models")]
    assert models and models[0][0] == "http://llm.example/v1/models" and models[0][1] == {"Authorization": "Bearer k"} and models[0][2] is False


# ── 허브 Drive 대조 목록 ─────────────────────────────────────────────────────────────────────────
def _hub_drive(tmp_path: Path, monkeypatch, sums: str, hashes: str) -> None:
    (tmp_path / "HWAXPortal/infra").mkdir(parents=True, exist_ok=True)
    (tmp_path / "HEAXHub").mkdir(exist_ok=True)
    (tmp_path / "HEAXHub/.env").write_text("HEAX_DRIVE_REMOTE=fake:HEAX/dist\n")
    stub = tmp_path / "stub"
    stub.mkdir(exist_ok=True)
    (stub / "sums").write_text(sums)
    (stub / "hashes").write_text(hashes)
    rc = stub / "rclone"
    rc.write_text(f'#!/usr/bin/env bash\ncase "$*" in\n'
                  f'  "cat fake:HEAX/dist/latest/SHA256SUMS") cat "{stub}/sums" ;;\n'
                  f'  "hashsum sha256 fake:HEAX/dist/latest/") cat "{stub}/hashes" ;;\n'
                  f'  *) exit 1 ;;\nesac\n')
    rc.chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub}:{os.environ['PATH']}")


def test_허브_대조_목록이_latest_와_맞으면_통과_다르거나_없으면_실패(tmp_path, pf, monkeypatch):
    _hub_drive(tmp_path, monkeypatch, "aa  ./a.sif\nbb  ./b.sif\n", "aa  a.sif\nbb  b.sif\ncc  loose.sif\n")
    pf.check_drive()
    assert any("2줄이 latest/ 와 맞는다" in x for x in _lines(pf, "✓")) and not _lines(pf, "✗"), pf.RESULTS
    assert any("대조 목록 밖" in x for x in _lines(pf, "·")), "목록 밖 SIF 는 정보로 알린다"
    pf.RESULTS.clear()
    _hub_drive(tmp_path, monkeypatch, "aa  ./a.sif\nbb  ./b.sif\nzz  ./gone.sif\n", "aa  a.sif\nXX  b.sif\n")
    pf.check_drive()
    bad = _lines(pf, "✗")
    assert len(bad) == 1 and "없음 1 · 다름 1" in bad[0] and "checksum failed" in bad[0], pf.RESULTS


# ── 원격 판을 표준입력으로 ───────────────────────────────────────────────────────────────────────
def _bin(tmp_path: Path) -> Path:
    """git · bash 만 있는 PATH — apptainer · rclone 이 없어 실 인스턴스 · 실 Drive 에 닿지 않는다."""
    b = tmp_path / "bin"
    b.mkdir()
    for tool in ("git", "bash"):
        os.symlink(subprocess.run(["bash", "-c", f"command -v {tool}"], capture_output=True, text=True).stdout.strip(), b / tool)
    return b


def test_표준입력으로_돌리면_지금_자리를_포털_리포_루트로_쓴다(tmp_path):
    root = tmp_path / "box" / "HWAXPortal"
    (root / "infra/scripts").mkdir(parents=True)
    (root / "infra/scripts/update-all.sh").write_text("#!/usr/bin/env bash\n")
    env = {"PATH": str(_bin(tmp_path)), "HOME": str(tmp_path / "home"),
           "HWAX_PREFLIGHT_AGENT": "http://127.0.0.1:9", "HWAX_PREFLIGHT_MXWP": "http://127.0.0.1:9"}
    r = subprocess.run([sys.executable, "-", "--no-fetch"], input=SCRIPT.read_text(encoding="utf-8"), cwd=root,
                       capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode in (0, 1) and "Traceback" not in r.stderr, r.stderr
    assert r.stdout.splitlines()[0] == f"update-all 사전 점검 — {root} (원격 안 묻기)"
    assert "요약 — ✗" in r.stdout
    r = subprocess.run([sys.executable, "-"], input=SCRIPT.read_text(encoding="utf-8"), cwd=tmp_path,
                       capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode != 0 and "포털 리포 루트에서 돌린다" in r.stderr
