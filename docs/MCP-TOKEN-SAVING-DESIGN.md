# MCP 도구 토큰 절약 설계서 — 스킬형 지연 로딩

> 2026-07-21, 게이트웨이·agent-server 코드 판독 기반 설계(미구현 — 착수 시 0단계 계측부터).

# MCP 도구 토큰 절약 — 스킬형 지연 로딩 구현 설계서

- 대상 저장소: `/home/koopark/claude/HWAXMcpGateway/gateway.py`, `/home/koopark/claude/HWAXAgentServer/app.py`, `/home/koopark/claude/HWAXAgentServer/deliberation.py`
- 현황 실측: 게이트웨이 도구 160개, 스키마 raw 94,416자(평균 590, 최대 2,838=create_report_draft). prod GLM은 TOOL_MAX 미설정으로 160개 전부 바인딩 → 슬림 240 기준 **83,816자가 매 ReAct 스텝마다 재전송**. dev(qwen 16K)는 TOOL_MAX=40+슬림120으로 21,663자 — 16K 컨텍스트의 약 1/3이 스키마로 소진.
- 토큰 환산 가정: JSON/영문 위주에 한글 설명 혼재라 1토큰 ≈ 3.5~4자. 이하 추정치는 이 범위 기준.

---

## 1) 옵션 비교

### A. 게이트웨이 meta-tool 모드 (search_tools + invoke_tool 만 노출)

게이트웨이가 `X-HWAX-Tool-Mode: meta` 요청에 한해 `_list_tools()`(gateway.py:394-397)에서 풀 리스트 대신 `[search_tools, invoke_tool, save_conversation]` 3개만 반환. 검색·호출 데이터 소스는 기존 전역 `exposed_tools`/`route`(gateway.py:122-123) 그대로.

| 항목 | 평가 |
|---|---|
| 스키마 토큰 절약 | 메타 도구 3개 ≈ 800자(~200토큰). prod 기준 스텝당 83,816자 → ~800자, **95% 이상 절감**. search 결과(top-5 × 슬림 설명+스키마 ≈ 4K자 ≈ 1K토큰)는 1회만 대화 이력에 들어감 |
| 구현 난이도 | **소(게이트웨이 ~80줄)**. SAVE_CONV_TOOL 전례(gateway.py:286-320, 378-380, 403)가 3단계 패턴(정의→노출→분기)을 이미 제공. invoke_tool은 L405 이후 기존 라우팅 재진입만 하면 되고, L413 호출 시점 그룹 인가가 이미 enforcement 담당 — 보안 추가 작업 없음 |
| 부작용 | 도구 발견성 저하(LLM이 뭐가 있는지 모름), 스텝 1~2회 증가(search→invoke 왕복), 자유형 dict 인자 품질 리스크. §5 참조 |
| 구조적 이점 | revive 루프 재집계(gateway.py:235-239)가 tools/list_changed 알림을 안 보내는 stale 문제가 **구조적으로 사라짐** — 매 검색이 live `exposed_tools`를 봄 |

### B. AgentServer per-query top-k 바인딩

`_cap_tool_count`(app.py:221-228)의 정적 `_TOOL_PRIORITY`+알파벳순 컷을 질문 인지 랭킹으로 교체. 삽입점은 로드 직후 단 한 곳(app.py:243)과 `_agent_stream`의 `_agent_for` 호출(app.py:302).

| 항목 | 평가 |
|---|---|
| 스키마 토큰 절약 | k=12 기준 12 × 평균 459자(슬림120) ≈ 5.5K자. dev 21,663 → 5.5K자(**~75%**), prod 83,816 → ~6K자(**~93%**) |
| 구현 난이도 | **소(최소침습)~중(캐시 구조 변경)**. 최소 버전은 `_cap_tool_count(tools, query)` 시그니처 변경 + 키워드 스코어 한 함수. 완전 버전은 캐시를 `{frozenset(groups): compiled_agent}` → `{frozenset(groups): prepped_tools}`로 바꾸고 요청마다 `create_react_agent` 재컴파일(저비용, 병목 아님) |
| 부작용 | **라우팅 정확도가 하드 실패 모드** — 매처가 정답 도구를 빠뜨리면 에이전트는 그 도구의 존재 자체를 모름(meta 모드는 재검색으로 회복 가능하지만 B는 불가). 정적 스냅샷 캐시라 게이트웨이 도구 변동에 stale(프로세스 재시작 전까지, app.py:231-254) |
| 비고 | 현행 컷은 "우선순위 24개 + add_training_data부터 알파벳순 16개"라는 준-임의 집합 — 어떤 질문 인지 랭킹이든 현행보다 나쁠 수 없음 |

