# 컨텍스트 노트 — ste × cae00 × Claude MCP

왜 그렇게 판단했는지. 결론만 보면 같은 조사를 다시 하게 된다.

## D-1. 조사 방법과 그 한계
네 갈래(셋업 경로·사용자 Claude 경로·ste MCP 사용성·적대 검토)를 읽기 전용으로 병렬 조사하고, high/fatal 발견 전부를
**반증 검증**에 태웠다(23 에이전트). 결과 **19건 확인·0건 기각** — 다만 검증자가 과장을 여럿 깎았고 그 정정이 계획의
정확도를 만든다(D-3~D-9 의 "정확히는" 이 그것이다). **cae00 은 이 박스에서 닿지 않는다.** 그래서 cae00 실상태는
추론이고, S0 이 "재는 것" 부터다.

## D-2. 요구의 모순은 "같은 실행에 두 뜻을 실어서" 생긴다
"update-all 로 바로" 와 "routine 에 에어갭 실배포 안 섞임" 은 셋업(명시 1회)과 갱신(routine)으로 가르면 둘 다 선다.
지금 코드의 `STE_DEPLOY=1` 게이트는 **존재하지 않는 크론**을 막고 있었다 — 리포·가이드에 update-all 크론이 없다
(`backup-local 03:30`·`koorm @reboot` 뿐). 그래서 "명시 플래그" 하나를 "사람 호출 ∧ 신선도 ∧ 세션" 세 신호로 바꾼다.
검증자 정정: `STE_DEPLOY=1 ./update-all.sh` 는 지금도 재실행(exec env)을 거쳐 2c 까지 이어지므로 `--with-ste` 는
**사실상 환경변수로 이미 존재**한다. 새로 짓는 것이 아니라 이름을 주고 게이트를 세 신호로 바꾸는 일이다.

## D-3. `ste-tunnel` 은 리포가 소유해야 한다
두 리포 전체에서 `ste-tunnel` 은 **언급 넷·정의 0** 이다(가이드 `systemctl --user status`, update-all 힌트, deploy-ste,
update-forges). 런북 §4 도 Teleport 로그인만 다룬다. 즉 손으로 만든 유저 유닛이고, 15812(MCP) 를 여는지는 아무도 모른다.
update-all 이 이제 라우트에서 `STE_MCP_URL=http://127.0.0.1:15812/mcp` 를 유도하는데 — 검증자 정정: **이 유도가 원인이
아니다.** provision 기본값이 원래 같은 값이고, `setup_requests.yaml:64` 도 그 값을 안내한다. 즉 15812 터널은 처음부터
전제였는데 정의된 적이 없다. 리포가 유닛 템플릿을 갖고 `install-ste-tunnel.sh` 가 `transport.env` 값으로 채운다.
services.yaml `only_on` 은 쓰지 않는다 — 그건 프로세스 기동 오케스트레이션이지 ssh 터널의 재접속·linger 를 다루지 않는다.

## D-4. "죽어도 초록" 네 자리 — 정확한 범위
1. 게이트웨이 `/health.backends[k] = (session is not None)` 이라 DOWN 이어도 **키는 남는다.** update-all §5 `calc_missing` 은
   `have = keys` 로 판정 → "빠진 백엔드 없음". DOWN 분기는 `*) 매핑된 서비스 없음(수동 확인)`. 검증자 정정: 완전 무음은 아니다 —
   ⚠ 두 줄과 `/refresh` 요약의 "불통 백엔드 1: ste" 는 찍힌다. **셋 다 비치명이라 exit 0** 이 문제다.
2. §6 자격중계 게이트는 아무 값으로 POST 해 401(www-authenticate 없음)이면 "설정됨" — **불일치와 일치를 구분 못 한다.**
   포털 `start.sh` 와 헤드 `installer/gen-secrets.sh` 가 **각자 난수**를 만드므로 불일치는 정상 경로에서 생긴다.
   검증자 정정: `refresh-code.sh` §8 은 불일치를 warn 만 찍고 exit 0 이다(과장이 아니라 축소였다). → `verify` 엔드포인트 + 정본 하나(포털)로.
3. 15812 프로브가 없다.
4. `access_policy_loaded == 0` 을 아무도 안 본다 — 그 상태면 `_backend_allowed` 가 **전원 허용**이고, 시크릿을 쥔 게이트웨이가
   임의 이메일로 ste 계정을 JIT 생성한다. per_user 백엔드만 "미적재 = 거부" 로 뒤집는다(전면 fail-closed 는 가용성을 위해 일부러 안 한 자리).

## D-5. 시크릿 유출 — 이번 세션이 반쪽만 고쳤다
`sync-sso-secret.sh`(932babe) 는 stdin 으로 넘기지만, **그것을 부르는 것은 direct 분기뿐**이다. teleport 경로는 `refresh-code.sh` §8
의 옛 판(`tr_run_sudo_sh "printf 'STE_SSO_SECRET=%s' '$_sso' >> …"`)을 그대로 돌고, Drive 스테이징 커밋(1d456de)이 바로 그 판이다.
Teleport 는 exec 명령을 감사 원장에 기록하므로(기본 동작 추론) 시크릿이 클러스터 관리자 시야와 헤드 `ps` 에 남는다.
이 시크릿은 임의 이메일로 ste 토큰을 찍을 수 있는 열쇠다. S1 첫 항목이다.

## D-6. 파일은 모델을 거치면 안 된다
`ste_submit_job(files=[{name, content:str}])` — content 를 `.encode()` 해 multipart 로 보낸다. base64·경로·URL·스테이징 옵션이 없다
(리포와 dev VM 배포본 동일). `rest_call` 은 JSON 본문만이라 multipart 우회도 막힌다. 검증자 정정: "수백 KB 상한" 은 코드 상한이 아니라
LLM 인자 크기 추정이고, "30초라 2GB 불가" 의 30초는 청크 간 대기다 — 확정 차단 요인은 게이트웨이 REST 프록시의 `request.body()`
**전량 메모리 버퍼**다. 유일한 스트리밍 경로(포털 `/ste/api/jobs`)는 **ste PAT** 를 요구해 "토큰 하나" 약속이 여기서 깨진다.
→ 사용자 명의 1회용 업로드 티켓(포털 PAT 로 발급) + `submit_job(upload_id)`. 바이트가 모델을 안 거치고 토큰도 하나다.

## D-7. 결과 회수 — `result.zip` 을 `rest_call` 로 부르면 게이트웨이가 죽는다
`get_job_result` 는 목록만 주고 설명이 `result.zip` 을 가리킨다. 모델이 그대로 `rest_call` 하면 게이트웨이가 응답을 통째로
메모리에 받는다 — 검증자 실측: **120MB 응답에 피크 521MB**(bytearray → bytes 복사 → json 시도 → text 한 벌 더). 아직 실사고는
아니다(감사 로그에 0건). 상한을 두고, 텍스트 꼬리용 `get_job_file` 을 따로 둔다. 정식 출구는 ste-sync 상주 에이전트인데
MCP 로 JIT 생성된 계정은 `sync_enabled` 를 켠 적이 없어 기본으로 안 걸린다 — 토글 도구가 필요하다.

## D-8. 권한 게이트 둘은 조용하다
`default_grants: [feat:chat]` 뿐이라 CAEG 밖 사용자는 `feat:api-token` 이 없어 발급 폼이 없고, `plat:smarttwin` 이 없으면
`tools/list` 에서 ste 8종이 **그냥 없다.** 백엔드 DOWN 과 권한 없음이 사용자에겐 같은 모양이다(`list_tool_apps` 를 불러야 갈린다).
검증자 정정: "/tokens 가 RA 카드만" 은 과장 — 다만 왜 발급이 없는지·어디서 요청하는지 **0줄**인 것은 사실이다.

## D-9. TLS — 판정 신호가 하나뿐이다
`/tls/info` 는 `issuer == subject`(자체서명)만 본다. 사내 사설 CA 로 서명돼 있으면 `self_signed=false` → 인증서를 **아예 안 심고**
Node 는 그 루트를 모른다. 그 분기가 코드에 없다(추론 — cae00 인증서 종류는 S0). 자체서명 분기는 버전 미고정 `npx -y mcp-remote`
8단 체인이고 `NO_PROXY` 는 배치 창에만 남는다(메모리 `hwax-mcp-bat-registration-backlog` 의 "8단 체인 재설계 보류" 가 이것).
근본은 사내 CA 서명이지만 그래도 사설 루트면 Node 에 안 실린다 → `needs_ca` 판정 + 발급 CA 체인 내려주기.

## D-10. 신선도 — teleport 경로에는 없다
direct 는 `_man` 지문 대조 후 다를 때만 배포하지만, teleport 는 `STE_DEPLOY` 게이트가 대조보다 **앞**이라 켜면 매번 전부다.
검증자 정정: "Drive 풀 수십 MB 매번" 은 틀렸다 — `rclone copy --checksum` 은 증분이다. 실제로 매번 드는 것은 dist 전개·wheel rsync·
pip --no-index·재기동 2~4회(드레인 없음 → 진행 중 2GB 업로드가 끊긴다). 반대로 dev 가 `pack-staging + push-to-drive` 를 잊으면
낡은 스테이징을 배포하고 sha256 만 맞으면 초록이다 — `build-all-to-drive.sh` 에 ste 가 **없다.**
그리고 `--if-stale` 지문이 `backend/src`·`web` 만 봐서 `backend/mcp_server`·`apps` 가 낡아도 "이미 최신" 이다.
→ 헤드에 `.deployed-commit` 마커, Drive 의 `ste-code.commit` 과 대조(수 KB), 지문 범위 확장, dev 쪽 push 자동화.

## D-11. 전부가 사람 로그인에 매달린다
cae00→헤드 유일 경로(배포 rsync·런타임 터널·게이트웨이 mint·rest_call)가 **하나의 Teleport 신원**에 매달리고, 만료를 보는
프로브가 없으며, tbot 은 계획서(`docs/01-plan/teleport-transport.md` §7-1)에 "가능" 으로만 있다. 검증자 정정: "무인 셋업이
정의되지 않는다" 는 맞지만, 계획서 자체가 이 상태를 "반자동 — 무인 cron 은 포기" 로 규정해 뒀다. 즉 설계된 한계다.
→ S4 는 관리자 협조(tbot)이고, 그 전까지 `tr_session_ok` + `ste-doctor` 의 잔여 TTL 표시로 **보이게** 한다.

## D-12. 하지 않기로 한 것과 이유
- gitignore 파일(`routes.local.env`·`transport.env`·`provision.env`)을 git 에 넣지 않는다 — 박스 비밀·주소다. 제안·검증까지만.
- 전면 fail-closed 로 안 뒤집는다 — 게이트웨이 fail-open 은 가용성을 위해 일부러 잡힌 자리(gateway.py 주석). per_user 만 닫는다.
- ste 승인제·PAT 체계를 안 바꾼다 — 신뢰 근거가 다른 두 로그인을 섞지 않는다(ste `authn.py` 주석).

