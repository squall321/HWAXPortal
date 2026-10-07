// 기다리는 동안 흐른 초를 센다 — 스피너 옆 '몇 초째' 표시용이다(브라우저 타임아웃이 아니다. 한도는 서버 한 곳에만 둔다)
import { useEffect, useState } from 'react';

/** active 인 동안 1초마다 다시 그리게 하고, active 가 된 뒤 흐른 초를 준다. 꺼지면 0 으로 돌아간다. */
export function useElapsed(active: boolean): number {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t0 = Date.now();
    setSec(0);
    const h = window.setInterval(() => setSec(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => window.clearInterval(h);
  }, [active]);
  return active ? sec : 0;
}
