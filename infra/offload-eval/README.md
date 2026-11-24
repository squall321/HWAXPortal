# 토큰 절감 2판 비교 테스트셋

「GLM · Qwen 에 맡기는 비중을 만들어도 품질 차이 없이 속도나 토큰량이 나아지는가」 를 잰다(사용자 요청 2026-11-24). 같은 과제를 두 갈래로 Claude Code 를
사람 없이(`claude -p`) 돌려 Claude 토큰 · 비용 · 시간 · 도구 호출 수 · 답을 모으고, 눈가림 판정과 사람 표본으로 품질을 본다.

| 갈래 | 무엇 |
|---|---|
| baseline | 지금처럼 — 2판 도구 여덟은 문맥에서 뺀다 |
| offload | 2판을 쓴다 — 연결 머리 `X-HWAX-Result: ref` · 2판 도구 여덟(`delegate_start` · `delegate_status` · `delegate_result` · `delegate_cancel` · `draft_section` · `llm_transform` · `result_get` · `result_ask`) · 시스템 프롬프트에 PC 킷 E 와 같은 규칙 묶음(포털 `frontend/src/lib/setupBat.ts` 의 `OFFLOAD_RULES` 를 실행 때 그대로 읽는다) |

과제 16(네 갈래 넷씩 — R 큰 결과 읽기 · M 다단계 조사 · W 긴 글 · T 변환, `tasks.yaml`) × 반복 2 × 두 갈래 = 실행 64, 판정 32. 계약은
[`docs/token-saving/offload-v2.md`](../../docs/token-saving/offload-v2.md), 계획은 [`eval-plan.md`](../../docs/token-saving/eval-plan.md), 결정은 `context-notes.md` TS-14.

## 1. cae00 에서 사람이 할 차례

리포 루트에서 돈다(경로는 이 파일 자리에서 유도한다 — 박스마다 리포 경로가 다르다).

1. **준비** — `node --version`(18 이상 — 포털 프론트를 짓는 node 가 있다) · `claude --version`(Opus 5.5 를 아는 판, 낡았으면 `claude update`). 로그인은 사람이
   `claude` 를 한 번 열어 `/status` 로 계정을 확인한다(이 실행기는 로그인을 하지 않는다). 리포는 update-all 로 최신.
2. **2판 스위치 켜기**(계약 §2 · §4) — 에이전트 서버 `.env` 에 `DELEGATE_ENABLED=1` · `DRAFT_ENABLED=1` · `TRANSFORM_ENABLED=1` · `RESULT_ASK_ENABLED=1`, 도는 심의가 없을
   때 `cd ../HWAXAgentServer && ./start.sh -d`. 게이트웨이 `provision.env` 에 `GATEWAY_RESULT_REFS=1` 을 적고 게이트웨이를 다시 띄운다(update-all §4 가 지문으로
   다시 띄운다 — TS-9). baseline 은 스위치가 켜져 있어도 2판 도구를 문맥에서 빼므로 같은 박스 상태로 두 갈래를 섞어 돌린다.
3. **PAT** — 포털 토큰 화면에서 받은 **일반 PAT**(읽기 전용 PAT 는 2판 도구를 못 부른다 — TS-8). 화면 · 셸 이력에 남지 않게 넣는다.

   ```bash
   read -rs HWAX_GATEWAY_PAT && export HWAX_GATEWAY_PAT
   ```

4. **사전 점검(돈 안 듦)** — `node infra/offload-eval/run-eval.mjs check`. `claude --help` 의 플래그 · PAT(게이트웨이 initialize) · `/tools-map` · 두 `/health` 의 2판
   표지 · 사용자 `CLAUDE.md` 오염을 보고 `✓ 돌릴 준비가 됐다` 가 뜰 때까지 고친다. 허용 목록 전부가 `~/hwax-offload-eval/allowlist.json` 에 남는다 — 돌리기 전에 본다.