### C. 도구 결과 슬림화/참조 전달 (대형 결과 저장 후 핸들 반환)

현행은 AgentServer `_cap_tool`(app.py:149-178)의 `s[:6000]` 단순 절단뿐. 절단돼도 건당 최대 6,000자(≈1.5~1.7K토큰)가 ReAct 이력에 **무기한 누적**되고 이후 모든 스텝에 재전송된다(합산 상한 없음). 게이트웨이 쪽 삽입점은 정확히 두 곳 — `_call_tool`의 정상 반환(gateway.py:425-428)과 재연결 후 반환(gateway.py:437-441) 직전.

| 항목 | 평가 |
|---|---|
| 결과 토큰 절약 | 대형 결과 건당 6,000자 → 핸들+head 요약 ~500자. 도구 5회 호출·10스텝 대화면 이력 누적분 수만 자 절감. 스키마가 아니라 **이력 누적**을 잡는 유일한 옵션 — A/B와 절약 축이 다름(상호 보완) |
| 구현 난이도 | **중**. 스풀 저장소+`fetch_result(handle)` 로컬 도구(SAVE_CONV_TOOL 패턴 재사용)+TTL GC. RA 저장 크레덴셜(config의 `rat_…` 토큰, X-Workspace-Slug)은 게이트웨이가 이미 보유 |
| 부작용 | 핸들 소유권 문제 — MCP 경로 `_audit`(gateway.py:64-76)은 caller를 안 남기므로(REST 경로만 rest_proxy.py:133,136) request_context에서 Authorization/groups를 읽어 귀속시켜야 함. LLM이 fetch_result를 안 부르고 요약만으로 오답할 수 있음 |
| 선행 조건 | **임계값을 정할 실측 데이터가 없음** — `_audit`에 result_bytes 필드부터 추가해야 함(현재 ms·ok·error 200자만) |

### D. vLLM prefix caching (참고 옵션)

자가호스팅이므로 API 비용 절약은 무의미하고, **컨텍스트 여유도 늘려주지 않는다** — 16K 한계는 그대로다. 절약되는 것은 동일 프리픽스(시스템 프롬프트+도구 스키마)의 KV 재계산, 즉 TTFT/GPU 처리량.

| 항목 | 평가 |
|---|---|
| 절약 | 토큰 0. ReAct 다중 스텝에서 스텝 간 프리픽스 재계산 제거(prod 83.8K자 프리픽스면 체감 큼) |
| 난이도 | **소**. vLLM 기동 플래그(`--enable-prefix-caching`) + 히트율 확인 |
| 상호작용 | **A와 시너지** — 메타 3개 도구는 모든 요청·스텝에서 프리픽스가 완전 동일. **B와 상충** — 요청마다 도구 집합이 바뀌면 요청 간 프리픽스 캐시가 깨짐(스텝 간 히트는 유지). B 채택 시 도구를 결정적 순서로 정렬해 동일 질문 재요청 히트라도 확보 |

### 비교 요약

| | 스키마 토큰 | 결과/이력 토큰 | 난이도 | 핵심 리스크 |
|---|---|---|---|---|
| A meta-tool | -95%+ | - | 소 | 발견성·모델 순응도 |
| B top-k | -75~93% | - | 소~중 | 매칭 실패 = 하드 실패 |
| C 핸들 | - | 대화당 수만 자 | 중 | 소유권·재조회 누락 |
| D prefix | 0 (지연만) | 0 | 소 | B와 상충 |

---

## 2) 권장 조합과 단계별 적용 순서

