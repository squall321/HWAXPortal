// 심의 관계도 — 누가 누구의 어떤 말을 반박했는지를 네트워크로 본다(회의록은 시간순이라 안 보인다)
import { useMemo, useState } from 'react';
import type { DelibData } from '../../types/chat';
import { colorOf, shortName } from './personaColor';
import { TextBlock } from './renderers/TextBlock';

/** 좌석 키 → mermaid 노드 id. 하이픈·점이 들어가면 mermaid 가 파싱을 못 한다. */
const nodeId = (key: string) => 'n' + key.replace(/[^0-9A-Za-z]/g, '_');

/** mermaid 라벨 안에서 깨지는 글자를 막는다 — 따옴표·괄호·개행. */
const safeLabel = (s: string) => s.replace(/["\n]/g, ' ').replace(/[[\]{}()]/g, '·').slice(0, 28);

interface Edge {
  from: string;
  to: string;
  round: number;
  counter: string;
  quote: string;
  basis: string;
}

/** 좌석 이름은 발언에 쓰인 표기가 제각각이라(키·이름·축약) 느슨하게 맞춘다. */
function resolveTarget(raw: string, seats: string[]): string | null {
  const t = raw.trim().toLowerCase();
  if (!t) return null;
  const exact = seats.find((s) => s.toLowerCase() === t);
  if (exact) return exact;
  return seats.find((s) => s.toLowerCase().includes(t) || t.includes(s.toLowerCase())) ?? null;
}

export function DelibGraph({ d }: { d: DelibData }) {
  const [open, setOpen] = useState(false);

  const { edges, seats } = useMemo(() => {
    const turns = d.turns ?? [];
    // 좌석 목록은 personas 를 정본으로 쓰되, 발언만 있고 명단에 없는 좌석도 살린다.
    const all = new Set<string>((d.personas ?? []).map((p) => p.key));
    for (const t of turns) all.add(t.persona);
    const list = [...all];
    const es: Edge[] = [];
    for (const t of turns) {
      for (const r of t.rebut ?? []) {
        const to = resolveTarget(r.target, list);
        // 대상을 못 찾으면 그리지 않는다 — 없는 사람을 가리키는 화살표는 거짓이다.
        if (!to || to === t.persona) continue;
        es.push({ from: t.persona, to, round: t.round, counter: r.counter, quote: r.quote, basis: r.basis });
      }
    }
    return { edges: es, seats: list };
  }, [d]);

  // ⚠ 조기 반환은 **훅을 전부 부른 뒤**에 둔다. 여기서 return 하면 아래 useMemo 가
  //   조건부 호출이 되어 훅 규칙 위반이다(렌더가 통째로 터진다).
  const engaged = useMemo(() => new Set(edges.flatMap((e) => [e.from, e.to])), [edges]);
  const chart = useMemo(() => {
    const lines = ['graph LR'];
    for (const s of seats) {
      if (!engaged.has(s)) continue; // 반박에 참여하지 않은 좌석은 고립점이라 뺀다
      lines.push(`  ${nodeId(s)}["${safeLabel(shortName(s))}"]`);
      lines.push(`  style ${nodeId(s)} fill:${colorOf(s)}22,stroke:${colorOf(s)},color:#e6e8eb`);
    }
    edges.forEach((e, i) => {
      lines.push(`  ${nodeId(e.from)} -->|"R${e.round}"| ${nodeId(e.to)}`);
      void i;
    });
    return lines.join('\n');
  }, [edges, seats, engaged]);

  // 반박이 하나도 없으면 그릴 관계가 없다. 빈 상자를 내밀지 않는다.
  if (edges.length === 0) return null;

  return (
    <section className="dg">
      <button type="button" className="dg-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? '▾' : '▸'} 관계도 — 반박 {edges.length}건 · 참여 {engaged.size}석
      </button>
      {open && (
        <>
          <p className="dg-note">
            화살표는 <b>반박한 방향</b>입니다(A → B = A가 B의 발언을 반박). 회의록은 시간순이라
            누가 누구를 향해 말했는지가 안 보입니다.
          </p>
          {/* 챗 본문과 같은 렌더러를 탄다 — mermaid 는 이미 거기 붙어 있다(따로 싣지 않는다). */}
          <TextBlock text={'```mermaid\n' + chart + '\n```'} />
          <ul className="dg-list">
            {edges.map((e, i) => (
              <li key={i}>
                <span className="dg-round">R{e.round}</span>
                <b style={{ color: colorOf(e.from) }}>{shortName(e.from)}</b>
                <span className="dg-arrow">→</span>
                <b style={{ color: colorOf(e.to) }}>{shortName(e.to)}</b>
                {e.quote && <span className="dg-quote">“{e.quote}”</span>}
                <span className="dg-counter">{e.counter}</span>
                {e.basis && <span className="dg-basis">근거 {e.basis}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
