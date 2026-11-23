# 포털 nginx 기본 시간 한도와 열린 파일 한도를 생성 conf 에서 받기(HP-79 · HP-80 · HP-81, HP-73 다시)

> cae00 이 2026-11-23 에 쓴 요청서(보내기 전 판)를 사용자가 dev 포털 세션에 붙여 넣었다. 원문 그대로 옮긴다.

작성일은 2026-11-23 입니다. 아직 보내지 않았습니다.

운영 박스에서 데이터허브 화면 일부가 60 초를 넘기면 끊깁니다. 사용자는 '사람이 많을 때 한도에 걸려 안 된다'고 느꼈습니다. 그런데 기록에는 동시 처리 한도에 걸린 흔적이 없습니다. 끊긴 요청은 모두 nginx 기본 시간 한도(60 s)에 걸렸습니다.

운영 박스에서는 11-23 에 생성된 `hwax.conf` 에 같은 값을 손으로 넣었습니다(4절). 그런데 conf 를 다시 만들 때마다 지워집니다(`start.sh` · `update-all.sh` · `update-collab.sh` · `deploy-all-from-drive.sh`). 그래서 이 값을 생성 스크립트에서 받게 해 달라고 요청합니다.

- 기준 판은 포털 `794048c2` 입니다. `gen-nginx-conf.sh` 를 마지막으로 바꾼 커밋은 `cd02a655` 입니다.
- 줄 번호는 11-23 에 운영 박스에서 읽기만 해서 땄습니다.
- 주소 · 도메인 · 사람 이름은 뺐습니다.

## 한눈에 보기

| 번호 | 어디 | 지금 | 바라는 것 | 급함 |
|---|---|---|---|---|
| HP-79 | `infra/nginx/hwax.conf.tmpl` `http` 블록(`:11` 부터) | http · server 수준에 `proxy_read_timeout` · `proxy_send_timeout` 이 없습니다. 그래서 `loc_extras` 의 `case` 에 없는 경로는 모두 nginx 기본값 60 s 입니다 | http 수준에 기본값을 한 줄 넣습니다(손잡이 `NGINX_PROXY_READ_TIMEOUT`, 기본 `600s`). location 에서 따로 정한 경로는 지금 값을 그대로 씁니다 | 높음 |
| HP-80 | 같은 템플릿 `:5`(`worker_processes`) · `:9`(`events`) | worker 의 열린 파일 한도가 박스 기본값(soft 1024)을 따릅니다. `worker_connections 1024` 와 같은 수입니다 | `worker_rlimit_nofile 65536` 을 넣습니다(손잡이 `NGINX_WORKER_RLIMIT_NOFILE`) | 중간 |
| HP-73(다시) | `infra/scripts/gen-nginx-conf.sh` `loc_extras`(`:27` 부터) | `*-mcp` 경로에 스트리밍 묶음이 없습니다 | 11-13 요청(`REQUEST-20261113-PORTAL-MCP-PATHS.md`) 그대로입니다. HP-79 와 함께 넣어 주십시오 | 중간 |
| HP-81 | 같은 파일 `loc_extras` | 큰 JSON 을 돌려주는 데이터허브 경로는 응답이 기본 버퍼를 넘습니다. 넘친 응답은 `/tmp` 임시 파일에 쓰입니다 | 데이터허브 웹 경로에 `proxy_buffers` · `proxy_buffer_size` 를 키우는 선택을 둡니다 | 낮음 · 선택 |

HP-70(데이터허브 웹 세 경로의 기본 한도, `REQUEST-20261112-DATAHUB-MOVE.md`)과 뿌리가 같습니다. HP-79 가 들어가면 HP-70 의 시간 한도 부분은 닫아도 됩니다.

## 1. 기록에서 본 것(11-23, 운영 박스에서 읽기만)

nginx 오류 기록은 10-19 부터 남아 있습니다. 그 전 기간에서 동시 처리 한도에 걸린 흔적은 하나도 없습니다.

| 찾은 문구 | 건수 |
|---|---|
| `worker_connections are not enough` | 0 |
| `Too many open files` | 0 |
| `limiting requests` · `limiting connections` | 0 |

최근 7 일(11-16 ~ 11-23)에 `upstream timed out`(504)이 42 건 있었습니다. 셋 다 location 에 시간 한도가 없는 데이터허브 웹 경로입니다.

| 경로(앞 세 단) | 건수 |
|---|---|
| `/failuretrace/api/server…` | 15 |
| `/compcore/api/cad…` | 13 |
| `/caegroup/api/review…` | 9 |
| `/caegroup/api/datasources…` | 2 |
| `/failuretrace/api/review` · `/objects` · `/graph` | 각 1 |

