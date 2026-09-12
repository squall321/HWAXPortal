// 문서를 붙인 뒤 '어디로 보낼지' 고르는 선택지 — 고르면 입력창에 채운다(보내는 건 사람이)
import { useEffect, useRef } from 'react';
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import { DEST_APPS } from './destApps';
import type { AttachedDoc } from './docAttach';

interface Props {
  docs: AttachedDoc[];
  onFill: (text: string) => void;
}

/** 행선지 하나. **여기 한 줄 더 쓰면 선택지가 는다** — 플랫폼은 계속 늘어난다. */
interface Destination {
  key: string;
  label: string;
  /** 마우스를 올렸을 때 — '언제 이걸 고르나'. 이름만 봐선 모른다. */
  title: string | ((deck: boolean) => string);
  /** 필요한 권한 키. 없으면 누구나. */
  need?: string;
  /** 이 형식에서만 보인다. 없으면 항상. */
  onlyKinds?: string[];
  /** 모델에게 줄 지시문. 되돌리기 어려운 도구는 **확인 단계를 지시문에 박는다.** */
  text: (ctx: { one: boolean; names: string }) => string;
}

/** 행선지 목록.
 *
 *  왜 별도 API 가 아니라 지시문인가 — 등록·발행은 되돌리기 어렵다. 전용 라우트를 파면 확인
 *  절차를 거기 다시 지어야 하는데 챗 경로엔 이미 있다(`import_record` 의 dry_run,
 *  `create_report_draft` 의 템플릿 확인). 지시문만 채우면 코드가 줄고 확인이 한 곳에 남는다.
 *
 *  무엇이 여기 들어올 수 있나 — 판정 기준은 하나다. **본문을 문자열로 받는가.** DRM 문서는 그
 *  PC 에서만 복호화되므로 서버 경로를 받는 도구(convert_file·import_file·report_ingest·intake·
 *  RA /imports/pptx)는 전부 막힌다. COM 추출은 그것들 **각각의** 대체재다(D-23).
 *
 *  ⚠ 어떤 것도 **자동으로 보내지 않는다.** 쓸 수 있는 곳이 하나뿐이어도 고르는 건 사람이다 —
 *  목록은 앞으로 계속 늘고, 하나뿐이라서 자동으로 보내면 는 순간 습관이 어긋난다. */
