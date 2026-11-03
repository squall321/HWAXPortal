# StandardPlatform 에 — MCP 도구마다 읽기 · 쓰기 표지를 달아 주세요(요청)

보내는 쪽 — HWAX 포털(MCP 게이트웨이 · 웹 챗 확인 관문을 맡은 쪽). 이 글을 SP 쪽에 건네는 것은 사용자다(사용자 결정 11-04, [context-notes.md](context-notes.md) SL-4).
대조 판 — SP `ab41cff`(0.4.72)의 `mcp_server/server.py`. 고친 날 2026-11-04(KST).

## 1. 무엇을

MCP 도구 표지(`ToolAnnotations`)를 도구마다 단다.

- 읽기만 하는 도구 — `readOnlyHint=True`.
- 바꿀 수 있는 도구(미리 보기가 기본인 것 · 읽기 모드가 있는 것도) — `readOnlyHint=False`.
- 그 가운데 지우기 · 되돌리기 · 덮어쓰기 · 멈추기 — 덧붙여 `destructiveHint=True`. 지금의 `DESTRUCTIVE_TOOLS` 와 같은 뜻이다.

`mcp>=1.27` 의 FastMCP 는 `mcp.tool(annotations=ToolAnnotations(...))` 를 받는다. 지금 `tool()` 감싸개가 `mcp.tool()` 을 인자 없이 부르므로,
감싸개가 표지를 인자로 받거나 이름 → 표지 표 하나를 `DESTRUCTIVE_TOOLS` 곁에 두고 감싸개가 고르면 된다. 새 도구가 표지 없이 들어오면 시험이 붉게 하면
빠짐이 없다(감싸개가 측정 · 관리자 확인을 한 자리에서 거는 것과 같은 까닭).

## 2. 까닭

- 받는 쪽은 표지를 먼저 본다. 표지가 없으면 이름의 낱말로 짐작하는데, 바꾸는 도구 49개 가운데 14개는 이름에 쓰기 낱말이 없어 읽기로 읽힌다(아래 표의
  '이름으로는 읽기로 읽힘'). 받는 쪽에서는 검색 순위(쓰기 도구를 내리는 보정)와 운영자 점검의 '목록 밖 쓰기' 알림이 그 판정을 쓴다.
- `lineage_repin` 은 설명에 '되돌릴 길이 없다' 고 적혀 있는데 이름으로는 쓰기인지 알 수 없어, 받는 쪽이 낱말(repin)을 더해야 했다(11-03).
- 같은 SP 를 셋 띄운 설치(정본 · 불량 추적 · CAE 그룹 데이터 허브)가 한 에이전트에 붙어 있다. 표지가 판과 함께 오면 판이 바뀔 때마다 받는 쪽을 고치지 않아도 맞는다.
- 받는 쪽의 자동 실행(분석 루틴 단계 · 심의 좌석의 자유 조회)은 읽기로 확인된 도구만 쓴다. 지금은 읽기 60개 가운데 이름으로 확인되는 23개만 쓰이고
  `object_resolve` · `graph_path` · `object_lineage` 같은 것은 막혀 있다 — `readOnlyHint=True` 가 오면 저절로 열린다.

## 3. 바꿀 수 있는 도구 49개 — 제안 표지

`destructiveHint` 는 지금의 `DESTRUCTIVE_TOOLS` 에 `lineage_repin` 하나를 더한 것이다(4절 물음).

