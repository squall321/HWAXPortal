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
- **SignalForge** — main `51ee09b`(그 아래 코드 판 `4e44497` — 위는 체크리스트 한 줄 문서만)(병합 `1ea7aa3` — SFO-1 · 2 `abf2e38` · SFO-3 `e78b853` · SFO-5 `842c188` · HP-71 `157a2e6`, 그 위 cae00 문서). Drive 새 이미지
  없음(`SignalForge/sif/latest/` 그대로 — 11-25 정기 동기화분). SIF 변경 없음 — sf-mcp 의 `mcp.sif` 파일 sha256 `68fed2ae…`, 허브 캐시 열쇠는 해당 없음(자체 빌드 ·
  Drive SHA256SUMS). 운영 손 — 코드 받기(update-all) → sf-mcp 다시 띄우기(update-all 이 안 했으면 11-07 문서 4절 워치독 락으로 — 다른 인스턴스는 그대로) → 확인
  (SignalForge `docs/DEPLOY_CAE00_2026-11-25.md` 2절 해석 세 줄 · 3절 게이트웨이 여섯 부르기). PLM 다시 받기 · `.env` 변경 없음 · DB 이관 없음(alembic 0048).
  들어간 뒤 박스 어휘표에 `ontology_lookup` 다음 호출 `search_voc(core_type=…, core_key=…)` 줄을 넣어도 된다(선택). dev 는 sf-mcp 재기동 · 새 인자와 응답 칸 확인.
  SFO-4 는 R25-Q4 답을 기다린다.
- **DocForge(준비 끝 · 올리기는 그쪽 사용자 승인 대기)** — 0.4.0 로컬 준비(판 올림 · 시험 319 통과 · req1125 → main 빠른 감기). 차례 — main · push → release 빠른 감기 →
  HEAXHub 등록 사본(IR-24 — 매니페스트 통째, 판 0.4.0 · `DOCFORGE_MAX_JOBS` 줄 빼기) → 빌드 · 재배치 → Drive → HEAXHub push(SIF 가 Drive 에 오른 뒤 — DEPLOY §7-2)
  → 일치 점검. HEAXHub 로컬 main 에 그쪽 미푸시 커밋 넷이 있어 heaxhub-4b 가 먼저 push 하지 않으면 함께 내보내지 않고 맞춘다. DB 이관 없음. 해시 · Drive · SIF 값은
  끝난 뒤 따로 온다. 6차 편지함 꼴은 DocForge 가 준 그대로 싣는다 —
  ① 잡 수 — 매니페스트에서 `DOCFORGE_MAX_JOBS` 를 뺐다 → `<데이터>/knobs.env` 의 값이 먹는다(없으면 1 · 재기동 없이 다음 잡부터, 이미 적은 값이 있으면 0.4.0 부터
  그 값). `DOCFORGE_VLM_MAX_CONCURRENCY` 는 잡 수와 상관없이 모델 서버 하나에 대한 전체 상한. ② 고른 쪽 판독 — vlm 이 켜지면 그림 파일로 못 읽는 것(연결선 · 글
  없는 도형 · 그림 채움 · 잘린 그림 · 웹에서 못 여는 형식 · 빠진 그림 · SmartArt · 묶음 · OLE)이 있는 슬라이드만 쪽 그림으로 판독, snapshot_page 는 켜지 않아도 된다.
  ③ 새 옵션 `snapshot_blocks`(selected 기본 · all · none) — 판독용으로만 그린 쪽 그림은 보고서에 싣지 않는다. ④ 판독 지시 판 df-vlm-3 — 캐시가 새로 쌓여 첫 변환은
  한 번 더 든다. ⑤ 생각 끄기 — 기본 그대로, 판독을 심의 모델 끝점으로 옮길 때만 `DOCFORGE_VLM_THINKING_OFF=0`(판단 끝점이 따로면 `DOCFORGE_LLM_THINKING_OFF=0`) —
  capabilities `vlm.thinking_off` · `llm.thinking_off`. ⑥ SP 연결 — `docforge_package` 응답과 conversion.json 에 `links[{type_slug · key · label · code ·
  matched_by}]`, capabilities 의 ontology 수는 받는 타입만 · 받지 않는 타입의 옛 행은 stale 묶음. 시험 덱 확인(11-10 덱 · vlm 켬) — 5쪽 흐름 글이 판독 없이 · 7쪽
  잘라 가린 부분의 코드 없음 · 8쪽 그림 채움이 그림 요소로 · 10쪽 TIFF → PNG · 2쪽 캡션 '[모델 판독] 요약' 꼴 · 4쪽 표 그림이 표 위젯 하나 · 판독 블록의 그림 번호가
  document.md 의 [그림 N] 과 같음 · capabilities version 0.4.0 · max_jobs 가 knobs.env 값. DFO-1 은 지우지 않고 stale 만 — 옛 행이 키트 수신 규칙(타입별 since
  커서)과 얽혀 지우면 되돌리기 어렵다. 운영 손 — update-all 로 받기 · 고를 일 둘(잡 여럿이면 knobs.env 의 `DOCFORGE_MAX_JOBS`, 판독을 심의 모델로 옮길 때만
  `DOCFORGE_VLM_THINKING_OFF=0`).
