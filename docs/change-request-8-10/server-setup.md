# 서버(cae00)에서 할 일 — 심의 엔진 변경 · 8·9·10차 변경 요청 · 시간 제한

> 대상: cae00 운영자 · **대조 시점 2026-10-08** · 보낸 쪽: dev(이 리포 `docs/change-request-8-10/` · `docs/delib-engine-feedback/`)
> 반영된 커밋 — 포털 `de60672`(코드 기준 — 그 뒤는 문서 커밋뿐이다) · 게이트웨이 `f6a4fe0` · 에이전트서버 `7683125` · AIDataHub `9eb744d` · HWAXRisk `7248651` · HEAXHub `091be05`.
> 두 묶음이 update-all 한 번에 같이 온다 — 8·9·10차 변경 요청과 심의 엔진 변경, 그리고 뒤이어 올라온 「시간 제한을 넉넉하게」(긴 심의·리스크 심사 경로의 시간 제한을 층으로 맞췄다 — §4-8, 결정은 `docs/delib-engine-feedback/context-notes.md` D-17).
> 코드는 전부 원격에 올라가 있다. 아래는 **박스마다 다른 값**이라 사람이 넣거나 확인하는 것이다(비밀·사내 주소는 리포에 적지 않는다).
> 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 근거는 줄번호가 아니라 **출력 문구**로 가리킨다.
> 출력의 표식 — `✗` 만 종료코드를 세운다 · `⚠` 는 경고 · `○` 는 설정이 없어 안 켠 기능(실패가 아니다) · `·` 는 진행 줄이다.
> 이 박스의 지금 상태는 이 문서가 알지 못한다. 그래서 확인마다 재는 명령을 적었다.
> `docs/cae00-deploy-guide.md` 의 「2026-09-27 반영분」 가운데 ARP 문단(1f 가 `systems.local.yaml` 의 `arp` 를 적는다 · 타일은 직결 링크)은 이 문서로 대체된다.

## 0. 순서 한눈에

| 단계 | 무엇 |
|---|---|
| 1 | 실행 전 확인 열둘(§1) — 걸리는 것이 있으면 그 칸대로 한 뒤에 넘어간다 |
| 2 | `./infra/scripts/update-all.sh` 한 번(§2) |
| 3 | 실행 뒤 확인(§3) |
| 4 | 쓰려는 기능만 설정(§4) — 안 넣어도 종전대로 돈다(ARP 타일만 예외다. §1 확인 6). 시간 제한의 층과 손잡이는 §4-8 이다 |

## 1. 실행 전에 확인할 것

전부 update-all 을 돌리기 **전에** 본다. 명령은 §1-1 에 번호대로 있다.

| # | 확인 | 방법 | 아니면(할 일) |
|---|---|---|---|
| 1 | 게이트웨이 작업트리의 `tool_areas.json` 수정을 걷었나 | 게이트웨이 리포에서 `git status --short tool_areas.json` 이 비어 있다 | 수정본을 다른 곳에 복사해 두고 `git checkout -- tool_areas.json`. `quality` 영역·`plm-defect`·`knox-bridge` 는 이제 추적 파일에 들어 있다. 안 걷으면 게이트웨이만 옛 코드로 남는다(§2 의 `갱신(git pull) 실패` 행) |
| 2 | 게이트웨이 설정에 `portal-admin` 을 거는 백엔드가 없나 | 명령 2 가 `[]` 를 찍는다(백엔드 이름만 나온다) | 이름이 나오면 반영을 멈추고 dev 에 알린다. 게이트웨이는 이제 토큰에 박힌 `portal-admin` 을 하위로 넘기지 않는다 |
| 3 | 이미 있는 `backend/config/access.local.yaml` 이 읽히나 | 명령 3. 파일이 없으면 아무것도 안 찍히고(정상) 있으면 `OK` 한 줄이다 | `OK` 가 아니면 고친 뒤 반영한다(오류 줄은 행 번호나 사유만 말하고 내용은 찍지 않는다). 이 파일은 이번 판부터 읽힌다 — 깨진 채 반영하면 포털은 뜨는데 요청이 전부 실패한다. 내용까지 보는 확인은 반영 뒤 §4-3 에 있다 |
| 4 | SmartTwinMCP(해석 잡 제출 도구)를 쓰는 박스면 주소가 설정돼 있나 | 명령 4. 첫 줄이 `1` 이면 설정돼 있다. `0` 이면 둘째 줄을 본다 — `000` 이면 그 포트를 듣는 것이 없다(안 쓰는 박스) | 첫 줄이 `0` 인데 둘째 줄이 `000` 이 아니면, 실행 전에 게이트웨이 `provision.env` 에 `SMARTTWIN_MCP_URL=http://127.0.0.1:5013/mcp` 를 적는다. 안 적으면 첫 재프로비저닝에서 그 도구들이 빠진다(뒤늦게 적으면 그다음 update-all 에 돌아온다) |
| 5 | ARP 주소가 설정 파일에 있나 | 명령 5 의 세 줄을 §1-2 표에 대어 본다 | 주소가 `gateway_config.json` 에만 있으면 실행 전에 `infra/.env` 에 `ARP_HOST` 를 적는다(§1-2 셋째 줄). 안 적으면 재프로비저닝이 도는 순간 arp 항목이 주소째 사라진다 |
| 6 | ARP 쪽이 타일 로그인을 받을 준비가 됐나 | ARP 담당에게 묻는다(ARP 서버의 `.env` 는 이 박스에서 볼 수 없다). `ARP_PORTAL_AUDIENCE` 가 글자 그대로 `aireadyportal` 이고 포털 JWKS·ISSUER 설정이 켜져 있어야 한다. 이 박스의 라우트 줄은 명령 6 으로 본다(`1` 이면 있다) | **준비 전이면** 라우트 줄을 적지 않는다(있으면 `#` 로 막는다). 타일이 숨고 토큰이 나가지 않으며 나머지는 그대로 반영된다. **준비됐으면** `backend/config/routes.local.env` 에 `aireadyportal=http://<ARP 서버>:<포트>/` 를 적는다(`ARP_HOST` 와 같은 서버 · 포트 기본 3001 · 끝의 `/` 까지). 이 줄이 있는 채 포털이 다시 뜨는 순간부터 타일 클릭이 `/aireadyportal/api/auth/portal-callback` 으로 로그인 토큰을 보낸다. ⚠ 어느 쪽이든 종전의 직결 타일은 이번 반영으로 사라진다 — 그동안 직결 링크가 필요하면 §4-4 의 임시 타일을 쓴다 |
| 7 | 반영 뒤에도 관리자가 있게 고정 관리자를 적었나 | 명령 7 이 `1` 을 찍는다. 관리자는 이제 원장(포털 사용자 DB)의 관리자 표지와 `PORTAL_ADMIN_EMAILS` 만 본다 — 로그인 값·토큰의 `portal-admin` 은 더는 관리자를 만들지 않는다 | 실행 **전에** `infra/.env` 에 `PORTAL_ADMIN_EMAILS=<운영자 로그인 이메일>` 을 적는다(적는 꼴 §1-3, 주의 §4-1). update-all 이 포털을 새로 띄우며 읽으므로 관리자 없는 구간이 생기지 않는다 |
| 8 | 옛 토큰이 권한을 잃지 않나 | 토큰에 `portal-admin` 이 박혀 있으면 지금까지는 포털이 그 주인을 관리자로 보아 권한을 전부 내줬다. 이제는 원장만 본다. 박스에 있는 서비스 토큰은 명령 8 로 주인과 표지를 본다. 개인 Claude 토큰은 이 박스에서 볼 수 없다 — mock 로그인 시절에 발급한 토큰이 해당한다 | `portal-admin 박힘: True` 인 토큰의 주인을 사용자 관리에서 찾는다. 소속이 비어 있으면 실행 전에 소속을 준다(재기동 불필요). 원장에 그 계정이 없으면 지금 쓰는 계정으로 토큰을 새로 발급해 갈아 끼운다. 안 하면 반영 직후 그 토큰으로는 도구가 일반 챗 수준으로 줄어든다 |
| 9 | 에이전트서버 `.env` 에 옛 심의 호출 한도가 남아 있지 않나 | 명령 9 에 `DELIB_TIMEOUT_S` 줄이 없거나 그 값이 1800 이상이다. 옛 환경 키트가 이 값을 600 으로 심었고, 키트는 없는 키만 더하므로 그 줄은 스스로 바뀌지 않는다 | 1800 보다 작으면 실행 **전에** 그 줄을 지운다(일부러 정한 값이면 1800 이상으로 올려 적는다). 안 지우면 넉넉해진 기본값(시도당 1800초)이 이 박스에만 안 먹는다 — 좌석이 많은 심의에서 좌석이 그 값에 걸려 빠지고, update-all 은 실행마다 §2 의 `⚠ agent-server .env 의 DELIB_TIMEOUT_S=…` 만 찍는다. 줄이 없던 박스는 종전에 심의 호출이 `LLM_TIMEOUT_S` 를 따랐고 그것도 없으면 한도가 없었다 — 이제는 시도당 1800초에 재시도 1회다(이번 실행이 `DELIB_TIMEOUT_S=1800` 을 적어 넣는다). `LLM_TIMEOUT_S` 는 더는 심의에 걸리지 않는다(챗 전용이고 안 적으면 900초다) |
| 10 | 절차에 선언한 상한보다 오래 걸린 단계가 없나 | 명령 10 이 `0건` 을 찍는다(원장 파일이 없는 박스는 `절차 원장이 없다` — 볼 것이 없다). 줄이 나오면 그 단계가 `fast` 는 30초, `slow` 는 110초를 넘긴 적이 있다 | 나온 줄을 dev(그 절차를 만든 쪽)에 보내, 그 단계를 `expect: slow` 로 고친 판을 다시 들인다(화면에는 이 칸이 없다). 단계 상한이 이번 판부터 정말 걸린다 — 안 고치면 종전에 늦게 성공하던 `fast` 단계가 30초에 `unknown`(`30초 안에 응답이 없다 — 실행 여부를 모른다`)으로 멈추고, 쓰기 단계면 사람이 확인해야 재개된다. 110초를 넘기는 도구는 단계 하나로 둘 수 없다(제출과 회수 두 절차로 가른다) |
| 11 | 포털 대화 저장소가 로컬 디스크에 있나 | 명령 11 이 `ext4`·`xfs` 같은 로컬 파일시스템 이름을 찍는다 | `nfs`·`nfs4`·`cifs`·`lustre`·`gpfs` 가 나오면 반영을 멈추고 dev 에 알린다. 새 판은 첫 기동에 이 DB 를 WAL 방식으로 바꾸는데(옆에 `-wal`·`-shm` 파일이 생긴다) 네트워크 파일시스템에서는 DB 가 깨질 수 있다. 끄는 설정은 없다 |
| 12 | 도는·줄 선 심의가 없나(맨 나중에 본다) | 명령 12 의 첫 명령이 찍는 두 줄(`delib_active`·`delib_queued`)의 수가 다 0 이다(웹 심의·리스크 패널·MCP 심의를 함께 센다). **아무 줄도 안 나오면 떠 있는 에이전트서버가 옛 판이다** — 둘째 명령이 `0` 을 찍는지 보고(MCP 로 시작한 심의만 센다) 웹 화면과 리스크 심사를 쓰는 사람들에게 시각을 알린다 | 끝날 때까지 기다린다. **이번 첫 실행에는 보호가 없다** — 떠 있는 에이전트서버가 옛 판이면 update-all 이 심의 수를 묻지 못해 종전대로 포털·nginx·에이전트서버를 내린다(§2 의 `· agent-server: /health 가 도는 심의 수(…)를 싣지 않는다(옛 판)` 줄). 돌던 심의는 끊겨 처음부터 다시 돌려야 한다. 새 판이 한 번 뜬 뒤부터는 심의가 있으면 update-all 이 그 재기동을 스스로 미루고 `○` 로 남긴다(§2). 게이트웨이와 HEAX Hub 의 앱은 그 보호 밖이다(§6) |

