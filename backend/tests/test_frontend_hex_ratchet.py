# tokens.css 밖 고유 hex 색의 래칫 — 늘면 pnpm build 가 실패하고, 줄면 기준을 낮추라고 알린다(docs/ui-refresh 단계 3 · D-25)
"""빌드(`pnpm build`)가 scripts/check-hex.mjs 를 먼저 부른다. 백엔드 시험만 도는 자리에서도 잡히게 여기서 한 번 더 부르고, 래칫이
정말로 막는지(사본에 새 #rrggbb 하나) · tokens.css 는 세지 않는지 · 기준은 내리기만 하는지를 본다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FE = Path(__file__).resolve().parents[2] / "frontend"
NEW = "#a1b2c3"   # 기준에 없는 색 — 이 시험이 쓰는 값이라 진짜 화면에 생기면 아래 첫 단언이 알린다

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")


def _copy(tmp_path: Path) -> Path:
    """프론트 사본 — 빌드 전체가 돌 수 있게 설정 파일까지(의존성 · 산출물 · 캡처는 빼고)."""
    fe = tmp_path / "frontend"
    shutil.copytree(FE, fe, ignore=shutil.ignore_patterns("node_modules", "dist", ".shots", ".results", "*.tsbuildinfo"))
    return fe


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["node", "scripts/check-hex.mjs", *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def test_지금_트리는_기준을_넘지_않는다():
    base = json.loads((FE / "scripts" / "hex-baseline.json").read_text("utf-8"))
    assert NEW not in base["values"], "시험용 색이 기준에 들어갔다 — NEW 를 기준에 없는 값으로 바꾼다"
    r = _run(FE)
    assert r.returncode == 0, r.stdout + r.stderr


def test_빌드가_타입_검사_전에_래칫을_부른다():
    build = json.loads((FE / "package.json").read_text("utf-8"))["scripts"]["build"]
    steps = [s.strip() for s in build.split("&&")]
    assert "node scripts/check-hex.mjs" in steps and steps.index("node scripts/check-hex.mjs") < steps.index("tsc -b"), build


def test_새_hex_하나가_든_사본에서_래칫이_막고_어디인지_말한다(tmp_path):
    fe = _copy(tmp_path)
    css = fe / "src" / "styles" / "chatpage.css"
    css.write_text(css.read_text("utf-8") + f"\n.zz-probe {{ color: {NEW.upper()}; }}\n", encoding="utf-8")
    r = _run(fe)
    assert r.returncode == 1, r.stdout + r.stderr
    assert NEW in r.stderr and "styles/chatpage.css:" in r.stderr, r.stderr


@pytest.mark.skipif(shutil.which("pnpm") is None or not (FE / "node_modules").exists(), reason="pnpm 또는 node_modules 가 없다")
def test_새_hex_하나가_든_사본에서_pnpm_build_가_실패한다(tmp_path):
    """받아들임 그대로 — 빌드 명령 전체가 실패해야 한다(래칫이 앞에서 끊으므로 타입 검사 · 번들까지 가지 않는다)."""
    fe = _copy(tmp_path)
    (fe / "node_modules").symlink_to(FE / "node_modules")
    ts = fe / "src" / "components" / "chat" / "personaColor.ts"
    ts.write_text(ts.read_text("utf-8") + f"\nexport const zzProbe = '{NEW}';\n", encoding="utf-8")
    r = subprocess.run(["pnpm", "run", "-s", "build"], cwd=fe, capture_output=True, text=True, timeout=300)
    assert r.returncode != 0 and NEW in r.stderr, r.stdout + r.stderr
    assert not (fe / "dist").exists(), "래칫에서 끊겨야 한다 — 번들이 만들어졌다"


def test_tokens_css_의_hex_는_세지_않는다(tmp_path):
    fe = _copy(tmp_path)
    tokens = fe / "src" / "styles" / "tokens.css"
    tokens.write_text(tokens.read_text("utf-8") + f"\n:root {{ --zz-probe: {NEW}; }}\n", encoding="utf-8")
    r = _run(fe)
    assert r.returncode == 0, r.stdout + r.stderr


def test_줄면_낮추라고_알리고_update_는_내리기만_한다(tmp_path):
    fe = _copy(tmp_path)
    path = fe / "scripts" / "hex-baseline.json"
    base = json.loads(path.read_text("utf-8"))
    path.write_text(json.dumps({**base, "unique": base["unique"] + 3}), encoding="utf-8")
    r = _run(fe)
    assert r.returncode == 0 and "--update" in r.stdout, r.stdout + r.stderr
    r = _run(fe, "--update")
    assert r.returncode == 0 and json.loads(path.read_text("utf-8"))["unique"] == base["unique"], r.stdout + r.stderr
    # 늘어난 상태에서 --update 는 기준을 올리지 않는다 — 실패로 끝나고 기준 파일은 그대로다
    css = fe / "src" / "styles" / "chatpage.css"
    css.write_text(css.read_text("utf-8") + f"\n.zz-probe {{ color: {NEW}; }}\n", encoding="utf-8")
    before = path.read_text("utf-8")
    r = _run(fe, "--update")
    assert r.returncode == 1 and path.read_text("utf-8") == before, r.stdout + r.stderr
