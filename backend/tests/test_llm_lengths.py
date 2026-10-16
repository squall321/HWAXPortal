# 길이 분포 추출기(llm-lengths.py) — 원장·심의 기록의 글이 결과로 새지 않는가 · 원장을 읽기만 하는가 · 수가 맞는가 · 기본 자리(docs/llm-pool/capacity.md 3절)
"""왜 — 이 추출기는 카드 원문·설계 변경이 든 리스크 앱 원장과 심의 기록을 연다. 거기서 글 한 조각이라도 결과 파일로 새면 그 파일이 어디로든
옮겨진다(측정 결과는 문서로 옮겨 적는다). 그래서 원장의 글 열과 심의 기록의 글마다 표식을 심고, 결과·표준 출력·표준 오류 어디에도 표식이
없고 결과의 모든 값이 수이며 이름이 정해 둔 것뿐인지 본다. 원장 질의는 프로세스로 들어오는 값부터 수인지 본다(글 열은 SQL 안에서 번호로)."""
import gzip
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LENGTHS_PY = ROOT / "infra/scripts/llm-lengths.py"
MARK = "ZQX본문표식"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # infra/scripts 에 __pycache__ 를 남기지 않는다
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


L = _load(LENGTHS_PY, "hwax_llm_lengths")


# 리스크 앱 원장 v4 의 rr_review_calls 와 같은 열(HWAXRisk backend/app/risk_store.py _DDL_V4) — 글 열에는 전부 표식을 넣는다.
_CALLS_DDL = """CREATE TABLE rr_review_calls (
  call_id TEXT PRIMARY KEY, target_key TEXT NOT NULL, agent_key TEXT NOT NULL, unit_id TEXT, owner_sub TEXT NOT NULL, run_id TEXT,
  kind TEXT NOT NULL, variant TEXT, deck_id TEXT, page_no INTEGER, seq INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL, outcome_class TEXT,
  cards_json TEXT, request_hash TEXT, input_sha TEXT, prompt_chars INTEGER, tokens_in INTEGER, tokens_out INTEGER, output_truncated INTEGER,
  finish_reason TEXT, soft_over INTEGER NOT NULL DEFAULT 0, attempts INTEGER, queued_ms INTEGER, llm_ms INTEGER,
  rows_expected INTEGER, rows_missing INTEGER, bad_lines INTEGER, stamp INTEGER NOT NULL DEFAULT 0, dropped_over_cap INTEGER, bg_dropped INTEGER,
  model TEXT, prompt_rev TEXT, norm_rev TEXT, limits_rev TEXT, credential_kind TEXT, result_gz BLOB, result_sha256 TEXT, quality_json TEXT,
  error_code TEXT, error_infra INTEGER, error_retryable INTEGER, error TEXT, started_at INTEGER, duration_ms INTEGER)"""

# (kind, agent, prompt_chars, tokens_in, tokens_out, attempts, llm_ms, started_at, duration_ms)
_ROWS = [
    ("verdict", "A", 2000, 1000, 100, 1, 900, 100, 10_000),
    ("verdict", "A", 6000, 3000, 300, 1, 900, 101, 10_000),
    ("verdict", "B", 9000, 4000, 400, 2, 900, 102, 10_000),     # 보충 시도 둘 — 시도마다 2000 · 200 으로 두 번 센다
    ("sweep", "C", 1500, 500, 50, 1, 900, 200, 1_000),
    (f"{MARK}-모르는종류", f"{MARK}-전문가", 1400, 700, 70, 1, 900, 105, 1_000),
    ("verdict", "A", None, None, None, None, None, 300, 5),         # review_busy — LLM 을 부르지 않았다(사용량·LLM 시간 없음)
]


