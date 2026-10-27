# hwax-risk — 수정 요청 (2026-10-27 · cae00 운영 기준)


요청 HWAX Portal 운영(cae00) · 대상 저장소 HWAXRisk(리스크 심사 앱 — cae00 런타임 `heax_app_hwax_risk` :9116, 소스 사본 `HEAXHub/var/integration_workspaces/hwax-risk/upstream/`) · 기준 판 리스크 앱 SIF `c3f46ba`(10-14, 파일:줄은 SIF 안 `/app/backend/app/` 기준)에 10-25 판 반영분(8절 커밋)을 빼고 남은 것만 적었다. 10-27 에 cae00 작업 사본(`HEAXHub/var/integration_workspaces/hwax-risk/upstream`, HEAD `ecad8c8` 10-21 — 8절 커밋을 모두 담는다)으로 다시 본 행은 근거 칸에 그 줄을 적었다 · update-all 로 받는 플랫폼: 예(HEAXHub 앱 SIF 로 받는다 — update-all 의 HEAX 구획과 update-collab 의 리스크 SIF 교체).


항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것(S · A · M · X · P 로 시작하는 짧은 번호)은 원문 번호에 '-' 를 넣어 적었다(예 10-25 시험 M-14).


바라는 것은 하나다. SSO 로 들어온 사람의 자격이 자동으로 이어져, 서비스 키 없이도 그 사람 시야로 심사가 끝까지 도는 것이다.


**한 줄**


- cae00 에는 서비스 쓰기 키가 없어 ReportArchive 반영이 조용히 pending 으로 남는다. 과제 owner 자격으로 RA 에 쓰는 것이 먼저다(RK-01).


- Claude(MCP)에서 캡처할 때 쓰는 PAT 에 청중 `step-forge` 가 없다. 그래서 단위 검문(G6)이 막힐 수 있다(RK-02).


- 웹으로 들어온 사람은 아직 PAT 를 손으로 등록한다. 자동 등록의 화면 몫이 남았다(RK-03).


- 설정 화면이 원인과 다른 문구를 보여 운영자가 이관 문제로 오해한다. `cred.key` 폴백도 화면에 크게 보이지 않는다(RK-05 · RK-06).


**건수**


| 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|
| 2 | 3 | 2 | 2 | 0 |


## 1. 높음 — 먼저 고칠 것


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| RK-01 | RA 쓰기가 서비스 쓰기 키 하나에만 묶여 있다. 키가 없는 cae00 에서는 RA 반영이 조용히 pending 으로 남는다. | `ra_client.py:327-339` 는 `HWAXRISK_PORTAL_PAT_RW` 만 쓴다(읽기 PAT 와 섞지 않는다). 작업 사본 HEAD `ecad8c8` 에서도 그대로다(그 판 기준 `:353-366`, 10-27 확인). 키가 없으면 `available=False` 이고 `external_sync` 가 pending 이다. 계획서 `PLAN.md:180` 은 RA 저장을 M-4 로 미뤘다. 게이트웨이 `per_user_sso.reportarchive` 는 10-03 부터 켜져 있고 RA `/api/auth/sso` 도 정상이다. | RA 쓰기를 과제 owner(또는 잡을 만든 사람)의 자격으로 한다. 게이트웨이를 거쳐 그 사람 이름으로 RA MCP 를 부르는 길이 이미 있으니 그 길을 쓴다. | 리스크 자격 R3 요청 1 |
| RK-02 | 설정 화면의 PAT 발급 버튼이 청중 `mcp-gateway` 하나로만 발급한다. 게이트웨이 REST 다리는 청중 `step-forge` 를 요구한다. | 위임 캡처의 REST 채널을 사람 PAT 로 다리(`/api/step-forge`)에 잇는 길은 10-25 판에 들어 있다(`0e65f3a` · `9ee4776` · `2c551b5`). 실제 캡처로 단위 검문(G6)이 「모름」이 아닌지는 아직 확인하지 못했다. 작업 사본 HEAD `ecad8c8` 에서도 버튼 쪽 `frontend/src/api/portalPat.ts:26` 은 `audiences: ["mcp-gateway"]` 이고 `SettingsPage.tsx:271` 안내도 같다. MCP 경로의 교환 명세 `backend/app/routes.py:69` 에만 `step-forge` 가 들어 있다(10-27 확인). | 발급 청중에 `step-forge` 를 더해 교환 명세(`routes.py:69`)와 맞춘다. 서비스 키는 마지막 폴백으로만 남긴다. 고친 뒤 Claude 캡처 한 번으로 G6 을 확인한다(7절). | 리스크 자격 R2 |


