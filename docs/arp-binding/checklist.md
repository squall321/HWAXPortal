# ARP 연결 — 체크리스트

- [x] update-all 1f: ARP_HOST·ARP_PORT → systems.local.yaml `arp.url` · provision.env `ARP_BASE` (모양 검사, 없으면 ○)
- [x] §5: 게이트웨이 config 의 arp 주소가 ARP_HOST:ARP_PORT 와 다르면 재프로비저닝
- [x] `.env.example` 에 ARP_HOST·ARP_PORT · 배포 가이드 한 줄
- [x] 추적 파일의 사내 IP 예시 지우기(update-all 주석 셋·게이트웨이 provision-config ARP 주석) · 내부 IP 가드 14 → 13
- [x] 시험(신규 12 · 변이 4건 전부 사망 · 포털 전체 991) · 커밋·푸시
- [ ] ② 판단: cae00 에서 `curl -s http://<ARP>:3001/login.html | head -40` 결과로 하위 경로 가능 여부
