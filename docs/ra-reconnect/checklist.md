# RA 재연결 — 체크리스트 (2026-09-27)

## 포털 코드 (dev)
- [x] `infra/.env.example` — `RA_HOST`(·`RA_PORT`·`RA_MCP_PORT`) · `LLM_BASE_URL`·`LLM_MODEL`·`LLM_API_KEY` 선언(값 없음 — env-sync 가 ○ 로 알린다)
- [x] `services.py` `enabled_here` — `unless_env` · `services.yaml` RA 두 항목에 `unless_env: RA_HOST`
- [x] `gen-nginx-conf.sh` `loc_extras()` 에 `report-archive`
- [x] `systems.yaml` RA 타일 → jwt-handoff 세 줄(옛 external-url 직결 제거)
- [x] `apply-envs.sh` `ra_env_value` — `infra/.env` 우선 · 킷 헤더 문구
- [x] `update-all.sh` **1e** — RA_HOST → routes.local.env·backend/.env·provision.env upsert(멱등) · LLM 1회 이관 · JWKS 후보 출력 · 없으면 ○
- [x] `update-all.sh` §5 — provision 에 `RA_MCP_URL`·`RA_WORKSPACE_SLUG` 전달 · RA 주소 드리프트 → 재프로비저닝 · `reportarchive)` 분기 원격 판정
- [x] 시험 `test_ra_remote_reconnect.py` + 전체 스위트 · 프론트 무관
- [x] 문서 — cae00 가이드에 RA 절 · context-notes · 메모리

- [x] HTTPS 위생 — `startup_warnings` `cookie_scheme` · `gen-nginx-conf.sh` 절대경로 가드 · `ste-doctor` 4c `https` 행 · routes.prod.env 낡은 주석 · 플레이북 routes.local.env (D-6)
- [x] 4-1 회귀 시험(라우트가 있어도 jwt-handoff 콜백 유지) · launch 계약(aud·scope·90초)

## cae00 (사용자)
- [ ] `infra/.env` 에 `RA_HOST=<A 주소>`(요청서 §1) → `git pull && ./infra/scripts/update-all.sh`
- [ ] 요청서 §8 여덟 줄 확인(구 :3000 안 뜸 · 공개 주소 화면 · 2MB 첨부 · 타일 SSO · RA 직접 접속 SSO · 챗 RA 도구가 새 데이터 · apply-envs 재실행에도 LLM 유지 · update-all 이 RA 죽었다고 경고 안 함)
- [ ] RA 담당에게 **JWKS 주소** 전달(1e 출력의 후보 중 하나 — 사내망 http :8088 이 간단) — https 를 고르면 사내 CA 일 때 `/tls/ca.crt` 도
- [ ] 공개 https 를 낼 박스면 `infra/.env` 에 `ENABLE_TLS=true·TLS_CERT_PATH(fullchain, 리포 루트 상대)·PUBLIC_BASE_URL=https://…·COOKIE_SECURE=true` → `ste-doctor` 의 `tls`·`https` 행 둘 다 초록
- [ ] 구 RA 설치본 정리는 3-5(LLM 이관) 확인 **뒤에** — RA 담당과 맞춘다
