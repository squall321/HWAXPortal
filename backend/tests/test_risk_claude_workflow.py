# 리스크 심사 Claude 길 워크플로(infra/pipeline/hwax-risk-claude.js)를 가짜 런타임과 가짜 과제 줄에서 돌려 집기·읽기·내기 규칙을 본다
"""엔진(HWAXAgentServer external_llm.py)이 판단 호출을 과제로 줄 세우면 잡 주인의 Claude Code 가 이 워크플로로 집어 답한다. 실제
Claude 로 돌려 보는 시험은 하지 않는다(사용자 결정 X-D1) — 여기의 에이전트는 전부 가짜다.

스크립트를 스텁 런타임에서 **실제로 돌린다**(test_delib_pipeline_js 와 같은 방식). 가짜 에이전트는 라벨(집기·답·내기·마침)로
갈리고, 스크립트가 프롬프트에 실은 인자(task_id · lease · offset · text 리터럴)를 읽어 가짜 과제 줄을 부른다 — 진짜 에이전트가 받는
글에서 값을 읽는 것과 같다. 가짜 과제 줄은 엔진 Board 의 규칙을 따른다 — 길이·자리는 유니코드 코드 포인트, 집기마다 새 임대(lease),
offset 이 없으면 붙이고 0 이면 처음부터 · 받은 길이와 다르면 offset_mismatch, 임대가 아니면 not_claimed, 상한을 넘으면
answer_too_large, final 이면 엔진에 넘긴다(max_chars 를 넘으면 잘라 finish_reason=length — 엔진의 토큰 어림 대신).

런타임 흉내 — Date.now()·인자 없는 new Date()·Math.random() 은 던진다(재개를 깨므로 런타임이 막는다). fetch·require 는 덫이다
(워크플로는 MCP 도구 밖으로 나가지 않는다).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = "infra/pipeline/hwax-risk-claude.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없다")

# 워크플로를 가짜 런타임에서 돌리는 구동기. 표준입력 {args, tasks, board?, script?, noTool?, claimNull?}.
#   tasks  — [{id, kind?, target_key?, run_id?, label?, system?, human?, max_chars?, then?}] (then — 이 과제를 마치면 세울 과제들)
#   board  — {page?(쪽 크기, 코드 포인트), hard?(answer_too_large 상한)}
#   script — 과제별 대본 {answers?[], lazy?{시도: 'first'|'jump'}, expire?{시도: 'read'|'answer'}(그 시도에서 임대를 푼다), hold?,
#            yields?, alter?{offset, times}, lose?{offset, times}, badFinal?, skipFinal?, loseFinal?, noSubmitTool?}
_NODE_RUN = r"""
const fs = require('fs');
const path = require('path');
const root = process.argv[1], scriptRel = process.argv[2];
const inp = JSON.parse(fs.readFileSync(0, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const cp = s => Array.from(String(s));
const tick = () => new Promise(r => setImmediate(r));

// 덫 — 워크플로는 네트워크·모듈을 쓰지 않는다.
const net = [];
for (const k of ['fetch', 'XMLHttpRequest', 'WebSocket', 'EventSource']) {
  globalThis[k] = function () { net.push(k); throw new Error('네트워크 금지 — ' + k); };
}
globalThis.require = function (m) { net.push('require:' + m); throw new Error('require 금지 — ' + m); };
// 런타임 흉내 — 재개를 깨는 셋은 던진다(스크립트에만 준다).
const NoDate = new Proxy(Date, {
  construct(t, a) { if (!a.length) throw new Error('new Date() 금지'); return new t(...a); },
  get(t, k) { if (k === 'now') return () => { throw new Error('Date.now() 금지'); }; return t[k]; },
});
const NoMath = Object.create(Math);
NoMath.random = () => { throw new Error('Math.random() 금지'); };

// ── 가짜 과제 줄(엔진 external_llm.Board 의 규칙) ──
const NOT_FOUND = { ok: false, code: 'task_not_found', message: '그런 과제가 없다' };
const NOT_CLAIMED = { ok: false, code: 'not_claimed', message: '이 임대로 집혀 있지 않다' };
class Board {
  constructor(o) {
    this.page = o.page || 7000; this.hard = o.hard || 2000000;
    this.tasks = []; this.seq = 0; this.leases = 0; this.claims = 0;
    this.log = []; this.delivered = {}; this.claimedNow = 0; this.maxClaimed = 0; this.phase = 0; this.maxByPhase = {};
  }
  add(t) {
    const system = t.system === undefined ? '[지시] 한 줄에 JSON 하나.' : t.system;
    const human = t.human === undefined ? '[자료] 카드와 변경.' : t.human;
    this.tasks.push({ id: t.id, kind: t.kind || 'verdict', target_key: t.target_key === undefined ? 'diff:mine' : t.target_key,
      run_id: t.run_id || '', label: t.label || '', system, human, text: system + human,
      max_chars: t.max_chars === undefined ? 33600 : t.max_chars, then: t.then || [], state: 'waiting', seq: ++this.seq,
      claims: 0, lease: null, buf: [], received: 0 });
  }
  live(id) { return this.tasks.find(x => x.id === id && x.state !== 'done'); }
  moved(d) {
    this.claimedNow += d; this.maxClaimed = Math.max(this.maxClaimed, this.claimedNow);
    this.maxByPhase[this.phase] = Math.max(this.maxByPhase[this.phase] || 0, this.claimedNow);
  }
  next() {
    const t = this.tasks.filter(x => x.state === 'waiting').sort((a, b) => a.seq - b.seq)[0];
    if (!t) return { empty: true, claimed: this.claimedNow, waited_s: 25.0 };
    t.state = 'claimed'; t.claims += 1; t.lease = 'ls-' + (++this.leases); t.buf = []; t.received = 0; this.claims += 1;
    this.moved(1);
    const s = cp(t.system).length, h = cp(t.human).length;
    const head = { task_id: t.id, lease: t.lease, kind: t.kind, max_tokens: 32000, max_chars: t.max_chars, chars: s + h,
      parts: [{ role: 'system', start: 0, chars: s }, { role: 'human', start: s, chars: h }],
      answer_deadline: 1760401200, answer_s: 1200, claim: t.claims, created_at: 1760400000 };
    for (const k of ['run_id', 'target_key', 'label']) if (t[k]) head[k] = t[k];
    return head;
  }
  held(id, lease) {
    const t = this.live(id);
    if (!t) return NOT_FOUND;
    if (t.state !== 'claimed' || !lease || lease !== t.lease) return NOT_CLAIMED;
    return t;
  }
  read(id, lease, offset) {
    const t = this.held(id, lease);
    let out;
    if (!t.id) out = t;
    else {
      const a = cp(t.text), total = a.length;
      if (!Number.isInteger(offset) || offset < 0 || offset > total) out = { ok: false, code: 'bad_offset', chars: total };
      else {
        const end = Math.min(total, offset + this.page);
        out = { task_id: t.id, offset, next_offset: end < total ? end : null, chars: total, text: a.slice(offset, end).join('') };
      }
    }
    this.log.push({ tool: 'review_task_read', task_id: id, lease, offset, code: out.code || '' });
    return out;
  }
  submit(id, lease, text, offset, final) {
    const t = this.held(id, lease);
    let out;
    if (!t.id) out = t;
    else if (offset !== null && offset !== undefined && offset !== 0 && offset !== t.received) {
      out = { ok: false, code: 'offset_mismatch', received_chars: t.received };
    } else {
      if (offset === 0) { t.buf = []; t.received = 0; }
      const n = cp(text).length;
      if (t.received + n > this.hard) out = { ok: false, code: 'answer_too_large', received_chars: t.received, max_chars: this.hard };
      else {
        t.buf.push(text); t.received += n;
        if (!final) out = { ok: true, task_id: t.id, done: false, received_chars: t.received };
        else {
          const full = t.buf.join(''), a = cp(full);
          let kept = full, finish = 'stop';
          if (t.max_chars && a.length > t.max_chars) { kept = a.slice(0, t.max_chars).join(''); finish = 'length'; }
          t.state = 'done'; this.moved(-1);
          this.delivered[t.id] = { text: kept, full, finish, claim: t.claims };
          out = { ok: true, task_id: t.id, done: true, chars: cp(kept).length, finish_reason: finish };
          if (finish === 'length') out.cut_chars = a.length - cp(kept).length;
          if (t.then.length) { this.phase += 1; for (const x of t.then) this.add(x); }
        }
      }
    }
    this.log.push({ tool: 'review_task_submit', task_id: id, lease, offset, final, chars: cp(text).length, text,
                    ok: out.ok === true, code: out.code || '', received: out.received_chars });
    return out;
  }
  expire(id) {   // 답 한도가 지났다 — 엔진처럼 임대를 지우고 버퍼를 비워 줄로 되돌린다
    const t = this.live(id);
    if (t && t.state === 'claimed') { t.state = 'waiting'; t.lease = null; t.buf = []; t.received = 0; this.moved(-1); }
  }
}

const board = new Board(inp.board || {});
for (const t of inp.tasks || []) board.add(t);
const sc = inp.script || {};
const st = { emptyClaims: 0, tries: {}, seen: {}, lostFinal: {}, reads: {}, inflight: 0, maxInflight: 0, answering: 0, maxAnswering: 0 };
const calls = [], logs = [];
const project = (v, s) => {
  if (!s || v == null) return v;
  if (s.type === 'array') return Array.isArray(v) ? v.map(x => project(x, s.items)) : v;
  if (s.type === 'object' && s.properties && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v).filter(([k]) => k in s.properties).map(([k, x]) => [k, project(x, s.properties[k])]));
  }
  return v;
};
const pick = (re, s) => { const m = re.exec(s); return m ? m[1] : null; };
const ids = p => ({ task_id: JSON.parse(pick(/^\s*task_id = (".*")$/m, p)), lease: JSON.parse(pick(/^\s*lease = (".*")$/m, p)) });

