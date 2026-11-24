# 운영 요청 모음(11-24) — 다른 세션 몫을 코드와 맞대 계획하고 나눠 보낸다

> 요청서 [request.md](request.md)(운영 박스가 11-24 기준으로 모은 안 끝난 요청 — 1절 121 · 2절 MCP 효율 · 3절 170 · 4절 결정 대기 56) ·
> 할 일 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md).

사용자 지시(11-24) — 「여기서 관리하는 플랫폼은 빼고 나머지를 확인해 고칠 것의 계획을 세우고 각 세션에 보낸다」.
요청서의 판정(「새 요청」 · 「받았으나 안 끝남」)을 그대로 넘기지 않고, 항목마다 받을 저장소의 지금 HEAD 와 맞댔다(11-25, 서브에이전트 다섯 — 읽기만).
줄의 낱말이 아니라 코드 · 커밋으로 판정한다(L21-8).

## 1. 몫 가름

| 절 | 받을 곳 | 이 문서에서 |
|---|---|---|
| 1-1 ~ 1-3 · 2절 G · A · P | 포털 · 게이트웨이 · 에이전트 서버 | **뺌 — 미배정**(hwaxportal-87 이 사용자에게 여쭙기로 함, R25-1). 87 의 미병합 가지가 같은 파일을 만진다 — 아래 '겹침' |
| 1-6 · 1-8 | 리스크 앱 · AIDataHub | **뺌 — 미배정.** 따로 세션이 없고 포털 세션들이 고쳐 온 저장소다 |
| 1-4 | StepForge | `stepforge-d4` 에 보냄 |
| 1-5 · IR-51(DocForge 몫) · IR-24(원본) | DocForge | `docforge-f6` 에 보냄 |
| 1-7 HH-18 · IR-24(사본) · SE-8 · 1-12 HP-71 | HEAXHub | `heaxhub-4b` 에 보냄 |
| 1-7 HH-10 | MaterialTwin | 보내지 않음 — 운영 쪽이 자연 키를 먼저 넘긴다(받은 편지함 10-31 Q1) |
| 1-9 · HP-71 | SignalForge | `signalforge-c6` 에 보냄 |
| 1-10 | MXWhitePaper | `mxwhitepaper-26` 에 보냄(질문 둘의 답 초안 확인) |
| 1-11 · HP-71 | KooRemapper | `kooremapper-4a` 에 보냄 |
| 3-2 | ste · 연계 브리지 | `smarttwinexplorer-06` · `koosolvercontainer-da` 에 보냄 — 21건 가운데 19건은 11-22 에 이미 보냈다(`../ste-stepforge-1117/`) |
| 3-10 | SmartTwin MCP | `smarttwinmcp-4c` 에 보냄 |
| 2절 B-1 · B-2 의 백엔드 몫 | HEAXHub 앱 · AIDataHub · SignalForge · MXWP · KooRemapper | **지금 보내지 않음** — 요청서가 운영 쪽 한 판(결과 손잡이 · 가벼운 보기 · 연결 기다림) 측정 뒤에 시작하라고 적었다 |
| 3절 나머지 | ReportArchive · PCB체크리스트 · SimFlow · Datahub 플랫폼 · ODB 허브 · ARP · FMEA · PLM 검색 · ComponentCore · GPU 운영 · MatNexus · SIREN · 허브 관리자 넷 · TestScope · SimEngBay | 보내지 않음 — 다른 팀 몫이라 운영 쪽이 담당에게 따로 보낸다(요청서 3절 머리말). ReportArchive 는 이 박스에 세션이 있어도 커밋하지 않는 저장소다 |
| 4절 | 사용자 결정 먼저 | 보내지 않음. 이 문서 몫과 닿는 것 — SF-6 · SF-10(StepForge) · SG-04(SignalForge) · MW-04 · MW-10 · MW-11(MXWP) · KR-20(KooRemapper) · MEMORY-8(HEAXHub) |

