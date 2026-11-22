// 웹 챗 Claude 의 고른 모델 · 생각 깊이 — 이 브라우저에 기억하고, 보내는 순간 목록 안의 값만 싣는다(docs/chat-llm-claude CC-8)
import type { ChatModels } from '../../api/chat.api';

const KEY_MODEL = 'hwax.claude.model';
const KEY_EFFORT = 'hwax.claude.effort';

// 서버가 준 목록(고를 수 있는 사람이면) — 입력창 칸이 받아 두고, 보내는 쪽(ChatContext)이 읽는다. 목록을 받기 전 · 대상이 아니면 null.
let caps: ChatModels['claude'] | null = null;

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // 사생활 창 · 막힌 저장소 — 기억하지 못할 뿐 기본으로 돈다
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch {
    /* 기억하지 못할 뿐이다 */
  }
}

export function setClaudeCaps(c: ChatModels['claude'] | null): void {
  caps = c && c.eligible ? c : null;
}

/** 지금 고른 값(목록 밖이거나 기억이 없으면 박스 기본). 고를 수 없는 사람이면 null. */
export function claudePick(): { model: string; effort: string } | null {
  if (!caps?.eligible) return null;
  const models = (caps.models ?? []).map((m) => m.id);
  const efforts = caps.efforts ?? [];
  const m = read(KEY_MODEL);
  const e = read(KEY_EFFORT);
  return {
    model: m && models.includes(m) ? m : (caps.default_model ?? models[0] ?? ''),
    effort: e && efforts.includes(e) ? e : (caps.default_effort ?? efforts[0] ?? ''),
  };
}

export function saveClaudePick(model: string, effort: string): void {
  write(KEY_MODEL, model);
  write(KEY_EFFORT, effort);
}
