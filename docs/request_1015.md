# 전문가·지식카드 화면 수정 요청 — 빈 카드 · 로그인 만료 · 긴 카드 · 검색 · 빈 전문가 · HE 운영자



요청일 2026-10-15 · 요청자 koo.park@ax.samsung.com(HWAX Portal) · 대상 **HWAXAgentServer · HWAXPortal · AIDataHub · KooRemapper**(재료 카드는 MaterialTwinWeb 도)

기준 — 포털 origin/main `90147ac` · 에이전트서버 origin/main `c4e4823` · AIDataHub `b401f88`(HEAD = origin) · KooRemapper origin/main `30a1f7d`. 아래 `파일:줄` 은 이 커밋 기준이다(cae00 작업 트리는 포털 `e6a8e52` · 에이전트서버 `7644284` 로 뒤에 있다 — 해당 코드는 같다).

근거 — 2026-10-14 cae00 전수 점검(전문가 796명 · 상세·목록·2쪽·검색·본문 — 호출 오류 0건 · 카드 72,252장)에서 「불러오기는 되는데 화면에서 제대로 안 보이는」 것 24건을 찾았고, 건마다 반대 검증을 거쳤다(반박 0건). 이 요청서는 절마다 origin/main 코드로 다시 확인하고 반대 검토를 한 번 더 거쳤다. cae00 측정은 읽기만 했다.



---



## 요약 — 사용자가 보는 것과 고칠 곳



| # | 요청 | 대상 | 사용자가 보는 것 | 우선 |

|---|---|---|---|---|

| K1 | 블록 구조 본문(blocks·subsections·children)을 마크다운으로 푼다. 풀어도 비면 RAG 절로 채운다. 그것도 없으면 「비어 있는 카드」를 띄운다 | HWAXAgentServer `_record_view`·`catalog_record` · 포털 `AgentDeepView.tsx:104`(선택) · AIDataHub 동기화(K6-4 로 넘긴다) | MX 백서 분석가 427장과 kooremapper-iga 6장이 제목만 늘어선 빈 카드로 열린다. 안내도 없다 | 1 |

| K2 | 갱신이 401·403 이면 로그인 화면으로 보낸다(ste 사본도 지운다). 상세 실패는 세 칸 공용 문구와 「다시 시도」로 보인다. `catalog_agent` 는 `session_failed`·`records_failed` 를 준다. (선택) 갱신 때 세션을 늘린다 | 포털 프런트 `client.ts`·`AuthContext.tsx`·`AgentFacts.tsx`·`PersonaBrowser`·`SeatBrowser`·`StartPicker`·`AgentDeepView` · 에이전트서버 `catalog_agent` · 포털 백엔드(선택) | 로그인 8시간 뒤에는 「조회 실패(http_401) — 다시 시도하세요」만 되풀이된다. 상세를 못 받은 전문가가 역할도 지식도 없는 사람으로 보인다 | 2 |

| K6-5 | 설명도 역할 문서도 없으면 「아직 등록되지 않은 전문가」라고 쓴다 | 포털 `AgentDeepView.tsx:240-247`(K2-4 와 같은 커밋) | 위에 아무것도 없는데 「위 설명이 전부입니다」라고 쓴다 | 2(K2 와 함께) |

| K3 | 총량(`total_sections`·`total_chars`)과 이어 읽을 위치(`next`)를 주고 「다음 부분 보기」를 단다. 표 문구는 표가 실제로 잘렸을 때만 붙인다. 재료 카드는 원천에서 정한다 | 에이전트서버 `RecordRequest`·`_record_view` · 포털 백엔드 프록시 · 포털 프런트 · MaterialTwinWeb·AIDataHub(9) | 열어 본 카드 38%가 6만 자에서 잘린다. 「표는 앞 0행입니다」라는 틀린 안내만 있고, 나머지를 읽을 길이 없다 | 3 |

| K4 | 시작 패널 제목을 `records_total` 로 센다 | 포털 `StartPicker.tsx:298-300` | 전문가 목록의 「64건 · 앞 20건」이 시작 패널에서는 「20건」이 된다(761명) | 4 |

| K5 | 검색어를 낱말로 나눠 AND 로 건다. `%`·`_` 를 이스케이프한다. agents 가 있으면 본문까지 찾는다. 설명문과 시험도 맞춘다 | AIDataHub `record_query_svc.py`·`mcp_runtime.py`·`records.py`·`chat_svc.py`·시험 · 포털 placeholder · 에이전트서버 독스트링 | 카드에 있는 낱말 둘을 순서를 바꾸거나 띄어서 치면 「맞는 카드가 없습니다」가 뜬다 | 5 |

| K8 | 정본의 도구 이름 2건을 고친다. 선택 앱 `optional` 을 둔다. 챗 운영자 문구는 붙은 앱만 말한다. 앱이 다 빠졌을 때 화면 문구를 바꾼다. (선택) update-all 뒤 미리보기를 돌린다 | 포털 `he-team.json`·`sync-he-personas.py`·`test_he_personas.py`·`AgentFacts`·`AgentDeepView` · 에이전트서버 `app.py` | ODB 허브 운영자가 없다. SmartTwin 운영자는 도구가 0개인데 「도구로 답한다」고 한다. 챗 한 턴에 서로 반대인 메시지 셋이 뜬다 | 6 |

| K6-1·2 | dynaforge-report 를 살릴지·돌릴지·접을지 정한다. kooremapper-modelmeta 를 지울지·채울지 정한다. 시험 업로드를 막는다(`--upload`) | AIDataHub 데이터 · KooRemapper `datahub.py`·`kr2datahub.py`·양식 문서 | 이름=키·설명 0자인 전문가가 2명 있다. 그중 한 명 뒤에는 S26-DEMO 시험 카드 3장뿐이다 | 7 |

| K6-3 | 등록 안 된 키로 적재하면 422 로 거절한다(strict 스위치) | AIDataHub `db_writer.py`·`config.py`·시험 | 앞으로 빈 전문가가 말없이 전문가 목록에 생긴다 | 7 |

| K6-4 | 상세 조회가 실패하면 덮어쓰지 않는다. 요약 폴백을 둔다. 요약만 바뀌어도 갱신한다. 154장을 다시 받는다 | AIDataHub `sync_svc.py`·`db_writer.py`·`sync_sources.yml`(동기화 재개는 운영 쪽) | MX 카드 4장 중 3장이 제목 한 줄로만 보인다. 154장은 허브 안의 본문이 비었다. 동기화 3곳이 10-01 부터 멈췄다 | 7 |

| K7 | `_restore_role` 이 `_role_doc` 으로 거른다. 역할이 비면 이름·키로 앉히고 `persona_role_empty` 경고를 낸다 | 에이전트서버 `deliberation.py`·시험 2파일 | 심의 소개 카드와 좌석 지시에 영문 허브 안내 3천 자가 역할로 들어간다. 경고도 없다 | 8 |

| K9 | (선택) JSON 원문 폴백을 json 코드펜스로 감싼다 | 에이전트서버 `app.py:4636`·시험 | SIM 카드 3장이 86~119줄 JSON 을 비례폭 문단 하나로 보인다 | 9 |



### 넣는 순서



1. **K1 빈 카드** — MX 백서 분석가 427장과 kooremapper-iga 6장이 제목만 늘어선 빈 카드로 열린다. 「비어 있다」 안내도 없다.

2. **K2 로그인 만료·상세 실패**(+ K6-5) — 로그인 8시간 뒤 모든 화면이 `http_401` 과 「다시 시도」만 보인다. 10-14 하루에 갱신 403 이 124건, 접속 IP 34곳에서 났다.

3. **K3 6만 자 잘림·이어 읽기** — 열어 본 카드 38%가 말없이 잘리고 「표는 앞 0행」이라는 틀린 안내가 붙는다. K1 위에 얹는다.

4. **K4 시작 패널 카드 수** — 한 줄 수정이다. K2 와 같은 포털 묶음·같은 빌드에 넣는다.

5. **K5 카드 검색** — 카드에 있는 낱말 둘로 찾아도 「맞는 카드가 없습니다」가 뜬다. 본문 검색(K5 요청 2)은 K1 다음에 낸다.

6. **K8 HE 운영자** — 정본 오류 2건 때문에 cae00 운영자 동기화가 아예 돌지 않아 ODB 허브 운영자를 만들 수 없다. stcx 개통 전에 들어가야 개통 직후 반영된다.

7. **K6 데이터·적재** — 허브 동기화 3곳(mxwp·signalforge-gs·materialtwin)이 10-01 부터 한 번도 돌지 않았다. 빈 전문가 2명과 시험 카드 3장이 운영 전문가 목록에 떠 있다.

8. **K7 심의 좌석의 빈 역할** — 빈 전문가를 좌석에 앉히면 영문 허브 안내 3천 자가 역할이 되고 경고도 없다.

9. **K9 (선택) SIM JSON 보기** — 급하지 않다. K1·K3 이 같은 함수를 고칠 때 한 줄로 같이 넣는다.



### 같은 파일을 고치는 요청 — 묶어서 넣는다



- **에이전트서버 `_record_view`·`catalog_record`** — K1(본문 풀기·빈 카드) → K3(총량·이어 읽기) → K9(JSON 폴백 펜스) 순이다. K3 은 K1 이 만든 `_flat_sections` 위에서 돈다. K3 요청 3 의 `catalog_record` 가 K1 요청 2 를 합친 최종 꼴이다(빈 카드 판정은 카드 전체 `total_chars == 0`).

- **에이전트서버 PR 순서** — K1 → K3 → K9 → K2(`catalog_agent`) → K8(운영자 문구) → K7(`deliberation.py`) → K5(독스트링). 줄 번호는 `c4e4823` 기준이라 앞 PR 이 들어가면 밀린다 — 내용으로 찾는다. `tests/test_catalog_deep.py` 에 K1(4경우)·K2(1)·K3(1)·K9(단언 2줄)이 시험을 더하고, `tests/test_operator_persona.py:301` 픽스처는 K2 가 실제 응답 모양으로 바꾼다.

- **포털 `AgentDeepView.tsx`** — 일곱 요청이 고친다(K1-3 `:104` · K2-4 `:113-116`·`:180`·`:210-211` · K6-5 `:240-247` · K3-6 `:39`·`:51-59` · K3-7 `:152-167`·`:326` · K5-5 `:265` · K8-4 `:12`·`:297-298`). 줄은 겹치지 않지만 K1-3·K3-6 은 `RecordReader` 안, K2-4·K6-5 는 프로필 블록 안이다. 포털 PR 하나로 묶고, K6-5 는 K2-4 와 같은 커밋으로 넣는다.

- **포털 `AgentFacts.tsx`**(K2-3 `DetailError` · K8-4 `operatorOffline`) · **`chat.api.ts`**(K2-3 `records_error` · K3-5 `RecordView`·`fetchRecord`) · **`StartPicker.tsx`**(K2-3 `:310-311` · K4 `:298-300`) — 겹치지 않는다. 같은 묶음·같은 빌드로 넣는다(프런트 빌드와 Drive 업로드는 한 번).

- **빈 역할 판정** — K2 요청 5(`catalog_agent`)·K7 요청 1(`_restore_role`)·K6-5(화면 문구)는 같은 기준으로 가른다. `agent_type` 이 있으면 원문을 받은 것이고, 그때 역할이 비면 실패가 아니라 「아직 등록되지 않은 전문가」다.

- **데이터 정리는 코드 확인 뒤에** — K6-1·K6-2 정리(빈 전문가·SIM 시험 카드 삭제)를 먼저 하면 K2·K6-5·K7·K9 의 박스 확인 대상이 사라진다. 코드 반영을 박스에서 확인한 뒤 데이터를 정리한다.

- **AIDataHub `sync_svc.py`·요약 규칙** — K6-4 가 맡는다. K1 요청 4 는 그쪽을 가리키기만 한다.



---



## K1. 블록 구조 본문 카드가 빈 카드로 열린다(MX 백서 분석가 · kooremapper-iga)



대상 — HWAXAgentServer(1·2) · HWAXPortal(3, 선택) · AIDataHub(4, 동기화·데이터) · 담당 판단: HWAXAgentServer.



기준 — 에이전트서버 origin/main `c4e4823` · 포털 `90147ac` · AIDataHub `b401f88` · MXWhitePaper `b32b135`. 측정은 cae00 에서 2026-10-15 에 읽기만 했다. 카드 원문은 AIDataHub REST 목록(`GET :8001/api/records?agent=…`)으로 받았다. 이 목록은 조회 수와 감사 로그를 쓰지 않는다. 키와 길이만 셌다.



**지금** — `/catalog/record` 는 `_record_view` 로 카드를 읽기 칸 모양으로 바꾼다(app.py:4598-4637). 이 함수는 절 본문으로 최상위 절의 `content_text` 나 `text` 만 읽는다(:4606-4608). `blocks`·`subsections`·`children` 은 보지 않는다. 두 전문가의 카드는 본문이 이 두 칸에 없다.



- **mx-whitepaper-analyst 427장.**

  - ① 273장은 MXWhitePaper DocumentJSON 트리다. 절 키가 `blocks|id|layout|(layoutWidths|)level|number|subsections|title` 이고, 글은 `blocks[]` 에 있다(paragraph 7,197 · table 6,784 · callout 1,023 · code 334 · math 11 · quote 2). 표 블록은 `headers`(list[str])와 `rows`(list[list[str]])를 블록 안에 둔다. 코드 블록은 `code`·`language` 를 쓴다. 콜아웃은 `title`·`text`·`variant` 를 쓰고, 수식은 `expression` 을 쓴다.

  - ② 154장은 동기화 자리표시다. 「본문」 절 하나에 `content_text` 가 0자다. sync_svc.py:264-275 는 `sections_field` 가 비면 `body_field`(기본 `body_text`)로 폴백한다. mxwp 매핑에는 `body_field` 가 없다(config/sync_sources.yml:89-142).

  - 자리표시 154장의 글은 AIDataHub `record_sections`(RAG 절)에 있다. 149장에 글이 있다(568행 · 167,969자). 5장은 어디에도 글이 없다(10-14 읽기 전용 DB 조회). 0309 는 오늘 `get_record_sections` 로 다시 봤다. 3행 중 첫 행은 빈 「본문」이고, 나머지 2행이 1,429자다.

- **kooremapper-iga 6장 전부.** 원인이 ①과 같다. 첫 카드 `DOC-HE-TST-2026-0000000002` 는 content 키가 `figures|meta|schema_version|sections|sources|tables|toc` 다. 절 키는 `blocks|children|figure_refs|id|level|table_refs|title` 이다(최상위 6절 · 전체 14절 · 블록 글 2,634자 · 절 자체 글 0자). 자식 절은 `children` 에 있다. 표는 `content.tables[]`(`caption`·`headers`·`rows`)에 두고 블록 `{type:'table', ref}` 로 가리킨다. 6장의 표·그림 ref 52건은 모두 이 목록에서 찾아진다. 코드 블록 글은 `code` 가 아니라 `text` 에 있다. 절 `id` 는 한 카드 안에서 겹치기도 한다(6장 중 2장).

- **지금 응답.** `/catalog/record` 응답은 다음과 같다. 모두 `truncated: False` 다.

  - 0339: 106절 · 글 0자.

  - 0022: 3절 · 0자.

  - 0309: 1절 · 0자.

  - kooremapper-iga 첫 카드: 6절 · 0자.

- **화면.** 읽기 칸은 절마다 제목과 `s.text` 를 그린다(AgentDeepView.tsx:54-58). 「본문이 비어 있는 카드입니다.」는 절이 0개일 때만 뜬다(:104). 원문(JSON) 폴백도 절이 0개일 때만 탄다(app.py:4631). 그래서 사용자는 제목만 늘어서고 그 아래가 빈 카드를 다 불러온 카드로 본다.

- **요약도 비었다.** 427장 중 320장의 summary 가 0자다(트리 172장 + 자리표시 148장). 목록은 빈 요약 줄을 숨기므로(AgentDeepView.tsx:312) 제목만 보인다. 카드 검색은 제목과 요약을 ILIKE 로 찾는다(AIDataHub record_query_svc.py:66-68). 그래서 이 카드들은 제목으로만 찾힌다.

- **오래된 버그다.** :4606-4616 은 0f0c9c1(2026-09-11)에 들어온 뒤 c4e4823 까지 바뀌지 않았다(git blame).

- **다른 전문가의 카드는 바뀌지 않는다.** DOC 카드 59,009장 중 1,205장을 표본으로 봤다. 1,204장이 평평한 `content_text` 절이다. 글이 있는 절에 자식 절이 붙은 카드는 0장이다. 그래서 1 은 블록이나 자식 절이 있는 카드만 바꾼다.

- **MXWhitePaper 코드는 그대로 옮기면 안 된다.** 같은 일을 하는 `flatten_sections`·`_render_blocks` 가 MXWhitePaper integrations/aidatahub/aidatahub_sync.py:99-190 에 있다. 하지만 `_render_table` 은 `rows[0]` 을 머리행으로 써서 MX 블록의 `headers` 를 버린다(:99-109). code 는 `lang`(:132)을, 수식은 `tex`(:135)를, callout 은 `kind`(:139)를 읽는다. MX 실데이터는 `language`·`expression`·`title`·`variant` 를 쓴다.



**요청**



1. `_record_view` 가 블록 구조를 풀게 해 주십시오. app.py:4598 앞에 함수 셋을 더하고 :4606-4608 을 바꾼다. 결과는 마크다운 문자열이다. 포털은 이미 표·코드펜스·`$$` 수식을 그린다(md.ts:134 표 · :215 수식 · TextBlock.tsx:197 펜스 · :339 표). 표 칸은 md.ts 가 ASCII `|` 로만 나누므로(md.ts:54-69), 칸 속 `|` 는 전각으로 바꾼다.



```diff

+def _md_cell(c) -> str:

+    # md.ts splitCells 는 ASCII '|' 로만 칸을 가른다 — 칸 속 '|' 는 전각으로.

+    return ("" if c is None else str(c)).replace("\n", " ").replace("|", "｜")[:200]

+

+

+def _block_md(b: dict, refs: dict) -> str:

+    """DocumentJSON 블록 한 개 → 마크다운. 표는 MXWhitePaper 가 블록 안에(headers·rows),

+    KooRemapper 는 content.tables 에 두고 ref 로 가리킨다(실측)."""

+    t = str(b.get("type") or "")

+    if t in ("table", "figure") and b.get("ref") in refs:

+        b = {**refs[b["ref"]], "type": t}

+    if t == "table":

+        hdr, rows = b.get("headers") or [], [r for r in b.get("rows") or [] if isinstance(r, list)]

+        if not hdr and rows:

+            hdr, rows = rows[0], rows[1:]

+        if not hdr:

+            return ""

+        md = ["| " + " | ".join(map(_md_cell, hdr)) + " |", "|" + " --- |" * len(hdr)]

+        md += ["| " + " | ".join(map(_md_cell, r)) + " |" for r in rows[:RECORD_ROWS_MAX]]

+        if len(rows) > RECORD_ROWS_MAX:  # 잘린 표를 전부인 척 보이지 않는다

+            md.append(f"\n*표 앞 {RECORD_ROWS_MAX}행만 싣는다 — 전체 {len(rows)}행.*")

+        return (f"**{b['caption']}**\n\n" if b.get("caption") else "") + "\n".join(md)

+    if t == "code":  # MXWP 는 code·language, KooRemapper 는 text

+        return f"```{b.get('language') or ''}\n{b.get('code') or b.get('text') or ''}\n```"

+    if t == "math":

+        return f"$$\n{b.get('expression') or b.get('tex') or ''}\n$$"

+    if t == "figure":

+        return f"*[그림] {b['caption']}*" if b.get("caption") else ""

+    text = str(b.get("text") or "")

+    if t == "list_item":

+        return f"{b.get('marker') or '-'} {text}"

+    if t == "callout" and b.get("title"):

+        return f"**{b['title']}** {text}"

+    return f"> {text}" if t == "quote" else text

+

+

+def _flat_sections(secs, refs: dict):

+    """절 트리(MXWP subsections · KooRemapper children) → (절, 본문) 깊이 우선.

+    content_text·text 가 비면 blocks 를 푼다 — 종전엔 최상위 content_text 만 읽어 제목만 남았다."""

+    for s in secs or []:

+        s = _first_dict(s)

+        text = str(s.get("content_text") or s.get("text") or "")

+        if not text and isinstance(s.get("blocks"), list):

+            text = "\n\n".join(t for t in (_block_md(_first_dict(b), refs) for b in s["blocks"]) if t)

+        yield s, text

+        yield from _flat_sections(s.get("subsections") or s.get("children"), refs)

```



```diff

     out["summary"] = str(rec.get("summary") or "")[:2000]

+    refs = {x["id"]: x for k in ("tables", "figures")

+            for x in (content.get(k) if isinstance(content.get(k), list) else []) if isinstance(x, dict) and x.get("id")}

     budget = RECORD_TEXT_MAX

-    for s in content.get("sections") or []:

-        s = _first_dict(s)

-        text = str(s.get("content_text") or s.get("text") or "")

+    for s, text in _flat_sections(content.get("sections"), refs):

         if budget <= 0:

```



   - 절 `id`·`level` 을 만드는 줄(:4615-4616)은 그대로 둔다. kooremapper-iga 는 한 카드 안에서 절 `id` 가 겹친다. 읽기 칸은 그 값을 React 키로 쓴다(`key={s.id || i}`, AgentDeepView.tsx:55). 그래서 `id` 를 채우면 키가 겹친다. `level` 은 두 모양 모두 정수로 들어 있다(MX 3,161절 · iga 358절).

   - 60,000자 상한과 200행 상한은 그대로 둔다. 블록 표가 200행을 넘으면 그 자리에 잘렸다고 적는다. MX 표 6,784개 중 2개(최대 322행)가 그렇다. 둘 다 60,000자 안쪽이라, 적지 않으면 사용자가 잘린 표를 전부로 읽는다(app.py:4585-4586 주석과 같은 이유).

   - 풀고 나면 MX 18장이 60,000자에서 잘린다(0339 는 25절째). 잘림 안내 문구는 60,000자 절단 항목에서 따로 다룬다.

   - 드문 MX 블록 20종 65개(도식 블록 15 · glossary-ref 14 · kpi-cards 6 · flow 4 · heading-4 4 …)는 글 칸이 없어 빠진다. 이번 요청에서는 다루지 않는다.



2. 풀어도 글이 0자인 카드를 처리해 주십시오(app.py:4647-4650).

   - 먼저 게이트웨이 도구 `get_record_sections` 로 RAG 절을 받아 채운다. 글이 있는 행이 없으면 절을 비운다. 그러면 읽기 칸이 이미 가진 「본문이 비어 있는 카드입니다.」(AgentDeepView.tsx:104)가 뜬다.

   - 이 도구는 `get_record` 와 같은 `ai-data-hub` 백엔드에 있다(게이트웨이 `/tools-map` 실측). 도구가 안 보이면 `_call` 이 None 을 돌려주고(deliberation.py:1832-1834), 아래에서 빈 목록이 된다.

   - 목록을 돌려주는 도구라 원소마다 content 하나로 온다. `_call` 은 그것을 이어 붙인다(deliberation.py:1840-1841). 그래서 `_parse_json` 대신 `_parse_json_multi`(deliberation.py:2024, app.py:74 에서 이미 import)로 받는다. 같은 서버의 `list_agents` 도 이렇게 받는다(app.py:1734).

   - `content_text` 가 빈 행은 버린다. 0309 의 RAG 절 첫 행도 빈 「본문」이다. 남은 행이 없으면 `_record_view` 에 넘기지 않는다. 빈 목록을 넘기면 :4631 원문(JSON) 폴백이 `{"sections": []}` 를 본문으로 띄운다.

   - 도구 호출이 실패하면 빈 카드로 보이지 않게 `record_failed` 를 돌려준다. `_call` 은 실패를 `(tool … error: …)` 글로 돌려준다(deliberation.py:1843-1844). 이것을 app.py 가 이미 import 한 `_tool_text_ok`(app.py:75)로 가린다. 읽기 칸은 이 오류를 「카드를 불러오지 못했습니다(record_failed).」로 보인다(AgentDeepView.tsx:325).



```diff

     rec = _first_dict(_parse_json(await _call(tools, "get_record", {"record_id": rid})))

     if not rec.get("id"):

         return {"error": "record_failed", "id": rid}

-    return _record_view(rec)

+    view = _record_view(rec)

+    if view["table"] is None and not any(s["text"] for s in view["sections"]):

+        # content 엔 빈 '본문' 자리표시뿐이고 글은 RAG 절에만 있는 카드가 있다(MXWP 자리표시 154장 중 149장, 실측).

+        raw = await _call(tools, "get_record_sections", {"record_id": rid})

+        if isinstance(raw, str) and raw.strip() and not _tool_text_ok(raw):

+            return {"error": "record_failed", "id": rid}  # 조회 실패를 '빈 카드'로 보이지 않는다

+        rows = [r for r in _parse_json_multi(raw) if isinstance(r, dict) and r.get("content_text")]

+        # 어디에도 글이 없으면 절을 비운다 — 제목만 늘어놓지 않고 읽기 칸이 '본문이 비어 있는 카드입니다.' 를 띄운다

+        alt = _record_view({**rec, "content": {"sections": rows}}) if rows else {"sections": [], "truncated": False}

+        view["sections"], view["truncated"] = alt["sections"], alt["truncated"]

+    return view

```



   - K3 이 함께 들어가면 이 판정과 다시 그리기는 K3 요청 3 의 꼴로 바꾼다. 판정은 쪽이 아니라 카드 전체 값(`total_chars == 0`)으로 한다. 그래야 이어 읽은 쪽에 빈 절만 남은 멀쩡한 카드를 빈 카드로 보지 않는다.



3. (포털, 선택) 다른 길로 제목만 있는 절이 와도 안내가 뜨게 해 주십시오. AgentDeepView.tsx:104 를 바꾼다. 2 가 들어가면 에이전트서버가 빈 카드를 절 0개로 주므로, 이 변경은 예전 응답에 대한 보험이다. `[].every` 는 true 라서 절이 0개인 종전 경우도 그대로 덮는다.



```diff

-      {rec.sections.length === 0 && !rec.table && <p className="pv-empty">본문이 비어 있는 카드입니다.</p>}

+      {rec.sections.every((s) => !s.text) && !rec.table && <p className="pv-empty">본문이 비어 있는 카드입니다.</p>}

```



4. (AIDataHub, 동기화·데이터) 2 는 화면을 살리는 우회다. 정본 쪽 수정은 **K6-4** 가 맡는다. 같은 줄을 두 곳에서 고치지 않게 여기서는 가리키기만 한다.

   - 상세 조회가 실패한 항목을 목록 응답만으로 덮어쓰지 않게 한다(sync_svc.py:822-828) — K6-4 요청 3.

   - mxwp 요약 폴백과, 요약·제목만 바뀌어도 갱신하기 — K6-4 요청 1·2. 2 가 들어가면 요약을 따로 강제로 다시 쓸 일은 없다.

   - 자리표시 154장 다시 받기 — K6-4 요청 4.

   - 동기화가 지금 도는지는 K6-4 가 확인했다. mxwp 정기 동기화는 10-01 부터 매번 SSRF 가드에 막혀 실패한다. 그래서 위 셋은 K6-4 요청 0(동기화 재개, 운영 쪽 결정)이 풀려야 효과가 난다.

   - 154장은 모두 06-12 에 만들어졌고, 마지막으로 바뀐 날은 08-07·08-10·08-12 다(REST 목록 `created_at`·`updated_at`). 검토 중 단건 조회로 바뀐 0022 를 빼면, MX 427장 중 09-03 뒤에 바뀐 카드는 없다.



