# LLM 서버 둘을 자원 보고 나눠 쓰기 — 계획

> 사용자 결정(2026-10-15): 두 서버(…136 · …137)에 **같은 모델**을 올리고, **자원 상황을 보고** 덜 바쁜 쪽으로 보낸다. 라우터는 **cae00** 에 둔다. 차례는 **리스크 심사 M3 를 올린 바로 뒤**다(LP-D1 · D5 · D6).
> 내부 IP·포트·키는 추적 파일에 적지 않는다 — 실제 주소는 `infra/.env` 에만.

## 1. 지금

HWAX 의 LLM 호출은 전부 서버 하나(…137 의 vLLM, GLM-5.2 · 1M 창)로 간다. 주소의 정본은 포털 `infra/.env` 의 `LLM_BASE_URL` 이고, 서비스마다 자기 `.env` 에 사본을 든다 — 에이전트 서버 `VLLM_BASE_URL` · AIDataHub `OPENAI_BASE_URL`(과 `LLM_BASE_URL`) · PaperIngest `GLM_BASE_URL` · SignalForge `OPENAI_BASE_URL` · HEAXHub `HEAX_APP_LLM_BASE_URL`(허브가 앱에 `LLM_BASE_URL` 로 넘긴다) · MXWhitePaper `LLM_BASE_URL`. 설정 킷(`infra/env-kits/apply-envs.sh`)은 '없는 키만 더한다' 라서 정본을 바꿔도 이미 적힌 사본은 바뀌지 않는다(LP-D4).

## 2. 모양

```
에이전트 서버 · AIDataHub · …  ──▶  LLM 라우터 127.0.0.1:9130/v1  ──▶  vLLM …136
                                         │ /metrics 를 2초마다          └▶ vLLM …137
```

사람이 적는 것은 `infra/.env` 의 한 줄이다 — `LLM_UPSTREAMS=<서버1 /v1 주소>,<서버2 /v1 주소>`. 그 줄이 있으면 update-all 이 라우터를 띄우고 사본들을 라우터로 바꾼다. 지우면 사본들이 `LLM_BASE_URL`(직접 주소)로 돌아가고 라우터가 내려간다. `RA_HOST`·`ARP_HOST` 와 같은 '한 줄 → 유도' 모양이다.

## 3. 라우터 계약(L-1)

**자리.** `infra/llm-router/llm_router.py` 한 파일(원시 ASGI + httpx). 포털 SIF 의 파이썬(3.13 · httpx 0.28 · uvicorn 0.49)으로 돈다 — 새 이미지가 없다. 띄우는 것은 `infra/scripts/llm-router.sh run`(앞에서 도는 `apptainer exec`, 리포를 `/workspace` 로 바인드, `127.0.0.1:${LLM_ROUTER_PORT:-9130}` 에만 듣는다), 내리는 것은 `llm-router.sh stop`(그 포트를 **LISTEN** 하는 프로세스만, 명령줄이 라우터인지 확인한 뒤 — 연결 중인 클라이언트를 죽이지 않는다).

**설정.** 리포 루트의 `infra/.env` 를 라우터가 직접 읽는다(파일 위치에서 유도, 키를 argv·환경으로 넘기지 않는다). 읽는 규칙은 update-all 의 `_envfile_value` 와 같다(마지막 활성 줄 · `export` 허용 · 공백 뒤 `#` 주석 · 따옴표 · CR 제거). 파일의 mtime 이 바뀌면 다음 지표 주기에 다시 읽는다 — 서버를 더하고 빼는 데 재기동이 없다.

