# 워크벤치 — 업무 절차 인벤토리

한 번 해낸 일을 **절차로 굳혀 두었다가, 대상만 바꿔 다시 돌린다.**

목표 사례 — ODB++ 를 가져와 열충격 SED 를 계산하고 보고서를 만들어 Report Archive 에
남기는 일이, 과제가 바뀌면 입력만 갈아 끼워 같은 절차로 돌아가는 것.

> **개정 2 (2026-09-14).** 사용자가 ODB 를 **cae00 `odb-hub`** 로 확정했고, 계획을
> 현실성 기준으로 다시 검토했다. 개정 1에서 **두 가지를 뒤집었다** — 배치(별도 앱 → 포털
> 모듈)와 학습의 위치(선행 필수 → 나중 보조). 이유는 [context-notes](context-notes.md)
> W-10·W-11 에 적었다.

---

## 0. 한 문단 요약

워크벤치에서 **도구를 한 단계씩 돌린다.** 워크벤치가 그 과정을 전부 기록한다. 끝나면
**"레시피로 저장"** 을 누른다 — 그때 어떤 값이 과제마다 바뀌는지 표시하면, 다음 과제에서는
그 값만 채워 **한 번에 재생**된다. 레시피는 서버에 쌓이고 남과 공유된다.

핵심은 **워크벤치가 자기 관측자라는 것**이다. 챗 기록을 해석해 절차를 복원하려 들면 지금
기록으로는 안 된다(§5). 워크벤치 안에서 한 일은 **기록이 곧 절차**라 해석이 필요 없다.

---

## 1. 무엇을 만드나 — 최소 형태

### 레시피

```yaml
id: thermal-shock-sed
version: 1
title: 열충격 SED 판정
vars:                                   # 과제마다 바뀌는 값
  - {key: odb_job, label: "ODB 잡 ID", type: string, required: true}
  - {key: pkg_type, label: "패키지 분류", type: enum, values: [WLP, FX, DIG],
     required: true, why: "형상 데이터로 유도할 수 없습니다"}
steps:
  - tool: odb_list_components
    args: {job_id: "{{odb_job}}"}
    save: {ap_cx: "$.ap.x", ap_cy: "$.ap.y"}      # 결과에서 뽑아 다음 단계에 넘긴다
  - tool: predict_sed
    args:
      sample:
        ap_cx: "{{ap_cx}}"
        pkg_type: "{{pkg_type}}"
        # …
  - tool: create_report_draft
    gate: human                                    # 사람 확인 자리
    args: {…}
```

**이게 전부다.** 변수 치환 `{{name}}` 과 결과 추출 `save` 두 가지 기계장치뿐이다.
조건 분기·반복·병렬은 **v1 에 넣지 않는다**(§6).

### 런

레시피를 한 번 실행한 기록이다. 단계마다 **도구·전문 인자·전문 결과·시각·소요·성공 여부**를
남긴다. 이 기록에서 레시피를 다시 뽑을 수 있으므로, **"하고 나서 저장" 이 성립한다.**

---

## 2. 어디에 만드나 — 포털 안의 격리된 모듈

개정 1에서는 별도 HEAX 앱(토폴로지 B)을 권했다. **되돌린다.** 결정적인 사실을 뒤늦게
확인했기 때문이다.

```python
# backend/app/agent/routes.py:223
def _chat_user_pat(keystore, settings, principal) -> str | None:
    """이 챗 한 번을 위한 단명 PAT. agent-server 가 이걸로 게이트웨이에 붙는다. …
       게이트웨이는 이 토큰을 포털 JWKS 로 검증하므로 위조가 불가능하고, 도구 인가도
       서비스 계정이 아니라 이 사람의 groups 로 이뤄진다"""
```

**포털은 이미 사용자 명의로 게이트웨이를 부를 수 있다.** 새 비밀도, HMAC 신원 단언도,
별도 리포·매니페스트·apptainer·배포·Drive 배선도 필요 없다. 별도 앱으로 가면 이 한 줄을
얻으려고 그 전부를 새로 만들어야 한다.

**독립성은 "별도 프로세스" 가 아니라 "공유 자원을 안 건드리는 것" 으로 얻는다.**