5. **연기 시험(작은 비용)** — 과제 하나 · 두 갈래 한 번씩.

   ```bash
   node infra/offload-eval/run-eval.mjs run --only T4 --reps 1 --out ~/hwax-offload-eval-smoke --max-budget-usd 5
   ```

   출력의 ⚠ · ✗ 줄과 `runs/*.json` 의 `init.tools_n` · `fence` 를 본다. 두 실행 비용의 합 × 32 가 본 실행의 어림이다.
6. **본 실행** — `node infra/offload-eval/run-eval.mjs run --max-budget-usd 5`(기본 — 모델 `claude-opus-5-5` · 반복 2 · 동시 1 · 결과 `~/hwax-offload-eval`).
   끊기면 같은 명령으로 이어 간다(끝난 실행은 건너뛰고 기반 오류만 다시). 울타리 위반이면 끝 코드 3 으로 멈춘다 — 기록을 사람이 본다.
7. **판정** — `node infra/offload-eval/run-eval.mjs judge`(판정 모델 기본 `claude-sonnet-5-5`, 꼴이 틀리면 한 번 다시).
8. **사람 표본** — `node infra/offload-eval/run-eval.mjs human` → `~/hwax-offload-eval/human-review.md` 의 4쌍마다 「판정」 줄에 A · B · 무를 적는다.
   어느 답이 어느 갈래인지는 `human-key.json` 에 따로 있다 — 다 적기 전에는 열지 않는다.
9. **보고서** — `node infra/offload-eval/run-eval.mjs report` → `report.md` · `summary.json`.
10. **돌려받을 것** — `report.md` · `summary.json` · 적은 `human-review.md` · `allowlist.json`. ⚠ 답에 사내 과제 내용이 들어 있다 — 이 리포(공개)나 받은 편지함에
    올리지 않고 사용자에게 직접 준다. `runs/` 의 사건 줄은 원본이라 박스에 둔다.
11. **끝나면** — `unset HWAX_GATEWAY_PAT`. 2판 스위치를 그대로 둘지는 결과를 보고 사람이 정한다(끄면 2 의 자리에서 지우고 같은 재기동).

## 2. 손잡이

| 손잡이 | 기본 | 뜻 |
|---|---|---|
| `--out` | `~/hwax-offload-eval` | 결과 폴더(0700). 모델이 다르면 다른 폴더를 쓴다(섞이지 않게 막는다) |
| `--model` · `--judge-model` | `claude-opus-5-5` · `claude-sonnet-5-5` | 실험 대상 · 판정 모델(사용자 결정 11-24) |
| `--reps` · `--only R1,T4` · `--arms baseline,offload` | 2 · 전부 · 둘 다 | 반복 · 과제 고르기 · 갈래 고르기 |
| `--concurrency` | 1 | 동시 실행. 위임은 사람마다 1건이라(계약 §3-1) 2 이상이면 offload 의 위임이 줄을 서 시간이 흐려진다 |
| `--timeout-min` · `--judge-timeout-min` | 30 · 10 | 실행 하나 · 판정 하나의 상한(넘으면 SIGINT → SIGTERM) |
| `--max-budget-usd` | 없음 | 실행 하나의 Claude Code 비용 상한(그대로 넘긴다) |
| `--seed` | 처음 실행 때 무작위 · `plan.json` 에 남김 | 섞인 차례 · A/B · 사람 표본 |
| `--no-spill-read` | 켬(결과 파일 Read 허용) | 4-3 을 본다 |
| `--tool-search off` | on | MCP 도구 검색을 끄고 도구를 처음부터 다 싣는다(낡은 판 대비 — 허용 도구가 수백이면 문맥이 크다) |
| `--gateway` · `--mcp-url` · `--agent` | `http://127.0.0.1:9110` · 그 `/mcp` · `http://127.0.0.1:9009` | 박스 안 주소(`/tools-map` · `/health` 는 무인증 · 박스 안에서만) |
| `--max-loss-rate` · `--max-mismatch-increase` | 0.10 · 0 | 판정 기준(5) |
| `--pairs` · `--force` | 4 · 끔 | 사람 표본 수 · 적어 둔 `human-review.md` 를 새로 만들기 |

