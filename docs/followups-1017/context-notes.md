# 10-17 사용자 결정 · cae00 리뷰 후속 — 결정과 까닭

**FU-D1 결정을 받은 방법(2026-10-17).** 남은 일 감사의 '정해 주셔야 함' 37줄을 탐색 에이전트 넷에 나눠 줄마다 '아직 열렸나 · 지금
코드는 무엇으로 도나 · 고르면 무엇이 바뀌나' 를 확인하게 했다(카드 64장). 데이터 이관 계획 §12 를 펼치니 체크리스트 줄보다 많아졌다.
카드를 넷으로 갈랐다 — 실제로 갈리는 것 21(여섯 묶음으로 여쭘), 이미 기본값으로 도는 것 27(한 번에 확정), 전제가 사라진 것 5 + 웹 검색에
딸린 둘(닫음), 사실 · 측정이 있어야 정할 것 11(필요한 것만 적음). 질문에 옮긴 사실은 직접 다시 확인했다 — 포털 저장소 공개
(`private: false`), 토큰 기본 범위 읽기 · 쓰기와 무기한 발급, 심의 조회의 주인 확인 없음, 리스크 앱 백업 일정 없음과 HEAXHub 스크립트가
제외 요청을 안 읽음, 데이터허브 0.0.0.0:8001 · 키 없이 200, 지식 리포 원격 없음 · ExpertGrounding 백업 없음, MXWP `instance stop --all`.

**FU-D2 VOC 는 다시 물었다.** 다섯째 묶음에서 '양쪽 수집 유지' 를 고르셨는데 그 카드는 cae00 도 수집한다는 전제였다. cae00 리뷰(D2)는
Redis 가 없어 cae00 수집이 돌지 않는다고 했다. 전제가 틀린 채 고른 답이라 다시 여쭸고 'dev 만 수집, 문서화' 로 정했다. 합치기의
'dev 가 이긴다' 규칙은 이 상태에 맞으므로 코드는 그대로다.

**FU-D3 사실이 있어야 정할 것(지금 열어 둔다).** 과제 키 대장(cae00 RA 기준정보에 과제 목록이 있나) · 절차를 게이트웨이 도구로(cae00 사용
수치) · RA 부서 표시(RA 담당의 답) · 카드 대조 동시 수(cae00 용량 측정) · ste 전각도 앱(preflight 결과) · 리스크 호출 원문 보존(cae00 DB
증가량) · 리스크 모델 상한(실제 STEP 크기) · ste 헤드노드 백업과 munge 키(헤드노드 확인) · 18대 노드 사양(장비가 정해지면).

**FU-D4 리뷰는 지금 HEAD 에서 다시 확인했다.** 리뷰는 cae00 이 돌린 커밋(포털 `70f9e5e` · 게이트웨이 `095c93a` · AIDataHub `57a5a4b` ·
HEAXHub `4e1954d` · KooRemapper `d25e12f`) 기준이다. 포털은 그 뒤 16커밋 · KooRemapper 28커밋이 더 있어 줄 번호가 다르다. 지적한 자리는
전부 그대로 있었다 — `services.py` 의 `open(log, "wb")` · update-all 의 `git stash show --name-only` · `provision-config.sh` 의
`mcp?token=` · 게이트웨이 `basicConfig(INFO)` · 에이전트 서버 `start.sh` 의 300초 조각 한도 · AIDataHub 병합의 `information_schema` 열 목록 ·
HEAXHub `SOURCE_NATURAL_KEY` 의 `publisher` · KooRemapper 안내 echo 의 백틱. 리뷰가 말한 U11 요청서는 이 리포에 없다(박스 쪽 문서) —
P3 · A1~A3 는 리뷰 본문과 안내서 문구를 기준으로 고친다.

**FU-D5 다른 세션의 작업은 건드리지 않는다.** 시작할 때 HEAXHub 에 남의 미커밋 수정(`deploy/apptainer/materialtwin-release-to-drive.sh`)이
있었고, KooRemapper · SignalForge 는 도구 상태 · 실행 산출물이 바뀌어 있었다. 커밋은 고친 파일만 골라 담는다.