| 자원 | 워크벤치가 | 이유 |
|---|---|---|
| `agent_semaphore`(64) | **자기 것을 만든다** | 넘치면 큐 없이 429 — 챗이 그만큼 막힌다. HWAXRisk 가 실제로 맞고 있다 |
| `agent_client`(풀 64) | **자기 것을 만든다** | read 타임아웃이 없어 풀을 먹으면 챗이 **조용히 멈춘다** |
| `conv_store` | **자기 sqlite(WAL)** | 연결 1개 + Lock, WAL 없음, async 안 동기 호출 |
| agent-server | **안 쓴다** | 인증 0 · 전역 가변 상태 12개 이상 · 아티팩트 정리에 네임스페이스 없음 |

접점은 작다.

```
backend/app/workbench/{__init__,routes,store,runner}.py   신규
backend/app/main.py                     import 1줄 + include_router 1줄(SPA 폴백보다 위)
frontend/src/pages/workbench/*.tsx      신규
frontend/src/App.tsx                    라우트 1개
frontend/src/components/layout/AppHeader.tsx  메뉴 1개
backend/config/access.yaml              feat:workbench (코드 0 · 재기동 0)
frontend/vite.config.ts                 dev 프록시 1줄
infra/services.yaml · start.sh · backup-local.sh · config.py   새 sqlite 등록(4곳)
```

**챗·심의 파일은 한 줄도 안 건드린다.**

⚠ 장기 자산이 포털 릴리스에 묶이는 것은 실제 단점이다(HWAXRisk 가 그래서 별도 앱으로 갔다).
그래서 **저장소를 독립 sqlite 로 두어 언제든 떼어낼 수 있게** 한다. 쓸모가 증명되면 그때
앱으로 승격한다 — 지금 승격 비용을 선불하지 않는다.

---

## 3. ODB — cae00 `odb-hub`. **dev 에서 시험할 수 없다**

사용자 결정이다. 그 결과가 계획에 미치는 영향이 크다.

| 사실 | 결과 |
|---|---|
| dev 게이트웨이에 odb 도구 **0/465** | dev 에서 이 경로를 **한 번도 못 돌린다** |
| `10.252.38.121:8000` dev 에서 차단 | REST 로도 못 본다 |
| 소스가 이 박스에 없다 | 스키마를 읽어서 알 수 없다 |
| 페르소나 `key_tools` 비어 있음 | 도구 이름조차 모른다 |

→ **고정물(fixture) 기반으로 개발한다.** cae00 에서 한 번 받아 온 도구 목록과 응답 표본을
리포에 넣고, 그것으로 어댑터를 만든다. 실주행 검증은 cae00 에서 한다.

### 사용자가 cae00 에서 해 줄 것 — 이게 없으면 ODB 설계 착수 불가

```bash
# ① odb-hub 가 내주는 도구 목록과 스키마
#    게이트웨이 MCP 로 tools/list 를 받아 odb 관련만 추린다
cd ~/Projects/HWAXAgentServer && .venv/bin/python - <<'PY'
import asyncio, json
from langchain_mcp_adapters.client import MultiServerMCPClient
conf = json.load(open("mcp_servers.json"))
async def main():
    c = MultiServerMCPClient(conf["mcpServers"] if "mcpServers" in conf else conf)
    ts = await c.get_tools()
    out = [{"name": t.name, "description": (t.description or "")[:1200],
            "args_schema": getattr(t, "args_schema", None)}
           for t in ts if "odb" in t.name.lower()]
    print(json.dumps(out, ensure_ascii=False, indent=2))
asyncio.run(main())
PY
```

② 그 도구 중 **실제로 한 번씩 불러 본 응답 표본**(민감정보는 지우고). 특히
`list_components` 계열 · `extract` 계열 · `copper` 계열 — SED 슬롯이 여기서 나온다.

③ `curl -s http://127.0.0.1:9110/tools-map | python3 -c "..."` 로 odb-hub 앱 키 확인.

받은 것은 `docs/workbench/fixtures/odb-hub/` 에 넣는다.

---

## 4. 막힌 조각은 정확히 어디인가

`predict_sed` 필수 입력 10개 중 형상 데이터로 채워지지 않는 것.

