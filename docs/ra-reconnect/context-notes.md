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

## D-8. 3라운드 — §5 재프로비저닝이 9월 22일부터 죽어 있었다 (2026-09-27)

2라운드 수정(6ccfa44)을 다시 봤다: 확인 6·기각 2. 가장 큰 것은 이 작업이 만든 게 아니다.

**§5 의 `provision-config.sh --force` 호출이 한 번도 실행되지 않았다(high, 607effb 2026-09-22 부터).** 대입어 사슬
`RAT_TOKEN=… ARP_BASE=… \` 사이에 넣은 **백틱 주석**(`` `# ste 위임 …` ``)을 bash 파서가 **명령어 자리**로 잡는다 — 대입어는
명령어 앞에서만 대입이라, 백틱이 빈 문자열로 사라지면 그 다음 단어 `STE_SSO_SECRET=…`(나는 어제 `RA_MCP_URL=…` 을 하나 더 얹었다)
가 명령 이름이 되어 `No such file or directory`(rc 127) 다. `set -e` 가 없으니 그대로 `$SVC down/up` 이 돌고, STILL 재검증은
`calc_missing`(health 의 **키 존재**)만 봐서 옛 config 그대로인데 **"✓ 재프로비저닝으로 백엔드 정합 완료"** 를 찍었다. 검토자가
최소 재현(`A=1 \`# 주석\` B=2 env` → `B=2: command not found`)과 §5 블록 원문 실행(스텁 provision 에 마커 0개)으로 증명했다.
그동안 게이트웨이 config 가 맞아 보인 것은 사람이 `provision-config.sh` 를 직접 돌린 회차 덕이다. **시험이 못 잡은 이유**:
셋 다 텍스트 검사였다(`STE_SSO_SECRET=` 가 문자열에 있는가) — 실행하지 않았다. 고침: 주석을 사슬 위로, 대입어를 붙여서, `if ( … )`
로 rc 를 보고 실패면 `fail`; STILL 에서 RA 호스트 드리프트도 다시 재고 provision 실패면 ✓ 를 찍지 않는다. 시험은 **스텁
provision-config.sh 를 실제로 부르는 실행형** + "사슬 안에 백틱으로 시작하는 줄 없음" 정적 가드.

**두 독자가 어긋났다(회귀).** `export RA_HOST=x` 는 `_common.sh` 가 `set -a` 로 소싱하니 적법한 줄인데, services.py(`_infra_value`,
`export` 허용·shlex)는 읽고 update-all(`_ra_envv`, sed)은 못 읽었다 — services.py 는 로컬 RA 를 끄고 1e 는 "미설정" 으로 세 파일을
안 적어 **RA 가 그 박스에서 통째로 죽는** 방향. shlex 는 또 `x#y` 의 `#` 도 자르고 `don't` 는 예외로 줄을 버려 sed 와 세 모양에서
갈렸다. 고침: **한 규칙**(export 허용·공백 뒤 `#`·양끝 공백·따옴표 문자·CR 제거·마지막 줄·빈 값=미설정)을 `_infra_value`(정규식,
shlex 제거)·`_ra_envv`·doctor `envv`·apply-envs `ra_env_value` 넷에 글자 단위로 같게 넣고, 일곱 가지 까다로운 줄로 두 독자의
값이 같은지 **직접 비교하는 시험**을 뒀다.

**나머지.** RA_HOST 가드가 문자 집합만 봐 `-x`·`.`·`ra.` 를 통과시키고(nginx `[emerg] host not found` — 생성기는 `-t` 실패를
경고만 하고 진행) `localhost`/127.x 도 통과시켰다(로컬 RA 를 끄면서 자기 자신을 가리킴) → 모양 정규식 + 루프백 거부. LLM 이관
루프가 "RA .env 에 없다"(키 없는 LLM 이면 정상)와 "infra/.env 에 못 썼다"(고장)를 한 칸에 넣고 ⚠ 로 냈다 → 갈라서 후자는
`fail`. skip 문구가 `only_on=None` 만 찍어 cae00 에서 처음 나올 그 줄이 사유를 말하지 못했다 → `unless_env=RA_HOST(설정됨 …)`.
`_infra_value` 가 파일을 못 읽으면 예외로 죽던 것 → **닫는 쪽**(대상 아님)으로 두고 stderr 에 말한다(모름은 대상이 아니다).
시험이 `backend/.venv/bin/python` 절대경로에 매달린 것 → `sys.executable`.

