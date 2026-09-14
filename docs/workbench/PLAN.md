# 워크벤치 — 업무 절차 인벤토리

한 번 해낸 일을 **절차로 굳혀 두었다가, 대상만 바꿔 다시 돌린다.**
목표 사례는 하나다 — ODB++ 를 가져와 열충격 SED 를 계산하고 보고서를 만들어
Report Archive 에 남기는 일이, 과제가 바뀌면 CAD 만 갈아 끼워 같은 절차로 돌아가는 것.

이 문서는 **2026-09-14 에 실물을 조사한 결과 위에** 세운 계획이다. 짐작으로 적은 항목은 없고,
확인 못 한 것은 그렇게 적었다. 조사 원자료는 [context-notes.md](context-notes.md) 에 있다.

---

## 0. 먼저 — 구상을 한 군데 고쳐야 한다

사용자 구상은 두 반쪽이다.

| 반쪽 | 무엇 | 지금 가능한가 |
|---|---|---|
| **(가) 절차를 돌린다** | A→Z 고정 워크플로를 실행 | **부품은 거의 다 있다.** 엮는 모델만 없다 |
| **(나) 절차를 배운다** | 챗으로 한 일을 기억했다가 재생 | **지금은 불가능하다** |

(나)가 불가능한 이유는 설계가 어려워서가 아니라 **기록이 절차를 복원할 만큼 충실하지 않아서**다.

포털이 대화에 남기는 도구 활동(`meta.activity[]`)은 문자열 다섯 개뿐이다.

```python
{"step": …[:200], "tool": …[:80], "detail": …[:400],
 "result_preview": …[:2000], "result_full": …[:2000]}
```

시각이 없고, 순번이 없고, 성공 여부가 없고, **호출과 결과를 짝지을 식별자가 없다.**
실제 대화 저장소에서 나온 증거가 이것을 못박는다.

> 한 메시지에서 `predict_sed` 가 `ap_cx=50.1 … 50.5` 로 **다섯 번 병렬 호출**됐는데,
> 기록은 `호출×5 → 완료×5` 순서이고 **결과 다섯 개의 프리뷰가 전부 같다.**
> 어느 결과가 어느 입력의 것인지 복원할 방법이 없다.

인자도 이미 220자로 잘려 들어오고, 절단 방식이 네 갈래로 제각각이며 그중 셋은 잘렸다는 표시조차
없다. **잘린 인자로 만든 절차는 다시 돌릴 수 없다.**

→ **그래서 P0 은 워크벤치가 아니라 "관측을 충실하게 만드는 일" 이다.** 크지 않다.
LangGraph 훅에 `run_id` 가 **이미 손에 있는데 버리고 있다**(`app.py:2607`·`:2633`).
이 한 필드와 절단 없는 인자만 붙이면 (나)의 전제가 선다. 챗 동작은 하나도 안 바뀐다.

**관측할 수 없는 절차는 기록할 수 없다.** 이 순서를 뒤집으면 나머지가 전부 짐작 위에 선다.

---

## 1. 무엇을 만들 것인가 — 한 문단

**레시피(Recipe)** 는 이름 붙은 절차다. 단계 목록과, 단계가 요구하는 **슬롯**(입력 자리)과,
슬롯을 채우는 **공급자**(추출 도구)로 이루어진다. 레시피는 서버에 저장되고 판본이 붙는다.
**런(Run)** 은 레시피를 특정 대상에 적용한 1회 실행이고, 모든 호출을 인자·결과·식별자와 함께
남긴다. 런이 끝나면 그 기록에서 **레시피를 역으로 제안**할 수 있다 — 그것이 (나)다.

핵심 설계 원칙은 하나다.

> **공급자가 없으면 실패하지 않는다. 사람에게 묻는다.**

ODB 허브가 이 박스에 없다는 제약이 여기서 해소된다. `ball_size` 슬롯의 공급자가 없으면
레시피는 멈추지 않고 **"이 값을 넣어 주세요" 한 칸**을 띄운다. 나중에 ODB 도구가 붙으면
같은 레시피가 **사람 개입 없이** 돈다. 레시피를 고칠 필요가 없다.

---

## 2. 목표 사례를 실물로 뜯어 본 결과

### 2-1. 막힌 곳은 계산기가 아니라 추출기다

`predict_sed` 의 필수 입력 10개다.

```
board_type(INT|HALF|FULL) · ap_cx · ap_cy · pkg_cx · pkg_cy
pkg_type(WLP|FX|DIG) · pkg_x · pkg_y · ball_size("147/250") · pad_size
```

