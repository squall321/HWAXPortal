# 패널 세션 하나의 짧은 PAT(그 앱 · 그 ui:// 주소 · 15분) 클레임 — 포털이 찍고 게이트웨이가 같은 꼴로 가른다(docs/request-1027 HA-20 · HP-42)
"""포털 챗의 MCP Apps 패널(설계 docs/request-1027/design-ha09-ha20.md B5.3 · B5.4). 패널의 tools/call · resources/read 는 포털 백엔드가 받아
이 토큰으로 게이트웨이에 보낸다 — 챗 PAT 로 보내면 감사가 chat 으로 남고 포털 결함이 곧 챗 권한 전부가 된다(B4 (가)).

게이트웨이 판별(HWAXMcpGateway gateway.py `_panel_scope`)이 보는 넷이 여기 있다 — purpose · jti 머리 · 청중 · panel 칸. 글자 하나라도 다르면
게이트웨이가 401 로 닫는다(일반 PAT 로 받지 않는다). 두 리포 계약 시험이 이 파일을 그대로 읽어 게이트웨이 판별에 넣어 본다 — 그래서 이 모듈은
표준 라이브러리만 쓴다(게이트웨이 시험 환경에서 따로 읽힌다).

청중을 MCP 청중(pat_chat_audience)과 따로 둔 까닭 — 이 판별을 모르는 옛 게이트웨이와 만나면 청중이 맞지 않아 닫힌다. 같은 청중이면 옛
게이트웨이가 패널 PAT 를 그 사람의 일반 PAT 로 받아 패널이 그 사람이 부를 수 있는 도구 전부를 부른다.
"""
import uuid

PANEL_PURPOSE = "mcp-app"
PANEL_JTI_PREFIX = "mcpapp-"
PANEL_AUDIENCE = "mcp-app-panel"
PANEL_PAT_NAME = "mcp-app"
PANEL_TTL_S = 900          # 15분 — 패널 세션이 이어지는 동안 포털이 다시 찍는다(유휴 30분 · 최대 4시간은 패널 세션의 몫)


def panel_claims(*, iss: str, sub: str, email: str, name: str | None, groups: list[str], app: str, uri: str, now: int,
                 audience: str = PANEL_AUDIENCE, ttl_s: int = PANEL_TTL_S) -> dict:
    """패널 PAT 클레임 — scope 는 api(게이트웨이 PAT 검증의 조건), scopes 는 mcp-app 하나(읽기 전용 PAT 로 읽히지 않는다), 권한 키는 싣지 않는다
    (로그인 그룹만 — 게이트웨이가 포털의 지금 권한으로 붙인다). jti 는 매번 새것이다(폐기 목록으로 하나씩 막을 수 있다)."""
    return {
        "iss": iss, "sub": sub, "email": email, "name": name, "groups": list(groups),
        "aud": [audience], "scope": "api", "scopes": [PANEL_PURPOSE], "pat_name": PANEL_PAT_NAME,
        "purpose": PANEL_PURPOSE, "panel": {"app": app, "uri": uri},
        "iat": int(now), "nbf": int(now), "exp": int(now) + int(ttl_s),
        "jti": f"{PANEL_JTI_PREFIX}{uuid.uuid4().hex}",
    }