def _risk_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute(_CALLS_DDL)
    for i, (kind, agent, pc, tin, tout, att, llm, start, dur) in enumerate(_ROWS):
        con.execute("INSERT INTO rr_review_calls(call_id, target_key, agent_key, unit_id, owner_sub, run_id, kind, variant, deck_id, state,"
                    " outcome_class, cards_json, request_hash, input_sha, prompt_chars, tokens_in, tokens_out, attempts, llm_ms, model,"
                    " prompt_rev, result_gz, quality_json, error_code, error, started_at, duration_ms)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"{MARK}-call-{i}", f"{MARK}-target", agent, f"{MARK}-unit", f"{MARK}@corp", f"{MARK}-run", kind, f"{MARK}-v",
                     f"{MARK}-deck", "ok", "ok", json.dumps([f"{MARK}-카드별칭"]), f"{MARK}-hash", f"{MARK}-sha", pc, tin, tout, att, llm,
                     f"{MARK}-model", f"{MARK}-rev", gzip.compress(f"{MARK} 카드 원문 «설계 변경»".encode()),
                     json.dumps({"why": f"{MARK} 판정 까닭"}), f"{MARK}-code", f"{MARK} 오류 글", start, dur))
    con.commit()
    con.close()


def _delib_jobs(d: Path) -> None:
    d.mkdir()
    job1 = {"id": f"{MARK}-job", "question": f"{MARK} 질문 원문", "label": f"{MARK}", "user": f"{MARK}@corp", "decision": "가" * 777,
            "turns": [{"persona": f"{MARK}-좌석", "round": 1, "say": f"{MARK} 짧게", "say_full": "나" * 50, "say_full_chars": 1234},
                      {"persona": f"{MARK}-좌석2", "round": 1, "say": f"{MARK} 짧게", "say_full": "다" * 321},
                      {"persona": f"{MARK}-좌석3", "round": 2, "say": "라" * 45},
                      {"note": f"전사 상한 — {MARK}"}]}
    job2 = {"id": "j2", "question": f"{MARK}", "turns": [{"persona": "x", "say": "마" * 10}], "decision": None}
    (d / "a.json").write_text(json.dumps(job1, ensure_ascii=False), encoding="utf-8")
    (d / "b.json").write_text(json.dumps(job2, ensure_ascii=False), encoding="utf-8")
    (d / "broken.json").write_text("{" + MARK, encoding="utf-8")
    (d / "list").mkdir()
    (d / "list" / "c.json").write_text(json.dumps({"turns": [{"say": "바" * 99999}]}), encoding="utf-8")   # 목록 캐시 — 세지 않는다


def _delib_runs(d: Path) -> None:
    raw = d / "2026-09-01_run" / "raw"
    raw.mkdir(parents=True)
    rows = [{"type": "started", "key": f"{MARK}"}, {"type": "result", "key": "k", "result": f"{MARK}" + "사" * 90},
            {"type": "result", "key": "k2", "result": {"say": f"{MARK} 좌석 발언", "stance": "찬성"}}]
    (raw / "wf_1.journal.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + f"\n{MARK} 깨진 줄\n",
                                           encoding="utf-8")
    (d / "2026-09-02_run2").mkdir()
    (d / "2026-09-02_run2" / "journal.jsonl").write_text(json.dumps({"type": "result", "result": "아" * 12}) + "\n", encoding="utf-8")


def _leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _keys_and_leaves(k, v, path)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, f"{path}[{i}]")
    else:
        yield ("leaf", path, o)


def _keys_and_leaves(k, v, path):
    yield ("key", path, k)
    yield from _leaves(v, f"{path}.{k}")


_ALLOWED_KEYS = {
    "rev", "made_at", "chars_per_token_p50", "sources", "card_review", "delib_jobs", "delib_runs_claude",
    "found", "unreadable", "rows", "rows_with_usage", "multi_attempt_rows", "llm_calls", "other_kind_rows",
    "jobs", "unreadable_files", "turns", "journals", "results", "bad_lines",
    "all", "by_kind", "sweep", "verdict", "offcard", "noinput", "summary", "other",
    "prompt_tokens", "output_tokens", "prompt_chars", "chars_per_token", "calls_in_flight", "experts_in_flight",
    "seat_output_chars", "chair_output_chars", "turns_per_job", "seat_output_tokens_est", "chair_output_tokens_est", "result_chars",
    "n", "mean", "std", "min", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99", "max", "hist", "edges", "counts",
}


