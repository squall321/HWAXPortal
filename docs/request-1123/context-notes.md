# 결정과 까닭 — nginx 한도(cae00 11-23 요청)

## NX-1 받은 것(11-23)

- 사용자가 cae00 이 쓴 요청서(보내기 전 판)를 붙여 넣었다 — [request.md](request.md). 기준 판 포털 `794048c2`.
- 4차 라운드 동결 중이지만 올린다 — 바뀌는 값이 cae00 이 지금 손으로 넣는 값과 같고(600s · 65536 · `*-mcp` 1h), 허브 앱 열쇠 · Drive 묶음에 닿지 않는다
  (conf 는 git 의 생성기로 박스에서 만든다).

## NX-2 지은 꼴(11-23)

- **HP-79** — 템플릿 http 레벨에 읽기 · 쓰기 둘 다 한 손잡이(`NGINX_PROXY_READ_TIMEOUT`, 기본 600s). 값 검사는 있는 `_nginx_time`(숫자에 단위 하나 · 0 은
  받지 않음 — nginx 의 0 은 '즉시 끊는다'). TLS server 에 따로 박지 않는다 — http 레벨 하나라 두 server 가 같이 물려받는다.
- **HP-80** — `worker_rlimit_nofile`(기본 65536). 생성기를 돌리는 셸의 `ulimit -Hn` 보다 크면 hard 로 낮추고 ⚠ — nginx 는 넘는 값을 알림 한 줄로 넘기고 soft 를
  그대로 둬, conf 에 적힌 값이 먹은 줄 알게 된다(요청서 3절). 생성기와 nginx 는 같은 셸(start.sh · update-all)에서 뜬다.
- **HP-73** — 이름이 `-mcp` 로 끝나는 라우트에 `/mcp-gw/` 와 같은 묶음. 침묵 한도는 새 손잡이를 만들지 않고 `NGINX_MCP_READ_TIMEOUT`(1h)을 읽기 · 쓰기에
  같이 쓴다 — 요청서가 손으로 넣는 값(1h)과 같고, MCP 입구의 침묵 한도가 둘로 갈리지 않게. 이름이 정해진 갈래(ste · apps …)가 먼저다.
- **HP-81** — 손잡이에 적은 라우트에만 `proxy_buffer_size 64k` · `proxy_buffers 32 64k` · `proxy_busy_buffers_size 128k`(응답 하나에 최대 2MB). 값은
  고정 — 요청은 '키우는 선택' 이고 크기 손잡이까지 두면 틀린 조합(busy 가 버퍼 합을 넘음)으로 nginx 가 즉사할 길이 생긴다. 기본 끔.
- **`infra/.env` 는 셸이 읽는다**(`_common.sh` 의 `set -a; . infra/.env`) — 따옴표 없는 빈칸은 뒤 낱말을 명령으로 돌린다. 라우트 목록 예시는 쉼표로 적었다.
- 있는 시험 하나(`test_request_1027_nginx` HP-47)가 conf 전체에서 `limit_` 글자를 찾다가 `worker_rlimit_nofile` 에 걸렸다 — 뜻(limit_rate · limit_conn)대로 좁혔다.
- 시험 — `test_request_1123_nginx.py`(생성기를 임시 리포에서 실제로 돌림 · hard 한도를 낮춘 셸 · `nginx -t`), 변이 넷(http 한도 뺌 · hard 로 안 낮춤 · mcp 갈래 끔 ·
  버퍼 안 붙임) 모두 붉게 잡힘.

## NX-3 cae00 답(11-24)

- 11-23 23:23 에 생성된 conf 에 http 레벨 600s · `worker_rlimit_nofile 65536` · `*-mcp` 스트리밍 묶음을 손으로 넣고 `nginx -t` 뒤 reload 했다. 받은 편지함 덧붙임
  (Q28)은 그 글을 받은 뒤에 붙어 답이 없다 — 다음 update-all 이 이 판(`4cf8e6ff` 뒤)을 받으면 생성기가 같은 값을 만든다. 손으로 다시 넣으면 `duplicate` 로
  `nginx -t` 가 실패한다 — 다음 라운드 글에 Q28 을 다시 싣는다.
