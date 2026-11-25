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
  고치는 손은 하나다 — DocForge 배치가 등록 사본까지 고친다(R25-11).

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

## R25-9 사용자 결정 넷(11-25 — 모두 권장안)

- **ST-27** — 「재 보고 나아질 때만 바꾼다」. 참값 표 · 반례 20 · 운영 표본 50 이름으로 먼저 채점하고, 지금 판정보다 나아질 때만 머리 낱말 우선을 켠다.
  D-490 이 되돌린 까닭(근거 0 · 반례에서 엉뚱한 역할 3 → 16)을 되풀이하지 않으려는 차례다. 운영 표본 50 이름은 운영 쪽이 따로 넘긴다.
- **ST-28** — 「지금대로 둔다」. `onto_link` 적용은 사람 신원이면 되고(미리 보기 기본 · `applied_by` 기록 · 서비스 신원 거절), 관리자로 좁히지 않는다.
- **DFO-2** — 「보류 유지」. 별칭 · 모델 label 은 맞추지 않는다(R-D48 그대로). `matched_by` 만 싣는다.
- **IR-11** — 「DocForge 가 스스로 그린다」. 판독이 켜졌고 고른 쪽이 있으면 그 쪽만 DocForge 가 쪽 그림을 그린다. 포털 IR-02(미배정)를 기다리지 않고,
  포털 밖 경로로 들어온 변환에도 먹는다. 포털 IR-02 의 snapshot_page 는 그대로 받는다(둘이 겹치면 같은 쪽을 두 번 그리지 않게 — DocForge 가 정한다).
- SF-7 의 닫힘 예/아니오 칸은 묻지 않고 운영 쪽에 돌렸다(R25-Q2) — 요청한 쪽이 꼭 필요한지부터 답해야 한다.

## R25-10 세션 답(11-25)

- **StepForge** — 판정이 같다. 차례 ST-24 → ST-26 → **BG-1 의 export_part_step REST**(브리지 P0 — 잡 한정 토큰은 브리지와 직접) → ST-20 · 21 · 22 → ST-23 →
  ST-25. basis 어휘는 도구 응답에만 둔다(온톨로지 선 enum 은 ST-25 블록에서 정해 KooRemapper 와 같이). ST-23 의 `fresh` 로 비싼 도구 40 설명 합이 늘면
  그 값은 사용자에게 묻는다(D-709 처럼). D-709(feat-laminate, 회귀 8007 통과)가 먼저 착지하고 이 묶음은 그 위 가지에서 짓는다.
  뒤이어 ST-24 와 BG-1 의 `export_part_step` REST 길을 가지에 지었고(main · 배치 아님 — 브리지에 전함), ST-26 은 시험 중이다(`next` 는 R25-Q3 답 뒤).
  **중간 알림(D-710, 갈래 `feat-1125` 로컬)** — 끝낸 것 ST-24 · ST-26(`next` 만 R25-Q3 뒤) · BG-1 · ST-20 · 21 · 22 · 23 · ST-27 채점 틀, 남은 것 ST-25 · ST-27 표본.
  ST-27 채점 틀 `scripts/role_order_score.py` 가 참값 표(13판 · 이름 1,103)로 판정 셋을 나란히 셌다 — current 맞힘 255 · 엉뚱 71 · 못 붙임 43 /
  head(요청 그대로 — 이름 속 가장 앞 키워드) 204 · 125 · 43(나빠짐 — 나사 이름 속 'Socket' 이 커넥터로, 지은 이름의 브래킷이 디스플레이로) /
  cushion(가장 앞 키워드가 완충 · 접착일 때만) 256 · 70 · 43(하나 나음). 사용자 결정(R25-9 「재 보고 나아질 때만」)대로 판정은 안 바꿨고 운영 표본 뒤 다시 센다.
  표본은 **운영 박스에서 돌려 숫자만 받는 꼴**로 제안했다 — 파트 이름을 dev 로 옮기지 않는다(R25-12).
  ST-22 는 그쪽 사용자 결정(11-25) 「part_location 에 새 칸만」 — 한 파트로 좁힌 줄에 `world_bbox_tight` · `tight_basis`, 옛 칸 · 저장값은 그대로(실측 곡면 정의 89 에서
  지금 상자가 고운 삼각화보다 최대 0.347 mm). ST-23 은 비싼 40 설명 합 14,089 → 14,126(+37)을 그쪽 사용자가 직접 정했다 — 위의 '사용자에게 묻는다' 는 닫혔다.
