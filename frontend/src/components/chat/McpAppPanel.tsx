// MCP Apps 패널 호스트 부품 — 포털이 그린 머리 · 격리 iframe(srcdoc · sandbox=allow-scripts · CSP 메타) · postMessage 브리지 · 첫 쓰기 확인 · 닫기(docs/request-1027 HP-42)
//
// 설계 docs/request-1027/design-ha09-ha20.md B5.5 · B7. 보안 판정(CSP · 문서 · 메시지 꼴 · open-link · 높이)은 lib/mcpApps 에 있다.
//  · 받는 메시지 — event.source 가 이 패널의 iframe 창일 때만(같은 출처가 없어 origin 은 'null' 이라 origin 으로는 가를 수 없다) · JSON-RPC 2.0 꼴 ·
//    크기 · 초당 수 상한. 모르는 요청은 오류로 답한다(조용히 삼키지 않는다).
//  · 패널이 부르는 tools/call · resources/read 는 포털 창구(/agent/panel/*)로만 간다 — 패널 PAT(그 앱 · 그 주소 · 15분)로 게이트웨이에 닿는다.
//  · 모델 맥락을 바꾸는 메서드(ui/update-model-context · ui/message)는 1단계에서 받지 않는다(B-5 (가)).
//  · 패널 문서가 떠나면(beforeunload · pagehide — 포털이 패널 문서 맨 앞에 넣은 시작 스크립트가 이 열기의 열쇠로 알린다) 그 자리에서 브리지를 닫고
//    (동기 dead 표지 — onMessage · post 맨 앞) 포털 세션을 닫는다. 바깥 출처로의 자기 이동은 포털 문서의 CSP(frame-src, index.html)가 막고, 같은 출처로 가더라도 새 문서는 브리지를
//    넘겨받지 못한다(B7 자료 빼내기 · 대리 호출 — 반대 검토 10-31). 두 번째 load 도 그대로 접는다(알림이 오지 않는 꼴의 덧막이).
//  · tool-input · tool-result 는 열 때 한 번만 보낸다. 입력을 모르면(서버 사본) tool-input 을 지어 보내지 않는다.
//  · 첫 쓰기 확인은 패널을 밀지 않는 덮개다 — 묻는 동안 iframe 은 누름을 받지 않고, 뜬 뒤 ASK_ARM_MS 동안 '허용' 은 눌리지 않는다(B-2 클릭재킹).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { callPanel, closePanel, confirmPanel, openPanel, PanelError, readPanel, type PanelOpened } from '../../api/panel.api';
import {
  ASK_ARM_MS,
  ASSUME_PROTOCOL_VERSIONS,
  HEIGHT_DEFAULT,
  HEIGHT_MAX,
  HOST_PROTOCOL_VERSION,
  SANDBOX,
  UNSUPPORTED,
  buildPanelDoc,
  claimSlot,
  clampHeight,
  isLeave,
  linkAllowed,
  liveResult,
  newLeaveKey,
  panelKey,
  rateGate,
  releaseSlot,
  rpcOf,
  type RpcMsg,
} from '../../lib/mcpApps';
import type { PanelPointer } from '../../types/chat';

type Phase = 'idle' | 'opening' | 'open' | 'closed' | 'folded' | 'error';

const TEARDOWN_WAIT_MS = 500;