## D-13. 사용자 결정 (2026-09-25)
1. **셋업/갱신 분리 + 세 신호 게이트 — 채택.** 덧붙인 조건: "새 옵션이 생겼을 때도 유용해야 한다." 그래서 ste 전용 코드가 아니라
   **재사용 가능한 모양**으로 만든다 — 명시 플래그 목록(`--with-<name>`)과 "사람호출 ∧ 신선도 ∧ 전제조건" 판정을 공용 함수로 두고,
   ste 는 그 첫 사용처다. 다음에 에어갭·외부 배포 단계가 생기면 같은 자리에 이름 하나 더하는 것으로 끝나야 한다.
2. **라우트 자동 기록 — 기본 켬.** teleport 박스의 값은 관례가 고정(`127.0.0.1:15810`)이라 안전하다. 끄는 손잡이(`HWAX_STE_AUTOROUTE=0`)만 남긴다.

## D-14. S1·S2 구현에서 배운 것 (2026-09-25)

**Drive 스테이징이 하루 전 판이었다.** 새 `drive-drift.sh ste` 를 처음 돌리자 Drive `1d456de` ≠ dev HEAD
`86c32b0` — 즉 cae00 이 그 시점에 `--with-ste` 를 돌렸다면 **시크릿을 argv 로 넘기는 옛 §8** 을 배포했을
것이다. "dev 가 push 를 잊으면 낡은 것을 배포하고도 초록" 이 가설이 아니라 실상태였다. `build-all-to-drive.sh ste`
로 올려 일치시켰다. 이 채널이 기본 대상에 들어 있어야 하는 이유가 첫 실행에서 증명됐다.

**게이트는 lib 하나, 이름은 등록만.** `hwax_gate <name> --fresh <cmd> --precond <cmd>` — ste 가 첫 사용처고
`HWAX_WITH`(update-all `--with-<name>`)·`<NAME>_DEPLOY=1` 은 이름 무관하게 읽힌다. "모름은 같음이 아니다" 를
lib 에 박았다(신선도 명령이 2+ 로 끝나면 사람이 불렀을 때만 진행하고 사유를 남긴다). 변이로 확인.

**시험이 스스로 걸린 것 둘.** (1) `sed -i` 를 금지하는 시험이 설명 주석의 `sed -i` 예시를 코드로 읽었다 —
주석을 빼고 판정. (2) 내부 IP 가드가 시험의 예시 주소(사설망 대역 둘)를 잡았다 — TEST-NET(`203.0.113.x`)으로.
   이 문서에 그 주소를 그대로 적자 **같은 가드가 이 문서도 잡았다** — 예시라도 추적 파일에는 적지 않는다. 둘 다 가드가 맞고 내가 틀린 경우다.

**`strings` 로 한글을 못 찾는다** 는 어제 배운 것을 이번엔 `grep -a -F` 로 처음부터 피했다.

**doctor 의 direct 신선도.** 헤드 마커(배포 시점 커밋)가 리포 HEAD 뒤인 것은 direct 박스에서 정상이다 —
direct 는 커밋이 아니라 **내용 지문**으로 갱신을 판정하므로(deploy-ste `--if-stale`), 경고가 아니라 정보로 낸다.
teleport 는 커밋이 신선도 키라 경고가 맞다.

**dev 에서 검증 못 한 것.** teleport 분기의 게이트(Drive `ste-code.commit` vs 헤드 `.deployed-commit`,
`tr_run true`)는 lib 단위 시험과 정적 시험까지고, 실주행은 cae00 `update-all --with-ste` 1회가 S0/S2 끝에 있다.
`ste-doctor` 의 `tsh status` 파싱은 dev 에 tsh 가 없어 형식을 못 봤다 — 못 읽으면 "모름" 으로 낸다.

## D-15. S3 실주행에서 배운 것 (2026-09-25)

**맨이름은 남의 도구를 맞힌다.** ste 의 `prepare_upload` 는 reportarchive 에 같은 이름이 있어 게이트웨이가
`ste_prepare_upload` 로 노출한다. 첫 실주행에서 맨이름을 불렀더니 오류가 아니라 **다른 앱의 정상 응답**(JSON 아님)이
돌아왔다 — "실패가 성공처럼 생겼다" 의 또 한 갈래다. 헤더 주석에 접두사 규칙을 적어 둔 것으로는 부족했다(모델은
도구 설명만 본다). 업로드 사슬의 설명·`how` 문장이 서로를 접두사 이름으로 가리키게 했고, 계약 테스트는 설명 본문에서
잡는다(ste 41709e6). 접두사가 붙는 넷: `ste_prepare_upload`·`ste_submit_job`·`ste_list_jobs`·`ste_cancel_job`.
나머지 여덟(`cluster_info`·`list_apps`·`get_app_schema`·`get_job_status`·`get_job_result`·`get_job_file`·
`get_sync_settings`·`set_job_sync`)은 오늘 맨이름이지만 **다른 앱이 같은 이름을 내는 순간 바뀐다** — 설명에
두 이름을 다 적는 규칙은 그래서 전 도구에 적용한다.

**실주행 결과(dev 게이트웨이, per_user PAT).** 티켓 발급 → curl PUT 81B → `ste_submit_job(upload_id)` PENDING →
같은 티켓 재제출 **409** → COMPLETED exit 0 → `get_job_file(slurm.out, tail 3)` 138B·truncated=false →
없는 파일 **404 를 isError 로** → `set_job_sync` 켬. 모델 컨텍스트를 지난 파일 바이트는 0(티켓과 curl 문장뿐).

**게이트웨이 재기동이 반영 경로다.** MCP 서버 설명을 고쳐 VM 에 배포해도 게이트웨이는 기동 때 모은 도구 목록을
들고 있다 — `start.sh restart` 뒤에 `list_tool_apps(app='ste')` 로 설명 본문을 다시 읽어 판정했다.

## D-16. 권한 안내·TLS 판정 (2026-09-25)

**"권한 없음" 과 "그런 앱 없음" 이 모델에게 같은 모양이었다.** `list_tool_apps` 는 권한 없는 앱을 목록에서
빼고 숫자(`hidden_no_access`)만 냈다 — 도구 이름이 새면 모델이 계획에 넣어 실패로만 끝나던 것을 막은 결정이었고
그건 유지한다. 대신 `denied_apps` 에 **라벨·필요 권한(`plat:`/`feat:`)·요청 경로(`/access?need=<키>`)** 만
싣는다. 게이트웨이 그룹 제한(POLICY)뿐이면 `request` 는 None — 포털에서 청할 수 있는 것이 아니라서다.
initialize instructions 9항이 "지어내거나 invoke_tool 로 우회하지 말고 요청을 안내하라" 를 박는다. 실호출
(plat:smarttwin 만 가진 호출자): 열린 앱 3 + 거부 14, 각 거부에 라벨·요청 경로.

**TokenPage 의 요청 경로는 `#api-token` 이 아니라 `?need=`.** 계획은 앵커로 적었지만 AccessPage 의 실제
계약은 `RequireEntitlement` 가 쓰는 `/access?need=<키>`(해당 행 강조 + "권한이 없어 이 화면으로 왔습니다" 배너)다.
같은 문을 쓴다. "이 토큰으로 지금 열리는 플랫폼" 은 `/auth/access` 행에 `tools`(게이트웨이 백엔드 유무) 한 필드를
더해 **도구가 딸린 항목만** 센다 — HEAXHub 허브처럼 타일뿐인 플랫폼은 토큰과 무관하다. 전문가 심의는 기능이지만
게이트웨이 백엔드(hwax-deliberation)가 있어 같은 목록에 든다.

**`self_signed` 는 틀린 질문이었다.** Node 가 죽는 조건은 "자체서명" 이 아니라 **"체인이 공개 루트에 안 닿는다"**
다 — 사내 CA 발급 인증서는 `self_signed=false` 라 안내가 안 뜨는데 Node 는 `UNABLE_TO_VERIFY_LEAF_SIGNATURE` 로
똑같이 죽는다. `/tls/info` 가 `needs_ca` 를 낸다: `openssl verify -no-CApath -no-CAfile -CAfile <certifi>` —
박스의 `/etc/ssl/certs` 를 **끄고** Mozilla 번들만 본다(사용자 PC 의 Node 와 같은 계열). 안 끄면 박스에 심어
둔 사설 CA 가 "공개" 로 읽혀 여기서는 되고 사용자 PC 에서는 안 되는 판정이 난다. `verify_error` 한 줄을 같이 내
만료 같은 다른 원인도 보이게 했다. 판정 수단이 없으면(openssl·번들 없음) 옛 기준(자체서명)으로 물러난다.

**내려 주는 것은 리프가 아니라 발급 CA 체인(`/tls/ca.crt`).** 리프를 심으면 갱신 때마다 사용자 PC 를 다시 만진다.
순서: `TLS_CA_PATH` > 리프 파일의 체인부(fullchain 이면 두 번째부터) > 자체서명 리프 자신. 리프만 있는 사내 CA
발급이면 **체인을 지어내지 않고** 404 + `ca_available:false` — 화면이 "리프로 대신한다, 운영자가 fullchain 또는
TLS_CA_PATH" 를 말한다. 개인키가 같은 파일에 있으면 어느 경로로도 안 낸다(테스트).

**settings.json env 경로는 안 했다.** 계획 5번 후반(`~/.claude/settings.json` env 에 `NODE_EXTRA_CA_CERTS`)은
S0 판정에 걸려 있고, 그 env 가 **Node 기동 전에** 적용되는지는 Windows 실측 없이는 모른다(NODE_EXTRA_CA_CERTS
는 프로세스 시작 때 읽힌다 — 늦게 넣으면 무시될 가능성). 모르는 것을 "우선" 으로 적지 않는다. 체크리스트에 남겼다.

**화면 실확인은 못 했다.** 권한 없는 계정으로 TokenPage 문구를 보려면 feat:api-token 없는 실계정이 필요한데 dev 에
없다. 빌드(tsc)와 코드 경로만 확인했다 — 체크리스트에 그렇게 적었다.

## D-17. 적대 검토 1라운드 — 확인 8·기각 0, 전부 수정 (2026-09-25)

D-16 커밋 셋을 네 차원(정확성·보안·무음 실패·계약)으로 훑고 지적 20건 중 상위 8건을 반박 시도 → **8건 전부 재현**.
빠진 12건은 low 였고 같은 파일에서 싸게 닫히는 것은 함께 넣었다.

**(A) 백엔드가 TLS 경로를 CWD 기준으로 풀었다(high).** `_common.sh` 가 `infra/.env` 를 export 하고 apptainer 가 호스트
env 를 그대로 넘기므로 `.env.example` 의 `TLS_CERT_PATH=infra/tls/hwax.crt` 는 컨테이너에서 `/workspace/backend/infra/…`
로 풀려 없다고 판정됐다 — nginx(gen-nginx-conf)·gen-tls-cert 는 같은 값을 리포 루트 기준으로 읽어 **둘이 어긋났다**.
dev 는 `infra/.env` 에 TLS_ 키가 없어 기본값으로 도망가 안 보였고, env-sync 가 다음 update-all 에 그 키를 채우면 dev 도
같은 상태가 될 참이었다. 종전 `_CERT_PATH` 부터 있던 결함 위에 내가 `_CA_PATH` 를 같은 방식으로 얹고 "TLS_CA_PATH 를
채우라" 고 안내했으니 이번 커밋 범위가 맞다. `_anchor()` — 상대값은 리포 루트 기준(nginx 계약과 동일). 컨테이너 안에서
검토가 쓴 재현 명령 그대로 다시 돌려 `/workspace/infra/tls/hwax.crt` 로 풀리는 것을 확인.

