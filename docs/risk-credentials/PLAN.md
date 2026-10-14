# 리스크 심사 앱 — SSO 로 들어온 사람의 자격으로 끝까지 돌게(서비스 키 없이)

요청 2026-10-14(koo.park, 「HWAXRisk 변경 요청 — SSO 로그인한 사람의 자격으로 리스크 심사가 끝까지 돌게」 R1~R5) · 계획 2026-10-14 · 대상 HWAXRisk(백엔드)·HWAXPortal·HWAXMcpGateway, 화면은 HWAXRisk 화면 세션에 요청서로.

결정의 이유는 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md), 화면 세션에 넘기는 것은 [frontend-request.md](frontend-request.md) 다.

## 1. 무엇을 하나

리스크 앱은 지금 두 종류의 자격으로 돈다 — 사람이 앱 설정에서 손으로 등록한 포털 PAT, 그리고 박스 `secrets.env` 의 서비스 키다. cae00 에는 서비스 키가 없다. 그래서 PAT 를 손으로 등록하지 않은 사람의 잡은 막히고, Claude 로 캡처하면 단위 검문이 「모름」으로 막힌다.

이 작업이 끝나면 다음과 같다.

- 웹으로 들어오든 Claude 로 들어오든 **그 사람의 포털 PAT 가 저절로 등록·갱신된다.**
- 사람이 시작한 잡은 **그 사람 자격으로만** 돌고, 자격이 없으면 서비스 시야로 내려가지 않고 멈추고 알린다.
- Claude 로 캡처해도 StepForge REST 를 그 사람 PAT 로 게이트웨이를 거쳐 읽는다.
- RA 로 아직 보내지 않은 일은 「반영 안 됨 — 사유」로 보인다.
- 설정 화면은 박스 자격이 왜 모자란지를 까닭별로 말한다. 필수 키는 실제로 쓰는 것만 남는다.

## 2. 사실(조사 2026-10-14, dev 의 main 기준)

요청서의 전제와 다른 것이 있어 먼저 적는다. 근거 줄은 [context-notes.md](context-notes.md) C-1 에 있다.

1. **RA 쓰기와 AIDataHub 반입은 운영 코드에 배선되어 있지 않다.** `PORTAL_PAT_RW`·`AIDH_API_KEY` 로 클라이언트를 만드는 곳이 없다. RA·ADH 로 보낼 일은 `rr_targets.external_sync_json` 에 쌓이기만 하고, 보내는 쪽(`nightly.retry_external_sync` 의 sender)이 연결되어 있지 않다. 패널 보고서(report_id)는 이것과 별개로, 에이전트 서버가 사람 자격으로 RA 에 이미 저장한다.
2. **박스 자격 판정 `secrets_valid` 가 쓰지 않는 두 키까지 필수로 센다.** 그래서 어느 박스든 경고가 뜬다. 판정은 `secrets.env` 파일만 보므로, env 로 준 `CRED_KEY` 도 '없음' 으로 센다.
3. **StepForge 에는 사람별 권한이 없다.** heax 토큰이면 전부 보이고 `owner` 는 기록일 뿐이다. 게이트웨이 REST 사이트 `step-forge`(GET 전용, 허브 관리자 토큰 주입)는 **사람의 포털 PAT 로** `/tree` 를 읽게 해 준다. 감사에도 그 사람으로 남는다.
4. **AIDataHub 에는 서버끼리 쓰는 사람별 길이 없다.** API 키에는 사람이 아니라 이름·부서만 실린다.
5. **포털에는 '서비스가 사람 X 의 PAT 를 받는 길' 이 없다.** PAT 로 PAT 를 발급할 수도 없다(일부러 막았다). 웹은 앱이 포털과 같은 출처라, 화면이 `POST /auth/pat` 를 세션 쿠키와 CSRF 로 부를 수 있다(지금 버튼이 하는 일).
6. **Claude 로 온 호출에서 게이트웨이는 호출자 본인의 포털 PAT 를 쥐고 있다.** 리스크 앱에 위임 단언을 받는 그 요청 안에서 그 PAT 에 닿는다(`_low.request_context.request`).
7. 게이트웨이 `GW_TOKEN` 은 `x-hwax-user` 로 아무나 사칭할 수 있고 에이전트 서버도 그것을 쥔다. 이 작업은 그 힘을 넓히지 않는다.

## 3. 사용자 결정(2026-10-14)

