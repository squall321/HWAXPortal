# 사람별 위임(ste 방식) — 서버 쪽에서 사람이 할 일

> 대상: 포털 운영자(cae00) · RA 담당 · TestScope · MatNexus 운영 담당 · 2026-10-03(C · D 는 10-21 — 외부 연결 `connect:` 로 다시 씀)
> 코드는 리포에 들어가 있다. 아래는 **박스마다 다른 값과 비밀**이라 사람이 넣는다(비밀·사내 주소는 리포에 적지 않는다).
> RA 위임 비밀은 `openssl rand -hex 32` 로 만들어 RA 담당과 같은 값을 쓴다(다른 서비스와 묶지 않는다).

## 원칙 — 비밀은 서비스 쪽이 준비된 뒤에 넣는다

포털·게이트웨이 쪽 비밀(`RA_SSO_SECRET`)이 생기는 순간 게이트웨이가 그 서비스를 **사람별 위임으로만** 부른다.
서비스가 아직 `/api/auth/sso` 를 모르면 그 서비스 도구 호출은 전부 거부된다(서비스 계정으로 대신 부르지 않는다). 그래서 이 값은
`start.sh` 가 자동으로 만들지 않는다 — ste 의 `STE_SSO_SECRET` 과 다른 점이다.

## A. Report Archive

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| A1 | RA 코드 | [ra-request.md](ra-request.md) — 옛 `sso/heax.py` 되살리기 + 부서 헤더 없으면 홈 부서 | RA 담당 |
| A2 | RA 서버 `backend/.env` | `HEAX_SSO_SECRET=<비밀>`(선택 `HEAX_SSO_ALLOWED_IPS=<포털 박스 IP>`) → RA 재기동 | RA 담당 |
| A3 | cae00 `infra/.env` | `RA_SSO_SECRET=<같은 비밀>` — `RA_HOST` 는 이미 있다(update-all 1e) | 포털 운영자 |
| A4 | cae00 | `./infra/scripts/update-all.sh` — 포털 재기동(비밀 전달) · 게이트웨이 재프로비저닝(`per_user_sso.reportarchive`, 부서 헤더 뺌) | 포털 운영자 |

확인: ① 사용자 관리 맨 위 '배선 설정' 의 'RA 사람별 위임' 이 사라진다. ② '개인 토큰 › 외부 연결' 의 RA 카드가 '포털 로그인으로 본인 명의 — 등록할 것 없음'.
③ Claude Code 에서 `reportarchive_list_reports(mine=true)` 가 **본인 공간**을 본다(예전 VOC: personal-5 로 가던 것). ④ 게이트웨이 감사(audit.jsonl)에
RA 호출이 `mode=as-user-pat` 로 남는다.

되돌리기: cae00 `infra/.env` 의 `RA_SSO_SECRET` 을 비우고 update-all — 종전 '토큰 등록' 방식으로 돌아간다(등록해 둔 토큰은 그대로 남아 있다).
update-all 출력에 '사람별 위임 끄기: reportarchive' 가 찍히고 게이트웨이 설정의 위임이 지워진다(D-17). `provision-config.sh` 를 손으로 돌리면
위임을 이어받으니 되돌리기는 update-all 로 한다.

## B. TestScope — 토큰 등록(구 RA 방식, D-15)

TestScope 는 다른 조직의 포털이라 그쪽 코드를 고치지 않는다. 사람마다 그쪽에서 개인 토큰을 발급해 포털에 등록한다.

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| B1 | TestScope 서버 MCP | 게이트웨이 박스(cae00)에서 :8022 에 닿게 — TestScope `.env` 의 `MCP_HOST`·`MCP_ALLOWED_HOSTS`(게이트웨이가 부르는 주소를 **포트까지 그대로**), 방화벽 | TestScope 운영 |
| B2 | cae00 `backend/.env` | `TESTSCOPE_BASE_URL=http://<TestScope 주소>:8020` — 포털이 등록된 토큰의 주인을 확인하는 주소. 비면 TestScope 카드가 안 뜬다 | 포털 운영자 |
| B3 | cae00 `backend/config/systems.local.yaml` | `testscope: {url: http://<TestScope 주소>:8020/}` — 앱 목록 타일(그쪽 주소로 새 탭). 비면 타일을 숨긴다 | 포털 운영자 |
| B4 | cae00 `~/Projects/HWAXMcpGateway/provision.env` | `TESTSCOPE_MCP_URL=http://<TestScope 주소>:8022/mcp` | 포털 운영자 |
| B5 | cae00 | `./infra/scripts/update-all.sh` | 포털 운영자 |
| B6 | 포털 사용자 관리 | TestScope 를 쓸 사람에게 TestScope 권한(CAEG 소속은 이미 전부) | 포털 관리자 |