**핵심 판단: dev와 prod의 최적해가 다르다.** 16K qwen(dev)은 메타 도구의 2단 간접 호출(search→invoke, args를 dict로 중첩)을 안정적으로 못 할 가능성이 높고, prod GLM은 스키마 83.8K자가 진짜 문제다. 게이트웨이가 이미 per-request 헤더 메커니즘(gateway.py:383-391)을 갖고 있으므로 **소비자별 모드 분리가 공짜**다 — dev는 B, prod는 A.

| 단계 | 내용 | 규모 | 성공 기준 |
|---|---|---|---|
| **0. 계측** | 게이트웨이 `_audit`에 result_bytes+caller 추가(gateway.py:64-76, 425-449) | S | audit.jsonl에 도구별 결과 크기 분포가 쌓임 → C의 임계값 근거 |
| **1. B 최소침습** | `_cap_tool_count(tools, query)` 질문 인지 랭킹 + `_agent_for` 캐시 구조 변경(app.py:221-228, 231-254, 302). `system_id`(app.py:139) → 백엔드 프리픽스 매핑으로 후보군 선축소 | S~M | dev에서 도메인 질문이 현행 준-임의 40개보다 정확한 도구를 잡는지 회귀 질문셋으로 확인 |
| **2. A 게이트웨이 meta 모드** | search_tools/invoke_tool 로컬 도구 + `X-HWAX-Tool-Mode` 분기(§3). AgentServer는 env `TOOL_MODE=meta`로 prod만 opt-in | M | prod GLM 스텝당 프롬프트 토큰 실측 95% 감소, 심의 회귀 시나리오 통과 |
| **3. C 결과 핸들** | 두 반환 지점 헬퍼 통합 + 스풀 저장 + fetch_result(§3). 단계 0의 실측으로 임계 결정(예: p95 초과분) | M | 대형 결과 도구(list_records, query_voc 등) 호출 후 이력 크기 감소 확인 |
| **4. D 플래그** | prod vLLM prefix caching 활성 + 히트율 모니터링. A 적용 후라 프리픽스가 안정적 | S | TTFT 개선 실측 |
| 부수 | deliberation.py `_tools_by_name`(deliberation.py:67-73)이 단계 1의 그룹셋별 도구 캐시를 공유 — 심의 실행마다 160개 재로드 제거 | S | 심의 기동 지연 감소 |

### recommend_agents 재활용 가능 여부

**직접 재활용은 불가.** `recommend_agents`는 AIDataHub의 '에이전트' 추천 의미 검색이라 색인 대상이 MCP 도구가 아니다. 도구 카탈로그를 AIDataHub 문서로 색인해 `semantic_search`를 태우는 우회도 가능하지만, (1) search_tools 호출마다 백엔드 왕복이 추가되고, (2) 게이트웨이가 AIDataHub 생존에 결합되며, (3) 160개 규모에서는 임베딩이 과잉이다 — 전역 `exposed_tools`에 풀 스키마가 이미 메모리에 있으므로(hooks [S] 판단과 동일) **키워드/부분문자열 매칭으로 시작**하는 것이 옳다. 재활용할 것은 검색기가 아니라 **디스패처 원형**이다 — deliberation.py의 `_call`(deliberation.py:76-89)이 이름으로 `ainvoke`하고 content-item 리스트를 텍스트로 합치는 패턴은 invoke_tool 소비측의 검증된 전례다.

---

## 3) 구체 구현 스케치

### 3-1. 게이트웨이: meta-tool 모드 (`gateway.py`)

**(a) 모드 판독 헬퍼 — `_request_groups()`(L383-391) 옆에 추가.**

```python
TOOL_MODE_HEADER = "x-hwax-tool-mode"  # 주의: x-hwax-groups 는 _bearer_gate(L488-491)가
                                        # PAT 경로에서 강제 재작성하므로 반드시 별도 이름

def _request_tool_mode() -> str:
    try:
        req = _low.request_context.request
        return (req.headers.get(TOOL_MODE_HEADER) or "full").lower()
    except Exception:
        return "full"
```

**(b) 메타 도구 정의 — SAVE_CONV_TOOL(L286-320) 아래 같은 패턴.**