AIDataHub 와 hwax-risk 쪽은 실행 전에 할 일이 없다 — 새 시간 한도가 전부 코드 기본값으로 돈다(§4-8).

### 1-1. 확인에 쓰는 명령

`grep -c` 가 파일이 없다고 하면 `0` 과 같다.

```bash
# 명령 2 — 게이트웨이 리포 루트에서. 백엔드 이름만 나온다
python3 -c "import json;c=json.load(open('gateway_config.json'));print([k for k,v in c.items() if isinstance(v,dict) and 'portal-admin' in (v.get('allowed_groups') or [])])"

# 명령 3 — 포털 리포 루트에서. 파일이 없으면 무출력, 있으면 OK(내용은 찍지 않는다)
PY=backend/.venv/bin/python; [ -x "$PY" ] || PY=python3
[ -f backend/config/access.local.yaml ] && "$PY" -c 'import sys,yaml; d=yaml.safe_load(open(sys.argv[1],encoding="utf-8")) or {}; assert isinstance(d,dict) and all(isinstance(p,dict) and p.get("id") for p in d.get("platforms") or []), "맨 위가 매핑이 아니거나 id 없는 플랫폼 항목이 있다"; print("OK")' backend/config/access.local.yaml 2>&1 | tail -1

# 명령 4 — 게이트웨이 리포 루트에서. 첫 줄 = 설정된 줄 수, 둘째 줄 = 기본 주소의 응답 코드
grep -cE '^[[:space:]]*(export[[:space:]]+)?SMARTTWIN_MCP_URL=[^[:space:]#]' provision.env
curl -s -o /dev/null -m 3 -w '%{http_code}\n' http://127.0.0.1:5013/mcp

# 명령 5 — 수와 True/False 만 찍힌다(주소는 안 찍힌다)
grep -cE '^[[:space:]]*(export[[:space:]]+)?ARP_HOST=[^[:space:]#]' infra/.env      # 포털 리포 루트에서
grep -cE '^[[:space:]]*(export[[:space:]]+)?ARP_BASE=[^[:space:]#]' provision.env    # 게이트웨이 리포 루트에서
python3 -c "import json;print('arp' in json.load(open('gateway_config.json')))"      # 게이트웨이 리포 루트에서

# 명령 6 — 포털 리포 루트에서. 라우트 줄이 있으면 1(# 로 막은 줄은 세지 않는다)
grep -cE '^[[:space:]]*aireadyportal[[:space:]]*=[[:space:]]*[^[:space:]]' backend/config/routes.local.env

# 명령 7 — 포털 리포 루트에서
grep -cE '^[[:space:]]*(export[[:space:]]+)?PORTAL_ADMIN_EMAILS=[^[:space:]#]' infra/.env

# 명령 8 — 포털 리포 루트에서. 토큰이 든 파일과 키 이름을 준다(아래는 HWAXRisk 의 예 — 경로·키를 바꿔 다른 토큰도 본다).
#          주인 이메일과 표지 유무만 찍고 토큰은 찍지 않는다
python3 - ../HEAXHub/var/app_data/hwax_risk/secrets.env HWAXRISK_PORTAL_PAT <<'PY'
import base64, json, sys
for ln in open(sys.argv[1], encoding="utf-8"):
    k, _, v = ln.strip().partition("=")
    if k.replace("export", "").strip() != sys.argv[2]: continue
    p = v.strip().strip("\"'").split(".")
    if len(p) != 3: print("JWT 모양이 아니다"); continue
    c = json.loads(base64.urlsafe_b64decode(p[1] + "=" * (-len(p[1]) % 4)))
    print(c.get("email"), "· portal-admin 박힘:", "portal-admin" in (c.get("groups") or []))
PY

# 명령 9 — 에이전트서버 리포 루트에서. 줄이 없으면 무출력이다(초만 찍힌다 — 비밀이 아니다). 같은 키가 두 줄이면 아래 줄이 이긴다
grep -nE '^(DELIB_TIMEOUT_S|LLM_TIMEOUT_S)=' .env

# 명령 10 — 포털 리포 루트에서(포털이 떠 있는 채로). 선언한 상한(fast 30초 · slow 110초)보다 오래 걸린 단계와 건수
#           (PROCEDURES_STORE_PATH 를 따로 적은 박스는 realpath 자리에 그 경로를 넣는다)
python3 - "$(realpath backend/data/procedures.sqlite)" <<'PY'
import os, sqlite3, sys
if not os.path.exists(sys.argv[1]): sys.exit("절차 원장이 없다")
q = """SELECT COALESCE(p.title, '(저장하지 않은 실행)'), s.ix, s.backend, s.tool, COALESCE(s.expect, 'fast'),
              MAX(s.duration_ms) / 1000, COUNT(*)
         FROM run_steps s JOIN runs r ON r.id = s.run_id
         LEFT JOIN procedure_versions v ON v.version_id = r.procedure_version_id
         LEFT JOIN procedures p ON p.id = v.procedure_id
        WHERE s.duration_ms > CASE COALESCE(s.expect, 'fast') WHEN 'fast' THEN 30000 ELSE 110000 END
        GROUP BY 1, 2, 3, 4, 5 ORDER BY 6 DESC"""
rows = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True).execute(q).fetchall()
for title, ix, backend, tool, expect, sec, n in rows:
    print(f"{title} · 단계 {ix} · {backend}.{tool} · {expect} · 최장 {sec}초 · {n}회")
print(f"{len(rows)}건")
PY

# 명령 11 — 포털 리포 루트에서. 대화 저장소가 놓인 파일시스템 종류(CONV_STORE_PATH 를 따로 적은 박스는 그 경로를 넣어 본다)
df -PT "$(dirname "$(realpath backend/data/conversations.sqlite)")" | awk 'NR==2 {print $2}'

# 명령 12 — 도는·줄 선 심의 수. 새 판이면 delib_active · delib_queued 두 줄이 나온다
curl -s --noproxy '*' -m 5 http://127.0.0.1:9009/health | grep -oE '"delib_(active|queued)": *[0-9]+'
#          아무 줄도 안 나오면 옛 판이다 — 에이전트서버 리포 루트에서 MCP 로 시작한 것만 센다
#          (잡 기록을 DELIB_JOB_DIR 로 옮긴 박스는 그 디렉터리의 *.json 을 센다)
grep -lE '"status": "(running|queued)"' "$(dirname "$(realpath artifacts)")"/delib-jobs/*.json 2>/dev/null | wc -l
```

Claude 가 붙어 있으면 명령 12 의 둘째 명령 대신 `deliberate_list` 의 `running`·`queued` 수로 봐도 된다(이것도 MCP 로 시작한 심의만 센다).

### 1-2. ARP 주소가 어디 있느냐에 따라 일어나는 일(확인 5)

| 명령 5 의 결과 | 이번 실행에서 일어나는 일 | 실행 전에 할 일 |
|---|---|---|
| 첫 줄이 `1` — `infra/.env` 에 `ARP_HOST` | 1f 가 게이트웨이 `provision.env` 에 `ARP_BASE` 를 적는다. 토큰 없이 등재된 옛 `arp` 항목은 걷히고(`· 옛 항목 걷어내기: arp`) 주소는 설정 파일에 남는다. 타일 라우트가 없거나 다른 서버를 가리키면 경고한다 | 없음 |
| 첫 줄 `0` · 둘째 줄 `1` — `provision.env` 에 `ARP_BASE` 만 | 옛 `arp` 항목은 걷히고 주소는 남는다. 1f 는 건너뛴다(`○ AI Ready Portal 주소 묶기`) — 타일 라우트 점검이 없다 | 없음. `ARP_HOST` 로 옮겨 적으면 라우트 점검까지 받는다 |
| 둘 다 `0` · 셋째 줄 `True` — 주소가 `gateway_config.json` 에만 | 옛 항목을 남긴다(`· 옛 항목 arp(토큰 없이 등재)는 걷어내지 않는다`). 그러나 다른 까닭으로 재프로비저닝이 돌면(기본 주소의 `smart-twin-mcp` 를 걷을 때가 그렇다) 토큰 없는 arp 항목이 **주소째** 사라진다 | `infra/.env` 에 `ARP_HOST=<ARP 서버 주소>` 를 적는다(포트가 3001 이 아니면 `ARP_PORT` 도). 주소는 게이트웨이 리포에서 `python3 -c "import json;print(json.load(open('gateway_config.json'))['arp']['url'])"` 로 본다 — 화면에서만 보고 밖에 붙이지 않는다 |
| 셋 다 없음 — ARP 를 붙이지 않은 박스 | 아무 일도 없다 | 없음 |

### 1-3. `infra/.env` 를 고칠 때(§1·§4-1 공통)

⚠ 이 파일은 스크립트들이 `set -e` 아래에서 bash 로 그대로 읽는다. 한 줄이 틀리면 그 파일을 읽는 스크립트(포털 기동·정지·nginx 생성·Drive 반입)가 그 줄에서 멈춘다.

- 쉼표 목록은 붙여 쓴다 — `KEY=a@corp.example,b@corp.example`. 쉼표 뒤에 공백을 두면 `command not found` 로 멈춘다.
- update-all 이 붙인 주석 줄(`# KEY=<…>   # ⚠ 값을 운영자가 정해야 한다…`)은 주석 기호만 지우지 않는다. `KEY=값` 한 줄로 새로 적는다 — `<…>` 자리표시자가 남으면 `syntax error near unexpected token` 으로 멈춘다.
- 값 줄에는 값만 둔다. 줄 끝에 설명을 달지 않고, 호스트 값(`ARP_HOST`·`RA_HOST`)은 스킴·포트 없이 주소만 적는다.
- 고친 뒤 곧바로 아래를 돌린다. `ok` 가 나와야 한다.

```bash
# 포털 리포 루트에서
bash -c 'set -euo pipefail; set -a; . ./infra/.env; echo ok'
```

`ok` 가 아니면 오류가 가리키는 줄을 고친다. 고치기 전에는 포털을 손으로 내리지 않는다 — update-all 은 이 오류에서 포털을 내리기 전에 멈추지만(`⚠ skip: portal failed (see above)`), 손으로 내린 포털은 다시 뜨지 않는다.

## 2. update-all 한 번 — 이번에 새로 보이는 줄

포털 리포 루트에서 `./infra/scripts/update-all.sh` 를 돌린다. 받기와 재기동을 한 실행에서 하므로 도중에 끊지 않는다(끊겼으면 다시 돌린다).
아래 줄은 조건이 맞을 때만 나온다 — 안 나오는 것은 실패가 아니다. 표는 나오는 순서다.
새 에이전트서버가 뜬 뒤의 실행은 심의가 돌거나 줄 서 있으면 포털·nginx·에이전트서버 재기동과 게이트웨이 재프로비저닝을 미루고 `○ … 건너뜀` 으로 남긴다(끝의 `○ 있는데 안 켠 것` 요약에도 다시 실린다). 그 줄이 있는 실행은 반영이 끝난 것이 아니다 — 심의가 끝난 뒤 한 번 더 돌린다.

