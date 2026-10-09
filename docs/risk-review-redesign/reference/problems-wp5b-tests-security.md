# WP5b(시험 전략·실주행·보안) 반대 검토 메모 — 2026-10-09

찾는 대로 덧붙인다. 근거는 직접 연 코드 줄 또는 설계서 절이다.

## P-01 (major) 가드 D(건너뜀 예산)가 xfail 을 건너뜀으로 센다 — C1 뒤에 C2 를 넣는 순간 dev 의 전체 시험이 rc=1 이 된다

- 근거(실측). 설계서 3.1 가드 D 의 훅을 그대로 옮겨 scratchpad 에서 pytest 9.1.1(리스크 venv)로 돌렸다. `@pytest.mark.xfail(strict=True)` 로 실패한 시험은 `report.skipped == True`(`wasxfail` 이 붙은 채)로 훅에 들어오고, `RR_STRICT_SKIPS=1` 이면 `1 passed, 1 xfailed` 인데 종료 코드가 1 이다.
- 설계서는 같은 꾸러미 안에서 xfail 을 세 군데 쓴다 — 가드 C 의 네 단언(3.1, C2 걸음), 미시험 18종 코드에서 생산자 결함이 나올 때(6절 위험표 '그 코드만 xfail(strict)'), WP1 수리 전의 재현 시험. dev·cae00 은 형제 리포가 곁에 있어 strict 기본값이 1 이다(가드 D 코드 `"1" if siblings else "0"`).
- 결과. C1(예산) → C2(xfail 넷) 순서로 커밋하면 C2 부터 `rr_verify.sh` 와 맨 `pytest` 가 늘 붉다. '붉은 것이 정상' 인 기간이 WP1 수리 커밋까지 이어져 가드가 첫날부터 무시된다.
- 고치는 법. C1 의 훅을 `if report.skipped and not hasattr(report, "wasxfail") and report.when in ("setup","call")` 로 적는다. '가드가 실제로 찾는다' 시험에 xfail 사례(세지 않는다)와 skip 사례(센다)를 둘 다 넣는다(pytester 가 아니라 scratch 디렉터리의 서브프로세스 pytest 로).

## P-02 (major) xfail(strict=True) 가 공장 함수의 예외까지 삼킨다 — 재현 시험이 '틀린 이유로' 초록이 된다

- 근거(실측). `@pytest.mark.xfail(strict=True)` 시험 본문에서 `TypeError` 를 던지면 `1 xfailed`·rc=0 이다. 가드 C 는 `make_diff_target(size=40)` → `plan_panel` → `brief.build_brief` 를 본문에서 부르고 단언 넷을 한다(3.1 가드 C). 공장이 터지든(서명 불일치·syn40 미완성) 단언이 실패하든 똑같이 xfail 이다.
- 이것은 설계서가 2.3절에서 고발한 것과 같은 모양이다 — '실패가 정상 응답과 똑같이 생겼다'. WP1 이 E7 을 고쳐도 공장이 여전히 터지고 있으면 xpass 가 안 나와 표식이 안 지워지고, 반대로 단언 넷 중 하나만 남아도 나머지 셋의 수리 여부를 알 수 없다.
- 고치는 법(C2 에 넣는다). ① 단언 넷을 시험 넷으로 쪼갠다(E7·E3·E4·E2 각각). ② 표식은 `xfail(strict=True, raises=AssertionError, reason="WP1 <걸음 번호>")` 로 적는다. ③ 타깃·좌석·브리프 조립은 모듈 픽스처로 올린다 — 픽스처 예외는 xfail 이 아니라 error 로 뜬다.

## P-03 (minor) 가드 D 의 허용 목록이 실제 건너뜀 자리와 안 맞는다

- 근거. `backend/tests` 의 `pytest.skip`/`skipif` 는 일곱 파일에 있다 — `test_config_datadir.py:75·283`, `test_manifest.py:32`, `test_parity.py:37·42·46·55`, `test_atoms.py:382`(엔진 리포 부재), `test_wiring_regressions.py:357·362`(포털 리포 부재 · **포털 모델을 이 venv 로 못 불러옴**), `test_client_contract.py:69`(프런트 `API_CLIENT` 부재 — 모듈 전체), `test_p6_routes.py:394`(프런트 화면 부재). 설계서 `ALLOWED_SKIPS` 는 앞의 둘뿐이다.
- 지금 dev 에서 실제로 건너뛰는 것은 `test_parity.py` 2건뿐임을 그 일곱 파일만 돌려 확인했다(`-p no:cacheprovider`, 리포 변화 없음). 그러나 프런트는 다른 세션이 개발 중이라 `API_CLIENT` 경로가 옮겨지는 날 백엔드 세션이 strict 로 붉어지고, `test_wiring_regressions.py:362` 는 포털이 새 의존을 들이는 날 같은 일이 난다(붉어지는 것이 옳다면 skip 을 fail 로 바꾸는 편이 낫고, 아니라면 목록에 있어야 한다).
- 고치는 법. C1 에서 일곱 자리 각각을 '형제가 있으면 fail / 허용' 으로 분류해 표로 적는다. 프런트 의존 둘은 허용 목록에 사유와 함께 넣는다(이 꾸러미는 frontend/ 를 안 건드린다).

## P-04 (major) 합성 픽스처의 두 기초 단언이 코드 사실과 어긋난다 — `diff_hash` 는 두 번 만들면 다르고, '크기 == 의미 이벤트 수' 는 파생 이벤트 때문에 안 선다

