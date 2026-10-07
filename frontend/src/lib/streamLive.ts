// 챗·심의 스트림이 살아 있는지를 화면 문장으로 옮긴다 — 서버 heartbeat(SSE ping)와 마지막 진행 시각만 본다
//
// 브라우저는 스트림을 끊지 않는다(타임아웃도 자동 중단도 없다 — 긴 심의를 끊을지는 중지 버튼을 쥔 사람이 정한다).
// 대신 빠져 있던 것이 '살아 있다' 는 표시였다: 깜박이는 점과 마지막 상태줄뿐이라, 한 시간 전에 죽은 스트림과
// 생각 중인 좌석이 똑같이 보였다.

export interface StreamLive {
  /** 어떤 프레임이든(heartbeat 포함) 마지막으로 받은 시각(ms). */
  signalAt: number;
  /** heartbeat 가 아닌 프레임(상태·발언·토큰 …)을 마지막으로 받은 시각(ms). */
  progressAt: number;
  /** 이 스트림에서 heartbeat 를 한 번이라도 받았다. 못 받았으면 heartbeat 가 없는 옛 서버일 수 있어
   *  침묵을 '끊김' 으로 읽지 않는다 — 그런 서버에서는 LLM 호출 한 번이 통째로 조용하다. */
  pinged: boolean;
}

/** 엔진 heartbeat 의 SSE 이벤트 이름. 내용은 없다 — 왔다는 사실이 전부다. */
export const HEARTBEAT_EVENT = 'ping';
// 서버는 15초마다 heartbeat 를 낸다(엔진 DELIB_HEARTBEAT_S). 세 번이 빠지면 끊겼을 수 있다고 말한다.
export const SILENT_AFTER_MS = 45_000;
// 진행이 이만큼 멎기 전에는 아무 말도 안 한다 — 토큰이 흐르는 동안 '0초 전' 이 깜박이지 않게.
export const QUIET_BEFORE_MS = 10_000;

export function startLive(now: number): StreamLive {
  return { signalAt: now, progressAt: now, pinged: false };
}

/** 프레임 하나를 받았다 — heartbeat 는 신호 시각만, 나머지는 진행 시각까지 옮긴다. */
export function noteFrame(live: StreamLive, event: string, now: number): void {
  live.signalAt = now;
  if (event === HEARTBEAT_EVENT) live.pinged = true;
  else live.progressAt = now;
}

/** 흐른 시간을 사람 말로 — 59초까지는 초, 그 뒤는 분, 한 시간부터는 시간과 분. */
export function ago(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}분`;
  return m % 60 ? `${Math.floor(m / 60)}시간 ${m % 60}분` : `${Math.floor(m / 60)}시간`;
}

export interface Liveness {
  /** alive = heartbeat 가 오고 있다 · silent = 오던 heartbeat 가 끊겼다 · unknown = heartbeat 를 본 적이 없다 */
  state: 'alive' | 'silent' | 'unknown';
  text: string;
}

/** 지금 화면에 할 말. 말할 것이 없으면(방금까지 진행이 있었다) null. */
export function liveness(live: StreamLive, now: number): Liveness | null {
  const sinceSignal = now - live.signalAt;
  const sinceProgress = now - live.progressAt;
  if (live.pinged && sinceSignal >= SILENT_AFTER_MS) {
    return {
      state: 'silent',
      text: `신호 없음 ${ago(sinceSignal)} — 연결이 끊겼을 수 있습니다. 심의는 서버에서 계속 돌 수 있으니, 다시 시작하기 전에 Report Archive 와 대화 목록을 확인하세요`,
    };
  }
  if (sinceProgress < QUIET_BEFORE_MS) return null;
  if (live.pinged) return { state: 'alive', text: `서버 살아 있음 · 마지막 진행 ${ago(sinceProgress)} 전` };
  return { state: 'unknown', text: `마지막 진행 ${ago(sinceProgress)} 전` };
}
