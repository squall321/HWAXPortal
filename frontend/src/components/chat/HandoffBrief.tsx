// 심의 브리프 — 챗에서 넘길 질문·목적(Job)·얹을 층·좌석을 AI가 제안하고 사용자가 확정하는 모달(핸드오프)
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  fetchDeliberateExperts,
  fetchDeliberateTopic,
  type ExpertsResponse,
  type HistoryMessage,
  type RecommendedExpert,
  type TopicSuggestion,
} from '../../api/chat.api';
import { useChat } from '../../state/ChatContext';
import type { Conversation } from '../../types/chat';
import { conversationEvidence } from './handoff';
import { SeatBrowser } from './SeatBrowser';
import { VocFirstPanel, type VocChoice } from './VocFirstPanel';
import { ClarifyPanel } from './ClarifyPanel';
import { mergeEvidence, vocEvidence } from './vocEvidence';
import { JOB_BY_ID, JOB_GROUPS, JOB_ROUTING, MODIFIERS, jobsByGroup, suggestJob, type JobId } from './delibTaxonomy';

const DEFAULT_SEATS = 6; // 추천 좌석 기본 선택 수(심의가 스파인 좌석은 자동 추가)
const MIN_SEATS = 2;  // 서버 심의는 좌석 2명 이상 필요
// ⚠ delib_opts.personas 는 백엔드에서 max_length=20 이다(routes.py). 넘겨 보내면 422 로
// 심의가 시작조차 안 된다 — 여기서 막고, 막았다는 걸 보여 준다. 엔진 MAX_REQ_SEATS 와 같아야 한다.
const MAX_SEATS = 20;

