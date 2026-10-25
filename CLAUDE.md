# HWAX Portal — 에이전트용 안내

사내 시스템 SSO 브로커 허브 + AI 챗/심의. FastAPI(백엔드) + React/Vite(프론트),
apptainer 인스턴스로 뜬다.

> 전역 `~/.claude/CLAUDE.md` 의 규칙(생각 먼저·최소 구현·수술적 변경·테스트 후 완료·
> 한국어 문장은 마침표로 끝)이 그대로 적용된다. 이 문서는 **이 리포에만 해당하는 것**을 적는다.

## 먼저 읽을 것

**[docs/gotchas.md](docs/gotchas.md)** — 실제로 사고가 났던 함정들이다. 포트킬 오살,
`git status` 절단으로 남의 작업 무효화, dev 에서 `deploy-all` 실행 시 리포 리셋,
e5 임베더 코사인 오독. 짐작으로 피할 수 있는 것들이 아니다.

## 박스마다 경로가 다르다 — 절대경로를 박지 마라

| 박스 | 리포 루트 |
|---|---|
| dev (smarttwincluster) | `/home/koopark/claude/<Repo>` |
| **cae00** | **`/home/koopark/Projects/<Repo>`** |

스크립트·설정·매니페스트 전부 **상대경로**로 쓴다. 앵커는 그 파일이 속한 리포 루트이고,
루트는 파일 위치에서 유도한다.

```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"      # bash
Path(__file__).resolve().parents[2]                          # python
```

형제 리포는 `../<Repo>` 로 닿는다. 절대경로를 박으면 cae00 에서 **조용히** 깨진다.

## 클러스터는 둘이다 — `ste`(24대)와 `stcx`(356대)

| 이름 | 무엇 | 쓰는 곳 |
|---|---|---|
| **ste** | **24대** 클러스터(`smart-twin-cluster-26`, 헤드 `icn401-0116-h01`) **이자** 그 위에 도는 SmartTwinExplorer 웹 | 웹 해석 시스템 |
| **stcx** | **356대** 클러스터. 공개 호스트 `stcx.sec.samsung.net` | 전각도·단일 낙하(SmartTwinMCP) |
| ~~stc~~ | ste 를 부르던 **옛 이름**. 클러스터 이름으로 쓰지 않는다 | `ssh stc` **접속 별칭**으로만 |

규모가 판별 기준이다 — **24대면 `ste`, 356대면 `stcx`.** 이름이 한 글자 차이라 사람도
에이전트도 틀리고, 틀리면 그 위에서 내린 설계 판단이 통째로 어긋난다(실제로 하루에 세 번
뒤집혔다). 기계 가드는 `backend/tests/test_cluster_naming.py` 가 세 리포를 가로질러 본다.

**면제 셋** — `ssh stc` 계열 접속 별칭(바꾸면 배포가 깨진다), `stc-` 잡 ID 접두사,
그리고 날짜가 박힌 기록 파일(`context-notes.md`·`checklist.md`·심의 예제 — 그때의 사실을
적은 로그라 다시 쓰면 기록을 위조하는 셈이다).

배선 전모는 `docs/cluster-wiring/` 에 있다.

## 띄우기

```bash
./infra/scripts/start.sh      # 없는 것만 띄운다(멱등)
./infra/scripts/status.sh
./infra/scripts/restart.sh    # 스택 전체 — routes.env·infra/.env 를 다시 읽는다
```

포털만 다시 띄우려면 인스턴스 하나만 내리고 `start.sh` 를 다시 부른다. 코드는
`$REPO_ROOT:/workspace` 로 **바인드 마운트**라 SIF 재빌드가 필요 없다.

```bash
apptainer instance stop hwax_portal && ./infra/scripts/start.sh
```

프론트를 고쳤으면 `cd frontend && pnpm build` 가 먼저다 — 컨테이너는 `frontend/dist` 를 낸다.

| 포트 | 무엇 |
|---|---|
| 8723 | 포털 백엔드(SPA 도 여기서 낸다) |
| 5283 | Vite 개발 프록시 |
| 9009 | Agent Server (챗·심의 SSE) |
| 9110 | MCP 게이트웨이 |

## MCP

`.mcp.json` 이 리포에 있다(박스 경로에 안 묶이게). 토큰은 **환경변수로** 준다.

