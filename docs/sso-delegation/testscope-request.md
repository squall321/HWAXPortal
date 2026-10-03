# TestScope — (선택) 포털 로그인 그대로 연결하기: `POST /api/auth/sso`

> 대상: TestScope 개발 담당 · 2026-10-03 · 보낸 쪽: HWAX 포털(`docs/sso-delegation/`)
> **지금은 아무것도 안 해도 됩니다.** HWAX 포털은 TestScope 를 **토큰 등록** 방식으로 붙입니다 — 사람마다 TestScope 에서 개인 토큰(`tsc_pat_…`)을
> 발급해 포털에 등록하면, 포털 AI(Claude·챗)가 그 토큰으로 TestScope 를 그 사람 명의로 부릅니다. TestScope 코드 수정은 필요 없습니다.
> 아래는 **사람이 토큰을 등록하는 수고까지 없애고 싶을 때만** 넣는 엔드포인트입니다(포털이 ste·HWAX Risk 에 쓰는 것과 같은 계약).

## 무엇이 달라지나

| | 토큰 등록(지금) | `/api/auth/sso` 를 넣은 뒤 |
|---|---|---|
| 사람이 할 일 | TestScope 에서 토큰 발급 → 포털에 붙여 넣기(만료되면 다시) | 없음 — 포털에 로그인돼 있으면 된다 |
| TestScope 가 할 일 | 없음 | 아래 엔드포인트 하나 + 비밀 하나 |
| 포털·게이트웨이 | 준비돼 있음 | 준비돼 있음(포털 운영자가 비밀 한 줄 넣고 update-all) |

## 계약 — `POST /api/auth/sso`(서버 간, 포털 게이트웨이가 부른다)

| | 내용 |
|---|---|
| 요청 헤더 | `X-Heax-Gateway-Secret`(TestScope 전용 공유 비밀) · `X-Heax-User-Email`(필수 — 포털이 인증한 사람) · `X-Heax-User-Name`(선택, **퍼센트 인코딩** — 한글 이름) · `X-Heax-Client`(`gateway`) |
| 응답 200 | `{"access_token": "<tsc_pat_…>", "token_type": "bearer", "expires_in": <그 토큰 만료까지 초>}` — 게이트웨이는 응답 안 `access_token` 을 찾아 쓰고 `expires_in` 보다 일찍 다시 받는다 |
| 오류 | 비밀이 비어 있으면 **404**(꺼짐) · 비밀 불일치 401 · 대기·정지·삭제 계정 403 · 이메일 없음 400 |
| 설정 | `HEAX_SSO_SECRET`(빈 값 = 꺼짐, 32자 이상 권장) · (선택) JIT 여부·토큰 범위·수명 |
| 함께 오는 헤더 | 위임으로 부르는 호출에는 그 사람 소속(`X-Heax-User-Affiliation`, 증명 `X-Heax-Aff-Proof` = 같은 비밀의 HMAC)도 실린다 — 쓰지 않으면 무시하면 된다 |

권하는 구현(TestScope 의 규칙에 맞춘 것 — 결정은 그쪽 몫):
- **사람 세션이 아니라 기계 자격(PAT)** 을 내주면 TestScope ADR 0009(PAT 로 들어온 쓰기는 '후보')가 AI 의 쓰기에도 그대로 걸립니다.
  기존 PAT 발급 서비스를 서버 안에서 부르면 됩니다(지금 PAT 로는 PAT 를 못 만드는 규칙 TSC-AUTH-0105 는 그대로 둬도 됩니다 — 이건 서버 안 호출이다).
- 토큰 이름 예 `HWAX 게이트웨이(gateway)`, 수명 1일 정도(게이트웨이가 최대 12시간 쓴다), 범위는 read·equipment:write·catalog:write 중 그쪽이 정한 것.
  **발급할 때 같은 이름의 직전 토큰을 회수**하면 토큰이 쌓이지 않습니다.
- 사람 찾기는 이메일(소문자). 없는 사람을 만들지(JIT) 말지는 그쪽 판단 — 만들지 않으면 403 으로 분명히.
- 비밀 비교는 상수 시간, 비밀·토큰은 로그에 남기지 않기.

## 켜는 순서

1. TestScope 에 위 엔드포인트를 넣고 `HEAX_SSO_SECRET` 설정.
2. 비밀은 **포털 운영자가 만들어 한 번 전달**합니다(`openssl rand -hex 32`) — 받은 값을 `HEAX_SSO_SECRET` 에, 포털은 같은 값을 `infra/.env` 의 `TESTSCOPE_SSO_SECRET` 에.
3. 포털 운영자가 update-all — 그때부터 포털 '외부 연결' 의 TestScope 카드가 '포털 로그인으로 본인 명의 — 등록할 것 없음' 으로 바뀝니다.

확인: 비밀 없이 POST → 404 · 틀린 비밀 → 401 · 맞는 비밀 + 이메일 → 200 `access_token`, 그 토큰으로 `GET /api/auth/me` 가 그 사람.
되돌리기: 포털 `TESTSCOPE_SSO_SECRET` 을 비우고 update-all 하면 토큰 등록 방식으로 돌아갑니다(게이트웨이 위임도 함께 지워집니다).
