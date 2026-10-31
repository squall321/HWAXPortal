# 문서 → RA 정밀 변환 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 조사 [research.md](research.md) · cae00 설정 [server-setup.md](server-setup.md).

## 계획(10-24)
- [x] 조사 — RA 형식 · 넣는 길 · 엔티티 · 지금 변환기 셋 · VLM · SP · HEAX 앱 바탕 · 바깥 도구(research.md)
- [x] 계획 · 원칙 · 단계 · 평가 · 위험(PLAN.md) · 결정 기록(DF-D1~D8)
- [x] 사람이 정할 것 §12-1 어디에(새 HEAX 앱 DocForge) · §12-3 VLM(stcx Qwen) — 10-24
- [ ] 사람이 정할 것 §12 남은 것 — 2 RA 에 넣는 길 · 4 금 표본 · 5 기준 숫자 · 6 형식 범위 · 7 Word 쪽 나누기 · 8 판독 자리 · 9 원본 슬라이드 그림 · 10 SP ↔ RA 엔티티 · 11 구조화 출력 — 사용자 결정 10-31 A19: (A) 지금 박힌 기본값으로 정한다 — 2 · 6 ~ 11 은 PLAN §12 에 적었다(DF-D25) · 4 · 5 는 cae00 금 표본 때 (10-31 정리)

