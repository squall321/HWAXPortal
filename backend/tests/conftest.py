# 시험이 운영 감사 원장(/data 의 agent_audit.sqlite)에 쓰지 않게 — 포털 기동(lifespan)이 get_settings() 로 경로를 읽는다
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
