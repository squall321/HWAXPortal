# set -e·pipefail 아래서 '정상인 0 아닌 값' 이 스크립트를 말없이 끝내던 자리들(docs/update-all-skip-unchanged D-14)
#
# 셈(가짜 apptainer·rclone)은 절대경로로만 부르고, 목록을 **두 번에 나눠** 써서 앞 조각에서 읽는 쪽이 파이프를 닫으면
# 뒤 조각이 SIGPIPE 를 받게 만든다 — 경합을 기다리지 않고 늘 재현된다.
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON = (ROOT / "infra/scripts/_common.sh").read_text(encoding="utf-8")
STE = (ROOT / "infra/scripts/deploy-ste.sh").read_text(encoding="utf-8")


def _fn(src: str, name: str, indent: str = "") -> str:
    i = src.index(f"{indent}{name}() {{")
    return src[i:src.index(f"\n{indent}}}\n", i) + len(indent) + 3]


def _bash(script: str, tmp_path, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", "set -euo pipefail\n" + script], capture_output=True, text=True, timeout=60,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), **env})


def _two_chunk_shim(tmp_path, name: str, first: str, rest_bytes: int = 300_000) -> Path:
    """첫 조각(줄 단위 — 진짜 출력처럼 줄바꿈으로 끝난다)을 쓰고 잠깐 쉰 뒤 큰 두 번째 조각을 쓴다 — 읽는 쪽이 첫 줄에서
    닫으면 SIGPIPE. 줄바꿈이 없으면 grep 이 줄을 다 읽을 때까지 안 닫아 재현이 안 된다(처음에 그렇게 짜서 대조군이 틀렸다)."""
    shim = tmp_path / name
    shim.write_text("#!/usr/bin/env bash\n"
                    f"printf '%s\\n' '{first}'\n"
                    "sleep 0.3\n"
                    f"head -c {rest_bytes} /dev/zero | tr '\\0' ' '\n"
                    "printf '\\n'\n")
    shim.chmod(0o755)
    return shim


def test_떠_있는_인스턴스를_없다고_읽지_않는다(tmp_path):
    """`instance list | grep -q` 는 grep 이 먼저 닫으면 apptainer 가 141 로 죽어 '없다' 가 됐다 — start.sh 가 떠 있는 포털을
    다시 띄우려다 set -e 로 죽어 nginx 가 안 떴고, stop.sh 는 멈추지 않았다."""
    shim = _two_chunk_shim(tmp_path, "apptainer", '{"instances": [{"instance": "hwax_portal", "pid": 1},')
    r = _bash(_fn(COMMON, "instance_running") +
              'if instance_running hwax_portal; then echo RUNNING; else echo ABSENT; fi\n'
              'if instance_running hwax_nginx; then echo RUNNING2; else echo ABSENT2; fi\n',
              tmp_path, APPTAINER=str(shim))
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["RUNNING", "ABSENT2"], r.stdout


def test_옛_모양은_실제로_그렇게_틀렸다(tmp_path):
    """위 시험이 셈 탓에 그냥 통과하는 게 아님을 보인다 — 파이프로 읽는 옛 모양은 같은 셈에서 '없다' 로 읽는다."""
    shim = _two_chunk_shim(tmp_path, "apptainer", '{"instances": [{"instance": "hwax_portal", "pid": 1},')
    old = ('instance_running() {\n  "$APPTAINER" instance list --json 2>/dev/null \\\n'
           '    | grep -q "\\"instance\\": *\\"$1\\"" || return 1\n}\n')
    r = _bash(old + 'if instance_running hwax_portal; then echo RUNNING; else echo ABSENT; fi\n', tmp_path, APPTAINER=str(shim))
    assert r.stdout.strip() == "ABSENT", (r.stdout, r.stderr)


def test_ste_배포_지문은_없는_트리에서_말없이_죽지_않는다(tmp_path):
    """frontend/dist 는 gitignore 라 새 클론에 없다 — cd 실패가 pipefail 로 대입까지 번져 set -e 가 출력 0줄로 끝냈다."""
    repo = tmp_path / "ste"
    for d in ("backend/src", "backend/mcp_server", "apps"):
        (repo / d).mkdir(parents=True)
        (repo / d / "a.txt").write_text(d)
    line = next(ln for ln in STE.splitlines() if ln.strip().startswith('_lman="$(for d in'))
    r = _bash(_fn(STE, "_man", "    ") + line + '\necho "LMAN=[$_lman]"\n', tmp_path, STE_REPO=str(repo))
    assert r.returncode == 0, (r.stdout, r.stderr)
    words = re.search(r"LMAN=\[(.*)\]", r.stdout).group(1).split()
    assert len(words) == 4 and words[-1] == "-", words


def test_ste_부트스트랩은_리모트_목록을_끝까지_읽는다(tmp_path):
    """`listremotes | head -1` 은 head 가 먼저 닫으면 rclone 이 SIGPIPE 를 받아 set -e 로 말없이 끝났다."""
    i = STE.index('  REMOTE="${STE_DRIVE_REMOTE:-}"')
    block = STE[i:STE.index('  [ -n "$REMOTE" ] || die', i)]
    for first, want in (("gdrive:", "gdrive:"), ("ApptainerImages:", "ApptainerImages:")):
        shim = _two_chunk_shim(tmp_path, "rclone", first)
        r = _bash(f'RCLONE="{shim}"\n' + block + 'echo "REMOTE=[$REMOTE]"\n', tmp_path)
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert f"REMOTE=[{want}]" in r.stdout, r.stdout
