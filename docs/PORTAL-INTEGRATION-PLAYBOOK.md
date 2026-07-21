# HWAX 포털 — 프로젝트 통합 운영 플레이북

> 새 앱(프로젝트)을 HWAX 포털에 붙이는 **표준 운영법**. ReportArchive 통합에서 end-to-end 검증됨.
> 다른 프로젝트에 전파용. "이 순서대로 따라 하면 `<portal>/<app>/` 로 뜬다"가 목표.

포털 구조 한 줄: **nginx(경로 라우팅)** → 각 앱(루프백 포트). 타일 메타는 `backend/config/systems.yaml`,
프록시 목적지는 `backend/config/routes.env`, nginx conf는 `infra/scripts/gen-nginx-conf.sh` 가 생성.

---

## 1. 통합 방식 고르기 (`integration_type`)

| 방식 | 언제 | 사용자 동작 |
|---|---|---|
| **proxy** (권장) | 앱을 포털 도메인 `/ <app>/` 아래로 넣고 SSO/TLS 공유 | nginx 역프록시. 앱이 **서브패스 인식** 필요(§2) |
| **external-url** | 앱이 자기 도메인/외부 주소가 따로 있음 | 타일이 그 URL 을 새 탭으로 염 |
| **jwt-handoff** | proxy + 포털 로그인으로 자동 로그인(SSO) | §8 |
| **iframe** | 외부 페이지 임베드 | X-Frame-Options 허용 필요 |

이 문서는 **proxy** 기준(대부분 이걸 씀).

---

## 2. 앱을 "서브패스 인식"하게 만들기 — proxy 의 핵심 (제일 중요)

앱이 `/ <app>/` 아래로 서빙되므로, **에셋·라우터·API 경로가 전부 그 prefix 를 달아야** 한다.
SPA(React/Vite) 기준 **3가지**:

1. **빌드 base** — 에셋 경로에 prefix. Vite: `vite build --base=/<app>/`
2. **SPA 라우터 basename** — ⚠️ **#1 함정**. 브라우저 URL 에 prefix 가 남으므로 라우터가 이를 알아야 함.
   React Router `createBrowserRouter` 는 **두 번째 인자**로:
   ```jsx
   const router = createBrowserRouter(
     createRoutesFromElements( /* ...routes... */ ),
     { basename: import.meta.env.BASE_URL.replace(/\/+$/, '') || '/' },   // ← 이 한 줄
   )
   ```
   standalone 빌드(base `/`)면 basename `/` 가 되어 **동작 동일** → 항상 넣어도 안전.
3. **API base** — 상대호출이 루트로 새지 않게. `VITE_API_BASE_URL=/<app>` → 호출이 `/<app>/api/...`
   로 나가고 nginx 가 prefix 를 벗겨 backend `/api/...` 로 도달.

포털용 빌드 한 줄(예):
```bash
NODE_OPTIONS=--max-old-space-size=8192 \
  VITE_API_BASE_URL=/<app> npx vite build --base=/<app>/
```
> `NODE_OPTIONS` 힙: 큰 SPA(plotly/three 등)는 기본 힙으로 빌드 중 OOM 남 → 8192 로 올린다.

**프레임워크별 서브패스 손잡이** (부록 A 참고):
Next.js `basePath`, FastAPI `--root-path`, Streamlit `--server.baseUrlPath`, Dash `url_base_pathname`,
Flask `SCRIPT_NAME`. — 포털은 이 값들을 env 로도 주입(`ROOT_PATH`, `BASE_PATH`, `NEXT_PUBLIC_BASE_PATH` 등).

---

## 3. 앱 서빙 (build-and-serve)

- **빌드 산출물을 서빙**한다(dev 서버 아님). 두 형태:
  - **combined**: 앱 백엔드가 빌드된 SPA + `/api` 를 한 프로세스로 서빙 (예: FastAPI `StaticFiles`/`SERVE_FRONTEND_DIST`). 가장 단순, 포털의 "업스트림 하나" 모델과 잘 맞음.
  - **split**: nginx/serve 가 정적 dist 직접 + `/api` 만 백엔드 프록시.
- **바인드는 `127.0.0.1:<PORT>`** (루프백). 포털 nginx 가 host netns 공유라 loopback 으로 닿는다. 외부 노출은 포털만.

---

## 4. 포털에 등록 (2곳 + 리로드)

**(a) 라우트** — `backend/config/routes.env` 에 한 줄:
```
<app>=http://127.0.0.1:<PORT>/
```
⚠️ **trailing slash 규칙** (`gen-nginx-conf.sh`):
- URL 이 **슬래시로 끝남** → nginx 가 `/ <app>/` prefix 를 **STRIP** (앱이 루트에서 서빙 + 에셋에 base 박힘 → 대부분 이것)
- **슬래시 없음**(bare host) → prefix 를 **PASS**(앱이 서브패스 *아래* 서빙, 예: `vite preview --base`)
- 경로가 있는 URL(`…/api/`)은 그대로 매핑(더 구체적 location 이 우선).

