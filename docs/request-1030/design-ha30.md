# HA-30 설계 — 허브를 건널 때 앞 허브의 id 를 넘기지 않게

요청 행 정본은 [`../request_261030.md`](../request_261030.md) HA-30(중간)이고 판단 기록은 [`context-notes.md`](context-notes.md) 다.
요청서의 기준 판은 cae00 에이전트 서버 `969e723` 이다. 이 문서의 줄 번호는 dev HEAD `7ca3a2e` 의 것이라 함수 이름을 함께 적는다.
설계만 한다 — 저장소 코드는 고치지 않았다(10-30 읽기 전용 대조).

## 0. 결정 한 줄

- 이 턴에 **허브 도구가 성공으로 돌려준 결과**에서 UUID 를 모아 '어느 허브에서 본 id 인가' 를 턴 상태에 적는다.
- 허브 도구를 부르기 직전에 인자에 든 UUID 가 **다른 허브에서만 본 것**이면 보내지 않고, '이 id 는 ○○ 허브 것 — key 로 다시 풀어라' 를 정확한 다음 호출(대상 허브의 object_resolve · type_slug · key)과 함께 돌려준다.
- 요청의 첫째 안(코드가 대신 key 로 다시 풀어 바꿔 보내기)은 고르지 않는다(5절).
- 기존 코드에 닿는 자리는 래퍼(`_cap_tool.capped`)의 두 곳 · 턴 시작 한 줄 · 어휘표 build 의 한 칸이다. 래퍼에서는 부르기 전(유령 ID 막이 바로 뒤 · HA-29 확인 카드 앞)과 결과 쪽(`_learn_ids(body)` 바로 옆)이다. 나머지는 새 도우미 함수다.

## 1. 실측과 지금 동작

### 1.1 실측

- 10-30 OT-07 — `failuretrace_graph_neighbors` 에 자주검증 허브의 id 를 넘겨 `[APP-GRAPH-0001]` 이었다.
- 10-27 온톨로지 시험 N-13 도 같은 꼴이었다(포털 `docs/request-1027/02-HWAXMcpGateway.md` HG-06 — 게이트웨이 감사 ok=True · 48자). 허브 MCP 는 오류를 `{"error": "[APP-GRAPH-0001] 객체를 찾을 수 없습니다."}` 봉투로 돌려준다(StandardPlatform `mcp_server/server.py` `_unwrap` · `backend/app/modules/graph/routes.py:429`).
- 규칙 ⑤('다른 허브로 건널 때는 앞 허브의 id 를 그대로 쓰지 말고 key 로 그 허브에서 다시 resolve')는 프롬프트 글뿐이다. 두 번의 시험(10-27 · 10-30)에서 지켜지지 않았다.

### 1.2 지금 코드(dev `7ca3a2e`)

| 자리 | 함수 · 줄 | 하는 일 | HA-30 과의 관계 |
|---|---|---|---|
| 규칙 ⑤ | `_CORE_RULES_DEFAULT`(193) · `_core_rules_text`(303) | 시스템 프롬프트 글 | 지킬지 말지는 모델 몫이다. |
| 유령 ID 막이 | `_turn_ids`(1410) · `_learn_ids`(1437) · `_phantom_id_arg`(1606) · `capped` 1919-1937 | 이번 턴 어디에도 없던 **정수**를 식별자 인자에 넣은 호출을 막는다 | `isinstance(v, int)` 가 아니면 보지 않는다 — UUID 문자열 id 는 처음부터 그냥 지난다. 결과에서 배울 때도 어느 앱의 결과인지 적지 않는다. |
| 앱 머리 | `_app_label_cached`(1804) · `_chat_result_note`(1813) | 결과 글 앞에 '[이 결과는 ○○ 앱의 … 이다]' | 모델에게 알려 줄 뿐이고, 호출 쪽 검사는 없다. |
| 허브 접기 | `_fold_hub_result`(1750) | 큰 허브 응답을 접는다 | 접은 글(모델이 보는 글)에서 배운다. |
| 도구 래퍼 | `_cap_tool`(1832) · `capped`(1886-2013) | 아래 순서로 돈다 | 두 자리를 더한다(3.7). |
| 턴 상태 | `_agent_stream_turn`(4807) · 4841-4842 | `_turn_ids` · `_turn_tool_calls` 를 턴마다 건다 | 같은 자리에서 새 상태를 건다. |
| 앱 맵 | `_TOOLS_MAP_CACHE`(2500) · `_tools_map`(2552) | 게이트웨이 `/tools-map` 의 노출 이름 → 백엔드 키 | 캐시만 읽는다. |
| 경유 | `capped` 2003-2005 의 `_eff` · `_inner_tool`(3905) | invoke_tool 의 안쪽 이름 | 판정 · 배우기 모두 안쪽 이름으로 한다. |
| 성패 | `_result_ok`(3864) | ✖ · 오류 봉투(`{"error": …}`)를 실패로 본다 | 실패 결과에서는 배우지 않는다. |

`capped` 의 지금 순서는 이렇다.

1. invoke_tool 의 안쪽 이름이 거부 도구(외부 응답자 과제 · 패널 · 루틴)면 돌려준다(1889-1903).
2. 외부 응답자 심의 · 반출 동의 칸을 실은 호출이면 돌려준다(1906-1918).
3. 유령 ID 막이(1919-1937).
4. 챗 인자 기본값(1938-1953).
5. 호출(1954) · 예외는 ✖ 글로(1956-2001).
6. 접기 → 자르기 → 인자 힌트 → `_learn_ids(body)` → 앱 머리 · 되풀이 꼬리(2002-2013).

## 2. 허브 · 도구 이름 · id 의 모양

### 2.1 어느 앱이 허브인가

- 포털 코어 어휘표(`backend/config/core_vocab.json`)의 canonical `rootdesigndatahub`(자주검증 Datahub(rootdesign))와 role `sibling` 인 `failuretrace`(FailureTrace) · `caegroupdatahub`(CAE 그룹 Datahub — 요청서의 '부서 허브')다. 셋 다 hwax-batch Datahub 플랫폼(StandardPlatform) 설치다.
- role `staging` 인 `stepforge-prod` · `dynaforge-prod` 는 허브가 아니다. StepForge · DynaForge 운영 사본(외부 연결)이라 도구와 id 꼴이 다르다.
- dev 게이트웨이 `/tools-map`(10-30 08:36 읽음)에는 허브가 없다(백엔드 17개 · 도구 564개). dev 에서 실물 재현은 안 되고, 시험은 가짜 도구로 한다.

### 2.2 노출 이름

- 세 허브는 같은 틀이라 도구 이름이 모두 같다(허브 MCP 의 `SAME_TOOLS_RULE` 이 스스로 그렇게 말한다).
- 게이트웨이 `_aggregate`(gateway.py:1122-1157)는 겹치는 이름에 `<백엔드 키에서 '-' 를 뺀 것>_<도구>` 접두를 단다. 그래서 `rootdesigndatahub_graph_neighbors` · `failuretrace_graph_neighbors` · `caegroupdatahub_graph_neighbors` 가 된다. 에이전트 `_ONTO_CORE`(2294)가 같은 이름을 쓴다.
- 모든 도구에는 같은 꼴의 호출 전용 별칭도 있다(gateway.py:1144-1151). 허브 하나만 붙은 박스면 접두가 없는 맨 이름이고, 그때는 `/tools-map` 이 가른다.

### 2.3 id 와 key

