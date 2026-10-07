# 서비스가 내부 목적지(RA·ARP)를 사내 프록시로 부르지 않게 — start.sh 가 NO_PROXY 를 명시해서 넘기고, update-all 이 RA·ARP 호스트를 더한다(9차 요청 §4-(5)·§4-(2))
"""왜 — start.sh 의 `--env` 명시 목록에 NO_PROXY 가 없어 호스트 env 상속에만 기댔다. 같은 파일이 SAML 에 대해
「상속에만 기대면 조용히 되돌아간다」고 적어 둔 바로 그 모양이다. 프록시를 타면 상대(RA)의 IP 허용목록에 걸려 403 이 난다
(게이트웨이에서 2026-10-03 실측). 그 우회 목록에 RA·ARP 가 들어 있는 것도 운영자 ~/.bashrc 의 임시 블록에 기대고 있었다 —
update-all 이 1e·1f 에서 읽은 두 호스트를 더해 뒤에 뜨는 서비스가 물려받게 하고, update-all 밖에서 뜨는 포털은 start.sh 가 직접 더한다.

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
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


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


def test_APPTAINERENV_로_넘기던_박스의_값을_덮지_않는다(start_portal):
    """apptainer 는 `--env` > `APPTAINERENV_*` > 호스트 env 순이다(실측 1.3.6). 컨테이너용 값을 APPTAINERENV_NO_PROXY 로만 주던
    박스는 종전엔 그 값이 들어갔다 — 합치지 않으면 명시한 `--env` 가 그것을 조용히 덮는다."""
    envs = start_portal(APPTAINERENV_NO_PROXY="198.51.100.7,127.0.0.1", NO_PROXY="127.0.0.1,203.0.113.7",
                        APPTAINERENV_no_proxy="198.51.100.8")
    assert set(envs["NO_PROXY"].split(",")) == {"198.51.100.7", "127.0.0.1", "203.0.113.7", "198.51.100.8"}
    assert envs["NO_PROXY"].count("127.0.0.1") == 1 and envs["no_proxy"] == envs["NO_PROXY"]


def test_별표와_대역_표기는_글자_그대로_간다(start_portal):
    """목록을 따옴표 없이 돌리면 `*` 가 현재 디렉터리의 파일 이름으로 풀린다."""
    envs = start_portal(NO_PROXY="*,203.0.113.0/24,*.corp.example")
    assert envs["NO_PROXY"] == "*,203.0.113.0/24,*.corp.example"


def test_둘_다_없는_박스에서도_기동이_죽지_않는다(start_portal):
    """set -u 아래다 — 미정의 변수를 그대로 읽으면 포털이 안 뜬다."""
    envs = start_portal()
    assert envs["NO_PROXY"] == "" and envs["no_proxy"] == ""
    assert envs["SESSION_SECRET"] == "s" * 40, "다른 --env 는 그대로다"


# ── update-all 밖에서 뜨는 포털(restart.sh·부팅 유닛) — infra/.env 의 RA_HOST·ARP_HOST 를 start.sh 가 직접 더한다 ─────────
def test_update_all_밖에서_띄워도_RA_ARP_호스트가_들어간다(start_portal):
    """update-all 의 export 는 그 실행이 띄운 프로세스만 받는다. restart.sh 로 띄운 포털은 운영자 셸의 값만 본다."""
    envs = start_portal("RA_HOST=203.0.113.10   # RA 주(A)\nARP_HOST=203.0.113.20\n")
    assert envs["NO_PROXY"] == "203.0.113.10,203.0.113.20" and envs["no_proxy"] == envs["NO_PROXY"]


def test_이미_있는_호스트는_두_번_넣지_않고_있던_항목도_그대로다(start_portal):
    """update-all 이 띄울 때는 물려받은 NO_PROXY 에 이미 둘 다 있다."""
    envs = start_portal("RA_HOST=203.0.113.10\nARP_HOST=203.0.113.20\n",
                        NO_PROXY="127.0.0.1,localhost,::1,198.51.100.9,203.0.113.10,203.0.113.20")
    assert envs["NO_PROXY"] == "127.0.0.1,localhost,::1,198.51.100.9,203.0.113.10,203.0.113.20"


def test_주석으로만_있는_호스트는_더하지_않는다(start_portal):
    envs = start_portal("# RA_HOST=   # ⚠ 값을 정해야 한다\n# ARP_HOST=\n", NO_PROXY="127.0.0.1")
    assert envs["NO_PROXY"] == "127.0.0.1"


# ── update-all — 1f 가 닫힌 뒤 RA·ARP 호스트를 NO_PROXY 에 더한다(뒤에 뜨는 서비스가 물려받는다) ─────────────────────
def _fn(name: str) -> str:
    i = UA.index(f"{name}() {{")
    return UA[i:UA.index("\n}\n", i) + 3]


def _top_export() -> str:
    """update-all 맨 위의 그 한 줄 — 루프백을 앞에 붙이고 no_proxy 를 NO_PROXY 와 같게 맞춘다."""
    i = UA.index('export NO_PROXY="127.0.0.1,localhost,::1')
    return UA[i:UA.index("\n", i) + 1]


def _run_1f_and_after(tmp_path, *, infra_env: str = "", pre: str = "", **env) -> tuple[str, str]:
    """맨 위 export → (1e 가 남긴 RA_HOST 는 pre 로) → 1f 원문 → 그 뒤 §2 머리까지 원문. 끝에서 **자식 프로세스**가 본 값을 찍는다."""
    repo = tmp_path / "HWAXPortal"; (repo / "infra").mkdir(parents=True); (repo / "backend/config").mkdir(parents=True)
    gw = tmp_path / "HWAXMcpGateway"; gw.mkdir()
    (repo / "infra/.env").write_text(infra_env)
    i = UA.index("# ── 1f) AI Ready Portal(ARP) 연결")
    block = UA[i:UA.index("# ── 2) 전 서비스 배포", i)]
    script = "\n".join([
        "set -uo pipefail",                       # update-all 과 같은 셸 옵션 — 리포가 정의하지 않는 변수를 읽으면 여기서 죽는다
        _top_export(),
        'ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; }; hr() { echo "HR:$*"; }',
        'hwax_skip() { echo "SKIP:$1"; }',
        _fn("_envfile_value"), _fn("_ra_envv"), _fn("_upsert_kv"),
        f'SELF_REPO="{repo}"', f'GW_DIR="{gw}"', pre, block,
        """bash -c 'printf "CHILD=[%s][%s]\\n" "${NO_PROXY-unset}" "${no_proxy-unset}"'""",
    ])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), **env})
    assert r.returncode == 0, r.stderr
    assert "unbound variable" not in r.stderr, r.stderr
    child = [ln for ln in r.stdout.splitlines() if ln.startswith("CHILD=")]
    assert len(child) == 1, r.stdout + r.stderr
    return child[0], r.stdout


LO = "127.0.0.1,localhost,::1"


def test_update_all_이_RA_ARP_호스트를_더하고_자식이_물려받는다(tmp_path):
    """**이 시험이 #12 의 이유다** — 더하지 않으면 뒤에 뜨는 게이트웨이·포털이 RA 를 프록시로 부른다."""
    child, out = _run_1f_and_after(tmp_path, infra_env="ARP_HOST=203.0.113.20\n", pre='RA_HOST="203.0.113.10"',
                                   NO_PROXY="198.51.100.9")
    want = f"{LO},198.51.100.9,203.0.113.10,203.0.113.20"
    assert child == f"CHILD=[{want}][{want}]", "있던 항목은 그대로, 두 호스트는 뒤에, 두 철자가 같은 값"
    assert "203.0.113.10" not in "".join(ln for ln in out.splitlines() if "NO_PROXY" in ln), "더한 것은 이름으로만 알린다"


