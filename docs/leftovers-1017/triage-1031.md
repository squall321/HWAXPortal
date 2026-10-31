# 옛 남은 일 다시 가르기(2026-10-31) — 448줄 판정 · 사용자 결정 · dev 작업 · cae00 물음

> 사용자 결정(10-31) — 옛 남은 일 목록(10-08 8·9·10차 · 10-17 [leftovers](PLAN.md) · [followups](../followups-1017/PLAN.md) · 그 밖 `docs/*/checklist.md`)을
> 갈라 움직일 수 있는 것을 움직인다. 지금 라운드(`request-1027` · `request-1029` · `request-1030` · `design-risk-review/ecad-1031` · `cae00-inbox`)는
> 그쪽이 다루어 뺐다. 판정은 지금 코드와 형제 리포의 커밋 · 파일:줄에 맞댄 근거로 했다(형제 리포는 읽기만). Report Archive 는 사용자가 다루는
> 리포가 아니라 '우리 몫 아님' 으로만 적고 묻지 않는다(10-31 지시).

## 0. 무엇을 했나

- **풀림 · 걷음은 그 줄에 덧붙였다**(`ddf3046`). 체크박스는 `[x]` 로 바꾸고 줄 끝에 ` — 풀림 <근거> (10-31 정리)` 또는 ` — 걷음: <까닭> (10-31 정리)` 를 단다.
  옛 글은 한 글자도 고치지 않았다 — 바뀐 165줄을 옛 줄과 맞대 '체크박스 + 덧붙임' 말고 바뀐 것이 0 인지 스크립트로 봤다. 표 줄은 마지막 칸 안에,
  여러 줄 항목은 항목 끝 줄에 달았다. 근거로 인용한 커밋은 그 리포에 있는지 다시 확인했다(전부 있다).
- **낡은 절차서 한 줄을 바로잡았다**(`3dd1db0`) — 8·9·10차 [server-setup](../change-request-8-10/server-setup.md) 4-2 의 `ARP_TOKEN` 칸이 '토큰만으로는 아무 줄 없이
  지나간다' 고 적었는데 `892a8fe` 뒤로는 `○` 줄이 찍힌다. 절차서는 기록 파일이 아니라 사람이 따르는 글이라 고친다.
- **사용자 결정 · dev 작업 · cae00 · 바깥 줄은 손대지 않았다**(열린 채). 아래 표 A · B · C 가 그 줄들의 정리다.
- **cae00 에서 읽기로 답할 물음**은 받은 편지함 [`2026-10-31-backlog.md`](../cae00-inbox/2026-10-31-backlog.md) Q1 ~ Q20 에 실었다. 박스를 바꾸는 사람 걸음은
  받은 편지함이 아니라 표 C-2 와 각 요청 폴더의 `server-setup.md` 에 있다(받은 편지함 README — 그 폴더는 묻는 곳이다).

## 1. 셈

| 갈래 | 줄 | 한 일 · 어디로 |
|---|---|---|
| 풀림(이미 됨) | 109 | 체크 + 근거 — 8·9·10차 context-notes 120줄 하나에 셋이 들어 줄로는 107(§6) |
| 걷음(낡음 · 대체됨) | 51 | 걷음 + 까닭 — 표 D |
| 사용자 결정 | 101 | 물음 30 + 판정 중에 나온 물음 둘 — 표 A |
| dev 에서 할 수 있음 | 47 | 작업 38 — 표 B |
| cae00 · 바깥 | 140 | 받은 편지함 물음 39줄(Q1 ~ Q20) · 사람 걸음 64 · 차례 대기 28 · 우리 몫 아님(Report Archive) 9 — 표 C |
| 합 | **448** | 줄로는 446 |

<details><summary>파일마다(풀림 · 걷음 · 결정 · dev · cae00·바깥)</summary>

| 파일(`docs/` 아래) | 풀림 | 걷음 | 결정 | dev | cae00·바깥 | 합 |
|---|---|---|---|---|---|---|
| `design-risk-review/checklist.md` | 17 | 6 | 2 | 17 | 15 | 57 |
| `risk-200k/checklist.md` | 4 | 2 | · | 1 | 7 | 14 |
| `risk-credentials/checklist.md` | 1 | · | · | 1 | 2 | 4 |
| `risk-review-redesign/checklist.md` | 1 | 7 | 2 | · | 12 | 22 |
| `deliberation-quality/checklist.md` | 1 | 3 | 2 | 3 | 6 | 15 |
| `deliberation-quality/method-menu/checklist.md` | 21 | · | · | · | · | 21 |
| `claude-delib-parity/checklist.md` | 1 | · | · | 1 | · | 2 |
| `delib-ops/checklist.md` | 2 | · | · | · | · | 2 |
| `chat-depth-context/checklist.md` | 1 | 1 | · | · | 2 | 4 |
| `chat-llm-stcx/checklist.md` | 1 | · | 1 | · | 1 | 3 |
| `chat-ppt/checklist.md` | 2 | · | · | · | 1 | 3 |
| `chat-self-check/checklist.md` | 2 | · | · | · | · | 2 |
| `chat-vision/checklist.md` | · | · | · | · | 1 | 1 |
| `cluster-deploy/checklist.md` | 2 | 2 | 50 | 1 | · | 55 |
| `data-migration/checklist.md` | 1 | 1 | 15 | 1 | 1 | 19 |
| `update-all-skip-unchanged/checklist.md` | 1 | · | · | · | · | 1 |
| `procedures/checklist.md` | 9 | 3 | 11 | 6 | 16 | 45 |
| `doc-to-ra/checklist.md` | 3 | · | 1 | · | 16 | 20 |
| `analysis-routines/checklist.md` | · | · | · | 1 | 1 | 2 |
| `doc-deliberate/checklist.md` | 1 | 1 | · | · | 2 | 4 |
| `upload/checklist.md` | · | · | · | 1 | 1 | 2 |
| `cluster-wiring/checklist.md` | 7 | 7 | 1 | · | 2 | 17 |
| `ste-cae00/checklist.md` | 4 | 3 | · | · | 2 | 9 |
| `ste-fullangle/checklist.md` | · | · | · | · | 4 | 4 |
| `sso-delegation/checklist.md` | 1 | 3 | · | · | 5 | 9 |
| `ext-connect/checklist.md` | 5 | · | · | · | · | 5 |
| `web-research/checklist.md` | · | 1 | 4 | 3 | 5 | 13 |
| `mxwp-wiki/checklist.md` | 1 | · | 1 | · | 6 | 8 |
| `ra-reconnect/checklist.md` | · | · | · | · | 3 | 3 |
| `ra-workspace/checklist.md` | · | 2 | · | · | · | 2 |
| `gateway-audit-ip/checklist.md` | 1 | · | · | · | · | 1 |
| `access-control/checklist.md` | · | · | · | · | 1 | 1 |
| `access-history/checklist.md` | 1 | · | · | · | · | 1 |
| `change-request-6/checklist.md` | 1 | · | · | · | · | 1 |
| `change-request-7/checklist.md` | · | · | · | · | 1 | 1 |
| `change-request-8-10/context-notes.md` | 4 | 2 | · | · | 5 | 11 |
| `change-request-8-10/server-setup.md` | 3 | 1 | 3 | 2 | 3 | 12 |
| `leftovers-1017/PLAN.md` | 2 | 3 | 1 | · | · | 6 |
| `leftovers-1017/context-notes.md` | 1 | · | 1 | 1 | · | 3 |
| `followups-1017/PLAN.md` | 1 | · | · | · | · | 1 |
| `followups-1017/checklist.md` | · | 2 | · | · | 3 | 5 |
| `followups-1017/context-notes.md` | 1 | · | 1 | · | 1 | 3 |
| `followups-1017/requests.md` | 2 | · | · | 1 | 2 | 5 |
| `followups-1017/server-setup.md` | · | · | 1 | · | 1 | 2 |
| `delib-engine-feedback/checklist.md` | · | · | 1 | · | · | 1 |
| `thinking-mode/checklist.md` | · | · | · | 1 | · | 1 |
| `chat-actions/checklist.md` | 1 | 1 | · | 1 | 4 | 7 |
| `improvement-1015/checklist.md` | · | · | 1 | · | 3 | 4 |
| `llm-pool/checklist.md` | · | · | · | · | 1 | 1 |
| `embedder-bge-m3/checklist.md` | 1 | · | · | · | · | 1 |
| `org-chart/checklist.md` | · | · | · | · | 1 | 1 |
| `request-1015/checklist.md` | · | · | · | · | 1 | 1 |
| `persona-chat/checklist.md` | · | · | · | 2 | · | 2 |
| `token-bat/checklist.md` | · | · | · | · | 2 | 2 |
| `ui-refresh/checklist.md` | 1 | · | 2 | 3 | · | 6 |

</details>

줄 번호는 `ddf3046` 직전 판(`a302af4`) 기준이다. 덧붙임만 했으므로 지금 판에서도 같다.

## 2. 표 A — 사용자 결정(101줄 → 물음 32)

**굵은 것이 추천**이다. 묶음(A1 · A2 · A3)은 대표 물음 하나에 답하면 딸린 줄이 그 답을 따른다.