**(b) 타일** — `backend/config/systems.yaml` 에 `id: <app>` 타일. **이미 있으면** 그대로.
- 레지스트리가 **route 목적지가 생기면 `external-url`→`proxy` 자동 승격**(`app/catalog/registry.py`),
  `SYS_<APP>_URL` env 로도 목적지 지정 가능. → 보통 systems.yaml 은 손 안 대도 됨.

**(c) 반영** — 전체 스택 재시작 말고 **surgical**:
```bash
cd <portal> && bash infra/scripts/gen-nginx-conf.sh          # routes.env → hwax.conf 재생성
. infra/scripts/_common.sh
"$APPTAINER" exec instance://hwax_nginx nginx -t -c /workspace/infra/nginx/hwax.conf   # 검증
"$APPTAINER" exec instance://hwax_nginx nginx -s reload -c /workspace/infra/nginx/hwax.conf   # graceful
```
- 라우트만으로 `/ <app>/` 는 즉시 동작. **타일이 proxy 로 바뀌려면** 포털 레지스트리 재읽기 필요 →
  `hwax_portal` 인스턴스 재기동, 또는 admin `POST /systems/reload`.

---

## 5. DB 정책 (건드리면 안 되는 선)

- **구동 중인 다른 서비스의 DB/인스턴스는 절대 안 건드린다.** 각 앱은 자기 DB 를 가진다.
- **dev**: 중립 인스턴스 재사용(예: 호스트 시스템 PostgreSQL `:5433`)에 **전용 role + DB** 새로 생성.
  운영이 아니므로 여기 DB 는 비어있는 게 정상.
- **prod**: 실 구축 DB 사용. dev 와이어링(`routes.prod.env`/실 DB)과 별개.
- **extension 은 superuser 로 미리 생성**(마이그레이션이 `CREATE EXTENSION` 하면 non-superuser 는 실패):
  ```bash
  sudo -u postgres psql -p 5433 -d <db> -c "CREATE EXTENSION IF NOT EXISTS vector;"   # pgvector 예
  ```
- 접속정보(DATABASE_URL·secrets)는 **gitignored `.env`** 에만.

---

## 6. 한 줄 러너 (`start.sh` 패턴)

각 앱 리포에 흩어진 조각(venv·마이그레이션·빌드·서빙)을 **하나의 멱등 커맨드**로 묶는다.
골격(ReportArchive `start.sh` 참고):
```bash
./start.sh                 # 빌드(필요시)+DB+서빙, 포털 base /<app>/
./start.sh --standalone    # base "/" 로 (포털 없이 직접)
./start.sh --rebuild       # 강제 재빌드 (모드 바꿀 때)
./start.sh --portal        # + 포털 nginx 라우트 재생성·리로드 (멱등)
./start.sh restart|stop|status
```
핵심 동작: `stop → venv 보장 → DB migrate(idempotent) → build(base+api) → serve(127.0.0.1:PORT) → (opt) portal attach`.
포트/베이스는 env(`PORT`, `BASE_PATH`)로 오버라이드. 런타임 로그·pid 는 gitignore 경로(`*.log`)로.

---

## 7. 배포 박스 = "받기 전용" (git 운영)

배포 서버는 원격을 **받기만** 한다(로컬 수정/커밋 안 함).
```bash
git config pull.ff only                      # 갈라지면 그냥 에러 (merge/rebase 안 만듦)
git fetch origin && git reset --hard origin/main   # 원격에 100% 맞춤 (현재 divergence 정리)
```
- `reset --hard` 는 **추적 파일 로컬 수정을 날린다**. 그래서:
  - 서버 한정 값(DB URL·비밀·주소)은 **gitignored `.env`** 에 → 살아남음.
  - `basename` 같은 **소스 1줄**은 로컬에 들고 있으면 재빌드 시 사라짐 → **업스트림에 반영**하거나 `start.sh` 가 빌드 직전 주입.
  - untracked 파일(러너·로컬 문서)은 reset 후에도 유지됨.
- 새 버전 받은 뒤 실제 반영: **의존성 동기화(`npm ci`/`pip install`) + DB migrate + 재빌드 + 재기동** (= `start.sh --rebuild restart`).

---

## 8. 외부 인프라(AI/vLLM 등) — 설정 참조 원칙

