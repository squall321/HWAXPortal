# 라미나 강도 · ply 피로를 적층 해석이 먹는 꼴로 — MaterialTwinWeb 세션에(요청 · 2026-10-31)

| 항목 | 내용 |
|---|---|
| 받는 곳 | MaterialTwinWeb 세션(기록의 주인). 받는 꼴의 주인은 LaminateAnalyzerMCP 다 — 2절의 꼴을 바꾸려면 그쪽과 맞춘다. |
| 근거 | 결손 장부 [`gaps/lamina-strength-fatigue.yaml`](../gaps/lamina-strength-fatigue.yaml)(종류 ① 도구 없음) · 절차 [PLAN](../PLAN.md) §10-3 '③ 보강' · §10-6 · [체크리스트](../checklist.md) '③ 보강 — 라미나 물성' 줄 · [triage-1031](../../leftovers-1017/triage-1031.md) 표 B 의 B5 |
| 대조한 판 | MaterialTwinWeb main `4273720` · LaminateAnalyzerMCP main `2d35565` · dev 운영 DB(10-31, 읽기 전용). 다른 리포는 읽기만 했다. |

## 1. 왜

포털 절차 R1(굽힘 수명 — `docs/procedures/fixtures/laminate-bend-life.yaml`)은 형상에서 굽힘 반경 · 두께를 읽고 적층 해석으로 층별 응력 · 파손 ·
피로 수명을 낸다. 적층 해석은 ply 마다 강도 다섯과 S-N 을 요구하고, 없으면 그 ply 를 빼고 W120 경고만 낸다 — 임계 ply 가 빠지면 수명을
과대평가한다. 이 값을 주는 도구가 없어 지금은 사람이 예시 값을 붙여 넣는다(`laminate-bend-life.yaml:55-66`).

## 2. 받는 쪽이 먹는 꼴 — LaminateAnalyzerMCP(이 요청으로 바꾸지 않는다)

- `Strength`(`app/schemas.py:17-24`) — Xt(섬유 1축 인장) · Xc(섬유 압축, 양수 크기) · Yt(횡 2축 인장) · Yc(횡 압축, 양수 크기) · S(면내 전단).
  모두 0 보다 크다. 단위는 SI 면 Pa, SI_mm 이면 MPa 다.
- `FatigueSN`(`:27-36`) — `model_type` 이 log_linear(FI = 1 − k·log10 N, 복합재 관례) 또는 basquin(FI = N^(−b)). k · b 는 0 보다 크고 1 이하다
  — 정적 강도로 정규화한 꼴이다.
- 출처 `SourceInfo`(`:9-14`) — `type`(measured · estimated · assumed · user) · `ref`(예 `materialtwin:material/42`).
- 도구 설명은 '강도는 materialtwin property registry 에서 조달 가능' 이라 적었지만(`app/mcp_server.py:200`), 안내의 MaterialTwin 연계(`:735-739`)는
  E 만 다룬다.

## 3. MaterialTwin 에 지금 있는 것(10-31 대조)

