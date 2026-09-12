// 개인 클로드가 이 PC 의 DRM 문서를 Office COM 으로 읽게 해 주는 로컬 MCP 서버(stdio, 무의존)
//
// 왜 필요한가 — 포털 경로는 추출한 **글**을 서버로 보낸다. 이 경로는 그것조차 안 보낸다.
// 문서가 PC 를 한 발짝도 안 떠나고, 클로드가 읽어서 바로 논의한다.
//
// 등록:
//   claude mcp add hwax-doc -- node "C:\\<이 파일이 있는 폴더>\\hwax-doc-mcp.mjs"
// 읽기 허용 폴더를 바꾸려면(기본: 내 문서·바탕화면·다운로드):
//   set HWAX_DOC_ROOTS=D:\작업;E:\검토자료
//
// 의존성 0 — Node 18+ 만 있으면 된다(클로드 코드가 깔려 있으면 이미 있다).
import { spawn } from 'node:child_process';
import { readFileSync, readdirSync, statSync, existsSync, rmSync, mkdtempSync } from 'node:fs';
import { join, dirname, resolve, extname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir, homedir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const PS1 = join(HERE, 'hwax-doc-extract.ps1');
const EXTS = ['.pptx', '.ppt', '.docx', '.doc', '.pdf', '.rtf', '.htm', '.html'];

// 읽을 수 있는 폴더를 좁힌다. MCP 서버는 모델이 인자를 정하므로, 경로를 열어 두면
// 모델이 아무 파일이나 읽어 달라고 할 수 있다 — 사람이 정한 울타리 안에서만 움직인다.
const ROOTS = (process.env.HWAX_DOC_ROOTS
  ? process.env.HWAX_DOC_ROOTS.split(';')
  : ['Documents', 'Desktop', 'Downloads', '문서', '바탕 화면', '다운로드'].map((d) => join(homedir(), d))
).map((p) => resolve(p)).filter((p) => existsSync(p));

function insideRoots(p) {
  const abs = resolve(p);
  return ROOTS.some((r) => abs === r || abs.startsWith(r + '\\') || abs.startsWith(r + '/'));
}

function runExtract(file) {
  // 출력은 임시 폴더로 뺀다 — 사용자의 원본 옆에 파일을 만들지 않는다(허락 없이 남기지 않는다).
  const out = mkdtempSync(join(tmpdir(), 'hwax-doc-'));
  return new Promise((done) => {
    const ps = spawn('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', PS1,
      file, '-OutDir', out], { windowsHide: true });
    let err = '';
    ps.stderr.on('data', (d) => { err += d.toString(); });
    ps.on('error', (e) => done({ error: `PowerShell 을 실행하지 못했습니다: ${e.message}` }));
    ps.on('close', (code) => {
      try {
        const md = readdirSync(out).find((f) => f.endsWith('.hwax.md'));
        if (!md) {
          done({ error: `추출 결과가 없습니다(종료코드 ${code}).\n${err.slice(0, 2000)}` });
          return;
        }
        done({ text: readFileSync(join(out, md), 'utf-8') });
      } catch (e) {
        done({ error: `결과를 읽지 못했습니다: ${e.message}` });
      } finally {
        rmSync(out, { recursive: true, force: true });
      }
    });
  });
}

function listDocs(dir, limit) {
  const base = dir ? resolve(dir) : ROOTS[0];
  if (!base || !insideRoots(base)) {
    return { error: `읽을 수 있는 폴더가 아닙니다. 허용: ${ROOTS.join(', ') || '(없음)'}` };
  }
  const rows = [];
  for (const name of readdirSync(base)) {
    if (!EXTS.includes(extname(name).toLowerCase())) continue;
    try {
      const st = statSync(join(base, name));
      if (st.isFile()) rows.push({ path: join(base, name), bytes: st.size, mtime: st.mtime.toISOString() });
    } catch { /* 읽기 권한 없는 항목은 건너뛴다 */ }
  }
  rows.sort((a, b) => (a.mtime < b.mtime ? 1 : -1));
  return { dir: base, files: rows.slice(0, limit || 30) };
}

