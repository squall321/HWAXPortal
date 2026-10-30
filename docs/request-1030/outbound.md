# 10-30 요청 — 다른 플랫폼에 보낸 것 · 사람이 보낼 것

요청서 정본 [`../request_261030.md`](../request_261030.md). 행의 글(무엇이 · 근거 · 할 일)은 정본에 있고, 보낼 때도 그 글을 그대로 붙였다.
답이 오면 이 표의 '답' 칸과 [`server-setup.md`](server-setup.md)(cae00 에서 사람이 할 일)에 옮겨 적는다.

## 1. 세션으로 보낸 것(10-30 KST, 포털 세션 hwaxportal-a5)

| 받는 곳 | 행 | 덧붙인 것 | 답 |
|---|---|---|---|
| SignalForge `signalforge-c6` | SG-04(다시) · SG-19 | HA-33 이 `{results, notes}` 를 펼친다 — 칸 이름을 지켜 달라. 세션이 둘이라 c6 에만 보냄 | 기다림 |
| DocForge `docforge-f6` | HH-14 | HA-28 이 읽을 docforge_status 의 끝 · 도는 중 칸, 새 목록 도구에 readOnlyHint | 10-30 끝 — DocForge main `e72cbe5`(도구) · `ab5547e`(판 0.3.1), **배치(release · HEAXHub 등록 사본 · SIF · Drive)는 그 세션의 사용자 승인 대기**(cae00 release 는 아직 `3ba0f6f` 0.3.0). ① 새 도구 `docforge_list_inputs()`(인자 없음 · readOnlyHint) — 운영자 입력 상자(SIF `/data/inbox`, 호스트 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/`)와 바로 밑 폴더, 응답 `{root, root_host, total, truncated, files:[{path, name, folder, bytes, format, modified}]}` 새것부터 200개, `files[].path` 를 convert 에 그대로. 업로드 스테이징은 나열하지 않음(남의 파일 이름이 보여서 — 요청과 다른 점, 근거 DocForge R-D47). ② docforge_status — `status` queued · running / done · failed · cancelled, `progress` 0 ~ 100, `stage` S0 ~ S7, `error`; **도구 오류는 `{ok:false, error, status:403}` 처럼 `status` 가 숫자 — 숫자면 기다리기를 끝낸다**, 잡은 한 번에 하나라 queued 는 앞 잡 대기. ③ readOnlyHint 는 읽기 넷(capabilities · list_inputs · status · package)에만. ④ 페르소나 `he-doc-docforge` 고침 셋(key_tools 에 list_inputs · can 의 맡기기 줄 · pitfalls 의 path 줄)은 **0.3.1 이 cae00 게이트웨이에 실린 뒤**(동기화가 없는 도구 이름에서 멈춘다 — 판단 C-8). ⑤ cae00 사람 몫 — 새 박스 값 없음, 0.3.1 받은 뒤 `/apps/doc_forge/api/v1/capabilities` version 0.3.1 · 게이트웨이 `/refresh` 뒤 docforge_* 여섯, OB-94 시험 파일은 위 상자에 평문 pptx 하나, dev 상자는 비워 둔다(build-all 이 dev 앱 데이터를 cae00 에 심는다) |
| StepForge `stepforge-d4` | ST-12 | HA-29 카드에 실을 시작 전 작업량을 셀 길이 있는지, HA-28 이 읽을 상태 칸 | 10-30 받음 — ① 시작 전 작업량은 이미 있는 읽기 도구 `estimate_cost(project_id, job, args)`(형상을 읽지 않고 DB 값만, 칸 `expected_s` · `cost_basis` · `gateway_verdict`(over · may_exceed · under · no_basis) · `basis_note` · `advice`) — ST-12 (2)가 판 전체 작업량 칸을 여기와 run_job 시작 응답에 더한다(칸 이름은 짓고 알림). ② `job_status(job_id)` 의 `status` 는 queued · running(도는 중) / done · failed · cancelled(끝), `progress` 0 ~ 100, `error` · `ended` · `result`, 판 전체 측정은 수십 분 — 상한을 넉넉히. ③ ST-12 (1) 합치기 진행률은 OCC 한 호출이라 묶음 합치기를 실물 큰 판에서 재 보고 정함, (3) owner 는 원천에서 가림. 지금 다른 묶음(온톨로지 그래프 도구) 착지 중이라 ST-12 는 그 뒤 판 |
| KooRemapper `kooremapper-4a` | KR-23(결정) · KR-01(다시) · KR-16(다시) | HP-53 이 레시피 도구를 DynaForge 운영자 writes 에, HP-52 가 find_reports 의 `items` 를 읽는다 | 기다림 |
| MX 백서 `mxwhitepaper-26` | MW-01(다시) · MW-12 | HA-08 이 '…열리지 않았습니다' 도 받는다 — 문구는 그대로 둬도 된다 | 기다림 |
| SmartTwinExplorer `smarttwinexplorer-06` | PA-20 | cluster_info 가 이 리포에 있다. 게이트웨이 HG-22 도 메일 · 사설 IP 를 가린다 | 기다림 |
| SmartTwinMCP `smarttwinmcp-4c` | PA-16 · PA-19(다시) | OB-92 · OB-34 · OB-25 가 이 둘을 기다린다 — PA-19 코드 몫만이라도 먼저 | 기다림 |

## 2. 사람이 보낼 것(이 세션이 닿지 않는다)

### AIDataHub — 살아 있는 세션이 없다

행 AD-01(다시) · AD-19 · AD-21 · AD-03(다시) · AD-04(다시) · AD-05 · AD-06(다시) · AD-07(다시) · AD-20 은 정본 끝 절 'AIDataHub' 표 그대로다.
AIDataHub 세션을 열 때 그 표와 아래 셋을 함께 준다. 10-27 회차의 코드 대조는 [`../request-1027/review-10-AIDataHub.md`](../request-1027/review-10-AIDataHub.md) 다.

1. **AD-04(다시)에 덧붙임 — 스위치 상태 칸.** 본문 검색 스위치(`AIDH_RECORDS_Q_BODY_SEARCH`)를 켤 때 기록 목록 · 검색 응답에 그 스위치 상태를 싣는다. 포털 HP-21(다시)이 그 칸을 보고 검색칸 문구를 바꾼다(포털 판단 C-3).
2. **AD-19 와 에이전트 HA-31 의 나눔.** 에이전트는 '추천 근거 · 기록 수' 처럼 다른 물음이 든 질문을 가로채지 않게 고친다. 추천 점수의 낱말 겹침 항(요청 낱말 · 신호 0 전문가)은 AIDataHub 몫이다.
3. **AD-21 과 포털 동기화.** 운영자 정의 동기화(`infra/scripts/sync-he-personas.py`)가 저장 뒤 500 에 첫 건에서 멈춘다. 포털은 저장 여부를 다시 읽어 확인하고 이어 가게 고치는 중이다(작으면 — HP-53 묶음). 근본 고침(저장 뒤 500 을 내지 않기)은 AIDataHub 몫 그대로다.

### Datahub 플랫폼(허브 셋 — hwax-batch) · ARP · 사내 파트너

- DP-14 · DP-15(4절)와 DP-01 · DP-02 · DP-04 · DP-05 · DP-06 · DP-07 · DP-08 · DP-09(끝 절) — cae00 의 Datahub 요청서(12-Datahub-platform)와 같은 묶음으로 사람이 보낸다.
- AR-9 · AR-10(4절)과 AR-1 ~ AR-4(다시) — 요청서 6절대로 cae00 의 16-ARP-ODBHub-core-ontology.md 에 이어 붙여 사람이 보낸다. 보내기 전에 사람이 16 문서를 한 번 읽는다(O-9).
- 포털 쪽 짝 — 게이트웨이 HG-22 가 사람 칸 이름 · 메일 · 사설 IP 를 가린다. 글 속 이름(DP-08 의 검출자 · 작업자)은 게이트웨이가 꼴로 가르지 못해 원천 몫 그대로다. ARP 낙하 높이 단위(AR-9)는 고쳐지기 전까지 포털 HP-53 이 ARP 운영자 함정 줄('낙하 높이 칸은 단위가 없다 — 시험 조건은 cm')로 메운다.
