# SP(StandardPlatform) 최신판 따라가기

사용자 지시 — 10-31 「키트를 쓰는 플랫폼은 늘 SP 최신판에 맞춘다」, 11-03 「standard platform 에 연계되는 것은 모두 최신화도 해야 한다」.
판단 기록은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md), cae00 사람 몫은 [server-setup.md](server-setup.md),
SP 쪽에 건넬 글은 [sp-annotations-request.md](sp-annotations-request.md)다. 날짜는 KST.

## 1. SP 에 무엇이 이어져 있나

| 갈래 | 무엇 | 맞추는 곳 |
|---|---|---|
| 키트 소비처 | StepForge `core/sp_core.py` · DocForge SP 거울 · SignalForge `plm_mirror.py` · KooRemapper | 각 리포 세션 — 포털 세션이 맞추기를 보낸다 |
| SP 설치(허브 셋) | cae00 의 정본 허브(rootdesign) · FailureTrace · CAE 그룹 데이터 허브 — 같은 SP 를 셋으로 띄운 것 | cae00 사람([server-setup.md](server-setup.md)) |
| 게이트웨이 | 쓰기 판정(`_tool_is_write` — 앱 표지 → 이름 낱말) · 읽기 목록 · 검색 열쇠 | HWAXMcpGateway |
| 포털 | 허브 운영자(`he-data-coreontology`)의 writes · confirm — 웹 챗 확인 관문(에이전트 서버 HA-29)이 이 목록을 읽는다 | `infra/personas/he-team.json` |
| 응답 꼴에 기대는 곳 | 에이전트 서버 · 포털이 SP 답의 꼴(SLUG_RE · '없다' 메아리)을 읽는다 — 키트가 아니다 | 판마다 꼴이 바뀌었는지만 본다 |

ReportArchive 는 뺀다 — 사용자가 다루는 리포가 아니다(10-31 지시).

## 2. 판이 바뀔 때마다

1. `git ls-remote` 로 SP HEAD 를 보고, 바뀌었으면 그 판의 `KIT_VERSION` · `CHANGES.md` · `UPGRADE.md` · MCP 도구 목록(`mcp_server/server.py` 의 `@tool()`)을 읽는다.
2. 키트가 바뀌었으면 소비처 세션 넷에 맞추기를 보낸다(층 1 `sp_core_pull.py` · 층 2 `01-AI-GUIDE` · 시험장 8단계).
3. MCP 도구가 늘거나 바뀌었으면 게이트웨이 쓰기 판정으로 새 도구를 가른다. 바꿀 수 있는 도구는 허브 운영자의 writes · confirm 에 **도구마다** `needs_tool` 칸으로
   붙인다 — 필수 칸에 두면 허브가 옛 판인 박스에서 동기화가 통째로 멈춘다(SL-2).
4. cae00 허브를 새 판으로 올리는 것은 사람 몫이다([server-setup.md](server-setup.md)). 올린 뒤 운영자 미리보기에 '목록 밖 쓰기' 줄이 없는지 본다.

## 3. 0.4.72 판(11-03)

- SP `ab41cff` = 0.4.72, 키트 `2026-11-03`. 키트 층 1(`sp_core_pull.py`)은 판 표시만 바뀌었고, 층 2(`01-AI-GUIDE`)에 받은 선을 받는 쪽 플랫폼에 넣는 규칙
  (§6.2 · §8.1 · §9 · §2 · §5.2 — 유효 기간 · 수량 칸 · 계보 원천)이 더해졌다.
- MCP — 0.4.67(10-31) 뒤 새 도구 일곱(`object_explode` · `object_lineage` · `lineage_repin` · `graph_reach` · `relation_propose` · `relation_proposals` ·
  `relation_proposal_decide`), `object_get`(`as_of` · `all_periods`) · `object_rollup`(`as_of`)에 기준일 인자가 붙었다(기본값이 있어 옛 호출은 그대로다).
  도구는 모두 110개다.
- 포털 몫 — 게이트웨이가 `lineage_repin` 을 쓰기로 읽게(SL-1), 운영자 목록에 바꾸는 도구 마흔둘(SL-2), 미리보기 대조를 관문과 같은 셈으로(SL-3), SP 에 표지
  요청(SL-4). 소비처는 [checklist.md](checklist.md) 1절.
