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
- **AI Ready Portal(ARP)** 도 같은 방식이다 — `infra/.env` 에 `ARP_HOST=<ARP 서버 주소>`(포트가 3001 이 아니면 `ARP_PORT`)를 두면
  **1f** 가 포털 타일 주소(`backend/config/systems.local.yaml` 의 `arp`)와 게이트웨이 `provision.env` 의 `ARP_BASE` 를 같이 적는다
  (§5 가 게이트웨이 config 의 arp 주소가 다르면 재프로비저닝). 타일은 직결 링크 그대로다 — 포털 경유(`/arp/`)는 보류(docs/arp-binding).
  ⚠ **2026-10-08 — 이 문단의 타일 부분은 대체됐다.** 1f 는 더는 `systems.local.yaml` 에 쓰지 않고(그 `arp:` 블록은 쓰이지 않는다), 타일은
  포털 경유(`/aireadyportal/`)다. 게이트웨이 `ARP_BASE` 를 적는 것은 그대로다. 지금 기준은 아래 「2026-10-08 반영분」이다.
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

## 2026-10-08 반영분 — 심의 엔진 변경 · 8·9·10차 변경 요청

단계별 절차는 [change-request-8-10/server-setup.md](change-request-8-10/server-setup.md) 다. 이 절은 무엇이 왔는지와 건너뛰면 아픈 것만 적는다.

- **온 것** — 심의 엔진(근거 합계 예산 · 동시 실행 대기 줄 · 봉인 실행), 관리자 판정을 원장과 `PORTAL_ADMIN_EMAILS` 로만, SSO 첫 로그인의 소속
  자동 지정(`access.local.yaml`), 부서 코드·사번 Claim, 내부 목적지 `NO_PROXY` 자동 더하기, 게이트웨이의 옛 항목 걷어내기, ARP 타일의 포털 경유 로그인.
- **반영은 `update-all` 한 번이지만, 돌리기 전에 절차서 §1 의 확인 열둘을 먼저 한다.** 실행 뒤에 읽으면 늦다 — 도는 심의가 끊기고
  (에이전트서버가 다시 뜬다), 깨진 `access.local.yaml` 은 포털이 뜬 뒤 요청을 전부 실패시키며, ARP 주소가 게이트웨이 설정에만 있으면
  주소째 지워지고, 토큰에 박힌 관리자 표지로만 전권이던 옛 토큰은 권한을 잃는다.
- **ARP 는 시각을 맞춘다.** `routes.local.env` 에 `aireadyportal=` 줄이 있는 채 포털이 다시 뜨는 순간부터 타일 클릭이 ARP 로 로그인
  토큰을 보낸다. ARP 쪽이 준비되기 전이면 그 줄을 빼고 반영한다(타일이 숨는다). 종전의 직결 타일은 어느 쪽이든 사라진다.
- **같은 실행에 「시간 제한을 넉넉하게」도 온다.** 긴 심의·리스크 심사 경로의 시간 제한을 층으로 맞췄다 — LLM 호출 시도당 1800초 · 도구 호출 600초 ·
  리스크 패널 12시간 · 챗 토큰 24시간, 엔진은 조용한 동안 15초마다 신호를 흘린다. 전부 코드 기본값이라 적을 것은 없다. 층·손잡이·적는 곳은 절차서 §4-8 이다.
- **그 묶음 때문에 실행 전에 볼 것 셋**(절차서 §1 확인 9~11) — 에이전트서버 `.env` 에 옛 키트가 심은 `DELIB_TIMEOUT_S=600` 이 있으면 지운다(안 지우면 새
  기본값이 이 박스에만 안 먹는다) · 절차 원장에서 선언한 상한(30초·110초)보다 오래 걸린 단계를 찾는다 · 포털 대화 저장소가 로컬 디스크인지 본다.
- **심의가 도는 동안에는 update-all 이 포털·nginx·HEAX Hub 재기동(새 앱 SIF 받기 포함)·에이전트서버 재기동과 게이트웨이 재프로비저닝을 미루고 `○` 로 남긴다**(강행은 `AGENT_RESTART_FORCE=1`).
  단 이번 첫 실행은 떠 있는 에이전트서버가 옛 판이라 그 보호가 걸리지 않는다 — 도는 심의가 없을 때 돌린다.

## 2026-10-17 반영분 — 업데이트 리뷰 후속 · 사용자 결정

단계별 절차는 [followups-1017/server-setup.md](followups-1017/server-setup.md) 다. 이 절은 무엇이 왔는지와 이 박스의 설정 판단만 적는다.

- **온 것** — 서비스 로그 덧붙여 쓰기(700 · 600) · 게이트웨이 로그의 토큰 가림 · AIDataHub 병합이 빠진 열을 알리고 다시 병합 · 레코드 m3
  시그니처 병합 · 이행 전 쉬는 트랜잭션 표시 · 챗 LLM 401 · 403 · 첫 조각 전 멈춤도 GLM 으로 · HEAX 앱 데이터 병합의 SQLite 부속 파일 · 통합
  앱 기동 실패 억제 · Caddy 로그 회전 · 리스크 앱 암호 백업(박스별 칸) · MXWP 갱신이 남의 인스턴스를 내리지 않음 · 설정 킷의 사내 주소 제거.
- **사람 몫** — 옛 자동 stash 정리 · AIDataHub PG 30분 시한 · AIDataHub 를 루프백으로 · 리스크 백업(age · 공개키 · 크론) · `cred.key` 정리 ·
  **11-14 전** stcx LLM `rolling`(절차서 1~5절).
- **이 박스의 설정 판단(10-17 사용자 결정)** — 리뷰 D1~D7 중 지금은 바꾸지 않는 것.
  - **VOC 수집은 dev 만** — 이 박스에는 Redis 가 없어 SignalForge 수집 · 알림(celery)이 돌지 않는다(D2). VOC 는 dev 병합으로 온다(10-17 +5,019).
    합치기의 'dev 가 이긴다' 규칙이 이 상태에 맞다. 여기서 수집을 켜려면 Redis 와 SignalForge `.env` 의 비밀번호가 함께 있어야 한다.
  - **SignalForge REST 중계는 쓰는 곳이 생길 때 키를 넣는다**(D1) — `SignalForge/.env` 의 `API_KEY` 가 코드 기본값이라 게이트웨이 `rest_call`
    의 `/api/v1/*` 가 전부 401 이다. MCP 도구 35종은 정상이고 REST 호출 기록은 0 이다. 열 때는 실제 키 → SignalForge API 재기동 → update-collab.
  - **AIDataHub 내부 동기화 3건은 그대로 멈춰 둔다**(D3) — 데이터는 Drive 병합으로 온다. 이제 막힌 사유가 원장 `last_status='blocked'` ·
    `last_error` 에 남는다(예전엔 'ok' 그대로였다).
  - **포털 메일은 SMTP 값이 있어야 켠다**(D6) — `MAIL_BACKEND=smtp` · `SMTP_HOST` · `MAIL_FROM`. 상태판 경보도 그것이 있어야 켜진다.

## 2026-10-25 반영분 — MX 백서 위키 · DocForge · StepForge · DynaForge, 돌리기 전 점검

10-17 뒤로 쌓인 변경(MX 백서 위키 · SSO 전용 · 위임, DocForge 정밀 변환, 심의 운영, 챗 자기검증 · PPT · 생각 깊이, StepForge 견주기 도구,
DynaForge 감시 수리, 배포 길 고침)을 이 박스가 한 번에 받는 순서다. 무엇이 달라졌는지는 포털 `/updates`, 기능별 절차는 끝의 표가 정본이다.

### 0. 사전 점검 — 읽기만 한다

```bash
cd ~/Projects/HWAXPortal && git fetch -q origin main && git show origin/main:infra/scripts/update-preflight.py | python3 -
```

- 받기 전의 박스에서 원격 판을 그대로 돌린다(작업 트리는 안 바뀐다). 받은 뒤에는 `python3 infra/scripts/update-preflight.py`.
- 보는 것 — 끊길 일(심의 · 카드 대조 · DynaForge · StepForge · DocForge · 위키 작업), update-all 이 치우거나 지우는 것(git 이 모르는 파일 ·
  로컬 커밋 · 들어올 DB 이관 · MX 백서 이관 0056 이 지울 줄 수 · 디스크), 새 기능에 빠진 설정(비밀은 해시 앞자리로만 견준다), Drive 에 이 박스가
  받을 판(포털 화면 · MX 백서 이미지 · 허브 대조 목록).
