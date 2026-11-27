# 자동 파이프라인 — 과제 · 차수에 새 입력이 오면 정해 둔 해석 · 보고서를 서비스 신원으로 저절로 돌리는 격리 모듈(docs/auto-pipeline)
"""포털은 해석을 모르고 계약(contract.md v1.1)만 부른다. 설계 기준은 docs/auto-pipeline/portal-api.md 다.

- spec     규칙 스펙 검증(범위 · 트리거 · 단계 연결도 · 한도 · stage)
- contract 앱 답의 꼴(원천 · 해석 다섯) · 입력 지문 · idem_key
- store    절차 저장소(procedures.sqlite)의 새 표 — 루틴 저장소처럼 같은 연결을 같이 쓴다
- token    호출마다 찍는 15분짜리 서비스 토큰(AP-8 · AP-13 — jti svc-ap-…)
- gateway  게이트웨이 호출(절차 실행기의 GatewaySession) · /tools-map 의 orig 로 노출 이름 찾기
- report   결과 봉투로 코드가 쓰는 보고서(per_analysis · summary · revdiff)
- ra       RA 시스템 계정 게시(박스 파일 auto_pipeline 줄이 있을 때만)
- engine   한 박자(감지 → 판정 → 실행 만들기 → 단계 나아가기 → 끝)
- routes   창구 /autopipe-api
"""

FEAT = "feat:auto-pipeline"          # grant_only — 「전부」 · 관리자 전권에 딸려 오지 않는다(AP-9)
JOB = "auto-pipeline"                # 서비스 신원의 작업 이름 — sub system:auto-pipeline, 게이트웨이 허용 목록의 jobs 키