- 근거 소스는 형제 리포의 StandardPlatform 0.4.52 사본(`StepForge/external/StandardPlatform`, 도구 76개)이다. 배포판은 더 새것이다(10-27 `/tools-map` 에서 허브마다 103개 — request-1027 HG-05). 그래서 설계는 도구 · 인자 이름 목록에 기대지 않고 **값의 꼴(UUID)** 로 본다.
- 객체 id 는 설치마다 따로 만든 UUIDv4 다(`backend/app/modules/objects/models.py:162` — `PgUUID(as_uuid=True), default=uuid.uuid4`). 관계 · 첨부 · 잡 · 이력 id 도 UUID 다.
- 형제 허브는 정본의 코어를 `/api/core/<타입>` 으로 **key 로** 받는다(`datasources/fetchers.py` 의 sp_core · `coreapi/schemas.py` — '값은 그 타입의 key 로 나간다 — id 로 주면 받는 쪽에서 아무것도 못 가리킨다'). 그래서 같은 객체가 허브마다 **id 는 다르고 key 는 같다**.
- 10-29 OT-12 는 key `JNT-SLD-01` 로 FailureTrace 와 정본이 같은 개체임을 확인했다. CAE 그룹 허브도 같은 key 의 관계가 정본과 같았다(`request_261029.md` OT-12 · CAE그룹 행).
- 예 — 정본 고장모드 key `JNT-SLD-01`(type_slug `failure_mode`), 부품 key `PRT-PCB`(type_slug `part`). id 는 `0b6f1c3e-6a51-4c1e-9f0e-1d2c3b4a5f60` 같은 꼴이다(시험용 예).

### 2.4 id 를 받는 자리(0.4.52 기준 — 예시일 뿐 목록으로 쓰지 않는다)

| 인자 | 도구 |
|---|---|
| `object_id` | object_get · object_history · object_rollup · object_references · objects_similar · graph_neighbors · object_update · object_restore · object_merge · attachment_upload_prepare · relation_add · relation_update · relation_remove · alias_candidate_apply |
| `dst_object_id` · `into` · `parent` | relation_add · object_merge · object_tree |
| `ids`(목록) | bulk_edit · objects_delete |
| 그 밖의 설치 id | `relation_id` · `entry_id` · `job_id` · `run_id` · `batch_id` · `attachment_id` · `candidate_id` · `alias_ids` · `snapshot_id` |
| 숨은 자리 | objects_list · objects_summary 의 `conditions[].value`(참조 칸의 값은 id 다 — `in` 은 `\|` 로 잇는다), object_resolve 의 `name` · search 의 `q` 에 id 를 넣은 경우, rdf_query 의 글 |

숨은 자리의 다른 허브 id 는 오류가 아니라 **0건**으로 돌아와 '없다' 로 읽힌다. graph_neighbors 의 APP-GRAPH-0001 보다 나쁜 꼴이라, 칸 이름이 아니라 인자 전체에서 UUID 를 찾는다.

### 2.5 결과에서 id 가 실리는 자리

- object_resolve · objects_resolve_many — `object` · `candidates[]` 가 `{id, key, label, type_slug, …}`(ResolveHit).
- objects_list — `items[]` 가 `{id, type_slug, key, label, …}`(ObjectOut).
- object_get — `object{…}` 와 `related[]` 의 `{relation_id, object_id, object_key, object_label, object_type_slug, …}`(RelatedObjectOut).
- graph_neighbors — `focus` · `nodes[]{id, key, label, type_slug}` · `edges[]{id, src, dst}`.
- search — `items[]{id, type_slug, key, label}`.
- 오류는 `{"error": "[APP-…] …"}` 봉투다. `_result_ok` 가 실패로 본다.

## 3. 설계

### 3.1 턴 상태

- `_turn_hub_ids: ContextVar`(기본 None)를 `_turn_ids` 옆에 둔다.
- `_agent_stream_turn` 의 `_turn_tool_calls.set(Counter())`(4842) 바로 뒤에서 `_turn_hub_ids.set({} if _XHUB_GATE else None)` 로 턴마다 새로 건다.
- 값은 `{uuid(소문자): {"apps": set[허브 키], "hub": 처음 본 허브, "tool": 처음 낸 도구 이름, "key": str, "type": str, "label": str}}` 다.
- None 이면(심의 · 카탈로그 · 루틴 · 띵킹 · 턴 밖의 시험) 배우지도 막지도 않는다. 유령 ID 막이와 같은 fail-open 이다.
- 상태는 변경 가능한 dict 하나라 병렬 도구 호출의 자식 문맥에서 더한 것이 같은 턴의 다음 호출에 보인다(`_learn_ids` 와 같은 꼴 — 1438-1440 의 주석).

### 3.2 허브 판정

- `_HUB_APPS_DEFAULT = {"rootdesigndatahub": "자주검증 Datahub(rootdesign)", "failuretrace": "FailureTrace", "caegroupdatahub": "CAE 그룹 Datahub"}`.
- `_core_vocab()` 의 `build()`(323)에 `"hubs"` 칸을 더한다 — `{canonical.app: canonical.label} ∪ {키: label for apps 가운데 role == "sibling"}`. `/health` core_vocab 꼴(`_core_vocab_health`)은 칸을 골라 싣으므로 바뀌지 않는다.
- `_hub_apps() -> {키: 라벨}` — 어휘표가 읽혔으면 그 `hubs`, 없거나 깨졌으면 기본표다. 박스 덧씌우기(`core_vocab.local.json`)로 sibling 을 더하면 커밋 없이 허브가 는다.
- `_hub_of(name) -> 허브 키 | ""` — `_TOOLS_MAP_CACHE["map"]` 만 본다(게이트웨이에 묻지 않는다 — 도구 호출마다 부르므로 `_app_label_cached` 와 같은 까닭). 맵에 이름이 있으면 그 키가 허브일 때만 그 키, 아니면 빈 값이다. 맵에 없으면 이름이 `<허브 키에서 '-' 를 뺀 것>_` 로 시작하는지로 가른다(별칭 · 캐시가 빈 때).
- `_hub_tool(hub, base) -> 노출 이름` — 글에 실을 대상 허브의 도구 이름이다. `<접두>_<base>` 가 맵에 있으면 그것, 맵의 `base` 가 그 허브 것이면 `base`, 둘 다 아니면 `<접두>_<base>`(별칭이라 invoke_tool 로 늘 닿는다).

### 3.3 배우기 — `_learn_hub_ids(name, text)`

자리는 `capped` 결과 쪽 두 갈래(2009 · 2012)의 `_learn_ids(body)` 바로 뒤다. 같은 `body`(접기 · 자르기 · 인자 힌트를 거친, 모델이 보는 글)와 `_eff`(경유면 안쪽 이름)를 준다.

1. 상태가 None 이거나 글이 아니면 끝낸다.
2. `_hub_of(name)` 가 빈 값(허브가 아닌 도구)이면 끝낸다.
3. `_result_ok(text)` 가 거짓(✖ · 오류 봉투 · 막이 글)이면 끝낸다. 오류 글은 받은 id 를 되풀이할 수 있어, 배우면 그 허브 것으로 잘못 적는다.
4. 글의 UUID 를 모두 모은다 — `_UUID_RE = (?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])`, 소문자로 맞추고 차례를 지켜 겹침을 뺀다.
5. 새 id 는 상태가 `_HUB_IDS_MAX`(20,000) 미만일 때만 적는다. 이미 있는 id 에 허브를 더하는 것은 늘 한다 — 상한이 거짓 막음을 만들지 않게 한다(넘으면 모르는 id 가 되어 지나간다).
6. 이름표(key · type · label)는 글을 JSON 으로 읽을 수 있을 때만 얻는다. 접기 머리 줄(`[포털 챗이 허브 응답을 접었다`)은 떼고 읽는다. 두 꼴만 본다 — `{id, key|label, type_slug}` 와 `{object_id, object_key|object_label, object_type_slug}`. 깊이 12 까지, 처음 본 이름표를 남긴다. 못 읽으면(상한에서 잘린 글) 이름표 없이 id 만 적는다.

