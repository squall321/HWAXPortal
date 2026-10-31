# 클러스터 배선 — 체크리스트

> 계획은 `PLAN.md`, 판단 근거는 `context-notes.md`. **dev 검증 / 실박스 검증**을 항목마다 갈라 적는다.

## 0. 전제 확인 (구현 전에 닫아야 하는 것)

- [x] **:5013 정본** — **KooSlurm**(`KooSlurmInstallAutomationRefactory/dashboard/smarttwin_mcp`). `~/claude/SmartTwinMCP` 는 고치지 않는다
- [x] **같은 경로가 양쪽에서 보인다**(사용자 확정) → ③ 은 경로 잇기
- [x] 착지 경로 **실값** 확인 (실박스) — 다만 코드는 경로를 박지 않으므로 실값과 무관하게 성립해야 한다 — 걷음: 덱을 stcx 대시보드 청크 업로드로 나른다(KooRemapper `92cb157` — '같은 경로' 전제가 실측으로 깨졌다, 56줄 10-17 정정 · D-6) · SmartTwinExplorer 에 ste 잡 폴더를 stcx 로 넘기는 코드 0 — 착지 실값은 ste 자체 운영에만 뜻이 있다 (10-31 정리)
- [x] 권한 — stcx 쪽 실행 계정이 ste 잡 폴더를 읽을 수 있나 (실박스, 추측 말고 시도) — 걷음: stcx 실행 계정이 ste 잡 폴더를 읽을 일이 없다(KooRemapper `92cb157` — 덱을 업로드로 나른다, 9줄과 같은 까닭) (10-31 정리)
- [x] 권한 — ste 계정이 만든 잡 디렉터리를 stcx 계정이 읽고/쓸 수 있는가 (실박스) — 걷음: stcx 계정이 ste 잡 디렉터리를 읽고 쓸 흐름이 없다(9줄과 같은 까닭) (10-31 정리)
- [x] ste 의 결과 보관 만료가 그 디렉터리를 지워 버리지 않는가 — **지운다**(10-17 코드 확인 — 끝난 잡을 동기화 뒤 7일 · 미동기화 제출 30일, D-6). 헤드 `.env` 값은 실박스에서
- [x] ~~DynaForge 컨테이너에 ssh/scp/rsync 가 있는가, ssh 별칭이 닿는가~~ — 버림(10-17 — ㉮ 길 선택(게이트웨이 MCP 재사용)으로 대체 — 덱은 이제 HTTP 로 올려 컨테이너에 ssh 가 필요 없다(KooRemapper 92cb157))
- [x] ~~ste 헤드노드에서 포털 JWKS 를 얻을 수 있는가 (에어갭)~~ — 버림(10-17 — ㉰ 공유 비밀 + HMAC 으로 대체 — JWT/JWKS 를 안 써서 에어갭 JWKS 문제가 사라졌다(이 체크리스트 ㉰))

## ① 표기 규율 — ste / stcx  ✅

- [x] 세 리포 전수 정정 (코드 주석·앱 정의·런북·계획서·사용자 노출 문구). **값은 안 건드렸다**
- [x] 가드 `backend/tests/test_cluster_naming.py` — 세 리포 가로지르기, 현재 위반 **0**
- [x] 면제 셋(접속 별칭·잡 ID 접두사·기록 파일)과 **면제가 실제로 걸리는지**까지 시험
- [x] 정본 선언 — 포털 CLAUDE.md, ste CLAUDE.md(신규), SmartTwinMCP CLAUDE.md
- [x] 파일 이름(`ste-stcx.conf.snippet`)은 **안 건드렸다** — stcx 호스트를 가리키는 것이 맞다

## ② ste 업로드 스트리밍화  ✅

- [x] 상한을 **읽기 전에** 본다(seek 으로 크기만 잰다 — 바이트를 한 개도 안 읽는다)
- [x] `jobs.create` 가 스풀 파일에서 디스크로 청크 복사(`_write_input`). 바이트 호출부도 그대로 받는다
- [x] 시험 6 — 통째 읽기를 시도하면 폭발하는 파일 객체 + `await f.read()` 재유입 가드
- [ ] 두 앞단 모두에 `client_max_body_size` + `proxy_request_buffering off` 확인(실박스)

