# LLM/GPU 현황 — cae00 절차

> 이 문서는 cae00 에서 LLM/GPU 현황 수집기(M1)와 관리자 화면(M2)을 켜는 사람 몫을 적는다. 계획은 [PLAN.md](PLAN.md) §3, 까닭은
> [context-notes.md](context-notes.md)(OD-2 ~), 할 일은 [checklist.md](checklist.md). 명령은 따로 적지 않으면 포털 리포 루트(cae00 은
> `~/Projects/HWAXPortal`)에서 돈다. 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다. 모두 읽기만 한다 — 수집기는 서버에 GET 만 보낸다.

## 0. 이 판을 받기만 하면 — 아무것도 바뀌지 않는다

`infra/.env` 에 `LLM_STATUS` 가 없으면 update-all 5d 에 ○ 한 줄만 남는다. 그 포트(8760)에 다른 앱이 떠 있어도 건드리지 않는다 — 수집기인지는
`/health` 의 몸으로 본다(`llm-status.sh probe` — OD-28).

- `○ LLM/GPU 현황 수집기 — infra/.env 에 LLM_STATUS 가 없다 — … 수집기를 띄우지 않았다`
- 1c(env-sync)가 `# LLM_STATUS=1` · `# LLM_STATUS_PORT=8760` · `# LLM_STATUS_REPLICA_PORTS=18711-18720` 를 **주석으로** 덧붙인다(선택 설정 — 켜지 않는다).
- 관리 메뉴의 'LLM · GPU 현황' 은 '수집기가 꺼져 있다'(503)를 보인다. 다른 화면 · 서비스는 그대로다.

## 1. 켜기 전에 — 무엇을 읽게 되나(손으로 한 번)

수집기는 `infra/.env` 를 스스로 읽는다. 켜기 전에 `once` 로 한 번 읽어 본다(저장하지 않는다 · 서버마다 GET 넷).

```bash
python3 infra/llm-status/collector.py once 2>/dev/null | python3 -c '
import json, sys
d = json.load(sys.stdin)
for t in d["targets"]:
    v = t["values"]
    up = "살아 있음" if v["up"]["value"] else (v["up"]["error"] or "모름")
    print(t["label"], t["addr"], "|", up, "| 판", v["version"]["value"], "| 창", v["context"]["value"], "|", v["models"]["error"] or "")
a = d["agent"]["values"]["up"]
print("에이전트 서버", a["value"], a["error"] or "")'
```

기대 — 대상마다 한 줄. 대상을 따로 적지 않으면 `LLM_UPSTREAMS` 의 서버들(GLM-1 · GLM-2 …), 없으면 `LLM_BASE_URL`(GLM), 그리고
`CHAT_LLM_BASE_URL`(챗 LLM)이다.

- **묶음 주소면 따로 적는다.** `LLM_BASE_URL` 이 18800 묶음(nginx)이면 'GLM' 카드의 도는 · 기다리는 요청 · KV · 판 · 모델은 그 읽기에 답한
  아무 한 대의 숫자다(OD-2). 토큰 속도 · 첫 토큰 · 끝까지 · 줄 선 시간 · 끝낸 요청 · 오류 · 끊김 · 선점 · 앞부분 캐시 적중은 같은 서버 프로세스
  (`process_start_time_seconds` 가 같은 표본)가 60초 안에 두 번 답했을 때만 그 한 대의 값으로 보이고, 아니면 '모름' 이다 — 뒤에 서버가 둘이면
  대개 값이 보이고 많으면 대개 '모름' 이다. 그 줄을 내지 않는 vLLM(API 서버 여럿)이면 창 안에서 카운터가 줄 때마다 그 창을 비워 거의 늘 '모름'
  이다(OD-26). 서버마다 보려면 2절의 `LLM_STATUS_TARGETS` 에 서버별 주소를 적는다 — 그 주소는 받은 편지함 2026-11-02 Q4 · Q5 의 답이다. 챗
  LLM(18700 묶음)도 같다 — 복제본은 `LLM_STATUS_REPLICA_PORTS` 로 따로 본다.
