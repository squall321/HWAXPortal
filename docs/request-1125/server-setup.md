# cae00 절차 — 운영 요청 모음(11-24) 포털 몫(1-1 · 1-12 · 2절, 11-28 가지 `wt1128/r1125-portal`)

> 결정과 까닭은 [context-notes.md](context-notes.md) R25-28. 이 절차는 포털 판이 main 에 들어간 뒤 update-all 로 받은 박스에서 한다.
> 쓰기 · 재기동은 표시한 걸음만 사람이 정한다. 명령 꼴은 받은 편지함 README 의 '명령 꼴'(앱 데이터 `${HWAX_DATA_ROOT:-/data}/appdata/<앱>` · SQLite 는 `roq`).

## 0. 받기 전에 넣을 것(update-all 이 ✗ 를 내지 않게)

- **게이트웨이 읽기 목록에 한 줄** — 새 §6 점검(HP-59)이 dev 에서 `heax-kooremapper_mcp:list_session_files`(GET 조회인데 읽기 목록에 없다)를 ✗ 로 잡았다.
  운영 박스도 같으면 update-all 이 끝 코드 1 이다. 게이트웨이 정본에 더해질 때까지 박스 덧씌우기 `HWAXMcpGateway/read_tools.local.json` 의 `tools` 에
  그 한 줄을 넣는다(재기동 없이 먹는다). 다른 줄이 ✗ 로 나오면 그 '백엔드:이름' 이 조회인지 보고 같은 자리에 넣는다.

## 1. 받은 뒤 확인(읽기)

| 항목 | 확인 |
|---|---|
| SE-9 | 실행 기록의 단계 제목 줄 꼬리에 `[HH:MM:SS]` |
| SE-2 | §1b 에 'AIDataHub 덤프는 뒤에서 뜬다(로그 …)' · deploy-all AIDataHub 구획에 기다림 줄(재기동이 정해졌을 때만) · 끝 요약 앞 '✓ AIDataHub 사전 덤프'. §1b + §2 합계가 줄었는지. 새 덤프 `…-pre.sql.gz` 를 `gunzip -t` · 시험 DB 복원으로 한 번 본다. update-all 이 뜬 `-pre` 와 병합 전 덤프 `pre-merge-*` 는 대상마다 새 둘만 남는다(`PRE_KEEP`) |
| SE-7 | SignalForge 구획에 덤프 받기 줄이 한 번 · 병합 줄 '(받은 덤프 sf-db-….sql.gz)'. 다음 실행에서 같은 덤프면 'DB MERGE 건너뜀'. 기록은 `infra/.state/sf-merge-last` |
| HP-58 | `./infra/scripts/env-sync.sh --check` 가 `AIDataHub/deploy/apptainer` 의 빠진 키를 이름으로 낸다(자동으로 넣지 않는다 — 필요한 줄만 손으로) |
| HP-59 | §6 에 '리스크 앱 조회 도구 N개 — 게이트웨이 읽기 판정을 지난다'(0 절을 했으면) |
| HP-68 | `KOORM_LOCAL_PARKED` 박스에서 kooremapper 장애 안내가 로컬 :8700 · :8701 · deploy-all kooremapper 대신 실제 업스트림 · '운영 노드 쪽을 본다' |
| HP-69 | `./infra/scripts/update-forges.sh stepforge` 가 덮어쓰기(프록시) 박스에서 '○ step_forge 건너뜀' · 끝 코드 0 |
| HPO-1 · HPO-4 · HP-82 | 박스 덧씌우기 `core_vocab.local.json` 의 lookup 다섯 줄 · apps 형제 둘을 걷은 뒤 게이트웨이 `/health` 의 core_vocab overlay · `roles.family` 다섯 · `ontology_lookup`(고장모드 key) 다음 호출 7줄 · 과제코드 9줄 · '실드캔 부품' 이 part exact. ⚠ 심의 '온톨로지 먼저 보기' 이웃 타입에 part 가 들었다(상한 60 · 4,000자 그대로) — 실제 과제 하나로 다른 이웃이 밀리는지 본다. 기본 `card-entity-bind.py`(타입 없이)에도 part 가 든다 — 부품을 아직 잇지 않으려면 2 절 |
| IR-01 · 02 · 07 · 08 | 시험 덱을 '이 대화에서 분석' 으로 — 2 ~ 4쪽 그림 물음에 답한다 · 감사 줄 `upload_dispatch` meta 에 vlm · snapshot_page · llm true · DocForge 판단 캐시에 새 항목. 끄기 `infra/.env` 에 `DOCFORGE_CHAT_VLM=false` + 포털 재기동(사람) |
| IR-03 · 04 · 05 · 06 · WD-11 | 그림 있는 덱을 붙이면 칩 · 완료 문구에 '그림 N · 판독 M' (판독 0 이면 안내) · DocForge 권한 없는 계정도 같은 문구 · 새 대화에서 칩이 비었다 · 차트 · 노트 있는 덱의 고르기 화면에 정밀 변환 '권함' · 잠긴 PPT 는 DRM 안내 |
| HP-60 | ste 잡이 도는 동안 `infra/scripts/deploy-ste.sh` 를 바로 부르면 rc 1 · 까닭 한 줄, `--force` 면 진행. update-all 은 '실행 중 ste 잡 N개 — 이번에는 바꾸지 않는다'(○) |
| HP-57 | `touch infra/.state/maintenance` 동안 `~/.local/state/hwax/watchdog.log` 에 down/up 줄이 없고 지우면 다시 돈다. update-collab 한 번 도는 동안도 없다 |

