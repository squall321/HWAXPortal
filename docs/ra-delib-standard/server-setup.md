# 운영 박스(cae00) 사람 몫 — 심의 보고서를 RA 시스템 공간에 확인 후 게시

> 무엇을 왜 하는지는 [PLAN.md](PLAN.md). 이 절차를 하지 않으면 지금처럼 개인 공간 초안까지만 간다(깨지는 것 없음).

## 0. 받을 판

| 리포 | 판 | 반영 |
|---|---|---|
| HWAXPortal | 이 절차가 든 main | update-all(포털 재기동 — 새 창구 셋 · 화면 단추) |
| HWAXMcpGateway | `c27a2f9` 이후 | update-all(게이트웨이 재기동 — `ra_report_format`) |
| HWAXAgentServer | 바꾼 것 없음 | — |

## 1. RA 판 확인

RA 화면의 판 표시나 `GET /api/health` 로 판을 본다.

- **0.180.0 이상이어야 한다.** 시스템 공간과 「AI 가 게시판을 골라 올리기」가 이 판에서 생겼다.
- 0.176.0 이상이면 형식 등록(2절 ②)까지는 된다.
- 0.180.0 아래면 2절 ①을 건너뛰고 3절에서 `--board` 를 빼고 등록한다. 형식만 바뀌고 게시 단추는 뜨지 않는다.

## 2. RA 시스템 관리자가 할 일(RA 화면)

① **시스템 공간 만들기.** 시스템 관리 → 「시스템 양식」 → 「시스템 공간」 탭에서 시스템 이름 `hwax` 로 공간을 만든다. 주소는 `sys-hwax` 가
   된다.

② **부서 등록.** 심의 보고서를 올릴 부서를 「게시 가능」으로 등록한다. 부서 하나를 등록하면 그 아래 전체가 쓸 수 있다.
   - ⚠ 「열람만」으로 열면 그 부서 사람은 올릴 수 없다. 보기만 할 부서는 「열람만」으로 따로 등록한다.

## 3. 형식 등록과 박스 파일(리포 루트에서, 게이트웨이와 같은 파이썬)

```bash
export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT — RA 에서 최상위 조직에 템플릿을 만들 수 있는 사람>
$PY infra/scripts/ra-register-format.py --owner-board <최상위 조직 slug>                                    # 미리보기
$PY infra/scripts/ra-register-format.py --owner-board <최상위 조직 slug> --apply --use --board sys-hwax    # 등록 · 박스 파일
```

- **소유는 최상위 조직으로 둔다.** RA 는 그 사람이 소유 부서 트리(조상 · 자손)의 멤버일 때만 형식을 보인다. 안 보이면 심의 보고서 저장이 404 로
  실패한다.
- 시스템 공간을 소유로 두면 안 된다. 시스템 공간의 부서 등록은 형식을 보이는 판정에 들지 않는다(코드로 읽음, 실호출로는 확인 못 함).
- 박스 파일 `infra/ra-formats.local.json`(gitignore)의 `deliberation` 줄이 `{"template_id": "sys.hwax.deliberation", "template_version": N,
  "board": "sys-hwax"}` 가 된다.
- 손으로 둔 `board` 는 뒤에 `--use` 만 다시 돌려도 남는다.

## 4. 확인

1. **포털:** 로그인한 셸에서 `GET /agent/ra/post-target` 이 `{"board": "sys-hwax"}` 이다.
2. **게이트웨이:** `/health` 의 `ra_formats.kinds.deliberation.source` 가 `box` 이다. 개인 Claude 에서 `ra_report_format` 을 부르면 `board` 가
   나온다.
3. **에이전트 서버:** `/health` 의 `ra_formats` 가 `box` 이다. 재기동은 필요 없다(파일이 바뀌면 다시 읽는다).
4. **웹 심의 하나:** 작은 주제로 하나 돌린다.
   - 결과 카드에 「시스템 공간에 올리기」가 뜬다. 누르면 「「…」 게시판 — N명이 보게 됩니다」가 나오는지 본다.
   - 게시를 누르면 RA 의 `sys-hwax` 게시판에 그 보고서가 보이는지 본다.
   - 시험 보고서라면 게시하지 말고 취소까지만 봐도 된다. 게시한 뒤에는 작성자가 직접 내릴 수 없다.
5. **리스크 종합 보고서**(앱 스위치를 켠 박스만): 새로 만든 초안의 형식이 `sys.hwax.deliberation` 인지 본다.
   - 리스크 앱 손잡이 `HWAXRISK_RA_REPORT_TEMPLATE` 을 일부러 다른 틀로 바꿔 둔 박스는 그 틀 그대로다.

## 되돌리기

- 박스 파일의 `board` 칸을 지우면 게시 단추가 사라진다. 다음 요청부터 반영되고 재기동은 필요 없다.
- 줄을 통째로 지우면 형식도 종전 `deliberation` v1 로 돌아간다.
- 이미 게시한 보고서는 RA 에서 게시취소를 청한다(게시판 매니저 승인).
