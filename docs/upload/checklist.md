# 챗 업로드 목적지 라우팅 — 체크리스트

계획 `PLAN-destinations.md` 기준. 사용자 결정 — 목적지별 그룹 · STEP 먼저 · B(되묻기) ·
그룹은 일단 `portal-admin` 후 `.env` 로 조정 · 되묻기에 **기존 과제 목록도 함께** 띄운다.

## 백엔드

- [x] `config.py` — `upload_groups_step` 추가, `upload_allowed_groups` 를 material 별칭으로 유지
      → 검증: 기존 물성 업로드 경로가 그대로 동작(회귀 없음)
- [x] `config.py` — `upload_staging_host_dir` 추가(컨테이너 경로 → 호스트 경로 변환용)
      → 검증: 미설정 시 컨테이너 경로 그대로 반환(로컬 개발에서 안 깨짐)
- [x] `upload.py` — `DESTINATIONS` 레지스트리(id·label·exts·groups_setting)
      → 검증: 확장자·그룹 조합별 단위 시험
- [x] `upload.py` — `allowed_destinations(settings, groups, ext)` · `require_destination_group()`
      → 검증: 그룹 없는 사용자에게 빈 배열, dispatch 는 403
- [x] `upload.py` — `host_path(settings, container_path)` 변환
      → 검증: 탐침으로 확인한 실제 경로와 일치
- [x] `routes.py` — `POST /upload` 응답에 `destinations[]` 추가
      → 검증: STEP 올리면 stepforge 만, CSV 면 material 만
- [x] `routes.py` — `GET /upload/destinations/stepforge/projects` (되묻기용 기존 과제 목록)
      → 검증: MCP `list_projects` 결과가 그대로 온다
- [x] `routes.py` — `POST /upload/dispatch` — 목적지 그룹 재검사 → 핸들러 분기
      → 검증: 클라이언트가 목적지를 조작해도 403
- [x] STEP 핸들러 — 새 과제면 `create_project`, 그다음 공통으로 등록(`upload_step`, zip 이면
      `import_archive`) + `run_job`
      → 한때 `intake` 한 번으로 줄였으나 되돌렸다. **배포된 SIF 에 `intake` 가 없어**
        첫 e2e 가 "unknown tool" 로 터졌다(D-8). `run_operation` 이 아니라 `run_job` 이다.
      → 검증: 실제 STEP e2e — 과제 생성 → 파싱 잡 `done` → 트리 9노드·5단계 → 파트 4개 형상

## 프론트

- [x] `Composer.tsx` — 업로드 응답의 `destinations` 로 버튼 렌더(심의 브리프 패턴 재사용)
- [x] stepforge 선택 시 — 새 과제명 입력 / 기존 과제 선택 토글
- [x] dispatch 후 잡 id·진행 안내

## 배포

- [x] `start.sh` — `UPLOAD_STAGING_HOST_DIR` 주입
- [x] `.env.example` — 업로드 섹션 신설(그룹 2개·스테이징 경로 2개·TTL). 원래 업로드 설정이
      템플릿에 통째로 없었다.

## 마무리

- [x] `context-notes.md` 에 결정·근거 누적
- [x] 프론트 빌드 통과
- [x] 커밋(의미 단위로 분리 — 백엔드/프론트/배포/실주행 수정 2건)
- [x] **실제 STEP 으로 end-to-end** — 포털 재기동 후 실주행. 목적지 필터(`.step` → stepforge 만)
      → 과제 생성 → 파싱 잡 `done` → 트리 9노드·5단계 → 파트 4개 형상까지 확인.
      돌리며 결함 2건을 잡았다(D-8·D-10). 시험 과제·PAT·스테이징은 회수했다.

## 남은 것

- [ ] **zip 실주행** — `import_archive` 분기는 코드로만 맞췄다. STEP 단일 파일만 실증했다.
- [ ] 프론트 `canUpload` 하드코딩(`['portal-admin']`) — 사내 그룹명을 .env 로 바꾸면
      여기도 고쳐야 버튼이 보인다. 서버가 그룹을 내려주는 쪽이 옳으나 이번 범위 밖.
- [ ] 두 번째 목적지(K파일 → DynaForge)는 이 구조가 서면 반복이다
