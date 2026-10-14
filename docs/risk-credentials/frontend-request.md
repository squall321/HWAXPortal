# 화면 요청서 — 리스크 앱 사람 자격(HWAXRisk `frontend/` 세션에)

보내는 쪽: 백엔드 세션(포털 리포 `docs/risk-credentials/`) · 2026-10-14 · 계획은 [PLAN.md](PLAN.md) 4.4. 백엔드 칸이 들어간 커밋은 이 문서 끝의 '반영' 에 적는다.

## 1. PAT 자동 등록·갱신

**왜.** 지금은 사람이 설정에서 「포털에서 발급해 등록」을 눌러야 그 사람 자격으로 잡이 돈다. 이제 패널 잡도 서비스 계정으로 내려가지 않으므로(사용자 결정 U-3), 누르지 않은 사람의 잡은 시작하지 못한다.

**백엔드가 주는 것.** `GET /api/me` 의 `portal_pat.auto` 다.

```text
auto: {
  enabled: bool,          // 사용자가 끄지 않았다
  due: bool,              // 지금 발급해 등록해야 한다(없음·폐기·못 풂·남은 수명이 갱신 문턱 밑·청중 모자람)
  due_reason: "absent" | "revoked" | "undecryptable" | "expiring" | "audience" | null,   // 앞의 것이 먼저다
  last_source: "web" | "gateway-exchange" | "manual" | null,
  last_at: epoch | null,
  last_error: string | null,                        // "<code>: <앱이 고른 글>" — 할 일을 말한다
  last_error_kind: "transient" | "final" | null,    // transient 는 앱이 10분 뒤 다시 바란다(gateway_misconfigured 포함)
  last_error_at: epoch | null,
  how_to_stop: string | null                        // 켜져 있을 때만 — 지우거나 폐기해도 다시 만들어지니 멈추려면 끈다
}                                                   // (스위치가 화면에 생기기 전이라 지금 글은 '곧 생긴다 — 그때까지는 운영자가
                                                    //  앱 데이터 DB 에서 끈다, 포털 docs/risk-review-redesign/server-setup-m1.md §7-2' 다)
```

끄기·켜기는 `PUT /api/me/portal-pat-auto {enabled: bool}` 이다. 꺼져 있던 것을 켜면 마지막 자동 실패와 그 쉼을 지운다(답의 `last_error`·`last_error_kind`·`last_error_at` 이 `null` 이 되고 곧바로 다시 바란다).

