# cae00 배포 가이드 — 무엇이 `update-all` 로 되고, 무엇이 따로인가

> **대조 시점 2026-09-26.** 실제 스크립트(update-all.sh · deploy-all-from-drive.sh · AIDataHub deploy ·
> STE deploy · 심의 파이프라인)와 대조해 썼다. 런타임(cae00 실행) 검증이 아니라 소스 검증이므로, 박스별
> 상태(provision.env 토큰 · rclone remote · .env 포트)에 따라 결과가 달라질 수 있다(§끝 주의 참조).
>
> ⚠ 근거는 **줄번호 대신 배너 문자열**로 가리킨다(`update-all.sh: hr "2c) …"`). update-all.sh 가 1,400여 줄로
> 자라며 줄번호가 통째로 밀렸고, 옛 인용이 엉뚱한 코드를 가리켜 이 문서를 믿을 수 없게 만들었다(2026-09-26 감사).

## 0. 한 줄 요약

- **`update-all` 한 방에 되는 것**: 포털·챗 스택·MCP 게이트웨이 배포 + **AIDataHub 데이터(전문가·카드) 병합** +
  워크플로 사본 동기화 + `.env` 새 옵션 채움(1c) + ste 라우트 자동 기록(1d) + `/data` 이관(2b) +
  **ste 코드 최신화(2c)** + agent-server `.env` 보정(3.5) + 헬스 게이트(§6·6b) + 챗 스모크(§7).
- **`update-all` 로 안 되는 것**(진짜 사람 몫 셋): ① ste **최초 반입**(번들·SIF·installer·토큰, 런북 §1~§8)
  ② `ste-tunnel` 유닛 설치(`install-ste-tunnel.sh`) ③ **프론트 빌드** — cae00 은 npm 에 못 닿아 Drive 아티팩트를 받는다.
- **dev 가 선행해야 하는 것**: 전문가/카드를 **dev AIDataHub 에 업로드 → `backup-to-drive`**(그래야 cae00 이 병합해
  온다). 빌드 아티팩트·ste 코드는 **`./infra/scripts/build-all-to-drive.sh [대상…]`** → **`./infra/scripts/drive-drift.sh`**
  로 Drive 가 dev 와 같은지 확인(0=일치·1=드리프트·2=확인불가). 안 올리면 cae00 은 그만큼 옛것을 받는다.
- **로그 표식 셋을 가른다** — `✗` 만 종료코드를 세운다 · `⚠` 는 경고 · **`○` 는 "기능은 있는데 옵션·설정이 없어
  이번 실행에서 셋업하지 않았다"** 로, 끝의 요약에 "켜려면" 과 함께 다시 나온다(실패가 아니다).

---

## 1. `git pull && update-all` 이 실제로 하는 일

`update-all` 은 스스로 최신화한다 — 앞의 `git pull` 없이도 §1 이 포털 레포를 `fetch + reset --hard origin/<branch>` 후 새 버전으로 1회 재실행한다(`UPDATE_ALL_REEXEC` 가드로 딱 1번). 로컬 수정이 있으면 — **기본 경로가 `git stash push -u` 로 치운 뒤 `reset --hard origin/<branch>`** 한다(치운 것은
`git stash pop` 으로 되돌린다). `NO_GIT_RESET=1` 은 **`merge --ff-only` 만** 하고 stash 는 하지 않는다(ff 불가면 현재
체크아웃 유지). 즉 stash 는 기본 쪽이고, `NO_GIT_RESET=1` 은 "아무것도 건드리지 말고 앞으로만 감기" 다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| **§0a** | `--with-<name>` 파싱 → `HWAX_WITH` — 무거운·외부 배포 단계를 이번 실행에 한해 강제(첫 사용처 `--with-ste`) | `hr` 없음(상단) · `lib/deploy-gate.sh` |
| **§0b** | **단일 실행 잠금** — 겹쳐 돌리면 기다리지 않고 **rc 3** 으로 즉시 끝난다(§2 의 rc 3 = 소스 갱신 실패와 다른 뜻). 잠금은 바깥 bash 가 쥐고 본문은 자식으로 돈다(자식엔 fd 를 닫아 넘겨 데몬이 물려받지 않는다). **Ctrl-C** 는 진행 중 단계까지 즉시 멈춘다. 단계가 INT 를 삼키고 정상 종료하면(rsync 는 rc 20, rclone) 본문이 그것을 받아 두고 **다음 § 머리에서** 멈춘다 — 그동안 잠금은 잡혀 있어 프롬프트가 돌아오지 않고, 두 번 눌러도 빨라지지 않는다(bash 는 전경 단계가 끝나기 전엔 trap 을 미룬다). 어느 쪽이든 Ctrl-C 로 멈췄으면 update-all 은 신호로 끝나 `;` 체인이 끊긴다. **`kill <pid>`** 는 바깥이 받은 즉시 "받음" 한 줄, 본문이 단계가 끝난 뒤 "받아 두었다" 한 줄을 찍고 **진행 중인 §(단락)가 끝난 뒤 다음 § 머리에서** 멈춘다(그때 지금까지의 ✗·○ 요약을 낸다)(단순 명령 경계에서 죽이면 §5 의 down→up 같은 짝이 반으로 갈려 서비스가 내려간 채 끝난다) — 원격·nohup 실행을 멈출 때는 `kill -TERM`(`kill -INT` 는 조용히 무시된다, INT 는 Ctrl-C 그룹에만 뜻이 있다). 본문의 `timeout` 은 전부 `--foreground` 다(기본 timeout 은 새 프로세스 그룹이라 Ctrl-C 가 그 단계에 닿지 않는다 — 2c 의 deploy-ste 가 900초 동안 Ctrl-C 무효였다). 옛 판(09-27 이전)이 물려준 fd 를 쥔 **데몬**만 남아 있으면 "옛 판이 fd 를 물려준 데몬이다" 한 줄을 찍고 잠금 파일을 새로 만들어 진행하고, 옛 판의 하위 단계(deploy-all 등)가 아직 돌면 rc 3 으로 기다리게 한다. 잠금이 잡혀 있는데 쥔 프로세스가 **안 보이면**(다른 사용자) 지우지 않고 rc 3 + 확인 명령. `flock` 없으면 잠금만 없이(kill·Ctrl-C 규율은 같다) 경고 후 진행, `python3` 없으면 Ctrl-C 복원 없이 경고만. 잠금 파일은 `/tmp/hwax-update-all.<해시>.lock`(TMPDIR 무관), 옆의 숨김 `.hwax-update-all-heal.<해시>` 는 지우지 않는다 — 예외 하나: 같은 리포를 `sudo` 로 돌린 적이 있으면 두 파일이 root 소유가 되어 모든 실행이 "열 수 없다(소유자 root)" rc 3 으로 막힌다. 그때는 **먼저 `ps -ef | grep update-all` 로 그 사용자의 실행이 도는지 보고**(돌면 기다린다) 끝난 흔적이면 문구가 안내하는 `sudo rm -f <두 파일>` 뒤 재실행. 롤백(09-27 이전 커밋으로 reset) 뒤 첫 실행은 rc 3 이 정상 — 한 번 더 돌린다(실측) | update-all.sh 상단 |
| §1 | 포털 레포 self-update(fetch+reset) → 1회 재실행 | `hr "1)"` |
| **§1a** | **워크플로 정본→런타임 사본 동기화** — `infra/pipeline/*.js`(meta 보유)를 gitignore 사본 `.claude/workflows/` 로 복사. 이름호출 런타임이 옛 사본 쓰는 갭 봉합 | 배너 없음(§1 뒤) · sync-workflows.sh |
| §1b | 배포 전 로컬 백업(/data/backups) + 일일 cron(03:30) 멱등 보장 | `hr "1b)"` |
| **§1c** | **`.env` 옵션 동기화**(env-sync.sh) — `.env.example` 의 새 키를 기존 `.env` 에 덧붙인다. 비밀·자리표시자는 **주석으로만** 넣고 "값을 정해야 한다" 로 보고(그 설정이 켜는 기능은 꺼진 상태) | `hr "1c)"` |
| **§1d** | **ste 라우트 자동 기록** — teleport 박스인데 `routes.local.env` 에 `ste=` 가 없으면 `ste=http://127.0.0.1:15810/` 를 적는다(§2 가 그 뒤에 nginx 를 다시 만든다). `HWAX_STE_AUTOROUTE=0` 으로만 끈다 | `hr "1d)"` |
| §2 | **전 서비스 배포** — `deploy-all-from-drive`: `portal mxwp heax aidh signalforge kooremapper`. 각 서비스 git pull → Drive 에서 **미리 빌드된 아티팩트 반입**(cae00 은 빌드 불가) → START. 끝에 nginx conf 재생성+재기동 **바뀌지 않은 서비스는 재기동 생략** — 아티팩트는 영구 캐시에 받아 안 바뀐 파일은 전송 0, 지문(git HEAD·SIF·dist·.env)이 **마지막으로 띄운 시점**(`infra/.state/restart-fp/`)과 같고 살아 있으면 stop/start 를 건너뛴다(기록은 **모든 리스너가 새 프로세스로 답한 뒤에만** — stop 이 안 돼 옛 프로세스가 하나라도 그대로면 ✗ "재기동이 되지 않았다 — 같은 프로세스가 답한다: <url>" 로 실패하고 기록하지 않는다. nginx 갱신도 같은 규율로 skip 에 집계)(줄로 보이고 Done 에서 모아 낸다). nginx 도 conf 지문이 같으면 bounce 생략. 전부 재기동: `HWAX_RESTART_ALL=1` | deploy-all-from-drive.sh |
| **§2b** | `/data` 이관 — `HWAX_DATA_ROOT` 가 있을 때만(멱등·자동 롤백) | `hr "2b)"` |
| **§3** | **AIDataHub 데이터 병합** — 아래 §2 참조. 비파괴 merge | `hr "3)"` |
| **§2c** | **ste 코드 최신화(다를 때만)** — `deploy-ste.sh --if-stale`(상한 900초). direct 박스는 지문이 다를 때만, teleport 박스는 공용 게이트 세 신호를 통과할 때만. 게이트가 막으면 rc 3 = "안 켬"(○ 장부) | `hr "2c)"` |
| **§2d** | **ste 터널 정합(teleport 박스만)** — `install-ste-tunnel.sh --check` 로 15810·15812 를 실측하고, 실패하면 리포 유닛으로 다시 세운다(옛 손 터널이 포트를 쥐고 있으면 내린다 — `STE_TUNNEL_NO_KILL=1` 로 끔). 종전엔 §6 이 **보고만** 해서 배포를 다시 돌려도 같은 빨강이 반복됐다(2026-09-28 사용자 실측). `sudo loginctl enable-linger` 는 비대화식이라 프롬프트 대신 한 줄 안내로 건너뛴다. teleport 가 아닌 박스는 ○ | `hr "2d)"` |
| §4 | 챗 스택 pull+재기동 — `signalforge-mcp mcp-gateway agent-server`(백엔드→게이트웨이→소비자 순) — **지문(git HEAD + .env + 매니페스트 identity 파일)이 마지막 기동 시점과 같고 살아 있으면 down/up 생략**(.env 를 누가 언제 고쳤든 지문에 든다). 재기동했으면 health 포트의 프로세스가 바뀐 것을 확인한 뒤에만 기록(같으면 ✗). `git pull` 만 실패하고 서비스가 정상이면 재기동 없이 끝에서 `▶ ⚠ 갱신(git pull) 실패:<이름>` + 종료코드 1(포털이 그렇더라도 나머지는 계속한다). 수동 강제: `HWAX_FORCE_RESTART="<이름> …"`. 전부 재기동: `HWAX_RESTART_ALL=1` | `hr "4)"` |
| **§3.5** | agent-server `.env` 보정 — `@FROM_RA` 미치환 마커 제거·재치환, `VLLM_BASE_URL` 확정 | `hr "3.5)"` |
| §5 | 게이트웨이 config 정합 — 기대 백엔드 빠졌으면 `provision-config --force` 후 재기동·재검증 | `hr "5)"` |
| §6 | **헬스 게이트**(critical) — 아래 표 밖 설명 참조 | `hr "6)"` |
| **§6b** | services.yaml 대조(기동·데이터 대상) | `hr "6b)"` |
| **§7** | **챗 스모크**(critical) — `/chat` 에 실제 문장 하나를 보내 응답이 오는지. 실패면 agent-server 로그 꼬리를 함께 낸다 | 스크립트 끝 |
| 끝 | **○ "있는데 안 켠 것" 요약** — 기능 N · 값 미정 설정 N · 선택 설정 N, 각각 "켜려면" 과 함께 | `hwax_skip_summary` |

