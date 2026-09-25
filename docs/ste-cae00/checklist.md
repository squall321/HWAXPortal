# 체크리스트 — ste × cae00 × Claude MCP

완료 기준을 만족할 때만 체크한다(만들었다 ≠ 됐다 — 검증까지가 완료).

## S0 — 재기 (cae00, 사람 1회)
- [ ] `ste-doctor --report` 를 cae00 에서 1회 실행, 출력을 `context-notes.md` §F 에 붙인다
- [ ] 확정할 것: ste-tunnel 의 `-L` 포트(15810 만/15812 도) · `systemctl --user cat ste-tunnel`
- [ ] 확정할 것: 포털 인증서 종류(`/tls/info` 의 `self_signed`, 체인이 공개 루트에 닿는가)
- [ ] 확정할 것: 헤드 `/opt/ste/.env` 의 `STE_SSO_SECRET` 일치 여부·`STE_MCP_TOKEN` 유무
- [ ] 확정할 것: Teleport 인증서 TTL·`port_forwarding` 허용·비대화식 만료 거동 — `ste-doctor` 의 teleport 항목이 `tsh status` 를 읽는다(형식 미확인이라 못 읽으면 "모름")
- [ ] 확정할 것: `provision.env` 의 `STE_MCP_URL`·`STE_SSO_URL` 명시 여부, `HEAX_MCP_TOKEN` 자동 발급 성공 여부
- [ ] 확정할 것: Drive `SmartTwinExplorer/staging` 의 `ste-code.commit` 이 dev HEAD·헤드 배포본과 같은가

## S1 — 시크릿 유출 차단 + 죽어도 초록인 자리 넷
- [x] `refresh-code.sh` §8 → `sync-sso-secret.sh` 호출로 교체(argv 에 시크릿 0건) · FORCE 분기도 stdin — ste `41ef116`, dev VM ps 6,240줄 샘플에 값 0건
- [ ] 이미 argv 판으로 배포된 회차가 있으면 시크릿 회전(`FORCE_SSO_SECRET=1`) — S0 결과에 따라
- [x] ste `POST /api/auth/sso/verify`(204/401, JIT 없음) + §6 이 포털 실제 값으로 2차 판정 — ste `3317f85`, 1차 프로브(옛 판·404 판별)는 유지
- [x] §6 이 `/health.backends.ste == true` 를 본다 · 15812 프로브(살아 있으면 406/200) · STE_ROUTED=1 이고 DOWN 이면 fail + 터널 -L 15812 힌트
- [~] §6 `access_policy_loaded == 0` → fail(완료) · 게이트웨이 per_user 백엔드 정책 미적재 = 거부(다음)
- [x] 검증: 시험 하네스에서 거짓 상태 넷(verify 401·ste false/absent·15812 000·정책 0)을 만들어 빨강 확인 + dev 실물에서 셋 초록
- [x] 변이: 세 가드를 되돌리면 각각 해당 시험만 깨진다

## S2 — 셋업 자동화
- [x] `infra/systemd/ste-tunnel.service` 템플릿(-L 15810·15812, ExitOnForwardFailure, Restart=always) + `install-ste-tunnel.sh`(transport.env 읽기, linger, `--check`; direct 는 무동작)
- [x] update-all 1d — `routes.local.env` `ste=` 부재 + teleport → `ste=http://127.0.0.1:15810/` **기본 기록**(§2 가 nginx 재생성), `HWAX_STE_AUTOROUTE=0` 으로 끔. 빈 `ste=` 는 존중
- [x] `deploy-backend.sh` 가 헤드 `/opt/ste/.deployed-commit` 기록(ste `86c32b0`, dev VM 확인) · `deploy-ste.sh` teleport 분기가 Drive `ste-code.commit` 과 대조(모름≠같음)
- [x] `--if-stale` 지문에 `backend/mcp_server`·`apps` 포함(4트리, dev 실측 "이미 최신")
- [x] 공용 게이트 `infra/scripts/lib/deploy-gate.sh` = 사람호출 ∧ 신선도 ∧ 전제(세션 = `tr_run true`) · `--with-ste`/`STE_DEPLOY=1` 은 ①② 강제 · 이름 무관(새 옵션은 등록만). tsh TTL 파싱은 S0 결과 뒤(dev 에 tsh 없음)
- [x] `update-all --with-<name>` 플래그(HWAX_WITH) · `flock` 잠금(겹치면 rc=3)
- [x] dev `build-all-to-drive.sh` 가 `pack-staging + push-to-drive` 를 포함(기본 대상에 ste) · `drive-drift.sh` 가 Drive `ste-code.commit` 을 HEAD 와 대조 — 실측: Drive 가 하루 전 판(`1d456de`)이었고 올려서 `86c32b0` 일치
- [x] `ste-doctor.sh` — 라우트·transport·web(15810)·mcp(15812)·터널 유닛·Teleport 잔여(tsh 있을 때)·시크릿 verify·게이트웨이 ste 세션·정책 적재·배포 신선도를 한 화면에(`--report` JSON, 읽기 전용). §6 은 ste 빨강 때 이것을 가리킨다
- [x] 검증(dev direct): 4트리 지문 같으면 무동작(실측) · 잠금 겹침 rc=3(시험) · 세 신호 각각 거짓일 때 사유 한 줄(시험 7건) · 변이 3건
- [ ] 검증(cae00): `update-all --with-ste` 1회 → `ste-doctor` 전부 초록 → 평소 `update-all` 이 ste 를 건드리지 않되 빨강이면 명령을 안내

