# 10-30 웹 챗 재시험 · 디지털 워커 QA — 수정 요청 (2026-10-30 · cae00 운영 기준)

요청 HWAX Portal 운영(cae00) · 대상 저장소 HWAXAgentServer(`app.py`) · HWAXMcpGateway(`gateway.py`) · HWAXPortal(`infra/`) · 박스 밖 플랫폼(Datahub 플랫폼 · HEAXHub DocForge · StepForge · ARP · SignalForge · 클러스터 앱, 끝 절에서 KooRemapper · AIDataHub · MX 백서를 더함) · 기준 판 포털 `aec8e29` · 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d` · update-all 로 받는 플랫폼: 에이전트 서버 · 게이트웨이 · 포털 · StepForge · HEAXHub(DocForge) · SignalForge · KooRemapper · AIDataHub · MX 백서는 예, ARP · 클러스터 앱(STE · stcx) · Datahub 플랫폼은 아니오(00-INDEX 와 같다).

근거는 같은 날 두 시험이다. [qa-ontology/QA-CHAT-QWEN-20261030.md](qa-ontology/QA-CHAT-QWEN-20261030.md)(온톨로지 16문항 재시험 — PASS 12 · PARTIAL 3 · FAIL 1)와 [qa-digital-worker/QA-DIGITAL-WORKER-20261030.md](qa-digital-worker/QA-DIGITAL-WORKER-20261030.md)(운영자 페르소나 14명 · 교차 2문항 — PASS 10 · PARTIAL 4 · FAIL 2)다. 둘 다 사용자가 SSO 로 로그인한 웹 화면으로만 시험했다. 줄 번호는 위 기준 판의 것이다. 10-29 요청(포털 `docs/request-1029`)으로 고쳐진 것은 다시 적지 않았다.

**한 줄**
- 전문가(운영자)를 고르거나 앱을 핀하거나 문서를 붙인 챗이 LLM 400 으로 모두 실패했다(HA-26). 지금은 박스 우회로 막아 두었다.
- 자기검증이 맞는 초안을 틀리게 고친다. 10-30 재시험의 PARTIAL · FAIL 넷 가운데 셋이 이 때문이다(HA-27).
- 디지털 워커가 잡을 LLM 으로 폴링하고(HA-28), 사람에게 묻지 않고 무거운 잡을 건다(HA-29).
- 게이트웨이 개인정보 가림이 계산 결과의 숫자를 망가뜨리면서(HG-21), 정작 담당자 실명 · 메일 · 내부 IP 는 가리지 못한다(HG-22).

**건수**

| 플랫폼 | 높음 | 중간 | 낮음 · 선택 |
|---|---|---|---|
| 에이전트 서버 | 4 | 3 | 3 |
| 게이트웨이 | 2 | 0 | 1 |
| 포털 | 0 | 3 | 5 |
| 박스 밖 플랫폼 | 3 | 13 | 14 |
| **합계** | **9** | **19** | **23** |

위 수는 1~4절 17건(높음 7 · 중간 7 · 낮음 3)에 맨 끝 절 '이전 회차에서 남은 챗 · 디지털 워커 요청' 34건(높음 2 · 중간 12 · 낮음 20)을 더한 것이다.

우리 몫(박스 설정 · 사람 결정)은 5절에 따로 적었고 위 건수에 넣지 않았다.

## 1. 에이전트 서버(HWAXAgentServer `969e723`)

| # | 심각도 | 무엇이 | 근거(파일:줄 · 실측) | 할 일 | 다시 볼 시험 |
|---|---|---|---|---|---|
| HA-26 | 높음 | 이 턴의 안내(전문가 · 앱 핀 · 지식카드 발췌 · 붙인 문서)가 있는 챗이 LLM 400 'System message must be at the beginning.' 으로 실패한다. | `_turn_msgs`(`app.py:312-317`)가 `CHAT_STABLE_PREFIX` 켬(기본)일 때 안내를 이력 뒤 · 사람 발화 바로 앞에 두 번째 ("system", …) 로 넣는다. stcx vLLM 의 Qwen 채팅 틀은 맨 앞이 아닌 system 을 거절한다. 10-30 09:52 전문가 턴 1/1 실패 · 자동 재시도 두 번(`app.py:5285`)도 같은 메시지라 같은 400 이었다. 박스 우회(`CHAT_STABLE_PREFIX=0`, 09:55) 뒤 운영자 14명 0/14 실패. | 안내를 두 번째 system 이 아니라 이번 사람 발화의 머리(같은 user 칸 — '[이번 턴의 안내] …' 뒤에 발화)로 넣는다. 그래도 400 'System message' 가 오면 자동 재시도 때 안내를 첫 system 에 합쳐 보낸다. 앞부분 고정을 끈 대가는 크게 보이지 않았다 — 끈 디지털 워커 시험의 캐시 적중 78.4%, 켠 OT 재시험 68.5%(문항 꼴이 달라 바로 견줄 수는 없다). 대화 고정으로 같은 질문 안의 호출이 캐시를 쓰는 몫이 크기 때문으로 본다. | 전문가 · 앱 핀 · 붙인 문서 챗 각 1회를 우회를 걷은 상태로. |
| HA-27 | 높음 | 자기검증이 맞는 값을 틀리게 고친다. | OT-04 개발모델 34 → 13 · OT-08 다른 가상검증 항목의 부서 A → 부서 B · OT-09 '20' 을 지우고 '근거 없음 — 추정' · DW-05 직전 기간 값을 지워 '가장 많이 늘어난' 순위가 비었다. 셋은 게이트웨이 읽기 도구로 서버 값을 직접 대조했다(초안이 맞았다). 검토자 입력의 조회 결과를 창에 맞춰 자르고(`app.py:4371` `_sc_fit(res, cap["res"])`), 바꿀 곳을 근거와 다시 대조하지 않고 넣는다(`app.py:4413` 이후). 이번 16문항에서 고침 12 · 의심 3 · 맞음 1, 디지털 워커 18턴에서 고침 15. | ① 고침의 [새 글] 에 든 숫자는 이번 턴 도구 결과 **원문(자르기 전)** 이나 그 원문 값의 합 · 차 · 비율일 때만 넣는다. 아니면 '짚음(반영 안 함)' 으로 돌린다. ② 초안의 숫자를 지우거나 '근거 없음' 으로 바꾸는 고침은 그 숫자가 원문에 있으면 버린다. ③ 검토자에게 준 결과가 잘렸으면 그 결과에서 온 수치는 고치지 말고 짚기만 하라고 검토자 지시에 밝힌다. | OT-04 · 08 · 09 · DW-05. /health self_check 의 fixed 비율. |
| HA-28 | 높음 | 잡 상태를 LLM 으로 폴링한다. | DW-02 후속 — run_checklist 를 건 뒤 get_task 를 26번 불렀고 LLM 요청이 29번 · 85초였다. 끝을 못 보고 저장된 옛 결과로 답했다. 같은 도구 네 번째의 '앞 결과를 써라' 꼬리(`app.py:1317`)는 폴링에 맞지 않는다. | 상태 조회 도구(get_task · job_status · heaxstep_forge_job_status · docforge_status · doe_status · study_get 등 — 도구 쪽 '상태' 표지나 이름 목록)는 에이전트가 코드로 일정 간격(예 10초) · 상한(예 10분)까지 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘긴다. 기다리는 동안 화면에 진행률을 흘린다. | DW-02 후속 · DW-03 후속. |
| HA-29 | 높음 | 사람에게 묻지 않고 무거운 잡을 건다. | DW-03 — StepForge run_job 두 번(graph · 판 전체 drop_check)을 확인 없이 걸었다. drop_check 는 10% 에서 1,812초를 돌다 사용자 결정으로 취소했다(단일 러너를 잡고 있었다). 프롬프트의 '잡 제출은 먼저 확인'(`app.py:162`)이 지켜지지 않는다. 운영자 정의에는 이미 `writes` · `confirm` 목록이 있다(포털 `infra/personas/he-team.json`). | 잡을 시작하는 도구(run_job · run_checklist · docforge_convert · 클러스터 제출 · 운영자 정의의 `writes`)는, 이번 턴 사람 발화가 그 일을 분명히 시키지 않았으면 코드 단에서 확인 카드로 멈춘다. 도구가 '예상 작업량' 을 주면 확인 문구에 싣는다. | DW-03. |
| HA-30 | 중간 | 허브를 건널 때 앞 허브의 id 를 그대로 넘긴다. | OT-07 — failuretrace_graph_neighbors 에 자주검증 id 를 넘겨 APP-GRAPH-0001 이었다(규칙 ⑤ 가 있는데도). | 허브 도구를 부를 때 object_id 가 다른 허브의 결과에서 온 것이면(이번 턴 결과에서 그 id 를 낸 도구의 앱으로 안다) 코드가 key 로 그 허브에서 다시 resolve 하거나, 부르기 전에 '이 id 는 ○○ 허브 것 — key 로 다시 풀어라' 를 돌려준다. | OT-07. |
| HA-31 | 중간 | 전문가 검색 가로채기 — 질문을 LLM 없이 '전문가 추천' 목록으로 답한다. | DW-13 — 'PCB 내부 크랙을 잘 아는 전문가 에이전트를 추천하고, 추천 근거가 된 기록 수를 알려줘.' 가 `is_agent_search`(`app.py:2587-2591` — 80자 이하 + '(전문가 · 에이전트) … (추천 · 알려 · 찾 …)')에 걸려 `run_agent_search`(`:2602`, 부르는 곳 `:5646`)로 갔다. LLM 0회 · 추천 10명 중 절반 무관(로그 플랫폼 · MCP 레지스트리 · 카메라 MIPI 등) · '기록 수' 는 답하지 않았다. 전문가(AI 데이터 허브 운영자)를 고른 대화에서도 가로챘다. | 빗금 트리거('/전문가' 등)만 결정적 목록으로 답하고, 자연어는 질문에 다른 물음(수 · 근거 · 비교 · 조건)이 없을 때만 가로챈다. 전문가를 고른 대화에서는 가로채지 않는다. 추천 순위에 무관한 사람이 오르는 까닭(recommend 점수 · 분야 섞기)을 본다. | DW-13. |
| HA-32 | 낮음 | 없는 코어 타입 이름을 지어내 부른다. | DW-22 — object_resolve(type_slug='management_standard')(실제는 criterion). | 코어 규칙 글에 어휘표 낱말 → 타입 이름 대응(고장모드 → failure_mode · 관리 기준 → criterion · 시험항목 → test_item …)을 한 줄로 싣는다(`core_vocab.json` 에 칸을 더해 만든다). | DW-22. |

## 2. 게이트웨이(HWAXMcpGateway `44f4b8d`)

| # | 심각도 | 무엇이 | 근거(파일:줄 · 실측) | 할 일 | 다시 볼 시험 |
|---|---|---|---|---|---|
| HG-21 | 높음 | 개인정보 가림이 계산 결과의 숫자를 망가뜨린다. | DW-07 — 적층 계산 결과의 소수 하나(소수점 뒤 숫자열이 15자리로 Luhn 을 통과)가 `4.[가림:IMEI]` 로 바뀌었다. `_IMEI_RX`(`gateway.py:624`)의 앞뒤 거르개가 `(?<![\w-])` · `(?![\w-])` 라 소수점 '.' 뒤의 숫자열을 IMEI 로 본다. | 앞뒤 거르개에 '.' 을 넣는다(`(?<![\w.-])` · `(?![\w.-])` — 지수 'e' 는 \w 에 든다). JSON 숫자 값(따옴표 없는 수)은 IMEI 칸 이름일 때만 가린다. | DW-07. |
| HG-22 | 높음 | 담당자 실명 · 메일 · 계정 · 사설 IP 가 답에 나간다. | DW-06 ARP `partOwner`(실명) · DW-03 StepForge `owner`(메일) · DW-12 클러스터 잡 제출자(메일)와 컨트롤러 사설 IP · DW-22 StepForge 담당 계정. 가림은 칸 이름 목록(`_PII_KEYS`, `gateway.py:612-620`)으로만 한다. | 칸 이름에 owner · partOwner · submitter · user · email · assignee 꼴을 더하고, 메일 꼴 · 사내 계정 꼴(영문.영문숫자)과 사설 IP 꼴(10.x · 172.16-31.x · 192.168.x)은 칸 이름과 상관없이 가린다. REST 다리 출력도 같은 가림을 거친다(TODO-20261029 R-08 과 같은 일). 원천 쪽 요청은 4절. | DW-03 · 06 · 12 · 22. |

## 3. 포털(HWAXPortal `aec8e29`)

| # | 심각도 | 무엇이 | 근거 | 할 일 | 다시 볼 시험 |
|---|---|---|---|---|---|
| HP-51 | 중간 | 운영자 정의가 가리키는 앱이 그 박스 게이트웨이에 없는지 미리 알 길이 없다. | DW-12 — he-sim-smarttwin 의 앱(smart-twin-mcp · smart-twin-cluster)이 cae00 게이트웨이에 없다. 챗을 보낸 뒤에야 화면 주의가 뜬다. | update-all 의 운영자 페르소나 미리보기(`infra/scripts/sync-he-personas.py` — `update-all.sh:1176`)나 '새 앱 점검'(`infra/scripts/app-checks.py` — `:3150`)에 '운영자 앱이 이 게이트웨이에 없다' 줄을 더한다. 전문가 고르기 화면에도 그 운영자에 작은 표지를 단다. | DW-12. |

## 4. 박스 밖 플랫폼

| # | 대상 | 심각도 | 무엇이 | 근거 | 할 일 |
|---|---|---|---|---|---|
| SG-04(다시) | SignalForge | 높음 | 제품 해석이 프로젝트 A 의 모델 · 마케팅명을 프로젝트 B 의 제품 코드로 푼다. 교차 업무에서 다른 제품의 VOC 를 주의 없이 싣는다. | DW-21 — SignalForge 온톨로지가 모델 C(코어에서 프로젝트 A)를 프로젝트 B 의 제품 코드로 이었다. 10-29 EX-03 · 10-30 OT-15 와 같다. 코어는 프로젝트 A · 프로젝트 B 를 다른 프로젝트로 둔다. | 데이터 결정(제품 행을 나눌지)이 남았다(포털 `docs/request-1029/signalforge-sg04-question.md`). 그 전까지는 resolve 결과에 '이 모델 · 이름이 여러 PLM 프로젝트에 걸린다' 주의 칸을 싣는다. |
| HH-14 | HEAXHub DocForge | 중간 | 입력 뿌리의 파일을 볼 도구가 없어 운영자가 변환할 파일을 고르지 못한다. | DW-10 — 도구 5개(convert · status · package · capabilities · cancel)뿐이고, 경로 '/' 접수는 '허용된 입력 뿌리 밖' 이었다. | 입력 뿌리의 파일 목록(이름 · 크기 · 형식 · 수정 시각, 하위 폴더 한 단계)을 주는 읽기 도구를 더한다. |
| ST-12 | StepForge | 중간 | 판 전체 drop_check 잡이 진행률 10% 에 30분 머물렀다. 한 호출 관문의 예상(60초)은 하한이었다. | DW-03 — 3,658형상 부울 합치기 단계에서 진행이 오르지 않았고 단일 러너를 잡았다. | 합치기 단계에도 진행률을 올리고, 잡 시작 응답에 '예상 작업량(형상 수 · 하한 초)' 과 '러너를 오래 잡을 수 있다' 를 싣는다. list_projects 의 담당자 칸은 MCP 출력에서 가린다. |
| AR-9 · AR-10 | ARP | 중간 | 담당자 실명이 MCP 출력에 실리고, 낙하 높이에 단위가 없다. | DW-06 `partOwner` · 낙하 높이 152 를 챗이 'mm' 로 읽었다(DW-06 · OT-13). | AR-9 — basicInfo 수치 칸에 단위를 싣는다. AR-10 — MCP 출력의 사람 칸을 가린다. [16-ARP-ODBHub-core-ontology.md](16-ARP-ODBHub-core-ontology.md) 에 함께 더한다. |
| PA-20 | Ste(클러스터 조회 앱) | 중간 | cluster_info 가 컨트롤러 사설 IP 와 잡 제출자 메일을 준다. | DW-12. | 챗 · MCP 출력에서는 호스트 이름만 싣고 IP · 메일은 뺀다. |
| DP-14 | Datahub 플랫폼(자주검증 · FailureTrace · 부서 허브) | 낮음 | 조건 주소 오류(APP-OBJECTS-0073)에 바른 주소 예가 없다. | OT-09 · 11 에서 4번. | 오류 문구에 그 타입에서 쓸 수 있는 주소 예(`in.applies_to_part` · `out.occurs_in_part` 꼴)를 싣는다. 응답 크기(DP-01)는 그대로다 — 10만 자 넘는 응답 11건(OT 재시험). |
| DP-15 | 부서 허브(Datahub) | 낮음 | 해석 기록이 비었다(같은 key 고장모드에 이어진 기록 0건). | 10-29 EX-01 — 해석 기록 타입 자체가 비었다. | 해석 기록 적재 계획을 묻는다(질문). |

## 5. 우리 몫(보내지 않음)

| # | 할 일 | 상태 |
|---|---|---|
| OB-91 | 박스 우회 `CHAT_STABLE_PREFIX=0`(에이전트 서버 .env, 10-30 09:55 재기동) — HA-26 이 들어오면 줄을 지우고 재기동한다. | 들어가 있다(Knox 봇 연동 세션, 백업 `~/portal-backups/agent.env.stableprefix-*`). |
| OB-92 | SmartTwin 운영자 — cae00 게이트웨이에 SmartTwin MCP 를 잇거나, 이 박스의 he-sim-smarttwin 정의를 연결된 클러스터 앱으로 바꾼다. | 남았다. |
| OB-93 | 도구 설명 예산 비교(`CHAT_TOOL_SCHEMA_BUDGET` 40000 → 30000) — 같은 16문항 · 첫 호출 첫 토큰 · search_tools 왕복. | 남았다(10-30 재시험 보고서 6절). |
| OB-94 | DocForge 입력 뿌리에 시험 파일 하나(DW-10 다시 보기). | 남았다. |
| OB-95 | 생각 강도 비교(`CHAT_LLM_REASONING_EFFORT` high · medium) — 디지털 워커 시험의 생각 글이 한 턴에 1,886 ~ 36,293자다. | 남았다. |
| OB-96 | 허브 큰 응답(graph_neighbors · object_fields · object_references) 견본에서 사람 이름을 지워 개발 쪽에 넘긴다. 개발이 그 칸 모양에 맞춰 접기 규칙을 짓는다(포털 `docs/request-1029` checklist O-12 · context-notes C-22). | 남았다. 끝 절의 HA-34 · DP-01(다시)와 맞물린다. |
| OB-97 | 포털 챗에서 'simflow 로 수지 도포 돌려줘' 가 패널 도구가 아니라 prepare_run 으로 시작하는지 한 번 본다. arp_upload_open 이 무엇을 돌려주는지 재어 개발 쪽에 넘긴다(에이전트 `app.py:2718-2719` — 실측이 오면 패널 전용 도구 집합에 더한다고 적혀 있다). | 남았다(reflection-1028/03 HA-05 확인). |
| OB-98 | 외부 연결 앱 손 시험 — 토큰이 없는 사용자에게 list_tool_apps 가 needs_connect 를 보이는지, 등록한 사용자의 whoami 신원 칸이 가림에 걸리지 않는지 본다(username 이 가림의 이름 칸에 든다 — 게이트웨이 `gateway.py:612-613`). | 남았다(02-HWAXMcpGateway 7절 M-16 · reflection-1028/02 HG-10). |
| OB-99 | 챗이 실제로 던진 search_tools 질의 8건으로 cae00 순위를 다시 잰다(포털 `docs/request-1029` context-notes C-14, 절차는 reflection-1028/02 2절 8번). | 남았다. 10-30 재시험의 근거 블록에는 search_tools 호출이 0회였다. |
| OB-100 | 15자리 접수 · 문서 번호가 Luhn 검사를 우연히 통과해 가려지는지 본다(게이트웨이 `gateway.py:609` — IMEI 꼴은 어느 글에서든 가린다). HG-21 의 '.' 거르개로는 낱개 15자리 번호가 풀리지 않는다. 보이면 HG-21 에 덧붙인다. | 남았다. |
| OB-101 | StepForge 코어 받기 cron 에 주 1회 `--full` 을 더한다. 허브에서 빠진 과제가 find_plm_task 결과에 남지 않게 한다. | 남았다(TODO-20261029 T-17). |
| OB-102 | DocForge 길 한 번 — 평문 pptx 를 'Report Archive — 정밀 변환' 과 '이 대화에서 분석' 으로 보낸다. DRM 파일은 PC 에서 만들지 않는다. | 남았다(TODO-20261029 H-05). |
| OB-103 | SimFlow 목적지 첫 실주행 — 회신(입력 확장자 · 업로드 상한, RA 가져오기 상한)이 오면 포털 `backend/.env` 로 맞추고 한 번 보낸다. | 회신 대기(TODO-20261029 W-03 · W-04 · 01-HWAXPortal HP-15). |
| OB-01 · OB-02 · OB-03 | stcx 챗 LLM 잡을 11-14 전에 다시 띄운다. 키를 바꾸면 포털 `infra/.env` 의 `CHAT_LLM_API_KEY` 를 고치고, 다른 사용 서비스 담당에게 11-10 무렵 미리 알린다. | 90-OURS 그대로 — 11-14 전(TODO-20261029 T-01 · T-02). |
| OB-04 | 운영 앱 둘(dynaforge-prod · stepforge-prod)의 '(시험)' 라벨을 박스 권한표에서 바로잡는다. 목록 · 검색 숨김은 들어왔지만 list_tool_apps 는 두 앱을 그 라벨로 보인다(게이트웨이 `gateway.py:3101`). | 90-OURS 그대로 — 사용자 확인(포털 checklist O-5). |
| OB-26 | ODB 허브 운영자(he-cad-odbhub)를 둘지 정한다. '둔다' 면 끝 절 HP-53 의 ODB 몫이 산다. | 90-OURS 그대로 — 사용자 결정(10-30 DW-02 는 이 운영자로 PASS). |
| OB-33 | hwax-batch 앱 설명 문안을 고쳐 search_tools 의 앱 설명 적중을 바로잡는다. 10-30 `/tools-map` 에서 자주검증 허브 설명은 옛 문안이고 부서 허브 설명은 빈 칸이다. | 90-OURS 그대로 — 남았다. |
| OB-34 · OB-25 | OB-92 의 잇기 길 — :5013 이 뜨면 게이트웨이 `provision.env` 로 SmartTwinMCP 를 등록하고(OB-34), 둘째 터널을 정한다(OB-25). 선행은 끝 절의 PA-16 · PA-19(다시)다. | 90-OURS 그대로 — stcx 답 대기(TODO-20261029 W-02). |
| OB-59 | StepForge 과제 찾기의 프로젝트 이름 · 마케팅명 길은 개발 main 에만 있다. 개발이 SIF 를 올렸다고 알리면 `infra/scripts/drive-drift.sh heax` 로 대조하고 update-all 뒤 OT-14 · OT-15 를 다시 본다. | 90-OURS 그대로 — 개발 SIF 대기(TODO-20261029 W-01 · 포털 `docs/request-1029` C-28). |
| OB-60 · OB-61 · OB-62 | 챗 업로드 손 시험 — 목적지 · 큰 파일 · DRM 파일(M-1 ~ M-6). | 90-OURS 그대로 — 10-29 · 10-30 QA 는 돌리지 않았다. |
| OB-63 | 자기검증 손 시험 — 도구 없는 턴의 '(근거 없음 — 추정)' 재현 · 짧은 답 건너뛰기 · 긴 답 중지(M-7 ~ M-10). | 90-OURS 그대로 — 두 QA 는 도구 턴의 판정 · 지연만 쟀다. |
| OB-64 · OB-65 | 위키 버튼 숨김(M-11 · M-12)과 위키 질문(M-13)을 웹 챗에서 본다. 끝 절의 HA-08(다시) · MW-01(다시)와 맞물린다. | 90-OURS 그대로 — 남았다. |
| OB-68 | VOC 화면 손 시험(M-18)과 get_voc_summary(제품 B) 한 번. | 90-OURS 그대로 — 남았다(reflection-1028/08 '운영 확인 필요'). |
| OB-71 | 챗 모델의 '예고만 하는' 호출을 생각 켬 · 끔으로 다시 잰다. 잦으면 그때 에이전트 서버에 따로 청한다. | 90-OURS 그대로 — 두 QA 보고서에는 이 현상 기록이 없다(TODO-20261029 H-06). |
| OB-85 | 챗 사용자 우회 안내(질문에 허브 · 도구 이름을 쓰거나 첫 질문에서 앱을 핀하기)를 걷는다. | 90-OURS 그대로 — 걷을 조건이 찼다(10-30 OT-06 ~ 10 첫 도구 코어 5/5 · 정본 허브를 부른 시험 14/16). |
| OB-87 | 빈 전문가 · 데모 카드의 cae00 몫을 지운다. | 90-OURS 그대로 — 끝 절 AD-05 · AD-06(다시) 뒤. |
| OB-89 | 지식카드 본문 검색 스위치를 켤지 정한다. | 90-OURS 그대로 — 끝 절 AD-04(다시)의 잰 값 대기. |

## 6. 다른 요청과 맞물린 것

- TODO-20261029 4절 R-07(invoke_tool 로 부른 허브 응답을 접지 않는다) — 이번 재시험의 10만 자 넘는 응답 11건이 그 길이었는지는 가르지 못했다. HA-27 ③ 과 함께 본다.
- TODO-20261029 4절 R-08(REST 다리 출력의 개인정보) — HG-22 와 같은 일이다. 한 번에 고친다.
- 10-29 요청의 자기검증 패치 방식(포털 `docs/request-1029` — '바꿀 곳만 받는다')은 들어왔다. HA-27 은 그 방식의 정확도 문제다.
- ARP 단위 · 사람 칸(AR-9 · AR-10)은 [16-ARP-ODBHub-core-ontology.md](16-ARP-ODBHub-core-ontology.md) 의 ARP 절에 이어 붙인다.

## 7. 다시 볼 시험

| 시험 | 언제 | 볼 것 |
|---|---|---|
| OT-04 · 08 · 09 · DW-05 | HA-27 뒤 | 초안의 맞는 값이 그대로 나간다. |
| 전문가 · 앱 핀 · 붙인 문서 챗 | HA-26 뒤, 우회(OB-91)를 걷은 상태로 | 400 이 없다. 접두 캐시 적중을 다시 잰다. |
| DW-02 후속 · DW-03(후속 포함) | HA-28 · HA-29 뒤 | 상태 조회가 LLM 왕복 없이 기다린다. 잡은 확인 뒤에만 건다. |
| DW-07 · DW-03 · 06 · 12 · 22 | HG-21 · HG-22 뒤 | 숫자가 그대로 나오고, 사람 이름 · 메일 · 사설 IP 가 가려진다. |
| DW-13 | HA-31 뒤 | 질문이 챗 에이전트로 가고 '기록 수' 를 답한다. |
| DW-10 | HH-14 뒤 | 입력 파일을 골라 변환까지 한다. |
| DW-21 · OT-15 | SG-04 결정 뒤 | 프로젝트 A 의 VOC 에 프로젝트 B 가 섞이지 않는다. |

## 이전 회차에서 남은 챗 · 디지털 워커 요청 (10-30 대조)

10-27 플랫폼별 요청서 · reflection-1028 · TODO-20261029 · 10-29 · 10-30 QA · 포털 `docs/request-1029` 개발 답을 cae00 HEAD(포털 `aec8e29` · 에이전트 서버 `969e723` · 게이트웨이 `44f4b8d` · KooRemapper `46e4283` · SignalForge `d2a794d` · AIDataHub `ac42bc6` · MX 백서 `f242254`)와 대조해, 챗 · 디지털 워커에 닿는데 아직 열려 있고 1~4절에 없는 것만 적었다. 10-27 행을 다시 올리는 것은 그 번호에 '(다시)' 를 붙였고(4절 SG-04(다시)와 같다), 새 것은 플랫폼마다 지금까지 쓴 마지막 번호 다음부터 매겼다. 심각도는 '무엇이' 칸 머리에 적었고, 심의에 닿는 것은 '심의' 로 표시했다. 고쳐진 것 · 우리 몫 · 보류 · 철회까지 모은 대조표는 [CHAT-DW-ROUTING-20261030.md](CHAT-DW-ROUTING-20261030.md) 에 있고, 우리 몫은 5절 표 끝(OB-96 이후)에 더했다.

### 에이전트 서버(HWAXAgentServer `969e723`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-33 | (중간 · 심의) 심의 전 VOC 미리보기가 `search_voc` 의 새 반환 꼴(객체 안 `results`)을 펼치지 않아, 실패 표시 없이 0건이 된다. | `app.py:6015`(search_voc 호출) · `:6021`(`_parse_json_multi` 결과의 원소마다 `_voc_row`). `_parse_json_multi`(`deliberation.py:2139` · `:2153`)는 객체 하나를 `[객체]` 로 돌려주고, `_voc_row`(`app.py:5980`)는 맨 위에 본문 칸이 없어 text 가 빈다. 빈 text 는 `:6026` 에서 걸러지고 실패로 세지 않아 `degraded` 도 거짓이다(`:6032`). SignalForge `d2a794d` `mcp-server/server.py:195` · `:209-217` 은 늘 `{total, results, strategy, match_mode, notes}` 를 돌려준다. | 결과가 객체이고 `results` 가 목록이면 그 목록을 펼쳐 읽는다. 펼친 뒤에도 0건이면 `notes` 를 미리보기에 싣는다. 펼칠 것이 없는데 결과 글이 비지 않았으면 0건 대신 `degraded` · `partial` 로 센다. | TODO-20261029 R-06 · reflection-1028/08 3절 1 · reflection-1028/00-SUMMARY 4절 |
| HA-34 | (낮음) 허브 응답 접기가 실제로 걸렸는지 로그 · `/health` 어디에도 남지 않는다. 그래서 10-29 · 10-30 두 재시험이 접기의 효과를 가리지 못했다. | `app.py:1656`(`_fold_hub_result`) · `:1909-1917`(invoke_tool 경유도 안쪽 이름으로 접는다). 접은 표지는 LLM 에 가는 결과 글 머리(`:1652` · `:1707`)에만 붙는다. HEAD 에 `fold_count` · `fold_stats` 가 0건이고, 접기 문구가 든 print 도 0건이다. | 허브 응답을 접을 때 로그 한 줄(도구 이름 · 원문 자 수 · 접은 뒤 자 수)을 남기고, `/health` 에 접은 횟수를 싣는다. | QA-CHAT-QWEN-20261030 4절 · 이 요청서 6절 첫 줄(R-07) · TODO-20261029 R-07 ① |
| HA-08(다시) | (낮음 · 심의) 위키 도구가 실린 채 꺼진 박스에서, 엔진이 찾는 꺼짐 글귀와 MX 백서 MCP 문구가 어긋난다. 그러면 챗에 보이는 심의 결정문 단마다 종전 오류 문구가 다시 붙는다. 지금은 위키 도구가 실리지 않아(MW-01) 잠복 상태다. | `deliberation.py:3294`(`_WIKI_OFF_HINTS` = 'wiki_disabled' · '위키는 아직 열리지 않았다') · `:3387`(도구 결과 글에서만 찾는다). MXWhitePaper `f242254` `dist/llm-docx-toolkit/mcp/api_client.py:104` 의 문구는 '…열리지 않았습니다' 이고, wiki_disabled 는 예외의 code 칸에만 둔다(`:487-488`). 10-30 게이트웨이 `/tools-map` 에 wiki_* 는 0개다. | 꺼짐 글귀를 '열리지 않았' 까지로 줄이거나, MX 백서 MCP 문구도 함께 받는다. | reflection-1028/03 HA-08(일부) · TODO-20261029 R-07 ③ · 90-OURS OB-64 · OB-65 |

### 게이트웨이(HWAXMcpGateway `44f4b8d`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-23 | (낮음 · 선택) HG-21 의 보조 안이다. 계산 앱(적층 · 열충격 · 단위 변환) 결과는 IMEI 숫자 꼴 검사를 건너뛴다. HG-21 본안('.' 거르개)만으로도 DW-07 은 풀린다. | `gateway.py:624`(`_IMEI_RX`) · `:696`(`_pii_mask` 는 어느 앱인지 모른다). 부르는 곳 `:5183` · `:5257` · `:5276` · `:5281` · `:5312` 은 도구 이름을 안다. | 부르는 곳에서 계산 앱 도구면 IMEI 숫자 꼴 검사만 건너뛰게 한다(칸 이름 가림은 그대로). 넣지 않기로 하면 이 행은 닫는다. | QA-DIGITAL-WORKER-20261030 4.3 #1 둘째 안 · DW-07 |

### 포털(HWAXPortal `aec8e29`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| HP-52 | (중간) 씨앗 절차 둘이 KooRemapper `find_reports` 의 봉투 응답을 목록으로 읽어, 첫 단계에서 `select:no_field` 로 멈춘다. 0건이어도 `on_none` 이 아니라 같은 오류다. | `docs/procedures/fixtures/fullangle-drop-part-report.yaml:40` · `docs/procedures/fixtures/partial-impact-part-report.yaml:43`(`select: {from: "$", …}`). 실행기는 객체 하나를 `[객체]` 로 감싸고(`backend/app/procedures/runner.py:518-521`), 그 객체에 `id` 칸이 없어 `:538-543` 에서 멈춘다. KooRemapper `46e4283` `platform/mcp_server/server.py:1224-1228` 은 `{items, total, reason, truncated}` 를 돌려준다. | 두 씨앗의 `select` 를 `from: items` 로 고친다(0건이면 `on_none` 이 걸린다). 이미 들인 사용자는 씨앗을 다시 들이면 판본이 오른다(`backend/app/procedures/routes.py:347-359` import_seed). 아니면 실행기가 `items` 배열 하나뿐인 봉투를 목록으로 풀어 준다. | TODO-20261029 R-05 · reflection-1028/04 3절 ① · reflection-1028/00-SUMMARY 4절 |
| HP-53 | (중간) 운영자 정의의 `writes` · `confirm` 이 비었거나 모자라다. 그래서 '요청했을 때만 부른다' · '확인을 받은 뒤 부른다' 안내가 여러 잡 · 쓰기 도구에 붙지 않고, HA-29 의 코드 관문이 읽을 목록도 빈다. | `infra/personas/he-team.json:84-87`(he-cad-odbhub — todo 그대로, key_tools · writes · confirm 빈칸) · `:402-405`(he-data-arp 같음) · `:449-450`(he-data-coreontology writes · confirm 빈칸) · `:825`(he-expert-risk writes 빈칸) · `:51`(he-cad-stepforge writes 에 run_recipe · save_recipe · set_revision · set_admin 없음) · `:166`(he-sim-dynaforge writes 에 recipe_* 없음). `infra/scripts/sync-he-personas.py:71-77` 이 두 목록을 프롬프트의 두 줄로 만든다. DW-03 은 run_job 이 writes 에 있는데도 확인 없이 걸었으니, 근본 고침은 HA-29 이고 이 행은 그 관문이 읽을 목록을 채우는 짝이다. | 10-30 cae00 `/tools-map` 과 대조한 목록 밖 도구를 각 운영자의 `writes`(잡 · 쓰기)와 `confirm`(지우기 · 권한 · 되돌리기 어려운 것)에 넣는다 — ODB run_checklist · run_analysis · run_compare · run_curvature · create_modified_odb · import_modified_odb, ARP arp_upload_create · arp_upload_stage · arp_upload_register · arp_upload_discard, 코어 허브 object_create · object_update · objects_delete · object_merge · datasource_sync · bundle_import · job_apply, 리스크 앱 risk_start_job · risk_create_project · risk_create_diff, StepForge run_recipe · save_recipe · set_revision · set_admin(confirm), DynaForge recipe_propose · recipe_register · recipe_run(KR-23). ODB · ARP 운영자는 todo · key_tools 도 채운다. ARP 운영자 함정에 '낙하 높이 칸은 단위가 없다 — 시험 조건은 cm' 한 줄을 넣는다(AR-9 전까지). `sync-he-personas.py` 미리보기(`:147-153` 검사 옆)는 운영자 앱의 쓰기 꼴 도구 가운데 두 목록에 없는 것을 알린다. ODB 몫은 OB-26 이 '둔다' 일 때다. | QA-DIGITAL-WORKER-20261030 DW-03 · DW-02 후속 · 이 요청서 HA-29 · TODO-20261029 R-09 · 90-OURS OB-26 |
| HP-54 | (낮음 · 조건부) SmartTwin 운영자 정본에 이 박스에 붙은 클러스터 앱(ste)이 없다. OB-92 에서 '정의를 바꾸는' 길을 고르면, 박스 손질은 다음 git 받기 · 병합에 사라진다. | `infra/personas/he-team.json:94-127`(he-sim-smarttwin — apps 는 smart-twin-mcp, 선택 몫은 smart-twin-cluster 뿐) · `infra/scripts/sync-he-personas.py:133-135`(앱이 없으면 건너뛴다). 10-30 `/tools-map` 의 ste 도구(cluster_info · submit_job · set_job_sync · ste_cancel_job 등)를 묶는 운영자가 0명이다. | OB-92 에서 둘째 길을 고르면 두 가지를 청한다. he-sim-smarttwin 에 ste 선택 몫(cluster_info 는 조회, submit_job · set_job_sync 는 writes, ste_cancel_job 은 confirm)을 둔다. 기본 앱이 없어도 선택 앱만으로 운영자를 만드는 규칙을 둔다. | QA-DIGITAL-WORKER-20261030 DW-12 · 이 요청서 OB-92 |
| HP-55 | (낮음) update-all 의 챗 도구 문구가 cae00 실제와 다르다. §1 은 TOOL_MAX=0 인 박스에 '미설정 → 기본 200' 이라 적고, §7 은 '챗 창의 45% 안이면 전부 바인딩' 이라 적는다. OB-93 예산 견주기 때 틀린 말이 된다. | `infra/scripts/update-all.sh:1385-1386`(TOOL_MAX 가 0 이어도 '미설정 → 기본 200') · `:3461-3462`('대형 컨텍스트 GLM 이라 전부 실림') · `:3474`('챗 창의 45% 안이면 전부 바인딩') · `:3480-3481`('챗 창의 45%' 고정 · '챗 서버 창을 넓힌다'). 10-29 update-all 로그가 이 문구를 냈다. 10-30 에이전트 `/health` 는 tool_max 0 · tool_cut 1,379 → 209(budget 88,473)다. 에이전트 `969e723` `app.py:2296` 은 `CHAT_TOOL_SCHEMA_BUDGET` 이 있으면 그 값을 예산으로 쓴다. | §1 은 박스 값이 0 이면 'TOOL_MAX=0 그대로(무캡)' 로 적는다. §7 챗 도구 줄은 `/health` tool_cut 의 budget 값과 그 출처(`CHAT_TOOL_SCHEMA_BUDGET` 이면 그 값, 없으면 창의 45%)로 바꾸고, '전부 바인딩' 과 GLM 권고 문구를 걷는다. | 01-HWAXPortal HP-07 남은 문구 · 포털 `docs/request-1029` W-2 · 이 요청서 OB-93 |
| HP-56 | (낮음 · 선택) '전작' · '후속' 이 어휘표 `search` 에는 있는데 코어 규칙 발동 낱말(`rule_words`)에는 없다. | `backend/config/core_vocab.json:9-12`(rule_words 15개에 없다) · `:23`(search 에는 있다). 10-30 OT-05 는 그래도 코어로 갔다. | rule_words 에 둘을 더할지 본다. 심의 낱말을 가로채지 않는지 게이트웨이 검색 평가와 함께 본다. | QA-CHAT-QWEN-20261030 5.2 #4 |
| HP-42(다시) | (낮음 · 조건부) 포털 웹 챗에 MCP Apps 패널 호스트가 없어, 파일이 끼는 워크플로우는 웹으로 돌아가야 한다. 에이전트 HA-20(2단계)이 먼저다. | 에이전트 `969e723` `app.py` 와 포털 `backend/app` · `frontend/src` 에 `ui_resource` 가 0건이다(HA-20 미반영). 게이트웨이 중계(HG-07)는 들어왔다(`44f4b8d` `gateway.py:4821` `_ui_meta`). | 2단계로 남긴다. 에이전트 HA-20(ui_resource SSE)이 들어오면 포털 패널 호스트를 다시 청한다. 지금은 답이 필요 없다. | 01-HWAXPortal HP-42 · reflection-1028/01 보류 · 개발 checklist(request-1027) '[~] HP-42' |
| HP-21(다시) | (낮음 · 조건부) 전문가 카드 본문 검색 스위치를 켜도 검색칸 문구가 '제목·요약에서 낱말로 찾기' 그대로다. 스위치(OB-89)가 꺼진 지금은 문구가 맞다. | `frontend/src/components/chat/AgentDeepView.tsx:323`. 개발 checklist(request-1027)는 '[~] 화면이 AIDataHub 스위치를 볼 길이 없다' 이다. | 본문 검색을 켤 때(AD-04(다시) · OB-89) AIDataHub 응답에 스위치 상태를 싣게 하고, 포털 문구를 그 칸에 맞춘다. | 01-HWAXPortal HP-21 · 90-OURS OB-89 |

### SignalForge(`d2a794d`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| SG-19 | (낮음) `search_voc` 와 `resolve_product_keyword` 가 느려, VOC 를 묻는 챗 한 턴이 길어진다. | 게이트웨이 감사(10-29 · 10-30, 도구 · ms · ok 만 읽음) — search_voc 성공 20건 중앙값 약 13.9초 · 최대 35.7초, resolve_product_keyword 성공 7건 중앙값 4.2초 · 최대 14.2초다. 코드 자리는 `mcp-server/server.py:214`(semantic_search_tool) · `mcp-server/tools/query.py:338`(`_matcher_codes`)다. | 두 도구가 느린 까닭을 보고 줄인다. 첫 호출의 시맨틱 적재인지, 매처 사전을 부를 때마다 짓는지부터 가린다(추정). SG-04(다시)와 같은 묶음으로 보낸다. | QA-CHAT-QWEN-20261029 5.5 SignalForge 행 · 포털 `docs/request-1029/signalforge-sg04-question.md` '함께 본 것' |

### KooRemapper · DynaForge(`46e4283`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| KR-23 | (중간) 챗 에이전트가 `recipe_propose` · `recipe_register` 로 올린 파이썬 레시피가 사람 검토 없이 모두에게 등록된다. 운영자 정의의 writes 에도 레시피 도구가 없어 HA-29 의 확인 카드에 걸리지 않는다(포털 몫은 HP-53). | `platform/backend/app/modules/recipes/routes.py:48-51`(propose — 로그인만 본다) · `:144-155`(register — 자동 관문을 통과하면 등록) · `platform/mcp_server/skill/kooremapper/SKILL.md:247-250`('효과를 봤으면 recipe_propose'). 10-30 게이트웨이 `/tools-map` 에 recipe_propose · recipe_register · recipe_run 이 있다. | 레시피 등록(recipe_register)을 사람 승인이나 관리자 권한으로 묶을지 답해 달라. 묶는다면 MCP 설명에 '등록은 사람이 승인한다' 를 싣는다. | TODO-20261029 R-09 · reflection-1028/04 3절 ⑤ |
| KR-01(다시) | (낮음) DynaForge 과제 검색이 허브 행의 별칭을 대조하지 않는다. | `platform/backend/app/modules/ontology/routes.py:65-67`(key · label · task_code 만 ilike 로 본다). 받기 코드 `platform/backend/app/runner/sp_core.py` · `platform/backend/app/worker/plm_sync.py` 에 alias 가 0건이라(HEAD 대조) 별칭을 담지도 않는다. | 받기가 허브 행의 aliases 를 보관하고, list_tasks 와 resolve 가 그것도 대조해 matched_by 에 alias 를 싣는다. | 04-KooRemapper-DynaForge KR-01 · reflection-1028/04 KR-01②(일부) · TODO-20261029 R-09 |
| KR-16(다시) | (낮음) list_tasks 가 key 순으로 먼저 자른 창 안에서만 순위를 매겨, 짧은 질의의 앞부분 일치가 창 밖으로 밀릴 수 있다. 행마다 match_kind 도 없다. | `routes.py:69-70`(fetch = min(1000, limit×5) 를 key 순으로 자른다) · `:91`(`_rank`) · `:105`(정렬 · 절단). 응답 항목에는 matched_by 만 있다(`:110`). | 앞부분 일치를 먼저 받거나 순위를 매긴 뒤 자르고, 행마다 match_kind(앞부분 · 낱말 경계 · 부분)를 싣는다. | 04-KooRemapper-DynaForge KR-16 · reflection-1028/04 KR-16(일부) |

### AIDataHub(`ac42bc6` — 10-18 뒤 커밋 0)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| AD-01(다시) | (중간) MX 백서 분석가 카드 154장의 1번 절이 비어, 챗 · 심의 근거에서 그 글이 빠진다. | `api_server/src/api/ingest/db_writer.py:201-202`(children 만 내려간다) — 이 파일에 subsections 는 0건이다(HEAD 대조). MX 백서 개발 답(reflection-1028/09 MW-07)이 '본문 빈 154장은 AIDataHub 평탄화 탓' 이라고 했다. | 평탄화가 subsections 도 내려가게 하고, 박스마다 색인을 다시 짓는 명령을 둔다. 일정을 알려 달라. | 10-AIDataHub AD-01 · AD-14 · TODO-20261029 R-03 |
| AD-19 | (중간) 추천 점수의 낱말 겹침 항이 '전문가 · 에이전트 · 추천 · 기록' 같은 요청 낱말에도 점수를 줘, 데이터 없는 무관한 전문가가 추천 상위에 오른다(코드 대조 추정). | `api_server/src/api/services/recommend_svc.py:54`(`_DESC_WEIGHT` 2.0) · `:65-76`(`_STOPWORDS` 에 '알려' 는 있고 전문가 · 에이전트 · 추천 · 근거 · 기록은 없다) · `:289-307`(전체 전문가를 질의 낱말 겹침으로 가점한다). 에이전트 `969e723` `app.py:2618` 은 질문 전체를 q 로 넘긴다. DW-13 에서 추천 10명 중 절반이 무관했다. | 낱말 겹침 항에서 요청 낱말(전문가 · 에이전트 · 추천 · 근거 · 기록 · 찾아)을 빼고, 기록 · 표본 신호가 0 인 전문가는 겹침만으로 상위에 오르지 않게 한다. HA-31 끝의 '추천 순위 까닭' 몫은 이 행이 받는다. | QA-DIGITAL-WORKER-20261030 DW-13 · 이 요청서 HA-31 · 포털 `docs/request-1029` context-notes 0절 |
| AD-21 | (중간) 전문가를 만들거나 고치면 저장은 되는데 500 을 돌려줘, 운영자 정의 동기화가 첫 건에서 멈춘다. | `api_server/src/api/routes/agents.py:185` · `:206`(저장 뒤 `AgentOut.model_validate`). 500(ValidationError)은 10-28 운영자 동기화 실측이고, 까닭 줄은 다시 재지 않았다. 운영자 정의를 바꾸는 HP-53 · HP-54 가 이 동기화를 탄다. | POST · PATCH `/api/agents` 가 저장 뒤 500 을 내지 않게 한다. 응답 모델이 저장한 값을 받게 하거나, 받을 수 없는 값은 저장 전에 거절한다. | TODO-20261029 R-02 |
| AD-03(다시) | (낮음) '이 대화에서 분석' 의 변환이 NASCA DRM 파일을 알아보지 못하고 '파일이 손상됐을 수 있다' 고 안내한다. | `api_server/src/api/services/mcp_write_svc.py:474-478`(convert_failed · 일반 안내). `api_server/src` 에 NASCA · DRM_PROTECTED 가 0건이다. 포털 첨부 판정(HP-14 `frontend/src/components/chat/docAttach.ts:34`)은 들어와 있다. | `convert_file` 앞에서 DRM 머리를 보고 `DRM_PROTECTED` 로 따로 알린다(포털 `docAttach.ts` 의 머리 표와 같게). | 10-AIDataHub AD-03 · TODO-20261029 R-03 |
| AD-04(다시) | (낮음) 지식카드 본문 검색 스위치의 속도를 아직 재지 않아, 챗 카드 검색이 제목 · 요약만 본다. | `api_server/src/api/config.py:37-38`(`AIDH_RECORDS_Q_BODY_SEARCH`, 기본 끔). 잰 값이 오지 않았다(TODO-20261029 W-06). | dev DB 사본에서 `EXPLAIN ANALYZE` 로 본문 검색 속도를 재서 알려 달라. | 10-AIDataHub AD-04 · 90-OURS OB-89 |
| AD-05 · AD-06(다시) | (낮음) 빈 전문가(dynaforge-report)와 데모 전문가(kooremapper-modelmeta)가 전문가 목록 · 추천 후보에 남아 있다. | 10-30 포털 nginx 경유 `GET /ai-data-hub/api/agents/<키>` 가 둘 다 200 · 설명 0자 · data_types [] 다. 지우는 순서는 dev 먼저, cae00 나중이다(AD-13 답). | dev 원본에서 두 전문가와 데모 카드 3장을 먼저 지워 달라(다음 덤프로 퍼진다). 일정을 알려 달라. cae00 몫은 OB-87 이다. | 10-AIDataHub AD-05 · AD-06 · AD-13 · 90-OURS OB-87 |
| AD-07(다시) | (낮음 · 심의) agent_search 가 as_of 를 받지 않아, 심의가 그 시점 뒤에 생긴 카드까지 근거로 쓸 수 있다. 챗에서 시작한 소급 심의도 같다. | `api_server/src/api/mcp_runtime.py` 에 as_of · valid_from 이 0건이다(HEAD 대조). 믿을 날짜 칸 records.valid_from 은 이미 있다(reflection-1028/10 AD-07). | agent_search 가 as_of 를 받아 `valid_from <= as_of` 로 거른다. 에이전트 서버 HA-11 이 이것을 기다린다. | 10-AIDataHub AD-07 · 03-HWAXAgentServer HA-11 · TODO-20261029 R-03 |
| AD-20 | (낮음) 카드와 전문가를 잇는 저장소가 둘(records.agents · agent_records)이라, 추천의 근거 기록 수와 전문가 기록 목록이 어긋날 수 있다. | `recommend_svc.py:253-255`(records.agents 로 센다) · `api_server/src/api/services/agent_svc.py:338-340`(agent_records 로 목록을 낸다). | 두 저장소를 하나로 합치거나 한쪽을 정본으로 맞춘다. 추천의 기록 수와 전문가 기록 목록이 같아야 한다. | 포털 `docs/request-1029` PLAN 2.4 E-5 · context-notes 0절 |

### MX 백서(MXWhitePaper `f242254`)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| MW-01(다시) | (낮음) mxwp-mcp 가 뜰 때 API 에 닿지 않으면 꺼진 위키 도구 14개를 그대로 싣는다(열린 쪽). 감시가 MCP 를 API 보다 먼저 살리면 챗에 위키 도구가 다시 보이고, HA-08(다시)의 문구 어긋남이 드러난다. | `dist/llm-docx-toolkit/mcp/server.py:1332-1344`(`_wiki_switch`) — 닿지 않으면 `:1342-1343` 이 True 를 돌려준다. `:404` 는 그때 wiki_* 를 싣는다. 10-28 뒤 커밋은 0이고, 10-30 은 위키 도구가 0개라 잠재 위험이다. | 닿지 않으면 위키 도구를 싣지 않고(닫힌 쪽) 잠시 뒤 다시 보거나, 부를 때 꺼짐을 알면 도구 목록을 바꾼다. | 09-MXWhitePaper MW-01 · reflection-1028/09 MW-01 남은 것 · 3절 2 · TODO-20261029 R-10 |
| MW-12 | (낮음) upload_image_from_url · upload_image_base64 · insert_image_block 설명이 http 모드에서 빠진 upload_image 를 가리켜, MX 백서 운영자가 없는 도구를 찾는다. | `server.py:757` · `:793` · `:843` 이 upload_image 를 말한다. `:397-398` · `:403` 은 http 모드에서 upload_image 를 싣지 않는다. 포털 운영자 정의(`infra/personas/he-team.json:620`)가 세 도구를 writes 로 쓴다. | 세 도구 설명에서 upload_image 를 빼고 upload_image_from_url · upload_image_base64 로 안내한다. | reflection-1028/09 3절 3 |

### Datahub 플랫폼(허브 셋 — hwax-batch)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| DP-01(다시) | (높음) 허브 응답이 여전히 커서 챗 문맥과 자기검증 입력을 크게 차지한다. 이 요청서에는 DP-14 의 곁말로만 있다. | QA-CHAT-QWEN-20261030 4절 — 10만 자 넘는 응답 11건이다. 에이전트 쪽 접기는 들어왔다(`969e723` `app.py:1618-1625` · `:1909-1917`). 원천 몫은 그대로다. | objects_list 의 ref_labels 를 쪽에 한 번만 싣고, objects_summary 의 group_options 를 기본에서 빼고, object_get 의 related 를 접는다. | 12-Datahub-platform DP-01 · QA-CHAT-QWEN-20261030 4절 · 이 요청서 DP-14 |
| DP-02(다시) | (높음) FailureTrace 의 솔더 접합 불량 분류 약 82% 가 'hip' 글자 오탐이라, 챗이 내는 문제점 수가 부풀어 있다. | QA-CHAT-QWEN-20261029 5.5 — 389건 중 319건으로 10-27 과 같다. 10-30 OT-12 는 389건을 정답으로 셌고 오탐을 짚지 않았다. | 자주검증 Datahub 의 그 분류 match_pattern 에서 짧은 영문 낱말(hip · pillow 등)에 낱말 경계를 두고, FailureTrace 연결을 다시 분류한다(데이터 · 관리 입력). | 12-Datahub-platform DP-02 · 90-OURS OB-58 |
| DP-04 · DP-05(다시) | (중간) '메인 PBA' 와 한국어 마케팅명으로 resolve 하면 none 이다. | QA-CHAT-QWEN-20261029 5.5 에서 다시 쟀고 그대로 none 이었다. | DP-04 — resolve 의 포함 단계에서 질의 안에 낱말로 든 별칭을 후보로 낸다. DP-05(데이터) — 과제 · 개발코드 행에 한국어 마케팅명 별칭을, 기판 부품 행에 '메인 PBA' · '메인 기판' 별칭을 넣는다. | 12-Datahub-platform DP-04 · DP-05 |
| DP-07(다시) | (중간) failuretrace_whoami 한 번이 40초 안팎이라, '신원부터 확인' 하는 운영자 흐름이 멈춘다. | 게이트웨이 감사(도구 · ms · ok 만 읽음) — 성공 호출이 44,434 ms(10-29) · 39,206 ms(10-30)로 10-27 의 27~33초보다 길다. 같은 때 자주검증 허브 whoami 는 232~521 ms 다. | facts 를 캐시하거나 근사 건수로 바꾼다. | 12-Datahub-platform DP-07 |
| DP-08(다시) | (중간) pd_defect 행의 label · content_text 에 검출자 · 작업자 이름이 그대로 실려 챗으로 나간다. HG-22 는 칸 이름 · 메일 · 계정 · 사설 IP 꼴만 가려 글 속 이름은 걸리지 않는다. | 10-27 온톨로지 시험 N-18 · 개발 결정 D-4(원천에서 가린다 — reflection-1028/03 HA-25). 게이트웨이는 자유 글 속 이름을 꼴로 가르지 않는다(`44f4b8d` `gateway.py:606-608` 주석). | FailureTrace 출력에서 사람 이름 칸을 가린다. 4절의 원천 쪽 개인정보 요청(AR-10 · PA-20)과 같은 묶음으로 보낸다. | 12-Datahub-platform DP-08 · 03-HWAXAgentServer HA-25 · 90-OURS OB-07 |
| DP-06(다시) | (낮음) graph_neighbors 의 최상위 truncated 가 간선을 다 받아도 참이라, 챗이 '관계가 잘렸다' 고 답한다. | QA-CHAT-QWEN-20261029 5.5 'DP-06 그대로' · QA-DIGITAL-WORKER-20261030 DW-01 답도 truncated 를 밝혔다. | 초점 노드의 간선이 잘렸을 때만 참으로 하고, 이웃 쪽에 더 있는 것은 다른 칸으로 낸다. | 12-Datahub-platform DP-06 |
| DP-09(다시) | (낮음) 코어 공백(시험항목의 부하 칸 · 낙하 시험 한 항목의 검출 고장모드 · tests_part 0건)이 챗 답의 빈칸이 된다. | 10-27 뒤 다시 잰 기록이 없다. 10-30 OT-07 · 10 · 11 은 PASS 라 당장의 영향은 작다. | 그대로 남았다고 알린다(데이터 · 관리 입력). | 12-Datahub-platform DP-09 |

### ARP

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| AR-1 ~ AR-4(다시) | (중간 — 16 문서 안의 심각도는 그대로) ARP 는 코어를 받지 않아 과제명 · 과제코드로 모델을 찾지 못하고(modelMatch none), 못 찾은 까닭도 하나뿐이다. | [16-ARP-ODBHub-core-ontology.md](16-ARP-ODBHub-core-ontology.md) 2절 AR-1 ~ AR-4(10-29 실측) · QA-DIGITAL-WORKER-20261030 DW-21 · QA-CHAT-QWEN-20261029 OT-08. 이 요청서 6절은 AR-9 · AR-10 만 16 문서에 이어 붙인다고 적었고, 16 문서는 아직 보내지 않았다. | 16 문서의 AR-1 ~ AR-4(과제명 · 과제코드로 모델 찾기 · 못 찾은 까닭 넷 · 받기 상태)를 AR-9 · AR-10 과 같은 묶음으로 보낸다. 보내기 전에 사람이 16 문서를 한 번 읽는다(QA-CHAT-QWEN-20261029 6절 O-9). | 16-ARP-ODBHub-core-ontology AR-1 ~ AR-4 |

### 클러스터 · SmartTwin(stcx)

| # | 무엇이 | 근거 (파일:줄) | 할 일 | 출처 |
|---|---|---|---|---|
| PA-16 · PA-19(다시) | (중간) stcx SmartTwinMCP 운영 배포와 `extra_scenario_overrides` 의 environment 덮어쓰기 잠금이 아직이다. OB-92 의 '잇기' 길을 지금 열면, 운영자 writes 의 낙하 도구로 컴퓨트 노드에서 임의 명령이 돌 수 있다. | 14-Partner-apps PA-16 · PA-19(10-27, 답 없음 — TODO-20261029 W-02 대기) · 포털 `aec8e29` `infra/personas/he-team.json:116`(he-sim-smarttwin writes 에 fullangle_drop_simulation · single_drop_simulation). 이 요청서 OB-92 에 이 선행 조건이 적혀 있지 않다. | PA-16(:5013 운영 배포)과 PA-19(environment 잠금)를 다시 묻는다. OB-92 의 잇기 길은 둘이 끝난 뒤에 연다(5절 OB-34 · OB-25). | 14-Partner-apps PA-16 · PA-19 · 이 요청서 OB-92 |