### 3.4 부르기 전 검사 — `_cross_hub_id_msg(target, args) -> str | None`

자리는 `capped` 의 유령 ID 막이(1919-1937) 바로 뒤, 인자 기본값(1938) 앞이다. 외부 응답자 관문(1906-1910)과 같은 갈래로 `(kw, *a 의 dict)` 를 돈다 — 직접 묶인 도구면 `(tool.name, _args)`, 경유(`_via_inv`)면 `(_args["name"], _args["arguments"])`.

1. 상태가 None 이거나 비었으면 None — 이 턴에 허브 결과가 아직 없다. 이 판정이 맨 앞이라 허브와 상관없는 턴의 비용은 dict 하나 읽기다.
2. `dst = _hub_of(target)` 가 빈 값이면 None.
3. 인자를 글로 만든다 — 글이면 그대로, 아니면 `json.dumps(args, ensure_ascii=False, default=str)`. 그 글의 UUID 를 모은다(칸 이름 · 깊이와 상관없다 — `conditions` 안 · `|` 로 이은 값 · JSON 글로 온 invoke_tool 인자도 잡힌다).
4. 막을 id 는 상태에 있고 `dst` 가 그 `apps` 에 없는 것이다. 상태에 없는 id(사람이 친 것 · 앞 턴의 것 · 처음 보는 것)와 `dst` 가 `apps` 에 든 id(제 것 · 공유 id)는 지난다.
5. 하나라도 있으면 보내지 않고 3.5 의 글을 돌려준다(`response_format == "content_and_artifact"` 면 `(글, None)`). 로그 한 줄을 남긴다 — `[gate] failuretrace_graph_neighbors(object_id=0b6f1c3e…) 차단 — rootdesigndatahub 의 id 를 failuretrace 에 실었다(다른 허브 id 1개)`.

막은 호출은 `_chat_result_note` 앞에서 끝나므로 W-5 되풀이 계수에 들지 않는다(유령 ID 막이와 같다).

### 3.5 돌려주는 글(정확한 문구)

상수 `_XHUB_ID_MARK = "는 다른 허브의 id 다"`, 보이는 id 상한 `_XHUB_SHOW = 3` 이다. 글의 짜임은 이렇다.

1. 머리 — `✖ 도구 {target} 호출 실패(보내지 않았다): `(✖ 는 `_TOOL_FAIL_MARK` — `_result_ok` 가 실패로 보고 화면 활동이 실패로 그린다).
2. id 마다(앞 3개) — `{칸}={uuid} 는 다른 허브의 id 다 — 이 턴에 {출처 허브 라벨} 의 {출처 도구} 결과에서 나왔다({누구}).` 칸은 그 UUID 가 든 맨 위 인자 이름이고, 못 가르면 `arguments` 다. 누구는 `key 「K」 · type_slug T` · `key 없음 · 이름 「L」 · type_slug T` · `key 를 결과에서 읽지 못했다` 가운데 하나다(type 을 모르면 그 조각을 뺀다).
3. 넘치면 — `그 밖에 {n}개도 다른 허브의 id 다.`
4. 까닭 — `허브마다 같은 객체도 id 가 달라 {대상 허브 라벨} 에서는 이 id 로 찾지 못한다.`
5. 고칠 길
   - 막은 id 가 하나이고 이름(key, 없으면 label)과 type 을 알면 `{res}(type_slug="{T}", name="{K}") 로 {대상} 의 id 를 받아 그 id 로 다시 불러라(그 타입이 없다고 하면 {srch}(q="{K}")).`
   - 하나이고 이름만 알면 `{srch}(q="{K}") 로 {대상} 에서 그 객체를 찾아 그 id 로 다시 불러라.`
   - 그 밖에는 `각 객체의 key 로 {res}(type_slug, name=key) — 여럿이면 {many}(type_slug, names=[…]) — 를 불러 {대상} 의 id 를 받아 다시 불러라. key 를 모르는 id 는 앞 허브의 결과에서 그 객체의 key 를 찾는다.`
   - `res` · `many` · `srch` 는 `_hub_tool(dst, "object_resolve" | "objects_resolve_many" | "search")` 다. 글에 싣는 K · L 은 공백을 한 칸으로 줄이고 `"` 를 `'` 로 바꾸고 80자로 자른다.
6. 꼬리 — `candidates 면 고르지 말고 사용자에게 묻고, none 이면 '{대상} 에서 찾지 못했다' 고 말하라. 인자 문제가 아니다 — 같은 id 로 다시 부르지 마라.`

OT-07 을 다시 짓는 경우에 모델이 받는 글은 이렇다.

```
✖ 도구 failuretrace_graph_neighbors 호출 실패(보내지 않았다): object_id=0b6f1c3e-6a51-4c1e-9f0e-1d2c3b4a5f60 는 다른 허브의 id 다 — 이 턴에 자주검증 Datahub(rootdesign) 의 rootdesigndatahub_object_resolve 결과에서 나왔다(key 「JNT-SLD-01」 · type_slug failure_mode). 허브마다 같은 객체도 id 가 달라 FailureTrace 에서는 이 id 로 찾지 못한다. failuretrace_object_resolve(type_slug="failure_mode", name="JNT-SLD-01") 로 FailureTrace 의 id 를 받아 그 id 로 다시 불러라(그 타입이 없다고 하면 failuretrace_search(q="JNT-SLD-01")). candidates 면 고르지 말고 사용자에게 묻고, none 이면 'FailureTrace 에서 찾지 못했다' 고 말하라. 인자 문제가 아니다 — 같은 id 로 다시 부르지 마라.
```

- key 의 출처 — 같은 턴에 그 UUID 를 낸 허브 결과의 JSON 이다(3.3 의 6). resolve · 목록 · 검색 · 그래프 노드 · object_get 의 관련 객체가 모두 key 를 싣는다.
- 'type 이 없다고 하면 search' 는 형제 허브가 코어 타입을 다른 slug 로 받았을 때의 대안이다(허브 MCP 안내 '타입을 모를 때의 첫 걸음 search').
- 글에는 게이트 표지 `_PHANTOM_ID_MARK` 를 싣지 않는다. 그 표지는 심의가 '실행되지 않은 호출' 로 읽는 다른 계약이다(deliberation.py:3012 · 3421).

### 3.6 손잡이

- `CHAT_XHUB_ID_GATE`(기본 `1`, `0` 이면 끈다 — 턴 상태를 None 으로 둬 종전과 글자 하나 다르지 않다). 기동 때 읽는다(`CHAT_STABLE_PREFIX` 와 같은 꼴 — 바꾸면 재기동).
- 끄는 손잡이를 두는 까닭은 HA-26 과 같다 — 박스에서 막음이 잘못 들면 커밋 없이 우회한다(복제 설치 같은 예외, 9절 R1).
- 상수(손잡이 아님) — `_HUB_IDS_MAX = 20_000` · `_XHUB_SHOW = 3` · 이름표 깊이 12 · 이름표 글 80자.

### 3.7 바꾸는 곳(코드 꼴)

`_learn_ids` · `_phantom_id_arg` 가 있는 'ID 출처' 절(1404-1616)에 상수 · 상태 · 함수 일곱(`_uuids` · `_hub_apps` · `_hub_of` · `_hub_tool` · `_hub_id_meta` · `_learn_hub_ids` · `_cross_hub_id_msg`)을 둔다. 래퍼에는 두 자리만 더한다.

