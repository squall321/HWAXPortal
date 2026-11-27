# 사내 MCP 앱 주인에게 건넬 요청서

> 계획 [../PLAN.md](../PLAN.md) M5 · 공통 계약 [../contract.md](../contract.md) · 근거 [../audit/onprem.md](../audit/onprem.md)(2절 목록 · 3절 품질 · 5-4 받는 곳) ·
> 운영 박스 점검 [../cae00-7th-section.md](../cae00-7th-section.md)(MQ-1 품질 카드). 처음 쓴 날 2026-11-27.

## 무엇 · 누가 건네나

- 게이트웨이에 붙은 사내 앱(운영 박스에만 있는 백엔드 약 1,200 도구)마다 한 장이다. 같은 주인이면 한 장으로 묶었다(MatNexus · TestScope, 데이터허브 다섯).
- 요청서마다 머리(무엇 · 왜) · 그 앱에 대해 알려진 숫자와 결함 · 공통 계약 가운데 그 앱에 특히 해당하는 것과 차례 · 프로토콜(stateless · 두 세대) · 로드맵(R1 ~ R3) ·
  이미 보낸 요청과 잇기 · 답하는 꼴을 둔다.
- **건네는 것은 사용자다**(PLAN 5절). 늘 [../contract.md](../contract.md) 와 함께 건넨다. 11-24 요청 모음(`../../request-1125/request.md` 3절)과 받는 곳이 같으면
  그 묶음과 함께 건네도 된다 — 요청서마다 잇는 번호를 적었고, 같은 내용을 다시 쓰지 않았다.
- 「이 박스 카드로 잼」 칸 — 운영 박스의 품질 카드(MQ-1)가 오면 dev 가 그 앱의 줄(표지 · 인자 설명 · 설명 길이 · 지연 · 실패)로 채운다. 카드 전에 건네도 된다 — 그 칸은
  「다음에 숫자를 보낸다」 로 둔다.
- 이 리포는 공개다 — 요청서에 실제 주소 · 계정 · 토큰 · 사람 이름 · 과제 이름을 적지 않았다. 앱 이름 · 도구 이름 · 수는 리포 문서에 이미 있는 만큼만 썼다.

## 목록

건넨 날 · 답 받음 칸은 건네고 답을 받을 때 채운다. 답은 [../context-notes.md](../context-notes.md) 에 옮기고, 이 표에는 날짜와 옮긴 곳만 적는다.

| 받는 곳 | 파일 | 함께 볼 것 | 건넨 날 | 답 받음 |
|---|---|---|---|---|
| StandardPlatform(틀 — Datahub 플랫폼 담당) · 허브 관리자 넷 | [sp-hubs.md](sp-hubs.md) | 표지 요청 `../../sp-latest/sp-annotations-request.md` · 1125 3-5 · 3-15 ~ 3-17 · 3-19 | | |
| ComponentCore 담당 | [componentcore.md](componentcore.md) | 1125 3-11 | | |
| MatNexus · TestScope 팀 | [matnexus-testscope.md](matnexus-testscope.md) | 1125 3-13 · 3-18 | | |
| ODB 허브 담당 | [odb-hub.md](odb-hub.md) | `../../design-risk-review/ecad-1031/odb-hub-request.md` · 1125 3-6 | | |
| ARP 담당 | [arp.md](arp.md) | 1125 3-7 | | |
| FMEA 담당 | [fmea.md](fmea.md) | `../../sso-delegation/fmea-request.md` · 1125 3-8 | | |
| SIREN 팀 | [siren.md](siren.md) — **보내기 전 사용자 결정**(19-SIREN 묶음 보류와 겹친다) | 1125 3-14 · 4절 R-1 ~ R-8 | | |
| SimFlow 담당 | [simflow.md](simflow.md) | 1125 3-4 | | |
| SimEngBay 담당 | [simengbay.md](simengbay.md) | 1125 3-20 | | |
| CircuitTrace(운영 쪽 앱) | [circuittrace.md](circuittrace.md) | 1125 1-2 CT-01 · 부록 A CTO-1 ~ 3 | | |
| 개발실 체크리스트 — 중계 MCP(운영 쪽) · 원 서버(PCB 체크리스트 담당) | [devlab-checklist.md](devlab-checklist.md) | 1125 3-3 · `../../request-1111/request.md` HG-30 | | |
| PLM 검색 에이전트 담당 | [plm-search-agent.md](plm-search-agent.md) | 1125 3-9 · 4절 PL-03 · PL-10(보류) | | |
| PLM 결함 검색(주인 모름) | [plm-defect.md](plm-defect.md) — 주인 확인부터 | `../../mxwp-wiki/` W8 | | |

