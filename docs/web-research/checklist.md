# 웹 리서치 도입 체크리스트

계획: [plan.md](plan.md) · 결정 기록: [context-notes.md](context-notes.md)

승인이 필요한 항목은 🔒 로 표시했다. **P2~P6 은 키도 승인도 필요 없다.**

## P0 — cae00 망 실측 (사용자 실행 필요)

- [ ] cae00 에서 `infra/scripts/check-egress.sh --json` 실행
- [ ] cae00 에서 `infra/scripts/check-egress.sh --sif <fastapi SIF>` 실행 (컨테이너 CA 상속)
- [ ] 세 분기 중 하나로 확정 — MITM / 폐쇄망 / dev 동일
- [ ] 결과를 context-notes 에 기록

## P1 — 승인 착수 🔒 (병렬, 대기 무관)

- [ ] 보안 검토 요청서 — 나간 문자열 전량 제시 가능함을 근거로
- [ ] deny-list 가 원리적으로 불완전함을 요청서에 **먼저 명시**
- [ ] HEAXHub 공유 인프라 변경(시크릿 bind) 결정 요청

## P2 — 앱 골격 + MCP 등록 (egress 0)

- [x] 소스 배치 결정 — in-tree / 로컬 git / GitHub 중 택일
- [x] upstream 최소 세트 — `pyproject.toml`, `app/__init__.py`, `app/main.py`, `app/mcp_server.py`
- [x] `mcp>=1.10,<2` 상한 (상한 없으면 hermetic SIF 에서 mcp 2.0 이 깔려 크래시)
- [x] `app/config.py` — 쓰기 경로 `HEAX_DATA_DIR` 우선 (SIF rootfs 는 read-only)
- [x] `app/errors.py` — 공통 envelope `{ok, data, errors, warnings, server}`
- [x] 도구 2개 — `search_internal`, `describe_search_status`
- [x] `HEAXHub/integrations/web-research-mcp/.portal/manifest.yaml`
- [x] 매니페스트 함정 검사 통과 (`build.stack`, `launch.health_check`, `max_attempts`, `mcp.description`)
- [x] SIF 빌드 + 기동
- [x] `check-mcp-registration.sh web_research_mcp` 5단계 통과
- [x] `/tools-map` 에 **프리픽스 없는 원래 이름**으로 등장 (충돌하면 자유조회에서 사라진다)
- [x] `_free_tool_ok()` 전 도구 True
- [x] 컨테이너 외부 커넥션 0건 확인 (`ss -tnp`) — pid 98499, 0건

### P2 검증 결과 (2026-08-08)

등록 체인 5단계 통과. 게이트웨이 45초 만에 합류(도구 225→227). 노출명이 프리픽스 없이
`describe_search_status`·`search_internal` 로 나와 자유조회 화이트리스트를 통과한다.
앱 프로세스 외부 커넥션 0건. `SEARCH_MODE=offline` 기본값에서 scholar·web 둘 다 비활성.

**신규 앱은 `redeploy-app.sh` 로 등록되지 않는다.** 그 스크립트는 DB 에 App 행이 이미
있는 앱을 재기동하는 용도라, 신규는 포트 할당에서 외래키 위반으로 실패한다
(`port_allocations_app_id_fkey`). 스캐너를 먼저 돌려야 App 행이 생긴다.

## P3 — 증거 원장 코어 (egress 0, LLM 0)

- [ ] fetch → 추출 → 문장분해 → 원장 → 독립군
- [ ] 도구 3개 — `get_page`, `search_in_page`, `get_quote`
- [ ] `get_page` 기본 `max_sentences=0` (본문 미반환)
- [ ] 골든셋 20 URL — 전재본 5개가 독립군 1개로 접히는가
- [ ] `(doc_id, i)` 왕복 바이트 동일
- [ ] dev 7B 에서 `maximum context length` 미발생

## P4 — 공공 학술 API + egress 래퍼 + **소스 토글 UI**

- [ ] `_egress()` 단일 래퍼 (모든 외부 호출이 여기를 지난다)
- [ ] `verify=False` 코드에 없음 — `git grep` 로 단언
- [ ] 3상태 어댑터 — `ok` / `blocked` / `degraded` / `empty`
- [ ] DDG CAPTCHA 픽스처로 `blocked` 분류 검증 (`empty` 로 나오면 실패)
- [ ] `egress.jsonl` 라인 수 == 독립 관측 네트워크 요청 수
- [ ] 카나리 토큰 전 경로 미유출
- [ ] `search_scholar` 도구
- [ ] **`DelibOptsPanel` 에 공공 학술 토글** — 바인딩에서 제외되는지 확인
- [ ] **챗 컴포저 위 소스 패널** — 같은 CSS 재사용
- [ ] 토글 OFF 시 모델의 도구 목록에 아예 없음을 SSE 로 확인

## P5 — 캐시·레이트리밋·서킷·SEARCH_MODE

- [ ] SQLite 캐시(WAL) — 동일 질의 2회 → egress 1건
- [ ] 토큰버킷 3중 + arXiv 3초/1회·PubMed 3rps 준수
- [ ] 서킷브레이커 — 5회 실패 후 소켓 미개방 (`ss -tn` 실측)
- [ ] `SEARCH_MODE=offline` → 외부 소켓 0건, 캐시 질의는 정상
- [ ] **전역 OFF 시 대화 토글이 비활성으로 보이는가**

## P6 — 심의 통합 + 인용 강제

- [ ] 웹 경로에서 `DELIB_CHAIR_CITE=1`, `DELIB_REBUT_QUOTE=1` 강제(끌 수 없게)
- [ ] `[W:doc_id#i]` ↔ `get_quote` 대조기
- [ ] 심의 10건 — 날조 인용률 0%
- [ ] 근거 0 심의에서 `[가설 단계]` 태깅
- [ ] RA 보고서 부록에 `queries_sent` 전문

## P7 — 일반 웹 🔒 (승인 + 시크릿 경로 + 키)

- [ ] `search_web` 도구
- [ ] deny-list 로더 + redaction 골든셋 (차단 100% / 오탐 ≤10%)
- [ ] 차단 시 `tcpdump` 로 외부 소켓 실제 0건
- [ ] 키 없이 기동 → 크래시 대신 `domain_only` 강등
- [ ] `git grep -iE "brave|api_key"` → 레포·매니페스트·cluster.yaml 에 0건
- [ ] 전역 잠금과 대화 토글의 상호작용 검증

## P8 — 배포 파이프라인

- [ ] `build-all-to-drive.sh` WANT 목록 반영
- [ ] `deploy-all-from-drive.sh` 반영
- [ ] `var/sifs` 스테이징 완전성 검사 (일부러 지워보고 경고 확인)
- [ ] `update-all.sh` 훅 — 앱 죽여 놓고 완주 시 exit 0 + 경고

## P9 — 평가

- [ ] 40문항 벤치 (공개기술 20 + 사내도메인 20)
- [ ] **웹 없는 베이스라인과 나란히 공표**
- [ ] 유의한 개선이 없으면 그 사실을 그대로 쓴다
