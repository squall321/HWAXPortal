# 체크리스트 — 상호작용 데이터 수집 · DB화 · 활용

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

## M0 준비
- [x] 사용자 결정 다섯(IX-1 ~ IX-5) 기록
- [x] 저장 스키마 — contract §2 표 넷 + 포털 몫이 더한 것 둘(shared_sessions.raw · erase_marks — IX-13 · IX-14, 계약 변경 제안)
- [x] 비밀 가림 규칙(칸 이름 · 값 꼴) · 시험 꼴 — 포털 `app/interactions/redact.py` · 부록 벡터 다섯을 시험이 단언 · PC 킷 정규식도 같은 벡터(IX-15 · IX-17)
- [x] 알림 문구 — 포털 몫(토큰 화면 · 웹 챗 첫 화면, 켠 박스에서만 — `/interactions/status` 의 notice) · 게이트웨이 몫은 게이트웨이 가지 · **문구 확정은 사람**
- [ ] 회사 개인정보 · 보안 규정 확인 — **사람**

## M1 원장층
- [x] ~~DB `hwax_interactions`(AIDataHub PG)~~ → 포털 `interactions.sqlite`(IX-10) — 데이터 레지스트리 클래스(sync: none) · start.sh 경로 넘김 · 0600 · 시험 격리(IX-11)
- [x] 포털 수집기 — S1 대화 저장소 증분 · 백필, S6 루틴 · 절차 증분(IX-11)
- [x] S2 웹 챗 턴 메타 — 중계가 켠 박스에서만 답 meta.turn(모델 · 생각 · 자기검증 · 확인 카드)으로 남기고 수집기가 옮긴다(쓴 도구 · 루틴은 종전 meta — IX-12). 팀은 아직(에이전트 서버가 SSE 로 주지 않는다)
- [ ] 게이트웨이 S3 — `_call_tool_body` 끝에서 인자 · 결과 원문을 스풀로(비밀 가림 · 상한 · via · corr · client) · 스풀 회전 · 넘침 알림
- [x] 포털 수집기가 게이트웨이 스풀을 가져감(겹침 막기 — UNIQUE(source, source_ref) · via 그대로 · share_conversation 줄 건너뜀 — IX-11 · IX-15)
- [x] S4 도구 검색 질의 — 게이트웨이 `/search-log` 를 옮긴다(30일 백필은 1000줄 한도 — 자리 · 호출자는 **게이트웨이에 청할 것**, IX-19)
- [x] 박스 스위치 `INTERACTIONS_ENABLED`(기본 끔 — 끄면 바이트까지 지금과 같음) · 상태판 줄 · update-all ○(포털 · 게이트웨이 둘 — 3.5i) · /health/interactions(IX-16)
- [x] 백업 대상(`backup-local.sh` portal) · 레지스트리 sync: none 시험(`test_interactions_infra.py`)
- [x] 시험 · 변이 · 전체 회귀(포털) — 게이트웨이는 그 가지 몫
- [ ] dev 켜서 실제 쌓임 확인(사람 결정 뒤 — 이 가지는 dev 를 재기동하지 않았다)

## M2 공유 길
- [ ] 게이트웨이 `share_conversation`(사람이 청한 때만 — 설명) → 포털
- [x] 포털 `POST /interactions/share`(PAT 또는 세션 + CSRF · 50 MB · 같은 세션 덮어쓰기 · 기록 파일 풀이 + 원문 가린 채 — IX-13)
- [x] PC 킷 — `/hwax-share` 명령 · 선택 `SessionEnd` 훅 · PC 쪽 비밀 가림 · 설정 배치에 선택 칸 · 박스 표시(IX-17)
- [ ] Windows 실시험(사람)

## M3 열람 · 지우기
- [x] 권한 `feat:interaction-analyst`(`grant_only`)
- [x] 내 기록 화면 · 검색 · 지우기 청구(원문 + 지우기 표지 — 가공본 · 임베딩은 M5 가 같은 id 로)
- [x] 분석가 화면 · 검색 · 원문 열기 감사 행(IX-18)

## M4 심의 · 리스크 편입
- [ ] S5 심의 잡 원장 → 원장층(끝난 잡 증분)
- [ ] S7 리스크 앱 읽기 창구 요청서(리스크 앱 몫) · 편입

## M5 가공층
- [ ] 밤 배치 — 가림 · 가명 · 요지 · 주제 · 앱 · 의도 · 결과 신호 · 임베딩(심의 · 띵킹 없는 때)

## M6 활용
- [ ] 집계 화면(수요 지도 · 결과 신호)
- [ ] 평가셋 내보내기 — 도구 검색 정답 후보 · 심의 A/B 재생 묶음
- [ ] 실패 지도 보고 → 플랫폼별 요청서 초안
- [ ] 지식 후보 큐 → AIDataHub 승인 흐름

## M7 운영
- [ ] 용량 추세 · 상태판 · 복구 연습
- [ ] cae00 받은 편지함(켜는 차례 · 알림 · 규정 확인 뒤)
