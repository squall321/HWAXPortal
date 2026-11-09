# 플랫폼 데이터를 코어와 잇기 — 포털 · 게이트웨이 몫과 넘길 것

> 요청서 정본 — [request.md](request.md)(cae00 운영 11-09, 사용자가 같은 날 넘김). 리포 사이 계약은 [design.md](design.md),
> 결정 · 까닭은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md)다.

## 1. 무엇을 · 왜

cae00 운영이 11-09 에 실측을 보냈다. 네 플랫폼(StepForge · DynaForge · SignalForge · DocForge)이 모두 코어 온톨로지를 받고는 있지만, 자기 데이터를
온톨로지로 만든 것은 거의 없고 코어에 이은 선은 넷 다 0 이다. 운영은 이를 코드 단 15건(SRC)과 박스 단 12건(BOX)으로 나눴다.

이 세션이 받는 일은 셋이다.

1. 포털 update-all 의 박스 훅 자리(SRC-12)를 짓는다.
2. 게이트웨이 질문 둘(SRC-14 · 15)에 답하고 고친다. 사용자 결정(11-09)으로 서비스 신원(SRC-13)과 챗의 StepForge 적용(SRC-15)을 짓는다.
   포털 · 게이트웨이 · 에이전트 서버 몫이다.
3. StepForge 몫(SRC-01 ~ 07, SRC-15 의 앱 쪽) · KooRemapper 몫(SRC-08 ~ 11) · SignalForge 몫(Q-2 다시 엶)을 그 세션에 넘긴다.

사용자 결정 여섯(11-09)은 [context-notes.md](context-notes.md) CK-2 에 있다. 앞선 결정 셋(C-30 · 10-16 · 11-04)을 뒤집었다.

## 2. 갈래

| 항목 | 받는 곳 | 처리 |
|---|---|---|
| SRC-01 ~ 06 | StepForge | StepForge 세션에 넘긴다. 허브 앱이라 cae00 update-all 이 끝날 때까지 main 에 올리지 않는다 |
| SRC-07 | StepForge | 서비스 단언을 받는다(design §6) |
| SRC-08 | KooRemapper | Q-5 결정을 싣고 넘긴다 |
| SRC-09 ~ 11 | KooRemapper | KooRemapper 세션에 넘긴다. update-all 이 코드와 Drive 바이너리를 함께 받으므로 cae00 update-all 전에는 main 에 올리지 않는다 |
| SRC-12 | 포털 | 여기서 짓는다(3절) |
| SRC-13 | 포털 · 게이트웨이 | 짓는다(design §2 · §3 — 사용자 결정) |
| SRC-14 | 게이트웨이 | 답과 고침(4절 · design §4) |
| SRC-15 | 게이트웨이 · 에이전트 서버 · 포털 운영자 정의 · StepForge | 짓는다(design §5 · §6 · §7 — 사용자 결정) |
| Q-2 | SignalForge | 다시 연다 — 대응표 둘(design §9) |
| Q-3 · Q-4 | cae00 | 받은 편지함 — 규칙은 전부 · 사람은 주인 과제만, 두 인스턴스 같이 |
| BOX-01 ~ 16 | cae00 | 받은 편지함 — 코드가 들어온 뒤 차례 |

## 3. SRC-12 — update-all 끝의 박스 훅

- **자리.** update-all 의 끝맺음 셋(1h 비우기 · 새 심의 멈춤 · 상태판 경보 멈춤 풀기) 뒤, ○ 요약 앞에서 돈다. 모든 배포가 끝난 뒤이고, 건너뛴
  ○ 줄이 끝 요약에 든다. 여기서는 § 머리(`hr`)를 부르지 않는다 — 비우기 깃발을 다시 세우면 내릴 곳이 없다.
- **무엇을.** `infra/hooks/post-update.d/*.local.sh` 를 이름 차례(로캘과 무관한 C 차례)로 하나씩 `bash` 로 돌린다. 작업 폴더는 포털 리포
  루트이고 표준 입력은 비운다. 훅에는 `HWAX_UPDATE_FAIL`(이 실행이 이미 실패를 셌으면 1)을 넘긴다.
- **박스 파일.** 훅은 git 이 모르는 박스 파일이다. 같은 커밋에 무시 규칙(`.gitignore`)을 넣는다. 무시하지 않으면 update-all §1 과
  deploy-all 의 `git stash -u` 가 치운다. 이름이 `.local.sh` 로 끝나지 않는 `*.sh` 는 돌리지 않고 한 줄로 짚는다.
- **실패.** 훅이 실패해도 update-all 의 종료코드에 섞지 않는다. 끝 요약에 줄 하나(`박스 훅 N개 중 M개 실패 — 이름(rc)`)로 따로 낸다. 모두
  끝났으면 그 줄은 `모두 끝났다` 다. 훅마다 상한 `HWAX_HOOK_TIMEOUT_S`(기본 3600초)가 있다. 넘기면 그 훅이 남긴 프로세스까지 정리하고
  실패로 센다(단계 상한과 같은 `HWAX_STEP_ID` 표식 · `_reap_step`).
- **건너뛰기.** 훅이 없으면 ○(있는데 안 켠 것)다. 종료 요청(`HWAX_UPDATE_ALL_STOP`)이 있었으면 ○ 로 건너뛴다.
  `--hooks-when-idle` 이면 일이 있거나 셀 수 없을 때 ○ 로 건너뛴다. 일은 넷을 본다.
  - 에이전트 서버 `/health` 의 도는 심의 · 줄 선 심의 · 리스크 카드 대조 수
  - DynaForge 의 도는 로컬 작업
  - StepForge 의 대기 · 도는 작업
  - DocForge 의 대기 · 도는 작업

  넷 모두 사전 점검(`update-preflight.py`)과 update-all 이 이미 쓰는 셈 그대로다. 그 앱이 없는 박스는 그 칸을 셈에서 뺀다.
