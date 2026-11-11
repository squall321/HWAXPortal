> 원문 — cae00 운영의 결과 보고 · 요청(2026-11-11, 사용자가 같은 날 이 세션에 붙여 줌). 표 줄 사이의 빈 줄만 걷었고 내용은 그대로다. 받는 몫은 [PLAN.md](PLAN.md) · 결정은 [context-notes.md](context-notes.md).

# cae00 받은 편지함 답(11-08 남은 것 · 11-09) · 11-11 업데이트에서 나온 요청

작성일은 2026-11-11 입니다.

cae00 에서 11-11 16:32 ~ 18:55(2시간 23분) update-all 을 돌렸고 종료코드 0 이었습니다. ste 배포는 routine 이라 건너뛰었습니다.

같은 날 19:09 에 운영 사본(`stepforge-prod` · `dynaforge-prod`)도 cae00 과 같은 판으로 올렸습니다(사용자 결정).

기준 판은 다음과 같습니다.

| 대상 | 판 |
|---|---|
| 포털 | `9f1b3ddc` |
| 게이트웨이 | `c47e883` |
| 에이전트 서버 | `5cd1938` |
| KooRemapper(DynaForge) | 리포 `b42a6d2` · 바이너리 `c5f74c18`(Drive `dist-20261108-234149Z`, revision `e6407dc`) |
| StepForge | `f1d9932`(Drive `dist-20261109-000024Z`, SIF `d0cd6b65…`) |
| 운영 사본 묶음 | `r20261111a` — 위 StepForge · KooRemapper 판 그대로 |

이 문서는 두 부분입니다.

- 1부는 받은 편지함 물음의 답입니다. 물음 번호마다 한 절입니다.

- 2부는 이번 실행과 운영 사본 올리기에서 나온 개발 쪽 요청입니다.

주소 · 실제 이름 · 과제 이름은 뺐습니다. 경로는 리포 안 경로와 설치 자리만 적었습니다. 값을 볼 수 없었던 것은 '못 봄' 과 까닭을 적었습니다.

## 한눈에 보기

| 글 · 번호 | 결과 | 개발 쪽이 할 것 |
|---|---|---|
| 11-09 Q1 DynaForge 새 판 | 넷 다 맞습니다 | 없음 |
| 11-09 Q2 사용자 알림 | 판이 올라가 이제 알릴 수 있습니다. 보내는 것은 사용자 몫입니다 | 없음 |
| 11-09 Q3 stcx 후처리 Post v51 | **아직 안 깔렸습니다**(지금 v50). 운영 측 설치 몫입니다 | 없음 |
| 11-09 Q4 StepForge 다섯째 묶음 | 됐습니다 | 없음 |
| 11-09 Q5 전처리 v135 SIF | **아직 안 깔렸습니다**(지금 10-29 판). 운영 측 설치 몫입니다 | 없음 |
| 11-09 Q6 코어 어휘 셋 | 이 문서에는 없습니다(아직 뽑지 않았습니다) | 없음 |
| 11-09 Q7 운영 사본이 판을 받는 길 | 이 박스 운영이 cae00 에서 손으로 올립니다. 같은 때 넣는 길이 있고, 11-11 에 지금 판을 그 길로 넣었습니다 | ST-14 질문 |
| 11-08 Q1 update-all | 11-08 실행(11-09 에 답함)과 11-11 실행 모두 종료코드 0 · ✗ 0 입니다 | 2부 |
| 11-08 Q2 사용자 알림 | 사용자 몫입니다 | 없음 |
| 11-08 Q3 앞 글(11-07)의 확인 | 11-09 에 답했습니다. Q5-2 만 미뤘습니다 | 없음 |
| 11-08 Q4 발표자료로 | 0절 · 1절 · ④ 는 됐습니다. ①②③ 은 사람 로그인을 기다립니다 | 없음 |
| 11-08 Q5 ste 해석기 깔기 | **못 했습니다.** 글의 설치 자리가 계산 노드에서 보이지 않습니다 | **PA-21** |

2부 요청은 아홉 건입니다.

