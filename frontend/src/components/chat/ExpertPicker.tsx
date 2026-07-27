// 심의 전 전문가 확인·수동추가 패널 — 추천(기본 선택)을 보여주고, 질문 관련도순 후보/검색으로 추가
import { useEffect, useMemo, useRef, useState } from 'react';
import type { ExpertsResponse, RecommendedExpert } from '../../api/chat.api';

export interface Persona {
  key: string;
  name: string;
  role: string;
}

interface ExpertPickerProps {
  topic: string;
  loading: boolean;
  experts: ExpertsResponse | null;
  /** 선택 전문가(+선택 도구 — 심의에서 실제 호출돼 정량 근거로 주입)로 심의 시작. */
  onConfirm: (personas: Persona[], tools: string[]) => void;
  onCancel: () => void;
}

const MIN_EXPERTS = 2; // 서버 심의는 전문가 2명 이상 필요
const MAX_EXPERTS = 12; // 심의 계약(delib_opts.personas) 상한
const DEFAULT_COUNT = 5;
const COUNT_OPTIONS = [3, 5, 7, 10, 12];
const POOL_LIMIT = 30; // 결과 표시 상한
const MAX_TOOLS = 6; // 심의 계약(delib_opts.tools) 상한 — 도구당 인자구성+호출 비용이 있어 보수적
const TOOL_LIST_LIMIT = 20;

interface AddRow {
  key: string;
  name: string;
  tags: string[];
  score?: number | null;
  role?: string;
  rank: number;
}

