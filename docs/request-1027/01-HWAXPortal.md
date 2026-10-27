# HWAXPortal — 수정 요청 (2026-10-27 · cae00 운영 기준)


요청 HWAX Portal 운영(cae00) · 대상 저장소 HWAXPortal(`infra/scripts` 의 update-all.sh · deploy-all-from-drive.sh · start.sh · update-sites.sh · services.py · gen-nginx-conf.sh · backup-local.sh · check-egress.sh, `infra/personas` · `sync-he-personas.py`, `backend/app/agent` 업로드 · 라우트, `frontend/src/components/chat`, `docs`) · 기준 판 cae00 `f6c3c71`(10-25 피드백 · nginx STE · 온톨로지 시험 · 10-27 재확인) · `e00338b`(update-all 안전) · `dba4c1e`(PPT) · `90147ac`(지식카드 · 파트너 타일) · `2e514e3`(FMEA 연결) · `70f9e5e`(10-17 수정 목록) · 10-16 origin/main(MCP 업로드) · update-all 로 받는 플랫폼: 예.


줄 번호는 각 행에 적은 기준 판의 것이다. 「10-27 재확인」은 cae00 `f6c3c71`(작업 트리 깨끗)을 읽기만 해서 본 결과다. 항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것은 '-' 를 넣어 적었다(예 PPT A-8 · nginx STE S-1 · 10-17 수정 목록 P-7 · 10-25 시험 M-5 · MCP 업로드 M-2). 자세한 근거는 출처 칸이 가리키는 원문 절에 있다.


**한 줄**


- 챗에서 Report Archive 로 보낸 큰 파일이 다 올라간 뒤 「변환 실패(HTTP 400).」 하나로 끝난다. 까닭은 화면에도 감사에도 남지 않는다(HP-02 · HP-03).


- 운영 박스 KooRemapper DB 의 크론 백업이 10-02 부터 매일 실패한다. 배포 재기동과 1분 감시가 겹쳐 PG 가 내려간 일도 있다(HP-01 · HP-04).


- 사람이 등록한 외부 토큰이 평문으로 저장되고, 포털 sqlite 4개가 아직 644 다(HP-05).


- update-all 이 거짓 종료코드 1 을 내고(도구 지도 150 KB 를 환경 변수로 넘긴다), TOOL_MAX 를 '전량 바인딩' 이라며 덮지만 실제로는 1,613개 중 225개만 묶인다(HP-06 · HP-07).


- nginx 를 다시 만들 때마다 `/ste/` 가 600s 로 돌아가고 `/simflow/` · `/stcx-llm/` 갈래가 없다. 한 변경으로 고친다(HP-12 · HP-13).


**건수**


| 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|
| 5 | 16 | 22 | 4 | 3 |


## 1. 높음 — 먼저 고칠 것


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HP-01 | **update-all** — deploy-all 이 KooRemapper 를 내렸다 올리는 사이에 1분 감시 cron 이 start.sh 를 겹쳐 돌린다. | 기준 `e00338b` · `infra/scripts/deploy-all-from-drive.sh:457-463`(stop.sh → start.sh → install-autostart.sh). 10-27 재확인 — `f6c3c71` 에서는 `:484` `hwax_restart_cycle kooremapper` 이고 표지는 없다. 10-09 01:22 에 `instance koorm_postgres already exists`(rc=255)가 났고 postgres 없는 appinit 셸이 남았다. 10-17 에 그 같은 이름의 빈 셸을 치우는 사이 감시가 겹쳐 띄워 KooRemapper PG 가 약 18시간 멈췄다(10-18 제안 §5 · 운영 기록). | stop 전에 표지(예 `$DATA_DIR/deploy.lock.d` 에 PID)를 만들고 start 뒤 trap 으로 지운다(실패해도 지운다). 감시가 그 표지를 보고 건너뛰는 몫은 04-KooRemapper-DynaForge.md 다. | update-all 안전 U1-2 |
| HP-02 | **챗 업로드 · RA 보내기** — 'Report Archive 로' 목적지가 크기 한도를 미리 알리지 않고, RA 가 밝힌 거절 사유를 화면에서 버린다. | 기준 `f6c3c71` · `backend/app/agent/upload.py:55-60`(DESTINATIONS['reportarchive'] 에 크기 칸이 없다) · `:243` 주석 「앱 하드 크기 상한은 두지 않는다 — nginx 2GB」 · `routes.py:1390`(「변환 실패(HTTP n).」 와 detail) · `DocDispatchPanel.tsx:134-138`(error 와 detail.warnings 만 그린다). PPT 기준 `dba4c1e` 에서는 `routes.py:1307-1311` 이다. 10-23 에 116쪽 · 45 MB 가 400 이었다. 26.2 MB 는 통과하고 27.5 MB 는 거절되며 RA 답은 「파일이 너무 큽니다.」 다. | 패널이 RA `detail` 의 message · code 를 그대로 보인다. 크기 · 쪽 수 까닭이면 「사진 압축 · 나눠 보내기 · AI 데이터 허브로 보내기」 를 함께 안내한다. DESTINATIONS 에 `max_bytes`(기본 25 MB)를 두고 목적지 응답에 실어 UploadRouter 가 미리 막는다. RA 갈래에서 크기를 넘으면 RA 를 부르지 않고 413 과 사유를 돌려준다. 정확한 값은 RA 회신 뒤에 정한다. | 10-25 피드백 PT-2 · PPT A-8 · A-10 — 높음(PPT 1순위) |
| HP-03 | **챗 업로드 · RA 보내기** — 보내기 실패가 감사 · 서버 로그 · 대화 어디에도 남지 않는다. | PPT 기준 `dba4c1e` · `routes.py` 보내기 실패 길 · `_dispatch_audited`. 10-27 재확인 — `f6c3c71` `routes.py:1305-1316` 은 예외일 때만 `status="failed"` 를 적는다. RA 400 처럼 `{"stage":"failed"}` 를 돌려주는 길(`:1390`)은 200 으로 끝나 감사에 `upload_stage` 두 줄만 남는다. | 실패도 감사에 `status=failed` 와 RA 상태 · 오류 코드(본문 없이)로 남긴다. 서버 로그에 한 줄(파일 크기 · 쪽 수 · RA 코드)을 남긴다. | PPT A-9 |
| HP-04 | **백업** — 일일 백업(03:30)이 KooRemapper 인스턴스에 exec 하지 못해 KooRemapper DB 덤프가 매일 실패한다. | 기준 `e00338b` · `infra/scripts/backup-local.sh:99`(`apptainer exec … instance://$inst pg_dump`, 10-27 `f6c3c71` 도 같다). 10-02 부터 매일 `DBUS_SESSION_BUS_ADDRESS is not set` 으로 실패한다. 크론과 같은 빈 환경에서 rc 255, 두 변수를 주면 rc 0 이다(10-16 실측). 박스는 crontab 맨 위에 두 변수를 넣어 막아 두었다. | `XDG_RUNTIME_DIR` · `DBUS_SESSION_BUS_ADDRESS` 가 비어 있고 `/run/user/<uid>` · `bus` 소켓이 있으면 스크립트가 스스로 채운다(본보기 AIDataHub `deploy/apptainer/_common.sh:210-214`). 확인 — 다음 날 `backup.log` 에 `✓ kooremapper → …sql.gz` 가 있다. | update-all 안전 U2 |
| HP-05 | **기타 · 보안** — 사람이 등록한 외부 토큰(RA · TestScope · FMEA · MatNexus 등)이 `connections` 표에 평문으로 들어가고, 포털 sqlite 4개가 644 다. | 기준 `2e514e3` · `backend/app/auth/user_store.py:111-116` · `:314-319`(`connections` 표). 10-27 재확인 — `/data/svc/portal` 에서 users.sqlite 만 600(10-25 박스 손질)이고 agent_audit · conversations · procedures · token_store 는 644 다. 플랫폼이 늘 때마다 사람마다 토큰이 하나씩 더 쌓인다. | 포털이 sqlite 를 만들 때 umask 077 을 쓰거나 기동할 때 600 으로 맞춘다. 등록 토큰 암호화를 검토한다. 박스 파일 권한을 바꾸는 것은 우리 몫(D17, 90-OURS-box-todo.md OB-13)이다. | FMEA 연결 1-9 ③ · 4절 끝 · 10-25 피드백 OPS-2 — 높음(토큰) |


