# HWAX 플랫폼 — 팀 업무 분장 (Team Roles)

> HWAX Portal 연합(federation)을 사람에게 분장하기 위한 역할 정의서.
> 각 역할 = **책임 / 구체 업무 / 산출물 / 인원**. 마지막에 협업 흐름·단일오너 원칙·인원 합계.

---

## 0. 범위 (Scope)

**대상 (개발·운영 분장)**
- **HWAXPortal** — 허브(SSO 브로커·라우팅·오케스트레이터·SPA·MCP 채팅 프록시)
- **HWAXAgentServer** — 포털 채팅의 LLM/에이전트 백엔드 (별도 레포)
- **MX White Paper** — AI 보조 사내 백서 플랫폼
- **HEAX Hub** — AI 자동화 툴·에이전트 포탈 (표준 개발 스택의 레퍼런스)
- **AI Data Hub** — 데이터 계층화·온톨로지·사내 API 단일 프록시

**제외**
- SPDM, Smart Twin Cluster — 외부 링크 타일(외부 시스템)
- Report Archive — 개발자 가이드만 제공(이관 대상지로는 ⑥에서 사용)
- SignalForge — 본 분장에서 **전담 오너 미지정** (유지보수 위주; 부록 참고)

---

## 1. 팀 구조 한눈에

| # | 역할 | 담당 컴포넌트 | 인원 |
|---|---|---|---|
| ①-A | 포털 앱 · 인증 · SSO 계약 | HWAXPortal | 1 |
| ①-B | 인프라 · 배포 · 릴리스 (DevOps) | 전 서비스 운영 | 1 |
| ⑤ | AI · 에이전트 · MCP + **MCP Gateway 설계** | HWAXAgentServer + chat | 1 |
| ⑥ | 문서 수집 + MCP + PPT 컨버터 → 백서/Report Archive | 문서 파이프라인 | **2** |
| ⑦ | HEAX Hub — 백+프 **표준 개발 스택 가이드** | HEAX Hub(레퍼런스) | 1 |
| ⑧ | AI Data Hub — **MCP로 수집할 데이터 양식 정리** | AI Data Hub | 1 |
| ⑨ | 사내 시스템 API 협의·연동 — **ARTS / MES / PLM** | 사내 연동 | **3** |

**합계: 10명** (9명 옵션은 §5 참고)

---

## 2. 역할별 상세

### ①-A — 포털 앱 · 인증 · SSO 계약 (풀스택) · 1명
**책임**: 허브 애플리케이션과 **모든 서비스가 붙는 인증 계약**의 단일 소유.
- **인증/SSO**: OIDC RP, provider(mock/saml/oidc), JWKS, launch 라우트 유지.
- **jwt-handoff 계약 소유**: `backend/config/systems.yaml`의 integration_type·audience·url 표준. 신규 서비스 SSO 연동 시 **온보딩 가이드** 제공(서비스는 "복제"만).
- **포털 SPA**: 타일 카탈로그, LaunchPage(auto-POST), 채팅독, 로그인.
- **라우팅·보안**: routes.env·nginx 생성·서브패스 STRIP, 세션/쿠키/CSRF.

**산출물**: SSO 온보딩 문서, 카탈로그 변경 PR 리뷰, 인증 회귀 테스트 셋.

### ①-B — 인프라 · 배포 · 릴리스 (DevOps) · 1명
**책임**: 부팅부터 사내망 배포까지 운영 토대의 단일 소유. (※ cae00 배포 사고가 이 영역)
- **오케스트레이터**: `infra/scripts/services.py`·`services.yaml`·systemd 유닛(부팅 자동·per-box PATH 베이킹), 헬스/롤백.
- **cae00 사내망 배포**: 프론트엔드 **프리빌드 후 dist ship**(사내망 npm/PyPI 불가 대응), per-box 설정 `VLLM_BASE_URL`·`MCP_CONFIG`·레포 경로를 **환경변수/.env로 표준화**(매니페스트 하드코딩 제거), `.env`/시크릿 관리, 레포 클론·`install-systemd.sh`.
- **TLS/도메인**: :443 종단(자체서명 → 사내 인증서), `hwax.sec.samsung.net`.

**산출물**: 배포 런북, per-box config 템플릿, 모니터링/알림.

### ⑤ — AI · 에이전트 · MCP + MCP Gateway 설계 · 1명
**책임**: 모델 호출과 툴 fan-out, 그리고 **MCP 중앙 게이트웨이**.
- **HWAXAgentServer**: LangGraph ReAct, MCP tool fan-out(langchain-mcp-adapters), SSE 스트리밍, LLM 엔드포인트 추상화(OpenAI 호환 `VLLM_BASE_URL`).
- **MCP Gateway 설계·구현** (`mcp_gateway_url :9100` 현재 미구현): 서비스별 MCP 서버를 중앙 게이트웨이로 — 토큰/인증 전달(서비스 PAT), 워크스페이스 라우팅, 툴 레지스트리, rate-limit·감사 로그.
- **MCP 서버 표준 템플릿** 정의(FastMCP·streamable_http·auth 헤더 규약) → 각 서비스가 이걸로 툴서버 작성.

**산출물**: 게이트웨이 아키텍처 문서 + 구현, MCP 서버 작성 가이드.

### ⑥ — 문서 수집 + MCP + PPT 컨버터 → 백서/Report Archive · 2명
**책임**: 팀 지식을 수집·검색가능화하고, 발표자료로 변환해 백서/RA로 이관.
- **2-A (수집·문서 MCP)**: 팀 문서(다양한 포맷) 수집 파이프라인 + **문서 MCP 서버**(검색/조회 툴 → 에이전트가 활용) + 메타데이터/태깅.
- **2-B (PPT 컨버터·이관)**: 문서·데이터 → **PPT 자동 생성 컨버터**(템플릿) + 결과를 **MX White Paper 페이지 / Report Archive**로 이관(API 연동).

