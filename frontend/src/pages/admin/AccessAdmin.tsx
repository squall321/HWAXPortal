// 사용자 관리의 권한 조각 — 허가 요청 대기열, 사용자별 소속·개별 허가 편집, 소속 일괄 지정
import { useEffect, useMemo, useState } from 'react';
import {
  decideAccessRequest,
  listAccessRequests,
  setUserAccess,
  type AccessPolicy,
  type AccessRequest,
} from '../../api/access.api';
import type { LocalUserRow } from '../../api/auth.api';

const box: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 10,
  padding: '0.8rem 1rem',
  margin: '0.8rem 0',
  background: 'var(--card)',
};

function labelOf(policy: AccessPolicy | null, key: string): string {
  if (!policy) return key;
  return [...policy.features, ...policy.platforms].find((i) => i.key === key)?.label ?? key;
}

/** 허가 요청 대기열 — 승인하면 그 사람의 개별 허가에 더해지고 곧바로 먹는다(재로그인 불필요). */
export function AccessRequestsPanel({ policy, onChanged }: { policy: AccessPolicy | null; onChanged: () => void }) {
  const [reqs, setReqs] = useState<AccessRequest[] | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState<number | null>(null);
  const load = () => {
    listAccessRequests('pending')
      .then(setReqs)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : '불러오기 실패'));
  };
  useEffect(load, []);
  const decide = async (id: number, approve: boolean) => {
    setBusy(id);
    setErr('');
    try {
      await decideAccessRequest(id, approve);
      load();
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : '처리 실패');
    } finally {
      setBusy(null);
    }
  };
  if (!reqs) return null;
  return (
    <div style={box}>
      <strong>권한 요청 {reqs.length}건</strong>
      {err && <span style={{ color: 'var(--danger-fg, #f28b82)', marginLeft: 8 }}>⚠ {err}</span>}
      {reqs.length === 0 ? (
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.3rem 0 0' }}>대기 중인 요청이 없습니다.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0 0', display: 'grid', gap: 6 }}>
          {reqs.map((r) => (
            <li key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
              <span>{r.email}</span>
              <b>{labelOf(policy, r.key)}</b>
              <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
                {new Date(r.created_at * 1000).toLocaleString()}
              </span>
              {r.note && <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>— {r.note}</span>}
              <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                <button className="btn-primary" disabled={busy === r.id} onClick={() => void decide(r.id, true)}>
                  승인
                </button>
                <button className="btn-secondary" disabled={busy === r.id} onClick={() => void decide(r.id, false)}>
                  거절
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** 소속 없는 활성 사용자를 한 번에 소속으로 — 권한 모델을 켤 때 기존 사용자를 옮기는 길. */
export function BulkAffiliation({
  policy,
  rows,
  onChanged,
}: {
  policy: AccessPolicy | null;
  rows: LocalUserRow[];
  onChanged: () => void;
}) {
  const [aff, setAff] = useState('CAEG');
  const [msg, setMsg] = useState('');
  const targets = rows.filter((r) => r.status === 'active' && !r.affiliation && !r.groups.includes('portal-admin'));
  if (!policy || policy.affiliations.length === 0 || targets.length === 0) return null;
  const run = async () => {
    const label = policy.affiliations.find((a) => a.id === aff)?.label ?? aff;
    if (!window.confirm(`소속이 없는 사용자 ${targets.length}명을 '${label}'(으)로 지정합니다. 계속할까요?`)) return;
    let ok = 0;
    for (const r of targets) {
      try {
        await setUserAccess(r.email, { affiliation: aff });
        ok += 1;
      } catch {
        /* 다음 사람 계속 — 결과는 아래에 수로 알린다 */
      }
    }
    setMsg(`${ok}/${targets.length}명 지정했습니다.`);
    onChanged();
  };
  return (
    <div style={{ ...box, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      <span>
        소속이 없는 활성 사용자 <b>{targets.length}명</b> — 기본 권한(일반 챗)만 씁니다.
      </span>
      <select value={aff} onChange={(e) => setAff(e.target.value)}>
        {policy.affiliations.map((a) => (
          <option key={a.id} value={a.id}>
            {a.label}
          </option>
        ))}
      </select>
      <button className="btn-secondary" onClick={() => void run()}>
        모두 이 소속으로
      </button>
      {msg && <span style={{ color: 'var(--muted)' }}>{msg}</span>}
    </div>
  );
}

/** 표의 소속 칸 — 고르면 곧바로 저장한다(권한은 요청마다 계산되므로 그 사람에게 바로 먹는다). */
export function AffiliationSelect({
  policy,
  row,
  onSaved,
  onError,
}: {
  policy: AccessPolicy | null;
  row: LocalUserRow;
  onSaved: () => void;
  onError: (m: string) => void;
}) {
  if (!policy) return <>{row.affiliation || '—'}</>;
  return (
    <select
      value={row.affiliation ?? ''}
      aria-label={`${row.email} 소속`}
      onChange={(e) =>
        void setUserAccess(row.email, { affiliation: e.target.value })
          .then(onSaved)
          .catch((err: unknown) => onError(err instanceof Error ? err.message : '저장 실패'))
      }
    >
      <option value="">— 없음(기본 권한)</option>
      {policy.affiliations.map((a) => (
        <option key={a.id} value={a.id}>
          {a.label}
        </option>
      ))}
    </select>
  );
}

/** 개별 허가 편집 — 기능·플랫폼 체크. 소속이 이미 주는 것은 표시만 한다(중복 허가를 만들지 않게). */
export function GrantEditor({
  policy,
  row,
  onSaved,
  onClose,
}: {
  policy: AccessPolicy;
  row: LocalUserRow;
  onSaved: () => void;
  onClose: () => void;
}) {
  const [sel, setSel] = useState<Set<string>>(() => new Set(row.grants ?? []));
  const [err, setErr] = useState('');
  const fromAff = useMemo(() => {
    const a = policy.affiliations.find((x) => x.id === row.affiliation);
    if (!a) return new Set<string>();
    if (a.grants.includes('*')) return new Set([...policy.features, ...policy.platforms].map((i) => i.key));
    return new Set(a.grants);
  }, [policy, row.affiliation]);
  const toggle = (k: string) =>
    setSel((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  const save = () =>
    void setUserAccess(row.email, { grants: [...sel] })
      .then(() => {
        onSaved();
        onClose();
      })
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : '저장 실패'));
  const group = (title: string, items: { key: string; label: string }[]) => (
    <fieldset style={{ border: 'none', padding: 0, margin: '0.4rem 0' }}>
      <legend style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{title}</legend>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem 0.9rem' }}>
        {items.map((i) => (
          <label key={i.key} style={{ fontSize: '0.85rem', opacity: fromAff.has(i.key) ? 0.55 : 1 }}>
            <input
              type="checkbox"
              checked={fromAff.has(i.key) || sel.has(i.key)}
              disabled={fromAff.has(i.key)}
              onChange={() => toggle(i.key)}
            />{' '}
            {i.label}
            {fromAff.has(i.key) && ' (소속)'}
          </label>
        ))}
      </div>
    </fieldset>
  );
  return (
    <div style={{ ...box, margin: '0.3rem 0' }}>
      <strong>{row.email} — 개별 허가</strong>
      {group('기능', policy.features.filter((f) => !policy.default_grants.includes(f.key)))}
      {group('플랫폼', policy.platforms)}
      {err && <p style={{ color: 'var(--danger-fg, #f28b82)' }}>⚠ {err}</p>}
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="btn-primary" onClick={save}>
          저장
        </button>
        <button className="btn-secondary" onClick={onClose}>
          닫기
        </button>
      </div>
    </div>
  );
}
