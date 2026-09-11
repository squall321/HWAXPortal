// 도구 영역(하는 일) 칩 — 도구 선택 UI 세 곳(도구 카드·심의 선정·시작 선택기)이 같은 1단 필터를 쓴다
import type { ToolArea } from '../../types/chat';
import { toolAreaHint } from './toolAreas';

/** 영역 칩 줄. value=null 이 '전체', ''(빈 문자열)은 미분류다.
 *  같은 칩을 다시 누르면 해제된다 — 칩은 라디오지만 '아무것도 안 고름'으로 돌아갈 길이 있어야 한다. */
export function ToolAreaChips({
  areas,
  value,
  onChange,
}: {
  areas: ToolArea[];
  value: string | null;
  onChange: (area: string | null) => void;
}) {
  if (!areas.length) return null;
  return (
    <div className="ta-chips" role="radiogroup" aria-label="도구 영역">
      <button
        type="button"
        role="radio"
        aria-checked={value === null}
        className={`ta-chip${value === null ? ' is-on' : ''}`}
        onClick={() => onChange(null)}
      >
        전체
      </button>
      {areas.map((a) => {
        const on = value === a.area;
        return (
          <button
            key={a.area || '_none'}
            type="button"
            role="radio"
            aria-checked={on}
            className={`ta-chip${on ? ' is-on' : ''}${a.area ? '' : ' is-none'}`}
            title={a.desc || toolAreaHint(a.area)}
            onClick={() => onChange(on ? null : a.area)}
          >
            {a.label}
            <span className="ta-n">{a.tool_count}</span>
          </button>
        );
      })}
    </div>
  );
}
