// 심의 전 'VOC 먼저 보기' — 화두로 고객 불만을 검색해 사람이 골라 근거로 넣고, 화두를 보강한다
import { useEffect, useRef, useState } from 'react';
import { fetchDeliberateVoc, type VocItem, type VocPreview } from '../../api/chat.api';
import { vocNoteDraft } from './vocEvidence';

/** 한 번에 넣을 수 있는 VOC 수 — 원천 근거 칸(12)을 대화 근거와 나눠 쓴다. */
export const MAX_VOC_PICKS = 6;

export interface VocChoice {
  /** 사람이 VOC 검색을 한 번이라도 돌렸다 — 그러면 엔진 자동 환기를 끈다(voc:'off'). */
  used: boolean;
  picked: VocItem[];
  note: string;
}

export function VocFirstPanel({ topic, onChange }: { topic: string; onChange: (c: VocChoice) => void }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<VocPreview | null>(null);
  const [kwText, setKwText] = useState('');
  // 배열로 둔다 — Record 로 두면 숫자형 id 키를 JS 가 오름차순으로 정렬해, 고른 순서가 아니라
  // id 순으로 근거에 실린다(실측으로 잡았다).
  const [picked, setPicked] = useState<VocItem[]>([]);
  const [note, setNote] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const ctrlRef = useRef<AbortController | null>(null);

  // '직접 봤다' 는 검색이 실제로 성공했을 때만이다. 조회가 실패(degraded)했는데 자동 환기까지
  // 끄면, 미리보기 순간 SignalForge 가 잠깐 죽었다는 이유로 심의의 VOC 가 통째로 사라진다.
  const used = res !== null && !res.unavailable && !res.error && !res.degraded;
  const pickedList = picked;
  const isPicked = (v: VocItem) => picked.some((x) => String(x.id) === String(v.id));

  // 부모에게는 결과만 알린다(부모가 evidence·human_note·voc 로 옮긴다).
  useEffect(() => {
    onChange({ used, picked: pickedList, note: note.trim() });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [used, picked, note]);

  useEffect(() => () => ctrlRef.current?.abort(), []);

  const search = (keywords?: string[]) => {
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setLoading(true);
    void fetchDeliberateVoc(topic, keywords, ctrl.signal).then((r) => {
      if (ctrl.signal.aborted) return;
      setRes(r);
      setKwText((r.keywords ?? []).join(', '));
      setLoading(false);
    });
  };

  const toggle = (v: VocItem) =>
    setPicked((prev) =>
      prev.some((x) => String(x.id) === String(v.id))
        ? prev.filter((x) => String(x.id) !== String(v.id))
        : prev.length < MAX_VOC_PICKS
          ? [...prev, v]
          : prev,
    );

  if (!open) {
    return (
      <button
        type="button"
        className="vf-open"
        onClick={() => {
          setOpen(true);
          if (!res) search();
        }}
        disabled={!topic.trim()}
      >
        📡 VOC 먼저 보기 — 화두로 고객 불만을 찾아 골라 넣습니다
      </button>
    );
  }

  const full = pickedList.length >= MAX_VOC_PICKS;
  return (
    <div className="vf">
      <div className="vf-head">
        <strong>VOC 먼저 보기</strong>
        <span className="vf-sub">고른 것만 원천 근거로 들어갑니다 · 최대 {MAX_VOC_PICKS}건</span>
        <button type="button" className="vf-x" onClick={() => setOpen(false)} aria-label="VOC 접기">
          접기
        </button>
      </div>

      <div className="vf-kw">
        <input
          value={kwText}
          onChange={(e) => setKwText(e.target.value)}
          placeholder="영어 검색어, 쉼표로 (예: hinge crack, screen crease)"
          aria-label="VOC 검색어"
          onKeyDown={(e) => {
            if (e.key === 'Enter') search(kwText.split(',').map((s) => s.trim()).filter(Boolean));
          }}
        />
        <button
          type="button"
          onClick={() => search(kwText.split(',').map((s) => s.trim()).filter(Boolean))}
          disabled={loading}
        >
          다시 검색
        </button>
      </div>
      <p className="vf-hint">VOC 본문은 대부분 영어라 검색어도 영어가 잘 걸립니다. 화두에서 자동으로 뽑은 뒤 고칠 수 있습니다.</p>

      {loading && <p className="vf-empty">SignalForge 검색 중…</p>}
      {!loading && res && (
        <>
          {res.unavailable && <p className="vf-warn">{res.note || 'VOC 도구를 쓸 수 없습니다(권한 또는 연결).'}</p>}
          {res.error && <p className="vf-warn">VOC 를 불러오지 못했습니다({res.error}).</p>}
          {res.degraded && <p className="vf-warn">SignalForge 조회가 실패했습니다 — '없음'이 아니라 '못 물어봄'입니다.</p>}
          {res.partial && <p className="vf-warn">일부 검색어는 조회가 실패했습니다 — 결과가 덜 나왔을 수 있습니다.</p>}
          {!res.unavailable && !res.error && !res.degraded && res.items.length === 0 && (
            <p className="vf-empty">일치하는 VOC 가 없습니다 — 검색어를 바꿔 보세요.</p>
          )}
          {res.note && !res.unavailable && <p className="vf-hint">{res.note}</p>}
          {res.items.length > 0 && (
            <ul className="vf-list">
              {res.items.map((v) => {
                const k = String(v.id);
                const on = isPicked(v);
                return (
                  <li key={k} className={`vf-item${on ? ' is-on' : ''}${!on && full ? ' is-off' : ''}`}>
                    <label className="vf-check">
                      <input type="checkbox" checked={on} disabled={!on && full} onChange={() => toggle(v)} />
                      <span className="vf-meta">
                        <span className="vf-kwtag">{v.keyword}</span>
                        {[v.product, v.platform, v.country, v.date].filter(Boolean).join(' · ')}
                        {typeof v.score === 'number' && <span className="vf-score">감성 {v.score.toFixed(2)}</span>}
                      </span>
                    </label>
                    <p className={`vf-text${expanded === k ? ' is-open' : ''}`}>{v.text}</p>
                    <span className="vf-actions">
                      <button type="button" onClick={() => setExpanded(expanded === k ? null : k)}>
                        {expanded === k ? '접기' : '전문'}
                      </button>
                      {v.url && (
                        <a href={v.url} target="_blank" rel="noreferrer noopener">
                          원문 ↗
                        </a>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      <div className="vf-note">
        <div className="vf-note-head">
          <span>화두 보강 — 패널이 매 라운드 정면으로 다룹니다(선택)</span>
          <button type="button" disabled={!pickedList.length} onClick={() => setNote(vocNoteDraft(pickedList))}>
            고른 VOC 로 초안
          </button>
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value.slice(0, 1800))}
          rows={3}
          placeholder="예: 폴드6 이후 모델에서 힌지 주름 불만이 늘었다 — 설계 변경과 연관이 있는지 따져라."
        />
      </div>
      {used && (
        <p className="vf-hint">
          VOC 를 여기서 직접 봤으므로 심의의 자동 VOC 환기는 끕니다 — 고른 {pickedList.length}건만 근거로 들어갑니다.
        </p>
      )}
    </div>
  );
}
