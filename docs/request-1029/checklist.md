# 10-29 웹 챗 온톨로지 QA 후속 — 체크리스트

계획은 [PLAN.md](PLAN.md), 까닭은 [context-notes.md](context-notes.md), 요청서 정본은 [`../request_261029.md`](../request_261029.md).
표기 — [ ] 할 일 · [x] 했다 · [~] 보류(까닭) · [-] 안 한다(까닭).

## 0. 결정(사용자)

- [x] D-1 코어 어휘표 정본 자리 — **포털**
- [x] D-2 시험 사본 — **기본 목록에서 뺀다**(2차로 당김)
- [x] D-3 도구 설명 예산 — **손잡이만 짓고 박스에서 견준다**
- [x] D-4 생각 강도 — **박스에서 견준다**
- [x] D-5 챗 침묵 한도 — **900초**(ping 뒤)
- [x] D-6 본답 출력 상한 — **두지 않는다**(O-11 안 함 · 자기검증 상한은 별개)
- [x] D-7 4차 — **재시험 결과를 보고 정한다**
- [x] D-E5-1 ~ D-E5-8 페르소나 연결(E-5) — **모두 권장안 (가)**(10-31 — [design-e5.md](design-e5.md) 5절, C-41)

## 1차(P0)

- [x] B-1 코어 어휘표 — 포털 `backend/config/core_vocab.json`(C-11 — 형제 리포가 파일로 읽는다) · 꼴 검사 시험 `tests/test_core_vocab.py`
- [x] B-1 게이트웨이 — 형제 파일 읽기(바뀐 시각) · 없으면 지금 동작 · `/health` 의 `core_vocab`(+ `canonical_backend`) · 시험이 실제 파일을 읽는다(HWAXMcpGateway eaee557 · 496eab1)
- [x] B-1 에이전트 — 형제 파일 읽기(바뀐 시각) · 없으면 지금 규칙 글 · 규칙 글 만들기 · `/health` 의 `core_vocab` · 시험이 실제 파일을 읽는다(HWAXAgentServer c8bffc6)
- [x] R-1 · R-7 코어 규칙 발동 낱말 넓히기 · '첫 걸음은 정본 resolve 하나'
- [x] R-2 규칙 ⑦ 에 FMEA · ARP · ODB 허브
- [x] R-8 관계 대응표 한 줄
- [x] R-3 정본 허브 도구 설명 앞 소개 한 줄(게이트웨이)
- [x] R-4 검색 동의어 → 허브 읽기 도구 이름 · 정본 먼저(사본은 정본 한 줄로 접는다 — C-12) · 띄어 쓴 꼴
- [x] R-5 '심의 · 토의 · 회의' 없으면 `deliberate_start` 가중 끔 — **코어 질문에만**(C-13, 그대로 하면 심의 낱말 14쌍 중 7쌍이 밀렸다)
- [x] 게이트웨이 검색 평가에 요청서 시험 질의 8건(가짜 허브 도구 지도) — 상위 5에 정본 읽기 도구 2개 이상 · 기존 147쌍 퇴보 없음 — 일곱이 2개 이상('낙하 해석 담당' 은 코어 낱말이 없다 — C-14), 147쌍은 dev · 합성 카탈로그 모두 그대로
- [x] W-9 자기검증 출력 상한(초안 비례 · 상한에 걸리면 초안)(HWAXAgentServer 85a636a)
- [x] P-1 ① 포털 중계 — 상류 읽기를 브라우저 쓰기와 떼기 · 끝에서 저장 · 퍼밋 · 큐 상한 · 끊으면 상류도 끊기(15c736d)
- [x] P-1 ③ 중지 단추가 화면 상태를 바로 푼다(cf4e1a0)
- [x] 1차 업데이트 이력(기술 변경 포함) · cae00 가이드 · push · 화면 빌드 + Drive(images-20261029-091343Z) — dev 게이트웨이 · 에이전트 · 포털 재기동은 사용자 확인 뒤(다른 세션의 미반영 커밋도 함께 켜진다)
- [ ] cae00 재시험 요청(사람 · cae00 세션)

