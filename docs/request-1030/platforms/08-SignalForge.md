# 08 SignalForge — 10-30 요청에서 할 일

- **받는 곳** — SignalForge 세션 `signalforge-c6`. SignalForge 세션이 둘(c6 · 7f)이라 c6 에만 보냈다.
- **어떻게 갔나** — 10-30 KST 포털 세션 `hwaxportal-a5` 가 두 행의 글을 그대로 보냈다. 덧붙인 것은 'HA-33 이 `{results, notes}` 를 펼친다 — 칸 이름을 지켜 달라' 한 줄이다. 답은 기다리는 중이다([`../outbound.md`](../outbound.md) 1절).
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md). SG-04(다시)는 4절 '박스 밖 플랫폼' 표, SG-19 는 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청' 의 'SignalForge(`d2a794d`)' 표에 있고, 다시 볼 시험은 7절이다.
- **cae00 기준 판** — SignalForge `d2a794d`.
- **이 박스(dev)에서 대조한 판** — 형제 리포 `SignalForge` 의 main `d2a794d` 다(origin/main 도 같다 — 마지막 fetch 2026-10-30 17:39 KST). `git log d2a794d..HEAD` 가 0건이라 아래 줄 번호는 cae00 판과 같고, 인용한 줄은 모두 `git show d2a794d:<파일>` 로 맞췄다. 워크트리는 본 리포 하나다. 대조 시각은 2026-10-30 17:58 KST(커밋된 판)와 18:02 KST(작업 트리)다.
- **작업 트리** — 17:58 KST 에는 코드 칸(`mcp-server` · `shared` · `crawler` · `backend` · `scripts` · `docs`)에 커밋하지 않은 변경이 없었다. 18:01 KST 에 `mcp-server/tools/query.py` · `mcp-server/tools/semantic.py` · `shared/keyword_match.py` 가 커밋 없이 바뀌었고, 주석에 SG-19 를 적었다. SignalForge 세션의 SG-19 작업으로 보인다(c6 · 7f 가운데 어느 쪽인지는 대조 못 함). 커밋 전이라 바뀔 수 있다 — 아래 SG-19 절에 18:02 KST 에 본 것을 적었다.

이름은 요청서처럼 가린 채로 둔다(프로젝트 A · B, 모델 C). 이 박스에서는 서비스를 부르지 않았고 시험도 돌리지 않았다 — 아래 '지금 판에서의 자리' 는 코드 대조다.

## 할 일

### SG-04(다시) · 높음 — 프로젝트 A 의 모델 · 마케팅명이 프로젝트 B 의 제품 코드로 풀린다

- **무엇이** — 제품 해석이 프로젝트 A 의 모델 · 마케팅명을 프로젝트 B 의 제품 코드로 푼다. 교차 업무에서 다른 제품의 VOC 를 주의 없이 싣는다.
- **근거** — DW-21 — SignalForge 온톨로지가 모델 C(코어에서 프로젝트 A)를 프로젝트 B 의 제품 코드로 이었다. 10-29 EX-03 · 10-30 OT-15 와 같다. 코어는 프로젝트 A · 프로젝트 B 를 다른 프로젝트로 둔다.
- **할 일** — 데이터 결정(제품 행을 나눌지)이 남았다(포털 `docs/request-1029/signalforge-sg04-question.md`). 그 전까지는 resolve 결과에 '이 모델 · 이름이 여러 PLM 프로젝트에 걸린다' 주의 칸을 싣는다.
- **다시 볼 시험**(7절 표의 행) — 시험: DW-21 · OT-15 / 언제: SG-04 결정 뒤 / 볼 것: 프로젝트 A 의 VOC 에 프로젝트 B 가 섞이지 않는다.

#### 지금 판에서의 자리 — SG-04(다시)

