# 결정과 까닭 — 운영 요청 모음(11-24) 다른 세션 몫

## R25-1 받은 것 · 몫 가름(11-25)

- 사용자가 운영 박스가 11-24 기준으로 모은 안 끝난 요청 전부를 [request.md](request.md) 에 넣었다(7,776줄 — 1절 121 · 2절 MCP 효율 · 3절 170 · 4절 56 ·
  부록 A 514). 지시는 「여기서 관리하는 플랫폼 제외하고 나머지를 확인해 고칠 것의 계획을 세우고 각 세션에 보낸다」.
- **'여기서 관리하는 플랫폼'** 을 포털 · 게이트웨이 · 에이전트 서버로 읽고, 따로 세션이 없어 포털 세션들이 고쳐 온 AIDataHub · 리스크 앱(1-6 · 1-8)도
  같이 뺐다. hwaxportal-87 에 물었더니 1-1 ~ 1-3 · 2절 · AIDataHub 몫은 아무도 받지 않았다 — 「미배정」으로 적고 87 이 사용자에게 여쭙기로 했다.
- 3절은 다른 팀 몫이라 운영 쪽이 담당에게 따로 보낸다(요청서 머리말). 이 박스에 세션이 있는 3-2(ste · 브리지) · 3-10(SmartTwin MCP)만 보낸다.
  ReportArchive 는 세션이 있어도 커밋하지 않는 저장소라 보내지 않는다.
- 2절 B-1 · B-2(백엔드 결과 크기 · 설명 길이)는 다른 세션 저장소에도 닿지만, 요청서가 운영 쪽 측정 한 판 뒤에 시작하라고 적어 지금 보내지 않는다.

## R25-2 코드와 맞대 판정한다(11-25)

- 요청서의 「새 요청 · 받았으나 안 끝남」 은 운영 쪽이 문서 · 커밋 낱말로 고른 것이다. 그대로 넘기면 이미 지은 것을 다시 짓게 한다(L21-7 · L21-8 —
  이미 막힌 것을 물었던 일). 그래서 받을 저장소의 지금 HEAD 와 항목마다 맞댔다 — 서브에이전트 다섯이 갈래(StepForge · DocForge · HEAXHub ·
  MaterialTwin · SignalForge · MXWP · KooRemapper · ste · 브리지 · SmartTwin MCP)를 읽기만으로 봤다.
- 바로잡힌 것이 적지 않다 — SF-4 · SF-7 · SRC-06 이미 됨, ST-19 · BBOX-5 · ST-28 답 있음, IR-14 · DFO-2 일부 됨, ste 코어 7건 · 브리지 13건 코드에 있음,
  BG-2 진단 절차 이미 있음. 이것은 받은 편지함으로 운영 쪽에 알려 부록 A 로 옮기게 한다(같은 요청이 다음 모음에 다시 오지 않게).
- 판정은 11-25 의 HEAD 기준이다. 보낼 때 세션에 「받기 전에 그쪽 HEAD 로 한 번 더 본다」 를 적는다 — 세션이 그사이 지었을 수 있다.

## R25-3 받을 세션(11-25)

- 같은 저장소에 세션이 둘인 곳은 포털 문서가 마지막으로 주고받은 쪽에 보낸다 — StepForge `stepforge-d4` · DocForge `docforge-f6` · HEAXHub
  `heaxhub-4b` · SignalForge `signalforge-c6` · MXWP `mxwhitepaper-26` · KooRemapper `kooremapper-4a` · ste `smarttwinexplorer-06` · 브리지
  `koosolvercontainer-da` · SmartTwin MCP `smarttwinmcp-4c`.
- **SmartTwin MCP 의 도는 코드는 SmartTwinMCP 리포가 아니라 KooSlurm `dashboard/smarttwin_mcp` · `dashboard/backend_5010`** 이다(`97c0e0b`). 앞선
  요청(PA-16 · PA-19)을 `smarttwinmcp-4c` 에 보냈던 대로 그 세션에 보내고 코드 자리를 밝힌다. KooSlurm 에 11-24 가지(`feat/images-manifest-mcp`)가
  있다 — 그 세션과 겹치지 않게 하라고 적는다.