- **SignalForge** — 판정 같음 · 차례 PLAN 그대로. SP main 이 움직였지만 키트 판은 그대로라 받는 쪽에 닿지 않는다.
  뒤이어 가지 `sfo-1125`(바탕 `5f97f24`)에 지었다 — SFO-1 · 2 `abf2e38` · 노트 `fd01daa` · SFO-3 `e78b853` · SFO-5 `842c188` · HP-71 `157a2e6`.
  시험은 크롤러 2,040 통과(실패 4 는 main 에서도 나거나 작업 폴더 이름 탓) · MCP 212 통과. SFO-4 는 R25-Q4 답 뒤, 국내 · 해외 향 나누기는 SG-04 데이터 결정 뒤.
  **짚은 함정** — `.env` 를 bash 로 source 하는 박스에서 따옴표 없는 `<포털 도메인>` 자리표시는 리다이렉션으로 읽혀 새 박스의 기동이 깨진다. 예시 값은
  따옴표로 감쌌고, 같은 HP-71 을 짓는 KooRemapper · HEAXHub 에 전했다.
- **KooRemapper** — R-04 · HP-71 은 바로 짓는다. 코어 클라이언트는 `trust_env=False`(KR-14)라 코어 받기는 NO_PROXY 와 무관하고, `_common.sh` 가 루프백을
  NO_PROXY 에 넣은 뒤 .env 를 읽어 `.env` 에 포털 도메인만 적으면 루프백이 빠진다 — 예시에 루프백까지 적는다. **R-09 는 그쪽에서 사용자 결정 둘을 묻는다**
  (판 입력칸을 문구만 · 과제코드도 풀기 · 거절 / 레시피 내보내기 자리 — 10-27 사용자가 고른 'git 내보내기 → 커밋' 설계가 바뀐다).
  **그쪽 사용자 결정(11-25)** — R-04 「같은 뿌리 다섯도 기다리게」 · R-09 (가) 「풀고, 안 풀리면 거절」 · (나) 「데이터 뿌리 아래로」. 뒤이어 가지 `corelink-int` 에
  로컬로 지었다 — R-04 `8e2f9a97` · `3a7393d5`(설치는 대상 옆 임시 파일 + `mv -fT` · stop 뒤 사라질 때까지 기다림 상한 `KOORM_STOP_WAIT_S` 60초, 모름은
  사라졌다고 안 봄 · 같은 뿌리 다섯 — restart · start 의 postgres 두 자리 · reset-db(사라진 걸 본 뒤에만 pgdata 지움) · supervisor · 훑는 시험 변이 17/17) ·
  HP-71 `1c3e604d` · `0c081725`(자리표시 따옴표 · 바꾸지 않은 자리표시 주소가 InvalidURL 로 받기를 통째로 터뜨리던 틈을 bad_url 로 멈춤) ·
  R-09 (가) `654079dc`(판 확정이 과제명 · 과제코드 · 옛 과제명 · 별칭으로 풀고 없음 · 둘 이상이면 400 task_unresolved + 후보, 허브 거울에 과제가 없는 박스는 글자 그대로) ·
  (나) `13340956`(등록 레시피 내보내기를 데이터 뿌리 `svc/kooremapper/recipes` 로 · 기동 때 리포 씨앗과 둘 다 읽음 · 그 자리가 없는 박스는 git 밖
  `platform/infra/data/recipes` — 10-27 설계가 가리킨 `tools/recipes_publish.sh` 는 리포에 없었다). 시험 백엔드 1166 통과(실패 4 는 작업 트리에 .env 가 없는
  감독자 로그 시험 — 올릴 때 주 체크아웃에서) · MCP 계약 13/13. **운영 사람 몫(착지 때 편지함)** — 데이터 뿌리의 `svc/kooremapper` 에 API 사용자가 쓸 수
  있어야 한다(storage 와 같은 소유자). 못 쓰면 등록은 되고 파일 내보내기만 경고. 남은 것 ST-25-KR(블록 뒤) · KR-12(DP-13 뒤) · KR-10 · KR-19(R25-Q6 뒤).
