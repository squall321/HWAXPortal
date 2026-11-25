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
- [x] SmartTwin MCP `smarttwinmcp-4c` → `smarttwinmcp-c8`(11-25 옮김 — R25-14 · 코드는 KooSlurm) — SM-04 → SM-01 → SM-02 → SM-03

## 답 받기

- [ ] 각 세션의 받음 · 차례 · 착지 판(동결 해제 뒤 push) — 받음 · 차례 답: 아홉 곳 모두(R25-10 · SmartTwin MCP c8 은 R25-17) · 가지 커밋: SignalForge `sfo-1125`(SFO-1 · 2 · 3 · 5 · HP-71) · ste 로컬 main(PA-02 `2397f32` · BG-6 `21a1718`) · HEAXHub 로컬 main(HH-18 `c9f39fd` · HP-71 `0375156` · SE-8 `38baee7`) · DocForge 가지 `req1125`(17건 · 커밋 14 · 0.4.0 배치 대기) · KooRemapper 가지 `corelink-int`(R-04 · HP-71 · R-09 — 해제 뒤 R-04 먼저) · StepForge 갈래 `feat-1125`(ST-20 ~ 24 · 26 · BG-1 · ST-27 틀 — 남은 것 ST-25 · ST-27 표본)
- [x] ST-25 짓기 전 물음 넷 → 편지함 R25-Q13 ~ Q16(R25-13)
- [ ] StepForge ST-25 블록(basis enum 바뀜 여부) → KooRemapper 에 전하기(StepForge 가 바이트 · sha 를 직접 함께 보낸다 — R25-13)
- [x] 5차 동결 해제(사용자 결정 11-25 — R25-16) → 일곱 세션에 전함 · ste-06 · 브리지는 계속 묶음 전함
- [x] 사용자 결정 넷(11-25 모두 권장안 — R25-9) → StepForge · DocForge 에 전하기
- [ ] 운영 쪽 답(편지함 2026-11-25) → 해당 세션에 전하기
- [x] IR-24 등록 사본은 DocForge 배치가 고친다 — 두 세션에 전함(R25-11)
- [x] ste PA-02 — 그쪽 사용자 결정 11-25: 도는 잡의 64 MB 넘는 파일은 잡 끝난 뒤 한 번 받기(R25-10)
- [x] StepForge ST-22 · ST-23 — 그쪽 사용자 결정 11-25(새 칸만 · 14,126)
- [x] ST-27 표본 — 편지함 R25-Q12 에 실음(StepForge `f0e63c5a` — `--counts-only --sample-only`, R25-12) · 답은 StepForge 착지 뒤
- [x] KooRemapper R-04 · R-09 — 그쪽 사용자 결정 11-25(같은 뿌리 다섯도 · 풀고 안 되면 거절 · 데이터 뿌리 아래로)
- [x] KooRemapper 착지 때 — 편지함에 데이터 뿌리 `svc/kooremapper` 쓰기 권한(API 사용자) — 문안 받음(R25-17), 87 에 넘길 묶음에
- [ ] HEAXHub SE-8 착지 때 — dev models-to-drive 한 번(Drive MANIFEST — 그 전에는 모델 건너뛰기가 안 먹는다) · 편지함에 첫 실행 모습(appdata 한 번 병합 · `.pre-merge` 348 → DB 마다 3 · dist 첫 전체 검사)
- [ ] DocForge 0.4.0 착지 때 — 편지함에 운영이 알 것 ① ~ ⑥ · 시험 덱 확인 · DFO-1 은 지우지 않고 stale 만(까닭)
- [ ] ste PA-02 착지 때 — 사용자 PC 에이전트 새로 받기 · 두 번 누르기를 편지함 사람 몫으로
- [ ] ste CalculiX 착지 때(요청서 밖 · 같은 라운드) — 동결 해제 뒤 ste push + KooCalculiX 꾸러미(SIF) Drive SmartTwinSolutions · 편지함에 「`/data/SmartTwinSolutions/KooCalculiX` 에 푼다」
- [ ] 브리지 다음 꾸러미(ST-17 · `3bc5584` · ST-7 · BG-1 — 브리지 SIF `koo_stebridge-e52a03a.sif`(6c2e83f 아님 — R25-16 바로잡기) · ste 쪽 `47b108f` · `fa1af4b` · `58508e9`) — **ste 교체 보고 뒤** 그쪽 사용자 확인으로 Drive, BG-1 은 StepForge 착지와 함께여야 운영에서 쓰인다
- [ ] KooRemapper stop rc 를 포털 `_stop` 이 삼키던 것 — 포털 몫 — 87 가지 `wt1126/koorm-stop-rc`(`566f72f6` · 포털 여섯 가지 병합 뒤 · 착지 해시는 87 이 6차 묶음에, leftovers-1121 L21-30)
- [ ] 레지스트리 part 의미 바꾸기(06 가지 `b4503ec` — 선언 + 튜플, 기록용 → 그 파트만 받기) — **새 브리지 SIF(`e52a03a`)와 StepForge `feat-1125` 가 운영에 든 뒤에만**(먼저 바꾸면 지금 요청이 실패, R25-10 브리지)

## 6차 라운드로(R25-15)

- [x] 5차 cae00 update-all 결과(Q29 — 끝 코드 0 · ✗ 0) → 사용자 결정으로 해제(R25-16) → 87 에 전함
- [x] 일곱 세션에 push · Drive 알리기(SIF 올리기가 막히면 사람 몫) — ste-06 · 브리지는 ste 교체 보고까지 묶음
- [ ] cae00 ste 교체 보고(Q35 뒤 — 기한 11-26) → ste-06 · 브리지 풀기(ste 로컬 34커밋 · 브리지 SIF `e52a03a`)
- [ ] cae00 이 `STE_LSTC_LICENSE_SERVER` 를 넣었다는 답 → ste-06 에 전하기(라이선스 기본값 빼는 가지 `0313ceb` 를 그때 올린다)
- [x] 게이트웨이 `wt1124/ste-upload-sha` — 87 의 셋(`4b3cdc1`) 뒤 사본 시험(1,247 통과 · 3 건너뜀) → `--no-ff` 병합 · push `63eed05`(옛 ste 와도 맞물림 — sha 칸 없으면 대조 생략) · dev 재기동은 87
- [ ] request-1125 착지 판 모음(push 뒤 해시 · Drive 이름 · SIF 파일 sha256 / 캐시 열쇠 이름 붙여) + 사람 몫 → 87(6차 편지함) — R25-17 에 모으는 중: 받음 게이트웨이 · MX 백서 · SignalForge · KooRemapper / 기다림 StepForge · DocForge(승인 대기) · HEAXHub · SmartTwin MCP
- [ ] 6차 편지함 나가면 사용자에게 「서버 업데이트 가능」 알림