## 2. 중간


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HP-06 | **update-all** — 헬스게이트가 150 KB 가 넘는 `/tools-map` 을 환경 변수로 python3 에 넘겨 'Argument list too long' 이 나고, 거짓 종료코드 1 로 끝난다. | 기준 `f6c3c71` · `infra/scripts/update-all.sh:2627` · `:3001` · `:3022`(관련 `:3134` is_mcp · `:3212`). `/tools-map` 150,552 B 가 MAX_ARG_STRLEN 131,072 B 를 넘는다. MCP_COUNTS 가 비어 is_mcp=0 이 되고 kooremapper_mcp 의 정상 404 가 실패로 잡힌다. `:3001` 의 전후 도구 비교도 조용히 빠진다(10-19, 도구 657개 때는 통과). | TM 을 임시 파일로 쓰고 python 에는 경로만(또는 stdin 으로) 넘긴다. 세 곳을 모두 고친다. python 실패를 `true` 로 삼키는 꼴을 바꿔 알림 줄(⚠)을 낸다. | 10-25 피드백 PT-3 |
| HP-07 | **update-all** — 원격 LLM 이면 TOOL_MAX=0 을 '전량 바인딩' 이라며 다시 덮지만, 실제로는 1,613개 중 225개만 묶인다. | 기준 `f6c3c71` · `infra/scripts/update-all.sh:1329-1358`(덮는 줄 1354-1355, ok 문구 1356 · 1358). 에이전트 `/health` tool_cut 1,613 → 225(예산 88,473 토큰). 에이전트 코드 기본은 200(`app.py:1648`)인데 주석은 80 이다. | 에이전트 C-1 이 고쳐지기 전에는 TOOL_MAX 를 덮지 않는다(또는 캡 경로 + TOOL_SCHEMA_BUDGET 약 85,000 을 허용한다). ok 문구는 '전량 바인딩' 대신 `/health` tool_cut 의 '절단 N개' 로 바꾼다. | 온톨로지 시험 C-8 |
| HP-08 | **update-all** — MCP 자동 복구(repair_mcp)가 심의를 보지 않고 재프로비저닝과 게이트웨이 재기동을 한다. | 기준 `e00338b` · `update-all.sh:2677`(호출) · `:2635-2652`(sync-provision-env --write · provision-config --force · :9110 재기동) · §5 심의 확인 `:1761`. 10-27 재확인 — `f6c3c71` 에서는 `repair_mcp()` `:3056` · 호출 `:3098` 이다. 그때 heax · mxwp 토큰이 한 번 더 바뀌고 몇 초 동안 심의 · 챗 도구 호출이 끊긴다. ste 스모크 오탐은 `ea28339` 로 반영됐다. | 프로비저닝 · 재기동 앞에 `hwax_delib_busy http://127.0.0.1:9009/health` 를 두고 바쁘면 건너뛴다. (선택) repair 환경에 지금 config 의 `HEAX_MCP_TOKEN` 을 넘겨 heax PAT 를 다시 찍지 않게 한다. 확인 — update-all 에서 repair_mcp 가 돌지 않거나 「건너뜀」 이고 종료코드가 0 이다. | update-all 안전 U5-2 · U5-3 |
| HP-09 | **update-all** — heax 재검증이 `heax_registry` 키가 있는지만 본다. | 기준 `e00338b` · `update-all.sh:1637` · `:2365`(HEAD `f6c3c71` 기준 :1936 의 `grep -q '"heax_registry"'` · :2783-2786). per_user_sso 가 그 키를 남기므로 PAT 발급이 실패해 heax 앱 9개가 빠져도 ✓ 가 나고, §6 은 「HEAX Hub 앱 0개」 를 echo 로만 찍는다. | 키 존재가 아니라 heax 백엔드 수(또는 `heax_registry.token` · `servers_url` 존재)를 본다. 새 PAT 를 받은 뒤 옛것을 지우는 몫은 02-HWAXMcpGateway.md 다. | update-all 안전 U6-3 |
| HP-10 | **update-all** — (조건부) MX 백서가 고정 `--reload` 로 돌아 deploy-all 의 git reset 이 이관 전에 새 코드를 불러온다. | MX 백서 `infra/apptainer/api.def:57`(%startscript). 10-25 23:40:36 에 다시 뜬 mxwp_api 도 `--reload --reload-dir /workspace/apps/api/app` 로 돈다(10-27 재확인). 새 코드가 옛 스키마로 잠시 돈다(전에는 500). | MX 백서가 startscript 에서 `--reload` 를 빼면 할 일이 없다. 빼지 않기로 하면 deploy-all 이 git reset 전에 mxwp_api 를 멈춘다. 둘 중 하나만 한다. | 10-25 피드백 MX-3(포털 몫 대안) |
| HP-11 | **update-all** — update-sites → `services.py` 로 뜨는 서비스(게이트웨이 등)는 `infra/.env` 의 NO_PROXY 를 받지 못하고 부모 환경만 물려받는다. | 포털 9차 기준 `update-all.sh:39` · `:710` · `services.py:338`(Popen 에 `env=` 없음). 10-27 재확인(`f6c3c71`) — `start.sh:143-210` 은 NO_PROXY · no_proxy 를 `--env` 로 명시해 넘긴다(포털 쪽은 반영). `services.py:418` · `:487` 의 Popen 에는 여전히 `env=` 가 없다. 지금은 게이트웨이가 기동 때 스스로 보정하고(`gateway.py:85-134`) 박스 운영자 셸 블록(10-07)으로 완화돼 있다. | services.py 로 띄우는 서비스에도 `infra/.env` 의 NO_PROXY 를 리터럴로 명시해 넘긴다(`${NO_PROXY}` 꼴은 전개되지 않아 장애가 난다). systemd · cron 같은 다른 기동 경로에서도 같게 한다. | 포털 9차 §2 · §3 |
| HP-12 | **nginx 생성기** — `/ste/` 의 `proxy_read_timeout` 이 conf 를 다시 만들 때마다 600s 로 돌아간다(손잡이가 없다). | 기준 `f6c3c71` · `infra/scripts/gen-nginx-conf.sh` `loc_extras()` 28-40행(`:38` `proxy_read_timeout 600s;` — ste · apps · heax-hub · report-archive · odb-hub 묶음의 따옴표 heredoc) · `_nginx_time` 186-211행 · 맨 끝 sed 286-290행 · `infra/.env.example` 216-219행. 다시 만드는 때는 start.sh:37 · deploy-all · update-collab · update-all 이다. cae00 은 3600s 를 손으로 다시 넣고 있다(10-25 19:47 · 10-26 09:44). | `proxy_read_timeout {{STE_READ_TIMEOUT}};` 토큰 · `STE_READ_TIMEOUT="$(_nginx_time NGINX_STE_READ_TIMEOUT 600s)"` · sed 한 줄을 더한다(기본 600s, 묶음이 불편하면 ste 갈래만 떼어도 된다). `.env.example` 에 `# NGINX_STE_READ_TIMEOUT=600s` 와 한 줄 설명을 더한다. 시험으로 고정한다 — 비우면 600s, `3600s` 면 HTTP · TLS 두 `/ste/` 블록 모두 3600s, `0` · `abc` 면 기본값, `nginx -t` 통과(지금은 295-306행이 ✗ 만 찍는다). HP-13 과 한 변경으로 한다. | 10-25 피드백 PT-8 · nginx STE S-1b~S-1d · S-3 · S-3b — 중간(S-1) |
| HP-13 | **nginx 생성기** — `loc_extras` 에 `simflow` · `stcx-llm` 갈래가 없다. 600MB 업로드가 nginx 임시 디스크에 통째로 쌓이고, `/simflow/mcp` 스트리밍과 `/stcx-llm/` 비스트리밍 생성이 60초 침묵에 끊긴다. | 기준 `90147ac` · `gen-nginx-conf.sh:26-50`(`loc_extras`) · 참고 `:66-77`. 10-27 재확인 — `f6c3c71` 에도 두 갈래가 없다. `/stcx-llm/` 은 실측 60.1초에 504 였고 본문은 이미지 base64 라 수십 MB 다. | simflow 갈래 — `client_max_body_size 600m` · `proxy_request_buffering off` · `proxy_buffering off` · `proxy_read_timeout 3600s`(aireadyportal 과 같은 처리). stcx-llm 갈래 — `client_max_body_size 200m` · `proxy_buffering off` · `proxy_read_timeout 3600s`. 확인 — 생성된 `hwax.conf` 의 `location /simflow/ {` 안에 네 줄이 있다(HTTP · TLS 두 곳). | 파트너 타일 T3 · T3 추가(10-17) |
| HP-14 | **챗 업로드 · RA 보내기** — DRM 판정(`isEncryptedOffice`)이 사내 DRM 머리를 알아보지 못한다. | 기준 `dba4c1e` · `frontend/src/components/chat/docAttach.ts:36` 은 첫 바이트 `PK`(평문) · `D0 CF 11 E0`(OLE = 암호)만 가른다. 10-25 PC 시험 파일(37,316 B)의 앞 34바이트가 DRM 머리였고, RA 추출은 「zip 손상」 으로만 답했다. | DRM 머리 `3C 23 23 20 4E 41 53 43 41` 도 암호로 보고 PC 도우미(COM 추출) 안내로 돌린다. | 10-25 피드백 RA-1(포털 몫) |
| HP-15 | **챗 업로드 · RA 보내기** — 챗 업로드 목적지에 SimFlow 가 없어 `.x_t` 등은 「보낼 곳이 없습니다」 로 끝난다. | 기준 10-16 origin/main · `backend/app/agent/upload.py:26-63` `DESTINATIONS`(material · stepforge · reportarchive · aidatahub · dynaforge) · `:188-220` · `:18-22` · `routes.py:1140-1183` · `_dispatch_inner` · `pat_default_audiences` · `Composer.classify`. 챗 PAT 의 `aud` 가 `mcp-gateway` 뿐이라 REST 중계도 거절한다. | `DESTINATIONS["simflow"]`(라벨 「SimFlow — 워크플로우 입력 파일」, 권한 `plat:simflow`, 확장자는 설정 값)를 더한다. simflow 갈래는 500MB 를 넘으면 미리 막고 게이트웨이 `/api/simflow/api/v1/mcp-uploads` 로 multipart 를 흘려 보낸다. aud 에 `simflow` 를 더하거나 이 갈래용 짧은 PAT 를 만든다. 401 이면 한 번 다시 보내고 413 · 401 은 알아듣는 문구로 바꾼다. `drm_pending` 이면 `ready` 까지 본다. DRM 원본은 그대로 보낸다. 선행은 게이트웨이 U1 이다. | MCP 업로드 U2 |
| HP-16 | **위키 표시** — 위키가 꺼져 있는데 챗 「위키에 남기기」 · 「해결됨」 버튼과 심의 옵션 「MX 백서 위키에도 남기기」 가 보이고, 누르면 실패한다. | 기준 `f6c3c71` · `frontend/src/components/chat/MessageList.tsx:62` 는 `can("plat:mxwhitepaper")` 만 본다. `DelibOptsPanel.tsx:32` 의 showWiki 는 그 권한이거나 `delibOpts.wiki` 면 참이다. 약 124명에게 보이고 누르면 502 다. 옵션을 켠 사람은 결정문 끝(다단이면 단마다)에 내부 오류 문구가 붙는다. 10-27 재확인 — frontend/src · backend/app 에 wiki_enabled grep 0건이다. 이번 업데이트로 생겼다(`6c16d83` · `5cdf65a`). | 박스의 위키 켜짐 여부를 포털에 내보낸다(box-config 깃발, 또는 게이트웨이를 거친 `/api/v1/wiki/health` 캐시). 꺼져 있으면 두 버튼과 심의 옵션을 숨기고 이미 켠 옵션을 끄는 길만 남긴다. 소속이 없는 사람에게 나가는 409 안내가 똑같이 실패할 「해결됨」 을 권하지 않게 고친다. | 10-25 피드백 PT-1 |
| HP-17 | **백업** — 비밀 백업에서 `infra/.env` 와 `backend/.env` 가 같은 자리에 들어가 앞의 것이 사라지고, 박스 파일이 빠진다. | 기준 `e00338b` · `infra/scripts/backup-local.sh:286-292` · `:291`(10-27 `f6c3c71` 도 같다). 일일 비밀 백업에 `infra/.env`(포털 비밀 정본)가 없다. `routes.local.env` · `systems.local.yaml` · 박스 권한표(`backend/config` 의 `*.local.yaml`) · `.git/info/exclude` · crontab · 리스크 앱 `secrets.env` · `origin.json` 도 백업이 없다. | 자리를 `portal/infra` · `portal/backend` 로 나눈다. `backend/config/*.local.env` · `*.local.yaml` · `.git/info/exclude` · `crontab -l` 출력 · 리스크 앱 데이터 폴더의 `secrets.env` · `origin.json` 을 더한다. 확인 — 다음 묶음을 `tar -tzf` 로 열어 두 `.env` 가 따로 있고 박스 파일 · crontab 이 들어 있다. | update-all 안전 U3 |
| HP-18 | **백업** — `--install-cron` 이 `crontab -l` 실패를 빈 crontab 으로 읽고 전체를 다시 쓴다. | 기준 `e00338b` · `infra/scripts/backup-local.sh:58-61`(10-27 `f6c3c71` 도 같다). 같은 꼴의 `install-logrotate` 도 있다. 「no crontab」 이 아닌 일시 실패 한 번에 백업 · 감시 · 터널 줄이 모두 지워질 수 있다. | 「no crontab for <user>」 일 때만 빈 목록으로 보고, 그 밖의 실패에는 쓰지 않고 exit 1 로 멈춘다. | update-all 안전 U4 |
| HP-19 | **페르소나** — 페르소나 정본이 접두 없는 도구 이름을 써서 cae00 동기화 미리보기가 exit 2 로 막힌다. | `infra/personas/`(json) · `infra/scripts/sync-*-personas.py`. key_tools 의 `get_job` · `list_tags` · `get_guide` · `restore_version` 4건이 cae00 에는 접두 이름(`heaxkooremapper_mcp_get_job` · `aidatahub_list_tags` · `reportarchive_get_guide` · `reportarchive_restore_version`)으로만 있다. 그래서 `--apply` 를 못 한다. | 겹치는 도구는 정본 json 에 접두 이름으로 적는다. 또는 동기화 스크립트가 박스의 접두 이름으로 풀어 준다. HP-20 의 선행이다. | 10-25 피드백 PT-7 — 원문은 낮음, HP-20 선행이라 중간에 둠 |
| HP-20 | **페르소나** — 코어 온톨로지 운영자 페르소나가 없어, 운영자 key_tools 가 먼저 묶이는 길을 코어 질문에 쓰지 못한다. | `infra/personas/he-team.json`(18명 — 허브 · MatNexus · FMEA 없음) · `infra/scripts/sync-he-personas.py` · 참조 에이전트 `app.py:4234-4247`(운영자 key_tools → first, 앱 → pinned). cae00 AIDataHub 의 he-* 는 15명이다. | `he-data-coreontology` 를 더한다 — apps rootdesigndatahub, optional 다른 허브 둘(failuretrace 와 나머지 하나 — 앱 키는 원문 C-12), key_tools object_resolve · objects_list · objects_summary · graph_neighbors · object_get, 역할 문서에 코어 온톨로지 규칙(에이전트 C-3 의 7줄). 미리보기 → `--apply` 는 우리 몫이다. | 온톨로지 시험 C-12 |
| HP-21 | **기타** — 전문가 카드 본문 검색 스위치를 켜도 검색칸 문구가 「제목·요약에서 낱말로 찾기」 그대로다. | 기준 `90147ac` · `frontend/src/components/chat/AgentDeepView.tsx:323`(10-27 `f6c3c71` 도 같다). | AIDataHub 의 `AIDH_RECORDS_Q_BODY_SEARCH` 를 켤 때 「제목·요약·본문에서 낱말로 찾기」 로 바꾼다. 스위치는 AIDataHub 가 속도를 잰 뒤(10-AIDataHub.md AD-04) 우리가 cae00 에서 켜므로(90-OURS-box-todo.md OB-89) 그때에 맞춘다. | 지식카드 K5 요청 2(포털 몫) |


