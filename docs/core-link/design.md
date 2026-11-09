# core-link — 리포 사이 계약

> 이 문서가 정본이다. 결정 · 까닭은 [context-notes.md](context-notes.md)(CK-1 ~ CK-7), 요청서 원문은 [request.md](request.md)에 있다.
> 받는 리포 — 포털(§1 · §2 · §7) · 게이트웨이(§3 · §4 · §5) · StepForge(§6) · 에이전트 서버(§7) · KooRemapper(§8) · SignalForge(§9).
> 리포마다 자기 절만 지으면 맞물리게 썼다. 이름(헤더 · 청중 · 접두 · 칸)은 글자 그대로 쓴다.

## 0. 한눈에

| 길 | 누가 | 무엇을 | 거치는 곳 |
|---|---|---|---|
| 박스 훅(SRC-12) | update-all | `infra/hooks/post-update.d/*.local.sh` | 포털 리포 안 |
| 서비스 신원(SRC-13) | 박스 작업(훅 등) | 허용 목록 안의 도구 · REST 쓰기 | 포털이 발급한 서비스 PAT → 게이트웨이 |
| 사람 단언 쓰기(SRC-15) | 챗의 사람 | StepForge `POST /api/onto-*` | 게이트웨이 REST 다리 → 허브 Caddy → StepForge |
| 서비스 단언 쓰기(SRC-07) | 박스 작업 | StepForge 규칙 단 쓰기 | 같은 다리, 주체만 `system:<작업>` |

## 1. 박스 훅(SRC-12 — 포털)

- update-all 의 끝맺음 셋 뒤 · `hwax_skip_summary` 앞에서 `infra/hooks/post-update.d/*.local.sh` 를 C 차례로 `bash` 로 돌린다. 작업 폴더는
  포털 리포 루트이고 표준 입력은 `/dev/null` 이다. 환경에는 `HWAX_UPDATE_FAIL`(0 · 1)이 실린다.
- 훅마다 상한 `HWAX_HOOK_TIMEOUT_S`(기본 3600초)를 둔다. 넘기면 `HWAX_STEP_ID` 표식으로 남은 프로세스를 정리하고 실패로 센다.
- 실패는 종료코드에 넣지 않는다. 끝 요약의 따로 줄 하나로 낸다.
- `--hooks-when-idle` 이면 바쁘거나 셀 수 없을 때 ○ 로 건너뛴다. 셈은 다음 넷이다.
  - 에이전트 `/health` 의 `review_active` · `delib_active` · `delib_queued`
  - DynaForge 의 로컬 running
  - StepForge 의 pending · running
  - DocForge 의 queued · running
- 훅 파일은 `.gitignore` 로 지킨다. 이름이 `.local.sh` 로 끝나지 않는 `*.sh` 는 돌리지 않고 짚는다.

## 2. 서비스 PAT(SRC-13 — 포털이 발급)

포털의 PAT 서명 키(RS256)로 찍는 JWT 다. 패널 PAT(`backend/app/agent/panel_pat.py`)와 같은 모양 규칙을 따른다. 모듈은 표준 라이브러리만 쓴다 —
게이트웨이 계약 시험이 그대로 읽는다.

```
iss    포털 PAT 의 iss 그대로
aud    ["mcp-gateway-service"]              ← 새 청중. 포털 챗 · REST 프록시 · 그림 받기 · 옛 게이트웨이는 이 청중을 모른다
sub    "system:<작업>"                       ← <작업> 은 ^[a-z0-9][a-z0-9-]{0,39}$
scope  "api"
scopes ["service"]                            ← 읽기 전용 PAT 로 읽히지 않는다(read 가 없다)
purpose "service"
pat_name "service:<작업>"
jti    "svc-<uuid4 hex>"
iat · nbf · exp                               ← 수명 1 ~ 365일(0 · 무기한 없음)
(email · name · groups 칸 없음)
```

- 발급은 `POST /auth/pat/service` 로 한다. 본문은 `{"job": "<작업>", "days": 1..365, "note": "<선택, 200자>"}` 이다. 포털 관리자만 되고
  세션 + CSRF 가 필요하다. 응답은 `{"token", "jti", "job", "expires_at"}` 이고 토큰은 이때 한 번만 보인다.
