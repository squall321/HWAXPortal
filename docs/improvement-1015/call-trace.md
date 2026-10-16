# 호출 추적(Phoenix) — 운영 안내

> 계획 [PLAN.md](PLAN.md) §2-2 · 결정 [context-notes.md](context-notes.md)(IM-D6 ③). 기록기는 에이전트 서버의 `call_trace.py`(HWAXAgentServer
> README 'Call trace'), 받는 쪽은 이 리포의 Phoenix 인스턴스다. 둘 다 기본 꺼짐이다.

에이전트 서버가 부르는 LLM 호출과 MCP 도구 호출을 **하나씩** 남긴다 — 어느 서버에서 얼마나 기다리고 얼마나 걸렸는지, 토큰을 얼마나 썼는지,
어느 심의·라운드·좌석(또는 챗 턴)의 호출인지. LLM 서버가 둘이 되면(docs/llm-pool) '어느 서버에서 얼마나 기다렸나' 가 특히 필요하다 — 라우터의
`/stats` 는 지금 순간만 본다.

## 무엇을 남기고 무엇을 남기지 않나

사용자 결정(IM-D6 ③)대로 **원문 없이 시간·토큰만** 남긴다. 가리는 것은 환경값이 아니라 코드다 — 본문을 켜는 손잡이는 없다. 기록기는 프롬프트·답·
스트림 조각·도구 인자·도구 결과·예외 문구를 읽지 않는다. 끝난 LLM 결과에서는 사용량과 모델 이름 칸만 꺼낸다. 자리 id 도 공백 없는 짧은 표지만 받는다
(질문 같은 글을 id 자리에 넣으면 버린다). 그래서 보존 기간·열람자를 따로 정하지 않고 지었다.

| 호출 | 남긴다 |
|---|---|
| LLM(스팬 이름 `llm`) | 어느 서버 — `hwax.llm.server`(에이전트 서버 .env 의 `VLLM_BASE_URL` 호스트:포트, 외부 응답자는 `external`) · `hwax.llm.upstream`(LLM 라우터를 지났으면 라우터가 실제로 보낸 서버 — 라우터 응답 머리 `x-hwax-llm-upstream`) |
| | 시간 — 시작과 끝(지연). 스트리밍 호출이면 `hwax.llm.ttft_ms`(첫 조각까지 — 큐 대기와 프리필)와 `hwax.llm.gen_ms`(그 뒤의 생성) |
| | 토큰 — `llm.token_count.prompt` · `completion` · `total`(서버가 준 사용량), 접두 캐시 적중 `llm.token_count.prompt_details.cache_read`(서버가 주면) |
| | 모델 이름 · `hwax.llm.http_status` · `hwax.llm.attempts`(SDK 재시도면 2 이상) · 실패면 예외 이름 `error.type` |
| 도구(스팬 이름 = 도구 이름) | 이름 · 시작과 끝 · 실패면 예외 이름 `error.type` 과 HTTP 상태 `hwax.http_status` |
| 둘 다 | `hwax.kind`(chat · delib · sim-delib · test-plan · thinking · card-review:<종류>) · `hwax.turn_id`(챗 턴) 또는 `hwax.job_id`(MCP 심의 잡) — 같은 값이 `session.id` 에도 들어가 Phoenix 의 세션 화면에서 묶인다 · `hwax.round` · `hwax.seat` · `hwax.unit` · `hwax.target`(카드 대조) |

- 호출 하나가 트레이스 하나다(부모 스팬이 없다). 묶음은 `session.id` 와 `hwax.*` id 로 본다.
- 비스트리밍 호출(심의 좌석·의장·카드 대조)은 지연 하나뿐이다 — 서버가 큐 대기를 따로 알려 주지 않는다. 대기를 보려면 스트리밍 챗의
  `ttft_ms` 와, 같은 시각의 다른 호출 수를 함께 본다.
- 스트리밍 챗 호출은 대개 토큰 수가 없다 — 서버가 스트림에 사용량을 실으려면 요청에 그 옵션을 넣어야 하는데, 기록기는 요청을 바꾸지 않는다.
- 도구 호출은 게이트웨이로 실제로 나간 것만 잰다 — 엔진의 문(유령 ID · 외부 응답자 차단)이 막은 호출은 스팬이 없다. `invoke_tool` 로 부른
  도구는 `invoke_tool` 로 남는다(안쪽 이름은 인자라 읽지 않는다).