## 3. 낮음 · 선택


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HP-22 | **update-all** — §6 「NO_PROXY 에 없는 내부 목적지」 알림이 실제 트래픽 기준으로 거짓이다. | `infra/scripts/check-egress.sh` · `update-all.sh` §6. 게이트웨이 `gateway.py:85-134` 가 기동 때 NO_PROXY 를 보정하고, ss 로 본 연결은 직접 연결이다. 표시된 셋(rootdesign · compcore · simengbay)은 nginx 프록시 대상이다(포털 쪽은 코드 grep 근거라 추정이다). | 판정을 부르는 주체별로 나눈다. nginx 전용 라우트는 빼고, 게이트웨이 목적지는 게이트웨이 `/health` 의 보정 결과로 판정한다. | 10-25 피드백 PT-6 |
| HP-23 | **update-all** — (선택) 출구 점검이 `TESTSCOPE_BASE_URL` 만 보고, 설정으로 붙는 FMEA(:5190) · MatNexus(:8012) 호스트는 잡지 않는다. | 기준 `2e514e3` · `infra/scripts/check-egress.sh:102`(머리 주석 `:60` · `:78`). | 게이트웨이 전용 포털 내부 정책 응답의 `connections[*].mcp_url` 호스트도 알린다. | FMEA 연결 PB14 |
| HP-24 | **update-all** — §7 스모크가 에이전트 자기검증 상태를 보지 않는다. | 에이전트 `/health` 키에 self_check 가 없다(10-25 시험 기록). | 에이전트가 `/health` 에 `self_check {on, counts, ms p50/p95, last_error}` 를 실으면 §7 스모크가 그 칸을 읽어 알린다. | 10-25 피드백 AG-2(포털 몫) |
| HP-25 | **update-all** — (참고) 게이트웨이를 재기동할 때 열린 스트림 98건이 응답 없이 끊겼다. | 10-25 19:41:15 gateway.log 'ASGI callable returned without completing response' 98건. 재기동은 포털 update-sites(`infra/scripts/update-sites.sh` → `services.py`)가 한다. | 게이트웨이 graceful shutdown 에 맞춰 update-sites 의 재기동 순서를 맞춘다. | 10-25 피드백 GW-5(포털 몫) |
| HP-26 | **update-all** — 사람별 위임 앱(simflow · arp · odb-hub)의 /verify 를 보지 않는다. | 기준 `e00338b` · `update-all.sh:2306-2318` 은 ste 의 /verify 만 본다(HEAD `f6c3c71` 기준 :2725-2740 근처). 상대가 비밀을 바꾸면 사람 호출만 실패하고 업데이트는 녹색이다. | `PER_USER_SSO_APPS` 로 붙인 앱도 같은 꼴로 확인한다. | update-all 안전 U10-1 |
| HP-27 | **update-all** — `install-ste-tunnel.sh --check` 가 유닛 파일에 `-L 127.0.0.1:15812:` 가 없어도 실패로 끝나지 않는다. | 기준 `e00338b` · `infra/scripts/install-ste-tunnel.sh:104-105` 는 문구만 찍는다. 15810 만 여는 옛 유닛으로 바뀌어도 §2d 가 놓친다. | 15812 가 없으면 0 이 아닌 값으로 끝낸다. | update-all 안전 U10-3 |
| HP-28 | **update-all** — update-all 게이트웨이 기대 시험이 ODB config 를 쿼리 꼴로만 쓴다. | 기준 `90147ac` · `backend/tests/test_update_all_gateway_expectations.py:636`(`ODB_CFG`) · `:706` · 참고 `update-all.sh:980-998` · `:985` 주석. | 게이트웨이가 ODB 토큰을 헤더로 옮기면 헤더 꼴 config 도 한 경우 더한다(그 블록을 게이트웨이 원문에서 꺼내 맞춰 보는 시험이면). | 파트너 타일 T4-2 |
| HP-29 | **챗 업로드 · RA 보내기** — 'AI 데이터 허브' 목적지가 inbox 에 둔 사본을 지우지 않는다. | 기준 `f6c3c71` · `backend/app/agent/routes.py:1519-1532`(`:1523` copy2 → convert_file → audit → return, unlink 없음). chat 갈래(`:1495-1503`)에는 unlink 가 있다. 10-22 의 26.6 MB 가 서버 홈 `~/aidh-inbox` 에 남아 있다. | convert 뒤(또는 import_record 확정 뒤) 지운다. 아니면 inbox 에 TTL sweep 을 둔다. 남은 파일 정리는 우리 몫(D10, 90-OURS-box-todo.md OB-10)이다. | 10-25 피드백 PT-4 |
| HP-30 | **챗 업로드 · RA 보내기** — 문서 칩의 H1 에 inbox 임시 이름(`<계정>-chat-<8자>-`)이 드러나, 에이전트가 제목을 인용하면 계정 ID 가 섞인다. | 기준 `f6c3c71` · `backend/app/agent/upload.py:384` record_markdown 이 meta.title(inbox stem)을 먼저 쓴다. | chat 갈래에서 meta.title 이 dest.stem 과 같으면 원래 파일 stem 으로 바꾼다. | 10-25 피드백 PT-5 |
| HP-31 | **챗 업로드 · RA 보내기** — (참고) 서버에서 변환한 문서가 심의 근거에 'office-com-extract' 로 표시된다. | 기준 `f6c3c71` · `frontend/src/components/chat/docAttach.ts:134` 는 extractedBy 가 있으면 무조건 COM 추출로 본다. | extractedBy 가 'AI 데이터 허브' 로 시작하면 'aidh-convert' 로 따로 표시한다. | 10-25 피드백 PT-9 |
| HP-32 | **챗 업로드 · RA 보내기** — (참고 · 관측 없음) 게이트웨이 재기동 중에는 '정밀 변환' 목적지가 60초 캐시 창 동안 다시 보일 수 있다. | `upload.py` gateway_tool_names 는 `/tools-map` 을 못 읽으면 None 이 되어 숨기지 않는다(설계 판독). 10-25 기준 `/tools-map` 의 docforge 도구는 0개다. | 마지막으로 성공한 도구 지도를 None 대신 계속 쓴다. | 10-25 피드백 PT-11 |
| HP-33 | **챗 업로드 · RA 보내기** — 위임 토큰으로 RA 를 부를 때도 `X-Workspace-Slug` 를 싣는다. | `backend/app/agent/routes.py:1035`(HEAD `f6c3c71` 기준 :1366) · 관련 `connections.py:166-167` · `:109-111` · `RaConnectionCard.tsx:153`. RA 연결 9건이 모두 workspace 를 갖고 그중 2명은 `personal-*` 다. 10-25 `c52aa81` 이 「RA 보장이 확인되면 뺀다」 를 그 줄에 적고 시험으로 고정했다. | RA 가 헤더 없는 호출에 홈 부서를 보장하면 위임 경로에서 헤더를 빼고 시험을 바꾼다. | 포털 9차 §6 |
| HP-34 | **챗 업로드 · RA 보내기** — (선택 · 보류) DRM 문서를 웹 챗에 붙이려면 손으로 세 걸음(내려받기 → `.bat` 위로 끌어 놓기 → `.hwax.md` 다시 붙이기)을 거친다. | 기준 `dba4c1e` · `docAttach.ts:36` `isEncryptedOffice` · `DocExtractHint` · 포털 `/doc-extract/` 배포물. | 「PC 의 PowerPoint 로 열어 가져오기」 버튼 하나로 바꾼다. 선행은 정보보호 지침 확인(우리 몫, PPT B-2 ②, 90-OURS-box-todo.md OB-27)이다. 사내 공식 DRM 복호화 연동이 있으면 서버 한 곳(업로드 파싱 앞)으로 줄어든다. | PPT B-0 · B-2 |
| HP-35 | **페르소나** — (선택) update-all 이 돌 때마다 dev 덤프를 merge 해, cae00 판 운영자(도구 수 · `mcp_apps` · key_tools)가 dev 판으로 덮일 수 있다(코드 판독, 실제로 덮인 예는 없다). | 기준 `90147ac` · `infra/scripts/update-all.sh:738-740` · AIDataHub `deploy/apptainer/merge-from-drive.sh:4` · `:54` · `:119` · 미리보기 `sync-he-personas.py:174-200`. cae00 행의 updated_at 이 비어 있으면 dev 가 이긴다. | merge 뒤에 `sync-he-personas.py` 미리보기(쓰기 없음)를 돌리고 ✗ · `+` · `~` 가 나오면 warn 으로 알린다. | 지식카드 K8 요청 5 |
| HP-36 | **기타** — 포털 대화 검색이 기동 때 표지를 `aidh-768` 로 시작해, 재시작할 때마다 첫 검색이 이미 m3 인 메시지까지 다시 임베딩한다(결과는 맞고 시간만 든다). | 기준 `70f9e5e` · `_LAST = {"tag": MODEL}`. | 기동 때 AIDataHub 헬스로 표지를 채우거나 질의를 먼저 임베딩한다. | 10-17 수정 목록 P-10 |
| HP-37 | **기타** — `docs/embedder-bge-m3/server-setup.md` 8절 「포털 대화 검색은 옛 색인(aidh-768)을 다시 쓴다」 가 맞지 않다. | `message_vectors` 가 `INSERT OR REPLACE`(PK message_id, chunk_ix)라 m3 행이 옛 행을 덮는다. | 되돌리면 e5 로 다시 색인한다고 고쳐 적는다. | 10-17 수정 목록 P-11 |
| HP-38 | **기타** — 리스크 앱 사람 자격 절차서의 기대값과 해시가 낡았다. | 기준 `e00338b` · `docs/risk-credentials/server-setup.md` 4-7 · 38 · 47행 · 32행(update-collab 단계) · `docs/risk-claude-engine/checklist.md:12`(`eee3240f`). `server-setup-m3.md` 의 해시 · 사본 이름은 `69e99b7` 로 반영됐다. | 지금 Drive latest 판(스키마 5 · 도구 31종)에 맞춘다. 확인 ④ 의 경로를 인스턴스 안 `/app/backend/scripts/rr_gateway_check.py` 로 바꾼다(운영 박스에는 HWAXRisk 체크아웃이 없다). 박스 판에 따라 사본 이름이 다르다는 것도 적는다. | update-all 안전 U10-4 · 10-17 수정 목록 P-7 |
| HP-39 | **기타** — env 킷의 `DELIB_TIMEOUT_S` 주석과 동작이 어긋난다. | 기준 `e00338b` · `infra/env-kits/agent-server.env:37-38`(「지우면 코드 기본값」) · `infra/env-kits/apply-envs.sh:80-105` 가 지운 줄을 매번 다시 넣는다. 값(1800)이 코드 기본값과 같아 동작은 같다. | 킷 줄을 주석으로 바꾸거나, 대상 `.env` 의 `# KEY=` 줄을 「일부러 뺐다」 로 읽게 한다. 어느 쪽이든 주석을 맞춘다. | update-all 안전 U10-2 |
| HP-40 | **기타** — (참고) 점검표 · 과제 지시가 실제 경로와 다르다. `/agent/upload/destinations` 는 없는 경로이고, `/upload/analyze` 는 물성 CSV 미리보기이며, claims_affiliation 은 `/health/ready` 로 볼 수 없다. | 기준 `f6c3c71` · `routes.py:1169-1194` · `:1931` · `auth/downstream.py:77-78`(`/health/ready` 의 키 5개에 없다). | 점검표를 `POST /agent/upload` · `/dispatch` 의 401 로 생존을 보게 고치고, claims_affiliation 은 실행 중 레지스트리로 확인하게 적는다. 필요하면 `/health/ready` 에 claims 를 켠 시스템 목록을 더한다. | 10-25 피드백 PT-10 |
| HP-41 | **기타** — (선택) 챗 시작 패널에서 고른 전문가의 카드 전체 목록을 열 길이 없다. | 기준 `90147ac` · `StartPicker.tsx`(제목 `:306-310`, `nameOf` `:57`)에 `AgentDeepView` 가 연결돼 있지 않다(10-27 `f6c3c71` 에도 0건). 본보기 `PersonaBrowser.tsx:68` · `:301-309` · `AgentDeepView.tsx:19-30`. | `deep` 상태를 두고 `pool.find((a) => a.key === agentSel)` 가 있을 때만 `<AgentDeepView …/>` 를 연다. 「전체 보기 →」 버튼은 제목 옆에 단다. | 지식카드 K4 요청 2 |
| HP-42 | **기타** — (2단계) 포털 챗에 MCP Apps 패널 호스트가 없어, 파일이 끼는 워크플로우는 웹으로 돌아가야 한다. | 기준 10-16 origin/main · `frontend/src/api/chat.api.ts:63-90`(정해진 SSE 종류만 받는다) · `renderers/TextBlock.tsx:385-438`(이미 `<iframe sandbox="allow-scripts" srcDoc>`) · `backend/app/agent/upload.py:285` `mcp_call`(브리지에는 쓰지 않는다) · 참고 게이트웨이 `gateway.py:3530-3567`. | `ui_resource` 이벤트를 받으면 포털 백엔드가 사용자 신원으로 `resources/read` 를 불러 같은 출처를 막은 샌드박스 iframe(리소스 CSP 반영)에 띄운다. 브리지는 `ui/initialize` · `initialized` · `size-changed` · `ping` · `tools/call` · `ui/open-link` · `ui/update-model-context` 를 처리한다. 보안 규칙을 먼저 정한다 — 그 리소스를 낸 백엔드의 도구만 허용하고, `invoke_tool` · `rest_call` · `rest_catalog` 와 게이트웨이 자체 도구는 막고, open-link 는 허용 출처만 연다. 브리지의 `tools/call` 은 포털 백엔드 → 게이트웨이 한 세션으로 보내고, 감사에 `via=mcp-app` 과 리소스 URI 를 남긴다. 패널 안 조각 업로드는 수 MB 까지만 두고 그 위는 HP-15 업로드로 안내한다. 선행은 게이트웨이 M-1 · 에이전트 M-2 ① 이다. | MCP 업로드 M-2 ②~⑤ |
| HP-50 | **기타** — (조건부) RA 가 회수 창구(`POST /api/auth/sso/revoke`)를 열면, 사용자 정지 처리의 앱별 회수 호출에 RA 가 들어가야 한다. | 포털 8차 §7 — 정지 때 ste 토큰 회수 · 포털이 든 RA 위임 토큰 버리기 · 게이트웨이의 그 사람 토큰 캐시 비우기는 `701b676` · `f90a9eb` 로 반영됐다. 남은 것은 RA 가 이미 내준 토큰을 RA 쪽에서 회수하는 호출이다. RA 에는 그 창구가 아직 없다(11-ReportArchive.md RP-02). | RA 가 창구를 열면 정지 처리가 그 창구를 부르게 한다. 지금의 앱별 회수 호출이 RA 창구도 이미 부르는 꼴이면 그렇다고 알려 달라. | 포털 8차 §7 · RA SSO §5 회수 |


