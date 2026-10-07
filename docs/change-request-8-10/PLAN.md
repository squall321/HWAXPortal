# 8·9·10차 변경 요청 반영 — 아직 반영되지 않은 요청 총정리(판 1)

> 2026-10-08 요청서(요청자 koo.park, 기준 포털 `614a764` · 게이트웨이 `dd8d604`). 1~10차 요청서 · UPSTREAM-ASKS · ARP·ODB 작업지시
> 가운데 미반영분만 모은 문서다 — 소스 요청 20건(#1~#20)과 질문 1건(#21). 줄번호는 원 요청서가 아니라 이 총정리를 따른다.
> 받은 본문이 5만 자에서 잘려 부록 B(9차 §4·§5·§6 원문)는 뒤늦게 왔다 — #2·#3·#12·#19 는 본문 서술로 먼저 구현하고 검토 단계에서 원문과 대조한다(D-9).
> 심의 엔진 요청서(24건)는 따로 진행 중이다 — `docs/delib-engine-feedback/`. 겹치는 것은 #1 하나다(D-2).

## 반영 표

| # | 무엇 | 어디 | 방침 |
|---|---|---|---|
| 1 | SSO 신규 가입자 소속 — Claim → 소속 매핑(ⓑ) · 기본 소속(ⓐ) · 「소속 미지정만 보기」(ⓒ) | 포털 `user_store.py`·`session.py`·`config.py`·`AccessAdmin`·`UsersAdminPage` | 엔진 요청 4-3 을 이것으로 대체(D-2) |
| 2 | 게이트웨이가 자기 백엔드 주소에서 `NO_PROXY` 유도 | 게이트웨이 `gateway.py` | D-8 |
| 3 | 포털 컨테이너에 `NO_PROXY` 명시 전달 | 포털 `infra/scripts/start.sh` | 요청대로 두 줄 |
| 4 | ARP·ODB 라우트 — 7-2 nginx arm · 7-3·7-4·7-5 타일 개명+핸드오프 · 7-6·7-7 update-all §1f | 포털 | 7-1 안 함 · 7-8 보류(D-6) |
| 5 | 언제나 관리자(`PORTAL_ADMIN_EMAILS`) + 관리자 지정·해제 화면 | 포털 `policy.py`·`access/routes.py`·`UsersAdminPage` | 요청대로 |
| 6 | 관리자 판정은 원장만 — 토큰에 박힌 표지 무력화 · 발급 때 빼기 · 해제 때 폐기 | 포털 `policy.py`·`pat.py` · 게이트웨이 `gateway.py` | D-3 |
| 7 | `access.local.yaml` 오버레이 | 포털 `policy.py` + 시험 4곳 | 요청대로 |
| 8 | `per_user_sso` 일반 순회(`PER_USER_SSO_APPS`) | 게이트웨이 `provision-config.sh` | 요청대로 |
| 9 | update-all 이 Knox 브리지를 기대 | 포털 `update-all.sh` | 요청대로 |
| 10 | `arp` 자격증명 자리 + 조건부 등재 / 기대 조건 | 게이트웨이 `provision-config.sh` · 포털 `update-all.sh` | 두 리포 같은 배포(D-5) |
| 11 | `smart-twin-mcp` 조건부 등재 | 게이트웨이 `provision-config.sh` · 포털 `update-all.sh` 기대 | D-4 |
| 12 | update-all 에서 내부 목적지 `NO_PROXY` 유도(`RA_HOST`·`ARP_HOST`) | 포털 `update-all.sh` | 본문 서술대로(D-9) |
| 13 | `systems.local.yaml` 로 새 타일(external-url 만) | 포털 `catalog/registry.py` | 요청대로, #7 과 함께 |
| 14 | 정지 시 앱 토큰 회수(ste revoke · RA 캐시 · 게이트웨이 `/conn-invalidate`) | 포털 `auth/routes/local.py` | 요청대로, best-effort |
| 15 | 정지를 사번으로도 검사 | 포털 `user_store.py`·`session.py`·`config.py` | 사번만(기본 꺼짐) — 제목의 LoginId 는 넣지 않았다(D-11) |
| 16 | `DeptId` 별도 칸 | 포털 `user_store.py`·`session.py`·`config.py` | 요청대로(기본 꺼짐) |
| 17 | 재연결 재시도가 신원을 빠뜨림 | 게이트웨이 `gateway.py` | 요청대로 |
| 18 | `services.yaml` `env:` 값 보간 | — | 하지 않는다 — #2 가 들어가 불필요(요청서 판단 그대로) |
| 19 | `check-egress.sh` 대상 확장 + update-all §6 에 연결 · `NO_PROXY` 의 CIDR 경고 | 포털 | D-9 |
| 20 | `tool_areas.json` — `quality` 영역 · `plm-defect` · `knox-bridge` | 게이트웨이 | **한 커밋** |
| 21 | (질문) 위임 경로의 `X-Workspace-Slug` | — | 지금은 그대로, RA 홈 부서 보장 확인 뒤 포털도 뺀다(D-7) |

## 순서

게이트웨이는 포털과 리포가 달라 먼저 돈다(`gateway.py` → `provision-config.sh`·`tool_areas.json`). 포털은 심의 엔진 작업의 포털 몫이 끝난 뒤
두 갈래로 간다 — 신원·권한·카탈로그(#16·#1·#15 → #5·#6·#14 → #7·#13·7-3~7-5)와 인프라 스크립트(#3·7-2·7-6·7-7·#9·#10·#11·#12·#19).
그다음 심의 엔진 변경과 **한꺼번에** 반박 검토 → 재현된 것만 수정 → 리포별 전체 시험.

## 같이 나가야 하는 것

- #10 — 게이트웨이(조건부 등재)와 포털(기대 조건)이 같은 배포. 한쪽만 나가면 update-all 이 매번 재프로비저닝을 헛돌린다.
- #6 — 포털 응답의 `is_admin` 과 게이트웨이가 그것을 읽는 쪽.
- 7-3·7-4·7-5 — 한 커밋(하나라도 빠지면 `test_access_control` 이 깨진다). 7-5 는 프론트 빌드 + Drive 가 있어야 반영된다.
- #20 — 한 커밋. 따로 나가면 cae00 의 `pull --ff-only` 가 멈춘다.

## 반영 뒤 박스에서 할 일(요청자)

- 7-3 이 들어오면 타일 클릭이 ARP 콜백으로 토큰을 보낸다 — ARP 의 JWKS·AUDIENCE 설정 시각과 맞춘다. `systems.local.yaml` 의 `arp:` 직결 오버레이를 지운다.
- `ARP_TOKEN`(게이트웨이 `provision.env`) — 없으면 arp 백엔드만 빠진다.
- `smart-twin-mcp` 를 쓰는 박스는 **첫 재프로비저닝 전에** `provision.env` 에 `SMARTTWIN_MCP_URL` 을 적는다(D-4). 안 적으면 그 재프로비저닝에서 도구가 빠진다.
- 관리자를 IdP 그룹으로 받던 박스(mock·oidc)는 포털 재기동 전에 `PORTAL_ADMIN_EMAILS` 를 적거나 원장에 관리자가 있는지 본다. 반영 뒤 `/health/ready` 의 `temporary` 에 `no_active_admin` 이 없어야 한다.
- 게이트웨이 설정에 `allowed_groups` 로 `portal-admin` 을 거는 백엔드가 없는지 반영 전에 한 번 본다(D-10).
- 첫 update-all 은 옛 arp·smart-twin 항목을 걷느라 한 번 재프로비저닝한다(게이트웨이·에이전트서버가 한 번 다시 뜬다).
- cae00 게이트웨이 작업트리의 `tool_areas.json` 수정은 pull 전에 걷는다(#20).
