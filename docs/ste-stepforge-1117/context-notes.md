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