**겹침(87 미병합 가지, 모두 커밋만)** — 에이전트 서버 `wt1124/offload-finish`(offload.py · mcp_server.py · usage_tokens.py — 1-3 OF-1 ~ 5 · 2절 A-1 과 같은 파일) ·
게이트웨이 `wt1124/fig-race` · `wt1124/interactions` · `wt1124/offload-finish` · 에이전트 서버 · 리스크 앱 `wt1124/risk-unit-split` · 포털 여섯 갈래.
1-1 ~ 1-3 · 2절 작업은 이 가지들이 main 에 들어간 뒤의 main 에서 딴다.

## 2. 대조 결과 한눈에(11-25)

| 저장소(HEAD) | 항목 | 남음 | 일부 됨 | 이미 됨 | 질문(답만) | 운영 몫 |
|---|---|---|---|---|---|---|
| StepForge(`a7c65a5e`) | 14 | 8 | 0 | 5 | 1 | 0 |
| DocForge(`4804aca` = 배치판 0.3.2 코드) | 17 | 14 | 3 | 0 | 0 | 0 |
| HEAXHub(`0cf7a45`) | 4 | 4 | 0 | 0 | 0 | 0 |
| MaterialTwin(`448dfa6`) | 1 | 0 | 0 | 0 | 0 | 1 |
| SignalForge(`5f97f24`) | 6 | 5 | 1 | 0 | 0 | 0 |
| MXWhitePaper(`d755a00`) | 3 | 1(선택) | 0 | 0 | 2 | 0 |
| KooRemapper(`7606736`) | 7 | 5 | 1 | 0 | 0 | 1 |
| ste(`ea8de98` 로컬 · `859a02d` origin) | 3-2 의 ste 몫 | 2 | 0 | 코어 7건 코드에 있음 · 미배포 | 1 | — |
| 브리지(KooSolverContainer `3bc5584`) | 3-2 의 브리지 몫 | 2 + 고를 일 2 | 2 | 13건 코드에 있음 · 미배포 | 0 | ST-8 값 |
| SmartTwin MCP(KooSlurm `ea9ebe59`) | 4 | 4 | 0 | 0 | 0 | 0 |

(HP-71 은 세 저장소에 하나씩, IR-24 는 DocForge · HEAXHub 에 하나씩 셌다.)

**요청서 판정을 바로잡는 것** — 운영 쪽에 받은 편지함으로 알린다(부록 A 로 옮길 것).

| ID | 요청서 | 지금 |
|---|---|---|
| SF-4 · SF-7 | 받았으나 안 끝남 | **이미 됨** — StepForge D-708 2차 `560ec255`, 운영 판 r20261123b(`edcddf44`)에 들어 있음. 남은 것은 운영 쪽 장부 쓰기 · 재시험 |
| SRC-06 | 새 요청 | **이미 됨** — `c454b498`(11-09). `STEPFORGE_CORE_LINK=off` 는 자동 실행만 끈다 — 사람이 부르는 set_revision(dry_run) · onto_candidates 에는 까닭이 나온다 |
| ST-19 · BBOX-5 | 질문 · 선택 | **답 있음** — StepForge D-691(`53433cbe`, 11-14). ST-19 는 「안 둔다」, BBOX-5 는 OCCT master 가 이미 고침 → 상류에 알릴 것 없음 |
| ST-28 | 질문 | **길 있음** — `onto_link`(한 호출 500줄 · 미리 보기 기본 · 적용은 사람 신원) |
| IR-14 | 새 요청 | **일부 됨** — EMF · WMF 는 이미 PNG 로 바꿔 판독(`efe3f73`). 남은 것은 TIFF |
| DFO-2 | 새 요청 | **일부 됨** — 과제명 · 과제코드 · 모델명 · 옛 key 로 이미 맞춤. 남은 것은 `matched_by` 싣기 · 별칭(보류 결정 R-D48) |
| DFO-1 | 위치 HEAXHub | 고칠 곳은 DocForge(`ontology/sp_mirror.py` · `sp_core.py`) |
| SE-8 | 위치 포털 · HEAXHub | 포털에서 바꿀 것 없음 — HEAXHub 스크립트 셋 |
| KR-12 | 받았으나 안 끝남 | 문서는 끝(`54304cdd` · `0012f97a`). 남은 코드는 DP-13 답 대기이고 지금 동작 영향 0. 요청서가 짚은 시험 줄은 SP 정의 파일을 보는 시험이라 고칠 대상이 아님 |
| MW-06 | 0056 이관 고치기 | 이미 적용된 DB 는 안 바뀐다 — 새 이관으로 고친다 |