- 마지막 라운드 뒤의 의장·요약 호출은 그 라운드 번호를 단 채 좌석 없이 남는다.

## 켜기 — cae00

1. **(dev, 한 번)** 이미지를 굽고 Drive 에 올린다 — `./infra/scripts/build-phoenix.sh` 뒤 `./infra/scripts/images-to-drive.sh`(portal·nginx
   이미지와 프런트 dist 도 함께 올린다 — status-board.md '켜기' 1 과 같다). 이미지는 340MB 남짓이다.
2. **(cae00)** 포털 `infra/.env` 에 한 줄 — `CALL_TRACE=1` 뒤 `./infra/scripts/update-all.sh`. §2(images-from-drive)가 `phoenix.sif` 를 받고
   **5c 가 Phoenix 를 띄운다**(지문 — 이미지 · 띄우는 스크립트 · 셈 — 이 바뀌었을 때만 다시 뜬다). 재부팅 뒤에는 부팅 유닛(hwax-stack —
   `services.py up --update`)이 띄운다. update-all 을 기다리지 않고 바로 띄우려면 `./infra/scripts/services.sh up call-trace`.
3. **(cae00)** 에이전트 서버 `HWAXAgentServer/.env` 에 한 줄 — `CALL_TRACE_URL=http://127.0.0.1:8750`. 반영은 재기동이다 — 도는 심의가
   없을 때 `cd ../HWAXAgentServer && ./start.sh -d`, 또는 다음 update-all §4(에이전트 서버 .env 가 바뀌어 다시 띄운다 — 도는 심의가 있으면 미룬다).
   기동 로그에 `[agent] 호출 추적(CALL_TRACE_URL) 켜짐 — 127.0.0.1:8750 …` 한 줄이 나오면 된 것이다.

