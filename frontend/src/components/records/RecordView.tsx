// 상호작용 기록 한 줄의 표와 원문 보기 — 내 기록 · 분석가 화면이 같이 쓴다(docs/interaction-data contract §6)
import { SURFACE_LABEL, type InteractionFull, type InteractionRow } from '../../api/interactions.api';

function when(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export function RecordTable({
  rows,
  showActor,
  onOpen,
  openId,
}: {
  rows: InteractionRow[];
  showActor: boolean;
  onOpen: (id: string) => void;
  openId: string | null;
}) {
  return (
    <div className="adm-table-wrap">
      <table className="adm-table">
        <thead>
          <tr>
            <th>시각</th>
            {showActor && <th>사람</th>}
            <th>어디서</th>
            <th>도구 · 앱</th>
            <th>내용</th>
            <th>결과</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className={openId === r.id ? 'is-open' : undefined}>
              <td className="adm-nowrap">{when(r.ts)}</td>
              {showActor && <td>{r.actor ?? '—'}</td>}
              <td>
                {SURFACE_LABEL[r.surface] ?? r.surface}
                {r.via && <span className="adm-muted"> · {r.via}</span>}
              </td>
              <td>{[r.app, r.tool].filter(Boolean).join(' · ') || '—'}</td>
              <td className="adm-muted-cell">
                <button type="button" className="adm-linkbtn" onClick={() => onOpen(r.id)} aria-label="원문 보기">
                  {(r.input_preview || r.output_preview || '(빈 글)').slice(0, 140)}
                </button>
              </td>
              <td>{r.status ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Block({ label, text }: { label: string; text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="rec-block">
      <h4>{label}</h4>
      <pre>{text}</pre>
    </div>
  );
}

export function RecordDetail({ rec, onClose }: { rec: InteractionFull; onClose: () => void }) {
  const meta = rec.meta ? JSON.stringify(rec.meta, null, 2) : null;
  return (
    <div className="adm-sec rec-detail">
      <h3>
        {SURFACE_LABEL[rec.surface] ?? rec.surface} — {when(rec.ts)}
        <button type="button" className="btn-secondary rec-close" onClick={onClose}>
          닫기
        </button>
      </h3>
      <p className="adm-hint">
        {[
          rec.actor && `사람 ${rec.actor}`,
          rec.client && `클라이언트 ${rec.client}`,
          rec.model && `모델 ${rec.model}`,
          rec.ms != null && `${rec.ms}ms`,
          rec.output_chars != null && `결과 ${rec.output_chars.toLocaleString()}자`,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {rec.shared && (
        <div className="rec-block">
          <h4>
            공유한 대화 — {rec.shared.title || rec.shared.session_id} ({rec.shared.messages.length}개
            {rec.shared.kind === 'transcript' ? ' · 기록 파일' : ''})
          </h4>
          <ol className="rec-msgs">
            {rec.shared.messages.map((m, i) => (
              <li key={i} className={`rec-msg is-${m.role}`}>
                <b>{m.role === 'user' ? '사람' : m.role === 'assistant' ? '어시스턴트' : '도구'}</b>
                <pre>{m.content}</pre>
              </li>
            ))}
          </ol>
        </div>
      )}
      <Block label="보낸 것(입력)" text={rec.input} />
      {!rec.shared && <Block label="받은 것(결과)" text={rec.output} />}
      {meta && (
        <details className="rec-block">
          <summary>메타</summary>
          <pre>{meta}</pre>
        </details>
      )}
    </div>
  );
}
