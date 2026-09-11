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

- [ ] 엔진이 `rebut` 를 turn 이벤트에 구조로 싣는다(지금은 산문 평탄화)
- [ ] 프론트 타입 `DelibTurn.rebut` + 저장(chatStore trim 예산 확인)
- [ ] 서버 대화 저장소가 stance·non_negotiable·rebut 를 잃지 않는지
- [ ] 심의 종료 후 **지식 그래프** 렌더(mermaid) — 누가 누구를 반박/지지했는지
- [ ] 이어하기가 반박·수치를 요약이 아니라 구조로 승계하는지

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
