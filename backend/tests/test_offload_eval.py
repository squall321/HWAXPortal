# 토큰 절감 2판 비교 테스트셋(infra/offload-eval/run-eval.mjs)을 가짜 claude · 가짜 게이트웨이로 돌려 울타리 · PAT · 이어 하기 · 셈 · 눈가림을 단언한다
#
# 진짜 claude -p 는 부르지 않는다(비용 — docs/token-saving TS-14). 가짜 claude 는 공식 문서의 stream-json 꼴(system/init · assistant tool_use ·
# user tool_result · result 의 usage · total_cost_usd · duration_ms · num_turns · permission_denials)을 그대로 낸다 — 가짜가 진짜와 다르면 판정
# 결함을 숨긴다. 가짜 게이트웨이는 /tools-map · /health · POST /mcp(initialize) 셋만 안다. node 가 없으면 건너뛴다.
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "infra/offload-eval"
RUN = EVAL / "run-eval.mjs"
PAT = "hwax_pat_EVALTEST_9f8e7d6c5b4a3210"
OFFLOAD = ["delegate_start", "delegate_status", "delegate_result", "delegate_cancel",
           "draft_section", "llm_transform", "result_get", "result_ask"]


def _node_major() -> int:
    node = shutil.which("node")
    if not node:
        return 0
    out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    m = re.match(r"v(\d+)", out)
    return int(m.group(1)) if m else 0


pytestmark = pytest.mark.skipif(_node_major() < 18, reason="node 18 이상이 없다 — 실행기(run-eval.mjs)는 node 로 돈다")

# 가짜 게이트웨이의 /tools-map — 읽기 · 쓰기 · 2판 · 게이트웨이 로컬이 섞여 있다. delegate_status 는 이름 낱말로 routine_read 에 들어온 꼴(baseline 은
# 그래도 빼야 한다), figure_list 는 이 박스에서 백엔드 도구다(게이트웨이 로컬 조회 목록에 이름이 있어도 열지 않는다).
TOOLS_MAP = {
    "map": {
        "find_parts": "heax-step_forge", "list_projects": "heax-step_forge", "search_records": "ai-data-hub",
        "create_report": "reportarchive", "delete_part": "heax-step_forge",
        **{n: ("_gateway" if n.startswith("result_") else "hwax-deliberation") for n in OFFLOAD},
        "search_tools": "_gateway", "list_tool_apps": "_gateway", "invoke_tool": "_gateway", "rest_call": "_gateway",
        "save_conversation": "_gateway", "routine_run_start": "_gateway", "figure_get": "_gateway",
        "figure_list": "some-backend",
    },
    "routine_read": ["delegate_status", "find_parts", "list_projects", "search_records"],
    "write": ["create_report", "delete_part"],
}
BASE_ALLOW = {"find_parts", "list_projects", "search_records", "search_tools", "list_tool_apps", "figure_get"}

FAKE_HELP = """Usage: claude [options] [command] [prompt]
  -p, --print  --output-format <format>  --verbose  --mcp-config <configs...>  --strict-mcp-config
  --settings <file-or-json>  --setting-sources <sources>  --permission-mode <mode> (choices: "acceptEdits", "default", "dontAsk", "plan")
  --tools <tools...>  --append-system-prompt <prompt>  --model <model>  --no-session-persistence  --max-budget-usd <amount>
"""

