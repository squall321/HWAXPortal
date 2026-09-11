export interface User {
  subject: string;
  email: string;
  display_name: string | null;
  groups: string[];
  department?: string;
  /** 소속(관리자 지정) — docs/access-control. */
  affiliation?: string;
  /** 요청 시점 권한 키(feat:·plat:). 없으면(옛 백엔드) 권한 모델 이전이라 모두 허용으로 본다. */
  entitlements?: string[];
}

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';
