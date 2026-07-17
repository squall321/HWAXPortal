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
| **0. 불량 환기(조건부)** | 화두에 불량·품질 얘기가 있으면 SignalForge 최근 이슈를 먼저 환기 — `alert_check` → 경보 제품별 `get_top_issues`(경보 없으면 `daily_briefing` 폴백) → `query_voc`(sentiment=negative) 증거. 연관되면 심의 컨텍스트에 포함, 아니면 환기만 하고 질문 기반 진행 | 게이트웨이 MCP (SignalForge VOC) |
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

- **역량 있는 Claude(개인 Claude via MCP / Claude Code)** — 지금 바로. 게이트웨이 도구로 0·1·2·4·5 단계를
  직접 오케스트레이션하고 3단계는 `hwax-deliberate` 워크플로 호출. (오늘 FPCB로 실증.)
  단계 0의 SignalForge 환기 결과는 요약해 `args.context`에 담아 전달하면 된다(워크플로 수정 불요).
- **포털 챗 "심의 모드"** — `/심의 <질문>` 트리거(agent-server `deliberation.py`). 단계 0(불량 환기·연관성
  LLM 판정)이 내장되어 있고, 결과는 RA `deliberation` 템플릿 보고서로 저장된다. dev vLLM(7B)로 완주는
  확인됐으나 실용 품질은 상암 프로덕션 LLM(GLM) 전제.
- **포털 "심의" 메뉴(/deliberate)** — 전용 페이지. 화두를 입력하면 `/심의` 트리거를 자동 부착해 위와 같은
  경로를 타고, 대화 기록은 챗과 분리된 `hwax.delib.*`(localStorage)에 남는다.

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
