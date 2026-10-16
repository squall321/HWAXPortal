# 운영·관측·검색 개선 여섯 — 체크리스트

> 계획 `PLAN.md` · 결정 `context-notes.md`.

- [x] 분석 — 여섯 제안의 근거를 지금 코드와 대조, 판정 · 순서 · 열린 물음(PLAN 1~4절), PORT-MAP 서비스 포트 표(9130)
- [ ] 6 도구 인자 설명 점수판 — 게이트웨이 재집계 때 앱별 비율 · 단위·범위 낱말 비율 · `/tools-map` 점수와 가장 나쁜 다섯 · 기준 아래 새 앱 기동 경고(막지 않음) · 시험
- [x] 1 상태판(1단계) — 설정 생성기(`gen-status-config.py` — 매니페스트 리스너 전부·게이트웨이 백엔드·에이전트 서버·라우터) · 이미지 굽기(`build-gatus.sh`, v5.37.0) · Drive 운반 · 띄우는 스크립트(`status-board.sh`) · 매니페스트(`status-board`, 기본 꺼짐) · update-all 5b · PORT-MAP(8740, IM-D7) · SMTP 경보(팀 공용 주소, IM-D6) · 시험 · 안내서 `status-board.md`
- [ ] 1 상태판(켜기 — 사람) — dev 에서 `build-gatus.sh` 뒤 `images-to-drive.sh` · cae00 `infra/.env` 에 `STATUS_BOARD=1`(경보는 `STATUS_ALERT_TO`) 뒤 update-all
- [ ] 1 상태판(2단계) — 스크립트 검사(`mcp-smoke.py` · Drive `latest/` 나이)를 외부 끝점으로 · 검사용 읽기 전용 PAT(사람) · Graph 박스 독립 발신기(IM-D3)
- [ ] 3 용량 측정 — 길이 분포 추출기(본문 없이) · GuideLLM 이미지 · 실행 스크립트(직결 대 라우터 · 붙임 켬·끔) · 절차서 / 측정은 사용자(cae00)
- [ ] 4 도구 검색 — 평가셋(오배정 사례 + 쌍 초안) · 지금 방식 기준선 · RRF 옵션(기본 꺼짐 · 임베더 죽으면 지금 방식) · 견주기 시험
- [ ] 5 한국어 검색 — 자동 질의 평가셋 · 지금 검색 기준선(사본에서) · 비교는 결과를 보고
- [ ] 2 호출 추적 — 원문 없이 시간·토큰만(IM-D6) · 에이전트 서버 연결(env 로 켬 · 본문 가림) · Phoenix 이미지 · 패키지 반입 길
- [ ] 업데이트 이력 · CLAUDE.md 문서 표
