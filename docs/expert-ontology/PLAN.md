# 전문가 고르기 · 지식카드 조회를 온톨로지에 잇기 — 계획

> 2026-11-03(KST) 세움. 사용자 물음 — '전문가 에이전트 고르는거에서 지식카드 조회도 온톨로지화가 될수 있나'. 같은 날 결정 넷(EO-1 ~ EO-4 —
> [context-notes.md](context-notes.md)). 대조 판 — 에이전트 서버 `332f70e` · AIDataHub `fccb0e5` · 게이트웨이 `1c93362` · 포털 `27c703cb` ·
> SP 키트 사본 0.4.67(StepForge `external/StandardPlatform` — cae00 허브는 더 새 판). 할 일은 [checklist.md](checklist.md)다.

## 0. 한눈에

- **된다. 다만 지금은 다리가 하나도 없다.** 전문가 고르기의 모든 길이 AIDataHub `recommend_agents` 하나이고(카드 절 의미검색 · 표본 질의 · 이름 낱말 겹침),
  카드(dev 59,032장 · 절 약 109만)에는 객체를 가리키는 칸이 없으며, AIDataHub 에는 온톨로지 모듈이 없다(1절).
- **'온톨로지화' 는 새 온톨로지가 아니라 잇기다(EO-1).** 카드를 이미 있는 플랫폼 객체 키(정본 허브의 고장모드 · 시험 항목 · 재료 물성 · 과제 · 모델 …)에 잇고,
  전문가는 그 카드들로 저절로 묶는다. E-5 의 '새 온톨로지로 다시 짓지 않는다'(design-e5 3.4)를 그대로 지킨다.
- **먼저 잰다(EO-2).** cae00 에서 카드 표본이 허브 객체에 얼마나 정확히 이어지는지(O0a)와, 그 연결이 맞는 전문가를 올리는지(O0b — E-5 기준선 B0 와 같은 날)를
  동작 변경 없이 잰다. 관문(G-EO)을 넘지 못하면 짓지 않는다.
- **연결은 AIDataHub 새 표(EO-3), 뽑기는 허브 사전 맞추기 · 정확만(EO-4).** LLM 호출 없이 결정적으로 다시 지을 수 있고, `object_resolve` 가 `exact` 일 때만 잇는다.

## 1. 지금 — 조사 셋(11-03)

### 1.1 전문가를 고르는 길 — 모두 `recommend_agents`

| 길 | 어디 | 무엇으로 |
|---|---|---|
| 심의 첫 좌석 | 에이전트 서버 `deliberation.py` `_discover` · `_rank_keys` | 질문 전체로 `recommend_agents{q}`(기본 5명) → 운영자 · 중복 거름 |
| 반대 도메인 좌석 | `_counter_seats` | LLM 이 짧은 축 셋 → 축마다 `_discover(3)` → 새 도메인 첫 사람(최대 2) |
| 이어하기 재심사(B17) | `_rescreen_seats` | 사람 의견에서 축 셋 → 축마다 `top_k=40` → 새 도메인(최대 2) |
| 심의 미리보기 · 지정 좌석 | `app.py` `POST /deliberate/experts` · `delib_opts.personas` | `top_k=40` · 화면이 위 다섯을 미리 고른다 |
| 챗 '전문가 뭐 있어' | `run_agent_search` | `top_k=10` |
| 띵킹 | `thinking.py` `_summon(10)` · `_screen_one` | 추천 → 좌석 범위 `agent_search` 예심(거의 다 통과) → 좌석 자기판정 |
| 리스크 앱 명단 | HWAXRisk `roster.py` | 도메인 목록 + `recommend_agents(top_k=60)` |

점수(AIDataHub `services/recommend_svc.py`) — `record_mean + 1.0 · sample_mean + 2.0 · desc_frac`. 카드 절 의미검색(위 50절, BGE-M3)의 전문가별 평균 ·
표본 질의 의미검색(전문가당 3) · 질문 낱말이 이름 · 설명 · 태그 · data_types 에 든 비율. `low_confidence` 는 최고 낱말 겹침 < 0.40.
**객체 · 온톨로지는 어디서도 안 쓴다** — E-5 의 그림자(`_persona_shadow` → `seat_cover`)가 로그만 쓰고 꺼져 있으며(`PERSONA_SHADOW_LOG`), 어휘표
`personas.domains` 는 비었다.