const DESTINATIONS: Destination[] = [
  {
    key: 'delib',
    label: '⚖ 심의 걸기',
    title: '판단이 갈리는 것을 전문가 좌석으로 수렴시킨다',
    need: 'feat:deliberation',
    text: ({ one, names }) =>
      `/심의 붙인 ${one ? '문서' : '문서들'}(${names})의 내용을 근거로 검토해 주세요. `
      + '여기에 무엇을 판단해 달라고 할지 한 문장으로 적으세요.',
  },
  {
    key: 'read',
    label: '📖 요약·쟁점 뽑기',
    title: '아무 데도 등록하지 않고 내용만 읽는다',
    text: ({ one }) =>
      `붙인 ${one ? '문서' : '문서들'}을 읽고 ① 핵심 결론 ② 근거가 약한 대목 `
      + '③ 이 자료만으로는 판단할 수 없는 것을 나눠서 정리해 주세요. '
      + '각 항목에 몇 번째 슬라이드·쪽에서 나온 것인지 표기하세요.',
  },
  {
    key: 'card',
    label: '📚 지식카드로 등록',
    need: 'plat:aidatahub',
    title: (deck) => (deck
      ? '발표자료엔 드물지만 교육자료·회의록·설계사양서라면 여기다 — 이후 검색·심의 근거로 재사용된다'
      : 'AI 데이터 허브에 등록해 이후 검색·심의 근거로 재사용한다'),
    text: ({ one }) =>
      `붙인 ${one ? '문서를' : '문서들을'} 지식카드로 등록하려 합니다.\n`
      + '1) list_doc_types 로 분류를 보고 이 문서에 맞는 doc_type 을 제안하세요 '
      + '(예: 설계사양서 design_spec · 시험계획 test_plan · 교육자료 training · 회의록 meeting_minutes). '
      + '**맞는 분류가 없으면 없다고 말하세요** — 분류가 어긋나면 나중에 검색으로 안 찾힙니다.\n'
      + '2) describe_record_schema 로 규격을 확인하고 import_record 를 **dry_run=true 로** 돌려 '
      + '모자란 항목(team·group·year 등)을 나에게 물어보세요.\n'
      + '3) 내가 확인하기 전에는 실제 저장하지 마세요.',
  },
  {
    key: 'report',
    label: '📄 Report Archive 에 올리기',
    need: 'plat:reportarchive',
    title: '보고서 초안으로 남긴다 — 템플릿은 내가 고른다',
    // 긴 문서를 한 번의 도구 호출에 다 담으려 하면 출력 토큰 상한에 걸려 중간에서 끊긴다.
    text: ({ one }) =>
      `붙인 ${one ? '문서를' : '문서들을'} Report Archive 에 보고서 초안으로 올리려 합니다.\n`
      + '1) list_templates 로 쓸 수 있는 템플릿을 보여 주세요. 문서 성격에 딱 맞는 게 없으면 '
      + '**없다고 말하고** 그중 가장 가까운 것을 근거와 함께 제안하세요 — 고르는 건 내가 합니다.\n'
      + '2) 내가 고르면 describe_template 으로 블록 구성을 확인하고, 본문은 extra_blocks '
      + '(heading·rich_text·table 위젯)에 담아 create_report_draft 를 dry_run=true 로 먼저 부르세요.\n'
      + '3) 문서가 길면 한 번에 다 넣지 말고 create_report_draft 로 앞쪽을 만든 뒤 '
      + 'update_report_draft(page=N) 으로 쪽을 이어 붙이세요. 몇 쪽으로 나눌지 먼저 알려 주세요.\n'
      + '4) 슬라이드·쪽 번호를 각 블록 제목에 남겨 원본과 대조할 수 있게 하세요.\n'
      + '5) 만든 뒤 suggest_report_tags → add_report_tags 로 축 태그를 붙이세요 — '
      + '**안 붙으면 나중에 목록·집계에서 안 찾힙니다.**\n'
      + '6) 초안은 내 개인함에 생깁니다. **어느 부서 게시판에 올릴지는 내가 고릅니다** — '
      + 'list_boards 로 후보를 보여 주고, 내가 고르면 preview_publish 로 대상을 확인시킨 뒤 '
      + 'publish_report 로 게시하세요(토큰은 10분·그 게시판 조합에만 유효). '
      + '폴더까지 정할 거면 list_folders → set_report_folders 입니다. '
      + '개인함에만 두겠다고 하면 게시하지 마세요.',
  },
  {
    key: 'wiki',
    label: '📘 MX 백서에 싣기',
    need: 'plat:mxwhitepaper',
    title: '사내 업무 백서(위키)에 문서를 만든다 — 노하우·가이드가 여기 쌓인다',
    // import_file(path) 는 서버가 파일을 읽어 DRM 에서 막힌다 — 추출문으로 같은 일을 한다.
    text: ({ one }) =>
      `붙인 ${one ? '문서를' : '문서들을'} MX 백서에 싣고 싶습니다.\n`
      + '1) search_documents 로 같은 주제 문서가 이미 있는지 먼저 보세요 — 있으면 새로 만들지 말고 '
      + '그 문서에 이어 붙일지 물어보세요.\n'
      + '2) 새로 만들 거면 create_document 로 문서를 만들고, query_rules 로 블록 작성법을 확인한 뒤 '
      + 'insert_block 으로 섹션을 채우세요. validate_block 으로 미리 검증하면 실패가 줍니다.\n'
      + '3) 슬라이드·쪽 번호를 소제목에 남겨 원본과 대조할 수 있게 하세요.',
  },
  {
    key: 'paper',
    label: '🔬 논문 코퍼스에 넣기',
    need: 'plat:paperingest',
    title: '외부 논문·특허라면 — 분류·색인·그라운딩을 거쳐 전문가 지식카드의 근거가 된다',
    text: ({ one }) =>
      `붙인 ${one ? '문서가' : '문서들이'} 외부 학술 논문(또는 특허)이면 코퍼스에 넣고 싶습니다.\n`
      + '1) 먼저 이게 **사내 산출물이 아니라 외부 문헌인지** 확인하세요. 사내 보고서면 여기가 아니라 '
      + 'Report Archive 나 지식카드입니다 — 아니면 그렇다고 말해 주세요.\n'
      + '2) 맞으면 submit_paper 로 본문(markdown)을 스테이징하고 inbox_status 로 대기 상태를 알려 주세요.\n'
      + '3) ingest_now 는 분류·색인·게이트까지 도는 무거운 작업이니 내가 시킬 때만 부르세요.',
  },
  {
    key: 'dyna',
    label: '💥 DynaForge 세션으로',
    need: 'plat:dynaforge',
    onlyKinds: ['html'],   // ingest_report 가 받는 것이 바로 이 형식이다
    title: '낙하·충격 해석 리포트라면 — 세션에 넣어 부품별 에너지·위험도를 본다',
    text: () =>
      '붙인 HTML 이 낙하·충격 해석 리포트라면 DynaForge 세션에 넣고 싶습니다.\n'
      + '1) 먼저 내용으로 낙하/충격 리포트가 맞는지 확인하세요 — 아니면 아니라고 말해 주세요.\n'
      + '2) 맞으면 create_session 후 ingest_report 로 넣고, 어떤 종류(deep/sphere/impact)로 '
      + '판별됐는지 알려 주세요.\n'
      + '⚠ 원본이 수십 MB 이상이면 이 경로가 아닙니다 — report_upload_instructions 로 REST intake '
      + '명령을 받아 그걸 쓰세요.',
  },
];