## 3. 세션별 계획

크기 S(반나절 안) · M(하루 안팎) · L(그 위). 차례는 받을 세션에 권하는 순서다.

### 3-1. StepForge(`stepforge-d4`)

| 차례 | ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|---|
| 1 | ST-24 | 남음(P1) | `core/data/part_ontology.yaml` 17칸 가운데 14칸에 코어 부품 값 · 출처 문구. glass · speaker_mic · analysis_aid 는 null 그대로 사유만 | S · `dangling_endpoint 0` 은 운영 허브 거울에서만 확인(받은 편지함) |
| 2 | ST-26 | 남음(P1) | 사람 선과 칸을 한 판정으로 묶는 해석 함수를 도구 다섯(identify_part · identify_parts · describe_part · find_parts · part_index) · 공개 표 · 챗 접기에 | M · ST-24 뒤. next 의 운영 허브 도구 이름 · 인자 꼴은 받은 편지함. basis 어휘(human · role+name · role · name)를 도구 응답에만 둘지 |
| 3 | ST-20 · ST-21 · ST-22 | 남음(P2 · P2 · P3) | 단면 묶음 — 교선 없는 파트를 이름 붙여 따로 · 자동 평면을 면 · 공차에서 띄우기 · 보고용 상자(공차 부풂) | M · M · M~L. 상자 하한 전제(단면 거르기 · auto_position · job_worker)를 깨지 않게 — 금본 D-200 · D-483 |
| 4 | ST-23 | 남음(P2) | 파싱 중 잰 대응 저장 막기 · 저장 전 열쇠 재확인 · `fresh=true` | M · 서명이 바뀌어 공개 표 · 인자 계약 금본 · 게이트웨이 바인딩이 따른다 |
| 5 | ST-25 | 남음(P2) | maps_to 출발에 `cad_part` · 이름 규칙 층 | L · ST-24 뒤. **KooRemapper ST-25-KR 과 같은 판**(공통 블록 sha 가드 D-689). basis enum 이 바뀌는지 StepForge 가 정해 KooRemapper 에 블록째 넘긴다 |
| — | ST-27 | 남음 · **결정 먼저** | pick_role 에서 머리 낱말 먼저 | M · D-490(「붙는 쪽 우선」 되돌림)을 넘는 바탕 판정 — 사용자 결정 뒤. 참값 표 · 반례 20 재채점 |
| — | SF-4 · SF-7 · SRC-06 · ST-19 · BBOX-5 | 이미 됨 | 없음(포털 기록만 닫음) | SF-7 의 닫힘 예/아니오 칸은 의도적으로 없음(문턱 없음) — 원하면 새 결정 |
| — | ST-28 | 질문 | 답 「길 있음」 확인만 | 관리자로 좁힐지는 정할 일 |

### 3-2. DocForge(`docforge-f6`)

운영 판 0.3.2 와 main 의 코드가 같다(차이는 문서 셋) — 「배치 기다림」 항목은 없다. 지금 release · Drive 보류(5차 라운드).