| 입력 | 나오는 곳 |
|---|---|
| `ap_c*` · `pkg_c*` · `board_type` · `ball_size` · `pad_size` | **ODB 만** |
| `pkg_x` · `pkg_y` | ODB bbox 또는 STEP `part_info` |
| **`pkg_type`(WLP\|FX\|DIG)** | **어디서도 안 나온다** — 패키지 기술 분류 |

그리고 **465종 중 SedInput 을 만들어 주는 어댑터가 0개다.** SED 도구 넷은 전부 평평한 dict 를
받고 파일 인자가 없다.

→ 설계 원칙 하나로 흡수한다.

> **공급자가 없으면 실패하지 않는다. 사람에게 묻는다.**

`pkg_type` 은 **영구 변수**로 둔다(레시피 `vars` 에 `why` 를 적어 왜 물어보는지 밝힌다).
ODB 도구가 안 붙은 환경에서는 `ap_cx` 등도 같은 자리로 내려온다 — 레시피는 그대로 돌고,
사람이 채우는 칸만 늘어난다. cae00 에서는 그 칸이 `pkg_type` 하나로 준다.

---

## 5. "챗으로 한 일을 기억한다" — 지금은 안 된다. 그래서 뒤로 뺐다

포털이 대화에 남기는 도구 활동은 문자열 다섯 개뿐이고 **호출과 결과를 짝지을 식별자가 없다.**

> 실제 대화 저장소 증거 — 한 메시지에서 `predict_sed` 가 `ap_cx=50.1 … 50.5` 로 다섯 번
> 병렬 호출됐는데 **결과 다섯의 프리뷰가 전부 같다.** 어느 결과가 어느 입력의 것인지 모른다.

인자도 이미 220자로 잘려 들어오고, 절단 방식이 네 갈래인데 셋은 표시조차 없다.

**개정 1에서는 이것을 고치는 일(P0)을 전제로 뒀다. 되돌린다.** §0 처럼 워크벤치가 자기
관측자면 이 문제를 **우회**한다 — 레시피는 챗 기록이 아니라 워크벤치 런에서 나온다.

관측 개선은 여전히 값어치가 있고(챗 활동 패널·핸드오프 근거가 정확해진다) **"챗에서 바로
레시피 뽑기"(S5)의 전제**지만, 핵심 기능의 **선행 조건은 아니다.**

---

## 6. v1 에 **안** 넣는 것

현실성의 절반은 안 만드는 목록이다.

| 안 넣는 것 | 왜 |
|---|---|
| 조건 분기·반복·병렬 | 목표 사례가 **직선**이다. 넣는 순간 미니 언어를 만들게 된다 |
| 능력 기반 재바인딩(`accepts`/`produces`) | 계약은 있는데 **데이터가 비었다** — `describe_data_capability("CAD")` 의 `capability_tools` 가 0건이다. 채우는 것부터가 별도 작업 |
| 앱 간 잡 규격 정규화 | 8개 모델이 제각각이지만 **목표 사례가 닿는 건 1~2개**다. 전부 정규화하는 것은 투기다 |
| 레시피 MCP 표면 | Claude 쪽에서 부를 수 있으면 좋지만 v1 가치에 필수가 아니다 |
| 심의 파이프라인 흡수·대체 | `infra/pipeline/*.js` 1,801줄은 심의 전용이고 그대로 둔다 |
| 게이트웨이에 순서 개념 추가 | 게이트웨이는 순수 프록시로 둔다(지금 `workflow\|recipe\|macro` grep 히트 0 — 의도다) |
| 스케줄 실행(cron) | 쌓인 레시피가 있어야 의미가 있다. 그때 가서 |

---

## 7. 자동화가 건드리면 안 되는 자리 셋

전부 **의도된 설계**다. 편의로 건너뛰면 안 된다.

1. **`publish_report`** 는 `preview_publish` 가 발급한 `confirm_token` 을 요구한다 — 2단 확인.
2. **`risk_add_finding`** 은 `cites` 0건이면 **422**. `claim`·`warrant` 는 자유 산문이고
   설계가 사람 등록(`origin='human'`)용이다.
3. **`pcb_warpage_surrogate`** 가 스스로 경고한다 — *"합성 데이터로 학습한 데모. 절대값을
   판정·양산 의사결정 근거로 쓰지 마라."*

