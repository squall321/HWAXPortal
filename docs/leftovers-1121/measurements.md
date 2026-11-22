# 운영 박스 측정 묶음 — 아홉 가지를 한 장에(11-22)

> 지어 놓고 재지 않은 것들이다. 재는 일은 운영 박스(cae00)에서만 된다 — dev 의 모델 · 데이터로 잰 값은 운영 판단에 쓰지 않는다.
> 여기는 **차례와 가리킴**만 둔다. 명령 · 판정 기준의 정본은 줄마다 적힌 그 주제의 절차서다(11-22 에 문서와 스크립트를 대조해 옮겼다).
> 계획은 [PLAN.md](PLAN.md) R3, 까닭은 [context-notes.md](context-notes.md) L21-13 이다.

## 차례 — 무엇이 무엇을 기다리나

1. **지금 바로 할 수 있는 것** — 전문가 온톨로지 잇기(⑨의 build → dry-run → bind) · 심의 품질 T1(①) · 10-29 박스 A/B(②) · 문서 변환(⑤ — 금 표본을 누가 주는지만 정해지면).
2. **실제 변경 대상이 있어야 하는 것(사람 — 리스크 재설계 M0-d)** — 리스크 M3 실주행(⑥) · 조합 QA(④) · 20만 창 A/B(⑦). 셋 다 같은 대상을 쓴다.
3. **그 뒤** — LLM 풀 용량(⑧ — 카드 대조 원장에 실사용 줄이 있어야 부하를 만든다. 심의 · 카드 대조가 0 일 때만 돈다) · 전문가 고르기 기준선(③ — 평가셋 A 를
   Drive 로 받고 실사용 질문 190건에 사람이 표시한 뒤) · 온톨로지 신호 켜기(⑨의 끝 — ③과 같은 날 재고 사용자가 수를 본 뒤).

①(심의 A/B) · ③의 LLM 겹 · ⑥ · ⑧은 같은 GLM 을 쓰므로 같은 시간에 두지 않는다.

## 아홉 가지

| # | 측정 | 정본 절차 | 먼저 있어야 하는 것 | 걸리는 것 | 돌려줄 수 | 막힌 것 |
|---|---|---|---|---|---|---|
| ① | 심의 품질 A/B(T1 ~ T7) | `../followups-1017/server-setup.md` 7절(T1). 그 뒤 손잡이는 같은 러너 `HWAXAgentServer/tools/delib_ab.py --knob <이름>` — `rebut_quote`(T2) · `prose_first`(T3) · `reasoning_effort`(T4 — 낮음 대 높음) · `chair_bestof` · `chair_cite`(T5) · `cross_exam` · `anchor`(T6) · `undecided`(T7) | GLM · 근거 도구 넷이 게이트웨이에 있을 것(`search_reports` 는 RA 가 붙어야 생긴다) · 심의가 한가한 때 | 손잡이 하나에 심의 18회(조건 둘 × 질문 셋 × 3회) — 몇 시간. 그동안 update-all 이 에이전트 서버 재기동을 미룬다 | 대조표(발언당 수치 인용 · 반박 인용률 · 파싱 실패율 · 결정문 수치 밀도) · 결정문 두세 쌍을 나란히 읽은 판정 | T2 는 T1 판정 뒤 · T3 은 T4 뒤 · T4 · T7 은 묶음 B 가 올라간 뒤(`reasoning_effort` · `undecided` 손잡이) |
| ② | 10-29 박스 A/B(대화 고정 O-2 · 도구 설명 예산 O-3 · 생각 강도 O-4) | `../request-1029/server-setup.md` 4 · 5절 | stcx 챗 LLM · 정답표 16문항 점검기(cae00 의 `~/ontology-test/` — 리포에 없다) | 문서에 없음 | OT-06 ~ 10 의 정본 허브 호출 · 프롬프트 토큰 평균 · 접두 캐시 적중 · 첫 토큰 시간 · 자기검증 p95 · 판정이 떨어지지 않는지 | 없음 |
| ③ | 전문가 고르기 기준선(E-5 B0) | `../request-1029/design-e5.md` 2.5 ~ 2.7 · 8절, 사람 몫은 `../request-1029/server-setup.md` 9절. 러너 `HWAXAgentServer/tools/seat_eval.py run · bands · report` | 평가셋 A · P · C(dev 가 지었다 — Drive 로 보내기가 남았다) · 실사용 질문 190건에 사람 둘이 표시(사용자 허락 · `SEAT_QUESTIONS_COLLECT=1`) · GLM(LLM 겹) | 문서에 없음(띵킹 본심 100건이면 좌석 호출 수백 번) | acc@1 · acc@3 · MRR@10 · 심의 hit@5 · 띵킹 적중 · '없음' 정밀도와 재현율, 관문 G0 | 평가셋 A 전송 · H 표시 |
| ④ | 리스크 앱 조합 QA | `../risk-app-combo-qa/PLAN.md` 2 ~ 4 · 6절 | Claude Sonnet(사용자 결정 11-01) · `EXTERNAL_LLM_ENABLED` · 돌릴 사람의 PAT 와 잡마다 반출 동의 · **실제 변경 3쌍** · 도메인 담당자의 판정 | Sonnet 과제 약 2,000 ~ 4,500(워크플로 한 번 상한 약 800 이라 여러 번) | 조합별 실제 리스크 재현율 · 앱별 고유 리스크 · 뺐을 때 줄어드는 몫 · 비용 — 결론은 필수 · 조건부 · 뺌 | 실제 변경 대상(M0-d) |
| ⑤ | 문서 → RA 정밀 변환 — 금 표본 기준선 · 판독 지표 | DocForge `docs/EVAL.md` 2 ~ 4절 · `docs/M0.md`, 포털 `../doc-to-ra/PLAN.md` 10 · 11절 · `cae00-handoff.md` | 금 표본 실문서 40 + DRM 5(사람이 준다) · stcx Qwen(동시 2 이하) · RA 엄격 생성은 사용자 명의 | 측정 시간은 문서에 없음 | 글 회계 100% · 표 칸 99% · 차트 값 100% · RA 저장 100% · 판독 유용성 3.5 이상 · 지어낸 수치 0 · 편집량이 기준선보다 적을 것 | 금 표본을 누가 언제 주는지 |
| ⑥ | 리스크 심사 M3 전원 실주행 | `../risk-review-redesign/server-setup-m3.md` 5절(5-1 ~ 5-9) · 1-5 · 6절 | 0절의 차례(M0-b → M0-d → 스키마 5 → M2 파일럿 → 챗 지연 기준선) · cells 대상 · 검토자 PAT · GLM | 배정표 승인 뒤 약 8,000 ~ 10,000 호출 — 3 ~ 4일(동시 8). 쟁점 패널 반나절 ~ 이틀 | 나갈 기준 여섯 · 진행판 · 쟁점 · 보고서 요약 · DB 크기 전후 · 챗 지연 | M0-b · M0-d · M2 파일럿 |
| ⑦ | 리스크 20만 창 A/B(W5) | `../risk-200k/server-setup.md` 4절 | 긴 카드를 가진 전문가가 드는 실제 대상 하나 · 빈 포트의 임시 에이전트 서버(`LLM_CONTEXT_TOKENS=200000`) | 문서에 없음(dev 표본에서 판정 호출 2.6배 · 훑기 4.5배) | 셀마다 걸린 카드 집합의 일치율 · 호출 수 · 잡 시간 · `[누락 0 증명]` | 실제 대상(M0-d) · G3 기준값(그때 사용자에게 묻는다) |
| ⑧ | LLM 풀 용량 | `../llm-pool/capacity.md` 1 ~ 8절 — `infra/scripts/llm-lengths.py` → `llm-capacity.sh --dry-run` → 본 측정 | 심의 · 카드 대조 · 줄 선 심의가 모두 0 · 카드 대조 원장에 실사용 줄 · 같은 모델의 서버 둘 | 보통 30 ~ 60분 — 그동안 챗이 느려진다 | 단계별 TTFT · 요청/s · 변형별 권장 동시 수와 세 손잡이 권장값 | 원장의 실사용 줄(⑥ 또는 M2 파일럿 뒤) |
| ⑨ | 전문가 · 지식카드 온톨로지 잇기 | `../expert-ontology/server-setup.md` 1 ~ 6 · 8절 — `onto.sh build` → `card-entity-bind.py --dry-run` → 잇기 → `persona-domains-build.py` | update-all 로 받기 · 정본 허브를 읽을 수 있는 PAT | build 15초 · 잇기 4분 안팎 | 받은 편지함 2026-11-21 Q1 ~ Q5(낱말 수 · 타입별 exact · 연결 요약 · 연결표) | 신호 켜기는 수를 본 뒤(③과 같은 날) |