| 입력 | 나오는 곳 | 지금 |
|---|---|---|
| `ap_c*` · `pkg_c*` | ODB 컴포넌트 좌표 | ODB 만 확실 |
| `pkg_x` · `pkg_y` | ODB bbox 또는 STEP `part_info` | 둘 다 가능 |
| `board_type` | ODB 컴포넌트 + 인터포저 | ODB 만 |
| **`ball_size` · `pad_size`** | ODB 패드 심볼 | **STEP·k파일에 아예 없다** |
| **`pkg_type`** | — | **어떤 형상 데이터로도 유도 불가** |

그리고 결정적으로 — **465종 중 SedInput 을 만들어 주는 어댑터가 0개다.** SED 도구 넷은 전부
평평한 dict 를 받고 파일을 받는 인자가 없다. 누가 됐든 손으로 조립해야 한다.

### 2-2. 그런데 ODB 경로는 "없는" 게 아니라 "안 이어져" 있다

```
/home/koopark/claude/ODB     dev 에 실재 — 파서 14종 · 체크리스트 룰 39개 · FastAPI
                             서비스 계층이 이미 인터페이스 독립(CLI·REST·MCP 공용)으로 설계됨
documents/MCP_INTEGRATION.md 447줄 규격서 — 도구 13종 제안까지 이미 합의돼 있음
```

제안된 도구가 막힌 슬롯과 정확히 맞물린다.

| 막힌 슬롯 | 규격서의 도구 |
|---|---|
| `ap_c*` · `pkg_c*` | `odb_list_components` |
| `board_type` | `odb_interposer_ratio` |
| `ball_size` · `pad_size` | `odb_extract_parts` |
| 워피지 3인자(동박 불균형·적층 비대칭·두께) | `odb_copper_ratio` |

**남는 사람 입력은 `pkg_type` 하나로 줄어든다.** 이건 패키지 기술 분류라 형상에서 유도할 수
없고, BOM·명명 규칙·사람 중 하나여야 한다 — 레시피의 **영구 슬롯**으로 둔다.

⚠ cae00 게이트웨이에는 `odb-hub` 가 붙어 있다. **그것이 어떤 도구를 내주는지는 확인 못 했다**
(dev 에서 도달 불가, 페르소나 `key_tools` 비어 있음). 로컬 엔진을 감쌀지 cae00 허브에 붙을지는
§8 의 결정 대기 항목이다.

### 2-3. 과제 키가 앱마다 따로 논다

```
StepForge      project_id    24-hex
DynaForge      session_id    user 스코프
ThermalShock   project       그냥 문자열 메타
ReportArchive  project       문자열 필터
HWAXRisk       target_key    별도 레지스트리
```

이 다섯을 묶는 것이 없다. **A→Z 가 매 단계 사람 손으로 이어지는 진짜 이유가 이것이다.**
워크벤치가 제공해야 할 첫 실체는 엔진이 아니라 **과제 키 레지스트리**다.

### 2-4. 보고서로 나가는 길은 갈린다

- `create_report_from_run(run_id)` 은 **반입된 해석 런** 전용이다. SED·적층·워피지 계산기는
  런을 만들지 않으므로 **이 길로 못 간다.**
- 계산 결과의 길은 `create_report_draft(template_id, template_version, title, blocks)` 다.
  순서가 정해져 있다 — `list_templates` → `describe_template` → `dry_run` → 생성 →
  **`suggest_report_tags`(필수, 안 달면 온톨로지 검색에서 사라진다)**.
- `publish_report` 는 `preview_publish` 가 발급한 `confirm_token` 을 요구한다.
  **사람 확인 자리가 의도적으로 박혀 있다** — 워크벤치가 자동으로 건너뛰면 안 된다.

---

## 3. 어디에 만들 것인가 — 토폴로지 B

사용자 요구는 "챗·심의에 지장을 주지 않는 독립 구성" 이다. 조사 결과 **붙일 곳이 정해진다.**

### 3-1. agent-server 에는 붙이지 않는다

| 사실 | 근거 |
|---|---|
| 인증이 아예 없다 | `Depends`/`Security`/`HTTPBearer` 0개. 방어는 `127.0.0.1` 바인드뿐 |
| 전역 가변 상태가 12개 넘는다 | `agent_cache`·`tool_degraded`·`tool_load_error`·`persona_cache`·`tool_snapshot` … |
| **그중 둘은 이미 교차오염 사고가 났다** | `tool_degraded` 가 다른 요청 스트림에 가짜 배너를 주입 → `ContextVar` 로 수정한 전례 |
| 아티팩트 정리에 네임스페이스가 없다 | 오래된 것부터 500개로 깎는다 → **워크벤치 산출물을 챗이 지운다**(반대도) |
| 무제한 큐 | `/chat` 이 `_detach_stream` 으로 무제한 `asyncio.Queue` 를 쓴다 |

