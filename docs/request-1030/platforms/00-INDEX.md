# 00 플랫폼별 할 일 — 10-30 요청 색인

- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md). 정본의 행 78개(1 ~ 4절 17 · 끝 절 34 · 5절 우리 몫 27)를 시트 열세 장에 나눴다. 같은 요청의 계획 · 판단 · 체크리스트 · 보낸 것은 [`../PLAN.md`](../PLAN.md) · [`../context-notes.md`](../context-notes.md) · [`../checklist.md`](../checklist.md) · [`../outbound.md`](../outbound.md) 다.
- **기계 대조(2026-10-30 18:28 KST)** — 행마다 정확히 한 시트가 `### <ID>` 제목으로 맡는다(78/78). 정본 칸 268개(심각도 · 무엇이 · 근거 · 할 일 · 다시 볼 시험 · 출처 · 상태, 4절의 '대상' 은 뺐다)가 그 행의 절에 글자 그대로 있다. 맞춘 것은 띄어쓰기와 상대 링크 대상뿐이다. 시트에 IPv4 · 토큰 꼴은 없다.
- **대조하며 시트를 고친 것** — [14](14-Partner-apps.md) '끝나면' 의 소제목 둘을 세션 이름이 앞에 오게 바꿨다(행 제목이 시트마다 하나가 되게). [12](12-Datahub-platform.md) 의 PA-20 상태와 [05](05-StepForge.md) 의 OB-59 상태는 [`../outbound.md`](../outbound.md) · 포털 [`../../request-1029/server-setup.md`](../../request-1029/server-setup.md) 의 기록에 맞췄다.
- **시트의 시각** — 시트마다 '지금 판에서의 자리' 는 dev 에서 17:50 ~ 18:13 KST 에 대조한 것이다. 고치는 중인 행(가지 · 설계서)은 그 뒤에도 바뀐다.

## 시트

'어떻게' 의 굵은 글은 다섯 갈래(우리가 고침 · 세션에 보냄 · 답 받음 · 사람이 보냄 · 보내지 않음)다. '다시 볼 시험' 은 정본 7절의 줄이고, 7절에 없으면 행 칸 · 근거의 문항을 적었다.

