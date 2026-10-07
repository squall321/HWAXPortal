# 내부 목적지가 사내 프록시로 새지 않는지 — check-egress.sh --internal 과 그것을 부르는 update-all §6 의 경고(9차 요청 §4-(4))
"""왜 — check-egress.sh 는 NO_PROXY 에 루프백 둘만 있는지 봤고, 그나마 아무도 부르지 않았다. 이 박스가 실제로 부르는 내부
목적지(RA·ARP·라우트의 원격 호스트·TestScope)가 NO_PROXY 에 없으면 그 호출만 프록시를 타고 상대의 IP 허용목록에 걸린다 —
기능 하나가 403 인데 게이트는 전부 초록이다(RA 사람별 위임, 2026-10-03 실측).

지키는 것.
 ① 목적지는 **리포가 아는 설정에서 유도한다**(infra/.env · routes(.local).env · backend/.env) — 주소를 스크립트에 적지 않는다.
 ② `--internal` 은 **네트워크를 건드리지 않는다** — update-all 이 매 실행 부르므로 멈출 일이 없어야 한다.
 ③ 주소·프록시 값은 찍지 않는다(프록시 주소에는 계정이 섞여 있을 수 있다) — 어느 설정인지 이름으로만 말한다.
 ④ update-all 에서는 **경고**다 — 종료코드를 세우지 않는다.
스크립트는 사본을 임시 리포에 놓고 실제로 돌린다. 주소는 문서용 예약 대역(TEST-NET)만 쓴다.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
PROXY = "http://svc-user:pw-not-real@proxy.example:8080"
RA, ARP, ODB, TS = "203.0.113.10", "203.0.113.20", "203.0.113.30", "198.51.100.40"


@pytest.fixture()
def box(tmp_path):
    """임시 리포 — RA·ARP(infra/.env) · 원격 라우트 하나(odb-hub) · TestScope(backend/.env) 를 아는 박스."""
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True); (repo / "backend/config").mkdir(parents=True)
    shutil.copy(ROOT / "infra/scripts/check-egress.sh", repo / "infra/scripts/check-egress.sh")
    (repo / "infra/.env").write_text(f"HTTP_PORT=8088\nRA_HOST={RA}   # RA 주(A)\nARP_HOST={ARP}\n")
    (repo / "backend/.env").write_text(f'TESTSCOPE_BASE_URL="http://{TS}:8020/"   # 그쪽 웹\n')
    (repo / "backend/config/routes.env").write_text(
        "# 예시:  heax-hub=http://192.0.2.99:4180\nheax-hub=http://localhost:4180/\nai-data-hub=http://127.0.0.1:8001/\n"
        "ste=http://192.0.2.50:15810/\n")
    (repo / "backend/config/routes.local.env").write_text(
        f"ste=\nreport-archive=http://{RA}:3000/\nodb-hub=http://{ODB}:8000/\n#aireadyportal=http://192.0.2.77:3001\n")
    # curl·openssl 이 불리면 표식이 남는다 — --internal 은 네트워크를 건드리지 않아야 한다
    shim = tmp_path / "shim"; shim.mkdir()
    for name in ("curl", "openssl"):
        (shim / name).write_text(f'#!/usr/bin/env bash\necho {name} >> "{tmp_path}/net.calls"\necho 200\n'); (shim / name).chmod(0o755)

    def run(*args: str, **env) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(repo / "infra/scripts/check-egress.sh"), *args], capture_output=True, text=True,
                              timeout=60, env={"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(tmp_path), **env})
    return repo, run, tmp_path / "net.calls"


ALL = f"127.0.0.1,localhost,{RA},{ARP},{ODB},{TS}"


def test_프록시가_없는_박스는_볼_것이_없다(box):
    """dev 는 직결이다 — 경고도 네트워크 호출도 없다."""
    _, run, calls = box
    r = run("--internal")
    assert r.returncode == 0 and "직결" in r.stdout, r.stdout + r.stderr
    assert not calls.exists()


def test_전부_NO_PROXY_에_있으면_통과하고_네트워크를_건드리지_않는다(box):
    _, run, calls = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY=ALL)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not calls.exists(), "--internal 이 curl·openssl 을 불렀다 — update-all 이 매 실행 부르는 자리다"


def test_빠진_목적지를_설정_이름으로_말하고_주소는_찍지_않는다(box):
    """**이 시험이 #19 의 이유다** — 종전엔 루프백 둘만 봐서 RA 가 빠져 있어도 조용했다."""
    _, run, calls = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY="127.0.0.1,localhost")
    assert r.returncode == 1, r.stdout + r.stderr
    for label in ("RA_HOST", "ARP_HOST", "라우트 odb-hub", "TESTSCOPE_BASE_URL"):
        assert label in r.stdout, r.stdout
    out = r.stdout + r.stderr
    for secret in (RA, ARP, ODB, TS, "pw-not-real", "proxy.example"):
        assert secret not in out, f"주소·프록시 값이 출력에 샜다: {secret}"
    assert not calls.exists()