- 행은 SignalForge 의 파일:줄을 짚지 않았다(근거는 시험 번호뿐이다). 할 일이 가리키는 포털 문서 [`../../request-1029/signalforge-sg04-question.md`](../../request-1029/signalforge-sg04-question.md)(10-29)는 이 박스에 있다. 안 셋(A 카탈로그에 제품 행을 따로 두고 매처 사전을 그 행에 잇기 · B 매처 사전에서 떼기만 · C 그대로 두고 응답에 한 줄)과 포털 권고 A 를 적었다. 그 글은 같은 일을 가린 이름 P8 · PH8 로 적었는데, 이 요청서의 프로젝트 A · B 와 같은 짝인지는 이름이 가려져 있어 대조 못 함.
- 답은 아직 없다. SignalForge 리포에서 SG-04 를 적은 곳은 10-27 처리 기록뿐이다(`docs/cae00-fix-2026-10-27/checklist.md:14` · `docs/cae00-fix-2026-10-27/context-notes.md:42` · `docs/DEPLOY_CAE00_2026-10-27.md:16`). 포털 10-29 체크리스트의 SG-04 줄도 `[-]`(묻는 글로 둠)다(포털 `docs/request-1029/checklist.md:78`).
- 주의 칸은 지금 판에 없다. `resolve_product_keyword`(`mcp-server/server.py:269-284`)가 부르는 `resolve_product_keyword_tool`(`mcp-server/tools/query.py:328-380`)의 결과(`:352-361`)는 keyword · match_mode · keyword_hits · candidates · resolved_code · resolved_via · tagged_count · status 와 note(`:362-379`)뿐이다. 커밋된 판 전체에서 '여러 PLM 프로젝트' · '여러 과제' 꼴의 문구도 0건이다(`git grep … d2a794d`). 18:02 KST 작업 트리의 커밋 전 변경(SG-19 절)에도 이 칸은 없다.
- 이 도구는 PLM 거울을 보지 않는다. 카탈로그 이름(`_RESOLVE_SQL`, `query.py:273-292`)이 정확히 맞지 않으면 제품 매처 별칭으로 다시 본다(`:336-345` — 10-27 SG-04 처리 `89a0583`, `_matcher_codes` 정의 `:295-308`). 마케팅명이 어느 제품 코드로 가는지는 그 매처 사전이 정한다(`crawler/base/product_match.py:28` `PRODUCT_PATTERNS` → `:1269-1273` `_COMPILED`, 판정은 `infer_all_product_codes` `:1693`).
- `search_voc` · `semantic_search` 의 질의 해석은 PLM 거울을 본다(`mcp-server/tools/semantic.py:449`). `shared/ontology.py:659-700` 의 `_detect_plm` 이 개발모델명 · 과제코드 · 과제명을 그 과제의 개발모델로 잇고, `_plm_products`(`:644-656`)가 모델코드 사전(`crawler/base/model_codes.py:161-163` `family_of`)으로 제품 코드를 고른 뒤 해석 notes 에 '<개발모델 · 과제> → <제품 코드>' 한 줄을 단다(`:699-700`). 그 notes 가 search_voc 봉투의 `notes` 로 나간다(`mcp-server/server.py:217`). 이 길에도 그 제품 코드가 다른 과제 · 프로젝트에 걸린다는 표시는 없다. 이 길을 들인 커밋은 `da0bfae` 다.
- 코드 읽기로는, 모델코드 사전이 기본 코드 하나를 제품 하나에만 잇는다(`crawler/base/model_codes.py:123-139` `_invert` — 두 제품에 걸리면 ValueError). 그래서 두 프로젝트의 개발모델이 같은 기본 코드를 쓰면 PLM 길도 한 제품 코드로 모인다.
- 주의 칸의 재료는 PLM 색인에 있다. `PlmIndex`(`crawler/base/plm_mirror.py:314-389`)는 과제마다 `project` 를 들고(`:339`) `plm_project` 의 이름표도 읽는다(`:348-349`). 제품 코드에서 과제 · 프로젝트로 거꾸로 가는 색인은 지금 없다.
- DW-21 이 매처 별칭과 PLM 거울 가운데 어느 길로 이어졌는지는 대조 못 함. cae00 의 질의 기록이 이 박스에 없고, 이름이 가려져 있다.

#### 우리 쪽 맞물림 — SG-04(다시)

