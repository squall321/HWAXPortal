# 09 MX 백서 — 10-30 요청에서 할 일

- **받는 곳** — 세션 `mxwhitepaper-26`(MXWhitePaper 리포).
- **어떻게 갔나** — 10-30 포털 세션 `hwaxportal-a5` 가 두 행을 정본 글 그대로 보냈고, 'HA-08 이 '…열리지 않았습니다' 도 받는다 — 문구는 그대로 둬도 된다' 를 덧붙였다([`../outbound.md`](../outbound.md) 1절). 이 시트를 맡을 때 상태는 '답 기다림' 이었다. 대조하는 동안 두 행이 커밋되어 올라갔고(`bb0a6a1` 17:51 KST · `bd2e79b` 17:52 KST), 답이 `../outbound.md` 답 칸에 '10-30 끝' 으로 옮겨졌다(포털 `bf5cd94`, 17:55 KST).
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 의 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)' › 'MX 백서(MXWhitePaper `f242254`)' 표. 맞물린 행은 같은 끝 절 '에이전트 서버' 표의 HA-08(다시)와 5절 '우리 몫' 의 OB-64 · OB-65 다.
- **cae00 기준 판** — MXWhitePaper `f242254`(10-28 07:16 KST 커밋). 행이 가리키는 다른 리포의 자리는 포털 `aec8e29` · 에이전트 서버 `969e723` 기준이다.
- **이 박스(dev)에서 대조한 판** — MXWhitePaper main `bd2e79b`(작업 트리 깨끗, `origin/main` 과 같다) · 포털 main `bf5cd94` · 에이전트 서버 main `7ca3a2e` · 게이트웨이는 cae00 판 `44f4b8d` 를 `git show` 로 읽었다. 대조 시각은 2026-10-30 17:59 KST 다. 읽기만 했다(시험 · 재기동 · 고침 없음).

## 할 일

### MW-01(다시) · 낮음 — API 에 닿지 않으면 위키 도구를 싣는다(열린 쪽)

- **무엇이** — (낮음) mxwp-mcp 가 뜰 때 API 에 닿지 않으면 꺼진 위키 도구 14개를 그대로 싣는다(열린 쪽). 감시가 MCP 를 API 보다 먼저 살리면 챗에 위키 도구가 다시 보이고, HA-08(다시)의 문구 어긋남이 드러난다.
- **근거** — `dist/llm-docx-toolkit/mcp/server.py:1332-1344`(`_wiki_switch`) — 닿지 않으면 `:1342-1343` 이 True 를 돌려준다. `:404` 는 그때 wiki_* 를 싣는다. 10-28 뒤 커밋은 0이고, 10-30 은 위키 도구가 0개라 잠재 위험이다.
- **할 일** — 닿지 않으면 위키 도구를 싣지 않고(닫힌 쪽) 잠시 뒤 다시 보거나, 부를 때 꺼짐을 알면 도구 목록을 바꾼다.
- **출처** — 09-MXWhitePaper MW-01 · reflection-1028/09 MW-01 남은 것 · 3절 2 · TODO-20261029 R-10

#### 지금 판에서의 자리

- **`bd2e79b` 로 고쳐졌다**(MXWhitePaper main, 10-30 17:52 KST 커밋, GitHub 에 올라갔다 — `origin/main` 이 `bd2e79b`). `f242254` 는 HEAD 의 조상이고 그 뒤 커밋은 아홉이다. `git log --oneline f242254..bd2e79b -- dist/llm-docx-toolkit/mcp/server.py` 는 넷이다 — `bd2e79b`(이 행) · `bb0a6a1`(MW-12) · `ff80871`(주석 한 줄) · `a7c411d`(W7 `wiki_lint_report`). `ff80871` · `a7c411d` 는 `_wiki_switch` 와 싣는 자리를 건드리지 않았다.
- 정본이 짚은 자리의 지금 모습은 이렇다.
  - `_wiki_switch` — `f242254` `:1332-1344` 가 `bd2e79b` `:1355-1369` 로 옮겨 갔고, 돌려주는 값이 `bool | None` 이 되었다. 200 이면 True, 404 `wiki_disabled` 면 False, 다른 API 오류면 None(`:1366`), 닿지 않으면 None(`:1367-1368`)이다. 옛 `:1342-1343` 의 `return True` 는 없다.
  - 싣는 자리 — `f242254` `:404` 의 `wiki_tool = mcp.tool if wiki else _skip` 가 `bd2e79b` `:418` 에서 `wiki_tool = mcp.tool if wiki else (_hold if wiki is None else _skip)` 이 되었다. 모름이면 `_hold`(`:412-416`)가 정의만 `_WIKI_HELD`(`:83`)에 모으고 싣지 않는다.
  - `main`(`:1434-1440`) — http 모드에서 모름이면 위키 도구 없이 뜨고, `_watch_wiki`(`:1382-1395`)가 `_WIKI_RECHECK_S = 10.0`(`:84`)초마다 다시 본다. 켜짐이면 `_open_wiki`(`:1372-1379`)가 미뤄 둔 도구를 싣고, 꺼짐이면 닫힌 채 둔다. stdio 는 모름이면 그대로 싣는다(`:1435-1436`).
  - 위키 도구 수 — `@wiki_tool(` 은 `f242254` · `bd2e79b` 모두 14개다.
