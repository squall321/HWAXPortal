// Chat data contract — mirrors the backend SSE / agent-response contract (plan §5).

export type Role = 'user' | 'assistant';

// Agent result object — the only payload the renderers parse (plan §5).
// graph/cad are Phase 4; Phase 2 only renders text.
export type ResultBlock =
  | { type: 'text'; content: string }
  | { type: 'graph'; content: string; metadata?: { title?: string; source?: string } }
  | { type: 'cad'; content: string; metadata?: { part_id?: string; format?: string } };

// 활동 패널 항목 — status 이벤트 누적분(어떤 도구·전문가가 쓰였는지). 대화 옆 정보 표시용.
export interface ActivityItem {
  ts: number;
  step: string;
  tool?: string | null;
  personas?: string[];
  tools_used?: string[];
  // 드릴다운 — 도구 호출 입력/결과 요약(서버에서 절단되어 옴).
  detail?: string;
  result_preview?: string;
  /** 같은 호출의 시작·완료를 잇는 키. 없으면 낡은 이벤트다(이름으로 묶는다). */
  call?: string;
  /** 도구 호출이 성공했나. 없으면 **모른다**(실패가 아니다). */
  ok?: boolean;
  /** 심의 핸드오프용 날것(≈1200자) — 화면에는 안 쓴다. 표시용(220자)보다 길 때만 온다. */
  result_full?: string;
  /** upload = 사람이 챗 화면에서 파일을 올려 보낸 결과(포털이 사람 대신 도구를 불렀다) — 다음 턴 이력의 근거가 '조회한 결과' 와
   *  다른 머리로 간다(docs/chat-ppt PP-D3). 없으면 그 턴에 모델이 부른 도구다. */
  origin?: 'upload';
}