- 종료코드 1(✗)이면 그 줄의 할 일을 하고 다시 돌린다. ⚠ 는 읽고 판단한다.
- **가장 큰 것 — 포털 타일 목록 `backend/config/systems.cae00.yaml`.** `backend/.env` 의 `CATALOG_PATH` 가 가리키는 이 파일을 git 이 모르면
  update-all 첫 단계(§1)의 `git stash -u` 가 작업 트리에서 치우고, 포털은 카탈로그를 못 읽어 뜨지 못한다. 점검이 ✗ 로 알리고
  `.git/info/exclude` 에 넣는 명령을 같이 보인다. 이번 판부터 `.gitignore` 에 `backend/config/systems.*.yaml` 이 있지만, 첫 실행의 stash 는
  옛 `.gitignore` 로 돈다. 점검 없이 돌려 포털이 안 뜨면 `git show 'stash@{0}^3:backend/config/systems.cae00.yaml' > backend/config/systems.cae00.yaml`
  로 되살리고 포털을 다시 띄운다.

### 1. dev 에서 먼저 — 이 박스가 받을 판(10-25 에 올렸다)

| 무엇 | 상태(10-25, 사용자 지시 「SIF 전달이 잘 안되던 건 다 최신본이 가게」) |
|---|---|
| 포털 화면 · 이미지 | 올림 — Drive 빌드 표지 = `origin/main:frontend`(a4feb335c0). 안 올렸으면 update-all §6 이 'SPA dist 가 지금 소스와 다르다' 로 실패했다 |
| MX 백서 이미지 web · api · wiki | 올림(`images-20261025-022913Z`) — 그때까지 latest/ 에 api · wiki 가 한 번도 없었고 web 은 09-13 판이었다. MX 백서 세션이 세 판을 확인했다 |
| StepForge SIF | 올림(`main` 끝 b8481c4 판, 되돌리기 `dist-20261025-022757Z/`) |
| voice-recorder SIF | 올림(`main` 끝 cd6970d 판, 되돌리기 `dist-20261025-023703Z/` — 그 전 Drive 판은 07-30) |
| DocForge 베타(0.3.0) | 남음 — 등록이 draft 라 게이트웨이에 안 실리고 포털 「정밀 변환」 목적지는 숨는다(오류는 아니다). DocForge · 허브 주인 몫 |

허브 앱이 이 박스에서 뜨는 조건 — 허브는 앱 소스를 매니페스트의 `source.ref` 에서 받는다. 커밋이 그대로이고 그 커밋으로 성공한 기록이
있으면 받은 SIF 로 그대로 띄운다. 커밋이 바뀌면 캐시 열쇠 `sha256(커밋 + 등록 사본 + 틀)` 을 받은 SIF 의 `.sif.hash` 와 견주고, 다르면
다시 지으려다(이 박스는 못 짓는다) 실패해 **그 회차엔 앱을 띄우지 않는다** — 허브가 다시 뜨면 그 앱은 꺼진 채 남는다. 그래서 앱 리포에
문서만 올려도 dev 가 다시 지어 Drive 로 보내야 한다. dev 에서 `./infra/scripts/drive-drift.sh heax` 가 10-25 부터 이 열쇠까지 견준다.
- MaterialTwinWeb — dev 리포가 GitHub 보다 61커밋 앞이다(09-05 뒤 push 안 함). dev 허브는 로컬 리포에서 받아 지었고 이 박스는 GitHub 을
  받는다. 지금은 커밋이 그대로라 받은 SIF 로 뜨지만, GitHub `main` 이 지은 커밋(a3563b6)이 아닌 곳으로 움직이면 뜨지 못한다. push 는
  사용자 결정 대기다(실을 범위). 다시 쓴 커밋을 올리게 되면 dev 가 그 커밋으로 지은 SIF 를 Drive 에 먼저 올린 뒤 push 하고, 이 박스의
  update-all 은 그 뒤에 돌린다. 허브 SIF 는 앱 리포의 추적 파일을 통째로 담는다 — 리포에서 무엇을 빼기로 하면 GitHub 만이 아니라 SIF
  (Drive `latest/` · Drive 휴지통의 옛 묶음 · 이 박스의 `var/sifs` 와 Drive 받기 캐시)도 다시 지어 갈아 끼우거나 지워야 한다.
  앱 DB 의 글(노트 · 설명)은 데이터 허브 카드로 내보내져 AIDataHub DB · Drive 매일 덤프(휴지통 포함) · 이 박스의 병합으로 간다 — 리포만
  정리해서는 걷히지 않는다(앱 DB 를 고치고 허브를 다시 맞추며, 지난 덤프는 따로 다룬다).
- SignalForge 화면 이미지(07-20)에는 '포털 밖 직접 접속 프록시'(08-28)가 없다 — 포털로 쓰는 데는 상관없다(SignalForge 몫).

### 2. 이 박스에서 돌리기 전 — 사람

1. 사전 점검 ✗ 0.
2. 도는 일이 없을 때 돌린다. 새 판(§1 이 포털을 받은 뒤 새 update-all 로 다시 돈다)은 DynaForge 로컬 작업이 돌면 그 재기동만 미룬다(○).
   떠 있는 에이전트서버가 10-22 전 판이면(10-17 갱신 뒤 그대로면) 심의가 돌 때 에이전트 재기동을 미룬다(○) — 그때는 끝난 뒤 한 번 더 돌린다. StepForge · DocForge
   작업은 허브가 다시 뜨면 끊긴다(막는 장치가 없다).
3. 에이전트서버 `.env` — 챗 자기검증은 기본 켜짐이다(모든 챗 답에 검토 호출이 하나 더 붙는다). 끄려면 `CHAT_SELF_CHECK=0`.
   `LLM_CONTEXT_TOKENS` 는 이제 상한이다 — 서버 창보다 작게 적혀 있으면 창이 그만큼 준다(점검이 견준다, 정본은 [delib-ops/server-setup.md](delib-ops/server-setup.md) §2).
4. 게이트웨이 `provision.env` 에 `HEAX_MCP_TOKEN` 고정을 권한다 — 없으면 재프로비저닝마다 허브에서 새로 발급한다(10-25 판부터 발급이 실패하면 앞 토큰으로 잇는다).
5. 디스크 — `/tmp` 12GiB 이상(AIDataHub 병합이 Drive 덤프 11GB 남짓을 `mktemp -d` 로 받는다).
6. MX 백서 사람 명의 위임은 그쪽 위임 창구(`POST /api/v1/auth/sso`)가 이 박스에서 답한 뒤에 켠다 — [mxwp-wiki/PLAN.md](mxwp-wiki/PLAN.md) §6 의 순서
   (MX 백서 `.env` → MX 백서 재기동 → `provision.env` → update-all). 두 곳의 `MXWP_SSO_SECRET` 이 다르면 신원 있는 MX 백서 호출이 전부 실패한다(점검이 해시로 견준다).

### 3. 도는 동안 — 이렇게 나오면 정상

- `○ kooremapper 재기동` — DynaForge 로컬 작업이 돌았다. 코드 · 배포물은 받았고 서버는 옛 것 그대로다. 끝난 뒤 한 번 더 돌린다.
- MX 백서 이관이 0056 을 지나면 짝 없는 `doc_triples` 를 지운다(점검이 센 수 — §1b 의 배포 전 백업에 남는다).
- MX 백서 이관 뒤 `migrate.sh` 가 restricted 거르기 재색인을 한 번 돈다(표지 `infra/data/.reindexed-audience-v1`). 0050 이 만드는 소속 → 팀
  표는 비어 있어, 관리자가 채우기 전엔 진입 때 팀이 옮겨지는 사람이 없다(MX 백서 세션 확인 — 이관 0050~0058 에서 데이터를 지우는 것은 0056 하나).
- 새로 실패로 세는 것 — DynaForge 배포물 받기 실패 · MX 백서 DB 이관 실패. 예전엔 경고만 남기고 초록으로 끝나 옛 화면 · 옛 스키마로 돌았다.

### 4. 돌린 뒤 — 확인 · 한 번만 하는 일

- update-all 끝 요약 ✗ 0, §6 의 `SPA dist 가 지금 소스와 같다` ✓.
- 게이트웨이 `curl -s --noproxy '*' localhost:9110/tools-map` — StepForge(다른 앱과 겹치는 이름은 `heaxstep_forge_` 접두가 붙는다) · DynaForge 리포트 도구 ·
  MX 백서 `wiki_*`, DocForge 베타 뒤엔 `docforge_*` 다섯.