알려진 약점(design-e5 · request-1030) — 긴 질문은 평균에 묻힌다 · 같은 도메인 안의 혼동(E-5 저작 반례의 84%) · '맡은 사람 없음' 판정이 없다 · 띵킹 예심은
거의 다 통과한다 · B17 재실행에서 서비스 · 필드 데이터 전문가 0명.

### 1.2 지식카드 — 객체 칸이 없다

- `records`(AIDataHub `db/models.py`) — 제목 · 요약 · `tags` · `agents`(카드 ↔ 전문가 정본) · `content`(JSONB) · `domain`(= 전문가 키) · `subject_keywords` ·
  `valid_from` · 벡터 둘(768 · BGE-M3 1024). 절 표 `record_sections`(1,090,000 안팎).
- 이어진 표는 `agent_records`(적재 순서) · `external_id_map` · `record_attachments` 뿐 — 재료 · 파트 · 과제 · 고장모드 · 문서 표가 없다.
- 구조는 `content` 안에만 있다 — ExpertAgents 카드 `card{type, tier, confidence, causal_status, standard_refs, fact_refs, sources}`, MaterialTwin
  `properties[]{key, domain, value, unit, method, source}`. 아무도 구조로 읽지 않는다(절 글만 FTS · 임베딩).
- dev 수 — 전문가 796(접두 23) · 카드 59,032(논문 26,194 · 특허 5,409 · 규격 867 · ExpertAgents 23,378 · 재료 2,688 …) · 묶음 72,252(중앙 48.5).
  규격은 자유 태그로 표기가 섞였다(IPC 131 · JESD 184 · IEC 218 · ASTM 103 가지).
- 뽑는 단계가 없다 — 구조는 원천이 이미 가진 것뿐이다.

### 1.3 이을 수 있는 객체

| 원천 | 타입(키 꼴) | 비고 |
|---|---|---|
| 정본 허브 `rootdesigndatahub`(cae00 에만) | plm_project · plm_task(키 = 과제명) · plm_model, cae00 확장 failure_mode · test_item · sim_capability · criterion · material_property, part(슬러그 미확인) | `(type_slug, key)` — 키는 허브끼리 같고 UUID 는 다르다. `object_resolve` 는 식별자 → 별칭 → 이름 → 포함, 포함만이면 exact 아님 |
| 형제 허브 failuretrace · caegroupdatahub | 고장 · 직원(가명) 등 | 가족 — 늘 접두 |
| StepForge | 허브 거울 + cad_revision · cad_part · part_role(16) | dev 에도 있다 |
| DynaForge | 허브 거울 + dev_revision(`<과제>@<코드>`) | 파트 · 재료 id 는 보고서마다 |
| Report Archive(비코어) | 축 — model · part · bom · phase · defect · rel_test · sim_type | 정수 id · 고치지 않는다 |
| SignalForge · MX 위키 | 제품 코드 · 부품 16 · 증상 32 / 엔터티 14 | 판정을 주지 않는다(입구 아님 — OF-5) |

정본이 없는 것 — 재료 실물(물성만 있다) · 공정 · 규격 · 시험 방법군 · 제품군(모델의 series 속성뿐) · 전문 분야(orgTaxonomy 23 코드가 사실상의 목록).

### 1.4 지켜야 할 앞선 결정

- E-5(10-31 D-E5-1 ~ 8 모두 (가)) — 측정 먼저(B0 · 관문 G0) · 실사용 H 가 기준 · 연결 표는 어휘표 `personas` 칸(도메인 단위) · 새 온톨로지 없음 · 추천 점수식은
  AIDataHub 몫 · 앉은 좌석을 빼지 않는다 · 코어 데이터 질문은 알리고 좌석은 부른다(D-E5-6).
