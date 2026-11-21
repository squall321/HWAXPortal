# 남은 일 전부 진행(11-21) — cae00 절차

> 2026-11-22(KST). 계획은 [PLAN.md](PLAN.md), 결정은 [context-notes.md](context-notes.md) L21-4 ~ L21-10 이다.
> 받을 판(묶음 A) — 게이트웨이 `9b5ab25` · `9224bd1`(master `210a50c`) · 에이전트 서버 `b33a728`(main `cde6eb0`) · 포털 `72f828cd` · `34766ff1` ·
> `31d08cb4`(main `aeec26d1`) · AIDataHub `1fe55d7`(병합 뒤 이 줄을 고친다). 모두 main 에 `--no-ff` 로 합쳤다.
> 대조 시점 — dev 11-22. dev 에는 Report Archive 가 떠 있지 않아 RA 에 닿는 것은 전부 가짜 RA 시험이다. 아래 3 · 4절이 진짜 RA 로 보는 첫 확인이다.

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

## 6. 그 밖에 이번에 들어오는 스위치

(묶음이 더 올라오면 여기에 더한다.)

## 되돌리기

묶음 A 는 설정 없이 들어오는 변경이라 되돌리려면 받기 전 판으로 돌아간다(update-all 의 되돌리기 그대로). 박스에서 켠 것은 각 절의 되돌리기를 따른다.