| 번호 | 대상 | 무엇 | 높이 |
|---|---|---|---|
| PA-21 | ste 묶음 · 해석기(KooSolverContainer) | 해석기 SIF 를 둘 자리 — `/opt/apps/sif` 가 계산 노드에서 보이지 않습니다 | 높음 |
| HP-63 | HWAXPortal(`docs/aidh-parts-sync`) | 조각 목록이 11-08 뒤로 새로 나오지 않습니다 — dev 의 하루 한 번 예약(AP-15)이 걸리지 않았습니다 | 중간 |
| HP-64 | HWAXPortal(update-all §3) · AIDataHub | 병합이 HE팀 운영자 글을 매 실행 dev 판으로 덮습니다(HP-35 의 다음 걸음) | 중간 |
| HP-53(다시) | HWAXPortal(`he-team.json`) | 운영자 일곱 명의 `writes` · `confirm` 밖 쓰기 도구(cae00 에만 있는 둘은 우리가 박스에서 고칩니다) | 중간 |
| ST-13 | StepForge | `disclosure.tools` 184 · `mcp_tools` 192 | 낮음 |
| ST-14 | StepForge | 새 판이 옮긴 DB 로 옛 판이 뜨는지(되돌리기) | 질문 |
| KR-24 | KooRemapper | 배포 바이너리가 '깨끗하지 않은' 작업 트리에서 지어졌습니다 | 낮음 |
| HG-30 | HWAXMcpGateway | `tool_areas.json` 에 `devlab-checklist` 가 없습니다 | 낮음 |
| HH-17 | DocForge | `docforge_list_inputs` 의 `root_host` 가 비어 있습니다 | 낮음 · 질문 |

---

# 1부. 받은 편지함 답

## 11-09 Q1. DynaForge 새 판

1. health — status ok · `revision` `e6407dc…` · `revision_matches_binary` true · published 2026-11-08T23:41:52Z · DB ok 입니다. 응답은 `data` 안에 싸여 있습니다.

2. 바이너리 sha256 — `c5f74c18…` 로 맞습니다. BUILD_INFO 의 stage 는 `dist-20261108-234149Z` 입니다.

3. 시스템 상태 — `operations` 65 · MCP 도구 89 로 글과 같습니다(11-11 다시 읽음). 마이그레이션은 상태 응답에 없어서, 같은 판을 올린 운영 사본 DB 에서 0020 으로 읽었습니다.

4. 되돌릴 판은 글대로 `dist-20261107-083706Z` 입니다. 바로 앞 바이너리(`15d013ec…`)는 update-all 직전 백업에도 있습니다.

덧붙임 — BUILD_INFO 의 describe 끝에 `-dirty` 가 붙어 있습니다. 2부 KR-24 에 적었습니다.

## 11-09 Q2. 동작 변화 여덟 · 결과가 바뀌는 고침 넷

판이 올라갔으므로 이제 알릴 수 있습니다. 글의 Q2 1 ~ 8 과 고침 넷을 그대로 보내면 됩니다.

보내는 것은 사용자 몫이고, 11-08 Q2 알림과 한 번에 묶어도 됩니다. 보냈는지는 사용자 답을 기다립니다.

## 11-09 Q3. stcx 후처리 이미지 Post v51(운영 측 설치)

- stcx(356대)에는 지금 v50(`2780f20`, 11-09 설치)이 있습니다. v51(SIF sha256 `32997e9b…`, 안의 VERSION `226eca7`)은 아직 안 깔렸습니다.

- 순서 조건(이 박스 DynaForge 가 `32cc364` 이상)은 11-08 실행(`752fa2b`)부터 이미 채워져 있었고, 지금 판(`e6407dc`)도 채웁니다.

- 이 박스에서 stcx 로 밀어 넣는 절차는 없습니다. 넘길지와 누가 깔지는 사용자가 정합니다. 이 문서를 쓸 때까지 아직 넘기지 않았습니다.

## 11-09 Q4. StepForge 다섯째 묶음

- 허브의 `step_forge.sif` sha256 은 `d0cd6b65…` 로 Drive 와 같습니다. `.sif.hash` 는 `99e5400f` 입니다(앞 판 `095ee5d3`).

- 인스턴스가 떴고 앱 health 는 200 입니다. 허브 경로는 401(로그인 필요)로 정상입니다.

- 게이트웨이 도구 수는 전체 카탈로그 기준 1,764 → 1,764 입니다. update-all 기록과 `/health` 는 1,743 → 1,743 으로 셉니다. 어느 쪽이든 글의 '새 도구 없음' 과 맞습니다.

- `system_capabilities` 의 build sha 는 `f1d9932…` · `mcp_tools` 192 입니다.

## 11-09 Q5. 전처리 이미지 v135 SIF(운영 측 설치)

- stcx 에는 지금 10-29 판이 있습니다(안의 KooRemapper `8c7c4f87…`).

- v135 **SIF**(sha256 `da892a35…`, 안의 KooRemapper `c5f74c18…`)는 아직 안 깔렸습니다. 같은 이름의 tar 와 v134 는 넘기지 않습니다.

- 넘길지와 누가 깔지는 사용자가 정합니다. 이 문서를 쓸 때까지 아직 넘기지 않았습니다.

## 11-09 Q6. 코어 어휘 셋

이 문서에는 없습니다. 아직 뽑지 않았습니다. 뽑으면 글이 적은 대로 사용자를 거쳐 파일로 넘깁니다.

## 11-09 Q7. 운영 사본이 새 판을 받는 길