| 출력 | 뜻 | 할 일 |
|---|---|---|
| `⚠ <키> — 값을 정해야 한다`(1c) 와 `infra/.env` 끝의 `# ── env-sync … ──` 아래 주석 줄 | 새 설정 키(§4-1 의 넷 가운데 아직 없던 것)가 주석으로 붙었다. 실패가 아니다 | 쓸 것만 §4-1. 적는 꼴은 §1-3 |
| `· <키> — 선택 설정(예시로만 적혀 있다)` 여섯 줄(1c)과 그 끝의 `⚠ 위 ⚠ 항목은 **주석으로** 넣었다 — 값을 채우고 …` | 포털의 시간 제한 손잡이 여섯(`AGENT_STREAM_IDLE_TIMEOUT_S` · `AGENT_UNARY_TIMEOUT_S` · `CHAT_PAT_TTL_S` · `CONV_STORE_BUSY_TIMEOUT_S` · `NGINX_AGENT_READ_TIMEOUT` · `NGINX_MCP_READ_TIMEOUT`)이 `infra/.env` 끝에 주석으로 붙었다. 실패가 아니다 | 없음. 주석에 적힌 값이 코드 기본값이다 — 채우지 않아도 그 값으로 돈다(§4-8) |
| `○ AI Ready Portal 주소 묶기` | `infra/.env` 에 `ARP_HOST` 가 없어 1f 를 건너뛰었다. 타일 라우트도 보지 않는다 | §1-2 에서 이 박스의 줄을 다시 본다 |
| `⚠ ARP 타일 라우트가 없다` | `ARP_HOST` 는 있는데 `aireadyportal=` 라우트가 없다. 타일이 숨는다 | 일부러 뺀 동안은 정상이다(§1 확인 6). 켤 때 적는다 |
| `⚠ ARP 주소가 두 곳에서 다르다` | `infra/.env` 의 `ARP_HOST` 와 라우트 파일의 `aireadyportal=` 이 다른 서버다(경고라 종료코드는 그대로다) | 둘을 같은 서버로 맞추고 다시 돌린다 |
| `· NO_PROXY 에 내부 목적지를 더했다: RA_HOST ARP_HOST` | 두 설정의 주소를 이 실행의 `NO_PROXY` 에 더했다(주소가 아니라 설정 이름이 찍힌다). 운영자 셸의 `NO_PROXY` 에 이미 있으면 이 줄은 안 나온다 | 없음 |
| `○ 포털·nginx 재기동 건너뜀 — 심의 N건 진행 중, M건 대기 — …` | 도는·줄 선 심의가 있어 포털을 내리지 않았다. 새 이미지와 `frontend/dist` 도 받지 않았다(리포의 코드만 당겨졌고 포털은 옛 프로세스다). 실패가 아니고 종료코드도 그대로다. 심의가 도는 동안에는 실행마다 나온다 | 심의가 끝난 뒤 update-all 을 다시 돌린다. 지금 끊어도 되면 `AGENT_RESTART_FORCE=1 ./infra/scripts/update-all.sh` — 웹 심의와 리스크 패널의 구독, 도는·줄 선 심의가 전부 끊긴다 |
| `⚠ portal not ready in 30s` 와 그 아래 로그 끝의 `database is locked`, 이어서 `⚠ skip: portal failed (see above)` | 새 판은 첫 기동에 원장에 부서 코드·사번 칸을 더한다. 그 순간 잠금에 걸렸다 | update-all 을 한 번 더 돌린다. 포털이 다시 뜨면서 스스로 낫는다 |
| `○ nginx 재기동 건너뜀 — 심의 N건 진행 중, M건 대기 — …` | 새 라우팅 conf 는 만들었지만 nginx 는 옛 conf 로 돈다(리스크 앱이 nginx 를 거쳐 포털에 붙어 있다) | 위 `○ 포털·nginx 재기동 건너뜀` 과 같다 |
| `✗ NGINX_AGENT_READ_TIMEOUT 값('…')을 쓰지 않는다` 또는 `⚠ NGINX_AGENT_READ_TIMEOUT(…)이 포털의 AGENT_STREAM_IDLE_TIMEOUT_S(…초)보다 크지 않다`(포털 기동 출력이나 `✓ nginx reloaded with current routes` 아래) | `infra/.env` 에 적은 nginx 침묵 한도가 모양이 틀려 기본값으로 만들었거나(이 `✗` 는 종료코드를 세우지 않는다), 포털 쪽 한도보다 크지 않아 순서가 뒤집혔다 | §4-8 대로 고쳐 적고 반영한다. 안 적은 박스에는 안 나온다 |
| `⚠ agent-server .env 의 DELIB_TIMEOUT_S=<값> 는 권장값(1800초)보다 짧다`(3.5) | §1 확인 9 를 놓쳤다. 에이전트서버는 그 짧은 값으로 돈다 | 그 줄을 지우고 `./infra/scripts/update-sites.sh agent-server`. 고치기 전에는 실행마다 나오고 끝의 경고 요약에도 실린다 |
| `· agent-server: /health 가 도는 심의 수(delib_active·delib_queued)를 싣지 않는다(옛 판) — 묻지 못하고 재기동한다` | 떠 있던 에이전트서버가 옛 판이라 심의 보호가 걸리지 않았다. 이번 첫 실행에서는 정상이다(§1 확인 12) | 없음. 다음 실행에도 나오면 agent-server 의 `갱신(git pull) 실패` 를 찾는다 |
| `○ agent-server 재기동 건너뜀 — 심의 N건 진행 중, M건 대기 — …` 와 `▶ ○ 재기동 미룸(심의가 돌거나 줄 서 있다): agent-server` | 에이전트서버의 새 코드·설정이 아직 반영되지 않았다(옛 프로세스가 돈다). 실패가 아니다 | 위 `○ 포털·nginx 재기동 건너뜀` 과 같다. 에이전트서버만이면 끝난 뒤 `./infra/scripts/update-sites.sh agent-server` |
| `· agent-server: /health 가 연속으로 4초 안에 답하지 않았다(듣고는 있다 — 매달린 것으로 본다). 도는 심의 수를 확인하지 못한 채 재기동한다` | 에이전트서버가 답을 못 해 다시 띄웠다. 돌던 심의가 있었다면 끊겼다 | 쓰는 사람들에게 알린다(끊긴 MCP 심의는 `interrupted` 로 남는다) |
| `▶ ⚠ 갱신(git pull) 실패: <서비스>` 와 `✗ update-sites 실패` | 그 서비스는 옛 코드로 돈다(게이트웨이면 §1 확인 1 을 놓친 것이다) | 그 리포에서 `git status --short` 로 로컬 수정을 찾아 걷고 다시 돌린다 |
| `○ ARP MCP 도구(챗의 AI Ready Portal)` | ARP 주소는 있는데 `ARP_TOKEN` 이 없어 arp 백엔드를 등재하지 않았다 | 토큰을 받으면 §4-2 |
| 같은 `○ ARP MCP 도구(챗의 AI Ready Portal)` 인데 사유가 `ARP_TOKEN 은 있는데 update-all 이 아는 ARP 주소가 없다` | 토큰은 적었는데 ARP 주소가 설정 파일에 없다. update-all 이 arp 를 기대하지 않아, 빠져 있어도 토큰을 바꿔도 재프로비저닝이 돌지 않는다 | `infra/.env` 에 `ARP_HOST` 를 적고 다시 돌린다(§1-2 셋째 줄) |
| `○ ODB 자동화 허브 MCP 도구` — `ODB_HUB_TOKEN 은 있는데 허브 주소를 모른다` | 허브 주소가 게이트웨이 `provision.env` 에도 지금 게이트웨이 설정에도 없어 odb-hub 를 등재하지 않는다(게이트웨이 코드에 박혀 있던 기본 주소를 걷었다). 이미 붙어 있는 박스는 설정이 주소를 알고 있어 안 나온다 | 게이트웨이 `provision.env` 에 `ODB_HUB_BASE=http://<ODB 자동화 허브 서버>:<포트>` 를 적고 다시 돌린다 |
| `○ SmartTwinMCP 도구(해석 잡 제출·후처리)` | SmartTwinMCP 주소가 설정돼 있지 않다 | 쓰는 박스라면 §1 확인 4 를 놓친 것이다. 주소를 적고 다시 돌린다 |
| `○ Knox 브리지 MCP 도구(챗의 메일·메신저)` | Knox 브리지 리포·설정이 없는 박스다 | 없음 |
| `✗ knox-bridge 백엔드가 게이트웨이 config 에 없다` | 브리지는 있는데 게이트웨이 설정에서 그 키가 빠졌다. 재프로비저닝으로는 되살아나지 않는다 | 게이트웨이 리포의 `gateway_config.json.bak.<날짜>`(또는 HWAXKnoxBridge 리포의 안내)에서 `knox-bridge` 블록을 `gateway_config.json` 에 옮기고 `./infra/scripts/update-sites.sh mcp-gateway` |
| `· 옛 항목 걷어내기: …` 뒤 재프로비저닝(그 출력의 `⚠ arp 생략 — …` · `⚠ smart-twin-mcp 생략 — …` 는 걷는 과정의 줄이다) | 토큰 없이 등재된 `arp`(ARP 주소를 아는 박스에서만), 기본 주소의 `smart-twin-mcp`(그 주소를 듣는 것이 없을 때만)를 게이트웨이 설정에서 뺀다 | 없음. `✓ 재프로비저닝으로 백엔드 정합 완료` 로 끝나야 한다. 이때 게이트웨이·에이전트서버가 한 번 더 뜬다. 다음 실행부터는 이 줄이 안 나와야 한다 |
| `· 옛 항목 arp(토큰 없이 등재)는 걷어내지 않는다` | ARP 주소가 게이트웨이 설정에만 있어 남겨 두었다(§1-2 셋째 줄). arp 의 가짜 DOWN 은 그대로다 | `infra/.env` 에 `ARP_HOST` 를 적고 다시 돌린다. 적기 전에는 매 실행 나온다 |
| `· 사람별 위임 끄기: <앱 키> — HWAXMcpGateway/provision.env 에서 그 앱의 비밀을 비웠거나 PER_USER_SSO_APPS 에서 뺐는데 게이트웨이는 아직 위임으로 부른다` | 일반 앱(§4-2 의 `PER_USER_SSO_APPS`)의 사람별 위임을 끈다. 재프로비저닝이 뒤따르고, 그 앱의 사람별 호출은 서비스 계정으로 되돌아간다 | 일부러 뺀 것이면 없음. 아니면 §4-2 대로 쌍과 비밀을 다시 적고 돌린다 |
| `○ 게이트웨이 재프로비저닝 건너뜀 — 심의 N건 진행 중, M건 대기 — 고칠 것(…)은 …` | 게이트웨이 설정의 어긋남(괄호 안)을 이번 실행에서 고치지 않았다 — 고치려면 게이트웨이·에이전트서버를 다시 띄워야 하는데 심의가 돈다 | 위 `○ 포털·nginx 재기동 건너뜀` 과 같다 |
| `⚠ arp 생략 — …` 줄 끝의 `⚠ 이번 실행은 ARP_BASE 를 받지 못해 … ARP_BASE=… 도 함께 적는다` | arp 항목이 주소와 함께 빠졌다 | 그 줄에 찍힌 `ARP_BASE=…` 를 게이트웨이 `provision.env` 에 옮겨 적는다(또는 `infra/.env` 의 `ARP_HOST`). 지나쳤으면 `gateway_config.json.bak.<날짜>` 에 옛 주소가 남아 있다 |
| `⚠ 포털 관리자 … 활성 관리자 0명`(§6) | 원장에도 고정 목록에도 활성 관리자가 없다 | §4-1 의 `PORTAL_ADMIN_EMAILS` 를 적고 반영한다 |
| `⚠ 프록시 우회 … NO_PROXY 에 없는 내부 목적지: …`(§6) | 그 목적지로 가는 호출이 사내 프록시로 샌다. 줄에는 주소가 아니라 **설정 이름**(`RA_HOST` · `ARP_HOST` · `라우트 <키>` · `TESTSCOPE_BASE_URL`)이 찍힌다 | §4-7 |
| `✗ SPA dist 가 지금 소스와 다르다(dist=… · HEAD=…)`(§6) | Drive 의 프론트 빌드가 옛것이다 | 이 박스에서 빌드하지 않는다. dev 에 알리고, 올라온 뒤 다시 돌린다. 그동안 새 화면은 보이지 않는다 |

## 3. 실행 뒤 확인

명령은 포털 리포 루트에서 돈다. ②·③ 의 출력에는 사내 주소가 찍힌다 — 리포·이슈·메신저에 붙이지 않는다.

