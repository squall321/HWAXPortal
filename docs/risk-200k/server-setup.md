# 리스크 심사 20만 창 — cae00 에서 할 일 (사람 몫)

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) · 체크리스트 [checklist.md](checklist.md).
> 대조 시점 2026-10-21 — 엔진 `27d7d8c` · 리스크 앱 W3 커밋 · 포털 이 문서의 커밋. 박스 상태는 적지 않는다(그때그때 본다).
> 4절(A/B)의 4-1 ~ 4-4 는 2026-11-22 에 리스크 앱 `699bba8` · 에이전트 서버 `a996b69` · 포털 `09693c6f` 의 코드로 다시 대조해 메웠다.
> 단위 쪽 줄(0 · 3절)과 6절은 2026-11-24 에 에이전트 서버 `b3159bc` · 리스크 앱 `45c2b05` 의 코드로 대조했다(W-D22 · W-D23).

## 0. 무엇이 바뀌나 — 스위치는 없다

장치는 **에이전트 서버가 아는 LLM 창 값**에서 저절로 켜진다(W-D7). 1M 창에서는 한 장 자리를 넘는 카드가 없어 조각 · 쪽이 생기지 않고,
엔진의 계획 · 판 · 계약 예제가 바이트 그대로다. 다만 1M 에서도 넓어지는 곳이 셋 있다(W-D21) — 훑기에 걸린 카드가 카드 밖 호출의 몫을
넘던 칸은 그 카드를 제목 대신 전문으로 싣고(토큰이 는다), 50만 자 남짓 넘는 단위는 보류 대신 카드를 조각 내며, 리스크 심사 좌석의 도구
순위에 `get_record_sections` 가 앞에 선다. GLM 5.3 Flash(20만)로 바꾸면 그 순간부터 —

- 한 장 자리(판정 · 훑기 자리 중 작은 것, 출력 32,000 토큰이면 약 12.6만 자)를 넘는 카드는 조각으로 나눠 여러 번 묻고 카드 한 장의
  판정으로 합친다(W1). 단위가 커서 카드와 함께 넘쳐도 같다(W2-C).
- 카드 밖 · 입력 결손 호출은 훑기에 걸린 카드와 훑기 답이 없는 카드를 창까지 전문으로 싣고, 넘치면 쪽으로 나눠 묻는다(W2-B).
- 검토 단위 하나가 홀로 창을 넘으면(출력 32,000 토큰이면 140,291자, 출력 미설정이면 155,915자) 종전에는 계획이 그 단위를 oversize 로 내고 잡이
  `ctx_too_small` 로 섰다. 이제 계획이 `unit_paged` 로 내고 에이전트 서버가 그 단위를 쪽으로 나눠 묻고 카드마다 한 결과로 합친다(W-D22 — 보충
  시도까지 통째로 안 들 때만). 문턱 손잡이는 에이전트 서버 환경의 `CARD_REVIEW_UNIT_PAGE_SHARE`(기본 1 — 6절의 측정을 본 뒤 정한다, 바꾸면
  에이전트 서버 재기동).
- 셀마다 카드 커버리지를 적고, 품질 블록(전문가 · 종합 보고서)에 `[누락 0 증명]` 줄이 실린다. 놓친 카드가 있으면 불변식 G10 이
  완결(C1)을 막는다(W3).
- 쟁점 패널의 긴 카드 절은 인용 둘레로 싣고, 좌석은 `get_record_sections` 로 절 전문을 다시 읽는다(W4).

호출은 는다 — dev 표본(32명) 기준 판정 호출이 셀당 중앙값 2.6배, 훑기 4.5배. 실제 배수는 4절 A/B 로 잰다.

## 1. 올리기

1. `update-all` 한 번 — 엔진 · 리스크 앱 · 포털이 함께 올라간다. 리스크 앱이 엔진의 새 칸(`extra.must_full`)을 보내는 것은 엔진의
   `limits.features` 에 `must_full` 이 있을 때뿐이라, 올리는 차례가 어긋나도 422 로 깨지지 않는다.