## 4. 질문 · 확인 요청


| # | 묻는 것 | 근거 | 출처 |
|---|---|---|---|
| HP-43 | `/ste/` 큰 결과 파일(수 GB) 내려받기가 `upstream prematurely closed connection while reading upstream` 으로 끊긴다. `proxy_read_timeout` · `proxy_send_timeout` 이 충분한지 봐 달라. | `GET /ste/api/jobs/<id>/result/file/<…>`(10-23 21:51~22:07 실측). 끊김이 ste 쪽(터널 · 서버) 원인인지는 14-Partner-apps.md 에 함께 묻는다. | nginx STE S-2 |
| HP-44 | update-all 의 거짓 종료코드(HP-06)가 §7 스모크 실패(rc 1)로도 잡혀 repair_mcp(HP-08)가 함께 돌 수 있는지 확인해 달라. | 우리 쪽 추론이고 관측은 없다. | update-all 안전 U5 · 10-25 피드백 PT-3 |
| HP-45 | 업무 절차 동시 실행 한도 `procedures_concurrency = 2` 를 심의 한도 6 에 맞출지 정해 달라. 맞춘다면 주석도 고친다. | `backend/app/config.py:212` 근처(HEAD `f6c3c71` 기준 :215) 주석은 「심의 DELIB_JOB_MAX_RUNNING · HWAXRisk risk_concurrency 와 같은 2」 인데 심의 한도는 6 으로 올렸다. 리스크 앱 `risk_concurrency = 2` 는 07-hwax-risk.md 에 같은 질문이 있다. | 심의 멈춤 §3 |
| HP-46 | 선언 플랫폼(connect) 반영이 최대 약 2분(정책 60초 + 패스 60초) 늦다. `/refresh` 로 충분한지, 포털이 mtime 변화를 보면 게이트웨이를 깨울지 판단해 달라. | 기준 `2e514e3` · 포털 `policy.py:350-366` · 게이트웨이 `gateway.py:1417-1420` · `:186`. | FMEA 연결 1-9 ⑨ |