1. **누가 · 어떤 길** — 두 운영 사본은 이 박스 운영(사용자)이 cae00 에서 손으로 올립니다.

   - 순서는 묶기 → 보내기 → 바꾸기 입니다. 묶음에는 cae00 에서 지금 도는 StepForge SIF 와 KooRemapper 리포 · 바이너리를 그대로 담습니다.

   - 그래서 dev 가 받은 편지함으로 알린 판은 cae00 update-all 을 거친 뒤, 사용자가 정할 때 운영 사본에 들어갑니다. 자동으로 따라가지는 않습니다.

   - update-all 은 운영 사본에 손대지 않습니다.

2. **같은 때 넣을 수 있나** — 넣는 길은 있습니다. 11-11 19:09 에 지금 판(`r20261111a`)을 그 길로 넣었습니다.

   - 코어와 잇는 판은 아직 나오지 않았습니다. 나오면 cae00 update-all 뒤에 같은 묶기 → 보내기 → 바꾸기로 넣습니다. 넣는 때는 사용자가 정합니다.

   - 이번 묶음 `r20261111a` 는 StepForge `f1d9932` · KooRemapper `b42a6d2` / 바이너리 `c5f74c18` 입니다. 앞 판은 `r20261106a` 였습니다.

   - 바꾸기 직전 cae00 심의 0, 운영 사본 잡 0 을 봤습니다. 되돌림용 DB 백업과 그 사본을 남겼습니다.

   - 바꾼 뒤 두 앱 health ok, DynaForge DB ok, 마이그레이션 0020 그대로입니다.

   - 게이트웨이가 다시 읽은 운영 사본 도구 수는 StepForge 184 → 192(넷째 묶음 도구 8 — cae00 은 11-08 부터 192), DynaForge 89 그대로입니다.

   - 새 StepForge 는 처음 뜰 때 DB 를 앞으로 옮겼습니다(새 표 7). 되돌릴 때 이것이 걸리는지 2부 ST-14 로 묻습니다.

3. **운영 사본 StepForge 웹에서 사람이 후보를 확정 · 거절할 수 있나** — 못 봄입니다. 사람이 로그인한 화면이 있어야 해서 이번에는 도구 응답과 상태만 봤습니다.

## 11-08 Q1. update-all

- 11-08 20:37 ~ 22:04 실행(1시간 27분)이 종료코드 0 · ✗ 0 이었고 11-09 에 답했습니다.

- 11-11 실행도 종료코드 0 · ✗ 0 입니다. 끝 줄은 '전체 최신화 완료 — 운영 준비 상태' 입니다.

- 안 뜬 앱은 `heax_demo_nextjs` 하나로 예전부터 그렇습니다.

- 끝 요약의 ⚠ 줄 가운데 개발 쪽 몫은 2부에 적었습니다(HP-63 · HP-64 · HP-53 · HG-30). 나머지는 '이 문서에서 뺀 것' 에 있습니다.

## 11-08 Q2. 사용자 알림

보내는 것은 사용자 몫입니다. 11-09 에 초안을 사용자에게 건넸습니다. ste 새 앱 넷은 배포하지 않았으므로 그 줄은 넣지 않았습니다.

## 11-08 Q3. 앞 글(11-07 Q1 ~ Q5)의 확인 — 11-09 에 답함

| 번호 | 결과 |
|---|---|
| 11-07 Q1 DocForge 0.3.1 | 넷 다 됐습니다(판 0.3.1 · 도구 여섯 · 동기화를 막는 줄 없음 · 시험 변환 잡 끝남). 시험 변환은 도구 길로 했고, 챗에서 말로 시키는 길(HA-29)은 사람 몫으로 남았습니다. 눈에 띈 것은 2부 HH-17 입니다 |
| 11-07 Q2 새 SIF 셋 | doc-forge · web-design-agents · laminate-analyzer-mcp 셋 다 떴습니다 |
| 11-07 Q3 SignalForge 다시 태깅 | 2절 dry-run 고침 0 이라 `--apply` 는 하지 않았습니다. MV 기록 폴더는 없습니다(이 박스는 Redis 가 없어 worker · beat 가 일하지 않습니다 — update-all 이 의도된 상태로 적습니다). 5절 수는 사용자에게만 건넸습니다 |
| 11-07 Q4 KooRemapper 11-07 판 | 넷 다 맞았습니다(revision · `apply_carryover_plan` · operations 65 · sha) |
| 11-07 Q5 단면 · 적층 넷 | 1 은 됐습니다(`routine_read` 에 있고 `write` 에 없음). 2 는 미뤘습니다(사용자 결정 11-09) — 포털 개인 토큰 화면에 '읽기만' 선택지가 없습니다. 서버 API 는 읽기 전용 발급을 받지만 화면은 늘 읽기 + 쓰기로 냅니다 |

## 11-08 Q4. 발표자료로

1. 0절 — 허브의 WDA `.sif.hash` 가 `bbe26b5a` 로 시작하고, features 에 `owner`, formats 의 `delib-16x9` 가 active, 허브를 거친 익명 요청이 401 이었습니다. **됐습니다.**

