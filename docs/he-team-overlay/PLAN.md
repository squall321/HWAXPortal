# HE팀 운영자 정의를 cae00 에서 — 박스 덧씌우기

사용자 결정 11-04 — 「사내(cae00)에는 있는데 이 개발 박스(dev)에는 없는 것들이 있다. 이제는 cae00 에서 관리하는 게 맞다.」 고른 안은 **덧씌우기**다 — git 의
`infra/personas/he-team.json` 은 기본값으로 두고, cae00 이 박스 파일 `infra/personas/he-team.local.json`(git 에 안 올림)으로 운영자를 더하고 칸을 덮고 뺀다.
판단 기록은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md), cae00 사람 몫은 [server-setup.md](server-setup.md)다. 날짜는 KST.

## 1. 왜

- dev 에 없는 앱이 있다 — 정본 허브 셋(rootdesign · FailureTrace · CAE 그룹) · ODB 허브 · ARP 등. 그 운영자의 도구 이름 · 쓰기 목록을 dev 에서는 실제 게이트웨이로 대조할 수
  없어 짐작으로 썼다(11-04 SP 0.4.72 쓰기 마흔둘도 SP 소스에서 읽었다). 고칠 때마다 cae00 미리보기 → 받은 편지함 → dev 고침으로 한 바퀴를 돈다.
- 측정 · 튜닝은 운영 박스에서 닫는다(10-29 사용자 지시 — 코어 어휘표 `core_vocab.local.json` · 검색 손잡이 `search_tuning.local.json` 이 같은 꼴이다).

## 2. 무엇을 — 덧씌우기 꼴

```json
{
  "_doc": "무엇을 왜 바꿨는지 사람이 적는 칸(읽는 쪽은 무시한다)",
  "groups":   { "<묶음>": "<라벨>" },
  "personas": {
    "<운영자 키>": { "<칸>": "<값>" },
    "<운영자 키>": null
  }
}
```

- `personas` 는 **운영자 키로 묶은 객체**다. 이미 있는 키면 그 운영자에 JSON merge patch(RFC 7386 — 객체는 재귀로 합치고 그 밖의 값은 바꾸며 `null` 은 그 칸을
  지운다, **목록은 통째로 바뀐다**)를 건다. 없는 키면 새 운영자다(정본과 같은 꼴을 다 적는다 — 동기화가 같은 검사로 본다). 값이 `null` 이면 이 박스에서 그 운영자를 뺀다.
- `groups` 는 merge patch 그대로다. 그 밖의 칸이 있으면 덧씌우기 전체를 버린다.
- 덧씌우기가 깨졌으면(JSON 이 아님 · 꼴이 틀림) **통째로 버리고 기본 정의로 돈다** — 그 사실은 동기화 미리보기 · update-all · 에이전트 서버 `/health` 에 찍힌다.
- 지문 — 합친 정의의 지문(키 차례 JSON 의 sha256 앞 12자, `_doc` 뺌)을 동기화와 에이전트 서버가 같은 셈으로 낸다. 두 값이 같으면 한 정의를 본다.

## 3. 누가 읽나 — 넷이 같은 합친 정의를 본다

| 읽는 곳 | 무엇을 | 고침 |
|---|---|---|
| `infra/scripts/sync-he-personas.py` | 운영자 → AIDataHub 행(미리보기 · `--apply` · `--check`) | 합친 정의로 만든다 · 덧씌우기 줄을 찍는다 |
| 포털 `backend/app/access/agent_guard.py` | 운영자가 모는 앱 → 플랫폼 허가 검사 | 합친 정의의 `apps` — 덧씌우기로 더한 운영자도 허가를 본다 |
| 에이전트 서버 `_confirm_lists` | writes · confirm → 웹 챗 확인 관문 | 덧씌우기도 읽고 바뀐 시각으로 다시 읽는다 · `/health` 에 덧씌우기 상태 |
| `infra/scripts/update-all.sh` | 동기화 `--check` 의 줄 · `/health` 의 관문 줄 | 덧씌우기 줄을 올린다 |

읽는 법은 `infra/personas/he_team.py`(표준 라이브러리만) 하나다 — 동기화 · 포털이 이것을 쓰고, 에이전트 서버는 같은 셈을 따로 갖고 시험이 둘을 견준다(코어 어휘표의
게이트웨이 · 에이전트 서버와 같은 까닭 — 다른 리포가 실행 중에 남의 코드를 들이지 않는다).

## 4. 규칙

- **dev 에 없는 앱의 운영자는 dev 에서 고치지 않는다** — cae00 이 박스 파일에서 고친다(그 박스의 실제 `/tools-map` 으로 대조된다). dev 는 두 박스에 다 있는 앱의 운영자만 고친다.
- git 의 기본값은 지우지 않는다 — 새로 띄운 박스 · dev 시험의 바탕이다. cae00 이 덮은 칸은 덧씌우기가 이긴다.
- 박스 파일은 git 밖이라 이력이 없다 — 고친 까닭은 `_doc` 에 적고, 고치기 전 판을 같은 폴더에 날짜를 붙여 남긴다(server-setup).
