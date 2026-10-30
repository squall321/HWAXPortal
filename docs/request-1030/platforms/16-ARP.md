# 16 ARP(AI Ready Portal) — 10-30 요청에서 할 일

- **받는 곳** — 사내 다른 팀(ARP 담당). 이 세션이 닿는 ARP 세션이 없어 사람이 보낸다. ARP 리포는 이 박스에 없다.
- **어떻게 갔나** — 아직 안 갔다. [`../outbound.md`](../outbound.md) 2절 '사람이 보낼 것' 에 있다. 요청서 6절대로 cae00 의 16-ARP-ODBHub-core-ontology.md 에 이어 붙여 사람이 보내고, 보내기 전에 사람이 16 문서를 한 번 읽는다(O-9). 정본 끝 절 ARP 행의 근거 칸도 '16 문서는 아직 보내지 않았다' 고 적었다. 대조 시각(포털 `bf5cd94`)에 outbound.md 2절은 처음 쓴 글(`ce41b8f`) 그대로다.
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 의 4절 '박스 밖 플랫폼' AR-9 · AR-10 행, 6절 '다른 요청과 맞물린 것' 넷째 줄, 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)' › 'ARP' 표의 AR-1 ~ AR-4(다시) 행이다. 16 문서 링크는 정본 링크가 가리키던 자리(`docs/16-ARP-ODBHub-core-ontology.md`)를 이 폴더에서도 가리키게 `../../` 로 고쳤다. 그 파일은 cae00 에만 있어 이 리포에서는 열리지 않는다(정본 링크도 같다).
- **cae00 기준 판** — ARP 는 update-all 로 받지 않는 플랫폼이라(정본 머리) 정본에 ARP 판(sha)이 없다. 기준은 cae00 문서 16-ARP-ODBHub-core-ontology.md(2절 AR-1 ~ AR-4 는 10-29 실측)와 10-30 QA 두 보고서(QA-DIGITAL-WORKER-20261030 · QA-CHAT-QWEN-20261030)다. 아래 우리 쪽 자리의 기준 판은 포털 `aec8e29` · 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d` 다.
- **이 박스(dev)에서 대조한 판** — ARP 리포 · 16 문서 · 10-30 QA 두 보고서는 이 박스에 없다(`~/claude` 의 리포 이름, 홈 아래 깊이 5 · `/data` 깊이 4 를 찾아 0건, `~/Projects` 는 없다). 우리 쪽 짝은 포털 main `bf5cd94` · 게이트웨이 master `67d8d00` · 에이전트 서버 main `7ca3a2e` 에서 봤고, 세 cae00 판은 이 박스에도 있어 `git show` 로 맞댔다. 형제 워크트리(`*-wt-1030-*`)는 열지 않았다. 대조 시각은 2026-10-30 17:50 ~ 18:05 KST 다. 읽기만 했다(시험 · 재기동 · 고침 없음).

## 할 일

### AR-9 · AR-10 · 중간 — 담당자 실명이 MCP 출력에 실리고, 낙하 높이에 단위가 없다

- **무엇이** — 담당자 실명이 MCP 출력에 실리고, 낙하 높이에 단위가 없다.
- **근거** — DW-06 `partOwner` · 낙하 높이 152 를 챗이 'mm' 로 읽었다(DW-06 · OT-13).
- **할 일** — AR-9 — basicInfo 수치 칸에 단위를 싣는다. AR-10 — MCP 출력의 사람 칸을 가린다. [16-ARP-ODBHub-core-ontology.md](../../16-ARP-ODBHub-core-ontology.md) 에 함께 더한다.

정본 4절 표에는 '다시 볼 시험' 칸이 없다. 7절에서 이 행이 걸리는 줄은 '끝나면' 에 적었다.

#### 지금 판에서의 자리

- **ARP 쪽은 대조 못 함 — 이 박스에 리포가 없다.** 이 행은 `파일:줄` 을 짚지 않았다(근거는 10-30 QA 의 DW-06 · OT-13). basicInfo 수치 칸과 `partOwner` 칸이 ARP MCP 응답의 어디에 있는지, 지금도 그대로인지는 ARP 리포나 cae00 실측 없이는 모른다. 두 QA 보고서도 이 박스에 없다.
- **AR-9(낙하 높이 단위)** — 이 박스에서 볼 수 있는 같은 관찰은 10-29 QA 본문(이 리포의 [`../../request_261029.md`](../../request_261029.md), 머리 '포털 웹 챗 온톨로지 QA — stcx Qwen 챗(2026-10-29)')의 OT-08 줄(`:59`)이다. 끝 칸에 '낙하 높이 152 를 'mm' 로 적었다(다른 시험 답에서는 cm).' 가 있다. 10-29 에도 같은 값을 'mm' 로 적은 답이 있었다.
  - 포털 쪽 메움 줄은 아직 없다. 포털 main `bf5cd94` 의 ARP 운영자(`infra/personas/he-team.json:382` `he-data-arp`)의 함정(`pitfalls`, `:398-400`)은 '없는 데이터를 있는 것처럼 말하지 않는다. 이 앱 도구가 안 보이면 연결 문제라고 말한다.' 한 줄뿐이다. `git log --oneline aec8e29..bf5cd94 -- infra/personas/he-team.json` 은 0건이다.
- **AR-10(사람 칸)** — 지금 게이트웨이 판은 `partOwner` 를 가리지 않는다. 게이트웨이 master `67d8d00` 의 가림 칸 이름 목록 `_PII_KEYS`(`gateway.py:613-620`, cae00 판 `44f4b8d` 에서는 `:612-619`)에 `partOwner` · `owner` 가 없다. 칸 이름 대조(`_PII_STR_RX`, `:622`)는 목록에 있는 이름과 같은 칸만 본다(대소문자 무시). `44f4b8d..67d8d00` 사이 `gateway.py` 를 고친 커밋은 여섯이지만, 그 diff 에 `_PII_*` · `_IMEI_RX` 줄은 0줄이다.
  - ARP 출력은 이 가림을 지난다. 게이트웨이의 `arp` 백엔드는 `ARP_BASE` 의 `/mcp` 다(`provision-config.sh:654-656`). 가림 `_pii_mask`(`gateway.py:697`)는 백엔드 도구 결과와 rest_call 에 걸린다(주석 `:611`, 부르는 곳 `:4364` · `:6222` · `:6296` · `:6315` · `:6320` · `:6351`). 그래서 ARP 가 그 칸을 내는 한, 지금 판(cae00 `44f4b8d` · dev `67d8d00` 모두)에서는 `partOwner` 값이 가려지지 않고 챗에 간다.
  - 자유 글 속 사람 이름은 게이트웨이가 꼴로 가르지 않는다(주석 `:608-609`, 정본 DP-08(다시)이 짚은 `44f4b8d` `:606-608`).

#### 우리 쪽 맞물림

- **보내는 길 — 사람 몫.** 정본 6절 넷째 줄은 '- ARP 단위 · 사람 칸(AR-9 · AR-10)은 [16-ARP-ODBHub-core-ontology.md](../../16-ARP-ODBHub-core-ontology.md) 의 ARP 절에 이어 붙인다.' 다. 그대로 cae00 의 16 문서에 이어 붙여 사람이 보낸다([`../outbound.md`](../outbound.md) 2절).
- **게이트웨이 HG-22 — 고치는 중**(가지 `wt1030/pii`, 대조 시각에 master 위 커밋 0). 정본 HG-22 의 근거 첫머리가 'DW-06 ARP `partOwner`(실명)' 이고, 할 일은 '칸 이름에 owner · partOwner · submitter · user · email · assignee 꼴을 더하고, 메일 꼴 · 사내 계정 꼴(영문.영문숫자)과 사설 IP 꼴(10.x · 172.16-31.x · 192.168.x)은 칸 이름과 상관없이 가린다. REST 다리 출력도 같은 가림을 거친다(TODO-20261029 R-08 과 같은 일). 원천 쪽 요청은 4절.' 이다. 들어가면 게이트웨이를 지나는 ARP 출력의 `partOwner` 칸 값이 가려질 계획이다.
  - 그래도 AR-10 은 ARP 몫으로 남는다. 정본이 원천 쪽 요청을 4절(이 행)에 따로 두었고, 게이트웨이는 글 속 이름을 가르지 못한다([`../outbound.md`](../outbound.md) 2절 '포털 쪽 짝' — '글 속 이름(DP-08 의 검출자 · 작업자)은 게이트웨이가 꼴로 가르지 못해 원천 몫 그대로다.').
- **같은 묶음의 원천 쪽 요청.** 정본 끝 절 DP-08(다시)의 할 일은 'FailureTrace 출력에서 사람 이름 칸을 가린다. 4절의 원천 쪽 개인정보 요청(AR-10 · PA-20)과 같은 묶음으로 보낸다.' 다. 그 가운데 PA-20 은 SmartTwinExplorer 가 10-30 에 끝냈다고 답했다(`4f5e0e0` — MCP `_scrub` 이 도구 여덟에서 `submitted_by` · `source_ip` · `owner_id` · `sync_dir` 를 빼고, 글 속 사설 IPv4 · 메일 꼴을 `[사설IP]` · `[메일]` 로 가린다, [`../outbound.md`](../outbound.md) 1절 답 칸). StepForge 도 ST-12 (3) owner 는 원천에서 가린다고 답했다(같은 표 — ST-12 는 지금 착지 중인 다른 묶음 뒤 판). 다른 원천이 고른 꼴이라 참고로만 적는다.
- **포털 HP-53 — 고치는 중**(main `bf5cd94` 에는 아직 없다). ARP 에 닿는 몫은 셋이다.
  - AR-9 메움 — 'ARP 운영자 함정에 '낙하 높이 칸은 단위가 없다 — 시험 조건은 cm' 한 줄을 넣는다(AR-9 전까지).' AR-9 이 들어오면 이 줄은 걷을 대상이 된다.
  - 쓰기 목록 — 'ARP arp_upload_create · arp_upload_stage · arp_upload_register · arp_upload_discard' 를 ARP 운영자의 `writes` · `confirm` 에 넣고, 'ODB · ARP 운영자는 todo · key_tools 도 채운다.' 이 목록은 에이전트 HA-29(고치는 중)의 확인 카드가 읽는다. 정본 HA-29 의 할 일은 '잡을 시작하는 도구(run_job · run_checklist · docforge_convert · 클러스터 제출 · 운영자 정의의 `writes`)는, 이번 턴 사람 발화가 그 일을 분명히 시키지 않았으면 코드 단에서 확인 카드로 멈춘다.' 다. ARP 에 청하는 일은 아니다.
  - 이름 대조 — 운영자 동기화는 `key_tools` · `writes` · `confirm` 의 이름이 그 앱의 게이트웨이 도구에 없으면 오류로 세고(`infra/scripts/sync-he-personas.py:147-150`), 오류가 하나라도 있으면 아무것도 쓰지 않고 끝난다(`:193-196`, [`../context-notes.md`](../context-notes.md) C-8). HP-53 이 들어간 뒤 ARP 가 위 네 이름을 바꾸면 cae00 동기화가 멈춘다.
  - 효과는 cae00 에서만 난다. dev 게이트웨이에는 arp 백엔드가 없어 ARP 운영자는 동기화에서 건너뛴다(`he-team.json:2` `_doc` · `sync-he-personas.py:132-134`). cae00 에서도 update-all 은 운영자 동기화를 미리보기만 하고(`infra/scripts/update-all.sh:1176`), 다르면 `--apply` 를 사람에게 맡긴다(`:1182`). 그 동기화가 저장 뒤 500 에 첫 건에서 멈추는 일(AD-21)은 두 쪽에서 고치는 중이다 — 포털은 저장 여부를 다시 읽어 이어 가게 하고([`../outbound.md`](../outbound.md) 2절 — HP-53 묶음), AIDataHub 의 근본 고침은 이 세션이 맡았다([`../context-notes.md`](../context-notes.md) C-7).

### AR-1 ~ AR-4(다시) · 중간(16 문서 안의 심각도는 그대로) — 과제명 · 과제코드로 모델 찾기 · 못 찾은 까닭 · 받기 상태

- **무엇이** — (중간 — 16 문서 안의 심각도는 그대로) ARP 는 코어를 받지 않아 과제명 · 과제코드로 모델을 찾지 못하고(modelMatch none), 못 찾은 까닭도 하나뿐이다.
- **근거** — [16-ARP-ODBHub-core-ontology.md](../../16-ARP-ODBHub-core-ontology.md) 2절 AR-1 ~ AR-4(10-29 실측) · QA-DIGITAL-WORKER-20261030 DW-21 · QA-CHAT-QWEN-20261029 OT-08. 이 요청서 6절은 AR-9 · AR-10 만 16 문서에 이어 붙인다고 적었고, 16 문서는 아직 보내지 않았다.
- **할 일** — 16 문서의 AR-1 ~ AR-4(과제명 · 과제코드로 모델 찾기 · 못 찾은 까닭 넷 · 받기 상태)를 AR-9 · AR-10 과 같은 묶음으로 보낸다. 보내기 전에 사람이 16 문서를 한 번 읽는다(QA-CHAT-QWEN-20261029 6절 O-9).
- **출처** — 16-ARP-ODBHub-core-ontology AR-1 ~ AR-4

#### 지금 판에서의 자리

- **ARP 쪽 · 16 문서는 대조 못 함 — 이 박스에 없다.** 2절 AR-1 ~ AR-4 의 글과 그 안의 심각도, `modelMatch` 칸, 받기 상태는 이 박스에서 볼 수 없다. QA-DIGITAL-WORKER-20261030(DW-21)도 이 박스에 없다. 그래서 이 행은 정본이 적은 만큼만 옮겼다.
- **이 박스에서 대조한 것** — 근거의 QA-CHAT-QWEN-20261029 는 이 리포의 [`../../request_261029.md`](../../request_261029.md) 다(머리 '포털 웹 챗 온톨로지 QA — stcx Qwen 챗(2026-10-29)').
  - OT-08 가상검증 줄(`:59`)은 FAIL 이다. 부른 것은 'ARP compare_items · search_data 와 CAE그룹 workspaces. 코어 0회.' 다.
  - 5.1 시스템별 판정의 ARP 줄(`:181`)은 코어를 '받지 않는다.' 이고, 끝 칸이 '자체 모델 목록으로만 찾아 과제명 · 과제코드로는 모델을 못 찾는다. 요청서 `../16-ARP-ODBHub-core-ontology.md` AR-1~AR-8.' 이다.
  - 6절 O-9(`:325`)는 '정리했다 — `../16-ARP-ODBHub-core-ontology.md`(ARP 8행 · ODB 9행, 우리 몫은 그 파일 5절). 보내기 전에 사람이 읽는다.' 다.
  - 그래서 16 문서의 ARP 몫은 AR-1 ~ AR-8 이고, 10-30 정본이 다시 올린 것은 그중 AR-1 ~ AR-4 다. AR-5 ~ AR-8 은 10-30 정본에 나오지 않는다. 새 행 AR-9 · AR-10 은 그 뒤 번호다.
- **16 문서의 자리** — 10-30 정본은 같은 폴더(`16-ARP-ODBHub-core-ontology.md`)로, 10-29 QA 는 한 단계 위(`../16-ARP-ODBHub-core-ontology.md`)로 적었다. 이 리포에는 두 자리 모두 없고 cae00 에만 있다([`../outbound.md`](../outbound.md) 2절 'cae00 의 16-ARP-ODBHub-core-ontology.md').

#### 우리 쪽 맞물림

- **이번 요청서의 HA · HG · HP 행 가운데 AR-1 ~ AR-4 를 바꾸는 것은 없다.** 우리 몫은 보내기다. 사람이 16 문서를 한 번 읽고(O-9) AR-9 · AR-10 과 한 묶음으로 보낸다(정본 끝 절 ARP 행 할 일 · [`../outbound.md`](../outbound.md) 2절). 16 문서 안의 우리 몫은 그 파일 5절이다(10-29 O-9). 그 5절은 이 박스에서 대조 못 함.
- **가까운 우리 고침 — 포털 HP-53, 고치는 중.** 정본 HP-53 은 'ODB · ARP 운영자는 todo · key_tools 도 채운다.' 고 적었다. ARP 운영자의 `todo`(`he-team.json:402`)는 지금 'cae00 에서 실제 도구를 보고 작업 순서·함정·key_tools 를 보강한다.' 이고 `key_tools`(`:403`)는 빈칸이다.
- **이미 들어간 우리 쪽(이번에 바꾸지 않는다)** — 10-29 R-2 로 코어 어휘표가 ARP 를 코어 아님으로 둔다. 포털 `backend/config/core_vocab.json:42` 가 `"arp": {"role": "noncore", "label": "ARP", "note": "해석 실측"}` 이다(`c398230`, cae00 판 `aec8e29` 에도 있다). 에이전트 서버 `_core_rules_text`(main `7ca3a2e` `app.py:286`, cae00 판 `969e723` `:254`)가 이 칸으로 규칙 ⑦ `⑦ {non} 는 코어 객체를 갖지 않습니다 — 표준 키 · 개수 · 관계는 코어에서 답하고, 코어 질문을 그쪽으로 보내지 마세요.` 를 만들고, `{non}` 에 'ARP(해석 실측)' 가 든다(`:305-306`, `969e723` `:273`). 10-29 체크리스트도 '[x] R-2 규칙 ⑦ 에 FMEA · ARP · ODB 허브' 다([`../../request-1029/checklist.md`](../../request-1029/checklist.md) `:22`).

## 끝나면

- **알릴 곳** — HWAX 포털 세션 `hwaxportal-a5`. ARP 팀은 그 세션에 닿지 않으므로 요청을 보낸 사람이 답을 받아 포털 세션에 넘긴다. 포털 세션이 [`../outbound.md`](../outbound.md) 2절과 `server-setup.md` 에 옮긴다(outbound.md 머리). 대조 시각에 `docs/request-1030/server-setup.md` 는 아직 없고, 체크리스트 0절 '받은 답을 `outbound.md` · `server-setup.md` 에 옮김' 도 열려 있다.
- **알려 줄 것**
  - AR-9 — 단위를 실은 basicInfo 수치 칸 이름과 단위(낙하 높이가 무엇으로 나가는지). 포털은 이 답을 보고 HP-53 의 ARP 함정 줄('AR-9 전까지')을 걷는다.
  - AR-10 — MCP 출력에서 가린 사람 칸 이름(`partOwner` 와 그 밖)과 가린 꼴(뺐는지 · 가림 표시인지). 게이트웨이 HG-22 도 칸 이름으로 가리므로, 이름을 알면 두 겹이 같은 칸을 보는지 맞대 볼 수 있다.
  - AR-1 ~ AR-4 — 16 문서 2절의 행마다 한 것(과제명 · 과제코드로 모델 찾기 · 못 찾은 까닭 넷 · 받기 상태). MCP 도구 이름 · 인자 · 응답 칸(`modelMatch` 등)이 바뀌었으면 그 이름.
  - 도구 이름 — arp_upload_create · arp_upload_stage · arp_upload_register · arp_upload_discard 를 바꿨는지. HP-53 이 이 이름을 ARP 운영자 목록에 넣고, 운영자 동기화는 게이트웨이에 없는 이름이 하나라도 있으면 아무것도 쓰지 않는다(`sync-he-personas.py:147-150` · `:193-196`).
  - 판 · 반영 시각 — ARP 커밋(또는 판 번호)과 ARP 서버에 반영한 시각.
- **배포 산출물** — 우리 쪽 SIF · Drive 판은 없다. ARP 는 update-all 로 받지 않는 플랫폼이고(정본 머리), 게이트웨이는 `arp` 백엔드로 ARP 서버의 `/mcp` 에 붙을 뿐이다(`provision-config.sh:654-656`). ARP 서버 반영은 ARP 팀 몫이다.
- **cae00 사람 몫(ARP 가 반영한 뒤)**
  - ARP 도구 · 설명이 바뀌었으면 게이트웨이로 확인한다. 도구가 있는지와 그 글은 소스가 아니라 게이트웨이 `tools/list` 로 본다(포털 `CLAUDE.md` MCP 절). 게이트웨이는 `GATEWAY_REVIVE_INTERVAL`(기본 60초, `gateway.py:217`)마다 백엔드 `list_tools` 를 다시 받아, 지문(`_tools_fp`, `:471`)이 바뀌면 다시 모은다(`:1519-1526`).
  - 다시 볼 때는 게이트웨이 결과 캐시를 넘긴다. 같은 호출의 결과를 `GATEWAY_CACHE_TTL`(기본 300초, `gateway.py:437`) 동안 붙들 수 있으므로(`_cache_put`, `:741-749`) 반영 직후 같은 질문은 5분 뒤에 본다.
  - HP-53 의 ARP 함정 줄을 걷는 것은 포털 몫이다. 걷은 뒤 cae00 에서 `python3 infra/scripts/sync-he-personas.py --apply` 로 반영한다(update-all 은 미리보기만 한다 — `update-all.sh:1176` · `:1182`).
- **7절 다시 볼 시험**
  - ARP 가 걸린 줄은 넷째 줄 하나다. '| DW-07 · DW-03 · 06 · 12 · 22 | HG-21 · HG-22 뒤 | 숫자가 그대로 나오고, 사람 이름 · 메일 · 사설 IP 가 가려진다. |' 가운데 DW-06 이 ARP `partOwner` 다. 7절은 이 줄을 HG-21 · HG-22 뒤로 걸었다.
  - AR-9(낙하 높이 단위)과 AR-1 ~ AR-4 의 다시 볼 줄은 7절에 없다. 두 행의 근거 시험은 DW-06 · OT-13(AR-9)과 DW-21 · OT-08(AR-1 ~ AR-4)이다. DW-21 은 7절에서 'DW-21 · OT-15 | SG-04 결정 뒤' 줄(SignalForge 몫)에 있다. ARP 를 다시 볼지는 사람이 정한다.
