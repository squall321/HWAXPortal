# 서버(cae00)에서 할 일 — 리스크 심사 M1(패널 수리·1백만 토큰·Claude 입구)

> 대상: cae00 운영자 · **대조 시점 2026-10-11** · 보낸 쪽: dev(이 리포 `docs/risk-review-redesign/`).
> 반영되는 리포와 push 된 커밋(2026-10-11) — HWAXRisk `6d6650a`(리스크 앱 SIF, Drive 에도 올림) · HWAXAgentServer `7644284` · HWAXMcpGateway `9dc6c01` · AIDataHub `b401f88` · HEAXHub `d65990c`(등록 사본) · HWAXPortal 은 이 문서를 담은 커밋(프론트 dist 는 Drive 에도 올림). 이보다 새 커밋이 있어도 update-all 이 함께 받는다.
> dev 에서는 같은 커밋으로 다섯 구성 요소를 다시 띄워 §3 의 ①③④⑤ 를 확인했다(② 는 dev 창이 16K 라 2,000 이 맞다).
> 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.
> 이 박스의 지금 상태는 이 문서가 알지 못한다. 그래서 확인마다 재는 명령을 적었다.

## 0. 한눈에

이번 묶음은 평소처럼 `./infra/scripts/update-all.sh` 한 번으로 들어온다. 사람이 할 일은 돌리기 전 확인 셋과 돌린 뒤 확인 다섯이다.

달라지는 것.
- **리스크 앱 패널이 끝까지 돈다.** 같은 과제의 두 번째 패널부터 저장이 실패하던 것, 저장이 터지면 결과를 잃던 것(이제 먼저 남기고 '다시 저장' 한다), 부품 이름의 낱말 때문에 브리프가 죽던 것을 고쳤다.
- **리스크 앱 DB 가 스키마 v3 로 오른다.** 새 SIF 가 처음 뜰 때 스스로 올리고 직전 사본을 남긴다. 옛 SIF 는 v3 DB 를 열지 못한다(§4).
- **글자를 자르지 않는다.** 엔진·포털·게이트웨이·AIDataHub 의 상한을 GLM-5.2 의 1백만 토큰 창에서 유도한다. `.env` 에 적어 둔 옛 상한이 있으면 그 값이 천장으로 걸린다(§1 확인 2).
- **Claude 에서 과제를 올리고 리스크 심사를 시작할 수 있다.** 리스크 앱 도구가 14종에서 25종이 된다(`risk_next_step` 부터). 쓰기 도구는 게이트웨이가 확인한 **본인 신원으로만** 쓴다. 리스크 앱 MCP 를 개인 토큰으로 **직접 등록한 길은 읽기 전용**이 된다.

## 1. 돌리기 전 확인

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | 도는 심의·리스크 잡이 없다 | `./infra/scripts/risk-review-inventory.sh` | `health:` 줄의 `delib_active`·`delib_queued` 가 0, `잡 상태별` 에 `running` 이 없다. 있으면 끝난 뒤 돌린다 — 돌아도 update-all 이 재기동을 미루지만(`○ … 재기동 건너뜀`) 그 실행은 반영이 덜 된 것이다 |
| 2 | 에이전트 서버 `.env` 에 옛 상한이 적혀 있지 않다 | 아래 명령 | 아무 줄도 안 나오면 된다. 나오면 §1-1 |
| 3 | 리스크 앱 DB 사본을 둘 자리가 있다 | `df -h` 로 리스크 앱 데이터 디렉터리(HEAXHub `var/app_data/hwax_risk` 또는 `/data` 이관 위치)의 여유를 본다 | DB 크기의 두 배 이상 |

확인 2 의 명령(에이전트 서버 리포 루트에서).

```bash
grep -nE '^(DELIB_(SEAT_CTX|SER_CLIP|TRANSCRIPT_CLIP|KNOWLEDGE_BUDGET|CHAT_CONTEXT_BUDGET|PRIOR_BUDGET|SHARE_BUDGET|HUMAN_NOTE_MAX|EVID_BUDGET|EVID_ITEM_MAX|EVID_ITEMS|MCP_PAGE_CHARS|MAX_TOKENS)|TOOL_RESULT_MAX|TOOL_SCHEMA_BUDGET|HIST_ITEM_MAX|HANDOFF_RESULT_CHARS|THINK_KNOWLEDGE_BUDGET|PERSONA_HELPER_ROLE_MAX|LLM_MAX_TOKENS)=' .env
```

### 1-1. 옛 상한이 나왔을 때

이 이름들은 이제 **적었을 때만** 천장으로 걸리고, 안 적으면 모델 창에서 유도한다. 일부러 낮춘 것이 아니면 그 줄을 지운다(값만 지우지 말고 줄째). 무엇을 왜 적었는지 모르면 dev 에 이름과 값을 알려 준다. 지운 뒤에는 update-all 이 에이전트 서버를 다시 띄울 때 반영된다.

`DELIB_TIMEOUT_S=1800` 은 시간 한도라 이 목록과 상관없다(지우지 않는다).

## 2. 돌리기