**화면에 찍히는 실제 순서**(배너 문자열) — `1) · 1b) · 1c) · 1d) · 2) · 2b) · 3) · 2c) · 2d) · 3.5) · 4) · 5) · 6) · 6b) · 7)`.
번호가 순서와 어긋난 자리가 있다(2c 가 3 뒤, 3.5 가 2c 뒤) — 배너 문자열로 찾는 것이 안전하다.

**§6 의 치명 항목**(하나라도 실패면 끝에서 `exit 1`, 그리고 무엇이 세웠는지 목록을 다시 낸다) — 무인증 `/health`
넷(portal:8723 · nginx:8088 · agent-server:9009 · gateway:9110) · 절차 모듈(`/procedures-api/health` 의 본문 `ok:true`,
상태코드로는 못 본다) · **SPA dist 대조**(`frontend/dist/.build-src` ≠ `HEAD:frontend` → dev 에서 빌드+Drive 발행이 필요
하다는 뜻) · 게이트웨이 **권한 정책 적재**(`access_policy_loaded=0` 이면 전 백엔드가 열리고 위임 백엔드는 닫힌다) ·
`ste=` 라우트가 있는 박스에서는 **ste 자격 중계**(시크릿 불일치 401 · 헤드에 시크릿 없음 404 · 포털 쪽 공백 · 옛 판)와
**ste MCP :15812**(미부착·무응답 — ste 도구 8종이 통째로 안 뜬다). 비치명(`⚠`)은 백엔드 도달·프록시 본문 같은
"이 박스 밖" 항목과 판정 불가 갈래다. **그리고 §2c 가 `deploy-ste.sh` 를 실제로 부른다** — 옛 문서의 "프로브만 한다 ·
힌트로 안내만 하고 호출하지 않는다" 는 2026-09-23 이전 사실이다. ste 가 빨강이면 먼저
`./infra/scripts/ste-doctor.sh`(한 화면 진단, `--report` 로 JSON) 를 본다.

---

## 2. 전문가·카드가 심의에 반영되는 경로 (AIDataHub)

전문가 도구(`recommend_agents`·`get_context_bundle`·`agent_search`)는 **AIDataHub 가 서빙**한다(게이트웨이 백엔드 `ai-data-hub`). ExpertAgents 는 *저작소*이고, 카드는 **AIDataHub 로 업로드돼야** 심의가 본다.

```
ExpertAgents(저작)                    dev AIDataHub                Drive                 cae00 AIDataHub
  knowledge/*/cards  ──erag export──▶  (Postgres)  ──backup-to-drive──▶  db-dumps  ──update-all §3 merge──▶  (live)
     fact-checked                                    aidh-db-*.sql.gz      merge-from-drive(비파괴)
```

### dev 에서 (업로드 2종 + Drive 반출)

| 명령 | 올리는 것 | 필터 |
|---|---|---|
| `erag export-aidatahub --upload --url <dev-aidh> --api-key <KEY>` | **전문가 정의**(agent) — recommend_agents·좌석 발굴이 이걸 본다 | 없음(전 전문가) |
| `erag export-records --upload --bind --url <dev-aidh> --api-key <KEY>` | **지식카드**(record) — 그라운딩(get_context_bundle·agent_search)이 이걸 인용 | **`fact-checked` 카드만**(draft 제외, 0장이면 중단) |
| `bash deploy/apptainer/backup-to-drive.sh` | dev AIDataHub DB 덤프 → Drive `AIDataHub/db-dumps` | 최신 RETAIN(기본 5)개 유지 |

> ⚠️ **두 업로드를 다 해야 한다.** 전문가 정의만 올리면 좌석은 발굴되나 그라운딩이 빈 근거가 되고,
> 카드만 올리면 records 는 있으나 전문가 목록에서 안 잡힐 수 있다. `export-aidatahub` → `export-records` 순.

