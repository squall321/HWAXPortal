# 컨텍스트 노트 — 토큰 하나 · REST→MCP

왜 그렇게 했는지. 결론만 보면 다시 같은 판단을 내리느라 시간을 쓴다.

## D-1. "포털 토큰은 MCP 전용" 이 **틀린 전제였다**

백엔드는 처음부터 다중 청중이다(`pat.py` `"aud": audiences  # array`), 게이트웨이에는 그 PAT 로
인증하는 REST 프록시가 **살아서 공개 오리진에 열려 있었다**(`rest_proxy.py`, `/mcp-gw/api/<site>/<path>`).
막고 있던 것은 화면 한 줄이다 — `TokenPage.tsx` 가 `audiences: ['mcp-gateway']` 를 박아 보냈다.

설정은 맞는데 **화면이 덮는** 모양이라 서버만 보면 원인이 안 잡힌다. 그래서 고칠 때 목록을
화면에 다시 적지 않고 **아예 안 보내게** 했다 — 서버가 사이트를 늘리면 화면은 가만히 있어도 따라온다.
`test_pat_one_token.py` 가 화면에 `audiences` 가 다시 생기면 깨진다.

## D-2. `aud` 에 `apps` 를 추가하는 처방은 **구현이 불가능하다**

다른 세션이 전달한 처방이었는데 실측으로 기각했다. `/apps/*` 게이트는 포털이 아니라 HEAXHub
자신의 forward_auth(`/api/v1/authz`)이고, 그 코드는 자기 HS256 토큰 또는 `heax_pat_` 불투명
토큰만 해석한다. 포털 PAT 는 RS256·다른 발급자라 **서명 단계에서 죽는다.** 더구나
`security.py` 는 기대 청중이 없으면 `aud` 를 **달고 온** 토큰을 명시적으로 거부한다 —
`aud` 를 붙이는 행위 자체가 역효과다.

`/apps/*` 를 열려면 허브 `authz.py` 에 포털 JWKS 분기를 **새로 다는** 수밖에 없다(PLAN §5, 미결).
부품은 같은 리포에 있다(`portal_sso.py` 의 JWKS 페처·RS256 검증, 300초 캐시).

## D-3. 도구를 자동 생성하지 않은 이유

하위 앱의 REST 를 전부 도구로 펴면 수백 개다(AIDataHub 96 · DynaForge 56 · ste 30 · StepForge …).
그러면 `tools/list` 가 모델 컨텍스트를 먹고, 이름이 겹치고, **정작 앱이 골라서 낸 좋은 도구가 묻힌다.**
그래서 둘만 뒀다 — 무엇이 있는지 묻는 것(`rest_catalog`)과 하나를 부르는 것(`rest_call`).

사용자 지시가 그대로 설계다. **의도적으로 연 MCP 가 먼저이고, REST 는 그것으로 안 되는 것의 우회로다.**
그 우선순위를 두 도구의 설명 첫 줄에 적었다 — 모델이 읽는 자리는 거기다.

## D-4. 사이트가 0개면 도구를 **안 낸다**

쓸 수 없는 도구를 목록에 두면 모델이 그것을 고르고 매번 빈손으로 돌아온다. `_visible_tools` 와
`list_tool_apps` 가 **같은 조건**(`if REST:`)을 본다 — 한쪽만 고치면 "목록엔 있는데 안 보인다" 가 된다.

## D-5. `per_user` 가 `inject` 를 이긴다 — 그리고 그래서 쓰기가 열린다

`inject` 는 **그 사이트의 마스터 키**다. 최저 권한 사용자가 청중만 맞는 PAT 를 찍어 그 권한을
그대로 쓸 수 있어서, 주입 사이트는 읽기전용으로 묶여 있다(`allowed_methods`).

그런데 ste·DynaForge 는 **사용자 위임이 이미 있다**(`per_user_sso`) — 게이트웨이가 그 사람 명의의
토큰을 발급받아 부를 수 있다. 본인 명의면 권한 상승이 없으므로 그 사이트가 자기 사용자에게
허용하는 만큼 그대로 된다. 그래서 `credential_mode` 를 두고 **per_user 를 우선**시켰고,
`allowed_methods` 는 `inject` 사이트만 묶는다.

서비스 자격으로 **조용히 강등하지 않는다.** 강등하면 남의 시야로 200 을 돌려주고, 실패가 정상
응답과 구분되지 않는다 — 이 리포가 반복해서 당한 그 모양이다(MCP 경로도 같은 자세를 취한다).

StepForge 는 위임이 없어서 주입뿐이고, 자체 소유권 판정도 없다(서비스 자격 = 전체 시야).
그래서 읽기전용으로 남는다. 쓰기를 열려면 그 앱에 소유권이 먼저 생겨야 한다.

