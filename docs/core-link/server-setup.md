# core-link — cae00 사람 몫(받은 뒤 차례)

> 계약 [design.md](design.md) · 결정 [context-notes.md](context-notes.md) · 요청서 [request.md](request.md)의 BOX-10 ~ 16 을 이 박스에서 하는 차례다.
> 받은 편지함 글이 이 문서를 가리킨다. 실제 이름 · 주소 · 토큰은 여기 적지 않는다.

## 0. 받을 판

| 리포 | 무엇 | 확인 |
|---|---|---|
| 포털 | 박스 훅(SRC-12) · 서비스 토큰 탭(SRC-13) · StepForge 운영자 두 줄(SRC-15) · update-all 의 `STEPFORGE_SSO_*` 배선 | update-all 끝 요약의 박스 훅 ○ 줄 · 토큰 화면 '서비스 토큰' 탭(관리자) |
| 게이트웨이 | 쓰기 낱말 셋(SRC-14) · 서비스 신원(SRC-13) · StepForge 단언 쓰기(SRC-15) | `/health` 의 `service_jobs` · `rest_catalog` 의 step-forge `write_paths` |
| 에이전트 서버 | 쓰기 메서드의 `rest_call` 은 늘 확인 카드 · StepForge 운영자에게 `rest_call` 묶음 | 챗에서 StepForge 운영자로 적용을 청하면 카드가 선다 |
| StepForge · KooRemapper · SignalForge | 각 세션의 코어와 잇기 판 | 받은 편지함 글의 판 표 |

## 1. 업데이트(BOX-10)

1. update-all 을 돌린다. 심의 · 리스크 검토 · StepForge · DynaForge 잡이 0 일 때 돌린다.
2. 끝 요약을 본다.
   - `○ 박스 훅(update-all 끝)` 이 정상이다. 아직 훅이 없다.
   - `○ StepForge 단언 쓰기 …` 도 정상이다. 2절을 하기 전이다.
3. **tools-map 앞뒤 대조(SRC-14).**
   - update-all 앞에 `curl -s http://127.0.0.1:9110/tools-map > /tmp/tm-before.json` 을 떠 둔다.
   - 뒤에 다시 떠서 `routine_read` 에서 빠진 도구를 본다. 쓰기 낱말 `link` · `edit` · `sync` 가 새로 잡은 것이다.
   - 빠진 도구가 실제로 읽기라면 게이트웨이 `read_tools.local.json` 에 넣는다.
4. **운영자 동기화 미리 보기.** 허브 도구 가운데 새로 '목록 밖 쓰기' 로 짚힌 것을 본다(`link_sp_core` · `ontology_link` · `link_objects` ·
   `sync_sp_core` 등). 운영자 박스 덧씌우기 `infra/personas/he-team.local.json` 의 `writes` 나 `confirm` 에 넣는다. 정본 허브 · ODB 허브 ·
   ARP 처럼 이 박스에만 있는 앱의 운영자는 이 박스에서만 고친다.

## 2. StepForge 단언 쓰기 켜기(SRC-15 · SRC-07의 운반)

1. 비밀 하나를 만든다(`openssl rand -hex 32`). 리포 · 로그 · 채팅에 붙이지 않는다.
2. 같은 값을 두 곳에 적는다.
   - StepForge 데이터 폴더의 `secrets.env` 에 `STEPFORGE_SSO_SECRET=<값>` 줄을 둔다. 포털 신원 검증의 `STEPFORGE_GATEWAY_SECRET` 은 건드리지
     않는다 — 그 줄은 허브 `gateway_shared_secret` 과 같은 값이고, 넣으면 웹 화면의 포털 신원 요청마다 `X-Heax-Gateway-Secret` 을 요구한다.
     이 줄을 바꾸면 이미 낸 단언은 바로 무효가 된다(StepForge 는 같은 줄로 단언을 서명한다).
   - `HWAXMcpGateway/provision.env` 에 `STEPFORGE_SSO_SECRET=<값>` 을 적는다(600). 주소가 기본(`<HEAX_MCP_BASE>/apps/step_forge/api/auth/sso`)과
     다르면 `STEPFORGE_SSO_URL` 도 적는다.
3. update-all 을 다시 돌린다. §5 가 `StepForge 단언 쓰기 드리프트` 를 찍고 재프로비저닝한다. 끝 요약에서 ○ 가 사라졌는지 본다.
4. **확인.**
   - 게이트웨이 `rest_catalog` 의 step-forge 칸에 `write_paths` 다섯(`/api/onto-link` · `/api/onto-put` · `/api/onto-define` ·
     `/api/onto-fill` · `/api/plm-sync`)이 나오는지 본다.
   - 웹 챗에서 StepForge 운영자를 고르고 시험 과제에 온톨로지 선 하나를 미리 보게 한다(MCP, 쓰기 없음).
   - 이어서 적용을 청한다. 확인 카드가 서는지 본다(`rest_call` · site=step-forge · method=POST · path=/api/onto-link).
   - 승인하면 적용되는지, StepForge 기록의 행위자가 그 사람인지 본다.
   - 확인이 끝나면 그 선을 지운다.
