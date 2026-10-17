// 대화 메시지 목록 — 클로드 스타일(어시스턴트 좌측 와이드/유저 버블), 스티키 자동 스크롤 + 하단 이동 버튼
import { useEffect, useRef, useState } from 'react';
import { friendlyError } from '../../lib/chatErrors';
import { useChat } from '../../state/ChatContext';
import type { Message, TurnMeta } from '../../types/chat';
import { copyText } from './clipboard';
import { AgentCatalogBlock } from './AgentCatalogBlock';
import { DelibView } from './DelibView';
import { ThinkView } from './ThinkView';
import { ToolCatalogBlock } from './ToolCatalogBlock';
import { IconArrowDown, IconCheck, IconCopy } from './icons';
import { colorOf, initialOf, shortName } from './personaColor';
import { StreamPulse } from './StreamPulse';
import { TextBlock } from './renderers/TextBlock';
import { Figure } from './renderers/Figure';
import { config } from '../../config';

function ErrorBlock({ raw }: { raw: string }) {
  const { retryLast, streaming } = useChat();
  const { title, hint, retry } = friendlyError(raw);
  return (
    <div className="chat-error">
      <div className="chat-error-title">⚠ {title}</div>
      {hint && <div className="chat-error-hint">{hint}</div>}
      {retry && (
        <button type="button" className="chat-error-retry" onClick={retryLast} disabled={streaming}>
          다시 시도
        </button>
      )}
    </div>
  );
}

