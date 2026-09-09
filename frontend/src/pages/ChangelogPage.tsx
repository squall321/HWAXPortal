// 업데이트 이력 — 지난 것까지 날짜별로 넘겨 가며 본다(로그인 팝업이 보여 준 것의 전체판)
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchChangelog, type ChangelogEntry } from '../api/changelog.api';
import { useAuth } from '../auth/useAuth';
import { ChangelogBold as Bold } from '../components/layout/ChangelogBold';
import { dayLabel, weekdayLabel, writeSeen } from '../components/layout/changelogShared';
import '../styles/changelog.css';

const PAGE = 20;

/** 같은 날짜의 항목을 한 덩이로 묶는다 — 이력은 '무엇이' 보다 '언제' 로 읽힌다.
 *  서버가 이미 최신순으로 주므로 순서를 다시 만들지 않고 **연속된 것만** 묶는다. */
function groupByDate(entries: ChangelogEntry[]): { date: string; rows: ChangelogEntry[] }[] {
  const out: { date: string; rows: ChangelogEntry[] }[] = [];
  for (const e of entries) {
    const last = out[out.length - 1];
    if (last && last.date === e.date) last.rows.push(e);
    else out.push({ date: e.date, rows: [e] });
  }
  return out;
}

export default function ChangelogPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [tag, setTag] = useState('');
  const [today, setToday] = useState('');
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [state, setState] = useState<'load' | 'ok' | 'fail'>('load');
  const [loadingMore, setLoadingMore] = useState(false);
  // 이 페이지를 열었다는 것은 이력을 읽었다는 뜻이다 — 같은 내용을 다음 로그인에 또
  // 팝업으로 들이밀지 않는다. 첫 로드에서 한 번만 적는다.
  const markedRef = useRef(false);

  const load = useCallback(
    async (nextTag: string) => {
      setState('load');
      const r = await fetchChangelog({ tag: nextTag || undefined, limit: PAGE });
      if (!r.ok) {
        setState('fail');
        return;
      }
      setEntries(r.entries);
      setToday(r.today);
      setTotal(r.total ?? r.entries.length);
      setHasMore(Boolean(r.has_more));
      // 분류를 걸어도 tags 는 전체 기준으로 온다 — 칩 목록이 필터마다 흔들리지 않게 유지.
      if (r.tags?.length) setTags(r.tags);
      setState('ok');
      if (!markedRef.current && user?.email && r.latest) {
        markedRef.current = true;
        writeSeen(user.email, r.latest);
      }
    },
    [user?.email],
  );

  useEffect(() => {
    void load(tag);
  }, [tag, load]);

  const more = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const r = await fetchChangelog({ tag: tag || undefined, offset: entries.length, limit: PAGE });
    if (r.ok) {
      setEntries((prev) => [...prev, ...r.entries]);
      setHasMore(Boolean(r.has_more));
    }
    setLoadingMore(false);
  };

  const groups = useMemo(() => groupByDate(entries), [entries]);

  return (
    <div className="clp-wrap">
      <header className="clp-head">
        <h1 className="clp-title">업데이트 이력</h1>
        <p className="clp-sub">
          포털이 어떻게 바뀌어 왔는지 날짜별로 볼 수 있습니다. 로그인할 때는 아직 못 보신
          것만 안내로 띄웁니다.
        </p>
      </header>

      {tags.length > 0 && (
        <div className="clp-filters" role="group" aria-label="분류 필터">
          <button
            type="button"
            className={`clp-chip${tag === '' ? ' is-on' : ''}`}
            onClick={() => setTag('')}
          >
            전체
          </button>
          {tags.map((t) => (
            <button
              key={t}
              type="button"
              className={`clp-chip cl-tag-${t}${tag === t ? ' is-on' : ''}`}
              onClick={() => setTag(t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {state === 'load' && <p className="clp-empty">불러오는 중…</p>}
      {state === 'fail' && (
        <p className="clp-empty">
          이력을 불러오지 못했습니다. 잠시 후 새로고침해 보세요.
        </p>
      )}
      {state === 'ok' && entries.length === 0 && (
        <p className="clp-empty">
          {tag ? `‘${tag}’ 분류의 항목이 아직 없습니다.` : '아직 기록된 업데이트가 없습니다.'}
        </p>
      )}

      {state === 'ok' && entries.length > 0 && (
        <>
          <p className="clp-count">
            {tag ? `‘${tag}’ ` : ''}
            {total}건 · {entries.length}건 표시 중
          </p>
          <ol className="clp-timeline">
            {groups.map((g) => (
              <li className="clp-day" key={g.date}>
                <div className="clp-day-mark">
                  <span className="clp-dot" aria-hidden="true" />
                  <time className="clp-day-date" dateTime={g.date}>
                    {dayLabel(g.date, today)}
                    {weekdayLabel(g.date) && (
                      <span className="clp-dow"> ({weekdayLabel(g.date)})</span>
                    )}
                  </time>
                  {g.date === today && <span className="clp-today">오늘</span>}
                </div>
                <div className="clp-day-body">
                  {g.rows.map((e, i) => (
                    <article className="clp-entry" key={`${e.date}-${i}`}>
                      <h2 className="clp-entry-title">
                        {e.title}
                        {e.tag && <span className={`cl-tag cl-tag-${e.tag}`}>{e.tag}</span>}
                      </h2>
                      {e.items.length > 0 && (
                        <ul className="cl-items">
                          {e.items.map((it, j) => (
                            <li key={j}>
                              <Bold text={it} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </article>
                  ))}
                </div>
              </li>
            ))}
          </ol>
          {hasMore && (
            <button type="button" className="clp-more" onClick={() => void more()} disabled={loadingMore}>
              {loadingMore ? '불러오는 중…' : `이전 이력 더 보기 (${total - entries.length}건 남음)`}
            </button>
          )}
          {!hasMore && <p className="clp-end">— 여기까지가 전부입니다 —</p>}
        </>
      )}
    </div>
  );
}