```bash
export HWAX_GATEWAY_PAT="<포털 /auth/pat 로 발급한 PAT>"
export HWAX_GATEWAY_URL="http://127.0.0.1:9110/mcp"   # 기본값이라 보통 생략
```

⚠ **도구가 있는지는 소스가 아니라 게이트웨이 `tools/list` 로 확인한다.** 앱 소스에
있어도 배포된 SIF 가 낡으면 게이트웨이에 안 뜬다 — 실제로 `unknown tool: intake` 로
한 번 터졌다(docs/upload/context-notes.md D-8).

## 심의 파이프라인

정본은 **`infra/pipeline/*.js`** 다. `.claude/workflows/` 는 사본이고 gitignore 다.

```bash
./infra/scripts/sync-workflows.sh --check   # 어긋난 것만 보고(종료코드 1=어긋남)
./infra/scripts/sync-workflows.sh           # 정본 → 사본
```

`update-all` 이 이 동기화를 포함한다. **JS 를 고쳤으면 sync, 파이썬(`deliberation.py`)을
고쳤으면 agent-server 재기동**이다 — 둘은 반영 경로가 다르다.

```bash
cd ../HWAXAgentServer && ./start.sh -d      # 재기동(백그라운드, 로그 agent-server.log)
```

## 이 리포에서 하지 않는 것

- **ReportArchive 리포에 커밋·push 하지 않는다.** federation 자동화의 제외 대상이다.
  API 로만 쓴다. 자세한 이유는 gotchas 참조.
- **dev 박스에서 `deploy-all-from-drive.sh` 를 돌리지 않는다.** 미푸시 커밋이 날아간다.
  빌드만 시험하려면 `build-all-to-drive.sh` 를 쓴다.
- 내부 IP·토큰·비밀번호를 추적 파일에 적지 않는다. 이 리포는 GitHub 에 있다.

## 문서