```python
        # (capped — 유령 ID 막이 바로 뒤, 인자 기본값 앞)
        # 다른 허브의 id(HWAXPortal docs/request-1030 HA-30) — 이 턴에 다른 허브의 결과에서만 본 id 를 허브 도구에 실은 호출은 보내지
        # 않고 key 로 다시 풀라고 돌려준다. 직접 묶인 도구로도, invoke_tool 의 안쪽 이름으로도 같다. HA-29 확인 카드보다 앞이다.
        for _args in (kw, *(x for x in a if isinstance(x, dict))):
            _target, _targs = ((_args.get("name"), _args.get("arguments")) if _via_inv
                               else (getattr(tool, "name", ""), _args))
            _xmsg = _cross_hub_id_msg(_target, _targs)
            if _xmsg:
                return ((_xmsg, None)
                        if getattr(tool, "response_format", "") == "content_and_artifact" else _xmsg)
```

```python
        # (capped — 결과 쪽 두 갈래 모두)
            _learn_ids(body)
            _learn_hub_ids(_eff, body)
```

```python
    # (_agent_stream_turn — 4842 바로 뒤)
    _turn_tool_calls.set(Counter())
    _turn_hub_ids.set({} if _XHUB_GATE else None)
```

```python
    # (_core_vocab 의 build — 323)
    "hubs": {d["canonical"]["app"]: d["canonical"].get("label") or d["canonical"]["app"],
             **{k: (a or {}).get("label") or k for k, a in (d.get("apps") or {}).items()
                if (a or {}).get("role") == "sibling"}},
```

규모는 함수 약 70줄 · 래퍼 9줄 · 턴 1줄 · build 3줄이다. HA-34 워크트리(`wt1030/ha34`)는 `_fold_hub_result` 안만 고쳤고 `capped` 는 건드리지 않아 겹치지 않는다. HA-26r · HA-31 · HA-33 · HA-08 워크트리도 이 자리를 건드리지 않는다(10-30 diff 대조).

## 4. 공유 id · 사람이 친 id · 앞 턴의 id

| 경우 | 판정 | 까닭 |
|---|---|---|
| 두 허브 결과에 다 나온 id(공유) | 지난다 — 대상이 `apps` 에 들어 있다. | 같은 UUID 가 대상 허브에서 진짜 그 객체일 수 있다(복제 설치). 잘못 지나간 경우의 대가는 지금과 같은 오류 한 번이다. |
| 대상 허브 결과에만 나온 id | 지난다. | 제 것이다. |
| 다른 허브 결과에서만 나온 id | 막는다. | OT-07 의 꼴이다. |
| 사람이 친 id · 앞 턴의 id(이 턴 허브 결과에 없음) | 지난다 — 모르는 id 다. | 출처 앱을 모른다. 요청 행의 범위가 '이번 턴 결과' 다. |
| 사람이 쳤고 이 턴에 다른 허브 결과에도 나온 id | 막는다 — 면제하지 않는다. | 설치마다 uuid4 라 다른 허브 결과에 나온 id 는 그 허브 것이 확실하다. 막고 key 로 풀게 하면 사람이 원한 답(대상 허브의 그 객체)에 닿는다. 복제 설치라면 다시 푼 결과가 같은 id 를 돌려줘 다음 호출이 지난다(한 왕복으로 스스로 풀린다). |
| 오류 결과에만 나온 id | 배우지 않는다. | 오류 글은 받은 id 를 되풀이한다. |

## 5. 코드가 대신 다시 풀까(요청의 첫째 안) — 평가

고르지 않는다. 할 수는 있지만 늘 되지는 않고, 되는 경우에도 숨은 호출이 남는다.

- **필요한 것** — 그 id 의 key · type_slug(같은 턴 결과에 있을 때만 — 간선 끝 · 참조 칸 값 · 잘린 글이면 없다), 대상 허브의 resolve 도구 손잡이(`capped` 는 도구 하나만 쥔다 — 턴의 도구 묶음을 문맥 변수로 따로 실어 날라야 한다).
- **안 되는 경우** — 대상 허브가 그 코어 타입을 다른 slug 로 받았으면 resolve 가 실패한다. `candidates` 면 규칙 ①(고르지 말고 묻는다) 때문에 코드가 고를 수 없다. `none` 이면(FailureTrace 는 코어 일부만 가진 사본이다) 결국 글을 돌려줘야 한다.
- **위험** — 쓰기 도구(relation_add · object_update · bulk_edit · objects_delete)에서 말없이 대상을 바꾸면 틀린 객체에 쓴다. 쓰기는 빼야 한다.
- **숨은 호출** — 근거 블록 · 활동 목록은 스트림의 도구 사건으로 만든다. 래퍼 안의 resolve 는 거기 안 보이고, 게이트웨이 감사에는 모델이 부르지 않은 호출이 남고, 자기검증은 바뀐 대상을 모른 채 결과를 대조한다.
- **시간** — 숨은 resolve(게이트웨이 한도 600초)와 본 호출(600초)이 한 도구 호출 안에 겹친다. 한 층이 그 합을 묶지 못하므로 따로 짧은 한도를 또 둬야 한다(7절).
- **대가 견주기** — 안 B 는 모델 왕복 한 번(대상 허브 resolve → 다시 부르기)이 는다. 그 대신 결정적이고 보이며, 기존 막이(유령 ID · 외부 응답자)와 같은 꼴이다. 규칙 ⑤ 가 프롬프트로는 안 지켜졌지만, 틀린 바로 그 순간의 도구 결과로 정확한 다음 호출을 주는 것은 다르다 — 유령 ID 막이가 그 길로 test_id 추측을 잡았다.

## 6. 같은 래퍼를 지나는 다른 행과의 차례

`_cap_tool.capped` 를 고치는 행은 HA-28(상태 조회를 코드가 기다린다) · HA-29(잡 · 쓰기는 확인 카드) · HA-30 이다. 고친 뒤의 차례는 이렇다.

1. invoke_tool 거부 도구(1889-1903) — 무조건 거부라 id 를 고치라고 할 까닭이 없다. 맨 앞 그대로.
2. 외부 응답자 · 반출 동의 거부(1906-1918) — 같은 까닭으로 그대로.
3. 유령 ID 막이(1919-1937) — 정수만 본다. HA-30 과 영역이 겹치지 않는다(정수 대 UUID 글).
4. **HA-30 `_cross_hub_id_msg`** — 출처 막이 둘을 붙여 둔다.
5. **HA-29 확인 카드** — HA-30 뒤여야 한다. 틀린 id 의 호출로 사람에게 확인을 받으면 확인 뒤에 HA-30 이 막아 사람의 확인이 헛것이 된다. id 를 먼저 고치게 하면 카드에는 바른 대상이 실린다. HA-29 가 확인 뒤 같은 호출을 다시 보내는 길을 두면 그 길도 HA-30 을 지난다(확인은 '사람이 시켰다' 이지 'id 가 맞다' 가 아니다). HA-29 를 `capped` 밖(그래프 단 확인)에 두면 카드를 띄우기 전에 `_cross_hub_id_msg(target, args)` 를 먼저 불러, 막힌 호출은 카드 없이 그 글을 돌려준다.
6. 챗 인자 기본값(1938-1953) — 기본값은 UUID 를 넣지 않아 HA-30 앞뒤 어디든 같다. 그대로 둔다.
7. **HA-28 기다리기**가 감싸는 호출(1954) — HA-30 의 검사는 첫 호출 전에 한 번 돈다. 다른 허브의 job_id 로는 기다리기를 시작하지 않는다. HA-28 이 `capped` 밖에서 조회를 되풀이하면 조회마다 검사가 다시 돌지만 값이 같아 결과도 같다.
8. 접기 → 자르기 → 인자 힌트 → `_learn_ids(body)` → **`_learn_hub_ids(_eff, body)`** → 앱 머리 · 되풀이 꼬리 — HA-28 이 LLM 에 넘기는 마지막 결과(끝났거나 상한에 닿은 결과)만 이 자리를 지나면 된다. 중간 조회 결과는 모델이 보지 않으므로 배우지 않아도 된다.

