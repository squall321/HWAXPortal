# 서버(cae00)에서 할 일 — 리스크 심사 M2 파일럿(카드 대조 · 대표 9명)

> 대상: cae00 운영자와 사용자 · **대조 시점 2026-10-12 · 초안** · 보낸 쪽: dev(이 리포 `docs/risk-review-redesign/`).
> **아직 돌리지 않는다.** 리스크 앱 M2 는 가지 `m2-cells` 에서 짓는 중이고 push 하지 않았다(v4 는 dev 리허설 뒤에 올린다 — PLAN 4절 C-2). 이 문서는 지금 아는 데까지 적은 초안이다. 아직 없는 걸음(S9 승격 · S10 전문가 보고서 · S11 품질 수치 · S12 REST·MCP)에 기대는 곳은 **[S12 뒤]** 처럼 표시했다. 단계 D(dev 리허설)가 끝나면 커밋 해시·도구 수·확인 문구를 채운 최종본을 보낸다.
> 지금 있는 것 — 리스크 앱의 단위 탐침 `backend/tests/synth/units_probe.py` 와 게이트웨이 대조 `backend/scripts/rr_gateway_check.py`(가지 `m2-u10`), 에이전트 서버 카드 대조 엔진과 포털 중계(단계 B, 포털 `0f66999` 이후).
> dev 에서 확인한 것 — 탐침을 dev 원장 사본(v4 로 이행)에 돌려 diff 2건의 줄을 받았다. 이 가지의 탐침을 떠 있는 dev 인스턴스 안(인스턴스의 파이썬과 `/data`)에서 돌리면 dev 원장이 아직 v3 라 `멈춤 — DB 스키마 3 ≠ 코드 4` 로 멈춘다(쓰기 없음). 대조 스크립트를 dev 게이트웨이에 PAT 없이 돌리면 배포본(M1 SIF, 26종)에 `risk_get_units` 가 없어 `판정 3` 이다.
> 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.
> 이 박스의 지금 상태는 이 문서가 알지 못한다. 그래서 확인마다 재는 명령을 적었다.

## 0. 한눈에

M2 의 나갈 기준을 cae00 의 실제 과제 하나에서 댄다. M0-d 로 만든 실제 변경 비교 대상에 카드 대조를 얹고(패널 방식 → 카드 대조), 사용자가 고른 영역 대표 9명이 검토 대상 단위 전부를 자기 카드마다 판정한다. 끝나면 전문가 보고서 9편이 나오고, 사용자가 3편을 읽고 인용 10개를 카드 원문과 대조해 '이 형식이 원하던 상세 보고서인가' 를 답한다(M2.md 1절 기준 4). 아니면 보고서 조립을 고치고 M3 로 가지 않는다.

