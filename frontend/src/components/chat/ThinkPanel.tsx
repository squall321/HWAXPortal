// Thinking 모드 토글 — (화면 이름은 영문 "Thinking". 한글 음차 "띵킹" 은 쓰지 않는다) 켜면 질문이 전문가 풀로 가고 답할 수 있는 좌석만 각자 답한다(회의 아님)
import { useChat } from '../../state/ChatContext';

export function ThinkPanel() {
  const { thinking, setThinking } = useChat();

  return (
    <details className="do-panel">
      <summary className="do-summary">
        <span className="do-gear" aria-hidden="true">🧠</span>
        Thinking 모드
        {thinking ? (
          <span className="do-count">켜짐</span>
        ) : (
          <span className="do-count do-count-off">꺼짐</span>
        )}
      </summary>
      <div className="do-body">
        <p className="do-note">
          질문을 전문가 <b>781명</b> 풀에 돌려, <b>답할 수 있는 사람만 각자 답합니다.</b> 소관이
          아닌 전문가는 억지로 답하지 않고 넘길 곳을 지목하며, 그 지목을 따라 한 번 더 소집합니다.
        </p>
        <ul className="do-list">
          <li className="do-item">
            <label className="do-toggle">
              <input type="checkbox" checked={thinking} onChange={() => setThinking(!thinking)} />
              <span className="do-label">켜기</span>
            </label>
            <span className="do-hint">
              끄기 전까지 <b>모든 발화</b>에 적용됩니다. 이 턴만 심의를 부르고 싶으면 그냥
              <code> /심의 </code> 로 시작하세요 — 명시한 쪽이 이깁니다.
            </span>
          </li>
        </ul>
        <p className="do-note">
          <b>심의와 다릅니다.</b> 회의도 반박도 표결도 없고 의장 결정문도 없습니다. 각자의 답을
          그대로 듣습니다. 대신 답이 하나로 정리되지는 않습니다 — 결론이 필요하면 심의를 쓰세요.
        </p>
        <p className="do-note">
          아무도 답하지 못하면 <b>그렇게 말합니다.</b> 그럴듯한 오답 대신 &ldquo;이 주제를 맡을
          전문가가 풀에 없다&rdquo;를 받는 것이 이 모드의 값입니다.
        </p>
      </div>
    </details>
  );
}
