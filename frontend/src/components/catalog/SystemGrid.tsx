import type { SystemTile as SystemTileData } from '../../api/systems.api';
import { SystemTile } from './SystemTile';

export function SystemGrid({
  systems,
  onLaunch,
}: {
  systems: SystemTileData[];
  onLaunch: (s: SystemTileData) => void;
}) {
  if (systems.length === 0) {
    return <p style={{ color: 'var(--muted)' }}>No systems available for your account.</p>;
  }
  return (
    <div className="tile-grid">
      {systems.map((s) => (
        <SystemTile key={s.id} system={s} onLaunch={onLaunch} />
      ))}
    </div>
  );
}
