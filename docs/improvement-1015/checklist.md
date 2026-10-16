# 운영·관측·검색 개선 여섯 — 체크리스트

> 계획 `PLAN.md` · 결정 `context-notes.md`.

- [x] 분석 — 여섯 제안의 근거를 지금 코드와 대조, 판정 · 순서 · 열린 물음(PLAN 1~4절), PORT-MAP 서비스 포트 표(8730)
- [x] 6 도구 인자 설명 점수판 — 게이트웨이 재집계 때 앱별 비율 · 단위·범위 낱말 비율 · `/tools-map` 점수와 가장 나쁜 다섯 · 기준 아래 새 앱 기동 경고(막지 않음) · 시험 — 10-16 게이트웨이 `2a98a6e`·`303f023` push(시험 454 · 변이 15/15), dev 재기동 실측: 앱 15 · 도구 436 · 인자 1,531 중 설명 23(1.5%) · 단위·범위 5, 기동 경고는 요약 한 줄(14/15 기준 미만). 가장 나쁜 다섯 — StepForge(635개 중 0) · SignalForge · LaminateAnalyzer · **우리 리스크 앱(132개 중 0)** · MaterialTwinWeb
- [x] 1 상태판(1단계) — 설정 생성기(`gen-status-config.py` — 매니페스트 리스너 전부·게이트웨이 백엔드·에이전트 서버·라우터) · 이미지 굽기(`build-gatus.sh`, v5.37.0) · Drive 운반 · 띄우는 스크립트(`status-board.sh`) · 매니페스트(`status-board`, 기본 꺼짐) · update-all 5b · PORT-MAP(8740, IM-D7) · SMTP 경보(팀 공용 주소, IM-D6) · 시험 · 안내서 `status-board.md`
- [ ] 1 상태판(켜기 — 사람) — ~~dev 에서 `build-gatus.sh` 뒤 `images-to-drive.sh`~~(10-16 끝 — Drive 포털 `latest/` 에 gatus.sif 26,083,328바이트) · cae00 `infra/.env` 에 `STATUS_BOARD=1`(경보는 `STATUS_ALERT_TO=<팀 공용 주소>`, 포털 backend/.env 의 SMTP 설정) 뒤 update-all
- [ ] 1 상태판(2단계) — 스크립트 검사(`mcp-smoke.py` · Drive `latest/` 나이)를 외부 끝점으로 · 검사용 읽기 전용 PAT(사람) · Graph 박스 독립 발신기(IM-D3)
- [x] 3 용량 측정 — 길이 분포 추출기(본문 없이) · GuideLLM 이미지 · 실행 스크립트(직결 대 라우터 · 붙임 켬·끔) · 절차서 — 10-16 main 에 합침 `6c3a6dc`(IM-D13 · LP-D17 · `docs/llm-pool/capacity.md`) · guidellm.sif 를 Drive 포털 `latest/` 에 올렸다(10-16) · 남은 것은 측정 자체(사용자 · cae00 · 심의 없는 때 — llm-pool L-8)
- [x] 4 도구 검색 — 평가셋(문서 사례 42쌍 · 설명 초안 108쌍, 전부 reviewed:false) · 지금 방식 기준선 · RRF 옵션(기본 꺼짐 · 색인 미완 · 임베더 오류 · 2초 초과면 그 호출은 부분문자열, 결과에 mode) · 견주기 시험 — 10-16 게이트웨이 master `095c93a`(시험 469 · 변이 20/20). dev 측정 hit@5 — doc 부분문자열 0.882 · RRF 0.706, auto 0.389 · 0.713 → 지금 꼴(k=60)로는 켜지 않는다(IM-D20)
- [ ] 4 도구 검색(켜기 판단 — 사람) — 쌍 검토(reviewed:true) · 정답 넓히기 · 실사용 질의 모으기(지금은 어디에도 남지 않는다 — 개인정보 판단) · k 60/10 결정 · 켜는 길(게이트웨이는 .env 를 읽지 않는다 — 띄우는 셸 환경) · cae00 에서 다시 재기(GPU 임베더 · DynaForge · RA 가 떠 있어야 doc 8쌍을 잰다)
- [ ] 5 한국어 검색 — 자동 질의 평가셋 · 지금 검색 기준선(사본에서) · 비교는 결과를 보고
- [x] 2 호출 추적(1단계) — 에이전트 서버 기록기 `call_trace.py`(CALL_TRACE_URL · 기본 꺼짐 · 본문은 코드가 가림 · OTLP/HTTP protobuf 손 인코딩 — 새 패키지 없음) · LLM 라우터 `x-hwax-llm-upstream` · Phoenix 20.19.0 이미지(`build-phoenix.sh`, 340MB) · `call-trace.sh`(루프백 8750 한 포트 — gRPC 수신기 끔) · 매니페스트 `call-trace`(CALL_TRACE · 기본 꺼짐) · update-all 5c(띄우기 · 내리기 · 두 줄 어긋남 알림) · Drive 운반 · PORT-MAP 8750 · 안내서 `call-trace.md` · 시험(에이전트 서버 14 · 변이 14/14, 포털 23 · 변이 15/15 + 7/7) · dev 실주행(스팬 14 — 표식 0건) — 10-16 에이전트 서버 main `94b18b9` · 포털 `4bc8d90`(IM-D14~D19)
- [ ] 2 호출 추적(켜기 — 사람) — ~~dev 가 phoenix.sif 를 Drive 에 올린다~~(10-16 끝 — Drive 포털 `latest/` 에 phoenix.sif 356,491,264바이트, sha256 이 에이전트가 구운 것과 같다) · cae00 포털 `infra/.env` 에 `CALL_TRACE=1` → update-all(§2 가 받고 5c 가 띄운다) · 에이전트 서버 `.env` 에 `CALL_TRACE_URL=http://127.0.0.1:8750` → 재기동(도는 심의가 없을 때 — 다음 update-all §4 도 다시 띄운다)
- [x] 우리 앱의 인자 설명 채우기 — 에이전트 서버 심의 도구 일곱의 인자 39개(10-16 `650b541`) · 리스크 앱 MCP 31종 인자 134개(10-16 리스크 앱 main `ae4af1d` — 허용값 · 상한은 코드 상수와 REST 본문 모델에서 읽는다 · 인자 계약 스냅샷 시험 · 변이 12/12 · 전체 3,359 통과, dev 교체 9419 · SIF Drive). dev 점수판 — hwax-deliberation 39/39(단위·범위 19), 리스크 앱 134/134(33)
- [ ] 업데이트 이력 · CLAUDE.md 문서 표
