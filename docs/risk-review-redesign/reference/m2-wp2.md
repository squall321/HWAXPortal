# M2 실행 계획 — WP2 검토 단위 · D-24 방식 고르기 · WP5a R5 최소분 · WP5b 시험 다섯

> 2026-10-12 작성. 닻은 HWAXRisk `c3f46ba`(M1 끝, 도구 26종·스키마 v3)에서 `grep` 과 직접 읽기로 다시 확인했다.
> 우선순위는 PLAN.md > problems.md > reference/04-contract.md > reference/spec-*.md 다. 아래에서 설계서와 다르게 적은 것은 그 근거(PLAN 절·문제 번호·결정 번호)를 붙였다.
> 이 문서는 읽기만 해서 썼다. 코드·시험을 돌리지 않았고 리포에 아무것도 쓰지 않았다.

## 범위

### 하는 것(M2)

| 걸음 | 무엇 | 근거 |
|---|---|---|
| 1 | 단위 순수 핵심 — 수집·묶기·줄 구조·요약 렌더·목록 글·해시·불변식 | PLAN §3 M2 `WP2 2` |
| 2 | 동결 발췌(근거 꾸러미 A 층만, 네트워크 0) | PLAN §3 M2 `WP2 7(동결 발췌만)` |
| 3 | 스키마 v4 가운데 단위 몫(`rr_unit_builds`·`rr_units`)과 `rr_targets.flow`, 반출·이양·폐기 등록 | `WP2 3`, PLAN §4 C-2 |
| 4 | WP5a R5 최소분 — 손잡이·`knobs.env`·기동 검사·`GET /api/meta/runtime`·매니페스트 설명 | PLAN §3 M2 `WP5a R5 의 최소분` |
| 5 | 저장·조회·REST·MCP 1(`risk_get_units`)·타깃 생성 훅(빌드가 안 되면 옛 흐름) | `WP2 4`, PLAN §4 '흐름 결정' |
| 6 | 방식 고르기 — `flow`(panels·cells), 돌기 전 바꾸기, 패널 위에 얹기, 문지기, 길잡이 | checklist M2 '방식 고르기(D-24)', D-24 |
| 7 | `structural.dyna.scope_changed` 인용 조회 | `WP2 6` 의 (a) |
| 8 | 검토 순서 함수 `planner.review_order` | `WP2 9` 가운데 순서 함수만 |
| 9 | change_kind 두 종(`contact_type`·`parameter`)을 정규화·스키마·택소노미에 맞춘다(조건부 — 열린 물음 4) | W2-21, R-32 |
| 10 | 실측 탐침과 실주행 절차 | `WP2 11`(CLI 는 빼고 — W2-11) |
| 11 | 게이트웨이 대조 스크립트 | `WP5b C15` |
| — | `WP5b C5·C7·C8·C9` — 주인은 WP3a·WP3b 이고 WP2 는 입력(단위)을 낸다. 아래 '시험 다섯' 표 | PLAN §3 M2 시험 |

### 일부러 빼는 것

| 무엇 | 까닭 | 근거 |
|---|---|---|
| 근거 꾸러미 B 층(실호출)·자격 순서·`ensure`·`POST /units/evidence` | 조건이 늘 거짓이고 인자가 실제 도구와 다르며 경합·캐시 결함의 대부분이 이 층이다. A 층은 IR 동결본에서 결정적으로 나오므로 빌드와 같은 트랜잭션에 얼린다 | PLAN §3 M2 '근거 꾸러미의 실호출', W2-03·W2-04 |
| 변경→영역 신호 전부(`unit_signals.py`·`part-roles`·`unit-routing` 자산의 신호 몫·`HWAXRISK_ROUTE_FILTER`)·시그니처 열(`signature_json`·`sig_hash`) | M2 는 거르기 끔이라 소비처가 없다. 시그니처의 소비처는 신호(M4)와 WP4 교차 칸(M3)이다 | PLAN §3 M2 '쓰지 않는 것', §5, W2-08·W2-09 |
| snap(현황) 단위 | 현황 타깃은 옛 흐름만 — `flow=cells` 로 열면 panels 로 열고 까닭을 싣는다 | PLAN §5 '현황 타깃의 단위', W2-15 |
| 전원 포함 — `defer_absent=False`·`undefer`·`input_gaps_json` 열·`mcad_absent` | M3 걸음이다. M2 파일럿은 입력 결손이 아닌 대표 9명이라 필요 없다 | PLAN §3 M3 `WP2 9`, W2-16 |
| 로스터 구절 질의·`top_k` 변경 | panels 타깃의 Tier A 사람이 바뀐다(옛 흐름이 꺼진 기능 때문에 바뀌는 자리) | X2-10 의 1, W2-12 |
| `panel_question(unit=…)`·`build_delib_opts(unit=…)`·`units.panel_evidence` | 쟁점 패널(M3)의 몫이고 WP4 가 제 함수로 만든다 | W2 cuts 5, PLAN §3 M3 |
| `SpecContext.unit_lines`(겹친 cid 의 대조 후보) | M1 이 `canonical_text_for` 에 `humanize_refs` 를 넣어(R-40) 이름 불일치는 이미 풀렸다. 남는 것은 브리지 cid 충돌뿐인데 브리지는 0행이다 | 열린 물음 7 |
| `hwax-risk dev-seed-pair` CLI | M1 의 `tests/synth/inject_dev.py`(7db27db)가 같은 일을 안전하게 한다 | W2-11 |
| 창에서 상한을 다시 유도하는 장치(`caps_for_limits`·`limits_rev`·limits 재빌드)와 글자 수 상한 | 운영 창은 1,048,576 토큰이다. 단위 크기는 정확도·호출 시간(M0-b)으로 정하고, 창이 모자라면 러너가 `ctx_too_small` 로 멈춘다 | PLAN §4 '단위 맞춤', D-21·D-22, W2-06 |
| `HWAXRISK_REVIEW_FLOW` 손잡이 | 타깃마다 `flow` 를 고르고(D-24) 기능 스위치는 `HWAXRISK_REVIEW_ENABLED` 하나다 | P-07, X2-10 의 4 |

## 걸음

순서는 의존 순이다. 걸음마다 리포 시험 전체(`cd backend && .venv/bin/python -m pytest -q`)와 `ruff check app tests` 가 초록이어야 다음으로 간다(PLAN §9).
모든 걸음의 회귀 가드는 같다(D-24) — `tests/rr/test_legacy_flow.py` 전부와 `tests/rr/test_panel_ledger.py::test_three_panels_of_one_target_all_close_done` 이 그대로 초록이다.
v4 는 dev 리허설이 끝날 때까지 push 하지 않는다(C-2). 그 전에는 로컬 커밋으로만 쌓고 v4 DDL 을 고칠 수 있다.

### 걸음 1 — 단위 순수 핵심(WP2 2)

**목적.** 한 diff 타깃의 `diff_json` 세 층 항목을 전부 검토 단위로 나눈다(잘림 0·미배정 0). 단위마다 줄 구조·요약·목록 글·해시를 결정적으로 만든다.

**파일·함수(닻 확인).**
- 새 `app/units.py`(순수 함수만) — `collect_diff_items` · `walk_cids`(독립 순회) · `partition` · `build_diff_units` · `unit_lines` · `render_unit` · `digest_of` · `unit_hash` · `check_invariants`. 첫 줄은 한글 한 줄 주석.
- 기대는 M1 함수(이제 있다) — `render.split_trailing_refs`·`render.humanize_refs`·`render.sanitize_source_text(…, limit=0)`·`render.assert_clean`·`render.lint_text`, `brief.name_index`·`brief.event_order`·`brief.KIND_PRIORITY`(14종). 설계서 7.1 의 'WP1 이 준다' 가 이미 섰다.
- `brief.event_order` 는 이벤트 행 모양(`change_kind`·`rel`·`magnitude`·`design_relevant`·`cid`)을 읽는다. `diff_json` 의 의미 이벤트는 `magnitude` 가 dict 이고 파라메트릭 항목은 `before·after·delta·rel` 이라, 그 모양으로 옮기는 작은 어댑터를 `units.py` 에 둔다.
- `diff.py` 의 버킷(확인함) — `structural.node_changes`·`edge_changes`·`hierarchy_moves`(node_changes 와 같은 dict — 중복 제거)·`orphans_delta`(cid 없음)·`dyna`(dict 안의 `scope_changed` 리스트), `parametric.*`, `semantic.events`. `_rollup_delta` 는 변화 표지 없이 접두마다 행을 낸다(before≠after 로 가린다). `EXCLUDED_REASONS` 10종 밖의 `source_drift`·`capture_partial` 을 실제로 붙인다.
- `app/devseed.py::to_adapter_results` — 실제 어댑터처럼 part_of 엣지를 싣는다. 실제 어댑터 함수 `adapters.mcad._part_of_edges`(mcad.py:879, 호출 :526)를 불러 만든다(생산자 그대로). 지금 합성기는 `parent_canon_key` 만 주고 part_of 엣지를 내지 않아 W2-02 의 hier 경우를 시험이 못 본다. dyna scope 엣지(`b=None`)는 이미 낸다.

