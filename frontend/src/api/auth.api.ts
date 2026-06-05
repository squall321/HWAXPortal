import type { User } from '../auth/types';
import { apiFetch } from './client';

export async function getMe(): Promise<User | null> {
  const res = await apiFetch('/auth/me');
  if (res.ok) return (await res.json()) as User;
  return null;
}

export async function postLogout(): Promise<void> {
  await apiFetch('/auth/logout', { method: 'POST' });
}
