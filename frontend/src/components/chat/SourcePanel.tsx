// 인터넷 검색 토글 — 입력창 도구 줄의 알약 + 위로 열리는 소스 선택. 켠 소스의 도구만 서버가 바인딩한다(끄면 모델의 도구 목록에 아예 없다)
import { useEffect, useId, useRef, useState } from 'react';
import { fetchSearchCapability } from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import type { SearchSource } from '../../types/chat';
import { IconChevronDown, IconGlobe } from './icons';

// 소스마다 나가는 곳도, 필요한 승인도, 위험도도 다르다. 한 스위치로 묶으면 일반 웹 승인이
// 안 난 동안 공공 학술까지 못 쓴다 — 그래서 따로 켠다.
const SOURCES: { key: SearchSource; label: string; hint: string; approval?: string }[] = [
  {
    key: 'scholar',
    label: '공공 학술',
    hint: 'arXiv·Crossref·OpenAlex·PubMed 에서 논문을 찾습니다. 무인증·약관 허용 범위입니다.',
  },
  {
    key: 'web',
    label: '일반 웹',
    hint: '검색엔진으로 일반 문서를 찾습니다.',
    approval: '보안 승인 전까지 서버가 차단합니다 — 켜도 나가지 않습니다.',
  },
];

export function SearchToggle() {
  const { searchSources, setSearchSources } = useChat();
  const on = new Set(searchSources);
  // 서버가 그 소스를 실제로 제공하는가. 전역이 꺼져 있으면 켤 수 없게 해야 한다 —
  // 켤 수 있는데 안 나가면 사용자는 도구가 고장났다고 생각한다.
  const [avail, setAvail] = useState<Record<string, boolean> | null>(null);
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    const ac = new AbortController();
    void fetchSearchCapability(ac.signal)
      .then((c) => setAvail(Object.fromEntries(
        Object.entries(c.sources ?? {}).map(([k, v]) => [k, !!v?.available]))))
      .catch(() => setAvail({}));
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        btn.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const toggle = (k: SearchSource) => {
    const next = new Set(on);
    if (next.has(k)) next.delete(k);
    else next.add(k);
    setSearchSources([...next]);
  };
  const active = SOURCES.filter((s) => on.has(s.key) && !(avail && !avail[s.key]));

  return (
    <div className="tool-wrap" ref={root}>
      <button
        ref={btn}
        type="button"
        className={`tool-pill${active.length ? ' is-on' : ''}`}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        title="인터넷 검색 — 켠 소스의 검색 도구만 모델에게 전달됩니다"
        onClick={() => setOpen((o) => !o)}
      >
        <IconGlobe width={15} height={15} />
        {active.length ? active.map((s) => s.label).join('·') : '검색'}
        <IconChevronDown width={13} height={13} className="tool-chev" />
      </button>
      {open && (
        <div className="tool-pop" id={id} role="dialog" aria-label="인터넷 검색 소스">
          <p className="tool-pop-title">인터넷 검색</p>
          <ul className="tool-pop-list">
            {SOURCES.map((s) => {
              const off = !!avail && !avail[s.key];
              return (
                <li key={s.key}>
                  <label className={`tool-opt${off ? ' is-off' : ''}`}>
                    <input type="checkbox" checked={on.has(s.key) && !off} disabled={off} onChange={() => toggle(s.key)} />
                    <span>
                      <b>{s.label}</b>
                      <span className="tool-opt-hint">
                        {s.hint}
                        {off && <em> 서버가 이 소스를 제공하지 않아 켤 수 없습니다.</em>}
                        {s.approval && avail?.[s.key] && <em> {s.approval}</em>}
                      </span>
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
          <p className="tool-pop-note">
            끄면 해당 도구가 모델에게 <b>전달되지 않습니다</b>(쓰지 말라는 지시가 아니라 부재). 나간 질의는 전량 기록됩니다.
          </p>
        </div>
      )}
    </div>
  );
}