| 주제 | 위치 |
|---|---|
| 함정·사고 기록 | `docs/gotchas.md` |
| cae00 배포(update-all 전 읽기 전용 사전 점검 `infra/scripts/update-preflight.py` — 받기 전엔 `git show origin/main:… \| python3 -`, 10-25) | `docs/cae00-deploy-guide.md` |
| 챗 업로드 목적지 라우팅 | `docs/upload/` (PLAN·checklist·context-notes) |
| 심의 품질·방법 메뉴 | `docs/deliberation-quality/` |
| 띵킹 모드(답할 수 있는 전문가만 각자 답한다) | `docs/thinking-mode/` |
| 설계 리스크 심사(계획·결정, **심사용 ECAD·MCAD 능력 정리** `cad-capabilities.md`·전체 카탈로그) | `docs/design-risk-review/` |
| 데이터 /data 통합·경로 레지스트리·DB 동기화 | `docs/data-migration/` (PLAN·checklist·context-notes) |
| 업데이트 이력(팝업·`/updates` 페이지, 항목 추가법) | `docs/changelog.md` |
| 전문가 페르소나 챗 | `docs/persona-chat/` (PLAN·checklist·context-notes) |
| 전문가 조직도·HE팀 MCP 운영자·심층 보기 | `docs/org-chart/` |
| 소속·허가 기반 접근(권한) | `docs/access-control/` |
| 심의 UX 7건(좌석 조직도·도구 영역·VOC 먼저·되묻기·관계도·이어하기) | `docs/delib-ux/` (PLAN·checklist·context-notes) |
| 토큰 하나로 하위 전부(포털 권한으로 범위 결정)·REST→MCP | `docs/one-token/` (PLAN·checklist·context-notes) |
| 클러스터 배선(ste=24대 웹·MCP, stcx=356대 낙하·DynaForge, 포털 SSO) | `docs/cluster-wiring/` (PLAN·checklist·context-notes) |
| ste × cae00 운영(update-all 1회 셋업·사용자 PC Claude MCP 연결·터널·시크릿·파일 경로) | `docs/ste-cae00/` (PLAN·checklist·context-notes) |
| ste(24대) 전각도 낙하 — 드라이버 앱·preflight·취소 전파 | `docs/ste-fullangle/` (PLAN·checklist·context-notes) |
| AI Ready Portal 연결(ARP_HOST 한 줄 → 타일 주소·게이트웨이 ARP_BASE, 포털 경유는 보류) | `docs/arp-binding/` (PLAN·checklist·context-notes) |
| 서비스별 접속 이력(로그인·타일 진입 원장, 정문 요청을 계정과 잇는 연결 ID, 관리자 '접속 이력') | `docs/access-history/` (PLAN·checklist·context-notes) |
| 게이트웨이 감사에 호출 IP·자격(via) — 누가 어디서 어떤 도구를 불렀나 | `docs/gateway-audit-ip/` (PLAN·checklist·context-notes) |
| 하위 서비스 사람별 연결(RA·TestScope 둘 다 토큰 등록 ↔ ste 방식 위임을 설정 한 줄로 고른다 — 비밀이 비면 토큰 등록; RA·TestScope 요청서·서버 설정; **10-20 MatNexus** — 그쪽이 위임 창구를 이미 갖춰 게이트웨이 `PER_USER_SSO_APPS` + `<접두>_MCP_URL` 설정만 · **FMEA Agent** 요청서, 권한표 · 숨김 타일 미리; **10-21 — MatNexus · FMEA 는 토큰 등록(외부 연결 `connect:`)으로 바뀜**) | `docs/sso-delegation/` (PLAN·checklist·context-notes·ra-request·testscope-request·**fmea-request**·server-setup) |
| 외부 연결을 설정만으로(토큰 등록 플랫폼을 박스 권한표 `access.local.yaml` 의 `connect:` 한 블록으로 — 빌드 · 코드 · 재기동 0, 첫 대상 FMEA Agent · MatNexus, 사용자 결정 10-21 셋 — 토큰 등록만 · 새 플랫폼은 주인 확인 안 함 · 빌드 없음; 포털 `/auth/connections/ext`(등록은 세션 + CSRF 만) · 합성 권한 `feat:connect` · 설정으로 그리는 카드 하나, 게이트웨이는 선언을 정책과 한 응답으로 받아 목록 전용 세션 · 사람 토큰으로만 호출 · 닫힌 쪽 권한 · 이름 겹침은 선언 쪽만 접두 · `/health` `conn_platforms`; cae00 반영은 사람 — sso-delegation server-setup C · D) | `docs/ext-connect/` (PLAN·checklist·context-notes·request) |
| 심의 엔진 변경(S26U 실사용 피드백 24건 — 버린 근거를 숨기지 않는다·봉인 심사·의장 전사 상한·대기 큐, 결정 D-1~D-16) | `docs/delib-engine-feedback/` (PLAN·checklist·context-notes) |
| 8·9·10차 변경 요청(SSO 소속 매핑·관리자는 원장만·`access.local.yaml`·ARP 타일 핸드오프·NO_PROXY·게이트웨이 조건부 등재, 결정 D-1~D-13) | `docs/change-request-8-10/` (PLAN·checklist·context-notes) |
| 리스크 심사 재설계(전 전문가가 자기 지식카드 전부로 검토 — 카드 대조는 혼자 먼저·토의는 쟁점만, 마일스톤 M0~M4, 문제 250건 색인·상세 설계서 일곱 편; **M1 완료** — 패널 수리·Claude 입구·1백만 토큰 기준 글자 잘림 해소, 패널 방식은 새 방식과 함께 남긴다 D-24; **M2 승인**(D-32); **M3 완료·올림**(10-15, 리스크 앱 main `a368c86` · 스키마 v5 · 도구 31종 — 전원·거르기·쟁점 패널·종합 보고서·사슬, 실행 계획 `M3.md`, 화면 요청서 `m3-frontend-request.md`, **거르기 표 승인 10-17**(D-56 — 새 검토 잡부터 거른다), 남은 것 M4 — cae00 M3 실주행 수치 뒤)) | `docs/risk-review-redesign/` (PLAN·M2·**M3**·checklist·context-notes·problems·**truncation**(잘림 해소 요약)·**server-setup-m1·m2·m3**(cae00 절차)·reference/(설계서·`m2-*`·`m3-*` 걸음별 상세)) |
| 리스크 심사를 20만 토큰 창에서(지식카드 누락 0 · 멈춤 0 — 넘치면 나눠 여러 번 부른다, 재설계 D-22 뒤집기, dev 실측 32명 · 5,716장; **스위치 없음 — 에이전트 서버의 창 값에서 저절로**(W-D7, GLM 5.3 Flash 확정); **W1 ~ W4 올림**(10-21) — 카드 조각은 엔진 run 안에서(앱에는 한 카드 = 한 행) · 큰 단위는 카드를 단위에 맞게 조각 · 카드 밖 · 입력 결손은 훑기에 걸린 카드를 창까지(`must_full`, 넘치면 쪽) · 셀 커버리지와 불변식 G10 · 품질 `[누락 0 증명]` 줄 · 패널 긴 절은 인용 둘레 · 좌석 `get_record_sections`; 남은 것 W5 cae00 A/B(사람 — `server-setup.md` 4절) · 호출 어림 보정 · 요약 계층) | `docs/risk-200k/` (PLAN·checklist·context-notes·**server-setup**(cae00 절차)) |
| 리스크 심사 앱 사람 자격(SSO 로 들어온 사람의 PAT 가 저절로 — 웹은 화면 자동, Claude 는 게이트웨이 토큰 교환 `POST /auth/pat/exchange` · 패널도 서비스로 안 내려감 · 캡처 REST 는 게이트웨이 step-forge · 필수 키는 CRED_KEY 하나, 결정 U-1~U-4) | `docs/risk-credentials/` (PLAN·checklist·context-notes·frontend-request) |
| 포털 UI 개선('세련되지 못하다' 원인 넷·결정·단계 0~4, 리뷰 방법은 임시 포털 캡처) | `docs/ui-refresh/` (PLAN·checklist·context-notes) |
| 리스크 심사를 Claude 로도(엔진의 LLM 자리에 외부 응답자 — Claude Code 워크플로가 MCP 로 과제를 집어 답한다, **기본 꺼짐**·잡마다 반출 동의, 실제 Claude 실행 시험은 하지 않음 — 사용자 결정 10-15; **X-1 ~ X-4 완료 · 올림**(10-15 ~ 10-16 — 엔진 `faadf28` · `53082a4` · 리스크 앱 `54c4385` · 포털 워크플로 `hwax-risk-claude.js` · `56adf3b`, 기본 꺼짐 — cae00 에서 켜는 법은 `docs/risk-review-redesign/server-setup-m3.md` 8절)) | `docs/risk-claude-engine/` (PLAN·checklist·context-notes) |
| Claude 길 심의도 GLM 길과 같은 기능으로(사용자 요청 10-21 — 좌석 자유 조회를 **글 왕복**으로: 응답자가 `CALL` 줄을 적고 **엔진이 실행**한다(tool_mode `tools`) · 일반 MCP 심의는 과제 머리 `job_id` + 워크플로 `jobId` · Tier 패널 잡도 `llm=claude` · 그림은 판독문만 간다고 말한다; 보안 · 동의 문은 그대로, Claude Code 가 직접 도는 길(hwax-deliberate.js)은 고치지 않음 CP-D3; **완료**(10-21) — 엔진 `82c8f37` · `235e493` · `63554c0` · `e436d15` · 리스크 앱 `3b6e42e` · `ecad8c8` · 워크플로 `d4f15de`, 남은 것 리스크 앱 웹 화면(프론트 세션 몫)) | `docs/claude-delib-parity/` (PLAN·checklist·context-notes·**frontend-request**) |
| LLM 서버 둘을 자원 보고 나눠 쓰기(같은 모델 둘 · vLLM 지표를 읽는 라우터 `infra/llm-router` :8730 · 앞부분 해시 붙임 · 연결 실패만 넘김 · 주소 사본 함께 바꾸기, **cae00 은 `infra/.env` 의 `LLM_UPSTREAMS` 한 줄로 켠다**(기본 꺼짐) — 반대 검토 세 라운드, 사용자 결정 10-15 · **용량 측정** — 카드 대조 길이로 GuideLLM 부하를 만들어 직결 대 측정용 라우터를 재고 세 손잡이를 권한다, 심의 없는 때 cae00 에서) | `docs/llm-pool/` (PLAN·checklist·context-notes·**server-setup**(cae00 절차)·**capacity**(용량 측정 절차)) |
| 챗·심의에서 그림을 모델이 보게(지금은 GLM 요청에 `image_url` 이 없다 — 진단 · 서버 탐침 `HWAXAgentServer/scripts/llm_vision_probe.py`, 챗 이미지 + 도구 그림, M3 뒤) | `docs/chat-vision/` (PLAN·checklist·context-notes) |
| 운영 수정 요청 10-15(전문가·지식카드 화면 — 빈 카드·로그인 만료·긴 카드·검색·빈 전문가·HE 운영자, K1~K9, 다섯 리포) | `docs/request_1015.md`(요청서 정본) · `docs/request-1015/` (PLAN·checklist·context-notes) |
| 운영·관측·검색 개선 여섯(상태판 Gatus · 호출 추적 Phoenix · LLM 풀 용량 측정 · 의미 기반 도구 검색 · 한국어 검색 평가 · 도구 인자 설명 점수판 — 제안 10-15 @박용진, 분석·판정 10-16 · **상태판 2단계 10-17** — MCP 실호출 · Drive `latest/` 를 밀어 넣는 쪽 `status-push.py` · 기록 sqlite · update-all 동안 경보 멈춤 1b2→5b) | `docs/improvement-1015/` (PLAN·checklist·context-notes·**status-board**(운영 안내)·call-trace) |
| 임베더를 BGE-M3 로(한국어 질의–영어 카드 정합성 · 무중단 슬롯 둘 `*_m3 halfvec(1024)` · 청크 백필 · dev GPU 로 채워 cae00 은 merge 로 받는다 · 소비처는 응답 모델을 따른다 · 모델별 점수 하한) | `docs/embedder-bge-m3/` (PLAN·checklist·context-notes) |
| 챗은 stcx GPU LLM, 심의는 GLM(챗 전용 LLM `CHAT_LLM_*` — 챗 ReAct · 챗 안 도구 계획만, 띵킹 · 심의 준비 · 심의 · 카드 대조는 GLM · stcx 가 죽으면 호출 단위로 GLM 넘김 · 생각 모드 끔 · 챗 턴 창은 두 서버 중 작은 쪽 · update-all 3.5c 가 `infra/.env` 에서 맞춘다, 사용자 결정 10-17 · **Qwen 도 1M**(YaRN factor 4 · 1,010,000 — stcx sbatch 는 사람 몫 server-setup 9절, 벌의 창이 섞인 동안의 '창이 모자라다' 400 은 GLM 으로 넘긴다, 사용자 결정 10-18)) | `docs/chat-llm-stcx/` (PLAN·checklist·context-notes·**server-setup**(cae00 절차)) |
| 절차(한 번 한 일을 굳혀 대상만 바꿔 재생) | `docs/procedures/` (PLAN·**examples**(정본 예제 넷)·checklist·context-notes·odb-request) |
| 남은 일 정리 10-17(체크리스트 37개 · 안 끝난 456줄을 코드 · 커밋과 맞대 갈래 여섯으로 — 사용자가 고른 세 묶음: 작은 결함 · 빈틈(합성 데이터 경고 · 인구조사 점검 · 병합 키 해석 등) · 기록 정리(이미 한 82 · 버림 26) · 문서 보강) | `docs/leftovers-1017/` (PLAN·checklist·context-notes) |
| 10-17 사용자 결정 · cae00 업데이트 리뷰 후속(결정 38 — 리뷰 P1~P9 · A1~A3 · G1 · G2 · H1~H5 · X1~X5 · K1 고침, 리스크 암호 백업(이 앱만 · 박스별 칸 `risk-backup/<박스>`, 공개키만 박스에 — **개인키는 사용자**) · 지식 리포 git 묶음 Drive 매일 · 설정 킷 사내 주소 0 · 통합 앱 기동 실패 억제 · 로그 이어쓰기와 Caddy 회전(logrotate 편입은 쓰기자가 새로 뜬 뒤), **cae00 사람 몫은 `server-setup.md`**, 요청서 셋, **묶음 B 완료(10-18)** — 읽기 토큰은 허용 목록 · 같은 소속 심의 열람 · 허브 앱을 포털 토큰으로(허브 권한만) · 그림 · 도구 검색 질의 30일 수집과 150쌍 검토 화면 · T1 절차, 남은 것 사람 몫(150쌍 검토 · T1 A/B · cae00 확인 `server-setup.md` 8절)) | `docs/followups-1017/` (PLAN·checklist·context-notes·**server-setup**·requests) |
| 챗 생각 깊이 · 대화 맥락(챗 Qwen 생각 켬 · `xhigh` · 출력 몫 65,536 · 이력에 앞 턴의 조회 근거 · 띵킹 좌석마다 세션 맥락 · '생각 중' 칸 · 답한 모델 표시 · **그림** — 올린 그림 · 도구 그림 · 앞 대화의 그림, 챗은 그대로 · 띵킹 · 심의는 탐침 뒤 자동(받으면 그림, 못 받으면 Qwen 판독문), 수정 제안서 10-18 F1~F5 · K1 · S1 · 4-b, 사용자 결정 10-18; **T5-b(10-22)** 심의 도중 좌석이 조회로 받은 그림도 판독문으로 근거에(`vision_transcribe` — 판독기는 기동 때 엔진에, MCP 잡 포함)) | `docs/chat-depth-context/` (PLAN·checklist·context-notes·request) |
| 심의 엔진 운영 10-22(새 심의 멈춤 `POST /drain {scope:"delib"}` — 시작 · 이어하기는 '점검 중 — 약 N분 뒤' · 줄은 붙잡힌다 · 줄이 재기동을 넘긴다(시작 인자 파일 `<잡 원장>/args` 0600 · 토큰 없음) · 끊긴 잡은 `deliberate_continue` 한 번으로 남은 라운드만 · 재기동 없는 한도 `POST /limits`(**좌석 합 상한** `max_seats_running` — 기본 꺼짐, 건수 한도는 3석도 20석도 1건) · 섞인 GLM 풀의 창 — `LLM_CONTEXT_TOKENS` 는 서버 답의 상한 · 600초마다 다시 묻고 줄일 때만, update-all 은 심의가 돌면 멈추고 `HWAX_DELIB_WAIT_S` 기다려 재기동 · 다시 선 줄 수, 요청 R1~R5 · O1 · O2, 결정 DO-D1~D16, **cae00 사람 몫은 `server-setup.md`**(상한을 먼저 적고 nginx `/v1/models` 우회를 걷는다)) | `docs/delib-ops/` (request·PLAN·checklist·context-notes·**server-setup**) |
| 챗 PPT — 보낸 결과를 대화에 남기기 · DRM 문서를 PC 의 PowerPoint 로 풀어 올리기(요청서 10-22 A1~A7 · B1~B7 — 보내기 성공을 대화의 어시스턴트 알림 + 업로드 근거로(활동 `origin: upload` → 이력 `kind: upload` → 에이전트 서버가 '사람이 올려 보낸 결과' 머리) · 이름이 박힌 지시문을 입력창에(비면만) · 다시 싣는 그림에 'N턴 전' · RA 0블록은 포털이 가져오기 저장 꼴을 그대로 넘겨서(정의에 내용을 넣는다) · A6 은 결함 아님 · A7 안 함(AIDH 는 최종 사용자를 모른다); **B 는 켠 채로 · 다시 저장한 PPTX 는 안 넣음**(사용자 결정 10-22) — 세션 + CSRF 로만 받는 일회용 표 · 도우미(추출기 `-Url` 모드)는 설정 파일의 주소로만 올리고 받는 계정을 먼저 묻는다 · 받은 글은 문서 칩으로 · HKCU 설치 배치; **완료 10-23** — 에이전트 `5033072` · 포털 커밋 여섯, 남은 것 Windows 실시험 · dev 에이전트 재기동(확인 뒤) · cae00 반영) | `docs/chat-ppt/` (request·PLAN·checklist·context-notes) |
| 문서 → Report Archive 정밀 변환(PPT · Excel · Word → RA 의 JSON + 리소스 — Docling + VLM + 구조화 출력(Pydantic AI 또는 대체재) + 사내 온톨로지(SP 의 과제 · 모델 · 부서 + RA 자체 엔티티 · 제안 큐), 원문 유지 + 모델 보강 · 정해진 일은 코드(차트 값은 XML 캐시) · 변환과 배달을 나눈다(패키지 → 포털이 사용자 명의로 엄격 생성 — 배치 유지) · 새 HEAX 앱 DocForge(가칭) · 금 표본 40 + DRM 5 로 기준선(RA 가져오기 · AIDH)과 견준다; **계획(10-24)** · 사용자 결정 10-24 — VLM 은 stcx Qwen · 새 HEAX 앱 **DocForge**(리포 `squall321/DocForge` · id `doc_forge` · 개발 main / 배치 release) · 뼈대는 dev(`9f0d2e9` — 걸어 다니는 뼈대 · 계약 · 단계 명세 · 명세 시험 · M0 탐침 · 배치 절차) · **dev 에서 먼저 개발하고 실데이터가 필요해지면 cae00**(DF-D14 — dev 시작점 DocForge `docs/START.md` D0~D11 · cae00 인계 `cae00-handoff.md` · cae00 은 SIF 를 못 지어 배치마다 dev 가 짓는다 · 허브 등록은 첫 SIF Drive 와 한 묶음 · 포털 배달은 포털 리포 몫); **10-24 — DocForge dev 단계 · 첫 배치 dev 쪽 · 2단계 E1~E6 끝, 포털 배달 「Report Archive — 정밀 변환」 붙임**(DF-D17 — 호스트 경로로 맡기고 · 진행 · 그 사람 명의 엄격 생성 · 한 번만 · 알림, 권한표 `docforge`), 남은 것 DocForge beta · 실주행 · PLAN §12) | `docs/doc-to-ra/` (PLAN·checklist·context-notes·**research**(파일 · 줄 근거)·**cae00-handoff**·**server-setup**(cae00 설정 · 확인 — 사람 몫)) |
| 챗 자기검증(답을 근거와 한 번 더 대조해 고친 뒤 본문에 — 사용자 결정 10-23 셋: **검증한 답만 본문에**(초안은 '생각' 칸) · 같은 챗 모델 · 항상(근거도 수치도 없는 짧은 답만 건너뜀); 에이전트 서버가 턴을 감싼다(token → reasoning, result · meta 붙잡기) · 검토자 생각 끔 · 창은 고친 답 몫을 먼저 떼고 넘칠 때만 55 · 25 · 20 · 고친 답은 다 쓴 뒤 한꺼번에 · 가드 여섯은 초안을 내고 까닭 · 근거 블록은 고친 답으로 재셈 · 화면은 고친 곳 · 못 함은 답 아래, 없음 · 생략은 모델 표시 옆; 끄기 `CHAT_SELF_CHECK=0`; **완료 10-23** — 에이전트 `d8011e0`, 남은 것 dev 재기동(확인 뒤) · cae00 · 실모델에서 느려짐 · 품질 보기) | `docs/chat-self-check/` (PLAN·checklist·context-notes) |
| MX WhitePaper 완전 연결 · LLM 위키(사용자 요청 10-24 — **정본 요청서는 MXWhitePaper `docs/llm-wiki/`**(request · CONTRACTS · SCHEMA-DRAFT · START · checklist · context-notes, 그 리포 세션이 개발); 제안된 구조는 **Karpathy 'LLM Wiki'**(원천 · 위키 · 규칙서, 들이기 · 묻기 · 점검, index · log) + 사내용 다섯(블록 근거 · 보이기 범위 · 변경 묶음과 검토 · 온톨로지 · 작업 실행기); 연결의 빈 곳은 **게이트웨이 경유 MXWP 호출이 서비스 계정 `admin@mx.local`** — ste 방식 위임(일반 길 `PER_USER_SSO_APPS` `mx-white-paper:MXWP`) · REST 다리 `per_user` · 진입 토큰 `affiliation` 클레임(시스템별) · 게이트웨이 `plat:` 서명 헤더, 시장불량 원천 후보는 cae00 `plm-defect`(`plat:plmdefect`) · SignalForge; 포털 몫 P1~P10 은 여기, 사람 결정 Q1~Q12 는 MXWP request §11) | `docs/mxwp-wiki/` (PLAN·checklist·context-notes) |

작업을 시작하기 전에 해당 폴더의 `context-notes.md` 를 본다 — **왜 그렇게 했는지**가
거기 있고, 없으면 같은 판단을 다시 내리느라 시간을 쓴다.
