#!/usr/bin/env node
// 토큰 절감 2판 비교 테스트셋 실행기 — 같은 과제를 baseline · offload 두 갈래로 claude -p 에 돌려 토큰 · 비용 · 시간 · 판정을 모은다
//
// 하위 명령 — check(돈 안 드는 사전 점검) · run(과제 × 반복 × 두 갈래, 섞인 차례 · 이어 하기) · judge(눈가림 판정) · human(사람 표본 4쌍) · report(보고서).
// 외부 패키지 없이 Node 18+ 로 돈다. 계획 · 결정은 HWAXPortal docs/token-saving/eval-plan.md · context-notes.md TS-14, 사람 차례는 README.md.
//
// 안전 — 사람 없이 도는 Claude 가 쓰기 도구를 부르면 안 된다. 허용 목록은 게이트웨이 /tools-map 의 routine_read(루틴 울타리와 같은 '읽기로 확인된' 노출 이름)
// ∪ 게이트웨이 로컬 조회 도구(게이트웨이 _LOCAL_READ 그대로)이고, invoke_tool · rest_call 은 넣지 않는다. offload 갈래만 2판 도구 여덟을 더한다. 허용 밖의 노출
// 도구 · 내장 도구는 deny 의 맨 이름으로 Claude 의 문맥에서 뺀다(공식 문서 — 맨 이름 deny 는 도구를 문맥에서 지운다). 권한 모드 dontAsk 는 허용 밖 호출을 묻지
// 않고 거절한다. PAT 는 HWAX_GATEWAY_PAT 로만 받고, 갈래마다 0600 임시 파일에만 쓰고 끝나면 지운다 — 남는 산출물에서는 *** 로 가린다.
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  chmodSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync,
} from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '../..');                       // 리포 루트 — 이 파일 자리에서 유도한다(박스마다 경로가 다르다)
const ARMS = ['baseline', 'offload'];
const MCP_PREFIX = 'mcp__hwax__';                          // --mcp-config 의 서버 이름 hwax → 도구 이름 mcp__hwax__<이름>
// 2판 도구 여덟(docs/token-saving/offload-v2.md — A 위임 넷 · C 작성 · D 변환 · B 받기 · 묻기). baseline 은 이것을 문맥에서 뺀다.
const OFFLOAD_TOOLS = ['delegate_start', 'delegate_status', 'delegate_result', 'delegate_cancel',
  'draft_section', 'llm_transform', 'result_get', 'result_ask'];
// 부를 때마다 서버 LLM 을 쓴다 — 결과의 tokens {input, output} 를 호출마다 더한다(칸이 없거나 null 이면 '모름' — 옛 에이전트 서버 · 사용량을 주지 않은 호출, TS-16)
const SERVER_LLM_TOOLS = new Set(['draft_section', 'llm_transform', 'result_ask']);
// 넣지 않는 게이트웨이 도구 — 안쪽 이름으로 아무 도구나 부른다(invoke_tool) · 아무 REST 나 부른다(rest_call). 두 갈래 모두 문맥에서 뺀다.
const FORBIDDEN = ['invoke_tool', 'rest_call'];
// 게이트웨이 로컬 조회 도구 — 게이트웨이 gateway.py _LOCAL_READ(읽기 전용 PAT 이 부르는 것) 그대로 + 그림 받기 · 목록(_FIG_READ_NAMES).
// routine_read 는 백엔드 도구만 담아 이것들이 없다. /tools-map 이 '_gateway' 로 귀속한 이름만 쓴다(그림 보관을 끈 박스에서 같은 이름의 백엔드
// 도구가 이 목록으로 열리지 않게 — 게이트웨이 반대 검토 6 과 같은 까닭).
const GATEWAY_LOCAL_READ = ['search_conversations', 'list_tool_apps', 'search_tools', 'browse_experts', 'use_experts',
  'verify_answer', 'rest_catalog', 'routine_list', 'routine_get', 'procedure_list', 'procedure_get', 'procedure_run_status',
  'insight_find', 'insight_get', 'kit_get', 'ontology_lookup', 'gas_transport_lookup', 'reliability_test_conditions',
  'gateway_readonly_allowlist', 'figure_get', 'figure_list'];
// 내장 도구 — --tools 로 고른 것(ToolSearch · 결과 파일 Read) 말고는 deny 의 맨 이름으로 뺀다. 모르는 이름은 deny 에 있어도 아무 일도 없다.
const BUILTINS = ['Bash', 'BashOutput', 'KillShell', 'KillBash', 'Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit',
  'NotebookRead', 'WebFetch', 'WebSearch', 'Task', 'Agent', 'Glob', 'Grep', 'LS', 'TodoWrite', 'TodoRead', 'Skill',
  'SlashCommand', 'ExitPlanMode', 'EnterPlanMode', 'AskUserQuestion', 'Monitor', 'ListMcpResourcesTool',
  'ReadMcpResourceTool', 'ToolSearch', 'EnterWorktree', 'ExitWorktree', 'LSP', 'Workflow', 'TaskStop', 'SendMessage',
  'CronCreate', 'CronDelete', 'CronList', 'RemoteTrigger', 'PushNotification'];
const DANGEROUS_BUILTINS = new Set(['Bash', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'WebFetch', 'WebSearch', 'Task',
  'Agent', 'Skill', 'SlashCommand', 'Workflow', 'CronCreate', 'RemoteTrigger', 'PushNotification', 'SendMessage']);
// 이 박스의 claude --help 에 있어야 하는 것(짐작하지 않는다 — 없으면 멈춘다). 근거는 README '확인한 Claude Code 플래그'.
const REQUIRED_FLAGS = ['--print', '--output-format', '--verbose', '--mcp-config', '--strict-mcp-config', '--settings',
  '--setting-sources', '--permission-mode', 'dontAsk', '--tools', '--append-system-prompt', '--model',
  '--no-session-persistence'];
const DEFAULTS = {
  tasks: join(HERE, 'tasks.yaml'), out: join(homedir(), 'hwax-offload-eval'), gateway: 'http://127.0.0.1:9110',
  agent: 'http://127.0.0.1:9009', claude: 'claude', model: 'claude-opus-5-5', 'judge-model': 'claude-sonnet-5-5',
  reps: '2', concurrency: '1', 'timeout-min': '30', arms: ARMS.join(','), 'max-loss-rate': '0.10',
  'max-mismatch-increase': '0', 'tool-search': 'on',
};
const KNOWN = new Set([...Object.keys(DEFAULTS), 'mcp-url', 'only', 'seed', 'no-spill-read', 'max-budget-usd', 'force',
  'pairs', 'judge-timeout-min']);
const LIVE = { children: new Set(), temps: new Set(), stop: false };
const say = (s) => process.stdout.write(`${s}\n`);

// ── 공통 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const eq = a.indexOf('=');
    const k = eq > 0 ? a.slice(2, eq) : a.slice(2);
    if (!KNOWN.has(k)) throw new Error(`모르는 손잡이 --${k} — README 의 손잡이 표를 본다`);
    if (eq > 0) o[k] = a.slice(eq + 1);
    else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) o[k] = argv[++i];
    else o[k] = true;
  }
  return { ...DEFAULTS, ...o };
}

const sha = (s) => createHash('sha256').update(s).digest('hex');
const median = (xs) => {
  const a = xs.filter((x) => Number.isFinite(x)).sort((p, q) => p - q);
  if (!a.length) return null;
  const m = a.length >> 1;
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
};
const sum = (xs) => xs.reduce((s, x) => s + (Number.isFinite(x) ? x : 0), 0);