- **ste** — PA-15 초안 맞음(`f923f96` — 요청 때 잰 크기를 선언하고 그만큼 보냄). PA-02 도 맞음 — 에이전트가 서버 크기를 그 앞 목록 크기와 견줘 도는 LS-DYNA 의
  d3hsp 는 늘 '크기 불일치' 로 지워진다(10-23 ~ 25 TB 급 되풀이). 고치는 길은 사용자 PC 재설치가 따라 그쪽 사용자에게 고르게 한다.
  **그쪽 사용자 결정(11-25) — 도는 잡의 큰 파일(64 MB 넘음)은 받지 않고 잡이 끝난 뒤 한 번 받는다.** 사용자 PC 에이전트를 새로 받아 두 번 누르는 걸음이 따른다
  (착지 때 편지함에 사람 몫으로 싣는다).
  뒤이어 로컬 main 에 지었다(원격보다 20 커밋 앞) — PA-02 `2397f32`(64 MB 넘는 파일은 잡이 끝난 뒤 한 번 · 끊기면 Range 로 이어서 · 작은 로그류는 도는 동안에도,
  가짜 서버 시험이 「도는 잡 세 번에 큰 파일 0 번 · 끝나면 한 번」 을 지키고 옛 코드에서는 떨어짐 · 서버는 그대로 · 화면 안내 글도) · BG-6 `21a1718`(설명 한 줄) ·
  기록 `79b17ee`. PA-15 는 코드로 확인한 앞 답 그대로 — 그 시각의 로그로 가른다(R25-Q11). `3c36726` 은 서버 쪽 고침이고
  운영이 11-23 에 `269f8c4` 로 바꿔 이미 들었다. **BG-6 은 param 을 더하지 않는다** — 두 번 줄일 틈만 생긴다. part-study 입력 설명에 좌표 · STL 은 m 라고 적는다.
  **덧붙임(11-25 오후, 요청서 밖)** — 그쪽 사용자 결정으로 새 해석기 CalculiX(ccx 2.23 · ste 앱 `calculix`)를 이번 라운드에 같이 올린다. 솔루션 꾸러미
  KooCalculiX(SIF 포함 — 원본은 KooSolverContainer `b8cc5bd` · `37b815c`)는 동결이 풀리면 ste 커밋 push 와 함께 Drive SmartTwinSolutions 로 간다.
  cae00 안내에 「꾸러미를 `/data/SmartTwinSolutions/KooCalculiX` 에 푼다」 가 더해진다(착지 때 편지함에 사람 몫으로).
- **MXWP** — MW-08 · MW-09 초안 둘 다 맞음. D7 재료 — seed 는 slug 가 겹치면 내용만 덮고 상태는 둔다: **보관한 것은 seed 를 다시 돌려도 보관, 지운 것은
  seed 가 다시 돌면(fresh · recover · clean_db · reset-db --seed · make seed) published restricted 로 되살아난다**(update-all 은 seed 를 돌리지 않는다).
  MW-09 덧 — admin 서비스 계정이면 남의 '내 후보' 에 후보를 넣을 수 있고 사람 신원이 남지 않는다. 연결기(W8)는 막지 말고 전용 계정으로 가른다.
  MW-06 은 지금 짓지 않는다(화면 설명 한 줄뿐 · 코어 받기 코드와 한 번에).
- **HEAXHub** — 넷 다 HEAD `0cf7a45` 에 그대로 남았다. 셋을 짓는다(로컬 커밋까지). HH-18 은 런처가 띄울 때마다 `$ROOT/.env` 를 읽어 얹는 도우미 하나를
  호스트 · SIF · 프록시 자리에 쓴다 — 따옴표는 백엔드 설정과 같은 python-dotenv 로 풀고, `.env` 에서 지운 키는 `APPTAINERENV_*` 만 뺀다(프록시 · LLM · 검색 키는
  셸 프로필에서 올 수도 있어 `.env` 에 없으면 프로세스 값 그대로 — 그쪽 사용자 결정). HP-71 은 예시 두 줄을 따옴표로. SE-8 은 받기 스크립트 셋의 되풀이를 줄이고
  tar 를 영구 캐시에 두어 'DB 밖 심기' 결정이 필요 없게 한다. **IR-24 는 DocForge 정본 릴리스(IR-23 뒤) 를 따라 doc_forge SIF 다시 짓기와 한 번에**(R25-5).
  뒤이어 main 로컬에 지었다(빌드 틀 .def · doc-forge 등록 사본은 손대지 않음 — R25-11) — HH-18 `c9f39fd`(런처 호스트 · SIF 와 apt_runner 의 instance start · exec
  가 띄울 때마다 `.env` 를 다시 읽어 얹는다 · CA 번들 경로도 같은 env · apptainer 는 --cleanenv 여도 호스트의 APPTAINERENV_* 를 넣어 apt_runner 까지) ·
  HP-71 `0375156`(주석 줄 · 따옴표 · 풀어도 bash source 와 python-dotenv 가 같은 값) · SE-8 `38baee7`(요청 1 ~ 5 전부 · 백업 사본은 DB 마다 최근 3 —
  요청의 '적어도 하나' 를 지킨다 · DB 밖 심기는 캐시에서 풀어 계속 돈다). 시험 — 백엔드 실패 14 는 변경 전과 같고 새 시험 8 통과, dist · models 는 가짜 rclone 으로 실측.
  **cae00 첫 실행에서 보일 것**(착지 때 편지함에) — appdata 는 표시가 없어 한 번 병합(0건)한 뒤부터 건너뛰고, 그 실행에서 쌓인 `.pre-merge` 사본 348개가
  DB 마다 3개로 준다(약 8 GB 회수 — 요청이 바란 것) · models 건너뛰기는 **dev 가 models-to-drive 를 한 번 돌려 Drive 에 MANIFEST 가 생긴 뒤부터**(그 전에는
  --fast-list 전체 비교) · dist 는 첫 실행만 전체 검사.