**(B) "리프로 대신한다" 는 거짓이었다(medium).** 사내 CA 가 발급한 리프는 NODE_EXTRA_CA_CERTS 에 넣어도 Node 가 발급자를
요구해 `UNABLE_TO_VERIFY_LEAF_SIGNATURE` 로 죽는다(검토가 Node 20 + mcp-remote 로 실측: 리프=실패, CA=200, 자체서명=자기 자신으로 200).
내가 D-16 에 "리프로 대신" 을 설계 의도로 적었던 것이 틀렸다. 이제 `needs_ca && !ca_available` 은 **연결 불가** 로 말하고
배치 버튼을 잠근다. 같은 이유로 `ca_available` 은 후보 체인이 **리프를 실제로 검증할 때만** true(엉뚱한 `TLS_CA_PATH` 를
"준비됨" 으로 내던 low 건도 여기서 닫힘). 후보: `TLS_CA_PATH` > fullchain 체인부 > 자체서명 리프 자신.

**(C) 게이트웨이 거부 사유를 안 갈랐다(medium ×2 + low).** `_denied_entry` 가 `_ACCESS_POLICY` 만 봐서 게이트웨이 그룹으로
막힌 사람에게 이미 가진 포털 권한을 청하라 했고, 정책 미수신(부팅 직후, 60초 뒤 풀림)을 "그룹 제한" 영구 상태처럼 말했다.
`_backend_allowed` 의 규칙을 `_deny_reason`(gateway_group·policy_not_ready·portal_access)으로 옮기고 사유별 안내 —
portal_access 만 needs·request, policy_not_ready 는 retry:true. 허용/거부 판정은 동치(테스트). 게이트웨이 4a8cf5e.

**(D) 만료 등 다른 verify 실패가 "CA 심어라" 로 나갔다(medium).** `verify_error` 를 아무도 안 읽었다. 백엔드가 `expired`
(cryptography not_valid_after)·`verified`(판정을 실제로 했는가) 를 내고, 화면이 `verify_error` 를 "판정 근거" 로 보이며
만료면 CA 처방 대신 "운영자가 갱신해야 한다" 로 막는다.

**(E) 옛 백엔드 + 새 dist 창(medium).** `tools` 필드가 없으면 전 행이 탈락해 "열리는 플랫폼이 없습니다" 를 사실처럼 냈다 —
dist 는 디스크에서 바로 서빙되고 백엔드는 재기동 전이라 배포 때마다 생기는 창이다. 필드가 boolean 이 아니면 "모름" 이라
섹션을 아예 안 낸다. 같은 창을 위해 `/tls/info` 도 `ca_available` 필드 유무로 옛 백엔드를 알아보고 `/tls/ca.crt` 대신 리프를 쓴다.

**low 에서 같이 닫은 것** — `verify_error` 의 임시 경로·번들 경로 제거(무인증 엔드포인트), DER/PKCS#12 `TLS_CA_PATH` 가 500
이던 것(UnicodeDecodeError), `TLS_CA_PATH` 못 읽으면 `ca_error` 로 이름 붙임, 요청마다 openssl 돌리던 것(파일 mtime 캐시),
시스템 `/etc/ssl/certs` 폴백 제거(사설 CA 가 "공개" 로 읽히는 길). **안 닫은 것** — `/tls/info`·`/auth/access` fetch 실패를
화면이 삼키는 것(이전과 같고, "모름" 으로 두는 편이 낫다고 봄).

**배운 것.** 검토가 잡은 여덟 중 넷은 내가 D-16 에 "그렇게 했다" 고 적은 설계 자체가 틀린 경우다(리프 대체·거부 안내·
verify_error 무소비·CWD). 내 설명이 자신 있게 읽힐수록 라운드가 필요하다.

## D-18. 적대 검토 2라운드 — 확인 10·기각 0, 그중 7건이 1라운드가 만든 회귀 (2026-09-25)

1라운드 수정 커밋(포털 de1fea9·게이트웨이 4a8cf5e)을 같은 네 차원으로 다시 봤다. 수집 24 → 검증 10 → **전부 재현**.
"앞 라운드의 수정 자체가 다음 라운드의 대상" 이 이번에도 맞았다 — 열 중 일곱이 내가 하루 전에 고치며 만든 것이다.

**(G1) CA 후보 검증이 서빙 체인을 버렸다(high, 회귀).** `_ca_bundle` 이 후보를 `-CAfile 후보 리프` 로 **리프만** 검증해,
nginx 가 leaf+int 를 서빙하고 `TLS_CA_PATH` 가 루트인 **표준 사내 PKI** 를 "연결 불가" 로 판정했다. Node 는 서버가
핸드셰이크로 보낸 중간 CA 를 받아 루트만 심으면 되므로(검토가 Node 20 으로 실측: root=200·int=실패·leaf=실패) 1라운드
이전 코드(루트를 그대로 내림)가 옳은 답이었다. 후보 검증에 서빙 체인부를 `-untrusted` 로 준다. 테스트에 root→int→leaf
체인을 넣었다(1라운드 테스트는 루트가 리프를 직접 서명해 이 회귀를 못 잡았다).

**(G2) mtime 캐시가 다섯 가지를 망쳤다(high·medium ×4, 회귀).** 키가 파일 stat 뿐이라 (a) openssl 일시 실패(OOM·타임아웃)
의 `verified=false·needs_ca=false` 오답이 파일 교체 전까지 고정되고 화면은 "공개 CA 정상" 과 바이트 단위로 같았다,
(b) 프로세스 생존 중 만료된 리프를 `expired=false` 로 계속 냈다, (c) `/tls/ca.crt` 는 캐시를 안 타 같은 순간 404 라 두
엔드포인트가 어긋났다, (d) 그래서 `/tls/ca.crt` 는 요청마다 openssl 을 1~3개 띄웠다(DoS 완화가 반만). 하나의 `_state()`
가 info 와 ca 를 함께 계산하고 두 엔드포인트가 그것을 본다 — TTL 60초(시간이 가면 만료가 보인다), **판정 수단이 없던
순간은 고정하지 않는다**(다음 요청이 다시 판정). 테스트: 일시 실패 비캐시·두 엔드포인트 일관·TTL.