## 2차(P1)

- [x] R-6 시험 사본 숨김(D-2) — 어휘표 앱 역할 '시험' · 챗 묶음 · 검색 · 개인 Claude 기본 목록에서 빼기 · 이름 부르기는 남김(HWAXMcpGateway ab3fcff, C-18)
- [x] R-9 다른 문자 낱말 → 자기검증(HWAXAgentServer 0c3148b)
- [x] R-10 도구 결과 머리에 앱 이름 · 근거 블록에 앱 이름(HWAXAgentServer d01a53b)
- [x] W-1 챗 LLM 호출에 대화 머리(HWAXAgentServer a478519 · 포털 e02898e, C-21) — 박스 부하분산기는 아래 O-2(사람)
- [x] W-3 고정 몫 맨 앞(이름순 대신 정해진 차례 — C-19) · 바뀌는 안내를 시스템 메시지 밖으로 · 턴을 가로질러 바이트까지 같은지 시험(HWAXAgentServer 8d10cc5)
- [x] W-5 같은 도구 네 번째 알림 · 허브 접기 셋 더(견본 없이 일반 규칙 — C-22) · `invoke_tool` 안쪽 이름(HWAXAgentServer d01a53b)
- [x] P-1 ② 다시 보일 때 서버 사본과 맞추기(bd01b0c)
- [x] P-1 ④ 챗 스트림 ping 15초(HWAXAgentServer 670778f, C-20) · 포털 `agent_chat_idle_timeout_s` 900초(fd49ede)
- [x] 2 · 3 · 4차 업데이트 이력 · cae00 안내(server-setup.md) · push · 화면 Drive(images-20261029-114227Z) · KooRemapper 화면 Drive(dist-20261029-115148Z) — cae00 재시험은 위 1차 줄과 함께(사람)

## 3차(결정 뒤)

- [x] W-2 `CHAT_TOOL_SCHEMA_BUDGET` 손잡이(D-3, HWAXAgentServer 4514199 · env 킷 주석 b16eebc, C-23) — 박스 A/B 는 아래 O-3(사람)
- [ ] W-6 생각 강도 박스 A/B(D-4 · O-4)
- [x] W-4 자기검증 패치 꼴 · 그 뒤 W-9 상한을 4,096 으로(HWAXAgentServer 969e723, C-24) — 요청서의 '건너뛰기 넓히기' 는 SC-D1 을 건드려 묻는다
- [-] W-7 한 턴 MCP 세션 하나 — 이득이 작다(호출당 0.1 ~ 0.3초), 끊김 처리가 새로 생긴다

## 4차(D-7 뒤 — 재시험 숫자가 필요 없는 E-1 · E-3 · E-6 은 사용자 지시 10-29 로 당긴다, C-17)