- 사람이 할 일 — 전제 확인(1절) → 켜기(2절) → 단위 세우고 재기(3절) → 9명 고르기(4절, 사용자) → 잡 시작(5절) → 지켜보기(6절) → 게이트웨이 대조(7절, 배포 뒤 아무 때나) → 보내기(8절).
- 바뀌는 것 — 리스크 앱 데이터 디렉터리의 `knobs.env` 한 줄, 그 대상의 심사 방식(`flow`)과 검토 단위·셀·판정 행. 이미 돈 패널·의견·등록부는 건드리지 않는다. 카드 대조 finding 은 패널 등록부에 섞이지 않고 다른 과제의 선례로도 쓰이지 않는다(M2.md 5절 #7·#9·#20).
- 걸리는 시간 — 셀 수는 9 × 검토 대상 단위 수이고 셀마다 호출이 여럿이다(훑기 · 판정 순·역·단독 · 카드 밖). 호출 하나의 초는 M0-b 탐침이 잰다. [S12 뒤] 잡을 만들 때 호출 추정(`calls_estimate{low, high}`)이 나온다.
- 공유 LLM — 카드 대조는 에이전트 서버 관문에서 동시 4(심의가 돌면 2)까지만 GLM 을 쓴다. 그동안 챗 첫 응답이 늦을 수 있어 잰다(8절).
- 검토는 사용자 PAT 로만 돈다. 자격이 만료되면 서비스 계정으로 내려가지 않고 잡이 `credential` 로 멈춘다(M2.md 2절 결정 3).

## 1. 전제 확인

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | M1 이 들어와 있다 | 포털 리포 루트에서 `./infra/scripts/risk-review-inventory.sh` | `스키마 버전:` 이 3 이상. 2 면 `server-setup-m1.md` 부터 |
| 2 | M0-b 탐침을 돌려 결과를 dev 에 보냈다 | `server-setup-m0b.md` 3절 | dev 가 받았다고 했다. 그 값으로 다시 정한 K·호출 초를 이 절차서 최종본에 적는다 |
| 3 | M0-d 의 실제 변경 비교 대상이 있다 | dev 와 같이 만든다(이 문서 밖). Claude 에서 `risk_list_projects` | 그 과제에 `target_key` 가 `diff:` 로 시작하는 대상이 있다. `target_key` 와 diff id(`diff:` 뒤)를 적어 둔다 |
| 4 | 그 대상에 살아 있는 잡이 없다 | Claude 에서 `risk_get_coverage(target_key='diff:…', with_seats=false)` | `job` 이 없거나 `state` 가 `completed`·`cancelled`·`failed` 다. `queued`·`running`·`paused`·`cancelling` 이면 끝난 뒤에 한다(방식을 바꾸지 못한다 — `flow_locked`) |
| 5 | M2 판이 들어왔다 | 1 과 같은 명령 | `스키마 버전: 4`. 3 이면 update-all 이 아직 리스크 앱을 바꾸지 못했다 — `○ … 재기동 건너뜀`(심의가 돌았다)이었으면 끝난 뒤 한 번 더 돌린다 |
| 6 | 에이전트 서버가 카드 대조를 안다 | 아래 명령 | `"capabilities":["card_review"]`, `review_active` 0, `request_worst_s` 가 18000 보다 작다 |
| 7 | 게이트웨이에 새 도구가 뜬다 | 7절의 대조 스크립트 | `판정 0 — 이상 없음`. [S12 뒤] 기대 도구 29종 |
| 8 | 검토를 돌릴 사람의 PAT 가 웹 리스크 앱에 등록돼 있고 넉넉하다 | 웹 리스크 앱 설정 화면 | 등록돼 있고 만료가 파일럿이 끝날 때보다 뒤다. [S12 뒤] 잡을 만들 때 짧으면 `credential_note` 가 미리 알린다 |

확인 6 의 명령(어느 디렉터리에서든).

```bash
curl -s --noproxy '*' http://127.0.0.1:9009/health | grep -oE '"(review_active|request_worst_s)": *[0-9.a-z]+|"capabilities": *\[[^]]*\]'
```

`capabilities` 가 비었으면 에이전트 서버가 카드 대조 전의 판이다. update-all 이 에이전트 서버를 다시 띄운 뒤 다시 본다.

## 2. 켜기 — `knobs.env` 한 줄

카드 대조(`flow='cells'`)는 박스마다 켠다. 스위치는 리스크 앱 데이터 디렉터리의 `knobs.env` 에 적고, 앱을 다시 띄워야 읽는다(기동 때 한 번 읽는다). 매니페스트(`launch.env`)에는 적지 않는다 — 거기 적으면 dev 와 cae00 이 같이 켜진다.

### 2-1. 데이터 디렉터리 찾기

앱은 컨테이너 안에서 `/data` 를 데이터 디렉터리로 쓰고, 허브가 호스트의 `var/app_data/hwax_risk` 를 거기에 묶는다. `/data` 이관을 한 박스는 그 경로가 심링크다.

```bash
cd ~/Projects/HEAXHub
D="$(readlink -f var/app_data/hwax_risk)" && echo "$D"
ls -l "$D/risk_review.db"                          # 원장이 여기 있어야 한다
grep -n '^HWAXRISK_' "$D/knobs.env" 2>/dev/null    # 이미 적힌 손잡이(없으면 아무것도 안 나온다)
```

`risk_review.db` 가 없으면 경로가 다르다 — 멈추고 dev 에 `echo` 출력을 보낸다.

### 2-2. 적기

`HWAXRISK_REVIEW_ENABLED` 줄이 없으면 덧붙인다.

```bash
printf 'HWAXRISK_REVIEW_ENABLED=1\n' >> "$D/knobs.env"
```

이미 `HWAXRISK_REVIEW_ENABLED=0` 줄이 있으면 덧붙이지 말고 그 줄의 값을 1 로 고친다. 값은 `1`·`true`·`yes`·`on` 만 켜기로 읽고, 그 밖의 낱말은 앱이 기동하지 않는다(조용히 꺼진 채 돌지 않게 한 것이다).

### 2-3. 앱 다시 띄우기

도는 잡이 없을 때(1절 확인 4) 허브 리포 루트에서 띄운다. 최신 SIF 그대로 인스턴스만 바꾼다(`--rebuild` 는 주지 않는다).

```bash
cd ~/Projects/HEAXHub
ls deploy/apptainer/redeploy-app.sh && deploy/apptainer/redeploy-app.sh hwax-risk
```

| 출력 | 뜻 | 할 일 |
|---|---|---|
| `✓ 재기동 완료 — port=…` | 새 설정으로 떴다 | 2-4 |
| `✗ 재기동 실패` | 앱이 기동하지 않았다 | `var/logs/integration_hwax_risk.log` 끝에서 `HWAXRISK_` 로 시작하는 문구를 본다 — 손잡이 값이 틀렸으면 고칠 자리(파일 경로와 이름)를 말한다 |
| `redeploy-app.sh` 가 없다 | 허브가 옛 판이다 | update-all 을 먼저 돌린다 |

### 2-4. 들었는지 보기

관리자 계정으로 웹 리스크 앱에 로그인한 브라우저에서, 같은 주소의 `/apps/hwax_risk/api/meta/runtime` 을 연다.

| 칸 | 기대 |
|---|---|
| `knobs.HWAXRISK_REVIEW_ENABLED` | `{"value": true, "source": "knobs.env"}` |
| `knobs_file` | `/data/knobs.env` — 컨테이너 안의 경로다. 호스트에서는 2-1 의 `$D/knobs.env` 와 같은 파일이다 |
| `schema_version` | 4 |

관리자 계정이 없으면 3-1 로 간다. 꺼져 있으면 3-1 의 응답이 `review_disabled` 로 같은 사실을 말한다.

## 3. 단위 세우기와 재기(M0-c)

### 3-1. 카드 대조로 바꾸기(얹기)

Claude 에서 대상을 방식만 바꿔 다시 연다. 무엇을 하는지 사용자에게 말하고 동의를 받은 뒤 부른다.

```text
risk_open_target(kind='diff', ref_id='<diff id>', consent=true, flow='cells', reason='M2 파일럿 — 카드 대조 얹기')
```

기대 — `created: false`, `flow: "cells"`, `flow_change.changed: true`, `flow_change.units` 의 `status` 가 `ok`(또는 `oversize`)이고 `reviewable_n` 이 검토 대상 단위 수다. 그 diff 에 대상이 아직 없었으면 `created: true` 로 새로 열리고 같은 요약이 `units` 칸에 온다. 웹에서도 같은 대상이 카드 대조 방식으로 보인다.

| 오류 | 뜻 | 할 일 |
|---|---|---|
| `review_disabled` | 스위치가 꺼져 있다 | 2절. 메시지가 고칠 자리(`knobs.env`)를 말한다 |
| `flow_locked` | 살아 있는 잡이 있거나, Claude 보충 회차가 브리프를 받아 간 패널이 아직 안 끝났다 | 끝난 뒤 다시 |
| `units_unbuildable` | 검토 단위가 서지 않았다(괄호 안이 빌드의 까닭) | 응답 전체를 dev 에 보낸다 |
| `delegation_required` | 게이트웨이가 본인 신원을 실어 보내지 못했다 | 응답의 `detail.fix` 를 따른다(`server-setup-m1.md` 3절 ④) |

단위 수만 재고 방식은 그대로 두려면 웹·REST 의 `POST /api/targets/{target_key}/units`(편집 권한)를 쓴다. 같은 단위가 서고 패널 방식은 바뀌지 않는다.

### 3-2. 단위 보기

```text
risk_get_units(target_key='diff:<diff id>')
```

`status` 가 `ok`, `stats.units.reviewable` 이 3-1 의 `reviewable_n` 과 같고, `invariants` 의 목록이 전부 비어 있다(`U4_lint`·`U5_clipped` 는 0). 단위가 많으면 `next_offset` 으로 나눠 준다(자르지 않는다).

### 3-3. 탐침 — 같은 수를 읽기 전용으로 다시 낸다

떠 있는 앱 인스턴스 안에서 탐침을 돌린다(cae00 에는 앱 venv 가 없어도 된다). 원장을 SQLite 읽기 전용으로 열고, 이행·러너 잠금·쓰기가 없다.

```bash
apptainer instance list                              # 출력에 heax_app_hwax_risk 줄이 있어야 한다
OUT=~/m2-units-$(date +%m%d-%H%M).jsonl
apptainer exec --pwd /app/backend instance://heax_app_hwax_risk \
  python -m tests.synth.units_probe --data-dir /data --target-key 'diff:<diff id>' > "$OUT"
cat "$OUT"
```

`--target-key` 대신 `--all` 을 주면 원장의 diff 전부를 한 줄씩 잰다(M0-c — 다른 실제 비교도 있으면 같이 보낸다).

| 줄 | 기대 | 다르면 |
|---|---|---|
| 화면의 `[원장] /data/risk_review.db · 스키마 v4 · 읽기 전용 · diff 1건 · 단위 손잡이 …` | 손잡이 넷이 `(default)` 또는 `(knobs.env)` | — |
| JSON 줄의 `"status"` | `"ok"`(또는 `"oversize"`) | `failed` 면 `error`·`error_detail` 과 함께 보낸다 |
| `"invariants_ok"` | `true` | 줄 전체를 보낸다 |
| `"active_builds"` | `[{"target_key": "diff:…", … "same_input": true, "same_stats": true}]` | `same_stats` 가 `false` 면 3-1 의 빌드와 손잡이가 다르다 — 줄 전체와 2-4 의 `knobs` 를 보낸다 |
| `멈춤 — /data/risk_review.db 가 없다` | — | `--data-dir /data` 를 그대로 썼는지 본다 |
| `No module named tests.synth.units_probe` | — | 인스턴스가 M2 전의 SIF 다. 1절 확인 5 |

줄에서 dev 가 읽는 칸 — `items`(층·klass 별 항목 수), `lower_only_n`(이벤트 없이 패널에 가지 않던 변화), `tol_unknown_n`(비교 잣대를 모르는 단서 줄), `units`(종류별 단위 수), `lines.per_unit`(단위당 변경 줄 p50·p95·max), `summary_chars`·`evidence_chars`(글자 합과 단위당 분포), `build_ms`, `stats`(빌드 회계 전부). 카드·단위 원문은 들어 있지 않다.

## 4. 9명 고르기 — 사용자

코드가 고르지 않는다(M2.md 5절 #11). 사용자가 영역 대표 9명을 고른다.

```text
risk_get_coverage(target_key='diff:<diff id>', with_seats=true)
```

- 영역(`domain`)마다 대표 한 명씩, 9개 영역에서 고른다. 대표는 그 영역의 1순위 좌석이다 — Tier A 패널을 돌린 대상이면 `seats` 의 `tier` 가 `A` 인 좌석이다. 패널을 돌리지 않아 `tier` 가 비어 있으면 [S12 뒤] 최종본이 1순위를 보는 곳을 적는다(그 전에는 dev 에 대상 키를 보내 묻는다). `agent_key` 를 적어 둔다.
- ECAD 가 없는 과제면 ECAD 에 기대는 영역(회로 등)은 고르지 않는다. 그 영역의 2순위부터는 `status` 가 `deferred`·`reason` 이 `ecad_absent` 로 보이고, 1순위는 `pending` 이어도 입력이 빠진 좌석이다. 입력 결손 호출은 M3 다. 잘못 넣으면 잡을 만들 때 `input_gap_m3` 로 거절되고 그 `agents` 를 말한다.
- 1순위의 카드가 0장이면 다음 순위로 바꾸거나 그대로 둔다(그 셀은 역할만으로 판정하는 `role_only` 가 된다). 무엇을 고를지는 사용자가 정한다. [S12 뒤] 카드 장수가 어디에 보이는지는 최종본에 적는다.

## 5. 잡 시작 — [S12 뒤]

**S12(REST·MCP)가 들어온 뒤에 쓸 수 있다.** 잡을 만드는 본체(S5)는 있고, `risk_start_job` 의 `mode`·`scope` 인자는 S12 가 더한다. 아래는 계획(M2.md 4.7, m2-wp3b S12)의 모양이고 최종본에서 확인한다.

```text
risk_start_job(target_key='diff:<diff id>', mode='reviews', scope={'agents': ['<키1>', …, '<키9>']}, consent=true)
```

- 무엇을 얼마나 돌리는지(셀 수·호출 추정)를 사용자에게 보이고 동의를 받은 뒤 `consent=true` 로 부른다. `tier` 는 주지 않는다.
- 응답 — `job_id`, `cells_total`(로스터 전원 × 단위), `cells_in_scope`(9 × 단위), `experts_in_scope`, `calls_estimate{low, high}`, `credential{kind, email, exp}`, 있으면 `credential_note`(높은 끝 추정 소요가 PAT 남은 수명보다 길다).
- 시작 직전 원장 크기를 적어 둔다(8절 6). `D` 는 2-1 에서 정한 데이터 디렉터리다(새 셸이면 2-1 의 첫 두 줄을 다시 돌린다).

```bash
ls -l "$D"/risk_review.db "$D"/risk_review.db-wal
```

| 거절 | 뜻 | 할 일 |
|---|---|---|
| `review_disabled` | 스위치가 꺼져 있다 | 2절 |
| `units_absent` | 활성 단위 빌드가 없다 | 3-1 |
| `review_job_exists` · `panel_job_running` | 이미 도는 잡이 있다 | 그 잡이 끝난 뒤 |
| `repersist_pending` | 다시 저장을 기다리는 패널이 있다 | `risk_repersist_panel` 로 먼저 정리한다 |
| `input_gap_m3` | 범위에 입력 결손 전문가가 있다 | 응답의 `agents` 를 빼고 다시(4절) |
| `scope_invalid` · `scope_empty` | 범위의 키가 로스터에 없거나 비었다 | 키 철자를 본다 |
| `consent_required` | 호출 추정이 동의 문턱(1,500)을 넘는다 | 사용자에게 보이고 `consent=true` |
| `review_too_large` | 높은 끝 추정이 상한(30,000)을 넘는다 | dev 와 상의(범위를 나눈다) |
| `pat_unavailable` | 쓸 사용자 PAT 가 없다 | 웹 리스크 앱 설정 화면에서 등록 |

## 6. 지켜보기 — [S12 뒤]

### 6-1. 진행판

```text
risk_get_coverage(target_key='diff:<diff id>', with_seats=false)
```

S12 가 기존 칸 옆에 `review` 칸을 더한다(셀이 없는 대상은 `null`). 계획의 모양 — `review.cells{total, by_state, by_basis, in_scope, out_of_scope_pending, failed_open}` · `review.experts{total, by_state}` · `review.quality`(60초마다 갱신되는 요약) · `review.job{id, mode, state, hold_code, hold_until, hold_n, error, credential_email, phase, progress, waiting, signal}`. 끝은 범위 안 셀이 전부 `reviewed` 이거나 `failed` 인 때다.

웹 대상 화면도 같은 원장을 읽는다.

### 6-2. 멈췄을 때 — `review.job.hold_code`

| 코드 | 뜻 | 저절로 다시 도나 | 할 일 |
|---|---|---|---|
| `user` | 사람이 멈췄다 | 아니다 | `risk_job_action(job_id='…', action='resume')` 또는 웹의 재개 |
| `credential` | 검토자 PAT 를 더 쓸 수 없다(만료·폐기·거절) | 아니다 | 웹 리스크 앱 설정에서 PAT 를 다시 등록하고 재개한다. 서비스 계정으로 내려가지 않는다 |
| `ctx_too_small` | 단위 하나가 LLM 창에 들지 않는다 | 아니다 | dev 에 알린다(다시 쪼개지 않는다 — D-22) |
| `llm_misconfigured` | 에이전트 서버의 LLM 설정(키·모델 이름) | 아니다 | 에이전트 서버 `.env` 의 `VLLM_*` 를 본다. dev 에 알린다 |
| `contract` | 앱과 엔진·포털의 요청 계약이 어긋났다(판이 섞였다) | 아니다 | update-all 이 셋을 같은 판으로 맞췄는지 본다. dev 에 알린다 |
| `content_fail_rate` | 내용 탓 실패가 절반을 넘었다(차단기) | 아니다 | dev 에 알린다 |
| `llm_outage` | LLM 에 닿지 않는다 | 예(5분 → 10분 → … 1시간) | 이어지면 LLM 서버 상태를 본다 |
| `aidh_unreachable` | 카드를 받지 못한다(AIDataHub·게이트웨이) | 예(5분 → 30분) | 이어지면 AIDataHub 를 본다 |
| `agent_outdated` | 에이전트 서버·포털에 카드 대조 경로가 없다 | 예(5분) | 1절 확인 6, update-all |
| `ctx_unknown` | LLM 서버가 창 크기를 알려 주지 않는다(10분 넘게) | 창 출처가 돌아오면 | LLM 서버가 닿는지 본다 |

자동 재개가 없는 보류는 고친 뒤 `resume` 해야 다시 돈다. 보류 코드가 나온 시각과 코드를 적어 둔다(8절 7).

### 6-3. 재기동해도 이어 도는지 — 한 번만

나갈 기준 3 이다. 셀이 몇십 개 `reviewed` 가 된 뒤, 호출이 도는 동안 앱을 한 번 내렸다 올린다(2-3 의 `redeploy-app.sh hwax-risk`). 기대 — 몇 분 안에 `review.cells.by_state` 의 `reviewed` 가 다시 늘고, 그 사이 `failed` 가 늘지 않는다(끊긴 호출은 차감 없이 다시 돈다). 전후의 `by_state` 를 적어 둔다.

### 6-4. 포털 대화가 늘지 않는지

나갈 기준 3 의 다른 반이다. 검토는 포털 대화를 만들지 않는다. 검토자 계정의 포털 챗 대화 목록을 시작 전과 끝난 뒤에 보고 새 대화 수를 적는다(0 이 기대다).

## 7. 게이트웨이 대조 — 배포 뒤 한 번

새 도구가 배포본 게이트웨이에 실제로 뜨는지 소스가 아니라 게이트웨이에 묻는다(리포 규칙 — 'unknown tool: intake' 전례). 읽기만 하고 update-all 에는 배선하지 않았다(M2.md 5절 #15). 기대 목록은 그 체크아웃의 `backend/app/mcp_server.py` 다.

```bash
cd ~/Projects/HWAXRisk
git log -1 --oneline                                # [S12 뒤] 최종본이 적는 커밋과 같아야 한다
python3 --version                                   # 3.10 이상
read -rs HWAX_GATEWAY_PAT && export HWAX_GATEWAY_PAT  # 포털 개인 토큰 — 화면·기록에 남지 않는다
python3 backend/scripts/rr_gateway_check.py
unset HWAX_GATEWAY_PAT
```

- PAT 를 주면 tools/list 를 묻고 `risk_get_units` 를 없는 대상 키로 한 번 부른다(쓰기 없음). PAT 없이 돌리면 무인증 `/tools-map` 목록만 본다(`[호출] 하지 않았다` 줄이 나온다).
- 게이트웨이 주소가 기본(`http://127.0.0.1:9110/mcp`)과 다르면 `HWAX_GATEWAY_URL` 로 준다. 셸의 프록시 변수는 쓰지 않는다.
- `~/Projects/HWAXRisk` 가 없거나 `python3` 이 3.10 보다 낮으면 앱 인스턴스의 파이썬으로 그 파일을 돌린다 — `apptainer exec instance://heax_app_hwax_risk python3 ~/Projects/HWAXRisk/backend/scripts/rr_gateway_check.py`. 체크아웃이 아예 없으면 `/app/backend/scripts/rr_gateway_check.py`(배포본 자신의 소스)를 돌리고 `[기대] … 도구 N종` 의 N 이 [S12 뒤] 29 인지 본다.

| 출력 | 뜻 | 할 일 |
|---|---|---|
| `판정 0 — 이상 없음` | 기대 도구가 다 뜨고 `risk_get_units` 가 `not_visible` 로 답한다 | — |
| `[빠짐] N종 — …` 과 `판정 3` | 배포된 리스크 앱 SIF 가 이 소스보다 낡았다 | update-all 을 다시 돌린다(허브 구획이 `○ … 재기동 건너뜀` 으로 미뤘을 수 있다). 그래도 3 이면 출력을 dev 에 보낸다 |
| `→ unknown tool` 과 `판정 3` | 게이트웨이 목록에만 있고 떠 있는 앱은 모른다 | 2-3 의 `redeploy-app.sh hwax-risk`, 1분 뒤 다시 |
| `[소스에 없음] N종 — …` | 이 체크아웃이 배포본보다 낡았다 | `git log -1` 을 보고 update-all 뒤 다시 |
| `PAT 를 거절했다(HTTP 401` | 토큰이 틀렸거나 만료됐다 | 포털 '개인 토큰' 페이지에서 다시 받는다 |
| `리스크 앱 도구가 하나도 안 보인다` | 그 계정에 리스크 앱 권한이 없거나 토큰 페이지에서 앱을 꺼 두었다 | PAT 없이 다시 돌려 `/tools-map` 에 앱이 있는지 본다 |
| `에 닿지 않는다` | 게이트웨이가 떠 있지 않거나 주소가 다르다 | `./infra/scripts/status.sh`(포털 리포) |
| `판정 2 — 판정 불가` 의 다른 문구 | 위에 없는 경우 | 출력 전체를 보낸다 |

종료 코드 — 0 이상 없음, 2 판정 불가, 3 배포본이 낡았다.

## 8. 보내기

dev 에 보낸다. 토큰·사내 주소는 넣지 않는다.

1. **단위 탐침 줄** — 3-3 의 `$OUT` 파일(`--all` 로도 돌렸으면 그것도).
2. **게이트웨이 대조 출력** — 7절 화면 전체.
3. **진행판 마지막 모양** [S12 뒤] — 끝난 뒤 `risk_get_coverage(…, with_seats=false)` 의 `review` 칸 전체.
4. **품질 수치** [S11·S12 뒤] — 격자(셀 상태·`basis`)·카드 폭포·절단(`output_truncated` 1·0·모름)·인용 통과율·뒤집힘·종류별 호출 초 p50·p95·최대·실측(셀당 호출 수, 양성 비율, 훑기 '무관' 비율, 토큰과 글자/토큰 비, 새 표 바이트). 표본이 모자란 값은 `null` 과 표본 수로 온다 — 0 으로 바꾸지 않는다.
5. **사용자 판정** — 보고서 9편 가운데 3편을 읽고 아래 표를 채운다. [S12 뒤] 보고서는 `risk_get_expert_report(target_key, agent_key, part='summary')` 와 웹 대상 화면의 전문가 보고서로 읽는다. 행마다 카드 참조가 `card:<record_id>#<section_id>` 로 붙고, 인용은 200자까지 보이고 원래 길이가 적힌다(사용자 결정 1). 카드 원문은 Claude 에서 그 `record_id` 의 지식카드를 열어 그 절을 본다.

   | # | 전문가 | 단위 | 카드 참조 | 보고서의 인용(앞부분) | 카드 원문에 그대로 있나 | 메모 |
   |---|---|---|---|---|---|---|
   | 1~10 | | | | | 예 · 아니오 | |

   그리고 한 줄 — **'이 형식이 원하던 상세 보고서인가'** 에 예·아니오, 아니오면 무엇이 달라야 하는지.
6. **원장 크기** — 5절에서 적은 시작 전 크기와 끝난 뒤의 `ls -l "$D"/risk_review.db "$D"/risk_review.db-wal`.
7. **멈춘 기록** — 6-2 의 보류 코드와 시각, 6-3 의 재기동 전후 `by_state`, 6-4 의 새 대화 수.
8. **챗 첫 응답 지연** — 지금 이 값을 찍는 로그가 없다. 파일럿 시작 전에 한 번, 도는 동안 하루 두세 번, 포털 챗에 같은 짧은 질문을 보내고 첫 글자가 나올 때까지의 초를 잰다. 시각·초·그때 `review_active`(1절 확인 6 의 명령)를 적는다.

## 9. 끄기와 되돌리기

- **끄기** — 도는 검토 잡을 먼저 멈추거나 취소한다(`risk_job_action(job_id='…', action='pause')` 또는 `'cancel'`). 그다음 `knobs.env` 의 줄을 `HWAXRISK_REVIEW_ENABLED=0` 으로 고치고 2-3 처럼 다시 띄운다. 꺼진 박스에서는 카드 대조로 열기·바꾸기·검토 잡 만들기가 `review_disabled` 로 거절된다. 이미 쌓인 셀·판정은 지워지지 않는다.
- **방식 되돌리기** — 카드 대조 → 패널은 그 대상에 검토 잡이 한 번도 없을 때만 된다(M2.md 5절 #3). 잡이 선 뒤에는 그 대상은 카드 대조로 남는다. 패널 결과와 등록부는 그대로 있다.
- **앱 판 되돌리기** — M2 SIF 가 처음 뜰 때 원장을 v4 로 올리고 직전 사본 `risk_review.db.pre-migrate-v3-<시각>` 을 남긴다. 옛 SIF 는 v4 원장을 열지 못한다. 옛 판으로 내리려면 그 사본을 `risk_review.db` 로 되돌린다 — 그 사이에 쓴 것은 잃는다(`server-setup-m1.md` 4절과 같은 방식).

## 10. 손잡이 (전부 선택 — 안 적으면 기본값)

리스크 앱 손잡이는 `$D/knobs.env` 에 적는다. 순서는 환경변수 > `knobs.env` > 코드 기본값이고, 고친 뒤에는 앱을 다시 띄운다(2-3). 값과 출처는 `/api/meta/runtime`(2-4)이 보인다. 정수가 아니거나 하한 밑이면 앱이 기동하지 않고 고칠 자리를 로그에 말한다.

| 이름 | 기본 | 무엇 |
|---|---|---|
| `HWAXRISK_REVIEW_ENABLED` | 0 | 카드 대조의 스위치(2절) |
| `HWAXRISK_UNIT_TARGET_LINES` · `HWAXRISK_UNIT_MAX_LINES` · `HWAXRISK_UNITS_SMALL_LINES` · `HWAXRISK_UNITS_MAX` | 20 · 40 · 15 · 60 | 단위 크기(줄 수). 검토 잡이 선 대상은 단위를 다시 세우지 않는다(`units_in_use`) — 파일럿 전에만 바꾼다 |
| `HWAXRISK_REVIEW_CONCURRENCY` | 4 | 앱의 검토 워커 수. 에이전트 서버 관문(`CARD_REVIEW_CONCURRENCY`)보다 크게 두지 않는다 |
| `HWAXRISK_REVIEW_CALL_TIMEOUT_S` | 18000 | 호출 하나의 벽시계. 1절 확인 6 의 `request_worst_s` 보다 커야 한다 |
| `HWAXRISK_REVIEW_READ_TIMEOUT_S` | 300 | 프레임 사이 침묵 한도(엔진 ping 15초). 벽시계보다 작아야 기동한다 |
| `HWAXRISK_REVIEW_MAX_CHARGED` | 2 | 셀의 내용 탓 실패 한도 |
| `HWAXRISK_REVIEW_CONSENT_CALLS` · `HWAXRISK_REVIEW_MAX_CALLS` | 1500 · 30000 | 동의가 필요한 호출 추정 · 넘으면 거절하는 상한 |

에이전트 서버 쪽 손잡이(`CARD_REVIEW_K` · `CARD_REVIEW_CONCURRENCY` 등)는 M2.md 4.5 에 있다. M0-b 결과로 `CARD_REVIEW_K` 를 바꾸게 되면 최종본에 적는다.

## 11. 이 초안이 아직 모르는 것

최종본(단계 D 뒤)에서 채운다.

- 반영 커밋 해시(HWAXRisk 가지를 합친 커밋 · 에이전트 서버 · 포털)와 게이트웨이 도구 수 29 의 확인.
- 5·6·8절의 [S12 뒤] 모양 — `risk_start_job` 의 `mode`·`scope` 인자, `review` 칸, `risk_get_expert_report` 의 인자와 쪽 나눔, 품질 수치의 칸 이름(S11).
- 전문가의 카드 장수와 영역 안 1순위를 어디서 보는지(4절 — 지금 진행판 좌석 행에는 순위가 없다).
- M0-b 로 다시 정한 `CARD_REVIEW_K` 와 호출 초 — 걸리는 시간 어림(0절).
- 6-3 재기동 시험을 dev 리허설에서 먼저 본 결과.
