# ste 를 cae00 에서 — `update-all` 한 번에 서고, 사용자 PC 의 Claude 에 바로 물린다

> 2026-09-24 착수. 대상은 **ste(24대 클러스터의 SmartTwinExplorer 웹·MCP)** 를 **cae00** 에서 운영하는 경로다.
> StepForge·DynaForge 는 범위 밖(별도 요청서로 진행 중). 판단 근거는 `context-notes.md`, 진행은 `checklist.md`.
>
> ⚠ **cae00 은 dev 에서 닿지 않는다.** 아래 "확인" 은 스크립트·문서·dev 실측으로 확인한 것이고, cae00 박스의
> 실상태(터널 포트·시크릿·인증서 종류·Teleport TTL)는 **미확인**이다. 그래서 S0 이 "재는 것" 부터 시작한다.

## 0. 요구와 결론

**요구** — cae00 에서 `update-all` 을 돌리면 ste 가 다 서고, 사용자가 자기 PC 의 Claude 를 MCP 로 물려 바로 쓴다.

**결론** — 배선 자체는 dev 에서 끝까지 실측된다(포털 로그인 → 게이트웨이 본인 명의 위임 → ste MCP → REST,
`/api/auth/me` 200). 그런데 cae00 에서는 그 배선 **앞뒤가 사람 손에 매달려 있고, 손을 안 대면 초록으로 가려진다.**
확인된 마찰 19건을 넷으로 묶으면 이렇다.

| 묶음 | 핵심 | 지금 상태 |
|---|---|---|
| **A. 셋업이 자동이 아니다** | `ste-tunnel` 을 만드는 코드가 **어느 리포에도 없다.** `routes.local.env` 의 `ste=` 는 gitignore 라 새 클론에 없다. 2c 는 teleport 에서 `STE_DEPLOY=1` 없이는 **아무것도 안 한다** | update-all 은 ste 코드를 **결코** 갱신하지 않고 "건너뜀" 만 찍는다 |
| **B. 죽어도 초록이다** | 게이트웨이 ste 가 DOWN 이어도 §5 는 키 유무만 봐서 통과, DOWN 분기는 "매핑된 서비스 없음". §6 자격중계 게이트는 **시크릿 불일치를 "설정됨" 으로** 읽는다. 15812 프로브가 없다 | 터널·시크릿·MCP 포트 셋 다 잘못돼도 exit 0 이 가능하다 |
| **C. 사용자 첫 성공이 멀다** | 파일이 MCP 로 못 간다(`content` 문자열 → LLM 컨텍스트 경유, 바이너리 불가). 결과는 목록만 주고 `result.zip` 을 `rest_call` 로 부르면 게이트웨이가 수 GB 를 메모리에 받는다. 권한 게이트 둘(`feat:api-token`·`plat:smarttwin`)을 아무도 말해 주지 않는다. TLS 가 사내 CA 서명이면 인증서를 아예 안 심는 분기 | "k파일 올려 돌리고 결과 받기" 는 지금 MCP 만으로 **안 된다** |
| **D. 전부가 사람 로그인에 매달린다** | cae00→헤드의 모든 경로(배포·런타임 터널·게이트웨이 mint)가 `tsh login` 인증서 하나에 묶여 있고, 만료를 보는 프로브가 없다. tbot 무인화는 계획서에만 있다 | "무인 셋업" 이 정의되지 않는다 |

그리고 **보안 결함 하나가 확인됐다** — cae00 실배포 경로(`refresh-code.sh` §8)가 `STE_SSO_SECRET` 을 **원격 명령 인자로**
넘겨 Teleport 세션 기록과 헤드 `ps` 에 남는다. dev 가 부르는 `sync-sso-secret.sh`(stdin)로 고쳤지만 **teleport 경로는 옛 판을 돈다.**
이건 순서와 무관하게 먼저다.

## 1. 요구의 모순을 어떻게 푸나 — 셋업과 갱신을 가른다

"`update-all` 로 바로" 와 "routine 에 에어갭 실배포가 섞이면 안 된다" 는 **같은 실행에 두 뜻을 싣는 한** 충돌한다.
가르면 둘 다 선다.