**(G3) 화면에 "모름" 이 없었다(medium).** `verified=false` 도 fetch 실패도 "공개 CA 정상" 과 같은 화면이었다 — D-17 에
"모름으로 두는 편" 이라 적었지만 실제 화면에 모름은 없었다. `tlsUnknown` 상태를 두어 노란 경고("판정을 못 했다, 사내 CA 면
아래 등록은 실패한다, 새로 고쳐 다시 확인")를 낸다. 또 잠긴 상태(만료·체인 없음)에서 배치 버튼만 잠그고 **스니펫은 존재하지
않을 인증서 경로를 든 명령을 그대로 냈다** — 스니펫도 함께 감추고 "운영자 조치 뒤 다시 열면 나온다" 로 바꿨다. 만료면
"자체서명 또는 사내 CA" 블록 대신 만료 블록만 낸다.

**(G4) 게이트웨이 사유가 `how` 하나에만 있었다(medium ×2).** 콕 집은 `error`("권한이 없는 앱"), 상위 `note`, initialize
9항, `rest_catalog`/`rest_call`/`_call_tool` 의 `forbidden:` 문구가 모두 사유 무관하게 "포털에서 청하라" 였다 — 모델이
먼저 읽는 지시문이 이 커밋이 고치려던 오안내를 그대로 지시했다. `_deny_text()` 하나가 사유 문장을 내고 넷이 그것을
쓴다. 9항은 사유별 행동을 명시한다(84b5719). 실호출: `forbidden: heaxstep_forge_whoami — … /access?need=plat:stepforge`.

**low 에서 같이 닫은 것** — `TLS_TRUST_BUNDLE` 도 리포 루트 앵커(1라운드가 세 키 중 하나를 빠뜨렸다), 리프만 있을 때
안내가 "루트 CA 까지" 를 말함, `.env.example` 주석이 바뀐 `ca_available` 의미(루트, 검증 필요)를 반영, `ste-doctor` 에
`tls` 행(S0 의 "cae00 인증서 종류" 를 이 행이 답한다: 공개/사설+체인 준비/사설+체인 없음/만료/판정 못 함/무응답).
**결정 기록** — `denied_apps.reason=policy_not_ready` 가 "지금 정책 미수신 창" 임을 인증된 호출자에게 알리는 것은 허용 범위로
둔다(도구 이름·내부 URL 은 여전히 없고, 알려야 재시도가 된다). **안 닫은 것** — `by='area'` 보기의 down 카운트(이전부터),
`TLS_CA_PATH` 번들에 무관한 CA 가 섞여도 통째로 내려가는 것(운영자 파일 그대로).

## D-19. 적대 검토 3라운드 — 확인 10·기각 0, 회귀 9 (2026-09-25)

2라운드 수정(포털 829792b·게이트웨이 84b5719)을 다시 봤다. 수집 20 → 검증 10 → 전부 재현, 그중 아홉이 2라운드가 만든 것.
뿌리는 하나가 컸다 — **"판정 수단이 없으면 첫 후보를 검증 없이 준다"**(2라운드에서 넣은 분기). 이것이 여섯 건을 낳았다.

**(H1) 검증 안 된 후보를 "준비됨" 으로 냈다(3·4·7·8·10·9).** 공개루트 판정(첫 openssl)은 됐는데 CA 후보 검증(둘째)만
일시 실패하면 `verified=true` 라 60초 캐시되고, 엉뚱한 `TLS_CA_PATH` 가 `/tls/ca.crt` 로 내려갔다. `ca_verified=false`
는 아무도 안 읽었다. 화면은 노란 "모름" 과 회색 "CA 체인을 심는다" 를 **동시에** 내고 실제 배치는 검증 안 된 CA 를 넣었다
— 경고문과 동작이 반대. 고침: 판정 못 하면 **주지 않는다**(`ca_available=false`, "판정 수단 없음"), `verified` 는 두 판정
모두를 뜻하고(`ca_verified` 필드 삭제), 못 한 순간은 5초만 보류(요청마다 되살리지 않되 곧 다시 판정), 화면은 "모름" 이면
배치·스니펫을 **잠그고** 다른 안내 블록을 안 낸다. 자체서명 포털에서 openssl 이 죽은 5초 동안 등록을 못 하는 대가는 받아들인다.

**(H2) 리프만 서빙하는 경우 "루트 CA 를 TLS_CA_PATH 에" 가 틀렸다(1).** 서버가 중간 CA 를 안 보내므로 루트만으로는 Node 도
못 믿는다(검토가 Node 20 으로 실측: leaf-only+root 실패, leaf-only+int+root 성공, leaf+int 서빙+root 성공). D-18 의 "루트만
심으면 된다" 는 leaf+int 서빙일 때만이다. 안내를 서빙 모양에 맞게 갈랐다 — 리프만: "발급 체인(중간 CA + 루트), 루트만으로는
안 된다" · 체인 있음: "루트까지 닿아야". 힌트는 발급자 결손(`issuer`)일 때만 붙는다(만료에 "루트까지" 를 붙이던 6).

**(H3) 만료는 리프 날짜만 봤다(6).** 중간 CA 만료·아직 유효하지 않음은 openssl 이 잡는데 `expired=false` 라 화면이 "체인 없음"
처방을 냈다. openssl 오류의 `expired`/`not yet valid` 도 `expired` 로 센다. 번들·인증서 파일을 못 읽은 openssl 실패(rc=1
"Error loading file")는 "판정" 이 아니라 "판정 수단 없음" 으로.

**(H4) doctor 가 `ca_error` 를 절대 못 보여 줬다(2).** `verify_error or ca_error` 인데 `needs_ca` 면 앞이 늘 차 있다 — 빨간
행이 "왜 체인을 못 쓰나" 를 한 번도 말하지 않았다. 둘을 갈라 분기마다 맞는 것을 낸다. 같은 스크립트의 §3 과 `update-all` §6 이
시크릿을 `curl -H` **argv** 로 넘기던 것(ps 에 보임, D-16 의 stdin 규율과 어긋남)도 `curl -K -`(stdin 설정)로 바꿨다 — 실측 204.

**(H5) REST 프록시 403 이 사유를 안 탔다(5).** `_deny_text` 소비처가 MCP 쪽 넷뿐이었다. `RestProxy(deny_text=)` 훅으로
다섯 번째를 이었다(게이트웨이 eb765cd). 포털 절차 판정기(`judge.py`)는 모든 `forbidden:` 을 재시도 불가로 봤는데, 정책 미수신
문구("잠시 뒤 다시")는 재시도 가능(`unavailable`)으로 가른다.

**안 닫은 것(기록)** — doctor 의 `warn`(모름)은 exit 0 이고 `update-all` §6 은 doctor 를 부르지 않는다: §6 은 자기 게이트
(verify·15812·정책)로 판정하고 doctor 는 진단 화면이다 — 계획 문구("§6 이 이것을 부른다")보다 이 분리가 낫다고 보고 유지.
`TLS_INFO_TTL`·`TLS_TRUST_BUNDLE` 은 개발 손잡이라 `.env.example` 에 안 넣는다. 잠긴 화면의 챗 curl 스니펫은 토큰 확인용이라 둔다.

**세 라운드 합계** — 확인 28·기각 0. 라운드마다 앞 라운드의 수정에서 회귀가 나왔다(2라운드 7/10, 3라운드 9/10). 4라운드는
돌리지 않는다 — 이번 수정은 분기 **삭제**·문구·훅 추가라 새 기계를 넣은 것이 아니고, 테스트가 회귀 케이스(중간 CA·둘째 openssl
실패·리프만+루트)를 잡는다. cae00 S0 실주행이 다음 검증이다.

## D-20. "있는데 안 켠 기능" 장부 — 옵션·설정이 없어 건너뛴 것은 전부 로그에 (사용자 지시, 2026-09-25)

**지시.** "기능이 있는데 옵션 없어서 셋업 안 된 것들도 전부 로그에 표시되게" — `--with-ste` 같은 옵션이나 `routes.local.env`·
`.env` 값이 없어 건너뛴 단계가 조용히 지나가면, 사용자는 그 기능이 리포에 있는 줄도 모른다. 실패(✗)·경고(⚠)와 섞이면
"깨졌다" 로 읽히니 표식을 따로 둔다(○ 자주색).

**구현.** `infra/scripts/lib/skip-ledger.sh` — `hwax_skip <이름> <왜> <켜려면>`(즉시 한 줄 + 장부), `hwax_skip_record`(장부만,
호출자가 이미 사유를 찍었을 때), `hwax_skip_summary`(끝에서 전부 다시). 장부는 **파일**(`HWAX_SKIP_LEDGER`, update-all 이
`mktemp` 로 만들어 export) — 자식 스크립트(deploy-ste·게이트 lib·env-sync)가 같은 파일에 적어야 한 곳에 모인다.
- 게이트 lib: "사람 호출 아님"(→ `--with-<name>` 또는 `<NAME>_DEPLOY=1`)·"전제조건 실패"(→ 전제를 세운 뒤 `--with-<name>`)는
  장부에. "이미 최신" 은 안 켠 것이 아니라 적지 않는다.
- deploy-ste `--if-stale`: 게이트가 막으면 **exit 3** — 0 이면 update-all 이 "배포됨" 과 못 가른다. update-all 2c 는 3 을
  "장부에 적혔다" 로 읽는다(실패 아님).
- update-all: 1c env-sync 없음 · 1d 자동 라우트를 `HWAX_STE_AUTOROUTE=0` 으로 끈 경우 · 2c deploy-ste 없음 · AIDataHub 동기화
  없음 · agent-server 리포 없음 · §6 "ste 라우트 미설정 — 건너뜀"(전에는 **초록 ✓** 였다) — 전부 `hwax_skip`.
- env-sync: "값을 정해야 한다" 로 주석 처리한 키(비밀·자리표시자)와 상한 초과로 미적용한 묶음도 장부에 — 그 설정이 켜는 기능은
  꺼져 있다는 뜻이다.
- 요약은 성공·실패 어느 쪽 끝에서도 나온다(판정 분기보다 앞). **실측**에서 env-sync 키가 28개 풀려 나와 정작 기능 항목이
  묻혔고 같은 키가 셋 겹쳤다 → 요약은 중복을 지우고 "설정 …" 항목은 **키 이름만 한 줄**로 접는다(키별 줄은 1c 에 이미 있다).
  dev 실측: `○ 있는데 안 켠 기능 1개 · 값 미정 설정 26개` + ste 라우트 한 줄 + 키 목록 한 줄.

**알고 둔 것.** env-sync 가 주석 문장을 키로 읽는 잡음(`Empty`·`provider`)이 목록에 섞인다 — env-sync 파서의 기존 동작이라
여기서 안 고쳤다. 리포 경로가 절대경로로 찍히는 것도 env-sync 의 기존 표기다(로그에만 나온다).

## D-21. TokenPage 권한 화면 — 실계정으로 보고 하나 고쳤다 (2026-09-25)

D-16·D-17 에서 "실계정이 없어 빌드·코드 경로만 확인" 으로 남겨 둔 것을 닫았다. **실 DB 를 건드리지 않는 방법** —
`USER_STORE_PATH` 를 임시 파일로 주고 `SERVE_FRONTEND=1` 로 빈 포트에 uvicorn 을 띄운다(`frontend/dist` 를 그대로
서빙하므로 SPA 도 돈다). 계정을 만들어 권한을 `PATCH /auth/access/users/<email>` 로 바꿔 가며 플레이라이트로 본다.
끝나면 프로세스·임시 파일을 지운다. 걸린 것 넷 — `.local`·`.test` 는 EmailStr 이 거부(예약 TLD, `@corp.com` 사용),
`serve_frontend` 기본값이 false, SPA 경로는 `/token` 이 아니라 **`/tokens`**, `pkill -f "port 8792"` 는 **자기 명령줄**을
맞혀 셸을 죽인다(exit 144 — 포트에서 PID 를 얻어 죽인다).

**본 것 셋.**
- `feat:api-token` 없고 `plat:reportarchive` 만: "연결 설정" 화면에 새 문장과 `/access?need=feat:api-token` 링크가 뜨고,
  누르면 그 행이 강조되며 배너가 "API 토큰 · MCP 개인 연결 권한이 없어 이 화면으로 왔습니다" 라고 정확히 말한다.
- 관리자(전부): "이 토큰으로 지금 열리는 플랫폼" 에 칩 17개(게이트웨이 백엔드가 있는 플랫폼 16 + 전문가 심의),
  "닫힌 것" 줄 없음. 타일뿐인 HEAXHub 허브·SPDM·Knox 는 안 들어간다 — `tools` 필드 설계가 의도대로 동작한다.
- `feat:api-token` + `plat:smarttwin` 만: 칩 1개, "닫힌 것 16개 — …" 목록.

**고친 것(이 검증이 아니면 안 보였다).** 닫힌 것이 여럿일 때 링크가 `need=<첫 항목>` 으로 가서 `/access` 배너가
"AI 데이터 허브 권한이 없어 이 화면으로 왔습니다" 라고 **사실과 다른** 말을 했다(사용자는 일반 링크를 눌렀을 뿐이다).
하나일 때만 그 행을 집고, 여럿이면 `/access` 로 보낸다 — 실측 재확인: 16개→`/access`, 1개→`need=plat:mxwhitepaper`.

## D-22. cae00 배포 가이드가 사람을 잘못 이끌고 있었다 — 51건 대조 (2026-09-26)

"dev 는 다 됐나" 를 확인하다 `docs/cae00-deploy-guide.md`(387줄)가 오늘 배선과 어긋난 것을 봤다. cae00 에서 사람이
**그대로 따라 하는** 문서라 코드보다 위험하다 — 네 갈래(단계표·ste 절·데이터/Drive·게이트웨이/주의)로 전수 대조: 지적 51건,
상위 6건 반박 검증 **전부 확인**, 나머지는 근거(파일:줄)와 함께 받았다.

**가장 나빴던 셋.**
- "**`update-all` 로 안 되는 것: STE**" · "§6 에서 프로브만 한다(비치명) · `deploy-ste.sh` 를 호출하지 않는다" — 2026-09-23
  이후 사실이 아니다. 2c 가 부르고, §6 의 ste 자격중계·15812 는 **치명**(exit 1)이다.
- "**`--with-ste`(현재 미적용) · 구현은 플래그 파싱 2줄이면 된다**" + 예시 스니펫 — 이미 구현돼 있어서, 문서를 따라 그
  스니펫을 넣으면 2c 와 **이중 트리거**가 된다.
- 터널을 "루프백 15810" 한 포트로 적었다 — **15812(ste MCP)** 가 없으면 ste 도구 8종이 통째로 안 뜬다. 문서에 15812 가
  한 번도 없었고 `install-ste-tunnel.sh` 도 0건이었다.

**문서가 아니라 코드였던 것 하나(고쳤다).** `update-forges.sh`(무인자)는 기본 대상에 `ste` 가 있는데 `deploy-ste.sh` 를
`--if-stale` **없이** 불러 공용 게이트를 통째로 우회했다 — "경량 표적 갱신(수 분)" 을 부른 사람이 에어갭 헤드 재배포·재기동을
무조건 받는다. 의도(=인자 없이 부름은 사람이 갱신하라 한 것)는 맞지만 **딸려 온 ste** 에까지 적용된 것이 틀렸다. 이름을 댔는가로
가른다 — `update-forges.sh ste` 는 전면 갱신, 무인자는 게이트 경유(`--if-stale`). 가짜 `deploy-ste.sh` 로 인자를 받아 적어
두 경로를 가르는 시험을 붙였다. `update-all.sh` 의 "teleport 는 STE_DEPLOY=1 없이는 안 돈다" 주석도 게이트 도입 뒤로 낡아 고쳤다.

**고친 방식.** 낡은 서술을 지우고 지금 사실로 바꿨다 — §0 요약(안 되는 것 = 최초 반입·터널 유닛·프론트 빌드 셋),
단계표에 0a·0b·1c·1d·2b·2c·3.5·6b·7 추가, §6 치명 목록 전개, `NO_GIT_RESET` 의미 역전 수정(stash 는 **기본** 쪽이다),
AIDataHub 채널(JSONL 아니라 **DB 덤프**), 심의 좌석(MCP **10**·웹 **9**, 솔버 좌석 유무로 다르다 — 수로 판정하지 말고 목록으로),
cae00 에서 `pnpm build` 를 지우고(npm 미도달) Drive 아티팩트 경로로, `access.yaml` 이 권한 정본이라는 것, 표식 셋(✗·⚠·○),
그리고 2026-09-26 반영분 절(1회 셋업 명령·TLS 판정·ste 도구가 안 뜰 때의 순서).

**규약도 바꿨다 — 근거를 줄번호가 아니라 배너 문자열로 가리킨다.** `update-all.sh` 가 1,400여 줄로 자라며 인용 여덟 개가
전부 엉뚱한 코드를 가리키고 있었다(§6 으로 인용한 402-420 은 지금 §5 이고, ste 로 인용한 485-486 은 kooremapper 토큰 추출이다).
줄번호는 밀리지만 `hr "2c) ste 코드 최신화"` 는 안 밀린다. 머리글에 **대조 시점**을 박아 다음 사람이 낡음을 판정할 수 있게 했다.
박스 상태를 날짜 박아 적던 메모("cae00 에 staging 만 없음", 08-26)는 지웠다 — 상태는 적는 것이 아니라 `ste-doctor --report` 로 잰다.

## D-23. 0b 잠금이 데몬에게 fd 를 물려줘 update-all 을 영구히 막았다 (2026-09-27, cae00 실측)

deploy-ste 성공 직후 `update-all` 이 "✗ update-all 이 이미 돌고 있다(/tmp/hwax-update-all.….lock)" 로 거부됐다 — 돌고 있는 것은 없었다.
0b 는 `exec 9>"$_LOCK"; flock -n 9` 였고, **fd 9 를 자식이 물려받는다.** update-all 이 띄운 데몬(에이전트서버 `nohup … &`·apptainer
instance 등)이 그 fd 를 쥔 채 살아 있으면 update-all 이 끝나도 flock 은 풀리지 않는다. cae00 의 첫 실행(§F 09-27)이 데몬들을 띄웠고,
그 뒤의 모든 실행이 거부될 판이었다. dev 에서 못 본 이유 — dev 는 09-25 실주행 한 번 뒤 다시 돌린 적이 없다(잠금 파일 자체가 없다).
dev 재현: `bash -c 'exec 9>L; flock -n 9; (sleep 4 &)'` 뒤 `flock -n L true` → busy, 보유자는 `sleep`.

고침(0b): flock(1) 을 **부모로 남긴다** — `HWAX_UPDATE_ALL_LOCKED=<lock> flock -n -E 75 -o "$_LOCK" bash "${BASH_SOURCE[0]}" "$@"`.
`-o` 는 명령(이 스크립트)에 fd 를 닫아 넘기므로 데몬이 받을 fd 가 없고, 잠금은 flock 프로세스가 스크립트 수명만큼 쥔다(실측: 안에서 보유자
comm=flock·busy, 데몬만 남은 밖에서 free, 명령 rc 전달, 충돌 rc 75). §1 의 `exec env UPDATE_ALL_REEXEC=1 bash update-all.sh` 재실행은
같은 PID 라 잠금이 이어지고, 환경변수 가드로 다시 잡으려 들지 않는다. **자가치유**: 충돌(75)이면 `/proc/*/fd` 에서 잠금 파일을 연
프로세스를 본다 — flock 도 update-all 도 없고 데몬만 있으면 옛 판이 물려준 fd 라 잠금 파일을 지우고 새 inode 로 다시 잡는다(옛 보유자는
"(deleted)" inode 를 쥔 채 무해). 보유자가 하나도 안 보이면(다른 사용자) 모름이라 거부한다. 로그엔 pid·comm 만(남의 인자는 토큰일 수 있다).
`flock` 이 없으면 잠금 없이 경고만 하고 진행한다(종전엔 command not found=rc 127 을 '이미 돌고 있다' 로 읽었다).

시험은 텍스트가 아니라 **실제 프로세스**로: 겹침 거부(rc 3) · 데몬을 띄운 뒤에도 잠금 자유 · 옛 판 모양의 고아 fd 만 있으면 자가치유
문구+진행 · 재실행(exec)·인자·종료코드 전달. 변이 4/4(−o 제거·자가치유 제거·가드 제거·잠금 제거 각각 해당 시험 실패). 스위트 761.
교훈은 [[bash-flock-fd-inherited-by-daemons]] 로.

## D-24. 0b 잠금 2차 — 검토가 잡은 셋(치유 경합·kill 이 안 멈춤·Ctrl-C 가 잠금만 풀음)과 다시 짠 모양 (2026-09-27)

D-23 의 판(flock(1) 부모 + 자가치유)을 적대 검토에 넣었더니 확인 6(고유 3)·기각 0. ① **치유 경합**: 고아 fd 상태에서 둘을 10ms 차로
띄우면 둘 다 stale 판정 → 서로의 새 잠금 파일을 지우고 **둘 다 진행**(8회 중 6회). ② **`kill <pid>` 가 안 멈춤**: 사람이 보는 PID 는
기다리기만 하는 바깥 bash 라 그것만 죽고 flock+본문은 떨어져 끝까지 돌았다(잠금은 BUSY, 재실행은 rc 3). ③ **Ctrl-C 가 잠금만 풀음**:
flock(1) 은 INT 에 바로 죽는데 본문 bash 는 자식이 INT 를 삼키고 정상 종료하면(rclone·rsync 류) 계속 돈다 — 실행은 계속·잠금은 해제·
프롬프트는 복귀라 바로 재실행하면 겹친다. 셋의 뿌리는 하나 — **잠금 보유자(flock)와 실행자(bash)가 다른 프로세스**라 수명이 갈린다.

다시 짠 모양: 잠금은 **바깥 bash 가 fd 9 로** 쥐고 본문은 같은 스크립트를 자식으로 돈다. 자식엔 `9>&-` 로 fd 를 닫아 넘겨 데몬이
못 물려받고, 바깥은 자식이 끝날 때까지 `wait` 한다 → 잠금 수명 = 본문 수명. 신호: INT(Ctrl-C)는 그룹 전체에 이미 가므로 바깥은
`trap ':'` 로 살아만 있고(넘기면 두 번 받은 자식 bash 가 INT 를 삼킨 뒤 죽는다 — 실측), TERM·HUP 은 바깥만 받으니 자식에게 넘긴다.
획득 단계(열기→시도→스캔→치유→재시도)는 `${LOCK}.heal` 잠금 아래 하나씩 — 경합 ①이 닫히고, 서로의 미획득 fd 를 '진짜' 로 보아
둘 다 물러나는 것도 막는다. 스캔 파이프(find|cut|sort)는 fd 8·9 를 닫고 돈다(안 닫으면 자기 자식들이 보유자로 잡혔다 — 첫 시험판).
가드 값은 `<잠금경로>:<바깥 PID>` 로 자식이 PPID 와 대조 — 데몬으로 새어 나간 변수로는 잠금을 못 건너뛴다.

**함정 하나 더(실측).** `&` 로 띄운 자식은 job control 없는 셸이 INT·QUIT 를 **무시**로 물려준다(POSIX). 그대로면 Ctrl-C 가 본문 어디에도
닿지 않아 sleep 이 INT 를 받고도 살았다. 비대화 bash 는 진입 시 무시된 신호를 되돌릴 수 없으므로 python3 이 기본 처리로 되돌린 뒤 같은
PID 로 bash 를 exec 한다. 시험도 같은 함정을 밟았다 — `bash -c 'trap … INT; sleep 5'` 는 마지막 명령 exec 최적화로 sleep 자체가 되어
trap 이 사라진다(`; true` 를 붙인다).

시험 12(실프로세스): 겹침 rc 3 · 데몬 비상속 · 고아 fd 치유 · **경합 15회 정확히 하나만 진행** · kill 로 본문 정지+잠금 해제 · Ctrl-C 가
본문을 멈춤 · Ctrl-C 를 삼킨 자식 뒤에도 잠금 유지+바깥 대기 · 보이지 않는 보유자 거부(잠금 파일 보존) · 새어 나간 가드 변수 무효 ·
flock 없음 경고 후 진행 · 옛 판 업그레이드 · exec 재실행/인자/rc/stdin. 변이 8/8. 스위트 771. 남긴 것(low): 옛 판이 'update-all' 없는
이름(심링크)으로 도는 중이면 stale 오판 · 롤백 뒤 첫 실행 rc 3(가이드에 적음).

## D-25. 0b 잠금 3차 — 2라운드가 잡은 셋: kill 이 단계를 고아로 남김·옛 판 하위 단계를 데몬으로 오판·중간 판에서 오는 첫 회 rc 3 (2026-09-27)

D-24 판(바깥 bash 보유 + TERM 을 자식 bash 에 넘김)을 다시 검토에 넣었더니 확인 6(고유 3)·기각 0. ① **kill 이 단계를 고아로 남긴다** —
자식 bash 는 TERM 에 즉사하지만 그 순간 전경으로 돌던 단계(deploy-all-from-drive·provision --force — 잠금이 직렬화하려는 바로 그 일)는
신호를 못 받아 끝까지 돌고, 바깥은 자식이 죽자마자 잠금을 놓아 즉시 재실행이 겹쳤다(sub.log 에 두 실행의 단계가 교차). D-23 판(flock 부모)은
하위 단계가 fd 9 를 물려받아 우연히 잠금을 지켰으니 이 축에선 후퇴였다. ② **옛 판의 하위 단계를 데몬으로 오판** — 옛 판 실행이 kill 되면
하위 단계가 fd 9 를 쥔 채 도는데 cmdline 에 update-all 이 없어 '고아' 로 분류돼 잠금을 지우고 겹쳤다. ③ **중간 판에서 오는 첫 회 rc 3** —
09-27 중간 판(flock -o 부모, 가드 값 `<lock>`)의 본문이 §1 에서 이 판으로 exec 하면 가드 형식이 달라 잠금을 잡으려 들고, 잡은 것은 자기 부모
flock 이라 '이미 돌고 있다' 로 죽었다(cae00 이 그 판을 pull 했으면 정확히 이 경로).

고침: ① 본문(자식)이 `trap 'exit 143' TERM; trap 'exit 129' HUP` — bash 는 전경 명령 중 trap 을 미루므로 **진행 중 단계가 끝난 뒤** 멈추고,
바깥은 그때까지 잠금을 쥔다(kill = 단계 뒤 정지, 즉시 정지는 Ctrl-C). 시험은 하위 단계(bash -c 루프)를 두고 kill 뒤 잠금 BUSY·SUBDONE·고아 없음을
본다. ② 보유자 판별에 update-all 이 전경으로 돌리는 하위 단계 이름(infra/scripts/·deploy-all-from-drive·provision-config·deploy/*.sh·
sync-from-drive·data-migrate)을 '진짜' 로 넣었다 — 그 경우 rc 3 으로 기다리게 한다. ③ 부모 comm=flock 이고 가드 값이 `<lock>` 이면 본문으로
간다(부모가 잠금을 쥔 채 우리를 낳은 것). 미검증 중 반영: 보유자가 안 보이면 한 번 더 시도 뒤 거부(스캔 60ms 사이에 앞 실행이 끝난 경우) ·
자식이 INT 로 죽었으면 바깥도 `kill -INT $$` 로 신호로 죽어 `;` 체인이 끊긴다(관례) · 치유 파일을 숨김 이름으로(`hwax-update-all.*` 를
지우는 손에 같이 지워지면 획득 직렬화가 사라진다) · 잠금 경로를 TMPDIR 에서 떼어 /tmp 고정(HWAX_LOCK_DIR 은 시험용) · python3 없음은 경고 후 진행 ·
`_child=""` 초기화 · §1 exec 전 장부 mktemp 정리 · 글롭 문자 경로 시험(`a[1]b`). **롤백 방향은 실측으로 못 박았다** — 새 바깥 아래서 본문이
옛 판(exec 9>lock)으로 exec 하면 옛 0b 가 바깥의 잠금에 막혀 rc 3(검토가 rc 0 이라 한 것은 방향을 헷갈린 것), 두 번째 실행은 정상.

**함정(실측).** case 패턴을 변수에 담으면 `|` 가 대안이 아니라 글자다 — 진짜 보유자 전부를 고아로 봤고 시험 4개가 그걸 잡았다. 변이 검사가
"통과" 로 나온 항목(flock 부모 인식 제거 → 초록)이 실은 이 결함 때문이었다 — 패턴을 고치자 그 변이도 빨갛게 됐다. 변이가 초록이면 시험이 아니라
**시험이 타는 코드**부터 의심한다. 시험 16(실프로세스), 변이 10/10, 스위트 776.

## D-26. 0b 잠금 4차 — 3라운드: timeout 이 Ctrl-C 를 삼킴·kill 이 짝 명령을 반으로 가름·상대경로 하위 단계 (2026-09-27)

3라운드(504e42b 대상) 확인 6(고유 4)·기각 0. ① **`timeout 900 deploy-ste.sh` 에 Ctrl-C 가 닿지 않는다** — GNU timeout 은 `--foreground`
없이 명령을 새 프로세스 그룹에 넣는다(setpgid). 터미널 INT 는 전경 그룹에만 가므로 deploy-ste 는 900초까지 그대로 돌고, 본문 bash 는 전경
자식이 정상 종료했으니 '처리됐다' 로 보고 다음 §로 넘어가며, 바깥은 rc≠130 이라 정상 종료한다. 진짜 pty 에 ^C 를 써도 같았다. 갈 곳이 kill -9
뿐이고 그러면 단계 고아+잠금 해제 = 겹침. → `timeout --foreground`(타임아웃 시 deploy-ste.sh 자체엔 TERM 이 간다). 시험이 실 스크립트의
timeout 호출 전부에 --foreground 를 요구한다. ② **kill 이 '단계' 가 아니라 '단순 명령' 뒤에 멈춘다** — 본문의 `trap 'exit 143' TERM` 은 다음
명령 경계에서 발화하므로 §5 `"$SVC" down` → `up`, mxwp `instance stop` → `up`, run_smoke `kill → 폴링 → start.sh --bg` 가 반으로 갈려
게이트웨이·에이전트서버가 내려간 채 rc 143 으로 끝났다(재현: SVC_DOWN_DONE 뒤 SVC_UP 없음). → trap 은 **플래그**만 세우고(받은 즉시 한 줄
찍음), 멈추는 자리는 **다음 § 머리 `hr()`** 다 — 진행 중인 §는 짝 명령까지 끝까지 간다. 바깥도 신호를 넘길 때 "받음 — 진행 중인 §가 끝나면
멈춘다" 를 찍는다(수 분짜리 단계에서 반응 없음으로 읽고 kill -9 로 가던 것). ③ **상대경로 하위 단계** — 보유자 판별 `*/deploy/*.sh*` 는 앞
슬래시를 요구해 deploy-all 이 실제로 쓰는 `bash deploy/apptainer/start.sh`·`./scripts/up.sh`·`./boot.sh`·`*-from-drive.sh` 를 데몬으로 봤다 →
패턴을 상대경로·이름으로 넓히고 아홉 가지 이름을 parametrize 로 잰다. ④ kill 시험의 `pgrep -f "seq 1 6"` 이 박스 전역 매치라 병렬 실행에서
빨갔다(변이 검사의 '죽였다' 오판까지) → tmp 이름 토큰으로 좁힘. 미검증 반영: 치유 잠금의 '열기 실패' 와 '15초 만료' 문구 분리 · 가짜 스크립트
헤더에 `set -uo pipefail`·장부 mktemp·실 hr() 을 넣어 초기화 줄들의 보호를 세움 · 새어 나간 가드 시험이 본문이 실제로 흘리는 값을 캡처해 쓴다 ·
python3 없는 경로도 데몬 비상속·stdin 을 잰다 · kill 시험 TERM/HUP parametrize. 남긴 것(low): 기동 직후 ~10ms 창의 Ctrl-C 유실(python3 shim 전) ·
`kill -INT <pid>` 는 조용한 no-op(가이드에 TERM 을 쓰라고 적음). 시험 42(실프로세스), 변이 9/9(초기화 한 줄은 신호 창 문제라 재현 불가), 스위트 786.

## D-27. 0b 잠금 5차 — 4라운드: §1 재실행이 정지 플래그를 버림·timeout 만료가 자식을 남김·root 소유 파일·pgrep 토큰 (2026-09-27)

4라운드(4fa33e0 대상) 확인 6(고유 4)·기각 0. ① **§1 의 exec 재실행이 정지 플래그를 버렸다** — 플래그가 셸 변수라 `exec env UPDATE_ALL_REEXEC=1
bash …` 뒤 새 이미지의 0b 가 0 으로 다시 시작했다. §1(git fetch/reset, cae00 은 프록시라 김) 중 받은 kill 은 '멈춘다' 두 줄을 찍고 §2 이하를
끝까지 돌았다. → 플래그를 **환경변수** `HWAX_UPDATE_ALL_STOP` 으로, 첫 진입(재실행 아님)에만 0 으로 시작. ② **timeout --foreground 만료(124)
가 자식을 남긴다** — --foreground 는 명령 하나에만 TERM 을 주고 그 자식(rsync·ssh)은 두므로, deploy-ste 는 죽고 rsync 는 살아 전송을 계속하는데
본문은 '중단했다' 고 찍고 잠금을 풀어 재실행이 살아 있는 전송과 겹쳤다(옛 `timeout` 은 그룹 전체를 죽였으니 4차가 만든 회귀). → 단계를 띄울 때
`HWAX_STEP_ID=<표식>` 을 환경에 실어 두고, 124 면 `_reap_step` 이 `/proc/*/environ` 에서 그 표식을 가진 살아 있는 프로세스를 찾아 TERM→3초→KILL.
③ **root 소유 잠금·치유 파일** — 같은 리포를 sudo 로 한 번 돌리면(AIDataHub desudo.sh 가 그 뒤처리다) /tmp 에 root 소유 두 파일이 남아 이후 모든
실행이 `exec 8>` EACCES 로 rc 3 인데 문구는 '/tmp 권한' 을 가리켰고 가이드는 치유 파일을 지우지 말라 했다. → 문구에 소유자·내 이름·`sudo rm -f
<둘>` 을 넣고 가이드에 예외를 적었다. ④ kill 시험의 pgrep 토큰이 `tmp_path.name` 이라 pytest 세션을 가로질러 같았다(병렬이면 3/3 빨강, 변이
검사의 '죽였다' 오판) → uuid. 미검증 반영: **삼켜진 Ctrl-C** — rsync 는 INT 를 잡아 rc 20 으로 정상 종료하므로 종전엔 표시 없이 다음 §로
이어졌다. 본문에 INT trap 을 두어 단계가 INT 로 죽었으면(`$?`=130) 종전처럼 바로 죽고, 삼켰으면 받아 두고 다음 § 머리에서 멈춘다 · hr 의 정지가
✗ 목록·○ 요약·장부 정리를 건너뛰던 것 → 멈출 때 지금까지의 ✗ 와 ○ 요약을 내고 '어느 § 부터 하지 않았다' 를 말한다 · 마지막 § 뒤에 kill 이 오면
'남은 §가 없어 끝까지 갔다' 한 줄 · 보이지 않는 보유자 재시도 조항의 시험(보유자가 스캔 중 끝나는 시간표) · timeout 검사 정규식이 `-k`·변수 초
꼴도 잡고 주석은 뺀다 · `scripts/down.sh` parametrize.

**함정 둘(실측).** 시험 하네스가 실 `hr()` 을 첫 `printf` 줄까지만 잘라 함수가 닫히지 않았다(hr 에 printf 를 하나 더 넣자 34개가 한꺼번에 빨강 —
"unexpected end of file"). 그리고 `pgrep -f <글자>` 는 시험을 띄운 셸의 cmdline 에 같은 글자가 있어 **자기 자신을 센다**(alive_after=1 로 보임) —
같은 이유로 `pkill -f` 가 내 셸을 죽였다(두 번째). 프로세스 생존은 pid 파일 + `kill -0` 으로 잰다. 변이 하나가 초록으로 남은 이유도 시험이었다 —
재시도 시험의 보유자(0.3초)가 0b 의 **첫 find(물려받은 fd 찾기, 셸 shim 으로 0.6초)** 동안 끝나 첫 시도가 성공했다. 시간표를 적어 두고 보유자를
1.0초로. 시험 49(실프로세스), 변이 11/11, 스위트 793. 남긴 것(low): 중간 판(flock 부모)에서 오는 첫 회에 flock 에 TERM 이 가면 본문은 계속·잠금은
해제(한 번뿐인 전환) · 기동 직후 ~10ms Ctrl-C 창 · `kill -INT <pid>` no-op.

## D-28. cae00 두 번째 update-all — RA 는 끝났고, ste 빨강 둘의 뿌리는 경로 관례와 헤드 상태 (2026-09-27)

사용자가 붙인 update-all 꼬리(새 0b 로 첫 실행 — 잠금 거부 없음). **RA 완료**: §5 가 "주소 드리프트: reportarchive — config 는 127.0.0.1 인데
RA_HOST 는 <A>" 를 잡아 실제로 재프로비저닝했고(9월 22일 이후 처음), §6 의 RA 포털 로그인 콜백이 **303** — 라우트·RA 새 판·SSO 켜짐·도달
네 조각이 다 섰다. RA MCP 도구 스모크 3/3. 사람이 RA 담당에게 넘길 숫자를 update-all 이 찍었다(portal-callback → 303 · 포털 JWKS 주소).
챗 스모크 통과. hwax-deliberation 도구 8종이 카탈로그에 새로 들어왔다(508→516).

**ste 빨강 둘.** ① `자격중계 404 — 헤드에 시크릿이 없다`: `deploy-ste.sh` 가 Drive 경로(refresh-code)를 부를 때 **PORTAL_ENV 를 안 넘겼다**
(direct 경로는 넘기고 있었다). ste 쪽 `sync-sso-secret.sh` 는 포털을 형제 디렉터리 `../HWAXPortal` 로만 찾는데 cae00 은 `~/SmartTwinExplorer`
와 `~/Projects/HWAXPortal` 이라 `/.env` 를 열려다 "포털 쪽 값이 비어 있다" 로 빠졌고 refresh-code §8 은 경고만 하고 완료로 끝났다 — 박스마다
리포 루트가 다르다는 CLAUDE.md 의 그 함정. 고침: 포털 `deploy-ste.sh` 가 두 경로 모두 `PORTAL_ENV="$SELF/infra/.env"` 를 넘기고(시험), ste
`sync-sso-secret.sh`(a28cf32) 는 관례 경로(형제 → ~/Projects → ~/claude)를 차례로 보고 못 찾으면 '못 찾았다(경로)' 로 말한다. 읽기 규칙도 포털
독자와 같게(첫 줄·따옴표만 벗기던 것). Drive 스테이징 a28cf32 재발행 → 다음 update-all 2c 가 stale 로 보고 다시 배포하며 §8 이 시크릿을 심는다.
② `ste MCP 15812 → 000`: deploy-ste 때 헤드는 `mcp : active` 였는데 게이트웨이는 터널로 못 붙는다 — 터널 유닛은 15812 를 열고 있으니(--check)
헤드의 ste-mcp.service 가 기동 직후 죽은 것으로 본다(Restart=on-failure 루프 가능). 이유는 헤드 journal 에만 있다 → `ste-doctor` 의 mcp 행이
빨강일 때 transport 로 `systemctl is-active ste-mcp`·`journalctl -u ste-mcp -n 8` 을 그대로 보여 주게 했고, update-all §6 의 힌트가 터널만
탓하던 문구를 고쳤다. 다음 실측은 doctor 출력이다. (smart-twin-mcp :5013 DOWN·arp DOWN 은 이번 범위 밖 — 전자는 stcx MCP 별건, 후자는 원격.)

## D-29. 0b 잠금 6차 — 5라운드: 삼킨 Ctrl-C 뒤 체인·정지 플래그의 PID 결합·sudo rm 안내·flock 없는 갈래 (2026-09-27)

5라운드(403597c 대상, 새 기계에 집중) 확인 6·기각 0 — 전부 medium/low 로 내려왔다. ① 삼킨 Ctrl-C 로 § 머리에서 멈춘 rc 143 은 바깥이
정상 종료라 `./update-all.sh; 다음` 체인이 이어졌다(단계가 INT 로 죽은 130 은 끊겼다 — 같은 Ctrl-C 가 단계의 INT 처리에 따라 갈렸다)
→ `_got_int=1` 이면 143 도 `kill -INT $$`. ② 정지 플래그 초기화가 `UPDATE_ALL_REEXEC` 만 보아, 종료 요청 뒤 같은 § 안에서 뜬 데몬이
REEXEC=1·STOP=1 을 물려받고 그 후손에서 띄운 다른 update-all 이 첫 hr 에서 신호 없이 죽었다 → '내 재실행' 판정을 PID 로
(`HWAX_UPDATE_ALL_REEXEC_PID=$$`, exec 는 PID 를 지킨다). ③ sudo rm 안내가 '그 사용자가 지금 돌고 있는가' 를 묻지 않았다(따르면 겹침)
→ 'ps 로 먼저 본다, 돌면 기다린다' + 파일이 없으면(디렉터리 문제) sudo rm 이 아니라 디렉터리를 가리킨다. ④ flock 없는 갈래엔 정지 기계가
하나도 없었다(kill 이 옛 모양) → 정지 규율을 함수로 빼 두 갈래가 같이 쓴다. ⑤ kill 시험의 HUP 갈래가 nohup 러너에서 결정적으로 빨강
(SIGHUP 무시 상속) → preexec 로 기본 처리 복원. ⑥ INT trap 이 명령 사이의 Ctrl-C 를 '단계가 삼켰다' 고 찍었다 → 문구 수정.
미검증 반영: hr 정지 문구의 자기모순('1) 부터는 하지 않았다' 가 §1 끝난 뒤) → '직전 머리 X · Y 머리에서 멈췄다', 정지 요약을 stdout 으로
(`> log` 에서 완주처럼 보이던 것), 가짜 헤더가 장부 lib 를 source 해 ○ 요약 호출의 보호를 세움, 데몬에 샌 플래그·flock 없는 갈래·디렉터리
문구 시험. **못 한 것**: '두 번째 Ctrl-C 는 즉시' — bash 는 전경 단계가 끝나기 전엔 trap 을 미루고 신호는 쌓이지 않아 삼키는 단계 아래선
두 번 눌러도 한 번으로 합쳐진다(실측, 시험이 잡았다). 바깥이 두 번째 INT 에 본문의 후손을 죽이는 길은 같은 실행이 띄운 데몬까지 죽이므로
넣지 않았다 — 문구로 남겼다. 시험 53(실프로세스), 변이 5/5, 스위트 800. 이번 라운드로 잠금 검토를 마감한다(심각도 medium 이하만 남았고
전부 반영·기록).

## D-30. "Error executing tool cluster_info" — 토큰은 어디까지 갔나, 무엇이 안 보였나 (2026-09-30)

사용자가 cae00 에서 `cluster_info` 가 `Error executing tool cluster_info : ` 로 실패했다고 알렸다(콜론 뒤는 옮기지 않았다).
읽기 전용 조사(게이트웨이 토큰 경로·ste 서버)와 검증으로 확인한 것:
- 그 문구는 **FastMCP(헤드의 ste MCP)** 만 낸다. 게이트웨이 실패는 문구가 다르다 — 토큰 발급 실패 `ste: <이메일> 자격증명으로
  호출하지 못했습니다 (…)`, 세션 없음 `backend ste unavailable`, 정책 `forbidden`. 그러니 **그 순간 터널(15812)은 열려 있었고
  요청은 헤드까지 갔다.** tbot/인증서 만료는 이번 원인이 아니다(만료되면 위 게이트웨이 문구가 나온다).
- 남는 갈래 둘. ① 토큰이 안 실렸다 — 게이트웨이 config 에 `heax_registry.per_user_sso.ste` 가 없으면 서비스 신분(Authorization
  없음)으로 부르고 REST 가 401 → `… → HTTP 401: … 신원이 없거나 토큰이 죽었다`. provision 이 이 블록을 **HEAX 토큰이 있을 때만**
  쓰고, update-all §5 는 백엔드 키가 통째로 없을 때만 재프로비저닝해서 한 번 빠지면 그대로 남는다. ② 토큰은 맞고 slurm 이 실패 —
  `cluster_info` 는 slurm 을 직접 부르는 유일한 조회 도구다(`… → HTTP 503: 클러스터 조회 실패`). ste 기본 slurm 경로
  `/opt/slurm/bin` 과 헤드 실설치 `/usr/local/slurm/bin` 의 관계는 확인하지 못했다.
- 점검 공백: 어느 점검도 **사용자 신분으로 ste 도구를 실제로 부르지 않는다.** ste-doctor 의 시크릿 대조는 **포털**의 값이고
  게이트웨이가 복사해 쥔 값이 아니다. 그래서 ①·시크릿 불일치·폐기된 캐시 토큰이 전부 초록 아래 숨는다.
- 게이트웨이는 발급·호출 **예외**에만 1회 재발급했다. ste 의 401 은 예외가 아니라 isError 결과로 오므로 폐기된 캐시 토큰을
  캐시 수명(12시간) 동안 계속 썼다.
사용자 결정: 점검 보강(2)과 재발급(3)을 한다(S5). tbot 무인화는 S4 그대로 사람 몫.

## F. cae00 실측 (S0)

### 2026-09-27 — 첫 `update-all` 뒤 `ste-doctor`(사용자 실행, 그대로)
```
✓ route          routes.local.env ste=http://127.0.0.1:15810/
✓ transport      teleport (~/SmartTwinExplorer/deploy/transport.env)     ← 리포가 형제(~/Projects)가 아니라 ~ 에 있다
✓ web            http://127.0.0.1:15810/api/health → 200 (터널 경유)
✗ mcp            http://127.0.0.1:15812/mcp → 000 — ste 도구 8종이 안 뜨는 원인
✓ tunnel-unit    active (리포 유닛)
⚠ teleport       tsh status 에서 만료 시각을 못 읽었다 — 세션이 없거나 형식이 다르다
✗ sso-secret     양쪽 다르다 (verify 401)                                    ← 오진: 옛 판의 미들웨어 401 (D-9)
✗ gateway-ste    ste 백엔드 absent
✓ policy         백엔드 21개분 적재됨 (ready=True)
✓ tls            사설·자체서명 — 발급 CA 체인 준비됨(/tls/ca.crt)
✗ https          :443 200 인데 설정이 어긋난다 — COOKIE_SECURE≠true
⚠ deployed       헤드에 배포 커밋 마커가 없다(옛 deploy-backend 로 배포됨)
```
update-all 끝: 챗 스모크 ✓(TOOL_MAX=0, 게이트웨이 437개) · ○ 기능 0 / 값 미정 3(LLM_*) / 선택 2(RA_PORT·RA_MCP_PORT) ·
✗ ste 자격중계(옛 판)·ste MCP(15812 000). **판정: 헤드에 옛 코드 — 2c 가 배포하지 않았다**(사유 미표시 → docs/ra-reconnect D-9 에서 고침).
S0 확정 항목 중 여기서 답이 난 것: 인증서 = 자체서명(https 켜짐) · 터널 = 리포 유닛 active · 정책 적재 21 · 라우트 = 있음.
남은 확정: 15812 가 터널에 있는가(`install-ste-tunnel.sh --check`) · Teleport TTL(형식) · 헤드 시크릿(코드 갱신 뒤) · Drive staging 대조.

## 확인된 마찰 19건 (검증 생존) — 원문은 `/tmp/claude-1000/ste_cae00_result.json`
| # | 심각도 | 갈래 | 제목 |
|---|---|---|---|
| 1 | high | 셋업 | ste-tunnel 을 아무 리포도 만들지 않고 15812 를 여는지 아무도 모른다 |
| 2 | high | 셋업 | 전 경로가 Teleport 세션 TTL 에 묶여 있고 tbot 이 없다 |
| 3 | high | 셋업 | routes.local.env 의 ste= 가 새 클론에 없어 "ste 안 씀" 으로 조용히 판정 |
| 4 | high | 사용자 | 입력 파일이 MCP 로 못 간다(content 문자열·큰 파일은 두 번째 토큰) |
| 5 | high | 사용자 | 헤드 시크릿·sso 반영이 수동 발화라 그때까지 ste 호출 전부 SSO 404/401 |
| 6 | high | MCP | 입력 파일이 모델 컨텍스트를 지나야만 올라간다 — 실 덱 제출 불가(MCP 경로) |
| 7 | high | MCP | 결과 바이트 도구가 없고 result.zip 을 rest_call 로 부르면 게이트웨이가 삼킨다 |
| 8 | high | MCP | 게이트웨이→ste MCP(:15812) 도달 근거가 없다(터널은 15810 만 문서화) |
| 9 | high | 적대 | §6 자격중계 게이트가 시크릿 불일치를 "설정됨" 초록으로 읽는다 |
| 10 | high | 적대 | 실배포 경로가 STE_SSO_SECRET 을 원격 명령 인자로 넘긴다 |
| 11 | high | 적대 | 15812 는 정의도 프로브도 없고 DOWN 이어도 exit 0 |
| 12 | high | 적대 | 사람이 로그인한 인증서에 매달려 무인 셋업이 정의되지 않는다 |
| 13 | medium | 셋업 | STE_DEPLOY=1 게이트가 존재하지 않는 크론을 막느라 요구를 깬다 |
| 14 | medium | 셋업 | teleport 경로에 신선도 판정이 없다 |
| 15 | medium | 사용자 | TLS — 자체서명 8단 체인이거나 사내 CA 면 인증서를 아예 안 심는다 |
| 16 | medium | 사용자 | 권한 게이트 둘을 어디서도 말해 주지 않는다 |
| 17 | medium | 사용자 | 게이트웨이→ste MCP 경로 미정의 — "권한 없음" 과 같은 모양 |
| 18 | medium | 적대 | 정책 미적재면 전 백엔드가 열리고 임의 이메일로 JIT 계정 생성 |
| 19 | medium | 적대 | 요구의 모순 — 셋업/갱신 분리로 푼다(D-2) |

### 2026-09-27 — `install-ste-tunnel.sh --check` · `deploy-ste.sh` 직접 실행
```
✓ 유닛 설치됨(active) · ✓ 15810 → 200 · ✗ 15812 → 000   ← 터널은 열려 있다, 헤드에 MCP 가 없다(옛 코드)
deploy-ste: 수신 33M ✓ · sha256 전부 OK ✓ · 3) 코드 커밋 고정: fetch OK → ✗ 커밋 체크아웃 실패: 41709e6…  → STE 배포 실패
```
판정: 2c 는 여기서 멈추고 있었다(docs/ra-reconnect D-10). 처방: `~/SmartTwinExplorer` 에서 `git status --short` 로 무엇이 더러운지 보고
`git stash push -u -m manual` 뒤 `deploy-ste.sh` 재실행. 새 판(6b7205e)부터는 §3 이 스스로 치운다.

### 2026-09-27 — `git -C ~/SmartTwinExplorer status --short` (사용자가 붙여 줌) → `stash push -u -m manual` → 다음 deploy-ste 전
```
 M apps/lsdyna/app.yaml
 M backend/tests/test_core.py
?? cluster.prod.yaml
?? deploy/transport.env.bak.20260828082136
```
판정: D-10 의 추정이 맞았다 — 추적 파일 둘의 로컬 편집이 체크아웃을 막았다(두 파일은 리포에서 5048c2b 가 마지막으로 고친 것. cae00 에서 먼저
손으로 고친 것이 뒤에 리포로 들어간 모양일 가능성 — `git stash show -p` 대조는 사용자 몫, 리포에 없는 것이면 리포로 옮긴다. 로컬 편집으로 두면
또 막힌다). **그런데 `-u` 가 미추적 둘도 담았다.** `cluster.prod.yaml` 은 설치기(`installer/orchestrate.sh --config`) 입력 — 실제 노드 목록이다.
배포 경로(refresh-code·deploy-backend·deploy-frontend)는 이 파일을 읽지 않아 이번 배포엔 지장이 없지만, 내가 6b7205e 에 넣은 §3 의 `stash -u` 는
이 파일이 루트에 있는 한 **배포마다** stash 로 보낸다(복구는 되지만 매번 사라진다). → SmartTwinExplorer **f64fb8b**: 더러움 판정을
`--untracked-files=no` 로, stash 에 `-u` 를 주지 않는다. 미추적 파일이 반입 커밋과 충돌하는 드문 경우는 checkout 이 그 파일 이름을 들어 실패하니
사람이 치운다(시험 4). Drive 스테이징 재발행(f64fb8b 일치). `transport.env` 자체는 gitignore 라 `-u` 도 건드리지 않았다(`-a` 만 담는다).
복구: 새 판이 cae00 에 앉은 뒤 `git -C ~/SmartTwinExplorer show 'stash@{0}^3:cluster.prod.yaml' > ~/SmartTwinExplorer/cluster.prod.yaml`
(미추적 파일은 stash 커밋의 **세 번째 부모**에 있다). 옛 §3(그냥 checkout)이 돌 이번 한 번은 깨끗한 트리라 그대로 통과해야 한다.

### 2026-09-28 — "여전히 배포하면 15812 에 아무것도 없다" — 배포가 터널을 세우지 않았다

사용자 증상: cae00 에서 `update-all` 을 다시 돌려도 `✗ ste MCP http://127.0.0.1:15812/mcp 에 아무것도 없다(000000)` 가 매번 나온다.

**뿌리 ①: 배포 경로에 터널을 세우는 단계가 없었다.** `install-ste-tunnel.sh` 를 부르는 곳은 **문서뿐**이었다(코드 0건).
§6 은 "없다" 고 **보고만** 했다. 그러니 배포를 몇 번 돌려도 터널은 아무도 손대지 않는다 — 사용자가 손으로 그 스크립트를
돌린 적이 없으면 영원히 같은 빨강이다. → **§2d) ste 터널 정합** 을 넣었다(§2c 바로 뒤, §5 게이트웨이 정합보다 앞).
`--check` 가 통과하면 아무것도 건드리지 않고, 실패하면 리포 유닛으로 다시 세운다. teleport 가 아닌 박스는 ○ 로 건너뛴다.
비대화식이라 `sudo loginctl enable-linger` 는 프롬프트 대신 건너뛰고 한 줄로 남긴다(`STE_TUNNEL_NONINTERACTIVE=1`).