2. 에이전트 서버 재기동 — `deliberation.py`(좌석 도구)가 바뀌었다. update-all 이 심의 도는 중이면 재기동을 미루므로(○ 건너뜀) 그때는
   심의가 끝난 뒤 다시 돌리거나 `cd ../HWAXAgentServer && ./start.sh -d`.
3. 확인 — 포털 경유로 `GET /agent/card-review/limits` 의 `features` 가 `["chunk", "must_full"]` 이다.

## 2. 20만 모델로 바꾸기

1. LLM 주소 · 모델을 GLM 5.3 Flash 로 바꾼다 — 정본은 `infra/.env` 의 `LLM_BASE_URL` · `LLM_MODEL`(· `LLM_API_KEY`), 에이전트 서버의
   사본은 `HWAXAgentServer/.env` 의 `VLLM_BASE_URL` · `VLLM_MODEL` 이다(LLM 서버 둘을 나눠 쓰면 `LLM_UPSTREAMS` 도 함께 — docs/llm-pool).
   update-all 출력의 `VLLM_BASE_URL=` 줄로 사본이 새 주소인지 보고, 아니면 사본을 손으로 고친 뒤 에이전트 서버를 재기동한다. 창은 LLM
   서버의 `/v1/models` 의 `max_model_len` 에서 읽는다. LLM 서버가 창을 알리지 않으면 에이전트 서버에 `LLM_CONTEXT_TOKENS=200000` 을 준다.
2. **출력 상한** — GLM 5.3 Flash 의 출력 상한을 알면 `CARD_REVIEW_MAX_TOKENS` 로 적는다(모르면 엔진 기본 셈 — 출력 16,000 토큰 가정,
   창 20만이면 프롬프트 한도 179,676자). 너무 크게 적으면 프롬프트 자리가 준다.
3. 도는 리스크 심사 잡은 멈추지 않는다 — 판이 바뀌면 앱이 그 세션을 놓고 다음 세션이 새 창으로 계획을 다시 받는다(보류 없음).
   이미 닫힌 셀은 그대로 남는다(커버리지를 적기 전 셀은 품질 줄에 '모름' 으로 센다).
4. 확인 — `GET /agent/card-review/limits` 의 `ctx_tokens` 가 200000 근처, `ctx_source` 가 `server`(또는 `env`).

## 3. 첫 잡에서 볼 것

- 전문가 보고서 품질 블록의 `[누락 0 증명]` 줄 — `놓침 0` 이어야 한다. `훑기에 걸렸는데 제목만` 이 0 이 아니면 단위가 창을 거의 다
  쓴 칸이 있다는 뜻이다(그 카드는 훑기에서 전문으로 맞대어졌다).
- 종합(완결)이 C1 에 서지 않으면 커버리지 · 불변식 목록에 `(G10)` 줄이 있는지 본다 — 어느 칸 · 어느 카드인지 적혀 있다.
- 에이전트 서버 로그 — `조각 n개` · `쪽 n개` 줄이 보이면 장치가 돈 것이다. `· 재판정 ok/failed/skipped` 는 조각들이 갈린 카드다.
  `단위 쪽 n개(쪽 자리 m자)` 줄은 홀로 창을 넘는 단위를 나눈 것이고, `· 판정 빠짐 [K…]` 이 붙으면 그 카드는 한 쪽에서 판정이 없어 빠진 카드로
  다시 묻는다(W-D22). 그런 단위가 머리(요약 · 읽는 법 · 결측)부터 창을 넘으면 쪽으로도 못 나눠 `over_budget` 보류다 — 6절의 `head_risk` 를 본다.
- 호출 수 · 시간 — 4절 A/B 의 기준이 된다.

## 4. A/B 측정 (W5 — G3 기준값 확인)

