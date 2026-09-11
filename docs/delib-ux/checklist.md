# 심의 UX 7건 — 체크리스트

승인된 순서대로. 체크는 **실제로 확인한 것**만 한다.

## ① 화이트리스트 네 칸 — 엔진에 있는데 웹에서 죽은 것을 켠다

- [x] 백엔드 `DelibOpts` 에 `non_negotiables` 선언(backend/app/agent/routes.py)
- [x] 백엔드 `DelibOpts` 에 `stop_after_round` 선언
- [x] 백엔드 `DelibOpts` 에 `rounds_so_far` 선언
- [x] 백엔드 `DelibOpts` 에 `append_to_report_id` 선언
- [x] `delibOptsToWire`(chatStore.ts)에 `stop_after_round` 추가 — 패널 토글은 이 겹도 통과해야 한다
- [x] `continueDeliberation` 이 `rounds_so_far`·`append_to_report_id` 를 실어 보낸다
      (`rounds_so_far` 는 `totalRounds`(계획값)가 아니라 **발언의 최대 round**(실측값)로 센다 —
      체크포인트로 일찍 멈추면 계획값이 과대평가된다)
- [x] ⚠ 체크포인트 토글이 이어하기에 따라붙지 않게 `stop_after_round: 0` 을 명시 —
      `extraDelibOpts` 가 패널 토글보다 **뒤에 병합**되므로 1회성이 보장된다
- [x] 회귀 방지 테스트 4건 — 프론트 두 경로에서 키를 뽑아 모델 필드와 집합 대조.
      **일부러 필드를 빼서 실제로 실패하는지 확인**했다(추출 실패 시에도 실패하게 만들었다)
- [x] 모델 통과 실측 — 네 값 전부 `model_dump` 를 통과해 중계된다
- [ ] **실제 심의를 한 번 돌려** 조항·라운드 번호·보고서 append 가 붙는지 — 아직 안 했다
      (LLM 왕복이 필요하고 RA 에 보고서가 생긴다)

## ② 반박 관계를 구조로 남긴다 (⑥·⑦의 재료)

- [x] 엔진이 `rebut` 를 turn 이벤트에 구조로 싣는다(`_rebut_items`, 테스트 3건)
- [x] 프론트 타입 `DelibTurn.rebut` + `mergeDelib` 병합
- [x] 심의 종료 후 **관계도** 렌더(`DelibGraph.tsx`, mermaid) — 누가 누구를 반박했는지.
      임시 진입점으로 확인: 노드 4·엣지 4 렌더, 좌석 색이 회의록과 일치,
      **반박이 없으면 아무것도 안 그린다**, mermaid 파싱 오류 0
- [x] `chatStore` 저장 트림에 `rebut` 예산 — 관계만 남기고 본문은 자른다(원문은 say 에 있다).
      쿼터를 넘기면 저장이 대화 절반을 버리고 재시도하므로 두 번 싣지 않는다
- [x] 서버 대화 저장소가 stance·non_negotiable·rebut 를 `meta` 로 영속(스키마 변경 없음) +
      프론트 복원. 구 저장분은 meta 가 없어 그대로 비어 온다(깨지지 않는다)
- [x] 이어하기가 **미해결 쟁점**을 승계 — `continue_summary` 의 남는 예산에 붙인다.
      결정문을 밀어내지 않고, 뒤 라운드(더 좁혀진 쟁점)를 먼저 싣는다.
      경계 실측: 예산 205/300/600/1200 전부 준수, 항목이 하나도 안 들어가면 빈 문자열
- [ ] JS 정본(infra/pipeline/hwax-deliberate.js)도 같은 구조를 내는지 — MCP 경로 파리티

## ③ 심의 좌석 조직도

- [ ] `PersonaBrowser` 를 다중 선택으로 — 선택 집합·토글·상한을 props 로
- [ ] 관련도(score/why)를 조직도에 배지로 머지 — 분류가 판단 근거를 지우면 안 된다
- [ ] 상한 12 / 하한 2 를 조직도 안에서 보이게(지금은 조용히 무시)
- [ ] ExpertPicker 와 HandoffBrief 의 기능 어긋남(axes/low_confidence) 정리

## ④ 도구 영역 분류

- [ ] 분류 정본을 어디에 둘지 결정(gateway 추적 파일 유력, config 는 안 됨)
- [ ] 영역 라벨 초안 — CAD·시뮬·VOC·보고서·물성·데이터·잡…
- [ ] 미분류 도구 수를 리포트(신규 도구가 조용히 빠지지 않게)
- [ ] 도구 선택 UI 3곳에 영역 1단 추가

## ⑤ VOC 먼저

- [ ] VOC 를 결정적으로 먼저 돌리는 스위치(지금은 질문 정규식 조건부)
- [ ] 결과를 사람이 고르는 UI(지금은 12건 자동 전량 전송)
- [ ] 고른 것으로 화두를 보강하는 폼

## ⑥ 되묻기

- [ ] Job 별 '메커니즘 분석 최소 정보' 체크리스트 정의
- [ ] 부족 항목 스캔 → `ask_user` 봉투(AIDataHub 선례)
- [ ] 답변을 담을 자리 결정(evidence 항목 vs 새 칸)
- [ ] ⚠ 고를 게 하나면 묻지 않는다(docs/upload/context-notes.md D-7)