**뿌리 ②: 000 의 두 원인을 출력이 가르지 못했다.** 확인한 사실 — 헤드의 MCP 서버는 `host="0.0.0.0"` 로 뜨고(ste
`backend/mcp_server/server.py:34`) dev(direct)에서 `/mcp` 가 **406** 을 준다. 즉 앱·경로·포트는 맞다. 터널 대상도 같은
기계다(`install-ste-tunnel.sh` 의 `TARGET` = `transport.sh` 의 `TARGET` = `$REMOTE_USER@$HEAD_NODE.$TP_CLUSTER`).
그러면 000 은 둘 중 하나다.
- **(a) 로컬에 15812 리스너가 없다** — 유닛이 그 포트를 안 열거나 못 연다. 가장 흔한 형태는 **옛 손 터널이 15810 을
  쥐고 있는 것**이다. 그러면 리포 유닛의 `-L` 바인드가 실패하고 `ExitOnForwardFailure=yes` 로 ssh 가 죽어 `Restart=always`
  가 영원히 재시도한다. 그동안 15810 은 **옛 프로세스**가 서비스하니 "15810 은 200, 15812 는 000, 유닛은 active" 라는
  정확히 헷갈리는 모양이 된다. → `_stray_pids` 가 그것을 좁게 골라(LISTEN·그 포트·`comm=ssh`·cmdline 에
  `-L 127.0.0.1:1581`·유닛 MainPID 아님) 내리고 유닛으로 다시 세운다. `STE_TUNNEL_NO_KILL=1` 로 끌 수 있다.
