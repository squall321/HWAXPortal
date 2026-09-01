# 챗 업로드 목적지 라우팅 — 체크리스트

계획 `PLAN-destinations.md` 기준. 사용자 결정 — 목적지별 그룹 · STEP 먼저 · B(되묻기) ·
그룹은 일단 `portal-admin` 후 `.env` 로 조정 · 되묻기에 **기존 과제 목록도 함께** 띄운다.

## 백엔드

- [ ] `config.py` — `upload_groups_step` 추가, `upload_allowed_groups` 를 material 별칭으로 유지
      → 검증: 기존 물성 업로드 경로가 그대로 동작(회귀 없음)
- [ ] `config.py` — `upload_staging_host_dir` 추가(컨테이너 경로 → 호스트 경로 변환용)
      → 검증: 미설정 시 컨테이너 경로 그대로 반환(로컬 개발에서 안 깨짐)
- [ ] `upload.py` — `DESTINATIONS` 레지스트리(id·label·exts·groups_setting)
      → 검증: 확장자·그룹 조합별 단위 시험
- [ ] `upload.py` — `allowed_destinations(settings, groups, ext)` · `require_destination_group()`
      → 검증: 그룹 없는 사용자에게 빈 배열, dispatch 는 403
- [ ] `upload.py` — `host_path(settings, container_path)` 변환
      → 검증: 탐침으로 확인한 실제 경로와 일치
- [ ] `routes.py` — `POST /upload` 응답에 `destinations[]` 추가
      → 검증: STEP 올리면 stepforge 만, CSV 면 material 만
- [ ] `routes.py` — `GET /upload/destinations/stepforge/projects` (되묻기용 기존 과제 목록)
      → 검증: MCP `list_projects` 결과가 그대로 온다
- [ ] `routes.py` — `POST /upload/dispatch` — 목적지 그룹 재검사 → 핸들러 분기
      → 검증: 클라이언트가 목적지를 조작해도 403
- [ ] STEP 핸들러 — 새 과제(`create_project`) 또는 기존 과제 선택 → `upload_step(호스트경로)` → 잡 반환
      → 검증: 실제 STEP 으로 end-to-end 1회

## 프론트

- [ ] `Composer.tsx` — 업로드 응답의 `destinations` 로 버튼 렌더(심의 브리프 패턴 재사용)
- [ ] stepforge 선택 시 — 새 과제명 입력 / 기존 과제 선택 토글
- [ ] dispatch 후 잡 id·진행 안내

## 배포

- [ ] `start.sh` — `UPLOAD_STAGING_HOST_DIR` 주입
- [ ] `.env.example` — 새 키 문서화

## 마무리

- [ ] `context-notes.md` 에 결정·근거 누적
- [ ] 프론트 빌드 통과
- [ ] 커밋(의미 단위로 분리 — 백엔드/프론트/배포)