- 페르소나 동기화(update-all 은 안 한다) — `python3 infra/scripts/sync-he-personas.py` 미리보기 → `--apply`. MX 백서 운영자
  (`he-doc-mxwhitepaper`), DocForge 가 실린 뒤엔 `he-doc-docforge`.
- `systems.cae00.yaml` 의 `mx-white-paper` 에 `claims_affiliation: true` — 없으면 타일 진입이 MX 백서에 소속을 싣지 않아 위키 소속 범위가 안 선다(점검이 본다).
- 계정 원장(`users.sqlite`)이 644 면 `chmod 600` — 외부 연결 토큰이 평문으로 든다.
- DocForge 를 쓰게 되면 [doc-to-ra/server-setup.md](doc-to-ra/server-setup.md) §1 의 `APPTAINERENV_DOCFORGE_INPUT_ROOTS` 와 Docling 모델(한 번).

### 5. 기능별 절차(정본)

| 기능 | 절차 |
|---|---|
| MX 백서 위키 · SSO 전용 · 사람 명의 위임 | [mxwp-wiki/PLAN.md](mxwp-wiki/PLAN.md) §6 · MXWhitePaper `docs/llm-wiki/START.md` |
| DocForge 정밀 변환 | [doc-to-ra/server-setup.md](doc-to-ra/server-setup.md) |
| 심의 운영(새 심의 멈춤 · 이어하기 · 한도 · 창 상한) | [delib-ops/server-setup.md](delib-ops/server-setup.md) |
| 챗 자기검증 · PPT · 생각 깊이 | [chat-self-check/PLAN.md](chat-self-check/PLAN.md) · [chat-ppt/PLAN.md](chat-ppt/PLAN.md) · [chat-depth-context/PLAN.md](chat-depth-context/PLAN.md) |
| 챗 LLM(stcx) · 임베더 BGE-M3 | [chat-llm-stcx/server-setup.md](chat-llm-stcx/server-setup.md) · [embedder-bge-m3/server-setup.md](embedder-bge-m3/server-setup.md) |
| 리스크 심사 20만 창 | [risk-200k/server-setup.md](risk-200k/server-setup.md) |
| 외부 연결(`connect:`) · 사람별 연결 | [sso-delegation/server-setup.md](sso-delegation/server-setup.md) C · D |
| 10-17 후속(사람 몫) | [followups-1017/server-setup.md](followups-1017/server-setup.md) |

## 2026-10-28 반영분 — 10-27 수정 요청(포털 몫)

요청서 · 결정 · 진행은 [request-1027/](request-1027/)(01 포털 · 02 게이트웨이 · 03 에이전트서버 — 고침, 07 리스크 앱 · 10 AIDataHub — 검토만)이 정본이다.
받는 길은 그대로 `git pull && update-all` 이다. 아래는 받은 뒤 **사람이** 할 일과 확인만 적는다(항목이 들어올 때마다 덧붙인다).

### 받은 뒤 — 사람

- **`/ste/` 읽기 시한(HP-12 · OB-80)** — `infra/.env` 에 `NGINX_STE_READ_TIMEOUT=3600s` 한 줄을 넣는다. 그 뒤 update-all(또는 restart.sh)이
  conf 를 다시 만들 때마다 그 값이 들어간다 — conf 에 3600s 를 손으로 다시 넣던 일을 멈춘다. 확인 `grep -n 'proxy_read_timeout' infra/nginx/hwax.conf`
  (`/ste/` 블록 둘 — HTTP · TLS).
- **`/ste/` 결과 파일 제한(HP-47 · 결정 D-6)** — 기본 끔이다. 한 클라이언트가 큰 결과를 되풀이해 받아 다른 사용자가 느려지면 `infra/.env` 에
  `NGINX_STE_RESULT_RATE=20m`(연결 하나의 속도) · `NGINX_STE_RESULT_CONN=2`(한 주소의 동시 수, 넘으면 429) 가운데 필요한 것을 넣는다.
  결과 파일(`result.zip` · `result/file/…`)에만 걸린다.
- **박스 crontab 맨 위 두 줄(XDG_RUNTIME_DIR · DBUS_SESSION_BUS_ADDRESS, OB-75)은 아직 둔다.** 백업은 이제 두 변수를 스스로 채우지만(HP-04),
  감시(`services.sh heal`)는 채우지 않는다. 걷기 전에 크론과 같은 빈 환경에서 감시가 인스턴스를 띄우는지 본다 —
  `env -i HOME="$HOME" PATH=/usr/bin:/bin ./infra/scripts/services.sh heal`.

- **HE팀 운영자 동기화(정본이 바뀌었다 — MX 백서 운영자)** — update-all 이 끝난 뒤 `python3 infra/scripts/sync-he-personas.py` 미리보기 →
  `--apply`. 위키가 꺼진 이 박스에서는 MX 백서 운영자가 위키 몫 없이 만들어진다(미리보기에 '· 일부 … wiki_ask 없이' 한 줄). update-all 은
  AIDH 를 합친 뒤 같은 미리보기를 돌려 이 박스 판과 다르면 ⚠ 로 알린다(HP-35).
- update-all §6 에 `○ 사람별 위임 <앱> 비밀 대조` 가 나오면 그 앱에 verify 창구가 없다는 기록이다(오류 아님). `✗ … 비밀이 상대와 다르다` 면
  그 앱의 위임 비밀과 `HWAXMcpGateway/provision.env` 의 `<접두>_SSO_SECRET` 을 맞춘다(HP-26).

- **게이트웨이(02 요청서) — 할 일 없음, 확인만.** 손잡이는 전부 기본값으로 켜져 온다(게이트웨이를 띄우는 셸의 환경에서만 읽는다 — `.env` ·
  `provision.env` 는 읽지 않는다). 개인정보 가림(HG-20)을 급히 꺼야 하면 그 환경에 `GATEWAY_PII_MASK=0` 을 주고 게이트웨이만 다시 띄운다.
  재기동 비우기 한도는 `GATEWAY_DRAIN_TIMEOUT`(30초) · `GATEWAY_SHUTDOWN_TAIL`(5초)이다.
- **ODB 토큰 헤더(HG-02 · HP-28)** — update-all §5 에 `· 옛 꼴 바꾸기: odb-hub …` 가 한 번 나오고 재프로비저닝이 돈다(정상). 그 뒤 모양만 본다(값은
  찍지 않는다, 포털 리포에서) — `python3 -c 'import json;d=json.load(open("../HWAXMcpGateway/gateway_config.json"))["odb-hub"];print("token=" in d["url"], "Authorization" in (d.get("headers") or {}))'`
  → `False True`. `/health` 의 odb-hub 가 정상이고, 사람별 위임이 켜져 있으면 감사 줄이 as-user-pat · 본인 이메일이다.
- **Desktop 패널(HG-07)** — Claude Desktop 을 `/mcp-gw/mcp` 로 붙여 `open_workflow_panel` 을 부르면 패널이 뜨고 `ui/initialize` 가 끝난다. 패널의
  `tools/call` 이 그 사람 명의(감사 as-user-pat)로 SimFlow 에 닿고 `ui/open-link` 가 된다. 안 뜨면 게이트웨이 로그의 `ui 리소스 목록을 받지 못했다` ·
  `ui 리소스 … 함께 낸다` 를 본다.