| 도구 | readOnlyHint | destructiveHint | 비고 |
|---|---|---|---|
| `platform_profile_update` | False |  |  |
| `ontology_import` | False |  |  |
| `ontology_delete` | False | True |  |
| `ontology_retype` | False | True | 이름으로는 읽기로 읽힘 |
| `ontology_rename_option` | False | True |  |
| `ontology_promote` | False |  | 이름으로는 읽기로 읽힘 |
| `ontology_restore` | False | True |  |
| `aliases_review` | False |  | 이름으로는 읽기로 읽힘 |
| `alias_candidate_apply` | False |  |  |
| `review_decide` | False | True |  |
| `lineage_repin` | False | True | DESTRUCTIVE_TOOLS 밖 — 4절 물음 |
| `bulk_edit` | False | True | 이름으로는 읽기로 읽힘 |
| `bulk_edit_undo` | False | True | 이름으로는 읽기로 읽힘 |
| `object_create` | False |  |  |
| `object_update` | False |  |  |
| `objects_delete` | False | True |  |
| `object_restore` | False | True |  |
| `object_merge` | False | True |  |
| `attachment_upload_prepare` | False |  |  |
| `attachment_remove` | False | True |  |
| `objects_import` | False |  |  |
| `bundle_import` | False |  |  |
| `bundle_undo` | False | True | 이름으로는 읽기로 읽힘 |
| `relation_add` | False |  |  |
| `relation_propose` | False |  |  |
| `relation_proposal_decide` | False |  |  |
| `relation_update` | False |  |  |
| `relation_remove` | False | True |  |
| `relations_import` | False |  |  |
| `job_apply` | False | True |  |
| `job_cancel` | False | True |  |
| `filestore_gc` | False | True | 이름으로는 읽기로 읽힘 |
| `datasource_sync` | False |  | 이름으로는 읽기로 읽힘 |
| `insight_manage` | False |  | 이름으로는 읽기로 읽힘 |
| `metric_define` | False |  | 이름으로는 읽기로 읽힘 |
| `metric_recompute` | False |  |  |
| `metric_home` | False |  | 이름으로는 읽기로 읽힘 |
| `metric_alert_save` | False |  |  |
| `config_delete` | False | True |  |
| `datasource_save` | False |  |  |
| `view_save` | False |  |  |
| `object_watch` | False |  | 이름으로는 읽기로 읽힘 |
| `object_years` | False |  | 이름으로는 읽기로 읽힘 |
| `review_undo` | False | True | 이름으로는 읽기로 읽힘 |
| `jobs_purge` | False | True |  |
| `export_start` | False |  |  |
| `slide_template_save` | False |  |  |
| `slide_create` | False |  |  |
| `slide_update` | False |  |  |

`extension_call` 은 읽기(GET)와 쓰기(DELETE 등)를 함께 한다 — `readOnlyHint=False` · `destructiveHint=True`(지금 `DESTRUCTIVE_TOOLS` 에 있다). 읽기만 하는 확장
자리는 나중에 따로 떼면 받는 쪽이 조회마다 확인을 묻지 않아도 된다(급하지 않다).

## 4. 물음 하나

`lineage_repin` 은 `DESTRUCTIVE_TOOLS`(MCP 로는 시스템 관리자만) 밖이다. 설명이 '이 객체를 고칠 수 있는 사람만' 이라 의도로 읽히지만, 옮긴 고정은 이 도구로
되돌릴 길이 없다고 적혀 있다. 관리자만으로 두지 않은 것이 의도인지 알려 달라 — 받는 쪽(웹 챗)은 어느 쪽이든 사람의 확인을 받고 부른다.

## 5. 읽기만 하는 도구 60개 — `readOnlyHint=True`

`get_guide` · `whoami` · `platform_profile` · `search` · `ontology_schema` · `table_infer` · `table_build` · `objects_list` · `object_resolve` · `objects_resolve_many` · `aliases_pending` · `alias_candidates` · `review_list` · `objects_summary` · `object_fields` · `objects_similar` · `object_get` · `object_history` · `object_rollup` · `object_explode` · `object_lineage` · `object_references` · `object_tree` · `graph_neighbors` · `graph_reach` · `graph_path` · `graph_overview` · `audit_recent` · `quality_report` · `fill_priorities` · `server_maintenance` · `notifications` · `bundle_runs` · `relation_proposals` · `job_status` · `jobs_list` · `datasources_list` · `datasource_runs` · `datasource_preview` · `rdf_schema` · `rdf_query` · `extensions_schema` · `metric_list` · `metric_query` · `metric_analyze` · `insights` · `metric_alerts` · `metric_runs` · `core_status` · `workspaces` · `views` · `webhooks` · `notices` · `board` · `review_history` · `server_status` · `slide_templates` · `slides_list` · `slide_get` · `slide_candidates`