HA-28 · HA-29 가 `capped` 를 도우미 차례로 다시 짜더라도 HA-30 은 '부르기 전 한 줄(`_cross_hub_id_msg`) + 결과 쪽 한 줄(`_learn_hub_ids`)' 로 옮겨 붙이면 된다.

## 7. 시간 한도 층

| 층(안쪽부터) | 값(기본) | 근거 |
|---|---|---|
| 허브 MCP → 허브 백엔드 | GET 60초 · POST 120초 | StandardPlatform `mcp_server/server.py` `_get` · `_post`(0.4.52) |
| 게이트웨이 도구 호출 | `GATEWAY_CALL_TIMEOUT` 600초 · 전송 읽기 660초(+60) | gateway.py:188 · 210 |
| 에이전트 MCP 요청 | `MCP_CALL_TIMEOUT_S` 900초(env-kit 은 주석 기본) | app.py:129 · 포털 `infra/env-kits/agent-server.env:114` |
| 챗 스트림 침묵 | 에이전트가 `DELIB_HEARTBEAT_S` 15초마다 ping → 포털 `AGENT_CHAT_IDLE_TIMEOUT_S` 900초 | app.py:1188 · 1246(`_pinged_stream`) · 포털 `backend/app/config.py:313` |
| 챗 한 턴 | `AGENT_RECURSION_LIMIT` 80(연속 도구 왕복 약 39회) | app.py:2107 |

- 안쪽이 먼저 걸리는 차례(60/120 < 600 < 900, 침묵은 ping 이 되감는다)는 지금 지켜지고 있고 HA-30 은 이것을 바꾸지 않는다.
- HA-30(안 B)은 기다림이 없다. 부르기 전 검사는 인자 글에 정규식 한 번, 배우기는 결과 글(`TOOL_RESULT_MAX` 200,000자 이하)에 정규식 한 번과 `json.loads` 한 번이다(수 ms). 네트워크도 없다(맵은 캐시만, 어휘표는 stat 두 번). 그래서 새 한도도, 줄 세울 층도 없다.
- 막은 호출 하나는 연속 왕복 하나(80 단계 가운데 2)를 쓴다. 안내를 무시하고 같은 id 로 거듭 부르는 모델은 기존 재귀 상한에서 기존 문구(`tool_loop_limit`)로 끝난다 — 새 한도를 두지 않는다.
- 안 A 였다면 숨은 resolve(최대 600초)와 본 호출(600초)이 한 도구 호출에 겹쳐 모델이 보는 호출 하나가 1,200초까지 갈 수 있다. `MCP_CALL_TIMEOUT_S` 는 요청마다라 그 합을 묶지 못한다. 그래서 안 A 는 따로 짧은 안쪽 한도(예 30초)가 있어야 했다 — 고르지 않은 까닭의 하나다.

## 8. 시험(블랙박스 — 이 문서만 보고 쓸 수 있게)

### 8.1 꾸밈

- 새 시험 파일 `tests/test_request_1030_ha30.py`. 루트 `conftest.py` 가 코어 어휘표를 '없음' 으로 두므로 허브 표는 기본표(셋)다.
- 앱 맵은 `tests/test_request_1029.py` 의 `_cache(monkeypatch, mapping, labels)`(127행) 꼴로 앉힌다 — `_TOOLS_MAP_CACHE["map"]` · `_APPS_CACHE` 와 `_tools_map` · `_gw_apps` 를 함께 막는다(떠 있는 dev 게이트웨이에 묻지 않게).
- 맵 — `{"rootdesigndatahub_object_resolve": "rootdesigndatahub", "rootdesigndatahub_graph_neighbors": "rootdesigndatahub", "failuretrace_object_resolve": "failuretrace", "failuretrace_graph_neighbors": "failuretrace", "failuretrace_objects_list": "failuretrace", "failuretrace_search": "failuretrace", "caegroupdatahub_object_get": "caegroupdatahub", "search_voc": "signalforge", "invoke_tool": "_gateway"}`.
- 기록하는 도구 — `tests/test_request_1029.py` 의 `_tool_of`(120행)와 같은 꼴로, 코루틴이 받은 인자를 목록에 적고 정해 둔 글을 돌려준다. `a._prep_tool(StructuredTool(name=…, description="d", coroutine=call, args_schema={"type": "object", "properties": {}}), arg_defaults=a._CHAT_ARG_DEFAULTS, chat=True)` 로 싼다(사전 스키마라 넘긴 인자가 그대로 코루틴에 간다). ⚠ 동기 `@tool` 은 `_cap_tool` 이 감싸지 않으므로(1838-1840) 반드시 코루틴 도구로 쓴다.
- 턴 상태 — `tok = a._turn_hub_ids.set({})` · 끝에서 `a._turn_hub_ids.reset(tok)`(W-5 시험의 `_turn_tool_calls` 와 같은 꼴).
- 값 — `U_RD = "0b6f1c3e-6a51-4c1e-9f0e-1d2c3b4a5f60"`(정본 JNT-SLD-01), `U_FT = "7c2d9e41-3b8a-4f6d-a0c5-8e9f1a2b3c4d"`(FailureTrace 의 같은 key), `U_PART = "3a4b5c6d-7e8f-4a1b-8c2d-9e0f1a2b3c4d"`(정본 PRT-PCB), `U_USER = "9d8c7b6a-5f4e-4d3c-8b2a-1f0e9d8c7b6a"`(아무 결과에도 없음).
- 결과 글 — `RD_RESOLVE = {"match": "exact", "object": {"id": U_RD, "key": "JNT-SLD-01", "label": "솔더 접합 불량 + 크랙", "type_slug": "failure_mode", "aliases": [], "status": "active", "matched_by": "key", "hint": ""}, "candidates": [], "hint": "", "truncated": false}` · `FT_RESOLVE` 는 같은 꼴에 `U_FT` · `GRAPH_ERR = {"error": "[APP-GRAPH-0001] 객체를 찾을 수 없습니다."}` · `RD_GRAPH = {"focus": U_RD, "nodes": [{"id": U_RD, "key": "JNT-SLD-01", "label": "솔더 접합 불량 + 크랙", "type_slug": "failure_mode"}, {"id": U_PART, "key": "PRT-PCB", "label": "PCB", "type_slug": "part"}], "edges": [{"id": "e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a5b", "relation": "occurs_in_part", "src": U_RD, "dst": U_PART}], "truncated": false}`(모두 JSON 글로).

### 8.2 단위 시험(입력 → 기대)