| # | 물음 | 정한 것 |
|---|---|---|
| U-1 | Claude 로 시작한 잡의 PAT 를 어떻게 받나(요청서 R1-2 의 가·나) | **토큰 교환.** 게이트웨이가 호출자 본인의 포털 PAT 를 증거로 포털에서 좁은 PAT 를 바꿔 받아 리스크 앱에 넘긴다. 앱이 '필요하다' 고 할 때만 한다. (가)는 GW_TOKEN 의 힘을 포털 중계까지 넓혀서, (나)는 백그라운드 러너가 사람 없이 매번 받으려면 리스크 앱이 아무나 사칭할 힘을 가져야 해서 택하지 않았다 |
| U-2 | 웹의 자동 등록·갱신은 어디서 | **화면이 자동으로 한다. 이번에는 요청서만 넘긴다.** 백엔드는 '지금 필요한가'·'끄기' 칸만 만든다 |
| U-3 | 사람 자격을 끝내 못 얻으면 패널 잡은 | **멈추고 알린다**(카드 대조 D-26 과 같다). 서비스 PAT 는 사람이 없는 짧은 호출(로스터·현장 VOC·캡처 MCP 폴백)에만 남고, 쓰이면 표시한다 |
| U-4 | RA 쓰기(R3)를 이번에 어디까지 | **보이게만 한다. 쓰기는 M4.** 보내는 쪽이 아직 없다는 것을 진행판·과제·MCP 에 싣는다 |

## 4. 설계

### 4.1 포털 — `POST /auth/pat/exchange`(토큰 교환)

PAT 하나를 증거로 **같은 사람의 더 좁은 PAT** 를 받는다. 넓히는 일은 하지 않는다.

- **인증**은 `Authorization: Bearer <원 PAT>` 하나다(세션 쿠키 길은 받지 않는다 — 웹은 `/auth/pat` 가 있다).
- **원 PAT 의 조건**
  - `verify_pat` 를 지난다(aud `mcp-gateway`, `scope=api`, 폐기·만료 아님).
  - `token_store` 에 기록된 PAT 다. 사람이 토큰 화면에서 발급한 것만 해당하고, 챗 PAT·절차 PAT(기록되지 않음, `purpose` 있음)는 403 `source_not_exchangeable` 이다. 24시간짜리 챗 PAT 로 90일짜리를 받는 수명 늘리기를 막는다.
  - 계정이 살아 있고(`entitled`), `feat:api-token` 권한이 있다(`/auth/pat` 와 같은 문).
- **본문**은 `{name, audiences, scopes, ttl_days, min_remaining_s?}` 이고, 좁히기만 허용한다.
  - `audiences ⊆ 원 PAT 의 aud`, `scopes ⊆ 원 PAT 의 scopes`(원에 없으면 `["read","write"]` 로 본다).
  - `ttl_days` 는 1 ~ `pat_max_ttl_days`. 만료는 `min(지금 + ttl, 원 PAT 의 만료)` 이다.
  - 그 수명이 `min_remaining_s`(기본 0)보다 짧으면 서명 전에 400 `source_expiring` 이다(C-12).
  - 범위 이름은 `^[a-z][a-z0-9_-]{0,31}$` 다(400 `bad_scope`, C-15).
- **발급**은 `/auth/pat` 와 같은 클레임에 `par`(원 PAT 의 jti)를 더하고, 원장에 `parent_jti` 를 기록한다. 토큰 목록에 `parent_jti` 와 함께 보이고 폐기할 수 있다(C-14·C-15).
  - 같은 이름의 앞선 교환 PAT 는 **폐기하지 않는다.** 소비자가 새것을 받아들인 뒤 옛것으로 `POST /auth/pat/revoke-self` 를 불러 죽인다(C-11).
  - 원 하나의 살아 있는 교환 PAT 은 다섯까지다. 넘으면 409 `too_many_children` 이다(C-13).
  - 원 PAT 를 폐기하면 그 자식도 폐기한다(연쇄).
- **감사**는 `PAT exchanged: sub=… name=<repr> parent=… aud=… exp=…` 다.
- 응답 모양은 `/auth/pat` 와 같다(`token`·`jti`·`exp`·`parent_jti`…). 거절은 `{detail:{code, message}}` 이고, 글에 받은 값을 되싣지 않는다.
- **`POST /auth/pat/revoke-self`** 는 Bearer 토큰 그 자신(과 연쇄로 그 자식)만 폐기하고 `{"revoked": jti}` 다. 이미 폐기된 토큰도 200 이다(멱등). 원장에 없는 챗·절차 PAT 는 404 `not_recorded`, Bearer 가 없거나 틀리거나 만료면 401 `invalid_token` 이다(C-11).