2. 1절 — 11-09 06:03 에 `WDA_DECK_ENABLED=true` 를 적고 포털만 다시 띄웠습니다. **됐습니다.** 11-11 update-all 뒤에도 켜진 그대로입니다.

3. 2절 — ④(익명 `/api/runs` → 401)는 **됐습니다.** ①②③ 은 로그인한 화면과 둘째 계정이 있어야 해서 사람을 기다립니다. 그때까지 켜 둡니다.

## 11-08 Q5. ste 새 앱 넷의 해석기 깔기

**못 했습니다.** 글이 적은 설치 자리(`/opt/apps/sif`)가 계산 노드에서 보이지 않습니다. 자세한 것과 묻는 것은 2부 PA-21 입니다.

ste 새 묶음(`d779f659b421`)도 이번에 배포하지 않았습니다(routine 이 ste 를 건너뜀). 자리가 정해진 뒤 묶음 배포와 해석기 깔기를 함께 할지는 사용자가 정합니다.

---

# 2부. 새 요청

## PA-21 (높음) ste 해석기 SIF 를 둘 자리 — 계산 노드에서 `/opt/apps/sif` 가 보이지 않습니다

**대상** — ste 묶음(새 앱 넷 reddish · part-study · part-study-registry · radioss)과 해석기 묶음을 낸 쪽(KooSolverContainer · ste 세션)

**본 것**(11-11, 읽기만, ste 24대 가운데 헤드와 계산 노드 1대)

- 11-08 글 Q5 는 '헤드의 `/opt/apps` 는 계산 노드가 읽기 전용 NFS 로 보고 … 헤드 한 곳에 두면 24대가 다 본다' 고 적었습니다. 본 것은 다릅니다.

- 헤드의 `/opt/apps` 는 로컬 디스크이고, 아래에는 `sif-web` 과 `ste` 두 폴더뿐입니다. `/opt/apps/sif` 는 없습니다.

- 헤드의 `/etc/exports` 에는 살아 있는 줄이 없습니다. `/etc/exports.d` 는 이번에 보지 않아 못 봄입니다.

- 살펴본 계산 노드 1대에는 `/opt/apps` 가 아예 없고, 붙인 공유는 `/data` · `/data2` · `/data3` 셋입니다. 나머지 23대는 한 대만 살펴봐서 못 봄입니다.

- 공유 `/data/SmartTwinSolutions/` 아래에는 KooOpenFOAM · KooOpenLB · KooSPH 셋만 있습니다.

- condensation 앱은 이미 공유 폴더로 비켜 갑니다.

  - app.yaml:21 은 `sif: /opt/apps/sif/koo_openfoam.sif` 입니다.

  - `ste/condensation/ste-run.sh:30-36` 이 솔루션 폴더를 `KOO_SOLUTION_DIR` → `${STE_SOLUTIONS_DIR:-/data/SmartTwinSolutions}/KooOpenFOAM` → `/opt/apps/KooOpenFOAM` 순으로 잡습니다.

  - `ste-run.sh:37-41` 은 app.yaml 의 SIF 가 없으면 솔루션 폴더 안 → `/opt/apps/sif` → 노드 로컬 `/opt/apptainers` 순으로 찾습니다.

  - 공유 KooOpenFOAM 폴더에 `scripts/build_case.py` 와 `koo_openfoam.sif`(819,671,040 B — 글의 크기와 같고, sha256 은 대조하지 않았습니다)가 있습니다. 그래서 이 순서대로라면 공유 폴더의 SIF 를 씁니다. 실제 잡 기록으로 확인하지는 않았습니다.

- `ste-run.sh:15` 주석도 '계산노드엔 NFS ro 로 보인다' 고 적지만, 살펴본 노드에는 `/opt/apps` 가 없습니다.

**그래서 생기는 일**

- 글대로 깔면 SIF 가 헤드에만 있고 노드에서는 보이지 않습니다.

- 글의 표대로라면 넷 다 실행 단계에서 실패합니다. reddish · part-study-registry · radioss 는 하나라도 없으면 실패하고, part-study 도 `koo_stebridge.sif` 가 필수라 실패합니다.

- 글의 1단계(`ls -l /opt/apps/sif/koo_openfoam.sif` — 있으면 건너뜀)는 폴더가 없어 늘 '없음' 이 됩니다. 같은 파일은 이미 공유 KooOpenFOAM 폴더에 있습니다.

**묻는 것**

