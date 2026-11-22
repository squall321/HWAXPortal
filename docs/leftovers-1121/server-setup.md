# 남은 일 전부 진행(11-21) — cae00 절차

> 2026-11-22(KST). 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md) L21-4 ~ L21-10 이다.
> 받을 판(묶음 A) — 게이트웨이 `9b5ab25` · `9224bd1`(master `210a50c`) · 에이전트 서버 `b33a728`(main `cde6eb0`) · 포털 `72f828cd` · `34766ff1` ·
> `31d08cb4`(main `aeec26d1`) · AIDataHub `1fe55d7`(main `09ecc04`). 모두 main 에 `--no-ff` 로 합쳤다.
> 받을 판(묶음 B · 11-22) — 게이트웨이 `bd37738` · `26183c3` · `d2878f9`(master `0e113bd`) · 에이전트 서버 `29f8554` · `5aa25c4` · `db4b75e` ·
> `a291297` · `fd6a4fc` · `d058c5c` · `190c8f4` · `ca02ada` · `ee8d5db` · `26c78f2`(main `ee26311`) · 포털 `3dfebc6e` · `1bb54c55` · `18016612` ·
> `e4cb252e` · `951fe9c6`(main `67fccb15`) · AIDataHub `9d2ced1` · `d2fa5c5`(main `b2f1b72`). 6절이 받는 것만으로 달라지는 것이다.
> 받을 판(묶음 C · 통합 판 11-22) — 게이트웨이 master `eb6fee8` · 에이전트 서버 main `ec90cb6` · 포털 main `c7cc3852` · 리스크 앱(HWAXRisk) main `699bba8`
> (허브 앱 — Drive SIF 를 함께 받는다). 7절이 받는 것만으로 달라지는 것과 스위치다.
> 대조 시점 — dev 11-22. 묶음 A 를 지을 때 dev 에는 Report Archive 가 떠 있지 않아 RA 에 닿는 것은 전부 가짜 RA 시험이었다. 그 뒤 dev 에 RA 최신판을
> 띄웠지만(context-notes L21-14) 사람 자격이 드는 실호출은 아직 못 했다 — 아래 3 · 4절이 진짜 RA 로 보는 첫 확인이다.

리포 자리는 박스마다 다르다 — 아래는 포털 리포 루트에서 형제 리포를 `../AIDataHub` 처럼 부른다. `$PY` 는 게이트웨이와 같은 파이썬(venv)이다.

## 1. 받기 — update-all 한 번

받는 것만으로 달라지는 것은 넷이다. 나머지는 이 박스에서 켜야 달라진다(5 · 6절).

| 달라지는 것 | 어디서 보나 |
|---|---|
| 챗에서 RA 의 `create_report_from_format`(양식으로 올리기)을 부르면 늘 확인 카드가 뜬다. 절차는 사람 승인 단계가 있어야 저장되고, 범용 실행기 · 화면 패널로는 못 부른다 | 에이전트 서버 `/health` 의 확인 관문 목록 수 · 포털 절차 저장 |
| 위임으로 RA 를 부를 때 부서 머리를 싣지 않는다 — RA 가 그 사람의 홈 부서로 정한다 | 2절 |
| 계정을 정지하면 RA 쪽 위임 토큰도 지운다(포털이 받은 것 · 게이트웨이가 받은 것). 위임이 꺼진 박스는 그 칸이 `off` 다 | 관리 › 사용자 정지의 응답 `app_revocations.reportarchive` |
| RA 가 본인 명의 토큰을 내주지 않을 때 안내가 까닭을 짚는다 | 챗 PPT 가져오기 · 보고서 그림 · 발표자료의 오류 글 |

## 2. 위임일 때 부서 머리 — 확인(읽기)

RA 가 v0.170.0 이상이어야 머리 없는 요청이 홈 부서로 간다. 위임 창구(`/api/auth/sso`)가 답한다는 것이 곧 그 판 이상이라는 뜻이다.
이 박스가 위임을 켜 두었으면(`RA_SSO_SECRET`) 한 사람의 계정으로 아래 하나를 해 본다.

- 챗에서 PPT 를 RA 로 보내거나 보고서에 그림을 넣는다 → 초안이 그 사람의 RA 개인 공간에 생기고 오류가 없다.
- 403 이 나면 그 사람의 RA 계정에 홈 부서가 없는 것이다(RA 화면에서 부서를 한 번 고르면 된다 — RA 의 `needs_workspace`).

위임을 켜지 않은 박스(토큰 등록 방식)는 달라지는 것이 없다 — 「외부 연결」 에서 고른 부서를 그대로 싣는다.

