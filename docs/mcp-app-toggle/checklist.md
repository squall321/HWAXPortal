# MCP 앱 켜고 끄기 — 체크리스트

## 1단계
- [x] 포털: `users.hub_muted_apps` 컬럼(가드된 ALTER) + 읽기·쓰기
- [x] 포털: `GET/PUT /auth/access/apps`(CSRF, 앱 키 검증, `_gateway` 제외) + PUT 뒤 게이트웨이 캐시 무효화
- [x] 포털: `/internal/access/entitlements` 에 `muted_apps`
- [x] 게이트웨이: PAT 분기에서 끈 앱 헤더 싣기(챗·절차 PAT 면제), 두 분기 모두 클라이언트 사본 버리기
- [x] 게이트웨이: `tools/list`·`search_tools`·`list_tool_apps`(muted_apps 칸)·`by='area'` 거르기, `use_experts` 표시
- [x] 게이트웨이: `/conn-invalidate` 가 그 사람 권한 캐시도 비운다 · 허브 지침에 끈 앱 안내
- [x] 포털 화면: 토큰 페이지 "허브에 보일 앱" 표 + 재연결 안내
- [x] 시험(게이트웨이·포털) + 변이 · 전체 시험
- [x] dev 실검증(스위치 → search_tools 에서 빠짐 → 켜면 돌아옴) · 프론트 빌드 + Drive 업로드(cae00 는 빌드 불가)
- [x] 커밋·푸시 · 적대적 검토

### 결과(2026-09-29)
- 시험: 게이트웨이 98(+7) · 포털 909(+9) · 변이 게이트웨이 5·포털 4 전부 사망.
- dev 실검증(같은 사용자의 개인 PAT): 평소 도구 425 → StepForge 끈 뒤 296(−129), search_tools·list_tool_apps 에서 빠지고
  muted_apps 에 나옴, invoke_tool 이름 호출은 됨 → 다시 켜면 425. 시험 PAT 는 폐기, 설정은 되돌림.
- 커밋: 게이트웨이 acd8c47 · 포털 2772955(백엔드)·8f4f248(화면)·8531673(문서). 포털 빌드 Drive 업로드(일치 확인).
