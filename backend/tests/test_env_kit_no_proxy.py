# 설정 킷의 NO_PROXY 는 사내 주소를 적지 않고 적용 시점에 박스 infra/.env 로 채운다(@NO_PROXY@ — 10-17 결정 1)
"""왜 — 이 리포는 공개다. 킷 다섯이 상암 LLM 호스트를 NO_PROXY 에 그대로 적고 있었다(가드의 마지막 예외 다섯). 값은 박스마다
다르고 정본은 포털 infra/.env(LLM_BASE_URL · RA_HOST · ARP_HOST)다 — update-all 1g 가 자기 프로세스의 NO_PROXY 에 더하는 것과 같은 목적지다.

apply-envs.sh 를 임시 박스에서 실제로 돌린다(HOME 을 임시로 — 형제 리포를 ~/claude 에서 찾지 못하게). 주소는 문서용(203.0.113.x)이다.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KITS = ROOT / "infra/env-kits"


def _apply(tmp_path: Path, infra_env: str, svc: str = "ai-data-hub", existing: str | None = None) -> str:
    portal = tmp_path / "HWAXPortal"
    shutil.copytree(KITS, portal / "infra/env-kits")
    (portal / "infra/scripts/lib").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/lib/llm-pool.sh", portal / "infra/scripts/lib/llm-pool.sh")
    (portal / "infra/.env").write_text(infra_env, encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    target = {"ai-data-hub": tmp_path / "AIDataHub/deploy/apptainer/.env",
              "heax-hub": tmp_path / "HEAXHub/.env"}[svc]
    target.parent.mkdir(parents=True)
    if existing is not None:
        target.write_text(existing, encoding="utf-8")
    r = subprocess.run(["bash", str(portal / "infra/env-kits/apply-envs.sh"), svc], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8"})
    assert r.returncode == 0 and f"→ {target}" in r.stdout, r.stdout + r.stderr
    return target.read_text(encoding="utf-8")


def _v(env: str, key: str) -> list[str]:
    return re.findall(rf"^{key}=(.*)$", env, re.M)


def test_킷은_NO_PROXY_에_주소를_적지_않는다():
    for kit in sorted(KITS.glob("*.env")):
        for line in kit.read_text(encoding="utf-8").splitlines():
            if line.startswith(("NO_PROXY=", "no_proxy=")):
                assert line.split("=", 1)[1] == "@NO_PROXY@", f"{kit.name}: {line.split('=', 1)[0]} 에 값을 직접 적었다"


def test_박스_infra_env_의_내부_목적지로_채운다(tmp_path):
    env = _apply(tmp_path, "LLM_BASE_URL=http://203.0.113.11:10000/v1\nRA_HOST=203.0.113.20\nARP_HOST=arp.example.test\n"
                           "NO_PROXY=.corp.example,203.0.113.11\n")
    want = "127.0.0.1,localhost,203.0.113.11,203.0.113.20,arp.example.test,.corp.example"
    assert _v(env, "NO_PROXY") == [want] and _v(env, "no_proxy") == [want], env


def test_아무것도_없으면_루프백만(tmp_path):
    env = _apply(tmp_path, "OTHER=1\n", svc="heax-hub")
    assert _v(env, "NO_PROXY") == ["127.0.0.1,localhost"] and _v(env, "no_proxy") == ["127.0.0.1,localhost"], env


def test_이미_있는_값은_건드리지_않는다(tmp_path):
    env = _apply(tmp_path, "LLM_BASE_URL=http://203.0.113.11:10000/v1\n", existing="NO_PROXY=keep.example,127.0.0.1\n")
    assert _v(env, "NO_PROXY") == ["keep.example,127.0.0.1"], env
    assert _v(env, "no_proxy") == ["127.0.0.1,localhost,203.0.113.11"], "없는 철자는 더한다"