- **포털 4절(업로드 · 화면 · 그 밖) — 화면은 Drive 판에 들어 있다.** 받은 뒤 사람 몫과 확인.
  - **연결 토큰 암호화(HP-05 · 결정 D-5)** — 할 일 없음. 포털이 처음 뜰 때 키 `backend/secrets/conn.key`(0600)를 만들고 옛 평문 행을 제자리에서
    바꾼다 — 포털 로그 `연결 토큰 N건을 암호문으로 바꿨다`. 포털 sqlite 는 뜰 때마다 `0600`(-wal · 링크 대상까지 — 종전 '644 면 chmod 600' 손질은
    필요 없다). 키는 **비밀 묶음**에만 든다(`portal/backend/secrets/conn.key`) — 다음 날 비밀 묶음 목록에서 본다. 키를 잃으면 기동 로그가
    `연결 토큰 N건을 풀 수 없다` 로 말하고 그 사람들은 '외부 연결' 에서 다시 등록한다(비밀 묶음에서 키를 되살리면 풀린다).
  - **SimFlow 업로드 목적지(HP-15)** — SimFlow 가 게이트웨이에 붙은 이 박스에서만 보인다. 확장자 · 한도는 SimFlow 쪽 답(PA-12) 전이라 기본
    `x_t` · 500 MB 다 — 답이 오면 포털 `backend/.env` 에 `SIMFLOW_UPLOAD_EXTS=x_t,x_b,…` · `SIMFLOW_UPLOAD_MAX_MB=…`(DRM 해제 기다림은
    `SIMFLOW_READY_WAIT_S`, 기본 120)를 적고 포털만 다시 띄운다. 첫 실주행이 SimFlow 계약(업로드 응답의 id · status 칸, 상태 조회
    `GET /api/v1/mcp-uploads/<id>`)의 확인이다 — `.x_t` 를 올려 목적지에 SimFlow 가 보이고, 받은 id 로 `run_workflow` 가 돌고, 게이트웨이 감사의
    그 줄이 `mode=as-user-pat` 인지 본다. 어긋나면 화면에 SimFlow 응답 그대로가 나온다 — 그 문구를 dev 에 보낸다.
  - **RA 보내기 한도(HP-02)** — 기본 25 MB(실측 26.2 MB 통과 · 27.5 MB 거절). RA 회신(RP-16)으로 값이 정해지면 포털 `backend/.env` 의
    `RA_IMPORT_MAX_MB` 한 줄(0 = 끔).
  - **AIDH inbox 옛 사본(HP-29 · OB-10)** — 이제 보낸 사본은 장부에 적고 24시간 뒤 지운다. 이 판 **전에** 쌓인 `~/aidh-inbox` 의 파일은 장부에 없어
    지워지지 않는다 — 한 번 손으로 치운다(지금 보내는 중인 것이 없을 때, `find ~/aidh-inbox -type f -mtime +1` 로 먼저 본다).
  - **HE팀 운영자 — 이름 넷 · 코어 온톨로지 운영자(HP-19 · HP-20)** — 위의 동기화 미리보기 → `--apply` 한 번에 함께 든다. 미리보기가 exit 2 없이
    `+ he-data-coreontology 새로 만든다` 를 내야 한다(허브 셋이 붙은 이 박스). FailureTrace · CAE 그룹 허브가 해석 도구(object_resolve)를 내지 않으면
    '· 일부 … 없이 만든다' 한 줄이 나온다(정상).
  - **떠 있는 값 확인(HP-40)** — `claims_affiliation` 은 update-preflight 가 **파일**을 본다. 떠 있는 값은
    `curl -s --noproxy '*' localhost:8723/health/ready` 의 `claims_affiliation` 이 `["mx-white-paper"]` 다(박스 파일이 덮은 뒤의 값). 챗 업로드 길의
    생존은 `curl -s -o /dev/null -w '%{http_code}\n' --noproxy '*' -X POST localhost:8723/agent/upload` 와 `…/agent/upload/dispatch` 가 `401`(세션
    없음 — 길은 있다)이다. `/agent/upload/destinations` 는 없는 경로(404)이고 `/upload/analyze` 는 물성 CSV 미리보기라 생존을 보지 못한다.
  - **update-all §7 새 줄** — `· 챗 자기검증: …`(HP-24 — 실패가 있으면 ⚠). MCP 스모크가 예상하지 못한 오류로 멈추면 이제 `스모크를 돌리지 못했다(rc=2)`
    ✗ 로 남고 재프로비저닝을 돌리지 않는다(HP-44) — 그 줄이 나오면 스모크 출력의 `✗ 스모크가 예상하지 못한 오류로 멈췄다` 를 dev 에 보낸다.

### 다음 날 확인

- `/data/backups/hwax/<박스>/backup.log` 에 `kooremapper → kooremapper-…sql.gz` 가 있다(HP-04 — 10-02 부터 매일 실패하던 덤프).
- 비밀 묶음을 열어 본다 — `tar -tzf "$(ls -t /data/backups/hwax/<박스>/secrets/daily/secrets-*.tar.gz | head -1)"` 에 `portal/infra/.env` 와
  `portal/backend/.env` 가 따로 있고, `portal/backend/config/`(systems.cae00.yaml · access.local.yaml …) · `portal/.git/info/exclude` ·
  `crontab/crontab.txt` · `heax/hwax_risk/secrets.env` · `origin.json` 이 든다(HP-17).
- 크론 설치기(백업 · 감시 · 로그 회전)는 crontab 을 못 읽으면 쓰지 않고 ✗ 로 멈춘다(HP-18) — update-all 1b 에 ⚠ 가 나오면 `crontab -l` 을 직접 본다.

## 2026-10-29 반영분 — 10-29 웹 챗 온톨로지 QA 후속(1차)

요청서 · 계획 · 결정은 [request-1029/](request-1029/)(PLAN · checklist · context-notes)이 정본이다. 받는 길은 그대로 `git pull && update-all`
이다(포털 · 게이트웨이 · 에이전트 서버, 화면은 Drive 판). 설정할 것은 없다 — 코어 어휘표는 포털 리포의 `backend/config/core_vocab.json` 이고
게이트웨이 · 에이전트 서버가 같은 박스의 그 파일을 읽는다.

### 받은 뒤 — 확인

- **게이트웨이** — `curl -s 127.0.0.1:9110/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"])'` 가
  `loaded: True · canonical: rootdesigndatahub · canonical_backend: True · tagline_applied: True` 다. `canonical_backend` 가 False 면 이 박스의
  정본 허브 백엔드 키가 어휘표의 `canonical.app` 과 다르다 — 정본 소개 줄 · 정본 대표 접기가 꺼진 채다(검색 낱말은 그대로 돈다). 키를 알려 주면
  dev 에서 어휘표를 고쳐 올린다. `tagline_applied` 가 False 면 다음 재활 회차(60초)에 다시 본다.
- **에이전트 서버** — `curl -s 127.0.0.1:9009/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"])'` 가
  `loaded: True · canonical: rootdesigndatahub` 다. False 면 챗 코어 규칙이 옛 글(발동 낱말 넷)로 돈다 — `error` 가 까닭이다(`없음` 이면 포털
  리포가 형제 자리 `../HWAXPortal` 에 없다).
- **화면** — 답을 기다리며 다른 탭으로 옮겼다 돌아와도 답이 끝까지 와 있다. 중지 단추가 곧바로 풀린다.

### 재시험 — 사람 · cae00 세션

- 같은 정답표 16문항(OT-01 ~ 16)과 챗이 부른 search_tools 질의를 다시 잰다. 원문 여덟은 이 박스 게이트웨이의 질의 기록
  (`../HWAXMcpGateway/tool_search_eval/queries.local.jsonl`)에 있다 — dev 는 요청서에 이름이 나온 일곱과 OT-07 영어 질문으로 쟀다(context-notes C-14).
- 보는 것 — OT-06 ~ 10 에서 정본 허브 호출이 1회 이상인지, OT-07 · 08 · 10 · 11 의 첫 도구가 코어인지, OT-11 고장모드 수가 71 인지, 자기검증 ms p95
  (`/health` `self_check`)와 '고친 답이 비어 초안 그대로' 가 주는지. 결과로 4차(E-1 ~ E-6)를 정한다(결정 D-7).
- '낙하 해석 담당' 은 코어 낱말이 없어 어휘표가 닿지 않는다 — 이 질의가 다시 코어를 건너뛰어도 1차가 고친 것과 무관하다(C-14).

## 2026-10-29 반영분 — 10-29 웹 챗 온톨로지 QA 후속(2 · 3차 · 4차 일부)

**받기 전에 [request-1029/server-setup.md](request-1029/server-setup.md) 를 읽는다** — 1 ~ 4차 전체의 수정 사항 · 받을 때 주의점 · 확인 · 사람 몫 · 되돌리기를 한 장에 모았다.
정본은 같은 [request-1029/](request-1029/)(checklist 2 · 3 · 4차, context-notes C-18 ~ C-29)다. 받는 길은 그대로 `git pull && update-all` 이다.
⚠ **포털과 에이전트 서버를 같은 판으로 받는다** — 포털의 챗 침묵 한도 900초(`AGENT_CHAT_IDLE_TIMEOUT_S`)는 에이전트 서버가 챗 스트림에도 15초마다 ping 을
내야 맞다. ping 없는 옛 에이전트 서버에 900초를 걸면 생각 · 비스트리밍 호출이 긴 답이 끊긴다(update-all 은 둘을 함께 올린다).
StepForge 몫(D-647 — `find_plm_task` 프로젝트 별칭 · `sync` 요약)은 StepForge 배치(Drive SIF) 뒤에 든다.

