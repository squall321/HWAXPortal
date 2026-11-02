# 온톨로지 먼저 — 체크리스트

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 검토 · 계획(dev — 11-02)
- [x] 입력 조사 셋(플랫폼 목록 · 챗 · 심의) 줄 대조 — 맞은 것 · 틀린 넷(OF-2 · OF-11)
- [x] dev 게이트웨이 `/tools-map` · `/health` 읽기(GET 만 — `search_tools` 는 부르지 않음) · 접두 이름 21 · 자유 조회에서 빠진 읽기 4(OF-3)
- [x] 계획서 · 결정 기록 · 체크리스트 · CLAUDE.md 문서 표 한 줄
- [x] 받은 편지함 `docs/cae00-inbox/2026-11-02.md` Q20 ~ Q22(읽기만 — dev 에서 글 그대로 돌려 봄)
- [x] 반대 검토 한 번 — 지적을 손수 확인해 고침(OF-12): F0 범위를 좁힘 · 표지는 챗 로드만 · PG-21 글자와 뜻 · 입구의 조건 · 리스크 좌석의 기존 노출
- [x] 사용자 결정 넷(PLAN §10) — 11-02 넷 다 권장안(OF-14)

## M0. cae00 읽기(사람 — 코드 없음)
- [ ] Q20 이름 지도 — 선언 백엔드와 상태 · 접두 꼴 수 · 접두를 떼면 자유 조회에 드는 것(정적 · 허브 가족 · 선언) · 온톨로지 도구의 노출 꼴과 읽기 표지 · 엔진이 맨 이름으로 부르는데 접두 꼴로만 있는 것
- [ ] Q21 잡 원장의 '전문가 자유 조회 활성 — N종' 줄 · 앞 6석의 좌석별 도구 수
- [ ] Q22 온톨로지 도구별 지연 · 결과 크기 · 들어온 자격
- [ ] 답을 PLAN §2.1 · §3 · §6.5 · §6.6 에 옮긴다 — Q20 의 마지막 줄이 비지 않았으면 그 기능을 따로 고친다(§3.5)

## M-R. 읽기 표지(사람 · 다른 리포 세션)
- [ ] cae00 박스 `read_tools.local.json` 에 SP 허브 셋의 `object_resolve` 와 DynaForge `ontology_types` · `ontology_object` · `ontology_sync_state`(백엔드 키:원래 이름) — 절차는 [server-setup.md](server-setup.md) 2절
- [ ] KooRemapper 세션에 `readOnlyHint` 요청(PLAN §9) — 달리면 박스 목록에서 걷는다
- [ ] 확인 — cae00 `/tools-map` 의 `routine_read` 에 그 이름들이 든다

## F0. 좌석 자유 조회의 접두 이름(사용자 결정 2 뒤 · `wt1102/insight-m2` 병합 뒤)
- [x] 게이트웨이 — `/tools-map` 에 `orig`(노출 이름 → 원래 이름, 다른 것만) · 앱 줄의 `declared` · 시험(OF-16)
- [x] 에이전트 서버 — `_tools_map()` 이 두 칸을 쥔다 · 리스크 심사가 아니고 선언 백엔드도 허브 가족도 아닐 때만 원래 이름으로 판정 · 닫기 목록 · 앱 지정의 물성 목록 검사도 원래 이름 · 두 칸이 없으면 지금 그대로(리스크 앱이 띄운 패널 started_by=app 도 뺀다 — OF-16)
- [x] 시험 — `aidatahub_semantic_search` 든다 · `heaxstep_forge_cancel_job` · `*_catalog_run` · `stepforgeprod_list_parts` · `rootdesigndatahub_get_guide` 안 든다 · 리스크 심사에 `reportarchive_list_reports` 안 든다
- [ ] dev 손 시험(가장 작은 모델) — 상태 줄 N 이 4 는다 — 올린 뒤(재기동이 필요하다). 지은 판의 셈을 dev `/tools-map` 에 대 봤다 — 후보 183 → 187, 는 것은 그 넷뿐(OF-16)
- [ ] cae00 — update-all 뒤 Q21 을 다시 읽어 N 이 Q20 '정적' 어림만큼 · 심의 하나의 좌석별 도구 목록 앞뒤 · 감사의 엔진 호출 `refused: no-connection` 이 늘지 않음
- [x] `delib_subject.py:55-56` 주석을 함께 고친다