**왜** — MX 백서 분석가 427장과 kooremapper-iga 6장이 모두 제목만 있는 빈 카드로 열린다. 「비어 있다」는 안내도 뜨지 않는다. 433장 중 428장의 글은 AIDataHub 에 있고, 챗·RAG 는 그 글을 쓴다. 카드 화면만 글을 못 보여 주므로, 사용자는 이 전문가를 지식이 없는 전문가로 읽는다.



**확인** — 먼저 에이전트서버 리포에서 `pytest tests/test_catalog_deep.py -q` 가 통과해야 한다. 기존 세 경우(문서·표·원문 JSON)는 글이 있어 새 길을 타지 않는다. 같은 파일에 네 경우를 더해 주십시오. MX 트리(blocks·subsections·표·코드), KooRemapper(children·tables ref·코드 text), 자리표시 + `get_record_sections` 성공, 같은 경우의 빈 결과·`(tool … error` 실패다.



다음으로 에이전트서버를 새 코드로 올린 뒤 cae00 에서 아래를 돌린다. 이 스크립트는 본문을 찍지 않고 절 수와 글자 수만 본다. 단건 REST `GET /api/records/{id}` 는 조회 수와 감사 로그를 쓰므로(records.py:168-172) 확인에는 쓰지 않는다.



```bash

python3 - <<'EOF'

import json, os, urllib.request

G = json.load(open(os.path.expanduser("~/kc-check/groups.json")))["caeg"]

for rid in ("DOC-MX-WP-2026-0000000339", "DOC-MX-WP-2026-0000000022",

            "DOC-MX-WP-2026-0000000309", "DOC-HE-TST-2026-0000000002"):

    req = urllib.request.Request("http://127.0.0.1:9009/catalog/record", method="POST",

                                 data=json.dumps({"id": rid, "groups": G}).encode(),

                                 headers={"Content-Type": "application/json"})

    d = json.load(urllib.request.urlopen(req, timeout=180))

    s = d.get("sections") or []

    print(rid, d.get("error"), len(s), sum(len(x["text"]) for x in s), d.get("truncated"))

EOF

```



기대값은 아래와 같다. 1 의 함수를 cae00 데이터(AIDataHub REST 목록)에 메모리에서 돌린 값이다. 0309 는 `get_record_sections` 실측이다. 에이전트서버에서 돌린 값은 아니다.



| 카드 | 지금 | 반영 뒤 |

|---|---|---|

| 0339(트리 · 요약 있음) | 106절 · 0자 | 25절 · 60,000자 · truncated True |

| 0022(트리 · 요약 없음) | 3절 · 0자 | 3절 · 1,435자 |

| 0309(자리표시) | 1절 · 0자 | 2절 · 1,429자(RAG 절) |

| kooremapper-iga 첫 카드 | 6절 · 0자 | 14절 · 3,031자 |



전체로는 MX 427장 중 422장(트리 273장 + 자리표시 149장)과 kooremapper-iga 6장에 글이 보여야 한다. MX 18장은 60,000자에서 잘리고 `truncated: True` 다. 글이 없는 MX 5장은 「본문이 비어 있는 카드입니다.」가 떠야 한다. 화면에서도 확인한다. 포털 심층 보기에서 MX 백서 분석가의 카드를 열면 글·표·코드가 보여야 한다.



K6-4 가 들어간 뒤에는 AIDataHub 를 읽기 전용 REST 목록으로 본다. 지금 값은 자리표시 154장, 요약 없음 320장이다.



```bash

python3 - <<'EOF'

import json, urllib.request

stub = nosum = 0

for off in range(0, 500, 100):

    d = json.load(urllib.request.urlopen(

        f"http://127.0.0.1:8001/api/records?agent=mx-whitepaper-analyst&limit=100&offset={off}", timeout=120))

    for r in d["items"]:

        secs = (r.get("content") or {}).get("sections") or []

        stub += len(secs) == 1 and secs[0].get("title") == "본문" and not secs[0].get("content_text")

        nosum += not r.get("summary")

print("자리표시", stub, "요약 없음", nosum)

EOF

```



---



## K2. 실패·로그인 만료를 실패로 보이기(전문가 상세·카드 화면)



대상 — HWAXPortal(frontend, 선택 1건은 backend) · HWAXAgentServer · 담당 판단: HWAXPortal 프런트 개발(요청 1~4) · HWAXAgentServer 개발(요청 5) · HWAXPortal 백엔드 개발(요청 6, 선택).

기준 — 포털 origin/main `90147ac` · 에이전트 서버 origin/main `c4e4823` · AIDataHub `b401f88`. 아래 `파일:줄` 은 이 판 기준이다(cae00 에서 `git show origin/main:…` 으로 읽었다).



**지금 — 로그인 만료.** 세션은 로그인하고 8시간 뒤에 끝난다. 갱신 쿠키와 CSRF 쿠키가 둘 다 `max_age=jwt_refresh_ttl`(28800초, `backend/app/config.py:95`)이다(`backend/app/auth/cookies.py:42`·`:60`). `/auth/refresh` 는 액세스 쿠키만 다시 준다(`backend/app/auth/routes/session.py:246`). 8시간이 지나면 CSRF 쿠키가 없어져 `require_csrf` 가 403 을 낸다(`backend/app/deps.py:115-118`). 갱신 토큰이 없을 때 나는 401(`session.py:238`)과 같은 만료이므로, 403 을 따로 고칠 일은 아니다. 프런트 `apiFetch` 는 401 이면 갱신을 한 번 해 보고, 실패하면 401 을 그대로 돌려준다(`frontend/src/api/client.ts:41-45`). 갱신 결과는 `:22` 에서 `r.ok` 만 본다. 받는 쪽은 저마다 `http_401` 문자열로 바꿔 화면에 띄운다(`frontend/src/api/chat.api.ts:206`·`:358`·`:408`). 로그인 화면으로 보내는 코드는 없다. `AuthContext` 는 창 포커스 때 `/auth/me` 가 실패해도 무시한다(`frontend/src/auth/AuthContext.tsx:41-43`). 주석(`:34-35`)에는 「진짜 만료는 다음 API 호출의 401 이 알린다」고 적혀 있지만, 그 401 을 받아 처리하는 곳이 없다.



10-14 실측(`infra/data/nginx-access.log`, 한 접속 IP). 05:58:03 에 SSO 로그인했고, 13:55:41 에 마지막 갱신 200 이 났다. 14:18:05 부터 갱신이 403 이다. 14:18~16:10 사이에 `/systems/heax-hub/launch` 401 → 갱신 403 이 16번 있었다. 화면을 안 볼 때도 부르는 주기 호출로 본다. `SsoPrimer` 가 5분마다 확인하고, 실패하면 최대 60분까지 늦춰 다시 부른다(`frontend/src/components/layout/SsoPrimer.tsx:13`·`:16`·`:62`·`:69`, `frontend/src/api/launch.api.ts:13` 이 `apiFetch` 를 쓴다). 로그에는 쿼리(`?via=primer`)가 안 남아 사용자 클릭과 구분하지는 못했다. 16:37~16:39 에 401 이 22건 났다(`/agent/deliberate/experts` 13 · `/agent/search-capability` 4 · `/auth/me` 3 · 대화 1 · changelog 1). 그 사이 갱신 14번은 모두 403 이었다. 화면은 계속 로그인 상태로 보였다. 사용자가 16:39:16 에 직접 로그아웃하고 16:39:33 에 SSO 로 다시 로그인하고서야 풀렸다. 로그아웃 때 ste 회수는 401 이었고, `/auth/logout` 도 CSRF 403 이었다(`session.py:254`). 그동안 뜬 문구는 아래와 같다(로그에 찍힌 호출을 코드로 따라가 확인했다. 화면 캡처는 없다).

- 시작 패널: 「조회 실패(http_401) — 다시 시도하세요.」(`frontend/src/components/chat/StartPicker.tsx:168`).

- 전문가 목록 창: 「전문가 목록을 불러오지 못했습니다 — 잠시 후 다시 열어 보세요.」(`frontend/src/components/chat/PersonaBrowser.tsx:183`).

- 전문가 풀을 그 탭이 이미 받아 두었다면(`frontend/src/components/chat/usePersonaPool.ts:13-16` 모듈 캐시) 전문가 목록은 그대로 그려지고, 전문가를 누르면 아래 문구가 뜬다.

  - 상세: 「상세를 불러오지 못했습니다(http_401).」(`PersonaBrowser.tsx:293`).

  - 전체 화면: 「설명을 불러오지 못했습니다(http_401).」 바로 밑에 「따로 쓴 역할 문서가 없습니다 — 위 설명이 전부입니다.」(`frontend/src/components/chat/AgentDeepView.tsx:210`·`:211`·`:246`).

  - 카드 목록: 「지식카드를 불러오지 못했습니다(http_401) — 보유 지식이 없다는 뜻이 아닙니다.」(`:289-291`).



다시 로그인하라는 안내는 어느 문구에도 없다. 「다시 시도」·「잠시 후」를 따라 해도 계속 실패한다. 10-14 하루 동안 `POST /auth/refresh` 403 은 124건이었고, 접속 IP 34곳에서 났다. 그중 63건은 같은 IP·같은 초의 `/systems/heax-hub/launch` 401 바로 뒤였다. 만료된 탭이 띄워져 있기만 해도 하루 종일 갱신 403 을 낸다는 뜻이다(같은 IP 의 00:00:38~05:00:38 매시 정각 패턴).



**지금 — 상세 실패가 빈 전문가로 보인다.** 에이전트 서버 `catalog_agent`(`app.py:4485-4533`)는 도구가 하나도 없을 때만 `error` 를 낸다(`:4491-4492`). `get_agent_session`·`list_records` 가 실패하는 경우는 셋이다.

- 도구 자체가 없다(`deliberation.py:1833-1834` 가 None 을 준다).

- `_cap_tool` 이 「✖ 도구 … 호출 실패」 문자열을 준다(`app.py:1107`).

- 도구가 실패를 평문으로 준다. 없는 키면 AIDataHub 가 `agent not found: <키>` 를 낸다(`api_server/src/api/mcp_runtime.py:402`). 10-15 에 Claude MCP 로 부르면 `Error executing tool get_agent_session: agent not found: zz-no-such-expert` 가 왔다. 에이전트 서버가 받는 문자열 모양은 미확인이다.



어느 경우든 예외가 나지 않는다. 그래서 기본값(name=key, 역할·프롬프트 빈 값, 카드 0)으로 200 을 주고, 로그(`:4516`·`:4532`)도 남지 않는다. 옆 경로는 이미 실패를 구분한다. `/catalog/agent/records` 는 `records_failed` 를 주고(`:4572-4574`), `_persona_meta` 는 도구 없음과 `(tool ` 응답을 따로 본다(`:2633-2640`).



10-15 실측(cae00 9009, caeg 그룹). 같은 날 다시 불러 같은 결과를 확인했다.

- 없는 키 `zz-no-such-expert` → 200 `{name: 키, role "", records_total 0, error 없음}`.

- `plat:aidatahub` 만 뺀 그룹으로 `cam-aa-process` → 200 `{name: 키, role "", records_total null, error 없음}`. 정상 그룹이면 이름 70자 · 역할 382자 · 카드 64건이 온다.



10-14 게이트웨이 로그(`/tmp/hwax-services/mcp-gateway.log`)에는 ai-data-hub 끊김이 있었다. 12:27:56 에는 진행 중 호출 14건이 실패로 돌아갔다. 12:35:53 에는 `get_agent_session` 이 `backend session down` 으로 실패해 한 번 다시 붙었다. 그 사이에 상세 화면 호출이 있었는지는 미확인이다(에이전트 서버 접근 로그에 시각이 없다).



프런트의 네 화면은 실패를 서로 다르게 다룬다.

- `PersonaBrowser.tsx:293` 과 `AgentDeepView.tsx:210` 은 `detail.error` 를 띄운다. 그런데 `AgentDeepView` 는 실패해도 프로필을 그린다(`:211`). 제목도 키로 바뀐다. `name = detail?.name || agent.name`(`:180`)인데, 실패본은 `name` 이 키이기 때문이다(`chat.api.ts:350`·`:358`).

- `SeatBrowser.tsx` 는 `error` 를 한 번도 읽지 않는다(상세 칸 `:196-214`). 그래서 심의 좌석 상세에는 이름·키·버튼만 남는다.

- `StartPicker.tsx` 는 카탈로그 오류(`:168`)만 본다(상세 칸 `:277-313`). 그래서 키 하나만 든 테두리 상자가 된다. 고정된 전문가로 패널을 다시 열면 상세를 아예 불러오지 않는다. `:30`·`:41` 에서 `pinnedAgent` 로 시작하지만 `showAgent` 를 부르지 않기 때문이다. 결과는 빈 상자다.

- `AgentDeepView` 는 `initialDetail` 이 실패한 응답이어도 다시 부르지 않는다(`:113-116`).



**요청**



1. **`client.ts` — 갱신이 확실히 실패하면 이벤트를 낸다.**

   ```diff

    // frontend/src/api/client.ts

   +/** 갱신이 401·403 으로 끝났다 — 세션을 되살릴 수 없다. AuthContext 가 듣는다. */

   +export const SESSION_EXPIRED_EVENT = 'hwax:session-expired';

   +

    let refreshInFlight: Promise<boolean> | null = null;

    …

   -      .then((r) => r.ok)

   +      .then((r) => {

   +        // 403 은 CSRF 쿠키가 없어서다 — 갱신 쿠키와 수명이 같아(cookies.py:42·:60) 401 과 같은 만료다.

   +        // 네트워크 오류·5xx 는 순간 끊김일 수 있어 알리지 않는다.

   +        if (r.status === 401 || r.status === 403) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));

   +        return r.ok;

   +      })

          .catch(() => false)

   ```

   동시에 난 401 은 `refreshInFlight` 로 갱신 한 번에 묶인다. 그 뒤에 나는 이벤트는 이미 로그아웃 상태라 아무 일도 하지 않는다. 세션은 살아 있는데 하위 앱이 401 을 준 경우는 갱신이 200 이므로 이벤트를 내지 않는다.



2. **`AuthContext.tsx` — 이벤트를 받으면 로그아웃 상태로 바꾼다.** 그러면 `ProtectedRoute` 가 `/login` 으로 보내고, 돌아올 경로를 `state.from` 에 담는다(`frontend/src/auth/ProtectedRoute.tsx:11-12`). 로그인 화면의 「삼성 AD 계정으로 로그인」(`frontend/src/pages/LoginPage.tsx:92`)을 한 번 누르면 같은 경로로 돌아온다(`session.py:140-147` 이 `return_to` 로 되돌린다). 포커스 때 부르는 `/auth/me`(`frontend/src/api/auth.api.ts:5`)와 `SsoPrimer` 의 주기 호출도 `apiFetch` 를 거치므로 같은 길로 잡힌다. 10-14 였다면 그 탭은 14:18:05 첫 갱신 403 때 로그인 화면으로 넘어갔을 것이다. 16:37 에 돌아온 사용자는 `http_401` 문구 대신 로그인 화면을 봤을 것이다. 화면마다 `http_401` 처리를 따로 고칠 필요는 없다.

   ```diff

    import { getMe, postLogout } from '../api/auth.api';

   +import { SESSION_EXPIRED_EVENT } from '../api/client';

    …

   +  // 갱신까지 실패하면 세션은 끝났다 — 화면마다 http_401 을 띄우지 말고 로그인으로 보낸다.

   +  // logout() 의 clearSteCredential·끝 두 줄(:59·:61-62)과 같다. 포커스 effect(:37-47) 다음에 둔다.

   +  useEffect(() => {

   +    const onExpired = () => {

   +      // ste 사본을 안 지우면 이 탭에서 다음에 로그인한 사람이 앞 사람의 ste 토큰을 그대로 쓴다

   +      // (StePrimer.tsx:38 이 사본이 있으면 다시 받지 않는다. 토큰에 만료가 없다 — :6-8).

   +      // 서버 회수(revokeSteCredential)는 부르지 않는다 — 세션이 없어 401 이다(10-14 16:39:16 실측).

   +      clearSteCredential();

   +      setUser(null);

   +      setStatus('unauthenticated');

   +    };

   +    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);

   +    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);

   +  }, []);

   ```

   `clearSteCredential` 은 이미 import 되어 있다(`:5`). 로그인 화면에서도 이벤트가 날 수 있다(포커스 때 `/auth/me`, 틀린 비밀번호의 401). 그때는 이미 `unauthenticated` 라 상태가 바뀌지 않으므로 되풀이되지 않는다. 바로 넘기면 읽던 화면이 로그인 화면으로 바뀐다. 그게 싫다면 같은 이벤트로 「로그인이 만료되었습니다 — 다시 로그인」 배너를 띄우고, 버튼에서 `login(location.pathname)` 을 부르면 된다. 어느 쪽이든 화면마다 고칠 필요가 없다는 점은 같다.



3. **전문가 상세 세 칸에 같은 실패 문구를 넣는다.** `AgentDetail`(`chat.api.ts:331-346`)에 칸을 하나 더한다(요청 5 에서 새로 생긴다).

   ```diff

      error?: string;

   +  /** 보유 지식 목록을 못 받았다(요청 5) — '0건'이 아니다. */

   +  records_error?: string;

    }

   ```

   `AgentFacts.tsx` 끝에 공용 컴포넌트를 더한다. 목록 실패 문구는 `AgentDeepView.tsx:290` 과 같게 쓴다.

   ```tsx

   /** 상세를 못 받았을 때 — 빈 전문가처럼 보이지 않게 한 줄로 말한다(전문가 목록·심의 좌석·시작 패널 공용). */

   export function DetailError({ detail, className = 'pv-empty' }: { detail: AgentDetail; className?: string }) {

     if (detail.error) return <p className={className}>상세를 불러오지 못했습니다({detail.error}).</p>;

     if (detail.records_error)

       return <p className={className}>보유 지식을 불러오지 못했습니다({detail.records_error}) — 보유 지식이 없다는 뜻이 아닙니다.</p>;

     return null;

   }

   ```

   세 칸 모두 보유 지식 목록 블록 바로 뒤에 둔다. 지금 `PersonaBrowser` 가 그 자리에 둔다(`:293`).

   - `PersonaBrowser.tsx:293` 줄을 `<DetailError detail={detail} />` 로 바꾼다.

   - `SeatBrowser.tsx:212`(목록 블록의 `)}`) 다음, `:213` `</>` 앞에 `<DetailError detail={detail} />` 를 넣는다. import(`:5`)에 `DetailError` 를 더한다.

   - `StartPicker.tsx:310`(목록 블록의 `)}`) 다음, `:311` `</>` 앞에 `<DetailError detail={detail} className="sp-warn" />` 를 넣는다. `sp-warn` 은 `:168` 과 같은 클래스다. `StartPicker` 는 아직 `AgentFacts` 를 import 하지 않으므로 `import { DetailError } from './AgentFacts';` 를 더한다.

   - `StartPicker` 가 `pinnedAgent` 로 열리면 상세를 불러오게 한다. `showAgent`(`:115-125`) 다음에 둔다. 저장소의 `npm run lint` 는 `--max-warnings 0` 이라(`frontend/package.json:10`), 같은 모양을 쓰는 `ExpertPicker.tsx:94` 처럼 의존성 경고를 끈다.

     ```tsx

       // 고정된 전문가로 다시 열면 상세도 불러온다 — 안 부르면 키만 든 빈 상자가 남는다.

       useEffect(() => {

         if (pinnedAgent) showAgent(pinnedAgent);

         // eslint-disable-next-line react-hooks/exhaustive-deps

       }, []);

     ```



4. **`AgentDeepView.tsx` — 실패하면 프로필을 그리지 않고 다시 시도 버튼을 준다.**

   ```diff

   -  /** 상세칸이 이미 받아 둔 요약. 있으면 다시 부르지 않는다(/catalog/agent 는 콜드 6~11초). */

   +  /** 상세칸이 이미 받아 둔 요약. 실패본이 아니면 다시 부르지 않는다(/catalog/agent 는 콜드 6~11초). */

    …

      const [detail, setDetail] = useState<AgentDetail | null>(initialDetail ?? null);

   +  const [reload, setReload] = useState(0);

      useEffect(() => {

        // 상세칸 요약이 늦게 도착하면 그걸 쓴다 — 여기서 따로 부른 것과 같은 응답이다.

   -    if (initialDetail) {

   +    // 실패본(error)은 물려받지 않고 다시 부른다.

   +    if (initialDetail && !initialDetail.error) {

          setDetail(initialDetail);

          return;

        }

   +    setDetail(null);

        let live = true;

    …

   -  }, [agent.key, initialDetail]);

   +  }, [agent.key, initialDetail, reload]);

    …

   -  const name = detail?.name || agent.name;

   +  // 실패본의 name 은 키다(chat.api.ts:350) — 그때는 전문가 목록의 이름을 쓴다.

   +  const name = (detail && !detail.error && detail.name) || agent.name;

    …

   -              {detail?.error && <p className="pv-empty">설명을 불러오지 못했습니다({detail.error}).</p>}

   -              {detail && (

   +              {detail?.error && (

   +                <p className="pv-empty">

   +                  설명을 불러오지 못했습니다({detail.error}).{' '}

   +                  <button type="button" className="pv-more" onClick={() => setReload((n) => n + 1)}>다시 시도</button>

   +                </p>

   +              )}

   +              {detail && !detail.error && (

   ```

   이렇게 하면 「따로 쓴 역할 문서가 없습니다」(`:246`)가 실패 문구 밑에 함께 나오지 않는다. 제목도 키 대신 사람 이름이 된다. `pv-more` 는 `AgentFacts.tsx:15` 의 「전체 보기 →」 버튼과 같은 클래스다. `records_error` 만 있는 응답은 프로필이 멀쩡하므로 그대로 물려받는다. 카드 목록은 이 화면이 따로 부르고 실패를 따로 알린다(`:288-291`).



5. **에이전트 서버 `catalog_agent` — 실패를 실패로 돌려준다**(`app.py:4496-4532`).

   ```diff

        try:

   -        sess = _first_dict(_parse_json(await _call(tools, "get_agent_session", {"agent_type": key})))

   +        raw_sess = await _call(tools, "get_agent_session", {"agent_type": key})

   +        sess = _first_dict(_parse_json(raw_sess)) if _result_ok(raw_sess) else {}

            sd = _first_dict(sess.get("data", sess))

   +        if not sd.get("agent_type"):

   +            # 도구 없음(None)·✖ 호출 실패·'agent not found' 평문이 다 여기로 온다. 빈 전문가로 주면

   +            # '역할도 지식도 없는 사람'으로 읽힌다. 적재 때 생긴 자리 행은 agent_type 이 있어 안 걸린다.

   +            raise ValueError(f"no agent session: {str(raw_sess)[:160]!r}")

            out["name"] = sd.get("name") or key

    …

        except Exception as exc:  # noqa: BLE001 — 상세 실패해도 지식 목록은 시도

   +        out["error"] = "session_failed"

            print(f"[catalog] agent session failed: {exc!r}")

        try:

   -        raw = _parse_json(await _call(tools, "list_records", {"agents": [key], "limit": 20}))

   -        recs = raw if isinstance(raw, list) else (

   -            (raw or {}).get("records") or (raw or {}).get("items") or (raw or {}).get("data") or [])

   +        raw_rec = await _call(tools, "list_records", {"agents": [key], "limit": 20})

   +        raw = _parse_json(raw_rec) if _result_ok(raw_rec) else None

   +        if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):

   +            # /catalog/agent/records(:4572)와 같은 판정 — '0건'과 '못 물어봤다'를 뭉개지 않는다.

   +            raise ValueError(f"no record list: {str(raw_rec)[:160]!r}")

   +        recs = raw["items"]

    …

        except Exception as exc:  # noqa: BLE001

   +        out["records_error"] = "records_failed"

            print(f"[catalog] records failed: {exc!r}")

   ```

   `_result_ok`(`:2475`)는 ✖ 표식, `(tool ` 머리, 첫 줄의 `error:`, 실패 봉투를 이미 잡는다. 없는 키의 평문(`Error executing tool …: agent not found: <키>` 꼴)은 첫 줄 검사(`:2472` `^(error|오류)\s*[:：]`)에 안 걸리지만, `agent_type` 검사가 잡는다. AIDataHub 의 성공 응답에는 늘 `agent_type` 이 들어 있다(`mcp_runtime.py:409-410`). 자리 행도 그렇다. 10-15 에 `get_agent_session("dynaforge-report")` 를 불러 `agent_type` 이 오는 것을 확인했다. 실패하면 `records_total` 은 None 으로 남는다(`:4529-4530` 은 성공했을 때만 채운다). 이제 실패가 예외로 바뀌므로 `[catalog] …` 로그도 남는다. AIDataHub `list_records` 는 늘 `{total, count, offset, items}` 를 준다(`mcp_runtime.py:957-961`). 그래서 지워지는 list·`records`·`data` 분기는 운영에서 쓰이지 않는다. 포털 프록시는 응답 본문을 그대로 넘기므로(`backend/app/agent/routes.py:697-699`) 포털 백엔드는 고칠 것이 없다.

   - 기존 테스트에 미치는 영향이다. `tests/test_catalog_deep.py:80-91` 은 그대로 통과한다(`PLAIN_SESSION` 에 `agent_type` 이 있고, 목록 픽스처가 `{total, items}` 다). `tests/test_operator_persona.py:296-311` 도 통과하지만, 목록 픽스처 `{"records": []}`(`:301`)는 새 판정에서 `records_failed` 로 읽힌다. 실제 모양 `{"total": 0, "count": 0, "offset": 0, "items": []}` 로 바꾼다.

   - 회귀 테스트를 하나 더한다(`tests/test_catalog_deep.py` 의 `_stub_records` 를 쓴다).

     ```python

     def test_상세_실패는_빈_전문가가_아니라_실패로_준다(monkeypatch):

         def handler(name, args):

             if name == "get_agent_session":

                 return "Error executing tool get_agent_session: agent not found: zz"   # 평문 실패

             return "✖ 도구 list_records 호출 실패: backend session down"

         _stub_records(monkeypatch, handler)

         out = asyncio.run(a.catalog_agent(a.AgentDetailRequest(key="zz")))

         assert out["error"] == "session_failed" and out["records_error"] == "records_failed"

         assert out["records_total"] is None

     ```