## 5. 결정 필요 (사용자)


| # | 정할 것 | 선택지 | 권하는 쪽(원문) | 출처 |
|---|---|---|---|---|
| HP-47 | `/ste/` 결과 파일에 속도 · 연결 제한을 걸지 정한다. 사내 클라이언트 한 대(Go-http-client)가 d3hsp(수 GB)를 처음부터 되풀이해 받는다. 10-25 20:3x 까지 1,873건 · 5,350.7 GB, 10-23 3,975 GB, 10-24 5,740 GB 이고, 끊긴 전송 때문에 nginx 오류가 하루 수백 건 쌓인다. | (가) 클라이언트가 고쳐질 때까지 결과 파일 경로에 rate limit 을 건다(포털 nginx 몫). (나) 클라이언트 쪽 고침만 기다린다. | 먼저 그 클라이언트의 담당을 찾는다(기록의 원천은 한 대다). 고쳐지기 전에 다른 `/ste/` 사용자의 지연이 보이면 (가). | 10-25 피드백 STE-1 · D13 |
| HP-48 | 업무 절차 사전 점검에 선언 플랫폼(FMEA · MatNexus) 토큰 등록 여부를 넣을지 정한다. 지금 `backend/app/procedures/routes.py:417-453` `_ra_precheck`(기준 `2e514e3`)는 RA 만 봐서, 미등록이면 실행 도중 게이트웨이에서 실패한다. | (가) 선언 플랫폼 단계에도 같은 점검을 둔다. (나) 지금처럼 RA 만 본다. | 원문에 권하는 쪽이 없다. | FMEA 연결 1-9 ⑤ |
| HP-49 | 웹 심의 좌석 상한을 20 으로 둘지 정한다. 엔진은 `DELIB_MAX_SEATS` 로 올릴 수 있지만(`b7c76c9` · `d51a156`) 웹 세 곳(`backend/app/agent/routes.py:176` · `HandoffBrief.tsx:27` · `RosterEditor.tsx:11`)은 20 고정이라 21석 이상은 422 다. | (가) 20 그대로 둔다(포털 결정 기록 D-3). (나) 세 곳이 엔진 설정값을 따르게 한다. | 웹에서도 21석 이상이 필요할 때만 (나). | 심의엔진 4-2 |


