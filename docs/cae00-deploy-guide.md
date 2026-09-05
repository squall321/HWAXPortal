# cae00 배포 가이드 — 무엇이 `update-all` 로 되고, 무엇이 따로인가

> 이 문서는 실제 스크립트(update-all.sh · deploy-all-from-drive.sh · AIDataHub deploy · STE deploy · 심의 파이프라인)를
> 라인 단위로 대조해 작성했다. 런타임(cae00 실행) 검증이 아니라 소스 검증이므로, 박스별 상태
> (provision.env 토큰 · rclone remote · .env 포트)에 따라 결과가 달라질 수 있다(§끝 주의 참조).

## 0. 한 줄 요약

- **`update-all` 한 방에 되는 것**: 포털·챗 스택·MCP 게이트웨이 배포 + **AIDataHub 데이터(전문가·카드) 병합** + 워크플로 사본 동기화 + 헬스 게이트.
- **`update-all` 로 안 되는 것**: **STE(SmartTwinExplorer)**. 헤드노드 stc(에어갭)에 사는 별도 서비스라 프로브만 한다 — 배포는 `deploy-ste.sh` 를 따로 실행한다.
- **dev 가 선행해야 하는 것**: 전문가/카드를 **dev AIDataHub 에 업로드 → `backup-to-drive`** (그래야 cae00 이 병합해 온다). STE 는 **`pack-staging + push-to-drive`**.

---

## 1. `git pull && update-all` 이 실제로 하는 일

`update-all` 은 스스로 최신화한다 — 앞의 `git pull` 없이도 §1 이 포털 레포를 `fetch + reset --hard origin/<branch>` 후 새 버전으로 1회 재실행한다(`UPDATE_ALL_REEXEC` 가드로 딱 1번). 로컬 수정을 지키려면 `NO_GIT_RESET=1 update-all`(ff-only, reset 대신 stash).

| 단계 | 하는 일 | 근거 |
|---|---|---|
| §1 | 포털 레포 self-update(fetch+reset) → 1회 재실행 | update-all.sh:66-89 |
| **§1a** | **워크플로 정본→런타임 사본 동기화** — `infra/pipeline/*.js`(meta 보유)를 gitignore 사본 `.claude/workflows/` 로 복사. 이름호출 런타임이 옛 사본 쓰는 갭 봉합 | update-all.sh:91-95 · sync-workflows.sh |
| §1b | 배포 전 로컬 백업(/data/backups) + 일일 cron(03:30) 멱등 보장 | update-all.sh:97-115 |
| §2 | **전 서비스 배포** — `deploy-all-from-drive`: `portal mxwp heax aidh signalforge kooremapper`. 각 서비스 git pull → Drive 에서 **미리 빌드된 아티팩트 반입**(cae00 은 빌드 불가) → START. 끝에 nginx conf 재생성+재기동 | deploy-all-from-drive.sh:145,2-6,374-400 |
| **§3** | **AIDataHub 데이터 병합** — 아래 §2 참조. 비파괴 merge | update-all.sh:139-182 |
| §4 | 챗 스택 pull+재기동 — `signalforge-mcp mcp-gateway agent-server`(백엔드→게이트웨이→소비자 순) | update-all.sh:233-242 |
| §5 | 게이트웨이 config 정합 — 기대 백엔드 빠졌으면 `provision-config --force` 후 재기동·재검증 | update-all.sh:244-364 |
| §6 | **헬스 게이트**(critical): portal:8723 · nginx:8088 · agent-server:9009 · gateway:9110 의 `/health→200`. 하나라도 실패면 `exit 1` | update-all.sh:402-420 |

**STE 는 §6 에서 프로브만** 한다(백엔드가 이 박스가 아니라 헤드노드라 실패해도 비치명). 실패 시 `deploy-ste.sh` 를 **힌트로 안내만** 하고 호출하지 않는다(update-all.sh:485-486,516).

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
- `sync-from-drive.sh`(DROP+CREATE+restore, 파괴적 전체복원)는 **update-all/deploy-all 이 자동 호출하지 않는다** — 재해복구·초기시드용 별도 수동 명령이다. 일상 반영은 §3 merge 로 충분하다.

---

## 3. 심의가 실제로 새 전문가·카드를 쓰는 조건

MCP 경로(Claude Code·게이트웨이)와 웹 경로(`/시뮬심의`) **둘 다 반영**돼 있다.

