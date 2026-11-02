# 심의 주제 고르기의 화면 쪽 셈(frontend subject.ts) — 후보는 그 사람의 도구 결과에서만 · 차수는 사소한 정규화 뒤 글자 그대로 · 보낼 꼴(과제 인사이트 그래프 M1)
"""docs/project-insight-graph PLAN §4.1 · §4.6. 프론트에 단위 시험 러너가 없어 TypeScript 를 옮겨 적어(transpile) node 로 함수를 부른다
(test_handoff_evidence_cap 과 같은 꼴).

  · 후보는 이 대화에서 부른 도구의 결과(StepForge find_plm_task · get_project_meta · list_projects, ODB 잡, DynaForge 리포트, 리스크 과제 stage)
    에서만 온다 — 어시스턴트의 글 · 실패한 호출 · JSON 으로 못 읽는(잘린) 결과는 보지 않는다. key 는 결과 행의 key 칸 그대로다.
  · 차수는 NFKC · 공백 · 소문자만 맞추고 '2차' · 'C2' · '양산' 은 차수가 아니다 — 에이전트 서버와 같은 코드 열한 개다(형제 리포를 읽어 견준다).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_front_window_payload import _node as _fe_node  # 서버 사본을 되살리는 시험들과 같은 길(conversations.api + chatStore 를 옮겨 적는다)

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"
CHAT = FE / "src/components/chat"
AGENT = ROOT.parent / "HWAXAgentServer" / "delib_subject.py"
_CONV = ["api/conversations.api.ts", "state/chatStore.ts"]

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 함수를 돌려 볼 수 없다",
)

KEY = "알파 개발_C2"
_FIND = {"query": KEY, "count": 2, "tasks": [
    {"key": KEY, "label": KEY, "active": True, "project": {"key": "PJ-ALPHA", "label": "알파 프로젝트", "active": True},
     "properties": {"task_code": "TC-1001", "aliases": ["알파"]}, "matched_by": ["key", "label"]},
    {"key": f"{KEY} 보강", "label": f"{KEY} 보강", "active": False, "project": None, "properties": {}, "matched_by": ["key"]}],
    "sync": {}}
_META = {"id": "019a2b3c4d5e6f7a8b9c0d1", "name": "알파 힌지 CAD", "code": "TC-1001",
         "revision": {"decided": True, "content_fp": "1a2b3c4d5e6f7a8b"},
         "plm_task": {"key": "베타 개발_C1", "label": "베타 개발_C1", "active": True, "properties": {"task_code": "TC-2001"},
                      "asked": "TC-2001", "resolved_via": "task_code"}}


@pytest.fixture(scope="module")
def js(tmp_path_factory):
    """subject.ts 를 CommonJS 로 옮겨 적고 함수 하나를 인자(JSON)로 부른다."""
    out = tmp_path_factory.mktemp("subject")
    (out / "run.cjs").write_text(
        "const ts = require('typescript'); const fs = require('fs');\n"
        f"const src = fs.readFileSync({json.dumps(str(CHAT / 'subject.ts'))}, 'utf8');\n"
        "const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } });\n"
        "fs.writeFileSync(__dirname + '/subject.js', js.outputText);\n"
        "const m = require('./subject.js');\n"
        "const [fn, arg] = process.argv.slice(2);\n"
        "const a = JSON.parse(arg);\n"
        "const r = fn === 'const' ? { STAGE_CODES: m.STAGE_CODES, TEXT: m.SUBJECT_TEXT_MAX, ARTS: m.SUBJECT_ARTIFACTS_MAX } : m[fn](...a);\n"
        "process.stdout.write(JSON.stringify(r === undefined ? null : r));\n", encoding="utf-8")

    def run(fn: str, *args):
        r = subprocess.run(["node", "run.cjs", fn, json.dumps(list(args), ensure_ascii=False)], cwd=str(out), capture_output=True,
                           text=True, timeout=120, env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                                        "NODE_PATH": str(FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return run


def test_차수는_사소한_정규화_뒤_글자_그대로만(js):
    for raw, want in (("dv1", "dv1"), (" ＤＶ２ ", "dv2"), ("PVR", "pvr"), ("M P", "mp"), ("2차", None), ("C2", None), ("양산", None),
                      ("dv-1", None), ("dv", None), ("pre1", None), (None, None), (3, None)):
        assert js("normRound", raw) == want, raw


def test_차수_코드와_상한이_에이전트_서버와_같다(js):
    if not AGENT.exists():
        pytest.skip(f"형제 리포 없음: {AGENT}")
    text = AGENT.read_text(encoding="utf-8")
    stages = re.search(r"^STAGES = \(([^)]*)\)", text, re.M)
    caps = re.search(r"^SP_TASK_MAX, ROUND_MAX, TEXT_MAX, REV_MAX, ARTIFACTS_MAX, WHY_MAX = (.+)$", text, re.M)
    assert stages and caps, "에이전트 서버 delib_subject 의 모양이 바뀌었다 — 이 추출도 고쳐라"
    got = js("const")
    assert got["STAGE_CODES"] == re.findall(r'"([a-z0-9]+)"', stages.group(1))
    _sp, _r, text_max, _rev, arts_max, _w = (int(x) for x in caps.group(1).split(","))
    assert (got["TEXT"], got["ARTS"]) == (text_max, arts_max)


def _conv(*activity, text="") -> dict:
    return {"id": "c1", "messages": [{"id": "m1", "role": "assistant", "text": text, "ts": 1, "activity": list(activity)}]}


def _act(tool: str, body, ok=True) -> dict:
    raw = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    return {"ts": 1, "step": tool, "tool": tool, "ok": ok, "result_full": raw}


def test_후보는_그_사람의_도구_결과에서만_오고_key_는_결과_행_그대로다(js):
    got = js("candidatesFromConversation", _conv(
        _act("heaxstep_forge_find_plm_task", _FIND),
        _act("get_project_meta", _META),
        _act("find_plm_task", {**_FIND, "tasks": [{**_FIND["tasks"][0], "key": "실패한 호출의 과제"}]}, ok=False),
        _act("find_plm_task", json.dumps(_FIND, ensure_ascii=False)[:120] + "…#a1b2c3"),
        _act("search_reports", {"tasks": [{"key": "다른 앱 결과"}]}),
        text=f"과제 「모델이 지어낸 과제」 와 {KEY} 를 보았다"))
    sp = {r["key"]: r for r in got["sp"]}
    assert set(sp) == {KEY, f"{KEY} 보강", "베타 개발_C1"}, "도구 결과의 행만 — 실패한 호출 · 잘린 결과 · 다른 도구 · 어시스턴트 글은 아니다"
    assert sp[KEY]["taskCode"] == "TC-1001" and sp[KEY]["project"] == "알파 프로젝트" and sp[KEY]["active"] is True
    assert sp[f"{KEY} 보강"]["active"] is False
    assert "get_project_meta" in sp["베타 개발_C1"]["from"], "기구 CAD 과제의 허브 과제(get_project_meta.plm_task)도 후보다"
    assert got["artifacts"] == [{"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b3c4d5e6f7a8b", "label": "알파 힌지 CAD",
                                 "from": "이 대화의 get_project_meta"}]


def test_보드_해석_리포트_차수_후보(js):
    report = {"reports": [{"id": "01hzx3k5q9v8n7m6p5r4s3t2w1", "title": "알파 낙하", "eng_meta": {"dev_revision": {"phase": "dv", "round": "2",
                                                                                                          "code": "DV2"}}}]}
    odb = {"jobs": [{"job_id": "ABCDEF0123456789", "project": "알파", "model": "SM-A100", "revision": "B", "board_type": "Main"},
                    {"job_id": "abcdef012345678", "project": "짧은 id"}]}
    risk = {"projects": [{"id": "x" * 32, "stage": "PV1"}, {"id": "y" * 32, "stage": "dv"}]}
    got = js("candidatesFromConversation", _conv(_act("dynaforge_list_reports", report), _act("find_job", odb),
                                                 _act("risk_list_projects", risk)))
    kinds = {(a["kind"], a["id"]): a for a in got["artifacts"]}
    assert kinds[("cae", "01HZX3K5Q9V8N7M6P5R4S3T2W1")]["rev"] == "dv2"
    assert kinds[("ecad", "abcdef0123456789")]["rev"] == "B" and len(kinds) == 2, "16진 16자가 아닌 job_id 는 보드가 아니다"
    assert [r["code"] for r in got["rounds"]] == ["dv2", "pv1"], "꼴에 맞는 원천 값만(리스크 앱의 'dv' 는 차수가 아니다)"


def test_보낼_꼴(js):
    assert js("subjectWire", None) is None
    assert js("subjectWire", {"spTask": " ", "round": "", "text": "  ", "artifacts": []}) is None, "고르지 않으면 주제가 없다"
    art = {"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b", "label": "x", "from": "y"}
    assert js("subjectWire", {"spTask": f" {KEY} ", "round": "dv1", "text": " 메모 ", "artifacts": [art]}) == \
        {"sp_task": KEY, "round": "dv1", "text": "메모", "artifacts": [{"kind": "mcad", "id": "019a2b3c4d5e6f7a8b9c0d1", "rev": "1a2b"}]}
    many = js("subjectWire", {"spTask": KEY, "round": "", "text": "가" * 900, "artifacts": [art] * 12})
    assert len(many["text"]) == 500 and len(many["artifacts"]) == 8 and "round" not in many


def _from_raw(raw):
    """대화 복원 모듈의 subjectFromRaw — 서버 사본을 되살리는 다른 시험들과 같은 길(conversations.api + chatStore 를 옮겨 적는다)로 부른다."""
    return _fe_node(_CONV, "const c = require('./api/conversations.api.js'); out(c.subjectFromRaw(input) ?? null);", raw)


@pytest.mark.parametrize("raw", [None, "알파", [], {"sp_task": KEY}, {"sp_task": KEY, "sp_state": "verified"}, {"sp_state": "Confirmed"}])
def test_서버가_낸_주제의_꼴이_아니면_두지_않는다(raw):
    """실시간 사건(mergeDelib)과 새로고침의 복원(serverMessagesToLocal)이 같은 함수다 — 확인 상태가 셋 가운데 하나가 아니면 없다."""
    assert _from_raw(raw) is None


def test_서버가_낸_주제는_알려진_칸만_꼴대로_옮긴다():
    raw = {"sp_task": KEY, "sp_state": "claimed", "sp_why": "까닭", "round": "dv1", "text": 3, "junk": 1, "sp_resolved_by": {"tool": "t"},
           "artifacts": [{"kind": "ecad", "id": "abcdef0123456789", "rev": "B", "x": 1}, {"kind": "zz", "id": "1"}, "a", {"kind": "cae"}]}
    assert _from_raw(raw) == {"sp_task": KEY, "sp_state": "claimed", "sp_why": "까닭", "round": "dv1", "text": "",
                              "artifacts": [{"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}, \
        "모르는 칸 · 꼴이 아닌 설계 자료는 버린다"
    assert _from_raw({"sp_state": "none", "round": None})["round"] is None


def test_새로고침은_답_meta_의_주제를_같은_꼴로만_되살린다():
    """복원 길(serverMessagesToLocal) — 확인 상태를 지어낸 meta.subject 는 그리지 않는다(반대 검토 11-02 — 종전엔 이 길에 시험이 없었다)."""
    def server(meta):
        return [{"role": "user", "content": "/심의 x", "ts": 1},
                {"role": "persona", "content": "발언", "persona": "mech-a", "round": 1, "ts": 2},
                {"role": "assistant", "content": "결정문", "ts": 3, "meta": meta}]
    script = ("const c = require('./api/conversations.api.js');"
              " out(c.serverMessagesToLocal(input).filter((m) => m.delib).map((m) => m.delib.subject ?? null));")
    rec = {"sp_task": KEY, "sp_state": "confirmed", "sp_resolved_by": {"tool": "t"}, "round": "dv1", "text": "", "artifacts": []}
    assert _fe_node(_CONV, script, server({"subject": rec})) == [{"sp_task": KEY, "sp_state": "confirmed", "round": "dv1", "text": "",
                                                                  "artifacts": []}]
    assert _fe_node(_CONV, script, server({"subject": {**rec, "sp_state": "verified"}})) == [None]
    assert _fe_node(_CONV, script, server(None)) == [None], "주제 없는 심의는 종전 그대로"


def test_실시간_사건과_새로고침_복원이_같은_꼴_함수를_지난다():
    """mergeDelib(ChatContext — 화면 부품 파일이라 node 로 못 부른다)이 복원과 같은 subjectFromRaw 를 부르는지 소스로 본다 — 한쪽이 꼴을 안 보면
    그쪽으로 아무 값이나 '확인됐다' 로 그려진다(반대 검토 11-02 — 종전 mergeDelib 은 객체면 그대로 두었다)."""
    ctx = (FE / "src/state/ChatContext.tsx").read_text(encoding="utf-8")
    case = ctx[ctx.index("case 'subject':"):]
    case = case[:case.index("break;")]
    assert "subjectFromRaw(e.subject)" in case and " as DelibData" not in case, case
    assert re.search(r"import \{[^}]*\bsubjectFromRaw\b[^}]*\} from '\.\./api/conversations\.api';", ctx), "복원과 같은 함수를 받는다"
    conv = (FE / "src/api/conversations.api.ts").read_text(encoding="utf-8")
    assert "subjectFromRaw((m.meta" in conv and "function subjectFromMeta" not in conv


def test_이어하기는_서버가_확인한_주제의_받는_칸만_다시_싣는다(js):
    rec = {"sp_task": KEY, "sp_state": "confirmed", "sp_resolved_by": {"tool": "t"}, "round": "dv3", "round_by": "person", "text": "메모",
           "artifacts": [{"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}
    assert js("subjectFromPrior", rec) == {"sp_task": KEY, "round": "dv3", "text": "메모",
                                           "artifacts": [{"kind": "ecad", "id": "abcdef0123456789", "rev": "B"}]}
    unknown = js("subjectFromPrior", {**rec, "round": None, "sp_state": "claimed"})
    assert "round" not in unknown and unknown["sp_task"] == KEY, "차수 모름은 싣지 않는다 — 서버가 다시 확인한다"
    assert js("subjectFromPrior", None) is None
