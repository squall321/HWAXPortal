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

## 반영 (남음 — 사람 손)
- [ ] dev: `./provision-config.sh --force` → 게이트웨이 재기동 → `tools/list` 로 394개 확인
- [ ] dev: 새 PAT 한 장으로 `rest_catalog` → `rest_call` 실호출 (ste·dyna-forge·step-forge)
- [ ] 프론트 빌드 배포 (`pnpm build` → SPA dist)
- [ ] cae00: `update-all` (provision 이 새 사이트를 만든다)

## 열기 전에 닫아야 할 것 (PLAN §3 — **미결**)
- [ ] **`scope`(read/write)가 아무 데서도 검증되지 않는다.** 지금은 한 장 = 전권이다
- [ ] 포털이 안 닿을 때 각 게이트가 어느 쪽으로 닫는지 확정
- [ ] 폐기 반영 시차를 숫자로 (게이트웨이 폐기목록 60초 · 연결캐시 300초 · 허브 캐시 없음)

## 결정 대기 (사용자)
- [ ] `/apps/*` 를 포털 PAT 로 열 것인가 (HEAXHub `authz.py` 에 JWKS 분기 — PLAN §5)
- [ ] 앱별 자격(`heax_pat_`·`kr_`·`ste_pat_`)을 없앨 것인가 남길 것인가
      — 권고는 **남긴다**(앱 단독 운영이 안 깨진다). 포털 PAT 는 그 위에 **추가로** 통한다
