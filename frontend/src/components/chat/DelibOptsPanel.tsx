// 심의 손잡이(깊이 회복 옵션) 웹 토글 패널 — env 재시작 없이 심의마다 옵션을 바꿔 A/B 한다
import { useCan } from '../../auth/useCan';
import { useChat } from '../../state/ChatContext';
import { DELIB_TIMEOUT_MAX_S } from '../../state/chatStore';
import type { DelibOpts } from '../../types/chat';
import { MODIFIERS } from './delibTaxonomy';
import { IconSliders } from './icons';
import { useWikiEnabled } from './useWikiEnabled';

// 표시 순서 = 권장 A/B 순서(GLM 리뷰 §5). heavy=부하 큰 옵션(경고 표식).
const FLAGS: { key: keyof DelibOpts; label: string; hint: string; heavy?: boolean }[] = [
  { key: 'evidence_prepass', label: '정량 근거 선주입', hint: '심의 전 지식·보고서 검색으로 수치를 컨텍스트에 주입 (권장 1순위)' },
  { key: 'rebut_quote', label: '반박 인용 계약', hint: '상대 발언 원문 인용을 강제·검증해 허수아비 반박 차단' },
  { key: 'cross_exam', label: '교차심문', hint: '지목 표적 1명의 원본 전체에 반박 (비용 중립)' },
  { key: 'anchor', label: '입장 앵커', hint: '수렴 라운드 동조 붕괴 방어' },
  { key: 'prose_first', label: '산문 후 JSON', hint: '형식 강제 완화로 사고 회수 (출력 1.5~2배·thinking 진단 후)', heavy: true },
  { key: 'chair_cite', label: '의장 출처 태깅', hint: '결정문 항목별 근거 라운드 표기 (가장 저렴)' },
];

// 손잡이가 아니라 진행 방식 — 위 A/B 플래그와 성격이 달라 따로 둔다.
const CHECKPOINT_HINT =
  '초기 입장만 듣고 멈춘다. 빠진 관점을 의견으로 보태 이어가면 좌석 재심사가 그 방향의 도메인을 불러온다';
// 결정문을 MX 백서 LLM 위키에도 — 범위는 내 소속, 소속이 없으면 '내 후보'(docs/mxwp-wiki P8). 켜 두면 이후 심의마다 남는다.
const WIKI_HINT =
  '결정문 · 표 · 소수 의견을 MX 백서 위키에 내 소속 범위로 남긴다. 소속이 없으면 MX 백서 \'내 후보\' 로 가서 승인해야 들어간다. '
  + '켜 두면 이후 심의마다 남는다';

const WIKI_OFF_HINT = '이 박스에서는 MX 백서 위키가 꺼져 있다 — 켜 둔 것을 끄기만 할 수 있다(켜 두면 결정문 끝에 실패 문구가 붙는다)';
// 기준일 — 소급 검증용(docs/request-1027 HA-11 · 사용자 결정 10-31 A-keep). 무엇을 거르지 않는지까지 적는다 — 감추면 '그 날 자료로만 돈 심의' 로 읽힌다.
const AS_OF_HINT =
  '이 날까지의 지식카드만 찾는다(소급 검증용). 날짜 없는 카드는 \'날짜 미확인\' 으로 남고, 날짜와 셈이 결정문 머리에 찍힌다. '
  + 'VOC · 보고서 · 다른 조회는 날짜로 거르지 않는다 — 그때 있던 자료만으로 보려면 봉인 실행이다. 켜 두면 이후 심의에도 걸린다';