| # | 입력 | 기대 |
|---|---|---|
| T1 OT-07 | 턴 상태 `{}` · `rootdesigndatahub_object_resolve` 가 `RD_RESOLVE` 를 돌려준 뒤 `failuretrace_graph_neighbors` 를 `{"object_id": U_RD}` 로 | failuretrace 도구 코루틴이 **불리지 않는다**. 결과는 `✖ 도구 failuretrace_graph_neighbors 호출 실패(보내지 않았다):` 로 시작하고 `object_id=0b6f1c3e-6a51-4c1e-9f0e-1d2c3b4a5f60 는 다른 허브의 id 다` · `자주검증 Datahub(rootdesign) 의 rootdesigndatahub_object_resolve 결과` · `key 「JNT-SLD-01」 · type_slug failure_mode` · `failuretrace_object_resolve(type_slug="failure_mode", name="JNT-SLD-01")` · `failuretrace_search(q="JNT-SLD-01")` · `FailureTrace 에서는 이 id 로 찾지 못한다` 를 담는다. `a._result_ok(결과)` 는 거짓, `a._PHANTOM_ID_MARK` 는 없다. 앱 머리('[이 결과는')가 없다. |
| T2 제 허브 | T1 뒤 `rootdesigndatahub_graph_neighbors({"object_id": U_RD})` | 불린다(인자 그대로) · 결과의 끝이 그 도구의 글이다. |
| T3 다시 푼 id | T1 뒤 `failuretrace_object_resolve({"type_slug": "failure_mode", "name": "JNT-SLD-01"})` 가 `FT_RESOLVE` 를 돌려준 다음 `failuretrace_graph_neighbors({"object_id": U_FT})` | 둘 다 불린다. 상태의 `U_FT` 는 `apps == {"failuretrace"}` 다. |
| T4 공유 id | T1 의 resolve 뒤 같은 인자의 `failuretrace_object_resolve` 가 `U_RD` 도 든 글(예 `FT_RESOLVE` 의 `object` 에 `"external_ids": {"core": U_RD}` 를 더한 것)을 돌려준 다음 `failuretrace_graph_neighbors({"object_id": U_RD})` | 불린다 — 상태의 `U_RD` 는 `apps == {"rootdesigndatahub", "failuretrace"}`. |
| T5 경유 | T1 의 resolve 뒤 `invoke_tool` 을 `{"name": "failuretrace_graph_neighbors", "arguments": {"object_id": U_RD}}` 로, 또 `arguments` 를 JSON 글 `'{"object_id": "<U_RD>"}'` 로 | 둘 다 불리지 않고 같은 글이다(대상 이름은 안쪽 이름). |
| T6 경유로 배우기 | 상태 `{}` 에서 `invoke_tool({"name": "rootdesigndatahub_object_resolve", "arguments": {…}})` 가 `RD_RESOLVE` 를 돌려준 뒤 `failuretrace_graph_neighbors({"object_id": U_RD})` | 막힌다 — 경유 결과도 안쪽 도구의 허브로 배운다. 상태의 `U_RD["tool"] == "rootdesigndatahub_object_resolve"`. |
| T7 숨은 자리 | T1 의 resolve 뒤 `failuretrace_objects_list({"type_slug": "pd_defect", "conditions": [{"field": "failure_mode", "op": "in", "value": f"{U_RD.upper()}\|{U_USER}"}]})` | 불리지 않는다. 글에 `conditions=0b6f1c3e-…` 가 있고(대문자로 줘도 잡는다) `U_USER` 는 글에 없다(모르는 id 는 막지 않는다). |
| T8 허브가 아닌 대상 | T1 의 resolve 뒤 `search_voc({"q": U_RD})` | 불린다. |
| T9 허브가 아닌 결과 | 상태 `{}` 에서 `search_voc` 가 `U_RD` 가 든 글을 돌려준 뒤 `failuretrace_graph_neighbors({"object_id": U_RD})` | 불린다 — 허브 결과만 배운다(상태에 `U_RD` 없음). |
| T10 오류 결과 | 상태 `{}` · `rootdesigndatahub_object_resolve` 가 `RD_RESOLVE` 를 낸 뒤 `failuretrace_object_resolve({"type_slug": "failure_mode", "name": "JNT-SLD-01"})` 가 `{"error": "[APP-OBJECTS-0001] 객체를 찾을 수 없습니다: <U_RD>"}` 를 돌려주고 다시 `failuretrace_graph_neighbors({"object_id": U_RD})` | 막힌다 — 오류 글은 배우지 않아 `U_RD["apps"] == {"rootdesigndatahub"}` 그대로다. |
| T11 모르는 id | 상태 `{}`(또는 T1 의 resolve 뒤) `failuretrace_graph_neighbors({"object_id": U_USER})` | 불린다. |
| T12 턴 밖 | 턴 상태를 걸지 않고(None) T1 의 두 호출 | 둘 다 불리고 아무것도 배우지 않는다(끈 손잡이는 8.3 T21 이 본다). |
| T13 맵이 빈 때 | `_cache(monkeypatch, {}, {})` 로 T1 | 이름 접두로 가려 똑같이 막는다. `a._hub_of("caegroupdatahub_object_get") == "caegroupdatahub"` · `a._hub_of("graph_neighbors") == ""` · `a._hub_tool("caegroupdatahub", "object_resolve") == "caegroupdatahub_object_resolve"`. |
| T14 맵 판정 | 맵 `{"object_resolve": "rootdesigndatahub", "search_voc": "signalforge"}` | `a._hub_of("object_resolve") == "rootdesigndatahub"`(허브 하나 박스의 맨 이름) · `a._hub_of("search_voc") == ""`. |
| T15 key 없는 id | `rootdesigndatahub_graph_neighbors` 결과가 간선 id 만 든 글(`{"edges": [{"id": X, "src": U_RD, "dst": U_PART}]}` — 노드 없음)일 때 `failuretrace_graph_neighbors({"object_id": U_PART})` | 막힌다. 글에 `key 를 결과에서 읽지 못했다` 와 `failuretrace_objects_resolve_many` 가 있고 `name="` 은 없다. |
| T16 관련 객체 꼴 | `rootdesigndatahub_object_get` 결과가 `{"object": {…}, "related": [{"relation_id": R, "relation": "occurs_in_part", "object_id": U_PART, "object_key": "PRT-PCB", "object_label": "PCB", "object_type_slug": "part"}]}` 일 때 `failuretrace_graph_neighbors({"object_id": U_PART})` | 막히고 `failuretrace_object_resolve(type_slug="part", name="PRT-PCB")` 가 글에 있다. |
| T17 접은 결과 | `RD_GRAPH` 를 노드 600개 · 간선 없음으로 키워(라벨을 길게 — 글이 `_HUB_BIG_CHARS` 60,000자를 넘게) `rootdesigndatahub_graph_neighbors` 가 돌려준 뒤 첫 50개 안의 노드 id 로 `failuretrace_graph_neighbors` | 막히고 그 노드의 key 가 글에 있다(접기 머리 줄을 떼고 이름표를 읽는다). 접혀 빠진 51번째 이후 노드 id 는 상태에 없다(모델이 보지 않은 id). |
| T18 여럿 | 정본 결과(`rootdesigndatahub_graph_neighbors` — key 가 있는 노드 다섯, id V1 ~ V5)를 배운 뒤 `failuretrace_objects_list({"type_slug": "pd_defect", "conditions": [{"field": "failure_mode", "op": "in", "value": "V1\|V2\|V3\|V4\|V5"}]})` | 불리지 않는다. 글에 `는 다른 허브의 id 다` 가 3번 · `그 밖에 2개도 다른 허브의 id 다.` · `failuretrace_objects_resolve_many` 가 있고, 세 줄의 칸은 모두 `conditions` 다. |
| T19 상한 | `monkeypatch.setattr(a, "_HUB_IDS_MAX", 2)` · 상태 `{}` 에서 UUID 셋이 든 정본 결과 → 셋째는 상태에 없다. 다음에 `failuretrace` 결과가 첫째 id 를 실으면 | 첫째 id 의 `apps` 에 `failuretrace` 가 더해진다(상한이 있어도 이미 있는 id 에는 더한다). |

표 안의 `\|` 는 `|` 다 — 마크다운 표의 칸 나눔을 피하려고 적은 것이다.

어휘표 시험은 따로 둔다.

- 어휘표가 없을 때(conftest 기본) `a._hub_apps()` 의 키는 `{"rootdesigndatahub", "failuretrace", "caegroupdatahub"}` 다.
- `monkeypatch.setattr(a, "CORE_VOCAB_PATH", _REAL)`(test_request_1029 의 `_REAL`)이면 같은 셋이고 `stepforge-prod` · `dynaforge-prod` 는 없다. 라벨은 어휘표의 것이다(`자주검증 Datahub(rootdesign)` · `FailureTrace` · `CAE 그룹 Datahub`).
- 임시 어휘표(canonical `hub` · apps `{"x": {"role": "sibling", "label": "X허브"}}`)면 `{"hub", "x"}` 다. `a._core_vocab_health()` 의 꼴은 고치기 전과 같다.