- 할 일의 두 길 가운데 앞 길이다. '부를 때 꺼짐을 알면 도구 목록을 바꾼다' 는 고르지 않았다 — 부르기 전까지 도구가 보이기 때문이다(MXWhitePaper `docs/llm-wiki/context-notes.md:360-366` WK-D82).
- 시험은 돌리지 않고 자리만 봤다. `dist/llm-docx-toolkit/mcp/tests/test_wiki_tools.py` 의 `test_wiki_switch_reads_health`(`:227` — 닿지 않으면 None, `:233`) · `test_unknown_wiki_starts_closed_then_opens`(`:240`) · `test_unknown_wiki_stays_closed_when_off`(`:253`)다.
- cae00 에 걸리는 길 — 포털 `infra/services.yaml:347-354` 의 mxwp-mcp 는 `mxwp_api` 인스턴스 안에서 `python3 -m mcp --http … --port 8765` 로 뜨고 감시 대상(`watch: true`)이다. 그래서 http 모드의 닫힌 쪽 길이 cae00 에 걸린다.
- 늦게 실은 도구를 게이트웨이가 보는 길 — 게이트웨이 `44f4b8d` 는 `REVIVE_INTERVAL_S`(기본 60초, `gateway.py:216`)마다 백엔드 `list_tools` 를 다시 받아, 지문이 바뀌면 다시 모은다(`:1503-1524`). 위키가 꺼진 cae00 에서는 실을 일이 없다.
- dev — :8765 리스너가 2026-10-30 08:54:11 UTC(17:54 KST)에 떴다. `bd2e79b` 커밋 시각(08:52:44 UTC)보다 뒤다. 그쪽이 보고한 도구 수(도구 40 · wiki 14)는 이 시트가 다시 세지 않았다.

#### 우리 쪽 맞물림

- **에이전트 HA-08(다시) — 고치는 중.** 엔진의 꺼짐 글귀(`deliberation.py:3294` `_WIKI_OFF_HINTS` = 'wiki_disabled' · '위키는 아직 열리지 않았다' — 에이전트 main `7ca3a2e` 에서도 아직 그대로다)가 '열리지 않았다' 와 '열리지 않았습니다' 를 다 받게 한다. 그래서 MX 백서는 꺼짐 문구(`dist/llm-docx-toolkit/mcp/api_client.py:104` `WIKI_OFF_MESSAGE` — `f242254` 와 `bd2e79b` 가 같다)를 바꾸지 않아도 된다. 보낼 때 이렇게 덧붙였고, MX 백서도 문구를 그대로 두었다(WK-D82).
- **MW-01 은 MX 백서 몫 그대로다.** 두 층이 다른 일을 한다. MW-01 은 API 에 닿지 않을 때 닫힌 쪽으로 떠서 꺼진 박스에 위키 도구가 실리지 않게 하고, HA-08 은 그래도 실렸을 때 엔진이 꺼짐을 알아보게 한다.
- **5절 OB-64 · OB-65 — cae00 사람 손 시험.** 위키 버튼 숨김(M-11 · M-12)과 위키 질문(M-13)을 웹 챗에서 본다. 정본은 '끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다' 고 적었고, 상태는 '90-OURS 그대로 — 남았다' 다.
- 지금 코드(이번 요청으로 바꾸지 않는다) — 포털 운영자 동기화는 MX 백서 운영자(`infra/personas/he-team.json:591` `he-doc-mxwhitepaper`)의 위키 몫(`:622-624` optional, `needs_tool: wiki_ask`)을 게이트웨이가 `wiki_ask` 를 낼 때만 잇는다(`infra/scripts/sync-he-personas.py:94-112`, 주석 `:97-99` 가 MW-01 을 전제로 적었다). MW-01 고침이 cae00 에 들어가면, 위키가 꺼진 cae00 에서 MCP 가 API 보다 먼저 떠도 그 몫이 붙지 않는다.

### MW-12 · 낮음 — 이미지 도구 설명이 http 에 없는 upload_image 를 가리킨다

