# 11-04 SIREN 연동 뒤 개발 쪽 요청 — 2026-11-04 · 11-05 고침 (cae00 운영 기준)

> 받은 원문(cae00 세션 → 사용자, 2026-11-05)을 그대로 옮겼다. 본문이 가리키는 `19-SIREN.md` · `SIREN-AGENT-DRAFT.md` 는 cae00 박스에만 있다.
> 이 리포의 계획 · 결정은 같은 폴더의 [PLAN.md](PLAN.md) · [context-notes.md](context-notes.md) 다.

11-04 에 SIREN 조회 창구(MCP, 도구 5개)를 cae00 게이트웨이에 '외부 연결' 로 붙이며 나온 개발 쪽 요청만 모았다. 박스에서 끝낸 일은 맨 아래 「박스에서 한 것」 이다.

SIREN 팀에 보낼 회신은 따로 [19-SIREN.md](19-SIREN.md) 다. 기준 판(11-05 update-all 뒤) — 포털 `72d297ad` · 게이트웨이 `a3ae08b` · 에이전트 서버 `a3d441f`.

11-05 고침 —

- HP-62(SIREN 운영자)는 보내지 않는다. 새 판의 박스 덧씌우기(`infra/personas/he-team.local.json`)로 cae00 에서 반영했다(4절).
- 사용자가 SIREN 을 챗뿐 아니라 심의 · 리스크 심사에서도 쓰기로 했다(11-04 밤). 그래서 에이전트 서버 HA-36 · HA-37, 리스크 앱 RK-12, 게이트웨이 HG-28 을 더했다.
- 11-05 오후 웹 챗 시험(6절)에서 게이트웨이 HG-29(SIREN 화면 링크가 가림에 깨진다) · 에이전트 서버 HA-38(쉼표로 잇댄 쪽 번호를 '확인되지 않은 수치' 로 띄운다)을 더했다.

| 받는 곳 | 높음 | 중간 | 낮음 | 한 줄 |
|---|---|---|---|---|
| HWAXPortal | 0 | 0 | 0 | 없다 — HP-62 는 박스에서 반영(11-05) |
| HWAXMcpGateway | 0 | 1 | 3 | 외부 연결 실패 안내가 한도 초과에도 '토큰 다시 등록' 이라 말한다 · 선언 백엔드에 요청 ID 싣기(선택) · SIREN 도구 영역 · 결과 속 화면 링크의 IP 가림(선택, SIREN R-9 가 먼저) |
| HWAXAgentServer | 0 | 1 | 2 | 외부 연결에서 읽기로 표시한 도구를 심의 좌석 자유 조회에 들인다 · 지정 도구 차례가 앱 접두 이름을 모른다 · 챗 수치 대조가 쪽 번호 목록을 수 하나로 읽는다 |
| HWAXRisk | 0 | 1 | 0 | 리스크 패널에 SIREN 사례를 지정 도구로 싣는다 |

## 1. HWAXPortal

보낼 것 없다. HP-62(HE팀 운영자에 SIREN 사례 조회 운영자 he-data-siren)는 11-05 13:38 에 cae00 박스 덧씌우기로 반영했다(4절). 정의 정본은 그 박스 파일이고, 초안과 근거는 [SIREN-AGENT-DRAFT.md](SIREN-AGENT-DRAFT.md) 다.

## 2. HWAXMcpGateway

### 중간

| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-26 | 외부 연결(as-conn) 호출이 실패하면 까닭과 상관없이 '토큰을 다시 등록하세요(만료·폐기 가능성)' 라고 답한다. 한도 초과 · 권한 밖 · 그쪽 서버 오류에도 사용자가 멀쩡한 토큰을 다시 발급하게 된다. 심의 · 리스크 심사에서 SIREN 을 쓰면 좌석들이 잡 주인 토큰 하나를 함께 써서 한도 초과가 더 잦다. | `gateway.py:8312`(판 `a3ae08b`) — `_call_as_user` 의 모든 예외가 같은 문구로 간다(원래 오류는 `{exc!r}` 로 괄호 안에 싣는다). SIREN 은 오류를 HTTP 200 + JSON-RPC 오류(코드 -32001, 문구 맨 앞에 `401 token_invalid` · `401 token_missing` 꼴)로 준다(11-04 실측 — 토큰 없음 · 틀린 토큰 두 번). 명세의 나머지는 `403 scope_denied` · `403 ip_denied` · `429 rate_limited` 다. 토큰당 동시 2건이라 챗이 SIREN 도구 셋을 함께 부르면 셋째가 429 가 된다. 지금은 cae00 운영자 안내(he-data-siren)가 괄호 안 원래 오류로 가르라고 LLM 에 시켜 메운다. | 예외 문구의 첫 HTTP 꼴 숫자(또는 McpError 문구 맨 앞 `401` · `403` · `429`)로 가른다 — 401 만 '다시 등록', 429 는 '잠시 뒤(Retry-After 가 있으면 그 초)', 403 은 '그쪽 권한 · 출발 IP — 관리자에게', 그 밖은 '그쪽 서버 오류'. 어느 쪽이든 다시 부르지 않는 것은 그대로 둔다. | 11-04 SIREN 연동 |

### 낮음 · 선택

| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HG-27 | 선언 백엔드(외부 연결)에 HWAX 요청 ID 를 싣지 않는다. 바깥 팀이 문제를 볼 때 양쪽 기록을 시각과 사람으로만 맞춘다. | `gateway.py:7006` `_request_corr()` 는 `X-HWAX-Corr` 를 감사 줄에만 쓴다. 선언 백엔드로 나가는 머리글은 그 사람의 Bearer 와 선택 `workspace_header` 뿐이다. SIREN 발급 안내 4장 ⑥ 이 `X-Request-Id` 를 선택으로 묻는다. | 선언 백엔드 호출에 `X-Request-Id: <corr 또는 호출마다 새 UUID>` 를 싣는다(접속 설정 `connect:` 에 켜고 끄는 키를 두면 더 좋다). 감사 줄에 같은 값을 남긴다. | SIREN 4장 ⑥ |
| HG-28 | `tool_areas.json` 에 SIREN 영역이 없어 다섯 도구가 '미분류' 로 보인다. 운영자 프롬프트의 도구 묶음 · 허브 보기도 미분류로 묶는다. | `tool_areas.json` 에 `siren` 0건(11-05 cae00). `gateway.py:4195` — 영역이 없으면 `미분류`. 11-05 update-all 도 같은 것을 비치명 항목으로 알렸다. | `tool_areas.json` 에 SIREN 영역(예: 키 `siren` · 라벨 '사내 불량 · 대책 사례')을 더하고 siren_search_cases · siren_get_case · siren_list_groups · siren_list_docs · siren_get_doc 를 넣는다. | 11-05 update-all |
| HG-29 | 선언 백엔드 결과 속 화면 링크의 사설 IP 를 가려 링크가 깨진다. 11-05 웹 챗 시험에서 SIREN 사례 링크 여섯 개가 모두 `http://[가림:IP]:<포트>/?…` 꼴이 되어 열리지 않았다. | `gateway.py:879` `_ip`(판 `a3ae08b`) — 사설 IPv4 는 칸 이름과 상관없이 꼴로 가린다(HG-22 · 사용자 결정 D-2, 손잡이는 전체 끄기 `GATEWAY_PII_MASK=0` 뿐). SIREN 결과의 `link` 칸(검색 hits[].link · 사례 카드 link)이 IP 주소로 온다. 박스 타일(systems.cae00.yaml 의 siren)은 이름 주소다. | 먼저 SIREN 에 이름 주소 링크를 청했다(19-SIREN R-9). 그쪽이 못 하면 — 접속 설정 `connect:` 에 '가리지 않을 주소' 키(예: `mask_keep_hosts`)를 두고, 그 호스트로 시작하는 URL 만 가리지 않는다. 다른 사설 IP 가림은 그대로 둔다. | 11-05 웹 챗 시험 |

