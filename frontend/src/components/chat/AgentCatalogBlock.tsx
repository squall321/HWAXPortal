// 전문가 카탈로그 카드 — '/전문가' 검색 응답(SSE agents)을 **고를 수 있는** UI 로 렌더.
// 도구(/도구)는 오래전부터 이 대우를 받았는데 전문가만 텍스트로 흘러 나가고 있었다.
import { useMemo, useState } from 'react';
import { useChat } from '../../state/ChatContext';
import type { AgentCatalog } from '../../types/chat';
import { PersonaBrowser } from './PersonaBrowser';
import { colorOf, initialOf, shortName } from './personaColor';
import { domainLabel } from './personaCatalog';

const POOL_LIMIT = 24;

export function AgentCatalogBlock({ catalog }: { catalog: AgentCatalog }) {
  const { pinnedAgent, setPinnedAgent } = useChat();
  const [q, setQ] = useState('');
  const [browse, setBrowse] = useState(false);

  const hits = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return [];
    return catalog.pool
      .filter((a) => a.name.toLowerCase().includes(needle) || a.key.toLowerCase().includes(needle))
      .slice(0, POOL_LIMIT);
  }, [catalog.pool, q]);

  const row = (key: string, name: string, desc?: string) => {
    const on = pinnedAgent === key;
    return (
      <li key={key}>
        <button
          type="button"
          className={`ac-row${on ? ' is-on' : ''}`}
          onClick={() => setPinnedAgent(on ? null : key, name)}
          title={desc}
        >
          <span className="ac-av" style={{ background: colorOf(name) }}>
            {initialOf(name)}
          </span>
          <span className="ac-body">
            <span className="ac-name" title={name}>{shortName(name)}</span>
            {desc && <span className="ac-desc">{desc}</span>}
          </span>
          <span className="ac-pick">{on ? '지정됨' : '이 전문가로'}</span>
        </button>
      </li>
    );
  };

  return (
    <div className="ac-card">
      <div className="ac-head">
        <span className="ac-title">
          전문가 {catalog.pool.length}명
          {catalog.query && <span className="ac-dim"> · ‘{catalog.query}’ 검색</span>}
        </span>
        <button type="button" className="ac-browse" onClick={() => setBrowse(true)}>
          조직도 열기 ⤢
        </button>
      </div>

      {catalog.recommended.length > 0 && (
        <>
          <div className="ac-sec">주제 관련 추천 {catalog.recommended.length}명</div>
          <ul className="ac-list">{catalog.recommended.map((r) => row(r.key, r.name, r.desc))}</ul>
        </>
      )}

      {(catalog.domains?.length ?? 0) > 0 && (
        <div className="ac-doms">
          {catalog.domains!.slice(0, 12).map(([code, n]) => (
            <span key={code} className="ac-dom">
              {domainLabel(code)} <b>{n}</b>
            </span>
          ))}
        </div>
      )}

      <input
        className="ac-search"
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={`전체 ${catalog.pool.length}명에서 이름·키로 찾기`}
        aria-label="전문가 검색"
      />
      {q.trim() &&
        (hits.length === 0 ? (
          <p className="ac-empty">일치 없음 — 조직도에서 분야별로 훑어보세요.</p>
        ) : (
          <ul className="ac-list">{hits.map((a) => row(a.key, a.name))}</ul>
        ))}

      <p className="ac-note">
        고르면 이 대화의 이후 발화가 그 전문가 페르소나로 흐릅니다. 오른쪽 <b>현재 전문가</b> 칸에서
        언제든 바꾸거나 해제할 수 있습니다.
      </p>

      {browse && <PersonaBrowser onClose={() => setBrowse(false)} />}
    </div>
  );
}