| 시트 | 플랫폼 | 행(심각도 높음 수 포함) | 받는 곳 | 어떻게 | 다시 볼 시험 |
|---|---|---|---|---|---|
| [01-HWAXPortal](01-HWAXPortal.md) | HWAX 포털 | 8 · 높음 0 — HP-51 · HP-52 · HP-53 · HP-54 · HP-55 · HP-56 · HP-42(다시) · HP-21(다시) | 이 세션 `hwaxportal-a5` | **우리가 고침.** HP-52 · HP-55 · HP-56 은 가지에 커밋이 있다(합치기 전). HP-51 · HP-53 은 대조 시각에 커밋이 없었다. 조건부 셋(HP-54 · HP-42(다시) · HP-21(다시))은 판단 C-4 · C-2 · C-3 의 조건을 기다린다. | DW-12(HP-51) — 7절 'HG-21 · HG-22 뒤' 줄과 같은 재시험에서 본다. |
| [02-HWAXMcpGateway](02-HWAXMcpGateway.md) | HWAX MCP 게이트웨이 | 3 · 높음 2 — HG-21 · HG-22 · HG-23 | 이 세션 `hwaxportal-a5` | **우리가 고침.** HG-21 · HG-22(REST 다리 R-08 포함)는 가지 `wt1030/pii` 에서 고치는 중이다(대조 시각 커밋 0). HG-23 은 닫았다(판단 C-1). | DW-07 · DW-03 · 06 · 12 · 22(HG-21 · HG-22 뒤). |
| [03-HWAXAgentServer](03-HWAXAgentServer.md) | HWAX 에이전트 서버 | 10 · 높음 4 — HA-26 ~ HA-34 · HA-08(다시) | 이 세션 `hwaxportal-a5` | **우리가 고침.** HA-26 첫 몫은 main `7ca3a2e` 에 들어갔다. 재시도 몫 · HA-31 · HA-32 · HA-33 · HA-34 · HA-08(다시)는 가지에 커밋이 있다(합치기 전). 높음 넷(HA-27 ~ HA-30)은 설계서 단계다(커밋 전). | OT-04 · 08 · 09 · DW-05(HA-27 뒤), 전문가 · 앱 핀 · 붙인 문서 챗(HA-26 뒤, OB-91 우회를 걷은 상태), DW-02 후속 · DW-03(HA-28 · HA-29 뒤), DW-13(HA-31 뒤). 행 칸에만 OT-07(HA-30) · DW-22(HA-32). |
| [04-KooRemapper-DynaForge](04-KooRemapper-DynaForge.md) | KooRemapper · DynaForge | 3 · 높음 0 — KR-23 · KR-01(다시) · KR-16(다시) | 세션 `kooremapper-4a` | **세션에 보냄.** 답을 기다린다. KR-23 은 고칠 일이 아니라 결정을 묻는 행이다. | 7절 줄 없음. |
| [05-StepForge](05-StepForge.md) | StepForge | 1 · 높음 0 — ST-12 | 세션 `stepforge-d4` | **세션에 보냄 · 답 받음.** 시작 전 작업량(`estimate_cost`)과 `job_status` 칸을 알려 왔다. ST-12 고침은 다른 묶음(온톨로지 그래프 도구) 뒤 판이다. | DW-02 후속 · DW-03(HA-28 · HA-29 뒤), DW-03 · 22(HG-21 · HG-22 뒤 줄). |
| [06-HEAXHub](06-HEAXHub.md) | HEAXHub(DocForge) | 1 · 높음 0 — HH-14 | 세션 `docforge-f6` | **세션에 보냄 · 답 받음.** 코드는 끝났다(`e72cbe5` · `ab5547e`, 0.3.1). 배치(release · 등록 사본 · SIF · Drive)는 그 세션의 사용자 승인을 기다린다. | DW-10(HH-14 뒤) — 0.3.1 이 cae00 에 뜨고 OB-94 의 시험 파일을 둔 뒤. |
| [08-SignalForge](08-SignalForge.md) | SignalForge | 2 · 높음 1 — SG-04(다시) · SG-19 | 세션 `signalforge-c6` | **세션에 보냄.** 답을 기다린다. 18:02 KST 에 그 작업 트리에 SG-19 의 커밋 전 변경이 보였다. | DW-21 · OT-15(SG-04 결정 뒤). |
| [09-MXWhitePaper](09-MXWhitePaper.md) | MX 백서 | 2 · 높음 0 — MW-01(다시) · MW-12 | 세션 `mxwhitepaper-26` | **세션에 보냄 · 답 받음.** 끝났다(`bb0a6a1` · `bd2e79b`). 새 이미지 없이 update-all 의 git 받기로 간다. | 7절 줄 없음. 5절 OB-64 · OB-65 손 시험과 맞물린다. |
| [10-AIDataHub](10-AIDataHub.md) | AIDataHub | 8(번호 9) · 높음 0 — AD-01(다시) · AD-19 · AD-21 · AD-03(다시) · AD-04(다시) · AD-05 · AD-06(다시) · AD-07(다시) · AD-20 | 코드 행은 이 세션(판단 C-7), 데이터 단계는 사람 | **사람이 보냄 → 코드 행은 우리가 고침.** 세션이 없어 사람 몫이던 것을 판단 C-7 이 코드 행만 이 세션에 맡겼다(가지 다섯, 대조 시각 커밋 0). 데이터 단계는 사용자 OK 뒤 사람 몫이다. | 7절 줄 없음. 10-27 7절에서 이어지는 cae00 확인 다섯(시트 '끝나면'). |
| [12-Datahub-platform](12-Datahub-platform.md) | Datahub 플랫폼(허브 셋 — hwax-batch) | 9(번호 10) · 높음 2 — DP-14 · DP-15 · DP-01(다시) · DP-02(다시) · DP-04 · DP-05(다시) · DP-07(다시) · DP-08(다시) · DP-06(다시) · DP-09(다시) | 사내 다른 팀(Datahub 플랫폼 담당) | **사람이 보냄.** 아직 안 갔다. cae00 의 12-Datahub-platform 요청서와 한 묶음으로 보낸다. | 7절 줄 없음. 행의 근거 문항(OT-09 · 11 · OT-12 · DW-01 · N-18 등)으로 cae00 에서 본다. |
| [14-Partner-apps](14-Partner-apps.md) | 파트너 앱(ste 클러스터 조회 · stcx SmartTwinMCP) | 2(번호 3) · 높음 0 — PA-20 · PA-16 · PA-19(다시) | PA-20 은 세션 `smarttwinexplorer-06`, PA-16 · PA-19(다시)는 세션 `smarttwinmcp-4c` | **세션에 보냄.** PA-20 은 답 받음 — 끝났다(`4f5e0e0`). cae00 반영(`deploy-ste.sh`)은 사람 몫이다. PA-16 · PA-19(다시)는 답을 기다린다. | DW-12(HG-21 · HG-22 뒤 줄) — PA-20 반영과 HG-22 가 다 든 뒤. |
| [16-ARP](16-ARP.md) | ARP(AI Ready Portal) | 2(번호 6) · 높음 0 — AR-9 · AR-10 · AR-1 ~ AR-4(다시) | 사내 다른 팀(ARP 담당) | **사람이 보냄.** 아직 안 갔다. cae00 의 16-ARP-ODBHub-core-ontology.md 에 이어 붙이고, 보내기 전에 사람이 16 문서를 읽는다(O-9). | DW-06(HG-21 · HG-22 뒤 줄). |
| [90-OURS](90-OURS.md) | 우리 몫(cae00 박스 · 사람) | 27(번호 33) · 심각도 칸 없음 — OB-91 ~ OB-103 · OB-01 ~ OB-89 | cae00 운영(사람) | **보내지 않음.** 시트가 네 묶음(지금 할 수 있는 것 · 우리 고침 뒤 · 다른 플랫폼 답 뒤 · 사람 결정)으로 나눴다. | 전문가 · 앱 핀 · 붙인 문서 챗(OB-91 을 걷은 뒤) · DW-10(OB-94 뒤). 나머지 7절 다섯 줄도 시트 끝에 정본 그대로 있다. |
| **합계** | | **78 · 높음 9** — 중간 19 · 낮음 23 · 우리 몫 27(정본 건수 표와 같다) | | | |