**계약.**
- `unit_id = 'u-' + sha1(builder_version|kind|정렬한 소유 참조)[:12]`(W2-18). 소유 참조가 0건인 단위는 만들지 않는다(W2-07).
- `kind ∈ bundle·boundary·global·excluded`. `snap_unit` 은 M4 다.
- 줄 구조 `lines[{ref, text, code, alias, layer, klass, direction, caveat, conf, derived_of, group}]` — 항목 하나에 한 줄이다(W2-17). 동형 묶음은 `group` 키로만 표시하고 접는 것은 요약 렌더에서만 한다.
- 줄 몸통은 `brief.e2_line` 과 같은 식 `split_trailing_refs(humanize_refs(text, name_index))` 다. 그래서 `risk_get_diff(part='lines')` 에서 옮긴 글과 글자까지 같다. `text` 는 «» 없음·참조 꼬리 없음·위생 통과(WP3a 가 감싼다 — C-14).
- 원천 문자열(부품명·재질 원문과 정규명·조립 키·치수 이름)은 요약·목록 글·제목 어디서나 `sanitize_source_text(…, limit=0)` 로 «» 안에 둔다(W2-10). 린터 적중은 빌드 실패가 아니다 — 그 칸을 다시 감싸 렌더하고, 그래도 걸리면 그 칸만 자리표시자로 두고 `flags.lint_fallback` 에 센다.
- 제외 처리표(caveat·none·모르는 사유 → caveat)는 `units.EXCLUDED_POLICY` 코드 상수로 둔다. `unit-routing` 자산은 만들지 않는다(소비처인 신호가 M4).
- 앵커는 `p:` 로 시작하고 그 스냅샷 노드 표에 있는 dn 만 센다. hier 엣지 항목은 자식 부품 원자에 싣고, 양 끝 dn 이 같은 항목·bridge 는 부품 원자, 앵커가 0개가 된 항목은 전역이다(W2-02).
- 전역 단위는 구획(명명 치수 → 롤업은 최상위 접두별 → scope → 모르는 버킷) 순으로 `target_lines` 마다 `global#n` 으로 가른다(W2-01). 단위 목록·총량 줄은 소유 줄이 아니라 `context` 에 둔다.
- 요약에는 순번을 박지 않는다 — `(소유 u-…)` 로 적고 `n/N` 은 읽을 때 붙인다(W2-13 c).
- `[부품]` 줄 상태에 `고아됨`·`고아 벗어남`(orphans_delta)을 적는다(W2-20).
- 크기는 줄 수로만 가른다 — `UnitCaps(target_lines=20, max_lines=40, small_lines=15, units_max=60)`, 설정에서만 읽는다. 글자 수 상한은 두지 않고 `summary_chars` 를 센다(D-21). 부품 원자 하나가 `max_lines` 를 넘으면 쪼개지 않고 `flags.split.rule='atom_oversize'` 로 남긴다(창이 아니라 정확도 상한이라 실패가 아니다 — D-22).
- 목록 글(`digest`)은 범위·건수 · 종류별 건수와 방향 · 재질 · 수치 범위 · 계면 전이 · 부품 이름 전부다. 고정 상한(설계서의 780자)은 없다. 이름 칸도 위생을 거친다(W2-19).
- `unit_hash = sha256(canonical_json([{ref, before, after, flag, excluded_reason, text}…]))[:16]`(값만 바뀌어도 달라진다).

**수용 기준.** U1 미배정 0(`walk_cids` 기준) · U2 소유 하나 · U3 상한(전역 분할 포함, 예외는 `atom_oversize` 표지뿐) · U4 린터 통과(fallback 포함) · U5 원천 문자열을 자르지 않는다 · U6 문맥 줄의 참조는 다른 단위가 소유한다. W2-01·02·07·10·17·18·19(이름)·20. 결정론 — 리스트·노드 행 순서를 섞어 세 번 돌려 `unit_id`·`unit_hash`·`summary_sha` 가 같다. 감소 변화 줄에 U+2212 와 '감소' 가 있고 요약 글에 모든 소유 참조가 나타난다.

**시험.** `tests/test_units_diff.py`. 입력은 전부 생산자 경로다 — `factories.make_diff_target(size=3·40·150, check=True)` 과 `devseed.random_script`(시드 다섯)의 `diff_json`, 그리고 `tests/fixtures/diff_pairs` 6쌍을 `compute_diff` 에 넣은 결과. 모르는 버킷·모르는 사유·cid 충돌은 생산자 결과를 복사해 그 칸만 바꾼다. 린터 낱말 재질(`강화유리`·`POKETONE`)·인젝션 이름·조립 이름 `안전_커버` 는 devseed 의 이름 인자로 만든다(`HAZARD_NAMES` 가 이미 `강화유리 WINDOW` 를 낸다). 독립 오라클 `all_cids`(재귀, 버킷 이름을 모른다)로 XU1·XU2 를, 자기 비교로 XU8 을, 감소 변화로 XU9 를 같이 본다 — C6 이 PLAN 의 M2 목록에 없어 여기에 접는다(열린 물음 5). syn150 의 단위 계산이 2초 안이다.

**의존.** 없음(M1 위). devseed 를 고친 뒤 `tests/rr/test_synth_manifest.py`·`test_inject_dev.py`·`test_legacy_flow.py` 가 그대로 초록인지 먼저 본다(part_of 엣지는 구조층 항목만 늘리고 의미 이벤트는 iface·contact 가족만 내므로 `synth_mismatch` 는 그대로일 것이다 — diff.py `_semantic` 의 `family == "iface"` 분기로 확인함).

**크기.** 16시간(코드 약 1,000줄·시험 약 800줄, 검토 라운드 포함).

### 걸음 2 — 동결 발췌(WP2 7, A 층만)

**목적.** 단위마다 그 부품의 양쪽 명세·끼인 계면 전부(변경 없는 것 포함, clearance 는 '근접' 으로 따로)·1홉 인접·해석 결과 행·규칙 적중을 IR 동결본에서 뽑아 근거 줄로 만든다. 네트워크를 쓰지 않는다.

**파일·함수.** `units.evidence_lines(unit, ir_view)`(순수)와 그 입력을 읽는 `units._ir_view(store, base_sid, target_sid)` — `rr_ir_nodes`·`rr_ir_edges`(두 스냅샷), `rr_snapshots.ir_json` 의 `results.part_risk`, `rr_states.rule_hits_json`, `rr_snapshots.degraded_json`(전부 DDL 에서 확인함). 별도 모듈 `unit_evidence.py` 는 만들지 않는다 — B 층·`ensure`·자격이 빠져 함수 둘이면 된다.

**계약.** `evidence[{ref, text}]` 의 `ref` 는 `p:`·`e:`·`rule:`·`sig:`·`tool:<캡처 call_id>` 뿐이다(새 스킴 없음 — C-8). 꾸러미는 빌드와 같은 트랜잭션에서 얼린다 — 동결 시각은 빌드 시각이고 다시 만들 일이 없다(IR·diff 는 불변). `evidence_status ∈ ok·failed(ir_absent — 폐기된 IR)·none(excluded 단위)`. 두 스냅샷의 `degraded_json` 코드를 `notes` 에 옮긴다(W2-20). 자르지 않는다 — 줄 순서만 설계서 3.8.3 의 우선순위를 따른다. `evidence_chars` 를 센다.

