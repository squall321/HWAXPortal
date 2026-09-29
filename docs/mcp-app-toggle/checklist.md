# MCP 앱 켜고 끄기 — 체크리스트

## 1단계
- [ ] 포털: `users.hub_muted_apps` 컬럼(가드된 ALTER) + 읽기·쓰기
- [ ] 포털: `GET/PUT /auth/access/apps`(CSRF, 앱 키 검증, `_gateway` 제외) + PUT 뒤 게이트웨이 캐시 무효화
- [ ] 포털: `/internal/access/entitlements` 에 `muted_apps`
- [ ] 게이트웨이: PAT 분기에서 끈 앱 헤더 싣기(챗·절차 PAT 면제), 두 분기 모두 클라이언트 사본 버리기
- [ ] 게이트웨이: `tools/list`·`search_tools`·`list_tool_apps`(muted_apps 칸)·`by='area'` 거르기, `use_experts` 표시
- [ ] 게이트웨이: `/conn-invalidate` 가 그 사람 권한 캐시도 비운다 · 허브 지침에 끈 앱 안내
- [ ] 포털 화면: 토큰 페이지 "허브에 보일 앱" 표 + 재연결 안내
- [ ] 시험(게이트웨이·포털) + 변이 · 전체 시험
- [ ] dev 실검증(스위치 → search_tools 에서 빠짐 → 켜면 돌아옴) · 프론트 빌드 + Drive 업로드(cae00 는 빌드 불가)
- [ ] 커밋·푸시 · 적대적 검토
