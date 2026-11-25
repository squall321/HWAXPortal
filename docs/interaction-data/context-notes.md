# 결정과 까닭 — 상호작용 데이터 수집 · DB화 · 활용

## IX-1 ~ IX-5 사용자 결정(2026-11-24)

- 요청 — 「모든 이용자가 했던 채팅이나 Claude MCP 로 나눈 데이터를 수집해 DB 화 · 활용」. 처음 분석(원문은 제자리 · 가린 가공본만 · 정책 먼저)에 대해 사용자가
  「최대한 많이 · 예외 없이」, 그리고 「Claude 대화는 기본으로 못 가져오지만 Claude 에서 보내는 명령을 MCP 로 부르면 그 텍스트를 끌어올 수 있다 — 사람들이 자의로
  제공하게」 라고 답했다.
- 그 뒤 물음 넷 — 모두 권장안. IX-2 MCP 호출은 모든 호출의 인자 · 결과 원문을 자동 저장(수집 사실을 알림) · IX-3 Claude 대화는 MCP 도구 + PC 킷 훅 둘 다(사람이
  스스로) · IX-4 원문은 본인 + 지정 분석가 · IX-5 무기한(본인 지우기 청구는 받는다).
- 「계획을 잘 세워 달라」 — PLAN 을 먼저 쓰고 단계마다 짓는다.

## IX-6 지금 남는 것을 먼저 센 까닭(2026-11-24)

- 이미 쌓이는 곳이 여럿이다 — 포털 대화 저장소(웹 챗 · 심의 원문, 주인만 봄 · 내 대화 의미검색 벡터), 심의 잡 원장, 게이트웨이 감사(인자 · 결과 없음),
  도구 검색 질의(30일 굴림), 루틴 · 절차 원장, 이용 통계. 새로 모아야 하는 것은 **개인 Claude 의 호출 원문(S3)과 공유 대화(S8)** 두 갈래뿐이고, 나머지는
  옮기거나 잇는 일이다. 그래서 M1 은 「새 수집 둘 + 옮기기」 로 묶었다.
- 도구 검색 질의는 30일 뒤 지워진다 — 무기한(IX-5)이면 지우기 전에 원장으로 옮겨야 한다(S4).

## IX-7 저장소 — AIDataHub PG 인스턴스의 따로 된 DB(2026-11-24, 이 세션 판단)

- 포털 SQLite 가 아니라 PostgreSQL — 무기한 · 원문 · MCP 결과까지 담으면 크기가 크고, 가공층 분류 · 집계 · 임베딩 검색에 PG 가 맞다.
- AIDataHub DB 안의 스키마가 아니라 **따로 된 DB** — AIDataHub 덤프 · 조각 스냅숏(dev → cae00 병합)이 DB 단위로 돈다. 같은 DB 면 dev 의 시험 데이터가
  cae00 에 섞이거나, cae00 원문이 덤프에 실려 Drive 로 나갈 길이 생긴다. 따로 된 DB 는 그 길이 없다. 백업은 박스의 `backup-local.sh` 대상으로만.
- 반대 검토 거리 — PG 인스턴스를 같이 쓰면 AIDataHub 재기동 · 이행이 수집기에 닿는다. 수집기는 스풀 · 재시도로 견딘다(4-1).

## IX-8 비밀은 원문이어도 남기지 않는다(2026-11-24, 이 세션 판단)

- 「예외 없이 원문」(IX-2)과 부딪히는 것처럼 보이지만 전제다. 도구 인자 · 결과 · Claude Code 기록 파일에는 토큰 · 키가 실린다(실제로 PAT 가 기록 파일에 남은
  적이 있다). 원장에 비밀이 들어가면 원문 열람 권한(IX-4)이 곧 남의 자격을 얻는 길이 된다. 칸 이름과 값 꼴로 지우고, 지운 자리는 `<가림:종류>` 로 남긴다.

## IX-9 수집이 호출을 막지 않는다 · 무음 실패 금지(2026-11-24, 이 세션 판단)

- 게이트웨이는 스풀에 한 줄 덧붙이기만 한다(포털이 가져간다). 포털이 내려가도 호출은 그대로 되고, 스풀은 회전한다. 스풀 넘침 · 수집 멈춤은 상태판 · update-all
  ✗ 로 알린다 — '실패가 정상 응답과 똑같이 생긴' 무음 결함(메모리 무음 결함 점검)을 되풀이하지 않는다.

## IX-10 저장소를 포털 SQLite 로 — IX-7 을 뒤집음(2026-11-24, 이 세션 판단)