- **완료 기준(요청서).** 빈 훅 폴더에서 동작은 지금과 같다(○ 한 줄만 더해진다 — 사용자 지시 '안 켠 기능도 로그에'). 실패하는 시험 훅
  하나로 종료코드 0 과 요약 줄이 함께 나와야 한다.

## 4. 게이트웨이 질문의 답

### SRC-15 — REST 다리가 StepForge 의 포털 신원 길(R2)로 들어가나

아니다. POST 셋만 연다고 되지 않는다. 까닭은 셋이다.

- REST 다리의 StepForge 칸은 사람 명의(`per_user`)가 아니라 게이트웨이의 허브 서비스 토큰(`inject`)으로 돈다. StepForge 에는 사람별 위임
  창구도 없다.
- StepForge 는 게이트웨이 표지 머리(`x-forwarded-user` · `x-hwax-*`)가 하나라도 있으면 신원을 거절한다(`gateway_marked`). 이 규칙은 게이트웨이의
  REST 다리를 겨냥해 쓴 것이고, 게이트웨이는 그 머리를 늘 단다. 그래서 열어도 적용은 `identity_refused` 다.
- 게이트웨이는 메서드를 경로마다가 아니라 사이트마다 연다. POST 를 열면 StepForge 의 모든 POST 가 서비스 계정으로 열린다. 또
  `rest_call` 은 챗 확인 관문(HA-29)의 어느 목록에도 없어 POST 에도 확인 카드가 서지 않는다.

열려면 세 리포를 고쳐야 한다. StepForge 에 위임 창구(서명 단언)를 두고, 게이트웨이에 사람별 위임과 경로별 막기를 넣고, 에이전트 서버
관문이 `rest_call` 의 POST 를 알아봐야 한다. 이는 10-16 결정과 C-30 을 뒤집는 일이다. 사용자가 11-09 에 열기로 정했다 — 꼴은
[design.md](design.md) §5 ~ §7 이다. GET 과 MCP 길은 그대로 두고 정해진 쓰기 경로에만 단언을 싣는다(CK-3).

### SRC-14 — 쓰기 목록에 `link_` 짝이 없는 까닭

목록 규칙이 놓친 것이다. 쓰기 낱말(`_WRITE_NAME`)에 `unlink` 는 있는데 `link` · `edit` · `sync` 는 없다(10-28 부터). 다른 판정이 이 도구들을
쓰기로 다루지도 않는다. 앱이 표지(readOnlyHint · destructiveHint)를 달지 않았기 때문이다(SP 는 표지 없이 도구를 단다).

- 울타리는 열려 있지 않았다. 읽기 토큰 · 루틴 · 패널이 모두 '모르면 막는다' 라 이 도구들을 막았다.
- 빈 곳은 운영자 동기화의 '목록 밖 쓰기' 알림이다. 이 도구들을 짚지 못해 챗 확인 카드(운영자 `writes` · `confirm`)에 올릴 기회가 없었다.
- 다음 판에 낱말 셋을 더하고, 새로 걸리는 읽기(ste `get_sync_settings`)와 원래 읽기인 DynaForge `plan_task_links` 를 읽기 목록에 넣는다
  (design §4).
- cae00 은 받은 뒤 운영자 동기화가 새로 짚는 허브 도구를 박스 덧씌우기(`he-team.local.json`)의 `writes` · `confirm` 에 넣는다.

## 5. SRC-13 — 서비스 신원(사용자 결정 11-09: 짓는다)

지금 박스 작업이 쓸 서비스 신원은 없다. 게이트웨이 공유 토큰(GW_TOKEN)은 `x-hwax-user` 를 믿어 아무 사람으로나 행세할 수 있으므로 박스
작업에 내줄 수 없다. 새로 짓는다면 이렇게 된다.

- 포털 관리자만 발급하는 서비스 PAT를 새 청중으로 둔다. `sub` 는 `system:<작업>` 이고 수명은 1 ~ 365일이며, 회수는 기존 회수 목록으로 한다.
- 게이트웨이는 박스 파일(`service_tools.local.json`)의 작업별 허용 도구만 부르게 하고, 감사 `caller` 에 `system:<작업>` 을 남긴다.
- 규모는 두 리포 · 코드 300줄 · 시험 200줄쯤이다.

다만 허브 앱은 이 신원을 그대로 보지 못한다. StepForge 가 서명 단언을 받게 고쳐야 한다(SRC-07 — design §6).

권했던 대안(사용자가 고르지 않음, 기록으로 남긴다). StepForge 의 코어 받기(`plm_sync`)는 지금 사람이 잡을 걸 때만 돈다. DynaForge 는 매시 받는다. StepForge 가 받기를
스스로 주기적으로 돌리고 그 뒤에 규칙 잇기(SRC-03 · 05)를 이으면, 바깥에서 쓰는 신원 없이 운영이 바라는 '사람 손 없이 도는 길'이 앱 안에서
선다. DynaForge 도 SRC-09 로 같다. 이때 박스 훅(BOX-15)은 요약을 읽기만 한다.

## 6. 하지 않는 것

- 운영 박스의 데이터 · 설정을 고치는 일(BOX-*) — cae00 몫이다. 이 세션은 받은 편지함에 차례만 싣는다.
- 정본 허브 안의 일 · 플랫폼 정의 내보내기 · DocForge · ReportArchive 타입 대응 — 요청서 7절이 뺐다.
- StepForge · KooRemapper 코드 — 그 세션 몫이다.