// ── 심의(deliberation) 구조화 스트림 — 라이브 회의·스테퍼·수렴 UI(DelibView)의 데이터 ──
export interface DelibTurn {
  /** 이번 회차 안의 라운드(1..N) — 진행률·라운드 묶음·수렴 판정은 이것으로 한다. */
  round: number;
  /** 이어하기 회차를 이어 센 번호(엔진 display_round). 라벨·다음 이어하기의 rounds_so_far 는 이것. */
  displayRound?: number;
  persona: string;
  /** 회의 버블 — 엔진이 화면용으로 줄인 글. 화면은 이것을 그린다. */
  say: string;
  /** 줄이지 않은 발언(엔진 say_full) — 엔진이 버블을 줄였을 때만 온다. 자료 경로(내보내기·서버 사본)는 이것을 쓴다. */
  sayFull?: string;
  position?: string; // 입장 한 줄 요약(R1/R3)
  stance?: string; // R3: 동의|조건부 동의|반대
  /** R3 양보 불가 제약 원문 — 이어하기에서 승계해 이전 결정이 되돌아가지 않게 한다(표시용 say 와 별개). */
  nonNegotiable?: string;
  /** 이 발언이 **누구의 어떤 말을** 반박했는지. 산문(say)에도 녹아 있지만, 그것만으로는
   *  관계를 그릴 수 없다 — 지식 그래프와 이어하기 승계가 쓰는 구조 부본이다. */
  rebut?: { target: string; quote: string; counter: string; basis: string }[];
  ts: number;
}
export interface DelibTally {
  agree: number;
  conditional: number;
  oppose: number;
  /** 스탠스를 표명하지 않았거나 아예 응답하지 못한 좌석. 침묵을 동의로 세지 않기 위한 칸이다.
   *  과거 저장분에는 없으므로 optional. */
  abstain?: number;
  /** 마지막 라운드에 실제로 응답한 좌석 수. total 은 **착석 수**라 둘이 다를 수 있다. */
  responded?: number;
  /** 착석 좌석 수(응답자 수가 아니다) — 예전엔 응답자 수였고 그래서 좌석이 유실되면
   *  '만장일치 3/3' 같은 거짓 표시가 나갔다. */
  total: number;
}
export interface DelibData {
  stage?: string; // recall|discover|r1..rN|decide|report
  stages?: string[]; // 지나온 단계(순서)
  roundN?: number; // 라운드당 패널 수(진행률 분모)
  totalRounds?: number; // 총 라운드 수(가변, 기본 3) — 스테퍼/회의록 동적 렌더용
  /** origin — 좌석 성격. primary(주 도메인) · counter(반대 도메인, 커버리지 게이트가 앉힌 좌석)
   *  · adversary(신규 Job 지정 반대석 — red-team/반증/반대) · carry(이어하기 유임)
   *  · new(이어하기 재심사로 합류). 없으면 primary 로 본다. */
  personas?: { key: string; role?: string; origin?: 'primary' | 'counter' | 'adversary' | 'carry' | 'new' }[];
  // 근거 카드 — 한 심의에 복수 출처가 올 수 있어 배열(SignalForge 환기 + 정량 근거 선주입).
  // 과거 저장분은 단일 객체일 수 있어 소비처는 배열/객체 양쪽을 허용한다.
  // notice — 근거가 아니라 **알림**인 카드(의장 전사를 줄였다 · 좌석이 유실됐다 · 앱 범위를 못 좁혔다). included=false 로
  // 오지만 '좌석에 주지 않은 근거' 가 아니다(좌석은 전부 받았다) — 엔진이 깃발로 가른다. 과거 저장분에는 없다.
  evidence?: { source: string; text: string; included: boolean; notice?: boolean }[];
  turns?: DelibTurn[];
  decision?: string;
  /** 쉬운 설명 — 비전문가용 정리(정식 심의 단계 'explain' 산출물). */
  plain?: string;
  outcome?: {
    report_id?: number | null;
    title?: string;
    tally?: DelibTally;
    unanimous?: boolean;
  };
}
// 심의 손잡이(웹 토글) — 켠 것만 서버로 전송, 나머지는 agent-server env 기본값. GLM 리뷰 §5.
// 불리언=0/1 플래그, chair_bestof=의장 후보 수(1=끔), timeout_s=호출당 타임아웃(초·미지정=기본).
export interface DelibOpts {
  evidence_prepass?: boolean;
  rebut_quote?: boolean;
  prose_first?: boolean;
  cross_exam?: boolean;
  anchor?: boolean;
  chair_cite?: boolean;
  chair_bestof?: number;
  rounds?: number;
  timeout_s?: number;
  /** 1이면 초기 라운드까지만 돌고 멈춘다(인간 체크포인트). 결정문 대신 전원 초기 입장이
   *  내려오고, 이어하기 폼으로 의견을 보태면 좌석 재심사가 그 방향의 도메인을 불러온다. */
  stop_after_round?: number;
  /** MX 백서 LLM 위키에도 결정문을 남긴다(기본 꺼짐). 범위는 내 소속이고, 소속이 없으면 '내 후보' 로 간다(docs/mxwp-wiki P8). */
  wiki?: boolean;
  // ── 이어하기(사람 개입 스티어링) 필드 — 손잡이가 아니라 승계 데이터다 ──
  /** 이번 회차에서 패널이 반드시 정면으로 다뤄야 할 사람의 의견. 매 라운드 프롬프트에 주입된다. */
  human_note?: string;
  /** 이전 심의 요약(보통 직전 결정문). 이어하기 1라운드의 출발점. */
  continue_summary?: string;
  /** 이전 좌석. 서버가 유임으로 잡고, 실효 질문으로 재심사해 신규 좌석을 더한다. */
  personas?: { key: string; role?: string }[];
  /** 이전 심의의 양보 불가 조항. 요약에 섞지 않고 따로 넘겨야 승계가 보장된다 —
   *  빠지면 이전 결정이 조용히 되돌아간다. */
  non_negotiables?: string[];
  /** 이번 발화에서 우선 사용할 도구 이름. 심의가 실제로 호출해 정량 근거로 주입한다. */
  tools?: string[];
  /** 라운드 중 전문가 자유 조회를 이 앱들로 좁힌다. tools 와 달리 전량 호출하지 않는다. */
  apps?: string[];
  /** 인터넷 소스 토글. 켠 소스의 도구만 바인딩된다 — 끄면 모델의 도구 목록에 아예 없다. */
  search_sources?: SearchSource[];
}

/** 인터넷 소스. 사내 자산은 나가지 않으므로 토글 대상이 아니다. */
export type SearchSource = 'scholar' | 'web';

