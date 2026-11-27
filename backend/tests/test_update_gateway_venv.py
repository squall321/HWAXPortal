# update-all · update-sites 가 게이트웨이를 다시 띄우기 전에 게이트웨이 전용 venv(MCP SDK 2.x)를 맞추는지 — 못 맞추면 내리지 않는지(docs/mcp-modernize M4)
"""왜 — SDK 2.x 판 게이트웨이의 start.sh 는 고른 파이썬의 mcp 가 2.x 가 아니면 띄우지 않는다. update-sites 는 down → up 이라 venv 없이 내리면
다시 못 띄운다(챗 · 심의 · 개인 Claude 의 도구가 통째로 끊긴다). cae00 은 바깥 pip 이 막혀 있을 수 있어 Drive 바퀴 꾸러미로 짓는다.

lib(infra/scripts/lib/gateway-venv.sh)를 **원문 그대로** 읽고, 게이트웨이 리포 · Drive(rclone) · 파이썬 · install.sh 는 가짜로 둔다(실물 venv ·
Drive 는 건드리지 않는다). restart_svc · §4 · §5 · 자동 복구 구획도 원문을 떼어 대역 services.sh 로 돌린다 — dev 에서 update-all 은 돌리지 않는다.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIBDIR = ROOT / "infra/scripts/lib"
LIB = LIBDIR / "gateway-venv.sh"
UPDATE_SITES = (ROOT / "infra/scripts/update-sites.sh").read_text(encoding="utf-8")
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
PINS = ["anyio==4.16.0", "httpx==0.28.1", "mcp==2.3.0", "pydantic==2.14.4", "pyjwt==2.15.1", "starlette==1.10.0", "uvicorn==0.54.0"]
REQ = """# 게이트웨이 런타임 의존성(시험용 사본)
mcp==2.3.0               # 공식 SDK 2.x
httpx==0.28.1
uvicorn==0.54.0
starlette==1.10.0
PyJWT[crypto]==2.15.1    # 추가 꼴
anyio==4.16.0
pydantic==2.14.4
"""
ARCH = os.uname().machine


def _key(pyv: str = "3.12") -> str:
    """열쇠의 꼴을 lib 와 따로 셈한다 — 이름 차례로 이은 `이름==판` 줄들의 sha256 앞 12자(꼴이 바뀌면 dev 가 올린 꾸러미를 cae00 이 못 찾는다)."""
    return f"py{pyv}-{ARCH}-" + hashlib.sha256(("\n".join(PINS) + "\n").encode()).hexdigest()[:12]


class Box:
    """가짜 박스 — 게이트웨이 리포 · Drive · 파이썬 · rclone · install.sh."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.gw = tmp / "HWAXMcpGateway"
        (self.gw / "tools/gateway-wheels").mkdir(parents=True)
        (self.gw / "gateway.py").write_text("# 시험용\n")
        (self.gw / "requirements.txt").write_text(REQ)
        self.calls = tmp / "calls"
        self.drive = tmp / "drive"
        self.bin = tmp / "bin"; self.bin.mkdir()
        self.vers = tmp / "venv-versions"           # 지은 venv 가 대답할 판(install 이 쓴다 · 시험이 바꾼다)
        # 파이썬 — venv · ensurepip 가 있는 3.12 인 척한다(판 묻기만 받는다)
        self.py = self.bin / "python-fake"
        self.py.write_text("#!/usr/bin/env bash\necho 3.12\n"); self.py.chmod(0o755)
        # rclone — fake:<경로> 를 drive/<경로> 로 읽는다. lsf 는 없는 폴더면 3(rclone 의 '디렉터리 없음'), RCLONE_LSF_RC 로 다른 실패를 흉내 낸다
        rc = self.bin / "rclone"
        rc.write_text(f'''#!/usr/bin/env bash
echo "rclone $*" >> "{self.calls}"
map() {{ local p="${{1#fake:}}"; printf '%s' "{self.drive}/${{p%/}}"; }}
case "$1" in
  lsf) [ -n "${{RCLONE_LSF_RC:-}}" ] && exit "$RCLONE_LSF_RC"; d="$(map "${{@: -1}}")"; [ -d "$d" ] || exit 3; ls -p "$d" ;;
  copy) cp -r "$(map "$2")"/. "$3"/ ;;
  *) exit 9 ;;
esac
''')
        rc.chmod(0o755)
        # install.sh — 리포의 것 자리. 받은 꾸러미 · 파이썬을 적고 .venv/bin/python 을 만든다(INSTALL_RC 면 실패 — venv 를 만들지 않는다)
        inst = self.gw / "tools/gateway-wheels/install.sh"
        inst.write_text(f'''#!/usr/bin/env bash
echo "install $(basename "$1") $2 GATEWAY_DIR=$GATEWAY_DIR" >> "{self.calls}"
echo "· ① 꾸러미 대조"
if [ "${{INSTALL_RC:-0}}" != 0 ]; then echo "✗ venv 짓기 실패 — 되돌린다" >&2; exit "$INSTALL_RC"; fi
mkdir -p "$GATEWAY_DIR/.venv/bin"
cp "{tmp}/venv-python" "$GATEWAY_DIR/.venv/bin/python"; chmod +x "$GATEWAY_DIR/.venv/bin/python"
printf '%s\\n' {" ".join(p.replace("==", " ") for p in PINS)} | paste -d' ' - - > "{self.vers}"
echo "✓ 게이트웨이 전용 venv"
''')
        inst.chmod(0o755)
        vp = tmp / "venv-python"                     # venv 파이썬 — 이름마다 판을 대답한다(모르면 -)
        vp.write_text(f'''#!/usr/bin/env bash
shift 2
for n in "$@"; do v="$(awk -v n="$n" '$1 == n {{ print $2 }}' "{self.vers}" 2>/dev/null)"; echo "$n ${{v:--}}"; done
''')
        vp.chmod(0o755)

    def env(self, **kw) -> dict:
        return {"PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.tmp), "HWAX_GW_DIR": str(self.gw),
                "HWAX_DRIVE_REMOTE": "fake:HWAXPortal/images", "GATEWAY_VENV_PYTHON": str(self.py),
                "HWAX_GW_VENV_NOTE": str(self.tmp / "note"), **kw}

    def bundle(self, key: str | None = None, pyv: str = "3.12", arch: str = ARCH, lock: list[str] | None = None, bad_sha: bool = False) -> Path:
        d = self.drive / "HWAXPortal/tools/gateway-wheels" / (key or _key(pyv))
        d.mkdir(parents=True)
        (d / "mcp-2.3.0-py3-none-any.whl").write_bytes(b"wheel")
        (d / "requirements.lock").write_text("\n".join(lock if lock is not None else
                                                       [p.replace("pyjwt", "PyJWT") for p in PINS] + ["pydantic_core==2.41.0"]) + "\n")
        (d / "install.sh").write_text("#!/usr/bin/env bash\n")
        (d / "MANIFEST.txt").write_text(f"hwax-mcp-gateway venv 바퀴 꾸러미\npython={pyv} (cp{pyv.replace('.', '')})\narch={arch}\n")
        sums = subprocess.run("sha256sum ./*.whl requirements.lock install.sh MANIFEST.txt | sed 's# \\./# #'", shell=True, cwd=d,
                              capture_output=True, text=True, check=True).stdout
        (d / "SHA256SUMS").write_text(sums)
        if bad_sha:
            (d / "requirements.lock").write_text("mcp==9.9.9\n")
        return d

    def venv(self, versions: dict[str, str]):
        (self.gw / ".venv/bin").mkdir(parents=True, exist_ok=True)
        (self.gw / ".venv/bin/python").write_text((self.tmp / "venv-python").read_text()); (self.gw / ".venv/bin/python").chmod(0o755)
        self.vers.write_text("".join(f"{k} {v}\n" for k, v in versions.items()))

    def calls_list(self) -> list[str]:
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def note(self) -> str | None:
        p = self.tmp / "note"
        return p.read_text() if p.exists() else None