모르는 손잡이는 멈춘다(오타로 기본값이 도는 것을 막는다).

## 3. 비용 · 시간 어림

- **비용** — 토큰 단가는 짐작하지 않는다. 연기 시험(1-5)의 두 실행 비용 합 × 32 가 본 실행 64 의 어림이고, 실제는 끝난 뒤 보고서의 `total_cost_usd` 합으로 본다
  (Claude Code 의 클라이언트 어림 — 청구와 다를 수 있다). 판정 32 의 비용은 보고서 「판정」 줄에 따로 나온다. `--max-budget-usd` 로 실행 하나를 막는다.
- **시간** — 실행 하나가 도구 호출 · 위임 기다림에 따라 몇 분에서 수십 분이다. 동시 1 로 64 실행이면 반나절 남짓을 잡고, 판정은 하나에 1분 안팎이다. 실제 수는
  보고서의 시간 합으로 본다. 끊어도 이어 가므로 나눠 돌려도 된다(섞인 차례라 어느 때 멈춰도 두 갈래가 고르게 쌓인다).

## 4. 안전 설계 — 사람 없이 도는 Claude 가 쓰기 도구를 부르지 않게

1. **허용 목록** — 게이트웨이 `/tools-map` 의 `routine_read`(루틴 울타리와 같은 '읽기로 확인된' 노출 이름 — 앱 표지 · 읽기 목록 · 조회 낱말, 모르면 막는 쪽) ∩ 노출
   ∪ 게이트웨이 로컬 조회 도구(게이트웨이 `_LOCAL_READ` 그대로 + `figure_get` · `figure_list`, `/tools-map` 이 `_gateway` 로 귀속한 이름만). `invoke_tool`(안쪽
   이름으로 아무 도구나) · `rest_call`(아무 REST 나)은 두 갈래 모두 넣지 않는다. offload 만 2판 도구 여덟을 더한다 — `routine_read` 가 이름 낱말로 `delegate_status`
   를 읽기로 봐도 baseline 에서는 뺀다. `routine_read` 이면서 `write` 에도 드는 도구(dev 11-24 기준 6개 — 게이트웨이 `read_tools.json` 이 이름으로 읽기로 확인한 것)는
   `check` 가 말해 준다.
2. **deny 의 맨 이름** — 허용 밖의 노출 도구 · `invoke_tool` · `rest_call` · (baseline) 2판 여덟 · 내장 도구를 `mcp__hwax__<이름>` · `Bash` 처럼 맨 이름으로 deny 에
   둔다. 공식 문서 — 「A bare tool name like `Bash` removes the tool from Claude's context entirely, so Claude never sees it」 · deny 는 allow 보다 먼저 본다.
3. **결과 파일 Read** — Claude Code 는 50,000자가 넘는 MCP 결과를 파일로 빼 두고 「Claude reads the file when it needs the content」(공식 문서 MCP output limits).
   Read 를 통째로 막으면 baseline 이 큰 결과를 못 읽어 offload 쪽으로 기운 결과가 나온다. 그래서 내장 도구는 `--tools ToolSearch,Read` 만 두고, Read 는 그 자리
   `Read(//<설정 폴더>/projects/**/tool-results/**)` 만 허용한다(dontAsk 라 다른 자리는 거절). 요청은 「Read 도 막는다」 였으므로 **사용자 확인이 필요하다** —
   `--no-spill-read` 면 Read 도 deny 로 간다. 실행 뒤 Read 가 그 자리 밖을 읽었으면 울타리 위반으로 멈춘다.