1. SIF 넷(`koo_fenics` · `koo_stebridge` · `koo_radioss` · `koo_openfoam`)을 어디에 둘지 정해 주십시오.

   - 예 ① 공유 `/data/SmartTwinSolutions/<해석기>/` 아래 — 지금 KooOpenFOAM 처럼(`/data/SmartTwinSolutions/KooOpenFOAM/koo_openfoam.sif`). 글의 4단계도 KooFEniCS 묶음을 이 아래에 풉니다.

   - 예 ② 노드 로컬 `/opt/apptainers`(24대에 하나씩).

   - 예 ③ 헤드의 웹 'SIF 올리기'(`/opt/apps/sif-web`)를 쓰는 길 — condensation app.yaml:18 은 '웹 업로드는 `/opt/apps/sif-web` 에 놓이므로 이 앱이 집지 않는다' 고 적습니다. 노드에서 보이는지도 함께 알려 주십시오.

2. 새 앱 넷의 설정 · 코드가 `/opt/apps/sif` 를 박아 두었는지 알려 주십시오. 박아 두었다면 condensation 처럼 찾는 순서(솔루션 폴더 → `/opt/apps/sif` → `/opt/apptainers`)를 넣거나, 1 의 자리로 바꾼 묶음이 필요합니다.

3. ste 앱 스크립트(`/opt/apps/ste/<앱>/`)를 계산 노드가 어떻게 읽는지 알려 주십시오. 잡 폴더로 옮겨 두는 것이라면 괜찮고, 노드에서 직접 읽는다고 보았다면 새 앱 넷에도 같은 문제가 생깁니다.

**확인하는 법** — 자리가 정해지면 글의 1단계(이미 있는지 보기) · sha256 대조 · 연막 시험 둘(reddish · radioss)을 그 자리로 다시 적어 주십시오. 1단계는 공유 KooOpenFOAM 폴더를 먼저 보게 해 주십시오. 깔기는 사용자 결정 뒤 사람이 합니다.

## HP-63 (중간) 조각 목록이 11-08 뒤로 새로 나오지 않습니다 — dev 의 하루 한 번 예약(AP-15)이 걸리지 않았습니다

**대상** — HWAXPortal `docs/aidh-parts-sync`(AP-15 — dev 의 `parts-to-drive.sh` 하루 한 번 예약)

**본 것** — 11-11 update-all §3 이 이렇게 적고 전체 덤프 길로 갔습니다.

```

조각 목록(manifest-20261108-003457Z.json)이 전체 덤프(aidh-db-20261111-044502Z.sql.gz)보다 76시간 낡았다

— dev 의 하루 한 번 내기(parts-to-drive.sh)가 멈췄다. 전체 덤프 길로

```

- 마지막 조각 목록은 2026-11-08 00:34 UTC 입니다. 전체 덤프는 그 뒤로도 매일 나옵니다.

- update-all 은 '멈췄다' 고 적지만, 예약은 처음부터 걸리지 않은 것으로 보입니다. `docs/aidh-parts-sync/checklist.md:8` 이 아직 열려 있습니다 — '[ ] dev cron(전체 덤프 뒤) — **사용자 몫**: 넣으려던 줄은 자동 모드 분류기가 막았다(AP-15)'. 그동안 나온 조각 목록은 손으로 한 번씩 낸 것으로 보입니다(추정 — dev 의 실행 기록은 이 박스에서 볼 수 없습니다).

- 그동안은 낡음 검사(AP-14)가 cae00 을 전체 덤프 길로 돌립니다. 11 GB 내려받기 · staging 적재 · 표 병합이고, 11-11 실행 2시간 23분 가운데 약 1시간 30분이 이 길이었습니다.

- 병합 결과는 정상이었습니다. 단면 표에 272행이 더해졌고 나머지 표는 +0 이었습니다. 잃은 데이터는 없습니다.

**바라는 것**

1. dev 에 하루 한 번 예약을 걸어 주십시오. 체크리스트대로 사용자가 dev 에서 직접 걸 몫이라면 그렇다고 알려 주시고, 넣을 줄을 체크리스트에 그대로 적어 주십시오. 사용자가 그 줄을 넣습니다.

2. 조각 내기가 실패하거나 하루 넘게 안 돌면 dev 쪽에서 알 수 있게 해 주십시오. 지금은 운영 쪽 update-all 이 돌 때에야 드러납니다.

3. (선택) 조각 목록을 전체 덤프와 같은 예약에서 함께 내는 방법도 있습니다. 그러면 둘이 어긋날 일이 줄어듭니다.

**확인하는 법** — 체크리스트 8줄이 닫히고, 다음 update-all §3 이 '조각 길' 로 가며 ⚠ 줄이 없으면 됩니다.

## HP-64 (중간) 병합이 HE팀 운영자 글을 매 실행 dev 판으로 덮습니다 — HP-35 의 다음 걸음

**대상** — HWAXPortal `infra/scripts/update-all.sh` §3 · `infra/scripts/sync-he-personas.py`, (가)라면 AIDataHub `deploy/apptainer/merge-from-drive.sh` 도

**본 것**