@pytest.fixture()
def box(tmp_path):
    return Box(tmp_path)


def _sh(script: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120, env=env)


def _lib(box: Box, body: str, **env) -> subprocess.CompletedProcess:
    """set -uo pipefail(update-sites · update-all 과 같다) 아래서 lib 를 읽고 body 를 돈다 — 풀리지 않은 변수가 있으면 여기서 깨진다."""
    return _sh(f'set -uo pipefail\n. "{LIB}"\n{body}', box.env(**env))


ALL_OK = {p.split("==")[0]: p.split("==")[1] for p in PINS}


# ── 판정 ──────────────────────────────────────────────────────────────────────────────────────────
def test_열쇠는_파이썬_판_아키텍처_고정_줄의_sha256_이다(box):
    r = _lib(box, f'_hwax_gw_venv_key 3.12 {ARCH} "$(_hwax_gw_venv_pins "{box.gw}/requirements.txt")"')
    assert r.stdout == _key(), (r.stdout, r.stderr)
    r = _lib(box, f'_hwax_gw_venv_pins "{box.gw}/requirements.txt"')
    assert r.stdout.split() == PINS, "이름은 소문자 · 추가 꼴([crypto]) · 주석을 떼고 이름 차례"


@pytest.mark.parametrize("req", [None, "mcp==1.28.0\nhttpx==0.28.1\n", "mcp>=2\n"])
def test_SDK_2x_를_고정하지_않는_판은_할_일이_없다(box, req):
    """옛 판(지금 master 에는 requirements.txt 가 없다) — 종전 venv 로 뜬다. 꾸러미를 찾지도 않는다."""
    if req is None:
        (box.gw / "requirements.txt").unlink()
    else:
        (box.gw / "requirements.txt").write_text(req)
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$? state=$HWAX_GW_VENV_STATE"; hwax_gw_venv_install; echo "irc=$?"')
    assert "rc=0 state=na" in r.stdout and "irc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
    assert "짓지 않는다" in r.stdout and box.calls_list() == []