목적은 같은 대상을 1M 과 20만으로 돌려 걸림 판정이 얼마나 같은지(G3, 초안 95% — 사용자에게 다시 묻는다) · 호출 수 · 시간을 재는 것이다.
**모델을 바꾸기 전에** 지금의 1M GLM 으로 둘 다 잴 수 있다 — 임시 에이전트 서버에 `LLM_CONTEXT_TOKENS=200000` 을 주면 엔진이 창을
20만으로 셈해 조각 · 쪽을 그대로 만든다(모델의 질은 같고 창만 다르다).
⚠ 엔진이 `41a3996`(docs/delib-ops R5 — 사람이 적은 창은 서버 답의 상한) 이상이어야 한다. 그 전 판에서는 서버 답(1M)이 이 값을 눌러 그냥
1M 으로 돈다(10-22 대조). 임시 서버를 띄운 뒤 그 `/health` 의 `context_tokens` 가 200000 이고 `context.source` 가 `env` 인지 먼저 본다.

1. 대상 하나를 고른다 — 긴 카드를 가진 전문가가 범위에 드는 것(dev 표본에서 passive-fuse-protection · mech-tim 같은 영역).
2. 지금 그대로 검토 잡 한 번(A) — **끝날 때까지**(열린 셀 0). 그 창을 적는다 — 운영 `curl -s --noproxy '*' http://127.0.0.1:9009/health` 의
   `context_tokens` · `context.source`. `docs/delib-ops` 로 `LLM_CONTEXT_TOKENS`(섞인 풀의 작은 창)를 적은 박스면 A 는 1M 이 아니라 그 값이다 —
   200000 이하면 A 와 B 의 창이 같아 잴 것이 없다.
3. 같은 대상 · 같은 범위를 20만 창으로 새 잡 한 번(B) — 4-2 의 때에 4-3(임시 서버) → 4-4(포털 중계를 임시 서버로 · B 잡 · 되돌리기). 리스크 앱이
   엔진을 고르는 칸이 없어 이 길이 박스 전체에 걸린다(4-1).
4. 견줄 것 — 셀마다 걸림(FAIL · WARNING) 카드 집합의 일치율, 판정 호출 · 훑기 · 카드 밖 호출 수, 잡 시간, `[누락 0 증명]` 줄. 엔진 로그의
   `조각 n개` · `쪽 n개` 줄은 A 가 운영 로그(`../HWAXAgentServer/agent-server.log`), B 가 임시 서버 로그(`$D/agent.log` — 4-3)에 있다.
5. 결과는 이 폴더의 context-notes 에 W-D 로 적는다(수치 · 대상 · 날짜). 그 배수로 호출 어림(W-D19)을 보정한다.

### 4-1. 리스크 앱은 엔진을 어디서 찾나 — 박스 전체 설정이다(11-22 코드 대조)

- 리스크 앱은 에이전트 서버를 직접 부르지 않는다. 카드 대조 넷(`limits` · `pack` · `plan` · `run`)과 패널(`/agent/chat`)은 `HWAXRISK_PORTAL_BASE`
  (리스크 앱 매니페스트 `.portal/manifest.yaml` 의 `launch.env` — 정문 nginx 오리진)의 포털로 간다(리스크 앱 `backend/app/engine_client.py`
  `PortalReviewEngine` · `PortalPanelEngine`). 포털은 그것을 자기 `AGENT_SERVER_URL`(포털 `backend/.env`, 기본 `http://127.0.0.1:9009`) 하나로
  중계한다(포털 `backend/app/agent/routes.py` `_cr_unary` · `card_review_run`). 게이트웨이는 거치지 않는다.
- 리스크 앱의 `HWAXRISK_AGENT_URL`(비면 `http://127.0.0.1:9009`)은 `/health` 만 읽는다 — 패널의 모델 스냅숏과 비우기 깃발. 카드 대조의 창은 여기서
  오지 않는다.
- 둘 다 환경변수다 — `<데이터>/knobs.env` 의 손잡이(`config.BOX_KNOBS`)가 아니다. 잡마다 엔진을 고르는 칸도 없다.
- 그래서 리스크 앱이 임시 서버를 보게 하는 길은 **포털의 중계 주소를 임시 서버로 바꾸는 것** 하나다. 그동안 이 포털의 챗 · 띵킹 · 웹 심의 ·
  리스크 패널 · 카드 대조가 **모두** 임시 서버로 간다(창 20만 · 임시 서버의 원장). 게이트웨이를 거친 MCP 심의(`deliberate_*`)는 게이트웨이
  설정의 에이전트 서버 백엔드(`hwax-deliberation` — 예제는 `:9009/mcp/`)로 가므로 운영 서버에 남는다. 운영 에이전트 서버는 내리지 않는다 —
  포털만 두 번(바꿀 때 · 되돌릴 때) 다시 띄운다.
