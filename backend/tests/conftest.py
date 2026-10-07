# 시험이 운영 감사 원장·계정 원장(/data 의 agent_audit.sqlite · users.sqlite)을 건드리지 않게 — 포털 기동(lifespan)이 get_settings() 로 경로를 읽는다
#
# get_settings() 는 lru_cache 라 **처음 불리기 전에** 환경을 정해야 한다 — 시험 모듈보다 먼저 읽히는 이 파일에서.
# 이게 없어서 dev 실원장 agent_audit 814줄 중 622줄이 시험 계정(user@corp.com)의 챗 기록이었다(2026-09-30 실측).
# 접속 원장(access_log, docs/access-history)은 시험 로그인마다 줄이 생기므로 그대로 두면 운영 이력이 시험으로 덮인다.
# 이미 명시로 정한 값은 그대로 둔다(setdefault).
import os
import tempfile

os.environ.setdefault(
    "AGENT_AUDIT_LOG_PATH",
    os.path.join(tempfile.mkdtemp(prefix="hwax-test-audit-"), "agent_audit.sqlite"))
# 계정 원장도 같은 이유로 — 시험이 `TestClient(app)` 로 포털을 띄우면 기동(lifespan)이 원장을 열고 **스키마 이관을 돌린다.**
# 칸을 더하는 변경(dept_id, 10차 요청 §7)을 넣자, 시험을 돌린 것만으로 그 박스의 실 원장(/data 의 users.sqlite)에 칸이 생기게 됐다
# — 재기동 전의 떠 있는 포털 밑에서. 시험마다 `app.state.user_store` 를 임시 원장으로 바꾸는 것은 기동 **뒤**라 이것을 못 막는다.
os.environ.setdefault(
    "USER_STORE_PATH",
    os.path.join(tempfile.mkdtemp(prefix="hwax-test-users-"), "users.sqlite"))
# 사용자를 정지하면 앱 쪽 자격도 회수한다(8차 요청 §7 — 게이트웨이 `/conn-invalidate` · ste `/api/auth/sso/revoke`). 그대로 두면 시험이
# 사용자를 정지할 때마다 이 박스에 **떠 있는** 게이트웨이를 backend/.env 의 실제 공유 시크릿으로 부른다 — 시험은 공유 서비스를 치면
# 안 된다(test_procedures_routes 의 같은 경고). 게이트웨이 기본 주소를 닫힌 포트로 돌리고 ste 위임은 끈다. 이 호출을 보는 시험은
# Settings 에 주소·비밀을 직접 주고 HTTP 대역을 건다(test_suspend_revokes_app_credentials).
os.environ.setdefault("MCP_GATEWAY_URL", "http://127.0.0.1:9")
os.environ.setdefault("STE_SSO_SECRET", "")