5. **끄기.** 스위치가 없다. `provision.env` 에서 비밀을 지워도 게이트웨이는 직전 칸을 잇는다. 끄려면 게이트웨이 설정
   (`gateway_config.json`)의 `heax_registry.rest_sso.step_forge` 칸을 지우고 게이트웨이를 다시 띄운다(CK-12).

## 3. 서비스 토큰과 허용 목록(BOX-11, SRC-13)

1. 포털 토큰 화면에서 '서비스 토큰' 탭(관리자만 보인다)을 연다. 작업 이름 `core-link`, 수명(예: 90일), 메모를 넣고 발급한다. 토큰은 이때 한
   번만 보인다. 600 권한 파일 하나에 두고, 훅에서 그 파일을 읽는다.
2. 게이트웨이 리포 루트에 `service_tools.local.json` 을 둔다. git 이 모르는 박스 파일이다. 꼴은 이렇다.

   ```json
   {"jobs": {"core-link": {
       "tools": [],
       "rest":  [{"site": "step-forge", "method": "POST", "path": "/api/plm-sync"},
                 {"site": "step-forge", "method": "POST", "path": "/api/onto-link"},
                 {"site": "step-forge", "method": "POST", "path": "/api/onto-fill"}]}}}
   ```

   - StepForge 가 서비스 단언으로 받는 것은 이 셋뿐이다.
     - `plm-sync` — 허브 받기. `full: true` 까지 받는다. `allow_mass_absence: true` 는 403 이다 — 멈춘 받기를 넘기는 것은 사람이 정한다.
     - `onto-link` — 규칙 단만이다. 줄마다 `rule` 이 실린 link 와 규칙이 지은 선의 unlink 만 받는다.
     - `onto-fill` — 증명(proof) 규칙만이다.
   - 그 밖은 StepForge 가 `identity_refused: service_not_allowed`(403)로 막는다.
   - 앱 안 규칙 잇기(SRC-03 · 05)가 돌면 훅은 `plm-sync` 하나로 충분하다. 나머지 둘은 훅이 규칙 단 선을 바깥에서 직접 이을 때 쓴다.
   - RA · TestScope 도구와 신원을 넘기는 백엔드(심의)의 도구는 넣어도 버려진다(CK-11 · CK-13).
3. 게이트웨이 `/health` 의 `service_jobs` 에 `core-link` 와 도구 수가 나오는지 본다. 파일은 다시 띄우지 않아도 읽힌다(mtime).
4. 회수는 토큰 화면 목록에서 한다. 게이트웨이는 60초 안에 거절한다.

## 4. 대응표 · 미리 보기 · 적용(BOX-12 ~ 14)

- **정의 판 주의.** StepForge 의 새 관계(`has_role` · `maps_to`)는 씨앗 정의(`stepforge-core.json`)에 든다. 박스에 정의 판(`onto_def_editions`)이
  있어도 씨앗은 **키마다** 먹는다. 같은 이름의 사람 판이 이미 있을 때만 그 키가 막힌다 — 그때는 `ontology_model` 머리의 `seed_held`(무엇 ·
  까닭 · 할 일)가 말한다(StepForge 정정 11-09).
- **StepForge 거울이 코어 `part` 를 받는지.** 코드 기본값으로 받는다 — 배포 설정 `STEPFORGE_SP_TYPES` 가 비어 있으면 카탈로그의 열린 타입
  전부를 받는다. 이 줄을 따로 적어 두었다면 `part` 를 넣거나 줄을 지운다. 받는 조건은 둘이다.
  - 데이터 폴더 `secrets.env` 의 `STEPFORGE_SP_TOKEN`(core:read)이 `part` 타입을 볼 수 있어야 한다.
  - 받기 잡(`plm_sync`)이 한 번 돌아야 한다.

  확인은 받기 잡 결과의 타입 줄이나 `system_capabilities.plm_hub` 에 `part` 가 보이는지다.
- **BOX-12.** StepForge 부품 역할 16 → 코어 `part` 초안을 사용자가 본다. 이번 판부터 대응표는 박스에서 사람이 고친다. 사람 신원(웹 화면 ·
  챗의 사람 단언)의 `onto_link` 로 `maps_to` 선을 잇고 끊으면 사람 선이 코드의 YAML 값을 이긴다. 다음 판의 YAML 도 사람 선을 덮지 않는다. SignalForge 대응표 둘(부품 16 · 증상 32)도 같다. 초안은 받은 편지함
  2026-11-09 Q6 의 코어 어휘로 각 세션이 만든다.