→ 레시피에 `gate: human` 을 두고, 런 기록에 **모델 출처·경고를 반드시 싣는다.**
"A to Z" 의 Z 는 게시가 아니라 **사람 앞에 놓는 것**이다.

---

## 8. 단계 — 각 단계가 그 자체로 쓸모 있어야 한다

### S0 · cae00 API 수집 — **사용자, 30분**
§3 의 세 가지. 이게 없으면 ODB 설계를 시작할 수 없다. 나머지 단계는 이것과 무관하게 진행된다.

### S1 · 레시피 저장소 + 실행기 + 최소 화면 — **가장 큰 덩어리**
- 격리 모듈(자기 세마포어·자기 httpx·자기 sqlite/WAL)
- 단계 실행 = `invoke_tool` 경유. `{{var}}` 치환 + `save` 결과 추출 두 가지만
- 런 기록(도구·전문 인자·전문 결과·시각·소요·성공)
- 화면 — 레시피 목록 / 단계별 실행 / 런 이력 / **"레시피로 저장"**
- `dry_run` 기본값
- **검증**: dev 에서 도구 2~3개짜리 레시피를 만들어 저장 → 변수 바꿔 재생

### S2 · 과제 키 레지스트리 — **작다**
StepForge `project_id` · DynaForge `session_id` · ThermalShock `project` · RA · Risk 를 묶는 표.
A→Z 가 끊기는 진짜 이유가 이것이다. **레시피 없이도 쓸모가 있다** — 사람이 앱을 오갈 때
키를 찾아 준다.

### S3 · ODB 어댑터 + 열충격 레시피 — **S0 이 선행**
- 고정물로 어댑터 작성 → SedInput 조립
- dev 에서는 ODB 단계가 "사람이 채우는 칸" 으로 내려간 상태로 완주 시험
- **cae00 에서 실주행 검증**
- 워피지 3인자도 같은 다리로 열리는지 확인

### S4 · 일괄 재생 — **S1~S3 이 서면 작다**
한 레시피를 과거 과제 N건에 돌려 비교표. 동시 실행 상한 + `dry_run` 기본.

### S5 · 챗 → 레시피 제안 — **선택. 관측 개선이 선행**
§5 의 네 가지(식별자·시각·전문 인자·앱 귀속)를 먼저 고친 뒤에만 의미가 있다.
자동 저장이 아니라 **사람이 확인·편집**한다.

### S6 · 리스크 패턴화 — **가장 뒤**
결과를 `risk_add_finding` 으로 흘린다. `risk_taxonomy` 의 통제 어휘를 쓴다(38 메커니즘 ·
동의어 18 — **추측해 넣으면 422**).
**선행 결손 둘** — 웹에서 리스크 심의를 고를 수 없고(`delibTaxonomy.ts` 의 `JobId` 7종에
`risk-review` 만 빠져 있다), `ConvKind` 에도 없어 앱이 만든 대화가 웹 목록에서 걸러진다.
둘 다 워크벤치와 별개의 기존 결손이고 S6 전에 닫아야 한다.

---

## 9. 남은 결정

| # | 결정 | 메모 |
|---|---|---|
| 1 | ~~ODB 어디에~~ | **정해짐 — cae00 `odb-hub`** |
| 2 | S0 을 언제 하나 | 사용자 30분. 이르면 이를수록 S3 설계가 빨라진다 |
| 3 | 첫 레시피를 무엇으로 | 열충격 SED 가 목표지만 **ODB 없이 dev 에서 완주되는 것**이 S1 검증에 낫다(예: STEP 반입 → 파트 조회 → 보고서 초안) |
| 4 | 일괄 재생 상한 | S4 때 정해도 된다 |

---

## 10. 확인 못 한 것

- **cae00 `odb-hub` 의 도구 목록·스키마·응답 모양** — S0 로 받는다. 그전까지 ODB 관련 설계는
  전부 가정이다.
- **브라우저 실물** — 이 세션은 로그인 자격이 없어 포털 화면을 한 번도 보지 못했다.
- `/home/koopark/claude/ODB` 로컬 엔진은 **쓰지 않기로 했다**(사용자 결정). 다만 그 리포의
  447줄 MCP 규격서는 odb-hub 어댑터를 설계할 때 **어휘 참고물**로 쓸 수 있다.
