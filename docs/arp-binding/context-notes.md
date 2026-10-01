# ARP 연결 — 결정과 이유

**D-1 ①만 먼저(2026-10-01).** cae00 실측 `curl http://<ARP>:3001/` → `Found. Redirecting to /login.html?next=%2F`. ARP 웹에는
자체 로그인이 있고(게이트웨이 주석의 '무인증' 은 MCP 얘기다), 이동을 **절대경로**(`/login.html`)로 한다. 포털 경유 `/arp/`(접두어
STRIP)로 두면 그 이동이 포털의 `/login.html` 로 가 깨진다 — `proxy_redirect` 로 Location 은 고칠 수 있지만 화면 안의 자산·API
경로까지 절대경로면 ARP 쪽 base path 설정이 필요하다. 그래서 ②는 로그인 화면을 본 뒤 정하고, 그와 무관한 ①(주소 한 줄)을 먼저 한다.

**D-2 타일 주소는 systems.local.yaml 에 쓴다(routes.local.env 아님).** routes 파일에 쓰면 타일이 프록시로 승격되고 nginx 가
location 을 만든다 — ②를 정하기 전에는 직결 링크를 유지해야 한다. update-all 이 그 파일의 `arp:` 블록만 새로 쓰고 다른 타일은
그대로 둔다(덮어쓰기 칸은 url 하나뿐이라 블록을 통째로 바꿔도 잃는 것이 없다). 내용이 같으면 쓰지 않는다(재기동 지문은 내용 해시).