## 6. 다른 플랫폼과 맞물린 것


| 이 문서 | 포털 몫 | 다른 플랫폼 몫 · 문서 | 출처 |
|---|---|---|---|
| HP-01 | deploy-all 이 표지를 만들고 지운다. | 04-KooRemapper-DynaForge.md KR-04 — 감시(`supervisor.sh`)가 표지나 update-all 잠금을 보면 건너뛴다. 표지 이름(`$DATA_DIR/deploy.lock.d`)을 두 쪽이 맞춘다. 그 전까지 배포 때 감시 줄을 잠시 빼는 것은 우리 몫이다(90-OURS-box-todo.md OB-79). | update-all 안전 U1-1 · U1-2 |
| HP-04 · HP-18 | `backup-local.sh` 가 두 변수를 채우고 crontab 다시 쓰기를 고친다. | 04-KooRemapper-DynaForge.md KR-05 · KR-09 — `backup-db.sh` · `_common.sh` · `install-autostart.sh`. 박스 crontab 맨 위 두 줄(임시)은 두 쪽이 들어오면 우리가 걷는다(90-OURS-box-todo.md OB-75). | update-all 안전 U2 · U4 |
| HP-08 · HP-09 | repair_mcp 앞 심의 확인과 heax 백엔드 수 재검증. | 02-HWAXMcpGateway.md HG-08 — 새 PAT 를 받은 뒤 옛것을 지운다. 박스 `provision.env` 의 `HEAX_MCP_TOKEN` 고정은 그 뒤 우리가 걷는다(90-OURS-box-todo.md OB-76). | update-all 안전 U5-2 · U6-1 · U6-3 |
| HP-02 · HP-03 | 거절 사유 표시 · 미리 막기 · 실패 감사. | 11-ReportArchive.md RP-16 — 가져오기 크기 · 쪽 수 · 그림 수 상한과 400 오류 문구 목록을 받고 OpenAPI · 화면에 적어 달라고 한다. `max_bytes` 값은 그 답으로 정한다. | PPT A-10 · 10-25 피드백 PT-2 |
| HP-14 | `docAttach.ts` 의 DRM 판정. | 11-ReportArchive.md RP-03 — 업로드 · 추출이 같은 머리를 알아보고 별도 오류를 낸다. 10-AIDataHub.md AD-03 — ppt 변환도 같은 판정을 한다. | 10-25 피드백 RA-1 |
| HP-16 | 버튼 · 심의 옵션 숨기기와 409 문구. | 03-HWAXAgentServer.md HA-08 — 꺼져 있으면 심의 `_wiki_submit` 을 건너뛰고 다단 심의에서는 한 번만 시도한다(`deliberation.py:3339-3349` · `:3359`). 09-MXWhitePaper.md MW-01 — `wiki_*` 14개를 켜져 있을 때만 등록한다. | 10-25 피드백 PT-1 · MX-2 |
| HP-10 | (대안) deploy-all 이 git reset 전에 mxwp_api 를 멈춘다. | 09-MXWhitePaper.md MW-03 — startscript 에서 `--reload` 를 뺀다. 둘 중 하나만 한다. | 10-25 피드백 MX-3 |
| HP-07 | update-all 이 TOOL_MAX 를 덮지 않는다. | 03-HWAXAgentServer.md HA-01 · HA-02 — 무캡 경로 캐시 키(C-1)와 코어 도구 늘 묶기(C-2). C-1 근거에 포털 `backend/app/agent/routes.py:402`(챗 PAT 30분 창)가 있지만 포털이 바꿀 것은 원문에 없다. | 온톨로지 시험 C-8 · C-1 · C-2 |
| HP-24 | §7 스모크가 self_check 를 읽는다. | 03-HWAXAgentServer.md HA-13 — `/health` 에 self_check 를 싣는다. | 10-25 피드백 AG-2 |
| HP-25 | update-sites 재기동 순서. | 02-HWAXMcpGateway.md HG-11 — graceful shutdown. | 10-25 피드백 GW-5 |
| HP-22 | check-egress 판정을 주체별로 나눈다. | 02-HWAXMcpGateway.md HG-18 — 기동 때 보정한 NO_PROXY 결과를 `/health` 에 싣는지. | 10-25 피드백 PT-6 |
| HP-12 · HP-13 | `loc_extras()` 한 변경. | 14-Partner-apps.md PA-12 — SimFlow 업로드 상한(MCP 업로드 U2 의 500MB 와 파트너 타일 T3 의 600MB 가 다르다)과 입력 확장자 목록. 90-OURS-box-todo.md OB-80 — 반영 뒤 `infra/.env` 에 `NGINX_STE_READ_TIMEOUT=3600s` 한 줄을 넣고 손 재적용을 멈춘다. | 파트너 타일 T3 · MCP 업로드 U2-1 · nginx STE §4 |
| HP-15 | SimFlow 목적지와 aud `simflow`. | 02-HWAXMcpGateway.md HG-04 — REST 중계에 SimFlow, 위층 401 이면 캐시 토큰 버리기가 먼저다. 사이트별 aud 를 맞추는 같은 꼴이 07-hwax-risk.md RK-02(PAT 버튼에 `step-forge`)에 있다. 14-Partner-apps.md PA-12 — SimFlow 입력 확장자 목록과 업로드 상한을 묻는다. | MCP 업로드 U1 · U2 · 리스크 자격 R2 |
| HP-42 | 포털 챗 패널 호스트와 브리지 보안 규칙. | 02-HWAXMcpGateway.md HG-07 — 도구 `_meta` · `ui://` 리소스 중계. 03-HWAXAgentServer.md HA-20 · HA-05 — `ui_resource` SSE 와 패널 전용 도구 숨기기(M-2 가 들어오면 푼다). 14-Partner-apps.md PA-14 — 패널이 부르는 도구 목록 · 브리지 메서드 · 리소스 CSP 를 묻는다. | MCP 업로드 M-0 · M-1 · M-2 |
| HP-28 | update-all 기대 시험에 헤더 꼴을 더한다. | 02-HWAXMcpGateway.md HG-02 — ODB 토큰을 헤더로 싣는다. 14-Partner-apps.md PA-09 — ODB 가 헤더를 먼저 보는지, 접속 기록에 본인 이메일이 찍히는지. | 파트너 타일 T4 · T4-2 · 운영쪽-1 |
| HP-33 | 위임 경로에서 `X-Workspace-Slug` 를 뺀다. | 11-ReportArchive.md RP-01 · RP-15 — SSO 계정의 홈 워크스페이스를 헤더 없이 보장하고 지금 처리 방식을 회신한다. | 포털 9차 §6 · RA SSO §2 · §4-1 · 포털 8차 §2-2 · §9 · §10-1 |
| HP-50 | RA 창구가 생기면 정지 처리에서 부른다. | 11-ReportArchive.md RP-02 — 회수 창구 `POST /api/auth/sso/revoke` 를 연다. | 포털 8차 §7 · RA SSO §5 회수 |
| HP-21 | 검색칸 문구. | 10-AIDataHub.md AD-04 — 운영 DB 사본에서 속도를 잰다. 90-OURS-box-todo.md OB-89 — 잰 값을 보고 cae00 에서 `AIDH_RECORDS_Q_BODY_SEARCH` 를 켠다. | 지식카드 K5 요청 2 |
| HP-35 | merge 뒤 미리보기 알림. | 10-AIDataHub.md AD-12 — 병합 규칙(`merge-from-drive.sh`) 확인. | 지식카드 K8 요청 5 |
| HP-29 | inbox 사본 지우기. | 90-OURS-box-todo.md OB-10 · OB-36 — 남은 `~/aidh-inbox` 사본과 `/tmp/ai_data_convert_*` 정리(D10). 10-AIDataHub.md AD-02 — 변환 부산물(`/tmp/ai_data_convert_*`)을 남기지 않는다. | 10-25 피드백 PT-4 · AIDH-1 · D10 |
| HP-19 · HP-20 | 정본 이름과 새 페르소나. | 90-OURS-box-todo.md OB-32 — 미리보기 → `--apply`. 03-HWAXAgentServer.md HA-03 — 운영자 key_tools 가 먼저 묶이는 길(`app.py:4234-4247`)과 코어 온톨로지 규칙(C-3). | 온톨로지 시험 C-12 · C-3 · 10-25 피드백 PT-7 |
| HP-45 · HP-49 | 절차 동시 한도와 웹 좌석 상한. | 07-hwax-risk.md RK-08 — `risk_concurrency = 2`. 03-HWAXAgentServer.md — 엔진 `DELIB_MAX_SEATS` 는 반영됐다. | 심의 멈춤 §3 · 심의엔진 4-2 |
| HP-43 · HP-47 | `/ste/` 결과 내려받기. | 14-Partner-apps.md PA-02 · PA-15 — 그 클라이언트가 끝난 잡만 받고 Range · If-Modified-Since · 크기 비교로 이어 받게 한다. 끊김이 ste 쪽 원인인지도 묻는다. HP-47 결정은 90-OURS-box-todo.md OB-11 에도 적었다. | 10-25 피드백 STE-1 · D13 · nginx STE S-2 |
| HP-46 | 반영 지연 판단. | 02-HWAXMcpGateway.md HG-17 — 같은 질문의 게이트웨이 자리(`gateway.py:1417-1420` · `:186`). | FMEA 연결 1-9 ⑨ |
| — | 포털 저장소 몫은 없다. 영역 고르기 화면(`ToolCatalogBlock.tsx:59` · `:74` · `StartPicker.tsx:75`)은 게이트웨이 `tool_areas.json` 을 그대로 보이고, 화면 변경 요청은 원문에 없다. | 02-HWAXMcpGateway.md HG-05 — 미분류 61.8% 를 줄이는 영역 규칙과 apps 기본값. | 온톨로지 시험 C-9 · 10-25 피드백 GW-4 · FMEA 연결 1-9 ⑦ |
| — | 포털 저장소 몫은 없다. 박스 권한표(`backend/config` 의 `*.local.yaml`)의 라벨 · 오버레이는 우리 몫이다(90-OURS-box-todo.md OB-04). | 03-HWAXAgentServer.md HA-23 · 02-HWAXMcpGateway.md HG-19 — '(시험)' 라벨 prod 앱(dynaforge-prod · stepforge-prod)을 챗에서 뺄지, 라벨을 바로잡을지는 사용자 결정이다. | 온톨로지 시험 C-4 |