def test_판이_맞으면_그대로_띄운다(box):
    box.venv(ALL_OK)
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$? state=$HWAX_GW_VENV_STATE"; hwax_gw_venv_install; echo "irc=$?"')
    assert "rc=0 state=ok" in r.stdout and "irc=0" in r.stdout and not r.stderr, r.stdout + r.stderr
    assert "✓ 게이트웨이 전용 venv 판 일치 — mcp 2.3.0" in r.stdout
    assert box.calls_list() == [], "판이 맞으면 Drive 를 묻지 않는다"


def test_venv_가_없으면_Drive_꾸러미로_짓는다(box):
    """성공 길 — 받기 · sha256 · 판 대조(prepare) → install.sh(install) → 지은 venv 의 판을 다시 맞댄다."""
    box.bundle()
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$? state=$HWAX_GW_VENV_STATE"; st="$HWAX_GW_VENV_STAGE"\n'
                  'hwax_gw_venv_install; echo "irc=$? state=$HWAX_GW_VENV_STATE"; [ -e "$st" ] && echo STAGE-LEFT || echo STAGE-GONE')
    out = r.stdout
    assert "rc=0 state=staged" in out and "irc=0 state=ok" in out and not r.stderr, out + r.stderr
    assert f"꾸러미 {_key()} 받음" in out and ".venv 가 없다" in out
    assert "✓ 게이트웨이 전용 venv 지음 — mcp 2.3.0" in out and "STAGE-GONE" in out
    calls = box.calls_list()
    assert calls[0].startswith("rclone lsf") and calls[1].startswith("rclone copy") and calls[2].startswith("install "), calls
    assert f"install {Path(calls[2].split()[1]).name} {box.py} GATEWAY_DIR={box.gw}" == calls[2], "받은 꾸러미 · 고른 파이썬 · 리포를 install.sh 에 준다"
    assert box.note() is None


