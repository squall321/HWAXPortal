# MX WhitePaper 완전 연결 · LLM 위키 — 포털 쪽 체크리스트

> MXWP 쪽 단계는 MXWhitePaper `docs/llm-wiki/checklist.md`. 여기는 [PLAN.md](PLAN.md) §3 의 P1~P10.

## 요청서(2026-10-24)
- [x] 조사 — Karpathy 원문 · MXWP 현황 · 포털 연결 상태 · 원천 위치(시장불량 · 해석 · 대화 · 온톨로지)
- [x] MXWhitePaper `docs/llm-wiki/` 요청서 여섯 · 이 폴더 셋

## 연결 · 신원(MXWP C1 뒤)
- [x] P1 게이트웨이 provision.env — `PER_USER_SSO_APPS` `mx-white-paper:MXWP` · `MXWP_SSO_SECRET` · `MXWP_SSO_URL` · `MXWP_SEND_PLAT=1` — **dev 10-24**(MXWP C1 fc7ddb3 뒤, 사용자 확인) · cae00 은 사람(PLAN §6)
- [x] P2 REST 다리 — 위임이 있을 때만 `per_user`(provision-config.sh) · 시험 — HWAXMcpGateway baa2880
- [x] P5 update-all — 비밀 · 끄기 · 어긋남은 이미 일반 길로 됨, `<접두>_SEND_PLAT` 넘기기 · 어긋남 더함 · 자동 생성 안 함 · 시험 — f7c9c7b(MXWP `.env` 비밀은 사람)
- [x] PLAN §5 확인(dev 10-24) — 감사 원장 `as-user-pat`(호출자 그 사람) · 만든 문서의 주인이 그 사람(DB) · 신원 없는 내부 호출은 `service` + `no-identity`
- [ ] PLAN §5 — 끄면 서비스 계정으로 되돌아오는지(dev 에서 아직 안 해 봄) · 브라우저 타일 실클릭으로 진입 토큰 `affiliation` 이 MXWP 에 들어가는지

- [x] 게이트웨이 MX 백서 서비스 토큰 — 살아 있으면 잇고 죽었을 때만 다시(게이트웨이 55962dd) · update-all 이 죽은 토큰을 알아 재프로비저닝(MW-D14)

## 소속 · 플랫폼 전달
- [x] P3 진입 토큰 `affiliation` 클레임(시스템별 켜기 `claims_affiliation` — `plat:` 은 원래 `groups` 에) · 시험(켠 시스템만 · 빈 값 · 지운 소속) — 703d949
- [x] P4 게이트웨이 `X-Heax-User-Plat` + `X-Heax-Plat-Proof`(앱별 `send_plat` · provision `<접두>_SEND_PLAT`) · 시험 — HWAXMcpGateway baa2880
  - [x] dev 끝에서 끝(10-24) — `plat:plmdefect` 범위 시험 문서가 그 권한이 있을 때만 MCP 로 열린다(없으면 404). MXWP MCP 서버가 헤더를 버리던 것은 그쪽이 고침(39c3c98)
  - [x] REST 다리(`rest_call` · `/api/<site>/`)의 사람별 경로에도 소속 · plat 증명 — 사용자 결정 10-24, HWAXMcpGateway 335213e (클라이언트가 보낸 증명 사본은 뗀다) · dev 반영(게이트웨이 재기동, rest_call 사람 명의 200)

## 쓰기 길(MXWP W1 · W2 · W3 · W6 뒤)
- [x] P6 '위키에 남기기' — 서버가 저장된 턴으로 봉투(`app/agent/wiki_send.py`) · 그 사람 챗 PAT 로 게이트웨이 `wiki_submit_source`(비밀 더 안 쥠) · 대화 알림(업로드 근거) · 감사 · 시험(서버 8 · 브라우저 4) — dev 반영 10-24(포털 재기동, 사용자 확인)
  - [x] dev 끝에서 끝(10-25 KST) — 같은 봉투 · 같은 `mcp_call` 로 게이트웨이를 거쳐 두 원천(바로 남기기 queued · 후보 held), MXWP 쪽이 읽기로 확인(MW-D19)
  - [ ] 사람 몫 — 브라우저에서 버튼 실클릭 · MX 백서 '내 후보' 승인(제안 범위 `aff:` 로 승인하려면 포털을 거쳐 MX 백서에 들어간 세션이어야 한다)