## D-6. 규칙은 **한 곳에만** 적는다

`allowed_methods`·`credential_mode` 둘 다 `rest_proxy.py` 가 정본이고 게이트웨이가 그것을 부른다
(`rest_proxy` 는 `gateway` 를 import 하지 않으므로 순환이 아니다). 같은 규칙을 두 군데 적어 두면
MCP 로는 통하고 REST 로는 막히는 **두 얼굴**이 된다. `test_allowed_methods_is_one_definition` 이
같은 함수 객체인지까지 본다.

## D-7. `audience_ok` 는 손으로 적지 않는다

종전엔 `["mx-white-paper","ai-data-hub","signalforge"]` 가 박혀 있어서 두 방향으로 어긋날 수 있었다.
사이트는 있는데 청중에 없으면 프록시가 `unknown site` 404 로 답하고, 청중에 있는데 사이트가 없으면
그 청중으로 PAT 를 찍어도 아무 효과가 없다(포털 허용 목록의 `heax-hub` 가 정확히 그 모양이었다).
이제 `sorted(rest)` 로 유도한다 — 어긋날 자리가 없어진다.

`heax-hub` 청중 자체는 포털 기본 목록에 **남겼다.** 지우면 `/apps/*` 배선을 여는 결정이 났을 때
다시 넣어야 하고, 지금 있어도 해는 없다(소비처가 없을 뿐이다).

## D-8. 지금 **열려 있는 채로 남는 구멍** — 합치기 전에 닫아야 한다

`scope`(read/write)가 **어디서도 검증되지 않는다.** 포털이 클레임에 싣지만 게이트웨이·검증기
어디서도 읽지 않는다. 발급 화면은 `scopes: ['read','write']` 를 보내며 권한이 있는 것처럼 보이게
한다 — 착시다. 청중을 넓힌 지금, 이것이 "한 장 = 전권" 을 뜻한다.

이번에 넓힌 범위는 **포털 권한으로 매 요청 다시 계산되는 것**(`_backend_allowed`)이라 사람 단위로는
막힌다. 못 막는 것은 "그 사람이 쓸 수 있는 사이트 안에서 read 만 주려 했는데 write 도 된다" 쪽이다.
읽기/쓰기를 나눌 필요가 생기면 그때 `scope` 를 실제로 강제해야 한다.

## D-10. 열기 직전에 **닫은** 구멍 — `none` 모드가 제한 없음이었다

적대 검토가 잡았고 실측으로 확인했다. 셋이 겹쳐 있었다.

1. 자격이 아무것도 없는 사이트(`inject` 도 `per_user` 도 없는 것 = 지금 `ai-data-hub`)는
   `allowed_methods` 가 **제한 없음**을 돌려줬다. 근거는 "주입이 없으니 권한 상승도 없다" 였다.
2. 그런데 AIDataHub 상류는 **무인증 200** 이다(`POST /api/embed` 실호출 확인) — 즉 이 프록시가
   **유일한 관문**이라 '권한 상승이 없다' 가 아니라 **'아무 통제도 없다'** 였다.
3. `feat:expert-chat` 이 `plat:aidatahub` 를 함의하므로(access.yaml) 전문가챗 허가만 있으면
   `_backend_allowed` 를 통과한다.

종전엔 발급 화면이 `mcp-gateway` 만 찍어서 우연히 막혀 있었다. **이번에 청중을 넓히고
`rest_call` 로 LLM 이 부를 수 있게 만드는 순간 그 우연한 장벽이 사라진다.** 그래서 규칙을
뒤집었다 — **쓰기의 기본은 닫힘**이고, 여는 길은 `per_user`(본인 명의라 상류 규칙이 그대로
적용된다)이거나 사이트별 `methods` 명시뿐이다.

## D-11. 아직 안 닫은 것 — `x-forwarded-user` 를 읽는 앱이 0곳이다

게이트웨이는 신원 힌트를 실어 보내지만 하위 앱 중 그것을 읽는 곳이 없다. `inject` 사이트에서
누가 했는지는 **게이트웨이 원장에만** 남는다(그래서 `_audit(caller=…)` 를 두 도구 모두에 걸었다).
`per_user` 사이트는 상류가 그 사람의 토큰을 보므로 상류 원장에도 남는다 — 이것도 per_user 를
우선시킨 이유 하나다. 주입 사이트에 쓰기를 열려면 귀속이 먼저 있어야 한다.

## D-12. ste 만 아직 안 된다 — **헤드노드에 뜬 것이 낡았다**(dev 실측)

dev 게이트웨이를 재기동해 실호출로 확인한 결과다. 여섯 사이트 중 다섯은 바로 됐다.