def test_venv_판이_다르면_다시_짓는다(box):
    box.venv({**ALL_OK, "mcp": "2.2.0", "uvicorn": "-"})
    box.bundle()
    r = _lib(box, 'hwax_gw_venv_ensure; echo "rc=$?"')
    assert "rc=0" in r.stdout, r.stdout + r.stderr
    assert "판이 다르다(mcp 2.2.0→2.3.0, uvicorn 없음→0.54.0)" in r.stdout
    assert any(c.startswith("install ") for c in box.calls_list())


def test_꾸러미가_없으면_내리지_말라고_하고_사람_몫을_남긴다(box):
    """꾸러미 없음 — ✗ · 까닭 · 사람 몫(바깥에 닿는 박스에서 push-cmd 두 줄 · 같은 열쇠) · update-all 로 넘길 사유 파일. install 은 부르지 않는다."""
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$? state=$HWAX_GW_VENV_STATE"; hwax_gw_venv_install; echo "irc=$?"')
    out = r.stdout
    assert "rc=1 state=fail" in out and "irc=1" in out and not r.stderr, out + r.stderr
    line = next(ln for ln in out.splitlines() if "✗" in ln)
    assert "Drive 에 이 판의 꾸러미가 없다" in line and f"tools/gateway-wheels/{_key()}/" in line
    assert "게이트웨이를 다시 띄우지 않는다(떠 있는 옛 프로세스가 그대로 돈다)" in line
    human = next(ln for ln in out.splitlines() if "사람 몫:" in ln)
    assert f"push-cmd --python 3.12 --arch {ARCH}" in human and _key() in human and "update-sites.sh mcp-gateway" in human
    assert not any(c.startswith("install ") for c in box.calls_list())
    note = box.note()
    assert note and note.count("\t") == 1 and "꾸러미가 없다" in note.split("\t")[0] and "push-cmd" in note.split("\t")[1]


def test_꾸러미_판이_다르면_깔지_않는다(box):
    box.bundle(lock=["mcp==2.2.0", "httpx==0.28.1"])
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$?"')
    assert "rc=1" in r.stdout, r.stdout
    line = next(ln for ln in r.stdout.splitlines() if "✗" in ln)
    assert "Drive 꾸러미의 판이 이 게이트웨이 판과 다르다" in line and "mcp 2.3.0≠2.2.0" in line and "uvicorn 0.54.0≠없음" in line
    assert "다시 짓고 덮어 올린다" in r.stdout and not any(c.startswith("install ") for c in box.calls_list())


@pytest.mark.parametrize("kind", ["python", "arch", "sha", "nolock"])
def test_꾸러미가_이_박스와_어긋나면_깔지_않는다(box, kind):
    d = box.bundle(pyv="3.11" if kind == "python" else "3.12", arch="aarch64" if kind == "arch" else ARCH, bad_sha=kind == "sha",
                   key=_key())
    if kind == "nolock":
        (d / "requirements.lock").write_text("")
        sums = subprocess.run("sha256sum ./*.whl requirements.lock install.sh MANIFEST.txt | sed 's# \\./# #'", shell=True, cwd=d,
                              capture_output=True, text=True, check=True).stdout
        (d / "SHA256SUMS").write_text(sums)
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$?"')
    assert "rc=1" in r.stdout and not r.stderr, r.stdout + r.stderr
    want = {"python": "꾸러미 파이썬 3.11", "arch": "aarch64", "sha": "sha256 이 맞지 않는다", "nolock": "requirements.lock 없음"}[kind]
    assert want in r.stdout, r.stdout


def test_짓기가_실패하면_내리지_않는다(box):
    box.bundle()
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$?"; hwax_gw_venv_install; echo "irc=$? state=$HWAX_GW_VENV_STATE"', INSTALL_RC="1")
    out = r.stdout
    assert "rc=0" in out and "irc=1 state=fail" in out, out + r.stderr
    line = next(ln for ln in out.splitlines() if "✗ 게이트웨이 전용 venv" in ln)
    assert "venv 를 짓지 못했다(install.sh rc 1" in line and "되돌렸다" in line
    assert "gateway-venv.sh ensure" in out and "venv 짓기 실패 — 되돌린다" in out, "install.sh 의 출력을 그대로 보인다"