사용자: TestScope 에서 내 정보 › 토큰 → 새 토큰(범위 **read** 필수, 쓰기 도구를 쓰려면 equipment:write·catalog:write) → 포털 '개인 토큰 › 외부 연결' 의
TestScope 카드에 붙여 넣기. TestScope 계정 이메일이 포털 계정 이메일과 같아야 한다(다르면 등록을 거절한다 — 남의 토큰 등록 방지).

확인: ① TestScope 카드에 '연결됨 — 끝자리 …'. ② Claude Code 에서 TestScope 도구(`list_conditions` 등)가 결과를 낸다. ③ 등록하지 않은 사람이 부르면
'TestScope 연결이 없습니다 … 외부 연결에서 등록' 으로 거부된다(공용 계정으로 대신 부르지 않는다).

### B-2. (선택) TestScope 도 ste 방식으로 — 사람이 토큰을 등록하는 수고를 없앨 때

TestScope 쪽이 [testscope-request.md](testscope-request.md) 의 `/api/auth/sso` 를 넣은 **뒤에만** — **10-20 확인: v0.62.0 에 들어왔다**
(`backend/app/modules/auth/gateway_token.py`, 위임 토큰은 읽기 전용 · 2일 · 이미 있는 계정만). TestScope 서버가 그 판으로 올라가 있는지는
그쪽 운영 담당에게 확인한다:

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| B2-1 | TestScope 서버 `backend\.env` | `HEAX_SSO_SECRET=<비밀>` → 재시작 | TestScope 운영 |
| B2-2 | cae00 `infra/.env` | `TESTSCOPE_SSO_SECRET=<같은 비밀>` — 위임 주소는 `backend/.env` 의 `TESTSCOPE_BASE_URL` 에서 유도된다 | 포털 운영자 |
| B2-3 | cae00 | `./infra/scripts/update-all.sh` | 포털 운영자 |

확인: TestScope 카드가 '포털 로그인으로 본인 명의 — 등록할 것 없음'. 되돌리기: `TESTSCOPE_SSO_SECRET` 을 비우고 update-all — 토큰 등록으로 돌아간다(출력에 '사람별 위임 끄기: testscope', D-17).
⚠ TestScope 가 `/api/auth/sso` 를 넣기 **전에** 비밀을 넣으면 TestScope 호출이 전부 거부된다(게이트웨이가 위임으로만 부른다).

## C. MatNexus · FMEA Agent — 토큰 등록, 박스 권한표의 `connect:` 한 블록(10-21, [docs/ext-connect](../ext-connect/PLAN.md))

**10-21 사용자 결정으로 바뀌었다.** 10-20 판(MatNexus 는 표준 위임 · FMEA 는 그쪽 답을 기다림)은 쓰지 않는다 — 둘 다 **토큰 등록**이다. 사람이
그쪽에서 받은 제 토큰을 포털 '개인 토큰 › 외부 연결'(`/tokens?tab=connect`) 카드에 등록하고, 게이트웨이는 그 토큰으로만 부른다. 새 플랫폼은
토큰 주인을 확인하지 않는다(필요한 플랫폼만 `owner_field` 로 켠다). 플랫폼이 늘어도 빌드 · 코드 · 재기동이 없다. 10-20 판은 git 이력에 있다.

⚠ `PER_USER_SSO_APPS` 에 `matnexus:MATNEXUS` · `fmea:FMEA` 와 `MATNEXUS_*` · `FMEA_*` 줄을 **넣지 않는다.** 같은 키의 정적 백엔드가 생기면
게이트웨이가 선언을 collision 으로 무시한다(`/health` 의 `conn_platforms` 에 `collision`). 이미 넣었으면 그 줄을 지우고 `gateway_config.json` 의
그 항목을 지운 뒤 게이트웨이를 다시 띄운다(provision 은 주소가 없는 실행에 직전 백엔드를 보존한다).