# 가짜 claude — 갈래(--append-system-prompt 유무)마다 정한 사건을 낸다. 받은 것은 FAKE_DIR/calls/<n>.json 에 적는다(Authorization 값은 sha 로만).
FAKE = r'''#!__PY__
import hashlib, json, os, stat, sys
D = os.environ["FAKE_DIR"]
a = sys.argv[1:]
if a == ["--version"]:
    print("2.1.300 (Claude Code)"); sys.exit(0)
if a == ["--help"]:
    print(__HELP__); sys.exit(0)
def opt(k):
    return a[a.index(k) + 1] if k in a else None
os.makedirs(os.path.join(D, "calls"), exist_ok=True)
n = len(os.listdir(os.path.join(D, "calls")))
def mode(p):
    return oct(stat.S_IMODE(os.stat(p).st_mode))
def emit(o):
    print(json.dumps(o, ensure_ascii=False), flush=True)
if opt("--output-format") == "json":
    prompt = sys.stdin.read()
    with open(os.path.join(D, "calls", f"{n:03d}.json"), "w") as f:
        json.dump({"kind": "judge", "argv": a, "stdin": prompt, "env_has_pat": "HWAX_GATEWAY_PAT" in os.environ}, f, ensure_ascii=False)
    bad = os.path.join(D, "judge_bad_done")
    if os.environ.get("FAKE_JUDGE_BAD_ONCE") and not os.path.exists(bad):
        open(bad, "w").close()
        emit({"type": "result", "subtype": "success", "is_error": False, "result": "판정은 이렇습니다 — 둘 다 좋다", "total_cost_usd": 0.02, "usage": {}, "num_turns": 1, "duration_ms": 900})
        sys.exit(0)
    sa = prompt.split("## 답 A", 1)[1].split("## 답 B", 1)[0]
    w = "B" if "999.25" in sa else "A"
    lo = "A" if w == "B" else "B"
    v = {"winner": w, "scores": {w: {"correct": 5, "complete": 5, "clear": 4}, lo: {"correct": 3, "complete": 4, "clear": 4}}, "reason": "수치가 근거와 맞는다"}
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "```json\n" + json.dumps(v, ensure_ascii=False) + "\n```", "total_cost_usd": 0.05, "usage": {"input_tokens": 3000, "output_tokens": 120}, "num_turns": 1, "duration_ms": 4000})
    sys.exit(0)
mcp_p, set_p = opt("--mcp-config"), opt("--settings")
mcp = json.load(open(mcp_p)); st = json.load(open(set_p))
h = mcp["mcpServers"]["hwax"]["headers"]
offload = "--append-system-prompt" in a
cap = {"kind": "run", "argv": [x for x in a], "prompt": opt("-p"), "cwd": os.getcwd(), "mcp_path": mcp_p, "settings_path": set_p,
       "mcp_mode": mode(mcp_p), "settings_mode": mode(set_p), "tmp_mode": mode(os.path.dirname(mcp_p)),
       "url": mcp["mcpServers"]["hwax"]["url"], "type": mcp["mcpServers"]["hwax"]["type"],
       "headers": {k: (v if k != "Authorization" else "sha:" + hashlib.sha256(v.encode()).hexdigest()) for k, v in h.items()},
       "settings": st, "env_has_pat": "HWAX_GATEWAY_PAT" in os.environ, "env_connectors": os.environ.get("ENABLE_CLAUDEAI_MCP_SERVERS")}
with open(os.path.join(D, "calls", f"{n:03d}.json"), "w") as f:
    json.dump(cap, f, ensure_ascii=False)
tools = [t for t in (opt("--tools") or "").split(",") if t] + [x for x in st["permissions"]["allow"] if x.startswith("mcp__")]
tools += [t for t in os.environ.get("FAKE_INIT_EXTRA", "").split(",") if t]
sid = "sess-%03d" % n
emit({"type": "system", "subtype": "init", "uuid": "u0", "session_id": sid, "apiKeySource": "none", "claude_code_version": "2.1.300",
      "cwd": os.getcwd(), "tools": tools, "mcp_servers": [{"name": "hwax", "status": "connected"}], "model": opt("--model"),
      "permissionMode": "dontAsk", "slash_commands": [], "output_style": "default", "skills": [], "plugins": []})
marker = os.path.join(D, "failed_once")
if os.environ.get("FAKE_FAIL_ONCE") and not os.path.exists(marker):
    open(marker, "w").close()
    print("API Error: connection reset", file=sys.stderr); sys.exit(1)
slow = os.path.join(D, "slow_once")
if os.environ.get("FAKE_SLOW_ONCE") and not os.path.exists(slow):
    open(slow, "w").close()
    import signal, time
    def on_int(*_):   # 진짜처럼 SIGINT 에 턴을 접고 result 를 낸다(반쪽 답)
        emit({"type": "result", "subtype": "success", "uuid": "res", "session_id": sid, "duration_ms": 1000, "duration_api_ms": 900, "is_error": False,
              "num_turns": 1, "result": "반쪽", "stop_reason": None, "total_cost_usd": 0.1, "usage": {"input_tokens": 1, "output_tokens": 1},
              "modelUsage": {}, "permission_denials": []})
        sys.exit(0)
    signal.signal(signal.SIGINT, on_int)
    time.sleep(60)
if os.environ.get("FAKE_LEAK"):
    print("debug header " + h["Authorization"], file=sys.stderr)
def use(i, name, inp):
    emit({"type": "assistant", "uuid": "a" + i, "session_id": sid, "parent_tool_use_id": None,
          "message": {"id": "msg_" + i, "type": "message", "role": "assistant", "model": opt("--model"), "content": [{"type": "tool_use", "id": i, "name": name, "input": inp}],
                      "stop_reason": "tool_use", "usage": {"input_tokens": 10, "output_tokens": 5}}})
def res(i, text, err=False):
    emit({"type": "user", "uuid": "r" + i, "session_id": sid, "parent_tool_use_id": None,
          "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": i, "content": [{"type": "text", "text": text}], "is_error": err}]}})
rows = "\n".join(f"| 파트 {k} | PC | {1234.5 if k == 1 else 100 + k} |" for k in range(1, 11))
denials = []
if not offload:
    use("t1", "mcp__hwax__search_tools", {"query": "파트 목록"})
    leak = (" 인증 " + h["Authorization"]) if os.environ.get("FAKE_LEAK") else ""
    res("t1", "도구 결과 — 부피 1234.5 mm3 · 응력 456.7 MPa · 101 102 103 104 105 106 107 108 109 110" + leak)
    use("t2", "mcp__hwax__invoke_tool", {"name": "delete_part", "arguments": {}})
    res("t2", "Permission to use mcp__hwax__invoke_tool has been denied.", True)
    denials = [{"tool_name": "mcp__hwax__invoke_tool", "tool_use_id": "t2", "tool_input": {"name": "delete_part"}}]
    if os.environ.get("FAKE_VIOLATE"):
        use("t3", "mcp__hwax__delete_part", {"id": 1})
        res("t3", '{"ok": true}')
    answer = "| 파트 | 재료 | 부피 |\n|---|---|---|\n" + rows + "\n\n최대 부피는 1234.5 이고 합은 999.25 다."
    cost, u, dur, turns = 1.0, {"input_tokens": 1000, "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 50000, "output_tokens": 800}, 60000, 4
else:
    use("d1", "mcp__hwax__delegate_start", {"task": "파트 표"})
    res("d1", '{"job_id": "dj1", "status": "queued", "max_steps": 12, "max_minutes": 10}')
    body = {"job_id": "dj1", "status": "done", "view": "full", "answer": "응력 456.7 · 부피 1234.5 · " + " ".join(str(100 + k) for k in range(1, 11)),
            "numbers": {"checked": 2, "mismatched": ["777.5"]}, "model": "qwen", "steps": 3, "tokens": {"input": 1200, "output": 300}, "evidence": []}
    for i in ("d2", "d3"):
        use(i, "mcp__hwax__delegate_result", {"job_id": "dj1"})
        res(i, json.dumps(body, ensure_ascii=False))
    use("d4", "mcp__hwax__draft_section", {"outline": "요약"})
    res("d4", '{"draft": "초안", "numbers": {"checked": 0, "mismatched": []}, "sources": [], "model": "glm"}')
    answer = ("| 파트 | 재료 | 부피 |\n|---|---|---|\n" + rows + "\n\n응력은 456.7 이다. delegate_start 로 맡겼고 손잡이 res_ABCDEFGH1234 를 받았다."
              " mcp__hwax__result_ask 로 물었다.")
    cost, u, dur, turns = 0.6, {"input_tokens": 600, "cache_creation_input_tokens": 1500, "cache_read_input_tokens": 30000, "output_tokens": 500}, 45000, 3
emit({"type": "assistant", "uuid": "z", "session_id": sid, "parent_tool_use_id": None,
      "message": {"id": "msg_z", "type": "message", "role": "assistant", "content": [{"type": "text", "text": answer}], "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1}}})
sub = os.environ.get("FAKE_SUBTYPE", "success")
emit({"type": "result", "subtype": sub, "uuid": "res", "session_id": sid, "duration_ms": dur, "duration_api_ms": dur - 5000, "is_error": sub != "success",
      "num_turns": turns, "result": answer, "stop_reason": "end_turn", "total_cost_usd": cost, "usage": u,
      "modelUsage": {opt("--model"): {"inputTokens": u["input_tokens"], "outputTokens": u["output_tokens"], "costUSD": cost}}, "permission_denials": denials})
'''