- **셋업(1회·명시)** — `update-all --with-ste`(또는 `STE_DEPLOY=1`). 부트스트랩·터널 유닛 설치·시크릿 동기화·코드 배포·전 게이트 검증까지 **한 번에 끝까지** 간다. 사람이 앉아서 부른다.
- **갱신(routine)** — 평소 `update-all`. ste 는 **세 신호가 모두 참일 때만** 배포한다. ① 사람이 부른 실행(`[ -t 0 ]` 또는 명시 플래그) ② 스테이징 커밋 ≠ 헤드의 배포 커밋(신선도) ③ Teleport 세션 유효. 하나라도 거짓이면 **사유를 한 줄로 찍고** 건너뛴다.
- **진단(항상)** — `ste-doctor`: 터널(15810·15812)·시크릿 일치·인증서 잔여·게이트웨이 ste 세션·권한 정책 적재를 **한 화면**에 낸다. §6 이 이것을 부르고, 빨강이면 `--with-ste` 를 **명령 그대로** 안내한다.

`STE_DEPLOY=1` 게이트가 막던 "크론" 은 리포·가이드 어디에도 없다(`backup-local 03:30`·`koorm @reboot` 뿐). 존재하지 않는 위협을
막느라 요구를 깨고 있었다.

## 2. 단계

### S0 — 재기 (cae00, 사람 1회) · 아무것도 고치지 않는다
cae00 의 실상태를 **숫자로** 받는다. 여기서 갈리는 것이 많다 — 터널 포트, 인증서 종류, 시크릿 일치, Teleport TTL.
- `ste-doctor --report` 를 먼저 만들어(S1 의 첫 산출물) cae00 에서 한 번 돌린다. 출력을 `context-notes.md` §F 에 붙인다.
- **판정**: 미확인 12개 중 몇 개가 확정됐나. 특히 15812 터널·시크릿 일치·`self_signed`.

### S1 — 시크릿 유출 차단 + 죽어도 초록인 자리 넷 (HWAXPortal·SmartTwinExplorer·게이트웨이)
1. `refresh-code.sh` §8 을 **통째로 `sync-sso-secret.sh` 호출로** 바꾼다. FORCE 분기도 stdin 으로. 이미 실행된 회차가 있으면 시크릿을 **회전**(`FORCE_SSO_SECRET=1`).
2. ste 에 `POST /api/auth/sso/verify`(시크릿만 검증, JIT 없음, 204/401)를 더하고 §6 이 **포털 실제 값**으로 그것을 친다. "아무 값 401 = 설정됨" 판정은 폐기.
3. §5/§6 이 게이트웨이 `/health.backends.ste == true` 를 본다(키 유무 아님). 15812 프로브(initialize 200 또는 406). ste DOWN 이면 **fail**(STE_ROUTED=1 일 때).
4. §6 이 `access_policy_loaded == 0` 이면 fail. 게이트웨이는 per_user 백엔드(ste·kooremapper_mcp)에 한해 **정책 미적재 = 거부**로 기본을 뒤집는다.
- **검증**: 각 항목을 dev 에서 **거짓 상태를 만들어** 빨강이 뜨는지 본다(시크릿을 다르게·15812 를 막고·정책 캐시를 지우고). 변이 검사로 가드를 되돌리면 시험만 깨지는지.

### S2 — 셋업 자동화 (HWAXPortal)
1. **`ste-tunnel` 을 리포가 소유한다** — `infra/systemd/ste-tunnel.service` 템플릿(`ssh -N -F <TELEPORT_SSH_CONFIG> -L 127.0.0.1:15810:127.0.0.1:15810 -L 127.0.0.1:15812:127.0.0.1:15812`, `ExitOnForwardFailure=yes`, `Restart=always`) + `install-ste-tunnel.sh`(SmartTwinExplorer `transport.env` 를 읽어 채움, linger). `only_on` 은 쓰지 않는다 — services.yaml 은 프로세스 기동이지 터널 관리가 아니다.
2. `routes.local.env` 에 `ste=` 가 없고 transport 가 teleport 면 `ste=http://127.0.0.1:15810/` 을 **제안**한다. teleport 박스의 값은 관례가 고정이라 `HWAX_STE_AUTOROUTE=1` 이면 기록 후 gen-nginx-conf.
3. `deploy-ste.sh` teleport 분기 게이트를 §1 의 **세 신호 AND** 로 바꾼다. 신선도는 `deploy-backend.sh` 가 헤드 `/opt/ste/.deployed-commit` 에 기록하고 Drive `ste-code.commit`(수 KB, `rclone cat`)과 대조한다. `--if-stale` 지문에 `backend/mcp_server`·`apps` 를 넣는다(지금은 MCP 서버가 낡아도 "이미 최신").
4. `transport.sh` 에 `tr_session_ok()` — `tsh status` 의 잔여 TTL 을 읽어 N분 미만이면 거부. `ste-doctor` 가 같은 값을 보여 준다.
5. `update-all --with-ste` 플래그(가이드 §4 의 미적용 제안을 살린다) + 잠금(`flock`) — 2c 배포 중 재실행이 겹치지 않게.
6. dev: `build-all-to-drive.sh` 가 `pack-staging + push-to-drive` 를 **포함**한다(clean tree 조건은 유지). 사람이 기억하는 선행 단계를 없앤다.
- **검증**: dev 의 direct 경로로 신선도·잠금·세 신호를 시험. teleport 는 cae00 에서 `--with-ste` 1회 실주행 후 `ste-doctor` 전부 초록.

