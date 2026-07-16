// 최소 안전 마크다운 렌더러 — 코드펜스/인라인코드/볼드만 React 노드로 변환(HTML 미주입, 스트리밍 커서 지원)
import { useState, type ReactNode } from 'react';
import { copyText } from '../clipboard';
import { IconCheck, IconCopy } from '../icons';

type Segment = { kind: 'text'; body: string } | { kind: 'code'; lang: string; body: string };

// 펜스(```)를 기준으로 텍스트/코드 세그먼트 분리. 스트리밍 중 아직 닫히지 않은
// 펜스는 끝까지 코드로 취급해 토큰이 흐르는 동안에도 코드로 렌더된다.
function splitFences(text: string): Segment[] {
  const segments: Segment[] = [];
  const lines = text.split('\n');
  let buf: string[] = [];
  let inCode = false;
  let lang = '';

  const flush = () => {
    if (buf.length === 0) return;
    segments.push(inCode ? { kind: 'code', lang, body: buf.join('\n') } : { kind: 'text', body: buf.join('\n') });
    buf = [];
  };

  for (const line of lines) {
    const fence = line.match(/^```(\S*)\s*$/);
    if (fence) {
      flush();
      inCode = !inCode;
      lang = inCode ? (fence[1] ?? '') : '';
    } else {
      buf.push(line);
    }
  }
  flush();
  return segments;
}

// 텍스트 세그먼트 안의 `inline code` 와 **bold** 처리 (그 외는 pre-wrap 일반 텍스트).
function renderInline(s: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/g;
  let last = 0;
  let i = 0;
  for (let m = re.exec(s); m; m = re.exec(s)) {
    if (m.index > last) out.push(s.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('`')) {
      out.push(
        <code key={`${keyBase}-c${i++}`} className="inline-code">
          {tok.slice(1, -1)}
        </code>,
      );
    } else {
      out.push(<strong key={`${keyBase}-b${i++}`}>{tok.slice(2, -2)}</strong>);
    }
    last = m.index + tok.length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

function CodeBlock({ lang, body, cursor }: { lang: string; body: string; cursor: boolean }) {
  const [copied, setCopied] = useState(false);
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
        <button type="button" className="codeblock-copy" onClick={onCopy} aria-label="코드 복사">
          {copied ? <IconCheck width={13} height={13} /> : <IconCopy width={13} height={13} />}
          <span>{copied ? '복사됨' : '복사'}</span>
        </button>
      </div>
      <pre>
        <code>
          {body}
          {cursor && <span className="stream-cursor" aria-hidden="true" />}
        </code>
      </pre>
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
          <CodeBlock key={i} lang={seg.lang} body={seg.body} cursor={cursor && i === lastIdx} />
        ) : (
          <span key={i} className="chat-text-seg">
            {renderInline(seg.body, `s${i}`)}
            {cursor && i === lastIdx && <span className="stream-cursor" aria-hidden="true" />}
          </span>
        ),
      )}
      {segments.length === 0 && cursor && <span className="stream-cursor" aria-hidden="true" />}
    </div>
  );
}
