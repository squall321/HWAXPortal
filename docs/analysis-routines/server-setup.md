# 분석 루틴 — cae00 에서 사람이 할 일 · 확인(R1 ~ R3, 10-30)

계획 [PLAN.md](PLAN.md) · 계약 [contracts.md](contracts.md) · R3 정본 [R3-design.md](R3-design.md) · 판단 [context-notes.md](context-notes.md).
**값(토큰 · 비밀)은 화면 · 로그 · 채팅에 붙이지 않는다.** 명령은 리포 루트 기준이다(cae00 은 `~/Projects/<리포>`).

## 0. 무엇이 들어오나

| 리포 | 무엇 | 반영 길 |
|---|---|---|
| HWAXPortal | `/routines-api`(짜기 · 실행 원장 · 보고서 렌더 · 이어서 · 보고서 다시 읽기) · 챗 중계의 루틴 턴(긴 idle · 브라우저가 떠나도 끝까지 읽기 · `meta.routine`) · 화면(절차 › 루틴 탭 · 챗 입력창의 '루틴' 알약 · 메시지 안 실행 보기) | update-all — 코드는 git, 화면은 Drive 의 SPA |
| HWAXMcpGateway | 루틴 도구 여섯 · 쓰기 분류(`/tools-map` 의 `write`) · MCP prompts `routine-<id>` · 지침 12번 | update-all — 게이트웨이 재기동 |
| HWAXAgentServer | 실행기 `routine.py` · `/chat` 의 루틴 가지 · `/health` 의 `routine_active` · `routine_max` | update-all — 에이전트 서버 재기동(도는 심의 · 루틴이 있으면 기다린다) |

새 sqlite 표 다섯(`routines` · `routine_versions` · `routine_runs` · `routine_stages` · `routine_calls`)은 기존 `procedures.sqlite` 안에 저절로 생긴다(칸 둘
`routine_runs.report_json` · `routine_runs.note` 도 없으면 붙인다 — 손댈 것 없음).

## 1. 권한 — 누가 쓰나

권한 키는 `feat:routines` 다(`backend/config/access.yaml` 의 기능 `routines`). 기본 부여(`default_grants`)는 `feat:chat` 뿐이라 **아무도 저절로 받지 않는다**(CAEG 는 전부).
주는 길은 다른 기능과 같다 — 소속째면 박스 권한표 `backend/config/access.local.yaml` 의 그 소속 `grants` 에 `feat:routines`, 사람마다면 포털 '내 권한' 요청을
관리자가 승인(사용자 개별 허가). 유효 권한 = 기본 ∪ 소속 ∪ 개별이다. 받은 사람만 절차 › 루틴 탭 · 챗의 '루틴' 알약 · 게이트웨이 루틴 도구가 열린다.

## 2. update-all 뒤 확인

| 확인 | 명령 | 기대값 |
|---|---|---|
| 포털 창구 | `curl -s http://127.0.0.1:8723/routines-api/health` | `{"ok": true, "contract": 1}` |
| 게이트웨이 읽기 분류 | `curl -s http://127.0.0.1:9110/tools-map \| python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d.get("routine_read",[])))'` | 0 보다 큰 수(옛 게이트웨이면 칸이 없어 0 — 그때 포털 계획은 옛 규칙으로 돈다) |
| 에이전트 서버 | `curl -s http://127.0.0.1:9009/health \| python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("routine_active"), d.get("routine_parked"), d.get("routine_max"))'` | `0 0 2`(도는 루틴 · 심의 멈춤 · 줄을 기다리며 쉬는 루틴 · 동시 상한) |
| 화면 | 루틴 권한이 있는 계정으로 챗 → 입력창 도구 줄의 '루틴' | 내 루틴 목록이 뜬다(없으면 절차 › 루틴에서 짜거나 예시를 가져온다) |

## 3. 손잡이(에이전트 서버 환경 — 기본값이면 안 적는다)

| 이름 | 기본 | 뜻 |
|---|---|---|
| `ROUTINE_MAX_RUNNING` | 2 | 동시에 도는 루틴 수. 넘으면 새 시작을 거절한다(줄 없음 — 'routine_busy', 1분 뒤 다시). stcx Qwen 을 챗과 나눠 쓰므로 낮게 둔다 |
| `ROUTINE_LLM` | `chat` | `chat` 이면 챗 LLM(stcx Qwen), `glm` 이면 심의 LLM |
| `ROUTINE_DELIB_POLL_S` | 20 | 심의 단계가 심의 상태를 보는 간격(초) |
| `ROUTINE_RESULT_CHARS` | 0(창에서 정함) | 도구 결과를 단계 모델에 보이는 글자 상한 |
| `ROUTINE_HISTORY_FRAMES` | 400 | 다시 붙을 때 되보내는 프레임 수 |

## 4. 운영 중 알아 둘 것

- **update-all 은 도는 루틴을 기다린다** — 루틴이 `/health` 의 `delib_active` 에 더해져 심의와 같은 기다림(`HWAX_DELIB_WAIT_S`, 기본 600초)을 탄다. 심의 멈춤이 풀리길 ·
  줄 선 심의가 시작되길 기다리는 루틴은 '쉼'(`routine_parked`)이라 세지 않는다 — 그래야 update-all 이 새 심의를 멈추고 기다리는 동안 그 루틴 때문에 끝나지 않는 일이 없다. 기다려도 안 끝나면
  에이전트 서버 재기동을 미룬다(○ 로 알린다). 실행기가 사라지면 — 억지 재기동(`AGENT_RESTART_FORCE=1`) · 강제 종료 · 쉬던 루틴을 둔 채 재기동 — 루틴은 원장에 running 으로 남고, 사람이 화면에서 '이어서' 로
  끝난 단계를 건너뛰고 잇는다('멈춤' 은 그 실행이 시작한 심의도 접는다).
