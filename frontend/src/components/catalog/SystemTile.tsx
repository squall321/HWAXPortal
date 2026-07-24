import type { SystemTile as SystemTileData } from '../../api/systems.api';

export function SystemTile({
  system,
  onLaunch,
}: {
  system: SystemTileData;
  onLaunch: (s: SystemTileData) => void;
}) {
  const external = system.integration_type === 'external-url';
  const soon = system.status === 'coming_soon';
  // 준비 중(coming_soon)은 클릭 불가로 — 미배포 앱을 눌러 404 나는 걸 막는다(config 에서 상태 지정).
  const inner = (
    <>
      <div className="tile-icon">{system.icon ?? '🔗'}</div>
      <div className="tile-body">
        <div className="tile-name">{system.name}</div>
        {system.description && <div className="tile-desc">{system.description}</div>}
        <div className="tile-meta">
          {system.category && <span className="tile-tag">{system.category}</span>}
          {soon ? (
            <span className="tile-tag tile-tag-soon">준비 중</span>
          ) : (
            <span className="tile-tag tile-tag-type">{external ? 'external' : 'SSO'}</span>
          )}
        </div>
      </div>
    </>
  );
  if (soon) {
    return (
      <div className="tile tile-soon" title={`${system.name} — 준비 중`} aria-disabled="true">
        {inner}
      </div>
    );
  }
  return (
    <button className="tile" onClick={() => onLaunch(system)} title={system.name}>
      {inner}
    </button>
  );
}
