# LLM/GPU 현황 수집기 배선 — 매니페스트(기본 꺼짐 · 제 파일만의 지문) · update-all 5d · 포트 표 · 예시 설정
"""왜 — 수집기는 기본 꺼짐이다(사용자 결정 OD-4). 켜는 것은 infra/.env 의 LLM_STATUS 한 줄이고, 그 한 줄로 ① update-all 5d 가 수집기를 띄우고
② start.sh 가 포털에 수집기 주소를 넘긴다(그 시험은 test_llm_status_route). 끄면 5d 가 떠 있는 것을 내리고 ○ 한 줄을 남긴다. 지문이 포털 HEAD 를 따르면 문서 커밋마다 수집기가 다시
떠서 쌓던 창이 빈다 — 제 파일만 지문이다.

⚠ 실물을 건드리지 않는다. update-all 5d 는 원문 그대로 임시 포털에서 돌리고 services.sh · update-sites · llm-status.sh 는 부른 사실만 적는
대역이다(http_code 도 대역). services.py 는 임시 리포에 복사해 env -i 로 부른다. 주소 · 값은 지어낸 것이다.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from tests.test_env_sync import _repo, _run  # env-sync 를 임시 포털 사본으로 돌린다

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra/scripts"
MANIFEST = {s["name"]: s for s in yaml.safe_load((ROOT / "infra/services.yaml").read_text(encoding="utf-8"))["services"]}
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")


def _services_mod():
    spec = importlib.util.spec_from_file_location("svc_for_llm_status", SCRIPTS / "services.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── 매니페스트 ─────────────────────────────────────────────────────────────────────────────────────
def test_매니페스트_항목은_LLM_STATUS_가_있는_박스에서만_다루고_제_파일로만_지문을_잡는다(tmp_path, monkeypatch):
    entry = MANIFEST["llm-status"]
    assert {k: entry[k] for k in ("dir", "if_env", "update", "fp_git", "fp", "start", "stop", "expect", "health", "tier")} == {
        "dir": ".", "if_env": "LLM_STATUS", "update": False, "fp_git": False,
        "fp": ["infra/llm-status", "infra/scripts/llm-status.sh"],
        "start": "./infra/scripts/llm-status.sh run", "stop": "./infra/scripts/llm-status.sh stop", "expect": 200,
        "health": "http://127.0.0.1:${LLM_STATUS_PORT:-8760}/health", "tier": 5}
    m = _services_mod()
    (tmp_path / "infra/llm-status").mkdir(parents=True)
    (tmp_path / "infra/scripts").mkdir()
    monkeypatch.setattr(m, "PORTAL_ROOT", tmp_path)
    monkeypatch.delenv("LLM_STATUS", raising=False)
    (tmp_path / "infra/.env").write_text("LLM_STATUS_PORT=18761\n", encoding="utf-8")
    assert m.enabled_here(entry) is False and "if_env=LLM_STATUS" in m.skip_reason(entry), "기본 꺼짐"
    assert m.health_url(entry) == "http://127.0.0.1:18761/health", "포트는 infra/.env 를 따른다(띄우는 스크립트와 같은 값)"
    (tmp_path / "infra/.env").write_text("LLM_STATUS=1\n", encoding="utf-8")
    assert m.enabled_here(entry) is True and m.health_url(entry) == "http://127.0.0.1:8760/health"
    (tmp_path / "infra/llm-status/collector.py").write_text("v1\n")
    (tmp_path / "infra/scripts/llm-status.sh").write_text("s1\n")
    f1 = m.service_fp(entry)
    (tmp_path / ".env").write_text("NEW_KEY=1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/x.md").write_text("문서\n")
    (tmp_path / "infra/.env").write_text("LLM_STATUS=1\nLLM_STATUS_TARGETS=A=http://a.example:1/v1\n", encoding="utf-8")
    (tmp_path / "infra/llm-status/__pycache__").mkdir()
    (tmp_path / "infra/llm-status/__pycache__/collector.cpython-310.pyc").write_bytes(b"x")
    assert m.service_fp(entry) == f1, "문서 · 루트 .env · infra/.env(수집기가 스스로 다시 읽는다) · 바이트코드는 지문이 아니다"
    (tmp_path / "infra/llm-status/collector.py").write_text("v2 longer\n")
    f2 = m.service_fp(entry)
    assert f2 != f1, "수집기 파일이 바뀌면 다시 띄운다"
    (tmp_path / "infra/scripts/llm-status.sh").write_text("s2 longer\n")
    assert m.service_fp(entry) != f2, "띄우는 스크립트가 바뀌어도"


def test_services_cli_는_파일의_LLM_STATUS_로만_켠다(tmp_path):
    """부팅 유닛과 같은 환경(env -i, infra/.env 파일만)에서 실제 매니페스트의 llm-status 항목을 묻는다."""
    lay = tmp_path / "HWAXPortal"
    (lay / "infra/scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS / "services.py", lay / "infra/scripts/services.py")
    shutil.copy(ROOT / "infra/services.yaml", lay / "infra/services.yaml")

    def run(env_text, *args):
        (lay / "infra/.env").write_text(env_text)
        return subprocess.run(["env", "-i", f"PATH={os.environ['PATH']}", sys.executable, str(lay / "infra/scripts/services.py"), *args],
                              capture_output=True, text=True, timeout=60)
    assert run("HWAX_BOX=x\n", "enabled", "llm-status").returncode == 1
    assert run("LLM_STATUS=1   # 켠다\n", "enabled", "llm-status").returncode == 0
    assert run("LLM_STATUS=1\nLLM_STATUS_PORT=18762\n", "health", "llm-status").stdout.strip() == "http://127.0.0.1:18762/health"


def test_상태판은_켠_박스에서_수집기의_health_를_200_으로_본다(tmp_path):
    from test_status_board import (
        Lay,  # noqa: PLC0415 — 상태판 시험의 임시 리포(생성기를 실제로 돌린다)
    )
    lay = Lay(tmp_path)
    lay.manifest([MANIFEST["llm-status"]])
    lay.infra_env("LLM_STATUS=1\nLLM_STATUS_PORT=18763\n")
    r = lay.gen()
    assert r.returncode == 0, r.stdout + r.stderr
    assert lay.endpoints()["http://127.0.0.1:18763/health"]["conditions"] == ["[CONNECTED] == true", "[STATUS] == 200"]


# ── 포트 · 예시 설정 · 포털 설정 ───────────────────────────────────────────────────────────────────
def test_포트는_허브_앱_포트_풀_밖이고_세_곳의_기본값이_같다():
    pm = (ROOT / "docs/PORT-MAP.md").read_text(encoding="utf-8")
    rows = [ln for ln in pm.splitlines() if re.match(r"^\| 8760 \|", ln)]
    assert len(rows) == 1 and "LLM/GPU 현황 수집기" in rows[0] and "LLM_STATUS_PORT" in rows[0], rows
    assert not 9100 <= 8760 <= 9999, "9100~9999 는 HEAXHub 앱 포트 풀이다"
    others = {int(m.group(1)) for m in re.finditer(r"^\| ([0-9]{4,5}) \|", pm, re.M)} - {8760}
    assert 8760 not in others
    spec = importlib.util.spec_from_file_location("llm_status_collector_ports", ROOT / "infra/llm-status/collector.py")
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    assert m.DEFAULT_PORT == 8760
    assert 'PORT="${PORT:-8760}"' in (SCRIPTS / "llm-status.sh").read_text(encoding="utf-8")
    assert "${LLM_STATUS_PORT:-8760}" in MANIFEST["llm-status"]["health"]


def test_예시_파일은_켜는_줄을_주석으로만_두고_env_sync_가_선택으로_알린다(tmp_path):
    """기본 꺼짐 — 실제 infra/.env.example 의 수집기 덩이를 이미 맞춰진 .env 에 흘려도 LLM_STATUS 가 켜진 줄로 들어가면 안 된다(모든 박스에서
    켜진다). 비워 두면 꺼짐인 손잡이를 '값을 정해야 한다' 로 재촉하지도 않는다(LLM_UPSTREAMS · STATUS_ALERT_TO 와 같은 까닭)."""
    example = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    i = example.index("# ── LLM/GPU 현황 수집기")
    d = _repo(tmp_path, example, example[:i])
    r = _run(d)
    assert r.returncode == 0, r.stdout + r.stderr
    added = (d / ".env").read_text(encoding="utf-8")[i:]
    for k in ("LLM_STATUS", "LLM_STATUS_PORT", "LLM_STATUS_REPLICA_PORTS"):
        lines = [ln for ln in added.splitlines() if re.match(rf"^#?\s*{k}=", ln)]
        assert len(lines) == 1 and lines[0].startswith(f"# {k}=") and "# 선택" in lines[0], (k, lines, added)
    assert "LLM_STATUS" not in "".join(ln for ln in r.stdout.splitlines() if "값을 정해야 한다" in ln), r.stdout
    assert not re.search(r"^\s*LLM_STATUS\w*=", added, re.M), "켜진 줄이 들어갔다"


# ── update-all 5d ──────────────────────────────────────────────────────────────────────────────────
def _ua_region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


class _Box5d:
    """update-all 5d 를 원문 그대로 임시 포털에서 돌린다 — services.sh enabled · update-sites · llm-status.sh stop 은 부른 사실만 적는 대역이다."""

    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts/lib").mkdir(parents=True)
        shutil.copy(SCRIPTS / "lib/skip-ledger.sh", self.repo / "infra/scripts/lib/skip-ledger.sh")
        self.calls, self.ledger = self.tmp / "calls.log", self.tmp / "ledger"
        self.calls.write_text("")
        self.ledger.write_text("")
        sh = {"services.sh": 'echo "services.sh $*" >> "{c}"; [ "$1" = enabled ] && exit "${{STUB_EN:-1}}"; exit 0',
              "update-sites.sh": 'echo "update-sites.sh $*" >> "{c}"; echo "  (대역) update-sites $*"; exit "${{STUB_US:-0}}"',
              "llm-status.sh": 'echo "llm-status.sh $*" >> "{c}"; echo "  (대역) llm-status $*"; exit "${{STUB_STOP:-0}}"'}
        for name, body in sh.items():
            p = self.repo / "infra/scripts" / name
            p.write_text("#!/usr/bin/env bash\n" + body.format(c=self.calls) + "\n", encoding="utf-8")
            p.chmod(0o755)

    def run(self, infra_env: str = "", **env) -> str:
        (self.repo / "infra/.env").write_text(infra_env, encoding="utf-8")
        envfile = _ua_region("_envfile_value() {", "\n}\n") + "\n}\n"
        body = _ua_region("# ── 5d) LLM/GPU 현황 수집기", "# ── 6) 헬스게이트")
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'SELF_REPO="{self.repo}"', f'SVC="{self.repo}/infra/scripts/services.sh"',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            'http_code() { echo "${STUB_HTTP:-000}"; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"', f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"',
            envfile, body, "echo END",
        ])
        base = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env={**base, **env})
        assert "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def called(self) -> list[str]:
        return self.calls.read_text().splitlines()


@pytest.fixture()
def box5d(tmp_path):
    return _Box5d(tmp_path)


def _tagged(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


def test_5d_꺼져_있으면_안_켠_기능으로_남기고_아무것도_띄우지_않는다(box5d):
    out = box5d.run("OTHER=1\n", STUB_EN="1")
    assert box5d.called() == ["services.sh enabled llm-status"], box5d.called()
    assert not _tagged(out, "HR:") and not _tagged(out, "FAIL:") and not _tagged(out, "BAD:"), out
    led = box5d.ledger.read_text()
    assert led.startswith("LLM/GPU 현황 수집기\t") and "LLM_STATUS=1" in led and "server-setup.md" in led, led
    plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
    assert "○ LLM/GPU 현황 수집기 — infra/.env 에 LLM_STATUS 가 없다" in plain, "즉시 한 줄(○)도 찍는다"


def test_5d_꺼졌는데_수집기가_떠_있으면_내린다(box5d):
    out = box5d.run("LLM_STATUS_PORT=18766\n", STUB_EN="1", STUB_HTTP="200")
    assert box5d.called() == ["services.sh enabled llm-status", "llm-status.sh stop"], box5d.called()
    assert any(":18766" in ln and "내렸다" in ln for ln in _tagged(out, "OK:")), out
    assert box5d.ledger.read_text().startswith("LLM/GPU 현황 수집기\t"), "내렸어도 꺼짐은 ○ 다"
    box5d.calls.write_text("")
    out = box5d.run("", STUB_EN="1", STUB_HTTP="200", STUB_STOP="1")
    assert any("내리지 못했다" in ln for ln in _tagged(out, "BAD:")) and not _tagged(out, "FAIL:"), out
    box5d.calls.write_text("")
    out = box5d.run("", STUB_EN="1", STUB_HTTP="404")
    assert box5d.called() == ["services.sh enabled llm-status"], "200 이 아니면(그 포트에 남이 답한다) 내리지 않는다"


def test_5d_켜져_있으면_update_sites_로_띄운다(box5d):
    out = box5d.run("LLM_STATUS=1\n", STUB_EN="0")
    assert box5d.called() == ["services.sh enabled llm-status", "update-sites.sh llm-status"], box5d.called()
    assert _tagged(out, "HR:5d)") and any("http://127.0.0.1:8760" in ln for ln in _tagged(out, "OK:")), out
    assert not _tagged(out, "FAIL:") and not _tagged(out, "BAD:") and not box5d.ledger.read_text(), out
    out = box5d.run("LLM_STATUS=1\nLLM_STATUS_PORT=18767\n", STUB_EN="0")
    assert any("http://127.0.0.1:18767" in ln for ln in _tagged(out, "OK:")), out


def test_5d_띄우지_못하면_실패로_센다(box5d):
    out = box5d.run("LLM_STATUS=1\n", STUB_EN="0", STUB_US="1")
    assert any("띄우지 못했다" in ln and "rc 1" in ln for ln in _tagged(out, "FAIL:")), out


def test_5d_LLM_STATUS_0_은_켜짐이라고_알린다(box5d):
    out = box5d.run("LLM_STATUS=0\n", STUB_EN="0")
    assert any("켜짐으로 읽힌다" in ln for ln in _tagged(out, "BAD:")), out


def test_5d_update_all_배선():
    i5c, i5d, i6 = UA.index("# ── 5c) 호출 추적(Phoenix)"), UA.index("# ── 5d) LLM/GPU 현황 수집기"), UA.index('hr "6) 헬스게이트"')
    assert i5c < i5d < i6, "5d 는 5c 뒤 · §6 앞이다"
    head = UA[:UA.index("set -uo pipefail")]
    assert "5d) LLM/GPU 현황 수집기" in head and "LLM_STATUS" in head, "사용법의 순서 목록에 있다"
    for line in _ua_region("# ── 5d) LLM/GPU 현황 수집기", "# ── 6) 헬스게이트").splitlines():
        assert not line.lstrip().startswith("`"), "대입어 사슬 안의 백틱 주석은 다음 대입어를 명령 이름으로 만든다"


def test_물려받은_수집기_포트를_버린다():
    """llm-status.sh stop 은 환경의 LLM_STATUS_PORT 를 먼저 본다 — 운영자 셸에 export 된 옛 포트가 update-sites → services.py down 으로 흘러
    지금 수집기 대신 옛 포트를 내리지 않게 update-all · update-sites 머리가 버린다(상태판 · 라우터 · 호출 추적과 같다)."""
    us = (SCRIPTS / "update-sites.sh").read_text(encoding="utf-8")
    heads = (UA[:UA.index('SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"')],
             us[:us.index('ROOT="$(cd "$(dirname "$0")/../.." && pwd)"')])
    for head in heads:
        r = subprocess.run(["bash", "-c", head + '\necho "[${LLM_STATUS_PORT-없음}]"\n'], capture_output=True, text=True, timeout=30,
                           env={"PATH": os.environ["PATH"], "HOME": "/nonexistent", "LLM_STATUS_PORT": "9555"})
        assert r.stdout.split()[-1:] == ["[없음]"], r.stdout + r.stderr