- **무엇이** — (낮음) upload_image_from_url · upload_image_base64 · insert_image_block 설명이 http 모드에서 빠진 upload_image 를 가리켜, MX 백서 운영자가 없는 도구를 찾는다.
- **근거** — `server.py:757` · `:793` · `:843` 이 upload_image 를 말한다. `:397-398` · `:403` 은 http 모드에서 upload_image 를 싣지 않는다. 포털 운영자 정의(`infra/personas/he-team.json:620`)가 세 도구를 writes 로 쓴다.
- **할 일** — 세 도구 설명에서 upload_image 를 빼고 upload_image_from_url · upload_image_base64 로 안내한다.
- **출처** — reflection-1028/09 3절 3

#### 지금 판에서의 자리

- **`bb0a6a1` 로 고쳐졌다**(MXWhitePaper main, 10-30 17:51 KST 커밋, 올라갔다). `bd2e79b` 에서 본 자리는 이렇다.
  - `upload_image_from_url` 설명 — `f242254` `:757` 의 '로컬 파일은 upload_image (셸 경로) 또는' 이 `bd2e79b` `:772-773` 에서 '로컬 파일은 upload_image_base64 (≤256KB) 사용' 이 되었다. 설명 전체는 `:769-776` 이다.
  - `upload_image_base64` — `f242254` `:793` 은 도구 설명이 아니라 그 도구 본문의 크기 초과 오류 문구(RuntimeError)였다. 설명(`f242254` `:770-777`)에는 처음부터 upload_image 가 없다. 오류 문구는 `bd2e79b` `:804-809` 에서 '웹 URL 이면 upload_image_from_url … 을 쓰고, 아니면 256KB 이하로 줄여 다시 올리세요' 로 바뀌었다.
  - `insert_image_block` 설명 — `f242254` `:843` 이 `bd2e79b` `:858` 에서 'upload_image_from_url · upload_image_base64 로 얻은 image_id 로 …' 가 되었다.
  - http 에서 빼는 자리는 그대로다 — 주석 `f242254` `:397-398` 은 `bd2e79b` `:404-405`, `local_tool = _skip if http else mcp.tool` `:403` 은 `:417` 이다. `upload_image` 는 `@local_tool(`(`:747`)이라 http 에서 빠진다.
- 남은 언급 — `bd2e79b` 의 `server.py` 에서 낱말 `upload_image` 는 http 주석(`:404`)과 그 도구 자신의 정의(`:748` · `:756`)에만 있다. `import_file` · `extract_pptx_images` 도 자기 정의 밖에서는 나오지 않는다. `mxwp_system_prompt`(`:464`)가 내는 `dist/llm-docx-toolkit/llm-system-prompt.md` 에는 0건이다. stdio 용 문서(`mcp/README.md` 3건 · `mcp/skill/mxwp/SKILL.md` 1건)에는 있고, MX 백서가 그대로 두기로 했다(`docs/llm-wiki/context-notes.md:367-370` WK-D83).
- 시험은 자리만 봤다. `tests/test_wiki_tools.py:211-213` 의 `test_http_mode_descriptions_do_not_point_at_dropped_tools` 가 http 모드 모든 도구 설명에서 뺀 도구 셋(`_LOCAL_PATH_TOOLS`, `:197`)의 이름을 찾는다. 시험이 보는 것은 도구 설명(`t.description`)뿐이라 `:804-809` 의 오류 문구는 시험 밖이다. 글은 고쳐져 있다.
- 포털 운영자 정의 — 포털 main `bf5cd94` 의 `infra/personas/he-team.json:620`(`he-doc-mxwhitepaper` 의 `writes`)은 `aec8e29` 그대로다(`git log --oneline aec8e29..bf5cd94 -- infra/personas/he-team.json` 0건). 세 도구의 이름은 바뀌지 않아 `:620` 과 어긋나지 않는다.
- 게이트웨이 반영 — 설명만 바뀌어도 게이트웨이 `44f4b8d` 가 다시 모은다. 지문이 이름마다 설명 + 입력 스키마의 해시이기 때문이다(`gateway.py:470-480` `_tools_fp`, 비교 `:1513-1524`).

#### 우리 쪽 맞물림

- **에이전트 HA-29 — 고치는 중.** 정본 HA-29 의 할 일은 잡을 시작하는 도구와 '운영자 정의의 `writes`' 를, 이번 턴 사람 발화가 그 일을 분명히 시키지 않았으면 코드 단에서 확인 카드로 멈추게 한다. MX 백서 운영자의 `writes`(`he-team.json:620`)에 이 행의 세 도구가 있으므로, HA-29 가 들어오면 셋도 사람이 시키지 않은 턴에서는 확인 카드에 걸린다.
- **포털 HP-53 — 고치는 중.** 정본 HP-53 할 일 칸의 목록(ODB · ARP · 코어 허브 · 리스크 앱 · StepForge · DynaForge)에 MX 백서 도구는 없다. 이 행이 가리키는 `:620` 은 HP-53 의 대상 밖이다.
- 운영자 동기화는 게이트웨이에 없는 도구 이름을 만나면 멈춘다([`../context-notes.md`](../context-notes.md) C-8). MW-12 는 이름이 아니라 설명만 바꿔 이 길에 걸리지 않는다.