### 4.2 게이트웨이 — 위임 단언을 받을 때 교환을 대신 걸어 준다

`per_user_sso` 항목에 선택 칸 `portal_pat_url` 을 더한다(hwax_risk 는 `…/apps/hwax_risk/api/auth/portal-pat`, `sso_url` 처럼 Caddy 경로). 단언 발급(`_mint_user_pat`)의 응답에 `portal_pat_wanted` 가 있으면 다음을 한다.

1. 지금 요청이 **포털 PAT 로 들어온 호출**인지 본다. GW_TOKEN 호출(에이전트 서버)은 하지 않는다 — 넘길 사람의 PAT 가 없다.
2. 포털 `POST /auth/pat/exchange` 를 **호출자의 Authorization 그대로** 부른다. 본문은 `portal_pat_wanted` 의 명세다.
3. 결과를 `portal_pat_url` 로 보낸다. 성공이면 `{pat}`, 실패면 `{error, message}` 이고, 헤더는 단언 발급과 같다(게이트웨이 비밀·위임 이메일·허브 토큰).

이 일은 **최선 노력**이다. 짧은 시간 한도를 두고, 실패해도 도구 호출은 그대로 간다. 감사 note 는 `portal-pat:registered` · `portal-pat:exchange-<code>` · `portal-pat:register-<status>` 다. 호출자의 PAT 는 포털에만 가고 리스크 앱에는 가지 않는다 — 리스크 앱은 좁힌 PAT 만 받는다.

`provision-config.sh` 가 hwax_risk 항목에 `portal_pat_url` 을 적는다.

### 4.3 리스크 앱

**자격 얻기(R1)**

- `POST /api/auth/sso`(위임 발급)는 위임 이메일의 등록 PAT 가 없거나·못 풀거나·폐기됐거나·남은 수명이 갱신 문턱 밑이면 `portal_pat_wanted: {name:"hwax-risk", audiences:["mcp-gateway"], scopes:["read"], ttl_days:90}` 를 싣는다. 사용자가 자동을 껐거나, 최근 실패의 쉼 시간 안이면 싣지 않는다.
- 새 `POST /api/auth/portal-pat` 는 게이트웨이 비밀과 위임 이메일로만 연다. `{pat}` 이면 `PUT /api/me/portal-pat` 와 같은 검사(이메일 일치·aud·scope·최소 수명·포털 확인·`['read']`)를 지나 등록하고, 출처를 `gateway-exchange` 로 적는다. `{error, message}` 이면 마지막 실패로 적는다.
- 새 살림 표 `_user_prefs(owner_sub, portal_pat_auto, auto_source, auto_at, auto_error, auto_error_at)` 를 둔다. 버전 밖이라 v5 가 필요 없다.
- `GET /api/me` 의 `portal_pat` 에 `auto{enabled, due, due_reason, last_source, last_at, last_error, last_error_at}` 를 더하고, `PUT /api/me/portal-pat-auto {enabled}` 를 둔다. 화면이 이 칸을 보고 자동 등록한다(U-2).
- 손잡이 `HWAXRISK_PAT_RENEW_BEFORE_S`(기본 7일)는 남은 수명이 이 밑이면 갱신이 필요하다는 뜻이다. `HWAXRISK_PAT_AUTO_RETRY_S`(기본 6시간)는 실패 뒤 다시 바라기까지의 쉼이다. 두 값의 관계는 기동 검사가 본다(갱신 문턱 > 패널 자격 여유).

**쓰기(U-3)**

- 패널 잡(`runner.resolve_credential_with_note`, `engine_client._credential`)은 서비스 PAT 로 내려가지 않는다. 요청자 → owner PAT 만 쓰고, 없으면 422 `pat_unavailable` 이다. 안내문은 '웹에서 앱을 한 번 열거나 Claude 에서 다시 부르면 자동으로 등록된다 · 설정에서 직접 등록할 수 있다 · 자동 실패 까닭' 이다.
- 이미 큐에 있는 패널 잡도 claim 때 같은 규칙으로 멈춘다(`rr_jobs.error`).
- 서비스 PAT 는 로스터·현장 VOC·캡처 MCP 폴백에만 남는다. 쓰이면 그 결과에 `credential: service` 를 남긴다(지금도 남기는 곳은 그대로, 없는 곳은 더한다).

