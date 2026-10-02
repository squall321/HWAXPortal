// 앱 카드 — 중립 카드 · 단색 글리프 · 한국어 분류 · 태그라인 1줄 · 설명 3줄(전문은 툴팁) · 새 탭으로 연다
import type { SystemTile } from '../../api/systems.api';
import { IconExternal } from '../chat/icons';
import { groupOf } from './appGroups';
import { PlatformLogo } from './PlatformLogo';

export function PlatformCard({ system, onOpen }: { system: SystemTile; onOpen: (s: SystemTile) => void }) {
  const coming = system.status === 'coming_soon';
  return (
    <button
      type="button"
      className={`app-card${coming ? ' is-coming' : ''}`}
      onClick={() => onOpen(system)}
      aria-label={`${system.name}${coming ? ' — 곧 공개' : ' — 새 탭에서 열기'}`}
      title={system.description || undefined}
    >
      <div className="app-card-top">
        <PlatformLogo id={system.id} />
        <span className="app-card-group">{groupOf(system.category)}</span>
      </div>
      <h3 className="app-card-name">{system.name}</h3>
      {system.tagline && <p className="app-card-tag">{system.tagline}</p>}
      {system.description && <p className="app-card-desc">{system.description}</p>}
      <div className="app-card-foot">
        {coming ? (
          <span className="app-card-badge">곧 공개</span>
        ) : (
          <span className="app-card-cta">
            새 탭에서 열기 <IconExternal width={13} height={13} />
          </span>
        )}
      </div>
    </button>
  );
}
