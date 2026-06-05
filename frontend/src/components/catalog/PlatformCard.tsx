import type { CSSProperties } from 'react';
import type { SystemTile } from '../../api/systems.api';
import { PlatformLogo } from './PlatformLogo';

export function PlatformCard({
  system,
  index,
  onOpen,
}: {
  system: SystemTile;
  index: number;
  onOpen: (s: SystemTile) => void;
}) {
  const coming = system.status === 'coming_soon';
  return (
    <button
      type="button"
      className={`pcard accent-${system.accent}${coming ? ' is-coming' : ''}`}
      style={{ '--i': index } as CSSProperties}
      onClick={() => onOpen(system)}
      aria-label={system.name}
    >
      <span className="pcard-glow" aria-hidden="true" />
      <span className="pcard-rim" aria-hidden="true" />
      <div className="pcard-top">
        <PlatformLogo id={system.id} accent={system.accent} />
        {system.category && <span className="pcard-cat">{system.category}</span>}
      </div>
      <h3 className="pcard-name">{system.name}</h3>
      {system.tagline && <p className="pcard-tag">{system.tagline}</p>}
      {system.description && <p className="pcard-desc">{system.description}</p>}
      <div className="pcard-foot">
        {coming ? (
          <span className="pcard-badge">곧 공개</span>
        ) : (
          <span className="pcard-cta">
            열기 <span className="pcard-arrow">→</span>
          </span>
        )}
      </div>
    </button>
  );
}
