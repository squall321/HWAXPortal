# drive-drift.sh 의 허브 '지어지지 않은 앱' 검사 — SIF 가 있어야 하는 앱인데 var/sifs 에 없으면 ✗ 다(가짜 허브 · 가짜 rclone)
"""왜 — 허브 dist-to-drive 는 var/sifs/*.sif 글롭으로 앱 SIF 를 싣는다. 한 번도 지어지지 않은 앱은 글롭에 걸리지 않아 Drive 에 없는 채 말이 없고,
drive-drift 의 크기 대조도 var/sifs 에 **있는** SIF 만 본다. cae00 허브는 앱을 짓지 못해(빌드 박스가 아니다) 그 앱을 띄우지 않는다
(docs/cluster-deploy 체크리스트 88 — '글롭은 빌드된 것만 올려 새 앱이 무언 탈락한다', 10-31 B1).

  · launch.mode 가 service · job_runner 인데 var/sifs/<폴더>.sif 가 없으면 ✗ 한 줄 · 종료코드 1.
  · proxy · iframe · url · static 은 '○ SIF 대상 아님 N개' 한 줄 — 지을 SIF 가 없다.
  · 박스 덮어쓰기(manifest.local.yaml)가 있는 앱은 ✗ 가 아니라 ○ — 크기 대조와 같은 판정(dist-to-drive 가 기본으로 싣지 않는다).
  · 앱 목록과 매니페스트는 cae00 이 받을 판(@{u})으로 읽는다 — 받지 않은 앱도 보고, 올리지 않은 앱은 보지 않는다.
  · 다 지어졌으면 새 ✗ 가 없다.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"
_GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
STACK = {"service": "fastapi", "job_runner": "python_cli", "proxy": "external_proxy", "iframe": "external_iframe",
         "url": "external_link", "static": "static_html"}


def _git(cwd: Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, env={**os.environ, **_GIT})
    assert r.returncode == 0, (a, r.stderr)
    return r.stdout.strip()


class Hub:
    """tmp/HWAXPortal(drive-drift) · tmp/HEAXHub(integrations · var/sifs) · PATH 앞의 가짜 rclone(Drive latest/ 의 크기 목록만 답한다)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        portal = tmp / "HWAXPortal"
        (portal / "infra/scripts").mkdir(parents=True)
        shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
        (portal / "backend/.venv/bin").mkdir(parents=True)
        os.symlink(sys.executable, portal / "backend/.venv/bin/python")
        self.portal = portal
        self.hub = tmp / "HEAXHub"
        (self.hub / "var/sifs").mkdir(parents=True)
        (self.hub / ".env").write_text("HEAX_DRIVE_REMOTE=fake:HEAX/dist\n")
        self.lsl = tmp / "drive-lsl"
        self.lsl.write_text("")
        stub = tmp / "stub"
        stub.mkdir()
        rc = stub / "rclone"
        rc.write_text(f'#!/usr/bin/env bash\ncase "$1" in\n  lsl) case "$2" in */dist/latest/) cat "{self.lsl}" ;; esac; exit 0 ;;\nesac\nexit 0\n')
        rc.chmod(0o755)
        self.env = {**os.environ, **_GIT, "PATH": f"{stub}:{os.environ['PATH']}", "HOME": str(tmp)}

    def app(self, d: str, mode: str | None, *, built: bool = False) -> None:
        """등록 사본 하나(launch.mode = mode, None 이면 launch 칸이 없다). built 면 var/sifs 의 SIF 와 Drive 의 같은 크기 사본도."""
        man: dict = {"name": d, "status": "beta", "build": {"stack": STACK.get(mode or "", "fastapi")}}
        if mode is not None:
            man["launch"] = {"mode": mode}
        p = self.hub / "integrations" / d / ".portal/manifest.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(man, allow_unicode=True))
        if built:
            (self.hub / "var/sifs" / f"{d}.sif").write_bytes(b"s" * 5)
            with self.lsl.open("a", encoding="utf-8") as fh:
                fh.write(f"{5:>12} 2026-10-31 07:00:00.000000000 {d}.sif\n")

    def local_override(self, d: str, kind: str = "file") -> None:
        lo = self.hub / "integrations" / d / ".portal/manifest.local.yaml"
        lo.parent.mkdir(parents=True, exist_ok=True)
        if kind == "dangling":
            os.symlink(self.tmp / "gone.yaml", lo)
        else:
            lo.write_text("resources: {memory_gb: 16}\n", encoding="utf-8")

    def publish(self) -> None:
        """허브를 git 리포로 — 지금의 integrations/ 를 올리고(GitHub 자리 bare) 그 갈래를 @{u} 로 둔다(cae00 이 받는 판)."""
        bare = self.tmp / "hub.git"
        bare.mkdir()
        _git(bare, "init", "--bare", "-q", "-b", "main")
        _git(self.hub, "init", "-q", "-b", "main")
        (self.hub / ".gitignore").write_text("var/\n.env\n")
        _git(self.hub, "add", "-A")
        _git(self.hub, "commit", "-qm", "apps")
        _git(self.hub, "remote", "add", "origin", str(bare))
        _git(self.hub, "push", "-q", "-u", "origin", "main")

    def run(self) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(self.portal / "infra/scripts/drive-drift.sh"), "heax"],
                              capture_output=True, text=True, env=self.env, timeout=120)


def _x_lines(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.lstrip().startswith("✗")]