## ③ stcx 반입 자동화

- [x] 공유 NFS 가 확인되면 — ste 잡 디렉터리 경로를 `work_dir` 로 잇는다 (전송 계층 없음) — 걷음: 같은 경로 전제가 사실이 아니어서 덱을 나른다(KooRemapper `92cb157` · 56줄 10-17 정정) — 반입은 34줄 길로 정해졌다 (10-31 정리)
- [x] 확인 안 되면 — 반입 수단을 정하고 그 경로만 자동화한다 — 풀림 KooRemapper `92cb157` — 반입 수단 = stcx 대시보드 청크 업로드(platform/backend/app/runner/stcx_client.py:669 StcxUploader), work_dir 은 잡마다 고유(worker/runner_loop.py:343-347) (10-31 정리)
- [x] 시험 — 경로 규약이 코드로 못 박히고, 어긋나면 **조용히가 아니라 명시적으로** 실패한다 — 풀림 KooRemapper platform/backend/tests/test_external_submit_poll.py:332 · :319 · :377 · :401 · stcx_client.py:731 · :837 — 어긋나면 그 자리에서 명시적으로 실패한다(`92cb157`) (10-31 정리)

## ④ cae00→stcx ssh 왕복

- [x] 실패 모드 분리 — 호스트 없음 / 인증서 만료 / 비0 종료 / 타임아웃이 반환값에서 구분된다 — 걷음: ㉮ 길이 게이트웨이 MCP(HTTP) 재사용이라(46줄) 낙하 경로에 ssh 홉이 없다 — HTTP 길의 실패 갈래는 KooRemapper stcx_client.py:544-614 와 게이트웨이 시한 문구가 가른다 (10-31 정리)
- [x] 낙하 시뮬 계열의 **별도 ssh 경로**가 코드 어디인지 확정 (없으면 그것이 결손) — 풀림 따로 된 ssh 경로는 없다 — :5013 정본 매니페스트가 transport local 이고 ssh 도구는 submit_lsdyna_remote 하나 · DynaForge 는 게이트웨이 MCP 로 낙하 도구를 부른다(KooRemapper stcx_client.py:42-43, `92cb157`) (10-31 정리)
- [x] 게이트웨이 타임아웃보다 오래 걸리는 명령의 처리 규약 — 풀림 KooRemapper stcx_client.py:35-37(클라이언트 시한 60초 < 게이트웨이 600초) · 제출 → 번호 → 지수 백오프 폴링(tests/test_external_submit_poll.py:555) · 제출 시간 초과는 재제출 없이 회수(worker/runner_loop.py:435-453) (10-31 정리)
- [x] 시험 — 가짜 ssh 하네스로 네 갈래 (dev 검증 가능) — 걷음: ssh 홉이 없어(39줄) 가짜 ssh 하네스의 대상이 없다 — HTTP 길은 가짜 MCP 시험이 덮는다(KooRemapper tests/test_external_submit_poll.py:450 · :469 · :401) (10-31 정리)

## ㉮ stcx 잡 → DynaForge 작업 옵션  *(브랜치 `feat/external-jobs-stcx`)*