- **KooRemapper** — 코드 `6a90a416`(`76067368..6a90a416` — R-04 → HP-71 → R-09 → 낙하 ⑥ 이미지 출처 받기(87 이 해제한 몫도 같은 판)), 그 뒤 문서만 `99eba022` ·
  `6299c510`(main 끝). Drive `dist-20261125-161932Z`(되돌릴 판 `dist-20261123-094507Z`). 7판과 다른 파일 둘 — `BUILD_INFO.txt` `5ecdd57b…` ·
  `koorm-frontend-dist.tar.gz` `97ec1a72…`, 그대로(C++ 안 바뀜) — 바이너리 `139036f2…` · `koorm-bin.tar.gz` `75229e42…` · cli.sif `38d7bb4d…` · api.sif `1a304194…` ·
  mcp.sif `cd325209…` · nginx.sif `22ac1af7…` · postgres.sif `465519bc…`. 캐시 열쇠 — health 의 revision 캐시는 `bin/BUILD_INFO.txt` 파일이 열쇠라 반입하면 재기동
  없이 revision 이 `6a90a416`(dev 실측), health `binary_sha256` = 바이너리 파일 sha256. DB 이관 없음(0026) · MCP 도구 120 · 연산 65(설명만 바뀜).
  운영 손 — ① 운영 노드 반입(git 받기 + Drive 반입 — update-all 또는 `dist-from-drive.sh --restart`, 새 원자적 설치 스크립트는 git 으로 온다) ② **편지함 한 줄** —
  「DynaForge 운영 노드 — API 를 띄우는 사용자가 `<데이터 뿌리>/svc/kooremapper` 에 새 폴더를 만들 수 있어야 한다(등록 레시피 내보내기 · storage 와 같은 소유자면
  됨). 확인은 그 사용자로 `test -w <데이터 뿌리>/svc/kooremapper && echo ok`. 못 쓰면 등록은 되고 파일 내보내기만 경고」 ③ 확인 — KooRemapper cae00 점검 문서 §1-15
  (health revision `6a90a41` · matches true · binary `139036f2…` · tools-map `heax-kooremapper_mcp` 120 · reachable) ④ 알고 받을 것 — stop · 재기동 스크립트가 인스턴스가
  60초 안에 안 사라지면 rc≠0 으로 멈춘다(`KOORM_STOP_WAIT_S`). **포털 `_stop` 이 rc 를 삼키면 그 멈춤이 안 보인다 — 포털(87) 몫으로 넘긴다.** dev — R-04 기다리기
  실물 통과 · 스모크 넷 · supervisor_log 4/4 · 백엔드 1166 · MCP 계약 13/13. KR-10 · KR-19 · KR-12 · ST-25-KR 은 기다린다.
- **SmartTwin MCP(c8 — 받음 · 차례)** — 11-25 SM 넷 받음(원문 3-10절 · SM 커밋 없음을 git log 로 확인). 그쪽 사용자 결정 — SM-04 → SM-01 → SM-02 → SM-03 → 카탈로그
  재생성(Pre v141 · Post v54 · KCR 새 명령 9개 도구화 · RIGID_DROP_ENDTIME · unified_analyzer rc 3), 항목마다 시험 통과면 main · push · 재시작. 지금까지 C-1(`e5cb6f41` ·
  `0b46313f` — push · 재시작 끝). **71 이 짚은 것** — 운영 stcx 는 아직 Pre v128 · Post v50(SP-5 · Q34 — v136/v51 · v141/v53 · v54 모두 안 깔림)이라 카탈로그가
  새 명령을 내걸면 운영에서 없는 판에 닿는다 → 판을 보고 거절하든지 설명에 「Pre v141 · Post v54 이상」 을 적어 달라고 했다(고르는 것은 c8).
