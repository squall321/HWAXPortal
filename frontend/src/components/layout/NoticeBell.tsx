// 머리줄 알림 — 안 읽은 수 표지와 알림 목록(제목 · 한 줄 · 시각 · 링크 · 읽음). 탭이 보이는 동안 1분마다 다시 묻는다(docs/request-1117 contracts §7)
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  fetchNotices,
  markAllNoticesRead,
  markNoticeRead,
  safeNoticeLink,
  unreadLabel,
  type Notice,
} from '../../api/notices.api';
import '../../styles/notices.css';

// 포털이 끝난 묶음을 묻는 간격(DELIB_BATCH_NOTICE_S 기본 60초)과 같게 — 더 자주 물어도 새 알림은 그보다 빨리 생기지 않는다
const POLL_MS = 60_000;

function when(sec: number): string {
  return new Date(sec * 1000).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

function BellIcon() {
  return (
    <svg className="ntc-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="M10 3a4.5 4.5 0 0 0-4.5 4.5v2.7L4 13.5h12l-1.5-3.3V7.5A4.5 4.5 0 0 0 10 3zM8.2 15.5a1.9 1.9 0 0 0 3.6 0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function NoticeBell() {
  const [items, setItems] = useState<Notice[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState('');
  const [loaded, setLoaded] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const id = useId();
  const { pathname } = useLocation();

  const load = useCallback(async () => {
    try {
      const r = await fetchNotices();
      setItems(r.items);
      setUnread(r.unread);
      setErr('');
    } catch (e) {
      setErr(e instanceof Error ? e.message : '알림을 불러오지 못했습니다.');
    } finally {
      setLoaded(true);
    }
  }, []);

  // 처음 한 번 · 보이는 동안 1분마다 · 탭을 다시 앞으로 가져왔을 때(절전으로 인터벌이 밀렸을 수 있다)
  useEffect(() => {
    void load();
    const tick = () => {
      if (document.visibilityState === 'visible') void load();
    };
    const t = window.setInterval(tick, POLL_MS);
    document.addEventListener('visibilitychange', tick);
    return () => {
      window.clearInterval(t);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [load]);

  // 열 때 새로 받는다 · 화면을 옮기면 닫는다
  useEffect(() => {
    if (open) void load();
  }, [open, load]);
  useEffect(() => setOpen(false), [pathname]);

  // 바깥을 누르거나 Esc 면 닫는다(Esc 는 단추로 포커스를 돌려준다)
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        btn.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const readOne = async (n: Notice) => {
    if (n.read_at) return;
    try {
      setUnread(await markNoticeRead(n.id));
      const now = Math.floor(Date.now() / 1000);
      setItems((xs) => xs.map((x) => (x.id === n.id ? { ...x, read_at: now } : x)));
    } catch (e) {
      setErr(e instanceof Error ? e.message : '읽음으로 표시하지 못했습니다.');
    }
  };

  const readAll = async () => {
    try {
      setUnread(await markAllNoticesRead());
      const now = Math.floor(Date.now() / 1000);
      setItems((xs) => xs.map((x) => (x.read_at ? x : { ...x, read_at: now })));
    } catch (e) {
      setErr(e instanceof Error ? e.message : '모두 읽음으로 표시하지 못했습니다.');
    }
  };

  const count = unreadLabel(unread);

  return (
    <div className="ntc" ref={root}>
      <button
        ref={btn}
        type="button"
        className={`ntc-btn${open ? ' is-open' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-label={unread > 0 ? `알림 — 안 읽은 알림 ${unread}건` : '알림'}
        title={unread > 0 ? `안 읽은 알림 ${unread}건` : '알림'}
        onClick={() => setOpen((o) => !o)}
      >
        <BellIcon />
        {count && (
          <span className="ntc-count" aria-hidden="true">
            {count}
          </span>
        )}
      </button>
      {open && (
        <div className="ntc-pop" id={id} role="dialog" aria-label="알림">
          <div className="ntc-head">
            <strong>알림</strong>
            <button
              type="button"
              className="ntc-act"
              disabled={unread === 0}
              onClick={() => void readAll()}
            >
              모두 읽음
            </button>
          </div>
          {err && (
            <p className="ntc-err" role="alert">
              {err}
            </p>
          )}
          {items.length === 0 ? (
            !err && (
              <p className="ntc-empty">
                {loaded
                  ? '아직 알림이 없습니다. 심의 묶음이 끝나면 여기에 알려 드립니다.'
                  : '불러오는 중입니다.'}
              </p>
            )
          ) : (
            <ul className="ntc-list">
              {items.map((n) => {
                const href = safeNoticeLink(n.link);
                return (
                  <li key={n.id} className={`ntc-item${n.read_at ? '' : ' is-unread'}`}>
                    <div className="ntc-title">{n.title}</div>
                    <div className="ntc-line">{n.line}</div>
                    <div className="ntc-meta">
                      <time dateTime={new Date(n.created_at * 1000).toISOString()}>
                        {when(n.created_at)}
                      </time>
                      <span className="ntc-src" title="원천 id">
                        {n.source_id}
                      </span>
                      <span className="ntc-gap" />
                      {href && (
                        <Link
                          to={href}
                          className="ntc-act"
                          onClick={() => {
                            void readOne(n);
                            setOpen(false);
                          }}
                        >
                          열기
                        </Link>
                      )}
                      {!n.read_at && (
                        <button type="button" className="ntc-act" onClick={() => void readOne(n)}>
                          읽음
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