**FU-D6 레코드 m3 채움은 '제목 · 본문이 같을 때만' 이다(AIDataHub `722d7a0`).** 리뷰 H1-b 의 요청은 '운영 값이 비었으면 `updated_at` 과
상관없이 채운다' 였고 처음엔 그대로 짰다(`a7a2ee4`). 그런데 박스에서 레코드를 고치면 `db_writer` 가 시그니처(v1 · m3)를 비워 그 박스의
스윕(30분)이 새 내용으로 다시 계산한다. 그 사이에 병합이 돌면 dev 의 옛 내용으로 만든 벡터가 들어가고, 비지 않았으니 스윕은 다시 하지
않는다 — 조용히 낡는다. 시그니처의 재료(제목 + 본문의 caption · headers · notes — `similarity_svc._record_signature`)가 양쪽에서 같을 때만
채운다(`title` · `content_hash`). 무엇이 재료인지 모르는 표는 채우지 않는다(다섯 번째 인자). dev PG 임시 DB 둘에서 실제로 돌려 봤다 — 같은
레코드는 채우고, 운영에서 고친 레코드는 빈 채 남고, 같은 덤프 두 번째 병합은 한 행도 다시 쓰지 않았다(xmin 같음). 끝나고 두 DB 는 지웠다.

**FU-D7 예전 병합이 남긴 위험(고치지 않음 — 크기를 재려면 cae00).** 예전 병합은 트리거 때문에 갱신한 레코드의 운영 `updated_at` 을 병합
시각으로 올렸다(08-26 21시 27,078건 · 07-27 21시 17,027건처럼 몰린 것). 그러면 '그 병합이 쓴 덤프 뒤 ~ 그 병합 전' 에 dev 에서 바뀐 레코드는
다음 병합에서 '운영이 더 새롭다' 로 건너뛰어진다 — 그 레코드가 dev 에서 다시 바뀔 때까지 cae00 은 한 판 옛것이다. 운영의 진짜 편집과 병합이
올린 시각을 가를 방법이 없어 되돌리지 않았다. 이번 판부터 병합이 운영 `updated_at` 을 dev 값 그대로 두어 새로 생기지는 않는다. 크기는
병합 중 staging 과 견줘 '운영이 더 새롭다는데 `content_hash` 가 다른 레코드' 를 세면 안다 — 필요하면 사용자 판단으로 연다. — 사용자 결정 10-31 A27: (나) 병합 끝 요약에 '운영이 더 새롭다는데 `content_hash` 가 다른 레코드 수' 한 줄(읽기만 — AIDataHub), dev 작업 진행 중(10-31) · 다음 cae00 병합에서 크기를 본 뒤 정한다 (10-31 정리)

**FU-D8 PG 30분 시한은 약속한 대로 나눴다.** 결정 카드에 '새 연결부터 들고, cae00 은 병합 · 백업이 없을 때 운영자가 한 줄로(dev 는 제가)'
라고 적었다. dev 는 10-17 에 걸었고(병합 · 덤프가 돌지 않는 것을 보고 · 새 연결에서 `30min`), cae00 한 줄은 AIDataHub
`deploy/apptainer/README.md` 'PG 안전망' 이다 — 적은 명령을 dev 에서 그대로 돌려 봤다. 이행 마이그레이션으로 자동화하지 않은 까닭 — 카드에
그렇게 여쭙지 않았다.