| # | 줄 | 물음 | 고를 것 |
|---|---|---|---|
| A1 | cluster-deploy 50줄(8 · 9 · 10 · 16 · 17 · 19 ~ 21 · 30 ~ 33 · 37 ~ 44 · 48 · 50 · 51 · 53 ~ 58 · 62 ~ 64 · 68 · 72 ~ 77 · 82 ~ 87 · 91 · 92 · 98 ~ 100) | 클러스터 배포 계획 v2(08-02 — 새 18대 · /data 1PB 전제, 10-17 결정 15 로 보류)를 어떻게 할까. | **① 걷기** — plan.md 는 기록으로 두고 열린 50줄을 걷음으로, 장비가 오면 HWAXProd 기준으로 새로 짠다(전제 셋이 바뀌었다 — RA 는 RA 담당 서버로 · 임베더는 BGE-M3 · 운영 노드는 HWAXProd 길(CPU 노드 둘 · 공유 NFS), 계획이 부르는 스크립트는 `git log --all` 에 흔적 0) · ② 보류 유지(18대가 따로 온다면) · ③ HWAXProd 기준으로 Phase 0 ~ 1 을 다시 쓴다. ①이면 98 ~ 100 의 cae00 전환은 데이터 이관 D6 이 맡는다고 적는다. 88줄은 계획과 무관하게 B1 로 닫는다. |
| A2 | data-migration 52 · 53 · 54 · 55 · 57 ~ 61 | D5(박스 사이 동기화를 ssh · rsync 로, Drive 로 나가는 DB 덤프 age 암호화)를 어떻게 할까. | **① 보류 유지** — 운영 전환(10-31) 중이고 같은 병합 스크립트를 다른 갈래가 고친다(AIDataHub `6f496fa` · SignalForge `396af7c`), 암호화는 D5 와 함께(결정 18 — 먼저 암호화하면 cae00 병합이 개인키 없이 멈춘다) · ② 지금 착수(받은 편지함 backlog Q5 뒤 dev ↔ cae00 부터) · ③ 걷기(Drive 채널 그대로 · 평문 덤프 감수). 55 ⑤ · 59 의 MaterialTwin 크론(라이브 DB export · 소비자 없는 30분 번들)은 D5 와 무관하게 MaterialTwin 담당 몫이다(A4 와 같은 길). |
| A3 | data-migration 66 · 67 · 68 · 70 · 71 | D6(포털 스택을 새 운영 서버로 · cae00 → 시험 서버)을 어떻게 할까. | **① 보류 유지** — 포털 스택의 운영 서버가 정해지면 연다(결정 14, 10-31 의 HWAXProd 노드는 StepForge · DynaForge 만 받았다) · ② 걷기(운영은 앱 단위 HWAXProd 길) · ③ HWAXProd 운영 노드를 D6 의 prod 로 다시 쓴다. 다시 열면 70줄 '결정 4 마스킹' 은 결정 22 로, 71줄 RA 칸은 '사람별 RA 연결이 그 박스에서 산다' 로 고쳐 읽는다. |
| A4 | data-migration 45 | MaterialTwin 이관 잔여(`.agent_work` 485M 가 리포 안 · source.local_path 19행 · `.pre-*` 작업 사본 31개 2.4G)를 누가 할까. | **① MaterialTwin 담당 세션에 넘긴다**(10-17 X1 ~ X3 '데이터 정리는 MaterialTwin 담당' 과 같은 길) · ② 포털 세션이 지금(목록을 보이고 확인 뒤 삭제 — 결정 17) · ③ 그대로 두고 걷는다(gitignore 라 stash 위험 없음). |
| A5 | design-risk-review 151 | E10 필드 · VOC · 문헌 근거의 남은 세 칸. | ① 제품코드가 여럿이면 — **(가) 첫 값만**(지금 · 호출 예산 그대로) / (나) 값마다 부르고 5줄을 나눔 / (다) 값마다 부르고 상한을 올림. ② taxonomy voc_map 시드 12행 — **(가) 기존 38코드에 사상**(지표 계열이 안 갈린다) / (나) 없는 3코드를 마이너 승급으로 신설. ③ evidence_profile.field — **(가) 코드가 센 값만 싣고 대조하지 않음**(기존 의장 헤더가 header_mismatch 가 안 된다) / (나) 의장이 신고하는 6번째 키로 대조. 필드 · 문헌 7종 실호출은 cae00 실측 몫이다. |
| A6 | design-risk-review 161 | 라벨 자동 유입 4경로(RA incident · test_run · DynaForge · VOC)를 언제 지을까. | **(가) M4(RA 쓰기 · ADH 보내기)와 함께**(RA 실데이터는 cae00 에만 · dev RA 는 내려가 있다 · VOC 길은 A5 ② 가 먼저) / (나) 지금 dev 에서 가짜 RA · VOC 로 먼저. |
| A7 | risk-review-redesign 197 | 종합 보고서를 RA 에 저장하는 문을 언제 지을까. | **(가) M3 실주행(184행) 뒤** — 실제 종합 보고서가 아직 없고 RK-01 보내는 쪽과 같은 파일(`ra_client.py`)이다 / (나) 지금 — 사람 이름 · 공개 과제만 · 포털이나 에이전트 서버에 문 하나. RA 리포는 건드리지 않는다(게이트웨이 `create_report_draft` 길). |
| A8 | risk-review-redesign 198 | M4 잔여 다섯(지표 · 쟁점 패널 자동 재개 · AIDataHub `get_agent_cards` · 밤 창 · 기본값 켬). | **(가) 밤 창 · `get_agent_cards` 는 걷고 나머지 셋은 181 · 184행 뒤로**(카드는 `/card-review/pack` 하나로 받는다 — `get_agent_cards` 는 9만 자 응답을 집는 위험, problems P-12) / (나) 다섯 다 M4 로 둔다. |
| A9 | deliberation-quality 92 · 93 | '판정 불가' 과반이면 결정문 결론부를 측정 계획으로 바꾸는 갈래(두 엔진에 없다)를 어떻게 할까. | **(가) T7 한 줄로 T-서열 끝(T6 뒤)에 남기고 지금은 짓지 않는다** / (나) 걷는다 — 근거 0 이면 [가설 단계](F2)가 붙고 MCP 수렴은 이미 '판정 불가 — 다음에 측정할 것' 을 받는다. 93줄은 같은 답을 따른다. |
| A10 | chat-llm-stcx 11 | C7(Qwen 1M — server-setup 9절)을 11-14 전 rolling 때 같이 할까. | **(가) rolling 만 하고 9절은 GLM 풀이 다 1M 일 때로** — 챗 턴 창 = min(챗 서버, GLM)이라 지금 올려도 26만 → 약 30만에 그친다 / (나) 10-18 결정대로 rolling 때 같이. |
| A11 | procedures 441 | 제출 씨앗의 '과제 목록 단계'(예약 단계는 `9ce09b6` 로 섰다). | **(A) 걷음 — project 는 자유 입력 그대로, 정본 잇기는 DynaForge 가 반입 뒤 SP 과제로** / (B) 제출 앞에 `list_tasks` 단계 + select — SP 받기가 꺼진 박스(dev · 지금 cae00)에서는 0건이라 씨앗이 멈춘다. |
| A12 | procedures 548 | 워피지 다리(환원 도구 0 · 산식 미정). | **(A) 보류** — 대상 모델이 합성 데이터 데모라 다리를 지어도 판정 근거가 못 된다, 실모델과 `get_copper_result` 성공 표본이 생기면 다시 / (B) 소비 앱에 워피지 환원 도구를 짓는다(두께 · 대각은 odb-hub 값, 동박율 · 비대칭 산식은 표본 뒤). |
| A13 | procedures 580 · 588 | 과제 키 레지스트리(PLAN §7 #8)를 어떻게 할까. | **(A) SP 과제 키를 앱 사이 정본으로** — 따로 짓지 않고 SP 받기(core:read 토큰)가 켜진 뒤 안 받는 앱(HWAXRisk · ThermalShock)에 SP 키를 받게 요청 / (B) HWAXRisk rr_projects 확장(원안) / (C) 포털 새 레지스트리. 먼저 볼 것 — cae00 `/procedures-api/stats`(받은 편지함 backlog Q17)로 §6-1 쓸모 판정, 미달이면 PLAN 규칙대로 S5 이후 보류. 588 은 (A) 면 걷음. |
| A14 | procedures 604 | 절차를 게이트웨이 도구로 등록할까. | **(A) cae00 stats 로 §6-1 쓸모를 본 뒤 정한다**(FU-D3 그대로) / (B) 걷음 — 분석 루틴의 MCP 길(`routine_*`, 게이트웨이 `67d8d00`)이 자리를 맡았다 / (C) 지금 등록. |
| A15 | procedures 605 | 실행을 '챗으로 가져가기'. | **(A) §6-1 쓸모 판정 뒤로** / (B) 지금 — `kind='chat'` 대화로, 실행 단계 요약(인자 · 결과를 줄인 판)을 첫 메시지로(줄의 `kind='procedures'` 는 어느 탭에도 안 보인다 — LO-D2). |
| A16 | procedures 609 · 616 · 620 | 실행 → 심의 다리. | **(A) §6-1 쓸모 판정 뒤로** / (B) 짓는다 — 챗 핸드오프와 같은 통로(`delib_opts.evidence` · 40건 · 인자 1,200자), 의장은 사람이 고르고 risk-review 고정은 뺀다. 616 · 620 은 이 답을 따른다. |
| A17 | procedures 617 · leftovers-1017/PLAN 48 | 심의 방법에 8번째 카드 '리스크 심사' 를 둘까. | **(A) 두지 않는다 — 입구는 `/risk` · 리스크 앱 하나**(같은 일을 하는 길이 둘이면 원장에 안 쌓이는 단발 심사가 생긴다 — LO-D3) / (B) 단다 — JobId 에 risk-review(단발 템플릿, 원장 미연동). |
| A18 | procedures 622 | 사람 finding 의 mechanism · domain 을 risk_taxonomy 어휘로 서버가 검사할까. | **(A) HWAXRisk 가 검사 — 422 + 허용값, unclassified 허용**(오타가 묶음 열쇠를 쪼갠다 — HWAXRisk routes.py:5585) / (B) 그대로 두고 S8 다리가 설 때 포털이 저장 전에 대조. |
| A19 | doc-to-ra 9 | PLAN §12 남은 것(2 · 4 ~ 11). | **(A) 지금 박힌 기본값으로 정한다** — 2 DF-D17 · 6 PPTX · DOCX · XLSX + PDF(HWP · HWPX 없음) · 7 제목 1 마다 쪽 · 8 caption + rich_text(기본 끔) · 9 끔(선택) · 10 RA 자동 태깅(RA 쪽은 사람이 건넴) · 11 대체재 허락 유지, 4 · 5 는 cae00 금 표본 때 / (B) 항목별로 따로 정한다. |
| A20 | cluster-wiring 59 | stcx 잡의 소유자 — 게이트웨이가 smart-twin 계열에 사람 신원을 싣지 않는다. | **① 「나로 일단」 유지, KooSlurm SSO 를 켤 때 함께 정한다**(꺼진 동안은 어느 길이든 admin 하나로 뭉친다) · ② 그때 게이트웨이 사람별 위임(PER_USER_SSO_APPS — `7bcdf49` 준비됨)과 DynaForge 덱 업로드도 같은 신원 · ③ DynaForge 가 예약자 PAT 로 smarttwin_mcp 를 직접. |
| A21 | web-research 82 | RA 보고서 부록에 `queries_sent` 전문을 넣을까. | **① 걷는다** — 일반 웹을 접어 보안 검토가 닫혔고 전량은 egress 원장 · `list_egress_log` 에 남는다 · ② 넣는다(에이전트 서버가 모아 부록 절로 — dev). |
| A22 | web-research 102 · 103 · 104 | 40문항 벤치(공개기술 20 · 사내도메인 20)를 잴까. | **① 지금은 접는다** — 학술 검색만 남았고 cae00 망(P0 — 받은 편지함 backlog Q11)도 모른다, P0 가 '닿는다' 면 다시 · ② 잰다(라벨은 도메인 전문가 0.5일 · cae00 에서 웹 없는 기준선과 나란히). 103 · 104 는 102 의 하위 규칙이다. |
| A23 | mxwp-wiki 45 | 위키 워커 PAT 에 `plat:plmdefect` 를 줄까. | **① 준다** — MXWP Q8 권장안(PLM 결함 먼저 · 사례 단위 · 사람 정보 뗌 · 위키 범위가 `plat:plmdefect` 라 그 권한 있는 사람만 본다) · ② 주지 않는다(시장불량은 위키에 들이지 않는다). MX 백서 Q8 · W8(cae00)과 한 번에 정한다. |
| A24 | change-request-8-10/server-setup 484 · 485 · delib-engine-feedback 56 | 끊긴 웹 심의(포털 화면 · 리스크 패널)의 결과 회수 · 취소를 어떻게 할까. | (가) 잡 원장 위로 — job_id 로 다시 붙기 · 취소 · 이어하기가 MCP 와 같아진다(큰 판 — 엔진 · 포털 중계 · 화면 · 리스크 앱) / **(나) 취소만 — 도는 분리 심의를 대화 id 로 멈추는 엔진 창구와 화면 '멈춤'**(작은 판 — 지금 아픈 것은 멈출 길이 없는 것이고 숨은 탭 끊김은 request-1029 P-1 이 줄였다) / (다) 지금처럼. 485 는 (가)면 재개 전 엔진 잡 확인까지, (나) · (다)면 운영 안내로 남긴다. delib-engine-feedback 56 은 이 물음 · B34(마지막 신호) · B38(시간 제한 넷)이 닫힐 때 함께 닫는다. 재기동 뒤 이어 돌기(request-1027 HA-09)와는 다른 갈래다. |
| A25 | change-request-8-10/server-setup 489 | 심의 보호(새 심의 멈춤 → 도는 심의 끝 기다림)를 넓힐까. | **(가) 게이트웨이 · SignalForge 까지** — O1 기다림을 그 둘의 재기동 앞으로 당긴다(기다림 하나로 셋을 덮고 도는 좌석의 도구 호출이 끊기지 않는다) / (나) '심의가 없을 때 update-all' 운영 규칙 / (다) AIDataHub · KooRemapper · 자기치유까지 전부(배포가 몇 시간씩 밀릴 수 있다). |
| A26 | leftovers-1017/context-notes 38 | 패널 방식의 선례 인용 기록 넷(precedent_refs · precedent_clusters · prior_cites_n · cited_by_later — DDL 주석에만 있다)을 언제 지을까. | **(가) P5 측정 때 함께** — 쓰는 사람이 없고 동작 결함이 아니다 / (나) 지금 짓는다 / (다) 걷는다 — 재설계 뒤 패널 방식 P5 측정은 하지 않는다. |
| A27 | followups-1017/context-notes 39 | 예전 병합이 남긴 '운영이 더 새롭다' 건너뜀을 어떻게 할까. | (가) 그대로 — dev 에서 다시 바뀌면 풀린다 / **(나) 병합 끝 요약에 '운영이 더 새롭다는데 content_hash 가 다른 레코드 수' 한 줄**(읽기만 — AIDataHub, 다음 cae00 병합에서 크기를 본 뒤 정한다) / (다) 한 번 dev 값으로 강제로 덮는다(운영의 진짜 편집과 가를 수 없어 위험). |
| A28 | followups-1017/server-setup 274 | cae00 에도 서비스 감시(`HWAX_WATCHDOG=1`)를 켤까. | **(가) 켠다** — 다섯(포털 · 게이트웨이 · 에이전트 서버 · mxwp-mcp · searxng)이 죽었을 때만 다시 뜬다, 손으로 오래 내릴 때는 감시를 먼저 끈다 / (나) 끈 채 둔다. |
| A29 | improvement-1015 16 | 한국어 검색의 남은 견주기(재정렬기 · KURE-v1 · Kiwi · pg_bigm)를 할까. | **(가) 재정렬기만** — 이미 연결돼 있어(`AIDH_RERANK_PROVIDER=bge_m3`) 재색인 없이 사본 API 로 다시 잰다 / (나) 넷 다 / (다) 닫는다 — BGE-M3 로 충분하다. |
| A30 | ui-refresh 32 · 36 | 남은 원형 공사(PageState · EmptyState · Button · Field · Card · Badge · Banner · Table)를 할까. | **(가) 닫는다** — 있는 원형(Modal · Tabs · Menu · Page)으로 두고 나머지는 새 화면이 필요로 할 때 / (나) 마저 짓는다(화면 이행까지 1 ~ 2주). |
| A31 | ra-workspace 38(걷음 줄 — 판정 중에 나온 물음) | 공개 리포의 그 기록 줄에 데모 계정 메일이 그대로 있다. 기록은 고치지 않는 규칙과 부딪힌다. | **(가) 그 메일만 `<데모 계정>` 으로 가린다** — 공개 리포 규칙(메일을 적지 않는다)이 먼저다, 히스토리는 10-17 결정 1 대로 그대로 / (나) 둔다. |
| A32 | risk-credentials 55 · claude-delib-parity 25 · B33 ~ B36(판정 중에 나온 물음) | 리스크 앱 화면(HWAXRisk frontend — 마지막 커밋 10-07 `3e01d13`)에 화면 요청서 넷(m3 · risk-credentials · claude-delib-parity · ecad-1031)과 이번 화면 몫이 밀려 있다. 화면 세션을 다시 돌릴까. | **(가) 한 세션으로 묶어 돌린다** — 웹 '과제 만들기' 가 지금 늘 422 라 웹으로 과제를 못 만든다(B33) / (나) 결함 하나(B33)만 먼저 / (다) 미룬다. |

## 3. 표 B — dev 작업(47줄 → 작업 38)

받아들임은 그 작업을 닫는 기준이다. 다른 리포는 그 리포 세션의 몫이고(포털 세션은 요청서 · 시험 기준을 준다), Report Archive 는 고치지 않는다.

### 포털(HWAXPortal)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B1 | cluster-deploy 88 | `infra/scripts/drive-drift.sh` 의 heax 구역(build-all-to-drive.sh 끝에 부른다)에 '지어지지 않은 앱' 검사 — `integrations/<폴더>/.portal/manifest.yaml`(@{u} 판 우선)의 `launch.mode` 가 service · job_runner 인데 `var/sifs/<폴더>.sif` 가 없으면 `✗` 한 줄 · DRIFT=1, proxy · iframe · url · static 은 '○ SIF 대상 아님 N개' 로 명시 제외, `manifest.local.yaml` 이 있는 앱은 지금 규칙대로 ○. 지금은 dist-to-drive 의 글롭이 없는 SIF 를 싣지 않아 cae00 에 조용히 빠진다. | 새 시험(test_drive_drift_heax_keys.py 꼴 — SIF 없는 service 앱 → ✗ 한 줄 · rc 1, external_proxy 앱 → ○ 제외 줄, 다 있으면 새 ✗ 0) · dev 실주행 새 ✗ 0. A1 의 답과 무관하게 닫는다. |
| B2 | data-migration 9 | `docs/cluster-deploy/context-notes.md` 끝에 '2026-10-31 — 데이터 이관 계획이 바꾼 두 가지' 를 덧붙인다 — ① 토폴로지 개정(D6 뒤 cae00 → 시험 서버, 결정 13 · 14) ② `/data/svc/<svc>/`(비-HEAX sqlite · 블롭 자리 — dev 09-05 · cae00 `/data/svc/portal`). plan.md 는 고치지 않는다. | git diff 가 덧붙임뿐 · 9줄 체크. A1 이 ① 이면 그 닫는 기록과 한 항목. |
| B3 | procedures 128 | `backend/app/procedures/runner.py` 의 publish_report 단계 — ① 게이트 전에 preview_publish 로 대상 · audience · 못 올리는 사유를 게이트 카드에 ② 승인 뒤 다시 불러 같으면 그 토큰으로 곧바로 publish_report, 다르면 차이를 보이고 다시 멈춤 ③ 토큰은 원장 · 노트 · 승인 지문에 남기지 않는다. 지금은 confirm_token 을 넣을 길이 없어 게시 단계가 성공할 수 없다. 더 싼 대안 — 저장 때 publish_report 단계를 거절하고 'RA 화면에서 게시' 안내. | httpx.MockTransport 가짜 게이트웨이 시험 넷(카드에 미리보기 · 대상이 다르면 게시 0회 · 같으면 1회 · 원장에 토큰 0) + 기존 `*_token` save 거절 유지. 실물은 cae00. 쓰는 씨앗이 0이라 급하지 않다. |
| B4 | procedures 338 | bend_profile(StepForge core/bending.py:622) · stackup_profile · sed_sample_from_odb 의 응답 키를 PLAN §10-7 칸(대상 · primary · basis · notes · `*_check` · `for_*_analysis`)과 표로 맞대고, 둘 이상 맞으면 §10-7 을 규약으로 올린다(PLAN 고침 + context-notes 새 W 번호). | 표의 칸마다 파일:줄. 선택 — 씨앗 save 경로가 `for_*_analysis` 아래인지 보는 정적 시험. |
| B5 | procedures 339 | `docs/procedures/gaps/lamina-strength-fatigue.yaml`(kind ① · owner MaterialTwinWeb ↔ LaminateAnalyzerMCP · 실측 근거 — 물성 분류에 직교이방 라미나 강도 · ply S-N 이 없다) + MaterialTwinWeb 요청서('이미 되는 길이 있으면 알려 달라' 함께). | 장부 파일 · 요청서 커밋. 그때까지 R1 은 laminate 변수로 사람이 넣는다. |
| B6 | procedures 581 · 584 | 앱별 과제 키 · 시야 표 한 문서 — 키 꼴 · 소유 주체(사용자 위임 / 서비스 계정 — odb-hub 는 서비스 토큰) · 시야(DynaForge list_sessions · find_reports 는 '소유분 + 같은 소속 공유분' — KooRemapper platform/mcp_server/server.py:1264, HWAXRisk · StepForge · ThermalShock · RA 게시판 권한은 읽기만) · ODB 잡 메타의 과제 칸 · SP 과제 키를 받나. 조직 단위 모아 보기에 관리자 자격이나 별도 원장이 필요한 앱을 표시. | 칸마다 파일:줄 · A13 결정 표로 쓸 수 있다. |
| B7 | analysis-routines 31 | 각본 MCP 클라이언트로 포털 + 게이트웨이를 끝에서 끝 한 번(dev, 리포는 고치지 않는다) — initialize → routine_list → routine_get(dev-demo) → routine_run_start → 단계마다 routine_call(허용 도구만) · routine_step_done → routine_report_submit. 선행은 사용자 PAT 한 줄(dev 포털 `/auth/pat`) — 재기동은 이미 됐다. | 포털 원장 셋(routine_runs · routine_stages · routine_calls)에 실행 끝 · 호출 ok · 보고서, 게이트웨이 감사에 `corr routine:<실행>:<단계>`, 울타리 밖 도구 한 번은 거절. |
| B8 | upload 70 | `backend/tests/test_upload_form_in_browser.py` — test_chat_ppt_in_browser 틀(진짜 Composer · 가짜 fetch)로 StepForge 목적지 폼(새 과제 — 과제명 · 단계 · 특이사항 · 접힌 칸 / 기존 과제 — project_id 만, 담당자 안내에 로그인 이메일)을 눌러 POST /upload/dispatch 본문을 단언. | 시험 통과 + 필드 하나를 빼는 변이가 잡힌다. |
| B9 | thinking-mode 68 | test_delib_stream_in_browser 하네스에 띵킹 장면 — 'think' 프레임(roster 셋 → screen 탈락 → verdict answer · pass(refer) · error → answer 글 → summary)을 흘려 머리 줄 '1명 답변 · 1명 기권 · 1명 응답 실패' · refer 칩 · 답 글 · '진행 중' 사라짐을 단언. | 새 시험 통과 · 셈 갈래 하나를 바꾼 변이에서 실패. |
| B10 | chat-actions 20 | ui-check(임시 포털 · mock 로그인) e2e 에 단언 — 챗 · 심의 화면을 연 동안 `/knox-bridge/ui/actions.json` 요청 0, `/apps` 에 그 타일 없음(관리자 · 기본 두 층). A-12 뒤의 기대는 coming_soon 이 아니라 숨김이다. | 단언이 늘 돌고, 임시 routes 에 `knox-bridge=` 를 넣은 사본에서는 실패한다(되돌림 검사). |
| B11 | persona-chat 58 | test_delib_stream_in_browser 하네스로 — 전문가를 지정해 보낸 뒤 가짜 SSE 답 → 말풍선(이름 · 키 · 테두리 색) → 같은 대화를 서버 사본(가짜 GET)으로 다시 열어 말풍선이 남는지. | 새 시험 통과. |
| B12 | persona-chat 60 | **결함** — 전문가 색의 입력이 화면마다 갈린다(챗 말풍선 · 고르기 화면 · 입력창 알약은 이름 — MessageList.tsx:137 · :144 · :153, 회의록 · 관계도 · 띵킹은 키 — DelibView.tsx:119 · :196 · :205 · DelibGraph.tsx:63 · ThinkView.tsx:9-21). 같은 사람이 대개 다른 색으로 보인다. 입력을 키 하나로 맞추고 ThinkView 의 사본 colorOf 를 personaColor 로 합치며 personaColor.ts 의 주석을 고친다. | 소스 시험(전문가 아바타 · 테두리의 colorOf 인자가 키) · 화면 시험(같은 전문가의 챗 말풍선과 회의록 아바타 배경색이 같다). |
| B13 | ui-refresh 11 | ui-check 에 caeg 층 — 빈 임시 원장에 `SSO_DEFAULT_AFFILIATION=CAEG` 를 주고 띄우면 mock 사용자가 CAEG 로 들어온다(session.py:60-72 · :117-128). Windows 글꼴 캡처는 사람 몫이라 줄을 둘로 가른다. | `UI_TIERS='admin basic caeg'` 통과 · caeg 층의 `/apps` 타일이 기본 층보다 많다. |
| B14 | ui-refresh 15 | `frontend/src/styles/chatpage.css` 의 라이트 폴백 여섯(:1300 · :1311 · :1321 · :1340 · :1457)을 걷어 `var(--x)` 만 남긴다(변수는 다 정의돼 있다). | `var(--…, #fff · #f6f7f9 · #111)` 꼴 0 · `pnpm build` · ui-check '밝은 패널' 단언 통과. |
| B15 | ui-refresh 39 | 빌드에 hex 래칫 — tokens.css 밖 고유 hex 수(10-31 셈 92개 · 250곳, 목표 ≤ 20)를 세어 기준 파일보다 늘면 실패, 줄면 기준을 낮추라고 알린다. | 새 `#rrggbb` 하나를 넣은 사본에서 `pnpm build` 실패, 지금 트리는 통과. |

### 게이트웨이(HWAXMcpGateway)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B16 | followups-1017/requests 22 | ① `provision-config.sh` 의 kooremapper_mcp 위임에 `KOORM_SEND_PLAT`(1 이면 send_plat, 안 적으면 직전 값 이어받기 — 지금 `<접두>_SEND_PLAT` 는 PER_USER_SSO_APPS 앱에만, :808-816) ② 그 요청서 §2 의 MCP 문단을 서명 헤더 길(X-Heax-User-Plat · X-Heax-Plat-Proof)로 고쳐 KooRemapper 세션에 넘긴다(아직 넘어가지 않았다). | ① 시험이 `KOORM_SEND_PLAT=1` → `per_user_sso.kooremapper_mcp.send_plat` 참을 본다 ② (그쪽) 권한 없는 사람의 제출이 '권한 없음' 으로 막히고 잡 기록에 남는다. |

### 에이전트 서버(HWAXAgentServer)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B17 | deliberation-quality 42 | 원 이어하기를 dev 에이전트 서버에 한 번 다시 — 저널(journal.jsonl)에서 원 질문 · 이전 결론 · 원 humanNote · 원 6석을 꺼내 `/chat` 에 '/심의' + delib_opts{continue_personas · continue_summary · human_note · rescreen 1 · stop_after_round 1 · save_report 0}. 같은 꼴 회귀 시험 하나(가짜 recommend_agents — 유임 전원 · 착석 도메인 제외 · 상한 2). | personas 사건에 원 6석 그대로 · origin new 가운데 서비스 운영 · 필드 데이터 계열 ≥1. 결과는 42 · 43행에 날짜와 함께 적고 제품 이름은 적지 않는다. |
| B18 | deliberation-quality 77 · 78 | `tests/test_continue_seat_role.py` 의 _REAL_RUN(가짜 LLM) 하네스로 이어하기 한 번(유임 + 재심사 신규). 77 — 1라운드 신규 좌석 프롬프트에 이전 결론 표지가 없고 유임엔 있으며 2라운드는 둘 다 있다. 78 — 2라운드 교차심문 표적 원문 가운데 적어도 하나에 신규 좌석의 1라운드 입장이 실린다(_cross_targets 커버리지 보정). | 시험 통과 · prompt_fn 의 origin 조건을 뒤집는 변이 · 커버리지 보정을 끄는 변이가 잡힌다. 쟁점 · 소수의견으로 남는지는 T1 cae00 실행 때 같이 읽는다. |
| B19 | web-research 81 | `deliberation.py` — 웹 리서치 3상태 봉투의 `data.status` 가 blocked · empty(또는 degraded 인데 results 0)면 근거로 세지 않는다(:5320-5321 · :6012-6013 — 지금은 envelope_failed 가 맨 위 status 만 봐 ev_count tool 이 오른다). | 그런 봉투뿐인 심의의 근거 프로파일에 '가설 단계' · 의장 지시에 [가설 단계] · 판정을 빼는 변이에서 실패 · 에이전트 전체 시험 · 포털 test_delib_opts_contract 통과, dev 재기동은 사용자 확인 뒤. |

### 웹 리서치(WebResearchMCP)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B20 | web-research 71 | `app/net.py` 의 `_throttle` 을 호스트별 `threading.Lock` 으로 묶는다(읽기 → 기다림 → 기록) — `80b1452` 뒤 도구가 스레드에서 돌아 동시 호출 둘이 같은 순간 나간다. 토큰버킷 3중 · 일일 쿼터는 일반 웹을 접어(결정 9) 범위에서 뺀다고 줄에 적는다. | 스레드 둘이 같은 호스트로 동시에 부르면 나감 시각 차 ≥ 간격(시험 간격 0.2초) · 잠금을 빼는 변이에서 실패 · 전체 시험 · push. |
| B21 | web-research 72 | `tests/test_egress.py` 에 서킷 시험 — 연결 실패 다섯 번 뒤 여섯째 egress 가 소켓 connect 0건(test_offline_opens_no_socket 의 후킹) · status blocked · '연속 실패로 차단', 쿨다운(작게) 뒤 다시 연다. | 시험 통과 · :196 서킷 검사를 빼는 변이에서 실패 · push(`ss -tn` 실측은 이 시험이 갈음한다). |

### 리스크 앱 백엔드(HWAXRisk)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B22 | design-risk-review 104 ② | POST `/projects/{id}/sources` 응답에 `duplicate_of[{project_id, code, owner_sub, created_at}]`(plan §8.2.3 — 막지 않고 알린다). 지금은 risk_store.py:86 주석뿐이다. | 같은 원천을 두 과제에 붙이면 duplicate_of 1건 · pytest. |
| B23 | design-risk-review 106 ① ~ ③ | brief E0 에 '요구 dim_limit n · 최소 여유 … · 시나리오 a/b' 또는 '요구 미등록' 한 줄 · E3 에 limit · margin 두 열과 margin 오름차순('미측정' 은 0 이 아니다) · 원자 저장 때 margin ≤0 인데 judgement OK 면 undetermined 로 보정. | 시험(요구 0건 E0 · margin 손계산 · 보정) · 변이. |
| B24 | design-risk-review 108 | sameas 6단계 전에 `len(rest_a) × len(rest_b) > 800 × 800` 이면 배정을 건너뛰고 degraded · warnings `fuzzy_skipped_large` · `sig:capture.fuzzy_skipped` · 쌍 caveat(plan.md:925) — 지금 sameas.py:593-629 는 크기와 무관하게 행렬을 짓는다. | 801 × 801 합성에서 건너뜀 · 표지 · ir_hash 결정론 · 799 × 799 는 그대로 · pytest. |
| B25 | design-risk-review 125 | 캡처가 kind 별 잘린 수(`stats.interfaces_truncated{kind:n}`)를 남기고, 쌍의 한쪽이라도 잘린 kind 의 엣지 · 파라메트릭 변경에 `excluded_reason='truncated'` 를 달아 의미 이벤트를 만들지 않는다(plan.md:835 · :1614) — 지금은 5,000행에서 잘린 쪽이 '간섭이 사라졌다' 는 가짜 사건을 낼 수 있다. | 한쪽만 잘린 합성 쌍에서 그 kind 의 removed 사건 0 · 항목은 diff_json 에 남음 · 변이 · pytest. |
| B26 | design-risk-review 126 | 노드 500 · 엣지 2,000 합성 쌍으로 `diff.compute_diff` < 5 s 단언과 tracemalloc 피크 기록(§10 #27). | 시험 하나 · 수치를 context-notes 에(피크 > 1.5 GB 면 매니페스트 memory_gb 3). |
| B27 | design-risk-review 132 · 152 | planner — 로스터를 얼릴 때 role_sha(원본 role 의 sha256[:12]) · persona_rev 를 채운다(지금 planner.py:180 · :232 가 두 칸을 빼 nightly 스탬프와 rr_seat_opinions.persona_rev 가 늘 NULL). 그 뒤 brief E7 이 회수한 좌석 의견의 persona_rev 가 지금 로스터와 다르면 '[이전 정의]' 접두(plan §5.6.1). | 새 로스터 행에 두 칸 · nightly 스탬프에 persona_rev · 판이 다른 의견 하나가 접두로 실리는 시험 · 변이. |
| B28 | design-risk-review 134 | MCP 길(미검증 actor) 패널의 원자를 회수로 되돌리는 길 — PUT `/curation/{id}` decision `approve_recall`(또는 큐 종류 recall_review) → recall_eligible=1 + rr_audit(`recall.approve`). 카드 대조 finding 은 종전대로 올리지 않는다. | P3 (21) 시험(MCP 산출 0 · 웹 1 · 승인 뒤 1 · 다른 열 바이트 동일). 쓰는 사람이 적은 길이라 급하지 않다. |
| B29 | design-risk-review 135 | rekey — 확정을 뒤집는 네 조작(same-as reject · unmerge_key · iface-ledger rejected · 계면 별칭 revoke)이 한 트랜잭션에서 plan.md:3339-3346 의 여섯 걸음(prev_status 기록 → finding subject_key 재계산 → 별칭 append/revoke → registry.merge → priors 재합산 · 무효 큐 닫기 → rr_audit `rekey`). 지금은 확정을 뒤집어도 합쳐진 등록부 행이 남는다. | `test_rekey.py`(확정 → reject 왕복에 등록부 support · priors 복귀 · 옛 reg: dangling 0 · 6홉 409) · 변이. 큰 일이다. |
| B30 | design-risk-review 136 | GET `/targets/{key}/audit`(?action · since · limit ≤200, 그 대상의 rr_audit 행, 비멤버 403) — 지금은 과제 단위 `/projects/{id}/audit` 만 있다(routes.py:1391). | 시험(멤버 200 · 비멤버 403 · 거름). 작은 일이다. |
| B31 | design-risk-review 143 ① ② | JobBody 에 `exclude_evidence[]` → params_json · 그 잡 패널 브리프에서 빼고 rr_panels.evidence_excluded_json · rr_audit(`brief.exclude`)(지금은 조용히 버려진다 — routes.py:3159-3186) · 통합 보고서 minutes 에 '사람 개입 요약'(rr_audit 건수와 같게). | P4 통과 (13) 시험. |
| B32 | risk-200k 7 | 읽기 전용 측정 스크립트(HWAXRisk backend/scripts 또는 포털 scripts) — 리스크 명단(list_agents 와 같은 풀) 전원의 카드를 AIDataHub `/api/agents/{agent}/records` 로 읽어 엔진 normalize_card · assign_aliases 로 펴고 limits() · plan() 식으로 1M · 20만의 한 장 자리 초과 카드 · 그런 전문가 · 입력 결손 몫 초과 · 셀당 판정 호출 어림을 JSON 으로. | dev 표본(시드 20261020)에서 W-D2 수치 재현(143장 · 19/32 · 31/32) · 명단 전원 결과를 context-notes W-D 로, 그 뒤 cae00 에서 한 번(사람). |

### 리스크 앱 화면(HWAXRisk frontend — 화면 세션, A32)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B33 | design-risk-review 104 ① | **결함** — 웹 '과제 만들기' 가 등급(classification)을 보내지 않아 서버가 늘 422 `classification_required` 로 거절한다(frontend RiskHomePage.tsx:131-137 · backend routes.py:861). 폼에 등급(internal · confidential)을 둔다. MCP `risk_create_project` 는 받는다. | 웹에서 과제 만들기 200 · `tsc -b && vite build`. |
| B34 | design-risk-review 104 ③ · 105 · 106 ④ · 107 · 111 · 113 · 114 · 143 ③ · 149 · leftovers-1017/context-notes 40 · change-request-8-10/server-setup 486 | 화면 몫 묶음(요청서 하나 — m3-frontend-request 에 한 절) — 등급 · lifecycle · 역할 칩과 필터, 멤버 · 이력 탭 · 이양 · 폐기 · GateBanner ack(104) · '조직 공개' 토글(105) · 제품 다중 선택 · '제품 연결 없음' 배지 · 여유 표(106) · '파서 세대 다름' 배지(107) · Gate.pass null 을 중립색 '판정 불가'(111) · RuleHit 평가 불가(113) · mcad 소스 카드의 상시 격리 경고(114 · LO-D6) · TargetPage 의 틀린 문구 걷기와 좌석 되돌리기 · skipped 사유 폼(143) · 키 병합 · 이름 · 되돌리기 폼(149) · 일꾼별 '마지막 신호 N초 전'(486 — 80초를 넘을 때만 강조). | 줄마다 — `tsc -b && vite build` · mcp_degraded 스냅샷의 G3 · G4 가 fail 로 안 보인다 · R-004 · R-005 가 평가 불가 · 판이 다른 두 스냅샷 비교에 배지 · editor 에게 토글이 잠긴다 · 도는 패널과 멈춘 패널이 갈린다. |
| B35 | risk-credentials 55 | `docs/risk-credentials/frontend-request.md` 대로 — 로그인 뒤 `auto.enabled && due` 면 조용히 한 번 발급 · 등록(source web) · 발급 청중 [mcp-gateway, step-forge](손 버튼도) · 끄기 스위치 · last_error · how_to_stop 표시(지금 api/portalPat.ts:26 청중이 mcp-gateway 하나). | `tsc -b && vite build` · PAT 없는 상태로 설정 화면을 열면 한 번 등록된다. |
| B36 | claude-delib-parity 25 | 패널 잡 만들기(Tier A · B · C)에 판단 LLM 선택(GLM 기본 · Claude) — Claude 면 반출 경고와 동의 체크(미리 체크하지 않는다), 체크했을 때만 llm 'claude' · consent_external true, 422 · 409 문구, hwax-risk-claude 안내, 진행판 'Claude' 배지(frontend-request.md 1절). | tsc · vite build · 브라우저 시험(체크 전 본문에 consent_external 없음 · GLM 잡 본문은 종전 그대로). |

### 다른 앱(요청서 — 그 리포 세션)

| # | 줄 | 할 일 | 받아들임 |
|---|---|---|---|
| B37 | procedures 329 | 절차 씨앗이 쓰는 도구부터 인자 description(값 종류 · 단위 · 범위 — 리스크 앱 `ae4af1d` 꼴) — LaminateAnalyzerMCP(analyze_laminate · solve_prescribed_curvature · recover_ply_stresses · estimate_fatigue_life) · StepForge(bend_profile · find_parts · stackup_profile) · KooRemapper(find_reports · report_summary · report_part_risk · report_directional · report_part_series · report_findings · create_session · run_operation) · ThermalShockMCP(sed_sample_from_odb · predict_sed). 10-31 dev 인자 2,053 중 설명 230(11.2%). | SIF 교체 뒤 dev `/tools-map` 의 arg_scores 에서 그 도구들 described == args. |
| B38 | change-request-8-10/server-setup 488 | 시간 제한 넷의 요청서 둘 — ① KooRemapper: MCP → REST 한도 60초(platform/mcp_server/server.py 일곱 곳)를 게이트웨이 도구 호출 600초 안쪽 값으로 · 전처리 잡 벽시계 1800초를 설정 손잡이로 ② HEAXHub: forward_auth 에 짧은 연결 · 응답 한도 · 생사 탐침은 연달아 여러 번 놓쳤을 때만 다시 띄운다(integration_launcher.py:92 · :654-661 · :791-801). HEAXHub 는 운영 전환(그쪽 2026-10-31 문서) 판 뒤에 넘긴다. | 60초 넘는 DynaForge 호출이 게이트웨이 한도 안에서 끝난다 · 탐침을 한 번 놓쳐도 앱 서버가 둘이 되지 않는다. |

## 4. 표 C — cae00 · 바깥(140줄)

### C-1. 받은 편지함 물음(39줄 → [2026-10-31-backlog](../cae00-inbox/2026-10-31-backlog.md) Q1 ~ Q20)

읽기만 하는 물음과 바깥 팀에 넘길 물음이다. 답은 리포가 아니라 사용자를 거쳐 온다.

| Q | 줄 | 무엇 |
|---|---|---|
| Q1 | design-risk-review 24 · 32 · followups-1017/context-notes 14 | 리스크 앱 원장 표 셋의 행 · 원문 바이트 · 30일 증가와 DB 크기, mcad 스냅샷의 리프 · 계면 최대와 상위 5% — (34) 보존 정책과 (39) 모델 상한의 사실. 계면 상한 6,000 이 REST 한 번의 5,000 보다 커서 그 사이 모델이 잘리므로 답이 오면 5,000 으로 맞추기를 권한다. |
| Q2 | risk-review-redesign 20 · 183 · risk-200k 8 · followups-1017/server-setup 150 | 리스크 앱 판 · 스키마 · 이행 사본 · 도구 수 · 동시 수 · 대상 · 변경 비교 수 · units_probe 줄(단위 크기 어림) · cred_key_source · `/api/health` 경고. |
| Q3 | chat-depth-context 55 · 67 · chat-vision 6 | 에이전트 서버 `/health`(chat_llm 넘김 · tool_cut · vision · seat_vision)와 그림 탐침. 챗 두 턴 비교 · 그림 올려 보기는 사람 걸음이다(Q3 에 적었다). |
| Q4 | chat-llm-stcx 13 | update-all 의 1g2 줄 · DocForge capabilities 의 vlm.source. |
| Q5 | data-migration 31 | `services.sh data --check` 의 끝 줄 · rc — D5 를 열려면 먼저다(A2). |
| Q6 | procedures 23 · 531 · sso-delegation 26 | 게이트웨이 `/tools-map` · `/health` — odb-hub 항목 · 열충격 12종 · testscope 가 붙었나. |
| Q7 | design-risk-review 89 · procedures 501 | DynaForge — 그 사람 PAT 의 list_sessions 수 · report_corpus 수. |
| Q8 | procedures 526 · 534 | ODB 허브 실물 — board_type 분포 · pad `r<N>` 값. |
| Q9 | cluster-wiring 29 | nginx `/ste/` 의 업로드 두 줄(이 박스) · stcx 앞단(stcx 운영). |
| Q10 | ste-cae00 53 · ra-reconnect 29 | ste-doctor 의 teleport · tunnel-cfg · tls · https 행. |
| Q11 | web-research 9 · 10 | check-egress(`--json` · `--sif`) — 학술 API 망 실측(P0). |
| Q12 | access-control 46 · change-request-7 6 · change-request-8-10/context-notes 11 · 90 | 소속 빈 사람 수 · 리스크 앱 포털 PAT 주인의 소속 · SAML 메타데이터의 SLO · 사번 Claim · 사번 빈 SSO 활성 행 수. |
| Q13 | change-request-8-10/server-setup 490 | ARP 로그아웃 주소가 내는 숫자. |
| Q14 | followups-1017/checklist 44 | 묶음 B — read_tools 경고 줄 · 허브 앱을 포털 토큰으로 · 같은 소속 심의(8-4 는 request-1029 E-9 이 대신한다). |
| Q15 | followups-1017/checklist 46 · ra-reconnect 27 | 옛 stash 수 · PG 시한 · 데이터허브 바인드 · 옛 RA 포트(리스크 백업 경고는 Q2, RA 쪽 넷은 C-4). |
| Q16 | chat-actions 24 | 챗 액션 사이드카 매니페스트의 상태 · 형식. |
| Q17 | procedures 245(+ A13 ~ A16 의 '먼저 볼 것') | `/procedures` 화면 · `/procedures-api/stats`. |
| Q18 | change-request-8-10/context-notes 37 · server-setup 491 | (바깥 — ODB 허브 담당) 포털 JWKS 로 jwt-handoff 를 받게 켰나. |
| Q19 | procedures 532 | (바깥 — 모델 담당) 학습 데이터 PKG_X · PKG_Y 의 축. |
| Q20 | sso-delegation 27 · 38 | (바깥 — TestScope 운영, 쓸 때만) 판 · 허용 호스트 · 방화벽. |

### C-2. 사람 걸음(64줄 — 박스를 바꾸거나 일을 돌린다, 절차 문서대로)

| 줄 | 어디서 · 누가 | 걸음 · 절차 |
|---|---|---|
| design-risk-review 86 · 88 | cae00 · 사용자 | 포털 챗 `/심의` chairTemplate risk-review 단발 3회(파싱 ≥2/3 · 지정 반대석 origin adversary 3/3 · personas origin 보존 3/3 · extra_seats 빈 것 3/3) · `apps=[heax-kooremapper_mcp]` 로 한 번 더(sim 좌석 report_part_risk · rel 좌석 search_objects 실호출 SSE ≥1 — RA 는 읽기만). 결과는 design-risk-review context-notes 에. 단발 리스크 심의를 쓰지 않을 거면 두 줄은 걷어도 된다. |
| design-risk-review 117 · 118 | dev(사용자) · cae00 | B2 dev StepForge 골든 SIF-E2E 재파싱 · 재검출 → 그 뒤 dev 가 골든 IR 시험(노드 3 · 엣지 2 · ir_hash 결정론 · world_center ±0.01mm) · B4 실무 규모 STEP 1건 업로드(사람이 고른다) · B5 DynaForge 세션 · K파일 · 리포트 각 1건(그 사람 PAT 로 캡처). 500파트 캡처 ≤10 s 시험은 dev 가 가짜 소스로 먼저 할 수 있다. |
| design-risk-review 138 · 144 · 156 | cae00 · 사용자 | 재설계 단계 E(M3 전원 실주행 — risk-review-redesign 184) 때 Tier 패널 품질 표지(low_tool_use · low_ir_cite) · SSE 귀속 · Tier B 벽시계 · 동시 슬롯 · 일일 상한 · 도는 중 재기동 뒤 이어 돌기 · rel 좌석 get_top_issues 실호출 · 계보 없는 과제 회수를 본다. registry 자유 조회 항은 D-18 로 걷히고 agent_search 재현은 M4 뒤다. |
| risk-200k 57 | cae00 · 사람 | `docs/risk-200k/server-setup.md` 4절 A/B(임시 에이전트 서버 `LLM_CONTEXT_TOKENS=200000` · PID 로만 내린다) — 셀마다 걸림 카드 집합 일치율(G3 초안 95% — 사용자에게 다시 묻는다) · 판정 · 훑기 · 카드 밖 호출 수 · 잡 시간 · [누락 0 증명] 줄. 32 · 33 · 43 · 58 줄의 수를 같은 때 센다. |
| risk-credentials 46 · 48 | dev 또는 cae00 · 사람 | 포털 토큰 화면에서 PAT 를 새로 낸다(기본 청중에 step-forge · mcp-gateway) → 그 PAT 로 Claude(hwax MCP)에서 risk_next_step → 토큰 목록에 hwax-risk 하나 · 앞선 것 폐기 · GET `/api/me` 의 portal_pat.auto.last_source 가 gateway-exchange → 같은 PAT 로 위임 캡처 → capture_rest 가 `/tree` 를 읽고 G6 이 unit_unknown 이 아니다. |
| risk-review-redesign 179 | cae00 · 사람(심의 · 카드 대조가 없을 때) | server-setup-m0b.md 2 ~ 3절 + server-setup-m3.md 3절(`--extra all`) — GLM 서버마다 그 주소만 담은 env 파일을 `--env-file` 로 주어 따로 잰다. 로그 끝 'M0-b 탐침 요약' 블록을 dev 에. |
| risk-review-redesign 180 · 67 | cae00 · 사용자와 | 대상이 없으면(재고는 Q2) 실제 과제 하나의 리비전 둘로 Claude 에서 risk_next_step → create_project → add_source → capture_snapshot 두 번 → create_diff → open_target(캡처하는 사람의 PAT 청중 step-forge 를 먼저 본다). target_key 를 dev 에. 그 대상에서 Tier A 대표 세 패널이 done 인지(67). 이 줄이 20 · 67 · 181 · 184 와 risk-200k W5 를 막는다. |
| risk-review-redesign 181 · 184 · 185 · 186 | cae00 · 사용자 | 180 · 183 뒤 server-setup-m3.md 4절(대표 9명 파일럿) · 5절(전원 실주행 — 동의 한 번 · ttft 탐침을 켠 채 · 도는 중 update-all 한 번) · 6절(쟁점 패널 상한 · 종합 보고서 · 막음 잔여) · 사용자가 종합 보고서를 읽는다. 수치는 dev 가 PLAN 6절에 적는다. |
| deliberation-quality 114 | cae00 · 사람(심의가 한가한 때) | `docs/followups-1017/server-setup.md` 7절 — T1 evidence_prepass A/B(`--repeat 3`) → 판정 → 이 줄에 날짜 · 판정 · summary 요약(결정문 원문은 옮기지 않는다). |
| chat-ppt 29 · doc-deliberate 6 · 14 · token-bat 14 · 22 | Windows PC · 사람 | 한 번의 Windows 실시험으로 — 설치 배치(HKCU) · 단추 · DRM 문서 하나 · 슬라이드 그림 · 취소 · 만료(10분) · 남이 낸 표 링크('아니오') · Office 버전과 Word 로 PDF 열기 · 추출 20번 잇달아 뒤 WINWORD · POWERPNT 0개 · 토큰 배치(Store 판 · NO_PROXY/no_proxy 함께 · 토큰 재발급 뒤 손 설정 유지 · Desktop 켠 채) · 인증서 받기 ② · ③(OK HTTP 200). 단계마다 됨 · 안 됨과 화면 문구만 돌려준다. |
| procedures 237 · 242 · 243 · 270 · 601 · 633 | dev(또는 cae00) 브라우저 · 사람 | 한 번의 브라우저 세션 — 로그인 → 절차 → R1 씨앗(U자 판 반입은 됐다) → '예제 값 모두 넣기' → 재생 → ⑦ create_report_draft 게이트에서 멈추나(dev 에서는 승인하지 않는다) · r_unfold 만 바꿔 재생(층별 응력 · 수명이 달라지나 — 줄의 bend_radius 는 이제 r_unfold 로 읽는다) · 도는 동안 다른 탭 챗 한 턴(429 없이) · 챗에서 SED 조건 다섯 → 원장에 predict_sed 다섯 줄이 각자 다른 인자 · 결과. 절차 라우트는 세션 쿠키만 받아 에이전트가 대신 못 돈다. |
| procedures 546 | cae00 · 사람 | 씨앗 thermal-shock-sed.yaml 을 실제 보드 하나로 끝까지(환원 → predict_sed). context-notes 에는 '토큰 주인 시야' 가 아니라 '서비스 토큰 · 접근 통제는 게이트웨이 plat:odbhub 하나' 로 적는다. |
| procedures 488 | cae00 · 사람 → dev | 첫 실제 전각도 · 부분충격 잡(cluster-wiring 96) 뒤 그 리포트로 find_reports · report_* 응답을 받아 dev 가 합성 고정물을 바꾼다(사내 값 · 과제명은 지우기 게이트). 헤드 /opt · 노드 SIF 가 v127 인지 먼저 본다. 코퍼스 수는 Q7. |
| cluster-wiring 96 | cae00 · 사람 | 운영의 첫 실제 전각도 잡 하나를 DynaForge(포털 R2a 씨앗)로 걸고 cae00-deploy-guide 「2026-10-30 반영분 — 낙하 트윈」 §4 — sacct COMPLETED 0:0 · return_manifest ok · postprocess succeeded · report_ids · external_job_key = `stcx:<잡 id>`. |
| doc-to-ra 18 · 42 · 67 | cae00 · 사람 | `docs/doc-to-ra/server-setup.md` §1 ~ §6(HEAXHub/.env 한 줄 · models-from-drive `HEAX_MODEL_APPS=doc_forge` · update-all → /health · 뼈대 잡) 뒤 dev · cae00 에서 PPTX 한 장을 정밀 변환 → 배달 → 알림. |
| doc-to-ra 21 · 22 · 23 · 25 · 26 · 43 | cae00 · 사람 | 금 표본(실문서 40 + DRM 5 — DocForge 개발 데이터 폴더, 리포 밖) → truth.py 정답 · 기준선(RA 가져오기 · AIDH convert_file — RA 는 부르기만) · check-cae00-env.sh 길 A/B · measure_docling · compare_parsers · probe_structured(GLM · Qwen 준수율 ≥99%) · probe_vlm · beta 배치 승인(DocForge 세션) 뒤 금 PPTX 지표. 차례는 `docs/doc-to-ra/cae00-handoff.md`. |
| doc-to-ra 29 | 사람 | SP 허브 주소 · core:read 토큰(StepForge 와 같은 미결 — cae00-deploy-guide §9) → 받은 뒤 cae00 에서 실 과제코드 · 모델명 꼴로 거울 시험. |
| analysis-routines 53 | cae00 · 사람 | update-all 뒤 examples/market-defect.yaml 루틴 한 번 — 단계별 토큰 · 시간 · 캐시 적중 · 커버리지를 10-29 기준선과(analysis-routines server-setup R5). |
| upload 69 | dev 챗 · 사람 | STEP 둘 든 zip 을 새 과제로 한 번 · 기존 과제로 한 번 → 파싱 잡 done · 파트 수, 시험 과제는 회수. |
| ste-cae00 33 · ste-fullangle 21 · 22 · 23 | cae00 · 사람 | `./infra/scripts/update-all.sh --with-ste`(SmartTwinExplorer 번들 `4f5e0e0` 반영 — request-1030 server-setup.md:74) → ste-doctor 전부 초록 · 다음 평소 update-all 이 ste 를 건드리지 않음 → ste list_apps 에 fullangle-drop → `ste_submit_job(preflight)` → preflight.json 전부 ✓ 이면 angles=2 실주행 · fullangle_verdict.json. |
| sso-delegation 39 | cae00 · 사람(TestScope 를 쓸 때만) | server-setup.md B2 ~ B5 · (고르면) B-2 · NO_PROXY 에 TestScope 호스트 · update-all. Q6 · Q20 뒤. |
| web-research 80 | cae00 · 사람 | Q11 로 학술 API 가 닿는 것을 본 뒤 학술 소스를 켠 심의 10건 — 결정문의 `[W:…]` 인용 수와 web_cite_unverified 경고 수(목표 0). |
| mxwp-wiki 14 · 27 · 40 | dev 브라우저 · 사람 | 소속이 있는 그 계정으로 포털 타일 → MX 백서 한 번(MX 백서 쪽이 소속 저장 확인) · 포털 챗 '위키에 남기기' 실클릭 · '내 후보' 하나를 aff:CAEG 로 승인. |
| mxwp-wiki 33 | cae00 · 사람 | `python3 infra/scripts/sync-he-personas.py` 미리보기 → `--apply`(request-1030 HP-53 과 같은 걸음). |
| mxwp-wiki 41 · 44 | cae00 · 사람 | MX 백서 리포 `python -m app.scripts.sso_only_check`(읽기 — 계정 목록이라 사용자에게만) 뒤 MXWP_SSO_ONLY 켜고 재기동 · 위임 비밀 하나 → 게이트웨이 provision.env 넷 · MXWP .env · update-all('✓ mx-white-paper 사람별 위임' · 비밀 대조 204) · 타일 로그인(mxwp-wiki PLAN §6). |
| followups-1017/checklist 45 | stcx · 사람 | 11-14 전 rolling — 현 라운드 OB-01 ~ 03 이 맡는다(A10 과 함께). |
| chat-actions 28 · 29 | cae00 · 사람(Q16 이 200 · JSON 일 때만) | routes.local.env 에 `knox-bridge=<사이드카>` → update-forges.sh portal → `/apps` 타일 · CAEG 계정 툴바 버튼 · 기본 계정 매니페스트 요청 0 · tools/list 에 bridge 도구 0. |
| improvement-1015 8 · 18 | cae00 · 사람(켤 때) | 상태판 — infra/.env `STATUS_BOARD=1` · `STATUS_ALERT_TO` · 포털 SMTP → update-all(5b) · 호출 추적 — `CALL_TRACE=1` → update-all(5c) → 에이전트 서버 `CALL_TRACE_URL` → 심의 없을 때 재기동. |
| improvement-1015 13 | cae00 · 사람 | 게이트웨이 리포에서 `tool_search_eval/run.py` snapshot · eval(박스 파일을 쓰므로 읽기 물음이 아니다) → 부분문자열 대 RRF hit@1 · hit@5 · MRR → 켤지와 k 는 사용자가 정한다. |
| llm-pool 12 | cae00 · 사람(심의 없는 때) | `docs/llm-pool/capacity.md` 2 ~ 8절 · 8절 표에 한 줄 · 세 손잡이는 server-setup.md 5절. followups-1017 FU-D3 '카드 대조 동시 수' 가 이 수를 기다린다. |
| request-1015 10 | cae00 · 사람 | 남은 넷 — KooRemapper → 허브 동기화 재개(K6-4) · K6-1(나) · K6-2(가) 정리가 운영 DB 에 들었나 · sim-drop-impact data_types · kc_sweep 다시 돌린 결과. 나머지 셋(OB-34 · OB-89 · HP-53)은 현 라운드에서 닫는다. |

### C-3. 차례 대기(28줄 — 앞 걸음이 끝나야 움직인다)

| 줄 | 무엇 뒤 |
|---|---|
| design-risk-review 119 | #15 = 118 의 B2 · #39 = Q1 의 답을 받아 사용자가 상한 값을 정한다 |
| design-risk-review 127 | 118 의 B5 · Q7 뒤 — 그 전까지 P2 (8)(9)는 합성 픽스처로만 채워진다 |
| risk-200k 32 · 34 | Q2(단위 크기) · 57 뒤 — 20만에서 홀로 창을 넘는 단위가 있으면 단위 쪽 나누기, 0 이면 시험 · 가드만 두고 걷는다(34 는 32 · 33 과 함께) |
| risk-200k 33 | 57 A/B 때 영역마다 등록부 행 수 · 요약 입력 글자 수 · 코드 조립본으로 떨어진 영역 수 — 흔하면 짓고 아니면 걷는다 |
| risk-200k 43 · 58 | 57 A/B 의 실제 호출 수(배수) 뒤 dev 가 calls_estimate 를 보정하고 실측표를 적는다 |
| risk-review-redesign 22 | 179 · 20(Q2)의 출력 뒤 dev 가 PLAN 6절 세 칸과 전원 1회 벽시계를 적는다 |
| risk-review-redesign 195 · 196 | M4 — 184 · 186 뒤 사용자가 짓거나 걷는다(cae00 물음 없음) |
| deliberation-quality 115 ~ 119 | T1(114) 판정 뒤 차례로 — T2 rebut_quote(기본이 이미 1이라 '끌지' 를 잰다) · T3 prose_first · T4 effort(러너 팔이 없어 그 차례에 dev 가 길부터) · T5 chair_bestof · chair_cite · T6 anchor 하나로 좁힘 |
| procedures 589 | A13 의 답 뒤 SP 받기가 켜진 박스에서 실제 과제 하나로 키가 이어지나 |
| doc-to-ra 30 · 49 · 52 · 55 · 59 | 금 표본과 23 · 25 · 26 실측 뒤(DocForge R-D) · SP 받기(29) 뒤 부서 · 모델 후보 규칙 · DOCX SmartArt 는 dev 빈칸으로 따로 남는다 |
| ste-fullangle 24 | 22 의 sbatch 판정 뒤 — ✗ 면 ste 에서는 하지 않고(사용자 결정) 앱을 둘지만 고른다(낙하는 stcx 길 — DynaForge) |
| web-research 11 · 12 | Q11 출력 뒤 — check-egress 3절이 MITM · 폐쇄망 · dev 동일로 가르고 dev 가 context-notes 에 적는다 |
| chat-actions 30 | 29 의 개통 확인 뒤 dev 가 changelog 에 '개통 환경에서' 한정 문구 한 줄 |
| followups-1017/requests 42 · 76 | MaterialTwin 데이터 담당 몫 — HEAXHub HH-10 과 받은 편지함 [2026-10-31](../cae00-inbox/2026-10-31.md) Q1 이 이미 묻는다 |
| org-chart 18 | 현 라운드 request-1030 HP-53 · OB-26 이 맡는다 |

### C-4. 우리 몫 아님 — Report Archive(9줄, 묻지 않는다)

| 줄 | 까닭 |
|---|---|
| design-risk-review 12 · 82 · 178 | RA 온톨로지 부트스트랩(6축 · 12관계 — HWAXRisk `backend/scripts/bootstrap_ra_ontology.py`, dry-run 뒤 `--apply`)은 RA 시스템 관리자가 그쪽에서 한다. M4 보내는 쪽을 지을 때 전제로만 적는다(KG 는 서비스 계정 이름 — 10-31 RK-01 D-1). 178 의 ADH 부트스트랩은 M4 다. |
| sso-delegation 25 | RA 담당 — 위임 창구 · 홈 부서 보장(RP-01). |
| ra-reconnect 30 | 옛 RA 설치본 정리는 RA 담당과 박스 운영자가 정한다. 우리 몫(27줄의 확인)은 Q15 에 넣었다. |
| change-request-8-10/context-notes 49 · server-setup 493 | RA 가 '헤더 없으면 홈 부서' 를 보장하는지는 RA 쪽 일이다. 밝혀지면 그때 위임일 때 헤더를 빼는 작은 판(routes.py · docforge_delivery.py · test_ra_sso)을 연다. |
| change-request-8-10/context-notes 59 | 홈이 개인함인 사람의 조직 배정은 RA 쪽 일이다. |
| doc-to-ra 28 | ra-requests.md(R1 ~ R5)는 사람이 RA 쪽에 건넨다 — 우리는 RA 에 쓰지 않는다. 포털 배달(사용자 명의 엄격 생성 · 25MB · 자동 태깅)은 doc-to-ra 42 실주행 때 본다. |

## 5. 표 D — 걷음(51줄, 까닭은 그 줄에도 달았다)

| 줄 | 까닭 |
|---|---|
| design-risk-review 72 · 91 | LO-D2 · LO-D3 — 대화 종류는 바꾸지 않고 8번째 카드는 짓지 않는다(백엔드 ConvCreate.kind 는 이미 risk-review 를 받는다) |
| design-risk-review 78 | 파싱 성공률은 리스크 앱 원장(risk_spec_parsed · spec_parse_failed)에서 센다 |
| design-risk-review 83 | (10) 은 10-17 사용자가 닫았다 — AIDataHub 로 보내는 쪽(M4)이 없어 확인할 동작이 없다 |
| design-risk-review 167 · 168 | ECAD 1단계(HWAXRisk `9bd5f48`) 뒤 나머지는 ecad-1031 과 앱 대장 §4 가 이어받았다 |
| risk-200k 9 | W-D7 로 결정 전 어림의 쓸모가 끝났다(보정은 43 · 57) |
| risk-200k 39 | W-D15 ③ — 쪽은 엔진 run 안에서 코드로 합치고 LLM 합치기 호출은 두지 않는다 |
| risk-review-redesign 19 · 118 | 179행(M3 단계 E, 보강 팔 포함)과 같은 실행이다(D-32) |
| risk-review-redesign 21 · 119 | 180행과 같은 걸음이다 |
| risk-review-redesign 120 · 122 | 파일럿은 181행(M3 엔진 위)으로, 수치는 186행에서 함께 적는다 |
| risk-review-redesign 190 | risk-200k W5 'cae00 A/B' 로 옮겨 정했다(W-D1 · W-D7) |
| deliberation-quality 86 | 118행 T5 가 같은 일(F2 등급 태깅)을 든다 |
| deliberation-quality 91 | MCP 수렴은 이미 '판정 불가 — 다음에 측정할 것' 을 받고(hwax-deliberate.js:740) 웹 엔진은 상호 배타 선택지가 없다 |
| deliberation-quality 120 | 따로 할 일이 아니라 T1 ~ T6 의 재는 법이다(114행) |
| chat-depth-context 45 | 10-27 HA-22 로 답했고 다시 재기는 운영 OB-71 이다 |
| cluster-deploy 66 · 67 | 부모 줄(RA 블루-그린)이 10-17 에 닫혔고 포털은 RA_HOST 하나로 다시 이었다(`aeb46ef`) — 컷오버 · 롤백은 RA 담당 몫 |
| data-migration 32 | D0 를 되돌릴 계획이 없고 목록이 가리키던 사본 파일도 없다 |
| procedures 354 | LO-D4 — 정기 갱신은 짓지 않는다(`--check` 가 내려간 백엔드 탓 '사라짐' 을 가르고 그때 갱신을 막는다 — `e76691d`) |
| procedures 412 | 09-16 라운드 대상이 그 뒤 코드로 덮였고 세 영역은 뒤 수정 라운드를 지났다 — 새 감사는 새 요청으로 |
| procedures 618 | LO-D2 — 대화 종류는 바꾸지 않는다(바꾸면 심의 탭에서 사라진다) |
| doc-deliberate 5 | 다시 저장 길을 쓰지 않는다 — 추출은 직접 읽기만, 다시 저장한 PPTX 보내기는 넣지 않는다(chat-ppt PP-D1 ②) |
| cluster-wiring 9 · 10 · 11 · 33 · 95 | 덱을 stcx 대시보드 업로드로 나른다(KooRemapper `92cb157`) — 공유 경로 · 권한을 쓰는 흐름이 없다 |
| cluster-wiring 39 · 42 | 낙하 경로가 게이트웨이 MCP(HTTP)라 ssh 홉이 없다 — HTTP 길은 가짜 MCP 시험이 덮는다 |
| ste-cae00 12 | S2 가 자동 대조로 바꿨다(drive-drift · deploy-ste · ste-doctor deployed 행) |
| ste-cae00 16 | argv 판으로 시크릿이 심긴 회차가 없다 |
| ste-cae00 47 | 설치 배치가 MCP 항목 env 에 NODE_EXTRA_CA_CERTS 를 넣는다(TB-D1) — Windows 확인은 token-bat 14 · 22 |
| sso-delegation 36 · 37 | MatNexus 는 외부 연결 `connect:`(토큰 등록)라 비밀 · 위임 창구가 없다 |
| sso-delegation 40 | FMEA 는 `connect:` 와 목록 계정 절차로 붙었다 — 남은 답이 오면 타일 소개 문구만 맞춘다 |
| web-research 97 | WANT 목록 길이 HEAX 일반 경로로 대체됐다 — 누락은 drive-drift · update-all 이 드러내고 '지어지지 않은 앱' 검사는 B1 |
| ra-workspace 37 · 38 | 운영은 RA 위임이라 조직 고르기 · 다중 조직 선택이 실사용되지 않는다(38 의 메일은 A31) |
| change-request-8-10/context-notes 38 | ARP 핸드오프 `8517dd5` 가 cae00 10-17 판에 들었다 — 반영 시각 지시가 지났다 |
| change-request-8-10/context-notes 80 | `3f6bb28` 이 cae00 10-17 게이트웨이 판에 들었다 — '배포 전 확인' 조건이 지났다 |
| change-request-8-10/server-setup 492 | 현 라운드(AIDataHub AD-07 · request-1027 HA-11)가 as_of 를 맡았다 |
| leftovers-1017/PLAN 9 · 16 · 50 | 10-17 범위 경계 · 셈 기록이다 — 남은 줄은 이번에 줄마다 갈랐다 |
| followups-1017/checklist 42 · 43 | request-1029 E-9 — 정답 달기는 포털 '도구 검색 검토', 질의 모으기는 굴러가는 창이다 |
| chat-actions 27 | cae00 은 `pnpm build` 를 돌리지 않는다(dev 빌드가 Drive 로 온다) · 커밋은 cae00 10-17 판에 들었다 |

## 6. 풀림 줄(107줄 — 근거는 그 줄에 달았다)

| 파일 | 줄 |
|---|---|
| design-risk-review | 26 · 76 · 85 · 87 · 96 · 97 · 98 · 102 · 103 · 109 · 110 · 131 · 137 · 142 · 162 · 169 · 175 |
| risk-200k | 23 · 42 · 45 · 61 |
| risk-credentials · risk-review-redesign · deliberation-quality | 47 · 178 · 43 |
| deliberation-quality/method-menu | 21 ~ 24 · 27 ~ 34 · 37 ~ 41 · 44 ~ 47 |
| claude-delib-parity · delib-ops | 26 · 24 · 25 |
| chat-depth-context · chat-llm-stcx · chat-ppt · chat-self-check | 66 · 8 · 9 · 34 · 19 · 20 |
| cluster-deploy · data-migration · update-all-skip-unchanged | 18 · 81 · 39 · 27 |
| procedures | 183 · 306 · 411 · 421 · 451 · 498 · 500 · 502 · 612 |
| doc-to-ra · doc-deliberate | 24 · 27 · 68 · 34 |
| cluster-wiring | 34 · 35 · 40 · 41 · 78 · 82 · 84 |
| ste-cae00 | 9 · 10 · 11 · 62 |
| sso-delegation · ext-connect | 35 · 19 · 67 · 68 · 69 · 70 |
| mxwp-wiki · gateway-audit-ip · access-history · change-request-6 | 30 · 11 · 14 · 8 |
| change-request-8-10 | context-notes 120 · 121(① '알림' 딱지 · ② 빠진 앱 위임 끄기 · ③ 토큰만 있는 안내 · 주인 검사 결정) · server-setup 487 · 494 · 507 |
| leftovers-1017 · followups-1017 | PLAN 17 · 49 · context-notes 6 · followups PLAN 57 · context-notes 136 · requests 6 · 55 |
| chat-actions · embedder-bge-m3 · ui-refresh | 25 · 20 · 33 |

## 7. 판정 중에 본 것

- **리스크 앱 웹 '과제 만들기' 가 늘 422 다**(B33) — 서버는 등급을 요구하는데 화면이 보내지 않는다. MCP 로는 만들어진다.
- **전문가 색이 화면마다 다르다**(B12) — 이름으로 칠하는 곳과 키로 칠하는 곳이 섞였다.
- dev 절차 원장에 09-15 21:00 의 실행 하나(제목 q · tool_00 ~ 59 · 결과 8바이트)는 시험이 남긴 흔적으로 보인다. 지울지는 사람이 정한다.
- 기록 줄에 든 계정 메일(ra-workspace 38)은 A31 로 묻는다.
