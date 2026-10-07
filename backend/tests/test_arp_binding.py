# ARP_HOST 한 줄로 게이트웨이 ARP_BASE 를 맞춘다(타일은 routes.local.env 의 aireadyportal=, 2026-10-07) — update-all 1f·§5 드리프트(docs/arp-binding)
#
# 주소는 문서용 예약 대역(TEST-NET)만 쓴다 — 이 리포는 GitHub 에 있다.
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    i = UA.index(f"{name}() {{")
    return UA[i:UA.index("\n}\n", i) + 3]


def _block(start: str, end: str) -> str:
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


STUBS = "\n".join([
    'ok() { echo "OK:$*"; }', 'bad() { echo "BAD:$*"; }', 'fail() { echo "FAIL:$*"; }', 'hr() { echo "HR:$*"; }',
    'hwax_skip() { echo "SKIP:$1"; }',
])


@pytest.fixture()
def box(tmp_path):
    repo = tmp_path / "HWAXPortal"
    (repo / "infra").mkdir(parents=True)
    (repo / "backend/config").mkdir(parents=True)
    gw = tmp_path / "HWAXMcpGateway"; gw.mkdir()

    def run(env_text: str) -> str:
        (repo / "infra/.env").write_text(env_text)
        script = "\n".join(["set -uo pipefail", STUBS, _fn("_envfile_value"), _fn("_ra_envv"), _fn("_upsert_kv"),
                            f'SELF_REPO="{repo}"', f'GW_DIR="{gw}"', f'ROUTES_ENV="{repo}/backend/config/routes.env"',
                            _block("# ── 1f) AI Ready Portal(ARP) 연결", "# ── 2) 전 서비스 배포")])
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                           env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
        assert r.returncode == 0, r.stderr
        return r.stdout
    return repo, gw, run


def test_한_줄로_게이트웨이를_적고_타일_덮어쓰기는_안_쓴다(box):
    repo, gw, run = box
    out = run("ARP_HOST=203.0.113.20\n")
    assert (gw / "provision.env").read_text().strip() == "ARP_BASE=http://203.0.113.20:3001"
    assert stat.S_IMODE((gw / "provision.env").stat().st_mode) == 0o600, "게이트웨이 provision.env 는 비밀 파일이다"
    assert "systems.local.yaml 에 쓰지 않는다" in out
    assert not (repo / "backend/config/systems.local.yaml").exists()


def test_손으로_둔_타일_덮어쓰기를_건드리지_않는다(box):
    """systems.local.yaml 은 재기동 지문에 들어 있다 — 1f 가 건드리면 포털이 괜히 재기동한다."""
    repo, gw, run = box
    f = repo / "backend/config/systems.local.yaml"
    f.write_text("# 손으로 만든 머리\nodb-hub:\n  url: http://198.51.100.2:8000/\n")
    before, mtime = f.read_text(), f.stat().st_mtime_ns
    run("ARP_HOST=203.0.113.20\nARP_PORT=4001\n")
    assert f.read_text() == before and f.stat().st_mtime_ns == mtime
    assert (gw / "provision.env").read_text().strip() == "ARP_BASE=http://203.0.113.20:4001"


@pytest.mark.parametrize("host", ["http://203.0.113.20", "localhost", "127.0.0.1", "203.0.113.20/x", "-bad"])
def test_주소가_아닌_값은_막고_아무것도_안_쓴다(box, host):
    repo, gw, run = box
    out = run(f"ARP_HOST={host}\n")
    assert "FAIL:ARP_HOST" in out
    assert not (repo / "backend/config/systems.local.yaml").exists() and not (gw / "provision.env").exists()


def test_포트가_숫자가_아니면_막는다(box):
    repo, gw, run = box
    out = run("ARP_HOST=203.0.113.20\nARP_PORT=30a1\n")
    assert "FAIL:ARP_HOST" in out and not (gw / "provision.env").exists()


def test_없으면_손으로_둔_그대로_쓰고_안_켠_기능으로_남긴다(box):
    repo, gw, run = box
    f = repo / "backend/config/systems.local.yaml"
    f.write_text("arp:\n  url: http://198.51.100.1:3001/\n")
    out = run("# ARP_HOST=\n")
    assert "SKIP:AI Ready Portal 주소 묶기" in out
    assert f.read_text() == "arp:\n  url: http://198.51.100.1:3001/\n" and not (gw / "provision.env").exists()