```bash
# ① 포털이 준비됐고 관리자가 있다 — temporary 에 no_active_admin · chat_pat_ttl 이 없어야 한다(포트는 infra/.env 의 HTTP_PORT)
curl -s http://127.0.0.1:8088/health/ready

# ② 포털 프로세스가 NO_PROXY 를 받았다 — RA·ARP 호스트가 보여야 한다
tr '\0' '\n' < /proc/$(lsof -t -i:8723 -sTCP:LISTEN)/environ | grep -i '^no_proxy='

# ③ 게이트웨이가 제 백엔드 주소를 살폈다 — 'NO_PROXY 에 내부 목적지 N곳을 더했다' 또는
#    'NO_PROXY — 더할 내부 목적지가 없다' 한 줄이면 정상이다(운영자 셸에 이미 다 있으면 뒤의 것이 나온다)
grep -a '내부 목적지' "$(readlink /proc/$(lsof -t -i:9110 -sTCP:LISTEN)/fd/1)" | tail -1

# ④ nginx 에 ARP·ODB 지시문이 들어갔다 — ARP 는 client_max_body_size 0, ODB 는 2048m 이고 둘 다 proxy_request_buffering off
#    라우트가 없는 쪽은 아무것도 안 나온다(정상). TLS 를 켠 박스는 블록이 두 번 나온다
grep -A13 'location /aireadyportal/' infra/nginx/hwax.conf
grep -A13 'location /odb-hub/' infra/nginx/hwax.conf

# ⑤ 에이전트서버가 새 판이고 심의 호출 한도가 걸렸다 — 첫 명령은 delib_active · delib_queued 두 줄을,
#    둘째 명령은 '심의: 호출 1회 1800.0초·재시도 1회' 가 든 한 줄을 찍어야 한다
curl -s --noproxy '*' -m 5 http://127.0.0.1:9009/health | grep -oE '"delib_(active|queued)": *[0-9]+'
grep -a '\[agent\] LLM 한도' "$(readlink /proc/$(lsof -t -i:9009 -sTCP:LISTEN)/fd/1)" | tail -1

# ⑥ 게이트웨이에 실제로 걸린 시간 한도 — 'GATEWAY_CALL_TIMEOUT=600' 이 든 한 줄
grep -a '시간 한도(초)' "$(readlink /proc/$(lsof -t -i:9110 -sTCP:LISTEN)/fd/1)" | tail -1

# ⑦ nginx /agent/ 의 침묵 한도 — 'proxy_read_timeout 50400s' (TLS 를 켠 박스는 두 줄)
grep -A8 'location /agent/' infra/nginx/hwax.conf | grep -o 'proxy_read_timeout [^;]*'

# ⑧ 대화 저장소가 WAL 로 바뀌었다 — 아무 줄도 안 나와야 한다
grep -a '대화 저장소를 WAL 로 바꾸지 못했다' "$(readlink /proc/$(lsof -t -i:8723 -sTCP:LISTEN)/fd/2)" | tail -1

# ⑨ AIDataHub 워치독의 판정 — AIDataHub 리포 루트에서. 첫 줄이 0 이면 이 박스는 워치독을 안 쓴다(볼 것 없음)
crontab -l 2>/dev/null | grep -c aidh-watchdog
grep -aE 'api (down|refused|timeout|answered)' deploy/apptainer/logs/watchdog.log | tail -3
```

| 확인 | 기대 | 아니면 |
|---|---|---|
| ① 준비·관리자 | `temporary` 에 `no_active_admin` 도 `chat_pat_ttl` 도 없다 | `no_active_admin` 이면 §4-1 의 `PORTAL_ADMIN_EMAILS` 를 적고 반영한다. `chat_pat_ttl` 이면 `infra/.env` 의 `CHAT_PAT_TTL_S` 가 너무 짧다 — 그 줄을 지우거나 46800 이상으로 적고 반영한다(§4-8) |
| ② 포털 `NO_PROXY` | RA·ARP 호스트가 보인다 | `infra/.env` 의 `RA_HOST`·`ARP_HOST` 가 주소만 적혀 있는지 본다(§1-3). 모양이 틀리면 기동 출력에 `⚠ infra/.env 의 … 가 IPv4 주소·호스트명 모양이 아니라 NO_PROXY 에 더하지 않는다` 가 나오고 빠진다 |
| ③ 게이트웨이 `NO_PROXY` | 두 줄 가운데 하나가 나온다 | 한 줄도 없으면 게이트웨이가 옛 코드로 떠 있다. §2 출력에서 `갱신(git pull) 실패` 를 찾는다 |
| ④ nginx | 라우트가 있는 쪽은 위 지시문이 보인다 | 라우트가 있는데 안 보이면 §2 출력에서 `nginx conf 생성 실패` 를 찾는다 |
| ⑤ 에이전트서버 | 첫 명령이 두 줄을 찍고, 둘째 명령이 찍는 줄에 `심의: 호출 1회 1800.0초·재시도 1회` 가 있다 | 첫 명령이 무출력이면 옛 판이 떠 있다 — §2 출력에서 agent-server 의 `갱신(git pull) 실패` 나 `○ agent-server 재기동 건너뜀` 을 찾는다. 초가 1800 보다 작으면 §1 확인 9 다. 초 자리에 `무제한` 이 찍히면 `.env` 에 `DELIB_TIMEOUT_S=0` 이 있다 — 지운다 |
| ⑥ 게이트웨이 시간 한도 | `GATEWAY_CALL_TIMEOUT=600` 이 든 한 줄이 나온다 | 줄이 없으면 게이트웨이가 옛 코드로 떠 있다(③ 과 같다). 값이 600 이 아니면 update-all 을 돌린 셸이 그 이름을 export 하고 있다 — 걷고 게이트웨이를 다시 띄운다(§4-8) |
| ⑦ nginx `/agent/` | `proxy_read_timeout 50400s` | `1h` 면 conf 가 옛것이다 — §2 출력에서 `nginx conf 생성 실패` 를 찾는다. 이 확인은 conf 파일을 본다 — §2 에 `○ nginx 재기동 건너뜀` 이 있었으면 떠 있는 nginx 는 아직 옛 값이다 |
| ⑧ 대화 저장소 | 아무 줄도 안 나온다. DB 옆에 `-wal`·`-shm` 파일이 생기는데 지우지 않는다(백업·이관 때도 같이 둔다) | 줄이 나오면 이번 기동은 종전 방식으로 돈다(동작은 한다). 다음 포털 재기동 뒤에 다시 본다. 그래도 나오면 dev 에 알린다 |
| ⑨ 워치독(쓰는 박스만) | 반영 뒤에 찍힌 줄이 `api timeout N/3 — …` · `api refused — recovering via start_api.sh` · `api answered again — …` 꼴이다(API 가 멀쩡하면 새 줄이 없다) | 반영 뒤 시각에 `api down — recovering` 이 찍히면 옛 스크립트가 돈다 — §2 출력의 AIDataHub 절에서 `✗ git …` 줄을 찾는다 |
| HE팀 페르소나 | 포털 리포 루트에서 `python3 infra/scripts/sync-he-personas.py` 의 끝 줄이 `미리보기(--apply 로 반영) — 새로 N · 고침 N · 그대로 N · 건너뜀 N` 이고 `✗` 줄이 없다(이름이 겹치는 상대 앱이 안 붙은 박스에서 통째로 멈추던 것을 고쳤다) | `✗` 가 없으면 같은 명령에 `--apply` 를 붙여 반영한다. `✗` 가 있으면 반영하지 않고 그 줄을 dev 에 알린다 |
| 프론트 | §2 출력에 `✓ SPA dist 가 지금 소스와 같다` | §2 표의 `✗ SPA dist` 행. ARP 타일 로고가 기본 원인 것, 관리자 화면에 새 항목이 없는 것도 같은 원인이다 |
| 관리자 화면 | 사용자 관리에 「소속 미지정만 보기」와 관리자 스위치가 보인다 | '프론트' 행과 같다 |
| RA 사람별 위임 | Claude 에서 `reportarchive_list_reports(mine=true)` 가 403 없이 본인 공간을 본다 | ③ 을 본다(게이트웨이가 프록시를 타면 403 이다) |
| ARP 타일(켠 박스만) | 클릭하면 포털 로그인 그대로 ARP 가 열린다 | ARP 로그인 화면이 뜨면 §1 확인 6 의 ARP 쪽 설정을 ARP 담당과 다시 본다 |
| ARP 로그아웃(켠 박스만) | `curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8088/aireadyportal/api/auth/logout` 이 404·405 가 아니다 | 404·405 면 ARP 에 그 주소가 없는 것이다. 숫자를 dev 에 알린다 — 그동안 포털에서 로그아웃할 때마다 실패 안내가 뜨고 ARP 세션은 남는다 |
| hwax-risk 새 SIF | Claude 에서 잡이 돈 적 있는 타깃에 `risk_get_coverage` 를 부르면 `job` 에 `signal` 칸이 있다(값은 `null` 이어도 된다). 잡이 없는 박스는 `risk_submit_panel_result` 의 인자에 `evidence_omitted` 가 보이는지만 본다(앞 묶음까지만 가린다) | §2 출력의 HEAX Hub 절에 `· hwax-risk.sif 같음 — 그대로` 가 있으면 Drive 에 새 SIF 가 없던 것이다. dev 에 알린다. `→ stop heax_app_hwax_risk` 줄이 있는데도 안 보이면 2분 뒤 다시 본다(게이트웨이가 60초마다 도구 목록을 다시 받는다). 그래도 없으면 HEAXHub 리포에서 `bash deploy/apptainer/redeploy-app.sh hwax-risk` |
| 심의 도구 | `deliberate_start` 설명에 대기(`queued`)·봉인(`risk-review-sealed`)과 `quiet_ok_s` 가 보인다 | 2분 뒤 다시 본다. 그래도 옛 설명이면 §2 출력에서 agent-server 의 `갱신(git pull) 실패` 를 찾는다 |
| 옛 토큰으로 붙은 서비스·개인 Claude | 반영 전과 같은 도구가 보인다 | 도구가 줄었거나 리스크 심사의 조회가 비면 §1 확인 8 이다. 사용자 관리에서 그 토큰의 주인에게 소속을 준다(재기동 불필요) |

## 4. 설정 — 쓰려는 것만

### 4-0. 무엇을 고치면 무엇으로 반영하나

명령은 전부 포털 리포 루트에서 돈다. 손으로 내렸다 올리지 않는다 — 아래 스크립트로 떠야 '마지막으로 띄운 시점' 이 기록된다. 손으로만 다시 띄우면 다음 update-all 이 그 서비스를 한 번 더 내렸다 올린다.

| 고친 파일 | 반영 명령 | 다시 뜨는 것 |
|---|---|---|
| 포털 `infra/.env`(4-1·4-8) · `backend/config/systems.local.yaml`(4-4) · `backend/config/routes.local.env` | `./infra/scripts/update-forges.sh portal` | 포털(라우트나 nginx 침묵 한도가 바뀌면 nginx 도) |
| 게이트웨이 `provision.env`(4-2) | `./infra/scripts/update-all.sh` | 게이트웨이·에이전트서버(재프로비저닝은 여기에만 있다) |
| 포털 `backend/config/access.local.yaml`(4-3) | 없음 | 없음 — 다음 요청부터 읽힌다 |
| 에이전트서버 `.env`(4-5·4-8) | `./infra/scripts/update-sites.sh agent-server` | 에이전트서버 |
| AIDataHub `deploy/apptainer/.env`(4-6) | `./infra/scripts/update-forges.sh aidh` | AIDataHub API(워치독 값 둘은 재기동 없이 다음 분부터 먹는다) |
| 운영자 셸의 `NO_PROXY`(4-7) | 새 셸에서 `HWAX_RESTART_ALL=1 ./infra/scripts/update-forges.sh portal` | 포털·nginx(파일이 안 바뀌어 강제로 띄운다) |
| hwax-risk 앱의 시간 한도(4-8) | 없음 — 이 박스에서 고치지 않는다. dev 에 알린다 | — |