- 목록은 `GET /auth/pat/service` 로 본다. 관리자만 되고, 칸은 `jti` · `job` · `note` · `issued_by` · `created_at` · `expires_at` · `revoked` 다.
  토큰 값은 없다.
- 회수는 기존 관리자 회수(`DELETE /auth/pat/{jti}`) → `revoked.json` 이다. 게이트웨이가 60초마다 읽는다.
- 토큰 원장 `record_pat` 에 남긴다. 새 칸 `issued_by` 는 발급한 관리자이고, 기존 ALTER 꼴로 더한다.
- 토큰 화면(`/tokens`)에는 관리자에게만 '서비스 토큰' 칸을 둔다. 발급 · 목록 · 회수를 하고 만료가 가까우면 표시한다.
- `/auth/pat/exchange` 는 이미 `purpose` 가 있는 원 토큰을 거절한다. 서비스 PAT 로 다른 PAT 를 바꿔 받을 수 없다.

## 3. 게이트웨이 — 서비스 신원(SRC-13)

- **검증.** 청중 `mcp-gateway-service` 를 bearer 문의 검증 목록에 더한다. 클레임은 `_service_scope` 가 모두 맞을 때만 받는다.
  `_panel_scope` 꼴로 purpose · jti 머리 · 청중 · sub 꼴 · scopes 를 보고, 하나라도 틀리면 401 이다. 회수는 기존 `revoked.json` 이다.
- **허용 목록.** 박스 파일 `service_tools.local.json`(게이트웨이 리포 루트, gitignore)이다. mtime 이 바뀌면 다시 읽는다
  (`read_tools.local.json` 꼴). 깨지면 통째로 버리고 모든 서비스 호출을 막는다.

  ```json
  {"jobs": {"core-link": {
      "tools": ["heax-step_forge:run_job", "heax-kooremapper_mcp:plan_task_links"],
      "rest":  [{"site": "step-forge", "method": "POST", "path": "/api/onto-link"}]}}}
  ```

  - `tools` 는 `백엔드:원래 이름` 이다. 집행이 이미 푸는 키다.
  - `rest` 는 사이트 · 메서드 · 경로가 글자 그대로 맞아야 한다(앞머리 맞춤 없음).
  - 파일에 없는 작업의 토큰은 문에서 **HTTP 403** 이다.
- **요청 신원.**
  - `x-hwax-user` 를 싣지 않는다. 사람 신원이 없다.
  - 게이트웨이 안쪽 머리 `x-hwax-service: <작업>` 를 싣는다. 클라이언트가 보낸 같은 머리는 두 벗기기 목록에서 지운다.
  - `via=service` 다. 그룹은 `gateway:service` 로 포털 접근 정책을 건너뛴다 — 울타리는 허용 목록이다.
- **집행.**
  - `tools/list` 는 그 작업의 `tools` 만 낸다. `rest` 가 있으면 `rest_call` 도 낸다.
  - `tools/call` 에서 목록 밖이면 MCP 오류 `forbidden: … service-denied` 와 감사 줄(`mode=refused`)이다.
  - `rest_call` 은 `rest` 항목과 맞을 때만 되고(§5), GET · HEAD 도 목록에 있어야 한다.
  - `invoke_tool` 을 거쳐도 같은 판정이다.
- **감사.** `caller` 는 `system:<작업>`, `note` 는 `svc:<jti 의 svc- 뒤 8자>`, `via` 는 `service` 다.
- **`/health`.** `service_jobs: {"<작업>": {"tools": N, "rest": M}}` 를 낸다. 토큰 · jti 는 싣지 않는다.
- **꼴 검사(검토 반영 — CK-11 · CK-13).**
  - 청중은 정확히 `{"mcp-gateway-service"}` 하나다.
  - '서비스 토큰이라 주장한다' 의 방아쇠는 purpose · 서비스 청중 · `system:` sub · `service` 범위다. jti 접두 `svc-` 는 꼴 검사에만 쓴다 —
    사람 PAT jti(`token_urlsafe`)가 그렇게 시작할 수 있다.
  - resources · prompts 는 내주지 않는다.
- **막는 백엔드.** 허용 목록에 넣어도 읽을 때 버리고(⚠), 부르면 `service-denied(<까닭>)` 이다.
  - RA · TestScope(`impersonation`) — 서비스 세션이 실제 사람의 토큰이다.
  - 신원을 넘기는 백엔드(`IDENTITY_FWD` — dev 는 `hwax-deliberation`, `identity-forward`) — 서비스 호출은 게이트웨이 공유 토큰의 내부 호출과
    같게 보여, 심의 엔진이 되부르는 지정 도구로 허용 목록을 벗어난다(검토 1차 major).
