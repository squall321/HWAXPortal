# 사람별 위임(ste 방식) — 서버 쪽에서 사람이 할 일

> 대상: 포털 운영자(cae00) · RA 담당 · TestScope · MatNexus 운영 담당 · 2026-10-03(D · E 는 10-20)
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

## C. MatNexus — 표준 위임(10-20, D-18 · D-19)

MatNexus 는 TestScope 와 같은 팀의 다른 조직 서버다. 위임 창구(`/api/auth/sso`)가 이미 있어 **우리 쪽 코드 없이 설정만** 넣는다. 사람이 토큰을
등록하지 않는다 — 게이트웨이가 그 사람 이름의 읽기 전용 `mnx_pat_` 를 받아 부른다(2일짜리, 12시간 캐시). 순서는 **MatNexus 먼저**다 — 우리 쪽에
비밀이 생기는 순간 위임으로만 부르므로, 그쪽 창구가 꺼져 있으면 MatNexus 도구가 전부 거부된다.

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| C1 | MatNexus 서버 `backend\.env` | `HEAX_SSO_SECRET=<비밀>`(`openssl rand -hex 32`, 다른 서비스와 묶지 않는다) · (선택) `HEAX_SSO_ALLOWED_IPS=<그쪽에서 본 cae00 주소>` → 재시작 | MatNexus 운영 |
| C2 | MatNexus 서버 MCP | `MATNEXUS_MCP_ALLOWED_HOSTS=<MatNexus 주소>:8012`(게이트웨이가 부르는 주소를 **포트까지 그대로** — 다르면 421) · 방화벽 TCP 8012 인바운드 | MatNexus 운영 |
| C3 | cae00 `~/Projects/HWAXMcpGateway/provision.env` | 아래 네 줄 | 포털 운영자 |
| C4 | cae00 `backend/config/systems.local.yaml` | `matnexus: {url: http://<MatNexus 주소>:8010/}` — 앱 목록 타일(새 탭). 비면 숨긴다 | 포털 운영자 |
| C5 | cae00 운영자 셸 | `NO_PROXY` 에 MatNexus 주소(포트 없이 — 8010 · 8012 둘을 부른다). TestScope 와 같은 서버라 그쪽을 이미 넣었으면 끝 | 포털 운영자 |
| C6 | cae00 | `./infra/scripts/update-all.sh` | 포털 운영자 |
| C7 | MatNexus 화면 | 쓸 사람의 MatNexus 계정이 **승인돼 있고 이메일이 포털 계정과 같아야** 한다(없거나 승인 대기면 403 — 위임은 계정을 만들지 않는다) | 사용자 · MatNexus 관리자 |
| C8 | 포털 사용자 관리 | MatNexus 권한(`plat:matnexus` — CAEG 소속은 이미 전부) | 포털 관리자 |

C3 의 네 줄(`<…>` 만 바꾼다, 다른 일반 앱이 이미 있으면 `PER_USER_SSO_APPS` 에 쌍을 띄어 쓰기로 더한다):

```bash
PER_USER_SSO_APPS="matnexus:MATNEXUS"
MATNEXUS_MCP_URL=http://<MatNexus 주소>:8012/mcp
MATNEXUS_SSO_URL=http://<MatNexus 주소>:8010/api/auth/sso
MATNEXUS_SSO_SECRET=<C1 과 같은 비밀>
```

확인: ① update-all 출력에 `✓ matnexus — …(사람별 호출은 위임 토큰으로)` · 기대 목록 누락 없음 · §6 '프록시 우회' 초록. ② 비밀이 맞는지(그쪽 창구만 —
아무것도 만들지 않는다, 비밀이 명령줄에 남지 않게 파일로 넘긴다):
`curl -s -o /dev/null -w '%{http_code}\n' -X POST -H @<(printf 'X-Heax-Gateway-Secret: %s\n' "$MATNEXUS_SSO_SECRET") http://<MatNexus 주소>:8010/api/auth/sso/verify`
→ 204(401 은 비밀 불일치, 404 는 그쪽 창구 꺼짐). ③ Claude Code 에서 MatNexus 도구가 본인 자료를 낸다 · 게이트웨이 감사(audit.jsonl)에 `mode=as-user-pat`.
MatNexus 의 `내 계정 → 토큰` 에 'HWAX 포털 게이트웨이 (gateway)' 가 보인다.

쓰기: 위임 토큰은 읽기 전용이다(MatNexus 의 결정 — 포털로 들어오는 쓰기는 그쪽이 프롬프트를 못 보는 통로). 쓰기 도구는 미리보기(dry_run)까지만
돈다 — 실제로 쓰려면 MatNexus 에서 발급한 토큰으로 MatNexus MCP 에 직접 붙는다. 되돌리기: C3 의 비밀을 비우고 update-all(출력 '사람별 위임 끄기:
matnexus') — 백엔드는 남고 호출은 토큰 없이 나가 MatNexus 가 401 로 막는다. 백엔드까지 걷으려면 네 줄을 지우고 `gateway_config.json` 의 `matnexus`
를 지운 뒤 게이트웨이를 다시 띄운다(provision 은 주소가 없는 실행에 직전 백엔드를 보존한다).

## D. FMEA Agent — 그쪽 답을 받은 뒤(10-20, D-20)

dev 에서는 닿지 않고(사내망 안쪽) 소스도 찾지 못했다. [fmea-request.md](fmea-request.md) 를 FMEA Agent 담당에게 보내 답을 받는다. 그쪽이
**표준 위임 창구**를 넣으면 C 와 똑같다 — 키 `fmea`, 접두 `FMEA` 로 `PER_USER_SSO_APPS="matnexus:MATNEXUS fmea:FMEA"` 와 `FMEA_MCP_URL` ·
`FMEA_SSO_URL` · `FMEA_SSO_SECRET`(타일은 `systems.local.yaml` 의 `fmea: {url: …}`). 권한표 `plat:fmea`(게이트웨이 `fmea`)와 숨김 타일 `fmea` 는
10-20 에 미리 넣었다 — 표에 없는 백엔드는 전체 공개라서다. 타일 소개 문구는 이름에서 지었으니 답을 받으면 맞춘다. 개인 토큰 + 본인 확인만
있다면 TestScope 같은 '토큰 등록' 이 필요하고 그때는 포털 · 게이트웨이 코드가 든다.

## 함께 보는 곳

- update-all §6 출력 — 게이트웨이 '권한 표 구멍' 경고가 없는지(testscope 는 access.yaml 에 이미 있다).
- 사용자 관리 맨 위 배선 설정 상자.
- 게이트웨이 `/health` 의 backends 에 `testscope` · `matnexus`.