const TOOLS = [
  {
    name: 'extract_document',
    description:
      '이 PC 의 문서(PPT·Word·PDF·HTML)를 설치된 Office COM 으로 읽어 평문 마크다운으로 돌려준다. '
      + 'DRM 문서는 이 PC·이 계정에서만 복호화되므로 서버가 파싱할 수 없다 — 그래서 여기서 읽는다. '
      + '슬라이드는 [s.N], 쪽은 [p.N] 으로 표시되니 근거를 인용할 때 그 번호를 함께 적어라. '
      + '원본 파일은 어디로도 전송되지 않는다.',
    inputSchema: {
      type: 'object',
      properties: { path: { type: 'string', description: '문서의 전체 경로' } },
      required: ['path'],
    },
  },
  {
    name: 'list_recent_documents',
    description: '읽을 수 있는 폴더에서 최근 문서를 나열한다. 사용자가 파일 이름만 말할 때 경로를 찾는 용도.',
    inputSchema: {
      type: 'object',
      properties: {
        dir: { type: 'string', description: '폴더 경로(생략하면 기본 폴더)' },
        limit: { type: 'integer', description: '최대 개수(기본 30)' },
      },
    },
  },
];

async function handle(req) {
  const { id, method, params } = req;
  const ok = (result) => ({ jsonrpc: '2.0', id, result });
  const text = (s) => ok({ content: [{ type: 'text', text: s }] });
  const fail = (s) => ok({ content: [{ type: 'text', text: s }], isError: true });

  if (method === 'initialize') {
    return ok({
      protocolVersion: params?.protocolVersion || '2024-11-05',
      capabilities: { tools: {} },
      serverInfo: { name: 'hwax-doc', version: '1.0.0' },
    });
  }
  if (method === 'tools/list') return ok({ tools: TOOLS });
  if (method === 'tools/call') {
    const args = params?.arguments || {};
    if (params?.name === 'list_recent_documents') {
      const r = listDocs(args.dir, args.limit);
      return r.error ? fail(r.error) : text(JSON.stringify(r, null, 1));
    }
    if (params?.name === 'extract_document') {
      const p = String(args.path || '').trim();
      if (!p) return fail('path 가 필요합니다.');
      if (!existsSync(p)) return fail(`파일이 없습니다: ${p}`);
      if (!insideRoots(p)) {
        return fail(`읽기 허용 폴더 밖입니다: ${p}\n허용: ${ROOTS.join(', ') || '(없음)'}\n`
          + '다른 폴더를 열려면 HWAX_DOC_ROOTS 환경변수에 추가하세요.');
      }
      if (!EXTS.includes(extname(p).toLowerCase())) {
        return fail(`지원하지 않는 형식입니다: ${extname(p)} (${EXTS.join(' ')})`);
      }
      if (!existsSync(PS1)) return fail(`추출기가 옆에 없습니다: ${PS1}`);
      const r = await runExtract(p);
      return r.error ? fail(r.error) : text(r.text);
    }
    return fail(`알 수 없는 도구: ${params?.name}`);
  }
  if (method === 'ping') return ok({});
  if (method?.startsWith('notifications/')) return null;   // 알림엔 응답하지 않는다
  return { jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } };
}

// stdio 는 줄 단위 JSON-RPC 다. 청크가 줄 중간에서 끊기므로 버퍼에 모아 줄로 잘라 읽는다.
let buf = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', async (chunk) => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    let req;
    try { req = JSON.parse(line); } catch { continue; }
    try {
      const res = await handle(req);
      if (res) process.stdout.write(JSON.stringify(res) + '\n');
    } catch (e) {
      if (req?.id !== undefined) {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: req.id,
          error: { code: -32603, message: String(e?.message || e) },
        }) + '\n');
      }
    }
  }
});
process.stdin.on('end', () => process.exit(0));