- 4-7 을 빼면 어느 것이든 `./infra/scripts/update-all.sh` 한 번으로도 된다. 바뀐 서비스만 다시 뜬다.
- **심의가 돌거나 줄 서 있으면 위 명령들이 재기동을 미룬다.** 포털 쪽은 `○ 포털·nginx 재기동 건너뜀`, 에이전트서버는 `○ agent-server 재기동 건너뜀`, 4-2 는 `○ 게이트웨이 재프로비저닝 건너뜀` 을 찍는다 — 그 줄이 나왔으면 고친 값은 **아직 반영되지 않았다**(`update-forges.sh portal` 은 그래도 끝에 `✓ portal 갱신 완료` 를 찍는다). 심의가 끝난 뒤 같은 명령을 다시 돌린다. 수는 §1-1 의 명령 12 로 본다.
- 기다릴 수 없으면 명령 앞에 `AGENT_RESTART_FORCE=1` 을 붙인다. 도는 심의(`interrupted` 로 닫힌다)와 줄 선 심의, 웹 심의·리스크 패널의 구독이 전부 끊긴다. 이 값을 `.env` 에 적어 두지 않는다 — 그 실행에만 준다.
- `update-forges.sh` 는 리포 루트가 `…/Projects/…` 인 박스에서만 위처럼 일한다. 경로가 다른 박스는 `./infra/scripts/deploy-all-from-drive.sh portal`(또는 `aidh`)을 부른다 — 같은 일을 한다.

### 4-1. 포털 `infra/.env` (반영 — `./infra/scripts/update-forges.sh portal`)

적는 꼴과 고친 뒤의 `ok` 확인은 §1-3 이다.

| 키 | 무엇 | 주의 |
|---|---|---|
| `PORTAL_ADMIN_EMAILS` | 언제나 관리자인 이메일. 쉼표로만 잇는다. 원장의 관리자와 OR 다 | 주소는 글자 그대로 견준다 — 별칭 도메인(`@corp.example` 과 `@ax.corp.example`)을 같은 사람으로 보지 않으니 둘 다 쓰는 사람은 **둘 다** 적는다. 그 주소로 한 번 로그인해 원장에 행이 있어야 관리자다. 정지가 이긴다. 반영 뒤 사용자 관리에서 그 사람이 「관리자 · 고정」으로 보이면 된 것이다. mock 로그인 박스에서 `MOCK_USER_EMAIL` 의 주소를 적으면 누구나 관리자다 |
| `SAML_ATTR_DEPT_ID` | 부서 코드 Claim 이름 — 원장의 부서 코드 칸에만 적는다 | 부서 코드를 `SAML_ATTR_DEPARTMENT` 로 받으면 사람이 적은 부서명이 코드로 덮인다. 코드는 이 키로 받는다 |
| `SAML_ATTR_SABUN` | 사번 Claim 이름 — 같은 사번의 정지된 계정이 있으면 SSO 로그인을 거절한다 | ⚠ 켜면 로그인이 막히는 사람이 생길 수 있다. 켜기 전에 사번이 회사를 넘어 겹치지 않는지 확인한다(겹치면 다른 회사의 같은 번호도 거절된다). 원장을 읽지 못하는 동안에는 사번이 오는 SSO 로그인이 전부 거절된다. 걸린 사람은 로그인 화면에서 '정지' 를 보고 접속 이력에 「SSO — 거절(같은 사번의 정지된 계정이 있음)」이 남는다. 이미 정지된 사람은 제 메일로 한 번 더 로그인을 시도해야 사번이 적힌다. 끄려면 값을 비우고 반영한다 |
| `SSO_DEFAULT_AFFILIATION` | SSO 로 처음 들어온 사람에게 줄 소속 id | ⚠ `CAEG`(전권)를 적으면 ADFS 를 통과한 **누구나** 전권이다. 일부에게만 줄 것이면 비워 두고 4-3 의 매핑 표를 쓴다 |

- `SAML_ATTR_*` 는 Assertion 의 속성 이름과 **글자 그대로** 같아야 한다(운영 ADFS 는 전체 URI). 이름을 모르면 짐작한 이름을 넣고 반영한 뒤 SSO 로 한 번 로그인한다. 이름이 틀렸으면 포털 로그에 `SAML: SAML_ATTR_…=… 이 Assertion 에 없다 — 받은 Claim: […]` 한 줄이 남는다(이름만 남고 값은 안 남는다). 거기서 골라 고쳐 적는다. 아래 명령에 줄이 안 나오면 이름이 맞은 것이다.
- 부서 코드·사번 칸은 새 판의 첫 기동(§2) 때 이미 생겼다. 여기서 따로 할 일은 없다.
- 계정을 정지하면 그 사람의 앱 쪽 자격도 함께 거둔다(새 설정은 없다). 거두지 못하면 같은 로그에 `정지 <이메일> — <앱> 쪽 자격 회수 실패` 가 남는다. 정지는 적용됐고, 그 앱이 이미 내준 토큰은 만료까지 남을 수 있다.

```bash
# 포털 로그에서 — 어느 박스든 지금 떠 있는 포털의 로그 파일을 본다
grep -a '이 Assertion 에 없다' "$(readlink /proc/$(lsof -t -i:8723 -sTCP:LISTEN)/fd/2)" | tail -1
```

### 4-2. 게이트웨이 `provision.env` (반영 — `./infra/scripts/update-all.sh`)

이 파일도 bash 가 읽는다. 공백이 든 값은 값 전체를 큰따옴표 한 쌍으로 묶는다.

| 키 | 언제 | 주의 |
|---|---|---|
| `ARP_TOKEN` | ARP 담당이 서버 간 `/mcp` 용 서비스 토큰을 내준 뒤 | 반영하면 스스로 재프로비저닝한다. `· config에 없거나 주소가 어긋난 백엔드: arp → 재프로비저닝`(옛 arp 항목이 이미 걷힌 뒤) 또는 `· 토큰 드리프트: arp`(옛 항목이 남아 있거나 토큰을 바꿨을 때)가 찍히고 `✓ 재프로비저닝으로 백엔드 정합 완료` 로 끝난다. ⚠ 두 줄 다 안 나오면 ARP 주소가 설정 파일에 없는 것이다(토큰만으로는 아무 줄 없이 지나간다) — §1-2 셋째 줄대로 `ARP_HOST` 를 적고 다시 돌린다. 지금은 `Authorization: Bearer` 로 싣는다 — ARP 가 쿼리(`?token=`) 방식이라고 회신하면 dev 에 알린다 |
| `SMARTTWIN_MCP_URL` | 이 박스에서 SmartTwinMCP(해석 잡 제출)를 쓸 때만 | 값은 `http://127.0.0.1:5013/mcp` 꼴이다. 쓰는 박스는 첫 update-all **전에** 적는다(§1 확인 4). 안 쓰는 박스는 적지 않는다 — 가짜 DOWN 이 사라진다 |
| `PER_USER_SSO_APPS` | ste 방식 위임을 쓰는 여섯 번째 앱을 붙일 때 | 목록 **전체를 큰따옴표 한 쌍으로** 묶어 `<앱 키>:<ENV 접두>` 를 공백으로 나열한다 — `PER_USER_SSO_APPS="app1:APP1 app2:APP2"`. 쌍마다 따옴표를 치거나 따옴표 없이 둘 이상 적으면 `command not found` 가 나고 값이 비어 아무 위임도 만들어지지 않는다. 그 앱의 `<접두>_SSO_SECRET`·`<접두>_SSO_URL` 도 같은 파일에 적는다. 반영 출력에 `✓ <앱 키> 사람별 위임 — …` 이 나오면 된 것이다. **끌 때는** `<접두>_SSO_SECRET` 값을 비우거나, 쌍과 그 앱의 줄들을 지우고 반영한다 — 어느 쪽이든 `· 사람별 위임 끄기: <앱 키>` 가 나와야 꺼진 것이다(이번 판부터 쌍째 지운 것도 update-all 이 알아챈다). 쌍째 지웠는데 그 줄이 안 나오면 위임이 옛 비밀로 남아 있다 — 쌍을 되살리고 비밀만 비워 다시 반영한 뒤에 지운다 |

### 4-3. 포털 `backend/config/access.local.yaml` (박스 파일 · 반영 명령 없음 — 다음 요청부터 읽힌다)

SSO 로 **처음** 들어오는 사람의 소속을 Claim 으로 정한다. 이미 있는 사람은 로그인해도 안 바뀐다 — 지금 소속이 빈 사람들은 관리자 화면의
「소속 미지정만 보기」에서 한 명씩 지정한다.

```yaml
# 값은 반드시 따옴표로 — 따옴표 없는 0123 은 숫자로 읽혀 영영 안 맞는다
sso_affiliation_map:
  - {claim: "<DeptId Claim 이름>", value: "<부서 코드>", affiliation: CAEG}
  # 회사 코드로 거는 행은 그 회사 사람 전원에게 그 소속을 준다 — 넣을지 먼저 정한다
  # - {claim: "<CompId Claim 이름>", value: "<회사 코드>", affiliation: CAEG}
```

- ⚠ 행 하나가 그 값을 가진 **전원**을 그 소속으로 넣는다. 회사 코드 한 행으로 `CAEG`(전권)를 주면 그 회사 사람 누구나 첫 로그인에 전권을 받고, `SSO_DEFAULT_AFFILIATION` 과 달리 어디에도 경고가 뜨지 않는다. 일부에게만 줄 것이면 부서 코드 행만 적는다.
- 위에서부터 처음 맞는 행이 이긴다. 넓은 행(회사)을 위에 두면 아래의 좁은 행(부서)은 쓰이지 않는다. 맞는 행이 없으면 `SSO_DEFAULT_AFFILIATION`(기본 빈 값).
- `claim` 은 전체 URI 가 정확하다. 짧은 이름(`CompId`·`DeptId`)은 그 로그인에 끝 이름이 같은 Claim 이 하나뿐일 때만 맞는다. 4-1 의 `SAML_ATTR_DEPT_ID` 를 켜지 않아도 동작한다.
- 부서 코드 값은 `SAML_ATTR_DEPT_ID` 를 켠 뒤 사용자 관리의 「부서 · 코드」 칸에서 읽는다(그 사람이 한 번 로그인한 뒤). 회사 코드 값은 포털에 남지 않는다 — SSO 운영 쪽에 묻는다.
- 자동으로 지정된 사람은 접속 이력의 로그인 줄에 `SSO — 첫 로그인, 소속 <소속 라벨>(<id>) 자동 지정(SSO 속성 규칙 · Claim 매핑)` 으로 남는다. 화면에서는 '자동 지정' 으로 찾는다(기본 소속으로 들어왔으면 끝이 `(기본 소속)` 이다).
- 박스에만 있는 게이트웨이 백엔드·타일도 이 파일의 `platforms` 에 적는다. ⚠ 같은 id 는 그 플랫폼을 **통째로 바꾼다** — 추적 파일의 플랫폼에 하나를 더하려면 그 플랫폼의 `systems`·`gateway` 를 전부 다시 적는다.
- ⚠ 저장할 때마다 아래 명령으로 읽히는지 본다. `OK` 면 됐다. 대괄호 목록이 나오면 읽히긴 했지만 버려진 행이나 표에서 빠진 타일·백엔드가 있다 — 목록의 문장대로 고친다(사용자 관리 맨 위 '배선 설정' 에도 뜬다). 오류 줄이 나오면 깨진 것이다 — 고칠 때까지 포털을 다시 띄우는 명령을 돌리지 않는다(update-all 도 포털을 다시 띄운다). 도는 중에는 직전 정책을 지키지만, 깨진 채 다시 뜨면 요청이 전부 실패한다.

```bash
# 포털 리포 루트에서(§2 를 마친 뒤 — 이 확인은 새 판의 코드를 쓴다)
apptainer exec --bind "$PWD:/workspace:ro" infra/apptainer/portal.sif sh -c 'cd /workspace/backend && python -c "
from pathlib import Path
from app.access.policy import load_raw, parse_policy
print(list(parse_policy(load_raw(Path(\"config/access.yaml\"))).warnings) or \"OK\")"' 2>&1 | tail -1
```

### 4-4. 포털 `backend/config/systems.local.yaml` (반영 — `./infra/scripts/update-forges.sh portal`)

