# 10-27 수정 요청 — 체크리스트

`[x]` 끝 · `[~]` 조건부(까닭) · `[-]` 하지 않음(결정) · `[ ]` 남음. 원문은 01 · 02 · 03 · 07(검토만). 결정은 context-notes.

## 1. update-all 안전

- [x] HG-08 heax PAT — 새것을 받은 뒤 옛것을 지운다(발급 실패 시 직전 토큰 · 백엔드 수 그대로 — 시험)
- [x] HP-09 heax 재검증 — 키가 아니라 heax 백엔드 수 · token · servers_url
- [x] HP-08 repair_mcp 앞 `hwax_delib_busy` — 바쁘면 건너뜀(선택: 지금 config 의 HEAX_MCP_TOKEN 넘기기)
- [x] HP-06 헬스게이트 도구 지도를 파일로(세 곳) · python 실패를 ⚠ 로
- [x] HP-07 TOOL_MAX 를 덮지 않는다 · ok 문구는 `/health` tool_cut
- [x] HP-01 KooRemapper 재기동 표지 `$DATA_DIR/deploy.lock.d`(PID, trap 으로 지움) — 감시 쪽은 KooRemapper KR-04(`f1ab307` — 첫 칸만 · 잠금은 /proc/locks)
- [x] HP-04 backup-local — XDG_RUNTIME_DIR · DBUS_SESSION_BUS_ADDRESS 스스로 채움(박스 crontab 두 줄 OB-75 는 감시를 본 뒤 — context-notes)
- [x] HP-17 비밀 백업 — portal/infra · portal/backend 로 나눔 + 박스 파일 · exclude · crontab · 리스크 secrets.env · origin.json(연결 토큰 키 D-5 는 HP-05 커밋에서)
- [x] HP-18 `--install-cron` · `install-logrotate` — 'no crontab' 만 빈 목록, 그 밖 실패는 멈춤(같은 꼴 install-watchdog · datamigrate 도)
- [x] HP-11 services.py Popen 에 `infra/.env` 의 NO_PROXY 리터럴(start.sh 와 같은 합집합 · 감시 · 부팅 유닛도 이 길)
- [x] HP-12 nginx `/ste/` read timeout 손잡이 `NGINX_STE_READ_TIMEOUT` + 시험(nginx -t 까지 — 박스는 OB-80 한 줄)
- [x] HP-13 nginx `simflow` · `stcx-llm` 갈래
- [x] HP-47 `/ste/` 결과 파일 연결 · 속도 제한 손잡이(기본 끔 — D-6, 결과 파일 경로에만)
- [x] HP-26 PER_USER_SSO_APPS 앱의 /verify 도 확인(verify 없는 앱은 ○ — dev MX 백서)
- [x] HP-27 install-ste-tunnel `--check` — 15812 없으면 0 아님
- [x] HP-22 check-egress — nginx 전용 라우트 빼기 · 게이트웨이 목적지는 `/health` 보정 결과(게이트웨이 519358f — HG-18)
- [x] HP-23 check-egress — 선언 플랫폼 mcp_url 호스트(박스 권한표 connect: — 게이트웨이 목적지로 센다)
- [x] HP-35 AIDH merge 뒤 페르소나 미리보기 → ✗ · + · ~ 면 warn(덤 — MX 백서 운영자 정본을 needs_tool 로 고침, 미리보기가 dev 에서 멈춰 있었다)
- [x] HP-39 env 킷 DELIB_TIMEOUT_S 주석(킷 줄을 주석으로 — 심지 않는다)

## 2. 에이전트서버

- [x] HA-01 무캡 경로 절단이면 원본 목록을 쥐고 턴마다 다시 고른다(게이트웨이 재호출 없음) — HA-21 도 함께(에이전트 45cd6ff)
- [x] HA-02 `_ONTO_CORE` 늘 묶기(보이는 것만 · 운영자 빼고 — 35b8478)
- [x] HA-03 SYSTEM_PROMPT 코어 규칙 일곱 줄(⑥ 의 시험 앱 문구는 D-1 — 라벨 바로잡기라 넣지 않음 — cccab32)
- [x] HA-04 `_cap_tool` 허브 응답 접기(칸 모양은 요청서 설명 — 실물 대조는 cae00 — 2a50cf3)
- [x] HA-05 패널 전용 도구 정확한 이름 집합으로 막기(`*panel*` 금지 — arp_upload_open 은 실측 없어 넣지 않음 — c02e05e)
- [x] HA-06 남의 이어하기는 시작 인자 파일을 쓰지 않는다 · 원 주인의 이어하기를 남긴다(3e7f00b)
- [x] HA-08 위키 꺼지면 `_wiki_submit` 건너뜀 · 다단은 한 번(8d519ec)
- [x] HA-24 챗 경로 plm_defect_search enrich 기본 0(D-3 — 1b42bbd)
- [x] HA-13 `/health` self_check(1b96a15)
- [x] HA-07 토큰화 잡음 · IDF · 앱 라벨 적중은 앱 지목 때만(504c150)
- [~] HA-09 끊긴 심의 체크포인트에서 이어하기 — 다단(해석 설계 · 구축 계획)의 단 경계는 했다(4c67229). 단 안 · 한 단 심의의 끊긴 라운드를 좌석 단위로 잇는 것은 라운드 실행 구조를 바꾸는 일이라 남음
  - [x] S0 반대 검토 10-31 — 재기동 겹침 고침 셋(에이전트 wt1031/ha09s0 `41408d8` · `5f9cca5` · `a25dfa6` — start.sh 가 옛 프로세스가 끝난 뒤 띄운다 · 종료 신호에서 줄을 닫는다 · 남이 닫은 원장을 덮지 않는다), '2초 뒤 kill -9' 전제를 바로잡은 글(설계서 A2.3 · A7 정정, 킷 · README)
  - [ ] A-7 재기동 때 흐르던 웹 챗 답 — 1초 상한이 끝까지 가던 답을 끊는다. 그대로 둘지 · 챗을 기다릴지(새 서버가 그만큼 늦게 뜬다) 사람 결정 대기