### 받은 뒤 — 확인

- **게이트웨이** — `/health` `core_vocab.staging_hidden` 이 이 박스에서 숨긴 시험 사본이다. 포털 `dbbb943`(10-31) 부터는 `[]` 가 맞다 — `dynaforge-prod` ·
  `stepforge-prod` 는 운영 앱이라 어휘표에서 뺐고(OB-04 사용자 결정 — [request-1030/context-notes.md](request-1030/context-notes.md) C-14), 웹 챗 · 개인 Claude 목록 ·
  `search_tools` 에 보통 앱으로 보인다. 시험 사본을 숨기려면 박스 덧씌우기 `backend/config/core_vocab.local.json` 에 그 백엔드를 역할 `staging` 으로 적는다
  (`{"apps": {"<백엔드 키>": {"role": "staging", "label": "<이름> 시험 사본"}}}`) — 그 앱이 여기에 들고, 이름으로 부르면 그대로 닿는다.
- **에이전트 서버** — `/health` `self_check` 의 `counts`(fixed · suspect)와 `ms.p95` 를 1차 재시험 수와 견준다. 자기검증은 이제 고칠 곳만 받는다(W-4).
  `suspect` 의 까닭이 '바꿀 곳을 초안에서 찾지 못했다' 로 많이 나오면 dev 에 보낸다(모델이 원문을 다르게 옮긴다는 뜻이다).
- **update-all §6 새 줄** — `· 새 앱 점검 — 기록이 없어 지금 앱 N개를 전부터 있던 것으로 적었다` 가 첫 실행에 한 번 나온다(정상 — 기록
  `infra/.state/app-checks.json`). 다음 실행부터 새로 붙은 앱만 14일 동안 ⚠ 로 짚는다(영역 · 권한 행 · 이름 겹침 · 인자 설명). 막지 않는다.

### 사람 몫 — 박스 설정

- **O-2 챗 LLM 부하분산기의 대화 고정** — 에이전트 서버가 챗 LLM 호출마다 `X-Session-Affinity` 머리(서버 대화 id 의 해시)를 싣는다. stcx 챗 LLM 앞
  nginx(`~/stcx-llm/nginx.conf`)가 그 머리로 복제본을 고르게 한다. `map` 은 http 블록에, `hash` 는 그 upstream 블록 맨 위에 둔다.

  ```nginx
  map $http_x_session_affinity $chat_affinity {
      ""      $request_id;                  # 머리가 없는 요청(다른 클라이언트)은 요청마다 다른 값 — 지금처럼 고르게 퍼진다
      default $http_x_session_affinity;
  }
  upstream <지금 이름 그대로> {
      hash $chat_affinity consistent;
      server …;                               # 지금 줄 그대로
  }
  ```

  `nginx -t` 뒤 다시 읽힌다(`nginx -s reload`). 확인은 같은 대화의 이어진 두 호출이 같은 복제본으로 가는지다(10-29 은 117쌍 중 1쌍).
- **O-3 도구 설명 예산 견주기** — 에이전트 서버 `.env` 에 `CHAT_TOOL_SCHEMA_BUDGET=30000` 을 적고 재기동한다(도는 심의가 없을 때
  `cd ~/Projects/HWAXAgentServer && ./start.sh -d`). 같은 16문항을 잰다. `40000` 으로 한 번 더 잰 뒤 나은 값을 남기거나 줄을 지운다(비면 종전대로
  챗 창의 45% — 호출마다 약 8.8만 토큰). 줄이면 `search_tools` → `invoke_tool` 왕복이 늘 수 있다 — 답의 질과 함께 본다.
- **안내 자리(W-3)** — 재시험에서 지시를 따르는 정도가 떨어지면 에이전트 서버 `.env` 에 `CHAT_STABLE_PREFIX=0`(종전 자리)을 적고 재기동한다.
- **오래 안 불린 도구 보고(E-3)** — `cd ~/Projects/HWAXMcpGateway && python3 tool_usage_report.py --out ~/unused-tools-$(date +%F).md`.
  앱마다 30일 동안 안 불린 도구가 나온다. 앱 주인에게 넘긴다(부른 사람 · 주소는 싣지 않는다).
- **SignalForge SG-04** — [request-1029/signalforge-sg04-question.md](request-1029/signalforge-sg04-question.md) 를 SignalForge 주인에게 넘긴다(P8 · PH8 제품 코드 — 데이터 결정).

## 2026-10-30 반영분 — 분석 루틴(R1 ~ R3 — 절차 탭의 플랫폼 연쇄를 챗 · Claude 가 같은 계약으로)

사람 몫 · 확인의 정본은 [docs/analysis-routines/server-setup.md](analysis-routines/server-setup.md) 다. 요점만 —

- **들어오는 것** — 포털(`/routines-api` · 챗 중계의 루틴 턴 · 화면 '루틴' 알약 · 실행 보기) · 게이트웨이(루틴 도구 여섯 · `/tools-map` 의 `routine_read` · prompts) ·
  에이전트 서버(`routine.py` · `/health` 의 `routine_active` · `routine_parked` · `routine_max`). 셋 다 update-all 이 재기동한다(에이전트 서버는 도는 심의 · 루틴을 기다린다 —
  심의 멈춤을 기다리며 쉬는 루틴은 세지 않는다). sqlite 표는 `procedures.sqlite` 안에 저절로 생긴다.
- **권한** — `feat:routines` 는 기본 부여가 아니다(CAEG 는 전부). 쓸 소속은 `access.local.yaml` 의 그 소속 `grants`, 사람마다면 '내 권한' 요청 → 관리자 승인.
- **단계는 읽기로 확인된 도구만** — 앱이 readOnlyHint 를 안 단 읽기 도구가 이름 규칙으로 막히면 게이트웨이 리포의 `read_tools.local.json`(gitignore)에 `<백엔드>:<원래 이름>` 을
  더한다(재기동 없이 읽는다). ⚠ 이 파일은 **새 판을 받은 뒤에** 만든다 — update-all §1 의 stash 는 옛 .gitignore 로 돈다(검색 손잡이 덧씌우기와 같은 주의).
- **확인** — `curl -s http://127.0.0.1:8723/routines-api/health` → `{"ok": true, "contract": 1}` · `/tools-map` 의 `routine_read` 수 > 0 · 에이전트 `/health` 의
  `routine_active` 0 · `routine_max` 2. R5 받아들이기(예시 연쇄 한 번 · 잰 값)는 server-setup.md 5절.

## 2026-10-30 반영분 — 검색 고리(E-7 ~ E-9 — 손잡이 · 덧씌우기 · 굴러가는 기록 · 검토 화면 · 피드백 보고서)

**받기 전에 [request-1029/server-setup.md](request-1029/server-setup.md) 7절을 읽는다.** 기본값은 지금 순위와 바이트까지 같다 — 덧씌우기 파일을 만들기 전에는
검색 답이 바뀌지 않는다. 게이트웨이 `f4d9546` · 에이전트 서버 `ab87137` · 포털(관리자 '도구 검색 검토' · update-all §7 지문 줄)을 update-all 한 번으로 받는다.
⚠ **덧씌우기 파일(`HWAXMcpGateway/search_tuning.local.json` · `backend/config/core_vocab.local.json`)은 이 판을 받은 뒤에 만든다** — update-all §1 의
stash 는 받기 전의 `.gitignore` 로 돌아 그 전에 만든 파일을 치운다. 이미 만들었으면 그 리포의 `.git/info/exclude` 에 먼저 적는다.
받은 뒤 끝 요약 §7 에 `· 검색 손잡이: 지문 …` · `· 코어 어휘표 지문: 게이트웨이 … · 에이전트 …`(둘이 같아야 한다) 두 줄이 보인다.
정답 달기 · 평가 · 플랫폼별 피드백 보고서(`platform_feedback_report.py`)는 사람 몫이다(7.3절).

## 2026-10-30 반영분 — 낙하 트윈(DynaForge 후처리 반입)

