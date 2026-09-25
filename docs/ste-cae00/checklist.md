# 체크리스트 — ste × cae00 × Claude MCP

완료 기준을 만족할 때만 체크한다(만들었다 ≠ 됐다 — 검증까지가 완료).

## S0 — 재기 (cae00, 사람 1회)
- [ ] `ste-doctor --report` 를 cae00 에서 1회 실행, 출력을 `context-notes.md` §F 에 붙인다
- [ ] 확정할 것: ste-tunnel 의 `-L` 포트(15810 만/15812 도) · `systemctl --user cat ste-tunnel`
- [ ] 확정할 것: 포털 인증서 종류(`/tls/info` 의 `self_signed`, 체인이 공개 루트에 닿는가)
- [ ] 확정할 것: 헤드 `/opt/ste/.env` 의 `STE_SSO_SECRET` 일치 여부·`STE_MCP_TOKEN` 유무
- [ ] 확정할 것: Teleport 인증서 TTL·`port_forwarding` 허용·비대화식 만료 거동
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
- [ ] `infra/systemd/ste-tunnel.service` 템플릿(-L 15810·15812, ExitOnForwardFailure, Restart=always) + `install-ste-tunnel.sh`(transport.env 읽기, linger)
- [ ] `routes.local.env` `ste=` 부재 + teleport → `ste=http://127.0.0.1:15810/` 제안, `HWAX_STE_AUTOROUTE=1` 이면 기록·gen-nginx-conf
- [ ] `deploy-backend.sh` 가 헤드 `/opt/ste/.deployed-commit` 기록 · `deploy-ste.sh` teleport 분기가 Drive `ste-code.commit` 과 대조
- [ ] `--if-stale` 지문에 `backend/mcp_server`·`apps` 포함
- [ ] `transport.sh` `tr_session_ok()`(tsh status 잔여 TTL) · 게이트 = 사람호출 ∧ 신선도 ∧ 세션 (STE_DEPLOY=1 은 ①② 를 강제로 참)
- [ ] `update-all --with-ste` 플래그 · `flock` 잠금
- [ ] dev `build-all-to-drive.sh` 가 `pack-staging + push-to-drive` 를 포함(clean tree 조건 유지)
- [ ] `ste-doctor` — 터널 두 포트·시크릿 verify·인증서 TTL·게이트웨이 ste 세션·정책 적재를 한 화면에, §6 이 호출
- [ ] 검증(dev direct): 신선도 같으면 무동작 · 다르면 배포 · 잠금 겹침 거부 · 세 신호 각각 거짓일 때 사유 한 줄
- [ ] 검증(cae00): `update-all --with-ste` 1회 → `ste-doctor` 전부 초록 → 평소 `update-all` 이 ste 를 건드리지 않되 빨강이면 명령을 안내

## S3 — 사용자 첫 성공
- [ ] ste `POST /api/uploads`(스트리밍 2GB, 사용자 명의 1회용 티켓) + MCP `prepare_upload` · `submit_job(upload_id)`
- [ ] MCP `get_job_file(job_id, path, tail|offset, ≤64KB)` · `get_job_result` 설명에서 `result.zip` 제거
- [ ] 게이트웨이 `rest_call`·REST 프록시 응답 크기 상한(1MB) — zip/binary 는 스트림을 끊고 error
- [ ] 도구 설명이 접두어 이름(`ste_submit_job`)을 가리킴 · `{'error':…}` → isError · `STE_MCP_TOKEN` 폴백 제거 · ste-sync 상태·토글 도구
- [ ] TokenPage: `canToken=false` 안내 링크 · "이 토큰으로 열리는 플랫폼" 목록 · `list_tool_apps` 거부 앱 라벨 · `initialize` instructions 한 줄
- [ ] `/tls/info` → `needs_ca` + 발급 CA 체인 내려주기 · Claude Code 는 settings.json env 경로 우선(S0 판정에 따라)
- [ ] 검증(dev, Claude Code 실주행): "k파일 올려 돌리고 결과 받기" 끝까지 · 모델 출력에 파일 바이트 0 · 권한 없는 계정으로 안내 문구 확인

## S4 — 무인화
- [ ] tbot 봇·조인 토큰 관리자 요청(teleport-transport.md §7-1 조건) → `transport.env` 전환 · 스크립트 무변경 확인
- [ ] 그 전까지: 가이드에 "cae00 ste 는 사람 로그인 전제" 명문화 · `ste-doctor` 잔여 TTL 표시

## 사용자 결정 (2026-09-25 확정)
- [x] 셋업/갱신 분리 + 세 신호 게이트 — **채택.** 새 옵션에도 쓰이게 **공용 함수**로(D-13)
- [x] 자동 라우트 기록 — **기본 켬**(`HWAX_STE_AUTOROUTE=0` 으로만 끈다)
