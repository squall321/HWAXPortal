// 개인 Claude 보기 — 허브 도구 목록을 전체 · 묶음(고른 영역) · 가벼운(찾기 · 부르기 둘)으로 고르는 칸(docs/request-1029 E-4)
import { useEffect, useRef, useState } from 'react';
import { fetchHubView, saveHubView, type HubView, type HubViewMode } from '../api/access.api';
import '../styles/tokenpage.css';

const MODES: { mode: HubViewMode; label: string; desc: string }[] = [
  { mode: 'full', label: '전체', desc: '내 권한 안의 허브 도구를 모두 싣습니다(지금과 같습니다).' },
  {
    mode: 'bundle',
    label: '묶음',
    desc: '고른 영역의 도구 + 정본 허브 읽기 도구 다섯 + 허브 자체 도구를 싣습니다. 형제 허브의 같은 도구 사본은 싣지 않습니다.',
  },
  {
    mode: 'light',
    label: '가벼운',
    desc: 'search_tools · invoke_tool 두 도구만 싣습니다 — 찾아서 부릅니다.',
  },
];

// 저장해 둔 영역 가운데 지금 게이트웨이에 없는 것은 고른 칸에서 뺀다 — 그대로 두면 저장이 '모르는 영역' 으로 거절된다
function knownAreas(v: HubView): string[] {
  return v.areas.filter((a) => !v.unknown_areas.includes(a));
}