## 2. 중간


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| RK-03 | 웹 경로로 들어온 사람의 포털 PAT 를 자동으로 등록 · 갱신하지 않는다. | MCP 경로 자동 등록과 웹용 백엔드 칸(`GET /api/me` 의 `portal_pat.auto` · `PUT /api/me/portal-pat-auto`)은 반영됐다(`491895c` · `5d47690`, 포털 `12862e3`, 게이트웨이 `c5ae578`). 웹 사용자는 아직 「포털에서 발급해 등록」 을 손으로 누른다. | 등록된 PAT 가 없거나 남은 수명이 `credential_margin_s` 밑이면 그 버튼이 하는 일을 자동으로 한다(같은 scope · aud · ttl, aud 에는 RK-02 의 `step-forge` 도 넣는다). 사용자가 끌 수 있게 한다. 만료 정책은 D-26(자격 만료는 멈추고 알린다) 그대로다. | 리스크 자격 R1 요청 1 · 3 |
| RK-04 | RA 반영이 안 된 사실과 까닭이 진행판 · 과제 화면에 보이지 않는다. | 과제 · 대상 응답과 `risk_get_coverage` · `risk_next_step` 에 `external_sync` 요약(`sender_unwired`)을 싣는 것은 반영됐다(`0966b41`). 화면 표시는 아직이다. | 진행판과 과제 화면에 「RA 반영 안 됨 — 사유」를 보인다. RK-01 이 들어오기 전까지 특히 필요하다. | 리스크 자격 R3 요청 2 |
| RK-05 | 운영 박스에서 `cred.key` 개발 폴백을 쓰는 중이어도 설정 화면에 크게 보이지 않는다. | 10-14 첫 PAT 등록 때 앱이 `<data>/cred.key` 를 새로 만들었다(암호문과 키가 같은 폴더). 기동 로그 안내 · 키 값을 그대로 옮기는 명령 · 절차서 7-1 은 반영됐다(`8d672c7` · `cdc5dbd`, 포털 `4a7ed81`). cae00 은 10-16 에 같은 값을 `HWAXRISK_CRED_KEY` 로 옮겼다. | 폴백 키를 쓰는 중이면 설정 화면에 크게 알리고, 그 값을 `HWAXRISK_CRED_KEY` 로 옮기는 절차를 안내한다. | 리스크 자격 R5 요청 2 |


## 3. 낮음 · 선택


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| RK-06 | 설정 화면이 `secrets_valid=false` 의 까닭을 나누지 않고 「저장된 비밀이 이 호스트에서 풀리지 않습니다」 하나로 보인다. | `main.py:119` `secrets_valid = box_match and all(k in secrets for k in config.SECRET_KEYS)` · `config.py:29-31` `SECRET_KEYS`. `origin.json` 은 `hostname: cae00` 이라 이관 문제가 아니다(10-14 기준 cae00 은 ⓑ · ⓒ). 까닭을 나눈 `GET /api/me` 의 `box.reasons` 는 반영됐다(`8d672c7` · `158f89e`). 설정 화면은 아직 고정 문구다. | 화면에서 ⓐ `origin.json` 호스트 불일치(이관 직후) ⓑ 빠진 키 이름(값 말고 이름만) ⓒ `cred.key` 개발 폴백 사용 중을 나눠 보인다. | 리스크 자격 R5 요청 1 |
| RK-07 | `/api/health` 의 warnings 에 backup_unencrypted 가 늘 뜬다. 의도로 비워 둔 경우 끄는 방법이 문서에 없다. | 10-25 `:9116/api/health` warnings 가 ['backup_unencrypted'] 다. 백업 암호화 키 `HWAXRISK_BACKUP_KEY`(age 공개키)를 운영 박스에 둘지는 아직 정하지 않았다(우리 몫 결정, 90-OURS-box-todo.md OB-17). | 운영에서 백업 키가 기본 전제인지 알려 준다. 의도한 설정일 때 이 알림을 끄는 방법을 문서화한다. | 10-25 피드백 HX-4 · 10-17 수정 목록 D5 |