- [x] E-1 권한표에 행 없는 백엔드 알림(update-all §6) — 이미 있다(10-01 3b61d63 '권한 표 대조' ✗ · 시험 test_update_all_access_table.py, C-25)
- [x] E-2 앱 역할 칸(정본 · 형제 · 시험) — 순위 · 접기 · 노출([design-e2-e4.md](design-e2-e4.md) 1.4 · 사용자 결정 10-31 권장안 그대로 — C-32 ~ C-37)
  - [x] E2-1 역할 읽기 · 보이기 — 가족 · 비코어 · 시험 · `/health core_vocab.roles` · `list_tool_apps` · `/tools-map` · 검색 줄의 `role`(HWAXMcpGateway 9b37b31)
  - [x] E2-2 가족 접기 — 원래 이름으로 한 줄 · `same_in` 의 `differs` · 설명이 같으면 기준본과 바이트까지 같다(같은 커밋, C-34)
  - [x] E2-3 가족은 늘 접두 — 옛 맨 이름은 호출 별칭으로 남기고 알린다(Q-2 — C-33) · 가족 · 형제 소개 줄이 바뀌면 다시 집계(같은 커밋)
  - [x] E2-4 형제 소개 줄 칸 — 게이트웨이(같은 커밋) · 포털 꼴 시험(형제에만 · 120자) · 표 설명(4ebf32e) — 문안은 운영자(아래 사람 몫)
  - [x] E2-5 비코어 낮추기 손잡이 `noncore_demote`(기본 끔 — C-36) · `weights.noncore` 0.5 · `/search-eval` 의 `+noncore_demote` 판(같은 커밋) ·
    피드백 보고서가 감점 규칙을 '보정 덕에만' 에 싣지 않는다(8186d9a) · 검토 화면의 판 · 규칙 이름(462887b)
  - [~] E2-6 형제 순위 신호(S-A) — 미룸(설계 1.4 — cae00 M-5 · M-6 에서 형제가 잘못 오르거나 밀릴 때만)
  - [x] 반대 검토(10-31) 고침 넷 — 비코어 낮추기의 앱 이름에 어휘표 라벨 · 키(C-44, HWAXMcpGateway f9b75c6) · 형제 소개 줄은 순위 밖이고
    접힌 형제가 그 줄을 싣는다 · 가족 밖 사본도 가족 무리로(C-43 · C-45, 2651020) · 표를 못 읽어도 늘 접두의 가족을 쥔다(C-46, 1ff9d74) · README(10bb6ec)
  - [x] Q-2 확인 — 목록에서도 오늘의 맨 이름을 지키나(사용자, C-47 — 지금 판은 접두 이름만 싣고 옛 맨 이름은 호출 별칭이다. 별칭은 이름으로 부르는
    쪽만 지킨다) — 사용자 확인 10-31: 그대로(목록은 늘 접두), cae00 의 바뀐 이름 수는 받은 편지함 2026-10-31 Q14 로 받는다
  - [ ] cae00 반영 뒤 M-2 · M-3 다시 — 바뀐 이름 0(`roles.family_prefixed.count`) · 접힌 줄 그대로(사람 · cae00 세션, server-setup 8절)
  - [ ] 비코어 낮추기 켜기 — cae00 `/search-eval` 의 `+noncore_demote` 판을 본 뒤 박스 덧씌우기(사람, Q-1 · server-setup 8.3)
  - [ ] 형제 소개 줄 문안 — 운영자가 cae00 `core_vocab.local.json` 에(사람, Q-3 — M-8 이 바탕)
- [x] E-3 오래 안 불린 도구 보고(30일 · 앱별) — 게이트웨이 `tool_usage_report.py`(8b6af6d, C-26)
- [x] E-4 개인 Claude 묶음 · 가벼운 모드([design-e2-e4.md](design-e2-e4.md) 2.4 · 사용자 결정 10-31 — C-32 · C-38 · C-39)
  - [x] E4-1 · E4-2 게이트웨이 — 보기 셋을 tools/list 에만(`_listed_tools`) · 머리 > 포털 설정 > 전체 · 웹 챗 · 절차 · GW_TOKEN 은 전체 · `list_tool_apps` 의 `view` ·
    `/health tools_list_by_view`(HWAXMcpGateway 4c17be8)
  - [x] E4-3 포털 저장 · 창구 — `users.hub_view` · `GET · PUT /auth/access/view` · 권한 응답 `view`(b0a050b)
  - [x] E4-4 포털 화면 — 토큰 화면 '허브에 보일 앱' 탭 위 보기 고르기 · 영역 칸 · 알림 넷(2444a89) — 프론트 형식 검사(`tsc -b`) 통과
  - [x] E4-5 리포 `.mcp.json` 보기 머리(늘 full) · mcp-app-toggle PLAN '2단계 대신 보기' · 업데이트 이력 · cae00 안내(server-setup 8절)
  - [x] 반대 검토(10-31) 고침 둘 — 포털 보기는 머리 `X-HWAX-View: portal` 로 청한 연결에만 · 등록 배치 · 명령이 Claude Code · Desktop 에 단다 · 안내가
    그것을 말한다(C-41, 게이트웨이 58f7dad · 포털 68f9d33 · 3680f42) · 게이트웨이가 보기를 모르면 화면이 알린다(C-42, 게이트웨이 0a0a0c0 · 포털 359e71e)
  - [ ] 임시 포털 캡처로 좁은 화면 확인 · 화면 빌드 + Drive(cae00 은 짓지 못한다) — 올릴 때
  - [ ] dev 실검증 — 개인 PAT 로 보기 셋(게이트웨이 · 포털 재기동은 사용자 확인 뒤 — 다른 세션의 미반영 커밋도 켜진다)
  - [ ] cae00 M-3 · M-4(목록 크기 · 개인 PAT 영역 분포) · Q-11(쓰는 클라이언트 · 불편) — 사람 · cae00 세션(설계 5절)
