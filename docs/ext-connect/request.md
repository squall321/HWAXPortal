# 외부 연결을 설정만으로 — 토큰 등록 플랫폼을 빌드 없이 붙이기(첫 대상 FMEA Agent · MatNexus) (2026-10-21)

> **사본** — 2026-10-21 사용자가 붙여 넣은 요청서다. 이 리포는 GitHub 에 있어 **내부 주소 두 개(`<FMEA_호스트>` · `<MatNexus_호스트>`)와
> 담당자 메일 주소만 자리표시로 바꿨다.** 나머지는 받은 글 그대로다(그때의 사실을 적은 기록이라 고쳐 쓰지 않는다 — 구현에서 달라진 것은
> [context-notes.md](context-notes.md) 에 적는다). 계획 [PLAN.md](PLAN.md) · 체크리스트 [checklist.md](checklist.md).

요청일 2026-10-21 · 요청자 koo.park(HWAX Portal 운영) · 대상 **HWAXPortal · HWAXMcpGateway**

기준 — 포털 origin/main `2e514e3` · 게이트웨이 origin/master `8e30ee5`. 아래 `파일:줄` 은 이 커밋 기준이다. cae00 에서 읽기만 해 대조했다
(검증 에이전트 4 · 설계안 3 + 심사 · 합성, 10-21). 새로 만드는 함수 · 필드 · 파일은 **(새)** 로 적는다.
이 문서는 MATNEXUS-CONNECTION-REQUEST.md(10-20)를 **대신한다**.

**한 줄** — 포털 '개인 토큰 › 외부 연결'(`/tokens?tab=connect`)을 **플랫폼 목록을 설정에서 읽는 화면**으로 바꿔 달라. 그러면 다음 외부 플랫폼부터는
박스 파일 한 곳에 항목을 적는 것으로 붙는다. 포털 빌드 · 코드 · 재기동이 필요 없다. 첫 대상은 FMEA Agent 와 MatNexus 다.

운영 결정(사용자, 10-21) 세 가지.
1. **토큰 등록 방식이다.** 사람이 그쪽에서 받은 자기 토큰을 등록하고, 게이트웨이는 그 사람의 토큰으로만 부른다. 공유 비밀로 사람 토큰을 받아 오는
   표준 위임(10-20 `726d7a6` · `acf985b` · 게이트웨이 `8e30ee5` 가 MatNexus 에 깐 길)은 두 곳 다 쓰지 않는다. MatNexus 는 위임 창구를 켜지 않는다(0절).
2. **새 플랫폼은 토큰 주인을 확인하지 않는다**(「그냥 토큰 입력하면 누구거라도 연결되게」). 필요한 플랫폼만 설정으로 켠다(1-5).
3. **외부 플랫폼이 늘어도 빌드가 필요 없어야 한다.** 이번 한 번만 포털 · 게이트웨이에 공통 기능을 넣는다.

지금 이 화면은 RA · TestScope 둘만 받는다. 포털 `connections.py:30` `SERVICES`, 화면 `TokenPage.tsx:262-263 · 297-298` 의 카드 두 장, 게이트웨이
`gateway.py:304` `PORTAL_CONN_BACKENDS` 가 모두 코드에 박혀 있다. 화면 `dist` 는 git 이 아니라 Drive 로 온다(`update-all.sh:2416-2427`).
그래서 지금은 플랫폼이 하나 늘 때마다 두 레포 코드와 화면 빌드가 든다.

---

## 0. 실측(2026-10-21, cae00 — 사내 프록시를 거치지 않고. FMEA 는 사용자 본인 토큰으로 목록까지만)

| 항목 | FMEA Agent | MatNexus |
|---|---|---|
| 주소 | 웹 화면 `<FMEA_호스트>:5195` · **MCP `<FMEA_호스트>:5190/mcp`**. FMEA 화면의 연결 안내는 `claude mcp add --transport http fmea http://<FMEA_호스트>:5190/mcp --header "Authorization: Bearer fmea_…"` 다 | REST `<MatNexus_호스트>:8010` · MCP `:8012/mcp` |
| 판 | 웹 `GET :5195/health` 200 — `auth.mode=local` · 활성 계정 6 · `code_version b740d51`. MCP `serverInfo` `fmea-analysis 1.29.1` · protocol `2025-03-26` · `Mcp-Session-Id` 세션. 서버는 개인 PC 에서 도는 것으로 보인다(`/health` 의 로그 경로) | `MatNexus API v1.292.1`(10-20) |
| 로그인 | 웹 `/` → 302 `/login`. 폼은 `username` · `password` 뿐이고 `/signup` 이 있다. SSO 는 없다. 웹(:5195)은 Bearer 를 보지 않는다 — 진짜 토큰도 401 `login_required` | 자체 계정. `/api/auth/me` · `/api/auth/tokens` 가 OpenAPI 에 있다 |
| 위임 창구 | 없다 — `/api/auth/sso` · `/sso/verify` 도 401 `login_required` | `POST /api/auth/sso` · `/sso/verify` → **404**(창구 꺼짐, 10-21 재확인) |
| 토큰 꼴 | **`fmea_…`**(48자), 웹 `/tokens` 에서 사람이 발급한다. 화면에는 `Bearer fmea_J…` 로 보인다 — 사람이 `Bearer ` 까지 붙여 넣을 수 있다(PB8 ⓪) | 개인 토큰 `mnx_pat_…`(10-20) |
| 토큰으로 MCP | `:5190/mcp` `initialize` 200 → **`tools/list` 23개**. `readOnlyHint` 를 단 도구는 0개다. 쓰는 도구 둘(`add_material_baseline_overlay_tool` · `add_spec_overlay_tool` — 비파괴 덮개 저장)이 섞여 있다 | 데이터 도구만 개인 토큰을 요구한다 |
| 토큰 없이 MCP | `:5190/mcp` `initialize` 부터 401 `{"error":{"code":"unauthenticated","message":"토큰이 필요합니다 — Authorization: Bearer <토큰> (앱 /tokens …"}}`. **목록도 토큰이 있어야 나온다**(1-4) | `initialize` 200 · **`tools/list` 114개** |
| 본인 확인 | **없다** — `:5190` 의 `/api/auth/me` · `/api/me` · `/api/users/me` · `/api/user` · `/api/whoami` · `/api/account` · `/api/profile` · `/me` 가 전부 404 다. 새 설계는 주인 확인을 하지 않으므로 막히지 않는다(1-5) | `GET /api/auth/me`(응답 모양 미확인 — 1-9 ②) |
| 직접 길 | 프록시 없이 `:5190` · `:5195` 에 닿는다 | 프록시 없이 `:8012` · `:8010` 에 닿는다 |
| 도구 이름 겹침 | 지금 게이트웨이 노출 도구 946개와 겹치는 이름 0개 | **4개** — `get_material` · `how_to_measure` · `measurement_gaps`(`heax-materialtwin_web`) · `get_ontology`(`signalforge`). 지금 규칙(`gateway.py:887-889`)이면 기존 앱의 이름까지 접두로 바뀐다(GW19) |
| 남은 위임 설정 | 게이트웨이 `heax_registry.per_user_sso` 에 `fmea` · `matnexus` 가 없다. 정적 백엔드에도 없다(키 이름만 확인) | 같다 |
| 프록시 | 포털(8723) · 게이트웨이(9110) 프로세스에 `http_proxy` 가 있고 `NO_PROXY` 에 두 호스트가 없다. 게이트웨이는 백엔드 주소를 스스로 우회 목록에 넣는다(`gateway.py:76` `_bypass_proxy_for`, 부팅 때 `:127-140`). 포털이 그쪽을 부를 때(토큰 확인)는 프록시를 탄다 — 새 설계는 `trust_env=False`(PB9) | 같다 |

---

## 1. 설계 — 외부 연결을 설정만으로(빌드 없이)

### 1-1. 한 줄

플랫폼 하나는 **박스 권한표(`backend/config/` 의 권한표 `.local.yaml`, 박스 전용)의 그 플랫폼 항목 안에 둔 `connect:` 블록 하나**로 선언한다.
포털은 이 블록으로 '외부 연결' 카드를 그리고 토큰을 받는다. 게이트웨이는 같은 블록을 권한 행과 함께 포털 내부 정책 주소(게이트웨이 전용, `/internal/…/policy`) 한 응답으로 받아
백엔드를 스스로 붙이고 뗀다. 호출은 늘 그 사람이 등록한 토큰으로만 나간다. 새 플랫폼에는 주인 확인을 하지 않는다.

| | 이번 한 번(이 요청) | 다음 플랫폼부터 |
|---|---|---|
| 포털 | 백엔드 코드 · 화면 빌드 1회(dist 는 Drive 로 — `build-all-to-drive.sh portal` → 박스 update-all 또는 deploy-all-from-drive) · 재기동 | 박스 권한표 편집 한 번. 빌드 · 코드 · 재기동이 없다 |
| 게이트웨이 | 코드 · 재기동 1회(박스 게이트웨이 리포를 새 판으로 올린 뒤, 한가할 때) | 없다. 60초 주기로 스스로 붙이고, `POST /refresh` 면 바로 붙인다 |
| 에이전트서버 | 없다 | 없다(1-9 ⑧) |

RA · TestScope 는 지금 코드 그대로 둔다. 같은 이메일 확인, RA 부서 헤더, SSO · 토큰 두 갈래가 모두 남는다. 기존 `GET /auth/connections` 응답도 한 글자도
바꾸지 않는다(새 목록은 새 주소로 낸다 — PB7). 그래서 앱마다 `*_BASE_URL` env · 라우트 · 카드 · 게이트웨이 상수를 두는 일이 없다.
`provision.env` 에 `MATNEXUS_MCP_URL` · `FMEA_MCP_URL` 을 **넣지 않는다**. 같은 키의 정적 백엔드가 생기면 게이트웨이가 그 `connect` 를 충돌로 보고 쓰지 않는다(GW3).

### 1-2. 박스 설정 예

