# ste-doctor 의 teleport 행 — 사람 tsh 세션이 아니라 **터널이 실제로 쓰는 인증서**(tbot 이면 tbot 것)를 본다(docs/ste-cae00 D-31)
#
# 진짜 SSH 인증서를 만들어(ssh-keygen -s) 유효·만료를 가른다 — 형식을 짐작해 흉내 내면 파서가 틀려도 초록이다.
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "infra/scripts/ste-doctor.sh").read_text(encoding="utf-8")

pytestmark = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen 이 없다")


def _block() -> str:
    i = SRC.index("  # Teleport 인증서 — **터널이 실제로 쓰는** ssh_config")
    return SRC[i:SRC.index("  # Teleport 세션 — tsh 가 있으면", i)]


def _envv() -> str:
    i = SRC.index("envv() {")
    return SRC[i:SRC.index("\n", i) + 1]


def _cert(d: Path, validity: str) -> Path:
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(d / "ca")], check=True)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(d / "key")], check=True)
    subprocess.run(["ssh-keygen", "-q", "-s", str(d / "ca"), "-I", "hwax-test", "-n", "ste-run", "-V", validity,
                    str(d / "key.pub")], check=True)
    return d / "key-cert.pub"


def _run(tmp_path, *, validity="-5m:+1h", tbot=True, unit_cfg=None, cert_lines=True, cert_name="key-cert.pub") -> str:
    d = tmp_path / "machine-id"; d.mkdir()
    c = _cert(d, validity)
    if cert_name != c.name:
        c.rename(d / cert_name)
    cfg = d / "ssh_config"
    lines = ["Host *.ste.teleport"]
    if cert_lines:
        lines += [f'    IdentityFile "{d}/key"', f'    CertificateFile "{d}/{cert_name}"']
    proxy = f'"/usr/local/bin/tbot" ssh-proxy-command --destination-dir={d}' if tbot else "tsh proxy ssh %r@%h:%p"
    lines += [f"    ProxyCommand {proxy}"]
    cfg.write_text("\n".join(lines) + "\n")
    tenv = tmp_path / "transport.env"
    tenv.write_text(f"TRANSPORT_MODE=teleport\nTELEPORT_SSH_CONFIG={cfg}\n")
    unit = tmp_path / "ste-tunnel.service"
    unit.write_text(f"[Service]\nExecStart=/usr/bin/ssh -N -F {unit_cfg or cfg} \\\n  -L 127.0.0.1:15810:127.0.0.1:15810 \\\n  ste\n")
    script = "\n".join([
        'ok() { echo "OK:$1 $2"; }', 'bad() { echo "BAD:$1 $2"; }', 'warn() { echo "WARN:$1 $2"; }',
        _envv(), f'TENV="{tenv}"', f'_tu="{unit}"', _block()])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_tbot_인증서가_살아_있으면_초록이고_남은_시간을_말한다(tmp_path):
    out = _run(tmp_path)
    assert "OK:teleport tbot 인증서 유효 — 남은" in out, out
    assert "OK:tunnel-cfg 터널 유닛이 같은 ssh_config 를 쓴다 (tbot)" in out


def test_tbot_인증서가_만료되면_빨강이다(tmp_path):
    """tbot 이 갱신을 멈추면 터널·ste 전부가 끊긴다 — 사람 세션이 없는 것과 섞으면 안 된다."""
    out = _run(tmp_path, validity="20200101:20200102")
    assert "BAD:teleport tbot 인증서가 **만료됐다**" in out, out


def test_터널이_다른_ssh_config_로_떠_있으면_빨강이다(tmp_path):
    """tbot 으로 바꿨는데 유닛은 옛 tsh 파일을 물고 있으면 사람 세션이 끝날 때 끊긴다."""
    out = _run(tmp_path, unit_cfg="/home/x/.tsh-ssh_config")
    assert "BAD:tunnel-cfg" in out and "install-ste-tunnel.sh" in out, out


def test_tsh_config_로_만든_파일도_인증서로_본다(tmp_path):
    out = _run(tmp_path, tbot=False)
    assert "OK:teleport tsh config 인증서 유효" in out, out


def test_인증서를_못_찾으면_모름이지_초록이_아니다(tmp_path):
    out = _run(tmp_path, cert_lines=False)
    assert "WARN:teleport" in out and "모름≠정상" in out, out


def test_CertificateFile_이_가리키는_인증서를_읽는다(tmp_path):
    """IdentityFile 옆 -cert.pub 로만 짐작하면 이름이 다른 인증서(tsh 가 만든 파일 등)를 못 찾는다."""
    out = _run(tmp_path, cert_name="ste-ssh-cert.pub")
    assert "OK:teleport tbot 인증서 유효" in out, out