/** 형식별 우선순위. 없애지 않고 **순서만** 바꾼다 — 교육자료·회의록은 PPT 로 오고,
 *  논문을 PPT 로 받는 일도 있다. 목록에 없는 행선지는 뒤로 간다. */
const RANK: Record<string, string[]> = {
  ppt: ['delib', 'read', 'report', 'wiki', 'card', 'paper'],   // 검토·보고 자료
  word: ['read', 'card', 'wiki', 'delib', 'report', 'paper'],  // 표준·절차서는 재사용 자산
  pdf: ['read', 'paper', 'card', 'wiki', 'delib', 'report'],   // 논문일 확률이 높다
  html: ['dyna', 'read', 'delib', 'card', 'wiki', 'report', 'paper'],
};

export function DocActions({ docs, onFill }: Props) {
  const can = useCan();
  const { pinnedApps, input } = useChat();
  const ctx = { one: docs.length === 1, names: docs.map((d) => d.meta?.source || d.name).join(', ') };
  const kinds = new Set(docs.map((d) => d.meta?.kind).filter(Boolean) as string[]);
  const deck = kinds.has('ppt');

  const order = RANK[docs[0]?.meta?.kind ?? ''] ?? RANK.word;
  const shown = DESTINATIONS
    .filter((d) => (!d.need || can(d.need)) && (!d.onlyKinds || d.onlyKinds.some((k) => kinds.has(k))))
    .sort((a, b) => {
      const ia = order.indexOf(a.key), ib = order.indexOf(b.key);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });

  // 지금 고른 전문가가 그 앱의 운영자면 그쪽이 추천이다 — 앞에 놓고 입력창에 **미리 채운다.**
  // 사람은 읽고 보내기만 하면 된다(확인 한 번). 자동 전송은 하지 않는다.
  const rec = shown.find((d) => (DEST_APPS[d.key] ?? []).some((a) => pinnedApps.includes(a)));
  const ordered = rec ? [rec, ...shown.filter((d) => d !== rec)] : shown;

  // 붙인 문서가 바뀔 때 한 번만 채운다. 사람이 이미 쓰던 글은 덮지 않는다.
  const filledFor = useRef('');
  const sig = docs.map((d) => d.name).join('|') + '#' + (rec?.key ?? '');
  useEffect(() => {
    if (!rec || filledFor.current === sig) return;
    filledFor.current = sig;
    if (!input.trim()) onFill(rec.text(ctx));
    // ctx·onFill 은 매 렌더 새로 만들어져 의존성에 넣으면 매번 다시 돈다 — sig 로 1회를 보장한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig, rec, input]);

  return (
    <div className="doc-actions" role="group" aria-label="붙인 문서를 어디로 보낼지">
      {ordered.map((d) => (
        <button key={d.key} type="button" onClick={() => onFill(d.text(ctx))}
          className={d === rec ? 'doc-rec' : undefined}
          title={typeof d.title === 'function' ? d.title(deck) : d.title}>
          {d.label}{d === rec && <em> · 지금 전문가</em>}
        </button>
      ))}
      <span className="doc-actions-hint">고르면 입력창에 채워집니다 — 읽고 고쳐서 보내세요.</span>
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
