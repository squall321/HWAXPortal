# 10-17 사용자 결정 · cae00 리뷰 후속 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

- [x] 결정 받기 — 여섯 묶음(34) + 리뷰 넷 = 38(10-17) · 리뷰 판정(PLAN 2절)

## 묶음 A — 보안 · 자료 보호 · 리뷰 결함
- [x] 게이트웨이 G1 — httpx 로거 WARNING · 우리 로그의 토큰 쿼리 가림 → 시험 · push(`5e867e9`) · dev 재기동(10-17 — services.py 로, 요청 줄 0 · 토큰 값 0)
- [x] 게이트웨이 G2 — 조사만(같은 이름 행을 덮어써 옛 토큰은 무효 · 쌓이지 않는다 — `5e867e9` 본문)
- [x] 포털 P1 — 서비스 로그 덧붙여 쓰기 · 디렉터리 700 · 파일 600(`f57d9b0`)
- [x] 포털 결정 25 · P4 — update-all 이 `.env` 백업을 stash 에 쓸어 넣지 않게 · stash 알림에 추적 안 되는 파일도(`7b6d8f1`)
- [x] 포털 P5 · P6 · P8 · P9 — 재기동 생략 문구 · 스모크 인자 검증 '건너뜀' · 7단계 도구 수 · 꺼진 이미지 · 미러 ○(`1a4ec9d` · `e908b62` · `3b88ea7` · `b9e9f55` · HEAXHub `d933c0b`)
- [x] 포털 P3 — 챗 LLM 안내서 '키는 없다' 바로잡기 · 3.5c 의 401(`ec044e4`)
- [x] 리스크 백업(결정 2) — HEAXHub 백업이 평문 DB 를 뺀다(`b4f01fc`) · 래퍼(HWAXRisk `ba8723c`) · age(dev 사용자 공간) · 키 · dev 매일 03:30 · 풀어 보기 · cae00 절차서(server-setup.md 4절)
- [x] 지식 리포 묶음(결정 3) — ExpertAgents · ExpertGrounding bundle + 커밋 안 된 변경 → Drive 매일 04:20(`1f36e0f` · 되살려 대조)
- [x] 데이터허브(결정 4 · 24) — API 127.0.0.1(dev 박스 · 예시 `4edf1c1`) · PG 30분 시한(dev 10-17) · cae00 절차(AIDataHub README 'PG 안전망' `a488600`)
- [x] 데이터허브 H1 · H1-b · H2 · H3 · H4 → 시험 · push · dev 반영(`a7a2ee4` · `722d7a0` · `86e485a` · `72d38eb` · `fc94747` · 포털 update-all §3 `2a24e7d` — dev API 재기동 10-17, 부팅 깨끗) · H5 기록(`a488600`)
- [x] 에이전트 서버 A1 · A2 · A3 → 시험 · push(`19a04e8` · `ea64c4d`) · dev 재기동(10-17 — 심의 0 확인 뒤)
- [x] HEAXHub X1 · X2 · X3 · X4 · 로그 이어쓰기 · Caddy 로그 회전(결정 16) → 시험 · push(`cf6d5f3` · `28154f1` · `9e670de` · `36a8b1d`)
- [x] MXWP 전체 정지 줄(결정 16 · `095f8e9`) · AIDataHub uvicorn 로그 이어쓰기(`81a6c7c`) · KooRemapper K1(`5926914`) → push
- [x] 사내 IP 킷(결정 1) — env-kits 를 박스 값으로(@NO_PROXY@) · 가드 0(`3b85873`)
- [x] 문서 — P2(`a42da84` · AIDataHub `99cae7b`) · P7(리스크 M3 절차서) · 결정 기록(확정 27 · 닫기 7 · 계획 문서 맞춤 · B7 · D5 · D6 사본 — `7fae400`) · VOC · REST(배포 가이드 10-17 절) · cae00 절차서(`52b1ec8`)
- [x] 요청서 — StepForge X5 · DynaForge 제출 권한 확인(결정 8) · MaterialTwin 데이터 정리(리뷰 4절) — requests.md(`2e2a352`)
- [x] 옛 사본 목록(결정 17) → 사용자 확인(10-18 '목록대로 모두') → 삭제 — 29개 · 24.0GB, 지우기 직전 다시 대조(꼴 · 링크 · 쥔 프로세스) 뒤 실패 0

## 묶음 B — 기능
- [x] 토큰 읽기 · 쓰기(결정 5) — 게이트웨이 `ffb5292`(scopes 가 read 만이면 허용 목록 `read_tools.json` 26종 · readOnlyHint · 자체 조회만, REST 다리 GET · HEAD 만, `save_conversation` 거부) · 리스크 앱 주석 `5833db9`. 챗 우회는 그대로. dev 게이트웨이 재기동 10-18 01:22(services.sh — `GATEWAY_AUDIT` 그대로)
- [x] 허브 앱 개방(결정 7) — HEAXHub `fc1ab89`(관문이 포털 PAT — JWKS kid · aud heax-hub · scope api · exp · sub · jti 필수 · 폐기 목록 60초 · 한 번도 못 읽으면 503 → 이메일로 허브 사용자(없으면 403 '허브에 한 번 로그인') → `can_view_app`, 읽기 PAT 는 GET · HEAD) · 진입 토큰 필수 클레임 `c168772`(jose 결함, FU-D19) · 감시 `74fa732`(FU-D19). dev 백엔드 재기동 10-18 01:24 · 실검증(폐기 목록 주소 · 292건 · 모르는 kid 401)
- [x] 같은 소속 심의 열람(결정 6) — 에이전트 서버 `9d4c931`(상태 · 결과 · 발언 · 이어하기 · 목록 — 주인 · 같은 소속 · 관리자 · 신원 없는 내부, 잡에 `owner_aff`) · 게이트웨이 `ab34abd`(`x-hwax-affiliation`). dev 에이전트 서버 재기동 10-18 01:28 · 실검증(내부 15건 · 다른 소속 0건)
- [x] 그림 인식 V-1 · V-2(결정 10) — 10-18 docs/chat-depth-context T5 로 했다(에이전트 서버 `0b2f8b6` · 포털 `2ff8dc0`, 심의 그림까지)
- [x] 도구 검색 재측정 · 질의 수집(결정 21) — 재측정 `686b42c`(그대로 끈다) · 질의 수집 `a17fc83`(이름 없이 30일, dev 는 10-18 01:22 부터) · 150쌍 검토 화면 https://claude.ai/artifact/MsLjvDFr3oMJsUXZbwavob (표시는 그 저장소 `marks/<쌍 id>`) · 되돌리기 `e617012`(`tool_search_eval/apply_review.py`)
- [x] T1 cae00 절차(결정 11) — 10-18 `server-setup.md` 7절(재기 · 판정 · 켜기 · 되돌리기). 재기 전 A/B 러너 결함 넷을 고쳤다(에이전트 서버 `3ca9894` — 결정문을 못 잡음 · 기본 주소 :8000 · 프록시 · 재는 심의가 RA 초안을 남김). 실행 · 판정은 사람(cae00)