- **HEAXHub** — main `38baee7`(`948c98c` 뒤 넷 — `0cf7a45` DynaForge 설명 op 수 · HH-18 `c9f39fd` · HP-71 `0375156` · SE-8 `38baee7`; DocForge 등록 사본 커밋이 곧 얹히므로
  `38baee7:main` 까지만 내보냄). models-to-drive 끝 — Drive `<remote>:HEAXHub/models/<앱>/MANIFEST` 셋(doc_forge 149 · thermal_shock_mcp 3 · voice_recorder 133 —
  합 285, 비교만 · 전송 없음). SIF · .def · SIF 앱 등록 사본 변경 없음(integrations/ 는 proxy 앱 둘 설명 두 줄 — 캐시 열쇠와 상관없음). DB 이관 없음.
  운영 손 — 꼭 할 것 없음. **알아 둘 것** — ① appdata 첫 실행이 옛 `.pre-merge` 사본을 DB 마다 최근 3개만 남기고 지운다(11-24 기준 348개 · 약 8GB 의 대부분) —
  남기려면 update-all **전에** 다른 곳으로 옮기거나 `.env` 에 `HEAX_APPDATA_PREMERGE_KEEP=<개수>` ② HH-18 — `.env` 를 고친 뒤 떠 있는 앱은 그대로, 새 값은 그 앱의
  다음 기동부터(허브 재기동 필요 없음). 첫 실행 모습 — appdata: 한 번 병합(「→ merge: <앱>/<db>」 · 0건 추가) 뒤 「옛 안전백업 N개 지움(DB 마다 최근 3개 남김)」,
  둘째부터 「app-data tar 가 지난 병합 때와 같다 — 안전백업 · DB 병합 건너뜀」 · models: cae00 에 지난번 값이 없어 첫 실행은 한 번 더 전체 비교, 둘째부터 「Drive
  MANIFEST 가 지난번과 같다 — 건너뜀」 · dist: 첫 실행 「checksums OK(전체 — 주 1회)」, 그 뒤 「옮긴 파일 없음 — checksum 생략」 또는 「(이번에 옮긴 N개)」,
  frontend 「frontend-dist 그대로 — 풀기 생략」 · 진행 표시는 30초마다 한 줄.
- **StepForge** — main `d7be049c`(코드 판 `9a7ca9d1` 위 문서 하나 — Drive SIF 는 `d7be049c` 로 지음). Drive `dist-20261125-162758Z`(`latest/` 같음). `step_forge.sif` 파일
  sha256 `cb3cc68b…` · 허브 캐시 열쇠 `step_forge.sif.hash` `df1db69c…`(로컬 · 묶음 · latest/ 셋 맞댐, SIF 안 BUILD_INFO 는 `d7be049c`). 운영 손 없음 — 설정 변화 없음
  (reachable false · chat_cut 60000 · MaterialTwin 주소 안 넣음 그대로), 늘 하듯 교체 전에 도는 잡이 없는지만 본다(교체가 도는 잡을 끊는다 · 따로 취소할 일은 없음).
  DB 이관 없음 — `edcddf44` → `d7be049c` 사이 DB 칸 · 표 · 판 표시(ERA) · 잡 인자 시대 변화 0 · 새 설정 키 0. **`a7c65a5e` 를 건너뛰고 바로 받아도 된다**(그 판은 레디쉬
  꼴 접기 하나이고 이 판에 들어 있다). 실린 것 — ST-20 · 21 · 22 · 23 · 24 · 26(next 만 R25-Q3 대기) · BG-1 `POST /api/projects/{id}/export-part-step` · ST-27 틀 ·
  D-709 적층 해석기 통로 · SP 서브모듈 0.4.105(키트 · coreapi 그대로). 알아 둘 것 — 출하 대응표(ST-24)가 역할 → 코어 부품 선 14줄을 긋는다(운영 허브 거울에 그
  key 가 있으면 선, 없으면 매달린 끝으로만 센다). 미룸 — ST-25 · ST-27 표본(R25-Q12 ~ Q16 답 뒤). 회귀 8015 통과 · 배포 확인 셋 통과.
  → BG-1: StepForge REST 가 이 판으로 운영에 들면 레지스트리 part 의미 바꾸기(ste 가지 `b4503ec`)에 남는 조건은 새 브리지 SIF(`e52a03a` — ste 교체 보고까지 묶임) 하나.
- **SmartTwin MCP — SM-04 먼저 착지(c8)** — KooSlurm origin main `89172f14`(반영 기록 `d93017a5`). backend_5010 의 `jwt_required` · `optional_jwt` 가 `kst_` 를 SSO 꺼짐보다
  먼저 본다(틀린 `kst_` 는 401 · optional 은 익명, 머리 없는 웹 요청은 그대로 admin) · `/api/me` 에 auth 칸(pat|jwt|sso_off). MCP `caller_identity` 는 `kst_` + auth=pat
  일 때만 받고 root · anonymous 류는 거절, REST 관문(PatVerifier)도 auth=pat 만. dev — live 확인 셋 · backend 56 · MCP 352 통과. 못 봄 — 진짜 위임 PAT 로 그 사람 이름이
  나오는지(이 세션의 게이트웨이 PAT 도 만료라 71 도 실호출 못 함 — 새 토큰은 사용자 몫이라 만들지 않았다).
  운영 손 — **backend_5010 먼저, 그다음 smarttwin-mcp**(MCP 가 auth 칸을 요구해 backend 가 옛 판이면 MCP 호출이 전부 fail-closed). 위임 PAT 는 이제 admin 이 아니라 그
  사람 권한(role user · dashboard)으로 풀린다(MCP 가 부르는 submit · preview · rerun 은 dashboard 만 요구 — 안 막힘). 운영이 11-24 에 건 `grant_only plat:smarttwin-run`
  (요청서 MEMORY-2 — 되돌리기는 운영 배포 리포 README §8)은 이 판이 운영에 든 뒤 **위임 PAT 로 게이트웨이 `list_recent_jobs` 의 caller 가 사람 이름인지 본 다음** 푼다 —
  푸는 결정은 운영 쪽 사용자. SM-01 ~ 03 · 카탈로그는 진행 중, 전달 길(git · Drive 이름)은 c8 이 끝에 준다.

