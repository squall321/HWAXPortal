// PPT·Word·PDF 원본을 붙였을 때 — DRM 때문에 이 PC 에서 추출해야 한다고 알리고, PC 도우미 단추 · 추출기를 준다
import { useEffect, useRef, useState } from 'react';
import {
  createPcTicket, fetchPcDoc, fetchPcSlide, getPcTicket,
  type PcTicket, type PcTicketState, type StagedFile,
} from '../../api/upload.api';
import { buildDocHelperBat } from '../../lib/setupBat';
import { kindLabel } from './docAttach';

interface Props {
  filename: string;
  /** 파일 첫 바이트로 본 판정. true=암호화(또는 구형 OLE) · false=평문 · null=모름. */
  encrypted: boolean | null;
  onClose: () => void;
  /** PC 도우미가 올린 글 · 그림을 입력창에 붙인다(손으로 .hwax.md 를 붙이던 길과 같다). 실패하면 까닭을 돌려준다. */
  onAttach?: (doc: File, slides: File[]) => Promise<string | void>;
  /** 받은 글을 다음 단계로 — 그 글의 스테이징 상자로 '어디로 보낼까요' 를 연다(AI 데이터 허브, docs/chat-ppt PP-D11). */
  onStaged?: (staged: StagedFile) => void;
  /** 감사용 서버 대화 id(받은 글을 서버가 대화에 쓰지는 않는다). */
  conversationId?: string;
}

// 도우미가 이 안에 표를 읽지 않으면(열림이 안 오면) 설치가 안 된 것으로 보고 설치 안내를 띄운다 — 표는 그대로 기다린다(10분).
const HELPER_WAIT_MS = 15_000;
const POLL_MS = 1_500;
// 상태 조회가 잇달아 이만큼 실패해야 멈춘다 — 한 번의 끊김으로 '실패' 를 굳히면 도우미가 올린 글을 화면이 놓친다.
const POLL_ERR_MAX = 3;
const OPEN_STATES = new Set(['waiting', 'opened', 'receiving']);

function launch(url: string) {
  // 사람이 누른 단추의 이어진 동작이라 브라우저가 '열까요' 를 묻는다. 안 열렸으면 아래 '다시 열기' 링크(새 클릭)를 쓴다.
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noreferrer';
  a.click();
}