- **DocForge** — 17건 받음 · 사용자 결정 둘 받음. 지금 HEAD 의 코드는 `4804aca` 와 같고(그 뒤는 문서뿐) 계획서와 다른 판정은 없다 — srcRect 는 pptx 에만
  있고 docx · xlsx 에는 아예 없다 · 생각 끄기는 `modelcall.py` 에 고정 · 동시 수 세마포어는 클라이언트마다 따로 · `matched_by` 없음. 차례는 PLAN 그대로이고
  DFO-3 은 DFO-2 와 같은 자리라 같이, `PROMPT_VERSION` 은 IR-11 · IR-17 · IR-20 을 한 번에 올린다. IR-11 — 쪽 그림(snapshot_page)이 이미 있으면 그것을 쓰고
  없을 때만 DocForge 가 그린다(같은 쪽을 두 번 그리지 않음). 코드는 따로 작업 폴더의 가지 `req1125` 에만, push · release · Drive 는 알림 뒤 · Drive 는 그쪽
  사용자 승인도 거친다.
  뒤이어 17건을 가지 `req1125` 에 다 지었다(로컬 커밋 14 · 시험 319 통과 · 그쪽 결정 R-D57 ~ R-D69). 해제 뒤 main 에 합쳐 push 하고 그쪽 사용자 승인으로
  **0.4.0 배치** — release → HEAXHub 등록 사본(IR-24 줄을 뺀 매니페스트 — 열쇠가 바뀐다) → SIF → Drive 차례. **운영이 알고 받을 것**(그쪽 초안, 착지 때 편지함에)
  — ① 잡 수는 knobs.env 의 `DOCFORGE_MAX_JOBS`(매니페스트에서 뺌), 판독 동시 수 `DOCFORGE_VLM_MAX_CONCURRENCY` 는 이제 잡 수와 상관없는 서버 전체 상한(4 그대로 둬도 됨)
  ② vlm 이 켜지면 그림 파일로 못 읽는 것(연결선 · 글 없는 도형 · 그림 채움 · 잘린 그림 · SmartArt · 묶음 등)이 있는 슬라이드만 DocForge 가 그려 판독(snapshot_page 없어도)
  ③ 새 옵션 `snapshot_blocks`(selected 기본 · all · none — snapshot_page 일 때 보고서에 싣는 쪽 그림) ④ 판독 지시 판 `df-vlm-3` 이라 판독 캐시가 새로 쌓인다
  ⑤ 판독을 심의 모델로 옮기려면 `DOCFORGE_VLM_THINKING_OFF=0`(capabilities 의 `vlm.thinking_off`) ⑥ `docforge_package` 응답에 `links[{type_slug · key · label · code ·
  matched_by}]`, capabilities 의 ontology 에 stale 묶음. 확인할 것은 11-10 시험 덱의 쪽별 모습(흐름 글이 판독 없이 · 잘린 코드 없음 · 그림 채움 · TIFF → PNG ·
  캡션 꼴 · 표 그림이 표 위젯 하나 · 판독 블록 라벨 = document.md 의 [그림 N]).
  **요청과 다른 곳 하나** — DFO-1 은 옛 행을 지우지 않고 stale 로 따로 보이게만 했다. 요청의 '쓰는 곳이 없으면 지운다' 는 키트 수신 규칙(타입별 since 커서)과
  얽혀 되돌릴 수 있는 쪽을 골랐다 — 착지 때 편지함에 그 까닭과 함께 적는다. **포털 IR-02(미배정 몫)는 snapshot_page 만 넘기면 된다** — 새 옵션을 넘길 필요 없음.