6. **선택(정책 결정) — 쓰는 동안에는 8시간에 끊기지 않게 한다.** 담당은 포털 백엔드다. `/auth/refresh`(`session.py:246` 옆)가 갱신 토큰도 다시 발급하면 된다(`cookies.set_session_cookies(…, refresh=jwt_service.issue_refresh(principal))`, `cookies.py:33`·`backend/app/auth/jwt_service.py:86`). CSRF 쿠키는 값은 그대로 두고 수명만 늘린다(`cookies.set_csrf_cookie(…, token=<지금 쿠키 값>)`, `cookies.py:54`). 그러면 계속 쓰는 사람은 로그인 8시간에 끊기지 않는다. 갱신 때 원장을 다시 보는 검사(`backend/tests/test_admin_ledger_only.py:147-157`)는 그대로 돈다. 절대 수명 8시간을 유지할지는 보안 정책이므로 담당이 정한다. 이것 없이 1~2 만 해도 「401 만 뜨는 화면」 문제는 풀린다.



**왜** — 세션이 끝난 사람은 지금 「다시 시도」·「잠시 후」를 따라 해도 계속 실패하고, 직접 로그아웃해야 풀린다(10-14 실측: 14:18 에 끝난 세션이 16:39 에 스스로 로그아웃할 때까지 이어졌다). 상세를 못 받은 전문가는 「역할도 지식도 없는 사람」으로 보여서, 사용자가 전문가를 고르거나 심의 좌석에 앉힐 때 잘못 판단하게 된다.



**확인**

- 로그인 만료(포털 반영과 프런트 빌드가 끝난 뒤). 먼저 서빙 중인 번들에 변경이 들어갔는지 본다.

  ```bash

  grep -l 'hwax:session-expired' ~/Projects/HWAXPortal/frontend/dist/assets/*.js

  grep -l '보유 지식을 불러오지 못했습니다' ~/Projects/HWAXPortal/frontend/dist/assets/*.js

  ```

  다음은 화면 확인이다. 브라우저 개발자 도구(Application → Cookies)에서 `hwax_session`·`hwax_csrf` 쿠키를 지운다. 새로 고치지 말고 전문가 목록에서 전문가 하나를 누른다. 10-14 와 같은 상태(CSRF 쿠키가 없어 갱신이 403)가 된다. `/login` 으로 넘어가고 Local Storage 의 `ste.token` 이 지워져 있으면 된다. SSO 로그인 뒤 같은 경로로 돌아오면 끝이다. 하루 `POST /auth/refresh` 403 건수도 본다(10-14 은 124건, 그중 63건이 `/systems/heax-hub/launch` 401 바로 뒤). 만료된 탭이 로그인 화면으로 넘어가면 `SsoPrimer`(`AppShell.tsx:27`)가 함께 내려가 주기 호출이 멈춘다. 그래서 그 몫이 탭마다 한 번으로 줄 것으로 본다. 로그인 화면에서도 창 포커스 때 `/auth/me`(`AuthContext.tsx:37-47`)는 계속 불리므로 0 이 되지는 않는다(예상이며 미확인).

  ```bash

  grep -c "$(date +%F)T.*\"POST /auth/refresh\" 403" ~/Projects/HWAXPortal/infra/data/nginx-access.log

  ```

- 상세 실패(에이전트 서버 반영 뒤, cae00 에서). 그룹은 10-14 전수 조사 때 만든 `~/kc-check/groups.json` 의 caeg(29개)를 쓴다.

  ```bash

  G=$(jq -c .caeg ~/kc-check/groups.json); N=$(jq -c '.caeg - ["plat:aidatahub"]' ~/kc-check/groups.json)

  q(){ curl -s --noproxy '*' -X POST 127.0.0.1:9009/catalog/agent -H 'Content-Type: application/json' \

         -d "{\"key\":\"$1\",\"groups\":$2}" | jq -c '{error,records_error,records_total}'; }

  q zz-no-such-expert "$G"   # 기대 error "session_failed"                 (지금 error null)

  q cam-aa-process   "$N"    # 기대 session_failed · records_failed · null (지금 error null)

  q cam-aa-process   "$G"    # 기대 error null · records_total 64          (정상은 그대로)

  q dynaforge-report "$G"    # 기대 error null                             (자리 행은 실패가 아니다)

  ```

  에이전트 서버 테스트(`pytest -q tests/test_catalog_deep.py tests/test_operator_persona.py`)도 통과해야 한다. 화면에서 상세 실패를 일부러 일으키는 방법은 미확인이다. 일반 포털 권한에서는 `feat:expert-chat` 이 `plat:aidatahub` 를 함께 주므로, 게이트웨이의 ai-data-hub 가 끊겼을 때만 생긴다. 세 칸의 실패 문구는 코드 리뷰로 확인한다.



---



## K3. 긴 카드가 6만 자에서 잘리고 나머지를 볼 수 없다



대상 — HWAXAgentServer · HWAXPortal(요청 1~8) · MaterialTwinWeb · AIDataHub 동기화 규칙(요청 9). 담당 판단 — 에이전트서버 개발(총량 필드·이어 읽기 위치) · 포털 개발(안내문·프록시 필드·「다음 부분 보기」) · MaterialTwinWeb 개발과 AIDataHub 데이터 담당(재료 카드 본문).

기준 — HWAXAgentServer origin/main `c4e4823` · HWAXPortal origin/main `90147ac` · AIDataHub `b401f88` · MaterialTwinWeb `6e45b40`(cae00 `~/Projects/HEAXHub/var/integration_workspaces/materialtwin-web/upstream` 사본. upstream 최신판은 미확인). 아래 `파일:줄` 은 이 커밋 기준이다. cae00 에 떠 있는 판(포털 `e6a8e52` · 에이전트서버 `7644284`)도 이 부분 코드는 같다(`git diff` 로 확인했다. 에이전트서버는 `RecordRequest`~`catalog_record` 가 글자까지 같다. 포털은 `AgentDeepView.tsx`·`chat.api.ts` 가 같고 `routes.py` 는 다른 곳만 다르다).



**지금** — 에이전트서버 `_record_view` 는 본문 절을 60,000자까지만 싣고 `truncated=True` 로 멈춘다(`app.py:4587` `RECORD_TEXT_MAX = 60000`, `app.py:4605-4616`). 카드 전체가 몇 절·몇 자인지는 응답에 없다. 요청은 `id`·`groups` 뿐이라 뒤를 달라고 할 길도 없다(`app.py:4580-4582` `RecordRequest`). 포털 프록시도 `id` 만 받아 넘긴다(`backend/app/agent/routes.py:729-730`, `:745`). 화면 안내문은 표가 없어도 표 문구를 붙인다(`frontend/src/components/chat/AgentDeepView.tsx:51-53` `표는 앞 {nf.format(rec.table?.rows.length ?? 0)}행입니다`). DOC 카드는 `table=null` 이라 「표는 앞 0행입니다」가 된다. 읽기 칸에는 더 보기 버튼이 없다(`AgentDeepView.tsx:54-59`, `:326`). 뒤가 없는 것은 아니다. AIDataHub `get_record` 가 이미 절 전부를 주고(`api_server/src/api/mcp_runtime.py:1024-1047` `"content": rec.content`), 에이전트서버가 6만 자 뒤를 버린다. 상한과 안내문은 처음 들어온 2026-09-11 판 그대로다(에이전트서버 `0f0c9c1`, 포털 `26a4448`).



- 실측(2026-10-14, 전원 796명 sweep). 첫 카드 778장을 열었고 297장(38%)이 잘렸다. 297장 모두 DOC·표 없음이라 전부 「표는 앞 0행입니다」가 보인다. 잘린 표와 잘린 JSON 원문 보기는 0장이다.

- 예. cam-aa-process 첫 카드 `DOC-CCT-PWR-2026-0000002348` 은 원문 119절·258,703자 중 30절·60,000자(약 23%)만 보인다(AIDataHub `GET /api/records/{id}` 의 `content.sections` 로 쟀다. 10-15 에 다시 쟀다).

- 상한은 대개 절 중간에서 걸린다. 위 카드는 30번째 절(2,251자)의 1,039자째에서 끊긴다. 절 번호만 넘겨 이어 읽으면 그 절 앞 1,039자를 되풀이하거나 뒤 1,212자를 건너뛴다. 그래서 아래 요청은 절 번호와 그 절 안 글자 위치를 함께 넘긴다.

- 재료 카드는 원천에서 이미 잘려 온다. material-twin-analyst 앞 300장(전체 2,729장) 중 52장이 6만 자를 넘고, 52장 모두 절 하나가 60,038자다. 뒤 38자는 본문이 아니다. MaterialTwinWeb 이 붙인 표지 `… (본문 절단 — 전체는 content.properties 참조)` 다(`backend/app/routers/hub_export.py:28` `_BODY_MAX_CHARS = 60_000`, `:79-80`). 전체 값은 `content.properties`(표본 25~368건, JSON 72,047~807,029자)에 있다. 그런데 읽기 칸은 절이 있으면 이 키를 버린다(`app.py:4631`. JSON 원문 보기는 절도 표도 없을 때만 나온다). 이 카드들은 요청 1~8 로도 뒤를 못 본다. 요청 9 가 따로 필요하다.

- 사용자에게 보이는 것은 「본문이 길어 앞부분만 싣습니다 — 표는 앞 0행입니다.」 한 줄과 본문 앞부분이다. 얼마나 잘렸는지도, 나머지를 읽는 방법도 나오지 않는다. 전문가 챗에서는 모델이 `get_record_sections` 로 뒤를 읽을 수 있다(`app.py:1246`, AIDataHub `mcp_runtime.py:1063` 의 `limit`·`offset`). 막힌 것은 읽기 칸이다.



**요청**



1. 에이전트서버 — `RecordRequest` 가 이어 읽을 위치를 받는다(`app.py:4580-4582`).

```diff

 class RecordRequest(BaseModel):

     id: str

     groups: list[str] = []

+    # 다음 부분 보기 — 앞 응답의 next 를 그대로 돌려받는다(절 번호 · 그 절 안 글자 위치).

+    section_offset: int = 0

+    char_offset: int = 0

```



2. 에이전트서버 — `_record_view` 가 총량(`total_sections`·`total_chars`)과 다음 위치(`next`)를 돌려준다(`app.py:4598`, `:4605-4616`, `:4631`). 위치를 주지 않으면 첫 쪽은 지금과 글자까지 같다(cae00 실데이터로 흉내 내 확인했다. 30절·60,000자·`truncated=True`).

```diff

-def _record_view(rec: dict) -> dict:

+def _record_view(rec: dict, section_offset: int = 0, char_offset: int = 0) -> dict:

@@

-    budget = RECORD_TEXT_MAX

-    for s in content.get("sections") or []:

-        s = _first_dict(s)

-        text = str(s.get("content_text") or s.get("text") or "")

-        if budget <= 0:

-            out["truncated"] = True

-            break

-        if len(text) > budget:

-            text, out["truncated"] = text[:budget], True

-        budget -= len(text)

+    flat = list(_flat_sections(content.get("sections"), refs))   # K1 이 푼 절(블록·자식 절 포함)

+    secs, texts = [s for s, _ in flat], [t for _, t in flat]      # 이어 읽기는 이 목록 위에서 돈다

+    # 얼마나 잘렸는지 말하려면 총량이 있어야 한다. next 가 None 이면 절은 끝까지 실었다.

+    out.update(total_sections=len(secs), total_chars=sum(map(len, texts)), next=None)

+    budget = RECORD_TEXT_MAX

+    for i in range(section_offset, len(secs)):

+        if budget <= 0:

+            out["truncated"], out["next"] = True, {"section": i, "char": 0}

+            break

+        start = char_offset if i == section_offset else 0

+        s, text = secs[i], texts[i][start:start + budget]

+        budget -= len(text)

         out["sections"].append({"id": str(s.get("section_id") or "")[:40], "title": str(s.get("title") or "")[:200],

                                 "level": s.get("level") if isinstance(s.get("level"), int) else 1, "text": text})

+        if start + len(text) < len(texts[i]):

+            # 상한은 대개 절 중간에서 걸린다 — 절 번호만 넘기면 그 절 앞을 되풀이하거나 뒤를 건너뛴다.

+            out["truncated"], out["next"] = True, {"section": i, "char": start + len(text)}

+            break

@@

-    if not out["sections"] and out["table"] is None:

+    if not secs and out["table"] is None:  # 끝을 넘긴 section_offset 이 JSON 원문 보기로 바뀌지 않게

@@ JSON 원문 폴백 안, text 를 만든 줄 바로 뒤

+        out.update(total_sections=1, total_chars=len(text))  # 비워 두면 SIM 카드가 '빈 카드'로 판정된다(요청 3)

```



   - **K1 위에 얹는다.** `_flat_sections`·`refs` 는 K1 요청 1 이 만든다. 그래서 `total_sections`·`total_chars`·`next` 는 푼 절 기준 값이다. K1 없이 이것만 넣는다면 `flat` 두 줄 대신 종전 꼴(`_first_dict(s)` · `content_text`/`text`)로 목록을 만든다.

   - **(선택) 끊는 자리.** 글자 위치로 자르므로 K1 이 만든 마크다운 표·코드펜스·`$$` 수식 한가운데서 끊길 수 있다. 「다음 부분 보기」로 같은 절에 이어 붙이면 다시 닫히지만, 첫 쪽 끝 절은 펜스가 닫히지 않은 채 그려진다(TextBlock 이 어떻게 그리는지는 미확인). 거슬리면 절단점을 그 절 안의 마지막 빈 줄(`



`)로 당긴다.



3. 에이전트서버 — `catalog_record` 가 위치를 넘긴다(`app.py:4650`). 다음 부분을 받을 때마다 `get_record` 로 카드 전체를 다시 받는다. 지금 첫 열기와 같은 비용이라 따로 `get_record_sections` 를 쓸 필요는 없다. 음수는 목록과 같은 꼴로 막는다(`catalog_agent_records` 의 `max(0, …)`). K1 요청 2(빈 카드면 RAG 절로 다시 그리기)와 같은 줄이라 둘을 합친 꼴로 쓴다. 빈 카드 판정은 쪽이 아니라 카드 전체 값(`total_chars == 0`)으로 하고, RAG 절로 다시 그릴 때도 같은 위치를 넘겨 `total_*`·`next` 까지 옮긴다.

```python

    so, co = max(0, req.section_offset), max(0, req.char_offset)

    view = _record_view(rec, so, co)

    if view["table"] is None and view["total_chars"] == 0:   # 쪽이 아니라 카드 전체로 판정한다

        raw = await _call(tools, "get_record_sections", {"record_id": rid})

        if isinstance(raw, str) and raw.strip() and not _tool_text_ok(raw):

            return {"error": "record_failed", "id": rid}       # 조회 실패를 '빈 카드'로 보이지 않는다

        rows = [r for r in _parse_json_multi(raw) if isinstance(r, dict) and r.get("content_text")]

        alt = (_record_view({**rec, "content": {"sections": rows}}, so, co) if rows

               else {"sections": [], "truncated": False, "total_sections": 0, "total_chars": 0, "next": None})

        view.update({k: alt[k] for k in ("sections", "truncated", "total_sections", "total_chars", "next")})

    return view

```



4. 포털 백엔드 — 프록시가 두 필드를 넘긴다(`backend/app/agent/routes.py:729-730`, `:745`). 목록 프록시(`routes.py:707`, `:723`)와 같은 꼴이다. 테스트 기대값도 같이 바꾼다(`backend/tests/test_catalog_deep_route.py:54`). 같은 경로를 부르는 `backend/tests/test_agent_unary_timeout.py:32` 는 기본값 0 이라 그대로 통과한다.

```diff

 class CatalogRecordRequest(BaseModel):

     id: str = Field(min_length=1, max_length=120)

+    section_offset: int = Field(default=0, ge=0, le=1_000_000)

+    char_offset: int = Field(default=0, ge=0, le=2_000_000)

@@ async def catalog_record(

-                              json={"id": body.id, "groups": principal.groups})

+                              json={**body.model_dump(), "groups": principal.groups})

```

```diff

-        assert seen[1] == ("/catalog/record", {"id": "DOC-1", "groups": grp})

+        assert seen[1] == ("/catalog/record", {"id": "DOC-1", "section_offset": 0, "char_offset": 0, "groups": grp})

```



5. 포털 프론트 — 타입과 호출(`frontend/src/api/chat.api.ts:384-398`, `:423-428`). 새 필드는 선택이다. `postJson` 이 `{ ...fallback, ...응답 }` 으로 합치므로 에이전트서버가 먼저 안 바뀌어도 화면은 지금처럼 돈다.

```diff

   truncated: boolean;

+  /** 원문 총량 — 에이전트서버가 아직 안 주면 없다. */

+  total_sections?: number;

+  total_chars?: number;

+  /** 다음 부분 위치 — null 이면 절은 끝까지 실었다. */

+  next?: { section: number; char: number } | null;

   error?: string;

 }

@@

-export function fetchRecord(id: string): Promise<RecordView> {

-  return postJson('/agent/catalog/record', { id }, {

+export function fetchRecord(id: string, at?: { section: number; char: number }): Promise<RecordView> {

+  return postJson('/agent/catalog/record', { id, section_offset: at?.section ?? 0, char_offset: at?.char ?? 0 }, {

```



6. 포털 프론트 — 안내문과 버튼(`AgentDeepView.tsx:39`, `:51-59`). 표 문구는 표가 실제로 잘렸을 때만 붙인다(`total_rows > rows.length`). 본문은 총량 대비로 말한다. 에이전트서버가 아직 총량을 안 주면 「본문이 길어 앞부분만 싣습니다.」만 나온다. 버튼은 목록 쪽 넘김과 같은 `pv-chip pv-chip-btn` 이다(`AgentDeepView.tsx:276`). 실패 문구는 이 파일의 「…불러오지 못했습니다(…)」 꼴을 따른다.

```diff

-function RecordReader({ rec }: { rec: RecordView }) {

+function RecordReader({ rec, onMore, moreLoading, moreError }: {

+  rec: RecordView; onMore?: () => void; moreLoading?: boolean; moreError?: string | null;

+}) {

+  // 무엇이 잘렸는지 따로 말한다 — 표가 없는 카드에 「표는 앞 0행」을 붙이지 않는다.

+  const shown = rec.sections.reduce((n, s) => n + s.text.length, 0);

+  const cutTable = rec.table && rec.table.total_rows > rec.table.rows.length ? rec.table : null;

+  const note = [

+    rec.next && rec.total_chars

+      ? `본문 ${nf.format(rec.total_sections ?? 0)}절·${nf.format(rec.total_chars)}자 중 앞 ${nf.format(shown)}자(약 ${Math.floor((shown * 100) / rec.total_chars)}%)를 싣습니다.`

+      : cutTable ? '' : '본문이 길어 앞부분만 싣습니다.',

+    cutTable ? `표는 ${nf.format(cutTable.total_rows)}행 중 앞 ${nf.format(cutTable.rows.length)}행입니다.` : '',

+  ].filter(Boolean).join(' ');

   return (

@@

-      {rec.truncated && (

-        <p className="dv-note">본문이 길어 앞부분만 싣습니다 — 표는 앞 {nf.format(rec.table?.rows.length ?? 0)}행입니다.</p>

-      )}

+      {rec.truncated && <p className="dv-note">{note}</p>}

       {rec.sections.map((s, i) => (

         …

       ))}

+      {rec.next && onMore && (

+        <button type="button" className="pv-chip pv-chip-btn" disabled={moreLoading} onClick={onMore}>

+          {moreLoading ? '불러오는 중…' : '다음 부분 보기 ▼'}

+        </button>

+      )}

+      {moreError && <p className="pv-empty">다음 부분을 불러오지 못했습니다({moreError}).</p>}

```



7. 포털 프론트 — 심층 보기가 받은 부분을 이어 붙인다(`AgentDeepView.tsx:152-167`, `:326`). 절 중간에서 이어 받은 첫 조각은 앞 절에 붙인다. 그래야 제목이 두 번 나오지 않는다. 보낸 위치가 지금의 `next` 와 같을 때만 붙인다. 그사이 같은 카드를 다시 열었으면 새 첫 쪽 뒤에 엉뚱한 쪽이 붙기 때문이다.

```diff

   const [recLoading, setRecLoading] = useState(false);

+  const [moreLoading, setMoreLoading] = useState(false);

+  const [moreError, setMoreError] = useState<string | null>(null);

   const selRef = useRef<string | null>(null);

   const openRecord = useCallback((id: string) => {

     selRef.current = id;

     setSelId(id);

     setRec(null);

     setRecLoading(true);

+    setMoreLoading(false);

+    setMoreError(null);

     …

   }, []);

+  const loadMore = useCallback(() => {

+    if (!rec?.next) return;

+    const id = rec.id;

+    const at = rec.next;

+    setMoreLoading(true);

+    setMoreError(null);

+    void fetchRecord(id, at).then((more) => {

+      if (selRef.current !== id) return;

+      setMoreLoading(false);

+      if (more.error) {

+        setMoreError(more.error);

+        return;

+      }

+      setRec((cur) => {

+        if (!cur || cur.id !== id || cur.next?.section !== at.section || cur.next?.char !== at.char) return cur;

+        const secs = [...cur.sections];

+        const add = [...more.sections];

+        if (at.char > 0 && secs.length && add.length) {

+          const last = secs.pop()!;

+          secs.push({ ...last, text: last.text + add.shift()!.text });

+        }

+        return { ...cur, sections: [...secs, ...add], next: more.next ?? null, truncated: more.truncated };

+      });

+    });

+  }, [rec]);

@@

-                {rec && !rec.error && <RecordReader rec={rec} />}

+                {rec && !rec.error && (

+                  <RecordReader rec={rec} onMore={loadMore} moreLoading={moreLoading} moreError={moreError} />

+                )}

```



8. 반영 순서. 에이전트서버(1~3)를 먼저 올리고 포털(4~7)을 올린다. 반대로 올려도 깨지지 않는다. 에이전트서버 `RecordRequest` 는 모르는 필드를 그냥 무시하고(pydantic 기본), `next` 가 없으면 버튼이 안 보인다. 안내문은 포털만 올라가도 「본문이 길어 앞부분만 싣습니다.」로 바뀐다. 포털은 프론트를 다시 빌드해야 반영된다(지금 nginx 가 내주는 번들은 `frontend/dist/assets/index-VgVFfFzR.js`(2026-10-11 17:17)이고, 「표는 앞」 문구가 들어 있다).



9. 재료 카드 — 1~8 로는 뒤가 안 보인다. MaterialTwinWeb 이 허브로 내보낼 때 본문을 6만 자에서 자르고 표지를 붙인다(`backend/app/routers/hub_export.py:28`, `:79-80`). AIDataHub 동기화는 그 `body` 를 절 하나(「본문」)로 싣고 전체 값은 `content.properties` 로만 남긴다(`config/sync_sources.yml:159` materialtwin, `:180` `body_field: body`, `:190-192` `content_extra_fields`, `api_server/src/api/services/sync_svc.py:276-280`, `:285`). 둘 중 하나를 정해 주십시오.

   - (가) 원천에서 고친다(권함). MaterialTwinWeb 이 본문을 자르지 않고 6만 자 이하 절 여러 개(`sections`)로 내보낸다. AIDataHub materialtwin 규칙에는 `sections_field: sections` 를 더한다(`sync_svc.py:265-269` 가 이미 받는다). 그러면 1~8 의 이어 읽기로 끝까지 보이고 표지 문구도 사라진다. 자른 까닭이 허브 문서 크기라서(`hub_export.py:27` 주석) 크기 한도는 MaterialTwinWeb 담당이 정한다.

   - (나) 읽기 칸에서 고친다. 에이전트서버 `_record_view` 가 그리지 않는 `content` 키(`properties`)를 맨 끝 「원문(JSON)」 절로 `secs` 에 더해 이어 읽기에 태운다. 다만 표본의 `properties` JSON 이 72,047~807,029자라 열 몇 번을 눌러야 하고, 사람이 읽을 꼴이 아니다.



**왜** — 열어 본 카드 778장 중 297장(38%)은 사용자가 앞부분만 본다. 그런데 화면은 전부인지, 얼마나 남았는지 말하지 않는다. 안내문이 없는 표를 말하니 사용자가 안내문 자체를 믿지 않게 된다. 재료 카드는 본문 끝 표지가 「content.properties 참조」라고 하는데, 화면 어디에도 그 값이 없다. 코퍼스 전체로 보면 절이 있는 카드 59,033장 중 8,534장이 6만 자를 넘는다(검증 단계에서 AIDataHub 를 읽기 전용 SQL 로 쟀다. 이번에는 다시 재지 않았다).



**확인**



1. 에이전트서버 반영 뒤 cae00 에서 읽기 전용 호출로 끝까지 따라가 본다. 이어 받은 글자 수의 합이 원문 총량과 같아야 한다.

```bash

python3 - <<'EOF'

import json, urllib.request

def rec(rid, at=None):

    body = {"id": rid, "groups": ["plat:aidatahub"], **({"section_offset": at["section"], "char_offset": at["char"]} if at else {})}

    req = urllib.request.Request("http://127.0.0.1:9009/catalog/record", json.dumps(body).encode(), {"Content-Type": "application/json"})

    return json.load(urllib.request.urlopen(req, timeout=120))

for rid in ("DOC-CCT-PWR-2026-0000002348", "DOC-MX-MAT-2026-0000000220"):

    r = rec(rid); total, got, calls = r["total_chars"], 0, 0

    while True:

        got += sum(len(s["text"]) for s in r["sections"]); calls += 1

        if not r["next"]: break

        r = rec(rid, r["next"])

    print(rid, total, got, calls)

EOF

# 기대: DOC-CCT-PWR-2026-0000002348 258703 258703 5

#       DOC-MX-MAT-2026-0000000220 60038 60038 2   ← 뒤 38자는 MaterialTwinWeb 표지다. 9 가 들어가면 이 줄의 숫자가 바뀐다.

```

2. 테스트. 에이전트서버 `tests/test_catalog_deep.py` 가 그대로 통과한다(위치를 안 주면 DOC·DATA·SIM 결과가 지금과 같다). 여기에 긴 카드 경우를 하나 더한다. 25,000자 절 5개면 `next` 를 따라 3번에 125,000자를 받고, 이어 붙인 절이 원문과 같아야 한다(이 계산은 cae00 실데이터로 흉내 내 확인했다. 위 두 카드도 이어 붙인 본문이 원문과 글자까지 같았다). 포털 `backend/tests/test_catalog_deep_route.py` 가 통과하고, `section_offset`·`char_offset` 을 0 이 아닌 값으로 보내 그대로 넘어가는 경우가 하나 더 있어야 한다.

3. 화면. 전문가 목록에서 cam-aa-process 심층 보기를 열고 첫 카드를 본다. 안내문이 「본문 119절·258,703자 중 앞 60,000자(약 23%)를 싣습니다.」이고 「표는」 문구가 없어야 한다. 「다음 부분 보기」를 한 번 누르면 30번째 절 뒤 1,212자가 같은 절에 이어 붙어야 한다. 그 절 제목이 두 번 나오면 안 된다. 네 번 누르면 안내문과 버튼이 사라져야 한다. material-twin-analyst 의 `DOC-MX-MAT-2026-0000000220` 은 한 번 누르면 같은 「본문」 절 끝에 표지 한 줄이 붙고 버튼이 사라진다. 1~8 은 여기까지다.