@pytest.mark.parametrize("mode", ["service", "job_runner"])
def test_SIF_가_있어야_하는_앱이_지어지지_않았으면_X_한_줄이고_드리프트다(tmp_path, mode):
    """**이 시험이 이 검사의 이유다** — 크기 대조는 var/sifs 에 있는 SIF 만 본다. 없는 앱은 종전엔 '✓ 일치' · 0 이었다."""
    h = Hub(tmp_path)
    h.app("ok", "service", built=True)
    h.app("new", mode)
    out = h.run()
    x = _x_lines(out.stdout)
    assert out.returncode == 1 and len(x) == 1, out.stdout + out.stderr
    assert f"✗ new — launch.mode {mode} 인데 var/sifs/new.sif 가 없다" in x[0] and "redeploy-app.sh new --rebuild" in x[0], x
    assert "✓ 일치" not in out.stdout and "→ 올려야 한다" in out.stdout


def test_proxy_iframe_url_static_은_대상_아님_한_줄로_센다(tmp_path):
    h = Hub(tmp_path)
    for d, mode in (("dynaforge", "proxy"), ("dash", "iframe"), ("link", "url"), ("docs", "static")):
        h.app(d, mode)
    h.app("ok", "service", built=True)
    out = h.run()
    assert out.returncode == 0 and "✓ 일치" in out.stdout and not _x_lines(out.stdout), out.stdout + out.stderr
    line = next(ln for ln in out.stdout.splitlines() if "SIF 대상 아님" in ln)
    assert line.lstrip().startswith("○ SIF 대상 아님 4개") and "dynaforge(proxy)" in line and "docs(static)" in line, line


def test_다_지어졌으면_새_X_가_없다(tmp_path):
    h = Hub(tmp_path)
    for d, mode in (("a", "service"), ("b", "job_runner")):
        h.app(d, mode, built=True)
    h.app("p", "proxy")
    out = h.run()
    assert out.returncode == 0 and "✓ 일치" in out.stdout and not _x_lines(out.stdout), out.stdout + out.stderr


@pytest.mark.parametrize("kind", ["file", "dangling"], ids=["파일", "끊긴_심링크"])
def test_덮어쓴_앱은_SIF_가_없어도_예상된_것이다(tmp_path, kind):
    """박스 덮어쓰기가 있는 앱은 dist-to-drive 가 기본으로 싣지 않는다(HEAXHub d4a6fe6) — 크기 대조의 ○ 와 같은 판정이다."""
    h = Hub(tmp_path)
    h.app("sf", "service")
    h.local_override("sf", kind)
    out = h.run()
    assert out.returncode == 0 and "✓ 일치" in out.stdout and not _x_lines(out.stdout), out.stdout + out.stderr
    assert "○ sf — var/sifs/sf.sif 가 없다. 예상된 것이다" in out.stdout and "manifest.local.yaml" in out.stdout


def test_cae00_이_받을_판의_매니페스트로_가른다(tmp_path):
    """작업 트리만 바꾼 매니페스트로는 가르지 않는다 — cae00 은 올린 판을 받는다(아래 열쇠 대조의 show() 와 같다)."""
    h = Hub(tmp_path)
    h.app("svc", "service")           # 올린 판은 service — 지어야 한다
    h.app("px", "proxy")              # 올린 판은 proxy — 지을 것이 없다
    h.publish()
    h.app("svc", "proxy")             # 작업 트리만 바꿨다
    h.app("px", "service")
    out = h.run()
    x = _x_lines(out.stdout)
    assert out.returncode == 1 and len(x) == 1 and "✗ svc — launch.mode service" in x[0], out.stdout + out.stderr
    assert "px(proxy)" in out.stdout


def test_받지_않은_앱은_보고_올리지_않은_앱은_보지_않는다(tmp_path):
    """올린 판에만 있는 앱 — dev 허브가 아직 못 봐 SIF 가 없는데 cae00 은 그 매니페스트를 받는다. 작업 트리에만 있는 앱은 cae00 에 가지 않는다."""
    h = Hub(tmp_path)
    h.app("ok", "service", built=True)
    h.app("later", "service")
    h.publish()
    shutil.rmtree(h.hub / "integrations/later")                  # dev 작업 트리에서는 아직 없다(받지 않았다)
    h.app("draft", "service")                                    # 올리지 않은 새 앱
    out = h.run()
    x = _x_lines(out.stdout)
    assert out.returncode == 1 and len(x) == 1, out.stdout + out.stderr
    assert "✗ later — " in x[0] and "git pull" in x[0], x
    assert "draft" not in out.stdout


def test_launch_mode_를_못_읽으면_판정하지_않았다고_말한다(tmp_path):
    h = Hub(tmp_path)
    h.app("odd", None)
    out = h.run()
    assert out.returncode == 0 and not _x_lines(out.stdout), out.stdout + out.stderr
    assert "? launch.mode 를 못 읽은 앱 1개(odd) — 지어졌는지 보지 않았다" in out.stdout


def test_X_줄은_파이프가_아니라_받은_글에서_센다():
    """판정 파이프 함정(docs/gotchas) — `printf | grep -q` 는 pipefail 아래서 SIGPIPE 로 드리프트를 놓친다. 이 구획도 받은 글을 case 로 본다."""
    src = DRIFT.read_text(encoding="utf-8")
    i = src.index('_unbuilt="$(')
    block = src[i:src.index("# 캐시 열쇠", i)]
    assert 'case $\'\\n\'"$_unbuilt" in *$\'\\n✗\'*) DRIFT=1; h=1' in block
    assert "grep -q" not in block