def test_라우트는_원격_호스트만_본다_루프백_주석_끈_라우트는_뺀다(box):
    """루프백 라우트는 프록시와 무관하고, routes.local.env 의 `ste=`(빈 값)는 추적 파일의 ste 를 이 박스에서 끈 것이다."""
    _, run, _ = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY=f"{RA},{ARP},{TS}")
    assert r.returncode == 1 and "라우트 odb-hub" in r.stdout
    for not_a_dest in ("heax-hub", "ai-data-hub", "ste", "aireadyportal", "report-archive"):
        assert not_a_dest not in r.stdout, f"{not_a_dest} 는 볼 목적지가 아니다(report-archive 는 RA_HOST 와 같은 호스트다): {r.stdout}"


@pytest.mark.parametrize("np_list,covered", [
    (ALL, True),
    ("*", True),                                                     # 전부 우회
    ("203.0.113.0/24, 198.51.100.0/24", False),                      # 대역 — httpx 는 슬래시 앞 한 주소로만 읽는다(9차 §5 · D-9)
    (f"{RA} , {ARP},\t{ODB}, {TS}", True),                           # 쉼표 둘레의 공백은 뗀다
    (f"{RA} {ARP} {ODB} {TS}", False),                               # 공백으로만 나누면 httpx 는 통째로 한 항목으로 읽는다
    (f"{RA}/32,{ARP}/24,{ODB}/8,{TS}/16", True),                     # 슬래시 앞이 그 주소 자신이면 덮인다(httpx 가 그렇게 읽는다)
    (f"{RA}:3000,{ARP},{ODB},{TS}", False),                          # RA_HOST 한 줄에서 :3000·:3002 두 주소가 나온다 — 포트 하나로는 못 덮는다
    (f"{RA},{ARP},{ODB}:8000,{TS}:8020", True),                      # 포트가 붙은 항목은 설정이 적은 그 포트만 덮는다
    (f"{RA},{ARP},{ODB}:9999,{TS}", False),                          # 다른 포트
    (f"{RA},{ARP},{ODB},{TS}:9999", False),
    ("203.0.113.0/28,198.51.100.40", False),                         # 대역 안에 있어도(RA 는 .10) 덮이지 않는다
    (f"113.10,{ARP},{ODB},{TS}", False),                             # IP 는 꼬리 일치로 보지 않는다
    (f"{RA},{ARP},{ODB}", False),                                    # TestScope 가 빠졌다
])
def test_NO_PROXY_가_받는_모양(box, np_list, covered):
    """서비스가 부를 때 쓰는 httpx 가 읽는 대로만 덮인 것으로 본다 — 초록이 거짓이면 이 점검은 없느니만 못하다. 종전엔 대역 안의
    주소를 덮였다고 봤는데, httpx 0.28.1 은 대역을 한 주소로만 읽어 그 호출이 프록시로 샜다(운영자 셸이 /24 인 박스가 초록이었다)."""
    _, run, _ = box
    r = run("--internal", http_proxy=PROXY, NO_PROXY=np_list)
    assert (r.returncode == 0) is covered, (np_list, r.stdout, r.stderr)


def test_호스트명은_도메인_꼬리로도_덮인다(box):
    repo, run, _ = box
    (repo / "infra/.env").write_text("RA_HOST=ra-a.corp.example\nARP_HOST=ARP.Corp.Example\n")
    (repo / "backend/.env").write_text("")
    (repo / "backend/config/routes.local.env").write_text("")
    (repo / "backend/config/routes.env").write_text("")
    assert run("--internal", https_proxy=PROXY, NO_PROXY=".corp.example").returncode == 0
    assert run("--internal", https_proxy=PROXY, NO_PROXY="corp.example").returncode == 0
    r = run("--internal", https_proxy=PROXY, NO_PROXY="*.corp.example")
    assert r.returncode == 1 and "RA_HOST" in r.stdout, "`*.도메인` 은 httpx 가 별표를 글자로 읽어 아무것도 덮지 않는다"
    assert run("--internal", https_proxy=PROXY, NO_PROXY="ra-a.corp.example,arp.corp.example").returncode == 0
    r = run("--internal", https_proxy=PROXY, NO_PROXY="rp.example,other.example")
    assert r.returncode == 1 and "RA_HOST" in r.stdout and "ARP_HOST" in r.stdout, "점 경계가 아닌 꼬리는 덮지 않는다"
    (repo / "infra/.env").write_text("RA_HOST=corp.example\n")
    assert run("--internal", https_proxy=PROXY, NO_PROXY="corp.example").returncode == 0
    assert run("--internal", https_proxy=PROXY, NO_PROXY=".corp.example").returncode == 1, "`.도메인` 은 하위만 덮는다(자신은 아니다)"