| 차례 | ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|---|
| 1 | IR-12 | 남음(P1) | srcRect 대로 잘라 싣기(EMF 는 PNG 로 바꾼 뒤). **docx · xlsx 는 srcRect 를 세지도 않는다 — 같이 막는다**(가린 내용이 새는 길) | M |
| 2 | IR-13 | 남음(P1) | `spPr/a:blipFill` 그림을 그림 요소로 더 낸다(글 요소는 그대로) | M |
| 3 | IR-11 · IR-15 · IR-16 | 남음(P1 · P2 · P2) | 쪽마다 '그림 파일로 못 읽는 것' 표지 → 고른 쪽만 쪽 그림 판독 · 연결선 'A → B' 글 · 쪽 그림 블록은 고른 쪽만 | L · M · S. 쪽 그림 재료는 포털 IR-02(미배정). DocForge 가 스스로 쪽 그림을 그릴지는 결정 |
| 4 | IR-17 · IR-20 | 남음(P2 · P3) | 판독 지시에 '요약:' 줄 → 캡션 · 축 이름 null 허용 | S · S. PROMPT_VERSION 은 IR-11 과 한 번에 올린다(캐시) |
| 5 | IR-14 · IR-18 · IR-19 | 일부 · 남음 · 남음 | TIFF → PNG · 문서 전체 그림 번호 · 표 그림 둘째 판독을 표 위젯으로 | S · S · M |
| 6 | IR-23 · IR-24(원본) | 남음(P2 · P2) | 판독 · 판단 동시 수를 프로세스를 넘어 세기(잡마다 프로세스) · 매니페스트 `DOCFORGE_MAX_JOBS` 줄 빼기 | M · S. **HEAXHub 등록 사본과 한 묶음 · SIF 다시 짓기 · Drive** — 매니페스트가 빌드 캐시 열쇠에 든다(R25-7) |
| 7 | DFO-1 · DFO-2 · DFO-3 | 남음 · 일부 · 일부 | 거울 수를 받는 타입만(옛 행 stale) · `matched_by` · 패키지 응답에 `links[]` | S · S · S. 별칭까지 맞출지는 결정(R-D48 보류) |
| 8 | IR-21 · IR-22 · IR-51 | 남음(P3) | 판독 머리 줄 · '없음' 줄 빼기 · 픽셀 기준 줄이기(긴 변 2048) · 끝점마다 생각 끄기 손잡이(기본 지금대로) | S · S · S. IR-51 의 에이전트 서버 몫은 미배정 |

### 3-3. HEAXHub(`heaxhub-4b`)

| 차례 | ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|---|
| 1 | HH-18 | 남음(P2) | 런처 세 자리(호스트 · SIF · apt)가 띄울 때마다 `.env` 를 다시 읽어 얹는 도우미 하나 | M · 따옴표 해석 · 지운 키를 뺄지는 세션이 정한다 |
| 2 | IR-24(사본) | 남음(P2) | `integrations/doc-forge/.portal/manifest.yaml` 의 같은 줄 빼기 | S · DocForge 와 한 묶음 · doc_forge SIF 다시 짓기 · Drive(R25-7). cae00 `manifest.local.yaml` 우회도 같은 까닭으로 안 됨 |
| 3 | SE-8 | 남음(P2) | `appdata-merge-from-drive.sh` · `models-from-drive.sh` · `dist-from-drive.sh` 반복 줄이기(요청 1 ~ 5) | M · tar 를 영구 캐시에 두면 'DB 밖 심기를 계속 돌릴지' 결정이 필요 없어진다 |
| 4 | HP-71 | 남음(P3) | `.env.example` 「앱에 넘기는 환경」 절에 코어 주소(포털 경로 꼴) · NO_PROXY 자리표시 | S |

### 3-4. SignalForge(`signalforge-c6`)

| 차례 | ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|---|
| 1 | SFO-1 · SFO-2 | 남음 · 일부(P1) | 프로젝트 key → 과제 → 제품 역색인 · 못 풀면 넓히지 않고 0건 + reason · 물러남 줄 한 번만 · `strict` 인자 | M · S. SG-04 데이터 결정(4절, 사용자)과 따로 먼저 지을 수 있다 |
| 2 | SFO-3 | 남음(P2) | resolve · search_voc 응답에 `core_key` · `matched_by` · `via` | S · SFO-1 뒤 |
| 3 | SFO-5 | 남음(P3) | search_voc 에 core_type · core_key 인자 | S · SFO-1 재사용 |
| 4 | SFO-4 | 남음(P2) | 받는 타입에 plm_model_code | M · 코어 칸 이름을 cae00 에서 먼저(받은 편지함) |
| 5 | HP-71 | 남음(P3) | 예시 .env 의 코어 주소 · NO_PROXY 자리표시 | S |

