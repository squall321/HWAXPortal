# LLM 서버 둘 — cae00 절차

> 이 문서는 …136 · …137 두 vLLM 서버를 cae00 의 LLM 라우터로 나눠 쓰게 하는 사람 몫을 적는다. 설계는 `PLAN.md`, 까닭은 `context-notes.md`(LP-D1~D14).
> 명령은 포털 리포 루트(cae00 은 `~/Projects/HWAXPortal`)에서 돈다. 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.
> 실제 주소·키는 `infra/.env` 에만 적는다 — 이 문서와 추적 파일에는 적지 않는다.

## 0. 이 판을 받기만 하면 — 아무것도 바뀌지 않는다

`LLM_UPSTREAMS` 를 적지 않은 박스에서 update-all 은 1i 에서 ○ 한 줄(`LLM 서버 풀(라우터)` — `infra/.env 에 LLM_UPSTREAMS 가 없다`)만 남긴다. 라우터는 뜨지 않고 LLM 주소 사본도 그대로다. 이 판을 받는 **첫** update-all 만 1c(env-sync)가 `infra/.env` 끝에 주석 두 줄(`# LLM_UPSTREAMS=   # 선택 — …` · `# LLM_ROUTER_PORT=8730   # 선택 — …`)을 붙이고 '선택 설정' ○ 를 남긴다 — 값을 정하라는 뜻이 아니다(비워 두면 꺼짐). 켜는 것은 아래 1~3절이다.

## 1. 먼저 — 두 서버가 같은지 본다

…136 의 vLLM 이 …137 과 **같은 모델 · 같은 창 · 같은 인자**로 떠 있어야 한다(LP-D6). cae00 에서 두 서버에 닿는지와 모델이 같은지 본다(키는 화면에 찍히지 않는다).

```bash
( set -a; . ./infra/.env; set +a
  for u in "http://<서버1>:<포트>/v1" "http://<서버2>:<포트>/v1"; do
    echo "== ${u%%/v1}"
    curl -s --noproxy '*' -m 5 ${LLM_API_KEY:+-H "Authorization: Bearer $LLM_API_KEY"} "$u/models" \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); print([(m.get("id"), m.get("max_model_len")) for m in d.get("data", [])])'
    curl -s --noproxy '*' -m 5 "${u%/v1}/metrics" | grep -c '^vllm:num_requests_running'
  done )
```

기대 — 두 서버의 `(모델 id, max_model_len)` 이 같고, 아래 숫자가 둘 다 1 이상이다(지표가 켜져 있다). 모델이나 창이 다르면 라우터는 창이 큰 서버로만 보내고 update-all 은 사본을 바꾸지 않는다.

## 2. 켜기 — `infra/.env` 한 줄

```
LLM_UPSTREAMS=http://<서버1>:<포트>/v1,http://<서버2>:<포트>/v1
```

- 쉼표로 나누고 공백을 넣지 않는다(공백이 필요하면 값 전체를 큰따옴표 한 쌍으로 감싼다 — start.sh 가 이 파일을 bash 로 읽는다).
- 주소마다 소문자 `http`/`https` 로 시작하고 정확히 `/v1` 로 끝난다. 계정(`user@`) · 질의(`?`) · IPv6 · 같은 서버 두 번 · 라우터 자신의 포트는 받지 않는다. 칸 하나는 2,048자까지다. 틀린 칸이 하나라도 있으면 update-all 은 아무것도 바꾸지 않고 ✗ 로 까닭을 말한다.
- `LLM_BASE_URL` 은 그대로 둔다 — 풀을 끄면 사본이 돌아갈 직접 주소다.
- 라우터 포트는 기본 8730 이다(`LLM_ROUTER_PORT` 로 바꾼다 — 풀을 켠 채 바꾸면 옛 포트 라우터는 저절로 안 내린다, 6절).

## 3. update-all

```bash
./infra/scripts/update-all.sh
```

기대 출력.

| 자리 | 문구 |
|---|---|
| 1i 머리 | `1i) LLM 라우터 (LLM_UPSTREAMS → 라우터 · 사본을 라우터 주소로)` |
| 라우터 | `✓ 라우터가 답한다 — 서버 2/2 올라옴 · 모델 같음 · 도는 요청 0` |
| 사본마다 | `✓ <리포>/<파일>  <키>: <옛 주소> → http://127.0.0.1:8730/v1  (백업 …/infra/.state/llm-pool-backups/<리포>/…)` |
| 사본 셈 | `· 사본 — 바꿈 N · 이미 그 주소 N · 관리 밖 N · 키 없음 N` |
| 다시 읽는 자리 | `· agent-server — §4 update-sites 가 …` 처럼 서비스마다 한 줄. PaperIngest 는 ⚠(이번 실행이 다시 읽게 하지 않는다 — 허브 앱은 HEAXHub 의 주소를 받는다) |
| §6 | `✓ LLM 라우터      서버 2/2 올라옴 · 모델 같음 · 도는 요청 N` |

✗ 가 나오면 사본은 바뀌지 않았다(서비스는 직접 주소로 그대로 돈다). 흔한 까닭 — `모델 대조 전`(라우터가 서버의 모델 목록을 아직 못 받았다 — 서버 키·주소를 본다) · `모델 다름`(1절) · `/health 가 답하지 않는다`(라우터 로그 `/tmp/hwax-services/llm-router.log`).

