# 보고서에 도구 그림 싣기 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 가지 — 포털 `wt1102/figures` · 에이전트 서버 `wt1102/figures`(올리지 않음).

## 포털

- [x] DocForge 배달의 RA 올리기를 `RaSession` 하나로 떼기(배달 동작은 그대로 — 기존 시험 그대로 통과)(RF-3)
- [x] `POST /agent/figures/to-report` — 게이트웨이 계약(RF-1 · RF-2 · RF-4 ~ RF-8)
- [x] `POST /agent/figures/upload` — 에이전트 서버용 올리기만(RF-1)
- [x] 시험 — 가짜 RA · 자격 · 읽기 전용 거절 · 꼴 · 크기 · sha256 · RA 오류 · 칸을 버린 RA · 동시 호출
- [x] 계약 시험 — 에이전트 서버의 `report_figures.attach` 를 진짜 포털 앱에 물린다(RF-15)
- [ ] 포털 전체 시험

## 에이전트 서버

- [x] `report_figures.py` — 그림 줄 찾기 · 그 사람 PAT 로 올리기 · 자리 표지 · 그림 칸 · 셈(RF-9 ~ RF-12)
- [x] `/보고서`(`run_report_save`) 에 잇기 — 결과 사건 `figures`
- [x] 심의 보고서(새 보고서 · 이어붙이기)에 잇기 — outcome `figures` · 결정문 끝 안내
- [x] 잡 원장이 outcome 의 `figures` 를 `report_figures` 로 접고 `deliberate_result` 가 낸다
- [x] 시험 — 단위 · `/보고서` · 심의(웹 · PAT 없는 잡)
- [ ] 에이전트 서버 전체 시험

## 마무리

- [x] 반대 검토(사본에서) — 신원 · 조용히 사라지는 그림 · 크기 · 꼴 · RA 오류 길, 재현한 것만 고침(RF-17 — F1 · F2 · F4 ~ F7 고침, F3 는 게이트웨이 · RA 몫)
- [x] 결정 기록(RF-1 ~ RF-18) 마감

## 표 칸 그림 — PC 키트 변환기 · 게이트웨이 배포(긴급 11-02 '표칸그림 필요해', RF-19 ~)

> 가지 — 포털 `wt1102/md2docx` · 게이트웨이 `wt1102/kit`(올리지 않음).

- [x] `infra/pc-kit/hwax-md2docx.py` — 홀로 선 줄 · 줄 안 · 표 칸 그림, 캡션, 열 몫 · 높이 상한, A4 · 맑은 고딕(RF-19)
- [x] 그림 주소 — 상대 · POSIX · H:/ · H:\ · UNC · `<…>` · 제목, ref 찾기(md 폴더 · `--fig-dir` → PAT 받기 → figure_get 안내)(RF-20)
- [x] 빠진 그림 종료 2 · docx 없음, `--allow-missing` 자리표, 저장 뒤 수 대조 종료 3(RF-21)
- [x] 포털 시험 `backend/tests/test_pc_kit_md2docx.py` — 열다섯, 변이 열여섯이 모두 빨강(3.10 · 3.13)
- [x] 게이트웨이 `kit_get` · `GET /kit/<이름>` — 표 · PAT · 404 · 감사 · README(RF-22)
- [x] 게이트웨이 검색 어휘 docx · 변환기 · 표 칸 — 띄어 쓴 열쇠(RF-23)
- [x] 끝까지 잇기(사본) — 빈 포트의 진짜 `_bearer_gate` 로 키트 받기 · figure_get 꼴 파일 · PAT 받기 → 변환 `그림 표기 3 · docx 그림 3 · 표 칸 안 2`
- [ ] 반대 검토(사본에서) — 표 칸 배치 · 조용히 사라지는 그림 · Windows 경로 · PAT 새기 · /kit/ 위조 · 경로 넘기(RF-24)
- [ ] 포털 전체 시험 · 게이트웨이 전체 시험

## 하지 않은 것(다음 몫)

- [ ] 반영 — push · 병합 · 재기동(에이전트 서버 · 포털)은 사람 몫이다
- [ ] 업데이트 이력(`docs/changelog.md`) 항목 — 올리는 세션이 쓴다
- [ ] CLAUDE.md 문서 표 한 줄 — 올리는 세션이 더한다
- [ ] `/ai-data-hub/attachments/…` 그림(AIDataHub 첨부)은 아직 싣지 않는다(RF-13)
- [ ] 분석 루틴의 RA 초안 · 챗에 사람이 올린 그림은 이 길을 타지 않는다(RF-13)
- [ ] 포털 잠금 밖의 RA 쓰기가 그림 칸을 지우는 경합 — 게이트웨이가 보고서마다 RA 쓰기를 줄 세우거나 RA 가 expected_revision 을(RF-6 · F3)
- [ ] RA 병합의 곁효과(배치 다시 짓기 · 여러 템플릿 보고서) RA 담당 확인(RF-18)
- [ ] 에이전트 서버 `vision.IMG_URL_RE` 의 `\b`(조사 앞 그림 주소를 놓친다) — 챗 그림 읽기 쪽 세션 몫(RF-13)
- [ ] PC 키트 반영 — 포털 · 게이트웨이 push · 병합 · 게이트웨이 재기동(kit_get 이 생긴다 · 변환기 파일은 포털 리포 받기만으로 새 판), 업데이트 이력 항목
- [ ] 실제 Windows PC 에서 한 번 — UNC · 드라이브 경로 · cp949 콘솔 · 사내 인증서(PAT 받기) · Word 로 열어 표 칸 그림 보기(RF-20)
- [ ] 현장 변환기(md2docx_z.py) 정리 · 개인 Claude 지침에 'docx 는 kit_get 의 변환기로' — 사용자 PC 몫
