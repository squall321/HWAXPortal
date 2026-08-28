<!-- 포탈에서 하기로 한 기능들의 구현도·남은 일 감사(살아있는 문서) -->
# 구현도 · 남은 일 점검 (2026-08-28)

포탈에서 하기로 한 기능들의 실제 구현 상태와 **남은 일**을 한눈에. 상세는 각 `*-FEATURE-SUMMARY.md`.
표기 — ✅ 완료 · 🟡 dev 완료·cae00/실행 대기 · ⬜ 미착수/설계만.

## 1. 논문 → 지식카드 파이프라인 (신규, 이번 세션 핵심)

| 항목 | 상태 | 비고 |
|---|---|---|
| PaperIngest 웹 UI(PDF 업로드·GLM 게이트·HEAX 타일) | ✅ | dev 기동 확인(port 9235, 웹UI 200) |
| 원본 PDF 보관(POST /papers) | ✅ | Claude 비전 저작용 |
| A+B GLM 게이트 env(LLM_ 폴백·NO_PROXY 자동, 내부IP 하드코딩 0) | ✅ | dev glm_ready:false 정상(LLM_ 미주입) |
| PaperAuthor P1 단일 PDF→카드(claude -p 비전) | ✅ | 실증 Allen/Hong |
| P3 MCP 자동분류·그라운딩(recommend_agents·get_context_bundle) | ✅ | DOC-ref 실재 검증됨 |
| P4 적대적 검증 게이트(verify_cards·get_record) | ✅ 코드 | 자동 게이트 full-run 은 background 필요(>10분) |
| P2 배치(run_inbox·ledger 멱등·실패격리) | ✅ | 편당 ~$3(--mcp) |
| Drive relay 송출(to_drive_pusher: cae00 inbox→Drive) | ✅ 코드 | cron 미설정 |
| **cae00 배포**(dist-from-drive→redeploy-app) | 🟡 | SIF Drive 송출 완료, cae00 pull·기동은 박스에서 |
| **cae00 LLM=상암 GLM 설정** | ⬜ | glm_ready:true 되려면 필요 |
| **relay cron + INBOX 경로 정합** | ⬜ | 호스트 cron, 컨테이너/data/_inbox↔app_data |
| **dev EG relay pull 자동화**(Drive OUTBOX→EG inbox→ingest→export) | ⬜ | 현재 수동, 설계문서만 |
| **out→ExpertAgents 정식 편입**(id 발급·병합) | ⬜ | 현재 out/ 대기(Allen 2+Hong 3) |

## 2. 심의(Deliberation) 파이프라인

| 항목 | 상태 | 비고 |
|---|---|---|
| 다중라운드 전문가 심의·수렴·의사결정문 | ✅ | hwax-deliberate |
| 시뮬 심의 2단 수치 스파인 7석 고정착석(MCP+웹) | ✅ | |
| 카드 그라운딩(심의 발언이 지식카드 인용, sim 기본 ON) | ✅ | |
| 3단 '구축 계획서'(build-plan) 특화 파라메트릭 모듈 개발계획 | ✅ opt-in | |
| 전문가·도구 직접선택 UX(pinned_tools·pinned_agent) | ✅ | |
| 반영 절차(API 재기동·erag 재색인·워크플로 sync) | ✅ 문서화 | |

## 3. 배포 · 운영

| 항목 | 상태 | 비고 |
|---|---|---|
| update-all 오케스트레이션(포털+전 서비스) | ✅ | |
| paper-ingest dev 배포(SIF 재빌드·기동·Drive 송출) | ✅ | 이번 세션 |
| STE(SmartTwinExplorer) 배포 자동화(refresh-code §11·deploy-ste 부트스트랩) | ✅ 코드 | update-all 과 분리 |
| **STE cae00 실주행 검증** | ⬜ | 사용자 몫 |
| **TLS/HTTPS go-live**(hwax.sec.samsung.net) | 🟡 | 스크립트·인증서생성기·문서 커밋완료, cae00 실행 대기 |
| **실 Samsung AD SSO 전환**(mock→real) | 🟡 | GO-LIVE.md 절차 문서화, 실행 대기 |

## 4. SSO · 게이트웨이 · 데이터

| 항목 | 상태 | 비고 |
|---|---|---|
| SSO 브로커 허브 + jwt-handoff(4개 서비스) | ✅ | |
| 경로 라우팅(hwax.../서비스명/) | ✅ | |
| MCP 게이트웨이(:9110, 다중 백엔드→도구 집계) | ✅ | health 255 tools |
| AIDataHub 그라운딩(recommend_agents·get_context_bundle·records) | ✅ | update-all §3 merge 로 cae00 반영 |
| 채팅독(스트리밍·도구실행·파일 업로드) | ✅ | 물성 CSV 업로드 왕복 포함 |

## 5. 기타 미결(백로그)

- SmartTwinMCP `feat/cuboid-scatter-drop` 브랜치 미머지.
- ExpertAgents 사용자 WIP(카드 27 미커밋) — 사용자 소관.
- P4 verify 자동 게이트 full-run 을 background 표준화(편당 >10분).

---
**요약** — 코드·dev 배포는 대부분 ✅. **남은 핵심은 cae00 쪽 실행**(paper-ingest pull·LLM설정·relay cron, TLS, AD SSO, STE 실주행)과 **파이프라인 자동화 2건**(dev EG relay pull, out→ExpertAgents 편입). cae00 airgap 은 박스에서 직접 실행해야 한다.
