# 문서 → RA 정밀 변환 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 조사 [research.md](research.md).

## 계획(10-24)
- [x] 조사 — RA 형식 · 넣는 길 · 엔티티 · 지금 변환기 셋 · VLM · SP · HEAX 앱 바탕 · 바깥 도구(research.md)
- [x] 계획 · 원칙 · 단계 · 평가 · 위험(PLAN.md) · 결정 기록(DF-D1~D8)
- [ ] 사람이 정할 것 §12 — 1 어디에 · 2 RA 에 넣는 길 · 3 VLM 자리 · 4 금 표본 · 5 기준 숫자 · 6 형식 범위 · 7 Word 쪽 나누기 · 8 판독 자리 · 9 원본 슬라이드 그림 · 10 SP ↔ RA 엔티티 · 11 구조화 출력

## M0 실측
- [ ] 금 표본 — 실문서 40건 + DRM 5건(사람) · dev `/data` · 정답 뽑기(원본 XML → 글 · 숫자 · 표 · 차트 값)
- [ ] 기준선 — RA 가져오기(+ ai-draft) · AIDH `convert_file` 을 금 표본에 · 지표 표
- [ ] Docling — dev 에 격리 venv · 금 표본 · 글 회계 · 표 · 차트 · 노트 · 기하 · 쪽당 시간(CPU · GPU) · 모델 무게 · 라이선스
- [ ] 형식별 직접 해부 — python-pptx · python-docx · openpyxl 로 Docling 이 놓치는 것(차트 XML 캐시 · 노트 · SmartArt · OMML · 병합 · 기하)
- [ ] Pydantic AI — 우리 GLM · Qwen 에 `NativeOutput` · `ToolOutput` · 비스트리밍 · 스키마 준수율(목표 ≥ 99%) · 대체재(vLLM json_schema 직접)와 견주기
- [ ] VLM 판독 — 공학 그림 · 그림 차트 값 · 그림 속 한국어 글 · 장당 시간 · 지어낸 수치 · Docling 그림 설명이 원격 VLM 을 부르나
- [ ] 그리기 — LibreOffice 헤드리스 + 한글 글꼴을 SIF 에 · 슬라이드 그림 · EMF → PNG
- [ ] RA — dev RA 에 엄격 생성(`POST /api/reports`) · `GET /api/widgets` 판 · 엔티티 API · MCP resolve · 제안 큐에 넣는 길 · 큰 파일 상한
- [ ] SP — 가짜 허브(수신 규칙 열하나) · 과제코드 · 모델명 꼴
- [ ] 결정 기록 — §7 의 선택을 수치로

## M1 PPTX 끝에서 끝
- [ ] DocForge 뼈대 — HEAX 앱(매니페스트 · MCP · 잡 · 원장) · 새 리포(§12-1 뒤)
- [ ] IR · PPTX 해부 · 배치(§6) · 서식 → 허용 태그 · 표 · 차트 → chart/pie/scatter · 노트 · 링크 · 그림(EMF → PNG)
- [ ] 검증 — 글 회계 · 숫자 대조 · 그림 회계 · RA 스키마 · 격자 합 · 무음 누락 0
- [ ] 포장 — `report.json` · `resources/` · `conversion.json`
- [ ] 포털 — 목적지 「Report Archive — 정밀 변환」 · 잡 진행 패널 · 사용자 명의 배달(엄격 생성) · 대화 알림
- [ ] 시험 · 반대 검토 · 변이 · dev 실주행 · 문서 · 이력 · 올림

## M2 Word · Excel(+ PDF)
- [ ] DOCX — 제목 · 번호 목록 · 표 · 그림 · 수식(OMML → LaTeX) · 각주 · 쪽 나누기(§12-7)
- [ ] XLSX — 시트 → 쪽 · 표 영역 찾기 · 머리 행 · 병합 · 숫자 형식 · 수식 + 값 · 차트 · 큰 시트
- [ ] PDF — Docling 기본
- [ ] 금 표본 지표

## M3 그림 읽기
- [ ] 그림 판독 · 그림 차트의 값(확인 필요 표시) · 그림 속 글 · SmartArt 그림
- [ ] '모델 판독' 표시 · 판독 캐시 · 동시 수 상한 · 챗 먼저
- [ ] 판독 지표 · 표시 없는 모델 글 0 · 챗 첫 조각 지연

## M4 온톨로지 · DRM · MCP
- [ ] SP 거울(수신 키트) · 과제 · 모델 · 부서 후보 + 근거 구절 · RA `key_value` · `tags` · 엔티티(§12-10)
- [ ] PC 도우미 묶음 길 — `hwax-doc/1` + 슬라이드 PNG 판독 · 낮은 충실도 표시
- [ ] MCP 도구(convert · status · package) · RA 에 넣는 길(§12-2)
- [ ] '이 대화에서 분석' 을 DocForge IR 로

## M5 운영
- [ ] cae00 — 굵은 SIF(모델 · LibreOffice · 글꼴) · Drive(지문 목록 합치기) · server-setup(사람 몫)
- [ ] 상태판 · RA 에서 고친 것을 평가 표본으로 · 절차서