- 우리 리포에는 SG-04 를 고치는 행이 없다. 10-29 판단 C-29(포털 [`../../request-1029/context-notes.md`](../../request-1029/context-notes.md))대로 카탈로그 · 태깅 사전의 데이터 결정은 SignalForge 몫으로 두었고, 이번에도 '보냄' 갈래다([`../PLAN.md`](../PLAN.md)).
- 에이전트 HA-33(고치는 중)은 심의 전 VOC 미리보기가 search_voc 봉투의 `results` 를 펼쳐 읽게 하고, 펼친 뒤에도 0건일 때만 `notes` 를 싣는다(요청서 HA-33 의 할 일). 그래서 주의를 search_voc 의 `notes` 에만 실으면 결과가 있는 미리보기에는 보이지 않는다. 주의 칸의 이름과 자리(resolve_product_keyword 결과에만 싣는지, search_voc 봉투에도 싣는지)를 알려 주면 미리보기에 실을지 우리 쪽에서 정한다.
- 7절의 DW-21 · OT-15 는 SG-04 결정 뒤 cae00 에서 사람이 웹 챗으로 다시 본다. 우리 쪽이 그 절차를 `docs/request-1030/server-setup.md`(아직 없다)에 적는다. 10-29 묻는 글은 고른 안이 정해지면 OT-05 · OT-15 로 확인한다고 적었다.

### SG-19 · 낮음 — `search_voc` · `resolve_product_keyword` 가 느리다

- **무엇이** — (낮음) `search_voc` 와 `resolve_product_keyword` 가 느려, VOC 를 묻는 챗 한 턴이 길어진다.
- **근거** — 게이트웨이 감사(10-29 · 10-30, 도구 · ms · ok 만 읽음) — search_voc 성공 20건 중앙값 약 13.9초 · 최대 35.7초, resolve_product_keyword 성공 7건 중앙값 4.2초 · 최대 14.2초다. 코드 자리는 `mcp-server/server.py:214`(semantic_search_tool) · `mcp-server/tools/query.py:338`(`_matcher_codes`)다.
- **할 일** — 두 도구가 느린 까닭을 보고 줄인다. 첫 호출의 시맨틱 적재인지, 매처 사전을 부를 때마다 짓는지부터 가린다(추정). SG-04(다시)와 같은 묶음으로 보낸다.
- **출처** — QA-CHAT-QWEN-20261029 5.5 SignalForge 행 · 포털 `docs/request-1029/signalforge-sg04-question.md` '함께 본 것'

#### 지금 판에서의 자리 — SG-19

