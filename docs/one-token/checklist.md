# 체크리스트 — 토큰 하나 · REST→MCP

## 조사 (완료)
- [x] 현행 인증 표면 전수 실측 — 포털·게이트웨이·허브·앱 (워크플로 `wrkhltb78`)
- [x] OData 대상 유무 확인 → **0건** (범위 밖, PLAN §0)
- [x] 전달받은 처방 ①(`aud` 에 `apps` 추가)이 되는지 → **불가**(근거는 context-notes D-2)

## 발급 — 한 장이 넓게 덮는다
- [x] `pat_default_audiences` 에 REST 다리 사이트(ste·dyna-forge·step-forge) 추가
- [x] `TokenPage.tsx` 가 청중을 **안 보낸다**(서버 기본값을 그대로 받게)
- [x] `PatCreateBody.audiences` 를 선택 항목으로
- [x] 시험 — 청중 미지정 발급이 다중 청중을 싣는다 / 화면이 다시 박으면 깨진다
      (`backend/tests/test_pat_one_token.py`, 변이 2건 확인)

## REST 를 MCP 로 — 얇게 둘만
- [x] `rest_catalog` — 어떤 사이트의 어떤 REST 가 있는지(내 권한으로 보이는 것만)
- [x] `rest_call` — 그 경로를 내 명의로 부른다
- [x] 두 도구 설명에 **전용 MCP 가 먼저**임을 명시
- [x] 사이트가 0개면 두 도구를 아예 안 낸다(`_visible_tools`·`list_tool_apps` 같은 조건)
- [x] 시험 6건 + 변이 4건 (`HWAXMcpGateway/test_gateway.py`)

## 사이트 확장 — 본인 명의로 갈 수 있으면 그렇게 간다
- [x] `credential_mode()` 정본 하나(`rest_proxy.py`) — per_user > inject > none
- [x] `allowed_methods()` 정본 하나 — **쓰기의 기본은 닫힘**(per_user 이거나 명시일 때만 연다)
- [x] 열기 직전에 닫은 구멍 — `none` 모드가 제한 없음이었다(context-notes D-10)
- [x] REST 프록시(HTTP)·MCP 다리 **둘 다** per_user 를 탄다(`mint` 주입)
- [x] provision: `ste`·`dyna-forge`(per_user) / `step-forge`(주입·읽기전용)
- [x] `portal.audience_ok` 를 `rest` 키에서 유도(손으로 적은 목록의 어긋남 제거)
- [x] `access.yaml` 에 `step-forge`·`dyna-forge` 추가 (`ste` 는 이미 있음)
- [x] 시험 3건 + 변이 3건 (`HWAXMcpGateway/test_provision_urls.py`)

## 반영
- [x] dev: `provision-config.sh --force` → 사이트 6개 · `audience_ok` 6개 · `per_user_sso` 에 ste
- [x] dev: 게이트웨이 재기동 → `tools/list` **394개**(392 → +2), 두 도구 확인
- [x] dev 실호출 — ai-data-hub 200 · step-forge 200 / 쓰기 405 · 없는 사이트 · 신원 없음 (D-12 표)
- [x] 프론트 빌드 (`pnpm build`)
- [x] **ste 최신화 완료** — 대상이 dev VM(`ste-head01`)이라 여기서 됐다(D-13 이 D-12 를 정정).
      소스 20개 지문 일치 · openapi 30→32 · 프론트 일치 · ste 테스트 102 통과 · 원장 무손상
- [x] **update-all 이 앞으로 한다(2c)** — direct 는 다를 때만 자동, teleport 는 `STE_DEPLOY=1`
- [x] ste 자격 중계 E2E — 게이트웨이가 본인 명의 PAT 로 `/api/auth/me` 200(계정 JIT 생성)
- [x] §6 자격중계 게이트 초록(`401 + www-authenticate 없음` = 양쪽 설정됨)
- [ ] dev: 포털 PAT 한 장으로 `/mcp-gw/api/<site>/…` HTTP 경로도 통하는지 (MCP 경로만 확인했다)
- [ ] cae00: `update-all` (provision 이 새 사이트를 만들고, 2c 가 ste 를 판정한다 —
      운영 클러스터라 실배포는 `STE_DEPLOY=1` 을 줄 때만 돈다)

## 열기 전에 닫아야 할 것 (PLAN §3 — **미결**)
- [ ] **`scope`(read/write)가 아무 데서도 검증되지 않는다.** 지금은 한 장 = 전권이다
- [ ] 포털이 안 닿을 때 각 게이트가 어느 쪽으로 닫는지 확정
- [ ] 폐기 반영 시차를 숫자로 (게이트웨이 폐기목록 60초 · 연결캐시 300초 · 허브 캐시 없음)

## 결정 대기 (사용자)
- [ ] `/apps/*` 를 포털 PAT 로 열 것인가 (HEAXHub `authz.py` 에 JWKS 분기 — PLAN §5)
- [ ] 앱별 자격(`heax_pat_`·`kr_`·`ste_pat_`)을 없앨 것인가 남길 것인가
      — 권고는 **남긴다**(앱 단독 운영이 안 깨진다). 포털 PAT 는 그 위에 **추가로** 통한다
