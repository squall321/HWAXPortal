// 인자 입력 2단 — 스키마 폼 + 원문 JSON
//
// 게이트웨이 465종 중 44종이 **속성 없는 object/array** 다(predict_sed 의 sample,
// create_report_draft 의 blocks). 그런 인자는 필수 필드 목록이 스키마가 아니라 도구 설명
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

  if (!tool) return <p className="pr-muted">도구를 먼저 고르세요.</p>;

  return (
    <div className="pr-form">
      {tool.description && (
        <div className="pr-meta">
          <button
            type="button"
            onClick={() => setOpenDesc((v) => !v)}
            className="pr-link-btn"
          >
            {openDesc ? '설명 접기' : '도구 설명 보기'}
          </button>
          {openDesc && (
            <p className="pr-prewrap pr-mt-2">{tool.description}</p>
          )}
        </div>
      )}

      {hasForm && !state.useRaw ? (
        <>
          {Object.entries(props).map(([key, sch]) => {
            const k = kindOf(sch);
            const structural = k === 'object' || k === 'array';
            return (
              <label key={key} className="pr-field">
                <span className="pr-label">
                  <code>{key}</code>
                  {required.has(key) && <span className="pr-danger"> *</span>}
                  <span className="pr-muted"> · {k}</span>
                  {structural && (
                    <span className="pr-muted"> — 원문 JSON 으로 넣습니다</span>
                  )}
                </span>
                {k === 'enum' ? (
                  <select
                    className="pr-input"
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
                    className="pr-input"
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
                    className="pr-input pr-mono"
                    placeholder={k === 'array' ? '[]' : '{}'}
                    value={state.values[key] ?? ''}
                    onChange={(e) => onChange({ ...state, values: { ...state.values, [key]: e.target.value } })}
                  />
                ) : (
                  <input
                    className="pr-input"
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
            className="pr-box-btn"
          >
            원문 JSON 으로 쓰기
          </button>
        </>
      ) : (
        <label className="pr-field">
          <span className="pr-label">
            인자(JSON)
            {!hasForm && (
              <span className="pr-muted"> — 이 도구는 스키마에 속성이 없습니다</span>
            )}
          </span>
          <textarea rows={8} className="pr-input pr-mono" value={state.raw} onChange={(e) => onChange({ ...state, raw: e.target.value })} />
          {hasForm && (
            <button
              type="button"
              onClick={() => onChange({ ...state, useRaw: false })}
              className="pr-box-btn"
            >
              폼으로 돌아가기
            </button>
          )}
        </label>
      )}
    </div>
  );
}