- [ ] E-5 전문가 고르기 기준선(누설 없는 평가셋) → 페르소나 ↔ 분야 ↔ 코어 타입 링크 · AI 데이터 허브 요청서(바인딩 저장소 하나 · 지워진 키) — 설계
  [design-e5.md](design-e5.md), 사용자 결정 D-E5-1 ~ 8 은 모두 (가)(10-31, C-48). 1단계(10-31)는 dev 에서 지을 수 있는 E5-0 · E5-1 · E5-2 · E5-4 다 — 좌석 ·
  도구 · '맡은 사람이 없다' 고르기는 그대로다(관문 G0 전)
  - [ ] E5-0 평가셋 A · P · C(`tools/seat_evalset.py` — dev 에서 짓고 Drive 로, D-E5-8) · A-test 봉인 줄을 design-e5 8절에 — 에이전트 서버 몫. 봉인 줄은 8절에
    적었다(10-31 — L2 이름 거름을 고친 뒤 다시 지은 판, C-55). Drive 로 보내기는 남았다
  - [ ] E5-1 창구 `POST /seat-eval` + 러너 `tools/seat_eval.py`(짝 비교 · McNemar · 갈래 · 판 지문) — 에이전트 서버 몫
  - [ ] E5-2 에이전트 서버 — 박스 파일 `seat_questions`(모으기 기본 꺼짐 `SEAT_QUESTIONS_COLLECT` · 창구 `/seat-questions*` · 다는 사람 `SEAT_QUESTIONS_LABELERS`) — 에이전트 서버 몫
  - [x] E5-2 포털 — 관리자 '전문가 고르기 검토'(`/admin/seat-review`) · 창구 `/auth/admin/seat-review/*`(관리자 · CSRF · 허용 목록 — 순위 · 점수 · 지금 좌석 ·
    표본 질문이 화면에 닿지 않는다) · 지난 날 모으기(대화 저장소 읽기 전용 · 이름 · 메일 · 대화 id 떼기 · 그쪽 스위치가 꺼져 있으면 읽지 않는다) · 계약
    [e5-seat-review-contract.md](e5-seat-review-contract.md)(`seat-review/1` · `seat-questions/1`, C-49) · 시험(누설 단언 · 형제 리포의 진짜 모듈로 한 바퀴 ·
    화면 헤드리스)
  - [ ] E5-2 cae00 — 사용자 허락 · 모으기 켜기 · 다는 사람 둘 정하기 · '지난 날 모으기' · 190건 표시(사람, server-setup 9절)
  - [ ] E5-3 B0 — cae00 결정적 겹 + LLM 겹(사람 · cae00 세션) → 관문 G0 판정을 design-e5 8절에
  - [x] E5-4 포털 — 어휘표 `personas` 칸(첫 판은 자기 앱이 있는 지식 전문가 여덟의 앱 덮어쓰기뿐 — 도메인 줄은 비었다, L7 · C-54) · 꼴 시험 · 형제 리포 대조(조직도 ·
    `types` · 게이트웨이 `tool_areas.json` · 에이전트 서버 `persona_links.validate` 가 한 줄도 버리지 않는다) · 게이트웨이 검색이 읽는 값이 같다(시험 + dev
    카탈로그 162질의 실측 — 답이 바이트까지 같고 어휘표 지문만 바뀐다)
  - [ ] E5-4 에이전트 서버 — 읽기 · 줄마다 검증 · `/health` `core_vocab.personas` · 그림자 기록 — 에이전트 서버 몫
  - [~] E5-5 · E5-6 · E5-7 — 관문 G0 뒤(사용자 결정 10-31). 도메인 줄(`personas.domains`)은 A-dev 와 도메인 검토로 — 연결을 쓰는 사람은 H 를 보지 않는다(L7)
    - [ ] 도메인 줄을 쓸 때 — `personas.domains` · `no_tools` 가 비지 않게 되면 에이전트 서버 형제 대조(`tests/test_persona_links.py` 의 `test_형제_리포_실파일_대조`)가
      '지식 도메인마다 줄 또는 no_tools' 를 저절로 요구한다(첫 판은 빠진 수만 센다 — C-55). 도메인 줄은 한 판에 빠짐없이 쓰고, 포털
      `test_personas_첫_판은_앱_전문가_덮어쓰기만이다` 를 그때 고친다(L7 을 지켰는지 context-notes 에)
  - [x] 반대 검토(10-31) 16건 고침 — L7 가름 · 도구 실패 · 어휘 칸 · 판 지문 · L2 이름 거름(A 다시 지음) · 첫 호출 지연 · 일치도 · McNemar · 그림자 기본 꺼짐 ·
    읽기 전용 · 보존 · 화면 이름 지우기 · id 지우기 · 심의 좌석 · 형제 대조(C-55 — 에이전트 서버 · 포털 wt1031/e5)
