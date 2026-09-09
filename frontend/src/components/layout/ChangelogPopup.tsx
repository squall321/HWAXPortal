// 로그인 직후 '아직 안 본 업데이트'를 한 번 띄운다 — 닫으면 그 날짜까지 봤다고 기록한다
import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchChangelog, type ChangelogEntry } from '../../api/changelog.api';
import { useAuth } from '../../auth/useAuth';
import '../../styles/changelog.css';

const SEEN_PREFIX = 'hwax.changelog.seen';

// 한 탭에서 한 번만 뜬다. AppShell 은 라우트마다 다시 마운트되므로, 이게 없으면 사용자가
// 닫자마자 페이지를 옮길 때 또 뜬다(저장이 막힌 브라우저에서는 매번 뜬다).
let shownThisSession = false;

const seenKey = (email: string) => `${SEEN_PREFIX}.${email}`;

function readSeen(email: string): string {
  try {
    return localStorage.getItem(seenKey(email)) ?? '';
  } catch {
    return '';
  }
}

function writeSeen(email: string, date: string): void {
  try {
    localStorage.setItem(seenKey(email), date);
  } catch {
    /* 사생활 모드 등 — 저장이 막혀도 팝업은 정상 동작한다(세션 플래그가 반복을 막는다) */
  }
}

/** `**굵게**` 만 지원하는 최소 렌더. 이력 문구가 쓰는 유일한 마크업이라 마크다운 스택을
 *  끌어오지 않는다(레이아웃 컴포넌트가 챗 렌더러에 묶이면 안 된다). */
function Bold({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
        part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
          <b key={i}>{part.slice(2, -2)}</b>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

/** 날짜를 '9월 9일' 로. 연도가 다르면 연도까지 보여 준다. */
function dayLabel(iso: string, today: string): string {
  const [y, m, d] = iso.split('-');
  if (!y || !m || !d) return iso;
  const same = today.startsWith(`${y}-`);
  const body = `${Number(m)}월 ${Number(d)}일`;
  return same ? body : `${y}년 ${body}`;
}

export function ChangelogPopup() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [latest, setLatest] = useState('');
  const [today, setToday] = useState('');

  useEffect(() => {
    if (!user?.email || shownThisSession) return;
    let alive = true;
    void fetchChangelog(readSeen(user.email) || undefined).then((r) => {
      if (!alive || r.entries.length === 0) return;
      shownThisSession = true;
      setEntries(r.entries);
      setLatest(r.latest);
      setToday(r.today);
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
                : `마지막으로 보신 뒤 ${entries.length}건이 올라왔습니다.`}
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
        </div>

        <div className="cl-foot">
          <button type="button" className="cl-ok" onClick={close}>
            확인
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