- **수치 스파인 5석 고정 착석**(정식화·이산화·검증 + 리뷰어 2석) — 기본 ON.
  - MCP: `hwax-sim-deliberate.js` `FIXED_CAE`(방법론 2 + 스파인 5 = 7석), `spine`/`spineReview` 플래그(기본 true).
  - 웹: `deliberation.py` `_SIM_FIXED_CAE`, env `DELIB_SIM_SPINE`/`DELIB_SIM_SPINE_REVIEW`(기본 1).
- **카드 그라운딩** — 발언이 지식카드를 인용.
  - MCP: `groundCards`(sim 기본 ON) → 각 좌석이 `get_context_bundle(agent_type)`·`semantic_search` 호출(hwax-deliberate.js:191-198).
  - 웹: `DELIB_PERSONA_KNOWLEDGE`(기본 1) → 페르소나별 `agent_search` 결정적 RAG 주입(deliberation.py:1837) — 다른 메커니즘, 같은 AIDataHub 의존.
- **전제(둘 다)**:
  1. **AIDataHub 에 해당 `xd-cae-*`(+발굴 대상) 전문가·records 가 동기화**돼 있어야 근거가 빈 값이 아니다 → §2 의 업로드+병합.
  2. **세션에 게이트웨이 MCP 연결** — 도구(get_context_bundle/agent_search/recommend_agents)가 노출돼야 한다. 미연결 시 MCP 는 페르소나 지식으로 발언(가법적·회귀 없음), 웹은 카드 주입 생략.
  3. **이름호출 최상위 워크플로**(hwax-sim-deliberate)는 `.claude/workflows/` 사본을 읽으므로 §1a 동기화가 선결(자식 hwax-deliberate 호출은 scriptPath 라 무관).

**검증 방법**: cae00 재기동 후 `/시뮬심의` 1건 → 2단 좌석에 스파인 7석이 뜨는지 + 발언에 카드 출처가 붙는지.

---

## 4. STE(SmartTwinExplorer) — 왜/어떻게 따로 배포하나

STE 백엔드는 **cae00 가 아니라 에어갭 헤드노드 stc** 에 있다. cae00 은 stc 직결 경로가 없어 **Teleport SSH 터널**(루프백 127.0.0.1:15810, `ste-tunnel`)로 닿는다. 그래서 STE 는 `services.yaml` 에 없고 `update-all` 은 프로브만 한다.

### STE 는 3단계

```
① (1회) 최초 반입 — 런북 §1~§8 수동 (사람)
      Teleport·transport.env · cluster.prod.yaml(노드·계정·키·라이선스) · 번들 9.6GB + SIF · installer(설치·토큰) · 첫 서비스 배포
      ↳ 관리자 협조(계산노드 공개키 등록 등) 필요. 정본: SmartTwinExplorer/docs/03-runbook/cae00-staging.md
② (이후) dev: deploy/pack-staging.sh
              STE_BUNDLE_DIR=var/staging deploy/push-to-drive.sh --path SmartTwinExplorer/staging
③ (이후) cae00: infra/scripts/deploy-ste.sh        # = STE deploy/refresh-code.sh(§11) 트리거
```

- `deploy-ste.sh` → `refresh-code.sh` 체인: pull-from-drive → sha256 → git 커밋 고정 → dist 전개 → (requirements 바뀐 회차만) wheel 병합 → deploy-frontend `--no-build` → deploy-backend. 배포 후 포털 프록시 `/ste/api/health` 본문에 `smart-twin-explorer` 있는지로 검증.
- **런타임 게이트**(refresh-code.sh:27-33): transport.env 존재, `tr_run 'true'`로 헤드노드 도달(Teleport 세션 만료면 §9-A), 정체성 가드(cae00 자신 가리키면 §9-D). 조건 안 되면 fail-fast.
- **최초 반입(①)은 자동화 밖** — refresh-code.sh 는 §11(코드 갱신)만 한다. 번들·SIF·토큰은 1회성이라 스크립트가 대신 안 한다.

> **현재 상태 메모(2026-08-26)**: 클러스터측(Teleport·SIF·설치)은 완료, **cae00 에 staging 만 없음**. staging 은 `refresh-code.sh` 가 직접 당기므로 — **staging 이 Drive 에 있으면** cae00 에서 `deploy-ste.sh` 한 번이 첫 코드 배포가 된다. 없으면 dev 에서 ②(pack+push) 먼저.