- [x] HA-10 잡 폴더 0700 · 원장 0640 · 상태 0600(b6e90c4)
- [x] HA-12 자기검증 도구 없는 턴 ② 바꾸기 + 회귀 시험(89d4f69)
- [~] HA-14 자기검증 검토 입력 상한 · 패치 — 상한은 ms p95 를 모은 뒤 정한다(HA-13 의 /health self_check 가 모은다)
- [x] HA-15 질문 언어로 답(기본 한국어 · 중국어 전환 금지 — 83b4927)
- [x] HA-16 도구 의미 색인 서명별 LRU(4 — 862ea74)
- [x] HA-17 좌석 그림 판독 전용 env `DELIB_SEAT_VISION_MAX` + `/health` seat_vision(f01286e)
- [x] HA-18 긴 카드 절단점을 펜스 · $$ 밖의 빈 줄로(44f3d20)
- [~] HA-11 as_of — AIDataHub AD-07 뒤
- [~] HA-19 SIM 카드 표 — '나중에'
- [~] HA-20 `ui_resource` SSE — HG-07 뒤(2단계)
- [-] HA-23 '(시험)' 앱 — D-1 라벨 바로잡기(박스, 코드 없음)
- [-] HA-25 이름 가림 — D-4 원천(FailureTrace DP-08)

## 3. 게이트웨이