4. **ToolSearch** — 공식 문서 「If you deny `ToolSearch` or leave it out of `--tools`, MCP tools load upfront instead」. 허용 도구가 수백(dev 11-24 기준 457)이라 처음부터 다
   실으면 문맥이 크다 — PC 의 기본(도구 검색 켬)과 같게 둔다. `--tool-search off` 면 빼고 `ENABLE_TOOL_SEARCH=false`.
5. **권한 모드 dontAsk** — 공식 문서 「Auto-denies every call that would otherwise prompt」 — 묻지 않고 거절하며, `permissions.allow` 로 미리 허용한 도구만 돈다.
   거절은 마지막 `result` 의 `permission_denials` 에 남고 보고서가 「막힌 호출」 로 센다. 같은 값을 설정 `defaultMode` 에도 둔다.
6. **설정 원천** — `--setting-sources local` + 리포 밖 빈 작업 폴더(`$TMPDIR/hwax-offload-eval-cwd`) — 사용자 · 프로젝트 설정(허용 규칙 · 훅)을 싣지 않는다.
   `--settings` 의 목록은 다른 설정과 합쳐지므로(공식 문서 「most lists merge」) 이것이 필요하다. 훅은 `disableAllHooks: true`, claude.ai 커넥터는
   `disableClaudeAiConnectors: true` + `ENABLE_CLAUDEAI_MCP_SERVERS=false`, MCP 는 `--strict-mcp-config` 로 이 실행기가 준 `hwax` 하나만.
   `--bare` 는 쓰지 않는다 — 문서 「In bare mode, Claude Code never reads OAuth credentials」(사람이 로그인한 박스에서 안 돈다). `--restricted` 도 쓰지 않는다 —
   「confines the built-in file tools to the working directories」 라 3 의 결과 파일 Read 를 막고, v2.1.248 아래에는 없다.
7. **울타리 대조** — 실행마다 `system/init` 의 `tools` 에 막을 도구(`invoke_tool` · `rest_call` · baseline 의 2판 · 위험한 내장)가 보이거나, 허용 밖 도구가 거절되지 않고
   돌았으면 위반이다 — 남은 실행을 멈추고 끝 코드 3. 허용 밖 노출 도구가 목록에만 보이면 경고(dontAsk 가 거절한다).
8. **PAT** — `HWAX_GATEWAY_PAT` 로만 받는다. 실행마다 0700 임시 폴더의 0600 `--mcp-config` 파일 머리에만 쓰고 끝나면(멈춰도) 지운다. 자식 `claude` 의 환경에서는
   뺀다. 남는 산출물(사건 줄 · stderr · 기록)은 PAT 글자를 `***` 로 바꾼다. `--mcp-config` 의 `${VAR}` 펼치기는 문서가 `.mcp.json` 에 대해서만 말해 기대지 않았다.
   사용자 `CLAUDE.md` 에 2판 규칙 표지(`hwax-offload:begin`)가 있으면 baseline 이 오염되므로 `check` 가 멈춘다.

### 확인한 Claude Code 플래그와 근거(2026-11-24)

이 박스(dev)의 `claude --help`(2.0.74)와 공식 문서(code.claude.com/docs — cli-reference · permissions · headless · mcp · agent-sdk/typescript)를 맞댔다.
실행기는 `check` · `run` 때 그 박스의 `claude --help` 에 아래가 다 있는지 보고, 없으면 멈춘다(짐작하지 않는다).