- 온톨로지 먼저(OF-1 · OF-14 ①) — 고른 플랫폼 안에서 풀고 코어 타입은 정본 허브 `object_resolve` 먼저 · 후보는 고르지 않는다(사람에게 묻는다).
- 과제 인사이트(PG-4 · PG-21) — SP 키는 서버가 부른 풀이의 결과 행에서만 · 엔진은 주제를 모른다(사람이 고른 근거는 예외).
- D-18 — 리스크 심사에는 새 길을 열지 않는다. OF-13 · '고리는 cae00 에서 닫는다' — 잴 것은 cae00 에서.

## 2. 무엇을 짓나(관문을 넘으면)

### 2.1 카드 ↔ 객체 연결 — AIDataHub 새 표(EO-3)

`record_entities` — `(record_id, hub, type_slug, key)` 마다 한 줄 · 맞춘 자리(`title` · `summary` · `section:<id>`) · 맞춘 글자 · 판정(`exact` 만 저장) ·
사전 판(`dict_version` — 허브 목록의 지문) · 지은 때. cae00 에서 짓는다(허브가 거기 있다). dev → cae00 병합(`merge-from-drive.sh`)이 덮지 않게 박스
쪽 표로 둔다(`read_count` 처럼). 카드가 바뀌거나 사전 판이 바뀌면 그 카드만 다시 짓는다.

### 2.2 뽑는 법 — 허브 사전 맞추기 · 정확만(EO-4)

1. 정본 허브 타입마다 `objects_list` 로 객체 이름 · 별칭 · 식별자를 받아 사전을 짓는다(별칭을 목록이 주지 않으면 객체마다 읽는다 — cae00 에서 확인).
2. 카드 제목 · 요약 · 절 글에서 사전 낱말을 맞춘다(NFKC · 대소문자 무시 · 영문은 낱말 경계 · 한글은 두 글자 이상 · 너무 흔한 낱말은 사전에서 뺀다 —
   빼는 목록은 O0a 에서 정한다).
3. 이미 있는 칸도 함께 — 과제 코드(`eng_meta.project` — 키가 아니라 속성이라 풀어야 한다) · SignalForge 제품 코드 · ExpertAgents `standard_refs`(규격은 정본이
   없어 잇지 않고 세기만).
4. 맞춘 이름을 `objects_resolve_many` 로 물어 **`exact` 만** 잇는다. `candidates` · `none` 은 잇지 않는다(세기만 — OF-14).

LLM 호출은 없다. 같은 카드 · 같은 사전이면 같은 연결이다.

### 2.3 전문가 쪽 — 저절로 묶는다

전문가의 객체 묶음 = 그 전문가 카드(`records.agents`)의 연결 합(객체마다 카드 수 · 대표 카드). 781명에게 손 줄을 쓰지 않는다(design-e5 3.4).

### 2.4 쓰는 곳 — 그림자 먼저

- **좌석 · 추천** — 질문을 정본 허브로 풀어(exact 만) 나온 객체를 가진 전문가에게 신호(카드 수 · 비율)를 준다. 추천 점수식은 바꾸지 않고 그 위에서 고른다
  (E-5 와 같은 자리 — 에이전트 서버). 먼저 그림자(로그만)로 돌리고 관문 뒤 켠다.
- **앉은 전문가의 카드 조회** — 질문이 객체로 풀렸으면 그 객체에 이어진 그 사람 카드를 먼저(`agent_search` 의 거름 · 올림 — AIDataHub 몫).
- **판정** — 풀린 객체를 가진 전문가가 아무도 없으면 '맡은 사람 없음' 후보, 과제 · 모델만 풀리면 '코어 데이터 질문'(D-E5-6) 후보. 둘 다 정밀도를 재고 켠다.
- **하지 않는 것** — 새 온톨로지 · LLM 추출 · 후보 고르기 · 리스크 심사 좌석(D-18) · dev 에서 허브 연결(dev 에는 허브가 없다 — 시험은 가짜로).

## 3. 단계