- **브리지** — 3-2 절 · §5-2 판정이 그쪽 기록과 맞다. **ST-7 은 그쪽 사용자 결정(11-25) 「레디쉬 빌드만 길을 둔다」** — 레디쉬 래퍼에 짓고 앱 선언(파라미터)은
  ste-06 에 넘긴다. BG-1 은 StepForge `feat-1125` 의 export-part-step REST 에 맞춰 `fetch_part.py` 에 「그 파트만 받기 · part_not_found」 를 짓는다 — part 가
  기록용에서 파트 고르기로 바뀌어 part-study 인자 · 레지스트리 선언은 06 과 맞추고, 잡 한정 토큰은 사용자 결정(주소만 먼저)대로 지금은 다루지 않고 발급하는
  곳이 생긴 뒤 stepforge-d4 와 맞춘다. 운영에서 쓰려면 StepForge 착지(동결 해제 뒤)와 다음 브리지 SIF 가 함께 가야 한다. ST-1 은 SF-3 출력 뒤. 다음
  꾸러미에 ST-17(`a9655da`) · `3bc5584` · ST-7 · BG-1 을 싣고 해제 알림 뒤 그쪽 사용자 확인을 받고 낸다. ST-2 · ST-8 은 R25-Q8 · Q9 답을 기다린다.
  **뒤이어 지음(11-25, 코드만)** — ST-7 은 레디쉬 래퍼 `--build-only 0|1`(ste `47b108f` — 케이스를 짓고 해석기 스키마로 검사한 뒤 멈춘다, 지은 케이스 ·
  예제 값으로 남은 칸 · 경고 · 파생량을 잡 요약에 · 앱 선언 build_only 는 06), BG-1 은 브리지 `fetch --part`(KooSolverContainer `6c2e83f` — export-part-step
  REST 로 그 파트만, 크기 · sha256 대조) · part-study `--part`(ste `fa1af4b`), 사유 part_not_found · stepforge_outdated · bridge_outdated(옛 브리지는 과제 전체를
  조용히 받지 않고 멈춘다). **레지스트리 요청서의 part 를 「그 파트만 받기」 로 바꾸는 일(06 의 선언 + 튜플)은 새 브리지 SIF 와 StepForge `feat-1125` 가 운영에
  든 뒤로 미룬다** — 먼저 바꾸면 part 를 적은 지금 요청들이 실패한다.

## R25-11 IR-24 등록 사본은 DocForge 배치가 고친다(11-25)

- PLAN 은 처음에 IR-24 를 DocForge(원본) · HEAXHub(사본) 두 세션에 나눠 보냈다. DocForge 가 「등록 사본 고치기는 배치 때 DEPLOY §7 대로 이쪽이 해 왔다」 고
  짚었다. DocForge `docs/DEPLOY.md` §7 의 2 가 바로 그 절차다 — release 를 옮긴 바로 뒤, 다음 스캔(300초) 전에 HEAXHub 등록 사본 하나만 커밋한다.
  늦거나 먼저 하면 스캐너가 옛 판 숫자로 한 번 더 짓는다(10-24 · 11-07 · 11-12 배치 기록).
- 그래서 사본 고치기는 DocForge 배치에 붙이고 HEAXHub 세션 목록에서 뺀다. 두 세션이 같은 줄을 고치면 커밋이 겹치고, 그 차례가 어긋나면 SIF 가 두 번
  지어진다. HEAXHub 세션에는 HH-18 이 빌드 틀(fastapi 틀 등)을 건드리지 않게 한 줄 덧붙였다 — 틀은 모든 허브 앱의 캐시 열쇠에 든다.

## R25-12 ST-27 운영 표본은 운영 박스에서 세고 숫자만 받는다(11-25)

- StepForge 는 운영 파트 이름 50 과 사람이 정한 역할을 JSON 으로 받아 dev 에서 `--sample` 로 읽겠다고 했다(리포에는 안 싣는다). 그래도 사내 CAD 이름이 운영
  박스 밖으로 나가는 길이다 — 과제 실물은 dev 로 꺼내지 않고 운영 박스에서 시험하고(`docs/ste-stepforge-1117`), 고리는 cae00 에서 닫는다.
- 그래서 표본 파일은 cae00 에만 두고 그 박스에서 채점 틀을 돌려 판정 셋의 숫자(맞힘 · 엉뚱 · 못 붙임)만 받는 꼴로 StepForge 에 제안했다. 돌리는 명령 · 숫자만
  내는 인자를 그쪽이 확인하면 받은 편지함 R25-Q12 로 싣는다.
- StepForge 가 그 꼴로 지었다(갈래 `feat-1125` `f0e63c5a` — 착지 판에 든다). SIF 가 리포 체크아웃을 `/app` 에 실어 스크립트 · 참값 표가 다 있고, `--sample-only` 면
  참값 표를 안 읽는다. `--counts-only` 는 화면 · JSON 어디에도 이름을 안 내고 `--changed` 와 함께 주면 인자 단계에서 거절한다(회귀가 본다). 편지함 R25-Q12 에 실었다.