## R25-18 6차 편지함이 나갔다(11-25)

- 87 이 `docs/cae00-inbox/2026-11-26.md`(`4c84e2f5`, Q40 ~ Q50)를 올렸다. request-1125 몫 — StepForge `d7be049c` · KooRemapper(DynaForge) `6a90a416`(main 은 SP 서브모듈만
  올린 `488168ea`) · HEAXHub `38baee7`(0절 1 맨 앞에 `.pre-merge` 지움) · SignalForge `51ee09b` · MX 백서 `90f5d8d` · stcx KooSlurm `d93017a5`(코드 `89172f14` — SM-04 포함)
  · 게이트웨이 `63eed05`. MW-08 은 Q50, MW-09 는 「알고 받을 것」. R25-Q12 ~ Q16 은 머리말에서 다시 불렀다. 사용자에게 「cae00 업데이트를 돌려도 된다」 고 전했다.
- 남은 것 — DocForge 0.4.0 은 판이 오면 87 이 이 글 끝에 덧붙임 절로. SmartTwin MCP SM-01 ~ 03 · 카탈로그는 KooSlurm main 에 넣기 전에 71 에 알려 달라고 c8 에 다시
  전했다(글의 판 `d93017a5` 와 어긋나지 않게). ste · 브리지는 Q35 ste 교체 보고까지 묶음 그대로.

## R25-19 SmartTwin 답 — grant_only 셋은 SM-01 판까지 남긴다 · 6차 글 덧붙임 부탁(11-25)

- c8 답(기동 차례 물음 둘) — dashboard_backend = backend_5010 이 맞다(유닛 WorkingDirectory · 5010 · backend_5010/.env, `start_production.sh` 84 · 129 · 501행). backend 가
  못 뜨면 MCP 는 닫힌 쪽(`caller_identity` 의 `/api/me` 실패 → StmcError · REST PatVerifier 503).
- **예외 둘이 6차 글(5절 103행)을 바꾼다.**
  - 호출자를 보지 않는 읽기 도구(`catalog_*` · `list_slurm_partitions` 류)는 backend 없이도 답한다. 이것은 읽기라 문제는 아니다.
  - `d93017a5` 판에는 SM-01 이 없다. 그래서 `train_pytorch_gpu` · `submit_distributed_train` · `submit_lsdyna_remote`(1.1.0) 셋은 PAT 를 보지 않고 서비스 계정으로
    sbatch 를 낸다. 글의 「위임 PAT caller 가 사람 이름이면 푼다」 만 따르면 이 셋이 함께 열린다.
- 87 에 덧붙임 문안을 부탁했다. 「셋이 `plat:smarttwin-run` 안에 있으면 SM-01 판까지 grant_only 를 풀지 않는다. 셋을 따로 묶을 수 있을 때만 나머지를 푼다.」 그리고
  Q45 의 「풀었는지」 를 「셋을 어떻게 남겼는지」 로. 까닭 — `plat:smarttwin-run` 은 git 에 없고 cae00 박스 덧씌우기에서 정의한 것이라 셋만 따로 남길 수 있는지
  dev 에서 모른다(포털 · 게이트웨이 소스에 그 이름이 없다 — grep 0).
- 같이 부탁한 것 — 6차 글 97 · 106행의 「Pre v141 · Post v54 그대로」 는 리포 기대값이다. 운영 stcx 에 깔린 판은 Pre v128 · Post v50(SP-5 · Q34)이라
  `image_version_check` 에 v141 · v54 를 주면 「다르다」 가 나오는 게 맞다는 한 줄.
- c8 은 KooSlurm main push 를 멈췄다(그쪽 사용자 결정 — SM-01 ~ 03 · 카탈로그를 다 끝내고 한 판으로). 그때까지 가지 `feat/sm-security-1125` ·
  `feat/catalog-regen-1125` 에 두고, main push 전에 71 에 알린다. 6차 판 `d93017a5` 는 그대로 유효하다.
- 87 이 덧붙임을 올렸다(`4b82e8da`). 확인한 것 — 5절에 「SM-01 없음 · 셋은 SM-01 판까지 grant_only · 셋이 `plat:smarttwin-run` 안이면 통째로 둔다」(문안 그대로) ·
  나머지를 푸는 조건(위임 PAT caller)은 둘째 단계 · 리포 기대값 v141 · v54 와 운영 v128 · v50 을 갈라 적고 `image_version_check` 의 「다르다」 는 실패 아님 ·
  기동 차례의 「전부 막힌다」 를 「호출자를 보는 호출은 닫힌 쪽 — 예외 읽기 도구와 셋」 으로 · Q45 는 「어떻게 남겼는지」. KooSlurm main 이 움직이면 87 에 알린다.