- **알려 둘 것.** 사람별 위임 앱(리스크 · MX 백서 · DynaForge · ste)은 신원이 없어 서비스 계정으로 불린다. 넣을지는 운영자가 허용 목록으로
  정한다.

## 4. 게이트웨이 — 쓰기 낱말(SRC-14)

- `_WRITE_NAME` 에 `link` · `edit` · `sync` 를 더한다.
- `read_tools.json` 의 `tools` 에 `heax-kooremapper_mcp:plan_task_links` · `ste:get_sync_settings` 를 더한다.

## 5. 게이트웨이 — REST 다리의 단언 쓰기(SRC-15 · SRC-07 운반)

- **설정.** provision 이 만든다.
  - `rest.step-forge` 는 지금 칸(`base` · `inject`)에 둘을 더한다. `"delegate": "step_forge"` 와
    `"write_paths": ["/api/onto-link", "/api/onto-put", "/api/onto-define"]` 이다. StepForge 가 서비스용 경로(§6)를 알리면 그것도 더한다.
  - 위임 발급 칸은 `per_user_sso` 와 **따로** 둔다(`rest_sso.step_forge`). 그래야 MCP 길이 지금 공유 세션 그대로다.
    칸은 `{"sso_url", "secret", "client": "gateway", "auth": "heax", "token_header": "X-Heax-Sso-Assertion"}` 다.
  - 박스 손잡이는 `STEPFORGE_SSO_SECRET` 이다(StepForge 의 `STEPFORGE_GATEWAY_SECRET` 과 같은 값). 주소 `STEPFORGE_SSO_URL` 은 선택이고,
    기본은 `<HEAX_MCP_BASE>/apps/step_forge/api/auth/sso` 다. 비밀이 비면 칸을 만들지 않는다. 그러면 쓰기는 거절하고 '켜려면' 을 안내한다.
- **집행.**
  - GET · HEAD 는 지금 그대로다(`inject` — 허브 서비스 토큰).
  - `write_paths` 에 든 경로의 POST 는 주체에 따라 갈린다.
    - 사람(PAT · 챗의 그 사람 이메일)은 사람 단언을 받아 싣는다.
    - 서비스(§3)는 그 작업의 `rest` 에 있을 때만 서비스 단언을 받아 싣는다.
    - 신원이 없으면(GW_TOKEN 만, 이메일 없음) **403** 이다.
  - 그 밖의 쓰기 메서드 · 경로는 **405** 다(지금 '쓰기 기본 닫힘' 을 경로까지 좁힌 것).
  - 읽기 전용 토큰 · 루틴은 지금처럼 `rest_call` 쓰기를 막는다.
  - 403 · 405 는 `rest_call` 결과 JSON 의 `status` 칸이다(MCP 도구라 HTTP 코드가 아니다). 문에서 모르는 작업의 거절만 진짜 HTTP 403 이다.
  - 맨 `/api/<사이트>/` 프록시는 StepForge 에 GET · HEAD 만 연다. 클라이언트가 보낸 `X-Heax-Sso-Assertion` · `X-Hwax-Delegate-*` 는 넘기지
    않는다.
- **운반.**
  - `Authorization: Bearer <허브 서비스 토큰>` 은 Caddy 문을 지나기 위한 것이다.
  - `X-Heax-Sso-Assertion: <단언>` 이 주체다.
  - 게이트웨이 표지 머리(`x-forwarded-user` 등)는 지금처럼 싣는다. StepForge 는 단언이 있으면 표지를 보지 않는다(§6).
- **발급 요청.** `POST <sso_url>` 이다. 머리는 `X-Heax-Gateway-Secret`, 주체 하나(`X-Hwax-Delegate-Email: <email>` 또는
  `X-Hwax-Delegate-Service: <작업>`), `X-Heax-Client`, Caddy 용 `Authorization` 이다.
  - 응답은 `{"token": "sfsso_…", "expires_in": N}` 이다.
  - 단언은 `sfsso_<b64url JSON 객체>.<서명>` 꼴이어야 하고, 주체 키는 `e` · `s` 가운데 정확히 하나가 있어야 하며 청한 것과 같아야 한다.
    어긋나면 발급 실패이고 캐시하지도 보내지도 않는다(`rrsso_` 접힘 검사와 같은 자세).
  - 주체마다 `expires_in − 60초` 까지 캐시한다. `expires_in` 이 60 이하거나 없으면 캐시하지 않는다. StepForge 가 쓰기에 401 · 403 으로 답하면
    그 단언을 버린다(다시 시도하지 않는다).
