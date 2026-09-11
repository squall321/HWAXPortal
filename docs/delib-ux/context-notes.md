# 심의 UX — 작업 노트

왜 그렇게 했는지. 다음 사람이 같은 판단을 다시 내리지 않도록.

## D-1. 이 리포의 반복 사고 — delib_opts 화이트리스트가 **두 겹**이다

새 심의 손잡이를 넣을 때 통과해야 하는 관문이 둘이다.

1. `frontend/src/state/chatStore.ts` `delibOptsToWire()` — 패널 토글을 전송 페이로드로 옮긴다.
2. `backend/app/agent/routes.py` `DelibOpts` — pydantic 모델. **선언 안 된 키는
   `model_dump(exclude_none=True)` 에서 조용히 사라진다.**

둘 중 하나만 빠져도 **에러가 안 난다.** 값이 없어진 채로 심의가 정상 동작한 것처럼 끝난다.
`chair_template` 과 `free_tools` 가 이미 이 사고를 겪었고 주석으로 남아 있는데, 그 옆에
`non_negotiables`·`stop_after_round`·`rounds_so_far`·`append_to_report_id` 네 개가 또 빠져
있었다(2026-09-11 조사).

⚠ 예외 하나 — `continueDeliberation` 이 쓰는 `extraDelibOpts` 는 `delibOptsToWire` 를
**우회**한다(ChatContext.tsx:546 이 병합만 한다). 그래서 이어하기 전용 키는 백엔드 모델만
고치면 된다. 반대로 패널 토글은 반드시 두 겹 다 고쳐야 한다.

**그래서 ①에 집합 대조 테스트를 넣는다** — 프론트가 보내는 키 전부가 백엔드 모델에 있는지
기계가 본다. 사람이 두 파일을 번갈아 보는 것으로는 네 번이나 놓쳤다.

## D-2. 체크포인트 토글은 **1회성**이어야 한다

`ChatContext.tsx:546` 이 패널 토글을 **매 발화에** 다시 싣는다. `stop_after_round=1` 을 켜 두면
이어하기도 1라운드에서 또 멈춘다(엔진 deliberation.py:2775 는 그 호출의 rnd==1 을 본다).
사용자는 "이어가라고 했는데 또 멈췄다" 를 보게 된다. 이어하기 전송에서 명시적으로 빼거나
켠 뒤 한 번만 쓰게 만든다.

## D-3. 좌석은 빼지 않는다 — 설계 결정이다

`personas` 변형 지점 다섯 곳이 **전부 추가**다(deliberation.py:2391·2420·2425·2432·2440).
좌석을 빼면 그 도메인의 이전 발언을 방어·수정할 당사자가 사라진다
(docs/deliberation-quality/context-notes.md:61). 사용자의 "로스터를 다시 고르게" 는
**빼기**가 아니라 **다음 회차 구성**으로 푼다.

⚠ 문서와 구현이 어긋나 있다 — 문서는 '유임 최소 보장(max(2, 절반))' 이라 적었는데 구현은
'전원 유임' 이다. 손대기 전에 어느 쪽을 정본으로 할지 정해야 한다.

## D-4. 분류가 판단 근거를 지우면 안 된다

좌석을 분야로 접는 순간, 사용자가 가진 **유일한** 판단 근거였던 관련도 %(최상위 대비)가
사라진다. 조직도는 `pool`(key/name/tags)만 그리고 score·why·axes·role 이 없기 때문이다.
`candidates`(≈40)를 key 로 머지해 배지를 얹지 않으면 "분류는 됐는데 누굴 골라야 할지 더
모르겠다" 가 된다. 챗은 1명만 고르니 덜 아팠지만 심의는 2~12명이라 직격이다.

## D-5. 도구 분류를 둘 자리 — `gateway_config.json` 은 안 된다

gitignore 이고 `provision-config.sh` 가 박스마다 생성한다. `--force` 재생성에 날아가고
`update-all.sh:274` 가 "git pull 로도 안 온다" 고 못 박는다. 게이트웨이 리포의 **추적 파일**
(APP_META 옆)이 맞다 — 라벨 정본이 이미 거기 있고 cae00 에 git 으로 간다. 반영에 게이트웨이
재기동이 필요하다(`_load_config` 는 임포트 1회).

프론트 상수는 싸 보이지만 cae00 이 프론트를 못 굽는다(Drive 왕복). 그리고 개인 Claude 가
MCP 로 직결할 때는 분류가 아예 안 보인다 — 실제 도구 호출의 상당수가 그 경로다.

## D-6. 반박 관계는 **이미 생성되고 있다** — 버려질 뿐이다

좌석 출력 스키마에 `rebut=[{target,quote,counter,basis}]` 가 있다. 문제는 그것이
`rounds_data`(서버 메모리)에서만 살고, 프론트로 나가는 turn 이벤트에도 `delib_jobs` 저장에도
RA 회의록에도 안 남는다는 것이다 — `_item_text` 가 산문으로 평탄화한다. 즉 ⑥(지식 그래프)은
**새로 만드는 게 아니라 버리기를 멈추는 일**이다.