```python
SEARCH_TOOLS_TOOL = types.Tool(
    name="search_tools",
    description=("사용 가능한 도구를 검색한다. 도구 호출 전 반드시 먼저 호출할 것. "
                 "query='select:이름' 은 정확 선택, 그 외는 키워드 검색. "
                 "분야 예: slurm 잡, VOC/감성, 재료물성, 적층판 해석, 보고서 작성, 문서/지식 검색"),
    inputSchema={"type": "object",
                 "properties": {"query": {"type": "string"},
                                "limit": {"type": "integer", "default": 5}},
                 "required": ["query"]},
)
INVOKE_TOOL = types.Tool(
    name="invoke_tool",
    description="search_tools 로 찾은 도구를 이름으로 호출한다. arguments 는 해당 도구의 inputSchema 를 따른다.",
    inputSchema={"type": "object",
                 "properties": {"tool_name": {"type": "string"},
                                "arguments": {"type": "object"}},
                 "required": ["tool_name"]},
)
```

**(c) 노출 분기 — `_list_tools()`(L394-397) 한 곳만 수정.**

```python
@_low.list_tools()
async def _list_tools():
    if _request_tool_mode() == "meta":
        return [SEARCH_TOOLS_TOOL, INVOKE_TOOL, SAVE_CONV_TOOL]
    return _visible_tools(_request_groups())   # 기존 경로 그대로 — Claude Code 무영향
```

**(d) 검색 구현 — `_visible_tools(_request_groups())` 위에서 매칭하므로 그룹 인가가 공짜로 유지.**

```python
def _search_tools_impl(query: str, limit: int = 5):
    visible = _visible_tools(_request_groups())          # 그룹 필터 자동 적용
    if query.startswith("select:"):                       # ToolSearch 와 문법 대칭
        names = {n.strip() for n in query[7:].split(",")}
        hits = [t for t in visible if t.name in names]
    else:
        words = [w for w in re.split(r"[^0-9a-z가-힣_]+", query.lower()) if w]
        def score(t):
            text = f"{t.name} {t.description or ''}".lower()
            return (sum(3 for w in words if w in t.name)
                    + sum(1 for w in words if w in text))
        hits = sorted((t for t in visible if score(t) > 0), key=score, reverse=True)[:limit]
    payload = [{"name": t.name,
                "description": (t.description or "")[:240],
                "inputSchema": t.inputSchema} for t in hits]   # 슬림 스키마 동봉 — dict 인자 품질 완화
    if not hits:
        payload = {"error": "no match", "hint": "다른 키워드로 재검색",
                   "sample_names": [t.name for t in visible[:20]]}
    return types.CallToolResult(content=[types.TextContent(type="text",
        text=json.dumps(payload, ensure_ascii=False))])
```

**(e) 호출 분기 — `_call_tool`(L400-411) 선두, SAVE_CONV 분기(L403) 아래.**

```python
    if name == SEARCH_TOOLS_TOOL.name:
        return _search_tools_impl(arguments.get("query", ""), int(arguments.get("limit", 5)))
    if name == INVOKE_TOOL.name:
        name = str(arguments.get("tool_name", ""))
        arguments = arguments.get("arguments") or {}
        # 이후 기존 코드로 fall-through — L405 unknown 처리, L411 route,
        # L413 호출 시점 그룹 인가가 그대로 이중 방어 담당. validate_input=False 라 추가 검증 부담 없음
    if name not in route:
        near = _search_tools_impl(name, 5)               # 자가 회복: 유사 도구 제안 동봉
        return types.CallToolResult(isError=True, content=[types.TextContent(type="text",
            text=f"unknown tool '{name}'. search_tools 를 먼저 호출하라. 유사 도구: {near.content[0].text}")])
```

**(f) `/health`(L461-471)는 손대지 않는다** — `tools: len(exposed_tools)` 의미(집계된 실제 도구 수)를 유지해야 오케스트레이터 프로브가 깨지지 않는다. README의 46개/9009 포트 수치는 stale이므로 검증 기준으로 삼지 말 것(실제 5개 백엔드 160도구, 포트 9110 — gateway.py:49).

