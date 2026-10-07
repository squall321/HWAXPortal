# update-all §6 권한 표 대조 — 그 박스의 실제 게이트웨이 백엔드가 access.yaml 에 다 있는지(5차 요청 §2)
"""왜 운영 박스 점검인가. CI 시험은 dev 게이트웨이만 본다 — cae00 의 구멍(simflow 전원 공개·plm-defect 전원 차단)은
cae00 에만 있는 백엔드였다. 블록을 원문 그대로 떼어 curl 을 셸 함수로 갈아 돌린다(실물 포털을 치지 않는다)."""
import json
import subprocess
from pathlib import Path

SRC = (Path(__file__).resolve().parents[2] / "infra" / "scripts" / "update-all.sh").read_text(encoding="utf-8")
SECRET = "gw-test-secret-value"


def _run(tmp_path, *, backends, policy, gw_dir=True):
    i = SRC.index("  # ── 이 박스의 게이트웨이 백엔드가 **전부** 권한 표")
    block = SRC[i:SRC.index("  # ── RA 사용자 위임", i)]
    gw = tmp_path / "gw"
    gw.mkdir(exist_ok=True)
    (gw / "gateway_config.json").write_text(json.dumps({"_gateway": {"token": SECRET}}))
    argv_log = tmp_path / "argv"
    script = "\n".join([
        'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }', 'fail() { echo "FAIL:$*"; }',
        'hwax_skip() { echo "SKIP:$1"; }',
        # 정책 응답을 내고, 받은 argv 를 적는다 — 시크릿이 argv 에 실리면 안 된다(stdin -K - 로만)
        f'curl() {{ printf "%s\\n" "$*" >> "{argv_log}"; cat >/dev/null; printf "%s" "$POLICY"; }}',
        "H='" + json.dumps({"backends": {b: True for b in backends}}) + "'",
        f"GW_DIR='{gw}'" if gw_dir else "GW_DIR=''",
        "POLICY='" + policy + "'",
        block,
    ])
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    return p.stdout, (argv_log.read_text() if argv_log.exists() else "")


def _pol(*keys):
    return json.dumps({"backends": {k: ["plat:x"] for k in keys}})


def test_전부_표에_있으면_초록(tmp_path):
    out, _ = _run(tmp_path, backends=["ste", "simflow"], policy=_pol("ste", "simflow", "arp"))
    assert out.startswith("OK:권한 표 대조"), out


def test_표에_없는_백엔드는_이름을_대고_실패한다(tmp_path):
    """**이 시험이 이 블록의 이유다** — cae00 의 simflow·plm-defect 모양."""
    out, _ = _run(tmp_path, backends=["ste", "simflow", "plm-defect"], policy=_pol("ste"))
    first = out.splitlines()[0]
    assert first.startswith("FAIL:권한 표 구멍") and "plm-defect simflow" in first, out


def test_구멍을_메울_자리로_박스_오버레이도_알린다(tmp_path):
    """그 박스에만 있는 백엔드를 추적 파일에 적게만 이끌면 박스 사정이 모든 박스의 표에 들어간다 — 오버레이를 함께 알린다."""
    out, _ = _run(tmp_path, backends=["ste", "simflow"], policy=_pol("ste"))
    assert "backend/config/access.yaml" in out and "backend/config/access.local.yaml" in out, out


def test_정책을_못_읽으면_초록이_아니라_경고(tmp_path):
    for bad_body in ("", "000", '{"detail":"forbidden"}', "not json"):
        out, _ = _run(tmp_path, backends=["simflow"], policy=bad_body)
        assert out.startswith("BAD:권한 표 대조"), (bad_body, out)


def test_시크릿은_argv_에_안_실린다(tmp_path):
    _, argv = _run(tmp_path, backends=["ste"], policy=_pol("ste"))
    assert "-K -" in argv and SECRET not in argv, argv


def test_게이트웨이_리포가_없으면_안_켠_기능으로_남긴다(tmp_path):
    out, _ = _run(tmp_path, backends=["simflow"], policy=_pol(), gw_dir=False)
    assert out.strip() == "SKIP:권한 표 대조", out
