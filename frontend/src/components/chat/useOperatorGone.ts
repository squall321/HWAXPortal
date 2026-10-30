// 고른 HE팀 운영자의 앱 가운데 이 서버 게이트웨이에 없는 것 — 입력창 전문가 알약 · 지정 칩이 보내기 전에 표지를 단다(docs/request-1030 HP-51)
import { useEffect, useState } from 'react';
import { fetchAgentDetail } from '../../api/chat.api';
import { operatorGoneApps } from './AgentFacts';

// 운영자 키 → (없는 앱 라벨, 받은 때). 상세는 콜드에 수 초 걸려 잠깐 붙들어 두되 오래 두지 않는다 — 게이트웨이는 끊긴 앱을 60초마다 다시
// 붙이고 update-all 은 앱을 다시 띄운다. 한 번 받은 값을 탭이 닫힐 때까지 쓰면 돌아온 앱에도 표지가 남고, 나중에 끊긴 앱은 못 짚었다.
const TTL_MS = 60_000;
const cache = new Map<string, { apps: string[]; at: number }>();

/** 보낸 뒤에야 뜨던 주의(에이전트서버 operator_app_missing)와 같은 판정 — 상세(/agent/catalog/agent)의 apps[].connected.
 *  운영자 키(he-)만 묻는다 — 풀의 전문가마다 상세를 부르지 않는다. 상세를 못 받으면 없다고 단정하지 않는다. */
export function useOperatorGone(key: string | null | undefined): string[] {
  const [gone, setGone] = useState<string[]>([]);
  useEffect(() => {
    if (!key?.startsWith('he-')) {
      setGone([]);
      return;
    }
    const hit = cache.get(key);
    setGone(hit?.apps ?? []);
    if (hit && Date.now() - hit.at < TTL_MS) return;
    let alive = true;
    void fetchAgentDetail(key).then((d) => {
      if (d.error) return;
      const g = operatorGoneApps(d);
      cache.set(key, { apps: g, at: Date.now() });
      if (alive) setGone(g); // 늦게 온 응답이 바뀐 전문가의 표지를 덮지 않는다
    });
    return () => {
      alive = false;
    };
  }, [key]);
  return gone;
}
