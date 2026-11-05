# SIREN 을 심의 · 리스크 심사에서 — cae00 절차(사람 몫)

> 대상: cae00 운영자. 계획 [PLAN.md](PLAN.md), 결정 [context-notes.md](context-notes.md). 올린 판은 `docs/request-1030/server-setup.md` 0절이 정본이다.

## 0. 받을 판

| 무엇 | 판 | 받는 길 |
|---|---|---|
| 포털 · 게이트웨이 · 에이전트 서버 | 포털 `518190d3` · 게이트웨이 `469f724` · 에이전트 서버 `5cd1938` | `update-all` 하나로 받는다(포털 → 게이트웨이 → 에이전트 서버 재기동 — 심의가 돌면 에이전트 서버 재기동은 미룬다) |
| 리스크 앱(hwax-risk) | `97d5aef` · Drive(HEAXHub) `dist-20261105-211248Z`(latest 에도) | `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk` — 스키마 · 이관 없음 |

⚠ **박스 권한표에 새 칸(`request_id` · `mask_keep_hosts`)을 적는 것은 새 판을 받은 뒤다.** 옛 포털은 모르는 칸이 든 `connect:` 블록을 통째로 버린다 —
먼저 적으면 SIREN 연결이 빠진다(SD-14). 이번 판은 새 칸이 없어도 그대로 돈다.

## 1. 받은 뒤 확인

1. **도구 영역(HG-28)** — 게이트웨이 `/tools-map` 의 `areas` 에서 siren 다섯이 `quality` 다. update-all 의 '미분류' 비치명 항목에서 siren 이 빠진다.
2. **실패 안내(HG-26)** — 토큰을 등록하지 않은 계정으로 SIREN 도구를 하나 부르면 지금처럼 등록 안내다. 등록한 계정으로 동시에 셋을 부르면 셋째가 `(429 — …)`
   안내이고 '다시 등록' 이라고 하지 않는다. 감사 줄(`audit.jsonl`)의 실패 줄에 `caller` · `mode: as-conn` · `note` 의 `status:429` 가 있다.
3. **요청 ID(HG-27)** — SIREN 호출 감사 줄에 `rid`(32자 16진)가 있다. SIREN 쪽 기록의 `X-Request-Id` 와 같은 값이다(SIREN 팀에 물어 맞춘다).
4. **심의 좌석(HA-36)** — SIREN 이 걸릴 만한 주제로 일반 심의를 하나 돌린다(시험 심의는 가장 작은 모델). 좌석 조회에 `siren_*` 가 보이고, 결과 카드 머리에
   '[외부 연결 siren 의 결과 — …]' 안내가 있다. 감사 줄로 같은 시각에 SIREN 을 두 건보다 많이 부르지 않았는지 본다(손잡이 `DELIB_CONN_CONCURRENCY`, 기본 2 —
   에이전트 서버 `.env`, 재기동해야 먹는다).
5. **리스크 앱(RK-12)** — 관리자로 `GET /apps/hwax_risk/api/meta/runtime` 의 `knobs.HWAXRISK_CASE_TOOLS` 가 `["siren_list_groups","siren_search_cases",
   "siren_get_case"]`(출처 default)다. 새로 짜는 보통 패널의 지정 도구 끝에 `siren_list_groups` · `siren_search_cases` 가, 쟁점 패널에는 셋이 있다(이미 짜 둔
   패널은 그때의 도구 그대로다). 실은 도구는 패널 품질(`GET /api/targets/<key>/panels` 의 `quality.case_tools`)에, 싣지 않은 까닭은 `case_tools_skipped`
   (`claude_job` — Claude 잡은 싣지 않는다 · `llm_cap` · `gateway_unread`)에 남는다. 잡 주인이 SIREN 토큰을 등록하지 않았으면 패널은 끝까지 가고
   `conn_unregistered: ["SIREN"]` 과 플래그가 남는다. 보고서 회의록 '[품질 플래그]' 에도 같은 줄이 선다.
6. **수치 대조(HA-38)** — 챗에서 SIREN 사례를 찾아 답이 쪽 번호를 `p.2,3,10` 처럼 잇대 적어도 '확인되지 않은 수치' 에 뜨지 않는다.

## 2. 고를 것(필요할 때만)

- **SIREN 링크의 사설 IP 가림 예외(HG-29)** — SIREN 이 이름 주소 링크를 주면(19-SIREN R-9) 할 것 없다. 못 주면 박스 권한표 siren 항목의 `connect:` 에
  `mask_keep_hosts: ["<SIREN 서버 사설 IPv4>"]` 한 줄을 더한다(포트 없이, 사설 IPv4 글자만 — 다른 꼴이면 블록을 버린다). 포털이 다음 요청부터 읽고 게이트웨이가
  1분 안에 받는다. 그 주소로 여는 링크만 풀리고 다른 사설 주소 가림은 그대로다. 운영자 글(he-data-siren)의 '링크에 [가림: 이 있으면 …' 줄은 그 뒤에 걷는다.
- **요청 ID 끄기(HG-27)** — 그쪽이 머리글을 거부하면 `connect:` 에 `request_id: false`.
- **리스크 패널의 SIREN 끄기 · 바꾸기(RK-12)** — 리스크 앱 `$DATA_DIR/knobs.env`(`/data/appdata/hwax_risk/knobs.env`)에 `HWAXRISK_CASE_TOOLS=off`(끔) 또는
  쉼표 목록(차례 그대로, 6개까지). 고친 뒤 `redeploy-app.sh hwax-risk`.

## 3. 되돌리기

- 게이트웨이 · 에이전트 서버 · 포털 — 앞 판으로 되돌리는 길은 update-all 의 판 고정과 같다(0절 앞 줄의 판). 새 칸을 적었으면 먼저 지운다.
- 리스크 앱 — 앞 Drive 판(`dist-20261103-011742Z`)으로 `dist-from-drive.sh` 를 다시 받는다. 또는 손잡이 `HWAXRISK_CASE_TOOLS=off` 만으로 SIREN 싣기를 끈다.