- `mcp-server/server.py:214` 는 그대로다. `search_voc`(`:162-217`)의 기본 길(`semantic=True`)이 `r = await semantic_search_tool(keyword, product_code, limit, days, order, match)` 를 부르는 줄이다. HA-33 의 근거가 짚은 봉투 줄(`:195` 도구 설명 · `:209-217` 두 길의 반환)도 그대로다. `git log d2a794d..HEAD -- mcp-server/server.py` 는 0건이다.
- `mcp-server/tools/query.py:338` 도 그대로다. `resolve_product_keyword_tool`(`:328-380`) 안의 `codes = _matcher_codes(keyword)` 이고, 카탈로그 이름이 정확히 맞지 않을 때만 지난다(`:336`). 정의는 `:295-308` 이다. `git log d2a794d..HEAD -- mcp-server/tools/query.py` 는 0건이다.
- 커밋된 판에는 SG-19 기록이 없다(`git grep SG-19 d2a794d` 0건). 행의 시간(중앙값 · 최대)은 서비스를 부르지 않아 이 박스에서 다시 재지 않았다 — 대조 못 함. 아래 넷은 커밋된 판(`d2a794d`)의 코드 읽기다.
- **'매처 사전을 부를 때마다 짓는가'** — `_matcher_codes` 는 부를 때마다 `from base import product_match` 를 하지만(`query.py:304-307`) 파이썬은 처음 읽은 모듈을 다시 읽지 않는다. 매처 정규식(`crawler/base/product_match.py:1269-1273` `_COMPILED`)과 모델코드 사전(`crawler/base/model_codes.py:139` `EXACT, FAMILY = _invert()`)은 모듈을 처음 읽을 때 한 번 짓는다. 부를 때마다 짓는 꼴은 코드에 보이지 않고, 프로세스의 첫 호출만 그 값을 낸다.
- **resolve 가 부를 때마다 하는 일** — 카탈로그 SQL(`query.py:334-335`, 맞은 제품마다 태깅 글 수를 함께 센다)과 말뭉치 전체의 키워드 건수(`:346-349`)다. 한국어 키워드는 두 칸 ILIKE 부분일치로 간다(`shared/keyword_match.py:73-74` · `:89-90`). 이 리포 주석은 한국어 5개 부분일치 × 두 칸이 7.5초였다고 적는다(`shared/keyword_match.py:97-98`, 2026-10-17 실측 · 활성 99만 행).
- **search_voc(시맨틱 길)가 부를 때마다 할 수 있는 일** — 카탈로그는 600초 캐시하고(`mcp-server/tools/semantic.py:41` · `:51-73`), PLM 거울은 30초마다 파일 시각만 다시 본다(`crawler/base/plm_mirror.py:395-417`). 바깥 모델 왕복은 둘이다. 사전이 증상을 못 찾았고 남는 말이 있거나 개념이 없으면 LLM 개념 추론(`semantic.py:451-452`, 시간 제한 기본 6초 — `mcp-server/tools/llm_concepts.py:28`)을 하고, 사전이 질의를 다 설명하지 못하면 질의 임베딩(`semantic.py:465-466`, 기본 8초 — `mcp-server/tools/vector.py:27`)을 한다. 둘 다 같은 질의는 캐시하고(`llm_concepts.py:76-79` · `vector.py:54-56`) 모델 요청에 `keep_alive: "30m"` 을 싣는다(`llm_concepts.py:80` · `vector.py:60`). 30분 넘게 쉰 뒤의 첫 호출이 모델 적재를 기다리는지가 '첫 호출의 시맨틱 적재' 의 후보다(재지 않음). 전역 벡터 훑기는 색인 전체를 스레드에서 돈다(`semantic.py:497-498`). 본 SQL 은 15초 시간 제한에 걸리면 주석만으로 한 번 더 돈다(`semantic.py:44` · `:509-520`).
- **단계 시간은 밖으로 나가지 않는다** — `semantic_search_tool` 은 `elapsed_ms` 를 재지만(`semantic.py:478` · `:545`) search_voc 봉투(`server.py:215-217`)에는 싣지 않는다. 그래서 게이트웨이 감사에는 한 호출의 총 ms 만 남는다.
- **작업 트리의 커밋 전 고침(18:02 KST 에 본 것)** — 아직 고쳐진 커밋은 없다. 작업 트리의 변경은 이렇다. resolve 의 키워드 건수에 시간 상한(`RESOLVE_COUNT_BUDGET_S`, 기본 2.5초)을 두고, 넘으면 5% 표본으로 어림하며, 결과에 `keyword_hits_exact` 칸을 더한다(`keyword_hits` 는 어림값이거나 비어 있을 수 있다). 시맨틱 길은 한국어 원문 경로를 한 번에 미리 훑고, 시간 상한(`SEMANTIC_KO_BUDGET_S`, 기본 4초)을 넘으면 그 경로를 빼고 notes 에 한 줄을 단다. 본 SQL 의 시간 제한은 15초에서 10초로 줄였다. 한글 키워드의 부분일치는 원문 칸만 본다. 주석에는 dev 2026-10-30 실측(한국어 원문 훑기 — 따뜻하면 1.5 ~ 2초, 차가우면 15 ~ 30초)이 적혀 있다. 봉투를 만드는 `mcp-server/server.py` 는 바뀌지 않았다.

#### 우리 쪽 맞물림 — SG-19