## 3. RA 의 판과 설정 — 확인(읽기)

코드로만 대조했고 이 박스의 RA 가 어느 판인지 모른다. 아래를 본 뒤 받은 편지함 2026-11-22 의 Q1 ~ Q3 으로 돌려준다.

- RA 의 판(화면 아래 또는 RA 담당에게) — v0.170 / v0.176 / v0.180 가운데 어디 위인지.
- RA `.env` 의 키 **이름**이 있는지만 — `HEAX_SSO_SECRET` · `HEAX_SSO_ALLOWED_IPS` · `MCP_PUBLIC_BASE` · `MCP_FILES_VIA_BACKEND`. 값은 보내지 않는다.
  `HEAX_SSO_ALLOWED_IPS` 가 있으면 포털 · 게이트웨이가 RA 를 부르는 주소가 그 목록에 들어 있어야 한다(없으면 위임이 403 이다).
- RA 에 템플릿 `deliberation` 이 있는지 — 심의 보고서나 `/보고서` 저장이 지금 되는지로 본다.

## 4. 정기 동기화 원천 끄기 — 이 박스에서만(쓰기)

AIDataHub 의 정기 동기화(MX 백서 · SignalForge · MaterialTwin)는 이 박스에서 내부 포트 가드에 막혀 실패만 쌓였다. 데이터는 Drive 조각
동기화가 나른다(사용자 결정 11-21). **dev 에서는 끄지 않는다** — 원천 앱이 같은 박스에 있어 정기 동기화가 실제로 당긴다.

```bash
bash ../AIDataHub/deploy/apptainer/sync-sources.sh list                                   # 읽기만 — 켜짐 · 마지막 상태 · 마지막 오류
bash ../AIDataHub/deploy/apptainer/sync-sources.sh disable mxwp signalforge-gs materialtwin
```

- `list` 에서 `last_status` 가 `blocked` 또는 `error` 이고 `last_sync_at` 이 오래된 것만 끈다. 잘 도는 원천이 있으면 그것은 두고 수만 알려 준다.
- 이름이 하나라도 틀리면 아무것도 바꾸지 않는다(끝 코드 2 — 있는 이름을 알려 준다). 재기동은 필요 없다.
- 끈 원천은 스케줄러가 건너뛰고 헬스의 `sync_stale_sources` 가 세지 않는다. 되돌리기는 `enable <이름>`.

## 5. RA 형식 스스로 등록 — 고를 때만(쓰기 · 기본 끔)

심의 보고서 · `/보고서` · 분석 루틴 보고서는 RA 의 `deliberation` v1 템플릿에 올린다. 그 템플릿이 이 박스 RA 에 있고 저장이 잘 되면
**아무것도 하지 않는다.** 템플릿이 없어 저장이 실패하거나 RA 담당이 손으로 둔 템플릿을 정리하려 할 때만 아래를 한다. RA v0.176.0 이상이어야 한다.

```bash
export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT>          # 그 사람이 --owner-board 부서에 RA 템플릿을 만들 수 있어야 한다
$PY infra/scripts/ra-register-format.py --owner-board <부서 slug>                  # 미리보기 — RA 에 쓰지 않는다
$PY infra/scripts/ra-register-format.py --owner-board <부서 slug> --apply          # 등록만 — 올리는 곳은 그대로다
$PY infra/scripts/ra-register-format.py --owner-board <부서 slug> --apply --use    # 등록하고 그 형식으로 올리기 시작
curl -s http://127.0.0.1:9009/health | python3 -c 'import sys,json; print(json.load(sys.stdin)["ra_formats"])'      # source 가 box 면 먹었다
```

- `--use` 는 `infra/ra-formats.local.json`(gitignore)에 id · 판을 적는다. 에이전트 서버 · 게이트웨이가 재기동 없이 읽는다(게이트웨이는 `/health` 의
  `ra_formats` — 인증이 필요한 쪽에 있다).
- 끝 코드 2 와 「`reportarchive:register_report_format` 가 없다」 면 RA 가 v0.176 전이다 — 그대로 둔다.
- 되돌리기 — `infra/ra-formats.local.json` 을 지운다. 종전 `deliberation` v1 로 돌아간다. RA 에 등록된 형식은 남는다(사람 작성 목록에는 뜨지 않는다).
- Claude Code 워크플로(`hwax-deliberate.js`)의 저장은 이 파일을 보지 않는다 — 늘 `deliberation` v1 이다.

## 6. 묶음 B — 받는 것만으로 달라지는 것과 스위치