- 포털 이미지(`portal.sif`)에 PostgreSQL 드라이버가 하나도 없다(psycopg · psycopg2 · asyncpg · sqlalchemy 모두 없음 — 11-24 확인). PG 로 가면 포털 이미지를 다시
  지어 Drive 로 보내야 하고, AIDataHub 의 재기동 · 이행이 수집기에 닿는다. 대화 저장소와 같은 꼴의 SQLite(`interactions.sqlite`, WAL)는 둘 다 없다.
- 지키던 것은 그대로다 — 포털 데이터 레지스트리의 파일이라 dev → cae00 병합 · Drive 덤프에 섞이지 않고, 백업은 portal 대상(로컬)이다.
- 크기 — 원문 1 MB 상한 · MCP 결과까지 담아도 SQLite 로 감당하는 범위(수십 GB). 가공층 분류 · 집계는 밤 배치가 읽는다. 커지면 그때 나눈다(달마다 파일).
- 계약 [contract.md](contract.md) — 스위치 둘 · 표 넷 · 게이트웨이 수집 창고와 가져가기 · 가림 규칙(공통 시험 벡터) · 공유 길 · 열람.

## IX-11 포털 몫 M1 · M2 · M3 를 지은 꼴(2026-11-24, 가지 wt1124/interactions)

- 스위치 `INTERACTIONS_ENABLED`(backend config · start.sh 가 infra/.env 값을 있을 때만 넘긴다) — 꺼지면 `/interactions/*` · `/health/interactions` 404, 원장 파일을
  열지도 않고, `/health/ready` 답 · 대화 사본(아래 IX-12 의 턴 메타)이 바이트까지 종전 그대로다. 수집기 주기는 `INTERACTIONS_INGEST_S`(기본 60, 0 이면 안 띄움).
- 원장 `interactions.sqlite` 는 대화 저장소와 같은 꼴(WAL · Lock · `with self._lock, self._conn:`). 데이터 레지스트리 클래스 `interactions`(sync: none — 박스 사이로
  옮기지 않는다) · backup-local portal · `_tighten_sqlite` 0600 · conftest 격리(`INTERACTIONS_STORE_PATH` · `INTERACTIONS_INGEST_S=0`) · test_suite_isolation.
- 수집기 원천 넷의 자리.
  - gateway — 게이트웨이가 준 불투명 cursor 를 그대로 돌려준다. 넣기(커밋) → 자리 쓰기 → ack 차례라 그 사이에 죽어도 다시 읽은 줄은 UNIQUE 가 거른다.
    ack 가 400(내준 적 없는 자리)이면 같은 자리를 되풀이하지 않는다 — 다음 쪽 자리의 ack 가 앞 조각까지 지운다.
  - conversations — 메시지 rowid 차례 · 주기마다 20,000줄까지(큰 저장소는 몇 주기에 걸쳐 백필). 끝 줄이 지워지면 rowid 가 다시 쓰이므로 자리를 max(rowid) 로 내리고
    500줄을 되돌아본다. 읽기는 제 연결 mode=ro(WAL 이라 쓰는 쪽을 막지 않는다) — 대화 저장소에 색인을 더하지 않는다(꺼진 박스의 바이트가 바뀐다).
  - procedures — 끝난(ended_at) 절차 실행의 단계 · 루틴 실행의 호출과 보고서. ended_at 자리 + 300초 되돌아보기. 돌던 · 사람 관문에 선 실행은 끝난 뒤 들어온다.
  - tool_search — 게이트웨이 `/search-log`(공유 비밀). 처음 30일, 그 뒤 지난 자리부터의 날 수(최소 2 — KST 날 경계). 뒤이은 호출(outcomes)이 나중에 붙어
    바꿔 쓰되 바뀐 것이 없으면 쓰지 않는다(ON CONFLICT … WHERE).

## IX-12 도구 호출 사건은 게이트웨이 줄 하나 · 턴 메타는 켠 박스에서만 남긴다(2026-11-24)

- 웹 챗이 부른 도구는 게이트웨이도 본다. 웹 챗 답 사건은 메시지 하나이고 그 턴의 도구 목록(activity)은 meta 로만 싣는다 — 도구 호출 사건은 게이트웨이 줄(mcp_call ·
  via chat 등)로만 센다. 절차 · 루틴 단계는 그 실행 원장의 사본(surface procedure · routine, via procedure · routine)이라 같은 호출의 게이트웨이 줄과 둘이 된다 —
  호출 수를 셀 때는 surface mcp_call 만 센다(분석가 화면 · M6 집계의 규칙).
- PLAN S2(턴 메타) — 중계가 SSE `meta`(답한 모델 · 생각 · 자기검증)와 `confirm`(확인 카드)을 답 meta.turn 으로 남긴다. **켠 박스에서만**이다 — 꺼진 박스의 대화
  사본은 종전 그대로다. 수집기는 그것을 model 칸과 meta 로 옮긴다.

