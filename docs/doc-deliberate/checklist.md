# 문서 심의 — 체크리스트

## 0. 선행 확인(막히면 설계가 바뀐다)
- [ ] 실제 DRM 문서로 COM 읽기가 되는지 확인(Word `Content.Text`, PPT `TextRange.Text`)
- [ ] `SaveAs2` 가 DRM 에 막히는지 확인(막히면 직접 읽기만 쓴다)
- [ ] 대상 PC 의 Office 버전·PDF 열기 가능 여부

## 1. 추출 코어
- [ ] Word 추출(ReadOnly·Visible=false·DisplayAlerts=0·Quit 보장)
- [ ] PowerPoint 추출(슬라이드·노트·표·그룹 도형)
- [ ] PDF 추출(Word 변환 폴백, 스캔본은 빈 텍스트임을 알림)
- [ ] HTML 추출(인코딩 판별)
- [ ] 출력 계약 — JSON {source, kind, pages[], text, tables[], warnings[]}
- [ ] 프로세스 누수 시험(연속 20회 실행 후 WINWORD.EXE 0개)

## 2. 로컬 MCP 서버
- [ ] stdio 서버 + `extract_document(path)`
- [ ] 경로 화이트리스트(임의 파일 읽기 방지)
- [ ] 토큰 페이지에 등록 명령 생성(기존 .bat 생성기 옆)

## 3. 심의 연결
- [ ] 추출 텍스트를 근거 채널로 넣는 흐름(클로드 경로)
- [ ] 긴 문서 분할 — 심의 근거 예산 안에 들어가게 요약·발췌 규칙
- [ ] 문서 인용 표기(슬라이드/페이지 번호)

## 4. (선택) 포털 업로드 경로
- [ ] 추출기 → 포털 POST(PAT 인증)
- [ ] 기존 업로드 오케스트레이션에 연결
- [ ] 문서 텍스트 서버 전송에 대한 사내 판단 확인