- 에이전트 HA-33(고치는 중)이 search_voc 봉투 `{total, results, strategy, match_mode, notes}` 를 펼친다. `results` 가 목록이면 펼쳐 읽고, 펼친 뒤에도 0건이면 `notes` 를 미리보기에 싣고, 펼칠 것이 없는데 결과 글이 비지 않았으면 `degraded` · `partial` 로 센다(요청서 HA-33 의 할 일). 빠르게 고치더라도 이 다섯 칸의 이름과 꼴(`results` 는 목록, `notes` 는 글 목록)을 지켜 달라 — 보낼 때 덧붙인 한 줄과 같다. 요청서가 적은 HA-33 의 읽기는 `results` · `notes` 를 보므로 칸을 더하는 것(예 단계 시간)은 걸리지 않는다.
- 미리보기가 행마다 읽는 칸도 있다. `_voc_row`(cae00 판 에이전트 `969e723` `app.py:5980-5993`)가 `id` · `content_translated`(없으면 `content_original`) · `product_name`(없으면 `product_code`) · `platform_name` · `country_code` · `published_at` · `sentiment_label` · `sentiment_score` · `source_url` 을 읽고, 본문이 빈 행은 미리보기에서 빠진다(`:6026`). 결과 행의 칸 이름도 지금처럼 두어 달라.
- 미리보기는 검색어(최대 6개)마다 search_voc 를 차례로 부른다(`969e723` `app.py:6008` · `:6014-6015`). 그래서 search_voc 한 번이 느리면 미리보기는 검색어 수만큼 길어진다.
- 우리 쪽 코드(에이전트 서버 · 게이트웨이 · 포털의 커밋된 HEAD)는 resolve_product_keyword 결과의 칸(`keyword_hits` · `resolved_code` · `resolved_via`)을 읽지 않는다(`git grep` 0건). 작업 트리의 고침처럼 `keyword_hits` 가 어림값이 되거나 비어도 우리 코드는 걸리지 않는다.
- 10-29 묻는 글의 '함께 본 것' 은 챗 한 턴에서 둘을 부르면 25초가 든다고 적었다(OT-15). 이 요청서도 SG-19 를 SG-04(다시)와 같은 묶음으로 보냈다.

## 끝나면

알릴 곳은 HWAX 포털 세션 `hwaxportal-a5` 다. 받은 답은 포털이 [`../outbound.md`](../outbound.md) 의 '답' 칸과 `docs/request-1030/server-setup.md`(cae00 사람 몫, 아직 없다)에 옮겨 적는다.

1. **SG-04 데이터 결정** — 10-29 묻는 글의 안(A · B · C) 가운데 무엇을 골랐는지 알려 달라. A 라면 다시 태깅할 범위(묻는 글이 적은 그 제품 코드의 VOC 43,179건 가운데 몇 건인지)와, 그 결과가 cae00 에 닿는 길(덤프 병합인지, cae00 에서 도는 명령인지)도 알려 달라.
2. **결정 전 주의 칸** — 칸 이름과 자리(resolve_product_keyword 결과 · search_voc 봉투의 `notes` · 둘 다)와 커밋을 알려 달라.
3. **SG-19** — 잰 까닭(첫 호출 적재 · LLM 개념 추론 · 질의 임베딩 · 벡터 훑기 · 본 SQL · 키워드 건수 가운데 어디인지, 단계별 ms)과 고친 커밋, 고친 뒤 두 도구의 시간을 알려 달라. 환경 손잡이를 남겼으면(작업 트리에는 `RESOLVE_COUNT_BUDGET_S` · `SEMANTIC_KO_BUDGET_S` 가 보인다) 기본값과 cae00 에서 바꾸는 자리도 알려 달라.
4. **반영 길** — sf-mcp 는 `mcp-server` · `shared` · `crawler` 를 바인드로 받는다(`scripts/up.sh:287-291`). 파이썬만 고쳤으면 git(update-all)과 sf-mcp 재기동(`scripts/up.sh`)으로 닿는지 적어 달라. 패키지가 바뀌어 이미지를 새로 올렸으면 Drive `SignalForge/sif/latest/` 의 판 이름을, 데이터를 고쳤으면 병합 · 다시 태깅 절차를 적어 달라. cae00 에서 사람이 할 일은 10-27 처럼 날짜별 적용 문서(`docs/DEPLOY_CAE00_2026-10-27.md` 꼴)로 받으면 좋다.
5. **봉투** — search_voc 의 다섯 칸과 결과 행의 칸 이름을 그대로 뒀는지 한 줄로 알려 달라.

7절 '다시 볼 시험' 가운데 이 플랫폼 몫은 하나다.

- DW-21 · OT-15 — SG-04 결정 뒤, 프로젝트 A 의 VOC 에 프로젝트 B 가 섞이지 않는지 cae00 웹 챗에서 사람이 본다.
- SG-19 에는 7절 시험이 없다. 근거와 같은 게이트웨이 감사(도구 · ms · ok)로 두 도구의 중앙값 · 최대를 다시 볼 수 있다.

이 플랫폼에 닿는 우리 쪽 사람 몫으로 5절 OB-68(VOC 화면 손 시험(M-18)과 get_voc_summary(제품 B) 한 번)이 남아 있다. SignalForge 가 할 일은 아니다.