4. 재료 카드(요청 9 뒤). (가) 를 골랐으면 다음 동기화 뒤 AIDataHub 원본에 표지가 없어야 한다.

```bash

curl -s --noproxy '*' http://127.0.0.1:8001/api/records/DOC-MX-MAT-2026-0000000220 | python3 -c "import json,sys; c=json.load(sys.stdin)['content']; t=''.join(s.get('content_text') or '' for s in c['sections']); print(len(c['sections']), len(t), '본문 절단' in t)"

# 기대: 절 여러 개 · 60,038자보다 길다 · False   (지금: 1 60038 True)

```

   (나) 를 골랐으면 읽기 칸 맨 끝에 「원문(JSON)」 절이 나오고 이어 읽기로 `properties` 끝까지 보여야 한다.



**미확인**

- 에이전트서버 게이트웨이 결과 상한 `CATALOG_RESULT_MAX`(기본 2,000,000자, `app.py:644`)를 넘는 카드가 있는지는 미확인이다. 그런 카드는 지금도 처음 열 때부터 `record_failed` 로 끝날 것이다(`_cap` 이 JSON 을 중간에서 자른다. 코드로만 판단했고 실측은 안 했다). 이 요청으로도 풀리지 않는다. 있으면 그 카드만 `get_record_sections(limit, offset)`(`mcp_runtime.py:1063`)로 나눠 받아야 한다.

- 표가 잘리는 경우(`RECORD_ROWS_MAX` 200행, `app.py:4624-4625`)의 안내문은 코드로만 확인했다. 이번 sweep 에서 표 카드가 잘린 사례는 0장이다.

- JSON 원문 보기(`app.py:4631-4636`)도 6만 자에서 자르지만 `next` 를 주지 않는다. sweep 에서는 0장이라 이번 범위에서 뺐다.

- 코퍼스 8,534장 중 재료 카드처럼 원천에서 잘린 카드가 몇 장인지는 미확인이다. material-twin-analyst 밖에도 같은 표지가 있는지는 재지 않았다.

- MaterialTwinWeb upstream 최신판이 cae00 사본(`6e45b40`, 2026-09-05)과 같은지는 미확인이다. AIDataHub 6시간 동기화(`config/sync_sources.yml:171`)가 이미 있는 레코드의 `content` 를 덮어쓰는지도 미확인이다.



---



## K4. 챗 시작 패널이 미리보기 20건을 보유 지식 수로 보인다



대상 — **HWAXPortal** frontend(포털 개발) · 에이전트서버·포털 백엔드는 고칠 것이 없다

기준 — 포털 origin/main `90147ac` · 에이전트서버 origin/main `c4e4823`. 아래 `파일:줄` 은 각 origin/main 기준이다. 포털 프런트 파일은 `frontend/src/` 아래다(`components/chat/`·`api/`·`pages/`·`styles/`).



**지금** — 챗의 「전문가·도구 고르고 시작」 패널(`ChatPage.tsx:167` `StartPicker`)에서 전문가 목록 열기 버튼으로 전문가를 고르면 목록 창이 닫힌다(`StartPicker.tsx:331` `onPick={browse === 'helper' ? addHelper : pickFromOrg}`, `PersonaBrowser.tsx:105-108`). 그다음 패널 아래 상세칸이 `pickFromOrg` → `showAgent` → `fetchAgentDetail` 로 그려진다(`StartPicker.tsx:146-149`, `:115-124`, 상세칸 블록 `:277-314`). 이 상세칸의 지식 제목은 `detail.records.length` 를 센다(`StartPicker.tsx:298-300`). 그런데 `records` 는 에이전트서버가 `list_records` 를 `"limit": 20` 으로 불러 온 미리보기다(`app.py:4518`). 실제 수는 `records_total` 로 따로 온다(`app.py:4529-4530`, docstring `:4489`). 포털 프록시는 이 응답을 그대로 넘긴다(`backend/app/agent/routes.py:699`). 타입 주석도 같은 뜻이다(`chat.api.ts:337-339`). 그래서 서버 쪽은 고칠 것이 없다.