## 요청서를 두지 않은 것

| 무엇 | 까닭 |
|---|---|
| SmartTwin MCP(stcx 356대) | 사내 쪽 서비스지만 코드가 dev 의 KooSlurm 세션에 있다 — 1단계를 그 세션에 이미 청했다(checklist M1). 계약 · 표지(SM-02)도 그 세션 몫 |
| 리포트 아카이브 | dev 에도 붙어 있고 RA 세션이 맡는다(1단계 로컬 커밋 · 아홉 항목 답 받음 — checklist M1) |
| knox-bridge · smart-twin-cluster | 주인 · 도구 수 · 쓰임을 모른다. MQ-1 카드의 앱 줄이 오면 다시 본다 |
| 35번째 백엔드 | 무엇인지 모른다(audit/onprem 1-2). MQ-1 카드로 이름이 나오면 다시 본다 |

## 요청서에 넣지 않은 것 — 사용자 결정이 먼저

1125 요청 모음 4절이 「사용자 결정이 먼저(보내지 않음)」 로 둔 것은 이 요청서들에도 싣지 않았다. 결정이 나면 그 앱 요청서에 덧붙인다.

- SIREN — 19-SIREN 묶음 R-1 ~ R-8(표지 · 토큰 확인 · 동시 한도 · 오류 꼴 · 사양 차이 · 신뢰 규칙 · 인자 설명). 그래서 [siren.md](siren.md) 는 통째로 「보내기 전 사용자 결정」 이다.
- PLM 검색 에이전트 — PL-03 · PL-10(검색 결과 · 챗 응답의 개인정보 가림 범위).
- TestScope — PA-03(사람별 위임 켜기 마지막 단계 — SSO 전환 대기).

## 공통 계약 항목과 게이트웨이가 재는 칸

요청서의 「카드 칸」 열은 이 표의 칸이다. 앱 쪽은 판(커밋 · 판 번호)만 알리면 되고, 수는 게이트웨이 품질 카드(`HWAXMcpGateway/mcp_quality_card.py`)가 잰다.

| 항목 | 카드 칸 | 목표 |
|---|---|---|
| C1 설명의 꼴 | `desc_gt1000` · `desc_lt100` · `desc_history` · `desc_shared_other_app` · `desc_p95` | 넘치는 것 · 이력 섞임 0 |
| C2 인자 설명 | `arg_described_ratio` · `nested_described_ratio` | 1.0(게이트웨이 점수판은 0.3 미만을 「부족」 으로 적는다) |
| C3 enum | `enum_args` | 닫힌 어휘 인자 전부 |
| C4 숫자 경계 | `numeric_bounded_ratio` | limit · page · 개수 · 비율 전부 |
| C5 구조 있는 객체 | `free_objects` | 0, 또는 설명에 키 예시 |
| C6 읽기 · 쓰기 표지 | `ro_annotated_ratio` · `ro_none` · `destructive` | 1.0 · 0 |
| C7 결과 꼴 | `output_schema_real` | 구조 있는 결과 전부 |
| C8 정직한 한도 | `audit.over_50k` · `audit.chars_p95` | 큰 결과는 요약 + handle · 페이지 |
| C9 이름 | `prefixed`(게이트웨이가 붙인 접두 — 앱 몫이 아니다) | 앱이 스스로 접두를 달지 않는다 |
| P1 ~ P3 프로토콜 | 카드 밖 — 앱이 판으로 알린다 | 1단계 stateless 먼저 |
