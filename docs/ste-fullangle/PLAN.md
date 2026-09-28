# ste 전각도 낙하 — HWAX 에서 ste(24대)로 전각도 낙하 잡을 던진다

> 대조 시점 2026-09-28. 코드는 SmartTwinExplorer 리포 `apps/fullangle-drop/`·`apps/_lib/fullangle-drop.sh`·
> `apps/_lib/fullangle_drop.py` 에 있다. 이 폴더는 판단 기록이다.

## 무엇을 · 왜

지금 전각도 낙하는 **stcx(356대)** 로만 던질 수 있다(SmartTwinMCP `fullangle_drop_simulation`·`smarttwin_submit`).
사용자는 **ste(24대)** 에도 던지고 싶다 — HWAX 챗·MCP 에서 `ste_submit_job` 으로.

ste 의 잡 모델은 "앱 하나 = sbatch 잡 하나(노드 1대)" 다. 전각도 낙하는 각도마다 LS-DYNA 잡이 하나씩(162개) 뜨고
끝에 구면 리포트 잡이 붙는 **잡 묶음**이라 모델이 맞지 않는다. 그래서 stcx 와 같은 방식을 쓴다.

- ste 잡 하나 = **드라이버**(1코어). KooChainRun `prepare` → `submit` 으로 각도별 잡과 리포트 잡을 던지고,
  그 잡들이 큐에서 빠질 때까지 지켜본 뒤 결과를 판정한다.
- ste 가 드라이버를 취소하면(TERM) 드라이버가 자식 잡을 전부 `scancel` 한다.

## 가능한가 — 판정

**된다. 단 실박스에서만 답할 수 있는 전제 넷이 있다.** 그래서 앱에 `mode=preflight` 를 넣었다.
HWAX 에서 한 번 던지면 ste 계산노드에서 아래를 판정해 `preflight.json` 으로 남긴다.

| 전제 | 틀리면 |
|---|---|
| 계산노드에서 `sbatch` 가 된다(파티션 AllocNodes·munge) | 드라이버 방식 자체가 불가 → ste 에서 안 한다(사용자 지시: "불가능하면 ste 에서 할 필요는 없어") |
| `/data/SmartTwinPreprocessor/bin/KooChainRun` 이 노드에서 보이고 돈다(GLIBC ≥ 2.35) | 배포·OS 문제 |
| `/opt/apptainers` 에 Preprocessor·Postprocessor·LS-DYNA SIF 가 있다 | SIF 배포 |
| LS-DYNA 라이선스 서버에 노드가 닿는다 | 네트워크 |

## 설계

| 항목 | 값 | 이유 |
|---|---|---|
| 드라이버 자원 | alpha · 1코어 · 168h · 비전유 | 해석은 자식 잡이 한다 |
| 각도 잡 rank | 128 고정 | ste LS-DYNA 라이선스가 128 미만을 거부한다(lsdyna 앱과 같은 사실) |
| 동시 실행 | `parallel` 기본 4 (0 = 각도마다 잡 하나, 제한 없음) | 라이선스 풀을 stcx 와 공유 — 한 사람이 풀을 다 쥐면 stcx 사용자가 멈춘다 |
| 라이선스 서버 | 백엔드 env `STE_LSTC_LICENSE_SERVER` → 없으면 lsdyna 앱 정의의 기본값 | 정본은 lsdyna 앱 하나. IP 를 새 파일에 적지 않는다 |
| 후처리 | KooChainRun 자동(각도별 inline deep + 구면 리포트 잡) | 드라이버가 postprocess 를 다시 부르지 않는다(stcx 드라이버의 이중 실행 결함을 옮기지 않는다) |
| 성공 판정 | `simulation_index.json` 의 완료 수 = 전체 AND `sphere_report.html` 존재 | 부모 잡 rc 만 보면 자식 실패가 성공처럼 보인다 |

## 범위 밖

- stcx 경로(backend_5010 템플릿)의 결함 — 자식 ID grep·부모만 취소·결과 경로 오기·후처리 이중 실행. 보고만 했다.
- ste 백엔드가 잡에 `--export=ALL` 로 자기 env(비밀 포함)를 넘기는 것 — ste 전반의 문제. 이 앱은 KooChainRun 을
  부르기 전에 `STE_*` 를 지워 자식 잡 수백 개로 번지지 않게만 한다.