### 3-5. MXWhitePaper(`mxwhitepaper-26`)

| ID | 판정 | 내용 |
|---|---|---|
| MW-08 | 질문 — 답 초안 「시드다」 | 골든 샘플 restricted 둘(06 · 08)을 seed 가 owner=admin 으로 싣는다. 운영 쪽은 두 장의 slug 가 샘플과 같은지만 맞댄다 → 같으면 D7 ① 은 '보관(또는 지움)' |
| MW-09 | 질문 — 답 초안 「맞다, 약해진다」 | 받기는 서비스 시야가 아니라 사람 시야라, 서비스 계정(admin)이면 범위 검사를 건너뛰고 남의 이름을 적을 수 있다 → 위키를 켜기 전에 사람별 위임(D7 ②). 4절 MW-10 결정의 재료 |
| MW-06 | 남음(선택, P3) | reliability-test 대응 글자 — 새 이관으로 `ext_axes` UPDATE. 코어 받기 코드(L)는 허브 토큰 뒤 |

세션에는 두 답 초안의 확인을 청한다. 결정(D7)은 4절 사용자 몫이다.

### 3-6. KooRemapper(`kooremapper-4a`)

| 차례 | ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|---|
| 1 | R-04 | 남음(P3, 하지만 다음 배포 전) | `dist-from-drive.sh` 의 SIF 설치를 '임시 파일 + mv' 로(떠 있는 squashfs 덮어쓰기) · `stop.sh` 가 인스턴스가 사라질 때까지 기다리고 넘으면 rc≠0 | S~M · 포털은 같은 문제를 `11874eb9` 에서 고쳤다. 포털 `_stop` 의 rc 삼킴은 포털 몫(미배정, 선택) |
| 2 | R-09 | 남음(P3) | 판 입력칸 문구 '과제코드' 가 틀린 key 를 만든다 — 문구를 과제명으로 또는 과제코드로도 풀기 · 등록 레시피 내보내기 자리를 데이터 뿌리 아래로(git stash -u 가 쓸어 감) | S · S · 화면은 빌드 · Drive |
| 3 | ST-25-KR | 남음(P2) | StepForge 가 확정한 maps_to 블록을 통째로 · `EXTERNAL_TYPES` 에 `cad_part` · 시험 두 자리 | S · StepForge ST-25 와 같은 판 |
| 4 | KR-12 | 일부 됨 | `EXTERNAL_TYPES` 의 plm_test_site · 개정 종류 괄호는 칸이 있을 때만 | S · DP-13(Datahub 플랫폼) 답 뒤. model_kind · rc_marker 로 갈음하면 뜻이 틀린다 |
| 5 | KR-10 · KR-19 | 운영 몫 · 남음 | 종료 판정을 실제 원문대로 · 옵션 · 결과 회수(7-1 후처리 예약 잇기 권함) · `*INCLUDE` | S · M~L · **운영 노드 첫 실제 제출과 진단 `last_raw` 전달이 먼저**(받은 편지함) · 받는 쪽 스키마 |
| 6 | HP-71 | 남음(P3) | `platform/.env.example` 코어 주소를 포털 경로 꼴로 · NO_PROXY 자리표시 | S |

## 4. 짝 · 차례 · 올리기