**FU-D9 리스크 백업은 '이 앱만, 박스별 칸' 이다.** 래퍼는 원래 HEAXHub app-data 백업 전체를 불러 공유 칸(`app-data` — dev 가 올리고
cae00 이 병합해 받는다)에 올리게 돼 있었다. cae00 의 `HEAX_DRIVE_REMOTE` 는 deploy-all 이 dev 와 같은 `HEAXHub/dist` 로 잡으므로, 카드대로
'cae00 에도 같은 줄' 을 돌리면 cae00 의 앱 데이터 전부가 그 칸의 `latest/` 를 덮어 dev → cae00 병합을 뒤섞고 다른 앱의 운영 데이터(음성
녹음 등)까지 평문으로 나갔을 것이다. 그래서 HEAXHub 스크립트에 앱(`HEAX_APPDATA_ONLY`)과 칸(`HEAX_APPDATA_CHANNEL`)을 더하고 래퍼는
`risk-backup/<박스>` 에 리스크 앱만 올린다(보존 5벌은 HEAXHub 의 것). 평문 원장이 다른 길(포털 build-all)로 나가지 않게 '곁에 `.age` 가
있으면 평문은 싣지 않는다' 를 HEAXHub 쪽에 걸었다. 키는 박스마다 만들지 않고 dev 와 같은 공개키를 쓴다 — 박스가 죽을 때 키도 함께 사라지면
백업을 못 푼다. **개인키는 지금 dev(`~/.config/hwax/risk-backup.agekey`, 600)에만 있다 — 사용자가 따로 지녀야 한다.**

**FU-D10 지식 리포 묶음에는 커밋 안 된 변경도 싣는다.** git 묶음은 커밋만 담는데 ExpertGrounding 은 커밋이 8월의 1개뿐이고 뒤 작업
1,482개가 작업 트리에만 있었다 — 묶음만이면 거의 빈 백업이다. 수정 · 추적 안 된 파일(.gitignore 존중)을 싣고 비밀 꼴(`.env*` · `*.key` ·
`*.pem`)과 `*.sif` 는 뺀다. 다른 세션이 그 리포를 쓰므로 커밋은 대신 하지 않았다. 바뀐 것이 없으면 올리지 않는다(지문의 정렬은 `LC_ALL=C`
— 빈 환경(크론)과 사람 셸의 지문이 갈려 같은 내용을 다시 올린 것을 보고 고쳤다).

**FU-D11 logrotate 편입은 미룬다.** HEAX 백엔드 · 워커 · beat, AIDataHub uvicorn, `/tmp/hwax-services` 는 이제 `>>` · "ab" 로 열지만,
`copytruncate` 는 떠 있는 쓰기자가 O_APPEND 일 때만 안전하다. dev 실측(`/proc/<pid>/fdinfo/1`) — HEAX 워커 · AIDataHub API 는 `0100001`(없음),
새 services.py 로 띄운 게이트웨이만 `0102001`. update-all 은 바뀐 서비스만 다시 띄우므로 편입은 박스마다 새로 뜬 것을 본 뒤다. 그때까지는 기동
때 크면 한 벌 넘기는 것(HEAX `_keep_log` · AIDH `rotate_log` · services.py `prep_log`)이 커짐을 막는다.

**FU-D12 `services.py enabled` 의 오류는 2 다.** P8(이미지 받기)을 고친 뒤 포털 전체 시험에서 기존 시험 다섯이 깨졌다 — 매니페스트가 없는
사본에서 services.py 가 예외로 죽으면 파이썬은 1 로 끝나는데 1 은 '이 박스 대상 아님' 이라 이미지를 '꺼짐' 으로 뺐다. update-all 의 상태판 ·
호출 추적 판정도 같은 1 을 받는다. 잡히지 않은 예외는 2(모름)로 바꿨다 — '실패가 정상 응답과 똑같이 생겼다' 의 또 한 꼴.

**FU-D13 HEAXHub 시험은 런처 디렉터리를 격리한다.** 기동 실패 억제는 상태 디렉터리에 기록을 남기는데 HEAXHub 에는 conftest 가 없어, 디렉터리를
돌리지 않는 기존 시험(모르는 스택 등)이 진짜 `var/integration_state` 에 쓰면 다음 실행부터 backoff 를 받는다. autouse 픽스처로 막았다. 덧붙여 —
워커는 작업 안에서 런처를 불러오고 자식이 200 작업마다 갈려, 커밋 전에 새 코드를 부른 자식이 dev 의 `heax_demo_nextjs` 억제 기록을 썼다
(옛 자식은 옛 코드로 계속 시도). 진행 중인 빌드를 끊을 수 있어 워커를 억지로 다시 띄우지 않았다 — 자식이 갈리며 맞춰진다.