def test_소문자_no_proxy_만_둔_박스도_읽는다(box):
    _, run, _ = box
    assert run("--internal", https_proxy=PROXY, no_proxy=ALL).returncode == 0


def test_두_철자가_다르면_소문자로_판정하고_다르다고_말한다(box):
    """파이썬(urllib·httpx)과 curl 은 소문자를 먼저 읽는다. 종전엔 대문자를 먼저 읽어, 손으로 돌릴 때 두 값이 다르면 서비스가
    읽는 것과 다른 목록으로 판정했다(update-all 안에서는 두 철자를 같게 맞춰 두므로 그 게이트의 출력은 그대로다)."""
    _, run, _ = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY=ALL, no_proxy="127.0.0.1")
    assert r.returncode == 1 and "RA_HOST" in r.stdout and "no_proxy" in r.stderr, r.stdout + r.stderr
    assert len(r.stdout.strip().splitlines()) == 1, "stdout 은 한 줄 그대로다 — 다르다는 말은 stderr 로"
    for secret in (RA, ARP, ODB, TS, "127.0.0.1"):
        assert secret not in r.stderr, "값은 찍지 않는다"
    assert run("--internal", https_proxy=PROXY, NO_PROXY="127.0.0.1", no_proxy=ALL).returncode == 0
    # 파이썬은 '있지만 빈' 소문자가 대문자를 지운다
    assert run("--internal", https_proxy=PROXY, NO_PROXY=ALL, no_proxy="").returncode == 1
    same = run("--internal", https_proxy=PROXY, NO_PROXY=ALL, no_proxy=ALL)
    assert same.returncode == 0 and same.stderr == "", "같으면 조용하다"
    full = run(https_proxy=PROXY, NO_PROXY=ALL, no_proxy="127.0.0.1", EGRESS_TIMEOUT="2")
    assert "no_proxy" in full.stdout and "RA_HOST" in full.stdout, "전체 진단도 소문자로 판정하고 다르다고 말한다"


def test_설정_파일이_없는_박스에서도_죽지_않는다(box):
    repo, run, _ = box
    for f in ("infra/.env", "backend/.env", "backend/config/routes.env", "backend/config/routes.local.env"):
        (repo / f).unlink()
    r = run("--internal", https_proxy=PROXY, NO_PROXY="127.0.0.1")
    assert r.returncode == 0 and "unbound variable" not in r.stderr, r.stdout + r.stderr


def test_env_독자는_update_all_의_정본과_같게_읽는다(box):
    """일치 시험은 둘 다 틀리면 통과한다 — 정본(update-all `_envfile_value`)을 오라클로 댄다."""
    repo, _, _ = box
    src = (repo / "infra/scripts/check-egress.sh").read_text(encoding="utf-8")
    mine = src[src.index("envv() {"):]; mine = mine[:mine.index("\n") + 1]
    canon = UA[UA.index("_envfile_value() {"):]; canon = canon[:canon.index("\n}\n") + 3]
    f = repo / "probe.env"
    f.write_text('A=x   # 설명\nexport B="y"\nC=   # 값 없이 주석만\n# D=주석\nE=1\nE=2\r\n')
    for k in "ABCDE":
        r = subprocess.run(["bash", "-c", f'{mine}{canon}\nprintf "[%s]|[%s]" "$(envv {k} "{f}")" "$(_envfile_value "{f}" {k})"'],
                           capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
        a, b = r.stdout.split("|")
        assert a == b, (k, r.stdout, r.stderr)
    assert r.stdout == "[2]|[2]"


def test_전체_진단에서도_내부_목적지를_본다(box):
    """사람이 손으로 돌리는 전체 진단(네트워크 프로브 포함 — 여기서는 대역이 답한다)도 같은 목록을 본다."""
    _, run, calls = box
    r = run(https_proxy=PROXY, NO_PROXY="127.0.0.1,localhost", EGRESS_TIMEOUT="2")
    assert r.returncode == 0, r.stderr
    assert "RA_HOST" in r.stdout and "라우트 odb-hub" in r.stdout and RA not in r.stdout
    assert calls.exists(), "전체 진단은 종전대로 바깥을 찔러 본다"


# ── update-all §6 — 경고로만 부른다 ───────────────────────────────────────────
def _gate_block() -> str:
    i = UA.index("# ── 내부 목적지가 프록시를 타지 않는가")
    return UA[i:UA.index("# 절차 모듈 — 상태코드로는 못 본다", i)]


def _gate(repo: Path, **env) -> str:
    script = "\n".join([
        "set -uo pipefail", "FAIL=0",
        'ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
        'hwax_skip() { echo "SKIP:$1"; }', f'SELF_REPO="{repo}"', _gate_block(), 'echo "FAIL=$FAIL"',
    ])
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(repo.parent), **env})
    assert r.returncode == 0 and "unbound variable" not in r.stderr, r.stderr
    return r.stdout