## 사람이 보내야 하는 것

- **AIDataHub** — [`10-AIDataHub.md`](10-AIDataHub.md). 세션이 없어 처음에는 사람 몫이었다([`../outbound.md`](../outbound.md) 2절). 판단 C-7(사용자 결정 10-30)로 코드 행(AD-01 의 코드 · AD-19 · AD-20 · AD-21 · AD-03(다시) · AD-07(다시))은 이 세션이 고친다. 사람에게 남은 것은 둘이다.
  - 데이터 단계 — AD-05 · AD-06(다시)의 dev 원본 지우기, AD-01 다시 짓기 실행(dev 먼저, cae00 은 그 박스 병합 뒤), AD-04(다시)의 dev DB 사본 측정. 모두 사용자 OK 뒤다.
  - outbound 2절 덧붙임 1(AD-04(다시) — 응답에 스위치 상태 칸)은 C-7 의 '맡는 것' 에 없다. 화면까지 닿으려면 에이전트 서버 `catalog_agent_records` 도 그 칸을 넘겨야 한다(시트 AD-04(다시) 맞물림).
- **Datahub 플랫폼(허브 셋)** — [`12-Datahub-platform.md`](12-Datahub-platform.md) 의 아홉 행을 cae00 의 12-Datahub-platform 요청서와 한 묶음으로 보낸다. DP-08(다시)은 원천 개인정보 묶음(AR-10 · PA-20)과 같이 간다. HA-30 설계서 9.2 Q9 의 'GRAPH-0001 문구에 key 로 object_resolve 한 줄' 은 정본 행이 아니라서, 덧붙일지는 보낼 때 정한다.
- **ARP** — [`16-ARP.md`](16-ARP.md) 의 AR-9 · AR-10 과 AR-1 ~ AR-4(다시)를 cae00 의 16-ARP-ODBHub-core-ontology.md 에 이어 붙여 보낸다(요청서 6절). 보내기 전에 사람이 16 문서를 한 번 읽는다(O-9). 그 문서는 cae00 에만 있어서 시트의 16 문서 링크는 이 리포에서 열리지 않는다.

## 결정이 필요한 것