- [x] 길 선택 — **게이트웨이 MCP 재사용**. 직접 ssh 는 SIF 재빌드·바인드 확장·시나리오 32KB 중복 구현이 들고, DynaForge 가 클러스터 자격증명을 쥐게 된다
- [x] 외부 잡 스파인 — 칸 셋 + 마이그레이션 0007. 고아 회수·세션 직렬화에서 외부 잡 제외(각각 변이로 확인)
- [x] 게이트웨이 MCP 클라이언트 — 접두사 별칭, `dry_run=False` 명시, 시한 60초(게이트웨이 120초 아래)
- [x] 응답 해석 — 이 도구들은 **글**을 돌려주고 실패도 성공 모양으로 온다. 못 읽으면 실패, 모르면 모름(변이로 확인)
- [x] 카탈로그 `stcx_fullangle_drop` + `invocation: "external"` 계약과 그 불변식
- [x] 제출·폴링(지수 백오프, 시간 기준 스캔)
- [x] 각도 프리셋 live 조회 `GET /api/v1/stcx/options`
- [x] **시나리오·옵션 전면** — 파라미터 18개(각도 5갈래·물리 5·연속·자원 4·`scenario_overrides` 탈출구). 폼은 카탈로그에서 자동 생성
- [x] **우선순위** — 프리셋 → 낱낱 옵션 → `scenario_overrides` 가 마지막에 이긴다. 병합 규칙을 서버 도구와 같게 맞췄다
- [x] **각도 파일**(`case_txt`) — 나르지 않고 세션 경로를 넘긴다. 파일 선택이 곧 각도원 선택
      → (10-17 정정) 지금은 다르다 — KooRemapper `92cb157`(10-14)부터 덱을 **나른다**(cae00 /data 와 stcx /data 가 다른 디스크라 세션 경로를 못 연다). `case_txt` · 프리셋 · `scenario_overrides` 같은 각도 방식 옵션은 그 판의 러너가 '다음 판' 이라며 거절하고(runner_loop.py `STCX_SUPPORTED`), 응답도 글이 아니라 JSON 봉투다 — 위의 응답 해석 · 프리셋 · 시나리오 · 우선순위 · 드롭다운 줄도 그 전 판의 기록이다
- [x] 프리셋 드롭다운 — **서버에 물어서** 채운다. 못 물어본 경우와 없는 경우를 가려 보여 주고, 직접 적을 길도 남긴다
- [x] ~~산출물 되먹임 — 결과는 클러스터에 있다. 어디까지 가져올지 결정 필요~~ — 닫음(10-17 — 사용자: 결과 위치만 잡 기록에 남기기로 10-15 에 정해 반영했고 자동 회수는 다음 판 — 남은 것은 결정이 아니라 클러스터 쪽 선행 작업이다)
- [ ] **잡 소유자** — 게이트웨이가 smart-twin 계열에 신원을 전달하지 않는다. 지금은 PAT 주인 한 명에게 귀속된다

## ㉯ ste → MCP → 포털  (배선 완료, 반영은 재기동)

- [x] ste MCP 서버는 **이미 있었다** — :15812, 도구 8종(전부 PAT 소유자 기준). 실호출로 확인
- [x] 프로비저너에 `ste` 백엔드 + dev `gateway_config.json` 등록
- [x] `access.yaml` 의 smarttwin 허가에 `ste` (붙이기 **전에** 적었다 — 정책 없는 백엔드는 전체 공개다)
- [x] **정적 백엔드도 사용자 위임에 들어가게** 게이트웨이 수정(`_delegation_app_id`) + 시험 4
- [x] 게이트웨이 재기동 후 `tools/list` 에 뜨는지 실호출 확인 (`/refresh` 는 정적 백엔드를 다시 안 읽는다) (확인 10-17 — dev — ste-cae00 체크리스트 S3 게이트웨이 실호출(ste_prepare_upload 포함, D-15) · S5, cae00 — ste-cae00 D-30)

## ㉰ 포털 로그인 → ste 계정·PAT 자동 연결  ✅