**수용 기준.** 변경 없는 계면까지 그 부품의 계면 전부가 실린다. IR 이 빈 타깃은 `failed`·`ir_absent` 다. 같은 입력이면 `evidence_sha` 가 같다. 원천 문자열 위생(W2-10 — `SUS304 OK` 같은 이름이 L16 에 걸리지 않는다). W2-03·W2-04 는 B 층이 없어 해당 없다.

**시험.** `tests/test_units_evidence.py` — syn40·syn150 의 생산자 IR. 오라클은 IR 표를 직접 세어 '그 부품의 계면 수 == 근거 줄의 계면 수' 를 본다.

**의존.** 걸음 1.

**크기.** 5시간.

### 걸음 3 — v4 블록의 단위 몫과 `flow` 열(WP2 3)

**목적.** 단위 표 둘과 타깃의 방식 열을 v4 에 넣고 반출·이양·폐기에 등록한다.

**파일·함수(닻 확인).** `app/risk_store.py`(`MIGRATIONS` 는 지금 `[(1, _DDL_V1), (2, _DDL_V2), (3, _DDL_V3)]`), `app/export.py::_SINCE_COLS`, `app/routes.py::TRANSFER_DERIVED`·`PURGE_BLANK_SQL`, `tests/test_store.py::PUSHED_DDL_SHA256` 와 `test_v3_is_the_three_panel_result_columns_and_a_v2_db_rises_to_it`(`[1, 2, 3]` 을 단언한다 — v4 와 함께 고친다), `tests/test_export_import.py`.

**계약 — v4(단위 몫).**

```sql
CREATE TABLE IF NOT EXISTS rr_unit_builds (            -- 빌드 머리 행. 한 번 쓰고 고치지 않는다(W2-13)
  target_key TEXT NOT NULL, rev INTEGER NOT NULL, owner_sub TEXT NOT NULL,
  status TEXT NOT NULL,                                -- ok | empty | oversize | failed (CHECK 없음 — C-3)
  builder_version TEXT NOT NULL DEFAULT '', input_hash TEXT NOT NULL DEFAULT '', source_hash TEXT NOT NULL DEFAULT '',
  caps_json TEXT NOT NULL DEFAULT '{}', blocked_by TEXT,   -- 'G2' | 'capture_partial' | NULL
  stats_json TEXT NOT NULL DEFAULT '{}', invariants_json TEXT NOT NULL DEFAULT '{}',
  unit_ids_json TEXT NOT NULL DEFAULT '[]',            -- 이 rev 의 [unit_id, seq] — 활성 단위와 순번은 여기서 읽는다
  reason TEXT, error TEXT, built_by TEXT, built_at INTEGER NOT NULL,
  PRIMARY KEY(target_key, rev));
CREATE TABLE IF NOT EXISTS rr_units (                  -- 검토 단위. 내용 주소라 한 번 쓰고 고치지 않는다
  target_key TEXT NOT NULL, unit_id TEXT NOT NULL, owner_sub TEXT NOT NULL, project_id TEXT NOT NULL,
  rev_first INTEGER NOT NULL, kind TEXT NOT NULL, reviewable INTEGER NOT NULL DEFAULT 1,
  scope_key TEXT, title TEXT NOT NULL DEFAULT '', digest TEXT NOT NULL DEFAULT '',
  unit_hash TEXT NOT NULL, cids_json TEXT NOT NULL, n_changes INTEGER NOT NULL DEFAULT 0, n_parts INTEGER NOT NULL DEFAULT 0,
  context_json TEXT, flags_json TEXT,
  lines_gz BLOB, summary_gz BLOB, summary_sha TEXT, summary_chars INTEGER,
  evidence_gz BLOB, evidence_sha TEXT, evidence_chars INTEGER, evidence_status TEXT, evidence_json TEXT,
  builder_version TEXT NOT NULL, created_at INTEGER NOT NULL,
  PRIMARY KEY(target_key, unit_id));
ALTER TABLE rr_targets ADD COLUMN flow TEXT NOT NULL DEFAULT 'panels';   -- panels | cells (C-5). 옛 행은 panels 로 읽힌다
```

- 설계서에서 뺀 열 — `active`·부분 유니크 인덱스·`rev_last`·`seq`(W2-13), `split_from`·`semantic_blocked`(빌드 행에서 유도), `signature_json`·`sig_hash`·`signals_*`(신호 M4), `evidence_frozen_at`(= `created_at`), `limits_rev`(D-22).
- 활성 빌드는 '그 타깃에서 `status ∈ (ok, empty, oversize)` 인 가장 큰 rev' 로 읽는다(파생).
- `rr_roster.input_gaps_json` 은 v4 에 넣지 않는다 — M2 에 읽는 곳이 없다(X3-03 의 v4 목록과 다르다 — 열린 물음 9). M3 v5 로 간다.
- v4 는 WP3b 1 의 표와 **한 블록**이다(C-2). 먼저 들어가는 쪽이 `_DDL_V4_SQL` 을 만들고 뒤는 같은 블록에 덧붙인다. push 전까지 블록을 고칠 때마다 같은 커밋에서 `PUSHED_DDL_SHA256[4]` 를 고친다.
- 등록 — `_SINCE_COLS`: `rr_unit_builds: ('built_at',)`·`rr_units: ('created_at',)`. `TRANSFER_DERIVED`: 두 표를 `target_key IN (SELECT target_key FROM rr_targets WHERE project_id = ?)` 로. `PURGE_BLANK_SQL`: `rr_units` 의 `title`·`digest`(빈 글)·`scope_key`·`context_json`·`flags_json`·`lines_gz`·`summary_gz`·`evidence_gz`·`evidence_json`(NULL), `rr_unit_builds.error`(NULL)(W2-22).

**수용 기준.** 빈 DB·v2(얼린 옛 DB)·v3 DB 에서 v4 이행이 멱등이고 `pre-migrate-v3-*` 사본이 하나 생긴다. 반출 → 빈 DB 들여오기 왕복에서 BLOB 이 같다. 옛 rev 가 든 DB 에 새 rev 를 들여와도 활성 빌드가 새 rev 다(W2-13 e). 폐기 뒤 `rr_units`·`rr_unit_builds` 의 어느 열에도 심어 둔 부품명·재질명이 없다(W2-22). 표 규약 시험(owner_sub·PK·CHECK 없음)이 통과한다.

**시험.** `tests/test_store.py`·`tests/test_export_import.py`·`tests/rr/test_legacy_flow.py`(v2 → v4). 행은 걸음 5 의 `units.persist` 로 만든다(손 INSERT 금지 — C4 출처 래칫).

**의존.** 걸음 1(행을 만들 함수). WP3b 1 과 블록 합의.

**크기.** 4시간.

### 걸음 4 — WP5a R5 최소분(손잡이·기동 검사)

**목적.** 새 흐름의 문(스위치)과 손잡이를 한 자리에서 읽고, 박스마다 다르게 켤 길을 두고, 뒤집힌 시간 한도로는 기동하지 않게 한다.

**파일·함수(닻 확인).** `app/config.py`(`Settings`·`load_settings`·`load_secrets`·`KNOB_HOME`), `app/main.py`(`check_credential_chain` 옆에 `check_review_chain`, `_lifespan` 에서 부른다), `app/routes.py`(`GET /api/meta/runtime` — 관리자), `.portal/manifest.yaml` 설명, `tests/test_boot.py`·`tests/test_manifest.py`·`tests/test_config_datadir.py`. HEAXHub `integrations/hwax-risk/.portal/manifest.yaml` 사본은 같은 날 맞춘다(H1 — 그 리포에서 diff 가 비는지만 본다).

**계약.**

| 손잡이 | 기본 | 읽는 곳 |
|---|---|---|
| `HWAXRISK_REVIEW_ENABLED` | 0 | 걸음 5·6 의 `flow=cells`(꺼져 있으면 409 `review_disabled`), WP3b 의 검토 잡 생성 |
| `HWAXRISK_UNIT_TARGET_LINES`·`_MAX_LINES`·`HWAXRISK_UNITS_SMALL_LINES`·`HWAXRISK_UNITS_MAX` | 20·40·15·60 | 걸음 1(`UnitCaps`) |
| `HWAXRISK_REVIEW_CONCURRENCY`·`_CALL_TIMEOUT_S`·`_READ_TIMEOUT_S`·`_MAX_CHARGED`·`_MAX_TRIES`·`_ON_CRED_CHANGE`·`_CONSENT_CALLS`·`_MAX_CALLS`·`_EST_CALL_S` | 4·14,400·1,800·2·20·`hold`·1,500·30,000·300 | WP3b 8·11(러너·잡 생성). 값은 WP5a 3.8.1 에서 C-24(동시 4)와 PLAN §7(자격 만료는 멈춘다)로 고친 것 |