- **심의 멈춤(`/drain scope=delib`) 중엔 새 루틴 · 이어서를 거절**한다(도는 루틴을 지켜보는 다시 붙기는 된다).
- **루틴은 실행하는 사람의 이름으로 돈다** — 서비스 계정으로 떨어지지 않는다. RA · FMEA · TestScope 토큰이 없는 사람의 그 단계는 '토큰 없음' 으로 건너뛰고 보고서
  커버리지에 적힌다. RA 초안도 그 사람 토큰이 없으면 건너뛰고 까닭을 적는다.
- **단계 안에서는 읽기로 확인된 도구만 부른다** — 게이트웨이 `/tools-map` 의 `routine_read`(readOnlyHint true · 읽기 목록 · 읽기 낱말이 있고 쓰기 동사가 없는 이름)만
  계획에 들고 게이트웨이 울타리도 그것만 통과시킨다. 모르는 이름은 막힌다(쓰기일 수 있어서 — 반대 검토 C-12). 심의 단계의 심의 도구 셋만 예외다.
  **읽기 도구인데 막히면** — 도구를 적은 단계는 준비도 까닭 · 계획의 `dropped_write` 에 나오지만, 도구를 비운 단계는 막힌 도구를 **조용히 묶지 않는다**(그때는
  `/tools-map` 의 `routine_read` 에 그 노출 이름이 있는지로 본다). 그 앱이 도구에 `readOnlyHint: true` 를 달거나, 지금 바로는 게이트웨이 리포의
  `read_tools.local.json`(gitignore, `{"tools": ["<백엔드>:<원래 이름>", …]}`)에 더한다. 파일의 바뀐 시각을 보고 재기동 없이 읽는다. ⚠ 새 판을 받은 **뒤에**
  만든다(update-all §1 stash 는 옛 .gitignore 로 돈다 — 받기 전에 만들면 stash 에 쓸려 간다). 확인은
  `curl -s http://127.0.0.1:9110/tools-map | python3 -c 'import json,sys;d=json.load(sys.stdin);print("<노출 이름>" in d.get("routine_read",[]))'`.
- 개인 Claude(Claude Code · Desktop)는 MCP prompts 로 루틴을 한 번에 시작한다 — `/mcp__hwax__routine-<루틴 id>`.

## 5. R5 받아들이기(사람 — 예시 연쇄 한 번)

0. **먼저 기준 키 도구를 읽기로 연다** — 'resolve' 는 동사로도 읽혀(`resolve_thread` 는 RA 토론을 닫는다) 이름 규칙에서 뺐다. 코어 허브(StandardPlatform)의
   `object_resolve`(GET) · `objects_resolve_many`(읽기 전용 POST)는 읽기인데(소스 — StepForge 리포에 실린 StandardPlatform 사본) 이 박스의 백엔드 키를 몰라 읽기 목록에
   넣지 않았다. cae00 의 **코어 허브 백엔드 키마다**(`rootdesigndatahub` · `failuretrace` · `caegroupdatahub` … — `/tools-map` 의 `apps` 로 확인) 둘을 게이트웨이 리포의
   `read_tools.local.json` 의 `tools` 에 더한다(예 `"rootdesigndatahub:object_resolve"` · `"rootdesigndatahub:objects_resolve_many"`). 외부 연결 MatNexus 의
   `resolve_property` 는 그 연결 블록(`access.local.yaml` 의 `connect:`)의 `read_tools` 나 같은 파일에 더한다. 그 밖에 예시 연쇄의 도구 가운데 `routine_read` 에 없는 것도
   같은 길이다(`curl -s http://127.0.0.1:9110/tools-map` 의 `routine_read` 와 견준다). 안 열면 기준 키 단계가 막혀 루틴이 시작부터 멈춘다(그 단계는 '멈춤' 으로 짠다).

1. 절차 › 루틴 › YAML 가져오기로 `docs/analysis-routines/examples/market-defect.yaml` 을 들인다(또는 그 꼴로 짠다).
2. 챗 입력창의 '루틴' → 그 루틴 → 모델 · 증상 입력 → 켜기 → 보낸다.
3. 본다 — 단계 칩이 차례로 바뀌는가 · 막힌 단계(권한 · 토큰 · 이 박스에 없음)가 까닭과 함께 건너뛰어지는가 · 기준 키 후보가 여럿이면 고르기가 뜨는가 · 보고서에 커버리지와 근거 부록이
   있는가 · RA 초안이 그 사람 이름으로 생겼는가.
4. 잰다 — 단계별 호출 수 · 시간(`GET /routines-api/runs/{id}`) · 토큰(호출 추적) · 커버리지를 10-29 기준선(질문당 108,275 토큰 · 50 ~ 105초)과 견준다 — 결과는
   `docs/analysis-routines/checklist.md` R5 에 적는다.
5. 탭을 닫았다 다시 열어 같은 대화를 본다 — 실행 보기가 원장에서 단계를 다시 그리고, 끝났으면 보고서가 대화에 남아 있어야 한다.