전문가 목록 상세칸과 심의 좌석 상세칸은 이미 `AgentFacts.RecordsHeading` 으로 옮겨서 `records_total` 을 쓴다(`AgentFacts.tsx:4-20`, `PersonaBrowser.tsx:282`, `SeatBrowser.tsx:205`). `RecordsHeading` 주석이 이 버그를 그대로 적어 두었다(`AgentFacts.tsx:5` 「예전엔 '보유 지식 20건'이라 2,729건인 사람도 20건으로 읽혔다」). 2026-09-11 변경 안내도 「상세칸의 '보유 지식' 수가 실제 수로 나옵니다」라고 사용자에게 알렸다(`backend/config/changelog.yaml:1245`). StartPicker 만 옮겨지지 않았다. `frontend/src` 에서 「보유 지식 (」로 세는 곳은 여기 한 곳뿐이다(`git grep '보유 지식 ('`). 이 줄은 `b1a5462`(2026-07-28) 뒤로 바뀌지 않았다(`git blame`).



사용자가 보는 화면은 이렇다. 전문가 목록에서 cam-aa-process 를 열면 「보유 지식 64건 · 앞 20건」이 보인다. 그 전문가를 고르면 시작 패널에는 「보유 지식 (20건)」이 뜬다. material-twin-analyst 는 2,729건인데 20건으로 보인다. 10-15 에 에이전트서버 `/catalog/agent` 를 읽기만 해서 다시 쟀다. cam-aa-process 는 미리보기 20·전체 64, material-twin-analyst 는 20·2,729, cam-system-architecture 는 6·6 이다. 10-14 전수 점검(796명)에서 카드가 있는 전문가는 778명이고, 그중 761명이 20건을 넘는다. 이 761명은 모두 시작 패널에서 20건으로 보인다. 모든 전문가의 미리보기 수는 min(20, 전체 수)와 같았다. 목록에 보이는 20건의 제목 자체는 맞고, 호출 오류도 0건이었다. 틀린 것은 제목의 숫자뿐이다.



지금 nginx 가 내주는 번들(`frontend/dist/assets/index-VgVFfFzR.js`, 10-11 빌드, `.build-src` = `e6a8e52:frontend`)에도 `보유 지식 (",J.records.length,"건)` 이 들어 있다. 같은 번들에 `RecordsHeading` 의 `보유 지식 ",n.toLocaleString("ko-KR")` 도 있어, 한 흐름 안에서 두 수가 다르게 보인다. `StartPicker.tsx`·`AgentFacts.tsx`·`chat.api.ts` 는 `e6a8e52` 와 origin/main 사이에 바뀌지 않았다. 따라서 지금 화면이 origin/main 의 동작과 같다.



**요청**

1. `StartPicker.tsx:298-300` 의 제목을 `RecordsHeading` 과 같은 계산과 같은 문구로 바꿔 주십시오. `RecordsHeading` 컴포넌트를 그대로 꽂지는 마십시오. 이 컴포넌트는 `onMore` 를 꼭 받아야 하고(`AgentFacts.tsx:6`), 「전체 보기 →」 버튼과 `pv-*` 제목 모양을 함께 그리기 때문에 `sp-*` 패널과 맞지 않는다. 숫자 계산만 맞추면 된다.



   ```diff

                  {detail.records.length > 0 && (

                    <>

   -                  <div className="sp-sub sp-dim">보유 지식 ({detail.records.length}건)</div>

   +                  <div className="sp-sub sp-dim">

   +                    보유 지식 {(detail.records_total ?? detail.records.length).toLocaleString('ko-KR')}건

   +                    {(detail.records_total ?? 0) > detail.records.length && (

   +                      <span className="sp-dim"> · 앞 {detail.records.length}건</span>

   +                    )}

   +                  </div>

                      <ul className="sp-detail-list sp-scroll">

   ```



   `records_total` 이 `null` 일 수 있다. 구 서버이거나 목록 호출이 실패한 경우다(`app.py:4495` 기본값). 그러면 지금처럼 미리보기 수만 보인다. 조건 `(detail.records_total ?? 0) > detail.records.length` 는 `RecordsHeading` 의 `total > preview`(`AgentFacts.tsx:7-8`, `:13`)와 같은 값을 낸다. `records_total` 이 `null` 이면 둘 다 거짓이다. 안쪽 `<span className="sp-dim">` 은 이 파일이 이미 쓰는 꼴이다(`StartPicker.tsx:176`, `:305`). `.sp-dim`(`chatpage.css:1233`)은 weight 400 이고 `.sp-sub`(`:1234`)는 600 이다. 그래서 「· 앞 20건」만 옅게 보이고, `RecordsHeading` 의 `pv-dim` 과 같은 역할을 한다. 이 문구를 보는 테스트는 없다. 프런트 테스트는 `frontend/e2e/ui.spec.ts` 하나이고, 거기에 이 문자열이 없다. `records_total?: number | null` 이라 `??` 뒤는 `number` 다. 다만 빌드와 타입 검사는 돌려 보지 않았다(미확인).

2. (선택) 「전체 보기 →」 버튼. 지금 StartPicker 에는 `AgentDeepView` 가 연결돼 있지 않다. 전문가 목록 상세칸에는 이미 「⤢ 전체 화면으로 보기」와 「전체 보기 →」가 있다(`PersonaBrowser.tsx:255-257`, `:282`). 그래서 고르기 전에는 전체 목록을 볼 수 있다. 시작 패널에도 넣는다면 `PersonaBrowser.tsx:68`, `:301-309` 와 같은 방식으로 만든다. `deep` 상태를 두고, `const agentObj = pool.find((a) => a.key === agentSel)` 가 있을 때만 `<AgentDeepView agent={agentObj} initialDetail={detail} onClose={() => setDeep(false)} />` 를 연다. 이 조회는 `nameOf` 와 같은 꼴이다(`StartPicker.tsx:57`). `AgentDeepView.tsx:19-30` 에 따르면 꼭 넘길 것은 `agent`·`onClose` 이고, `path`·`actions`·`onAsk` 는 빼도 된다. 버튼은 1 의 제목 옆에 `sp-*` 모양으로 단다. 이때도 `RecordsHeading` 을 그대로 쓰면 `pv-detail-h` 제목 모양이 `sp-*` 패널에 섞인다. 어떻게 보이는지는 확인하지 않았다(미확인). 숫자는 1 만으로 맞는다.

3. 반영한 뒤 포털 프런트 dist 를 새로 빌드해 Drive 에 올려 주십시오. 빌드 경로는 `update-all.sh:1763-1765` 안내문대로다. `./infra/scripts/build-all-to-drive.sh portal` 을 돌리거나, `pnpm build` 뒤 `images-to-drive.sh` 를 돌린다. cae00 은 dist 를 직접 빌드하지 않는다. Drive 의 `frontend-dist.tar.gz` 를 받아 푼다(`images-from-drive.sh:65-73`). 따라서 소스만 올라가면 화면은 바뀌지 않는다. 박스의 추적 파일은 고치지 않는다. 포털 개발이 dist 를 Drive 에 올리는 시점은 확인하지 못했다(미확인).



같은 상세칸에 `detail.error` 가 보이지 않는 문제는 다른 항목(상세 불러오기 실패 표시)에서 다룬다. 두 변경은 같은 `StartPicker.tsx:277-314` 블록을 건드린다. 그래서 같이 반영하면 편하다.



**왜** — 전문가 목록 상세칸은 「64건」인데, 고르고 나면 같은 흐름 안에서 「20건」으로 줄어 보인다. 그래서 카드가 많은 전문가(778명 중 761명)를 시작 직전에 보면 지식이 적은 전문가처럼 보이고, 이미 고쳤다는 9-11 안내와도 어긋난다.



**확인**



```bash

# cae00 — 포털 갱신(update-collab.sh)으로 새 dist 가 풀린 뒤

cd ~/Projects/HWAXPortal/frontend

cat dist/.build-src; git -C .. rev-parse HEAD:frontend      # 둘이 같아야 새 dist 다(지금은 53c2035d… = e6a8e52). update-all.sh:1760-1767 과 같은 대조다

f=$(grep -o 'assets/index-[A-Za-z0-9_-]*\.js' dist/index.html | head -1)

grep -o '보유 지식 (' "dist/$f" | wc -l                      # 0 이어야 한다(지금 index-VgVFfFzR.js 는 1)

```



화면에서도 확인한다. 챗 → 「전문가·도구 고르고 시작」 → 전문가 목록 열기 순서로 들어간다.

- cam-aa-process 를 고르면 상세칸에 「보유 지식 64건 · 앞 20건」이 보여야 한다.

- material-twin-analyst 를 고르면 「보유 지식 2,729건 · 앞 20건」이 보여야 한다.

- cam-system-architecture(전체 6건)를 고르면 「보유 지식 6건」만 보이고 「앞 …건」은 없어야 한다.



시작 패널의 수는 전문가 목록 상세칸에 보이는 수와 같아야 한다.



---



## K5. 카드 검색이 붙은 구절만 찾는다



대상 — AIDataHub(`record_query_svc` · 설명문 · 시험) + HWAXPortal(검색칸 문구) + HWAXAgentServer(독스트링 한 줄) · 담당 판단: AIDataHub 담당(검색 조건) / 포털 개발(문구) / 에이전트서버 개발(독스트링)

기준 — AIDataHub `b401f88`(cae00 HEAD = origin/main) · 포털 origin/main `90147ac` · 에이전트서버 origin/main `c4e4823`. 아래 `파일:줄` 은 이 커밋 기준이다.



**지금** — 심층 보기 검색칸(`frontend/src/components/chat/AgentDeepView.tsx:265` 「카드 제목·요약으로 찾기」)에 친 글자는 앞뒤 공백만 깎인다(`:134`). 에이전트서버도 앞뒤 공백을 깎고 200자로 자를 뿐이다. 그 글자를 `agents:[전문가 키]` 와 함께 게이트웨이를 거쳐 `list_records` 에 넘긴다(`app.py:4568-4570`). AIDataHub 는 그 글자 전체를 한 덩어리로 `title ILIKE '%q%' OR summary ILIKE '%q%'` 에 건다(`api_server/src/api/services/record_query_svc.py:66-69`, 패턴은 `sql_compat.py:248-251` `f"%{q}%"`). 낱말로 나누지 않는다. `%`·`_` 도 이스케이프하지 않는다. 본문(`record_sections.content_text`)은 보지 않는다. REST(`routes/records.py:124`) · MCP(`mcp_runtime.py:950`) · 챗(`chat_svc.py:186`)이 모두 이 함수를 쓴다.



그래서 낱말 둘이 제목이나 요약에 **붙어서, 그 순서로** 있을 때만 찾는다. 2026-10-15 실측(cae00 `POST 127.0.0.1:9009/catalog/agent/records`, caeg 그룹, 읽기만)은 아래와 같다.



| 전문가 | 검색어 | total |

|---|---|---|

| cam-aa-process | `접착제` · `접착제 물성` | 4 · 1 |

| | `접착제 드리프트` · `드리프트 접착제` | 0 · 0 |

| | `Camera module` · `module Camera` · `camera  module`(공백 둘) | 8 · 0 · 0 |

| | `Camera_module` | 8 (`_` 가 와일드카드로 먹힌다. 8건 모두 제목·요약에 `Camera_module` 글자는 없다) |

| mx-whitepaper-analyst | `모바일` · `반도체` · `소프트웨어` | 2 · 3 · 2 |



「접착제 물성(Tg·CTE·모듈러스)과 온도에 따른 초점·틸트 드리프트」 카드는 두 낱말을 다 담았다. 그런데 `접착제 드리프트` 로는 0건이다. 화면에는 `‘접착제 드리프트’ 에 맞는 카드가 없습니다.`(`AgentDeepView.tsx:295-296`)가 뜬다. mx-whitepaper-analyst 는 427장 중 320장의 요약이 AIDataHub 원본부터 비어 있다. 그 카드들은 제목(중앙값 9자)으로만 걸린다. 그 320장 중 319장은 `record_sections.content_text` 에 본문이 있다. 읽기 전용 SQL 로 본문까지 넣어 세면 `모바일` 2→73, `반도체` 3→32, `소프트웨어` 2→54건이다(2026-10-14). 태그는 영어(`mobile`·`semiconductor`)라 태그 일치로는 풀리지 않는다.



**요청**



1. **낱말마다 AND 를 건다. 낱말 하나 안에서는 제목 OR 요약(OR 본문)으로 묶는다.** `record_query_svc.py` 를 아래처럼 바꾼다. 이스케이프는 SQLAlchemy 2.0 의 `icontains(..., autoescape=True)` 에 맡긴다. cae00 설치본은 2.0.49이고 `requirements.txt:9` 는 `>=2.0.36` 이다. 컴파일 결과는 PG 에서 `title ILIKE '%' || $1 || '%' ESCAPE '/'`, SQLite 에서 `lower(title) LIKE '%' || lower(?) || '%' ESCAPE '/'` 다. 값의 `%`·`_` 는 `/%`·`/_` 로 바뀐다. 이 결과는 cae00 venv 에서 DB 없이 컴파일만 해서 얻었다. `paginate_rows` 가 감싸는 `count(*)` 서브쿼리에서도 EXISTS 가 바르게 상관된다.



   ```diff

   # api_server/src/api/services/record_query_svc.py

   -from sqlalchemy import or_, select

   +from sqlalchemy import and_, exists, or_, select

    from sqlalchemy.ext.asyncio import AsyncSession



   -from ..db.models import Record

   +from ..db.models import Record, RecordSection

    from .sql_compat import (

   +    FTS_OR_MAX_TOKENS,

        ArrayPredicate,

        array_contains,

        array_overlap,

        paginate_rows,

   -    summary_ilike,

    )

   @@ :66-69

   -    if q:

   -        stmt = stmt.where(

   -            or_(summary_ilike(Record.title, q), summary_ilike(Record.summary, q))

   -        )

   +    # 낱말마다 AND — 통째 구절 ILIKE 는 순서가 바뀌거나 사이에 낱말이 끼면 0건이었다.

   +    # 본문은 전문가 필터가 있을 때만 본다(필터 없이 record_sections 를 다 훑지 않게).

   +    tokens = (q or "").split()[:FTS_OR_MAX_TOKENS]

   +    if tokens:

   +        stmt = stmt.where(and_(*[_q_token(t, body=bool(agents)) for t in tokens]))

   ```

   `query_records` 위에 아래 함수를 둔다.

   ```python

   def _q_token(tok: str, *, body: bool):

       """낱말 하나 — 제목·요약에 그 글자가 있으면 참. '%'·'_' 는 글자 그대로다.



       body 면 본문 절(record_sections)도 본다. 낱말마다 EXISTS 를 따로 두므로

       두 낱말이 서로 다른 절에 있어도 맞는다.

       """

       terms = [

           Record.title.icontains(tok, autoescape=True),

           Record.summary.icontains(tok, autoescape=True),

       ]

       if body:  # 요청 2 — 미루면 이 블록과 body 인자를 뺀다

           terms.append(exists().where(

               RecordSection.record_id == Record.id,

               RecordSection.content_text.icontains(tok, autoescape=True),

           ))

       return or_(*terms)

   ```

   - `str.split()` 은 공백 여럿과 앞뒤 공백을 버린다.

   - 낱말 상한은 기존 `FTS_OR_MAX_TOKENS`(`sql_compat.py:59`, 12)를 쓴다. `fts_match` 의 SQLite 폴백도 같은 상한으로 낱말을 나눈다(`sql_compat.py:293`).

   - 구절이 맞는 카드는 낱말 AND 에도 맞는다. 그래서 지금 찾던 카드는 계속 찾는다. 결과가 줄어드는 것은 `%`·`_` 를 와일드카드로 쓰던 질의뿐이다. PG 에서는 기본 이스케이프 글자 `\` 도 이제 글자 그대로다.

   - ⚠ 「제목에 모든 낱말」 OR 「요약에 모든 낱말」로 짜면 안 된다. 그러면 한 낱말은 제목에, 다른 낱말은 요약에 있는 카드를 또 놓친다.

   - ⚠ `fts_match`(`sql_compat.py:254`)로 바꾸지 않는다. PG 의 `'simple'` 설정은 통째 토큰만 맞춘다. 그러면 `온도` 로 「온도에 따른」 제목을 못 찾는다. 지금 ILIKE 는 그 제목을 찾는다(cam-aa-process `온도` 5건). `'simple'` 의 토큰 동작은 운영 DB 에서 돌려 보지 않았으므로 미확인이다.

   - `summary_ilike` 는 `search_svc.py:638` 도 쓴다. 그래서 헬퍼는 그대로 두고 이 파일의 import 만 뺀다.



2. **본문 일치(위 `if body:` 블록)는 1 과 같이 넣기를 권한다. 기본값은 `agents` 가 있을 때만이다.** 같은 꼴의 섹션 ILIKE 가 이미 `search_svc.py:634-639` 에 있다.

   - 왜 agents 로 거나. `record_sections` 는 2026-09-09 에 862,910행이었다. 그때 to_tsvector 전수 스캔은 25.6초였다(`alembic/versions/0031_fts_gin_index.py:12-14`). 코드와 마이그레이션에 `trgm` 인덱스는 한 건도 없다. `paginate_rows` 는 count 와 쪽을 따로 돌린다. 그래서 필터 없는 `/api/records?q=` 나 agents 없는 MCP `list_records` 에 본문 항을 걸면 그 표를 두 번 훑을 수 있다.

   - agents 가 있으면 바깥 행이 그 전문가 카드로 좁혀진다(`agents` GIN, `models.py:84`). 그 위에서 EXISTS 는 `idx_sections_record`(`models.py:296`, `alembic/versions/0001_initial_schema.py:157`)를 탈 수 있다. 심층 보기는 늘 agents 를 보낸다(`app.py:4568`). 챗 도구(`chat_svc.py:186`)는 agents 를 넘기지 않으므로 본문을 보지 않는다.

   - ⚠ 속도는 미확인이다. 운영 DB 의 실물 인덱스도 미확인이다. 머지 전에 운영 DB 사본에서 `EXPLAIN ANALYZE` 를 재 주십시오. 기준은 카드가 가장 많은 전문가(material-twin-analyst 2,729장)다. 필터 없는 경로까지 켜려면 그 경로도 재 보고 `body=True` 로 바꾼다. 느리면 `pg_trgm` GIN 인덱스를 달고 다시 잰다.

   - 본문으로 찾은 mx-whitepaper-analyst 카드는 지금 열면 제목만 있고 본문이 비어 보인다. 에이전트서버 `_record_view`(`app.py:4598`, `:4608`)가 절의 `content_text`·`text` 만 읽기 때문이다. 이것은 별도 항목이다. 그 항목이 같이 들어가야 찾은 까닭이 화면에 보인다.



3. **설명문을 맞춘다.** 같은 동작을 적은 소스는 세 군데다. 문서는 한 파일이다.

   ```diff

   # api_server/src/api/mcp_runtime.py:927 — 모델이 질의를 고를 때 읽는 문구다

   -        "team/group/doc_type/data_type/tags/agent/year + 제목·요약 키워드(q) 로 "

   +        "team/group/doc_type/data_type/tags/agent/year + 낱말 검색(q — 공백으로 나눈 "

   +        "낱말을 모두 담은 카드. 제목·요약, agents 를 주면 본문까지 부분 일치) 로 "

   # api_server/src/api/routes/records.py:107

   -    q: str | None = Query(None, description="ILIKE on title + summary"),

   +    q: str | None = Query(None, description="all words, ILIKE title/summary (+ body with agent)"),

   # api_server/src/api/services/chat_svc.py:112

   -                    "q": {"type": "string", "description": "제목/요약 키워드"},

   +                    "q": {"type": "string", "description": "제목/요약에 모두 담긴 낱말(공백으로 나눔)"},

   ```

   - `api_server/docs/AGENT_API_GUIDE_MEDIUM.md:328`·`:339`·`:835` 도 「ILIKE on title + summary」라고 적는다. 같은 뜻으로 고친다.

   - `distribution/` 아래 사본(2026-05 배포 묶음, 자체 인라인 쿼리)은 이 요청 밖이다.

   - 에이전트서버는 q 를 그대로 넘기므로 코드를 바꿀 것이 없다. 독스트링 `app.py:4562` 의 「제목·요약 검색(q)」만 「낱말 검색(q — 제목·요약·본문)」으로 맞춘다.



4. **시험.** `api_server/tests/test_record_query_svc.py` 에는 q 시험이 하나도 없다. 독스트링 `:4` 만 q 를 검증한다고 적혀 있다. `test_routes_records.py` · `test_list_records_tags_whole.py` · `test_pg_integration.py` · `integration/test_full_flow.py` 도 q 를 쓰지 않는다. 포털과 에이전트서버 시험에도 이 문구나 q 동작을 단언하는 것이 없다. 그래서 **고쳐야 할 기존 시험은 없다.** 같은 파일의 `_seed`(`:11-22`)로 아래 시험을 더한다.

   ```python

   _Q_SEEDS = [  # (제목, 요약)

       ("접착제 물성과 온도에 따른 초점 드리프트", "요약말"),

       ("수율 100%", ""),

       ("부품 1000개", ""),

       ("Camera_module", ""),

       ("Camera module", ""),

   ]





   @pytest.mark.asyncio

   @pytest.mark.parametrize("q, n", [

       ("드리프트 접착제", 1),        # 순서를 뒤집었다

       ("접착제 드리프트", 1),        # 사이에 낱말이 낀다

       ("  접착제   드리프트 ", 1),   # 공백 여럿

       ("접착제 요약말", 1),          # 한 낱말은 제목, 한 낱말은 요약

       ("접착제 없는말", 0),          # 한 낱말이 없다 → AND

       ("100%", 1),                   # 지금은 '부품 1000개' 까지 2건

       ("Camera_module", 1),          # 지금은 'Camera module' 까지 2건

   ])

   async def test_q_words_and(test_session, q, n):

       from api.services.record_query_svc import query_records



       for i, (title, summary) in enumerate(_Q_SEEDS, 1):

           await _seed(test_session, id=f"DOC-HE-CAE-2026-000000000{i}", title=title, summary=summary)

       _, total = await query_records(test_session, q=q)

       assert total == n





   @pytest.mark.asyncio

   async def test_q_matches_section_body_with_agents(test_session):  # 2 를 넣을 때

       from api.db.models import RecordSection

       from api.services.record_query_svc import query_records



       rid = "DOC-HE-CAE-2026-0000000001"

       await _seed(test_session, id=rid, title="AP", summary="", agents=["a"])

       test_session.add(RecordSection(record_id=rid, section_id="1", level=1, title="본문",

                                      content_text="모바일 AP 발열"))

       await test_session.flush()

       _, total = await query_records(test_session, q="모바일 발열", agents=["a"])

       assert total == 1  # 두 낱말 다 본문에만 있다

       _, total = await query_records(test_session, q="모바일 발열")

       assert total == 0  # 전문가 필터가 없으면 본문은 보지 않는다

   ```

   - 섹션 시드 꼴은 `test_agent_search_top_k.py:32` 를 따른다.

   - PG 경로(`AIDH_TEST_PG_URL` 를 줄 때만 도는 `test_pg_integration.py`)에도 아래 시험을 더한다. 그러면 `ESCAPE '/'` 가 실제 PG 에서 도는지 확인된다. 그 파일의 `_seed` 는 `(session, rid, **over)` 꼴이다.

     ```python

     @pytest.mark.asyncio

     async def test_q_literal_percent_pg(pg_session):

         from api.services.record_query_svc import query_records



         await _seed(pg_session, "DATA-HE-CAE-2026-0000000001", title="수율 100%")

         await _seed(pg_session, "DATA-HE-CAE-2026-0000000002", title="부품 1000개")

         _, total = await query_records(pg_session, q="100%")

         assert total == 1

     ```

   - 위 기대값은 cae00 venv 의 SQLAlchemy 2.0.49 와 메모리 SQLite 로 같은 식을 돌려 맞췄다. 실제 pytest 는 돌리지 않았다(미확인).

   - 독스트링 `:4` 는 그대로 맞는 말이 된다.



5. **포털 문구(HWAXPortal).** AIDataHub 가 바뀐 판에 맞춰 placeholder 를 고친다.

   ```diff

   # frontend/src/components/chat/AgentDeepView.tsx:265

   -                    placeholder="카드 제목·요약으로 찾기"

   +                    placeholder="제목·요약·본문에서 낱말로 찾기"

   ```

   - 2 를 넣지 않으면 `제목·요약에서 낱말로 찾기` 로 한다.

   - AIDataHub 변경이 늦어지면 그때까지는 `카드 제목·요약에 붙은 구절로 찾기` 로 둔다. 지금 동작을 사실대로 적은 문구다.

   - 이 파일은 `e6a8e52` 와 `90147ac` 사이에 바뀌지 않았다.



**왜** — 카드에 있는 낱말 두 개로 찾았는데 「맞는 카드가 없습니다」가 나오면, 사용자는 그 지식이 없다고 결론짓는다. 요약이 빈 카드(mx-whitepaper-analyst 320장)는 지금 제목 몇 글자로만 검색에 걸린다.



**확인** — AIDataHub 를 새로 받은 뒤 cae00 에서 읽기만 한다. `kc-check/groups.json` 은 이번 점검 때 만든 caeg 그룹 목록이다. ⚠ 게이트웨이는 `list_*` 결과를 300초 캐시한다(HWAXMcpGateway `gateway.py:345` `CACHE_TTL_S`, 지금 `/health` 의 `cache.ttl_s` 300). 그래서 AIDataHub 를 다시 띄우고 5분이 지난 뒤에 돌린다.



```bash

timeout 120 ssh hwax 'python3 - <<"EOF"

import json, urllib.request

g = json.load(open("/home/koopark/kc-check/groups.json"))["caeg"]

def total(k, q):

    b = json.dumps({"key": k, "q": q, "offset": 0, "limit": 50, "groups": g}).encode()

    r = urllib.request.Request("http://127.0.0.1:9009/catalog/agent/records", data=b,

                               headers={"Content-Type": "application/json"})

    return json.load(urllib.request.urlopen(r, timeout=60)).get("total")

for k, q in [("cam-aa-process", "접착제 드리프트"), ("cam-aa-process", "드리프트 접착제"),

             ("cam-aa-process", "module Camera"), ("cam-aa-process", "camera  module"),

             ("cam-aa-process", "Camera_module"), ("mx-whitepaper-analyst", "모바일")]:

    print(k, repr(q), total(k, q))

EOF'

```



기대값은 아래와 같다.

- `접착제 드리프트` · `드리프트 접착제` 는 1 이상이다.

- `module Camera` · `camera  module` 은 8 이상이다(지금 `Camera module` 이 8).

- `Camera_module` 은 8 보다 작아진다. 8건 모두 제목·요약에 그 글자가 없으므로(10-15 확인) 1 만 넣으면 0 이다. 2 까지 넣으면 본문에 그 글자가 있는 카드만 남는다.

- `모바일` 은 1 만 넣으면 2 그대로다. 2 까지 넣으면 73 안팎이다(10-14 읽기 전용 SQL 73).



화면은 포털 → 전문가 심층 보기 → cam-aa-process → 검색칸에서 본다. `드리프트 접착제` 를 치면 「접착제 물성(Tg·CTE·모듈러스)…」 카드가 떠야 한다. 프론트를 다시 빌드한 뒤에는 실제로 서빙되는 번들에 새 문구가 있어야 한다. 아래 명령의 결과가 1 이상이면 된다.



```bash

timeout 60 ssh hwax 'cd ~/Projects/HWAXPortal/frontend/dist && grep -c "낱말로 찾기" "$(grep -o "assets/index-[^\"]*\.js" index.html | head -1)"'

```



---



## K6. 빈 전문가·시험 데이터·빈 요약 정리



대상 — AIDataHub(데이터·적재·동기화) · KooRemapper(등재 코드) · HWAXPortal(문구 1곳) · cae00 운영(AIDataHub 동기화 설정) · 담당 판단: AIDataHub 데이터 담당 + KooRemapper 작성자(문구는 포털 개발, 동기화 설정은 AIDataHub 운영)

기준 — AIDataHub `b401f88`(HEAD = origin) · KooRemapper origin/main `30a1f7d` · 포털 origin/main `90147ac` · 에이전트서버 origin/main `c4e4823`. 아래 `파일:줄` 은 모두 이 커밋 기준이다.

실측 — 2026-10-14 전문가 796명 전수 조사와 10-15 재측정이다. 10-15 에는 AIDataHub REST(에이전트·목록 조회)와 `get_record_sections` 를 읽고, AIDataHub 서버 로그 `deploy/apptainer/logs/uvicorn.log`·`.1`(10-01~10-15)을 읽었다. 단건 조회 `GET /api/records/{id}` 는 read_count 를 올리고, 그 바람에 updated_at 도 바뀐다(`api_server/src/api/routes/records.py:52-68`, `db/models.py:242` onupdate). 검토 중 `DOC-MX-WP-2026-0000000022` 를 이렇게 두 번 읽어서 그 레코드의 updated_at 이 10-14 22:09Z 로 바뀌었다. 그 밖에는 아무것도 바꾸지 않았다.



| # | 무엇 | 지금 | 정할 것 |

|---|---|---|---|

| K6-1 | `dynaforge-report` | 이름=키 · 설명 0자 · 카드 0건. 08-15 스모크 등재가 남긴 자리다 | 살릴지 · 있는 전문가로 돌릴지 · 접을지 |

| K6-2 | `kooremapper-modelmeta` | 이름=키 · 설명 0자. 카드 3장이 전부 S26-DEMO 시험 업로드다 | 지울지 · 채울지 |

| K6-3 | 적재의 자동 껍데기 | 등록 안 된 키로 빈 전문가를 말없이 만든다(위 둘의 원인) | strict 로 막을지 |

| K6-4 | `mx-whitepaper-analyst` | 427장 중 빈 요약 320장 · 본문이 빈 레코드 154장 · 동기화가 10-01 부터 매번 실패 | 동기화 재개(보안 설정) · 폴백 · 재동기화 |

| K6-5 | 포털 문구 | 설명이 없는데 「위 설명이 전부입니다」라고 쓴다 | — |



운영자 15명과 `sim-structural-calc` · `sim-thermal-sed` 의 카드 0건은 설계대로다. 이 정리의 대상이 아니다.



### K6-1. dynaforge-report — 스모크 등재가 남긴 빈 전문가



**지금**

- AIDataHub 행은 이름=키다. 설명 0자이고 태그·예시·data_types 가 하나도 없다(`GET /api/agents/dynaforge-report`, 10-15). 생성 시각 `2026-08-15T11:46:22.931453Z` 는 스모크 레코드 `SIM-MX-CAE-2026-0000000013` 의 생성 시각과 같다. 적재가 만든 자동 껍데기다(K6-3). 역할 원문은 자동 틀이다(`api_server/src/api/services/recommend_svc.py:833-839`, 「Help the user with: (no description)」). 그래서 에이전트서버가 빈 역할로 친다(`app.py:4475-4476`).

- 붙어 있는 레코드 2건(`…0013`·`…0014`, 「S26-DROP dv1 — Test_001_Full26_1Step sphere 리포트」)은 만든 지 1분 남짓 만인 11:47:47Z 에 소프트 삭제됐다. `/api/records/?agent=dynaforge-report` 는 total 0이고, `include_deleted=true` 를 주면 2다.

- 이 키를 붙이는 곳은 KooRemapper `platform/backend/app/reports/datahub.py:160` `"agents": ["dynaforge-report"]` 한 곳이다(fecc083, 2026-08-15 11:49:54Z). KooRemapper 에는 이 전문가를 등록하는 코드가 없다(`api/agents`·`create_agent`·`patch_agent` grep 0건). 같은 리포의 양식 문서는 `agents` 를 「등재 주체」 `"<forge>-report"` 로 정해 두었다(`docs/impact-ingest/datahub-sim-report-schema.md:19`·`:36`).

- 등재 경로는 운영에서 열려 있다.

  - REST: `platform/backend/app/modules/reports/routes.py:769` `POST /reports/{id}/publish-datahub`. koorm_api `:8700` OpenAPI(`/api/openapi.json`)에 `/api/v1/reports/{report_id}/publish-datahub` 로 실재한다(10-15).

  - MCP: `platform/mcp_server/server.py:1352` `publish_report_to_datahub`. 게이트웨이 `/tools-map` 에 실재한다(10-15).

  - 목적지 기본값: `platform/backend/app/config.py:122` `http://127.0.0.1:8001`, 곧 운영 AIDataHub 다.



  리포트 소유자 한 명이 한 번만 등재해도 SIM 카드가 이 빈 전문가 밑으로 들어간다.

- 사용자 화면은 이렇다. 전문가 목록의 「앱 지식 분석가」 분류 아래(분류 정의 JSON — `frontend/src/components/chat/` 안 `:105-110`, `personaCatalog.ts:148`)에 키 그대로의 이름으로 뜬다. 프로필은 비어 있고, 카드 목록은 「연결된 지식카드가 없습니다.」다(`AgentDeepView.tsx:299`). 골라서 대화하면 `persona_role_empty` 경고(`app.py:3134`)와 「연관 지식카드 없음 — 일반 지식으로 답변」(`app.py:3166`)이 나온다.

- 올라올 SIM 카드는 본문에 절이 없어서 에이전트서버가 「원문(JSON)」 한 절로 보인다(`app.py:4636`, 설계된 폴백). 이 정리의 대상은 아니다.



**요청** — 셋 중 하나를 정해 주십시오.

1. (가) **살린다.** DynaForge 리포트를 이 이름으로 계속 올릴 거면, 다음 등재 전에 행을 채운다. `PATCH /api/agents/dynaforge-report`(`api_server/src/api/routes/agents.py:188`)로 name(예: 「DynaForge 해석 리포트」) · description · system_prompt · common_tags(`sim:drop_impact` 등) · data_types `["SIM"]` · sample_queries 를 넣는다. KooRemapper 코드는 그대로 둔다.

2. (나) **있는 전문가로 돌린다.** 이 등재는 낙하 해석이므로(`datahub.py:28` `SIM_DOMAIN = "drop_impact"`) `sim-drop-impact`(「세트 낙하·충격 해석 전문가」, 설명 394자, 카드 192장, 10-15 실재 확인)가 맞다. 그 전문가의 data_types 는 지금 `["DOC"]` 뿐이다. `SIM` 을 더할지 같이 정한다.



```diff

 # platform/backend/app/reports/datahub.py

 SIM_DOMAIN = "drop_impact"

+# 등재 레코드를 붙일 AIDataHub 전문가 — 허브에 등록된 키여야 한다. 없는 키를 주면 적재가

+# 이름=키·설명 0자의 빈 전문가를 말없이 만든다(dynaforge-report 가 2026-08-15 그렇게 생겼다).

+HUB_AGENT = "sim-drop-impact"

 ...

         "source_system": "DynaForge",

-        "agents": ["dynaforge-report"],

+        "agents": [HUB_AGENT],

```



   - 양식 문서 `datahub-sim-report-schema.md:19`·`:36` 의 「`agents` = 등재 주체 `<forge>-report`」도 「붙일 허브 전문가 키(허브에 등록된 것)」로 같이 고친다. 그대로 두면 다음 forge 가 같은 껍데기를 또 만든다.

   - `platform/backend/tests/test_report_datahub.py` 는 `agents` 를 확인하지 않는다. 깨지는 테스트는 없다.

   - 이 변경이 배포된 **뒤에** `DELETE /api/agents/dynaforge-report`(`routes/agents.py:208`)로 행을 지운다. `agent_records` 2행은 FK cascade 로 같이 지워진다. 그 2행이 가리키는 레코드는 이미 소프트 삭제돼 있다. 순서를 거꾸로 하면 다음 등재가 껍데기를 다시 만든다.

3. (다) **접는다.** 허브에 올릴 계획이 없으면 등재를 끈다. `datahub_url` 을 비우면 라우트가 400을 낸다(`routes.py:782-783`, 근거는 `config.py:121` 주석). 설정 키는 `KOORM_DATAHUB_URL` 이다. Settings 는 프로세스 환경과 `platform/.env`·`platform/backend/.env` 를 읽는다(`config.py:24-28`). 박스가 어느 쪽으로 넣는지는 미확인이다(env 파일은 읽지 않았다). MCP 도구도 같은 라우트를 부르므로(`server.py:1374`) 함께 막힌다. 그다음 2 처럼 행을 지운다.



**왜** — 등재 경로가 열려 있다. 정하지 않으면 첫 실제 DynaForge 리포트가 이름도 설명도 없는 전문가 밑에 들어간다.



**확인** — 아래 K6-3 명령의 결과에서 `dynaforge-report` 가 빠진다. (나)를 골랐다면, 반영된 upstream 을 받은 뒤 `git -C ~/Projects/KooRemapper show origin/main:platform/backend/app/reports/datahub.py | grep -n '"agents"'` 결과가 `[HUB_AGENT]` 다.



### K6-2. kooremapper-modelmeta — 자동 껍데기와 S26-DEMO 시험 카드 3장



**지금**

- 행은 이름=키다. 설명 0자이고 태그·예시·data_types 가 하나도 없다. 생성 시각 `2026-07-31T23:37:04.820180Z` 는 첫 카드 `SIM-MX-CAE-2026-0000000010` 의 생성 시각과 같다. 이것도 자동 껍데기다. 같은 접두의 `kooremapper-iga` 에는 이름·설명(35자)·태그 4개·역할 98자가 있다.

- 키를 붙이는 곳은 `tools/kr2datahub.py:201` `"agents": ["kooremapper-modelmeta"]` 한 곳이다. 이 스크립트도 전문가를 등록하지 않는다.

- 카드 3장이 전부 시험 업로드다.

  - `…0010` · `…0011` 「S26-DEMO dv1 — deck.k 모델 메타」: 같은 deck.k 를 두 번 올렸다. 010은 첨부가 없고 011은 첨부가 2개다.

  - `…0012` 「S26-DEMO pv2 — nbr_board.k 모델 메타」.



  셋 다 project `S26-DEMO` 이고 07-31 23:37~23:44Z 에 만들어졌다. 스크립트 첫 커밋 c02a8c4(23:44:52Z) 직전이다. 모델도 시험 크기다(deck.k 노드 56개 · 요소 37개, nbr_board.k 요소 18개).

- `status: draft` 로는 시험 데이터를 가를 수 없다. draft 가 허브 기본값이라(`api_server/src/api/ingest/normalizer.py:501`) 실제 레코드도 draft 다.

- `--datahub` 의 기본값은 환경변수 `AIDH_URL` 이고, 없으면 `http://localhost:8001` 이다(`kr2datahub.py:34`·`:105`). 그래서 cae00 에서 둘 다 없이 돌리면 운영 허브로 올라간다. 이 3장을 어디서 올렸는지는 미확인이다.



**요청**

1. (가) **지운다**(시험 데이터로 볼 때). 레코드 3건을 `DELETE /api/records/{id}`(소프트 삭제, `routes/records.py:239`)로 먼저 지운다. 그다음 `DELETE /api/agents/kooremapper-modelmeta` 로 행을 지운다. `kr2datahub.py:201` 의 키를 그대로 두면 다음 실제 업로드가 껍데기를 다시 만든다(K6-3 strict 가 꺼져 있을 때). 스크립트가 붙일 키도 같이 정한다.

2. (나) **살린다**(kr2datahub 로 실제 모델을 올릴 계획일 때). 행을 채운다. name(예: 「KooRemapper 모델 메타 분석가」) · description · system_prompt · common_tags(`part:` · `mat:` · `stage:`) · data_types `["SIM"]` · sample_queries 를 넣는다. 이 경우에도 S26-DEMO 3장은 지운다. 010과 011은 중복이다.

3. 어느 쪽이든, 시험 업로드가 운영 허브로 가지 않게 막을지 정해 주십시오. 한 가지 방법은 `--dry-run`(`:108`)을 `--upload` 로 뒤집어, 그 옵션을 줄 때만 올리는 것이다(`:220` `if a.dry_run:` → `if not a.upload:`). 사용법 주석(`:15`)도 같이 고친다.



**왜** — 운영 사용자가 이 전문가를 열면 시험 카드 3장만 보인다. 그중 012는 실제 재료 카드 `DOC-MX-MAT-2026-0000000002` 에 연결돼 있다. 그래서 진짜 모델 메타로 읽힐 수 있다.



**확인** — (가)면 K6-3 명령의 결과에서 `kooremapper-modelmeta` 가 빠진다. (나)면 그 전문가에 이름·설명이 생긴다. 시험 카드 수는 이렇게 본다(목록 조회라 read_count 를 올리지 않는다).



```bash

curl -s --noproxy '*' 'http://127.0.0.1:8001/api/records/?agent=kooremapper-modelmeta' | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])'   # 지금 3 → 0

```



### K6-3. 적재가 등록 안 된 키로 빈 전문가를 말없이 만든다



**지금**

- `api_server/src/api/ingest/db_writer.py:809-849` `_resync_agents` 는 레코드의 `agents` 에 등록 안 된 키가 있으면 `Agent(name=agent_type, description="", common_tags=[], data_types=[])` 를 만든다(:830-841).

- 그 앞의 검증(:321-336)은 같은 경우에 경고만 남긴다. 주석(:322-326)과 문구 「pending strict validation」은 strict 전환을 예고해 둔 것이다. 경고는 서버 로그에만 남는다. 그래서 K6-1·K6-2 의 껍데기가 두세 달 동안 전문가 목록에 떠 있었다.

- 같은 함수의 팀 검증은 이미 strict 다. `validate_team_group`(:402-403 → `services/org_svc.py:28-45`)은 422를 내고, 설정 `strict_team_validation`(`config.py:73`)으로 끌 수 있다.

- 지금 796명 중 이름=키이거나 설명이 0자인 전문가는 이 둘뿐이다.

- 동기화 소스 3곳이 쓰는 키(`market-voc-analyst` · `mx-whitepaper-analyst` · `material-twin-analyst`, `config/sync_sources.yml:65-66·131-132·199-200`)는 모두 등록돼 있다(10-15).



**요청** — 예고된 strict 로 바꿔 주십시오. 팀 검증과 같은 모양(설정 스위치 + 422)으로 한다.



```diff

 # api_server/src/api/config.py:73

     strict_team_validation: bool = True

+    # records.agents 에 agents 테이블에 없는 키가 있으면 적재를 거절한다. false 면 지금처럼

+    # 경고만 남기고 _resync_agents 가 이름=키·설명 0자의 빈 행을 만든다.

+    strict_agent_validation: bool = True

```



```diff

 # api_server/src/api/ingest/db_writer.py:330-336

         for agent_type in record_in.agents:

             if agent_type and agent_type not in registered_agents:

+                if settings.strict_agent_validation:

+                    raise HTTPException(

+                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

+                        detail=f"agent '{agent_type}' is not registered — register it before ingest (record {record_in.id})",

+                    )

                 logger.warning(

                     "record %s references unregistered agent_type %r — pending strict validation",

                     record_in.id,

                     agent_type,

                 )

```



- `settings`(`..config`)·`HTTPException`·`status`(`fastapi`)는 이 함수가 모델을 가져오는 방식대로 함수 안(:309-316)에서 import 한다. 주석(:322-326)도 strict 로 고친다.

- 설정에는 접두가 없다(`config.py:13-15`). 운영에서 되돌릴 때는 `STRICT_AGENT_VALIDATION=false` 다.

- 응답 코드는 경로마다 다르다. convert 경로에서는 422가 그대로 나간다. 번들 경로는 `write_record` 의 예외를 모두 500 `DB_WRITE_FAILED` 로 감싼다(`routes/bundle.py:330-340`). 사유는 메시지에 실린다. 팀 검증의 422 도 지금 같은 길로 나간다. KooRemapper 업로더 둘은 모두 번들 경로(`/api/ingest/bundle`)를 쓴다. 동기화 경로(`routes/records.py` `_import_one`)는 run 의 failed·dead_letter 로 남긴다.

- `_resync_agents` 의 stub 생성(:830-841)은 스위치가 false 일 때만 실행된다. 그대로 둔다.

- 등록 안 된 키로 적재하는 기존 테스트가 있다. `api_server/tests/test_ingest.py:236-262`(`cline_sr`)와 `:342-367`(`cline_sr`·`rag_general`)이다. 빈 DB 에 `iga-analyst` 픽스처(`tests/conftest.py:545`)를 넣는 `tests/test_auto_embed_trigger.py:26`·`:51` 도 그렇다. 스위치를 켠 채로는 이 테스트들이 깨진다. 키를 먼저 넣거나 그 테스트에서 스위치를 끈다. 이 테스트들이 지금 통과하는지는 돌려 보지 않아 미확인이다.

- 지금 있는 두 껍데기 행은 이미 등록된 키다. 그래서 strict 를 켜도 KooRemapper 등재는 그대로 통과한다. strict 는 새 키만 막는다. K6-1 (나)·(다)나 K6-2 (가)로 행을 지운 뒤에 옛 키로 올리면 그때부터 거절된다.

- 켜기 전에 다른 번들 업로더가 등록 안 된 키를 쓰는지 본다. 10-01~10-15 서버 로그에 「references unregistered agent_type」 경고는 0건이다. 다만 액세스 로그가 꺼져 있어 그 기간에 적재가 있었는지는 로그로 알 수 없다(미확인).

- strict 를 고르지 않으면 같은 껍데기가 다음 업로더에서 또 생긴다.



**왜** — 등록 안 된 키 하나가 이름도 설명도 없는 전문가를 운영 전문가 목록에 올린다. 그 사실은 서버 로그의 경고 한 줄로만 남는다.



**확인**



```bash

# cae00 — 이름=키이거나 설명 0자인 전문가. 지금 ['dynaforge-report', 'kooremapper-modelmeta'] → [] 이어야 한다

curl -s --noproxy '*' 'http://127.0.0.1:8001/api/agents/' | python3 -c 'import json,sys; print([a["agent_type"] for a in json.load(sys.stdin) if a.get("name")==a["agent_type"] or not a.get("description")])'

```



strict 동작은 테스트로 확인한다. 등록 안 된 키로 `write_record` 를 부르면 422 `HTTPException` 이 나야 한다. 스위치를 끄면 지금처럼 빈 행이 생겨야 한다. 운영 허브에 시험 번들을 올리지 않는다.



### K6-4. mx-whitepaper-analyst — 빈 요약 320장 · 본문이 빈 레코드 154장 · 멈춘 동기화



**지금**

- 카드 427장 중 320장은 AIDataHub 안에서부터 요약이 빈 문자열이다(`GET /api/records/?agent=mx-whitepaper-analyst` 전수 조회, 10-14와 10-15가 같다). 10-14 의 DB 읽기로는 허브 전체의 빈 요약 324장 가운데 320장이 이 전문가 것이다. 나머지 4장은 전문가가 없다. 에이전트서버와 포털은 받은 값을 그대로 넘긴다. 그래서 사용자 화면의 카드 목록에서 4장 중 3장이 짧은 제목 한 줄로만 보인다.

- 320장의 구성은 namu-archive 위키 171장, 작성자 태그만 있는 1장, 태그가 `status:published` 하나뿐인 148장이다.

- 원인 ① — 폴백이 없다.

  - mxwp 매핑은 `config/sync_sources.yml:112` `summary_field: summary` 뿐이다. `api_server/src/api/services/sync_svc.py:327-330` 은 그 값이 있을 때만 요약을 넣는다.

  - `summary_template` 을 더하는 방법으로는 안 된다. 템플릿이 있으면 필드보다 먼저 쓰인다(`sync_svc.py:183`). 그래서 요약이 있는 107장을 덮어쓴다. `default:` 필터는 고정 문자열만 받는다(:155-156).

- 원인 ② — 다시 동기화해도 요약만 바뀐 레코드는 건너뛴다. 해시는 `content` 만 보고 계산한다(`db_writer.py:319`). :409-411 은 해시가 같으면 제목·요약을 보지 않고 skipped 로 끝낸다. 이 동작은 테스트가 고정해 두었다(`api_server/tests/test_ingest.py:286-296`, 요약만 바꾼 입력이 skipped). 그래서 폴백을 넣어도 본문이 그대로인 namu 171장은 바뀌지 않는다.

- 원인 ③ — 154장은 본문이 비었다.

  - `records.content` 가 「본문」 한 절이고 그 `content_text` 가 ""다(154장 가운데 148장은 요약도 비었다). 상세 응답의 metadata·sections 가 섞이지 않은 모양이다.

  - 154장 모두 06-12 생성이다. updated_at 은 08-07(72장) · 08-10(37장) · 08-12(45장)에 몰려 있다. 다만 updated_at 은 단건 조회에도 바뀐다(위 실측 줄). 그래서 그날 덮어썼다는 근거로는 약하다.

  - 코드 흐름은 이렇다. `sync_svc.py:791-828` 은 상세 조회가 200이 아니거나 예외가 나면 경고만 남기고 목록 응답만으로 변환한다. MXWP 목록 응답에는 메타만 있다(:771-773). 그래서 :264-279 의 폴백이 빈 「본문」 한 절을 만든다.

  - 확인된 것은 이 코드 흐름과 데이터 모양이 맞는다는 데까지다. 8월에 상세 조회가 실제로 실패했는지는 미확인이다. 남은 로그는 10-01 부터다.

- 원인 ④ — 동기화가 10-01 부터 한 번도 돌지 않았다.

  - 서버 로그(`deploy/apptainer/logs/uvicorn.log`·`.1`, 10-01~10-15)에서 mxwp 정기 동기화 525번이 모두 같은 메시지로 실패했다. 「sync_source base_url unsafe: non-standard port blocked: 8800 … set AIDH_SYNC_ALLOW_INTERNAL=true if intended」다. 성공 로그(「scheduled sync …: status=」)는 0건이다.

  - 막는 코드는 SSRF 가드 `api_server/src/api/services/url_safety.py:110-122` 다. `127.0.0.1:8800` 은 루프백이고 비표준 포트라 `AIDH_SYNC_ALLOW_INTERNAL` 없이는 통과하지 못한다. 배포 예시는 같은 호스트 소스일 때 이 값을 true 로 둔다(`deploy/apptainer/.env.example:160-164`).

  - 부팅할 때마다 「sync_bootstrap [mxwp]: api_key_env='MXWP_INTERNAL_KEY' not set」도 남는다(10-01·10-11). MXWP API 는 키 없이 부르면 목록·상세 모두 401이다(10-15).

  - signalforge-gs(525번)·materialtwin(45번)도 같은 이유로 실패한다. 이 둘은 K6 밖이다. 같은 설정으로 함께 풀린다.

  - 그래서 아래 1~3 은 동기화가 다시 돌아야 효과가 난다.

- 원문은 아직 남아 있다. `get_record_sections` 로 `DOC-MX-WP-2026-0000000109` 를 읽으면 1번 절만 빈 「본문」이다. 2번 「개요」와 4번 「응용」에는 본문이 그대로 있다(10-15). `…0113` 도 같다. 1번 절만 바뀌고 나머지가 남은 까닭은 미확인이다. 모든 절을 지우고 다시 넣는 `_resync_sections`(:602-614)의 동작과 맞지 않는다.

- 카드를 열면 절 제목만 있고 글이 비어 보이는 문제는 별도 항목이다. 에이전트서버 `_record_view` 가 블록 본문을 읽지 않아서 생긴다. 여기서는 허브 데이터만 다룬다.



**요청**

0. **동기화를 다시 돌린다(cae00 AIDataHub 운영 — 보안 설정이라 담당이 정한다).** `AIDH_SYNC_ALLOW_INTERNAL=true` 는 사설 IP·루프백·비표준 포트 차단을 끈다(`url_safety.py:18-20`, 메타데이터 주소는 계속 막는다). 이 값을 켤지, 아니면 내부 주소 몇 개만 허용하는 코드 변경을 요청할지 정해 주십시오. `MXWP_INTERNAL_KEY` 도 넣어야 목록이 401을 면한다. 값은 화면에 띄우지 않는 방법으로 넣는다. 서버가 이 env 를 어느 파일에서 받는지는 미확인이다(env 파일과 프로세스 환경은 읽지 않았다). 3 을 먼저 넣고 켜는 것이 안전하다. 지금 코드로 켜면 상세 조회가 실패한 문서는 다시 빈 「본문」으로 덮인다.

1. **요약 폴백.** 매핑 키 하나를 추가해, 원본 요약이 비면 첫 본문의 앞 300자를 쓴다. 평문화에는 record_sections 와 같은 `db_writer._blocks_to_text` 를 쓴다. import 는 이 파일이 이미 `..routes.records` 를 가져오는 방식(:769)대로 함수 안에서 한다. MXWP DocumentJSON 은 하위 절을 `subsections` 에 둔다(10-15 REST 의 `…0022` content).



```diff

 # api_server/src/api/services/sync_svc.py — transform_record 앞에 둔다

+def _first_body_text(sections: list[Any]) -> str:

+    """요약이 빈 원본의 폴백 — 처음으로 글이 있는 절의 평문(record_sections 와 같은 평문화)."""

+    from ..ingest.db_writer import _blocks_to_text

+

+    for s in sections:

+        if not isinstance(s, dict):

+            continue

+        text = (_blocks_to_text(s.get("blocks") or []) or str(s.get("content_text") or "")).strip()

+        # MXWP DocumentJSON 은 하위 절을 subsections 에 둔다(다른 원본은 children).

+        text = text or _first_body_text(s.get("subsections") or s.get("children") or [])

+        if text:

+            return text

+    return ""

 ...

     # 9. summary — field 또는 template

     summary = _resolve_field(raw, rules, field_key="summary_field", template_key="summary_template")

+    if not summary and rules.get("summary_from_body"):

+        summary = _first_body_text(out["content"].get("sections") or [])[:300] or None

     if summary:

         out["summary"] = summary[:500]

```



```diff

 # config/sync_sources.yml — mxwp mapping_rules

       summary_field: summary

+      summary_from_body: true   # 원본 요약이 비면 첫 본문 앞 300자(namu 위키 171장 등)

```



   yml 은 부팅할 때 sync_sources 에 반영된다(`api_server/src/api/main.py:227-228`). mapping_rules 는 자유 dict 라 새 키를 막는 검증이 없다(`services/sync_bootstrap.py:86-87`).

2. **요약·제목만 바뀌어도 갱신한다.** 1이 실제로 반영되려면 이 변경이 필요하다.



```diff

 # api_server/src/api/ingest/db_writer.py:408-411

     if existing is not None:

-        if existing.content_hash == content_hash:

+        # 본문 해시만 보면 제목·요약만 바뀐 원본(요약 폴백 포함)이 영영 반영되지 않는다.

+        if (existing.content_hash == content_hash

+                and existing.title == record_in.title

+                and (existing.summary or "") == record_in.summary):

             logger.info("Record %s unchanged — skipping", record_in.id)

             return WriteResult(existing, action="skipped")

```



   - `api_server/tests/test_ingest.py:286-296` 의 기대(요약만 바꾸면 skipped)를 `updated` 로 같이 바꾼다. 같은 입력을 두 번 넣는 테스트(`:282-285`, `tests/test_convert_route.py:242-264`)는 그대로 skipped 다.

   - 갱신 경로는 시그니처를 비우고 절을 다시 넣는다(:433-434, :464-465). 그래서 첫 run 에서 저장된 제목·요약이 지금 매핑 결과와 다른 레코드만큼 재임베딩이 돈다. mxwp 는 많아야 320장이다. 다른 두 소스(signalforge-gs·materialtwin)에서 그런 레코드가 몇 장인지는 미확인이다.

   - 태그에도 같은 빈틈이 있다. 태그를 비교에 넣을지는 담당 판단이다.

3. **상세 조회가 실패하면 덮어쓰지 않는다.** 상세 조회를 쓰는 소스는 mxwp 하나다(`detail_endpoint` 는 `sync_sources.yml:97` 에만 있다).



```diff

 # api_server/src/api/services/sync_svc.py:791-828

                     if use_detail:

+                        detail_err: str | None = None

                         try:

                             ...

                             if d_resp.status_code == 200:

                                 ...

                             else:

+                                detail_err = f"detail fetch → {d_resp.status_code}"

                                 logger.warning(

-                                    "detail fetch %s → %s — skipping enrichment",

+                                    "detail fetch %s → %s — skipping record",

                                     detail_url, d_resp.status_code,

                                 )

                         except Exception as exc:  # noqa: BLE001

-                            logger.warning("detail fetch failed: %s — using list-only", exc)

+                            detail_err = f"detail fetch failed: {exc}"

+                            logger.warning("detail fetch failed: %s — skipping record", exc)

+                        if detail_err:

+                            # 목록 응답은 메타뿐이다(:771-773). 그대로 변환하면 있던 본문을 빈 「본문」 한 절로 덮는다.

+                            failed += 1

+                            dead_letter.append({"raw": _redact_for_dead_letter(raw), "error": detail_err})

+                            continue

```



   이렇게 바꾸면 상세 조회가 계속 실패하는 문서가 있을 때 run 이 partial 이 되고, dead_letter 에 사유가 남는다. tests/ 에는 동기화 변환(`transform_record`·`detail_endpoint`)을 다루는 테스트가 없다. 1 과 3 에 테스트를 하나씩 더한다.

4. **이미 본문이 빈 154장.** 0·3 이 들어간 뒤 담당이 다음 두 가지를 본다.

   - ① 첫 mxwp run 의 결과(`GET /api/sync/sources/{id}/runs`, `routes/sync.py:309`)에서 failed·dead_letter 의 사유.

   - ② 한 건(`…0109`)의 MXWP 상세 조회가 키를 넣고 200인지.



   상세 조회가 되는데도 그대로라면, 그 문서는 목록 필터(`status: published`, `sync_sources.yml:137-138`)에서 빠진 것이다. 원본에서 내린 문서면 허브에서도 내린다. 아니면 그 154장만 다시 동기화한다.



**왜** — 목록에서 카드 4장 중 3장은 무엇에 관한 카드인지 제목 몇 글자로만 알 수 있다. 카드 검색도 제목·요약만 보므로 이 카드들은 짧은 제목으로만 찾힌다. 154장은 허브 안의 본문 자체가 비어 있다. 그리고 동기화가 멈춰 있어서 원본이 바뀌어도 허브에 들어오지 않는다.



**확인**



```bash

# cae00 — 0 뒤: 마지막 mxwp 정기 동기화 로그가 「… failed: sync_source base_url unsafe …」 에서 「scheduled sync mxwp: status=…」 로 바뀐다

grep -o '"msg": "scheduled sync mxwp[^"]*' ~/Projects/AIDataHub/deploy/apptainer/logs/uvicorn.log | tail -1

```



```bash

# cae00 — 지금 "427 빈 요약 320 속 빈 154". 0·1·2 뒤 다음 mxwp run 이 끝나면 빈 요약이 본문 있는 만큼(namu 171장 안팎) 준다. 3·4 뒤 속 빈 → 0.

# 목록 조회라 read_count·updated_at 을 건드리지 않는다.

for o in 0 100 200 300 400; do curl -s --noproxy '*' "http://127.0.0.1:8001/api/records/?agent=mx-whitepaper-analyst&limit=100&offset=$o"; echo; done | python3 -c '

import json,sys

it=[i for l in sys.stdin if l.strip() for i in json.loads(l)["items"]]

hollow=lambda s: len(s)==1 and s[0].get("title")=="본문" and not (s[0].get("content_text") or "").strip()

print(len(it), "빈 요약", sum(not (i.get("summary") or "").strip() for i in it), "속 빈", sum(hollow((i.get("content") or {}).get("sections") or []) for i in it))'

```



화면에서도 본다. 포털 전문가 목록에서 mx-whitepaper-analyst 를 전체 화면으로 열고, 카드 목록에 요약 줄이 붙는지 확인한다.



### K6-5. 포털 — 설명 없는 전문가에 「위 설명이 전부입니다」



**지금**

- `frontend/src/components/chat/AgentDeepView.tsx:240-247` 은 역할 문서(`detail.prompt`)가 없으면 늘 「따로 쓴 역할 문서가 없습니다 — 위 설명이 전부입니다.」를 쓴다. 위 설명(`detail.role`, :213)이 비어 있어도 같은 문구가 나온다. `fetchAgentDetail` 은 role 기본값을 '' 로 채운다(`frontend/src/api/chat.api.ts:350`).

- K6-1·K6-2 의 두 전문가가 바로 그 경우다. 위에 아무것도 없는데 「위 설명이 전부」라고 쓴다.

- 조회가 실패했을 때도 오류 문구(:210) 바로 아래에 같은 줄이 나온다. 프로필 블록이 `detail.error` 를 보지 않기 때문이다(:211).

- 이 문구는 리포 전체에서 이 한 곳에만 있다.

- 「코드가 아니라 데이터 문제」라는 같은 판단이 `docs/doc-deliberate/context-notes.md:1173-1177` 에 이미 적혀 있다. 데이터가 정리되면 이 줄은 앞으로 생길 빈 전문가에만 쓰인다.



**요청**



```diff

 // frontend/src/components/chat/AgentDeepView.tsx:241-247

                   {detail.prompt ? (

                     <div className="dv-doc">

                       <TextBlock text={detail.prompt} />

                     </div>

-                  ) : (

+                  ) : detail.role ? (

                     <p className="pv-empty">따로 쓴 역할 문서가 없습니다 — 위 설명이 전부입니다.</p>

+                  ) : (

+                    <p className="pv-empty">설명과 역할 문서가 아직 등록되지 않은 전문가입니다.</p>

                   )}

```



- 이 변경은 :211 을 `detail && !detail.error` 로 바꾸는 변경(세션 만료·조회 실패 항목)과 같은 커밋으로 넣는다. 따로 넣으면 조회가 실패했을 때도 「아직 등록되지 않은 전문가」라고 단정한다.

- 이 문구를 확인하는 프런트 테스트는 없다.

- 프런트를 다시 빌드해야 nginx 가 내보내는 번들(`frontend/dist`)에 들어간다.



**왜** — 없는 설명을 「위 설명」이라고 가리키면, 사용자는 화면이 덜 그려졌다고 읽는다.



**확인**

- 데이터 정리 전이라면 `kooremapper-modelmeta` 를 전체 화면으로 열었을 때 새 문구가 보인다.

- 배포는 `dist/index.html` 이 싣는 번들에 새 문구가 있는지로 확인한다. 아래 결과가 1 이상이어야 한다.



```bash

D=~/Projects/HWAXPortal/frontend/dist; grep -c '아직 등록되지 않은 전문가' "$D/$(grep -o 'assets/index-[^"]*\.js' "$D/index.html" | head -1)"

```



---



## K7. 심의 좌석에 빈 전문가를 앉히면 영어 자리표시 역할이 들어간다



대상 — HWAXAgentServer(`deliberation.py` · 테스트 2파일) · 담당 판단: 에이전트서버 개발

기준 — HWAXAgentServer origin/main `c4e4823` · AIDataHub `b401f88` · 포털 origin/main `90147ac` · (참고) HWAXMcpGateway origin/master `9dc6c01`. 아래 `파일:줄` 은 이 커밋 기준이다.



**지금** — 심의의 지정 좌석은 `_restore_role` 이 `get_agent_session` 으로 역할 원문을 다시 받는다(`deliberation.py:4809`). 이 함수는 `sd.get("description") or sd.get("system_prompt")` 를 아무 손질 없이 쓴다(`deliberation.py:3854`).

설명이 빈 전문가는 AIDataHub 가 자동 틀을 system_prompt 로 내준다(`api_server/src/api/services/recommend_svc.py:833-836` — `"(no description)"`, `You are an assistant for "…"`). 에이전트가 있으면 `get_agent_session` 은 언제나 이 값을 싣는다(`api_server/src/api/mcp_runtime.py:404`, `:414`). 심의는 도구 결과를 크게 받으므로 이 원문이 잘리지 않고 그대로 온다(`deliberation.py:4473`, 기본 2,000,000자 `app.py:644`).

챗은 같은 값을 `_role_doc` 으로 거른다. 자동 틀이면 ""를 돌려주고, 아니면 `this hub` 가 든 머리말부터 뒤를 잘라 낸다(`app.py:4459-4482`, 챗 로더 `app.py:2647-2648`). 같은 리포의 카드 대조 팩도 설명을 먼저 쓰고, 비면 `_role_doc` 으로 거른 system_prompt 를 쓴다(`card_review.py:2651-2654`). 역할이 비면 챗은 `persona_role_empty` 경고를 띄운다(`app.py:3133-3137`). `deliberation.py` 에는 `_role_doc` · `_HUB_GUIDE_RE` · `persona_role_empty` 가 하나도 없다(grep 0건). 챗 쪽 수정(`e147fa5`, 2026-09-13)이 심의에는 오지 않았다.



실측(2026-10-15, AIDataHub `GET /api/agents/<key>/system-prompt`, 읽기만) 결과는 이렇다. dynaforge-report 는 3,038자, kooremapper-modelmeta 는 3,068자다. 둘 다 `You are an assistant for "…"` 로 시작하고 `- Help the user with: (no description)` 줄이 있다. 머리말은 다음과 같다.

- `## First step on every conversation` — get_agent_session 을 먼저 부르라는 지시다.

- `## How to access this hub — use the MCP tools (NOT web fetch)`.

- `## CRITICAL — do NOT use WebFetch / browser fetch on this hub`.

- 본문에 `curl -s ".../api/discover"` 같은 내부 주소 예시도 있다.



796명 전수 조사(2026-10-14)에서 설명이 빈 전문가는 이 둘뿐이다. 둘 다 심의 좌석 풀에 있다. 풀은 키가 빈 항목만 거르고 역할은 싣지 않는다(`app.py:4034-4040`). 그래서 전문가 목록에서 골라 앉힌 좌석은 role 이 ""로 들어온다(포털 `frontend/src/pages/DeliberatePage.tsx:106` → `deliberation.py:1423-1428`).

이어하기는 이전 회차의 소개용 역할(앞 280자)을 그대로 되넘긴다(포털 `frontend/src/state/ChatContext.tsx:792-793`, MCP `mcp_server.py:422-423`). 그래서 이미 돈 심의를 이어가면 fallback 자리에 영문 틀이 들어 있다.

사용자에게 보이는 것은 두 가지다.

- 소개 카드에 영문 틀의 앞 280자가 나온다(`deliberation.py:4885` → 포털 `frontend/src/components/chat/DelibView.tsx:129`).

- 좌석 발언의 시스템 메시지 `전문 영역: …` 에 약 3천 자의 영문 안내가 통째로 들어간다(`deliberation.py:2181`). `_ROLE_CLIP` 기본값이 0, 곧 무절단이기 때문이다(`deliberation.py:137`). 운영 박스에도 `DELIB_ROLE_CLIP` 이 없다(10-14 검증 단계 실측이다. 이번 검토에서는 다시 보지 않았다).



챗과 달리 경고는 없다. 이 결함은 이전부터 있던 것이다(`deliberation.py:3854` 의 식은 `83a53ce`, 2026-08-07). 박스 작업 트리(`7644284`)에서 origin/main 까지의 `deliberation.py` 변경 21줄은 `_restore_role` 을 건드리지 않는다.

미확인 — 실제 심의는 띄우지 않았다(잡이 생긴다). 좌석 화면은 코드와 허브 실측으로 추론했다. 자동 발굴(`recommend_agents`)이나 띵킹 소집이 이 둘을 뽑는지는 재지 않았다.



**요청**

1. `_restore_role` 이 system_prompt 를 챗·카드 대조와 같은 `_role_doc` 으로 거르게 해 주십시오.

   - 설명을 먼저 쓰는 지금 순서는 그대로 둔다(`card_review.py:2654` 와 같은 순서다). 챗은 거른 system_prompt 를 먼저 쓰지만, 순서까지 바꾸면 설명이 있는 좌석의 역할이 달라진다. 이 순서를 지키면 설명이 있는 794명의 좌석 역할은 바뀌지 않는다.

   - 원문은 받았는데(`agent_type` 이 있다) 역할이 비면 영문 틀이나 빈 값 대신 호출자가 준 역할 → 이름 → 키 순으로 앉히고, 그 키를 `empty` 에 적는다. 호출 실패(`why`)와는 따로 센다.

   - 호출자가 준 역할도 `_role_doc` 으로 한 번 거른다. 이어하기가 되넘긴 영문 틀(위 `ChatContext.tsx:792-793`)이 다시 앉지 않게 하려는 것이다.

   - 늦은 import 는 이 리포가 이미 쓰는 방식이다(`card_review.py:2651`, `deliberation.py:1767`).

```diff

-async def _restore_role(tools: dict, key: str, fallback: str = "", why: dict | None = None) -> str:

+async def _restore_role(tools: dict, key: str, fallback: str = "", why: dict | None = None,

+                        empty: set | None = None) -> str:

     """페르소나 역할 원본을 get_agent_session 으로 복원한다(실패 시 fallback).

 

     why 를 주면 **호출이 실패해** 원본을 못 받은 좌석의 사유를 {좌석 키: 사유} 로 적는다(호출부가 알린다).

-    도구 실패는 예외가 아니라 문자열로 온다(✖ · "(tool … error"). 역할 문서가 그냥 빈 전문가는 적지 않는다."""

+    도구 실패는 예외가 아니라 문자열로 온다(✖ · "(tool … error"). 역할 문서가 그냥 빈 전문가는 why 가 아니라

+    empty 에 적는다(주면). 그 좌석은 fallback, 그것도 비면 이름·키로 앉는다."""

+    from app import _role_doc  # noqa: PLC0415 — 순환 방지용 늦은 import

     try:

         raw = await _call(tools, "get_agent_session", {"agent_type": key})

         if why is not None and isinstance(raw, str) and _RA_FAIL_WRAP.match(raw.lstrip()):

             why[key] = _RA_FAIL_WRAP.sub("", raw.strip(), count=1)[:200]

         sess = _first_dict(_parse_json(raw))

         sd = _first_dict(sess.get("data", sess))

-        full = sd.get("description") or sd.get("system_prompt") or ""

+        # ⚠ system_prompt 를 그대로 쓰지 않는다. 설명이 빈 전문가는 허브 자동 틀('You are an assistant for "…"')과

+        #   허브 사용 안내를 받는다. 챗(_persona_meta)·카드 대조(card_review)와 같은 _role_doc 으로 거른다.

+        full = sd.get("description") or _role_doc(str(sd.get("system_prompt") or ""))

         if full:

             return full[:_ROLE_CLIP] if _ROLE_CLIP > 0 else full

+        if sd.get("agent_type"):      # 원문은 받았다 — 호출 실패가 아니라 역할 문서가 빈 전문가다

+            if empty is not None:

+                empty.add(key)

+            # 이어하기는 이전 회차의 소개용 역할을 되넘긴다 — 거기 영문 틀이 실려 올 수 있어 같이 거른다.

+            return _role_doc(fallback) or str(sd.get("name") or "") or key

     except Exception as exc:  # noqa: BLE001 — 실패해도 제공된 role/key 로 참여

         if why is not None:

             why[key] = type(exc).__name__

     return fallback

```

   `_discover`(`deliberation.py:3888`) · 시뮬 좌석(`:4261`) · 띵킹(`thinking.py:419`)은 `empty` 를 넘기지 않는다. 그래도 거르기와 이름·키 대체는 똑같이 받는다. 빈 전문가가 그 길로 앉으면 role 이 "" 나 영문 틀 대신 이름(띵킹은 넘긴 이름)이 된다. 호출부와 가짜 함수(`tests/test_operator_persona.py:253` `fake_role(tools, key, fallback="")`, `tests/test_request_cuts.py:187` `_text(*_a, **_k)`)는 손대지 않아도 된다.

2. 지정 좌석 복원 단계에서 빈 역할을 좌석마다 상태줄로 알리고, 챗과 같은 코드 `persona_role_empty` 로 경고를 한 번 내 주십시오(`deliberation.py:4805-4837`).

```diff

-        _rr_sem, _rr_why = asyncio.Semaphore(max(1, _rr_par)), {}      # 세마포어는 여기서 만든다(_kn_sem 과 같은 까닭)

+        _rr_sem, _rr_why, _rr_empty = asyncio.Semaphore(max(1, _rr_par)), {}, set()   # 세마포어는 여기서 만든다(_kn_sem 과 같은 까닭)

 

         async def _rr_one(p):

             async with _rr_sem:

-                p["role"] = await _restore_role(tools, p["key"], p.get("role") or "", why=_rr_why)

+                p["role"] = await _restore_role(tools, p["key"], p.get("role") or "", why=_rr_why, empty=_rr_empty)

 ...

                 yield _sse("status", {

                     "step": f"역할 복원 {_rr_done}/{len(personas)} — {_rk}"

-                            + (f" · 원문을 받지 못해 호출자가 준 역할로 간다({_rr_why[_rk]})" if _rk in _rr_why else ""),

+                            + (f" · 원문을 받지 못해 호출자가 준 역할로 간다({_rr_why[_rk]})" if _rk in _rr_why else "")

+                            + (" · 등록된 역할 문서가 비었다" if _rk in _rr_empty else ""),

                     "tool": None})

         finally:

             for _t in _rr_tasks:

                 if not _t.done():

                     _t.cancel()

+        if _rr_empty:

+            # 챗의 persona_role_empty(app.py:3134)와 같은 알림 — 종전엔 허브 영문 자동 틀이 역할로 조용히 앉았다.

+            yield _sse("warning", {"code": "persona_role_empty",

+                                   "message": f"{', '.join(sorted(_rr_empty))} 에 등록된 역할 문서가 비어 있습니다 "

+                                              "— 전문가 말투·범위가 적용되지 않습니다."})

```

3. 테스트를 맞춰 주십시오.

   - `tests/test_delib_seats.py:630` 은 호출 문자열을 그대로 고정해 두었다. 그래서 2를 넣으면 `src.index` 가 ValueError 로 깨진다. 고정 문자열을 새 호출문으로 바꿔 주십시오.

```diff

-    restore = src.index('p["role"] = await _restore_role(tools, p["key"], p.get("role") or "", why=_rr_why)')

+    restore = src.index('p["role"] = await _restore_role(tools, p["key"], p.get("role") or "", why=_rr_why, empty=_rr_empty)')

```

   - `tests/test_role_restore_parallel.py` 의 `_Roles` 에 `blank=()` 를 더해 주십시오. `broken` 과 같은 모양이다. blank 좌석은 `{"data": {"agent_type": key, "name": key, "description": "", "system_prompt": 'You are an assistant for "…" …\n\n## How to access this hub — …\n…'}}` 을 돌려준다. 빈 좌석 셋을 앉혀 확인할 것은 다음과 같다.

     - 호출자가 역할을 준 좌석은 그 역할로 앉는다.

     - 역할이 ""인 좌석은 키로 앉는다.

     - 역할 자리에 이전 회차의 영문 틀(앞 280자)을 넘긴 좌석도 키로 앉는다. 이어하기의 경우다.

     - 어느 좌석 role 에도 `You are an assistant` · `this hub` 가 없다.

     - `역할 문서가 비었다` 가 붙은 줄은 그 세 좌석의 줄뿐이고, `받지 못해` 줄은 0건이다.

     - `persona_role_empty` 경고가 한 번 나오고 세 키가 다 들어 있다.



     기존 시험은 `_Roles()` 기본값(blank 없음)을 쓰므로 그대로 통과해야 한다. `"받지 못해"` 1건 단언(같은 파일 `:95`)도 마찬가지다.

   - 설명이 비고 관리자 프롬프트 뒤에 허브 안내가 붙은 좌석도 시험해 주십시오. 입력은 `tests/test_persona_inject.py:15` `RAW_ROLE` 과 같다. 안내를 뗀 본문으로 앉아야 하고, `empty` 에 들면 안 된다.



데이터 쪽 조치, 곧 두 전문가에게 설명을 등록하거나 풀에서 숨기는(지우는) 일은 별건이다(AIDataHub 데이터 담당 · KooRemapper). 이 요청은 그 조치와 상관없이 같은 영문 틀이 좌석에 다시 앉지 않게 막는다.

별건(이 요청에 넣지 않는다) — HWAXMcpGateway `use_experts` 도 system_prompt 를 먼저, 그대로 준다(`gateway.py:2276`, origin/master `9dc6c01`). 받는 쪽이 MCP 클라이언트라 허브 안내가 맞는 자리일 수 있다. 그래서 따로 판단한다.



**왜** — 사용자가 고른 전문가 대신 영문 허브 사용 설명서('get_agent_session 을 먼저 불러라' · 'WebFetch 금지')가 그 좌석의 역할이 되고, 좌석은 그 엉뚱한 지시를 근거로 발언한다. 챗에서는 같은 전문가를 고르면 경고가 뜨는데, 심의에서는 아무 표시도 없다.



**확인**

```bash

# HWAXAgentServer — 반영 커밋에서

.venv/bin/python -m pytest tests/test_role_restore_parallel.py tests/test_delib_seats.py \

  tests/test_continue_seat_role.py tests/test_request_cuts.py \

  tests/test_persona_inject.py tests/test_operator_persona.py -q

```

박스에 반영된 뒤 포털 심의에서 좌석 고르기로 dynaforge-report(또는 kooremapper-modelmeta)를 앉혀 시작하면 다음이 보여야 한다.

- ① 소개 카드의 역할 칸이 `dynaforge-report` 다. 이름이 키와 같아 키가 한 번 더 보인다. `You are an assistant for …` 는 없다.

- ② 활동 패널에 `역할 복원 n/N — dynaforge-report · 등록된 역할 문서가 비었다` 줄이 있다.

- ③ ⚠ 줄에 `dynaforge-report 에 등록된 역할 문서가 비어 있습니다 …` 가 나온다.



③은 뒤에 오는 경고에 덮일 수 있다. 포털은 경고를 하나만 남긴다(`frontend/src/state/ChatContext.tsx:722` → `frontend/src/components/chat/MessageList.tsx:123-124`). 반면 활동 패널은 진행 줄을 쌓아 둔다(`ChatContext.tsx:682-705`). 그래서 화면의 정본 확인은 ②다. MCP 로 띄웠으면 `deliberate_status` 의 `warnings` 에 같은 문구가 남는다(`delib_jobs.py:507-511`, 최근 10건).

데이터 쪽 조치가 먼저 들어가면 박스에 이 길을 탈 전문가가 없다. 그때는 위 테스트로만 확인한다.

미확인 — 요청 1~3 이 다른 테스트에 주는 영향은 `tests/` grep 으로만 보았다. 테스트를 돌려 보지는 않았다(박스 읽기 전용).



---



## K8. HE팀 운영자 — SmartTwin 운영자 도구 0개 · ODB 허브 운영자 없음 · 앱 빠짐 문구



대상 — HWAXPortal(`infra/personas/he-team.json` · `infra/scripts/sync-he-personas.py` · `backend/tests/test_he_personas.py` · `frontend/src/components/chat/AgentFacts.tsx` · `AgentDeepView.tsx`) · HWAXAgentServer(`app.py`) · 담당 판단: 포털 개발(정본·동기화·화면 문구) · 에이전트서버 개발(챗 운영자 문구)



기준 — 포털 origin/main `90147ac` · 에이전트서버 origin/main `c4e4823` · AIDataHub `b401f88` · 게이트웨이 `9dc6c01`(origin/master). 아래 `파일:줄` 은 이 커밋 기준이다. 정본과 동기화 스크립트는 cae00 작업트리 `e6a8e52` 와 origin/main 이 같다(`git diff` 빈 결과). cae00 실측은 2026-10-14~15 이고 읽기만 했다. 「메모리에서 돌렸다」는 origin/main 의 `plan()` 에 cae00 `/tools-map` 과 AIDataHub GET 만 물린 것이다. 쓰기는 없었다.



**지금**



ODB 허브 운영자가 없다.

- cae00 AIDataHub 의 he-* 는 15명이다(전체 796명). 전부 dev 에서 만든 행이다(created_at 2026-09-11T17:01:56~57Z). dev 덤프로 들어왔다. update-all 은 돌 때마다 dev 덤프를 merge 한다(`infra/scripts/update-all.sh:738-740`). 처음에 merge 로 들어왔는지 복원으로 들어왔는지는 미확인이다.

- 정본 17명 중 `he-cad-odbhub` 와 `he-data-arp` 가 없다(`GET :8001/api/agents/he-cad-odbhub` → 404). odb-hub 는 cae00 게이트웨이에 도구 39개로 붙어 있다. ARP 는 게이트웨이에 없다(임시 직접 타일). 그래서 ARP 운영자는 빠지는 게 맞다.

- 절차서는 cae00 에서 동기화를 돌리라고 한다(`docs/cae00-deploy-guide.md:414-420`, HE 운영자 동기화 체크리스트(`docs/` 안 `checklist.md:18`) 미체크). 그런데 지금 정본으로는 돌릴 수 없다. origin/main 의 `plan()` 을 메모리에서 돌렸더니 오류가 2건 나왔다.

  - `he-doc-reportarchive: writes 에 이 앱에 없는 도구 — upload_from_url`(`he-team.json:443`). cae00 에는 simflow 도 붙어 있다. 그래서 게이트웨이는 이 도구를 `reportarchive_upload_from_url` 과 `simflow_upload_from_url` 이라는 이름으로만 낸다. 접두 없는 이름은 별칭 규칙(`sync-he-personas.py:115-116`)으로도 통과하지 못한다.

  - `he-research-web: key_tools 에 이 앱에 없는 도구 — search_web`(`he-team.json:555`). cae00 의 웹 리서치 브로커는 도구가 7개이고 search_web 이 없다. `describe_search_status` 를 부르면(10-15) 사유가 나온다. 「일반 웹 검색 공급자가 지정되지 않았습니다(WEB_PROVIDER=brave|searxng). (그래서 search_web 을 등록하지 않았습니다.)」 즉 박스 설정에 따라 생기고 없어지는 도구다.

  - 오류가 하나라도 있으면 `main()` 은 아무것도 만들거나 고치지 않고 2 를 돌려주고 끝난다(`sync-he-personas.py:160-163`). 미리보기도 건너뜀 줄과 ✗ 만 찍는다. `+`·`~` 는 하나도 보이지 않는다.



SmartTwin 운영자는 cae00 에서 도구가 0개다. stcx 가 붙어도 지금 구조로는 고칠 길이 없다.

- 정본은 앱 둘을 모두 필수로 적는다(`he-team.json:95` `["smart-twin-mcp", "smart-twin-cluster"]`). 동기화는 앱이 하나라도 없으면 그 페르소나를 통째로 건너뛴다(`sync-he-personas.py:105-108`).

- cae00 에 붙일 앱은 smart-twin-mcp(stcx :5013) 하나다. smart-twin-cluster(:5012, slurm 19종)는 프로비저너가 관리하는 키가 아니다(`HWAXMcpGateway/provision-config.sh:806-808`). 작업지시에도 없다. 그래서 SmartTwinMCP 가 붙은 뒤에도 이 운영자는 계속 건너뛰어진다. 메모리에서 smart-twin-mcp 도구만 더한 가짜 맵으로도 건너뛰었다. 그러면 dev 판이 그대로 남는다(「도구 37개」 · slurm_* 입구 도구 · `mcp_apps` 둘).

- apps 에서 cluster 만 빼서도 안 된다. key_tools·writes·confirm 에 있는 slurm_* 6개(`he-team.json:122-124`)가 「이 앱에 없는 도구」로 걸린다. 그러면 동기화 전체가 멈춘다. dev 에서는 slurm 도구도 잃는다.



앱이 빠진 운영자를 두고 화면과 챗이 서로 다른 말을 한다.

- 지금 he-sim-smarttwin 은 앱 둘이 다 없다. `/tools-map` 606개 중 smart-twin-* 는 0개다. `127.0.0.1:15013` 은 LISTEN 상태지만 `/mcp` 는 Empty reply 다(curl 52, 10-15 실측). `POST :9009/catalog/agent` 도 두 앱 모두 `tool_count 0 · connected false` 를 돌려준다.

- 상세칸 머리말은 늘 「MCP 운영자 — 대화하면 이 앱의 도구를 직접 호출해 답합니다」다(`AgentFacts.tsx:29`). 그런데 바로 밑 두 줄은 「이 서버에 연결 안 됨」이다(`:34`). 이 조각은 상세칸 셋이 같이 쓴다(`PersonaBrowser.tsx:265` · `SeatBrowser.tsx:202` · `AgentDeepView.tsx:221`).

- 전체 화면에서 카드가 없을 때 나오는 문구는 `detail.operator` 만 본다. 그래서 「…앱 도구를 직접 호출해 답합니다」가 나온다(`AgentDeepView.tsx:297-298`).

- 챗 한 턴에 세 메시지가 같이 뜬다.

  - 상태: 「지정 앱 2개 → 도구 0개 우선」(`app.py:3004`).

  - 경고: 「…연결돼 있지 않습니다 — 그 앱 도구 없이 답합니다」(`:3097-3101`).

  - 상태: 「he-sim-smarttwin — Smart Twin, 시뮬레이션 클러스터 도구로 답합니다」(`:3113`).

- 운영자 블록(`app.py:3106-3113`)은 `_op_missing` 을 보지 않는다. 그래서 [중요] 지시 「그 도구를 호출하겠다고 말하지 말라」(`:3102-3104`) 바로 뒤에 「{앱} 의 도구를 직접 호출해 답하라」가 붙는다. 모델은 서로 반대인 지시 둘을 받는다.

- 앱 하나만 빠진 경우도 문제다. stcx 를 개통한 뒤에는 cluster 만 빠진다. 그래도 경고와 지시는 「도구 없이 답하라」다. 붙어 있는 Smart Twin 도구까지 쓰지 말라는 뜻으로 읽힌다. 이것은 미확인이다. :5013 이 아직 안 떠서 실제 답은 보지 못했다.

- 「Smart Twin」이라는 이름은 `_pretty_group` 의 폴백이다(`app.py:1551-1553`, `:1584`). 게이트웨이 라벨은 「시뮬레이션 실행(SmartTwin)」이다(`HWAXMcpGateway/gateway.py:1609`). 연결 안 된 앱은 이 라벨이 오지 않는다. `_GROUP_LABEL`(`app.py:1510-1516`)에도 smart-twin-mcp 가 없다.



**요청**



1. **정본의 도구 이름 고치기 — `infra/personas/he-team.json`.**

   - reportarchive 는 접두 별칭으로 적는다. 별칭은 겹치는 앱이 없는 박스에서도 통과한다(`sync-he-personas.py:115-116`, 정본 `_doc`, 그 규칙을 보는 시험 `test_he_personas.py:207-226`).

   - 본문 문구도 같이 맞춘다. cae00 에서는 `upload_file` 도 `reportarchive_upload_file` 이라는 이름으로만 나온다.

   - search_web 은 key_tools 에서만 뺀다. 운영자의 앱 도구는 전부 우선 묶인다(`app.py:3002-3003`). 그래서 dev 에서 search_web 은 그대로 묶이고, 입구 도구 자리에서만 빠진다. 할 수 있는 일 줄에는 박스마다 있고 없음을 적는다. 작업 순서 첫 줄이 이미 describe_search_status 로 켜진 소스를 먼저 보게 한다.

```diff

@@ he-doc-reportarchive — pitfalls(:440) · writes(:443)

-        "로컬 파일은 reportarchive_prepare_upload(셸 curl), 웹 파일은 upload_from_url 로 올린다. upload_file(base64)은 최후수단이다."

+        "로컬 파일은 reportarchive_prepare_upload(셸 curl), 웹 파일은 reportarchive_upload_from_url 로 올린다. reportarchive_upload_file(base64)은 최후수단이다."

-      "writes": ["create_report_draft", "create_report_from_preset", "create_report_from_run", "update_report_draft", "append_rows", "patch_cells", "copy_report", "save_report_as_preset", "add_report_tags", "set_report_folders", "link_reports", "reply_comment", "request_composite_item", "upload_from_url", "reportarchive_prepare_upload"],

+      "writes": ["create_report_draft", "create_report_from_preset", "create_report_from_run", "update_report_draft", "append_rows", "patch_cells", "copy_report", "save_report_as_preset", "add_report_tags", "set_report_folders", "link_reports", "reply_comment", "request_composite_item", "reportarchive_upload_from_url", "reportarchive_prepare_upload"],

@@ he-research-web — can(:536) · key_tools(:555)

-        "검색 — search_internal(수집 원장, 사외로 안 나감), search_scholar(arXiv·Crossref·OpenAlex·PubMed), search_web(일반 웹).",

+        "검색 — search_internal(수집 원장, 사외로 안 나감), search_scholar(arXiv·Crossref·OpenAlex·PubMed), search_web(일반 웹 — 공급자가 지정된 박스에만 있다).",

-      "key_tools": ["describe_search_status", "search_internal", "search_scholar", "search_web", "get_page", "search_in_page", "get_quote"],

+      "key_tools": ["describe_search_status", "search_internal", "search_scholar", "get_page", "search_in_page", "get_quote"],

```



2. **선택 앱 `optional` 추가 — 박스마다 붙은 앱이 다른 운영자.**

   - 페르소나에 `optional` 칸을 둔다. 그 `app` 이 게이트웨이에 붙어 있을 때만 그 칸들을 정본 뒤에 잇는다. 없으면 빼고 만든다. 그 페르소나를 건너뛰지는 않는다.

   - 뒤의 도구 이름 검사·라벨·`mcp_apps`(`:109-141`)는 합쳐진 `p` 를 그대로 쓴다. 그래서 더 고칠 곳이 없다.

   - 「빼고 만든다」는 `skipped` 에 넣지 않는다. 넣으면 끝 줄 「건너뜀 N」(`:212`)이 실제로 만든 페르소나까지 센다. 기존 시험 `test_접두_이름은_겹치는_앱이_빠진_게이트웨이에서도_통과한다`(`test_he_personas.py:224-225`, `assert not errors and not skipped`)도 he-sim-smarttwin 에서 깨진다. 메모리에서 시험 판정을 돌려 확인했다. 그래서 선택 인자 `notes` 로 따로 받는다. 반환값은 지금처럼 셋이라 기존 시험은 그대로 돈다.

```diff

@@ infra/scripts/sync-he-personas.py — plan() 앞 · plan() 머리(:88-89)

+# 박스마다 붙은 앱이 다르다(cae00 에는 smart-twin-cluster 가 없다). 그 앱 몫의 칸은 페르소나의 optional 에 묶고,

+# 앱이 이 게이트웨이에 붙어 있을 때만 정본 뒤에 잇는다. 없어도 그 페르소나는 건너뛰지 않는다.

+_LISTS = ("can", "workflow", "concepts", "pitfalls", "samples", "key_tools", "writes", "confirm")

+

+

+def _with_optional(p: dict, by_app: dict) -> tuple[dict, list[str]]:

+    """정본 한 명 → 붙어 있는 선택 앱의 칸을 이은 사본, 빠진 선택 앱."""

+    q = {**p, "apps": list(p["apps"]), **{f: list(p[f]) for f in _LISTS}}

+    absent: list[str] = []

+    for o in p.get("optional") or []:

+        if o["app"] not in by_app:

+            absent.append(o["app"])

+            continue

+        q["apps"].append(o["app"])

+        for f in _LISTS:

+            q[f] += o.get(f) or []

+    return q, absent

+

+

-def plan(spec: dict, tmap: dict) -> tuple[list[dict], list[str], list[str]]:

-    """정본 + 게이트웨이 → 올릴 페이로드 목록, 건너뛴 사유, 오류."""

+def plan(spec: dict, tmap: dict, notes: list[str] | None = None) -> tuple[list[dict], list[str], list[str]]:

+    """정본 + 게이트웨이 → 올릴 페이로드 목록, 건너뛴 사유, 오류. notes 를 주면 선택 앱을 빼고 만든 페르소나를 적는다."""

@@ plan() :105-109

         missing = [a for a in p["apps"] if a not in by_app]

         if missing:

             skipped.append(f"{key}: 이 게이트웨이에 앱이 없다({', '.join(missing)}) — 붙어 있는 박스에서 돌리면 생긴다")

             continue

+        p, absent = _with_optional(p, by_app)

+        if absent and notes is not None:

+            notes.append(f"{key}: {', '.join(absent)} 없이 만든다(선택 앱)")

         tools = sorted(t for a in p["apps"] for t in by_app[a])

@@ main() :157-159

-    rows, skipped, errors = plan(spec, tmap)

+    notes: list[str] = []

+    rows, skipped, errors = plan(spec, tmap, notes)

     for s in skipped:

         print(f"  · 건너뜀 {s}")

+    for n in notes:

+        print(f"  · 일부 {n}")

```

   정본은 아래처럼 옮긴다. 옮기는 줄의 문구는 그대로 둔다.

```diff

@@ he-sim-smarttwin (:94-130)

-      "apps": ["smart-twin-mcp", "smart-twin-cluster"],

+      "apps": ["smart-twin-mcp"],

-      "summary": "낙하·충격 LS-DYNA 해석을 SmartTwin 으로 제출하고, 잡 상태·실패 진단·재실행과 Slurm 클러스터 조회를 맡는 HE팀 운영자.",

+      "summary": "낙하·충격 LS-DYNA 해석을 SmartTwin 으로 제출하고, 잡 상태·실패 진단·재실행을 맡는 HE팀 운영자. Slurm 클러스터 조회는 그 앱이 붙은 박스에서만 한다.",

   (can :103 · concepts :114 · pitfalls :120 · samples :129 의 클러스터 줄은 아래 optional 로 옮긴다)

-      "key_tools": ["smarttwin_scenario_options", "smarttwin_submit", "list_recent_jobs", "smarttwinmcp_job_status", "get_job_details", "job_diagnose", "slurm_list_jobs", "slurm_job_results", "slurm_job_log"],

-      "writes": ["smarttwin_submit", "fullangle_drop_simulation", "single_drop_simulation", "smarttwinmcp_submit_job", "submit_lsdyna_job", "slurm_submit_job", "job_rerun", "job_postprocess", "job_collect", "catalog_run"],

-      "confirm": ["job_stop", "slurm_job_control", "slurm_node_set_state"],

+      "key_tools": ["smarttwin_scenario_options", "smarttwin_submit", "list_recent_jobs", "smarttwinmcp_job_status", "get_job_details", "job_diagnose"],

+      "writes": ["smarttwin_submit", "fullangle_drop_simulation", "single_drop_simulation", "smarttwinmcp_submit_job", "submit_lsdyna_job", "job_rerun", "job_postprocess", "job_collect", "catalog_run"],

+      "confirm": ["job_stop"],

+      "optional": [{

+        "app": "smart-twin-cluster",

+        "can": ["클러스터 조회(읽기 전용) — slurm_list_jobs·slurm_list_nodes·slurm_job_results·slurm_job_log·slurm_job_accounting."],

+        "concepts": ["smart-twin-cluster 도구는 조회 전용이고, smart-twin-mcp 도구가 실제로 돌린다."],

+        "pitfalls": ["d3plot·binout 은 바이너리라 slurm_job_results 는 파일 목록만 준다. 수치 분석은 DynaForge 리포트 도구 몫이다."],

+        "samples": ["지금 클러스터에 비어 있는 노드 몇 개야?"],

+        "key_tools": ["slurm_list_jobs", "slurm_job_results", "slurm_job_log"],

+        "writes": ["slurm_submit_job"],

+        "confirm": ["slurm_job_control", "slurm_node_set_state"]

+      }],

```

   - 정본 `_doc`(`:2`)와 스크립트 독스트링(`:13-17`)에 `optional` 설명을 한 줄씩 더한다.

   - `backend/tests/test_he_personas.py` 에 시험을 한 건 더한다.

     - smart-twin-mcp 도구만 있는 가짜 맵이면 he-sim-smarttwin 이 errors·skipped 없이 만들어져야 한다. `notes` 는 한 줄이고, `mcp_apps == ["smart-twin-mcp"]` 여야 한다. 프롬프트와 key_tools 에는 `slurm_` 이 없어야 한다.

     - cluster 도구도 있는 맵이면 `mcp_apps` 가 둘이고 key_tools 에 `slurm_job_log` 가 있어야 한다. `notes` 는 비어야 한다.

   - 기존 시험에 미치는 영향.

     - 겹침 시험(`:169-187`)은 최상위 key_tools·writes·confirm 만 보고 optional 안의 이름은 보지 않는다. 지금 옮기는 slurm_* 는 겹치는 데가 없다.

     - `:186` 의 `smarttwinmcp_submit_job` 은 writes 에 남는다.

     - `test_access_control.py:47` 은 `["smart-twin-mcp"]` 로도 플랫폼을 찾는다(`access.yaml:82`).

   - 권한 판정 `agent_guard.py:24-38` `he_apps` 는 `apps` 만 읽는다. 두 앱이 같은 plat:smarttwin 이라(`access.yaml:77-82`) 판정은 그대로다. 나중에 다른 플랫폼의 앱을 선택 앱으로 두면 `he_apps` 에도 넣어야 한다.

   - 메모리 시뮬레이션 결과(cae00 `/tools-map` 기준, 쓰기 없음)는 다음과 같다.

     - 1 과 2 를 넣으면 오류는 0건이고 만들 행은 15개다. `+` 1 · `~` 3 · 그대로 11 이다.

     - smart-twin-mcp 만 있는 가짜 맵에서는 he-sim-smarttwin 이 만들어지고 `mcp_apps` 가 `["smart-twin-mcp"]` 다.

     - dev 처럼 앱이 둘 다 있으면 he-sim-smarttwin 의 response_config 는 지금과 같다. 프롬프트는 옮긴 줄이 칸 끝으로 가서 바뀐다.

     - 그래서 반영 뒤 dev 에서는 he-sim-smarttwin · he-doc-reportarchive · he-research-web 이 한 번씩 `~` 로 뜬다.

   - cluster 몫은 이름이 slurm_ 으로 시작하는 도구만으로 나눴다. `list_recent_jobs` · `get_job_details` · `job_diagnose` 같은 나머지가 전부 smart-twin-mcp 쪽인지는 미확인이다. dev `/tools-map` 으로 확인해 주십시오.



3. **챗 운영자 문구 — HWAXAgentServer `app.py`.**

   - 붙어 있는 앱만 말한다. 붙은 앱이 하나도 없으면 「직접 호출해 답하라」를 싣지 않는다.

   - `_op_missing` 은 `/tools-map` 을 받았을 때만 채워진다(`:3009-3011`). 받지 못하면 지금처럼 모든 앱 이름으로 답한다.

   - 기존 시험 `tests/test_operator_persona.py` 가 보는 「지정 앱 1개」·`operator_app_missing`·「연결돼 있지 않다」는 그대로 남는다.

```diff

@@ :3002-3005 — 그 앱 도구가 정말 없을 때만 '0개 우선' 대신 없다고 말한다

             _from_apps = [n for n, gk in _tm.items() if gk in apps and n not in pinned]

             pinned = list(dict.fromkeys([*pinned, *first, *sorted(_from_apps)]))

-            yield _sse("status", {"step": f"지정 앱 {len(apps)}개 → 도구 {len(_from_apps)}개 우선",

+            # 매핑을 못 받았으면(_tm 빈 값) 없다고 단정하지 않는다. _from_apps 는 콕 집은 도구를 빼고 센다.

+            _no_tools = bool(_tm) and not any(gk in apps for gk in _tm.values())

+            yield _sse("status", {"step": (f"지정 앱 {len(apps)}개 — 이 서버에는 그 앱 도구가 없습니다" if _no_tools

+                                           else f"지정 앱 {len(apps)}개 → 도구 {len(_from_apps)}개 우선"),

                                   "tool": None, "tools_used": apps})

@@ :3097-3104 — 일부만 빠졌으면 붙은 앱으로 답한다고 말한다

+        _op_ok = [a for a in op_apps if a not in _op_missing]

         if _op_missing:

             _ml = ", ".join(_app_label(a) for a in _op_missing)

+            _okl = ", ".join(_app_label(a) for a in _op_ok)

             yield _sse("warning", {"code": "operator_app_missing",

                                    "message": f"{agent_key} 가 모는 앱({_ml})이 이 게이트웨이에 연결돼 있지 않습니다 — "

-                                              "그 앱 도구 없이 답합니다."})

+                                              + (f"{_okl} 도구로 답합니다." if _okl else "그 앱 도구 없이 답합니다.")})

             sys_prompt += (f"\n\n[중요] 이 운영자가 모는 앱({_ml})의 도구가 지금 연결돼 있지 않다. 그 도구를 "

-                           "호출하겠다고 말하지 말고, 연결되지 않았다는 사실을 먼저 밝힌 뒤 도구 없이 답할 수 "

-                           "있는 범위만 답하라.")

+                           "호출하겠다고 말하지 말고, 연결되지 않았다는 사실을 먼저 밝힌 뒤 "

+                           + (f"연결된 {_okl} 의 도구로 할 수 있는 범위에서 답하라." if _okl

+                              else "도구 없이 답할 수 있는 범위만 답하라."))

@@ :3110-3113 — 운영자 블록이 [중요] 와 반대로 말하지 않게

-            _opl = ", ".join(_app_label(a) for a in op_apps) or "지정 앱"

-            sys_prompt += (f"\n\n[HE팀 MCP 운영자 — 사용자가 선택]\n너는 '{agent_key}' 운영자다. 아래 사전 지식과 "

-                           f"작업 순서를 따라 {_opl} 의 도구를 직접 호출해 답하라.\n{persona.get('role') or ''}")

-            yield _sse("status", {"step": f"{agent_key} — {_opl} 도구로 답합니다", "tool": None})

+            if op_apps and not _op_ok:

+                sys_prompt += (f"\n\n[HE팀 MCP 운영자 — 사용자가 선택]\n너는 '{agent_key}' 운영자다. 모는 앱이 이 서버에 "

+                               f"연결돼 있지 않으니 아래 사전 지식으로 답할 수 있는 범위만 답하라.\n{persona.get('role') or ''}")

+                yield _sse("status", {"step": f"{agent_key} — 모는 앱이 연결돼 있지 않아 도구 없이 답합니다", "tool": None})

+            else:

+                _opl = ", ".join(_app_label(a) for a in _op_ok) or "지정 앱"

+                sys_prompt += (f"\n\n[HE팀 MCP 운영자 — 사용자가 선택]\n너는 '{agent_key}' 운영자다. 아래 사전 지식과 "

+                               f"작업 순서를 따라 {_opl} 의 도구를 직접 호출해 답하라.\n{persona.get('role') or ''}")

+                yield _sse("status", {"step": f"{agent_key} — {_opl} 도구로 답합니다", "tool": None})

@@ :1512 — 연결 안 된 앱도 게이트웨이와 같은 이름으로

     "signalforge": "SignalForge VOC", "smart-twin-cluster": "시뮬레이션 클러스터",

+    "smart-twin-mcp": "시뮬레이션 실행(SmartTwin)",

```



4. **화면 문구 — `AgentFacts.tsx` · `AgentDeepView.tsx`.**

   - 앱이 전부 `connected === false` 일 때만 문구를 바꾼다. `null`(매핑을 못 받음)일 때는 연결이 없다고 단정하지 않는다. 에이전트서버와 같은 규칙이다.

   - `AgentFacts.tsx` 에서 컴포넌트가 아닌 함수를 export 하면 `react-refresh/only-export-components`(`frontend/.eslintrc.cjs`)에 걸린다. `pnpm lint` 는 `--max-warnings 0` 이다. 그래서 `ChatContext.tsx:1045` 처럼 한 줄 끈다.

```diff

@@ frontend/src/components/chat/AgentFacts.tsx:22-29

+/** 운영자의 앱이 이 서버 게이트웨이에 하나도 안 붙었다 — '도구로 답한다' 고 말하면 안 되는 경우.

+ *  connected 가 null(매핑을 못 받음)이면 없다고 단정하지 않는다(에이전트서버 _op_missing 과 같은 규칙). */

+// eslint-disable-next-line react-refresh/only-export-components

+export function operatorOffline(detail: AgentDetail | null | undefined): boolean {

+  const apps = detail?.apps ?? [];

+  return !!detail?.operator && apps.length > 0 && apps.every((a) => a.connected === false);

+}

+

 export function OperatorApps({ detail }: { detail: AgentDetail }) {

   …

-      <h4 className="pv-detail-h">MCP 운영자 — 대화하면 이 앱의 도구를 직접 호출해 답합니다</h4>

+      <h4 className="pv-detail-h">

+        {operatorOffline(detail)

+          ? 'MCP 운영자 — 이 서버에는 이 운영자의 앱이 연결돼 있지 않아 지금은 도구로 답하지 못합니다'

+          : 'MCP 운영자 — 대화하면 이 앱의 도구를 직접 호출해 답합니다'}

+      </h4>

@@ frontend/src/components/chat/AgentDeepView.tsx:12 · :297-298

-import { OperatorApps } from './AgentFacts';

+import { OperatorApps, operatorOffline } from './AgentFacts';

 …

                     : detail?.operator

-                      ? '지식카드가 없습니다 — 이 전문가는 지식카드가 아니라 앱 도구를 직접 호출해 답합니다.'

+                      ? operatorOffline(detail)

+                        ? '지식카드가 없습니다 — 이 운영자의 앱이 이 서버에 연결돼 있지 않아 지금은 도구로도 답하지 못합니다.'

+                        : '지식카드가 없습니다 — 이 전문가는 지식카드가 아니라 앱 도구를 직접 호출해 답합니다.'

                       : '연결된 지식카드가 없습니다.'}

```

   - `fetchAgentDetail` 은 빈 값 위에 응답을 덮는다(`chat.api.ts:348-362`). 그래서 `apps` 가 없으면 `operatorOffline` 은 false 이고 지금 문구가 나온다.



5. **(선택) update-all 뒤에 동기화 미리보기 돌리기 — `infra/scripts/update-all.sh`.**

   - update-all 은 돌 때마다 dev 덤프를 merge 한다. 규칙은 updated_at 이 같거나 더 최신인 쪽이 이기는 것이다. cae00 행의 updated_at 이 비어 있으면 dev 가 이긴다(`update-all.sh:738-740`, AIDataHub `deploy/apptainer/merge-from-drive.sh:4` · `:54` · `:119`).

   - 그래서 dev 에서 나중에 동기화하면 cae00 에서 만든 판이 dev 판으로 덮일 수 있다(도구 수 · `mcp_apps` · key_tools). 이것은 코드만 읽고 내린 판단이다. 실제로 덮인 예는 아직 없다(미확인).

   - merge 뒤에 `sync-he-personas.py` 미리보기(쓰기 없음)를 돌리게 해 주십시오. ✗·`+`·`~` 가 나오면 `warn` 으로 알리면 된다.



넣지 않은 것 — 아래 셋은 이번 요청에 넣지 않았다. 챗 경고가 이미 뜨기 때문이다.

- 고르기 버튼(`PersonaBrowser.tsx` · `SeatBrowser.tsx`)에 「앱 연결 안 됨」 표시를 다는 것. 원하면 `operatorOffline` 을 그대로 쓰면 된다.

- 손으로 심의 좌석에 앉힌 운영자에게 같은 경고를 내는 것. `deliberation.py` 에는 `mcp_apps` 처리가 없다.

- 프롬프트 머리줄에 박힌 고정 도구 수(「도구 37개」)를 없애는 것.



**왜** — ODB 허브는 cae00 에 붙어 있는데 HE팀이 ODB 운영자를 고를 수 없다. SmartTwin 운영자는 도구가 0개인데 화면은 「도구로 답한다」고 하고, 모델은 서로 반대인 지시 둘을 받는다. 지금 정본 구조로는 stcx 가 붙어도 이 운영자를 cae00 판으로 고칠 수 없다.



**확인**

```bash

# dev — 포털 시험·lint

cd backend && .venv/bin/python -m pytest -q tests/test_he_personas.py tests/test_access_control.py

cd ../frontend && pnpm lint && pnpm build

# dev — 에이전트서버 시험

cd ~/Projects/HWAXAgentServer && python -m pytest -q tests/test_operator_persona.py

# cae00 — git pull 뒤. 기본은 미리보기다(GET 만. --apply 가 없으면 쓰지 않는다 — sync-he-personas.py:174-200)

cd ~/Projects/HWAXPortal && python3 infra/scripts/sync-he-personas.py

#   기대: ✗ 없음

#         · 건너뜀 he-sim-smarttwin(smart-twin-mcp) · he-data-arp(arp)

#         + he-cad-odbhub 새로 만든다 (1589자)

#         ~ he-doc-reportarchive 고친다: system_prompt(도구 70→71)

#         ~ he-research-web 고친다: system_prompt, response_config(도구 8→7)

#         ~ he-expert-risk 고친다: system_prompt(도구 14→26)

#         미리보기(--apply 로 반영) — 새로 1 · 고침 3 · 그대로 11 · 건너뜀 2

python3 infra/scripts/sync-he-personas.py --show he-research-web | sed -n 3p   # 「웹 리서치 브로커 도구 7개를 직접 호출해 일한다.」

```

- 화면 — 전문가 목록에서 「SmartTwin 시뮬레이션 운영자」를 연다. 상세칸 머리말과 전체 화면의 빈 카드 문구에 「연결돼 있지 않아」가 나와야 한다. 다른 운영자(예: StepForge)는 지금 문구 그대로여야 한다.

- 챗 — 이 운영자를 골라 한 번 묻는다. 상태는 「지정 앱 2개 — 이 서버에는 그 앱 도구가 없습니다」와 「he-sim-smarttwin — 모는 앱이 연결돼 있지 않아 도구 없이 답합니다」 둘이어야 한다. 경고는 「…연결돼 있지 않습니다 — 그 앱 도구 없이 답합니다.」 한 줄이어야 한다. 「도구 0개 우선」과 「… 도구로 답합니다」는 없어야 한다. 앱 이름은 「시뮬레이션 실행(SmartTwin), 시뮬레이션 클러스터」로 나와야 한다. `POST :9009/catalog/agent` 의 smart-twin-mcp 라벨도 「시뮬레이션 실행(SmartTwin)」이어야 한다.



**운영 쪽 (요청 아님)**

1. 포털을 pull 한 뒤 위 미리보기를 본다. ODB 운영자를 둘지는 사용자가 정한다. 두기로 하면 `--apply` 한다. 같은 실행이 위의 `~` 셋도 고친다. ODB 사전 지식은 아직 뼈대뿐이다. workflow·pitfalls·key_tools 를 채워 다시 반영해야 한다(`docs/cae00-deploy-guide.md:423-424`).

2. stcx SmartTwinMCP 가 :5013 에서 실제로 뜨면 게이트웨이에 등록한다. 10-15 현재 `127.0.0.1:15013/mcp` 는 Empty reply 다.

   - `HWAXMcpGateway/provision.env` 에 `SMARTTWIN_MCP_URL=http://127.0.0.1:15013/mcp` 를 넣고 `update-collab.sh --no-portal --no-risk` 를 돌린다(`knox-bridge/docs/STCX-SMARTTWIN-WORKORDER.md:50` · `:53`).

   - `gateway_config.json` 에 손으로 넣지 않는다. 관리 키라서 다음 프로비저닝이 지운다(`provision-config.sh:806-808`).

3. 등록한 뒤 미리보기를 다시 본다.

   - he-sim-smarttwin 이 `~` 로 나와야 한다. 행은 dev 판으로 이미 있다. 「· 일부 he-sim-smarttwin: smart-twin-cluster 없이 만든다(선택 앱)」 줄도 떠야 한다.

   - 지금 cae00 에서 smart-twin-mcp 와 겹칠 이름은 `submit_job`(ste)·`job_status`(heax-step_forge) 둘이다. 정본은 이 둘을 이미 접두 이름으로 적었다(`he-team.json:122` · `:123`). 나머지 이름이 정본과 같은지는 :5013 이 떠야 안다(미확인). 다르면 ✗ 가 난다. 그때는 이름을 고치는 요청을 다시 낸다.

   - ✗ 가 없으면 `--apply` 한다.

4. update-all 을 돌린 뒤에는 미리보기를 한 번 더 본다. `~` 가 다시 뜨면 dev merge 가 덮었거나 그 박스의 도구 수가 바뀐 것이다. 어느 쪽이든 `--apply` 로 cae00 판을 다시 올린다.



---



## K9. (선택) 모의해석(SIM) 카드가 원문 JSON 한 덩어리로 보인다



대상 — HWAXAgentServer(origin/main `c4e4823`) · HWAXPortal(`90147ac`, 바꿀 것 없음) · AIDataHub(`b401f88`, 근거만). 담당 판단 — 에이전트서버 개발. 선택 항목이다. 안 고쳐도 잃는 내용은 없다.



**지금** — kooremapper-modelmeta 의 카드 3장(`SIM-MX-CAE-2026-0000000010`·`…011`·`…012`, data_type SIM · doc_type model_meta)을 열면 「원문(JSON)」 섹션 하나만 나온다. 10-15 실측(`POST 127.0.0.1:9009/catalog/record`, 읽기 호출)에서 셋 다 `sections=['원문(JSON)']` · `table=None` · `sources=0` · `truncated=False` 다. 크기는 1,506자/86줄 · 2,312자/119줄 · 1,903자/89줄이다. 잘리거나 빠진 내용은 없다.

- 원인 — `_record_view` 는 DOC(`sections`)와 DATA(`headers`·`rows`) 두 모양만 푼다(`app.py:4598-4600`). SIM 본문은 AIDataHub `SimContent`(`api_server/src/api/schemas/sim.py:30-53`, `extra="allow"`) 모양이라 둘 다 아니다. 이 3장의 최상위 키는 inputs·solver·outputs·runtime·eng_meta·components·attachments·connectivity·solver_version 이다(`…010` 에는 attachments 가 없다). 그래서 `app.py:4631-4636` 이 sources 를 뺀 content 전부를 `json.dumps(indent=1)` 로 **평문** 섹션에 싣는다. 버리지 않고 보여 주는 것은 의도된 동작이다(같은 docstring 「모르는 모양은 버리지 않고 JSON 원문으로 보인다」).

- 포털은 응답을 손대지 않는다. 프록시는 받은 JSON 을 그대로 돌려준다(`backend/app/agent/routes.py:746`). `RecordReader` 는 섹션 글을 그대로 `TextBlock` 에 넘긴다(`AgentDeepView.tsx:57`). 펜스도 빈 줄도 없어 마크다운 문단 하나(`md.ts:112` → `.md-p`, `chat.css:74-76` `white-space: pre-wrap`)가 된다. `looksLikeArt`(`md.ts:91-97`)는 박스 그림 줄이 2개 이상이거나 파이프 2개 이상인 줄이 3개 이상일 때만 고정폭으로 바꾼다. 이 카드들은 박스 그림 0줄 · 파이프 줄 1줄이라 해당하지 않는다. 사용자에게는 줄바꿈과 1칸 들여쓰기만 남은 비례폭 문단으로 보인다. 구문 강조와 복사 버튼은 없다.

- 범위 — 10-14 전수 조사(796명)에서 연 첫 카드 778장 중 이 폴백에 걸린 것은 kooremapper-modelmeta 의 `…012` 하나였다(나머지 777장은 DOC). 1쪽(최대 50장)에 DOC 가 아닌 카드가 있는 전문가도 이 하나다. 「AIDataHub 의 SIM 22건 중 전문가에 묶인 것은 이 3장」이라는 수는 10-14 검증 때 잰 것이고 이번에 다시 세지 않았다(미확인). 폴백은 `0f0c9c1`(2026-09-11, 심층 보기 첫 커밋)부터 같은 모양이라 회귀가 아니다.

- 화면은 브라우저로 직접 열어 보지 않았다(미확인). 소스와 CSS 기준이다.



**요청**

1. **(가장 싼 것) 폴백 JSON 을 ```` ```json ```` 펜스로 감싼다.** `HWAXAgentServer/app.py:4636` 한 줄과 테스트 두 줄이다.



   ```diff

                text = json.dumps(rest, ensure_ascii=False, indent=1, default=str)

                out["truncated"] = out["truncated"] or len(text) > RECORD_TEXT_MAX

   -            out["sections"].append({"id": "", "title": "원문(JSON)", "level": 1, "text": text[:RECORD_TEXT_MAX]})

   +            out["sections"].append({"id": "", "title": "원문(JSON)", "level": 1,

   +                                    "text": "```json\n" + text[:RECORD_TEXT_MAX] + "\n```"})

   ```



   `tests/test_catalog_deep.py:76-77` 의 SIM-1 단언 뒤에 펜스 단언을 붙인다. 지금 단언(제목 「원문(JSON)」 · 본문에 `"tool_call"`)은 바꾸지 않아도 통과한다. 그래서 펜스를 지키는 줄이 따로 필요하다.



   ```diff

        s = asyncio.run(a.catalog_record(a.RecordRequest(id="SIM-1")))

        assert s["sections"][0]["title"] == "원문(JSON)" and '"tool_call"' in s["sections"][0]["text"]

   +    j = s["sections"][0]["text"]

   +    assert j.startswith("```json\n") and j.endswith("\n```"), "모르는 모양은 코드 블록으로 보인다"

   ```

   - 포털은 바꿀 것이 없다. `TextBlock` 이 펜스를 나눠(`TextBlock.tsx:181-208`) `CodeBlock`(`:443`, 분기 `:569-570`)으로 그린다. 고정폭(`chat.css:426-427`) · json 구문 강조(`highlight.ts:65`·`:109`) · 4줄 이상이면 줄번호(`TextBlock.tsx:453`) · 복사 · 줄바꿈 토글이 이미 있다. `json` 은 미리보기 대상(`:387`, html·svg 만)도, 마크다운으로 풀어 그리는 대상(`:555-559`, markdown·md 또는 언어 표시 없는 표)도 아니다. 응답 모양(`sections[].text` 는 문자열)이 그대로라 `RecordView` 타입(`frontend/src/api/chat.api.ts:384-398`)과 기본값 병합(`:409`)도 그대로다.

   - 펜스가 안에서 먼저 닫히지 않는다. 펜스는 줄 첫머리에서만 판정한다(`TextBlock.tsx:197` `` /^```(\S*)\s*$/ ``). `json.dumps(indent=1)` 출력은 첫 줄 `{` 와 끝 줄 `}` 말고는 모두 공백으로 시작한다. 문자열 안 줄바꿈은 `\n` 으로 이스케이프된다. 지금 3장에는 백틱이 하나도 없다(10-15 실측). 자르기(`[:RECORD_TEXT_MAX]`)를 감싸기 전에 하므로 잘린 카드도 펜스가 닫힌다.

   - 다른 곳에는 닿지 않는다. `_record_view` 를 부르는 곳은 `app.py:4650` 하나다. `/catalog/record` 는 심층 보기 읽기 칸 전용이다(`app.py:4640-4642` 「LLM 미경유」). 포털에서 이 경로를 부르는 것도 `fetchRecord`(`chat.api.ts:423`) 하나이고, 그것을 부르는 곳은 `AgentDeepView.tsx:162` 뿐이다. 그래서 대화나 LLM 쪽에는 영향이 없다.

   - 대안 — 펜스 대신 섹션에 `kind: "json"` 을 달고 `RecordReader` 가 고정폭으로 그리는 길도 있다. 다만 섹션 타입(`chat.api.ts:386`)과 화면을 포털에서 같이 바꿔야 한다. 이 요청은 한 리포에서 끝나는 펜스를 권한다. `indent=2` 로 바꿀지는 담당 판단이다.

