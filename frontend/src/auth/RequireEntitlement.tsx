// 권한 라우트 가드 — 권한이 없으면 페이지 대신 '내 권한'으로 보낸다(무엇이 없는지 표시)
import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useCan } from './useCan';

/** `need` 가 여럿이면 **하나만 있어도** 연다 — 한 페이지가 여러 권한의 살림을 같이 이고 있는
 *  경우가 있다(예: /tokens 는 PAT 발급과 Report Archive 연결·조직 선택을 함께 담는다).
 *  없는 권한으로 튕길 때는 첫 번째 것을 이유로 보여 준다. */
export function RequireEntitlement({ need, children }: { need: string | string[]; children: ReactNode }) {
  const can = useCan();
  const keys = Array.isArray(need) ? need : [need];
  if (!keys.some((k) => can(k))) {
    return <Navigate to={`/access?need=${encodeURIComponent(keys[0])}`} replace />;
  }
  return <>{children}</>;
}
