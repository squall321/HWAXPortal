# 챗 업로드 목적지 라우팅 — 작업 중 결정과 근거

계획은 `PLAN-destinations.md`, 진행은 `checklist.md`. 여기는 **왜 그렇게 했는지**만 쌓는다.

## D-1. 전송을 REST 멀티파트가 아니라 공유 경로 + MCP 로

StepForge 에 파일을 넣는 길이 둘이었다.

- REST `POST /projects/intake` 멀티파트 — 바이트를 직접 보낸다. 대신 포털이 **사용자별 heax
  토큰**을 얻어야 한다(jwt-handoff 서버사이드). 자격증명 경로가 하나 더 생긴다.
- MCP `intake(path=…)` — 포털이 이미 쓰는 패턴(사용자 PAT → 게이트웨이 MCP)을 그대로 쓴다.
  감사도 사람 단위로 남는다. 파일 본문은 안 나른다 — StepForge 가 경로만 받는다.

**후자를 골랐다.** 두 번째 자격증명 경로를 만들지 않는 게 이 시스템에서 더 중요했다.
StepForge 도 같은 판단을 이미 해뒀다 — "파일 **본문**은 MCP 로 나르지 않는다. 693MB 급을
페이로드에 실을 수 없어서다"(mcp_server.py `intake` 독스트링).

## D-2. 호스트 경로 변환이 필수라는 것 — 실측으로 확인

`intake`/`upload_step` 은 "서버가 읽을 수 있는 **절대경로**"를 요구한다. 포털이 보는
`/var/upload-staging` 은 포털 컨테이너 안에서만 유효하다.

실행 중인 `heax_app_step_forge` 인스턴스에서 직접 읽어 확인했다.

```
호스트에 생성   ~/.hwax/upload-staging/_probe/probe.txt
컨테이너에서    apptainer exec instance://heax_app_step_forge cat <같은 경로>
              → portal-staging-visibility-probe        ✓
              → HOME=/home/koopark                     ✓
```

apptainer 가 `$HOME` 을 자동 마운트해 **양쪽이 같은 절대경로를 본다.** 그래서 포털은
컨테이너 경로가 아니라 호스트 경로를 넘겨야 하고, 그 변환이 `upload.host_path()` 다.
`upload_staging_host_dir` 이 비면 변환하지 않는다 — 로컬·비컨테이너 실행에서 안 깨지게.

> 이 한 줄이 설계의 전제였다. 검증 전에 코딩했으면 런타임에서야 "경로를 못 읽는다"로 터졌다.

## D-3. 수신 게이트를 '어느 목적지든 하나'로 완화

`require_upload_group`(물성 그룹)을 그대로 두면 **CAD 담당자가 STEP 을 올리지도 못한다** —
목적지를 나누기 전 동작이 그랬다. 그래서 수신은 `require_any_upload_group` 으로 바꾸고,
목적지별 판정은 dispatch 가 한다.

어디에도 속하지 않으면 받지 않는다. 쓰지도 못할 파일을 디스크에 쌓을 이유가 없다.

## D-4. dispatch 가 목적지 권한을 다시 판정한다

`/upload` 응답의 `destinations[]` 는 **UI 를 그리기 위한 참고값**이다. 클라이언트가
`destination` 문자열을 바꿔 보낼 수 있으므로 실행 직전에 다시 판정한다.
이 프로젝트가 원래 "프론트 숨김 + 백엔드 재검증" 두 층을 두던 것과 같은 자세다.

## D-5. 계획과 달라진 것 — `run_operation` 이 아니라 `run_job`

계획에는 `create_project` → `upload_step` → `run_operation` 으로 적었다. **`run_operation` 은
없다. `run_job` 이다.** 계획서 이름 그대로 짰으면 런타임에서 터졌다.

한때 `intake`(과제 생성·메타·등록·잡을 한 번에) 로 새 과제 경로를 1회로 줄였으나
되돌렸다 — 이유는 D-8.

## D-8. 소스에 있다고 쓸 수 있는 게 아니다 — **배포된** 도구만 쓴다

첫 실주행 e2e 가 `"unknown tool: intake"` 로 터졌다. `intake` 는 StepForge 소스에 분명히
있었다(`app/mcp_server.py`). 그런데 그날(2026-09-01) 23:16 커밋 c8fab07 로 들어온 것이고,
**배포된 SIF 는 그보다 낡았다.** `set_project_meta`·`get_project_meta` 도 같은 커밋이라
함께 없었다.

> 게이트웨이는 **실행 중인 앱이 가진 도구**만 노출한다. 소스를 읽어 도구 이름을 고르면
> 배포 시차만큼 틀린다. 확인은 게이트웨이 `tools/list` 로 해야 한다(250개 중 대조).