2. **(나중에) 부품 표.** SIM 카드가 늘어나면 `content.components` 가 dict 목록일 때(`sim.py:46`) 표로 싣는다. 모양은 기존 표와 같게 `{caption:'부품', headers:[pid, title, elem_class, n_elems, area_ext, volume, material.name], rows:…, total_rows:…, notes:''}` 다. 칸은 기존 `_cell`(`app.py:4591`)로 다듬는다. `notes` 는 포털 타입이 문자열로 요구한다(`chat.api.ts:392`). `connectivity.contact_edges`(a_title–b_title, type)와 `attachments`(kind, file_name)는 짧은 섹션으로 싣는다. 나머지 키는 마지막 「원문(JSON)」 섹션(1 의 펜스)에 남긴다. ⚠ `table` 이나 섹션을 채우면 폴백 조건(`app.py:4631` `not out["sections"] and out["table"] is None`)이 꺼진다. 그래서 남은 JSON 은 따로 붙여야 한다. 표는 `RecordReader`(`AgentDeepView.tsx:60-79`)가 이미 그리므로 포털 변경은 없다. 지금 카드는 부품이 1~2개라 급하지 않다.



이번 항목에 넣지 않은 것 — 카드 안 레코드 id(예: `…012` 안의 `DOC-MX-MAT-2026-0000000002`)를 링크로 만드는 일은 SIM 만의 문제가 아니다(모든 카드에 해당한다). 제목이 같은 데모 카드 `…010`·`…011`(「S26-DEMO dv1 — deck.k 모델 메타」)이 중복인지는 데이터 소유자가 볼 일이다. kooremapper-modelmeta 에 역할·프롬프트가 없는 문제도 이 항목 밖이다.