- 포털이 같은 주소로 묻는 뒤 일(이용 통계 접기 `usage_fold` · 알림 폴러 · 인사이트 접수)도 그동안 임시 서버에 묻는다. 이용 통계의 에이전트 서버
  몫은 오늘 · 아직 안 닫힌 날이면 되돌린 뒤 다음 접기가 운영 값으로 다시 쓰지만, 그 사이 닫히는(사흘째) 날이 있으면 임시 서버의 수로 닫힌다 —
  되돌린 뒤 관리 '이용 통계' 의 접기 기록을 본다(닫힌 날을 다시 여는 길은 대조하지 않았다 — 확인 필요).
- 리스크 앱만 따로 돌리는 길(포털을 하나 더 띄우고 리스크 앱의 `HWAXRISK_PORTAL_BASE` 를 그쪽으로)은 쓰지 않는다 — 리스크 앱을 다시 배치해야
  하고(그동안 그 앱의 다른 잡도 그쪽으로 간다), 두 번째 포털이 같은 원장으로 뒤에서 도는 일(알림 폴러 · 이용 통계 접기 같은 것)을 함께 돌리는지
  대조하지 않았다(확인 필요).

### 4-2. 언제 — 사람이 없는 때

1. A 잡이 끝났다(열린 셀 0). 판(`limits_rev`)이 바뀌면 도는 잡의 남은 셀은 새 창으로 계획을 다시 받는다(2절 3) — 끝나지 않은 A 의 셀이 20만으로
   섞인다. 되돌릴 때도 같다 — B 잡이 끝나기 전에 되돌리면 B 의 남은 셀이 A 의 창으로 돈다.
2. 운영 에이전트 서버가 한가하다 — 셋 다 0 이다(`../llm-pool/capacity.md` 1절과 같은 줄). 리스크 앱 화면에서도 A/B 말고 돌거나 기다리는 잡이 없다.

   ```bash
   curl -s --noproxy '*' http://127.0.0.1:9009/health \
     | python3 -c 'import json,sys; d=json.load(sys.stdin); print("카드 대조", d.get("review_active"), "· 심의", d.get("delib_active"), "· 줄 선 심의", d.get("delib_queued"))'
   ```

3. 챗 · 심의를 쓰는 사람에게 미리 알린다 — 바꾼 동안 시작한 웹 심의는 임시 서버의 원장에 남아, 되돌린 뒤에는 포털이 운영 서버에 묻으므로 화면에서
   이어지지 않는다. 밤이나 주말처럼 아무도 쓰지 않는 때를 고른다.
4. 재는 동안 update-all 을 돌리지 않는다 — 포털을 다시 띄우면 그 순간 운영 주소로 돌아간다(1 의 섞임).

### 4-3. 임시 에이전트 서버 띄우기

`start.sh` 로 띄우지 않는다. `start.sh` 는 `.env` 를 명령줄 환경보다 **뒤에** 읽어(`.env` 가 이긴다) 운영 `.env` 에 `LLM_CONTEXT_TOKENS`(4절 2)가
있으면 이 실행의 20만을 덮고, `AGENT_PORT` 가 있으면 그 포트(운영 서버)를 내리고 다시 띄운다. `-d` 면 기본 로그(`agent-server.log`)를 비우고 새로
쓴다. 그리고 같은 리포 자리의 잡 원장(`delib-jobs` — `artifacts` 의 형제)을 함께 쓴다 — 기동 때 원장의 줄 선 심의를 다시 세우므로
(`delib_jobs._requeue`) 운영 서버의 줄이 두 번 돈다. 아래는 `.env` 를 `start.sh` 와 같은 규칙으로 읽은 **뒤에** 이 실행의 값을 덮고, 원장 · 그림 ·
비우기 깃발 · 기준선 자리 · 토큰 장부를 따로 둔다.