다음 플랫폼을 붙이는 절차(요청서 [1-7](../ext-connect/request.md)).

| # | 무엇 | 누가 |
|---|---|---|
| C1 | 그쪽 팀에서 넷을 받는다 — MCP 주소, 토큰 접두, 사람이 토큰을 발급하는 곳, 토큰 없이 initialize · tools/list 가 되는지. 코드는 받지 않는다 | 포털 운영자 |
| C2 | cae00 에서 프록시 없이 · 토큰 없이 미리 본다(아래 명령, 비밀은 보내지 않는다). 200 이면 `list_auth: open`, 401 이면 `registered:<포털 이메일>`. 연결이 끊기면 길부터 고친다 | 포털 운영자 |
| C3 | 그쪽 도구 이름이 지금 게이트웨이 도구와 겹치는지 본다 — 겹치면 선언 쪽 도구만 `<키>_` 접두가 붙는다(기존 앱의 맨 이름은 그대로) | 포털 운영자 |
| C4 | 박스 권한표(`~/Projects/HWAXPortal/backend/config/access.local.yaml`)의 `>>> hwax-batch` 블록 **밖**에 항목과 `connect:` 를 적고 저장한다(아래 예). 같은 id 는 추적 권한표의 항목을 통째로 바꾸므로 label · systems · gateway · hide_unless_routed 를 다시 적는다. 포털은 다음 요청부터 카드를 보인다 | 포털 운영자 |
| C5 | `update-collab.sh --check`(cae00 운영 스크립트 — 이 리포의 추적 파일이 아니다). 아무것도 바꾸지 않는다. ① 에 새 블록의 알림이 없고 ⑥ 이 초록이어야 한다 | 포털 운영자 |
| C6 | 게이트웨이에 바로 반영 — 아래 `/refresh`(토큰은 명령줄에 나타나지 않는다). 그냥 두면 최대 약 2분 안에 스스로 붙는다 | 포털 운영자 |
| C7 | `list_auth: registered:<이메일>` 이면 그 포털 계정으로 `/tokens?tab=connect` 에 들어가 목록용 토큰을 등록하고 C6 을 한 번 더 부른다(그 계정에도 `plat:<id>` 가 있어야 등록된다) | 목록 계정 주인 |
| C8 | 확인 — `/health` 의 `conn_platforms.<키>` 가 `ok` · `backends.<키>` 가 true · `/tools-map` 에 그 도구들 · 시험 사용자가 카드에 등록하고 읽기 도구 하나를 부르면 감사(`audit.jsonl`)에 `mode=as-conn` 과 `tok:` 지문 · 등록하지 않은 사용자에게는 `/tokens?tab=connect` 를 가리키는 거절 안내 | 포털 운영자 · 시험 사용자 |
| C9 | `/tools-map` 을 보고 같은 블록의 `read_tools` 에 읽기 도구의 **원래 이름**을 채운다(저장하면 바로 반영 — 읽기 전용 PAT · 응답 캐시가 이것을 본다). 쓰기 도구는 넣지 않는다 | 포털 운영자 |
| C10 | 권한 — 쓸 사람에게 `plat:<id>`(CAEG 소속은 이미 전부). 타일이 그 박스에 없으면 `hide_unless_routed: false` 로 두어야 권한 요청을 받는다 | 포털 관리자 |

할 일은 여기까지다 — 빌드 0, 코드 0, 재기동 0. `backend/.env` · `infra/.env` · `provision.env` · `gateway_config.json` 도 손대지 않는다.
되돌릴 때는 `connect:` 블록이나 그 항목을 지우고 C6 을 부른다(떼어 내기 전까지도 게이트웨이가 그 백엔드를 닫아 둔다). 남은 토큰은 사용자가 카드의
'더 이상 연결하지 않는 서비스' 줄에서 지운다. 타일은 cae00 에서 `systems.cae00.yaml`(`backend/.env` 의 `CATALOG_PATH`)이다 — `systems.local.yaml`
이 아니다(10-20 판의 C4 · D 가 틀렸다).

C2 · C6 명령(`<…>` 만 바꾼다).