**왜** — 3장뿐이고 내용도 다 보인다. 다만 86~119줄짜리 JSON 이 비례폭 문단 하나로 보여 중첩 구조를 따라가기 어렵다. 한 줄만 고치면 고정폭·강조·복사가 되는 코드 블록이 된다.



**확인**

```bash

# 에이전트서버 리포 — 테스트

.venv/bin/python -m pytest tests/test_catalog_deep.py -q



# cae00 — 에이전트서버 반영·재기동 뒤(읽기 호출)

curl -s --noproxy '*' -m 60 -H 'Content-Type: application/json' \

  -d '{"id":"SIM-MX-CAE-2026-0000000012","groups":["plat:aidatahub"]}' \

  http://127.0.0.1:9009/catalog/record \

 | python3 -c 'import json,sys; t=json.load(sys.stdin)["sections"][0]["text"]; print(t.startswith("```json\n"), t.endswith("\n```"))'

# → True True   (10-15 현재는 False False — 본문이 '{\n "inputs":' 로 시작해 'null\n}' 로 끝난다)

```

화면 확인 — 포털 전문가 목록에서 kooremapper-modelmeta 의 심층 보기(전체 화면)를 열고 카드 하나를 고른다. 「원문(JSON)」 아래가 `json` 머리표 · 줄번호 · 복사 버튼이 붙은 코드 블록이면 된다. DOC 카드(예: cam-aa-process 첫 카드)는 지금과 같아야 한다.