```yaml
# ~/Projects/HWAXPortal/backend/config/ 의 박스 권한표(.local.yaml)
#   박스 전용 파일이다(.gitignore). 고치면 다음 요청부터 반영되고 재기동은 필요 없다.
#   '>>> hwax-batch' 블록 밖에 적는다.
#   같은 id 는 추적 권한표의 항목을 통째로 바꾼다. 그래서 label · systems · gateway · hide_unless_routed 를 다시 적는다.
#   connect: 는 이 파일에서만 읽는다. 추적 권한표에 적힌 connect 는 버리고 알림을 남긴다.
platforms:
  # … 기존 rootdesigndatahub · failuretrace · caegroupdatahub(hwax-batch) · simflow …
  - id: fmea
    label: FMEA Agent
    desc: FMEA 분석 · 소재 기준선/규격 덮개
    systems: [fmea]                  # 박스 타일(systems.cae00.yaml)이 이미 있다(10-21)
    gateway: [fmea]                  # 권한 행. connect.backend 가 여기 없으면 connect 를 버린다
    hide_unless_routed: true
    connect:
      # backend: fmea                # 생략하면 id 를 쓴다. 게이트웨이 백엔드 키이자 포털 service 다
      mcp_url: http://<FMEA_호스트>:5190/mcp
      token_hint: "fmea_…"
      token_prefix: "fmea_"
      issue: "FMEA 웹 화면에 로그인한 뒤 토큰 메뉴(/tokens)에서 발급한 토큰을 붙여 넣습니다. 'Bearer ' 까지 붙여도 됩니다."
      issue_url: http://<FMEA_호스트>:5195/tokens
      verify: mcp                    # 등록할 때 그 토큰으로 보낸 initialize 가 200 이어야 저장한다. 유효성만 보고 주인은 보지 않는다
      list_auth: "registered:<목록용 포털 계정 이메일>"   # initialize · tools/list 에만 그 계정이 카드에 등록한 fmea 토큰을 쓴다(1-4)
      read_tools: []                 # 읽기 도구의 원래 이름. 첫 등재 뒤 /tools-map 을 보고 채운다. 비어 있으면 전부 쓰기로 본다
      note: "쓰기 도구 2개(add_material_baseline_overlay_tool · add_spec_overlay_tool)는 이 토큰 주인 명의로 FMEA 에 덮개를 저장합니다."
  - id: matnexus
    label: MatNexus
    desc: 물성 관리 시스템(TestScope 와 같은 팀)
    systems: [matnexus]
    gateway: [matnexus]
    hide_unless_routed: false        # 타일이 아직 없다. true 로 두면 권한 요청까지 막힌다(1-6)
    connect:
      mcp_url: http://<MatNexus_호스트>:8012/mcp
      token_hint: "mnx_pat_…"
      token_prefix: "mnx_pat_"
      issue: "MatNexus 의 내 계정 › 토큰에서 개인 토큰을 발급해 붙여 넣습니다."
      verify: none                   # initialize 는 토큰 없이도 열려 있어 mcp 검증으로는 알 수 있는 것이 없다
      # verify: url                  # 1-9 ② 가 확인되면 이 줄과 아래 줄로 바꾼다(재기동 없음)
      # verify_url: http://<MatNexus_호스트>:8010/api/auth/me
      # owner_field: email           # 켜면 포털 이메일과 같은 계정의 토큰만 받는다(fail-closed). 기본은 끔(10-21 결정)
      list_auth: open                # 토큰 없이 tools/list 114개가 나온다
      read_tools: []
      note: "읽기 전용 토큰이면 MatNexus 가 쓰기 도구를 거절합니다."
```

`connect:` 칸은 아래와 같다. 카드 제목은 플랫폼 `label` 을 쓴다.

| 칸 | 필수 | 뜻과 검사 |
|---|---|---|
| `backend` | 아니오(기본 `id`) | 게이트웨이 백엔드 키이자 포털 service 다. 꼴은 `^[a-z0-9][a-z0-9_-]{1,40}$` 이다. 그 항목의 `gateway:` 안에 있어야 한다. `reportarchive` · `testscope` · `heax-…` · `_gateway` · `rest` · `portal` · `heax_registry` 는 받지 않는다. 다른 플랫폼과 겹쳐도 안 된다 |
| `mcp_url` | 예 | Streamable HTTP 주소다. http(s) 만 받는다. 계정(`user@`) · `?쿼리` · `#조각` 은 받지 않는다. 호스트는 IP 이거나 `[a-z0-9._-]+` 여야 한다. 게이트웨이 `_bypass_proxy_for`(`gateway.py:76`)가 `NO_PROXY` 에 적을 수 있는 꼴이다 |
| `token_hint` | 아니오(기본 `token_prefix`+`…`) | 카드 자리표시와 게이트웨이 거절 안내에 쓴다 |
| `token_prefix` | 권장 | 토큰이 이 글자로 시작해야 저장한다. 다른 플랫폼의 접두(다른 `connect` 의 접두, `rat_`, `tsc_pat_`)로 시작하면 거절한다. 32자 이하다 |
| `issue` · `issue_url` · `note` | 아니오 | 카드 문구다. 글자로만 그린다. `issue_url` 은 http(s) 만 받는다 |
| `verify` | 아니오(기본 `none`) | `none`, `mcp`(그 토큰으로 initialize 200), `url`(`verify_url` 에 Bearer 로 GET 200) 중 하나다. 유효성만 본다 |
| `owner_field` | 아니오(기본 없음) | `verify: url` 일 때만 쓴다. 응답 JSON(맨 모델이든 `data` 봉투든)의 그 칸 이메일이 포털 이메일과 같아야 저장한다. 이메일이 없어도, 달라도 거절한다 |
| `list_auth` | 아니오(기본 `open`) | `open` 또는 `registered:<포털 이메일>` 이다(1-4) |
| `read_tools` | 아니오(기본 `[]`) | 읽기 도구의 원래 이름이다. 게이트웨이 `read_tools.json` 목록에 **더해진다**(1-6) |
| `workspace_header` · `workspace_label` | 아니오 | 부서 같은 값을 실을 헤더 이름과, 카드에 생길 두 번째 칸의 이름이다. 지금 두 앱은 쓰지 않는다. Authorization · Proxy-Authorization · Cookie · Host · Content-* · Accept · Mcp-* · X-CSRF-Token · X-Hwax-* · X-Heax-* 는 받지 않는다(포털과 게이트웨이 둘 다 막는다) |

누가 어떻게 읽는지는 아래와 같다.

| 읽는 곳 | 어떻게 | 반영 |
|---|---|---|
| 포털 정책 객체(`policy.py:329-372`) | 요청마다 두 파일의 mtime 을 본다(`:350-366`). 깨진 파일이면 직전 정책을 계속 쓰고, 관리자 '배선 설정'에 `problems()` 로 띄운다 | 다음 요청 |
| 게이트웨이 | 포털 내부 정책 주소(게이트웨이 전용, `/internal/…/policy`) 의 (새) `connections` 를 권한 행과 **한 응답**으로 받는다. 60초마다 받는다(정책 주기 루프 `:1417-1420`). 백엔드는 다음 재활 패스(`REVIVE_INTERVAL_S` `:186`, 60초)에서 붙는다 | 최대 약 2분, `POST /refresh` 면 즉시 |
| 게이트웨이 디스크 | (새) `.conn_registry_cache.json`(0600, gitignore)이다. 포털이 늦게 떠도 부팅 때 다시 붙일 수 있게 한다. 토큰은 담지 않는다 | — |

새 비밀 저장소는 없다. 사람 토큰은 지금의 `connections` 표(`user_store.py:111-116`)에 그대로 들어간다. FMEA 목록용 토큰은 `list_auth` 가 가리키는 포털 계정이
그 카드에 등록한 토큰이다.

### 1-3. 고칠 곳

#### 포털 백엔드(HWAXPortal)

