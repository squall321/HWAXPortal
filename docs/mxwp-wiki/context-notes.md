# MX WhitePaper 완전 연결 · LLM 위키 — 결정과 까닭(포털 쪽)

> MXWP 쪽 결정은 MXWhitePaper `docs/llm-wiki/context-notes.md`(WK-D). 여기는 포털 · 게이트웨이 · 에이전트 서버에 걸린 것만 MW-D 번호로.

## 2026-10-24

- **MW-D1 요청서는 MXWP 리포에 둔다(정본), 포털에는 포털 몫만.** 까닭 — MXWP 는 사용자 자기 리포이고 그 리포의 VS Code 세션이 개발한다(DocForge 때와 같은 꼴 —
  `docs/doc-to-ra/`). 포털 세션이 읽는 곳에는 포털이 할 일만 있어야 같은 판단을 두 곳에서 다시 하지 않는다.
- **MW-D2 신원은 ste 방식 위임(일반 길 `PER_USER_SSO_APPS`)으로, 토큰 등록(`connect:`)이 아니다.** 까닭 — MXWP 는 같은 박스 · 같은 포털이 배포하는 앱이라
  비밀 하나로 끝난다. `connect:` 는 같은 키의 정적 백엔드(`mx-white-paper`)가 있으면 게이트웨이가 겹침으로 무시한다(`provision-config.sh` 의 '끄기' 안내문).
- **MW-D3 진입 토큰의 `access` 클레임은 시스템별로 켠다.** 까닭 — 소속 · 플랫폼 권한은 그것을 쓰는 앱에만 보낸다. 모든 jwt-handoff 시스템의 토큰을 한꺼번에
  바꾸면 쓰지도 않는 앱에 소속이 퍼진다.
- **MW-D4 `plat:` 전달은 소속 증명과 같은 서명 규칙으로, 앱별로 켠다.** 까닭 — 평문 헤더는 사용자가 앱 정문에 직접 붙어 스스로 적을 수 있다(게이트웨이
  `AFF_PROOF_HEADER` 주석의 논리 그대로). MXWP 위키는 PLM 결함 검색(`plat:plmdefect`)에서 온 사실을 그 권한이 있는 사람에게만 보여야 한다.
- **MW-D5 '위키에 남기기' 봉투는 포털 서버가 저장된 턴으로 짓는다.** 까닭 — 화면이 보낸 근거를 믿으면 사람이 근거를 꾸며 위키에 넣을 수 있다. 대화 저장소는
  주인만 읽으므로 그 사람 명의 요청 안에서만 짓는다.
- **MW-D6 대화를 일괄로 내보내지 않는다.** 위키로 가는 것은 주인이 보낸 턴 · 승인한 후보뿐(권장 B — MXWP request §11 Q1, 사용자 결정 대기).
- **MW-D7 비밀은 자동 생성하지 않는다(RA 때와 같은 까닭)** — MXWP 위임 창구가 준비되기 전에 비밀이 생기면 게이트웨이가 위임을 켜고 그 순간 MXWP 호출이
  거부로 바뀐다.
- **MW-D8 MW-D3 을 좁힌다 — 진입 토큰에 더하는 것은 소속(`affiliation`) 하나다.** 까닭 — 코드를 보니 진입 토큰 `groups` 에는
  `deps.entitled` 가 그 요청에 원장으로 센 `feat:` · `plat:` 합성 그룹이 이미 실린다(`JwtDownstreamIssuer.mint` 가 `principal.groups` 를 그대로
  싣는다). `access{affiliation, plat[]}` 묶음은 같은 값을 두 번 싣는 셈이다. 소속은 권한표에 없는 id 면 빼고(게이트웨이용
  `/internal/access/entitlements` 와 같은 규칙), 켜는 것은 시스템별(`claims_affiliation`)로 남긴다.
- **MW-D9 게이트웨이 `plat:` 헤더는 앱별 설정 `send_plat` 이 참(True)일 때만, provision 은 `<접두>_SEND_PLAT` 이 적혀 있을 때만 그 값을 바꾼다.**
  까닭 — 문자열 설정을 켠 것으로 읽으면 손으로 넣은 오타가 권한 목록을 퍼뜨린다. 안 적은 실행이 끄면 손으로 돌린 provision 한 번에 위키의
  `plat:` 범위가 조용히 닫힌다(이어받기 — RA · TestScope 비밀과 같은 규칙).
- **MW-D10 REST 다리는 위임이 있을 때만 `per_user` 로.** 까닭 — 위임 창구(MXWP C1)가 없는 판에서 바꾸면 지금 되는 GET 이 '위임 설정이 없다' 로
  끊긴다. 위임이 생기면 `credential_mode` 가 `per_user` 를 먼저 보므로 주입 토큰은 남기지 않는다.
- **MW-D11 P5 는 '넘기기 하나' 로 줄었다 — 비밀 · 주소 · 끄기 · 어긋남은 일반 길(`PER_USER_SSO_APPS`)이 이미 한다.** 비밀은 포털 `infra/.env` 가 아니라
  게이트웨이 provision.env 에 둔다(일반 앱의 규칙). 빠져 있던 것은 `<접두>_SEND_PLAT` 이었다 — provision-config.sh 는 `os.environ` 만 읽고
  update-all 은 이름 셋만 넘겨, 켜도 닿지 않고 어긋남도 못 봤다(조용한 결함). MXWP `.env` 에 같은 비밀을 넣는 것은 사람 몫으로 남긴다 —
  RA 와 같고, 비밀이 두 리포의 파일에 갈라지는 자리를 스크립트가 맞추게 하면 어느 쪽이 정본인지 흐려진다.