// ── 띵킹 모드 — 답할 수 있는 전문가만 각자 답한다(회의 아님) ──────────────────
// 심의(DelibData)와 형제이지만 구조가 다르다. 라운드도 표결도 결정문도 없고, 좌석마다
// '답했나 기권했나' 와 '기권했으면 어디로 넘겼나' 가 단위다.
export interface ThinkSeat {
  key: string;
  name?: string;
  domain?: string;
  /** recommend_agents 의 합성 점수. 코사인이 아니라 순위용이다(절대값 비교 금물). */
  score?: number;
  /** 질의 토큰이 좌석 프로필에 포함된 어휘 비율(0~1). 벡터와 독립인 신호다. */
  desc_match?: number;
  sections?: number;
  records?: number;
  /** 예심 — 그 좌석의 실제 바인딩 문서에서 나온 근거 수. */
  hits?: number;
  screened?: boolean;
  screenReason?: string;
  /** 본심 — answer(답함) · pass(기권) · error(응답 실패, 기권 아님). */
  verdict?: 'answer' | 'pass' | 'error';
  /** verdict='error' 의 사유(타임초과 · 형식 실패 · 예외 원문). 다음 행동이 갈린다 —
   *  타임초과는 재시도, 형식 실패는 질문을 바꾸는 쪽이다. 없으면 서버가 안 보낸 것(구 버전). */
  error?: string;
  scope?: string;
  answer?: string;
  basis?: string[];
  /** 기권 좌석이 지목한 분야(위임 사슬의 입력). */
  refer?: string[];
  /** 소집된 홉. 0=최초 소집, 1 이상=위임으로 합류. */
  hop?: number;
}
export interface ThinkData {
  seats?: ThinkSeat[];
  handoffs?: { phrases: string[]; seats: string[] }[];
  summary?: {
    answered: number;
    passed: number;
    screened_out: number;
    errored: number;
    /** 답변 상한에 걸려 **묻지 않은** 좌석 수. 0이 아니면 화면이 그렇게 말해야 한다. */
    capped?: number;
    hops: number;
    no_answer: boolean;
  };
}
// SSE `think` 이벤트 payload — kind 별로 위 필드의 부분집합이 실려온다.
export interface ThinkEvent {
  kind: 'roster' | 'screen' | 'verdict' | 'answer' | 'handoff' | 'summary';
  [k: string]: unknown;
}

// SSE `delib` 이벤트 payload — kind 별로 위 필드의 부분집합이 실려온다.
export interface DelibEvent {
  kind: 'stage' | 'evidence' | 'personas' | 'turn' | 'decision' | 'plain' | 'outcome';
  [k: string]: unknown;
}

// ── 분석 루틴(docs/analysis-routines R3) — 챗에서 켠 루틴을 에이전트 서버의 실행기가 단계로 돈다 ──
// 단계 · 실행 상태의 정본은 포털 원장이다(app/procedures/routines.py STAGE_STATES · RUN_STATES). 화면은 SSE 와 GET /routines-api/runs/{id} 로 읽는다.
export type RoutineStepState = 'pending' | 'running' | 'ok' | 'empty' | 'ambiguous' | 'denied' | 'not_connected' | 'unavailable' | 'failed' | 'skipped';
export type RoutineRunState = 'queued' | 'running' | 'waiting' | 'done' | 'failed' | 'cancelled' | 'interrupted';
/** SSE `routine` 이벤트 payload — kind 로 가른다(R3-design §3.2). 모든 프레임에 run_id 가 있다. */
export interface RoutineEvent {
  kind: 'plan' | 'step' | 'step_done' | 'gate' | 'report' | 'done';
  run_id: string;
  [k: string]: unknown;
}
/** 고를 것 하나 — 기준 키 후보가 여럿일 때 사람이 고른다(POST /routines-api/runs/{id}/steps/{step}/pick). */
export interface RoutineCandidate {
  label: string;
  key: string;
}
export interface RoutineStepView {
  id: string;
  title: string;
  kind: string;
  /** 포털이 원장과 맞대 고친 상태(RoutineStepState) — 모르는 값이 와도 그대로 둔다. */
  state: string;
  summary?: string;
  reason?: string;
  flags?: string[];
  calls?: number;
  /** 도는 동안의 한 줄(심의 진행 '라운드 2/3 · 좌석 발언' 같은 것) — 단계가 닫히면 지운다. */
  detail?: string;
  backends?: string[];
  label?: string;
}
/** 메시지에 붙는 루틴 실행 — 흐르는 동안 SSE 로 채우고, 흐르지 않는 메시지는 화면이 run_id 로 포털에서 다시 읽는다. */
export interface RoutineState {
  run_id: string;
  routine_id?: string;
  title: string;
  /** 실행 상태(RoutineRunState). 서버 사본에서 되살렸는데 상태가 없으면 '' 다(모른다). */
  state: string;
  steps: RoutineStepView[];
  gate?: { step: string; candidates: RoutineCandidate[]; message?: string };
  report?: {
    ra_upload?: string;
    ra_report_id?: string | number | null;
    ra_error?: string | null;
    ra_next?: string | null;
    warnings?: string[];
  };
  /** 이 턴이 이어서 · 다시 붙기로 시작했다(plan 프레임의 resumed). */
  resumed?: boolean;
  reason?: string;
}
/** 요청 칸 `routine`(포털 RoutineReq · extra=forbid) — 새 실행은 id · version · inputs · note, 이어서 · 다시 붙기는 run_id 만,
 *  끝난 실행의 RA 초안 올리기는 run_id · upload_ra. */
