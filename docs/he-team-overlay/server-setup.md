# HE팀 운영자 박스 덧씌우기 — cae00 사람 몫

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 고친 날 2026-11-04(KST).

## 1. 처음 만들기

- **update-all 로 이 판을 받은 뒤에 만든다.** 이 판이 `.gitignore` 에 `infra/personas/he-team.local.json` 을 더한다 — 그 전에 만들면 update-all 첫 stash 가
  옛 `.gitignore` 로 돌아 이 파일을 치운다.
- 자리 — `~/Projects/HWAXPortal/infra/personas/he-team.local.json`. 꼴은 PLAN 2절이다. 예 —

```json
{
  "_doc": "11-0X — 무엇을 왜 바꿨는지(예: 정본 허브 쓰기 목록을 이 박스 /tools-map 으로 맞춤)",
  "personas": {
    "he-data-coreontology": {"writes": ["rootdesigndatahub_object_create", "rootdesigndatahub_object_update"]},
    "he-data-<새 앱>": {"apps": ["<새 앱>"], "name": "…", "summary": "…", "mission": "…", "can": [], "workflow": [], "concepts": [],
                        "pitfalls": [], "key_tools": [], "writes": [], "confirm": [], "samples": []},
    "he-cad-odbhub": null
  }
}
```

  - 있는 운영자 — 고칠 칸만 적는다. **목록은 통째로 바뀐다**(writes 에 하나를 더하려면 기본의 writes 를 옮겨 적고 더한다).
  - 새 운영자 — 정본(`he-team.json`)의 한 명과 같은 꼴을 다 적는다. 키는 `he-<묶음>-<앱>` 이고 묶음은 `groups` 에 있어야 한다(없으면 `groups` 로 더한다).
  - 뺄 운영자 — `null`. 기본에 없는 키를 `null` 로 적으면 미리보기가 '뺀다고 적었는데 기본에 없는 키' 로 알린다(오타).
- 토큰 · 비밀번호는 적지 않는다 — 운영자 정의에는 필요 없다.

## 2. 고칠 때마다

```bash
cd ~/Projects/HWAXPortal
f=infra/personas/he-team.local.json
[ -f "$f" ] && cp "$f" "infra/personas/he-team.local.$(date +%Y%m%d-%H%M).json"   # 고치기 전 판 — git 밖이라 이력이 없다
# … 고친다 …
python3 infra/scripts/sync-he-personas.py            # 미리보기 — 아무것도 바꾸지 않는다
python3 infra/scripts/sync-he-personas.py --apply    # 반영
curl -s http://127.0.0.1:9009/health | python3 -c 'import json, sys; print(json.load(sys.stdin)["confirm_gate"]["lists"])'
```

- 미리보기 첫 줄이 `· 덧씌우기 he-team.local.json — 고침 … · 더함 … · 뺌 … · 지문 <X>` 다. `✗ 덧씌우기 … 을 버렸다 — <까닭>` 이면 꼴이 틀렸다 — 고칠 때까지
  기본 정의로 돈다(확인 관문도 기본 목록만).
- 새 운영자 · 고친 이름은 그 박스 게이트웨이 `/tools-map` 과 대조된다 — `✗ … 에 이 앱에 없는 도구` 면 이름을 고친다(지금까지와 같은 검사).
- 에이전트 서버 확인 관문은 재기동 없이 바뀐 시각으로 다시 읽는다 — `/health` 의 `confirm_gate.lists.overlay.fingerprint` 가 미리보기의 지문 `<X>` 와 같으면 같은
  정의를 본다. update-all §6 · §7 도 같은 줄과 지문 대조(다르면 ⚠)를 찍는다. `overlay` 칸이 없으면 에이전트 서버가 이 판보다 옛 판이다(update-all 로 받는다).

## 3. 규칙

- 이 박스에만 있는 앱(정본 허브 셋 · ODB 허브 · ARP …)의 운영자는 여기서 고친다 — dev 는 고치지 않는다. 두 박스에 다 있는 앱은 dev 가 git 의 `he-team.json` 에서 고친다.
- git 의 기본값이 바뀌어도(update-all 로 받음) 이 파일이 덮은 칸은 이 파일이 이긴다 — 기본이 새로 더한 칸은 이 파일이 덮지 않았으면 그대로 들어온다.