**산출물**: 문서 수집 MCP 서버, PPT 컨버터, 백서/RA 이관 파이프라인.

### ⑦ — HEAX Hub: 백+프 표준 개발 스택 가이드 · 1명
**책임**: HEAX Hub를 **레퍼런스 구현**으로, 팀 공통 개발 스택을 정의·전파.
- **표준 정의**: 백엔드(FastAPI 패턴), 프론트(React/Vite·`VITE_BASE_PATH` 서브패스·auth store), SSO consumer 패턴, 서브패스 빌드·배포 컨벤션.
- **가이드 역할**: 신규 앱이 따라야 할 스택·구조를 문서/스캐폴드로 만들고 **교육·코드리뷰**.

**산출물**: 표준 스택 가이드 + 프로젝트 템플릿, 온보딩 교육 자료, 리뷰 체크리스트.

### ⑧ — AI Data Hub: MCP로 수집할 데이터 양식 정리 · 1명
**책임**: "무엇을 어떤 양식으로 수집·적재할지" 표준 정의.
- **데이터 스키마/온톨로지**: 필드·타입·태그·부서, RAG-ready 포맷, 데이터군 분류 체계.
- AI Data Hub MCP(수집/조회 툴)를 활용해 정의하고, **⑥(문서)·⑨(사내시스템)에서 들어올 데이터가 이 양식에 맞도록** 규약 제공.

**산출물**: 데이터 수집 양식/스키마 정의서, AIDH 적재 규약, 태그 체계.

### ⑨ — 사내 시스템 API 협의·연동: ARTS / MES / PLM · 3명 (시스템당 1명)
**책임**: 사내 시스템을 협의하고 데이터를 가져와 AI Data Hub에 적재.
- **ARTS 담당 / MES 담당 / PLM 담당** — 각자 1개 시스템:
  - 소유팀·권한·API 스펙·보안 **협의**(거버넌스).
  - 데이터 추출 → **AI Data Hub "단일 API 프록시"**에 커넥터로 등록.
  - 추출 데이터를 **⑧의 스키마로 매핑**.

**산출물**: 시스템별 API 연동 스펙·권한 합의서, 추출/적재 커넥터, AIDH 프록시 등록.

---

## 3. 데이터·시스템 흐름

```
⑨ ARTS / MES / PLM ──┐
                      ├─▶ ⑧ AIDH 데이터 양식/스키마 ──▶ AI Data Hub 적재(RAG-ready)
⑥ 팀 문서 수집 ───────┤
                      └─▶ ⑥ PPT 컨버터 ──▶ MX White Paper / Report Archive

모든 데이터·툴 ─▶ ⑤ MCP(게이트웨이) ─▶ HWAXAgentServer(채팅) ─▶ ① 포털에서 사용
⑦ 표준 스택 ─▶ 전 서비스 개발에 적용 |  ①-A SSO 계약 ─▶ 신규 서비스 온보딩
```

---

## 4. 협업 인터페이스 (handoff)

| 제공 | → | 수요 | 내용 |
|---|---|---|---|
| ⑨ ARTS/MES/PLM | → | ⑧ | 원천 데이터 (⑧ 스키마로 매핑) |
| ⑧ 데이터 양식 | → | ⑨·⑥·AIDH | 수집/적재 표준 |
| ⑥ 문서/PPT | → | 백서·Report Archive | 이관 콘텐츠 |
| ⑤ MCP 게이트웨이 | → | 전 서비스·채팅 | 툴 노출·인증 라우팅 |
| ⑦ 표준 스택 | → | 전 서비스 | 개발 컨벤션 |
| ①-A SSO 계약 | → | 신규 서비스 | 연동 온보딩 |
| ①-B per-box 표준 | → | 전 서비스 | 배포·환경 |

---

## 5. 사일로 금지 — 단일 오너 필수

이번 배포(cae00)에서 깨진 것은 모두 "공통인데 주인이 없던" 영역이었음. 다음은 **반드시 중앙 단일 오너**:

- **SSO/인증 계약 → ①-A**: 서비스가 제각각 손대면 깨짐(예: jose `leeway`, 서브패스 쿠키 Path). 패턴은 ①-A 소유, 서비스는 복제만.
- **인프라/배포 → ①-B**: per-box 설정(엔드포인트·경로·PATH), 사내망 빌드(프리빌드 ship), 시크릿/.env, systemd. 미소유 시 cae00 FAIL 반복.
- **MCP/게이트웨이 → ⑤**: 엔드포인트·툴서버 표준 한 곳에서.

---

## 6. 인원 합계 & 9명 옵션

- **현재 합계: 10명** = ①(2) + ⑤(1) + ⑥(2) + ⑦(1) + ⑧(1) + ⑨(3)
- 원래 9명 → ARTS/MES/PLM(+3), SignalForge 오너(−1), ① 분할(+1) = net +2 → 10
- **9명에 맞추려면**: ⑦(HEAX 표준 가이드)을 ①-A(포털 앱/표준)에 흡수하거나 ⑧과 묶음.

---

## 부록 — 미지정 / 주의

- **SignalForge**: 본 분장에서 전담 오너 미지정(유지보수 위주). 필요 시 ⑦ 또는 ①이 흡수.
- **per-box 하드코딩 부채**: `services.yaml`의 `VLLM_BASE_URL`·`MCP_CONFIG`·레포 경로가 dev 박스 절대경로. ①-B가 환경변수/.env로 표준화(우선순위 높음).
- **`.env`는 git 비추적**: 새 서버는 서비스별 `.env`를 `.env.example` 기준으로 1회 채워야 함(①-B 책임).