새 설정은 없다. 게이트웨이 · 에이전트 서버 · 포털은 재기동해야 먹고(update-all 이 한다) AIDataHub 는 API 재기동이다. **에이전트 서버와 포털은 함께
받는다** — 포털의 심의 손잡이 계약(`undecided` · `reasoning_effort`)이 엔진과 짝이다.

| 무엇 | 기본 | 달라지는 것 · 켜는 법 |
|---|---|---|
| 게이트웨이가 백엔드 도구를 부르는 길 | 받으면 달라진다 | 일회성 세션(사람별 위임)도 상주 세션(서비스 계정)도 `tools/call` **하나만** 보낸다. 종전엔 MCP 클라이언트가 호출 성공 뒤에 출력 스키마를 대조했고(일회성 세션은 호출마다 `tools/list` 를 다시 물었다) 그 대조가 실패하면 토큰 재발급 · 재연결 재시도가 **이미 돈 쓰기 도구를 다시** 돌렸다. 이제 답을 그대로 돌려준다 — 게이트웨이는 백엔드 답의 출력 스키마를 대조하지 않는다(끝 클라이언트 몫). 사람별 위임은 호출마다 왕복이 하나 준다. 게이트웨이 로그에 「MCP 세션에 send_request 가 없다」 경고가 뜨면 이 박스의 MCP SDK 꼴이 달라 옛 길로 떨어진 것이다 — 받은 편지함 Q5 로 알린다 |
| 챗 · 보고서가 읽는 그림 주소 | 받으면 달라진다 | 조사가 바로 붙은 주소(「…png에」)도 그림으로 읽는다. 확장자가 겹친 이름(「shot.jpg.png」)을 끝까지 읽는다(종전엔 앞 확장자에서 끊었다) |
| 보고서의 AIDataHub 첨부 그림 | 켜짐 | `/보고서` · 심의 보고서의 글에 지식카드 첨부 그림 주소(`/ai-data-hub/attachments/…`)가 있으면 그림 칸으로 싣는다(8 MB 까지 · 래스터만). 앞에 호스트가 붙은 첨부 주소는 건드리지 않는다(다른 박스의 그림일 수 있다). AIDataHub 가 답하지 않아 받기가 잇달아 둘 늦게 실패하면 남은 첨부는 받지 않고 그 자리에 까닭을 남긴다. 끄려면 에이전트 서버 `.env` 에 `REPORT_FIG_ATTACHMENTS=0` — 그때는 주소가 글에 그대로 남는다 |
| 그림 표지의 짝 안내 | 받으면 달라진다 | 도구 결과에 PNG 와 SVG 가 함께 오면 표지 글이 「보고서 · 문서에는 png 등 래스터 ref 만 들어간다 — 같은 그림의 짝이면 래스터 쪽을 넣는다」 고 말한다 |
| 심의 T7(판정 불가 과반 → 측정 계획) | **끔** | 에이전트 서버 `.env` 의 `DELIB_UNDECIDED=1` 또는 심의마다 `advanced.undecided=1`. 재는 법은 `cd ../HWAXAgentServer && $PY -m tools.delib_ab --knob undecided --questions <질문 파일> --repeat 3 --out ab_undecided/`(근거를 비운 질문으로 — 판정 불가가 실제로 뽑히는지). 리스크 심사 · 계획서 틀에는 붙지 않는다 켠 심의에서 판정 불가를 밝힌 좌석은 표 집계에서 「미표명」 으로 세고, 좌석이 적은 「다음에 잴 것」 은 회의록에도 실린다. 의장이 결정문을 못 냈으면 표지를 찍지 않는다. 리스크 심사 · 계획서 심의(그 1단 포함)에는 붙지 않는다 |
| 심의 생각 강도(T4) | 서버 값 그대로 | 심의마다 `advanced.reasoning_effort`(low · medium · high · xhigh)를 줄 수 있다. 주지 않으면 종전과 같다. 재는 법은 `$PY -m tools.delib_ab --knob reasoning_effort …`([measurements.md](measurements.md)) |
| 절차 씨앗 「낙하 — 결과 귀환 확인」 | 씨앗 | `docs/procedures/fixtures/drop-return-check.yaml` 을 절차 화면에서 가져다 쓴다. 전부 읽기다. DynaForge 11-15 판 이상이어야 한다 |
| 추천의 판정 후보 | 끔(`SEAT_ONTO` 를 켠 박스만) | AIDataHub `recommend_agents` 의 `onto` 통계에 `verdict`(`core_question` · `no_owner`)가 실린다. 알리기만 하고 순위 · 좌석은 그대로다. `no_owner` 는 이번 추천의 후보 안에서 세고, 카드가 한 장도 없는 객체는 잡지 못한다(카드에 이어진 객체만 질문에서 풀린다) — 드물게만 나오는 것이 정상이다 |