- **SignalForge 대응표.** SignalForge 리포 `docs/DEPLOY_CAE00_2026-11-10-core-link.md` 를 따른다.
  - update-all 뒤 cron 의 `plm-sync.sh` 가 `/shared` 를 스스로 바인드해 코어 `part` · `failure_mode` 를 받고 대응표를 짓는다. 재기동은 없고,
    beat 로 받는 박스만 worker 를 재기동한다.
  - 먼저 `.env` 의 `SF_SP_CORE_TYPES` 가 셋으로 박혀 있지 않은지 본다(그 문서 1절).
  - 처음에는 `plm-sync.sh --full` 결과의 `core_link` 를 본다(2절).
  - 사람 선은 `scripts/core_link.py show · set · none · unset` 으로 넣는다(3절). 표는 리포가 아니라 `crawler/data/plm/core-link/` 에 있다.
- **BOX-13.** 플랫폼마다 `--dry-run`(SRC-03 · 05 · 08 · 09)으로 이을 수 · 후보 수 · 못 붙인 수를 표로 만들어 사용자에게 보인다.
- **BOX-14.** 확인한 것만 적용한다. 쓰기 전에 그 앱 DB 를 따로 백업하고 개수가 0 이 아닌지 본다.
- **Q-3(사용자 결정).** 정확 일치 규칙 잇기는 과제 28 개 모두에 돈다. 사람이 고르는 개정 이름 · 앞 판은 운영자 자신의 과제만 정하고, 남의
  과제는 미리 보기 표를 주인에게 보낸다.
- **Q-4(사용자 결정).** 두 인스턴스를 같은 때에 한다. 운영 사본(`stepforge-prod` · `dynaforge-prod`)은 이 박스 update-all 범위 밖이다. 새 판을
  넣는 길은 받은 편지함 2026-11-09 Q7 의 답을 따른다. 서비스 신원 · 박스 훅 · 챗의 REST 단언 쓰기는 이 박스 허브 인스턴스에만 걸린다(CK-9).

## 5. 박스 훅(BOX-15, SRC-12)

1. `infra/hooks/post-update.d/50-core-link.local.sh` 를 둔다(600). 폴더 README 가 규칙이다 — 이름은 `.local.sh` 로 끝나고, 실패는
   종료코드에 들지 않는다.
2. 앱 안 규칙 잇기(SRC-03 · 04 · 05)가 돌면 훅은 StepForge 허브 받기를 한 번 걸고 결과를 요약하면 된다. 예시는 이렇다. 서비스 토큰은
   600 파일에 두고, 게이트웨이 venv 의 MCP 클라이언트로 `rest_call` 을 부른다(`infra/scripts/mcp-smoke.py` 와 같은 클라이언트).

   ```bash
   #!/usr/bin/env bash
   # 코어와 잇기 — StepForge 허브 받기를 걸고 요약 한 줄(서비스 토큰 core-link · docs/core-link server-setup 5절)
   set -uo pipefail
   GW="$(cd ../HWAXMcpGateway && pwd)"
   TOKEN_FILE="$HOME/.config/hwax/core-link.token"          # 600 — 포털 토큰 화면 '서비스 토큰' 에서 받은 값
   "$GW/.venv/bin/python" - "$TOKEN_FILE" <<'PY'
   import asyncio, sys
   from mcp.client.session import ClientSession
   from mcp.client.streamable_http import streamablehttp_client
   tok = open(sys.argv[1], encoding="utf-8").read().strip()
   async def main() -> int:
       async with streamablehttp_client("http://127.0.0.1:9110/mcp", headers={"Authorization": f"Bearer {tok}"}) as (r, w, _):
           async with ClientSession(r, w) as s:
               await s.initialize()
               res = await s.call_tool("rest_call", {"site": "step-forge", "method": "POST", "path": "/api/plm-sync",
                                                     "body": {"full": False}})
               print("  · core-link 훅 —", "".join(getattr(c, "text", "") for c in res.content)[:400])
               return 1 if res.isError else 0
   sys.exit(asyncio.run(main()))
   PY
   ```

   - 받기가 멈췄으면(held — 절반 넘게 한꺼번에 사라짐) 결과의 `problems` 가 요약 줄에 나온다. 넘길지는 사람이 허브를 보고 정한다
     (`allow_mass_absence` 는 서비스 토큰으로 못 넘긴다).
   - 응답이 실패면 훅이 1 로 끝나 끝 요약의 박스 훅 줄에 실패로 나온다(종료코드에는 들지 않는다).
3. 바쁠 때는 건너뛰려면 `./infra/scripts/update-all.sh --hooks-when-idle` 로 돌린다.

## 6. 확인(BOX-16)

플랫폼마다 남긴다 — ④ 선 수 · 후보 수, 그리고 `onto_path`(파트 → 역할 → 코어 부품) 한 줄이다.

## 7. 되돌리기

| 무엇 | 어떻게 |
|---|---|
| 박스 훅 | 그 `.local.sh` 를 지우거나 이름을 바꾼다(다음 update-all 이 ○ 로 알린다) |
| 서비스 토큰 | 토큰 화면에서 회수 · `service_tools.local.json` 에서 그 작업을 지운다 |
| StepForge 단언 쓰기 | 2-5 의 끄기 |
| 쓰기 낱말(SRC-14) | 읽기로 다룰 도구를 `read_tools.local.json` 에 넣는다(코드 되돌리기 없이) |
