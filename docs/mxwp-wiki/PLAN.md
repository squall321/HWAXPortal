# MX WhitePaper 완전 연결 · LLM 위키 — 포털 쪽 몫

> 2026-10-24 · 사용자 요청 — "mx whitepaper 도 SSO 연동 포함해서 다 연결되었으면 좋겠어. 그리고 mx whitepaper 는 llm wiki 에 필요한 기능들을 추가해서
> 넣었으면 좋겠어 … 시장불량 데이터(cae00 에 있는 데이터들)와 시뮬레이션 플랫폼으로부터 얻어지는 인사이트들을 온톨로지화하고 사람들이 묻거나 해결한
> 문제들을 이용해서 자연스럽게 llm-wiki 에 지식이 쌓이는 구조를 만들고 싶어. 제안되는 구조가 있는지의 여부와 있다면 mx-whitepaper 에 개발 요청으로
> 디테일하게 써줘야 해."
>
> **정본 요청서는 MXWhitePaper 리포 `docs/llm-wiki/`**(request · CONTRACTS · SCHEMA-DRAFT · START · checklist · context-notes). 거기서 MXWP 세션이
> 개발한다. 이 폴더는 **포털 · 게이트웨이 · 에이전트 서버가 할 일**(그 요청서의 P1~P9)과 순서만 적는다.

## 1. 답 — 제안된 구조가 있나

있다. Karpathy 의 'LLM Wiki'(gist `karpathy/442a6bf555914893e9891c11519de94f`, 2026-04-04) — 원천(불변) · 위키(LLM 이 쓰고 유지) · 규칙서 세 층,
들이기 · 묻기(좋은 답은 되쌓기) · 점검 세 작업, `index.md` · `log.md`. 개인 · 한 사람 큐레이터 전제라, 사내용으로 블록 근거 · 보이기 범위(포털 권한표를
따른다) · 변경 묶음과 검토 · 온톨로지 · 작업 실행기를 더한다(MXWP `docs/llm-wiki/request.md` §1).

## 2. 지금 연결 상태(2026-10-24 조사)

| 항목 | 상태 |
|---|---|
| 타일 SSO(jwt-handoff, `systems.yaml` `mx-white-paper`) · 로그아웃 연동 · nginx 라우트(`routes.env` 46~51행) · 배포 · 상태판 · `plat:mxwhitepaper` | 됨(실제 로그인 끝까지 확인한 기록은 없다) |
| 게이트웨이 MCP 백엔드 `mx-white-paper` | 됨 — 그러나 **서비스 토큰**(`admin@mx.local`) 명의. 위임 없음(`per_user_sso` 에 없다), REST 다리는 `inject`(GET · HEAD 만) |
| 포털 → MXWP 쓰기 | 챗 문서 메뉴 'MX 백서에 싣기' 는 지시문만 채운다(`DocActions.tsx` `key: 'wiki'`) · 업로드 목적지 없음 · 심의 결정문은 RA 로만 |
| 소속 · 플랫폼 권한 전달 | 진입 토큰 `groups` 에는 원장으로 센 `plat:` · `feat:` 합성 그룹이 **원래 실린다**(`deps.entitled` → `with_entitlements`) — 소속만 없다. 게이트웨이는 위임 백엔드에 소속 + 증명은 싣지만 `plat:` 는 안 싣는다 |
| MXWP 설정 킷(`infra/env-kits/mx-white-paper.env`) | 새 박스에서 손으로(update-all 은 에이전트 서버 킷만) |

## 3. 할 일(포털 · 게이트웨이 · 에이전트 서버)

MXWP 쪽 C1(위임 창구)이 dev 에 올라오기 **전에는** P1 · P5 의 비밀을 넣지 않는다 — 위임이 켜지는 순간 MXWP 호출은 그 창구가 없으면 거부로 바뀐다
(RA 때와 같은 규칙 — `docs/sso-delegation/PLAN.md` §2-2).

