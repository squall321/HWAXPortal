# update-all · deploy-all 의 단계 제목 줄 꼬리에 시각이 붙는가 — 구간 시간을 실행 기록만으로 재려고(docs/request-1125 SE-9)
"""왜 — 11-05 동기화 효율 조사(SE-1 ~ SE-8)는 단계가 만든 파일 이름 · 수정 시각 · 재기동 지문 파일 시각으로 구간을 다시 맞춰야 했다.
제목 문구와 앞부분은 그대로 두어 '══ 4)' · '── AIDataHub' 같은 기존 grep 이 그대로 맞아야 한다.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _hr_line(script: str) -> str:
    src = (ROOT / "infra/scripts" / script).read_text(encoding="utf-8")
    start = src.index("\nhr() {") + 1
    # 함수 정의만 떼어 낸다 — update-all 은 여러 줄, deploy-all 은 한 줄
    end = src.index("\nok() {", start)
    body = src[start:end]
    r = subprocess.run(["bash", "-c", body + '\nhr "4) 챗 스택 재기동"'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_update_all_제목에_시각():
    out = _hr_line("update-all.sh")
    assert "══ 4) 챗 스택 재기동 ══" in out, out
    assert re.search(r"\[\d\d:\d\d:\d\d\]\n$", out), out


def test_deploy_all_제목에_시각():
    out = _hr_line("deploy-all-from-drive.sh")
    assert "── 4) 챗 스택 재기동 ──" in out, out
    assert re.search(r"\[\d\d:\d\d:\d\d\]\n$", out), out
