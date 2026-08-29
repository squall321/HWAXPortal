<!-- 시뮬 심의 출력 규격화(sim_spec) — 변수·산출물을 기계판독 스키마로 -->
# 시뮬 심의 출력 규격화 (sim_spec) — 2026-08-29

## 왜 (범위 판단)

심의 출력을 행동가능하게 만들되, **시험-시뮬 1:1 대응(correlation 심의)은 억지**라 접었다 — 물리량·조건·불확실
경로가 서로 달라 1:1 매핑이 불가한 경우가 많다. 대신 **sim 심의가 스스로 도출하는 변수·산출물만 규격화**한다.
sim 심의는 그 변수를 이미 도출하므로(mechanism (4) 미지 파라미터, sim-plan (7) 물성·식별성) 규격화가 억지가
아니라 원래 있는 것을 구조로 못박는 것이다. 딱 이 선에서 마무리한다(범용 산출·test·correlation 안 벌림).

## 규격 (sim_spec)

sim-plan 결정문 산문 뒤에 ```json 펜스 블록으로 함께 낸다. 값은 산문 (7)(8)(9)와 일치, 모르면 빈 문자열(환각 금지).

```
{
  parameters: [ { name, symbol, unit, role: state|material|BC|geometry,
                  source: 문헌|측정|피팅, value_or_range,
                  identifiability: 식별가능|퇴화, degeneracy_note, resolving_obs } ],   // sim-plan (7)
  outputs:    [ { quantity, symbol, unit, uncertainty_band,                              // UQ 좌석
                  acceptance_criterion, validity_range } ],                              // 검증 좌석
  model:      { eq_family, dim, reduction, solver, discretization },                     // (2)(3)(4)(5)
  compute:    { cluster, cores, wallclock, license }                                     // (9)
}
```

우리가 강화한 (7)식별성·(8)검증임계·(9)자원·UQ 구간을 기계판독으로 뽑는 것. 산문은 그대로 두고 규격을 옆에 붙인다.

## 배선 (두 엔진 정합)

- **sim-plan chairTemplate** — `hwax-deliberate.js` CHAIR_ITEMS['sim-plan'] + `deliberation.py` _CHAIR_ITEMS['sim-plan']:
  결정문 끝에 sim_spec 을 ```json 으로 강제(같은 필드).
- **추출** — `hwax-sim-deliberate.js::parseSimSpec(decision)`: ```json 펜스 우선, 없으면 마지막 균형 {...}
  블록(중괄호 세기, 중첩 방어). 실패는 null(비치명적). `simPlan.spec` 로 반환.
- **build-plan 승계** — 3단 context 에 `[2단 sim_spec]` JSON 을 실어, build-plan (2)가 **산문 재파싱 대신 구조로
  승계**(값 어긋나면 규격 우선, 불일치는 (12)에). 지금까지 build 가 sim 산문 20000자를 재파싱하던 것을 대체.

## 값

- **억지 없음** — sim 심의가 도출한 것만 규격화.
- **build-plan 무손실 승계** — 산문 파싱 오류·후미 유실 제거.
- **비교·재사용** — 여러 sim 심의의 변수·산출을 표로 비교(반복 게이트 물성 식별 등).

## 검증

node --check(2 JS)·py_compile·parseSimSpec 단위(펜스·중첩폴백·실패). 반영: agent-server 재기동, 워크플로 sync.
