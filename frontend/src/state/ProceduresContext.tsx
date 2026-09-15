// 절차 페이지 스코프 상태 — 도구 카탈로그 + 실행 폴링
//
// ⚠ App() 루트가 아니라 '/procedures/*' 라우트 요소 안에서만 Provider 를 건다(선례: '/deliberate').
// ⚠ useChat() 을 쓰지 않는다 — 도구 선택이 챗의 pinnedTools 로 새면 안 된다.
//
// 진행 상태는 **폴링**으로 본다. SSE 를 내면 nginx 두 파일을 같이 고쳐야 하고, v1 은 폴링으로
// 충분하다(실행은 202 로 이미 요청 밖에서 돈다).
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { getRun, listTools, type RunDetail, type ToolInfo } from '../api/procedures.api';

// 게이트웨이 도구 지문은 60초 주기로 바뀔 수 있다 — 카탈로그를 그보다 오래 들고 있지 않는다.
const CATALOG_TTL_MS = 60_000;
const POLL_MS = 1500;

type Ctx = {
  tools: ToolInfo[];
  toolsError: string | null;
  toolsLoading: boolean;
  reloadTools: () => void;
  /** 이 실행이 끝날 때까지(또는 게이트에 멈출 때까지) 폴링한다. */
  watch: (runId: string | null) => void;
  watched: RunDetail | null;
  refreshWatched: () => Promise<void>;
};

const ProceduresCtx = createContext<Ctx | null>(null);

const RESTING = new Set(['done', 'failed', 'cancelled', 'gated']);

export function ProceduresProvider({ children }: { children: ReactNode }) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [toolsLoading, setToolsLoading] = useState(false);
  const fetchedAt = useRef(0);

  const [runId, setRunId] = useState<string | null>(null);
  const [watched, setWatched] = useState<RunDetail | null>(null);
  // ⚠ **지금 보고 있는 실행**을 동기로 들고 있는다. `refreshWatched` 가 렌더 시점의
  // runId 를 가두면, 다시 돌리기처럼 `watch(새 id)` 직후에 부르는 자리에서 **옛 실행**을
  // 받아 와 덮어쓴다. 새 실행이 곧장 게이트나 계획 완료로 앉으면 폴링이 한 번 돌고
  // 멈추므로 그 덮어쓰기가 **영구**가 된다 — 주소는 새 실행인데 화면은 옛 실행이고,
  // 거기서 '확인하고 계속' 을 누르면 옛 실행의 id·지문으로 승인이 나간다.
  const runIdRef = useRef<string | null>(null);

  const reloadTools = useCallback(() => {
    if (Date.now() - fetchedAt.current < CATALOG_TTL_MS && tools.length) return;
    setToolsLoading(true);
    listTools()
      .then((r) => {
        setTools(r.tools);
        setToolsError(null);
        fetchedAt.current = Date.now();
      })
      .catch((e: Error) => setToolsError(e.message))
      .finally(() => setToolsLoading(false));
  }, [tools.length]);

  const refreshWatched = useCallback(async () => {
    const id = runIdRef.current;
    if (!id) return;
    try {
      const r = await getRun(id);
      if (runIdRef.current === id) setWatched(r);   // 그새 옮겨 갔으면 버린다
    } catch {
      /* 폴링 실패는 조용히 넘긴다 — 다음 주기가 다시 본다 */
    }
  }, []);

  const watch = useCallback((id: string | null) => {
    runIdRef.current = id;   // 동기로 — 효과로 미루면 그 사이 호출이 옛 것을 본다
    setRunId(id);
    setWatched(null);
  }, []);

  useEffect(() => {
    if (!runId) return;
    let alive = true;
    let timer: number | undefined;

    const tick = async () => {
      if (!alive) return;
      try {
        const r = await getRun(runId);
        if (!alive) return;
        setWatched(r);
        // 쉬는 상태면 멈춘다. 게이트도 쉬는 상태다 — 사람이 눌러야 움직인다.
        if (RESTING.has(r.state)) return;
      } catch {
        /* 무시하고 다시 시도 */
      }
      timer = window.setTimeout(tick, POLL_MS);
    };
    void tick();
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [runId]);

  const value = useMemo<Ctx>(
    () => ({ tools, toolsError, toolsLoading, reloadTools, watch, watched, refreshWatched }),
    [tools, toolsError, toolsLoading, reloadTools, watch, watched, refreshWatched],
  );
  return <ProceduresCtx.Provider value={value}>{children}</ProceduresCtx.Provider>;
}

export function useProcedures(): Ctx {
  const v = useContext(ProceduresCtx);
  if (!v) throw new Error('useProcedures 는 ProceduresProvider 안에서만 쓴다');
  return v;
}