```bash
cd ../HWAXAgentServer                     # 포털 리포 루트에서
T=9019                                    # 빈 포트 — 허브 앱 포트 풀(9100 ~ 9999) 밖
D="$HOME/agent-ab-200k"                   # 이 실행의 몫(원장 · 그림 · 깃발 · 로그) — 운영 자리와 겹치지 않게
ss -ltn | grep ":$T " || echo "· :$T 비었다"   # 줄이 찍히면 누가 쓴다 — T 를 바꾼다
mkdir -p "$D"
(
  while IFS= read -r l || [ -n "$l" ]; do   # start.sh 와 같은 규칙 — KEY=값 줄만, 양끝 따옴표만 벗긴다
    case "$l" in ''|'#'*) continue ;; esac
    printf '%s' "$l" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=' || continue
    k="${l%%=*}"; v="${l#*=}"
    case "$v" in \"*\") v="${v#\"}"; v="${v%\"}" ;; \'*\') v="${v#\'}"; v="${v%\'}" ;; esac
    export "$k=$v"
  done < .env
  export VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}" VLLM_MODEL="${VLLM_MODEL:-qwen2.5-7b-dev}"
  export LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S="${LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S:-300}"
  export MCP_CONFIG="${MCP_CONFIG:-$(pwd)/mcp_servers.json}"
  export LLM_CONTEXT_TOKENS=200000 ARTIFACT_DIR="$D/artifacts" DELIB_JOB_DIR="$D/delib-jobs" \
         DRAIN_STATE_PATH="$D/review-drain.json" SEAT_EVAL_DIR="$D/seat-eval" USAGE_TOKENS_DIR="$D/usage"
  mkdir -p "$ARTIFACT_DIR"
  nohup .venv/bin/uvicorn app:app --host 127.0.0.1 --port "$T" --timeout-graceful-shutdown 1 > "$D/agent.log" 2>&1 &
  echo $! > "$D/pid"
)
```

- LLM 주소 · 키 · 모델 · 출력 상한(`CARD_REVIEW_MAX_TOKENS` 등)은 운영 `.env` 그대로다 — 창만 다르다. 임시 서버의 사람별 LLM 토큰은 운영
  장부가 아니라 `$D/usage` 에 쌓인다.
- 확인 — 몇 초 뒤 둘 다 `200000 env` 다(`limits` 의 `features` 는 `['chunk', 'must_full']`).

  ```bash
  curl -s --noproxy '*' http://127.0.0.1:$T/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["context_tokens"], d["context"]["source"])'
  curl -s --noproxy '*' http://127.0.0.1:$T/card-review/limits | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["ctx_tokens"], d["ctx_source"], d["features"])'
  ```

- dev 에서 이 블록 그대로 띄워 확인했다(11-22 — 둘 다 `200000 env`, PID 로 내린 뒤 포트가 빈다). cae00 에서는 처음이다.

### 4-4. 포털 중계를 임시 서버로 · B 잡 · 되돌리기

```bash
cd ../HWAXPortal                          # 4-3 과 같은 셸 — T · D 가 그대로 있어야 한다
apptainer instance stop hwax_portal && APPTAINERENV_AGENT_SERVER_URL="http://127.0.0.1:$T" ./infra/scripts/start.sh
```

- apptainer 는 `--env` > `APPTAINERENV_*` > 호스트 환경 순이고(`infra/scripts/start.sh` 의 NO_PROXY 주석 — 실측 1.3.6), 포털 설정은 환경변수가
  `backend/.env` 를 이긴다(pydantic-settings). `start.sh` 는 `AGENT_SERVER_URL` 을 `--env` 로 넘기지 않으므로 이 한 줄이 컨테이너에 든다.
  `export` 하지 않는다 — 셸에 남으면 되돌릴 때도 실린다.
- 확인 — 포털을 거친 창이 임시 서버의 것이다(`feat:deliberation` 이 있는 사람의 포털 PAT — 명령줄에 싣지 않게 머리 파일로).

  ```bash
  H=$(mktemp); printf 'Authorization: Bearer %s\n' "$HWAX_GATEWAY_PAT" > "$H"     # mktemp 는 0600 이다
  curl -s --noproxy '*' -H @"$H" http://127.0.0.1:8723/agent/card-review/limits \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("ctx_tokens"), d.get("ctx_source"))'   # 200000 env
  ```