## 7. 다시 볼 시험


| 시험 | 언제 | 무엇을 본다 |
|---|---|---|
| 10-25 시험 M-1 | HP-32 뒤 | 목적지 목록에 세 개만 보이고 '정밀 변환' 은 없다. |
| 10-25 시험 M-3 | HP-30 뒤 | 칩 H1 이 `<계정>-chat-<8자>-…` 가 아니다. |
| 10-25 시험 M-4 | HP-29 뒤 | 'AI 데이터 허브' 로 보낸 뒤 `~/aidh-inbox` 에 사본이 남지 않는다. |
| 10-25 시험 M-5 | HP-02 · HP-03 뒤 | 약 27 MB 평문 .pptx 를 RA 로 보내면 올리기 전에 막히고 사유가 보이며, 감사에 failed 줄이 남는다. |
| 10-25 시험 M-6 | HP-14 뒤 | DRM .pptx 를 끌어 놓으면 PC 도우미 안내가 뜬다. |
| 10-25 시험 M-11 · M-12 | HP-16 뒤 | 위키가 꺼져 있으면 버튼 · 심의 옵션이 보이지 않고 결정문에 오류 문구가 붙지 않는다. |
| OT-01~16 | 에이전트 C-1~C-6 과 HP-07 뒤 | `search_tools` 상위 8과 에이전트 `/health` tool_cut 을 다시 재고, 온톨로지 시험 5절대로 웹 챗 16개를 돌린다. |
| update-all 한 번 | HP-06 · HP-08 · HP-09 뒤 | 종료코드 0, kooremapper_mcp 판정 ✓, 전후 도구 비교 출력이 있고 repair_mcp 는 돌지 않거나 「건너뜀」 이다. |
| 다음 날 백업 | HP-04 · HP-17 뒤 | `backup.log` 에 `✓ kooremapper → …sql.gz` 가 있고, 비밀 묶음 `tar -tzf` 에 `portal/infra/.env` · `portal/backend/.env` · 박스 파일 · crontab 이 있다. |
| nginx 재생성 | HP-12 · HP-13 뒤 | 생성기 시험(S-3b)이 통과하고, `hwax.conf` 의 `/ste/` 두 블록 · `location /simflow/ {` 네 줄 · `/stcx-llm/` 갈래가 있다. |
| SimFlow 업로드 | HP-15 뒤 | `.x_t` 를 올리면 목적지에 SimFlow 가 보이고, 받은 id 로 `run_workflow` 가 돈다(감사 `mode=as-user-pat`). |