- HP-35 의 미리보기 알림은 들어왔습니다. 그 알림이 실제로 매 실행 뜹니다.

  - 11-03 5명, 11-05 2명, 11-08 4명, 11-11 3명이 '이 박스 판과 다르다' 였습니다.

  - 그때마다 사람이 백업을 뜨고 `sync-he-personas.py --apply` 를 돌렸습니다. 고친 뒤 미리보기는 0 이었습니다.

- 11-11 의 셋은 코어 온톨로지 · 보고서 아카이브 · DocForge 운영자의 `system_prompt` 였습니다.

  - 세 운영자는 이 박스에만 있는 앱(Report Archive · 세 데이터허브)의 도구를 씁니다.

  - 운영자 글이 박스의 앱 구성을 따라 달라지고, dev 덤프에는 dev 판 글이 들어 있는 것으로 보입니다(추정). 그렇다면 dev 쪽에서 무엇을 고쳐도 병합할 때마다 다시 덮입니다.

- 병합과 사람의 `--apply` 사이에는 챗 · 심의가 dev 판 운영자 글로 돕니다.

- 손 백업은 실제로 두 번 빠졌습니다.

  - 11-05 실행 뒤 적용 때는 백업을 뜨지 않았습니다.

  - 11-09 적용(11-08 실행 몫) 때는 백업 거르기가 엉뚱한 칸을 봐서 0건이었습니다. AIDataHub 의 운영자 행은 `agent_type` 으로 묶이는데, 다른 칸으로 걸렀습니다.

  - 11-11 은 `agent_type` 으로 걸러 21건을 받고 개수를 본 뒤 적용했습니다.

**바라는 것** — 아래 가운데 하나입니다. 우리는 (나)가 낫다고 봅니다. 병합 규칙을 바꾸지 않고, 지금 사람이 하는 일을 그대로 자동으로 하기 때문입니다.

- (가) §3 병합에서 he-* 운영자 행의 운영자 정의 칸을 건너뜁니다. 운영자의 정본은 `he-team.json` 과 박스 덧씌우기이고, §6 동기화가 그것만 씁니다. 병합은 AIDataHub `merge-from-drive.sh` 가 하므로 그쪽도 바뀝니다.

- (나) `update-all.sh` §3 끝에서 자동으로 이렇게 합니다. AIDataHub 는 바뀌지 않습니다.

  1. he-* 운영자를 `agent_type` 기준으로 백업합니다.

  2. 백업 개수가 운영자 수와 맞는지 봅니다. 맞지 않거나 0 이면 멈추고 알립니다(11-09 의 0건 백업이 이 걸음으로 막힙니다).

  3. `--apply` 를 돌립니다.

  4. 미리보기가 0 인지 봅니다.

**확인하는 법** — 다음 update-all 끝 요약에 '페르소나 N명이 이 박스 판과 다르다' 줄이 없으면 됩니다. (나)라면 백업 폴더와 개수가 기록에 찍혀야 합니다.

## HP-53(다시) (중간) 운영자 일곱 명의 `writes` · `confirm` 밖 쓰기 도구 — 11-11 수

**대상** — HWAXPortal `infra/personas/he-team.json`

**본 것** — HP-53 의 미리보기 알림은 들어왔습니다. 11-11 update-all §6 이 '운영자 11명의 앱에 `writes` · `confirm` 어디에도 없는 쓰기 도구가 있다' 를 냈습니다.

기록에 줄로 찍힌 것은 10명입니다. 나머지 1명은 줄이 없어 못 봄입니다. 그 가운데 he-cad-stepforge 3개(onto_define · onto_link · onto_put)는 문서대로 정상입니다(C-30). 남은 9명은 다음과 같습니다.

| 운영자 | 수 | 기록에 찍힌 도구(앞 8개까지) | 앱이 dev 에도 있나 | 누가 고치나 |
|---|---|---|---|---|
| he-sim-dynaforge | 10 | attach_cad · attach_cae_package · attach_render · confirm_task_alias · recipe_deprecate · remove_task_alias · save_result_to_path · set_report_revision 외 2 | 예 | dev |
| he-calc-laminate | 2 | run_progressive_failure · run_sensitivity_analysis | 예 | dev |
| he-data-aidatahub | 1 | draft_agent | 예 | dev |
| he-doc-mxwhitepaper | 1 | upload_image_bytes | 예 | dev |
| he-doc-webdesign | 1 | approval_record | 예 | dev |
| he-doc-docforge | 31 | add_object_alias · add_report_tags · create_embed_bundle · create_html_report · create_object · create_report_draft · create_report_from_format · create_report_from_preset 외 23 | 섞임(DocForge 는 예, Report Archive 도구는 cae00 에만) | dev 먼저(아래 2) |
| he-doc-reportarchive | 17 | add_object_alias · create_embed_bundle · create_html_report · create_object · create_report_from_format · create_sp_properties · create_sp_relation_types · create_sp_types 외 9 | 섞임으로 봄(어느 앱 도구인지 이 기록만으로 다 가르지 못함) | dev 먼저(아래 2) |
| he-data-arp | 5 | arp_upload_detect · arp_upload_meta · arp_upload_open · arp_upload_staged · arp_upload_targets | 아니오(cae00 에만) | 우리(박스) |
| he-data-coreontology | 3 | caegroupdatahub_document_write · failuretrace_document_write · rootdesigndatahub_document_write | 아니오(cae00 에만) | 우리(박스) |

