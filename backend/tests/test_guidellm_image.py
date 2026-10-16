# GuideLLM 측정 이미지 — 판을 못박고 토크나이저를 sha256 으로 굽는가 · Drive 로 올리고 받고 어긋남을 보는가(build-guidellm.sh · images-to/from-drive · drive-drift)
"""왜 — cae00 은 인터넷이 없어 dev 가 구운 이미지를 Drive 로 받는다. 굽는 날마다 판이 달라지면 측정끼리 견줄 수 없고, 올리는 쪽만 고치고
받는 쪽을 빼먹으면 '이미지는 Drive 로 간다' 가 거짓이 된다(searxng 에서 한 번 났다). 받는 쪽의 실제 동작은 test_images_from_drive 가 본다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SH = ROOT / "infra/scripts/build-guidellm.sh"


def test_GuideLLM_이미지는_판을_못박고_토크나이저를_sha256_으로_굽는다():
    src = BUILD_SH.read_text(encoding="utf-8")
    for pin in ('GUIDELLM_VERSION="0.8.0"', 'TORCH_VERSION="2.14.1+cpu"', 'BASE_IMAGE="python:3.12.14-slim-bookworm"',
                'GUIDELLM_DEPS_BEFORE="2026-10-01T00:00:00Z"', 'TOKENIZER_REV="cf457fa734ab149ffef225f80893eb38c6ff5cdc"',
                'TOKENIZER_JSON_SHA256="19e773648cb4e65de8660ea6365e10acca112d42a854923df93db4a6f333a82d"', "export PYTHONNOUSERSITE=1",
                '--uploaded-prior-to "$GUIDELLM_DEPS_BEFORE"', "HF_HUB_OFFLINE=1"):
        assert pin in src, pin
    assert '/infra/apptainer/guidellm.sif' in src and ". \"$ROOT/infra/scripts/_common.sh\"" not in src
    assert "/opt/tokenizers/glm-5.2" in src


def test_이미지는_Drive_로_간다_올리고_받고_어긋남을_본다():
    up = (ROOT / "infra/scripts/images-to-drive.sh").read_text(encoding="utf-8")
    down = (ROOT / "infra/scripts/images-from-drive.sh").read_text(encoding="utf-8")
    drift = (ROOT / "infra/scripts/drive-drift.sh").read_text(encoding="utf-8")
    assert 'cp "$GUIDELLM_SIF" "$STAGE/guidellm.sif"' in up and "[ -f guidellm.sif ] && files=\"$files guidellm.sif\"" in up
    assert 'hwax_install_if_changed "$STAGE/guidellm.sif" "$APPT_DIR/guidellm.sif"' in down
    loops = [ln.split(" in ", 1)[1].split(";")[0].split() for ln in drift.splitlines() if ln.strip().startswith("for _sif in ")]
    assert len(loops) == 1 and "guidellm" in loops[0], loops  # 상태판(gatus) 등 다른 이미지와 같은 목록에 있다
