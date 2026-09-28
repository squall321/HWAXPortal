# ste 전각도 낙하 — 체크리스트

## dev (이 세션)

- [x] PLAN·context-notes
- [x] `apps/_lib/fullangle_drop.py` — scenario 생성 · 자식 잡 ID 수집 · 판정 · 라이선스 서버 해석
- [x] `apps/_lib/fullangle-drop.sh` — preflight / run(prepare → submit → 대기 → 판정) · TERM 시 자식 전부 취소
- [x] `apps/fullangle-drop/app.yaml`
- [x] ste 시험 31건 — 앱 로드·렌더·sbatch 머리, 래퍼 진입점·가짜 slurm·실제 프로세스 취소(e2e: 실제 잡 스크립트), 변이 14개 전부 사망
- [x] 실제 KooChainRun 대조 — prepare(scenario 형식)·submit(기록만 하는 sbatch)으로 runner_config·jobs.json·submit.log·잡 머리 확인
- [x] ste 전체 시험 160건 + HWAX 클러스터 표기 가드
- [x] 커밋(ste 3a420db 템플릿 대기 · 9f53c2c 앱) — 푸시는 검토 뒤
- [ ] 적대적 검토

## 사용자 (실박스)

- [ ] ste 배포(`update-all` 이 ste 를 반영하는 경로 그대로)
- [ ] HWAX 에서 `ste_submit_job(app="fullangle-drop", params={"mode":"preflight"}, files=[아무 .k])` → `preflight.json` 확인
- [ ] preflight 가 전부 ✓ 면 작은 모델로 `num_angles=2` 실주행 → `fullangle_verdict.json` 확인
- [ ] `sbatch` 항목이 ✗ 면: ste 에서는 하지 않는다(사용자 결정). 앱을 지우거나 두고 stcx 만 쓴다
