// 서비스 토큰(관리자 전용) — 박스 작업(update-all 훅 등)이 게이트웨이를 부르는 system:<작업> 토큰을 발급 · 회수하는 칸(docs/core-link design §2)
import { type FormEvent, useCallback, useEffect, useState } from 'react';
import {
  createServicePat,
  listServicePats,
  revokePat,
  type ServicePatCreated,
  type ServicePatMeta,
} from '../api/pat.api';
import { copyText } from './chat/clipboard';
import '../styles/tokenpage.css';

// 작업 이름 — 서버(app/auth/service_pat.py 의 JOB_RE)와 같은 꼴. 화면은 먼저 알려 줄 뿐이고 서버가 다시 본다.
const JOB_RE = /^[a-z0-9][a-z0-9-]{0,39}$/;
const MIN_DAYS = 1;
const MAX_DAYS = 365; // 무기한은 없다 — 만료와 회수 둘 다로 죽는다
// 만료가 이만큼 안으로 들어오면 표시한다 — 새 토큰을 발급해 박스 작업에 갈아 끼울 시간을 둔다
const SOON_S = 14 * 86400;

function fmtDate(sec: number): string {
  return new Date(sec * 1000).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

// created · onCreated — 방금 발급한 토큰은 토큰 화면(TokenPage)이 쥔다. 이 칸에 두면 탭을 오갈 때(칸이 내려갔다 다시 뜰 때) 사라졌다.
export default function ServiceTokenPanel({
  created,
  onCreated,
}: {
  created: ServicePatCreated | null;
  onCreated: (got: ServicePatCreated | null) => void;
}) {
  const [job, setJob] = useState('');
  // 숫자칸의 글 그대로 둔다 — 비운 칸을 숫자로 바꾸면 NaN 이 value 에 들어간다
  const [days, setDays] = useState('90');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [rows, setRows] = useState<ServicePatMeta[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listServicePats()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const jobOk = JOB_RE.test(job);
  const daysN = Number(days);
  const daysOk = /^\d+$/.test(days) && daysN >= MIN_DAYS && daysN <= MAX_DAYS;

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!jobOk || !daysOk || busy) return;
    setBusy(true);
    setError(null);
    try {
      const got = await createServicePat({ job, days: daysN, note: note.trim() || undefined });
      onCreated(got);
      setCopied(false);
      setJob('');
      setNote('');
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '서비스 토큰 발급에 실패했습니다.');
    } finally {
      setBusy(false);
    }
  };

  const onCopy = async () => {
    if (!created) return;
    const ok = await copyText(created.token);
    setCopied(ok);
    if (!ok) setError('복사하지 못했습니다 — 아래 토큰을 직접 선택해 복사하세요.');
  };

  const onRevoke = async (r: ServicePatMeta) => {
    const ask = `작업 ${r.job} 의 서비스 토큰을 회수할까요? 이 토큰을 쓰는 박스 작업은 1분 안에 게이트웨이에서 막히고, 되돌릴 수 없습니다.`;
    if (!window.confirm(ask)) return;
    setError(null);
    try {
      await revokePat(r.jti);
      if (created?.jti === r.jti) onCreated(null); // 방금 발급한 토큰을 회수하면 표시도 지운다
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : '서비스 토큰 회수에 실패했습니다.');
    }
  };

  const now = Date.now() / 1000;

  return (
    <>
      {/* 제목은 토큰 화면의 탭 이름('서비스 토큰')이 대신한다. 표 모양은 같은 화면의 '내 토큰' 표(tokenpage.css)를 쓴다 */}
      <section className="tok-sec">
        <p className="tok-muted hub-lead">
          사람이 아니라 박스 작업 하나(<code>system:작업</code>)의 이름으로 게이트웨이를 부르는
          토큰입니다. 게이트웨이는 그 박스의 <code>service_tools.local.json</code> 에 그 작업이
          허용한 도구 · REST 경로만 부르게 하고, 목록에 없는 작업의 토큰은 403 으로 막습니다. 포털
          챗 · 토큰 교환에는 쓰이지 않습니다.
        </p>
        {error && (
          <p role="alert" className="tok-danger">
            {error}
          </p>
        )}
        <h2>새 서비스 토큰</h2>
        <form onSubmit={onCreate} className="tok-form">
          <input
            id="svc-job"
            value={job}
            onChange={(e) => setJob(e.target.value)}
            placeholder="작업 이름 (예: core-link)"
            aria-label="작업 이름"
            maxLength={40}
          />
          <input
            id="svc-days"
            type="number"
            min={MIN_DAYS}
            max={MAX_DAYS}
            step={1}
            value={days}
            onChange={(e) => setDays(e.target.value)}
            aria-label="수명(일)"
            title={`수명(일) — ${MIN_DAYS} ~ ${MAX_DAYS}`}
          />
          <input
            id="svc-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="메모 (선택 — 어느 박스 · 어디에 넣었는지)"
            aria-label="메모"
            maxLength={200}
          />
          <button type="submit" className="btn-primary" disabled={busy || !jobOk || !daysOk}>
            {busy ? '발급 중…' : '발급'}
          </button>
        </form>
        {job && !jobOk && (
          <p className="tok-hint">
            작업 이름은 영소문자 · 숫자로 시작하고 영소문자 · 숫자 · <code>-</code> 만 40자까지
            씁니다.
          </p>
        )}
        {!daysOk && (
          <p className="tok-hint">
            수명은 {MIN_DAYS} ~ {MAX_DAYS}일입니다(무기한 없음).
          </p>
        )}
      </section>

      {created && (
        <section className="tok-created">
          <div className="tok-created-title">
            지금만 보이는 토큰 — 이 화면을 벗어나면 다시 볼 수 없습니다. 반드시 복사해 박스 작업의
            비밀 자리에 넣으세요.
          </div>
          <div className="tok-copy">
            <div className="tok-copy-head">
              <span>
                서비스 토큰 (system:{created.job} · {fmtDate(created.expires_at)} 만료)
              </span>
              <button
                type="button"
                className="btn-secondary tok-btn-sm"
                onClick={() => void onCopy()}
              >
                {copied ? '복사됨' : '복사'}
              </button>
            </div>
            <pre>{created.token}</pre>
          </div>
          <p className="tok-hint">
            게이트웨이 박스의 <code>service_tools.local.json</code> 에 작업{' '}
            <code>{created.job}</code> 이 있어야 이 토큰이 통합니다. 없으면 게이트웨이가 403 으로
            막습니다.
          </p>
        </section>
      )}

      <section className="tok-sec">
        <h2>발급한 서비스 토큰</h2>
        {rows === null ? (
          !error && <p className="tok-muted">불러오는 중…</p>
        ) : rows.length === 0 ? (
          <p className="tok-muted">아직 발급한 서비스 토큰이 없습니다.</p>
        ) : (
          <div className="tok-table-wrap">
            <table className="tok-table svc-table">
              <thead>
                <tr>
                  <th>작업</th>
                  <th>발급</th>
                  <th>만료</th>
                  <th>jti</th>
                  <th aria-label="동작"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const left = r.expires_at - now;
                  return (
                    <tr key={r.jti} className={r.revoked ? 'is-revoked' : undefined}>
                      <td>
                        {/* 메모는 작업 이름 밑에 — 칸을 하나 줄여 좁은 화면에서도 '내 토큰' 표와 같은 다섯 칸이다 */}
                        <span className="svc-job">
                          {r.job}
                          {r.revoked && <span className="tok-badge">회수됨</span>}
                        </span>
                        {r.note && <div className="tok-hint">{r.note}</div>}
                      </td>
                      <td>
                        {fmtDate(r.created_at)}
                        <div className="tok-hint">{r.issued_by}</div>
                      </td>
                      <td>
                        {fmtDate(r.expires_at)}
                        {!r.revoked && left <= 0 && <span className="tok-badge">만료됨</span>}
                        {!r.revoked && left > 0 && left < SOON_S && (
                          <span
                            className="tok-badge is-soon"
                            title="새 토큰을 발급해 박스 작업에 갈아 끼우세요"
                          >
                            {Math.ceil(left / 86400)}일 남음
                          </span>
                        )}
                      </td>
                      <td className="tok-jti">{r.jti}</td>
                      <td className="tok-cell-act">
                        {!r.revoked && left > 0 && (
                          <button
                            type="button"
                            className="btn-secondary tok-btn-sm"
                            onClick={() => void onRevoke(r)}
                          >
                            회수
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