### 3-2. 포털의 공유 자원도 재사용하지 않는다

| 자원 | 재사용하면 |
|---|---|
| `agent_semaphore`(64) | 넘치면 큐 없이 **429 즉시 거절** — 챗이 그만큼 막힌다 |
| `agent_client`(풀 64, read 타임아웃 없음) | 풀을 먹으면 챗이 429 가 아니라 **조용히 멈춘다**(더 나쁜 고장) |
| `conv_store` | 연결 1개 + Lock, **WAL 없음**, async 안에서 동기 sqlite → 이벤트 루프를 막는다 |

**실증이 있다.** HWAXRisk 가 이미 포털 `/agent/chat` 을 쓰는데, 예외 클래스 이름이 그대로
*"엔진 슬롯이 없다(포털 agent_semaphore 429)"* 이고 패널 하나가 챗 슬롯을 **최대 40분** 쥔다.

### 3-3. 그래서 — 별도 HEAX 앱 + 포털은 창

리스크 심사가 이미 간 길이고(**토폴로지 B**), 그 근거가 이번 구상과 같다.

> *"이 자산은 과제 수십 개·수년치가 쌓이는 장기 자산이라 포털 릴리스·박스 수명에 묶이면 안 된다"*

비용도 측정돼 있다(커밋 `943252f`) — **포털 백엔드 0줄**, 기존 파일 3개 + 새 페이지 1개.

```
HEAXWorkBench (새 앱)              포털(창)                    게이트웨이
├ 레시피 저장소(sqlite, WAL)       ├ App.tsx        +1 라우트   └ .portal/manifest.yaml 의
├ 런 저장소(호출 전문 기록)         ├ AppHeader.tsx  +1 메뉴        mcp:{expose:true} 한 블록으로
├ 실행기(invoke_tool 경유)         ├ systems.yaml   +1 타일        60초 내 자동 흡수
├ 과제 키 레지스트리                └ access.yaml    +1 그룹        (설정·코드 변경 0)
└ MCP 표면(list/describe/run)       페이지 1개(신규)
```

**챗·심의 파일은 한 줄도 안 건드린다.**

---

## 4. 레시피 모델 — 새로 발명하지 않는다

스택에 이미 **선언형 카탈로그의 정답**이 있다. 그대로 베낀다.

| 베낄 것 | 어디서 | 무엇을 |
|---|---|---|
| 단계 서술자 | **KooRemapper `catalog_data.json`**(47 ops) | `{키: {type, required, default, enum, desc}}` + JSON Schema 파생 + Draft2020 검증 + 전제조건 플래그 + 검증된 예제 + 함정 노트 |
| 인자 세트 | **SmartTwinMCP 템플릿** | `{name, applies_to[], args{}, tags[], notes}` — "이름 붙인 인자 세트 + 적용 가능 도구" |
| 실행 기록 | **SmartTwinMCP `audit_events`** | `(occurred_at, actor, tool@version, action enum, target, detail JSON=args)`. `pipeline_step` 액션까지 이미 있다 |
| 판본 박은 재실행 | **HEAXHub `POST /jobs/{id}/rerun`** | `app_version_id` 로 판본을 고정해 인자+입력파일까지 복원 |
| 실행 기반 | **ReportArchive 잡 큐** | `type`+`payload` 단일 테이블, 핸들러 등록, 우선순위·백오프·dedup·reaper·스케줄러 |
| 조건 저장·재생 | **`saved_searches`** | 스냅샷이 아니라 조건을 저장해 열 때마다 재실행 + 구독 + 워터마크 |
| 호출 통로 | **`invoke_tool` + `search_tools`** | 이름으로 실행. 인가·캐시·사용자 위임·감사를 그대로 탄다 |

### 레시피 스키마(초안)

