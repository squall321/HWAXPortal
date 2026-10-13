# 화면 요청서 — 리스크 앱 사람 자격(HWAXRisk `frontend/` 세션에)

보내는 쪽: 백엔드 세션(포털 리포 `docs/risk-credentials/`) · 2026-10-14 · 계획은 [PLAN.md](PLAN.md) 4.4. 백엔드 칸이 들어간 커밋은 이 문서 끝의 '반영' 에 적는다.

## 1. PAT 자동 등록·갱신

**왜.** 지금은 사람이 설정에서 「포털에서 발급해 등록」을 눌러야 그 사람 자격으로 잡이 돈다. 이제 패널 잡도 서비스 계정으로 내려가지 않으므로(사용자 결정 U-3), 누르지 않은 사람의 잡은 시작하지 못한다.

**백엔드가 주는 것.** `GET /api/me` 의 `portal_pat.auto` 다.

```text
auto: {
  enabled: bool,          // 사용자가 끄지 않았다
  due: bool,              // 지금 발급해 등록해야 한다(없음·못 풂·폐기·남은 수명이 갱신 문턱 밑)
  due_reason: "absent" | "undecryptable" | "revoked" | "expiring" | null,
  last_source: "web" | "gateway-exchange" | "manual" | null,
  last_at: epoch | null,
  last_error: string | null, last_error_at: epoch | null
}
```

끄기·켜기는 `PUT /api/me/portal-pat-auto {enabled: bool}` 이다.

**할 일**
- 앱 화면이 처음 뜰 때(로그인된 사용자) `auto.enabled && auto.due` 이면, 지금 버튼이 하는 일(`api/portalPat.ts` — `/auth/pat` 발급 → `PUT /api/me/portal-pat`)을 **조용히** 한 번 한다. 등록 요청에는 `source: "web"` 을 싣는다(백엔드가 받는 선택 칸).
- 발급 청중을 `["mcp-gateway", "step-forge"]` 로 바꾼다(지금 `portalPat.ts` 는 `mcp-gateway` 하나다). 위임 캡처의 REST 다리(게이트웨이 `/api/step-forge`)가 PAT 의 aud 에 `step-forge` 를 요구한다(context-notes C-10). 손 버튼도 같은 청중으로 바꾼다.
- 실패하면 막지 말고 알림 한 줄을 띄운다(`portalPat.ts` 의 지금 오류 문구 — 세션 없음·`feat:api-token` 없음·로그인 만료). 같은 세션에서 되풀이하지 않는다.
- 설정 화면에 '자동 등록' 스위치(`auto.enabled`)를 두고, `last_source`·`last_at`·`last_error` 를 보인다.

## 2. 박스 자격 문구

**왜.** 지금 화면은 `box.secrets_valid=false` 면 무조건 「저장된 비밀이 이 호스트에서 풀리지 않습니다」라고 한다. cae00 운영자는 이것을 이관 문제로 읽었지만 실제 까닭은 빠진 키·`cred.key` 폴백이었다.

**백엔드가 주는 것.** `GET /api/me` 의 `box.reasons[]` 다.

```text
reasons: [{ code: "host_mismatch" | "missing_required" | "cred_key_dev_fallback" | "missing_optional",
            keys?: string[], message: string, fix: string }]
cred_key_source: "secrets" | "env" | "path" | "dev_fallback" | "absent"
```

**할 일**
- 고정 문구 대신 `reasons` 의 `message`·`fix` 를 그대로 보인다(설정 `SettingsPage.tsx` 의 Banner, 홈 `RiskHomePage.tsx` 의 Banner).
- `missing_optional` 은 경고가 아니라 정보로 보인다(앱은 돈다). `secrets_valid` 는 그대로 쓰되 그 뜻이 '필수가 갖춰졌다' 로 바뀌었다.

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
  - 등록 삭제(`PUT /api/me/portal-pat {pat: null}`)는 자동 스위치를 바꾸지 않는다. 자동이 켜져 있으면 다음에 앱을 열 때 다시 등록된다 — 지운 채 두려는 사람에게는 자동도 함께 끄게 해 주십시오.
  - `box.reasons[].keys` 는 `missing_required`·`cred_key_dev_fallback`·`missing_optional` 에만 있다(`host_mismatch` 에는 없다).
  - `external_sync.<채널>.pending_ops` 는 **건수(정수)**다. op 목록은 `GET /api/reports` 의 `ra_state`·재동기 응답이 지금처럼 준다.
  - `external_sync` 가 실리는 곳은 `GET /api/projects/{id}` 의 `targets[]` 각 항목, `GET /api/targets` 의 각 항목, `GET /api/targets/{key}/coverage` 다.
