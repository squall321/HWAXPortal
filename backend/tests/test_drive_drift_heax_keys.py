# drive-drift.sh 의 허브 캐시 열쇠 대조 — cae00 허브가 받은 SIF 를 그대로 띄울지(열쇠가 맞나)를 가짜 허브 · 가짜 앱 리포 · 가짜 rclone 으로 본다
"""왜 — 10-25 에 크기 대조만으로는 못 잡는 전달 실패를 찾았다. cae00 허브는 앱 소스를 매니페스트의 source.ref 에서 받고, 커밋이
바뀌면 sha256(커밋 + 매니페스트 + 틀)을 받은 SIF 의 .sif.hash 와 견준다. 다르면 다시 지으려다(그 박스는 못 짓는다) 실패해 그 회차엔
앱을 띄우지 않는다. StepForge 는 문서 커밋 뒤 SIF 를 다시 안 올렸고, MaterialTwinWeb 은 GitHub 이 61커밋 뒤였다.

  · 열쇠가 갈래 끝과 맞으면 말이 없다(✓ 일치).
  · dev 는 끝 커밋으로 다시 지었는데 Drive 가 옛 판이면 ✗ — 올린다.
  · 커밋은 그대로고 매니페스트 · 틀만 바뀌었으면 한 줄 정보(·) — cae00 은 다시 재지 않는다.
  · GitHub 이 지은 커밋보다 뒤(push 안 함)면 ⚠.
  · 갈래 끝이 지은 커밋보다 앞(새 커밋을 안 지음)이면 ✗ — 다시 짓고 올린다.
계산식은 HEAXHub integration_sif_builder._hash_inputs 와 같다(10-25 dev 의 step_forge · voice-recorder 열쇠를 그대로 재현해 확인).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DRIFT = ROOT / "infra/scripts/drive-drift.sh"
_GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
TPL = b"Bootstrap: docker\nFrom: python:3.12-slim\n"


def _git(cwd: Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, env={**os.environ, **_GIT})
    assert r.returncode == 0, (a, r.stderr)
    return r.stdout.strip()


def _key(commit: str, man: dict, tpl: bytes = TPL) -> str:
    x = hashlib.sha256()
    x.update(commit.encode()); x.update(b"\0")
    x.update(json.dumps(man, sort_keys=True, default=str).encode()); x.update(b"\0"); x.update(tpl)
    return x.hexdigest()


class Box:
    """tmp/HWAXPortal(drive-drift) · tmp/HEAXHub(등록 사본 · 틀 · var/sifs · 받은 소스) · tmp/src/<앱>(작업) → tmp/src/<앱>.git(GitHub 자리) · tmp/drive(Drive latest/ 의 .sif.hash)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        portal = tmp / "HWAXPortal"
        (portal / "infra/scripts").mkdir(parents=True)
        shutil.copy(DRIFT, portal / "infra/scripts/drive-drift.sh")
        (portal / "backend/.venv/bin").mkdir(parents=True)
        os.symlink(sys.executable, portal / "backend/.venv/bin/python")
        self.hub = tmp / "HEAXHub"
        (self.hub / "backend/app/services/sif_templates").mkdir(parents=True)
        (self.hub / "backend/app/services/sif_templates/fastapi.def").write_bytes(TPL)
        (self.hub / "var/sifs").mkdir(parents=True)
        (self.hub / ".env").write_text("HEAX_DRIVE_REMOTE=fake:HEAX/dist\n")
        self.drive = tmp / "drive"
        self.drive.mkdir()
        stub = tmp / "stub"
        stub.mkdir()
        rc = stub / "rclone"
        rc.write_text(f'#!/usr/bin/env bash\ncase "$1" in\n  copy) cp "{self.drive}"/*.sif.hash "$3"/ 2>/dev/null; exit 0 ;;\nesac\nexit 0\n')
        rc.chmod(0o755)
        self.env = {**os.environ, **_GIT, "PATH": f"{stub}:{os.environ['PATH']}", "HOME": str(tmp)}
        self.portal = portal

    def app(self, d: str) -> tuple[Path, Path, dict]:
        """앱 리포 하나 — 첫 커밋을 GitHub 자리(bare)에 올리고 등록 사본은 그 주소의 main 을 가리킨다."""
        bare, work = self.tmp / "src" / f"{d}.git", self.tmp / "src" / d
        bare.mkdir(parents=True)
        _git(bare, "init", "--bare", "-q", "-b", "main")
        work.mkdir(parents=True)
        _git(work, "init", "-q", "-b", "main")
        (work / "app.py").write_text("v = 1\n")
        _git(work, "add", "-A"); _git(work, "commit", "-qm", "one")
        _git(work, "remote", "add", "origin", str(bare)); _git(work, "push", "-q", "origin", "main")
        man = {"name": d, "status": "beta", "build": {"stack": "fastapi"}, "source": {"type": "git", "url": str(bare), "ref": "main"}}
        self.manifest(d, man)
        return work, bare, man

    def manifest(self, d: str, man: dict) -> None:
        p = self.hub / "integrations" / d / ".portal/manifest.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(man, allow_unicode=True))

    def commit(self, work: Path, push: bool = True) -> str:
        (work / "app.py").write_text((work / "app.py").read_text() + "v += 1\n")
        _git(work, "commit", "-qam", "more")
        if push:
            _git(work, "push", "-q", "origin", "main")
        return _git(work, "rev-parse", "HEAD")

    def built(self, d: str, commit: str, local_key: str, drive_key: str, work: Path | None = None) -> None:
        """dev 가 지은 판(.def 의 upstream commit · var/sifs 의 열쇠)과 Drive 의 열쇠. work 를 주면 허브가 받은 소스 자리를 그것의 사본으로."""
        (self.hub / "var/sifs" / f"{d}.sif.hash").write_text(local_key + "\n")
        (self.hub / "var/sifs" / f"{d}.def").write_text(f"%labels\n    upstream commit: {commit}\n")
        (self.drive / f"{d}.sif.hash").write_text(drive_key + "\n")
        if work is not None:
            ws = self.hub / "var/integration_workspaces" / d / "upstream"
            ws.parent.mkdir(parents=True, exist_ok=True)
            _git(self.tmp, "clone", "-q", str(work), str(ws))

    def run(self) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(self.portal / "infra/scripts/drive-drift.sh"), "heax"],
                              capture_output=True, text=True, env=self.env, timeout=120)