| # | 자리(`2e514e3`) | 지금 | 할 일 |
|---|---|---|---|
| PB1 | 포털 권한 모듈 `policy.py:40-51` `Item` | 플랫폼 행 필드 | `connect: ConnectSpec \| None = None` 를 더한다. (새) frozen `ConnectSpec` 의 필드는 backend · mcp_url · token_hint · token_prefix · issue · issue_url · note · verify · verify_url · owner_field · list_auth · read_tools(tuple) · workspace_header · workspace_label · platform_id · label · desc 다. 모두 해시할 수 있어 `Item` 은 frozen 으로 남는다 |
| PB2 | `policy.py:135-188` `load_raw` | `sso_affiliation_map` 은 박스 파일에서만 받는다(`:148-149`) | `connect` 도 같은 꼴로 박스 전용으로 한다. 오버레이를 합치기 전(`:150`)에 추적 파일의 플랫폼 dict 에서 `connect` 를 떼고 메모를 남긴다(「추적 권한표의 connect 는 읽지 않는다 — 박스 권한표 에만」). git push 한 번으로 모두의 토큰이 다른 주소로 가는 일을 막는다 |
| PB3 | `policy.py:206-255` `parse_policy` | 항목을 만드는 곳 `:208-215`, 메모 `:239`, `Policy(...)` `:254-255` | 플랫폼마다 (새) `_parse_connect(d, notes, seen)` 를 부른다. 1-2 칸 표대로 검사하고, 틀리면 **그 블록만** 버리고 메모를 남긴다. 던지지 않는 것은 `:237-251` 의 SSO 행 버리기와 같은 자세다. 메모는 `Policy.warnings` 를 거쳐 관리자 '배선 설정'(`:368-372`)과 update-collab ①(`update-collab.sh:207-208`)에 뜬다 |
| PB4 | `policy.py:62-118` `Policy` | `gateway_policy()` `:106-112` | (새) `connections() -> dict[str, ConnectSpec]` 는 백엔드 키로 찾는다. (새) `gateway_connections()` 는 키마다 {platform, label, desc, hint, prefix, mcp_url, list_auth, read_tools, workspace_header} 를 낸다. 안내 문구 · verify 칸 · 비밀은 담지 않는다 |
| PB5 | 포털 권한 모듈 `routes.py:325-329` `internal_policy` | `{"backends": …}` | `p = _policy(request)` 를 한 번만 부르고 `{"backends": p.gateway_policy(), "connections": p.gateway_connections()}` 를 낸다. 권한 행과 연결 선언이 같은 파싱에서 나온다. `backends` 만 읽는 곳(게이트웨이 `:1401`, update-collab `:548`, update-all §6)은 그대로 돈다 |
| PB6 | `backend/app/auth/routes/connections.py:25` 가져오기 · `:30` `SERVICES` | `principal_pat_or_session, require_csrf` · `("reportarchive", "testscope")` | `get_current_principal`(`deps.py:34`) · `ensure`(`deps.py:86`) · `jwt` · `re` 를 더 가져온다. `SERVICES` 는 그대로 둔다. (새) `BUILTIN = frozenset(SERVICES)`. (새) `_registry(request)` 는 앱 상태에 든 정책 객체의 `.get().connections()` 를 돌려준다(`main.py:92`). 권한 모듈 `routes.py:17` 이 이 파일을 가져오므로 거꾸로는 가져오지 않는다 |
| PB7 | `connections.py:248` 뒤 (새) `GET /auth/connections/ext` | `list_connections`(`:232-248`)는 그대로 둔다 — `test_testscope_connection.py:165` 가 그 응답의 키 집합을 정확히 단언한다 | 새 주소가 `{platforms: [...], orphans: [...]}` 를 낸다. `platforms[]` 는 선언마다 {service, label, token_hint, issue, issue_url, note, verify, workspace_label, entitled, need(`plat:<id>`), requestable, connected(`connection_meta` 또는 null)} 다. `requestable` 은 그 키가 숨긴 키가 아니라는 뜻이고, 권한 모듈 `routes.py:34-37` 과 같은 두 줄(`policy.hidden_keys(catalog.live_ids())`)로 셈한다. `orphans[]` 는 그 사람의 행 중 내장도 선언도 아닌 service 를 {service, tail, created_at} 로 낸다. `mcp_url` · `verify_url` · `list_auth` 는 내지 않는다. 인증은 `principal_pat_or_session` 이다(읽기) |
| PB8 | `connections.py:326` 뒤 (새) 라우트 | — | `PUT · DELETE /auth/connections/ext/{service}` 를 둔다. path 꼴은 `^[a-z0-9][a-z0-9_-]{1,40}$` 이다. `/ext/` 아래에 두므로 RA · TestScope 라우트(`:147` · `:251` · `:293` · `:317`)를 가릴 수 없고, 내장 키에는 404 를 낸다. 인증은 **브라우저 세션 + CSRF 만** 받는다(`Depends(get_current_principal)` + `Depends(require_csrf)`). PAT 는 받지 않는다(1-5). PUT 순서: ⓪ `token.strip()` 뒤 맨 앞의 `Bearer `(대소문자 무관, 뒤 공백 포함)를 뗀다 — FMEA 화면이 `Bearer fmea_…` 로 보여 준다 ① 선언이 없으면 404 ② `ensure(principal, need)` 가 아니면 403 ③ `^[\x21-\x7e]{8,512}$` 인지 본다(개행 · 공백 없음) ④ **포털 JWT 를 거절한다** — 서명 검사 없이 풀어 `iss == settings.jwt_issuer` 면 400 이다(`config.py:93`, PAT 발급 `routes/pat.py:96`). 포털 PAT 는 접두가 없는 JWT 라 접두 검사로는 못 잡는다 ⑤ `token_prefix` 와 다른 접두를 본다(자기 접두의 앞부분인 접두는 빼고 본다) ⑥ `workspace` 는 `workspace_header` 가 선언됐을 때만 받고 `^[A-Za-z0-9._:-]{0,120}$` 로 본다 ⑦ `await _verify_ext(...)` ⑧ `store.set_connection(...)` ⑨ `await _invalidate_gateway_cache(...)`(`:70-96`) ⑩ `logger.info("connection set: %s for %s (verify=%s, owner not verified)")` — 로그에 토큰은 남기지 않는다. ⓪~⑥ 은 네트워크를 쓰지 않는다. DELETE 는 CSRF 를 보고 내장 키에 404 를 내는 것 말고는 그 사람의 행이면 지운다. 권한을 잃은 사람의 행과 선언이 사라진 '고아' 행도 지운다 |
| PB9 | `connections.py:265-291` 옆 (새) `_verify_ext(spec, token, email)` | `_testscope_owner` 는 env 프록시를 따른다 | `httpx.AsyncClient(timeout=8, trust_env=False)` 로 만든다. 사람 토큰이 사내 프록시를 지나지 않는다. `mcp` 는 JSON-RPC `initialize`(Accept `application/json, text/event-stream`)가 200 이면 통과하고, 받은 `Mcp-Session-Id` 로 DELETE 를 보낸다(실패는 무시한다). `url` 은 Bearer GET 이 200 이면 통과한다. 401 · 403 은 400 「<label> 가 이 토큰을 거부했습니다 — 만료 · 폐기 · 잘못 복사」, 그 밖의 코드는 400(코드만), `httpx.HTTPError` 는 502(예외 이름만)다. `owner_field` 가 있으면 `:303-310` 과 같이 fail-closed 로 본다. 응답 본문은 돌려주지 않는다 |
| PB10 | `connections.py:345-346` `internal_connection` | `if service not in SERVICES: raise AuthError("unknown service", 404)` | `if service not in SERVICES and service not in _registry(request)` 로 바꾼다. 공유 비밀 검사(`:337-344`)는 그대로다. 선언이 사라지면 404 가 나고 게이트웨이가 호출을 거절한다 |
| PB11 | `backend/app/auth/user_store.py:349-358` 뒤 | `connection_meta` | (새) `connection_services(email) -> list[str]` 는 service 만 SELECT 한다. 토큰 칸은 읽지 않는다. 표(`:111-116`)는 그대로 둔다 |
| PB12 | `backend/app/auth/routes/session.py:217-225` · `agent/routes.py:658` 의 `entitlements` | 화면이 받는 합성 권한 목록 | (새) 합성 권한 `feat:connect` — 그 사람이 `connect` 선언이 있는 플랫폼의 `plat:<id>` 를 하나라도 가지면 넣는다. 화면 문(PF4)이 플랫폼 이름 없이 이것 하나만 본다 |
| PB13 | 추적 권한표(`backend/config/` 의 권한표 yaml) `:77-91` | matnexus(`:80-82`)는 「표준 위임 · PER_USER_SSO_APPS · MATNEXUS_SSO_*」, fmea(`:88-89`)는 「그쪽 답을 받아 정한다 · 표준 위임이면 …」 | 주석만 고친다 — 「박스 파일 항목의 `connect:` 로 토큰 등록 앱이 된다. 추적 파일의 `connect` 는 읽지 않는다」. 머리(`:1-13`)에 `connect:` 칸을 적는다. 행은 그대로 둔다(1-6 ④) |
| PB14 | `infra/scripts/check-egress.sh:102`(머리 주석 `:60` · `:78`) | `TESTSCOPE_BASE_URL` 을 본다 | 선택 사항이다. 포털 내부 정책 주소(게이트웨이 전용, `/internal/…/policy`) 의 `connections[*].mcp_url` 호스트도 알린다 |

#### 포털 화면 — 설정으로 그리는 카드 하나

| # | 자리 | 할 일 |
|---|---|---|
| PF1 | (새) `frontend/src/components/ExternalConnectionCards.tsx` | `TestScopeConnectionCard.tsx`(142줄)의 토큰 등록 꼴과 CSS(`ra-card` · `ra-lead` · `ra-status` · `ra-row ra-paste` · `ra-msg`)를 그대로 쓴다. 그러나 TestScope 카드를 복사하지는 않는다. 그 카드는 주소 · 응답 칸 · `mode === 'sso'` 갈래(`:85-107`) · 범위 문구(`:113-115`) · 자리표시(`:131`)가 TestScope 에 박혀 있다. 새 카드는 `apiFetch('/auth/connections/ext')` 를 한 번 부르고 `platforms ?? []` 를 그린다. 옛 백엔드(404)면 아무것도 그리지 않는다. 카드마다 `<h2>{label} 연결</h2>`, issue · note(글자로만, `dangerouslySetInnerHTML` 없음), `issue_url` 링크(`^https?://` 일 때만, `rel="noopener noreferrer"` · `target="_blank"`), 고정 안내 「이 토큰의 주인은 확인하지 않습니다 — 등록한 토큰의 계정 명의로 기록됩니다. 남의 토큰이나 HWAX 포털 토큰은 넣지 마세요.」 를 그린다. 연결됐으면 「연결됨 — …tail · 날짜」 와 해제 단추를, 아니면 붙여넣기 칸(자리표시 `${token_hint} 로 시작하는 ${label} 토큰`)과 등록 단추를 그린다. `workspace_label` 이 있으면 두 번째 칸을 더한다. `entitled` 가 아니면 칸 대신, `requestable` 이면 '내 권한' 화면(`?need=${need}`) 로 가는 '권한 요청 →' 링크를, 아니면 「관리자에게 문의」 를 그린다. 등록 · 해제는 `/auth/connections/ext/${encodeURIComponent(service)}` 로 PUT · DELETE 한다(CSRF 는 `apiFetch` 가 싣는다). 성공 문구는 verify 에 따라 「확인하고 연결했습니다.」 또는 「저장했습니다 — 토큰을 미리 확인하지 않습니다. 틀리면 첫 호출에서 그쪽이 거절합니다.」 다. 오류는 `errorDetail()` 로 보인다(`TestScopeConnectionCard.tsx:52` 와 같게). 해제 실패를 성공으로 보이지 않는다(`:68-72`). `orphans[]` 는 「더 이상 연결하지 않는 서비스 — 저장된 토큰 …tail」 과 해제 단추만 그린다. **코드에 플랫폼 이름이나 문구가 하나도 없으므로** 이것이 마지막 빌드다 |
| PF2 | `frontend/src/pages/TokenPage.tsx:11` | `import { ExternalConnectionCards } from '../components/ExternalConnectionCards';` 를 더한다 |
| PF3 | `TokenPage.tsx:262-263`(PAT 없는 화면) · `:297-298`('connect' 탭) | `<TestScopeConnectionCard />` 바로 뒤에 `<ExternalConnectionCards />` 를 둔다. RA · TestScope 카드는 손대지 않는다. PAT 없는 화면의 머리 설명(`:255-256`)은 RA 만 말하니 「외부 서비스 계정 · 토큰을 연결합니다」 로 고친다 |
| PF4 | `frontend/src/App.tsx:79` `RequireEntitlement need={['feat:api-token', 'plat:reportarchive']}` · `components/layout/AppHeader.tsx:79` `canTokens` · `:94` 메뉴 | 지금은 API 토큰 권한이나 RA 권한이 없으면 `/tokens` 에 못 들어간다. FMEA · MatNexus 권한만 있는 사람은 '내 권한' 으로 튕긴다. 그런데 게이트웨이 거절 안내는 그 사람을 `/tokens?tab=connect` 로 보낸다 | 두 곳의 조건에 `'feat:connect'`(PB12)를 더한다. 메뉴 이름은 `feat:api-token` 이 없으면 '연결 설정' 이다(지금 `:94` 와 같다). 같은 틈이 있던 TestScope 도 이것으로 함께 풀린다 |
| PF5 | `frontend/.eslintrc.cjs:24-26` | 인라인 스타일 예외 목록에 `TokenPage.tsx` · `RaConnectionCard.tsx` · `TestScopeConnectionCard.tsx` 가 있다 | 새 카드를 같은 목록에 넣는다 |