cae00 · icn401(KooSlurm 운영) · stcx 에서 사람이 돌리는 확인이다. 원문은 KooRemapper `docs/requests/hwax-portal-cae00-checks-2026-10-30.md`(origin/main
`40d3d55` — Drive 판 `dist-20261030-142622Z`(`24bca1c`, SP 받는 쪽 전부) · §0 1번 · §1 · §1-1(새 절) · §8 · §9 를 고친 판, 그 앞 판 `352a8fd` 는 변형 뷰어 1단계)이고, 명령 · 기대값은
그대로 옮겼다. 정본 — DynaForge 쪽 결정 · 계약은 KooRemapper `platform/docs/REQUEST-postprocess-operation.md` §10 ·
`docs/01-plan/features/{postprocess-reservation-1028,sphere-risk-map-1029}.plan.md` · 총괄 `drop-twin-1028.checklist.md`, KooSlurm 쪽은 KooSlurm
`docs/sso_enable_20261029/{icn401_apply_check,sso_enable_procedure}.md`(origin `46c647e4`). 포털 쪽 몫은 R2a 제출 씨앗의 후처리 예약(`9ce09b6`,
절차 context-notes W-101)과 과제 메타 넷(`project` · `dev_rev` · `variation` · `doe` — 선택 변수, 비우면 그 칸이 빠진다, W-102)이다 — 기존 씨앗을 들인 사람은
절차 › 정본 예제 '다시 가져오기' 로 새 판을 받는다.

### 0. 순서 — 한 줄씩

1. **cae00** — `git pull && update-all`(update-all §2 가 kooremapper 의 Drive 판 `dist-20261030-142622Z` 를 받는다) → 아래 1 · 1-1.
2. **icn401** — `git pull && sudo ./dashboard/start_production.sh` → 아래 3(KooSlurm 문서 §2).
3. **비밀 하나를 두 곳에** — icn401 `HEAX_GATEWAY_SECRET`(backend_5010/.env) = cae00 `KOORM_KOOSLURM_SSO_SECRET`(KooRemapper platform/.env) → 아래 2 · 3-3.
4. **cae00** — `KOORM_STCX_BACKEND_URL` 확인 → DynaForge 재기동 → 아래 2 확인.
5. 운영의 **첫 실제 전각도 잡** 뒤 → 아래 4.
6. (사람 · 읽기만) stcx viz 노드 · 게이트웨이 감사 → 아래 5 · 6.
7. (운영 측) stcx 후처리 이미지 **Post v42** 설치 — 단면 영상 응력 0 프레임 고침 → 아래 5-1.

SSO 켜기는 **이번에 하지 않는다**(아래 7 — 조건이 안 섰다).

### 1. cae00 — DynaForge 받기(update-all 뒤)

이번 판에 든 것 — 반입 속도(raw_decode `288afb7` · sphere 블록 분리 `c7970dc`) · 후처리 예약 `postprocess`(`4ff9a79` → 위임 창구 `e62f601` · rc 3 경고) ·
구면 위험도 맵(3D · 허용비 · 상위 N, `f366816`) · 렌더 결과 반입 C-11(`85ba2f0`) · postprocess 의 비운 선택 칸 null 을 없는 칸으로(`07679d7`) ·
`dev_rev` 를 예약 때 반입 규칙으로(`3574342`) · **변형 뷰어 1단계** — 리포트에 StepForge fe_cad 묶음 붙이기(REST `POST /reports/{id}/cad` · MCP `attach_cad`,
`aa63e2a`) · 맵에서 각도를 고르면 「형상 보기」(`d37fcbb`) · **SP 받는 쪽 전부**(아래 1-1, `f36270f` · `a3eff43` · `306346d` · `80a862a` · `24bca1c`). **마이그레이션 다섯**(0015 · 0016 · 0017 — 모두 null 허용 칸 · 유일 제약, 0018 — 새 표 셋과 null 허용 칸 둘, 0019 — 트리거, 옛 코드에 영향 없음).
바이너리는 그대로(`8c7c4f87`).

| 확인 | 명령 | 기대값 |
|---|---|---|
| 판 | `curl -s http://127.0.0.1:8700/api/health` | `"status":"ok"` · `revision` 이 이번 게시 BUILD_INFO 의 커밋(`24bca1c`) |
| 소스 | KooRemapper 리포 루트에서 `git log -1 --oneline` | `24bca1c` 이거나 그 뒤 — 위 `revision` 은 Drive 판의 커밋이라 그 뒤에 파이썬만 바뀐 커밋은 여기서만 보인다. 앞이면 null 을 보내는 손님(MCP 직접 호출 — Claude 등)이 비운 선택 칸에서 422 를 받고(포털 R2a 는 칸째 빼고 보내 영향 없음 — W-102), 틀린 `dev_rev` 가 예약은 되고 잡이 끝난 뒤 반입에서야 실패한다 |
| 마이그레이션 | KooRemapper 리포 루트에서 `bash platform/infra/scripts/migrate.sh` | 「Running upgrade」 줄 없이 「✓ migrations applied」 = 이미 0019 까지 올라 있다(빠졌으면 이 명령이 그 자리에서 올린다 — 0015 · 0016 · 0017 · 0018 · 0019). ★0019 는 **지운 리포트의 개정 선**을 한 번 지운다 — 개정 비교의 「리포트」 수가 지운 리포트만큼 줄 수 있다(정상, 사용자 결정 10-30) |
| MCP 도구 | 게이트웨이 tools/list 에서 kooremapper 도구 수, 또는 `platform/mcp_server/venv/bin/python platform/mcp_server/smoke.py` | 85개(`attach_render` · `attach_cad` · `ontology_types` · `ontology_find` · `ontology_object` 가 새로 있다) · `MCP SMOKE: PASS` |
| 화면 | 세션 → 전각도 리포트 펼치기 → 「부품 위치·방향 시각화」 → 보기 「구(3D)」 | 3D 구가 뜬다(three.js 는 묶음 안에 있다 — 망 밖에 안 나간다) · 허용값을 넣으면 「초과 · 경고」 수가 보인다 |
| 형상 보기 | 같은 맵의 상위 표에서 각도 한 줄을 누른다 | 「고른 각도 …」 줄이 생긴다. CAD 묶음을 붙인 리포트면 「형상 보기」 로 glb 가 열리고 파트가 칠해진다(「속 보기」 로 속 파트). 안 붙였으면 붙이는 길(MCP `attach_cad` · REST)이 적힌다 — 운영에서 누가 붙일지는 아래 9 |

### 1-1. cae00 — SP 받는 쪽(이번 판에 더해진 것)

SP 키트 2026-10-21 판(규칙 16 · 시험장 8단계 자동 시험) 받기 · 잠금 · 실행 기록 · 주 1회 처음부터 · 식별자 바뀜 반영 · 합쳐진 과제 알림과 관리자 옮기기 ·
과제 검색(KR-01 다시 · KR-16 다시) · 받은 것 보기(화면 · API · MCP 셋) · 다시 확정하면 옛 리포트 선을 뗀다 · 지운 리포트의 개정 선은 DB 가 함께 지운다
(`f36270f` · `a3eff43` · `306346d` · `80a862a` · `24bca1c`). **실제 허브 주소 · `core:read` 토큰은 아직 없다** — 그래서 받기는 꺼진 채가 정상이다.

| 확인 | 어디서 | 기대값 |
|---|---|---|
| 과제·개정 스위치 | 시스템 상태 → 「과제·개정 (온톨로지)」 카드 | 켜짐/꺼짐과 **사유**. 꺼졌으면 왼쪽 메뉴에 「온톨로지」 가 **없는 것이 정상**이다(꺼지면 없어진다) |
| (켜진 박스만) 보기 | 왼쪽 메뉴 「온톨로지」 | 받은 타입 · 상태별 건수 · 객체(활성 · 그만 씀 · 사용 안 함 구별) — 아직 받은 적이 없으면 「받은 것이 없다」 |
| (켜진 박스 · 관리자만) 받기 카드 | 시스템 상태 → 「허브 받기 (관리자)」 | 주소 · 토큰이 없으면 「허브 주소 · 토큰이 없어 받기가 꺼져 있다」 · 단추가 잠긴다 — 정상. 토큰이 생기면 「지금 받기」 → 결과 「정상」 또는 「확인 필요」 + 사유 |
| 과제 검색 | MCP `list_tasks(q=…)` | 항목마다 `matched_by` · `match_kind`, 응답에 `truncated` · `total` (허브에서 받은 과제가 있을 때) |

⚠ 화면이 옛것이면 — dist 는 받았는데 API 가 옛 index 를 내는 것이다. `update-all` 이 재기동을 건너뛰었는지(§2 의 지문 — '바뀐 것만 재기동') 보고,
아니면 KooRemapper `platform/infra/scripts/restart-api-only.sh`(도는 잡 0 확인 뒤).

