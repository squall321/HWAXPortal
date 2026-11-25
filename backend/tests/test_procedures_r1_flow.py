# R1 적층 굴곡 수명을 포털 경로로 끝까지 — 씨앗 가져오기 → 판본 → live 실행 → 사람 확인 → 완주 → 펼침 반경만 바꿔 재생(docs/procedures W-120)
"""checklist S1 '검증' 의 'dev 첫 절차 완주 → 저장 → 변수 바꿔 재생' 과 S2 의 '완주 → 저장 → 반경만 바꿔 재생' 을 이 박스에서 자격 없이 되는 데까지 닫는다.

지나가는 것은 포털의 진짜 길 전부다 — 라우트(씨앗 가져오기 · 판본 · 실행 시작 · 확인 · 결과) · 저장 검증(게이트웨이 스키마 대조) · 실행기(세션 ·
드리프트 · 치환 · 게이트 · 판정 · save) · 원장. 게이트웨이만 대역이고, 대역이 내는 글은 **실제 계산 녹취**다 — ②~⑥ 은 LaminateAnalyzerMCP 원천을
그대로 불러 받은 글(fixtures/procedures/laminate_r1_local.json), ① 은 09-14 dev 게이트웨이 실호출(laminate_responses.json `bend`), ⑦ 은 09-16 게이트웨이로
부른 RA dry_run 응답(thermal_shock_responses.json — 다른 절차의 제목이 든 응답 그대로다, 이 시험은 그 꼴만 쓴다). 인공 고정물이 아니다(W-75).

못 지나가는 것 — 게이트웨이를 **사람의 PAT** 로 지나는 홉. 이 박스에는 사람 자격이 없고 만들지 않는다(W-38). 그 홉은 checklist S1 의 브라우저 완주 ·
'포털 화면에서 R1 을 실제로 완주'(사람)가 덮는다.

R 에 대해 — 씨앗은 D-287 뒤로 굽힘반경을 사람에게 묻지 않고 형상에서 읽는다(①). 그래서 '반경만 바꿔' 의 변수는 펼친 상태 반경 `r_unfold` 다. 예제 형상
(R 6 mm)은 굽힌 상태에서 이미 첫 사이클 파손이라(Tsai-Wu R 0.0757 — W-38) 수명은 두 판 다 1 사이클이고, 바뀌는 것은 ④ 의 등가하중과 ⑥ 의 층별
진폭 · 평균 · 층별 수명이다. ⑤ 는 굽힌 상태라 형상이 정하므로 그대로다.
"""
import json
from pathlib import Path

import httpx
import yaml

from tests.test_procedures_routes import PREFIX, _until, client, user  # noqa: F401  (client · user 는 픽스처)

FIX = Path(__file__).parent / "fixtures" / "procedures"
SEED = Path(__file__).resolve().parents[2] / "docs" / "procedures" / "fixtures" / "laminate-bend-life.yaml"
LOCAL = json.loads((FIX / "laminate_r1_local.json").read_text(encoding="utf-8"))
DEV = json.loads((FIX / "laminate_responses.json").read_text(encoding="utf-8"))
TS = json.loads((FIX / "thermal_shock_responses.json").read_text(encoding="utf-8"))
REC = LOCAL["records"]
# 녹취의 입력 적층 — 씨앗의 예시 그대로다. 씨앗의 예시를 바꾸면 녹취를 다시 받는다(대역이 다른 적층에 옛 답을 내지 않게 맞댄다).
LAMINATE = next(v["example"] for v in yaml.safe_load(SEED.read_text(encoding="utf-8"))["vars"] if v["key"] == "laminate")


def _body(key: str) -> dict:
    return json.loads(REC[key]["text"])


def _eq(key: str) -> dict:
    return _body(key)["data"]["equivalent_loads"]


