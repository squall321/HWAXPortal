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
- [ ] HP-22 check-egress — nginx 전용 라우트 빼기 · 게이트웨이 목적지는 `/health` 보정 결과(HG-18 뒤)
- [ ] HP-23 check-egress — 선언 플랫폼 mcp_url 호스트
- [x] HP-35 AIDH merge 뒤 페르소나 미리보기 → ✗ · + · ~ 면 warn(덤 — MX 백서 운영자 정본을 needs_tool 로 고침, 미리보기가 dev 에서 멈춰 있었다)
- [x] HP-39 env 킷 DELIB_TIMEOUT_S 주석(킷 줄을 주석으로 — 심지 않는다)

## 2. 에이전트서버

- [ ] HA-01 무캡 경로 절단이면 q_key · pin_key 를 캐시 키에(또는 원본만 캐시하고 _select_tools 매 턴) — HA-21 도 함께
- [ ] HA-02 `_ONTO_CORE` 늘 묶기(보이는 것만)
- [ ] HA-03 SYSTEM_PROMPT 코어 규칙 일곱 줄(⑥ 의 시험 앱 문구는 D-1 — 라벨 바로잡기라 넣지 않음)
- [ ] HA-04 `_cap_tool` 허브 응답 접기
- [ ] HA-05 패널 전용 도구 정확한 이름 집합으로 막기(`*panel*` 금지 — risk_list_panels)
- [ ] HA-06 남의 이어하기는 시작 인자 파일을 쓰지 않는다
- [ ] HA-08 위키 꺼지면 `_wiki_submit` 건너뜀 · 다단은 한 번
- [ ] HA-24 챗 경로 plm_defect_search enrich 기본 0(D-3)
- [ ] HA-13 `/health` self_check
- [ ] HA-07 토큰화 잡음 · IDF · 앱 라벨 적중은 앱 지목 때만
- [ ] HA-09 끊긴 라운드 체크포인트에서 이어하기
- [ ] HA-10 잡 폴더 0700 · 원장 0640
- [ ] HA-12 자기검증 도구 없는 턴 ② 빼기 + 회귀 시험
- [ ] HA-14 자기검증 검토 입력 상한 · 패치(ms p95 뒤)
- [ ] HA-15 질문 언어로 답(기본 한국어 · 중국어 전환 금지)
- [ ] HA-16 도구 의미 색인 서명별 LRU
- [ ] HA-17 좌석 그림 판독 전용 env + `/health`
- [ ] HA-18 긴 카드 절단점을 빈 줄로
- [~] HA-11 as_of — AIDataHub AD-07 뒤
- [~] HA-19 SIM 카드 표 — '나중에'
- [~] HA-20 `ui_resource` SSE — HG-07 뒤(2단계)
- [-] HA-23 '(시험)' 앱 — D-1 라벨 바로잡기(박스, 코드 없음)
- [-] HA-25 이름 가림 — D-4 원천(FailureTrace DP-08)

## 3. 게이트웨이

- [ ] HG-01 search_tools — 온톨로지 동의어 · quality/voc 가중 · 쓰기 감점 · 정본 하나(same_in) · 앱 라벨 가중
- [ ] HG-02 ODB 토큰을 헤더로(이어받기는 헤더 먼저 · 옛 쿼리도) + 시험 → 포털 HP-28
- [ ] HG-03 401 · `_token_rejected` 일 때만 재발급 · `_user_pat(stale=…)`
- [ ] HG-04 REST 중계 simflow · 위층 401 이면 캐시 버리기 · `X-Gateway-Token-Evicted`
- [ ] HG-06 감사 — error 키 · isError 면 ok=false
- [ ] HG-05 tool_areas — 코어 정규식 → knowledge · apps 기본값 · include_tools=false 를 영역 요약에도
- [ ] HG-07 `_meta` 옮기기 · resources 처리기(1단계 중계)
- [ ] HG-20 나가는 응답 개인정보 기본 가림(D-2)
- [ ] HG-09 404 부정 캐시 · 상태 바뀔 때만 로그 · since
- [ ] HG-10 list_tool_apps needs_connect
- [ ] HG-11 graceful shutdown → 포털 HP-25
- [ ] HG-12 search_tools 응답 요약 · required 만
- [ ] HG-13 안내문 유사도 수치를 모델 무관하게
- [-] HG-19 '(시험)' 앱 — D-1 라벨 바로잡기