- B 잡 — 리스크 앱 쪽은 할 일이 없다. 앱이 창 · 판을 60초 동안 들고 있으므로(`review_runner.LIMITS_CACHE_S`) 확인 뒤 1분 넘게 지나 같은 대상 · 같은
  범위로 **새** 검토 잡을 만든다. scope 로 전문가 몇 명만 고른 잡이면 마감 범위가 닫히지 않아 쟁점 패널 · 영역 요약이 돌지 않는다
  (`../risk-review-redesign/server-setup-m3.md` 의 9명 파일럿과 같다). 쟁점 패널이 도는 범위면 그 패널도 임시 서버로 간다 — 견줄 것(4)은 셀 ·
  전문가 보고서까지라, 셀이 다 닫히면 되돌리기 전에 잡을 멈춘다(`risk_job_action(action='pause')` 또는 화면).
- 되돌리기 — B 의 셀이 다 닫힌 뒤. 운영 값이 돌아왔는지(4절 2 에서 적은 창 · 출처) 보고 임시 서버를 **그 PID 로만** 내린다(포트킬 금지 —
  docs/gotchas.md).

  ```bash
  apptainer instance stop hwax_portal && ./infra/scripts/start.sh            # APPTAINERENV_ 없이
  curl -s --noproxy '*' -H @"$H" http://127.0.0.1:8723/agent/card-review/limits \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("ctx_tokens"), d.get("ctx_source"))'   # 운영 값
  kill "$(cat "$D/pid")"
  ps -p "$(cat "$D/pid")" >/dev/null && echo "아직 산다 — 몇 초 뒤 다시 본다" || echo "내렸다"
  ss -ltn | grep ":$T " || echo "· :$T 비었다"
  rm -f "$H"
  ```

- `$D` 는 결과(4 · 5)를 적은 뒤 지운다 — 로그에 대상 정보가 남는다.

## 5. dev 에서 미리 본 것

- 엔진 시험 2,543 · 리스크 앱 시험 · 포털 중계 재생(계약 예제 — 조각 · 쪽 장면 포함)이 통과했다.
- dev 표본 32명(카드 5,711장)을 20만으로 계획 — `oversize.cards` 0, 조각 카드 143장 → 조각 360개, 조각마다 실행 준비가 창 안이다.
- 배선 리허설 `HWAXRisk/backend/tests/synth/rehearsal_d.py run <스크래치> --ctx 200000 --long-cards` — 리스크 앱 → 포털 → 엔진 →
  가짜 LLM 을 실제 프로세스로 띄워 끝까지 돌렸다(10-21, 9/9 — 재기동 셋 · 취소 포함). 조각 판정 25 · 조각 훑기 3 · 쪽 카드 밖 5,
  `[누락 0 증명] 닫힌 칸 25 · 카드 × 칸 265 = 판정 105 + 카드 밖·입력 결손 전문 65 + 훑기 전문 대조만 95 + 놓침 0`. 이 모드는 근거 꾸러미
  실호출을 끈다(하네스의 게이트웨이 싱크가 물성 도구를 503 으로 받아 그 단위가 31분 백오프한다 — 운영과 무관).
- 단위 쪽(W-D22, 11-24) — 엔진 시험 17(멈춤 0 · 카드 누락 0 · 줄 누락 0 · 전문 노출 교집합 · 드는 단위는 그대로 · 쪽 실패는 그 오류) · 변이 12/12 ·
  엔진 전체 5,051 · 계약 예제(plan · verdict · noinput `unit_paged`)를 리스크 앱 회계(참조가 Q8 을 지난다)와 포털 중계 재생(77)이 받는다. 배선
  리허설 `rehearsal_d.py run <스크래치> --ctx 200000 --long-cards --giant-unit`(본 대상 첫 단위의 얼린 근거에 18만 자 줄) — 점검 9 통과: 그 단위의
  판정 쪽 10 · 카드 밖 쪽 5 · 칸 5개 다 검토함 · 놓침 0 · 불변식 빔 · 잡 completed(보류 없음) · 에이전트 서버 로그 '단위 쪽' 21줄, 점검 8 과
  재기동 셋 · 취소도 통과(9/10 — 남은 하나 `live_stores_untouched` 는 새 워크트리에 gitignore 파일 `backend/secrets/conn.key` 가 없어 하네스가
  띄운 포털이 지은 것이다. 하네스가 그 경로를 스크래치로 돌리지 않는 빈틈이고 단위 쪽과 무관하다). dev 원장에는 단위를 세운 대상이 없어 운영 단위
  크기는 6절로 잰다.