#### 게이트웨이(HWAXMcpGateway)

| # | 자리(`8e30ee5`) | 지금 | 할 일 |
|---|---|---|---|
| GW1 | `gateway.py:304-310` | 내장 두 개 | 글자 그대로 둔다. (새) `_BUILTIN_CONN = frozenset(PORTAL_CONN_BACKENDS)` 를 둔다. (새) 상태는 셋이다 — `_CONN_REG`(받은 선언 중 검사를 통과한 것), `_CONN_ACTIVE`(선언으로 만든 백엔드, 빠질 때까지 GW7 이 지킨다), `_CONN_STATUS`(키 → ok · down · no-list-token · collision · no-policy-row · invalid). GW5 가 선언 키를 `PORTAL_CONN_BACKENDS`(키→키)와 `PORTAL_CONN_META`({label, hint, workspace_header})에 넣고 뺀다. 내장 키는 덮지도 빼지도 않는다. 그래서 `:4143-4200` 의 라우팅 · 미등록 거절 안내(`:4162-4174`) · `mode=as-conn` 감사(`:4197-4199`)를 그대로 쓴다. 거절 문구 끝의 「공용 계정으로 대신 부르면 …」(`:4171-4172`)는 RA 사정이라 선언 키에는 붙이지 않는다 |
| GW2 | `:607-627` `_Backend` | `__init__(key, url, headers)`. `run()` 이 `self.headers` 로 영속 세션을 연다(`:627`) | `__init__(…, list_headers=None, list_only=False)` 로 바꾸고, `run()` 은 `{**self.headers, **(self.list_headers or {})}` 로 연다. 선언 백엔드는 `headers={}` 로 만든다. 그래서 `_call_as_user`(`:3906`)와 `_call_with_identity`(`:3931`)가 목록용 자격을 물려받을 수 없다. `list_fp` 는 목록 토큰 sha256 의 앞 12자다(비교 · 로그용) |
| GW3 | `:1387-1416` 정책 갱신 함수 | `backends` 만 읽는다(`:1401`) | 같은 JSON 의 `connections` 를 읽는다. 없으면 옛 포털이므로 {} 로 본다. (새) `_conn_validate(key, spec, 같은 응답의 backends)` 로 검사한다. 키 꼴이 틀리거나, `BACKENDS`(정적) · `heax-` · `_BUILTIN_CONN` · `PER_USER_SSO`(`:274`) · `IDENTITY_FWD` 와 겹치면 collision 이다. 같은 응답의 `backends` 에 행이 없으면 no-policy-row 다. URL 꼴 · 호스트 꼴 · `list_auth` · `workspace_header`(포털과 같은 막는 목록)가 틀리면 invalid 다. 통과한 것으로 `_CONN_REG` 를 한 번에 바꾼다(await 없이). 바뀌었으면 (새) `.conn_registry_cache.json` 을 0600 으로 쓴다. 조회가 실패하면 직전 값을 그대로 둔다(`:1402-1404` 와 같다) |
| GW4 | `:1372-1385` 정책 캐시 적재 함수 옆 | — | (새) `_load_conn_registry_cache()` 를 둔다. 권한 캐시가 실렸을 때(정책 준비 표지)만 읽는다 |
| GW5 | `:1172` 옆 (새) `_conn_reconcile(tg)` | — | 시작할 때 `wanted = dict(_CONN_REG)` 로 떠 둔다. 키마다 목록 헤더를 정한다 — `open` 이면 {} 다. `registered:<email>` 이면 `await _portal_connection(key, email)`(`:325`, 300초 캐시, `/conn-invalidate` 로 비워진다)을 부른다. None 이면 no-list-token 으로 두고 백엔드를 만들지 않는다. `_ConnLookupError` 면 이번 패스는 그 키를 건드리지 않는다. 토큰이 있으면 헤더는 {'Authorization': 'Bearer …'} 다. 만드는 순서는 `PORTAL_CONN_*` 에 먼저 넣기 → `_bypass_proxy_for([url])`(`:76`, heax 의 `:970` 과 같은 자리) → `_Backend(key, url, {}, lh, list_only=True)` → `DISCOVERED_META[key] = {label, description}`(`_app_meta` `:1795` 가 읽는다 — 앱 이름이 'Fmea' 가 되지 않게) → `await _first_connect(tg, key, b)`(`:1037`) → `_CONN_ACTIVE` 에 넣기다. 이미 있는데 url 이나 `list_fp` 가 다르면 그 세션만 멈추고 다시 만든다. 선언에서 빠진 키는 세션을 멈추고, `backends` · `DISCOVERED_META` · `_LAST_TOOLS` · `_FP` · `_LIVENESS_MISS` 에서 빼고, `_cache_flush_backend`(`:527`)를 부르고, `PORTAL_CONN_*` 에서 뺀다. `_CONN_ACTIVE` 에서는 **뒤이은 `_aggregate` 가 성공한 뒤에** 뺀다. 그 전에 경로가 남아 있어도 GW7 이 닫는다. 로그에는 키 · 호스트 · 상태만 남긴다 |
| GW6 | `:1050` `_revive_once` · `:1177` · `:4421` | 주기 루프와 `POST /refresh` 가 잠금 없이 같은 함수를 부른다. `_aggregate`(`:829`)와 재연결 루프(`:1141`)는 await 를 사이에 두고 `backends.items()` 를 돈다 | (새) `_REVIVE_LOCK`(anyio.Lock, lifespan 에서 만든다)로 `_revive_once` 전체를 감싼다. 두 패스가 동시에 돌면서 키를 넣고 빼면 `dictionary changed size` 가 나거나 같은 백엔드가 두 번 생겨 세션 태스크가 샌다. 지금의 heax 합류에도 같은 위험이 있다. 감싼 몸통의 첫 문장은 `revived \|= await _conn_reconcile(tg)` 다 |
| GW7 | `:1298-1323` `_deny_reason` — `:1312`(need) 뒤, `:1314`(SERVICE_GROUP) 앞 | 표에 없는 백엔드는 누구에게나 열린다(`:1323`) | `if backend_key in _CONN_ACTIVE and (backend_key not in _CONN_REG or not need): return "gateway_group"` 를 넣는다. 선언 백엔드는 행이 없거나 선언이 지워진 순간부터 내부 서비스 호출에도 닫힌다. `policy_not_ready` 를 쓰지 않는 까닭이 있다. 허브 안내는 그 사유에 「잠시 뒤 다시 부르라」 고 말한다(`_deny_text` `:1331-1342`). 지운 플랫폼에는 틀린 안내다 |
| GW8 | `:1183-1215` lifespan | 정적 → heax → `_aggregate`(`:1209`) → 권한 캐시(`:1213`) | `:1209` 앞에서 정책 캐시 적재 함수 → `_load_conn_registry_cache()` → 잠금 안에서 `await _conn_reconcile(tg)` 를 부른다. 선언 백엔드가 첫 카탈로그에 든다. `:1213-1215` 는 그대로 둔다 |
| GW9 | `:826-875` `_aggregate`(힌트 `:875`) | 앱의 `readOnlyHint` 만 본다 | `_CONN_ACTIVE` 키의 힌트는 「앱 힌트가 참이거나, 이름이 `read_tools` 에 있고 앱이 readOnlyHint=False 를 적지 않았을 때」 참이다. 선언된 읽기 도구는 노출 사본에 `ToolAnnotations(readOnlyHint=True)` 를 단다. `_readonly_denial`(`:3332-3346`)은 이미 `READ_TOOLS`(추적 파일 `read_tools.json`, 적재 때 한 번 읽는다 `:3318-3329`) **또는** 힌트를 보므로 고치지 않는다. `read_tools` 는 `read_tools.json` 에 더해지는 박스 목록이고 재기동 없이 바뀐다 |
| GW10 | `:421-438` `_cache_key` | 이름 접두(`_CACHEABLE` `:383`)로 캐시를 정한다 | `_CONN_ACTIVE` 키는 힌트가 참인 도구만 캐시한다. 선언하지 않은 도구는 캐시하지 않는다. 두 번째 쓰기가 무음으로 버려지지 않게 하려는 것이다 |
| GW11 | `:3847` `_call_shared` 맨 앞 | 상주 세션으로 부른다 | `b.list_only` 면 isError 를 **돌려준다**. 던지지 않으므로 `:4222-4249` 의 재연결 재시도가 돌지 않는다. 목록 전용 세션은 어떤 길로도 tools/call 에 쓰이지 않는다 |
| GW12 | `:4149-4150` PORTAL_CONN 분기의 `no-identity` | 신원이 없으면 `note = "no-identity"` 로 서비스 세션까지 내려간다(`:4220`) | `backend_key not in _BUILTIN_CONN` 이면 `_audit(..., mode="refused", note="no-identity")` 를 남기고 isError 「<label>: 사람 신원이 없는 호출은 받지 않는다(서비스 계정 없음)」 를 돌려준다. RA · TestScope 는 지금처럼 서비스 세션으로 간다 |
| GW13 | `:4177-4181` | `extra = {_wh: …} if _wh else None` 다음 `_call_as_user` | 선언 키면 `extra = {**(extra or {}), "Authorization": None}` 로 만든다. `_call_as_user`(`:3906-3912`)는 대소문자와 무관하게 기존 Authorization 을 떼고 None 값은 싣지 않으므로, 그 사람의 Bearer 하나만 나간다 |
| GW14 | `:4197-4199` as-conn 감사 | `caller=email, mode="as-conn"` | 선언 키면 `note="tok:<sha256(token)[:10]>"` 를 단다. 토큰 없이도 포털 사용자와 그쪽 토큰 주인을 이을 수 있다. RA 감사 줄은 그대로다 |
| GW15 | `:4278-4297` `/health` · `:4402-4421` `/refresh` | — | `/health` 에 `conn_platforms: {키: 상태}` 를 더한다. 무인증 응답에는 키와 상태만 싣고 이메일 · 주소는 싣지 않는다. `/refresh` 는 `_revive_once` 앞에서 정책 갱신 함수 를 부른다. 운영자가 새 플랫폼을 바로 붙일 수 있다. GW_TOKEN 이 필요한 것은 그대로다 |
| GW16 | `:38` `_MaskSecretsFormatter` | — | 선택 사항이다. 선언된 `token_prefix` 로 시작하는 8자 이상 문자열도 가린다 |
| GW17 | `.gitignore`(정책 캐시 파일 옆) | — | `.conn_registry_cache.json` 을 더한다 |
| GW18 | `provision-config.sh:836-842` · `:764-766` | 비밀 없는 `<P>_MCP_URL` 에 「✓ <키> — <주소>(⚠ 위임이 없다 — 토큰 없이 불러 앱이 거절한다. 켜려면 <P>_SSO_SECRET · <P>_SSO_URL)」, `:764-766` 은 「일반 앱에는 포털 등록 토큰 길이 없다」 | 두 문구만 고친다 — 「토큰 등록 앱이면 PER_USER_SSO_APPS 에서 빼고 포털 박스 권한표의 connect: 로 붙인다 — 같은 키의 정적 백엔드가 있으면 게이트웨이가 그 connect 를 collision 으로 무시한다」. `MANAGED`(`:828-830`)는 바꾸지 않는다. 선언 백엔드는 `gateway_config.json` 에 쓰지 않는다. ⚠ 10-21 초안의 「MANAGED 에 matnexus · fmea 를 넣는다」 는 틀렸다 — 넣으면 `:837-839` 가 `<P>_MCP_URL` 백엔드를 만들지 않고 건너뛴다 |
| GW19 | `:881-889` 이름 겹침 · `:4032` | 이름이 겹치면 **두 앱 모두** `<key>_` 접두로 바꾼다. 기존 앱이 쓰던 맨 이름은 사라져 `route.get(name)` 이 못 찾는다 | `_CONN_ACTIVE` 키의 도구만 접두로 낸다(`<key>_<이름>`). 기존 앱의 맨 이름은 그대로 둔다. MatNexus 가 붙으면 `get_material` · `how_to_measure` · `measurement_gaps`(MaterialTwin) · `get_ontology`(SignalForge)의 맨 이름이 바뀌어, 그 이름을 부르던 절차 · 핀 · 클라이언트가 'unknown tool' 이 된다(0절 실측) |
| GW20 | `README.md:94-100` | 등록 토큰 표가 RA · TestScope 둘 | 선언 방식(`connect:`)을 한 줄로 적고, 내장 둘과 구분한다 |