class _R1Gateway:
    """게이트웨이 대역 — 받은 인자로 녹취를 고른다. 녹취에 없는 인자 · dry_run 없는 보고서 초안은 **실패로 답하고 적어 둔다**(바깥 쓰기를 흉내 내지 않는다)."""

    SCHEMAS = {**LOCAL["schemas"], "create_report_draft": TS["schemas"]["create_report_draft"]}
    BACKEND = {"bend_profile": "heax-step_forge", "create_report_draft": "reportarchive",
               **{t: "heax-laminate_analyzer_mcp" for t in LOCAL["schemas"] if t != "bend_profile"}}

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.strays: list[str] = []
        self.alias = {f"{b.replace('-', '')}_{t}": t for t, b in self.BACKEND.items()}

    def _answer(self, tool: str, a: dict) -> str | None:
        if self.BACKEND.get(tool) == "heax-laminate_analyzer_mcp" and a.get("laminate") != LAMINATE:
            return None   # 녹취는 씨앗의 예시 적층(객체)으로 받았다 — 글로 온 적층(형 맞추기 W-35 가 빠진 것)이나 다른 적층에는 답이 없다
        if tool == "bend_profile":
            return json.dumps(DEV["bend"]["body"], ensure_ascii=False, indent=2) if a == {
                "project_id": "R1-굴곡수명-예제(U자판)", "part": "UBEND_1"} else None
        if tool == "analyze_laminate":
            return REC["analyze"]["text"]
        if tool == "solve_prescribed_curvature":
            pick = {6.0: "bent", 1000.0: "flat_1000", 100.0: "flat_100"}.get(float(a.get("bend_radius", -1)))
            return REC[pick]["text"] if pick and (a["bend_axis"], a["width"]) == ("x", "free") else None
        if tool == "recover_ply_stresses":
            return REC["plies"]["text"] if a.get("loads") == _eq("bent") else None
        if tool == "estimate_fatigue_life":
            lo = {json.dumps(_eq(k), sort_keys=True): k for k in ("flat_1000", "flat_100")}.get(
                json.dumps(a.get("loads_min"), sort_keys=True))
            return REC[f"life_{lo[5:]}"]["text"] if lo and a.get("loads_max") == _eq("bent") else None
        if tool == "create_report_draft":
            return json.dumps(TS["ra_create_dry_run"], ensure_ascii=False, indent=2) if a.get("dry_run") is True else None
        return None

    def handler(self, req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content or b"{}") if req.content else {}
        m = body.get("method")
        if m == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}, headers={"mcp-session-id": "r1"})
        sse = {"content-type": "text/event-stream"}
        if m == "tools/list":
            tools = [{"name": t, "description": "", "inputSchema": s} for t, s in self.SCHEMAS.items()]
            return httpx.Response(200, text=f"data: {json.dumps({'jsonrpc': '2.0', 'id': 3, 'result': {'tools': tools}})}\n\n", headers=sse)
        if m == "tools/call":
            p = body["params"]
            assert p["name"] == "invoke_tool", p["name"]
            tool = self.alias.get(p["arguments"]["name"], p["arguments"]["name"])
            args = p["arguments"].get("arguments") or {}
            self.calls.append((tool, args))
            text = self._answer(tool, args)
            if text is None:
                self.strays.append(tool)
            res = ({"isError": False, "content": [{"type": "text", "text": text}]} if text is not None else
                   {"isError": True, "content": [{"type": "text", "text": f"대역에 없는 호출: {tool}"}]})
            return httpx.Response(200, text=f"data: {json.dumps({'jsonrpc': '2.0', 'id': 2, 'result': res})}\n\n", headers=sse)
        return httpx.Response(200)

    def install(self, c) -> None:
        from app.procedures.runner import ProceduresRunner

        c.app.state.procedures_runner = ProceduresRunner(
            settings=c.app.state.procedures_runner.settings, store=c.app.state.procedures_store,
            client=httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=10.0),
            mint_pat=lambda p, run, ix: "pat-r1")


def _run_to_done(c, h, pid: str, form: dict) -> dict:
    """live 로 시작 → ⑦ 확인 카드에서 멈춤 → 사람 확인 → 끝. 화면이 하는 그대로 HTTP 로만 간다."""
    r = c.post(f"{PREFIX}/runs", json={"procedure_id": pid, "vars": form, "mode": "live"}, headers=h)
    assert r.status_code == 202, r.text
    rid = r.json()["run_id"]

    def state():
        return c.get(f"{PREFIX}/runs/{rid}", headers=h).json()["state"]
    _until(lambda: state() in ("gated", "failed", "done"), "⑦ 확인 카드까지")
    run = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert run["state"] == "gated", (run["state"], run.get("stage"), [(s["ix"], s["state"], s.get("error")) for s in run["steps"]])
    gate = run["steps"][6]
    assert gate["tool"] == "create_report_draft" and gate["stage"] == "gate" and gate["args"]["dry_run"] is True, gate
    assert [s["state"] for s in run["steps"][:6]] == ["done"] * 6, [(s["state"], s.get("error")) for s in run["steps"]]
    ack = c.post(f"{PREFIX}/runs/{rid}/steps/6/ack", json={"args_sha256": gate["args_sha256"]}, headers=h)
    assert ack.status_code == 200 and ack.json()["resumed"] is True, ack.text
    _until(lambda: state() in ("done", "failed"), "확인 뒤 끝나기")
    run = c.get(f"{PREFIX}/runs/{rid}", headers=h).json()
    assert run["state"] == "done", (run["state"], run.get("stage"), run["steps"][-1])
    return run


def _result(c, h, rid: str, ix: int) -> dict:
    got = c.get(f"{PREFIX}/runs/{rid}/steps/{ix}/result", headers=h)
    assert got.status_code == 200, got.text
    return json.loads(got.json()["text"])


def test_녹취는_W38_의_게이트웨이_실호출과_같은_답이다():
    """녹취가 dev 에서 사람이 본 답과 같아야 이 시험의 완주가 그 답의 완주다 — 09-14 게이트웨이 실호출(W-38)의 수와 맞댄다."""
    assert round(_eq("bent")["M"][0], 1) == 3842.7 and round(_eq("flat_1000")["M"][0], 1) == 23.1
    assert round(_body("plies")["data"]["first_ply_failure"]["tsai_wu_R"], 4) == 0.0757
    assert _body("life_1000")["data"]["life_cycles"] == 1.0
    assert all(REC[k]["text"].startswith("{\n") for k in REC), "원천이 내는 글은 들여쓴 JSON 이다 — 한 줄로 바꾸면 고정물이 거짓이 된다(W-75)"