### 3-2. 게이트웨이: 결과 계측 + 핸들 치환 (`gateway.py` L425-428, L437-441)

두 `return res`를 헬퍼 하나로 묶는다.

```python
RESULT_SPOOL_THRESHOLD = int(os.environ.get("GATEWAY_RESULT_SPOOL_BYTES", "0"))  # 0=치환 끔(계측만)

def _finalize_result(res, name, backend_key, ms):
    raw = _serialize_result(res)                  # content + structuredContent 직렬화
    caller = _request_caller()                    # request_context 에서 Authorization(PAT sub)/groups 판독
    _audit(name, backend_key, ok=not getattr(res, "isError", False),
           ms=ms, caller=caller, bytes=len(raw))  # ← 단계 0: 임계 결정용 실측
    if (RESULT_SPOOL_THRESHOLD and len(raw) > RESULT_SPOOL_THRESHOLD
            and _request_tool_mode() == "meta"):  # 모드 조건부 필수 — Claude Code 경로도 같은 코드를 지남
        handle = _spool.put(caller, raw)          # 스풀: 로컬 디스크 우선. RA 승격은 config 의
                                                  # reportarchive rat_ 토큰 재사용으로 후속 확장
        return types.CallToolResult(content=[types.TextContent(type="text",
            text=raw[:1500] + f"\n…[전체 {len(raw)}B → fetch_result(handle='{handle}') 로 조회. TTL 1h]")])
    return res
```

`fetch_result(handle)`는 SAVE_CONV_TOOL 패턴의 세 번째 로컬 도구로 추가하고, put 시점의 caller와 대조해 소유권을 검사한다(MCP 경로 audit에 caller가 없던 공백을 이 헬퍼가 함께 메운다 — REST 경로의 `caller=claims.get("sub")` 패턴(rest_proxy.py:133,136)을 MCP 경로로 이식).

### 3-3. AgentServer: per-query top-k (`app.py`)

```python
# app.py:221-228 — 유일한 컷 지점이므로 여기만 바꾸면 dev/prod 공통 적용
def _cap_tool_count(tools, query: str = ""):
    if TOOL_MAX <= 0 or len(tools) <= TOOL_MAX:
        return tools
    words = [w for w in re.split(r"[^0-9a-z가-힣_]+", (query or "").lower()) if len(w) > 1]
    rank = {n: i for i, n in enumerate(_TOOL_PRIORITY)}      # 무매칭 폴백으로 유지
    def key(t):
        name = getattr(t, "name", "")
        text = f"{name} {getattr(t, 'description', '') or ''}".lower()
        hits = sum(3 if w in name else 1 for w in words if w in text)
        return (-hits, rank.get(name, len(rank)), name)
    return sorted(tools, key=key)[:TOOL_MAX]

# app.py:231-254 — 캐시를 컴파일된 에이전트에서 '도구 목록'으로 강등(로드는 여전히 그룹셋당 1회)
async def _agent_for(app, groups, message: str = ""):
    key = frozenset(groups or [])
    tools = app.state.tool_cache.get(key)
    if tools is None:
        tools = [_prep_tool(t) for t in await MultiServerMCPClient(_with_groups(groups)).get_tools()]
        app.state.tool_cache[key] = tools        # 로드 실패 시 미캐시 반환 로직(ec070a1)은 유지
    return create_react_agent(app.state.llm, _cap_tool_count(tools, message))
    # create_react_agent 컴파일은 저비용 — 요청당 재생성이 병목 아님.
    # 멀티턴 정합 문제 없음: history 는 user/assistant (role,content) 튜플만 재구성(app.py:257-280)

# app.py:302 — req.message 가 스코프에 있는 유일한 에이전트 생성 지점
agent = await _agent_for(app, req.groups, req.message)
```

`system_id`(app.py:139, 'portal Phase 2' 주석의 의도) → 백엔드 프리픽스 매핑(예: signalforge 페이지→`query_voc/search_voc/chart_*`, slurm 페이지→`slurm_*`)으로 후보군을 먼저 좁히면 top-k 정밀도가 오른다. deliberation.py `_tools_by_name`(deliberation.py:67-73)은 `app.state.tool_cache[key]`를 공유하도록 한 줄 수정.

