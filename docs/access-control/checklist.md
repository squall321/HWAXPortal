# 소속·허가 기반 접근 — 체크리스트

체크는 **실제로 확인한 것**만 한다.

## A. 정책·계산 (포털 백엔드)

- [ ] `backend/config/access.yaml` — 기능·플랫폼 표(포털 타일·게이트웨이 백엔드), 소속별 기본 허가(CAEG=전부), 기본 허가(일반 챗)
- [ ] 정책 로더 + 대조 테스트(타일·게이트웨이 백엔드·HE팀 앱이 전부 어느 플랫폼에 속하는지)
- [ ] users 에 affiliation·grants 칸, 허가 요청 표
- [ ] 유효 권한 계산(소속 ∪ 개별 ∪ 기본 ∪ 함의, 관리자=전부) — 요청마다, 합성 그룹(feat:·plat:)으로 principal.groups 에
- [ ] `/auth/me` 에 affiliation·entitlements

## B. 관리·요청

- [ ] 관리자 API — 사용자 소속·개별 허가 편집, 요청 승인·거절
- [ ] 사용자 API — 내 권한 표(허가 여부·이유·요청 상태), 요청 보내기

## C. 포털 강제

- [ ] /agent/chat — thinking·pinned_agent·delib_opts·검색 소스, 에이전트서버에 entitlements 전달
- [ ] /agent/deliberate/*·/agent/catalog/*·업로드·PAT 발급·/systems 타일·launch

## D. 에이전트서버

- [ ] ChatRequest.entitlements — 심의 계열 트리거·Thinking·전문가 지정 막기(방어 심층)

## E. 게이트웨이

- [ ] 포털 정책(백엔드별 필요 권한) 가져오기·캐시
- [ ] PAT 호출자의 권한을 요청 시점 값으로(PAT 에 박힌 그룹 대신)

## F. 프론트

- [ ] User 타입·can() — 창에 돌아오면 /auth/me 다시
- [ ] 메뉴·라우트 숨김(심의·API 토큰·리스크), 입구 숨김(슬래시 명령·넘기기·Thinking·조직도·업로드·웹 검색)
- [ ] 내 권한 페이지 — 표·요청
- [ ] 관리자 화면 — 소속·개별 허가·요청 큐

## G. 검증

- [ ] dev 에서 CAEG 밖 테스트 계정으로 — 메뉴 숨김·API 거절·MCP 도구 차단 → 허가 → 보임
- [ ] 문서·체인지로그·cae00 배포 안내(기존 사용자 소속 지정)
