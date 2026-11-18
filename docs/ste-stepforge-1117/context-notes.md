# 레디쉬 · 결로 연계(StepForge → ste) — 결정과 까닭

> 원문은 같은 폴더의 `reddish-request.md` · `condensation-request.md`(11-17 cae00 디지털워커 시험). 포털 · 게이트웨이 몫은 레디쉬 PT-R1 ~ R4 · 결로 P-1 ~ P-3.

## SS-1 (11-18) 전달과 받을 곳

- 사용자 지시로 원문을 StepForge(`stepforge-d4`) · ste(`smarttwinexplorer-06`) · 브리지(`koosolvercontainer-da` — `KooSolverContainer/ste_integration/bridge`)에 나눠 보냈다.
- ste 06 이 코드와 맞대 몫을 다시 갈랐다. 'STE' 앞으로 온 항목 상당수는 ste 코어가 아니라 앱 래퍼 · 해석기 스크립트라서 koosolvercontainer-da 몫이다. S-1 · S-2 검출 · S-4 · 판정 · 빌더 검사 내용 · ST-R6 · R8 · R10 · S-6 · S-9 · 래퍼 종료 규칙이 여기에 든다.
  ste 코어(06)에 남는 것은 `result/stage.json` 을 읽어 failed_stage · reason_code 싣기 · `ste_job_summary` 틀 · 앱 기본 입력 받기 · 스키마 틀 · `mine` · `get_job_file` 범위다.
- ste main · Drive 는 `1e53260` 에 묶여 있다(hwaxportal-a5 와 정한 것 — cae00 update-all · 해석기 깔기 끝을 기다린다). a5 는 11-18 세션 목록에 없어 풀어도 되는지는 사용자에게 묻는다.

## SS-2 (11-18) 파일을 ste 로 옮기는 길은 게이트웨이(P-1)가 먼저

- 잡 안에 StepForge 자격을 넣지 않는다(ST-R1 보류). ste 잡은 모두 같은 계정으로 돌아, 공용 토큰을 잡 환경에 넣으면 같은 노드의 다른 사람 잡이 읽을 수 있다(06).
- 그래서 게이트웨이가 그 사람 신원으로 StepForge 산출물을 서버끼리 받아 ste 업로드 스테이징에 넣고 `upload_id` 만 돌려준다. part-study 는 파일 모드로 돈다.
  BR-R1(레지스트리 fetch)은 이 결과를 보고 남길지 정한다.
- ste 스테이징 창구(06 확인)
  - 흐름: 그 사람의 위임 PAT 로 `POST /api/uploads` → `{id, ticket, expires_at}` → 서버끼리 `PUT /api/uploads/{id}/{파일이름}`(`Authorization: Bearer <ticket>`, 파일마다 한 번, 디스크로 흘림) → 그 사람이 `submit_job(app, upload_id)`.
  - 규칙
    - 업로드 주인은 제출자와 같아야 한다(아니면 404).
    - 한 번만 쓴다(제출 뒤 409). 티켓은 24시간이고 그 업로드 경로 밖에는 권한이 없다. 안 쓴 업로드는 24시간 뒤 지운다.
    - 파일 이름은 경로 없는 평이름이다. 점으로 시작할 수 없고 예약 이름(slurm.out · status · job.sh 등)도 안 된다. 주 입력은 앱 패턴을 따른다(part-study 는 `*.step`).
  - 크기는 파일 하나당 `STE_MAX_UPLOAD_MB`(기본 10,240 MB)이고, 앞단 nginx 도 10240m 이다. 업로드 하나에 파일을 여럿 넣을 수 있다.
  - sha256 은 ste 가 돌려주지 않는다. 게이트웨이가 흘리며 직접 잰다. 06 에 파일별 sha256 을 상태에 실어 달라고 청했다(급하지 않음).
- 남은 물음: StepForge 산출물을 1 MB 상한 없이 흘려 받을 REST 경로가 있는지(stepforge-d4 답 기다림).

## SS-3 (11-18) 잡 목록 소유자

- ste 는 MCP 출력에서 제출자 메일 · owner_id 를 뺐다(PA-20). 그래서 ST-R9 · PT-R4 는 `owner` 를 싣지 않고 항목마다 `mine` 만 둔다.

## SS-4 (11-18) P-1 을 지으며 본 것