### cae00 에서 — `update-all` 이 자동으로

§3 이 `merge-from-drive.sh` 로 Drive 최신 덤프를 **스테이징 DB 에 로드 후 병합**한다 — **dev 신규는 추가, cae00 자체 등록분은 보존(DROP 안 함, 운영 DB 가 순간도 안 빈다)**. 최신 덤프가 지난 병합분(`.last-merged`)과 같으면 생략(update-all.sh:170-182, merge-from-drive.sh:9).

- 즉 **재기동만으로는 반영 안 된다**(레지스트리는 시작 스냅샷이지만 데이터는 Postgres 영속). **§3 병합**이 반영 지점이고, `update-all` 이 그걸 돈다.
- `sync-from-drive.sh`(DROP+CREATE+restore, 파괴적 전체복원)는 **복원을 자동으로 하지 않는다**. 단 §3 이 매 실행마다
  `--dry-run --skip-git` 으로 한 번 부른다 — 스택·임베딩 모델 확보용이고 데이터는 건드리지 않는다. 파괴적 전체복원은
  사람이 **인자 없이** 부를 때만이다(재해복구·초기시드). 일상 반영은 §3 merge 로 충분하다.

---

## 3. 심의가 실제로 새 전문가·카드를 쓰는 조건

MCP 경로(Claude Code·게이트웨이)와 웹 경로(`/시뮬심의`) **둘 다 반영**돼 있다.

- **수치 스파인 고정 착석** — 기본 ON. 좌석 수가 두 경로에서 다르다(솔버 좌석 유무).
  - MCP: `hwax-sim-deliberate.js` `FIXED_CAE` = 방법론 2(modeling·post) + `SPINE_CORE` **4**(정식화·이산화·**솔버**·검증)
    + `SPINE_REVIEW` 2 + `SPINE_VALIDATION` 2 = **10석**. 플래그 `spine`/`spineReview`/`spineValidation`(기본 true).
  - 웹: `deliberation.py` `_SIM_FIXED_CAE` = 방법론 2 + 코어 **3**(솔버 없음) + 리뷰 2 + 검증·UQ 2 = **9석**.
    env `DELIB_SIM_SPINE`/`DELIB_SIM_SPINE_REVIEW`/`DELIB_SIM_SPINE_VALIDATION`(기본 1).
- **카드 그라운딩** — 발언이 지식카드를 인용.
  - MCP: `groundCards`(sim 기본 ON) → 각 좌석이 `get_context_bundle(agent_type)`·`semantic_search` 호출(`hwax-deliberate.js` 의 `groundCards`).
  - 웹: `DELIB_PERSONA_KNOWLEDGE`(기본 1) → 페르소나별 `agent_search` 결정적 RAG 주입(`deliberation.py` 의 같은 이름 게이트) — 다른 메커니즘, 같은 AIDataHub 의존.
- **전제(둘 다)**:
  1. **AIDataHub 에 해당 `xd-cae-*`(+발굴 대상) 전문가·records 가 동기화**돼 있어야 근거가 빈 값이 아니다 → §2 의 업로드+병합.
  2. **세션에 게이트웨이 MCP 연결** — 도구(get_context_bundle/agent_search/recommend_agents)가 노출돼야 한다. 미연결 시 MCP 는 페르소나 지식으로 발언(가법적·회귀 없음), 웹은 카드 주입 생략.
  3. **이름호출 최상위 워크플로**(hwax-sim-deliberate)는 `.claude/workflows/` 사본을 읽으므로 §1a 동기화가 선결(자식 hwax-deliberate 호출은 scriptPath 라 무관).

**검증 방법**: cae00 재기동 후 `/시뮬심의` 1건 → 고정 좌석 목록(방법론 2 + 코어 + 리뷰 2 + 검증·UQ 2)이 **다 앉았는지**
+ 발언에 카드 출처가 붙는지. 좌석 **수**로 판정하지 않는다 — MCP 10 · 웹 9 로 다르고 플래그로도 바뀐다.

---

## 4. STE(SmartTwinExplorer) — 왜/어떻게 따로 배포하나

STE 백엔드는 **cae00 가 아니라 에어갭 ste 헤드노드** 에 있다. cae00 은 그 헤드노드 직결 경로가 없어 **Teleport SSH
터널**(`ste-tunnel`)로 닿는데 **포트가 둘**이다 — 루프백 **15810**(웹·REST)과 **15812**(ste MCP). 15812 가 없으면 게이트웨이
ste 백엔드가 영구 DOWN 이고 **ste 도구 8종이 통째로 안 뜬다**(§6 이 fail 로 잡는다). 유닛은 리포가 소유한다 —
`infra/systemd/ste-tunnel.service` 템플릿 + `./infra/scripts/install-ste-tunnel.sh`(설치 · `--check` 로 두 포트 실측 · **update-all §2d 가 자동으로 부른다** ·
15812 가 000 이면 두 원인을 갈라 준다 — 로컬 리스너가 **없으면** 유닛이 그 포트를 못 연 것이고(옛 손 터널이 15810 을 쥐면 `ExitOnForwardFailure` 로 유닛이 영원히 재시도한다), **있는데** 000 이면 헤드에서 `127.0.0.1:15812` 로 가는 연결이 거부된 것이다(`ste-doctor.sh` 가 헤드의 listen **주소**와 헤드 자기 자신의 `curl /mcp` 코드를 같이 보여 준다) ·
`remove`, linger 포함, 값은 `transport.env` 에서 읽는다). STE 는 `services.yaml` 의 **기동·갱신 대상이 아니다**(데이터만
`data_only:` 에 등록돼 `services.py data --check` 가 본다).

**cae00 → ste 헤드의 모든 경로(배포·터널·사용자 위임)는 Teleport 인증서 하나에 매달린다** — `SmartTwinExplorer/deploy/transport.env`
의 `TELEPORT_SSH_CONFIG` 가 가리키는 ssh_config 의 인증서다. 사람의 `tsh login`(→ `tsh config`)이면 그 세션이 끝날 때, tbot(Machine ID)이면
tbot 이 갱신을 멈출 때 끊긴다 — §2c 는 전제조건 실패로 ○ 를 찍고(실패 아님) 터널은 죽는다. tbot 으로 무인화하려면
`TELEPORT_SSH_CONFIG` 를 tbot destination 의 `ssh_config` 로 바꾸고 `./infra/scripts/install-ste-tunnel.sh` 로 터널을 다시 세운다(스크립트 무변경).
**지금 이 박스가 어느 쪽인지는 여기 적지 않는다** — `./infra/scripts/ste-doctor.sh` 의 `teleport` 행(그 ssh_config 인증서의 남은 시간,
tbot 여부)과 `tunnel-cfg` 행(터널 유닛이 같은 파일을 쓰는가)으로 본다. 못 읽으면 "모름" 으로 낸다 — 모름을 정상으로 읽지 않는다.
2026-09-30 사용자 보고: cae00 에서 tbot 이 인증서를 갱신 중(docs/ste-cae00 D-31).

### STE 는 3단계

```
① (1회) 최초 반입 — 런북 §1~§8 수동 (사람)
      Teleport·transport.env · cluster.prod.yaml(노드·계정·키·라이선스) · 번들 9.6GB + SIF · installer(설치·토큰) · 첫 서비스 배포
      ↳ 관리자 협조(계산노드 공개키 등록 등) 필요. 정본: SmartTwinExplorer/docs/03-runbook/cae00-staging.md
      ↳ 터널 유닛(15810·15812): ./infra/scripts/install-ste-tunnel.sh   (--check 로 두 포트 확인)
② (이후) dev: ./infra/scripts/build-all-to-drive.sh ste   # pack-staging + push-to-drive(Drive staging)
              ./infra/scripts/drive-drift.sh              # Drive 가 dev HEAD 와 같은지 대조(0=일치)
③ (이후) cae00: ./infra/scripts/update-all.sh --with-ste   # §2c 가 deploy-ste.sh 를 부른다(게이트 통과 시)
              또는 ./infra/scripts/deploy-ste.sh           # 사람이 직접 = 게이트 없이 전면 갱신
```

