# cae00 인계 — DocForge 상세 개발 (2026-10-24)

> 읽는 사람 — cae00 에서 DocForge 를 이어 개발할 세션(사람 · 에이전트). 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) ·
> 조사 근거 [research.md](research.md). 앱 리포 **`squall321/DocForge`**(GitHub 비공개, 2026-10-24 커밋 `9f0d2e9` — `main` · `release` 같은 커밋).
> 이 문서는 '무엇을 어떤 순서로' 다. '어떻게' 는 DocForge 리포의 `CLAUDE.md` 와 `docs/` 가 정본이다.
>
> **언제 쓰나** — 사용자 결정(10-24, DF-D14)으로 **dev 에서 먼저 개발한다**(시작점 DocForge `docs/START.md` D0~D11). 이 문서는 **실데이터가 필요해진 시점**
> (실문서로 정할 것 · stcx Qwen 진짜 호출 · 실제 RA · SP 허브 · DRM)부터 cae00 에서 쓴다. 권장 — 첫 배치 묶음 직후 작은 M0(실문서 5건 · VLM 탐침)를 일찍.

## 0. 정해진 것 · 받은 것

- **사용자 결정(10-24)** — VLM 은 **stcx Qwen** · 변환기는 **새 HEAX 앱 DocForge** · **dev 에서 먼저 개발하고 실데이터가 필요해지면 cae00**(처음엔 '상세 개발은
  cae00' 이었다 — DF-D14 로 고침) · 새 앱을 배치해 넣는 것까지 이 계획으로.
- **DocForge 의 지금**(`9f0d2e9`) — 걸어 다니는 뼈대가 돈다.
  - 앱 — /health · REST · MCP 도구 다섯(`docforge_*`) · 잡(원장 · 실행기 · 워커 프로세스) · 신원
  - 계약 — IR · RA 위젯 · 패키지 · 변환 보고서
  - 동작 — 뼈대 패키지(원본 이름 · 안내 · 원본 첨부) · 글 회계 · 서식 → 허용 태그
  - 자리와 명세만 — 해부(Docling · 형식별) · 그리기 · VLM · 12칸 격자 · 표 · 차트 · LLM 판단 · 온톨로지(모듈 머리 docstring + 명세 시험)
  - 시험 16 통과 + 명세 시험 8(xfail strict)
- **아직 사람 몫**
  - 금 표본 40 + DRM 5(PLAN §12-4)
  - SP 허브 주소 · `core:read` 토큰(StepForge 와 같은 미결)
  - 첫 배치의 dev 쪽(§2)
  - PLAN §12 의 남은 결정(2 · 4~11)

## 1. 첫날 — 순서대로

1. **받기** — `cd ~/Projects && git clone https://github.com/squall321/DocForge.git`. cae00 에서 GitHub push 가 되는지 이때 본다 — 안 되면 사람에게 알린다
   (자격을 새로 만들지 않는다).
2. **읽기** — `DocForge/CLAUDE.md` → 이 문서 → [PLAN.md](PLAN.md)(§3 원칙 · §11 단계) → `DocForge/docs/CAE00-DEV.md` → `docs/DEPLOY.md` → `docs/M0.md`.
3. **환경 판정** — `bash scripts/check-cae00-env.sh`(사내 CA 가 있으면 `CA=<경로>` 로 한 번 더) → **길 A**(cae00 venv) 또는 **길 B**(dev 가 지은 앱 SIF 를
   개발 환경으로). 결과는 DocForge `docs/context-notes.md` 에 날짜와 함께 적는다.
4. **시험** — 길 A 면 `.venv` 를 만들어 `python -m pytest -q`(16 통과 · 8 xfail 이 나와야 한다). 길 B 면 첫 배치(§2) 뒤 `bash scripts/dev-in-sif.sh python -m pytest -q`.
5. **뼈대 실주행** — 첫 배치가 끝났으면 `docs/DEPLOY.md` §5(REST 로 파일 하나 → done → package.zip).
6. **M0** — `docs/M0.md` 순서대로. 금 표본이 오기 전에는 §1 · §4(구조화 출력) · §5(VLM — 합성 그림 몇 장으로) · §7(RA 위젯 사본 · TODO(M0) 채우기)부터 한다.

## 2. 첫 배치 — dev 쪽 몫(cae00 세션은 못 한다)

**cae00 은 이 앱의 SIF 를 지을 수 없다**(apt · torch). 첫 SIF 는 dev 가 짓는다 — 사람이나 dev 세션이 `DocForge/docs/DEPLOY.md` §4 의 1~6 을 한다.
요약하면 순서는 이렇다.
- HEAXHub 에 등록 사본을 커밋한다(`integrations/doc-forge/.portal/manifest.yaml`).
- SIF 를 짓는다 — 빌드 훅이 LibreOffice · 한글 글꼴 · torch CPU · Docling · Pydantic AI 를 다 깐다.
- 모델 무게를 받아 Drive 로 올린다.
- SIF 를 Drive 로 올린다.

그다음 cae00 쪽은 사람이 §4 의 7~9 를 한다. 박스 값 · `models-from-drive`(처음에는 `HEAX_MODEL_APPS="doc_forge"`) · update-all · /health 확인이다.
cae00 세션은 그 결과를 기다리는 동안 길 A(가능하면)나 dev SIF 없이 되는 일(계약 · 명세 시험 · RA 위젯 TODO)을 한다.

배치 때마다 같은 손이 든다(`DEPLOY.md` §7). cae00 세션이 `main` 에 올리면 dev 가 `release` 를 빠른 감기로 옮기고 다시 지어 Drive 로 보낸다.
그 뒤 cae00 이 update-all 로 받는다. `release` 는 cae00 세션이 옮기지 않는다 — 옮기면 cae00 이 받을 SIF 의 캐시 열쇠가 어긋나 앱이 안 뜬다.

## 3. 단계 · 완료 기준

[PLAN.md](PLAN.md) §11 이 정본이다. 요약은 아래와 같다.

| 단계 | 어디서 | 끝났다는 것 |
|---|---|---|
| M0 실측 | cae00 | 도구 선택(Docling 대 native · 구조화 출력 방식 · VLM 켬/동시 수)을 수치로 정하고 `docs/m0-results.md` · 결정 기록 · 기준선 수치 |
| M1 PPTX | cae00(개발) + dev(빌드) + 포털(배달) | 금 PPTX 지표 ≥ 기준선 · 무음 누락 0 · 명세 시험 xfail 표시 다 뗌 · dev · cae00 실주행 |
| M2 Word · Excel(+ PDF) | 같음 | 금 표본 지표 |
| M3 그림 읽기 | 같음 | 판독 지표 · 표시 없는 모델 글 0 · 챗 첫 조각 지연이 늘지 않음 |
| M4 온톨로지 · DRM · MCP | 같음 + SP 허브(사람) | 온톨로지 지표 · DRM 표본 |
| M5 운영 | cae00 | 상태판 · 절차서 · RA 에서 고친 것을 평가 표본으로 |

## 4. 포털 쪽 몫 — 배달(M1)

DocForge 는 RA 에 넣지 않는다(DF-D2). 넣는 것은 포털이다 — **HWAXPortal 리포의 일**이라 포털 세션이 dev 에서 하거나, cae00 에서 하려면 **따로 clone 한
사본**에서 하고 push 한다(§5). 명세는 아래와 같다.

1. **목적지** — `backend/app/agent/upload.py` 의 DESTINATIONS 에 `reportarchive_precise` 를 더한다.
   - 이름 「Report Archive — 정밀 변환(배치 유지 · 그림 판독)」
   - 확장자 — M1 은 pptx, M2 에 docx · xlsx · pdf
   - 권한 — RA 권한 + DocForge 가 보이는 사람
   - 지금 'Report Archive 로 보내기'(RA 가져오기 + ai-draft)는 비교 기준선이라 남긴다.
2. **맡기기** — 받아 둔 파일의 **호스트 경로**를 사용자 PAT 로 게이트웨이 MCP `docforge_convert(path, parser)` 에 넘긴다(StepForge 보내기와 같은 꼴 — 파일
   본문은 MCP 로 나르지 않는다). `job_id` 를 받아 stage 'dispatched'.
   - DocForge 쪽 `DOCFORGE_INPUT_ROOTS` 에 포털 업로드 스테이징의 호스트 경로가 있어야 한다.
   - DocForge 가 `status: beta` 라야 게이트웨이에 실린다.
3. **진행** — 화면 패널이 포털 라우트를 거쳐 `docforge_status` 를 1.5초마다 본다(PC 도우미 폴링과 같은 박자).
4. **받기** — 끝나면 `docforge_package(job_id)` 의 `package_rel` 을 `<포털 리포 루트>/../HEAXHub/var/app_data/doc_forge/<package_rel>` 로 읽는다(형제 리포 ·
   apptainer 가 $HOME 을 붙여 같은 절대경로로 보인다 — StepForge 보내기 실측).
   - `realpath` 가 그 데이터 루트 밑인지 보고, 잡을 맡긴 사람과 지금 사람이 같은지 본다.
5. **넣기** — 지금 RA 가지와 같은 사용자 명의(`ra_sso` 위임 또는 등록 토큰)를 쓴다.
   - `resources/` 를 하나씩 `POST /api/files` 로 올린다.
   - `report.json` 의 `res://<이름>` 을 받은 file_id 로 바꾼다.
   - `template_id` · `template_version` 을 pages[0] 에서 위로 올려 **엄격 생성** `POST /api/reports` 로 넣는다(배치를 지키는 유일한 길 — DF-D3).
   - 25MB 를 넘는 리소스(RA 기본 상한)는 올리지 말고 보고서에 적는다.
6. **알리기** — 대화에 알림 한 건을 남긴다(업로드 근거 `kind: upload` — docs/chat-ppt PP-D3). 담는 것은 셋이다.
   - 보고서 링크
   - 변환 보고서 요약 — 쪽 · 블록 · 버린 것 수 · 모델 판독 수 · 무음 누락 0
   - '모델 판독' 블록이 있으면 확인하라는 문구
7. **시험** — 가짜 RA(test_ra_sso 꼴) + 가짜 DocForge MCP 로 1~6 을 끝에서 끝까지 본다. 화면은 브라우저 시험(test_chat_ppt_in_browser 꼴)으로 본다.
   업데이트 이력에도 적는다.

## 5. 다른 리포를 고쳐야 할 때(cae00)

- **HWAXPortal · HEAXHub** — `~/Projects/<Repo>` 는 **운영 체크아웃**이다(update-all 이 pull · 재기동한다). 거기에 커밋하지 않은 변경을 남기면 배치가 깨진다.
  `git clone … ~/work/<Repo>-dev` 처럼 따로 받아 커밋 · push 하고, 운영에는 update-all 로 받는다.
- **Report Archive** — 고치지 않는다(이 리포의 규칙 · federation 자동화 제외 대상). RA 쪽이 필요하면 요청서를 쓴다.
  - 엄격 생성 MCP 도구 또는 패키지 가져오기(PLAN §12-2)
  - `__import_blank__` 보장
  - 큰 첨부 상한
  - SP key ↔ 엔티티 합의(§12-10)
- **StepForge** — SP 수신 키트(`core/sp_core.py`)를 **옮겨 쓰는 것**만 한다(출처 머리 주석). StepForge 를 고치지 않는다.

## 6. 하지 말 것

- `release` 를 cae00 에서 옮기지 않는다. HEAX 허브를 손으로 재기동하지 않는다(update-all · `redeploy-app.sh doc-forge` 만).
- dev 박스에서 `deploy-all-from-drive.sh` 를 돌리지 않는다(dev 리포가 리셋된다). cae00 에서도 update-all 밖에서 돌리지 않는다.
- 운영 `var/app_data/doc_forge` 를 개발 데이터로 쓰지 않는다(`dev-in-sif.sh` 가 막는다). 다른 앱의 app_data 를 건드리지 않는다.
- stcx Qwen 에 동시 2 를 넘겨 보내지 않는다(챗 모델이다). 심의 · 카드 대조가 붐빌 때 무거운 실측을 돌리지 않는다.
- 금 표본 · 판독 결과 · 사내 문서 글을 리포 · 커밋 · 로그 · 이슈에 넣지 않는다. 비밀 · 내부 주소도(리포는 GitHub 에 있다).
- `pkill -f` 를 쓰지 않는다(pid 로). `git status` 를 잘라 보고 커밋하지 않는다(남의 변경을 섞는다).
- 도구가 있는지는 소스가 아니라 **게이트웨이 tools/list** 로 본다(SIF 가 낡으면 소스에 있어도 없다 — docs/upload D-8).

## 7. 보고 · 기록

- DocForge 리포 — `docs/checklist.md`(체크) · `docs/context-notes.md`(R-D 결정과 까닭) · `docs/m0-results.md`(수치). 의미 단위로 커밋 · push.
- 포털 — 큰 결정(PLAN §12 를 뒤집거나 정하는 것)은 이 폴더의 `context-notes.md` 에 DF-D 번호로 덧붙인다. 포털 사본(§5)에서 커밋 · push 한다.
- 사람에게는 단계가 끝날 때마다 무엇을 쟀고 무엇을 정했으며 사람 몫이 무엇인지를 짧게 알린다.

## 부록 A — HEAX 허브 규약(조사 2026-10-24, 자세히는 DocForge `docs/DEPLOY.md` §2)

| 것 | 규칙 |
|---|---|
| 등록 | HEAXHub 리포의 `integrations/doc-forge/.portal/manifest.yaml`(스캐너는 그 사본만) |
| 이름 | SIF `var/sifs/doc-forge.sif`(slug) · 데이터 `var/app_data/doc_forge`(id) |
| 빌드 | 스캔은 기동 때와 300초마다 · 웹훅 없음 · 캐시 열쇠 = 커밋 + 매니페스트 + 틀 · **cae00 은 못 짓는다** |
| 기동 | 20회 × 1초 안에 /health < 500 · `--cleanenv` · `/data` 바인드 · `ROOT_PATH=/apps/doc_forge`(Caddy 가 벗김) |
| 환경 | `launch.env` + 강제 PORT · HOST · HEAX_DATA_DIR · ROOT_PATH + `HEAXHub/.env` 의 `APPTAINERENV_X=` |
| 재배치 | 스캔은 건강한 인스턴스를 재기동하지 않는다 → `redeploy-app.sh doc-forge [--rebuild]` |
| MCP | status beta · stable 만 · 게이트웨이 60초 폴링 · 내부 `/mcp` 정확히(리다이렉트 금지) · 기본 서비스 계정 명의 |
| 모델 | SIF 밖 `/data/models` · `models-to-drive` / `models-from-drive`(처음엔 `HEAX_MODEL_APPS="doc_forge"`) |

## 부록 B — Drive 의 HEAXHub 지문 목록 합치기(앱 SIF 몇 개만 올릴 때)

cae00 의 `dist-from-drive.sh` 는 받은 뒤 `sha256sum -c SHA256SUMS` 로 대조하고 틀리면 멈춘다. `dist-to-drive.sh` 는 부분 실행에서도 `latest/SHA256SUMS` 를
**이번에 올린 파일만**으로 덮어쓴다. 이미 실린 줄을 지키려면 다음 순서로 한다(2026-10-24 실제로 함).
1. `rclone copyto <원격>/latest/SHA256SUMS <임시>` 로 받는다.
2. 남길 줄의 파일을 받아 `sha256sum -c` 로 맞는지 확인한다.
3. 남길 줄 + 새 SIF · `.sif.hash` 줄로 새 목록을 만든다.
4. SIF · `.hash` 를 `rclone copyto` 로 올린다.
5. 새 목록을 **맨 마지막에** 올린다.
6. `rclone md5sum` 으로 원격과 로컬을 맞대 본다.

올리는 사이에 cae00 이 받으면 대조에서 멈춘다. 잘못된 판이 깔리지는 않는다.