- **(b) 리스너는 있는데 000** — 터널은 섰고 **헤드에서 `127.0.0.1:15812` 로 가는 연결이 거부**된 것이다.
  → `ste-doctor` 가 헤드에서 `ss -ltn` 의 **주소**(개수가 아니라)와 **헤드 자기 자신의 `curl /mcp` 코드**를 보여 준다.
  헤드에서 406/200 이면 터널·포워딩 문제, 헤드에서도 000 이면 서비스가 실제로 안 선 것이다. 이 한 줄이 남은 공간을 없앤다.

⚠ **`listen: 1` 은 증거가 아니었다.** 종전 진단은 `ss -ltn | grep -c ":15812 "` 였는데, 그 개수는 `::1` 전용 바인드도 1 로
센다 — 그러면 `-L …:127.0.0.1:15812` 목적지와 안 맞아 "헤드는 살아 있는데 000" 이 된다. 주소를 찍게 바꿨다.

⚠ **`|| echo 000` 이 코드를 두 번 찍었다.** curl 은 연결 실패에도 `-w` 로 이미 `000` 을 찍는다 — 그래서 사용자 화면에
`000000` 이 나왔다. ste 경로 넷(ste-doctor `code`·verify·https, install-ste-tunnel, update-all `_mcp_probe`)을 고쳤다.
`deploy-all` 의 `probe()` 가 같은 함정을 이미 주석으로 적어 두고 있었는데 이쪽엔 반영되지 않았던 자리다.

