# M3 실행 계획 — WP4 등록부 병합 · 쟁점 토의 · 완결 판정 · 종합 보고서 (꾸러미 m3-synthesis)

> 2026-10-14 작성. 닻은 HWAXRisk `3aea93b` · HWAXAgentServer `412edde` · HWAXPortal `e329386` 에서 `grep` 으로 다시 찾은 것이다.
> 우선순위 — PLAN.md > M2.md(계약과 결정 #1~#25) > context-notes D-32·D-33·D-34 > **이 문서** > problems.md > reference/04-contract.md > reference/spec-wp4-issues-synthesis.md.
> 형제 계획 둘과 나눠 짓는다. `m3-cells.md` 는 전원 포함·입력 결손(`no_input`)·거르기(`na_irrelevant`)·표본 재검토·실패 셀 처분을, `m3-engine-ops.md` 는 엔진의 요약 호출 종류·관문(동시 8/4)·비우기를 맡는다. 이 문서는 그 둘에서 **받는 계약**만 적는다(3.9 · 3.13).
> v5 의 이 꾸러미 몫은 3.1 이다. `m3-cells.md` 의 몫과 한 블록으로 합친 뒤에만 커밋한다.
> 계획이며 코드는 아직 한 줄도 없다(`issues.py` · `synth.py` · `closure.py` · `chain.py` · `rr_issues` · `rr_reports` 는 세 리포 어디에도 없다).

## 1. 범위

### 들어오는 것

| 걸음 | WP4 | 무엇 |
|---|---|---|
| S3-0 | — | 시작 걸음 — 닻 재확인, 문제를 수용 기준으로 옮김, 형제 계획과 이름 맞춤 |
| S3-1 | 1 | 스키마 v5 의 이 꾸러미 몫(새 표 넷 · 열 열셋)과 반출·이양·폐기 배선 |
| S3-2 | 3 | 택소노미 1.2(메커니즘 14종)와 메커니즘 → 영역 배정표 자산 |
| S3-3 | 3(M2 #25) | 카드 대조 finding 의 메커니즘 — 앱 쪽(미분류 분리 · 영역 밖 표지). 엔진의 걸린 줄 `mech` 는 `m3-engine-ops` E3-4 |
| S3-4 | 2 | 등록부 병합 — 카드 대조 finding 을 `cells` 대상의 등록부에 넣는다, 지지 수 넷, 주장값, 쟁점 결과 덮어쓰기 |
| S3-5 | 7 | 잡 사슬 — 마감 범위가 끝났을 때만 쟁점 → 종합으로 잇고, 좁은 범위 뒤에는 코드 조립 보고서만 |
| S3-6 | 8(선정) | 쟁점 선정 — FAIL 을 가린 클러스터 유형 포함, 상한 24(P1 은 48) |
| S3-7 | 8(패널) | 쟁점 패널 — 기존 심의 엔진, 근거 꾸리기, 결과 묶기, 실패·재개 |
| S3-8 | 9 | 완결 판정 — 모든 레벨의 잔여, 실제로 검토한 전문가만 센다, 사람 확인 |
| S3-9 | 10 | 영역 요약 15건과 과제 종합 보고서(앱 사본 · 판 번호) |
| S3-10 | 12 | REST 와 MCP 도구 둘(`risk_get_issues` · `risk_get_report`, 와이어 25,000자 쪽 나누기) |
| S3-11 | 14 | JS 파이프라인 안내문 · 문서 · 업데이트 이력 |
| S3-12 | — | WP5b C10(이 꾸러미 몫) · C11 · C12 · C14 · C16 |
| S3-13 | 15 | dev 리허설 → v5 확정 → push · SIF · 게이트웨이 `tools/list` 31종 → cae00 전원 실주행 지원 |

### 빠지는 것

- 2차 영향 패스(`rr_cross_cells` · `cross` 종류 · `cross-pairs` 자산)와 결손 사냥(`rr_mech_cells` · `rr_mech_hunts` · `hunt` 종류)은 M4 다(PLAN 5절 · D-12). M3 는 셀의 넘김 줄(`rr_review_cells.handoffs_json`)과 메커니즘 신고(`mechs_json`)를 **표로만** 싣고, 완결 표기에 '2차 영향 미실행' · '결손 사냥 미실행' 을 단다.
- 쟁점 유형 `cross_dissent`(교차 칸이 없다) · `split_severity` · `mixed_direction`(hold 정책에서 거의 발화하지 않고 결과 판정에 구멍이 있다 — WP4 P-17-4)은 M4 다. 같은 대상의 리스크와 개선 행은 보고서 표에 나란히 보인다.
- `topic_key`(L2 묶음)와 `view=topics` 는 뺀다(프런트가 다른 세션이고 보고서는 주의 등급으로 접힌다 — WP4 cuts). v6 의 ADD COLUMN 으로 들어올 수 있다.
- RA 저장(WP4 11 — `push_report_to_ra` · `ra_*` 열)은 M4 다(PLAN 5절). 종합 보고서는 앱 REST 와 `risk_get_report` 로 읽는다. `ra_client.RA_REPORT_TOOLS` 는 건드리지 않는다.
- 전원 포함·입력 결손 호출·거르기·표본 재검토·실패 셀 처분 REST(`retry`·`skip`)는 `m3-cells.md` 다. 엔진의 `summary` 종류와 관문 손잡이는 `m3-engine-ops.md` 다.
- 쟁점 패널 자동 재개(재기동 뒤)는 M4 다(PLAN 3절 M4). M3 에서는 재기동이 쟁점 잡을 멈추고 사람이 재개한다.
- 카드 대조 finding 의 회수 자격(M2 #9 `recall_eligible = 0`)은 그대로 둔다(7절 (a)-3). 과제를 가로지르는 통계(`rr_delta_priors`)에 `cells` 대상은 M3 동안 기여하지 않는다(7절 (a)-2).
- HWAXRisk `frontend/` 는 다른 세션 몫이다. 응답 필드까지만 정한다.

## 2. 지금 코드 — M2 뒤의 사실과 닻

전부 `3aea93b` 에서 열어 확인한 것이다. 줄 번호는 참고이고 고칠 자리는 함수 이름으로 다시 찾는다.

- **스키마는 v4 로 굳었다.** `risk_store.py` `MIGRATIONS = [(1,…),(2,…),(3,…),(4, _DDL_V4)]`, `tests/test_store.py` `PUSHED_DDL_SHA256[4] = "f44b1630…"`. v4 가 이미 `rr_targets.flow` · `rr_jobs.mode`(주석 `NULL = panels · panels · reviews`) · `rr_jobs.hold_*` · `rr_findings.unit_id·source_kind·source_id·agent_key` 를 넣었다. 그래서 WP4 3.1.1 의 열 가운데 여덟은 이미 있다. v5 는 나머지다(3.1).
- **등록부는 카드 대조 finding 을 읽지 않는다(M2 #7·#20).** `card_review` 거름이 app 안에 **20곳** 이다. 대상 범위로 읽는 자리 셋 — `registry._load_findings` · `registry._contested_marking_done` · `routes._cluster_finding_ids`. 패널 범위이거나 패널 브리프에만 쓰이는 자리 넷 — `narrative.persist_panel_result` · `runner.repersist_panel` · `registry._minutes_lines` · `brief.scholar_query`. 과제를 가로지르는 학습·지표·야간 자리 열하나 — `learning._ATOM_SQL`·`_LABEL_SQL`·`on_label`·`_sample_claims`·`mine_patterns`, `metrics._finding_row`·`precedents_by_model`·`distinct_models`·`_load_atoms`·`sync_labels`, `nightly.scan_unclassified`. 카드 finding 이 걸릴 수 없는 자리 둘 — `routes._next_human_claim_uid`(사람 finding 순번) · `put_curation`(의심 문구 회수 — M2 #9). S3-4 는 대상 범위 셋만 흐름에 따라 연다.
- **지지 수는 패널 수다.** `registry._merge_cluster` 의 `support = len(panels) if panels else len(llm_members)`. 카드 대조 finding 은 `panel_id` 가 없어 원자 수로 떨어진다(xd 122명이 부풀린다 — m-16).
- **`close_level` 은 흐름을 가르지 않는다.** `registry.close_level` 은 `rr_coverage`·`rr_panels` 만 보고, `raised` 는 이미 돌려준다(WP1 R-47). C1 은 Tier A 패널 done 3건을 요구하므로 `cells` 대상은 지금 영원히 C0 이다. `_unresolved_parse_failures` 는 error 패널을 이미 세지 않는다(RR-ADV-3 — WP4 P-12 의 옛 흐름 절반은 끝났다).
- **통합 보고서는 저장되지 않는다.** `registry.build_consolidated_report` 는 `build_report` 를 불러 돌려줄 뿐이고, `runner._complete_panel` 이 `raised` 일 때 부르지만 값을 버린다. `GET /targets/{key}/report` 경로는 없다. `GET /reports` 는 RA 포인터(`rr_targets.report_ids_json`)만 읽는다.
- **영역 필터와 보고서 독자 키는 고쳐졌다(WP4 0d).** `routes.registry_payload` 는 `merged.domains`·`owner_domain` 으로 거른다.
- **잡 사슬의 자리.** 패널 잡은 `runner._finish_job` 이 닫고(Tier B 뒤 C3 면 Tier C 를 자동 큐), 검토 잡은 `review_runner.ReviewLoop._finish(job, 'completed', error)` 가 닫는다(`_complete_or_phase` — 범위 안 열린 셀 0 이면 실패 셀 수를 `error` 에 적고 `completed`). 둘 다 다음 단계를 부르는 자리가 없다(WP4 P-06). `runner.PANEL_JOBS_SQL = "COALESCE(mode, 'panels') = 'panels'"`, `FLOW_GATED_TIERS = ("A","B","C")` 이고 주석이 'M3 의 tier I 는 막지 않는다' 고 적어 두었다.
- **좌석 회차.** `narrative.persist_panel_result` 는 `origin in ('primary','counter')` 인 좌석만 `rr_coverage.cycle` 을 쓰고 나머지는 `NONLEDGER_CYCLE_BASE(100000) + panel_no` 다. 검토 의견은 `REVIEW_CYCLE_BASE(500) + cycle` 이다. 쟁점 패널은 모든 좌석이 원장 밖 회차여야 한다(S3-7).
- **카드에는 메커니즘 표지가 없다.** 엔진 `card_review.normalize_card` 의 칸은 `record_id·card_id·title·type·checkable·tier·confidence·causal_status·review_status·standard_refs·sources_n·sections` 뿐이다(03-cards 의 카드 머리와 같다). 판정 `v` 줄(`_STR_FIELDS[("verdict","v")]`)에도 `mech` 가 없다. 카드 밖 `f` 줄만 `mech`·`mech_free` 를 내고, 목록 밖이면 `free` 로 고친다(`_check_f`). 앱은 이미 모든 종류의 요청에 `extra.mechanisms`(택소노미 active 코드)를 싣는다(`engine_client.run_body` · `review_mechanisms`) — 엔진이 그 목록을 offcard 에만 그린다.
- **걸린 카드는 전부 단독 재질의를 받는다.** `review_runner._Session._solo_set` 이 실효가 FAIL·WARNING 인 카드, 변형이 갈린 카드, 빠진 카드를 고른다. `expert_report._card_members` 는 메커니즘을 `solo.get("mech") or eff.get("mech")` 로 읽는다 — 단독 줄에 `mech` 가 생기면 그대로 쓰인다.
- **hold 정책.** `expert_report._hold` 가 등록부로 갈 판정을 WARNING·중대까지로 묶고, 원래 값은 finding 의 `judgement_claimed`·`severity_claimed` 에 남는다(M2 사용자 결정 2).
- **택소노미는 1.1 이다.** `assets/taxonomy.v1.json` — 영역 15 · 메커니즘 38(interface 9·mechanical 8·material 6·thermal 5·electrical 5·process 5) · change_kind 14(M2 가 `contact_type`·`parameter` 를 더했다). `narrative._normalize_mechanism` 이 대분류 여섯을 코드에 박아 두었다. `schemas/risk_spec.v1.json` 의 `finding.mechanism` enum 도 여섯이다(영역 enum 은 15 — WP4 2.2 ⑧ 의 '12' 는 틀렸다, P-17-1).
- **근거 예산은 창에서 유도한다.** `brief.web_profile(engine_budget)` 이 엔진 `/health` 의 `evid_budget`(1M 창에서 약 500,000자)으로 `CAPS` 를 배수로 키운다. 쟁점 근거도 이 프로파일을 쓴다(WP4 의 16,000자 표는 128K 시절 값이다 — D-21).
- **엔진 쪽 `save_report`.** 포털 `DelibOpts` 에 선언돼 있고(M1 P1), 리스크 러너는 아직 보내지 않는다(`deliberation.py` 주석 — '러너가 save_report 를 보내지 않는다'). 쟁점 패널은 `save_report = 0` 을 보낸다(X3 — 비공개 과제의 RA 보고서 24~48건 방지).
- **MCP 쪽 나누기 선례.** `mcp_server.MCP_RESULT_CHARS = 25_000`, `_wire_chars` · `_fit_rows`(행 목록), `_report_page_chars`(쪽 크기를 와이어로 재며 줄인다), `routes.check_report_version`(409 `report_version_moved`). 도구는 29종이다(`tests/test_mcp_tools.py` `TOOL_NAMES`).
- **손잡이 자리.** `config.BOX_KNOBS`(`Knob(...)` — 환경변수 > `$DATA_DIR/knobs.env` > 기본값). 매니페스트 `launch.env` 는 두 키로 못 박혀 있다(`tests/test_manifest.py`).
- **로스터 실물(게이트웨이 `list_agents`, 10-14).** sh 는 센서·음향이다(`sh-acoustic-enclosure`·`sh-mems-mic`·`sh-microspeaker-transducer`·`sh-magnetometer-hall`·`sh-ambient-light-proximity` …). ESD 는 `rel-esd-eos` 와 `passive-tvs-esd`, 방수는 `mech-ip-sealing` 과 `rel-waterproof-ip`, 미광은 `cam-flare-ghost`, SAR 는 `rf-sar-compliance`, 자석 정렬은 `pwr-wireless-charging`, 홀 피드백은 `cam-ois-control` 이 갖는다. std 는 JEDEC·3GPP 규격 여덟 명뿐이라 WP4 부록 A 가 std 에 둔 SAR·EMI·공차·부식 자리는 맞지 않는다.

## 3. 계약 제안

### 3.1 스키마 v5 — 이 꾸러미 몫

어휘 열에는 CHECK 를 걸지 않는다(C-3 — 허용 연산이 CREATE·ADD COLUMN·INDEX 뿐이라 한 번 건 제약은 어휘를 늘릴 수 없게 만든다). 새 표는 전부 `owner_sub`·`target_key` 가 있다(`test_every_table_of_every_version_follows_the_conventions` 를 그대로 통과한다). `LOCAL_ONLY_TABLES` 에 더하는 표는 없다.

```sql
-- v5 — 리스크 심사 재설계 M3 의 WP4 몫(쟁점·종합·완결). m3-cells 의 몫과 한 블록 · 한 커밋으로 합친다.
-- dev 리허설(S3-13)이 끝날 때까지 push 하지 않는다 — 그때 tests/test_store.py 의 PUSHED_DDL_SHA256[5] 를 적는다.

ALTER TABLE rr_jobs ADD COLUMN chain_json TEXT;          -- {root_job_id, prev_job_id, stage, round, cells_hash, registry_hash, scope_open, reason}
                                                         -- rr_jobs.mode 어휘는 주석으로 넓힌다: NULL = panels · panels · reviews · issues · synth
ALTER TABLE rr_panels ADD COLUMN kind TEXT NOT NULL DEFAULT 'coverage';   -- coverage | issue
ALTER TABLE rr_panels ADD COLUMN issue_id TEXT;          -- kind='issue' 이면 rr_issues.issue_id
CREATE INDEX IF NOT EXISTS ix_rr_panels_kind ON rr_panels(target_key, kind, status);

ALTER TABLE rr_registry ADD COLUMN support_experts INTEGER;   -- 서로 다른 제기 전문가 수(쟁점 패널 원자·반대석·사람 제외)
ALTER TABLE rr_registry ADD COLUMN support_domains INTEGER;   -- 그 전문가들의 로스터 영역 수
ALTER TABLE rr_registry ADD COLUMN support_units INTEGER;     -- 서로 다른 unit_id 수(NULL 은 세지 않는다)
ALTER TABLE rr_registry ADD COLUMN support_verified INTEGER;  -- 검증된 인용이 1건 이상인 원자를 낸 전문가 수
ALTER TABLE rr_registry ADD COLUMN attention TEXT;            -- A | B | C | D (읽는 순서 — 판정이 아니다)
ALTER TABLE rr_registry ADD COLUMN issue_id TEXT;
ALTER TABLE rr_registry ADD COLUMN issue_state TEXT;          -- NULL | queued | planned | running | upheld | downgraded | escalated | rejected | undetermined | untried_cap | skipped | withdrawn
CREATE INDEX IF NOT EXISTS ix_rr_registry_attention ON rr_registry(target_key, attention, priority);

ALTER TABLE rr_targets ADD COLUMN level_label TEXT;      -- 완결 표기(잔여 포함). 맨 레벨 이름은 잔여 0 일 때만
ALTER TABLE rr_targets ADD COLUMN closure_json TEXT;     -- closure.cell_counts·잔여의 캐시(진행판 5초 폴링이 원장을 다시 세지 않게 — P-17-13)
ALTER TABLE rr_targets ADD COLUMN closure_at INTEGER;

CREATE TABLE IF NOT EXISTS rr_issues (                   -- 쟁점. 등록부 클러스터 하나에 하나
  issue_id TEXT PRIMARY KEY,                             -- 'iss-' + sha1(target_key|anchor_cluster_key)[:12]
  target_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  anchor_cluster_key TEXT NOT NULL,                      -- .imp 없는 base 키 — resolve_cluster_key 를 지난 값(P-17-6)
  unit_id TEXT,                                          -- 대표 원자의 단위
  types_json TEXT NOT NULL,                              -- ["held_fail","solo_severe","split_verdict"] 가운데 걸린 것 전부
  p_class TEXT NOT NULL,                                 -- P1 | P2 | P3
  priority REAL NOT NULL, rank INTEGER,                  -- 선정 순서(1부터, 결정론)
  basis_json TEXT NOT NULL,                              -- {raisers[], opposers[], claimed{}, distribution{}, registry_before{}, refs[]} — 편성 때 동결
  basis_hash TEXT NOT NULL,                              -- 제기자·반대자 집합과 주장값의 해시 — 바뀌면 다시 고른다(P-01 ⓐ)
  seats_json TEXT,                                       -- 패널을 만들 때 동결 [{key, domain, origin, rank_in_domain, issue_role}]
  state TEXT NOT NULL DEFAULT 'queued',                  -- queued | planned | running | resolved | inconclusive | untried_cap | withdrawn | skipped
  state_reason TEXT,                                     -- cap | engine_fail | chain_cancelled | spec_parse_failed | no_decision | no_matching_atom | human
  outcome TEXT,                                          -- upheld | downgraded | escalated | rejected | undetermined
  outcome_json TEXT,                                     -- {panel_id, atom_finding_ids[], severity_after, judgement_after, grade_after, contest_note}
  panel_id TEXT,                                         -- 지금 그 쟁점의 패널 — resolve_issue 는 이것과 같은 패널의 결과만 쓴다(P-17-5)
  attempts INTEGER NOT NULL DEFAULT 0, charged INTEGER NOT NULL DEFAULT 0,
  selected_round INTEGER NOT NULL DEFAULT 1, cells_hash TEXT,   -- 고를 때의 마감 범위 셀 지문
  reraised_json TEXT,                                    -- 닫힌 뒤 새 영역이 다시 제기했을 때의 표기(자동 재토의 없음)
  status_source TEXT NOT NULL DEFAULT 'code', decided_by TEXT, decided_at INTEGER, reason TEXT,
  created_at INTEGER, updated_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS ux_rr_issues_anchor ON rr_issues(target_key, anchor_cluster_key);
CREATE INDEX IF NOT EXISTS ix_rr_issues_state ON rr_issues(target_key, state, rank);

CREATE TABLE IF NOT EXISTS rr_summaries (                -- 영역 요약·과제 종합의 LLM 서술과 코드 대조 결과
  summary_id TEXT PRIMARY KEY,                           -- 'sm-' + sha1(target_key|scope_kind|scope_key|input_hash)[:16]
  target_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  scope_kind TEXT NOT NULL, scope_key TEXT NOT NULL,     -- domain '<영역 코드>' | target '-'
  input_hash TEXT NOT NULL, input_chars INTEGER, n_rows INTEGER,
  state TEXT NOT NULL DEFAULT 'pending',                 -- pending | running | done | code_only
  state_reason TEXT,                                     -- no_rows | content_fail | infra_exhausted | ctx_too_small | checks_failed
  output_json TEXT, checks_json TEXT,                    -- 객체로 옮긴 출력 · {missing[], nums_unsourced[], refs_outside[], retried}
  attempts INTEGER NOT NULL DEFAULT 0, charged INTEGER NOT NULL DEFAULT 0,
  infra_streak INTEGER NOT NULL DEFAULT 0, not_before INTEGER,
  run_id TEXT, call_id TEXT, model TEXT, prompt_rev TEXT, error_code TEXT, error TEXT,
  created_at INTEGER, finished_at INTEGER, updated_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_rr_summaries_scope ON rr_summaries(target_key, scope_kind, scope_key, created_at);

CREATE TABLE IF NOT EXISTS rr_reports (                  -- 종합 보고서 판(앱 사본이 정본 — RA 투영은 M4)
  report_uid TEXT PRIMARY KEY,                           -- 'rp-' + sha1(target_key|version_no)[:16]
  target_key TEXT NOT NULL, owner_sub TEXT NOT NULL,
  version_no INTEGER NOT NULL,
  trigger TEXT NOT NULL,                                 -- reviews_partial | reviews_closed | issues_closed | synth_done | ack | manual | level_up
  flow TEXT NOT NULL, level TEXT NOT NULL, level_label TEXT NOT NULL,
  narrative_state TEXT NOT NULL,                         -- none | partial | full — 서술이 붙은 정도
  title TEXT NOT NULL,
  counts_json TEXT NOT NULL,                             -- 그 판을 만들 때의 closure 수(보고서 머리와 같은 값)
  closure_hash TEXT NOT NULL, cells_hash TEXT NOT NULL, registry_hash TEXT NOT NULL,
  summary_ids_json TEXT,
  pages_gz BLOB NOT NULL, pages_n INTEGER NOT NULL,      -- gzip(JSON [{page_no, kind, title, blocks{background[], results[], recommendation[], minutes[]}}])
  content_hash TEXT NOT NULL,                            -- 직전 판과 같으면 새 판을 만들지 않는다
  created_at INTEGER NOT NULL,
  UNIQUE(target_key, version_no));

CREATE TABLE IF NOT EXISTS rr_close_acks (               -- 완결 잔여의 사람 확인. rr_gate_acks 와 같은 관례에 이력을 남긴다
  target_key TEXT NOT NULL, item TEXT NOT NULL, ack_at INTEGER NOT NULL,
  owner_sub TEXT NOT NULL,
  ack_by TEXT NOT NULL, ack_reason TEXT NOT NULL,        -- 300자 안, 빈 문자열이면 422
  basis_n INTEGER NOT NULL, basis_hash TEXT NOT NULL,    -- 확인 시점 잔여 수와 그 행 집합의 sha256[:12] — 집합이 바뀌면 낡은 확인이다
  revoked_by TEXT, revoked_at INTEGER,                   -- 취소는 행을 지우지 않고 표기한다
  PRIMARY KEY(target_key, item, ack_at));                -- 유효한 확인 = 그 item 의 revoked_at 이 NULL 인 가장 늦은 행(P-11)
```

- WP4 3.1 에서 바꾼 것 — `rr_close_acks` 의 PK 에 `ack_at` 을 넣어 재확인 이력이 남는다(P-11). `rr_reports` 에서 `ra_*` 열을 뺐다(M4 가 v6 ADD COLUMN 으로). `rr_summaries.n_rows_omitted` 를 뺐다(1M 창에서 행을 버리지 않는다 — 넘치면 `ctx_too_small` 로 `code_only` 이고 크게 알린다, D-21). `rr_issues` 에 `rank`·`state_reason`·`charged`·`cells_hash` 를 더하고 결과 어휘에 `escalated` 를 더했다(3.6). 후속 단계의 낡음 판정(X1-07)은 새 표(`rr_post_runs`) 대신 `rr_jobs.chain_json.cells_hash` 와 `rr_reports.cells_hash` 로 한다.
- 주장값·분포·쟁점 전 값은 열이 아니라 `rr_registry.merged_json` 의 `claimed` · `distribution` · `before_issue` 칸이다(3.5). `cells` 대상에만 쓴다 — 패널 대상의 `merged_json` 바이트가 그대로다.
- 요약 호출은 새 표가 아니라 `rr_review_calls`(kind `summary`, `agent_key='synth'`, `unit_id` NULL, `run_id` = 종합 잡)에 한 행씩 남긴다. 차단기·호출 초 집계가 같은 원장을 읽는다.
- 반출·이양·폐기 — `export._SINCE_COLS` 에 `rr_issues:updated_at` · `rr_summaries:updated_at` · `rr_reports:created_at` · `rr_close_acks:ack_at`. 행 변환 셋을 더한다 — `rr_panels.brief_gz` 는 `kind='issue'` 행에서 비운다(쟁점 근거 I6 에 카드 절 원문이 든다 — 사용자 결정 1 의 반출 200자) · `rr_registry.merged_json` 의 `card:` 인용과 근거 문장 «» 를 200자로 줄이고 원래 길이를 적는다(M2 #18·#21 의 규칙을 등록부로 넓힌다 — M3 부터 카드 인용이 등록부에 들어온다) · `rr_issues.basis_json` 의 인용도 같다. `routes.TRANSFER_DERIVED` 에 넷. `routes.PURGE_BLANK_SQL` — `rr_issues`(basis_json·outcome_json·seats_json·reraised_json) · `rr_summaries`(output_json·checks_json) · `rr_reports`(pages_gz 를 빈 gzip 으로 — NOT NULL) · `rr_close_acks`(ack_reason 을 `[purged]`) · `rr_targets.closure_json`.

### 3.2 메커니즘 → 영역 배정표 — 모양과 자리

- **자리.** 새 자산 `HWAXRisk/backend/app/assets/mech-owners.v1.json`. 택소노미 파일 안에 넣지 않는다 — 배정은 사람이 고치는 정책이고, 고칠 때마다 `taxonomy_version`(IR·지표 키의 접미 `@<taxonomy_version>` 이 된다 — `nightly`)을 올리면 안 된다. `taxonomy.VOCAB_ASSETS` 에 이름을 더해 `/meta/vocab` 이 판을 보이고, `risk_taxonomy`(MCP)와 `GET /meta/taxonomy` 가 표를 함께 준다(사용자가 Claude 에서도 훑을 수 있게).
- **모양.**

```json
{"mech_owners_version": "1.0", "taxonomy_version": "1.2", "review_status": "draft",
 "reviewed_by": null, "reviewed_at": null,
 "note": "소유 = 그 메커니즘을 아무도 안 봤을 때 누구에게 묻나(쟁점 패널 인접 석 · M4 결손 사냥). 관련 = 그 영역 사람이 이 메커니즘을 말해도 믿나. 거르기의 코드 신호는 소유 ∪ 관련을 '관련 있음' 으로 읽는다.",
 "rows": [{"code": "thermal.cte_mismatch", "owners": ["rel", "material"], "related": ["pcb", "mech", "sim", "disp"]}]}
```

- **읽는 함수(`taxonomy.py`).** `mech_owners() -> dict[code, {owners: tuple, related: tuple}]` · `domains_for(codes) -> dict[domain, 'owner'|'related']` · `mechanisms_of(domain) -> {owner: [...], related: [...]}` · `mech_owners_meta() -> {version, review_status, reviewed_at}`.
- **소비자.** ① `m3-cells` 의 거르기 코드 신호 — 단위의 변경 → 후보 메커니즘(그쪽 몫) → 이 표 → 영역. ② 쟁점 패널의 인접 석(S3-7). ③ 카드 대조 finding 의 메커니즘이 그 전문가 영역 밖이면 표지 `mech_out_of_domain`(S3-3, 판정을 바꾸지 않는다). ④ M4 결손 사냥의 대표.
- **승인 문.** `review_status` 가 `approved` 가 아니면 거르기의 코드 신호는 `unknown` 으로 읽는다(D-33 ② '하나라도 관련·모름이면 본다' — 승인 전에는 거르기가 사실상 꺼진다). 코드는 승인 전에 들어가도 되고, 사용자가 표를 훑은 뒤 `review_status:"approved"` · `reviewed_by` · `reviewed_at` 만 고친 커밋이 거르기를 연다. 시험이 이 문을 지킨다.
- **불변식(시험).** 택소노미 active 코드마다 정확히 한 행이 있고 소유가 1개 이상이다. 영역 이름은 전부 택소노미 영역 15개 안이다. 15개 영역이 전부 어느 행엔가(소유 또는 관련) 나온다. 한 행에서 소유와 관련이 겹치지 않는다.
- 초안 표는 3.4 에 있다.

### 3.3 M2 #25 의 결정 — 카드 대조 finding 의 메커니즘

**권고 — 판정 틀에 `mech` 를 더한다(엔진 `prompt_rev` 를 `cr-verdict-2` 로 올린다). 걸린(WARNING·FAIL) 줄에만 필수다.** 카드 표지에서 유도하는 길은 쓰지 않는다. 엔진 쪽 변경은 `m3-engine-ops.md` E3-4 가 맡고, 이 꾸러미는 앱 쪽(미분류 분리·영역 밖 표지)을 맡는다.

- **까닭.** ① 유도할 표지가 없다 — 카드 머리에 메커니즘 칸이 없고(2절) 태그도 type·tier·confidence 셋뿐이다(03-cards). ② D-34 는 '#25 도 배정표 위에서 정한다' 고 했지만 배정표는 메커니즘 → 영역이라 거꾸로(영역 → 메커니즘) 읽으면 한 영역에 메커니즘이 십수 개다(mech 는 소유·관련 30여 개). 카드 하나의 메커니즘을 고를 수 없다. 배정표는 검사(`mech_out_of_domain`)에만 쓴다. ③ 카드 제목·본문 낱말로 동의어 사전을 맞추는 길은 조용히 틀린다 — 맞지 않으면 아무 표시 없이 다른 메커니즘으로 접힌다(X1 의 '실패가 정상 응답과 같은 모양'). ④ finding 이 되는 것은 걸린 행뿐이고(`_card_members`), 걸린 카드는 이미 전부 단독 재질의를 받는다(`_solo_set`) — 걸린 줄에 칸 둘을 더하면 finding 전부가 메커니즘을 갖고 호출 수는 늘지 않는다. OK·해당 없음 줄에는 칸을 요구하지 않으므로 카드 전수 판정의 출력 토큰은 거의 그대로다. ⑤ 앱의 읽는 쪽(`expert_report._card_members` 의 `solo.get("mech")`)이 이미 있다.
- **엔진 — `m3-engine-ops.md` E3-4 가 한다(같은 모듈을 두 꾸러미가 고치지 않는다 — WP4 P-07).** 그 계획은 `v` 줄 전부에 `mech`·`mech_free` 칸을 두되 **WARNING·FAIL 줄에만 필수**로 하고, verdict 요청이면 변형과 상관없이 [메커니즘 목록](P 의 5%, 52종이면 약 1,500자)을 싣는다. 목록 밖은 `free` + `mech_free`, 걸렸는데 비면 `checks.mech='missing'` 표지만(보충 사유가 아니다). `PROMPT_REV["verdict"] = "cr-verdict-2"`. 처음 이 계획은 단독 재질의 줄에만 두자고 적었는데, 그쪽 안이 낫다 — 걸린 카드의 단독 재질의가 끝내 빠져도 묶음 판정 줄의 `mech` 가 남고, 늘어나는 것은 호출마다 목록 1,500자(1M 창의 0.2% 미만)와 걸린 줄의 40자뿐이다. 그쪽 안을 받는다.
- **앱.** `mech` 가 비거나 `free` 면 `mechanism_detail = 'unclassified'` 이고 클러스터 키의 세부 자리에 `'unclassified~' + free_key` 를 넣는다(WP4 3.3.4 (다)). `free_key` 는 `mech_free` 를 NFKC·소문자·공백·구두점 제거한 앞 24자이고, `mech_free` 도 비면 `'card~' + (card_id or record_id)` 다. 같은 규칙을 `family_key` 에도 건다(P-17-6 — 갈라 놓은 것을 근접 중복 스캔이 다시 묶지 않게). **이 분리는 `flow='cells'` 대상의 finding 에만 건다** — 패널 대상의 새 finding 키는 지금 식 그대로다(D-24 회귀 가드).
- **비용과 위험.** `cr-verdict-2` 로 오르면 살아 있는 검토 잡은 다시 계획하고 입력 지문이 바뀐 셀을 처음부터 돈다(M2.md 4.8 — `prompt_rev` 는 셀 `input_hash` 에 든다). 그래서 이 변경과 택소노미 1.2(요청 본문의 `extra.mechanisms` 가 바뀐다)는 **살아 있는 검토 잡이 없을 때** 배포한다(절차서에 적는다). cae00 의 M2 파일럿 대상에서 이미 마감된 finding 은 다시 마감해도 메커니즘이 생기지 않는다(단독 줄을 다시 묻지 않는다) — 그 finding 은 `unclassified~` 로 갈려 남는다. 받아들인다.
- **`m3-engine-ops` 와의 맞춤.** 이 꾸러미가 기대는 것은 둘이다 — `rr_card_verdicts.mech` 에 실효 행(단독 재질의가 있으면 그것, 없으면 묶음 판정)의 코드가 오는 것, 그리고 셀 지문(`review_runner.prompt_key`)을 그 셀이 부르는 종류의 판만으로 잇는 것(`m3-cells` C3-3 — `summary` 판이 올라도 셀이 다시 돌지 않게). 앱의 읽는 쪽은 `solo.get("mech") or eff.get("mech")` 그대로다.

### 3.4 메커니즘 → 영역 배정표 초안 (사용자 검토용 — D-34)

**사용자가 한 번 훑을 표다.** 52행(기존 38 + 새 14)이다. '소유' 는 그 메커니즘을 아무도 안 봤을 때 누구에게 묻나(쟁점 패널의 인접 석, M4 결손 사냥의 대표 — 순서가 뜻이 있다, 첫째가 먼저), '관련' 은 그 영역 사람이 그 메커니즘을 말해도 믿나다. **거르기의 코드 신호는 소유 ∪ 관련을 '관련 있음' 으로 읽는다** — 표에 영역을 넣을수록 그 영역 셀은 덜 걸러진다(호출이 는다), 빼면 그 영역은 훑기 판단 하나로 걸러질 수 있다(D-33 ②). 바탕은 WP4 부록 A 이고, 게이트웨이 로스터(10-14 `list_agents`)를 보고 바꾼 칸에 ✱ 를 달았다. 영역 코드는 택소노미의 것이다(xd 외관·조립 설계 · sim 해석 · cam 카메라 · rel 신뢰성 · soc SoC · disp 디스플레이 · mech 기구 · pcb PCB · rf RF·안테나 · passive 수동 소자 · pwr 전원·배터리 · sh 센서·음향 · mem 메모리 · std 규격(JEDEC·3GPP) · material 재료).

| 코드 | 이름 | 소유 | 관련 | 바꾼 까닭(✱) · 로스터 근거 |
|---|---|---|---|---|
| thermal.cte_mismatch | CTE 불일치 | rel · material | pcb · mech · sim · disp | |
| thermal.thermal_shock | 열충격 | rel | sim · material · pcb · cam✱ | ✱ cam-module-rel(열충격·온도사이클) |
| thermal.hotspot | 국부 발열 | mech✱ · soc · pwr | sim · disp · cam✱ | ✱ 세트 열설계는 mech(mech-thermal-architecture·mech-vapor-chamber·mech-graphite-spreader) · cam-flash-led |
| thermal.thermal_resistance | 열저항 | mech · soc | pwr · material · sim · std✱ | ✱ std-jedec-thermal-metrology |
| thermal.solder_fatigue | 솔더 열피로 | rel · pcb | sim · passive · mem · soc · std✱ | ✱ std-jedec-failure-model |
| mechanical.drop_stress | 낙하 응력 | sim · mech | rel · disp · cam · xd · pcb✱ | ✱ 보드 스트레인(pcb-solder-joint-reliability) |
| mechanical.bending | 굽힘 | mech · sim | disp · pcb · rel · passive✱ | ✱ passive-mlcc-flex-crack |
| mechanical.buckling | 좌굴 | mech · sim | xd · disp✱ | ✱ 폴더블 적층(disp-foldable-stackup) |
| mechanical.fatigue | 피로 | rel · mech | sim · material | |
| mechanical.vibration | 진동 | sim · rel | mech · cam · sh | |
| mechanical.press_fit | 압입 | mech · xd | material · pcb✱ | ✱ pcb-btb-connector(체결력) |
| mechanical.rattle | 덜그럭 | xd · mech | sh · cam | |
| mechanical.mass | 질량 | mech · xd | sim · pwr | |
| interface.tied | 접합 | mech | xd · material | |
| interface.touching | 접촉 | mech | xd · disp · cam | |
| interface.clearance | 간극 | mech · xd | pwr · disp · cam · rf | |
| interface.interference | 간섭 | mech · xd | disp · cam · pcb | |
| interface.tied_loss | 접합 상실 | mech | rel · material | |
| interface.clearance_close | 간극 근접 | mech · xd | pwr · rf · disp | |
| interface.adhesive_area | 접착 면적 | mech · material | disp · rel · xd | |
| interface.tolerance_stackup | 공차 누적 | xd · mech | cam✱ · disp✱ | ✱ std 를 뺐다(std 에 공차 전문가 없음) · cam-aa-process · disp-module-bonding |
| interface.cross_file_untrusted | 파일 사이 불신 | sim | mech | |
| electrical.net | 넷 | pcb | soc · pwr · passive · mem · rf | |
| electrical.si_pi | SI·PI | pcb · soc | mem · pwr · passive | |
| electrical.emi | EMI | rf · rel✱ · pcb | soc · pwr · mech✱ · passive✱ | ✱ std 를 뺐다 · rel-emc · mech-emi-shielding · passive-ferrite-bead |
| electrical.creepage | 연면 거리 | pwr · pcb | rel✱ | ✱ std 를 rel 로(std 에 해당 전문가 없음) |
| electrical.pad_lift | 패드 들뜸 | pcb · rel | passive · mem | |
| material.creep | 크리프 | rel✱ · material | mech | ✱ 순서 — material 은 1명이고 카드 0장(P-15) |
| material.moisture | 흡습 | rel✱ · material | pcb · disp | ✱ 순서(P-15) · rel-humidity-bias |
| material.corrosion | 부식 | rel✱ · material | mech · pcb✱ | ✱ 순서 · std 를 뺐다 · rel-chemical-corrosion · pcb-surface-finish |
| material.property_uncertain | 물성 불확실 | material | sim | |
| material.adhesive_aging | 접착 열화 | rel✱ · material | disp · mech | ✱ 순서(P-15) |
| material.supplier_change | 공급사 변경 | material · rel✱ | std✱ · passive✱ | ✱ rel-supplier-quality · std-jedec-qual-program · passive-component-engineering |
| process.tolerance | 공정 공차 | xd | mech · rel✱ | ✱ std 를 뺐다 · rel-spc-yield |
| process.solder | 솔더링 | pcb | passive · rel · mem · std✱ | ✱ std-jedec-package-outline(코플래너리티) |
| process.adhesive_cure | 접착 경화 | material · xd | disp · mech · rel✱ | ✱ rel-fastening-bonding |
| process.screw_torque | 나사 토크 | xd · mech | rel | |
| process.warpage | 휨 | pcb · disp | sim · material · mech | |
| **optical.alignment** | 광축·틸트·초점 | cam | mech · xd · sh · disp | cam-aa-process · cam-lens-design · cam-folded-prism · sh-tof-ranging(창 정렬) · disp-upc |
| **optical.stray_light** | 미광·플레어·빛샘 | cam · disp | sh · xd · mech | cam-flare-ghost · disp-polarizer-optics · sh-ambient-light-proximity(크로스톡) |
| **optical.contamination** | 이물·김서림 | cam | sh · rel · xd | cam-module-rel(렌즈 포깅·이물) · sh 센서 창 |
| **acoustic.leak** | 음향 누설·실링 | sh | mech · rel · xd | sh-acoustic-enclosure · sh-mems-mic · mech-ip-sealing · rel-waterproof-ip |
| **acoustic.resonance** | 공진·이음 | sh | mech · passive · sim | sh-microspeaker-transducer · sh-lra-actuator · passive-mlcc-acoustic · passive-power-inductor(코일 울음) |
| **acoustic.port_block** | 음향 포트 막힘 | sh | mech · xd · rel | sh-acoustic-enclosure(포트·메쉬·멤브레인) |
| **rf.detune** | 공진 주파수 이동 | rf | mech · xd · disp | rf-antenna-design · mech-lds-antenna · mech-metal-frame |
| **rf.efficiency** | 방사 효율·흡수 | rf | mech · disp · std | rf-ota-certification · mech-exterior-materials(외장 투과) · std-3gpp-ue-rf |
| **rf.isolation** | 격리·간섭·디센스 | rf | pcb · soc · mech · passive | rf-desense · rf-coexistence · mech-emi-shielding · passive-ferrite-bead |
| **rf.sar** | 전자파 흡수율 | rf | mech · sh | ✱ WP4 의 소유 std 를 뺐다(std 에 SAR 전문가 없음) · rf-sar-compliance · sh 근접·그립 센서 |
| **interface.seal_compression** | 실링 압축량 | mech · xd | material · rel · sh | mech-ip-sealing(압축률·압축영구변형) |
| **interface.ingress_path** | 침수·분진 경로 | mech · rel | xd · sh · pcb | rel-waterproof-ip · pcb-usbc-receptacle(수분 감지) |
| **electrical.esd** | 정전기 방전 경로 | rel · passive | pcb · mech · pwr · xd | ✱ WP4 의 소유 pcb 를 rel·passive 로 · rel-esd-eos · passive-tvs-esd · pwr-input-protection(케이블 방전) |
| **electrical.magnetic_interference** | 자기 간섭(자석·홀·코일) | sh | cam · pwr · rf · mech | ✱ WP4 '미정' 을 sh 로 · sh-magnetometer-hall · cam-ois-control·cam-vcm-actuator · pwr-wireless-charging(자석 정렬) · rf-nfc(페라이트) |

새 대분류는 셋(`optical` · `acoustic` · `rf`)이고 기존 대분류에 넷을 더한다(interface 2 · electrical 2). 대분류 `rf` 는 영역 코드 `rf` 와 글자가 같다 — 두 축을 문자열로 잇는 코드는 없지만(영역은 좌석 키 접두에서 온다) 동의어 사전에 `rf` 를 낱말로 넣지 않는다(6절 위험).

**훑을 때 봐 주면 좋은 셋.**
1. **xd(122명)를 얼마나 넓게 두나.** 지금 초안은 xd 를 52개 가운데 24개에 둔다(소유 11 · 관련 13). mech 는 41개, rel 은 27개다. xd 셀은 전 셀의 약 3분의 1 이라 xd 가 표에 넓게 있으면 거르기가 줄이는 호출이 크게 준다. 좁히면 조립·외관이 걸린 변경에서 xd 를 훑기 판단 하나로 거를 수 있다.
2. **mem·std 는 관련으로만 있다.** 소유인 코드가 없다. 단위의 변경이 그 메커니즘으로 이어지지 않으면 이 두 영역은 훑기 판단 하나로 걸러질 수 있다(영역 1순위 대표는 거르지 않는다 — D-33 ①).
3. **material 은 1명·카드 0장이다.** 재질 메커니즘의 첫 소유를 rel 로 바꿨다(P-15). 쟁점 패널의 인접 석과 M4 사냥이 rel 로 먼저 간다.

### 3.5 등록부 병합 — 지지 수 · 주장값 · 쟁점 결과 덮어쓰기

- **어느 finding 을 읽나.** 새 함수 `registry.finding_scope(store, target_key) -> (sql 조각, params)` 하나가 정한다. `flow='cells'` 이면 출처를 가리지 않고 전부(패널·카드 대조·쟁점 패널·사람), `flow='panels'` 이면 지금처럼 `COALESCE(source_kind,'') <> 'card_review'` 다. 대상 범위로 읽는 세 자리(`_load_findings` · `_contested_marking_done` · `routes._cluster_finding_ids`)가 이 함수를 부른다. 나머지 열일곱 자리는 그대로 두고 까닭을 한 줄 주석으로 단다(패널 범위·패널 브리프 넷은 `cells` 대상에서 돌지 않거나 카드 finding 이 `panel_id` 가 없어 안 걸린다 · 과제를 가로지르는 열하나는 M2 #9 를 지킨다 · 나머지 둘은 카드 finding 이 걸릴 수 없다). 시험이 app 안의 `card_review'` 출현 자리를 목록으로 못 박는다(새 자리를 넣으면 분류를 강제한다).
- **패널을 돌린 뒤 `cells` 로 바꾼 대상**(얹기 — M2 #3)은 두 출처가 한 등록부로 합쳐진다. 비교용 '패널만 본 등록부' 는 저장하지 않고 `GET …/registry?source=panels` 가 그 자리에서 `merge(…, persist=False, include_card=False)` 로 계산한다(7절 (a)-1).
- **지지 수 넷(`_support_counts`).** 기각되지 않은 llm 원자 가운데 `source_kind <> 'issue_panel'` 인 것에서 센다(쟁점 패널 원자는 이미 센 사람을 다시 앉힌 것이라 세지 않는다 — 덮어쓰기 값으로만 쓴다). 반대석·의장·사람은 세지 않는다.
  - `support_experts` = 서로 다른 제기 전문가(`finding_json.raised_by`, 없으면 `agent_key`).
  - `support_domains` = 그 전문가들의 로스터 영역 수(로스터에 없으면 키 접두).
  - `support_units` = 서로 다른 `unit_id`.
  - `support_verified` = `finding_json._resolved_cites` 에 `ok` 이고 `verified` 인 행이 1개 이상인 원자를 낸 전문가 수(카드 행이면 앱 재대조 `quote_ok = 1` 이다).
  - 기존 `support` 는 `cells` 대상에서 `support_experts` 와 같은 값, 패널 대상에서 지금 식 그대로다. 새 열 넷은 두 흐름 모두 채운다(패널 대상은 참고값 — 등록부 행 바이트가 바뀌므로 패널 대상의 바이트 동일 시험은 `_MERGE_OWNED_COLUMNS` 의 옛 열과 `merged_json` 을 견준다).
- **주장값(hold 정책의 이음 — WP4 P-02 · X1-18).** `cells` 대상의 `merged_json.claimed` = `{judgement, severity, sev3, fail_experts, critical_experts, verified_fail_experts}` — 살아 있는 카드 대조 원자의 `judgement_claimed`·`severity_claimed` 최댓값과, 그 값을 낸 서로 다른 전문가 수, 그 가운데 카드 인용이 대조를 지난 전문가 수다. `merged_json.distribution` = `{by_judgement_claimed{}, by_severity{}, raisers_by_domain{}}`(사람이 '12명 · FAIL 9 · WARNING 3' 을 읽는 원천).
- **주의 등급(`attention_of`).** WP4 3.10.2 의 식에 넣는 `sev3`·`judgement` 를 `max(등록부 값, 검증된 주장값)` 으로 바꾼다 — 검증된 주장값 = `verified_fail_experts ≥ 1` 일 때의 주장값(X1-18 (1)). 치명·FAIL 은 어느 경우에도 B 이상이다. 정렬은 등급 → 우선순위 → `support_domains` → `support_experts` → 키.
- **쟁점 결과의 덮어쓰기(D-34 — 덮되 원래 분포를 같은 줄에).** `merge()` 가 그 대상의 `rr_issues`(state `resolved`)를 `resolve_cluster_key` 를 지난 닻 키로 읽어 `_merge_cluster(…, issue=…)` 에 넘긴다.

| 쟁점 결과 | 등록부 행 |
|---|---|
| `upheld` · `downgraded` · `escalated` | 행의 `severity`·`sev3`·`judgement`·`evidence_grade` 를 그 쟁점의 **지금 패널**(`rr_issues.panel_id`) 원자 값으로 둔다. 구성원에서 계산한 값은 `merged_json.before_issue = {severity, sev3, judgement, claimed, distribution, support_*}` 에 남는다. 우선순위를 다시 센다 |
| `rejected` | 사람 finding 이 없으면 `code_status='rejected_in_panel'`, `rejected` 는 기각 원자 수. 지지 수는 지우지 않는다('제기 12명 · 패널 기각' 으로 보인다) |
| `undetermined` · 쟁점 없음 | 지금 그대로 |

  - 사람이 정한 상태는 어느 경우에도 건드리지 않는다(`registry._write_registry_row` 의 지금 규칙). 쟁점 패널의 FAIL 은 hold 를 지나지 않으므로 등록부에 FAIL 로 선다 — 판정 후보가 `no-go` 가 될 수 있다(M2 사용자 결정 2 — 'FAIL 은 쟁점 토의나 사람이 올린다').
  - 닫힌 쟁점 뒤에 **새 영역**의 전문가가 같은 클러스터를 제기하면 `rr_issues.reraised_json` 과 등록부 `needs_review_json` 에 표기만 한다(자동 재토의 없음). 다시 고를 때의 규칙은 3.6.
  - 패널 대상에는 쟁점이 없으므로 이 갈래가 돌지 않는다.
- **과제를 가로지르는 기여.** `cells` 대상은 M3 동안 `rr_delta_contrib` 에 기여하지 않는다 — `_recompute_contrib` 가 그 대상의 기여 행을 비운다(`STATS_VERSION` 그대로). 카드 대조 원자는 회수 자격이 0 이고(M2 #9), 쟁점 패널 원자만 따로 세는 규칙은 M4 의 회수 승인과 함께 정한다(7절 (a)-2).
- **재제기 비교(`_is_stronger`).** `cells` 대상의 행은 `support_domains` 로 견준다. 사람이 닫을 때 `set_status` 가 `status_basis_json.support_domains_at_decision` 을 함께 적고, 기준선에 그 값이 없으면 새 행의 `support_domains` 를 옛 `support_at_decision` 과 견준다(P-17-10).
- **반출.** `merged_json` 의 `card:` 인용·근거 문장 «» 를 200자로 줄이고 원래 길이를 적는다(3.1 · 사용자 결정 1).

### 3.6 쟁점 — 유형 · 등급 · 상한 · 결과

닻은 등록부 클러스터 하나다. 한 클러스터가 여러 유형에 걸리면 쟁점은 하나이고 `types_json` 에 전부 적는다. 사람이 이미 닫은 행(`status_source <> 'code'`)은 올리지 않는다. 고르는 것은 코드다(LLM 0회).

| 유형 | 조건(전부 `cells` 대상의 등록부·셀·판정 행에서) | 반대 측 |
|---|---|---|
| `held_fail` | 살아 있는 카드 대조 원자 가운데 `judgement_claimed='FAIL'` 또는 `severity_claimed='치명'` 이 1건 이상(= FAIL 을 hold 가 가린 클러스터, P-02) | 같은 단위·겹치는 변경 참조에 `applies='yes'`·OK 를 낸 전문가(있으면) |
| `solo_severe` | 리스크 행이고 `max(sev3, claimed.sev3) ≥ 2` 이며 `support_experts = 1` | 없음 — 인접 석을 앉힌다 |
| `split_verdict` | 대표 메커니즘이 `unclassified` 가 아니고, 같은 단위에서 그 원자의 변경 참조와 겹치는 줄에 `applies='yes'`·`judgement='OK'`·`quote_ok=1` 을 낸 **다른** 전문가가 `HWAXRISK_ISSUE_SPLIT_MIN_OPPOSERS`(2)명 이상이고, 그 전문가들의 셀 `mechs_json` 에 그 메커니즘 코드가 있다(P-03 — 카드 태그가 아니라 셀의 신고와 참조로 정의한다) | 그 OK 를 낸 전문가 |

- **등급.** `P1` = 검증된 주장값(`verified_fail_experts ≥ 1`) 또는 등록부 값이 FAIL 이거나 치명. `P2` = 검증 안 된 주장 FAIL·치명, 또는 `sev3 = 2`. `P3` = 그 밖.
- **우선순위.** `priority = max(sev3, claimed.sev3) × w_det × w_grade × max(TYPE_WEIGHT) × (1 + 0.1 · min(반대자 수, 3))`, `TYPE_WEIGHT = {held_fail: 1.4, split_verdict: 1.3, solo_severe: 1.0}`. 순서 = `(p_class, −priority, anchor_cluster_key)` — 입력 순서와 무관하다.
- **상한(D-34 를 이렇게 읽는다).** 타깃당 돌리는 쟁점 패널은 P1 을 먼저 `HWAXRISK_ISSUE_PANEL_HARD_CAP`(48)까지, 그 뒤 P2·P3 을 합계가 `HWAXRISK_ISSUE_PANEL_CAP`(24)에 닿을 때까지 채운다. 곧 `n_run = min(P1, 48) + max(0, 24 − min(P1, 48))` 로 막힌다(P1 이 24건을 넘으면 P2·P3 은 한 건도 안 돈다). 상한은 그 타깃이 지금까지 돌린 쟁점 패널 수 전부로 센다(다시 고른 회차도 같은 상한을 쓴다). 상한 밖은 `untried_cap`(`state_reason='cap'`) — 지우지 않고 보고서 '미토의 쟁점' 에 **행으로** 싣는다. `held_fail` 이 상한 밖이면 '전문가 N명이 FAIL 로 봤으나 미토의' 문장이 행마다 붙는다(P-02 ③).
- **다시 고를 때(`selected_round + 1`).** 같은 닻이면 같은 행이다(`issue_id` 결정론). `queued`·`untried_cap` 은 근거·우선순위를 새로 쓴다. `planned`·`running` 은 건드리지 않는다. `resolved`·`inconclusive` 는 `basis_hash`(제기자·반대자·주장값)가 바뀌었을 때만 `queued` 로 되돌린다(P-01 ⓐ — 적은 인원의 판정이 많은 인원의 판정을 영구히 덮지 않게). 후보에서 빠진 `queued` 는 `withdrawn`. 사람의 `skip` 은 `skipped`(사유 필수, 잔여에 든다).
- **결과 어휘(`resolve_issue`).** 그 패널 원자 가운데 닻 키(또는 3.7 의 닻 맞춤으로 닻에 붙은 것)를 가진 원자로 정한다. 하나도 없으면 `inconclusive`·`undetermined`(`no_matching_atom`). 전부 `rejected_in_panel` 이면 `resolved`·`rejected`. 닻 키에 개선 원자만 있으면 `resolved`·`rejected`(P-17-4). 살아 있는 원자가 여럿이면 `sev3` 가 가장 큰 것. 그 값이 주장값 최댓값(없으면 등록부 값)보다 낮으면 `downgraded`, 같으면 `upheld`, 높으면 `escalated`. 판정이 `undetermined` 면 `inconclusive`. 결정문을 파싱하지 못했으면 `inconclusive`(`spec_parse_failed`). `rr_issues.panel_id` 가 그 패널이 아니면 결과를 패널 행에만 남기고 쟁점은 건드리지 않는다(P-17-5 — 늦게 끝난 옛 워커와 재제출).

### 3.7 잡 사슬

```
reviews(검토 잡 — 어느 범위든) ──completed──▶ chain.on_reviews_closed
   ├─ 마감 범위에 열린 셀(pending·running)이 남았다 ─▶ 병합 → closure.refresh → 코드 조립 보고서 판(trigger reviews_partial). 끝
   └─ 마감 범위가 전부 닫혔다 ─▶ 병합 → closure.refresh → 코드 조립 보고서 판(trigger reviews_closed)
                                   → issues.select_issues → 돌릴 쟁점이 있으면 issues 잡, 없으면 synth 잡
issues(쟁점 패널을 한 줄로) ──completed·failed──▶ chain.on_issues_closed ─▶ 병합 → closure.refresh → 보고서 판(issues_closed) → synth 잡
synth(영역 요약 15 + 종합 1) ──completed──▶ chain.on_synth_closed ─▶ 보고서 판(synth_done) → closure.refresh
```

- **마감 범위.** `cells` 대상의 마감 레벨 기본은 `C3`(전원 — D-34)이다. 대상을 `cells` 로 열거나 바꿀 때 `rr_targets.close_level` 이 비어 있으면 `C3` 를 적는다(패널 대상의 기본 `HWAXRISK_DEFAULT_CLOSE_LEVEL=C2` 는 그대로). 마감 범위 = `C3` 면 격자 전부(로스터 × 검토 대상 단위), `C2` 면 Tier B 범위의 셀이다. '열린 셀' 은 `pending`·`running` 만이다 — `failed`·`skipped`·`na_irrelevant`·`no_input` 은 닫힌 것이다(C-18 '잡은 끝나고 완결이 막힌다').
- **좁은 범위의 검토 잡**(파일럿 9명, Tier A 만, 한 영역만)이 끝나면 쟁점·종합을 잇지 않는다(P-01). 병합과 코드 조립 보고서만 낸다 — 보고서 머리에 '마감 범위 미완 — 열린 셀 N' 이 서고 완결 표기도 그렇다.
- **사슬이 만드는 잡**은 `rr_jobs.mode ∈ {issues, synth}`, `tier` NULL, `chain_json = {root_job_id, prev_job_id, stage, round, cells_hash, registry_hash, scope_open: 0, reason}`, `params_json` 의 `requester`·`user_memo`·`consent`(사슬 생성은 `consent_source='chain'`)를 앞 잡에서 복사한다(P-09). **자격 검사로 행을 만들지 않는 일이 없다** — 자격이 없으면 행을 `queued` 로 만들고 `error='pat_unavailable: …'` 를 적는다. 집는 쪽이 지금처럼 자격 없는 잡을 건너뛰며 사유를 남긴다.
- **원자성.** 다음 잡 생성은 앞 잡의 상태 전이와 다른 트랜잭션이다(네트워크를 걸치지 않지만 `ReviewLoop._finish` 의 UPDATE 와 섞지 않는다). 그 사이에 재기동하면 `chain.sweep(store)` 가 메운다 — `RiskRunner` 의 틱(30초)이 `cells` 대상마다 '마지막 단계가 끝났는데 다음 단계 잡이 없다' 를 찾아 하나만 만든다(`chain_json.prev_job_id` 로 멱등). X1-07 ① 의 '사슬이 끊긴 채 공허하게 참' 을 막는다.
- **실패와 취소.** `issues` 잡이 `failed`(연속 3패널 오류)로 닫혀도 남은 `queued` 쟁점을 `untried_cap`(`engine_fail`)으로 옮기고 `synth` 를 잇는다(P-08 ②). 사람이 취소한 잡 뒤에는 잇지 않는다(남은 `queued` 는 `untried_cap`·`chain_cancelled`). 종합이 서술을 못 붙여도 코드 조립 판이 이미 있다(P-08 ①).
- **수동 시작.** 공개 REST 의 `mode` 는 `panels`·`reviews` 그대로다. 사람은 `PUT /issues/{id} {action:'queue'}`(쟁점 잡을 만들거나 기존 잡에 붙인다)와 `POST /targets/{key}/report {refresh_summaries:true}`(종합 잡)로 단계를 다시 부른다.
- **누가 집나.** `issues` 는 패널 러너(`runner.claim_next_job`)다 — `PANEL_JOBS_SQL` 을 `COALESCE(mode,'panels') IN ('panels','issues')` 로 넓히고 `pause_job`·`resume_job`·`cancel_job` 의 `mode != 'panels'` 갈래가 `issues` 를 패널 잡으로 다루게 고친다. `synth` 는 새 `synth.SynthWorker` 다(`RiskRunner._synth_tick` — 한 번에 잡 하나, 요약 호출은 차례로). 엔진 관문(동시 8 · 심의가 돌면 4 — `m3-engine-ops`)을 같이 쓰므로 따로 동시 수를 두지 않는다.
- **비우기.** update-all 의 비우기 신호(`m3-engine-ops`)가 선 동안 `claim_next_job` 은 새 쟁점 패널을 집지 않고 `SynthWorker` 는 새 요약 호출을 내지 않는다(기다림 부류 `draining` — M2.md 4.4).

### 3.8 완결 판정 — 잔여 · 조건 · 표기 · 확인

`registry.close_level` 은 문지기로 남는다 — `flow='cells'` 면 새 `closure.close_level_cells`, 아니면 지금 본문 그대로다(이름만 `_close_level_panels`). 반환 dict 는 지금 키를 전부 두고 `flow`·`level_label`·`qualifiers`·`counts`·`level_current`·`regressed` 를 더한다. 레벨 어휘(`C0 · C1 · C2 · C2(closed) · C3`)는 넓히지 않는다.

**잔여(qualifier).** 모든 레벨에서 그 레벨이 본 범위의 잔여를 붙인다(X1-02). '막음' 은 확인(ack) 전에 저장 레벨이 `C2(closed)`·`C3` 로 오르지 않는다는 뜻이고, '표기' 는 늘 붙되 막지 않는다는 뜻이다.

| item | 세는 것 | 표기 예 | 막음 |
|---|---|---|---|
| `input_gap` | `no_input` 셀과 그 전문가 수·영역(영역 전원이 입력 결손이면 영역 이름까지 — 면제가 아니라 잔여, X1-02 (2)) | 입력 결손 110명·880셀(soc·pcb·rf·passive·pwr·mem) | 막음 |
| `failed` | `failed` 셀(사유별 수) | 실패 3셀 | 막음 |
| `skipped` | 사람이 넘긴 셀(`failed → skipped`) + (영역 × 단위)마다 넘김이 그 칸의 절반을 넘은 곳 | 사람 넘김 12셀 | 막음 |
| `issues_untried` | 쟁점 `untried_cap`·`inconclusive`·`skipped`, 그 가운데 P1 과 `held_fail` 따로 | 미토의 쟁점 3건(주장 FAIL 1) | 막음 |
| `filtered` | 거른 셀(`na_irrelevant`)과 표본 재검토 결과(`closure_cells().filtered` — 3.13) | 거름 4,210셀(표본 212 · 놓친 걸림 0 · 95% 상한 1.4%) | 표기. 표본 하한을 못 채웠거나(`floor_met` 거짓) 놓침 상한이 5% 를 넘거나 거르기가 꺼졌다 켜졌으면 막음(`m3-cells` 의 `filter_audit` 조건) |
| `unit_excluded` | 제외 단위의 항목 가운데 사유가 `capture_partial`·`partial_scope`·`source_drift` 인 것(X1-10 — `not_design_relevant`·`null_both` 는 수만 싣는다) | 부분 캡처 — 제외 412건 | 막음 |
| `quality` | `review_quality.compute` 의 기준 밖 항목 + 셀 기준 strong 비율 0.7 미달(X1-05) | 검토 품질 기준 밖 2항 | 막음 |
| `cross_not_run` | M3 에서는 늘 있다. 넘김 줄 수와 (영역 → 영역) 쌍 수를 함께 | 2차 영향 미실행(넘김 41건 표만) | 표기 |
| `mech_not_run` | M3 에서는 늘 있다. 셀의 메커니즘 신고 표를 함께 | 결손 사냥 미실행 | 표기 |

확인으로 넘길 수 **없는** 것(일이 덜 끝난 것 — X1-07·WP4 3.9.4 규칙 4) — 미배정 변경 항목, 격자 결손(셀 수 ≠ 로스터 × 검토 대상 단위), `pending`·`running` 셀, `reviewed` 셀의 카드 판정 누락, 전문가 보고서 누락, 쟁점 `queued`·`planned`·`running`, 그리고 **후속 낡음**(`chain_stale` — 쟁점 선정이나 마지막 보고서 판의 `cells_hash` 가 지금 셀 지문과 다르다). 이것들은 레벨 조건에서 거짓으로 걸리고 표기에 '후속 낡음(재검토 N셀)' · '열린 셀 N' 처럼 붙는다.

**조건(셀 기반 — WP4 3.9.3 를 고친 것).**
- **C1 대표 완료.** 검토 대상 단위 ≥ 1, 미배정 0, 격자 완전. 요구 영역(`risk_roster_domains`) 전부에 대해 영역 1순위 대표(D-33 ① — 거르지 않는다)의 셀이 전부 닫혔다(`reviewed`·`no_input`·`failed`). 단위 0 이면 `C0(심사할 단위 없음)`.
- **C2 심층 완료.** C1 + Tier B 범위 셀이 전부 닫혔다 + 영역별 깊이 + 쟁점 단계가 지금 셀 지문으로 돌았고(신선) P1 쟁점에 `queued`·`planned`·`running` 이 없다. **깊이는 실제로 검토한 전문가만 센다(X1-02 · X1-04).** `active` = 그 영역에서 거르지 않은 셀이 하나라도 있고 입력 결손이 아닌 전문가, `have` = 그 가운데 `basis='cards'` 인 `reviewed` 셀이 1개 이상이고 셀이 전부 닫힌 전문가, `need = active if active < 3 else max(3, ceil(0.3·active))`. `active = 0` 인 영역(전원 입력 결손 또는 대표 말고 전부 거름)은 조건을 면하되 잔여(`input_gap` · `filtered`)에 영역 이름이 선다. 파싱 실패는 패널이 아니라 쟁점으로 센다(P-12 — P1 쟁점 가운데 `inconclusive(spec_parse_failed)`).
- **C3 전원 완료.** C2 + 격자 전부 닫힘 + 넘긴 셀이 '거르지 않고 입력 결손도 아닌 셀' 의 5% 이하(X1-01 — 분모를 고쳤다, 넘으면 잔여) + 쟁점 `queued`·`planned`·`running` 0 + 마지막 보고서 판이 신선(종합까지 지금 지문으로 돌았다) + **막음 잔여가 0 이거나 전부 유효하게 확인됐다.**
- 저장 레벨은 지금처럼 내려가지 않는다. 지금 계산이 낮으면 `level_current` 와 `regressed: true` 를 돌려주고 표기에 '재개방 N셀'(새 단위면 '신규 N셀')을 붙인다(X1-24). `rr_targets.level_label` 은 늘 지금 계산의 표기다 — 목록·필터가 맨 `C3` 를 보지 않게.

**표기(`level_label`).** `"<레벨>" + ("(" + 잔여 표기를 ' · ' 로 + ")" if 잔여 else "")`. 막음 잔여가 남아 오르지 못했으면 `"C2 · C3 대기(…)"`, 마감 레벨이 C2 인 대상은 `"C2 · 마감 대기(…)"`(P-13 ③). **M3 의 `cells` 대상에는 `cross_not_run`·`mech_not_run` 이 늘 있으므로 맨 `C3` 는 나오지 않는다** — 확인을 다 받은 대상의 최선은 `C3(2차 영향 미실행 · 결손 사냥 미실행)` 이다. 보고서 제목 · 진행판 · MCP 응답이 모두 이 문자열을 쓴다.

**확인(`closure.ack_residual` · `revoke_ack`).** 막음 잔여 한 종류씩이다. 사유 필수(300자 안, 비면 422), 확인 시점의 잔여 행 집합 해시(`basis_hash`)를 함께 받고 지금 값과 다르면 409 `residual_changed`. 확인 뒤 집합이 바뀌면(실패가 하나 늘거나 결손이 풀렸다) 그 확인은 낡아 다시 받는다. 취소는 행을 지우지 않고 표기한다. 행위마다 `rr_audit(scope='target', action='close.ack' | 'close.ack.revoke')` 한 행. 누가 하나 — 과제 소유자와 관리자(context-notes '권고값' — 편집자는 403). 확인이 오면 `closure.refresh` 와 보고서 판(trigger `ack`)을 만든다.

**캐시(`closure.refresh`).** 계산은 병합·쟁점 해결·셀 처분·확인·보고서 조립 뒤에 한 번 하고 `rr_targets.closure_json`·`level_label`·`closure_at` 에 둔다. 진행판(`coverage_payload`)과 MCP 는 캐시를 읽는다(P-17-13 — `_contested_marking_done` 이 finding 수천 건의 JSON 을 푼다). `GET /targets/{key}/closure?fresh=1` 만 그 자리에서 다시 센다.

**응답 모양(`GET /targets/{key}/closure`).**

```json
{"target_key": "…", "flow": "cells", "level": "C2", "previous_level": "C1", "raised": true, "close_level": "C3",
 "level_current": "C2", "regressed": false,
 "level_label": "C2 · C3 대기(입력 결손 110명·880셀 · 거름 4,210셀(표본 212 · 놓친 걸림 0 · 95% 상한 1.4%) · 미토의 쟁점 3건(주장 FAIL 1) · 2차 영향 미실행(넘김 41건 표만) · 결손 사냥 미실행)",
 "c1": true, "c2": true, "c3": false,
 "qualifiers": [{"item": "input_gap", "n": 880, "experts": 110, "domains": ["soc", "pcb"], "blocking": true, "acked": false, "basis_hash": "5f0c9e11ab02"}],
 "counts": {"roster": 359, "units": {"reviewable": 20, "excluded_by_reason": {}, "unassigned": 0},
   "cells": {"expected": 7180, "actual": 7180, "by_state": {}, "reviewed_by_basis": {"cards": 0, "background": 0, "role_only": 0, "noinput": 0}},
   "experts": {"active_by_domain": {}, "reviewed_cards": 0, "input_gap": 110, "filtered_only": 0, "reports": {"expected": 359, "ready": 0, "partial": 0, "blocked": 0, "missing": 0}},
   "cards": {"폭포": "review_quality 의 카드 칸 그대로"},
   "filter": {"population": 0, "sampled": 0, "risk_miss": 0, "relevance_miss": 0, "undetermined": 0, "upper95": null, "widened_cells": 0},
   "issues": {"by_state": {}, "by_outcome": {}, "p1": {"selected": 0, "run": 0, "untried": 0}, "held_fail": {"selected": 0, "untried": 0}, "cap": {"base": 24, "hard": 48}},
   "registry": {"clusters": 0, "attention": {"A": 0, "B": 0, "C": 0, "D": 0}, "single_heuristic_ratio": null, "card_fail_claimed": 0},
   "handoffs": {"lines": 41, "pairs": 17}, "mechanisms_reported": {"codes": 0, "free": 0},
   "chain": {"issues": {"job_id": null, "fresh": false}, "report": {"version_no": null, "fresh": false}},
   "quality": {"out_of_bounds": []}},
 "detail": {"depth": {}, "strong_ratio_cells": null, "skipped_ratio": null}}
```

### 3.9 요약 호출 — `m3-engine-ops` 에서 받는 것

엔진의 `summary` 종류는 `m3-engine-ops.md` 의 계약 3 과 E3-6 이 정한다. 이 꾸러미는 그것을 그대로 받고, 앱이 해야 할 것만 적는다.

- **받는 모양.** `limits.kinds` 에 `summary`, `limits.summary{p, …, line_max 400, narrative_max, cover_max, cover_hard_max}`, `runnable.summary`, `prompt_rev.summary = "cr-summary-1"`. 요청 `{kind:'summary', variant:null, target_key, expert:null, summary{scope{kind, key, label}, rows[{ref:'reg:<cluster_key>', text}], must_cover['reg:…'], blocks[{name, title, text}]}, expect}` — 엔진이 `R001…` 별칭을 매기고 결과 줄에 되돌린 `refs` 를 싣는다. 출력은 JSON Lines(`head` 한 줄 · `risk` · `conflict` · `gain` · `watch` · `ask` · `para` 한 줄 이상 · `inj`)이고 앱이 객체(`headline`·`key_risks[]`·`conflicts[]`·`gains[]`·`watch[]`·`info_requests[]`·`narrative`)로 옮긴다. 엔진 검사 — 모르는 별칭은 지우고 `checks.refs`, 수치가 행·블록에 없으면 `checks.nums_unsourced`(표지만), `must_cover` 가운데 `risk`·`conflict` 어디에도 없는 것이 `missing` 이고 그것만 보충한다. 조립이 `p_hard` 를 넘으면 422 `over_budget`(LLM 0회, 다시 쪼개지 않는다), `must_cover` 가 `cover_hard_max` 를 넘으면 422 `cover_too_large`.
- **앱이 하는 것.**
  - `rows` — 그 범위의 등록부 행 **전부**(영역 요약은 `merged.domains` 에 그 영역이 있는 행, 종합은 주의 A 전부와 B 상위). 한 줄은 3.10 의 꼴(400자 안 — `line_max`)이다. 행을 버리지 않는다(D-21).
  - `must_cover` — 그 범위의 주의 A 행을 우선순위 순으로 `limits.summary.cover_max` 까지. 넘는 A 행은 서술 대상이 아니라 코드 표에만 있고, 보고서 그 쪽에 '서술은 A 상위 N건 — 나머지 M건은 표' 를 적는다(조용히 빼지 않는다 — 그쪽 계약 그대로).
  - `blocks` — `numbers`(그 범위의 완결 수 — `closure.cell_counts` 에서), `issues`(영역 안 쟁점 결과 표), `asks`(보류 행의 `need` 상위), 종합 호출이면 `domains`(영역 요약의 `head`·`risk` — 앞 단계 LLM 글이라 엔진이 «» 안에 그린다).
  - **대조(`synth.check_summary`)** — 엔진의 `missing` 이 남았거나(보충을 다 써도) `checks.nums_unsourced` 가 선 줄이 있으면 지적을 실어 한 번 다시 묻고, 그래도면 그 범위를 `code_only(checks_failed)` 로 닫는다. 앱은 되돌린 `refs` 가 입력 `reg` 안인지를 한 번 더 본다(두 리포의 정규화가 갈리면 크게 보이게).
  - **`runnable.summary = false`**(그 박스에서 요약만 못 돈다)이거나 `over_budget` 이면 LLM 을 부르지 않고 `code_only(ctx_too_small)` 이며 보고서 머리에 크게 적는다.
  - 요청 본문은 셀 일과 같은 포털 중계 넷을 지나고(새 경로 없음), 관문(동시 8 · 심의가 돌면 4)을 같이 쓴다. 호출 원장은 `rr_review_calls`(kind `summary`)다.
  - 계약 예제(`req_summary_domain.json` · `result_summary_ok.json` · `result_summary_repaired.json` · `result_summary_missing.json` · `error_over_budget_summary.json`)를 앱 시험이 형제 경로로 읽는다(못 읽으면 skip 이 아니라 실패 — P-22).

### 3.10 종합 보고서 — 판과 쪽

- `synth.assemble_report(store, target_key, *, trigger) -> {report_uid, version_no, pages_n, level_label, counts, narrative_state}`. 등록부·쟁점·셀·완결 수·요약 행에서 코드가 조립한다. **보고서의 모든 수는 같은 호출 안에서 부른 `closure.cell_counts` 한 벌에서 나온다** — 그 값이 `rr_reports.counts_json` 이고 머리의 표다(나갈 기준 4). `content_hash` 가 직전 판과 같으면 새 판을 만들지 않는다. 조립은 어떤 단계의 트랜잭션 밖에서 try/except 로 감싼다(조립이 터져도 사슬·패널 완료를 무르지 않는다 — P-16).
- 쪽 모양은 전문가 보고서와 같다 — `{page_no, kind, title, blocks{background[], results[], recommendation[], minutes[]}}`(M2 S10 · PLAN 4절 REST). 마크다운 렌더와 25,000자 쪽 나누기는 `expert_report.render_pages` 의 방식을 그대로 쓴다.

| 쪽 | 블록 | 내용 | 누가 |
|---|---|---|---|
| 1 본문 | background | 대상·과제·소스·게이트·비교가능성(`registry.build_report` 의 조각) · **완결 표기와 잔여 표** · 커버리지 수치 표(3.8 의 counts) · 모델·자격 혼합 · 판 번호와 '마감 범위 미완 — 열린 셀 N'(좁은 범위 판) | 코드 |
| | results | (0) 종합 서술 — '서술은 LLM, 근거는 아래 표' 머리말(없으면 '서술 없음 — 까닭') (a) 주의 A 전부 (b) B 상위 30 (c) 개선 상위 (d) 넘김 표(2차 영향 미실행의 대신 — 영역 → 영역 · 건수 · 단위) (e) 쟁점 결과 표 — 행마다 **원래 분포와 패널 결과를 한 줄에**('제기 12명(FAIL 9 · WARNING 3) · 반대 2명 → 쟁점 패널 하향 중대/WARNING') | (0)만 LLM |
| | recommendation | 판정 후보와 사유 · 확정 판정 · 조건 · 닫는 확인 · 열린 물음 · 정보 요청(보류 행의 `need` 를 접어 건수 순 — X1-15 (3)) · **미토의 쟁점(행으로)** · '카드 대조가 FAIL 로 본 것 n건 · 그 가운데 치명 k건(등록부에는 hold 로 주의)'(X1-18 (2), `rr_card_verdicts` 에서 직접 센다) | 코드 |
| | minutes | 쟁점 패널 목록 · 영역 × 셀 상태 표(검토를 basis 별로 — X1-04) · 거름 표본 결과 · 품질 블록(`review_quality.block` — 이 판의 고정본, WP5b 3.11.1) · 사람 개입(확인·넘김) | 코드 |
| 2~16 영역 | results | 영역마다 한 쪽 — 영역 수치, 요약 서술(또는 '서술 없음 — 까닭'), 그 영역의 A·B 행, C·D 건수, 영역 안 쟁점 | 서술만 LLM |
| 메커니즘 | results | 단위 × 메커니즘 대분류 표(제기 · 신고) · 택소노미 밖 메커니즘 표(`mech_free` 집계) — 머리에 '결손 사냥 미실행' | 코드 |
| 부록 | minutes | 전문가 색인 359줄 — 키 · 영역 · 셀(검토/거름/입력 결손/실패/넘김) · 카드 판정 수/기대 수 · 걸림 수 · 카드 밖 · 인용 통과율 · 보고서 판(`risk_get_expert_report` 로 읽는다) | 코드 |

- 영역 요약은 **로스터 영역 15개 전부**에 한 건씩 선다. 행이 0 인 영역은 LLM 을 부르지 않고 `code_only(no_rows)` 로 서고(나갈 기준 4 의 '15건' 에 든다), 보고서 그 쪽에 '이 영역이 제기한 클러스터 없음 — 검토 N셀 · 거름 M셀' 을 싣는다.
- 영역 요약의 입력은 전문가 보고서가 아니라 **그 영역이 제기에 참여한 등록부 행 전부**다(`merged.domains` 에 그 영역). 한 행은 `{ref:'reg:e6f6e60b99cc', text:'severity=중대 · judgement=WARNING(주장 FAIL) · mechanical.drop_stress · dimension · «REAR_COVER» · 제기 7명/3영역/2단위(검증 4) · 쟁점 upheld · «주장 글»'}` 꼴이다(판단어 린터가 허용하는 꼴 — P-17-12, 400자 안 — `line_max`). 별칭은 엔진이 매긴다. 행을 버리지 않는다 — xd 의 행이 수백이어도 1M 창에 든다(D-21). 넘치면 `ctx_too_small` 로 `code_only` 이고 보고서 그 쪽 머리에 크게 적는다.
- 종합 호출의 입력은 영역 요약 15건의 `head`·`risk`(영역당 전부), 주의 A 전부와 B 상위, 쟁점 결과 표, 넘김 표, 커버리지 수치다.
- 보고서 제목은 `리스크 심사 보고서 v{n} [{level_label}] — {target_key}` 이고, 근거 등급이 전부 경험칙이면 지금처럼 `[가설 단계]` 를 앞에 붙인다.

### 3.11 REST · MCP

기존 키는 하나도 지우지 않는다. 더하기만 한다. 읽기는 지금 관례(`_target_row(target_key, owner_sub)`), 쓰기는 `require_role(… 'editor')` + `rr_audit` 이고 확인(ack)만 소유자·관리자다.

| 경로 | 무엇 |
|---|---|
| `GET /targets/{key}/coverage` | + `level_label` · `qualifiers[]`(캐시) · `stage{mode, job_id, state, hold_code}`(지금 도는 사슬 단계) · `report{version_no, narrative_state, created_at}` |
| `GET /targets/{key}/closure?fresh=0\|1` (새) | 3.8 의 응답 전체 + 확인 목록(유효·낡음·취소) |
| `POST /targets/{key}/closure/acks/{item}` · `DELETE …` (새) | 본문 `{reason, basis_hash}`. 소유자·관리자만(편집자 403). 409 `residual_changed` · 422 `ack_not_allowed`(막음 잔여가 아니거나 확인으로 못 넘기는 것) |
| `GET /targets/{key}/issues?state&p_class&type&limit(100, 최대 500)&offset` (새) | `{target_key, total, limit, offset, next_offset?, cap{base, hard, run}, rows[{issue_id, rank, types, p_class, priority, anchor_cluster_key, unit_id, state, state_reason, outcome, outcome_json, distribution{raisers, by_judgement_claimed, by_severity, opposers}, panel_id, seats[{key, domain, issue_role}], selected_round}]}` |
| `PUT /issues/{issue_id}` (새) | `{action: 'queue' \| 'skip', reason}` — `untried_cap` 을 올리거나(상한을 넘기는 사람의 결정, 사유 필수) 건너뛴다(`skipped`, 잔여에 든다). `rr_audit(scope='target', action='issue.queue' \| 'issue.skip')` |
| `GET /targets/{key}/report?version&page&part=summary\|domains\|mechanisms\|appendix\|full&format=json\|md` (새) | `{target_key, version, report_uid, level_label, narrative_state, counts, pages_total, page_no, next_page?, page{…}}` 또는 `format=json` 이면 쪽 전체. `version` 이 지금 판과 다르면 409 `report_version_moved`(쪽을 받는 사이 새 판이 섞이지 않게) |
| `POST /targets/{key}/report` (새) | `{refresh_summaries: false}` 면 코드 조립 판을 그 자리에서, `true` 면 종합 잡을 만든다(editor) |
| `GET /targets/{key}/registry` | + 쿼리 `attention` · `unit_id` · `source=panels`(3.5 — 패널만 본 비교 보기, 저장 없음) · `offset`. 행에 `support_experts·support_domains·support_units·support_verified·attention·issue_id·issue_state` 와 `merged.claimed·distribution·before_issue` |
| `GET /targets/{key}/panels` · `GET /panels/{id}/transcript` | 패널마다 + `kind` · `issue_id`, 쿼리 `kind` |
| `POST /panels/{id}/complete` | 쟁점 패널도 받는다(고쳐서 다시 내기 — 러너와 같은 갈래를 탄다) |

(10-15 덧붙임 — 반대 검토 뒤 더한 칸, 지운 칸 없음.) 쟁점 행(REST·MCP)과 요약 입력에 `reargue`(패널이 판정한 쟁점의 근거가 바뀌어 다시 토의가 필요함 — 새 패널이 정할 때까지 옛 판정을 보이고, 새 패널이 결정을 못 내면 '…(새 패널 결정 못 함)'). 새 잔여 `issues_reraised`. 확인·확인 취소 응답에 `report_version`. 쪽 나누기 목록에 `ledger_rev`(바뀌면 offset 0 부터). 등록부 MCP 행은 `merged_json` 없이 목록을 줄이고 `merged.lists_total`. 남에게는 모든 쓰기·읽기 경로가 없는 것과 같은 404(가드 `tests/rr/test_review1_stranger.py` — 쓰기 51 · 읽기 41 · MCP 31). 결정은 context-notes D-44~D-52.

MCP 는 **29 → 31종**이다(PLAN 4절 C-30). 새 도구 둘은 읽기 전용이다(`test_no_write_tools` 의 뜻 그대로).

- `risk_get_issues(target_key, state=None, p_class=None, limit=100, offset=0)` — REST 와 같은 함수(`routes.issues_payload`)를 `_fit_rows` 로 감싼다. 와이어(들여쓰기 2 JSON)가 25,000자 안에 들 때까지 `limit` 를 줄이고 남으면 `next_offset` 을 준다(자르지 않는다). 설명문에 '쟁점은 웹 러너가 돌린다 — Claude 에서는 지켜본다' 를 적는다.
- `risk_get_report(target_key, part='summary', version=None, page=1)` — `routes.report_source`·`report_render`·`report_envelope` 를 쓰고 쪽 크기는 `_report_page_chars` 와 같은 식(그 판의 쪽 전부가 와이어 25,000자 안에 들 때까지 줄인다, 조각 하나가 넘는 쪽은 자르지 않는다)이다. 둘째 쪽부터 `version` 대조.
- `risk_get_coverage`·`risk_get_registry` 는 같은 함수라 새 칸이 저절로 붙는다. `risk_get_registry` 에 인자 `attention`·`unit_id` 를 더한다(새 도구가 아니다). 기본 응답 크기는 지금처럼 `REGISTRY_LIMIT`·`next_offset` 이다 — 행에 `merged` 가 커지므로 `_fit_rows` 로 감싼다.
- `risk_submit_panel_result` 는 쟁점 패널이면 `{error:'issue_panel_web_only'}` 다(옛 흐름 패널은 그대로).
- `risk_next_step` — 검토 잡이 끝난 뒤의 단계를 말한다. 쟁점 잡이 돌면 지켜볼 도구로 `risk_get_issues`, 멈췄으면(재기동 — M4 전에는 자동 재개 없음) `risk_job_action(action='resume')`, 종합이 `code_only` 면 그 까닭, 막음 잔여가 남았으면 '웹 화면에서 소유자·관리자가 확인한다(사유 필수)' 와 `GET …/closure`. `facts` 에 `level_label` 을 싣는다.
- 확인(ack)·쟁점 올리기/건너뛰기는 MCP 쓰기 도구로 내지 않는다(7절 (a)-10). Claude 사용자는 웹 화면에서 한다.
- 게이트웨이에 실제로 뜨는지는 `tools/list` 로 본다(SIF 를 다시 지어야 반영된다 — CLAUDE.md).

### 3.12 손잡이 (전부 선택 — `$DATA_DIR/knobs.env`, `launch.env` 에 적지 않는다)

| 이름 | 기본 | 무엇 |
|---|---|---|
| `HWAXRISK_ISSUE_PANEL_CAP` | 24 | 타깃당 쟁점 패널(P2·P3 이 채울 수 있는 합) — D-34 |
| `HWAXRISK_ISSUE_PANEL_HARD_CAP` | 48 | P1 쟁점의 상한 — D-34 |
| `HWAXRISK_ISSUE_SPLIT_MIN_OPPOSERS` | 2 | `split_verdict` 의 최소 반대자 수 |
| `HWAXRISK_ISSUE_MAX_CHARGED` | 2 | 쟁점 하나의 내용 탓 실패 한도(넘으면 `inconclusive`) |
| `HWAXRISK_SUMMARY_MAX_CHARGED` · `HWAXRISK_SUMMARY_INFRA_MAX` | 2 · 6 | 요약 하나의 내용 탓 · 인프라 실패 한도(넘으면 `code_only` — P-08 ③) |

일일 패널 상한(`HWAXRISK_DAILY_PANEL_CAP` 24)은 쟁점 패널에도 그대로 걸린다(WP4 3.7.7). 수확 체감 정지는 쟁점 패널에 걸지 않는다(`_diminishing` 이 `kind='coverage'` 만 본다). 대신 최근 5개 쟁점 패널이 전부 `rejected`·`inconclusive` 면 `progress_json.advice='issue_yield_low'` 를 적는다(멈춤은 사람이 정한다).

### 3.13 `m3-cells` 에서 받는 것

이름은 `m3-cells.md`(같은 날 쓴 형제 계획)의 것에 맞췄다 — 그쪽 3.9 롤업 표와 3.10 `closure_cells` 다. 이 꾸러미는 아래 함수만 부른다.

| 이름 | 모양 | 어디에 쓰나 |
|---|---|---|
| 셀 상태 `no_input` · `na_irrelevant`(밖으로는 '거름') 와 전이 | `review_cells.CELL_STATES` 그대로, 그쪽 3.1 의 전이 다섯(`running → na_irrelevant` 분류 · `na_irrelevant → pending` 넓힘·늦은 넘김·보충 표본 …) | 완결 판정의 '닫힌 셀', 잔여 `input_gap`·`filtered` |
| 셀의 거름 표지 | `route='filtered'`(표본은 `route='audit'`), `basis='filtered'`, `route_json{rule, decision, routing_rev(change-routing · mech-owners · taxonomy 판)}` | 잔여 `filtered`, 보고서 거름 표 |
| `review_cells.closure_cells(store, target_key)` | `{grid, by_state, by_basis, failed{open, by_code}, skipped{n, experts, by_note}, filtered{n, would_filter, by_domain, audit{sampled, floor_met, risk_miss, relevance_miss, undetermined, kept, upper95, upper95_conservative}, shadow, widened, off}, no_input{experts, cells, by_outcome}, undetermined{rows, cells}, out_of_scope_pending, invariants[]}` — GROUP BY 라 폴링에도 쓴다 | `closure.cell_counts` 의 셀 몫 전부, 잔여 `input_gap`·`failed`·`skipped`·`filtered`, 나갈 기준 1 의 판정(`pending + running == 0 and invariants == []`) |
| 전문가 원장 롤업 | 그쪽 3.9 표 — `reviewed` 0 이고 `no_input` ≥1 이면 `abstain(no_input:ecad_absent)`, 전부 거름이면 `abstain(filtered:<n>)`, 넘김뿐이면 `skipped(cells_skipped:<n>)`. 이 꾸러미는 그 사유 문자열로 깊이·strong 의 분모에서 뺀다(X1-02) | 깊이의 `active`, 의견 행 |
| 전원 포함 · `rr_roster.input_gaps_json` | 로스터 전원이 격자에 든다(ECAD 의존 영역 포함) | 격자 완전 |
| 실패 셀 처분 REST | `POST /targets/{key}/cells/retry` · `/skip`(묶음, 넘김은 사유 필수) — `failed → pending` · `failed → skipped` | 잔여 `failed`·`skipped`, 처분 뒤 `closure.refresh` |
| 메커니즘 → 영역 배정표 소비 | 3.2 의 읽는 함수, 승인 전 `unknown` | 거르기 코드 신호 |

## 4. 걸음

짓는 순서는 다섯 단계다. 단계 안의 걸음은 파일이 겹치지 않으면 나란히 간다.

| 단계 | 걸음 | 끝나면 |
|---|---|---|
| A 바탕 | S3-0 · S3-1 · S3-2 · S3-3 | v5 블록(합친 것)이 가지에서 초록, 택소노미 1.2 와 배정표 초안, 앱의 미분류 분리. 엔진 `cr-verdict-2`·`summary` 는 `m3-engine-ops` 가 같은 무렵 올린다 |
| B 병합·쟁점 | S3-4 → S3-6 → S3-7 | 가짜 엔진 원장에서 쟁점이 골라지고 쟁점 패널이 가짜 패널 엔진으로 돈다 |
| C 사슬·완결·종합 | S3-5 · S3-8 · S3-9 | 가짜 엔진으로 reviews → issues → synth 가 사람 손 없이 이어지고 보고서 판이 선다 |
| D 바깥 | S3-10 · S3-11 · S3-12 | 도구 31종, 안내문, 시험 |
| E 리허설 | S3-13 | v5 확정 → push → SIF → `tools/list` 31 → cae00 전원 실주행 지원 |

- **리스크 앱은 가지 `m3` 에서 짓는다.** v5 는 dev 리허설이 끝날 때까지 push 하지 않는다(PLAN 4절 C-2 · D-7). 날마다 main 을 받아 rebase 한다.
- **모든 걸음의 회귀 가드(D-24).** `tests/rr/test_legacy_flow.py` 전부, `tests/rr/test_panel_ledger.py` 의 패널 셋 연속 `done`, `tests/test_registry.py` 의 `test_close_level_*` 열세 건, 패널 대상의 `registry.merge`·`close_level` 바이트 동일 시험(S3-4 가 만든다)이 그대로 초록이다.
- **소비자 시험의 입력은 생산자 함수로 만든다(PLAN 9절).** 원장은 `devseed` → 캡처·diff → `units` → M2 검토 루프(`tests/synth/fake_review_engine.py`)로 돌려 만든다. 카드 판정 행·finding 을 손으로 INSERT 하지 않는다(씨앗 출처 래칫 `tests/rr/test_fixture_provenance.py` 가 본다). 쟁점 패널 결과는 지금의 가짜 패널 엔진이 `risk_spec` 을 내는 길로 만든다.
- 걸음마다 그 리포 시험 전체를 돌리고 논리 단위로 커밋한다. 각 단계 끝에 반대 검토 한 라운드를 돌린다(감사는 라운드로 돈다).

### S3-0 시작 걸음

- **목적.** 이 계획의 닻을 걸음 시작 시점에 다시 확인하고, 문제를 수용 기준으로 옮기고, 형제 계획과 이름을 맞춘다(PLAN 9절).
- **할 일.** ① 2절의 닻을 `grep` 으로 다시 찾는다(`card_review'` 20곳 · `MIGRATIONS` · `PANEL_JOBS_SQL` · `_solo_set` · `_hold` · `close_level` · `_finish` · `persist_panel_result` 의 회차 줄). ② WP4 P-01~P-17 과 X1-01~X1-27 가운데 이 꾸러미에 닿는 것을 아래 걸음의 수용 기준으로 옮겼는지 대조표로 남긴다(5절의 표). ③ `m3-cells` 와 3.13 의 이름, `m3-engine-ops` 와 3.9 의 계약을 맞춘다 — 갈리면 합친 계획(M3.md 가 서면 그 4절)이 정한다. ④ v5 블록의 주인은 이 꾸러미의 S3-1 이다 — `m3-cells` 가 그렇게 적었다(그쪽 3.13 — `rr_unit_live` 한 표를 덧붙인다). 통합 가지 `m3` 와 꾸러미별 하위 가지도 그쪽 a-15 와 같다. ⑤ HWAXRisk `context-notes.md` 에 'v5 는 재설계 M3 몫, 가지 `m3`' 를 먼저 적는다.
- **수용 기준.** 대조표에 빠진 문제 번호가 없다. 닻이 2절과 다르면 이 문서를 고친다.
- **의존.** 없다.
- **크기.** 3시간.

### S3-1 스키마 v5 — 이 꾸러미 몫 (WP4 1)

- **목적.** 3.1 의 DDL 을 `m3-cells` 의 몫과 한 블록·한 커밋으로 싣고 반출·이양·폐기를 배선한다.
- **파일 · 닻.** `risk_store.py` `MIGRATIONS` 에 `(5, _DDL_V5)`, `_DDL_V5_SQL` 머리 주석에 'dev 리허설 뒤 push — PUSHED_DDL_SHA256[5] 가 지킨다'. `tests/test_store.py` `PUSHED_DDL_SHA256` 에 5(로컬 커밋마다 고쳐도 되고 S3-13 에서 굳는다), 'v1 밖 표 집합' 과 `_columns` 단언. `export.py` `_SINCE_COLS` 넷 · 행 변환 셋(3.1). `routes.py` `TRANSFER_DERIVED` 넷 · `PURGE_BLANK_SQL` 다섯. `rr_jobs.mode` 의 v4 주석은 고칠 수 없으므로(굳은 블록) 새 어휘는 `runner.JOB_MODES` 상수와 v5 머리 주석에 적는다.
- **수용 기준.** P-11(WP4 표는 v5 로, PK 는 시험이 끝난 뒤 굳는다) · C-3(어휘 열에 CHECK 없음) · C-9(박스 지역 표 없음) · 사용자 결정 1(반출 200자 — 쟁점 근거·등록부 인용까지).
- **시험.** 새 `tests/rr/test_v5_upgrade.py`(M2 의 `test_v4_upgrade.py` 와 같은 꼴) — v4 원장(`tests/rr/v3_build.py` 의 v3 원장을 v4 로 올리고 M2 검토 루프로 셀·판정·보고서를 채운 것)을 v5 로 올려 행이 그대로다. 옛 v2 얼린 DB(`tests/fixtures/legacy/`)를 v5 로 올려 골든이 그대로다. 새 표 행은 S3-4~S3-9 의 생산자 함수로 넣고(그 걸음이 서면 이 시험을 다시 묶는다) 반출 → 빈 DB 들여오기 왕복에서 쟁점 패널의 `brief_gz` 가 비고, 등록부·쟁점의 카드 인용이 200자이며 원래 길이가 실린다. 이양은 새 표 넷의 `owner_sub` 를 옮기고, 폐기는 원문 칸을 비운다(`rr_reports.pages_gz` 는 빈 gzip).
- **의존.** S3-0, `m3-cells` 의 v5 문장.
- **크기.** 7시간.

### S3-2 택소노미 1.2 와 메커니즘 → 영역 배정표 (WP4 3)

- **목적.** 메커니즘 14종을 더하고(D-34) 배정표를 사용자가 훑을 수 있는 자산으로 낸다. 거르기(`m3-cells`)와 쟁점 패널(S3-7)이 같은 표를 읽는다.
- **파일 · 닻.** `assets/taxonomy.v1.json` — `taxonomy_version` 1.2, `axes.mechanism` 에 14행(`code·mechanism·detail·label·description·default_detectability·default_tools`(모르면 `[]`)`·version_added '1.2'·status 'active'·merged_into null`), `synonyms` 에 새 코드의 낱말(한·영). `schemas/risk_spec.v1.json` `definitions.finding.properties.mechanism.enum` 에 `optical`·`acoustic`·`rf`(대분류 — P-17-1). `narrative._normalize_mechanism` 의 대분류 집합 `{"thermal", …, "process"}` 를 `taxonomy.mechanism_majors()`(자산에서 읽는다)로 바꾼다. 새 `assets/mech-owners.v1.json`(3.2·3.4) · `taxonomy.VOCAB_ASSETS` 에 이름 · 읽는 함수 넷. `routes` `GET /meta/taxonomy` 와 `mcp_server.risk_taxonomy` 가 배정표와 `review_status` 를 함께 준다.
- **수용 기준.** D-34(14종 · 사용자가 표를 훑는다), WP4 2.2 ⑦(미분류 뭉침의 절반 — 나머지 절반은 S3-3), P-15(material 순서), P-17-1(enum 은 대분류).
- **시험.** 3.2 의 불변식 넷. 승인 문 — `review_status='draft'` 면 `taxonomy.domains_for` 의 결과에 `approved: false` 가 실리고(거르기가 그것을 `unknown` 으로 읽는 시험은 `m3-cells` 몫). **동의어 충돌 없음** — 지금 리포의 `risk_spec` 픽스처 전부(`tests/fixtures/risk_spec/*`)와 옛 타깃 골든의 finding 을 1.1·1.2 로 각각 정규화해, 1.1 에서 이미 코드로 풀리던 것은 1.2 에서도 같은 코드다(달라지는 것은 1.1 에서 `unclassified` 이던 것뿐이고 그 목록을 시험에 적는다). `engine_client.review_mechanisms()` 가 52개다. `test_legacy_flow.py`(얼린 키 — 삽입 시 동결이라 바뀌지 않는다) 그대로.
- **의존.** S3-0. 사용자 검토는 이 걸음을 막지 않는다(승인 문이 거르기만 막는다).
- **크기.** 6시간.

### S3-3 카드 대조 finding 의 메커니즘 — 앱 쪽 (M2 #25 — 3.3)

- **목적.** 카드 근거 finding 이 `process.unclassified` 한 클러스터로 뭉치지 않게 한다. 엔진이 걸린 줄에 `mech` 를 싣는 것은 `m3-engine-ops.md` E3-4 이고, 이 걸음은 그것을 받는 앱 쪽이다.
- **파일 · 닻.** `expert_report._mech_parts`(빈 값·`free` 의 `free_key` — 3.3), `narrative._normalize_finding` 이 `cluster_key_of` 를 부르는 자리(`SpecContext` 에 `flow` 칸을 더해 `cells` 일 때만 세부 자리를 `unclassified~<free_key>` 로), `registry.family_key_of` 를 부르는 자리(같은 규칙), `expert_report` 의 표지 `mech_out_of_domain`(배정표의 소유 ∪ 관련 밖 — `finding_json.flags` 와 전문가 보고서 품질 칸에 센다, 판정은 바꾸지 않는다), 걸렸는데 `mech` 가 빈 판정(`checks.mech='missing'`)의 수를 품질 칸에.
- **수용 기준.** M2 #25, WP4 2.2 ⑦ · 3.3.4 (다), P-17-6(family_key), D-24(패널 대상 키 불변), D-34(배정표는 검사에만).
- **시험.** 입력은 M2 루프를 가짜 검토 엔진(걸린 줄에 `mech` 를 싣게 대본을 고친 것 — 모양은 엔진 계약 예제 `result_verdict_mech.json` 그대로, 형제 경로로 읽는다)으로 돌려 만든 원장이다. finding 의 메커니즘이 실효 행의 코드와 같다. 두 전문가가 서로 다른 `mech_free` 를 내면 두 클러스터, 같은 코드를 내면 한 클러스터다. `mech` 도 `mech_free` 도 없으면 `card~<card_id>` 로 갈린다. 패널 대상의 새 패널 finding(가짜 패널 엔진)이 지금 식의 키를 받는다. 배정표 밖이면 표지가 서고 판정이 같다.
- **의존.** S3-2(배정표), `m3-engine-ops` E3-4(엔진이 먼저 올라가 있어야 실제 값이 온다 — 없으면 지금처럼 비고 `card~` 로 갈린다).
- **크기.** 4시간.

### S3-4 등록부 병합 — 카드 대조 finding 을 넣는다 (WP4 2 — 3.5)

- **목적.** `cells` 대상에서 M2 #7·#20 을 푼다. 지지 수를 전문가·영역·단위·검증으로 나눠 세고, hold 가 가린 주장값과 분포를 같은 행에 남기고, 쟁점 결과를 덮어쓰는 자리를 둔다. 패널 대상은 바이트로 그대로다.
- **파일 · 닻.** `registry.py` — 새 `finding_scope`, `_load_findings`·`_contested_marking_done` 이 그것을 부른다, `_merge_cluster(…, issue=None, flow='panels', roster_domain=None)`, 새 `_support_counts`·`_claimed`·`attention_of`, `_MERGE_OWNED_COLUMNS` 에 새 열 일곱, `_write_registry_row` 의 INSERT 열, `merge()` 가 흐름·로스터·해결된 쟁점을 읽어 넘긴다, `_recompute_contrib`(`cells` 대상은 비운다), `_is_stronger`·`set_status`(`support_domains_at_decision`). `routes._cluster_finding_ids`(`finding_scope`), `routes.registry_payload`(`attention`·`unit_id`·`source=panels`). `export.py` 등록부 인용 변환(S3-1 과 같은 함수). 나머지 열일곱 자리에 까닭 주석.
- **수용 기준.** M2 #7·#20 을 `cells` 대상에서만 푼다 · D-24(패널 대상 바이트 동일) · m-16(지지 수 부풀림 — 이제 전문가 수다) · P-02(주장값) · X1-18 (1)(검증된 주장값만 주의 등급을 올린다) · P-17-6(별칭 접기) · P-17-10(재제기 비교) · WP4 3.5.3(덮어쓰기와 원래 분포) · D-34.
- **시험.** ① **패널 대상 바이트 동일** — 옛 타깃 픽스처와 합성 40건 패널 셋(가짜 패널 엔진)의 등록부 행(옛 열·`merged_json`)·`close_level`·`verdict_candidate` 가 v5 코드 전후로 같다. 같은 대상에 M2 방식으로 검토를 얹어도(흐름 `panels` 그대로) 같다. ② M2 루프로 만든 `cells` 원장에서 12명이 같은 클러스터를 내면 `support_experts` 12, 영역 수가 로스터 영역 수와 같고, `support_verified` 는 인용이 대조를 지난 사람 수다. ③ hold 아래 FAIL 9명·WARNING 3명이면 행은 중대/WARNING 이고 `claimed.judgement='FAIL'`·`fail_experts=9`, 인용이 대조를 지났으면 주의 등급 A 다. ④ 쟁점 결과 다섯 갈래(가짜로 만든 `rr_issues` 행이 아니라 S3-7 이 서기 전에는 `issues.resolve_issue` 의 순수 판정 함수로 만든 결과)가 3.5 표대로 행을 고치고 `before_issue` 가 남는다. 사람이 닫은 행은 어느 경우에도 그대로다. ⑤ `cells` 대상 병합 뒤 `rr_delta_contrib` 에 그 대상 행이 없다. ⑥ `card_review'` 출현 자리 목록 시험(래칫). ⑦ 패널을 돌린 뒤 `cells` 로 바꾼 대상에서 `registry?source=panels` 의 행이 바꾸기 전 등록부와 같다.
- **의존.** S3-1 · S3-3(키 규칙).
- **크기.** 12시간.

### S3-5 잡 사슬 — 마감 범위가 끝났을 때만 잇는다 (WP4 7 — 3.7)

- **목적.** 검토 잡이 끝난 뒤 쟁점 → 종합이 사람 손 없이 이어지되, 적은 인원의 결과로 쟁점·종합을 닫지 않는다(P-01). 사슬이 끊겨 완결 조건이 공허하게 참이 되지 않는다(X1-07).
- **파일 · 닻.** 새 `app/chain.py`(첫 줄 한국어 주석) — `scope_open(store, target_key) -> int` · `cells_hash(store, target_key) -> str`(마감 범위 셀의 `(unit_id, agent_key, state, n_fail, n_warning, n_offcard, error_code)` 정렬 sha256[:16]) · `on_reviews_closed(store, job)` · `on_issues_closed(store, job)` · `on_synth_closed(store, job)` · `sweep(store) -> dict` · `create_stage_job(store, target_key, stage, *, prev)`. `review_runner.ReviewLoop._finish` — `completed` 로 바뀐 직후(`changed` 일 때, 같은 트랜잭션 밖)에 `chain.on_reviews_closed`. `runner._finish_job` — `mode == 'issues'` 갈래. `runner.claim_next_job`·`PANEL_JOBS_SQL`·`pause_job`·`resume_job`·`cancel_job` 의 `mode` 갈래. `runner.RiskRunner` — `_synth_tick`·`_chain_tick`(30초, `chain.sweep`). `routes.post_target_flow`·`POST /targets` — `cells` 로 열 때 `close_level` 이 비었으면 `C3`. `config.BOX_KNOBS` 는 건드리지 않는다(3.12 의 손잡이는 S3-6·S3-9 가 더한다).
- **계약.** 3.7 그대로.
- **수용 기준.** P-01(마감 범위) · P-06(사슬을 굴리는 손) · P-08 ①②(코드 조립 판을 먼저, 쟁점 잡이 실패해도 종합) · P-09(요청자·동의 승계, 자격 없음이 사슬을 끊지 않는다) · X1-07 ①③(끊긴 사슬 — `sweep` · 좁은 범위 뒤에는 잇지 않는다) · C-18(실패 셀이 잡을 세우지 않는다) · D-34(기본 마감 전원).
- **시험.** 가짜 검토 엔진 + 가짜 패널 엔진 + 가짜 요약 엔진(시험 디렉터리 한 벌씩 — D-15)으로 합성 대상 하나를 끝까지 돈다. ① `scope.agents` 3명 검토 잡이 끝나면 쟁점·종합 잡이 생기지 않고 코드 조립 판 v1(`reviews_partial`)이 서며 표기에 '열린 셀 N' 이 있다. ② 이어 전원 검토 잡이 끝나면 쟁점 잡 → 종합 잡이 차례로 생기고 판이 v2(`reviews_closed`) · v3(`issues_closed`) · v4(`synth_done`)로 오른다. ③ 검토 잡이 `completed` 로 바뀐 직후 다음 잡을 만들기 전에 프로세스를 죽였다 살리면 `sweep` 이 정확히 한 개를 만든다(두 번 돌려도 하나). ④ 자격 해석기가 사슬 중간부터 None 을 돌려줘도 다음 잡 행이 `queued` 로 생기고 `error` 가 적힌다. ⑤ 사람이 쟁점 잡을 취소하면 종합 잡이 생기지 않고 남은 쟁점은 `untried_cap(chain_cancelled)` 다. ⑥ 쟁점 패널 셋이 잇달아 엔진 오류면 쟁점 잡이 `failed` 이고 남은 쟁점이 `untried_cap(engine_fail)` 이며 종합 잡이 생긴다. ⑦ 패널 대상의 Tier B → C 자동 후속은 지금 그대로다.
- **의존.** S3-4(병합) · S3-8 의 `closure.refresh`(없으면 그 자리를 빈 함수로 두고 S3-8 이 채운다) · S3-9 의 `assemble_report`(같다).
- **크기.** 10시간.

### S3-6 쟁점 선정 (WP4 8 의 앞 절반 — 3.6)

- **목적.** 토의할 거리를 코드가 고른다. hold 가 가린 FAIL 을 놓치지 않는다. 상한 밖은 지우지 않고 '미토의' 로 남긴다.
- **파일 · 닻.** 새 `app/issues.py` — `select_issues(store, target_key, *, selected_round, settings=None) -> {candidates, queued, untried_cap, withdrawn, by_type, by_class}` · `issue_types(row, cells, verdicts) -> list[str]` · `p_class_of` · `issue_priority` · `allocate_cap(ordered, cap, hard_cap)` · `basis_of`. `config.BOX_KNOBS` 에 `HWAXRISK_ISSUE_PANEL_CAP`·`_HARD_CAP`·`HWAXRISK_ISSUE_SPLIT_MIN_OPPOSERS`·`HWAXRISK_ISSUE_MAX_CHARGED`. `registry.resolve_cluster_key`(닻 키).
- **수용 기준.** P-02 ①②③(`held_fail` · 주장값으로 등급 · 상한 밖도 행으로) · P-03(`split_verdict` 재정의) · P-01 ⓐ(제기자가 바뀐 해결 쟁점은 다시) · P-17-6(별칭) · X1-18 · D-34(24/48).
- **시험.** 입력은 M2 루프를 가짜 검토 엔진 대본(전문가마다 같은 카드 묶음에 FAIL·WARNING·OK 를 섞은 것)으로 돌려 만든 원장이다. ① 12명이 FAIL 로 본 클러스터는 `held_fail`·P1 이다(등록부 값은 중대/WARNING). ② 인용 대조를 지난 FAIL 이 없으면 같은 클러스터가 P2 다. ③ 한 명만 낸 중대 클러스터는 `solo_severe` 다. ④ 같은 단위·같은 줄에 OK·대조 통과를 낸 전문가가 둘이고 그 셀 신고에 같은 코드가 있으면 `split_verdict` 이고, 한 명이면 아니다. ⑤ P1 30건이면 30건 전부 `queued`, P1 60건이면 48건 `queued`·12건 `untried_cap`, P1 10건·P2 30건이면 P1 10 + P2 14 가 `queued` 다. ⑥ 원장 행을 섞어 넣어도 같은 순서다. ⑦ 사람이 닫은 행은 후보가 아니다. ⑧ 해결된 쟁점의 제기자 집합이 바뀌면 `queued` 로 돌아가고, 그대로면 그대로다. ⑨ 상한 셈이 다시 고른 회차에서도 누적이다.
- **의존.** S3-4.
- **크기.** 8시간.

### S3-7 쟁점 패널 (WP4 8 의 뒤 절반)

- **목적.** 쟁점 하나를 지금 심의 엔진의 작은 패널 하나(3라운드)로 판정하고, 그 결과로 등록부 행을 덮되 원래 분포를 같은 줄에 남긴다(D-34). 실패·재기동에서 쟁점이 사라지거나 두 번 판정되지 않는다.
- **파일 · 닻.**
  - `issues.py` — `plan_issue_panel(store, target_key, *, job, settings=None) -> dict | None`(한 트랜잭션에서 `rr_panels` INSERT(`kind='issue'`·`tier='I'`·`issue_id`) + `UPDATE rr_issues SET state='planned' … WHERE state='queued'` 의 rowcount 1 일 때만 — `plan_next_panel` 의 `PlanConflict` 방식) · `seats_for(issue)` · `issue_question(store, issue) -> str`(600자 안, 부품 이름·변경 종류·메커니즘 이름과 '네 필드를 [근거] I1 의 값 그대로 쓰라') · `start_issue_panel` · `release_issue(store, panel_id, *, charge)` · `resolve_issue(store, panel_id) -> {issue_id, state, outcome}`.
  - `brief.py` — 새 `build_issue_brief(store, target_key, issue, *, seats, panel_id, profile, strict_lint=False)` 와 `ISSUE_CAPS`(바닥 표 — 프로파일 배수로 큰다, `web_profile(engine_budget)` 그대로) · `_QUOTED_SOURCES` 에 `issue_verdicts`·`issue_cards`·`issue_handoffs`.
  - `runner.py` — `run_panel` 의 `planner.plan_next_panel` 자리에서 `job.mode == 'issues'` 면 `issues.plan_issue_panel`, `planner.start_panel_seats` 대신 `issues.start_issue_panel`, `build_delib_opts` 의 `panel['kind'] == 'issue'` 갈래(근거 = `build_issue_brief`, 질문 = `issue_question`, 지정 도구 `[]`, `rounds=3` 고정 — `panel_budget` 을 쓰지 않는다, `save_report=0`, `knowledge_query` = 질문), `_complete_panel` 의 `apply_seat_results` 를 건너뛰고 `issues.resolve_issue` → `registry.merge` → `closure.refresh`, `fail_panel_seats` 를 부르는 다섯 자리와 `recover_running_panels` 에서 쟁점 패널이면 `issues.release_issue`, `_diminishing` 의 조회에 `kind = 'coverage'`, `repersist_panel` 의 끝에 `resolve_issue`.
  - `narrative.persist_panel_result` — `kind='issue'` 면 모든 좌석이 원장 밖 회차(`NONLEDGER_CYCLE_BASE + panel_no`), `rr_character` 를 앉히지 않는다, finding 은 `source_kind='issue_panel'`·`source_id=panel_id`·`unit_id`=쟁점의 단위, 닻 맞춤(원자의 `subject_key` 와 메커니즘 대분류가 닻과 같은데 키만 다르면 삽입 때 `cluster_key` 를 닻 키로 두고 계산값은 `finding_json.cluster_key_computed` — WP4 3.7.6). `narrative._panel_scope` 의 쟁점 갈래 — 근거에 실은 카드 절과 단위 줄을 인용 범위에 싣는다(P-17-7).
  - `routes.complete_panel`(REST 재제출 — 러너와 같은 갈래), `mcp_server.risk_submit_panel_result`(`issue_panel_web_only`), `planner.check_invariants`(쟁점 패널은 `issue_id` 가 있고 쟁점의 `panel_id` 와 맞다 · 좌석이 로스터 안이다).
- **좌석.** 로스터 좌석 최소 2 · 최대 5, 기준선 옹호 지정석은 엔진이 더한다. 제기 석 1~2(인용 대조를 지난 사람 → 근거 등급 → `rank_in_domain` → 키, 영역이 다르면 다른 영역 먼저), 반대 석 0~2(3.6 의 반대 측, 같은 순서), 반대가 없으면 인접 석 1~2(닻 메커니즘의 배정표 소유 ∪ 관련 영역 가운데 제기 석과 다른 영역에서, 그 단위 셀이 `reviewed` 이고 `applies='yes'` 판정이 많은 사람). `seats_json` 한 줄은 `{key, domain, origin, rank_in_domain, issue_role}`(`origin` 은 제기 `primary` · 반대·인접 `counter` — `rr_seat_opinions.origin` CHECK 안이다).
- **근거 — 무엇을 먹이나(`build_issue_brief`).** 엔진이 뒤 항목부터 버리므로 순서가 뜻이 있다(작은 창 — P-17-3).

| 키 | 내용 | 원천 |
|---|---|---|
| I1 | 쟁점 정의 — 유형, 닻의 `mechanism`·`mechanism_detail`·`subject`·`change_kind`(그대로 쓰라는 값), 분포(제기 n명·영역별, 주장 판정별 수, 심각도별 수, 반대 n명), hold 표기('등록부 값은 hold 로 WARNING — 원래 FAIL 9명') | `rr_issues.basis_json` · `rr_registry` |
| I4 | 제기 측 판정 — 전문가·카드 `card:<record_id>#<sid>`·카드 인용 원문·변경 줄 인용·사유·주장 심각도·영향 경로·닫는 확인·조건별 대조 줄·인용 대조 여부. 카드 밖 지적이면 그 `f` 줄 | `rr_card_verdicts`(실효·solo) · `rr_findings` |
| I5 | 반대 측 판정 — 같은 모양(OK 행의 인용·참조·사유) | 같음 |
| I6 | 인용된 카드의 **인용이 맞은 절만** 원문으로(같은 절은 한 번) — 대조를 못 지난 인용의 카드는 제목과 '인용 대조 실패' 만 | 얼린 팩(`cardpack.load_pack`, 판정 행의 `section_id`) |
| I2 | 변경 원문 — 그 단위에서 대상 부품에 걸린 변경 줄과 문맥 줄 전부(정규 표기, `[c:…]`) | `units.review_payload` |
| I3 | 근거 발췌 — 그 단위의 동결 발췌 가운데 대상 부품 것 | `rr_units.evidence_gz` |
| I0 | 스코프·게이트·결측(지금 E0 그대로) | `brief._item_e0` |
| I7 | 넘김 — 그 단위에서 다른 영역으로 넘긴 줄 가운데 대상 부품·닻 영역에 닿는 것 | `rr_review_cells.handoffs_json` |
| I8 | 같은 대상의 선례(E5 조립기를 대상으로 좁혀) | `rr_registry` |
| M | 사용자 메모 | 잡 |

  좌석 계약(I0c)은 러너가 지금처럼 둘째 칸에 끼운다. 항목 수는 `brief.EVIDENCE_MAX_ITEMS`(12) 안이다. 크기는 `web_profile` 의 배수로 큰다(1M 창 약 500,000자 — 낮은 고정 천장 없음, D-21). 카드 원문(I6)을 절 단위로 좁히는 까닭은 둘이다 — 인용되지 않은 절이 `rr_panels.brief_gz`(반출되는 열)에 남지 않게 하고(WP5b 카나리아), 좌석이 볼 것을 그 쟁점에 맞춘다. 전문가·카드의 글(I4·I5·I6·I7)은 `_QUOTED_SOURCES` 라 판단어 린터가 코드 산문으로 읽지 않고, 전부 «» 안이다(앞 단계 LLM 출력의 2차 주입 위생 — WP5b 3.10.4).
- **실패와 재개.**

| 일 | 패널 | 쟁점 | 잡 |
|---|---|---|---|
| 엔진 관문 자리 없음(`EngineBusy`)·스트림 놓침·결정문 없음 | 지금 패널과 같은 닫기(`_close_panel_*`) | `queued` 로, 차감 없음 | 지금 규칙(멈춤 또는 다음 틱) |
| 재기동(`recover_running_panels`) | `error('restart')`. 결과가 저장돼 있으면 `persist_error` 로 다시 저장 대기(M1) | `queued`, 차감 없음 | 멈춘다 — 사람이 재개(자동 재개는 M4) |
| 결정문 파싱 실패 | `done`·`risk_spec_parsed=0` | `charged + 1`, 한도(2)면 `inconclusive(spec_parse_failed)`. `POST /panels/{id}/complete` 재제출로 고치면 `resolve_issue` 가 다시 돈다 | 계속 |
| 연속 3패널 오류 | — | 남은 `queued` → `untried_cap(engine_fail)` | `failed` → 종합을 잇는다(S3-5) |
| 결과 저장 실패 | `persist_error`(M1 선저장) | `running` 그대로 — 다시 저장(`risk_repersist_panel`)이 `resolve_issue` 까지 한다. 포기하면 `queued` | 멈춘다 |
| 일일 패널 상한(24) | — | `queued` 그대로 | `paused(daily_cap)` → 다음 날 지금 규칙대로 |

- **수용 기준.** WP4 3.7 전부(좌석 원장 함수를 부르지 않는다 · 회차 · 성격 진술 없음 · 닻 맞춤 · 3라운드 고정) · P-17-3(순서) · P-17-4·5(결과 판정) · P-17-7(인용 범위) · P-17-8 · X3(`save_report=0`) · D-34(덮되 분포) · M2 #12 와 같은 태도(다시 저장 대기 패널이 있는 대상은 새 쟁점 패널을 편성하지 않는다 — `awaiting_repersist`).
- **시험.** 입력은 S3-6 의 선정 결과(생산자 함수)다. ① 편성 전후 `rr_coverage` 표 전체 해시가 같다. ② 같은 전문가를 쟁점 패널 둘에 앉혀도 저장된다(회차가 갈린다). ③ 근거의 순서가 I1 → I4 → I5 → I6 → …이고, I6 에 인용되지 않은 절이 없으며(카나리아 절을 심은 합성 카드), 판단어 린터를 `strict` 로 지난다. ④ 질문에 부품 이름과 메커니즘 이름이 있다. ⑤ 가짜 패널 엔진이 닻과 키만 다른 원자를 내도 닻에 붙고 `cluster_key_computed` 가 남는다. ⑥ 결과 다섯 갈래(upheld · downgraded · escalated · rejected · undetermined)가 3.6 표대로이고 등록부 행이 3.5 표대로다. ⑦ 실패 표의 줄마다 한 시험(재기동은 실제 `recover_running_panels`). ⑧ 쟁점 패널 셋이 잇달아 새 클러스터 0 이어도 잡이 `diminishing` 으로 멈추지 않는다. ⑨ 늦게 끝난 옛 패널의 재제출이 지금 패널의 결과를 덮지 않는다. ⑩ `build_delib_opts` 출력에 `save_report: 0`·`rounds: 3`·`tools: []` 가 있고 포털 `DelibOpts` 계약 시험(`test_delib_opts_contract.py`)을 지난다.
- **의존.** S3-6 · S3-4 · S3-2(배정표 — 인접 석).
- **크기.** 18시간.

### S3-8 완결 판정 (WP4 9 — 3.8)

- **목적.** '빠짐없이 봤다' 를 코드가 세는 수로 내고, 못 본 것을 모든 레벨의 표기에 붙인다. 잔여가 남으면 맨 `C3` 를 적지 않는다.
- **파일 · 닻.** 새 `app/closure.py` — `cell_counts(store, target_key) -> dict` · `residuals(store, target_key, counts) -> list[dict]` · `close_level_cells(store, target, *, persist) -> dict` · `level_label(level, residuals, *, state) -> str` · `refresh(store, target_key) -> dict`(캐시 쓰기) · `ack_residual(store, target_key, item, *, reason, by, basis_hash)` · `revoke_ack(store, target_key, item, *, by)`. `registry.close_level` 은 문지기(흐름 갈래, 옛 본문은 `_close_level_panels` 로 이름만). `routes` — `GET /targets/{key}/closure` · `POST|DELETE …/closure/acks/{item}` · `coverage_payload` 가 `cells` 대상이면 캐시를 읽는다. `review_quality.compute`(품질 기준 밖 · 셀 기준 strong), `review_cells.closure_cells`(3.13), `planner.review_order`(Tier · 대표), `units` 의 활성 빌드(미배정·제외 사유).
- **수용 기준.** X1-01(넘김 잔여 · 분모 · 영역 × 단위 몰림) · X1-02(모든 레벨 · 실제 검토한 전문가만 · 영역 전원 결손은 잔여) · X1-03(카드 판정 비율 대신 폭포) · X1-04(basis 로 가른다) · X1-05(셀 기준 strong) · X1-07(빈 격자·끊긴 사슬·낡은 후속은 참이 아니다) · X1-10(제외 항목) · X1-13(표본 — 판단 불가는 놓침 쪽, `m3-cells` 가 낸 수를 쓴다) · X1-18 (3)(미토의 표기에 주장 FAIL 수) · X1-24(낮아진 계산 · `level_label` 저장) · X1-27(분모는 늘 로스터 × 검토 대상 단위) · P-12 · P-13 · P-17-13 · P-17-14(노출 전수 칸은 `unassigned` 만) · D-13 · D-34(기본 마감 전원) · WP5b 3.4.5 C-a~C-e.
- **시험.** 결정표와 속성은 S3-12 의 C11 이다. 이 걸음은 함수 단위로 — `level_label` 이 잔여 0 일 때만 맨 레벨 이름이다. 확인의 `basis_hash` 가 어긋나면 409. 사유가 빈 확인은 422, 편집자의 확인은 403. 확인·취소마다 `rr_audit` 한 행. 캐시가 병합·쟁점 해결·확인·셀 처분 뒤에 새로 써지고, 진행판 응답이 캐시와 같다. `cells` 대상 2,000셀 · finding 5,000건 원장에서 `refresh` 한 번이 1초 안이다(실측해 적는다).
- **의존.** S3-4 · S3-6(쟁점 수) · S3-5(사슬 단계의 지문), `m3-cells` 의 셀 상태·`closure_cells`·롤업.
- **크기.** 14시간.

### S3-9 영역 요약과 종합 보고서 (WP4 10 — 3.9 · 3.10)

- **목적.** 15개 영역 요약과 과제 종합 서술을 LLM 이 쓰되, 모든 표와 수는 코드가 내고 그 수가 완결 판정과 같다. LLM 이 죽어도 보고서는 나온다.
- **파일 · 닻.** 새 `app/synth.py` — `domain_rows(store, target_key, domain) -> list[dict]` · `row_line(row) -> str` · `plan_summaries(store, target_key, *, run_id) -> dict`(입력 해시가 같은 `done` 행이 있으면 다시 만들지 않는다) · `summary_request(store, summary) -> dict` · `check_summary(result, rows) -> dict` · `class SynthWorker`(`claim` → 요약 행 하나씩 → 엔진 `run(kind='summary')` → 검사 → 저장, 기다림·인프라·내용 탓은 `review_ops.classify` 와 `backoff_s`) · `assemble_report(store, target_key, *, trigger) -> dict` · `render_report_md(report, *, part)` · `render_pages(report, page_chars)` · `report_source(store, target_key, *, version)`. `engine_client.PortalReviewEngine.run` 이 `kind='summary'` 본문을 그대로 넘긴다(`run_body` 와 나란한 `summary_body`). `rr_review_calls` 에 요약 호출 한 행씩(`kind='summary'`, `agent_key='synth'`). `runner.RiskRunner._synth_tick`. `review_quality.block` 을 보고서 minutes 에 그 판의 고정본으로. `config.BOX_KNOBS` 에 `HWAXRISK_SUMMARY_MAX_CHARGED`·`_INFRA_MAX`. `routes` — `GET|POST /targets/{key}/report`.
- **계약.** 3.9 · 3.10 그대로.
- **수용 기준.** WP4 3.8(누가 무엇을 쓰나 · 표지 대조 · `code_only`) · P-08 ③(인프라 6번 · 내용 탓 2번 뒤 `code_only`, 창 초과도 `code_only` 이고 크게 알린다) · P-16(조립은 트랜잭션 밖, try/except) · P-17-9(단위 0 대상은 사람이 부르면 한 판) · P-17-12(요약 줄 표기는 린터 허용 꼴) · X1-03 · X1-04 · X1-15 (3) · X1-18 (2) · D-21(행을 버리지 않는다) · M3 나갈 기준 4(영역 요약 15건과 종합, 그 수치가 완결 판정과 같다) · WP5b 3.11.3(품질 블록 문면 규칙 여섯).
- **시험.** 입력은 S3-5 의 사슬을 가짜 엔진들로 끝까지 돌린 원장이다. ① 로스터 영역 15개 전부에 요약 행이 서고, 행 0 인 영역은 LLM 호출 없이 `code_only(no_rows)` 다. ② 가짜 요약 엔진의 결과가 엔진 계약 예제 모양 그대로(`result_summary_missing.json` — 보충을 다 써도 `must_cover` 하나가 빠짐, `checks.nums_unsourced` 가 선 줄)이면 앱이 지적을 실어 한 번 다시 묻고, 두 번째도 그러면 `code_only(checks_failed)` 이며 보고서가 그 쪽에 '서술 없음 — 까닭' 을 싣는다. ③ 주의 A 행이 `cover_max` 를 넘으면 `must_cover` 는 상위 `cover_max` 건이고 보고서에 '서술은 A 상위 N건 — 나머지 M건은 표' 가 있다. `runnable.summary=false` 면 LLM 호출 0 · `code_only(ctx_too_small)`. ④ 엔진이 늘 인프라 오류면 6번 뒤 `code_only(infra_exhausted)` 이고 보고서 판이 선다(`narrative_state='partial'` 또는 `none`). ⑤ **보고서 머리의 수 == 같은 시점의 `closure.cell_counts`**(문면에서 수를 다시 읽어 견준다 — WP5b 3.11.3 규칙 5). ⑥ 내용이 같으면 새 판을 만들지 않는다. ⑦ 주의 C 는 본문에 표가 없고 건수만, 치명·FAIL(주장값 포함)은 어느 등급이든 본문에 있다. ⑧ 쪽을 이어 붙이면 `part='full'` 과 같다. ⑨ 부록 색인이 로스터 수와 같은 줄 수다. ⑩ 요약 프롬프트(가짜 엔진이 받은 본문)에 카드 절 원문이 없고, 앞 단계 LLM 글은 «» 안에만 있다.
- **의존.** S3-8(수) · S3-4(등록부) · S3-7(쟁점 결과) · `m3-engine-ops` 의 `summary` 종류와 계약 예제.
- **크기.** 16시간.

### S3-10 REST · MCP (WP4 12 — 3.11)

- **목적.** 웹과 Claude 가 같은 함수로 쟁점과 종합 보고서를 읽는다(D-23). 359명 로스터 · 쟁점 48건에서도 MCP 응답 하나가 와이어 25,000자 안이다.
- **파일 · 닻.** `routes.py` — `issues_payload` · `PUT /issues/{issue_id}` · `report_source`·`report_render`·`report_envelope` · `registry_payload`·`coverage_payload` 의 새 칸 · `panels_payload`·`transcript` 의 `kind`·`issue`. `mcp_server.py` — `risk_get_issues`·`risk_get_report` 와 `_INSTRUCTIONS`, `risk_get_registry` 의 인자 둘과 `_fit_rows` 감싸기, `risk_submit_panel_result` 의 쟁점 패널 거절. `entry.next_step`(3.11). `.portal/manifest.yaml` 의 `mcp.description`. `tests/test_mcp_tools.py`(`TOOL_NAMES` 31 · `CALLS` · 빈 원장 기대) · `tests/test_no_write_tools.py` · `tests/test_p6_routes.py` · `tests/test_mcp_entry.py` · `tests/test_mcp_brief_relay.py`(와이어 상한 값 공유).
- **수용 기준.** PLAN 4절 C-30(31종) · REST 한 벌 · D-23 · D-24 · P-17-2(도구 수 단언은 '앞 목록 + 둘') · M2.md 4.8 의 쪽 나누기 규율.
- **시험.** 응답 필드를 스냅샷 시험으로 못 박는다(프런트 세션의 계약). 남의 대상은 REST 404 · MCP `not_visible`(경로 목록은 라우터에서 뽑는다 — WP5b 3.10.1). 쟁점 48건·각 제기자 120명 원장에서 `risk_get_issues` 한 번의 와이어가 25,000자 안이고 `next_offset` 으로 이어 받으면 전부다. 영역 15쪽·부록 359줄 보고서에서 `risk_get_report` 의 쪽 전부가 와이어 안이고 이으면 `part` 전체다. `version` 이 어긋나면 409. 위임 단언 없는 Bearer 로 새 읽기 도구는 지금 읽기 도구와 같은 갈래다. 쓰기 도구 목록이 그대로다.
- **의존.** S3-6 · S3-7 · S3-8 · S3-9.
- **크기.** 7시간.

### S3-11 JS 안내문 · 문서 · 업데이트 이력 (WP4 14)

- **목적.** Claude 사용자가 `cells` 대상의 쟁점 패널을 보충 회차로 돌리려다 막히는 까닭과 대신 쓸 도구를 안내문에서 읽게 한다.
- **파일 · 닻.** HWAXPortal `infra/pipeline/hwax-risk-review.js` 의 `meta.whenToUse` 한 문장('카드 대조(flow=cells) 대상은 받지 않는다 — 그 대상의 쟁점 패널은 웹 러너가 돌리고, 쟁점은 risk_get_issues, 종합 보고서는 risk_get_report 로 읽는다'). 코드는 고치지 않는다 — `cells` 대상은 이미 `cells_flow_web_only` 로 브리프를 내지 않는다(`routes._cells_flow_web_only`). `./infra/scripts/sync-workflows.sh` 로 사본을 맞춘다. 문서 — 이 폴더 `checklist.md`·`context-notes.md`(결정 기록), `docs/design-risk-review/`(계획 §6.9 완결 조건과 §4.7 병합의 개정 한 단락), `docs/changelog.md`(사용자 체감과 기술 둘 다 — 메모리 '이력에 기술 변경도 전부'), cae00 절차서 `server-setup-m3.md` 의 이 꾸러미 몫(배포 조건 — 살아 있는 검토 잡이 없을 때, 배정표 승인 커밋, 확인 화면 경로).
- **수용 기준.** WP4 3.13 · P-17-8 · CLAUDE.md '심의 파이프라인'(JS 를 고치면 sync).
- **시험.** `./infra/scripts/sync-workflows.sh --check` 종료코드 0. 포털 파리티 시험(`test_parity`·`check_chair_parity.py`)이 그대로 초록이다(문구는 `whenToUse` 뿐).
- **의존.** S3-10.
- **크기.** 3시간.

### S3-12 WP5b 시험 — 이 꾸러미 몫 (C10 · C11 · C12 · C14 · C16)

- **C10 품질 수치(이 꾸러미 몫).** 거르기 칸·입력 결손 칸·뒤집힘 모집단(`rq-2`)은 `m3-cells` 가 `review_quality` 에 넣는다. 이 꾸러미는 둘만 한다 — 품질 블록을 종합 보고서 판에 그 판의 고정본으로 싣는 것(WP5b 3.11.1)과, `quality` 잔여(3.8)가 `compute(...)['out_of_bounds']` 와 셀 기준 strong 비율을 읽는 것. 보고서 문면이 '음성 → 걸림' 뒤집힘을 `rq-2` 의 모집단(1순위 보정 셀)으로만 말하고 그 밖은 `미측정` 으로 적는지 본다(D-33 — 8절 5). 시험 — 손으로 센 작은 원장(생산자 함수로 만든 것)과 값이 같다 · 문면의 수 == `json` 의 수 · 문면 린터 위반 0 · 옛 타깃은 한 줄.
- **C11 완결 판정 결정표.** 새 `tests/rr/test_close_level_cells.py`. 원장은 S3-5 의 사슬을 가짜 엔진으로 돌리고 `m3-cells` 의 셀 상태 전이 함수로 상태를 만든다(손 INSERT 없음). 결정표 14행 — ① 단위 0 → `C0(심사할 단위 없음)` ② 격자 결손 → C0 ③ 대표 셀 미종결 → C0 ④ 대표 종결·나머지 열림 → `C1(…)` 에 잔여와 '열린 셀 N' ⑤ Tier B 범위 종결·깊이·쟁점 신선·P1 열림 0 → C2 ⑥ 마감 레벨 C2 대상에 막음 잔여 → `C2 · 마감 대기(…)`, 확인 뒤 `C2(closed)(…)` ⑦ 전원 종결·막음 잔여 0 → 저장 C3, 표기 `C3(2차 영향 미실행 · 결손 사냥 미실행)` ⑧ 전원 종결·`input_gap` 미확인 → `C2 · C3 대기(입력 결손 …)` ⑨ 그 확인 → `C3(입력 결손 … · …)` ⑩ 확인 뒤 `no_input` 셀 하나 더 → 확인 낡음 → 대기, 저장 레벨은 그대로이고 `regressed` ⑪ `pending` 한 셀 → 확인과 무관하게 C3 아님 ⑫ 회로 6영역 전원 `no_input` → C1·C2 표기에 입력 결손과 영역 이름(X1-02) ⑬ 쟁점 선정 뒤 셀이 다시 열려 재검토 → 후속 낡음 → C2 거짓·'후속 낡음(재검토 N셀)' ⑭ 거른 셀의 표본에서 놓친 걸림 → `filtered` 표기에 놓침 수. 속성 다섯 — C-a 단조 · C-b 빈 칸(`pending`·`running` 이 있으면 C3 아님 — `failed` 는 확인하면 C3 가능, C-18 로 바뀐 뜻을 적는다) · C-c 도배(전부 `reviewed` 여도 검증 인용 0 이면 `quality` 잔여가 C2 를 넘지 못하게 막는다) · C-d 입력 결손(깊이의 분자·분모에 없다, 남으면 표기) · C-e 옛 타깃(셀 없는 대상은 `_close_level_panels` 와 같은 값 — 열세 건과 골든).
- **C12 보안.** 새 `tests/rr/test_security_synthesis.py`. ① 카나리아 — 합성 카드의 인용되지 않는 절에 `CANARY-<hex>` 를 심고 사슬을 끝까지 돈 뒤 쟁점 패널의 `brief_gz`·엔진에 간 근거·요약 엔진에 간 본문·`rr_reports.pages_gz`·`rr_summaries`·`rr_issues`·REST·MCP 응답(새 경로·도구 전부)·반출 파일·로그(caplog)에 없다. 있어야 하는 곳은 묶음 동결본과 카드 대조 프롬프트뿐이다(WP5b 3.10.1). ② 인용 상한 — 보고서·쟁점 응답·반출의 카드 인용이 판정당 200자를 넘지 않는다. ③ 남의 과제 — 새 REST 경로 전부 404, 새 MCP 도구 전부 `not_visible`(경로 목록은 라우터에서 뽑는다). ④ 확인 권한 — 편집자 403, 소유자·관리자만, MCP 경로 확인 없음. ⑤ 2차 주입 — 카드 대조의 `why`·`mech_free`·카드 밖 `title` 에 주입 문구를 심은 원장으로 쟁점 근거와 요약 본문을 만들면 그 문구가 «» 안에만 있다(WP5b 3.10.4 의 넷째 줄).
- **C14 대역 일치.** ① 쟁점 패널의 SSE — dev 리허설(S3-13)에서 실제 엔진이 낸 쟁점 패널 프레임을 긁개를 거쳐 `tests/fixtures/sse/captured/issue_panel_*.sse` 로 남기고 가짜 패널 엔진이 같은 모양인지 본다(`tests/rr/test_fake_conformance.py` 에 한 갈래). ② 요약 호출 — 엔진이 만든 계약 예제(`run_summary_*.sse`)를 앱의 요약 클라이언트가 그대로 먹고, 가짜 요약 엔진이 같은 프레임을 낸다(형제 경로가 곁에 있는데 못 읽으면 skip 이 아니라 실패 — P-22).
- **C16 문서.** S3-11 과 같은 커밋 묶음.
- **수용 기준.** WP5b 3.4.5 · 3.10 · 3.11 · C10~C12 · C14 · C16 가운데 이 꾸러미에 닿는 것.
- **의존.** S3-5~S3-10, `m3-cells`(셀 상태·`closure_cells`·`rq-2`), `m3-engine-ops`(요약 계약 예제).
- **크기.** 12시간.

### S3-13 리허설 · v5 확정 · push · cae00 전원 실주행 지원

- **목적.** v5 를 dev 리허설로 검증한 뒤에만 push 한다(C-2 · D-7). M3 나갈 기준 2~5 의 증거를 cae00 에서 댈 수 있게 한다.
- **차례.**
  1. 세 리포 시험 전체(리스크 앱 `cd backend && .venv/bin/python -m pytest -q`, 에이전트 서버, 포털)와 계약 예제 해시 가드.
  2. dev 배선 리허설 — M2 의 `tests/synth/rehearsal_d.py` 를 넓힌다(빈 포트·스크래치 디렉터리·가짜 LLM 1M 창·임시 에이전트 서버·임시 포털·임시 리스크 앱, 실 저장소 무접촉 단언 그대로). 합성 대상 하나에서 전문가 15명(영역마다 대표 — 거르기·입력 결손이 섞이게 `m3-cells` 손잡이를 켠다) × 전 단위 검토 → 사슬 자동 진행 → 쟁점 패널 2건 이상(가짜 LLM 대본이 FAIL 을 내게) → 종합 잡 → 보고서 판 넷. 도중에 리스크 앱을 SIGKILL 로 한 번 내리고(쟁점 패널 도는 중) 올려서 쟁점이 `queued` 로 돌아오고 잡을 사람이 재개하면 끝까지 가는 것을 본다. 포털 대화 수(쟁점 패널은 대화를 만든다 — 그 수가 쟁점 패널 수와 같다), 요약 호출이 대화를 만들지 않는 것, `save_report` 0 이라 RA 초안이 생기지 않는 것을 센다. 판정의 질은 보지 않는다.
  3. 리허설이 표 모양을 바꾸라고 하면 v5 를 고친다(push 전이라 고칠 수 있다). `PUSHED_DDL_SHA256[5]` 를 굳힌다.
  4. **배포 조건** — 살아 있는 검토 잡이 없을 때(3.3 의 `prompt_rev` 올림과 택소노미 1.2). 에이전트 서버(`cr-verdict-2` + `summary`)를 먼저 올리고, 리스크 앱 push → hwax-risk SIF → dev 인스턴스 교체(`apptainer instance list` 출력에서 이름을 확인하고 내린다, 다시 올리는 것은 허브에 맡긴다) → 이행 사본 `pre-migrate-v4-*` 확인 → 게이트웨이 `tools/list` 에서 `risk_get_issues`·`risk_get_report` 를 실제로 본다(31종).
  5. cae00(사용자) — 절차서 `server-setup-m3.md` 의 이 꾸러미 몫. 배정표를 사용자가 훑고 `review_status:"approved"` 커밋(그 전에는 거르기가 꺼진 채로 돈다). 실제 대상 1건 · 359명 전원 → 사슬 → 쟁점 패널(상한 안 전부) → 종합 → 완결 표기를 읽는다. 사람 몫은 출력 문구 기준으로 적는다.
- **수용 기준.** M3 나갈 기준 2~5 의 증거를 모은다(5절 표).
- **의존.** S3-1~S3-12, 형제 계획 둘의 dev 배포.
- **크기.** 10시간(cae00 벽시계·사용자 시간 제외).

## 5. 나갈 기준 대응 · 크기

### 5.1 M3 나갈 기준(PLAN 3절)과 걸음

| 나갈 기준 | 이 꾸러미의 걸음 | 보는 곳 |
|---|---|---|
| 1 모든 셀이 종결이거나 사유 있는 `failed`, 그 수와 사유가 종합 보고서 머리에 | S3-8 · S3-9(머리 표) — 셀 상태와 처분은 `m3-cells` | `GET …/closure` 의 `counts.cells`, 보고서 1쪽 background |
| 2 전문가 보고서 359편 | S3-8(`counts.experts.reports` — 빠지면 일이 덜 끝난 것이라 C1 부터 막는다) · S3-9(부록 색인 359줄) — 보고서 자체는 M2 S10 과 `m3-cells`(입력 결손·거름 전문가의 보고서) | `reports.missing = 0`, 부록 줄 수 == 로스터 |
| 3 쟁점 패널이 상한 안에서 전부 끝났고 상한 밖은 '미토의 쟁점' | S3-6 · S3-7 · S3-9 | `GET …/issues` 의 `state`, `queued·planned·running` 0, 보고서 recommendation 의 미토의 행 |
| 4 영역 요약 15건과 종합, 그 수치가 완결 판정과 같다 | S3-9 · S3-8 | `rr_summaries` 15 + 1, `rr_reports.counts_json == closure.cell_counts`(같은 호출) |
| 5 잔여를 달고 나온다, 잔여가 있으면 맨 `C3` 가 아니다 | S3-8 · S3-12(C11) | `level_label`, 결정표 14행 |
| 6 비우기로 이어 돈다 · 챗 지연 2배 안 | (`m3-engine-ops`) — 이 꾸러미는 쟁점 잡·종합 잡이 `draining` 을 기다림으로 다루는 것만(3.7) | — |

### 5.2 WP4 문제와 걸음

| 문제 | 걸음 | | 문제 | 걸음 |
|---|---|---|---|---|
| P-01 마감 범위 | S3-5 · S3-6 | | P-10 다시 물은 칸 | 뺀다(교차·사냥 M4) |
| P-02 hold 와 쟁점 | S3-4 · S3-6 · S3-9 | | P-11 v5 | S3-1 |
| P-03 split_verdict | S3-6 | | P-12 파싱 실패 셈 | S3-8 |
| P-04 도장 한도 | 뺀다(사냥 M4) — 메커니즘 신고는 표만 | | P-13 C2 의 입력 결손 | S3-8 |
| P-05 표본 주체 | `m3-cells` | | P-14 넘김 영역 이름 | S3-9(표에 실을 때 영역 코드로 정규화, 못 맞추면 '영역 미상' 줄 — 교차 칸은 M4) |
| P-06 사슬의 손 | S3-5 | | P-15 material 소유 | S3-2 |
| P-07 같은 모듈 두 꾸러미 | S3-3 · `m3-engine-ops` | | P-16 보고서 자리 | S3-9 |
| P-08 보고서가 사슬 끝에만 | S3-5 · S3-9 | | P-17 묶음 | 1 S3-2 · 2 S3-10 · 3 S3-7 · 4·5 S3-6 · 6 S3-3·S3-4 · 7 S3-7 · 8 S3-7 · 9 S3-9 · 10 S3-4 · 11 S3-13 · 12 S3-9 · 13 S3-8 · 14 S3-8 · 15 뺀다(snap 은 M4) |
| P-09 자격 승계 | S3-5 | | | |

X1 은 S3-8 의 수용 기준(위)에 적었다. 이 꾸러미에 닿지 않는 것 — X1-08·X1-09(교차·사냥, M4), X1-11·X1-12·X1-16·X1-17·X1-19~X1-23·X1-25·X1-26(셀·엔진 — M2 에서 닫혔거나 `m3-cells` 몫), X1-14 는 실효 규칙이 M2 S4 에서 들어갔고 쟁점 쪽은 `held_fail` 이 받는다(변형이 갈린 카드는 `judgement_claimed` 가 가장 무거운 값이다).

### 5.3 크기

| 걸음 | 시간 |
|---|---|
| S3-0 시작 | 3 |
| S3-1 v5 | 7 |
| S3-2 택소노미·배정표 | 6 |
| S3-3 #25(앱 쪽) | 4 |
| S3-4 병합 | 12 |
| S3-5 사슬 | 10 |
| S3-6 쟁점 선정 | 8 |
| S3-7 쟁점 패널 | 18 |
| S3-8 완결 판정 | 14 |
| S3-9 요약·종합 | 16 |
| S3-10 REST·MCP | 7 |
| S3-11 안내문·문서 | 3 |
| S3-12 시험 | 12 |
| S3-13 리허설·push | 10 |
| **걸음 합** | **130** |
| 반대 검토 라운드(단계마다)와 재작업 | 약 25 |
| **이 꾸러미 합** | **약 155** |

PLAN 8절의 M3 어림(약 80시간)은 세 꾸러미 합의 값이었다. 이 꾸러미 하나가 그 두 배다 — M2 를 꾸러미별로 다시 셌을 때와 같은 모양이다(M2.md 7절). 달력으로는 단계 A~D 에 2주 남짓, 리허설·배포에 2~3일, cae00 전원 실주행은 거르기 실측과 쟁점 패널 벽시계(6절)에 달렸다.

## 6. 위험

| 위험 | 대비 |
|---|---|
| v5 가 몇 주 가지에 머문다 — 형제 계획이나 다른 세션이 `MIGRATIONS` 를 먼저 건드리면 부딪친다 | 가지 `m3` 에서 짓고 날마다 rebase. 블록 파일의 주인 하나(S3-0 ④). HWAXRisk 문서에 'v5 는 M3 몫' 을 먼저 적는다 |
| `cr-verdict-2` 와 택소노미 1.2 가 살아 있는 검토 잡의 셀을 처음부터 다시 돌게 한다(셀 `input_hash` 에 `prompt_rev`, 요청 본문에 `extra.mechanisms`) | 배포 조건을 절차서에 — 살아 있는 검토 잡이 없을 때. cae00 M2 파일럿 대상의 마감된 finding 은 메커니즘 없이 `unclassified~` 로 갈려 남는다(받아들인다) |
| 패널을 돌린 뒤 `cells` 로 바꾼 대상(cae00 M2 파일럿이 그 길일 수 있다)은 v5 를 올린 뒤 첫 병합에서 등록부가 바뀐다 | 업데이트 이력과 절차서에 적는다. 비교용 보기 `registry?source=panels` 를 둔다 |
| 쟁점 패널은 타깃 안에서 한 줄로 돈다 — 24건이면 반나절~하루, P1 48건이면 일일 패널 상한(24) 때문에 이틀을 넘는다(패널 하나 31~87 LLM 호출, 실측 없음) | 진행판의 `stage`·`progress`, 길잡이가 남은 쟁점 수와 다음 날 재개를 말한다. 일일 상한을 쟁점에서 뺄지는 사용자 몫(7절 (b)-3) |
| 재기동이 쟁점 잡을 멈추고 자동 재개가 없다(M4) — 밤새 멈춰 있을 수 있다 | `risk_next_step` 의 막힘 맨 앞에 '재개' 를 둔다. 결과가 저장된 패널은 다시 저장이 먼저다(M1) |
| 쟁점 패널의 FAIL 이 등록부에 그대로 서서 판정 후보가 `no-go` 가 된다 | 의도한 동작(M2 사용자 결정 2). 보고서가 원래 분포를 같은 줄에 싣는다(D-34) |
| 패널 4~6석이 전문가 십수 명의 판정을 뒤집는다 | 덮되 분포를 남긴다(D-34). 사람 확정이 그 위다. 최근 다섯 패널이 전부 기각·불명이면 `issue_yield_low` 알림 |
| 요약 LLM 이 없는 수를 쓰거나 A 행을 빼먹는다 | 표·수는 전부 코드다. 엔진의 `missing`·`nums_unsourced`·모르는 별칭 표지로 한 번 다시 묻고 그래도면 `code_only`. 서술 머리에 'LLM 서술 — 근거는 아래 표' |
| 쟁점 근거(I6)와 등록부 `merged_json` 에 카드 원문이 들어와 반출로 샌다(사용자 결정 1 은 판정당 200자) | 반출 행 변환 셋(3.1) · I6 는 인용이 맞은 절만 · C12 카나리아 |
| 진행판 5초 폴링이 셀 7,000여 개 · finding 수천 건을 다시 센다 | `closure_json` 캐시(3.8). 실측해 1초를 넘으면 `_contested_marking_done` 을 병합 때 셈으로 옮긴다 |
| 배정표에 xd 를 넓게 두면 거르기가 줄이는 호출이 크게 준다 — `m3-cells` 의 호출 어림(D-33 의 3,000~5,000)이 흔들린다 | 3.4 의 '훑을 때 봐 주면 좋은 셋'. 승인 전에는 거르기가 꺼진 채로 돈다(안전 쪽) |
| M3 의 `cells` 대상은 맨 `C3` 가 될 수 없다(2차 영향·결손 사냥 미실행이 늘 붙는다) — 사용자가 '끝나지 않는다' 로 읽을 수 있다 | 표기 잔여(막지 않는다)로 두고 보고서 머리에 'M4 에서 돈다' 를 적는다(D-12 의 뜻 그대로) |
| 대분류 `rf` 가 영역 코드 `rf` 와 글자가 같다 | 두 축을 문자열로 잇는 코드가 없다(영역은 좌석 키 접두). 동의어 사전에 `rf` 를 낱말로 넣지 않고, 시험이 대분류 집합과 영역 집합의 겹침을 이 하나로 못 박는다 |
| 프런트가 `tier='I'` 패널·`kind`·`level_label` 을 모른다 | 기존 키를 지우지 않고 더하기만 한다. 응답 필드 스냅샷을 프런트 세션에 넘긴다 |
| 쟁점 패널이 포털에 대화를 만든다(종전 패널과 같다) — 카드 대조의 '대화 0건' 과 다르다 | 의도한 동작이다. 리허설에서 '대화 수 == 쟁점 패널 수' 로 센다. 요약 호출은 카드 대조 중계를 지나므로 대화가 없다 |

## 7. 열린 물음

### (a) 계획에서 정한 것 — 권고대로 간다

1. **패널을 돌린 뒤 `cells` 로 바꾼 대상의 등록부.** 두 출처를 한 등록부로 합친다. 비교는 저장 없는 보기(`source=panels`)로 한다. 대안(패널 등록부를 동결해 따로 두기)은 표가 하나 더 들고 두 등록부가 서로 다른 쟁점을 낳는다.
2. **과제를 가로지르는 통계.** `cells` 대상은 M3 동안 `rr_delta_contrib` 에 기여하지 않는다. 카드 대조 원자는 회수 자격이 0 이고(M2 #9), 실제 GLM 의 전원 결과를 사람이 읽기 전에 다른 과제의 E8 선례에 섞지 않는다. M4 에서 `STATS_VERSION 1.1`(기여 = `support_domains`)과 함께 연다.
3. **카드 대조 finding 의 회수 자격.** M2 #9 그대로 0 이다. D-32 로 형식은 승인됐지만 판정의 질은 아직 실제 GLM 으로 본 적이 없다(D-32 의 마지막 문장). cae00 전원 실주행을 읽은 뒤 과제 단위 일괄 승인 절차를 M4 에 둔다.
4. **M3 의 쟁점 유형은 셋이다** — `held_fail` · `solo_severe` · `split_verdict`. `split_severity`·`mixed_direction`·`cross_dissent`·`variant_split` 은 M4 다(변형이 갈린 카드는 `judgement_claimed` 가 가장 무거운 값이라 `held_fail` 이 받는다).
5. **상한의 뜻.** P1 을 48까지 먼저, P2·P3 은 합계 24까지. 상한은 그 대상이 돌린 쟁점 패널 누적이다(3.6). D-34 의 '치명' 은 P1(검증된 주장값 또는 등록부 값이 FAIL·치명)로 읽는다.
6. **쟁점 결과 어휘에 `escalated` 를 더한다.** 패널이 전문가들보다 무겁게 보면 그것도 덮는다(분포는 남는다).
7. **요약 출력은 JSON Lines 다**(`m3-engine-ops` A2 와 같다). 카드 대조와 같은 파서·같은 보충이고, 절단은 `finish_reason` 으로 안다(X1-22).
8. **종합 잡은 요약을 차례로 부른다.** 영역 15 + 종합 1 이 한 시간 남짓이다(호출 5분 가정). 엔진 관문을 같이 쓰므로 따로 동시 수를 두지 않는다.
9. **행이 0 인 영역의 요약은 LLM 없이 `code_only(no_rows)` 로 선다.** '15건' 에 든다.
10. **확인(ack)과 쟁점 올리기·건너뛰기는 웹·REST 만이다.** MCP 쓰기 도구를 더하지 않는다(도구 31종 고정, '되돌리기 어려운 결정은 사람이 화면에서'). 확인은 소유자와 관리자만(context-notes 권고값).
11. **잔여에 둘을 더한다** — `unit_excluded`(X1-10)와 `quality`(X1-05 · 권고값 '품질이 기준 밖이면 사람이 사유와 함께 받아들여야 닫힌다'). 사용자가 적은 일곱(입력 결손·실패·사람 넘김·미토의·2차 영향 미실행·결손 사냥 미실행·거름)은 그대로다.
12. **2차 영향 미실행·결손 사냥 미실행은 '표기' 잔여다(막지 않는다).** M3 에서 사람이 할 수 있는 일이 없는데 대상마다 확인을 받게 하면 의례가 된다. 맨 `C3` 는 여전히 나오지 않는다. **거름도 표본이 기준을 채우면 표기다** — 거르기는 사용자가 정한 정책(D-33)이라 표본이 '놓침 상한 5% 이하' 를 보였으면 확인을 다시 받지 않는다. 기준을 못 채우면 막음이다.
13. **`cells` 대상의 기본 마감은 C3 다**(D-34 '전원'). 15명·114명은 Tier A·B 로 중간 점검 지점이다.
14. **쟁점 패널은 `save_report=0` 이다.** 비공개 과제에 RA 보고서가 24~48건 생기지 않게(X3). 공개 과제도 같다 — 종합 보고서가 앱에 있다.
15. **쟁점 근거의 카드 원문은 인용이 맞은 절만**이고, 쟁점 패널의 `brief_gz` 는 반출에서 비운다.
16. **#25 는 엔진 단독 재질의 줄의 `mech` 로 한다**(3.3). 배정표는 검사에만 쓴다.
17. **배정표는 택소노미와 따로 둔다**(`mech-owners.v1.json`, 승인 문 `review_status`).
18. **`topic_key` 와 RA 저장은 v6·M4 다.**

### (b) 사용자가 정할 것

1. **메커니즘 → 영역 배정표(3.4)를 한 번 훑고 승인한다**(D-34). 특히 xd 를 얼마나 넓게 둘지(넓을수록 거르기가 덜 줄인다), mem·std 를 관련으로만 둔 것, 재질 계열의 첫 소유를 rel 로 바꾼 것. 승인 전에는 거르기가 꺼진 채로 돈다.
2. **보류(`undetermined`) 행을 잔여로 올리나**(X1-15). 지금 계면 간극 변화는 전부 `tol_unknown` 이라 간극 규칙 카드는 '가릴 값이 없다' 가 정직한 답이고, 보류가 클 것으로 본다. 권고 — 적용 판정 가운데 보류가 20% 를 넘으면 `undetermined` 잔여(막음)로 올린다. 답이 없으면 보고서에 수만 싣고 잔여로 세지 않는다.
3. **쟁점 패널을 일일 패널 상한(24)에서 빼나.** 권고 — 빼지 않는다(공유 LLM 을 지킨다). 그러면 P1 이 24건을 넘는 대상은 쟁점 단계가 이틀을 넘는다.
4. **패널을 돌린 뒤 `cells` 로 바꾼 cae00 파일럿 대상의 등록부가 M3 배포 뒤 첫 병합에서 바뀐다** — 그 전에 패널 등록부를 내보내 둘지(반출 한 번이면 된다).

## 8. D-33 · D-34 에서 틀렸거나 덜 정해진 것

1. **D-34 의 '#25 도 이 표 위에서 정한다' 는 성립하지 않는다.** 배정표는 메커니즘 → 영역이고, 카드에는 메커니즘 표지가 없다. 거꾸로 읽으면 한 영역에 메커니즘이 십수 개라 카드 하나의 메커니즘을 고를 수 없다. 이 계획은 엔진 단독 재질의 줄에 `mech` 를 받고, 배정표는 '그 전문가 영역 밖 메커니즘' 표지에만 쓴다(3.3).
2. **D-34 의 '치명 48건' 이 덜 정해졌다.** 치명만인지 FAIL 도인지, 48 이 합계인지 P1 만의 수인지가 없다. 그리고 hold 정책 아래 등록부에는 치명·FAIL 이 하나도 없으므로(카드 대조가 WARNING·중대까지만 올린다) 등록부 값으로 세면 P1 이 늘 0 이다(WP4 P-02). 이 계획은 '검증된 주장값 또는 등록부 값이 FAIL·치명' 을 P1 로, 48 을 P1 의 상한으로, 24 를 P2·P3 이 채울 수 있는 합계로 읽었다(3.6).
3. **D-34 의 '덮되 분포를 남긴다' 에 갈래 둘이 비었다.** 패널이 전문가들보다 무겁게 보는 경우(`escalated`로 정했다)와, 패널 원자가 닻에 붙지 않아 판정이 없는 경우(`inconclusive` — 덮지 않는다)다.
4. **D-34 의 '심의가 돌면 절반(4)' 은 쟁점 단계와 맞물린다.** 쟁점 패널이 곧 심의다 — 한 대상이 쟁점 단계에 들어가면 같은 박스의 다른 대상 카드 대조가 4 로 내려간다. 그 대상 자신의 검토는 이미 끝났으므로 충돌은 아니지만, 여러 대상을 겹쳐 돌리면 벽시계가 는다. 요약 호출도 같은 관문을 쓴다.
5. **D-33 의 '이중 판정은 걸린 것에만' 은 음성 → 걸림 뒤집힘을 잴 수 없게 만든다.** OK·해당 없음 판정은 순서 뒤집기를 받지 않으므로 '문제없음이라 한 카드가 순서만 바꿔도 걸림이 되나' 가 재지지 않는다(M2 는 이중 판정 전량이 그 측정을 대신한다며 무작위 음성 재질의를 뺐다 — m2-wp3b '빠지는 것'). `m3-cells` 는 영역 1순위 셀만 묶음 전체를 rev 하는 보정 모집단(`knobs.dual_calib='tier_a'`)과 무작위 음성 rev 손잡이(`HWAXRISK_REVIEW_DUAL_NEG_PCT`, 기본 0 — 그쪽 b-3)로 메운다. 이 꾸러미의 보고서는 그 모집단 밖을 0% 가 아니라 '미측정' 으로 적는다. 사용자에게 남는 물음은 그쪽 b-3 하나다.
6. **D-33 의 '거른 셀의 일부(기본 5%)' 는 작은 모집단에서 통계가 서지 않는다.** 놓침 0 으로 95% 상한 5% 이하를 말하려면 표본 59건이 있어야 해서, 거른 셀이 1,180개 밑이면 5% 로는 모자란다. 그리고 '놓친 걸림' 의 정의(판단 불가를 놓침 쪽에 넣나 — X1-13)와 '넓힌다' 의 범위가 D-33 에 없다. `m3-cells` 가 셋 다 정했다 — 표본 수 `max(ceil(5% × N), min(N, 59))` 와 영역마다 최소 1건, 결과 넷(`risk_miss`·`relevance_miss`·`undetermined`·`kept`), 넓힘 단위. 이 꾸러미는 그 수를 그대로 싣는다(3.8 `filtered`). D-33 문장 자체는 덜 정해진 채이므로 context-notes 에 그쪽 정의를 덧붙여 적기를 권한다.
7. **D-33 ② 는 배정표의 넓이에 달렸다.** '코드 신호와 훑기 둘 다 무관일 때만 거른다' 에서 코드 신호가 배정표를 쓰므로, 표에 영역을 넣는 것이 곧 그 영역을 거르지 않는 결정이다. D-33 의 어림(셀 7,200 → 2,000~2,500)은 표를 보기 전의 값이다 — xd 가 메커니즘 24개에 있으면(3.4 초안) xd 셀 2,400여 개 가운데 상당수가 남는다.
8. **D-34 의 14종 가운데 소유가 '미정' 이던 넷은 로스터로 풀렸다.** 음향 셋은 sh(센서·음향 — context-notes), 자기 간섭은 sh(`sh-magnetometer-hall`). WP4 부록이 소유로 둔 std 는 SAR 에 맞지 않는다(std 는 JEDEC·3GPP 여덟 명) — rf 로 옮겼다.
9. **PLAN 7절의 'M3 앞 — 낮 시간 동시 4' 는 D-34 의 8 로 바뀌었는데 PLAN 표가 아직 4 다.** M3 계획을 합칠 때 PLAN 7절을 고친다.

## 9. 실측이 필요한 값

| 값 | 출하 기본 | 재는 곳 | 바꾸는 자리 |
|---|---|---|---|
| 대상당 쟁점 후보 수 · P1 수 · `held_fail` 수 | 상한 24 · 48 | cae00 전원 실주행(`GET …/issues`) | `HWAXRISK_ISSUE_PANEL_CAP`·`_HARD_CAP` |
| 쟁점 패널 하나의 LLM 호출 · 벽시계 | 31~87회 · 모름 | dev 리허설(가짜 LLM 이라 호출 수만), cae00 | 진행판 어림 |
| 쟁점 결과 분포(유지·하향·상향·기각·불명) | — | cae00 | `issue_yield_low` 문턱 |
| 영역별 등록부 행 수(특히 xd) · 요약 입력 글자 | 버리지 않는다 | cae00 | 넘치면 `ctx_too_small` — 그때 영역 나누기(M4) |
| 요약 호출 초 · `code_only` 비율 | 내용 탓 2 · 인프라 6 | cae00 | `HWAXRISK_SUMMARY_*` |
| `closure.refresh` 한 번의 시간(셀 7,000여 개 · finding 수천) | 캐시 | dev 합성 큰 원장, cae00 | 캐시 시점 · `_contested_marking_done` 옮기기 |
| 보고서 판 크기(쪽 수 · 바이트) | 쪽 25,000자 | cae00 | `expert_report.PAGE_CHARS` 와 같은 값 |
| 새 표 바이트(`rr_issues`·`rr_summaries`·`rr_reports`) | — | cae00 | 백업 계획 |
| `mech_out_of_domain` 비율 | 표지만 | cae00 | 배정표 고침(사용자) |
| 넘김 줄 수 · (영역 → 영역) 쌍 수 | 표만 | cae00 | M4 의 2차 영향 범위 |