### S3 — 사용자 첫 성공 (SmartTwinExplorer MCP · HWAXPortal 화면 · 게이트웨이)
1. **파일 입구** — ste 에 사용자 명의 1회용 업로드 티켓 `POST /api/uploads`(스트리밍, 2GB) 를 두고, MCP 에 `prepare_upload` → 사용자 PC 의 Claude 가 `curl` 로 올림 → `submit_job(upload_id=…)`. 바이트가 **모델을 안 거친다.** 포털 PAT 하나로 끝난다(티켓이 ste PAT 를 대신한다).
2. **파일 출구** — `get_job_file(job_id, path, tail_lines|offset, 상한 64KB)` 텍스트 도구. `get_job_result` 설명에서 `result.zip` 언급을 지우고 이 도구와 ste-sync 로 안내. 게이트웨이 `rest_call`·REST 프록시에 **응답 크기 상한**(1MB, 초과 시 스트림을 끊고 error) — 지금은 120MB 응답에 피크 521MB 를 쓴다(실측).
3. 도구 설명이 **접두어 이름**을 가리키게(`ste_submit_job`). `{'error':코드}` 를 isError 로. `STE_MCP_TOKEN` 폴백을 **끈다**(신원 없으면 401 이 맞다 — 지금은 잠복한 "전체 잡" 폴백이다). ste-sync 상태·토글 도구.
4. **권한 안내** — TokenPage `canToken=false` 에 "API 토큰 권한 → /access#api-token" 링크, 발급 화면에 "이 토큰으로 지금 열리는 플랫폼" 목록. 게이트웨이 `list_tool_apps` 가 거부된 앱의 라벨과 요청 경로를 낸다. `initialize` instructions 에 한 줄.
5. **TLS** — `/tls/info` 가 `self_signed` 대신 **`needs_ca`**(체인이 공개 루트에 닿는가)를 내고, 사설 CA 면 리프가 아니라 **발급 CA 체인**을 내려 준다. Claude Code 는 stdio 8단 체인 대신 `~/.claude/settings.json` env 에 `NODE_EXTRA_CA_CERTS` 를 두는 길을 우선한다(S0 의 인증서 종류 판정에 따라 갈린다).
- **검증**: dev 에서 Claude Code 로 "k파일 올려 돌리고 결과 받기" 시나리오를 **실제로** 끝까지. 모델 출력에 파일 바이트가 0.

### S4 — 무인화 (관리자 협조)
- tbot(Machine ID) 봇·조인 토큰을 클러스터 관리자에게 요청(SmartTwinExplorer `docs/01-plan/teleport-transport.md` §7-1 조건). `transport.env` 의 `TELEPORT_SSH_CONFIG` 를 tbot 생성 파일로 바꾸면 **스크립트 무변경**이다.
- 그 전까지 계획서에 명문화: **cae00 의 ste 는 사람 로그인이 전제**이고, `ste-doctor` 가 잔여 TTL 을 보여 준다.

## 3. 하지 않는 것
- StepForge·DynaForge 관련(별도 요청서).
- `routes.local.env`·`transport.env`·`provision.env` 를 git 에 넣는 것 — 박스 비밀·주소다. **제안·검증까지만** 자동화한다.
- 게이트웨이 fail-open(정책 캐시로 버티기)을 전면 fail-closed 로 뒤집는 것 — 가용성을 위해 일부러 그렇게 잡힌 자리다. per_user 백엔드만 닫는다.
- ste 웹 자체의 승인제·PAT 체계를 바꾸는 것.

## 4. 순서와 이유
**S1 → S2 → S3 → S4.** S1 이 먼저인 이유는 둘이다 — 시크릿 유출은 순서를 기다리지 않고, "죽어도 초록" 을 안 고치면 S2·S3 의 성과를 **판정할 수 없다.** S0 은 S1 의 `ste-doctor` 가 생기는 즉시 cae00 에서 1회.