- 근거 1(실측). `diff.py:577~584` 의 봉투는 `project_id`·`base.snapshot_id`·`target.snapshot_id` 를 담고, `diff_hash` 는 `diff_id`·`created_at` 만 빼고 해시한다(`diff.py:1719~1721`). 스냅샷 id 는 `build_ir` 이 `snapshot_id or new_uuid()`(`ir_builder.py:1140`, uuid4)로 준다. 같은 어댑터 결과·같은 `captured_at`·같은 project id 로 임시 DB 둘에 각각 `freeze_snapshot`×2 → `create_diff` 를 돌리니 `diff_hash` 가 `3b70527d…` 와 `4579256f…` 로 달랐다. 설계서 3.3.1('결정론 단언은 `rr_diffs.diff_hash` 로 한다')·C3 검증('두 번 만들면 `diff_hash` 가 같다')·5.1 첫 행은 이대로는 늘 붉다. 같은 DB 안에서는 `freeze_snapshot` 이 `(project_id, ir_hash)` 로 재사용하고 `create_diff` 가 같은 쌍을 다시 만들지 않으므로(`diff.py:1699`) '두 번' 은 DB 둘일 수밖에 없다.
- 근거 2(실측 + 코드). 기존 어댑터 픽스처(mcad+dyna+result)에서 mcad 부품 하나의 `min_dim` 만 절반으로 줄였더니 의미 이벤트가 `part.thickness_changed` 1 + `cross.bridge_stale` 1 = **2건**이었다. `diff.py:1415~1422` 는 mcad 두께·bbox 가 바뀌고 같은 묶음의 dyna pid 가 noise 면 `cross.bridge_stale` 을 늘 덧붙인다. `diff.py:1464~1479` 는 조립 단위의 내부·외부 엣지 수가 1 이상 바뀌면 `asm.rollup_changed` 를 낸다 — 계면·접촉을 더하거나 빼는 연산(#1·2·7·8·9·10·18·19)과 부모 이동(#6)이 전부 이것을 끌고 온다.
- 그래서 3.3.4 의 '크기는 의미 이벤트 수다(공장이 `len(events) == size` 를 단언)' 와 `syn3` = '두께 감소 1·재질 교체 1·간극 감소 1'(기본 `with_dyna=True`), `syn40` = '33종 각 1건 + 7' 은 동시에 설 수 없다. `syn40` 에서 `cross.bridge_stale` 과 `asm.rollup_changed` 는 '각 1건' 이 아니라 여러 건이 된다. 3.3.1 이 '출력에 맞춰 기대를 고치지 않는다' 고 못 박아 두었으므로 구현자는 공장 단언을 못 넘는다.
- 고치는 법(C3 에 넣는다). ① 크기의 정의를 '대본의 연산 수(= `ChangeRecord` 수)' 로 바꾸고, 이벤트 수 기대는 `sum(len(r.expect_codes))` 로 대본에서 계산한다. 연산표(3.3.3)에 '끌고 오는 코드' 열을 더한다(#23~26 → `cross.bridge_stale` 조건, 엣지 증감 → `asm.rollup_changed`). ② 결정론 단언은 `diff_hash` 가 아니라 '식별자를 뺀 본문' 으로 한다 — `{k: v for k in diff if k not in (diff_id, created_at, project_id)}` 에서 `base.snapshot_id`·`target.snapshot_id` 를 지운 정규 JSON 의 해시(시험 쪽 도우미). 또는 공장이 `freeze_snapshot(..., snapshot_id=<씨앗에서 유도>)` 로 id 를 고정한다(`build_ir` 가 그 인자를 받는다, `ir_builder.py:786`) — 이 경우 project id 도 고정해야 한다.

- (P-04 보충) `contact.type_changed`(#20)는 설계서가 적은 법('contact 엣지의 종류를 바꾼다')으로는 안 나온다. `_edge_change` 는 엣지 `kind` 가 달라질 때만 `kind_changed` 를 내고(`diff.py:838~840`), contact 계열의 kind 는 `contact`·`scope` 둘뿐이며(`ir_builder.py:48~53`), 어댑터 픽스처의 종류는 `attrs.contact_type`(`*CONTACT_TIED_SURFACE_TO_SURFACE`)에 있다. `status_changed` 는 의미 이벤트 전에 걸러진다(`diff.py:1274`). 즉 같은 쌍의 엣지가 contact ↔ scope 로 뒤집힐 때만 이 코드가 난다. 설계서 9절이 '확인 못 함' 으로 둔 것을 코드로 확인했다 — `syn40` 의 '33종 각 1건' 은 지금 생산자로는 32종이다. C3 에서 #20 은 처음부터 '생산자 결함(WP1 목록) · xfail(raises=AssertionError)' 로 적고 시작한다.

## P-05 (major) 하네스의 임시 리스크 앱이 **실 에이전트 서버**의 `/health` 를 읽는다 — `HWAXRISK_AGENT_URL` 이 환경 목록에 없다

- 근거. 리스크 앱은 에이전트 서버를 포털 경유가 아니라 직접 읽는 길이 따로 있다 — `engine_client.py:42` `DEFAULT_AGENT_URL = "http://127.0.0.1:9009"`, `:310` `settings.agent_url or DEFAULT_AGENT_URL`, 설정은 `config.py:204` `HWAXRISK_AGENT_URL`(기본 빈 값). 설계서 3.8.1 이 임시 리스크 앱에 주는 환경은 `HWAXRISK_DATA_DIR`·`PORT`·`HWAXRISK_PORTAL_BASE`·`HWAXRISK_HEAX_API`·`HWAXRISK_GATEWAY_MCP` 다섯뿐이다. '닫힌 포트를 주는 것은 실물로 새는 호출을 막기 위해서' 라고 적었는데 정작 9009 가 빠졌다.
- WP5a 는 새 흐름의 러너가 바로 이 주소의 `/health` 에서 `capabilities.card_review`(없으면 `agent_outdated` 로 보류, spec-wp5a 964·1098행) · `request_worst_s`·`quiet_ok_s`(벽시계·침묵 한도, 852·867행) · `context_tokens`(묶음 계획, 951행) · `draining` 을 읽게 설계했다('PortalPanelEngine.health 와 같은 주소', 710행).
- 결과. S0·S1 에서 임시 앱은 일은 임시 에이전트 서버(19009)에 보내면서 판단은 실 서버(9009)의 상태로 한다. 실 서버가 아직 옛 코드면 `agent_outdated` 로 S0 가 시작도 못 한다. 새 코드면 실 LLM 의 창으로 계획을 짜 가짜 LLM(16,384 흉내)에 보내고, 실 서버에 세운 비우기 신호가 리허설을 멈추며, 원장의 `model` 에 실 모델 이름이 찍혀 품질 블록 머리(모델·프롬프트 판)가 틀린다. S0 ③(재기동)·S4 ④(비우기)의 판정이 엉뚱한 서버를 본다.
- 고치는 법(C13). 임시 리스크 앱 환경에 `HWAXRISK_AGENT_URL=http://127.0.0.1:$RR_PORT_AGENT` 를 더한다. 쓰지 않는 바깥 주소도 닫는다 — `HWAXRISK_AIDH_BASE=http://127.0.0.1:9`(기본 8001 실물), `HWAXRISK_HEAX_BASE=http://127.0.0.1:9`(기본 4180 실물). S0 통과 기준에 '원장의 `model` 이 가짜 LLM 이 준 이름과 같다' 를 넣어 새는지를 기계로 본다. `test_rr_stack_safety.py` 에 '하네스가 띄우는 앱의 환경에 실 포트(9009·9110·8001·4040·4180)를 가리키는 값이 없다(에이전트 서버의 게이트웨이·LLM 만 예외로 명시)' 를 더한다.

## P-06 (minor) 가짜 LLM 의 기본 포트 18000 은 실 서비스(SignalForge API)다 — 실 포트 목록도 모자라다

- 근거. dev 에서 `ss -ltnp` 로 18000 에 uvicorn 리스너가 있고, `infra/scripts/update-all.sh:1670` 이 `signalforge :18000(API)` 를 탐침한다(`deploy-all-from-drive.sh:356` 도 같다). cae00 도 같은 스택이다.
- 결과. 3.8.3 규칙 3('쓰이고 있으면 띄우지 않는다') 때문에 기본값으로는 `rr_stack.sh up` 이 늘 2 로 끝난다. 규칙 5 의 실 포트 목록(8723·5283·9009·9110·8088·8000·8001)에는 18000·17370(SignalForge)·4040·4180(HEAXHub — 실 리스크 앱이 그 뒤에 있다)이 없다.
- 고치는 법(C13). 포트를 고정 기본값으로 두지 않는다. `up` 이 `python -c 'socket.bind(("127.0.0.1",0))'` 로 빈 포트 다섯을 받아 `$STATE/ports.env` 에 적고 그것을 쓴다(동시 실행도 풀린다). 규칙 5 는 목록을 박지 않고 시작 시점의 **전체** 리스너 표(`ss -ltnpH`)를 떠 두었다가 '하네스 포트를 뺀 나머지' 를 견준다.

## P-07 (major) cae00 에서 도는 단계(S2 품질·S3·S4 의 syn150)에 합성 타깃과 심은 60쌍을 넣을 길이 없다

- 근거(설계서 안의 모순). ① 3.8.4 는 S2(품질)·S3·S4 를 cae00 GLM 에서 `syn40`·`syn40+심은 60쌍`·`syn150` 으로 돈다고 적는다. ② 6절 '박스 차이' 는 'cae00 실주행은 배포된 스택으로 한다(임시 인스턴스는 dev 의 방식이다)' 라고 적는다. ③ 3.8.2 는 `rr_seed.py` 가 `.rr-temp` 표식 없이는 거부하고, fixture 과제는 '배포된 스택을 한 번 확인하는 데만' 쓰며 'LLM 을 부르는 단계는 임시 인스턴스' 라고 적는다. 셋을 다 지키면 cae00 에 합성 타깃을 넣을 수 없다.
- 근거(코드·다른 설계서). 대본(`tests/synth/scripts.py`)·공장(`tests/factories.py`)·심은 쌍(`tests/synth/planted_real.json`)은 `tests/` 아래라 SIF 에 안 실린다(`pyproject.toml` `include = ["app*"]`). cae00 의 유일한 주입 통로인 WP2 의 `hwax-risk dev-seed-pair` 는 `--parts 640 --mutations 300 --seed 7` 꼴의 무작위 변형만 받는다(spec-wp2 1005행) — `syn40`(33종 전수)도 심은 변경도 못 만든다. 설계서 스스로 'cae00 에 호스트 venv 가 없을 수 있다' 고 적었으므로 `rr_realrun.py` 를 cae00 에서 돌릴 파이썬도 정해지지 않았다. 배포된 앱에 누구 자격으로 붙는지도 없다(임시 인스턴스는 하네스가 뽑은 HMAC 비밀로 SSO 단언을 만들지만, 실물에서 그 비밀을 읽어 단언을 만드는 것은 사용자 사칭이다).
- 결과. 품질 기준(3.7.3 — 'GLM 에서만 건다')과 `xp.planted ≥ 90%`·K 파일럿은 잴 수 없다. S3 가 통과 판정을 못 내면 S4 로 못 넘어가거나, 기준 없이 넘어간다. WP5a 의 시범(실제 리비전 쌍 · 대표 15명, spec-wp5a 1281행)은 돌지만 거기에는 정답을 아는 변경이 없어 놓침률을 못 잰다.
- 고치는 법. ① 대본 넷과 `PLANTED` 의 '연산·기대값' 을 `app/devseed.py`(또는 `app/assets/devseed-scripts.v1.json`)로 올린다 — 시험은 그것을 import 하고, WP2 의 명령은 `hwax-risk dev-seed-pair --script syn40 [--planted <파일>]` 을 받는다(C3 과 WP2 걸음 11 에 넣는다). ② 3.8.2 의 문장을 'cae00 의 S2 품질·S3·S4(syn150)는 배포된 스택의 fixture 과제(`FIX-`·`corpus_excluded=1`·`private`)에서 돈다. 끝나면 과제를 purge 한다' 로 고치고 결정 4 의 '한 번만' 을 지운다. ③ `rr_realrun.py` 에 `--deployed` 방식을 둔다 — 표준 라이브러리만 쓰고(venv 없음), 사용자가 환경변수로 준 자기 PAT 로 공개 REST 만 부르며, 지표는 DB 가 아니라 `GET …/quality`(= `review_quality.compute`)로 받는다. 실험 넷(`xp.*`)은 포털 중계 `/agent/card-review/run` 을 그 PAT 로 직접 부른다. ④ 이 셋이 계획에 안 들어가면 S3 를 'WP5a 시범 + dev 의 형식 확인' 으로 줄이고 품질 기준표를 '첫 실제 과제 뒤로 미룸' 이라고 적는다(cuts 참조).

## P-08 (major) '누구 자격으로 돌았나' 가 원장에 거짓으로 남는다 — 엔진이 사용자 PAT 거절을 서비스 계정으로 조용히 넘긴다

- 근거. WP3a 의 `pack` 은 `_tools_by_name(app, groups, CATALOG_RESULT_MAX, user=…, user_pat=…)` 로 도구를 받는다(spec-wp3a 279~281행). 그 함수는 지금 코드에서 사용자 PAT 가 거절되면 **두 번** 서비스 계정으로 넘어간다 — 로드 때(`deliberation.py:1303~1319`)와 호출마다 401 일 때(`_svc_fallback`, `:1359~1386`). 사실은 요청 단위 ContextVar(`_pat_degraded`, `:21`·`:1316`)와 `_cred_mid` 에만 적히고, 읽는 곳은 심의 결정문과 심의 스트림뿐이다(`:3281`·`:3682`·`:3723`). WP3a 설계서에는 이 표식을 `pack`·`run` 응답에 싣는 줄이 없다(`degraded`·`credential` grep 0건).
- 설계서 3.10.3 은 '누구 자격으로 돌았는지가 호출마다 남는다' · '폐기 목록에 jti 가 뜬 뒤 새로 시작한 칸이 0' · '자격 혼합 표기' 를 시험으로 고정하고 3.7.1 `rv.credential` 을 지표로 둔다. 그런데 앱이 아는 것은 '내가 어느 PAT 를 실어 보냈나' 뿐이다. 만료·폐기된 PAT 를 실은 `pack`·카드 밖 검색 호출은 서버에서 서비스 계정으로 성공하고, 원장에는 `credential_kind='owner'` 로 남는다. 며칠짜리 실행에서 정확히 이 일이 난다.
- dev 하네스는 늘 이 길이다. 임시 포털은 자기 JWT 키로 PAT 를 찍고(`ui-check.sh` 의 `JWT_KEYS_DIR="$D/jwt"`·`JWT_AUTOGEN_KEYS=true` 와 같은 환경), 실 게이트웨이는 실 포털의 JWKS 로만 검증한다(`gateway.py:116`·`:3535~3539`). 그래서 S0~S2 의 `pack` 은 전부 서비스 계정 강등으로 돈다 — 설계서 9절 셋째 항목('확인 못 함')의 답이다. 사용자 위임 경로와 3.10.2 의 '`plat:aidatahub` 없는 자격으로 `pack` → 오류' 는 하네스로는 한 번도 지나지 않는다.
- 고치는 법. ① WP3a 에 더한다 — `pack` 응답과 `run` 결과 프레임의 `meta` 에 `credential_effective: 'user'|'service'` 와 `credential_note` 를 싣는다(`_pat_degraded`·`_cred_mid` 를 읽어서). ② WP3b 는 `rr_review_calls.credential_kind` 와 `rr_expert_reports` 의 팩 머리에 **서버가 알려 준 값** 을 적는다(보낸 값이 아니라). ③ 이 꾸러미 C7 의 계약 예제에 그 칸을 넣고 R9(잎 필드를 바꾸면 원장이 달라진다)가 지키게 한다. C12 에 '401 을 주는 가짜 게이트웨이 → 결과에 `service`, 품질 블록에 자격 혼합' 사례를 더한다. ④ 3.8.4 의 S0·S1 통과 기준에 '`credential_effective` 가 전부 `service` 다(임시 PAT 라 그래야 맞다)' 를 적고, 사용자 위임 경로는 '배포된 스택에서만 본다' 고 5.3절에 적는다.

## P-09 (major) dev 임시 인스턴스에 '실전문가 N명' 을 앉힐 길이 없다

- 근거. S0·S1 은 '실전문가 3명', S2 는 'mech 19명' 이다(3.8.4). 타깃의 로스터는 본문 `agents` 가 없으면 `roster.fetch_for_target` 이 게이트웨이에서 받는다(`routes.py:2032~2036`, `roster.py:218` — 자격은 그 사용자의 등록 PAT). 하네스는 `HWAXRISK_GATEWAY_MCP=http://127.0.0.1:9/mcp` 로 닫아 두고, 열어도 임시 포털 PAT 는 실 게이트웨이가 거절한다(P-08). 리스크 앱 쪽에는 서비스 계정 폴백이 없다. 그러면 `roster_source='unavailable'`·`roster_size 0` 인 타깃이 열리고 칸이 0 이다.
- 공장 `make_diff_target(..., agents=None)` 과 `rr_seed.py` 는 `agents` 를 받게 돼 있으나 그 목록(`key`·`domain`·`relevance` — `planner.freeze_roster` 가 읽는 모양, `planner.py:112~142`)을 누가 어디서 만드는지가 설계서에 없다.
- 고치는 법(C13). `rr_seed.py --agents-file <json>` 을 필수로 하고, 그 파일은 하네스의 `rr_stack.sh roster` 가 **사용자가 환경변수로 준 실 PAT**(`HWAX_GATEWAY_PAT`)로 실 게이트웨이의 `list_agents` 를 한 번 읽어 `$T` 에 만든다(리포에 안 넣는다). S0 는 실전문가 대신 합성 전문가 3명 + 합성 카드(가짜 게이트웨이가 `get_agent_session`·`list_records`·`get_record` 를 답한다)로 바꿔 실물 의존을 0 으로 만든다 — 배선 리허설이 실 AIDataHub·실 게이트웨이의 가동 여부에 묶이지 않는다.

## P-10 (major) C2(브리프 모양 계약)가 아직 없는 것 둘에 기댄다 — `syn40` 과 `brief.PLACEHOLDERS`

- 근거 1. 가드 C 는 '`syn40` 타깃(3.3절)을 공장 함수로 만들고' 로 시작한다. 4절 표에서 C2 의 선행은 '없음' 이고 `syn40` 을 만드는 합성기는 C3 이며 C3 의 선행이 C2 다. 돌고 돈다.
- 근거 2. 단언 1 은 `placeholders_in(built)` 을 `brief.PLACEHOLDERS` 로 센다. 그 상수는 지금 코드에 없고(`brief.py` 의 자리표시는 본문에 흩어져 있다), WP1 설계서에도 없다(`PLACEHOLDERS` grep 0건), 계약(04)에도 없다. 설계서 7.1 이 '청한다' 고 굵게 적은 것이 어디에도 받아들여지지 않았다. 게다가 C2 는 WP1 **앞** 에 들어가는 재현 시험이라 WP1 이 상수를 만들기를 기다릴 수 없다.
- 근거 3. 단언 넷(E7·E3·E4·E2)에 필요한 입력은 명명 치수 변화·결과 변화·감소 이벤트·편성된 좌석뿐이다. 33종 전수(`syn40`)가 필요 없다. 지금대로면 WP1 의 첫 수리가 33종 합성기(9절이 '만들 수 있는지 모른다' 고 적은 `part.replaced`·`g2_fail` 포함)를 기다린다 — 계약 C-1 의 'WP1 이 먼저 나간다' 와 어긋난다.
- 고치는 법. ① C2 의 입력을 `syn40` 이 아니라 기존 어댑터 픽스처 셋(`fixtures/ir/adapter_*.json`)에 변형 셋(두께 감소·명명 치수 변화·결과 지표 변화)을 준 작은 쌍으로 바꾼다 — 공장 함수만으로 된다(이 검토에서 같은 방법으로 diff 를 만들어 봤다). ② 자리표시 단언은 상수에 기대지 않고 시험 쪽 정규식(`\[[^\]\n]*(없음|해당 없음)[^\]\n]*\]`)으로 뽑아 '기대 집합' 과 견준다. WP1 이 상수를 만들면 그때 바꾼다. ③ C3 을 둘로 쪼갠다 — C3a(`devseed` 뼈대 + WP1 재현에 드는 연산 + `syn3`)는 WP1 S0 과 같이, C3b(33종 전수 · `syn150`·`syn600` · 변형)는 WP2 와 나란히. C3b 는 WP1 을 막지 않는다.

## P-11 (major) 가드 E(대역 일치)의 표본을 만드는 단계가 없다 — S1 은 패널을 돌리지 않는다

- 근거. 가드 E 가 지키려는 것은 2.3절 #4 다 — 실 심의 엔진이 좌석마다 내는 `source='<키> · 지식카드'` 프레임(`deliberation.py:4139`)을 `FakePanelEngine`·`fixtures/sse/normal.sse` 가 안 낸다. C14 의 검증도 '가짜 엔진에서 지식카드 프레임을 빼면 붉다' 다. 표본은 '3.8절의 S1 이 갱신한다' 고 적었다(3.1 가드 E · C14 의 선행 'S1 실행').
- 그런데 S1 은 '전문가 3 × 단위 3' 의 **카드 대조** 실행이다(3.8.4). 카드 대조는 `/card-review/run` 의 프레임을 내고, 심의 엔진의 패널 프레임(`evidence`·`· 지식카드`)은 한 줄도 안 낸다. 패널이 도는 단계는 쟁점 토의가 열리는 S2 이후이고 그것도 쟁점이 생겨야 열린다. 표본 디렉터리는 비어 있게 되고, 빈 표본에서 뽑은 어휘는 공집합이라 가드 E 는 늘 초록이다(0건을 훑고 통과하는 가드 — 5.1절이 스스로 금한 모양).
- 고치는 법. ① S1 에 '옛 흐름 패널 1건(Tier A, 좌석 3)을 임시 인스턴스에서 실 dev LLM 으로 돌려 SSE 를 받는다' 를 걸음으로 더하거나, ② 표본을 실주행에 묶지 않고 에이전트 서버의 기존 스트림 시험(`tests/test_delib_silent_drops.py` — 실제로 스트림을 돌린다)이 낸 프레임을 `tests/fixtures/sse/captured/` 로 내보내는 시험을 C14 에 둔다(실 LLM 없이 실 엔진 코드의 어휘가 나온다). ②가 싸고 결정적이다. ③ 가드 E 에 '표본이 0건이면 실패' 와 '표본 어휘에 `· 지식카드` 가 있다' 를 먼저 단언한다.

## P-12 (major) 옛 타깃 골든(C0)이 WP1 의 **의도된** 변경에 깨진다 — 유일한 옛 데이터 방어선이 첫 꾸러미에서 붉어진다

- 근거. C0 은 `coverage_payload`·`registry_rows`·`close_level`·`build_report` 의 정규화 출력 전체를 `7248651` 에서 받아 골든으로 얼리고 '옛 응답 넷이 골든과 같다' 를 단언한다(3.9.1). 설계서는 'WP1 이 브리프 문면을 바꾸므로 브리프는 안 담는다' 만 대비했다.
- WP1 은 그 넷도 일부러 바꾼다. ① `registry.close_level` 의 반환에 `raised` 키를 더한다(spec-wp1 990행, R-47). ② 날것 이름·해시 글의 방패와 이름 치환을 '표시 시점에 건다' — 옛 데이터의 등록부·보고서 글이 달라지는 것이 목적이다(538·1158행). ③ WP1 의 v3 는 `rr_targets.report_gz·report_level·report_built_at` 를 더하고 보고서 응답에 `stored` 를 싣는다(1001행). 뒤 꾸러미도 `coverage_payload.job` 에 잡 열(`mode`·`hold_*`)을 더한다(계약 C-5).
- 결과. 골든은 WP1 의 첫 몇 커밋에서 붉어지고, '출력에 맞춰 기대를 고치지 않는다'(3.3.1)와 부딪친다. 골든을 다시 받는 순간 '이행 뒤 옛 타깃의 레벨·등록부가 그대로인가' 를 지키는 것이 없어진다.
- 고치는 법(C0). 골든을 통짜 비교에서 '불변 사영' 비교로 바꾼다. 파일에 담는 것은 ① `close_level` 의 `level`·`c1`·`status_counts`·`detail` 의 수치 칸, ② `coverage_payload` 의 `roster_size`·`by_domain`·`by_status`·`strong`·`unseated_n`·`level`·`close_level`, ③ `registry_rows` 의 `(cluster_key, status, severity, n_supporters, finding id 집합)`, ④ 보고서 블록의 **키 목록과 행 수** 다. 글(문면)과 새로 생기는 키는 견주지 않는다. 사영 함수는 시험 파일에 두고 '키가 더해지는 것은 통과, 있던 키의 값이 달라지면 실패' 로 적는다. WP1·WP4 가 값을 일부러 바꾸는 칸이 있으면 그 꾸러미의 커밋이 골든의 그 칸을 사유와 함께 고친다(변경 목록을 `legacy/CHANGES.md` 에 남긴다).

## P-13 (major) 품질 기준이 통계적으로 '거의 늘 기준 밖' 이다 — 권고 처분(결정 2)과 합치면 타깃마다 자동 재실행·완결 보류가 난다

- 근거(계산 — 단측 95% 정확 이항). 0/29 의 상한은 9.81%, 0/58 은 5.03%, 0/59 는 4.95%, 1/59 는 7.79%, 2/59 는 10.29% 다.
- `rv.stage1_miss` 는 자산에 `upper_max 0.05` 와 `min_n 29` 로 적혔다(3.11.1). 표본이 29~58 이면 '측정됨' 으로 계산되는데 **놓침이 0 이어도** 상한이 5% 를 넘어 기준 밖이다. 통과할 수 있는 값이 없다.
- `rv.flip_neg_pos` 는 `upper_max 0.05`·`min_n 59` 다. n=59 에서 통과하려면 뒤집힘이 정확히 0 이어야 한다. 진짜 뒤집힘률이 1% 여도 통과 확률은 55%, 2% 면 30% 다(n=120 에서도 2% 면 30%, n=300 이어야 85%). 설계서의 문면 예시(2/59 → 상한 10.3% → 기준 밖)가 바로 이 모양이다.
- 결정 2 의 권고는 '기준 밖이면 완결(C2 이상)을 보류하고 그 영역을 자동으로 한 번 다시 돈다. 그래도 밖이면 사람이 수용을 적어야 닫힌다' 다. 위 수로는 정상적인 실행의 절반 이상이 재실행(영역 전체의 LLM 호출 2배)과 사람 수용을 거친다. '며칠씩 걸려 운영을 막으면 안 된다' 는 브리프와 부딪친다.
- 고치는 법(C10 의 자산 + 8절 결정 1·2). ① `min_n` 을 문턱이 실제로 통과 가능한 수로 맞춘다 — 상한 5% 기준이면 `rv.stage1_miss` 59 이상. ② 타깃 단위 **차단** 기준에서 상한을 쓰는 것은 완결 판정이 이미 쓰는 무관 칸 표본(WP4)만 남긴다. 뒤집힘·순서·훑기 놓침은 타깃마다 표본이 작으므로 '표기 전용(점추정 + 상한)' 으로 내리고, 차단은 모델·프롬프트 판마다 한 번 재는 실험값(`xp.*`, n 을 300 이상으로 잡을 수 있다)에 건다. ③ 자동 재실행은 뺀다(cuts) — 기준 밖이면 `[검토 품질 기준 밖 N항]` 을 찍고 사람이 '그 영역의 걸림 없음을 단독으로 다시' 를 고른다. ④ `test_review_quality.py` 에 '자산의 모든 `upper_max` 문턱에 대해 k=0·n=min_n 이 통과한다' 는 자기 검사를 넣는다.

## P-14 (major) 잡음 바닥과 실험 지표 넷이 앱에 들어올 길이 없다 — 문턱과 문면이 읽는데 아무도 안 준다

- 근거. 3.7.1 은 `xp.repeat`(잡음 바닥)·`xp.planted`·`xp.k_pilot`·`xp.inj_ab` 를 '원장이 아니라 하네스 산출 파일(`$T/realrun/*.json`)에 남긴다' 고 적는다. `$T` 는 `mktemp -d` 이고 끝나면 지운다(3.8.3 규칙 11). cae00 의 앱은 SIF 안이라 하네스 파일을 못 읽는다.
- 그런데 문턱은 `max(5%, 잡음 바닥 + 3%p)` 이고(3.7.3) 자산에 `noise_margin: 0.03` 이 있으며, 문면은 `같은 물음 반복 1.3% (모델 실험값)` 을 찍는다(3.11.3). `review_quality.compute` 의 반환과 자산 파일 어디에도 그 값의 자리가 없다.
- 결과. 구현하면 잡음 바닥은 늘 없음이라 문턱은 늘 5% 이고 문면의 그 칸은 늘 `미측정` 이다. K 파일럿으로 정한 K 도 같은 처지다 — 정한 값을 어디에 적어 박스에 싣는지가 없다(K 는 `/card-review/limits` 가 준다 — 에이전트 서버의 `CARD_REVIEW_K` env).
- 고치는 법. ① 자산에 `experiments` 칸을 둔다 — `{"<model>|<prompt_rev>": {"repeat": {"k": 4, "n": 300}, "planted": {...}, "measured_at": "2026-…"}}`. S3 가 끝나면 그 수를 사람이 자산에 옮겨 커밋한다(C16 문서 걸음에 넣는다). `compute` 는 지금 타깃의 `(model, prompt_rev)` 로 찾아 없으면 `미측정` 과 문턱 5% 를 쓴다. ② 하네스 산출은 `$T` 가 아니라 사용자가 준 `--out`(리포 밖, 기본 `~/rr-realrun/<날짜>/`)에 남기고 지우지 않는다. ③ K 파일럿의 결론은 'cae00 에이전트 서버 `.env` 의 `CARD_REVIEW_K` 한 줄' 이라고 절차서에 적는다.

## P-15 (major) '카드 한 장에서 온 인용의 합 ≤ 그 카드의 30%' 는 계약 C-15 와 부딪치고 구현 주인이 없다

- 근거. 3.10.1 설계 2 와 시험 '인용 상한' 은 판정당 200자·카드당 합 30% 를 단언한다. 그런데 ① 어느 설계서에도 이 상한을 거는 코드가 없다 — WP3a 의 `cq` 규칙은 '15자 이상 그대로' 하한뿐이고(spec-wp3a 505·528행) 상한이 없으며, WP3b·WP4 에도 없다. 이 설계서의 의존 목록 D1~D9 에도 빠져 있다. ② 계약 C-15 는 '문제없음도 행으로 두고 카드 문구 인용을 요구한다' — 카드 한 장은 (관련 단위 수 × 변형)만큼 인용된다. 점검 카드의 본문은 1,600자 안팎이고 규칙 절은 449자다(03-cards.md 의 `…0142` 절 길이 449·320·343·276·234). 단위가 30개인 타깃이면 15자 하한만으로도 450자, 실제 인용(40~80자)이면 1,200자를 넘어 30%(약 480자)를 정상 운영에서 넘는다. 변경이 많은 과제일수록 먼저 넘는다. ③ 넘으면 무엇을 하는지(인용을 버리나, 행을 버리나)가 없다. 버리면 그 행은 '인용 불통과 → 형식만 채운 칸' 이 되어 품질 지표를 스스로 깎는다.
- 고치는 법. 카드당 30% 상한을 뺀다(cuts). 남기는 것은 둘이다 — ① 판정당 200자 상한은 WP3a 의 검사표에 `checks.quote='long'` 으로 넣는다(의존 D10 으로 더한다). 저장은 하되 응답·보고서·RA 로 나갈 때 200자에서 끊고 끊었다고 적는다. ② 카드 원문 복원 방지는 권한 함의(결정 3 — `plat:risk → plat:aidatahub`)와 묶음 동결본 비노출(카나리아 시험)로 한다. '카드별 인용 합 / 카드 길이' 는 차단이 아니라 품질 블록의 참고 수치로만 낸다.

## P-16 (major) `review_quality` 의 걸음 순서가 계약과 안 맞고, 블록을 싣는 쪽이 없다

- 근거 1(순서). 계약 C-16 은 판정 범주 접기와 화면 말을 `review_quality.verdict_class` 한 곳에 둔다. 전문가 보고서를 코드로 조립하는 것은 WP3b 이고 WP3b 는 WP4 앞이다(C-1). 그런데 `app/review_quality.py` 를 만드는 걸음 C10 의 선행은 'WP3b 의 원장, WP4 의 `audit.binom_upper`·`rr_cell_audits`' 다(4절). WP3b 가 필요로 하는 함수가 WP4 뒤에 생긴다.
- 근거 2(소비처). 7.1 은 '통합 보고서 조립이 `review_quality.block()` 을 부르고 `close_level` 이 기준 밖을 본다' 를 WP4 에 청했다. WP4 설계서에는 `review_quality`·'검토 품질'·`form_only` 가 한 줄도 없다(grep 0건). 대신 WP4 는 같은 수(격자·카드 판정 전수·표본 n·놓침 k·상한)를 자기 함수 `cell_counts` 로 따로 센다(spec-wp4 3.9.2). 계약 C-29 는 모듈의 이름만 정했고 누가 부르는지는 안 정했다.
- 결과. 이대로면 `block()` 은 만들어지고 시험도 초록인데 보고서에 안 실린다(이 설계서가 2.3절에서 고발한 '발행은 되는데 소비처 0'). 실리더라도 같은 수가 두 함수에서 나와 보고서 머리와 품질 블록이 갈린다. 표시 말도 WP4 는 '문제없음'·'판단 불가' 를 코드 문장에 쓴다(382~393행 — 린터 L06·L17 에 걸린다. `render.lint_text('문제없음')` 이 실패함을 확인했다).
- 고치는 법. ① C10 을 둘로 쪼갠다 — C10a(`verdict_class`·표시 말 사전·자산 뼈대·린터 시험, 원장 의존 없음)는 WP3b 의 보고서 조립 걸음 **앞** 에, C10b(`compute`·`block`)는 WP4 의 `audit` 뒤에. ② WP4 걸음 10(요약·보고서 조립)에 '`review_quality.block()` 을 통합 보고서 블록 목록에 넣는다' 와 '진행판 응답에 `form_only`·`out_of_bounds`' 를 적는다. ③ 격자·카드 전수·무관 칸 표본의 수는 `review_quality` 가 다시 세지 않고 WP4 의 `cell_counts` 를 불러 쓴다(R9 식 시험 — `block().json.grid == cell_counts()`). ④ C10b 의 시험에 '`build_report` 가 낸 블록 키 목록에 `quality` 가 있다' 를 넣어 소비처를 고정한다.

- (P-12 보충) C0 의 단언 ④('새 경로는 옛 타깃에 단위 없음을 답한다')는 그 경로가 생기기 전이라 '지금 코드에서 초록' 일 수 없다. C0 에서는 ①②③⑤만 두고 ④는 WP2·WP3b 의 경로 커밋에 붙인다. 단언 ③은 패널 함수를 직접 부르지 말고 **러너의 잡 집기** 를 지나게 한다 — 이행이 `rr_jobs.mode` 기본값을 `'panels'` 로 안 주면 옛 queued 잡이 러너의 거르기에서 빠져 영영 안 도는데(계약 C-5), 직접 부르는 시험은 그것을 못 본다. 이행 뒤 `rr_targets.flow == 'panels'` 도 같이 단언한다.

## P-17 (major) L6(두 워커 경합)은 스레드 8개로는 늘 통과한다 — 두 프로세스의 경합을 안 넣는다

- 근거. `RiskStore` 는 프로세스당 연결 하나와 `threading.RLock` 하나다(`risk_store.py:574~581` — '앱 프로세스 하나가 소유', `:674~696` 의 `tx()` 가 락을 쥔 채 `BEGIN IMMEDIATE`). 한 저장소 객체를 스레드 8개가 나눠 쓰면 선점의 읽기-쓰기가 파이썬 락으로 직렬화돼 겹칠 수가 없다. 운영에서 겹치는 것은 프로세스 둘이다 — HEAXHub 가 인스턴스를 바꾸는 사이의 옛·새 프로세스, 그리고 WP5a 가 '러너 잠금 주인'·`runner_lock_held` 로 대비한 바로 그 경우다(spec-wp5a 571행).
- 고치는 법(C9). L6 을 '같은 DB 파일을 여는 `RiskStore` 객체 N개(워커마다 하나)' 로 바꾼다 — 연결과 락이 따로라 SQLite 파일 잠금만 남는다. 단언은 셋이다. ① 같은 셀을 두 저장소가 선점하면 하나만 성공한다. ② 진 쪽은 `database is locked` 예외가 아니라 '못 집음' 으로 돌아온다(busy_timeout). ③ 러너 잠금을 못 쥔 저장소의 러너는 셀을 하나도 집지 않는다. 재기동 복구(L8)도 '다른 저장소 객체가 `running` 을 남기고 닫힌 뒤 새 객체가 연다' 로 돌린다.

## P-18 (major) 하네스 안전 시험이 늘 도는 pytest 안에서 실 프로세스를 띄울 수 있다

- 근거. `tests/rr/test_rr_stack_safety.py` 는 `tests/rr/` 에 있어 기본 실행에 든다(3.2 표의 T0~T5 '늘'). 내용은 '포트를 미리 점유해 놓고 `rr_stack.sh up` 이 2 로 끝나는지' 다(3.8.3 끝). 지키려는 가드(포트 점검)가 틀렸거나 점유한 포트가 다섯 중 하나뿐이면, 이 시험이 **임시 에이전트 서버를 실 `.env`·실 `mcp_servers.json`(게이트웨이 서비스 토큰)으로 실제로 띄운다** — 사람이 `pytest` 를 칠 때마다. 리포 메모의 전례(상대경로 하네스가 실 apptainer 로 dev nginx 를 내린 사고)와 같은 종류다.
- 고치는 법(C13). ① `rr_stack.sh` 는 띄우는 명령을 `RR_LAUNCH`(기본 `exec`) 한 자리로 지나게 하고, 시험은 `RR_LAUNCH=<마커 파일에 한 줄 쓰고 끝나는 스텁의 절대경로>` 를 준다. 단언은 '종료 코드 2 **그리고** 마커 0줄' 이다. ② 포트 점검은 다섯 포트를 **전부** 본 뒤에야 첫 프로세스를 띄운다(하나씩 보고 하나씩 띄우지 않는다). ③ `down` 시험의 '남의 PID' 는 시험이 직접 띄운 `sleep` 자식으로 한다. ④ 띄우는 명령에 `--host 127.0.0.1` 을 명시하고 시험이 스텁 인자에서 확인한다 — 임시 에이전트 서버는 인증이 없고 본문의 `groups`·`user_email` 을 그대로 게이트웨이 신원으로 싣는다(`HWAXAgentServer/start.sh:37~50` 의 경고). 이 박스는 공인 IP 가 직접 붙어 있다.

## P-19 (minor) 하네스의 상태 자리와 '밖에 안 썼다' 판정이 정해지지 않았다

- `up`·`down`·`status` 는 따로 불리는데 `T="$(mktemp -d)"` 를 어디에 적어 두는지가 없다. 동시 실행 잠금 `mkdir "$LOCK"` 의 자리도 없고(`$T` 아래면 잠금이 아니다), 죽은 뒤 남은 잠금을 누가 푸는지도 없다. 고치는 법 — 고정 자리 `${XDG_RUNTIME_DIR:-/tmp}/rr-stack.<uid>/` 를 잠금 겸 상태 디렉터리로 쓴다. 안에 `tmpdir`·`pids`·`ports.env` 를 둔다. `status` 는 적힌 PID 가 다 죽었으면 '낡은 잠금' 이라고 말하고 `down --stale` 만 지운다. `rm -rf "$T"` 는 `$T/.rr-temp` 가 있을 때만 한다.
- 5.1절의 '임시 디렉터리 밖에 쓰지 않는다(실 저장소 파일의 mtime 과 크기를 앞뒤로 견준다)' 는 여러 세션·사용자가 쓰는 dev 에서 늘 거짓 경보다 — 포털 감사 원장·대화 저장소는 남의 요청으로도 바뀌고, 게이트웨이 `audit.jsonl` 은 하네스 자신이 바꾼다고 3.8.2 가 적었다. 고치는 법 — 하네스가 띄운 PID 각각의 `/proc/<pid>/fd` 를 읽어 쓰기로 연 정규 파일이 전부 `$T` 아래인지 본다(단계마다 한 번).
- SSO 단언으로 들어온 호출자는 `role=None` 이라 관리자 경로가 닫힌다(`identity.py:196~200`). 하네스가 WP5a 의 관리자 경로(`GET /api/meta/runtime` 등)를 판정에 쓰면 403 이다. S0 의 확인 항목은 소유자 경로만 쓰게 적는다.

## P-20 (minor) S0 의 '`limits` 가 K 를 1 이상으로 준다' 는 늘 참이다

- 근거. WP3a 의 식이 `K = max(1, min(CARD_REVIEW_K, K_out))` 다(spec-wp3a 3.3절). dev(16,384)에서 실제로 갈리는 것은 `CARD_V` 3,393자다 — 그보다 긴 카드는 `FIXED + B + 카드 > P_hard` 라 `oversize` 로 빠진다(같은 절). 설계서 3.8.4 의 '카드 2~3장과 단위 본문 6,000자' 는 그 표(B 3,008자 · 카드 1~2장)와도 다르다(계약 C-17 이 이미 3,008 로 적었다).
- 고치는 법. S0·S1 통과 기준을 '`ctx_assumed == false`, 실은 팩의 `oversize` 카드 0(있으면 수와 길이를 기록), 단위 재빌드 뒤 `unit_size ≤ unit_body_max` 위반 0' 으로 바꾼다. `oversize` 카드가 있는 전문가의 셀이 dev 에서 `reviewed` 가 될 수 있는지는 WP3b 의 `rows_expected` 정의에 달렸다 — S1 의 '9칸 전부 reviewed 또는 사유 있는 failed' 에 'oversize 로 빠진 카드는 기대 수에서 빠지고 셀에 표기된다' 를 더한다.

## P-21 (minor) 카나리아 시험이 `output_gz`·호출 원장에는 헛통과한다

- 근거. 카나리아는 '인용될 일 없는 절' 에 심는다(3.3.6). 가짜 LLM 은 그 절을 인용하지 않으므로 모델 원답(`output_gz`)·결과 프레임에는 애초에 카나리아가 없다. 3.10.1 설계 1 이 '호출 원장의 `output_gz` 도 같은 시험에 넣는다' 고 한 부분은 반출에 그 열이 실려도 초록이다.
- 고치는 법(C12). 카나리아를 둘로 한다. `CANARY-PACK-<hex>` 는 지금대로(묶음 원문 누출). `CANARY-QUOTE-<hex>` 는 가짜 LLM 이 `cq` 로 **인용하게** 하고, 단언은 '판정 행·전문가 보고서에는 있다(결정 3) · 반출에서 `LOCAL_ONLY` 로 뺀 표의 줄에는 없다 · AIDataHub 로 갈 발췌에는 없다(3.10.1 설계 4) · 로그에는 없다' 로 자리마다 가른다.

## P-22 (minor) 리포 간 요청 검증의 실행 조건이 비어 있다

- 근거. 3.5절은 리스크가 조립한 `run` 본문을 '형제 리포의 `card_review` 요청 검증에 서브프로세스로(`_PORTAL_VALIDATE` 와 같은 방식)' 넣는다. 그 방식은 리스크 venv 의 파이썬을 형제 디렉터리에서 돌린다(`test_wiring_regressions.py:359` — `sys.executable`, `cwd=backend`). 리스크 venv 로 에이전트 서버를 불러 보니 `deliberation`·`thinking` 은 import 되고 `app` 은 `langchain_mcp_adapters` 가 없어 실패한다. WP3a 의 `card_review` 는 창을 `app._model_context_tokens()` 에서 늦게 읽는다(spec-wp3a 76·196행). 예산 검사(XU10 이 '여기서 같이 걸린다' 고 한 것)가 `app` 을 건드리면 서브프로세스는 실패하고, 기존 관례(`:362`)대로면 skip 이다.
- 고치는 법(C7 + WP3a 걸음 1). `card_review.limits(ctx_tokens:int, llm_max_tokens:int|None)` 와 `validate_request(body, limits)` 를 `app` 을 import 하지 않는 순수 함수로 둔다(그 사실을 에이전트 쪽 AST 시험이 지킨다). 리스크 시험은 창 16,384 와 128,000 을 인자로 준다. 서브프로세스가 import 에 실패하면 skip 이 아니라 fail 이다(형제가 곁에 있을 때).

## P-23 (minor) 잔 어긋남

- 공장 기본값 `make_project(code="SYN-1")` 은 `UNIQUE(owner_sub, code)` 라 한 저장소에서 두 번 부르면 409 다(`routes.py:424~` 독스트링). 같은 과제에 타깃을 둘 만들면 `_supersede_previous_target`(`routes.py:1905~1950`)이 앞 타깃을 닫고 좌석을 carried 로 넘긴다 — 얼린 DB 의 '타깃 셋' 과 보안 시험의 '남의 과제' 는 과제를 따로 써야 한다. 공장이 `code` 를 씨앗에서 유도하게 한다.
- `routes.create_target` 은 인자로 받은 저장소가 아니라 모듈 전역 `get_store()` 를 쓴다(`routes.py:1988`). 공장의 `store` 인자가 무시되지 않게 공장 안에서 `routes.get_store` 를 그 저장소로 바꿔 끼우고 되돌린다(기존 시험의 방식, `test_e2e_smoke.py:76~77`).
- `rr_large` 표식은 `pyproject.toml` 의 `markers` 에 등록하고 기본 `addopts` 에 `-m "not rr_large"` 를 넣어야 맨 `pytest` 가 `syn600`(상한 300초 × 변형)을 돌지 않는다. 설계서는 `rr_verify.sh` 에만 그 선택을 적었다. 벽시계 상한 단언(60초·300초)은 공유 dev 박스에서 흔들리므로 실패가 아니라 경고 + 기록으로 둔다.
- `FakePanelEngine` 은 지금 세 벌이다(`test_runner_panel.py:81`·`test_e2e_smoke.py:167`·`test_engine_client.py:603`). 가드 E 가 어느 것을 보는지 정하고 C14 에서 `tests/fakes_panel.py` 한 벌로 모은다.
- `planted_real.json` 의 `(agent_key, card_id)` 는 dev 코퍼스에서 고른다. cae00 코퍼스에 그 카드가 없거나 본문이 고쳐졌으면 분모가 조용히 준다. 파일에 카드의 `upstream_checksum` 을 같이 적고, 실행 머리에서 '없는 카드·체크섬이 다른 카드' 를 세어 0 이 아니면 그 쌍을 빼고 목록을 찍는다.
- S0 ③ 은 에이전트 서버만 내렸다 올린다. 운영에서 가장 잦은 끊김은 포털(중계) 재기동이다. 임시 포털을 내렸다 올리는 사례를 같은 단언(차감 없이 `pending` → 이어 돈다)으로 더한다.

- 2.5절은 '`plat:risk` 와 `plat:aidatahub` 사이에 함의가 없다' 고만 적었다. `feat:deliberation` 은 이미 `plat:aidatahub` 를 함의한다(`config/access.yaml:30~33`, 함의는 플랫폼 항목에도 걸 수 있다 — `policy.py:206~213`). 카드 대조 중계가 `feat:deliberation` 을 요구하므로 포털을 지난 호출자는 늘 `plat:aidatahub` 가 있다. 3.10.2 의 '`plat:aidatahub` 없는 자격으로 `pack`' 사례는 포털 경유로는 안 생기고 에이전트 서버에 `groups` 를 직접 준 시험으로만 만들 수 있다. 결정 3 의 함의 한 줄은 '보고서만 보는 사람(`plat:risk` 뿐)' 을 위한 것으로 좁혀 적는다.

---

## 뺄 것 · 미룰 것 (cuts)

1. 카드당 인용 합 30% 상한(3.10.1 설계 2 뒷절 · 시험 '인용 상한' 둘째 단언) — 계약 C-15 와 부딪치고 주인이 없다(P-15). 잃는 것은 '보고서 여러 장으로 카드의 규칙 절을 거의 복원할 수 있다' 는 것. 지금 독자는 전부 카드를 볼 수 있다. 조직 밖 독자에게 보고서를 열 때 다시 본다.
2. 결정 2 의 자동 재실행과 타깃 단위 상한 차단(뒤집힘 · 순서 · 훑기 놓침) — 통계상 거의 늘 걸린다(P-13). 표기 전용으로 내린다. 잃는 것은 기준 밖 타깃이 스스로 다시 돌지 않는다는 것. 실제 과제 세 건의 분포를 본 뒤 문턱을 건다.
3. 하네스의 `HWAXRISK_AIDH_API_KEY` 복사(3.8.1) — 계약 C-10 이 그 경로를 안 쓴다. 지금 코드도 런타임에 그 클라이언트를 안 붙인다(`adh_client_from_settings` 호출처 0). 잃는 것 없음. 실 비밀을 임시 디렉터리로 옮기는 걸음이 하나 사라진다.
4. `rr_gateway_check.py`(C15)와 update-all 배선(D9) — 부르는 쪽이 없다(WP5a 는 실행 전 점검에서 그 실행의 자격으로 `tools/list` 를 직접 묻는다). 잃는 것은 배포 뒤 새 MCP 도구 미노출의 자동 적발. 새 MCP 도구를 실제로 더하는 커밋과 같이 넣는다.
5. `syn600` · 벽시계 상한 단언 · '넷 전부 × 변형 일곱 전부' — `syn3`·`syn40`·`syn150` 과 `syn40 × 변형` 만 남긴다. 잃는 것은 600건급 입력의 재분할 · 시간 회귀를 미리 보는 것. 5.2절이 '첫 실제 diff 의 분포로 구성을 고친다' 고 했으니 그때 만든다.
6. 주입 보고 시 '가른 재발주'(7.4 P3 · D6)와 `xp.inj_ab` — 계약에 안 들어갔다. 구획 탈출 · 2차 주입 · `rv.inj` 표기 시험은 남긴다. 잃는 것은 순응하는 모델이 주입 카드와 한 묶음인 다른 카드를 걸림 없음으로 닫는 것을 자동 격리하지 못한다는 것. 사내 저작 카드가 아닌 문서(논문 · 특허)를 판정 카드로 쓰기 시작할 때 넣는다.
7. dev 실 LLM 의 S2(mech 19명) — S0 을 가짜 LLM 으로 19명 × 단위 수까지 키우고 S1(9칸)만 실 LLM 으로 한다. 잃는 것은 7B 에서의 동시성 · 재개 실측(운영 타깃이 아니다). cae00 fixture 과제의 S2 품질과 합친다.
8. 가드 E 의 실주행 채집과 긁개(`scrub()`) — 에이전트 서버 스트림 시험이 낸 프레임을 표본으로 쓴다(P-11 ②). 잃는 것은 실 LLM 에서만 나오는 프레임 변종. S1 에서 새 프레임 종류가 실제로 보이면 그때 더한다.
9. 3.9.2 의 '쟁점 브리프 예제를 JS 시험에 먹이기' 와 MCP evidence_only 집계 시험 — 계약 C-30 이 새 흐름 타깃에서 JS 경로를 막는다. '막힌다(안내문)' 한 건으로 바꾼다. 잃는 것 없음.
10. `review_quality` 가 다시 세는 `rv.grid`·`rv.cards`·`rv.na_audit` 와 부록(영역별 표 · 전문가 이상치 상위 10) — WP4 의 `cell_counts` 를 불러 쓴다(P-16). 잃는 것은 첫 판 보고서의 영역 · 전문가별 이상치 표.

## 직접 확인해 맞았던 것 (confirmed)

- 씨앗 출처 래칫의 기준선 — `INSERT INTO rr_diffs 8 · rr_diff_events 4 · rr_states 9 · rr_snapshots 16 · rr_panels 15` 가 지금 `tests/` 에서 그대로 세어진다.
- 2.3절 실례 — `brief.py:1016` 이 `agent_key` 를 읽고 `planner.py:425·450` 이 `key` 로 쓴다. `brief.py:514·551` 이 `diff_json` 최상위의 `dims_delta`·`result_delta` 를 `name`·`base`·`target` 으로 읽는다. `brief.py:481` 이 `layer IN ('semantic','structural')` 을 읽는데 `_event_rows` 는 `semantic` 만 쓴다. `runner.py:1383~1384` 가 `level.get("raised")` 를 본다.
- dev 의 리스크 시험에서 지금 건너뛰는 것은 `test_parity.py` 2건뿐이다(skip 이 있는 일곱 파일만 캐시 없이 돌렸다).
- `freeze_snapshot` → `create_diff` 는 네트워크 없이 임시 DB 에서 생산자 경로 전체를 탄다(직접 돌렸다).
- 에이전트 서버 `start.sh` 는 포트의 옛 리스너를 kill · kill -9 하고, `.env` 를 환경보다 **우선** 으로 export 하며, 기본 바인드는 `127.0.0.1` 이다(`:37~50` — 설계서 9절의 '9009 가 밖으로 닫혀 있는지' 는 기본값에서는 닫혀 있다).
- `ui-check.sh` — 저장소 경로 아홉을 임시로, 포트가 쓰이면 2 로 끝남, 자기 PID 만 내림.
- `rr_audit.scope` CHECK 10종 · `action` 은 자유, `rr_metrics.dimension` CHECK 6종, `export.TABLE_ORDER` 가 DDL 에서 자동 추출, 이행 직전 `pre-migrate-<ts>` 사본.
- 품질 블록 문면 예시가 `render.lint_text` 를 통과한다. '문제없음' · '심각도 중대' · '판정 FAIL' 은 걸린다.
- 게이트웨이 `/tools-map` 은 무인증이고 도구 이름 → 백엔드 사상을 준다. 리스크 MCP 도구는 `@mcp.tool()` 14종이다.
- 엔진 — 지식카드 근거 프레임 `source='<키> · 지식카드'`(`deliberation.py:4139`), `save_report=1` 기본(`:894`), `finish_reason=='length'` 절단 표식(`:1647~1652`).
- nginx `location /agent/` 가 새 중계 경로도 덮는다(버퍼링 끔 · 침묵 한도 손잡이).
- 정확 이항 상한 — 0/59 → 4.95%, 2/59 → 10.29%, 3/120 → 6.33%(설계서 문면의 수와 같다).

## 확인하지 못한 것 (unknowns)

- cae00 에 리스크 앱 · 에이전트 서버의 호스트 venv 가 있는지, cae00 코퍼스의 카드 id · 체크섬이 dev 와 같은지, GLM 의 창 · 출력 상한.
- 서비스 PAT(`HWAXRISK_PORTAL_PAT`)의 주체가 `feat:deliberation` 을 갖는지 — 없으면 서비스 계정으로 내려간 실행은 중계에서 전부 403 이다(비밀 파일을 열지 않았다).
- 임시 포털(mock 인증)이 찍는 PAT 가 리스크 앱의 등록 조건(읽기 전용 범위 · 남은 수명 > `credential_margin_s`)을 채우는지.
- scipy 없는 리스크 venv(순수 파이썬 헝가리안)에서 노드 450 이상의 `sameas`·`diff` 시간.
- `part.replaced`·`part.split`·`part.merged`·`g2_fail` 을 어댑터 결과 수준에서 안정적으로 만들 수 있는지(넣어 보지 않았다).
- WP3b 가 `oversize` 로 빠진 카드를 기대 수에서 빼는지(dev 16K 에서 셀이 `reviewed` 가 될 수 있는지가 여기 달렸다).
- 쟁점 패널 단계에서 임시 에이전트 서버가 서비스 계정으로 실 RA · 실 포털 대화에 실제로 쓰는지(코드로 따라가지 않았다).
- 세 리포의 전체 시험은 돌리지 않았다. WP3b 의 러너 절과 WP4 의 종합 절은 접점만 grep 으로 읽었다.

## 판정 (verdict)

코드에 대한 주장은 대부분 맞고(직접 연 것 스물 남짓이 그대로였다) 시험 층의 뼈대는 선다. 그러나 바닥에 까는 장치 몇이 이대로는 첫 커밋에서 깨진다 — 건너뜀 예산이 xfail 을 세고, 합성 픽스처의 기초 단언(`diff_hash` 동일 · 크기 == 이벤트 수 · 33종)이 생산자 코드와 어긋나며, C2 가 아직 없는 것에 기댄다. 실주행 절반은 서지 않는다 — 임시 리스크 앱이 실 에이전트 서버의 `/health` 를 읽고, 실전문가 로스터를 받을 길이 없으며, cae00 단계에는 합성 타깃과 심은 변경을 넣을 길이 없고, 누구 자격으로 돌았는지가 원장에 거짓으로 남는다. 품질 기준은 통계상 거의 늘 '기준 밖' 이고 품질 블록을 싣는 쪽이 없다. 데이터를 망치거나 떠 있는 서비스를 내리는 걸음은 찾지 못했다(blocker 0 · major 16 · minor 7) — 계획서에 옮기기 전에 major 를 고치고 cuts 열 개를 덜어 내면 선다.

(검토 중 동작 확인용 탐침 — 스크래치 디렉터리의 임시 스크립트 · 임시 DB — 을 만들어 썼고 끝난 뒤 지웠다. 네 리포의 `git status --porcelain` 은 0줄이다.)
