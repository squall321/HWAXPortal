# 전문가 고르기 · 지식카드 조회를 온톨로지에 잇기 — 체크리스트

계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 조사 · 계획(dev — 11-03)
- [x] 조사 셋 — 고르는 길 · 카드 자료 구조와 조회 · 이을 수 있는 객체(EO-0)
- [x] 사용자 결정 넷 — 11-03 모두 권장안(EO-1 ~ EO-4)
- [x] 계획서 · 체크리스트 · 결정 기록 · CLAUDE.md 문서 표 한 줄

## O0a 범위 탐침(포털 리포 · 읽기 전용 — dev 에서 짓고 cae00 에서 돈다)
- [x] `infra/scripts/card-entity-probe.py` — 게이트웨이 경유 읽기만(허브 `objects_list` · `objects_resolve_many`, AIDataHub `list_records` · `get_record` ·
      `get_record_sections`), 표본 층화 · 사전 · 맞추기 · exact 만 · 수만 내기(카드 글 · 사람 이름을 내지 않는다) — `d9d92bbd`(EO-5)
- [x] 시험 — 가짜 허브 · 가짜 AIDataHub(exact · candidates · none · 별칭 · 흔한 낱말 · 짧은 이름 · 낱말 경계 · 쪽 넘김 · 쓰기 도구를 부르지 않음) — 23, 변이 넷 붉음
- [x] dev 마른 실행 — 허브 없음(그렇다고 말하고 끝 2) · 진짜 AIDataHub 카드 8장 + 가짜 허브로 층 · 카드 · 절 · 맞추기(EO-5)
- [x] 받은 편지함 — [`../cae00-inbox/2026-11-03.md`](../cae00-inbox/2026-11-03.md) Q1 ~ Q3(범위 · 부품 슬러그와 별칭 · 뺄 낱말)
- [ ] cae00 답 — Q1 ~ Q3(사람)

## O0b 신호(E-5 B0 와 같은 날)
- [ ] 추천 위 40명의 객체 묶음으로 A-test 순위를 다시 매기는 갈래 — E-5 B0 실행기(`seat_probe` · `/seat-eval`)에 붙인다
- [ ] H 가 달리면 H 로 다시

## 관문 G-EO(사람)
- [ ] O0a · O0b 숫자로 G-EO1 · G-EO2 판정 — 못 넘으면 여기서 멈추고 숫자 · 까닭을 남긴다

## O1 ~ O3(관문 뒤)
- [ ] AIDataHub 요청서 — `record_entities` · 짓는 일 · 병합 보호 · 읽기 창구 · `agent_search` 객체 거름
- [ ] 에이전트 서버 그림자 — 좌석 · 추천 · 띵킹의 객체 신호 로그
- [ ] 켜기 — 좌석 신호 · 카드 먼저 · '맡은 사람 없음' · '코어 데이터 질문'(박스 스위치 기본 끔)

## 미리 짓기(11-21 — 사용자 결정 EO-6, 계획 6절)
- [x] 결정 기록 EO-6 ~ EO-14 · 계획 6절 · CLAUDE.md 문서 표
- [x] AIDataHub — 이행 0033(`record_mentions` · `record_entities` · `onto_terms` · `onto_state`) · 규칙 파일 · `services/onto_svc.py`(낱말 · 뽑기 · 짓기 · 잇기 · 프로필 ·
      질문 맞추기 · 전문가 신호) — `8c9506c`
- [x] AIDataHub — `api.scripts.onto` · `deploy/apptainer/onto.sh`(build · bind · status · profile)
- [x] AIDataHub — `recommend_agents` 의 `onto` 인자(off 면 응답이 그대로) · MCP 창구
- [x] AIDataHub — 시험 13(뽑기 · 잇기 · 프로필 · 신호 · 추천 셋 · 명령) · 전체 787 통과(실패 35 는 main 과 같은 목록)
- [x] dev PostgreSQL 실데이터 — 임시 스키마에서 짓기 · 잇기 · 신호 · 프로필(EO-13)
- [x] 에이전트 서버 — `SEAT_ONTO`(기본 끔) · 도구가 인자를 알 때만 · 리스크 심사 제외 · 그림자 줄 · 시험 8 · 전체 4,786 통과 — `f5b5dd8`
- [x] 포털 — `card-entity-bind.py`(허브 읽기 둘 · exact 만 · 사전 파일 0600 · `onto.sh bind`) · 시험 11(가짜 허브 · 가짜 AIDataHub 명령) — `6a7b367c`
- [x] 포털 — `persona-domains-build.py`(박스 덧씌우기에만) · 시험 5. 추적 어휘표에는 줄을 더하지 않았다(EO-10)
- [x] cae00 절차 [server-setup.md](server-setup.md) · 박스 훅 보기 · 받은 편지함 `../cae00-inbox/2026-11-21.md` · 업데이트 이력
- [x] 올림(가지 병합 `--no-ff`) — AIDataHub main `85c3f2f` · 에이전트 서버 · 포털
- [x] dev — AIDataHub 재기동(이행 0033) · `onto.sh build` 254,668줄 11.8초 · 두 번째 건너뜀 · `persona-domains-build.py` 셈(줄 둘 — 적지 않았다)
- [ ] dev 에이전트 서버 재기동은 하지 않았다 — 스위치가 기본 끔이라 다음 재기동 때 그대로 들어온다
- [ ] cae00(사람) — 받기 · build · `--dry-run` · bind · 수 보고 · G-EO 판정 뒤 `SEAT_ONTO`(server-setup 1 ~ 6절)
- [ ] 미룬 것 — 앉은 전문가의 카드 먼저 보기 · '맡은 사람 없음' · '코어 데이터 질문'(EO-12) · LLM 뽑기(연결 수를 본 뒤 다시 묻는다)
