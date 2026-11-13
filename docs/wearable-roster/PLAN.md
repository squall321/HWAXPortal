# 웨어러블 로스터 161명 — 지식카드 저작 (포털 몫)

> 정본 계획은 ExpertAgents 가지 `wt1113/wearable-roster` 의 `docs/01-plan/wearable-roster.plan.md`(OI-014) · 지시서 `wearable-roster.brief.md` ·
> `checklist-wearable-roster.md` 다. 이 폴더는 포털이 맡는 것만 적는다. 할 일 [checklist.md](checklist.md) · 결정 [context-notes.md](context-notes.md).

## 무엇

사용자 요청(2026-11-13) — "예산 막혀서 안 되던 것들 다 해 줘" → 고른 것 「논문 전문 → 지식카드 저작」, 이어서 "웨어러블 지식카드를 서브에이전트로 나눠 만든다.
드라이브에 웨어러블 · 인체공학 논문을 계속 모은다 · 논문 받는 건 됐고 지식카드 만들기 가자."

- 로스터 정본은 Drive `KnowledgeAssets/PaperDownloader/WEARABLE_EXPERT_ROSTER.md`(161명 · 19 클러스터).
  인체공학 `HUMAN_ERGONOMICS_EXPERT_ROSTER.md`(147명)는 그 논문이 Drive 에 올라오면 같은 길로 간다(11-13 현재 검색 목록만).
- 이 세션이 조율하고, 저작 · 검증은 워크플로 서브에이전트가 ExpertAgents worktree 에서 한다(본 리포의 동료 미커밋 JEDEC 작업 무접촉).

## 포털 몫

1. 조직도 라벨 — `frontend/src/components/chat/orgTaxonomy.json` 에 '웨어러블 HW 지식' 갈래 + 도메인 19개(`b8849209`). 전문가가 없는 도메인은 트리가 숨긴다.
2. 배정 · 겹침 도구 — 추출본 색인 · BGE-M3 배정 · 기존 전문가 최근접 · 약어 배정(세션 스크래치 — 결과는 ExpertAgents 계획에 실린다).
3. 워크플로 셋 — 클러스터 계획(19) → 전문가별 저작 → 카드당 적대 검증 · 정정 · 재판정.
4. 마무리 — AIDataHub 내보내기(dev) · 프론트 빌드 · 업데이트 이력 · cae00 받은 편지함(새 분류 · 새 전문가가 AIDataHub 동기화로 간다).