```yaml
id: thermal-shock-sed-report
version: 3
title: 열충격 SED 판정 + 보고서
inputs:                                   # 사람이 주는 것 — 과제마다 바뀌는 것만
  - {key: project, type: project_ref, required: true}
  - {key: odb_archive, type: file, accept: [.tgz], required: false}
slots:                                    # 단계가 요구하는 값
  - {key: pkg_type, type: enum, values: [WLP, FX, DIG], provider: null,
     ask: "패키지 기술 분류를 고르세요 — 형상에서 유도할 수 없습니다"}
  - {key: ball_size, type: string, provider: odb_extract_parts#ball_size}
  - {key: board_type, type: enum, values: [INT, HALF, FULL], provider: odb_interposer_ratio#board_type}
steps:
  - id: ingest
    tool: odb_ingest          # 없으면 이 단계는 skipped, 그 슬롯은 ask 로 내려간다
    args: {path: "${inputs.odb_archive}"}
    produces: {job_id: $.job_id}
  - id: extract
    tool: odb_extract_parts
    needs: [ingest]
    args: {job_id: "${steps.ingest.job_id}"}
  - id: predict
    tool: predict_sed
    needs: [extract]
    args:
      sample:
        board_type: "${slots.board_type}"
        pkg_type:   "${slots.pkg_type}"
        ball_size:  "${slots.ball_size}"
        # …
  - id: report
    tool: create_report_draft
    needs: [predict]
    gate: human               # publish 전 사람 확인(RA 가 confirm_token 을 요구한다)
```

**단계가 도구 이름에 직접 묶이지 않아도 된다.** `describe_data_capability` 가 이미 도구를
**타입 대수**로 기술한다(`accepts: DATA → produces: SIM`). 레시피는 이름 대신 능력으로 쓸 수
있고, 실행기가 그때 붙어 있는 도구로 **재바인딩**한다. 다만 CAD 는 등록이 0건이라 —
**능력 등록을 채우는 것 자체가 작업 항목이다**(§6 P3).

---

## 5. 위험 — 먼저 적어 둔다

| # | 위험 | 대응 |
|---|---|---|
| 1 | **기록이 부실한 채로 (나)를 만든다** | P0 을 먼저 한다. 관측이 안 되면 학습은 흉내다 |
| 2 | **자동화가 사람 확인 자리를 건너뛴다** | `publish_report` 2단 확인, `risk_add_finding` 인용 필수는 **의도된 설계**다. `gate: human` 으로 레시피에 박는다 |
| 3 | **합성 데이터 모델을 근거로 쓴다** | `pcb_warpage_surrogate` 가 스스로 경고한다 — *"합성 데이터로 학습한 데모. 절대값을 판정 근거로 쓰지 마라"*. 런 기록에 모델 출처·경고를 반드시 싣는다 |
| 4 | 앱마다 잡 규격이 다르다(8종) | 정규화 어댑터 계층을 둔다. 상태 enum·id 형식·인자 봉투를 하나로 매핑 |
| 5 | JS·파이썬 이중 엔진을 물려받는다 | 워크벤치는 **파이썬 한 갈래**로 간다. 심의의 JS/파이썬 이중 정본을 복제하지 않는다 |
| 6 | 과거 과제 일괄 재생이 자원을 태운다 | 자기 세마포어 + `dry_run` 기본 + 배치 상한. 포털 자원은 안 쓴다 |
| 7 | 레시피가 낡은 도구 판본을 가리킨다 | HEAXHub `app_version_id` 방식으로 판본을 박고, 불일치 시 **경고하고 멈춘다** |
| 8 | ODB 허브 계약이 cae00 과 다르다 | 로컬 엔진 감싸기와 cae00 허브 붙이기를 **어댑터 뒤로** 숨긴다(§8 결정 대기) |

---

## 6. 단계 — P0 부터

각 단계는 **그 단계만으로도 값어치가 있어야** 한다. 뒤가 취소돼도 앞이 쓸모없어지지 않게 한다.

### P0 — 관측을 충실하게 (워크벤치 밖, 선행 필수)
- LangGraph 훅의 `run_id` 를 status 이벤트에 싣는다(`app.py:2607`·`:2633` — 이미 손에 있다).
- 인자를 절단 없이 보존한다. 절단이 불가피하면 **절단 표식을 남긴다**(`deliberation.py:2361`
  의 `…#sha1[:6]` 방식이 유일한 선례다).
- `ts`·소요시간·성공여부·앱 귀속을 `activity[]` 에 싣는다(프론트 타입에는 `ts` 가 이미 선언돼
  있는데 서버가 저장하지 않는다).
- **값어치** — 이것만으로 챗의 도구 활동 패널이 정확해지고, 핸드오프 근거의 인자가 살아난다.

### P1 — 과제 키 레지스트리
- 다섯 앱의 키를 하나로 묶는 표. `project_ref → {stepforge, dynaforge, thermalshock, ra, risk}`.
- **값어치** — 레시피가 없어도, 사람이 앱을 오갈 때 키를 찾아 주는 것만으로 쓸모가 있다.