- 502 가 몰린 시각은 업데이트 재기동 창과 겹칩니다. 한도 때문에 생긴 502 는 아닙니다.
- 지금 worker 는 16 개입니다. worker 의 열린 파일 한도는 soft 1024, hard 1048576 입니다. 아직 넘친 적은 없지만 여유가 없습니다. 프록시 연결은 손님 하나에 연결 둘(앞 · 뒤)을 쓰므로, worker 하나가 손님 500 명 남짓에서 막힙니다. hard 가 크므로 soft 를 올리는 데 따로 권한은 필요 없습니다.
- 같은 7 일에 '응답을 임시 파일에 썼다'는 기록이 `/failuretrace/` 88,195 건, `/rootdesign/` 13,436 건 있었습니다. 끊김은 아닙니다. 다만 그만큼 느려지고 `/` 파티션을 씁니다(HP-81).

## 2. HP-79 시간 한도가 없는 경로는 60 초에 끊긴다

**지금**

- 템플릿 `http` 블록에 `proxy_read_timeout` 이 없습니다. server 블록에도 없습니다.
- `loc_extras` 가 시간 한도를 주는 경로는 `ste` · `apps` · `heax-hub` · `report-archive` · `odb-hub` · `simflow` · `stcx-llm` · `aireadyportal` 뿐입니다.
- 그 밖의 경로는 nginx 기본값 60 s 입니다. 여기에는 `routes.env` · `routes.local.env` 에서 온 데이터허브 웹 경로 여섯, `*-mcp` 열 경로, `ai-data-hub` · `mx-white-paper` · `signalforge` · `devlab-checklist` · `knox-bridge` 가 들어갑니다.

**바라는 것** — 템플릿 `http` 블록의 `proxy_http_version 1.1;` 아래에 넣습니다.

```nginx
    proxy_read_timeout {{PROXY_READ_TIMEOUT}};   # NGINX_PROXY_READ_TIMEOUT, 기본 600s
    proxy_send_timeout {{PROXY_READ_TIMEOUT}};
```

- location 에서 정한 값이 앞섭니다. 그래서 지금 600 s · 3600 s 를 단 경로는 바뀌지 않습니다.
- 포털 본체 `location /` 도 600 s 가 됩니다.
- 템플릿이 `client_max_body_size` 를 http 수준에 두는 것과 같은 이유입니다. 경로마다 붙이면 새 경로가 생길 때마다 조용히 기본값으로 돌아갑니다.
- 치르는 값도 있습니다. 멈춘 뒤쪽 서비스가 연결을 60 s 대신 600 s 동안 붙잡습니다. 그래서 HP-80 과 함께 넣어야 합니다.

## 3. HP-80 worker 열린 파일 한도

```nginx
worker_processes auto;
worker_rlimit_nofile {{WORKER_RLIMIT_NOFILE}};   # NGINX_WORKER_RLIMIT_NOFILE, 기본 65536
```

- `worker_connections` 는 그대로 1024 여도 됩니다. worker 16 개 × 1024 이면 지금 쓰는 양보다 훨씬 큽니다. 막는 쪽은 열린 파일 수입니다.
- 값이 박스의 hard 한도보다 크면 nginx 가 기동할 때 알림을 남기고 soft 를 그대로 둡니다. 기본값은 hard 보다 작게 잡아 주십시오.

## 4. 운영 박스에서 한 것(11-23)

생성된 `hwax.conf` 에 아래를 손으로 넣었습니다. 순서는 백업 → 백업 확인 → 넣기 → `nginx -t` → reload 였습니다.

| 넣은 것 | 자리 |
|---|---|
| `proxy_read_timeout 600s;` · `proxy_send_timeout 600s;` | `http` 블록, `proxy_http_version 1.1;` 아래(HP-79) |
| `worker_rlimit_nofile 65536;` | `worker_processes auto;` 아래(HP-80) |
| `proxy_buffering off;` · `proxy_cache off;` · `gzip off;` · `proxy_read_timeout 1h;` · `proxy_send_timeout 1h;` | `*-mcp` 열 경로, 두 server 블록(HP-73) |

- 박스 스크립트로 넣었으므로 백업과 되돌리기도 그 스크립트로 합니다.
- conf 를 다시 만들 때마다 지워지므로 그때마다 다시 넣습니다. 이 요청이 들어가면 손으로 넣는 일을 멈춥니다.

## 5. 반영 뒤 확인

- `gen-nginx-conf.sh` 를 돌린 뒤 `grep -nE 'proxy_read_timeout|worker_rlimit_nofile' infra/nginx/hwax.conf` 로 http 수준 한 줄과 맨 위 한 줄이 생겼는지 봅니다.
- reload 뒤 worker 하나의 `/proc/<pid>/limits` 에서 `Max open files` 가 65536 인지 봅니다.
- 60 초를 넘는 데이터허브 요청 하나가 504 없이 끝나는지 봅니다. 1절의 `/failuretrace/api/server…` 가 그런 요청입니다.
- `/ste/` · `/apps/` · `/report-archive/` 의 값(3600 s · 600 s)이 그대로인지 봅니다.
