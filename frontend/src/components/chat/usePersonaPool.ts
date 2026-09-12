// 전문가 전체 풀 로더 — 명부(키·이름)를 먼저 받아 조직도를 그리고, 태그는 뒤에서 받아 얹는다
import { useEffect, useState } from 'react';
import { fetchDeliberateExperts, type PoolExpert } from '../../api/chat.api';

// 풀은 780명 규모라 화면을 열 때마다 다시 받으면 낭비다. 세션 안에서는 한 번만 받는다
// (전문가 등록은 AIDataHub 관리 화면에서 일어나므로 대화 중 바뀌는 값이 아니다).
//
// 2단으로 받는다. 전체 응답의 69%(301KB)가 **태그**인데 태그는 검색에만 쓰이고 트리를 그리는
// 데는 키·이름이면 된다. 서버도 light 호출에서는 추천(recommend_agents 최대 5회)을 건너뛴다.
// 그래서 ① 명부로 조직도를 즉시 그리고 ② 전체를 뒤에서 받아 조용히 갈아 끼운다(태그 검색이
// 그때부터 된다). 사람은 트리를 훑는 동안 기다리지 않는다.
let cache: PoolExpert[] | null = null;      // 태그까지 실린 전체
let roster: PoolExpert[] | null = null;     // 명부만(키·이름)
let inflight: Promise<PoolExpert[]> | null = null;
let fullInflight: Promise<PoolExpert[]> | null = null;

function loadRoster(): Promise<PoolExpert[]> {
  if (cache) return Promise.resolve(cache);
  if (roster) return Promise.resolve(roster);
  if (!inflight) {
    inflight = fetchDeliberateExperts('전체 카탈로그 조회', undefined, undefined, true)
      .then((r) => {
        if (r.pool.length) roster = r.pool;
        return r.pool;
      })
      .finally(() => {
        inflight = null; // 실패했으면 다음 열림에서 다시 시도한다
      });
  }
  return inflight;
}

function loadFull(): Promise<PoolExpert[]> {
  if (cache) return Promise.resolve(cache);
  if (!fullInflight) {
    fullInflight = fetchDeliberateExperts('전체 카탈로그 조회')
      .then((r) => {
        if (r.pool.length) cache = r.pool;
        return r.pool;
      })
      .finally(() => {
        fullInflight = null;
      });
  }
  return fullInflight;
}

export function usePersonaPool(): { pool: PoolExpert[]; loading: boolean; failed: boolean } {
  const [pool, setPool] = useState<PoolExpert[]>(() => cache ?? roster ?? []);
  const [loading, setLoading] = useState(!(cache ?? roster));
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    if (!cache) {
      void loadRoster()
        .then((p) => {
          if (!alive) return;
          setPool((cur) => (cur.length && cache ? cur : p));
          setFailed(p.length === 0);
        })
        .catch(() => alive && setFailed(true))
        .finally(() => alive && setLoading(false));
      // 전체(태그)는 뒤에서 — 도착하면 조용히 갈아 끼운다. 실패해도 트리는 그대로 쓴다.
      void loadFull()
        .then((p) => {
          if (alive && p.length) setPool(p);
        })
        .catch(() => {});
    }
    return () => {
      alive = false;
    };
  }, []);

  return { pool, loading, failed };
}
