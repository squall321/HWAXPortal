# 10-17 사용자 결정 · cae00 리뷰 후속 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [x] 결정 받기 — 여섯 묶음(34) + 리뷰 넷 = 38(10-17) · 리뷰 판정(PLAN 2절)

## 묶음 A — 보안 · 자료 보호 · 리뷰 결함
- [x] 게이트웨이 G1 — httpx 로거 WARNING · 우리 로그의 토큰 쿼리 가림 → 시험 · push(`5e867e9`) · dev 재기동은 아래 '반영'
- [x] 게이트웨이 G2 — 조사만(같은 이름 행을 덮어써 옛 토큰은 무효 · 쌓이지 않는다 — `5e867e9` 본문)
- [x] 포털 P1 — 서비스 로그 덧붙여 쓰기 · 디렉터리 700 · 파일 600(`f57d9b0`)
- [x] 포털 결정 25 · P4 — update-all 이 `.env` 백업을 stash 에 쓸어 넣지 않게 · stash 알림에 추적 안 되는 파일도(`7b6d8f1`)
- [x] 포털 P5 · P6 · P8 · P9 — 재기동 생략 문구 · 스모크 인자 검증 '건너뜀' · 7단계 도구 수 · 꺼진 이미지 · 미러 ○(`1a4ec9d` · `e908b62` · `3b88ea7` · `b9e9f55` · HEAXHub `d933c0b`)
- [x] 포털 P3 — 챗 LLM 안내서 '키는 없다' 바로잡기 · 3.5c 의 401(`ec044e4`)
- [ ] 리스크 백업(결정 2) — HEAXHub 백업이 평문 DB 를 뺀다 · age · 키 · dev 매일 03:30 · cae00 절차서
- [ ] 지식 리포 묶음(결정 3) — ExpertAgents · ExpertGrounding bundle → Drive 매일
- [x] 데이터허브(결정 4 · 24) — API 127.0.0.1(dev 박스 · 예시 `4edf1c1`) · PG 30분 시한(dev 10-17) · cae00 절차(AIDataHub README 'PG 안전망' `a488600`)
- [x] 데이터허브 H1 · H1-b · H2 · H3 · H4 → 시험 · push · dev 반영(`a7a2ee4` · `722d7a0` · `86e485a` · `72d38eb` · `fc94747` · 포털 update-all §3 `2a24e7d` — dev API 재기동 10-17, 부팅 깨끗) · H5 기록(`a488600`)
- [ ] 에이전트 서버 A1 · A2 · A3 → 시험 · push · dev 재기동
- [ ] HEAXHub X1 · X2 · X3 · X4 · 로그 이어쓰기 · Caddy 로그 회전(결정 16) → 시험 · push
- [ ] MXWP 전체 정지 줄(결정 16) · KooRemapper K1 → push
- [ ] 사내 IP 킷(결정 1) — env-kits 를 박스 값으로 · 가드 0
- [ ] 문서 — ~~P2~~(`a42da84` · AIDataHub `99cae7b`) · P7 · 결정 기록(확정 27 · 닫기 7 · 계획 문서 맞춤 · VOC · REST · 웹 검색 · B7 · D5 · D6 사본)
- [ ] 요청서 — StepForge X5 · DynaForge 제출 권한 확인(결정 8) · MaterialTwin 데이터 정리(리뷰 4절)
- [ ] 옛 사본 목록(결정 17) → 사용자 확인 → 삭제

## 묶음 B — 기능
- [ ] 토큰 읽기 · 쓰기(결정 5) — 게이트웨이 · 리스크 앱 대조
- [ ] 허브 앱 개방(결정 7) — 5 뒤
- [ ] 같은 소속 심의 열람(결정 6)
- [ ] 그림 인식 V-1 · V-2(결정 10)
- [ ] 도구 검색 재측정 · 질의 수집(결정 21)
- [ ] T1 cae00 절차(결정 11)

## 사람 몫(cae00 · 사용자)
- [ ] stcx LLM 잡 만료 — **11-14 전** `~/stcx-llm/llmctl.sh rolling`(리뷰 4절)
- [ ] cae00 — 옛 stash 확인 뒤 drop · PG 시한 한 줄 · 리스크 백업 키 · 데이터허브 바인드 확인

## 마무리
- [ ] 업데이트 이력 · CLAUDE.md 문서 표 · 메모리