async function claimAgent(p, label) {
  if (inp.noTool) return { outcome: 'no_tool', polls: 1, error: 'unknown tool: review_task_next' };
  if (inp.claimNull) return null;
  const wait = Number(pick(/wait_s = (\d+)/, p)), max = Number(pick(/횟수 상한 = (\d+)/, p));
  for (let i = 1; i <= max; i += 1) {
    const r = board.next();
    board.log.push({ tool: 'review_task_next', wait_s: wait, worker: label, task_id: r.task_id || '' });
    if (!r.empty) return { outcome: 'task', polls: i, ...r };
    await tick();
  }
  st.emptyClaims += 1;
  return { outcome: 'empty', polls: max };
}

async function answerAgent(p) {
  const { task_id, lease } = ids(p);
  const s = sc[task_id] || {};
  const k = st.tries[task_id] = (st.tries[task_id] || 0) + 1;   // 이 과제의 몇 번째 답 에이전트인가
  st.answering += 1; st.maxAnswering = Math.max(st.maxAnswering, st.answering);
  try {
    if (s.hold) { let y = 0; while (st.emptyClaims < s.hold.emptyClaims && y < (s.hold.maxYields || 400)) { await tick(); y += 1; } }
    const ex = (s.expire || {})[k];                                // 그 시도에서 답 한도가 지난다(임대가 풀린다)
    if (ex === 'read') board.expire(task_id);
    const pages = []; let text = ''; let off = 0;
    const lazy = (s.lazy || {})[k];
    while (off !== null) {
      const r = board.read(task_id, lease, off);
      if (r.ok === false) return { outcome: r.code, pages, error: r.message || '' };
      pages.push({ offset: off, next_offset: r.next_offset === null ? -1 : r.next_offset });
      text += r.text;
      off = r.next_offset;
      if (lazy === 'first') break;                                  // 앞쪽만 읽고 멈춘 게으른 에이전트
      if (lazy === 'jump' && pages.length === 1 && off !== null) off += board.page;   // 한 쪽을 건너뛴다
      for (let i = 0; i < (s.yields || 0); i += 1) await tick();
    }
    (st.reads[task_id] = st.reads[task_id] || []).push(text);
    if (ex === 'answer') board.expire(task_id);
    const answers = s.answers || [];
    const answer = answers.length ? answers[Math.min(k, answers.length) - 1] : `{"task":"${task_id}","read":${cp(text).length}}`;
    return { outcome: 'answered', pages, answer, error: '' };
  } finally { st.answering -= 1; }
}