## 3. HWAXAgentServer

### 중간

| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-36 | 심의 좌석의 자유 조회가 읽기 도구를 이름의 동사 접두로만 고른다. 그래서 게이트웨이가 읽기로 표시한 외부 연결(선언 백엔드) 도구가 빠진다. SIREN 다섯 도구(`siren_*`)는 앱 이름이 앞에 붙어 있어 좌석이 부르지 못한다. 앞으로 외부 연결로 붙는 플랫폼도 이름 꼴이 같으면 똑같이 빠진다. | `deliberation.py:4380` `_FREE_ALLOW` 는 접두 튜플(`list_` · `get_` · `search_` …)이다. `:4422` `_free_tool_ok` 가 이것으로 판정하고, `:6411` 의 좌석 도구 조립이 그 판정을 쓴다. 게이트웨이 `/tools-map` 에서 siren 다섯은 읽기다(박스 권한표 `connect.read_tools` — 11-04). 지금은 '지정 도구'(delib_opts.tools, 최대 6 — `:114` `_TOOLS_MAX`)로만 SIREN 결과를 좌석에 줄 수 있다. | 선언 백엔드(외부 연결)의 도구 가운데 게이트웨이가 읽기로 확인한 것(`/tools-map` 의 읽기 표지 · routine_read)을 자유 조회 후보에 들인다. `_FREE_DENY` · 리스크 심사 D-18 · 기준일 거름은 지금처럼 이것보다 앞선다. 한도도 함께 본다 — 좌석들은 잡 주인 토큰 하나를 같이 쓴다(SIREN 은 토큰당 동시 2건 · 검색 1분 10번). 잡 안에서 선언 백엔드마다 동시 호출을 줄 세우는 손잡이(기본 2)를 두고, 429 를 받은 백엔드는 그 잡에서 다시 부르지 않는다. 같은 인자는 잡 캐시(`_fcache`)가 이미 합친다. | 11-04 사용자 결정(심의에서 SIREN) |

### 낮음

| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| HA-37 | 지정 도구를 목록 · 검색 먼저 부르도록 차례를 다시 매기는데, 앱 이름이 앞에 붙은 도구는 그 판정에 걸리지 않는다. 사용자가 고른 차례가 체크박스 차례라서 siren_get_case 가 siren_search_cases 보다 먼저 불리면 사례 ID 를 몰라 건너뛴다. | `deliberation.py:6562` — `key=lambda n: 0 if n.startswith(("list_", "search_", "find_")) else 1`. `siren_list_groups` · `siren_search_cases` 는 둘 다 1 로 간다. | 판정을 이름 전체가 아니라 앱 접두를 뗀 꼴(또는 `_list_` · `_search_` · `_find_` 가 든 꼴)로 한다. 접두를 아는 것은 게이트웨이 `/tools-map` 의 도구 → 앱 매핑이다. | 11-05 SIREN 심의 점검 |
| HA-38 | 챗 답의 수치 대조가 쉼표로 잇댄 쪽 번호(`p.2,3,10,11,23`)를 천 단위 수 하나로 읽어 '위 조회 결과에서 확인되지 않은 수치' 로 띄운다. 맞는 쪽 번호가 출처 없는 값처럼 보여 사람이 답을 의심한다. | `app.py:1802`(판 `a3d441f`) — 수치 토큰이 '천단위 콤마와 소수점을 포함해 원문 표기 그대로' 잡는다. 표시는 `:1832`(근거 블록 `_evidence_block`, `:1814`). 11-05 웹 챗 시험 — 띄운 값 `3,10,11,23` · `18,35` 는 근거 문서의 쪽 번호다(SIREN 결과의 evidence[].page 는 쪽마다 따로 온다). 같이 뜬 `4.4`(사람 확정 99 / 2,270 의 비율)는 계산 값이라 맞게 띄웠다. | 천단위 콤마는 쉼표 뒤 묶음이 모두 세 자리일 때만 수 하나로 본다(`\d{1,3}(,\d{3})+`). 그 꼴이 아니면 쉼표로 나눠 하나씩 대조한다. | 11-05 웹 챗 시험 |

