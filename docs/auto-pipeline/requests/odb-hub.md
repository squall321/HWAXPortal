# ODB 허브 요청 — 자동 파이프라인 열충격 입력(2026-11-27)

> ODB 허브는 cae00 전용이라 dev 세션이 없다 — 사람이 운영 쪽에 보낸다. 정본 계약 [../contract.md](../contract.md) v1.1.

열충격 해석(ThermalShock)의 입력은 ODB 허브의 `get_part_detail` · `get_interposer_result` 응답이다. 자동 파이프라인이 과제 · 차수마다 이 입력을 사람
없이 얻으려면 아래 가운데 하나가 필요하다(ThermalShock 요청 TS-AP4 와 함께 정한다).

- **OH-AP1 원천** — 새 보드(ODB++)가 들어오면 계약 §1 `auto_changes` 로 알린다(`subject` 의 허브 key · 개발 단계 · 입력 sha256).
- **OH-AP2 추출 단계** — 계약 §2 의 다섯으로 「열충격 입력 추출」을 해석 단계처럼 갖춘다(`sync: true` · 결과 봉투의 `artifacts` 에 ThermalShock 이 받을
  꼴). 포털이 그 결과를 `upstream` 으로 ThermalShock 에 넘긴다.
- 서비스 신원 — ODB 허브는 서비스 토큰을 쓴다(10-31 정리 B6). 허용 목록 이름은 운영 박스의 백엔드 키 기준 `<키>:auto_*`.