**FU-D14 age 는 사용자 공간에 둔다.** dev 는 `apt-get download age`(서명된 저장소)로 받은 우분투 꾸러미를 `dpkg-deb -x` 로 `~/.local/opt/age`
에 풀었다(sudo · 설치 없음). cae00 은 apt 가 깨져 있어(리뷰 D2) 같은 꾸러미와 체크섬을 Drive `HWAXPortal/tools/age/` 에 두었다 — 절차서의
명령을 dev 에서 임시 접두사로 그대로 따라 해 봤다.

**FU-D15 옛 사본 목록(결정 17) — 확인 대기.** dev 의 `.pre-move-*` 19 · `.rolled-back-*` 6(09-05 이관의 원본과 실패 때 옮겨 둔 사본)과 쓸모없는
파일 넷(`HEAXHub/dev2.db` 와 부속 둘 — 참조 0, `var/app_data/materialtwin.db` 0바이트), 모두 29개 · 24.0GB. 지우기 전에 — 그것을 가리키는
심링크 0, 그 안의 파일을 쥔 프로세스 0(`/proc/*/fd`). 가장 큰 둘은 AIDataHub PG 의 옛 사본 두 벌(각 9.8GB)이다. 사용자 확인을 받고 지운다. → **10-18 사용자 '목록대로 모두 지우기' — 지우기 직전에 다시 대조(경로가 정확히 `.pre-move-20260905-…` · `.rolled-back-…` · 쓸모없는 넷인지, 링크 · 쥔 프로세스 0)한 뒤 29개 모두 지웠다(실패 0). /home 여유 322G → 335G. 서비스 다섯 그대로 200.**

**FU-D16 dev 공인 IP 노출은 그대로 둔다(10-18 사용자).** dev 의 `enp13s0` 에 공인 주소(/26)가 붙어 있고 포트 85개가 모든 주소로 듣는다(포털 · PG 다섯 · MySQL · Redis · MinIO · NFS · 원격 데스크톱 · VNC · 쿠버네티스 등). 10-17 에 바깥 주소가 AIDataHub 에 붙어 200 을 받은 기록이 있어 AIDataHub 만 루프백으로 고쳤다. 방화벽(ufw · sudo)과 서비스별 루프백을 여쭸고 '그대로 두기' 를 고르셨다 — 다시 묻지 않는다. 새 서비스의 기본 바인드는 루프백으로 둔다(이번 AIDataHub 처럼).

**FU-D17 묶음 B 결정(10-18, 질문 카드 둘).** 사용자 "그래 다 이어서 해줘야겠다". 조사 셋(읽기 토큰 · 허브 앱 / 같은 소속 열람 / 도구 검색 ·
T1)을 바탕으로 여쭸다. ⑤ 읽기 토큰의 도구 — **허용 목록 + `readOnlyHint` 존중**(동사 규칙은 미분류 222~270개 · 양방향 오분류 —
`fetch_rerank_model` 은 내려받기, `catalog_run` 은 실행, `tag_search` 는 읽기인데 쓰기처럼 보인다). ⑤ 챗 우회 — **그대로**(읽기 토큰으로 포털
`/agent/chat` · 카드 대조를 부르면 포털이 `["chat"]` PAT 를 새로 찍어 엔진이 RA 초안을 쓴다 — 리스크 앱 패널의 길이고, 심의 산출물 저장으로
본다). ⑦ 허브 앱의 사람별 권한 — **허브 권한(`can_view_app`)만**. ⑥ **시작 때 소속 · 주인 없는 옛 잡은 내부와 관리자만 · 목록에 같은 소속 것도(주인
표시)** — 목록은 권한 안(내 것만)을 권했지만 사용자가 팀의 심의를 목록에서 찾는 쪽을 골랐다. ㉑ 질의 수집 **30일** · 150쌍은 **검토 화면**.
S1 은 **요청서 그대로**(10-17 규칙).

