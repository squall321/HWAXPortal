// 배선 요청·설정 — **안 되어 있으면 여기서 말한다.** 다 되면 아무것도 안 그린다
//
// 이 스택에서 반복된 실패 모양이 "설정 한 줄이 빠졌는데 아무 데도 안 보인다" 였다.
// 배포는 성공하고 화면도 멀쩡한데 그 기능만 조용히 안 되는 식이라, 며칠 뒤 사용자가
// "왜 안 되죠" 로 발견한다. 안 본 곳에 적어 두는 것은 안 적은 것과 같다 — 그래서 상자는
// 사용자 관리 맨 위에 두고, 헤더 '관리' 에 건수를 늘 띄운다(종전엔 모든 사람이 여는 앱 목록 위에 있었다, docs/ui-refresh 단계 4).
import { useCallback, useEffect, useState } from 'react';
import { listSetupRequests, setSetupAck, type SetupAck, type SetupRequest } from '../../api/setup.api';
import '../../styles/setup.css';

const SEV_LABEL: Record<string, string> = {
  blocker: '필수',
  important: '권장',
  request: '요청',
};
const STATE_LABEL: Record<string, string> = {
  todo: '안 되어 있음',
  manual: '확인 필요',
  unknown: '확인 못 함',
};
// "기본값이 들어가나" — 사람이 반드시 손대야 하는 것과 그냥 한 번 돌리면 되는 것을 가른다.
// 이 구분이 없으면 목록 전체가 "다 내가 해야 하는 일" 로 보여서 아무도 시작하지 않는다.
const DEFAULT_LABEL: Record<string, string> = {
  auto: '기본값 있음',
  generate: '없으면 생성됨',
  none: '값을 정해야 함',
};

export function SetupRequests() {
  const [items, setItems] = useState<SetupRequest[] | null>(null);
  const [acked, setAcked] = useState<SetupAck[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(
    () =>
      listSetupRequests()
        .then((r) => {
          setItems(r.items);
          setAcked(r.acked);
        })
        .catch(() => setItems([])),
    [],
  );
  useEffect(() => {
    void load();
  }, [load]);

  const ack = async (id: string, on: boolean) => {
    setBusy(id);
    setErr(null);
    try {
      await setSetupAck(id, on);
      await load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  if (!items || (items.length === 0 && acked.length === 0)) return null; // 다 됐으면 조용히 사라진다

  const blockers = items.filter((i) => i.severity === 'blocker').length;
  return (
    <section className={`setup-requests${items.length === 0 ? ' is-clear' : ''}`} aria-label="배선 설정" id="setup">
      <header>
        <strong>{items.length > 0 ? `배선 설정 ${items.length}건` : '배선 설정 — 남은 것 없음'}</strong>
        {blockers > 0 && <span className="sev sev-blocker">필수 {blockers}</span>}
        <span className="hint">
          포털이 확인하는 항목은 고쳐지면 사라집니다. 확인할 수 없는 항목은 해 두고 <b>확인함</b>을 누르세요.
        </span>
      </header>
      {err && (
        <p className="setup-err" role="alert">
          {err}
        </p>
      )}
      {items.length > 0 && (
        <ul>
          {items.map((it) => (
            <li key={it.id} className={`sev-${it.severity}`}>
              <button type="button" aria-expanded={open === it.id} onClick={() => setOpen(open === it.id ? null : it.id)}>
                <span className={`sev sev-${it.severity}`}>{SEV_LABEL[it.severity] ?? it.severity}</span>
                <span className="title">{it.title}</span>
                {it.tag && <span className="tag">{it.tag}</span>}
                <span className={`dflt dflt-${it.default}`}>{DEFAULT_LABEL[it.default] ?? ''}</span>
                <span className="state">{STATE_LABEL[it.state] ?? it.state}</span>
              </button>
              {open === it.id && (
                <div className="setup-body">
                  <pre className="body">{it.body}</pre>
                  {it.state === 'manual' && (
                    <button
                      type="button"
                      className="btn-secondary setup-ack"
                      disabled={busy !== null}
                      onClick={() => void ack(it.id, true)}
                    >
                      {busy === it.id ? '저장 중…' : '했습니다 — 확인함'}
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {acked.length > 0 && (
        <details className="setup-acked">
          <summary>확인한 항목 {acked.length}건</summary>
          <ul>
            {acked.map((a) => (
              <li key={a.id}>
                <span className="title">{a.title}</span>
                <span className="tag">
                  {a.by} · {new Date(a.at * 1000).toLocaleDateString('ko-KR')}
                </span>
                <button
                  type="button"
                  className="btn-secondary setup-ack"
                  disabled={busy !== null}
                  onClick={() => void ack(a.id, false)}
                >
                  {busy === a.id ? '저장 중…' : '되돌리기'}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
