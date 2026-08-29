// 심의 브리프 — 챗에서 넘길 질문·좌석·템플릿을 AI가 제안하고 사용자가 확정하는 모달(핸드오프 P3)
import { useEffect, useMemo, useState } from 'react';
import { fetchDeliberateExperts, type ExpertsResponse } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import type { Conversation } from '../../types/chat';
import { conversationEvidence } from './handoff';

// 결정문 형식(chairTemplate) — 백엔드 _CHAIR_ITEMS 키와 맞춘다.
const TEMPLATES = [
  { id: 'default', label: '일반 의사결정문' },
  { id: 'mechanism', label: '메커니즘 규명' },
  { id: 'sim-plan', label: '해석 계획서' },
  { id: 'test-plan', label: '시험 계획서' },
];
const DEFAULT_SEATS = 6; // 추천 좌석 기본 선택 수(심의가 스파인 좌석은 자동 추가)

export function HandoffBrief({ conv, onClose }: { conv: Conversation; onClose: () => void }) {
  const { startHandoff, streaming } = useChat();
  const derived = useMemo(() => {
    const firstUser = conv.messages.find((m) => m.role === 'user');
    return (firstUser?.text ?? '').replace(/^\/(심의|deliberate|토의)\s*/, '').trim();
  }, [conv]);
  const evidence = useMemo(() => conversationEvidence(conv), [conv]);

  const [topic, setTopic] = useState(derived);
  const [template, setTemplate] = useState('default');
  const [experts, setExperts] = useState<ExpertsResponse | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  // 화두로 추천 좌석 발굴(디바운스 + 취소) — AI 제안, 사용자 확정. 상위 N석 기본 선택.
  useEffect(() => {
    const t = topic.trim();
    if (!t) {
      setExperts(null);
      return;
    }
    setLoading(true);
    const ctrl = new AbortController();
    const h = setTimeout(() => {
      void fetchDeliberateExperts(t, ctrl.signal)
        .then((r) => {
          setExperts(r);
          setChecked(new Set((r.recommended ?? []).slice(0, DEFAULT_SEATS).map((e) => e.key)));
        })
        .finally(() => setLoading(false));
    }, 500);
    return () => {
      clearTimeout(h);
      ctrl.abort();
    };
  }, [topic]);

  const rec = experts?.recommended ?? [];
  const toggle = (k: string) =>
    setChecked((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });

  const confirm = () => {
    const t = topic.trim();
    if (!t || streaming) return;
    const personas = rec.filter((e) => checked.has(e.key)).map((e) => ({ key: e.key, role: e.role }));
    // P4 재활용 도구(일반화) — 챗이 부른 도구가 속한 앱을 레지스트리 그룹에서 도출해 free-query 범위로
    // 넘긴다(앱 바운드, 하드코딩 0). 좌석이 같은 앱을 이어 조회해 더 파낼 수 있다. ≤3(delib_opts.apps 상한).
    const usedTools = new Set(evidence.map((e) => e.tool).filter(Boolean));
    const toolAll = experts?.tools?.all ?? [];
    const apps = [
      ...new Set(toolAll.filter((x) => usedTools.has(x.name)).map((x) => x.group).filter(Boolean)),
    ].slice(0, 3) as string[];
    startHandoff({ topic: t, personas, chairTemplate: template, ...(apps.length ? { apps } : {}) });
    onClose();
  };

  return (
    <div className="cx-brief-overlay" role="dialog" aria-modal="true" aria-label="심의 브리프" onClick={onClose}>
      <div className="cx-brief" onClick={(e) => e.stopPropagation()}>
        <div className="cx-brief-head">
          <strong>심의 브리프</strong>
          <span className="cx-brief-sub">AI 제안을 확인·수정하고 심의를 시작합니다</span>
          <button type="button" className="cx-brief-x" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>

        <label className="cx-brief-field">
          <span>질문 (편집 가능)</span>
          <textarea value={topic} onChange={(e) => setTopic(e.target.value)} rows={2} />
        </label>

        <label className="cx-brief-field">
          <span>결정문 형식</span>
          <select value={template} onChange={(e) => setTemplate(e.target.value)}>
            {TEMPLATES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        <div className="cx-brief-field">
          <span>
            좌석 제안 {loading ? '(발굴 중…)' : `— ${checked.size}석 선택 · 심의가 스파인 좌석 자동 추가`}
          </span>
          <div className="cx-brief-seats">
            {rec.map((e) => (
              <label key={e.key} className="cx-brief-seat">
                <input type="checkbox" checked={checked.has(e.key)} onChange={() => toggle(e.key)} />
                <span className="cx-brief-seat-name">{e.name}</span>
                {e.why && <span className="cx-brief-seat-why">{e.why}</span>}
              </label>
            ))}
            {!loading && rec.length === 0 && (
              <span className="cx-brief-empty">추천 좌석 없음 — 심의가 자동 발굴합니다</span>
            )}
          </div>
        </div>

        <div className="cx-brief-field">
          <span>원천 근거 {evidence.length}건 — 검증 대상이지 결론이 아닙니다</span>
          <div className="cx-brief-ev">
            {evidence.map((ev, i) => (
              <div key={i} className="cx-brief-ev-item">
                <span className="cx-brief-ev-src">
                  {ev.source}
                  {ev.tool ? ` · ${ev.tool}` : ''}
                </span>
                <span className="cx-brief-ev-res">{ev.result.slice(0, 200)}</span>
              </div>
            ))}
            {evidence.length === 0 && <span className="cx-brief-empty">추출된 원천 근거 없음</span>}
          </div>
        </div>

        <div className="cx-brief-actions">
          <button type="button" className="cx-brief-cancel" onClick={onClose}>
            취소
          </button>
          <button type="button" className="cx-brief-go" onClick={confirm} disabled={!topic.trim() || streaming}>
            심의 시작 · {checked.size}석 · 근거 {evidence.length}건
          </button>
        </div>
      </div>
    </div>
  );
}