### 8.3 실제 경로 시험(한 턴)

`tests/fakes/llm_server.py` 는 글만 내고 도구 호출을 내지 못한다. 그래서 `tests/test_chat_loop_fit.py` 의 꾸밈을 쓴다 — `_agent(monkeypatch, llm, tools)`(96행 — 앱이 실제로 만드는 길 `_agent_for`, 게이트웨이 클라이언트만 스텁)와 `_LoopLLM`(229행) 처럼 받은 `ToolMessage` 수로 차례를 아는 대본 모델(`bind_tools` 는 자기 자신, `_stream` 도 같은 답). 창은 `_win` 픽스처(33행)처럼 `app._ctx_cache["n"]` 을 크게 둔다. `_agent` 를 부르기 **전에** `_cache(...)` 를 건다.

| # | 대본 | 기대 |
|---|---|---|
| T20 OT-07 한 턴 | ① `rootdesigndatahub_object_resolve(type_slug="failure_mode", name="JNT-SLD-01")` ② `failuretrace_graph_neighbors(object_id=U_RD)` ③ `failuretrace_object_resolve(type_slug="failure_mode", name="JNT-SLD-01")` ④ `failuretrace_graph_neighbors(object_id=U_FT)` ⑤ 답 글. 에이전트를 `_agent_for` 로 바꿔 끼우고 `app._agent_stream(app.app, ChatRequest(message="JNT-SLD-01 의 불량 기록 연결을 FailureTrace 에서 보여줘", groups=["portal-admin"], history=[]))` 를 끝까지 읽는다. | failuretrace graph 도구의 기록이 `[{"object_id": U_FT}]` 하나다. 모델의 셋째 호출이 받은 마지막 `ToolMessage` 에 `는 다른 허브의 id 다` 와 `failuretrace_object_resolve(type_slug="failure_mode", name="JNT-SLD-01")` 가 있다. SSE `status` 의 '도구 완료: failuretrace_graph_neighbors' 는 두 번이고 첫째 `ok` 는 거짓 · 둘째는 참이다. `result` 사건의 글에 ⑤ 의 답이 있다. `error` 사건은 없다. |
| T21 끄면 종전 | T20 과 같되 `monkeypatch.setattr(a, "_XHUB_GATE", False)` 와 ② 의 도구가 `GRAPH_ERR` 를 돌려주게. 도구 코루틴은 불릴 때 `a._turn_hub_ids.get()` 도 적는다. | ② 가 불린다(기록에 `U_RD`). 모델이 받은 둘째 `ToolMessage` 는 허브의 `[APP-GRAPH-0001]` 글이다. 도구가 적은 턴 상태는 모두 None 이다. |
| T22 턴마다 새 상태 | T20 뒤 같은 에이전트로 둘째 턴을 돌리고 대본이 첫 호출로 `failuretrace_graph_neighbors(object_id=U_RD)` 를 낸다 | 불린다 — 앞 턴에 배운 것은 다음 턴에 남지 않는다(요청 행 범위 '이번 턴'). |

### 8.4 HA-29 합친 뒤의 맞물림 시험(합치기 단계)

- HA-29 목록의 쓰기 도구(예 `failuretrace_relation_add`)에 정본 id 를 `dst_object_id` 로 실으면 확인 카드가 아니라 HA-30 글이 온다. 같은 호출을 대상 허브 id 로 고치면 그때 확인 카드가 온다.

### 8.5 cae00 재시험(사람 몫 — 요청서 '다시 볼 시험' OT-07)

- OT-07 질문을 웹 챗으로 다시 보낸다.
- 활동 목록에 `failuretrace_graph_neighbors` 실패(보내지 않음) → `failuretrace_object_resolve` → `failuretrace_graph_neighbors` 성공 차례가 보이거나, 모델이 처음부터 FailureTrace 에서 key 로 푼다.
- 에이전트 서버 로그에 `[gate] … 다른 허브 id` 줄이 막은 수만큼 있다.
- 게이트웨이 감사에 그 턴의 `failuretrace_graph_neighbors` 가 `APP-GRAPH-0001` 로 끝난 줄이 없다.

## 9. 위험과 열린 질문

### 9.1 위험

| # | 위험 | 대응 |
|---|---|---|
| R1 | 두 허브가 같은 UUID 를 쓰는 복제 설치면, 대상 허브에서 아직 안 본 정본 id 를 막는다. | 막은 글대로 대상 허브에서 key 로 풀면 같은 id 가 돌아와 대상 허브 결과로 배우고, 다음 호출이 지난다 — 왕복 하나로 스스로 풀린다. 잦으면 `CHAT_XHUB_ID_GATE=0`. |
| R2 | 다른 허브 결과의 글(본문 · 메모)이 다른 설치의 id 를 언급하면 그 허브에서도 '본 id' 가 되어 지난다. | 지금과 같은 오류 한 번이다. 이름표처럼 'id 자리' 만 배우게 좁히면 막을 수 있지만 배포판 응답 꼴에 묶인다 — 넣지 않는다. 이 줄은 놓치는 쪽만이다 — 같은 글이 막는 쪽으로 드는 길은 R9 다. |
| R3 | 형제 허브가 그 코어 타입을 다른 slug 로 받았으면 글이 준 resolve 가 실패한다. | 글에 search 대안을 싣는다. |
| R4 | 맵 캐시가 비었고 허브 도구가 맨 이름(허브 하나 박스)이면 허브로 못 가린다. | 그 박스에는 건널 다른 허브가 없다. 맵이 차면 가린다(fail-open). |
| R5 | 배포판(0.4.52 보다 새것)의 응답 꼴이 바뀌면 이름표(key)를 잃을 수 있다. | 막기는 UUID 꼴로 하므로 남는다. 글이 'key 를 결과에서 읽지 못했다' 로 바뀔 뿐이다. cae00 재시험에서 key 가 실리는지 본다. |
| R6 | 쓰기 도구의 글 칸에 다른 허브 id 를 '값' 으로 적으려는 호출도 막힌다. | 허브 설계상 설치를 건너는 가리킴은 key 다. 예외를 두지 않는다. |
| R7 | HA-29 를 `capped` 밖(그래프 단)에 두면 확인 카드가 HA-30 보다 먼저 뜬다. | 6절 5 — 카드 앞에서 `_cross_hub_id_msg` 를 먼저 부른다. |
| R8 | 성능 — 결과마다 정규식과 JSON 읽기가 한 번 는다. | 200,000자 이하에서 수 ms 다. 허브가 아닌 도구 결과는 `_hub_of` 에서 끝난다. |
| R9 | (10-31 반대 검토) 다른 허브 결과의 글에만 적힌 UUID 도 그 허브의 id 로 배운다 — 본문 · 메모, StandardPlatform 0.4.66(`418af00`)부터는 search 가 싣는 게시판 글의 `posts[].snippet`(본문에서 q 앞뒤 40자)도 그렇다. 그 UUID 가 다른 허브의 객체면, 그 id 로 진짜 주인 허브를 부르는 호출(그래프 · 검색 모두)이 그 턴 내내 막히고, 막은 글의 안내('key 를 모르는 id 는 앞 허브의 결과에서 그 객체의 key 를 찾는다')도 거짓이 된다 — 앞 허브의 결과(글)에는 key 가 없다. R2 의 반대쪽이고, 반대 검토 2차(`2aa076e`)가 메아리 id 에서 결함으로 닫은 것과 같은 꼴이다(dev 사본에서 재현). | **사용자 결정 대기(10-31).** ① 받아들인다 — 이 줄이 받아들인 위험이 되고, 피해 갈 손잡이는 `CHAT_XHUB_ID_GATE=0` 이다. ② 좁게 막는다 — search 결과의 `posts[]` 안(title · snippet)에서만 나온 UUID 는 배우지 않는다(이름표가 있는 id 자리에도 나온 UUID 와 글 id `posts[].id` 는 그대로 배운다). 배포판 꼴에 묶이지만 칸 이름이 바뀌면 지금 동작으로 돌아갈 뿐이다. 고르면 이 칸을 고치고, ②면 '실어 보내지 않은 다른 허브 UUID 가 글 snippet 에만 있는' 시험을 `RV2_ECHO` 옆에 더한다(고치기 전 판에서 붉은지 본다). |