**할 일**
- 앱 화면이 처음 뜰 때(로그인된 사용자) `auto.enabled && auto.due` 이면, 지금 버튼이 하는 일(`api/portalPat.ts` — `/auth/pat` 발급 → `PUT /api/me/portal-pat`)을 **조용히** 한 번 한다. 등록 요청에는 `source: "web"` 을 싣는다(백엔드가 받는 선택 칸).
- 발급 청중을 `["mcp-gateway", "step-forge"]` 로 바꾼다(지금 `portalPat.ts` 는 `mcp-gateway` 하나다). 위임 캡처의 REST 다리(게이트웨이 `/api/step-forge`)가 PAT 의 aud 에 `step-forge` 를 요구한다(context-notes C-10). 손 버튼도 같은 청중으로 바꾼다.
- 실패하면 막지 말고 알림 한 줄을 띄운다(`portalPat.ts` 의 지금 오류 문구 — 세션 없음·`feat:api-token` 없음·로그인 만료). 같은 세션에서 되풀이하지 않는다.
- 설정 화면에 '자동 등록' 스위치(`auto.enabled`)를 두고, `last_source`·`last_at`·`last_error` 를 보인다. 스위치 옆에 `how_to_stop` 을 보인다.
- `due_reason: "audience"` 는 등록된 PAT 에 `step-forge` 청중이 없다는 뜻이다(위임 캡처의 REST 다리가 닫힌다). 화면은 `due` 를 보고 지금처럼 두 청중으로 새로 발급해 등록하면 된다.
- **설정의 「포털에서 발급해 등록」 버튼도 `source: "web"` 을 싣는다.** 지금은 아무것도 싣지 않아 `manual` 로 적힌다. 백엔드는 갈아 끼울 때 앞선 등록의 출처가 `web`·`gateway-exchange`(앱이 받아 온 것)일 때만 옛 PAT 를 폐기하므로, 버튼으로 낸 PAT 가 `manual` 로 적히면 다음 갱신 때 폐기되지 않고 쌓인다. 사람이 PAT 를 손으로 붙여 넣는 칸은 지금처럼 `source` 없이(= `manual`) 보낸다 — 그 PAT 는 그 사람의 Claude PAT 일 수 있어 폐기하지 않는다(폐기하면 Claude 길과 그 자식들까지 죽는다).
- 새 PAT 를 등록하면 백엔드가 앞서 등록돼 있던 `hwax-risk` 이름의 PAT 를 포털에서 폐기한다 — 앞선 등록의 출처가 `web`·`gateway-exchange` 일 때만이다(`/auth/pat/revoke-self` — 응답을 보낸 뒤 최선 노력). 화면이 옛 PAT 를 따로 폐기할 필요는 없고, 발급 이름은 `hwax-risk` 그대로 둔다(다른 이름의 PAT 는 폐기하지 않는다).
- 자동 등록 스위치를 내보내면 백엔드 세션에 알려 주십시오. `how_to_stop`·`pat_unavailable` 안내의 '곧 생긴다 — 그때까지는 운영자가 앱 데이터 DB 에서 끈다(켠다), 포털 …server-setup-m1.md §7-2' 꼬리를 뗀다. 웹 자동 등록을 내보낼 때도 같다 — 지금 안내는 '웹에서 앱을 열면 자동 등록' 을 말하지 않는다.

## 2. 박스 자격 문구

**왜.** 지금 화면은 `box.secrets_valid=false` 면 무조건 「저장된 비밀이 이 호스트에서 풀리지 않습니다」라고 한다. cae00 운영자는 이것을 이관 문제로 읽었지만 실제 까닭은 빠진 키·`cred.key` 폴백이었다.

**백엔드가 주는 것.** `GET /api/me` 의 `box.reasons[]` 다.

```text
reasons: [{ code: "host_mismatch" | "missing_required" | "cred_key_invalid" | "cred_key_dev_fallback"
                  | "cred_key_path_missing" | "missing_optional",
            keys?: string[], message: string, fix: string }]
cred_key_source: "secrets" | "env" | "path" | "dev_fallback" | "absent"
```

**할 일**
- 고정 문구 대신 `reasons` 의 `message`·`fix` 를 그대로 보인다(설정 `SettingsPage.tsx` 의 Banner, 홈 `RiskHomePage.tsx` 의 Banner).
- `missing_optional` 은 경고가 아니라 정보로 보인다(앱은 돈다). `secrets_valid` 는 그대로 쓰되 그 뜻이 '필수가 갖춰졌다' 로 바뀌었다.
- `secrets_valid` 를 거짓으로 만드는 code 는 `host_mismatch`·`missing_required`·`cred_key_invalid`(키가 Fernet 키 형식이 아니다)·`cred_key_dev_fallback` 이다. `cred_key_path_missing`(HWAXRISK_CRED_KEY_PATH 가 가리키는 파일이 없다)은 경고로 보이되 그것만으로는 막지 않는다.
- `fix` 의 셸 명령은 백틱 하나로 감싼 한 줄이다(데이터 디렉터리에서 돈다). 복사하기 쉽게 코드 모양으로 보여 주십시오. 글에는 절대경로가 없다 — 경로는 관리자용 `GET /api/meta/runtime` 의 `data_dir` 이다.
- **익명**에게는 `box` 가 `{hostname, secrets_valid, cred_key_present, portal_base, reasons: [{code}]}` 다. 앞의 넷은 이 작업 전부터 공개였고 지금 화면이 그대로 읽는다. 까닭의 `message`·`fix`·`keys` 와 `cred_key_source` 는 싣지 않는다 — 익명 화면은 `message`·`fix` 를 기대하지 않는다.

