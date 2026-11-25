# 체크리스트 — 운영 요청 모음(11-24) 다른 세션 몫

> 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md).

## 확인 · 계획(11-25)

- [x] 몫 가름 — 포털 · 게이트웨이 · 에이전트 서버 · AIDataHub · 리스크 앱은 뺌(미배정, 87 확인 — R25-1)
- [x] 코드 대조 다섯 갈래(읽기만) — StepForge · DocForge · HEAXHub/MaterialTwin/SignalForge/MXWP · KooRemapper · ste/브리지/SmartTwin MCP
- [x] PLAN · context-notes · checklist
- [x] 받은 편지함 2026-11-25 — 요청서 판정 바로잡기 · 운영 쪽 답이 필요한 것(BG-2 진단 절차는 11-22 편지함에 이미 실림)
- [x] 이 폴더 · 편지함 커밋 · 올리기(경로를 짚어서만 — R25-6) — `e4611b7c`

## 세션에 보내기(11-25 — 아홉 곳 모두 전달됨)

- [x] StepForge `stepforge-d4` — ST-24 → ST-26 → ST-20 · 21 · 22 → ST-23 → ST-25(KooRemapper 와 같은 판) · ST-27 결정 대기 · 이미 됨 다섯 닫기 · BG-1 의 export_part_step REST 길
- [x] DocForge `docforge-f6` — IR-12(+ docx · xlsx) → IR-13 → IR-11 · 15 · 16 → IR-17 · 20 → IR-14 · 18 · 19 → IR-23 · IR-24 → DFO → P3 · IR-51
- [x] HEAXHub `heaxhub-4b` — HH-18 · IR-24 사본(SIF 다시 짓기 · Drive — R25-5) · SE-8 · HP-71
- [x] SignalForge `signalforge-c6` — SFO-1 · 2 → SFO-3 → SFO-5 · SFO-4(cae00 칸 이름 뒤) · HP-71
- [x] MXWhitePaper `mxwhitepaper-26` — MW-08 · MW-09 답 초안 확인 · MW-06(선택)
- [x] KooRemapper `kooremapper-4a` — R-04 → R-09 → ST-25-KR → KR-12(DP-13 뒤) · KR-10 · KR-19(운영 첫 제출 뒤) · HP-71
- [x] ste `smarttwinexplorer-06` — PA-02 · PA-15 답 · BG-6 units · 동결 뒤 17커밋 푸시
- [x] 브리지 `koosolvercontainer-da` — BG-1(P0, StepForge REST 길) · ST-1(SF-3 뒤) · ST-7 고를 일 · ST-17 다음 꾸러미
- [x] SmartTwin MCP `smarttwinmcp-4c`(코드는 KooSlurm) — SM-04 → SM-01 → SM-02 → SM-03

## 답 받기

- [ ] 각 세션의 받음 · 차례 · 착지 판(동결 해제 뒤 push) — 받음 · 차례 답: StepForge · SignalForge · KooRemapper · ste · MXWP · HEAXHub · DocForge(R25-10) / 기다림: 브리지 · SmartTwin MCP · 가지 커밋: SignalForge `sfo-1125`(SFO-1 · 2 · 3 · 5 · HP-71) · ste 로컬 main(PA-02 `2397f32` · BG-6 `21a1718`) · HEAXHub 로컬 main(HH-18 `c9f39fd` · HP-71 `0375156` · SE-8 `38baee7`) · DocForge 가지 `req1125`(17건 · 커밋 14 · 0.4.0 배치 대기) · StepForge 갈래 `feat-1125`(ST-20 ~ 24 · 26 · BG-1 · ST-27 틀 — 남은 것 ST-25 · ST-27 표본)
- [ ] StepForge ST-25 블록(basis enum 바뀜 여부) → KooRemapper 에 전하기
- [ ] 5차 동결 해제(87 알림) → 각 세션에 전하기
- [x] 사용자 결정 넷(11-25 모두 권장안 — R25-9) → StepForge · DocForge 에 전하기
- [ ] 운영 쪽 답(편지함 2026-11-25) → 해당 세션에 전하기
- [x] IR-24 등록 사본은 DocForge 배치가 고친다 — 두 세션에 전함(R25-11)
- [x] ste PA-02 — 그쪽 사용자 결정 11-25: 도는 잡의 64 MB 넘는 파일은 잡 끝난 뒤 한 번 받기(R25-10)
- [x] StepForge ST-22 · ST-23 — 그쪽 사용자 결정 11-25(새 칸만 · 14,126)
- [x] ST-27 표본 — 편지함 R25-Q12 에 실음(StepForge `f0e63c5a` — `--counts-only --sample-only`, R25-12) · 답은 StepForge 착지 뒤
- [ ] KooRemapper R-09 — 그쪽 세션이 사용자에게 묻는 결정 둘(R25-10)
- [ ] HEAXHub SE-8 착지 때 — dev models-to-drive 한 번(Drive MANIFEST — 그 전에는 모델 건너뛰기가 안 먹는다) · 편지함에 첫 실행 모습(appdata 한 번 병합 · `.pre-merge` 348 → DB 마다 3 · dist 첫 전체 검사)
- [ ] DocForge 0.4.0 착지 때 — 편지함에 운영이 알 것 ① ~ ⑥ · 시험 덱 확인 · DFO-1 은 지우지 않고 stale 만(까닭)
- [ ] ste PA-02 착지 때 — 사용자 PC 에이전트 새로 받기 · 두 번 누르기를 편지함 사람 몫으로