def test_지었는데_판이_다르면_실패다(box):
    box.bundle()
    r = _lib(box, 'hwax_gw_venv_prepare && { echo "mcp 2.0.0" > "' + str(box.vers) + '.over"; }\n'
                  f'sed -i "s#{box.vers}#{box.vers}.over#" "{box.tmp}/venv-python"\nhwax_gw_venv_install; echo "irc=$?"')
    assert "irc=1" in r.stdout and "지은 venv 의 판이 requirements.txt 와 다르다" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("case,want", [
    ("nopython", "파이썬 3.11 이상(venv · ensurepip 있음)이 아니다"),
    ("noremote", "HWAX_DRIVE_REMOTE 가 없어"),
    ("rclone_err", "Drive 를 읽지 못했다(rclone lsf rc 1"),
])
def test_받을_수_없으면_까닭을_가른다(box, case, want):
    env = {}
    if case == "nopython":
        env["GATEWAY_VENV_PYTHON"] = str(box.tmp / "no-such-python")
    elif case == "noremote":
        env["HWAX_DRIVE_REMOTE"] = ""
    else:
        env["RCLONE_LSF_RC"] = "1"
    box.bundle()
    r = _lib(box, 'hwax_gw_venv_prepare; echo "rc=$?"', **env)
    assert "rc=1" in r.stdout and want in r.stdout and "사람 몫:" in r.stdout and not r.stderr, r.stdout + r.stderr
    assert not any(c.startswith("install ") for c in box.calls_list())


def test_파이썬은_3_11_이상만_고른다(box, tmp_path):
    """GATEWAY_VENV_PYTHON 이 없으면 python3.12 · 3.13 · 3.11 · HEAXHub standalone · python3 가운데 3.11 이상(venv · ensurepip)의 첫 것 — 3.10 은 고르지
    않는다(mcp 2.x 의 httpx2 가 3.11 부터라 dev 와 판이 갈린다 — 게이트웨이 README)."""
    only = tmp_path / "only"; only.mkdir()
    (only / "python3").write_text("#!/usr/bin/env bash\nexit 3\n"); (only / "python3").chmod(0o755)   # 3.10 인 척 — 판 묻기에 3 으로 끝난다
    for t in ("bash", "sed", "awk", "sha256sum", "cut", "tail", "tr", "dirname", "head", "sort", "uname", "mktemp", "grep", "ls", "cp", "rm", "cat"):
        p = subprocess.run(["bash", "-c", f"command -v {t}"], capture_output=True, text=True).stdout.strip()
        if p:
            os.symlink(p, only / t)
    os.symlink(box.bin / "rclone", only / "rclone")
    env = box.env(GATEWAY_VENV_PYTHON="", PATH=str(only), HEAX_DIR=str(tmp_path / "no-heax"))   # 이 박스의 진짜 허브 파이썬이 끼지 않게
    r = _sh(f'set -uo pipefail\n. "{LIB}"\nhwax_gw_venv_prepare; echo "rc=$?"', env)
    assert "rc=1" in r.stdout and "venv 를 지을 파이썬 3.11 이상(venv · ensurepip 있음)을 찾지 못했다" in r.stdout, r.stdout + r.stderr
    (only / "python3.12").write_text(box.py.read_text()); (only / "python3.12").chmod(0o755)
    box.bundle()
    r = _sh(f'set -uo pipefail\n. "{LIB}"\nhwax_gw_venv_prepare; echo "rc=$? py=$HWAX_GW_VENV_PY"', env)
    assert f"rc=0 py={only}/python3.12" in r.stdout, r.stdout + r.stderr