#### 포털 운영 스크립트(HWAXPortal `infra/`)

| # | 자리 | 지금 | 할 일 |
|---|---|---|---|
| PX1 | `infra/scripts/mcp-smoke.py:85-97` `_identity_only` · `:194`(`/tools-map` 으로 도구→백엔드) · `update-all.sh:2886-2925`(run_smoke · repair_mcp) | 신원 없이 부르는 스모크가 `per_user_sso` 키만 뺀다. 선언 백엔드는 `/tools-map` 에 나오지만 `gateway_config.json` 에는 없어서 빼지 못한다. 그러면 GW12 가 거절해 0성공 → rc 1 → repair_mcp 가 재프로비저닝 · **게이트웨이 재기동** → 다시 ✗ 가 update-all 마다 돈다 | `_identity_only` 가 게이트웨이 `/health` 의 `conn_platforms` 키도 「사람 신원으로만 답하는 백엔드 — 검사 못 함」 으로 뺀다. `test_update_all_health_gate.py:139-147` 에 그 꼴을 더한다 |
| PX2 | `update-all.sh:2130` | 다운 백엔드에 「매핑된 서비스 없음」 ⚠ | `conn_platforms` 키는 「외부 연결 플랫폼 — 그쪽 서버 상태」 로 알리고 복구 대상에 넣지 않는다 |

### 1-4. 토큰만 받는 MCP(FMEA)의 도구 목록

게이트웨이는 사람 없이 목록을 받아 둔다. 정적 백엔드는 설정의 `headers` 만 싣고 연다(`gateway.py:1187-1190` → `_Backend.run` `:627-630`). FMEA `:5190/mcp` 는
`initialize` 부터 401 이라 세션이 없고(`:636-642`), 목록이 0개이며(`:845-847`), 60초마다 다시 시도만 한다(`:1141-1160`). 그래서 `list_auth` 로 목록 받는 법만 설정으로 정한다.

| `list_auth` | 영속 세션(initialize · tools/list · 60초 확인) | tools/call |
|---|---|---|
| `open`(MatNexus) | 자격 없이 연다. 114개가 나온다 | 부르는 사람의 토큰으로 단발 세션을 연다 |
| `registered:<email>`(FMEA) | 그 포털 계정이 FMEA 카드에 등록한 토큰을 `list_headers` 에만 싣는다. 23개가 나온다 | 부르는 사람의 토큰으로 단발 세션을 연다. 목록 토큰은 닿지 않는다 |

목록 토큰이 호출에 쓰이지 않게 다섯 겹으로 막는다.

1. 선언 백엔드의 `_Backend.headers` 는 `{}` 다(GW2). `_call_as_user` 의 바탕 헤더에 목록 토큰이 없다.
2. 선언 키에서는 Authorization 을 한 번 더 뗀다(GW13). 그래서 누가 설정에 헤더를 넣어도 그 사람의 Bearer 하나만 나간다.
3. 신원 없는 호출은 `_call_shared`(`:4220`)에 닿기 전에 거절한다(GW12).
4. `_call_shared` 는 `list_only` 세션이면 isError 를 돌려준다(GW11). 재연결 재시도(`:4249`)도 같다.
5. `PER_USER_SSO` 와 같은 키는 선언으로 받지 않는다(GW3). 같은 키가 있으면 위임 분기(`:4087-4094`, if/elif)가 신원 없는 호출에 `note="no-identity"` 만 달고
   PORTAL_CONN 분기(3)를 건너뛰어 상주 세션까지 내린다. 설계안 하나(minimal-diff)에 실제로 있던 구멍이다. cae00 에는 지금 `fmea` · `matnexus` 위임 항목이 없다(0절).

토큰을 누구 것으로 할지는 이렇게 권한다. FMEA `/signup` 으로 **목록 전용 FMEA 로컬 계정**을 만든다. 그 계정의 토큰을, `list_auth` 가 가리키는 포털 계정
(예: 공용 관리자 로컬 계정)으로 로그인해 FMEA 카드에 등록한다. 주인 확인이 없으므로 이렇게 등록할 수 있다.
사람의 토큰을 쓰면 FMEA 로그에 그 사람이 60초마다 목록을 부른 것으로 남는다. 그 사람이 토큰을 폐기하거나 떠나면 도구도 사라진다.

| 상황 | 동작 |
|---|---|
| 목록 토큰을 바꿀 때 | 카드에서 다시 등록하면 포털이 `/conn-invalidate` 를 부른다(`gateway.py:4350-4392`, 이메일 단위). 다음 패스가 `list_fp` 변화를 보고 그 세션만 갈아 끼운다. 재기동이 없다 |
| 목록 계정이 아직 등록하지 않았을 때 | 상태가 `no-list-token` 이 되고 백엔드를 만들지 않는다 |
| 목록 토큰이 만료 · 폐기됐을 때 | 상태가 `down` 이 된다. 직전 목록은 `AGG_STALE_ROUNDS`(`:983`, 기본 10)번 집계까지 남았다가 빠진다. 두 경우 모두 `/health` `conn_platforms` 와 update-collab ⑥ 에 보인다 |
| FMEA 가 목록을 토큰 없이 열어 줄 때(3절 ①) | `list_auth: open` 한 줄로 바꾼다. 목록에 쓰는 자격이 아예 사라진다 |

카탈로그는 목록 계정이 받은 tools/list 하나를 모두가 본다. FMEA 가 역할마다 다른 목록을 준다면 그 이름들이 `plat:fmea` 를 가진 모두에게 보인다.
그래도 호출은 각자의 토큰으로 가므로 FMEA 가 호출마다 권한을 판정한다.
쓰지 않기로 한 길이 둘 있다. 박스 비밀 파일에 목록 토큰을 두는 길은 비밀 저장소가 하나 더 생기고 토큰을 바꿀 때 셸이 필요하다.
첫 호출 때 그 사람의 토큰으로 목록을 받는 길은 누가 부르기 전까지 카탈로그가 비어 있고 건강 신호도 없다.

