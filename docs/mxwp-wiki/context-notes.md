# MX WhitePaper 완전 연결 · LLM 위키 — 결정과 까닭(포털 쪽)

> MXWP 쪽 결정은 MXWhitePaper `docs/llm-wiki/context-notes.md`(WK-D). 여기는 포털 · 게이트웨이 · 에이전트 서버에 걸린 것만 MW-D 번호로.

## 2026-10-24

- **MW-D1 요청서는 MXWP 리포에 둔다(정본), 포털에는 포털 몫만.** 까닭 — MXWP 는 사용자 자기 리포이고 그 리포의 VS Code 세션이 개발한다(DocForge 때와 같은 꼴 —
  `docs/doc-to-ra/`). 포털 세션이 읽는 곳에는 포털이 할 일만 있어야 같은 판단을 두 곳에서 다시 하지 않는다.
- **MW-D2 신원은 ste 방식 위임(일반 길 `PER_USER_SSO_APPS`)으로, 토큰 등록(`connect:`)이 아니다.** 까닭 — MXWP 는 같은 박스 · 같은 포털이 배포하는 앱이라
  비밀 하나로 끝난다. `connect:` 는 같은 키의 정적 백엔드(`mx-white-paper`)가 있으면 게이트웨이가 겹침으로 무시한다(`provision-config.sh` 의 '끄기' 안내문).
- **MW-D3 진입 토큰의 `access` 클레임은 시스템별로 켠다.** 까닭 — 소속 · 플랫폼 권한은 그것을 쓰는 앱에만 보낸다. 모든 jwt-handoff 시스템의 토큰을 한꺼번에
  바꾸면 쓰지도 않는 앱에 소속이 퍼진다.
- **MW-D4 `plat:` 전달은 소속 증명과 같은 서명 규칙으로, 앱별로 켠다.** 까닭 — 평문 헤더는 사용자가 앱 정문에 직접 붙어 스스로 적을 수 있다(게이트웨이
  `AFF_PROOF_HEADER` 주석의 논리 그대로). MXWP 위키는 PLM 결함 검색(`plat:plmdefect`)에서 온 사실을 그 권한이 있는 사람에게만 보여야 한다.
- **MW-D5 '위키에 남기기' 봉투는 포털 서버가 저장된 턴으로 짓는다.** 까닭 — 화면이 보낸 근거를 믿으면 사람이 근거를 꾸며 위키에 넣을 수 있다. 대화 저장소는
  주인만 읽으므로 그 사람 명의 요청 안에서만 짓는다.
- **MW-D6 대화를 일괄로 내보내지 않는다.** 위키로 가는 것은 주인이 보낸 턴 · 승인한 후보뿐(권장 B — MXWP request §11 Q1, 사용자 결정 대기).
- **MW-D7 비밀은 자동 생성하지 않는다(RA 때와 같은 까닭)** — MXWP 위임 창구가 준비되기 전에 비밀이 생기면 게이트웨이가 위임을 켜고 그 순간 MXWP 호출이
  거부로 바뀐다.

## 조사 근거(2026-10-24)

- 게이트웨이 `mx-white-paper` 백엔드 · REST 다리는 서비스 토큰(`HWAXMcpGateway/provision-config.sh` 98~130 · 490~493 · 534~536행 근처).
- 일반 위임 길 `PER_USER_SSO_APPS="<키>:<접두>"` → `<접두>_SSO_SECRET` · `<접두>_SSO_URL`(같은 파일 703~737행 근처) — 정적 백엔드는 키가 곧 위임 id
  (`gateway.py` `_delegation_app_id`).
- 게이트웨이 `/health` 에는 위임 목록이 없다 — provision 이 `✓ <키> 사람별 위임 — <주소>` 를 찍는다.
- 포털 진입 토큰 클레임 — `downstream.py` `JwtDownstreamIssuer.mint`(소속 · 플랫폼 없음).
- 시장불량 원천 후보 — `plm-defect`(cae00 게이트웨이에만, `access.yaml` `plmdefect` · 알려진 도구 `plm_case_detail` · `plm_similar_cases`) · SignalForge.
