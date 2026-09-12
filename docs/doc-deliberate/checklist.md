# 문서 심의 — 체크리스트

## 0. 선행 확인(막히면 설계가 바뀐다)
- [x] 실제 DRM 문서로 COM 읽기가 되는지 확인(Word `Content.Text`, PPT `TextRange.Text`)
- [ ] `SaveAs2` 가 DRM 에 막히는지 확인(막히면 직접 읽기만 쓴다)
- [ ] 대상 PC 의 Office 버전·PDF 열기 가능 여부

## 1. 추출 코어
- [x] Word 추출(ReadOnly·Visible=false·DisplayAlerts=0·Quit 보장)
- [x] PowerPoint 추출(슬라이드·노트·표·그룹 도형)
- [x] PDF 추출(Word 변환 폴백, 스캔본은 빈 텍스트임을 알림)
- [x] HTML 추출(인코딩 판별)
- [x] 출력 계약 — `.hwax.md`(머리말 + `[p.N]`/`[s.N]` 표지). JSON 은 2차(RA 세그먼트)
- [ ] 프로세스 누수 시험(연속 20회 실행 후 WINWORD.EXE 0개)

## 2. 로컬 MCP 서버
- [ ] stdio 서버 + `extract_document(path)`
- [ ] 경로 화이트리스트(임의 파일 읽기 방지)
- [ ] 토큰 페이지에 등록 명령 생성(기존 .bat 생성기 옆)

## 3. 심의·챗 연결 (웹)
- [x] 심의 사전 근거 예산 확대(11KB→60KB) + 세 계층 계약 테스트
- [x] `HANDOFF_RESULT_CHARS` 동반 상향(1,200→4,000) — 예산만 올리면 소용없다
- [x] 브라우저에서 추출문 읽기(`docAttach.ts`) — 서버 업로드 없음
- [x] Office 원본을 붙이면 추출 안내 + 추출기 내려받기(`DocExtractHint`)
- [x] 챗 주입(`_doc_block` → sys_prompt, 세 갈래 공유) + 근거 규율
- [x] 심의 주입(`delib_opts.evidence` 채널 재사용)
- [x] 문서 인용 표기(`[p.N]`/`[s.N]` 를 추출기가 달고 규율이 인용을 요구)
- [ ] 띵킹 모드 경로에도 문서 주입

## 4. (선택) 포털 업로드 경로
- [ ] 추출기 → 포털 POST(PAT 인증)
- [ ] 기존 업로드 오케스트레이션에 연결
- [ ] 문서 텍스트 서버 전송에 대한 사내 판단 확인
