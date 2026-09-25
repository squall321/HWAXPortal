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

## F. cae00 실측 (S0 에서 채운다)
_아직 비어 있다. `ste-doctor --report` 출력을 여기에 붙인다._

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
