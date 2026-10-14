# 서버(cae00)에서 할 일 — 리스크 심사 M1(패널 수리·1백만 토큰·Claude 입구)

> 대상: cae00 운영자 · **대조 시점 2026-10-11** · 보낸 쪽: dev(이 리포 `docs/risk-review-redesign/`).
> 반영되는 리포와 push 된 커밋(2026-10-11) — HWAXRisk `c3f46ba`(리스크 앱 SIF, Drive 에도 올림) · HWAXAgentServer `7644284` · HWAXMcpGateway `9dc6c01` · AIDataHub `b401f88` · HEAXHub `04c0930`(등록 사본) · HWAXPortal 은 이 문서를 담은 커밋(프론트 dist 는 Drive 에도 올림). 이보다 새 커밋이 있어도 update-all 이 함께 받는다.
> dev 에서는 같은 커밋으로 다섯 구성 요소를 다시 띄워 §3 의 ①③④⑤ 를 확인했다(② 는 dev 창이 16K 라 2,000 이 맞다). 합성 40건 과제로 Claude 에서 Tier A 패널 셋을 끝까지 돌렸다(context-notes D-25).
> 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.
> 이 박스의 지금 상태는 이 문서가 알지 못한다. 그래서 확인마다 재는 명령을 적었다.

## 0. 한눈에

이번 묶음은 평소처럼 `./infra/scripts/update-all.sh` 한 번으로 들어온다. 사람이 할 일은 돌리기 전 확인 셋과 돌린 뒤 확인 다섯이다.

달라지는 것.
- **리스크 앱 패널이 끝까지 돈다.** 같은 과제의 두 번째 패널부터 저장이 실패하던 것, 저장이 터지면 결과를 잃던 것(이제 먼저 남기고 '다시 저장' 한다), 부품 이름의 낱말 때문에 브리프가 죽던 것을 고쳤다.
- **리스크 앱 DB 가 스키마 v3 로 오른다.** 새 SIF 가 처음 뜰 때 스스로 올리고 직전 사본을 남긴다. 옛 SIF 는 v3 DB 를 열지 못한다(§4).
- **글자를 자르지 않는다.** 엔진·포털·게이트웨이·AIDataHub 의 상한을 GLM-5.2 의 1백만 토큰 창에서 유도한다. `.env` 에 적어 둔 옛 상한이 있으면 그 값이 천장으로 걸린다(§1 확인 2).
- **Claude 에서 과제를 올리고 리스크 심사를 시작할 수 있다.** 리스크 앱 도구가 14종에서 26종이 된다(`risk_next_step` 부터, 저장이 실패한 패널의 다시 저장 `risk_repersist_panel` 포함). 쓰기 도구는 게이트웨이가 확인한 **본인 신원으로만** 쓴다. 리스크 앱 MCP 를 개인 토큰으로 **직접 등록한 길은 읽기 전용**이 된다.

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
| ③ | 게이트웨이에 리스크 앱 새 도구가 뜬다 | Claude 에서 `list_tool_apps(app='heax-hwax_risk')` | 도구 26종, 그 안에 `risk_next_step`·`risk_repersist_panel` 이 있다. 그보다 적으면 허브가 아직 옛 SIF 다 |
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

## 7. 리스크 앱 비밀 키 — `secrets.env` (2026-10-14 덧붙임)

> 리스크 앱 데이터 디렉터리(cae00 은 `/data/appdata/hwax_risk/`, 0600)의 `secrets.env` 다. 값은 화면에 띄우지 않고 넣는다.
> 아래 '이번 뒤' 칸은 사람 자격 작업([../risk-credentials/PLAN.md](../risk-credentials/PLAN.md))이 들어간 뒤의 뜻이다 — 그 전 SIF 에서는
> 다섯 키가 전부 필수로 세어져 '이 박스의 자격이 없습니다' 가 늘 뜬다(원인과 다른 문구 — 요청 R5).

