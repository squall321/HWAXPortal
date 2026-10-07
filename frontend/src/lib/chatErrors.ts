// 챗·심의가 실패했을 때 화면이 하는 말 — 걸린 한도와 그 손잡이를 말하고, 다시 시도하면 무슨 일이 생기는지 알린다
//
// MessageList 안에 있던 friendlyError 를 옮겼다(node 시험이 직접 부른다). 종전 문구는 한도가 걸린 세 경우 모두
// 손잡이를 말하지 않았다 — 엔진 타임아웃은 '라운드 수를 줄이거나 무거운 옵션을 끄라' 고 권했고(넉넉히 기다리자는 쪽과
// 정반대다), 프록시 절단은 'TypeError: network error', 범위를 넘은 값은 'Request failed (422)' 였다.
import { DELIB_TIMEOUT_MAX_S } from '../state/chatStore';

const STREAM_CUT = '스트림이 끊겼습니다';
const REJECTED = '요청 값이 허용 범위를 벗어났습니다';

/** 응답이 흐르던 **중에** 연결이 끊겼을 때 메시지에 남기는 글(friendlyError 가 머리말로 알아본다).
 *  ⚠ 심의는 구독이 끊겨도 서버에서 끝까지 돈다(분리 태스크). 곧바로 다시 시도하면 두 번째 심의가 나란히 돌아
 *  공유 LLM 부하가 말없이 두 배가 된다 — 그래서 먼저 볼 곳을 말한다. */
export function streamCutMessage(cause: string): string {
  return (
    `${STREAM_CUT} — 프록시의 침묵 한도(NGINX_AGENT_READ_TIMEOUT)에 걸렸거나 서버가 재기동했을 수 있습니다. ` +
    '심의는 서버에서 계속 돌 수 있습니다 — 결과는 Report Archive 와 대화 목록에서 확인하세요. ' +
    `다시 시도하면 두 번째 심의가 나란히 돕니다. (${cause})`
  );
}

/** 422(검증 거절) 본문을 한 줄로 — 어느 칸이 무엇을 어겼는지. 본문을 못 읽으면 종전 문구다.
 *  detail[i].input 은 쓰지 않는다(요청 본문을 통째로 되싣고 있을 수 있다). */
export function rejectedMessage(status: number, body: unknown): string {
  const detail = body && typeof body === 'object' ? (body as { detail?: unknown }).detail : undefined;
  if (!Array.isArray(detail)) return `Request failed (${status})`;
  const parts = detail
    .filter((d): d is { loc?: unknown; msg?: unknown } => Boolean(d) && typeof d === 'object')
    .map((d) => {
      const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== 'body').join('.') : '';
      return [loc, typeof d.msg === 'string' ? d.msg : ''].filter(Boolean).join(': ');
    })
    .filter(Boolean);
  return parts.length ? `${REJECTED}(${status}) — ${parts.slice(0, 3).join(' / ')}` : `Request failed (${status})`;
}

const afterDash = (r: string) => r.slice(r.indexOf('—') + 1).trim();

/** 원문 오류를 사용자용 안내(원인 + 다음 행동)로 — 막다른 원문 대신 뭘 해야 할지 알려준다. */
export function friendlyError(raw: string): { title: string; hint?: string; retry: boolean } {
  const r = raw || '';
  if (/취소/.test(r)) return { title: '중단되었습니다', retry: true };
  // 포털 릴레이의 침묵 한도 — 포털이 준 문구에 초·손잡이·확인할 곳이 다 들어 있다. 그대로 보인다.
  if (r.includes('AGENT_STREAM_IDLE_TIMEOUT_S'))
    return { title: '에이전트 서버의 신호가 끊겨 구독을 닫았습니다', hint: r, retry: true };
  if (r.startsWith(STREAM_CUT)) return { title: STREAM_CUT, hint: afterDash(r), retry: true };
  // 같은 값으로 다시 보내면 같은 거절이다 — 다시 시도 버튼을 내지 않는다.
  if (r.startsWith(REJECTED))
    return {
      title: REJECTED,
      hint:
        afterDash(r) +
        (r.includes('timeout_s')
          ? ` · 호출 타임아웃(timeout_s)은 LLM 호출 1회 기준이고 ${DELIB_TIMEOUT_MAX_S}초까지입니다(엔진 DELIB_TIMEOUT_MAX_S)`
          : ''),
      retry: false,
    };
  if (/gateway|게이트웨이|도구를 불러오지/i.test(r))
    return { title: '도구 서버에 연결하지 못했습니다', hint: '게이트웨이가 준비 중일 수 있어요. 잠시 후 다시 시도하세요.', retry: true };
  if (/no_personas|전문 페르소나|페르소나/i.test(r))
    return { title: '관련 전문가를 찾지 못했습니다', hint: '화두를 조금 더 구체적으로 바꿔 다시 시도하세요.', retry: true };
  // LLM 호출 한도 — 줄이라고 권하지 않는다. 좌석이 많은 패널은 공유 LLM 에 줄을 서는 시간까지 이 시계에 들어간다.
  if (/timeout|timed out|시간 ?초과/i.test(r))
    return {
      title: 'LLM 호출이 제한 시간에 걸렸습니다',
      hint:
        `옵션의 '호출 타임아웃'(timeout_s, 최대 ${DELIB_TIMEOUT_MAX_S}초)을 늘리거나 운영자가 서버 기본값(DELIB_TIMEOUT_S)을 올립니다. ` +
        `라운드 수나 좌석을 줄일 일이 아닙니다. — ${r}`,
      retry: true,
    };
  if (/심의 처리 중 오류|심의 오류/.test(r))
    return { title: '심의가 완료되지 못했습니다', hint: `${r} — 반복되면 관리자에게 문의하세요.`, retry: true };
  // 응답을 받기도 전에 실패했다(fetch 거절) — 서버에서 도는 것이 없으니 다시 시도해도 겹치지 않는다.
  if (/unreachable|연결|connection|http_5|Failed to fetch|NetworkError|network error/i.test(r))
    return { title: '서버에 연결하지 못했습니다', hint: '네트워크를 확인하고 잠시 후 다시 시도하세요.', retry: true };
  if (/에이전트 처리 중 오류|agent_error/i.test(r))
    return { title: '응답 생성에 실패했습니다', hint: '잠시 후 다시 시도하세요. 반복되면 관리자에게 문의하세요.', retry: true };
  return { title: r || '오류가 발생했습니다', retry: true };
}