- `deploy-ste.sh` → `refresh-code.sh` 체인(teleport 경로): pull-from-drive → sha256 → git 커밋 고정 → dist 전개 →
  (requirements 바뀐 회차만) wheel 병합 → **`deploy-backend.sh` → `deploy-frontend.sh --no-build`**(back 이 먼저다 —
  front 를 먼저 돌리면 첫 배포에서 `Unit ste-backend.service not found` 로 죽는다) → 에이전트용 **CA 번들**(실패해도 계속)
  → **포털 자격 중계 시크릿**(`deploy/sync-sso-secret.sh`, 값은 stdin 으로만 넘긴다 — argv 는 Teleport 감사원장·`ps` 에 남는다).
  배포 후 포털 프록시 `/ste/api/health` 본문에 `smart-twin-explorer` 있는지로 검증. 시크릿이 어긋나면
  `FORCE_SSO_SECRET=1 ../SmartTwinExplorer/deploy/sync-sso-secret.sh`(포털 값으로 덮는다).
- **런타임 게이트**(refresh-code.sh:27-33): transport.env 존재, `tr_run 'true'`로 헤드노드 도달(Teleport 세션 만료면 §9-A), 정체성 가드(cae00 자신 가리키면 §9-D). 조건 안 되면 fail-fast.
- **최초 반입(①)은 자동화 밖** — refresh-code.sh 는 §11(코드 갱신)만 한다. 번들·SIF·토큰은 1회성이라 스크립트가 대신 안 한다.

> **박스 상태는 날짜를 박아 적지 않는다** — 옛 메모("cae00 에 staging 만 없음", 2026-08-26)가 한 달 낡은 채 남아 사람을
> 잘못 이끌었다. 지금 상태는 **재서 안다**: cae00 에서 `./infra/scripts/ste-doctor.sh --report` 한 번(라우트·전송 모드·
> 15810·15812·터널 유닛·Teleport 잔여·시크릿 verify·게이트웨이 ste 세션·권한 정책·포털 TLS·배포 신선도). dev 에서는
> `./infra/scripts/drive-drift.sh` 가 Drive staging 커밋과 dev HEAD 를 대조한다.

### `--with-ste` — **구현됨**(셋업과 갱신을 가르는 공용 게이트)

`--with-<name>` 은 일반 규칙이다(§0a) — 이름을 `HWAX_WITH` 로 실어 그 단계를 이번 실행에 한해 강제한다. 판정은
`infra/scripts/lib/deploy-gate.sh` 의 `hwax_gate` 하나이고, **세 신호가 모두 참일 때만** 배포한다.

| 신호 | 참이 되는 조건 |
|---|---|
| ① 사람 호출 | 대화형 터미널(`[ -t 0 ]`) **또는** `--with-ste` **또는** `STE_DEPLOY=1`. 크론·파이프는 거짓 |
| ② 신선도 | Drive `ste-code.commit` ≠ 헤드 `/opt/ste/.deployed-commit`(배포할 변경이 있다). 같으면 건너뜀. **못 재면 "모름" 이고 모름은 같음이 아니다** — 사람이 부른 경우만 진행하며 사유를 남긴다 |
| ③ 전제조건 | `tr_run true` — Teleport 세션으로 헤드노드에 닿는다 |

- 막히면 `deploy-ste.sh` 가 **rc 3** 을 돌려주고 update-all 은 그것을 "안 켬" 으로 읽어 **○ 장부**에 사유와 "켜려면
  `--with-ste`" 를 적는다(실패가 아니다). 옛 문서의 스니펫을 손으로 넣으면 §2c 와 **이중 트리거**가 되니 넣지 않는다.
- **대화형 실행은 그 자체로 ①을 만족한다** — cae00 에서 사람이 손으로 `./infra/scripts/update-all.sh` 를 치면 ②③이
  참인 회차에는 ste 실배포가 그 안에서 돈다. 헤드를 건드리고 싶지 않은 회차라면 Drive 를 올리지 않아(②가 거짓) 두거나,
  터미널이 아닌 경로(크론·파이프)로 돌린다.
- `./infra/scripts/update-forges.sh`(무인자)에 딸려 오는 ste 는 **게이트 경유**다(2026-09-26 수정). 전면 갱신은 이름을
  대야 한다 — `./infra/scripts/update-forges.sh ste` 는 지문이 같아도 유닛·venv·시크릿까지 다시 맞춘다(에어갭 박스에서는
  Drive 왕복 + 헤드 재기동이라 "수 분" 이 아니다).

---

## 5. 명령 요약 (치트시트)

```sh
# ── 포털·챗·MCP·AIDataHub 반영 (cae00) ──
./infra/scripts/update-all.sh              # 자기 최신화 + 전서비스 + AIDH merge + ste(2c) + 헬스게이트 + 챗 스모크
#   rc 3 = 다른 update-all 이 돌고 있다(0b flock — 겹쳐 돌리지 않는다). §2 의 rc 3(소스 갱신 실패)과 다른 뜻이다.
#   끝의 ○ 줄은 실패가 아니라 "옵션·설정이 없어 안 켠 단계" 다 — "켜려면" 이 함께 나온다.
./infra/scripts/update-all.sh --with-ste   # ste 를 이번 실행에 강제(에어갭 배포는 게이트 세 신호를 본다)
./infra/scripts/ste-doctor.sh              # ★ste 한 화면 진단(--report 로 JSON). 라우트·15810·15812·터널·TTL·시크릿·TLS
./infra/scripts/update-forges.sh           # ★경량 표적 갱신: stepforge+dynaforge+ste+chat — 딸려 온 ste 는 게이트 경유
./infra/scripts/update-forges.sh portal    # ★★포털만 — 포털 빌드만 새로 올린 경우. update-all 을 다 돌릴 필요가 없다
./infra/scripts/update-forges.sh portal chat   # 여러 개 나열 가능
./infra/scripts/update-forges.sh mxwp      # 정본 어휘(portal·mxwp·heax·aidh·signalforge·kooremapper)를 그대로 쓴다 — §2 에 위임된다
./infra/scripts/update-forges.sh chat      # 챗·심의 스택만(포털+agent-server+게이트웨이)
./infra/scripts/update-forges.sh ste       # STE **전면** 갱신(이름을 댔다 = 지문 같아도 유닛·venv·시크릿까지)
./infra/scripts/update-forges.sh restart   # 갱신 없이 재시작만 — nginx 안 뜨면 자동 부검(conf -t·TLS cap 힌트)
NO_GIT_RESET=1 ./infra/scripts/update-all.sh   # 로컬 수정 보존 모드

# ── 전문가/카드를 AIDataHub 에 반영 (dev 선행 → cae00 은 update-all 이 병합) ──
# dev:
erag export-aidatahub --upload --url http://localhost:8001 --api-key <KEY>   # 전문가 정의
erag export-records   --upload --bind --url http://localhost:8001 --api-key <KEY>   # fact-checked 카드
bash deploy/apptainer/backup-to-drive.sh                                       # 덤프 → Drive
# cae00: (update-all §3 이 자동 merge)

# ── 빌드 아티팩트·ste 코드를 Drive 로 (dev — 안 올리면 cae00 은 옛것을 받는다) ──
./infra/scripts/build-all-to-drive.sh            # 전체(portal mxwp heax signalforge kooremapper ste)
./infra/scripts/build-all-to-drive.sh portal ste # 골라서
./infra/scripts/drive-drift.sh                   # Drive ↔ 이 박스 대조(0=일치·1=드리프트·2=확인불가)

# ── STE 배포 (cae00) ──
./infra/scripts/update-all.sh --with-ste   # 권장 — §2c 가 게이트를 통과할 때만 배포
./infra/scripts/deploy-ste.sh              # 사람이 직접 = 게이트 없이 전면 갱신(refresh-code.sh §11 체인)
./infra/scripts/install-ste-tunnel.sh --check   # 터널 15810·15812 실측(없으면 ste 도구 8종이 안 뜬다)

# ── 재해복구: AIDataHub 를 Drive 덤프로 통째 교체(파괴적, 평소엔 불필요) ──
bash deploy/apptainer/sync-from-drive.sh
```

---

## 6. 주의 — 소스 검증 기준(런타임 미확인)