export function ExpertPicker({ topic, loading, experts, onConfirm, onCancel }: ExpertPickerProps) {
  // 선택 집합 — key → persona. 관련도순 상위 autoCount 명을 기본 선택으로 시딩한다.
  const [chosen, setChosen] = useState<Record<string, Persona>>({});
  const [autoCount, setAutoCount] = useState(DEFAULT_COUNT);
  const [query, setQuery] = useState('');
  // 선택 도구 — 기본 빈 집합(자동 파이프라인 도구는 항상 돌아감). 고르면 실제 호출돼 근거 주입.
  const [toolSel, setToolSel] = useState<Set<string>>(new Set());
  const [toolQuery, setToolQuery] = useState('');
  const seededRef = useRef(false);

  // 관련도순 랭킹 — candidates(≈40) 우선, 없으면 recommended 폴백.
  const ranked = useMemo<RecommendedExpert[]>(
    () => (experts?.candidates?.length ? experts.candidates : experts?.recommended || []),
    [experts],
  );

  const seed = (n: number): Record<string, Persona> => {
    const m: Record<string, Persona> = {};
    for (const r of ranked.slice(0, n)) m[r.key] = { key: r.key, name: r.name, role: r.role };
    return m;
  };

  useEffect(() => {
    if (seededRef.current || !experts) return;
    setChosen(seed(DEFAULT_COUNT));
    seededRef.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [experts]);

  // 자동 인원 변경 = 관련도 상위 N 명으로 재선택(명시적 액션 — 이후 수동 편집은 유지).
  const changeCount = (n: number) => {
    setAutoCount(n);
    setChosen(seed(n));
  };

  const toggle = (p: Persona) =>
    setChosen((prev) => {
      const next = { ...prev };
      if (next[p.key]) delete next[p.key];
      else if (Object.keys(next).length < MAX_EXPERTS) next[p.key] = p;
      return next;
    });

  const add = (r: { key: string; name: string; role?: string }) =>
    setChosen((prev) => {
      if (prev[r.key] || Object.keys(prev).length >= MAX_EXPERTS) return prev;
      return { ...prev, [r.key]: { key: r.key, name: r.name, role: r.role || '' } };
    });

  const chosenList = useMemo(() => Object.values(chosen), [chosen]);
  const full = chosenList.length >= MAX_EXPERTS;

  // 후보(질문 연관도순) 인덱스 — 검색 결과를 관련도 우선으로 정렬하는 데 사용.
  const candByKey = useMemo(() => {
    const m = new Map<string, { rank: number; score?: number | null; role: string }>();
    ranked.forEach((c, i) => m.set(c.key, { rank: i, score: c.score, role: c.role }));
    return m;
  }, [ranked]);

  // 관련도 표시 — recommend 점수는 확률이 아니라 상대값 → 최상위 대비 % 로 환산.
  const topScore = ranked[0]?.score ?? 0;
  const relPct = (s?: number | null): number | null =>
    typeof s === 'number' && topScore > 0 ? Math.round((s / topScore) * 100) : null;

  const topPicks = ranked.slice(0, autoCount);

  // 추가 목록 — 검색어 없으면 아직 미선택인 관련 후보(관련도순), 있으면 전체 풀 부분일치(관련 우선).
  const results = useMemo<AddRow[]>(() => {
    if (!experts) return [];
    const q = query.trim().toLowerCase();
    if (!q) {
      return ranked
        .filter((c) => !chosen[c.key])
        .slice(0, POOL_LIMIT)
        .map((c, i) => ({ key: c.key, name: c.name, tags: c.tags || [], score: c.score, role: c.role, rank: i }));
    }
    const out: AddRow[] = [];
    for (const a of experts.pool) {
      if (chosen[a.key]) continue;
      const hay = `${a.name} ${a.key} ${(a.tags || []).join(' ')}`.toLowerCase();
      if (!hay.includes(q)) continue;
      const c = candByKey.get(a.key);
      out.push({
        key: a.key,
        name: a.name,
        tags: a.tags || [],
        score: c?.score,
        role: c?.role,
        rank: c ? c.rank : Number.MAX_SAFE_INTEGER,
      });
    }
    out.sort((x, y) => x.rank - y.rank);
    return out.slice(0, POOL_LIMIT);
  }, [query, experts, chosen, candByKey, ranked]);

  const enough = chosenList.length >= MIN_EXPERTS;
  const poolCount = experts?.pool.length ?? 0;

  // ── 도구 선택 — 자동 파이프라인 도구는 항상 돌아가고, 여기서 고른 도구는 추가로 실호출된다.
  const toolRec = experts?.tools?.recommended ?? [];
  const toolPipeline = experts?.tools?.pipeline ?? [];
  const toolAll = useMemo(() => experts?.tools?.all ?? [], [experts]);
  const toolFull = toolSel.size >= MAX_TOOLS;
  const toggleTool = (name: string) =>
    setToolSel((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < MAX_TOOLS) next.add(name);
      return next;
    });
  const toolResults = useMemo(() => {
    const q = toolQuery.trim().toLowerCase();
    if (!q) return [];
    return toolAll
      .filter((t) => `${t.name} ${t.desc}`.toLowerCase().includes(q))
      .slice(0, TOOL_LIST_LIMIT);
  }, [toolQuery, toolAll]);

  return (
    <div className="cx-ep">
      <div className="cx-ep-head">
        <p className="cx-ep-kicker">심의 전문가 선정</p>
        <h2 className="cx-ep-topic">{topic}</h2>
        <p className="cx-ep-note">
          기본은 추천 전문가로 진행됩니다. 인원을 늘리거나, 아래에서 제외·직접 추가해 정합도를 높이세요.
        </p>
      </div>

      {loading ? (
        <div className="cx-ep-loading">전문가 선정 중…</div>
      ) : (
        <>
          {experts?.error && (
            <p className="cx-ep-warn">
              추천을 불러오지 못했습니다({experts.error}). 자동 선정으로 진행하거나 직접 골라주세요.
            </p>
          )}

          <section className="cx-ep-sec">
            <h3 className="cx-ep-sec-title">
              추천 전문가
              <span className="cx-ep-badge">관련도 상위 {topPicks.length}명</span>
              <span className="cx-ep-count">
                <label htmlFor="cx-ep-auto">자동 인원</label>
                <select
                  id="cx-ep-auto"
                  value={autoCount}
                  onChange={(e) => changeCount(Number(e.target.value))}
                >
                  {COUNT_OPTIONS.map((n) => (
                    <option key={n} value={n}>
                      {n}명{n === DEFAULT_COUNT ? ' (기본)' : ''}
                    </option>
                  ))}
                </select>
              </span>
            </h3>
            {topPicks.length ? (
              <ul className="cx-ep-list">
                {topPicks.map((r) => {
                  const pct = relPct(r.score);
                  return (
                    <li key={r.key} className="cx-ep-item">
                      <label className="cx-ep-check">
                        <input type="checkbox" checked={!!chosen[r.key]} onChange={() => toggle({ key: r.key, name: r.name, role: r.role })} />
                        <span className="cx-ep-body">
                          <span className="cx-ep-name">
                            {r.name}
                            {pct !== null && <span className="cx-ep-score">관련도 {pct}%</span>}
                          </span>
                          {r.role && <span className="cx-ep-role">{r.role}</span>}
                          {r.why && <span className="cx-ep-why">{r.why}</span>}
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="cx-ep-empty">추천 결과가 없습니다 — 아래에서 직접 골라주세요.</p>
            )}
          </section>

          <section className="cx-ep-sec">
            <h3 className="cx-ep-sec-title">
              직접 추가
              {poolCount > 0 && <span className="cx-ep-badge">{poolCount}명 풀</span>}
            </h3>
            <input
              className="cx-ep-search"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="분야·이름·키워드로 검색 (예: 열충격, warpage, battery)"
              aria-label="전문가 검색"
            />
            <p className="cx-ep-subtle">
              {full
                ? `최대 ${MAX_EXPERTS}명까지 선정됩니다 — 더 넣으려면 먼저 제외하세요.`
                : query.trim()
                  ? '검색 결과 — 질문 관련 전문가가 위로 정렬됩니다.'
                  : '질문 관련 전문가(관련도순). 검색하면 전체 풀에서 찾습니다.'}
            </p>
            <ul className="cx-ep-results">
              {results.length === 0 ? (
                <li className="cx-ep-empty">{query.trim() ? '일치하는 전문가가 없습니다.' : '추가할 관련 후보가 없습니다.'}</li>
              ) : (
                results.map((a) => {
                  const pct = relPct(a.score);
                  return (
                    <li key={a.key} className="cx-ep-result">
                      <button type="button" className="cx-ep-add" onClick={() => add(a)} disabled={full}>
                        <span className="cx-ep-name">{a.name}</span>
                        {pct !== null && <span className="cx-ep-score">관련도 {pct}%</span>}
                        {a.tags?.length ? <span className="cx-ep-tags">{a.tags.slice(0, 4).join(' · ')}</span> : null}
                        <span className="cx-ep-plus" aria-hidden="true">＋</span>
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </section>

          {(toolRec.length > 0 || toolAll.length > 0) && (
            <section className="cx-ep-sec">
              <h3 className="cx-ep-sec-title">
                사용 도구
                <span className="cx-ep-badge">선택 {toolSel.size}/{MAX_TOOLS}</span>
              </h3>
              {toolPipeline.length > 0 && (
                <p className="cx-ep-subtle">
                  자동 사용(파이프라인): {toolPipeline.join(' · ')} — 아래에서 고른 도구는 추가로 실제
                  호출돼 정량 근거로 주입됩니다.
                </p>
              )}
              {toolRec.length > 0 && (
                <ul className="cx-ep-results">
                  {toolRec.slice(0, 8).map((t) => (
                    <li key={t.name}>
                      <label className="cx-ep-tool">
                        <input
                          type="checkbox"
                          checked={toolSel.has(t.name)}
                          onChange={() => toggleTool(t.name)}
                          disabled={!toolSel.has(t.name) && toolFull}
                        />
                        <span className="cx-ep-name">{t.name}</span>
                        <span className="cx-ep-tags">{t.desc}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
              <input
                className="cx-ep-search"
                type="text"
                value={toolQuery}
                onChange={(e) => setToolQuery(e.target.value)}
                placeholder="도구 검색 (예: predict_sed, warpage, voc)"
                aria-label="도구 검색"
              />
              {toolQuery.trim() && (
                <ul className="cx-ep-results">
                  {toolResults.length === 0 ? (
                    <li className="cx-ep-empty">일치하는 도구가 없습니다.</li>
                  ) : (
                    toolResults.map((t) => (
                      <li key={t.name}>
                        <label className="cx-ep-tool">
                          <input
                            type="checkbox"
                            checked={toolSel.has(t.name)}
                            onChange={() => toggleTool(t.name)}
                            disabled={!toolSel.has(t.name) && toolFull}
                          />
                          <span className="cx-ep-name">{t.name}</span>
                          <span className="cx-ep-tags">{t.desc}</span>
                        </label>
                      </li>
                    ))
                  )}
                </ul>
              )}
              {toolSel.size > 0 && (
                <div className="cx-ep-chips">
                  {[...toolSel].map((n) => (
                    <span key={n} className="cx-ep-chip">
                      🔧 {n}
                      <button
                        type="button"
                        className="cx-ep-chip-x"
                        onClick={() => toggleTool(n)}
                        aria-label={`${n} 제외`}
                        title="제외"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </section>
          )}

          <section className="cx-ep-sec">
            <h3 className="cx-ep-sec-title">
              선정됨
              <span className="cx-ep-badge">
                {chosenList.length}/{MAX_EXPERTS}명
              </span>
            </h3>
            <div className="cx-ep-chips">
              {chosenList.length === 0 ? (
                <span className="cx-ep-empty">선정된 전문가가 없습니다.</span>
              ) : (
                chosenList.map((p) => (
                  <span key={p.key} className="cx-ep-chip">
                    {p.name}
                    <button
                      type="button"
                      className="cx-ep-chip-x"
                      onClick={() => toggle(p)}
                      aria-label={`${p.name} 제외`}
                      title="제외"
                    >
                      ×
                    </button>
                  </span>
                ))
              )}
            </div>
          </section>

          <div className="cx-ep-actions">
            <button type="button" className="cx-ep-cancel" onClick={onCancel}>
              취소
            </button>
            <button
              type="button"
              className="cx-ep-start"
              disabled={!enough}
              onClick={() => onConfirm(chosenList, [...toolSel])}
              title={enough ? '선정한 전문가·도구로 심의를 시작합니다' : `전문가를 ${MIN_EXPERTS}명 이상 선정하세요`}
            >
              심의 시작 ({chosenList.length}명{toolSel.size > 0 ? ` · 도구 ${toolSel.size}` : ''})
            </button>
          </div>
          {!enough && <p className="cx-ep-hint">전문가를 {MIN_EXPERTS}명 이상 선정해야 심의를 시작할 수 있습니다.</p>}
        </>
      )}
    </div>
  );
}