function theme(): 'light' | 'dark' {
  const t = document.documentElement.dataset.theme;
  if (t === 'light' || t === 'dark') return t;
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function McpAppPanels({ panels }: { panels: PanelPointer[] }) {
  return (
    <div className="mcp-panels">
      {panels.map((p) => (
        <McpAppPanel key={panelKey(p)} pointer={p} />
      ))}
    </div>
  );
}

export function McpAppPanel({ pointer }: { pointer: PanelPointer }) {
  const key = panelKey(pointer);
  // 이 탭이 그 사건을 받았으면(결과가 이 탭에 있다) 바로 연다. 기록에서 온 포인터는 '다시 열기' 카드로 둔다(B-4 (가)).
  const [phase, setPhase] = useState<Phase>(() => (liveResult(key) !== undefined ? 'opening' : 'idle'));
  const [opened, setOpened] = useState<PanelOpened | null>(null);
  const [height, setHeight] = useState(HEIGHT_DEFAULT);
  const [note, setNote] = useState('');
  const [ask, setAsk] = useState<{ tool: string; resolve: (ok: boolean) => void } | null>(null);
  const [armed, setArmed] = useState(false); // 확인이 뜬 뒤 ASK_ARM_MS 가 지나야 '허용' 을 받는다
  const [leaveKey, setLeaveKey] = useState(''); // 이 열기의 떠남 알림 열쇠 — 패널 문서의 시작 스크립트에 싣는다
  const frame = useRef<HTMLIFrameElement | null>(null);
  const openedRef = useRef<PanelOpened | null>(null);
  const loads = useRef(0);
  const pending = useRef(new Map<string | number, (m: RpcMsg) => void>());
  const seq = useRef(0);
  const autoDone = useRef(liveResult(key) === undefined);   // 기록에서 온 포인터는 저절로 열지 않는다
  const gen = useRef(0);    // 여는 차례 — 여는 중에 접히거나 닫히면 늦게 온 열기 답을 버리고 그 세션을 닫는다
  const asking = useRef<Promise<boolean> | null>(null);   // 묻는 확인 하나 — 한꺼번에 온 쓰기 여럿이 같은 답을 기다린다
  const dead = useRef(false); // 패널 문서가 떠났다 — 그 iframe 창과는 더 주고받지 않는다(다시 열면 새 iframe 이라 푼다)
  const fed = useRef(false);  // tool-input · tool-result 를 보냈다 — 열 때 한 번만

  const post = useCallback((msg: RpcMsg) => {
    if (dead.current) return; // 떠난 문서 자리에 온 새 문서(바깥 · 같은 출처)에는 답 · 알림을 보내지 않는다
    frame.current?.contentWindow?.postMessage(msg, '*');
  }, []);

  /** 패널을 내린다 — teardown 을 보내 답을 잠깐 기다리고(wait), iframe 을 치우고, 포털 패널 세션을 닫는다. */
  const shut = useCallback(
    async (next: Phase, why: string, wait: boolean) => {
      gen.current += 1;
      const o = openedRef.current;
      openedRef.current = null;
      releaseSlot(key);
      setAsk((a) => {
        a?.resolve(false); // 묻던 확인은 거절로 끝낸다 — 닫힌 패널의 호출이 기다린 채 남지 않게
        return null;
      });
      if (o && frame.current?.contentWindow) {
        seq.current += 1;
        const id = `teardown-${seq.current}`;
        const done = new Promise<void>((res) => {
          pending.current.set(id, () => res());
          window.setTimeout(res, wait ? TEARDOWN_WAIT_MS : 0);
        });
        post({ jsonrpc: '2.0', id, method: 'ui/resource-teardown', params: {} });
        if (wait) await done;
        pending.current.delete(id);
      }
      dead.current = true; // 이제 iframe 을 치운다 — 그 문서가 내려가며 보내는 떠남 알림 · 메시지는 받지 않는다(닫기를 '이동' 으로 읽지 않게)
      if (o) void closePanel(o.panel_id);
      setOpened(null);
      setNote(why);
      setPhase(next);
    },
    [key, post],
  );

  /** 패널 문서가 떠났다(떠남 알림 · 두 번째 load) — 동기로 dead 를 세워 그 뒤 메시지를 받지도 보내지도 않고, 기다리지 않고 포털 세션을 닫는다. */
  const left = useCallback(() => {
    dead.current = true;
    void shut('folded', '패널이 다른 문서로 이동하려 해 닫았다', false);
  }, [shut]);

  const open = useCallback(async () => {
    const my = ++gen.current;
    setPhase('opening');
    setNote('');
    loads.current = 0;
    claimSlot(key, () => void shut('folded', '패널을 셋 이상 열어 오래된 이 패널을 접었다', false));
    try {
      const o = await openPanel(pointer.uri, pointer.tool, pointer.call);
      if (gen.current !== my) {
        void closePanel(o.panel_id); // 여는 중에 접혔다 · 닫혔다 · 내려갔다 — 막 연 포털 세션을 닫는다(그리지 않는다)
        return;
      }
      dead.current = false; // 새 iframe — 옛 iframe 창의 메시지는 event.source 가 달라 받지 않는다
      fed.current = false;
      openedRef.current = o;
      setLeaveKey(newLeaveKey());
      setOpened(o);
      setHeight(HEIGHT_DEFAULT);
      setPhase('open');
    } catch (e) {
      if (gen.current !== my) return;
      releaseSlot(key);
      setNote(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  }, [key, pointer.call, pointer.tool, pointer.uri, shut]);

  // 이 탭이 받은 사건이면 곧바로 연다
  useEffect(() => {
    if (phase === 'opening' && !openedRef.current && !autoDone.current) {
      autoDone.current = true;
      void open();
    }
  }, [phase, open]);

  // 메시지가 지워지거나(언마운트) 탭을 떠나면 teardown 을 보내고 닫는다(기다리지 않는다). 여는 중에 내려가면(대화 옮김 · 서버 사본 교체로 줄이
  // 다시 선다) 차례(gen)를 올려 늦게 온 열기 답의 포털 세션을 open 이 닫게 하고 자리도 돌려준다(반대 검토 10-31 — 종전엔 세션이 청소까지 남았다).
  useEffect(() => {
    const away = () => void shut('closed', '', false);
    window.addEventListener('pagehide', away);
    return () => {
      window.removeEventListener('pagehide', away);
      if (openedRef.current) {
        away();
        return;
      }
      gen.current += 1;
      releaseSlot(key);
      // StrictMode(개발)는 붙자마자 정리를 한 번 흉내 내고 다시 붙인다 — 저절로 열기를 되돌려 다시 붙을 때 다시 연다(실제 언마운트는 다시 붙지 않는다)
      autoDone.current = liveResult(key) === undefined;
    };
  }, [shut, key]);

  // 확인이 뜨면 잠깐 '허용' 을 받지 않는다 — 패널이 고른 순간에 띄운 확인에 사람의 다음 누름이 떨어지지 않게(B-2 클릭재킹)
  useEffect(() => {
    setArmed(false);
    if (!ask) return;
    const t = window.setTimeout(() => setArmed(true), ASK_ARM_MS);
    return () => window.clearTimeout(t);
  }, [ask]);

  // 브리지
  useEffect(() => {
    if (phase !== 'open' || !opened) return;
    const gate = rateGate();
    const reply = (m: RpcMsg, result: unknown) => post({ jsonrpc: '2.0', id: m.id, result });
    const fail = (m: RpcMsg, code: number, message: string) => {
      if (m.id !== undefined) post({ jsonrpc: '2.0', id: m.id, error: { code, message } });
    };
    const confirmWrite = (tool: string) =>
      (asking.current ??= new Promise<boolean>((resolve) =>
        setAsk({
          tool,
          resolve: (ok) => {
            asking.current = null;
            resolve(ok);
          },
        }),
      ));

    // 열 때 한 번만 — initialized 를 되풀이해 입력 · 결과(_meta 포함)를 다시 받는 길로 쓰이지 않게. 입력을 모르면(서버 사본 · 큰 입력은 브라우저
    // 사본에 없다) 빈 인자를 지어 보내지 않는다 — 패널이 '인자 없이 불렸다' 로 읽는다(반대 검토 10-31).
    const sendInput = () => {
      if (fed.current) return;
      fed.current = true;
      if (pointer.input) post({ jsonrpc: '2.0', method: 'ui/notifications/tool-input', params: { arguments: pointer.input } });
      const res = liveResult(key);
      if (res) post({ jsonrpc: '2.0', method: 'ui/notifications/tool-result', params: { ...res, isError: false } });
      else if (res === undefined)
        setNote(pointer.input ? '결과는 그 탭에만 있었다 — 입력만 다시 보냈다' : '입력 · 결과가 이 기기에 없다 — 패널을 입력 없이 열었다');
    };

    const callTool = async (m: RpcMsg) => {
      const p = m.params ?? {};
      const name = typeof p.name === 'string' ? p.name : '';
      const args = p.arguments && typeof p.arguments === 'object' && !Array.isArray(p.arguments) ? (p.arguments as Record<string, unknown>) : {};
      if (!name) return fail(m, -32602, 'tools/call 에 name 이 없다');
      // 첫 쓰기면 포털이 409 confirm_required 로 멈춘다 — 포털이 그린 확인을 받고 한 번만 다시 부른다(B-2 (가)). 같이 기다리던 다른 쓰기가 먼저
      // 확인했으면 확인 창구가 no_pending_confirm 이다 — 그대로 다시 부른다(세션이 이미 허용됐다).
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          const r = await callPanel(opened.panel_id, name, args);
          if (r.error) return fail(m, r.error.code ?? -32000, r.error.message ?? '오류');
          return reply(m, r.result ?? {});
        } catch (e) {
          if (!(e instanceof PanelError && e.code === 'confirm_required' && e.token && attempt === 0))
            return fail(m, -32000, e instanceof Error ? e.message : String(e));
          if (!(await confirmWrite(name))) return fail(m, -32000, '사람이 이 패널의 쓰기를 허용하지 않았다');
          try {
            await confirmPanel(opened.panel_id, e.token);
          } catch (e2) {
            if (!(e2 instanceof PanelError && e2.code === 'no_pending_confirm'))
              return fail(m, -32000, e2 instanceof Error ? e2.message : String(e2));
          }
        }
      }
    };

    const readRes = async (m: RpcMsg) => {
      const uri = typeof m.params?.uri === 'string' ? m.params.uri : '';
      if (!uri.startsWith('ui://')) return fail(m, -32602, '패널은 ui:// 리소스만 읽는다');
      try {
        const r = await readPanel(opened.panel_id, uri);
        if (r.error) fail(m, r.error.code ?? -32000, r.error.message ?? '오류');
        else reply(m, r.result ?? {});
      } catch (e) {
        fail(m, -32000, e instanceof Error ? e.message : String(e));
      }
    };

    const handle = (m: RpcMsg) => {
      switch (m.method) {
        case 'ui/initialize': {
          const want = typeof m.params?.protocolVersion === 'string' ? m.params.protocolVersion : '';
          reply(m, {
            protocolVersion: ASSUME_PROTOCOL_VERSIONS.includes(want) ? want : HOST_PROTOCOL_VERSION,
            hostInfo: { name: 'hwax-portal', version: '1' },
            hostCapabilities: { serverTools: {}, serverResources: {}, openLinks: {}, logging: {},
                                sandbox: { permissions: {}, csp: opened.csp } },
            hostContext: { theme: theme(), locale: 'ko-KR', timeZone: 'Asia/Seoul', displayMode: 'inline',
                           availableDisplayModes: ['inline'], platform: 'web', containerDimensions: { maxHeight: HEIGHT_MAX },
                           toolInfo: { tool: { name: pointer.tool } } },
          });
          return;
        }
        case 'ui/notifications/initialized':
          sendInput();
          return;
        case 'ui/notifications/size-changed':
          setHeight(clampHeight(m.params?.height));
          return;
        case 'ping':
          reply(m, {});
          return;
        case 'tools/call':
          void callTool(m);
          return;
        case 'resources/read':
          void readRes(m);
          return;
        case 'ui/open-link': {
          const url = m.params?.url;
          if (!linkAllowed(url, opened.open_origins)) return fail(m, -32000, '허용하지 않은 주소라 열지 않는다');
          window.open(String(url), '_blank', 'noopener,noreferrer');
          reply(m, {});
          return;
        }
        case 'notifications/message':
          return; // 패널의 로그 — 화면 · 모델에 싣지 않는다
        default:
          if (m.method && UNSUPPORTED.has(m.method)) fail(m, -32601, `${m.method} 은(는) 1단계에서 받지 않는다 — 패널은 모델 맥락을 바꾸지 못한다`);
          else fail(m, -32601, `모르는 메서드: ${m.method ?? '(없음)'}`);
      }
    };

    const onMessage = (ev: MessageEvent) => {
      if (dead.current) return; // 떠난 문서의 자리에 온 새 문서는 같은 창(WindowProxy)이라 event.source 로는 가를 수 없다
      // 떠남 알림은 열쇠로만 가린다 — 떠나는 문서의 event.source 는 그 iframe 창과 같지 않을 수 있다(10-31 실측). 열쇠는 이 패널 문서에만 있다
      if (isLeave(ev.data, leaveKey)) return left();
      const win = frame.current?.contentWindow;
      if (!win || ev.source !== win) return; // 다른 창 · 다른 패널의 메시지는 받지 않는다
      const m = rpcOf(ev.data);
      if (!m) return;
      if (!gate()) return fail(m, -32000, '메시지가 너무 잦다');
      if (m.method === undefined) {
        // 우리 요청(teardown)의 답
        if (m.id !== undefined) pending.current.get(m.id)?.(m);
        return;
      }
      handle(m);
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [phase, opened, pointer.input, pointer.tool, key, post, leaveKey, left]);

  const onLoad = () => {
    loads.current += 1;
    if (loads.current > 1) left(); // 떠남 알림이 오지 않은 꼴의 덧막이(load 를 미루는 문서에는 늦다 — 알림이 먼저다)
  };

  const doc = useMemo(() => (opened ? buildPanelDoc(opened.html, opened.csp, leaveKey) : ''), [opened, leaveKey]);
  const label = opened?.app_label || pointer.title || pointer.app || '앱';
  return (
    <section className={`mcp-panel is-${phase}`} data-panel={key}>
      <header className="mcp-panel-head">
        <span className="mcp-panel-app">{label}</span>
        <code className="mcp-panel-uri" title={pointer.uri}>{pointer.uri}</code>
        <span className="mcp-panel-mark">앱이 그린 화면 — 포털이 아니다 · 포털은 여기서 비밀번호를 묻지 않는다</span>
        {phase === 'open' && (
          <button type="button" className="btn-secondary mcp-panel-close" onClick={() => void shut('closed', '', true)}>
            닫기
          </button>
        )}
        {(phase === 'idle' || phase === 'closed' || phase === 'folded' || phase === 'error') && (
          <button type="button" className="btn-secondary mcp-panel-reopen" onClick={() => void open()}>
            {phase === 'idle' ? '패널 — 다시 열기' : '다시 열기'}
          </button>
        )}
      </header>
      {note && <div className="mcp-panel-note">{note}</div>}
      {phase === 'opening' && <div className="mcp-panel-note">패널을 여는 중…</div>}
      {phase === 'open' && opened && (
        <div className="mcp-panel-body">
          <iframe
            ref={frame}
            className={`mcp-panel-frame${opened.prefers_border ? ' has-border' : ''}`}
            title={`${label} 패널`}
            sandbox={SANDBOX}
            referrerPolicy="no-referrer"
            allow=""
            srcDoc={doc}
            style={{ height, ...(ask ? { pointerEvents: 'none' as const } : {}) }}
            onLoad={onLoad}
          />
          {/* 첫 쓰기 확인 — iframe 위의 덮개라 패널을 밀지 않는다(흐름에 끼우면 패널이 밀려 사람의 다음 누름이 '허용' 에 떨어진다 — B-2 클릭재킹) */}
          {ask && (
            <div className="mcp-panel-ask" role="alertdialog" aria-modal="true" aria-label="패널 쓰기 확인">
              <div className="mcp-panel-ask-box">
                <span>
                  ⚠ {label} 패널이 쓰기 · 작업 제출 도구 <code>{ask.tool}</code> 을(를) 부르려 한다. 이 패널 세션에서 허용할까?
                </span>
                <div className="mcp-panel-ask-actions">
                  <button
                    type="button"
                    className="btn-primary mcp-panel-allow"
                    disabled={!armed}
                    onClick={() => { ask.resolve(true); setAsk(null); }}
                  >
                    허용
                  </button>
                  <button type="button" className="btn-secondary mcp-panel-deny" onClick={() => { ask.resolve(false); setAsk(null); }}>
                    거절
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
