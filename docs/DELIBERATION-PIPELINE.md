# HWAX 심의 파이프라인 (Deliberation Pipeline)

> **한 줄**: 질문 → (게이트웨이 도구로) 정량 분석 → 다중 라운드 전문가 심의 수렴 →
> 고차원 그래프·표 생성·분석 → Report Archive 보고서. 게이트웨이 MCP의 주요 기능 중 하나.

## 배경 / 결정 (사용자 확정)

- 이 파이프라인을 **게이트웨이 MCP의 핵심 기능**으로 제품화한다.
- 심의 결과는 **깔끔히 정리**하고, **고차원 그래프·표 생성·분석**을 포함한다.
- 형태: **코어 = 재사용 워크플로**, 게이트웨이/포털에 **진입점 노출**(둘 다).
- 시각화 4종 전부 — 의사결정 매트릭스·정량 차트(파레토·스캐터·바)·수렴 다이어그램·민감도/기여도.

## 5단계 파이프라인

| 단계 | 하는 일 | 구현 |
|---|---|---|
| **1. 발굴** | `recommend_agents(question)`로 관련 전문 페르소나 + 필요 도구 식별 | 게이트웨이 MCP (AIDataHub) |
| **2. 분석(도구)** | 계산·데이터 MCP로 정량 근거 생성(DOE·비교·시뮬), 결과를 구조화 | 게이트웨이 MCP (laminate/materialtwin/…) |
| **3. 심의(N라운드)** | R1 병렬 의견 → R2 반박·수치 심화 → R3 수렴 → 의사결정문 | **[hwax-deliberate.js](../infra/pipeline/hwax-deliberate.js)** |
| **4. 시각화·분석** | 구조화 데이터 → 민감도 바·파레토 스캐터·수렴 다이어그램·의사결정 매트릭스 (인라인 SVG) | **[infra/pipeline/viz_module.py](../infra/pipeline/viz_module.py)** |
| **5. 보고** | 회의록+의사결정+그래프를 정리해 Report Archive 보고서 작성 + 렌더 | 게이트웨이 MCP (ReportArchive `create_report_draft`) |

**역할 분담** — 게이트웨이 MCP가 **도구(계산·에이전트·RA)** 를 제공하고, 파이프라인은 그 위의
**오케스트레이션 패턴**이다. 도메인 도구 실행·페르소나 발굴·시각화 조립은 도메인별이라 호출자(역량 있는
Claude) 몫이고, 도메인 무관한 **다중 라운드 수렴**은 워크플로가 캡슐화한다.

> 정본은 `infra/pipeline/hwax-deliberate.js`(추적됨). 이름으로 호출하려면 `.claude/workflows/`(로컬,
> gitignore)에 복사하고, 아니면 `Workflow({scriptPath:'infra/pipeline/hwax-deliberate.js', args})`로 호출.

## 코어 — 재사용 워크플로 `hwax-deliberate`

```
Workflow({ name: 'hwax-deliberate', args: {
  question: '...',                       // 심의 주제
  context:  '...정량 근거 텍스트...',      // 단계2 도구 결과 요약
  options:  [{id:'A', ...}, ...],        // 후보/선택지
  personas: [{key:'pcb-warpage', role:'...'}, ...]  // 단계1 발굴 결과
}})
→ { round1, round2, round3, decision }
```
- args 는 객체/JSON 문자열 둘 다 방어(`typeof args === 'string' ? JSON.parse : args`).
- R1→R2(반박·심화)→R3(수렴)→의장 의사결정문. 라운드 수·페르소나는 파라미터.

## 시각화·분석 모듈 `viz_module.py`

- `main_effects(rows, factors, resp)` — 2^k 요인의 main-effect(민감도) 계산.
- `effects_svg / scatter_svg / convergence_svg / matrix_html` — 인라인 SVG/HTML(테마 토큰, 외부 리소스 0).
- 재사용: 어떤 DOE/비교 심의에도 rows+factors+matrix+convergence 만 주면 4종 산출.

## 진입점 (노출)

- **역량 있는 Claude(개인 Claude via MCP / Claude Code)** — 지금 바로. 게이트웨이 도구로 1·2·4·5 단계를
  직접 오케스트레이션하고 3단계는 `hwax-deliberate` 워크플로 호출. (오늘 FPCB로 실증.)
- **포털 챗 "심의 모드"** — 후속. dev vLLM(7B)은 이 오케스트레이션에 약하므로 상암 프로덕션 LLM(GLM) 연결 시
  agent-server 에 트리거 노출. [[hwax-mcp-orchestration]] 의 agent-server 확장 지점.

## 실증 (2026-07-17) — FPCB 적층 DOE

- 단계1: `recommend_agents("FPCB 적층 강성 warpage")` → pcb-rigid-flex·pcb-warpage·disp-foldable-stackup·mech-drop-impact·sim-structural-calc.
- 단계2: laminate MCP로 2^3 DOE(동박×PI×배치) 8런 → 굽힘/면내 유효강성.
- 단계3: `hwax-deliberate` 3라운드 (16 에이전트, 414K 토큰) → **만장일치 수렴**: 전역 최적 없음, 존별 설계(굴곡=Run1, 리지드=Run8).
- 단계4: 민감도(배치 효과 +60.2 vs 면내 0.0=A행렬 순서무관)·파레토·수렴·의사결정 매트릭스.
- 단계5: Report Archive report #1 "FPCB 적층 DOE — 두께·배치에 따른 강성과 설계 방향".

## 반패턴

- 단일 라운드 병렬 의견으로 그침 — 수렴·심화가 없으면 '의견 나열'일 뿐 의사결정이 안 된다.
- 강성 등 단일 지표로 판정 — 도메인별 목적함수가 갈리면 다축(예: 정규화 D·절대 D·변형률)으로.
- 시각화 없이 텍스트만 — 고차원 트레이드오프/수렴은 그래프가 텍스트보다 압도적으로 명료.
- 게이트웨이에 도메인 도구를 하드코딩 — 도구는 백엔드에, 파이프라인은 오케스트레이션만.
