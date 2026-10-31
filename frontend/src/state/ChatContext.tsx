// 다중 대화 + localStorage 영속을 관리하는 챗 전역 상태 — SSE 스트리밍은 chat.api 그대로 재사용
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { streamChat } from '../api/chat.api';
import { listRuns } from '../api/routines.api';
import {
  appendServerMessage,
  createServerConversation,
  deleteServerConversation,
  fillTrimmed,
  getServerConversation,
  listServerConversations,
  renameServerConversation,
  serverConvToLocal,
  type ConvKind,
} from '../api/conversations.api';
import { useAuth } from '../auth/useAuth';
import { useCan } from '../auth/useCan';
import type { AgentCatalog, Conversation, DelibData, DelibEvent, DelibOpts, DelibTally, DelibTurn, Message, RoutineRequest, SearchSource, ThinkData, ThinkEvent, ThinkSeat, ToolCatalog } from '../types/chat';
import { conversationEvidence, priorGatheredEvidence, EVID_ITEMS, type HandoffEvidence } from '../components/chat/handoff';
import { isRoutineTerminal, mergeRoutine } from '../components/chat/routine';
import { ROUTINE_STOPPED_BEFORE_RUN } from '../lib/chatErrors';
import { docsAsEvidence, type AttachedDoc } from '../components/chat/docAttach';
import type { AttachedImage } from '../components/chat/imageAttach';
import { buildHistory } from '../components/chat/history';
import type { UploadNotice } from '../components/chat/uploadNotice';
import { noteFrame, startLive, type StreamLive } from '../lib/streamLive';
import { panelPointer } from '../components/chat/panels';
import { UI_HOST_TOKEN } from '../lib/mcpApps';
import {
  decisionAsOf,
  delibOptsToWire,
  loadActiveId,
  loadConversations,
  loadDelibOpts,
  loadDraftPins,
  newId,
  saveActiveId,
  saveConversations,
  saveDelibOpts,
  saveDraftPins,
  type DraftPins,
} from './chatStore';

/** 챗에서 켜 둔 분석 루틴(docs/analysis-routines R3) — 다음 발화 한 번에 실려 간다. title 은 보이기용이라 서버로 가지 않는다. */
export interface ArmedRoutine {
  id: string;
  version?: number;
  title: string;
  inputs: Record<string, unknown>;
  /** 이 값으로 보낸 시작이 실행을 만들기 전에 끝난 까닭(서버의 거절 글 등) — 실패한 턴이 보낸 값을 되살려 켜 둘 때 단다. 고르기 창이 칸 옆에
   *  보이고, 고쳐서 다시 켜면 지워진다. */
  reason?: string;
}

/** 루틴 턴에 보낸 요청 — 실행 id 를 받기 전에 실패하면 되살리기 · 다시 시도에 쓴다. title 은 보이기용이다(chat.api 가 아는 칸만 실어
 *  서버로 가지 않는다). */
type SentRoutine = RoutineRequest & { title?: string };

// 덧붙인 말(note)의 상한 — 포털 중계 RoutineReq.note · 포털 RunIn.note · 게이트웨이 routine_run_start 가 같은 2,000자(파이썬 글자 수 = 코드 포인트)다.
// 넘으면 중계가 요청 전체를 422 로 거절해 루틴이 시작조차 못 했다. 선에 싣는 덧붙인 말만 자른다 — 사람 말풍선과 message 는 그대로 간다.
const ROUTINE_NOTE_MAX = 2000;

/** 덧붙인 말을 상한까지 — 코드 포인트로 센다. UTF-16 으로 자르면 그림 글자(😀)를 반으로 갈라 짝 없는 대리 글자가 가고, 포털이 그 글을 글로
 *  읽지 못해 또 422(string_unicode)다. */
function clipNote(s: string): string {
  return s.length <= ROUTINE_NOTE_MAX ? s : Array.from(s).slice(0, ROUTINE_NOTE_MAX).join('');
}

/** 실행 id 를 받기 전에 끝난 루틴 턴(■ 로 끊음 · 받던 중 끊김 · 게이트웨이 · 실행기 오류 · 침묵 한도)이 서버에 만든 실행을 내 실행 목록에서
 *  찾는다 — 같은 루틴 · 이 대화의 실행 가운데 이 대화의 메시지가 아직 가리키지 않는 가장 새것(목록이 최근 시작부터다). 없으면 null 이다.
 *  시각으로 가르지 않는다 — 포털 started_at 은 서버 시계이고 보낸 때는 이 PC 의 시계라, 두 시계가 어긋나면 그 턴의 실행을 놓쳐 실행이 둘이
 *  되거나 앞 턴의 실행에 붙었다(R3 반대 검토 2차 #6 · #13). 메시지가 가리키는 실행(앞 턴의 답 · 이어서)은 그 턴의 것이다. */
async function findLostRun(routineId: string, conversationId: string | undefined, shown: Set<string>): Promise<string | null> {
  // 대화 id 없이 보낸 턴(서버 대화 저장 미가용)의 실행은 대화에 묶이지 않았다 — 이 대화의 것인지 가릴 수 없다
  if (!conversationId) return null;
  try {
    const { runs } = await listRuns(routineId);
    // 목록이 conversation_id 를 싣지 않는 포털이면 아무것도 맞지 않는다 — 다른 대화(다른 탭 · 다른 입력)의 실행을 잇지 않는다(닫힌 쪽)
    const hit = runs.find((r) => r.routine_id === routineId && r.conversation_id === conversationId && !shown.has(r.id));
    return hit?.id ?? null;
  } catch {
    // 목록을 못 읽었다 — 부른 쪽이 예전처럼 보낸 요청을 다시 보낸다(그 턴의 실행이 서버에서 돌고 있었으면 실행이 둘이 된다)
    return null;
  }
}

// 실행 id 를 받기 전에 이 오류로 끝난 새 루틴 턴은 실행이 서버에 생겼을 수 있다 — 받던 중의 끊김 · 중계의 침묵 한도(AGENT_STREAM_IDLE_TIMEOUT_S) ·
// 중계가 에이전트 스트림을 읽다 끊김 · 게이트웨이 오류(포털이 게이트웨이 시간 한도보다 늦었거나 보낸 뒤 답이 끊겼으면 원장에는 남았다) · 실행기
// 오류. 다시 시도는 같은 요청을 또 보내기 전에 그 실행을 찾는다(R3 반대 검토 2차 #11 — 게이트웨이 오류를 거절로만 보아 실행이 둘이 되고 앞 것은
// 아무도 돌리지 않는 running 으로 남았다).
const ROUTINE_MAYBE_STARTED = new Set(['stream_cut', 'agent_stream_idle', 'agent_unreachable', 'routine_gateway', 'routine_internal']);

interface ChatContextValue {
  // 다중 대화
  conversations: Conversation[];
  activeId: string | null;
  activeConversation: Conversation | null;
  /** 활성 대화의 메시지(없으면 빈 배열) — ChatDock/MessageList 공용. */
  messages: Message[];
  input: string;
  streaming: boolean;
  /** 흐르는 턴이 루틴 턴이다 — 그 턴의 ■ 는 화면 받기만 끊고 실행은 서버에서 돈다(입력창 힌트가 그렇게 말한다). */
  routineStreaming: boolean;
  /** 흐르는 루틴 턴의 실행이 이미 끝났다(RA 초안 올리기 턴 · 끝남 · 실패 · 멈춤 계획을 받은 턴) — 그칠 실행이 없어 ■ 힌트가 '멈춤' 을 말하지 않는다. */
  routineClosed: boolean;
  setInput: (v: string) => void;
  /** 글을 보낸다. 켜 둔 루틴(armedRoutine)이 있으면 이 발화에 실어 보내고 끈다(한 번 쓰기) — 사람이 쓴 글이 루틴에 덧붙인 말(note)이고,
   *  글이 비면 '루틴: <제목>' 을 글로 싣는다(덧붙인 말이 아니다). extraDelibOpts 를 준 발화(심의 넘기기 · 이어하기)는 켜 둔 루틴을 쓰지 않는다.
   *  routineOpt — 값으로 넘기는 루틴 요청(이어서 · 다시 시도). null 이면 켜 둔 루틴을 쓰지도 싣지도 않는다(한 번 누름 보내기 — ChatActionBar). */
  sendMessage: (text: string, extraDelibOpts?: Record<string, unknown>, routineOpt?: RoutineRequest | null) => void;
  /** 이어하기 — 끝난 심의(prior)에 사람 의견을 넣어 후속 심의를 스티어링. roster 를 주면 그 명단으로
   *  간다(사람이 좌석을 직접 고름 — 재심사가 좌석을 더 얹지 않는다). 없으면 같은 전문가 + 재심사. */
  continueDeliberation: (prior: DelibData, opinion: string, roster?: { key: string; role?: string }[]) => void;
  // 심의로 넘기기(핸드오프) — 챗에서 정리한 실데이터(도구결과)를 원천 근거로 실어 현재 대화에서 심의를 연다.
  // 브리프(P3)가 확정한 질문·좌석·템플릿을 받는다. 미지정이면 화두는 첫 발화, 좌석은 심의 자동발굴.
  startHandoff: (opts?: {
    topic?: string;
    personas?: { key: string; role?: string }[];
    chairTemplate?: string;
    modifiers?: string[];
    tools?: string[];
    apps?: string[];
    trigger?: string; // 기본 '/심의 '. sim/test 는 다단 트리거(/시뮬심의·/시험계획)로 넘긴다.
    extraOpts?: Record<string, unknown>; // 추가 delib_opts(예: build_plan) 를 그대로 병합.
    extraEvidence?: HandoffEvidence[]; // 브리프에서 사람이 고른 추가 원천(VOC 먼저 보기) — 대화 근거 앞에.
  }) => void;
  /** 실패 재시도 — 마지막 사용자 발화를 다시 보낸다(심의 페이지는 트리거 강제). */
  retryLast: () => void;
  /** 심의 손잡이(웹 토글) — 심의 페이지 패널이 읽고 쓴다. 전송 시 켠 것만 서버로 실린다. */
  delibOpts: DelibOpts;
  setDelibOpts: (o: DelibOpts) => void;
  /** 사용자 지정 우선 도구 — 활성 대화의 것(대화 전이면 다음 새 대화용 draft). 이후 발화에 실린다. */
  pinnedTools: string[];
  setPinnedTools: (names: string[]) => void;

  pinnedApps: string[];
  setPinnedApps: (keys: string[]) => void;