def test_push_cmd_는_같은_열쇠로_짓기_올리기_두_줄을_낸다(box):
    r = subprocess.run(["bash", str(ROOT / "infra/scripts/gateway-venv.sh"), "push-cmd", "--python", "3.12", "--arch", ARCH],
                       capture_output=True, text=True, timeout=60, env=box.env())
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    assert _key() in lines[0]
    assert f"{box.gw}/tools/gateway-wheels/build.sh --python 3.12 --arch {ARCH} --out" in lines[1]
    assert lines[2].startswith(f'rclone sync "$O" "fake:HWAXPortal/tools/gateway-wheels/{_key()}/"'), lines[2]
    assert box.calls_list() == [], "명령만 찍는다 — 짓지도 올리지도 않는다"


# ── update-sites restart_svc — 내리기 전에 맞추고, 못 맞추면 내리지 않는다 ───────────────────────────────────────
LIBS = "".join(f'. "{LIBDIR}/{n}"\n' for n in ("change-detect.sh", "skip-ledger.sh", "delib-busy.sh", "llm-pool.sh", "gateway-venv.sh"))


def _restart_svc_block() -> str:
    i = UPDATE_SITES.index('SKIPPED_RESTART=""')
    return UPDATE_SITES[i:UPDATE_SITES.index("# 1) 포털 먼저", i)]


def _restart(box: Box, name: str = "mcp-gateway", extra: str = "", health: str = "", **env):
    st = box.tmp / "state"; st.mkdir(exist_ok=True)
    svc = box.tmp / "svc.sh"
    svc.write_text(f'#!/usr/bin/env bash\necho "svc $*" >> "{box.calls}"\n'
                   'case "$1" in update) echo "  · $2  updated";; fp) echo f-new;; status) echo "  ✓ up $2";; '
                   f'health) {"echo " + health if health else ":"};; enabled) exit 0;; esac\nexit 0\n')
    svc.chmod(0o755)
    script = (f'set -uo pipefail\nSVC="{svc}"\n{LIBS}{extra}\nexport HWAX_RESTART_STATE_DIR="{st}" HWAX_WAIT_DOWN_MAX=1 HWAX_WAIT_UP_MAX=1\n'
              f'show_cause() {{ :; }}\n{_restart_svc_block()}\nrestart_svc "{name}"; echo "rc=$?"; echo "DEFERRED=[$DEFERRED_RESTART]"')
    r = _sh(script, box.env(**env))
    state = (st / name).read_text().strip() if (st / name).exists() else None
    return r.stdout + r.stderr, box.calls_list(), state


def test_꾸러미가_없으면_게이트웨이를_내리지_않는다(box):
    """**이 시험이 이 갈래의 이유다** — down · up 이 불리지 않고, 지문도 적지 않는다(다음 실행이 다시 본다). 옛 프로세스가 그대로 돈다."""
    out, calls, state = _restart(box)
    assert "svc down mcp-gateway" not in calls and "svc up mcp-gateway" not in calls, calls
    assert state is None and "rc=1" in out, out
    assert "꾸러미가 없다" in out and "재기동하지 않는다 — 게이트웨이 전용 venv 가 서지 않았다" in out


def test_지을_수_있으면_내리기_바로_앞에_짓고_띄운다(box):
    box.bundle()
    out, calls, _ = _restart(box)
    assert "rc=0" in out or "svc up mcp-gateway" in calls, out
    i_inst = next(i for i, c in enumerate(calls) if c.startswith("install "))
    assert calls.index("svc update mcp-gateway") < calls.index(next(c for c in calls if c.startswith("rclone lsf"))) < i_inst \
        < calls.index("svc down mcp-gateway") < calls.index("svc up mcp-gateway"), calls
    assert "✓ 게이트웨이 전용 venv 지음" in out


def test_짓기가_실패하면_게이트웨이를_내리지_않는다(box):
    box.bundle()
    out, calls, state = _restart(box, INSTALL_RC="2")
    assert any(c.startswith("install ") for c in calls) and "svc down mcp-gateway" not in calls, calls
    assert state is None and "rc=1" in out and "venv 를 짓지 못했다" in out