```bash
curl --noproxy '*' -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"precheck","version":"0"}}}' \
  <MCP 주소>

python3 -c 'import json,os;print("header = \"Authorization: Bearer %s\"" % json.load(open(os.path.expanduser("~/Projects/HWAXMcpGateway/gateway_config.json")))["_gateway"]["token"])' \
  | curl -s --noproxy '*' -K - -X POST http://127.0.0.1:9110/refresh
```

C4 의 블록(두 플랫폼, 칸의 뜻과 검사는 요청서 [1-2](../ext-connect/request.md) 의 표).

```yaml
platforms:
  - id: fmea
    label: FMEA Agent
    desc: FMEA 분석 · 소재 기준선/규격 덮개
    systems: [fmea]
    gateway: [fmea]                  # 권한 행 — connect 의 백엔드 키가 여기 없으면 connect 를 버린다
    hide_unless_routed: true
    connect:
      mcp_url: http://<FMEA_호스트>:5190/mcp
      token_hint: "fmea_…"
      token_prefix: "fmea_"
      issue: "FMEA 웹 화면에 로그인한 뒤 토큰 메뉴(/tokens)에서 발급한 토큰을 붙여 넣습니다. 'Bearer ' 까지 붙여도 됩니다."
      issue_url: http://<FMEA_호스트>:5195/tokens
      verify: mcp                    # 등록할 때 그 토큰으로 보낸 initialize 가 200 이어야 저장한다(주인은 보지 않는다)
      list_auth: "registered:<목록용 포털 계정 이메일>"
      read_tools: []
      note: "쓰기 도구 2개(add_material_baseline_overlay_tool · add_spec_overlay_tool)는 이 토큰 주인 명의로 FMEA 에 덮개를 저장합니다."
  - id: matnexus
    label: MatNexus
    desc: 물성 관리 시스템(TestScope 와 같은 팀)
    systems: [matnexus]
    gateway: [matnexus]
    hide_unless_routed: false        # 타일이 아직 없다 — true 면 권한 요청까지 막힌다
    connect:
      mcp_url: http://<MatNexus_호스트>:8012/mcp
      token_hint: "mnx_pat_…"
      token_prefix: "mnx_pat_"
      issue: "MatNexus 의 내 계정 › 토큰에서 개인 토큰을 발급해 붙여 넣습니다."
      verify: none                   # initialize 는 토큰 없이 열려 있어 mcp 확인으로는 알 수 있는 것이 없다
      list_auth: open
      read_tools: []
      note: "읽기 전용 토큰이면 MatNexus 가 쓰기 도구를 거절합니다."
```

## D. FMEA Agent — 목록 계정

FMEA 의 `/mcp` 는 initialize 부터 토큰을 요구한다(10-21 실측). 그래서 게이트웨이가 사람 없이 도구 목록을 받으려면 목록용 토큰이 하나 든다 —
`list_auth: registered:<포털 이메일>` 이 가리키는 포털 계정이 FMEA 카드에 등록한 토큰을 **목록 세션에만** 싣는다(호출은 늘 부르는 사람의 토큰).
권하는 꼴은 FMEA `/signup` 으로 만든 **목록 전용 FMEA 로컬 계정**의 토큰을, 공용 관리자 로컬 계정 같은 포털 계정으로 로그인해 등록하는 것이다.
사람의 토큰을 쓰면 FMEA 로그에 그 사람이 60초마다 목록을 부른 것으로 남고, 그 사람이 토큰을 폐기하거나 떠나면 도구도 사라진다. 목록 계정이
아직 등록하지 않았으면 `conn_platforms.fmea` 가 `no-list-token`, 토큰이 만료 · 폐기되면 `down` 이다. FMEA 가 목록을 토큰 없이 열어 주면
`list_auth: open` 한 줄로 바꾼다 — 그쪽에 청할 것은 [fmea-request.md](fmea-request.md)(목록 공개 · readOnlyHint · 상시 운영).

## 함께 보는 곳

- update-all §6 출력 — 게이트웨이 '권한 표 구멍' 경고가 없는지(testscope 는 access.yaml 에 이미 있다).
- 사용자 관리 맨 위 배선 설정 상자.
- 게이트웨이 `/health` 의 backends 에 `testscope` · `matnexus` · `fmea`, `conn_platforms` 에 `matnexus` · `fmea` 가 `ok`.
