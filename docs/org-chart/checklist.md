# 조직도 재편 · HE팀 · 심층 보기 — 체크리스트

## ① 조직도 계층

- [x] 도메인→분류→루트 표(personaCatalog) + 미분류 폴더
- [x] 트리·개요 공용 컴포넌트 — PersonaBrowser·SeatBrowser 둘 다
- [x] 실 풀 781명으로 임시 진입점 검증

## ② HE팀 MCP 페르소나

- [x] he-team.json — 앱별 사전 지식·작업 순서·함정·예시 질문(17명, cae00 전용 2명 포함)
- [x] sync-he-personas.py — /tools-map 으로 도구 이름 대조·system_prompt 조립, AIDataHub upsert(미리보기 기본)
- [x] 에이전트서버 — mcp_apps 자동 바인딩, 입구 도구 first, 안내대만 상시 예약, 지식카드 선조회 생략, 캐시 TTL
- [x] 심의 자동 좌석 추천에서 he-* 제외(조직도 수동 선택은 허용)
- [x] dev 에 등록(15명) + 실제 챗으로 검증 — 열충격(predict_sed)·StepForge(list_projects)
- [x] 조직도 HE팀 묶음 라벨(HE_GROUP_LABEL) + 상세칸 '운영 앱' 줄
- [ ] ARP·ODB — cae00 에서 `python3 infra/scripts/sync-he-personas.py --apply` 로 생성, 사전 지식 보강

## ③ 에이전트 심층 보기

- [ ] 에이전트서버 — 지식카드 목록(페이지·검색·총수)·카드 본문
- [ ] 포털 프록시
- [ ] 전체 화면 뷰 — 역할 전문·예시·태그·카드 목록·본문 리더
- [ ] 두 브라우저 상세칸에서 진입