**기각 둘.** "원격 RA 도달성을 아무도 안 본다" — §5 의 RA 호스트 드리프트 분기가 본다. "doctor `envv` 의 tail -1 이 transport.env
에서 다른 도구와 다른 줄을 고른다" — transport.sh 도 `set -a` 소싱(마지막 줄)이라 같다.

**교훈 둘.** ① 셸에서 **주석은 명령 위에만**, 대입어 사슬·파이프 안에 백틱 주석을 두지 않는다(이 리포에 두 번 들어갔고 둘 다 같은
줄을 죽였다). ② "그 명령이 실행됐는가" 를 텍스트로 확인하는 시험은 확인이 아니다 — 스텁을 두고 **실행**해 마커를 본다.

## D-9. cae00 첫 실측이 드러낸 것 (2026-09-27, 사용자가 update-all 꼬리·ste-doctor 를 붙여 줌)

**ste 빨강 넷은 뿌리가 하나 — 헤드에 옛 코드.** `deployed` "마커 없음", 자격중계 "옛 판(미들웨어 401)", `mcp` 15812 → 000,
`gateway-ste` absent. 즉 2c 가 이번 실행에서 배포하지 않았는데 **끝 요약(○)에 사유가 없었다** — `--if-stale` 의 초기 탈출 둘("리포
없음"·"접속 설정 없음")이 `exit 0` 만 하고 장부에 안 적었다 → 이제 `exit 3` + 장부. 그리고 update-all 의 1d 는 STE 리포를 형제
(`../SmartTwinExplorer`)에서만 찾는데 cae00 은 **`~/SmartTwinExplorer`** 다(doctor·deploy-ste 는 거기서 찾았다) → `_ste_repo_dir()`
로 셋을 같은 규칙으로. 실제로 2c 가 왜 멈췄는지는 그 구간 로그가 없어 아직 모른다 — 사용자에게 `deploy-ste.sh` 직접 실행 로그를 부탁.

**doctor 의 `sso-secret 다르다` 는 오진이었다.** 옛 판의 인증 미들웨어가 낸 401 을 "시크릿 다름" 으로 읽고 `FORCE_SSO_SECRET` 을 처방했다 —
update-all §6 은 `WWW-Authenticate` 헤더로 가르는데 doctor 는 안 갈랐다. 같은 프로브를 넣어 "옛 판 — 코드 갱신부터" 로 낸다.

**`teleport` 행이 형식을 못 읽었다.** 터널은 살아 있는데(web 200) 잔여 TTL 을 못 본 채 "모름". `tsh status -f json` 을 먼저 시도하고
그래도 못 읽으면 **원문 첫 줄들**을 보여 다음 판에 형식을 맞춘다.

**RA 쪽은 돌았다(사용자 몫이 이미 되어 있었다).** ○ 요약에 "RA 원격 재연결" 이 없으니 `RA_HOST` 가 있었고 1e 가 돌았다. 그런데 요약이
`LLM_BASE_URL·LLM_MODEL·LLM_API_KEY` 를 "값 미정" 으로 냈다 — 1c(env-sync)가 적은 것을 1e 가 뒤에서 채워도 장부에 그대로 남는다 →
`hwax_skip_forget` 로 1e 가 채운 키는 지운다. RA MCP 도구는 게이트웨이가 `RAT_TOKEN` 이 있을 때만 기대한다 — RA_HOST 는 있는데 토큰이
없으면 챗에서 RA 가 조용히 빠지므로 장부에 남긴다. 사용자 run 은 §5 재프로비저닝 부활(0469734) **전**이라 게이트웨이 config 갱신은 다음
실행부터다.

**https 는 켜져 있었다.** `:443 200`, 인증서는 **자체서명**(`tls` 행) — 남은 것은 `COOKIE_SECURE=true` 한 줄. 사용자 PC 의 Claude 는
배치파일이 `/tls/ca.crt` 를 심는다. RA 담당에게 줄 JWKS 는 사내망 http :8088 후보가 맞다(RA 쪽 CA 불필요).

## D-10. 2c 가 멈춘 자리 — refresh-code §3 체크아웃 (2026-09-27, 사용자가 deploy-ste.sh 직접 실행 로그를 붙여 줌)

`install-ste-tunnel.sh --check`: 15810 → 200, **15812 → 000** — 터널은 둘 다 열려 있으니 헤드에 MCP 가 없는 것(옛 코드엔 `ste-mcp.service`
가 없다. 그 유닛은 `deploy-backend.sh` 가 만든다). `deploy-ste.sh`: Drive 수신 33M ✓ · sha256 전부 ✓ · **§3 코드 커밋 고정에서
"커밋 체크아웃 실패: 41709e6…"** — 번들 fetch 는 됐고(`HEAD -> FETCH_HEAD`) 체크아웃이 막혔다. 종전 §3 은 checkout 의 stderr 를
`/dev/null` 로 보내 **git 이 왜 막았는지 아무도 못 봤다**. 유력한 원인은 배포용 사본(`~/SmartTwinExplorer`)의 더러운 작업트리
(추적 파일의 로컬 수정, 또는 반입 커밋이 만드는 파일이 미추적으로 이미 있음) — 그러나 이건 추정이고, 고친 스크립트가 다음 실행에서
git 의 문장을 보여 준다.

고침(SmartTwinExplorer 6b7205e): §3 이 작업트리가 더러우면 목록을 찍고 `stash -u`(복구 가능)로 치운 뒤 `checkout --detach`,
실패하면 git 의 마지막 문장을 붙여 die. 실제 git 저장소·번들로 두 경로를 시험(더러운 트리 통과 · 없는 커밋의 사유 표시). Drive
staging 을 다시 발행해 cae00 의 다음 pull 이 이 판을 받게 했다. **닭과 달걀**: 고친 §3 은 새 판 안에 있는데 그것을 반입하는 것이
옛 §3 이다 — 그래서 cae00 에서 한 번은 사람이 `stash` 를 손으로 하고 `deploy-ste.sh` 를 다시 돌린다(가이드에 적음). 그 뒤부터는 자동.

## D-11. 4라운드 — 3라운드 수정(0469734) 자체를 검토: 확인 6(고유 3)·기각 0·미검증 14 중 저비용 10 반영 (2026-09-27)

**확인 ①(high, 회귀) 값 없이 주석만 있는 줄.** `RA_HOST=   # ⚠ 값을 운영자가 정해야 한다(…)` — env-sync 가 넣는 `# RA_HOST=   # ⚠ …` 의
`# ` 만 지운 모양(D-7 이 "자연스러운 편집" 이라 부른 그 편집의 값-미기입 변형)이라 실제로 생긴다. bash 는 빈 값인데 **네 독자가 모두**
주석 문구를 값으로 읽었다 — `=` 뒤 공백(`[[:space:]]*`·`[ \t]*`)을 먼저 먹어 `#` 앞 공백이 사라지고, 그 뒤의 `\s+#.*$` 가 안 걸린다.
services.py 는 shlex 시절(6ccfa44) `None` 을 돌렸으니 3라운드가 만든 회귀. 결과: services.py 는 '원격 RA' 로 로컬 RA 를 끄고, 1e 는 주석문을
호스트라며 FAIL, 같은 모양이 `RA_PORT` 에 오면 `report-archive=http://h:# ⚠ …/` 가 라우트에 ✓ 로 적혔다. **3라운드의 일치 시험이 이걸 통과시킨
이유** — `py == sh` 만 단언해 둘이 같은 방향으로 틀리면 초록이다. 고침: 주석을 벗긴 **뒤에** 공백을 지운다(`=//p` → `s/[[:space:]]+#.*$//` →
trim). update-all 의 독자를 `_envfile_value <파일> <키>` 하나로 모아 `_ra_envv`·RA .env 사전검사·이관 루프·RAT_TOKEN 이 같은 함수를 쓰고,
doctor `envv`·apply-envs `ra_env_value`(RA .env 폴백도 같은 규칙 — 종전엔 `grep|head -1|cut` 로 첫 줄·따옴표 그대로였다, U7/U12)도 같게.
파이썬은 `\s`·`strip()` 대신 **ASCII 공백만**(U9: NBSP·U+3000 을 `\s` 는 먹고 C-로케일 sed 는 안 먹어 두 독자가 갈린다). 시험은 값-없음+주석
세 줄과 NBSP 를 더하고, **bash 를 오라클로**(`set -a; . file; printf %s "$RA_HOST"`) 댄다 — bash 가 못 읽는 줄(`don't`)만 제외.

**확인 ②(medium) §5 실패 문구의 `(rc $?)` 는 늘 0.** `else _prov_ok=0; fail "…(rc $?)"` — 대입 뒤의 `$?` 는 0 이다. D-8 이 살리려던 rc 127 같은
진단값이 정확히 이 줄에서 사라졌다. `_rc=$?` 를 else 의 **첫 명령**으로. 같은 자리(U5): provision 이 실패했는데도 게이트웨이·에이전트서버를 옛
config 로 튕기고 STILL 분기가 같은 원인에 fail 을 한 줄 더 쌓았다 → `_prov_ok=1` 일 때만 재기동, 실패면 재검증은 참고 문구만. 시험은
provision-config.sh 스텁을 rc 127/3/0 으로 **실행**해 문구의 rc 와 SVC 호출 기록을 본다(3라운드 시험은 텍스트 포함 검사였다).

**확인 ③(medium) 못 읽음을 '설정됨' 으로.** `skip_reason` 이 `_unless_env_allows` 를 다시 불러 InfraEnvUnreadable 을 또 잡고(경고 2회) 그 False 를
`(설정됨 — 다른 서버에서 돈다)` 로 찍었다 — `2>/dev/null` 로 부르는 자리(§5·deploy-all)에서는 거짓 문구만 남는다. `_unless_env_state(svc, warn)` 가
(허용, 사유) 를 돌리고 사유가 '읽을 수 없음' 과 '설정됨' 을 가른다. `_infra_env()` 의 PermissionError 트레이스백은 그대로 둔다 — 소리 나는 실패다.

**미검증 14 중 반영.** 루프백 가드 소문자 비교·별칭(`LOCALHOST`·`localhost.localdomain`·`0.0.0.0`·`ip6-localhost`, U2/U8/U11) · `_ra_shape` 문구에
하이픈 규칙(U3) · `_upsert_kv` 가 `export KEY=` 줄을 활성 줄로 보고 접두어를 지킨다(U4 — 독자만 넓혀 생긴 불일치: 쓰기는 앞의 비-export 줄을
고치고 bash 는 export 줄의 옛 값을 봤다) · LLM 이관 `_failed`∧`_absent` 동시·`_moved` 빈 문구(U6) · chmod 시험 `NOT_ROOT`(U10) · **거부한
RA_HOST 는 비운다**(U13 — 남겨 두면 §5·§6 이 믿어 원인 하나에 ✗ 셋) · 가이드·PLAN 의 ○ 문구를 실제 제목 "Report Archive 원격 재연결" 로(U14).

**반영 안 함(기록만).** `_ra_shape` 의 라벨 길이 63·숫자만인 이름(관찰 — nginx 가 잡는다) · `install-ste-tunnel.sh`·`deploy-ste.sh` 의
transport.env 독자는 아직 `=[[:space:]]*//p`(다른 파일·다른 규칙, 같은 모양의 함정은 있다 — ste 쪽 작업에서).

**변이 검사(감사 규율 ②).** 일곱 수정을 하나씩 되돌리자 새 시험이 각각 실패했다 — 독자 공백 순서(2 failed)·rc 순서(2)·실패 후 재기동(2)·
거부값 잔존(1)·upsert export(1)·services 공백 순서(1)·못읽음 문구(1). 스위트 758.