## M1. 챗 데이터 칸(포털 어휘표 · 에이전트 서버)
- [x] 포털 — `core_vocab.json` 에 `ontology`(apps — 지금 `_ONTO_CORE` 를 같은 차례로 · `facts`) · `_doc`
- [x] 에이전트 서버 — 칸 읽기 · 앱 줄마다 검사(가족 앱의 `entry` 는 버림) · 고정 몫을 (백엔드, 원래 이름) → 노출 이름으로 · 맵이 없으면 지금 상수(지도에 없는 이름은 옛 규칙의 이름 — OF-17)
- [x] 에이전트 서버 — `entry` 가 있을 때만 규칙 ⑧ 한 줄 · 입구 도구 설명 표지는 챗 로드(`chat=True`)에만(순위에서는 뗀다 · 캐시 열쇠에 입구 — OF-18)
- [x] 에이전트 서버 — `/health` `core_vocab.ontology`(앱 · 고정 몫 · 이 박스에 없는 이름 · 버린 줄)
- [x] 시험 — 기본값에서 시스템 프롬프트 · 고정 몫이 글자 그대로 · 덧씌우기 `entry` 로 규칙 · 표지가 선다 · 심의 로드에는 표지가 없다 · 틀린 앱 줄만 버린다 · 두 서비스 지문이 같다(덧씌우기를 둘 다 받아들인다 — 게이트웨이 · 에이전트 서버가 같은 줄에서 같은 입구를 읽는다)
- [ ] dev 재기동 · `/health` 확인 — 올린 뒤(이 가지는 재기동하지 않는다)

## M2. cae00 재기(사람)
- [ ] 덧씌우기 끔 — 16문항 · 운영자 14명(10-30 과 같은 판정)
- [ ] 덧씌우기 켬(사용자 결정 4 의 입구들 — 판정을 돌려주는 것만) — 같은 묶음
- [ ] PLAN §7.1 의 기준으로 판정 · 기본값을 정한다

## M3. 게이트웨이 손잡이(개인 Claude)
- [x] `onto_first`(기본 끔) · 가중치 `onto`(`_TUNING_WEIGHTS` · `_TUNING_FALLBACK`, 보정 없는 점수에는 넣지 않음) · `_core_vocab_parse` 가 `entry` 쌍을 앱 줄마다 읽고 예외를 내지 않는다
- [x] 시험 — 끄면 순위가 바이트까지 같다 · 켜면 앱을 부른 질의에서만 입구가 오른다 · 코어 질의에는 걸리지 않는다 · 틀린 `entry` 줄이 덧씌우기 전체를 버리지 않는다
- [ ] cae00 — 박스 정답쌍에 입구 쌍 · `/search-eval` 의 `+onto_first` 판

## M4. 심의 미리보기(포털 — 사용자 결정 3 이 (가)일 때 · `wt1102/insight-m2` 병합 뒤 · M-R 뒤)
- [x] `POST /agent/deliberate/onto-preview` — 그 사람의 PAT · 읽기 확인 · `object_resolve` → exact 일 때만 `graph_neighbors(depth 1, facts 타입)` · 줄여 4,000자(닻은 M1 과 같은 풀이로 확인 · exact 의 key 가 닻과 같을 때만 — OF-20)
- [x] 화면 — 심의 시작 · 챗→심의 브리프의 VOC 먼저 옆 칸 · 행 고르기 · 리스크 심사 계열 · 봉인 · 기준일이면 숨김 · '고른 행은 결정문 · 보고서의 근거에 남는다' 안내(두 화면에 리스크 · 봉인 입구는 없고 창구가 리스크 심사 계열을 422 로 거절)
- [x] 고른 행 → 호출 하나에 `delib_opts.evidence` 한 항목(출처 · 도구 · 인자)
- [x] 시험 — 가짜 허브 응답(exact · candidates · none · 읽기 미확인 · 게이트웨이 불통) · SP 사본의 응답 칸과 견줌 · 헤드리스 브라우저
- [ ] cae00 — 실제 주제 하나로 사람이 본다

## M5 · M6(조건부)
- [ ] M5 자동 사전 조회 — 사용자 결정 3 이 (나)일 때만 · 모델과 횟수를 먼저 묻는다 · M2 contracts 의 '엔진은 주제를 모른다' 를 그 세션과 고친다
- [ ] M6 좌석 자유 조회에 열기 — 잰 값이 있을 때만 · 다른 허브 UUID 막이를 먼저 심의로

## 다른 세션에 넘길 것(PLAN §9 · §11)
- [ ] 과제 인사이트 M2 세션 — `hwax-deliberate.js` 의 맨 이름 `semantic_search`(남음) · 사용자 결정 3 에 따른 contracts §1(3) 문장(이 가지에서 고쳤다 — OF-20)
- [ ] 리스크 심사 재설계 세션 — 리스크 좌석에 지금도 닿는 온톨로지 읽기 · 지정 도구로 넣을 수 있는 SP 허브 · 위키 · `onto_*`(PLAN §6.1)
- [ ] SignalForge · MX 백서 세션 — `resolve_product_keyword` · `wiki_entity` 가 exact · candidates · none 을 돌려줄 수 있나
- [ ] 좌석 조회 안내의 `get_guide` · 챗 상시 핵심의 `semantic_search` — Q20 답 뒤에 정한다