function downloadHelperBat() {
  const blob = new Blob([buildDocHelperBat(window.location.origin)], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'hwax-doc-helper-setup.bat';
  a.click();
  URL.revokeObjectURL(url);
}

/** DRM 문서는 그 PC·그 사용자 세션에서만 복호화된다. 서버가 원본을 받아 파싱하면 암호화된
 *  바이트만 본다 — ReportArchive 의 /imports/pptx 도, AI 데이터 허브의 convert_file 도 거기서
 *  막힌다. 그래서 추출을 PC 로 옮긴다. 올라가는 것은 원본이 아니라 추출된 글이다. */
export function DocExtractHint({ filename, encrypted, onClose, onAttach, onStaged, conversationId }: Props) {
  const ext = filename.slice(filename.lastIndexOf('.') + 1).toLowerCase();
  const kind = ext === 'pptx' || ext === 'ppt' ? 'ppt' : ext === 'pdf' ? 'pdf' : 'word';
  const label = kindLabel({ kind });
  const app = kind === 'ppt' ? 'PowerPoint' : 'Word';

  const [slides, setSlides] = useState(false);
  const [pc, setPc] = useState<{ t: PcTicket; at: number; st?: PcTicketState; errs?: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState<{ chars: number; slides: number; staged?: StagedFile } | null>(null);
  const [late, setLate] = useState(false);
  // 기다리는 동안 부모가 다시 그려져도 가장 새 콜백을 부른다(오래된 콜백은 붙인 문서 목록이 낡았다).
  const cb = useRef({ onAttach, onStaged });
  cb.current = { onAttach, onStaged };

  const start = async () => {
    setBusy(true); setErr(''); setDone(null); setLate(false);
    try {
      const t = await createPcTicket({ filename, conversation_id: conversationId ?? '', slides: kind === 'ppt' && slides });
      setPc({ t, at: Date.now() });
      launch(t.helper_url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'PC 도우미를 부르지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  // 표의 상태를 본다 — 받으면 글 · 그림을 가져와 붙이고 멈춘다. 닫힌 표(실패 · 취소 · 만료)도 멈춘다.
  useEffect(() => {
    if (!pc || (pc.st && !OPEN_STATES.has(pc.st.state))) return;
    let stop = false;
    const timer = window.setTimeout(async () => {
      try {
        const st = await getPcTicket(pc.t.ticket);
        if (stop) return;
        if (st.state === 'waiting' && Date.now() - pc.at > HELPER_WAIT_MS) setLate(true);
        if (st.state !== 'waiting') setLate(false);
        if (st.state === 'received' && st.received) {
          const doc = await fetchPcDoc(pc.t.ticket, st.received.doc_name);
          const imgs: File[] = [];
          for (let n = 1; n <= st.received.slides; n += 1) imgs.push(await fetchPcSlide(pc.t.ticket, n));
          const why = await cb.current.onAttach?.(doc, imgs);
          if (stop) return;
          if (why) setErr(why);
          setDone({ chars: st.received.chars, slides: st.received.slides, staged: st.staged });
        }
        setPc((p) => (p && p.t.ticket === pc.t.ticket ? { ...p, st, errs: 0 } : p));
      } catch (e) {
        if (stop) return;
        const errs = (pc.errs ?? 0) + 1;
        if (errs < POLL_ERR_MAX) {
          setPc((p) => (p && p.t.ticket === pc.t.ticket ? { ...p, errs } : p));   // 다시 묻는다
          return;
        }
        setErr(e instanceof Error ? e.message : '상태를 못 읽었습니다.');
        setPc((p) => (p && p.t.ticket === pc.t.ticket
          ? { ...p, errs, st: { state: 'failed', filename, expires_in_s: 0, error: '상태를 못 읽었습니다' } } : p));
      }
    }, POLL_MS);
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [pc, filename]);

  const state = pc?.st?.state ?? (pc ? 'waiting' : null);
  const waiting = state != null && OPEN_STATES.has(state);
  const closedWhy: Record<string, string> = {
    failed: '받지 못했습니다', cancelled: 'PC 에서 취소했습니다', expired: '표가 만료됐습니다(10분)',
    closed: '새로 누른 단추가 이 표를 닫았습니다',
  };

  return (
    <div className="doc-hint" role="region" aria-label="문서 추출 안내">
      <div className="doc-hint-head">
        <strong>{filename}</strong>
        <span className="doc-hint-sub">{label} 는 이 PC 에서 읽습니다.</span>
        <button type="button" className="doc-hint-x" onClick={onClose} aria-label="닫기">×</button>
      </div>
      {/* 이름이 아니라 **바이트**로 갈린다. DRM 이 브라우저 읽기에도 투명하면 여기서 이미
          평문이라 서버가 그대로 파싱할 수 있고, COM 추출이 필요 없다. 짐작하면 멀쩡한
          파일에도 불필요한 수고를 시킨다. */}
      {encrypted === false ? (
        <p className="doc-hint-alt">
          <b>이 파일은 이 PC 에서 평문으로 읽힙니다</b> — 첫 바이트가 정상 문서 형식입니다.
          그러면 추출기가 필요 없습니다.
          <a href="/report-archive/" target="_blank" rel="noreferrer"> Report Archive</a> 의
          <b> PPT에서 불러오기</b> 로 올리면 서버가 직접 읽어 <b>그림·표까지</b> 보고서로
          만들어 줍니다(여기 추출은 글만 갑니다). 그래도 글만 빠르게 보고 싶으면 아래로 진행하세요.
        </p>
      ) : (
        <p className="doc-hint-alt">
          {encrypted === true
            ? '이 파일은 암호화돼 있거나 구형 형식입니다 — 서버가 열지 못합니다. 아래 방법이 맞습니다.'
            : '형식을 단정하지 못했습니다. 서버가 못 읽으면 아래 방법으로 진행하세요.'}
          {' '}DRM 이 안 걸린 자료라면 <a href="/report-archive/" target="_blank" rel="noreferrer">Report Archive</a> 의
          <b> PPT에서 불러오기</b> 가 그림까지 넣어 주므로 그쪽이 낫습니다.
        </p>
      )}
      <p className="doc-hint-why">
        사내 DRM 문서는 <b>그 PC, 그 계정</b>에서만 복호화됩니다. 파일을 그대로 올리면 서버는
        암호화된 바이트만 보게 됩니다. 그래서 PC 에 설치된 Office 로 한 번 읽어 <b>글만</b>
        올립니다 — 원본 파일은 PC 를 떠나지 않습니다.
      </p>

      {/* PC 도우미 — 단추 하나로 이 PC 의 Office 가 열어 뽑고 포털로 올린다(docs/chat-ppt B). 처음 한 번은 설치 배치가 든다. */}
      <div className="doc-hint-pc">
        <div className="doc-hint-pc-row">
          <button type="button" className="doc-hint-go" disabled={busy || waiting} onClick={() => void start()}>
            {busy ? '부르는 중…' : waiting ? 'PC 도우미를 기다리는 중…' : `PC 의 ${app} 로 열어 가져오기`}
          </button>
          {kind === 'ppt' && (
            <label className="doc-hint-opt">
              <input type="checkbox" checked={slides} disabled={waiting} onChange={(e) => setSlides(e.target.checked)} />
              {' '}슬라이드 그림도(최대 12장)
            </label>
          )}
        </div>
        {state === 'waiting' && !late && (
          <p className="doc-hint-state">PC 화면에 ‘HWAX 문서 도우미’ 가 뜹니다 — 브라우저가 열지 물으면 [열기] 를 누르세요.</p>
        )}
        {state === 'opened' && (
          <p className="doc-hint-state">PC 도우미가 열렸습니다 — PC 화면에서 <b>받는 계정이 본인인지</b> 확인하고 파일을 고르세요.</p>
        )}
        {state === 'receiving' && <p className="doc-hint-state">받는 중…</p>}
        {late && state === 'waiting' && pc && (
          <div className="doc-hint-state" role="status">
            PC 도우미가 응답하지 않습니다. <b>처음이면</b> 설치 배치를 받아 한 번 실행한 뒤 다시 누르세요(관리자 권한 불필요).
            <span className="doc-hint-dl">
              <button type="button" className="doc-hint-go" onClick={downloadHelperBat}>도우미 설치 배치 받기</button>
              <a href={pc.t.helper_url} rel="noreferrer">설치돼 있으면 — 다시 열기</a>
            </span>
          </div>
        )}
        {state && closedWhy[state] && (
          <p className="doc-hint-err" role="alert">
            ⚠ {closedWhy[state]}{pc?.st?.error ? ` — ${pc.st.error}` : ''}. 단추를 다시 누르면 새로 시작합니다.
          </p>
        )}
        {done && (
          <div className="doc-hint-state" role="status">
            입력창에 붙였습니다 — 글 {done.chars.toLocaleString()}자{done.slides ? ` · 슬라이드 그림 ${done.slides}장` : ''}.
            이제 물어보세요.
            {done.staged && (done.staged.destinations ?? []).length > 0 && (
              <span className="doc-hint-dl">
                <button type="button" className="doc-hint-go" onClick={() => done.staged && cb.current.onStaged?.(done.staged)}>
                  이 글을 AI 데이터 허브로도 보내기
                </button>
              </span>
            )}
          </div>
        )}
        {err && <p className="doc-hint-err" role="alert">⚠ {err}</p>}
        {!pc && (
          <p className="doc-hint-note">
            처음 한 번은 <button type="button" className="doc-hint-link" onClick={downloadHelperBat}>도우미 설치 배치</button>를
            받아 실행합니다 — 추출기를 내 사용자 폴더에 두고 이 단추와 잇습니다. PC 도우미는 올리기 전에 받는 계정을 보여 주고 묻습니다.
          </p>
        )}
      </div>

      <details className="doc-hint-more">
        <summary>손으로 하기 — 추출기를 직접 돌려 붙이기</summary>
        <ol className="doc-hint-steps">
          <li>
            아래 <b>두 파일을 같은 폴더</b>에 내려받습니다.
            <span className="doc-hint-dl">
              <a href="/doc-extract/hwax-doc-extract.bat" download>hwax-doc-extract.bat</a>
              <a href="/doc-extract/hwax-doc-extract.ps1" download>hwax-doc-extract.ps1</a>
            </span>
          </li>
          <li>
            <b>처음 한 번만</b> — <code>hwax-doc-extract.bat</code> 를 그냥 두 번 눌러 자가 시험을
            돌립니다(이 PC 에서 Office 를 부를 수 있는지 확인).
          </li>
          <li>
            <code>{filename}</code> 를 <code>hwax-doc-extract.bat</code> <b>위로 끌어다 놓습니다.</b>
            옆에 <code>{filename.replace(/\.[^.]+$/, '')}.hwax.md</code> 가 생깁니다.
          </li>
          <li>그 <code>.hwax.md</code> 를 여기 붙이면 내용을 읽고 심의합니다.</li>
        </ol>
      </details>
      <p className="doc-hint-note">
        Word·PowerPoint 가 이미 열려 있어도 괜찮습니다 — 작업 중인 창은 건드리지 않습니다.
        스캔한 PDF 는 글자가 없어 빈 결과가 나옵니다.
      </p>
      <details className="doc-hint-more">
        <summary>개인 클로드(Claude Code)를 쓴다면 — 올리는 단계 없이</summary>
        <p>
          같은 폴더에 <a href="/doc-extract/hwax-doc-mcp.mjs" download>hwax-doc-mcp.mjs</a> 를 함께
          받아 아래 한 줄로 등록하면, 클로드가 이 PC 의 문서를 직접 읽습니다.
          <b>추출한 글조차 서버로 가지 않습니다.</b>
        </p>
        <code className="doc-hint-cmd">claude mcp add hwax-doc -- node "C:\받은폴더\hwax-doc-mcp.mjs"</code>
        <p>
          기본으로 내 문서·바탕화면·다운로드만 읽습니다. 다른 폴더를 열려면
          <code>HWAX_DOC_ROOTS</code> 환경변수에 <code>;</code> 로 구분해 적으세요.
        </p>
      </details>
    </div>
  );
}