### 2. cae00 — 후처리 예약(7-1) 설정

`platform/.env`(KooRemapper)에 둘. **값은 화면 · 로그 · 채팅에 붙이지 않는다.**

```
KOORM_STCX_BACKEND_URL=<cae00 에서 닿는 stcx 대시보드 주소 — 덱 업로드에 쓰는 것과 같은 값>
KOORM_KOOSLURM_SSO_SECRET=<icn401 backend_5010/.env 의 HEAX_GATEWAY_SECRET 과 같은 값>
```

선택 — `KOORM_POSTPROCESS_WAIT_DAYS`(기본 7) · `KOORM_KOOSLURM_TIMEOUT_SEC`(기본 30). 넣은 뒤 재기동(도는 잡 0 확인 → `restart-api-only.sh`, 또는 다음
`update-all` 이 .env 지문으로 재기동).

**확인 — 없는 잡으로 예약해 본다**(운영 잡을 건드리지 않는다). 콘솔에서 세션 하나 → 오퍼레이션 `postprocess` → `job_key=stcx:0`, `sim_type=fullangle_drop`
→ 실행. 또는 `platform/mcp_server/venv/bin/python platform/mcp_server/allops_smoke.py` 의 postprocess 줄.

| 잡의 오류 문구 | 뜻 |
|---|---|
| 「구성 안 됨 — KOORM_… 이(가) 비었다」 | 설정이 아직 안 들어갔다(또는 재기동 전) |
| 「위임 창구가 잡 소유자의 토큰을 내주지 않았다(sso_401)」 | 비밀이 icn401 과 다르다 |
| 「…(sso_404)」 | icn401 에 비밀이 아직 없다(아래 3-3) — 창구가 닫혀 있다 |
| 「…(sso_400)」 | 이메일이 사용자 이름 규칙에 안 맞는다(`@` 앞이 `[a-z0-9._-]` 1~32 · admin · root · anonymous 거절) |
| 1~2분 뒤 「클러스터가 이 잡을 모른다(`/info` 404 …)」 | **정상** — 설정 · 위임 · 대시보드 REST 가 다 닿았다(잡 0 은 없다) |

### 3. icn401 — KooSlurm 반영(사람)

KooSlurm `docs/sso_enable_20261029/icn401_apply_check.md` 그대로. 요점 —

1. 반영 `git pull && sudo ./dashboard/start_production.sh`(로그를 /tmp 에 tee). 결과 귀환(`7c280000` 까지) · 위임 창구(`3f72f4c6`) · 문서(`46c647e4`)가
   한 번에 들어간다.
2. 확인 10개 — 코드 판 · 템플릿 동기화 줄 · 드라이버 템플릿 `grep -c write_return_manifest` = 3 · LSTC 플레이스홀더 0 · 「→ SSO=false → 정본 conf:
   hpc-portal.conf」 · frontend_3010 재빌드 · 백엔드 active · C 라우트(새 코드면 400 · error_code 9001) · 다운로드 티켓 · 위임 창구 비밀 전 404.
3. `HEAX_GATEWAY_SECRET` 넣기(backend_5010/.env · chmod 600 · 재시작) →
   `curl -s -o /dev/null -w '%{http_code}' -X POST -H "X-Heax-Gateway-Secret: <비밀>" https://<대시보드>/api/auth/sso/verify` → **204**(틀리면 401).
   같은 값을 cae00 위 2 에.

### 4. 운영 첫 실제 전각도 잡 뒤 — 끝까지 한 번

1. **B(드라이버 매니페스트)** — KooSlurm 문서 §4: `sacct` · 드라이버 로그 끝 「=== 귀환 매니페스트 ===」 · `<RESULT_DIR>/output/return_manifest.json`.
   정상이면 `COMPLETED 0:0` · `ok: true` · 리포트 sha256 이 파일과 같다. 없으면 `FAILED 3:0` · `reason` · `log_tail` — 그 줄을 KooSlurm 에 넘긴다(없으면 C 로
   다시 거는 curl 이 문서에 있다).
2. **DynaForge 예약** — 그 잡을 제출한 절차(포털 R2a, `9ce09b6`)가 걸어 둔 `postprocess` 잡이 `succeeded` 가 되고 `resolved_cmd.report_ids` 에 리포트 id 가
   생긴다. 리포트가 예약자 명의로 들어왔는지(제출 때 과제 메타 — `project` · `dev_rev` · `variation` · `doe` — 를 채웠으면 그 값도), 리포트 상세의
`external_job_key` = `stcx:<잡 id>` 인지 본다.
3. 실패면 잡의 `error_summary` 가 매니페스트 까닭을 그대로 싣는다 — 그 문구를 DynaForge 에 넘긴다.

### 5. stcx viz 노드 — 읽기만(SceneForge · S1)

GPU 는 노드마다 챗 LLM 과 함께 쓴다 — **읽기만**(MIG 전환 · GPU 재설정 · 설치 · 렌더 없음). 명령의 정본은 SceneForge `scripts/stcx_viz_readcheck.sh`(f46e835)
— 결과를 텍스트 파일 하나로 모은다. 그 파일을 SceneForge 세션에 넘긴다.

```
bash stcx_viz_readcheck.sh                                    # 1단계 — 로그인 노드만, 노드에 잡을 걸지 않는다
bash stcx_viz_readcheck.sh <viz 파티션> <노드> <S1 결과 폴더>    # 2단계 — 고른 노드에 CPU 1 · 512M · 5분 · GPU 요청 없는 잡 하나
```

- 2단계 앞뒤로 cae00 에서 `~/stcx-llm/llmctl.sh status`(챗 LLM 이 그대로인지).
- **<S1 결과 폴더>** — S1 은 아직 나오지 않았다(KooD3plotReader 추출기 계약 대기). 둘 자리는 정해졌다 — 각도 run 폴더의 `Output/s1.h5`(KooD3plotReader
  계약 초안 2, 10-30 — `<RESULT_DIR>/output` 아래). 추출기는 아직 운영 이미지에 없다(libhdf5 를 넣은 다음 판 대기). 그러니 지금은 운영 전각도 잡 하나의
  `<RESULT_DIR>/output`(sphere_report.html 이 있는 곳 — 귀환 매니페스트의 `job.result_dir`)로 마운트를 본다.
- 스크립트를 못 옮기면 한 줄씩 — SceneForge `docs/requests/dynaforge-sceneforge-tasks-reply-2026-10-29.md` 「cae00 명령」 절(sinfo · squeue · 챗 LLM
  sbatch gres · scontrol config · `nvidia-smi` · `ldconfig -p` 로 GL/EGL/NVENC/Vulkan 라이브러리 · `apptainer --version` · `ls -la <폴더>`).
- 제어면 준비로 둘 더 — SceneForge 를 돌릴 cae00 계정에서 `ssh -o BatchMode=yes stcx true && echo ok`(sbatch 낼 길이 비밀번호 없이 열리나, C-13) ·
  `ssh stcx df -h /data2`(렌더 작업자 SIF · 결과 자리 여유 — 자리는 노드 관리자와 정한다).
- GPU 를 쓰는 시험(T1 · T2)은 SceneForge `docs/research/stcx-gpu-test-plan-2026-10-29.md`(e3371e7) — 읽기 점검 결과가 나온 뒤 챗 LLM 운영과 시간을 잡고.

### 5-1. stcx — 후처리 이미지 Post v42(운영 측 설치)

단면 영상 **응력 0 프레임**(K-1 — 운영 영상 24개 중 7개가 오류 없이 응력 0) 고침이 든 판이다(KooD3plotReader `5abbc76`). pyKooCAE 가 Drive
`ApptainerImages:SmartTwinPreprocessor/` 에 올렸다 — `SmartTwinPostprocessor_20261029_v42.tar.gz`, sha256 헤드리스 `1a6e0933…` · GUI `4536ea72…`. 이 박스에서
stcx 로 밀어 넣는 절차는 없고 **설치는 운영 측 몫**이다.

- 설치 뒤 — `apptainer exec <설치한 SmartTwinPostprocessor.sif> head -3 /opt/kood3plot/VERSION` → `Version: 5abbc76`.
- 고침 자체는 dev 헤드에서 확인했다 — 결함을 매번 일으키는 설정(LS-PrePost 예산 20M)을 심어도 정상이고, 옛 판(Post v41 `282630b`)은 같은 설정에서 0 을 내며
  rc 0 으로 끝났다(KooRemapper `7818cbc`). 운영에서는 설치 뒤 전각도 잡 하나의 단면 영상 마지막 프레임 범례가 `max = 0, at node# 0` 이 아닌지만 본다.