@pytest.fixture()
def sources(tmp_path):
    db = tmp_path / "risk_review.db"
    _risk_db(db)
    _delib_jobs(tmp_path / "jobs")
    _delib_runs(tmp_path / "runs")
    return db, tmp_path / "jobs", tmp_path / "runs"


def _extract_cli(tmp_path, db, jobs, runs, *extra):
    out = tmp_path / "out" / "lengths.json"
    r = subprocess.run([sys.executable, str(LENGTHS_PY), "--out", str(out), "--risk-db", str(db), "--delib-jobs", str(jobs),
                        "--delib-runs", str(runs), *extra], capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return r, out


def test_추출기는_수만_내놓고_원장의_글은_어디에도_새지_않는다(tmp_path, sources):
    db, jobs, runs = sources
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    r, out = _extract_cli(tmp_path, db, jobs, runs)
    assert r.returncode == 0, r.stderr
    raw = out.read_text(encoding="utf-8")
    assert MARK not in raw and MARK not in r.stdout and MARK not in r.stderr, "본문 표식이 결과·출력에 샜다"
    res = json.loads(raw)
    for what, path, v in _leaves(res):
        if what == "key":
            assert v in _ALLOWED_KEYS, f"결과에 정해 두지 않은 이름 {v!r}({path}) — 원장의 글이 이름으로 샜을 수 있다"
        else:
            assert v is None or isinstance(v, (int, float, bool)), f"{path} 가 수가 아니다: {v!r}"
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before, "원장을 바꿨다(mode=ro 로만 연다)"
    assert sorted(p.name for p in db.parent.iterdir() if p.name.startswith("risk_review.db")) == ["risk_review.db"], "원장 옆에 파일을 남겼다"


def test_원장_질의는_글_열을_수로_바꿔서만_꺼낸다(tmp_path):
    """결과만이 아니라 프로세스로 들어오는 값부터 수다 — 종류는 차례 번호, 전문가는 DENSE_RANK 번호."""
    db = tmp_path / "r.db"
    _risk_db(db)
    con = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    rows = con.execute(L._CALLS_SQL).fetchall()
    con.close()
    assert rows and all(v is None or isinstance(v, (int, float)) for row in rows for v in row), rows


def test_추출기의_수(tmp_path, sources):
    db, jobs, runs = sources
    r, out = _extract_cli(tmp_path, db, jobs, runs)
    res = json.loads(out.read_text(encoding="utf-8"))
    src = res["sources"]
    assert src["card_review"] == {"found": True, "rows": 6, "rows_with_usage": 5, "multi_attempt_rows": 1, "llm_calls": 6,
                                  "other_kind_rows": 1}
    cr = res["card_review"]
    v = cr["by_kind"]["verdict"]
    assert v["prompt_tokens"]["n"] == 4 and v["prompt_tokens"]["p50"] == 2000 and v["prompt_tokens"]["max"] == 3000, "보충 시도는 시도마다 평균"
    assert v["output_tokens"]["p50"] == 200
    assert v["chars_per_token"]["n"] == 2 and v["chars_per_token"]["p50"] == 2.0, "글자/토큰은 시도 1회 호출에서만"
    assert cr["by_kind"]["other"]["prompt_tokens"]["n"] == 1 and set(cr["by_kind"]) == {"verdict", "sweep", "other"}
    a = cr["all"]["prompt_tokens"]
    assert (a["n"], a["min"], a["p50"], a["max"]) == (6, 500, 1000, 3000)
    assert a["hist"]["edges"][:3] == [0, 1, 2] and sum(a["hist"]["counts"]) == 6 and a["hist"]["edges"][-1] > 3000
    # 돌던 수 — 시작 100(A) 101(A) 102(B) 105(모르는 종류의 전문가) 200(C). 끝은 +10초·+1초.
    assert cr["calls_in_flight"]["max"] == 4 and cr["calls_in_flight"]["n"] == 5
    assert cr["experts_in_flight"]["max"] == 3 and cr["experts_in_flight"]["min"] == 1
    assert res["chars_per_token_p50"] == 2.0
    dj = res["delib_jobs"]
    assert src["delib_jobs"] == {"found": True, "jobs": 2, "unreadable_files": 1, "turns": 4}
    assert sorted([dj["seat_output_chars"]["min"], dj["seat_output_chars"]["max"]]) == [10, 1234]
    assert dj["chair_output_chars"]["n"] == 1 and dj["chair_output_chars"]["max"] == 777
    assert dj["turns_per_job"]["max"] == 3, "note 줄은 발언이 아니다"
    assert dj["seat_output_tokens_est"]["max"] == 617.0, "글자/토큰 중앙값(2.0)으로 나눈 추정"
    dr = res["delib_runs_claude"]
    assert src["delib_runs_claude"] == {"found": True, "journals": 2, "results": 3, "bad_lines": 1}
    assert dr["result_chars"]["min"] == 12


def test_추출기는_없는_출처를_말하고_덮지_않는다(tmp_path):
    r, out = _extract_cli(tmp_path, tmp_path / "없음.db", tmp_path / "없음", tmp_path / "없음2")
    assert r.returncode == 0, r.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["sources"]["card_review"]["found"] is False and res["card_review"] == {} and res["chars_per_token_p50"] is None
    assert "llm-capacity.sh 는 이 파일로 부하를 만들 수 없다" in r.stderr
    r2, _ = _extract_cli(tmp_path, tmp_path / "없음.db", tmp_path / "없음", tmp_path / "없음2")
    assert r2.returncode == 2 and "덮지 않는다" in r2.stderr
    r3, _ = _extract_cli(tmp_path, tmp_path / "없음.db", tmp_path / "없음", tmp_path / "없음2", "--force")
    assert r3.returncode == 0


def test_추출기의_기본_자리는_리포_루트와_형제_리포에서_유도한다(tmp_path, monkeypatch):
    """박스마다 리포 루트가 다르다(dev ~/claude · cae00 ~/Projects) — 절대경로가 아니라 리포 루트와 ../<형제 리포> 에서 찾는다."""
    portal, data = tmp_path / "Projects" / "HWAXPortal", tmp_path / "data"
    (portal / "infra").mkdir(parents=True)
    (data / "appdata" / "hwax_risk").mkdir(parents=True)
    (data / "svc" / "agent-server" / "artifacts").mkdir(parents=True)
    hub = tmp_path / "Projects" / "HEAXHub" / "var" / "app_data"
    hub.mkdir(parents=True)
    (hub / "hwax_risk").symlink_to(data / "appdata" / "hwax_risk")                 # /data 이관 박스의 브리지 심링크
    agent = tmp_path / "Projects" / "HWAXAgentServer"
    agent.mkdir()
    (agent / "artifacts").symlink_to(data / "svc" / "agent-server" / "artifacts")
    for k in ("DELIB_JOB_DIR", "ARTIFACT_DIR", "DELIB_ARCHIVE_ROOT", "HWAX_DATA_ROOT"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(L, "ROOT", portal)
    assert L.default_risk_db() == data / "appdata" / "hwax_risk" / "risk_review.db"
    assert L.default_delib_jobs() == data / "svc" / "agent-server" / "delib-jobs", "artifacts 의 실제 경로 옆(delib_jobs.JOB_DIR 규칙)"
    assert L.default_delib_runs() == Path("/data/delib-runs")
    (portal / "infra" / ".env").write_text(f"export HWAX_DATA_ROOT='{data}'   # 이관한 박스\n", encoding="utf-8")
    assert L.default_delib_runs() == data / "delib-runs"
    (portal / "infra" / ".env").write_text(f"HWAX_DATA_ROOT={data}\nDELIB_ARCHIVE_ROOT={tmp_path}/arch\n", encoding="utf-8")
    assert L.default_delib_runs() == tmp_path / "arch"
    (agent / ".env").write_text(f"DELIB_JOB_DIR={tmp_path}/jobs\n", encoding="utf-8")
    assert L.default_delib_jobs() == tmp_path / "jobs"