### 1-5. 본인 확인 정책

**새 플랫폼은 기본이 '확인 안 함'이다**(사용자 결정 10-21). 토큰을 등록할 때 포털은 그쪽에 주인을 묻지 않는다. 그래서 FMEA 에 본인 확인 API 를
요청하지 않아도 된다. 대신 아래 여섯 가지를 본다.

| # | 막는 것 | 어떻게 |
|---|---|---|
| 1 | 토큰 바꿔치기 — PAT 를 훔친 사람이 피해자의 행에 자기 토큰을 넣으면 피해자의 이후 입력이 공격자 계정에 쌓인다 | ext PUT · DELETE 는 브라우저 세션 + CSRF 만 받고 PAT 는 받지 않는다(PB8) |
| 2 | 쓸 수 없는 사람의 토큰이 쌓이는 것 | `ensure(principal, "plat:<id>")`(`deps.py:86`). 권한은 요청마다 다시 계산된다(`deps.py:47`) |
| 3 | 헤더 주입 | `Bearer ` 를 뗀 뒤 `^[\x21-\x7e]{8,512}$` 로 본다 |
| 4 | HWAX 포털 PAT 가 남의 서버로 가는 것 | `iss == settings.jwt_issuer` 인 JWT 는 검증이나 저장보다 먼저 거절한다 |
| 5 | 다른 서비스 토큰(`rat_` · `tsc_pat_` · 다른 플랫폼)을 잘못 붙여 넣는 것 | `token_prefix` 와 다른 접두를 네트워크를 쓰기 전에 본다 |
| 6 | 오타 · 만료 토큰 | `verify`(none · mcp · url)로 유효성만 본다. `trust_env=False` 다 |

켜는 법도 설정 하나다. 주인을 묶어야 하는 플랫폼은 `verify: url` · `verify_url` · `owner_field` 를 적는다. 그러면 이메일이 없거나 다를 때 거절한다.
TestScope(`connections.py:301-310`)와 같은 fail-closed 다. 코드는 바뀌지 않는다.

**RA · TestScope 는 지금 그대로 둔다.**
- RA 는 `_ra_profile` 과 같은 이메일 확인, 부서 라우트를 그대로 쓴다.
- TestScope 는 `_testscope_owner`(`:265-290`)와 같은 이메일 확인(`:301-310`)을 그대로 쓴다. 두 PUT 은 지금처럼 PAT 도 받는다.
- `list_connections`(`:232-248`)의 응답은 한 글자도 바꾸지 않는다. 새 목록은 PB7 의 새 주소로 낸다.
- 일반 라우트는 `/ext/` 아래에 두고 내장 키에는 404 를 낸다. 포털 파서(PB3)와 게이트웨이(GW3)도 내장 키를 받지 않는다. 그래서 설정만으로 RA · TestScope 를 확인 없는 길로 옮길 수 없다.
- 게이트웨이의 내장 META(RA `X-Workspace-Slug`, TestScope None)는 그대로다. 위임 분기(`:4087`)가 먼저 도는 것도 그대로라 `RA_SSO_SECRET` · `TESTSCOPE_SSO_SECRET` 두 갈래가 남는다. 내장 키의 신원 없는 서비스 세션 경로(`:4149-4150` → `:4220`)도 남는다.

받아들인 위험도 있다. A 가 B 의 토큰을 등록하면 그쪽에는 B 가 한 것으로 남는다(그 토큰을 A 가 이미 손에 쥐었다는 뜻이기도 하다).
카드의 안내 문구, 감사의 `caller=<포털 이메일>` 과 `tok:` 지문, 카드에 보이는 등록 시각으로 나중에 추적한다.

### 1-6. 권한표 순서 · 프록시 · 쓰기 도구

**권한표 순서(정책 구멍 막기)** — 표에 없는 백엔드는 '전체 공개'(`gateway.py:1323`)다. 이 구멍을 운영 순서에 맡기지 않고 구조로 막는다.
게이트웨이는 권한을 등록 토큰보다 먼저 본다(`:4042` → `:4143`). 그래서 CAE그룹(추적 권한표 `:18-20` `grants: ["*"]`)이 아닌 사람은 `plat:<id>` 승인이 먼저다.

1. `connect` 는 그 항목의 `gateway:` 에 백엔드 키가 있을 때만 산다(PB3). 행 없이 선언만 있을 수 없다.
2. 행과 선언은 한 파싱, 한 응답으로 나간다(PB5). 게이트웨이가 행 없는 선언을 받아도 no-policy-row 로 둔다(GW3).
3. 게이트웨이도 닫힌 쪽으로 판정한다(GW7). `_CONN_ACTIVE` 키는 행이 없거나 선언이 지워지면 `gateway_group` 으로 막힌다. 부팅 캐시, 오래된 정책, 빼는 동안의 틈 모두 같다.
4. 박스 항목을 지우면 추적 행(추적 권한표 `:77-91`)이 되살아나 행이 연결보다 오래 남는다. 그래도 선언이 `_CONN_REG` 에서 빠지는 순간 GW7 이 닫는다. `/internal/connections` 도 404 를 내 호출이 거절된다. 백엔드는 다음 패스에서 떼어 낸다.
5. update-collab ⑥ 의 정책 구멍 검사(`update-collab.sh:546-557`)는 정적 · heax 백엔드를 위해 그대로 돈다. 선언 백엔드는 행이 있어야 생기므로 이 검사를 늘 통과한다.
6. 숨긴 플랫폼은 권한 요청을 받지 않는다(권한 모듈 `routes.py:104-108` → 404). 관리자 목록에서도 빠진다(`:77` · `:215`). `hide_unless_routed: true` 인데 그 박스에 타일이 없으면 카드는 '권한 요청' 대신 「관리자에게 문의」 를 보인다. 그래서 MatNexus 는 타일이 생길 때까지 `false` 로 둔다. FMEA 타일(`systems.cae00.yaml`)은 카탈로그를 다시 읽은 뒤에 살아난다.

**프록시**
- 게이트웨이는 백엔드를 만들기 전에 `_bypass_proxy_for([mcp_url])`(`:76`)를 부른다. httpx 는 클라이언트를 만들 때 env 를 읽으므로 단발 세션(`_oneshot`)도 이 설정을 따른다. `NO_PROXY` 에 적을 수 없는 호스트는 invalid 로 두고 받지 않는다.
- 포털의 `_verify_ext` 는 `trust_env=False` 로 만든다.
- 프록시를 거쳐야만 닿는 호스트면 닫힌 채로 실패한다(verify 502, 백엔드 down). 토큰이 프록시로 새지는 않는다. 길은 1-7 ② 로 먼저 확인한다. FMEA · MatNexus 는 직접 닿는다(0절).
- 박스 env 의 `NO_PROXY` 를 손댈 일은 이 길에는 없다.

**쓰기 도구**
- FMEA 의 23개는 모두 readOnlyHint 가 없어 쓰기로 본다. 읽기 전용 포털 PAT(scopes=[read])로 붙은 Claude 는 `read_tools.json` 의 `READ_TOOLS` 나 힌트, `read_tools` 에 든 도구만 부른다(`_readonly_denial` `:3332-3346`). 지금 그대로면 FMEA 23개가 전부 'read_only' 로 거절된다.
- `read_tools` 는 닫힌 쪽 허용 목록이다. 쓰기 도구를 넣으면 읽기 전용 PAT 가 그 도구를 부를 수 있게 되고, 결과가 캐시돼 두 번째 쓰기가 무음으로 버려진다. 앱이 readOnlyHint=False 를 적었으면 앱이 이긴다(GW9).
- 선언 키의 응답 캐시는 선언된 읽기 도구만 쓴다(GW10).
- 쓰기 도구 두 개는 토큰 주인 명의로 FMEA 에 덮개를 저장한다. 이 사실은 카드 `note` 에 적는다. FMEA 에 readOnlyHint 를 청하는 것(3절 ③)은 그대로 남는다.

**실패할 때**

| 경우 | 결과 |
|---|---|
| `connect` 오타 | 그 블록만 버리고 알림을 남긴다(배선 설정 · update-collab ①). 카드와 백엔드가 없다. 이미 붙어 있던 플랫폼이면 다음 패스에서 떼어진다 |
| 박스 권한표의 YAML 이 깨졌을 때 | 포털은 직전 정책을 쓴다(`policy.py:358-365`). 게이트웨이도 직전 선언을 쓴다 |
| 포털이 죽었을 때 | 게이트웨이는 직전 정책과 선언을 쓴다(디스크 캐시). 사람 호출은 conn-lookup-error 로 거절된다(`:4157-4160`). 다른 신원으로 대신 부르지 않는다 |
| 게이트웨이가 죽었을 때 | 등록은 된다. 포털의 `_invalidate_gateway_cache` 가 False 를 남긴다(`connections.py:70-96`) |
| 그쪽 MCP 가 죽었을 때(FMEA 서버 PC 가 꺼졌을 때 등) | `/health` 에 false 로 보인다. 호출은 연결 실패 안내로 끝난다 |
| 버전이 섞였을 때 | 옛 게이트웨이는 `connections` 를 무시한다. 새 게이트웨이와 옛 포털이면 선언이 비어 있다. 옛 화면은 새 주소를 부르지 않는다. 어느 조합도 안전하다. 10-21 초안(앱마다 상수)과 달리 「게이트웨이가 먼저 뜨면 포털 404 를 '등록 없음' 으로 30초 캐시」(`gateway.py:344-350 · 357-359`) 문제도 없다 — 선언은 포털이 낸 것만 산다 |

### 1-7. 다음 플랫폼을 붙이는 운영 절차

1. 그쪽 팀에서 네 가지를 받는다. MCP 주소, 토큰 접두, 사람이 토큰을 발급하는 곳, 토큰 없이 initialize · tools/list 가 되는지다. 코드는 받지 않는다.
2. cae00 에서 프록시 없이, 토큰 없이 미리 본다. 비밀은 보내지 않는다. 결과가 200 이면 `list_auth: open`, 401 이면 `registered:<포털 이메일>` 이다. 연결이 끊기면 길부터 고친다(프록시가 살아 있는 호스트를 가리는 일이 있다).
   ```bash
   curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -X POST \
     -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"precheck","version":"0"}}}' \
     <MCP 주소>
   ```