- 뺀 손잡이 — `HWAXRISK_REVIEW_ENGINE`(D-15), `HWAXRISK_REVIEW_FLOW`(P-07), `HWAXRISK_PACK_RETAIN_DAYS`·`HWAXRISK_PANEL_AUTORESUME_MAX_S`(WP5a cuts), `HWAXRISK_AIDH_CALL_TIMEOUT_S`(C-10 — AIDataHub REST 를 쓰지 않는다), `HWAXRISK_REVIEW_RUNS_PARALLEL`(1 고정), 밤 창 전부.
- `$DATA_DIR/knobs.env` — `load_secrets` 와 같은 파서로 읽는다. 순서는 환경변수 > `knobs.env` > 코드 기본값이다. 추적 파일이 아니고 재배포에 남고 박스마다 다르다(P-07 ②). cae00 파일럿은 이 파일에 `HWAXRISK_REVIEW_ENABLED=1` 한 줄로 켠다.
- `GET /api/meta/runtime` — `{knobs: {<이름>: {value, source: env|knobs.env|default}}, runner_lock, schema_version, app_version}`. 비밀은 싣지 않는다.
- `check_review_chain(settings)` — `READ_TIMEOUT_S ≤ CALL_TIMEOUT_S`(0 은 끔), 검토 자격 여유(`CALL_TIMEOUT_S` + 엔진 대기 예산 + 600) < `routes.PAT_MIN_REMAINING_S`(86,400). 뒤집히면 `check_credential_chain` 처럼 RuntimeError 로 기동을 막고 고칠 손잡이와 `KNOB_HOME` 을 말한다.
- 매니페스트 설명 — 도구 수(M2 끝 29종)·새 흐름 한 줄·`knobs.env`. `launch.env` 는 그대로 둔다.

**수용 기준.** 손잡이마다 기본값·환경 덮어쓰기·`knobs.env` 덮어쓰기와 출처 표기. 뒤집힌 값에서 기동 실패. `test_manifest.py` 통과. P-07(스위치 하나)·P-10(사전 점검은 싼 것만 — 이 걸음에서는 만들지 않고 WP3b 11 의 잡 생성에 둔다).

**시험.** `tests/test_boot.py`(기동 검사), `tests/test_config_datadir.py`(knobs.env 를 임시 데이터 디렉터리에 쓴 뒤 `load_settings`), `tests/test_manifest.py`.

**의존.** 없음. 걸음 5·6 과 WP3b 8 이 이것을 읽는다.

**크기.** 5시간.

### 걸음 5 — 저장·조회·REST·MCP 1·타깃 생성 훅(WP2 4, 흐름 결정)

**목적.** 빌드 결과를 원장에 얹고, WP3b 가 읽을 함수를 내고, `cells` 로 연 타깃에 단위를 세우되 안 서면 옛 흐름으로 연다.

**파일·함수(닻 확인).** `app/units.py`(저장·조회), `app/routes.py::create_target`(지금 순서 — 검증 → G6 → 409 → 로스터 조회(트랜잭션 밖) → `with store.tx():` 타깃 INSERT·`planner.freeze_roster`·`_supersede_previous_target`), `routes.TargetBody`(kind·ref_id·consent·agents), `routes.coverage_payload`, `GET /targets` 목록, `app/mcp_server.py`(`_scoped`·`routes.mcp_scope_owner`), `app/brief.py::begin_suspect_queue`·`_on_suspect`(인젝션 적중 → `rr_curation_queue`).

**계약 — 함수(W2-14 의 이름을 여기서 못 박는다).**
- `units.compute(store, kind, ref_id, *, owner_sub, caps) -> dict` — 읽기와 계산만 한다(타깃 행이 생기기 전에 부른다). 예외는 `status='failed'` 로 접는다. `kind='snap'` 이면 `failed`·`snap_not_supported`. `suspects[]` 를 함께 돌려준다(W2-19).
- `units.persist(store, target_key, owner_sub, built, *, built_by, reason=None) -> dict` — 한 트랜잭션. 빌드 행 INSERT, 단위 행은 `INSERT OR IGNORE`(내용 주소), suspects 를 큐에 적재.
- `units.build_units(store, target_key, *, built_by, reason=None) -> dict` — 활성 빌드와 `input_hash` 가 같으면 쓰지 않는다. 그 타깃에 검토 잡(WP3b 의 `rr_jobs.mode='reviews'`)이 하나라도 있으면 입력이 달라지는 재빌드는 409 `units_in_use` 다(M2 에는 `force` 길을 두지 않는다 — 열린 물음 10).
- `units.manifest(store, target_key, *, offset=0, limit=None)` · `units.get_unit(store, target_key, unit_id, part)` (`part ∈ summary·lines·evidence`) · `units.load_units(store, target_key, *, reviewable_only=True)` · `units.manifest_items(store, target_key) -> [{unit_id, kind, title, text}]`(WP3b 의 `units.packets` 를 이 이름으로 맞춘다) · `units.review_payload(store, target_key, unit_id, agent_key)`(C-14 모양 `{unit_id, kind, title, summary, lines[{ref,text}], evidence[{ref,text}], notes, missing[]}` + `unit_hash`·`summary_sha`·`evidence_sha`·`evidence_status`·`input_gaps`) · `units.unit_refs(store, target_key, unit_id) -> set[str]`(소유 줄 + 근거 줄의 참조. 문맥 줄은 빼서 다른 단위 참조가 Q8 에서 떨어지게 한다) · `units.ref_index(store, target_key)`.
- `missing[]` 는 타깃 수준 결측(스냅샷 `missing_json` — ecad·mcad·dyna)과 빌드의 `blocked_by` 다. `input_gaps` 는 걸음 8 의 계산값이다.

**계약 — 타깃 생성 훅(PLAN §4 '흐름 결정', W2-05·W2-24).**
1. `TargetBody.flow: Literal['panels','cells'] = 'panels'`. `cells` 인데 `REVIEW_ENABLED=0` 이면 409 `review_disabled`.
2. `cells` 면 로스터 조회 앞에서 `units.compute` 를 부른다(ms 단위라 540초 로스터 기한을 먹지 않는다 — X2-10 의 2 는 시험의 시간 단언으로 지킨다).
3. 빌드가 `ok·oversize` 가 아니면 `flow='panels'` 로 열고 응답에 `flow_fallback: {from: 'cells', reason: <status|error>}` 를 싣는다.
4. 타깃·로스터·승계 트랜잭션은 지금 그대로다(로스터 동결 규칙도 그대로 — 보류 포함).
5. `cells` 로 열렸으면 그 트랜잭션이 닫힌 **뒤** 제 트랜잭션에서 `units.persist` 를 한다. 던지면 `failed` 빌드 행 + `flow='panels'`(아직 아무것도 안 돌았다) + `flow_fallback.reason='persist_error'` 다(W2-24).
6. `panels` 타깃은 생성 때 단위를 만들지 않는다. 재려면 `POST /targets/{key}/units` 를 따로 부른다.

**계약 — REST(PLAN §4 'REST 한 벌' 과 겹치지 않는 자원이다).**

| 경로 | 권한 | 응답 키 |
|---|---|---|
| `POST /api/targets` | 종전 | 종전 + `flow`·`flow_fallback?`·`units?: {rev, status, blocked_by, n, reviewable_n, lines_total, by_kind, excluded_by_reason}` |
| `POST /api/targets/{key}/units` 본문 `{reason?}` | editor | `{rev, status, changed, blocked_by, stats, invariants}` |
| `GET /api/targets/{key}/units?offset=&limit=` | 멤버 | `{target_key, flow, rev, status, blocked_by, stats, invariants, total, offset, returned, next_offset?, units: [{unit_id, seq, kind, reviewable, scope_key, title, digest, n_changes, n_parts, summary_chars, evidence_chars, evidence_status, unit_hash, links}]}` |
| `GET /api/targets/{key}/units/{unit_id}?part=summary\|lines\|evidence` | 멤버 | `{unit_id, part, rev_first, seq, total, text \| lines \| evidence}` |
| `GET /api/targets/{key}/coverage` | 종전 | 종전 + `flow`·`units: {rev, status, reviewable_n}`(진행 `review` 칸은 WP3b 11) |
| `GET /api/targets` | 종전 | 행마다 `flow` |