export function HandoffBrief({ conv, onClose }: { conv: Conversation; onClose: () => void }) {
  const { startHandoff, streaming } = useChat();
  const derived = useMemo(() => {
    const firstUser = conv.messages.find((m) => m.role === 'user');
    return (firstUser?.text ?? '').replace(/^\/(심의|deliberate|토의)\s*/, '').trim();
  }, [conv]);
  const evidence = useMemo(() => conversationEvidence(conv), [conv]);
  // 이 대화에서 감지된 도구 신호로 Job 제안(휴리스틱). null 이면 억지로 추천하지 않고 메뉴에서 고르게 한다.
  const suggestion = useMemo(
    () => suggestJob(evidence.map((e) => e.tool).filter(Boolean) as string[]),
    [evidence],
  );

  // 좌석 추천의 입력 — 화두 한 줄이 아니라 오간 대화 전체다. 서버가 이걸 도메인 축으로
  // 쪼갠 뒤 축마다 짧은 질의로 검색한다(통째로 임베딩에 던지면 추천이 오히려 나빠진다).
  const history = useMemo<HistoryMessage[]>(
    () =>
      conv.messages
        .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.text.trim())
        .slice(-40)
        .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.text.slice(0, 4000) })),
    [conv],
  );

  const [topic, setTopic] = useState(derived);
  // 화두는 **첫 발화가 아니라 오간 내용 전체**에서 뽑는다. 대화는 움직인다 — 처음엔 "왜 부족하냐"
  // 로 시작해도 쟁점은 "12um 로 낮출 것인가" 로 옮겨 간다. 첫 발화를 화두로 넣으면 심의가
  // 이미 지나온 자리를 다시 판다.
  //   ⚠ 실패는 **첫 발화 그대로**다(되묻기와 같은 규율). 제안이 안 되는 것보다 화면이 안
  //     열리는 것이 나쁘다. 사람이 고쳐 쓰는 칸이므로 제안은 초안일 뿐이다.
  const [suggested, setSuggested] = useState<TopicSuggestion | null>(null);
  const [topicBusy, setTopicBusy] = useState(true);
  const touched = useRef(false);            // 사람이 손대면 제안이 덮지 않는다
  const [job, setJob] = useState<JobId>(suggestion?.id ?? 'default');
  const [mods, setMods] = useState<Set<string>>(new Set());
  const [experts, setExperts] = useState<ExpertsResponse | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [browsing, setBrowsing] = useState(false); // 전창 좌석 조직도
  const [voc, setVoc] = useState<VocChoice>({ used: false, picked: [], note: '' });

  useEffect(() => {
    const ctrl = new AbortController();
    setTopicBusy(true);
    void fetchDeliberateTopic(history, derived, job, ctrl.signal).then((r) => {
      setSuggested(r);
      // 사람이 이미 고쳤으면 덮지 않는다 — 제안이 사람 입력을 지우면 최악이다.
      if (!touched.current && r.topic.trim()) setTopic(r.topic);
      setTopicBusy(false);
    });
    return () => ctrl.abort();
    // job 이 바뀌면 다시 뽑는다(무엇을 판단할지가 달라진다). history·derived 는 대화 고정.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job]);
  // 원천 근거 = 고른 VOC(앞) + 대화 근거, 합쳐 12건 — 화면 수와 실제 실릴 수가 같아야 한다.
  const vocEv = useMemo(() => vocEvidence(voc.picked), [voc.picked]);
  const { droppedConv } = useMemo(() => mergeEvidence(vocEv, evidence), [vocEv, evidence]);

  // 화두로 추천 좌석 발굴(디바운스 + 취소) — AI 제안, 사용자 확정. 상위 N석 기본 선택.
  useEffect(() => {
    const t = topic.trim();
    if (!t) {
      setExperts(null);
      return;
    }
    setLoading(true);
    const ctrl = new AbortController();
    const h = setTimeout(() => {
      void fetchDeliberateExperts(t, ctrl.signal, history)
        .then((r) => {
          setExperts(r);
          setChecked(new Set((r.recommended ?? []).slice(0, DEFAULT_SEATS).map((e) => e.key)));
        })
        .finally(() => setLoading(false));
    }, 500);
    return () => {
      clearTimeout(h);
      ctrl.abort();
    };
  }, [topic, history]);

  const rec = experts?.recommended ?? [];
  const axes = experts?.axes ?? [];

  // 좌석 색인 — 추천·후보(≈40)·전체 풀(781)을 한 곳에 모은다. `checked` 가 정본이고
  // personas 는 여기서 만든다. ⚠ 전에는 confirm 이 rec(추천 5)에서만 personas 를 만들어,
  // 풀에서 고른 좌석이 조용히 사라졌다.
  const seatIndex = useMemo(() => {
    const m = new Map<string, { key: string; name: string; role?: string }>();
    for (const e of experts?.pool ?? []) m.set(e.key, { key: e.key, name: e.name });
    for (const e of experts?.candidates ?? []) m.set(e.key, { key: e.key, name: e.name, role: e.role });
    for (const e of rec) m.set(e.key, { key: e.key, name: e.name, role: e.role });
    return m;
  }, [experts, rec]);

  // 수동 추가 검색 — 후보(관련도순)를 앞에, 전체 풀을 뒤에. 추천에 없는 좌석을 직접 앉힌다.
  const [seatQuery, setSeatQuery] = useState('');
  const searchHits = useMemo<RecommendedExpert[]>(() => {
    const q = seatQuery.trim().toLowerCase();
    if (!q) return [];
    const recKeys = new Set(rec.map((e) => e.key));
    const hit = (n: string, k: string) => n.toLowerCase().includes(q) || k.toLowerCase().includes(q);
    const out: RecommendedExpert[] = [];
    for (const e of experts?.candidates ?? []) {
      if (!recKeys.has(e.key) && hit(e.name, e.key)) out.push(e);
    }
    const have = new Set([...recKeys, ...out.map((e) => e.key)]);
    for (const e of experts?.pool ?? []) {
      if (out.length >= 25) break;
      if (!have.has(e.key) && hit(e.name, e.key)) out.push({ key: e.key, name: e.name, role: '' });
    }
    return out.slice(0, 25);
  }, [seatQuery, experts, rec]);

  // 추천 밖에서 직접 고른 좌석 — 검색창을 비워도 목록에 남아야 해제할 수 있다.
  const manual = useMemo(
    () => [...checked].filter((k) => !rec.some((e) => e.key === k)).map((k) => seatIndex.get(k)),
    [checked, rec, seatIndex],
  );

  // 조직도용 어댑터 — 여기 정본은 `checked`(키 집합)라서 조직도가 쓰는 모양으로 옮겨 준다.
  const seatSelected = useMemo(() => {
    const m: Record<string, { key: string; name: string; role: string }> = {};
    for (const k of checked) {
      const e = seatIndex.get(k);
      m[k] = { key: k, name: e?.name ?? k, role: e?.role ?? '' };
    }
    return m;
  }, [checked, seatIndex]);

  const toggle = (k: string) =>
    setChecked((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else if (n.size < MAX_SEATS) n.add(k);
      return n;
    });
  const seatFull = checked.size >= MAX_SEATS;
  const toggleMod = (id: string) =>
    setMods((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const confirm = () => {
    const t = topic.trim();
    if (!t || streaming) return;
    // 체크된 전부 — 추천이든 풀에서 직접 고른 것이든 함께 간다.
    const personas = [...checked]
      .map((k) => seatIndex.get(k))
      .filter((e): e is { key: string; name: string; role?: string } => !!e)
      .map((e) => ({ key: e.key, ...(e.role ? { role: e.role } : {}) }));
    // P4 재활용 도구(일반화) — 챗이 부른 도구가 속한 앱을 레지스트리 그룹에서 도출해 free-query 범위로
    // 넘긴다(앱 바운드, 하드코딩 0). 좌석이 같은 앱을 이어 조회해 더 파낼 수 있다. ≤3(delib_opts.apps 상한).
    const usedTools = new Set(evidence.map((e) => e.tool).filter(Boolean));
    const toolAll = experts?.tools?.all ?? [];
    const apps = [
      ...new Set(toolAll.filter((x) => usedTools.has(x.name)).map((x) => x.group).filter(Boolean)),
    ].slice(0, 3) as string[];
    const route = JOB_ROUTING[job];
    // VOC 먼저 보기 — 직접 봤으면 자동 환기를 끄고(사람이 뺀 VOC 가 다시 들어오지 않게),
    // 보강 문장은 매 라운드 구속 의견(human_note)으로.
    const extraOpts = {
      ...(route.opts ?? {}),
      ...(voc.used ? { voc: 'off' } : {}),
      ...(voc.note ? { human_note: voc.note } : {}),
    };
    startHandoff({
      topic: t,
      personas,
      trigger: route.trigger,
      ...(route.chair ? { chairTemplate: route.chair } : {}),
      ...(Object.keys(extraOpts).length ? { extraOpts } : {}),
      ...(vocEv.length ? { extraEvidence: vocEv } : {}),
      ...(mods.size ? { modifiers: [...mods] } : {}),
      ...(apps.length ? { apps } : {}),
    });
    onClose();
  };

  return (
    <div className="cx-brief-overlay" role="dialog" aria-modal="true" aria-label="심의 브리프" onClick={onClose}>
      <div className="cx-brief" onClick={(e) => e.stopPropagation()}>
        <div className="cx-brief-head">
          <strong>심의 브리프</strong>
          <span className="cx-brief-sub">AI 제안을 확인·수정하고 심의를 시작합니다</span>
          <button type="button" className="cx-brief-x" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>

        <label className="cx-brief-field">
          <span>
            질문 (편집 가능)
            {topicBusy && <em className="cx-brief-note"> · 대화를 읽어 화두를 뽑는 중…</em>}
          </span>
          <textarea value={topic} rows={3}
            onChange={(e) => { touched.current = true; setTopic(e.target.value); }} />
        </label>
        {suggested && !topicBusy && (
          <div className="cx-brief-topic">
            {suggested.why && <p className="cx-brief-why">{suggested.why}</p>}
            <div className="cx-brief-alts">
              {suggested.options.map((o) => (
                <button key={o} type="button" title="이 화두로 바꾸기"
                  onClick={() => { touched.current = true; setTopic(o); }}>{o}</button>
              ))}
              {derived && topic.trim() !== derived && (
                <button type="button" className="cx-brief-raw" title="대화에서 뽑지 않고 첫 발화 그대로"
                  onClick={() => { touched.current = true; setTopic(derived); }}>
                  ↩ 첫 발화 그대로
                </button>
              )}
            </div>
          </div>
        )}

        {/* 되묻기 — 대화에 이미 있는 건 안 묻는다(서버가 대화까지 원문 대조). 보강하면 좌석을 다시 찾는다. */}
        <ClarifyPanel topic={topic} job={job} history={history} onApply={setTopic} />

        {suggestion && (
          <div className="cx-brief-rec">
            <span className="cx-brief-rec-badge">이 대화 기반 제안</span>
            <div className="cx-brief-rec-line">
              <strong>{JOB_BY_ID[suggestion.id].name}</strong>
              <span className="cx-brief-rec-eng">{JOB_BY_ID[suggestion.id].engine}</span>
            </div>
            <p className="cx-brief-rec-why">{suggestion.why} · 다르면 아래에서 고르세요</p>
          </div>
        )}

        <div className="cx-brief-field">
          <span>무엇을 하는 심의인가 — 하나 고르세요 (산출은 결정 문서입니다)</span>
          {JOB_GROUPS.map((g) => (
            <div className="cx-jobgroup" key={g.id}>
              <div className="cx-jobgroup-label">
                <b>{g.label}</b>
                <span>{g.hint}</span>
              </div>
              <div className="cx-brief-jobs">
                {jobsByGroup(g.id).map((j) => (
                  <button
                    type="button"
                    key={j.id}
                    className={`cx-brief-job${job === j.id ? ' is-on' : ''}`}
                    onClick={() => setJob(j.id)}
                    aria-pressed={job === j.id}
                    title={`산출: ${j.out}`}
                  >
                    <span className="cx-brief-job-top">
                      <span className="cx-brief-job-name">{j.name}</span>
                      <span className="cx-brief-job-eng">{j.engine}</span>
                    </span>
                    <span className="cx-brief-job-when">{j.when}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="cx-brief-field">
          <span>얹을 층 — 선택 (여럿 가능)</span>
          <div className="cx-brief-mods">
            {MODIFIERS.map((m) => (
              <button
                type="button"
                key={m.id}
                className={`cx-brief-mod${mods.has(m.id) ? ' is-on' : ''}`}
                onClick={() => toggleMod(m.id)}
                aria-pressed={mods.has(m.id)}
                title={m.when}
              >
                {m.name}
              </button>
            ))}
          </div>
        </div>

        {/* 축 — 대화 전체를 읽고 풀의 도메인 분류에서 고른 것. 왜 이 좌석인지의 근거다.
            비어 있으면 화두 한 줄로만 추천했다는 뜻이라, 그렇게 말해 준다. */}
        {!loading && (
          <div className="cx-brief-field">
            <span>
              {axes.length
                ? `대화에서 잡은 축 ${axes.length}개 — 축마다 따로 좌석을 찾았습니다`
                : '축 없음 — 화두 한 줄로만 추천했습니다'}
            </span>
            {axes.length > 0 && (
              <div className="cx-brief-axes">
                {axes.map((a) => (
                  <div key={a.domain} className="cx-brief-axis">
                    <span className="cx-brief-axis-dom">{a.domain}</span>
                    <span className="cx-brief-axis-phrase">{a.phrase}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 추천은 관련도가 낮아도 늘 채워 내놓는다 — 서버가 '자신 없음'을 말하면 화면이 그대로
            옮겨야 한다. ExpertPicker 에만 있고 여기엔 없어서, 같은 실수를 브리프 경로에서는
            계속 할 수 있었다. */}
        {!loading && experts?.low_confidence && (
          <p className="cx-brief-lowconf">
            이 주제를 맡을 전문가가 풀에 없을 수 있습니다 — 아래 추천은 관련도가 낮습니다.
            조직도에서 직접 고르시거나, 질문을 더 구체적인 용어로 바꿔 보세요.
          </p>
        )}

        <div className="cx-brief-field">
          <span className="cx-brief-seatlabel">
            좌석 제안{' '}
            {loading
              ? '(발굴 중…)'
              : `— ${checked.size}/${MAX_SEATS}석 선택${seatFull ? ' · 가득' : ''} · 심의가 스파인 좌석 자동 추가`}
            {!loading && experts?.pool?.length ? (
              <button type="button" className="cx-brief-browse" onClick={() => setBrowsing(true)}>
                🗂 조직도에서 고르기
              </button>
            ) : null}
          </span>
          <div className="cx-brief-seats">
            {rec.map((e) => (
              <label key={e.key} className="cx-brief-seat">
                <input
                  type="checkbox"
                  checked={checked.has(e.key)}
                  disabled={seatFull && !checked.has(e.key)}
                  onChange={() => toggle(e.key)}
                />
                <span className="cx-brief-seat-name">{e.name}</span>
                {e.axes?.length ? (
                  <span className="cx-brief-seat-axis">{e.axes.join(' · ')}</span>
                ) : null}
                {e.why && <span className="cx-brief-seat-why">{e.why}</span>}
              </label>
            ))}
            {manual.map((e) =>
              e ? (
                <label key={e.key} className="cx-brief-seat">
                  <input type="checkbox" checked onChange={() => toggle(e.key)} />
                  <span className="cx-brief-seat-name">{e.name}</span>
                  <span className="cx-brief-seat-axis">직접 추가</span>
                </label>
              ) : null,
            )}
            {!loading && rec.length === 0 && manual.length === 0 && (
              <span className="cx-brief-empty">추천 좌석 없음 — 심의가 자동 발굴합니다</span>
            )}
          </div>

          {/* 추천 밖에서 직접 앉히기 — 추천 5명이 전부가 아니다. 후보(관련도순) 다음 전체 풀. */}
          <input
            className="cx-brief-seatsearch"
            value={seatQuery}
            onChange={(e) => setSeatQuery(e.target.value)}
            placeholder={`전문가 직접 찾기 — 이름·키로 검색 (풀 ${experts?.pool?.length ?? 0}명)`}
          />
          {seatQuery.trim() && (
            <div className="cx-brief-seats cx-brief-hits">
              {searchHits.map((e) => (
                <label key={e.key} className="cx-brief-seat">
                  <input
                    type="checkbox"
                    checked={checked.has(e.key)}
                    disabled={seatFull && !checked.has(e.key)}
                    onChange={() => toggle(e.key)}
                  />
                  <span className="cx-brief-seat-name">{e.name}</span>
                  <span className="cx-brief-seat-axis">{e.key}</span>
                </label>
              ))}
              {searchHits.length === 0 && <span className="cx-brief-empty">일치하는 전문가 없음</span>}
            </div>
          )}
        </div>

        <div className="cx-brief-field">
          <VocFirstPanel topic={topic} onChange={setVoc} />
        </div>

        <div className="cx-brief-field">
          <span>
            원천 근거 {Math.min(12, vocEv.length + evidence.length)}건
            {vocEv.length > 0 && ` (고른 VOC ${vocEv.length} + 대화 ${evidence.length - droppedConv})`} — 검증 대상이지
            결론이 아닙니다
            {droppedConv > 0 && ` · 대화 근거 ${droppedConv}건은 12건 상한으로 빠집니다`}
          </span>
          <div className="cx-brief-ev">
            {evidence.map((ev, i) => (
              <div key={i} className="cx-brief-ev-item">
                <span className="cx-brief-ev-src">
                  {ev.source}
                  {ev.tool ? ` · ${ev.tool}` : ''}
                </span>
                <span className="cx-brief-ev-res">{ev.result.slice(0, 200)}</span>
              </div>
            ))}
            {evidence.length === 0 && <span className="cx-brief-empty">추출된 원천 근거 없음</span>}
          </div>
        </div>

        <div className="cx-brief-actions">
          <button type="button" className="cx-brief-cancel" onClick={onClose}>
            취소
          </button>
          <button type="button" className="cx-brief-go" onClick={confirm} disabled={!topic.trim() || streaming}>
            {JOB_BY_ID[job].name} 심의 시작 · {checked.size}석{mods.size ? ` · 얹을 층 ${mods.size}` : ''} · 근거{' '}
            {Math.min(12, vocEv.length + evidence.length)}
          </button>
        </div>

        {browsing && experts && (
          <SeatBrowser
            pool={experts.pool}
            candidates={experts.candidates?.length ? experts.candidates : rec}
            selected={seatSelected}
            onToggle={(r) => toggle(r.key)}
            min={MIN_SEATS}
            max={MAX_SEATS}
            onClose={() => setBrowsing(false)}
          />
        )}
      </div>
    </div>
  );
}
