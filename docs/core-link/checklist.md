# core-link — 할 일

> 계획 [PLAN.md](PLAN.md) · 계약 [design.md](design.md) · 결정 [context-notes.md](context-notes.md).
> 코드는 모두 가지에서 짓고, cae00 이 11-08 · 11-09 라운드 update-all 을 끝냈다고 알린 뒤 올린다(CK-7).

## 0. 문서 · 결정

- [x] 요청서 옮김(request.md)
- [x] 조사 넷 — SRC-14 쓰기 판정 · SRC-15 REST 다리와 StepForge R2 · 서비스 신원 재료 · update-all 훅 자리
- [x] 사용자 결정 여섯(CK-2)
- [x] 계약서(design.md) · 결정 기록 CK-1 ~ CK-7
- [ ] 문서 커밋 · 올림

## 1. 넘기기

- [ ] StepForge 세션 — SRC-01 ~ 06 · SRC-07(design §6 서비스 단언) · SRC-15 앱 쪽(발급 · 받기) · Q-3 · Q-4 알림
- [ ] KooRemapper 세션 — SRC-08(다리 셋 · 정확 일치만) · SRC-09 ~ 11
- [ ] SignalForge 세션 — 대응표 둘(design §9)
- [ ] 세 세션에 보류 알림 — main 은 cae00 update-all 뒤
- [ ] StepForge 가 알릴 서비스용 REST 경로 받기 → 게이트웨이 `write_paths` · 운영 허용 목록 예시

## 2. 포털

- [ ] SRC-12 박스 훅 — lib · update-all 인자 · 끝 요약 줄 · `.gitignore` · 폴더 README
- [ ] SRC-12 시험 — 빈 폴더(지금과 같음 + ○) · 실패 훅(종료코드 0 + 요약 줄) · 상한 · 바쁨/모름 건너뛰기 · 이름 틀린 훅 · 무시 규칙
- [ ] SRC-13 서비스 PAT — 모듈(표준 라이브러리만) · `POST/GET /auth/pat/service` · 원장 `issued_by` · 토큰 화면 관리자 칸
- [ ] SRC-13 시험 — 클레임 꼴 · 관리자만 · CSRF · 수명 상하한 · 회수 · exchange 거절
- [ ] SRC-15 `he-team.json` `he-cad-stepforge` can · pitfalls 두 줄 + 운영자 시험
- [ ] 업데이트 이력(changelog) 항목

## 3. 게이트웨이

- [ ] SRC-14 낱말 셋 + 읽기 목록 둘 + 시험
- [ ] SRC-13 `_service_scope` · 박스 파일 · 집행 셋(목록 · 호출 · rest_call) · 감사 · `/health` · 계약 시험(포털 모듈 읽기)
- [ ] SRC-15 `rest_sso.step_forge` · `write_paths` · 단언 발급 · 캐시 · 접힘 검사 · 405 · 403 · provision(`STEPFORGE_SSO_SECRET`) · 가짜 StepForge 시험
- [ ] `.gitignore` 에 `service_tools.local.json`

## 4. 에이전트 서버

- [ ] `rest_call` 쓰기 메서드 → 늘 확인 카드 + 시험
- [ ] StepForge 운영자 챗에서 `rest_call` 묶임 확인

## 5. 올리기(cae00 update-all 뒤)

- [ ] 업데이트 라운드 — 리포별 끝 확인 · 병합(문서가 해시를 인용하면 --no-ff) · 올림 · Drive(StepForge · KooRemapper · SignalForge · 포털 화면)
- [ ] dev 반영 · 맞물림 실호출(게이트웨이 ↔ StepForge 단언)
- [ ] 받은 편지함 — BOX-10 ~ 16 차례 · 서비스 토큰 발급 · `service_tools.local.json` 예시 · `STEPFORGE_SSO_SECRET` · 훅 예시 · Q-3 · Q-4 · tools-map 앞뒤 대조
