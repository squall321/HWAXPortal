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
#   · 연결 토큰 암호 키(HP-05) — 계정 원장을 열면 키가 없을 때 만든다. 그대로 두면 시험이 이 박스의 backend/secrets/conn.key 를 만든다.
#   · 상호작용 원장(docs/interaction-data) — 켠 박스의 backend/.env 를 읽은 시험이 기동하면 원장을 연다. 실 원장(/data/svc/portal 의 그 파일)에 시험 사건이 쌓인다.
for _key, _name in (("TOKEN_STORE_PATH", "token_store.sqlite"), ("CONV_STORE_PATH", "conversations.sqlite"),
                    ("PROCEDURES_STORE_PATH", "procedures.sqlite"), ("CONN_KEY_PATH", "conn.key"),
                    ("INTERACTIONS_STORE_PATH", "interactions.sqlite")):
    os.environ.setdefault(_key, os.path.join(tempfile.mkdtemp(prefix="hwax-test-store-"), _name))
# 상호작용 수집기(docs/interaction-data) — 시험이 포털을 띄울 때 켠 박스의 설정을 읽어도 백그라운드 수집이 이 박스에 떠 있는 게이트웨이를
# backend/.env 의 공유 비밀로 부르지 않게 끈다(창구 · 원장은 그대로 시험한다). 수집을 보는 시험은 run_once 에 Settings · HTTP 대역을 직접 준다.
os.environ.setdefault("INTERACTIONS_INGEST_S", "0")
# 사용자를 정지하면 앱 쪽 자격도 회수한다(8차 요청 §7 — 게이트웨이 `/conn-invalidate` · ste `/api/auth/sso/revoke`). 그대로 두면 시험이
# 사용자를 정지할 때마다 이 박스에 **떠 있는** 게이트웨이를 backend/.env 의 실제 공유 시크릿으로 부른다 — 시험은 공유 서비스를 치면
# 안 된다(test_procedures_routes 의 같은 경고). 게이트웨이 기본 주소를 닫힌 포트로 돌리고 ste 위임은 끈다. 이 호출을 보는 시험은
# Settings 에 주소·비밀을 직접 주고 HTTP 대역을 건다(test_suspend_revokes_app_credentials).
os.environ.setdefault("MCP_GATEWAY_URL", "http://127.0.0.1:9")
os.environ.setdefault("STE_SSO_SECRET", "")
# LLM/GPU 현황 수집기(docs/ops-dashboard) — 시험이 이 박스의 수집기 저장소(infra/.state/llm-status)에 쓰거나, 실제 infra/.env 의 키를 읽어 실 LLM
# 서버를 두드리지 않게. 수집기는 이 둘을 환경에서 먼저 본다(collector.py). 무엇을 여는지는 test_suite_isolation 이 수집기의 기본 자리를 열어 본다.
os.environ.setdefault("LLM_STATUS_STATE_DIR", tempfile.mkdtemp(prefix="hwax-test-llm-status-"))
os.environ.setdefault("LLM_STATUS_ENV_FILE", os.path.join(tempfile.mkdtemp(prefix="hwax-test-llm-status-env-"), "infra.env"))
# 포털 관리자 화면(LLM · GPU 현황)은 떠 있는 수집기를 부르지 않게 주소를 비운다(꺼짐 — 그 창구를 보는 시험은 Settings 에 주소를 직접 주고 HTTP 대역을 건다).
os.environ.setdefault("LLM_STATUS_URL", "")
# 과제 인사이트(docs/project-insight-graph M2) — 인사이트 읽기 창구가 이 박스에 떠 있는 에이전트 서버(backend/.env 의 공유 비밀 · 주소)에서 MCP 잡 카드를
# 당기지 않게 끈다. 당기기를 보는 시험은 Settings 에 간격 · 주소 · 비밀을 직접 주고 HTTP 대역을 건다(tests/test_insights.py).
os.environ.setdefault("INSIGHT_SYNC_S", "0")
# 심의 묶음 끝남 알림(docs/request-1117 contracts §7) — 시험이 포털을 띄울 때마다(lifespan) 백그라운드 당기기가 이 박스에 떠 있는 에이전트 서버를
# backend/.env 의 공유 비밀로 부르지 않게 끈다. 당기기를 보는 시험은 tick 에 Settings · 가짜 엔진을 직접 준다(tests/test_notice_poller.py).
os.environ.setdefault("DELIB_BATCH_NOTICE_S", "0")
# 이용 통계의 날마다 접기(docs/ops-dashboard M2) — 시험이 포털을 띄울 때마다(lifespan) 백그라운드 접기가 이 박스에 떠 있는 게이트웨이 · 에이전트 서버를
# backend/.env 의 공유 비밀로 부르거나 이 박스의 정문 로그(infra/data/nginx-access.log)를 읽지 않게 끈다. 접기를 보는 시험은 run_once 에 Settings · HTTP
# 대역을 직접 준다(tests/test_usage_fold.py). 접는 표는 감사 원장 파일 안이라 위 AGENT_AUDIT_LOG_PATH 격리가 그대로 덮는다(새 경로 설정이 없다).
os.environ.setdefault("USAGE_FOLD_S", "0")
# 자동 파이프라인(docs/auto-pipeline) — 시험이 포털을 띄울 때 켠 박스의 backend/.env 를 읽어도 박자 작업이 이 박스에 떠 있는 게이트웨이를 서비스 토큰으로
# 부르지 않게 끈다(원장은 위 PROCEDURES_STORE_PATH 격리가 덮는다 — 새 경로 설정이 없다). 박자를 보는 시험은 Engine.tick 에 가짜 게이트웨이를 직접 준다.
os.environ.setdefault("AUTO_PIPELINE_TICK_S", "0")
# HE팀 운영자 박스 덧씌우기(docs/he-team-overlay) — 시험이 이 박스의 infra/personas/he-team.local.json 을 읽어 정본 시험 · 접근 검사 판정이
# 박스마다 달라지지 않게, 없는 자리로 돌린다. 덧씌우기를 보는 시험은 경로를 직접 준다(tests/test_he_team_overlay.py).
os.environ.setdefault("HE_TEAM_LOCAL_PATH", os.path.join(tempfile.mkdtemp(prefix="hwax-test-he-team-"), "he-team.local.json"))