- [x] E-7 검색 보정 옵션화 — 손 동의어 · 낱말 묶음 · 가중치를 설정으로(항목마다 owner · source_fix) · 박스 덧씌우기 · 묶음별 끄기 · 덧씌우기 지문(/health · update-all · 평가) · 규칙별 기여 기록 · 평가 '보정 끔' 비교(D-8 — QA 뒤)
- [x] E-8 플랫폼별 피드백 보고서 — 보정 덕에만 찾아진 질의 · 인자 설명 · 안 불린 도구 · 큰 응답 · 실패, cae00 기록으로 cae00 에서 · 고쳐지면 규칙을 걷는다(D-8 — QA 뒤)
- [x] E-9 cae00 닫힌 고리(코드 · 문서 — 16문항 회귀 · 박스에서 켜고 끈 비교는 cae00 사람 몫, server-setup 7.3) — 굴러가는 질의 기록 + '찾기 → 부르기 → 성공' 신호 · 16문항 회귀 · 포털 화면 검토(박스 파일) · cae00 에서 덧씌우기 켜고 끈 비교 · dev 기본값으로 올리기는 선택(D-8 — QA 뒤)
  - [x] ① 게이트웨이 search_tuning.json(지금 상수 그대로) · 박스 덧씌우기 · 묶음별 끄기 · 순위 바이트 같음(_SEARCH_TOOLS_MASTER · 평가 142쌍) — 게이트웨이 1539b5b
  - [x] ② 어휘표 덧씌우기 core_vocab.local.json — 게이트웨이 8dc2719 · 에이전트 ab87137(형제 리포 원문 대조 가드) · 포털 gitignore
  - [x] ③ 지문 — 게이트웨이 · 에이전트 /health · update-all §7(챗 도구 가시성 줄 곁 — 설계의 '§6' 은 자리를 잘못 적었다) · 평가 · 기록
  - [x] ④ 귀속 · boost_only · 날짜별 굴러가는 질의 기록 · 뒤이은 호출 결과 줄 — 게이트웨이 1539b5b(손잡이와 한 커밋)
  - [x] ⑤ 창구 /search-log · /search-review · /search-eval · run.py live — 게이트웨이 1c7fcc1 · 9e9a8c0
  - [x] ⑥ platform_feedback_report.py — 게이트웨이 ed94439(손잡이 지문은 게이트웨이와 같다 — 시험이 맞댄다 · dev 실데이터 0.2초 · 신원 0건)
  - [x] ⑦ 포털 관리자 '도구 검색 검토' 화면 + 백엔드(관리자 · CSRF → 게이트웨이 공유 비밀)
  - [x] 문서(README 셋 · server-setup 7절 · 배포 가이드 10-30 절) · 이력 · push(게이트웨이 f4d9546 · 에이전트 ab87137 · 포털) · 화면 Drive images-20261029-210547Z(임시 포털 캡처로 좁은 화면 표 · 입력칸을 고친 판)
