// Thinking 모드 토글 — 입력창 도구 줄의 알약(화면 이름은 영문 "Thinking". 한글 음차 "띵킹" 은 쓰지 않는다). 켜면 질문이 전문가 풀로 가고 답할 수 있는 좌석만 각자 답한다(회의 아님)
import { useChat } from '../../state/ChatContext';
import { IconLightbulb } from './icons';

const HELP =
  '켜면 질문을 전문가 풀에 돌려 답할 수 있는 사람만 각자 답합니다(회의·표결·결정문 없음 — 결론이 필요하면 심의). ' +
  '아무도 못 답하면 그렇다고 말합니다. 끄기 전까지 모든 발화에 적용되고, 이 턴만 심의하려면 /심의 로 시작하세요.';

export function ThinkToggle() {
  const { thinking, setThinking } = useChat();
  return (
    <button
      type="button"
      className={`tool-pill${thinking ? ' is-on' : ''}`}
      aria-pressed={thinking}
      title={HELP}
      onClick={() => setThinking(!thinking)}
    >
      <IconLightbulb width={15} height={15} />
      Thinking
    </button>
  );
}
