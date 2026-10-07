# ARP 연결 — 결정과 이유

**D-1 ①만 먼저(2026-10-01).** cae00 실측 `curl http://<ARP>:3001/` → `Found. Redirecting to /login.html?next=%2F`. ARP 웹에는
자체 로그인이 있고(게이트웨이 주석의 '무인증' 은 MCP 얘기다), 이동을 **절대경로**(`/login.html`)로 한다. 포털 경유 `/arp/`(접두어
STRIP)로 두면 그 이동이 포털의 `/login.html` 로 가 깨진다 — `proxy_redirect` 로 Location 은 고칠 수 있지만 화면 안의 자산·API
경로까지 절대경로면 ARP 쪽 base path 설정이 필요하다. 그래서 ②는 로그인 화면을 본 뒤 정하고, 그와 무관한 ①(주소 한 줄)을 먼저 한다.

**D-2 타일 주소는 systems.local.yaml 에 쓴다(routes.local.env 아님).** routes 파일에 쓰면 타일이 프록시로 승격되고 nginx 가
location 을 만든다 — ②를 정하기 전에는 직결 링크를 유지해야 한다. update-all 이 그 파일의 `arp:` 블록만 새로 쓰고 다른 타일은
그대로 둔다(덮어쓰기 칸은 url 하나뿐이라 블록을 통째로 바꿔도 잃는 것이 없다). 내용이 같으면 쓰지 않는다(재기동 지문은 내용 해시).

**D-3 타일은 포털 경유(`/aireadyportal/`), update-all 1f 는 타일 덮어쓰기를 쓰지 않는다(2026-10-08) — D-1·D-2 를 대체한다.**
D-1 의 보류 사유(ARP 가 `/login.html` 같은 절대경로로 이동해 접두어 STRIP 프록시 뒤에서 깨진다)는 ARP 가 고쳐 없어졌다 —
`arp_base.js` 신규 · stripMiddleware · `go()` 접두어 부착(2026-09-28~10-06). 그래서 타일의 목적지는 이제 `routes.local.env` 의
`aireadyportal=` 한 줄이고(접두어는 ARP 요청서 그대로, 10-07 결정), D-2 가 정한 `systems.local.yaml` 의 `arp:` 직결 덮어쓰기는 쓰지 않는다.
1f 에서 `_upsert_tile_url` 과 그 호출을 걷었다. 남는 것은 `ARP_HOST` → 게이트웨이 `provision.env` 의 `ARP_BASE` 기입과 §5 의 주소 드리프트 검사다.

걷은 이유는 셋이다. ① 타일 id 가 `aireadyportal` 로 바뀌면(작업지시 7-3) 1f 가 매 실행 다시 쓰는 `arp:` 는 **고아 항목**이 된다 —
레지스트리가 경고하고, 이 파일은 포털 재기동 지문에 들어 있어 지문만 흔든다. ② "포털 경유는 보류(D-1)" 라는 낡은 주석이 스크립트에 남아
있었다. ③ ARP_HOST 가 없을 때의 안내문이 "타일 주소를 systems.local.yaml 에 둔다" 고 사람을 잘못 이끌었다.
작업지시 원안이 든 근거("덮어쓰기가 콜백 주소를 덮어 SSO 가 조용히 깨진다")는 **틀렸다** — 핸드오프 타일의 덮어쓰기는 레지스트리가
무시하고(`41e6f67`), `test_catalog_local_overlay` 가 그것을 지킨다. 그래도 위 셋 때문에 걷는다.

그대로인 것 — 플랫폼 id `arp` 와 게이트웨이 백엔드 키 `arp`(바꾸면 `plat:arp` 가 걸린 전원이 막힌다, docs/change-request-8-10 D-6).
큰 업로드(해석결과 최대 6GB)는 nginx 의 `aireadyportal` location 에서만 상한을 푼다(전역 2048m 은 그대로 — 같은 문서 D-6).

⚠ 1f 는 `aireadyportal=` 라우트를 **적지 않는다**(1e 가 `report-archive=` 를 적는 것과 다르다). ARP 서버 주소는 `infra/.env` 의
`ARP_HOST` 와 `routes.local.env` 의 `aireadyportal=` 두 곳에 손으로 있다 — 이사하면 둘 다 고친다.
박스에서 할 일은 7-3 이 들어온 뒤 `systems.local.yaml` 의 `arp:` 블록을 지우는 것 하나다(1f 는 이제 그 파일을 읽지도 쓰지도 않는다).