- **KR-23 — 레시피 등록을 사람 승인으로 묶을지(KooRemapper 의 답).** KooRemapper 계획서는 'LLM 자동 + 자동 관문' 을 사용자가 고른 것으로 적었다. 그래서 그 결정을 바꿀지가 답이다. HA-29 확인 카드는 웹 챗에만 걸리고, 게이트웨이에 바로 붙은 MCP 손님은 그 카드를 지나지 않는다.
- **OB-92 — SmartTwin 운영자를 살리는 길.** 첫째 길(잇기)은 PA-16 · PA-19(다시)가 끝난 뒤 OB-34 · OB-25 로 연다. 둘째 길(정의 바꾸기)을 고르면 HP-54 를 연다.
- **OB-26 — ODB 허브 운영자(he-cad-odbhub)를 둘지.** '둔다' 면 HP-53 의 ODB todo · key_tools 를 쓴다. writes · confirm 은 판단 C-5 대로 지금 채운다.
- **AD-05 · AD-06(다시) — dev 원본 데이터 지우기.** 두 전문가와 데모 카드 3장을 지울지와 그 시각을 정한다(사용자 OK — C-7). 지우기 전에 dynaforge-report 에 묶인 레코드를 sim-drop-impact 로 다시 묶을지 먼저 정한다. cae00 몫은 그 뒤 OB-87 이다.
- **AIDataHub 의 나머지 데이터 단계** — AD-01 다시 짓기 실행과 AD-04(다시) 측정도 사용자 OK 뒤다. AD-20 을 이행(alembic)으로 합치면 cae00 은 기동 때 데이터가 바뀌므로, 이것도 OK 대상인지 함께 정한다(10 시트의 추정).
- **AD-04(다시) 덧붙임 1 을 누가 맡을지** — 응답의 스위치 상태 칸이다. C-7 목록 밖이고, HP-21(다시)이 이 칸을 기다린다.
- **OB-89 — 본문 검색 스위치를 켤지.** AD-04(다시)의 잰 값이 온 뒤 정한다.
- **OB-04 — 운영 앱 둘의 '(시험)' 라벨.** 요청서는 두 앱을 '운영 앱' 이라 부르는데, 코어 어휘표(`backend/config/core_vocab.json:36-37`)는 같은 둘을 역할 `staging` 으로 숨긴다(10-29 D-2). 라벨과 역할 칸을 같은 뜻으로 맞출지 함께 정한다.
- **HG-22 의 가림 범위** — 메일 · 계정 꼴을 칸 이름과 상관없이 가리면 whoami 의 본인 이메일도 가려질 수 있다(OB-98 · 10-27 M-16). '영문.영문숫자' 꼴이 DocForge 목록의 파일 이름 · 경로(`deck.pptx` 등)를 가리면 docforge_convert 가 경로를 못 받는다(06 시트). 고치는 중인 가지에서 두 자리를 어떻게 비킬지 정한다.
- **SG-04 데이터 결정(SignalForge 쪽)** — 제품 행을 나눌지다(10-29 묻는 글의 안 A · B · C, 포털 권고 A). DW-21 · OT-15 다시 보기가 이 결정을 기다린다.
- **DocForge 0.3.1 배치(그 세션의 사용자 승인)** — 배치 뒤에야 OB-94 · DW-10 · C-8 고침 셋이 열린다.

## 답을 받으면 옮길 곳

- **[`../outbound.md`](../outbound.md)** — 세션 답은 1절 표의 '답' 칸에, 사람이 보낸 것의 답은 2절에 옮긴다. 18:28 KST 에 답을 기다리는 곳은 KooRemapper(KR-23 · KR-01(다시) · KR-16(다시)) · SignalForge(SG-04(다시) · SG-19) · SmartTwinMCP(PA-16 · PA-19(다시))다. 사람이 보낼 Datahub · ARP 는 아직 보내지 않았다.
- **`server-setup.md`(이 폴더 — 아직 없다, [`../checklist.md`](../checklist.md) 0절 · 4절)** — cae00 에서 사람이 칠 명령과 기대값을 적는다. 이미 받은 답에서 옮길 것이 넷 있다.
  - DocForge — 0.3.1 배치 뒤 `/apps/doc_forge/api/v1/capabilities` 의 version 0.3.1, 게이트웨이 `/refresh` 뒤 `docforge_*` 여섯, OB-94 시험 파일(입력 상자에 평문 pptx 하나), C-8 고침 셋 뒤 운영자 동기화, OB-102.
  - MX 백서 — update-all 의 git 받기와 이관 0059 · 0060, mxwp-mcp `tools/list` 의 `wiki_*` 0개, 로그 두 줄.
  - SmartTwinExplorer — Drive 스테이징 번들(`4f5e0e0`)을 `STE_DEPLOY=1 infra/scripts/deploy-ste.sh` 로 반영한 뒤 DW-12 다시 보기.
  - StepForge — `infra/scripts/drive-drift.sh heax` 대조, update-all 뒤 OT-14 · OT-15(OB-59). ST-12 판은 그 뒤에 온다.
- **[`../checklist.md`](../checklist.md)** — 0절 '받은 답을 옮김' 과 3c(DocForge 고침 셋 — 0.3.1 이 cae00 게이트웨이에 실린 뒤)를 체크한다.
- **그 플랫폼 시트** — 머리의 '어떻게 갔나' 와 '끝나면' 을 답에 맞춘다. 이번 대조에서 낡은 상태 둘(12 의 PA-20 · 05 의 OB-59)을 바로잡았다.