## R25-13 ST-25 는 운영 쪽 답 넷 뒤에 짓는다(11-25)

- StepForge 가 짓기 전에 넷을 물었다 — 코어 부품 위아래 칸 · 별칭 사전 · 잡음 낱말 표 · 11-24 측정 재현. dev 에서 맞대 보니 `kind_parent` 는 어느 리포에도 없고
  (요청서에만 있다) SP plm-core 정의에도 없다. 요청서가 든 `part_id_rule.yaml:29-35` 는 StepForge 의 특수 PART ID 대역 표라 잡음 낱말 표가 아니다 — 요청서의
  자리 인용이 틀렸거나 운영 세션이 따로 쓴 목록을 가리킨다. 넷 다 운영 박스에서만 답이 나오므로 받은 편지함 R25-Q13 ~ Q16 으로 실었다.
- 공통 블록(D-689 · ST-25-KR)에서 바뀌는 것은 `src_type_slugs` 에 cad_part · 설명의 앱 목록 · rule 근거 층 도움말이다. 블록이 서면 StepForge 가 그 바이트와
  sha 를 포털 · KooRemapper 에 함께 보낸다(R25-4).

## R25-14 SmartTwin MCP 몫은 `smarttwinmcp-c8` 이 맡는다(11-25)

- 11-24 22:02 UTC 에 `smarttwinmcp-4c` 에 보낸 SM-04 · 01 · 02 · 03 에 답도 커밋도 없었다(11-25 14:35 KST 기준 idle).
- 같은 날 KooSlurm `dashboard/smarttwin_mcp` 를 실제로 고친 세션은 `smarttwinmcp-c8` 이다. 낙하 트윈 계약 C-1 의 job_status `runs:true`(`e5cb6f41` ·
  `0b46313f`)로, KooRemapper 가 KR-10 · KR-19 결과 회수에 쓸 칸으로 짚었다. 그래서 묶음을 c8 에 다시 보내고, 4c 에는 손대지 않았으면 두고 시작했으면
  c8 과 이 세션에 알리라고 했다(겹침 막기 — c8 은 시작 전에 SM-04 커밋이 있는지 본다).
- 맞댄 판 `ea9ebe59` 뒤의 변경은 C-1 의 job_status 뿐이다. SM-04 · SM-01 자리는 그대로이고, SM-02 는 C-1 이 고친 job_status `meta.yaml` 위에 읽기 칸을 얹는다.

## R25-15 업데이트 차례 — 5차는 지금, request-1125 몫은 6차(11-25)

- 87 확인(11-25) — 5차 라운드는 11-24 글 그대로 cae00 이 돌려도 된다. 원격 머리가 5차 고정 판과 같고(게이트웨이 · 에이전트 · AIDataHub · StepForge · WDA ·
  MXWP · KooRemapper · HEAXHub · SignalForge 모두 뒤 커밋 0), 포털 main 은 docs 커밋만, Drive latest 도 그대로다. update-all 이 11-25 편지함(R25-Q12 ~ Q16)을
  새 글로 찍지만 막지는 않는다 — Q29 와 함께 답할 물음이 늘었을 뿐이다.
- 동결은 Q29(update-all 끝 코드 · ✗ · ○ 줄 · 「풀어도 된다」)가 와야 풀린다. 풀리면 87 이 이 세션에 알린다.
- 풀린 뒤 — 아홉 세션의 push · Drive 는 87 의 병합과 따로 가도 된다(리포가 다르다). Drive SIF 올리기는 자동 모드가 막으면 사람 몫이다. 게이트웨이 병합 차례는
  fig-race → interactions → offload-finish(87) → `wt1124/ste-upload-sha`(71) — gateway.py 가 겹쳐 앞엣것이 들어간 뒤 rebase 사본으로 시험하고 `--no-ff` 로 병합한다.
- 6차 편지함은 87 이 쓴다. 이 세션은 request-1125 몫의 착지 판(리포 · 커밋 · Drive 이름 · SIF 파일 sha256 과 캐시 열쇠는 이름을 붙여 따로)과 사람 몫을 모아
  건넨다 — 해시는 병합 · push 가 끝난 판으로(로컬 커밋 해시는 rebase 하면 사라진다), 실제 주소 · 이름은 빼고.

## R25-16 5차 동결 해제 — ste · 브리지는 계속 묶는다(11-25)