## 4. HWAXRisk

리스크 앱 소스는 cae00 에 없다(SIF 와 데이터 `/data/appdata/hwax_risk` 만 있다). 그래서 앱 쪽 파일 · 줄은 적지 못했다. 에이전트 서버 주석이 가리키는 패널 질문 자리는 `runner.panel_question` 이다.

### 중간

| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| RK-12 | 리스크 패널 심의에 SIREN 사례(사내 부품 불량 · 대책)가 들어가지 않는다. 같은 부품 · 현상의 과거 사례와 대책을 패널이 보지 못한다. | 에이전트 서버 판 `a3d441f`. 리스크 심사 좌석의 자유 조회는 `_FREE_ALLOW` · 앱 조건부 `_RISK_READ_TOOLS`(`deliberation.py:968`) · 의장 조건부 `_RISK_KEEP_TOOLS`(`:1076`)로만 연다(`:6411` 조립). `siren_*` 은 셋 어디에도 없다. 지정 도구(delib_opts.tools, 최대 6)는 리스크 심사에서도 D-18 갈래(`_risk_designated_refusal`, `:1035`)만 거절하므로 siren 다섯은 부를 수 있고, 결과는 모든 좌석 프롬프트에 실린다. 부르는 신원은 잡 주인(X-HWAX-User)이고, 게이트웨이는 그 사람이 등록한 SIREN 토큰을 쓴다. SIREN 은 바깥 사례 DB 라 같은 과제의 앞 판정이 실리지 않는다(D-18 과 부딪히지 않는다). | 러너가 패널 심의를 띄울 때 부품 · 현상이 걸린 패널이면 delib_opts.tools 에 `siren_list_groups` → `siren_search_cases` → `siren_get_case` 를 **이 차례로** 싣는다(6자리 안에서 남은 몫만큼, HA-37 전에는 차례가 그대로 간다). 잡 주인이 SIREN 토큰을 등록하지 않았으면 셋 다 등록 안내로 끝난다 — 패널은 그대로 가고, 결과 카드에 'SIREN 미연결' 로 남긴다. 근거 표에 사례마다 trust(사람 확정 · 검토 중 · AI 초안)를 칸으로 남기고, 사람 확정이 아닌 사례는 후보로만 적는다. 패널 명단에 cae00 운영자 he-data-siren 을 앉히는 것은 선택이다(좌석 역할은 summary 를 쓴다). | 11-04 사용자 결정(리스크 심사에서 SIREN) |

## 5. 이 문서에서 뺀 것

- 리스크 심사 좌석의 자유 조회 목록(`_RISK_KEEP_TOOLS`)에 siren 을 더하는 길 — 11-05 사용자가 리스크 앱 쪽 요청(RK-12)을 골랐다.
- 읽기 표지 — SIREN 도구에 readOnlyHint 가 없어 박스 권한표(`backend/config/` 의 로컬 권한표 yaml)의 `connect.read_tools` 로 다섯 도구를 읽기로 표시했다(게이트웨이 `/tools-map` 에서 다섯 모두 `readOnlyHint: true`). 추적 `read_tools.json` 은 고치지 않았다. SIREN 에 표지를 청했다(19-SIREN.md R-1).

## 6. 박스에서 한 것 (cae00)

**11-04 13:22 ~ 13:40 KST — 연결**

