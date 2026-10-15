# 운영 수정 요청 10-15(전문가·지식카드 화면) — 진행 계획

> 정본은 요청서 `docs/request_1015.md`(K1~K9 · 운영 쪽 · 반영 확인). 이 문서는 나누는 법·결정·차례만 적는다. 요청서의 `파일:줄` 은 그 기준 커밋(포털 `90147ac` · 에이전트서버 `c4e4823` · AIDataHub `b401f88` · KooRemapper `30a1f7d`) 기준이라 지금은 밀렸다 — 내용으로 찾는다.
> 우선순위 — 실제 운영 문제라 리스크 심사 M3 의 남은 검토보다 앞선다(M3 는 아직 운영에 안 올라갔다).

## 1. 사용자 결정(10-15)

| 항목 | 결정 |
|---|---|
| K6-1 dynaforge-report | **(나) 있는 전문가로 돌린다** — KooRemapper 등재 키를 `sim-drop-impact` 로(`HUB_AGENT` 상수), 양식 문서도 고친다. `sim-drop-impact` 의 data_types 에 `SIM` 을 더한다(운영 데이터 — 사용자/운영 몫). 빈 행 삭제는 KooRemapper 변경이 배포된 **뒤에**(운영) |
| K6-2 kooremapper-modelmeta | **(가) 지운다 + 시험 업로드를 막는다** — `kr2datahub.py` 는 `--upload` 를 줄 때만 올린다(기본은 미리보기), 붙일 키는 허브에 등록된 전문가로. 레코드 3건 → 행 순서의 삭제는 운영 몫 |
| K6-3 strict | 요청서대로 **기본 켬**(`strict_agent_validation=True`, 되돌리기 `STRICT_AGENT_VALIDATION=false`) |
| K3-9 재료 카드 | **(가) MaterialTwinWeb 이 내보낼 때 절로 나눈다**(크기 한도는 MaterialTwinWeb 담당 몫 — 기본값을 두고 손잡이로) |
| K5-2 본문 검색 | **스위치 뒤, 기본 끔** — 운영 DB 사본에서 `EXPLAIN ANALYZE`(material-twin-analyst 2,729장 기준)를 잰 뒤 켠다. 낱말 AND·`%`·`_` 이스케이프(K5-1)는 바로 켠다 |
| K2-6 로그인 수명 | **갱신 때 연장**(쓰는 동안은 8시간이 지나도 끊기지 않게). 만료 뒤 401 은 어느 경우든 로그인 화면으로 보낸다(K2 본체) |

## 2. 나누는 법 — 리포별 세 갈래(같은 파일은 한 갈래가 차례로)

| 갈래 | 리포 | 차례(요청서 '같은 파일을 고치는 요청') |
|---|---|---|
| A | HWAXAgentServer | K1(`_record_view`·`catalog_record` 본문 풀기·빈 카드) → K3(총량·이어 읽기) → K9(JSON 펜스) → K2-5(`catalog_agent` 의 `session_failed`·`records_failed`) → K8(운영자 문구) → K7(`deliberation.py` `_restore_role`) → K5(독스트링). `tests/test_catalog_deep.py`·`test_operator_persona.py` |
| B | HWAXPortal | 프런트 한 묶음(K1-3 · K2 · K6-5 · K3 · K4 · K5 placeholder · K8 화면) + 백엔드(K3 프록시 · K2-6 세션 연장) + K8 정본(`he-team.json`·`sync-he-personas.py`·`test_he_personas.py`). 빌드와 Drive 업로드는 한 번 |
| C | AIDataHub · KooRemapper · MaterialTwinWeb | AIDataHub K5(검색) · K6-3(strict) · K6-4(동기화 덮어쓰기 금지·요약 폴백·요약만 바뀌어도 갱신) · K3-9 받는 쪽, KooRemapper K6-1(나)·K6-2(가) 코드, MaterialTwinWeb K3-9(가) |

- 갈래 B 는 갈래 A 의 응답 모양(K2-5 의 `session_failed`·`records_failed`, K3 의 `total_sections`·`total_chars`·`next`)을 요청서의 계약대로 쓴다 — A 가 먼저 들어가면 그 실제 모양으로 맞춘다.
- 다른 세션이 KooRemapper·MaterialTwinWeb·AIDataHub 를 만질 수 있다 — 갈래 C 는 시작 전에 각 리포의 `git status`·최근 커밋을 보고, 남의 미커밋 변경이 있으면 건드리지 않고 알린다.
- 데이터 정리(K6-1·K6-2 의 행·레코드 삭제, `sim-drop-impact` 의 data_types)는 **운영 몫**이다 — 코드가 박스에 들어간 것을 확인한 뒤(요청서 '데이터 정리는 코드 확인 뒤에').

## 3. 확인

- 각 K 절의 **확인** 을 따른다(dev 에서 시험·lint, cae00 에서 읽기 호출 — 사용자 몫).
- 전부 들어간 뒤 cae00 전수 점검(`~/kc-check/kc_sweep.py`, 운영 쪽 도구)을 다시 돌린다 — 요청서 '반영 확인 — 전체' 의 표.
- 반영 경로 — 포털 프런트는 dist 빌드 → Drive(`build-all-to-drive.sh portal`) → cae00 `update-collab.sh`. 에이전트서버·AIDataHub·KooRemapper 는 update-all. AIDataHub 재기동 뒤 게이트웨이 `list_*` 캐시가 300초 남으니 K5 확인은 5분 뒤.
