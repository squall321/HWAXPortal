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

## D-6. 감사(5갈래 × 반박 검증) — 48 판정, 확인 2 · 뒤집힘 4 · 미검증 42 (2026-09-27)
감사가 도는 사이 내가 작업본을 고쳐서, "missing" 넷(3-1·3-2·3-3·3-6)이 반박 단계에서 **뒤집혔다** — 감사자는 커밋본을 읽었고
작업본에는 이미 돼 있었다. 확인된 둘: ① 부팅 유닛(`hwax-stack.service`)이 무인자 `services.py up` 을 돈다 — `unless_env` 가
`cmd_up` 의 `enabled_here` 를 통과하므로 RA_HOST 있는 박스에서는 구 RA 에 도달하지 않는다(검증자가 :353 을 확인). 별도 예외를
유닛에 박지 않는다 — "어디서 빼는가" 가 둘로 갈린다. ② `RA_BASE_URL` 은 `backend/.env` 만이 주입 경로다 — 1e 가 거기 적고,
§2 가 매 실행 포털을 `stop→start` 하므로 그때 읽힌다(추가 재기동 불필요, 1e 메시지에 적음).

**HTTPS 에 대해 감사가 낸 것(이번에 닫은 것).**
- `ENABLE_TLS` 기본값이 false 다 — TLS 서버 블록은 그때만 생성된다. 공개 주소가 https 인 박스는 `infra/.env` 에
  `ENABLE_TLS=true·TLS_CERT_PATH(fullchain)·PUBLIC_BASE_URL=https://…·COOKIE_SECURE=true` 넷이 같이 가야 한다. 이 넷의 정합을
  아무도 보지 않았다 → `ste-doctor` **4c `https` 행**(종단 200 · 스킴 · 쿠키), `startup_warnings` 에 **`cookie_scheme`**(https 인데
  secure=false 면 외부 IdP 의 cross-site POST 에 상태 쿠키가 안 실리고, http 인데 true 면 브라우저가 쿠키를 버려 로그인 루프).
- `start.sh` 는 인증서가 없으면 **자체서명을 자동 생성**한다 — `ENABLE_TLS=true` 로 켜는 순간 정식 인증서가 없어도 :443 이
  자체서명으로 뜬다. 그래서 `tls` 행(어떤 인증서인가)과 `https` 행(켜져서 응답하는가)은 다른 질문이고 둘 다 낸다.
- `TLS_CERT_PATH` 에 **절대경로**를 주면 nginx 가 즉사한다 — 생성기가 `/workspace/$TLS_CERT_PATH` 로 붙이고 컨테이너에는 리포만
  바인드된다(백엔드 `tlscert.py` 는 절대경로를 받아 둘의 계약이 달랐다). 생성기에 가드를 넣었다: 상대경로가 아니면 이유를 말하고 멈춘다.
- 4-2 JWKS: 기존 앱 넷은 같은 박스라 백엔드 :8723 을 직접 봤지만 RA 는 다른 박스다 — nginx 경유(:8088 또는 https)여야 한다.
  1e 가 그 둘을 찍는다. 감사도 요청서도 사내망 http 후보를 "더 간단" 으로 본다(RA 쪽 CA 불필요).
- HSTS·http2 는 넣지 않았다 — 자체서명·인증서 미확정 상태에서 HSTS 는 되돌리기 어렵다. 정식 인증서가 들어온 뒤의 일이다.

**뒤집힌 판정에서 배운 것.** 감사를 구현과 **같은 시간에** 돌리면 감사자는 커밋본과 작업본 중 무엇을 보는지 모른다. 이번엔
반박 검증이 그 차이를 잡아 줬지만, 다음엔 감사는 커밋 뒤에 돌린다.