## 3. RA 상태 모양 어긋남(지금 있는 결함)

- 백엔드의 `GET /api/reports` 의 `ra_state` 와 `POST /targets/{key}/resync` 는 **객체** `{state, attempts, next_at, last_error, done_at, pending_ops[]}` 를 준다. 화면의 타입(`types.ts` 44-45·797)은 문자열 `"pending"|"done"|"unavailable"` 로 읽는다.
- 홈 배지는 `"synced"` 를 찾지만 백엔드의 값은 `"done"` 이다.
- 이번 작업으로 과제·대상 응답에 `external_sync{ra|adh: {state, pending_ops, reason, message}}` 요약이 생긴다. 지금은 `reason: "sender_unwired"`(RA 로 보내는 쪽이 아직 없다 — M4)다. 그 `message` 를 '재동기' 를 누르기 전에도 보이게 해 주십시오.

## 반영

- 백엔드 칸이 들어간 커밋 — HWAXRisk 브랜치 `creds`(2026-10-14, 아직 push·main 합침 전).
  - `8d672c7` 박스 자격(R5) — `box.reasons[]`·`box.cred_key_source`.
  - `491895c` 자동 등록(R1) — `portal_pat.auto`·`PUT /api/me/portal-pat-auto`·`PUT /api/me/portal-pat` 의 `source`.
  - `5d47690` 패널 자격(U-3) — 사람 PAT 가 없으면 잡 만들기가 422 `pat_unavailable` 이고, `message` 가 자동 등록 길과 마지막 자동 등록 실패를 말한다.
  - `0e65f3a` 캡처 REST(R2) — 캡처 응답의 `credentials{mcp, rest}`.
  - `0966b41` RA 반영 요약(R3) — `external_sync{ra|adh}`.
- 위 1~3절과 다르거나 더해진 것이다.
  - `portal_pat` 은 로그인한 사람에게 **늘 객체**다. 등록이 없으면 `{registered: false, email: null, groups: [], exp: null, auto}` 이다(`auto` 를 싣기 위해서다). 익명과 박스 불일치(이관 직후)는 종전처럼 `null` 이다.
  - `PUT /api/me/portal-pat-auto` 의 답은 `portal_pat.auto` 와 같은 꼴의 객체 하나다.
  - `source` 는 `web`·`manual` 만 받는다(그 밖은 422 `E100`). `last_source` 의 `gateway-exchange` 는 게이트웨이 길로만 적힌다.
  - 등록 삭제(`PUT /api/me/portal-pat {pat: null}`)는 자동 스위치를 바꾸지 않는다. 자동이 켜져 있으면 다음에 앱을 열 때 다시 등록된다 — 지운 채 두려는 사람에게는 자동도 함께 끄게 해 주십시오. 지운 PAT 가 앱이 받아 온 `hwax-risk` PAT(앞선 출처 `web`·`gateway-exchange`)면 백엔드가 응답 뒤 포털에서도 폐기한다(3라운드) — 화면이 따로 폐기할 필요는 없다.
  - `box.reasons[].keys` 는 `missing_required`·`cred_key_dev_fallback`·`missing_optional` 에만 있다(`host_mismatch` 에는 없다).
  - `external_sync.<채널>.pending_ops` 는 **건수(정수)**다. op 목록은 `GET /api/reports` 의 `ra_state`·재동기 응답이 지금처럼 준다.
  - `external_sync` 가 실리는 곳은 `GET /api/projects/{id}` 의 `targets[]` 각 항목, `GET /api/targets` 의 각 항목, `GET /api/targets/{key}/coverage` 다.