- **MW-D12 사용자 결정(10-24, MXWP 세션에서 — MXWhitePaper context-notes WK-D15 · WK-D17)** — 대화 수확은 **B(후보 + 한 번 승인)** · 질문자
  비공개, 범위는 토큰 넷 + 위키가 아닌 기존 `restricted` 문서도 같은 필터로 막는다. 그래서 P7 의 '해결됨' → 후보는 이 꼴로 짓는다(주인만 보는
  `held` 원천 · 7일 · 자동 승인 없음). 남은 사람 결정은 Q2 · Q8 · Q11 · Q12.
- **MW-D13 dev 에서 켰다(10-24, 사용자 확인)** — 비밀 하나를 MXWP `.env`(644 → 600 으로 좁힘) · 게이트웨이 provision.env 에, `mxwp_api` 만 재기동,
  게이트웨이 손 재프로비저닝(GW_TOKEN · heax 토큰 보존) · 게이트웨이와 포털만 재기동(에이전트 서버는 같은 GW_TOKEN 이라 그대로). 확인 — 감사
  `as-user-pat` · 만든 문서의 주인이 그 사람 · 신원 없는 호출은 `service` + `no-identity`. 곁가지 셋 — ① 첫 손 실행이 infra/.env 를 export 해
  heax_registry 를 잃은 config 를 썼다(재기동 전에 대조해 잡음 — docs/gotchas.md). ② 재프로비저닝이 `portal.api_base` 를 더해 dev 의 RA 호출도
  09-29 결정대로 본인 등록 토큰으로만 간다(dev config 가 낡아 있었다). ③ `koo.park` 의 MXWP 역할이 reader 라 챗에서 MXWP 쓰기가 403 —
  위임이 맞게 그 사람 역할로 막힌 것이다(예전엔 서비스 계정으로 통과). 역할은 사용자 결정.

- **MW-D14 MX 백서 서비스 토큰은 '살아 있으면 잇고 죽었을 때만 다시' — 다른 플랫폼(DynaForge kr_ PAT)과 같은 규칙으로.** 까닭 — MXWP 시험 둘이
  dev DB 에 `DELETE FROM api_tokens` 를 돌려 게이트웨이 서비스 토큰 둘과 사람들의 개인 토큰이 통째 지워졌고(그쪽 f7484b9 로 시험이 자기 사용자만
  지우게 고침), 게이트웨이는 도구는 뜨고 신원 없는 호출만 401 인 채였다. 또 provision 이 `--force` 마다 토큰을 회전해 떠 있는 게이트웨이의 토큰이
  재기동까지 죽었다. 고친 것 — provision 은 그 토큰으로 `/api/v1/me` 를 물어 산 것은 잇고(게이트웨이 55962dd), update-all 은 죽은 토큰을
  `_mxwp_token_drift` 로 알아 재프로비저닝한다(MXWP 가 안 닿으면 방아쇠로 삼지 않는다). 다른 표를 통째로 비우는 MXWP 시험은 아직 남아 사용자 결정 대기.
- **MW-D15 역할은 다른 플랫폼처럼 포털에서 받아 오지 않는다.** 조사(10-24) — HEAXHub · HWAX Risk · ste · DynaForge · RA · AIDataHub 모두 첫 진입에
  고정 기본값(일반 사용자 · editor · member)으로 만들고 이후 역할은 그 앱 관리자가 관리한다. `groups` · `portal-admin` 을 역할로 바꾸는 곳은 없다.
  MXWP 도 같다(기본 editor · 위임 호출은 admin 을 owner 로 낮춤). `koo.park` 의 reader 는 08-01 생성 때 값이라 MXWP 관리자가 한 번 고칠 일이다
  (MXWP 세션의 권한 판정이 '권한 부여' 로 막아 사용자에게 넘김 — 다른 세션이 대신 하지 않는다).

- **MW-D16 사용자 결정(10-24) — MXWP 시험은 시험 전용 DB 로, 다른 것에 지장을 주지 않게.** MXWP 세션이 끝냈다(그쪽 2dd41f2) — 같은 postgres 의
  `mxwp_test` 를 시험 하네스가 만들어 올리고, 시험 DB 가 dev DB 와 같거나 이름이 `_test` 로 끝나지 않으면 시험이 시작하지 않는다(닫힌 쪽).
  Meilisearch 는 `test_` 접두 · MinIO 는 `mxwp-test-*`. 떠 있는 인스턴스는 그대로였고, 전체 1,336 두 번 동안 dev DB 85 표 51,008 줄이 표마다
  같았다. 뒤에 게이트웨이의 서비스 시야 · 위임 호출 모두 정상(읽기 확인).

## 조사 근거(2026-10-24)

- 게이트웨이 `mx-white-paper` 백엔드 · REST 다리는 서비스 토큰(`HWAXMcpGateway/provision-config.sh` 98~130 · 490~493 · 534~536행 근처).
- 일반 위임 길 `PER_USER_SSO_APPS="<키>:<접두>"` → `<접두>_SSO_SECRET` · `<접두>_SSO_URL`(같은 파일 703~737행 근처) — 정적 백엔드는 키가 곧 위임 id
  (`gateway.py` `_delegation_app_id`).
- 게이트웨이 `/health` 에는 위임 목록이 없다 — provision 이 `✓ <키> 사람별 위임 — <주소>` 를 찍는다.
- 포털 진입 토큰 클레임 — `downstream.py` `JwtDownstreamIssuer.mint`(소속 없음 — `plat:` 은 `groups` 에 원래 실린다. 처음엔 '플랫폼 없음' 으로 잘못 읽었다 → MW-D8).
- 시장불량 원천 후보 — `plm-defect`(cae00 게이트웨이에만, `access.yaml` `plmdefect` · 알려진 도구 `plm_case_detail` · `plm_similar_cases`) · SignalForge.