도는 심의가 있으면 에이전트 서버 재기동이 미뤄진다(○ `agent-server 재기동 건너뜀`) — 그 서버는 다음 update-all 까지 직접 주소로 돈다. 라우터를 지나는 요청이 있으면 라우터 재기동도 미뤄진다(○ `llm-router 재기동 미룸`, 강행은 `LLM_ROUTER_RESTART_FORCE=1` — 그 스트림이 끊긴다).

## 4. 확인

```bash
curl -s --noproxy '*' http://127.0.0.1:8730/health | python3 -m json.tool
curl -s --noproxy '*' http://127.0.0.1:8730/stats  | python3 -m json.tool
```

- `/health` — `status` 가 `ok`, `upstreams_up` 이 2, `models.match` 가 `true`. `kept_last_list: true` 면 infra/.env 의 목록이 비었거나 틀려 마지막 목록으로 내고 있다.
- `/stats` — 서버마다 `up` · `running` · `waiting` · `kv` · `sent`. 챗이나 심의를 한 번 돌린 뒤 두 서버의 `sent` 가 는다. 같은 대화 · 같은 전문가의 카드 묶음은 같은 서버로 붙는다(접두 캐시) — 한쪽으로 몰려 보여도 붙인 서버가 상대보다 2 이상 바쁘면 떨어진다.

## 5. 처리량까지 두 배로(선택 — LP-D7)

라우터만으로 두 서버를 함께 쓴다. 카드 대조를 두 배로 돌리려면 세 곳을 **함께** 올린다(하나만 올리면 사슬이 어긋난다 — 워커가 관문보다 많으면 거절과 재시도, 중계가 관문보다 적으면 중계에서 기다린다).

아래 16 · 16 · 24 는 '두 배' 의 예다. 이 박스의 값은 `capacity.md`(용량 측정 — 심의 없는 때 cae00 에서 30~60분)가 표와 함께 권한다 — 그 값을 이 자리에 쓴다.

| 곳 | 줄 | 다시 띄우기 |
|---|---|---|
| `../HWAXAgentServer/.env` | `CARD_REVIEW_CONCURRENCY=16` | 도는 심의가 없을 때 `cd ../HWAXAgentServer && ./start.sh -d` |
| 리스크 앱 `knobs.env`(경로는 `../risk-review-redesign/server-setup-m3.md` 2절의 `$D`) | `HWAXRISK_REVIEW_CONCURRENCY=16` | 도는 검토 잡이 없을 때 리스크 앱 재기동 |
| `backend/.env` | `CARD_REVIEW_MAX_STREAMS=24` | `apptainer instance stop hwax_portal && ./infra/scripts/start.sh` |

판단 — 카드 대조가 도는 동안 `/stats` 의 두 서버 `waiting` 이 0 근처면 그대로 둔다. 늘 0 보다 크면 셋을 함께 내린다. …136 을 정비하는 날(풀이 하나로 줄어드는 날)에는 먼저 셋을 8 · 8 · 12 로 되돌린다.

## 6. 끄기 · 되돌리기

- **끄기** — `infra/.env` 의 `LLM_UPSTREAMS` 줄을 지우고 update-all. 라우터를 가리키는 사본만 `LLM_BASE_URL` 로 돌아가고(1i 머리 `1i) LLM 라우터 — 풀 꺼짐(LLM_UPSTREAMS 없음 → 사본을 직접 주소로)`), 라우터는 §4 뒤에 내린다(`✓ LLM 라우터(:8730)를 내렸다 — 풀 꺼짐, 사본은 직접 주소다`). 미룬 재기동이 있거나 아직 라우터를 가리키는 사본이 있으면 ○ `LLM 라우터 내리기 미룸` — 다음 update-all 이 다시 본다. 한 서버에 일부러 묶어 둔 사본은 `LLM_BASE_URL` 로 돌아간다(묶음은 되살리지 않는다).
- **파일째 되돌리기** — 바꾸기 전 사본은 `infra/.state/llm-pool-backups/<리포>/<파일>.<UTC>` 에 있다(600). `cp -p <백업> <원래 파일>` 로 덮고 그 서비스를 다시 띄운다.
- **포트를 바꿨다** — 사본은 새 포트로 옮겨지지만 옛 포트의 라우터는 저절로 안 내린다. update-all 이 찍는 `LLM_ROUTER_PORT=<옛 포트> ./infra/scripts/llm-router.sh stop` 을 돌린다.

## 7. 알아 둘 것

- **관리 밖** — AIDataHub 챗 화면이 저장하는 주소 덮어쓰기(`chat_llm_config.json`)는 파일 사본보다 먼저다. 그 화면에서 주소를 저장했다면 라우터 주소로 바꾸거나 지운다. HEAXHub 자신의 `LLM_LOCAL_ENDPOINT` 는 OpenAI `/v1` 주소가 아니라 다루지 않는다.
- **https 서버** — 사설 CA 뒤의 https 는 받지 않는다(라우터는 운영자 셸의 프록시·CA 설정을 물려받지 않는다). 사내망 http 이거나 공인 인증서여야 한다.
- **키** — 라우터는 손님이 보낸 `Authorization` 을 그대로 넘긴다(키를 끼워 넣지 않는다). 키를 바꾸면 사본들의 키도 바꾼다.
- **로그** — `/tmp/hwax-services/llm-router.log`. 요청 본문과 키는 찍지 않는다(서버 오르내림 · 모델 어긋남 · 연결 실패만).