- `HTTP 401 — 키가 없다(infra/.env 의 LLM_API_KEY)` 면 모델 목록 · 창만 못 읽는다(상태 · 지표는 키 없이 읽힌다). 3절의 키를 본다.
- `연결 거부` · `연결 시간 초과(3초)` · `읽기 시간 초과(5초)` 는 그 서버의 까닭이다 — 그 서버만 '모름' 이고 다른 서버는 그대로 읽힌다.

## 2. 켜기 — `infra/.env`

켜기 전에 그 포트를 남이 쓰지 않는지 본다 — cae00 의 8760 은 아직 확인하지 않았다(docs/PORT-MAP.md).

```bash
ss -ltnpH 'sport = :8760'     # 아무 줄도 나오지 않아야 한다 — 줄이 나오면 아래 LLM_STATUS_PORT 에 빈 포트를 적는다(7절)
```

```
LLM_STATUS=1
# 선택 — 서버마다 따로(묶음 주소는 부하 · 판이 아무 한 대의 숫자이고 속도 · 지연은 같은 서버가 이어 답할 때만 보인다 — 1절). 이름은 영숫자 · . _ - 로 40자까지(그래프 주소에 쓴다) · agent · router 는 수집기가 쓰는 이름이라 못 쓴다
LLM_STATUS_TARGETS=GLM-1=http://<GLM 서버1 주소>:<포트>/v1,GLM-2=http://<GLM 서버2 주소>:<포트>/v1,QWEN=http://127.0.0.1:18700/v1
# 선택 — 챗 LLM 복제본(호스트 · 스킴은 CHAT_LLM_BASE_URL 의 것)
LLM_STATUS_REPLICA_PORTS=18711-18720
# 선택 — 포트 → 노드 짝 파일(받은 편지함 Q7 의 답 — 그 파일의 자리)
LLM_STATUS_REPLICA_MAP=~/stcx-llm/<짝 파일>
```

- env-sync 가 넣어 둔 주석 줄이 있으면 그 줄의 `#` 을 지우고 값을 적는다. `LLM_STATUS=0` 도 켜짐이다(값이 있으면 켠다 — 5d 가 알린다).
- 서버별 GLM 주소가 `LLM_BASE_URL` · `LLM_UPSTREAMS` 의 주소가 아니면 그 서버에는 키를 싣지 않는다 — 모델 목록 · 창만 '키를 싣지 않는다' 로 보인다(3절).
- 쉼표로만 나눈다 — 공백을 쓰려면 값 전체를 큰따옴표로 감싼다(이 파일은 포털 start.sh 가 bash 로 소싱한다).
- 짝 파일의 꼴은 Q7 답 전까지 가정이다 — 줄마다 `<포트> <노드>`(사이는 공백 · = · : · , 중 하나 · 순서는 바뀌어도 된다 · `#` 뒤는 설명) 또는
  JSON `{"18711": "<노드>", …}` · `[{"port": 18711, "node": "<노드>"}, …]`. 못 읽으면 복제본은 포트로만 보이고 화면 머리에 '설정 — 짝 파일 …' 까닭이
  뜬다. 꼴이 다르면 dev 에서 `infra/llm-status/collector.py` 의 `read_replica_map` 하나를 맞춘다.

## 3. 키

수집기가 `infra/.env` 의 `LLM_API_KEY` · `CHAT_LLM_API_KEY` 를 **스스로** 읽는다 — 이미 LLM 풀(docs/llm-pool) · 챗 LLM(docs/chat-llm-stcx)으로
적어 둔 그 줄이다. 새로 적을 것은 없다.