export interface RoutineRequest {
  id?: string;
  version?: number;
  inputs?: Record<string, unknown>;
  /** 사용자가 덧붙인 말 — 루틴을 켜 두고 사람이 쓴 글(없으면 ""). 글 없이 보낼 때 싣는 '루틴: <제목>' 은 덧붙인 말이 아니다.
   *  새 실행에만 간다 — 실행기가 원장에 남겨 이어서 · 고른 뒤 잇기에도 그 말을 쓴다(포털 상한 2,000자). */
  note?: string;
  run_id?: string;
  /** 끝난 실행의 저장 보고서를 RA 초안으로 올린다(ra.upload 'ask' — 화면의 'RA 초안 올리기'). run_id 와 함께만 보낸다. */
  upload_ra?: boolean;
}

// 도구 카탈로그(SSE `tools` 이벤트) — '/도구' 검색 시 서버가 추천+전체 목록을 내려준다.
// 사용자가 직접 선택한 도구는 대화의 pinnedTools 가 되어 이후 발화에서 우선 사용된다.
export interface ToolInfo {
  name: string;
  desc: string;
  score?: number;
  /** 소유 MCP 앱 키·이름 — 앱별 계층 선택용(게이트웨이 /tools-map 유래). */
  group?: string;
  group_label?: string;
  /** 영역(하는 일) 키·이름 — 게이트웨이 tool_areas.json 판정. ''/없음 = 미분류. */
  area?: string;
  area_label?: string;
}
/** MCP 앱 한 건 — 앱 단위 선택(pinnedApps)의 단위. tool_count 는 이 사용자에게 보이는 수. */
export interface ToolApp {
  app: string;
  label: string;
  desc?: string;
  tool_count: number;
}
/** 도구 영역 한 건 — 앱이 아니라 '하는 일'로 묶은 1단 필터. area='' 는 미분류. */
export interface ToolArea {
  area: string;
  label: string;
  desc?: string;
  tool_count: number;
}
export interface ToolCatalog {
  query?: string;
  recommended: ToolInfo[];
  all: ToolInfo[];
  /** 앱 목록 — 없으면(구 서버) all[].group 으로 프론트가 재구성한다. */
  apps?: ToolApp[];
  /** 영역 목록 — 없으면(구 서버) all[].area 로 재구성, 그마저 없으면 영역 칩을 안 그린다. */
  areas?: ToolArea[];
}

// 전문가 카탈로그(SSE `agents` 이벤트) — '/전문가' 검색 시 서버가 추천+전체 풀을 내려준다.
// 도구(ToolCatalog)와 대칭인 채널인데 오래 소비처가 없어 조용히 버려지고 있었다.
export interface AgentCatalog {
  query?: string;
  recommended: { key: string; name: string; desc?: string }[];
  pool: { key: string; name: string }[];
  /** [도메인 코드, 인원] — 서버가 인원 많은 순으로 정렬해 준다. */
  domains?: [string, number][];
}