function CopyAction({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = () => {
    void copyText(text).then((ok) => {
      if (!ok) return;
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button type="button" className="msg-copy" onClick={onCopy} aria-label="응답 복사">
      {copied ? <IconCheck width={14} height={14} /> : <IconCopy width={14} height={14} />}
      <span>{copied ? '복사됨' : '복사'}</span>
    </button>
  );
}

/** 그 발화에 올린 그림 — 서버 주소(images)가 오면 그것(포털 프록시가 낸다), 오기 전엔 보낼 때의 썸네일(localImages). */
function UserImages({ msg }: { msg: Message }) {
  const srcs = msg.images?.length ? msg.images.map((u) => `${config.apiBase}${u}`) : (msg.localImages ?? []);
  if (!srcs.length) return null;
  return (
    <div className="msg-images">
      {srcs.map((src, i) => (
        <Figure key={`${i}-${src.slice(-24)}`} src={src} alt={`올린 그림 ${i + 1}`} />
      ))}
    </div>
  );
}

function Row({ msg }: { msg: Message }) {
  if (msg.role === 'user') {
    return (
      <div className="msg user">
        <div className="msg-bubble">
          <TextBlock text={msg.text} />
        </div>
        <UserImages msg={msg} />
      </div>
    );
  }

  // 심의 메시지는 구조화 라이브 뷰(스테퍼·회의·수렴)로 — 텍스트 스트림 대신 DelibView 가 본문.
  const hasDelib = Boolean(msg.delib && (msg.delib.stages?.length || msg.delib.turns?.length));
  // 띵킹 메시지도 마찬가지 — 좌석이 하나라도 소집되면 ThinkView 가 본문이다.
  const hasThink = Boolean(msg.think?.seats?.length);

  // ⚠ 이 지역 변수의 뜻은 '스트리밍 중인데 아직 내용이 없다' 이지 띵킹 모드가 아니다.
  //   이름이 겹치므로 헷갈리지 말 것(모드 쪽은 hasThink).
  const thinking = Boolean(msg.streaming) && !msg.text && !hasDelib && !hasThink;
  // A finished assistant turn with no text/error (e.g. the model only called a tool
  // and produced no closing text) would otherwise render empty — show a fallback.
  const emptyDone =
    !msg.streaming && !msg.text && !msg.error && !msg.status && !hasDelib && !hasThink &&
    !msg.toolCatalog && !msg.agentCatalog;

  // 페르소나 말풍선 — 지정 전문가로 보낸 발화의 답이면 심의 회의록처럼 '누가 말했는지'를 세운다.
  // 심의·띵킹 메시지에는 붙이지 않는다 — 그쪽은 좌석마다 자기 버블을 이미 그린다.
  const persona = !hasDelib && !hasThink ? msg.persona : undefined;
  const who = persona ? persona.name || persona.key : '';

  return (
    <div className={`msg assistant${persona ? ' is-persona' : ''}`}>
      {persona && (
        <div className="msg-who">
          <span className="msg-av" style={{ background: colorOf(who) }} aria-hidden="true">
            {initialOf(who)}
          </span>
          <span className="msg-who-name" title={who}>{shortName(who)}</span>
          <span className="msg-who-key">{persona.key}</span>
        </div>
      )}
      <div
        className="msg-content"
        style={persona ? { borderLeftColor: colorOf(who) } : undefined}
      >
        {/* 챗 서버의 생각 글 — 접힌 칸. 답이 나오기 전엔 '생각 중' 으로(1~2분 동안 화면이 멈춰 보이지 않게, docs/chat-depth-context C2). */}
        {msg.reasoning && <ReasoningBlock text={msg.reasoning} live={Boolean(msg.streaming) && !msg.text} />}
        {hasDelib ? (
          <DelibView msg={msg} />
        ) : hasThink ? (
          <ThinkView msg={msg} />
        ) : (
          msg.text && <TextBlock text={msg.text} cursor={Boolean(msg.streaming)} />
        )}
        {/* 도구 카탈로그('/도구' 검색) — 사용자가 직접 선택·변경해 지정 도구로 확정하는 카드. */}
        {msg.toolCatalog && <ToolCatalogBlock catalog={msg.toolCatalog} />}
        {/* 전문가 카탈로그('/전문가' 검색) — 도구와 같은 대우. 여기서 바로 페르소나를 지정한다. */}
        {msg.agentCatalog && <AgentCatalogBlock catalog={msg.agentCatalog} />}
        {/* 토큰이 흐른 뒤에도 도구 호출 등으로 status가 다시 올 수 있다 — 텍스트 아래에 표시. */}
        {msg.text && msg.status && <div className="msg-status-text">{msg.status}</div>}
        {thinking && (
          <div className="msg-thinking" aria-label="응답 생성 중">
            {msg.status ? (
              <span className="msg-status-text">{msg.status}</span>
            ) : (
              <span className="typing-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            )}
          </div>
        )}
        {/* 도는 턴 아래의 생존 표시 — 진행이 멎었을 때만 말한다(살아 있음 / 신호 없음). 스트림은 끊지 않는다. */}
        {msg.streaming && <StreamPulse />}
        {emptyDone && <div className="msg-status-text">(응답이 없습니다)</div>}
        {msg.warn && (
          <div className="msg-warn" role="status">⚠ {msg.warn}</div>
        )}
        {msg.error && <ErrorBlock raw={msg.error} />}
      </div>
      {!msg.streaming && msg.text && (
        <div className="msg-actions">
          <CopyAction text={msg.text} />
          {msg.meta && <ModelBadge meta={msg.meta} />}
        </div>
      )}
    </div>
  );
}

/** 챗 서버의 생각 글 — 접어 둔다(수만 자일 수 있다). 도는 동안은 '생각 중 · N자' 로 진행만 보인다. */
function ReasoningBlock({ text, live }: { text: string; live: boolean }) {
  return (
    <details className="msg-reasoning">
      <summary>{live ? '생각 중' : '생각'} · {text.length.toLocaleString()}자</summary>
      <div className="msg-reasoning-body">{text}</div>
    </details>
  );
}

/** 이 턴에 답한 모델 · 생각 설정 — 넘김(챗 서버 → GLM)이 섞였으면 그렇게 말한다(같은 질문에 답의 깊이가 달라진다, C3). */
function ModelBadge({ meta }: { meta: TurnMeta }) {
  const names = Object.keys(meta.models ?? {});
  if (!names.length) return null;
  const main = meta.chat_model && names.includes(meta.chat_model) ? meta.chat_model : names[0];
  const others = names.filter((n) => n !== main);
  const effort = meta.thinking ? ` · 생각 ${meta.effort ?? '켬'}` : meta.thinking === false ? ' · 생각 끔' : '';
  const label = `${main}${effort}${others.length ? ` · 넘김 ${others.map((n) => `${n} ${meta.models[n]}회`).join(', ')}` : ''}`;
  return <span className="msg-model" title="이 답을 낸 모델(호출 수)">{label}</span>;
}

export function MessageList({ messages }: { messages: Message[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  // Auto-scroll only when the user is already near the bottom, so streaming tokens don't
  // yank the view down while they're scrolled up reading earlier messages.
  const stickRef = useRef(true);
  const [stuck, setStuck] = useState(true);

  const onScroll = () => {
    const el = bodyRef.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    stickRef.current = near;
    setStuck(near);
  };

  useEffect(() => {
    if (stickRef.current) endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  const jumpToEnd = () => {
    stickRef.current = true;
    setStuck(true);
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  };

  return (
    <div className="msg-wrap">
      <div className="chat-body" ref={bodyRef} onScroll={onScroll}>
        <div className="chat-col">
          {messages.length === 0 && (
            <div className="msg assistant">
              <div className="msg-content">
                <TextBlock text="무엇을 도와드릴까요?" />
              </div>
            </div>
          )}
          {messages.map((m) => (
            <Row key={m.id} msg={m} />
          ))}
          <div ref={endRef} />
        </div>
      </div>
      {!stuck && (
        <button type="button" className="msg-jump" onClick={jumpToEnd} aria-label="맨 아래로 이동">
          <IconArrowDown width={15} height={15} />
        </button>
      )}
    </div>
  );
}