- 키는 `/v1/models` 에만 싣는다. `/health` · `/version` · `/metrics` 는 키를 묻지 않는다(vLLM — OD-2).
- 어느 키를 싣나 — `LLM_API_KEY` 는 `LLM_BASE_URL` · `LLM_UPSTREAMS` 의 서버에만, `CHAT_LLM_API_KEY` 는 `CHAT_LLM_BASE_URL` 과 그 복제본에만 싣는다.
  같은 주소인지는 스킴 · 포트가 같고 호스트가 같거나 둘 다 `localhost` · `127.0.0.1` · `::1` 이면 같다(OD-33). `LLM_STATUS_TARGETS` 에 적은 주소가 그
  어느 것도 아니면 키를 싣지 않는다 — 그 서버가 키를 물으면 모델 목록 · 창이 `HTTP 401 — 이 주소에는 키를 싣지 않는다` 로 보인다(상태 · 지표는 키 없이
  읽힌다). 401 이어도 다른 키로 다시 해 보지 않는다(키를 다른 서버에 보내지 않는다).
- 키는 명령줄 · 환경 · 로그 · 화면 어디에도 싣지 않는다. 수집기는 환경을 비우고(`env -i`) 시스템 python3 격리 모드(`-I`)로 뜨고, 원격에서 받은
  글과 내는 답 · 로그 줄에서 설정의 키를 `<가림>` 으로 바꾼다(라우터 규칙 LP-D11).

## 4. update-all

```bash
./infra/scripts/update-all.sh
```

5d 에서 기대하는 줄.

- `✓ LLM/GPU 현황 수집기 — http://127.0.0.1:8760 (루프백 — 사람은 포털 관리 › LLM · GPU 현황으로 본다, …)`

같은 실행의 §2 가 포털을 다시 띄운다(`infra/.env` 가 바뀌었다 — 포털 지문). 다시 뜬 포털은 start.sh 가 넘긴 수집기 주소(`LLM_STATUS_URL`)를 받는다.
도는 심의가 있어 포털 재기동이 미뤄졌으면 화면은 그동안 '수집기가 꺼져 있다'(503)다 — 심의가 끝난 뒤 update-all 을 한 번 더.
상시 상태판(STATUS_BOARD)을 켠 박스면 상태판이 수집기의 `/health` 도 1분마다 본다(5b 가 매니페스트에서 저절로 싣는다).

## 5. 확인

```bash
./infra/scripts/services.sh status llm-status
curl -s --noproxy '*' http://127.0.0.1:8760/health; echo
tail -20 /tmp/hwax-services/llm-status.log
ls -la infra/.state/llm-status/
```

- `/health` — `"status":"ok"` · `"targets":<대상 수>` · `"enabled":true` · `"db_error":null`. 주기가 멈추면 503 `"stalled"` 다.
- 로그 — `시작 — 127.0.0.1:8760 · 15초마다(모델 목록 60초) · 저장 infra/.state/llm-status`, `설정을 읽었다 — LLM 대상 N · …`, 그리고 서버가
  내려가거나 다시 오를 때만 한 줄씩. 요청마다 남기지 않는다.
- 저장 — 폴더 `drwx------`, `llm-status.sqlite`(와 `-wal` · `-shm`) `-rw-------`.
- 화면 — 관리 › LLM · GPU 현황.
  - 머리 — '수집기 도는 중', 원천(서버 · 에이전트 서버 · 라우터)마다 상태 · 판 · 지표 · 모델 목록을 마지막으로 읽은 때. 노란 칸은 낡았다(주기 셋을
    놓쳤다 — 지표 45초 · 모델 목록 180초).
  - 서버 카드 — 모델 · 살아 있음(아니면 까닭) · vLLM 판 · 창(같은 모델의 창이 서버마다 다르면 '서버끼리 창이 다르다' — Q12 3번의 그 물음) · 도는/기다리는
    요청과 1시간 · 24시간 그래프 · KV 캐시 · 입력/출력 토큰 초당 · 첫 토큰 · 끝까지 · 줄 선 시간 p50 · p95(≈ — 5분 창의 히스토그램 어림) · 끝낸 요청 ·
    HTTP 5xx 답 · 오류로 끝난 요청 · 끊김(abort) · 선점(분당) · 앞부분 캐시 적중. 한 요청이 'HTTP 5xx 답' 과 '오류로 끝난 요청' 에 함께 들 수 있다 —
    스트리밍이 아닌 요청이 엔진 오류로 끝나면 vLLM 이 500 으로도 답한다(스트리밍은 이미 200 을 보낸 뒤라 '오류로 끝난 요청' 에만 든다, OD-30).
  - 복제본 표 — 포트(와 노드) · 상태 · 도는 · 기다리는 · KV · 출력 토큰 초당 · 첫 토큰 p95 · 창 · 판.
  - 지금 쓰는 일 — `curl -s http://127.0.0.1:9009/health` 의 delib_active · review_active 등과 같은 수다(HWAX 몫만 — 같은 서버를 바로 부르는
    다른 서비스는 들지 않는다).