| # | 리포 · 파일 | 할 일 | 의존 |
|---|---|---|---|
| P1 | HWAXMcpGateway `provision.env`(설정만) | `PER_USER_SSO_APPS` 에 `mx-white-paper:MXWP` · `MXWP_SSO_SECRET` · `MXWP_SSO_URL`(기본 `http://127.0.0.1:8800/api/v1/auth/sso`) · `MXWP_SEND_PLAT=1`(P4). 일반 길이라 코드 수정 없음(`provision-config.sh` `PER_USER_SSO_APPS` 순회). 목록 조회용 서비스 헤더는 남긴다 | MXWP C1 |
| P2 | HWAXMcpGateway `provision-config.sh` | REST 다리 `rest["mx-white-paper"]` 를 **위임이 있을 때만** `per_user`(ste 줄과 같은 모양), 없으면 지금처럼 서비스 토큰 주입 — 위임 창구가 없는 MXWP 판에서 REST 가 끊기지 않게. `rest_call` 쓰기도 그 사람 명의로 열린다 | P1 — **10-24 구현** |
| P3 | HWAXPortal `backend/app/auth/downstream.py` · `routes/launch.py` · `schemas/system.py` · `systems.yaml` | 진입 토큰에 소속 `affiliation` 클레임 — **시스템별 켜기**(`claims_affiliation: true`, MXWP 만). `plat:` 은 원래 `groups` 에 실리므로 더하지 않는다. 값은 이번 요청에 원장으로 센 소속(`request.state.entitlements`), **권한표에 없는 소속 id 와 빈 값은 칸 자체를 뺀다**(게이트웨이 `/internal/access/entitlements` 와 같은 규칙). 시험 `tests/test_launch_affiliation_claim.py` — 켠 시스템만 · 빈 값 · 지운 소속 · 추적 카탈로그에서 켠 것은 MXWP 하나 | 없음 — **10-24 구현** |
| P4 | HWAXMcpGateway `gateway.py`(`_plat_proof` — 소속 증명 옆) · `provision-config.sh` | 위임 호출에 `X-Heax-User-Plat`(`plat:` 만 정렬 · 쉼표 · 퍼센트 인코딩) + `X-Heax-Plat-Proof`(`v1|<email>|<정렬한 목록>|<exp>` HMAC-SHA256, 같은 앱별 비밀, 120초) — **앱별 켜기**(`per_user_sso.<앱>.send_plat` 이 참일 때만 — provision.env `<접두>_SEND_PLAT=1`, 안 적으면 이어받기 · 0 이면 끔). 값은 게이트웨이가 확인한 그룹(`_request_groups`)에서만. 목록이 비면 두 헤더를 지운다 | P1 — **10-24 구현** |
| P5 | HWAXPortal `infra/scripts/update-all.sh` | 일반 길이라 비밀 · 주소는 **게이트웨이 provision.env** 에 둔다(P1) — update-all 은 이미 그 값들을 provision 에 넘기고(`_sso_generic_names`) · 비면 `PER_USER_SSO_OFF` 로 끄고 · config 와 어긋나면 재프로비저닝한다. 빠져 있던 것은 `<접두>_SEND_PLAT` 하나 — 넘기기와 어긋남(`<키>_sso_plat`)을 더했다. MXWP `.env` 의 같은 비밀은 **사람이** 넣는다(RA 와 같다 — 비밀이 두 리포 파일에 갈라지는 자리라 한 번에 손으로). **비밀은 자동 생성하지 않는다** | 없음 — **10-24 구현**(f7c9c7b) |
| P6 | HWAXPortal 백엔드 + `DocActions.tsx` | 답 아래 **'위키에 남기기'** — 서버가 저장된 그 턴(질문 · 최종 답 · 활동 요약)으로 `qa` 봉투를 지어(화면이 보낸 근거를 믿지 않는다) 그 사람 명의로 MXWP `POST /api/v1/wiki/sources`. 사람 토큰은 `app/auth/ra_sso.py` 꼴의 도우미(`X-Heax-Client: hwax-portal`). 성공은 대화에 알림 + 업로드 근거(챗 PPT 때의 '보낸 결과를 대화에 남기기' 와 같은 길) | MXWP W1 · W2 · W3 |
| P7 | HWAXPortal 백엔드 · 화면 | **'해결됨'** 표시(턴 단위) → 위키 **후보**(주인만 보는 `held` 원천, 7일). 자동 후보(자기검증 통과 + 도구 근거 + 이어지는 '됐다') 여부는 사용자 결정(MXWP request §11 Q1, 권장 B) | P6 |
| P8 | HWAXAgentServer `deliberation.py` | 심의 결정문을 RA 와 함께 위키에도 — 게이트웨이 도구 `wiki_submit_source`(사람 명의로 게이트웨이가 위임)로 `deliberation` 봉투. 버린 근거 · 소수 의견을 빼지 않는다. 심의 옵션 `delib_opts.wiki`(기본 꺼짐 — 결정 Q1 과 함께) | MXWP W6 |
| P9 | HWAXPortal 상태판 · 이력 · services.yaml | `gen-status-config.py` 에 MXWP `/api/v1/wiki/health` · `infra/services.yaml` MXWP 항목에 여섯째 인스턴스 `mxwp_wiki`(MXWP W3 뒤) · 바뀔 때마다 `backend/config/changelog.yaml` | MXWP W3 |
| P10 | HWAXAgentServer · 페르소나 | `wiki_*` 도구가 게이트웨이 `tools/list` 에 뜬 뒤 — 도구 영역(`HWAXMcpGateway/tool_areas.json`)에 넣고, 페르소나 `he-doc-mxwhitepaper`(`infra/personas/he-team.json`) 안내문에 '위키 먼저 묻기' | MXWP W6 |

