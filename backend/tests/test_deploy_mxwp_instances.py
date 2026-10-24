# cae00 배치가 MX 백서의 새 SIF 를 받으면 그 SIF 로 뜬 인스턴스를 전부 내렸다 올린다 — 위키 워커(mxwp_wiki)까지(docs/mxwp-wiki P9)
"""왜 — MX 백서 images-from-drive 는 바뀐 SIF 를 갈아 끼운다. 떠 있는 인스턴스 밑의 SIF 를 덮어쓰면 squashfs 가 깨져 그 안의 exec 가
전부 죽는다(cae00 mxwp_api → mxwp-mcp 에서 실제로 났다). 배치는 내렸다 MX 백서 start.sh 로 다시 띄우는데, start.sh 는 떠 있는 인스턴스를
'이미 떠 있다' 로 건너뛴다 — 정지 목록에서 빠진 인스턴스는 깨진 마운트로 남는다. 위키 워커(wiki.sif)가 W3 로 새로 생겼다.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "infra/scripts/deploy-all-from-drive.sh"
MXWP = ROOT.parent / "MXWhitePaper"
# 밖에서 받는 이미지 — 거의 바뀌지 않아 배치가 내리지 않는다(종전 그대로). MX 백서가 짓는 SIF 만 본다.
_THIRD_PARTY = {"POSTGRES_SIF", "MEILI_SIF", "MINIO_SIF"}


def _stop_list() -> list[str]:
    m = re.search(r'_stop\(\)\s*\{\s*local _i; for _i in ([a-z_ ]+); do "\$_appt" instance stop', DEPLOY.read_text(encoding="utf-8"))
    assert m, "deploy-all-from-drive.sh 의 MX 백서 _stop 을 못 찾았다 — 모양이 바뀌었으면 이 시험도 고쳐라"
    return m.group(1).split()


def test_MX_백서_배치는_위키_워커도_내렸다_올린다():
    assert _stop_list() == ["mxwp_web", "mxwp_wiki", "mxwp_api"], "순서는 MX 백서 stop.sh 와 같다(web · wiki · api)"


def test_MX_백서가_짓는_SIF_로_뜨는_인스턴스는_전부_정지_목록에_있다():
    start = MXWP / "infra/scripts/start.sh"
    if not start.is_file():
        pytest.skip(f"형제 리포 없음: {MXWP}")
    inst = dict(re.findall(r"^(INST_[A-Z]+)=(\S+)", (MXWP / "infra/scripts/_common.sh").read_text(encoding="utf-8"), re.M))
    pairs = re.findall(r'start_instance "\$(INST_[A-Z]+)" "\$([A-Z_]+_SIF)"', start.read_text(encoding="utf-8"))
    assert pairs and inst, "MX 백서 start.sh · _common.sh 에서 인스턴스를 못 뽑았다 — 모양이 바뀌었으면 이 시험도 고쳐라"
    need = {inst[i] for i, sif in pairs if sif not in _THIRD_PARTY}
    assert "mxwp_wiki" in need, "위키 워커를 뽑지 못했다 — 추출이 틀렸다"
    missing = sorted(need - set(_stop_list()))
    assert not missing, f"MX 백서가 짓는 SIF 로 뜨는데 배치가 내리지 않는 인스턴스 — 갈아 끼운 SIF 위에서 깨진 채 남는다: {missing}"