기록은 운영자마다 도구 이름을 8개까지만 찍습니다(`infra/scripts/sync-he-personas.py:57` `LOOSE_SHOW`). 전체 목록은 dev 에서 `sync-he-personas.py` 미리보기를 돌리면 나옵니다.

**바라는 것**

1. dev 에도 있는 앱의 쓰기 도구를 `he-team.json` 의 `writes`(잡 · 쓰기) 또는 `confirm`(지우기 · 권한 · 되돌리기 어려운 것)에 넣어 주십시오. '예' 다섯 명 전부와, 섞인 둘의 dev 쪽 도구입니다.

2. 섞인 둘(he-doc-docforge · he-doc-reportarchive)은 1 을 먼저 끝내 주시거나, 두 목록 가운데 어느 항목을 dev 가 맡는지 알려 주십시오.

   - 박스 덧씌우기(`he-team.local.json`)는 JSON merge patch(RFC 7386)라서 목록을 통째로 바꿉니다(`infra/personas/he_team.py:9` · `:26`, `docs/he-team-overlay/PLAN.md:26-27`).

   - 그래서 우리가 이 둘의 `writes` 를 박스에서 적으면, 그 뒤 dev 가 더한 항목을 박스 판이 덮습니다.

**우리가 할 것(요청 아님)** — cae00 에만 있는 앱의 운영자 둘(he-data-arp · he-data-coreontology)은 박스 덧씌우기로 `writes` · `confirm` 을 채웁니다. `docs/he-team-overlay/PLAN.md:46` 의 규칙('dev 에 없는 앱의 운영자는 dev 에서 고치지 않는다 — cae00 이 박스 파일에서 고친다')대로입니다. 그래서 HP-53 원문의 ARP · 코어 허브 몫은 거둡니다.

**왜** — 두 목록 밖 도구에는 '요청했을 때만 부른다' · '확인을 받은 뒤 부른다' 안내가 붙지 않습니다. HA-29 의 코드 관문이 읽을 목록도 빕니다(HP-53 원문).

**확인하는 법**

- dev 의 고침 뒤 — dev 미리보기의 '목록 밖 쓰기' 에서 '예' 다섯 명과 섞인 둘의 dev 쪽 도구가 사라지면 됩니다.

- 우리 덧씌우기까지 들어간 뒤 — 다음 cae00 update-all §6 의 '목록 밖 쓰기' 줄이 he-cad-stepforge 하나만 남으면 됩니다.

## ST-13 (낮음) StepForge `disclosure.tools` 184 · `mcp_tools` 192

**본 것** — cae00 StepForge(`f1d9932`)의 `system_capabilities` 가 `mcp_tools` 192 · `catalog.total` 192 인데 `disclosure.tools` 는 184 입니다. 운영 사본도 같은 판이라 같습니다.

- 수는 넷째 묶음에서 늘어난 도구 8개(carryover_report · list_fill_rules · onto_cad_view · onto_candidates · onto_define · onto_link · onto_put · save_fill_rule)와 맞습니다. 여덟 다 카탈로그에는 있습니다.

- 어느 도구가 빠졌는지는 응답에 이름이 없어 못 봄입니다. 위 여덟은 수가 맞는 데서 나온 추정입니다.

**바라는 것** — 새 도구 여덟의 disclosure 항목을 채우거나, 일부러 뺀 것이면 `system_capabilities` 에 빠진 도구 이름을 함께 실어 주십시오.

**확인하는 법** — 다음 판의 `system_capabilities` 에서 `disclosure.tools` 가 `mcp_tools` 와 같거나, 빠진 도구 이름이 함께 나오면 됩니다.

## ST-14 (질문) 새 판이 옮긴 DB 로 옛 판이 뜨는지

**본 것** — 운영 사본 StepForge 가 앞 판(`2f5e903`)에서 `f1d9932` 로 바뀌며 처음 뜰 때 DB 를 앞으로 옮겼습니다(새 표 7). 바꾸기 직전 DB 백업은 남겼습니다.

**묻는 것** — 옛 판(`2f5e903`)이 이렇게 옮긴 DB 로 떠도 되는지 알려 주십시오.

- 된다면 되돌릴 때 판만 되돌립니다.

- 안 된다면 판과 함께 백업 DB 도 되돌려야 하고, 그 사이에 쌓인 데이터는 잃습니다. 그렇다면 되돌릴 때 지켜야 할 것을 알려 주십시오.