// mods — 심의 첫 화면만 준다: '얹을 층'(방법 보강)은 새 심의를 시작할 때만 쓰여, 이어 묻는 화면에는 없다.
// 종전엔 첫 화면 한가운데 칩 줄로 나와 목적 카드·입력창 사이를 갈랐다(docs/ui-refresh 단계 4).
export function DelibOptsPanel({ mods }: { mods?: { on: ReadonlySet<string>; toggle: (id: string) => void } } = {}) {
  const { delibOpts, setDelibOpts } = useChat();
  // 권한이 사라져도 켜진 채 저장된 토글은 숨기지 않는다 — 보이지 않는 채 켜져 있으면 끌 길이 없다.
  const canWiki = useCan()('plat:mxwhitepaper');
  const wikiOn = useWikiEnabled(canWiki);
  // 위키가 꺼진 박스에서는 숨긴다 — 켠 사람의 결정문 끝에 내부 오류 문구가 붙었다(HP-16). 이미 켜 둔 것은 끄는 길만 남긴다.
  const showWiki = (canWiki && wikiOn !== false) || !!delibOpts.wiki;

  const setFlag = (key: keyof DelibOpts, on: boolean) =>
    setDelibOpts({ ...delibOpts, [key]: on });
  const setNum = (key: 'chair_bestof' | 'timeout_s' | 'rounds', v: number | undefined) =>
    setDelibOpts({ ...delibOpts, [key]: v });

  const active =
    FLAGS.filter((f) => delibOpts[f.key]).length +
    (delibOpts.chair_bestof && delibOpts.chair_bestof > 1 ? 1 : 0) +
    (delibOpts.stop_after_round === 1 ? 1 : 0) +
    (delibOpts.wiki ? 1 : 0) +
    (delibOpts.as_of ? 1 : 0) +
    (mods?.on.size ?? 0);

  return (
    // ⚠ SourcePanel(인터넷 검색 토글)을 여기서 렌더하지 않는다 — Composer 가 이미 그린다.
    // 이 패널은 언제나 Composer 와 함께 놓이므로 같은 토글이 화면에 두 번 나왔다.
    <details className="do-panel">
      <summary className="do-summary">
        <IconSliders className="do-gear" width={15} height={15} aria-hidden="true" />
        심의 옵션
        {active > 0 && <span className="do-count">{active}개 켜짐</span>}
      </summary>
      <div className="do-body">
        {mods && (
          <>
            <p className="do-section">방법 보강 — 고른 심의 목적 위에 덧붙입니다</p>
            <ul className="do-list">
              {MODIFIERS.map((m) => (
                <li key={m.id} className="do-item">
                  <label className="do-toggle">
                    <input type="checkbox" checked={mods.on.has(m.id)} onChange={() => mods.toggle(m.id)} />
                    <span className="do-label">{m.name}</span>
                  </label>
                  <span className="do-hint">{m.when}</span>
                </li>
              ))}
            </ul>
            <p className="do-section">진행</p>
          </>
        )}
        <ul className="do-list">
          <li className="do-item">
            <label className="do-toggle">
              <input
                type="checkbox"
                checked={delibOpts.stop_after_round === 1}
                onChange={(e) =>
                  setDelibOpts({ ...delibOpts, stop_after_round: e.target.checked ? 1 : undefined })
                }
              />
              <span className="do-label">1라운드 후 검토</span>
            </label>
            <span className="do-hint">{CHECKPOINT_HINT}</span>
          </li>
          {showWiki && (
            <li className="do-item">
              <label className="do-toggle">
                <input
                  type="checkbox"
                  checked={!!delibOpts.wiki}
                  disabled={wikiOn === false && !delibOpts.wiki}
                  onChange={(e) => setDelibOpts({ ...delibOpts, wiki: e.target.checked || undefined })}
                />
                <span className="do-label">MX 백서 위키에도 남기기</span>
              </label>
              <span className="do-hint">{wikiOn === false ? WIKI_OFF_HINT : WIKI_HINT}</span>
            </li>
          )}
          <li className="do-item">
            <span className="do-label">라운드 수</span>
            <select
              className="do-num"
              value={delibOpts.rounds ?? 3}
              onChange={(e) => setNum('rounds', Number(e.target.value))}
            >
              {[2, 3, 4, 5, 6, 7, 8].map((n) => (
                <option key={n} value={n}>
                  {n}라운드{n === 3 ? ' (기본)' : ''}
                </option>
              ))}
            </select>
            <span className="do-hint">1 초기입장 + 중간 심화·반박 + 마지막 수렴. 늘릴수록 깊어지지만 느려집니다</span>
          </li>
          <li className="do-item">
            <span className="do-label">기준일</span>
            {/* date 입력칸은 YYYY-MM-DD 만 낸다 — 비우면 거르지 않는다(보내기 전에 delibOptsToWire 가 꼴을 한 번 더 본다). */}
            <input
              type="date"
              className="do-num"
              aria-label="기준일"
              value={delibOpts.as_of ?? ''}
              onChange={(e) => setDelibOpts({ ...delibOpts, as_of: e.target.value || undefined })}
            />
            <span className="do-hint">{AS_OF_HINT}</span>
          </li>
        </ul>
        <p className="do-warn">아래 손잡이는 한 번에 하나씩 켜서 비교하세요 — 여러 개를 동시에 켜면 효과가 상쇄되고 부하가 커집니다.</p>
        <ul className="do-list">
          {FLAGS.map((f) => (
            <li key={f.key} className="do-item">
              <label className="do-toggle">
                <input
                  type="checkbox"
                  checked={!!delibOpts[f.key]}
                  onChange={(e) => setFlag(f.key, e.target.checked)}
                />
                <span className="do-label">
                  {f.label}
                  {f.heavy && <span className="do-heavy" title="부하 큰 옵션">부하↑</span>}
                </span>
              </label>
              <span className="do-hint">{f.hint}</span>
            </li>
          ))}
          <li className="do-item">
            <span className="do-label">
              의장 best-of
              <span className="do-heavy" title="부하 큰 옵션">부하↑</span>
            </span>
            <select
              className="do-num"
              value={delibOpts.chair_bestof ?? 1}
              onChange={(e) => setNum('chair_bestof', Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n === 1 ? '끔' : `${n}개→선택`}
                </option>
              ))}
            </select>
            <span className="do-hint">결정문 후보 n개 생성 후 심판 선택 (temp&gt;0 필요)</span>
          </li>
          <li className="do-item">
            <span className="do-label">호출 타임아웃</span>
            <span className="do-timeout">
              <input
                type="number"
                className="do-num"
                min={10}
                max={DELIB_TIMEOUT_MAX_S}
                step={30}
                placeholder="기본"
                value={delibOpts.timeout_s ?? ''}
                onChange={(e) =>
                  setNum('timeout_s', e.target.value ? Number(e.target.value) : undefined)
                }
              />
              <span className="do-unit">초</span>
            </span>
            {/* 짧은 값을 권하지 않는다 — 좌석이 많은 패널은 공유 LLM 에 줄을 서는 시간까지 이 시계에 들어간다. */}
            <span className="do-hint">
              LLM 호출 1회의 제한입니다(심의 전체가 아닙니다). 비우면 서버 기본 1800초 · 최대 {DELIB_TIMEOUT_MAX_S}초
            </span>
          </li>
        </ul>
      </div>
    </details>
  );
}
