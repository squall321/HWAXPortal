// 안전 마크다운 렌더러 — md.ts 파서의 블록 AST(제목/구분선/표/목록/인용/문단)와 인라인 서식을
// React 노드로 변환(HTML 미주입, 스트리밍 커서 지원). 코드펜스는 기존 세그먼트 분리 유지,
// html/svg 펜스는 sandbox iframe 미리보기 지원(포털 문서에 직접 주입하지 않음 — XSS 격리).
import { useState, type ReactNode } from 'react';
import { copyText } from '../clipboard';
import { IconCheck, IconCopy, IconExternal } from '../icons';
import { parseBlocks, parseInline, type Block } from './md';

type Segment =
  | { kind: 'text'; body: string }
  | { kind: 'code'; lang: string; body: string; closed: boolean };

// 펜스(```)를 기준으로 텍스트/코드 세그먼트 분리. 스트리밍 중 아직 닫히지 않은
// 펜스는 끝까지 코드로 취급해 토큰이 흐르는 동안에도 코드로 렌더된다.
// closed: 닫는 펜스를 만난 코드 블록만 true — 미완성 HTML 미리보기를 막는 근거.
function splitFences(text: string): Segment[] {
  const segments: Segment[] = [];
  const lines = text.split('\n');
  let buf: string[] = [];
  let inCode = false;
  let lang = '';

  const flush = (closed: boolean) => {
    if (buf.length === 0) return;
    segments.push(
      inCode ? { kind: 'code', lang, body: buf.join('\n'), closed } : { kind: 'text', body: buf.join('\n') },
    );
    buf = [];
  };

  for (const line of lines) {
    const fence = line.match(/^```(\S*)\s*$/);
    if (fence) {
      flush(inCode); // inCode였다면 이 펜스가 코드 블록을 닫는다
      inCode = !inCode;
      lang = inCode ? (fence[1] ?? '') : '';
    } else {
      buf.push(line);
    }
  }
  flush(false); // 텍스트 끝 — 코드였다면 아직 닫히지 않은 스트리밍 블록
  return segments;
}

// 인라인 서식(md.ts parseInline) → React 노드. 링크는 http/https 만 파서가 통과시키며
// 새 탭 + noopener 로만 연다. DelibView 발언 버블 등 인라인 전용 표면에서 재사용(InlineMd).
function renderInline(s: string, keyBase: string): ReactNode[] {
  return parseInline(s).map((tok, i) => {
    const key = `${keyBase}-i${i}`;
    switch (tok.t) {
      case 'code':
        return (
          <code key={key} className="inline-code">
            {tok.s}
          </code>
        );
      case 'bold':
        return <strong key={key}>{tok.s}</strong>;
      case 'em':
        return <em key={key}>{tok.s}</em>;
      case 'strike':
        return <del key={key}>{tok.s}</del>;
      case 'link':
        return (
          <a key={key} className="md-link" href={tok.href} target="_blank" rel="noopener noreferrer">
            {tok.s}
          </a>
        );
      default:
        return tok.s;
    }
  });
}

/** 인라인 마크다운만 렌더 — 심의 발언 버블처럼 블록 구조가 필요 없는 한 줄 표면용. */
export function InlineMd({ text }: { text: string }) {
  return <>{renderInline(text, 'im')}</>;
}

// 블록 AST → React 노드. 제목은 챗 버블 스케일에 맞춘 클래스(md-h1~h4)로,
// 표는 가로 스크롤 래퍼로 격리해 버블 폭을 넘지 않게 한다.
function renderBlock(b: Block, key: string): ReactNode {
  switch (b.t) {
    case 'h': {
      const lv = Math.min(b.level, 4);
      return (
        <div key={key} className={`md-h md-h${lv}`}>
          {renderInline(b.text, key)}
        </div>
      );
    }
    case 'hr':
      return <hr key={key} className="md-hr" />;
    case 'quote':
      return (
        <blockquote key={key} className="md-quote">
          {renderInline(b.text, key)}
        </blockquote>
      );
    case 'list': {
      const items = b.items.map((it, i) => (
        <li key={`${key}-l${i}`} className={it.depth ? `md-li-d${it.depth}` : undefined}>
          {renderInline(it.text, `${key}-l${i}`)}
        </li>
      ));
      return b.ordered ? (
        <ol key={key} className="md-list" start={b.start}>
          {items}
        </ol>
      ) : (
        <ul key={key} className="md-list">
          {items}
        </ul>
      );
    }
    case 'table':
      return (
        <div key={key} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {b.head.map((c, i) => (
                  <th key={i} style={{ textAlign: b.align[i] === 'c' ? 'center' : b.align[i] === 'r' ? 'right' : 'left' }}>
                    {renderInline(c, `${key}-h${i}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.rows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((c, ci) => (
                    <td
                      key={ci}
                      style={{ textAlign: b.align[ci] === 'c' ? 'center' : b.align[ci] === 'r' ? 'right' : 'left' }}
                    >
                      {renderInline(c, `${key}-r${ri}c${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    default:
      return (
        <p key={key} className="md-p">
          {renderInline(b.text, key)}
        </p>
      );
  }
}

// ── html/svg 미리보기 — sandbox iframe 경유만 허용(dangerouslySetInnerHTML 금지) ──

const PREVIEW_LANGS = new Set(['html', 'svg']);

// 콘텐츠 스타일은 콘텐츠가 결정 — 래핑 시 최소 스타일(margin 0, 시스템 폰트)만 주입.
const PREVIEW_PRELUDE =
  '<style>html,body{margin:0}body{padding:8px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#fff}</style>';

function buildSrcDoc(lang: string, body: string): string {
  if (lang === 'svg') {
    // 인라인 주입 금지 — svg도 srcDoc 최소 html로 감싸 같은 iframe 격리를 탄다.
    return `<!doctype html><html><head><meta charset="utf-8">${PREVIEW_PRELUDE}</head><body>${body}</body></html>`;
  }
  const head = body.trimStart().slice(0, 15).toLowerCase();
  // 완전한 문서면 그대로(문서 앞에 스타일을 붙이면 quirks 모드가 되므로), 조각이면 래핑.
  if (head.startsWith('<!doctype') || head.startsWith('<html')) return body;
  return `<!doctype html><html><head><meta charset="utf-8">${PREVIEW_PRELUDE}</head><body>${body}</body></html>`;
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

// 새 탭 열기 — blob: URL은 만든 문서(포털)의 오리진을 "상속"하므로 LLM HTML을 blob 문서에
// 직접 넣으면 포털 쿠키/스토리지에 닿는다. 신뢰된 래퍼 문서 안의 sandbox iframe(srcdoc)으로
// 한 번 더 감싸 챗 내 미리보기와 동일한 격리를 유지한다.
function openPreviewTab(lang: string, body: string): void {
  const doc =
    '<!doctype html><html><head><meta charset="utf-8"><title>HWAX 미리보기</title>' +
    '<style>html,body{margin:0;height:100%}iframe{display:block;border:0;width:100%;height:100%}</style>' +
    '</head><body><iframe sandbox="allow-scripts" referrerpolicy="no-referrer" srcdoc="' +
    escapeAttr(buildSrcDoc(lang, body)) +
    '"></iframe></body></html>';
  const url = URL.createObjectURL(new Blob([doc], { type: 'text/html' }));
  window.open(url, '_blank', 'noopener,noreferrer');
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

function PreviewFrame({ lang, body }: { lang: string; body: string }) {
  return (
    <div className="preview-wrap">
      {/* allow-same-origin 절대 금지 — 포털 쿠키/스토리지 격리 */}
      <iframe
        className="preview-frame"
        sandbox="allow-scripts"
        srcDoc={buildSrcDoc(lang, body)}
        referrerPolicy="no-referrer"
        title={lang === 'svg' ? 'SVG 미리보기' : 'HTML 미리보기'}
      />
    </div>
  );
}

function CodeBlock({ lang, body, closed, cursor }: { lang: string; body: string; closed: boolean; cursor: boolean }) {
  const [copied, setCopied] = useState(false);
  const [view, setView] = useState<'preview' | 'code'>('preview');
  const normLang = lang.toLowerCase();
  const previewable = PREVIEW_LANGS.has(normLang);
  // 스트리밍 중(펜스 미닫힘)에는 코드로 두고, 닫힌 뒤에만 미리보기 활성화.
  const showPreview = previewable && closed && view === 'preview';

  const onCopy = () => {
    void copyText(body).then((ok) => {
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="codeblock">
      <div className="codeblock-hd">
        <span className="codeblock-lang">{lang || 'code'}</span>
        <div className="codeblock-actions">
          {previewable && (
            <>
              <button
                type="button"
                className={`codeblock-toggle${showPreview ? ' active' : ''}`}
                disabled={!closed}
                onClick={() => setView('preview')}
                aria-label="미리보기로 전환"
              >
                미리보기
              </button>
              <button
                type="button"
                className={`codeblock-toggle${showPreview ? '' : ' active'}`}
                onClick={() => setView('code')}
                aria-label="코드로 전환"
              >
                코드
              </button>
              <button
                type="button"
                className="codeblock-copy"
                disabled={!closed}
                onClick={() => openPreviewTab(normLang, body)}
                aria-label="새 탭에서 열기"
                title="새 탭에서 열기"
              >
                <IconExternal width={13} height={13} />
              </button>
            </>
          )}
          <button type="button" className="codeblock-copy" onClick={onCopy} aria-label="코드 복사">
            {copied ? <IconCheck width={13} height={13} /> : <IconCopy width={13} height={13} />}
            <span>{copied ? '복사됨' : '복사'}</span>
          </button>
        </div>
      </div>
      {showPreview ? (
        <PreviewFrame lang={normLang} body={body} />
      ) : (
        <pre>
          <code>
            {body}
            {cursor && <span className="stream-cursor" aria-hidden="true" />}
          </code>
        </pre>
      )}
    </div>
  );
}

export function TextBlock({ text, cursor = false }: { text: string; cursor?: boolean }) {
  const segments = splitFences(text);
  const lastIdx = segments.length - 1;
  return (
    <div className="chat-text">
      {segments.map((seg, i) =>
        seg.kind === 'code' ? (
          <CodeBlock key={i} lang={seg.lang} body={seg.body} closed={seg.closed} cursor={cursor && i === lastIdx} />
        ) : (
          <span key={i} className="chat-text-seg">
            {parseBlocks(seg.body).map((b, bi) => renderBlock(b, `s${i}b${bi}`))}
            {cursor && i === lastIdx && <span className="stream-cursor" aria-hidden="true" />}
          </span>
        ),
      )}
      {segments.length === 0 && cursor && <span className="stream-cursor" aria-hidden="true" />}
    </div>
  );
}