| 키 | 무엇 | 누구 명의 | 없으면 | 이번 뒤 |
|---|---|---|---|---|
| `HWAXRISK_CRED_KEY` | 사람이 등록한 포털 PAT 를 암호화하는 키(Fernet) | 사람 아님 — 박스 값 | 앱이 첫 PAT 등록 때 `<data>/cred.key` 를 만들어 쓴다(아래 7-1) | **필수 하나** |
| `HWAXRISK_HEAX_GATEWAY_SECRET` | 게이트웨이 사람별 위임 단언의 비밀 | 사람 아님 — provision-config 가 만든다 | Claude 로 온 호출이 사람으로 보이지 않고(쓰기 도구 거절) PAT 자동 등록도 없다 | 선택(Claude 길에 필요) |
| `HWAXRISK_PORTAL_PAT` | 서비스 읽기 PAT | 비인격 서비스 계정 | 사람 PAT 가 없을 때의 짧은 조회(전문가 명단·현장 VOC·캡처 MCP 폴백)가 닫힌다 | 선택 — 사람이 시작한 잡(패널·카드 대조)은 쓰지 않는다 |
| `HWAXRISK_HEAX_SERVICE_PAT` | 허브 서비스 토큰(StepForge REST) | 허브 관리자 PAT | 웹 로그인 토큰도 게이트웨이 경유 본인 PAT 도 없는 캡처가 G6 `unit_unknown` 으로 막힌다 | 선택 — 마지막 폴백 |
| `HWAXRISK_PORTAL_PAT_RW` | RA 쓰기 | — | 지금은 달라지는 것이 없다(보내는 쪽 미배선, M4) | 선택 |
| `HWAXRISK_AIDH_API_KEY` | AIDataHub 반입 키 | AIDataHub 관리자가 발급하는 API 키(이름 `hwax-risk`) | 지금은 달라지는 것이 없다(반입하는 쪽 미배선, M4) | 선택 — 반입의 정본은 서비스 키다(사람별 서버 간 길이 없다, 요청 R4) |
| `HWAXRISK_BACKUP_KEY` | 백업 암호화(age 공개키) | — | 백업이 평문이고 `/api/health` 에 `backup_unencrypted` | 선택 |

### 7-1. `cred.key` 를 `secrets.env` 로 옮기기

앱이 `<data>/cred.key` 를 만들어 쓰고 있으면(설정 화면 '이 박스' 의 `cred_key_source` 가 `dev_fallback`, 기동 로그에 경고) 그 값을 **그대로** 옮긴다. 새 키를 만들어 넣으면 이미 등록된 PAT 가 전부 풀리지 않는다.

```bash
D=/data/appdata/hwax_risk                        # 리스크 앱 데이터 디렉터리
K="$(tr -d '[:space:]' < "$D/cred.key" 2>/dev/null)"
if [ -z "$K" ]; then echo "cred.key 가 없거나 비었다 — 멈춘다"
elif grep -qE '^HWAXRISK_CRED_KEY=.+' "$D/secrets.env" 2>/dev/null; then echo "secrets.env 에 이미 있다 — 멈춘다"
else printf '\nHWAXRISK_CRED_KEY=%s\n' "$K" >> "$D/secrets.env"; chmod 600 "$D/secrets.env"; echo "옮겼다"; fi
unset K
```

앞에 붙인 줄바꿈은 `secrets.env` 끝에 줄바꿈이 없을 때 앞 줄에 붙어 두 키가 함께 깨지는 것을 막는다. 값은 화면에 나오지 않는다.

그 뒤 리스크 앱을 다시 띄우고(`redeploy-app.sh hwax-risk`) 설정 화면의 `cred_key_source` 가 `secrets` 인지 본다. `cred.key` 는 지우지 말고 백업과 함께 둔다(같은 값이다).

### 7-2. 자동 등록을 멈추려면

포털 토큰 화면에서 '교환으로 생김 · hwax-risk' 토큰을 폐기해도, 그 사람의 자동 등록이 켜져 있으면 다음 Claude 호출 때 다시 생긴다(context-notes C-17). 멈추는 스위치는 리스크 앱 설정 화면에 곧 생긴다. 그때까지는 운영자가 앱 데이터 DB 에서 그 사람의 자동 등록을 끈다(앱이 돌고 있어도 된다 — 요청마다 다시 읽는다).

```bash
D=/data/appdata/hwax_risk                        # 리스크 앱 데이터 디렉터리
WHO='someone@example.com'                         # 끌 사람의 이메일(소문자)
python3 - "$D/risk_review.db" "$WHO" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); who = sys.argv[2].strip().lower()
con.execute("INSERT INTO _user_prefs(owner_sub, portal_pat_auto) VALUES(?, 0)"
            " ON CONFLICT(owner_sub) DO UPDATE SET portal_pat_auto = 0", (who,))
con.commit(); print(who, "자동 등록 끔")
PY
```

그 뒤 포털 토큰 화면에서 그 사람의 '교환으로 생김 · hwax-risk' 토큰을 폐기한다. 다시 켤 때는 앞선 실패의 쉼(최대 6시간)도 함께 지운다 — 같은 명령의 SQL 을 아래로 바꾼다.

```text
con.execute("INSERT INTO _user_prefs(owner_sub, portal_pat_auto) VALUES(?, 1)"
            " ON CONFLICT(owner_sub) DO UPDATE SET portal_pat_auto = 1,"
            " auto_error = NULL, auto_error_kind = NULL, auto_error_at = NULL", (who,))
```
 끈 동안 그 사람이 시작한 패널·카드 대조는 PAT 를 손으로 등록할 때까지 `pat_unavailable` 로 멈춘다.