- vLLM/LLM 처럼 **다른 서버에서 운영**하는 자원은 **config/env 로 주소를 잡고, 라이브 엔드포인트를 테스트로 확인하지 않는다**(dev 박스의 포트는 무관한 서비스일 수 있어 오해 유발).
- 예(ReportArchive): 생성 LLM = `LLM_BACKEND=openai` + `LLM_BASE_URL=http://<ip>:<port>/v1` + `LLM_MODEL=<served-model>`;
  임베딩 = `EMBEDDING_BACKEND=ollama` + `OLLAMA_BASE_URL=…`. dev 는 기본 `mock`(미연결)이 정상.

## 9. SSO (선택 — `jwt-handoff`)

- 포털이 짧은 **RS256 launch JWT** 발행 → 앱이 콜백 consumer(JWKS 검증 + 세션 발급) 구현.
- systems.yaml 타일: `integration_type: jwt-handoff` / `audience: <app>` / `url: /<app>/api/auth/portal-callback`.
- 서브패스 prefix-strip 전제 + SPA 는 토큰 handoff(cookie/localStorage) 방식에 맞춰야 함.
- 상세 consumer 구현은 각 앱 리포의 SSO 가이드 참조(예: ReportArchive `SSO_SETUP.local.md`).

---

## 10. 검증 체크리스트 (포털 경유 `:<HTTP_PORT>`)

```bash
P=http://127.0.0.1:8088          # 포털 nginx
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/                    # 200, SPA
curl -s $P/<app>/api/health                                          # 앱 헬스
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/assets/<hashed.js> # 200 (에셋)
curl -s -o /dev/null -w "%{http_code}\n" $P/<app>/<deeplink>         # 200 (SPA fallback)
for x in / /heax-hub/ /ai-data-hub/; do curl -s -o /dev/null -w "$x %{http_code}\n" $P$x; done  # 다른 라우트 무영향
```
- [ ] `/ <app>/` SPA 뜸 · 에셋 200 · 딥링크(새로고침) 200
- [ ] `/ <app>/api/...` 도달(strip 확인) · [ ] 타일 `proxy`/`available` · [ ] 다른 앱 무영향

---

## 11. 전파 시 각 프로젝트가 남길 문서 (deliverable)

- **포털 쪽**:
  - `docs/<APP>-FEATURE-SUMMARY.md` — 기능 6 + 마일스톤 6(주차별), 비개발자 개조식 (기존 앱들과 동일 포맷).
  - `docs/LINKED-SERVICES.md` 갱신 — proxy(strip/pass) 표에 `<app>` 행 추가.
- **앱 리포 쪽**: `docs/HWAX-PORTAL-INTEGRATION.md` — 아래 템플릿(부록 B) 채우기.

---

## 부록 A. 프레임워크별 서브패스 치트시트

| 스택 | 빌드/실행 base | 라우터/기타 |
|---|---|---|
| Vite + React Router | `vite build --base=/<app>/` | `createBrowserRouter(routes, { basename: BASE_URL })` |
| Next.js | `next.config` `basePath:'/<app>'` | asset prefix 자동 |
| FastAPI (SPA 서빙) | dist base `/<app>/` | `uvicorn --root-path /<app>` (docs/API 용) |
| Streamlit | `--server.baseUrlPath /<app>` | prefix pass |
| Dash/Plotly | `url_base_pathname='/<app>/'` | prefix pass |
| Flask/WSGI | — | `SCRIPT_NAME=/<app>` |
| 정적 HTML | 상대경로 or base 태그 | nginx `file_server` |

routes.env: **자기 에셋에 base 가 박히면 STRIP(슬래시 O)**, **서브패스 아래서 서빙하면 PASS(슬래시 X)**.

## 부록 B. 앱 리포용 `docs/HWAX-PORTAL-INTEGRATION.md` 템플릿

```markdown
# <App> ↔ HWAX 포털 통합

- integration_type: proxy   (base /<app>/)
- 서빙: <combined FastAPI | split nginx> on 127.0.0.1:<PORT>
- 빌드: `NODE_OPTIONS=--max-old-space-size=8192 VITE_API_BASE_URL=/<app> vite build --base=/<app>/`
- 서브패스 손잡이: <router basename 1줄 | next basePath | --root-path ...>
- routes.env: `<app>=http://127.0.0.1:<PORT>/`   (STRIP)
- DB: dev=<중립 인스턴스/포트/role>, prod=<실 DB>. extension: <있으면 superuser 생성>
- 실행: `./start.sh` (또는 배포 스크립트)
- SSO: <미구현 | jwt-handoff, 콜백 = /<app>/api/auth/portal-callback>
- 검증: §10 체크리스트 통과
```

---

*작성 기준: ReportArchive 포털 통합(2026-06) 실전 경험. 포털 내부 동작은 `docs/LINKED-SERVICES.md`,
`infra/scripts/gen-nginx-conf.sh`, `backend/app/catalog/registry.py` 참조.*