### 3-4. AgentServer: meta 모드 소비 (`app.py` + `.env`)

```python
TOOL_MODE = os.environ.get("TOOL_MODE", "full")   # prod .env 에서 TOOL_MODE=meta

def _with_groups(groups):                          # app.py:100-109 기존 함수 확장
    cfg = ...  # 기존 헤더 주입
    if TOOL_MODE == "meta":
        cfg["headers"]["X-HWAX-Tool-Mode"] = "meta"
    return cfg
```

meta 모드에서는 `_cap_tool_count`/`_slim_tool`이 자연히 no-op(도구 3개)이 되고, 시스템 프롬프트에 사용 규약 한 단락을 추가한다 — "도구가 필요하면 반드시 search_tools 로 먼저 검색하고, 결과의 inputSchema 에 맞춰 invoke_tool 을 호출하라." 게이트웨이·AgentServer는 같은 파이썬 venv를 공유하므로(start.sh:6-8) mcp SDK 버전 불일치로 인한 스키마 협의 리스크는 낮다.

---

## 4) Claude Code 경로와의 대칭성

**Claude Code 경로는 이미 해결돼 있다.** Claude Code는 게이트웨이의 160개 도구를 클라이언트측 deferred tools + ToolSearch로 소비한다 — 도구 이름만 프롬프트에 들고 있다가 필요할 때 스키마를 로드하는, 본 설계의 A안과 동형인 구조가 하니스 레벨에 이미 있다. 따라서 게이트웨이 쪽에서 Claude Code를 위해 할 일은 **아무것도 없으며, 기본 모드(풀 리스트)를 절대 바꾸지 않는 것**이 곧 대칭성 유지다.

대칭 구도는 다음과 같다.

| | Claude Code | AgentServer(GLM) |
|---|---|---|
| 지연 로딩 주체 | 클라이언트(하니스 deferred+ToolSearch) | 서버(게이트웨이 meta 모드) |
| 게이트웨이 소비 방식 | 기본 모드 — `_list_tools()` 풀 스키마 | `X-HWAX-Tool-Mode: meta` opt-in |
| 검색 문법 | `select:이름` + 키워드 | search_tools 도 동일 문법 채택(§3-1d) — 정신 모델 대칭 |
| 공유 자산 | 전역 `exposed_tools`/`route`(gateway.py:122-123), 그룹 인가(L363-380, L413), audit, 백엔드 세션 — **전부 동일** | 좌동 |

유지 원칙 세 가지.
1. 모드는 요청 헤더로만 갈린다 — 엔드포인트·라우팅 테이블·인가 경로는 하나다. 게이트웨이의 그룹 헤더 메커니즘(gateway.py:383-391)과 동일 방식이므로 소비자 추가 시에도 게이트웨이는 불변이다.
2. 결과 슬림화(C)는 반드시 모드 조건부다 — Claude Code 경로도 `_call_tool`의 같은 반환 지점을 지나므로(gateway.py:425-428, 437-441) 무조건 치환하면 Claude Code의 원본 충실도(README의 "CallToolResult 그대로 반환" 계약)를 깨뜨린다.
3. 새 헤더는 `x-hwax-groups`와 별도 이름이어야 한다 — PAT 경로의 `_bearer_gate`가 groups 헤더를 강제 재작성하므로(gateway.py:488-491) 같은 이름 계열에 실으면 소실된다.

---

## 5) 리스크와 완화책