def test_update_all_은_빠진_목적지를_경고로_말하고_실패로_세지_않는다(box):
    repo, _, _ = box
    out = _gate(repo, https_proxy=PROXY, NO_PROXY=f"127.0.0.1,localhost,{RA},{ARP}")
    line = [ln for ln in out.splitlines() if ln.startswith("BAD:")]
    assert len(line) == 1 and "라우트 odb-hub" in line[0] and "TESTSCOPE_BASE_URL" in line[0], out
    assert "RA_HOST" not in line[0], "1g 가 더한 것은 빠졌다고 하지 않는다"
    assert "FAIL=0" in out and "FAIL:" not in out, "경고다 — 종료코드를 세우지 않는다"
    assert ODB not in out and TS not in out and "pw-not-real" not in out


def test_update_all_은_다_있으면_초록_한_줄이다(box):
    repo, _, _ = box
    out = _gate(repo, https_proxy=PROXY, NO_PROXY=ALL)
    assert out.startswith("OK:프록시 우회") and "BAD:" not in out and "FAIL=0" in out, out
    assert _gate(repo).startswith("OK:프록시 우회"), "프록시가 없는 박스(dev)도 초록이다"


def test_update_all_은_점검이_깨져도_실패로_세지_않는다(box):
    """점검 스크립트가 죽거나 없어도 배포 판정을 흔들지 않는다."""
    repo, _, _ = box
    (repo / "infra/scripts/check-egress.sh").write_text("#!/usr/bin/env bash\nexit 7\n")
    out = _gate(repo)
    assert "BAD:프록시 우회" in out and "FAIL=0" in out and "FAIL:" not in out, out
    (repo / "infra/scripts/check-egress.sh").unlink()
    out = _gate(repo)
    assert "SKIP:프록시 우회 점검" in out and "FAIL=0" in out, out


# ── httpx 가 읽지 않는 NO_PROXY 항목(대역 · `*.도메인` · 공백으로 나눈 항목) — 9차 §5 · docs/change-request-8-10 D-9 ──────────
CIDRS = "127.0.0.1,localhost,203.0.113.0/24,198.51.100.0/24"


def test_대역으로만_덮인_목적지는_빠졌다고_하고_대역이_죽은_값이라고_알린다(box):
    """**이 구획의 이유다** — 운영자 셸의 NO_PROXY 가 /24 인 박스(9차 §5)에서 이 점검이 '전부 NO_PROXY 에 있다' 초록이었다.
    같은 값으로 httpx 는 그 대역의 호스트를 프록시로 보낸다(대역의 첫 주소 하나만 직결). 빠졌다고만 하면 운영자는 NO_PROXY 에
    대역이 있는 것을 보고 점검이 틀렸다고 읽는다 — 그 항목이 왜 안 듣는지를 같은 줄에서 말한다."""
    _, run, calls = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY=CIDRS)
    assert r.returncode == 1, r.stdout + r.stderr
    for label in ("RA_HOST", "ARP_HOST", "라우트 odb-hub", "TESTSCOPE_BASE_URL"):
        assert label in r.stdout, r.stdout
    assert "대역" in r.stdout and "2개" in r.stdout and "httpx" in r.stdout, r.stdout
    assert len(r.stdout.strip().splitlines()) == 1, "update-all 이 이 한 줄을 그대로 싣는다"
    for secret in (RA, ARP, ODB, TS, "203.0.113.0", "198.51.100.0", "/24", "pw-not-real"):
        assert secret not in r.stdout + r.stderr, f"주소·대역이 출력에 샜다: {secret}"
    assert not calls.exists()