옛 타깃(단위 없음)에는 500 이 아니라 `{status: 'none'}` 을 답한다(WP5b 3.9.1 ④).

**계약 — MCP.** `risk_get_units(target_key, unit_id=None, part='manifest', offset=0)` — 읽기, `_scoped('target', …)`, 범위 밖은 `not_visible`. 목록과 `lines` 는 `offset`·`next_offset` 으로 나눠 준다 — Claude Code 의 MCP 결과 상한(25,000토큰, d074004)을 넘기지 않되 자르지 않는다(823c4ab 와 같은 방식). 도구 27번째, `TOOL_NAMES` 맨 뒤에 붙는다.

**수용 기준.** 같은 입력 재빌드가 no-op 이다. 상한 손잡이를 바꾸면 새 rev 가 서고 겹치는 `unit_id` 행은 그대로다. 단위 계산 예외·`persist` 예외에도 `POST /targets` 가 200 이고 타깃·로스터가 남으며 `flow='panels'` 다(W2-05·W2-24). `panels` 타깃 생성은 `units.compute` 를 한 번도 부르지 않는다. 빌드 `empty`(자기 비교)는 `cells` 로 열리지 않는다(XU8). 인젝션 이름이 큐에 오른다(W2-19). MCP 범위 밖 `not_visible`. `manifest_items` 가 검토 대상 단위 전부를 덮는다.

**시험.** `tests/test_units_store.py`(새), `tests/test_p6_routes.py`, `tests/test_mcp_tools.py`(`TOOL_NAMES` 에 `risk_get_units`, `CALLS` 에 `("risk_get_units", {"target_key": "snap:s1"}, "not_visible")`), `tests/rr/test_legacy_flow.py::test_mcp_tools_keep_their_names_and_order`(새 도구가 뒤에 붙는다). 타깃은 `factories.make_target(…, flow=…)`(실제 `routes.create_target` — 공장에 `flow` 인자만 더한다)과 `make_diff_target` 으로 만든다. `persist` 실패는 `monkeypatch` 로 함수를 던지게 해서 만든다(입력을 손으로 쓰지 않는다).

**의존.** 걸음 1·2·3·4.

**크기.** 10시간.

### 걸음 6 — 방식 고르기(D-24) — 바꾸기·얹기·문지기·길잡이

**목적.** 아직 돌지 않은 대상은 방식을 바꾸고, 패널을 돌린 대상에는 카드 대조를 얹으며, `cells` 대상에서 옛 Tier 잡과 L2 보충 회차를 막고, Claude 길잡이가 두 방식을 나란히 보인다.

**파일·함수(닻 확인).** `app/routes.py`(새 `POST /targets/{key}/flow`, `brief_payload(issue_token=True)`·`brief_by_token`), `app/runner.py::create_job`(사용자 잡과 `_finish_job` 의 C3 자동 후속 Tier C 가 둘 다 이 함수를 지난다 — 문지기를 라우트가 아니라 여기에 둔다), `app/entry.py::open_target`·`next_step`(6단계 '심사 대상' 분기, `_CONSENT_WHY`), `app/mcp_server.py::risk_open_target`.

**계약.**
- `POST /api/targets/{key}/flow` 본문 `{to: 'panels'|'cells', reason}` — editor(잡을 세울 수 있는 사람과 같다). 응답 `{target_key, flow, changed, units?}`. 감사 `rr_audit(scope='target', action='target.flow', channel=web|rest|mcp)`(scope `target` 은 CHECK 안에 있다).
- `panels → cells` — 살아 있는 잡(어느 mode 든)이 없고, `REVIEW_ENABLED=1` 이고, 단위 빌드가 `ok·oversize` 일 때만(없으면 그 자리에서 `build_units`). 이미 돈 패널·의견·등록부는 건드리지 않는다(D-24 '비교', 권고값 '이미 패널이 돈 옛 타깃에 검토를 얹는 것은 허용'). 막히면 409 `flow_locked`(`job_live`)·`review_disabled`·`units_unbuildable`(빌드 상태와 까닭).
- `cells → panels` — 그 타깃에 검토 잡(`rr_jobs.mode <> 'panels'`)이 한 번도 없을 때만. 아니면 409 `flow_locked`(`review_ran`).
- 문지기 — `runner.create_job` 은 `flow='cells'` 타깃의 Tier A·B·C 를 422 `flow_mismatch` 로 거절한다(쟁점 패널 `tier='I'` 는 M3 러너가 만들므로 거절 대상이 아니다). `brief_payload(issue_token=True)`·`brief_by_token` 도 `cells` 타깃에 `flow_mismatch` 다(L2 `hwax-risk-review.js` 는 panels 대상에서만 돈다 — D-24). 브리프 미리보기는 그대로 둔다.
- `risk_open_target(kind, ref_id, consent=False, flow=None, reason=None)` — 새 대상이면 `flow`(없으면 panels)로 열고, 이미 연 내 대상인데 `flow` 가 다르면 같은 바꾸기 함수를 지난다(쓰기 — `require_delegate`, 감사 channel `mcp`). 새 도구를 만들지 않는다.
- `risk_next_step` — 대상을 열기 전 단계(`where='target'`)에 `risk_open_target` 두 걸음(`flow='panels'` — 영역을 섞은 패널 3라운드, `flow='cells'` — 전문가별 카드 대조)을 나란히 준다. 기능이 꺼진 박스에서는 cells 걸음 대신 `notes` 에 '이 박스에서는 꺼져 있다 — knobs.env' 를 적는다. 열린 `cells` 대상의 빌드가 안 서 있으면 `blocked` 에 `units_unbuildable` 을 싣는다. `cells` 대상의 잡 걸음(`risk_start_job` 의 범위 인자)은 WP3b 11 이 이 분기 뒤에 붙인다.
- `GET /targets/{key}/coverage`·`risk_get_coverage` 에 `flow`(걸음 5).

**수용 기준.** 바꾸기 규칙 표 전부(돌기 전 양방향 · 패널 뒤 얹기 · 검토 뒤 되돌림 거절 · 살아 있는 잡 거절 · 꺼진 스위치 거절)와 감사 행. 사용자 Tier 잡과 C3 자동 후속이 `cells` 대상에서 거절된다. `cells` 대상의 브리프 토큰 발급이 거절되고 panels 대상은 종전과 바이트가 같다. 길잡이가 두 걸음을 보인다. MCP 쓰기는 위임 신원만(`delegation_required`). D-24 회귀 가드.

**시험.** `tests/test_p6_routes.py`·`tests/test_mcp_entry.py`·`tests/test_runner.py`(자동 후속은 `_finish_job` 을 실제로 돌린다)·`tests/rr/test_panel_ledger.py`. 대상은 `make_diff_target` 과 `make_target(flow=…)` 으로 만들고 패널은 기존 가짜 엔진으로 돌린 뒤 얹는다. 검토 잡 행은 WP3b 의 잡 생성 함수가 들어온 뒤 그것으로 만든다(그 전까지 `review_ran` 분기 시험은 WP3b 1 의 커밋에서 켠다).

**의존.** 걸음 4·5. `review_ran` 판정은 WP3b 1 의 `rr_jobs.mode`(v4).

**크기.** 6시간.

### 걸음 7 — `structural.dyna.scope_changed` 인용 조회(WP2 6 의 a)

**목적.** 좌석·판정이 `contact.scope_changed` 원자료 cid 를 인용하면 지금은 dangling 이다. 그것을 푼다.

**파일·함수(닻 확인).** `app/narrative.py::SpecContext.diff_item` — `structural.values()` 가운데 리스트인 버킷만 훑어 `dyna`(dict 안의 `scope_changed` 리스트)를 못 본다(c3f46ba 에서 그대로).

**계약.** 구조층에서 dict 인 값은 그 안의 리스트까지 한 단계 더 훑는다. 단위가 없는 타깃의 동작은 바뀌지 않는다.