def test_심의_때문에_재기동을_미루면_짓지_않고_받은_꾸러미를_버린다(box):
    """install.sh 는 있던 venv 를 비켜 둔다 — 재기동을 미룬 채 지으면 옛 프로세스가 비켜 난 venv 위에서 몇 시간 돈다."""
    box.bundle()
    stub = ('hwax_alive() { return 0; }\n'
            'hwax_delib_gate() { HWAX_DELIB_GATE_BUSY="1 0"; HWAX_DELIB_GATE_PROBE=0; return 3; }\n'
            f'hwax_gw_venv_discard() {{ [ -n "$HWAX_GW_VENV_STAGE" ] && echo "discard" >> "{box.calls}"; rm -rf "$HWAX_GW_VENV_STAGE"; HWAX_GW_VENV_STAGE=""; }}\n')
    # 게이트웨이는 update-all 아래(HWAX_DELIB_GATE)이고 살아 있을 때만 심의를 묻는다 — health url 을 하나 준다(답은 대역 hwax_alive)
    out, calls, state = _restart(box, extra=stub, health="http://127.0.0.1:1/health", HWAX_DELIB_GATE=str(box.tmp / "gate"))
    assert "DEFERRED=[ mcp-gateway]" in out, out
    assert "discard" in calls and not any(c.startswith("install ") for c in calls) and "svc down mcp-gateway" not in calls, calls


def test_다른_서비스는_게이트웨이_venv_를_보지_않는다(box):
    out, calls, _ = _restart(box, name="agent-server")
    assert not any(c.startswith(("rclone", "install")) for c in calls) and "게이트웨이 전용 venv" not in out, (calls, out)


def test_실제_실행이_lib_를_읽는다():
    """restart_svc · §5 · 자동 복구는 command -v 로 감싼다(떼어 도는 시험 사본은 lib 를 안 읽는다) — 그러니 실제 스크립트가 lib 를 읽는지 여기서 건다.
    안 읽으면 가드가 말없이 사라지고, SDK 2.x 판을 받은 박스에서 게이트웨이를 내린 뒤 못 띄운다."""
    assert '. "$ROOT/infra/scripts/lib/gateway-venv.sh"' in UPDATE_SITES
    assert '. "$SELF_REPO/infra/scripts/lib/gateway-venv.sh"' in UA
    r = subprocess.run(["bash", "-c", f'. "{LIB}"; for f in hwax_gw_venv_prepare hwax_gw_venv_install hwax_gw_venv_discard hwax_gw_venv_ensure '
                                      'hwax_gw_venv_note_take; do declare -F "$f" >/dev/null || echo "MISSING $f"; done'],
                       capture_output=True, text=True)
    assert r.stdout == "" and r.returncode == 0, r.stdout + r.stderr
    # 짓기는 내리기 바로 앞, 받기는 심의 기다림 앞이다
    blk = _restart_svc_block()
    assert blk.index("hwax_gw_venv_prepare") < blk.index("hwax_delib_gate ") < blk.index("hwax_gw_venv_install") < blk.index('"$SVC" down "$name"')


# ── update-all — §4 의 사유를 끝 요약에 · §5 · 자동 복구는 다시 띄우기 전에 ─────────────────────────────────────
def test_update_all_4_는_자식이_남긴_사유를_fail_로_싣는다(box, tmp_path):
    i = UA.index('"$SELF_REPO/infra/scripts/update-sites.sh" signalforge-mcp mcp-gateway agent-server; _us_rc=$?')
    block = UA[i:UA.index("\nfi\n", UA.index("hwax_gw_venv_note_take", i)) + 4]
    stub = tmp_path / "infra/scripts/update-sites.sh"; stub.parent.mkdir(parents=True)
    stub.write_text(f'#!/usr/bin/env bash\n. "{LIB}"\n_hwax_gw_venv_fail "Drive 에 이 판의 꾸러미가 없다(x)" "dev 에서 push-cmd" >/dev/null\nexit 1\n')
    stub.chmod(0o755)
    ledger = tmp_path / "ledger"; ledger.write_text("")
    r = _sh(f'set -uo pipefail\nSELF_REPO="{tmp_path}"\n. "{LIB}"\nfail() {{ echo "FAIL:$*"; }}\n{block}\necho end',
            {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "HWAX_SKIP_LEDGER": str(ledger)})
    fails = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    assert len(fails) == 2 and "end" in r.stdout and not r.stderr, r.stdout + r.stderr
    assert "게이트웨이를 다시 띄우지 않았다(옛 프로세스가 돈다) — 전용 venv: Drive 에 이 판의 꾸러미가 없다(x) · 사람 몫: dev 에서 push-cmd" in fails[1]
    assert not (tmp_path / "ledger.gw-venv").exists(), "꺼낸 사유는 지운다(다음 § 가 다시 세지 않게)"


