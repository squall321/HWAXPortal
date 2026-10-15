# 세션이 끝나면 화면이 로그인으로 가는지 — 갱신이 401·403 이면 만료 이벤트를 내고 AuthContext 가 로그아웃 상태로 바꾼다(K2-1·2)
"""로그인 8시간 뒤 갱신이 403(CSRF 쿠키 만료)이 되면 프런트는 401 을 그대로 돌려줬고, 화면마다 「조회 실패(http_401) —
다시 시도하세요」만 되풀이했다. 로그인 화면으로 보내는 코드가 없었다(docs/request_1015.md K2, 10-14 실측: 14:18 에 끝난 세션이
16:39 에 사용자가 직접 로그아웃할 때까지 이어졌다).

프런트 전용이라 소스 지점을 본다 — 이벤트를 내는 곳(client.ts)과 듣는 곳(AuthContext.tsx) 중 하나만 빠져도 조용히 반쪽이 된다.
로그인 화면으로 보내는 일은 ProtectedRoute 가 이미 한다(status 가 unauthenticated 면 /login, 돌아올 경로는 state.from).
"""
from pathlib import Path

_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _between(src: str, start: str, end: str) -> str:
    i = src.index(start)
    return src[i:src.index(end, i)]


def test_갱신이_401_403_으로_끝나면_만료_이벤트를_낸다():
    src = (_FRONT / "api" / "client.ts").read_text("utf-8")
    assert "export const SESSION_EXPIRED_EVENT = 'hwax:session-expired';" in src
    fn = _between(src, "function doRefresh", "export async function apiFetch")
    then = _between(fn, ".then(", ".catch(")
    assert "r.status === 401 || r.status === 403" in then, "403 은 CSRF 쿠키가 없어서다 — 401 과 같은 만료다"
    assert "window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))" in then
    assert "return r.ok;" in then
    assert "dispatchEvent" not in fn[fn.index(".catch("):], "네트워크 오류는 순간 끊김일 수 있다 — 로그아웃시키지 않는다"


def test_만료_이벤트를_받으면_로그아웃_상태로_바꾸고_ste_사본을_지운다():
    src = (_FRONT / "auth" / "AuthContext.tsx").read_text("utf-8")
    assert "import { SESSION_EXPIRED_EVENT } from '../api/client';" in src
    body = _between(src, "const onExpired = () => {", "};")
    for need in ("clearSteCredential();", "setUser(null);", "setStatus('unauthenticated');"):
        assert need in body, f"{need} 가 없다"
    # 앞 사람의 ste 토큰이 브라우저에 남으면 이 탭에서 다음에 로그인한 사람이 그대로 쓴다(StePrimer 는 사본이 있으면 다시 안 받는다)
    assert body.index("clearSteCredential();") < body.index("setStatus('unauthenticated');")
    # 서버 회수·로그아웃은 부르지 않는다 — 세션이 없어 401·403 이다(10-14 16:39 실측)
    assert "revokeSteCredential(" not in body and "postLogout(" not in body
    assert "window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);" in src
    assert "return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);" in src


def test_로그인_화면으로_보내는_길은_그대로다():
    """이벤트가 status 만 바꾸면 ProtectedRoute 가 /login 으로 보내고 돌아올 경로를 담는다 — 이 길이 바뀌면 위 두 곳이 헛돈다."""
    src = (_FRONT / "auth" / "ProtectedRoute.tsx").read_text("utf-8")
    assert "if (status === 'unauthenticated') {" in src
    assert '<Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />' in src