- [x] **발급은 ste, 보관은 아무도 안 한다** — 포털은 중계만(DB 에 안 쌓는다), 브라우저가 유일한 사본
- [x] 승인제는 **자리를 옮겼다** — 포털 `visible_systems`(plat:smarttwin)가 판정. 비밀번호 가입의 승인제는 그대로
- [x] "SSO 리다이렉트 없이 401" 과 **충돌하지 않는다** — nginx 를 안 건드리고 서버 간 토큰 교환만 한다
- [x] **에어갭 JWKS 문제가 사라졌다** — JWT 대신 공유 시크릿 + hmac. 새 wheel 0개
- [x] 통로별 PAT 이름(`portal:<메일>:<클라이언트>`) — 게이트웨이 발급이 브라우저 토큰을 죽이던 결함 수정
- [x] 로그아웃이 **서버 원장과 브라우저 사본을 둘 다** 끊는다
- [x] 시험 — ste 18 + 포털 12. 인가 가드는 **변이로** 확인(그 줄을 지우면 그 시험만 깨진다)
- [x] 실박스 — cae00 과 ste 헤드노드에 **같은** `STE_SSO_SECRET` 설정 — 풀림 10-30 cae00 QA 에서 ste 도구가 SSO 사용자 명의로 답했다(docs/request_261030.md:60 PA-20 · DW-12) — 위임은 이 비밀로만 선다(HWAXMcpGateway provision-config.sh:729-741 · ste MCP 서비스 토큰 폴백 없음) (10-31 정리)

## 반영에 필요한 재기동 (놓치면 "고쳤는데 안 바뀐다")

- [x] **DynaForge API** — 작업 카탈로그는 `@lru_cache` 라 기동 때 한 번 읽는다. 재기동 전에는 새 작업이 목록에 안 뜬다 — 풀림 dev DynaForge /api/health revision `24bca1c`(2026-10-30) — 카탈로그 항목(`2f84b31`) 뒤 API 가 여러 번 다시 떴다 · cae00 은 update-all 이 Drive 판이 바뀔 때 다시 띄운다(cae00-deploy-guide 2026-10-30 낙하 트윈 §1) (10-31 정리)
- [x] **게이트웨이** — 정적 백엔드(ste)는 `/refresh` 로 안 붙는다 (확인 10-17 — dev 재기동 3ba4bb1(394종), cae00 — ste 도구 호출이 게이트웨이를 지나 헤드의 ste MCP 에 닿았다(ste-cae00 D-30))
- [x] **ste 백엔드** — 인증 변경(`/api/auth/sso`) 반영. **2026-09-23 실측: 아직 안 됐다.**
      `http://<헤드노드>:15810/openapi.json` 에 sso 경로가 0건이고 시크릿을 맞게 줘도 401 이다
      (인증 미들웨어가 공개 경로로 모른다). 코드는 `c7e3411` 로 원격에 올라가 있으니 남은 것은
      **헤드노드 배포**뿐이다 — `deploy/refresh-code.sh` 를 **cae00 에서** 돌린다.
      그때까지 ste 는 게이트웨이 MCP 위임과 REST 다리가 **둘 다** 실패한다(서비스 계정으로
      조용히 강등하지 않으므로 사유가 보인다). 자세한 실측은 `docs/one-token/context-notes.md` D-12 — 풀림 10-30 cae00 QA 에서 ste 도구가 사람 명의로 성공했다(docs/request_261030.md:60 · request-1030/platforms/14-Partner-apps.md:29) — 게이트웨이는 사람 PAT 를 헤드 /api/auth/sso 에서만 받는다(SmartTwinExplorer `3c3ce91`) (10-31 정리)
- [x] 프론트 빌드 — 포털 `pnpm build`, DynaForge `npm run build` 둘 다 완료(둘 다 `dist` 를 바인드로 낸다)

## 사용자 몫 (실박스)

- [x] cae00 에서 `routes.local.env` 의 `ste=` 가 ste 헤드노드를 가리키는지 확인 (확인 10-17 — ste-cae00 context-notes §F(09-27) — 라우트 ste= 가 헤드로 가는 teleport 로컬 터널을 가리키고 터널 경유 웹이 200)
- [x] ste·stcx 공유 NFS·권한 실측 — 걷음: 공유 NFS · 권한을 쓰는 흐름이 없다(KooRemapper `92cb157` — 덱을 나른다, 9 · 10 · 11줄과 같은 까닭) (10-31 정리)
- [ ] 실주행 E2E — 파일 업로드부터 stcx 낙하 결과 회수까지
