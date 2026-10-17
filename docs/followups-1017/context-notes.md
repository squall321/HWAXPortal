# 10-17 사용자 결정 · cae00 리뷰 후속 — 결정과 까닭

**FU-D1 결정을 받은 방법(2026-10-17).** 남은 일 감사의 '정해 주셔야 함' 37줄을 탐색 에이전트 넷에 나눠 줄마다 '아직 열렸나 · 지금
코드는 무엇으로 도나 · 고르면 무엇이 바뀌나' 를 확인하게 했다(카드 64장). 데이터 이관 계획 §12 를 펼치니 체크리스트 줄보다 많아졌다.
카드를 넷으로 갈랐다 — 실제로 갈리는 것 21(여섯 묶음으로 여쭘), 이미 기본값으로 도는 것 27(한 번에 확정), 전제가 사라진 것 5 + 웹 검색에
딸린 둘(닫음), 사실 · 측정이 있어야 정할 것 11(필요한 것만 적음). 질문에 옮긴 사실은 직접 다시 확인했다 — 포털 저장소 공개
(`private: false`), 토큰 기본 범위 읽기 · 쓰기와 무기한 발급, 심의 조회의 주인 확인 없음, 리스크 앱 백업 일정 없음과 HEAXHub 스크립트가
제외 요청을 안 읽음, 데이터허브 0.0.0.0:8001 · 키 없이 200, 지식 리포 원격 없음 · ExpertGrounding 백업 없음, MXWP `instance stop --all`.

**FU-D2 VOC 는 다시 물었다.** 다섯째 묶음에서 '양쪽 수집 유지' 를 고르셨는데 그 카드는 cae00 도 수집한다는 전제였다. cae00 리뷰(D2)는
Redis 가 없어 cae00 수집이 돌지 않는다고 했다. 전제가 틀린 채 고른 답이라 다시 여쭸고 'dev 만 수집, 문서화' 로 정했다. 합치기의
'dev 가 이긴다' 규칙은 이 상태에 맞으므로 코드는 그대로다.

**FU-D3 사실이 있어야 정할 것(지금 열어 둔다).** 과제 키 대장(cae00 RA 기준정보에 과제 목록이 있나) · 절차를 게이트웨이 도구로(cae00 사용
수치) · RA 부서 표시(RA 담당의 답) · 카드 대조 동시 수(cae00 용량 측정) · ste 전각도 앱(preflight 결과) · 리스크 호출 원문 보존(cae00 DB
증가량) · 리스크 모델 상한(실제 STEP 크기) · ste 헤드노드 백업과 munge 키(헤드노드 확인) · 18대 노드 사양(장비가 정해지면).

**FU-D4 리뷰는 지금 HEAD 에서 다시 확인했다.** 리뷰는 cae00 이 돌린 커밋(포털 `70f9e5e` · 게이트웨이 `095c93a` · AIDataHub `57a5a4b` ·
HEAXHub `4e1954d` · KooRemapper `d25e12f`) 기준이다. 포털은 그 뒤 16커밋 · KooRemapper 28커밋이 더 있어 줄 번호가 다르다. 지적한 자리는
전부 그대로 있었다 — `services.py` 의 `open(log, "wb")` · update-all 의 `git stash show --name-only` · `provision-config.sh` 의
`mcp?token=` · 게이트웨이 `basicConfig(INFO)` · 에이전트 서버 `start.sh` 의 300초 조각 한도 · AIDataHub 병합의 `information_schema` 열 목록 ·
HEAXHub `SOURCE_NATURAL_KEY` 의 `publisher` · KooRemapper 안내 echo 의 백틱. 리뷰가 말한 U11 요청서는 이 리포에 없다(박스 쪽 문서) —
P3 · A1~A3 는 리뷰 본문과 안내서 문구를 기준으로 고친다.

**FU-D5 다른 세션의 작업은 건드리지 않는다.** 시작할 때 HEAXHub 에 남의 미커밋 수정(`deploy/apptainer/materialtwin-release-to-drive.sh`)이
있었고, KooRemapper · SignalForge 는 도구 상태 · 실행 산출물이 바뀌어 있었다. 커밋은 고친 파일만 골라 담는다.