**FU-D18 조사에서 나온 사실(10-18 — 결정의 전제).** ① 게이트웨이 도구 521개 모두 MCP annotations 가 없다(dev 실측) — '읽기 표시만 연다' 는
지금 0개를 연다. ② 포털 토큰 화면은 `['read','write']` 고정이라 읽기 PAT 는 교환(`/auth/pat/exchange`)으로만 생긴다 — 지금 쓰는 곳은 리스크 앱
하나이고, 게이트웨이로 부르는 25종은 모두 읽기다(동사 규칙이면 그 가운데 14~16개가 미분류라 캡처가 깨진다). ③ 챗 · 절차 PAT 의 범위는
`["chat"]` 이다 — '`write` 가 없으면 읽기' 로 판정하면 챗이 막힌다 → `read` 있고 `write` 없을 때만 읽기 전용. ④ 심의 조회(상태 · 결과 · 발언)는
MCP 에서만 하고 주인 확인이 없다 · 잡에는 X-HWAX-User 원문(퍼센트 인코딩)만 남고 소속은 없다 · 이어하기가 남의 결정문을 내 잡으로 옮기는
우회로다 · dev 원장 15건 중 12건이 주인 없음. ⑤ 소속 키는 원장의 `affiliation` 하나(지금 표에는 CAEG 하나뿐) — 같은 소속은 사실상 거의 모두다.
⑥ 허브 관문은 쿠키 → 허브 PAT → 허브 HS256 JWT 순으로만 받아 포털 RS256 PAT 는 401 이다. ⑦ search_tools 질의는 어디에도 남지 않는다.

**FU-D19 묶음 B 구현 · dev 반영 · 드러난 결함(10-18).** ⑤ 게이트웨이 `ffb5292` · ⑥ 에이전트 서버 `9d4c931` + 게이트웨이 `ab34abd` ·
⑦ HEAXHub `fc1ab89` · ㉑ 게이트웨이 `a17fc83` · `e617012`. dev 는 게이트웨이(services.sh — 손으로 띄우면 `GATEWAY_AUDIT` 가 빠져 감사가 리포
자리로 간다) · 허브 백엔드(허브 `start.sh` — 커밋이 바뀌면 백엔드와 celery 를 같이) · 에이전트 서버(`./start.sh -d` — 도는 심의 0 확인)를
다시 띄우고 실물로 봤다 — 허브 폐기 목록 주소가 JWKS 에서 지어져 292건을 읽고 모르는 kid 는 401, 심의 목록은 신원 없는 내부 15건 · 다른 소속 0건.
⑦ 의 판단 둘 — 폐기 목록을 **한 번도** 못 읽었으면 포털 토큰을 받지 않는다(무기한 PAT 의 유일한 통제), 갱신 실패는 직전 목록으로 버티되 10초
뒤 다시(관문은 앱 자산 요청마다 돈다). 포털이 안 닿는 것(503)과 나쁜 토큰(401)을 본문 `detail` 로 가른다.
드러난 결함 셋 — ① python-jose 는 PyJWT 식 `options={"require": [...]}` 를 말없이 버린다(실측 — aud 없는 토큰이 `audience=` 를 통과,
jti · exp 가 없으면 재사용 막기에서 KeyError 500). 허브 진입 토큰 검증을 같이 고쳤다(`c168772` — 포털의 진입 토큰은 넷을 늘 실어 로그인은
그대로). **같은 꼴이 SignalForge `backend/app/api/portal_sso.py` 와 MXWhitePaper `apps/api/app/routers/portal_sso.py` 에 있다** — 서명이 있어야
하고 포털의 진입 토큰은 aud 를 늘 실어 뚫리지는 않는다(잘못된 토큰이 401 대신 500). SignalForge 는 다른 세션의 미커밋 작업이 있어 손대지
않았다 — 고칠지 사용자에게 여쭌다. → **10-18 사용자 'ㄱㄱ'** — SignalForge `de6a71b`(백엔드 파일만 · 다른 세션의 `.bkit` · `reports`
는 그대로) · MXWhitePaper `c164dda` · lat 문서 `79abd6c`, 셋 다 고치기 전 코드에서 시험이 실패하는 것을 봤다. MXWP dev 는 `--reload` 라 바로
실렸다. SignalForge dev 백엔드(10-15 부터 · `--reload` 없음)는 다른 세션이 돌보는 스택이라 다시 띄우지 않았다 — 그쪽 `scripts/up.sh` 나
cae00 update-all 에 실린다. MXWP 전체 시험의 401 실패(개발용 인증 우회가 꺼진 인스턴스 환경)는 고치기 전 코드에서도 같다. ② 허브 감시(`scripts/watchdog.sh`, 매분)가 `start.sh` 가 막 띄운 백엔드를 기동 reconcile(앱 22개 —
1분 넘게) 중에 죽이고 다시 띄웠다(dev 01:24 실측 — 두 번 기동). ③ 감시는 백엔드 · 워커 · beat 를 `>` 로 열어 앞 프로세스의 기록을 지웠다 —
10-17 결정 16 이 `start.sh` 만 고쳤다. ②③ 은 `74fa732`(backend.rev 시각부터 300초 여유 · 감시가 띄울 때도 시각을 찍음 · `>>`). 덧붙여 dev 허브
백엔드는 10-10 부터 옛 커밋(091be05)으로 떠 있었다 — 그 뒤 백엔드 커밋은 이번 재기동으로 처음 dev 에 실렸다.