- [x] E-6 새 앱 등록 자동 점검 — update-all §6 '새 앱 점검'(95f9274 · `infra/scripts/app-checks.py`, C-27) · 찾은 DocForge 미분류는 게이트웨이 44f4b8d

## 관련 프로젝트 — 이 박스에서 고칠 수 있는 것(사용자 지시 10-29, C-17)

- [x] StepForge — `find_plm_task` 가 과제의 프로젝트 별칭(마케팅명)으로도 찾는다(OT-15 no_match) — StepForge D-647(C-28)
- [ ] StepForge 운영 결정 셋 · 알림 · 확인 — [stepforge-ops-decisions.md](stepforge-ops-decisions.md)(cae00 사람 몫, server-setup 4절)
- [x] StepForge — `find_plm_task` 응답의 sync 칸을 줄인다(0 ~ 2행에 11 ~ 12천 자, N-10) — StepForge D-647 · D-637 의 '본문 그대로' 를 사용자 지시로 뒤집음(C-28)
- [-] SignalForge SG-04(P8 마케팅명 → PH8 제품 코드) — 제품 카탈로그 · 태깅 사전의 구조 결정이고 요청서의 P8 · PH8 은 가린 이름이다. 묻는 글 [signalforge-sg04-question.md](signalforge-sg04-question.md)(C-29)
- [-] Datahub 플랫폼 DP-01 ~ 05 · objects_summary 오류 문구 · FailureTrace DP-02 · CAE 그룹 허브 해석 기록 · ARP · ODB 허브 — 이 박스에 코드가 없다(cae00 · 바깥 시스템, C-17)

## 박스 · 다른 쪽(포털 코드 아님)

- [ ] O-2 부하분산기 대화 고정(W-1 뒤)
- [ ] O-3 도구 설명 예산 A/B — `CHAT_TOOL_SCHEMA_BUDGET` 30,000 · 40,000 · 같은 16문항(W-2)
- [ ] O-4 생각 강도 A/B(W-6 · D-4)
- [ ] O-5 '(시험)' 라벨 바로잡기
- [-] O-11 본답 출력 상한 — 사용자 결정 D-6(두지 않는다)
- [ ] O-12 허브 응답 견본(사람 이름 지운 것)
- [ ] O-13 박스 권한표에 허브 셋 · componentcore · plm-search-agent · simengbay · 시험 사본 행이 있는지 — cae00 의 마지막 update-all 로그 §6 '권한 표 대조' · '권한 표 구멍' 줄이 답한다(C-25)
- [ ] 플랫폼 몫(요청서 5.5) — DP-01 ~ 06 · StepForge · SignalForge SG-04 · CAE 그룹 허브 해석 기록 — 그쪽 요청서로