### 9.2 열린 질문(권고 답 포함)

| # | 질문 | 권고 |
|---|---|---|
| Q1 | 코드가 대신 key 로 다시 풀어 바꿔 보낼까(요청의 첫째 안)? | 아니다 — 돌려주기(안 B). 5절. |
| Q2 | 앞 턴 근거(이력 evidence)의 id 도 배울까? | 이번에는 안 한다. 요청 행의 범위가 '이번 턴' 이고 OT-07 은 한 턴 안이다. 턴을 건너는 실측이 나오면 `_agent_stream_turn` 의 같은 자리에서 `req.history` 의 어시스턴트 항목 `evidence[{tool, result}]` 마다 `_learn_hub_ids(tool, result)` 를 부르면 된다(4줄 — `_hist_evidence` 와 같은 꼴). |
| Q3 | 사람이 친 id 를 면제할까? | 면제하지 않는다(4절). 이 턴 허브 결과에 없는 사람의 id 는 어차피 지난다. |
| Q4 | 공유 id(두 허브 결과에 다 나온 id)는? | 막지 않는다(4절 · R1). |
| Q5 | 루틴(`routine._step_call`) · 심의 좌석에도 걸까? | 이번 행은 챗만이다. 루틴 단계는 key 를 넘기도록 짜였다(R3 봉투). R5 실주행에서 보이면 같은 두 함수를 `_step_call` 에 붙인다 — 배우기는 백엔드 키(`bk`)를 바로 쓴다. 심의는 문맥 변수를 걸지 않아 지금처럼 꺼진 채다. |
| Q6 | 시험 사본(stepforge-prod · dynaforge-prod)이나 다른 앱으로 넓힐까? | 넓히지 않는다. 그 앱들의 id 꼴과 공유 여부를 모른다. 허브가 늘면 어휘표 덧씌우기에 role `sibling` 으로 더한다. |
| Q7 | 같은 다른-허브 id 를 거듭 보내면 글을 세게 바꿀까? | 지금은 같은 글로 막는다(결정적). 재귀 상한이 끝을 지킨다. cae00 재시험에서 되풀이가 보이면 둘째부터 '이미 막혔다 — 지금까지의 결과로 답하라' 를 붙인다. |
| Q8 | `/health` 에 막은 수를 실을까? | 로그 한 줄만 둔다(유령 ID 막이와 같다). 재시험 OT-07 은 에이전트 로그의 `[gate] … 다른 허브 id` 줄로 본다. 필요해지면 HA-34 의 `hub_fold` 옆에 `hub_xid{blocked}` 를 둔다. |
| Q9 | 개인 Claude(게이트웨이 MCP 직접 연결)는 이 관문이 없다 — 허브 쪽 오류 문구도 고칠까? | 고치도록 청한다. 허브의 '객체를 찾을 수 없습니다'(APP-GRAPH-0001 · object_get 의 찾지 못함)에 '다른 설치의 id 일 수 있다 — key 로 object_resolve' 한 줄을 DP-14(조건 주소 예)와 같은 묶음으로 보낸다(`outbound.md` — 사람이 보냄). 이 행을 막지는 않는다. |
| Q10 | 근거 블록이 막힌 호출도 '조회한 것' 으로 싣는다(유령 ID 막이와 같은 지금 동작). | 이 행에서는 그대로 둔다. 근거 블록이 실패한 호출을 가르는 일은 두 막이에 함께 걸리는 따로 된 일이다. |

## 10. 요청 행과 코드가 어긋나는 곳

1. **'object_id' 만이 아니다.** 허브의 id 는 여러 칸(`object_id` · `dst_object_id` · `into` · `parent` · `ids` · `*_id`)과 깊은 자리(`conditions[].value` · resolve 의 `name` · search 의 `q`)에 실린다. 숨은 자리의 다른 허브 id 는 오류가 아니라 0건으로 돌아와 '없다' 로 읽힌다. 설계는 칸 이름이 아니라 인자 전체의 UUID 꼴로 본다(2.4).
2. **'코드가 key 로 그 허브에서 다시 resolve' 는 늘 되지 않는다.** key · type 을 모르는 id(간선 끝 · 참조 칸 값 · 잘린 글), 대상 허브의 다른 type slug, candidates(규칙 ① — 고르지 않는다), none, 쓰기 도구의 말없는 대상 바꾸기가 걸린다. 숨은 호출은 근거 블록 · 활동 · 자기검증에 보이지 않고 게이트웨이 감사에만 남는다(5절).
3. **'그 id 를 낸 도구의 앱' 은 노출 이름만으로는 모자란다.** 세 허브가 같은 도구 이름이라 게이트웨이 백엔드 키로 가려야 하고(`/tools-map` 캐시), invoke_tool 은 안쪽 이름으로, 맵에 없는 별칭은 접두로 가린다. 그리고 **오류 결과는 빼야** 한다 — 오류 글이 받은 id 를 되풀이하면 그 허브 것으로 잘못 배운다(3.3 의 3).
4. **'허브 도구' 의 범위가 코드 어디에도 없다.** 어휘표의 role(canonical · sibling)로 정하고, role staging(시험 사본)은 넣지 않는다(3.2).
5. **기존 유령 ID 막이가 못 잡은 까닭이 근거에 없다.** `_phantom_id_arg`(1606)는 정수 인자만 봐서 UUID 문자열 id 에는 처음부터 닿지 않았다. HA-30 은 그 빈자리(UUID · 앱 출처)를 메운다.
6. 행에는 코드 줄이 없다. 규칙 ⑤ 는 cae00 `969e723` 의 `_core_rules_text` 와 `_CORE_RULES_DEFAULT` 에 있고(dev 303 · 193), 지키는 코드는 없다.
7. dev 게이트웨이에는 허브가 붙어 있지 않아(10-30 `/tools-map` 백엔드 17개) dev 에서 OT-07 을 실물로 다시 볼 수 없다. 시험은 가짜 도구로 잠그고, 실물은 cae00 재시험(OT-07 — 사람 몫, `server-setup.md`)으로 본다.

## 11. 고칠 파일

- `HWAXAgentServer/app.py` — 상수 · 문맥 변수 · 함수(ID 출처 절), `_core_vocab.build` 의 `hubs`, `capped` 두 자리, `_agent_stream_turn` 한 줄.
- `HWAXAgentServer/tests/test_request_1030_ha30.py` — 8절의 시험(새 파일).
- `HWAXAgentServer/README.md` — 챗 막이 절에 다른 허브 id 막이와 `CHAT_XHUB_ID_GATE` 한 단락.
- `HWAXPortal/infra/env-kits/agent-server.env` — `# CHAT_XHUB_ID_GATE=1` 주석 한 줄(설명 포함).
- `HWAXPortal/docs/request-1030/` — 체크리스트 HA-30 체크 · 판단 기록(Q1 · Q3 · Q2 결정) · `server-setup.md` 의 OT-07 재시험 줄, 합칠 때 `backend/config/changelog.yaml` 업데이트 이력(분류 '기술' 포함).