### `--with-ste` (원하면 붙일 수 있음, 현재 미적용)

`update-all --with-ste` = 평소 배포 + 끝에 `deploy-ste.sh` 트리거. 구현은 플래그 파싱 2줄이면 된다.
```sh
case " $* " in *" --with-ste "*) WITH_STE=1 ;; esac      # 상단
[ "${WITH_STE:-0}" = 1 ] && "$SELF_REPO/infra/scripts/deploy-ste.sh"   # 배포 끝
```
**기본은 분리 유지** — `--with-ste` 없이 도는 routine·크론 실행에 실 stc 에어갭 배포가 섞여 발화하지 않게. 명시적으로 줄 때만 STE 가 간다.

---

## 5. 명령 요약 (치트시트)

```sh
# ── 포털·챗·MCP·AIDataHub 반영 (cae00) ──
./infra/scripts/update-all.sh              # 자기 최신화 + 전서비스 + AIDH merge + 헬스게이트
./infra/scripts/update-forges.sh           # ★경량 표적 갱신: stepforge+dynaforge+ste+chat(수 분)
./infra/scripts/update-forges.sh chat      # 챗·심의 스택만(포털+agent-server+게이트웨이)
./infra/scripts/update-forges.sh ste       # STE 코드 갱신(deploy-ste 체인)  — 골라서 조합 가능
./infra/scripts/update-forges.sh restart   # 갱신 없이 재시작만 — nginx 안 뜨면 자동 부검(conf -t·TLS cap 힌트)
NO_GIT_RESET=1 ./infra/scripts/update-all.sh   # 로컬 수정 보존 모드

# ── 전문가/카드를 AIDataHub 에 반영 (dev 선행 → cae00 은 update-all 이 병합) ──
# dev:
erag export-aidatahub --upload --url http://localhost:8001 --api-key <KEY>   # 전문가 정의
erag export-records   --upload --bind --url http://localhost:8001 --api-key <KEY>   # fact-checked 카드
bash deploy/apptainer/backup-to-drive.sh                                       # 덤프 → Drive
# cae00: (update-all §3 이 자동 merge)

# ── STE 배포 (별도) ──
# dev:
deploy/pack-staging.sh && STE_BUNDLE_DIR=var/staging deploy/push-to-drive.sh --path SmartTwinExplorer/staging
# cae00:
infra/scripts/deploy-ste.sh                # refresh-code.sh(§11) 트리거

# ── 재해복구: AIDataHub 를 Drive 덤프로 통째 교체(파괴적, 평소엔 불필요) ──
bash deploy/apptainer/sync-from-drive.sh
```

---

## 6. 주의 — 소스 검증 기준(런타임 미확인)

- 이 가이드는 **스크립트를 읽어** 검증했고, cae00 에서 실제로 돌려 확인한 것이 아니다. 종료코드·재프로비저닝·Drive 반입의 실제 성패는 박스 상태에 달렸다.
- **박스별(gitignore) 미확인**: `provision.env` 토큰, rclone remote, AIDataHub `.env` 의 실제 API 포트, `routes.local.env` 의 ste= 값, ste-tunnel 서비스 구동 여부.
- **그라운딩의 실제 전제 미확인**: cae00 AIDataHub 에 `xd-cae-*`(스파인 7석 + 발굴 대상) 전문가·records 가 실제 동기화돼 있는지 — 이게 그라운딩이 "빈 근거"가 아니라 실제 인용으로 채워지는 배포측 조건이다. 재기동·업로드·병합 후 §3 검증 방법으로 확인할 것.
- dev 에서 `backup-to-drive`/`export-*` 를 **크론으로 도는지 수동인지** 미확인 — 이 가이드는 명령만 정리했다.

## 2026-09-02 반영분 — update-all 후 확인·1회 조치

`git pull && update-all` 로 자동 반영되는 것.
- 심의 파이프라인 절단·유실 수정 전체(워크플로 JS 는 §1a 동기화, agent-server·게이트웨이는 §4).
- AIDataHub **데이터**(§3 병합) — `material-twin-analyst` 승격 페르소나, 물성 지식 41건 바인딩,
  재료 카드 2,688건. dev 가 `export-to-drive.sh` 로 올린 sync JSONL 을 §3 이 머지한다.

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