## 4. 포털 업로드 · 화면 · 그 밖

- [ ] HP-02 RA 목적지 max_bytes(기본 25MB) · 미리 막기 · 413 · 패널이 RA detail 을 보임 + 안내
- [ ] HP-03 보내기 실패 감사 status=failed · 서버 로그 한 줄
- [ ] HP-14 DRM 머리 `3C 23 23 20 4E 41 53 43 41`
- [ ] HP-16 위키 꺼지면 버튼 · 심의 옵션 숨김(켜짐 신호) · 409 문구
- [ ] HP-29 AIDH inbox 사본 지우기
- [ ] HP-30 칩 H1 임시 이름
- [ ] HP-31 extractedBy 'aidh-convert'
- [ ] HP-32 마지막으로 성공한 도구 지도를 계속 쓴다
- [ ] HP-05 sqlite 600(umask) · 연결 토큰 암호화(D-5)
- [ ] HP-48 절차 사전 점검 — 선언 플랫폼 토큰(D-7)
- [ ] HP-15 SimFlow 목적지(HG-04 뒤)
- [ ] HP-41 StartPicker 「전체 보기 →」
- [ ] HP-21 카드 본문 검색 문구(스위치에 맞춤)
- [ ] HP-19 페르소나 정본 접두 이름(또는 동기화가 풀기)
- [ ] HP-20 he-data-coreontology
- [ ] HP-24 §7 스모크가 self_check(HA-13 뒤)
- [ ] HP-25 update-sites 재기동 순서(HG-11 뒤)
- [ ] HP-28 ODB 헤더 꼴 기대 시험(HG-02 뒤)
- [ ] HP-36 대화 검색 표지 기동 때 채움
- [ ] HP-37 embedder 절차서 8절
- [ ] HP-38 리스크 자격 절차서 기대값
- [ ] HP-40 점검표 경로
- [-] HP-49 웹 좌석 20 그대로(D-8)
- [-] HP-10 MX 백서 `--reload` — MX 백서 MW-03 이 고쳤다(APP_ENV=development 일 때만 --reload, 10-28 그쪽 알림) · 포털 할 일 없음
- [~] HP-33 X-Workspace-Slug — RA RP-01 회신 뒤
- [~] HP-34 DRM 버튼 하나 — 정보보호 지침(우리 몫) 뒤 · 보류
- [~] HP-42 MCP Apps 패널 호스트 — HG-07 · HA-20 뒤(2단계)
- [~] HP-50 RA 회수 창구 — RA RP-02 뒤

## 5. 질문 답(answers.md)

- [ ] HP-43 · HP-44 · HP-45 · HP-46 · HG-14 · HG-15 · HG-17 · HG-18 · HA-21 · HA-22

## 6. 리스크 앱(07) — 검토만(사용자 「별도로 검토」)

- [x] review-07-hwax-risk.md — 항목마다 코드 대조 · 몫(앱 백엔드 · 화면 세션 · 포털 · 박스) · 권하는 길

## 7. AIDataHub(10) — 검토만(사용자 「별도로 검토」)

- [x] review-10-AIDataHub.md — AD-01 ~ AD-18 코드 대조 · 요청서에 없는 발견 N1 ~ N5 · 줄 번호 대응표
- [x] AD-16 포털 문서 몫 — `docs/embedder-bge-m3/checklist.md` B6 에 cae00 전환(10-17 11:15) 반영
- [ ] 사용자 결정 — AD-17(정기 동기화를 다시 켤지, 검토자 권고 (나)) · AD-18(글 없는 MX 백서 카드를 내릴지, 권고 (나)). AD-01 의 원인 가르기 질의는 결정과 상관없이 먼저(AIDataHub · 박스 운영)