- 그래프는 처음에 비어 있다(쌓는 중) — 1시간 그래프는 몇 분 뒤, 24시간 그래프는 5분 칸이 접힌 뒤부터 선이 보인다.

## 6. 답을 기다리는 자리(스텁) — 화면에 '모름 — 무엇이 필요한가' 로 보인다

| 칸 | 지금 | 필요한 것 | 다음 |
|---|---|---|---|
| GPU 잡(stcx Slurm) | `모름 — … ssh stcx 가 되는지가 먼저다(… Q8)` | Q8(사람 없는 `ssh stcx`) · Q9(LLM 잡 sbatch 머리 · 잡 줄) | M3 — 60초마다 ssh 한 번(BatchMode · 정해진 읽기 명령)으로 squeue. dev 에서 짓고 cae00 에서만 확인된다 |
| GPU 하드웨어 | `모름 — … 노드 관리자(Q11), … 운영 팀(Q12)의 승인이 먼저다(M4)` | Q11(stcx 노드 — 다음 rolling 때 sbatch 에 nvidia-smi 표본 한 줄이 권장) · Q12(GLM 서버의 하드웨어 원격 측정) | M4 |
| 복제본 노드 이름 | 포트만 보인다(짝 파일을 안 적었거나 못 읽었다) | Q7(짝 파일의 자리 · 꼴) | 2절 `LLM_STATUS_REPLICA_MAP` |
| GLM 서버별 대상 | 묶음 주소면 'GLM' 한 줄의 부하 · 판은 아무 한 대의 숫자이고 속도 · 지연은 같은 서버가 이어 답할 때만 보인다(1절) | Q4 · Q5(서버마다 주소 · 판 · 지표 줄 수) | 2절 `LLM_STATUS_TARGETS` |
| 긁는 주기 | 15초(코드 값) | Q12 1번(15 ~ 30초마다 긁어도 되나) | 더 길게를 요구하면 dev 에서 손잡이를 더한다(지금은 없다 — OD-17) |

## 7. 손잡이 — `infra/.env`

| 키 | 기본 | 언제 |
|---|---|---|
| `LLM_STATUS` | 없음(꺼짐) | 켠다. `0` 도 켜짐 — 끄려면 줄을 지운다 |
| `LLM_STATUS_PORT` | `8760` | 그 포트를 남이 쓸 때만(docs/PORT-MAP.md — 9100 ~ 9999 는 허브 앱 포트 풀이라 피한다). 바꾸면 옛 포트의 수집기는 손으로 내린다 — `LLM_STATUS_PORT=<옛 포트> ./infra/scripts/llm-status.sh stop` |
| `LLM_STATUS_TARGETS` | 없음(기본 대상) | 서버마다 따로 볼 때(2절) |
| `LLM_STATUS_REPLICA_PORTS` | 없음 | 챗 LLM 복제본을 따로 볼 때(예 `18711-18720` — 64개까지) |
| `LLM_STATUS_REPLICA_MAP` | 없음 | 복제본에 노드 이름을 붙일 때(2절 · Q7) |
| `LLM_STATUS_AGENT_URL` | `http://127.0.0.1:9009` | 에이전트 서버를 다른 포트에 띄운 박스만 |

