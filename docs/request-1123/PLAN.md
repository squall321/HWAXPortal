# 포털 nginx — 기본 시간 한도 · 열린 파일 한도 · `*-mcp` 스트리밍 · 큰 응답 버퍼(cae00 11-23 요청)

> 요청서 [request.md](request.md)(HP-79 · HP-80 · HP-73 다시 · HP-81) · 할 일 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md).

운영 박스에서 데이터허브 화면이 60 초를 넘기면 끊겼다(7일 504 42건 — 모두 location 에 시간 한도가 없는 경로). 동시 처리 한도에 걸린 흔적은 0 이다.
cae00 은 생성된 `hwax.conf` 에 같은 값을 손으로 넣고 있는데, conf 를 다시 만들 때마다 지워진다. 생성기(`gen-nginx-conf.sh` · 템플릿)가 받게 한다.

## 짓는 것

| 번호 | 자리 | 무엇 | 손잡이(`infra/.env`) · 기본 |
|---|---|---|---|
| HP-79 | 템플릿 `http` — `proxy_http_version 1.1;` 아래 | `proxy_read_timeout` · `proxy_send_timeout` 기본값. location 이 정한 값이 앞선다 | `NGINX_PROXY_READ_TIMEOUT` · `600s` |
| HP-80 | 템플릿 맨 위 — `worker_processes auto;` 아래 | `worker_rlimit_nofile`. 생성기를 돌리는 셸의 hard 한도보다 크면 hard 로 낮추고 알린다 | `NGINX_WORKER_RLIMIT_NOFILE` · `65536` |
| HP-73 | `loc_extras` — 이름이 `-mcp` 로 끝나는 라우트 | `proxy_buffering off` · `proxy_cache off` · `gzip off` · `proxy_read_timeout` · `proxy_send_timeout` — HTTP · TLS 두 server 블록 다(라우트 블록은 둘이 같은 글) | `/mcp-gw/` 와 같은 `NGINX_MCP_READ_TIMEOUT` · `1h` |
| HP-81 | `loc_extras` — 손잡이에 적은 라우트만 | `proxy_buffer_size` · `proxy_buffers` · `proxy_busy_buffers_size` 를 키운다 | `NGINX_LARGE_BUFFER_ROUTES`(라우트 이름, 쉼표) · 기본 비움(끔) |

- 값 모양이 틀리면 버리고 기본값으로 만든다(지금 `_nginx_time` 과 같은 규칙 — 한 줄 오타로 정문이 `[emerg]` 로 내려가지 않게).
- HP-70(데이터허브 웹 세 경로의 시간 한도)은 HP-79 로 닫는다.

## 차례

1. 템플릿 · 생성기 · 시험(임시 리포에서 실제로 생성 — 있는 nginx 시험 꼴) · `nginx -t`(SIF 가 있으면).
2. 포털 전체 회귀 → main → dev 재생성 · reload 확인(`/proc/<worker>/limits`).
3. cae00 받은 편지함 2026-11-23 에 덧붙임 — 손으로 넣기를 멈추는 때 · 반영 뒤 확인(요청서 5절).