## R25-20 DocForge 0.4.0 착지 — HEAXHub 판도 b4309c0 으로(11-25)

- docforge-f6 — 그쪽 사용자 승인(11-25)으로 dev 쪽 배치 끝. 원격 ls-remote 로 맞대 확인 — DocForge release `3a578a29`(배치 판) · main `6e6c10f8`(release 뒤 배치 기록 문서
  하나) · HEAXHub main `b4309c0`. Drive `latest/doc-forge.sif` · `.sif.hash` · 되돌리기 `dist-20261125-211307Z/` · SHA256SUMS 30줄. SIF 파일 sha256 `71aa8471…de65`
  (852M) · 허브 캐시 열쇠(.sif.hash 내용) `e06a0152…9932` — SHA256SUMS 의 .sif.hash 파일 sha256 `e160b915…3727` 은 셋째 숫자라 따로 적었다. DB 이관 없음.
- **HEAXHub 판이 6차 글의 `38baee7` 에서 `b4309c0` 으로 움직였다.** 그 위 커밋 하나(`integrations/doc-forge/.portal/manifest.yaml` — 등록 사본 0.4.0 · IR-24 줄 빼기, R25-11).
  운영 update-all 은 main 을 받으므로 글의 판 줄을 고쳐 달라고 87 에 함께 전했다.
- 운영 손일 — update-all 로 받기 · `/health` 0.4.0 · capabilities(max_jobs · vlm.thinking_off) · 11-10 시험 덱 일곱 줄. 고를 일 둘 — `DOCFORGE_MAX_JOBS`(knobs.env, 적어 둔 값이
  있으면 0.4.0 부터 그 값) · 판독을 심의 모델로 옮길 때만 `DOCFORGE_VLM_THINKING_OFF=0`. 운영이 알 것 ① ~ ⑥ · DFO-1 까닭은 앞서 넘긴 정리 그대로.
- DocForge 는 cae00 update-all 이 끝날 때까지 release 를 옮기지 않는다 — 끝나면 알린다.
- 덧붙임 — DocForge 원격 main 이 문서 커밋 하나로 `f4422e5e` 로 한 번 더 움직였다(ls-remote 확인). release 는 `3a578a29` 그대로라 운영이 받는 판은 바뀌지 않는다. 87 에 「글의 판은
  release 로 · main 해시를 적었으면 바꾸거나 빼기」 를 전했다.
- 87 이 올렸다(`0e91cace` — 6차 글 9절 · Q51). 확인 — 한눈에 표 HEAXHub `b4309c0` · DocForge 는 release `3a578a29` 만(main 해시 뺌) · 파일 sha256 과 캐시 열쇠를 이름 붙여 ·
  머리말에 「HEAXHub 판도 바뀌었다」 한 줄. 이로써 6차 글에 request-1125 몫이 다 실렸다 — 남은 것은 ste · 브리지(Q35 교체 보고 뒤) · SmartTwin SM-01 ~ 03(다음 판).

## R25-21 6차 운영 답(일부) — 몫별로 나눔(11-26)

- 사용자가 붙여 넣은 운영 답(11-26 KST). Q40 ~ 44 · 46 · 47 · 51 은 「update-all 뒤 채움」, Q49 는 11-30. update-all 은 15:13 에 걸었으나 남의 심의 하나가 14:40 뒤로
  멈춰 일 없음 기다림(3시간)이 안 비었고, 그쪽 사용자 결정으로 18:34 에 접은 뒤 18:47 에 다시 걸었다(N26-1 — 에이전트 서버 몫이라 87 에 넘김).
- **Q45 → c8.** KooSlurm `d93017a5` 반영(15:35 ~ 15:38). 헤드 사본은 다른 계정 소유 · 헤드에서 git ssh 막힘 → 포털 박스의 git bundle 로 fast-forward(`b6a3d75` → `d93017a5`,
  22커밋). smarttwin-mcp 유닛은 운영 배포 리포 판 폴더에서 돌아 `start_production.sh` 는 재기동만 한다 — MCP 코드는 배포 리포 판 길(build → push → stage → swap)로 따로.
  차례는 backend 15:36:02 → MCP 15:38:01, `/api/me` auth 칸 확인. 결함 하나 — `catalog_run image_version_check` 가 얇은 배포 사본에서 스크립트를 못 찾는다(c8 몫).
  헤드 사본에서 직접 돌려 DIFF 9 · ERR 0. **바로잡음 — 깔린 판은 Pre v128 · Post v53**(SP-5 · 6차 글의 「Post v50」 은 틀림, NFS `.version` 11-23 20:55 바뀜).
  대기 꾸러미는 Pre v141 맞음 · Post · Post GUI 는 v54 아님(Post 대기본 = 깔린 v53) → 두 SIF 를 다시 받아야 함 — Drive 위치 · 누구 몫인지 c8 에 물었다.
  grant_only 는 `plat:smarttwin-run` 이 백엔드 전체를 묶는 한 항목이라 통째로 유지(SM-01 판까지). `images{}` · 위임 PAT caller 는 못 봄.
