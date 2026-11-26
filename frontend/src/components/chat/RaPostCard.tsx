// 심의 결과 카드의 「시스템 공간에 올리기」 — 미리보기(게시판 · 볼 사람 수)를 보여 주고 사람이 확인한 뒤에만 게시한다(docs/ra-delib-standard RS-3)
import { useEffect, useState } from 'react';
import { knownPostBoard, postReport, previewPost, type PostTarget } from '../../api/raPost.api';

type Phase =
  | { k: 'idle' }
  | { k: 'busy'; what: string }
  | { k: 'confirm'; t: PostTarget }
  | { k: 'done'; name: string; already: boolean }
  | { k: 'error'; msg: string };

/** 이 박스가 심의 게시판을 정했을 때만 그린다. 게시판은 서버(박스 파일)가 정한다 — 화면은 고르지 않는다. 누르기 전에는 포털에 묻지 않는다. */
export function RaPostCard({ reportId }: { reportId: number }) {
  const [board, setBoard] = useState<string | null>(null);
  const [ph, setPh] = useState<Phase>({ k: 'idle' });
  useEffect(() => {
    let live = true;
    void knownPostBoard().then((b) => live && setBoard(b));     // 그리면서 포털에 묻지 않는다 — 앱 머리가 미리 물은 답만(WD-D78)
    return () => {
      live = false;
    };
  }, []);
  if (!board) return null;

  const ask = async () => {
    setPh({ k: 'busy', what: '어디에 올라가는지 확인하는 중…' });
    try {
      const p = await previewPost(reportId);
      const t = p.targets.find((x) => x.slug === p.board);
      if (!t) setPh({ k: 'error', msg: '게시판을 찾지 못했습니다 — 운영 담당에게 알려 주세요.' });
      else if (t.already_mounted) setPh({ k: 'done', name: t.name, already: true });
      else if (t.blocked || !p.ok) setPh({ k: 'error', msg: `이 게시판에는 올릴 수 없습니다 — ${t.blocked ?? '권한을 확인하세요'}` });
      else setPh({ k: 'confirm', t });
    } catch (e) {
      setPh({ k: 'error', msg: e instanceof Error ? e.message : '미리보기를 받지 못했습니다' });
    }
  };
  const go = async () => {
    setPh({ k: 'busy', what: '게시하는 중…' });
    try {
      const r = await postReport(reportId);
      setPh({ k: 'done', name: r.name, already: r.already });
    } catch (e) {
      setPh({ k: 'error', msg: e instanceof Error ? e.message : '게시하지 못했습니다' });
    }
  };

  return (
    <div className="dv-card post" aria-live="polite">
      <span className="dv-card-k">Report Archive 시스템 공간</span>
      {ph.k === 'idle' && (
        <>
          <span className="dv-card-t">심의 보고서 올리기</span>
          <span className="dv-card-s">올리기 전에 어느 게시판에 몇 명이 보는지 먼저 보여 줍니다.</span>
          <button type="button" className="btn-secondary dv-post-btn" onClick={() => void ask()}>
            시스템 공간에 올리기
          </button>
        </>
      )}
      {ph.k === 'busy' && <span className="dv-card-s">{ph.what}</span>}
      {ph.k === 'confirm' && (
        <>
          <span className="dv-card-t">
            「{ph.t.name}」 게시판{ph.t.audience != null ? ` — ${ph.t.audience}명이 보게 됩니다` : ''}
          </span>
          <span className="dv-card-s">게시한 뒤에는 작성자가 직접 내릴 수 없고 게시판 매니저의 승인이 필요합니다.</span>
          <span className="dv-post-actions">
            <button type="button" className="btn-primary dv-post-btn" onClick={() => void go()}>
              게시
            </button>
            <button type="button" className="btn-secondary dv-post-btn" onClick={() => setPh({ k: 'idle' })}>
              취소
            </button>
          </span>
        </>
      )}
      {ph.k === 'done' && (
        <span className="dv-card-t">
          {ph.already ? `「${ph.name}」 에 이미 게시돼 있습니다` : `「${ph.name}」 에 게시했습니다`}
        </span>
      )}
      {ph.k === 'error' && (
        <>
          <span className="dv-card-s dv-post-err">{ph.msg}</span>
          <button type="button" className="btn-secondary dv-post-btn" onClick={() => setPh({ k: 'idle' })}>
            다시
          </button>
        </>
      )}
    </div>
  );
}