- [x] HG-01 search_tools — 온톨로지 동의어 · quality/voc 가중 · 쓰기 감점 · 정본 하나(same_in) · 앱 이름 가중(게이트웨이 93cda53 — dev 147쌍 doc hit@1 0.475 → 0.550)
- [x] HG-02 ODB 토큰을 헤더로(이어받기는 헤더 먼저 · 옛 쿼리도) + 시험(ecde6e2 · 계약 dccb620) → 포털 HP-28
- [x] HG-03 401 · `_token_rejected` 일 때만 재발급 · `_user_pat(stale=…)`(c605b84 — 진짜 MCP 클라이언트로 401 꼴 실측)
- [x] HG-04 REST 중계 simflow · 위층 401 이면 캐시 버리기 · `X-Gateway-Token-Evicted`(ce31ed1)
- [x] HG-06 감사 — 오류 봉투면 ok=false · 사유(be7570f — 포털 판정기를 오라클로)
- [x] HG-05 tool_areas — 코어 정규식 → knowledge · apps 기본값 · include_tools=false 를 영역 요약에도(7845ccf)
- [x] HG-07 `_meta` 옮기기 · resources 처리기(bbd5c87 — ui:// 만, 메모리 전송 왕복 시험) — 확인은 cae00 Desktop(사람)
- [x] HG-20 나가는 응답 개인정보 기본 가림(D-2, 2a2cba6 — 칸 이름 · IMEI Luhn, 끄기 GATEWAY_PII_MASK=0)
- [x] HG-09 목록 계정 백오프 60 → 600초 · 상태 바뀔 때만 로그 · `/health` conn_since(bde1017)
- [x] HG-10 list_tool_apps needs_connect(5fe6ea0)
- [x] HG-11 graceful shutdown(177c22a — 실물 SIGTERM 0.11초에 포트, 진행 중 요청 200) → 포털 HP-25
- [x] HG-12 search_tools 응답 요약 · required 만 · 선택 인자 이름(93cda53, detail=true 면 전문)
- [x] HG-13 안내문 유사도 수치를 모델 무관하게(9bb5b17)
- [-] HG-19 '(시험)' 앱 — D-1 라벨 바로잡기

## 4. 포털 업로드 · 화면 · 그 밖

- [x] HP-02 RA 목적지 max_bytes(기본 25MB) · 미리 막기 · 413 · 패널이 RA detail 을 보임 + 안내(2043930)
- [x] HP-03 보내기 실패 감사 status=failed · 서버 로그 한 줄(2043930)
- [x] HP-14 DRM 머리 `3C 23 23 20 4E 41 53 43 41`(2043930)
- [x] HP-16 위키 꺼지면 버튼 · 심의 옵션 숨김(켜짐 신호) · 409 문구(138970f)
- [x] HP-29 AIDH inbox 사본 지우기(2043930 — 장부 · 24시간, 옛 사본은 사람이 한 번 · OB-10)
- [x] HP-30 칩 H1 임시 이름(2043930)
- [x] HP-31 extractedBy 'aidh-convert'(2043930)
- [x] HP-32 마지막으로 성공한 도구 지도를 계속 쓴다(2043930)
- [x] HP-05 sqlite 600 · 연결 토큰 암호화(D-5)(f2ffa60 — 키 backend/secrets/conn.key · 비밀 묶음 · 시험 격리)
- [x] HP-48 절차 사전 점검 — 선언 플랫폼 토큰(D-7)(3e020aa)
- [x] HP-15 SimFlow 목적지(ff585d2 — 사이트 PAT · 설정 확장자 · drm_pending 기다림, 계약 확인은 cae00 첫 실주행 · PA-12)
- [x] HP-41 StartPicker 「전체 보기 →」(a05fbda)
- [~] HP-21 카드 본문 검색 문구 — 보류: 화면이 AIDataHub 스위치(`AIDH_RECORDS_Q_BODY_SEARCH`)를 볼 길이 없다. OB-89 로 켤 때 맞추거나 AIDH 가 응답에 스위치 상태를 싣게 청한다
- [x] HP-19 페르소나 정본 접두 이름(42e6648 — 접두 별칭, 동기화가 풀기는 고르지 않음)
- [x] HP-20 he-data-coreontology(62ed7b2 — dev 는 허브가 없어 건너뜀, `--apply` 는 cae00 사람)
- [x] HP-24 §7 스모크가 self_check(847c403)
- [x] HP-25 update-sites 재기동 순서 — 고칠 것 없음(down → 리스너 닫힘 → up 이 HG-11 과 맞물린다, 회귀 시험 게이트웨이 054d397)
- [x] HP-28 ODB 헤더 꼴 기대 시험(40f6b76) · 옛 쿼리 꼴이면 재프로비저닝을 한 번 당긴다(92ae8d7)
- [x] HP-36 대화 검색 표지 — 첫 색인 전에 한 번 묻는다(075472f)
- [x] HP-37 embedder 절차서 8절(78ed68c)
- [x] HP-38 리스크 자격 절차서 기대값(78ed68c)
- [x] HP-40 점검표 경로 — 점검표는 요청한 쪽 것이라 cae00 가이드에 확인 길 · /health/ready claims_affiliation(0eb5041)
- [-] HP-49 웹 좌석 20 그대로(D-8)
- [-] HP-10 MX 백서 `--reload` — MX 백서 MW-03 이 고쳤다(APP_ENV=development 일 때만 --reload, 10-28 그쪽 알림) · 포털 할 일 없음
- [~] HP-33 X-Workspace-Slug — RA RP-01 회신 뒤
- [~] HP-34 DRM 버튼 하나 — 정보보호 지침(우리 몫) 뒤 · 보류
- [~] HP-42 MCP Apps 패널 호스트 — HG-07 · HA-20 뒤(2단계)
- [~] HP-50 RA 회수 창구 — RA RP-02 뒤

## 5. 질문 답(answers.md)

- [x] HP-43 · HP-44 · HP-45 · HP-46 · HG-14 · HG-15 · HG-17 · HG-18 · HA-21 · HA-22 — `answers.md`(HP-44 는 고침 099eff2 · HP-45 는 주석 0b787d5)

## 6. 리스크 앱(07) — 검토만(사용자 「별도로 검토」)

- [x] review-07-hwax-risk.md — 항목마다 코드 대조 · 몫(앱 백엔드 · 화면 세션 · 포털 · 박스) · 권하는 길

## 7. AIDataHub(10) — 검토만(사용자 「별도로 검토」)

- [x] review-10-AIDataHub.md — AD-01 ~ AD-18 코드 대조 · 요청서에 없는 발견 N1 ~ N5 · 줄 번호 대응표
- [x] AD-16 포털 문서 몫 — `docs/embedder-bge-m3/checklist.md` B6 에 cae00 전환(10-17 11:15) 반영
- [ ] 사용자 결정 — AD-17(정기 동기화를 다시 켤지, 검토자 권고 (나)) · AD-18(글 없는 MX 백서 카드를 내릴지, 권고 (나)). AD-01 의 원인 가르기 질의는 결정과 상관없이 먼저(AIDataHub · 박스 운영)
