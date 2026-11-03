# 전문가 고르기 · 지식카드 조회를 온톨로지에 잇기 — 결정 기록

계획은 [PLAN.md](PLAN.md), 할 일은 [checklist.md](checklist.md)다. 날짜는 KST.

**EO-0 조사 셋(11-03).** 읽기만 한 조사 셋을 나눠 돌렸다 — (1) 전문가를 고르는 길, (2) 지식카드 자료 구조와 조회, (3) 이을 수 있는 온톨로지 식별자.
대조 판은 에이전트 서버 `332f70e` · AIDataHub `fccb0e5` · 게이트웨이 `1c93362` · SP 키트 사본 0.4.67. 숫자는 dev GET 창구로만 셌다(DB 연결 없음).
- 고르는 길은 심의 첫 좌석 · 반대 도메인 좌석 · B17 재심사 · 미리보기 · 챗 '전문가' · 띵킹 · 리스크 앱 명단까지 모두 AIDataHub `recommend_agents` 다
  (`services/recommend_svc.py` — 카드 절 의미검색 평균 + 1.0 × 표본 질의 + 2.0 × 이름 · 설명 낱말 겹침). 객체 · 온톨로지는 어디서도 안 쓴다 — E-5 그림자
  (`persona_links.py` `seat_cover`)는 로그만 · 꺼짐, 어휘표 `personas.domains` 는 비었다. 게이트웨이 `browse_experts` 는 이름 조각만 본다.
- 카드는 `records`(태그 · `agents` · JSONB `content` · 절 · 벡터)뿐이고 객체 표 · 개념 표 · 관계 표가 없다(AIDataHub 에 온톨로지 모듈 없음 —
  ontology-first PLAN 과 같은 말). 구조는 `content` 안(ExpertAgents 카드 type · tier · confidence · standard_refs · fact_refs, MaterialTwin 물성 키)에만 있고
  아무도 구조로 읽지 않는다. 뽑는 단계가 없다. dev — 전문가 796 · 카드 59,032 · 묶음 72,252, 규격 태그의 표기가 섞였다.
- 이을 수 있는 키는 정본 허브(cae00 에만)의 `(type_slug, key)` — plm_project · plm_task · plm_model(리포에 있다) · failure_mode · test_item · sim_capability ·
  criterion · material_property(cae00 확장 — 리포 밖) · part(슬러그 미확인). `object_resolve` · `objects_resolve_many` 가 exact · candidates · none 을 준다
  (식별자 → 별칭 → 이름 → 포함, 포함만이면 exact 아님 · 한 번에 500). 형제 허브 · StepForge · DynaForge 거울, RA 축(비코어), SignalForge · MX 위키(판정 없음).
  정본이 없는 것 — 재료 실물 · 공정 · 규격 · 시험 방법군 · 제품군 · 전문 분야.
- 카드 · 전문가와 SP 키 사이의 다리는 없다. 앱 고유 id 만 있다 — MaterialTwin 재료 id(`external_id_map` · `code:` 태그) · SignalForge 제품 코드
  (`subject_keywords`) · `eng_meta.project`(과제 코드 — SP 키가 아니라 풀어야 한다). RA 의 전문가 ↔ 판정 ↔ 파트 연결은 RK-01 뒤에 꺼져 있다.

**EO-1 사용자 결정 11-03 — 범위는 '있는 온톨로지에 잇기'.** 카드를 이미 있는 플랫폼 객체 키(정본 허브 먼저)에 잇고 전문가는 그 카드들로 저절로 묶는다.
새 온톨로지는 짓지 않는다(design-e5 3.4 · PLAN 3절 그대로). 정본이 없는 공정 · 규격은 비워 둔다. 버린 것 — AIDataHub 안 개념 · 별칭 표(허브에 없는 것까지
덮지만 어휘 사본이 하나 더 생기고 허브와 어긋난다 — 10-29 '어휘는 한 곳에').

**EO-2 사용자 결정 11-03 — 먼저 재고 짓는다.** O0a(카드 표본 300장의 타입별 exact 연결 비율)와 O0b(E-5 평가셋에서 객체 겹침 신호의 힘)를 동작 변경 없이
cae00 에서 잰다 — 허브가 cae00 에만 있고, 측정 · 튜닝은 운영 박스에서 닫는다(OF-13 · closed-loop). O0b 는 E-5 기준선 B0 와 같은 날이다(같은 평가셋 · 같은 실행기).
범위가 낮으면 짓지 않는다. 버린 것 — 바로 짓고 켜며 재기(범위가 낮으면 걷어야 한다).

**EO-3 사용자 결정 11-03 — 연결은 AIDataHub 새 표.** 카드 정본 곁(`record_entities`)에 두어 좌석 고르기와 앉은 전문가의 카드 조회(`agent_search`) 둘 다 쓴다.
cae00 에서 짓고 dev → cae00 병합이 덮지 않게 한다(박스 쪽 표 — `read_count` 와 같은 꼴). AIDataHub 세션 몫이라 관문 뒤에 요청서를 쓴다. 버린 것 — cae00 박스
파일(전문가 단위만 — 카드 조회를 못 거른다). E-5 의 어휘표 `personas` 칸(D-E5-3)은 도메인 단위 손 줄이라 이것과 겹치지 않는다 — 카드 단위 연결은 수가 커서
어휘표에 둘 수 없다.

**EO-4 사용자 결정 11-03 — 뽑기는 허브 사전 맞추기 · 정확만.** 정본 허브 객체 목록의 이름 · 별칭 · 식별자로 카드 제목 · 요약 · 절을 맞추고, 이미 있는 칸(과제
코드 · 제품 코드)도 함께 풀어 `objects_resolve_many` 가 `exact` 일 때만 잇는다(`candidates` · `none` 은 세기만 — OF-14). LLM 호출이 없어 결정적이고 다시 지을
수 있다. 버린 것 — LLM 추출(동의어 · 우회 표현을 잡지만 카드 59,032장만큼 GLM 호출 · 시간 · 판마다 흔들림).
