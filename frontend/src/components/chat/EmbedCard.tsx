// 뷰어 카드 — 도구가 준 같은 출처 /apps/<앱>/… 화면을 답 아래 격리 창(sandbox="allow-scripts")으로 띄운다(docs/chat-embeds)
import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import { isEmbedPath } from '../../state/chatStore';
import type { EmbedPointer } from '../../types/chat';

/** 한 답의 뷰어 카드들 — 이 탭이 받은 것(live)은 연 채로, 기록에서 온 것은 접힌 채(옛 대화를 열 때 창 여럿을 한꺼번에 띄우지 않게). */
export function EmbedCards({ embeds, live }: { embeds: EmbedPointer[]; live: boolean }) {
  // 그리기 직전에 한 번 더 거른다 — 브라우저 사본은 사람이 고칠 수 있다(규칙은 chatStore.isEmbedPath · docs/chat-embeds PLAN 1절)
  const list = embeds.filter((e) => isEmbedPath(e.url)).slice(0, 8);
  if (!list.length) return null;
  return (
    <div className="embed-cards">
      {list.map((e) => (
        <EmbedCard key={e.url} embed={e} startOpen={live} />
      ))}
    </div>
  );
}

function EmbedCard({ embed, startOpen }: { embed: EmbedPointer; startOpen: boolean }) {
  const [open, setOpen] = useState(startOpen);
  const [ready, setReady] = useState(false);
  const [tall, setTall] = useState(false);

  // 창 이동은 포털의 15분 세션 재발급(apiFetch 의 /auth/refresh)을 못 탄다 — 허브 Caddy 가 로그인 쿠키를 보므로 낡았으면 빈 창이다(11-01 RA 카드와
  // 같은 까닭). 처음 열 때 인증 경로를 한 번 불러 쿠키를 새로 한 뒤 창을 띄운다. 실패해도 띄운다(빈 창이면 머리의 '새 탭' 이 있다).
  useEffect(() => {
    if (!open || ready) return;
    let alive = true;
    apiFetch('/auth/me')
      .catch(() => undefined)
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, [open, ready]);

  return (
    <div className={`embed-card${open ? ' is-open' : ''}`}>
      <div className="embed-head">
        <span className="embed-app">{embed.app}</span>
        <span className="embed-title" title={embed.title}>
          {embed.title}
        </span>
        <span className="embed-spacer" />
        {open && (
          <button type="button" className="embed-btn" onClick={() => setTall((t) => !t)} aria-pressed={tall}>
            {tall ? '작게' : '크게'}
          </button>
        )}
        <a className="embed-btn" href={embed.url} target="_blank" rel="noopener noreferrer" title="새 탭에서 열기">
          새 탭
        </a>
        <button type="button" className="embed-btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          {open ? '접기' : '열기'}
        </button>
      </div>
      {open && ready && (
        // ⚠ sandbox 는 allow-scripts 하나 — 허브 앱은 포털과 같은 출처라 allow-same-origin 을 주면 앱 스크립트가 포털 쿠키 · 저장소에 닿는다(CE-2).
        //   그래서 쿠키로 API 를 부르는 뷰어는 이 창에서 돌지 않는다 — 에이전트 서버가 혼자 도는 뷰어만 카드로 낸다.
        <iframe
          className={`embed-frame${tall ? ' is-tall' : ''}`}
          sandbox="allow-scripts"
          src={embed.url}
          referrerPolicy="no-referrer"
          loading="lazy"
          title={embed.title}
        />
      )}
    </div>
  );
}