export interface Message {
  id: string;
  role: Role;
  // For assistant messages this fills incrementally from `token` deltas, then
  // settles to the final `result` block. User messages are plain text.
  text: string;
  // Unix ms — set when the message is created; survives persistence round-trips.
  ts?: number;
  result?: ResultBlock;
  // Transient status line shown while the agent works (from `status` events).
  status?: string;
  // status 이벤트 누적 — 활동 패널(도구·전문가·진행)용. 영속됨.
  activity?: ActivityItem[];
  // 심의 구조화 데이터 — 라이브 회의/스테퍼/수렴 렌더(DelibView)용. 영속됨.
  delib?: DelibData;
  // 도구 카탈로그(SSE tools 이벤트) — 도구 선택 카드(ToolCatalogBlock) 렌더용. 영속됨.
  toolCatalog?: ToolCatalog;
  // 전문가 카탈로그(SSE agents 이벤트) — 전문가 선택 카드용. toolCatalog 와 같이 영속하지
  // 않는다(풀이 700명 넘어 대화마다 쌓으면 localStorage 쿼터를 먹는다).
  agentCatalog?: AgentCatalog;
  /** 이 답이 **누구의 것**인지 — 지정 전문가(페르소나)로 보낸 발화의 답에 전송 시점에 찍는다.
   *  대화 상태(pinnedAgent)만 보면 나중에 전문가를 바꿨을 때 과거 답까지 그 사람 것으로
   *  보이고, 새로고침하면 아예 사라진다. name 은 표시용(서버 계약은 여전히 key=agent_type). */
  persona?: { key: string; name?: string };
  // 띵킹 구조화 데이터 — 좌석별 답변·기권 렌더(ThinkView)용. 영속됨.
  think?: ThinkData;
  /** 이 발화에 붙인 문서 — **이름과 길이만** 남긴다. 본문(수만 자)까지 대화에 넣으면
   *  localStorage 쿼터를 바로 먹는다(agentCatalog 를 안 남기는 것과 같은 이유). */
  docs?: { name: string; chars: number; kind?: string }[];
  /** 이 발화에 올린 그림의 서버 주소(/agent/artifacts/…, SSE user_images) — 다음 턴 이력에 실려 챗 · 띵킹 · 심의가 다시 본다(T5).
   *  주소만이라 작다 — 영속된다. */
  images?: string[];
  /** 서버 주소가 오기 전의 썸네일(data URL) — 화면에만, 영속하지 않는다(쿼터). user_images 가 오면 지운다. */
  localImages?: string[];
  error?: string;
  // 자격증명 강등 등 치명적이지 않은 경고 — 심의가 서비스 계정으로 근거를 모은 경우.
  // error 와 달리 응답을 막지 않고 옆에 지속 표시한다(무음 강등 가시화).
  warn?: string;
  streaming?: boolean;
  /** 챗 서버가 생각한 글(SSE reasoning) — 접힌 '생각 중' 칸에만 보인다. 다음 턴 이력에 넣지 않고 영속하지 않는다(수만 자 — 쿼터). */
  reasoning?: string;
  /** 이 턴에 답한 모델 · 생각 설정(SSE meta) — 넘김이 일어나면 같은 질문에 답의 깊이가 달라진다. 영속됨(작다). */
  meta?: TurnMeta;
  /** 분석 루틴 턴의 실행(SSE routine — mergeRoutine). 영속됨(단계 12개까지라 작다). 서버 사본은 포인터(run_id · 제목 · 상태)만 쥔다. */
  routine?: RoutineState;
  /** 확인 카드(SSE confirm, HA-29) — 단추를 그린다. 영속됨(작다). 서버 사본에는 본문의 카드 글만 있다. */
  confirm?: ConfirmCard;
}

/** 에이전트 서버가 턴 끝에 내는 meta — models 는 이 턴의 모델 호출 수(모델 이름 → 횟수). docs/chat-depth-context C3. */
export interface TurnMeta {
  models: Record<string, number>;
  chat_model?: string | null;
  thinking?: boolean | null;
  effort?: string | null;
  fallback_to?: string | null;
  /** 자기검증 — 초안을 근거와 대조해 고친 결과(에이전트 서버, docs/chat-self-check). 끈 서버 · 옛 메시지는 없다. */
  self_check?: SelfCheck | null;
}