## 2. 사람이 정하는 걸음

1. **nginx MCP 직결(HP-72 · HP-74 · HP-75)** — 기본은 둘 다 꺼짐이고 HP-74(끝 슬래시 308)는 저절로 붙는다.
   - 박스 중계를 걷으려면: 네 경로(데이터허브 셋 · MX 백서)의 routes.local.env 줄을 중계 대신 터널 포트로 돌리고 `infra/.env` 에
     `NGINX_UPSTREAM_HOST_ROUTES=<그 넷의 라우트 이름, 쉼표>` → `./infra/scripts/gen-nginx-conf.sh`(nginx -t 통과) → nginx 재기동. 포털 도메인 Host 로 보낸
     initialize 가 200 이면 중계를 내린다.
   - 평문 막기: `NGINX_TLS_ONLY_ROUTES=*-mcp` → 같은 차례. 8088 의 `/<id>-mcp/mcp` 가 사내망 주소에서 403, 443 은 200. 이 박스의 게이트웨이 · 점검이 루프백으로
     부르는 길은 그대로다 — 다른 박스가 8088 로 부르는 *-mcp 가 있으면 먼저 https 로 바꾼다.
2. **카드 ↔ 부품 잇기(HPO-2 · 부록 A D-2)** — AIDataHub 의 타입별 다시 쓰기(AD-22) 판이 들어간 뒤에만 된다(앞 판이면 명령이 '다른 타입 연결이 지워진다'
   로 멈춘다). `card-entity-bind.py --only-types part --dry-run` 로 수를 보고, 뜻이 섞인 낱말(25개 — 운영 쪽 결정 대기)을 `onto_rules.local.json` 에 정한 뒤
   `--only-types part` 로 잇는다. 요약에 타입별 전후 수 · 연결 0 인 타입의 까닭이 나온다.
3. **서비스 감시 표지(HP-57)** — 손으로 오래 내릴 때 `touch infra/.state/maintenance`, 다 올린 뒤 `rm infra/.state/maintenance`.
4. **AIDataHub 덤프를 종전대로 함께 뜨려면** `HWAX_AIDH_BACKUP_BG=0`(SE-2). 03:30 일일 덤프를 배포 전 롤백 지점으로 쓸지(SE-2 ③)는 사용자 결정(SYNCEFF-4) 뒤.

## 3. WD 포털 몫(가지 `wt1128/wd-portal` — WD-03 · 04 · 05 · 06 · 08 · 13, R25-29)

> 받는 판의 짝 — 에이전트 서버 main `b8de57b`(WD-03 c27c13e · WD-05 f955eff · WD-06 eb3dd1d · WD-08 b1007bf · WD-13 3c6a54d)와 게이트웨이 `2b89a32`(WD-04).
> 에이전트 서버가 앞 판이면 포털 당기기가 경고 로그 'WD-03(c27c13e) 전의 판이다' 를 남기고(대화가 안 생긴다) 이어가기는 `agent_outdated` 로 거절된다.

| 항목 | 확인(읽기) |
|---|---|
| WD-03 | 포털 재기동 뒤 60초 안에 포털 로그 'MCP 심의 대화 — 새 대화 N …' (처음 한 번은 지난 MCP 심의를 다 들인다 — 커서 0). 끄기는 `backend/.env` 의 `DELIB_CONV_SYNC_S=0` + 포털만 재기동(사람). 들인 수는 `roq <대화 저장소> "select count(*), count(distinct conversation_id) from mcp_delib_jobs"` |
| WD-03 | 개인 Claude 로 짧은 심의 하나(시험 심의 — 가장 작은 판)를 끝내면 심의 페이지 사이드바에 'MCP' 표지 대화가 서고, 같은 잡을 다시 끝내도(경계) 하나다. 이어하기 잡은 같은 대화에 붙는다 |
| WD-04 | 개인 Claude 가 `save_conversation`(activity 를 실어)으로 저장한 대화를 웹에서 열고 '원 도구 결과가 있니?' — 결과 원문 인용. 사이드바는 새로 고침 없이 1분 안에 선다 |
| WD-05 | 들인 MCP 심의 대화에서 '이어가기' → 진행 카드 · 에이전트 서버 원장의 새 잡 `continues` 가 앞 잡 · 끝나면 같은 대화에 다음 회차가 붙는다 |
| WD-06 | 웹 챗에서 심의를 시켜 확인 카드가 서면 맨 위 요약(종류 · 라운드 · 좌석 · RA 저장 · 근거 · 앱). 종류를 바꾸고 '바꾼 대로 실행' → 에이전트 서버 로그 '[confirm] 카드 … 고침 — deliberate_start 의 job' |
| WD-13 | 같은 승인 뒤 진행 카드 → 끝나면 보고서 링크 · '심의 페이지에서 결정문 보기' |
| WD-08 | 사이드바 '엔진 심의 잡 찾기' — 보름 전 날짜로 찾고 결정문 전문 · '이 대화에 싣기' · '더 보기' |

⚠ 대화 주인 키 — 들인 대화는 그 이메일로 낸 사람 PAT 의 sub(없으면 이메일)로 쓴다. 운영 박스 SAML 은 sub 가 이메일이라 맞다. sub 를 이메일이 아닌 값으로 쓰는
박스(OIDC `oidc_claim_subject`)에서 PAT 를 한 번도 내지 않은 사람(웹 챗 확인 카드로만 연 심의)의 대화는 그 사람에게 보이지 않는다 — 그런 박스면 알린다.