- 이 가이드는 **스크립트를 읽어** 검증했고, cae00 에서 실제로 돌려 확인한 것이 아니다. 종료코드·재프로비저닝·Drive 반입의 실제 성패는 박스 상태에 달렸다.
- **박스별(gitignore) 값은 이제 재서 안다** — `routes.local.env` 의 `ste=` 는 §1d 가 teleport 박스에 자동으로 적고,
  터널 구동은 `./infra/scripts/install-ste-tunnel.sh --check`(두 포트 실측)와 `./infra/scripts/ste-doctor.sh` 가 판정한다.
  ste 전반은 **`./infra/scripts/ste-doctor.sh --report`** 한 번으로 한 화면에 나온다. 아직 눈으로 볼 것: `provision.env`
  토큰, rclone remote, AIDataHub `.env` 의 실제 API 포트.
- **표식 셋을 섞어 읽지 않는다** — `✗` 만 종료코드를 세우고 끝에서 목록으로 다시 나온다 · `⚠` 는 경고(이 박스 대상이
  아닌 것·판정 불가) · `○` 는 "기능은 있는데 옵션·설정이 없어 안 켰다" 로 끝의 요약에 "켜려면" 과 함께 나온다.
  §1c 가 `.env.example` 의 새 키를 기존 `.env` 에 덧붙이는데, 비밀·자리표시자는 **주석으로만** 넣고 "값을 정해야 한다" 로
  보고한다 — 그 값이 비어 있는 동안 그 설정이 켜는 기능은 꺼져 있다.
- **그라운딩의 실제 전제 미확인**: cae00 AIDataHub 에 `xd-cae-*`(스파인 7석 + 발굴 대상) 전문가·records 가 실제 동기화돼 있는지 — 이게 그라운딩이 "빈 근거"가 아니라 실제 인용으로 채워지는 배포측 조건이다. 재기동·업로드·병합 후 §3 검증 방법으로 확인할 것.
- dev 에서 `backup-to-drive`/`export-*` 를 **크론으로 도는지 수동인지** 미확인 — 이 가이드는 명령만 정리했다.

## 2026-09-02 반영분 — update-all 후 확인·1회 조치

`git pull && update-all` 로 자동 반영되는 것.
- 심의 파이프라인 절단·유실 수정 전체(워크플로 JS 는 §1a 동기화, agent-server·게이트웨이는 §4).
- AIDataHub **데이터**(§3 병합) — `material-twin-analyst` 승격 페르소나, 물성 지식 41건 바인딩,
  재료 카드 2,688건. **dev 가 `backup-to-drive.sh` 로 올린 DB 덤프**(`AIDataHub/db-dumps` 의 `aidh-db-*.sql.gz`)를 §3 이
  `merge-from-drive.sh` 로 머지한다. `export-to-drive.sh` 의 sync JSONL(`AIDataHub/sync`)은 update-all 이 타지 않는 별도 채널이다.

1회 수동 조치(있다면).
- **cae00 AIDataHub 자체의 materialtwin 동기화 소스**: dev 에서 `page_size 50 × max_pages 50 = 2,500`
  상한에 걸려 카드가 2,500 에서 매번 끊기던 함정이 있었다(커서는 소진 전 미저장이라 매회 처음부터).
  cae00 이 자기 MaterialTwin 을 직접 동기화한다면 같은 함정이 있다 —
  `PATCH /api/sync/sources/<materialtwin id> {"page_size":100}` 한 번이면 된다(코드 무변경).
- `.mcp.json` 이 리포에 생겼다 — `export HWAX_GATEWAY_PAT=<PAT>` 없으면 hwax MCP 가 연결 실패로
  뜬다(조용히 없는 게 아니라 명확히 실패한다). CLAUDE.md 참조.

## 2026-09-03 반영분 — STE 웹 복구 + 로컬 계정·RA 연결

`git pull && update-all` 로 자동 반영되는 것.
- 이메일 로컬 계정(승인제 가입·/admin/users)·계정별 챗 캐시 분리·RA 연결 토큰 기능.
  프론트 dist 는 Drive `latest/` 에 있다(§ images-from-drive).
- 카탈로그가 routes.local.env 오버레이를 읽는다 — 아래 STE 복구의 전제.

**STE 웹 복구(1회 수동).** 8/25 커밋(419b5ec)이 base routes.env 의 ste 를 끄고 오버레이
방식으로 바꿨는데 cae00 에 오버레이가 없어, update-all 의 nginx conf 재생성 시점부터
/ste/ 가 사라졌다(웹 접속 두절 — 실사고). 타일도 이때부터 '준비중'으로 뜬다.

> **2026-09-25 이후 §1d 가 이 한 줄을 자동으로 적는다**(teleport 박스 · `HWAX_STE_AUTOROUTE=0` 으로만 끈다).
> 아래는 `transport.env` 가 없는 박스·direct 박스·자동 기록을 끈 경우의 수동 경로다.

```bash
cd ~/Projects/HWAXPortal
echo 'ste=http://127.0.0.1:15810/' >> backend/config/routes.local.env   # Teleport 터널(§5)
./infra/scripts/gen-nginx-conf.sh
# ⚠ -c 필수 — 없이 부르면 reload 프로세스가 기본 conf 의 pid 경로(/run/nginx.pid)를 봐서
#   "open /run/nginx.pid failed" 로 죽는다. 우리 conf 는 pid 를 /tmp 에 둔다(rootless).
apptainer exec instance://hwax_nginx nginx -c /workspace/infra/nginx/hwax.conf -s reload
systemctl --user status ste-tunnel   # 터널이 죽어 있으면 재기동
apptainer instance stop hwax_portal && ./infra/scripts/start.sh   # 타일 상태 반영(레지스트리)
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8088/ste/   # 200/401 이면 복구
```

**RA 연결 토큰(1회 — 스크립트가 양쪽을 배선한다, 멱등).**
```bash
./infra/scripts/wire-gateway-shared-token.sh   # backend/.env 없으면 만들고, 있으면 덧붙인다
```
- 이후 각 사용자: RA 프로필에서 토큰(rat_) 발급 → 포털 API 토큰 페이지 하단 카드에 등록.
  cae00 RA 가 `/api/me/mcp-tokens` 라우트(v0.157.x)를 갖고 있는지 확인 — 없으면 RA 재기동으로
  최신 코드 반영(dev 에서 실사고: 8/14 프로세스가 낡아 404, requirements 동기화 후 재기동으로 해소).

## 2026-09-04 반영분 — DynaForge 불안정 리포트 회신

cae00 리포트(§1~§5)에 대한 판정·조치. `git pull && update-all` 후 아래가 자동/수동으로 갈린다.

**판정 교정 2건(문제 아님).**
- "heax var/sifs·integration 로그 없음" — **설계다.** DynaForge 는 heax 통합 빌드가 아니라
  **자체 스택**(KooRemapper platform: 자체 SIF `platform/infra/apptainer/*.sif`, 자체
  supervisor, 자체 로그 `platform/data/`)이고, update-all(deploy-all §kooremapper)이
  git_update + dist-from-drive + start 로 이미 관리한다. 상태 확인 위치가 다를 뿐이다.
- "MCP 라우트 406(무인증 도달)" — 핸드셰이크·tools/list 는 열리지만 **실도구 호출은 앱
  자체 kr_ 토큰 인증이 거부함을 실측**(무토큰 list_sessions → '인증 토큰이 필요합니다').
  외부 MCP 클라이언트(허브 세션 불가)가 kr_ 만으로 붙게 하는 의도적 개방 — 노출은 도구
  목록 스키마 수준. 더 닫고 싶으면 별도 결정.

**자동 반영(이번 커밋들).**
- 간헐 다운의 본체 = **감독 부재**: deploy-all kooremapper 절이 이제
  `install-autostart.sh`(@reboot 크론+supervisor 감시, 멱등)를 설치한다(237c27e).
- `env: development` 의 본체 = .env 부재 시 example 복사: **example 기본을 production
  으로**(KooRemapper 96aa47f). 단 cae00 에 이미 생성된 platform/.env 는 안 바뀐다 —
  **1회 수동**: `KOORM_APP_ENV=production` 으로 고치고 재기동.
