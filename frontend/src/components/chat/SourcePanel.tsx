// 인터넷 소스 토글 — 켠 소스의 도구만 서버가 바인딩한다(끄면 모델의 도구 목록에 아예 없다).
import { useChat } from '../../state/ChatContext';
import type { SearchSource } from '../../types/chat';

// 소스마다 나가는 곳도, 필요한 승인도, 위험도도 다르다. 한 스위치로 묶으면 일반 웹 승인이
// 안 난 동안 공공 학술까지 못 쓴다 — 그래서 따로 켠다.
const SOURCES: { key: SearchSource; label: string; hint: string; approval?: string }[] = [
  {
    key: 'scholar',
    label: '공공 학술',
    hint: 'arXiv·Crossref·OpenAlex·PubMed 에서 논문을 찾습니다. 무인증·약관 허용 범위입니다.',
  },
  {
    key: 'web',
    label: '일반 웹',
    hint: '검색엔진으로 일반 문서를 찾습니다.',
    approval: '보안 승인 전까지 서버가 차단합니다 — 켜도 나가지 않습니다.',
  },
];

export function SourcePanel() {
  const { searchSources, setSearchSources } = useChat();
  const on = new Set(searchSources);

  const toggle = (k: SearchSource) => {
    const next = new Set(on);
    if (next.has(k)) next.delete(k);
    else next.add(k);
    setSearchSources([...next]);
  };

  return (
    <details className="do-panel">
      <summary className="do-summary">
        <span className="do-gear" aria-hidden="true">🌐</span>
        인터넷 검색
        {on.size > 0 ? (
          <span className="do-count">{on.size}개 켜짐</span>
        ) : (
          <span className="do-count do-count-off">꺼짐</span>
        )}
      </summary>
      <div className="do-body">
        <p className="do-note">
          끄면 해당 도구가 <b>모델에게 전달되지 않습니다</b> — 쓰지 말라는 지시가 아니라 부재입니다.
          나간 질의는 전량 기록됩니다.
        </p>
        <ul className="do-list">
          {SOURCES.map((s) => (
            <li className="do-item" key={s.key}>
              <label className="do-toggle">
                <input type="checkbox" checked={on.has(s.key)} onChange={() => toggle(s.key)} />
                <span className="do-label">{s.label}</span>
              </label>
              <span className="do-hint">
                {s.hint}
                {s.approval && <b className="do-warn"> {s.approval}</b>}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