---



## 운영 쪽 (요청 아님)



**반영 경로**

1. 포털 프런트는 개발 쪽이 dist 를 빌드해 Drive 에 올려야 화면이 바뀐다(`./infra/scripts/build-all-to-drive.sh portal`). cae00 은 `update-collab.sh` 로 받는다. 이 스크립트가 포털 코드를 pull 하고, dist 가 Drive 와 다를 때만 받는다(`update-collab.sh:18`). 받은 뒤 `dist/.build-src` 와 `git rev-parse HEAD:frontend` 가 같은지 본다(K4 확인). K1-3·K2·K3·K4·K5-5·K6-5·K8-4 를 한 번에 빌드한다.

2. 에이전트서버·AIDataHub·KooRemapper 코드는 update-collab 이 pull 하지 않는다. update-collab 은 에이전트서버를 재기동만 한다(`update-collab.sh:13`·`:19` — 그것들은 update-all). 이 셋은 update-all 로 받는다. update-all 의 ste 스모크 ✗(종료코드 1)는 전부터 있던 것이다. KooRemapper 재기동 경합이 나면 stop.sh + start.sh 로 다시 띄운다. 에이전트서버 작업 트리는 지금 `7644284` 라 origin/main `c4e4823` 보다 뒤에 있다. update-all 이 이 리포도 받는다(10-11 update-all 로 `7644284` 가 됐다).

3. AIDataHub 를 재기동하면 게이트웨이의 `list_*` 캐시가 300초 남는다. 그래서 K5 확인은 5분 뒤에 한다.



**게이트웨이·HE 운영자(K8)**

4. stcx SmartTwinMCP 가 :5013 에서 실제로 뜨면 게이트웨이에 등록한다. 10-15 현재 `127.0.0.1:15013/mcp` 는 Empty reply 다. 등록은 `HWAXMcpGateway/provision.env` 에 `SMARTTWIN_MCP_URL=http://127.0.0.1:15013/mcp` 를 넣고 `update-collab.sh --no-portal --no-risk` 를 돌려서 한다. `gateway_config.json` 에 손으로 넣지 않는다. 관리 키라서 다음 프로비저닝이 지운다(`provision-config.sh:806-808`). 짐작한 주소도 넣지 않는다.

5. smart-twin-cluster(:5012, slurm)를 두 번째 터널로 cae00 에 붙일지 정한다. K8-2 `optional` 이 들어가면 붙이지 않아도 운영자는 만들어진다.

6. 포털을 pull 한 뒤 `python3 infra/scripts/sync-he-personas.py` 미리보기를 본다(GET 만 하고 쓰지 않는다). ✗ 가 없고 기대한 줄(`+ he-cad-odbhub` · `~` 3 · 건너뜀 2)이 나오면 다음으로 간다. ODB 운영자를 둘지는 사용자가 정하고, 두기로 하면 `--apply` 한다. ODB 사전 지식은 아직 뼈대뿐이다. workflow·pitfalls·key_tools 를 채워 다시 반영해야 한다. stcx 를 등록한 뒤와 update-all 을 돌린 뒤에도 미리보기를 다시 본다. `~` 가 다시 뜨면 `--apply` 한다.



**AIDataHub 동기화(K6-4)**

7. 동기화를 다시 돌릴지 정한다. mxwp·signalforge-gs·materialtwin 정기 동기화가 10-01 부터 전부 실패한다. SSRF 가드가 `127.0.0.1:8800` 같은 비표준 포트를 막기 때문이다. `AIDH_SYNC_ALLOW_INTERNAL=true` 로 켤지, 내부 주소만 허용하는 코드 변경을 요청할지는 담당이 정한다(보안 설정). `MXWP_INTERNAL_KEY` 도 넣어야 한다. 값은 화면에 띄우지 않는 방법으로 넣는다. 서버가 이 env 를 어느 파일에서 받는지는 미확인이다. **K6-4-3 이 들어가기 전에는 켜지 않는다.** 지금 코드로 켜면 상세 조회가 실패한 문서가 다시 빈 「본문」으로 덮인다.

8. 켠 뒤에는 첫 mxwp run 의 failed·dead_letter 사유를 본다(`GET /api/sync/sources/{id}/runs`). 그걸 보고 154장을 어떻게 할지 정한다. 다시 받거나, 원본에서 내린 문서면 허브에서도 내린다. K3-9 (가)의 재료 카드 재반입도 이 동기화가 돌아야 확인할 수 있다.



**데이터 담당·정책 결정**

9. dynaforge-report 를 어떻게 할지 정한다. (가) 행을 채운다. (나) `sim-drop-impact` 로 돌리고 data_types 에 SIM 을 더한다. (다) 등재를 끈다. (나)·(다)는 KooRemapper 변경이 배포된 **뒤에** 행을 지운다.

10. kooremapper-modelmeta 와 S26-DEMO 3장(`SIM-MX-CAE-2026-0000000010~012`)을 지울지 채울지 정한다. 지우면 레코드를 먼저 지우고 행은 나중에 지운다. K9 의 박스 확인(…012)과 K6-5·K7 의 화면 확인은 이 정리 **전에** 한다.

11. K6-3 strict 를 켤지 정한다(`STRICT_AGENT_VALIDATION`, 되돌릴 때는 false). 켜기 전에 등록 안 된 키를 쓰는 다른 업로더가 있는지 본다.

12. MXWP 원문에 summary 값이 있는지 MXWP 담당에게 묻는다. MXWP API 는 키가 필요해서 읽지 못했다. 어디에도 글이 없는 MX 카드(K1 은 5장, findings 는 7장 — 미확인)를 내릴지도 정한다.

13. 재료 카드(K3-9)를 어떻게 할지 정한다. (가) MaterialTwinWeb 이 절로 나눠 내보낸다. (나) 읽기 칸에서 properties 를 보인다. 크기 한도는 MaterialTwinWeb 담당이 정한다.

14. K5-2 본문 검색은 운영 DB 사본에서 `EXPLAIN ANALYZE` 를 잰 뒤에 켤지 정한다. 기준은 카드가 가장 많은 material-twin-analyst(2,729장)다.

15. K2-6 로그인 절대 수명 8시간을 유지할지 정한다(보안 정책).



**정리**

16. 검증이 cae00 에 남긴 파일 — `/tmp/.tm_ro_check`(게이트웨이 tools-map JSON, 비밀 없음)는 10-15 에 지웠다. `HWAXPortal/backend/app/access/__pycache__/agent_guard.cpython-312.pyc` 는 gitignore 대상이고 같은 폴더에 원래 pyc 가 있어 그대로 둔다.

17. 검토 중 단건 `GET /api/records/DOC-MX-WP-2026-0000000022` 를 두 번 불렀다. 그래서 그 레코드의 read_count 와 updated_at(→ 2026-10-14T22:09:35Z)이 바뀌었다. 되돌릴 것은 없다. 앞으로 확인에는 목록 조회만 쓴다.

18. ~/kc-check 스윕에 검사 하나를 더한다. 「절은 있는데 글이 0자인 카드」를 실패로 센다(findings #18). 우리 도구라 요청이 아니다.



---



## 반영 확인 — 전체



각 절의 **확인** 을 따른다. 모두 들어간 뒤에는 cae00 전수 점검(`~/kc-check/kc_sweep.py` — 운영 쪽 도구, 읽기만)을 다시 돌린다. 지금 값과 기대값은 다음과 같다.



| 항목 | 2026-10-14 | 반영 뒤 |

|---|---|---|

| 호출 오류(상세·목록·2쪽·검색·본문) | 0 | 0 |

| 절은 있는데 글이 0자인 카드(첫 카드 기준) | mx-whitepaper-analyst · kooremapper-iga | 0 (글이 정말 없는 카드는 「본문이 비어 있는 카드입니다」) |

| 잘린 카드의 안내 | 297장 모두 「표는 앞 0행」 | 「본문 N절·N자 중 앞 N자(약 N%)」 + 「다음 부분 보기」 |

| 시작 패널 보유 지식 | 761명이 「20건」 | 전문가 목록과 같은 수 |

| 이름=키·설명 0자 전문가 | dynaforge-report · kooremapper-modelmeta | K6-1·K6-2 결정대로 |

| HE 운영자 | 15명(ODB 허브 없음) · SmartTwin 도구 0 | ODB 허브 운영자 · SmartTwin 은 연결된 앱만 말한다 |



담당: DX부문 HWAX Portal (koo.park@ax.samsung.com)