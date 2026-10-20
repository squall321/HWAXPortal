# 설치 파일(hwax-claude-setup.bat) — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

## 10-20 개선 요청 다섯
- [x] 1 Store 판 설정 위치 — 두 곳 다 찾아 반영 · 줄마다 경로
- [x] 2 대소문자 구분 읽기 — JavaScriptSerializer(Desktop · Claude Code 두 병합) · 백업 유지
- [x] 3 env 기본값 — NO_PROXY(포털 호스트 · localhost · 127.0.0.1) · NODE_EXTRA_CA_CERTS = 포털 + 윈도우 신뢰 저장소 묶음(실패하면 포털 인증서만)
- [x] 4 토큰 갱신 — 있는 hwax 항목을 바탕으로 AUTH · 명령 · 주소만, 손으로 넣은 env 는 남김
- [x] 5 실행 중인 Claude Desktop 이면 멈춤 · 트레이 종료 안내(설정을 바꾸기 전에)
- [x] 화면에 보여 주는 수동 스니펫(Desktop · Claude Code)도 같은 env
- [x] 시험(test_setup_bat) — 26 통과(새 6 · 고친 5, 변이 셋 잡힘) — 산출물 글로 다섯 각각 · 기존 시험(토큰 비노출 · 괄호 블록 없음 · 라벨) 그대로
- [x] 화면 빌드 · Drive · 업데이트 이력 — 빌드 표식 = `HEAD:frontend`, Drive `images-20261020-071607Z` + `latest/frontend-dist.tar.gz`(10-20), 이력 10-20 '연결'
- [ ] 실제 Windows 확인(사람 — 염종섭 님): Store 판 · NO_PROXY/no_proxy 가 함께 있는 설정 · 토큰 재발급 뒤 손 설정 유지 · Desktop 켠 채 실행

## 10-20 (2) 인증서 따로 받기 · 직접 설정 안내(사용자 요청)
- [x] 인증서 내려받기 버튼 — 배치 버튼 옆 · 발급 전 '포털 인증서' 칸(받아서 PEM 확인 뒤 저장)
- [x] 직접 설정 안내 여섯 — 생성기 `certGuide`(배치와 같은 경로 · 같은 묶음 본문), 배치 산출물 바이트 동일 확인
- [x] 화면 수동 조각이 배치와 같은 묶음(`hwax-ca-bundle.pem`)을 가리킴
- [x] 시험 31 통과(새 5 — ③ 은 사설 CA https 서버에 실제로 돌린다), 변이 다섯 잡힘 · 화면 캡처(발급 전 · 발급 직후, 임시 포털)
- [x] 화면 빌드 · Drive · 업데이트 이력 — 빌드 표식 = `HEAD:frontend`(커밋 뒤 다시 빌드), Drive `images-20261020-074433Z` + `latest/`
- [ ] 실제 Windows 확인(사람): ② 를 PowerShell 창에 붙여 넣어 묶음이 생기는지 · ③ 이 OK HTTP 200 인지