**수용 기준.** 기존 인용 시험 전부 불변. scope_changed cid 가 풀린다(설계서 2.2·5 걸음 6).

**시험.** `tests/test_persist_panel.py` — syn40(대본에 `contact.scope_changed` 가 있다)의 `diff_json` 에서 그 cid 를 꺼내 패널 결과(`factories.portal_panel_body`)에 인용시킨다.

**의존.** 없음.

**크기.** 1.5시간.

### 걸음 8 — 검토 순서 함수(WP2 9 가운데 `review_order` 만)

**목적.** WP3b 가 전문가를 도는 순서를 준다. Tier 는 범위가 아니라 순서다.

**파일·함수(닻 확인).** `app/planner.py` — `TIERS`·`tier_rank_cap`(A=1·B=ceil(0.3·크기)·C=전원)·`_domain_sizes`·`_roster_rows`. `routes._ecad_absent_for_target`(타깃의 ECAD 부재). `rr_roster.ecad_dependent` 열.

**계약.** `planner.review_order(store, target_key) -> [{order, agent_key, domain, rank_in_domain, tier, deferred, input_gaps}]`. 정렬 키는 (tier A→B→C, `rank_in_domain`, domain, agent_key)다. `input_gaps` 는 저장하지 않고 계산한다 — `ecad_dependent=1` 이고 타깃이 ECAD 부재면 `['ecad_absent']`. `deferred` 는 그 좌석의 `rr_coverage.status` 다(M2 는 로스터 동결 규칙을 바꾸지 않는다). M2 에 입력 결손 호출이 없으므로 WP3b 의 격자는 `input_gaps` 가 빈 전문가만 받는다(계약 — WP3b 6).

**수용 기준.** 설계서 5.1 의 `PLAN_SIZES`(합 359)에서 A 15 · B 누적 114 · 전체 359 경계, 두 번 불러 같다.

**시험.** `tests/test_planner.py` — 로스터는 `factories.make_target(agents=…)`(실제 `freeze_roster`)로 만든다.

**의존.** 없음.

**크기.** 1.5시간.

### 걸음 9 — change_kind 두 종(R-32, 조건부 — 열린 물음 4)

**목적.** 생산자가 내는 `contact_type`·`parameter` 를 정규화가 `none` 으로 바꾸지 않게 한다. M2 의 finding 승격(WP3b 9)이 그 줄에서 finding 을 만들면 지금은 조용히 `none` 이 된다.

**파일(닻 확인).** `app/narrative.py::_CHANGE_KINDS`(12종, 보정은 1171행 부근 `if change_kind not in _CHANGE_KINDS`), `app/schemas/risk_spec.v1.json` 의 `change_kind.enum`(12종), `app/assets/taxonomy.v1.json` 의 `axes.change_kind`(12종, `taxonomy_version` 1.0). 대조 — `schemas/rr_diff.v1.json`·`brief.KIND_PRIORITY` 는 이미 14종이다. 에이전트 서버·JS 파이프라인에는 열거가 없다(grep — 세 리포 같은 날 변경이 아니다).

**계약.** 네 곳이 같은 14종이다. 택소노미 판 번호는 열린 물음 4 를 따른다.

**수용 기준.** '자산 축 == `_CHANGE_KINDS` == risk_spec enum ⊇ rr_diff enum' 시험. `taxonomy_version` 을 읽는 시험·파리티(`test_parity.py`)가 통과한다.

**시험.** syn40 의 `contact.friction_changed` 이벤트를 인용한 finding 을 실제 정규화에 넣어 `change_kind='parameter'` 가 남는다.

**의존.** 없음.

**크기.** 2시간.

### 걸음 10 — 실측 탐침과 실주행 절차(WP2 11)

**목적.** M0-c(실제 `diff_json` 에서 단위 수·줄 분포)와 dev 리허설·cae00 파일럿이 같은 숫자를 같은 방법으로 낸다.

**파일.** `backend/tests/synth/units_probe.py`(새) — 데이터 디렉터리의 DB 를 SQLite `mode=ro` 로 열고(이행·러너 잠금 없음, 스키마가 다르면 멈춤 — `inject_dev.py` 와 같은 규율), 고른 diff 마다 `units.compute` 를 돌려 JSON 한 줄을 찍는다 — 항목(층·klass)·`lower_only_n`·`tol_unknown` 수·단위(kind)·단위당 줄 p50·p95·max·글자·근거 글자·빌드 ms·불변식. cae00 은 SIF 로만 돌므로 같은 숫자를 `POST /api/targets/{key}/units` → `GET /units` 의 `stats` 로 낸다(LLM 0, 단위 표에만 쓴다). 절차서 `HWAXPortal/docs/risk-review-redesign/server-setup-m2.md` — `knobs.env` 한 줄, M0-d 타깃에 `POST /units`, 얹기(`POST /flow {to:'cells'}` 또는 `risk_open_target(flow='cells')`), 확인할 출력 문구(줄 번호 대신 — PLAN §9).

**수용 기준.** 탐침이 쓰기 0(시험이 실행 전후 DB 파일 해시를 견준다). 탐침 숫자와 REST `stats` 가 같다. 절차서의 명령을 dev 에서 하나씩 돌려 출력과 맞춘다.

**시험.** `tests/rr/test_units_probe.py` — syn150 을 임시 DB 에 생산자 경로로 넣고 탐침을 돌린다.

**의존.** 걸음 5.

**크기.** 3시간.

### 걸음 11 — 게이트웨이 대조(WP5b C15)

**목적.** 새 도구(`risk_get_units` 와 WP3b 의 둘)가 배포본 게이트웨이에 실제로 뜨는지 소스가 아니라 게이트웨이에 묻는다(리포 규칙, '`unknown tool: intake`' 전례).

**파일.** `backend/scripts/rr_gateway_check.py`(읽기 전용) — 기대 목록은 `app/mcp_server.py` 의 `@mcp.tool` 함수 이름을 AST 로 뽑는다(venv 없이 돈다). `HWAX_GATEWAY_PAT` 이 환경에 있으면 MCP `tools/list`, 없으면 `GET /tools-map` 의 `heax-hwax_risk` 백엔드 이름(접두는 꼬리 일치). 새 읽기 도구 하나를 없는 키로 불러 `not_visible`(살아 있음)과 `unknown tool`(목록에만 있음)을 가른다. 종료 0(이상 없음)·2(판정 불가)·3(배포본이 낡았다 — SIF 재빌드와 인스턴스 교체). PAT 는 인자로 받지 않는다.

**계약.** update-all 에 배선하지 않는다(problems.md WP5b cuts 'rr_gateway_check.py(C15)와 update-all 배선(D9)' 가운데 배선만 뺀다 — PLAN 이 C15 를 M2 에 넣었으므로 스크립트는 둔다). 절차서(걸음 10)가 배포 뒤 한 번 부른다.

**수용 기준.** 가짜 `/tools-map`·가짜 MCP 로 0·2·3 세 종료 코드. 실 게이트웨이를 부르지 않는다(conftest 의 루프백 밖·서비스 포트 차단 — bea34fb).

**시험.** `tests/rr/test_gateway_check.py` — `httpx.MockTransport` 또는 빈 포트의 작은 ASGI 앱. 기대 목록은 실제 `mcp_server.py` 를 읽는다.

**의존.** 걸음 5(도구 27종). M2 끝에는 WP3b 11 의 둘까지 29종을 본다.

**크기.** 3시간.

### WP5b 시험 다섯 — 주인과 증명할 것