- 사본 — `~/portal-backups/siren-20261104-132244/`(박스 권한표 · systems.cae00.yaml · infra/.env · hwax.conf · start.log).
- 박스 권한표(`backend/config/` 의 로컬 권한표 yaml) — 플랫폼 `siren`(systems · gateway `siren`, `connect:` — 조회 창구 주소 · 토큰 머리 `siren_`(처음엔 명세대로 `siren_pat_` 였으나 11-04 실발급 토큰이 `siren_` 로 시작해 20:24 에 바꿨다 — 사본은 `~/portal-backups/` 의 `*.siren-prefix-20261104-202450`) · `verify: none` · `list_auth: open` · `read_tools` 다섯). `verify: none` 인 까닭 — SIREN `initialize` 가 아무 토큰에나 200 이라 등록 때 맞는지 알 수 없다.
- `backend/config/systems.cae00.yaml` — 타일 `siren`(external-url · SIREN 화면 · sort_order 48).
- `infra/.env` — `NO_PROXY` · `no_proxy` 끝에 SIREN 서버 IP. 게이트웨이는 선언 주소를 기동 중에 스스로 프록시 밖으로 빼므로 다음 재기동 대비다.
- 게이트웨이는 다시 띄우지 않았다. 선언을 1분 안에 읽어 `siren: ok`, 도구 5개가 원래 이름으로 붙었다. 토큰 없는 사람의 호출은 게이트웨이에서 멈추고 등록 안내를 돌려준다(SIREN 으로 가지 않는다 — 11-04 실측).
- 첫 사람 신원 호출 — 사용자가 SIREN 토큰을 '외부 연결' 카드에 등록한 뒤 22:45:52 에 게이트웨이로 `siren_list_groups` 를 한 번 불렀다. 성공(301 ms), 감사 줄 `mode=as-conn` · 부른 사람 · 토큰 지문이 남았다. 검색 · 사례 카드 · 원고는 시험 날 SIREN 과 함께 본다(trust 칸 이름 대조는 그때).
- 포털만 다시 띄웠다(감시 크론을 내리고 → `hwax_portal` 정지 → `HWAX_NO_BUILD=1 start.sh` → 감시 크론 복구). 멈춘 시간 약 3초, 타일 21 → 22. 새로 지은 hwax.conf 는 사본과 같았다(/ste/ 3600 s 그대로).

**11-05 13:38 KST — SIREN 운영자(he-data-siren), 포털 `72d297ad`**

- 사본 — `~/portal-backups/siren-persona-20261105-133822/`(반영 전후 에이전트 `/health` · AIDataHub 조회 · apply 기록). 덧씌우기 파일은 그 전에 없었다(지문 `d460e82e2850`).
- `infra/personas/he-team.local.json`(gitignore 박스 파일)을 새로 두었다 — `personas` 에 `he-data-siren` 하나(묶음 data · 앱 siren · 도구 다섯은 읽기라 writes · confirm 비움). 미리보기 · `--check` 에 ✗ 없음, 프롬프트 2,261자(한도 8,000).
- `sync-he-personas.py --apply` — 새로 1 · 고침 0 · 그대로 18 · 건너뜀 1. AIDataHub 전문가 800 → 801.
- 에이전트 `/health` `confirm_gate.lists.overlay` — state ok · added he-data-siren · 지문 `86a974686d00`(미리보기와 같다). 다시 돌린 미리보기는 새로 0 · 그대로 19. 재기동 없음.

**11-05 14:55 ~ 15:03 KST — 웹 챗 시험 한 번(박스 변경 없음)**