| 필요한 값 | MaterialTwin 키(`backend/app/property_taxonomy.py`) | 막히는 곳 |
|---|---|---|
| Xt · Yt | `mechanical.tensile_strength`(:19) | 정의의 조건 축이 `temperature_k` 하나다. 값에 `direction` 조건이 실리기는 한다(dev 1,441행 중 325행 — MD · TD · in-plane …). 그러나 정규 방향 어휘(`backend/app/direction_vocab.py:31-39` — in-plane · through-thickness · MD · TD · axial · radial · circumferential · isotropic)에 라미나 1 · 2 축이 없다 |
| Xc · Yc | `mechanical.compressive_strength`(:137) | 같다 — 조건 축 `temperature_k` 하나, dev 88행 중 방향 조건 7행 |
| S | `mechanical.shear_strength`(:126-127) | 금속 · 적층판을 한 키에 담는다(펀치 전단 포함). 면내(12) 전단강도를 고를 규칙이 없다. 조건 축 `shear_plane`(:127)이 있지만 어휘가 없는 자유 글이고(:122-125 주석 — 시험규격과 OR), dev 18행 중 3행에만 실렸고 셋 다 'through-thickness (punch, across laminations)' 다 — 펀치 전단에만 쓰여 12 면을 고르는 규칙이 되지 못한다 |
| S-N(log_linear k) | 없음 | 정적 강도로 정규화한 S-N 을 받을 키가 없다. 이름이 비슷한 `mechanical.fatigue_strength_coefficient_normalized`(:320-321, σ'f/E — dev 14행)는 E 로 나눈 꼴(변형률–수명 식의 탄성 항 계수)이다. log_linear k 는 정적 강도로 나눈 기울기라 다른 양이고, 하나에서 다른 하나를 만들면 역산이다 |
| S-N(basquin b) | `mechanical.fatigue_strength_exponent`(:324-325) | 금속 Basquin(σa = σf'(2Nf)^b)이라 부호 · 정규화 관례가 다르고, 조건 축(`model` · `stress_ratio_R`)에 방향이 없다 |
| (헷갈리기 쉬운 것) | `mechanical.interlaminar_shear_strength`(:108-109) | 층간 전단이다 — S 가 아니다 |
| (참고) 카드 내보내기 | `backend/app/dyna_export.py:1317-1321` | 방향이 엇갈린 재료에 '*MAT_ORTHOTROPIC 계열을 쓰라' 고 알리기만 한다 — 이방성 카드 길이 없다 |

## 4. 바라는 것 — 둘 중 하나를 알려 달라

1. **이미 되는 길이 있으면 알려 달라.** 예를 들어 강도 행에 방향 조건을 다는 규칙(어느 값이 섬유 1 · 횡 2 인지)이 이미 있고 그 값을 찾는 도구가
   있다면, 그 길과 표본 재료 하나를 알려 주면 포털이 절차 단계로 잇는다. 포털은 숨은 역량을 결손으로 오판한 적이 있다(절차 PLAN §9-4 — DynaForge
   `run_operation` 뒤의 matdb · matswap).
2. **없으면** — 재료 하나에 대해 라미나 강도 다섯과 (인쇄된 경우) S-N 을 받는 길을 둔다. 꼴은 그쪽이 정하되 받는 쪽이 그대로 쓰게 하는 것이
   목표다. 적층 해석의 `material` 블록(`orthotropic_2d` 의 E1 · E2 · G12 · nu12 + `strength` + `fatigue` + `source{type, ref}`)을 내는 읽기 도구
   하나면 절차가 사람 칸 없이 잇는다. 값마다 출처(source id)를 달고, 인쇄되지 않은 값은 '없음' 으로 가른다.

## 5. 받아들임

- 섬유 · 횡 값이 인쇄된 일방향 복합재 하나로, 한 번의 MCP 호출이 강도 다섯과 (있으면) S-N 을 적층 해석의 단위 · 꼴로 돌려주고 출처가 붙는다.
- 인쇄되지 않은 값은 비어 있다고 말한다 — 다른 값에서 역산하지 않는다.
- 그 응답을 적층 해석 `recover_ply_stresses` · `estimate_fatigue_life` 에 그대로 넣으면 W120 없이 돈다.
- 그 뒤 포털이 R1 씨앗의 사람 칸을 단계로 바꾸고 결손 장부를 `fixed` 로 닫는다(포털 몫).

## 6. 하지 않을 것

- 역산하지 않는다(그쪽 규칙 — 인쇄된 값만). Yt 를 E2 에서, basquin b 를 다른 계수에서 만들지 않는다.
- MD · TD 를 말없이 1 · 2 로 읽지 않는다 — 필름 · 압연 방향은 라미나 축이 아니다. 맞대려면 규칙을 적는다.
- 등방 `tensile_strength` 로 빈 칸을 채우지 않는다.
- 적층 해석의 받는 꼴을 이 요청으로 바꾸지 않는다. 포털은 MaterialTwin DB 에 쓰지 않는다.

## 7. 누가 답하나

MaterialTwinWeb 세션 — '이미 되는 길' 이면 그 길과 표본 하나, 짓는다면 꼴과 판. 포털 메인 세션이 받아 결손 장부의 `status` · `confirmed_by` 와
절차 체크리스트의 '③ 보강' 줄에 적는다. 그때까지 R1 은 `laminate` 변수로 사람이 넣는다.

## 답(MaterialTwinWeb 세션, 2026-10-31 — 조사만)

- **이미 되는 길이 있다 — 새 키는 필요 없다.** 다섯 강도는 기존 키 + `direction` 조건으로, S 는 `shear_strength`(`shear_plane`), ply S-N 은
  `fatigue_strength` 또는 Basquin 계수 · 지수로 담긴다. `get_material_properties` 한 번이 한 재료의 전 물성을 돌려준다.
- **막힌 것은 데이터다.** 다섯을 다 가진 카드가 0 이고, 가장 가까운 재료 1380(E-glass/epoxy UD)은 넷이 있고 S 가 없다.
- **방향 표기** — 포털이 답했다(10-31): 라미네이트 입력에 맞춰 1(섬유) · 2(횡) · 12(면내 전단)로 정규화하고, MD 는 출처를 보고 건마다 정한다.
- 남은 일 둘(데이터 파동 · 표기 정규화)은 그쪽 사용자 승인 뒤다. 결손 장부(`gaps/lamina-strength-fatigue.yaml`)의 `answer` 에 같은 내용을 적었다.