# ── 타일 라우트 — ARP 주소는 두 곳에 있다(infra/.env 의 ARP_HOST · 라우트 파일의 aireadyportal=) ─────────────
# 1f 는 라우트를 적지 않는다(손으로 적는다). 그래서 한쪽만 고치거나 라우트를 빼먹을 수 있고, 둘 다 오류 없이 지나간다 —
# 라우트가 없으면 포털이 타일을 숨기고(ARP 를 붙인 박스인데 타일만 안 보인다), 다르면 타일과 챗의 ARP 도구가 서로 다른 서버를 본다.
def _routes(repo, *, local: str | None = None, base: str | None = None) -> None:
    for name, text in (("routes.local.env", local), ("routes.env", base)):
        f = repo / "backend/config" / name
        if text is None:
            f.unlink(missing_ok=True)
        else:
            f.write_text(text)


def _bad(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("BAD:")]


def test_타일_라우트가_없으면_알린다(box):
    repo, _gw, run = box
    (warn,) = _bad(run("ARP_HOST=203.0.113.20\n"))
    assert "aireadyportal=" in warn and "routes.local.env" in warn, "무엇을 어디에 적는지 말한다"
    _routes(repo, local="# aireadyportal=http://203.0.113.20:3001/\nste=http://198.51.100.7:15810/\n")
    assert len(_bad(run("ARP_HOST=203.0.113.20\n"))) == 1, "주석 줄은 라우트가 아니다"


@pytest.mark.parametrize("route", ["http://203.0.113.20:3001/", "http://203.0.113.20:3001", "  http://203.0.113.20:3001/  ",
                                   "https://203.0.113.20/"])
def test_타일_라우트가_같은_서버를_가리키면_조용하다(box, route):
    repo, _gw, run = box
    _routes(repo, local=f"aireadyportal={route}\n")
    assert _bad(run("ARP_HOST=203.0.113.20\n")) == []


def test_타일_라우트가_다른_서버를_가리키면_알린다(box):
    """ARP 서버가 이사했는데 한쪽만 고쳤다."""
    repo, _gw, run = box
    _routes(repo, local="aireadyportal=http://198.51.100.1:3001/\n")
    (warn,) = _bad(run("ARP_HOST=203.0.113.20\n"))
    assert "ARP_HOST" in warn and "aireadyportal=" in warn and "둘 다" in warn


def test_타일_라우트는_local_이_base_를_이기고_호스트명은_대소문자를_가리지_않는다(box):
    repo, _gw, run = box
    _routes(repo, base="aireadyportal=http://198.51.100.1:3001/\n")
    assert len(_bad(run("ARP_HOST=203.0.113.20\n"))) == 1, "base 의 옛 주소"
    _routes(repo, base="aireadyportal=http://198.51.100.1:3001/\n", local="aireadyportal=http://203.0.113.20:3001/\n")
    assert _bad(run("ARP_HOST=203.0.113.20\n")) == [], "nginx 는 local 을 쓴다(gen-nginx-conf 와 같은 우선순위)"
    _routes(repo, local="aireadyportal=http://ARP.Corp.Example:3001/\n")
    assert _bad(run("ARP_HOST=arp.corp.example\n")) == []


# 1f 는 라우트 줄을 `aireadyportal=` 로 붙여 적은 것만 읽었다. nginx 를 만드는 gen-nginx-conf 와 포털 카탈로그는 키 둘레의 공백을
# 떼고 읽어, `aireadyportal = http://…` 로 적은 박스는 라우트가 멀쩡한데 매 실행 "ARP 타일 라우트가 없다" ⚠ 가 떴다(끝 요약에도
# 실린다). 거꾸로 박스 파일에서 빈 값으로 끈 라우트(`aireadyportal=`)는 추적 파일로 넘어가 '있다' 로 읽었다.
@pytest.mark.parametrize("line", ["aireadyportal = http://203.0.113.20:3001/", "aireadyportal =http://203.0.113.20:3001/",
                                  "  aireadyportal\t=\thttp://203.0.113.20:3001/"])
def test_타일_라우트는_키_둘레의_공백을_떼고_읽는다(box, line):
    repo, _gw, run = box
    _routes(repo, local=line + "\n")
    assert _bad(run("ARP_HOST=203.0.113.20\n")) == []


def test_공백을_두고_적은_라우트가_다른_서버면_없다가_아니라_다르다고_한다(box):
    """'없다' 고 하면 운영자는 이미 있는 줄을 또 적는다."""
    repo, _gw, run = box
    _routes(repo, local="aireadyportal = http://198.51.100.1:3001/\n")
    (warn,) = _bad(run("ARP_HOST=203.0.113.20\n"))
    assert "둘 다" in warn and "라우트가 없다" not in warn


