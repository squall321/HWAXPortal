// 심의 전 전문가 확인·수동추가 패널 — 추천(기본 선택)을 보여주고, 질문 관련도순 후보/검색으로 추가
import { useEffect, useMemo, useRef, useState } from 'react';
import type { ExpertsResponse } from '../../api/chat.api';

export interface Persona {
  key: string;
  name: string;
  role: string;
}

interface ExpertPickerProps {
  topic: string;
  loading: boolean;
  experts: ExpertsResponse | null;
  /** 선택 전문가로 심의 시작. */
  onConfirm: (personas: Persona[]) => void;
  onCancel: () => void;
}

const MIN_EXPERTS = 2; // 서버 심의는 전문가 2명 이상 필요
const POOL_LIMIT = 30; // 결과 표시 상한

interface AddRow {
  key: string;
  name: string;
  tags: string[];
  score?: number | null;
  role?: string;
  rank: number;
}

export function ExpertPicker({ topic, loading, experts, onConfirm, onCancel }: ExpertPickerProps) {
  // 선택 집합 — key → persona. 추천이 도착하면 1회 시딩(기본은 추천 그대로).
  const [chosen, setChosen] = useState<Record<string, Persona>>({});
  const [query, setQuery] = useState('');
  const seededRef = useRef(false);

  useEffect(() => {
    if (seededRef.current || !experts) return;
    const init: Record<string, Persona> = {};
    for (const r of experts.recommended) init[r.key] = { key: r.key, name: r.name, role: r.role };
    setChosen(init);
    seededRef.current = true;
  }, [experts]);

  const toggle = (p: Persona) =>
    setChosen((prev) => {
      const next = { ...prev };
      if (next[p.key]) delete next[p.key];
      else next[p.key] = p;
      return next;
    });

  const add = (r: { key: string; name: string; role?: string }) =>
    setChosen((prev) => ({ ...prev, [r.key]: { key: r.key, name: r.name, role: r.role || '' } }));

  const chosenList = useMemo(() => Object.values(chosen), [chosen]);

  // 후보(질문 연관도순) 인덱스 — 검색 결과를 관련도 우선으로 정렬하는 데 사용.
  const candByKey = useMemo(() => {
    const m = new Map<string, { rank: number; score?: number | null; role: string }>();
    (experts?.candidates || []).forEach((c, i) => m.set(c.key, { rank: i, score: c.score, role: c.role }));
    return m;
  }, [experts]);

  // 관련도 표시 — recommend 점수는 0~1 확률이 아니라 상대값이라, 최상위 대비 % 로 환산해 보여준다.
  const topScore = experts?.candidates?.[0]?.score ?? 0;
  const relPct = (s?: number | null): number | null =>
    typeof s === 'number' && topScore > 0 ? Math.round((s / topScore) * 100) : null;

  // 추가 목록 — 검색어 없으면 질문 관련 후보(관련도순), 있으면 전체 풀 부분일치(관련 후보 우선).
  const results = useMemo<AddRow[]>(() => {
    if (!experts) return [];
    const q = query.trim().toLowerCase();
    if (!q) {
      return (experts.candidates || [])
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
  }, [query, experts, chosen, candByKey]);

  const enough = chosenList.length >= MIN_EXPERTS;
  const poolCount = experts?.pool.length ?? 0;

  return (
    <div className="cx-ep">
      <div className="cx-ep-head">
        <p className="cx-ep-kicker">심의 전문가 선정</p>
        <h2 className="cx-ep-topic">{topic}</h2>
        <p className="cx-ep-note">
          기본은 추천 전문가로 진행됩니다. 원하면 아래에서 제외하거나 직접 추가해 정합도를 높이세요.
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
              {experts?.recommended?.length ? <span className="cx-ep-badge">{experts.recommended.length}</span> : null}
            </h3>
            {experts?.recommended?.length ? (
              <ul className="cx-ep-list">
                {experts.recommended.map((r) => {
                  const pct = relPct(r.score);
                  return (
                    <li key={r.key} className="cx-ep-item">
                      <label className="cx-ep-check">
                        <input type="checkbox" checked={!!chosen[r.key]} onChange={() => toggle(r)} />
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
              {query.trim()
                ? '검색 결과 — 질문 관련 전문가가 위로 정렬됩니다.'
                : '질문 관련 전문가(관련도순). 검색하면 전체 풀에서 찾습니다.'}
            </p>
            <ul className="cx-ep-results">
              {results.length === 0 ? (
                <li className="cx-ep-empty">{query.trim() ? '일치하는 전문가가 없습니다.' : '관련 후보가 없습니다.'}</li>
              ) : (
                results.map((a) => {
                  const pct = relPct(a.score);
                  return (
                    <li key={a.key} className="cx-ep-result">
                      <button type="button" className="cx-ep-add" onClick={() => add(a)}>
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

          <section className="cx-ep-sec">
            <h3 className="cx-ep-sec-title">
              선정됨
              <span className="cx-ep-badge">{chosenList.length}명</span>
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
              onClick={() => onConfirm(chosenList)}
              title={enough ? '선정한 전문가로 심의를 시작합니다' : `전문가를 ${MIN_EXPERTS}명 이상 선정하세요`}
            >
              심의 시작 ({chosenList.length}명)
            </button>
          </div>
          {!enough && <p className="cx-ep-hint">전문가를 {MIN_EXPERTS}명 이상 선정해야 심의를 시작할 수 있습니다.</p>}
        </>
      )}
    </div>
  );
}