| 시험 | 주인 | 증명할 것 | WP2 가 내는 것 |
|---|---|---|---|
| C5 합성 카드·심은 정답(`tests/synth/cards.py`) | WP3a(카드 모양)·WP3b(앱 시험) | 함정 11종(`violated_rule`·`irrelevant_rule`·`number_trap`·`newline_table`·`injection`·`url_fence`·`canary`·`zero_cards`·`max_cards`·`shared_card`·`lookalike_id`)이 각각 켜진다. `oracle(card_id, unit_events)` 가 대본과 같은 pos·neg 를 낸다 | 오라클이 읽는 `unit_events` 는 devseed 대본 → 실제 diff → `units.review_payload` 의 `lines` 다(손으로 쓴 단위 금지). `planted_real.json` 의 세 경우도 devseed 연산으로 적는다 |
| C7 공유 예제·세 리포 계약·파리티 벡터 | WP3a(예제·`validate_request`)·WP3b(`collect_review_stream`)·포털(WP3a P1 중계) | 요청 방향 — 앱이 syn40·syn150 에서 조립한 `run` 본문 전부가 에이전트 서버 검증기를 422 없이 지난다(서브프로세스, 형제가 곁에 있는데 import 가 실패하면 skip 이 아니라 fail — P-22). 결과 예제의 잎 필드를 바꾸면 원장 행이 달라진다. 신원 칸 넷 덮어쓰기. QP1·QP2 파리티 | 요청 본문의 `unit` 은 `units.review_payload` 의 출력이다. 줄 0개 단위가 없고(`empty_unit`), 1백만 토큰 창의 `limits` 로 `OverBudget` 이 0 이다(XU10 을 이 자리에서 본다 — 16K 창 단언은 D-22 로 뺀다) |
| C8 가짜 LLM 한 벌·끝까지 닫히는 모양 | WP3a(`tests/fakes/llm.py`)·WP3b(`tests/rr/test_review_outcomes.py`) | 거동 16종의 기대(한 줄 깨짐은 그 행만 빠지고 `missing` 이면 `reviewed` 가 아니다 등). `missing` 검사를 지우면 거동 2 가 붉다(사본에서) | 프롬프트 쪽 단언 '변경 줄 별칭 수 == `len(unit.lines) + len(unit.evidence)`'(조용한 절단 없음)의 입력 단위 |
| C9 셀 상태기계·판정 집합·인용 | WP3b | L1~L9(L6 은 같은 DB 를 연 `RiskStore` 둘 — P-17)·V1~V5·Q1~Q8 | Q8 '변경 쪽 참조는 그 단위의 줄에 있어야 한다' 의 기준 `units.unit_refs`. 다른 단위가 소유한 참조(문맥 줄 포함)는 떨어진다 |
| C15 게이트웨이 대조 | WP5a(운영) — 리스크 리포 스크립트 | 걸음 11 | `risk_get_units` 를 탐침 도구로 쓴다 |

WP2 몫(C7 요청 방향의 단위 공장과 C9 Q8 의 `unit_refs` 시험)은 약 2시간이고 WP3b 걸음과 같은 커밋 묶음으로 들어간다(WP5b 4절 'C6 이후는 구현과 같은 커밋 묶음').

### 합계

| 걸음 | 시간 |
|---|---|
| 1 단위 순수 핵심 | 16 |
| 2 동결 발췌 | 5 |
| 3 v4 단위 몫 | 4 |
| 4 R5 최소분 | 5 |
| 5 저장·조회·REST·MCP·훅 | 10 |
| 6 방식 고르기 | 6 |
| 7 scope_changed | 1.5 |
| 8 review_order | 1.5 |
| 9 change_kind 두 종 | 2 |
| 10 탐침·절차 | 3 |
| 11 게이트웨이 대조 | 3 |
| C7·C9 의 WP2 몫 | 2 |
| **합** | **59** |

PLAN §8 의 M2 어림은 110시간(WP3a·WP3b·품질 모듈·리허설·파일럿 포함)이다. 이 꾸러미만 그 절반을 넘으므로 M2 전체 어림이 모자랄 공산이 크다. M1 은 70시간 어림에 여러 리포의 커밋 약 130개(HWAXRisk 만 `7248651..c3f46ba` 72개)가 들었다.

## M1 이후 달라진 것

| 설계서의 가정(7248651) | 지금(c3f46ba) | 할 일 |
|---|---|---|
| 스키마 v3 는 재설계 표 전부를 담는 통합 블록이다(WP5a 3.2.3, 설계서 3.2 '그 블록이 나가기 전이면 거기에') | v3 는 `rr_panels` 세 열뿐이고 나갔다. `migrate.lock`·출발 버전 사본·사본 정리(X2-01·X2-02)가 들어 있다 | 단위 표는 v4 다. v4 는 WP3b 와 한 블록이고 dev 리허설 전에는 push 하지 않는다. `test_v3_is_…` 의 `[1, 2, 3]` 단언과 `PUSHED_DDL_SHA256` 을 v4 커밋에서 고친다 |
| 공용 표기 함수(`split_trailing_refs`·`humanize_refs`·`norm_quote`·`name_index`·`event_order`)는 WP1 이 줄 것이고 없으면 WP2 가 넣는다 | 다 있다. `event_order` 는 종류 돌림(`KIND_PRIORITY` 14종)·크기 절댓값·감소 먼저 | 그대로 쓴다. `diff_json` 항목을 이벤트 행 모양으로 옮기는 어댑터만 둔다 |
| 계면 항목의 정규 표기가 `p:해시↔p:해시` 라 단위 줄의 실명 인용이 떨어진다 → `SpecContext.unit_lines` 필요(3.6.4) | `canonical_text_for` 가 `humanize_refs` 로 이름을 바꿔 대조한다(R-40) | `unit_lines` 는 M3 로 미룬다(열린 물음 7). `scope_changed` 조회만 고친다(걸음 7 — 아직 dangling) |
| 브리프 변경 칸이 4,050자라 좌석에 6~12건만 간다 | 웹 브리프가 엔진 창에서 유도한 예산으로 변경 목록을 싣고, 생략은 꼬리에 센다(837cca0·D-25) | 새 흐름의 값은 '잘림을 피한다' 가 아니라 '단위별로 전문가가 카드마다 판정한다' 다. 단위 요약도 자르지 않는다 |
| 단위 본문 상한 B 는 128K 창에서 12,126자, 넘으면 limits 로 재빌드(3.13, W2-06) | 운영 창 1,048,576 토큰(D-20). 작은 창 장치는 만들지 않는다(D-22) | `caps_for_limits`·`limits_rev`·글자 상한·근거 4,500자 상한·목록 글 780자 상한을 뺀다. 단위 크기는 줄 수로만, 값은 M0-b·M0-c 로 정한다. 창이 모자라면 러너가 `ctx_too_small` |
| 합성기 `tests/synth_ir.py`·`hwax-risk dev-seed-pair` CLI 를 WP2 가 만든다(걸음 1·11) | `app/devseed.py`(C3)와 `tests/synth/inject_dev.py`(7db27db)가 있다. 단 part_of 엣지를 내지 않는다 | CLI 는 만들지 않는다. devseed 가 실제 어댑터 함수로 part_of 엣지를 싣게 한다(걸음 1) |
| MCP 도구 14 → 15(`risk_get_units`) | 26종(Claude 입구 12종). 쓰기는 게이트웨이 위임 신원만(2eecb36). Claude Code 의 MCP 결과 상한 25,000토큰을 넘으면 본문 대신 파일 안내가 간다(d074004) | M2 끝 29종(26 + `risk_get_units` + WP3b 의 둘). `risk_get_units` 는 나눠 준다. `flow` 는 `risk_open_target` 인자로 받는다(새 도구 없음) |
| 타깃은 웹 `POST /targets` 로만 연다 | `entry.open_target` 이 같은 `routes.create_target` 을 부르고, 이미 연 대상이면 그것을 돌려준다. 길잡이 `risk_next_step` 이 단계를 건다 | 그 '이미 연 대상' 갈래가 방식 바꾸기의 Claude 입구다. 길잡이 6단계에 두 방식을 둔다 |
| Tier 잡은 사람이 세운다 | `runner._finish_job` 이 close_level C3 면 Tier B 뒤에 Tier C 를 스스로 세운다(consent_source `close_level`) | `cells` 문지기를 라우트가 아니라 `runner.create_job` 에 둔다 |
| 흐름 스위치 `HWAXRISK_REVIEW_FLOW`(코드 기본 panels, 전환은 WP5) | D-24 — 타깃마다 고르고 기본은 panels, M2 형식 승인 뒤 기본을 다시 정한다 | 그 손잡이를 만들지 않는다. `HWAXRISK_REVIEW_ENABLED` 와 `knobs.env` 로 박스마다 켠다(P-07) |
| `flow='cells'` 면 로스터를 `defer_absent=False` 로 동결(3.10.1) | 전원 포함은 PLAN 이 M3 로 옮겼다 | M2 의 `cells` 대상도 지금 규칙으로 동결한다. 입력 결손은 계산해 주고(걸음 8) WP3b 가 그 전문가를 M2 격자에서 뺀다 |
| 옛 타깃 회귀 가드(C0)는 계획만 있다 | `tests/fixtures/legacy`(7248651 의 v2 DB·골든)와 `test_legacy_flow.py`, 패널 셋 연속 done 시험이 있다 | 모든 걸음의 회귀 가드로 쓴다(D-24) |
| change_kind 두 종(R-32)은 WP2 2 가 택소노미에 더한다 | `rr_diff.v1.json`·`KIND_PRIORITY` 는 14종, `_CHANGE_KINDS`·`risk_spec.v1.json`·택소노미 1.0 은 12종 그대로다. PLAN 은 '택소노미 1.1' 을 M3(WP4 3)에 두었다 | 걸음 9(조건부). 판 번호가 PLAN 과 부딪친다(열린 물음 4) |
| WP3b 설계서는 `flow='units'`·`units.packets(max_chars)` 를 부른다 | 계약 C-5 는 `cells` 다 | `cells` 와 `units.manifest_items` 로 못 박고 WP3b 계획에 알린다 |