- **Q48 → ste-06 · 브리지.** 자동 교체 아직 — 11-23 기다리개가 11-26 00:08 기한에 멈춤(ste 잡 22 ~ 27), 새 기다리개 기한 11-30 23:59. 라이선스 서버 줄 안 넣음 →
  `0313ceb` 계속 보류 · ste 로컬 34커밋 · 브리지 SIF `e52a03a` 계속 묶음.
- **Q50 · R25-Q5 → MXWP.** restricted 두 장 모두 시드(owner = 시드 관리자 · change_log `seed` · slug 골든 06 · 08) → 운영 사용자 결정 「보관」, 실행 결과는 채울 것.
- **R25-Q12 ~ Q16 → StepForge.** ST-27 표본은 운영 노드 StepForge 인스턴스에서(포털 박스 사본은 동결 · 인스턴스 0), 표본 JSON 은 사람 몫 · /data 밖으로 안 옮김.
  ST-25 재료 — `kind_parent`(부모 part key · 100개 · 깊이 3) · 집합의 갈래는 아래 부품의 kind_parent 가 집합 key 를 가리키는 꼴 · 같은 꼴 위 칸 `whole`(구성 상위 · 51개) ·
  별칭은 `properties.aliases`(189/224 · 1,111) · 잡음 낱말은 스크립트 안 `strip_noise`(요청서의 `part_id_rule.yaml` 인용은 틀림) · 재현 규칙(name_match · head_match ·
  붙인 글자 수 대 낱말 수). **바로잡음 — conflict 는 셌다**: 이름+역할 함께 10,655 중 다름 · 위아래 아님 5,240(6.9%) → ST-25 꼴 51,518(68.3%). 역할 대응이 그 뒤 바뀌어
  StepForge 가 지은 뒤 같은 꼴로 다시 세는 것이 맞다. 이로써 ST-25 짓기 전 물음 넷이 다 풀렸다 — 지으면 블록 바이트 · sha 를 KooRemapper 에 직접(R25-13).
- 다음 편지함에 고쳐 실을 것(87 에 전함) — SM 판 안내에 배포 리포 판 길 · git bundle · Post v53 바로잡음 · ST-27 명령은 운영 노드에서.
- MX 백서 답(MW-08 보관) — 코드 고칠 것 없음. main 이 문서만 `7dfb637` 로(90f5d8d 위 `docs/llm-wiki/context-notes.md` 하나, ls-remote 확인). 6차 글 191행 「지운 것은 seed 가
  다시 돌면 되살아난다」 는 범위가 넓었다 — MX 백서의 지우기가 곧 보관이고 slug 가 조건 없는 UNIQUE 라 seed 는 겹친 행의 제목 · 요약 · 본문만 고치고 상태를 둔다. 다시 생기는
  것은 관리자 「보관 문서」 에서 영구 삭제한 뒤 seed 가 돌 때뿐. 87 에 판(`7dfb637`) · 문장 고침 · 보관하는 길 · 실행 결과로 볼 것(archived · published restricted 0장)을 넘겼다.

## R25-22 6차 운영 답(둘째 — 빈칸 채움) — 몫별로 나눔(11-26)

운영이 앞 답의 「채울 것」 칸만 모아 보냈다(사용자가 붙여 넣음). 받을 세션마다 나눠 보냈다. ste · 브리지는 바뀐 것이 없어 보내지 않았다.

- **Q40 · Q41 · Q42 · Q46 · Q48 → 87.**
  - update-all 끝 코드 0, 19:52:57 KST(둘째 시도). ✗ 0 · ○ 2. 「있는데 안 켠 것」 15줄에 새 줄 둘(상호작용 기록 두 스위치)이 기대대로 나왔다.
  - HEAXHub `.pre-merge` 348개 · 10,396 MiB 를 같은 /data 안 백업으로 옮겼다(지운 것 0). 리포 8개 HEAD 가 기대값과 같다. 게이트웨이 백엔드 35 · 도구 1,984.
  - kr_ PAT 건너뜀 줄은 없었다. provision.env 의 KOORM_BASE 로 재는 쪽으로 갔지만, 성공 여부는 로그에 없다.
  - 재료 카드 `0|0|2893` 으로 dev 와 같다.
  - 리스크 단위 측정이 0 인 까닭은 단위 빌드가 0 이라서다. 다시 재야 한다. 절차서의 `~/Projects/HWAXRisk` 경로가 운영 박스에 없다.