class _GW(BaseHTTPRequestHandler):
    tools_map = TOOLS_MAP
    health = {"status": "ok", "result_refs": {"enabled": True, "min_chars": 20000}, "offload": {"delegate": True, "draft": True, "transform": True, "result_ask": True}}

    def log_message(self, *a):
        pass

    def _json(self, code, body):
        b = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/tools-map":
            self._json(200, self.tools_map)
        elif self.path == "/health":
            self._json(200, self.health)
        else:
            self._json(404, {})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length") or 0))
        ok = self.path == "/mcp" and self.headers.get("authorization") == f"Bearer {PAT}"
        self._json(200 if ok else 401, {"jsonrpc": "2.0", "id": 1, "result": {}} if ok else {"error": "expired"})


@pytest.fixture()
def env(tmp_path):
    """가짜 게이트웨이 · 가짜 claude · 결과 폴더 · 부르는 함수."""
    gw_cls = type("GW", (_GW,), {"tools_map": json.loads(json.dumps(TOOLS_MAP)), "health": json.loads(json.dumps(_GW.health))})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), gw_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir()
    claude = tmp_path / "bin" / "claude"
    claude.parent.mkdir()
    claude.write_text(FAKE.replace("__PY__", sys.executable).replace("__HELP__", repr(FAKE_HELP)))
    claude.chmod(0o755)
    out = tmp_path / "out"
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)

    def run(*args, extra_env=None, pat=PAT):
        e = {k: v for k, v in os.environ.items() if not k.startswith(("FAKE_", "HWAX_GATEWAY_PAT"))}
        e.update({"FAKE_DIR": str(fake_dir), "HOME": str(home), "CLAUDE_CONFIG_DIR": str(home / ".claude"), "HWAX_GATEWAY_PAT": pat,
                  "TMPDIR": str(tmp_path / "tmp")})
        (tmp_path / "tmp").mkdir(exist_ok=True)
        e.update(extra_env or {})
        cmd = ["node", str(RUN), *args, "--out", str(out), "--claude", str(claude), "--gateway", base, "--agent", base]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=e)

    def calls(kind=None):
        d = fake_dir / "calls"
        got = [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.exists() else []
        return [c for c in got if kind is None or c["kind"] == kind]

    yield {"run": run, "calls": calls, "out": out, "gw": gw_cls, "tmp": tmp_path, "fake": fake_dir}
    srv.shutdown()


def _ok(r):
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _offload_rules_from_setup_bat() -> str:
    """포털 설정 배치의 규칙 묶음 — 실행기와 다른 길(파이썬 리터럴)로 읽어 맞댄다."""
    src = (ROOT / "frontend/src/lib/setupBat.ts").read_text(encoding="utf-8")
    m = re.search(r"const OFFLOAD_RULES = (\[.*?\])\.join\('\\n'\);", src, re.S)
    assert m, "setupBat.ts 의 OFFLOAD_RULES 자리가 바뀌었다"
    return "\n".join(ast.literal_eval(m.group(1)))


def test_tasks_parse_like_pyyaml_and_stay_read_only_and_public():
    js = subprocess.run(["node", "--input-type=module", "-e",
                         f"import {{parseYaml}} from {json.dumps(str(RUN))}; import {{readFileSync}} from 'node:fs';"
                         f"process.stdout.write(JSON.stringify(parseYaml(readFileSync({json.dumps(str(EVAL / 'tasks.yaml'))}, 'utf8'))))"],
                        capture_output=True, text=True, timeout=60)
    assert js.returncode == 0, js.stderr
    doc = yaml.safe_load((EVAL / "tasks.yaml").read_text(encoding="utf-8"))
    assert json.loads(js.stdout) == doc, "실행기의 작은 YAML 파서가 PyYAML 과 다르게 읽는다"
    tasks = doc["tasks"]
    assert len(tasks) == 16 and len({t["id"] for t in tasks}) == 16
    helps = {"R": ["B"], "M": ["A"], "W": ["C"], "T": ["D"]}
    for g, want in helps.items():
        grp = [t for t in tasks if t["group"] == g]
        assert len(grp) == 4 and all(t["helps"] == want for t in grp), g
    for t in tasks:
        assert "읽기만 하고 아무것도 바꾸지 마라" in t["prompt"], t["id"]
        assert t["expect"].get("shape"), t["id"]
        assert len(t["expect"]) >= 2, f"{t['id']} — 코드로 볼 꼴 검사가 하나는 있어야 한다"
    text = (EVAL / "tasks.yaml").read_text(encoding="utf-8")
    assert not re.search(r"https?://|\b\d{1,3}(?:\.\d{1,3}){3}\b|@\w+\.\w+", text), "공개 리포 — 주소 · 메일을 적지 않는다"


def test_allowlist_is_routine_read_plus_gateway_reads_and_offload_adds_eight(env):
    _ok(env["run"]("run", "--only", "R1", "--reps", "1", "--seed", "11"))
    runs = env["calls"]("run")
    assert len(runs) == 2
    by = {("offload" if "--append-system-prompt" in c["argv"] else "baseline"): c for c in runs}
    for arm, c in by.items():
        allow = c["settings"]["permissions"]["allow"]
        mcp = {x[len("mcp__hwax__"):] for x in allow if x.startswith("mcp__hwax__")}
        want = BASE_ALLOW | (set(OFFLOAD) if arm == "offload" else set())
        assert mcp == want, (arm, sorted(mcp ^ want))
        assert "invoke_tool" not in mcp and "rest_call" not in mcp
        deny = set(c["settings"]["permissions"]["deny"])
        for b in ("Bash", "Write", "Edit", "MultiEdit", "WebFetch", "WebSearch", "Task", "Agent", "NotebookEdit"):
            assert b in deny, (arm, b)
        assert {"mcp__hwax__invoke_tool", "mcp__hwax__rest_call", "mcp__hwax__create_report", "mcp__hwax__delete_part",
                "mcp__hwax__save_conversation", "mcp__hwax__routine_run_start", "mcp__hwax__figure_list"} <= deny, arm
        assert ({f"mcp__hwax__{n}" for n in OFFLOAD} <= deny) == (arm == "baseline"), arm
        assert not (deny & set(allow)), "deny 가 허용을 이긴다 — 겹치면 허용이 죽는다"
        assert c["settings"]["permissions"]["defaultMode"] == "dontAsk" and c["settings"]["disableAllHooks"] is True
        assert c["settings"]["disableClaudeAiConnectors"] is True and c["env_connectors"] == "false"
        # 결과 파일 Read — 그 자리만(//절대 경로 꼴), 나머지 Read 는 dontAsk 가 거절한다
        spill = [x for x in allow if x.startswith("Read(")]
        assert spill == [f"Read(/{env['tmp']}/home/.claude/projects/**/tool-results/**)"], spill
        argv = c["argv"]
        assert argv[0] == "-p" and argv[1] == c["prompt"] and "읽기만 하고" in c["prompt"]
        for flag, val in (("--permission-mode", "dontAsk"), ("--setting-sources", "local"), ("--tools", "ToolSearch,Read"),
                          ("--model", "claude-opus-5-5"), ("--output-format", "stream-json")):
            assert argv[argv.index(flag) + 1] == val, flag
        for flag in ("--strict-mcp-config", "--no-session-persistence", "--verbose"):
            assert flag in argv, flag
        assert c["type"] == "http" and c["url"].endswith("/mcp") and c["headers"]["X-HWAX-View"] == "full"
        assert ("X-HWAX-Result" in c["headers"]) == (arm == "offload")
        assert not c["cwd"].startswith(str(ROOT)), "작업 폴더가 리포 안이면 프로젝트 CLAUDE.md · 설정이 실린다"
    rules = by["offload"]["argv"][by["offload"]["argv"].index("--append-system-prompt") + 1]
    assert rules == _offload_rules_from_setup_bat(), "PC 킷 E 와 같은 글이어야 한다"
    assert "result_ask(" in rules and "delegate_start" in rules and "draft_section" in rules
    al = json.loads((env["out"] / "allowlist.json").read_text())
    assert set(al["baseline"]["allow"]) == BASE_ALLOW and set(al["offload"]["allow"]) == BASE_ALLOW | set(OFFLOAD)
    # 결과 파일 Read 를 끄면 Read 도 deny 로 간다
    _ok(env["run"]("run", "--only", "R2", "--reps", "1", "--no-spill-read"))
    c = env["calls"]("run")[-1]
    assert c["argv"][c["argv"].index("--tools") + 1] == "ToolSearch" and "Read" in c["settings"]["permissions"]["deny"]
    assert not [x for x in c["settings"]["permissions"]["allow"] if x.startswith("Read")]


def test_pat_reaches_only_the_temp_header_and_never_an_output(env):
    r1 = _ok(env["run"]("run", "--only", "R1,T4", "--reps", "1", "--seed", "3", extra_env={"FAKE_LEAK": "1"}))
    r2 = _ok(env["run"]("judge"))
    r3 = _ok(env["run"]("human", "--pairs", "2"))
    r4 = _ok(env["run"]("report"))
    want = "sha:" + hashlib.sha256(f"Bearer {PAT}".encode()).hexdigest()
    for c in env["calls"]("run"):
        assert c["headers"]["Authorization"] == want, "PAT 는 임시 MCP 설정의 머리로만 간다"
        assert c["mcp_mode"] == "0o600" and c["settings_mode"] == "0o600" and c["tmp_mode"] == "0o700"
        assert not Path(c["mcp_path"]).exists() and not Path(c["settings_path"]).exists(), "임시 파일은 끝나면 지운다"
        assert c["env_has_pat"] is False, "자식 claude 에는 PAT 환경변수를 넘기지 않는다"
    assert all(c["env_has_pat"] is False for c in env["calls"]("judge"))
    leaked = [p for p in env["out"].rglob("*") if p.is_file() and PAT in p.read_text(encoding="utf-8", errors="replace")]
    assert not leaked, leaked
    for r in (r1, r2, r3, r4):
        assert PAT not in r.stdout + r.stderr
    ev = "".join(p.read_text() for p in (env["out"] / "runs").glob("*baseline.events.jsonl"))
    assert "Bearer ***" in ev, "가짜가 흘린 PAT 를 가렸어야 한다(가림이 실제로 일했다)"
    rec = json.loads(next((env["out"] / "runs").glob("*baseline.json")).read_text())
    assert "***" in rec["stderr_tail"] and PAT not in rec["stderr_tail"]
    assert not list((env["tmp"] / "tmp").glob("hwax-eval-*")), "임시 폴더가 남았다"
    assert stat.S_IMODE(env["out"].stat().st_mode) == 0o700


def test_resume_skips_finished_runs_and_retries_infra_errors(env):
    r = _ok(env["run"]("run", "--only", "R1,M1", "--reps", "1", "--seed", "5", extra_env={"FAKE_FAIL_ONCE": "1"}))
    assert len(env["calls"]("run")) == 4 and "result 사건 없음" in r.stdout
    failed = [json.loads(p.read_text()) for p in (env["out"] / "runs").glob("*.json") if json.loads(p.read_text())["infra_error"]]
    assert len(failed) == 1
    _ok(env["run"]("run", "--only", "R1,M1", "--reps", "1", extra_env={"FAKE_FAIL_ONCE": "1"}))
    runs = env["calls"]("run")
    assert len(runs) == 5, "기반 오류 하나만 다시 돈다"
    redo = "offload" if "--append-system-prompt" in runs[-1]["argv"] else "baseline"
    assert redo == failed[0]["arm"] and runs[-1]["prompt"].strip() in {t["prompt"].strip() for t in yaml.safe_load((EVAL / "tasks.yaml").read_text())["tasks"] if t["id"] == failed[0]["task"]}
    r3 = _ok(env["run"]("run", "--only", "R1,M1", "--reps", "1"))
    assert len(env["calls"]("run")) == 5 and "남은 것 0" in r3.stdout
    (env["out"] / "runs" / "M1.r1.offload.json").unlink()
    _ok(env["run"]("run", "--only", "R1,M1", "--reps", "1"))
    assert len(env["calls"]("run")) == 6
    plan = json.loads((env["out"] / "plan.json").read_text())
    assert plan["seed"] == 5 and plan["model"] == "claude-opus-5-5"
    bad = env["run"]("run", "--only", "R1", "--reps", "1", "--model", "claude-sonnet-5-5")
    assert bad.returncode != 0 and "다른 모델" in bad.stdout


def test_timeout_is_an_infra_error_even_with_a_late_result_and_odd_results_are_flagged(env):
    r = _ok(env["run"]("run", "--only", "R1", "--reps", "1", "--arms", "baseline", "--timeout-min", "0.02", extra_env={"FAKE_SLOW_ONCE": "1"}))
    rec = json.loads((env["out"] / "runs" / "R1.r1.baseline.json").read_text())
    assert rec["timed_out"] is True and rec["result"] and rec["infra_error"].startswith("시간 초과"), "SIGINT 뒤의 result 는 반쪽 답이다"
    assert "시간 초과" in r.stdout
    _ok(env["run"]("run", "--only", "R1", "--reps", "1", "--arms", "baseline"))
    assert len(env["calls"]("run")) == 2, "시간 초과는 다음 run 에 다시 돈다"
    _ok(env["run"]("run", "--only", "R1", "--reps", "1", "--arms", "offload", extra_env={"FAKE_SUBTYPE": "error_max_budget_usd"}))
    _ok(env["run"]("report"))
    md = (env["out"] / "report.md").read_text()
    assert "- R1.r1.offload — 결과 error_max_budget_usd · is_error" in md
    assert json.loads((env["out"] / "summary.json").read_text())["arms"]["offload"]["runs"] == 1, "끝은 났으니 갈래의 결과로 센다"


def test_report_counts_tokens_cost_judgement_and_server_side(env):
    _ok(env["run"]("run", "--only", "R1,T4", "--reps", "2", "--seed", "7"))
    _ok(env["run"]("judge"))
    _ok(env["run"]("report"))
    s = json.loads((env["out"] / "summary.json").read_text())
    b, f = s["arms"]["baseline"], s["arms"]["offload"]
    assert b["runs"] == f["runs"] == 4
    assert b["cost"] == pytest.approx(4.0) and f["cost"] == pytest.approx(2.4)
    assert (b["input"], b["output"], b["cache_write"], b["cache_read"]) == (4000, 3200, 8000, 200000)
    assert f["claude_tokens"] == 4 * (600 + 500 + 1500 + 30000) and b["tokens_med"] == 1000 + 800 + 2000 + 50000
    assert b["duration_s"] == pytest.approx(240) and f["duration_med"] == pytest.approx(45) and b["turns_med"] == 4
    assert (b["tool_calls"], f["tool_calls"], b["denied"], f["denied"]) == (8, 16, 4, 0)
    assert (b["checks_ok"], b["checks_n"], f["checks_ok"], f["checks_n"]) == (2, 4, 2, 4), "R1 표 10행은 통과 · T4 다섯 줄은 실패"
    # 숫자 — baseline 은 999.25 가 출처 없음, offload 는 서버가 표시한 777.5(같은 잡을 두 번 받아도 한 번)
    assert (b["num_unsourced"], f["num_unsourced"], f["server_mismatched"]) == (4, 0, 4)
    # 서버 LLM — 위임 토큰은 잡마다 한 번, draft_section 은 tokens 칸이 없어 '모름' 호출로 센다
    assert (f["server_jobs"], f["server_tokens_in"], f["server_tokens_out"], f["server_unknown_calls"]) == (4, 4800, 1200, 4)
    assert b["server_tokens_in"] == 0 and f["runs_using_offload"] == 4
    assert s["judge"] == {**s["judge"], "wins": 4, "ties": 0, "losses": 0, "judged": 4, "failed": 0, "loss_rate": 0}
    v = s["verdict"]
    assert v["no_quality_difference"] is True and (v["mismatch_base"], v["mismatch_off"]) == (4, 4)
    md = (env["out"] / "report.md").read_text()
    assert "품질 차이 없음 = 판정 패배율 ≤ 10%" in md and "충족 — 품질 차이 없음" in md
    assert "| 줄인 몫(offload) | | 40.0% |" in md, "비용 4.00 → 2.40"
    assert "offload 승 4 · 무 0 · 패 0" in md and "위임 토큰" in md
    # 손잡이 — 어긋남이 줄어야만 통과로 바꾸면 미충족
    _ok(env["run"]("report", "--max-mismatch-increase", "-1"))
    s2 = json.loads((env["out"] / "summary.json").read_text())
    assert s2["verdict"]["mismatch_ok"] is False and s2["verdict"]["no_quality_difference"] is False
    assert "**미충족**" in (env["out"] / "report.md").read_text()


def test_judge_is_blind_retries_a_bad_shape_once_and_human_sample_is_parsed(env):
    _ok(env["run"]("run", "--only", "R1,T4", "--reps", "2", "--seed", "7"))
    _ok(env["run"]("judge", extra_env={"FAKE_JUDGE_BAD_ONCE": "1"}))
    js = env["calls"]("judge")
    assert len(js) == 5, "꼴이 틀린 첫 답만 한 번 더 부른다"
    for c in js:
        p = c["stdin"]
        for leak in ("baseline", "offload", "delegate_start", "res_ABCDEFGH1234", "mcp__hwax__", "result_ask"):
            assert leak not in p, leak
        assert "## 답 A" in p and "## 답 B" in p and "읽기만 하고 아무것도 바꾸지 마라" in p
        a = c["argv"]
        assert a[a.index("--model") + 1] == "claude-sonnet-5-5" and a[a.index("--tools") + 1] == ""
        assert a[a.index("--permission-mode") + 1] == "dontAsk" and "--strict-mcp-config" in a
    recs = [json.loads(p.read_text()) for p in sorted((env["out"] / "judge").glob("*.json"))]
    assert len(recs) == 4 and all(r["verdict"] for r in recs)
    assert sorted(len(r["attempts"]) for r in recs) == [1, 1, 1, 2]
    assert {r["map"]["A"] for r in recs} == {"baseline", "offload"}, "A/B 는 짝마다 무작위다"
    assert all(r["map"][r["verdict"]["winner"]] == "offload" for r in recs), "판정의 A/B 를 갈래로 되돌려 센다"
    # 사람 표본
    _ok(env["run"]("human"))
    md = env["out"] / "human-review.md"
    text = md.read_text()
    assert text.count("## 쌍 ") == 4 and "baseline" not in text and "offload" not in text and "delegate_start" not in text
    key = json.loads((env["out"] / "human-key.json").read_text())
    assert len(key) == 4
    again = env["run"]("human")
    assert again.returncode != 0 and "--force" in again.stdout, "적어 둔 판정을 덮지 않는다"
    filled = text
    for k in key:
        letter = "A" if k["map"]["A"] == "offload" else "B"
        head = f"## 쌍 {k['pair']} — "
        i = filled.index(head)
        j = filled.index("- 판정(A · B · 무):", i)
        filled = filled[:j] + f"- 판정(A · B · 무): {letter}" + filled[j + len("- 판정(A · B · 무):"):]
    md.write_text(filled)
    _ok(env["run"]("report"))
    s = json.loads((env["out"] / "summary.json").read_text())
    assert s["human"] == {"pairs": 4, "filled": 4, "agree": 4}


def test_fence_violation_stops_the_whole_run(env):
    r = env["run"]("run", "--only", "R1,R2,R3", "--reps", "1", "--arms", "baseline", "--seed", "1", extra_env={"FAKE_VIOLATE": "1"})
    assert r.returncode == 3 and "울타리 위반" in r.stdout
    assert len(env["calls"]("run")) == 1, "위반 뒤로는 돌리지 않는다"
    r2 = env["run"]("run", "--only", "R4", "--reps", "1", "--arms", "baseline", extra_env={"FAKE_INIT_EXTRA": "mcp__hwax__invoke_tool"})
    assert r2.returncode == 3 and "목록에 막을 도구가 보인다" in r2.stdout


def test_preflight_refuses_before_spending(env):
    r = env["run"]("check", pat="")
    assert r.returncode != 0 and "HWAX_GATEWAY_PAT" in r.stdout
    r = env["run"]("check", pat="hwax_pat_WRONG_000000000")
    assert r.returncode != 0 and "401" in r.stdout and "hwax_pat_WRONG" not in r.stdout
    ok = _ok(env["run"]("check"))
    assert "허용 baseline — 6개" in ok.stdout and "허용 offload — 14개" in ok.stdout and "돌릴 준비가 됐다" in ok.stdout
    env["gw"].tools_map = {**TOOLS_MAP, "map": {k: v for k, v in TOOLS_MAP["map"].items() if k != "draft_section"}}
    env["gw"].health = {"result_refs": {"enabled": False}, "offload": {"delegate": True, "draft": False, "transform": True, "result_ask": True}}
    r = env["run"]("check")
    assert r.returncode == 2 and "draft_section" in r.stdout and "result_refs.enabled" in r.stdout and "offload.draft" in r.stdout
    r = env["run"]("run", "--reps", "1")
    assert r.returncode != 0 and not env["calls"]("run"), "사전 점검을 넘지 못하면 한 번도 부르지 않는다"
    assert _ok(env["run"]("check", "--arms", "baseline")).returncode == 0, "baseline 만 돌릴 때는 2판 스위치를 보지 않는다"
    (env["tmp"] / "home/.claude/CLAUDE.md").write_text("<!-- hwax-offload:begin -->\n규칙\n<!-- hwax-offload:end -->\n")
    r = env["run"]("check", "--arms", "baseline")
    assert r.returncode == 2 and "baseline 이 오염된다" in r.stdout
    assert env["run"]("run", "--rep", "1").returncode != 0, "모르는 손잡이는 멈춘다(오타로 기본값이 도는 것을 막는다)"