## 뼈대 · 인계(10-24, dev)
- [x] DocForge 리포(`squall321/DocForge` 비공개 · main · release `9f0d2e9`) — 앱 · 계약 · 걸어 다니는 뼈대 · 단계 명세 · 시험 16 + 명세 8 · 스크립트 · 문서(CLAUDE.md · docs/*)
- [x] 인계 계획서 [cae00-handoff.md](cae00-handoff.md) — 첫날 순서 · 첫 배치(dev 몫) · 단계 · 포털 배달 명세 · 다른 리포 · 하지 말 것 · 허브 규약 · 지문 목록 합치기
- [x] 순서 고침(DF-D14) — dev 먼저(DocForge `docs/START.md` D0~D11), 실데이터가 필요해지면 cae00 · 허브 등록은 첫 SIF Drive 와 한 묶음(DF-D15)
- [x] dev 단계 D0~D11(DocForge 창의 세션 — `docs/START.md`) — 10-24
- [x] 첫 배치 dev 쪽 — HEAXHub 등록 · SIF 빌드 · 모델 · Drive 를 한 날에(DocForge docs/DEPLOY.md §4 1~6) — 10-24, release `3154dfa`
- [x] dev 2단계(DocForge `docs/START.md` §8) — E1 PPTX 수식 · E2 DOCX · E3 XLSX · E4 PDF · E5 PC 도우미 묶음 · E6 평가 도구(truth · eval) — 10-24
- [ ] 첫 배치 cae00 쪽(사람) — 박스 값 · models-from-drive · update-all · /health · 뼈대 실주행(§4 7~9 · §5)

## M0 실측
- [ ] 금 표본 — 실문서 40건 + DRM 5건(사람) · cae00 개발 데이터 폴더(리포 밖) · 정답 뽑기(원본 XML → 글 · 숫자 · 표 · 차트 값)
- [ ] 기준선 — RA 가져오기(+ ai-draft) · AIDH `convert_file` 을 금 표본에 · 지표 표
- [ ] Docling — cae00(길 A venv · 길 B 앱 SIF) · 금 표본 · 글 회계 · 표 · 차트 · 노트 · 기하 · 쪽당 시간(CPU · GPU) · 모델 무게 · 라이선스
- [x] 형식별 직접 해부 — python-pptx · python-docx · openpyxl 로 Docling 이 놓치는 것(차트 XML 캐시 · 노트 · SmartArt · OMML · 병합 · 기하) — 풀림 DocForge docforge/parse/pptx_native.py · docx_native.py + omml.py · xlsx_native.py · docs/m0-results.md dev 절(10-24) — 금 표본 대조는 23 · 43줄 (10-31 정리)
- [ ] Pydantic AI — 우리 GLM · Qwen 에 `NativeOutput` · `ToolOutput` · 비스트리밍 · 스키마 준수율(목표 ≥ 99%) · 대체재(vLLM json_schema 직접)와 견주기
- [ ] VLM 판독 — 공학 그림 · 그림 차트 값 · 그림 속 한국어 글 · 장당 시간 · 지어낸 수치 · Docling 그림 설명이 원격 VLM 을 부르나
- [x] 그리기 — LibreOffice 헤드리스 + 한글 글꼴을 SIF 에 · 슬라이드 그림 · EMF → PNG — 풀림 DocForge docs/DEPLOY.md:88-89(SIF 에 LibreOffice 25.2.3 · 한글 글꼴 42) · docforge/render/libreoffice.py(쪽 그림 · EMF → PNG) — 실문서 표본은 cae00 M0 (10-31 정리)
- [ ] RA — dev RA 에 엄격 생성(`POST /api/reports`) · `GET /api/widgets` 판 · 엔티티 API · MCP resolve · 제안 큐에 넣는 길 · 큰 파일 상한
- [ ] SP — 가짜 허브(수신 규칙 열하나) · 과제코드 · 모델명 꼴
- [ ] 결정 기록 — §7 의 선택을 수치로

## M1 PPTX 끝에서 끝
- [x] DocForge 뼈대 — HEAX 앱(매니페스트 · MCP · 잡 · 원장) · 새 리포(§12-1 뒤) — 10-24
- [x] IR · PPTX 해부 · 배치(§6) · 서식 → 허용 태그 · 표 · 차트 → chart/pie/scatter · 노트 · 링크 · 그림(EMF → PNG) · 수식(E1) — 합성 · 공개 견본
- [x] 검증 — 글 회계 · 숫자 대조 · RA 스키마(RA 자신의 검증) · 격자 합 · 무음 누락이면 잡 실패 · 평가 도구(truth · eval, E6)
- [x] 포장 — `report.json` · `resources/` · `conversion.json` · `ir.json`
- [x] 포털 — 목적지 「Report Archive — 정밀 변환」 · 잡 진행 패널 · 사용자 명의 배달(엄격 생성) · 대화 알림(DF-D17 · 10-24, 가짜 MCP · 가짜 RA 시험)
- [x] 포털 — 브라우저 시험(정밀 변환 진행 → 배달 → 알림, test_chat_ppt_in_browser)
- [x] 포털 — 창을 닫아 넣지 못한 정밀 변환 다시 열기(입력창 위 목록 · 이어 보기 · 숨기기 · 잡 기록 7일, DF-D23 · DocForge E15)
- [x] DocForge 0.2.0 배치 dev 쪽 — release `7b166ac` · HEAXHub `973444a` · dev 허브 · Drive(10-25)
- [x] cae00 사람 몫 절차서 [server-setup.md](server-setup.md) — HEAXHub/.env 한 줄 · 모델 처음 한 번 · update-all 순서 · 권한(CAEG 은 `*`) · 페르소나 동기화 · 확인 · 막히면
- [ ] cae00 update-all(사람 — server-setup §1 ~ §6) → dev · cae00 실주행
- [ ] 금 PPTX 지표 ≥ 기준선(cae00 · 금 표본) · 반대 검토 · 변이 · dev 실주행(beta 뒤)

## M2 Word · Excel(+ PDF)
- [x] DOCX — 제목 · 번호 목록 · 표 · 그림 · 수식(OMML → LaTeX) · 각주 · 쪽 나누기(word_split 기본 h1 — §12-7 잠정) — E2
- [x] XLSX — 시트 → 쪽 · 표 영역 찾기 · 머리 행 · 병합 · 숫자 형식 · 수식 + 값 · 차트 · 큰 시트 — E3
- [x] PDF — Docling 기본 — E4
- [ ] 금 표본 지표

## M3 그림 읽기
- [ ] 그림 판독 · 그림 차트의 값(확인 필요 표시) · 그림 속 글 · SmartArt 그림
- [x] '모델 판독' 표시 · 판독 캐시 · 동시 수 상한(가짜 서버로 — 진짜 stcx Qwen 은 cae00)
- [x] 그림 둘째 판독 — 첫 판독의 종류로 고른 그림만 차트 값(구조화 출력 · '값 확인 필요') · 그림 속 글(DocForge E9 · R-D39 · 10-25)
- [ ] 판독 지표 · 표시 없는 모델 글 0 · 챗 첫 조각 지연

## M4 온톨로지 · DRM · MCP
- [x] SP 거울(수신 키트 — StepForge 판을 옮김) · 과제 · 모델 후보(글자 그대로 · 근거 구절) · 첫 쪽 `key_value` · `tags`(DocForge E13 · E14 — 가짜 허브로, 진짜 허브 주소 · 토큰은 사람 몫)
- [ ] 부서 후보 · pattern · fuzzy · llm(실데이터 — SP 모델명 규칙) · RA 엔티티(§12-10 · RA 요청서)
- [x] RA 요청서 [ra-requests.md](ra-requests.md) — 템플릿 시드 · 검증만(dry_run) · SP key 를 엔티티 code 로(자동 태깅) · 원본 첨부 상한 · 운영 확인(DF-D24 · DocForge E17). RA 쪽에 건네기는 사람 몫
- [x] PC 도우미 묶음 길 — `hwax-doc/1` + 슬라이드 PNG 판독 · 낮은 충실도 표시(DocForge E5 · R-D35, 포털이 글 + 그림을 zip 으로 넘김 DF-D18 · 10-25)
- [x] MCP 도구(capabilities · convert · status · package · cancel) · RA 에 넣는 길(포털이 사용자 명의 엄격 생성 — DF-D17, §12-2 의 M1 몫)
- [x] '이 대화에서 분석' 을 DocForge 로 — DocForge 가 보이는 사람은 DocForge 가 읽은 글(document.md)을 문서 칩으로 · 아니면 지금 길(DF-D19 · 10-25)
- [x] DocForge 운영자 페르소나 `he-doc-docforge`(infra/personas/he-team.json — RA 는 선택 앱, DocForge 가 게이트웨이에 실리면 동기화가 만든다 · DF-D20)

## M5 운영
- [ ] cae00 — 굵은 SIF(모델 · LibreOffice · 글꼴) · Drive(지문 목록 합치기) · server-setup(사람 몫)
- [x] 상태판 · RA 에서 고친 것을 평가 표본으로 · 절차서 — 풀림 infra/scripts/gen-status-config.py:257-271(백엔드별 검사 — heax-doc_forge) · DocForge `d2808ea`(E16 사람 편집량) · docs/doc-to-ra/server-setup.md — 실데이터로 쌓는 것은 cae00 실사용 뒤 (10-31 정리)