| # | 실패 모드 | 완화책 |
|---|---|---|
| R1 | **GLM이 search_tools를 건너뛰고 invoke_tool에 추측 이름을 넣는다** (가장 유력한 실패 모드) | 3중 방어. (1) unknown tool 에러에 유사 도구 top-5와 "search_tools 를 먼저 호출하라"를 동봉해 자가 회복 루프 형성(§3-1e), (2) AgentServer 시스템 프롬프트에 사용 규약 명시, (3) invoke_tool description에 선행 조건 명기. 그래도 실패율이 높으면 **하이브리드로 후퇴** — AgentServer가 사용자 질문으로 search_tools를 서버측 선실행해 top-k 결과를 시스템 프롬프트에 주입(A의 토큰 절약 + B의 직접성) |
| R2 | **GLM이 도구를 아예 안 쓴다** — 노출 2~3개뿐이라 "slurm 잡 상태 봐줘"에 해당 도구가 보이지 않아 발견성 저하 | search_tools description에 대표 도메인 카테고리를 나열(§3-1b)해 "검색하면 나온다"는 단서 제공. 회귀 질문셋(slurm/VOC/재료/보고서 각 도메인)으로 도구 사용률을 배포 전후 비교 |
| R3 | **자유형 dict 인자 품질** — invoke_tool의 `arguments: object`는 스키마 강제가 없고(validate_input=False, gateway.py:400) 백엔드 에러가 불친절할 수 있다 | search_tools 결과에 슬림 inputSchema 동봉(§3-1d)으로 호출 직전 스키마를 컨텍스트에 확보. 필요 시 invoke 경로에 한해 게이트웨이 선택적 jsonschema 검증을 추가해 "required 'job_id' 누락" 수준의 친절한 에러로 변환 |
| R4 | **왕복 증가** — search→invoke로 스텝 1~2회 추가. prod는 스트리밍 비활성(vLLM GLM tool_calls 유실 우회, 커밋 744ca13)이라 체감 지연이 큼 | R1의 서버측 선검색 주입이 첫 왕복을 제거. 스텝당 토큰이 95% 줄어 LLM 호출 자체는 빨라지므로 순지연은 실측으로 판단 |
| R5 | **16K dev 모델에 meta 모드 부적합** — 2단 간접 호출·중첩 dict는 소형 모델에서 정확도가 떨어짐 | 애초에 dev에 meta를 강제하지 않는다 — 소비자별 헤더 분리(dev=B top-k, prod=A meta)가 설계의 전제(§2) |
| R6 | **B의 매칭 실패는 하드 실패** — top-k에 정답 도구가 없으면 회복 불가 | `_TOOL_PRIORITY` 폴백 유지 + system_id 후보군 축소로 정밀도 보강. 근본적으로는 prod가 A로 넘어가면 B는 dev 전용 완충이 됨 |
| R7 | **B의 정적 스냅샷 stale** — 게이트웨이 revive 재집계는 알림을 안 보내므로(gateway.py:235-239) AgentServer 캐시가 낡는다 | 도구 캐시에 TTL(예: 10분) 부여 또는 주기 재로드. meta 모드는 매 검색이 live `exposed_tools`를 보므로 구조적으로 해소 — prod 전환의 부가 근거 |
| R8 | **C 핸들의 소유권·수명** — MCP 경로는 caller 미기록이라 무귀속 핸들은 타 사용자 결과 열람 통로가 됨 | put 시점 caller 귀속(request_context의 PAT sub 또는 groups) + fetch_result에서 대조(§3-2), TTL GC(1h), 핸들은 추측 불가 랜덤 id |
| R9 | **LLM이 fetch_result를 안 부르고 head 요약만으로 오답** | 치환문에 전체 크기·조회 방법을 명시(현행 절단 안내문의 승격판). 임계는 단계 0 실측(p95)으로 보수적으로 설정해 치환 빈도 자체를 낮춤 |
| R10 | **D와 B의 프리픽스 상충** — 요청마다 도구 집합이 바뀌면 요청 간 KV 캐시 미스 | B에서는 선택 도구를 이름순 결정적 정렬로 바인딩. D의 본 수혜처는 프리픽스가 완전 고정되는 A 적용 후 prod — 적용 순서를 A 다음(단계 4)에 둔 이유 |
| R11 | **헬스체크·문서 혼선** — meta 모드 도입으로 "노출 도구 수"의 의미가 갈라짐 | `/health`의 `tools`는 `len(exposed_tools)`(집계된 실제 도구 수) 의미를 불변 유지(gateway.py:461-471). README의 "46개"·포트 9009는 stale이므로(실제 160개·9110) 이번 작업에서 README 수치도 함께 정정 |