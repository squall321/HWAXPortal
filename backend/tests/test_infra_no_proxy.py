# 포털 컨테이너가 내부 목적지(RA·TestScope)를 사내 프록시로 부르지 않게 — start.sh 가 NO_PROXY 를 명시해서 넘긴다(9차 요청 §4-(5))
"""왜 — start.sh 의 `--env` 명시 목록에 NO_PROXY 가 없어 호스트 env 상속에만 기댔다. 같은 파일이 SAML 에 대해
「상속에만 기대면 조용히 되돌아간다」고 적어 둔 바로 그 모양이다. 프록시를 타면 상대(RA)의 IP 허용목록에 걸려 403 이 난다
(게이트웨이에서 2026-10-03 실측).

블록은 원문 그대로 떼어 **실제로 돌린다** — `_common.sh` 사본이 임시 리포의 infra/.env 를 소싱하고, apptainer 자리에 선 대역이
받은 인자를 적는다(실물 인스턴스·실물 infra/.env 를 건드리지 않는다). 주소는 문서용 예약 대역(TEST-NET)만 쓴다.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
START = (ROOT / "infra/scripts/start.sh").read_text(encoding="utf-8")


def _portal_block() -> str:
    i = START.index("# 3. Portal (single-origin")
    return START[i:START.index("# 안 뜬 이유를 배포 출력에 바로 보인다", i)]


@pytest.fixture()
def start_portal(tmp_path):
    """start.sh 의 포털 기동 블록을 임시 리포에서 돌려, apptainer 가 받은 `--env` 를 dict 로 돌려준다."""
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/_common.sh", repo / "infra/scripts/_common.sh")
    argv = tmp_path / "argv"
    stub = tmp_path / "bin/apptainer"; stub.parent.mkdir()
    # 대역 — `instance list` 에는 빈 목록(= 안 떠 있다), `instance start` 는 인자를 한 줄에 하나씩 적는다
    stub.write_text('#!/usr/bin/env bash\n[ "$1 $2" = "instance start" ] && printf \'%s\\n\' "$@" > "' + str(argv) + '"\nexit 0\n')
    stub.chmod(0o755)
    (tmp_path / "cwd").mkdir(); (tmp_path / "cwd/어떤파일").write_text("x")   # 글롭이 풀리면 이 이름이 값에 섞인다

    def run(infra_env: str = "", **env) -> dict:
        (repo / "infra/.env").write_text("SESSION_SECRET=" + "s" * 40 + "\n" + infra_env)
        argv.unlink(missing_ok=True)
        script = f'. "{repo}/infra/scripts/_common.sh"\ncd "{tmp_path}/cwd"\n{_portal_block()}'
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                           env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "APPTAINER": str(stub),
                                "HWAX_DATA_ROOT": str(tmp_path / "data"), **env})
        assert r.returncode == 0, r.stderr
        assert argv.exists(), "대역 apptainer 가 불리지 않았다 — 블록이 기동 갈래를 타지 않았다"
        args = argv.read_text().split("\n")
        return dict(args[i + 1].split("=", 1) for i, a in enumerate(args[:-1]) if a == "--env")
    return run


def test_NO_PROXY_를_두_철자_모두_명시해서_넘긴다(start_portal):
    """**이 시험이 이 파일의 이유다** — 종전엔 `--env` 목록에 아예 없었다."""
    envs = start_portal(NO_PROXY="127.0.0.1,localhost,203.0.113.7")
    assert envs["NO_PROXY"] == "127.0.0.1,localhost,203.0.113.7"
    assert envs["no_proxy"] == envs["NO_PROXY"], "httpx·curl 은 소문자를 먼저 본다 — 둘이 다르면 소문자가 이긴다"


def test_소문자만_둔_박스의_값을_빈_값으로_덮지_않는다(start_portal):
    """요청서의 두 줄(`no_proxy=${NO_PROXY:-}`)을 그대로 넣으면 소문자만 둔 박스에서 `no_proxy=` 빈 값이 넘어가고,
    apptainer 는 명시한 값이 있으면 호스트 값을 물려주지 않는다(실측 1.3.6) — 있던 우회까지 지운다."""
    envs = start_portal(no_proxy="203.0.113.7,.corp.example")
    assert envs["no_proxy"] == "203.0.113.7,.corp.example"
    assert envs["NO_PROXY"] == envs["no_proxy"]


def test_두_철자가_다르면_합친다_중복_없이(start_portal):
    envs = start_portal(NO_PROXY="127.0.0.1,203.0.113.7", no_proxy="203.0.113.7, 198.51.100.4")
    assert envs["NO_PROXY"] == "127.0.0.1,203.0.113.7,198.51.100.4"
    assert envs["no_proxy"] == envs["NO_PROXY"]


def test_별표와_대역_표기는_글자_그대로_간다(start_portal):
    """목록을 따옴표 없이 돌리면 `*` 가 현재 디렉터리의 파일 이름으로 풀린다."""
    envs = start_portal(NO_PROXY="*,203.0.113.0/24,*.corp.example")
    assert envs["NO_PROXY"] == "*,203.0.113.0/24,*.corp.example"


def test_둘_다_없는_박스에서도_기동이_죽지_않는다(start_portal):
    """set -u 아래다 — 미정의 변수를 그대로 읽으면 포털이 안 뜬다."""
    envs = start_portal()
    assert envs["NO_PROXY"] == "" and envs["no_proxy"] == ""
    assert envs["SESSION_SECRET"] == "s" * 40, "다른 --env 는 그대로다"
