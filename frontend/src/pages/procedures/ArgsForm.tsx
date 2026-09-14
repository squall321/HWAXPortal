// 인자 입력 2단 — 스키마 폼 + 원문 JSON
//
// 게이트웨이 465종 중 44종이 **속성 없는 object/array** 다(predict_sed 의 sample,
// create_report_draft 의 blocks). 그실행 인자는 필수 필드 목록이 스키마가 아니라 도구 설명
// 산문에 있어서 폼을 그릴 수가 없다 — 원문 JSON 으로 받고 설명을 옆에 접어 둔다.
//
// 프론트에서 값을 검증하지 않는다. 서버(도구 pydantic)가 돌려준 오류를 그대로 보인다 —
// 두 곳에서 같은 판정을 하면 반드시 어긋난다.
//
// 새 npm 의존성 0 — rjsf·monaco 를 들이지 않는다(cae00 은 오프라인 pnpm 빌드다).
import { useMemo, useState } from 'react';
import type { JsonSchema, ToolInfo } from '../../api/procedures.api';

export type ArgsState = { values: Record<string, string>; raw: string; useRaw: boolean };

export function emptyArgs(): ArgsState {
  return { values: {}, raw: '{}', useRaw: false };
}

/** 폼 상태 → 실제로 보낼 인자. 파싱 실패는 throw 한다(호출부가 화면에 띄운다). */
export function buildArgs(tool: ToolInfo | null, st: ArgsState): Record<string, unknown> {
  if (st.useRaw || !tool || !Object.keys(tool.inputSchema?.properties ?? {}).length) {
    const t = st.raw.trim();
    if (!t) return {};
    const parsed: unknown = JSON.parse(t);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('인자는 JSON 객체여야 합니다 — 예: {"project_id": "abc"}');
    }
    return parsed as Record<string, unknown>;
  }
  const out: Record<string, unknown> = {};
  for (const [key, sch] of Object.entries(tool.inputSchema.properties ?? {})) {
    const rawVal = st.values[key];
    if (rawVal === undefined || rawVal === '') continue;
    out[key] = coerce(key, rawVal, sch);
  }
  return out;
}

function kindOf(sch: JsonSchema): string {
  if (sch.enum?.length) return 'enum';
  const t = Array.isArray(sch.type) ? sch.type[0] : sch.type;
  if (t) return t;
  // anyOf: [{type:'number'},{type:'null'}] — 선택 인자의 흔한 모양이다
  const first = sch.anyOf?.find((a) => a.type && a.type !== 'null');
  return (Array.isArray(first?.type) ? first?.type[0] : first?.type) ?? 'string';
}

function coerce(key: string, raw: string, sch: JsonSchema): unknown {
  const k = kindOf(sch);
  if (k === 'integer' || k === 'number') {
    const n = Number(raw);
    if (Number.isNaN(n)) throw new Error(`${key}: 수치가 아닙니다 — ${raw}`);
    return n;
  }
  if (k === 'boolean') return raw === 'true';
  if (k === 'object' || k === 'array') {
    try {
      return JSON.parse(raw);
    } catch {
      throw new Error(`${key}: JSON 이 아닙니다`);
    }
  }
  return raw; // 문자열은 {{var}} 도 그대로 통과시킨다 — 치환은 서버가 한다
}

const box: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg)',
  color: 'var(--fg)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '0.4rem 0.55rem',
  fontSize: '0.85rem',
};
const mono = { ...box, fontFamily: 'var(--cx-mono, monospace)' };

export function ArgsForm({
  tool,
  state,
  onChange,
}: {
  tool: ToolInfo | null;
  state: ArgsState;
  onChange: (s: ArgsState) => void;
}) {
  const [openDesc, setOpenDesc] = useState(false);
  const props = tool?.inputSchema?.properties ?? {};
  const required = useMemo(() => new Set(tool?.inputSchema?.required ?? []), [tool]);
  const hasForm = Object.keys(props).length > 0;

  if (!tool) return <p style={{ color: 'var(--muted)' }}>도구를 먼저 고르세요.</p>;

  return (
    <div style={{ display: 'grid', gap: '0.7rem' }}>
      {tool.description && (
        <div style={{ fontSize: '0.82rem', color: 'var(--muted)' }}>
          <button
            type="button"
            onClick={() => setOpenDesc((v) => !v)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--muted)',
              cursor: 'pointer',
              padding: 0,
              textDecoration: 'underline',
            }}
          >
            {openDesc ? '설명 접기' : '도구 설명 보기'}
          </button>
          {openDesc && (
            <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.4rem' }}>{tool.description}</p>
          )}
        </div>
      )}

      {hasForm && !state.useRaw ? (
        <>
          {Object.entries(props).map(([key, sch]) => {
            const k = kindOf(sch);
            const structural = k === 'object' || k === 'array';
            return (
              <label key={key} style={{ display: 'grid', gap: '0.25rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--fg)' }}>
                  <code>{key}</code>
                  {required.has(key) && <span style={{ color: '#f0a' }}> *</span>}
                  <span style={{ color: 'var(--muted)' }}> · {k}</span>
                  {structural && (
                    <span style={{ color: 'var(--muted)' }}> — 원문 JSON 으로 넣습니다</span>
                  )}
                </span>
                {k === 'enum' ? (
                  <select
                    style={box}
                    value={state.values[key] ?? ''}
                    onChange={(e) => onChange({ ...state, values: { ...state.values, [key]: e.target.value } })}
                  >
                    <option value="">(비움)</option>
                    {(sch.enum ?? []).map((v) => (
                      <option key={String(v)} value={String(v)}>
                        {String(v)}
                      </option>
                    ))}
                  </select>
                ) : k === 'boolean' ? (
                  <select
                    style={box}
                    value={state.values[key] ?? ''}
                    onChange={(e) => onChange({ ...state, values: { ...state.values, [key]: e.target.value } })}
                  >
                    <option value="">(비움)</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : structural ? (
                  <textarea
                    rows={4}
                    style={mono}
                    placeholder={k === 'array' ? '[]' : '{}'}
                    value={state.values[key] ?? ''}
                    onChange={(e) => onChange({ ...state, values: { ...state.values, [key]: e.target.value } })}
                  />
                ) : (
                  <input
                    style={box}
                    value={state.values[key] ?? ''}
                    placeholder={sch.description?.slice(0, 60) ?? ''}
                    onChange={(e) => onChange({ ...state, values: { ...state.values, [key]: e.target.value } })}
                  />
                )}
              </label>
            );
          })}
          <button
            type="button"
            onClick={() => onChange({ ...state, useRaw: true })}
            style={{ ...box, cursor: 'pointer', width: 'auto', justifySelf: 'start' }}
          >
            원문 JSON 으로 쓰기
          </button>
        </>
      ) : (
        <label style={{ display: 'grid', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--fg)' }}>
            인자(JSON)
            {!hasForm && (
              <span style={{ color: 'var(--muted)' }}> — 이 도구는 스키마에 속성이 없습니다</span>
            )}
          </span>
          <textarea rows={8} style={mono} value={state.raw} onChange={(e) => onChange({ ...state, raw: e.target.value })} />
          {hasForm && (
            <button
              type="button"
              onClick={() => onChange({ ...state, useRaw: false })}
              style={{ ...box, cursor: 'pointer', width: 'auto', justifySelf: 'start' }}
            >
              폼으로 돌아가기
            </button>
          )}
        </label>
      )}
    </div>
  );
}