**캡처 REST(R2)**

- 순서는 ① 웹 호출자의 heax 토큰(직접 `/apps/step_forge/api/…`) ② 위임 호출이고 사람 PAT 가 쓸 만하면 게이트웨이 REST(`{게이트웨이}/api/step-forge/api/…`, Bearer 사람 PAT) ③ 서비스 `HEAX_SERVICE_PAT` ④ 없음이다.
- `entry._credentials.capture_rest` 는 `caller_token · user_pat_gateway · service_pat · null` 이고, 안내문(`_rest_channel_absent`·`_fix_gate_blocked`)은 ② 를 먼저 말한다.

**RA 반영 안 됨(R3, U-4)**

- `external_sync` 요약 `{ra|adh: {state, pending_ops, reason, message}}` 를 과제·대상 응답, `risk_get_coverage`, `risk_next_step` 에 싣는다.
- `reason` 은 `sender_unwired`(보내는 쪽이 아직 없다 — M4)다. 나중에 배선되면 `credential_missing` 등이 붙는다.

**박스 자격(R5)**

- 필수 키는 `HWAXRISK_CRED_KEY` 하나다. 나머지 다섯은 선택이고, 각각 무엇이 안 되는지와 함께 적는다.
- `CRED_KEY` 의 출처는 `secrets · env · path · dev_fallback · absent` 이다. `dev_fallback`(`<data>/cred.key` 를 앱이 만든 것)이면 기동 로그와 설정 화면에 경고하고, **그 값을 그대로** `secrets.env` 로 옮기는 절차를 안내한다(새 키를 넣으면 등록된 PAT 가 안 풀린다).
- `GET /api/me` 의 `box` 에 `reasons[{code, keys?, message, fix}]` 를 더한다. 코드는 `host_mismatch · missing_required · cred_key_dev_fallback · missing_optional` 이다. `secrets_valid` 는 `host_mismatch`·`missing_required`·`cred_key_dev_fallback` 이 없을 때 참이다.

### 4.4 화면(HWAXRisk 화면 세션)

[frontend-request.md](frontend-request.md) — 자동 등록·끄기, 박스 자격 까닭별 문구, RA 상태 모양(백엔드는 객체, 화면은 문자열로 읽는 어긋남).

### 4.5 절차서

`docs/risk-review-redesign/server-setup-m1.md` 에 키 표(무엇·누구 명의·없으면 안 되는 것·이번 뒤)와 `cred.key` 옮기기를 넣는다. cae00 반영 절차는 [server-setup.md](server-setup.md)(구현 끝에 쓴다)다.

## 5. 하지 않는 것

- RA·AIDataHub 실제 쓰기 배선(M4).
- 포털에 '비밀만으로 아무 사람의 PAT 를 발급하는 길'(U-1 에서 택하지 않음).
- `scopes` 를 게이트웨이·포털이 실제로 강제하는 일(원-토큰 D-8 의 열린 항목 — 이 작업은 교환에서 좁히기만 지킨다).
- 화면 코드(U-2 — 요청서만).

## 6. 순서

| 단계 | 리포 | 무엇 | 확인 |
|---|---|---|---|
| P0 | 포털 | 이 문서들 | — |
| P1 | 포털 | 교환 끝점 + 폐기 연쇄 + 시험 → push(부르는 곳이 없어 동작 변화 없음) | 포털 시험 전체 |
| P2 | 리스크 앱 | R5 · U-3 · R2 · R3 보이기 · 자동 칸 · `/api/auth/portal-pat` · 단언의 `portal_pat_wanted` | 리스크 시험 전체·ruff |
| P3 | 게이트웨이 | `portal_pat_url` 처리 · provision-config | 게이트웨이 시험 |
| P4 | 셋 | 반대 검토 1라운드(보안 — 사칭·수명 늘리기·새는 토큰·조용한 강등) → 고침 | 재현 뒤 고침 |
| P5 | dev | 배포 → Claude(hwax MCP)로 `risk_next_step` → 교환 → 등록까지 실주행, 웹 PAT 없는 사람의 패널이 멈추는지 | 실호출 |
| P6 | 포털 | cae00 절차서 · 업데이트 이력 · push | — |