- `mcp_add_hint` 가 프록시 경유 접속에선 포털 고정 라우트
  (`https://<포털>/apps/kooremapper_mcp/mcp`)를 안내한다(KooRemapper 1f2c817).
  게이트웨이 등 직결 조회는 종전 로컬 주소 폴백 — 원하면 platform/.env 에
  `KOORM_MCP_PUBLIC_URL=` 로 못 박는다.

**신원(§5)** — 게이트웨이 per-user 위임은 이미 작동한다(등록 사용자는 본인 명의 응답 실측).
"전원 hwax.demo" 는 위임 결함이 아니라 **다들 데모 계정으로 로그인**한 결과다 — 포털
로컬 계정(각자 이메일 가입)으로 옮기면 그대로 각자 명의가 된다. kr_ 발급이 웹 전용인
것은 감독 편입으로 웹이 안정되면 충분하다.

**확인법(순서).**
```bash
crontab -l | grep koorm-autostart               # 감독 설치됨
pgrep -f 'supervisor.sh' >/dev/null && echo 감시중
curl -s http://127.0.0.1:8700/api/health        # api ok
# system_status 의 env 가 production (KOORM_APP_ENV 수동 조치 후)
```

## 2026-09-05 반영분 — /data 이관(옵트인, infra/.env 한 줄)

리포 안에 쌓이던 데이터(pg·sqlite·첨부·MinIO·JWT 키)를 `/data` 로 옮기는 이관기가 `update-all` 에 들어갔다.
**infra/.env 에 `HWAX_DATA_ROOT` 가 없으면 아무것도 하지 않는다**(종전과 동일). 켜면 update-all 의 `2b)` 단계가
아직 옛 경로에 있는 것만 골라 옮기고(멱등), 옛 경로는 심링크로 남겨 크론·워치독·수동 스크립트가 그대로 동작한다.
설계·근거는 `docs/data-migration/`(PLAN §2 원칙 D1~D12, §10).

```bash
cd ~/Projects/HWAXPortal
grep -E '^HWAX_(DATA_ROOT|BOX|BOX_ROLE)=' infra/.env        # 비어 있어야 정상(처음)
df -h /data && du -sh ../SignalForge/data/postgres ../AIDataHub/deploy/apptainer/data/postgres   # 여유 ≥ 합계 ×1.2
apptainer instance list | grep -cE 'postgres|heax-pg'         # pg 인스턴스가 떠 있어야 행수 대조가 된다(안 떠 있으면 그 서비스는 블로커로 건너뜀)
printf 'HWAX_DATA_ROOT=/data\nHWAX_BOX_ROLE=staging\n' >> infra/.env
git pull && ./infra/scripts/update-all.sh                    # 2b) 단계에서 서비스별 "이동 완료 (N클래스)" 확인
./infra/scripts/services.sh data --check                     # rc 0 · 옮긴 클래스가 same
```

서비스별로 **정지 → pre-move 백업(backup-local) → 복사·checksum 검증 → 옛 경로 rename+심링크 → 기동 → 행수 대조**
순이며 어느 단계든 실패하면 자동 롤백(`↩` 줄)하고 다음 서비스로 넘어간다. 정지 창은 서비스당 수 초~1분(dev 실측: 포털 9s·HEAX 48s·AIDH 9.8G 21s).
pre-move 백업은 1b) 가 방금 만든 덤프(3시간 이내)를 재사용하므로 두 번 덤프하지 않는다. 실행 동안 크론을 통째로 멈추고(워치독이 되살리지 않게) 끝나면 복원한다.

| 상황 | 할 일 |
|---|---|
| 일부 `✗ … 롤백` | 그냥 다음 `update-all` 에서 다시 시도된다(멱등). 원인은 출력의 ✗ 줄·`/data/hwax/state/data-migrate/journal.jsonl` |
| 무엇을 옮길지 미리 보기 | `./infra/scripts/data-migrate.sh plan` (변경 없음) |
| 특정 서비스만 되돌리기 | `./infra/scripts/data-migrate.sh rollback <svc>` |
| 강제 종료 뒤 크론이 비어 있음 | `./infra/scripts/data-migrate.sh resume-crons` (다음 run 도 자동 복원한다) |
| 옛 사본 정리 | `<옛경로>.pre-move-<TS>`·`<목표>.rolled-back-<TS>` 는 도구가 지우지 않는다 — 며칠 지켜본 뒤 사람이 `rm -r` |

옮기지 않는 것: 로그(logrotate 몫)·백업 디렉터리(backup-local 이 `/data/backups/hwax/<box>/` 에 이미 쓴다)·캐시·
SignalForge `reports/`·`audit/`(추적 파일 포함 — 심링크 불가, 등록만).

### 2026-09-05 실사고 — `HWAX_DATA_ROOT=data`(슬래시 없음)로 첫 실행

infra/.env 에 `/data` 가 아니라 `data` 가 들어갔다. 도구가 절대경로를 검증하지 않아 목표가 전부 `~/Projects/HWAXPortal/data/…` 상대경로로
계산됐고, 결과는 세 가지였다. ① 포털 `start.sh` 가 상대경로 `--bind` 를 만들어 apptainer 가 기동을 거부, 포털이 내려간 채 남음.
② mcp-gateway `audit.jsonl`·agent-server `artifacts` 가 허공을 가리키는 상대 심링크로 바뀜(agent-server 는 그 때문에 기동 실패 → 자동 롤백).
③ 리포 루트에 미추적 `data/` 트리가 생김. 이후 코드는 절대경로가 아니면 아무것도 하지 않고 rc 1 로 끝나며, start.sh 도 절대경로만 바인드한다.

**복구 순서**(update-all 이 아직 돌고 있으면 Ctrl-C 한 번 → `↩ 롤백`·`크론 복원` 줄을 기다린 뒤).

```bash
cd ~/Projects/HWAXPortal
# 1) 값 교정
sed -i 's|^HWAX_DATA_ROOT=.*|HWAX_DATA_ROOT=/data|' infra/.env && grep '^HWAX_DATA_ROOT=' infra/.env
# 2) 상대경로를 가리키는 심링크만 골라 .pre-move 원본을 제자리로(절대경로 심링크·일반 디렉터리는 건드리지 않음)
for f in ../HWAXMcpGateway/audit.jsonl ../HWAXAgentServer/artifacts \
         ../MXWhitePaper/infra/data/postgres ../MXWhitePaper/infra/data/minio \
         ../KooRemapper/platform/infra/data/postgres ../KooRemapper/platform/storage \
         ../HEAXHub/var/pg ../HEAXHub/var/app_data ../HEAXHub/job_storage ../SignalForge/data/postgres \
         ../AIDataHub/deploy/apptainer/data/postgres ../AIDataHub/deploy/apptainer/data/attachments \
         ../AIDataHub/deploy/apptainer/data/figures ../AIDataHub/api_server/mcp_uploads/_uploads \
         backend/data/users.sqlite backend/data/conversations.sqlite backend/secrets/agent_audit.sqlite backend/secrets/token_store.sqlite backend/secrets/jwt; do
  [ -L "$f" ] || continue
  case "$(readlink "$f")" in /*) ;; *) rm "$f" && mv "$f".pre-move-* "$f" && echo "복원 $f" ;; esac
done
# 3) 리포 루트에 생긴 상대 트리 — 원장만 /data 로 보존하고 제거(안 지우면 다음 deploy-all 의 git stash -u 가 통째로 stash 한다)
du -sh data; find data -type f | head -20
mkdir -p /data/hwax/state/data-migrate && cat data/hwax/state/data-migrate/journal.jsonl >> /data/hwax/state/data-migrate/journal.jsonl
rm -rf data
# 4) 내려간 서비스 기동·확인
./infra/scripts/services.sh up && ./infra/scripts/services.sh status
crontab -l | grep -cv '^\s*\(#\|$\)'          # 종전 줄 수(2)
# 5) 고친 코드로 다시
git pull && ./infra/scripts/data-migrate.sh plan   # 목표가 /data/... 절대경로인지 눈으로 확인
./infra/scripts/update-all.sh
```


## 2026-09-11 반영분 — HE팀 MCP 운영자 · 전문가 심층 보기 · 소속·허가 기반 접근

세 가지가 함께 들어간다. **반영 순서는 포털 → 에이전트서버 → 게이트웨이**다(게이트웨이가 포털에서
권한 정책을 받아 온다).