## IX-13 공유 — 기록 파일은 아는 꼴만 꺼내고 원문은 가린 채 둔다(2026-11-24)

- Claude Code 기록 파일(JSONL)의 줄 꼴은 공식 문서가 '안쪽 꼴 · 판마다 바뀐다' 고 적는다(code.claude.com sessions). 그래서 type user · assistant 의 message.content
  (글 · text · tool_use · tool_result 블록)만 꺼내고, 모르는 줄은 세기만 한다(skipped). 원문은 줄마다 JSON 으로 풀어 구조 가림 → 다시 쓴 것을 zlib 으로 둔다 —
  `shared_sessions.raw`(계약 §2 에 없는 칸 — 보고의 계약 변경 제안). 꺼낸 것이 0 이어도 받는다(꼴이 바뀐 것이 messages 0 으로 드러난다).
- 공유 하나는 사건 한 줄(surface shared_claude · source share · source_ref = 공유 id)도 같은 트랜잭션에 둔다 — 내 기록 · 분석가 검색이 같은 줄로 본다. 같은 session_id 는
  덮어쓴다(주인마다). 게이트웨이의 share_conversation 호출 줄(인자에 대화)은 수집기가 건너뛴다(겹치지 않게 — 게이트웨이 작업자 확정).

## IX-14 지우기 표지(2026-11-24)

- 본인 지우기는 그 사람의 events · shared_sessions 를 지우고 `erase_marks(actor, upto)` 를 남긴다. 표지가 없으면 대화 저장소 되돌아보기 창 · 게이트웨이 창고에 남은
  그 시각 전 줄이 다음 주기에 다시 들어와 지운 것이 조용히 되살아난다. 그 시각 뒤의 일은 다시 쌓인다(수집 사실은 알린다). 열람 감사는 지우지 않는다(누가 봤는지는 남는다).

## IX-15 게이트웨이 확정 꼴에 맞춘 것(2026-11-24 — 게이트웨이 가지 wt1124/interactions f28ae6c)

- via — 게이트웨이 낱말(pat · chat · procedure · mcp-app · gw-token · service …)을 **그대로** 칸에 둔다. 계약 §2 의 여섯(pat · panel · procedure · routine · agent ·
  service)과 다르지만 짐작으로 바꿔 적지 않는다 — 계약 변경 제안.
- 캡처가 꺼진 게이트웨이는 내부 창구를 일반 인증으로 보내 401 이다 — 공유 비밀이 틀린 것과 꼴이 같다. 그래서 게이트웨이 `/health` 의 interactions.enabled 가 참일 때만
  401 · 403 을 실패로 세고, 아니면 기다림(pending)이다. 404 · 405 · 연결 거부도 기다림이다.
- args 가 1 MB 를 넘으면 글(앞부분) + args_chars — 글도 받는다(args_chars 는 meta). result_chars · sha256 은 가린 원문 전체 기준이라 그대로 쓴다. ts 는 소수 초 → 초.
- 가림 차례 PEM → (칸 이름) → Bearer → JWT, Bearer 뒤 구분은 빈칸 · 탭만(게이트웨이와 같다 — 계약 §4 의 글은 Bearer 를 먼저 적었다).
- 게이트웨이 /health interactions.errors(창고에 덧붙이지 못한 줄)가 0 이 아니면 `spool_errors` 로 붉다.

## IX-16 실패가 정상처럼 보이지 않게(2026-11-24 — IX-9 를 지은 꼴)

- 문제 코드 — collector_off(켰는데 주기 0) · collector_dead · failing:<원천>(잇단 실패 3) · stalled:<원천>(마지막 성공이 10분 또는 주기 × 10 보다 오래 — 기다림은 제외) ·
  spool_dropped · spool_errors · spool_old(창고의 가장 오래된 줄이 1시간 넘음). 내는 곳 — `/health/interactions`(문제가 있으면 503 · 무인증이라 코드 · 시각만) ·
  `/health/ready` 의 interactions 칸(켠 박스만) · 상태판 줄(gen-status-config — 켠 박스만) · 로그 경고(까닭이 바뀔 때와 10번마다) · 분석가 화면 머리.

## IX-17 PC 킷 — /hwax-share · SessionEnd 훅(2026-11-24)

