# HEAX-HUB MCP 자동연동 (auto-wire into HWAX Gateway)

> heax-hub에 MCP 앱이 추가되면 게이트웨이 config를 손대지 않고 자동으로
> 포털 챗 + 개인 Claude에서 그 도구를 쓸 수 있게 한다.

## 결정 (사용자 확정)

1. **표식 = 매니페스트 규약 (DB 마이그레이션 無)** — integrations의 `.portal/manifest.yaml`에
   `mcp:` 블록을 선언하면 그 앱이 MCP 서버로 인식된다. `AppType` enum은 건드리지 않는다.
2. **인증 = heax 서비스 PAT 주입** — 게이트웨이가 heax의 서비스 PAT(`claude-mcp`류)를
   `Authorization: Bearer`로 주입해 Caddy forward_auth(`/authz`) 게이트를 통과한다.
   heax registry가 각 MCP의 **상대경로**를 주고, base(오리진)는 게이트웨이 config가 갖는다
   (도메인 하드코딩 회피 — dev=localhost:4180 / prod=heax 도메인).

## 매니페스트 규약

`.portal/manifest.yaml`에 선택 블록 추가:

```yaml
mcp:
  expose: true            # 게이트웨이 흡수 대상 표식 (필수 true)
  path: /mcp              # 앱이 서빙하는 MCP 경로 (기본 /mcp)
  transport: streamable_http
  allowed_groups: []      # (선택) 게이트웨이 그룹 필터 — 비면 전체 공개, 있으면 caller
                          # groups 와 교집합 있어야 도구 노출/호출(쓰기·민감 도구 제한용)
```

스캐너가 manifest 전체를 `AppVersion.manifest_snapshot`(raw yaml)로 저장하므로
스캐너 수정 불필요 — `mcp` 블록이 그대로 보존된다.

## heax 측 (backend)

- 신규 라우터 `app/api/v1/mcp.py` → `GET /api/v1/mcp/servers`.
  - published(beta/stable) 앱 중 manifest에 `mcp.expose:true`인 것만.
  - 반환: `{"servers":[{"id","name","path":"/apps/<id><mcp.path>","transport"}]}` (상대경로).
  - 인증: 기존 `CurrentUser`(Bearer PAT) + `visible_app_ids` 가시성 필터.
- `router.py`에 include.

## 게이트웨이 측 (HWAXMcpGateway/gateway.py)

- config `heax_registry: {servers_url, base, token, poll_s}` (gitignore된 gateway_config.json).
  - `servers_url` = heax 백엔드 `http://127.0.0.1:4040/api/v1/mcp/servers`
  - `base` = heax Caddy 오리진 `http://127.0.0.1:4180` (MCP 실제 연결 대상)
  - `token` = heax 서비스 PAT
- `_discover_heax()` — servers_url 폴링 → `heax-<id>` 백엔드 spec(url=base+path, headers=Bearer token).
- `_backends_lifespan` 시작 시 + `_revive_loop` 매 주기: 신규 heax MCP는 추가·재집계,
  사라진 것은 정지·제거. 기존 정적 백엔드/재활 로직은 그대로.
- config에 `heax_registry` 없으면 이 기능 완전 비활성(기존 동작 무변경).

## 서비스 토큰 조달

- dev: heax `pat_service.issue()`로 seed admin 앞 PAT 1개 발급 → gateway_config.token.
- prod: provision-config.sh가 `HEAX_MCP_TOKEN` env 있으면 주입, 없으면 heax_registry 생략.

## 체크리스트

- [x] heax `app/api/v1/mcp.py` 작성 + router 등록
- [x] heax 재기동 → `GET /api/v1/mcp/servers` 인증·shape 검증(무인증 401, PAT 200 `{"servers":[]}`)
- [x] gateway.py `_discover_heax()` + lifespan/revive 통합 (heax_registry 없으면 완전 비활성)
- [x] gateway_config.example.json + provision-config.sh에 heax_registry(옵션, HEAX_MCP_TOKEN env) 반영
- [x] dev heax 서비스 PAT 발급(admin@example.com, name=hwax-gateway-mcp) → 라이브 gateway_config.json 주입
- [x] 테스트 MCP 앱(manifest `mcp` 블록)로 e2e: registry→gateway **자동 흡수(118→119, 재시작 無)**→
      Caddy forward_auth를 PAT로 통과→`selftest_ping` 게이트웨이 경유 호출 성공. 제거 시 자동 드롭(119→118)
- [x] 커밋 (HEAXHub / HWAXMcpGateway 각각; 시크릿 비커밋)

## 검증 결과 (2026-07-16, dev)

- 무인증 registry → 401, PAT → 200. 게이트웨이 재기동 시 heax 폴링 정상(빈 목록 → 백엔드 무변).
- 시드 앱(status=stable, manifest `mcp.expose:true`) + Caddy 라우트(`register_app_route`) →
  registry 즉시 노출 → 게이트웨이 revive 루프가 `heax-mcp-selftest` 백엔드로 흡수 → `selftest_ping`
  게이트웨이 경유 호출 `selftest pong: auto-wire works`. 앱 제거 시 다음 주기에 백엔드 자동 제거.
- gateway_config.json(600, gitignore)에만 heax PAT 저장 — 커밋 안 함. example/provision 은 플레이스홀더/env.

## 주의

- ReportArchive는 무관(hands-off 유지).
- Smart Twin Cluster(STC) MCP는 동결(사용자 개편 중) — 이 작업과 별개.
- gateway_config.json은 시크릿(600, gitignore) — PAT 커밋 금지.