- **Q50 → MXWP · 87.**
  - 보관 완료(20:16, published 336 → 334).
  - 운영은 6차 글 191행을 믿고 「seed 를 다시 돌리면 되살아날 수 있다」고 적었다. 87 이 아직 191행과 판 줄을 고치지 않았다(origin/main 확인). 다음 편지함에 바로잡기를 다시 부탁했다.
- **Q51 → DocForge.**
  - 0.4.0 운영 확인. 시험 덱 일곱 줄 모두 맞음(판독 17/17). release 고정을 풀어도 된다고 알렸다.
  - 판독 품질 참고 둘(같은 그림의 두 판독이 다를 때 캡션이 따를 쪽 · 오탈자)도 함께 보냈다.
  - 첫 실행 실패는 운영 챗 LLM 복제 10자리 중 9자리가 11-20 에 실행 한도(30일)로 끝나 있던 탓이었다. 운영이 60일로 늘렸다. 87 에 chat-llm-stcx 안내를 손볼지 물었다.
- **Q43 → StepForge.** d7be049c 반입(20:23 ~ 20:24), mcp_tools 207, edge_groups 넷이 다 보인다. 레지스트리 part 의미 바꾸기는 여전히 새 브리지 SIF 뒤다.
- **Q44 → KooRemapper.**
  - 6a90a41 반입, 확인 넷 맞음.
  - 레시피 내보내기의 마지막 자리가 읽기 전용 묶음 안이었다. 운영이 `KOORM_RECIPE_EXPORT_DIR` 을 storage 아래로 주어 고쳤다. dev 에는 마지막 자리를 storage 아래로 두라는 제안이 왔다.
  - 재기동 때 올리던 파일 1건이 끊겼다.
- **Q45 → c8.**
  - images{} 는 아직 못 봤다. 템플릿 잡이 없었고(152개 모두 직접 낸 잡), 운영이 부분 충격 템플릿 잡을 내는 중이다.
  - 그 과정에서 대시보드 백엔드가 업로드 공유 폴더를 못 만들면 /tmp 로 조용히 물러나는 결함이 나왔다. 6월 실행 계정이 바뀐 뒤 파일을 같이 올리는 제출이 모두 막혔던 것으로 보인다. 운영이 22:31 에 폴더를 만들어 고쳤고, 기동 때 실패로 알리라는 제안이 왔다.
- **Q47 → SignalForge.** 모두 통과(sf-mcp 다시 뜸 · 2절 · 3절 여섯 호출).

## R25-23 착지 · 답 묶음 — KooRemapper 셋 · StepForge ST-25 지음 · DocForge · SignalForge(11-26)

- **KooRemapper(git pull 만, Drive 그대로 dist-20261125-161932Z) — 87 에 넘김.**
  - 804a7acb: 레시피 마지막 자리 storage/.recipes. Q44 운영 제안 그대로다.
  - 664a2f28 · b931c275(§1-16): 진행 중 올리기를 기다리는 재기동. `uploads_in_flight` · `KOORM_UPLOAD_DRAIN_S` 300 · `KOORM_STOP_WAIT_S` 60 · 넘으면 rc 1 로 멈춘다. 그쪽 사용자 결정 11-26 「수를 보이고 재기동이 기다린다」.
  - 포털 `_stop` 이 rc 를 삼키면 이 멈춤이 안 보인다. 87 가지 wt1126/koorm-stop-rc(566f72f6)와 함께 싣도록 부탁했다.
  - ST-25-KR 4f8f73ec · e24ea649(§1-17). 블록 지문 8cc5a705…dc171 은 StepForge origin 블록에서 다시 재서 같았다.
  - 허브 관리자 몫: 두 블록이 같은 바이트여야 하고, part_role · cae_part · cad_part · part 를 모두 코어 공개로 둔다(SP _open_end).
- **StepForge ST-25** — feat-1125 6eb72bd6 으로 지었다(push 뒤 d7be049c..b7e937b6). 착지 값은 그쪽이 곧 준다. KooRemapper 와 같은 회차여야 한다.
  - 「basis role → role+name」 경고는 포털 · 게이트웨이 · 에이전트 서버에 읽는 곳이 없음을 확인했다(grep 0).
- **DocForge** — release 를 옮기지 않는다(3a578a29 뒤가 문서 커밋뿐). 판독 품질 참고 둘은 그쪽 체크리스트의 열린 줄로 뒀다.
- **SignalForge 권고(선택)** — 박스 어휘표에 search_voc 다음 호출 줄을 넣는다면 core_type/core_key 나 strict=true 꼴로. 87 에 넘겼다.
- 같은 묶음으로 87 에 넘긴 것: 심의 보고서 RA 제출 표준(docs/ra-delib-standard — 포털 05fa692e · 게이트웨이 c27a2f9, 사람 몫 server-setup) · 포털 RA 링크 접두(ac2cb88d) · 첫 화면 RA 부서 카드(7125a146) · MX 백서 191행 고침(다시).

## R25-24 StepForge ST-25 착지 · 이번 회차를 막는 것(11-26)