def test_글자_그대로_다_있으면_초록이고_죽은_항목은_같이_알린다(box):
    _, run, _ = box
    r = run("--internal", https_proxy=PROXY, NO_PROXY=ALL + ",203.0.113.0/24,*.corp.example")
    assert r.returncode == 0 and "전부 NO_PROXY 에 있다" in r.stdout and "2개" in r.stdout and "httpx" in r.stdout, r.stdout
    r = run("--internal", https_proxy=PROXY, NO_PROXY=ALL + f",{RA}/32")
    assert r.returncode == 0 and "httpx" not in r.stdout, "/32 는 그 주소 하나로 읽힌다 — 죽은 값이 아니다"
    r = run("--internal", https_proxy=PROXY, NO_PROXY=ALL)
    assert r.returncode == 0 and "httpx" not in r.stdout, "죽은 항목이 없으면 안내도 없다"


def test_전체_진단도_죽은_항목을_경고한다(box):
    _, run, _ = box
    r = run(https_proxy=PROXY, NO_PROXY=CIDRS, EGRESS_TIMEOUT="2")
    assert "httpx" in r.stdout and "2개" in r.stdout and "TESTSCOPE_BASE_URL" in r.stdout, r.stdout
    assert "httpx" not in run(https_proxy=PROXY, NO_PROXY=ALL, EGRESS_TIMEOUT="2").stdout


def test_update_all_은_대역으로만_덮인_박스를_초록으로_보지_않는다(box):
    """1g 가 RA·ARP 를 글자 그대로 더한 뒤의 모양 — 나머지(라우트·TestScope)는 운영자의 대역뿐이다."""
    repo, _, _ = box
    out = _gate(repo, https_proxy=PROXY, NO_PROXY=f"{CIDRS},{RA},{ARP}")
    (line,) = [ln for ln in out.splitlines() if ln.startswith("BAD:")]
    assert "라우트 odb-hub" in line and "TESTSCOPE_BASE_URL" in line and "RA_HOST" not in line and "대역" in line, out
    assert "FAIL=0" in out and "203.0.113.0" not in out and ODB not in out


def _httpx_direct(monkeypatch, np: str, url: str) -> bool:
    """같은 NO_PROXY 로 httpx 가 그 주소를 직결로 부르는가 — 네트워크는 건드리지 않는다(어느 전송을 고르는지만 본다)."""
    import httpx

    for k in ("NO_PROXY", "no_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:8080")
    monkeypatch.setenv("NO_PROXY", np)
    with httpx.Client() as c:
        return c._transport_for_url(httpx.URL(url)) is c._transport


def _one_dest(box, host: str):
    repo, run, _ = box
    (repo / "infra/.env").write_text(f"RA_HOST={host}\n")
    for f in ("backend/.env", "backend/config/routes.env", "backend/config/routes.local.env"):
        (repo / f).write_text("")
    return run


@pytest.mark.parametrize("entry,host", [
    ("203.0.113.0/24", "203.0.113.10"), ("203.0.113.0/24", "203.0.113.0"), ("203.0.113.10/32", "203.0.113.10"),
    ("203.0.113.10", "203.0.113.10"), ("203.0.113.1", "203.0.113.10"),
    ("*.corp.example", "ra.corp.example"), ("*corp.example", "ra.corp.example"),
    (".corp.example", "ra.corp.example"), (".corp.example", "corp.example"),
    ("corp.example", "ra.corp.example"), ("corp.example", "corp.example"), ("rp.example", "ra.corp.example"),
    ("CORP.Example", "ra.corp.example"), ("corp.example.", "ra.corp.example"),
    ("*", "203.0.113.10"), ("other.example,*", "ra.corp.example"),
    (" 203.0.113.10 ", "203.0.113.10"), ("203.0.113.10 203.0.113.20", "203.0.113.10"),
])
def test_판정이_httpx_가_실제로_고르는_길과_같다(box, monkeypatch, entry, host):
    """일치 시험은 둘 다 틀리면 통과한다 — 서비스가 실제로 쓰는 httpx 를 오라클로 댄다. 스크립트와 이 파일의 기대표가 같은
    오해(대역은 덮는다)를 나눠 가져 초록이었다."""
    run = _one_dest(box, host)
    np = f"127.0.0.1,localhost,{entry}"
    covered = run("--internal", https_proxy=PROXY, NO_PROXY=np).returncode == 0
    direct = _httpx_direct(monkeypatch, np, f"http://{host}:3000/")
    assert covered == direct, (f"NO_PROXY 항목 {entry!r} · 호스트 {host!r} — 점검은 {'덮였다' if covered else '빠졌다'}, "
                               f"httpx 는 {'직결' if direct else '프록시'}")


