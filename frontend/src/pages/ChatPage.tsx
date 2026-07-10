// 챗을 메인 콘텐츠로 전면 배치하는 페이지 — 데이터 업로드/질의의 기본 진입점
import { useAuth } from '../auth/useAuth';
import { useChat } from '../state/ChatContext';
import { MessageList } from '../components/chat/MessageList';
import { Composer } from '../components/chat/Composer';
import '../styles/chat.css';
import '../styles/chatpage.css';

export default function ChatPage() {
  const { user } = useAuth();
  const { messages } = useChat();

  return (
    <div className="chatpage">
      <div className="chatpage-head">
        <span className="chatpage-kicker">HWAX ASSISTANT</span>
        <h1 className="chatpage-title">데이터를 올리거나 물어보세요</h1>
        <p className="chatpage-sub">
          {user?.display_name ? `${user.display_name}님, ` : ''}
          요청을 이해해 알맞은 플랫폼으로 연결하고 결과를 대화로 돌려드립니다.
        </p>
      </div>
      <div className="chatpage-conv">
        <MessageList messages={messages} />
        <Composer />
      </div>
    </div>
  );
}
