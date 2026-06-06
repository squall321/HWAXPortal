import { apiFetch } from './client';

export type IntegrationType = 'external-url' | 'proxy' | 'jwt-handoff' | 'saml-handoff';
export type Accent = 'violet' | 'cyan' | 'amber' | 'emerald' | 'sky' | 'rose' | 'indigo';
export type SystemStatus = 'available' | 'coming_soon';

export interface SystemTile {
  id: string;
  name: string;
  description: string | null;
  tagline: string | null;
  icon: string | null;
  accent: Accent;
  category: string | null;
  status: SystemStatus;
  integration_type: IntegrationType;
  url: string | null; // present only for external-url tiles
}

export async function listSystems(): Promise<SystemTile[]> {
  const res = await apiFetch('/systems');
  if (!res.ok) throw new Error('Failed to load systems');
  return (await res.json()) as SystemTile[];
}