  /** 인터넷 소스 토글. 켠 것만 바인딩된다 — 끄면 모델의 도구 목록에서 사라진다. */
  searchSources: SearchSource[];
  setSearchSources: (v: SearchSource[]) => void;
  /** 사용자 지정 전문가(agent_type) — '전문가와 대화' 모드. 대화 전 선택 시 새 대화에 적용. */
  pinnedAgent: string | null;
  /** 지정 전문가의 사람 이름(표시용). 없으면 키를 그대로 보여 준다. */
  pinnedAgentName: string | null;
  setPinnedAgent: (key: string | null, name?: string) => void;
  /** 보조 전문가 — 주 전문가와 한 목소리로 답한다(각자 답하는 Thinking 과 다르다). 최대 4명. */
  pinnedHelpers: { key: string; name?: string }[];
  setPinnedHelpers: (list: { key: string; name?: string }[]) => void;
  /** 띵킹 모드 — 답할 수 있는 전문가만 각자 답한다(회의 아님). 세션 토글이라 매 발화에 실린다. */
  thinking: boolean;
  setThinking: (v: boolean) => void;
  /** 켜 둔 분석 루틴 — 다음 발화 한 번에 실려 가고 꺼진다. 세션 토글이다(저장하지 않는다). 권한(feat:routines)이 없으면 싣지 않는다. */
  armedRoutine: ArmedRoutine | null;
  setArmedRoutine: (r: ArmedRoutine | null) => void;
  /** 루틴 실행을 잇는다 — 활성 대화에 '루틴 이어서: <제목>' 발화로 run_id 를 보낸다. 에이전트 서버에 살아 있으면 다시 붙고(지금까지의
   *  프레임을 다시 받는다), 아니면 포털 원장에서 끝난 단계를 건너뛰고 잇는다. 보낸 뒤 바로 풀린다(턴이 끝나기를 기다리지 않는다).
   *  uploadRa — 끝난 실행의 저장 보고서를 RA 초안으로 올린다('RA 초안 올리기: <제목>' 발화로 {run_id, upload_ra: true}, ra.upload 'ask' · 저절로
   *  올리기(auto)가 실패한 실행의 다시 올리기). */
  resumeRoutine: (runId: string, title?: string, opts?: { uploadRa?: boolean }) => Promise<void>;
  /** 붙인 문서(브라우저에서 읽은 추출문). 보내도 **비우지 않는다** — 대화에는 본문을 남기지 않으므로(쿼터) 칩을 떼기 전까지 매 발화에
   *  다시 실려 뒤따르는 질문을 받는다(처음 1901dbf 부터 그랬다 — 주석만 '비운다' 로 낡아 있었다, docs/chat-ppt PP-D6).
   *  원본 파일은 서버로 가지 않는다(DRM 전제: 추출은 PC 의 Office COM 에서 끝난다). */
  attachedDocs: AttachedDoc[];
  setAttachedDocs: (list: AttachedDoc[]) => void;
  /** 이번 발화에 올릴 그림(줄인 data URL). 보내면 비워진다 — 서버가 저장한 주소가 그 발화에 남아 다음 턴 이력으로 다시 실린다(T5). */
  attachedImages: AttachedImage[];
  setAttachedImages: (list: AttachedImage[]) => void;
  /** 보내기 결과를 대화에 남긴다 — 어시스턴트 알림 한 건 + 업로드 근거(docs/chat-ppt A2 · PP-D3). 대화가 없으면 새로 만든다.
   *  서버 사본에도 붙인다(답을 받는 중인 대화면 그 답이 저장된 뒤). 종전엔 결과가 업로드 패널 안에서만 끝나 다음 질문이 몰랐다. */
  addUploadNotice: (n: UploadNotice) => void;
  /** 받기가 끊긴 심의를 서버에서 멈췄다(포털 POST /agent/deliberate/cancel 200) — 그 메시지에 멈춤을 적는다(브라우저 사본에도 남는다).
   *  받는 중인 심의는 멈춤 사건(SSE delib cancelled)이 적으므로 부르지 않는다(triage A24). */
  markDelibStopped: (msgId: string, message: string) => void;
  stop: () => void;
  /** 지금 도는 스트림의 생존 신호(마지막 프레임·마지막 진행 시각). 돌지 않으면 null. 상태가 아니라 읽는 함수다 —
   *  토큰마다 다시 그리지 않고, 보여 주는 쪽(StreamPulse)이 1초마다 읽는다. */
  streamLive: () => StreamLive | null;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  // 보조 페이지(/apps, /launch)의 플로팅 독 상태
  open: boolean;
  openDock: () => void;
  closeDock: () => void;
  toggleDock: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
const ChatContext = createContext<ChatContextValue | undefined>(undefined);

// 멀티턴 이력은 components/chat/history.ts(buildHistory)가 만든다 — 심의 브리프(HandoffBrief)도 같은 함수를 쓴다.

/** 심의 delib 이벤트를 메시지의 DelibData 로 병합 — kind 별 리듀서. */
function mergeDelib(prev: DelibData | undefined, e: DelibEvent): DelibData {
  const d: DelibData = { ...(prev ?? {}) };
  // 실행 id — 에이전트 서버가 첫 심의 사건에 싣는다(triage A24). '멈춤' 이 이 심의 하나만 짚는 열쇠다.
  if (typeof e.run_id === 'string' && e.run_id && !d.runId) d.runId = e.run_id;
  // 다단 심의(/시뮬심의) — 앞 단의 결정문 뒤에 다음 단이 열렸다(엔진의 단 경계 표지 checkpoint, 또는 결정문 뒤에 온 단 사건). 그 단의 결정문에서
  // 내린다. 한 단 심의는 결정문 뒤에 단 사건이 오지 않아 서지 않는다 — 받기가 끊긴 칸의 '멈춤' 이 이것으로 남는다(DelibView).
  if (e.kind === 'checkpoint' || (d.decision && (e.kind === 'stage' || e.kind === 'personas' || e.kind === 'turn'))) d.nextStage = true;
  switch (e.kind) {
    case 'stage': {
      const stage = String(e.stage ?? '');
      d.stage = stage;
      d.stages = [...(d.stages ?? []), stage];
      if (typeof e.n === 'number') d.roundN = e.n;
      break;
    }
    case 'personas':
      d.personas = (e.personas as DelibData['personas']) ?? [];
      if (typeof e.totalRounds === 'number') d.totalRounds = e.totalRounds;
      break;
    case 'evidence': {
      // 복수 출처(SignalForge 환기 + 정량 근거 선주입)가 서로 덮어쓰지 않게 append.
      const prevEv = Array.isArray(d.evidence) ? d.evidence : d.evidence ? [d.evidence] : [];
      d.evidence = [
        ...prevEv,
        {
          source: String(e.source ?? ''),
          text: String(e.text ?? ''),
          included: Boolean(e.included),
          // 알림 카드 깃발 — 여기서 안 옮기면 화면이 알림을 '좌석에 주지 않은 근거' 로 부른다.
          ...(e.notice ? { notice: true } : {}),
        },
      ];
      break;
    }
    case 'turn': {
      const turn: DelibTurn = {
        round: Number(e.round ?? 0),
        ...(e.display_round != null ? { displayRound: Number(e.display_round) } : {}),
        persona: String(e.persona ?? ''),
        say: String(e.say ?? ''),
        // 버블은 줄인 글이다 — 줄이지 않은 글은 따로 쥔다(화면은 say, 내보내기는 sayFull ?? say).
        ...(typeof e.say_full === 'string' && e.say_full ? { sayFull: e.say_full } : {}),
        ...(e.position ? { position: String(e.position) } : {}),
        ...(e.stance ? { stance: String(e.stance) } : {}),
        ...(e.non_negotiable ? { nonNegotiable: String(e.non_negotiable) } : {}),
        ...(Array.isArray(e.rebut) && e.rebut.length
          ? { rebut: e.rebut as DelibTurn['rebut'] }
          : {}),
        ts: Date.now(),
      };
      d.turns = [...(d.turns ?? []), turn];
      break;
    }
    case 'decision':
      d.decision = String(e.text ?? '');
      d.finishing = false; // 마무리가 끝났다 — 다단 심의는 다음 단에서 다시 멈출 수 있다
      d.nextStage = false; // 열린 단이 결정문을 냈다 — 또 다음 단이 있으면 엔진이 표지를 다시 낸다
      break;
    case 'plain':
      d.plain = String(e.text ?? '');
      break;
    case 'outcome':
      d.outcome = {
        report_id: (e.report_id as number | null) ?? null,
        title: String(e.title ?? ''),
        tally: e.tally as DelibTally | undefined,
        unanimous: Boolean(e.unanimous),
      };
      break;
    case 'cancelled':
      // 사람이 멈췄다(에이전트 POST /deliberate/cancel — triage A24) — 오류가 아니다. 뒤따르는 done 이 받기를 닫는다.
      d.cancelled = { message: String(e.message ?? '') };
      break;
    case 'finishing':
      // 의장이 결정문을 냈다 — 그 단의 결정문까지는 마무리(요약 · 쉬운 설명 · Report Archive 저장)라 에이전트가 멈추지 않는다(409 finishing).
      d.finishing = true;
      break;
  }
  return d;
}

/** 이어하기에 실을 **미해결 쟁점** 블록 — 누가 누구의 무엇을 반박했는지.
 *
 *  ⚠ 이게 없으면 이어하기에 **의장 결정문 텍스트만** 간다. 결정문은 합의된 결론이라
 *  '무엇을 두고 갈렸는지' 가 지워진다 — 다음 회차가 같은 논점을 처음부터 다시 판다.
 *  반박은 라운드를 거쳐 좁혀진 쟁점이므로 승계 가치가 가장 높은 부분이다.
 *
 *  결정문을 밀어내지 않는다 — 결정문 **뒤에** 붙인다. 엔진이 요약 상한에서 머리부터 실으므로 넘치면 이 블록이 먼저 빠지고,
 *  엔진이 그 사실을 카드로 알린다. 종전엔 여기서 결정문과 합쳐 8,000자 예산을 따로 셈해, 엔진이 받을 때는 이미 안이었다. */
function priorIssueBlock(turns: DelibTurn[] | undefined): string {
  const seen = new Set<string>();
  const lines: string[] = [];
  // 뒤 라운드가 더 좁혀진 쟁점이다 — 뒤 라운드부터 적는다(엔진이 상한에서 꼬리를 빼면 앞(초기) 쟁점이 먼저 빠진다).
  for (const t of [...(turns ?? [])].reverse()) {
    for (const r of t.rebut ?? []) {
      const counter = (r.counter || '').trim();
      if (!counter) continue;
      const key = `${t.persona}>${r.target}:${counter.slice(0, 40)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const basis = r.basis ? ` (근거 ${r.basis})` : '';
      lines.push(`- R${t.displayRound ?? t.round} ${t.persona} → ${r.target}: ${counter}${basis}`);
    }
  }
  if (lines.length === 0) return '';
  const head = '\n\n[이전 회차에서 갈렸던 쟁점 — 결론이 아니라 **아직 다툰 자리**다. ' +
    '이번 회차에서 정면으로 다루고, 해소됐으면 무엇이 근거였는지 밝혀라]\n';
  return head + lines.map((l) => l + '\n').join('');
}

/** 띵킹 think 이벤트를 메시지의 ThinkData 로 병합 — 좌석 키로 한 행을 계속 채워 나간다. */
function mergeThink(prev: ThinkData | undefined, e: ThinkEvent): ThinkData {
  const d: ThinkData = { ...(prev ?? {}) };
  const seats = [...(d.seats ?? [])];
  const upsert = (key: string, patch: Partial<ThinkSeat>) => {
    const i = seats.findIndex((x) => x.key === key);
    if (i >= 0) seats[i] = { ...seats[i], ...patch };
    else seats.push({ key, ...patch });
  };
  switch (e.kind) {
    case 'roster': {
      const hop = Number(e.hop ?? 0);
      for (const raw of (e.seats as ThinkSeat[]) ?? []) upsert(raw.key, { ...raw, hop });
      break;
    }
    case 'screen':
      upsert(String(e.key ?? ''), {
        hits: Number(e.hits ?? 0),
        screened: !e.passed,
        screenReason: String(e.reason ?? ''),
      });
      break;
    case 'verdict':
      upsert(String(e.key ?? ''), {
        verdict: e.verdict as ThinkSeat['verdict'],
        scope: String(e.scope ?? ''),
        refer: (e.refer as string[]) ?? [],
        ...(e.error ? { error: String(e.error) } : {}),
      });
      break;
    case 'answer':
      upsert(String(e.key ?? ''), {
        name: String(e.name ?? ''),
        domain: String(e.domain ?? ''),
        answer: String(e.text ?? ''),
        basis: (e.basis as string[]) ?? [],
      });
      break;
    case 'handoff':
      d.handoffs = [
        ...(d.handoffs ?? []),
        { phrases: (e.phrases as string[]) ?? [], seats: (e.seats as string[]) ?? [] },
      ];
      break;
    case 'summary':
      d.summary = {
        answered: Number(e.answered ?? 0),
        passed: Number(e.passed ?? 0),
        screened_out: Number(e.screened_out ?? 0),
        errored: Number(e.errored ?? 0),
        capped: Number(e.capped ?? 0),
        hops: Number(e.hops ?? 0),
        no_answer: Boolean(e.no_answer),
      };
      break;
  }
  d.seats = seats;
  return d;
}

/** 첫 사용자 메시지 → 대화 제목(≈40자). */
// 받는 중인 대화에 온 보내기 알림을 그 스트림이 끝나고 얼마 뒤 서버 사본에 붙이나 — 포털이 답을 저장하는 틈(스트림 끝 → 저장)을 비켜 간다.
const NOTICE_AFTER_STREAM_MS = 800;

function makeTitle(text: string): string {
  const t = text.replace(/\s+/g, ' ').trim();
  if (!t) return '새 대화';
  return t.length > 40 ? `${t.slice(0, 40).trimEnd()}…` : t;
}

interface ChatProviderProps {
  children: ReactNode;
  /** 이력 localStorage 네임스페이스 — 심의 페이지는 'hwax.delib' 로 분리(기본 일반 챗). */
  storagePrefix?: string;
  /** 전송 시 서버로만 붙는 프리픽스(화면 표시는 원문) — 심의 페이지가 '/심의 ' 자동 부착에 사용.
   *  대화의 "첫 발화"에만 붙는다 — 이후 발화는 일반 챗(GLM 이어가기)으로 흐른다. */
  sendPrefix?: string;
  /** 서버 대화 저장소 동기화 — 설정 시 이 kind 의 서버 대화(MCP 심의 포함)를 목록에 병합하고,
   *  전송을 서버 대화에 저장한다(정본=서버, localStorage=캐시). 미설정이면 종전 로컬 전용. */
  serverKind?: ConvKind;
}

// 다시 보일 때 서버 사본과 맞추는 침묵 문턱 — 챗 · 심의 스트림 모두 15초마다 ping 을 낸다(P-1 ②)
const RESYNC_QUIET_MS = 20_000;

export function ChatProvider({
  children,
  storagePrefix = 'hwax.chat',
  sendPrefix = '',
  serverKind,
}: ChatProviderProps) {
  // 캐시 네임스페이스는 **계정별**이다 — 미구분 키는 같은 브라우저의 이전 사용자 대화가
  // 다음 사용자에게 그대로 보였다(실사고 2026-09-03: koo.park 로그인에 hwax.demo 대화 노출).
  // 로그인 확정(user) 후 아래 로드 효과가 채운다 — 그 전에는 빈 상태.
  const { user } = useAuth();
  // 권한 없는 모드는 보내지 않는다 — 입구를 숨겨도 저장된 상태(Thinking 켬·지정 전문가·웹 검색
  // 소스)가 남아 있으면 매 발화가 403 이 된다. 백엔드도 막는다(docs/access-control).
  const can = useCan();
  const scopedPrefix = user ? `${storagePrefix}.${user.email}` : null;
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  // 흐르는 턴이 루틴 턴인가 — sendMessage 가 켜고 그 스트림의 끝 정리(settle)가 끈다
  const [routineStreaming, setRoutineStreaming] = useState(false);
  // 그 루틴 턴의 실행이 이미 끝났나(올리기 턴 · 끝난 계획) — ■ 힌트가 '멈춤' 을 가리키지 않게. 같은 자리에서 켜고 끈다
  const [routineClosed, setRoutineClosed] = useState(false);
  // 심의 손잡이(웹 토글) — 상태는 UI 바인딩용, ref 는 전송 시점 읽기용(sendMessage 재생성·스테일 방지).
  const [delibOpts, setDelibOptsState] = useState<DelibOpts>({});
  const delibOptsRef = useRef<DelibOpts>(delibOpts);
  const setDelibOpts = useCallback(
    (o: DelibOpts) => {
      delibOptsRef.current = o;
      setDelibOptsState(o);
      if (scopedPrefix) saveDelibOpts(o, scopedPrefix);
    },
    [scopedPrefix],
  );
  // 계정별 캐시 로드 — 로그인(또는 계정 전환) 시점에 그 사람 네임스페이스로 다시 채운다.
  useEffect(() => {
    if (!scopedPrefix) return;
    const convs = loadConversations(scopedPrefix);
    setConversations(convs);
    const saved = loadActiveId(scopedPrefix);
    setActiveId(saved && convs.some((c) => c.id === saved) ? saved : null);
    const opts = loadDelibOpts(scopedPrefix);
    delibOptsRef.current = opts;
    setDelibOptsState(opts);
    // 구(계정 미구분) 키는 그 자체가 누출 사본 — 발견 즉시 제거한다.
    try {
      for (const k of ['conversations', 'activeId', 'delibOpts']) {
        localStorage.removeItem(`${storagePrefix}.${k}`);
      }
    } catch {
      /* noop */
    }
  }, [scopedPrefix, storagePrefix]);
  const abortRef = useRef<AbortController | null>(null);
  // 도는 스트림의 '중지됨' 정리 — 중지 단추가 읽기 루프를 기다리지 않고 부른다(docs/request-1029 P-1 ③)
  const stopUiRef = useRef<(() => void) | null>(null);
  // 스트리밍 중인 대화 id — 그 대화가 삭제되면 스트림도 중단하기 위해 추적.
  const streamConvRef = useRef<string | null>(null);
  // 도는 스트림의 생존 신호 — 프레임이 올 때마다 시각만 적는다. 여기서 스트림을 끊지 않는다(표시용).
  const liveRef = useRef<StreamLive | null>(null);
  const streamLive = useCallback(() => liveRef.current, []);
  // 대화 시작 전(랜딩) 선택한 전문가·도구 — 다음 '새 대화' 생성 시 대화에 옮겨 심는다.
  // ref 는 sendMessage 전송 시점 읽기용(스테일 방지 — delibOpts 패턴과 동일).
  // 새로고침에 날아가면 사용자는 **여전히 골라 둔 줄** 알고 첫 발화를 던진다(entry-F7).
  const [draftPins, setDraftPinsState] = useState<DraftPins>(() => loadDraftPins());
  // 인터넷 소스는 대화별이 아니라 세션 단위 토글이다 — 기본값은 '전부 끔'(빈 배열).
  // undefined 를 기본으로 두면 종전 동작(전부 허용)이 되어, 켠 적 없는데 나가는 상황이 된다.
  const [searchSources, setSearchSources] = useState<SearchSource[]>([]);
  // 띵킹 모드도 세션 토글이다(소스 토글과 같은 성격). ref 는 전송 시점 읽기용 —
  // 상태만 쓰면 sendMessage 클로저가 스테일 값을 실어 토글이 한 턴 늦게 반영된다.
  const [thinking, setThinkingState] = useState(false);
  const thinkingRef = useRef(false);
  const setThinking = useCallback((v: boolean) => {
    thinkingRef.current = v;
    setThinkingState(v);
  }, []);
  // 켜 둔 분석 루틴 — 띵킹 토글과 같은 꼴(상태는 화면, ref 는 보내는 순간 읽기). 보내면 꺼진다(sendMessage).
  const [armedRoutine, setArmedRoutineState] = useState<ArmedRoutine | null>(null);
  const armedRoutineRef = useRef<ArmedRoutine | null>(null);
  const setArmedRoutine = useCallback((r: ArmedRoutine | null) => {
    armedRoutineRef.current = r;
    setArmedRoutineState(r);
  }, []);
  // 루틴 턴에 보낸 요청(사람 발화 id → 요청) — 실행 id 를 받기 전에 실패한 턴(동시 상한 routine_busy 등)을 '다시 시도' 가 같은 요청으로
  // 다시 보내게 한다. 일반 챗 글로 다시 가면 '루틴: <제목>' 이 질문으로 답해진다. 화면 세션 동안만 쥔다(작다).
  const routineSentRef = useRef<Map<string, SentRoutine>>(new Map());
  // 실행 id 를 받기 전에 끝난 루틴 턴(사람 발화 id) — ■ 로 끊었거나 받던 중에 끊겼거나 실행이 생겼을 수 있는 오류(ROUTINE_MAYBE_STARTED)로 끝났다.
  // 실행이 서버에 생겼는지 모른다 — 중계는 브라우저가 떠나도 상류를 끝까지 읽고 실행기는 구독이 끊겨도 돈다(R3-design D7 · D9). '다시 시도' 는 같은
  // 요청을 또 보내기 전에 그 실행을 찾는다(retryLast).
  const routineUnknownRef = useRef<Set<string>>(new Set());
  // 계정이 바뀌면(로그아웃 · 다른 사람의 로그인) 앞 사람이 켜 둔 루틴과 그 입력 · 다시 보낼 요청을 버린다 — 이메일 로그인 · 로그아웃은 페이지를
  // 다시 읽지 않아 루트 ChatProvider 가 그대로 살고, 앞 사람의 루틴이 다음 사람의 발화에 실렸다(R3 반대 검토 #36). 계정별 캐시 네임스페이스
  // (scopedPrefix)가 바뀌는 때다 — 같은 사람의 /auth/me 다시 받기(창 포커스)는 바뀌지 않는다. 세는 값은 보낸 뒤 계정이 바뀐 턴이 실패해도
  // 그 루틴을 되살리지 않게 한다(sendMessage 의 rearm).
  const accountEpochRef = useRef(0);
  useEffect(() => {
    accountEpochRef.current += 1;
    setArmedRoutine(null);
    routineSentRef.current.clear();
    routineUnknownRef.current.clear();
  }, [scopedPrefix, setArmedRoutine]);
  // 붙인 문서도 전송 시점 읽기다(같은 스테일 함정). 보내도 비우지 않는다 — 대화에 본문을 남기지 않으므로 칩을 떼기 전까지 매 발화에
  // 다시 실려 뒤따르는 질문을 받는다(그림과 다르다 — 그림은 서버 주소가 이력으로 다시 간다). 처음부터 그 동작이었고 주석만 낡았다(PP-D6).
  const [attachedDocs, setAttachedDocsState] = useState<AttachedDoc[]>([]);
  const attachedDocsRef = useRef<AttachedDoc[]>([]);
  const setAttachedDocs = useCallback((list: AttachedDoc[]) => {
    attachedDocsRef.current = list;
    setAttachedDocsState(list);
  }, []);
  // 올린 그림 — 문서와 달리 보낸 뒤 비운다. 그림은 서버에 남고(아티팩트) 그 주소가 이력으로 다음 턴에 다시 실리므로, 남겨 두면 같은
  // 그림이 매 턴 두 번(이번 발화 + 앞 대화의 그림) 간다.
  const [attachedImages, setAttachedImagesState] = useState<AttachedImage[]>([]);
  const attachedImagesRef = useRef<AttachedImage[]>([]);
  const setAttachedImages = useCallback((list: AttachedImage[]) => {
    attachedImagesRef.current = list;
    setAttachedImagesState(list);
  }, []);
  const draftPinsRef = useRef(draftPins);
  const setDraftPins = useCallback((v: DraftPins) => {
    draftPinsRef.current = v;
    setDraftPinsState(v);
    saveDraftPins(v);
  }, []);

  // 변경 시 저장(토큰 단위 갱신이 잦으므로 250ms 디바운스). 로그인 전(null)에는 저장하지 않는다.
  useEffect(() => {
    if (!scopedPrefix) return;
    const t = window.setTimeout(() => saveConversations(conversations, scopedPrefix), 250);
    return () => window.clearTimeout(t);
  }, [conversations, scopedPrefix]);
  useEffect(() => {
    if (!scopedPrefix) return;
    saveActiveId(activeId, scopedPrefix);
  }, [activeId, scopedPrefix]);

  // 진행 중 이탈 경고 — 탭을 닫으면 이 화면은 남은 진행을 다시 받지 못한다. 심의는 구독이 끊겨도 서버에서 끝까지
  // 돌지만(분리 태스크) 결과는 Report Archive 와 서버 대화에만 남고, 일반 챗은 응답이 통째로 유실된다.
  // streaming 동안만 beforeunload 를 걸어 실수로 탭을 닫는 걸 막는다(완료 시 자동 해제).
  useEffect(() => {
    if (!streaming) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = ''; // 브라우저 기본 확인 대화 표시
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [streaming]);

  // ── 서버 대화 저장소 동기화(정본=서버, localStorage=캐시) ──────────────────
  // 서버 목록의 updated_at(ms) — "열 때 최신 로드" 판정용(서버가 더 새로우면 상세 재로드).
  const serverMetaRef = useRef<Map<string, number>>(new Map());
  // 상세 로드 중복 방지.
  const detailLoadingRef = useRef<Set<string>>(new Set());

  /** 서버 상세를 가져와 해당 대화의 메시지를 교체(스트리밍 중엔 건드리지 않음). */
  const refreshFromServer = useCallback((serverId: string) => {
    if (detailLoadingRef.current.has(serverId)) return;
    detailLoadingRef.current.add(serverId);
    void getServerConversation(serverId)
      .then((detail) => {
        if (!detail) return;
        const fresh = serverConvToLocal(detail);
        setConversations((prev) =>
          prev.map((c) =>
            (c.serverId ?? c.id) !== serverId || streamConvRef.current === c.id
              ? c
              : { ...c, title: fresh.title, messages: fresh.messages, updatedAt: fresh.updatedAt },
          ),
        );
      })
      .catch(() => {
        /* 서버 미가용 — 캐시로 계속(비치명적) */
      })
      .finally(() => {
        detailLoadingRef.current.delete(serverId);
      });
  }, []);

  // 로그인 후 1회(+사용자 변경 시): 서버 목록을 로컬 목록에 병합. 메시지는 열 때 로드.
  useEffect(() => {
    if (!serverKind || !user) return;
    let cancelled = false;
    void listServerConversations()
      .then((list) => {
        if (cancelled) return;
        const metas = list.filter((m) => m.kind === serverKind);
        for (const m of metas) serverMetaRef.current.set(m.id, m.updated_at * 1000);
        setConversations((prev) => {
          const bySrv = new Map(prev.map((c) => [c.serverId ?? c.id, c] as const));
          const merged = [...prev];
          for (const m of metas) {
            if (bySrv.has(m.id)) continue; // 이미 로컬 캐시에 있음 — 상세는 열 때 판정
            merged.push({
              id: m.id,
              serverId: m.id,
              title: m.title || '새 대화',
              messages: [], // 자리표시자 — 선택 시 상세 로드
              createdAt: m.created_at * 1000,
              updatedAt: m.updated_at * 1000,
            });
          }
          return merged.sort((a, b) => b.updatedAt - a.updatedAt);
        });
      })
      .catch(() => {
        /* 서버 미가용 — 로컬 캐시만으로 동작 */
      });
    return () => {
      cancelled = true;
    };
  }, [serverKind, user]);

  // "열 때 최신 로드": 활성 대화가 서버 대화인데 비었거나 서버가 더 새로우면 상세 재로드.
  useEffect(() => {
    if (!serverKind || !activeId) return;
    const conv = conversations.find((c) => c.id === activeId);
    const sid = conv?.serverId;
    if (!conv || !sid) return;
    const serverTs = serverMetaRef.current.get(sid) ?? 0;
    const stale = conv.messages.length === 0 || serverTs > conv.updatedAt + 2000;
    if (stale && streamConvRef.current !== conv.id) refreshFromServer(sid);
    // conversations 를 deps 에 넣으면 교체 직후 재실행되지만 stale 판정이 false 라 루프 없음.
  }, [serverKind, activeId, conversations, refreshFromServer]);

  // 브라우저 사본을 저장 한도(쿼터)로 줄여 둔 대화 — 열 때 서버 정본에서 줄인 칸(도구 날것·심의 발언·근거)만 되채운다. 이걸 안
  // 하면 새로고침 뒤 심의로 넘기기·이어하기·내보내기가 줄인 판(날것 대신 미리보기, 발언 45건, 근거 4건)으로 만들어진다.
  // 통째로 바꾸지 않는다 — 서버 사본에 없는 칸(보고서 번호·쉬운 설명·좌석 명단)은 브라우저 것이 맞다(fillTrimmed).
  useEffect(() => {
    if (!serverKind || !activeId) return;
    const conv = conversations.find((c) => c.id === activeId);
    const sid = conv?.serverId;
    if (!conv || !sid || !conv.cacheTrimmed || conv.cacheFillFailed || streamConvRef.current === conv.id) return;
    if (detailLoadingRef.current.has(sid)) return;
    detailLoadingRef.current.add(sid);
    void getServerConversation(sid)
      .then((detail) => {
        if (!detail) return;
        const fresh = serverConvToLocal(detail);
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== conv.id || streamConvRef.current === c.id) return c;
            const filled = fillTrimmed(c.messages, fresh.messages);
            // 모양이 달라 못 채웠으면 표식을 지우지 않는다(지우면 줄인 판이 원본처럼 남는다). 같은 세션에 다시 가져오지 않게
            // 실패를 메모리에 적고, 대화 머리가 '줄인 판으로 만들어진다' 를 알린다(ExportBar).
            if (!filled) return { ...c, cacheFillFailed: true };
            return { ...c, cacheTrimmed: false, messages: filled };
          }),
        );
      })
      .catch(() => {
        /* 서버 미가용 — 줄인 사본으로 계속(비치명적) */
      })
      .finally(() => {
        detailLoadingRef.current.delete(sid);
      });
  }, [serverKind, activeId, conversations]);

  // ── 보내기 알림(docs/chat-ppt PP-D3) ─────────────────────────────────────────────
  // 서버 사본은 대화마다 한 줄로 잇는다(서버 대화 만들기 · 덧붙이기) — 다음 발화는 이 줄을 기다린다(알림이 만든 서버 대화를 모르고 하나 더
  // 만들지 않게). 답을 받는 중인 대화면 그 스트림이 끝나고 잠시 뒤 붙인다 — 포털은 답을 스트림 끝에 적으므로, 먼저 적으면 다른 기기에서
  // 알림이 답보다 앞에 선다. 기다릴 스트림은 알림이 온 그때 정한다(늦게 정하면 다음 발화의 스트림을 기다려 서로 붙잡는다).
  const noticeChainRef = useRef<Map<string, Promise<string | undefined>>>(new Map());
  const streamDoneRef = useRef<Map<string, Promise<void>>>(new Map());
  const convsRef = useRef<Conversation[]>(conversations);
  convsRef.current = conversations;

  const addUploadNotice = useCallback(
    (n: UploadNotice) => {
      const now = Date.now();
      const msg: Message = { id: newId(), role: 'assistant', text: n.text, ts: now, activity: n.activity };
      let cid = activeId && convsRef.current.some((c) => c.id === activeId) ? activeId : null;
      if (!cid) {
        cid = newId();
        const conv: Conversation = { id: cid, title: makeTitle(n.title), messages: [msg], createdAt: now, updatedAt: now };
        setConversations((prev) => [conv, ...prev]);
        setActiveId(cid);
      } else {
        const id0 = cid;
        setConversations((prev) =>
          prev.map((c) => (c.id !== id0 ? c : { ...c, updatedAt: now, messages: [...c.messages, msg] })),
        );
      }
      if (!serverKind) return;
      const id = cid;
      const waitFor = streamConvRef.current === id ? streamDoneRef.current.get(id) : undefined;
      const prev = noticeChainRef.current.get(id) ?? Promise.resolve<string | undefined>(undefined);
      const next = prev
        .then(async (prevSid) => {
          if (waitFor) {
            await waitFor;
            await new Promise((r) => window.setTimeout(r, NOTICE_AFTER_STREAM_MS));
          }
          let sid = prevSid ?? convsRef.current.find((c) => c.id === id)?.serverId;
          if (!sid) {
            sid = await createServerConversation(makeTitle(n.title), serverKind);
            const s1 = sid;
            serverMetaRef.current.set(s1, Date.now());
            setConversations((p) => p.map((c) => (c.id === id ? { ...c, serverId: s1 } : c)));
          }
          await appendServerMessage(sid, { role: 'assistant', content: n.text, meta: { activity: n.activity, upload: true } });
          return sid;
        })
        // 서버에 못 남겨도 화면 사본은 남는다(대화 저장 미가용 박스의 종전 폴백과 같다)
        .catch(() => convsRef.current.find((c) => c.id === id)?.serverId);
      noticeChainRef.current.set(id, next);
      void next.then(() => {
        if (noticeChainRef.current.get(id) === next) noticeChainRef.current.delete(id);
      });
    },
    [activeId, serverKind],
  );

  const patch = useCallback((convId: string, msgId: string, fn: (m: Message) => Message) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id !== convId
          ? c
          : {
              ...c,
              updatedAt: Date.now(),
              messages: c.messages.map((m) => (m.id === msgId ? fn(m) : m)),
            },
      ),
    );
  }, []);

  // 멈춤 응답을 기다리는 동안 다른 대화로 옮겨 갔어도 그 메시지가 든 대화에 적는다(활성 대화에 묶지 않는다).
  const markDelibStopped = useCallback((msgId: string, message: string) => {
    setConversations((prev) =>
      prev.map((c) =>
        !c.messages.some((m) => m.id === msgId)
          ? c
          : {
              ...c,
              updatedAt: Date.now(),
              messages: c.messages.map((m) =>
                m.id === msgId && m.delib ? { ...m, delib: { ...m.delib, cancelled: { message } } } : m,
              ),
            },
      ),
    );
  }, []);

  const sendMessage = useCallback(
    // routineOpt — 셋째 인자(값으로 넘기는 이어서 · 다시 시도 · 한 번 누름 보내기). undefined 면 켜 둔 루틴을 쓰고, null 이면 루틴 없이 보낸다.
    (message: string, extraDelibOpts?: Record<string, unknown>, routineOpt?: SentRoutine | null) => {
      // 분석 루틴(R3) — 넘겨받은 요청이 먼저고, 없으면 켜 둔 루틴을 한 번 쓰고 끈다. 심의 넘기기 · 이어하기(extraDelibOpts)는 켜 둔 루틴을
      // 쓰지 않는다 — 에이전트 서버는 루틴 가지를 심의보다 먼저 보므로 그 심의가 루틴 실행으로 바뀐다. 권한이 없으면 싣지 않는다.
      const armed = routineOpt === undefined && !extraDelibOpts ? armedRoutineRef.current : null;
      // 사람이 쓴 글이 루틴에 덧붙인 말(note)이다 — 실행기가 단계 · 인사이트 프롬프트에 싣고 원장에 남겨 이어서에도 쓴다(R3 C3). 글 없이 보내면
      // 서버가 받는 글(1자 이상)로 '루틴: <제목>' 을 싣는다 — 이것은 덧붙인 말이 아니다. 루틴이 실리지 않으면(권한 없음) 빈 글은 보내지 않는다.
      const typed = message.trim();
      const text = typed || (armed && can('feat:routines') ? `루틴: ${armed.title}` : '');
      // 한 번에 한 스트림 — streaming 은 이 함수를 만든 때의 값이라, 기다린 뒤에 부르는 쪽(고르기 뒤 잇기 등)은 받는 중인데도 거짓을 본다. 스트림이
      // 시작하며 곧바로 쥐고 그 스트림의 끝 정리만 놓는 abortRef 로도 막는다(R3 반대 검토 2차 #12 — 둘째 스트림이 열려 먼저 끝난 쪽이 다른 쪽의 ■ 를 지웠다).
      if (!text || streaming || abortRef.current) return;
      if (armed) setArmedRoutine(null);
      const routineReq: SentRoutine | null = !can('feat:routines')
        ? null
        : (routineOpt ??
          (armed
            ? { id: armed.id, ...(armed.version ? { version: armed.version } : {}), inputs: armed.inputs, note: clipNote(typed), title: armed.title }
            : null));
      // 실행을 만들기 전에 끝난 새 루틴 턴(포털 · 중계의 거절 · 동시 상한 · 연결 실패) — 보낸 값을 다시 켜 두고 까닭을 단다. 고르기 창이 그 값과
      // 까닭을 칸 옆에 보이고, '다시 시도' 는 그 값(고쳤으면 고친 값)으로 보낸다(R3 반대 검토 #14 — 거절 하나에 적은 값이 다 사라졌다). 실행이 생긴
      // 뒤(routine 프레임이 왔다 — 모든 routine 프레임에 run_id 가 있다)는 되살리지 않는다(다시 보내면 실행이 둘이다). 그새 다른 루틴을 켰거나
      // 계정이 바뀌었으면 건드리지 않는다. 사람이 ■ 로 끊은 것 · 받던 중에 끊긴 것은 실행 전의 거절이 아니다(실행은 서버에서 돌 수 있다).
      let runSeen = false;
      const epoch = accountEpochRef.current;
      const rearm = (reason: string) => {
        if (!routineReq?.id || routineReq.run_id || runSeen) return;
        if (armedRoutineRef.current || accountEpochRef.current !== epoch) return;
        setArmedRoutine({
          id: routineReq.id,
          ...(routineReq.version ? { version: routineReq.version } : {}),
          title: routineReq.title || routineReq.id,
          inputs: routineReq.inputs ?? {},
          reason,
        });
      };

      const now = Date.now();

      // 멀티턴: 이번 user 메시지를 붙이기 전의 활성 대화 메시지가 history가 된다(중복 금지).
      const existing = conversations.find((c) => c.id === activeId);
      // 앞 턴의 조회 근거도 싣는다 — 다음 턴 · 띵킹 좌석이 '아까 조회한 그 값' 을 알게(docs/chat-depth-context CD-D5).
      // 앞 발화에 올린 그림의 주소도 — 챗 · 띵킹 · 심의가 앞 대화의 그림으로 다시 본다(T5).
      const history = buildHistory(existing?.messages ?? [], { evidence: true, images: true });
      // 첫 발화 여부 — sendPrefix(심의 트리거)는 첫 발화에만 붙는다(이후는 GLM 이어가기).
      // 사람 발화가 없으면 첫 발화다 — 보내기 알림(어시스턴트)만 있는 대화도 첫 발화에 트리거가 붙는다(docs/chat-ppt PP-D3).
      const isFirstTurn = !existing || !existing.messages.some((m) => m.role === 'user');

      // 유효 지정 전문가·도구 — 기존 대화는 대화에 저장된 것, 새 대화(랜딩)는 draft 를 쓴다.
      const draft = draftPinsRef.current;
      const effPinnedTools = existing ? (existing.pinnedTools ?? []) : draft.tools;
      const effPinnedApps = existing ? (existing.pinnedApps ?? []) : draft.apps;
      const effPinnedAgent = can('feat:expert-chat') ? (existing ? existing.pinnedAgent : draft.agent) : null;
      const effSources = can('plat:webresearch') ? searchSources : [];
      const effPinnedAgentName = existing ? existing.pinnedAgentName : draft.agentName;
      // 보조 전문가 — 주 전문가가 없으면 보조도 없다(첫 명이 목소리다). 권한도 주 전문가와 같이 본다.
      const effHelpers = (effPinnedAgent
        ? (existing ? (existing.pinnedHelpers ?? []) : (draft.helpers ?? []))
        : []).slice(0, 4);

      // 붙인 문서 — 이 발화에만 실린다. 본문은 대화에 남기지 않고(쿼터) 이름·길이만 남긴다.
      // 루틴 턴(이어서 · 고른 뒤 잇기 · RA 초안 올리기 · 다시 시도)은 붙인 그림 · 문서를 싣지도 비우지도 않는다 — 실행기가 읽지 않아 그림은 저장되지
      // 않은 채 칩에서만 사라졌다(R3 반대 검토 2차 #14). 다음 일반 턴의 것으로 남긴다. 켜 둔 루틴을 보내는 입력창은 붙인 것이 있으면 보내지 않는다.
      const docs: AttachedDoc[] = routineReq ? [] : attachedDocsRef.current;
      // 사전 근거 — 붙인 문서(앞, 사람이 방금 고른 것) + 일회성 extra(핸드오프·이어하기)의 근거. 포털 상한(EVID_ITEMS — 엔진과
      // 같은 수)을 넘으면 422 라 여기 **한 자리**에서 끊고, 넘친 수를 이 답의 근거 카드(알림)로 남긴다 — 엔진은 받은 것만 알아
      // 이 절단을 알릴 수 없다. 종전엔 대화 근거·이어하기 승계 근거·문서 병합이 저마다 말없이 120건에서 끊었다.
      const evAll = [
        ...docsAsEvidence(docs),
        ...(Array.isArray(extraDelibOpts?.evidence) ? (extraDelibOpts?.evidence as HandoffEvidence[]) : []),
      ];
      const evDropped = Math.max(0, evAll.length - EVID_ITEMS);
      const imgs: AttachedImage[] = routineReq ? [] : attachedImagesRef.current;
      const userMsg: Message = {
        id: newId(), role: 'user', text, ts: now,
        ...(docs.length ? { docs: docs.map((d) => ({ name: d.name, chars: d.chars, kind: d.meta?.kind })) } : {}),
        // 서버 주소(user_images)가 오기 전까지의 썸네일 — 영속하지 않는다.
        ...(imgs.length ? { localImages: imgs.map((i) => i.dataUrl) } : {}),
      };
      const botId = newId();
      if (routineReq) routineSentRef.current.set(userMsg.id, routineReq);
      // 이 답이 누구 것인지는 **보낼 때** 찍는다 — 나중에 전문가를 바꿔도 과거 답의 주인이
      // 바뀌지 않고, 새로고침해도 남는다(대화 상태만 보면 둘 다 깨진다).
      // 루틴 턴의 답은 지정 전문가의 것이 아니다 — 루틴 가지가 먼저라 그 발화에 전문가가 쓰이지 않는다.
      const botMsg: Message = {
        id: botId,
        role: 'assistant',
        text: '',
        ts: now,
        streaming: true,
        ...(effPinnedAgent && !routineReq ? { persona: { key: effPinnedAgent, name: effPinnedAgentName } } : {}),
        ...(evDropped
          ? {
              delib: {
                evidence: [{
                  source: '사전 근거 건수 초과',
                  text: `근거 ${evAll.length}건 중 뒤쪽 ${evDropped}건은 상한(${EVID_ITEMS}건)을 넘겨 심의에 보내지 않았다.`,
                  included: false,
                  notice: true,
                }],
              },
            }
          : {}),
      };

      // 활성 대화가 없으면(랜딩/새 대화) 첫 전송 시점에 대화를 생성한다.
      let convId = activeId && conversations.some((c) => c.id === activeId) ? activeId : null;
      if (!convId) {
        convId = newId();
        const conv: Conversation = {
          id: convId,
          title: makeTitle(text),
          messages: [userMsg, botMsg],
          createdAt: now,
          updatedAt: now,
          // 랜딩에서 고른 전문가·도구를 새 대화에 옮겨 심고 draft 는 비운다(1회성).
          ...(draft.tools.length ? { pinnedTools: draft.tools } : {}),
          ...(draft.apps.length ? { pinnedApps: draft.apps } : {}),
          ...(draft.agent ? { pinnedAgent: draft.agent } : {}),
          ...(draft.agent && draft.agentName ? { pinnedAgentName: draft.agentName } : {}),
          ...(draft.agent && draft.helpers?.length ? { pinnedHelpers: draft.helpers } : {}),
        };
        setConversations((prev) => [conv, ...prev]);
        setActiveId(convId);
        if (draft.tools.length || draft.apps.length || draft.agent) setDraftPins({ tools: [], apps: [] });
      } else {
        setConversations((prev) =>
          prev.map((c) =>
            c.id !== convId
              ? c
              : { ...c, updatedAt: now, messages: [...c.messages, userMsg, botMsg] },
          ),
        );
      }

      setInput('');
      if (imgs.length) setAttachedImages([]);
      setStreaming(true);
      setRoutineStreaming(Boolean(routineReq));
      // RA 초안 올리기는 끝난 실행에만 간다 — 그칠 실행이 없다(끝난 계획을 받은 이어서도 그렇다 — 아래 onRoutine)
      setRoutineClosed(Boolean(routineReq?.upload_ra));
      liveRef.current = startLive(now);
      const controller = new AbortController();
      abortRef.current = controller;
      streamConvRef.current = convId;
      const cid = convId;
      // 이 스트림의 끝 — 받는 중에 온 보내기 알림이 서버 사본에 붙을 때를 기다린다(addUploadNotice)
      let endStream: () => void = () => undefined;
      const streamEnded = new Promise<void>((res) => {
        endStream = res;
      });
      streamDoneRef.current.set(cid, streamEnded);
      const finishStream = () => {
        endStream();
        if (streamDoneRef.current.get(cid) === streamEnded) streamDoneRef.current.delete(cid);
      };
      // 이 스트림의 끝 정리(마지막 메시지 고침 · 공용 상태 풀기)는 한 번만 한다 — 끝(done) · 중지 · 오류가 모두 이리로 온다. 중지가 화면을
      // 먼저 풀면 사용자가 곧바로 다음 발화를 보낼 수 있다 — 늦게 온 옛 스트림의 끝이 새 스트림의 상태(streaming · 중지 대상)를 지우면 안 된다.
      let settled = false;
      const settle = (last: (m: Message) => Message) => {
        if (settled) return;
        settled = true;
        patch(cid, botId, last);
        setStreaming(false);
        setRoutineStreaming(false);
        setRoutineClosed(false);
        liveRef.current = null;
        abortRef.current = null;
        streamConvRef.current = null;
        stopUiRef.current = null;
        finishStream();
      };
      // 실행 id 를 받기 전에 새 루틴 턴이 끝났다(■ · 받던 중 끊김 · ROUTINE_MAYBE_STARTED 의 오류) — 실행이 서버에 생겼는지 모른다. 다시 시도가 내
      // 실행 목록에서 먼저 찾는다. 그런 턴이면 참이다
      const unknownRun = (): boolean => {
        if (!routineReq?.id || routineReq.run_id || runSeen) return false;
        routineUnknownRef.current.add(userMsg.id);
        return true;
      };
      const cancelled = () => {
        // 실행 id 를 받기 전에 ■ 로 끊은 새 루틴 턴은 루틴 칸이 아직 없다 — 오류 상자가 실행은 서버에서 돌 수 있고 다시 시도가 그것을 찾는다고
        // 말한다(lib/chatErrors). '중단되었습니다' 만으로는 루틴이 멈춘 것으로 읽혔다(R3 반대 검토 2차 #16)
        const lost = !settled && unknownRun();
        settle((m) => ({
          ...m,
          streaming: false,
          status: undefined,
          // 토큰이 이미 조금 왔으면 부분 응답을 그대로 두고, 아니면 취소를 표기.
          error: m.error ?? (m.text ? undefined : lost ? ROUTINE_STOPPED_BEFORE_RUN : '취소됨'),
        }));
      };
      // 중지는 화면을 곧바로 푼다 — 읽기 루프가 멈춰 있으면(숨은 탭 · 멈춘 연결) abort 의 거절이 늦거나 오지 않아 '생각 중' 이
      // 그대로였다(OT-07). 거절이 나중에 와도 위 settled 가 두 번 하지 않는다.
      stopUiRef.current = cancelled;

      // 심의 페이지 등에서 서버 트리거 프리픽스를 자동 부착 — "첫 발화"에만(이후 발화는
      // 일반 챗으로 흘려 심의 로그 위에서 GLM 이어가기가 되게 한다). 직접 입력했으면 존중.
      const applyPrefix = sendPrefix && (isFirstTurn || text.startsWith(sendPrefix.trim()));
      const outbound = applyPrefix && !text.startsWith(sendPrefix.trim()) ? sendPrefix + text : text;

      void (async () => {
        // 서버 정본 확보 — serverKind 설정 시 이 대화의 서버 id 를 보장(없으면 생성).
        // 실패해도 채팅은 계속(로컬 캐시 전용) — cae00 등 서버 저장 미가용 폴백.
        let serverId = existing?.serverId;
        // 보내기 알림이 이 대화의 서버 사본을 만들거나 붙이는 중이면 끝나기를 기다린다 — 알림이 이 발화보다 앞에 적히고, 서버 대화를 둘 만들지 않는다
        const notices = noticeChainRef.current.get(cid);
        if (notices) serverId = serverId ?? (await notices);
        if (serverKind && !serverId) {
          try {
            serverId = await createServerConversation(makeTitle(text), serverKind);
            const sid = serverId;
            serverMetaRef.current.set(sid, now);
            setConversations((prev) => prev.map((c) => (c.id === cid ? { ...c, serverId: sid } : c)));
          } catch {
            serverId = undefined;
          }
        }
        await streamChat(outbound, {
        signal: controller.signal,
        history,
        ...(serverId ? { conversationId: serverId } : {}),
        // 사용자 지정 전문가·도구 — 기존 대화 저장분 또는 랜딩 draft(없으면 미전송).
        ...(effPinnedTools.length ? { pinnedTools: effPinnedTools } : {}),
        ...(effPinnedApps.length ? { pinnedApps: effPinnedApps } : {}),
        ...(effPinnedAgent ? { pinnedAgent: effPinnedAgent } : {}),
        // 이름도 함께 — 서버 대화에 적혀 다른 기기에서 키가 아닌 이름으로 되살아난다.
        ...(effPinnedAgent && effPinnedAgentName ? { pinnedAgentName: effPinnedAgentName } : {}),
        // 여러 명이면 [주 전문가, ...보조] 로 보낸다 — 서버가 첫 명을 목소리로 삼는다.
        ...(effPinnedAgent && effHelpers.length
          ? { pinnedAgents: [effPinnedAgent, ...effHelpers.map((h: { key: string }) => h.key)] }
          : {}),
        searchSources: effSources,
        // 붙인 문서의 **추출문**만 간다(원본 파일은 브라우저를 떠나지 않는다).
        ...(docs.length ? { documents: docs.map((d) => ({ name: d.name, kind: d.meta?.kind, text: d.text })) } : {}),
        // 올린 그림 — 서버가 저장하고 주소를 user_images 로 돌려준다(아래 onUserImages 가 이 발화에 남긴다).
        ...(imgs.length ? { images: imgs.map((i) => ({ name: i.name, mime: i.mime, data: i.dataUrl })) } : {}),
        // 띵킹 모드 — 켠 동안 모든 발화에 실린다. 서버는 명시 슬래시 트리거(/심의 등)를
        // 먼저 보므로, 모드가 켜져 있어도 그 턴에 대놓고 심의를 부르면 심의가 이긴다.
        ...(thinkingRef.current && can('feat:thinking') ? { thinking: true } : {}),
        // 분석 루틴 — 본문 맨 위 칸 routine 으로 간다(아래 delib_opts 에 넣지 않는다). 에이전트 서버는 이 칸을 심의 · 띵킹 · 슬래시보다 먼저 본다.
        ...(routineReq ? { routine: routineReq } : {}),
        // MCP Apps 패널 표지(HA-20) — 이 화면에는 호스트 부품(McpAppPanel)이 있다. 권한이 없으면 싣지 않는다(포털이 손잡이 · 권한을 다시 본다)
        ...(can('feat:panels') ? { uiHost: UI_HOST_TOKEN } : {}),
        // 심의 손잡이(웹 토글) — 켠 것만. 서버 트리거 프리픽스가 붙는 심의 첫 발화에만 의미가 있지만,
        // 이어가기(일반 챗)로 흘러도 agent-server 챗 경로가 무시하므로 항상 실어도 무해하다.
        ...(() => {
          // 패널 손잡이(켠 것만) + 일회성 extra(이어하기 human_note·요약·personas)를 병합
          // 심의는 자유 조회에서 거르므로 delib_opts 에도 실어야 한다. 챗은 top-level
          // search_sources 를 쓴다 — 두 경로가 서버에서 서로 다른 자리에서 걸러진다.
          const w: Record<string, unknown> = { ...delibOptsToWire(delibOptsRef.current),
                      search_sources: effSources, ...(extraDelibOpts ?? {}) };
          // 붙인 문서는 심의에도 **원천 근거 채널**로 넣는다 — 엔진이 이미 '검증 대상이지
          // 결론이 아니다' 로 프레이밍해 좌석에 주므로 별도 통로를 팔 이유가 없다.
          // 문서를 앞에 둔다(사람이 방금 고른 것 = 더 관련). 넘친 수는 위 evDropped 가 알린다.
          if (evAll.length) w.evidence = evAll.slice(0, EVID_ITEMS);
          return Object.keys(w).length > 0 ? { delibOpts: w } : {};
        })(),
        onStatus: (e) =>
          patch(cid, botId, (m) => {
            // 활동 패널용 누적 — 같은 step 연속 중복은 스킵. 건수로 버리지 않는다 — 종전 60건 캡은 도구를 30번 넘게 부른
            // 답에서 앞쪽 호출을 지워 심의로 넘길 근거(conversationEvidence)가 줄었다. 영속 크기는 저장(chatStore)이 따로 줄인다.
            const prev = m.activity ?? [];
            const last = prev[prev.length - 1];
            const activity =
              last && last.step === e.step
                ? prev
                : [
                    ...prev,
                    {
                      ts: Date.now(),
                      step: e.step,
                      tool: e.tool ?? null,
                      ...(e.personas ? { personas: e.personas } : {}),
                      ...(e.tools_used ? { tools_used: e.tools_used } : {}),
                      ...(e.detail ? { detail: e.detail } : {}),
                      ...(e.result_preview ? { result_preview: e.result_preview } : {}),
                      // 호출 · 완료 짝 키와 성패 — 활동 패널이 짝 키로 묶고(ActivityPanel), 다음 턴 이력의 근거가 결과에 인자를 잇는다
                      // (history.turnEvidence). 종전엔 저장하지 않아 패널은 이름으로만 묶였다.
                      ...(e.call ? { call: e.call } : {}),
                      ...(typeof e.ok === 'boolean' ? { ok: e.ok } : {}),
                      // 화면엔 안 쓴다 — 심의 핸드오프가 읽는 날것. 영속 시 예산으로 묶는다.
                      ...(e.result_full ? { result_full: e.result_full } : {}),
                    },
                  ];
            return { ...m, status: e.step, activity };
          }),
        onToken: (e) =>
          patch(cid, botId, (m) => ({ ...m, text: m.text + e.delta, status: undefined })),
        onDelib: (e) => patch(cid, botId, (m) => ({ ...m, delib: mergeDelib(m.delib, e) })),
        onThink: (e) => patch(cid, botId, (m) => ({ ...m, think: mergeThink(m.think, e) })),
        // 루틴 실행 — 계획 · 단계 · 고를 것 · 보고서 · 끝을 이 답의 실행 상태로 합친다(보고서 글은 token 으로 따로 온다).
        onRoutine: (e) => {
          // 끝난 실행의 계획 · 끝('이미 끝났다' 이어서 · 실행의 끝) — 그칠 실행이 없다. 끝 정리 뒤 늦게 온 프레임은 다음 턴의 표시를 건드리지 않는다
          if (!settled && (e.kind === 'plan' || e.kind === 'done') && typeof e.state === 'string' && isRoutineTerminal(e.state))
            setRoutineClosed(true);
          patch(cid, botId, (m) => ({ ...m, routine: mergeRoutine(m.routine, e) }));
        },
        onTools: (e: ToolCatalog) =>
          patch(cid, botId, (m) => ({ ...m, toolCatalog: e, status: undefined })),
        onAgents: (e: AgentCatalog) =>
          patch(cid, botId, (m) => ({ ...m, agentCatalog: e, status: undefined })),
        onResult: (block) =>
          patch(cid, botId, (m) => ({
            ...m,
            result: block,
            text: block.type === 'text' ? block.content : m.text,
            status: undefined,
          })),
        onWarning: (e) => patch(cid, botId, (m) => ({ ...m, warn: e.message })),
        // 생각 글 — 접힌 칸에만(다음 턴 이력 · 영속에는 넣지 않는다). 답한 모델 · 강도는 메시지 아래 표시로.
        onReasoning: (e) => patch(cid, botId, (m) => ({ ...m, reasoning: (m.reasoning ?? '') + (e.delta ?? '') })),
        onMeta: (e) => patch(cid, botId, (m) => ({ ...m, meta: e })),
        // 확인 카드(HA-29) — 단추를 그릴 카드. 본문의 카드 글은 token 으로 따로 온다
        onConfirm: (e) => {
          if (e && typeof e.id === 'string' && Array.isArray(e.calls)) patch(cid, botId, (m) => ({ ...m, confirm: e }));
        },
        // MCP Apps 패널(HA-20) — 포인터는 메시지에, 결과는 이 탭에만(panels.panelPointer 가 lib/mcpApps 의 live 에 둔다)
        onUiResource: (e) => {
          const p = panelPointer(e);
          if (p) patch(cid, botId, (m) => ({ ...m, panels: [...(m.panels ?? []), p].slice(-8) }));
        },
        // 올린 그림의 서버 주소 — 이 발화(사람 메시지)에 남겨 다음 턴 이력에 싣는다. 썸네일도 이 주소로 바꾼다(data URL 은 버린다).
        onUserImages: (e) =>
          patch(cid, userMsg.id, (m) => ({ ...m, images: (e.urls ?? []).filter((u) => typeof u === 'string'), localImages: undefined })),
        onError: (e) => {
          patch(cid, botId, (m) => ({ ...m, error: e.message, status: undefined }));
          // 실행이 서버에 생겼을 수 있는 오류(ROUTINE_MAYBE_STARTED) — 다시 시도는 ■ 로 끊은 턴과 같이 그 실행을 먼저 찾고, 없으면 보낸 요청 그대로다
          if (ROUTINE_MAYBE_STARTED.has(e.code)) unknownRun();
          // 받던 중에 끊긴 것 · 침묵 한도는 실행 전의 거절이 아니다(응답이 흐르기 시작했다) — 되살려 다시 보내게 이끌지 않는다. 게이트웨이 · 실행기
          // 오류는 실행 전의 거절(입력 값)일 수도 있어 값을 되살린다 — 다시 시도가 실행을 찾으면 그 되살린 것은 끈다(retryLast)
          if (e.code !== 'stream_cut' && e.code !== 'agent_stream_idle') rearm(e.message);
        },
        onSignal: (ev) => {
          if (ev === 'routine') runSeen = true; // 실행이 생겼다 — 이 턴이 실패해도 되살리지 않는다(rearm)
          if (liveRef.current) noteFrame(liveRef.current, ev, Date.now());
        },
        onDone: () => settle((m) => ({ ...m, streaming: false, status: undefined })),
        });
      })().catch((err) => {
        // AbortError is expected on stop(); surface anything else.
        if (err instanceof DOMException && err.name === 'AbortError') cancelled();
        else {
          settle((m) => ({ ...m, error: String(err), streaming: false, status: undefined }));
          rearm(String(err));
        }
      });
    },
    [streaming, activeId, conversations, patch, sendPrefix, serverKind, setDraftPins, can, setAttachedImages, setArmedRoutine, searchSources],
  );

  // 이어하기(사람 개입 스티어링) — 끝난 심의에 사람 의견을 넣어, 같은 전문가가 이전 결정을
  // 이어받아 그 의견 방향으로 다시 토론하게 한다. 원 화두는 활성 대화의 첫 사용자 발화에서 취한다.
  const continueDeliberation = useCallback(
    (prior: DelibData, opinion: string, roster?: { key: string; role?: string }[]) => {
      const note = opinion.trim();
      if (!note || streaming) return;
      const conv = conversations.find((c) => c.id === activeId);
      const firstUser = conv?.messages.find((m) => m.role === 'user');
      const topic = (firstUser?.text ?? '').replace(/^\/(심의|deliberate|토의)\s*/, '').trim();
      if (!topic) return;
      // 양보 불가 조항 승계 — 결정문 요약에만 의존하면 조항이 빠져도 아무도 모르고, 그러면
      // 이전 심의가 조항으로 못박은 제약이 이어하기에서 조용히 되돌아간다. 건수로 자르지 않는다 — 좌석에 싣는 수는 엔진이
      // 정하고 넘으면 카드로 알린다(종전 12건 컷은 엔진 상한과 같은 수라 그 카드가 영영 안 떴다). 한 회차가 낼 수 있는 수는
      // 포털 상한(좌석 20 × 라운드 8) 안이다.
      const nonNegotiables = [
        ...new Set(
          (prior.turns ?? [])
            .map((t) => (t.nonNegotiable ?? '').trim())
            .filter(Boolean),
        ),
      ];
      // 이전 회차까지 실제로 돈 라운드 수 — 없으면 회의록이 매 회차 '1R 초기입장' 으로
      // 되돌아가 몇 번째 논의인지 알 수 없다. 발언의 최대 round 가 실측값이다
      // (totalRounds 는 '계획된' 수라 체크포인트로 일찍 멈추면 과대평가된다).
      // 이어 센 번호로 센다 — 회차 안 번호로 세면 이어하기를 두 번 할 때 번호가 또 겹친다(실심의 E2E).
      const roundsSoFar = Math.max(0, ...(prior.turns ?? []).map((t) => t.displayRound ?? t.round ?? 0));
      // 같은 RA 보고서에 페이지로 덧붙인다 — 없으면 회차마다 새 보고서로 흩어진다.
      const priorReport = prior.outcome?.report_id ?? null;
      // 좌석 — 사람이 고른 명단이 우선. 없으면 이전 좌석. ⚠ 서버에서 **복원한** 심의는 personas 가
      // 비어 있어서(발언만 저장된다) 그대로 보내면 엔진이 좌석을 처음부터 새로 발굴했다 — 발언자로 채운다.
      const carried = prior.personas?.length
        ? prior.personas.map((p) => ({ key: p.key, role: p.role ?? '' }))
        : [...new Set((prior.turns ?? []).map((t) => t.persona).filter(Boolean))].map((key) => ({ key, role: '' }));
      const seats = roster?.length ? roster.map((p) => ({ key: p.key, role: p.role ?? '' })) : carried;
      // 이전 회차가 도구로 뽑은 수치를 승계한다 — 조항을 요약에서 분리한 것과 같은 이유다.
      // 요약 문장에 살아남은 것만 넘어가면 나머지는 사라지고, 다음 회차는 같은 걸 다시
      // 조회하거나 못 하면 기억으로 말한다. 기존 evidence 채널을 쓴다(계약 변경 없음).
      const gathered = priorGatheredEvidence(prior.evidence);
      sendMessage('/심의 ' + topic, {
        human_note: note,
        ...(gathered.length ? { evidence: gathered } : {}),
        // 결정문 전문 + 쟁점(뒤). 좌석에 싣는 길이는 엔진이 정하고(머리부터 — 결정문이 우선이다) 줄였으면 카드로 알린다.
        // 종전엔 여기서 8,000자로 잘라 보내 결정문 뒤쪽((5)뒤집힘·(7)신뢰도·risk_spec)이 말없이 빠졌다.
        continue_summary: (prior.decision ?? '') + priorIssueBlock(prior.turns),
        personas: seats,
        ...(roster?.length ? { rescreen: 0 } : {}),
        ...(nonNegotiables.length ? { non_negotiables: nonNegotiables } : {}),
        ...(roundsSoFar > 0 ? { rounds_so_far: roundsSoFar } : {}),
        ...(priorReport ? { append_to_report_id: priorReport } : {}),
        // ⚠ 체크포인트는 **1회성**이다. 패널 토글이 매 발화에 다시 실리므로(아래 sendMessage
        //   의 delibOptsToWire), 켜 둔 채 이어하면 이어하기도 1라운드에서 또 멈춘다.
        //   사용자는 "이어가라고 했는데 또 멈췄다" 를 보게 된다. 여기서 명시적으로 끈다.
        stop_after_round: 0,
        // 기준일 — 앞 회차 글 머리의 값이 이긴다(없었으면 없이 — undefined 는 JSON 에서 빠지고 패널 값도 덮는다). 패널 값은 브라우저마다 따로라
        // 다른 기기에서 연 대화 · 패널을 비운 뒤의 이어하기가 기준일 없이 오늘의 카드로 돌았다(docs/request-1027 HA-11 반대 검토 10-31 — MCP 는
        // 원장의 _CONT_CARRY 가 잇는다). 패널 값과 다르면 이어가기 칸이 그렇다고 밝힌다(DelibView ContinueBar).
        as_of: decisionAsOf(prior.decision),
      });
    },
    [conversations, activeId, streaming, sendMessage],
  );

  // 심의로 넘기기(핸드오프) — 챗 워크스페이스에서 정리한 실데이터(도구결과)를 원천 근거로 실어
  // 현재 대화에서 심의를 연다. 요약이 아니라 날것을 넘긴다(P1). 좌석은 심의가 발굴한다
  // (질문·좌석 확정 브리프 UI 는 후속 P3). 화두는 continueDeliberation 과 같이 첫 사용자 발화에서 취한다.
  const startHandoff = useCallback(
    (opts?: {
      topic?: string;
      personas?: { key: string; role?: string }[];
      chairTemplate?: string;
      modifiers?: string[];
      tools?: string[];
      apps?: string[];
      trigger?: string;
      extraOpts?: Record<string, unknown>;
      /** 브리프에서 사람이 고른 추가 원천(예: 'VOC 먼저 보기'). 대화 근거 **앞**에 두고 합쳐 포털 상한(EVID_ITEMS)까지. */
      extraEvidence?: HandoffEvidence[];
    }) => {
      if (streaming) return;
      const conv = conversations.find((c) => c.id === activeId);
      if (!conv) return;
      const firstUser = conv.messages.find((m) => m.role === 'user');
      const topic = (opts?.topic ?? firstUser?.text ?? '')
        .replace(/^\/(심의|deliberate|토의)\s*/, '')
        .trim();
      if (!topic) return;
      // 사람이 고른 것(extraEvidence)을 앞에. 포털 상한(EVID_ITEMS)은 sendMessage 가 한 자리에서 걸고 넘친 수를 알린다
      // (브리프도 같은 수를 미리 보인다 — mergeEvidence).
      const evidence = [...(opts?.extraEvidence ?? []), ...conversationEvidence(conv)];
      const extra: Record<string, unknown> = {};
      if (evidence.length) extra.evidence = evidence;
      if (opts?.personas?.length) extra.personas = opts.personas;
      if (opts?.chairTemplate) extra.chair_template = opts.chairTemplate;
      if (opts?.modifiers?.length) extra.modifiers = opts.modifiers;
      if (opts?.tools?.length) extra.tools = opts.tools;
      if (opts?.apps?.length) extra.apps = opts.apps;
      if (opts?.extraOpts) Object.assign(extra, opts.extraOpts); // 예: build_plan(구축 계획 3단)
      // sim/test 는 다단 트리거로 넘겨 고정 좌석·2단 파이프라인을 타게 한다(evidence 는 그 경로도 승계).
      sendMessage((opts?.trigger ?? '/심의 ') + topic, extra);
    },
    [conversations, activeId, streaming, sendMessage],
  );

  // 루틴 실행 잇기(R3-design D8) — 활성 대화에 '루틴 이어서: <제목>' 발화로 run_id 를 보낸다. 고를 것을 고른 뒤(pickCandidate)에도,
  // 재기동 뒤 running 으로 남은 실행에도 이 길이다. 켜 둔 루틴은 건드리지 않는다(다음 발화의 것이다). 덧붙인 말은 다시 보내지 않는다 — 실행기가
  // 원장(note)에서 읽는다(이 발화 글은 덧붙인 말이 아니다). uploadRa — 끝난 실행의 저장 보고서를 RA 초안으로 올린다(ra.upload 'ask', R3 C4 · 저절로
  // 올리기(auto)가 실패한 실행의 다시 올리기 — 게이트웨이는 초안이 이미 있으면 다시 만들지 않는다).
  const resumeRoutine = useCallback(
    async (runId: string, title?: string, opts?: { uploadRa?: boolean }) => {
      const id = runId.trim();
      if (!id || !can('feat:routines')) return;
      if (opts?.uploadRa) {
        sendMessage(`RA 초안 올리기: ${title?.trim() || id}`, undefined, { run_id: id, upload_ra: true });
        return;
      }
      sendMessage(`루틴 이어서: ${title?.trim() || id}`, undefined, { run_id: id });
    },
    [can, sendMessage],
  );

  // 실패 재시도 — 활성 대화의 마지막 사용자 발화를 다시 보낸다. 심의 페이지(sendPrefix)에서는
  // 트리거를 강제로 붙여 심의를 재실행한다(재시도는 '첫 발화'가 아니라 prefix 자동적용이 안 됨).
  const retryLast = useCallback(() => {
    if (streaming) return;
    const conv = conversations.find((c) => c.id === activeId);
    const msgs = conv?.messages ?? [];
    const lastUser = [...msgs].reverse().find((m) => m.role === 'user');
    if (!lastUser?.text) return;
    // 루틴 턴은 같은 글을 일반 챗으로 다시 보내지 않는다 — 실행 id 를 받았으면 그 실행을 잇고(새 실행을 또 만들지 않는다), 받기 전에
    // 실패했으면(동시 상한 등) 그때 보낸 요청을 다시 보낸다.
    const reply = msgs.slice(msgs.indexOf(lastUser) + 1).find((m) => m.role === 'assistant');
    const sentRoutine = routineSentRef.current.get(lastUser.id);
    if (reply?.routine?.run_id) {
      // RA 초안 올리기 턴이면 올리기를 다시 — 그 실행은 끝났다(그냥 이어서는 '이미 끝났다' 로 끝난다)
      if (sentRoutine?.upload_ra) void resumeRoutine(reply.routine.run_id, reply.routine.title, { uploadRa: true });
      else void resumeRoutine(reply.routine.run_id, reply.routine.title);
      return;
    }
    if (sentRoutine) {
      if (!can('feat:routines')) return;
      // 실패가 보낸 값을 다시 켜 두었다(sendMessage 의 rearm). 켜 둔 것이 같은 루틴이면 그 값(고르기 창에서 고쳤으면 고친 값)으로 보내고 켜 둔
      // 것을 쓴다 — 고친 값을 두고 옛 값을 또 보내 같은 거절을 되풀이하지 않고, 성공한 뒤 같은 루틴이 다음 발화에 또 실리지 않게. 덧붙인 말은
      // 그때 보낸 것 그대로다(이 발화 글이 '루틴: <제목>' 이어도 덧붙인 말이 되지 않는다).
      const resend = () => {
        const cur = armedRoutineRef.current;
        if (sentRoutine.id && cur?.id === sentRoutine.id) {
          setArmedRoutine(null);
          sendMessage(lastUser.text, undefined, { ...sentRoutine, version: cur.version, inputs: cur.inputs, title: cur.title });
        } else sendMessage(lastUser.text, undefined, sentRoutine);
      };
      // 실행 id 를 받기 전에 끝난 턴(■ · 받던 중 끊김 · 게이트웨이 · 실행기 오류 · 침묵 한도) — 그 실행이 서버에서 돌고 있을 수 있어 같은 요청을 또
      // 보내면 실행이 둘이다. 내 실행 목록에서 같은 루틴 · 이 대화의 실행 가운데 이 대화의 메시지가 아직 가리키지 않는 가장 새것을 찾아 있으면 그것을
      // 잇는다(메시지가 가리키는 실행은 앞 턴의 것이다 — 시각으로 가르지 않는다, findLostRun). 없거나 목록을 못 읽으면 예전처럼 다시 보낸다.
      if (sentRoutine.id && !sentRoutine.run_id && routineUnknownRef.current.has(lastUser.id)) {
        const shown = new Set(msgs.map((m) => m.routine?.run_id).filter((x): x is string => Boolean(x)));
        const epoch = accountEpochRef.current;
        void findLostRun(sentRoutine.id, conv?.serverId, shown).then((runId) => {
          // 찾는 사이에 다른 턴이 흐르기 시작했거나 계정이 바뀌었다 — 둘을 함께 흘리지 않고, 앞 사람의 요청을 다음 사람의 이름으로 보내지 않는다(#36)
          if (streamConvRef.current || accountEpochRef.current !== epoch) return;
          if (!runId) {
            resend();
            return;
          }
          // 그 턴의 실패가 되살려 켜 둔 같은 루틴(까닭이 달렸다 — 고르기 창에서 고쳐 켜면 까닭이 지워진다)은 이 턴의 값이다. 실행을 찾아 이으니 끈다 —
          // 남기면 다음 발화가 같은 루틴을 또 시작해 실행이 둘이다
          const cur = armedRoutineRef.current;
          if (cur && cur.id === sentRoutine.id && cur.reason) setArmedRoutine(null);
          void resumeRoutine(runId, sentRoutine.title);
        });
        return;
      }
      resend();
      return;
    }
    const trig = sendPrefix.trim();
    const text = trig && !lastUser.text.startsWith(trig) ? sendPrefix + lastUser.text : lastUser.text;
    // 다시 보내는 것은 그 발화 그대로다 — 그새 켜 둔 루틴을 싣지 않는다(null)
    sendMessage(text, undefined, null);
  }, [conversations, activeId, streaming, sendMessage, sendPrefix, resumeRoutine, can, setArmedRoutine]);

  // 지정 도구 갱신 — 활성 대화가 있으면 대화에 저장(localStorage 영속), 대화 전(랜딩)이면
  // 다음 새 대화용 draft 에 저장. 빈 배열이면 해제.
  const setPinnedTools = useCallback(
    (names: string[]) => {
      const clean = [...new Set(names.map((n) => n.trim()).filter(Boolean))].slice(0, 12);
      if (activeId) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id !== activeId ? c : { ...c, pinnedTools: clean.length ? clean : undefined },
          ),
        );
      } else {
        setDraftPins({ ...draftPinsRef.current, tools: clean });
      }
    },
    [activeId, setDraftPins],
  );

  // 지정 앱 갱신 — 도구와 같은 저장 규칙. 앱은 서버가 도구로 펼치므로 개수 캡이 3이다.
  const setPinnedApps = useCallback(
    (keys: string[]) => {
      const clean = [...new Set(keys.map((k) => k.trim()).filter(Boolean))].slice(0, 3);
      if (activeId) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id !== activeId ? c : { ...c, pinnedApps: clean.length ? clean : undefined },
          ),
        );
      } else {
        setDraftPins({ ...draftPinsRef.current, apps: clean });
      }
    },
    [activeId, setDraftPins],
  );

  // 지정 전문가 갱신 — 대화 있으면 대화에, 없으면 draft 에. null 이면 해제.
  // name 은 표시용이다. 서버 계약은 그대로 key(agent_type) 하나만 나간다.
  const setPinnedAgent = useCallback(
    (key: string | null, name?: string) => {
      const clean = key?.trim() || undefined;
      const label = clean ? name?.trim() || undefined : undefined;
      if (activeId) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id !== activeId ? c : { ...c, pinnedAgent: clean, pinnedAgentName: label },
          ),
        );
      } else {
        setDraftPins({ ...draftPinsRef.current, agent: clean, agentName: label });
      }
    },
    [activeId, setDraftPins],
  );

  // 보조 전문가 갱신 — 주 전문가와 같은 자리(대화 또는 draft)에 둔다. 주 전문가가 없으면
  // 보조도 의미가 없으므로 보내는 쪽에서 함께 비운다(effHelpers).
  const setPinnedHelpers = useCallback(
    (list: { key: string; name?: string }[]) => {
      const clean = list.filter((h) => h && h.key.trim()).slice(0, 4);
      if (activeId) {
        setConversations((prev) =>
          prev.map((c) => (c.id !== activeId ? c : { ...c, pinnedHelpers: clean })),
        );
      } else {
        setDraftPins({ ...draftPinsRef.current, helpers: clean });
      }
    },
    [activeId, setDraftPins],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    stopUiRef.current?.();
  }, []);

  // 화면이 다시 보일 때(숨은 탭 → 보임) 받는 중인 대화가 RESYNC_QUIET_MS 넘게 조용했으면 서버 사본과 맞춘다(docs/request-1029 P-1 ②).
  // 포털 중계는 브라우저가 읽지 않아도 상류를 끝까지 읽어 서버 사본에 답을 저장한다(P-1 ①). 서버 사본의 마지막이 이 턴의 사람 발화 뒤의 답이면
  // 받는 중 표시를 끝내고 서버 사본으로 바꾼다. 서버에 아직 답이 없으면 아무것도 하지 않는다(답이 오는 중이다).
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return;
      const cid = streamConvRef.current;
      const live = liveRef.current;
      if (!cid || !live || Date.now() - live.signalAt < RESYNC_QUIET_MS) return;
      const conv = convsRef.current.find((c) => c.id === cid);
      const sid = conv?.serverId;
      const asked = [...(conv?.messages ?? [])].reverse().find((m) => m.role === 'user')?.text?.trim();
      if (!sid || !asked) return;
      void getServerConversation(sid)
        .then((detail) => {
          if (!detail || streamConvRef.current !== cid) return;
          const msgs = detail.messages ?? [];
          const last = msgs[msgs.length - 1];
          const lastUser = [...msgs].reverse().find((m) => m.role === 'user');
          if (!last || last.role !== 'assistant' || !String(last.content ?? '').trim()) return;
          if (!lastUser || !String(lastUser.content ?? '').includes(asked)) return; // 서버에 이 턴이 없다(저장 실패 등) — 옛 답으로 바꾸지 않는다
          abortRef.current?.abort();
          stopUiRef.current?.();
          const fresh = serverConvToLocal(detail);      // 받은 사본을 그대로 쓴다(한 번 더 묻지 않는다)
          setConversations((prev) =>
            prev.map((c) => (c.id !== cid ? c : { ...c, title: fresh.title, messages: fresh.messages, updatedAt: fresh.updatedAt })),
          );
        })
        .catch(() => {
          /* 서버 미가용 — 받는 중인 스트림을 그대로 둔다 */
        });
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, []);

  const newConversation = useCallback(() => {
    // 빈 대화를 목록에 만들지 않는다 — activeId=null이 '새 대화(랜딩)' 상태.
    setActiveId(null);
    setInput('');
  }, []);

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      if (streamConvRef.current === id) {
        abortRef.current?.abort();
        stopUiRef.current?.();
      }
      const sid = conversations.find((c) => c.id === id)?.serverId;
      if (sid) {
        serverMetaRef.current.delete(sid);
        void deleteServerConversation(sid).catch(() => {});
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
      setActiveId((prev) => (prev === id ? null : prev));
    },
    [conversations],
  );

  const renameConversation = useCallback(
    (id: string, title: string) => {
      const t = title.trim();
      if (!t) return;
      const sid = conversations.find((c) => c.id === id)?.serverId;
      if (sid) void renameServerConversation(sid, t).catch(() => {});
      // 이름 변경은 updatedAt을 건드리지 않는다(사이드바 순서 유지).
      setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: t } : c)));
    },
    [conversations],
  );

  const openDock = useCallback(() => setOpen(true), []);
  const closeDock = useCallback(() => setOpen(false), []);
  const toggleDock = useCallback(() => setOpen((v) => !v), []);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [conversations, activeId],
  );
  const messages = activeConversation?.messages ?? [];

  return (
    <ChatContext.Provider
      value={{
        conversations,
        activeId,
        activeConversation,
        messages,
        input,
        streaming,
        routineStreaming,
        routineClosed,
        setInput,
        sendMessage,
        continueDeliberation,
        startHandoff,
        retryLast,
        delibOpts,
        setDelibOpts,
        pinnedTools: activeConversation ? (activeConversation.pinnedTools ?? []) : draftPins.tools,
        setPinnedTools,
        pinnedApps: activeConversation ? (activeConversation.pinnedApps ?? []) : draftPins.apps,
        setPinnedApps,
        searchSources,
        setSearchSources,
        attachedDocs,
        setAttachedDocs,
        attachedImages,
        setAttachedImages,
        addUploadNotice,
        markDelibStopped,
        pinnedAgent: activeConversation ? (activeConversation.pinnedAgent ?? null) : (draftPins.agent ?? null),
        pinnedAgentName: activeConversation
          ? (activeConversation.pinnedAgentName ?? null)
          : (draftPins.agentName ?? null),
        setPinnedAgent,
        pinnedHelpers: (activeConversation
          ? (activeConversation.pinnedHelpers ?? [])
          : (draftPins.helpers ?? [])),
        setPinnedHelpers,
        thinking,
        setThinking,
        armedRoutine,
        setArmedRoutine,
        resumeRoutine,
        stop,
        streamLive,
        newConversation,
        selectConversation,
        deleteConversation,
        renameConversation,
        open,
        openDock,
        closeDock,
        toggleDock,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within <ChatProvider>');
  return ctx;
}
