# 자동 연결 — 서버 쪽에서 사람이 할 일

> 대상: 포털 운영자(cae00)·RA 담당·TestScope 담당 · 2026-10-03
> 코드는 리포에 들어가 있다. 아래는 **박스마다 다른 값**이라 사람이 넣는다(비밀·사내 주소는 리포에 적지 않는다).

## A. Report Archive — 자동 연결 켜기

| # | 어디 | 무엇 | 누가 |
|---|---|---|---|
| A1 | RA 서버(A/B) `backend/.env` | `PORTAL_JWKS_URL=http://<포털 박스>:8088/.well-known/jwks.json` — 비어 있으면 타일 SSO 도 자동 연결도 꺼진다 | RA 담당 |
| A2 | cae00 `infra/.env` | `RA_HOST=<RA 주소>` — 이미 있으면 그대로(update-all 1e 가 `RA_BASE_URL` 등을 유도) | 포털 운영자 |
| A3 | cae00 | `./infra/scripts/update-all.sh` — §6 의 'RA 담당에게 줄 숫자: portal-callback → NNN' 이 303/400/401 이면 A1 이 된 것 | 포털 운영자 |

끄고 싶으면 cae00 `backend/.env` 에 `CONN_AUTO_LINK=false`(직접 붙여 넣는 길은 남는다). 그 밖의 손잡이(기본값이면 안 건드려도 된다):
`CONN_PAT_DAYS=90` · `CONN_ROTATE_DAYS=14` · `CONN_LOOKUP_WAIT_S=6` · `CONN_KEY_PATH=secrets/jwt/conn.fernet`.

확인: 권한(plat:reportarchive)이 있는 계정으로 포털에 로그인 → '개인 토큰 › 외부 연결' 의 Report Archive 카드가 '자동 연결됨 · 만료 …'.
안 되면 카드에 이유가 뜬다 — 'RA 쪽 포털 연결이 꺼져 있다'(A1), '계정이 막혀 있다'(RA 에서 비활성·JIT 꺼짐), '닿지 않는다'(A2·방화벽).

⚠ 처음 만들어진 RA 계정은 조직(부서)이 비어 있다. 보고서를 조직 게시판에 쌓으려면 그 사람이 RA 타일로 한 번 들어가 부서를 고르거나,
카드의 '보고서를 저장할 조직' 에서 고른다(종전과 같다).

## B. TestScope — 켜기(TestScope 쪽 계약이 된 뒤)

TestScope 쪽 준비는 [testscope-requirements.md](testscope-requirements.md). 그 뒤 cae00 에서:

| # | 파일 | 무엇 |
|---|---|---|
| B1 | `backend/.env` | `TESTSCOPE_BASE_URL=http://<TestScope 주소>:8020` — 포털이 서버에서 부르는 API 주소. 비면 TestScope 카드·연결이 없다 |
| B2 | `backend/config/routes.local.env` | `testscope=http://<TestScope 주소>:8020/` — 타일 SSO 용 nginx 경로(`/testscope/`). 이 줄이 있어야 타일이 뜬다 |
| B3 | TestScope `.env` | `PORTAL_JWKS_URL=http://<포털 박스>:8088/.well-known/jwks.json` |
| B4 | `~/Projects/HWAXMcpGateway/gateway_config.json` | Claude·챗 도구가 필요하면 백엔드 `"testscope": {"url": "http://<TestScope>/mcp", "transport": "streamable_http", "headers": {"Authorization": "Bearer <서비스 토큰>"}}` 를 넣는다(provision --force 에서 보존된다) |
| B5 | 같은 파일 `portal` 블록 | `"conn_backends": {"testscope": "testscope"}` — 이것을 넣는 순간 TestScope 호출은 **본인 토큰 필수**(없으면 거부·연결 안내). 자동 연결(§A 와 같은 방식)이 TestScope 에서 되는 것을 확인한 뒤 넣는다 |
| B6 | cae00 | `./infra/scripts/update-all.sh`(포털 재기동·nginx 재생성·게이트웨이 재기동) |

권한: TestScope 를 쓸 사람에게 '사용자 관리' 에서 TestScope 권한을 준다(CAEG 소속은 이미 전부 있다).

## C. 확인 순서(한 번에)

1. update-all §6 출력 — RA 콜백 숫자, 게이트웨이 '권한 표 구멍' 경고가 없는지(testscope 백엔드를 넣었으면 access.yaml 에 이미 있다).
2. 포털 '사용자 관리' 맨 위 배선 설정 상자.
3. 본인 계정으로 '외부 연결' 카드 상태.
4. Claude Code 에서 RA 도구(`reportarchive_list_reports` 등)가 본인 공간을 보는지.
