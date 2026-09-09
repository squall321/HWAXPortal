// 전문가 전체 풀 로더 — 한 번 받아 모듈에 캐시한다(빠른 선택기와 조직도가 같은 목록을 본다)
import { useEffect, useState } from 'react';
import { fetchDeliberateExperts, type PoolExpert } from '../../api/chat.api';

// 풀은 780명 규모라 화면을 열 때마다 다시 받으면 낭비다. 세션 안에서는 한 번만 받는다
// (전문가 등록은 AIDataHub 관리 화면에서 일어나므로 대화 중 바뀌는 값이 아니다).
let cache: PoolExpert[] | null = null;
let inflight: Promise<PoolExpert[]> | null = null;

function load(): Promise<PoolExpert[]> {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = fetchDeliberateExperts('전체 카탈로그 조회')
      .then((r) => {
        if (r.pool.length) cache = r.pool;
        return r.pool;
      })
      .finally(() => {
        inflight = null; // 실패했으면 다음 열림에서 다시 시도한다
      });
  }
  return inflight;
}

export function usePersonaPool(): { pool: PoolExpert[]; loading: boolean; failed: boolean } {
  const [pool, setPool] = useState<PoolExpert[]>(() => cache ?? []);
  const [loading, setLoading] = useState(!cache);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (cache) return;
    let alive = true;
    void load()
      .then((p) => {
        if (!alive) return;
        setPool(p);
        setFailed(p.length === 0);
      })
      .catch(() => alive && setFailed(true))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  return { pool, loading, failed };
}
