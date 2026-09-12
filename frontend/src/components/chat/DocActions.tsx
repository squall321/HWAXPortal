// 문서를 붙인 뒤 '이걸로 뭘 할지' 를 고르는 칩 — 고르면 입력창에 지시문을 채운다(전송은 사람이)
import { useCan } from '../../auth/useCan';
import type { AttachedDoc } from './docAttach';

interface Props {
  docs: AttachedDoc[];
  onFill: (text: string) => void;
}

/** 왜 별도 API 가 아니라 지시문인가.
 *
 *  등록·발행은 되돌리기 어렵다. 전용 라우트를 파면 확인 절차를 그 라우트에 다시 만들어야 하는데,
 *  챗 경로에는 이미 그게 있다 — `import_record` 는 dry_run 으로 모자란 항목을 되묻고,
 *  `create_report_draft` 는 템플릿을 먼저 보게 한다. 모델이 그 규약대로 움직이도록 지시문만
 *  채워 주면 코드가 줄고 확인 절차가 한 곳에 남는다.
 *
 *  **보내지는 않는다.** 사람이 읽고 고친 뒤 직접 보낸다 — 이게 '되돌리기 어려운 일 전에
 *  사람이 확인한다' 의 실질이다. */
export function DocActions({ docs, onFill }: Props) {
  const can = useCan();
  const names = docs.map((d) => d.meta?.source || d.name).join(', ');
  const one = docs.length === 1;

  const actions: { key: string; label: string; title: string; text: string }[] = [];

  if (can('feat:deliberation')) {
    actions.push({
      key: 'delib',
      label: '⚖ 심의 걸기',
      title: '전문가 좌석을 세워 이 문서를 두고 논의한다',
      text: `/심의 붙인 ${one ? '문서' : `문서 ${docs.length}건`}(${names})의 내용을 근거로 `
        + '검토해 주세요. 여기에 무엇을 판단해 달라고 할지 한 문장으로 적으세요.',
    });
  }

  actions.push({
    key: 'read',
    label: '📖 요약·쟁점 뽑기',
    title: '등록하지 않고 내용만 읽는다',
    text: `붙인 ${one ? '문서' : '문서들'}을 읽고 ① 핵심 결론 ② 근거가 약한 대목 `
      + '③ 이 자료만으로는 판단할 수 없는 것을 나눠서 정리해 주세요. '
      + '각 항목에 몇 번째 슬라이드·쪽에서 나온 것인지 표기하세요.',
  });

  if (can('plat:aidatahub')) {
    actions.push({
      key: 'card',
      label: '📚 지식카드로 등록',
      title: 'AI 데이터 허브에 등록해 이후 검색·심의 근거로 쓴다',
      text: `붙인 ${one ? '문서를' : '문서들을'} 지식카드로 등록하려 합니다. `
        + 'describe_record_schema 로 규격을 먼저 확인하고, import_record 를 **dry_run=true 로** '
        + '돌려 모자란 항목(team·group 등)을 나에게 물어보세요. '
        + '내가 확인하기 전에는 실제 저장하지 마세요.',
    });
  }

  if (can('plat:reportarchive')) {
    actions.push({
      key: 'report',
      label: '📄 Report Archive 에 올리기',
      title: '이 문서를 보고서 초안으로 만든다 — 템플릿은 내가 고른다',
      // 긴 문서를 한 번의 도구 호출에 다 담으려 하면 출력 토큰 상한에 걸려 중간에서 끊긴다.
      // update_report_draft(page=N) 으로 쪽을 이어 붙이는 길을 미리 알려 준다.
      text: `붙인 ${one ? '문서를' : '문서들을'} Report Archive 에 보고서 초안으로 올리려 합니다.\n`
        + '1) list_templates 로 쓸 수 있는 템플릿을 보여 주세요. 문서 성격에 딱 맞는 게 없으면 '
        + '**없다고 말하고** 그중 가장 가까운 것을 근거와 함께 제안하세요 — 고르는 건 내가 합니다.\n'
        + '2) 내가 고르면 describe_template 으로 블록 구성을 확인하고, 본문은 extra_blocks '
        + '(heading·rich_text·table 위젯)에 담아 create_report_draft 를 dry_run=true 로 먼저 부르세요.\n'
        + '3) 문서가 길면 한 번에 다 넣지 말고 create_report_draft 로 앞쪽을 만든 뒤 '
        + 'update_report_draft(page=N) 으로 쪽을 이어 붙이세요. 몇 쪽으로 나눌지 먼저 알려 주세요.\n'
        + '4) 슬라이드·쪽 번호를 각 블록 제목에 남겨 원본과 대조할 수 있게 하세요.',
    });
  }

  return (
    <div className="doc-actions" role="group" aria-label="붙인 문서로 할 일">
      {actions.map((a) => (
        <button key={a.key} type="button" title={a.title} onClick={() => onFill(a.text)}>
          {a.label}
        </button>
      ))}
      <span className="doc-actions-hint">고르면 입력창에 채워집니다 — 고쳐서 보내세요.</span>
      {can('plat:reportarchive') && (
        <details className="doc-actions-note">
          <summary>보고서 템플릿이 문서와 안 맞는다면</summary>
          Report Archive 에는 자유형식 문서를 담는 <code>문서 가져오기</code> 템플릿이 있는데,
          <b>누군가 RA 웹에서 '가져오기'를 한 번 써야 만들어집니다</b>(get-or-create).
          한 번만 하면 그 뒤로는 여기서도 고를 수 있습니다.
        </details>
      )}
    </div>
  );
}