3. 그쪽 도구 이름이 지금 게이트웨이 도구와 겹치는지 본다(GW19 가 들어오기 전에는 겹치면 붙이지 않는다).
4. 박스 권한표(`~/Projects/HWAXPortal/backend/config/` 의 권한표 `.local.yaml`) 의 `hwax-batch` 블록 밖에 항목과 `connect:` 를 적고 저장한다(1-2 꼴). 포털은 다음 요청부터 카드를 보인다.
5. `~/Projects/HWAXPortal/infra/scripts/update-collab.sh --check` 를 돌린다. 아무것도 바꾸지 않는다. ① 에 새 블록의 알림이 없어야 하고, ⑥ 이 초록이어야 한다.
6. 게이트웨이에 바로 반영하려면 아래를 부른다. 토큰은 명령줄에 나타나지 않는다. 그냥 두면 최대 약 2분 안에 스스로 붙는다.
   ```bash
   python3 -c 'import json,os;print("header = \"Authorization: Bearer %s\"" % json.load(open(os.path.expanduser("~/Projects/HWAXMcpGateway/gateway_config.json")))["_gateway"]["token"])' \
     | curl -s --noproxy '*' -K - -X POST http://127.0.0.1:9110/refresh
   ```
7. `list_auth: registered:<email>` 이면 그 포털 계정으로 `/tokens?tab=connect` 에 들어가 목록용 토큰을 등록한다. 그 뒤 6번을 한 번 더 부른다.
8. 확인한다.
   - `curl -s --noproxy '*' http://127.0.0.1:9110/health` 에서 `conn_platforms.<키>` 가 `ok` 이고 `backends.<키>` 가 true 여야 한다.
   - `/tools-map` 에 그 플랫폼의 도구가 보여야 한다.
   - 시험 사용자가 카드에 토큰을 등록하고 Claude 에서 읽기 도구 하나를 부른다. 게이트웨이 감사에 `mode=as-conn` 과 `tok:` 지문이 남아야 한다.
   - 등록하지 않은 사용자에게는 `/tokens?tab=connect` 를 가리키는 거절 안내가 나와야 한다.
9. `/tools-map` 을 보고 같은 파일의 `read_tools` 에 읽기 도구의 원래 이름을 채운다. 저장하면 바로 반영된다.
10. 할 일은 여기까지다. 빌드 0, 코드 0, 재기동 0 이다. `backend/.env` · `infra/.env` · `provision.env` · `gateway_config.json` 도 손대지 않는다.
11. 되돌릴 때는 `connect:` 블록이나 그 항목을 지우고 6번을 부른다. 떼어 내기 전까지도 GW7 이 닫아 둔다. 저장된 토큰은 사용자가 카드의 '고아' 줄에서 지운다.

### 1-8. 시험

**포털**
- 박스 권한표 오버레이 시험 파일
  - 추적 권한표의 `connect` 는 떼어지고 알림이 남는다.
  - 박스 파일의 `connect` 는 항목을 통째로 바꿀 때도 살아남는다.
  - `gateway:` 를 뺀 오버레이 항목은 `connect` 도 버린다.
- (새) `test_ext_connections.py` — 파싱
  - 정상 블록 둘(fmea · matnexus)이 읽힌다.
  - 아래 경우는 그 블록만 버리고 알림을 남기며, 나머지 정책은 그대로 읽힌다. `gateway:` 밖의 backend, 내장 키, `heax-` 접두, 중복 키, `?token=` · `user@` · `#` 이 든 주소, `javascript:` issue_url, 틀린 `list_auth`, 막는 헤더(Authorization · X-Hwax-User), `mcp` 모드의 `owner_field`.
- 재기동 없는 반영
  - 박스 파일에 `connect` 를 더하면 다음 `GET /auth/connections/ext` 에 나온다.
  - 지우면 사라지고 `/internal/connections/<svc>` 가 404 를 낸다.
- 포털 내부 정책 주소(게이트웨이 전용, `/internal/…/policy`)
  - `connections` 의 키가 모두 `backends` 에 있다(불변식).
  - 공유 토큰이 틀리면 403 이다.
- `GET /auth/connections/ext`
  - `platforms[]` 의 entitled · need · requestable 이 맞고, 숨긴 키면 requestable 이 false 다.
  - `orphans[]` 가 나온다.
  - 본문에 `mcp_url` · `verify_url` · `list_auth` 문자열이 없다.
- 합성 권한 — 선언 플랫폼 권한이 하나라도 있으면 `feat:connect` 가 있고, 없으면 없다.
- ext PUT
  - CSRF 가 없으면 403, Bearer PAT 면 401 또는 403 이다.
  - 모르는 service 와 `reportarchive` · `testscope` 는 404 다.
  - `plat:` 권한이 없으면 403 이다.
  - `'Bearer fmea_x…'` 와 `'fmea_x…'` 가 같은 값으로 저장된다.
  - 접두가 다르거나 다른 플랫폼의 접두면 400 이다. 자기 접두의 앞부분인 접두는 통과한다.
  - 개행 · 공백이 든 토큰은 400 또는 422 다.
  - 포털 JWT(`iss=jwt_issuer`)는 400 이고 네트워크를 쓰지 않는다.
  - `verify: none` 은 저장하고 캐시 무효화를 부른다.
  - `mcp` 는 200 이면 저장하고, 401 이면 저장하지 않고, 연결 실패면 502 다.
  - 클라이언트가 `trust_env=False` 로 만들어진다.
  - caplog 에 토큰이 없다.
  - `owner_field` 가 있으면 다른 이메일은 400, 빈 이메일은 502 다.
- ext DELETE — CSRF 가 필요하다. 고아 행도 지운다. 무효화를 부른다.
- 호환
  - `test_testscope_connection.py`(목록 키 집합 단언 `:165` 포함) · `test_ra_sso.py` · 권한 제어 시험 파일 가 고치지 않고 통과한다.
  - `PUT /auth/connections/testscope` 는 여전히 주인을 확인한다.
- 운영 스크립트 — `mcp-smoke.py` 가 `conn_platforms` 키를 부르지 않는다(PX1).

**화면**
- `tsc` 와 `npm run build` 가 통과한다.
- 새 주소가 404 면 아무것도 그리지 않는다. 선언이 둘이면 카드가 두 장이다.
- entitled 가 false 면 요청 링크나 「관리자에게 문의」 를 그린다.
- PUT · DELETE 주소에 `encodeURIComponent` 가 걸린다.
- `feat:connect` 만 있는 사용자가 `/tokens?tab=connect` 에 들어가고 메뉴에 '연결 설정' 이 보인다.
- `/tokens?tab=connect` 를 캡처해 확인한다(`e2e/ui.spec.ts:12` 의 경로 목록에 이미 있다).

**게이트웨이**(`test_gateway.py` · `test_provision_urls.py`)
- 선언 하나로 `_Backend(headers={}, list_only=True)` 가 생긴다. `registered` 면 `list_headers` 를 모의 `/internal/connections` 에서 받는다.
- `_call_as_user` 의 최종 헤더에는 그 사람의 Bearer 하나만 있다. 목록 토큰은 없다. 소문자 `authorization` 이 섞여 있어도 같다.
- `list_only` 백엔드에서 `_call_shared` 는 네트워크도 재연결도 없이 isError 를 돌려준다.
- 신원 없는 호출은 거절되고 감사에 `refused` · `no-identity` 가 남는다. 내장 testscope 의 신원 없는 호출은 여전히 서비스 세션으로 간다(회귀 시험).
- 충돌 — `PER_USER_SSO` 와 같은 키는 collision 이고 위임 분기로 새지 않는다. 정적 키 · `heax-` · `testscope` · `IDENTITY_FWD` 도 collision 이다. 같은 응답의 `backends` 에 없는 키는 no-policy-row 다. `connections` 가 없는 옛 포털 응답이면 선언이 비고, 기존 백엔드는 그대로다.
- 이름 겹침 — 선언 백엔드의 도구가 기존 앱과 겹치면 선언 쪽만 `<key>_` 접두가 붙고 기존 맨 이름은 그대로 불린다(GW19).
- 권한 — 행 없는 선언 키는 SERVICE_GROUP 에도 `gateway_group` 이다. 선언을 지운 직후, 패스 전에도 `gateway_group` 이다. 다음 패스에서 세션과 경로가 사라지고, `_aggregate` 가 성공한 뒤 `_CONN_ACTIVE` 에서 빠진다.
- 프록시와 목록 토큰 — `_first_connect` 전에 `_bypass_proxy_for` 가 불려 `NO_PROXY` 에 호스트가 들어간다. 적을 수 없는 호스트는 invalid 다. 목록 토큰 지문이 바뀌면 그 세션만 갈아 끼운다. 목록 계정이 404 면 no-list-token 이고 백엔드가 없다.
- 동시성 — `/refresh` 와 주기 패스를 함께 돌려도 백엔드는 한 번만 생기고 RuntimeError 가 없다(`_REVIVE_LOCK`).
- 읽기 도구 — `read_tools` 가 힌트와 노출 사본의 readOnlyHint 를 세운다. 앱이 False 를 명시하면 앱이 이긴다. 읽기 전용 PAT 는 선언된 읽기만 부른다. `read_tools.json` 항목도 그대로 통과한다(더하기). 선언되지 않은 도구는 `_cache_key` 가 None 이다.
- 감사 — 선언 키 감사에 `tok:<10 hex>` 가 남고, 감사 파일에 토큰은 없다. RA 감사 줄은 그대로다.
- 부팅과 상태 — 캐시 두 개가 있고 포털이 503 이면, `open` 선언은 첫 카탈로그에 들고 `registered` 는 다음 패스에 든다. 캐시 파일은 0600 이고 토큰 꼴 문자열이 없다. `/refresh` 가 정책을 먼저 받는다. `/health` `conn_platforms` 에는 상태만 있다.
- `test_provision_urls.py` — 새 GW18 문구를 본다. `MANAGED` 는 그대로다. 기존 정확-dict 시험(`:885-923`)은 고치지 않고 통과한다.
- 회귀 — `test_gateway.py` 의 RA · TestScope 묶음(`:1709-1880`)이 고치지 않고 통과한다.