- cae00 5차 답(11-24 글 Q29 ~ Q39)을 사용자가 이 세션에 붙여 넣었다. update-all 끝 코드 0 · ✗ 0 · 박스는 「풀어도 된다 · 최종 결정은 사용자」. 폴더별 기록은
  87 이 했다(`42e05012` — leftovers-1121 L21-29 · request-1123 NX-4 · token-saving). 답 원문은 리포에 두지 않는다.
- **사용자 결정(11-25) — 동결을 푼다.** 일곱 세션(StepForge · DocForge · HEAXHub · SignalForge · MXWP · KooRemapper · SmartTwin MCP c8)에 push · Drive 를
  알렸고, 착지 판은 push 뒤 해시 · Drive 이름 · SIF 파일 sha256 과 캐시 열쇠를 이름 붙여 따로 · 사람 몫 · DB 이관 유무로 돌려받는다.
- **ste · 브리지는 계속 묶는다.** cae00 ste 자동 교체(staging `859a02d`)가 아직이다(Q35 — 도는 잡 13 · 기한 11-26). 4차 답 때 정한 「ste · 브리지는 ste 가
  바뀔 때까지」(SS-12)가 그대로 간다 — 87 도 같은 판단. ste-06 의 17커밋 · CalculiX, 브리지 다음 꾸러미는 cae00 이 ste 교체를 보고한 뒤에 푼다.
- **StepForge 는 운영이 지난 판을 건너뛴다.** 운영은 아직 `edcddf44`(5차의 `a7c65a5e` 를 넣지 않음 — 시점은 그쪽 사용자). feat-1125 는 운영이 받지 않은 판
  위에 쌓이므로 87 이 6차 글에 「a7c65a5e 를 건너뛰고 새 판을 바로 받아도 되는지」 를 넣는다 — StepForge 에 그 답(DB 이관 · 설정 변화 · 잡 취소)을 함께 달라고 했다.
  BG-1 의 StepForge REST 는 먼저 들어가도 된다(브리지 쪽 바꿈은 묶여 있고 레지스트리 part 의미는 둘 다 운영에 든 뒤).
- ST-25 · ST-27 표본은 이번 착지에 없다 — 운영 답 R25-Q12 ~ Q16(받은 편지함 11-25)은 이번 답에 없었다(update-all 이 그 글 전에 돌았다).
- request-1125 1-3 절(토큰 절감 쪽)은 87 의 미병합 `wt1124/offload-finish` 와 같은 파일이라 87 이 말할 때까지 아무에게도 보내지 않는다(87 부탁).
- §5 의 `✓ 기존 kr_ PAT 유효` 줄은 update-all 점검이 아니라 게이트웨이 provision 이 찍은 줄이었다 — 87(포털) 몫, 6차에 묻는다.
- **바로잡기(브리지 답 11-25)** — 다음 꾸러미의 브리지 SIF 는 `6c2e83f` 가 아니라 `koo_stebridge-e52a03a.sif`(파일 sha256 `8d1e7c45…`)다. ste-06 의 스테이징
  끝단이 짚은 둘을 고쳐 다시 지었다 — 옛 StepForge 의 404 를 어느 글이든 `stepforge_outdated` 로 가른다(브리지 `e52a03a`), 고른 파트를 못 받으면 올린 STEP 으로
  잇지 않는다(ste `58508e9`). 06 이 스테이징에서 다시 돌려 확인했다. 꾸러미(KooFEniCS · KooOpenFOAM)는 그대로. StepForge 파트 반출 REST 가 먼저 운영에 들면
  레지스트리 part 의미 바꾸기(06 가지 `b4503ec`)에 남는 조건은 새 브리지 SIF 하나다. 브리지는 ste 교체 보고 뒤 그쪽 사용자에게 Drive 를 묻고 반영 안내 ①②③ 을 쓴다.
- **바로잡기(ste-06 답 11-25)** — ste 로컬 main 은 origin(`859a02d`)보다 **34 커밋** 앞선다(17 아님 — PA-02 · BG-6 · CalculiX · 선언 둘 `6585583`(레디쉬 빌드만 ·
  part-study 그 파트만 받기) · 브리지 세션의 래퍼 셋 `47b108f` · `fa1af4b` · `58508e9` · 문서). 레지스트리 part 는 main 이 아니라 가지 `registry-part-fetch`(`b4503ec`)
  — 새 브리지 SIF 와 StepForge feat-1125 가 운영에 든 다음 라운드에 합친다. 라이선스 서버 기본값을 빼는 가지(`0313ceb`)는 cae00 이 `.env` 에
  `STE_LSTC_LICENSE_SERVER` 를 넣었다고 알려야 올린다(Q35 — 아직 안 넣음 · 시점은 그쪽 사용자). 스테이징 VM 은 ste `58508e9` · 브리지 SIF `e52a03a` · 솔루션 꾸러미
  stage-1125(`63b9f91`)로 운영과 다르다. 올리기는 ste 교체 보고 뒤 그쪽 사용자에게 다시 묻는다.