def test_박스_파일에서_빈_값으로_끈_라우트는_추적_파일로_넘어가지_않는다(box):
    """gen-nginx-conf 는 박스 파일이 정의한 키의 추적 줄을 버린다 — 빈 값은 '이 박스에서 끔' 이고 location 이 안 생긴다."""
    repo, _gw, run = box
    _routes(repo, base="aireadyportal=http://203.0.113.20:3001/\n", local="aireadyportal=\n")
    (warn,) = _bad(run("ARP_HOST=203.0.113.20\n"))
    assert "라우트가 없다" in warn
    _routes(repo, base="aireadyportal=http://198.51.100.1:3001/\n", local="aireadyportal =  \n")
    (warn,) = _bad(run("ARP_HOST=203.0.113.20\n"))
    assert "라우트가 없다" in warn and "둘 다" not in warn


@pytest.mark.parametrize("base,local", [
    ("", "aireadyportal=http://203.0.113.20:3001/\n"), ("", "aireadyportal = http://203.0.113.20:3001\n"),
    ("", "  aireadyportal\t=\thttp://203.0.113.20:3001/\n"), ("", "#aireadyportal=http://203.0.113.20:3001/\n"),
    ("aireadyportal=http://203.0.113.20:3001/\n", None), ("aireadyportal=http://203.0.113.20:3001/\n", "ste=http://198.51.100.7:15810/\n"),
    ("aireadyportal=http://203.0.113.20:3001/\n", "aireadyportal=\n"), ("aireadyportal=http://203.0.113.20:3001/\n", "aireadyportal = \n"),
    ("", "aireadyportal=http://198.51.100.9:3001/\naireadyportal = http://203.0.113.20:3001/\n"),      # 같은 파일 안에서는 마지막 줄
    ("", None),
])
def test_라우트가_없다는_판정이_nginx_에_location_이_없는_것과_같다(box, tmp_path, base, local):
    """**정본은 생성기다** — gen-nginx-conf.sh 를 같은 라우트 파일로 실제로 돌려, 1f 가 '없다' 고 하는 경우가 정확히 그 conf 에
    /aireadyportal/ location 이 없는 경우인지 본다(1f 의 주석이 'gen-nginx-conf 와 같다' 고 적어 두고 다르게 읽고 있었다)."""
    repo, _gw, run = box
    _routes(repo, base=base, local=local)
    says_missing = any("라우트가 없다" in w for w in _bad(run("ARP_HOST=203.0.113.20\n")))
    gen = tmp_path / "gen/HWAXPortal"
    (gen / "infra/scripts").mkdir(parents=True); (gen / "infra/nginx").mkdir(); (gen / "backend/config").mkdir(parents=True)
    for f in ("gen-nginx-conf.sh", "_common.sh"):
        shutil.copy(ROOT / "infra/scripts" / f, gen / "infra/scripts" / f)
    shutil.copy(ROOT / "infra/nginx/hwax.conf.tmpl", gen / "infra/nginx/hwax.conf.tmpl")
    (gen / "infra/.env").write_text("HTTP_PORT=8088\nPORTAL_PORT=8723\n")
    (gen / "backend/config/routes.env").write_text(base)
    if local is not None:
        (gen / "backend/config/routes.local.env").write_text(local)
    r = subprocess.run(["bash", str(gen / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    has_location = "location /aireadyportal/ {" in (gen / "infra/nginx/hwax.conf").read_text(encoding="utf-8")
    assert says_missing is (not has_location), (base, local, r.stdout)


def test_ARP_HOST_가_없거나_거부되면_라우트를_보지_않는다(box):
    repo, _gw, run = box
    assert _bad(run("# ARP_HOST=\n")) == [], "안 쓰는 박스(dev)에 경고를 내지 않는다"
    assert _bad(run("ARP_HOST=localhost\n")) == [], "거부된 값은 위의 ✗ 하나로 끝난다"


# ── §5 — 게이트웨이 config 의 arp 주소가 ARP_HOST 와 다르면 재프로비저닝 ─────────────────────
@pytest.mark.parametrize("cfg_url,expect", [
    ("http://198.51.100.1:3001/mcp", True),       # 이사 전 주소가 남아 있다
    ("http://203.0.113.20:3002/mcp", True),       # 포트만 다르다
    ("http://203.0.113.20:3001/mcp", False),      # 같다
])
def test_5_는_arp_주소가_어긋나면_재프로비저닝한다(tmp_path, cfg_url, expect):
    gw = tmp_path / "gw"; gw.mkdir()
    (gw / "gateway_config.json").write_text(json.dumps({"arp": {"url": cfg_url}}))
    block = _block("  # ARP — 키(arp)는 있으니 calc_missing 이 못 잡는다.", "  # ste 사용자 위임 — 게이트웨이 config")
    script = f'MISSING=""\nARP_HOST="203.0.113.20"\nARP_PORT="3001"\nGW_DIR="{gw}"\n' + block + 'printf "MISSING=[%s]\\n" "$MISSING"\n'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"]})
    assert r.returncode == 0, r.stderr
    assert ("MISSING=[arp]" in r.stdout) is expect, r.stdout