고정 값(코드) — 15초마다(모델 목록 60초) · 연결 3초 · 읽기 5초(에이전트 서버 /health 는 12초) · 주기 셋을 놓치면 낡음 · 표본 48시간 · 5분 접기
35일 · 대상 32개까지.
포털 쪽 `LLM_STATUS_URL`(backend/.env)은 적지 않는다 — start.sh 가 `LLM_STATUS` 를 보고 넘긴다. 직접 적은 값은 `LLM_STATUS` 가 없을 때만 산다.

## 8. 끄기 · 손으로

- 끄기 — `infra/.env` 의 `LLM_STATUS` 줄을 지우고 update-all. 5d 가 `✓ LLM/GPU 현황 수집기(:8760)를 내렸다 — … 쌓은 기록은 infra/.state/llm-status 에
  그대로 남는다` 와 ○ 를 남긴다. 기록을 지우려면 수집기가 내려간 뒤 그 폴더를 손으로 지운다.
- 손으로 — `./infra/scripts/llm-status.sh start`(뒤에서 띄우고 곧바로 돌아온다 · 로그 `/tmp/hwax-services/llm-status.log` · 그 포트에 이미 듣는 것이
  수집기가 아니면 띄우지 않고 실패한다) · `stop`(그 포트를 듣는 수집기만 내린다 — 명령줄이 수집기가 아니면 손대지 않는다) · `check`(그 포트를 듣는 것이
  수집기인가 — update-sites 가 재기동을 생략하기 전에 같은 것을 묻는다, OD-29). `LLM_STATUS` 가 없는 박스에서 손으로 띄우면 다음 update-all 이 내린다.

## 9. 알아 둘 것

- 수집기는 포털 백엔드가 아니라 호스트의 시스템 python3(3.10 이상 · 표준 라이브러리만)으로 돈다 — 포털 갱신으로 끊기지 않는다(OD-4). 지문은
  수집기 파일 · 띄우는 스크립트뿐이라 문서 커밋으로는 다시 뜨지 않는다. `infra/.env` 는 주기마다 다시 읽는다 — 대상 · 키를 바꿔도 다시 띄우지 않는다.
- 수집기 창구(127.0.0.1:8760)에는 인증이 없다 — 라우터 `/stats` · 상태판과 같은 신뢰 수준이다. 같은 박스의 다른 계정이 서버의 호스트:포트와 수를 읽을 수
  있다. 키 · 주소 원문(계정 · 경로)은 내지 않는다.
- 서버 한 대가 매달려도 다른 서버는 제 주기에 읽힌다 — 그 서버는 앞 읽기가 끝날 때까지 주기를 건너뛰고 값이 낡음으로 보인다.
- 지금 쓰는 일(에이전트 서버)이 '모름 — 늦음' 이면 그 /health 가 12초 안에 답하지 않은 것이다 — LLM 이 안 닿으면 에이전트 서버가 창을 묻느라
  늦는다(내려감이 아니다). '내려감' 은 연결 거부 · 오류 상태(5xx 등)일 때만이다(OD-36).
- 서버가 다시 뜨면(`process_start_time_seconds` 가 바뀐다) 앞 프로세스의 표본은 셈에서 빠진다 — 새 프로세스의 표본이 둘 쌓일 때까지 빈칸이고
  음수 속도를 그리지 않는다. 그 줄이 없는 서버는 창 안에서 카운터가 하나라도 줄면 그 창(카드 60초 · 지연 5분)을 비운다(OD-26). 어느 길로 쟀는지는
  값의 `source` 가 말한다(`metrics/process_start_time_seconds` · `metrics/counters_only`). 카드의 토큰 속도는 60초 창, 그래프는 표본마다(15초)다.
- 저장은 대상 13개(GLM 둘 · Qwen 묶음 · 복제본 열)면 수십 MB 다(표본 48시간 · 5분 칸 35일 — 5분마다 지운다).
