// 심의 전 되묻기 — 메커니즘 분석에 필요한 최소 정보가 비었으면 몇 가지를 한 번에 묻고, 답을 화두에 붙인다
import { useEffect, useState } from 'react';
import { fetchDeliberateClarify, type ClarifyResult, type HistoryMessage } from '../../api/chat.api';
import { augmentTopic } from './clarify';

/** 되묻기는 **선택**이다 — 건너뛰어도 심의는 그대로 간다. 서버가 실패하면 아무것도 안 그린다. */
export function ClarifyPanel({
  topic,
  job,
  history,
  onApply,
}: {
  topic: string;
  job: string;
  history?: HistoryMessage[];
  /** 보강된 화두 — 부모가 전문가를 다시 찾는다. */
  onApply: (topic: string) => void;
}) {
  const [res, setRes] = useState<ClarifyResult | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [skipped, setSkipped] = useState(false);

  // 화두가 바뀌면(보강 적용 포함) 다시 스캔한다 — 방금 답한 칸은 이제 '있음'이라 안 묻는다.
  // 그래서 몇 번이고 모자란 것만 되묻게 된다. 입력 중 폭주를 막으려 잠깐 기다린다.
  useEffect(() => {
    if (!topic.trim()) return;
    const ctrl = new AbortController();
    const h = setTimeout(() => {
      void fetchDeliberateClarify(topic, job, history, ctrl.signal).then((r) => {
        if (ctrl.signal.aborted) return;
        setRes(r);
        setAnswers({});
      });
    }, 600);
    return () => {
      clearTimeout(h);
      ctrl.abort();
    };
  }, [topic, job, history]);

  if (skipped || !res || !res.applicable || !res.ask.length) return null;

  const asked = res.slots.filter((s) => res.ask.includes(s.key));
  const known = res.slots.filter((s) => s.present && s.value);
  const filled = asked.filter((s) => (answers[s.key] || '').trim());

  return (
    <div className="cq">
      <div className="cq-head">
        <strong>질문 보강</strong>
        <span className="cq-sub">메커니즘 분석에 필요한 정보 {asked.length}가지가 비어 있습니다 — 선택</span>
        <button type="button" className="cq-skip" onClick={() => setSkipped(true)}>
          건너뛰기
        </button>
      </div>
      {known.length > 0 && (
        <p className="cq-known">
          화두에서 읽은 것 —{' '}
          {known.map((s) => (
            <span key={s.key} className="cq-known-item">
              <b>{s.label}</b> {s.value}
            </span>
          ))}
        </p>
      )}
      <ul className="cq-list">
        {asked.map((s) => (
          <li key={s.key} className="cq-item">
            <label className="cq-q" htmlFor={`cq-${s.key}`}>
              <b>{s.label}</b> {s.question}
            </label>
            <input
              id={`cq-${s.key}`}
              value={answers[s.key] || ''}
              onChange={(e) => setAnswers((a) => ({ ...a, [s.key]: e.target.value.slice(0, 300) }))}
              // 후보가 하나뿐이면 고르게 하지 않는다 — 버튼 하나짜리 선택은 확인이 아니라 방해다
              // (docs/upload/context-notes.md D-7). 입력칸의 예시로만 보인다.
              placeholder={s.options.length === 1 ? `예: ${s.options[0]}` : '모르면 비워 두세요'}
            />
            {s.options.length > 1 && (
              <span className="cq-opts">
                {s.options.map((o) => (
                  <button
                    key={o}
                    type="button"
                    className="cq-opt"
                    onClick={() =>
                      setAnswers((a) => {
                        const cur = (a[s.key] || '').trim();
                        return { ...a, [s.key]: cur && !cur.includes(o) ? `${cur}, ${o}` : cur || o };
                      })
                    }
                  >
                    {o}
                  </button>
                ))}
              </span>
            )}
          </li>
        ))}
      </ul>
      <div className="cq-foot">
        <span className="cq-hint">답은 질문에 붙어 전문가 추천과 매 라운드에 함께 실립니다.</span>
        <button
          type="button"
          className="cq-apply"
          disabled={!filled.length}
          onClick={() => onApply(augmentTopic(topic, filled.map((s) => ({ label: s.label, value: answers[s.key] }))))}
        >
          보강해서 다시 찾기 ({filled.length})
        </button>
      </div>
    </div>
  );
}