// 챗 자기검증 결과 — ok 고칠 것 없음 · fixed 고친 답이 본문 · flagged 짚기만 했다(초안이 본문, 10-30 HA-27) ·
// skipped 짧은 잡담이라 건너뜀 · suspect · failed · unreadable 은 검증하지 못해 초안이 본문이다(reason 이 까닭).
export interface SelfCheck {
  status: 'ok' | 'fixed' | 'flagged' | 'skipped' | 'suspect' | 'failed' | 'unreadable';
  fixes?: string[];
  /** 짚은 곳(반영하지 않음) — 검토자의 [짚은 점]과, 조회 결과 원문과 어긋나 답에 넣지 않은 고침(HA-27). */
  flags?: string[];
  /** 원문에 있는 값을 지우거나 바꿔 버린 고침 — QA 용이라 화면에 보이지 않고 브라우저 사본에 남기지 않는다(chatStore). */
  dropped?: string[];
  /** 관문이 돈 턴만 — 넣음 · 짚음 · 버림 수(QA 용). */
  gate?: Record<string, unknown>;
  reason?: string;
  ms?: number;
}

/** 확인 카드의 호출 하나(SSE confirm, 10-30 HA-29) — 무엇 · 인자 · 예상 작업량은 본문의 카드 글에도 같다. */
export interface ConfirmCall {
  tool: string;
  app?: string;
  kind: 'job' | 'write' | 'confirm';
  args_text: string;
  workload?: string;
  again: boolean;
}

/** 확인 카드(SSE confirm) — 사람이 이번 말로 시키지 않았거나 되돌리기 어려운 작업은 에이전트 서버가 보내지 않고 멈춘다.
 *  단추는 approve_text · decline_text 를 다음 말로 보낸다. 서버는 카드를 30분 · 한 번만 받는다(expires_at — epoch ms). */
export interface ConfirmCard {
  id: string;
  expires_at: number;
  calls: ConfirmCall[];
  approve_text: string;
  decline_text: string;
}

// 대화 한 건 — localStorage('hwax.chat.*') 영속 단위 (chatStore.ts가 직렬화 담당).
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  // 서버 대화 저장소 정본 id — 있으면 /agent/chat 이 이 대화에 user+assistant 를 서버 저장.
  // 서버에서 로드된 대화(MCP 심의 포함)는 id === serverId. 웹 생성분은 전송 시 발급받아 채움.
  serverId?: string;
  /** 브라우저 사본을 저장 한도(쿼터)로 줄였다 — 열 때 서버 정본에서 줄인 칸을 되채운다(ChatContext · fillTrimmed). */
  cacheTrimmed?: boolean;
  /** 줄인 사본을 서버 정본으로 되채우지 못했다(메시지 모양이 다르다) — 이 세션에서만 쥐는 값이라 저장하지 않는다. 대화 머리가 알린다. */
  cacheFillFailed?: boolean;
  // 사용자 지정 우선 도구 — 도구 카탈로그에서 선택. 이 대화의 이후 발화에 pinned_tools 로 실린다.
  pinnedTools?: string[];
  // 사용자 지정 우선 앱 — 앱을 고르면 그 앱의 도구 전체가 우선 사용된다(서버가 펼침).
  pinnedApps?: string[];
  // 인터넷 소스 토글 — undefined 면 종전 동작, 배열이면 그 소스만 바인딩된다(빈 배열=전부 끔).
  searchSources?: SearchSource[];
  // 사용자 지정 전문가(agent_type) — '전문가와 대화' 모드. 이후 발화에 pinned_agent 로 실린다.
  pinnedAgent?: string;
  // 그 전문가의 사람 이름 — 화면 표시용이다. 없으면 키를 그대로 보여 준다(구 저장분).
  pinnedAgentName?: string;
  /** 보조 전문가 — 주 전문가 뒤에 서서 판단 기준·도구만 빌려준다(답은 한 목소리다). */
  pinnedHelpers?: { key: string; name?: string }[];
}

// SSE event payloads (plan §5).
export interface StatusEvent {
  step: string;
  tool: string | null;
  // 심의 경로가 얹는 구조화 정보 — 활동 패널용(없으면 무시).
  personas?: string[];
  tools_used?: string[];
  detail?: string;
  result_preview?: string;
  /** 같은 호출의 시작·완료를 잇는 키. 없으면 낡은 이벤트다(이름으로 묶는다). */
  call?: string;
  /** 도구 호출이 성공했나. 없으면 **모른다**(실패가 아니다). */
  ok?: boolean;
  result_full?: string;
}
export interface TokenEvent {
  delta: string;
}
export interface ErrorEvent {
  code: string;
  message: string;
}

export interface ChatState {
  open: boolean;
  messages: Message[];
  input: string;
  streaming: boolean;
}
