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

## D-5. 계획과 달라진 것 — `intake` 를 쓴다

계획에는 `create_project` → `upload_step` → `run_operation` 3회로 적었다. 도구 목록을 실제로
확인하니 두 가지가 달랐다.

- StepForge 에 **`intake` 가 이미 있다** — 과제 생성·메타·등록·잡을 한 번에 한다.
  새 과제 경로는 3회 → **1회**로 줄었다.
- **`run_operation` 은 없다. `run_job` 이다.** 계획서 이름 그대로 짰으면 런타임에서 터졌다.

기존 과제에 붙일 때만 `upload_step` + `run_job` 로 간다 — `intake` 는 과제를 새로 만들기 때문.

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
- **실제 STEP end-to-end 미검증.** 단위·타입·빌드까지만 했다. 포털 재기동 후 한 번 돌려야 한다.
- `.env.example` 에 새 키 2개(`UPLOAD_GROUPS_STEP`·`UPLOAD_STAGING_HOST_DIR`) 미문서화.
