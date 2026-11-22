// 입력창 도구 줄의 'Claude 모델 · 생각 깊이' 칸 — 웹 챗이 Claude 로 답하는 사람에게만 보이고, 고른 값은 이 브라우저에 기억한다(docs/chat-llm-claude CC-8)
import { useEffect, useState } from 'react';
import { fetchChatModels, type ChatModels } from '../../api/chat.api';
import { claudePick, saveClaudePick, setClaudeCaps } from './claudePick';

const EFFORT_LABEL: Record<string, string> = {
  low: '생각 낮음',
  medium: '생각 보통',
  high: '생각 높음',
  xhigh: '생각 매우 높음',
  max: '생각 최대',
};

const HELP =
  '이 대화의 답을 낼 Claude 모델과 생각 깊이입니다. 깊을수록 오래 생각하고 비용이 큽니다. ' +
  '고른 값은 이 브라우저에 기억되고, 답 아래에 실제로 답한 모델과 깊이가 보입니다.';

export function ClaudePicker() {
  const [caps, setCaps] = useState<ChatModels['claude'] | null>(null);
  const [pick, setPick] = useState<{ model: string; effort: string } | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    void fetchChatModels(ac.signal)
      .then((r) => {
        setClaudeCaps(r.claude);
        setCaps(r.claude);
        setPick(claudePick());
      })
      .catch(() => {
        setClaudeCaps(null); // 목록을 못 받으면 칸을 그리지 않는다 — 보낼 때 고른 값을 싣지 않고 박스 기본으로 돈다
      });
    return () => ac.abort();
  }, []);

  if (!caps?.eligible || !pick) return null;
  const models = caps.models ?? [];
  const efforts = caps.efforts ?? [];
  const change = (model: string, effort: string) => {
    saveClaudePick(model, effort);
    setPick({ model, effort });
  };
  return (
    <span className="tool-pill claude-pick" title={HELP}>
      {models.length > 1 ? (
        <select
          className="claude-pick-select"
          aria-label="답할 Claude 모델"
          value={pick.model}
          onChange={(e) => change(e.target.value, pick.effort)}
        >
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      ) : (
        <span>{models[0]?.label ?? pick.model}</span>
      )}
      {efforts.length > 1 && (
        <select
          className="claude-pick-select"
          aria-label="생각 깊이"
          value={pick.effort}
          onChange={(e) => change(pick.model, e.target.value)}
        >
          {efforts.map((x) => (
            <option key={x} value={x}>
              {EFFORT_LABEL[x] ?? x}
            </option>
          ))}
        </select>
      )}
    </span>
  );
}