def test_열쇠가_갈래_끝과_맞으면_말이_없다(tmp_path):
    b = Box(tmp_path)
    work, _, man = b.app("ok")
    head = _git(work, "rev-parse", "HEAD")
    b.built("ok", head, _key(head, man), _key(head, man))
    out = b.run()
    assert out.returncode == 0 and "✓ 일치" in out.stdout and " ok " not in out.stdout, out.stdout + out.stderr


def test_dev_는_새로_지었는데_Drive_가_옛_판이면_올리라고_한다(tmp_path):
    b = Box(tmp_path)
    work, _, man = b.app("sf")
    old = _git(work, "rev-parse", "HEAD")
    head = b.commit(work)                                    # 문서 커밋 하나 — 그 뒤 dev 는 다시 지었고 Drive 는 그대로(StepForge 10-24)
    b.built("sf", head, _key(head, man), _key(old, man))
    out = b.run()
    assert out.returncode == 1 and "✗ sf — dev 는 main 끝" in out.stdout and "SLUG=sf" in out.stdout, out.stdout + out.stderr


def test_매니페스트_틀만_바뀌었으면_한_줄_정보다(tmp_path):
    b = Box(tmp_path)
    work, _, man = b.app("demo")
    head = _git(work, "rev-parse", "HEAD")
    b.built("demo", head, _key(head, man), _key(head, man))
    b.manifest("demo", {**man, "description": "새 설명"})   # 등록 사본만 고쳤다 — 커밋은 그대로
    out = b.run()
    assert out.returncode == 0 and "· 매니페스트 · 틀만 바뀐 앱 1(demo)" in out.stdout and "✗" not in out.stdout, out.stdout + out.stderr


def test_GitHub_이_지은_커밋보다_뒤면_push_하라고_알린다(tmp_path):
    b = Box(tmp_path)
    work, _, man = b.app("mt")
    local = b.commit(work, push=False)                       # 로컬에만 있는 커밋으로 지었다(MaterialTwinWeb 10-25)
    b.built("mt", local, _key(local, man), _key(local, man), work=work)
    out = b.run()
    assert out.returncode == 0 and "⚠ mt — Drive SIF 는" in out.stdout and "push 안 한 커밋" in out.stdout, out.stdout + out.stderr


def test_갈래_끝이_지은_커밋보다_앞이면_다시_짓고_올리라고_한다(tmp_path):
    b = Box(tmp_path)
    work, _, man = b.app("vr")
    built = _git(work, "rev-parse", "HEAD")
    b.commit(work)                                           # 새 커밋이 올라갔는데 dev 도 Drive 도 옛 판
    b.built("vr", built, _key(built, man), _key(built, man), work=work)
    out = b.run()
    assert out.returncode == 1 and "✗ vr — Drive SIF 는" in out.stdout and "redeploy-app.sh --rebuild vr" in out.stdout, out.stdout + out.stderr