⚠ 둘을 따로 켜는 까닭(한 줄로 묶지 않은 까닭) — 에이전트 서버의 .env 를 만지는 길은 env 킷(`apply-envs.sh`)뿐인데 그것은 **없는 키만 더한다**.
켜기는 되지만 끄기·포트 바꾸기가 따라가지 않아, 끈 박스의 에이전트 서버가 죽은 주소로 계속 보내게 된다. 두 쪽을 함께 고쳐 쓰려면 update-all 에
LLM 라우터(1i)만 한 구획이 새로 든다 — 이번에는 넣지 않았다. 대신 update-all 5c 가 **두 줄이 어긋나면 알린다** — 받는 쪽만 켜졌거나(⚠ '받는
쪽(Phoenix)만 켜졌다') 끈 박스에 보내는 줄이 남았으면(⚠ 'CALL_TRACE_URL 이 남아 있다'). 에이전트 서버 .env 는 고쳐 쓰지 않는다(IM-D18).
킷(`infra/env-kits/agent-server.env`)에는 주석으로만 적어 두었다.

⚠ `phoenix.sif` 가 처음 들어오는 update-all 에서는 포털도 한 번 다시 뜬다 — deploy-all 의 포털 지문이 `infra/apptainer/*.sif` 를 보기 때문이다.

## 보는 곳

- Phoenix 는 **루프백에만** 듣는다(`127.0.0.1:8750`). 화면·API·수신에 로그인이 없어서다. 정문(nginx)에 라우트를 걸지 않는다.
- 사람은 자기 PC 에서 SSH 터널로 본다 — `ssh -N -L 8750:127.0.0.1:8750 <cae00 접속 별칭>` 을 띄워 두고 브라우저로 `http://localhost:8750`.
  프로젝트 `hwax-agent-server` 를 연다. 'Sessions' 는 챗 턴·심의 잡 단위(토큰 합계가 함께 보인다), 'Spans' 는 호출 단위다. 거르기는 속성 이름을
  점으로 잇는다 — `hwax.llm.upstream == '<서버>'` · `hwax.seat == '<좌석 키>'` · `hwax.round == 2` · `span_kind == 'TOOL'`(2026-10-16 dev 확인).
- 박스 안에서는 REST 로 — `curl -s 'http://127.0.0.1:8750/v1/projects/hwax-agent-server/spans?limit=20'`.
- Phoenix 자체는 `./infra/scripts/services.sh status call-trace` 로, 로그는 `/tmp/hwax-services/call-trace.log` 다(WARNING 이상만).
- 상시 상태판(status-board.md)을 켠 박스는 `/healthz` 를 1분마다 본다 — 매니페스트 항목이 있으면 저절로 든다.

## 보존

- 기본 30일(`CALL_TRACE_RETENTION_DAYS`) — 매주 일요일 0시(UTC)에 그보다 오래된 트레이스를 지운다.
- ⚠ 이 값은 **DB 를 처음 만들 때만** 기본 정책으로 들어간다. 그 뒤로 바꾸려면 Phoenix 화면의 Settings → Data Retention(`/settings/data`)에서
  기본 정책(Default Project Retention Policy)을 고치거나, Phoenix 를 내리고 `infra/.state/call-trace/` 를 지운 뒤 다시 띄운다(쌓인 기록이 사라진다).
- 저장은 `infra/.state/call-trace/`(디렉터리 700, gitignore)의 SQLite 하나다. 본문이 없어 스팬 하나가 1~2KB 다(2026-10-16 dev 실측 — 스팬
  2,000개에 DB 본파일이 2.2MB 늘었다. WAL 은 따로 수 MB). 하루 호출 수 × 보존 날 수 × 2KB 로 어림한다.

## 끄기

1. 에이전트 서버 `.env` 의 `CALL_TRACE_URL` 줄을 지우고 재기동한다(도는 심의가 없을 때).
2. 포털 `infra/.env` 의 `CALL_TRACE` 줄을 지운다 — 다음 update-all 5c 가 떠 있는 Phoenix 를 내리고 ○ 로 남긴다(바로 내리려면
   `./infra/scripts/call-trace.sh stop`). 값을 0 으로 두면 켜짐으로 읽힌다(값이 있으면 켜는 if_env 다 — update-all 이 ⚠ 로 알린다).

순서가 바뀌어도 해는 없다 — Phoenix 가 내려가 있으면 에이전트 서버는 기록만 버리고(로그에 `[call-trace] ⚠ … 보내지 못했다` 한 줄) 호출은 기다리지
않는다. 다시 올라오면 `✓ 다시 보낸다` 한 줄이다.

## 포트·보존 바꾸기

- `CALL_TRACE_PORT`(기본 8750) — 9100~9999 는 HEAXHub 앱 포트 풀이라 쓰지 않는다([PORT-MAP](../PORT-MAP.md)). 바꾸면 옛 포트의 Phoenix 를 먼저
  내린다 — `CALL_TRACE_PORT=<옛 포트> ./infra/scripts/call-trace.sh stop`(stop 만 환경의 포트를 먼저 본다) 뒤 update-all(5c) 이나
  `services.sh up call-trace`. update-all · update-sites 는 셸이 물려준 `CALL_TRACE_PORT` 를 버린다(infra/.env 가 정본이다).
  에이전트 서버의 `CALL_TRACE_URL` 도 같은 포트로 고치고 재기동한다.
- `CALL_TRACE_RETENTION_DAYS`(기본 30, 0 은 지우지 않는다) — 위 '보존' 의 ⚠.
- 틀린 값(포트가 수가 아니다 · 날 수가 0 이상의 정수가 아니다)이면 띄우지 않고 까닭을 찍는다.

## 무엇이 어디에

| 무엇 | 어디 |
|---|---|
| 기록기(LLM 콜백 · 도구 감싸기 · OTLP protobuf 인코더 · 보내는 스레드) | HWAXAgentServer `call_trace.py`(시험 `tests/test_call_trace.py`) |
| 이미지 굽기(판 고정 — 판과 다이제스트) | `infra/scripts/build-phoenix.sh` → `infra/apptainer/phoenix.sif` |
| Drive 운반 | `images-to-drive.sh` · `images-from-drive.sh`(latest/ 의 phoenix.sif) · `drive-drift.sh` |
| 띄우기·내리기 | `infra/scripts/call-trace.sh {run\|stop}` |
| gRPC 수신기를 끄는 셈 | `infra/call-trace/phoenix_serve.py` |
| 매니페스트 항목 | `infra/services.yaml` 의 `call-trace`(tier 5, `if_env: CALL_TRACE`) |
| 저장(SQLite, gitignore) | `infra/.state/call-trace/` |
| 라우터의 '실제 서버' 머리 | `infra/llm-router/llm_router.py`(`x-hwax-llm-upstream`) |
| 시험 | `backend/tests/test_call_trace.py` · `test_llm_router.py`(머리) · `test_images_from_drive.py` |

## 띄우는 방식과 그 까닭

- `apptainer exec --cleanenv --no-home` — 띄운 셸의 프록시·비밀이 딸려 들어가지 않고 홈에 아무것도 쓰지 않는다. 상태 디렉터리를 `/state` 로,
  `infra/call-trace/` 를 `/hwax` 로(읽기 전용) 붙인다.
- `PHOENIX_HOST=127.0.0.1` 로 화면·API·OTLP/HTTP 수신이 한 포트에 뜬다. Phoenix 의 **gRPC 수신기는 이 값을 보지 않고 모든 인터페이스(`[::]`)에
  열린다** — 끄는 환경값도 없다(읽기 전용 모드에서만 꺼지는데 그러면 웹 수신도 막힌다). 그래서 띄우는 셈이 그 수신기의 시작을 비운다. 판이 바뀌어
  그 자리가 없으면 띄우지 않고 끝난다(조용히 모든 인터페이스에 열리지 않게). 기동 화면에 찍히는 `OTLP over gRPC …:4317` 은 듣지 않는 포트다.
- Phoenix 가 스스로 공용 인터넷으로 나가는 것(글꼴 · 원격 측정 · WASM 받기)을 끄고(`PHOENIX_ALLOW_EXTERNAL_RESOURCES=false` ·
  `PHOENIX_TELEMETRY_ENABLED=false`), 쓰지 않는 기능을 끈다 — 에이전트 도우미와 그 서버 쪽 bash · `/mcp` · 코드 샌드박스.
- 이미지의 `PYTHONPATH` 는 끝이 `:` 라 띄운 자리가 import 경로에 든다 — 띄우는 셈이 그 자리를 뺀다.
- 기록기는 OTLP/HTTP **protobuf** 로 보낸다 — Phoenix 20.19 의 `/v1/traces` 는 `application/x-protobuf` 만 받는다(JSON 은 415). 필요한 메시지
  몇 개만 손으로 인코딩해 에이전트 서버에 새 패키지가 들지 않는다(cae00 은 패키지를 들일 길이 없다). 시험이 공식 정의(`opentelemetry-proto`)로
  읽어 맞댄다.

## 판

지금 판은 **Phoenix 20.19.0**(2026-10-01 공개, `arizephoenix/phoenix` 의 그 판 다중 아키텍처 목록 다이제스트)이다. 올릴 때는
`build-phoenix.sh` 의 `PHOENIX_VERSION` · `PHOENIX_DIGEST` 두 줄과 이 문서를 함께 고치고 굽는다 — 받은 이미지의 판 라벨(`arize-phoenix-v<판>`)이
다르면 굽기가 멈춘다. 새 판에서 다시 볼 것 — gRPC 수신기 자리(`phoenix.server.grpc_server.GrpcServer.__aenter__`), 이미지 안 파이썬 경로
(`/usr/bin/python3.13`), `/v1/traces` 가 받는 형식, 위 환경값 이름들. 새 이미지가 Drive 로 오면 update-all 5c 가 지문(이미지)이 바뀐 것을 보고
다시 띄운다.

## 함정

- 에이전트 서버를 켜고 Phoenix 를 안 띄우면 기록은 전부 버려진다(로그 ⚠ 한 줄 — 호출은 그대로 돈다). 둘 다 켰는지는 Phoenix 화면에 새 스팬이
  보이는지로 본다.
- Phoenix 가 다시 뜨는 동안의 기록은 버려진다(보내는 쪽은 다시 보내지 않는다).
- 외부 응답자(Claude 길) 호출은 `external` 서버로 남고 토큰 수가 없다(사람 쪽 Claude 가 답한다). 지연은 과제가 줄을 서서 답이 오기까지다.