def _section5_gate() -> str:
    i = UA.index('  _reprov_deferred=""')
    return UA[i:UA.index('  if [ -n "$MISSING" ]; then\n    echo "  · config에 없거나', i)]


def test_update_all_5_는_venv_가_서지_않으면_재프로비저닝을_통째로_미룬다(box):
    """재프로비저닝은 게이트웨이 재기동까지 한 벌 — config 만 고치고 재기동을 빼면 떠 있는 프로세스와 파일이 갈린다. provision 보다 먼저 본다."""
    assert UA.index("hwax_gw_venv_ensure \"${GW_DIR:-}\"") < UA.index('if ( cd "$GW_DIR" && export PER_USER_SSO_APPS ')
    gate = _section5_gate()
    r = _sh(f'set -uo pipefail\n{LIBS}fail() {{ echo "FAIL:$*"; }}\nGW_DIR="{box.gw}"; MISSING="arp"\n{gate}\n'
            'printf "MISSING=[%s] DEFERRED=[%s]\\n" "$MISSING" "$_reprov_deferred"', box.env(AGENT_RESTART_FORCE="1"))
    assert "MISSING=[] DEFERRED=[arp]" in r.stdout and not r.stderr, r.stdout + r.stderr
    f = next(ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:"))
    assert "재프로비저닝을 이번 실행에서 하지 않았다(arp)" in f and "꾸러미가 없다" in f and "사람 몫:" in f
    box.venv(ALL_OK)
    r = _sh(f'set -uo pipefail\n{LIBS}fail() {{ echo "FAIL:$*"; }}\nGW_DIR="{box.gw}"; MISSING="arp"\n{gate}\n'
            'printf "MISSING=[%s] DEFERRED=[%s]\\n" "$MISSING" "$_reprov_deferred"', box.env(AGENT_RESTART_FORCE="1"))
    assert "MISSING=[arp] DEFERRED=[]" in r.stdout and "FAIL:" not in r.stdout, r.stdout + r.stderr


def test_자동_복구는_venv_가_서지_않으면_게이트웨이를_죽이지_않는다(box):
    """repair_mcp 는 포트 점유자를 kill 한 뒤 start.sh --bg 다 — venv 가 없으면 start.sh 가 띄우지 않아 게이트웨이가 통째로 내려간다."""
    i = UA.index("repair_mcp() {")
    fn = UA[i:UA.index("\n}\n", i) + 3]
    for name in ("sync-provision-env.sh", "provision-config.sh", "start.sh"):
        (box.gw / name).write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "{box.calls}"\n'); (box.gw / name).chmod(0o755)
    (box.gw / "gateway_config.json").write_text(json.dumps({"_gateway": {"port": 1}}))
    script = (f'set -uo pipefail\n{LIBS}fail() {{ echo "FAIL:$*"; }}\nhwax_delib_busy() {{ return 1; }}\nGW_DIR="{box.gw}"\n{fn}\n'
              'rc=0; repair_mcp || rc=$?; echo "RC=$rc"')
    r = _sh(script, box.env())
    assert "RC=1" in r.stdout, r.stdout + r.stderr
    assert not any(c.split()[0] in ("sync-provision-env.sh", "provision-config.sh", "start.sh") for c in box.calls_list()), box.calls_list()
    assert any(ln.startswith("FAIL:MCP 자동 복구(재프로비저닝 → 게이트웨이 재기동)를 하지 않았다") for ln in r.stdout.splitlines()), r.stdout