## R25-17 착지 판 모음(6차 편지함 — 87 에 건넨다, 11-25 ~)

> push 뒤 해시 · Drive 이름 · SIF 파일 sha256 / 캐시 열쇠(이름 붙여 따로) · 운영 손 · DB 이관. 모이면 87 에 한 번에 넘긴다.

- **게이트웨이** — master `63eed05`(fig-race · interactions · offload-finish(87) 뒤 `wt1124/ste-upload-sha` — P-1 ste 업로드 sha 대조, 옛 ste 와도 맞물림). dev 재기동
  87(16:17 UTC). 운영 손 없음.
- **MX 백서** — main `90f5d8d`(앞 판 `d755a00` 뒤 두 커밋 `8af70bc` · `90f5d8d` 은 문서만 — 동작 같음). Drive 바뀐 판 없음(`images-20261031-073148Z` ·
  `latest/` 그대로) → SIF sha256 · 캐시 열쇠 해당 없음(허브가 짓지 않고 update-all 의 Drive 받기로 든다). 운영 손 없음 · DB 이관 없음 · 재기동 없음.
  알고 받을 것 — `d755a00` 의 `wiki.def`(프록시 기본값 뺌)는 다음 wiki.sif 에 든다. 지금 판도 `.env` 의 `MXWP_FALLBACK_PROXY` 를 먼저 쓰니 5차에서 그 줄이
  있는 박스는 동작이 같다(비면 지금 판은 옛 기본값, 새 판은 직결).
  - MW-08 답 — **시드다.** 골든 샘플 17 가운데 restricted 는 06 · 08 두 장이고 시드가 전부를 시드 관리자 소유 · 첫 판 메모 `seed` 로 싣는다. 그래서 D7 ① 은
    소유자 정정이 아니라 보관 또는 지움. 보관은 seed 를 다시 돌려도 보관으로 남고, 지운 것은 seed 가 다시 돌면(새로 깔기 · DB 초기화 — update-all 은 seed 를
    안 돌린다) published restricted 로 되살아난다. 이 박스의 두 장이 같은 글인지는 R25-Q5 가 가린다.
  - MW-09 답 — **맞다, 약해진다.** 원천 보내기는 호출자 역할로 시야를 짓고 게이트웨이 서비스 계정은 기본이 관리자라 범위 검사 · 주인 바꾸기 검사를 건너뛴다 —
    챗이 그 계정으로 보내면 아무 범위 · 남의 주인으로 보낼 수 있고 보낸 사람이 기록에 안 남는다. 관리자 아닌 계정으로 바꾸면 연결기가 깨진다. 결론 — 챗에서
    위키 보내기를 켜기 전에 사람별 위임(D7 ②), 연결기(W8)는 막지 말고 전용 계정으로 가른다.
  - MW-06(선택) — 이번 착지에 없다. 코어 받는 코드와 함께 새 이관으로(MX 백서 W8 체크리스트).
- **SignalForge** — main `4e44497`(병합 `1ea7aa3` — SFO-1 · 2 `abf2e38` · SFO-3 `e78b853` · SFO-5 `842c188` · HP-71 `157a2e6`, 그 위 cae00 문서). Drive 새 이미지
  없음(`SignalForge/sif/latest/` 그대로 — 11-25 정기 동기화분). SIF 변경 없음 — sf-mcp 의 `mcp.sif` 파일 sha256 `68fed2ae…`, 허브 캐시 열쇠는 해당 없음(자체 빌드 ·
  Drive SHA256SUMS). 운영 손 — 코드 받기(update-all) → sf-mcp 다시 띄우기(update-all 이 안 했으면 11-07 문서 4절 워치독 락으로 — 다른 인스턴스는 그대로) → 확인
  (SignalForge `docs/DEPLOY_CAE00_2026-11-25.md` 2절 해석 세 줄 · 3절 게이트웨이 여섯 부르기). PLM 다시 받기 · `.env` 변경 없음 · DB 이관 없음(alembic 0048).
  들어간 뒤 박스 어휘표에 `ontology_lookup` 다음 호출 `search_voc(core_type=…, core_key=…)` 줄을 넣어도 된다(선택). dev 는 sf-mcp 재기동 · 새 인자와 응답 칸 확인.
  SFO-4 는 R25-Q4 답을 기다린다.