def test_update_all_은_이미_있는_호스트를_두_번_넣지_않는다(tmp_path):
    child, _ = _run_1f_and_after(tmp_path, infra_env="ARP_HOST=203.0.113.10\n", pre='RA_HOST="203.0.113.10"',
                                 NO_PROXY="203.0.113.10,198.51.100.9")
    assert child == f"CHILD=[{LO},203.0.113.10,198.51.100.9][{LO},203.0.113.10,198.51.100.9]"


@pytest.mark.parametrize("pre", ['RA_HOST=""', "unset RA_HOST"])
def test_update_all_은_없는_값을_더하지_않고_죽지도_않는다(tmp_path, pre):
    """RA_HOST 는 미설정·거부(1e 가 비운다)면 빈 값이다. ARP_HOST 는 주석 줄이라 빈 값. set -u 아래에서 끝까지 돈다."""
    child, out = _run_1f_and_after(tmp_path, infra_env="# ARP_HOST=\n", pre=pre)
    assert child == f"CHILD=[{LO}][{LO}]"
    assert "SKIP:AI Ready Portal 주소 묶기" in out


@pytest.mark.parametrize("arp", ["localhost", "http://203.0.113.20", "203.0.113.20/x"])
def test_update_all_은_1f_가_거부한_값을_더하지_않는다(tmp_path, arp):
    child, out = _run_1f_and_after(tmp_path, infra_env=f"ARP_HOST={arp}\n", pre='RA_HOST=""')
    assert "FAIL:ARP_HOST" in out and child == f"CHILD=[{LO}][{LO}]"
