# 사람별 위임(ste 방식) — 서버 쪽에서 사람이 할 일

> 대상: 포털 운영자(cae00) · RA 담당 · TestScope 운영 담당 · 2026-10-03
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

## C. 함께 보는 곳

- update-all §6 출력 — 게이트웨이 '권한 표 구멍' 경고가 없는지(testscope 는 access.yaml 에 이미 있다).
- 사용자 관리 맨 위 배선 설정 상자.
- 게이트웨이 `/health` 의 backends 에 `testscope`.