### P2 — 레시피 저장소 + 인벤토리 화면
- 앱 골격 + sqlite(WAL) + MCP 표면 + 포털 창. 레시피 CRUD·판본·검색.
- 실행기는 아직 없다. **손으로 쓴 레시피를 보관·공유**하는 것까지.
- **값어치** — `delib_opts` 가 브라우저 localStorage 에만 있는 문제도 같은 저장소로 해소된다.

### P3 — 실행기 + 슬롯·공급자
- `invoke_tool` 경유 결정적 실행. 체크포인트·재개·`dry_run`.
- 공급자 없는 슬롯 → 사람에게 묻는 칸. **여기서 ODB 부재가 설계로 흡수된다.**
- 능력 등록(`describe_data_capability`)의 CAD 공백을 채운다.

### P4 — ODB 연동
- `documents/MCP_INTEGRATION.md` 447줄 규격을 구현한다(서비스 계층이 이미 준비돼 있다).
- **값어치** — SED 와 워피지 3인자가 한 번에 열린다. 사람 입력이 `pkg_type` 하나로 준다.

### P5 — 학습(챗 → 레시피 제안)
- P0 의 충실한 기록에서 절차를 **제안**한다. 자동 저장이 아니라 **사람이 확인·편집**한다.
- 근거 — 인자가 살아 있고 호출이 짝지어져야 성립한다. P0 없이는 불가능하다.

### P6 — 일괄 재생 + 리스크 패턴화
- 한 레시피를 과거 과제 N건에 돌려 비교표를 만든다.
- 결과를 `risk_add_finding` 으로 흘린다. ⚠ `claim`·`warrant` 는 자유 산문이고 `cites` 는
  0건이면 422 다 — **완전 자동이 아니라 근거를 대는 자리가 있다.**
- **선행 결손 둘** — 웹에서 리스크 심사를 고를 수 없다(`delibTaxonomy.ts` 의 `JobId` 7종에
  `risk-review` 만 빠져 있다). `ConvKind` 에도 없어 앱이 만든 대화가 웹 목록에서 걸러진다.
  둘 다 워크벤치와 별개의 기존 결손이고, P6 전에 닫아야 한다.

---

## 7. 안 하는 것

- **범용 워크플로 엔진을 새로 쓰지 않는다.** 심의 파이프라인(1,801줄)은 심의 전용이고
  그대로 둔다. 워크벤치는 그것을 대체하지도 흡수하지도 않는다.
- **게이트웨이에 합성·순서 개념을 넣지 않는다.** 게이트웨이는 순수 프록시·집계기로 둔다
  (`workflow|pipeline|recipe|macro` grep 히트 0건 — 지금 상태가 의도다).
- **챗·심의의 동작을 바꾸지 않는다.** P0 은 기록을 더 남기는 것이지 흐름을 바꾸는 게 아니다.

---

## 8. 사용자 결정이 필요한 것

| # | 결정 | 선택지 |
|---|---|---|
| 1 | **ODB 를 어디에 붙이나** | ㉮ dev 의 `/home/koopark/claude/ODB` 를 MCP 로 감싼다(규격서 있음, dev 에서 시험 가능) · ㉯ cae00 의 `odb-hub` 에 붙는다(도구 목록 미확인, dev 에서 시험 불가) · ㉰ 어댑터 뒤에 둘 다 |
| 2 | **워크벤치 앱 이름·리포** | 새 리포 `HEAXWorkBench` 신설 · 기존 앱(HEAXHub?) 안에 모듈로 |
| 3 | **실행 신원** | 워크벤치가 게이트웨이를 부를 때 ㉮ 사용자 위임(HWAXRisk 의 HMAC 신원 단언 방식) · ㉯ 서비스 계정 PAT. ㉮가 옳지만 배선이 더 든다 |
| 4 | **P0 을 지금 하나** | 워크벤치와 무관하게 그 자체로 값어치가 있다. 먼저 해 둘지 |
| 5 | **일괄 재생 상한** | 과거 과제 N건 동시 실행 상한과 `dry_run` 기본값 |

---

## 9. 확인 못 한 것

- **cae00 `odb-hub` 가 내주는 실제 MCP 도구 목록** — dev 에서 도달 불가(`10.252.38.121:8000`
  차단), 페르소나 `key_tools` 가 비어 있고 매니페스트에 `mcp:{}` 블록이 없다.
- **`/home/koopark/claude/ODB` 의 서비스 함수 시그니처 전수** — 규격서의 도구 13종이 실제
  서비스 함수와 1:1 로 맞는지는 구현 시 확인해야 한다.
- **브라우저 실물** — 이 세션은 로그인 자격이 없어 포털 화면을 한 번도 보지 못했다.
