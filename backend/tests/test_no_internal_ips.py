# 추적 파일에 **내부 IP 가 늘지 않게** 막는다 — 이 리포는 public GitHub 에 있다
#
# CLAUDE.md 가 명시로 금지한다: "내부 IP·토큰·비밀번호를 추적 파일에 적지 않는다.
# 이 리포는 GitHub 에 있다." 그런데 실측(2026-09-15 7차 감사)으로 추적 파일 **14개**에
# 사내 IP **10개**가 있고, `raw.githubusercontent.com` 이 **200** 을 준다(= 공개로 읽힌다).
# 게다가 **git 히스토리에도 이미 있어**, HEAD 를 지워도 공개 기록은 남는다.
#
# ⚠ 그래서 이 검사는 "0건" 을 요구하지 않는다 — 지금 지우는 것은 배포가 읽는 설정을
# 건드리고, 히스토리 세탁은 force-push 라 **사람이 결정할 일**이다. 대신 **늘지 않게**
# 막는다. 새 IP 를 적으면 여기서 걸린다. 사람이 정리하면 이 수를 내리면 된다.
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 사내 대역. 127.x(루프백)·0.0.0.0 은 뺀다 — 그건 내부 배치가 아니다.
_IP = re.compile(r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\.?\d{0,3}\b")
# 지금 있는 것(줄이는 방향으로만 바꾼다). 늘리려면 **먼저 왜 필요한지 적어라.**
KNOWN_FILES = 15   # 실측 — 문서 1개가 더 있었다(CHAT-FIRST-AI-INTEGRATION.md)


def _tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    return [ROOT / p for p in out.stdout.splitlines() if p]


def test_내부_IP_를_적은_추적_파일이_늘지_않았다():
    hits = {}
    for p in _tracked():
        rel = str(p.relative_to(ROOT))
        # 이 검사 파일 자신(예시 IP 를 적는다)과 lock 파일(패키지 해시에 숫자열이 섞인다)은 뺀다
        if rel == "backend/tests/test_no_internal_ips.py" or rel.endswith("pnpm-lock.yaml"):
            continue
        if not p.is_file() or p.suffix in (".png", ".jpg", ".ico", ".woff2", ".sif"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found = sorted(set(_IP.findall(text)))
        if found:
            hits[str(p.relative_to(ROOT))] = found
    assert len(hits) <= KNOWN_FILES, (
        f"내부 IP 를 적은 추적 파일이 {KNOWN_FILES} → {len(hits)} 로 늘었다. "
        f"이 리포는 **public GitHub** 에 있다(CLAUDE.md 금지 항목). "
        f"새로 생긴 것: {sorted(set(hits) )[:8]}")


def test_가드가_실제로_찾는다():
    """0건을 훑고 통과하면 아무것도 안 지킨다 — 실제로 찾는지 본다."""
    assert _IP.search("NO_PROXY=10.198.143.137,localhost")
    assert _IP.search("http://192.168.0.5:8000")
    assert not _IP.search("127.0.0.1:8723"), "루프백은 내부 배치가 아니다"
    assert not _IP.search("0.0.0.0:8723")
    assert len(_tracked()) > 100, "추적 파일을 못 읽었다 — 가드가 죽었다"
