# 10-17 후속 — 다른 리포 · 담당에게 보내는 요청 셋

> 각 절은 따로 떼어 보내도 읽히게 썼다. 배경은 [PLAN.md](PLAN.md) 2절(cae00 업데이트 리뷰 판정)과 [context-notes.md](context-notes.md).
> 주소 · 토큰은 적지 않는다(이 리포는 공개다). 포털 쪽에서 이미 고친 것은 각 절 끝에 적었다.

## 1. StepForge — `part_history` 의 인자 조건을 스키마로(리뷰 X5)

**무엇** — `part_history` 는 `projects` 와 `task_code` 중 하나가 있어야 하는데 MCP 입력 스키마의 `required` 에 아무것도 없다. 인자 없이
부르면 `ValueError` 다. 스키마만 보는 쪽(포털 update-all 의 MCP 스모크 · Claude 같은 MCP 클라이언트)은 '인자 없이 불러도 되는 도구' 로
읽는다 — 10-17 cae00 스모크가 이 도구를 `{}` 로 불러 StepForge 가 3개 중 2개만 통과로 찍혔다.

**근거** — 떠 있는 인스턴스의 `app/mcp_server.py` 의 `part_history(projects=None, …, task_code="")`.

**바라는 것(둘 중 하나)**
- 입력 스키마에 조건을 적는다 — `anyOf: [{required: [projects]}, {required: [task_code]}]`(또는 둘 중 하나를 필수로).
- 인자 없이 부르면 예외 대신 구조화된 안내를 돌려준다 — 예: `{"error": "args_required", "need_one_of": ["projects", "task_code"]}`.

**포털 쪽에서 한 것** — 스모크가 '인자를 요구하는 거절'(오류가 그 도구의 인자 이름을 말하고 인증 · 전송 오류가 아닌 것)은 실패로 세지
않고 다음 후보를 부르며, 인자 칸 없는 도구부터 고른다(포털 `e908b62`). 그래서 급하지 않다 — 스키마가 맞으면 Claude 가 첫 호출부터
맞게 부른다.

## 2. DynaForge(KooRemapper) — stcx 제출 전에 그 사람의 SmartTwin 권한을 본다(사용자 결정 8)

**무엇** — stcx(356대) 해석 잡은 공용 토큰 한 명 이름으로 나간다. 그래서 포털에서 SmartTwin 권한이 없는 DynaForge 사용자도 그 토큰으로
잡을 낼 수 있는 것으로 보인다(포털 쪽에서 본 것이고 DynaForge 코드로는 확인하지 않았다).

**사용자 결정(10-17)** — '공용 계정, 권한 확인 추가'. stcx 에는 지금처럼 한 계정으로 내되, DynaForge 가 **제출 전에** 요청한 사람이
포털의 `plat:smarttwin` 권한을 가졌는지 보고 없으면 막는다. 사람별 명의(stcx 의 SSO · 사람별 토큰 창구)는 그쪽 팀 일이라 지금 하지 않는다.

**포털이 주는 것**
- 권한 이름 — `plat:smarttwin`(포털 `backend/config/access.yaml` 의 `smarttwin` — 타일 `smart-twin-cluster` · `ste`, 게이트웨이 백엔드
  `smart-twin-mcp` · `smart-twin-cluster` · `ste`). DynaForge 자체는 `plat:dynaforge` 다.
- 웹(jwt-handoff) — 포털이 실행할 때 주는 90초 실행 토큰의 `groups` 에 그 사람의 합성 권한(`plat:*` · `feat:*`)이 **그 순간 계산값으로**
  실린다. DynaForge 가 그 값을 자기 세션에 들고 있으면 제출 때 볼 수 있다(권한을 거둔 것은 다음 로그인부터 먹는다).
- MCP(게이트웨이 경유) — 게이트웨이의 허가는 **백엔드 단위**라 DynaForge 의 제출 도구 하나만 `plat:smarttwin` 으로 막을 수 없다(백엔드
  전체에 걸면 SmartTwin 권한 없는 사람이 DynaForge 도구를 전부 잃는다). 그 길의 신원(게이트웨이가 넘기는 사람 단언)에서 그룹을 읽거나,
  포털에 묻는 길을 따로 정해야 한다 — 어느 쪽이 맞는지 알려 주면 포털 쪽 배선을 맞춘다.

**바라는 것** — 제출 경로(웹 · MCP 모두)에서 요청자에게 `plat:smarttwin` 이 없으면 잡을 내지 않고 '권한 없음 — 포털에서 SmartTwin 권한을
요청하라' 를 돌려준다. 막은 기록(누가 · 언제 · 무엇을)을 DynaForge 잡 기록에 남긴다.

## 3. MaterialTwin 데이터 담당 — 출처 · 물성값 중복 정리(리뷰 4절 · X3)

**무엇** — 10-17 cae00 병합에서, 나중에 채워진 `publisher` 때문에 같은 출처가 새 행이 되어 정정 4건이 중복으로 들어갔다(재료 254).

**정리 부탁(cae00 운영 DB)**
- 출처 **1534 와 3184** 를 하나로 합친다.
- 물성값 **67907~67910**(재료 254)의 중복을 정리한다.
- (따로 할 일) DB 전체에 같은 값 묶음이 약 1,100개 있다 — 서로 다른 출처 691 · 같은 출처 446. 이 건은 위와 별개로 정리 계획이 필요하다.

**HEAXHub 쪽에서 한 것** — 병합의 출처 자연키에서 `publisher` 를 뺐다(HEAXHub `28154f1`, 08-18 에 `authors` · `year` 를 뺀 것과 같은 까닭 —
나중에 채워지는 보강 필드). 빼도 출처가 유일하다(dev 3,165/3,165). 그래서 앞으로의 병합은 같은 중복을 새로 만들지 않는다 — 이미 들어간
것만 위처럼 정리하면 된다.
