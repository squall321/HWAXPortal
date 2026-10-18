# logrotate (C) 묶음 — 쥔 프로세스가 모두 O_APPEND 일 때만 copytruncate 한다(append-guard.sh, followups-1017 FU-D11 의 뒤)
"""왜 — copytruncate 는 O_APPEND 로 연 쓰기자에만 안전하다. 아니면 truncate 뒤 다음 write 가 옛 오프셋으로 가서 파일 앞이 NUL 구멍이
된다. 기동 스크립트는 10-17 에 `>>` · "ab" 로 고쳤지만 박스마다 그 전에 뜬 프로세스가 옛 fd 를 쥐고 남아 있을 수 있어(dev 10-18 실측 —
옛 감시가 `>` 로 띄운 허브 백엔드) 그 로그들을 회전에서 빼 두고 있었다. 이제 회전 직전에 쥔 프로세스를 보고 아니면 그 로그만 건너뛴다.

진짜 logrotate 를 임시 파일 · 임시 상태 파일로 돌린다. 쥐는 프로세스는 이 시험이 띄운 것만이고 끝나면 그 pid 만 내린다.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "infra/logrotate/append-guard.sh"
TMPL = (ROOT / "infra/logrotate/hwax.conf.tmpl").read_text(encoding="utf-8")


def _hold(path: Path, mode: str) -> subprocess.Popen:
    """path 를 mode('a' | 'w')로 열고 쥔 채 기다리는 프로세스 — 열 때까지 기다려 돌려준다."""
    p = subprocess.Popen([sys.executable, "-c", f"f=open({str(path)!r}, {mode!r}); import time; time.sleep(60)"])
    for _ in range(100):
        fds = Path(f"/proc/{p.pid}/fd")
        try:
            if any(str(path) == str(x.readlink()) for x in fds.iterdir()):
                return p
        except (FileNotFoundError, PermissionError):
            pass
        time.sleep(0.05)
    p.kill()
    raise AssertionError("쥐는 프로세스가 파일을 열지 못했다")


def _guard(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(GUARD), str(path)], capture_output=True, text=True, timeout=30)


def test_가드는_O_APPEND_없이_쥔_프로세스가_있으면_거절한다(tmp_path):
    log = tmp_path / "svc [1].log"                  # find -lname 의 패턴 글자([ ])도 글자로 맞춘다
    log.write_text("앞 기록\n")
    assert _guard(log).returncode == 0, "아무도 안 쥐었으면 회전해도 안전하다"
    a = _hold(log, "a")
    try:
        assert _guard(log).returncode == 0, "O_APPEND 쓰기자만 — 허락"
        w = _hold(log, "r+")
        try:
            r = _guard(log)
            assert r.returncode == 1 and str(w.pid) in r.stderr and str(a.pid) not in r.stderr, r.stderr
        finally:
            w.kill(); w.wait()
    finally:
        a.kill(); a.wait()


@pytest.mark.skipif(not shutil.which("logrotate"), reason="logrotate 없음")
@pytest.mark.parametrize("mode, rotated", [("a", True), ("r+", False)])
def test_진짜_logrotate_가_가드를_따른다(tmp_path, mode, rotated):
    """nosharedscripts(기본)에서 prerotate 가 실패하면 그 로그는 copytruncate 하지 않는다 — 내용 그대로 · 회전본 없음."""
    log = tmp_path / "backend.log"
    log.write_text("x" * 4096 + "\n")
    conf = tmp_path / "lr.conf"
    conf.write_text(f"""{log}
{{
    daily
    rotate 2
    missingok
    copytruncate
    prerotate
        {GUARD} "$1"
    endscript
}}
""")
    h = _hold(log, mode)
    try:
        r = subprocess.run(["logrotate", "-f", "-s", str(tmp_path / "state"), str(conf)], capture_output=True, text=True, timeout=60)
    finally:
        h.kill(); h.wait()
    rest = sorted(x.name for x in tmp_path.iterdir() if x.name.startswith("backend.log."))
    if rotated:
        assert r.returncode == 0 and rest and log.stat().st_size == 0, (r.returncode, r.stderr, rest)
    else:
        assert not rest and log.stat().st_size == 4097, "가드가 막은 로그는 자르지도 옮기지도 않는다"
        assert "append-guard" in r.stderr, r.stderr


def _code(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def test_템플릿의_C_묶음():
    i = TMPL.index("# (C)")
    blk = TMPL[i:TMPL.index("# (B)", i)]
    for f in ("HEAXHub/var/logs/backend.log", "HEAXHub/var/logs/worker.log", "HEAXHub/var/logs/beat.log",
              "AIDataHub/deploy/apptainer/logs/uvicorn.log", "/tmp/hwax-services/*.log"):
        assert f in blk, f"{f} 가 가드 묶음에 없다"
        assert f not in _code(TMPL[:i]) and f not in _code(TMPL[TMPL.index("# (B)"):]), f"{f} 가 가드 없는 묶음에도 있다 — NUL 구멍"
    assert 'append-guard.sh "$1"' in blk and "copytruncate" in blk and "sharedscripts" not in blk.replace("nosharedscripts", ""), \
        "가드는 로그마다(nosharedscripts) 돌아야 한 로그 실패가 묶음 전체를 막지 않는다"