- 고침 1라운드(2026-10-14, 같은 브랜치 `creds`)로 바뀐 칸이다. 위 1·2절에 반영했다.
  - `portal_pat.auto` — `due_reason` 에 `audience`, 새 칸 `last_error_kind`·`how_to_stop`. `last_error` 는 이제 게이트웨이가 보낸 글이 아니라 앱이 고른 `"<code>: <글>"` 이다.
  - `box` — 익명은 `{secrets_valid, reasons[{code}]}` 만(2라운드에서 공개 칸 셋을 되돌렸다 — 아래). reason code `cred_key_invalid`·`cred_key_path_missing` 이 더해졌다. `GET /api/meta/runtime` 에 `data_dir`.
  - 캡처 응답 `credentials.rest` 는 게이트웨이 다리가 실패해 서비스 PAT 로 넘어갔으면 `"user_pat_gateway→service_pat"` 이고, 다리가 실패했으면 `credentials.rest_bridge{http_status, error}` 가 함께 있다.
- 고침 2라운드(2026-10-14, 같은 브랜치 `creds`, `b7c008d`~`e34a0a6`)로 바뀐 칸이다. 위 1·2절에 반영했다.
  - `box`(`aaf0650`) — 익명에게 `hostname`·`cred_key_present`·`portal_base` 를 되돌렸다. 1라운드가 이것을 빼자 지금 `SettingsPage` 가 익명에게 빨간 'cred_key: absent' 배지와 빈 호스트 이름을 띄웠다(`types.ts` 는 `hostname` 을 요구한다). `reasons` 는 그대로 code 만이다.
  - 캡처 응답(`c783cc9`) — `credentials.rest_ok: bool` 을 더했다. REST 호출이 하나 이상 있었고 전부 읽혔으면 참이다(어느 자격으로든). 서비스 PAT 가 없는 박스에서는 `credentials.rest` 가 다리가 읽었든 못 읽었든 `"user_pat_gateway"` 라 이것으로 가른다. REST 를 부르지 않은 캡처도 거짓이다.
  - 등록 출처(`b4d82bd`) — 설정 버튼은 `source: "web"` 을 싣는다(1절). 지금 버튼은 싣지 않아 `manual` 이다.
  - 안내 글(`10be03b`) — `how_to_stop` 과 `pat_unavailable` 의 `message` 는 지금 있는 길만 말한다. 등록은 Claude 에서 hwax_risk 도구를 부르기와 이 버튼이고, 멈추기는 곧 생길 스위치(그때까지는 운영자가 `PUT /api/me/portal-pat-auto`)다.
  - 바뀌지 않은 것 — 웹 `PUT /api/me/portal-pat` 는 포털에 못 닿으면 종전처럼 502 `portal_unreachable` 이다. 424 는 게이트웨이 전용 문(`POST /api/auth/portal-pat`)만이다.
- 고침 3라운드(2026-10-14, 같은 브랜치 `creds`, `99e9b84`~`3aea93b`)로 바뀐 칸이다. 위 1절에 반영했다.
  - `last_error_kind`(`99e9b84`) — 게이트웨이 설정 결함 `gateway_misconfigured` 가 `final` 에서 `transient` 로 바뀌었다(운영자가 게이트웨이를 고치면 10분 안에 다시 바란다).
  - `PUT /api/me/portal-pat-auto`(`11a93bf`) — 꺼져 있던 것을 켜면 답의 `last_error`·`last_error_kind`·`last_error_at` 이 `null` 이다. 켜져 있는 채 다시 켜면 그대로다.
  - 등록 삭제(`1bfc1d8`) — 응답 모양은 그대로이고, 앱이 받아 온 `hwax-risk` PAT 면 응답 뒤 포털에서 폐기한다.
  - 안내 글(`3aea93b`) — `how_to_stop` 과 `pat_unavailable` 의 `message` 에서 '운영자가 그 사람으로 `PUT /api/me/portal-pat-auto`' 를 뺐다(운영자가 그 사람으로 부를 길이 없다). 이제 '운영자가 앱 데이터 DB 에서 끈다(켠다), 포털 docs/risk-review-redesign/server-setup-m1.md §7-2' 다.
  - 캡처 호출 행(`eaad8f5`·`b99d5f9`) — 화면 칸은 그대로다. 게이트웨이 504 하나로는 다리를 건너뛰지 않고, 호출 행의 '120초 동안 응답이 없었다' 는 그 호출 자신의 시간 초과일 때만이다.
