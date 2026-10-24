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

## 소속 · 플랫폼 전달
- [x] P3 진입 토큰 `affiliation` 클레임(시스템별 켜기 `claims_affiliation` — `plat:` 은 원래 `groups` 에) · 시험(켠 시스템만 · 빈 값 · 지운 소속) — 703d949
- [x] P4 게이트웨이 `X-Heax-User-Plat` + `X-Heax-Plat-Proof`(앱별 `send_plat` · provision `<접두>_SEND_PLAT`) · 시험 — HWAXMcpGateway baa2880

## 쓰기 길(MXWP W1 · W2 · W3 · W6 뒤)
- [ ] P6 '위키에 남기기' — 서버가 저장된 턴으로 봉투 · 사람 토큰 도우미 · 대화 알림 · 이력
- [ ] P7 '해결됨' → 후보(사용자 결정 Q1 = B, 10-24 — MW-D12)
- [ ] P8 심의 결정문 → 위키(`delib_opts.wiki`, 기본 꺼짐)
- [ ] P9 상태판 `/api/v1/wiki/health` · services.yaml 여섯째 인스턴스 · 업데이트 이력
- [ ] P10 도구 영역 · 페르소나 안내문(게이트웨이 `tools/list` 확인 뒤)

## 사람(cae00)
- [ ] 비밀 → 게이트웨이 provision.env 넷 · MXWP `.env` · update-all · 타일 로그인 확인(PLAN §6)
- [ ] 위키 워커 PAT 의 `plat:plmdefect` 여부(권한표 담당)