## 묶음 C — 바로 할 수 있는 것(10-19 사용자 '바로 할 수 있는 것들은 다 하자')
- [x] logrotate 편입(FU-D11 의 뒤) — 회전 직전 가드 `infra/logrotate/append-guard.sh`(쥔 프로세스가 모두 O_APPEND 일 때만, 아니면 그 로그만 건너뜀) · 템플릿 (C) 묶음(HEAX backend · worker · beat · AIDH uvicorn · `/tmp/hwax-services/*.log`) · 시험(진짜 logrotate). dev 렌더 · 허브 백엔드를 `>>` 로 다시 띄움(10-19 06:00 KST) — 셋 다 가드 통과. cae00 은 `HWAX_LOGROTATE=1` 이면 update-all 이 렌더한다(옛 fd 를 쥔 쓰기자는 가드가 건너뛴다)
- [x] 포털 PAT 로 `/mcp-gw/api/<사이트>/…` HTTP 경로(one-token 42) — 10-19 통한다 · 읽기 전용 PAT 의 쓰기는 HTTP 길에서도 403(결정 5). PAT 는 dev 가짜 로그인 세션으로 정상 발급(CSRF 이중 제출 그대로) · 하루짜리 · 끝나고 폐기
- [x] MXWhitePaper dev 시험 401 — 원인 · 고침 → 08-19 `b5b199c` 가 dev admin 폴백 기본을 닫은 뒤 시험 380여 건이 깨져 있었다. MXWP `051acc3`(시험 프로세스에서만 켬 · 닫힌 기본값 시험) · lat `ac629d0` — 전체 1204 통과
- [x] 전문가 검색 — 늘 거절되는 두 좌석 · 임베딩 없는 카드 9% → 임베딩 밀림은 이미 풀림(절 431 · 0.04%) · `encode_many` CPU 폴백 AIDataHub `ac42bc6` · 두 좌석 태그 조건 비움(VOC 히트 0 → 2 · 4, 백서 0 → 10 — 백서는 사용자 '비운다' 뒤, FU-D23)
- [x] 감시 보강(사용자 결정 10-19 '감시 보강만', FU-D24) — 포털 `services.py heal`(매니페스트 `watch: true` 다섯 · 포트 연결 거부 세 번일 때만 down · up · 백오프 · update-all 동안 건너뜀) · `install-watchdog.sh` · update-all 은 `HWAX_WATCHDOG=1` 일 때만(꺼져 있으면 ○ 로 남김) · dev 크론 설치 · searxng 로 끝까지 확인. KooRemapper 감시가 MCP 연결도 본다(`559f582`). smarttwin-mcp 는 dev systemd drop-in `Restart=always`

## 사람 몫(cae00 · 사용자)
- [x] 150쌍 검토(검토 화면) — 표시가 끝나면 Claude 에게 '검토 표시를 되돌려' → 내려받기 · `apply_review.py`(먼저 보고 `--write`) · 재측정 — 걷음: request-1029 E-9 ② 가 정답 달기를 포털 '도구 검색 검토'(관리 → 박스의 pairs.local.jsonl)로 바꿨다(docs/request-1029/PLAN.md:89 · server-setup.md:161-162) — 사람 몫은 request-1029 server-setup 7.3 (10-31 정리)
- [x] 30일 뒤(첫 줄 날짜 + 30일) — 모은 질의(`queries.local.jsonl`)에 정답을 달아 `source: usage` 로 재측정 · RRF 판정(cae00 · dev 각자) — 걷음: 질의 모으기가 일회성 30일에서 굴러가는 창(날짜별 queries-<날>.local.jsonl · 기본 30일 — HWAXMcpGateway gateway.py:2808-2814)으로 바뀌었다 — 정답 달기는 request-1029 server-setup 7.3, RRF 판정은 improvement-1015 4번 줄 (10-31 정리)
- [ ] cae00 update-all 뒤 묶음 B 확인 — `server-setup.md` 8절
- [ ] stcx LLM 잡 만료 — **11-14 전** `~/stcx-llm/llmctl.sh rolling`(리뷰 4절)
- [ ] cae00 — 옛 stash 확인 뒤 drop · PG 시한 한 줄 · 리스크 백업 키 · 데이터허브 바인드 확인

## 마무리
- [x] 업데이트 이력 · CLAUDE.md 문서 표 · 메모리 — 10-18 묶음 B(포털 `3ae79f5` · `5323e08`)
