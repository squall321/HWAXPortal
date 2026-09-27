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

## D-7. 2라운드 검토(커밋본 대상) — 확인 8·기각 0, 그중 둘이 "시험이 실제 경로를 안 탔다" (2026-09-27)

**① `unless_env: RA_HOST` 가 파일에서 읽히지 않았다(high).** `enabled_here` 는 `_hwax_setting` 으로 값을 읽고, 그 함수가 보는
`_infra_env()` 는 `HWAX_*` 키만 파싱한다(데이터 이관 설계 — docs/data-migration). `infra/.env` 에만 적은 `RA_HOST` 는 services.py
에 **절대** 도달하지 않았고, 오케스트레이터를 부르는 어느 경로(부팅 유닛 `hwax-stack.service`·`services.sh`·update-all 의 `$SVC up`)도
RA_HOST 를 env 로 넘기지 않는다 — 즉 3-1 보호가 실제로는 0 이었고 가이드의 확인 명령(`services.sh enabled report-archive` → 1)도
0 을 냈을 것이다. **내 시험이 못 잡은 이유**: `_infra_env` 를 `{}` 로 monkeypatch 하고 `setenv` 만 써서 파일 파서를 한 번도 타지
않았다. 고침: `_infra_value(key)` — 같은 파서 규칙(인라인 주석·따옴표·빈 값=미설정·마지막 줄)으로 임의 키를 읽고 `unless_env` 만 이걸
쓴다(HWAX_ 허용 목록은 그대로 — os.environ 에 넣지 않는다). 시험은 **실제 임시 infra/.env** 로, 그리고 `env -i` 로 services.py CLI 를
돌려 부팅 유닛과 같은 환경에서 rc 1 을 확인한다.

**② `_ra_envv` 가 인라인 주석을 값에 붙였다(high).** `tr -d` 로 공백을 지우니 `RA_HOST=x   # ⚠ …` 가 `x#⚠…` 이 되고, 가드(`*:*`·`*/*`)를
통과해 세 파일에 깨진 URL 이 ✓ 로 적혔다. 이 편집은 가정이 아니다 — 1c env-sync 가 정확히 `# RA_HOST=   # ⚠ 값을 운영자가 정해야
한다` 를 넣고, 운영자는 `# ` 만 지운다. 고침: bash 가 읽는 규칙대로(공백 뒤 `#` 이후 제거·양끝 공백·따옴표·CR), 가드는 허용 문자만
(`[A-Za-z0-9.-]`, IPv6 미지원을 문장으로 말함). doctor 의 `envv` 도 같았다.

**여기서 로케일 함정을 하나 더 봤다.** 고친 sed(`s/[[:space:]]+#.*$//`)가 Bash 툴에선 벗기고 파이썬 자식 셸에선 안 벗겼다 — 같은
`LANG=en_US.UTF-8`, 같은 GNU sed 4.8, 같은 입력. 짧은 한글은 되고 긴 한글("값을 운영자가 정해야 한다")은 안 됐다. `LC_ALL=C`
로는 결정적으로 된다 → 세 독자(`_ra_envv`·LLM 값·doctor `envv`) 모두 `LC_ALL=C sed`. 원인 규명은 안 했다(해도 결과가 안 바뀐다) —
**한글이 든 줄에 정규식을 걸 땐 바이트 단위로 고정한다** 를 규칙으로 남긴다.

**③~⑧(medium·low, 전부 고침).** 개행 없는 파일 끝에 `>>` 가 이어붙어 `RAT_TOKEN=…RA_MCP_URL=…` 한 줄이 되고 §5 가 그 토큰을 소싱
하던 것(끝에 개행이 없으면 먼저 개행) · `_upsert_kv` 의 python 실패가 무시되고 ✓ 가 찍히던 것(rc 를 보고 fail) · 원격 RA 가
게이트웨이에 못 붙어도 ⚠ 두 줄로 `✓ 전체 최신화 완료` 하던 것(ste MCP 와 같은 등급으로 **fail**) · 새로 만드는 `backend/.env`·
`provision.env` 가 0644 로 태어나던 것(600) · LLM 이관이 셋 중 하나만 옮기고도 ✓ 하던 것(옮긴 키·빠진 키를 말하고 ⚠) · §5 드리프트가
소문자 hostname 을 원문과 비교해 대문자 호스트명에 매번 재프로비저닝하던 것 · TLS 가드가 `../` 를 통과시키던 것 · `apply-envs -n` 이
API 키 실값을 찍던 것(가림) · 시험 둘이 이 박스의 `backend/.env`·환경변수에 매달려 있던 것(`Settings(_env_file=None)`·정합 기본값).

**세 라운드 합계** — 1라운드(작업본과 엇갈림)에서 뒤집힘 4 · 2라운드 확인 8. 이번엔 2라운드가 진짜를 잡았고 그 둘은 모두 "시험이
실제 경로를 흉내만 냈다" 였다. 시험이 통과했다는 사실이 아니라 **시험이 무엇을 탔는가**를 봐야 한다.
