// 허브에 보일 앱 — 개인 Claude(Code·Desktop 등)의 허브 도구 목록·검색에서 관심 없는 앱을 끄는 표(docs/mcp-app-toggle)
import { useEffect, useState } from 'react';
import { fetchHubApps, saveHubApp, type HubApps } from '../api/access.api';
import '../styles/tokenpage.css';

export default function HubAppsPanel() {
  const [data, setData] = useState<HubApps | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    fetchHubApps()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const toggle = async (app: string, muted: boolean) => {
    if (!data || saving) return;
    setSaving(app);
    setError(null);
    try {
      setData(await saveHubApp(app, muted));
    } catch (e) {
      setError((e as Error).message);
      // 실패하면 서버의 지금 상태로 다시 그린다 — 옛 화면을 들고 있으면 다른 탭에서 바꾼 것과 어긋난 채 남는다.
      // 다시 읽기가 끝날 때까지 스위치를 잠가 둔다(안 기다리면 그 사이 누른 스위치를 늦게 온 옛 표가 되돌린다).
      await fetchHubApps()
        .then(setData)
        .catch(() => {});
    } finally {
      setSaving(null);
    }
  };

  return (
    <section className="tok-sec">
      {/* 제목은 토큰 화면의 탭 이름('허브에 보일 앱')이 대신한다. 표 모양은 같은 화면의 '내 토큰' 표(tokenpage.css)를 쓴다 */}
      <p className="tok-muted hub-lead">
        관심 없는 앱을 끄면 개인 Claude 의 허브 도구 목록과 도구 검색에서 빠집니다. 권한과는 별개이고, 포털 웹 챗·웹 심의에는 영향이
        없습니다(Claude Code 에서 돌리는 심의도 개인 Claude 라 끈 앱이 검색에서 빠집니다). 도구 검색은 바로 바뀌고, 열려 있는 Claude 의 도구 목록은 다시 연결해야 바뀝니다 — Claude Code 는 <code>/mcp</code>
        에서 hwax 재연결(또는 재시작), Desktop 은 완전히 종료한 뒤 다시 실행하세요.
      </p>
      {error && (
        <p role="alert" className="tok-danger">
          {error}
        </p>
      )}
      {!data ? (
        !error && <p className="tok-muted">불러오는 중…</p>
      ) : (
        <div className="tok-table-wrap">
          <table className="tok-table hub-apps">
            <thead>
              <tr>
                <th>앱</th>
                <th className="hub-num">도구</th>
                <th>상태</th>
                <th>허브에 보이기</th>
              </tr>
            </thead>
            <tbody>
              {data.apps.map((a) => (
                <tr key={a.app}>
                  <td title={a.description || a.app}>
                    {a.label}
                    <span className="hub-key">{a.app}</span>
                  </td>
                  <td className="hub-num">{a.tool_count}</td>
                  <td className="hub-state">
                    {a.absent ? '지금 없음' : !a.allowed ? '권한 없음' : a.reachable ? '연결됨' : '연결 끊김'}
                  </td>
                  <td>
                    <label className="hub-switch">
                      <input
                        id={`hub-app-${a.app}`}
                        type="checkbox"
                        checked={!a.muted}
                        // 앱 이름을 붙인다 — 없으면 화면 낭독기가 스위치마다 '보임/꺼짐' 만 읽는다
                        aria-label={`${a.label} 허브에 보이기`}
                        // disabled 로 막으면 저장하는 동안 포커스가 사라진다 — 알리기만 하고 중복 저장은 toggle 이 막는다
                        aria-disabled={saving !== null}
                        onChange={() => toggle(a.app, !a.muted)}
                      />
                      {saving === a.app ? '저장 중…' : a.muted ? '꺼짐' : '보임'}
                    </label>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
