// 권한 확인 훅 — 메뉴·입구를 권한 없으면 아예 숨긴다(백엔드가 한 번 더 막는다, docs/access-control)
import { useCallback } from 'react';
import { useAuth } from './useAuth';

/** can('feat:deliberation') — /auth/me 가 준 요청 시점 권한으로 판정한다.
 *  entitlements 가 없으면(권한 모델 이전 백엔드) 막지 않는다 — 옛 서버에서 메뉴가 통째로 사라지지 않게. */
export function useCan(): (key: string) => boolean {
  const { user } = useAuth();
  const ents = user?.entitlements;
  return useCallback((key: string) => !ents || ents.includes(key), [ents]);
}