// 씨앗 있는 난수(mulberry32) — 차례 섞기 · A/B 정하기 · 사람 표본을 같은 씨앗이면 같게 한다.
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const seedOf = (...parts) => parseInt(sha(parts.join('|')).slice(0, 8), 16);
function shuffle(xs, r) {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function writeAtomic(path, text, mode = 0o600) {
  const tmp = `${path}.part`;
  writeFileSync(tmp, text, { mode });
  renameSync(tmp, path);
}
const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'));

// PAT 가림 — 남는 산출물(사건 줄 · stderr · 기록)에 PAT 글자가 섞여도 *** 로 바꾼다(겹쳐 막기 — 처음부터 싣지 않는 것이 먼저다).
function redactor() {
  const pat = process.env.HWAX_GATEWAY_PAT || '';
  return (s) => (pat.length >= 8 ? String(s).split(pat).join('***') : String(s));
}

// ── 과제 파일(작은 YAML — tasks.yaml 이 쓰는 꼴만: 블록 매핑 · 블록 시퀀스 · 흐름 목록 · 블록 글 | · 수 · 따옴표 글) ─────────

function parseYaml(src) {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  let i = 0;
  const indent = (l) => l.match(/^ */)[0].length;
  const skip = () => { while (i < lines.length && (/^\s*$/.test(lines[i]) || /^\s*#/.test(lines[i]))) i++; };
  const fail = (why) => { throw new Error(`tasks YAML ${i + 1}째 줄 — ${why}`); };
  const isSeq = (l, n) => /^-( |$)/.test(l.slice(n));
  function scalar(s) {
    s = s.trim();
    if (s.startsWith('"')) return JSON.parse(s);
    if (s.startsWith("'")) return s.slice(1, -1).replace(/''/g, "'");
    if (s.startsWith('[')) {
      if (!s.endsWith(']')) fail('흐름 목록은 한 줄에 닫는다');
      const items = []; let cur = ''; let q = '';
      for (const ch of s.slice(1, -1)) {
        if (q) { cur += ch; if (ch === q) q = ''; } else if (ch === '"' || ch === "'") { q = ch; cur += ch; } else if (ch === ',') { items.push(cur); cur = ''; } else cur += ch;
      }
      if (cur.trim()) items.push(cur);
      return items.map(scalar);
    }
    s = s.replace(/\s+#.*$/, '');
    if (/^-?\d+$/.test(s)) return Number(s);
    if (/^-?\d+\.\d+$/.test(s)) return Number(s);
    if (s === 'true' || s === 'false') return s === 'true';
    if (s === 'null' || s === '~' || s === '') return null;
    return s;
  }
  function blockText(parent) {
    const body = []; let bi = null;
    while (i < lines.length) {
      const l = lines[i];
      if (/^\s*$/.test(l)) { body.push(''); i++; continue; }
      const k = indent(l);
      if (k <= parent || (bi !== null && k < bi)) break;
      if (bi === null) bi = k;
      body.push(l.slice(bi)); i++;
    }
    while (body.length && body[body.length - 1] === '') body.pop();
    return `${body.join('\n')}\n`;
  }
  function node(minIndent) {
    skip();
    if (i >= lines.length) return null;
    const n = indent(lines[i]);
    if (n < minIndent) return null;
    return isSeq(lines[i], n) ? seq(n) : map(n);
  }
  function seq(n) {
    const out = [];
    for (;;) {
      skip();
      if (i >= lines.length || indent(lines[i]) !== n || !isSeq(lines[i], n)) break;
      const rest = lines[i].slice(n + 2);
      if (!rest.trim()) { i++; out.push(node(n + 1)); continue; }
      if (/^[A-Za-z_][\w-]*:( |$)/.test(rest)) { lines[i] = ' '.repeat(n + 2) + rest; out.push(map(n + 2)); continue; }
      i++; out.push(scalar(rest));
    }
    return out;
  }
  function map(n) {
    const out = {};
    for (;;) {
      skip();
      if (i >= lines.length) break;
      const k = indent(lines[i]);
      if (k < n || (k === n && isSeq(lines[i], n))) break;
      if (k > n) fail('들여쓰기가 맞지 않는다');
      const m = lines[i].slice(n).match(/^([A-Za-z_][\w-]*):(?: +(.*))?$/);
      if (!m) fail('키: 값 꼴이 아니다');
      i++;
      const rest = (m[2] || '').trim();
      if (rest === '|') out[m[1]] = blockText(n);
      else if (rest === '' || rest.startsWith('#')) out[m[1]] = node(n + 1);
      else out[m[1]] = scalar(rest);
    }
    return out;
  }
  return node(0);
}

function loadTasks(path) {
  const text = readFileSync(path, 'utf8');
  const doc = path.endsWith('.json') ? JSON.parse(text) : parseYaml(text);
  const tasks = doc?.tasks;
  if (!Array.isArray(tasks) || !tasks.length) throw new Error(`${path} 에 tasks 가 없다`);
  const seen = new Set();
  for (const t of tasks) {
    if (!/^[A-Za-z0-9_-]+$/.test(t.id || '') || seen.has(t.id)) throw new Error(`과제 id 가 비었거나 겹친다 — ${t.id}`);
    seen.add(t.id);
    if (typeof t.prompt !== 'string' || !t.prompt.trim()) throw new Error(`${t.id} 에 prompt 가 없다`);
  }
  return { tasks, sha: sha(text) };
}

// ── Claude Code 확인 · 규칙 묶음 · 허용 목록 ─────────────────────────────────────────────────────────────────────────────

function claudeCaps(bin) {
  const run = (args) => spawnSync(bin, args, { encoding: 'utf8', timeout: 60000 });
  const v = run(['--version']);
  if (v.error || v.status !== 0) throw new Error(`claude 를 부르지 못했다(${bin}) — Claude Code CLI 가 깔려 있는지 본다`);
  const h = run(['--help']);
  const help = `${h.stdout || ''}${h.stderr || ''}`;
  const missing = REQUIRED_FLAGS.filter((f) => !help.includes(f));
  if (missing.length) throw new Error(`이 박스의 claude --help 에 없는 것 — ${missing.join(' · ')}. 판을 올리고(claude update) 다시 본다`);
  return { version: String(v.stdout || '').trim(), help };
}

// PC 킷 E 와 같은 규칙 묶음 — 포털 설정 배치가 사용자 CLAUDE.md 에 넣는 글(frontend/src/lib/setupBat.ts OFFLOAD_RULES)을 그대로 읽는다(사본을 두지 않는다).
function offloadRules() {
  const src = readFileSync(join(ROOT, 'frontend/src/lib/setupBat.ts'), 'utf8');
  const m = src.match(/const OFFLOAD_RULES = (\[[\s\S]*?\])\.join\('\\n'\);/);
  if (!m) throw new Error('setupBat.ts 에서 OFFLOAD_RULES 를 찾지 못했다 — 규칙 묶음의 자리가 바뀌었으면 이 읽기를 고친다');
  const arr = vm.runInNewContext(m[1], Object.create(null), { timeout: 1000 });
  if (!Array.isArray(arr) || !arr.every((s) => typeof s === 'string')) throw new Error('OFFLOAD_RULES 가 글 목록이 아니다');
  return arr.join('\n');
}

const configDir = () => process.env.CLAUDE_CONFIG_DIR || join(homedir(), '.claude');

async function getJson(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

// 허용 · deny 목록 — 갈래마다. spill 은 50,000자가 넘는 MCP 결과를 Claude Code 가 파일로 빼 둔 자리를 Read 로 읽게 할지(README '결과 파일 읽기').
function fences(toolsMap, { spill, toolSearch }) {
  const map = toolsMap.map || {};
  const exposed = new Set(Object.keys(map));
  const hard = new Set([...FORBIDDEN, ...OFFLOAD_TOOLS]);
  const base = new Set([
    ...(toolsMap.routine_read || []).filter((n) => exposed.has(n)),
    ...GATEWAY_LOCAL_READ.filter((n) => map[n] === '_gateway'),
  ].filter((n) => !hard.has(n)));
  const builtins = [...(toolSearch ? ['ToolSearch'] : []), ...(spill ? ['Read'] : [])];
  const spillRule = `Read(/${join(configDir(), 'projects')}/**/tool-results/**)`;   // '//절대 경로' 꼴(공식 문서 Read 규칙)
  const out = {};
  for (const arm of ARMS) {
    const allow = new Set(base);
    if (arm === 'offload') for (const n of OFFLOAD_TOOLS) if (exposed.has(n)) allow.add(n);
    const denyMcp = new Set([...FORBIDDEN, ...(arm === 'baseline' ? OFFLOAD_TOOLS : []),
      ...[...exposed].filter((n) => !allow.has(n))]);
    out[arm] = {
      allow: [...allow].sort(),
      builtins,
      settings: {
        permissions: {
          allow: [...[...allow].sort().map((n) => MCP_PREFIX + n), ...builtins.filter((b) => b !== 'Read'), ...(spill ? [spillRule] : [])],
          deny: [...BUILTINS.filter((b) => !builtins.includes(b)), ...[...denyMcp].sort().map((n) => MCP_PREFIX + n)],
          defaultMode: 'dontAsk',
        },
        disableAllHooks: true,
        disableClaudeAiConnectors: true,
      },
      missing_offload: arm === 'offload' ? OFFLOAD_TOOLS.filter((n) => !exposed.has(n)) : [],
    };
  }
  return out;
}

// 실행 뒤 울타리 대조 — 목록(init)에 막을 것이 보이거나, 허용 밖 도구가 거절되지 않고 돌았으면 위반이다(위반이면 run 전체를 멈춘다).
function fenceCheck(dg, arm, fence) {
  const allow = new Set(fence.allow);
  const hard = new Set([...FORBIDDEN, ...(arm === 'baseline' ? OFFLOAD_TOOLS : [])]);
  const okBuiltin = new Set([...fence.builtins, 'EndConversation']);
  const violations = []; const warnings = [];
  for (const t of dg.init?.tools || []) {
    if (t.startsWith(MCP_PREFIX)) {
      const s = t.slice(MCP_PREFIX.length);
      if (hard.has(s)) violations.push(`목록에 막을 도구가 보인다 — ${t}`);
      else if (!allow.has(s)) warnings.push(`목록에 허용 밖 도구 — ${t}(dontAsk 가 거절한다)`);
    } else if (t.startsWith('mcp__')) warnings.push(`목록에 다른 MCP 서버 도구 — ${t}`);
    else if (DANGEROUS_BUILTINS.has(t)) violations.push(`목록에 내장 도구가 보인다 — ${t}`);
    else if (!okBuiltin.has(t)) warnings.push(`목록에 모르는 내장 도구 — ${t}`);
  }
  for (const c of dg.calls) {
    if (c.denied || c.is_error !== false) continue;            // 거절됐거나 오류로 끝난 호출은 돌지 않았다
    if (c.name.startsWith(MCP_PREFIX)) { if (!allow.has(c.short)) violations.push(`허용 밖 도구가 돌았다 — ${c.short}`); }
    else if (c.name === 'Read') {
      if (!fence.builtins.includes('Read') || !String(c.input?.file_path || '').includes('/tool-results/')) violations.push(`Read 가 결과 파일 밖을 읽었다 — ${c.input?.file_path}`);
    } else if (!okBuiltin.has(c.name)) violations.push(`허용 밖 도구가 돌았다 — ${c.name}`);
  }
  return { violations, warnings };
}

// ── 사건 줄 읽기 · 셈 ───────────────────────────────────────────────────────────────────────────────────────────────────

function blockTexts(content) {
  if (typeof content === 'string') return [content];
  if (!Array.isArray(content)) return [];
  return content.map((b) => (b?.type === 'text' ? String(b.text || '') : `[${b?.type || '?'}]`));
}

// stream-json 사건 → init · result · 도구 호출(주 대화만 — Task 는 막혀 있다). assistant 사건은 한 메시지를 블록마다 여러 번 낼 수 있어 id 로 겹침을 뺀다.
function digest(events) {
  let init = null; let result = null;
  const uses = new Map(); const results = new Map();
  for (const e of events) {
    if (e?.type === 'system' && e.subtype === 'init') init = e;
    else if (e?.type === 'result') result = e;
    else if (e?.type === 'assistant' && !e.parent_tool_use_id) {
      for (const b of e.message?.content || []) if (b?.type === 'tool_use' && !uses.has(b.id)) uses.set(b.id, b);
    } else if (e?.type === 'user' && Array.isArray(e.message?.content)) {
      for (const b of e.message.content) if (b?.type === 'tool_result') results.set(b.tool_use_id, { texts: blockTexts(b.content), is_error: !!b.is_error });
    }
  }
  const denied = new Set((result?.permission_denials || []).map((d) => d.tool_use_id));
  const calls = [...uses.values()].map((u) => {
    const name = String(u.name || ''); const r = results.get(u.id);
    return {
      id: u.id, name, short: name.startsWith(MCP_PREFIX) ? name.slice(MCP_PREFIX.length) : name, input: u.input,
      texts: r?.texts || [], chars: sum((r?.texts || []).map((t) => t.length)), is_error: r ? r.is_error : null, denied: denied.has(u.id),
    };
  });
  return { init, result, calls };
}

// 숫자 대조 — 에이전트 서버 evidence.sig_numbers · unsourced_numbers 와 같은 판정(소수점이 있거나 100 이상인 수만, 쉼표를 빼고 부분 문자열).
// 파이썬 \w 는 한글도 글자로 보므로 앞쪽 경계를 \p{L}\p{N}_ 로 쓴다.
const NUM_RE = /(?<![\p{L}\p{N}_.])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d.])/gu;
function sigNumbers(text) {
  const out = [];
  for (const m of String(text || '').matchAll(NUM_RE)) {
    const raw = m[0]; const norm = raw.replaceAll(',', ''); const v = Number(norm);
    if (!Number.isFinite(v) || (!norm.includes('.') && v < 100)) continue;
    out.push([raw, norm]);
  }
  return out;
}
function unsourcedNumbers(answer, sources) {
  const src = String(sources).replaceAll(',', ''); const seen = new Set(); const bad = [];
  for (const [raw, norm] of sigNumbers(answer)) {
    if (seen.has(norm)) continue;
    seen.add(norm);
    if (!src.includes(norm)) bad.push(raw);
  }
  return { checked: seen.size, bad };
}

// 꼴 검사 — tasks.yaml 의 expect 가운데 코드로 볼 수 있는 것.
function tableRowsMax(text) {
  let best = 0; let cur = -1;
  for (const line of String(text).split('\n')) {
    const t = line.trim();
    if (!t.startsWith('|')) { cur = -1; continue; }
    if (/^[|:\-\s]+$/.test(t) && t.includes('-')) continue;   // |---|---| 구분 줄
    cur = cur < 0 ? 0 : cur + 1;                              // 표의 첫 줄은 머리
    best = Math.max(best, cur);
  }
  return best;
}
function shapeChecks(expect, answer) {
  const a = String(answer || ''); const out = {};
  if (!expect) return out;
  if (expect.table_rows_min != null) { const g = tableRowsMax(a); out.table_rows = { ok: g >= expect.table_rows_min, got: g, want: `≥ ${expect.table_rows_min}` }; }
  if (expect.lines_exact != null) { const g = a.split('\n').filter((l) => l.trim()).length; out.lines = { ok: g === expect.lines_exact, got: g, want: `= ${expect.lines_exact}` }; }
  if (Array.isArray(expect.chars)) { const g = [...a.trim()].length; out.chars = { ok: g >= expect.chars[0] && g <= expect.chars[1], got: g, want: `${expect.chars[0]} ~ ${expect.chars[1]}` }; }
  if (Array.isArray(expect.must_include)) { const miss = expect.must_include.filter((w) => !a.includes(w)); out.must_include = { ok: !miss.length, got: miss.length ? `빠짐 ${miss.join(' · ')}` : '모두', want: expect.must_include.join(' · ') }; }
  if (expect.latin_ratio_min != null) {
    const lat = (a.match(/[A-Za-z]/g) || []).length; const han = (a.match(/[\uAC00-\uD7A3]/g) || []).length;
    const g = lat + han ? lat / (lat + han) : 0;
    out.latin_ratio = { ok: g >= expect.latin_ratio_min, got: Math.round(g * 100) / 100, want: `≥ ${expect.latin_ratio_min}` };
  }
  return out;
}

// 2판 도구 결과에서 서버 쪽 셈 — 서버 LLM 토큰(위임은 delegate_result 의 tokens 를 잡마다 한 번, 작성 · 변환 · 묻기는 결과의 tokens 를 호출마다) ·
// 서버 숫자 어긋남 · tokens 를 모르는 잡 · 호출 수.
const tokensOf = (t) => (t && typeof t === 'object' && Number.isFinite(Number(t.input)) && Number.isFinite(Number(t.output))
  ? { input: Number(t.input), output: Number(t.output) } : null);
function serverSide(dg) {
  const jobs = new Set(); const jobTokens = new Map(); const jobNums = new Map(); const callTokens = [];
  let mismatched = 0; let unknownCalls = 0; let unreadable = 0;
  for (const c of dg.calls) {
    if (!OFFLOAD_TOOLS.includes(c.short) || c.denied || c.is_error !== false) continue;
    let obj = null;
    for (const t of c.texts) { try { const o = JSON.parse(t); if (o && typeof o === 'object') { obj = o; break; } } catch { /* 머리 + ref 로 줄었거나 글 — 아래에서 센다 */ } }
    if (!obj) { if (SERVER_LLM_TOOLS.has(c.short)) unknownCalls++; if (c.short !== 'result_get') unreadable++; continue; }
    const n = obj.numbers ? (obj.numbers.mismatched_total ?? (obj.numbers.mismatched || []).length) : 0;
    if (c.short === 'delegate_start' && obj.job_id) jobs.add(obj.job_id);
    if (c.short === 'delegate_result' && obj.job_id) {
      jobs.add(obj.job_id);
      const t = tokensOf(obj.tokens);
      if (t) jobTokens.set(obj.job_id, t);
      if (obj.numbers) jobNums.set(obj.job_id, n);
    } else if (SERVER_LLM_TOOLS.has(c.short)) {
      mismatched += n;
      const t = tokensOf(obj.tokens);
      if (t) callTokens.push(t); else unknownCalls++;
    }
  }
  const tok = [...jobTokens.values(), ...callTokens];
  return {
    jobs: jobs.size, tokens_in: sum(tok.map((t) => t.input)), tokens_out: sum(tok.map((t) => t.output)),
    jobs_without_tokens: jobs.size - jobTokens.size, calls_with_tokens: callTokens.length, unknown_calls: unknownCalls,
    mismatched: mismatched + sum([...jobNums.values()]), unreadable,
  };
}

// ── run ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────

const keyOf = (task, rep, arm) => `${task}.r${rep}.${arm}`;

function cleanupTemps() {
  for (const d of LIVE.temps) { try { rmSync(d, { recursive: true, force: true }); } catch { /* 끝나는 길 */ } }
  LIVE.temps.clear();
}

// 사전 점검 — check 와 run 이 같이 쓴다. 돈이 드는 호출은 없다.
async function preflight(o, arms) {
  const pat = process.env.HWAX_GATEWAY_PAT || '';
  if (!pat) throw new Error('HWAX_GATEWAY_PAT 가 비었다 — 포털 토큰 화면에서 받은 일반 PAT 를 환경변수로 준다(읽기 전용 PAT 는 2판 도구를 못 부른다 — TS-8)');
  const caps = claudeCaps(o.claude);
  if (o['max-budget-usd'] && !caps.help.includes('--max-budget-usd')) throw new Error('이 박스의 claude 에 --max-budget-usd 가 없다');
  const mcpUrl = o['mcp-url'] || `${o.gateway.replace(/\/$/, '')}/mcp`;
  const st = await fetch(mcpUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json, text/event-stream', authorization: `Bearer ${pat}` },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'hwax-offload-eval', version: '1' } } }),
    signal: AbortSignal.timeout(20000),
  });
  await st.body?.cancel?.();
  if (st.status !== 200) throw new Error(`게이트웨이가 PAT 를 받지 않았다(initialize → ${st.status}) — 토큰 수명 · 박스를 본다`);
  const toolsMap = await getJson(`${o.gateway.replace(/\/$/, '')}/tools-map`);
  if (!Array.isArray(toolsMap.routine_read)) throw new Error('/tools-map 에 routine_read 가 없다 — 게이트웨이 판이 낡았다');
  const spill = !o['no-spill-read'];
  const toolSearch = o['tool-search'] !== 'off';
  const fz = fences(toolsMap, { spill, toolSearch });
  const problems = [];
  if (arms.includes('offload')) {
    if (fz.offload.missing_offload.length) problems.push(`게이트웨이 목록에 2판 도구가 없다 — ${fz.offload.missing_offload.join(' · ')}(에이전트 서버 .env 스위치 · 게이트웨이 GATEWAY_RESULT_REFS 를 켜고 재기동 — README 2)`);
    const gh = await getJson(`${o.gateway.replace(/\/$/, '')}/health`).catch(() => null);
    if (!gh?.result_refs?.enabled) problems.push('게이트웨이 /health 의 result_refs.enabled 가 참이 아니다(GATEWAY_RESULT_REFS=1 · 재기동)');
    const ah = await getJson(`${o.agent.replace(/\/$/, '')}/health`).catch(() => null);
    const off = ah?.offload;
    if (!off) problems.push(`에이전트 서버 /health 에 offload 표지가 없다(${o.agent})`);
    else for (const k of ['delegate', 'draft', 'transform', 'result_ask']) if (off[k] !== true) problems.push(`에이전트 서버 offload.${k} 가 꺼져 있다`);
  }
  const memo = join(configDir(), 'CLAUDE.md');
  if (existsSync(memo) && readFileSync(memo, 'utf8').includes('hwax-offload:begin')) problems.push(`${memo} 에 2판 규칙 묶음이 있다 — baseline 이 오염된다. 평가 동안 그 표지 사이를 걷어 둔다`);
  const rules = offloadRules();
  return { pat, caps, mcpUrl, toolsMap, fz, spill, toolSearch, problems, rules };
}

function writeAllowlist(out, pf) {
  const doc = { at: new Date().toISOString(), spill_read: pf.spill, tool_search: pf.toolSearch, forbidden: FORBIDDEN };
  for (const arm of ARMS) doc[arm] = { allow: pf.fz[arm].allow, builtins: pf.fz[arm].builtins, deny: pf.fz[arm].settings.permissions.deny };
  writeAtomic(join(out, 'allowlist.json'), `${JSON.stringify(doc, null, 1)}\n`);
  return sha(JSON.stringify([pf.fz.baseline.allow, pf.fz.offload.allow, pf.spill, pf.toolSearch]));
}

async function cmdCheck(o) {
  const arms = String(o.arms).split(',');
  const pf = await preflight(o, arms);
  const { tasks } = loadTasks(o.tasks);
  say(`Claude Code ${pf.caps.version} — 필요한 플래그 모두 있음(${REQUIRED_FLAGS.length}).`);
  say(`게이트웨이 — PAT 받음 · 노출 ${Object.keys(pf.toolsMap.map || {}).length} · routine_read ${pf.toolsMap.routine_read.length}.`);
  for (const arm of ARMS) say(`허용 ${arm} — ${pf.fz[arm].allow.length}개 + 내장 ${pf.fz[arm].builtins.join(' · ') || '없음'} · deny ${pf.fz[arm].settings.permissions.deny.length}.`);
  say(`invoke_tool · rest_call 은 두 갈래 모두 뺐다. 결과 파일 Read — ${pf.spill ? '켬(결과 파일 자리만)' : '끔'} · 도구 검색 — ${pf.toolSearch ? '켬' : '끔'}.`);
  const both = pf.fz.baseline.allow.filter((n) => (pf.toolsMap.write || []).includes(n));
  if (both.length) say(`routine_read 이면서 write 에도 드는 것 ${both.length} — 게이트웨이 읽기 목록이 읽기로 확인한 것이라 연다(${both.slice(0, 10).join(' · ')}${both.length > 10 ? ' …' : ''}).`);
  mkdirSync(o.out, { recursive: true, mode: 0o700 });
  writeAllowlist(o.out, pf);
  say(`허용 목록 전부 — ${join(o.out, 'allowlist.json')}(돌리기 전에 본다).`);
  say(`규칙 묶음 — setupBat.ts OFFLOAD_RULES ${pf.rules.length}자(sha256 ${sha(pf.rules).slice(0, 12)}).`);
  say(`과제 ${tasks.length} × 반복 ${o.reps} × 갈래 ${arms.length} = 실행 ${tasks.length * Number(o.reps) * arms.length}.`);
  if (pf.problems.length) { for (const p of pf.problems) say(`✗ ${p}`); process.exitCode = 2; } else say('✓ 돌릴 준비가 됐다.');
}

function loadPlan(o, tasksSha) {
  mkdirSync(join(o.out, 'runs'), { recursive: true, mode: 0o700 });
  chmodSync(o.out, 0o700);
  const p = join(o.out, 'plan.json');
  if (existsSync(p)) {
    const plan = readJson(p);
    if (plan.model !== o.model) throw new Error(`이 결과 폴더는 모델 ${plan.model} 로 시작했다 — 다른 모델은 다른 --out 에`);
    if (plan.tasks_sha !== tasksSha) say('⚠ 과제 파일이 계획을 만든 뒤 바뀌었다 — 이어 하되 보고서에 적는다.');
    return plan;
  }
  const seed = o.seed != null ? Number(o.seed) : Math.floor(Math.random() * 2 ** 31);
  const plan = { created: new Date().toISOString(), seed, model: o.model, reps: Number(o.reps), tasks_sha: tasksSha };
  writeAtomic(p, `${JSON.stringify(plan, null, 1)}\n`);
  return plan;
}

async function runOne(job, ctx) {
  const { pf, o, plan, red, allowSha } = ctx;
  const key = keyOf(job.task.id, job.rep, job.arm);
  const recPath = join(o.out, 'runs', `${key}.json`);
  const evPath = join(o.out, 'runs', `${key}.events.jsonl`);
  const fence = pf.fz[job.arm];
  const tmp = mkdtempSync(join(tmpdir(), 'hwax-eval-'));
  LIVE.temps.add(tmp);
  chmodSync(tmp, 0o700);
  const cwd = join(tmpdir(), 'hwax-offload-eval-cwd');        // 빈 작업 폴더 — 리포 밖이라 프로젝트 설정 · CLAUDE.md 가 실리지 않는다
  mkdirSync(cwd, { recursive: true, mode: 0o700 });
  const headers = { Authorization: `Bearer ${pf.pat}`, 'X-HWAX-View': 'full' };   // 보기는 두 갈래 모두 전체(리포 .mcp.json 과 같이)
  if (job.arm === 'offload') headers['X-HWAX-Result'] = 'ref';
  const mcpPath = join(tmp, 'mcp.json'); const setPath = join(tmp, 'settings.json');
  writeFileSync(mcpPath, JSON.stringify({ mcpServers: { hwax: { type: 'http', url: pf.mcpUrl, headers } } }), { mode: 0o600 });
  writeFileSync(setPath, JSON.stringify(fence.settings), { mode: 0o600 });
  const args = ['-p', job.task.prompt, '--model', o.model, '--output-format', 'stream-json', '--verbose',
    '--mcp-config', mcpPath, '--strict-mcp-config', '--settings', setPath, '--setting-sources', 'local',
    '--permission-mode', 'dontAsk', '--tools', fence.builtins.join(','), '--no-session-persistence'];
  if (job.arm === 'offload') args.push('--append-system-prompt', pf.rules);
  if (o['max-budget-usd']) args.push('--max-budget-usd', String(o['max-budget-usd']));
  const env = { ...process.env, ENABLE_CLAUDEAI_MCP_SERVERS: 'false' };
  delete env.HWAX_GATEWAY_PAT;                                  // 자식에게는 넘기지 않는다(임시 파일의 머리로만 간다)
  if (!pf.toolSearch) env.ENABLE_TOOL_SEARCH = 'false';
  const started = Date.now(); const events = []; let stderr = '';
  const evTmp = `${evPath}.part`;
  writeFileSync(evTmp, '', { mode: 0o600 });
  let timedOut = false; let exit = null;
  try {
    exit = await new Promise((res) => {
      const ch = spawn(o.claude, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
      LIVE.children.add(ch);
      const lim = Number(o['timeout-min']) * 60000;
      const t1 = setTimeout(() => { timedOut = true; ch.kill('SIGINT'); setTimeout(() => ch.kill('SIGTERM'), 15000).unref(); setTimeout(() => ch.kill('SIGKILL'), 30000).unref(); }, lim);
      createInterface({ input: ch.stdout }).on('line', (line) => {
        const safe = red(line);
        writeFileSync(evTmp, `${safe}\n`, { flag: 'a' });
        try { events.push(JSON.parse(safe)); } catch { events.push({ type: '_raw', text: safe.slice(0, 2000) }); }
      });
      ch.stderr.on('data', (b) => { stderr = (stderr + b.toString('utf8')).slice(-20000); });
      ch.on('error', (e) => { stderr += `\n${e.message}`; });
      ch.on('close', (code, signal) => { clearTimeout(t1); LIVE.children.delete(ch); res({ code, signal }); });
    });
  } finally {
    rmSync(tmp, { recursive: true, force: true });             // PAT 가 든 임시 파일을 바로 지운다
    LIVE.temps.delete(tmp);
  }
  renameSync(evTmp, evPath);
  const dg = digest(events);
  const fc = fenceCheck(dg, job.arm, fence);
  const hwax = (dg.init?.mcp_servers || []).find((s) => s.name === 'hwax');
  let infra = null;
  // 시간 초과는 SIGINT 뒤에 result 를 내도 반쪽 답이다 — 기반 오류로 두어 합계 · 판정에서 빼고 다음 run 에 다시 돈다
  if (timedOut) infra = `시간 초과(${o['timeout-min']}분)`;
  else if (!dg.result) infra = `result 사건 없음(끝 코드 ${exit.code}${exit.signal ? ` · ${exit.signal}` : ''})`;
  else if (!hwax || /fail|error|auth/i.test(String(hwax.status))) infra = `hwax MCP 가 붙지 않았다(${hwax ? hwax.status : '목록에 없음'})`;
  const r = dg.result || {};
  const rec = {
    key, task: job.task.id, rep: job.rep, arm: job.arm, model: o.model, claude_version: pf.caps.version, seed: plan.seed,
    started_at: new Date(started).toISOString(), wall_ms: Date.now() - started, exit_code: exit.code, signal: exit.signal,
    timed_out: timedOut, infra_error: infra, allow_sha: allowSha, allow_n: fence.allow.length, builtins: fence.builtins,
    init: dg.init ? { model: dg.init.model, tools_n: (dg.init.tools || []).length, mcp_servers: dg.init.mcp_servers, permissionMode: dg.init.permissionMode } : null,
    result: dg.result ? {
      subtype: r.subtype, is_error: r.is_error, duration_ms: r.duration_ms, duration_api_ms: r.duration_api_ms, num_turns: r.num_turns,
      total_cost_usd: r.total_cost_usd, usage: r.usage, modelUsage: r.modelUsage, permission_denials_n: (r.permission_denials || []).length,
    } : null,
    answer: typeof r.result === 'string' ? r.result : '',
    calls: dg.calls.map((c) => ({ name: c.short, chars: c.chars, error: c.is_error, denied: c.denied, input: red(JSON.stringify(c.input ?? {})).slice(0, 300) })),
    fence: fc, stderr_tail: red(stderr).slice(-2000),
  };
  writeAtomic(recPath, `${JSON.stringify(rec, null, 1)}\n`);
  return rec;
}

async function cmdRun(o) {
  const arms = String(o.arms).split(',');
  if (!arms.every((a) => ARMS.includes(a))) throw new Error(`--arms 는 ${ARMS.join(' · ')} 가운데서`);
  const { tasks, sha: tasksSha } = loadTasks(o.tasks);
  const only = o.only ? new Set(String(o.only).split(',')) : null;
  const pf = await preflight(o, arms);
  if (pf.problems.length) { for (const p of pf.problems) say(`✗ ${p}`); throw new Error('사전 점검을 넘지 못했다 — check 로 다시 본다'); }
  const plan = loadPlan(o, tasksSha);
  const allowSha = writeAllowlist(o.out, pf);
  const red = redactor();
  const jobs = [];
  for (const t of tasks) if (!only || only.has(t.id)) for (let rep = 1; rep <= plan.reps; rep++) for (const arm of arms) jobs.push({ task: t, rep, arm });
  const order = shuffle(jobs, rng(plan.seed));               // 섞인 차례 — 갈래가 시간대(서버 부하)에 몰리지 않게
  const todo = order.filter((j) => {
    const p = join(o.out, 'runs', `${keyOf(j.task.id, j.rep, j.arm)}.json`);
    if (!existsSync(p)) return true;
    const rec = readJson(p);
    return !rec.result || !!rec.infra_error;                    // 끝난 것은 건너뛴다(이어 하기) — 기반 오류만 다시
  });
  say(`실행 ${jobs.length} 가운데 남은 것 ${todo.length} — 모델 ${o.model} · 동시 ${o.concurrency} · 씨앗 ${plan.seed}.`);
  let i = 0; let done = 0; let halted = null;
  const worker = async () => {
    while (!LIVE.stop && !halted && i < todo.length) {
      const j = todo[i++];
      const rec = await runOne(j, { pf, o, plan, red, allowSha });
      done++;
      const r = rec.result || {};
      say(`[${done}/${todo.length}] ${rec.key} — ${rec.infra_error ? `✗ ${rec.infra_error}` : `${r.subtype} · $${Number(r.total_cost_usd || 0).toFixed(3)} · ${Math.round((r.duration_ms || 0) / 1000)}초 · 도구 ${rec.calls.length}`}`);
      for (const w of rec.fence.warnings.slice(0, 3)) say(`   ⚠ ${w}`);
      if (rec.fence.violations.length) {
        halted = rec;
        say(`   ✗ 울타리 위반 — ${rec.fence.violations.join(' · ')}`);
        for (const c of LIVE.children) c.kill('SIGINT');
      }
    }
  };
  await Promise.all(Array.from({ length: Math.max(1, Number(o.concurrency)) }, worker));
  if (halted) { process.exitCode = 3; say(`울타리 위반으로 멈췄다(${halted.key}) — 보고서를 내기 전에 사람이 기록을 본다.`); }
  else if (LIVE.stop) { process.exitCode = 130; say('멈췄다 — 다시 run 하면 남은 것부터 이어 간다.'); }
  else say('끝. 다음은 judge.');
}

// ── judge ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

// 눈가림 — 갈래 이름은 판정 프롬프트에 싣지 않는다. 답 안의 2판 도구 이름 · 결과 손잡이도 두 답 모두에서 같은 표지로 바꾼다(갈래가 비치지 않게).
function mask(text) {
  return String(text || '')
    .replaceAll(MCP_PREFIX, '')
    .replace(new RegExp(`\\b(${OFFLOAD_TOOLS.join('|')})\\b`, 'g'), '[도구]')
    .replace(/\bres_[A-Za-z0-9_-]{6,}/g, '[ref]');
}

function judgePrompt(task, a, b, retry) {
  return [
    '너는 두 답을 견주는 심사자다. 같은 과제에 대한 답 A 와 답 B 가 있다. 어느 쪽이 더 나은지 판정한다.',
    '', '## 과제', task.prompt.trim(), '', '## 기대 꼴', String(task.expect?.shape || '(따로 없음)'),
    '', '## 답 A', mask(a).trim() || '(빈 답)', '', '## 답 B', mask(b).trim() || '(빈 답)', '',
    '## 판정 기준',
    '- correct(정확) — 과제에 맞고, 수치 · 사실이 서로 어긋나거나 지어낸 티가 없는가. 근거 없이 단정한 수치는 깎는다.',
    '- complete(충실) — 과제가 요구한 항목과 기대 꼴을 다 채웠는가.',
    '- clear(명료) — 읽고 바로 쓸 수 있게 정리됐는가.',
    '- 점수는 각 1 ~ 5 정수다. winner 는 셋을 종합해 A · B · tie 가운데 하나이고, 차이가 작으면 tie 다.',
    '- 길이 · 꾸밈이 아니라 내용으로 판정한다. 너는 도구로 사실을 확인할 수 없다 — 답 안의 일관성과 과제 부합으로만 본다.',
    '', '## 출력',
    '아래 꼴의 JSON 하나만 낸다(다른 글 없이).',
    '{"winner": "A|B|tie", "scores": {"A": {"correct": 1, "complete": 1, "clear": 1}, "B": {"correct": 1, "complete": 1, "clear": 1}}, "reason": "한두 문장"}',
    ...(retry ? ['', '앞 답이 이 꼴에 맞지 않았다. JSON 하나만 다시 낸다.'] : []),
  ].join('\n');
}

function parseVerdict(text) {
  const s = String(text || ''); const i = s.indexOf('{'); const j = s.lastIndexOf('}');
  if (i < 0 || j <= i) return null;
  let v; try { v = JSON.parse(s.slice(i, j + 1)); } catch { return null; }
  const okScore = (x) => Number.isInteger(x) && x >= 1 && x <= 5;
  if (!['A', 'B', 'tie'].includes(v?.winner)) return null;
  for (const side of ['A', 'B']) for (const k of ['correct', 'complete', 'clear']) if (!okScore(v.scores?.[side]?.[k])) return null;
  if (typeof v.reason !== 'string') return null;
  return { winner: v.winner, scores: { A: v.scores.A, B: v.scores.B }, reason: v.reason };
}

async function callJudge(o, prompt, red) {
  const tmp = mkdtempSync(join(tmpdir(), 'hwax-eval-j-'));
  LIVE.temps.add(tmp);
  chmodSync(tmp, 0o700);
  const cwd = join(tmpdir(), 'hwax-offload-eval-cwd');
  mkdirSync(cwd, { recursive: true, mode: 0o700 });
  const mcpPath = join(tmp, 'mcp.json'); const setPath = join(tmp, 'settings.json');
  writeFileSync(mcpPath, JSON.stringify({ mcpServers: {} }), { mode: 0o600 });
  writeFileSync(setPath, JSON.stringify({ permissions: { deny: BUILTINS, defaultMode: 'dontAsk' }, disableAllHooks: true, disableClaudeAiConnectors: true }), { mode: 0o600 });
  const args = ['-p', '표준 입력의 과제와 두 답을 판정 기준대로 견주고, 지시한 꼴의 JSON 하나만 낸다.', '--model', o['judge-model'],
    '--output-format', 'json', '--mcp-config', mcpPath, '--strict-mcp-config', '--settings', setPath, '--setting-sources', 'local',
    '--permission-mode', 'dontAsk', '--tools', '', '--no-session-persistence'];
  const env = { ...process.env, ENABLE_CLAUDEAI_MCP_SERVERS: 'false' };
  delete env.HWAX_GATEWAY_PAT;
  try {
    return await new Promise((res) => {
      const ch = spawn(o.claude, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
      LIVE.children.add(ch);
      let out = ''; let err = '';
      const t = setTimeout(() => ch.kill('SIGTERM'), Number(o['judge-timeout-min'] || 10) * 60000);
      ch.stdout.on('data', (b) => { out += b.toString('utf8'); });
      ch.stderr.on('data', (b) => { err = (err + b.toString('utf8')).slice(-4000); });
      ch.on('error', (e) => { err += e.message; });
      ch.on('close', (code) => {
        clearTimeout(t); LIVE.children.delete(ch);
        let r = null;
        for (const s of [out.trim(), out.trim().split('\n').pop()]) { try { r = JSON.parse(s); break; } catch { /* 다음 꼴로 — 둘 다 아니면 오류로 */ } }
        res({ code, result: r, stderr: red(err).slice(-1000) });
      });
      ch.stdin.end(prompt);
    });
  } finally { rmSync(tmp, { recursive: true, force: true }); LIVE.temps.delete(tmp); }
}

function pairsOf(o, tasks) {
  const runs = new Map();
  const dir = join(o.out, 'runs');
  if (existsSync(dir)) for (const f of readdirSync(dir)) if (f.endsWith('.json')) { const r = readJson(join(dir, f)); runs.set(r.key, r); }
  const pairs = [];
  const plan = existsSync(join(o.out, 'plan.json')) ? readJson(join(o.out, 'plan.json')) : { reps: Number(o.reps) };
  for (const t of tasks) for (let rep = 1; rep <= plan.reps; rep++) {
    const b = runs.get(keyOf(t.id, rep, 'baseline')); const f = runs.get(keyOf(t.id, rep, 'offload'));
    const ok = (r) => r && r.result && !r.infra_error;
    pairs.push({ task: t, rep, baseline: b, offload: f, matched: ok(b) && ok(f) });
  }
  return { pairs, runs, plan };
}

async function cmdJudge(o) {
  const { tasks } = loadTasks(o.tasks);
  const { pairs, plan } = pairsOf(o, tasks);
  const red = redactor();
  mkdirSync(join(o.out, 'judge'), { recursive: true, mode: 0o700 });
  const todo = pairs.filter((p) => p.matched && !(existsSync(join(o.out, 'judge', `${p.task.id}.r${p.rep}.json`)) && readJson(join(o.out, 'judge', `${p.task.id}.r${p.rep}.json`)).verdict));
  say(`판정할 짝 ${todo.length}(짝이 맞은 것 ${pairs.filter((p) => p.matched).length}) — 판정 모델 ${o['judge-model']}.`);
  for (const p of todo) {
    if (LIVE.stop) break;
    const r = rng(seedOf(plan.seed, 'judge', p.task.id, p.rep))();
    const map = r < 0.5 ? { A: 'baseline', B: 'offload' } : { A: 'offload', B: 'baseline' };
    const attempts = []; let verdict = null;
    for (let k = 0; k < 2 && !verdict; k++) {
      const prompt = judgePrompt(p.task, p[map.A].answer, p[map.B].answer, k > 0);
      const res = await callJudge(o, prompt, red);
      const text = res.result?.result;
      verdict = parseVerdict(text);
      attempts.push({ code: res.code, ok: !!verdict, cost: res.result?.total_cost_usd ?? null, usage: res.result?.usage ?? null, text: red(String(text ?? '')).slice(0, 4000), stderr: res.stderr });
    }
    const rec = { task: p.task.id, rep: p.rep, model: o['judge-model'], map, verdict, attempts, error: verdict ? null : '판정 꼴이 두 번 다 맞지 않았다' };
    writeAtomic(join(o.out, 'judge', `${p.task.id}.r${p.rep}.json`), `${JSON.stringify(rec, null, 1)}\n`);
    say(`${p.task.id}.r${p.rep} — ${verdict ? `${verdict.winner === 'tie' ? '무' : `${verdict.winner}(${map[verdict.winner]})`}` : '✗ 판정 실패'}`);
  }
}

// ── human ────────────────────────────────────────────────────────────────────────────────────────────────────────────────

async function cmdHuman(o) {
  const { tasks } = loadTasks(o.tasks);
  const { pairs, plan } = pairsOf(o, tasks);
  const md = join(o.out, 'human-review.md');
  if (existsSync(md) && !o.force) throw new Error(`${md} 가 이미 있다 — 적어 둔 판정을 지우지 않게 멈춘다(새로 만들려면 --force)`);
  const n = Number(o.pairs || 4);
  const pick = shuffle(pairs.filter((p) => p.matched), rng(seedOf(plan.seed, 'human'))).slice(0, n);
  const key = []; const out = [
    '# 사람 표본 판정 — 토큰 절감 2판 비교', '',
    '쌍마다 두 답(A · B)을 읽고 「판정」 줄에 A · B · 무 가운데 하나를 적는다. 어느 답이 어느 갈래인지는 human-key.json 에 따로 있다 — 다 적기 전에는 열지 않는다.',
    '판정 기준은 판정 모델과 같다 — 정확(수치 · 사실이 맞고 지어낸 티가 없는가) · 충실(요구한 항목 · 꼴) · 명료. 다 적은 뒤 report 를 다시 돌리면 판정 모델과의 일치를 센다.', '',
  ];
  pick.forEach((p, idx) => {
    const r = rng(seedOf(plan.seed, 'human-ab', p.task.id, p.rep))();
    const map = r < 0.5 ? { A: 'baseline', B: 'offload' } : { A: 'offload', B: 'baseline' };
    key.push({ pair: idx + 1, task: p.task.id, rep: p.rep, map });
    out.push('---', '', `## 쌍 ${idx + 1} — ${p.task.id} · 반복 ${p.rep} · ${p.task.title || ''}`, '', '### 과제', '', p.task.prompt.trim(), '',
      '### 기대 꼴', '', String(p.task.expect?.shape || '(따로 없음)'), '', '### 답 A', '', mask(p[map.A].answer).trim(), '',
      '### 답 B', '', mask(p[map.B].answer).trim(), '', '- 판정(A · B · 무):', '- 까닭:', '');
  });
  writeAtomic(md, `${out.join('\n')}\n`);
  writeAtomic(join(o.out, 'human-key.json'), `${JSON.stringify(key, null, 1)}\n`);
  say(`사람 표본 ${pick.length}쌍 — ${md}(갈래 열쇠는 human-key.json).`);
}

function readHuman(o) {
  const md = join(o.out, 'human-review.md'); const kp = join(o.out, 'human-key.json');
  if (!existsSync(md) || !existsSync(kp)) return null;
  const key = readJson(kp); const got = new Map(); let cur = null;
  for (const line of readFileSync(md, 'utf8').split('\n')) {
    const h = line.match(/^## 쌍 (\d+) — /);
    if (h) { cur = Number(h[1]); continue; }
    const v = line.match(/^- 판정\(A · B · 무\):\s*(.*)$/);
    if (v && cur != null) { const s = v[1].trim(); got.set(cur, s.startsWith('A') ? 'A' : s.startsWith('B') ? 'B' : s.startsWith('무') ? 'tie' : null); }
  }
  return key.map((k) => ({ ...k, winner: got.get(k.pair) ?? null }));
}

// ── report ───────────────────────────────────────────────────────────────────────────────────────────────────────────────

function metricsOf(o, rec, task) {
  const evp = join(o.out, 'runs', `${rec.key}.events.jsonl`);
  const events = existsSync(evp) ? readFileSync(evp, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return {}; } }) : [];
  const dg = digest(events);
  const u = rec.result?.usage || {};
  const sources = [task.prompt, ...dg.calls.flatMap((c) => c.texts)].join('\n');
  const nums = unsourcedNumbers(rec.answer, sources);
  const sv = serverSide(dg);
  const checks = shapeChecks(task.expect, rec.answer);
  const cv = Object.values(checks);
  return {
    cost: Number(rec.result?.total_cost_usd ?? NaN), input: Number(u.input_tokens ?? NaN), output: Number(u.output_tokens ?? NaN),
    cache_write: Number(u.cache_creation_input_tokens ?? 0), cache_read: Number(u.cache_read_input_tokens ?? 0),
    duration_s: Number(rec.result?.duration_ms ?? NaN) / 1000, turns: Number(rec.result?.num_turns ?? NaN),
    tool_calls: dg.calls.length, denied: rec.result?.permission_denials_n ?? 0,
    offload_used: [...new Set(dg.calls.filter((c) => OFFLOAD_TOOLS.includes(c.short) && !c.denied).map((c) => c.short))],
    checks, checks_ok: cv.filter((c) => c.ok).length, checks_n: cv.length,
    num_checked: nums.checked, num_unsourced: nums.bad.length, unsourced: nums.bad.slice(0, 10), server: sv,
  };
}

const fmt = (x, d = 0) => (Number.isFinite(x) ? x.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }) : '—');
const pct = (b, f) => (Number.isFinite(b) && Number.isFinite(f) && b > 0 ? `${fmt(((b - f) / b) * 100, 1)}%` : '—');

async function cmdReport(o) {
  const { tasks, sha: tasksSha } = loadTasks(o.tasks);
  const { pairs, runs, plan } = pairsOf(o, tasks);
  const matched = pairs.filter((p) => p.matched);
  const M = new Map();
  for (const p of matched) for (const a of ARMS) M.set(p[a].key, metricsOf(o, p[a], p.task));
  const agg = {};
  for (const a of ARMS) {
    const ms = matched.map((p) => M.get(p[a].key));
    agg[a] = {
      runs: ms.length, cost: sum(ms.map((m) => m.cost)), cost_med: median(ms.map((m) => m.cost)),
      input: sum(ms.map((m) => m.input)), output: sum(ms.map((m) => m.output)), cache_write: sum(ms.map((m) => m.cache_write)),
      cache_read: sum(ms.map((m) => m.cache_read)), duration_s: sum(ms.map((m) => m.duration_s)), duration_med: median(ms.map((m) => m.duration_s)),
      turns_med: median(ms.map((m) => m.turns)), tool_calls: sum(ms.map((m) => m.tool_calls)), denied: sum(ms.map((m) => m.denied)),
      checks_ok: sum(ms.map((m) => m.checks_ok)), checks_n: sum(ms.map((m) => m.checks_n)),
      num_checked: sum(ms.map((m) => m.num_checked)), num_unsourced: sum(ms.map((m) => m.num_unsourced)),
      server_mismatched: sum(ms.map((m) => m.server.mismatched)), server_jobs: sum(ms.map((m) => m.server.jobs)),
      server_tokens_in: sum(ms.map((m) => m.server.tokens_in)), server_tokens_out: sum(ms.map((m) => m.server.tokens_out)),
      server_jobs_without_tokens: sum(ms.map((m) => m.server.jobs_without_tokens)), server_unknown_calls: sum(ms.map((m) => m.server.unknown_calls)),
      server_calls_with_tokens: sum(ms.map((m) => m.server.calls_with_tokens)),
      server_unreadable: sum(ms.map((m) => m.server.unreadable)), runs_using_offload: ms.filter((m) => m.offload_used.length).length,
    };
    agg[a].claude_tokens = agg[a].input + agg[a].output + agg[a].cache_write + agg[a].cache_read;
    agg[a].tokens_med = median(ms.map((m) => m.input + m.output + m.cache_write + m.cache_read));
  }
  // 판정
  const J = new Map();
  for (const p of matched) {
    const jp = join(o.out, 'judge', `${p.task.id}.r${p.rep}.json`);
    if (existsSync(jp)) J.set(`${p.task.id}.r${p.rep}`, readJson(jp));
  }
  let wins = 0; let ties = 0; let losses = 0; let jfail = 0; let jcost = 0;
  const scoreSum = { baseline: { correct: 0, complete: 0, clear: 0 }, offload: { correct: 0, complete: 0, clear: 0 } };
  for (const j of J.values()) {
    jcost += sum(j.attempts.map((x) => Number(x.cost)));
    if (!j.verdict) { jfail++; continue; }
    const w = j.verdict.winner === 'tie' ? 'tie' : j.map[j.verdict.winner];
    if (w === 'offload') wins++; else if (w === 'baseline') losses++; else ties++;
    for (const side of ['A', 'B']) for (const k of ['correct', 'complete', 'clear']) scoreSum[j.map[side]][k] += j.verdict.scores[side][k];
  }
  const judged = wins + ties + losses;
  const lossRate = judged ? losses / judged : null;
  const maxLoss = Number(o['max-loss-rate']); const maxInc = Number(o['max-mismatch-increase']);
  const mmBase = agg.baseline.num_unsourced; const mmOff = agg.offload.num_unsourced + agg.offload.server_mismatched;
  const verdict = judged === 0 ? null : { loss_rate: lossRate, loss_ok: lossRate <= maxLoss, mismatch_base: mmBase, mismatch_off: mmOff, mismatch_ok: mmOff - mmBase <= maxInc };
  if (verdict) verdict.no_quality_difference = verdict.loss_ok && verdict.mismatch_ok;
  // 사람 표본
  const human = readHuman(o);
  let hFilled = 0; let hAgree = 0;
  for (const h of human || []) {
    if (!h.winner) continue;
    hFilled++;
    const j = J.get(`${h.task}.r${h.rep}`);
    if (!j?.verdict) continue;
    const hw = h.winner === 'tie' ? 'tie' : h.map[h.winner];
    const jw = j.verdict.winner === 'tie' ? 'tie' : j.map[j.verdict.winner];
    if (hw === jw) hAgree++;
  }
  const allRuns = [...runs.values()];
  const allowShas = new Set(allRuns.map((r) => r.allow_sha).filter(Boolean));
  const B = agg.baseline; const F = agg.offload;
  const L = [];
  L.push('# 토큰 절감 2판 비교 — 보고서', '');
  L.push(`- 만든 때 ${new Date().toISOString()} · 모델 ${plan.model || o.model} · 판정 모델 ${[...new Set([...J.values()].map((j) => j.model))].join(' · ') || '—'} · Claude Code ${[...new Set(allRuns.map((r) => r.claude_version))].join(' · ') || '—'} · 씨앗 ${plan.seed ?? '—'}`);
  L.push(`- 과제 ${tasks.length} × 반복 ${plan.reps ?? o.reps} — 실행 기록 ${allRuns.length} · 기반 오류 ${allRuns.filter((r) => r.infra_error).length} · 짝이 맞은 것 ${matched.length}(합계 · 판정은 이것만 센다)`);
  L.push(`- 허용 목록 — baseline ${allRuns.find((r) => r.arm === 'baseline')?.allow_n ?? '—'} · offload ${allRuns.find((r) => r.arm === 'offload')?.allow_n ?? '—'}(2판 도구 여덟 더함) · invoke_tool · rest_call 없음 · 내장은 ${[...new Set(allRuns.map((r) => (r.builtins || []).join('+') || '없음'))].join(' / ')}${allowShas.size > 1 ? ` · ⚠ 실행 사이에 허용 목록이 ${allowShas.size} 가지로 바뀌었다` : ''}`);
  if (plan.tasks_sha && plan.tasks_sha !== tasksSha) L.push('- ⚠ 과제 파일이 계획을 만든 뒤 바뀌었다.');
  L.push('', '## 판정 기준(제안 — 손잡이로 바꾼다)', '');
  L.push(`품질 차이 없음 = 판정 패배율 ≤ ${fmt(maxLoss * 100, 0)}%(--max-loss-rate) 이고 숫자 대조 어긋남이 늘지 않음(offload 어긋남 − baseline 어긋남 ≤ ${maxInc}, --max-mismatch-increase).`);
  L.push('offload 어긋남은 Claude 답의 출처 없는 수 + 서버가 표시한 numbers.mismatched 를 함께 센다(서버 답을 Claude 가 옮기면 Claude 쪽 대조로는 안 잡혀서).', '');
  if (!verdict) L.push('→ **판정 없음** — judge 를 먼저 돌린다.');
  else L.push(`→ **${verdict.no_quality_difference ? '충족 — 품질 차이 없음' : '미충족'}** — 패배율 ${fmt(lossRate * 100, 1)}%(${losses}/${judged}) ${verdict.loss_ok ? '✓' : '✗'} · 숫자 어긋남 baseline ${mmBase} → offload ${mmOff} ${verdict.mismatch_ok ? '✓' : '✗'}`);
  L.push('', '## 갈래 합계(짝이 맞은 실행)', '');
  L.push('| 갈래 | 실행 | 비용 USD 합 | 비용 중앙값 | Claude 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 토큰 합 | 토큰 중앙값 | 시간 합(분) | 시간 중앙값(초) | 턴 중앙값 | 도구 호출 | 막힌 호출 | 꼴 검사 | 숫자 확인/출처 없음 |');
  L.push('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|');
  for (const a of ARMS) {
    const g = agg[a];
    L.push(`| ${a} | ${g.runs} | ${fmt(g.cost, 2)} | ${fmt(g.cost_med, 3)} | ${fmt(g.input)} | ${fmt(g.cache_write)} | ${fmt(g.cache_read)} | ${fmt(g.output)} | ${fmt(g.claude_tokens)} | ${fmt(g.tokens_med)} | ${fmt(g.duration_s / 60, 1)} | ${fmt(g.duration_med, 0)} | ${fmt(g.turns_med, 1)} | ${g.tool_calls} | ${g.denied} | ${g.checks_ok}/${g.checks_n} | ${g.num_checked}/${g.num_unsourced} |`);
  }
  L.push(`| 줄인 몫(offload) | | ${pct(B.cost, F.cost)} | ${pct(B.cost_med, F.cost_med)} | ${pct(B.input, F.input)} | ${pct(B.cache_write, F.cache_write)} | ${pct(B.cache_read, F.cache_read)} | ${pct(B.output, F.output)} | ${pct(B.claude_tokens, F.claude_tokens)} | ${pct(B.tokens_med, F.tokens_med)} | ${pct(B.duration_s, F.duration_s)} | ${pct(B.duration_med, F.duration_med)} | ${pct(B.turns_med, F.turns_med)} | ${pct(B.tool_calls, F.tool_calls)} | | | |`);
  L.push('', '비용은 Claude Code 가 낸 total_cost_usd(클라이언트 어림 — 청구와 다를 수 있다)를 그대로 더했다. 줄인 몫이 음수면 offload 가 더 썼다.');
  L.push('', '## 서버 LLM — Claude 밖에서 쓴 것(숨기지 않는다)', '');
  L.push('| 갈래 | 2판 도구를 쓴 실행 | 위임 잡 | 서버 토큰 입력 | 서버 토큰 출력 | 토큰 모름(잡) | 토큰을 센 호출(작성 · 변환 · 묻기) | 토큰 모름(작성 · 변환 · 묻기 호출) | 서버 숫자 어긋남 | 읽지 못한 2판 결과 |');
  L.push('|---|---|---|---|---|---|---|---|---|---|');
  for (const a of ARMS) { const g = agg[a]; L.push(`| ${a} | ${g.runs_using_offload} | ${g.server_jobs} | ${fmt(g.server_tokens_in)} | ${fmt(g.server_tokens_out)} | ${g.server_jobs_without_tokens} | ${g.server_calls_with_tokens} | ${g.server_unknown_calls} | ${g.server_mismatched} | ${g.server_unreadable} |`); }
  L.push('', '서버 토큰은 위임 delegate_result 의 tokens(잡마다 한 번)와 draft_section · llm_transform · result_ask 결과의 tokens(호출마다)를 더한 것이다. tokens 칸이 없거나 null 인 잡 · 호출(옛 에이전트 서버 · 서버가 사용량을 주지 않은 호출)은 \'모름\' 으로 센다 — 그 몫은 관리 › 이용 통계의 그 사람 LLM 사용량(종류 offload — 옛 기록은 other)으로 함께 본다.');
  L.push('', '## 판정(눈가림)', '');
  L.push(`offload 승 ${wins} · 무 ${ties} · 패 ${losses}(판정 ${judged} / 짝 ${matched.length}) · 판정 실패 ${jfail} · 판정 비용 $${fmt(jcost, 2)}`);
  if (judged) {
    const av = (a, k) => fmt(scoreSum[a][k] / judged, 2);
    L.push('', '| 갈래 | 정확 평균 | 충실 평균 | 명료 평균 |', '|---|---|---|---|');
    for (const a of ARMS) L.push(`| ${a} | ${av(a, 'correct')} | ${av(a, 'complete')} | ${av(a, 'clear')} |`);
  }
  L.push('', '## 사람 표본', '');
  L.push(human ? `human-review.md ${human.length}쌍 가운데 적힌 것 ${hFilled} · 판정 모델과 일치 ${hAgree}/${hFilled}` : '아직 없다 — human 을 돌리고 적는다.');
  L.push('', '## 과제별', '');
  L.push('| 과제 | 반복 | 갈래 | 비용 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 | 시간(초) | 턴 | 도구 | 2판 도구 | 꼴 | 숫자 확인/출처 없음 | 서버 토큰 입/출 | 서버 어긋남 | 판정 |');
  L.push('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|');
  const perRun = [];
  for (const p of pairs) {
    if (!p.baseline && !p.offload) continue;                   // 아직 한 번도 안 돈 짝(--only 로 일부만 돌린 때)
    const j = J.get(`${p.task.id}.r${p.rep}`);
    const w = j?.verdict ? (j.verdict.winner === 'tie' ? '무' : `${j.map[j.verdict.winner]} 승`) : (j ? '실패' : '—');
    for (const a of ARMS) {
      const rec = p[a];
      if (!rec) { L.push(`| ${p.task.id} | ${p.rep} | ${a} | 없음 | | | | | | | | | | | | | |`); continue; }
      if (!p.matched) { L.push(`| ${p.task.id} | ${p.rep} | ${a} | ${rec.infra_error ? `✗ ${rec.infra_error}` : '(짝 없음)'} | | | | | | | | | | | | | |`); continue; }
      const m = M.get(rec.key);
      perRun.push({ key: rec.key, task: p.task.id, rep: p.rep, arm: a, ...m });
      const ck = Object.entries(m.checks).map(([k, v]) => `${v.ok ? '✓' : '✗'}${k}(${v.got})`).join(' ') || '—';
      L.push(`| ${p.task.id} | ${p.rep} | ${a} | ${fmt(m.cost, 3)} | ${fmt(m.input)} | ${fmt(m.cache_write)} | ${fmt(m.cache_read)} | ${fmt(m.output)} | ${fmt(m.duration_s, 0)} | ${fmt(m.turns)} | ${m.tool_calls} | ${m.offload_used.join(' · ') || '—'} | ${ck} | ${m.num_checked}/${m.num_unsourced} | ${a === 'offload' ? `${fmt(m.server.tokens_in)}/${fmt(m.server.tokens_out)}` : '—'} | ${a === 'offload' ? m.server.mismatched : '—'} | ${w} |`);
    }
  }
  // 끝은 났지만 success 가 아닌 실행(예산 상한 · 실행 중 오류 등)도 드러낸다 — 갈래의 결과라 합계 · 판정에는 그대로 든다
  const odd = (r) => r.result && (r.result.subtype !== 'success' || r.result.is_error);
  const warn = allRuns.filter((r) => r.fence?.warnings?.length || r.fence?.violations?.length || r.infra_error || odd(r));
  L.push('', '## 실패 · 경고', '');
  if (!warn.length) L.push('없음.');
  for (const r of warn) L.push(`- ${r.key} — ${[r.infra_error, odd(r) && !r.infra_error ? `결과 ${r.result.subtype}${r.result.is_error ? ' · is_error' : ''}` : null, ...(r.fence?.violations || []).map((v) => `위반 ${v}`), ...(r.fence?.warnings || []).slice(0, 3)].filter(Boolean).join(' · ')}`);
  writeAtomic(join(o.out, 'report.md'), `${L.join('\n')}\n`);
  writeAtomic(join(o.out, 'summary.json'), `${JSON.stringify({ arms: agg, judge: { wins, ties, losses, failed: jfail, judged, loss_rate: lossRate, cost: jcost }, verdict, human: human ? { pairs: human.length, filled: hFilled, agree: hAgree } : null, per_run: perRun }, null, 1)}\n`);
  say(`보고서 — ${join(o.out, 'report.md')}`);
}

// ── 입구 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

// 시험이 모듈로 읽는 것 — 파서 · 울타리 · 숫자 대조 · 꼴 검사 · 눈가림(backend/tests/test_offload_eval.py).
export { fences, judgePrompt, loadTasks, mask, offloadRules, parseYaml, shapeChecks, sigNumbers, unsourcedNumbers };

const CMDS = { check: cmdCheck, run: cmdRun, judge: cmdJudge, human: cmdHuman, report: cmdReport };
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.on('exit', cleanupTemps);
  process.on('SIGINT', () => {
    if (LIVE.stop) { cleanupTemps(); process.exit(130); }
    LIVE.stop = true;
    say('\n멈춤을 청했다 — 도는 실행에 SIGINT 를 보내고 임시 파일을 지운다(한 번 더 누르면 바로 끝낸다).');
    for (const c of LIVE.children) c.kill('SIGINT');
  });
  const [cmd, ...rest] = process.argv.slice(2);
  if (!CMDS[cmd]) {
    say('쓰는 법 — node run-eval.mjs <check|run|judge|human|report> [--손잡이 값 …] (README.md)');
    process.exit(cmd ? 2 : 0);
  }
  try {
    const o = parseArgs(rest);
    o.out = resolve(o.out);
    await CMDS[cmd](o);
  } catch (e) {
    say(`✗ ${redactor()(e.message)}`);
    process.exitCode = process.exitCode || 1;
  }
}