## KR-24 (낮음) 배포 바이너리가 '깨끗하지 않은' 작업 트리에서 지어졌습니다

**본 것** — Drive `dist-20261108-234149Z` 의 KooRemapper BUILD_INFO 입니다.

```

describe : v1.7.0-1055-ge6407dc-dirty

worktree : dirty — .bkit/runtime .bkit/snapshots .bkit/state platform/infra

```

`revision_matches_binary` 는 true 라서 지금 문제는 없습니다. 다만 `platform/infra` 가 바뀐 채 지어졌다면 리포의 그 판으로 같은 바이너리를 다시 지을 수 없을 수 있습니다.

**바라는 것** — 깨끗한 트리에서 짓거나, 빌드와 무관한 경로(`.bkit/*`)는 dirty 판정에서 빼 주십시오. `platform/infra` 의 차이가 빌드에 들어갔는지 알려 주십시오.

**확인하는 법** — 다음 판 BUILD_INFO 의 describe 에 `-dirty` 가 없거나, worktree 줄에 `.bkit/*` 만 남으면 됩니다.

## HG-30 (낮음) `tool_areas.json` 에 `devlab-checklist` 가 없습니다

**본 것** — 11-11 update-all 이 '새 앱 개발실 체크리스트(devlab-checklist, 붙은 지 2일) — 영역 없는 도구 9/9개' 를 냈습니다. 그래서 영역 고르기 화면에서 이 앱 도구 아홉이 '미분류' 입니다.

**바라는 것** — 게이트웨이 리포 `tool_areas.json` 의 `apps` 에 `"devlab-checklist": "<영역>"` 한 줄을 넣어 주십시오. 기판 설계 검증 도구라서 CAD 쪽 영역이 맞다고 봅니다. 영역 키는 같은 파일의 `areas` 에서 골라 주십시오.

**확인하는 법** — 다음 update-all 에 devlab-checklist 의 '영역 없는 도구 9/9개' 줄이 없으면 됩니다.

## HH-17 (낮음 · 질문) `docforge_list_inputs` 의 `root_host` 가 비어 있습니다

**본 것** — 11-07 Q1 시험(11-09) 때 `docforge_list_inputs` 가 컨테이너 안 경로만 주고 `root_host` 는 null 이었습니다. 그 경로로 `docforge_convert` 를 부르면 변환은 잘 됩니다.

**묻는 것** — `root_host` 가 null 인 것이 의도인지 알려 주십시오. 의도라면 응답에 '이 경로를 그대로 convert 에 넘긴다' 는 안내 한 줄이 있으면 챗이 헷갈리지 않습니다.

**확인하는 법** — 다음 판에서 `root_host` 가 채워지거나, 응답에 그 안내 줄이 있으면 됩니다.

---

## 이 문서에서 뺀 것

- **운영 사본의 단면 · 적층 넷**(section_pair_view · section_batch · compare_stackup · stackup_figure)은 운영 사본에서 쓰기 표지 그대로 둡니다(사용자 결정 11-11). 요청하지 않습니다.

- **11-07 Q5-2 포털 개인 토큰의 '읽기만' 선택지** — 사용자 결정(11-09)으로 미뤘고, 이번에도 요청하지 않습니다. 11-07 Q5-2 는 열린 채 둡니다.

- **박스 설정으로 고칠 것은 우리 몫입니다.**

  - 11-10 에 세 데이터허브가 옮겨진 뒤, 코어 거울 받기 설정이 옛 주소를 봅니다.

  - 운영 사본의 환경 값 몇 가지가 아직 비어 있습니다.

  - 운영 사본 되돌리기 절차를 정리하는 일도 우리 몫입니다.

  - cae00 에만 있는 앱의 운영자 둘의 `writes` · `confirm`(HP-53(다시) 참고).

- **개발실 체크리스트의 인자 설명 0/26** — 우리가 만든 중계 서버라 우리가 고칩니다.

- **SIREN 의 이름 겹침**(`list_groups` 가 matnexus 와 겹침)**과 인자 설명 0/12** — SIREN 팀 몫입니다. 인자 설명은 19-SIREN R-8 에 이미 있고, 이름 겹침은 19 에 더할 거리입니다.

- **SmartTwin 운영자의 앱이 이 게이트웨이에 없음** — 예전부터 있던 것이고 HP-51 · HP-54 에 있습니다.

- **외부 연결 fmea 가 붙지 않음 · `heax_demo_nextjs` 미서빙** — 그쪽 서버와 이 박스의 상태라 요청하지 않습니다.

- **11-09 Q6 코어 어휘** — 따로 뽑아 사용자를 거쳐 넘깁니다.

- **ste 묶음 배포 · 해석기 깔기 · stcx 이미지 설치** — 사용자 결정과 운영 측 몫입니다. PA-21 의 답을 받은 뒤 정합니다.