- **StepForge ST-25 착지 — 87 에 넘김.** main 71982cb4(코드 71a01206) · Drive `dist-20261126-215721Z`(latest/ 도) · DB 이행 없음 · 앞 판 d7be049c 로 되돌려도 된다.
  - SIF 수 둘(파일 sha256 c5921730… · 허브 .sif.hash c2627348…)은 개발 박스 · Drive 판 · latest 셋이 같다고 그쪽이 확인했다.
  - 운영 손 할 일은 KooRemapper §1-17 과 같은 둘(허브가 두 블록을 같은 바이트로 · 코어 공개 넷)뿐이다.
  - 허브 블록 가져오기는 StepForge 새 SIF 가 든 뒤에 두 앱을 같이 한다. KooRemapper 는 git pull 로 먼저 새 블록이 되기 때문이다.
- **dev 반영** — 사용자 승인(11-26)으로 포털 · 게이트웨이를 다시 띄웠다. 켜진 것은 RA 변경(ac2cb88d · 7125a146 · 05fa692e · c27a2f9)뿐이다.
- **cae00 업데이트 판단(사용자 물음 11-26)** — 남은 것은 87 의 이번 회차 편지함 하나다(마지막 글 0e91cace — RA 제출 표준 · KooRemapper §1-16 · §1-17 · ST-25 · MX 191행 고침 · MX 판 56bfc2c 가 아직 없다).
  - 포털 · 게이트웨이 몫만이면 지금 받아도 동작이 같다(박스 파일에 게시판이 없으면 게시 단추가 숨는다).
  - MX 백서 판 정정(7dfb637 → 56bfc2c, 문서 커밋 둘)도 87 에 넘겼다.

## R25-25 운영 둘째 답의 Q45 덧붙임 2 — 계산 노드에 공유 볼륨이 없다(11-27)

- 운영 둘째 답(R25-22 로 이미 몫별로 나눔)에 11-27 07:05 KST 덧붙임이 더해졌다. images{} 는 여전히 못 봄이다.
- 다시 낸 템플릿 잡이 시작하자마자 실패했다. 계산 클러스터 공유 볼륨이 헤드에만 있고 계산 노드 355대에는 없다. 그동안 348대는 같은 이름의 빈 폴더로 버텼고, 8대에는 그 폴더도 없었다.
  - 운영이 8대에 폴더를 만들어 시작 직후 실패는 풀었다.
  - 업로드 입력을 계산 노드가 잡 시작 때 복사하지 못하는 문제는 남았다(운영이 코드로 판단, 실측 아님). 잡 로그도 노드 디스크에만 남는다.
- 운영이 요청서 `cluster-shared-folder-request-20261127.md`(SH-01 ~ 06)를 따로 준다. 앞의 「기동 때 실패로 알리기」 제안은 SH-04 에 합쳐졌다. 원문은 아직 안 왔다.
- SmartTwin MCP(c8)와 87 에 넘겼다. 자동 파이프라인의 전각도 낙하도 이 문제에 걸린다(docs/auto-pipeline AP-7).

## R25-26 공유 폴더 요청서 SH-01 ~ 06 원문 — KooSlurm 에(11-27)

- 사용자가 운영 요청서 원문을 붙여 주었다. 사본은 `cluster-shared-folder-request-20261127.md`.
- 코드 줄(job_submit_api.py 125 · 127 · 150–159 · 644)을 KooSlurm main d93017a5 와 맞대 같았다.
- SH-04 를 이미 받은 SmartTwin MCP 세션(c8)에 원문 그대로 넘겼다. 착지 값(커밋 · icn401 반영 · 운영 손 할 일 — 새 환경값 둘 · /data 아래 폴더 소유)을 청했다. KooSlurm main push 전에 알리라는 SM-01 규칙 그대로.
- 자동 파이프라인의 전각도 낙하 실주행도 SH-01 · 02 뒤다(docs/auto-pipeline AP-7).

## R25-27 ste GitHub main 올림 — Drive 는 그대로(11-27)

- ste 세션(smarttwinexplorer-06)이 그쪽 사용자 지시로 GitHub main 을 859a02d → 47101d9 로 올렸다(35 커밋 · 빨리감기). 원격 가지 둘(registry-part-fetch b4503ec · lsdyna-license-default-removal 0313ceb)은 main 에 합치지 않았다.
- Drive staging 은 859a02db7d93 그대로라 cae00 기다리개의 꾸러미 · 11-23 글 6절 · 6-1 → 6-2 절차는 영향이 없다. cae00 의 .deployed-commit 이 859a02d 면 GitHub main 의 조상이라 추적도 맞다.
- 라이선스 가지는 cae00 의 `STE_LSTC_LICENSE_SERVER` 줄이 들어오기 전까지 합치지 않는 것 그대로. 다음 Drive(ste · CalculiX)는 교체 보고(기한 11-30) 뒤 그쪽 사용자에게 묻고 한다. 87 에 알렸다.