- PC 의 시험용 Edge(CDP)에서 사용자가 SSO 로그인한 창으로, 전문가 he-data-siren 을 고르고 운영자 예시 질문 '카메라 모듈 소음 관련 과거 사례와 대책 찾아줘' 를 보냈다(14:55:46). 답까지 70초, 챗 모델 qwen3.8-flash-next.
- 게이트웨이 감사 — 14:56:14 ~ 14:56:33 에 siren 6번(list_groups 1 · search_cases 3 · get_case 2), 모두 ok · `mode=as-conn` · 부른 사람 = 사용자 · `via=chat`. 결과 확인으로 15:03:11 ~ 15:03:16 에 같은 신원으로 search_cases 1 · get_case 2 를 더 불렀다(`via=gw-token`). 동시 2건 · 검색 1분 10번 안.
- 운영자 규칙은 지켰다 — groups 를 늘 주고, 한 · 영으로 따로 찾고, 사례 카드는 둘만 열고, 사례마다 trust 를 적었다(SIREN 결과와 맞춘 11건 모두 같음). AI 초안이 대부분인 축에는 '가설 · 후보' 주의를 붙였고, 처리 범위 약 14% · '근거 없음 ≠ 리스크 없음' 도 적었다.
- 안 된 것 — 화면 링크 여섯 개가 가림에 깨졌다(HG-29 · SIREN R-9). 수치 대조가 쪽 번호를 띄웠다(HA-38).
- 실제 결과 칸 — trust 는 human_confirmed 같은 값이 아니라 글(「확정(사람 검증)」 · 「AI 초안 — 미검증」 · 「확정(사람 검증) · 원인은 원문에 없어 추정」)이다. 칸별 `fields.*.trust` · `flags.why_inferred` · `human_verified` · `tier` 가 오고, `analysis.inferred` 는 없다.

**11-05 17:12 KST — 운영자 글을 실제 결과 칸에 맞춤(사용자 확인 뒤)**

- 사본 — `~/portal-backups/siren-persona-v2-20261105-171207/`(앞 판 덧씌우기 파일 · 에이전트 `/health` 전후 · AIDataHub he-data-siren 행 · apply 기록). 바꾸기 전에 박스 파일이 13:38 판(sha 앞 16자 `82d91657d9d2962b`)과 같은지 보고 바꿨다.
- 고친 것 — can(검색 hits · 사례 카드 fields 네 칸의 실제 칸 이름), workflow 넷째 줄(trust 글을 그대로 적기, link 에 '[가림:' 이 있으면 링크 대신 사례 ID 와 포털 SIREN 타일 안내), concepts 첫 셋(trust 글 값 · human_verified, 원인 추정은 trust 글 · flags.why_inferred · why_ai_estimated · fields.why.trust 로 가르고 caveat 를 함께 적기, '사람 확정 1% 아래' 대신 그룹별 수는 siren_list_groups 로). 나머지는 그대로다.
- `sync-he-personas.py --apply` — 새로 0 · 고침 1 · 그대로 18 · 건너뜀 1. AIDataHub 프롬프트 2,261 → 2,748자(한도 8,000), 전문가 801 그대로.
- 에이전트 `/health` overlay — state ok · 지문 `3f597f81391a`(미리보기와 같다). 다시 돌린 미리보기는 고침 0 · 그대로 19. 재기동 없음.
- 되돌리기 — 사본의 `he-team.local.json` 을 `infra/personas/` 에 되돌려 두고 `sync-he-personas.py --apply`.
- 다시 시험(17:13:10, 같은 질문) — 답 55초, siren 7번(목록 1 · 검색 3 · 카드 3, 카드는 하나씩 차례로), 모두 ok · as-conn · 사용자 · `via=chat`. 링크 0개, 끝에 '링크는 IP 가림으로 열리지 않는다 — 포털 SIREN 타일에서 source_case_id 로 찾으라' 한 줄. trust 글을 그대로 적었고, 원인 추정 사례는 '원인: 추정 — 원문에 …없음' 으로 썼다. min_trust=human_confirmed 검색 0건을 'SIREN 에 검증된 근거가 아직 없다(리스크 없음 아님)' 로 읽었다. 이번에는 수치 대조가 아무것도 띄우지 않았다(검증 ✓ — 쪽 번호를 `p.11, p.15` 처럼 따로 적었다).