async function submitAgent(p) {
  const { task_id, lease } = ids(p);
  const offset = Number(pick(/^\s*offset = (\d+)$/m, p));
  let text = JSON.parse(pick(/^\s*text = (".*")$/m, p));
  const tm = pick(/received_chars 가 정확히 (\d+) 이면/, p);
  const total = tm === null ? null : Number(tm);
  const s = sc[task_id] || {};
  if (s.noSubmitTool) return { called: false, error: 'unknown tool: review_task_submit' };
  const key = task_id + '@' + offset;
  const seen = st.seen[key] = (st.seen[key] || 0) + 1;            // 이 자리 조각을 몇 번째 싣는가
  const hit = rule => rule && rule.offset === offset && seen <= (rule.times || 1);
  if (hit(s.alter)) text = cp(text).slice(0, -1).join('');         // 옮겨 싣기가 한 글자를 빠뜨렸다
  const first = board.submit(task_id, lease, text, offset, pick(/^\s*final = (true|false)$/m, p) === 'true');
  let fin = null;
  const match = total !== null && first.ok === true && first.received_chars === total;
  if (total !== null && first.ok === true && !first.done && ((match && !s.skipFinal) || (!match && s.badFinal))) {
    fin = board.submit(task_id, lease, '', first.received_chars, true);   // badFinal — 조건을 어기고 마친다
  }
  if (hit(s.lose)) return null;                                      // 호출은 됐는데 보고를 잃었다
  return { called: true, first, ...(fin ? { final: fin } : {}), error: '' };
}

async function finalAgent(p) {
  const { task_id, lease } = ids(p);
  const offset = Number(pick(/^\s*offset = (\d+)$/m, p));
  const r = board.submit(task_id, lease, '', offset, true);
  if ((sc[task_id] || {}).loseFinal && !st.lostFinal[task_id]) { st.lostFinal[task_id] = 1; return null; }
  return { called: true, first: r, error: '' };
}

