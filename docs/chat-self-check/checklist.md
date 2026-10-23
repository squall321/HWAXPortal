# 챗 자기검증 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md).

## 에이전트 서버
- [x] S1 감싸개 — 초안은 생각 칸 · 결과 붙잡기 · 고친 답 본문 · 근거 블록 재셈 · meta · 오류 · 조기 종료 길
- [x] S2 검토자 — 입력(예산 · 잘림 표지 · 쓰지 않는 몫 넘기기) · 다섯 가지 · 출력 꼴 · 판정 · 고친 점만 생각 칸(고친 답은 본문으로만)
- [x] S3 지킴 — 못 읽음 · 빈 답 · 지나치게 짧음 · 그림 링크 잃음 · 끊김 · 실패 · 바뀐 글자 없음은 ok
- [x] S5 손잡이(`CHAT_SELF_CHECK` · `CHAT_SELF_CHECK_THINK`) · 시험 환경 기본 끔(conftest)
- [x] 시험 21건 · 변이 32개 · 전체 2,682 통과 · 커밋 `d8011e0`
- [ ] push

## 포털 화면
- [x] S4 검증 표시(`CheckNote` · `CheckBadge`) · 브라우저 시험 5건 · 변이 8개
- [ ] 커밋 · 빌드 · Drive(포털 일치) · push

## 문서
- [x] 계획 · 결정(SC-D1~D11) · 업데이트 이력 · CLAUDE.md 행 · 기억
- [ ] dev 에이전트 서버 재기동(사용자 확인 뒤) — 그 전까지 dev 챗은 종전 그대로(화면은 self_check 가 없으면 아무것도 더하지 않는다)
- [ ] cae00 반영(update-all — 사람) · 실모델에서 `meta.self_check.ms` 와 고친 곳 표본 보기
