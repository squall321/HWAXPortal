# 사람별 위임(ste 방식) — 서버 쪽에서 사람이 할 일

> 대상: 포털 운영자(cae00) · RA 담당 · TestScope 운영 담당 · 2026-10-03
> 코드는 리포에 들어가 있다. 아래는 **박스마다 다른 값과 비밀**이라 사람이 넣는다(비밀·사내 주소는 리포에 적지 않는다).
> 비밀은 `openssl rand -hex 32` 로 만들고, **서비스마다 따로** 둔다(RA 와 TestScope 를 같은 값으로 묶지 않는다).

## 원칙 — 비밀은 서비스 쪽이 준비된 뒤에 넣는다

포털·게이트웨이 쪽 비밀(`RA_SSO_SECRET`·`TESTSCOPE_SSO_SECRET`)이 생기는 순간 게이트웨이가 그 서비스를 **사람별 위임으로만** 부른다.
서비스가 아직 `/api/auth/sso` 를 모르면 그 서비스 도구 호출은 전부 거부된다(서비스 계정으로 대신 부르지 않는다). 그래서 이 둘은
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

## B. TestScope

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| B1 | TestScope 배포 | v0.50.0 이상(포털 위임·타일 SSO·접두 경로가 들어간 판) | TestScope 운영 |
| B2 | TestScope 서버 `backend\.env` | `HEAX_SSO_SECRET=<비밀>` · `PORTAL_JWKS_URL=http://<포털 박스>:8088/.well-known/jwks.json` — 새 키는 배포가 옛 .env 를 들고 오므로 **손으로** 넣는다 → 서비스 재시작 | TestScope 운영 |
| B3 | TestScope 서버 MCP | 게이트웨이 박스에서 :8022 에 닿게 — `.env` 의 `MCP_HOST`·`MCP_ALLOWED_HOSTS`(TestScope 배포.md 의 MCP 절) | TestScope 운영 |
| B4 | cae00 `backend/config/routes.local.env` | `testscope=http://<TestScope 서버>:8020/` — 타일(`/testscope/`)과 위임·MCP 주소가 여기서 유도된다(MCP 포트가 8022 가 아니면 `provision.env` 에 `TESTSCOPE_MCP_URL`) | 포털 운영자 |
| B5 | cae00 `infra/.env` | `TESTSCOPE_SSO_SECRET=<B2 와 같은 비밀>` | 포털 운영자 |
| B6 | cae00 | `./infra/scripts/update-all.sh` | 포털 운영자 |
| B7 | 포털 사용자 관리 | TestScope 를 쓸 사람에게 TestScope 권한(CAEG 소속은 이미 전부 있다) | 포털 관리자 |

확인: ① 앱 목록에 TestScope 타일이 뜨고, 누르면 본인 계정으로 들어간다(처음이면 계정이 생긴다 — 쓰기는 TestScope 에서 부서가 정해진 뒤).
② Claude Code 에서 TestScope 도구(`list_conditions` 등)가 결과를 낸다. ③ TestScope 토큰 목록에 'HWAX 게이트웨이(gateway)' 가 **하나만** 있다.

## C. 함께 보는 곳

- update-all §6 출력 — 게이트웨이 '권한 표 구멍' 경고가 없는지(testscope 는 access.yaml 에 이미 있다).
- 사용자 관리 맨 위 배선 설정 상자.
- 게이트웨이 `/health` 의 backends 에 `testscope`.
