// 전문가 팀 고르기 · 저장 · 고치기 · 지우기 — 미리 만든 주 1 + 보조 4 조합을 고르면 그 순간의 사본을 부르는 쪽에 넘긴다(docs/expert-teams 2-1)
import { useCallback, useEffect, useState } from 'react';
import {
  createTeam,
  deleteTeam,
  listTeams,
  resolveTeam,
  setTeamOfficial,
  updateTeam,
  TEAM_LIMITS,
  type Team,
  type TeamMember,
  type TeamScope,
  type TeamSnapshot,
} from '../../api/teams.api';
import { useAuth } from '../../auth/useAuth';
import { Modal } from '../ui/Modal';
import { shortName } from './personaColor';

/** 지금 고른 조합 — 「팀으로 저장」 · 「구성을 지금 조합으로」 가 이것을 쓴다. 주 전문가가 없으면 저장할 조합이 없다. */
export interface TeamCombo {
  lead: TeamMember | null;
  helpers: TeamMember[];
  apps: string[];
  tools: string[];
}

const who = (m: TeamMember) => shortName(m.name || m.key);

function members(t: { lead: TeamMember; helpers: TeamMember[]; apps: string[]; tools: string[] }): string {
  const parts = [`주 ${who(t.lead)}`];
  if (t.helpers.length) parts.push(`보조 ${t.helpers.map(who).join(', ')}`);
  if (t.apps.length) parts.push(`앱 ${t.apps.length}`);
  if (t.tools.length) parts.push(`도구 ${t.tools.length}`);
  return parts.join(' · ');
}

function TeamForm({
  initial,
  canReplace,
  onSubmit,
  onCancel,
  submitLabel,
}: {
  initial: { name: string; description: string; scope: TeamScope };
  /** 고치기에서만 — 구성(주 · 보조 · 앱 · 도구)을 지금 조합으로 바꿀지 고른다. */
  canReplace: boolean;
  onSubmit: (v: { name: string; description: string; scope: TeamScope; replace: boolean }) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
}) {
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [scope, setScope] = useState<TeamScope>(initial.scope);
  const [replace, setReplace] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="tm-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim() || busy) return;
        setBusy(true);
        void onSubmit({ name: name.trim(), description: description.trim(), scope, replace }).finally(() => setBusy(false));
      }}
    >
      <input className="pp-search tm-name" value={name} maxLength={TEAM_LIMITS.name} onChange={(e) => setName(e.target.value)}
             placeholder="팀 이름(예: 힌지 낙하 검토팀)" aria-label="팀 이름" autoFocus />
      <input className="pp-search" value={description} maxLength={TEAM_LIMITS.description}
             onChange={(e) => setDescription(e.target.value)} placeholder="언제 쓰는지(선택)" aria-label="팀 설명" />
      <select className="pp-search tm-scope" value={scope} onChange={(e) => setScope(e.target.value as TeamScope)} aria-label="공유 범위">
        <option value="private">나만</option>
        <option value="org">같은 소속에 공유</option>
      </select>
      {canReplace && (
        <label className="tm-check">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> 구성을 지금 조합으로 바꾸기
        </label>
      )}
      <div className="tm-actions">
        <button type="submit" className="pp-clear tm-submit" disabled={busy || !name.trim()}>{busy ? '저장 중…' : submitLabel}</button>
        <button type="button" className="pp-clear" onClick={onCancel}>취소</button>
      </div>
    </form>
  );
}