- 설정 배치 [5c]. 칸이 켜지면 `%USERPROFILE%\.hwax\hwax-share.ps1`(UTF-8 BOM — 5.1 은 BOM 없는 .ps1 의 한글을 깨뜨린다) · `<설정 폴더>\commands\hwax-share.md` ·
  (자동 칸) `<설정 폴더>\settings.json` 의 hooks.SessionEnd 에 명령 글이 hwax-share.ps1 인 훅(timeout 30 — 기본 1.5초 몫으로는 큰 기록을 못 올린다). 끄고 다시 돌리면
  표지(hwax-share)가 있는 파일 · 그 훅만 걷는다. settings.json 은 엄격한 UTF-8 JSON 객체일 때만 고치고 남의 훅은 그대로다. JavaScriptSerializer 로 다시 쓰므로 한 줄
  JSON 이 된다(뜻은 같다 — .claude.json 직접 쓰기와 같은 길).
- 기록 파일 자리 — 문서 규칙 `<설정 폴더>\projects\<프로젝트>\<세션 id>.jsonl`(설정 폴더는 CLAUDE_CONFIG_DIR 먼저). 명령은 `${CLAUDE_SESSION_ID}` 를 넘긴다 — 문서는
  스킬 치환표에 적고 옛 commands 파일에서 되는지는 적지 않는다. 안 풀려 빈 값이면 지금 폴더의 프로젝트 폴더에서 가장 새 파일을 고른다. 훅은 표준입력의 transcript_path.
- 토큰은 배치가 hwax 연결에 넣은 자리(.claude.json · .config.json 의 mcpServers.hwax — headers.Authorization 또는 env.AUTH)에서 그때 읽는다(재발급을 따라간다).
  포털은 직결(프록시 없음 — 배치가 mcp-remote 에 NO_PROXY 로 주는 것과 같다). 배치가 포털 인증서를 두었으면(needs_ca) 그 인증서로 고정해 받는다(이름 불일치는 거절).
- PC 쪽에서도 줄마다 가린다(서버와 같은 정규식 글자 — 시험이 벡터로 맞댄다). 50 MB 는 파일 · 본문 둘 다 본다. 스크립트 base64 가 cmd 한 줄 상한(8191자)을 넘어
  6000자 조각(HWAX_SHARE_PS1_00 …)으로 싣는다. Windows 실시험은 사람 몫이다(이 박스에 PowerShell 이 없다).

## IX-18 분석가 열람 감사 · 화면(2026-11-24)

- 분석가 창구는 세션만(PAT 로 남의 원문을 긁지 않게). 검색도 감사 한 줄(action search · owner 는 거른 사람) — 미리보기도 원문 조각이다. 원문 열기 open · 기록 파일 원문
  open_raw. 내 기록은 PAT 도 받는다(내 것만 · 남의 id 는 없는 것과 같은 404).
- 화면 — 계정 › '내 기록'(/records) · 관리 › '상호작용 기록'(/admin/interactions, 분석가만 — 관리자가 아니어도 분석가면 관리 메뉴에 그 줄만 보인다). 켠 박스에서만 메뉴와
  알림 문구(토큰 화면 · 웹 챗 첫 화면)가 그려진다 — `/interactions/status` 가 404 면 그리지 않는다.

## IX-19 도구 검색 질의의 한계 — 게이트웨이에 청할 것(2026-11-24)

- `/search-log` 는 limit 1000 · 새것부터이고 자리(since) · 쪽이 없으며 호출자가 없다. 처음 30일 백필은 최근 1000줄까지만이고, 한 번에 1000줄이 오면 놓쳤을 수 있다고
  상태에 남긴다. 청할 것 — since(ts 또는 id) 자리 · 쪽 넘김 · 호출자(actor) 칸. 그 사이 개인 Claude 의 search_tools 호출은 수집 창고 줄(mcp_call)로도 들어온다.

## IX-20 계약을 지은 꼴에 맞춤 — via 는 게이트웨이 낱말 그대로(2026-11-24, 이 세션 판단)

- 게이트웨이(`f28ae6c`)와 포털(`wt1124/interactions`)을 짓고 나니 계약과 다른 곳이 여섯 나왔다. 계약을 지은 꼴로 고쳤다(contract §2 · §3 · §4 · §9).
- `via` — 대응표를 두지 않고 게이트웨이 낱말을 그대로 쓴다. 처음 여섯은 짓기 전의 짐작이었고, 대응표는 어긋날 곳을 하나 더 만든다.
- 게이트웨이 쪽 제안 둘(창고 줄 고유 id · 캡처가 꺼지면 404)은 받지 않았다 — 포털 열쇠(소수 초 시각 · 연결 · 요청 · 인자 · 결과 해시)가 겹치지 않고, 꺼짐은
  `/health` 로 이미 가른다. 지금 꼴로 되는 일에 두 리포를 다시 고치지 않는다.
