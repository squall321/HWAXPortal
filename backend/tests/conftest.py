# 시험이 이 박스의 실 저장소(/data 의 감사·계정·토큰·대화 원장, 절차 저장소)를 건드리지 않게 — 포털 기동(lifespan)이 get_settings() 로 경로를 읽는다
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
# 나머지 셋(토큰·대화·절차 저장소)도 같은 이유로 — 기동이 이 박스의 실 저장소를 열었다(dev 는 /data/svc/portal 로 걸린 그 파일들이다).
#   · 토큰 — 시험이 낸 PAT 가 실 원장에 쌓이고, 정지·관리자 해제 시험의 revoke_all_for 가 실 원장에서 돈다.
#   · 절차 — 기동이 close_stale() 로 '돌던 단계' 를 unknown 으로 마감한다. 떠 있는 포털이 실제로 돌리던 단계까지 닫는다.
#   · 대화 — 스키마 이관이 실 DB 에서 돈다.
# 무엇을 열었는지는 test_suite_isolation 이 포털을 띄워 sqlite 에 직접 물어 본다.
for _key, _name in (("TOKEN_STORE_PATH", "token_store.sqlite"), ("CONV_STORE_PATH", "conversations.sqlite"),
                    ("PROCEDURES_STORE_PATH", "procedures.sqlite")):
    os.environ.setdefault(_key, os.path.join(tempfile.mkdtemp(prefix="hwax-test-store-"), _name))
# 사용자를 정지하면 앱 쪽 자격도 회수한다(8차 요청 §7 — 게이트웨이 `/conn-invalidate` · ste `/api/auth/sso/revoke`). 그대로 두면 시험이
# 사용자를 정지할 때마다 이 박스에 **떠 있는** 게이트웨이를 backend/.env 의 실제 공유 시크릿으로 부른다 — 시험은 공유 서비스를 치면
# 안 된다(test_procedures_routes 의 같은 경고). 게이트웨이 기본 주소를 닫힌 포트로 돌리고 ste 위임은 끈다. 이 호출을 보는 시험은
# Settings 에 주소·비밀을 직접 주고 HTTP 대역을 건다(test_suspend_revokes_app_credentials).
os.environ.setdefault("MCP_GATEWAY_URL", "http://127.0.0.1:9")
os.environ.setdefault("STE_SSO_SECRET", "")
