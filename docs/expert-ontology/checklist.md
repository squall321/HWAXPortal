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
- [ ] 결정 기록 EO-6 ~ EO-12 · 계획 6절 · CLAUDE.md 문서 표
- [ ] AIDataHub — 이관(`record_mentions` · `record_entities` · `onto_state`) · 규칙 파일 · `services/onto_svc.py`(낱말 · 뽑기 · 짓기 · 잇기 · 프로필 · 질문 맞추기)
- [ ] AIDataHub — `api.scripts.onto` · `deploy/apptainer/onto.sh`(build · bind · status · profile)
- [ ] AIDataHub — `recommend_agents` 의 `onto` 인자(off 면 응답이 그대로) · MCP 창구
- [ ] AIDataHub — 시험(뽑기 · 잇기 · 프로필 · 추천 셋) · 전체 시험
- [ ] 에이전트 서버 — `SEAT_ONTO`(기본 끔) · 도구가 인자를 알 때만 · 리스크 심사 제외 · 시험
- [ ] 포털 — `card-entity-bind.py`(허브 읽기 둘 · exact 만 · 사전 파일 · `onto.sh bind`) · 시험(가짜 허브)
- [ ] 포털 — `persona-domains-build.py` · 어휘표 `personas.domains` 첫 줄(구조 셈)
- [ ] dev — 이관 · `onto.sh build` · 수 확인 · 프로필
- [ ] cae00 절차(`server-setup.md`) · 박스 훅 보기 · 받은 편지함 · 업데이트 이력
- [ ] 올림(가지 병합 `--no-ff`) · dev 반영
- [ ] cae00(사람) — 받기 · build · bind · 수 보고 · G-EO 판정 뒤 `SEAT_ONTO`

