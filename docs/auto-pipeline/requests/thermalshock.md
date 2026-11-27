# ThermalShock 요청 — 자동 파이프라인 열충격 해석(2026-11-27)

> 받을 곳: ThermalShockMCP 리포(`../ThermalShockMCP`) 세션 — **지금 열린 세션이 없다**(사용자에게 알림). 정본 계약 [../contract.md](../contract.md) v1.1.

ThermalShock 은 잡 없는 동기 SED 예측이다. 자동 파이프라인의 열충격 단계로 쓰려면 아래가 필요하다.

## 청할 것

- **TS-AP1 해석 다섯(`sync: true`)** — `auto_profiles` · `auto_check` · `auto_submit`(곧바로 `state: done`) · `auto_status`(늘 done) · `auto_result`.
  - 판정 낱말 바꾸기 — `OK` · `WARNING` · `FAIL` → `pass` · `marginal` · `fail`(기준 2.0 · 2.2 는 `limit` · `limit_source` 로).
  - 결과 봉투 — `sed_pred` · `uncertainty_std` · `out_of_range` 를 metrics 로(단위 필수), `model_version` 을 `app_version` 옆 notes 에.
- **TS-AP2 과제 열쇠** — 지금 `project` 는 자유 글(기본 unknown)이다. subject 의 허브 key · 개발 단계를 받아 기록에 남긴다(10-31 정리 A13 — SP key 받기).
- **TS-AP3 사람 값** — 패키지 종류 · 볼 크기는 늘 사람 값이다. 과제마다 보관하고 사람이 넣는 길(도구 · 화면)을 두고, 없으면 `auto_check` 가
  `missing: [{kind: "human_input", name: "pkg_type", …}]` 로 답한다. HALF / FULL 판정도 사람 값이면 같은 꼴.
- **TS-AP4 입력 원천** — 입력은 ODB 허브의 `get_part_detail` · `get_interposer_result` 응답이다. 둘 중 하나를 정해 주세요.
  (가) 규칙의 앞 단계(ODB 추출)가 낸 결과 봉투를 `upstream` 으로 받는다(계약 §2) — 포털 권장.
  (나) ThermalShock 이 subject 로 ODB 허브를 스스로 읽는다.
- **TS-AP5 서비스 신원** — `service_identity` 를 답한다. 허용 목록 이름은 `heax-thermal_shock_mcp:auto_*`.

## 순서

- 포털은 계약 꼴의 가짜로 먼저 짓는다. ODB 허브는 cae00 전용이라 실주행은 cae00 에서만 된다.
