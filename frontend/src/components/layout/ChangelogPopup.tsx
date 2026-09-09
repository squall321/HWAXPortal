// 로그인 직후 '아직 안 본 업데이트'를 한 번 띄운다 — 닫으면 그 날짜까지 봤다고 기록한다
import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { fetchChangelog, type ChangelogEntry } from '../../api/changelog.api';
import { useAuth } from '../../auth/useAuth';
import { ChangelogBold as Bold } from './ChangelogBold';
import { dayLabel, readSeen, writeSeen } from './changelogShared';
import '../../styles/changelog.css';

// 한 탭에서 한 번만 뜬다. AppShell 은 라우트마다 다시 마운트되므로, 이게 없으면 사용자가
// 닫자마자 페이지를 옮길 때 또 뜬다(저장이 막힌 브라우저에서는 매번 뜬다).
let shownThisSession = false;

export function ChangelogPopup() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [latest, setLatest] = useState('');
  const [today, setToday] = useState('');
  // 상한(5건)에 걸려 못 보여 준 게 몇 건인지 — "이전 이력" 으로 안내할 근거다.
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!user?.email || shownThisSession) return;
    let alive = true;
    void fetchChangelog({ since: readSeen(user.email) || undefined }).then((r) => {
      if (!alive || r.entries.length === 0) return;
      shownThisSession = true;
      setEntries(r.entries);
      setLatest(r.latest);
      setToday(r.today);
      setTotal(r.total ?? r.entries.length);
    });
    return () => {
      alive = false;
    };
  }, [user?.email]);

  const close = useCallback(() => {
    // 받아온 것의 최신이 아니라 **전체의** 최신을 적는다 — limit 에 잘린 옛 항목이
    // 다음 로그인에 다시 뜨지 않게.
    if (user?.email && latest) writeSeen(user.email, latest);
    setEntries([]);
  }, [user?.email, latest]);

  useEffect(() => {
    if (entries.length === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [entries.length, close]);

  if (entries.length === 0) return null;

  const isToday = Boolean(today) && entries[0].date === today;
  const hidden = Math.max(0, total - entries.length);

  return createPortal(
    <div className="cl-backdrop" onClick={close}>
      <div
        className="cl-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cl-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="cl-head">
          <span className="cl-spark" aria-hidden="true">
            ✦
          </span>
          <div>
            <h2 className="cl-title" id="cl-title">
              {isToday ? '오늘 업데이트되었습니다' : '그동안 달라진 것'}
            </h2>
            <p className="cl-sub">
              {isToday
                ? '이번에 바뀐 내용입니다.'
                : `마지막으로 보신 뒤 ${total}건이 올라왔습니다.`}
            </p>
          </div>
          <button type="button" className="cl-x" onClick={close} aria-label="닫기">
            ×
          </button>
        </div>

        <div className="cl-body">
          {entries.map((e, i) => (
            <section className="cl-entry" key={`${e.date}-${i}`}>
              <div className="cl-entry-head">
                <span className="cl-date">{dayLabel(e.date, today)}</span>
                {e.tag && <span className={`cl-tag cl-tag-${e.tag}`}>{e.tag}</span>}
              </div>
              <h3 className="cl-entry-title">{e.title}</h3>
              {e.items.length > 0 && (
                <ul className="cl-items">
                  {e.items.map((it, j) => (
                    <li key={j}>
                      <Bold text={it} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
          {hidden > 0 && (
            <p className="cl-more-note">…그 밖에 {hidden}건이 더 있습니다.</p>
          )}
        </div>

        <div className="cl-foot">
          {/* 팝업을 닫아도 언제든 다시 볼 수 있어야 한다 — 지난 이력으로 가는 길. */}
          <Link className="cl-link" to="/updates" onClick={close}>
            이전 이력 모두 보기 →
          </Link>
          <button type="button" className="cl-ok" onClick={close}>
            확인
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