| 사이트 | 실호출 결과 |
|---|---|
| ai-data-hub | `GET /health` → 200 `{"status":"ok"}` (읽기전용으로 묶인 것 확인) |
| step-forge | `GET /` → 200 · `POST` → `method not allowed` |
| mx-white-paper · signalforge | 서비스가 내려가 있어 `paths: null` + 사유(빈 목록이 아니다) |
| dyna-forge | `plat:dynaforge` 없는 그룹으로 부르면 `forbidden` (권한 표가 작동) |
| **ste** | ❌ `SSO 401` — 게이트웨이가 그 사람 명의 토큰을 못 받는다 |

원인은 배선이 아니다. **헤드노드에 떠 있는 ste 빌드에 `/api/auth/sso` 가 아예 없다** —
`http://192.168.130.10:15810/openapi.json` 에 sso 경로가 0건이고, 시크릿을 맞게 줘도 401 이다
(인증 미들웨어가 공개 경로로 모르기 때문). 리포에는 있다(`c7e3411`, 원격에도 올라가 있다).

**소스에 있는 것과 떠 있는 것이 다르다** — 이 리포가 반복해서 당한 그 모양이라, 판정을 소스가
아니라 실호출로 했더니 잡혔다.

여파는 REST 다리 하나가 아니다. **ste MCP 의 사용자 위임도 같은 엔드포인트를 쓴다** —
헤드노드가 갱신되기 전까지 둘 다 서비스 계정이 아니라 **실패**로 떨어진다(조용히 강등하지
않게 만들어 뒀으므로 사유가 보인다).

**정정 — 위 문단에서 "cae00 에서만 된다" 고 적은 것은 이 박스에서는 틀렸다.**
`192.168.130.10` 은 에어갭 운영 헤드노드가 아니라 **dev 박스 위의 libvirt VM `ste-head01`**
이다(로컬 브리지 `virbr-ste`, `virsh list` 로 확인). ste 리포의 `deploy/transport.env` 가
`TRANSPORT_MODE=direct` 라 dev 에서 ssh 로 직접 닿고 배포도 된다 — Drive·Teleport 가 필요 없다.
운영 클러스터(teleport)만 cae00 경로다. 도달성은 대상이 무엇인지로 갈리고, 이름이 같아서
헷갈린다.

→ 그래서 **여기서 고쳤다.** D-13 참조.

## D-13. ste 를 실제로 최신화하고, update-all 이 앞으로 하게 만들었다

**지금 한 것.** VM 의 `/opt/ste/backend/src` 와 리포를 sha256 으로 대조해 **8개 파일이 다름**을
확인하고(이번 세션에 고친 것 전부), `deploy-backend.sh` → `deploy-frontend.sh` 로 배포했다.
결과: 소스 20개 지문 **완전 일치**, openapi 경로 30 → 32(`/api/auth/sso`·`/sso/revoke` 등장),
프론트도 일치(에이전트 바이너리에 이번 세션 수정 둘이 들어 있다), ste 테스트 102개 통과.

손대기 전에 **되돌릴 수 없는 것을 백업했다** — `/opt/ste/state`(SQLite 계정 원장)·`apps-web`·
`.env` + 현 소스 스냅샷을 `/opt/ste/.pre-refresh-<시각>/` 에. 배포 후 원장은 그대로다
(`users=1 pats=2 jobs=11 sessions=3` → 같음, 그 뒤 SSO 로 계정 하나가 정상 생성돼 users=2).

**`rsync --delete` 범위를 먼저 직접 확인했다.** 대상은 `/opt/ste/backend/` 와 `/opt/ste/apps/`
뿐이라 `state`·`apps-web` 은 그 밖이다(스크립트 주석의 주장이 코드와 맞았다). 단 `apps/` 는
삭제 대상이므로 **VM 에만 있는 앱이 있으면 날아간다** — 대조해서 없음을 확인하고 돌렸다.
다음 사람도 그 확인을 먼저 해야 한다.

**시크릿 심기를 떼어냈다.** 이 일이 `refresh-code.sh`(Drive 경로) 안에만 있어서
`deploy-backend.sh` 로 배포하면 코드는 새것인데 시크릿이 없어 자격 중계가 404 로 남았다.
`deploy/sync-sso-secret.sh` 로 꺼내 **양쪽 경로가 같은 것을 부른다**(D-6 과 같은 이유).
값은 원격 셸 **인자로 넘기지 않는다** — ps 에 보이고 히스토리에 남아서 stdin 으로 넣는다.