## 대조하다 본 어긋남(고칠 것)

- **심의 손잡이의 기본값** — 절차서는 「손잡이는 전부 기본 꺼짐」 이라 적지만 엔진은 `DELIB_REBUT_QUOTE` · `DELIB_CROSS_EXAM` 의 기본이 1(켜짐)이다. T2 · T6 의 A/B 는
  「끔 대 켬」 으로 돌려 대조군이 끈 쪽이 된다 — 러너는 대조군을 0 으로 보내므로 그대로 돌리면 된다. 결과를 읽을 때 「운영 기본 = 실험군」 임을 적는다.
- **조합 QA 의 점검 스크립트 자리** — 계획서는 `scripts/rr_gateway_check.py` 라 적지만 실제는 `HWAXRisk/backend/scripts/rr_gateway_check.py` 다.
- **20만 창 A/B** — 메움(11-22) — `../risk-200k/server-setup.md` 4-1 ~ 4-4. 리스크 앱은 엔진을 포털 중계(`HWAXRISK_PORTAL_BASE` → 포털
  `AGENT_SERVER_URL`)로만 보고 잡마다 고르는 칸이 없어 **박스 전체**다 — 임시 서버(원장 따로 · `LLM_CONTEXT_TOKENS=200000`)를 띄우고 사람이 없는 때
  포털만 그쪽으로 다시 띄웠다가 되돌린다(운영 에이전트 서버는 내리지 않는다).
- **10-29 O-4** — 메움(11-22) — `../request-1029/server-setup.md` 4-1. `xhigh`(대조군) → `medium` → `low`, 조건마다 16문항 × 3회(T1 관례). `high` 는
  모델 템플릿이 받는지 확인 필요.
- **문서 변환의 기준선 둘** — 메움(11-22) — `../doc-to-ra/server-setup.md` §8. 돌리는 명령은 포털 업로드 창구 둘(목적지 `reportarchive` · `aidatahub`)과
  DocForge `edits.py snap` 이다. **채점기는 아직 없다** — DocForge `run.py` 가 DocForge 패키지만 읽어 지어야 한다(DocForge 몫).
