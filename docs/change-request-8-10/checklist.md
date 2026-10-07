# 8·9·10차 변경 요청 — 체크리스트

## 게이트웨이(HWAXMcpGateway)
- [x] #2 NO_PROXY 유도
- [x] #17 재연결 재시도 신원
- [x] #6 하위로 넘기는 그룹에서 portal-admin 빼기(`is_admin` 일 때만)
- [x] #8 `PER_USER_SSO_APPS`
- [x] #10 `ARP_TOKEN` · 조건부 등재
- [x] #11 smart-twin-mcp 조건부 등재
- [x] #20 `tool_areas.json`(한 커밋)

## 포털 — 신원·권한·카탈로그
- [x] #16 `dept_id` 칸
- [x] #1 Claim → 소속 매핑 · 기본 소속 · 「소속 미지정만 보기」
- [x] #15 사번 정지 검사
- [x] #5 `PORTAL_ADMIN_EMAILS` · 관리자 지정·해제
- [x] #6 관리자는 원장만 · 발급 때 빼기 · 해제 때 폐기 · `is_admin` 응답
- [x] #14 정지 시 앱 토큰 회수
- [x] #7 `access.local.yaml`
- [x] #13 `systems.local.yaml` 새 타일
- [x] 7-3·7-4·7-5 ARP 타일(한 커밋)

## 포털 — 인프라 스크립트
- [x] #3 start.sh `NO_PROXY`
- [x] 7-2 nginx arm
- [x] 7-6·7-7 update-all §1f · 시험
- [x] #9 knox-bridge 기대
- [x] #10 arp 기대 조건
- [x] #11 smart-twin-mcp 기대 조건
- [x] #12 NO_PROXY 유도
- [x] #19 check-egress

## 게이트웨이 뒤처리(구현 단위가 남긴 것)
- [x] 포털 update-all 이 `PER_USER_SSO_APPS`·`<접두>_SSO_*` 를 provision 에 넘긴다(#8 짝)
- [ ] 엔진 `_AREA_HINT` 에 `quality`(#20 짝)
- [ ] `provision-config.sh` 의 ODB 허브 기본 주소(사내 IP 가 추적 파일에 박혀 있다 — 종전부터) 걷기

## 검증·반영(심의 엔진 변경과 함께)
- [x] 반박 검토 → 확정분 수정 → 전체 시험(D-13)
- [ ] dev 선행 — `provision.env` 에 `SMARTTWIN_MCP_URL` · `infra/.env` 에 `PORTAL_ADMIN_EMAILS`
- [ ] push · 빌드 · Drive · dev 재기동 · `/health/ready` 에 `no_active_admin` 없음
- [ ] 업데이트 이력 · CLAUDE.md 표