- `arp:` 블록을 지운다 — 타일 id 가 `aireadyportal` 로 바뀌어 쓰이지 않는다(남겨 두면 포털이 뜰 때마다 경고 한 줄). 지우기 전에 그 블록을 다른 곳에 적어 둔다(되돌릴 때 쓴다). 이것만 지웠으면 따로 반영할 것은 없다.
- 박스에만 있는 새 타일은 `<새 id>: {name: ..., url: ...}` 로 적는다(외부 링크 타일만). 4-3 의 `platforms` 에 같이 안 적으면 **모두에게 보인다.**
- (ARP 가 준비되기 전 임시) 직결 링크를 남기려면 `arp:` 블록을 지우지 말고 `name` 한 줄을 더한다. 권한은 아래처럼 `access.local.yaml` 에서 건다. `aireadyportal=` 라우트를 적는 날 두 블록을 함께 지운다.

```yaml
# systems.local.yaml
arp:
  name: AI Ready Portal(직결)
  url: http://<ARP 서버>:<포트>/
# access.local.yaml — 같은 id 는 통째로 바뀌므로 셋 다 적는다(안 적으면 이 타일이 모두에게 보인다)
platforms:
  - id: arp
    label: AI Ready Portal
    systems: [aireadyportal, arp]
    gateway: [arp]
```

### 4-5. 에이전트서버 `.env` (반영 — `./infra/scripts/update-sites.sh agent-server`)

전부 선택이다. 안 넣으면 기본값으로 돈다. 반영은 에이전트서버를 다시 띄운다 — 심의가 돌거나 줄 서 있으면 스스로 미룬다(§4-0). 이 파일에 적는 시간 한도(`DELIB_TIMEOUT_S` 등)는 §4-8 에 따로 모았다.

| 키 | 기본 | 무엇 |
|---|---|---|
| `DELIB_EVID_ITEMS` | 120 | 사전 근거 칸 수. 기본값이 120 이 됐다 — 따로 넣을 필요 없다(예전에 더 작은 값을 적어 둔 박스는 그 줄을 뺀다). 칸 수보다 합계 예산이 먼저 걸린다(§5) |
| `DELIB_DECISION_CTX` | (없음 = 자동) | 의장이 보는 라운드당 전사 상한(자). **넣지 않으면 모델 컨텍스트에서 유도한다** — 128K 창·3라운드에서 라운드당 최대 약 36,000자이고, 화두·근거가 실린 만큼 줄며 4라운드부터는 더 좁다. 값을 넣으면 그 값이 자동을 덮는다. 임시로 24000 을 넣어 두었다면 3라운드 심의에서는 빼는 쪽이 더 넓다. 빼기 전에 `curl -s http://127.0.0.1:9009/health` 의 `context_tokens` 가 운영 모델의 창으로 잡혀 있는지 본다 |
| `DELIB_MAX_SEATS` | 20 | 요청 좌석 상한. 지정 반대석은 상한 밖에서 한 석 더 앉는다. 포털 웹 화면의 상한은 20 그대로다(MCP·리스크 앱 경로만 풀린다) |
| `DELIB_JOB_MAX_RUNNING` | 2 | 동시에 도는 심의 수(전역). 0 이하는 2 로 읽는다 |
| `DELIB_JOB_MAX_RUNNING_PER_USER` | 0 = 전역과 같음 | 한 사람이 동시에 돌릴 수 있는 수. 여러 사람이 패널을 돌리면 전역을 올리고 이것을 낮춘다(전역 6 · 사람별 2 처럼). 전역을 올리면 AIDataHub 풀(4-6)도 같이 본다 |
| `DELIB_JOB_QUEUE_MAX` | 20 | 상한에 걸렸을 때 줄 세울 수. 0 이면 종전처럼 거절한다 |
| `DELIB_HUMAN_NOTE_MAX` | 2000 | 사람 의견 상한(자). 잘리면 화면과 결과에 알린다. 포털 웹은 8,000 까지 받는다 |
| `DELIB_KNOWLEDGE_CONCURRENCY` | 6 | 좌석 지식카드 조회를 한 번에 몇 명씩 하나 |
| `DELIB_KNOWLEDGE_SYNTHETIC_SEATS` | (빈 값) | 지식카드를 조회할 합성 지정석 키(쉼표). 반대석을 AIDataHub 에 **등록한 뒤에만** 적는다(`delib-baseline-defender` 같은 키) |
| `DELIB_SER_CLIP` | 700 | 좌석 발언 칸 하나의 상한(자). 넓은 창에서는 0(끊지 않음)으로 풀 수 있다 |

⚠ 값 줄 끝에 설명을 붙이지 않는다(`KEY=6  # 설명`). 이 파일은 `#` 뒤를 떼지 않아 그 값이 숫자로 읽히지 않고 기본값으로 돈다(`DELIB_DECISION_CTX` 만은 자동이 아니라 옛 6,000자로 떨어진다). 환경 키트(`infra/env-kits/agent-server.env`)의 줄을 옮겨 적을 때도 `#` 뒤를 지운다. 반영한 뒤 아래로 확인한다 — 아무 줄도 안 나와야 한다.

```bash
# 지금 떠 있는 에이전트서버의 로그에서(띄운 방법에 따라 파일이 다르다 — 이 명령은 어느 쪽이든 맞는 파일을 본다)
grep -a 'env .*파싱 실패' "$(readlink /proc/$(lsof -t -i:9009 -sTCP:LISTEN)/fd/1)"
```

줄이 나오면 그 키의 줄 끝을 지우고 다시 반영한다. 리포 안의 `agent-server.log` 는 `./start.sh -d` 로 띄웠을 때만 쓰인다 — update-all 이 띄운 박스에서는 옛 파일이다.
글자 값인 `DELIB_KNOWLEDGE_SYNTHETIC_SEATS` 는 이 문구가 남지 않는다. `deliberate_start` 설명의 「지금 적힌 키」에 적은 키가 그대로 보이는지로 확인한다.

### 4-6. AIDataHub `deploy/apptainer/.env` (반영 — `./infra/scripts/update-forges.sh aidh`)

`DB_POOL_SIZE`(12) · `DB_MAX_OVERFLOW`(8) · `DB_POOL_TIMEOUT`(60초). 선택이다 — 기본값으로 충분하다. 올릴 때는 같은 PostgreSQL 을 쓰는 앱들의 합을
`max_connections` 와 견준다. ⚠ `api_server/.env` 에 넣으면 다음 기동에 사라진다 — `deploy/apptainer/.env` 에 넣는다. 값 없는 줄(`DB_POOL_SIZE=`)은 남기지 않는다 — API 가 기동에서 멈춘다.

이번에 같은 파일에 생긴 시간 한도도 전부 선택이다(안 적어도 기본값으로 돈다 — update-all 이 이 파일에 덧붙이지 않는다).

| 키 | 기본 | 무엇 |
|---|---|---|
| `AIDH_DB_CONNECT_TIMEOUT_S` | 10 | 새 DB 연결을 맺는 한도(초). `DB_POOL_TIMEOUT` 보다 작게 둔다 |
| `AIDH_SEARCH_STATEMENT_TIMEOUT_S` | 90 | 검색 도구가 돌리는 SQL 문장 하나의 한도(초, 0 = 끔). `DB_POOL_TIMEOUT` 과 더한 값이 에이전트서버의 `KNOWLEDGE_TIMEOUT_S`(180)보다 작아야 한다 |
| `AIDH_HEALTH_GAUGE_TIMEOUT_S` | 2 | `/api/system/health` 가 DB 게이지를 기다리는 한도(초). 넘으면 게이지만 비우고 곧바로 200 을 준다 |
| `AIDH_WATCHDOG_PROBE_TIMEOUT_S` | 5 | 워치독(매분 cron)이 `/health` 의 답을 기다리는 초 |
| `AIDH_WATCHDOG_TIMEOUT_STRIKES` | 3 | 답이 늦은 것이 몇 번 이어져야 API 를 다시 띄우나(약 3분). 연결 거부는 종전대로 곧바로 다시 띄운다 |

- 위 셋(API 가 읽는다)은 값 없는 줄을 남기지 않는다 — `DB_POOL_SIZE` 와 같다. 반영은 API 재기동이다.
- 아래 둘(워치독이 읽는다)은 재기동 없이 다음 분부터 먹는다. 종전에는 5초 안에 두 번 못 답하면 바쁜 API 도 다시 띄웠고, 그때마다 돌던 검색이 끊겼다. 판정은 `deploy/apptainer/logs/watchdog.log` 에 사유와 함께 남는다(§3 의 ⑨).

### 4-7. 운영자 셸의 `NO_PROXY`(`~/.bashrc`) (반영 — 새 셸에서 `HWAX_RESTART_ALL=1 ./infra/scripts/update-forges.sh portal`)

- 게이트웨이는 이제 제 백엔드 주소를 스스로 더하고, 포털은 `RA_HOST`·`ARP_HOST` 를 받는다. **RA·ARP 때문에 넣은 줄은 없어도 된다.**
- 그 밖의 내부 호스트(ODB · TestScope · LLM 등)가 거기 있으면 **지우지 않는다.**
- §2 에 `NO_PROXY 에 없는 내부 목적지: …` 가 나왔으면, 찍힌 설정 이름에 적힌 호스트를 `NO_PROXY` 에 주소 그대로 더한다(쉼표로 나눈다). 그 호출은 포털이 하므로 포털만 다시 띄운다 — 게이트웨이는 손댈 것이 없다.
- ⚠ 대역(`a.b.c.0/24`) · `*.도메인` · 공백으로 나눈 항목은 동작하지 않는다(httpx 가 읽지 못한다). 주소를 하나씩 쉼표로 나눠 적는다. §2 의 그 줄 끝 괄호에 `httpx 가 읽지 못하는 모양이다` 가 붙으면 이 경우다.
- 고친 뒤 새 셸에서 `./infra/scripts/check-egress.sh --internal` 을 돌린다(네트워크를 건드리지 않는다). `내부 목적지 N곳이 전부 NO_PROXY 에 있다` 가 나오면 된 것이다. 설정 이름이 찍히면 그것이 아직 빠져 있다. 된 뒤에 위 반영 명령으로 포털을 다시 띄운다.

### 4-8. 시간 제한 — 어느 층이 먼저 걸리나, 어디에 적나

전부 코드 기본값이 있다. **안 적어도 된다** — 이 값들 때문에 이 박스에서 미리 할 일은 §1 확인 9 하나다. 심의 전체에 거는 시간 제한은 없다(안쪽 한도가 전부 유한해 스스로 끝난다).
안쪽 한도가 바깥보다 먼저 걸려야, 걸린 값과 손잡이 이름이 든 문구가 나온다. 한 줄만 바꾸면 순서가 뒤집히므로 표의 위아래 줄을 같이 본다.