| 키 | 기본 | 뜻 |
|---|---|---|
| `LLM_UPSTREAMS` | (없음 = 풀 꺼짐) | vLLM 의 `/v1` 주소들, 쉼표·공백으로 나눈다 |
| `LLM_API_KEY` | — | 라우터 자신의 `/v1/models` 대조에만 쓴다. 손님 요청의 `Authorization` 은 **그대로 넘긴다**(라우터가 키를 끼워 넣지 않는다 — 이 박스의 다른 계정이 키 없이 LLM 을 쓰게 되지 않게) |
| `LLM_ROUTER_PORT` | 9130 | 띄우는 스크립트가 쓴다 |
| `LLM_ROUTER_SCRAPE_S` | 2 | `/metrics` 읽는 주기 |
| `LLM_ROUTER_STICKY_SLACK` | 4 | 붙인 서버가 가장 한가한 서버보다 이만큼 이상 바쁘면 떨어뜨린다 |
| `LLM_ROUTER_PREFIX_CHARS` | 8000 | 붙임 열쇠로 해시하는 메시지 앞부분 글자 수 |
| `LLM_ROUTER_CONNECT_TIMEOUT_S` | 5 | 연결 한도(넘김 판정) |
| `LLM_ROUTER_COOLDOWN_S` | 15 | 연결이 안 된 서버를 빼 두는 시간 |

**고르기.** 서버마다 마지막 지표의 `vllm:num_requests_running + vllm:num_requests_waiting`(라벨 묶음 전부 합) 에 '그 뒤로 라우터가 더 보낸 수'(지금 도는 수 − 지표 읽을 때 도는 수, 0 아래는 0)를 더한 것이 부하다. 지표가 없는 서버(404·파싱 실패)는 라우터가 보낸 도는 수만으로 잰다. 같으면 KV 사용률(`vllm:kv_cache_usage_perc`, 옛 이름 `vllm:gpu_cache_usage_perc`)이 낮은 쪽, 그것도 같으면 목록 앞쪽.

**붙임.** 본문이 JSON 이고 `messages` 가 있으면 `role:내용`(목록 내용은 글 조각만)을 차례로 이은 앞 `PREFIX_CHARS` 자, `prompt` 면 그 앞부분을 해시한 것이 열쇠다. 열쇠마다 렌데부 해시로 선호 서버가 정해지고, 선호 서버 부하 − 최소 부하 < `STICKY_SLACK` 이면 선호 서버로, 아니면 가장 한가한 서버로 보낸다. 같은 전문가의 카드 묶음·같은 대화가 같은 서버의 접두 캐시를 다시 쓴다(LP-D2). 클라이언트는 고치지 않는다.

**넘김.** 연결 실패(연결 거절·연결 한도 초과 — 요청이 서버에 닿지 않은 것)만 그 서버를 `COOLDOWN_S` 동안 빼고 다음 서버로 다시 보낸다(요청마다 서버 하나에 한 번). 연결된 뒤의 일(HTTP 오류·생성 중 끊김)은 그대로 넘기고 다시 보내지 않는다(LP-D3). 빠진 서버는 지표가 다시 읽히면 돌아온다. 모두 빠졌으면 전부를 다시 시도해 본다(멀쩡해졌을 수 있다).

**흐름.** 위로는 늘 스트림으로 보내고 받은 바이트를 그대로 흘린다(SSE 든 한 덩어리 JSON 이든). 손님이 끊으면 — 머리를 받기 전이든 흐르는 중이든 — 1초 안에 위 연결을 닫아 vLLM 이 생성을 멈추게 한다(지금 클라이언트가 vLLM 에 직접 붙어 있을 때와 같다 — 버려진 생성이 GPU 를 잡지 않게). 시간 한도는 연결 한도 하나다. 읽기·쓰기는 한도가 없다 — 한도는 부르는 쪽의 것이고 그 끊김이 위로 전해진다(시간 한도 층에 새 층을 끼우지 않는다).

**모델 대조.** 기동 때와 60초마다 서버마다 `/v1/models` 를 읽어 모델 id 묶음과 `max_model_len` 을 견준다. 다르면 `/health` 의 `models.match=false` 와 경고 한 줄(바뀔 때만).

**엔드포인트.** `GET /health` — `{status: ok|degraded|down, upstreams_total, upstreams_up, inflight, models{match, ids, max_model_len}, config_mtime}`(down 이면 503). `GET /stats` — 서버마다 `{url, up, running, waiting, kv, scrape_age_s, inflight, sent, connect_fail, retried_away, sticky, overflow}`. 그 밖의 모든 경로는 고른 서버의 같은 경로로 넘긴다(`/v1/*` · `/tokenize` 등). 요청마다 로그를 남기지 않는다 — 기동·다시 읽기·서버 오르내림·모델 어긋남·연결 실패만. 키와 본문은 어디에도 찍지 않는다.