```bash
# ⚠ cae00 에서 `pnpm build` 를 돌리지 않는다 — npm 에 못 닿는다. 프론트는 dev 에서 빌드해 Drive 로 보낸 것을 받는다
#    (dev: pnpm build → build-all-to-drive.sh portal). cae00 은 git pull + update-all 이면 된다.
cd ~/Projects/HWAXPortal && git pull && ./infra/scripts/update-all.sh
# 게이트웨이 권한 정책이 붙었는지 — 무인증 /health 는 access_policy 본문을 더 이상 내지 않는다(적재 수만 낸다)
curl -s 127.0.0.1:9110/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print("정책 백엔드", d["access_policy_loaded"], "· ready", d.get("access_policy_ready"))'
```

**1) HE팀 페르소나 등록(ARP·ODB 포함).** cae00 게이트웨이에는 arp·odb-hub 가 붙어 있어 dev 에서
건너뛴 둘까지 생긴다.

```bash
cd ~/Projects/HWAXPortal
python3 infra/scripts/sync-he-personas.py            # 미리보기 — 무엇이 생기고 무엇이 바뀌는지
python3 infra/scripts/sync-he-personas.py --apply
```

ARP·ODB 페르소나의 사전 지식은 뼈대(매니페스트 설명 + 도구 지도)다. 실제 도구를 보고
`infra/personas/he-team.json` 의 workflow·pitfalls·key_tools 를 채운 뒤 다시 `--apply` 한다.

**2) 소속 지정 — 안 하면 기존 사용자가 일반 챗만 쓴다.** 권한 표의 **정본은 `backend/config/access.yaml`** 이다
(`default_grants: [feat:chat]` · 소속 `CAEG` 는 `grants: ["*"]` · `features`/`platforms`, 각 플랫폼의 `systems` 는 포털 타일,
`gateway` 는 게이트웨이 백엔드 키). 요청마다 mtime 을 보므로 표를 고쳐도 재기동이 필요 없다. **새 게이트웨이 백엔드·
타일·페르소나 앱은 이 표에 먼저 넣는다** — 표에 없는 백엔드는 "전체 공개" 로 판정된다. 권한 모델을 켜면 소속이 없는
사용자는 기본 권한(일반 챗)만 갖는다. 관리자로 로그인해 **사용자 관리** 화면 위쪽의
`소속 없는 활성 사용자 N명 → 모두 이 소속으로(CAE그룹)` 를 한 번 누른다. 다른 그룹(자주검증·
실장솔루션) 사람이 섞여 있으면 그 사람만 소속을 빼고 개별 허가로 필요한 것만 켠다.

**3) 서비스 PAT 계정 확인.** HWAXRisk 는 포털 PAT(`HWAXRISK_PORTAL_PAT`)로 게이트웨이를 부른다.
그 PAT 를 발급한 계정이 CAEG 이거나 관리자여야 도구가 보인다 — 게이트웨이가 PAT 에 박힌 값이
아니라 **그 계정의 지금 권한**을 쓰기 때문이다. 리스크 심사에서 조회가 비면 여기부터 본다.

**4) 확인.** 권한이 없는 계정으로 로그인해 심의 메뉴가 **안 보이는지**, `/deliberate` 가 내 권한
화면으로 가는지, 내 권한에서 요청→승인 뒤 새로고침 없이 메뉴가 뜨는지 본다.

## 2026-09-19 반영분 — 한글 이름 앱 접속 · StepForge 관통 신호 · SignalForge 주소 드리프트

**반영 순서는 포털 → 게이트웨이 → 허브(HEAXHub) → 앱 재배포**다. 포털이 먼저여야 게이트웨이가
절차 PAT 의 `purpose` 클레임을 받는다(그 반대로 하면 승인한 절차 단계가 승인 **뒤에** 막힌다).

```bash
# ⚠ cae00 에서 `pnpm build` 는 돌리지 않는다(npm 미도달) — 프론트는 Drive 아티팩트로 온다
cd ~/Projects/HWAXPortal && git pull && ./infra/scripts/update-all.sh   # 포털 dist 반입·재기동까지
cd ../HWAXMcpGateway && git pull && ./start.sh restart
cd ../HEAXHub && git pull && ./deploy/apptainer/start.sh      # rev 가 바뀌면 backend·celery 를 스스로 교체한다
```

**1) SignalForge 주소는 스스로 맞춰진다.** cae00 게이트웨이 설정이 8013 을 가리키는데 SignalForge 는
8008 에서 돈다 — 키가 있어서 `calc_missing` 이 못 보던 자리다. 이제 `update-all` 이 **선언(그 서비스의
`.env` 의 `MCP_PORT`)과 어긋난 주소**를 찾아 다시 프로비저닝한다.

```bash
cd ~/Projects/HWAXPortal && ./infra/scripts/update-all.sh
# 확인 — 아무것도 안 나오면 어긋난 것이 없다(종료코드 0)
cd ../HWAXMcpGateway && python3 provision_urls.py drift gateway_config.json "$(dirname "$PWD")"
curl -s 127.0.0.1:9110/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['tools'], [k for k,v in d['backends'].items() if not v] or '전부 정상')"
```

**2) StepForge 공개 주소는 이 박스에서 한 줄을 넣어야 한다(1회).** 값의 정본이 gitignore 된 호스트
`.env` 라 리포를 따라오지 않는다. 안 넣으면 앱이 내는 링크가 자리표시자로 나온다(앱은 "모른다"고
말하는 쪽이라 조용히 틀리지는 않는다).

```bash
cd ~/Projects/HEAXHub
echo 'APPTAINERENV_STEPFORGE_PUBLIC_BASE=<사용자가 실제로 접속하는 포털 주소>' >> .env
./deploy/apptainer/redeploy-app.sh step_forge --rebuild
# 들어갔는지는 컨테이너 프로세스로 본다(앱 헬스로는 안 보인다)
tr '\0' '\n' < /proc/$(pgrep -f 'root-path /apps/step_forge' | head -1)/environ | grep STEPFORGE_PUBLIC_BASE
```

⚠ `redeploy-app.sh` 는 이제 **스스로 `.env` 를 싣는다**(HEAXHub e994243). 예전에는 셸에서 바로 부르면
앱 env 가 조용히 빠진 채 멀쩡히 떴다 — dev 에서 실제로 났고, 컨테이너 environ 을 직접 보기 전까지
아무 신호가 없었다.

**3) 확인 — 화면이 아니라 도구 응답으로 본다.**

```bash
# 한글 이름 사용자로 로그인해 앱 화면(/apps/<앱>/)이 열리는지 — 예전에는 500 이었다
# StepForge: 간섭이 있는 과제에서 inspect_report 응답에 아래 세 칸이 있으면 반영된 것이다
#   tolerance_level_touching_candidates · tolerance_level_buried_suspects · worst_interference[].sliver_verdict
```

## 2026-09-26 반영분 — ste × cae00 1회 셋업 · 포털 TLS 판정 · 로그의 ○ 표식

앞선 절들과 달리 **이 절이 지금 기준이다**(그 위 날짜 절들은 그때의 기록이다). 배경은
`docs/ste-cae00/`(PLAN · checklist · context-notes D-13~D-21).

`git pull && update-all` 로 자동 반영되는 것.
- **새 단계 여섯** — 0a(`--with-<name>`) · 0b(flock, 겹쳐 돌리면 rc 3) · 1c(`.env` 새 옵션 채움) ·
  1d(ste 라우트 자동 기록) · 2c(ste 코드 최신화) · 3.5(agent-server `.env` 보정). §6 은 치명 항목이 늘었고
  끝에 **○ "있는데 안 켠 것" 요약**이 붙는다(실패가 아니다 — "켜려면" 이 함께 나온다).
- **ste 헬스게이트가 진짜로 판정한다** — 자격 중계는 시크릿 **실제 값**으로 `verify` 를 쳐서 204/401/404 를 가르고
  (종전엔 아무 값 401 을 "설정됨" 으로 읽어 불일치를 못 잡았다), ste MCP :15812 를 프로브하며, 게이트웨이 권한 정책
  미적재를 실패로 본다.
- **포털 TLS 판정이 바뀌었다** — `GET /tls/info` 가 `self_signed` 가 아니라 **`needs_ca`**(체인이 공개 루트에 닿는가)를
  낸다. 사내 CA 로 발급된 인증서도 개인 Claude(Node)는 못 믿으므로 같은 안내가 필요하다.