- **같은 판으로** — StepForge ST-25 ↔ KooRemapper ST-25-KR(공통 블록). DocForge IR-24 원본 ↔ HEAXHub 사본(+ SIF 다시 짓기 · Drive). DocForge IR-23 은 IR-24 앞.
- **세션 사이에 청할 것** — 브리지 BG-1(P0) ← StepForge 에 export_part_step 의 REST 길(지금 MCP 에만). 브리지 ST-1 ← StepForge SF-3 출력.
- **포털 쪽(미배정)에 기대는 것** — DocForge IR-11 · IR-16 ← 포털 IR-02. KooRemapper R-04 의 포털 `_stop` rc(선택). DocForge IR-51 · 에이전트 서버 몫.
- **운영 쪽 답 먼저** — SFO-4 · KR-10/KR-19 · ST-24 확인 · ST-26 도구 꼴 · ST-25 conflict 수 · MW-08 slug · HH-10 · ste 자동 교체 · BG-2 진단기 ·
  ST-2 한계 값 · ST-8 h 값 · PA-02 장비 주인 · PA-15 로그. 받은 편지함 [2026-11-25](../cae00-inbox/2026-11-25.md).
- **올리기** — 5차 라운드 동결 중이다. 각 세션의 코드는 가지 · 로컬 커밋까지, push · Drive 는 동결 해제 뒤(87 이 알리면 이 세션이 각 세션에 전한다).
  이 폴더의 문서는 동결 중에도 올린다(87 과 합의 — 문서만 바뀌는 커밋).

## 5. ste · 브리지 · SmartTwin MCP

**요청서보다 훨씬 앞서 있다.** 3-2 의 「지었다는 기록 없음」 상당수는 낡은 기록이다.
- ste — 11-22 에 로컬에만 있던 코어 몫(ST-4 · 5 · 10 · 11 · 12 · 14 · 16)이 지금 origin/main `859a02d` · Drive staging 에 있다. 운영은 `1e53260` 이고
  cae00 의 자동 교체(잡 0 이 되면, 기한 11-26)를 기다린다. 로컬 main 은 origin 보다 17커밋 앞(ST-17 래퍼 `11f90a7` 등) — 동결로 미푸시.
- 브리지 — ST-6(레디쉬 지표까지) · ST-9 · ST-13 · ST-15 · ST-17(0D) · BG-6(브리지 몫) 은 지어 11-23 Drive 꾸러미에 있다(ST-17 `a9655da` · `3bc5584` 은 꾸러미 뒤).
- **BG-2 의 진단 절차는 이미 있고 운영 쪽에도 갔다** — 브리지 `ste_integration/DIAGNOSE.md`(`0134e4f`, 11-18) · Drive `SIF_Images/tools/`, 받은 편지함
  2026-11-22 에 실렸다. 운영 쪽 결과(숫자 JSON)만 아직이다.
- **3-10 을 받을 저장소는 SmartTwinMCP 리포가 아니다** — 그 리포는 도는 코드가 아니고(`97c0e0b`), 정본은 KooSlurm `dashboard/smarttwin_mcp` ·
  `dashboard/backend_5010` 이다(상대 클러스터 stcx). 앞선 요청(PA-16 · PA-19)처럼 `smarttwinmcp-4c` 에 보낸다.

### 5-1. ste(`smarttwinexplorer-06`)

| ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|
| PA-02(처음) | 남음 | 같은 결과 파일을 되풀이해 받는 클라이언트는 ste 자신의 ste-sync 에이전트(Go — 기본 User-Agent)로 보인다. 도는 잡의 64 MB 넘는 파일을 받고, 자라면 크기 어긋남 → 부분 파일 지움 → 0 부터 다시. 끝나지 않은 잡의 큰 파일은 받지 않거나, 같은 파일이 자라면 이어 받기 | M · 사용자 PC 에이전트 재배포. 관리자 에이전트가 남의 잡을 받던 결함(`3c36726`)은 운영 판에 없음 |
| PA-15(처음) | 질문 — 답 초안 | 파일이 줄면 본문이 Content-Length 보다 짧게 끝나 nginx 의 그 문구가 난다 — ste 쪽 후보. 재기동 · 터널 끊김도 같은 문구 | 운영 쪽이 그 시각 ste 백엔드 로그로 가린다. PA-02 와 뿌리가 같을 수 있다 |
| BG-6 | 일부 됨 | part-study params 에 units 칸이 없어 `--units` 를 넘기지 않는다 — param 하나 더하기, 또는 있는 가드 둘로 충분한지 정하기 | S |
| ST-4 · 5 · 10 · 11 · 12 · 14 · 16 | 코드에 있음 · 미배포 | 없음 — 자동 교체 뒤 운영 확인 | — |
| ST-17(ste 래퍼) | 로컬에만 | 동결 해제 뒤 푸시 · 다음 Drive | — |