@pytest.mark.parametrize("entry,host", [("113.10", "203.0.113.10"), ("corp.example/24", "ra.corp.example")])
def test_드문_모양은_빠졌다고_보는_쪽으로_틀린다(box, monkeypatch, entry, host):
    """httpx 는 이런 항목도 꼬리 일치로 받는다. 점검은 받지 않는다 — 일부러 적을 모양이 아니고, 틀려도 '덮였다' 쪽으로는 틀리지 않는다."""
    run = _one_dest(box, host)
    np = f"127.0.0.1,localhost,{entry}"
    assert run("--internal", https_proxy=PROXY, NO_PROXY=np).returncode == 1
    assert _httpx_direct(monkeypatch, np, f"http://{host}:3000/") is True


# ── 포트가 붙은 항목 — httpx 는 그 포트만 우회한다 ───────────────────────────────────────────
@pytest.mark.parametrize("ts_url,entry", [
    (f"http://{TS}:8020/", f"{TS}:8020"), (f"http://{TS}:8020/", f"{TS}:9999"), (f"http://{TS}:8020/", TS),
    (f"http://{TS}/", f"{TS}:80"), (f"http://{TS}:80/", f"{TS}:80"), (f"https://{TS}/", f"{TS}:443"),
    (f"https://{TS}:443/", f"{TS}:443"), (f"https://{TS}:8443/", f"{TS}:8443"), (f"http://{TS}:443/", f"{TS}:443"),
    ("http://ts.corp.example:8020/", "corp.example:8020"), ("http://ts.corp.example:8020/", "corp.example:1"),
])
def test_포트_판정이_httpx_가_실제로_고르는_길과_같다(box, monkeypatch, ts_url, entry):
    """종전엔 항목의 포트를 떼고 호스트만 맞췄다 — `<호스트>:9999` 가 :8020 으로 가는 호출도 덮었다고 봤다. httpx 는 그 포트만
    우회하고, 기본 포트(http 80 · https 443)는 '포트 없음' 으로 다뤄 `:80` 항목은 아무것도 덮지 않는다."""
    repo, run, _ = box
    (repo / "infra/.env").write_text("")
    (repo / "backend/config/routes.env").write_text("")
    (repo / "backend/config/routes.local.env").write_text("")
    (repo / "backend/.env").write_text(f"TESTSCOPE_BASE_URL={ts_url}\n")
    np = f"127.0.0.1,localhost,{entry}"
    covered = run("--internal", https_proxy=PROXY, NO_PROXY=np).returncode == 0
    direct = _httpx_direct(monkeypatch, np, ts_url)
    assert covered == direct, f"항목 {entry!r} · 목적지 {ts_url} — 점검은 {'덮였다' if covered else '빠졌다'}, httpx 는 {'직결' if direct else '프록시'}"


def test_한_호스트를_두_포트로_부르면_포트_붙은_항목_하나로는_덮이지_않는다(box):
    """라우트와 TestScope 가 같은 호스트의 다른 포트다 — 어느 포트 하나를 적은 항목은 다른 쪽 호출을 못 덮는다."""
    repo, run, _ = box
    (repo / "infra/.env").write_text("")
    (repo / "backend/config/routes.env").write_text("")
    (repo / "backend/config/routes.local.env").write_text(f"odb-hub=http://{ODB}:8000/\n")
    (repo / "backend/.env").write_text(f"TESTSCOPE_BASE_URL=http://{ODB}:8020/\n")
    assert run("--internal", https_proxy=PROXY, NO_PROXY=f"{ODB}:8000").returncode == 1
    assert run("--internal", https_proxy=PROXY, NO_PROXY=ODB).returncode == 0
    (repo / "backend/.env").write_text(f"TESTSCOPE_BASE_URL=http://{ODB}:8000/api\n")
    assert run("--internal", https_proxy=PROXY, NO_PROXY=f"{ODB}:8000").returncode == 0, "같은 포트면 한 항목으로 덮인다"