- [x] P7 '해결됨' → 후보(consent candidate — MX 백서가 주인만 보는 held 로, '내 후보' 에서 범위를 골라 승인) — P6 과 같은 길
- [x] P8 심의 결정문 → 위키(`delib_opts.wiki`, 기본 꺼짐) — 엔진이 RA 저장 자리에서 단마다 `deliberation` 봉투 · 사람 명의 · 소속 범위(없으면 후보) · 결정문 끝 안내, MCP `deliberate_start(wiki)` · 이어하기 이어받음, 포털 `DelibOpts.wiki` · 원장 소속 중계 · 심의 옵션 토글(MX 백서 권한) · 시험(엔진 12 — 봉투는 MX 백서 pydantic 모델로 검증 · 포털 중계 1) — MW-D18
  - [ ] dev 반영 — 에이전트 서버 재기동(사용자 확인 10-24) · 포털 재기동과 화면 빌드는 한 묶음(먼저 빌드하면 옛 백엔드가 `wiki` 를 말없이 버린다)
- [x] P9 상태판 — MX 백서 위키 워커 끝점(워커가 있는 판만 · 최근 박동 · 맨 앞이 stopped 아님 · 줄 · 24시간 실패 수) · cae00 배치가 `mxwp_wiki` 도 내렸다 올린다(갈아 끼운 SIF 위에서 깨진 채 남지 않게) · 시험(생성기 1 · 배치 2 — MXWP start.sh 와 대조) · 이력 — MW-D20
- [x] P10 도구 영역 — 위키 쓰기 넷(`wiki_submit_source · wiki_fileback · wiki_propose · wiki_add_question`)은 '데이터 등록·온톨로지', 읽기는 앱 기본 '사내 지식 검색'(게이트웨이 `tool_areas.json`) · 페르소나 `he-doc-mxwhitepaper` '위키 먼저 묻기'(정본 · dev 등록부는 그 한 명만 반영 — `sync-he-personas` 의 `plan` 으로) — MW-D21
  - [ ] cae00 — 페르소나는 `python3 infra/scripts/sync-he-personas.py` 미리보기 뒤 `--apply`(사람 몫, 다른 페르소나의 어긋남도 같이 보인다)

## 사람을 따로 받지 않는다(사용자 결정 10-25 — MW-D22)
- [x] MX 백서 세션이 지었다(그쪽 7c3d2db 서버 · de8c5a3 화면, 설정 `MXWP_SSO_ONLY` 기본 꺼짐 · 비상 관리자 `MXWP_LOCAL_LOGIN_ALLOW` · 진입 링크 `PORTAL_LAUNCH_URL` · 목록 `python -m app.scripts.sso_only_check`) — 게이트웨이 위임 · API 토큰 길은 그대로
  - 진입 링크는 박스마다 **포털 `PUBLIC_BASE_URL` + `/launch/mx-white-paper`** — dev 는 443 앞단(다른 프로젝트 HPC 포털)에도 MX 백서가 열려 있어 상대 주소가 404 다(10-25 확인 — dev 의 MX 백서 요청은 443 의 이 박스 브라우저 한 곳, 포털 진입 콜백 0)
- [ ] dev 켜기 · 끝에서 끝(비밀번호 로그인 403 · 포털 진입으로만 · 하루 넘은 세션도 소속 유지)
- [ ] cae00 — 포털로 들어온 적 없는 계정 목록을 본 뒤 켠다(사람 몫)

## 사람(cae00)
- [ ] 비밀 → 게이트웨이 provision.env 넷 · MXWP `.env` · update-all · 타일 로그인 확인(PLAN §6)
- [ ] 위키 워커 PAT 의 `plat:plmdefect` 여부(권한표 담당)
