# RA 재연결 — 결정 기록

## D-1. 질문이 바뀐다 (2026-09-27)
사용자 질문은 "RA 최신화했는데 HTTPS 준비됐나" 였다. 요청서를 읽으면 HTTPS 는 여덟 항목 중 하나다 — RA 가 박스를 떠났고,
포털이 "같은 박스" 전제를 여덟 곳에서 갖고 있다. HTTPS 만 답하면 나머지 일곱이 그대로 사고가 된다(구 RA 되살림·LLM 공백).

## D-2. 운영자 값은 RA_HOST 하나, 나머지는 유도
요청서는 세 파일에 주소를 각각 적으라 한다(routes.local.env·backend/.env·provision.env). 손으로 셋을 맞추면 하나가 빠지고
그 하나는 조용히 옛 주소를 본다 — ste 의 `STE_SSO_URL` 이 정확히 그렇게 죽어 있었다(docs/one-token D-12). 그래서 1e 가
`RA_HOST` 하나로 셋을 upsert 한다. B 로 넘길 때도 값 하나만 바꾼다(요청서 §5 의 세 단계가 한 단계가 된다).

## D-3. 박스 이름이 아니라 설정으로 가른다 — `unless_env`
services.yaml 에는 `only_on: <hostname>` 이 있다. RA 항목을 "cae00 이 아닐 때만" 으로 쓰면 박스 이름이 박힌다(cae00 호스트명이
바뀌거나 다른 운영 박스가 생기면 틀린다). `unless_env: RA_HOST` 는 "RA 가 원격인 박스" 를 그 사실 자체로 가른다. dev 는
RA_HOST 가 없어 종전대로 로컬 RA 를 다룬다 — 요청서 3-1 의 "삭제" 를 그대로 하면 dev 의 RA MCP 가 안 뜬다.

## D-4. LLM 정본을 포털로
env-kit 넷(agent-server·paper-ingest·ai-data-hub·signalforge·heax-hub)이 `@FROM_RA:LLM_*@` 로 RA `.env` 를 읽는다. 마커 이름은
그대로 두고(`test_no_tracked_secrets` 가 허용 목록으로 갖고 있다) **해석 순서**만 바꾼다 — `infra/.env` 의 같은 키가 있으면 그것,
없으면 RA `.env`(레거시). 1e 가 RA `.env` 가 아직 있을 때 한 번 복사한다. 이 순서면 cae00 에서 RA 설치본을 지워도, dev 에서
RA 가 mock 이어도 동작이 바뀌지 않는다.

## D-5. JWKS 주소는 사람이 준다, 후보는 기계가 찍는다
RA 서버가 포털 JWKS 를 받아 갈 주소(요청서 4-2)는 RA 서버에서 닿는 주소라 포털이 확정할 수 없다. 1e 가 두 후보(이 박스 LAN
http:8088 · 공개 https)와 로컬 프로브 결과를 찍고, 사내 CA 면 `/tls/ca.crt` 를 같이 주라고 말한다. https 를 고르면 RA 쪽에
CA 가 필요하고, http 사내망은 그게 없다 — 요청서 자신이 후자를 "더 간단" 이라 했다.