## 열린 물음

1. **방식 바꾸기의 규칙.** 권고 — `panels → cells` 는 살아 있는 잡이 없으면 패널이 돈 뒤에도 허용(얹기), `cells → panels` 는 검토 잡이 한 번도 없을 때만. cae00 원장에 실제 변경 비교 타깃은 M0-d 가 만드는 한 건뿐이라, M2 파일럿 대상은 M1 나갈 기준에서 패널 셋을 돈 그 타깃일 공산이 크고 그러면 얹기가 곧 파일럿 길이다(D-24 '비교'). 권한은 잡과 같은 editor 로 둔다(X2-11 은 소유자·관리자를 제안했다 — 사람 확인이 필요하면 그쪽으로 좁힌다).
2. **스위치와 박스별 켜기.** 권고 — `HWAXRISK_REVIEW_ENABLED` 기본 0, 박스별로는 `$DATA_DIR/knobs.env`(P-07). 매니페스트 `launch.env` 에 박으면 dev·cae00 이 같이 켜진다.
3. **`flow=cells` 로 연 snap 대상.** 권고 — 거절하지 않고 panels 로 열며 `flow_fallback.reason='snap_not_supported'` 를 싣는다(PLAN §4 '흐름 결정' 과 같은 꼴).
4. **R-32 를 M2 에서 할지와 판 번호.** 권고 — M2 에서 한다(WP3b 9 의 finding 승격이 `contact_type`·`parameter` 줄에서 조용히 `none` 을 만든다). 택소노미는 1.1 로 올리고 M3 의 메커니즘 14종은 1.2 로 적는다(W2-21). PLAN §3 M3 의 '택소노미 1.1 만' 문구를 '1.2' 로 고쳐야 한다 — 사용자·계획 관리자 몫.
5. **C6(단위 계약 XU)이 PLAN 의 M2 목록에 없다.** 권고 — XU1·XU2·XU8·XU9 는 걸음 1 시험에 접고(독립 오라클 `all_cids` 포함), XU6 은 D-22·R-40 뒤로 걸음 1 의 '줄 몸통 == `e2_line` 몸통' 단언으로 갈음하고, XU10 은 C7 요청 방향(1백만 토큰 창)에서 본다. XU3·XU4·XU5·XS1 은 M3 C6 으로 둔다.
6. **C15 — problems.md 는 빼자 했고 PLAN 은 M2 에 넣었다.** PLAN 이 이긴다. 권고 — 스크립트는 두고 update-all 배선(D9)만 뺀다.
7. **`SpecContext.unit_lines`(WP2 6 의 b).** 권고 — M3 로 미룬다. 소비처는 단위 줄을 인용하는 쟁점 패널이고, M1 의 R-40 으로 이름 불일치는 풀렸으며 남는 브리지 cid 충돌은 브리지 0행이라 재현 입력이 없다.
8. **시그니처·역할 표.** 권고 — M2 에서는 열·자산을 만들지 않는다. 목록 글에 필요한 건수·재질·수치 범위는 빌드 중 메모리에서 센다. 신호(M4)·교차 칸(M3)이 올 때 v5 열로 더한다(한 번 넣은 열은 지울 수 없다 — C-2).
9. **`rr_roster.input_gaps_json` 을 v4 에 넣나.** X3-03 은 v4 목록에 넣었다. 권고 — 넣지 않는다(M2 에 읽는 곳이 없고 계산으로 충분하다). M3 의 `undefer`·`backfill` 이 쓸 때 v5 로 더한다.
10. **검토 잡이 선 뒤의 재빌드.** 권고 — M2 는 409 `units_in_use` 로 막는다(`force`·셀 비우기는 WP3b `reset_review` 와 함께 M3). 재빌드를 부르는 원인(상한 손잡이·빌더 판)이 M2 에서는 사람의 손잡이 변경과 배포뿐이다.
11. **PLAN §7 'M2 앞' 세 결정 가운데 이 걸음들에 닿는 것.** 자격 만료(셋째)만 닿는다 — 권고대로 '멈추고 알린다' 면 `HWAXRISK_REVIEW_ON_CRED_CHANGE=hold` 와 `check_review_chain` 의 자격 여유 단언이 걸음 4 의 값이다. 카드 원문 복제(첫째)는 `rr_card_packs` 의 반출 제외·폐기(WP3b)이고 단위 표와 무관하다. FAIL 정책(둘째)은 WP3b·WP4 다.
12. **cells 대상의 승계.** 앞 타깃이 있는 과제에서 `cells` 로 열면 `_supersede_previous_target` 이 좌석을 `carried` 로 닫는다(X4 131행). M2 격자는 `rr_coverage` 상태를 보지 않으므로 해가 없다. 권고 — M3(롤업·완결이 `rr_coverage` 를 읽을 때)로 미룬다.

## 실측이 필요한 값

| 값 | 기대는 것 | 재는 곳 | 출하 기본값 |
|---|---|---|---|
| 실제 diff 의 항목 수(층·klass별)와 `lower_only_n`(이벤트 없이 좌석에 안 가던 변화) | 단위 수·셀 수·벽시계 | M0-c(M0-d 의 cae00 타깃에 `POST /units` 또는 탐침) | 없음(잰다) |
| 검토 대상 단위 수(kind별) | 격자 크기 = 9명 × 단위(M2), 359 × 단위(M3) | M0-c | 경고선 `HWAXRISK_UNITS_MAX=60`(넘으면 `oversize` — 잡 생성 때 동의) |
| 단위당 변경 줄 p50·p95·max | 묶음 크기, 한 판정 호출의 입력 | M0-c | `target_lines=20`·`max_lines=40`·`small_lines=15` |
| 줄 수와 판정 정확도·호출 시간의 관계 | `max_lines` 를 내릴지 | M0-b(K 탐침)·M2 파일럿 | 40 그대로, 실측 뒤 고친다 |
| 단위 요약 글자·근거 글자 p50·p95·max | 호출 시간, 창 여유 | M0-c | 상한 없음(글자로 자르지 않는다) |
| `tol_unknown` 단서 줄의 비율 | 판정 불가 몰림, 어댑터 tol 수리의 값어치 | M0-c | 단서 줄로 싣는다 |
| G2 차단·`capture_partial` 빌드 비율 | 의미층 없는 단위의 질 | M0-c | 머리 주의 줄 |
| hier(part_of) 구조 항목 수와 경계 단위 비율, 실제 조립 노드의 `asm_key` | W2-02 수리의 효과, 경계 단위 셀 수 | M0-c | 자식 부품 원자에 싣는다 |
| 가장 큰 diff 의 빌드 시간 | `create_target` 동기 요청 여유(nginx 600초 − 로스터 540초) | M0-c | 시험 단언 syn150 2초 안, 실측이 5초를 넘으면 빌드를 타깃 생성 뒤로 옮긴다 |
| 타깃당 단위 표 증가분(gz) | 백업·반출 크기 | M2 파일럿 | 설계서 추정 수백 KB |
| 전수 훑기의 '무관' 비율(목록 글을 본 판단) | 거르기를 켤 값어치(M4) | M2 파일럿(WP3b) | 거르기 끔 — 목록 글은 자르지 않는다 |
