# update-all 의 ⚠ 경고를 끝에서 다시 센다 — 종료코드는 그대로(5차 요청 §5)
"""cae00 이 상시 경고 둘('매핑된 서비스 없음' 다운 백엔드)에 섞여 vLLM 정지를 같은 출력에서 놓쳤다. 그 줄은 echo 라 어디에도
세어지지 않았다. bad 정의와 끝 요약을 원문 그대로 떼어 돌린다."""
import re
import subprocess
from pathlib import Path

SRC = (Path(__file__).resolve().parents[2] / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")


def _summary_block() -> str:
    i = SRC.index("# ⚠ 경고 요약")
    return SRC[i:SRC.index('if [ "$FAIL" = 1 ]; then', i)]


def _run(body: str) -> subprocess.CompletedProcess:
    bad_def = re.search(r"^bad\(\)  \{.*\}$", SRC, re.M).group(0)
    return subprocess.run(["bash", "-c", "\n".join([bad_def, body, _summary_block(), "echo RC_MARK"])],
                          capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})


def test_경고는_끝에서_건수와_함께_다시_나온다():
    p = _run('bad "다운 백엔드 arp — 매핑된 서비스 없음(수동 확인)"; bad "LLM 엔드포인트 무응답"')
    assert p.returncode == 0, p.stderr
    tail = p.stdout.split("경고 2건", 1)
    assert len(tail) == 2, p.stdout
    assert "· 다운 백엔드 arp" in tail[1] and "· LLM 엔드포인트 무응답" in tail[1]


def test_경고가_없으면_요약도_없다():
    p = _run(":")
    assert "경고" not in p.stdout and p.stdout.strip() == "RC_MARK"


def test_매핑_없는_다운_백엔드는_echo_가_아니라_경고다():
    assert '*) bad "다운 백엔드 $b — 매핑된 서비스 없음(수동 확인)" ;;' in SRC
    assert 'echo "  · 다운 백엔드 $b' not in SRC


def test_경고는_종료코드를_세우지_않는다():
    """bad 가 FAIL 을 건드리면 비치명 경고로 배포가 실패한다 — 색과 판정이 어긋나던 옛 결함의 반대 방향."""
    bad_def = re.search(r"^bad\(\)  \{.*\}$", SRC, re.M).group(0)
    assert "FAIL" not in bad_def.replace("WARN_ITEMS", "")