**update-all 이 앞으로 한다(2c).** 종전에 안 했던 이유는 "실배포가 routine·크론에 섞여
발화하면 안 된다" 였다. 그 의도를 **운영 클러스터에만** 남기고 축을 transport.env 로 잡았다 —
`direct` 는 매 실행 지문 대조 후 다를 때만, `teleport` 는 `STE_DEPLOY=1` 명시 때만.
심는 쪽(2c)과 판정하는 쪽(§6 헬스게이트)은 갈라 뒀다. 같은 코드가 심고 판정하면
"심었다고 했으니 됐다" 가 되고 실제로 열리는지는 아무도 안 본다.

**실측으로 잡아 막은 것 셋** (설계할 때 안 보였던 것들이다) —
1. `--if-stale` 이 리포 없는 박스에서 **Drive 부트스트랩 22MB 다운로드를 시작했다.** update-all
   한 번이 그걸 발화시키면 막으려던 바로 그 모양이다. 자동 호출은 있는 것만 최신화한다.
2. **닿지 않는 헤드에 40초+ 매달렸다.** update-all 이 매 실행 이 경로를 타므로 헤드가 죽은
   박스에서 갱신 전체가 멈춘다. ssh ConnectTimeout 10초 + update-all 쪽 900초 상한.
3. 원격 지문을 못 읽었을 때 **"같다"로 읽으면** 낡은 박스를 영원히 건너뛰며 초록을 낸다.
   못 읽으면 최신이라 하지 않는다(닿지 않는 헤드로 실측: "이미 최신" 안 나오고 종료코드 1).

**끝에서 끝까지 확인했다.** 게이트웨이가 `mxcaegroup@gmail.com` 명의로 ste PAT 를 받아
`/api/auth/me` 200(계정이 그 자리에서 생성, id=2)·`/api/jobs` 200. §6 자격중계 게이트도
`401 + www-authenticate 없음` = 양쪽 설정됨으로 초록이다.

**변이 검사에서 내 시험 하나가 약했다.** 리포 부재 가드를 떼도 뒤의 접속설정 가드가 같은
"건너뛴다" 를 찍어 통과했다 — 사유 문구를 각각 못박도록 강화했다.

**적대 조사가 내가 못 본 것 둘을 찾았다.**
1. `update-forges.sh` 의 `do_ste()` 가 **박스로 갈라** dev 를 스킵했다("deploy-ste 는 cae00
   전용이다" — 이제 거짓이다). 가르는 축은 박스가 아니라 **전송 방식**이다. 박스로 막아 둔 탓에
   dev 의 ste 가 낡은 채로 남았다. 스킵을 뗐고 `deploy-ste.sh` 가 스스로 경로를 고르게 했다.
2. dev 의 `routes.env` 는 `#ste=`(주석)이지만 **gitignore 된 `routes.local.env` 에 `ste=` 가
   활성**이다. `_ste_routed()` 가 그 파일을 먼저 보므로 dev 에서도 `STE_ROUTED=1` 이고 §6
   게이트가 돈다 — "dev 는 ste 를 안 쓴다" 고 읽으면 틀린다.

조사가 확증해 준 것(내가 독립적으로도 확인한 것들) — `--delete` 범위는 `backend/`·`apps/`·
`/opt/apps/ste/`·`web/` 넷이고 `state`·`apps-web` 은 그 **형제**라 안전하다. `refresh-code.sh`
를 dev 에서 쓰면 안 되는 이유가 하나 더 있다 — 그것은 `git checkout <커밋>` 으로 **리포 HEAD 를
고정**하고 `dist` 를 tar 로 덮는다. 저작 리포인 dev 에서 돌리면 작업 트리를 건드린다.
그리고 `ste-mcp` 은 `ste` 패키지를 import 하지 않는다(httpx 로 REST 를 부르는 얇은 래퍼) —
백엔드 소스만 바꿨으면 `ste-backend` 재기동만으로 충분하다.



## D-9. 이번에 고친 파일과 시험

| 무엇 | 어디 |
|---|---|
| 두 도구 정의·핸들러·가시성 | `HWAXMcpGateway/gateway.py` |
| 자격·메서드 규칙 정본, per_user 프록시 | `HWAXMcpGateway/rest_proxy.py` |
| 사이트 셋 + `audience_ok` 유도 | `HWAXMcpGateway/provision-config.sh` |
| 시험(다리 6·프로비저닝 3) | `HWAXMcpGateway/test_gateway.py`·`test_provision_urls.py` |
| 기본 청중·발급 화면·API 타입 | `HWAXPortal/backend/app/config.py`·`frontend/src/pages/TokenPage.tsx`·`frontend/src/api/pat.api.ts` |
| 권한 표에 새 사이트 키 | `HWAXPortal/backend/config/access.yaml` |
| 시험(한 장이 넓게 덮는가) | `HWAXPortal/backend/tests/test_pat_one_token.py` |

변이 검사로 확인했다 — 각 가드를 되돌리면 해당 시험만 깨지고, 되돌린 뒤 `git diff` 가 비었다.