## S3 — 사용자 첫 성공
- [x] ste `POST /api/uploads`(스트리밍 2GB, 사용자 명의 1회용 티켓) + MCP `prepare_upload` · `submit_job(upload_id)` — ste 3317f85·86c32b0
- [x] MCP `get_job_file(job_id, path, tail|offset, ≤64KB)` · `get_job_result` 설명에서 `result.zip` 제거 — ste 3c3ce91
- [x] 게이트웨이 `rest_call`·REST 프록시 응답 크기 상한(1MB) — zip/binary 는 스트림을 끊고 error — 게이트웨이 d17ff29 (실측: result.zip 이 body 0 으로 오류)
- [x] 도구 설명이 접두어 이름(`ste_submit_job`·**`ste_prepare_upload`**)을 가리킴 · `{'error':…}` → isError · `STE_MCP_TOKEN` 폴백 제거 · ste-sync 상태·토글 도구 — ste 3c3ce91·41709e6 (D-15)
- [x] TokenPage: `canToken=false` 안내 링크(`/access?need=feat:api-token`) · "이 토큰으로 지금 열리는 플랫폼" 목록(`/auth/access` 행의 `tools`) · `list_tool_apps` 거부 앱 라벨·필요 권한·요청 경로(`denied_apps`, 게이트웨이 bbfec74) · `initialize` instructions 9항 — D-16
- [x] `/tls/info` → `needs_ca`(openssl verify, 공개 번들만)·`ca_available`·`verify_error` + `/tls/ca.crt` 발급 CA 체인(`TLS_CA_PATH` 선택) — D-16
- [x] 적대 검토 1라운드 8건 수정(TLS 경로 앵커·리프 대체 거짓·거부 사유·만료·옛 백엔드 창) — D-17
- [x] 적대 검토 2라운드 10건 수정(체인 -untrusted·공유 TTL 상태·모름 상태·스니펫 잠금·사유 전파·doctor tls 행) — D-18
- [ ] Claude Code `~/.claude/settings.json` env 의 `NODE_EXTRA_CA_CERTS` 경로 — **S0 판정 뒤**(cae00 인증서 종류 + 그 env 가 Node 기동 전에 적용되는지 실측 필요, 여기서는 못 한다)
- [~] 검증(dev, 게이트웨이 실호출): "파일 올려 돌리고 결과 받기" 끝까지 **통과**(티켓→PUT 81B→제출→재제출 409→COMPLETED→꼬리 3줄→없는 파일 404→sync 토글, D-15) · 모델 출력에 파일 바이트 0 · 권한 없는 호출자의 `list_tool_apps` 실호출(plat:smarttwin 만 → 거부 14개 라벨·요청 경로, D-16) · **화면으로 못 본 것**: 권한 없는 계정으로 TokenPage 문구(빌드·코드 경로만 확인, 실계정 없음)

## S4 — 무인화
- [ ] tbot 봇·조인 토큰 관리자 요청(teleport-transport.md §7-1 조건) → `transport.env` 전환 · 스크립트 무변경 확인
- [ ] 그 전까지: 가이드에 "cae00 ste 는 사람 로그인 전제" 명문화 · `ste-doctor` 잔여 TTL 표시

## 사용자 결정 (2026-09-25 확정)
- [x] 셋업/갱신 분리 + 세 신호 게이트 — **채택.** 새 옵션에도 쓰이게 **공용 함수**로(D-13)
- [x] 자동 라우트 기록 — **기본 켬**(`HWAX_STE_AUTOROUTE=0` 으로만 끈다)