| # | 층(안쪽 → 바깥) | 기본 | 손잡이 | 적는 곳 |
|---|---|---|---|---|
| 1 | LLM 서버에 연결 | 10초 | `LLM_CONNECT_TIMEOUT_S` | 에이전트서버 `.env` |
| 2 | 심의의 LLM 호출 한 번(시도 1회) | 1800초 | `DELIB_TIMEOUT_S`(0 = 한도 없음). 심의 하나만이면 요청의 `timeout_s`(10 ~ `DELIB_TIMEOUT_MAX_S` 14400) | 에이전트서버 `.env` |
| 3 | 그 호출의 재시도까지 | 3608초(2 × 1800 + 8) | `DELIB_LLM_MAX_RETRIES`(1) | 에이전트서버 `.env` |
| 4 | 좌석 발언 하나(스트림이 조용할 수 있는 구간) · 의장 결정문 | 10824초(3 × 3608) · 의장은 다시 부르는 것까지 7216초(2 × 3608) | `DELIB_PARSE_RETRIES` · `DELIB_CHAIR_RETRIES`(1) | 에이전트서버 `.env` |
| 5 | 좌석의 도구 호출 — AIDataHub 안 | 풀 대기 60초 + 검색 문장 90초 | `DB_POOL_TIMEOUT` · `AIDH_SEARCH_STATEMENT_TIMEOUT_S` | AIDataHub `deploy/apptainer/.env`(§4-6) |
| 6 | 좌석의 도구 호출 — 지식카드 조회 | 180초(넘으면 한 번 다른 방식으로 되묻는다) | `KNOWLEDGE_TIMEOUT_S` | 에이전트서버 `.env` |
| 7 | 좌석의 도구 호출 — 게이트웨이가 백엔드를 기다린다 | 600초(시간 초과는 다시 보내지 않는다) | `GATEWAY_CALL_TIMEOUT` | 게이트웨이를 띄우는 셸의 환경(`.env`·`provision.env` 는 읽지 않는다) |
| 8 | 좌석의 도구 호출 — 엔진이 게이트웨이를 기다린다 | 900초 | `MCP_CALL_TIMEOUT_S` | 에이전트서버 `.env` |
| 9 | 개인 Claude ↔ 게이트웨이(nginx `/mcp-gw/`) | 1h | `NGINX_MCP_READ_TIMEOUT` | 포털 `infra/.env`(nginx 생성기가 읽는다) |
| 10 | 리스크 패널 한 건(벽시계) | 43200초(12시간) | `HWAXRISK_PANEL_TIMEOUT_S`(0 = 끔) | hwax-risk 앱 매니페스트의 `launch.env` |
| 11 | 침묵 한도 ① 포털이 에이전트서버 스트림을 읽는다 | 46800초(13시간) | `AGENT_STREAM_IDLE_TIMEOUT_S`(0 = 끔) | 포털 `infra/.env` |
| 12 | 침묵 한도 ② nginx `/agent/` | 50400s(14시간) | `NGINX_AGENT_READ_TIMEOUT`(0 은 받지 않는다) | 포털 `infra/.env`(nginx 생성기가 읽는다) |
| 13 | 침묵 한도 ③ 리스크 앱이 포털 스트림을 읽는다 | 54000초(15시간) | `HWAXRISK_ENGINE_READ_TIMEOUT_S` | hwax-risk 앱 매니페스트의 `launch.env` |
| 14 | 챗 토큰 수명(포털이 요청마다 에이전트서버에 넘기는 요청자 자격) | 86400초(24시간) | `CHAT_PAT_TTL_S` | 포털 `infra/.env` |
| 신호 | 엔진이 조용한 동안 흘리는 heartbeat — 11~13 이 살아 있는 심의에 걸리지 않게 한다 | 15초 | `DELIB_HEARTBEAT_S`(0 = 끔) | 에이전트서버 `.env` |

- 반영 명령은 §4-0 표에서 그 파일의 줄이다. 값 줄에는 수만 적는다(에이전트서버 `.env` 는 줄 끝 설명을 떼지 않는다 — §4-5). nginx 두 값만 단위 하나(s·m·h·d)를 붙일 수 있다.
- 지금 걸린 값은 §3 의 ⑤(에이전트서버)·⑥(게이트웨이)·⑦(nginx)로 본다. 4 의 값은 잡마다 `deliberate_status` 의 `quiet_ok_s` 로 나온다.
- 표 밖의 포털 손잡이 둘(`infra/.env`) — `AGENT_UNARY_TIMEOUT_S`(600초, 심의 전 도우미의 대기. 넘으면 실패가 아니라 기본값으로 진행한다) · `CONV_STORE_BUSY_TIMEOUT_S`(30초, 대화 저장소의 잠금 대기. 올리지 않는다 — 리스크 앱이 포털의 대화 생성을 기다리는 30초를 넘으면 안 된다).
- 게이트웨이(7) — 기본값이 운영값이다. 0 을 적지 않는다(끄는 값이 아니다). 올리려면 감싸는 값(8·9 와 포털 코드 안의 절차 워밍업 690초)을 같은 폭으로 올려야 하므로 dev 에 알린다. §3 의 ⑥ 이 600 이 아니면 운영자 셸의 그 export 를 걷고, 도는 심의가 없을 때 새 셸에서 `HWAX_RESTART_ALL=1 ./infra/scripts/update-sites.sh mcp-gateway` 를 돌린다(게이트웨이 재기동에는 심의 보호가 없다).
- hwax-risk(10·13) — 그 앱은 셸의 export 도 `.env` 도 받지 않는다(매니페스트의 `launch.env` 만 닿는다). 매니페스트는 추적 파일이라 이 박스에서 고치면 다음 update-all 이 원격 것으로 되돌린다 — 바꿔야 하면 dev 에 알린다. 기본값이면 할 일이 없다.

**좌석이 호출 한도에 걸려 빠질 때.** 화면과 상태줄에 `⚠ N라운드 좌석 유실: <좌석> · LLM 호출이 1,800초 안에 끝나지 않았다(2회 시도 · APITimeoutError)` 가 나온다. 먼저 이 박스의 `DELIB_TIMEOUT_S` 를 올린다(3600 부터 — 반영은 §4-0). 심의 하나만이면 부르는 쪽이 `timeout_s` 로 올린다(§5). 같이 지킬 것은 셋이다.

- 2 × `DELIB_TIMEOUT_S` + 8 이 리스크 패널 벽시계(10)보다 작아야 한다. 21596 을 넘기려면 dev 에 알려 벽시계도 올린다.
- `DELIB_TIMEOUT_MAX_S` 는 올리지 않는다. 포털과 화면의 상한(14400)과 같은 수여야 한다 — 이것만 올리면 포털이 422 로 막는다.
- heartbeat 를 켜 둔다. 켜져 있는 한 침묵 한도(11~13)와 챗 토큰(14)은 그대로 두면 된다.

**heartbeat 는 끄지 않는다.** 끄면(`DELIB_HEARTBEAT_S=0`) 좌석 발언 하나가 끝날 때까지 스트림에 아무것도 흐르지 않는다. 그러면 `timeout_s` 를 올려 청한 심의는 침묵이 11~13 을 넘어 살아 있는 채 구독이 끊기고(상한 14400 이면 86424초), 브라우저와 nginx 사이의 사내 프록시가 조용한 연결을 끊어도 막을 것이 없고, 화면은 `서버 살아 있음` 을 말하지 못하며, 리스크 앱은 벽시계와 취소를 다음 프레임이 올 때에야 본다. 끈 박스는 기동 로그의 `[agent] ⚠ DELIB_HEARTBEAT_S=0` 줄이 11~13 이 넘어야 할 초를 적는다.

**챗 토큰 수명은 46800 밑으로 내리지 않는다.** 길게 두면 사용자가 로그아웃했거나 세션(8시간)이 끝난 뒤에도 그 심의에 건넨 토큰이 살아 있다(에이전트서버 메모리에만 있고 챗 용도로만 쓰이며, 권한은 게이트웨이가 60초마다 포털에 다시 묻는다). 짧게 두면 그보다 오래 돈 심의가 도는 중에 요청자 자격을 잃고, 그 뒤의 조회와 보고서 저장을 서비스 계정으로 한다(경고 `credential_degraded` — 결과가 요청자 시야와 다를 수 있다). 1800 이하는 쓰지 않고 86400 으로 읽는다(0 은 끔이 아니다). 46800 밑이면 쓰기는 하되 §3 의 ① 에 `chat_pat_ttl` 이 뜬다.

도는 심의가 살아 있는지는 아래에서 본다.

| 어디서 | 무엇을 |
|---|---|
| 이 박스 | §1-1 의 명령 12 — `delib_active`(도는 수) · `delib_queued`(줄 선 수) |
| MCP(Claude) | `deliberate_status` 의 `idle_s`(마지막 이벤트 뒤 초) · `last_step`(마지막으로 일어난 일) · `quiet_ok_s`(좌석 발언 하나가 조용할 수 있는 초). `idle_s` 가 `quiet_ok_s` 안이면 기다리는 중이다. 넘었다고 멈춘 것도 아니다(자유 조회 단계는 더 길다) — 다시 띄우지 않는다 |
| 웹 화면 | 도는 턴 아래의 `서버 살아 있음 · 마지막 진행 N분 전`. heartbeat 가 45초 끊기면 `신호 없음 N초 — 연결이 끊겼을 수 있습니다…` 로 바뀐다(화면이 끊지는 않는다) |
| 리스크 심사 | `risk_get_coverage` 의 `job.signal`(`frame_idle_s` · `last_step`). 화면은 아직 그리지 않는다(§6) |

한도가 걸리면 부른 쪽에 아래처럼 보인다.

| 걸린 층 | 보이는 것 | 그 뒤 |
|---|---|---|
| 2~4 LLM 호출 | `⚠ N라운드 좌석 유실: …`(경고 `seat_lost`). 그 좌석만 그 라운드에서 빠지고 심의는 간다. 의장이면 오류 `chair_failed`(`의장이 결정문을 내지 못했다 — …`) | 위 「좌석이 호출 한도에 걸려 빠질 때」. 의장 실패는 §5 |
| 7 도구 호출 | `backend <키>: <도구> 이 600초 안에 답하지 않았다(GATEWAY_CALL_TIMEOUT)…` | 같은 호출을 곧바로 다시 보내지 않는다(백엔드는 아직 일하고 있을 수 있다) |
| 10 리스크 패널 | 패널 오류 `panel_timeout: 패널이 43200초(HWAXRISK_PANEL_TIMEOUT_S)를 넘겼다 — …`. 잡은 멈춘다 | §6 |
| 11 포털 | 오류 `agent_stream_idle` — `에이전트 서버가 46800초 동안 아무 신호도 보내지 않아 구독을 끊었다(AGENT_STREAM_IDLE_TIMEOUT_S)…` | 심의는 서버에서 계속 돌 수 있다. 다시 시작하기 전에 Report Archive 와 대화 목록을 본다 |
| 12 nginx | nginx 는 문구를 못 낸다. 화면이 `스트림이 끊겼습니다 — 프록시의 침묵 한도(NGINX_AGENT_READ_TIMEOUT)에 걸렸거나 서버가 재기동했을 수 있습니다…` 로 알린다 | 11 과 같다 |
| 14 챗 토큰 | 경고 `credential_degraded` | `CHAT_PAT_TTL_S` 가 그 심의보다 짧다 |

## 5. 실사용 팀이 바꿔 쓸 것(Claude·MCP 로 심의를 부르는 쪽)

