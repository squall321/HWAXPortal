// 배선 요청·설정 — **안 되어 있으면 여기서 말한다.** 다 되면 아무것도 안 그린다
//
// 이 스택에서 반복된 실패 모양이 "설정 한 줄이 빠졌는데 아무 데도 안 보인다" 였다.
// 배포는 성공하고 화면도 멀쩡한데 그 기능만 조용히 안 되는 식이라, 며칠 뒤 사용자가
// "왜 안 되죠" 로 발견한다. 그래서 홈에 둔다 — 안 본 곳에 적어 두는 것은 안 적은 것과 같다.
import { useEffect, useState } from 'react';
import { listSetupRequests, type SetupRequest } from '../../api/setup.api';

const SEV_LABEL: Record<string, string> = {
  blocker: '필수',
  important: '권장',
  request: '요청',
};
const STATE_LABEL: Record<string, string> = {
  todo: '안 되어 있음',
  manual: '확인 필요',
  unknown: '확인 못 함',
};
// "기본값이 들어가나" — 사람이 반드시 손대야 하는 것과 그냥 한 번 돌리면 되는 것을 가른다.
// 이 구분이 없으면 목록 전체가 "다 내가 해야 하는 일" 로 보여서 아무도 시작하지 않는다.
const DEFAULT_LABEL: Record<string, string> = {
  auto: '기본값 있음',
  generate: '없으면 생성됨',
  none: '값을 정해야 함',
};

export function SetupRequests() {
  const [items, setItems] = useState<SetupRequest[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    listSetupRequests().then(setItems).catch(() => setItems([]));
  }, []);

  if (!items || items.length === 0) return null;    // 다 됐으면 조용히 사라진다

  const blockers = items.filter((i) => i.severity === 'blocker').length;
  return (
    <section className="setup-requests" aria-label="배선 설정">
      <header>
        <strong>배선 설정 {items.length}건</strong>
        {blockers > 0 && <span className="sev sev-blocker">필수 {blockers}</span>}
        <span className="hint">다 되면 이 상자는 사라집니다.</span>
      </header>
      <ul>
        {items.map((it) => (
          <li key={it.id} className={`sev-${it.severity}`}>
            <button type="button" onClick={() => setOpen(open === it.id ? null : it.id)}>
              <span className={`sev sev-${it.severity}`}>{SEV_LABEL[it.severity] ?? it.severity}</span>
              <span className="title">{it.title}</span>
              {it.tag && <span className="tag">{it.tag}</span>}
              <span className={`dflt dflt-${it.default}`}>{DEFAULT_LABEL[it.default] ?? ''}</span>
              <span className="state">{STATE_LABEL[it.state] ?? it.state}</span>
            </button>
            {open === it.id && <pre className="body">{it.body}</pre>}
          </li>
        ))}
      </ul>
    </section>
  );
}