## 4. 배선(L-2 · L-3)

- **매니페스트.** `infra/services.yaml` 에 `llm-router`(dir `.` · tier 5 · `update: false`). 새 칸 둘 — `if_env: LLM_UPSTREAMS`(그 키가 비어 있지 않은 박스에서만 다룬다, `unless_env` 의 거울 · infra/.env 를 못 읽으면 '모름' 이라 닫는다)와 `fp_git: false`(지문에 포털 HEAD 를 넣지 않고 `fp:` 경로 `infra/llm-router` · `infra/scripts/llm-router.sh` 만 — 포털 커밋마다 라우터가 재기동돼 도는 LLM 호출이 끊기지 않게).
- **재기동 미룸.** `update-sites.sh` 가 `llm-router` 를 내리기 전에 `/health` 의 `inflight` 를 본다. 0 보다 크면 미루고 ○ 로 남긴다(에이전트 서버의 심의 미룸과 같은 규율). 강행은 `LLM_ROUTER_RESTART_FORCE=1`.
- **update-all 1i 'LLM 라우터'.** `LLM_UPSTREAMS` 가 있으면 ① 목록 모양 검사 ② `update-sites.sh llm-router`(지문이 같고 살아 있으면 생략) ③ `/health` 가 답하고 서버 하나 이상이 올라와 있을 때만 ④ 사본들을 라우터 주소로 바꾼다 — 사본의 지금 값이 '관리하는 값'(직접 주소 `LLM_BASE_URL` · 목록의 서버 주소 · 라우터 주소)일 때만, 바꾸기 전에 그 파일을 백업하고, 바꾼 파일 목록과 되돌리기 한 줄을 찍는다. 관리하는 값이 아닌 사본(사람이 일부러 적은 다른 주소)은 그대로 두고 ⚠. `LLM_UPSTREAMS` 가 없으면 라우터를 가리키는 사본만 직접 주소로 되돌리고 라우터를 내리며, 아무것도 없으면 ○(켜려면 그 한 줄).
- **새 키.** `apply-envs.sh` 의 `@FROM_RA:LLM_BASE_URL@` 은 풀이 켜져 있으면 라우터 주소로 푼다(1i 뒤 3.5 에서 더해진 키가 직접 주소로 남지 않게). 같은 규칙을 `infra/scripts/lib/llm-pool.sh` 한 곳에 둔다.
- **§6.** 라우터 한 줄 — 서버 올라옴 수 · 모델 같음 · 도는 요청.

## 5. 동시 수(L-4) — 지금은 자동으로 올리지 않는다(LP-D7)

라우터만으로 두 서버를 함께 쓴다 — 카드 대조 8 개가 4·4 로 나뉘고, 한쪽에 챗·심의가 몰리면 다른 쪽으로 간다. 처리량까지 두 배로 쓰려면 세 곳이 같이 움직여야 한다 — 에이전트 서버 `.env` 의 `CARD_REVIEW_CONCURRENCY` · 리스크 앱 `knobs.env` 의 `HWAXRISK_REVIEW_CONCURRENCY` · 포털 `backend/.env` 의 `CARD_REVIEW_MAX_STREAMS`(이상). 그래서 절차서에 세 줄과 판단법(`/stats` 의 waiting 이 0 근처면 올린다, 늘 0 보다 크면 내린다)을 싣고, 코드 기본값(8 · 8 · 12)과 시간 한도 사슬 시험은 그대로 둔다.

## 6. 걸음

| # | 무엇 |
|---|---|
| L-1 | 라우터 · 띄우는 스크립트 · 매니페스트 항목 · `services.py` 두 칸 · 시험(가짜 vLLM 둘 — 고르기 · 붙임 · 넘김 · 스트림 · 끊김 전파 · 한쪽 죽음 · 다시 읽기) |
| L-2·3 | `lib/llm-pool.sh` · update-all 1i · `update-sites` 미룸 · `apply-envs` · §6 · `infra/.env.example` · 시험 |
| L-4 | 절차서의 세 줄(자동 아님 — LP-D7) |
| L-5 | 반대 검토 · 변이 검사 |
| L-6 | 절차서(cae00) · 업데이트 이력 · push |