**손 시험(cae00, 반영 뒤)**
- `update-collab.sh --check` 에서 ① 알림이 없고, ⑥ 이 초록이고, `conn_platforms` 가 ok 다.
- `/tools-map` 에 FMEA 23개와 MatNexus 114개가 있고, MaterialTwin · SignalForge 의 `get_material` · `how_to_measure` · `measurement_gaps` · `get_ontology` 가 맨 이름으로 그대로 불린다.
- 각 카드에 등록하고 읽기 도구 하나를 부르면 `mode=as-conn` 과 `tok:` 가 남는다.
- 등록하지 않은 사용자는 거절된다.
- 쓰기 도구를 두 번 부르면 FMEA 에 두 건이 남는다(캐시되지 않는다).
- update-all 한 번이 MCP 스모크에서 게이트웨이를 재기동하지 않는다(PX1).

### 1-9. 남은 질문

1. **FMEA(3절 ①)** — initialize · tools/list 를 토큰 없이 열 수 있는가. 열 수 있으면 `list_auth: open` 으로 끝난다. 못 열면 목록 계정은 누구로 하는가(권장은 전용 FMEA 계정 + 어느 포털 계정).
2. **MatNexus** — `:8010/api/auth/me` 가 유효한 `mnx_pat_` 에 200, 틀린 토큰에 401 을 내는가. 그렇다면 `verify: url` 로 바꾼다(재기동 없음). `owner_field` 는 끈 채로 두는가.
3. **평문 토큰** — `users.sqlite` 는 0644 이고 토큰은 평문이다(4절 끝). 박스에서 chmod 600 을 할지, 포털이 기동할 때 맞추게 할지(코드), 암호화를 넣을지 정한다. 플랫폼이 늘 때마다 사람마다 토큰이 하나씩 더 쌓인다.
4. **세션 전용 등록** — ext 등록은 세션 전용으로 하고 PAT 를 거절하는 데 동의하는가. RA · TestScope 는 지금처럼 PAT 도 받는다.
5. **신원 없는 호출** — 에이전트서버의 잡이나 절차가 사람 없이 FMEA · MatNexus 를 부를 일이 있는가. 이 설계는 그런 호출을 거절한다. 절차 사전 점검(`procedures/routes.py:417-453` `_ra_precheck`)은 RA 만 본다 — 선언 플랫폼 단계는 등록이 없으면 실행 중에 게이트웨이에서 실패한다. 같은 점검을 선언 플랫폼에도 둘지 정한다.
6. **FMEA 읽기 도구** — 첫 등재 뒤 `/tools-map` 을 보고 `read_tools` 를 채울지, FMEA 가 readOnlyHint 를 달 때까지 기다릴지(3절 ③) 정한다.
7. **도구 영역** — `tool_areas.json` 의 `apps` 에 키가 없으면 그 도구는 `unclassified` 로 간다. 선언에 `area` 칸을 둘지, 게이트웨이가 `desc` 로 가를지 정한다.
8. **에이전트서버 캐시** — `agent_cache`(HWAXAgentServer `app.py:2385`)는 도구를 묶은 에이전트를 기한 없이 둔다. 새 도구는 `search_tools` · `invoke_tool` 로는 바로 닿는다. 캐시가 바뀔 때까지 그것으로 충분한지, 카탈로그가 바뀌면 캐시를 비우게 할지(별도 요청) 정한다.
9. **반영 지연** — 최대 약 2분(정책 60초 + 패스 60초)이다. `/refresh` 로 충분한지, 포털이 mtime 변화를 보면 게이트웨이를 깨울지 정한다.
10. **RA · TestScope 이관** — 나중에 RA · TestScope 도 `connect` 꼴로 옮길지 정한다. 그러려면 `owner_field`, 부서 고르기, sso 갈래 표지가 더 든다. 이번 범위에는 넣지 않는다.

---

## 2. 함께 고칠 문서 · 10-21 초안 정정

| # | 자리 | 할 일 |
|---|---|---|
| D1 | 포털 `docs/sso-delegation/server-setup.md` C(MatNexus 표준 위임) · D(FMEA 「그쪽 답을 받은 뒤」) | 1-7 절차로 다시 쓴다. cae00 의 타일 파일은 `systems.cae00.yaml`(`backend/.env` `CATALOG_PATH`)이지 `systems.local.yaml` 이 아니다(C4 `:75` · D `:105` 가 틀렸다) |
| D2 | `docs/sso-delegation/PLAN.md:64-90`(§5) · `checklist.md:29-40` · `context-notes.md:140`(D-18) · `:166`(D-20) · `CLAUDE.md:134` · `backend/config/changelog.yaml:113-117` | 지우지 말고 「10-21 — MatNexus · FMEA 는 토큰 등록(외부 연결 `connect:`)으로 바뀜」 을 덧붙인다 |
| D3 | `docs/sso-delegation/fmea-request.md` | (나) 개인 토큰이 채택안이다. 「본인 확인 API」 요구는 빼고(1-5), 목록 공개 · readOnlyHint · 상시 운영(3절)으로 바꾼다 |
| D4 | 게이트웨이 `README.md:94-100` | GW20 |
| D5 | 10-21 초안 2절(P1~P10 · G1~G6, 앱마다 TestScope 를 복사하는 길) | 이 문서 1절이 대신한다. 특히 초안 G5(「MANAGED 에 넣는다」)는 틀렸다(GW18) |
| D6 | 10-21 초안의 보안 메모 「10-03 D-13 에서 Fernet 을 걷었다」 | 틀렸다. 등록 토큰은 처음부터 평문이다. 10-03 D-8 이 자동 연결용으로 Fernet 을 계획했으나 커밋되지 않은 작업 트리째 D-13 에서 걷혔다(`context-notes.md:39-43 · 87-92`, `git log -S Fernet` 결과 없음) |

## 3. FMEA Agent 쪽에 청할 것

1. **토큰 없이 `initialize` · `tools/list` 를 열어 줄 수 있습니까?** 지금은 `initialize` 부터 401 `unauthenticated` 다. 열어 주시면 저희 쪽 목록 전용 계정이 필요 없어집니다(1-4). TestScope · MatNexus 는 목록을 열고 데이터를 내는 호출만 토큰을 요구합니다.
2. 토큰 수명 · 폐기 방법 · 읽기 전용 토큰이 있는지 알려 주십시오.
3. 도구에 `readOnlyHint` 를 달아 주십시오. 지금 23개 모두 없어, 읽기 전용 자격으로 붙은 Claude 에서는 전부 쓰기로 보고 막힙니다. 쓰는 도구(`add_material_baseline_overlay_tool` · `add_spec_overlay_tool`)와 읽는 도구를 가를 수 있게 하려는 것입니다.
4. Host 허용목록을 쓴다면 게이트웨이가 부르는 주소(`<FMEA_호스트>:5190`)를 포트까지 그대로 넣어 주십시오.
5. 서버가 개인 PC 에서 도는 것으로 보입니다. 그 PC 가 꺼지면 도구가 사라지니 상시 운영 계획을 알려 주십시오.

본인 확인 API 는 청하지 않는다 — 새 플랫폼은 주인 확인을 하지 않기로 했다(1-5). 있다면 `verify: url` 로 켤 수 있다.

## 4. 반영 순서(운영 쪽 — 요청 아님)

⚠ 재기동이 드는 단계(②③)는 다른 서비스 작업 · 심의가 없는 때에, 운영 담당이 정한 시각에만 한다.

1. dev — 포털을 빌드해 Drive 에 올린다(`build-all-to-drive.sh portal`). 화면 `dist` 는 git 이 아니라 Drive 로 오므로 박스의 git pull 만으로는 카드가 안 보이고, update-all §6 이 dist 어긋남을 알린다(`update-all.sh:2416-2427`).
2. cae00 — 포털을 새 판으로 올린다(update-all 또는 `deploy-all-from-drive.sh portal`). 이때 박스 권한표에 아직 `connect:` 가 없으니 화면은 그대로다.
3. cae00 — 게이트웨이 리포를 새 판으로 올린 뒤(지금 박스 HEAD 는 `e617012` 로 origin/master 보다 뒤다. update-collab 은 게이트웨이 리포를 당기지 않는다) 게이트웨이를 다시 띄운다(update-collab).
4. cae00 — 1-7 의 ②~⑨ 를 FMEA · MatNexus 로 한다. MatNexus 는 GW19 가 들어왔는지 먼저 본다(이름 4개 겹침). FMEA 는 목록 전용 계정의 토큰을 등록한다(3절 ① 답 전까지).
5. 권한 — CAE그룹이 아닌 사람은 포털 '내 권한' 에서 FMEA Agent(`plat:fmea`) · MatNexus(`plat:matnexus`)를 요청하고 관리자가 승인한다. MatNexus 는 박스 항목에서 `hide_unless_routed: false` 여야 요청할 수 있다(1-2).
6. 사용자 — 그쪽에서 토큰 발급 → '외부 연결' 카드에 붙여 넣기(`Bearer ` 가 붙어 있어도 된다) → Claude 에서 읽기 도구 하나로 확인. 게이트웨이 감사에 `mode=as-conn` 이 찍힌다.

> **함께 봐 주실 것(보안)** — 등록 토큰은 포털 SQLite `connections` 표에 **처음부터 평문**으로 저장된다(`user_store.py:111-116` · `:314-319`).
> cae00 의 `/data/svc/portal/users.sqlite` 는 지금도 **0644** 다(10-21 확인). 플랫폼이 늘수록 사람마다 토큰이 더해지므로 파일 권한(600)이나 암호화를 검토해 달라(1-9 ③).

담당: HWAX Portal (koo.park)