```bash
./infra/scripts/update-all.sh
```

평소와 같다. 이번에 새로 보일 수 있는 줄.

| 출력 | 뜻 | 할 일 |
|---|---|---|
| `○ … 재기동 건너뜀 — 심의 N건 진행 중` | 도는 심의가 있어 재기동을 미뤘다. 그 구성 요소는 옛 코드로 돈다 | 심의가 끝난 뒤 한 번 더 돌린다 |
| HEAX 허브 구획의 같은 `○` 줄 | 허브 앱(리스크 앱 포함) 교체도 심의가 돌면 미룬다. 미룬 것은 실패가 아니다 | 위와 같다 |

## 3. 돌린 뒤 확인

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| ① | 리스크 앱 DB 가 v3 다 | `./infra/scripts/risk-review-inventory.sh` | `스키마 버전: 3` |
| ② | 엔진이 1백만 토큰 창으로 근거 예산을 잡았다 | 같은 출력의 `health:` 줄 | `evid_budget` 이 389,648 안팎이다. 2,000 이나 20,067 이면 창을 못 읽었거나(§1 확인 2 의 손잡이·`LLM_CONTEXT_TOKENS`) 옛 엔진이다 |
| ③ | 게이트웨이에 리스크 앱 새 도구가 뜬다 | Claude 에서 `list_tool_apps(app='heax-hwax_risk')` | 도구 25종, 그 안에 `risk_next_step` 이 있다. 14종이면 허브가 아직 옛 SIF 다 |
| ④ | Claude 쓰기가 본인 이름으로 된다 | Claude 에서 `risk_next_step` | 응답이 오고 `delegation_required` 가 없다. 있으면 그 응답의 `detail.fix` 를 따른다 |
| ⑤ | 게이트웨이 감사에 옛 앱 표식이 늘지 않는다 | 게이트웨이 리포 루트에서 `grep -c folded-old-app audit.jsonl`(감사 경로를 `GATEWAY_AUDIT` 로 바꾼 박스는 그 파일)을 리스크 앱을 새로 띄운 직후와 Claude 로 리스크 도구를 한 번 부른 뒤에 두 번 센다 | 두 수가 같다. 늘었으면 허브가 아직 옛 SIF 로 돈다 |

## 4. 되돌리기

- **리스크 앱** — v3 로 오른 DB 는 옛 SIF 가 열지 못한다(기동을 거부한다). 옛 SIF 로 내리려면 데이터 디렉터리의 `risk_review.db.pre-migrate-v2-<시각>` 을 `risk_review.db` 로 되돌린다. 그 사이에 쓴 것은 잃는다. 사본은 기동마다 가장 새것 둘만 남는다.
- **나머지 리포** — 평소처럼 git 으로 되돌리고 그 구성 요소를 다시 띄운다. 게이트웨이와 리스크 앱은 어느 쪽이 먼저 바뀌어도 서로 끊기지 않는다(옛 리스크 앱과 섞이면 종전처럼 돌고 감사에 `folded-old-app` 이 남는다).

## 5. 사용자에게 알릴 것

- Claude 에서 리스크 심사는 `risk_next_step` 부터 시작한다. 과제 올리기·캡처·변경 비교·심사 시작을 Claude 에서 할 수 있고, 결과는 웹 리스크 앱에 그대로 보인다.
- 리스크 앱 MCP 를 개인 토큰으로 **직접 등록**한 사람은 쓰기가 막힌다(읽기만 된다). hwax 게이트웨이 MCP 하나로 쓰면 된다.
- 심의·챗이 긴 글을 자르지 않는다. 대신 한 번의 호출이 길어질 수 있다.

## 6. 새 손잡이 (전부 선택 — 안 적으면 기본값)

| 이름 | 어디 | 기본 | 무엇 |
|---|---|---|---|
| `DELIB_MCP_PAGE_CHARS` | 에이전트 서버 `.env` | 25000 | Claude 가 받는 `deliberate_*` 결과 한 쪽의 글자 수. 사용자 PC 의 `MAX_MCP_OUTPUT_TOKENS` 를 낮췄으면 같이 낮춘다 |
| `GATEWAY_CACHE_ITEM_MAX_BYTES` · `GATEWAY_CACHE_MAX_BYTES` | 게이트웨이를 띄우는 환경 | 코드 기본 | 응답 캐시의 한 건·전체 바이트 상한. 넘는 결과는 캐시하지 않고 그대로 준다 |
| `AIDH_RERANK_MAX_LENGTH` · `AIDH_SEARCH_TOP_K_MAX` | AIDataHub `deploy/apptainer/.env` | 코드 기본 | 재정렬 모델 입력 길이·검색 top_k 의 상한 |
| `HWAXRISK_RUNNER_LOCK_RETRY_S` | 리스크 앱(허브 매니페스트 env) | 코드 기본 | 러너 잠금을 못 쥔 프로세스가 다시 시도하는 간격 |

dev 박스에 넣은 메모리 감시기 설정(earlyoom)은 dev 전용이다. cae00 에 옮기지 않는다.
