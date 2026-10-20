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
- [ ] 화면 빌드 · Drive · 업데이트 이력
- [ ] 실제 Windows 확인(사람 — 염종섭 님): Store 판 · NO_PROXY/no_proxy 가 함께 있는 설정 · 토큰 재발급 뒤 손 설정 유지 · Desktop 켠 채 실행