1회 확인·조치(cae00).

```bash
cd ~/Projects/HWAXPortal
./infra/scripts/install-ste-tunnel.sh          # 터널 유닛(15810·15812) 설치 — 이미 있으면 --check 만
./infra/scripts/update-all.sh --with-ste       # 1회 셋업: ste 코드까지 함께
./infra/scripts/ste-doctor.sh --report         # 한 화면 진단(JSON) — 출력을 docs/ste-cae00/context-notes.md §F 에 붙인다
curl -s 127.0.0.1:8088/tls/info | python3 -m json.tool   # needs_ca·ca_available·expired·verified
```

- `tls` 행이 **사설 CA 인데 발급 CA 체인 없음** 이면 개인 Claude 연결이 불가다 — `TLS_CERT_PATH` 를 **루트까지 포함한
  fullchain** 으로 두거나 `TLS_CA_PATH` 에 **발급 체인(중간 CA + 루트)** 을 준다. 리프 한 장이나 루트 하나만으로는 안 된다
  (서버가 중간 CA 를 보내지 않으면 Node 가 발급자를 요구한다 — 실측).
- 사용자의 개인 Claude 연결은 포털 **AI 토큰** 화면에서 끝낸다(토큰 + 배치파일). 판정이 안 되거나 체인이 없으면 그 화면이
  **등록 명령을 만들지 않고** 이유를 말한다 — 모르는 채로 만든 등록은 인증서가 빠지거나 검증 안 된 것이 들어간다.
- ste 도구가 보이지 않으면 순서대로: `ste-doctor.sh` 의 `mcp`(15812) → `gateway-ste` → `policy` → 사용자 권한
  (`plat:smarttwin`·`feat:api-token`). 권한 없는 앱은 목록에 없고 `denied_apps` 에 라벨·필요 권한·요청 경로만 나온다.

## 2026-09-27 반영분 — Report Archive 재연결(RA 가 포털 박스를 떠났다)

RA 가 새 서버쌍(A 주·B 대기)으로 이사했고 공개 주소는 `https://hwax.sec.samsung.net/report-archive/` 다(RA 요청서:
RA 리포 `docs/[참고] HWAX포탈_연동_요청서.md`, 포털 쪽 답과 결정은 `docs/ra-reconnect/`). **포털 운영자가 할 일은 값 하나다.**

```bash
cd ~/Projects/HWAXPortal && git pull
$EDITOR infra/.env            # RA_HOST=<RA 주(A) 서버 주소>   ← 요청서 §1. 호스트만(스킴·포트·경로 없이)
./infra/scripts/update-all.sh
```

`update-all` 이 그 값으로 자동으로 한다(**1e** 단계).
- `routes.local.env` 에 `report-archive=http://<RA_HOST>:3000/`(끝 `/` = 접두어 STRIP) → §2 가 nginx 를 다시 만든다.
  `loc_extras` 에 `report-archive` 가 들어가 첨부 1GB·AI 작성 10분·스트리밍이 통한다(413·504 방지).
- `backend/.env` 의 `RA_BASE_URL`, 게이트웨이 `provision.env` 의 `RA_MCP_URL` — §5 가 config 와 다르면 재프로비저닝한다.
- `services.yaml` 의 로컬 RA 두 항목(`report-archive`·`reportarchive-mcp`)은 `RA_HOST` 가 있는 박스에서 **이 박스 대상이
  아니다**(`unless_env`) — 스택 재기동이 **구 RA 를 되살리지 않는다**(두 DB 가 갈라지던 위험).
- **LLM 설정 정본 이관** — 포털 챗·심의·PaperIngest 는 LLM 주소를 형제 `ReportArchive/.env` 에서 상속했다. 1e 가 그 값을
  `infra/.env` 의 `LLM_BASE_URL·LLM_MODEL·LLM_API_KEY` 로 한 번 옮긴다. **이게 끝난 뒤에만** 구 RA 설치본을 지운다(RA 담당과 맞춘다).
- 타일은 다른 앱과 같은 **jwt-handoff** 다(`systems.yaml` 세 줄) — 포털 코드 변경 없음.
- 1e 가 끝에 **RA 담당에게 줄 JWKS 주소** 후보를 찍는다(요청서 §4-2, RA 의 `PORTAL_JWKS_URL`). 사내망 http(이 박스 :8088)가
  간단하고, 공개 https 를 고르면 인증서가 사내 CA·자체서명일 때 RA 서버에 `http://127.0.0.1:8088/tls/ca.crt` 의 체인을 둔다.
  인증서 종류는 `./infra/scripts/ste-doctor.sh` 의 `tls` 행 또는 `curl -s 127.0.0.1:8088/tls/info`.

확인(요청서 §8).
```bash
./infra/scripts/services.sh enabled report-archive; echo $?      # 1 = 이 박스 대상 아님(맞다)
curl -sI https://hwax.sec.samsung.net/report-archive/             # 200 text/html, 로그인 화면
curl -s  https://hwax.sec.samsung.net/report-archive/api/health   # {"status":"ok",...}
curl -s 127.0.0.1:9110/health | python3 -c 'import json,sys; print(json.load(sys.stdin)["backends"].get("reportarchive"))'   # True
grep -c FROM_RA ../HWAXAgentServer/.env                          # 0 — 마커가 값으로 치환됐다
```
- 타일을 눌러 로그인 화면 없이 RA 로 들어가면 SSO 끝. 안 되면 RA 쪽 `PORTAL_JWKS_URL` 부터(요청서 §4-3).
- **B 로 넘길 때**(요청서 §5): RA 담당이 B 의 DB 를 승격한 뒤, 포털은 `infra/.env` 의 `RA_HOST` 를 B 주소로 바꾸고
  `update-all` — 라우트·`RA_BASE_URL`·`RA_MCP_URL` 셋이 함께 따라간다. 되돌리기도 그 한 줄이다.
- `RA_HOST` 를 비워 두면 종전대로 "같은 박스의 :3000" 이고 ○ 요약에 "Report Archive 원격 재연결 — RA_HOST 미설정" 이 남는다(dev 는 그것이 정상).
- **ste 배포가 "커밋 체크아웃 실패" 로 멈추면**(2026-09-27 실측) — 배포용 사본 `~/SmartTwinExplorer` 의 작업트리가 더럽다.
  `git -C ~/SmartTwinExplorer status --short` 로 보고 `git -C ~/SmartTwinExplorer stash push -m manual`(추적 파일만 — `-u` 는 설치기 입력 `cluster.prod.yaml` 같은 미추적 운영 파일까지 담는다. 이미 담았으면 `git -C ~/SmartTwinExplorer show 'stash@{0}^3:cluster.prod.yaml' > ~/SmartTwinExplorer/cluster.prod.yaml` 로 꺼낸다) 뒤 `./infra/scripts/deploy-ste.sh`
  를 다시 돌린다(한 번뿐 — 새 판의 §3 은 스스로 치우고 git 의 사유를 보인다). 15812 가 000 인 것도 같은 원인이다(헤드의
  `ste-mcp.service` 는 배포가 만든다).
- **HTTPS 자체는 포털 nginx 가 종단한다** — `infra/.env` 의 `ENABLE_TLS=true` 일 때만 :443 서버 블록이 생긴다(기본 false). 공개 https 로
  갈 박스는 넷을 같이 둔다: `ENABLE_TLS=true` · `TLS_CERT_PATH=infra/tls/<fullchain>.crt`(**리포 루트 상대경로** — 절대경로는 nginx 컨테이너에
  안 보여 즉사, 생성기가 막는다) · `PUBLIC_BASE_URL=https://hwax.sec.samsung.net` · `COOKIE_SECURE=true`. 어긋나면 `/health/ready` 의
  `temporary` 에 `cookie_scheme` 이 실리고 `ste-doctor` 의 `https` 행이 빨강이다. 인증서가 없으면 `start.sh` 가 **자체서명을 만들어 띄운다** —
  정식(사내 CA) 발급본을 `infra/tls/` 에 넣고 재기동해야 `tls` 행이 "공개 CA" 또는 "체인 준비됨" 이 된다.