def test_R1_을_포털_경로로_완주하고_펼침_반경만_바꿔_재생한다(user):
    c, h = user
    gw = _R1Gateway()
    gw.install(c)

    # 저장 — 씨앗을 들이고(같은 저장 검증 · 게이트웨이 스키마 대조) dev 몫으로 ⑦ 에 dry_run 을 단 판본을 올린다
    made = c.post(f"{PREFIX}/seeds/laminate-bend-life/import", headers=h)
    assert made.status_code == 201, made.text
    assert not [w for w in made.json()["warnings"] if "대조를 건너뛰" in w or "안 보인다" in w], made.json()["warnings"]
    pid = made.json()["id"]
    spec = c.get(f"{PREFIX}/procedures/{pid}", headers=h).json()["spec"]
    spec["steps"][6]["args"]["dry_run"] = True
    v2 = c.post(f"{PREFIX}/procedures/{pid}/versions", json={"title": spec["title"], "spec": spec}, headers=h)
    assert v2.status_code == 201 and v2.json()["version_no"] == 2, v2.text

    # 완주 — 입력은 화면이 보내는 꼴(전부 문자열 · 적층은 JSON 글)
    ex = {v["key"]: v["example"] for v in spec["vars"]}
    form = {k: json.dumps(v, ensure_ascii=False) if k == "laminate" else str(v) for k, v in ex.items()}
    first = _run_to_done(c, h, pid, form)
    assert [t for t, _ in gw.calls] == ["bend_profile", "analyze_laminate", "solve_prescribed_curvature",
                                       "solve_prescribed_curvature", "recover_ply_stresses", "estimate_fatigue_life",
                                       "create_report_draft"], gw.calls
    assert gw.strays == [], f"녹취에 없는 인자로 불렀다(또는 dry_run 없이 보고서를 만들려 했다): {gw.strays}"
    got = first["inputs"]
    assert got["r_designed"] == 6.0 and got["t_part"] == 1.2 and got["bend_basis"] == "analytic_cylinder_pair"
    assert round(got["tsai_wu_r"], 4) == 0.0757 and got["failure_mode"] == "fiber_tension" and got["life_cycles"] == 1.0
    title1 = gw.calls[-1][1]["title"]
    assert "UBEND_1" in title1 and "R 6.0 ↔ 1000" in title1, title1

    # 변수 바꿔 재생 — 펼침 반경만 1000 → 100
    n = len(gw.calls)
    second = _run_to_done(c, h, pid, {**form, "r_unfold": "100"})
    again = gw.calls[n:]
    assert gw.strays == [] and len(again) == 7, again
    assert first["procedure_version_id"] == second["procedure_version_id"]
    assert float(again[3][1]["bend_radius"]) == 100.0, "④ 는 바꾼 값으로 다시 계산한다"
    assert again[5][1]["loads_min"] == _eq("flat_100") != _eq("flat_1000"), "⑥ 은 이 실행의 ④ 가 뽑은 하중을 받는다 — 지난 실행의 중간값이 딸려 오지 않는다"
    assert again[2][1] == gw.calls[2][1] and again[4][1] == gw.calls[4][1], "③ · ⑤ 는 형상의 반경이라 인자가 그대로다"
    assert second["inputs"]["tsai_wu_r"] == got["tsai_wu_r"] and second["inputs"]["life_cycles"] == 1.0
    assert "R 6.0 ↔ 100 " in again[6][1]["title"], again[6][1]["title"]

    # 층별로는 바뀐다 — 첫 사이클 파손이라 수명 칸은 같아도 진폭 · 평균 · 층별 수명이 반경을 따른다
    l1, l2 = _result(c, h, first["id"], 5)["data"], _result(c, h, second["id"], 5)["data"]
    a1, a2 = l1["critical_ply"]["sigma_amplitude"], l2["critical_ply"]["sigma_amplitude"]
    assert round(a1, 1) == 9022.9 and round(a2, 1) == 8532.7, (a1, a2)
    assert l1["plies"][1]["cycles_to_failure"] == 1.0 and round(l2["plies"][1]["cycles_to_failure"], 2) == 2.34
    m1, m2 = _result(c, h, first["id"], 3)["data"], _result(c, h, second["id"], 3)["data"]
    assert round(m1["equivalent_loads"]["M"][0], 2) == 23.06 and round(m2["equivalent_loads"]["M"][0], 2) == 230.56

    # 한 절차의 이력으로 두 실행이 남는다
    hist = c.get(f"{PREFIX}/runs", params={"procedure_id": pid}, headers=h).json()["runs"]
    assert {r["id"] for r in hist} >= {first["id"], second["id"]}
