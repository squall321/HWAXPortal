# 박스 작업(update-all 훅 등)이 게이트웨이를 부르는 서비스 PAT 의 클레임 — 포털이 찍고 게이트웨이 _service_scope 가 같은 꼴로 가른다(docs/core-link design §2 · CK-4)
"""서비스 신원(docs/core-link SRC-13). 사람이 아니라 박스 작업 하나(`system:<작업>`)의 토큰이다. 게이트웨이는 박스 파일 service_tools.local.json
에 적힌 그 작업의 허용 목록만 부르게 한다(design §3) — 울타리는 그 목록이다. 그래서 이 토큰에는 사람 신원(email · name · groups)이 없다.

패널 PAT(app/agent/panel_pat.py)와 같은 모양 규칙을 따른다. 게이트웨이 판별이 보는 것(purpose · jti 머리 · 청중 · sub 꼴 · scopes)이 모두 여기 있고,
글자 하나라도 다르면 게이트웨이가 401 로 닫는다. 두 리포 계약 시험이 이 파일을 그대로 읽어 게이트웨이 판별에 넣어 본다 — 그래서 이 모듈은 표준
라이브러리만 쓴다(게이트웨이 시험 환경에서 따로 읽힌다).

청중을 따로 둔 까닭 — 포털 챗 · 토큰 교환(pat_chat_audience) · REST 프록시 · 그림 받기 · 이 판별을 모르는 옛 게이트웨이는 이 청중을 몰라 닫힌다.
실수로 다른 데 쓰여도 열리지 않는다(CK-4).
"""
import re
import uuid

SERVICE_AUDIENCE = "mcp-gateway-service"
SERVICE_PURPOSE = "service"
SERVICE_JTI_PREFIX = "svc-"
SERVICE_SUB_PREFIX = "system:"          # sub 는 "system:<작업>"
SERVICE_PAT_NAME_PREFIX = "service:"    # pat_name 은 "service:<작업>"
# 작업 이름. fullmatch 로만 본다 — match 의 $ 는 끝 줄바꿈 앞에서도 맞아 "core-link\n" 을 통과시킨다.
JOB_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
SERVICE_MIN_DAYS = 1
SERVICE_MAX_DAYS = 365                  # 0 · 무기한은 없다 — 만료와 회수(revoked.json) 둘 다로 죽는다


def service_claims(*, iss: str, job: str, now: int, days: int) -> dict:
    """서비스 PAT 클레임 — scope 는 api(게이트웨이 PAT 검증의 조건), scopes 는 service 하나(read 가 없어 읽기 전용 PAT 로 읽히지 않는다).
    email · name · groups 칸은 없다(사람 신원이 아니다). jti 는 매번 새것이다(폐기 목록으로 하나씩 막는다).

    job 이 JOB_RE 꼴이 아니거나 days 가 SERVICE_MIN_DAYS ~ SERVICE_MAX_DAYS 의 정수가 아니면 ValueError 다. 거절 글에 받은 값을 되싣지
    않는다 — 발급 화면이 그대로 보여 주는 글이다."""
    if not isinstance(job, str) or not JOB_RE.fullmatch(job):
        raise ValueError(f"job 은 {JOB_RE.pattern} 꼴이어야 한다 — 영소문자 · 숫자로 시작하고 영소문자 · 숫자 · - 만 40자까지")
    if isinstance(days, bool) or not isinstance(days, int) or not SERVICE_MIN_DAYS <= days <= SERVICE_MAX_DAYS:
        raise ValueError(f"days 는 {SERVICE_MIN_DAYS} ~ {SERVICE_MAX_DAYS} 의 정수여야 한다(무기한 없음)")
    now = int(now)
    return {
        "iss": iss, "sub": f"{SERVICE_SUB_PREFIX}{job}",
        "aud": [SERVICE_AUDIENCE], "scope": "api", "scopes": [SERVICE_PURPOSE],
        "pat_name": f"{SERVICE_PAT_NAME_PREFIX}{job}", "purpose": SERVICE_PURPOSE,
        "jti": f"{SERVICE_JTI_PREFIX}{uuid.uuid4().hex}",
        "iat": now, "nbf": now, "exp": now + days * 86400,
    }