## 4. 질문 · 확인 요청


| # | 묻는 것 | 왜 | 출처 |
|---|---|---|---|
| RK-08 | `risk_concurrency = 2` 를 심의 동시 한도 6 에 맞출지 정해 달라. | 심의 한도는 10-22 에 2 에서 6 으로 올렸다. 포털 업무 절차 설정의 주석은 「심의 · HWAXRisk 와 같은 2」 라고 적고 있다. 맞춘다면 포털 주석도 함께 고친다(6절). | 심의 멈춤 §3 |
| RK-09 | 지금 판의 필수 비밀 키 목록이 무엇인가. | 10-14 기준 `config.py:29-31` `SECRET_KEYS` 는 5종(`HWAXRISK_PORTAL_PAT` · `HWAXRISK_PORTAL_PAT_RW` · `HWAXRISK_HEAX_SERVICE_PAT` · `HWAXRISK_AIDH_API_KEY` · `HWAXRISK_CRED_KEY`)이다. 10-17 기록은 `HWAXRISK_PORTAL_PAT` 를 선택 키로 본다. RK-06 화면의 「빠진 키 이름」 과 박스 서비스 키 결정(90-OURS-box-todo.md OB-18)이 이 목록에 걸린다. | 리스크 자격 '지금 상태' · 10-17 수정 목록 5절 |


## 5. 결정 필요 (사용자)


없음. RK-01~RK-03 이 들어오기 전에 박스 서비스 키를 임시로 채울지, 운영 박스에 백업 암호화 키를 넣고 남은 `cred.key` 를 치울지는 박스 결정이다. 앱 쪽 할 일이 없어 우리 몫 문서(90-OURS-box-todo.md OB-18 · OB-17)에만 적었다.


## 6. 다른 플랫폼과 맞물린 것


| 맞물린 것 | 이 플랫폼 몫 | 다른 쪽 몫 (같은 폴더의 요청서) | 출처 |
|---|---|---|---|
| PAT 청중 | RK-02 · RK-03 — 발급 청중에 `step-forge`. | HWAXMcpGateway 요청서(02-HWAXMcpGateway.md) — 할 일 없음, 다리의 사이트별 aud 규칙은 그대로 둔다. HWAXPortal 요청서(01-HWAXPortal.md HP-15) — 같은 꼴로 챗 PAT 에 aud `simflow` 를 더한다(SimFlow 업로드). StepForge 요청서(05-StepForge.md) — 할 일 없음. | 리스크 자격 R2 · MCP 업로드 U2 |
| RA 쓰기를 사람 자격으로 | RK-01 — owner 자격으로 쓴다. | HWAXMcpGateway 요청서(02-HWAXMcpGateway.md) — 할 일 없음, `per_user_sso.reportarchive` 는 10-03 부터 켜져 있다. ReportArchive 요청서(11-ReportArchive.md RP-01) — SSO 계정의 홈 워크스페이스 보장이 아직이라, 사람 이름으로 쓴 보고서가 개인함에 쌓일 수 있다(추정). | 리스크 자격 R3 · RA SSO §2 · 포털 8차 §2-2 |
| SIF 대조 · `knobs.env` | 없음. | HEAXHub 요청서(06-HEAXHub.md HH-02 · HH-04 · HH-05) — 부분 배포가 `SHA256SUMS` 를 덮어 리스크 앱 SIF(204MB)가 대조 없이 깔린 적이 있다(10-15). 10-17 리스크 앱 부분 배포도 목록을 덮어 `step_forge.sif` 줄이 빠졌다. 우리 몫 문서(90-OURS-box-todo.md OB-77) — 박스는 `knobs.env`(`HWAXRISK_REVIEW_ENABLED=0`)를 운영 값으로 먼저 두었다. | update-all 안전 U7 · U8 · U9 · 10-17 수정 목록 X-6 |
| 업무 절차 동시 한도 주석 | RK-08 — 값을 정한다. | HWAXPortal 요청서(01-HWAXPortal.md HP-45) — `backend/app/config.py:212` 근처 `procedures_concurrency = 2` 와 그 주석. | 심의 멈춤 §3 |
| 리스크 앱 사람 자격 절차서 | 없음. | HWAXPortal 요청서(01-HWAXPortal.md HP-38) — `docs/risk-credentials/server-setup.md` 의 4-7 · 38 · 47 · 32행 기대값과 `docs/risk-claude-engine/checklist.md:12` 해시를 지금 Drive latest(스키마 5 · 도구 31종)에 맞추고, 확인 ④ 경로를 인스턴스 안 `/app/backend/scripts/rr_gateway_check.py` 로 바꾼다. | update-all 안전 U10-4 · 10-17 수정 목록 3-1절 |
| 챗의 패널 도구 숨기기 | 없음(알림). | HWAXAgentServer 요청서(03-HWAXAgentServer.md HA-05) — 거부 목록에 `*panel*` 무늬를 쓰지 않는다. 쓰면 `risk_list_panels` 가 걸린다. | MCP 업로드 M-0 |