// rev — 같은 탭의 '허브에 보일 앱' 이 바뀌면 올라간다(끈 앱은 영역 수에서 빠지므로 수만 다시 읽는다. 고르던 것은 그대로 둔다)
export default function HubViewPanel({ rev = 0 }: { rev?: number }) {
  const [data, setData] = useState<HubView | null>(null);
  const [mode, setMode] = useState<HubViewMode>('full');
  const [areas, setAreas] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const first = useRef(true);

  useEffect(() => {
    let alive = true;
    fetchHubView()
      .then((v) => {
        if (!alive) return;
        setData(v);
        if (first.current) {
          first.current = false;
          setMode(v.mode);
          setAreas(knownAreas(v));
        }
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [rev]);

  // 고른 영역은 차례와 상관없이 견준다 — 껐다 다시 켠 영역이 '바뀜' 으로 보이지 않게
  const sameAreas = (a: string[], b: string[]) =>
    [...a].sort().join(',') === [...b].sort().join(',');
  const dirty =
    !!data && (mode !== data.mode || (mode === 'bundle' && !sameAreas(areas, data.areas)));
  const valid = mode !== 'bundle' || areas.length > 0;

  const toggleArea = (area: string) => {
    setSaved(false);
    setAreas((cur) => (cur.includes(area) ? cur.filter((a) => a !== area) : [...cur, area]));
  };

  const save = async () => {
    if (!dirty || !valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      const v = await saveHubView(mode, mode === 'bundle' ? areas : []);
      setData(v);
      setMode(v.mode);
      setAreas(knownAreas(v));
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="tok-sec hub-view" aria-labelledby="hub-view-title">
      <h2 id="hub-view-title">개인 Claude 보기</h2>
      <p className="tok-muted hub-lead">
        개인 Claude(Code · Desktop)가 허브에서 받는 도구 목록의 크기를 고릅니다. 보기는 목록만
        줄입니다 — 목록 밖 도구도 <code>search_tools</code> 로 찾아 <code>invoke_tool</code> 로
        부르고, 권한은 그대로입니다. 아래 표에서 끈 앱은 어느 보기에서도 빠집니다.
      </p>
      {error && (
        <p role="alert" className="tok-danger">
          {error}
        </p>
      )}
      {!data ? (
        !error && <p className="tok-muted">불러오는 중…</p>
      ) : (
        <>
          {!data.view_supported && (
            <p role="status" className="tok-danger">
              지금 허브(게이트웨이)는 보기를 아직 모릅니다 — 고른 보기는 저장되지만, 게이트웨이가 새
              판으로 바뀌기 전까지 도구 목록은 전체 그대로입니다.
            </p>
          )}
          <fieldset className="hub-view-modes">
            <legend className="hub-view-legend">보기</legend>
            {MODES.map((m) => (
              <label key={m.mode} className="hub-view-mode">
                <input
                  type="radio"
                  name="hub-view-mode"
                  value={m.mode}
                  checked={mode === m.mode}
                  onChange={() => {
                    setSaved(false);
                    setMode(m.mode);
                  }}
                />
                <span>
                  <b>{m.label}</b>
                  {data.mode === m.mode && <span className="hub-view-now"> · 지금</span>}
                  <span className="hub-view-desc">{m.desc}</span>
                </span>
              </label>
            ))}
          </fieldset>
          {mode === 'bundle' && (
            <fieldset className="hub-view-areas">
              <legend className="hub-view-legend">
                묶음에 실을 영역 — 하나 이상(숫자는 내 권한 안의 도구 수)
              </legend>
              {data.area_options.map((o) => (
                <label key={o.area} className="hub-view-area" title={o.description || o.area}>
                  <input
                    type="checkbox"
                    checked={areas.includes(o.area)}
                    onChange={() => toggleArea(o.area)}
                  />
                  <span>{o.label}</span>
                  <span className="hub-num">{o.tool_count}</span>
                </label>
              ))}
            </fieldset>
          )}
          <ul className="tok-muted hub-view-notes">
            <li>
              열려 있는 Claude 세션의 도구 목록은 다시 연결해야 바뀝니다 — Claude Code 는{' '}
              <code>/mcp</code> 에서 hwax 재연결(또는 재시작), Desktop 은 완전히 종료한 뒤 다시
              실행하세요.
            </li>
            {mode === 'light' && (
              <li>
                가벼운 보기에서는 패널 도구(SimFlow · ARP 의 open_* 등)의 패널이 뜨지 않고, 파괴 ·
                제어 도구(delete_ · cancel_ 등)는 <code>invoke_tool</code> 로 부를 수 없어 닿지
                않습니다(전체 보기로 바꿔 씁니다). 모든 호출이 <code>invoke_tool</code> 한 도구의
                허락으로 묻습니다.
              </li>
            )}
            {mode === 'bundle' && (
              <li>
                영역이 없는(미분류) 도구 {data.unclassified}개는 어느 묶음에도 들지 않습니다 —{' '}
                <code>search_tools</code> 로 찾아 부릅니다.
              </li>
            )}
            <li>
              보기는 이 화면의 등록 배치 · 명령으로 붙인 Claude Code · Desktop 에만 먹습니다(연결 머리{' '}
              <code>X-HWAX-View: portal</code>). 이 기능 전에 받은 배치로 등록했으면 새 토큰으로
              배치를 다시 받아 돌리거나, 등록 설정의 hwax 머리에 그 줄을 더하세요.
            </li>
            <li>
              그 머리가 없는 연결은 늘 전체입니다 — 내 토큰으로 서버에서 도는 앱(리스크 심사 · 위키
              등), 스크립트, Gemini · Codex, 리포 파이프라인(리포 <code>.mcp.json</code> 으로 도는
              심의 · 리스크 워크플로). 포털 웹 챗 · 웹 심의 · 절차에도 영향이 없습니다.
            </li>
          </ul>
          {data.unknown_areas.length > 0 && (
            <p className="tok-danger">
              저장해 둔 영역 가운데 지금 허브에 없는 것: {data.unknown_areas.join(', ')} — 다시
              저장하면 빠집니다.
            </p>
          )}
          <div className="hub-view-actions">
            <button
              type="button"
              className="btn-primary"
              disabled={!dirty || !valid || saving}
              onClick={() => void save()}
            >
              {saving ? '저장 중…' : '보기 저장'}
            </button>
            {mode === 'bundle' && !valid && (
              <span className="tok-muted">영역을 하나 이상 고르세요.</span>
            )}
            {saved && !dirty && (
              <span role="status" className="tok-muted">
                {data.view_supported
                  ? '저장했습니다 — 새로 연결할 때부터 적용됩니다.'
                  : '저장했습니다 — 다만 지금 게이트웨이는 보기를 몰라 목록이 전체로 돕니다(게이트웨이가 새 판으로 바뀐 뒤부터 먹습니다).'}
              </span>
            )}
          </div>
        </>
      )}
    </section>
  );
}
