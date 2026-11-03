# SP 최신판 — cae00 사람 몫

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 묻는 것(읽기)은 받은 편지함 [`../cae00-inbox/2026-11-04.md`](../cae00-inbox/2026-11-04.md)에 있고,
여기는 박스를 바꾸는 걸음이다. 고친 날 2026-11-04(KST).

## 1. 허브 셋을 0.4.72 로

- 무엇 — 정본 허브(rootdesign) · FailureTrace · CAE 그룹 데이터 허브. 같은 SP 를 셋으로 띄운 것이라 판을 함께 맞춘다.
- 0.4.72(`ab41cff`)는 앱 · DB 가 0.4.71 과 같다(SP 커밋 글 — 키트 문서만 바뀌었다). 그래서 허브가 0.4.71 이면 올리지 않아도 MCP 도구가 같다. 판은 받은 편지함
  Q1 로 먼저 본다.
- 올리는 법 — 허브를 띄운 쪽이 SP 릴리스 번들의 `deploy/deploy.sh update`(SIF 교체 + 마이그레이션 + 재시작, 자료 그대로)로 인스턴스마다(`APP_SLUG`) 올린다.
  서버 두 대 이중화면 SP README 「이중화」 의 순서를 따른다. 이 리포 밖의 일이다.

## 2. 올린 뒤 — 포털 쪽 확인 · 반영

먼저 update-all 로 이 글이 든 포털 판과 게이트웨이 `a3ae08b2`(쓰기 낱말 repin — 게이트웨이 재기동으로 켜진다)를 받는다. 순서는 1절과 바뀌어도 된다.

1. 게이트웨이는 백엔드 도구 목록을 60초마다 다시 받아 바뀌면 다시 묶는다 — 허브를 올린 뒤 1 ~ 2분이면 재기동 없이 새 도구가 보인다(받은 편지함 Q1 명령을 다시 돌려 본다).
2. 운영자 미리보기 → 반영.

```bash
cd ~/Projects/HWAXPortal
python3 infra/scripts/sync-he-personas.py            # 미리보기 — 아무것도 바꾸지 않는다
python3 infra/scripts/sync-he-personas.py --apply    # 반영
```

   - 기대 — `he-data-coreontology` 에 ✗ 가 없다. '· 일부 he-data-coreontology: rootdesigndatahub 의 …' 줄이 없다(있으면 그 허브가 아직 옛 판이다 —
     빠진 도구만 빼고 만든다). '목록 밖 쓰기 he-data-coreontology' 줄이 없다(형제 허브의 같은 도구는 이제 관문과 같은 셈으로 적힌 것으로 센다 — SL-3).
   - 다른 운영자 줄은 이 판과 상관없다 — 앞서 보던 대로 읽는다.
3. 에이전트 서버 확인 관문은 `../HWAXPortal/infra/personas/he-team.json` 을 바뀐 시각으로 다시 읽는다(재기동 없음). update-all §7 의 관문 줄 또는 `/health` 의
   `confirm_gate.lists` 가 `loaded: true` · 쓰기 161 · 확인 114 면 이 판의 목록이다(목록은 박스와 상관없이 이 파일에서 온다).