`intake` 자체가 `create_project` → 등록 → `run_job` 묶음일 뿐이라, 그 묶음을 포탈에서 편다.
SIF 가 새로 배포돼도 그대로 동작한다 — 있는 도구만 쓰기 때문이다. 잃는 것은 `owner` 메타
자동 기입인데, 그 `set_project_meta` 도 어차피 배포 전이다. 대신 `create_project` 의
`description` 에 올린 사람을 적고, 감사 로그에는 원래대로 사람 단위로 남는다.

## D-9. zip 은 `import_archive` 로 — e2e 가 아니었으면 못 봤다

목적지 확장자 목록이 `zip` 을 받는데, 기존 과제 분기가 무조건 `upload_step` 을 불렀다.
`upload_step` 은 파일 하나짜리라 zip 은 등록 단계에서 터진다. 확장자로 갈라 보낸다.

`intake` 를 풀어 쓰면서 두 분기(새 과제·기존 과제)의 꼬리가 `등록 → run_job` 으로 같아졌고,
그 덕에 이 구멍이 한 자리에서 드러났다. 원래대로였으면 새 과제 zip 만 우연히 동작했을 것이다.

## D-10. 스테이징 ID 는 파일명 접두가 아니라 **폴더**

접두(`{staging_id}__{원본명}`)를 쓰면 32자 uuid 가 파일명의 일부가 되어 StepForge 의
**영구 파트 경로**에까지 박힌다. e2e 에서 실제로 이렇게 나왔다.

```
/과제/5bdc5a41417644c3a69b98c28a3940b0__d_nested.step/NESTED_ROOT/SUB_A_1/SCREW_A1
```

미관 문제가 아니다 — 이 경로가 곧 `run_job` 범위 지정(`params.scope.match_path`)의 대상이라,
포탈 내부 식별자가 남의 시스템 범위 문법을 오염시킨다. 폴더로 바꾸니 깨끗해졌다.

```
/과제/d_nested.step/NESTED_ROOT/SUB_A_1/SCREW_A1
```

딸린 수정 둘. `staging_id` 가 이제 **경로 한 조각**이라 값 자체를 막는다(`isalnum` — 전에는
glob 패턴의 접두라 그럴 필요가 없었다). 그리고 청소가 상자를 지운다 — 상자 mtime 으로
판정해 쓰는 중인 업로드를 지우지 않고, 형식 전환 전에 남은 평탄 파일도 계속 지운다.

## D-6. 파싱을 동기로 기다리지 않는다

StepForge 매니페스트가 `memory_gb: 16` 인 근거가 "693MB 파싱 피크 RSS 5.13GB 실측"이다.
챗 요청 안에서 기다리면 안 된다. 등록하고 `job_id` 를 돌려준 뒤 사용자가 진행을 본다.
`run: none` 으로 잡 없이 등록만 할 수도 있다.

## D-7. 되묻기에서 고를 게 하나면 묻지 않는다

`UploadRouter` 는 `destinations.length === 1` 이면 바로 그 패널로 간다. 버튼 하나짜리
질문은 확인이 아니라 방해다. 둘 이상일 때만 고르게 한다.

## 알려진 빚

- **프론트 `canUpload` 가 `['portal-admin']` 하드코딩이다.** 목적지별 그룹을 나눈 뒤로 이
  목록은 '어느 목적지든 쓸 수 있는 그룹의 합집합'이어야 한다. 사내 그룹명을 `.env` 로 바꾸면
  여기도 고쳐야 하고, 안 고치면 **권한 있는 사용자에게 버튼이 안 보인다.**
  서버가 그룹을 내려주는 게 옳지만 이번 범위 밖으로 뒀다.
- **`intake` 로 되돌아갈 여지.** StepForge SIF 가 c8fab07 이후로 재배포되면 `intake`·
  `set_project_meta` 가 게이트웨이에 뜬다. 그때 `owner`·`department`·`purpose` 를 채우고
  싶으면 D-8 의 묶음 대신 `intake` 를 쓸 수 있다. **다만 지금 코드도 그대로 동작하므로
  급한 일이 아니다** — 바꾼다면 게이트웨이 `tools/list` 로 존재를 먼저 확인할 것.
- **zip 분기는 코드로만 맞췄고 실제 zip e2e 는 안 했다.** STEP 단일 파일은 실주행으로
  확인했다(파싱 잡 done, 트리 9노드, 파트 4개).
- StepForge 는 zip 안의 **폴더 계층을 평탄화**한다(`ingest.ingest_zip` — 이름이 STEP↔MSH
  짝의 키라서). 폴더 트리로 받은 대형 모델은 경로가 사라져 `match_path` 범위 지정을 못
  쓴다. 동명 충돌은 `overwritten` 으로 보고된다. **StepForge 쪽 판단 사항**이다.
