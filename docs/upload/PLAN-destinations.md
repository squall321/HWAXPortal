# 챗 업로드 목적지 라우팅 — 계획

2026-09-01. 지금 챗 업로드는 **materialtwin 물성 등록 하나로 고정**돼 있다.
STEP 을 StepForge 로 보내는 것처럼 **목적지를 고를 수 있게** 만든다.

사용자 결정 — **목적지별로 권한 그룹을 다르게**, **STEP 먼저**, **B 방식(업로드 후 되묻기)**.

## 왜 B(되묻기)인가

확장자로 자동 라우팅하지 않는다. 지금 설계가 물성 DB 오염을 막으려고 권한 게이트를 두 층
(프론트 버튼 + 백엔드 API)이나 두고 있는데, 자동 라우팅은 그 방향과 어긋난다. 같은 확장자를
다른 목적지에 넣고 싶은 경우도 막힌다. **목적지는 사람이 고른다.**

되묻기 UI 는 새로 만들지 않는다 — 심의 브리프가 이미 버튼으로 뜨는 방식을 그대로 쓴다.

## 현재 구조 (실측)

```
Composer.tsx  →  POST /upload  →  stage_upload()          →  $HOME/.hwax/upload-staging/<user>/<id>__<name>
                 require_upload_group(upload_allowed_groups)   (컨테이너에선 /var/upload-staging)
                                 →  POST /upload/register  →  mcp_call(gateway, 사용자 PAT, register_material …)
```

- 수신 층은 이미 튼튼하다 — 1MiB 청크 스트리밍(메모리 안전), TTL 청소, 사용자별 디렉터리,
  경로 조작 방어, 2층 권한 게이트, 감사 기록. **이 층은 건드리지 않는다.**
- 고쳐야 할 것은 **목적지가 하나로 하드코딩**돼 있다는 것뿐이다.

## 전송 방식 결정 — 공유 경로 + MCP

StepForge 로 파일을 보내는 길이 둘이다.

| | 방식 | 판정 |
|---|---|---|
| A | StepForge REST `POST /projects/intake` 멀티파트 | **안 쓴다.** 포털이 heax 토큰을 사용자별로 얻어야 한다(jwt-handoff 서버사이드). 두 번째 자격증명 경로가 생긴다 |
| B | MCP `upload_step(project_id, path)` + 공유 경로 | **채택.** 포털의 기존 패턴(사용자 PAT → 게이트웨이 MCP)을 그대로 쓴다. 감사도 사람 단위로 남는다 |

`upload_step` 은 "서버에서 읽을 수 있는 **절대경로**"를 요구한다(mcp_server.py:168).
포털 스테이징 호스트 경로는 `$HOME/.hwax/upload-staging` 이고 apptainer 는 `$HOME` 을 기본
마운트하므로 StepForge 가 같은 경로를 본다.

> **✓ 검증됨(2026-09-01).** 실행 중인 `heax_app_step_forge` 인스턴스 안에서 포털 스테이징
> 호스트 경로를 그대로 읽어 확인했다 — apptainer 가 `$HOME` 을 자동 마운트하므로
> `/home/koopark/.hwax/upload-staging/...` 가 컨테이너에서 같은 절대경로로 보인다.
> `HOME=/home/koopark` 도 동일하다. 따라서 포털은 **컨테이너 경로(/var/upload-staging)가 아니라
> 호스트 경로**를 `upload_step(path=)` 에 넘겨야 한다 — 이 변환이 구현의 필수 항목이다.

## 설계

### 1. 목적지 레지스트리 (`upload.py`)

```python
DESTINATIONS = {
  "material": {label, exts: {csv, xlsx}, groups_setting: "upload_groups_material"},
  "stepforge": {label, exts: {step, stp, msh, zip}, groups_setting: "upload_groups_step"},
}
```

- 목적지마다 **자기 그룹 설정**을 가진다. 비어 있으면 아무도 못 쓴다(안전 기본 — 현행 유지).
- `upload_allowed_groups` 는 `upload_groups_material` 의 별칭으로 남긴다(하위호환).

### 2. `/upload` 응답에 고를 수 있는 목적지를 실어 보낸다

```json
{ "staging_id": "...", "filename": "a.step", "ext": "step",
  "destinations": [ {"id":"stepforge","label":"StepForge — 파트 추출·메시·K파일"} ] }
```

**사용자 그룹 ∩ 확장자**로 계산한다. 하나도 없으면 빈 배열 — 프론트가 "보낼 곳이 없다"를 띄운다.
이게 B(되묻기)의 입력이다.

### 3. `POST /upload/dispatch` — 고른 목적지로 보낸다

`{staging_id, filename, destination, options}` 를 받아 목적지별 핸들러로 분기한다.
목적지 그룹을 **여기서 다시 검사한다**(응답의 destinations 를 믿지 않는다 — 클라이언트가 조작 가능).

STEP 핸들러 — `upload_step` 은 프로젝트가 이미 있어야 하므로 두 단계다.
`create_project` → `upload_step` → (선택) `run_operation`. 프로젝트 이름은 사용자가 준다.

### 4. StepForge 파싱은 잡으로 던진다

407MB SIF 에 파싱 피크 RSS **5.13GB** 실측이다(매니페스트 `memory_gb: 16` 의 근거).
챗 요청 안에서 동기로 돌리면 안 된다. 등록만 하고 잡 id 를 돌려준 뒤 사용자가 진행을 본다.

## 하지 않을 것

- 수신·스테이징 층 수정 — 이미 충분하다
- 확장자 자동 라우팅 — 위 참조
- 프론트 대공사 — 기존 브리프 버튼 패턴 재사용
- materialtwin 경로 동작 변경 — 별칭으로 그대로 둔다

## 열린 질문

1. **StepForge 프로젝트를 매번 새로 만들 것인가, 기존 것에 붙일 것인가.**
   `upload_step` 은 같은 이름 재등록을 **갱신**으로 처리하고, 잡이 도는 중 교체는 막는다.
   기존 과제 목록을 되묻기에 함께 띄우는 편이 나아 보이나 사용자 확인 필요.
2. **그룹 이름** — `upload_groups_step` 에 넣을 실제 사내 그룹명을 모른다.
3. 두 번째 목적지 이후(K파일 → DynaForge, 문서 → AIDataHub)는 이 구조가 서면 반복이다.
