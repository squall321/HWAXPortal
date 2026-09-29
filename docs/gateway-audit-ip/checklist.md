# 게이트웨이 감사 IP — 체크리스트

- [x] 게이트웨이: `_request_ip()`(형식 검사) · `_request_via()` · `_audit(ip=, via=)` + caller 기본값
- [x] 게이트웨이: 미들웨어 두 분기에서 `x-hwax-via` 싣기 + 클라이언트 사본 버리기
- [x] 게이트웨이: `/mcp` 401 감사(IP·사유)
- [x] REST 다리: `request.client` 직접 전달, 계정은 이메일, 토큰 없음도 감사
- [x] 시험: 컨텍스트 있음/없음·가짜 값·`.client` 없음·위조 via 버림·401·REST · 변이
- [x] dev 실검증(nginx 경유 = 외부 IP, 직접 = 127.0.0.1, via 구분)
- [x] 문서(README 감사 칸)
- [x] 적대적 검토 1차(D-9) — 확인 3건 + 방어 1건 반영, 변이 5건 전부 사망, 시험 109 → 112
- [ ] 푸시 · cae00 반영(게이트웨이 pull + 재기동)

### 결과(2026-09-29)
- 시험: 게이트웨이 99 → 109(+10). 변이 10건 전부 사망(via 사본 두 분기·형식 검사·주소 읽기 가둠·caller 기본값·401 거름·
  챗 판정·REST 계정·REST 토큰없음·REST 주소).
- dev 실검증(게이트웨이 재기동, 리스너 pid 교체 확인): 직접 127.0.0.1:9110 → `ip=127.0.0.1 via=gw-token` · nginx `/mcp-gw/` 경유
  → 박스 공인 주소 · 토큰 없이 → `POST /mcp unauthorized: no-bearer` + 주소 · `.well-known` 조회는 안 남음 · 이 세션의 개인
  PAT(박스 안 Claude Code) → `caller=<계정> ip=127.0.0.1 via=pat`.
