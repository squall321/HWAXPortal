import type { SystemTile as SystemTileData } from '../../api/systems.api';

export function SystemTile({
  system,
  onLaunch,
}: {
  system: SystemTileData;
  onLaunch: (s: SystemTileData) => void;
}) {
  const external = system.integration_type === 'external-url';
  return (
    <button className="tile" onClick={() => onLaunch(system)} title={system.name}>
      <div className="tile-icon">{system.icon ?? '🔗'}</div>
      <div className="tile-body">
        <div className="tile-name">{system.name}</div>
        {system.description && <div className="tile-desc">{system.description}</div>}
        <div className="tile-meta">
          {system.category && <span className="tile-tag">{system.category}</span>}
          <span className="tile-tag tile-tag-type">{external ? 'external' : 'SSO'}</span>
        </div>
      </div>
    </button>
  );
}