시험 `backend/tests/test_ste_tunnel_repair.py` 8건 — 000 중복 금지, 옛 터널 고르기 여섯 갈래(남의 프로세스·자기 유닛을
안 고른다), 두 원인 분기 문구, 헤드 자기 probe, §2d 의 배선·순서(§5·§6 보다 앞)·teleport 아님 ○ 처리. 스위트 871.

**같은 날 확인 중에 나온 셋(dev 실주행·진입점 시험).**
- **`--check` 의 진단이 한 번도 돌지 않았다.** 스크립트가 `set -euo pipefail` 이라 `check_ports; _cp=$?` 에서 check_ports 가 1 을 내는
  순간 끝났다. 리스너·원인 분기·옛 터널 표시가 전부 죽은 코드였고, 종전 판의 '로컬 리스너' 줄도 같은 이유로 안 나왔다(dev 실측: rc 1
  인데 진단 0줄). → `_cp=0; check_ports || _cp=$?`. 함께 `_port_pids` 가 '아무도 안 듣는다' 를 grep 무일치 rc 1 로 내 대입을 타고
  스크립트를 죽이던 것 → `|| true`. **함수를 떼어 set -e 없이 돌린 시험은 이것을 원리적으로 못 본다** — 진입점 시험을 넣었다.
- **direct 박스에서 `--check` 가 거짓 빨강**(유닛 없음·000·000)이었다. transport 를 설치 경로에서만 읽었다. → 맨 앞에서 읽고
  direct 면 "터널 불필요" rc 0. 그 독자도 정본 규칙으로 바꿨다(종전 `_v` 는 첫 줄·주석 미처리라 `TRANSPORT_MODE=teleport  # 운영`
  이 `teleport#운영` 으로 읽혀 "모른다" 로 죽었다 — transport.sh 는 bash 로 소싱해 teleport 로 읽는다).
