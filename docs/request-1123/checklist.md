# 체크리스트 — nginx 한도(cae00 11-23 요청)

- [x] HP-79 템플릿 http 수준 `proxy_read_timeout` · `proxy_send_timeout`(손잡이 `NGINX_PROXY_READ_TIMEOUT` · 600s)
- [x] HP-80 `worker_rlimit_nofile`(손잡이 `NGINX_WORKER_RLIMIT_NOFILE` · 65536 · hard 한도로 낮춤)
- [x] HP-73 `*-mcp` 라우트 스트리밍 묶음(`NGINX_MCP_READ_TIMEOUT`)
- [x] HP-81 큰 응답 버퍼 손잡이(`NGINX_LARGE_BUFFER_ROUTES` · 기본 끔)
- [x] 시험 — 생성된 conf(HTTP · TLS) · 틀린 값 · hard 한도 · 기존 값 그대로(/ste/ · /apps/ · /report-archive/ · /agent/ · /mcp-gw/) · `nginx -t`
- [x] `.env.example` 손잡이 넷 주석
- [ ] 포털 전체 회귀 → main
- [ ] dev conf 재생성 · reload · worker `Max open files`
- [ ] cae00 받은 편지함 2026-11-23 덧붙임 · 업데이트 이력