- MaterialTwin(HH-10)은 운영 쪽 자연 키가 먼저라 지금 보내지 않는다.

## R25-4 같은 판으로 묶을 것(11-25)

- **StepForge ST-25 ↔ KooRemapper ST-25-KR** — 두 저장소의 maps_to 공통 블록이 바이트로 같아야 한다(sha 가드 D-689 · KooRemapper 시험
  `MAPS_TO_SHA256`). 근거 층(role+name · role · name)을 basis enum 의 새 값으로 싣는다면 블록의 enum · help 도 바뀐다. 그래서 KooRemapper 에는
  'cad_part 한 줄' 이 아니라 'StepForge 가 확정한 블록 그대로' 를 받으라고 보낸다. enum 이 바뀌는지는 StepForge 가 정한다.
- **DocForge IR-24 원본 ↔ HEAXHub 등록 사본** — 매니페스트 둘에서 같은 줄을 뺀다. IR-23(동시 수를 서비스 전체로)이 앞이다(줄만 빼면 기본 1 로 같다).

## R25-5 매니페스트를 고치면 SIF 를 다시 짓는다(11-25)

- HEAXHub 의 SIF 빌드 캐시 열쇠는 효과 매니페스트 전체의 해시다(`integration_sif_builder.py` · `MANIFEST_SPEC.md`). IR-24 로 매니페스트 줄을 빼면
  dev 가 doc_forge SIF 를 다시 지어 Drive 에 함께 올려야 한다 — 아니면 cae00 이 캐시 미스로 보고 다시 지으려다 실패해 그 회차 기동을 건너뛴다.
  cae00 에서 `manifest.local.yaml` 로 우회하는 것도 같은 까닭으로 안 된다. DocForge · HEAXHub 양쪽 글에 적는다.

## R25-6 올리기는 동결 뒤(11-25)

- 5차 라운드 동결이 아직이다(87 — cae00 답 Q29 대기). 동결 중에도 문서만 바뀌는 커밋은 main 에 올려 왔다 → 이 폴더 문서 · 받은 편지함은 올린다.
- 각 세션의 코드는 가지 · 로컬 커밋까지, push · Drive 는 해제 뒤로 적는다. 해제 알림은 87 이 이 세션에 주고, 이 세션이 각 세션에 전한다.
- 같은 main 체크아웃을 87 과 같이 쓴다 — 경로를 짚어서만 add · commit 한다(`git status` 를 잘라 통째로 add 하면 남의 작업이 섞인다 — gotchas).

## R25-7 세션 사이에 청할 것(11-25)

- 브리지 BG-1(P0 — 레지스트리가 과제 전체가 아니라 그 파트만 받기)은 StepForge 에 export_part_step 의 REST 길이 있어야 한다(지금 MCP 에만 있고
  `app/rest.py` 의 export-part-fragment 는 덱 조각이라 다르다). 잡 한정 토큰(브리지 7.27)도 걸린다. StepForge · 브리지 양쪽 글에 서로를 적는다.
- 브리지 ST-1 의 다각형 개구부는 StepForge SF-3 출력 뒤다(11-22 합의 그대로).

## R25-8 사용자에게 물을 것(11-25)

- 세션이 혼자 정하면 안 되는 바탕 판정 · 보안 경계 다섯 — ST-27 · ST-28 · SF-7 판정 칸 · DFO-2 별칭 · IR-11 쪽 그림 스스로 그리기(PLAN 6절).
  보내는 글에는 「결정 대기 — 짓지 않는다」 로 적고, 사용자 답을 받으면 전한다.
- MXWP MW-08 · MW-09 의 답 초안은 4절 D7(MW-10) 결정의 재료다 — 결정은 사용자 몫이라 이 문서에서 정하지 않는다.
