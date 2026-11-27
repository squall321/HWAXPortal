# MCP 공통 계약 — 앱 · 사내 MCP 에 보내는 기준표

> 정본 계획 [PLAN.md](PLAN.md). 이 글은 HWAX 게이트웨이에 붙는 모든 MCP 서버(우리 앱 · 사내 앱)에 같은 꼴로 보낸다. 받는 쪽은 항목마다 「됨 · 할 차례 · 안 함(까닭)」
> 을 답한다. 근거 숫자는 [audit/contract.md](audit/contract.md) · [audit/onprem.md](audit/onprem.md).

## 0. 왜

게이트웨이에는 cae00 기준 도구가 2,000개 가까이 모인다. 모델은 도구를 이름 · 설명 · 인자 스키마로만 고르고 부른다. 그 셋이 산문 · 이력 · 빈칸이면 2,000개
속에서 잘못 고르고, 인자를 지어내고, 읽기 도구를 쓰기로 막는다. 아래 아홉 항목은 그것을 스키마로 옮기는 최소 기준이다.

## 1. 프로토콜 — stateless · 두 세대

| # | 항목 | 기준 |
|---|---|---|
| P1 | stateless | 서버가 세션을 쥐지 않는다. SDK 1.x 면 `FastMCP(..., stateless_http=True)`(1단계). 세션에 기대던 상태는 서버가 낸 handle 을 도구 인자로 받는다(스펙 SEP-2567) |
| P2 | 두 세대(dual-era) | SDK 2.x(`mcp>=2.3`, Python 3.11 이상)로 옮겨 2026-07-28 새 세대와 옛 세대(initialize)를 같은 자리에서 낸다 — 2.x 는 플래그 없이 둘 다 받는다(2단계). 마운트한 앱은 호스트 lifespan 에서 `mcp.session_manager.run()` 을 들어간다 |
| P3 | 오류 꼴 | 모델이 읽어야 할 오류는 `ToolError`(2.x) 로 낸다 — 일반 예외는 2.x 에서 「Error executing tool <이름>」 으로 가려져 내용이 사라진다. `ToolError` 도 2.3 에서는 글 앞에 「Error executing tool <이름>: 」 머리가 붙는다(게이트웨이 · 포털은 이 머리를 떼고 읽는다). 계약 오류를 `{"error": "<낱말>", "detail": "<사람 글>"}` JSON 하나로 내려면 `CallToolResult(is_error=True, content=[…])` 를 직접 돌려준다(DocForge 0.5.0 꼴). 이미 쓰는 오류 봉투(errors[] 등)가 있고 소비처가 그 꼴을 읽으면 봉투를 그대로 둔다 |

## 2. 도구 계약 — 아홉 항목

| # | 항목 | 기준 | 1.x 에서 쓰는 법 |
|---|---|---|---|
| C1 | 설명의 꼴 | 첫 줄에 무엇을 하는지 한 문장 → 언제 쓰나 · 언제 형제 도구를 쓰나(이름으로) → 돌려주는 꼴 · 한도 · 페이지. 400 ~ 1,500자. 결정 번호 · 날짜 · 실측 일화 · 판 이력은 넣지 않는다(문서로) | docstring 첫 단락 |
| C2 | 인자 설명 | 모든 인자에 설명 · 단위(MPa · mm · s) · 범위 · 기본값의 뜻. 산문 「Args:」 가 아니라 스키마에 | `Annotated[float, Field(description="… (MPa)", ge=0)]` |
| C3 | 닫힌 어휘는 enum | 정해진 낱말 집합이면 enum. 큰 집합(100개 넘음)은 설명에 찾는 도구 이름을 적는다 | `Literal["x", "y"]` |
| C4 | 숫자 경계 | `limit` · `page` · 개수 · 비율에 최소 · 최대. 상한은 설명에도 적는다 | `Field(ge=1, le=200)` |
| C5 | 구조 있는 객체 | 자유형 `object` 대신 모델(`$defs`)로. 정말 자유형이면 키 예시를 설명에 | pydantic 모델 인자 |
| C6 | 읽기 · 쓰기 표지 | 모든 도구에 `readOnlyHint` · 바꾸는 도구는 `destructiveHint` · 같은 호출을 거듭해도 같으면 `idempotentHint`. 바깥 세계를 부르면 `openWorldHint`. **tools/list 에 camelCase 로 나오는지 꼭 확인** | 1.x 는 `ToolAnnotations(readOnlyHint=True)`(camelCase — ⚠ 1.x 에서 `read_only_hint=` 로 쓰면 모르는 칸으로 붙어 `{"read_only_hint": true}` 가 나가고 클라이언트는 표지를 못 받는다). 2.x 는 `ToolAnnotations(read_only_hint=True)` |
| C7 | 결과 꼴 | 구조 있는 결과는 반환 타입을 모델로 적어 실제 필드가 있는 `outputSchema` 를 낸다. 큰 결과는 요약 + handle · 페이지. ⚠ SDK 는 구조 결과가 있으면 같은 내용을 글로도 실어 응답이 두 배가 된다 — 큰 결과(수 MB)를 내는 도구는 게이트웨이가 한쪽만 모델에 넘길 때까지(PLAN M2) 모델을 달지 않아도 된다. 결과 모델은 추가 칸을 허용해 앱이 칸을 더해도 깨지지 않게 | 반환 타입 힌트 |
| C8 | 정직한 한도 | 잘랐으면 잘랐다고(`truncated` · `total` · `next_cursor`). 조용히 200 · 100 에서 끊지 않는다 | 결과 칸 |
| C9 | 이름 | 앱 안에서 뜻이 겹치지 않는 동사_대상. 앱 사이 흔한 이름(`search` · `list_jobs` · `cancel_job`)은 앱 접두를 스스로 달지 않는다 — 게이트웨이가 겹칠 때만 접두를 붙인다. 설명에 게이트웨이 접두 이름을 박지 않는다 | — |

## 3. 로드맵 — 해당하는 앱만

| # | 항목 | 기준 |
|---|---|---|
| R1 | 이벤트 | 오래 도는 잡 · 새 데이터가 생기는 앱은 게이트웨이 이벤트 허브가 받을 이벤트를 낸다 — 지금은 「바뀐 것 목록」 읽기 도구(커서 · 시각 · 종류 · id)로 충분하다(게이트웨이가 묻고 `io.modelcontextprotocol/events` 로 다시 낸다). 이름은 `<앱>.<대상>.<일>`(예 `stepforge.revision.created`) |
| R2 | 길 안내 | 앱의 대표 업무 둘 ~ 다섯을 「목적 · 차례 · 입구 도구 · 확인할 쓰기」 로 적어 보낸다 — 게이트웨이 목적 표(`tool_purposes.json`)와 skill 의 씨앗이 된다 |
| R3 | 앱 입구 | 그 앱을 처음 부를 때 먼저 부를 도구 하나(`get_guide` · `next_step` 류)를 정해 알린다 |

## 4. 답하는 꼴

항목마다 한 줄 — `C2 | 할 차례 | 11-30 판에서 | (비고)`. 도구 수 · 인자 설명 비율 · 표지 비율은 게이트웨이 품질 카드가 잰다. 앱 쪽은 판(커밋 · SIF 열쇠)만 알리면 된다.
