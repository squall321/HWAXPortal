# 헬스게이트가 **진짜 고장만** ✗ 로 말하는가 — 2026-09-20 cae00 로그에서 드러난 네 자리
"""왜 — 그날 로그에 ✗ 가 넷 찍혔는데 종료코드를 세운 것은 **하나도 없었다**(전부 `bad`).
사람은 넷 다 고장으로 읽었고, 그중 하나는 이 박스 대상도 아닌 서비스였다(searxng, only_on).
색이 판정과 어긋나면 로그를 안 믿게 되고, 그러면 진짜 고장도 묻힌다.

여기서 지키는 것 넷.
 ① `services.sh enabled` — 이 박스 대상인지 **정본(services.yaml)** 이 답한다(셸에 호스트명 비교를 복제하지 않는다).
 ② 헬스게이트의 searxng 블록이 그 답을 본다.
 ③ `bad`(⚠ 비치명)와 `fail`(✗ 치명)이 눈으로 갈린다 + 끝에서 실패 목록을 다시 낸다.
 ④ MCP 스모크가 **쓰기 도구를 부르지 않는다** — `ingest_now` 를 읽기 도구로 오인해 매 실행마다
    실제 인입·색인·그라운딩을 발사하고 있었다.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra" / "scripts"
UPDATE_ALL = SCRIPTS / "update-all.sh"


def _sh(script: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", **(env or {})})


def _block(start: str, end: str) -> str:
    src = UPDATE_ALL.read_text(encoding="utf-8")
    i = src.index(start)
    return src[i:src.index(end, i)]


# ── ① services.sh enabled ──────────────────────────────────────────────────
def _services_mod():
    spec = importlib.util.spec_from_file_location("svcmod", SCRIPTS / "services.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["svcmod"] = m
    spec.loader.exec_module(m)
    return m


def test_enabled_answers_with_exit_codes_only(monkeypatch):
    """0=이 박스 대상 · 1=아님 · 2=그런 서비스 없음. 출력이 아니라 **종료코드**로 답해야
    부르는 쪽이 자기 문구로 말할 수 있다(사람 문구를 grep 하면 문구가 바뀔 때 조용히 깨진다)."""
    m = _services_mod()
    names = [s["name"] for s in m.load()]
    only_on = next((s for s in m.load() if s.get("only_on")), None)
    if only_on is None:
        pytest.skip("only_on 을 쓰는 서비스가 services.yaml 에 없다")

    hosts = only_on["only_on"]
    hosts = [hosts] if isinstance(hosts, str) else list(hosts)
    import socket

    monkeypatch.setattr(socket, "gethostname", lambda: hosts[0])
    assert m.cmd_enabled([only_on["name"]]) == 0, "대상 박스인데 1 을 냈다"
    monkeypatch.setattr(socket, "gethostname", lambda: "다른박스-" + hosts[0])
    assert m.cmd_enabled([only_on["name"]]) == 1, "대상이 아닌데 0 을 냈다"
    assert m.cmd_enabled(["그런서비스없음"]) == 2
    assert names, "services.yaml 을 못 읽었다"


# ── ② 헬스게이트가 only_on 을 본다 ─────────────────────────────────────────
SEARX = ('# searxng — 종전엔 프로브도 복구도 없었다', '# Smart Twin Explorer')


def test_the_health_gate_skips_a_service_this_box_does_not_run(tmp_path):
    """cae00 의 그 모순 — 한 줄 사이에 '✗ 죽었다' 와 '이 박스 대상 아님' 이 같이 찍혔다."""
    stub = tmp_path / "svc"
    stub.write_text('#!/usr/bin/env bash\n[ "$1" = "enabled" ] && exit 1\nexit 0\n', encoding="utf-8")
    stub.chmod(0o755)
    helpers = 'ok() { echo "OK $*"; }\nbad() { echo "BAD $*"; }\nprobe() { echo "PROBE $*"; }\n'
    r = _sh(helpers + f'SVC="{stub}"\nhttp_code() {{ echo 000; }}\n' + _block(*SEARX))
    assert "PROBE" not in r.stdout, f"대상이 아닌데 두드렸다 — {r.stdout!r}"
    assert "BAD" not in r.stdout, "대상이 아닌데 경고를 찍었다"
    assert "이 박스 대상 아님" in r.stdout, f"조용히 넘어갔다(그것도 나쁘다) — {r.stdout!r}"


def test_the_health_gate_still_probes_where_the_service_belongs(tmp_path):
    """반대로 망가뜨리지 않았는지 — 대상 박스에서는 종전처럼 두드리고 복구까지 간다."""
    stub = tmp_path / "svc"
    stub.write_text('#!/usr/bin/env bash\n[ "$1" = "enabled" ] && exit 0\necho "UP $*"\n', encoding="utf-8")
    stub.chmod(0o755)
    helpers = 'ok() { echo "OK $*"; }\nbad() { echo "BAD $*"; }\nprobe() { echo "PROBE $*"; }\n'
    r = _sh(helpers + f'SVC="{stub}"\nhttp_code() {{ echo 000; }}\n' + _block(*SEARX))
    assert "PROBE" in r.stdout and "UP up searxng" in r.stdout, r.stdout


# ── ③ 치명/비치명이 갈린다 ─────────────────────────────────────────────────
def test_advisory_and_fatal_are_visually_different_and_only_fatal_counts():
    helpers = _block("hr() {", "# HTTP 코드 프로브")
    r = _sh(helpers + '\nFAIL=0\nbad "경고다"\nfail "진짜 실패다"\n'
            'echo "FAIL=$FAIL"\nprintf "%s" "$FAIL_ITEMS"\n')
    assert "\033[1;33m⚠\033[0m 경고다" in r.stdout, f"경고가 여전히 빨간 ✗ 다 — {r.stdout!r}"
    assert "\033[1;31m✗\033[0m 진짜 실패다" in r.stdout
    assert "FAIL=1" in r.stdout, "fail 이 종료 판정을 안 세운다"
    assert "· 진짜 실패다" in r.stdout and "· 경고다" not in r.stdout, "끝맺음 목록에 경고가 섞였다"


def test_every_fatal_goes_through_fail():
    """`bad "…"; FAIL=1` 방언이 남아 있으면 그 항목만 노란 ⚠ 로 찍힌다(치명인데)."""
    src = UPDATE_ALL.read_text(encoding="utf-8")
    stray = [l.strip() for l in src.splitlines()
             if l.strip() == "FAIL=1" and "fail()" not in l]
    assert not stray, f"fail 을 거치지 않고 FAIL 을 세우는 자리가 남았다: {len(stray)}곳"


# ── ④ 스모크가 쓰기 도구를 부르지 않는다 ───────────────────────────────────
def _smoke_mod():
    spec = importlib.util.spec_from_file_location("smokemod", SCRIPTS / "mcp-smoke.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("name", ["ingest_now", "gate_expert_now", "render_submit",
                                  "report_ingest", "purge_cache", "reload_config"])
def test_side_effecting_tools_are_never_probed(name):
    """`ingest_now` 는 드롭폴더 전량을 분류·색인·그라운딩한다 — 스모크가 그걸 매번 불렀다."""
    m = _smoke_mod()
    assert m.WRITE.match(name) or m.WRITE_ANY.search(name), f"{name} 이 '읽기 도구'로 샌다"


@pytest.mark.parametrize("name", ["inbox_status", "list_reports", "get_report", "search_cards"])
def test_read_tools_are_still_probed(name):
    """반대로 다 막아 버리면 스모크가 아무것도 안 본다."""
    m = _smoke_mod()
    assert not (m.WRITE.match(name) or m.WRITE_ANY.search(name)), f"{name} 까지 막았다"
