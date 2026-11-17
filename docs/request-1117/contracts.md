# 11-17 요청 — 리포 사이 꼴(리스크 앱 ↔ 심의 엔진 ↔ 게이트웨이)

> 짓기 전에 정한 꼴이다. 바꾸면 이 파일을 먼저 고치고 두 쪽 시험을 함께 고친다. 결정 까닭은 [context-notes.md](context-notes.md).

## 1. 근거 묶음(RK-02) — 앱이 만들고, 호출자 · 엔진이 받는다

- **항목 꼴은 엔진 근거 항목 그대로** — `{source, tool, args, result, key}`(HWAXAgentServer `mcp_server.py` 의 evidence 설명 · `deliberation.py`
  `_EVID_KEY_MAX = 24`). `key` 는 `[A-Za-z0-9_.-]{1,24}`, 본문은 `result` 하나에만. `source` 는 사람이 읽는 표식(묶음 id · 판 · 코드).
- **맨 앞 항목은 늘 색인** — 묶음에 든 행 코드 전부와 판 · 칸 정의 판 · 묶음 id · 지문. 좌석이 '이 묶음에 없는 행' 을 '없음' 으로 읽지 않게, 색인
  끝에 "이 목록 밖의 행은 이 근거에 싣지 않았다(없다는 뜻이 아니다)" 한 줄.
- **만들기** `POST /api/targets/{key}/evidence-bundles`, MCP `risk_build_evidence_bundle` — 입력 `{version?, codes?, template{name, caps{칸: 자},
  total_cap}, mask?}`. 답 `{bundle_id, fingerprint, items_n, total_chars, per_field{칸: {chars, truncated}}, masked_n, limits{items, chars}}`.
  엔진 상한(설정 `HWAXRISK_BUNDLE_MAX_ITEMS` · `HWAXRISK_BUNDLE_MAX_CHARS` — 기본은 11-17 `deliberate_jobs` limits 120 · 135,538)을 넘으면 만들지
  않고 422 와 까닭(넘은 값 · 상한).
- **받기** `GET /api/evidence-bundles/{bundle_id}`, MCP `risk_get_evidence_bundle` — `{bundle_id, target_key, version, fingerprint, evidence: [항목 …]}`.
  `evidence` 를 고치지 않고 `deliberate_start(evidence=…)` 에 넣으면 된다(사용자 결정 — 앱 몫 먼저). 읽기 권한은 그 과제의 구성원.
- **지문** — `sha256(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")))` 의 hex. 엔진이 풀어 실은 뒤 같은 식으로 다시
  재어 '차이 0' 을 본다(DL-01 수용).

## 2. 참조 근거(DL-01) — 엔진이 푼다

- evidence 항목에 `result` 대신 `ref: {kind, id}` 를 둘 수 있다(본문 항목과 섞어 쓴다). 엔진은 시작 전에 **그 사람 신원**으로 게이트웨이를 불러
  풀고, 푼 항목을 그 자리에 차례대로 펼친다.
- `kind: risk_bundle` → 게이트웨이 `heax-hwax_risk` 의 `risk_get_evidence_bundle(bundle_id=id)` → 답의 `evidence` 를 펼친다. 펼친 뒤 §1 의 지문을 다시
  재어 묶음의 `fingerprint` 와 다르면 evidence_omitted 에 까닭(조용히 싣지 않는다).
- 풀이 실패(권한 · 없음 · 불통)는 그 항목을 빼고 evidence_omitted 에 `ref:<kind>:<id> — 까닭`. 다른 kind 는 도구 · 답 꼴을 확인한 것만 연다.
- 잡 원장에 ref 와 풀이 결과(자수 · 지문 · 시각)를 남겨 이어하기가 같은 ref 로 같은 근거를 다시 싣는다.

## 3. 구조화 결정(DL-03) — 엔진이 내고, 앱(RK-03)이 받는다

- `deliberate_result(view="decision_json")` → `{job_id, job, template, decision_json, consistency}`.
- job risk-review · risk-review-sealed 의 `decision_json` 은 결정문의 `risk_spec`(리스크 앱 `app/narrative.py` `parse_risk_spec` 과 같은 규칙 —
  마지막 ```json 펜스, 없거나 깨지면 끝에서 마지막 균형 중괄호, `schema == "risk_spec"`)에 엔진이 아는 표결을 덧붙인 것이다 —
  `{risk_spec, votes: {tally: {찬성 · 조건부 · 반대 …: 수}, by_seat?}, cites: [{key, n}]}`. 못 읽으면 `decision_json: null` 과 `parse_error`.
- `consistency` — `{consensus_claim: "전원 합의" 따위 결정문 문장(없으면 null), tally, match: bool | null, note}`. 문장이 만장일치를 말하는데 표결에
  반대 · 조건부가 있으면 `match: false`.
- 리스크 앱 RK-03 은 job_id 를 받으면 게이트웨이로 이 답을 읽고(그 사람 신원), 결정 JSON 을 직접 받으면 그대로 쓴다. 엔진이 아직 이 꼴을 내지
  않는 판이면 결정문 글을 받아 `parse_risk_spec` 으로 읽는다(표결 칸은 비고 그렇게 말한다).

## 4. 표기 규칙(RK-07) — 앱이 정하고 묶음 · 보고 묶음이 쓴다

- `risk_taxonomy(part="labels")` → 축(grade · type · attention · verdict)마다 `{값: 표시 글}` 과 SP 판정 키. 묶음 · 보고 묶음의 글은 이 표시 글만 쓴다.
