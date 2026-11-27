# 자동 파이프라인 보고서(revdiff 첫 차수 · 값 변화 · 종합 · 해석별) · RA 시스템 계정 게시(줄 없으면 안 부름 · 0600 · dry_run 경고 · 답 잃음 · 게시 다시 · 토큰을 안 찍음)
"""보고서는 결과 봉투로 코드가 쓴다(portal-api §5). RA 는 가짜 전송(MockTransport)이다 — 박스 파일과 토큰 파일은 임시 자리다(이 박스의
infra/ra-formats.local.json · 비밀 파일을 읽지 않는다)."""
from __future__ import annotations

import json
import logging
import os

import httpx
import pytest
from autopipe_fakes import SPEC, THERMAL, FakeAnalysis, Harness, ready_run

from app.agent import ra_post as _ra_post
from app.autopipe import ra as RA

TOKEN = "rat_test-system-account-0123456789abcdef"
REP_SPEC = {**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                              {"id": "per", "kind": "report", "report": "per_analysis", "needs": ["thermal"]},
                              {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal"]},
                              {"id": "revdiff", "kind": "report", "report": "revdiff", "needs": ["thermal"]}]}


@pytest.fixture()
def box(tmp_path, monkeypatch):
    """RA 박스 파일 · 토큰 파일을 임시 자리로. 돌려주는 함수로 줄을 적는다."""
    path = tmp_path / "ra-formats.local.json"
    monkeypatch.setattr(_ra_post, "PATH", path)
    monkeypatch.setattr(RA, "ROOT", tmp_path)

    def write(row: dict | None, *, mode: int = 0o600, extra: dict | None = None):
        doc = {"deliberation": {"template_id": "sys.hwax.deliberation", "template_version": 1}, **(extra or {})}
        if row is not None:
            doc["auto_pipeline"] = row
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        tok = tmp_path / "secrets" / "ra-auto.token"
        tok.parent.mkdir(exist_ok=True)
        tok.write_text(TOKEN + "\n", encoding="utf-8")
        os.chmod(tok, mode)
    return write


ROW = {"board": "sys-hwax-auto", "token_file": "secrets/ra-auto.token",
       "formats": {k: {"template_id": "sys.hwax-auto.report", "template_version": 1} for k in ("per_analysis", "summary", "revdiff")}}


class FakeRA:
    def __init__(self):
        self.calls: list[tuple[str, str, dict, dict]] = []
        self.warnings: list[str] = []
        self.lose_create = False
        self.mount_status = [200]
        self.next_id = 70

    def __call__(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}")
        self.calls.append((req.method, req.url.path, body, dict(req.headers)))
        if req.url.path == "/api/reports/ai-draft":
            if body.get("dry_run"):
                return httpx.Response(200, json={"success": True, "data": {"dry_run": True, "warnings": self.warnings}})
            if self.lose_create:
                raise httpx.ReadTimeout("답을 잃었다")
            self.next_id += 1
            return httpx.Response(200, json={"success": True, "data": {"report_id": self.next_id, "url": f"/w/u/reports/{self.next_id}"}})
        if req.url.path == "/api/mounts":
            st = self.mount_status.pop(0) if len(self.mount_status) > 1 else self.mount_status[0]
            return httpx.Response(st, json={"success": st == 200, "data": {"items": []}, "message": "잠시 불통" if st != 200 else ""})
        return httpx.Response(404)

    def paths(self) -> list[str]:
        return [f"{m} {p}" + (" dry" if b.get("dry_run") else "") for m, p, b, _ in self.calls]


@pytest.fixture()
def fake_ra(monkeypatch):
    ra = FakeRA()
    monkeypatch.setattr(RA, "_TRANSPORT", httpx.MockTransport(ra))
    return ra


@pytest.fixture()
def mk(tmp_path):
    made = []

    def make(*apps, **kw):
        d = tmp_path / f"h{len(made)}"
        d.mkdir()
        h = Harness(d, *apps, **kw)
        made.append(h)
        return h
    yield make
    for h in made:
        h.close()


