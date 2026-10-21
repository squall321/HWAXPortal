# 외부 연결을 설정만으로 — 계획 (2026-10-21)

> 요청서 [request.md](request.md)(사양 — `파일:줄` · 칸 표 · 시험 목록은 거기에 있다) · 체크리스트 [checklist.md](checklist.md) ·
> 결정 [context-notes.md](context-notes.md). 앞선 맥락은 [sso-delegation](../sso-delegation/PLAN.md)(RA · TestScope 토큰 등록 · 10-20 MatNexus 표준 위임).

## 1. 무엇 · 왜

포털 '개인 토큰 › 외부 연결'(`/tokens?tab=connect`)이 RA · TestScope 두 장만 받는다 — 포털 `SERVICES`, 화면의 카드 두 장, 게이트웨이
`PORTAL_CONN_BACKENDS` 가 코드에 박혀 있어 플랫폼이 하나 늘 때마다 두 리포 코드와 화면 빌드가 든다. 이번 한 번 공통 기능을 넣어, 다음
플랫폼부터는 **박스 권한표(`access.local.yaml`)의 그 플랫폼 항목에 `connect:` 블록 하나**로 붙게 한다(빌드 · 코드 · 재기동 0).
첫 대상은 FMEA Agent · MatNexus.

사용자 결정(10-21) 셋 — ① 토큰 등록 방식(사람이 그쪽에서 받은 제 토큰을 등록하고 게이트웨이는 그 토큰으로만 부른다 — 10-20 의 MatNexus
표준 위임은 쓰지 않는다) ② 새 플랫폼은 토큰 주인을 확인하지 않는다(필요한 플랫폼만 설정으로 켠다) ③ 플랫폼이 늘어도 빌드가 필요 없다.

## 2. 범위

하는 것 — 요청서 1-3 의 고칠 곳 전부.

| 묶음 | 리포 | 항목 |
|---|---|---|
| E1 포털 백엔드 | HWAXPortal | PB1 ~ PB13(+ PB14 선택) — `connect:` 파싱(박스 파일에서만) · 정책 응답에 `connections` · `/auth/connections/ext`(목록 · 등록 · 해제, 등록은 세션 + CSRF 만) · 내부 조회가 선언 키를 받는다 · 합성 권한 `feat:connect` |
| E2 게이트웨이 | HWAXMcpGateway | GW1 ~ GW20 — 선언을 정책과 한 응답으로 받아 백엔드를 스스로 붙이고 뗀다(목록 전용 세션 · 사람 토큰으로만 호출 · 닫힌 쪽 권한 · 이름 겹침은 선언 쪽만 접두 · 읽기 도구 · 감사 지문 · `/health` 상태) |
| E3 포털 화면 | HWAXPortal | PF1 ~ PF5 — 설정으로 그리는 카드 하나(`ExternalConnectionCards`) · `/tokens` 문에 `feat:connect` |
| E4 운영 스크립트 | HWAXPortal `infra/` | PX1 · PX2 — 스모크가 선언 백엔드를 신원 없이 부르지 않는다 · 다운 알림 |
| E5 문서 | 두 리포 | D1 ~ D6 · 게이트웨이 README(GW20) · 업데이트 이력 · CLAUDE.md |

하지 않는 것 — cae00 반영(요청서 4절, 운영 쪽 — 요청 아님) · FMEA 에 청할 것(3절) · 남은 질문 1-9 의 결정(설계의 기본값으로 구현하고
결정은 사람에게 남긴다 — context-notes EC-D2) · RA · TestScope 를 `connect` 꼴로 옮기기(1-9 ⑩) · 등록 토큰 암호화(1-9 ③ — 알리기만).

## 3. 걸음

| # | 무엇 | 끝의 판정 |
|---|---|---|
| E1 | 포털 백엔드 | 새 시험(파싱 · 목록 · 등록 · 해제 · 내부 조회 · 합성 권한) + 포털 전체 시험 · 호환(TestScope · RA · 권한 시험을 고치지 않고 통과) |
| E2 | 게이트웨이 | 새 시험(선언 → 백엔드 · 호출 헤더 · 목록 전용 · 신원 없음 · 충돌 · 권한 닫힘 · 이름 겹침 · 읽기 도구 · 캐시 · 감사 · 동시성 · 부팅 캐시 · `/health`) + 게이트웨이 전체 시험 · RA · TestScope 묶음 회귀 |
| E3 | 포털 화면 | `tsc` · `pnpm build` · 화면 시험 · `/tokens?tab=connect` 캡처 |
| E4 | 운영 스크립트 | `test_update_all_health_gate.py` 에 선언 백엔드 꼴 |
| E5 | 문서 | 이력 시험 · 내부 IP 가드 |

리포마다 끝난 것부터 올린다. 화면은 커밋 **뒤** 빌드해 Drive 에 올린다(`build-all-to-drive.sh portal` — cae00 은 빌드를 못 한다).

## 4. 반영 순서(운영 — 요청서 4절)

dev push · 화면 Drive → cae00 포털 update-all → cae00 게이트웨이 리포를 새 판으로 · 재기동(한가할 때) → 박스 권한표에 `connect:`(요청서 1-7) →
권한 승인 → 사람이 토큰 등록. 재기동이 드는 단계는 심의 · 다른 작업이 없는 때에 운영 담당이 정한다.
