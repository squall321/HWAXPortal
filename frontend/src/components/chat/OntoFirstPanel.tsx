// 심의 전 '온톨로지 먼저 보기' — 확인된 주제 과제를 정본 허브에서 풀고 한 걸음 이웃을 사람이 골라 원천 근거로 넣는다(docs/ontology-first M4)
import { useEffect, useRef, useState } from 'react';
import { fetchOntoPreview, type OntoPreview } from '../../api/chat.api';
import { ontoEvidence, type OntoChoice } from './ontoEvidence';

function stateText(r: OntoPreview): string {
  const why = r.why ?? '';
  switch (r.state) {
    case 'unavailable':
      return `이 박스에서 부를 수 없습니다 — ${why}`;
    case 'error':
      return `정본 허브를 부르지 못했습니다 — '없음' 이 아니라 '못 물어봄' 입니다(${why}).`;
    default:
      return why;
  }
}

/** spTask — 심의 주제(M1)의 과제 key(비면 버튼만 보이고 꺼져 있다). chair — 그 심의의 의장 틀(서버가 리스크 심사 계열을 거절한다).
 *  리스크 심사 · 봉인 · 기준일 심의에서는 부모가 이 패널을 그리지 않는다. */
export function OntoFirstPanel({ spTask, chair, onChange }: { spTask: string; chair?: string; onChange: (c: OntoChoice) => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<OntoPreview | null>(null);
  const [anchor, setAnchor] = useState(false);
  // 배열로 둔다 — 고른 차례가 아니라 화면 차례로 근거에 싣지만(ontoEvidence), 집합의 키 정렬에 기대지 않는다(VOC 먼저 보기와 같다).
  const [picked, setPicked] = useState<string[]>([]);
  const ctrlRef = useRef<AbortController | null>(null);
  const key = spTask.trim();

  // 부모에게는 결과만 알린다(부모가 evidence 로 옮긴다).
  useEffect(() => {
    onChange({ evidence: ontoEvidence(res, anchor, picked), rows: picked.length, anchor });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [res, anchor, picked]);

  useEffect(() => () => ctrlRef.current?.abort(), []);

  const load = () => {
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setLoading(true);
    void fetchOntoPreview(key, chair, ctrl.signal).then((r) => {
      if (ctrl.signal.aborted) return;
      setRes(r);
      setAnchor(false);
      setPicked([]);
      setLoading(false);
    });
  };

  // 이웃 행을 고르면 주제 과제 칸도 보이게 함께 고른다 — 이웃 근거의 인자(object_id — 허브 id) · 머리(「key」) · 관계 글('이 과제')이 주제 과제를
  // 가리켜, 고르지 않은 주제 과제의 key · id 가 말없이 나가면 안 된다(반대 검토 11-02 — docs/ontology-first OF-29). 주제 과제를 빼면 고른 이웃 행도 뺀다.
  const toggle = (id: string) => {
    const on = !picked.includes(id);
    setPicked((prev) => (on ? (prev.includes(id) ? prev : [...prev, id]) : prev.filter((x) => x !== id)));
    if (on) setAnchor(true);
  };
  const toggleAnchor = () => {
    if (anchor) setPicked([]);
    setAnchor(!anchor);
  };

  if (!open) {
    return (
      <button
        type="button"
        className="vf-open"
        onClick={() => {
          setOpen(true);
          if (!res) load();
        }}
        disabled={!key}
        title={key ? undefined : '심의 주제에서 과제를 고르면 켜집니다'}
      >
        {key
          ? `온톨로지 먼저 보기 — 주제 과제 「${key}」의 한 걸음 이웃을 정본 허브에서 골라 넣습니다`
          : '온톨로지 먼저 보기 — 심의 주제에서 과제를 고르면 켜집니다'}
      </button>
    );
  }

  const rows = res?.rows ?? [];
  return (
    <div className="vf">
      <div className="vf-head">
        <strong>온톨로지 먼저 보기</strong>
        <span className="vf-sub">고른 행만 원천 근거로 들어갑니다 · 호출 하나에 한 항목</span>
        <button type="button" className="vf-x" onClick={() => setOpen(false)} aria-label="온톨로지 먼저 보기 접기">
          접기
        </button>
      </div>

      {loading && <p className="vf-empty">주제 과제를 확인하고 정본 허브를 조회하는 중…</p>}
      {!loading && res && (
        <>
          {res.state !== 'ok' && <p className="vf-warn">{stateText(res)}</p>}
          {(res.notes ?? []).map((n) => (
            <p key={n} className="vf-hint">
              {n}
            </p>
          ))}
          {(res.state === 'candidates' || res.state === 'mismatch') && (res.candidates ?? []).length > 0 && (
            <ul className="vf-list" aria-label="정본 허브 후보(고를 수 없다)">
              {(res.candidates ?? []).map((c) => (
                <li key={c.id} className="vf-item is-off">
                  <span className="vf-meta">
                    <span className="vf-kwtag">{c.type || '후보'}</span>
                    {[c.key ?? 'key 없음', c.label, c.matched_by && `${c.matched_by}로 맞음`, c.status].filter(Boolean).join(' · ')}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {res.state === 'ok' && res.anchor && (
            <ul className="vf-list">
              <li className={`vf-item${anchor ? ' is-on' : ''}`}>
                <label className="vf-check">
                  <input type="checkbox" checked={anchor} onChange={toggleAnchor} />
                  <span className="vf-meta">
                    <span className="vf-kwtag">주제 과제</span>
                    {res.anchor.line}
                  </span>
                </label>
              </li>
              {rows.map((r) => {
                const on = picked.includes(r.id);
                return (
                  <li key={r.id} className={`vf-item${on ? ' is-on' : ''}`}>
                    <label className="vf-check">
                      <input type="checkbox" checked={on} onChange={() => toggle(r.id)} />
                      <span className="vf-meta">
                        <span className="vf-kwtag">{r.type_label}</span>
                        {`${r.key ?? 'key 없음'} · ${r.label}`}
                      </span>
                    </label>
                    <p className="vf-text">{r.rel}</p>
                  </li>
                );
              })}
            </ul>
          )}
          {res.state === 'ok' && rows.length > 0 && (
            <p className="vf-hint">
              이웃 행을 고르면 주제 과제 칸도 함께 골라집니다 — 관계 글의 &apos;이 과제&apos; 가 주제 과제라 그 key · 허브 id 가 근거에 함께 실립니다.
              주제 과제를 빼면 고른 이웃 행도 빠집니다.
            </p>
          )}
          {res.state === 'ok' && rows.length === 0 && <p className="vf-empty">어휘표 타입의 이웃이 없습니다 — 주제 과제 하나만 고를 수 있습니다.</p>}
          {res.state === 'ok' && (res.total ?? 0) > (res.shown ?? 0) && (
            <p className="vf-hint">
              전체 {res.total}행 가운데 {res.shown}행만 보입니다(글자 상한) — 나머지는 근거로 넣을 수 없습니다.
            </p>
          )}
          {res.state === 'ok' && res.hub_truncated && <p className="vf-hint">허브가 상한으로 답을 잘랐습니다 — 이웃이 이게 전부가 아닙니다.</p>}
          {res.note && <p className="vf-hint">{res.note}</p>}
          {res.state !== 'ok' && (
            <div className="vf-kw">
              <button type="button" onClick={load} disabled={loading}>
                다시 보기
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
