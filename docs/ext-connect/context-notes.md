# 외부 연결을 설정만으로 — 결정과 까닭

> 계획 [PLAN.md](PLAN.md) · 요청서 [request.md](request.md) · 체크리스트 [checklist.md](checklist.md). 앞선 결정은
> [sso-delegation/context-notes.md](../sso-delegation/context-notes.md)(D-1 ~ D-20).

**EC-D1 요청서를 사양으로 삼고 dev 리포 두 곳만 고친다(2026-10-21).** 요청서는 cae00 에서 포털 `2e514e3` · 게이트웨이 `8e30ee5` 를 읽어
대조했고, dev 의 두 리포가 같은 커밋이라 `파일:줄` 이 그대로 맞는다(읽어서 확인). cae00 반영(4절)은 '운영 쪽 — 요청 아님' 이라 하지 않는다.
요청서 사본은 내부 주소 · 담당자 메일 주소만 자리표시로 바꿔 [request.md](request.md) 에 둔다(이 리포는 GitHub 에 있다).

**EC-D2 남은 질문(1-9)은 구현을 막지 않는다 — 설계의 기본값으로 짓고 결정은 사람에게 남긴다.** ③ 평문 토큰은 알리기만(이번 범위 밖),
④ 등록은 세션 + CSRF 만(PAT 거절 — 설계 그대로), ⑤ 신원 없는 호출은 거절(설계 그대로 — 절차 사전 점검을 넓히는 것은 따로),
①②⑥⑦⑨ 는 설정 · 운영의 일이고 ⑧ ⑩ 은 별도 요청이다.

**EC-D3 모르는 칸이 든 `connect:` 블록은 통째로 버린다(PB3).** 칸 표에 없는 이름(`verfy: url` 같은 오타)을 건너뛰고 나머지를 받으면
주인 확인을 켜려던 블록이 확인 없이 붙는다 — 오타가 검사를 조용히 끄는 쪽으로 틀린다. 버리고 알림(`Policy.warnings` → 배선 설정 ·
update-collab ①)을 남긴다. 다른 정책은 그대로 읽힌다(SSO 행 버리기와 같은 자세).

**EC-D4 `feat:connect` 는 `compute()` 한 곳에서 붙인다(PB12).** 화면이 받는 entitlements(`session.py` · `agent/routes.py`)와 게이트웨이가
읽는 `/internal/access/entitlements` 가 모두 `compute` → `with_entitlements` 를 지나므로 따로 고칠 곳이 없다. 사유는
`implied:plat:<id>` 이고 관리자도 받는다(관리자는 모든 `plat:` 을 가진다). 표의 항목이 아니라 요청 · 허가 대상이 아니다.

**EC-D5 PB14(선택)는 하지 않는다.** 선언 백엔드는 게이트웨이가 세션을 열기 전에 `_bypass_proxy_for` 로 호스트를 프록시에서 빼고(GW5),
포털 확인은 `trust_env=False` 라(PB9) 박스 `NO_PROXY` 가 덮지 않아도 새지 않는다. `check-egress.sh` 의 '덮이지 않음' 점검에 넣으면 고칠 것
없는 경고가 매번 뜨고, 셸이 포털 내부 정책을 읽으려면 공유 비밀을 다뤄야 한다. 호스트를 보려면 게이트웨이 `/health` 의 `conn_platforms`
와 로그(키 · 호스트 · 상태)를 본다.

**EC-D6 포털 전체 시험의 실패 둘은 이 작업과 무관하다(2026-10-21).** `test_llm_pool_lib.py::test_셀_수_없으면_0_이_아니라_모른다` ·
`test_llm_pool_update_all.py::test_임시_파일을_못_만드는_박스에서_풀을_꺼도_라우터를_내리지_않는다` 는 깨끗한 HEAD(`2e514e3`) 사본에서도 같이
실패한다(3,202 통과 · 2 실패). 둘 다 `ulimit -f 1` 로 here-doc 임시 파일 실패를 흉내 내는데, 그 실패가 일어나지 않아 시험 스스로
'시험이 헛돈다' 로 멈춘다. 원인은 확인하지 않았다(이 박스 bash 5.1 이 작은 here-doc 을 파이프로 보내는 것으로 짐작한다). 범위 밖이라 남긴다.