## 7. 묶음 C(통합 판) — 받는 것만으로 달라지는 것과 스위치

새 설정은 없다(스위치는 모두 기본 꺼짐이거나 종전 그대로). 게이트웨이 · 에이전트 서버 · 포털(프론트 빌드)이 함께 재기동돼야 한다 — **에이전트 서버가
게이트웨이보다 먼저이거나 함께**다(새 절차 도구 `procedure_run_start` 를 챗 턴 밖에서 막는 관문이 에이전트 서버에 있다). 워크플로 사본을 맞춘다
(`sync-workflows.sh` — update-all 에 든다). 리스크 앱은 첫 기동에 스키마 v8 → v9 이행이 저절로 돈다(`pre-migrate-v8-*` 사본 하나 — 반출 · 들여오기는
두 박스가 같은 판일 때만).

| 무엇 | 기본 | 달라지는 것 · 켜는 법 |
|---|---|---|
| 과제 인사이트 깔기 | 켜짐(권한 `feat:insights` · 과제를 단 일반 심의에서만) | 같은 (과제, 차수)의 확인 · 반박 카드를 근거로 깐다(최근 20장 · 보고서 독자가 볼 수 있는 것만 — 부서 작업 공간은 같은 소속으로 본다). 봉인 심의는 깔지 않는다 · 기준일 심의는 그 날 뒤 카드를 뺀다 · 리스크 심사 계열은 대상이 아니다. 끄는 스위치는 없다 — 주제를 달지 않으면 안 깐다 |
| 과제 인사이트 화면 | 받으면 달라진다 | 「판이 바뀜」 · 「같은 결론 n번」 칩 · 옛 key 알림 · 「검토 줄」 탭. StepForge 개정을 그 사람 PAT 로 한 번 묻는다(못 읽으면 「모름」) |
| 절차 → 심의 · 챗 | 받으면 달라진다(권한 `feat:procedures`) | 실행 화면의 「심의로 넘기기」 · 「챗으로 가져가기」. 리스크 심사로는 넘기지 않는다 |
| 게이트웨이 절차 도구 넷 | 받으면 생긴다 | `procedure_list` · `procedure_get` · `procedure_run_start`(기본 plan) · `procedure_run_status`. 개인 토큰으로 live 를 시작할 때 확인 없이 도는 쓰기 · 잡 단계가 있으면 거절. 손잡이 `GATEWAY_PROCEDURE_TIMEOUT_S`(기본 60) |
| 이용 통계 접기 | 켜짐(`USAGE_FOLD_S` 기본 3600 · 0 은 끔) | 포털이 기동 30초 뒤와 한 시간마다 원천 다섯을 날마다 접는다(포털 감사 원장 안의 표 셋 · 게이트웨이는 감사 원장 곁 `usage-rollup.sqlite`). 첫 접기는 감사 원장 전체를 한 번 읽는다 — 받은 편지함 Q11 |
| 발표자료 관리 | 꺼짐(`WDA_DECK_ENABLED`) | 켠 박스에서 PDF 미리보기 · 다시 시도 · 사본 지우기 · 루틴 RA 초안의 단추 |
| 리스크 종합 보고서 → RA 초안 | 꺼짐(리스크 앱 `HWAXRISK_RA_REPORT_DRAFT`) | 포털 창구가 그 사람 명의로 쓴다(리스크 앱 절차서 `docs/ra-report-draft.md`). 켜려면 리스크 앱 `knobs.env` 에 한 줄 · 게이트웨이의 리스크 앱 사람별 위임이 켜져 있어야 한다 |
| 웹 챗 Claude 모델 권한 | 아무에게도 없다 | 권한 표에 `feat:chat-claude` 가 보인다. 「전부」 · 관리자 전권에 딸려 오지 않고 개별 허가로만 연다. 에이전트 서버 쪽이 올라오기 전에는 줘도 아무 일이 없다 |
| 리스크 심사 · 보고서 정리 | 받으면 달라진다 | 리스크 심사의 지정 도구 · 좌석 조회에서 절차 도구를 닫는다 · `/보고서 정리` 는 도구를 묶지 않은 챗 모델로 돈다 |

## 되돌리기

묶음 A 는 설정 없이 들어오는 변경이라 되돌리려면 받기 전 판으로 돌아간다(update-all 의 되돌리기 그대로). 박스에서 켠 것은 각 절의 되돌리기를 따른다.