## 끝나면

두 행은 끝났다(위 '지금 판에서의 자리'). 알릴 곳은 HWAX 포털 세션 `hwaxportal-a5` 이고, 답은 이미 [`../outbound.md`](../outbound.md) 답 칸에 옮겨졌다(포털 `bf5cd94`). 아래는 그 답을 이 박스에서 대조한 것과 남은 것이다.

- **커밋** — MXWhitePaper main `bb0a6a1`(MW-12) · `bd2e79b`(MW-01(다시)). GitHub 에 올라갔다(`origin/main` 이 `bd2e79b`, 17:59 KST 대조).
- **배포 산출물** — 새 SIF · Drive 판은 필요 없다. 두 커밋은 `server.py` · 시험 · 문서만 바꿨고 `.def` · 의존성 변경이 없다. mxwp-mcp 는 `mxwp_api` 인스턴스 안에서 리포 체크아웃(`/workspace` 바인드 — MXWhitePaper `infra/scripts/start.sh:193`)을 돈다(포털 `infra/services.yaml:352`).
- **cae00 에 닿는 길** — update-all §2 의 `infra/scripts/deploy-all-from-drive.sh` 가 MXWhitePaper 를 `git_update`(GitHub fetch · reset)로 받는다(`:261-265`). 지문(앞에 git HEAD — `:194` · `:283`)이 바뀌면 mxwp 를 다시 띄우고 `migrate.sh` 를 돌린 뒤(`:286-290`), `services.sh up mxwp-mcp` 로 MCP 를 다시 올린다(`:292-294`).
- **함께 켜지는 것** — `f242254..bd2e79b` 아홉 커밋(W7 일곱 포함)이 같이 간다. 그 안에 이관 0059 · 0060(`apps/api/alembic/versions/0059_wiki_lint_inquiry.py` · `0060_wiki_notification_kinds.py`)과 `.env.example` 새 키 둘(`WIKI_TOOLS_URL` · `WIKI_TOOLS_TOKEN` — 주석에 '비면 위키 안에서만 답한다')이 있다. `.def` · 의존성 · `infra/` 변경은 0건이다. `apps/web` 19개 파일(W7 화면)도 바뀌었는데, 웹은 Drive 의 web.sif 로 간다(`deploy-all-from-drive.sh:268`). MX 백서 작업 노트는 W7 web.sif 를 'Drive 로는 올리지 않았다(사람이 시킬 때)' 라고 적었다(`docs/llm-wiki/context-notes.md:352-354`). Drive 의 지금 판은 대조 못 함 — 이 박스에서 Drive 를 읽지 않았다. W7 화면이 cae00 웹에 가야 하는지는 이 두 행의 일이 아니므로 MX 백서 쪽이 따로 알린다.
- **cae00 사람 몫** — MX 백서 답은 '사람 몫 없음' 이다(update-all 의 git 받기로 간다). 확인 줄은 그쪽 답 그대로 둘이다.
  - mxwp-mcp tools/list 의 `wiki_*` 가 0개다(위키 꺼짐).
  - MCP 가 API 보다 먼저 떴으면 로그에 '위키 도구를 미루고 다시 본다' 한 줄(`server.py:1439`)이 있고, '미뤄 둔 위키 도구 N개를 실었다'(`:1391`)는 없어야 맞다.
  - 이 시트가 덧붙이는 확인(정본 · 답에는 없다) — 게이트웨이 `tools/list` 의 upload_image_from_url · upload_image_base64 · insert_image_block 설명에 upload_image 가 없다. 포털 `CLAUDE.md` MCP 절의 '도구가 있는지는 소스가 아니라 게이트웨이 `tools/list` 로 확인한다' 를 설명 글에도 쓰자는 제안이다.
  - 포털 세션이 이 확인 줄을 `server-setup.md` 에 옮긴다(`../outbound.md` 머리). 대조 시각에 `docs/request-1030/server-setup.md` 는 아직 없고, 체크리스트 0절 '받은 답을 `outbound.md` · `server-setup.md` 에 옮김' 도 열려 있다.
- **7절 다시 볼 시험** — 7절 표에 MX 백서 몫 시험은 없다. 맞물린 손 시험은 5절 OB-64 · OB-65(M-11 · M-12 · M-13)이고 HWAX 우리 몫이다. 정본은 이 둘이 끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다고만 적었다.