## 6. 운영 단위 크기 분포 재기 (W0 · W-D23 — 사람 몫)

목적 — 검토 단위가 창의 '단위 몫'(`unit_body_max`) · '단위 홀로 자리'(단위 쪽 문턱)를 얼마나 넘는지 재서 W-D22 손잡이를 정하고, 쪽이 흔하면 4절
A/B 에 그 단위가 든 대상을 고른다. **읽기만 한다** — 원장을 읽기 전용(`mode=ro`)으로 열고, 서비스를 띄우거나 내리지 않는다. 결과에는 대상 키 ·
단위 id · 글자 수만 있다(부품 이름 · 줄 글이 없다).

1. 리스크 앱 리포가 이 스크립트(`backend/scripts/unit_window_census.py`)를 가진 판이고 에이전트 서버가 W-D22 판인지 — update-all 뒤면 둘 다다.
   스크립트가 엔진을 들여 판을 보고, 낡았으면 `[잴 수 없음] 엔진이 이 측정보다 낡았다` 로 멈춘다(종료 2).
2. 리스크 앱 리포 루트에서 한 줄(에이전트 서버 venv 의 python — 앱의 단위 모듈도 그 venv 로 들어온다. 앱 설정이 들일 때 만드는 데이터 디렉터리는
   스크립트가 빈 임시 디렉터리로 돌린다).

   ```bash
   cd ../HWAXRisk                            # 포털 리포 루트에서
   ../HWAXAgentServer/.venv/bin/python backend/scripts/unit_window_census.py \
     --db ${HWAX_DATA_ROOT:-/data}/appdata/hwax_risk/risk_review.db --out /tmp/unit-census.json
   ```

   - 끝줄 `[잼] 단위 N개(대상 a/b) — 1M 쪽 0 · 200k 쪽 x · 200k-32k 쪽 y` 가 요약이다. 창 셋은 1M · 20만(출력 미설정 — 프롬프트 한도 179,676자) ·
     20만 출력 32K 다. 박스가 `CARD_REVIEW_MAX_TOKENS` 를 적었으면 그 창을 하나 더 준다 — `--windows` 는 기본 셋을 갈아 끼우므로 셋을 다 적는다
     (예 `--windows 1M=1048576:0,200k=200000:0,200k-32k=200000:32000,box=200000:<그 값>`).
   - 원장 자리가 다르면 `--db` 를 바꾼다(HEAX 데이터 디렉터리의 `hwax_risk/risk_review.db`).
3. 볼 것(JSON) — `by_window.<창>` 의 `within`(몫 안) · `soft_over`(몫 넘음 — 카드를 단위에 맞게 조각 낸다) · `paged`(쪽 — 종전에는 멈춤) ·
   `head_risk`(머리가 쪽 자리 바닥에 안 든다 — 0 이어야 한다) · `pages_min` · `pages_max`(쪽 수 어림의 합), 그리고 `sizes` · `head` · `line_max` ·
   `top`. `targets.skipped` 는 단위를 세우지 않은 대상 따위다(까닭이 적혀 있다).
4. 결과는 이 폴더의 context-notes 에 W-D 로 적는다(수 · 날짜 — 대상 키는 적지 않아도 된다). `paged` 가 0 이면 손잡이는 기본 그대로다.
   `head_risk` 가 0 이 아니면 그 단위의 머리(요약 · 읽는 법)가 왜 긴지 본다. `/tmp/unit-census.json` 은 적은 뒤 지운다.