- **감사.** 사람이면 `caller` 는 그 이메일, 서비스면 `system:<작업>` 이다. 쓰기 경로 호출은 `note` 에 `rest:POST <경로>` 를 남긴다.

## 6. StepForge — 단언 발급 · 받기(SRC-15 앱 쪽 · SRC-07)

리스크 앱(HWAXRisk `backend/app/identity.py` 의 `mint_sso_assertion` · `_verify_sso_assertion`, `routes.py` 의 `POST /api/auth/sso`)을 그대로
본뜬다. 다른 것은 접두와 서비스 주체 둘이다.

- **발급 `POST /api/auth/sso`.** 허브 Caddy 뒤 `/apps/step_forge/api/auth/sso` 다.
  - 발급 비밀이 비면 404 다. 비밀 줄은 StepForge 데이터 폴더 `secrets.env` 의 새 줄 `STEPFORGE_SSO_SECRET` 을 제안했다(StepForge 세션 확인
    중). 기존 `STEPFORGE_GATEWAY_SECRET` 은 허브 `gateway_shared_secret` 과 같은 값이고, 있으면 포털 신원 요청마다 `X-Heax-Gateway-Secret`
    을 요구한다. 그래서 위임을 켜려고 그 줄을 넣으면 웹 화면 적용이 깨질 수 있다.
  - `X-Heax-Gateway-Secret` 이 그 값과 같아야 한다(상수 시간 비교). 아니면 403 이다.
  - 주체는 정확히 하나다. 둘 다 있거나 둘 다 없으면 400 이다.
    - `X-Hwax-Delegate-Email` — `@` 가 든 이메일, 소문자로 둔다.
    - `X-Hwax-Delegate-Service` — `^[a-z0-9][a-z0-9-]{0,39}$`.
  - 200 `{"token": "sfsso_<b64u(JSON)>.<b64u(HMAC-SHA256(비밀, b64u(JSON)))>", "expires_in": ttl}` 이다.
    - JSON 은 사람이면 `{"e": <email>, "x": <만료 epoch>, "d": 1}`, 서비스면 `{"s": <작업>, "x": …, "d": 1}` 이다.
    - ttl 은 60 ~ 3600초다.
  - 저장하지 않는다(무상태).
- **받기.** `admins.caller()` · R2 판정이다.
  - `X-Heax-Sso-Assertion` 이 있으면 검증한다. 접두 · 서명 · 만료를 보고, 사람이면 `@` 를 본다.
    - 사람 단언이 맞으면 그 이메일이 신원이다. 이것으로 R2(`portal_identity_apply`)를 통과한다 — 게이트웨이 표지 머리가 있어도 된다.
      권한은 그 사람의 StepForge 권한 그대로다.
    - 서비스 단언이 맞으면 신원은 `system:<작업>` 이다. StepForge 가 정한 **서비스 허용 작업**만 받는다.
      - 받는 것은 규칙 단 `onto_link` 적용(출처 `rule`)과 `onto_fill` 잡이다.
      - `confirm` · `reject` · 규칙 단 아닌 적용 · 정의(`onto_define`) · `onto_put` 은 `identity_refused: service_not_allowed` 다.
    - 단언이 있는데 틀리거나 만료됐으면 `identity_refused: assertion_invalid` 다. 다른 신원으로 내려가지 않는다.
  - 단언이 없으면 지금 규칙 그대로다(`gateway_marked` 등).
- **알려 줄 것.** 서비스 허용 작업의 REST 경로를 포털 세션에 알린다. `onto_fill` 잡을 거는 REST 끝점이 없으면 둔다. 게이트웨이
  `write_paths` 와 운영 허용 목록 예시에 그대로 쓴다.
- **기록.** 적용 · 잡의 행위자 칸에 이메일 또는 `system:<작업>` 을 남긴다.
- MCP 길은 그대로 둔다. 신원이 없고 미리 보기만 된다.