**FU-D20 150쌍 검토 화면(결정 21).** claude.ai 아티팩트 https://claude.ai/artifact/MsLjvDFr3oMJsUXZbwavob — 쌍 · 두 순위 상위 다섯 · 도구 짧은 설명은
페이지에 싣고(바뀌지 않는 입력), 표시만 저장소(`marks/<쌍 id>` — `{verdict, gold?, query?, memo?, at, by?}`)에 둔다. 도구 설명은 320자로 줄이고
주소 · 사내 호스트를 가렸다(설명 전문은 추적하지 않는 카탈로그 스냅샷이라). 표시는 Claude 가 내려받아 `apply_review.py` 로 되돌린다 — 먼저
보고(`--write` 없이) 맞으면 쓴다. 빼기는 줄을 지운다(git 이력이 남긴다). 정답 확인은 '이 질의에 맞는 도구가 이것뿐인가' 가 핵심이라 고침은
두 순위의 후보를 골라 정답에 더하는 꼴이다(README '읽는 법' 3 — 정답이 좁아 RRF 가 맞는 다른 도구를 놓침으로 센다).

**FU-D21 logrotate 편입은 가드로(10-19).** FU-D11 은 '박스마다 쓰기자가 새로 뜬 뒤 손으로 넣는다' 였다 — 템플릿은 박스 공용이라 정적 목록에
박스별 상태를 담을 수 없다. 대신 회전 직전 가드(`append-guard.sh` — `find /proc/[0-9]*/fd -lname` 로 그 파일을 쥔 fd 를 찾아 fdinfo flags 의
02000 을 본다, dev 한 번 70ms 남짓)를 prerotate 로 건다. logrotate 3.19 의 nosharedscripts(기본)는 prerotate 가 실패하면 **그 로그만**
건너뛴다 — 진짜 logrotate 로 시험했다(`r+` 로 쥐면 내용 그대로 · 회전본 없음, `a` 면 회전). 덧붙여 dev 허브 백엔드는 10-18 01:24 옛 감시가
`>` 로 띄운 것이라 가드가 실제로 막았고(첫 실측), 허브 `start.sh` 로 다시 띄워 풀었다. 감시는 이번엔 끼어들지 않았다(74fa732).

