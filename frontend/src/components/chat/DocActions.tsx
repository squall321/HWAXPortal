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
      label: '📄 보고서 초안으로',
      title: 'Report Archive 에 초안을 만든다',
      text: `붙인 ${one ? '문서로' : '문서들로'} 보고서 초안을 만들려 합니다. `
        + 'list_templates → describe_template 순으로 보고 **어느 템플릿에 어떻게 담을지 먼저 제안**해 '
        + '주세요. 내가 고른 다음에 create_report_draft 를 부르세요.',
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
    </div>
  );
}
