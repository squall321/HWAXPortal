// 사용자 관리의 권한 조각 — 허가 요청 대기열, 사용자별 소속·개별 허가 편집, 소속 일괄 지정, 관리자 지정·해제
import { useEffect, useMemo, useState } from 'react';
import {
  decideAccessRequest,
  listAccessRequests,
  setUserAccess,
  type AccessPolicy,
  type AccessRequest,
} from '../../api/access.api';
import { isUnassigned, type LocalUserRow } from '../../api/auth.api';
import '../../styles/admin.css';

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
    <div className="adm-box">
      <strong>권한 요청 {reqs.length}건</strong>
      {err && <span className="adm-err">⚠ {err}</span>}
      {reqs.length === 0 ? (
        <p className="adm-note">대기 중인 요청이 없습니다.</p>
      ) : (
        <ul className="adm-reqs">
          {reqs.map((r) => (
            <li key={r.id}>
              <span>{r.email}</span>
              <b>{labelOf(policy, r.key)}</b>
              <span className="adm-meta">
                {new Date(r.created_at * 1000).toLocaleString()}
              </span>
              {r.note && <span className="adm-meta">— {r.note}</span>}
              <span className="adm-actions">
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
  const targets = rows.filter(isUnassigned);
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
    <div className="adm-box is-inline">
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
      {msg && <span className="adm-muted">{msg}</span>}
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

/** 표의 역할 칸 — 관리자 지정·해제. 관리자 여부도 요청마다 원장으로 정하므로 바꾸면 그 사람에게 곧바로 먹는다.
 *  고정 관리자(박스 설정 PORTAL_ADMIN_EMAILS)는 여기서 못 바꾼다 — 눌러도 안 되는 스위치 대신 그 상태를 보인다. */
export function AdminToggle({
  row,
  self,
  onSaved,
  onError,
}: {
  row: LocalUserRow;
  /** 지금 화면을 보는 관리자 본인의 줄 — 스스로는 해제하지 못한다(서버도 거절한다). */
  self: boolean;
  onSaved: () => void;
  onError: (m: string) => void;
}) {
  const on = row.groups.includes('portal-admin');
  if (row.admin_pinned)
    return (
      <span
        className="adm-pin"
        title="박스 설정(PORTAL_ADMIN_EMAILS)에 있는 주소라 언제나 관리자입니다. 여기서는 해제할 수 없고, 그 설정에서 빼야 합니다."
      >
        관리자 · 고정{row.status === 'disabled' && ' (정지 중에는 권한 없음)'}
      </span>
    );
  // 지정은 활성 계정에만 한다(승인 대기는 '관리자로 승인'). 표지가 남아 있는 줄은 상태와 무관하게 뗄 수 있어야 한다.
  if (row.status !== 'active' && !on) return <span className="adm-muted">—</span>;
  const save = () => {
    if (
      on &&
      !window.confirm(
        `${row.email} 의 관리자 권한을 해제합니다. 그 사람의 개인 토큰(PAT)도 모두 폐기됩니다. 계속할까요?`,
      )
    )
      return;
    void setUserAccess(row.email, { admin: !on })
      .then(onSaved)
      .catch((err: unknown) => onError(err instanceof Error ? err.message : '저장 실패'));
  };
  return (
    <label
      className="adm-switch"
      title={self && on ? '자기 자신의 관리자 권한은 해제할 수 없습니다 — 다른 관리자에게 요청하세요.' : undefined}
    >
      <input
        type="checkbox"
        checked={on}
        disabled={self && on}
        // 이메일을 붙인다 — 없으면 화면 낭독기가 줄마다 '관리자' 만 읽는다
        aria-label={`${row.email} 관리자`}
        onChange={save}
      />
      관리자
    </label>
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
    <fieldset className="adm-grants">
      <legend>{title}</legend>
      <div className="adm-grants-list">
        {items.map((i) => (
          <label key={i.key} className={fromAff.has(i.key) ? 'is-from-aff' : undefined}>
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
    <div className="adm-box is-tight">
      <strong>{row.email} — 개별 허가</strong>
      {group('기능', policy.features.filter((f) => !policy.default_grants.includes(f.key)))}
      {group('플랫폼', policy.platforms)}
      {err && <p className="adm-err">⚠ {err}</p>}
      <div className="adm-actions">
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