export function TeamPicker({
  current,
  onPick,
  onClose,
}: {
  current: TeamCombo;
  /** 고른 팀의 사본 — 부르는 쪽이 지정값으로 복사한다. why 는 빠진 전문가가 있을 때의 알림. */
  onPick: (snap: TeamSnapshot, why: string) => void;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const admin = Boolean(user?.groups.includes('portal-admin'));
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  // 고른 팀에서 이 사람이 쓸 수 없는 전문가가 빠졌으면 닫지 않고 알린다(ET-2 — 닫힌 쪽 · 알린다)
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    listTeams()
      .then((r) => setTeams(r.teams))
      .catch((e: Error) => setErr(e.message));
  }, []);
  useEffect(() => load(), [load]);

  const act = async (id: string, fn: () => Promise<unknown>) => {
    setBusy(id);
    setErr(null);
    try {
      await fn();
      load();
    } catch (e) {
      setErr((e as Error).message);
      load();          // 409(그새 고침) · 지워짐 — 지금 판을 다시 받는다
    } finally {
      setBusy(null);
    }
  };

  const pick = async (t: Team) => {
    setBusy(t.id);
    setErr(null);
    try {
      const r = await resolveTeam(t.id);
      if (!r.team) {
        setErr(r.why || '이 팀을 쓸 수 없습니다.');
        return;
      }
      onPick(r.team, r.why);
      if (r.why) setNotice(`「${r.team.name}」 을 지정값으로 복사했습니다 — ${r.why}`);
      else onClose();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const combo = current.lead
    ? { lead: current.lead, helpers: current.helpers.slice(0, TEAM_LIMITS.helpers), apps: current.apps.slice(0, TEAM_LIMITS.apps),
        tools: current.tools.slice(0, TEAM_LIMITS.tools) }
    : null;

  return (
    <Modal onClose={onClose} label="전문가 팀">
      <div className="pp-backdrop" onClick={onClose}>
        <div className="pp-card tm-card" onClick={(e) => e.stopPropagation()}>
          <div className="pp-head">
            <span className="pp-title">전문가 팀</span>
            <button type="button" className="pp-x" onClick={onClose} aria-label="닫기">×</button>
          </div>
          <p className="pp-hint tm-note">
            미리 만든 주 전문가 1 + 보조 4 조합입니다. 고르면 그 순간의 구성이 이 대화의 지정값으로 복사됩니다 — 나중에 팀을 고쳐도 연
            대화는 그대로입니다. 내가 쓸 수 없는 전문가(앱 권한이 없는 운영자)는 고를 때 빠집니다.
          </p>
          {err && <p className="sp-warn tm-err" role="alert">{err}</p>}
          {notice && <p className="sp-warn tm-notice" role="status">{notice}</p>}

          {combo ? (
            saving ? (
              <TeamForm
                initial={{ name: '', description: '', scope: 'private' }}
                canReplace={false}
                submitLabel="팀으로 저장"
                onCancel={() => setSaving(false)}
                onSubmit={async (v) => {
                  try {
                    await createTeam({ name: v.name, description: v.description, scope: v.scope, ...combo });
                    setSaving(false);
                    setErr(null);
                    load();
                  } catch (e) {
                    setErr((e as Error).message);
                  }
                }}
              />
            ) : (
              <button type="button" className="pp-expand tm-save-open" onClick={() => setSaving(true)}>
                ＋ 지금 조합을 팀으로 저장 <span className="sp-dim">— {members(combo)}</span>
              </button>
            )
          ) : (
            <p className="pp-hint">주 전문가를 고르면 지금 조합을 팀으로 저장할 수 있습니다.</p>
          )}

          <div className="pp-body">
            {!teams && !err && <p className="pp-empty">팀을 불러오는 중…</p>}
            {teams && teams.length === 0 && <p className="pp-empty">아직 팀이 없습니다 — 전문가를 고른 뒤 위에서 저장하세요.</p>}
            {teams && teams.length > 0 && (
              <ul className="pp-list">
                {teams.map((t) => (
                  <li key={t.id} className="tm-item">
                    <button type="button" className="pp-row tm-row" disabled={busy !== null} onClick={() => void pick(t)}
                            title="고르면 이 구성을 지정값으로 복사합니다">
                      <span className="pp-row-body">
                        <span className="pp-row-name">
                          {t.name}
                          {t.official && <span className="tm-badge is-official">공식</span>}
                          {t.scope === 'org' && <span className="tm-badge">같은 소속</span>}
                          {!t.mine && <span className="tm-badge">{t.owner_email}</span>}
                        </span>
                        <span className="pp-row-sub">{members(t)}</span>
                        {t.description && <span className="pp-row-sub">{t.description}</span>}
                      </span>
                    </button>
                    {(t.editable || t.deletable || admin) && editing !== t.id && (
                      <div className="tm-actions">
                        {t.editable && (
                          <button type="button" className="pp-clear tm-edit" onClick={() => setEditing(t.id)}>고치기</button>
                        )}
                        {t.deletable && (
                          <button type="button" className="pp-clear tm-del" disabled={busy !== null}
                                  onClick={() => {
                                    if (window.confirm(`팀 「${t.name}」 을 지울까요? 이미 연 대화 · 루틴 실행은 제 사본을 쥐어 그대로입니다.`))
                                      void act(t.id, () => deleteTeam(t.id));
                                  }}>
                            지우기
                          </button>
                        )}
                        {admin && (
                          <button type="button" className="pp-clear tm-official" disabled={busy !== null}
                                  onClick={() => void act(t.id, () => setTeamOfficial(t.id, !t.official))}>
                            {t.official ? '공식 떼기' : '공식 달기'}
                          </button>
                        )}
                      </div>
                    )}
                    {editing === t.id && (
                      <TeamForm
                        initial={{ name: t.name, description: t.description, scope: t.scope }}
                        canReplace={Boolean(combo)}
                        submitLabel="고치기 저장"
                        onCancel={() => setEditing(null)}
                        onSubmit={async (v) => {
                          await act(t.id, () => updateTeam(t.id, t.version, {
                            name: v.name, description: v.description, scope: v.scope, ...(v.replace && combo ? combo : {}),
                          }));
                          setEditing(null);
                        }}
                      />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
