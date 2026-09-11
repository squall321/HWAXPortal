// 이어하기 좌석 조정 — 한 회차를 돈 뒤 명단을 사람이 고른다(빼기 + 조직도로 더하기)
import { useState } from 'react';
import { SeatBrowser } from './SeatBrowser';
import { colorOf, initialOf, shortName } from './personaColor';
import { usePersonaPool } from './usePersonaPool';

export type Seat = { key: string; role: string };

// 좌석 상한 — 엔진 MAX_REQ_SEATS·포털·ExpertPicker·HandoffBrief 와 같아야 한다(test_seat_cap_contract).
const MAX_SEATS = 20;

/** 명단을 **고른다**. 기본은 기존 좌석 전원 유지다 — 좌석을 빼면 그 사람의 이전 발언을 이번 회차에서
 *  방어·수정할 당사자가 사라지므로(docs/delib-ux/context-notes.md D-3), 빼는 건 사람이 알고 하게 경고한다.
 *  명단을 손대면 엔진 재심사가 좌석을 더 얹지 않는다(rescreen:0) — 고른 명단 그대로 간다. */
export function RosterEditor({
  current,
  roster,
  onChange,
}: {
  current: Seat[];
  roster: Seat[];
  onChange: (next: Seat[]) => void;
}) {
  const { pool, loading } = usePersonaPool();
  const [browsing, setBrowsing] = useState(false);
  const has = (k: string) => roster.some((s) => s.key === k);
  const nameOf = (k: string) => pool.find((p) => p.key === k)?.name ?? k;
  const removed = current.filter((s) => !has(s.key));
  const added = roster.filter((s) => !current.some((c) => c.key === s.key));

  const toggle = (s: Seat) => onChange(has(s.key) ? roster.filter((x) => x.key !== s.key) : [...roster, s]);

  return (
    <div className="re">
      <ul className="re-list">
        {[...current, ...added].map((s) => {
          const on = has(s.key);
          const isNew = added.some((a) => a.key === s.key);
          return (
            <li key={s.key}>
              <label className={`re-seat${on ? '' : ' is-off'}${isNew ? ' is-new' : ''}`}>
                <input type="checkbox" checked={on} onChange={() => toggle(s)} />
                <span className="re-av" style={{ background: colorOf(nameOf(s.key)) }}>
                  {initialOf(nameOf(s.key))}
                </span>
                <span className="re-name" title={s.key}>
                  {shortName(nameOf(s.key))}
                </span>
                {isNew && <span className="re-tag">새 좌석</span>}
              </label>
            </li>
          );
        })}
      </ul>
      <div className="re-foot">
        <button type="button" className="re-add" onClick={() => setBrowsing(true)} disabled={loading}>
          🗂 조직도에서 더하기{loading ? ' (불러오는 중…)' : ''}
        </button>
        <span className="re-count">{roster.length}석</span>
      </div>
      {removed.length > 0 && (
        <p className="re-warn">
          빼는 좌석 {removed.length}명({removed.map((s) => shortName(nameOf(s.key))).join(', ')})의 이전 발언은 이번
          회차에서 방어·수정할 사람이 없습니다.
        </p>
      )}
      {roster.length > 0 && roster.length < 2 && <p className="re-warn">심의는 2석 이상이어야 합니다.</p>}
      <p className="re-hint">명단을 고치면 엔진이 새 분야 좌석을 자동으로 더하지 않습니다 — 고른 명단 그대로 갑니다.</p>

      {browsing && (
        <SeatBrowser
          pool={pool}
          candidates={[]}
          selected={Object.fromEntries(roster.map((s) => [s.key, { key: s.key, name: nameOf(s.key), role: s.role }]))}
          onToggle={(r) => toggle({ key: r.key, role: r.role })}
          min={2}
          max={MAX_SEATS}
          onClose={() => setBrowsing(false)}
        />
      )}
    </div>
  );
}