하지 않는 것 — MXWP 코드는 여기서 고치지 않는다(그 리포 세션 몫). 대화 저장소를 일괄로 내보내지 않는다(주인만 읽는다는 약속 — 위키로 가는 것은 주인이 보내거나
승인한 턴뿐). 공유 비밀을 다른 앱과 같이 쓰지 않는다(앱마다 따로).

## 4. 순서

```text
MXWP W0 ─▶ MXWP C1 위임 창구 ─▶ P1 · P2 · P5(dev 비밀) ─▶ §5 확인
       └─▶ P3 · P4(소속 · 플랫폼 전달) ─────────────────────▶ MXWP W2 완료(범위)
MXWP W3(원천 · 작업) ─▶ P9 상태판 · services.yaml
MXWP W6(MCP · 묻기) ─▶ P6 · P7 ─▶ P8 · P10
```

## 5. 다 됐는지 확인(포털 쪽)

- dev — 비밀을 넣기 전: 게이트웨이 감사 원장에서 MXWP 호출은 지금처럼 서비스 계정. 넣은 뒤: 포털 챗이 만든 MXWP 문서의 소유자가 그 사람 · 감사 줄이 사람 명의 모드.
- 비밀을 비우고 update-all → 위임이 꺼지고(`PER_USER_SSO_OFF`) 서비스 계정으로 돌아온다(되돌리기가 된다).
- P3 — `claims_affiliation` 을 켠 MXWP 진입 토큰에만 `affiliation` 이 있고 다른 jwt-handoff 앱의 토큰은 그대로(`tests/test_launch_affiliation_claim.py`).
- P4 — MXWP 가 받은 `X-Heax-Plat-Proof` 를 다른 이메일 · 만료 · 목록 바꿈으로 시험해 거부되는지(MXWP 쪽 시험과 짝).
- 타일 로그인 — dev · cae00 에서 브라우저로 끝까지 한 번(사람).

## 6. cae00(사람)

MXWP 위임 창구(C1)가 그 박스에 올라온 뒤에 한다.

1. 비밀 하나를 만든다(`openssl rand -hex 32`) — 메신저 평문 말고.
2. 게이트웨이 `HWAXMcpGateway/provision.env` 에 넷 — `PER_USER_SSO_APPS` 에 `mx-white-paper:MXWP` 쌍(이미 다른 쌍이 있으면 공백으로 덧붙인다) ·
   `MXWP_SSO_SECRET=<비밀>` · `MXWP_SSO_URL=http://127.0.0.1:8800/api/v1/auth/sso` · `MXWP_SEND_PLAT=1`.
3. MXWP `.env` 에 같은 비밀(`MXWP_SSO_SECRET=<비밀>`) → `mxwp_api` 재기동(MXWP 의 방식대로).
4. update-all → 로그에 `✓ mx-white-paper 사람별 위임 — … · plat 권한 전달` 이 나오는지, §5 확인.

끄기 — provision.env 의 `MXWP_SSO_SECRET` 을 비우고 update-all(서비스 계정으로 돌아간다). 시장불량 쪽 — 위키 워커의 읽기 전용 PAT 에
`plat:plmdefect` 를 줄지는 권한표 담당이 정한다(MXWP request §11 Q8). 실데이터 연결(W8)은 cae00 에서만.