| 단계 | 무엇 | 어디 · 누가 | 동작 변경 |
|---|---|---|---|
| **O0a** 범위 | 카드 표본 300장(문서 종류 층화)을 허브 사전으로 맞추고 exact 로 풀어 타입별 연결 비율 · 카드당 수 · 흔한 낱말을 잰다 | 포털 리포 읽기 전용 탐침(`infra/scripts/card-entity-probe.py` — 지음 11-03 EO-5) — cae00 에서 사람이 돌린다(받은 편지함 2026-11-03 Q1 ~ Q3) | 없음 |
| **O0b** 신호 | E-5 평가셋(A-test 300 · H)에서 질문 → 객체 → 전문가 묶음 겹침이 정답 전문가 순위를 올리는지 — 오늘 추천 순위 위 40명만 묶음을 지어 견준다 | E-5 B0 와 같은 날 · cae00 | 없음 |
| **관문 G-EO** | 3.1 의 기준 | 사람이 숫자를 보고 정한다 | — |
| **O1** 연결 표 | `record_entities` · 짓는 일(cae00) · 병합 보호 · 읽기 창구 · `agent_search` 의 객체 거름 | AIDataHub 세션(요청서) | 표만 · 고르기 그대로 |
| **O2** 그림자 | 좌석 · 추천 · 띵킹에서 객체 신호를 로그로 | 에이전트 서버 | 없음(로그) |
| **O3** 켜기 | 관문 뒤 좌석 신호 · 카드 먼저 · 두 판정 | 에이전트 서버 · AIDataHub | 박스 스위치(기본 끔) |

### 3.1 관문(안 — O0 숫자를 본 뒤 사람이 정한다)

- **G-EO1 범위** — 고르기에 쓸 타입(failure_mode · test_item · material_property · sim_capability 가운데) 하나 이상에서 표본 카드의 20% 이상이 exact 로 이어진다.
  논문 · 특허 묶음은 따로 센다.
- **G-EO2 신호** — A-test 에서 상위 3 적중이 오르고(짝 비교 유의 — E-5 2.7 과 같은 법) 어느 도메인 갈래도 5%p 넘게 떨어지지 않는다. H 가 달린 뒤에는 H 가 기준이다
  (D-E5-1).
- 못 넘으면 O1 을 청하지 않고 숫자와 까닭만 남긴다.

## 4. 다른 쪽 몫

- **AIDataHub 세션** — O1(표 · 짓는 일 · 병합 보호 · 읽기 창구 · `agent_search` 거름). 관문 뒤에 요청서를 쓴다. 지금 청하는 것은 없다.
- **에이전트 서버** — O2 · O3. E-5 그림자(`persona_links.py`) 곁에 둔다.
- **cae00(사람)** — O0a 탐침 실행 · O0b 는 E-5 B0 와 함께. 받은 편지함으로 청한다.

## 5. 위험 · 열린 점

- **범위가 낮을 수 있다.** 카드의 절반 넘게(약 31,600장)가 논문 · 특허라 사내 객체(과제 · 모델)와는 거의 안 이어지고, 고장모드 · 시험 항목 · 재료 물성이 이어질지가
  관건이다(추정 — O0a 가 잰다).
- **허브 타입이 다 확인되지 않았다.** part 슬러그 · work-core(부서 · 사람 · 주제 …) 설치 여부 · 별칭을 목록이 주는지 — cae00 에서 본다.
- **같은 도메인 혼동을 가를지 모른다.** 같은 분야 전문가들은 같은 객체를 다룰 수 있다 — O0b 가 잰다.
- **사전 맞추기의 거짓 적중.** 짧은 이름(두세 글자 · 약어)이 흔한 낱말과 겹친다 — 흔한 낱말 빼기 · 낱말 경계로 줄이고 O0a 의 표본을 사람이 훑어 정밀도를 본다.
- **기준일(as_of).** 연결은 카드에 딸리므로 카드의 `valid_from` 을 따른다 — 객체의 생애(과제 종료 등)는 이번 범위 밖이다.