## 8. 이 문서에서 뺀 것


- PLM 관련 전부 — 사람 신원 전달(PLM-USER-IDENTITY-REQUEST · PLM-6 · D3) · 공유 한도(PLM-1 · D1) · enrich 기본값(D4) · `/plm-defect/` 경로에서 nginx 가 X-HWAX-User 를 덮어쓰는 포털 몫(10-25 피드백 PLM-20)은 보류다. 사용자 결정 「일단 PLM 관련은 그대로 두자」 를 따른다.


- 포털 10차 §1 · §5(가입 · 로그인 분리, 가입 선점)는 보류다. 공용 관리자 계정 때문에 로컬 로그인은 일부러 남기고, 로컬 가입은 승인하지 않는다.


- 유출 토큰 교체는 요청하지 않는다(사용자 결정, 10-25).


- 정지를 `LoginId` 로도 검사(미반영 총정리 §1 #15, `session.py:83-101`)는 조건부다. LoginId 만 오는 로그인이 실측될 때만 보낸다(사번 몫은 `d6f49e0` · `c0de1fb` 로 반영됐다).


- RA · TestScope 를 connect 꼴로 옮기기(FMEA 연결 1-9 ⑩)는 원문이 이번 범위 밖으로 둔다.


- 박스 `update-collab.sh` 의 심의 멈춤 손 수정(멈춤 → 기다림 → 재기동 → 내림 · EXIT 덫, 심의 멈춤 §4)은 포털 저장소에 보낼 것이 아니다. 이 파일은 박스 전용이라 git 이 추적하지 않는다(10-27 cae00 `.git/info/exclude` 확인). 포털 쪽 심의 멈춤은 `284e604` 로 반영됐고, 박스 파일은 우리 몫이다(90-OURS-box-todo.md OB-78).


- PPT A-1 「함께 확인한 것」 셋은 10-27 `f6c3c71` 에서 반영을 확인했다 — `DispatchResult` 에 `'done'`(`upload.api.ts:27-28`) · `<UploadRouter key=…>`(`Composer.tsx:441-442`) · RA 0블록 판정(`routes.py:1400-1401`).


- `start.sh` 의 NO_PROXY 명시 전달은 반영됐다(10-27 `f6c3c71` `start.sh:143-210`). services.py 갈래는 HP-11 이다.


- PPT A-1~A-6 · B-1 · B-2 ① 은 반영으로 정리됐다.


- `/ste/` 크기 10240m 과 크기 시험은 `308d3ac` 로 반영됐다(nginx STE §4).


- update-all 안전 U5-1(ste 스모크 오탐)은 `ea28339` 로 반영됐다.


- 포털 8차 §3 · §4 · §5 · §7 포털 쪽(§7 의 RA 회수 호출만 HP-50 으로 남겼다), 9차 §4 · §5 · §6 답(`c52aa81`) · §7-2, 10차 2 · 3 · 4 · 6 · 7 은 반영됐다.


- 10-17 수정 목록 3-1 의 P-7 밖 포털 항목과 P-7 일부(`69e99b7`)는 반영됐다.


- 지식카드 K3 요청 1~8 의 포털 몫(`520aadf` · `2e51b95`) · K4 요청 1 · 3(`23459cb`) · K5 의 포털 몫(`fb42f42`)은 반영됐다.


- 심의엔진 4-1 · 4-3 · 4-4 와 4-2 의 엔진 쪽(`b7c76c9` · `d51a156`), 심의 멈춤 R1 · R5 · durable 대기열 · 재기동 없는 한도(포털 `284e604`)는 반영됐다.


- FMEA 연결의 포털 항목(PB14 밖)은 반영됐다.


- 파트너 자동 로그인 타일은 끝났다 — ARP(10-15) · SimFlow(10-16) · ODB 허브(10-26) 모두 jwt-handoff 이고, 타일은 박스 카탈로그(우리 몫)다(파트너 타일 T1 · T2).


- 코어 온톨로지 연결 설정(주소 · 토큰 · NO_PROXY · 재기동 · 주기)은 10-27 cae00 · prod 에서 끝났다(우리 몫).


- MX 백서 APP_ENV=production 은 10-25 23:40 박스에서 반영됐다. `--reload` 는 HP-10 과 09-MXWhitePaper.md 다.


- 우리 몫(박스)은 90-OURS-box-todo.md 에 있다 — 나머지 sqlite 4개 600(D17) · `/ste/` 3600s 손 재적용 · crontab 맨 위 XDG/DBUS · 페르소나 `--apply` · `~/aidh-inbox` 정리(D10) · 박스 권한표 라벨 · 오버레이(C-4, OB-04) · 포털 사용자 관리(소속 빈 사용자 · 대기 건, 로컬 가입은 승인하지 않는다).