| 쓰는 것 | 근거 |
|---|---|
| `-p "<과제>"` · `--model` | headless — `claude -p "query"`. 프롬프트는 `-p` 바로 뒤에 둔다(`--tools` · `--mcp-config` 는 값을 여럿 받는다) |
| `--output-format stream-json --verbose` | 줄마다 JSON 사건, 「The last line of the stream is a `result` message」. `result` 에 `duration_ms` · `num_turns` · `total_cost_usd` · `usage` · `modelUsage` · `permission_denials`(SDKResultMessage), `system/init` 에 `tools` · `mcp_servers`(SDKSystemMessage), 도구 호출은 `assistant` 의 `tool_use` 블록 · 결과는 `user` 의 `tool_result` 블록 |
| `--mcp-config <파일> --strict-mcp-config` | 「Skip the MCP servers configured in places such as `.mcp.json`, `~/.claude.json`, or a plugin, and load the ones you pass with `--mcp-config`」. 서버 이름 `hwax` → 도구 `mcp__hwax__<이름>` |
| `--settings <파일>` · `--setting-sources local` | 6 |
| `--permission-mode dontAsk` | 5 |
| `--tools "ToolSearch,Read"` | 「Use `""` to disable all … The flag doesn't affect MCP tools」 · 4 |
| `--append-system-prompt` | offload 의 규칙 묶음 — 「Append custom text to the end of the default system prompt」 |
| `--no-session-persistence` | 세션을 디스크에 남기지 않는다(print 모드) |
| `--output-format json`(판정) | 한 번에 `result` 하나 — 판정 모델의 답은 `result`, 비용은 `total_cost_usd` |

## 5. 결과 해석

- **판정 기준(제안 — 사람이 바꾼다)** — 「품질 차이 없음 = 판정 패배율 ≤ 10% 이고 숫자 대조 어긋남이 늘지 않음」. 패배율 = baseline 이 이긴 짝 / 판정한 짝.
  어긋남은 baseline 은 Claude 답의 출처 없는 수, offload 는 그것 + 서버가 표시한 `numbers.mismatched`(서버 답을 Claude 가 옮기면 Claude 쪽 대조로는 안 잡혀서).
  `--max-loss-rate` · `--max-mismatch-increase` 로 바꾼다.
- **숫자 대조** — 답의 수(소수점이 있거나 100 이상 — 에이전트 서버 `evidence.sig_numbers` 와 같은 판정)가 그 실행이 본 도구 결과 · 과제 글에 있는지.
- **합계 · 개선율** — 두 갈래가 다 끝난 짝만 센다. 「줄인 몫」 이 음수면 offload 가 더 썼다(예 도구 호출 수는 위임 기다림 때문에 늘 수 있다).
- **서버 LLM** — Claude 밖에서 쓴 것을 숨기지 않는다. 위임 잡의 토큰은 `delegate_result` 의 `tokens`(잡마다 한 번)이고, `draft_section` · `llm_transform` ·
  `result_ask` 는 결과에 tokens 칸이 없어 호출 수만 센다 — 서버 총량은 관리 › 이용 통계의 그 사람 LLM 사용량(종류 other, 평가한 날)으로 함께 본다.
- **꼴 검사** — `tasks.yaml` 의 `expect`(표 행 수 · 줄 수 · 글자 수 · 들어야 할 낱말 · 영어 비율). 데이터가 없는 과제는 두 갈래가 함께 「없다」 로 답할 수 있다.
- **사람 표본** — 판정 모델과의 일치 수. 4쌍 가운데 어긋나는 것이 많으면 판정 결과를 덜 믿는다.

## 6. 한계

- 판정 모델은 도구로 사실을 확인하지 못한다 — 정확성은 답 안의 일관성과 코드 숫자 대조로 본다.
- 눈가림은 갈래 이름을 빼고 답 안의 2판 도구 이름 · 결과 손잡이를 같은 표지로 바꾸는 데까지다. 글투로 갈래가 비칠 수는 있다.
- 두 갈래는 같은 게이트웨이 · 같은 사람으로 섞어 돈다. 게이트웨이 응답 캐시 · 서버 부하가 차례에 따라 다를 수 있어 섞인 차례로 고르게 나눈다.
- 실제 PC 의 개인 보기(`X-HWAX-View`)와 달리 두 갈래 모두 `full` 로 붙는다(리포 `.mcp.json` 과 같다). PC 킷의 `/hwax-ask` · `/hwax-draft` 명령은 깔지 않는다 — 과제는
  명령이 아니라 글로 준다.