async function agent(prompt, opts) {
  const o = (opts && typeof opts === 'object') ? opts : {};
  const label = String(o.label || '');
  calls.push({ label, prompt: String(prompt), argc: arguments.length, optsType: opts === undefined ? 'none' : typeof opts,
               phase: o.phase || '', effort: o.effort || '', schema: !!o.schema });
  st.inflight += 1; st.maxInflight = Math.max(st.maxInflight, st.inflight);
  try {
    await tick();
    let out;
    if (label.startsWith('집기')) out = await claimAgent(prompt, label);
    else if (label.startsWith('답')) out = await answerAgent(prompt);
    else if (label.startsWith('내기')) out = await submitAgent(prompt);
    else if (label.startsWith('마침')) out = await finalAgent(prompt);
    else throw new Error('모르는 에이전트 라벨 — ' + label);
    return project(out, o.schema);
  } finally { st.inflight -= 1; }
}
const parallel = fns => Promise.all(fns.map(f => f().catch(() => null)));
const log = m => { logs.push(String(m)); };
const src = fs.readFileSync(path.resolve(root, scriptRel), 'utf8').replace(/^export const meta/m, 'const meta');
new AsyncFunction('args', 'agent', 'parallel', 'log', 'phase', 'workflow', 'Date', 'Math', src)(
  inp.args, agent, parallel, log, () => {}, async () => { throw new Error('자식 워크플로는 없다'); }, NoDate, NoMath)
  .then(result => {
    const tasks = board.tasks.map(t => ({ id: t.id, state: t.state, claims: t.claims }));
    process.stdout.write(JSON.stringify({ result, calls, logs, net, st,
      board: { log: board.log, delivered: board.delivered, claims: board.claims, maxClaimed: board.maxClaimed,
               maxByPhase: board.maxByPhase, tasks } }));
  })
  .catch(e => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
"""


def _node(args, tasks=(), **extra) -> subprocess.CompletedProcess:
    return subprocess.run(["node", "-e", _NODE_RUN, str(_ROOT), _SCRIPT],
                          input=json.dumps({"args": args, "tasks": list(tasks), **extra}),
                          capture_output=True, text=True, timeout=120)


def _run(args, tasks=(), **extra) -> dict:
    r = _node(args, tasks, **extra)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


def _serve(tasks=(), **kw) -> dict:
    """맡은 대상 diff:mine 하나 · 일꾼 하나(차례가 정해진다) · 빈 집기 한 번에 멈춤 — 시험마다 필요한 것만 바꾼다."""
    args = {"targetKey": "diff:mine", "concurrency": 1, "idlePolls": 1, **kw.pop("args", {})}
    return _run(args, tasks, **kw)


def _submits(out: dict, task_id: str) -> list:
    return [x for x in out["board"]["log"] if x["tool"] == "review_task_submit" and x["task_id"] == task_id]


def _outcomes(out: dict) -> dict:
    return {t["task_id"]: t["outcome"] for t in out["result"]["tasks"]}


def _lines(n: int, width: int = 99, ch: str = "가") -> str:
    """줄 n 개(줄마다 width 자 + 줄바꿈) — 조각이 줄 끝에서 끊기는지 보는 답."""
    return "".join(f"{i:06d}" + ch * (width - 6) + "\n" for i in range(n))


# ── 여러 쪽 읽기와 조각 내기 ─────────────────────────────────────────────────────────────
def test_여러_쪽을_읽고_긴_답을_조각으로_나눠_낸다():
    """프롬프트 5만여 자는 쪽(가짜 7,000자) 여덟으로 읽고, 답 4만 자는 15,000자 안쪽 조각 셋으로 낸다 — 조각은 줄 끝에서 끊고
    (옮겨 싣는 에이전트가 줄 가운데서 끝난 조각을 '마저 잇지' 않게), 내용이 다 맞은 뒤에 따로 마친다. 엔진이 받은 답은 낸 답과
    바이트째 같다(심의 의장 결정문의 ```json 펜스도 그대로)."""
    human = "변경 L01 «보스 간극 0.5 → 0.2 mm»\n" * 1700
    answer = "## 리스크 심사 보고서\n" + _lines(400) + "```json\n{\"risk_spec\": []}\n```\n"
    out = _serve([{"id": "xt-1", "kind": "deliberation", "human": human, "label": "risk-review", "max_chars": 60000}],
                 script={"xt-1": {"answers": [answer]}})
    assert _outcomes(out) == {"xt-1": "answered"}
    assert out["st"]["reads"]["xt-1"] == ["[지시] 한 줄에 JSON 하나." + human], "프롬프트 전문을 읽지 않았다"
    reads = [x["offset"] for x in out["board"]["log"] if x["tool"] == "review_task_read"]
    assert reads == list(range(0, len("[지시] 한 줄에 JSON 하나." + human), 7000))
    assert out["board"]["delivered"]["xt-1"]["text"] == answer
    subs = _submits(out, "xt-1")
    content = [x for x in subs if not x["final"]]
    assert len(content) == 3 and [x["offset"] for x in content] == [0, content[0]["chars"], content[0]["chars"] + content[1]["chars"]]
    assert all(x["chars"] <= 15000 for x in content)
    assert all(x["text"].endswith("\n") for x in content[:-1]), "조각이 줄 가운데서 끊겼다"
    assert subs[-1]["final"] and subs[-1]["chars"] == 0 and subs[-1]["offset"] == len(answer), "내용을 다 맞춘 뒤 빈 조각으로 마친다"
    assert out["result"]["answered"] == {"deliberation": 1} and out["result"]["stoppedBy"] == "idle"


def test_BMP_밖_글자가_쪽과_조각의_경계에_걸려도_코드_포인트로_센다():
    """엔진의 길이·자리는 코드 포인트다. 𝜎(UTF-16 둘)가 쪽 경계와 조각 경계(15,000번째 코드 포인트)에 걸려도 쪽은 그대로 이어지고,
    조각은 그 글자를 가르지 않고, 받은 길이(received_chars)는 코드 포인트로 맞는다. 답 길이가 max_chars 와 같으면(UTF-16 으로는
    넘는다) 줄이라고 다시 쓰게 하지 않는다."""
    system = "가" * 6999 + "𝜎"          # 첫 쪽(7,000 코드 포인트)의 끝 글자가 𝜎
    human = "𝜀" + "나" * 9000 + "𝜎"
    answer = "다" * 14999 + "𝜎" + "라" * 100     # 15,000번째 코드 포인트가 𝜎 — 줄바꿈이 없어 거기서 끊는다
    n = len(answer)                              # 파이썬 len 은 코드 포인트다
    out = _serve([{"id": "xt-a", "system": system, "human": human, "max_chars": n}], script={"xt-a": {"answers": [answer]}})
    assert out["st"]["reads"]["xt-a"] == [system + human]
    assert out["board"]["delivered"]["xt-a"]["text"] == answer
    first = _submits(out, "xt-a")[0]
    assert first["chars"] == 15000 and first["text"].endswith("𝜎") and first["received"] == 15000
    assert sum(1 for c in out["calls"] if c["label"].startswith("답")) == 1, "max_chars 안의 답을 줄이라고 다시 썼다(UTF-16 으로 셌다)"
    assert out["board"]["delivered"]["xt-a"]["finish"] == "stop"


# ── 받은 길이 맞추기 ─────────────────────────────────────────────────────────────────
def test_응답을_잃은_조각은_서버가_받은_자리에서_잇는다():
    """둘째 조각을 실은 에이전트가 보고를 잃었다(호출은 됐다). 같은 자리로 다시 내면 offset_mismatch{received_chars} 가 오고, 그 길이가
    우리 조각의 경계라 거기서 잇는다 — 둘째 조각이 두 번 붙지 않고, 첫 조각을 다시 내지도 않는다."""
    answer = _lines(400)
    out = _serve([{"id": "xt-m", "max_chars": 60000}], script={"xt-m": {"answers": [answer], "lose": {"offset": 15000, "times": 1}}})
    assert out["board"]["delivered"]["xt-m"]["text"] == answer
    subs = _submits(out, "xt-m")
    assert [(x["offset"], x["code"]) for x in subs if not x["final"]] == [
        (0, ""), (15000, ""), (15000, "offset_mismatch"), (30000, "")], subs
    assert _outcomes(out) == {"xt-m": "answered"}


def test_서버가_받은_길이가_조각의_경계가_아니면_처음부터_다시_낸다():
    """보고를 잃은 조각이 바꿔 적혀 붙었다면 서버의 길이는 우리 경계가 아니다 — 그 버퍼는 우리 답의 앞부분이 아니므로 잇지 않고
    offset 0 으로 처음부터 다시 낸다(엔진에는 마치기 전이라 아무것도 가지 않았다)."""
    answer = _lines(400)
    out = _serve([{"id": "xt-r", "max_chars": 60000}], script={"xt-r": {"answers": [answer], "lose": {"offset": 15000, "times": 1},
                                                     "alter": {"offset": 15000, "times": 1}}})
    assert out["board"]["delivered"]["xt-r"]["text"] == answer
    offs = [(x["offset"], x["code"]) for x in _submits(out, "xt-r") if not x["final"]]
    assert offs == [(0, ""), (15000, ""), (15000, "offset_mismatch"), (0, ""), (15000, ""), (30000, "")], offs


def test_옮겨_싣기가_조각을_바꿔_적으면_마치지_않고_처음부터_다시_낸다():
    """서버가 받은 길이가 낸 조각의 끝과 다르면 옮겨 싣는 에이전트가 글을 바꿨다 — 마치기 전에 알아채고 처음부터 다시 낸다. 바뀐 답이
    엔진에 가지 않는다."""
    answer = _lines(100)
    out = _serve([{"id": "xt-e"}], script={"xt-e": {"answers": [answer], "alter": {"offset": 0, "times": 1}}})
    assert out["board"]["delivered"]["xt-e"]["text"] == answer
    subs = _submits(out, "xt-e")
    assert [x["offset"] for x in subs if not x["final"]] == [0, 0] and subs[0]["chars"] == len(answer) - 1
    assert any("바꿔 적었다" in m for m in out["logs"])
    assert not any(c["label"].startswith("마침") for c in out["calls"]), "어긋난 버퍼를 마치려 했다(서버의 offset 검사에 기댔다)"


def test_조건을_어기고_마친_어긋난_답은_성공으로_적지_않는다():
    """옮겨 싣는 에이전트가 받은 길이가 틀렸는데도 마쳤다 — 엔진에는 바뀐 답이 갔다. 워크플로는 그것을 답으로 세지 않고
    delivered_mismatch 로 남긴다('실패가 정상 응답과 똑같이 생겼다' 를 막는다)."""
    answer = _lines(100)
    out = _serve([{"id": "xt-b"}], script={"xt-b": {"answers": [answer], "alter": {"offset": 0, "times": 1}, "badFinal": True}})
    assert out["board"]["delivered"]["xt-b"]["text"] != answer
    assert _outcomes(out) == {"xt-b": "delivered_mismatch"}
    assert out["result"]["answered"] == {} and out["result"]["failures"] == {"delivered_mismatch": 1}


def test_마치는_호출을_빠뜨리면_따로_마친다():
    """마지막 조각의 에이전트가 길이가 맞았는데도 마치지 않았다 — 워크플로가 마치는 호출(빈 글 · final)을 따로 낸다."""
    answer = _lines(10)
    out = _serve([{"id": "xt-f"}], script={"xt-f": {"answers": [answer], "skipFinal": True}})
    assert out["board"]["delivered"]["xt-f"]["text"] == answer
    assert any(c["label"].startswith("마침") for c in out["calls"])


def test_마친_보고를_잃은_뒤의_task_not_found_는_실패가_아니라_모름이다():
    """마치는 호출의 보고를 잃고 다시 냈더니 과제가 없다 — 이미 마쳐 엔진에 넘어갔을 수 있다. 실패로도 성공으로도 적지 않고
    delivered_unconfirmed 로 남긴다."""
    answer = _lines(10)
    out = _serve([{"id": "xt-u"}], script={"xt-u": {"answers": [answer], "skipFinal": True, "loseFinal": True}})
    assert out["board"]["delivered"]["xt-u"]["text"] == answer
    assert _outcomes(out) == {"xt-u": "delivered_unconfirmed"}


def test_마지막_조각의_보고를_잃으면_마쳤는지_모른다고_남긴다():
    """마지막 조각을 실은 에이전트는 받은 길이가 맞으면 그 자리에서 마친다 — 그 보고를 잃었다. 같은 자리로 다시 내니 과제가 없다
    (이미 마쳐 엔진에 넘어갔다). 실패로도 성공으로도 적지 않고 delivered_unconfirmed 로 남긴다."""
    answer = _lines(10)
    out = _serve([{"id": "xt-v"}], script={"xt-v": {"answers": [answer], "lose": {"offset": 0, "times": 1}}})
    assert out["board"]["delivered"]["xt-v"]["text"] == answer
    assert [(x["offset"], x["final"], x["code"]) for x in _submits(out, "xt-v")] == [
        (0, False, ""), (1000, True, ""), (0, False, "task_not_found")]
    assert _outcomes(out) == {"xt-v": "delivered_unconfirmed"}


def test_내기가_끝내_안_되면_까닭을_남기고_멈춘다():
    """내기 에이전트가 도구를 찾지 못했다 — 같은 자리로 상한(조각 수 × 2 + 4)까지만 다시 해 보고 submit_failed 로 그 오류를 남긴다."""
    out = _serve([{"id": "xt-s"}], script={"xt-s": {"noSubmitTool": True}})
    rec = out["result"]["tasks"][0]
    assert rec["outcome"] == "submit_failed" and "unknown tool: review_task_submit" in rec["note"]
    assert sum(1 for c in out["calls"] if c["label"].startswith("내기")) == 6


# ── 집기가 풀림 · 상한 ─────────────────────────────────────────────────────────────────
def test_내는_중_not_claimed_면_멈추고_다시_내지_않는다():
    """답을 쓰는 사이 답 한도가 지나 과제가 줄로 돌아갔다(임대가 풀렸다) — 첫 조각이 not_claimed 다. 그 임대로 다시 내지 않는다
    (새 집기의 버퍼에 닿지 않게). 줄로 돌아간 과제는 다시 집혀(claim 2) 새 임대로 처음부터 답한다."""
    out = _serve([{"id": "xt-n"}], script={"xt-n": {"answers": ["{\"a\":1}"], "expire": {"1": "answer"}}})
    subs = _submits(out, "xt-n")
    stale = [x for x in subs if x["lease"] == "ls-1"]
    assert [x["code"] for x in stale] == ["not_claimed"], "풀린 임대로 다시 냈다"
    assert [t["outcome"] for t in out["result"]["tasks"]] == ["not_claimed", "answered"]
    assert out["board"]["delivered"]["xt-n"]["claim"] == 2 and all(x["lease"] == "ls-2" for x in subs[1:])


def test_읽는_중_not_claimed_면_답하지_않는다():
    out = _serve([{"id": "xt-o"}], script={"xt-o": {"answers": ["{\"a\":1}"], "expire": {"1": "read"}}})
    first = out["result"]["tasks"][0]
    assert first["outcome"] == "not_claimed"
    assert not [x for x in _submits(out, "xt-o") if x["lease"] == "ls-1"]


def test_answer_too_large_면_줄여_다시_써서_처음부터_낸다():
    """엔진의 버퍼 상한(가짜 50자)을 넘었다 — 답 에이전트에게 상한 안으로 다시 쓰게 하고 offset 0 부터 낸다."""
    out = _serve([{"id": "xt-l"}], board={"hard": 50},
                 script={"xt-l": {"answers": ["x" * 80, "y" * 30]}})
    assert out["board"]["delivered"]["xt-l"]["text"] == "y" * 30
    subs = _submits(out, "xt-l")
    assert [(x["offset"], x["code"]) for x in subs if not x["final"]] == [(0, "answer_too_large"), (0, "")]
    second = [c for c in out["calls"] if c["label"].startswith("답")][1]["prompt"]
    assert "[다시 쓰기]" in second and "50자" in second and "max_chars = 49" in second


def test_answer_too_large_뒤_임대가_풀렸으면_다시_내지_않는다():
    out = _serve([{"id": "xt-L"}], board={"hard": 50},
                 script={"xt-L": {"answers": ["x" * 80, "y" * 30], "expire": {"2": "answer"}}})
    stale = [x for x in _submits(out, "xt-L") if x["lease"] == "ls-1"]
    assert [(x["offset"], x["code"]) for x in stale] == [(0, "answer_too_large"), (0, "not_claimed")], "풀린 임대로 다시 냈다"
    assert [t["outcome"] for t in out["result"]["tasks"]] == ["not_claimed", "answered"]


def test_max_chars_를_넘은_답은_한_번_줄여_다시_쓰게_한다():
    out = _serve([{"id": "xt-c", "max_chars": 100}], script={"xt-c": {"answers": ["가" * 150, "나" * 80]}})
    assert out["board"]["delivered"]["xt-c"]["text"] == "나" * 80
    second = [c for c in out["calls"] if c["label"].startswith("답")][1]["prompt"]
    assert "150자였다" in second and "100자 안으로" in second


def test_다시_써도_넘으면_그대로_내고_잘림을_알린다():
    """집은 과제를 답 없이 두면 답 한도 동안 잡이 선다 — 두 번째도 넘치면 그대로 내고, 엔진이 자른 것(finish_reason=length)을 센다."""
    out = _serve([{"id": "xt-C", "max_chars": 100}], script={"xt-C": {"answers": ["가" * 150]}})
    assert out["board"]["delivered"]["xt-C"]["finish"] == "length"
    assert _outcomes(out) == {"xt-C": "answered"} and out["result"]["cut"] == 1
    assert any("잘랐다" in m for m in out["logs"])


# ── 빠진 쪽 ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("lazy", ["first", "jump"])
def test_쪽을_빠뜨린_답은_내지_않고_다시_읽게_한다(lazy):
    """답 에이전트가 앞쪽만 읽거나 한 쪽을 건너뛰었다 — 적어 온 쪽 사슬(offset · next_offset)이 끊긴다. 그 답은 내지 않고 까닭을
    붙여 다시 쓰게 한다."""
    human = "자료 " * 9000
    out = _serve([{"id": "xt-p", "human": human}], script={"xt-p": {"lazy": {"1": lazy}}})
    answers = [c["prompt"] for c in out["calls"] if c["label"].startswith("답")]
    assert len(answers) == 2 and "다 읽지 않았다" in answers[1]
    assert _outcomes(out) == {"xt-p": "answered"}
    assert len(_submits(out, "xt-p")) == 2   # 두 번째 답만 낸다(조각 하나 + 마침)


def test_두_번_다_쪽을_빠뜨리면_내지_않는다():
    out = _serve([{"id": "xt-q", "human": "자료 " * 9000}], script={"xt-q": {"lazy": {"1": "first", "2": "jump"}}})
    assert _outcomes(out) == {"xt-q": "read_incomplete"}
    assert not _submits(out, "xt-q")


# ── 맡은 과제만 ──────────────────────────────────────────────────────────────────────
def test_맡지_않은_대상의_과제는_읽지도_답하지도_않는다():
    """주인의 줄은 선착순 하나라 다른 대상의 과제 · target_key 가 없는 과제도 온다. 집기는 됐어도 읽지도 내지도 않는다(답 한도 뒤
    엔진이 되돌린다). 맡은 대상의 과제는 평소대로 답한다."""
    out = _serve([{"id": "xt-x", "target_key": "diff:other", "run_id": "delib-1"}, {"id": "xt-y", "target_key": ""},
                  {"id": "xt-z", "target_key": "diff:mine"}])
    assert _outcomes(out) == {"xt-x": "foreign", "xt-y": "foreign", "xt-z": "answered"}
    touched = {x["task_id"] for x in out["board"]["log"] if x["tool"] in ("review_task_read", "review_task_submit")}
    assert touched == {"xt-z"}
    assert not [c for c in out["calls"] if c["label"].startswith("답") and ("xt-x" in c["prompt"] or "xt-y" in c["prompt"])]
    assert out["result"]["skipped"] == {"verdict": 2} and out["result"]["answered"] == {"verdict": 1}
    assert any("맡지 않은 과제" in m and "diff:other" in m and "targetKeys 에 더해" in m for m in out["logs"])
    # 대상이 없는 과제 — 쟁점 패널 심의가 지금 이렇게 온다(질문 머리가 [쟁점 …] 라 엔진이 대상을 읽지 못한다). 까닭을 그대로 말한다.
    assert any("맡지 않은 과제" in m and "xt-y" in m and "target_key 가 없어" in m for m in out["logs"])


def test_여러_대상을_맡을_수_있다():
    out = _run({"targetKeys": ["diff:a", "diff:b"], "concurrency": 1, "idlePolls": 1},
               [{"id": "t1", "target_key": "diff:a"}, {"id": "t2", "target_key": "diff:b"}, {"id": "t3", "target_key": "diff:c"}])
    assert _outcomes(out) == {"t1": "answered", "t2": "answered", "t3": "foreign"}


# ── 멈춤 · 동시 수 · 상한 ─────────────────────────────────────────────────────────────
def test_빈_집기가_idlePolls_번_잇달면_멈춘다():
    """한 집기 에이전트는 review_task_next 를 6번까지 부른다 — idlePolls 8 이면 6번 · 2번의 두 에이전트로 8번을 채우고 멈춘다."""
    out = _run({"targetKey": "diff:mine", "concurrency": 3, "idlePolls": 8})
    nexts = [x for x in out["board"]["log"] if x["tool"] == "review_task_next"]
    per = {w: sum(1 for x in nexts if x["worker"] == w) for w in ("집기 1", "집기 2", "집기 3")}
    assert per == {"집기 1": 8, "집기 2": 8, "집기 3": 8}
    limits = sorted(re.search(r"횟수 상한 = (\d+)", c["prompt"]).group(1) for c in out["calls"] if c["label"] == "집기 1")
    assert limits == ["2", "6"]
    assert all("wait_s = 25" in c["prompt"] for c in out["calls"] if c["label"].startswith("집기"))
    assert out["result"]["stoppedBy"] == "idle" and out["result"]["tasks"] == []


def test_다른_일꾼이_과제를_쥐고_있으면_멈추지_않는다():
    """일꾼 1 이 긴 과제를 쓰는 사이 일꾼 2 의 집기는 비어도 멈추지 않는다 — 엔진은 답을 받은 뒤에 다음 과제들을 세운다. 일꾼 2 가
    먼저 멈추면 그 뒤의 과제 둘을 일꾼 하나가 차례로 받는다(동시 수가 줄어든 채 잡이 끝까지 간다)."""
    out = _run({"targetKey": "diff:mine", "concurrency": 2, "idlePolls": 2},
               [{"id": "A", "then": [{"id": "B"}, {"id": "C"}]}],
               script={"A": {"hold": {"emptyClaims": 3}}, "B": {"yields": 30}, "C": {"yields": 30}})
    assert _outcomes(out) == {"A": "answered", "B": "answered", "C": "answered"}
    assert out["board"]["maxByPhase"]["1"] == 2, "A 뒤에 선 과제 둘을 동시에 집지 못했다(일꾼 2 가 먼저 멈췄다)"
    assert out["result"]["stoppedBy"] == "idle"


def test_동시_일꾼은_엔진의_주인당_상한_8_을_넘지_않는다():
    tasks = [{"id": f"c{i:02d}"} for i in range(12)]
    out = _run({"targetKey": "diff:mine", "concurrency": 20, "idlePolls": 1}, tasks,
               script={t["id"]: {"yields": 40} for t in tasks})
    assert out["result"]["workers"] == 8
    assert out["board"]["maxClaimed"] == 8 and out["st"]["maxAnswering"] == 8
    assert {c["label"] for c in out["calls"] if c["label"].startswith("집기")} == {f"집기 {i}" for i in range(1, 9)}
    assert any("요청 20" in m and "EXTERNAL_LLM_MAX_INFLIGHT" in m for m in out["logs"])
    assert out["result"]["answered"] == {"verdict": 12}


def test_maxTasks_를_넘겨_집지_않는다():
    """일꾼 넷이 동시에 집어도 집기 자리를 먼저 잡으므로 maxTasks 2 를 넘겨 집지 않는다 — 나머지 셋은 줄에 그대로 있다."""
    out = _run({"targetKey": "diff:mine", "concurrency": 4, "idlePolls": 1, "maxTasks": 2}, [{"id": f"m{i}"} for i in range(5)])
    assert out["board"]["claims"] == 2
    assert [t["state"] for t in out["board"]["tasks"]].count("waiting") == 3
    assert out["result"]["stoppedBy"] == "max_tasks"


def test_에이전트_상한에_닿기_전에_새_과제를_집지_않는다():
    """런타임은 워크플로 하나에 에이전트 1,000 개까지다 — 800 개를 쓰면 새 과제를 집지 않고 쥔 과제만 끝낸 뒤 멈춘다(남은 과제는 줄에
    그대로 — 다시 돌리면 된다). 쥔 과제를 끝내지 못한 채 런타임이 던지게 두지 않는다."""
    tasks = [{"id": f"k{i:03d}"} for i in range(300)]
    out = _run({"targetKey": "diff:mine", "concurrency": 8, "idlePolls": 1}, tasks)
    res = out["result"]
    assert res["stoppedBy"] == "agent_cap" and 800 <= res["agents"] < 830
    assert set(_outcomes(out).values()) == {"answered"}, "쥔 과제를 끝내지 못했다"
    assert [t["state"] for t in out["board"]["tasks"]].count("waiting") == 300 - len(res["tasks"]) > 0
    assert any("다시 돌린다" in m for m in out["logs"])


def test_도구가_없으면_곧바로_모두_멈춘다():
    out = _run({"targetKey": "diff:mine", "concurrency": 4}, [{"id": "t"}], noTool=True)
    assert out["result"]["stoppedBy"] == "tools_unavailable"
    assert len(out["calls"]) <= 4
    assert any("EXTERNAL_LLM_ENABLED" in m for m in out["logs"])


def test_집기가_잇달아_실패하면_멈춘다():
    out = _run({"targetKey": "diff:mine", "concurrency": 1}, [{"id": "t"}], claimNull=True)
    assert out["result"]["stoppedBy"] == "claim_errors" and len(out["calls"]) == 3


# ── 네트워크 없음 · 런타임 규칙 ──────────────────────────────────────────────────────────
def test_네트워크를_쓰지_않는다():
    """워크플로는 게이트웨이 MCP 도구(에이전트)로만 닿는다 — fetch·require 를 부르지 않고 소스에도 없다."""
    out = _serve([{"id": "t1"}, {"id": "t2", "target_key": "diff:other"}])
    assert out["net"] == []
    code = "\n".join(re.sub(r"//.*$", "", ln) for ln in (_ROOT / _SCRIPT).read_text(encoding="utf-8").splitlines())
    for word in ("fetch(", "require(", "import(", "XMLHttpRequest", "WebSocket", "http://", "https://"):
        assert word not in code, word


def test_에이전트_호출은_프롬프트와_옵션_둘만_넘기고_단계는_meta_에_있다():
    out = _serve([{"id": "t1"}, {"id": "t2", "target_key": "diff:other"}], script={"t1": {"answers": [_lines(200)]}})
    bad = [(c["label"], c["argc"], c["optsType"]) for c in out["calls"] if c["argc"] > 2 or c["optsType"] != "object"]
    assert not bad
    assert all(c["schema"] for c in out["calls"])
    assert {c["phase"] for c in out["calls"]} == {"집기", "답", "내기"}
    meta = _meta()
    assert [p["title"] for p in meta["phases"]] == ["집기", "답", "내기"]
    assert meta["name"] == "hwax-risk-claude"
    # 기계적인 셋(집기·내기·마침)만 낮은 effort — 답은 세션의 effort 를 그대로 쓴다
    assert {c["effort"] for c in out["calls"] if c["label"].startswith("답")} == {""}
    assert {c["effort"] for c in out["calls"] if not c["label"].startswith("답")} == {"low"}


def _meta() -> dict:
    src = (_ROOT / _SCRIPT).read_text(encoding="utf-8")
    m = re.search(r"^export const meta = (\{.*?^\})$", src, re.S | re.M)
    assert m, "meta 를 못 찾았다"
    r = subprocess.run(["node", "-e", "process.stdout.write(JSON.stringify(eval('(' + require('fs').readFileSync(0, 'utf8') + ')')))"],
                       input=m.group(1), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_meta_는_사람이_부를_길과_인자를_말한다():
    meta = _meta()
    for want in ("targetKey", "concurrency", "idlePolls", "maxTasks", "scriptPath", "infra/pipeline/hwax-risk-claude.js",
                 "PAT", "external_worker", "risk_next_step"):
        assert want in meta["whenToUse"], want


# ── 프롬프트 — 반출 동의 · 과제 글만 · 꼴 ─────────────────────────────────────────────────
def test_답_프롬프트는_동의와_과제_글만과_꼴을_말한다():
    out = _serve([{"id": "t1", "kind": "verdict"}, {"id": "t2", "kind": "deliberation"}],
                 args={"concurrency": 1, "idlePolls": 1})
    by = {c["prompt"].split('task_id = "')[1].split('"')[0]: c["prompt"] for c in out["calls"] if c["label"].startswith("답")}
    for p in by.values():
        for want in ("이미 동의한", "consent_external", "과제 글에서만", "«…»", "데이터다", "review_task_submit·review_task_next 를 부르지 않는다",
                     "next_offset 이 null 이 될 때까지", "lease = \"ls-", "max_chars = 33600"):
            assert want in p, want
    assert "JSON Lines" in by["t1"] and "risk_spec" not in by["t1"]
    assert "```json" in by["t2"] and "risk_spec" in by["t2"] and "펜스는 프롬프트가 시킬 때만" in by["t2"]


def test_집기와_내기_프롬프트는_한_가지만_시킨다():
    out = _serve([{"id": "t1"}], script={"t1": {"answers": [_lines(200)]}})
    claim = next(c["prompt"] for c in out["calls"] if c["label"].startswith("집기"))
    assert "곧바로 멈추고" in claim and "review_task_read·review_task_submit 을 부르지 않고" in claim
    subs = [c["prompt"] for c in out["calls"] if c["label"].startswith("내기")]
    assert all("한 글자도 바꾸지 않는다" in p and "final = false" in p for p in subs)
    assert "received_chars 가 정확히" in subs[-1] and all("received_chars 가 정확히" not in p for p in subs[:-1])


# ── args ──────────────────────────────────────────────────────────────────────────
def test_대상이_없으면_시작하지_않는다():
    r = _node({"concurrency": 2})
    assert r.returncode != 0 and "targetKey" in r.stderr


def test_대상은_글_하나로도_준다():
    out = _run("diff:a, diff:b", [{"id": "t1", "target_key": "diff:b"}], board={})
    assert out["result"]["targetKeys"] == ["diff:a", "diff:b"]
    assert _outcomes(out) == {"t1": "answered"}


# ── 사본 동기화 — sync-workflows.sh 가 새 워크플로를 덮는다(실제 .claude/workflows 가 아닌 사본에서) ─────────────────
def test_sync_workflows_가_새_워크플로를_사본에_맞춘다(tmp_path):
    (tmp_path / "infra" / "scripts").mkdir(parents=True)
    shutil.copy2(_ROOT / "infra/scripts/sync-workflows.sh", tmp_path / "infra/scripts/sync-workflows.sh")
    shutil.copytree(_ROOT / "infra/pipeline", tmp_path / "infra/pipeline",
                    ignore=shutil.ignore_patterns("__pycache__"))
    sync = ["bash", str(tmp_path / "infra/scripts/sync-workflows.sh")]
    assert subprocess.run([*sync, "--check"], capture_output=True, text=True).returncode == 1
    r = subprocess.run(sync, capture_output=True, text=True)
    assert r.returncode == 0 and "hwax-risk-claude.js" in r.stdout
    copy = tmp_path / ".claude/workflows/hwax-risk-claude.js"
    assert copy.read_bytes() == (_ROOT / _SCRIPT).read_bytes()
    assert subprocess.run([*sync, "--check"], capture_output=True, text=True).returncode == 0
    copy.write_text("// 낡은 사본\n", encoding="utf-8")
    r = subprocess.run([*sync, "--check"], capture_output=True, text=True)
    assert r.returncode == 1 and "hwax-risk-claude.js" in r.stdout
