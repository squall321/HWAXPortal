export interface User {
  subject: string;
  email: string;
  display_name: string | null;
  groups: string[];
}

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';