# ── 보고서 ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_첫_차수는_revdiff_가_첫_차수라고_말하고_해석별_종합이_수치를_옮긴다(mk, box):
    box(None)
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule(REP_SPEC)
    run = ready_run(h)
    st = h.steps(run["id"])
    assert "## 첫 차수" in st["revdiff"]["report_md"]
    per = st["per"]["report_md"]
    assert per.startswith("# [자동] 낙하 · 열충격 기본 — TASK-A dv1 · 해석별 보고서")
    assert "자동 — 규칙 「낙하 · 열충격 기본」 v1" in per and "규칙을 켠 사람 maker@example.com" in per
    assert "| 솔더 SED 최대 | 0.82 | MJ/m3 | 1 | 사내 기준 | 합(pass) |" in per
    assert "그림 `fig-1`" in per and "원자료 d3plot — `/cluster/run/1`" in per
    assert "thermal: 합(pass) — 수치 1개" in st["summary"]["report_md"]
    assert st["summary"]["ra_state"] is None, "RA 줄이 없으면 게시하지 않는다"


def test_다음_차수의_revdiff_는_값과_판정_변화를_맞댄다(mk, box):
    box(None)
    app = FakeAnalysis(THERMAL, sync=True)
    h = mk(app)
    h.rule(REP_SPEC)
    ready_run(h, "TASK-A", "dv1")
    app.verdict = "fail"
    app.metrics = [{"name": "sed_max", "label": "솔더 SED 최대", "unit": "MJ/m3", "value": 1.2, "limit": 1.0, "verdict": "fail"},
                   {"name": "warp", "unit": "mm", "value": 0.3}]
    h.src.add("TASK-A", "dv2", ref="p-2", sha="e" * 64, at=h.t + 1)
    h.tick(10)
    h.tick(700)
    dv2 = [r for r in h.runs() if r["revision"] == "dv2"][0]
    md = h.steps(dv2["id"])["revdiff"]["report_md"]
    assert "앞 차수 — dv1" in md
    assert "판정 합(pass) → 부(fail) (바뀜)" in md
    assert "| 솔더 SED 최대 | 0.82 | 1.2 | MJ/m3 | +0.38 (+46.3%) | 합(pass) → 부(fail) |" in md
    assert "| warp | — | 0.3 | mm | 새로 생김 |" in md


def test_종합은_끝나지_않은_해석을_숨기지_않는다(mk, box):
    box(None)
    a, b = FakeAnalysis(THERMAL, sync=True), FakeAnalysis("heax-kooremapper_mcp", sync=True)
    b.check_answer = {"ready": False, "missing": [{"kind": "infra", "why": "공유 볼륨"}], "inputs": []}
    h = mk(a, b)
    h.rule({**SPEC, "steps": [{"id": "thermal", "kind": "analysis", "app": "thermal_shock_mcp", "profile": "default"},
                              {"id": "drop", "kind": "analysis", "app": "kooremapper_mcp", "profile": "default"},
                              {"id": "summary", "kind": "report", "report": "summary", "needs": ["thermal", "drop"]}]})
    run = ready_run(h)
    md = h.steps(run["id"])["summary"]["report_md"]
    assert "## 끝나지 않은 해석(숨기지 않는다)" in md and "drop: 막힘 — missing:infra" in md
    assert h.store.get_run(run["id"])["state"] == "partial"


# ── RA 게시 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_auto_pipeline_줄이_없으면_RA_를_부르지_않는다(mk, box, fake_ra):
    box(None)
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule(REP_SPEC)
    ready_run(h)
    assert fake_ra.calls == [] and RA.health()["configured"] is False