**FU-D22 dev 메모리 부족이 서비스를 내렸다(10-18 07:11 UTC — 10-19 발견).** earlyoom(dev drop-in `hwax-dev.conf` — `-m 6,3 -s 100,100`
· `--prefer '^(python|python3|pytest|node)$'` · `--avoid` 에 `code` 등)이 10-18 하루 SIGTERM 1,300번 남짓을 보냈고, 07:11 에 포털(인스턴스는
남고 앱만 죽음) · 게이트웨이(93MB) · KooRemapper MCP(인스턴스 남음) · smarttwin-mcp(systemd `Restart=on-failure` 는 SIGTERM 을 깨끗한 종료로
봐 다시 안 띄움) · mxwp-mcp · searxng 가 함께 내려가 14시간 꺼져 있었다. AIDataHub API 는 감시가 매분 다시 띄우지만 다시 죽는다(10-19 도 두 번).
복구 — 포털 `apptainer instance stop hwax_portal && start.sh` · 게이트웨이 · mxwp-mcp · searxng `services.sh up` · smarttwin-mcp `sudo systemctl start`
· KooRemapper MCP 는 인스턴스를 내려 KooRemapper 감시가 다시 띄우게. 메모리를 먹는 쪽은 서비스가 아니다 — `cpptools` 3개 42GB · `code` 226개
31GB · VM 16GB · Claude 세션 52개 9GB, 우리 서비스는 합쳐 15GB 남짓. 빈틈 넷(포털 · 게이트웨이 · KooRemapper MCP · smarttwin-mcp 는 죽어도
안 돌아온다)과 earlyoom 설정은 사용자 결정으로 넘긴다. — 풀림 사용자 결정 10-19 '감시 보강만'(FU-D24) — 포털 services.py heal(watch: true 다섯) · KooRemapper 감시가 MCP 연결도 본다(`559f582`) · smarttwin-mcp systemd Restart=always(묶음 C) — earlyoom 설정은 그대로 둔다 (10-31 정리)

**FU-D23 두 좌석의 태그 조건(10-19).** `mx-whitepaper-analyst` 는 `required_tags=[whitepaper]` 인데 묶인 427장은 전부 `doc_type=whitepaper` 이고
그 태그는 0장, `market-voc-analyst` 는 `[voc]` 인데 2장은 `voc:camera` 같은 갈래 태그뿐이다 — 두 좌석 모두 `required_doc_type` 에 이미 맞는 종류가
있고 묶음이 그것을 보장한다. 조건이 문서 종류를 태그로 잘못 적은 것이라 비운다(카드 427장에 태그를 다는 것보다 좁고 되돌리기 쉽다 — 되돌릴 값
`[whitepaper]` · `[voc]`). agents 표는 cae00 병합에 `updated_at` 으로 실린다. VOC 좌석은 비웠고(게이트웨이 `agent_search` 히트 0 → 2 · 4),
백서 좌석은 자동 모드의 권한 검사가 '공유 자원 수정' 으로 막아 사용자 확인을 기다린다.

**FU-D24 서비스 감시(10-19 사용자 '감시 보강만').** 포털 스택에는 죽은 서비스를 다시 띄우는 것이 없었다(허브 · AIDataHub · KooRemapper ·
SignalForge 는 제 감시가 있다). `services.py heal` 을 매분 크론으로 — 판단 넷. ① **연결 거부만 죽음** — 느린 응답 · 시간 초과 · HTTP 오류로
판정하면 바쁜 에이전트 서버를 다시 띄워 도는 심의를 끊는다. earlyoom 에 죽은 모양은 '아무도 안 듣는다' 다. 세 번(5초 간격). ② 고치는 길은
매니페스트의 down(stop) → up — 인스턴스만 남고 앱이 죽은 포털도 stop 이 인스턴스를 내려 풀린다. ③ update-all 이 도는 동안은 건너뛰되
**잠금은 잡지 않는다**(잡으면 막 시작하려던 update-all 이 '이미 돈다' 로 물러난다) — 명령줄로만 본다. 감시 자신의 겹침은 자기 잠금(파이썬
fd 는 자식에게 안 물려진다 — 예전 flock 사고 없음). ④ 박스의 운영 동작을 바꾸므로 cae00 은 `HWAX_WATCHDOG=1` 일 때만(로그 회전과 같은 게이트).
대상은 오늘 죽고 스스로 안 돌아온 넷 + 같은 처지의 에이전트 서버 — report-archive(RA 는 손대지 않음) · vllm(dev 는 원래 꺼짐)은 넣지 않았다.
덧붙여 — 변이 확인 뒤 `WATCH_TRIES = 3→1` 처럼 **크기가 같은 변이를 같은 초에 되돌리면** 파이썬이 `__pycache__` 의 변이된 바이트코드를 계속
쓴다(크기 · 초 단위 시각으로만 판정). 해시로 원본을 확인해도 import 쪽은 낡은 코드를 돈다 — 복원 뒤 그 모듈의 pyc 를 지운다.