## 7. 에이전트 서버 · 포털 운영자 정의(SRC-15 챗 쪽)

- **확인 관문(HA-29).** `rest_call` 의 `method` 가 GET · HEAD 가 아니면(대소문자 무시) 운영자 목록과 상관없이 늘 확인 카드다(`confirm`
  부류). 카드는 승인이 실제로 보낼 인자 그대로 그린다(다듬지 않는다). 사이트 · 메서드 · 경로 · query · 본문을 칸마다 JSON 으로 싣고, 칸마다
  400자에서 자른다. 값 안의 구분자로 칸을 지어낼 수 없다.
- **챗 밖의 쓰기는 막는다(검토 1차).** 심의 · 리스크 패널의 지정 도구, 좌석 자유 조회, 외부 응답자의 `CALL` 줄이 부르는 `rest_call` 이 쓰기
  메서드면 엔진이 보내기 전에 거절한다(`rest_write_refused` 경고 · 끝 카드). 확인 카드가 서는 곳은 챗 턴뿐이다. 그래서 챗 모델이 심의에 지정
  도구로 `rest_call` 을 넣어도 쓰기는 나가지 않는다.
- StepForge 운영자(`he-cad-stepforge`)를 고른 챗에서 `rest_call` 이 묶여야 한다. 지금 묶이지 않으면 묶는다.
- **포털 `infra/personas/he-team.json` 의 `he-cad-stepforge`.** `can` · `pitfalls` 에 한 줄씩 더한다.
  - 미리 보기는 MCP `onto_link` · `onto_put` · `onto_define`(`dry_run=true`)로 한다.
  - 적용은 `rest_call(site="step-forge", method="POST", path="/api/onto-link", body=<미리 보기와 같은 인자, dry_run=false>)` 이고 확인
    카드가 선다. MCP 로 `dry_run=false` 를 부르면 `identity_refused` 다.

## 8. KooRemapper(DynaForge) — SRC-08 ~ 11

요청서 3-2절 그대로다. 사용자 결정 Q-5 는 다리 셋 다다 — `cae_part` → `part` · `cae_finding` → `failure_mode` · `cae_campaign` →
`analysis_method`.

- 이름 · 별칭이 하나로 맞을 때만 `rule` 선으로 잇고, 나머지는 후보다.
- 다시 반입해도 사람 선은 남는다.
- 다리는 자체 정의(`dynaforge-core.json`)에 둔다. 바이트 사본인 정본 어휘는 고치지 않는다.

## 9. SignalForge — 코어와 잇기(Q-2 다시 엶)

- 대응표는 둘이다. VOC 부품 16 → 코어 `part` key 이고, 증상 32 → 코어 `failure_mode` key 다.
- 초안은 SignalForge 가 내고 cae00 운영 사용자가 확인한다(BOX-12 와 같은 꼴). 코어에 맞는 것이 없으면 비우고 까닭을 단다.
- 뼈대 규칙은 요청서와 같다. 정확 일치(키 · 별칭이 하나로 정해지는 것)만 `rule` 선이고, 짐작은 후보로만 낸다. 다시 지을 때는 `rule` 선만
  지우고 사람 선은 둔다.

## 10. 순서와 보류(CK-7)

1. 여섯 리포 모두 **가지에서** 짓고 시험한다. main 에는 cae00 이 11-08 · 11-09 라운드 update-all 을 끝냈다고 사용자가 알린 뒤에 올린다.
2. 맞물림 시험은 다음 셋이다.
   - 포털 서비스 PAT 클레임 ↔ 게이트웨이 `_service_scope`(두 리포 계약 시험 — 패널 PAT 처럼 게이트웨이 시험이 포털 모듈을 읽는다).
   - 게이트웨이 단언 쓰기 ↔ StepForge 발급 · 받기(가짜 StepForge 로 게이트웨이 시험, 진짜는 dev 허브에서 올린 뒤).
   - 에이전트 관문 ↔ `rest_call`.
3. 올린 뒤 cae00 은 다음 차례로 간다. BOX-10(업데이트) → BOX-11(서비스 토큰 발급 · `service_tools.local.json`) → BOX-12 ~ 14 →
   BOX-15(훅) → BOX-16. Q-4 결정으로 두 인스턴스를 같은 때에 한다.
