# HWAX Portal — 에이전트용 안내

사내 시스템 SSO 브로커 허브 + AI 챗/심의. FastAPI(백엔드) + React/Vite(프론트),
apptainer 인스턴스로 뜬다.

> 전역 `~/.claude/CLAUDE.md` 의 규칙(생각 먼저·최소 구현·수술적 변경·테스트 후 완료·
> 한국어 문장은 마침표로 끝)이 그대로 적용된다. 이 문서는 **이 리포에만 해당하는 것**을 적는다.

## 먼저 읽을 것

**[docs/gotchas.md](docs/gotchas.md)** — 실제로 사고가 났던 함정들이다. 포트킬 오살,
`git status` 절단으로 남의 작업 무효화, dev 에서 `deploy-all` 실행 시 리포 리셋,
e5 임베더 코사인 오독. 짐작으로 피할 수 있는 것들이 아니다.

## 박스마다 경로가 다르다 — 절대경로를 박지 마라

| 박스 | 리포 루트 |
|---|---|
| dev (smarttwincluster) | `/home/koopark/claude/<Repo>` |
| **cae00** | **`/home/koopark/Projects/<Repo>`** |

스크립트·설정·매니페스트 전부 **상대경로**로 쓴다. 앵커는 그 파일이 속한 리포 루트이고,
루트는 파일 위치에서 유도한다.

```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"      # bash
Path(__file__).resolve().parents[2]                          # python
```

형제 리포는 `../<Repo>` 로 닿는다. 절대경로를 박으면 cae00 에서 **조용히** 깨진다.

## 띄우기

```bash
./infra/scripts/start.sh      # 없는 것만 띄운다(멱등)
./infra/scripts/status.sh
./infra/scripts/restart.sh    # 스택 전체 — routes.env·infra/.env 를 다시 읽는다
```

포털만 다시 띄우려면 인스턴스 하나만 내리고 `start.sh` 를 다시 부른다. 코드는
`$REPO_ROOT:/workspace` 로 **바인드 마운트**라 SIF 재빌드가 필요 없다.

```bash
apptainer instance stop hwax_portal && ./infra/scripts/start.sh
```

프론트를 고쳤으면 `cd frontend && pnpm build` 가 먼저다 — 컨테이너는 `frontend/dist` 를 낸다.

| 포트 | 무엇 |
|---|---|
| 8723 | 포털 백엔드(SPA 도 여기서 낸다) |
| 5283 | Vite 개발 프록시 |
| 9009 | Agent Server (챗·심의 SSE) |
| 9110 | MCP 게이트웨이 |

## MCP

`.mcp.json` 이 리포에 있다(박스 경로에 안 묶이게). 토큰은 **환경변수로** 준다.

```bash
export HWAX_GATEWAY_PAT="<포털 /auth/pat 로 발급한 PAT>"
export HWAX_GATEWAY_URL="http://127.0.0.1:9110/mcp"   # 기본값이라 보통 생략
```

⚠ **도구가 있는지는 소스가 아니라 게이트웨이 `tools/list` 로 확인한다.** 앱 소스에
있어도 배포된 SIF 가 낡으면 게이트웨이에 안 뜬다 — 실제로 `unknown tool: intake` 로
한 번 터졌다(docs/upload/context-notes.md D-8).

## 심의 파이프라인

정본은 **`infra/pipeline/*.js`** 다. `.claude/workflows/` 는 사본이고 gitignore 다.

```bash
./infra/scripts/sync-workflows.sh --check   # 어긋난 것만 보고(종료코드 1=어긋남)
./infra/scripts/sync-workflows.sh           # 정본 → 사본
```

`update-all` 이 이 동기화를 포함한다. **JS 를 고쳤으면 sync, 파이썬(`deliberation.py`)을
고쳤으면 agent-server 재기동**이다 — 둘은 반영 경로가 다르다.

```bash
cd ../HWAXAgentServer && ./start.sh -d      # 재기동(백그라운드, 로그 agent-server.log)
```

## 이 리포에서 하지 않는 것

- **ReportArchive 리포에 커밋·push 하지 않는다.** federation 자동화의 제외 대상이다.
  API 로만 쓴다. 자세한 이유는 gotchas 참조.
- **dev 박스에서 `deploy-all-from-drive.sh` 를 돌리지 않는다.** 미푸시 커밋이 날아간다.
  빌드만 시험하려면 `build-all-to-drive.sh` 를 쓴다.
- 내부 IP·토큰·비밀번호를 추적 파일에 적지 않는다. 이 리포는 GitHub 에 있다.

## 문서

| 주제 | 위치 |
|---|---|
| 함정·사고 기록 | `docs/gotchas.md` |
| cae00 배포 | `docs/cae00-deploy-guide.md` |
| 챗 업로드 목적지 라우팅 | `docs/upload/` (PLAN·checklist·context-notes) |
| 심의 품질·방법 메뉴 | `docs/deliberation-quality/` |
| 설계 리스크 심사 | `docs/design-risk-review/` |

작업을 시작하기 전에 해당 폴더의 `context-notes.md` 를 본다 — **왜 그렇게 했는지**가
거기 있고, 없으면 같은 판단을 다시 내리느라 시간을 쓴다.