- **`$USER` 가 없는 환경에서 복구가 죽는다.** cron·systemd 타이머 같은 축소된 환경에는 `USER` 가 없어 `set -u` 가 linger 검사에서
  "unbound variable" 로 끝냈다. → `${USER:-$(id -un)}`.

진입점 시험은 진짜 스크립트를 그 자신의 strict mode 로 돌린다. 옛 터널 제거는 **진짜 프로세스**로 끝까지 태운다 — 인터프리터를 `ssh` 라는
이름의 링크로 띄우면 comm 이 `ssh` 이고 `-c` 뒤 인자가 cmdline 에 남는다(sleep 을 복사하면 `-L` 인자를 거부하고 스스로 즉시 죽어
'내렸다' 단언이 헛돌았다). 내려간 프로세스는 시험의 자식이라 좀비로 남는데 `kill -0` 은 좀비에도 성공한다 — 셈은 cmdline 이
비었는지로 산 것을 가른다. 변이 8종(set -e 되돌림·`|| true` 제거·direct 조기 종료 제거·USER 폴백 제거·옛 독자·kill 제거·
MainPID 고름·comm 검사 제거)이 전부 시험에 죽는다 — 마지막 것은 처음에 살아남아 이름만 다르고 명령줄이 같은 경우를 넣었다.
