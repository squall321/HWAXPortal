// 심의 손잡이(깊이 회복 옵션) 웹 토글 패널 — env 재시작 없이 심의마다 옵션을 바꿔 A/B 한다
import { useChat } from '../../state/ChatContext';
import type { DelibOpts } from '../../types/chat';

// 표시 순서 = 권장 A/B 순서(GLM 리뷰 §5). heavy=부하 큰 옵션(경고 표식).
const FLAGS: { key: keyof DelibOpts; label: string; hint: string; heavy?: boolean }[] = [
  { key: 'evidence_prepass', label: '정량 근거 선주입', hint: '심의 전 지식·보고서 검색으로 수치를 컨텍스트에 주입 (권장 1순위)' },
  { key: 'rebut_quote', label: '반박 인용 계약', hint: '상대 발언 원문 인용을 강제·검증해 허수아비 반박 차단' },
  { key: 'cross_exam', label: '교차심문', hint: '지목 표적 1명의 원본 전체에 반박 (비용 중립)' },
  { key: 'anchor', label: '입장 앵커', hint: '수렴 라운드 동조 붕괴 방어' },
  { key: 'prose_first', label: '산문 후 JSON', hint: '형식 강제 완화로 사고 회수 (출력 1.5~2배·thinking 진단 후)', heavy: true },
  { key: 'chair_cite', label: '의장 출처 태깅', hint: '결정문 항목별 근거 라운드 표기 (가장 저렴)' },
];

export function DelibOptsPanel() {
  const { delibOpts, setDelibOpts } = useChat();

  const setFlag = (key: keyof DelibOpts, on: boolean) =>
    setDelibOpts({ ...delibOpts, [key]: on });
  const setNum = (key: 'chair_bestof' | 'timeout_s', v: number | undefined) =>
    setDelibOpts({ ...delibOpts, [key]: v });

  const active =
    FLAGS.filter((f) => delibOpts[f.key]).length +
    (delibOpts.chair_bestof && delibOpts.chair_bestof > 1 ? 1 : 0);

  return (
    <details className="do-panel">
      <summary className="do-summary">
        <span className="do-gear" aria-hidden="true">⚙</span>
        심의 옵션
        {active > 0 && <span className="do-count">{active}개 켜짐</span>}
      </summary>
      <div className="do-body">
        <p className="do-warn">한 번에 하나씩 켜서 비교하세요 — 여러 개를 동시에 켜면 효과가 상쇄되고 부하가 커집니다.</p>
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
                max={1800}
                step={30}
                placeholder="기본"
                value={delibOpts.timeout_s ?? ''}
                onChange={(e) =>
                  setNum('timeout_s', e.target.value ? Number(e.target.value) : undefined)
                }
              />
              <span className="do-unit">초</span>
            </span>
            <span className="do-hint">LLM 호출당 제한. 무거운 옵션엔 600 권장 (비우면 서버 기본값)</span>
          </li>
        </ul>
      </div>
    </details>
  );
}
