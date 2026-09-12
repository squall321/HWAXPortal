// 붙인 문서를 브라우저에서 직접 읽어 챗·심의 근거로 만든다 — 원본은 서버로 올리지 않는다
import type { HandoffEvidence } from './handoff';

/** 문서 한 건당 상한(자). **포털 ChatDocument.text 상한 이하**여야 한다 — 크면 붙일 수는
 *  있는데 전송이 422 로 죽는다(계약 테스트가 이 역전을 본다).
 *  여기서 미리 자르지 않는 이유는, 자르는 일을 예산과 낱장 경계를 아는 서버가 하기 때문이다.
 *  200슬라이드급 발표자료도 통째로 보낸다. */
export const DOC_CHARS_MAX = 2_000_000;
/** 한 발화에 붙일 수 있는 문서 수. */
export const DOC_MAX = 5;

/** COM 추출이 필요한 형식 — 브라우저는 COM 을 못 부르고, DRM 은 서버 파싱을 막는다. */
const EXT_NEEDS_COM = ['pptx', 'ppt', 'docx', 'doc', 'pdf', 'rtf', 'odt', 'odp', 'htm', 'html', 'mht', 'mhtml'];
/** 그대로 읽히는 형식 — 추출기 산출물(.hwax.md)과 평문. */
const EXT_TEXT = ['md', 'txt', 'text', 'log'];
/** 종전 업로드 경로(물성 DB·StepForge)가 가져가는 형식. */
const EXT_UPLOAD = ['csv', 'xlsx', 'step', 'stp', 'msh', 'zip'];

export type DocVerdict = 'text' | 'needs-com' | 'upload' | 'unknown';

export interface AttachedDoc {
  name: string;
  /** 본문(추출문). 이것만 서버로 간다. */
  text: string;
  chars: number;
  /** 추출기가 남긴 머리말 — 없으면 사용자가 직접 만든 평문이다. */
  meta?: DocMeta;
  /** 원문이 상한을 넘어 잘렸나. */
  truncated: boolean;
}

export interface DocMeta {
  schema?: string;
  source?: string;
  kind?: string;
  units?: string;
  chars?: string;
  extractedBy?: string;
  extractedAt?: string;
}

export function extOf(name: string): string {
  const i = name.lastIndexOf('.');
  return i < 0 ? '' : name.slice(i + 1).toLowerCase();
}

/** 이 파일을 어떻게 다룰지. 확장자로만 판정한다 — 내용을 읽기 전에 정해야 하는 갈림길이다. */
export function classify(name: string): DocVerdict {
  const e = extOf(name);
  if (EXT_TEXT.includes(e)) return 'text';
  if (EXT_NEEDS_COM.includes(e)) return 'needs-com';
  if (EXT_UPLOAD.includes(e)) return 'upload';
  return 'unknown';
}

/** 추출기 머리말(--- … ---) 파싱. 사람이 만든 평문에는 없으므로 undefined 가 정상이다. */
export function parseMeta(text: string): DocMeta | undefined {
  if (!text.startsWith('---')) return undefined;
  const end = text.indexOf('\n---', 3);
  if (end < 0) return undefined;
  const head = text.slice(3, end);
  const kv: Record<string, string> = {};
  for (const line of head.split('\n')) {
    const m = /^([a-z_]+):\s*(.+)$/.exec(line.trim());
    if (m) kv[m[1]] = m[2].trim();
  }
  if (!kv.schema?.startsWith('hwax-doc/')) return undefined;
  return {
    schema: kv.schema,
    source: kv.source,
    kind: kv.kind,
    units: kv.units,
    chars: kv.chars,
    extractedBy: kv.extracted_by,
    extractedAt: kv.extracted_at,
  };
}

/** 형식 이름 — 칩에 보여 준다. */
export function kindLabel(meta: DocMeta | undefined): string {
  switch (meta?.kind) {
    case 'ppt': return '발표자료';
    case 'word': return '문서';
    case 'pdf': return 'PDF';
    case 'html': return 'HTML';
    default: return '문서';
  }
}

/** 낱장 수 표기 — 발표자료는 슬라이드, 나머지는 쪽. */
export function unitsLabel(meta: DocMeta | undefined): string {
  if (!meta?.units) return '';
  return meta.kind === 'ppt' ? `${meta.units}슬라이드` : `${meta.units}쪽`;
}

/** 브라우저에서 파일을 읽어 문서 한 건으로. 서버를 거치지 않는다(원본 반출 없음). */
export async function readDoc(file: File): Promise<AttachedDoc> {
  const raw = await file.text();
  const truncated = raw.length > DOC_CHARS_MAX;
  const text = truncated ? raw.slice(0, DOC_CHARS_MAX) : raw;
  if (!text.trim()) throw new Error(`${file.name} — 글자가 없습니다.`);
  return { name: file.name, text, chars: text.length, meta: parseMeta(text), truncated };
}

/** 붙인 문서를 심의 사전 근거 항목으로. 도구 결과와 같은 채널을 쓴다 —
 *  심의 엔진이 이미 '검증 대상이지 결론이 아니다' 로 프레이밍해 좌석에 주기 때문이다. */
export function docsAsEvidence(docs: AttachedDoc[]): HandoffEvidence[] {
  return docs.map((d) => ({
    source: `업로드 문서 · ${d.meta?.source || d.name}`.slice(0, 200),
    tool: d.meta?.extractedBy ? 'office-com-extract' : 'text-attach',
    args: [kindLabel(d.meta), unitsLabel(d.meta), `${d.chars.toLocaleString()}자`]
      .filter(Boolean).join(' · ').slice(0, 1200),
    result: d.text,
  }));
}
