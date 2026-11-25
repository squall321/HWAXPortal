// 상호작용 기록 박스 상태 훅 — 켜진 박스에서만 메뉴 · 알림 문구를 그리게(꺼지면 null, docs/interaction-data contract §1 · §7)
import { useEffect, useState } from 'react';
import { fetchInteractionStatus, type InteractionStatus } from '../api/interactions.api';

/** 로그인한 사람에게만 묻는다(user 가 없으면 묻지 않는다). 한 탭에 한 번 — fetchInteractionStatus 가 약속을 나눠 쓴다. */
export function useInteractionStatus(loggedIn: boolean): InteractionStatus | null {
  const [st, setSt] = useState<InteractionStatus | null>(null);
  useEffect(() => {
    if (!loggedIn) return;
    let live = true;
    void fetchInteractionStatus().then((s) => live && setSt(s));
    return () => {
      live = false;
    };
  }, [loggedIn]);
  return st;
}