- StepForge `download_artifact` 는 6000자를 넘는 답의 `data_base64` 를 접어 뺀다(chat_fold D-512). 게이트웨이는 조각을 늘 `full=true` 로 받는다. 시험의 가짜 StepForge 도 `full` 이 없으면 접게 해 두었다 — 그 칸을 빠뜨리면 시험이 깨진다.
- ste PUT 은 티켓뿐 아니라 업로드 주인 계정도 받는다(`routes/uploads.py put_file`). 그래서 게이트웨이는 위임 PAT 하나로 열기 · 올리기를 하고 티켓을 쥐지 않는다.
- ste 결함 둘을 06 에 알렸다.
  - 본문 도중 끊기면(`ClientDisconnect`) `.part` 가 남는다.
  - 업로드 상태의 `files` 가 그 `.part` 까지 센다.
  - 게이트웨이가 sha256 이 어긋나 일부러 끊는 바로 그 경우다. 고쳐질 때까지 게이트웨이는 끊긴 업로드를 `upload_id_broken` 으로 답해 쓰지 말라고 한다.
- StepForge `_download_chunk` 는 조각마다 파일 전체를 읽고 sha256 을 다시 잰다. 130 MB 파일이면 조각 130개 × 전체 읽기다. 파트 하나 STEP(57 KB)은 상관없다. StepForge 에 알렸다.
- 게이트웨이 가림(PII)은 base64 글을 거의 건드리지 않는다. 메일 · IP · 계정 꼴은 `@` · `.` 가 있어야 하고, IMEI 꼴은 Luhn 검사를 지나는 숫자 15자리 연속이 있어야 한다. 그래도 걸리면 sha256 대조가 끊는다.

## SS-5 (11-18) 읽기 도구 이름은 심의 좌석 접두를 피한다

- 요청서의 `material_gas_transport` 는 `material_` 로 시작한다. 에이전트 `deliberation.py` `_FREE_ALLOW` 가 여는 접두라, 그 이름이면 리스크 심사 · 심의 좌석의 자유 조회에 새로 열린다(D-18 — 리스크 심사에 새 길을 열지 않는다).
- 그래서 `gas_transport_lookup` 으로 지었다. 신뢰성 시험 쪽도 `reliability_test_conditions` 로 짓고 같은 시험을 걸었다. 좌석에 열지는 사용자 결정으로 따로 정한다.

## SS-6 (11-18) 공용 조건표는 만들지 않는다

- PT-R2 · P-2 의 "개인 토큰이 없으면 공용 프리셋으로 대신 받을지 묻는다" 에 쓸 공용 조건표가 어디에도 정의돼 있지 않다.
- 값을 지어내지 않는다. 토큰이 없으면 등록 안내와 "사람에게 시험 조건을 직접 묻는다" 를 답한다. 표가 생기면(누가 어떤 근거로 정하는지와 함께) 그때 잇는다.
- 조도(lux)는 TestScope 조건 어휘에 없다. 장비 사양에만 있다. 늘 null 과 까닭을 답한다.

## SS-7 (11-18) StepForge · HEAXHub 답

- **StepForge(stepforge-d4) — D-707, 그쪽 사용자 확인.** 전부 하고 두 번에 착지한다. main 은 cae00 이 `dist-20261117-215201Z` 를 받은 뒤에 민다.
  - 1차: SF-R1 `export_part_step`(산출물 kind `part_step` — `to_ste_upload` 는 안 만든다) · SF-R2 `part_outline_2d` · F-1 `cavity_openings`(조사부터) · F-2(포털 P-1 꼴) · F-8 · F-7 · SF-R6.
  - 2차: SF-R3 · R4 · R5 · F-3 · F-4 · F-5 · F-6.
  - P-1 이 기대는 `download_artifact` 조각 칸은 그대로 두고, 바꾸면 먼저 알린다. 조각마다 파일 전체를 다시 읽던 것은 이 판에서 고친다(seek · 파일 sha256 한 번).
  - 1 MB 상한 없는 REST `GET /api/projects/{id}/artifacts/{kind}/{ref}` 도 이미 있다. 게이트웨이는 사람 명의가 보장되는 MCP 조각 길을 쓴다.
- **HEAXHub(heaxhub-4b) — 그쪽 사용자 확인.**
  - 꼴: 서버 줄마다 선택 칸 `build: {commit(7자), started_at(UTC ISO)}`.
  - 값은 떠 있는 인스턴스의 것이다(런처가 SIF 를 띄울 때 SIF 안 커밋을 적는다). built_at 은 싣지 않는다.
  - 모르면 칸째 뺀다. 프록시 앱 · 커밋 없는 SIF · 옛 인스턴스가 그렇다.
  - 게이트웨이 받는 쪽은 `629f32c` 다. 꼴이 맞을 때만 그대로 싣고, 칸이 없으면 줄에도 없다.
