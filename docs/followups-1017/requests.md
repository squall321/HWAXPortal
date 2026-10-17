# 10-17 · 10-18 후속 — 다른 리포 · 담당에게 보내는 요청

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

## 4. StepForge — MaterialTwin 기본 주소를 허브가 띄운 자리로(수정 제안서 S1 · 10-18 추가)

**무엇** — `core/materials.py` 의 `TWIN_DEFAULT = "http://127.0.0.1:9233"`. 허브가 띄운 MaterialTwin 은 허브가 배정한 앱 포트(cae00 은 지금
9107 — 앱 포트는 허브 포트 풀 9100~9999 에서 배정된다)에 있고, 허브 프록시로는 `<허브 오리진>/apps/materialtwin_web` 이다. 기본값이 빗나가면
`material_sources` 가 MaterialTwin 을 「재지 않음(null)」 으로 두어 사용자는 개수를 못 받고 왜인지도 모른다(10-18 사용자 보고 — 「MaterialTwin
주소가 127.0.0.1:9233 으로 뜨는데 실제 서비스는 9107」).

**지금 cae00** — HEAXHub `.env` 에 `APPTAINERENV_STEPFORGE_MATERIALTWIN_URL=<허브 프록시>/apps/materialtwin_web` 을 넣어 우회했다(10-18 04:0x,
수정 제안서 4절). 이 줄이 없는 박스(dev · 새 박스)는 같은 증상이다.

**바라는 것**
1. 허브가 띄운 앱이면 기본값을 허브 프록시 경로(`<허브 오리진>/apps/materialtwin_web`)로 유도한다. 고정 포트(9233 · 9107)는 쓰지 않는다.
   또는 HEAXHub 가 형제 앱 주소를 `HEAX_APP_URL_<slug>` 꼴로 넣어 주면 그것을 읽는다(그 길이 맞으면 HEAXHub 에 같은 요청을 낸다).
2. 「닿지 않음」 과 「없음」 을 가른다 — 주소에 닿지 않으면 `material_sources` 가 null 대신 「MaterialTwin 에 닿지 않는다(<주소>)」 를 내고,
   `field_check` 도 같은 것을 경고로 낸다.
3. (확인 부탁) 루프백 호출이 프록시를 타지 않는지 — cae00 은 사내 프록시 환경값이 걸려 있어 `NO_PROXY` 가 빠지면 127.0.0.1 호출도 프록시로
   갈 수 있다(포털 게이트웨이가 같은 함정을 겪었다 — 포털 `docs/change-request-8-10/context-notes.md` D-8).

**포털 쪽에서 한 것** — StepForge 는 고치지 않았다(그 리포는 그쪽 세션이 결정 기록과 함께 맡는다). 포털 「앱」 검색이 허브 앱(MaterialTwin
Web 등)도 찾게 했다(수정 제안서 F4) — 사용자가 「MaterialTwin 이 연결 해제되었나」로 묻게 된 다른 절반이다.

## 5. MaterialTwin 데이터 담당 — 새 자연키로 처음 돈 병합의 어긋남(수정 제안서 4-b · 10-18 추가)

**무엇** — 10-18 04:0x cae00 HEAX 반입의 app-data 병합에서 MaterialTwin 이 「정정 **11건**이 운영에서 옛 행을 못 찾았다」 · 「판정 1건이
대응행을 못 찾았다」를 냈다(10-17 아침은 4건). 새 자연키(HEAXHub `28154f1` — publisher 제외)로 처음 돈 병합이라 그사이 쌓인 어긋남이 한꺼번에
드러난 것으로 보인다. 같은 측정이 두 행이 되었을 수 있다.

**확인 부탁** — 병합 요약 JSON 의 `correction_misses`(11) · `verdict_misses`(1)를 열어, 옛 행을 못 찾은 정정이 같은 측정의 두 번째 행을
만들었는지 본다. 그렇다면 3절(출처 1534 · 3184, 물성값 67907~67910)과 같은 방식으로 정리한다. 다음 병합에서도 수가 줄지 않으면 자연키가
아직 흔들리는 것이다 — 그 필드를 알려 주면 HEAXHub 쪽 병합 키를 맞춘다.