| 무엇 | 지금 |
|---|---|
| 근거 형식 | `{source, tool, args, result, key}`. 본문은 `result` 에 둔다(다른 이름도 받지만 `result` 가 정본). `key` 에 제 번호(`E1-CH-015` — 영문·숫자·`_.-` 24자 이내)를 넣으면 좌석·의장이 받는 근거 줄의 표지가 `[e:N\|E1-CH-015]` 로 찍힌다. 결정문의 인용은 `[e:N]` 이거나 그 표지를 옮겨 적은 꼴이다(둘은 같은 항목이다 — 키가 안 찍힌 결정문은 고장이 아니다) |
| 미리 자르지 않는다 | 항목당 **천장**이 150,000자일 뿐이고, 먼저 걸리는 것은 모델 컨텍스트에서 유도되는 **합계 예산**이다(128K 창·기본 설정에서 전부 합쳐 약 18,000자). 항목 하나도 이 값을 넘지 못하고, 앞 항목부터 채우다 넘치면 뒤 항목은 통째로 빠진다. 지금 걸리는 값은 `deliberate_jobs` 의 `limits`(`evidence_items`·`evidence_item_chars`·`evidence_total_chars`)로 본다. 합이 그 안에 들게 하고 중요한 근거를 앞에 둔다 |
| 버려진 근거 | `deliberate_status`·`deliberate_result` 의 `evidence_omitted`(목록 `[{source, text}]`)에 실린다. 목록이 비어 있지 않으면 좌석이 못 봤거나 줄여서 본 근거, 못 앉힌 좌석, 봉인이 닫은 요청, 잘린 사람 의견이 있다는 뜻이다(30건을 넘으면 앞 30건과 마지막 5건만 남는다) |
| 소급 검증 | `job: "risk-review-sealed"` 하나로 VOC 환기 · 지식·보고서 사전 검색 · 지정 도구 사전 호출 · 좌석 자유 조회 · 좌석 지식카드 · 웹 리서치 · 이어하기 좌석 재심사를 닫는다. 닫지 않는 것은 좌석 구성과 역할 정의(지금 시점의 전문가 레지스트리), 그리고 모델이 학습으로 아는 것이다. 결정문 머리에 `■ 봉인 실행` 줄이 찍힌다. 단발 심의에만 선다(sim-plan·test-plan·build-plan 은 거절한다). 이어하기(`deliberate_continue`)는 봉인을 이어받고 풀 수 없다. 다만 처음에 넣은 `evidence` 는 이어받지 않는다 — 이어하는 회차의 좌석은 이전 결정문과 사람 의견만 본다. 근거를 다시 보여야 하면 새 심의로 시작한다 |
| 저장 | 저장 없이 돈 심의는 이어가도 저장하지 않는다. 켜려면 이어하기에 `advanced={"save_report": 1}` 을 준다 |
| 동시 실행 | 상한에 걸리면 `queued` 로 줄을 서고 순번을 알려 준다. 상태는 `queued` → `running` → 끝 |
| 내 심의만 | 목록(`deliberate_list`)에는 내가 시작한 심의와 주인이 안 적힌 옛 심의만 실리고(남의 것은 `running`·`queued` 수로만 보인다) 남의 심의는 접을 수 없다. 신원 없이 부르는 서비스 계정 호출은 종전대로 전부 본다 |
| 걸리는 시간 | 좌석이 많은 심의는 몇 시간 걸린다. 심의 전체에 거는 시간 제한은 없다 — 호출 하나하나에만 걸린다. 시작한 뒤 곧바로 다시 묻지 말고 `job_id` 를 적어 둔다 |
| 조용한 잡 | `deliberate_status` 의 `idle_s`(마지막 이벤트 뒤 초)가 `quiet_ok_s` 안이면 멈춘 것이 아니다 — 다시 시작하지 않는다(같은 심의가 나란히 돈다). 넘었다고 멈춘 것도 아니다(자유 조회 단계는 더 길게 조용하다). `last_step` 이 마지막으로 일어난 일이다. 그만두려면 `deliberate_cancel` 이다. `quiet_ok_s` 가 `null` 이면 그 서버가 호출 한도를 꺼 둔 것이다 |
| `timeout_s` | `advanced={"timeout_s": …}` 는 **LLM 호출 한 번**의 한도다(심의 전체가 아니다). 10 ~ `DELIB_TIMEOUT_MAX_S`(기본 14400)초로 받고, 범위 밖이면 가까운 끝값으로 돌며 `evidence_omitted` 에 뜬다. 비우면 서버 기본값이다 — 지금 값과 상한은 `deliberate_jobs` 의 `limits.timeout_s_default`·`limits.timeout_s_max` 다. 이어하기가 이어받는다. 포털을 거치는 웹 경로(`delib_opts.timeout_s`)는 14400 을 넘는 값을 422 로 거절한다(화면 입력은 14400 까지다) |
| 좌석이 빠짐 | 상태줄과 `evidence_omitted` 에 `N라운드 좌석 유실 — … LLM 호출이 N초 안에 끝나지 않았다(…)` 가 뜨면 그 좌석이 호출 한도에 걸린 것이다. 라운드나 좌석을 줄이지 않는다 — `timeout_s` 를 올려 다시 돌리거나 운영자에게 서버 기본값(`DELIB_TIMEOUT_S`)을 올려 달라고 한다 |
| 의장 실패 | 의장이 끝내 결정문을 내지 못하면 스트림은 오류 코드 `chair_failed` 로 끝나고 MCP 잡은 `status: error` 다(`error` 가 `의장이 결정문을 내지 못했다 — …` 로 시작한다). 라운드는 버리지 않는다 — 좌석별 마지막 입장이 결과로 내려오고 회의록·보고서가 남는다. `timeout_s` 를 올려 `deliberate_continue` 로 이으면 결정문을 받는다(종전에는 전 라운드가 버려졌다) |
| 끊긴 화면 | 웹 화면은 도는 동안 `서버 살아 있음 · 마지막 진행 N분 전` 을 보이고, 끊기면 `스트림이 끊겼습니다 — … 심의는 서버에서 계속 돌 수 있습니다` 로 알린다. 다시 시도하면 두 번째 심의가 나란히 돈다 — 결과를 Report Archive 와 대화 목록에서 먼저 찾는다 |

## 6. 아직 안 된 것

| 무엇 | 사정 |
|---|---|
| 끊긴 웹 심의의 결과 회수·취소 | 웹 화면에서 시작한 심의는 잡 원장에 없다. 스트림이 끊긴 뒤의 결과는 Report Archive 와 대화 목록에서만 찾고, 서버에서 도는 것을 멈출 길이 없다. 리스크 앱의 취소·일시정지도 앱 쪽 구독만 닫는다 — 엔진은 그 심의를 끝까지 돌린다. 다음 묶음이다 |
| 리스크 잡이 멈춤(`paused`)으로 남음 | 패널이 `panel_timeout`(벽시계 12시간) · `engine_silent` · `engine_stream_cut` · `engine_busy`(포털의 자리를 3600초 기다렸다) · `chair_failed` · `restart`(앱이 다시 떴다)로 닫히면, 좌석 재시도를 깎지 않고 잡을 멈춘다(사유는 잡의 오류 문구에 있다). 스스로 다시 돌지 않는다 — 사람이 재개한다. 엔진은 첫 심의를 계속 돌리고 있을 수 있어, 곧바로 재개하면 같은 좌석으로 두 번째가 나란히 돈다. `chair_failed` 면 재개 전에 에이전트서버의 `DELIB_TIMEOUT_S` 를 올린다(§4-8) |
| 리스크 심사 화면의 '마지막 신호' | 서버는 도는 패널의 마지막 신호를 준다(`risk_get_coverage` 의 `job.signal`). 화면이 아직 그리지 않아, 화면에서는 도는 패널과 멈춘 패널이 똑같이 `running` 이다 |
| 리스크 앱의 프로세스 잠금 | 허브가 앱 서버를 하나 더 띄우면 둘째 프로세스가 도는 패널을 `restart` 로 닫을 수 있다. 데이터 디렉터리 잠금은 아직 없다 |
| KooRemapper·HEAX Hub 의 시간 제한 넷 | DynaForge MCP 가 제 REST 를 60초만 기다린다 · 전처리 잡의 벽시계가 1800초다 · 허브의 앱 인가 요청에 한도가 없다 · 허브가 생사 탐침을 한 번 놓치면 앱 서버를 하나 더 띄운다. 넷 다 종전 그대로다(허브 재기동이 필요해 따로 올린다) |
| 심의 보호가 닿지 않는 재기동 | update-all 이 미루는 것은 포털·nginx·에이전트서버 재기동과 게이트웨이 재프로비저닝이다. 게이트웨이(코드가 바뀐 실행)와 HEAX Hub 의 앱 교체(hwax-risk 새 SIF)는 심의가 돌아도 다시 뜬다 — 그 순간의 좌석 도구 호출이 실패하고, 도는 리스크 패널은 `restart` 로 닫힌다. 인자 없는 `update-sites.sh` 의 포털 재기동과 손으로 내리는 것도 묻지 않는다 |
| ARP 로그아웃 | ARP 가 그 주소를 내는지 확인된 적이 없다. §3 에서 잰 숫자를 받은 뒤 정한다 |
| ODB 허브 타일 SSO(7-8) | ODB 가 `PORTAL_JWKS_URL` 을 켠 뒤 |
| `as_of` 날짜 컷오프 | 걸 수 있는 문서 날짜가 없다(색인일뿐이다). 지식카드를 어떻게 볼지 정한 뒤 |
| 위임 경로의 `X-Workspace-Slug` | RA 가 "헤더 없으면 홈 부서" 를 보장하는 것이 확인되면 포털도 뺀다. 확인되면 dev 에 알린다 |
| id 를 아는 사람이 남의 심의를 읽는 것 | 막을지 정해야 한다(운영자가 남의 심의를 들여다보는 쓰임이 있을 수 있다) |

## 7. 되돌리기

반영 명령은 §4-0 표의 것이다.

- 소속 매핑 — `access.local.yaml` 의 `sso_affiliation_map` 을 지우면 끝이다(반영 명령 없음). 이미 지정된 소속은 관리자 화면에서 고친다.
- 고정 관리자 — `PORTAL_ADMIN_EMAILS` 에서 빼고 반영한다. 그 사람이 원장에도 관리자면(사용자 관리의 관리자 스위치가 켜져 있다) 여전히 관리자다 — 목록에서 뺀 **뒤에** 그 스위치를 끈다. 목록에 있는 동안에는 화면에서 끌 수 없다.
- 사번 검사 — `SAML_ATTR_SABUN` 값을 비우고 반영한다.
- 대기 줄 — 에이전트서버 `.env` 에 `DELIB_JOB_QUEUE_MAX=0` 을 적고 반영한다. 종전처럼 상한에서 거절한다.
- 일반 앱의 사람별 위임 — 4-2 의 `PER_USER_SSO_APPS` 칸에 적은 대로 끈다.
- 심의 호출 한도 — 에이전트서버 `.env` 의 `DELIB_TIMEOUT_S` 를 종전 값으로 적고 반영한다. 키트를 받은 박스의 종전은 600, 줄이 없던 박스의 종전은 `LLM_TIMEOUT_S` 에 적어 둔 값이고 그것도 없었으면 `0`(한도 없음)이다. 0 이면 멈춘 호출 하나가 심의 자리를 끝없이 붙들고(기동 로그에 `[agent] ⚠ DELIB_TIMEOUT_S=0` 이 남는다) `quiet_ok_s` 가 `null` 이 된다.
- heartbeat — `DELIB_HEARTBEAT_S=0` 이 종전(신호 없음)이지만 되돌리지 않는다. 끄면 일어나는 일은 §4-8 에 있다 — 끌 까닭이 있으면 먼저 dev 에 알린다.
- 챗 토큰 수명 — 종전(30~60분)은 `infra/.env` 의 `CHAT_PAT_TTL_S=3600` 이다. 그보다 오래 도는 심의가 도는 중에 자격을 잃고(조회·저장이 서비스 계정으로 간다) `/health/ready` 의 `temporary` 에 `chat_pat_ttl` 이 계속 뜬다. 줄이더라도 46800 밑으로는 내리지 않는다.
- 리스크 패널 벽시계 — 종전(40분)으로는 이 박스에서 되돌릴 수 없다(§4-8 의 hwax-risk 줄). 필요하면 dev 에 알린다. 벽시계에 걸린 패널은 이제 좌석을 깎지 않고 잡을 멈추므로(§6) 재개하면 이어 돈다.
- 심의 보호 — 설정으로 끄지 않는다. 미루지 않고 끊어야 하는 실행에만 `AGENT_RESTART_FORCE=1` 을 붙인다(§4-0).
- 워치독 — AIDataHub `deploy/apptainer/.env` 에 `AIDH_WATCHDOG_TIMEOUT_STRIKES=1` 을 적으면 종전처럼 첫 판정에 API 를 다시 띄운다(다음 분부터 먹는다).
- ARP 타일 — 이 박스에서 포털 리포를 옛 커밋으로 되돌리지 않는다(다음 update-all 이 원격 최신으로 다시 맞춘다). 끄려면 `backend/config/routes.local.env` 의 `aireadyportal=` 줄을 `#` 로 막고 `./infra/scripts/update-forges.sh portal` 을 돌린다 — 타일이 숨고 토큰이 나가지 않는다. 그동안 직결 링크가 필요하면 §4-4 의 임시 타일을 쓴다. 직결 링크로 완전히 되돌리는 것은 dev 가 되돌림 커밋과 프론트 빌드를 올린 뒤의 일이다.