## 7. 다시 볼 시험


| 시험 | 언제 | 통과 기준 |
|---|---|---|
| Claude 캡처 | RK-02 가 들어온 뒤. | Claude 에서 StepForge 과제를 한 번 캡처했을 때 단위 검문(G6)이 「모름」으로 막히지 않는다. |
| RA 반영 | RK-01 이 들어온 뒤. | 사람 자격으로 돈 잡의 `external_sync` 가 pending 으로 남지 않고, RA 에 그 사람 이름으로 들어간다. |
| 박스 반영 | 새 SIF 를 받은 뒤. | `./infra/scripts/update-collab.sh --check` 가 리스크 앱 SIF 해시 · 스키마에 이상 없음을 낸다. 앱 설정 화면의 「이 박스」 · 「러너」 칸과 Claude `risk_next_step` 의 자격 표시가 맞다. |
| 백업 알림 | RK-07 과 백업 키 결정(90-OURS-box-todo.md OB-17) 뒤. | `:9116/api/health` warnings 가 정한 설정과 맞다. |


## 8. 이 문서에서 뺀 것


- R1 의 MCP 경로 자동 등록 · 서비스 시야로 말없이 내려가지 않기 · 웹용 백엔드 칸 — 반영됐다(`491895c` · `5d47690`, 포털 `12862e3`, 게이트웨이 `c5ae578`).


- R2 의 REST 다리 연결과 서비스 키 마지막 폴백 — 반영됐다(`0e65f3a` · `9ee4776` · `2c551b5`). 청중 몫만 RK-02 에 남겼다.


- R3 의 응답 요약 `sender_unwired` — 반영됐다(`0966b41`). 화면 몫만 RK-04 에 남겼다.


- R4 — 10-27 정리로 빠졌다(반영 · 철회).


- R5 의 `box.reasons` · 기동 로그 안내 · 키 옮기는 명령 · 절차서 7-1 — 반영됐다(`8d672c7` · `158f89e` · `cdc5dbd`, 포털 `4a7ed81`).


- 심의엔진 요청의 hwax-risk 3건 — 10-27 정리로 빠졌다(반영).


- `cred.key` 값을 `HWAXRISK_CRED_KEY` 로 옮기기 — 10-16 에 박스에서 했다(같은 값이라 등록된 PAT 가 그대로 풀린다).


- 리스크 원장 과제 등록 · 공개 범위 · 요구 등록 같은 실사용 설정 — 실사용 팀과 우리 몫이다(심의엔진 5절, 90-OURS-box-todo.md OB-38).


- 박스 서비스 키 임시 채우기(리스크 자격 '운영 쪽 결정 대기')와 백업 암호화 키 · 남은 `cred.key` 처리(10-17 수정 목록 D5 · 10-25 피드백 HX-4 의 박스 몫) — 박스 결정이라 결정 칸에서 뺐다(90-OURS-box-todo.md OB-18 · OB-17).


- 10-25 업데이트 때 리스크 비우기 깃발 정리 — 박스에서 끝났다.
