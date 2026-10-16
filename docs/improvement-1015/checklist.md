# 운영·관측·검색 개선 여섯 — 체크리스트

> 계획 `PLAN.md` · 결정 `context-notes.md`.

- [x] 분석 — 여섯 제안의 근거를 지금 코드와 대조, 판정 · 순서 · 열린 물음(PLAN 1~4절), PORT-MAP 서비스 포트 표(8730)
- [x] 6 도구 인자 설명 점수판 — 게이트웨이 재집계 때 앱별 비율 · 단위·범위 낱말 비율 · `/tools-map` 점수와 가장 나쁜 다섯 · 기준 아래 새 앱 기동 경고(막지 않음) · 시험 — 10-16 게이트웨이 `2a98a6e`·`303f023` push(시험 454 · 변이 15/15), dev 재기동 실측: 앱 15 · 도구 436 · 인자 1,531 중 설명 23(1.5%) · 단위·범위 5, 기동 경고는 요약 한 줄(14/15 기준 미만). 가장 나쁜 다섯 — StepForge(635개 중 0) · SignalForge · LaminateAnalyzer · **우리 리스크 앱(132개 중 0)** · MaterialTwinWeb
- [x] 1 상태판(1단계) — 설정 생성기(`gen-status-config.py` — 매니페스트 리스너 전부·게이트웨이 백엔드·에이전트 서버·라우터) · 이미지 굽기(`build-gatus.sh`, v5.37.0) · Drive 운반 · 띄우는 스크립트(`status-board.sh`) · 매니페스트(`status-board`, 기본 꺼짐) · update-all 5b · PORT-MAP(8740, IM-D7) · SMTP 경보(팀 공용 주소, IM-D6) · 시험 · 안내서 `status-board.md`
- [ ] 1 상태판(켜기 — 사람) — ~~dev 에서 `build-gatus.sh` 뒤 `images-to-drive.sh`~~(10-16 끝 — Drive 포털 `latest/` 에 gatus.sif 26,083,328바이트) · cae00 `infra/.env` 에 `STATUS_BOARD=1`(경보는 `STATUS_ALERT_TO=<팀 공용 주소>`, 포털 backend/.env 의 SMTP 설정) 뒤 update-all
- [ ] 1 상태판(2단계) — 스크립트 검사(`mcp-smoke.py` · Drive `latest/` 나이)를 외부 끝점으로 · 검사용 읽기 전용 PAT(사람) · Graph 박스 독립 발신기(IM-D3)
- [x] 3 용량 측정 — 길이 분포 추출기(본문 없이) · GuideLLM 이미지 · 실행 스크립트(직결 대 라우터 · 붙임 켬·끔) · 절차서 — 10-16 main 에 합침 `6c3a6dc`(IM-D13 · LP-D17 · `docs/llm-pool/capacity.md`) · guidellm.sif 를 Drive 포털 `latest/` 에 올렸다(10-16) · 남은 것은 측정 자체(사용자 · cae00 · 심의 없는 때 — llm-pool L-8)
- [ ] 4 도구 검색 — 평가셋(오배정 사례 + 쌍 초안) · 지금 방식 기준선 · RRF 옵션(기본 꺼짐 · 임베더 죽으면 지금 방식) · 견주기 시험
- [ ] 5 한국어 검색 — 자동 질의 평가셋 · 지금 검색 기준선(사본에서) · 비교는 결과를 보고
- [x] 2 호출 추적(1단계) — 에이전트 서버 기록기 `call_trace.py`(CALL_TRACE_URL · 기본 꺼짐 · 본문은 코드가 가림 · OTLP/HTTP protobuf 손 인코딩 — 새 패키지 없음) · LLM 라우터 `x-hwax-llm-upstream` · Phoenix 20.19.0 이미지(`build-phoenix.sh`, 340MB) · `call-trace.sh`(루프백 8750 한 포트 — gRPC 수신기 끔) · 매니페스트 `call-trace`(CALL_TRACE · 기본 꺼짐) · update-all 5c(띄우기 · 내리기 · 두 줄 어긋남 알림) · Drive 운반 · PORT-MAP 8750 · 안내서 `call-trace.md` · 시험(에이전트 서버 14 · 변이 14/14, 포털 23 · 변이 15/15 + 7/7) · dev 실주행(스팬 14 — 표식 0건) — 10-16 에이전트 서버 main `94b18b9` · 포털 `4bc8d90`(IM-D14~D19)
- [ ] 2 호출 추적(켜기 — 사람) — dev 가 phoenix.sif 를 Drive 에 올린 뒤 cae00 포털 `infra/.env` 에 `CALL_TRACE=1` → update-all(§2 가 받고 5c 가 띄운다) · 에이전트 서버 `.env` 에 `CALL_TRACE_URL=http://127.0.0.1:8750` → 재기동(도는 심의가 없을 때 — 다음 update-all §4 도 다시 띄운다)
- [ ] 우리 앱의 인자 설명 채우기 — 리스크 앱 MCP 31종(132개 · X-2 합친 뒤) · ~~에이전트 서버 deliberate_* (제안 근거의 14개)~~(10-16 — 심의 도구 일곱의 인자 39개 전부, 상한 수는 엔진 상수에서 읽는다 · 시험 셋 · 변이 3/3)
- [ ] 업데이트 이력 · CLAUDE.md 문서 표