def test_시스템_계정으로_초안_게시하고_토큰을_로그_원장_응답에_싣지_않는다(mk, box, fake_ra, caplog):
    box(ROW)
    caplog.set_level(logging.DEBUG)
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule(REP_SPEC)
    run = ready_run(h)
    st = h.steps(run["id"])
    for sid in ("per", "summary", "revdiff"):
        assert st[sid]["ra_state"] == "posted" and st[sid]["ra_report_id"], st[sid]
    assert fake_ra.paths()[:3] == ["POST /api/reports/ai-draft dry", "POST /api/reports/ai-draft", "POST /api/mounts"]
    _, _, draft, hdr = fake_ra.calls[1]
    assert draft["template_id"] == "sys.hwax-auto.report" and draft["template_version"] == 1
    assert set(draft["blocks"]) == {"background", "results", "recommendation", "minutes"}
    assert all(len(x) <= 2000 for v in draft["blocks"].values() for x in v)
    assert hdr["authorization"] == f"Bearer {TOKEN}" and "x-client" not in hdr, "MCP 길이 아니다(확인 토큰 단계 없음)"
    mount = fake_ra.calls[2][2]
    assert mount["workspace_slugs"] == ["sys-hwax-auto"] and "confirm_token" not in mount
    blob = json.dumps([h.store.steps(run["id"]), h.store.events(run["id"]), RA.health()], ensure_ascii=False, default=str)
    assert TOKEN not in blob and TOKEN not in caplog.text


def test_토큰_파일이_0600_이_아니면_쓰지_않는다(mk, box, fake_ra):
    box(ROW, mode=0o644)
    hl = RA.health()
    assert hl["configured"] is False and "0600" in hl["error"]
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule(REP_SPEC)
    ready_run(h)
    assert fake_ra.calls == []


def test_형식이_블록을_받지_않으면_만들지_않는다(mk, box, fake_ra):
    box(ROW)
    fake_ra.warnings = ["블록 results 는 템플릿에 없다 — 버린다"]
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule({**SPEC})
    run = ready_run(h)
    st = h.steps(run["id"])["summary"]
    assert st["ra_state"] == "failed" and st["ra_error"].startswith("ra_template_mismatch")
    assert fake_ra.paths() == ["POST /api/reports/ai-draft dry"]


def test_만들기_답을_잃으면_다시_만들지_않는다(mk, box, fake_ra):
    box(ROW)
    fake_ra.lose_create = True
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule({**SPEC})
    run = ready_run(h)
    st = h.steps(run["id"])["summary"]
    assert st["ra_state"] == "failed" and st["ra_error"].startswith("ra_outcome_unknown")
    n = len(fake_ra.calls)
    h.tick(60)
    assert len(fake_ra.calls) == n, "같은 보고서가 둘이 되지 않게 다시 부르지 않는다"


def test_게시가_잠깐_실패하면_다음_박자에_게시만_다시_한다(mk, box, fake_ra):
    box(ROW)
    fake_ra.mount_status = [503, 200]
    h = mk(FakeAnalysis(THERMAL, sync=True))
    h.rule({**SPEC})
    run = ready_run(h)
    st = h.steps(run["id"])["summary"]
    assert st["ra_state"] == "drafted" and st["ra_report_id"] == "71"
    h.tick(60)
    st = h.steps(run["id"])["summary"]
    assert st["ra_state"] == "posted" and st["ra_report_id"] == "71"
    assert fake_ra.paths() == ["POST /api/reports/ai-draft dry", "POST /api/reports/ai-draft", "POST /api/mounts", "POST /api/mounts"]


@pytest.mark.parametrize("row,needle", [
    ({**ROW, "board": "../x"}, "board"),
    ({**ROW, "token_file": "/abs/path"}, "상대 경로"),
    ({**ROW, "formats": {"summary": {"template_id": "x", "template_version": 0}}}, "formats"),
    ({**ROW, "token_file": "secrets/없음.token"}, "없다"),
])
def test_박스_파일_줄의_꼴(box, row, needle):
    box(row)
    hl = RA.health()
    assert hl["configured"] is False and needle in hl["error"]


def test_다른_종류_줄을_더해도_심의_형식_리더는_그대로다(box):
    """ra_post(심의 보고서 게시)는 deliberation 줄만 읽는다 — auto_pipeline 줄을 더해도 심의 형식 · 게시판이 그대로다."""
    box(ROW)
    assert _ra_post.status()["template_id"] == "sys.hwax.deliberation" and _ra_post.status()["error"] is None