### 6. 게이트웨이 — 게이트웨이를 거친 stcx 제출이 지금 되는가(선택)

```
tail -3000 ~/Projects/HWAXMcpGateway/audit.jsonl | grep -a '"backend": "smart-twin' | tail -5
```

`ok` · `error` 칸만 본다. 게이트웨이는 smart-twin 백엔드에 Authorization 을 싣지 않아(사람별 위임은 미룸 — 사용자 「나로 일단」), smarttwin_mcp 가 서버 env
`STMC_CLUSTER_TOKEN` 으로 넘어간다. 그것도 없으면 거부다.

### 7. SSO 켜기 — 이번엔 하지 않는다(조건)

KooSlurm `docs/sso_enable_20261029/sso_enable_procedure.md`. 켜기 전에 설 것 —

- **IdP 주소** — 저장소의 운영 YAML 사본은 `sso.saml.idp.sso_url` 이 비었다. 비었으면 켜는 순간 아무도 로그인 못 한다(icn401 실제 YAML 확인).
- **SSO 꺼진 동안 발급한 kst_ 는 전부 admin 으로 저장됐다** — 켠 뒤 그대로 두면 관리자 토큰이다. 절차서 §2 대로 지우고 다시 발급(`~/.claude.json` 의
  smarttwin kst_ 포함). **smarttwin-mcp 유닛 env 의 `STMC_CLUSTER_TOKEN` 도** — 그대로 두면 게이트웨이 경유 제출이 전부 관리자 권한으로 간다. 다시 발급한
  토큰의 주인이 그 뒤 제출 · 업로드의 명의가 된다(KooSlurm `a4734e7a`).
- **DynaForge 덱 업로드의 신원 = 제출 신원**(절차서 §0 조건 5) — 게이트웨이 경유 단일 신원이면 업로드도 그 토큰(`STMC_CLUSTER_TOKEN`), 사람별 위임이면
  업로드도 위임 창구 토큰. 어긋나면 켜는 순간 거절된다. 어느 쪽인지는 켤 때 사용자 결정이고, DynaForge 업로더는 그 결정에 맞춰 짓는다(지금은 보류).
- 걸린 예약이 없을 때 켠다 — 켜는 순간 신원이 admin → 실제 사용자로 바뀌어 켜기 전 예약은 403 으로 닫힌다.

### 8. 되돌리기

- **DynaForge** — 아티팩트: `rclone copy ApptainerImages:KooRemapper/dist/dist-<이전 판>/ ApptainerImages:KooRemapper/dist/latest/`(이번 판 바로 앞은
  `dist-20261030-032145Z`) 뒤 `update-all`(또는 `dist-from-drive.sh --restart`). 코드: 이전 커밋으로. 마이그레이션 0015 · 0016 · 0017 은 null 허용 칸 · 유일
  제약, 0018 은 새 표 셋과 null 허용 칸 둘, 0019 는 트리거라 옛 코드가 그대로 돈다 — 되돌리지 않아도 된다(0019 가 지운 「지운 리포트의 선」 은 되살리지 않는다 —
  리포트가 없다).
- **KooSlurm** — 그쪽 문서의 되돌리기 절.
- **포털 R2a 씨앗** — 예약 두 단계(④ 세션 · ⑤ 후처리)를 빼고 싶으면 그 절차를 고친 새 판을 저장한다(지난 판은 그대로 남는다).

### 9. 남은 사람 결정(참고)

SP 허브 주소 · `core:read` 토큰(받기를 켜는 조건 — 넣으면 시간마다 받고 7일마다 처음부터) · CAD 묶음을 리포트에 붙일 주체(포털 절차의 한 단계 · 사용자 MCP — MCP `attach_cad` 는 MCP 컨테이너가 읽는 경로만 되고 StepForge 산출 자리는 안 보인다
(dev 실측), REST 는 어디서든) · 옛 결과 리포트 셸 다시 만들기 `--regen-sh`(pyKooCAE — 옛 부분충격 결과는 이것 없이 7-1 로 못 받는다) · SSO 켤 시각(위 7) · 렌더 결과를 붙이는 명의
(소유자만 / 같은 소속) · 보고 영상 「접촉 앞」 해석 밖 구간 · 과제 키 검증(7-4) · pyKooCAE F 예제. R2a 씨앗의 과제 메타(project · dev_rev · variation · doe)는
10-30 판부터 선택 변수로 묻는다(W-102) — 비우면 그 칸이 빠지고, 메타 없이 반입된 리포트는 find_reports · report_facets 의 과제 간 비교에서 빠진다.
`dev_rev` 는 DynaForge 가 반입 때 받는 꼴(pre · dv1~3 · dvr · pv1~3 · pvr · pra · mp)에서 고른다 — DynaForge `3574342` 부터는 틀린 꼴이 예약 때 422 다
(그 앞 판은 잡이 끝난 뒤 반입에서야 실패했다).

## 2026-10-31 반영분 — 10-30 수정 요청(웹 챗 재시험 · 디지털 워커 QA) · 받은 편지함

**받기 전에 [request-1030/server-setup.md](request-1030/server-setup.md) 를 읽는다** — 받는 판 표 · 확인 · 손잡이 · 다시 볼 시험 · 사람 몫이 한 장이다.
정본은 같은 [request-1030/](request-1030/)(PLAN · checklist · context-notes C-1 ~ C-24 · outbound)다. 받는 길은 그대로 `git pull && update-all` 이다.
받기 전에 읽으려면 `git fetch` 뒤 `git show origin/main:docs/request-1030/server-setup.md` 로 본다(작업 트리는 그대로다).

- ⚠ **AIDataHub 데이터 단계에는 차례가 있다** — dev 지우기(사용자가 직접)가 실린 덤프가 이 박스에 병합되기 **전에** OB-73 의 K9(데모 카드 `…012`)을
  본다. 병합이 레코드의 소프트 삭제를 옮겨 카드가 목록에서 빠진다(server-setup 8-3). dev 지우기가 돌았으면 K9 은 **update-all 을 돌리기 전에** 본다 —
  update-all 이 새 덤프를 스스로 병합하고, 손 병합(8-1)도 그 뒤다.
- ⚠ **SignalForge** — 이 판을 받는 update-all 은 SignalForge 코드가 바뀌었으면 sf-mcp 를 곧바로 새 코드로 다시 띄운다. 그쪽 10-31 cae00 문서의 재기동 차례(병합 뒤)와
  어긋나므로 받기 전에 server-setup 3절의 사용자 결정 줄을 본다. 받은 뒤에는 그 절의 PLM 처음 받기를 바로 한다.
- **챗 관문 넷(HA-27 ~ HA-30)** — 에이전트 서버와 포털(화면 Drive `images-20261030-220551Z`)을 같은 판으로 받는다. 받은 뒤 `/health` 넷과 update-all §7 줄을
  본다(6-1). 손잡이는 모두 에이전트 서버 재기동 뒤에 먹는다(6-2).
- **받은 편지함** — update-all 이 git 받기 뒤 `→ cae00 받은 편지함 — …` 줄로 이 박스에 마지막으로 알린 뒤의 새 글을 알리고 끝 요약에서 다시 낸다
  (기준은 `infra/.state/inbox-head` — `git pull` 을 먼저 해도 빠지지 않는다. 기록이 없는 첫 실행은 글을 모두 찍는다).
  [cae00-inbox/README.md](cae00-inbox/README.md) 대로 이 박스에서 읽기만으로 답하고, 답은 리포 밖 파일로 사용자에게 준다 — 이 박스에서 리포에 커밋하지 않는다.
- **AIDataHub 병합** — `6f496fa` 는 병합 스크립트 고침이라 Drive 덤프가 그대로면 update-all 이 돌리지 않는다. 받은 뒤(K9 뒤) 병합을 한 번 손으로 돈다 —
  update-all 이 받아 둔 덤프를 `AIDH_MERGE_DUMP` 로 넘기고(안 넘기면 약 11 GB 를 다시 받는다) 운영자 미리보기를 한 번 더 본다(8-1 의 두 줄).
- **OB-04 · OB-26** — 박스 권한표의 '(시험)' 라벨 고치기와 ODB 허브 입구 도구 노출 꼴 확인(7절).