### 5-2. 브리지(`koosolvercontainer-da`)

| ID | 판정 | 바꿀 것 | 크기 · 기대는 것 |
|---|---|---|---|
| BG-1(P0) | 일부 됨 | 주소 짐작 · 실패 갈래는 끝. 아직 과제 전체를 내보낸다 — 그 파트만 받기 · part_not_found | M · **StepForge 에 export_part_step 의 REST 길이 없다**(MCP 에만) — StepForge 에 함께 청한다. 잡 한정 토큰(7.27) 결정 |
| ST-1 | 코드에 있음 · 다각형 영역 남음 | StepForge cavity_openings 다각형을 개구부로 받는 길 | M · SF-3 출력 뒤 |
| ST-2 | 코드에 있음 | 유량 어긋남 한계 기본 50 %(요청 예시 5 %) — 받아들일지 답만 | 운영 쪽 답 |
| ST-7 | 코드에 있음 | 레디쉬 「빌드만」 길(결로 check_only 처럼) — 해도 되고 안 해도 됨 | S · 고를 일 |
| ST-8 | 일부 됨 | 변별 h 표 값이 모두 null(D-46 — 지어내지 않음) | 값과 출처는 요청 쪽 · 도메인 담당(받은 편지함) |
| ST-17 | 코드에 있음 · Drive 에 없음 | 다음 꾸러미에 | — |
| BG-2 · ST-6 · ST-9 · ST-13 · ST-15 | 코드에 있음 · 미배포 | 없음 — 반입 뒤 운영 재시험 | — |

### 5-3. SmartTwin MCP(`smarttwinmcp-4c`, 코드는 KooSlurm)

| 차례 | ID | 판정 | 바꿀 것 | 크기 |
|---|---|---|---|---|
| 1 | SM-04(P1) | 남음 | SSO 꺼짐 확인이 개인 토큰 확인보다 앞이라 무엇이 와도 admin 으로 풀린다 — 차례를 바꾸고 caller_identity 가 admin 같은 이름을 받지 않게 | S |
| 2 | SM-01(P1) | 남음 | 직접 sbatch 도구 셋(train_pytorch_gpu · submit_distributed_train · submit_lsdyna_remote 1.1.0)에 호출자 · 작업 폴더 확인 — `single_drop_simulation/1.1.2` 의 선례 꼴 | M |
| 3 | SM-02(P2) | 남음 · 전제 일부 틀림 | mode-* 태그는 읽기 · 쓰기가 아니라 시야 구분이다(읽기 도구도 mode-own). meta.yaml 에 읽기 칸을 따로 두고 annotations(fastmcp 는 dict 를 받는다) | S~M |
| 4 | SM-03(P3) | 남음 | `install_offline.sh:92` 의 고정 경로 · 유닛 예시 · wheel 해시 | S |

## 6. 사용자 결정이 필요한 것(이 문서 몫)

| 무엇 | 저장소 | 왜 |
|---|---|---|
| ST-27 — 역할 고르기에서 이름의 머리 낱말 먼저 | StepForge | D-490 이 되돌린 바탕 판정을 바꾼다 |
| ST-28 — 대응표 넣기를 관리자로 좁힐지 | StepForge | 지금은 사람 신원이면 된다 |
| SF-7 — 닫힘 예/아니오 판정 칸 | StepForge | StepForge 는 문턱을 두지 않으려 일부러 뺐다 |
| DFO-2 — 별칭까지 맞출지 | DocForge | 짧은 별칭이 긴 낱말 속에서 잘못 맞는 것을 막으려 보류했다(R-D48) |
| IR-11 — DocForge 가 고른 쪽의 쪽 그림을 스스로 그릴지 | DocForge | 아니면 포털 IR-02 가 snapshot_page 를 넘겨야만 된다 |
