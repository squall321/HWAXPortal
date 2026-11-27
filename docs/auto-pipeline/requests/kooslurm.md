# SmartTwinMCP · KooSlurm 요청 — 자동 파이프라인 낙하 사슬의 서비스 계정 제출(2026-11-27)

> 보낸 곳: SmartTwin MCP 세션(KooSlurm 리포). 정본 계약 [../contract.md](../contract.md) v1.1 §0.2 · §5.

자동 파이프라인의 전각도 낙하는 DynaForge 가 계약의 주인이고, 실제 제출은 stcx 로 간다(`fullangle_drop_simulation` · `catalog_run`). 사람 없이 돌므로
제출 명의가 서비스 계정이어야 한다.

## 청할 것

- **KS-AP1 서비스 계정 제출 길** — DynaForge 가 사람 없이 낼 때 쓸 KooSlurm 위임(서비스 계정 sbatch — SM-01 계열)과 그 계정의 한도 · 감사.
  어느 계정으로 낼지는 운영이 정한다(받은 편지함 물음).
- **KS-AP2 공유 폴더 SH-01 · 02** — 업로드 입력 · 잡 로그 위치(같이 넘긴 요청서 `cluster-shared-folder-request-20261127.md`). 이것이 풀려야 낙하
  자동 실행이 실주행된다.
- **KS-AP3 상태 바꾸기에 쓸 정보** — `job_status` 의 Slurm 상태 + KooChainRun 상태를 DynaForge 가 다섯 낱말로 바꾸기 쉽게, 끝 · 실패 · 취소를 가를 칸을
  안정된 낱말로.

## 순서

- KooSlurm main push 전에 알려 달라는 규칙(SM-01) 그대로.
