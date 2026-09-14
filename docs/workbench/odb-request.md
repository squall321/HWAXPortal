# cae00 에서 받아 올 것 — ODB 허브 API 정보

워크벤치 [S3(ODB 어댑터)](checklist.md) 를 설계하려면 cae00 `odb-hub` 가 **무엇을 내주는지**
알아야 한다. dev 에서는 알 방법이 없다.

| 왜 dev 에서 못 하나 | |
|---|---|
| 게이트웨이 도구 465종 중 odb **0종** | 실제로 세어 확인했다 |
| odb-hub 주소(`backend/config/systems.yaml` 의 odb-hub `url`) | dev 에서 차단(`http=000`) |
| 소스가 이 박스에 없다 | 스키마를 읽어서 알 수 없다 |
| 페르소나 `he-cad-odbhub` 의 `key_tools` 가 비어 있다 | **도구 이름조차 모른다** |

**이 문서 하나만 보고 cae00 에서 실행할 수 있게** 썼다. 계획 전체는 [PLAN.md](PLAN.md).

소요 — 30분 안팎. §1·§2 는 데이터를 바꾸지 않는다. §3 은 아래 **읽기 게이트가 막는 범위 안에서만**
그렇다 — 스크립트가 게이트웨이 서비스 토큰으로 도구를 직접 부르므로 문장이 아니라 게이트가
지켜야 한다.

---

## 0. 먼저 — 프록시, 결과를 둘 곳, 지울 것

```bash
# 사내 프록시가 127.0.0.1:9110 호출을 가로채 curl 000 이 난다 — update-all.sh:25-27 과 같은 처치
export NO_PROXY="127.0.0.1,localhost,::1${NO_PROXY:+,$NO_PROXY}"; export no_proxy="$NO_PROXY"

RAW=~/odb-hub-raw; mkdir -p "$RAW"                      # 원본은 리포 밖에 받는다
mkdir -p ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub   # 지운 뒤에만 여기로(§3½)
```

원본은 `$RAW` 에 받고, §3½ 에서 지운 것만 `fixtures/odb-hub/` 에 두고 **커밋해서 dev 로
넘긴다.** 이게 dev 에서 어댑터를 만드는 재료다.

> ⚠ **지우고 넣을 것** — 내부 IP·토큰 · 파일 경로(`/home/<id>`, `/data/<과제>`) · 잡 ID·프로젝트명 ·
> 이메일·사번 · 고객사명·미공개 과제명 · error 문자열 안의 `input_value=` 되비침. 표본은 `result`
> 만이 아니라 **`args` 와 `error` 칸도** 본다. 이 리포는 GitHub 에 있다.
> 좌표·치수·층 구조 같은 **형상 수치는 그대로 둬도 된다**(그게 정작 필요한 것이다).

---

## 1. 도구 목록과 스키마 ← **가장 중요**

게이트웨이는 다른 백엔드와 이름이 겹칠 때만 접두어를 붙인다. 허브 도구가 `list_jobs`·`get_board`
처럼 bare 이름이면 `"odb" in name` 필터로는 겹치는 것만 잡힌다. 그래서 **§2 를 먼저 돌려 앱 키를
알아낸 뒤** 그 키로 고른다.

```bash
cd ~/Projects/HWAXAgentServer
ODB_APP=<§2 에서 찾은 앱 키>       # 예: odb-hub
.venv/bin/python - "$ODB_APP" <<'PY' > "$RAW/tools.json"
import asyncio, json, sys, datetime, urllib.request
from langchain_mcp_adapters.client import MultiServerMCPClient

APP = sys.argv[1]
CONF = json.load(open("mcp_servers.json"))
TM = json.load(urllib.request.urlopen("http://127.0.0.1:9110/tools-map"))
MAP = TM.get("map") or {}                        # 노출 이름 → 앱 키(무인증·무필터)

async def main():
    tools = await MultiServerMCPClient(CONF).get_tools()
    hit = [t for t in tools if MAP.get(t.name) == APP]
    pre = APP.replace("-", "") + "_"
    out = [{"exposed_name": t.name,
            "backend": APP,
            "original": t.name[len(pre):] if t.name.startswith(pre) else t.name,
            "description": t.description or "",
            "args_schema": getattr(t, "args_schema", None),
            "metadata": getattr(t, "metadata", None),      # annotations(readOnlyHint 등)가 있으면 여기
            "paged": any(k in (getattr(t, "args_schema", None) or {}).get("properties", {})
                         for k in ("limit", "offset", "cursor", "page"))} for t in hit]
    print(json.dumps({"collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
                      "total_tools": len(tools), "app": APP, "odb_tools": len(hit), "tools": out},
                     ensure_ascii=False, indent=2, default=str))

asyncio.run(main())
PY
head -30 "$RAW/tools.json"
```

**확인할 것.** `odb_tools` 가 0이면 바로 "안 붙어 있다" 로 결론 내지 말고 §2 의 `apps` 배열을
본다 — 0에는 세 뜻이 있다.

- (a) `apps` 에 odb 허브 항목이 **없으면** 그 박스 게이트웨이에 **미등록**이다. 아래는 전부
  건너뛰고 **그 사실만 알려 주면 된다**(설계가 통째로 달라진다).
- (b) 항목은 있는데 `tool_count` 0 · `reachable` false 면 **등록됐지만 불통**이다(게이트웨이가
  집계 시점에 세션 없는 백엔드를 건너뛴다). 허브를 살린 뒤 §1 을 다시 돌린다.
- (c) 항목이 있고 `tool_count` 도 0이 아니면 `mcp_servers.json` 의 토큰이 권한 필터에 걸린 것이다
  (`tools/list` 는 호출자 그룹으로 거른다, `/tools-map` 은 무필터). `infra/scripts/update-all.sh`
  의 토큰 정합 검사가 무엇을 말하는지 본다.

---

## 2. 앱 키 확인 ← §1 보다 먼저

```bash
curl -s http://127.0.0.1:9110/tools-map | python3 -c "
import sys, json
from collections import Counter
d = json.load(sys.stdin); m = d.get('map') or {}
print('전체', len(m), '종')
for app, n in Counter(m.values()).most_common():
    mark = '  ← 이것인가?' if any(k in app.lower() for k in ('odb', 'ecad', 'pcb')) else ''
    print(f'  {app:34} {n:3}{mark}')
print('--- apps ---')
for a in d.get('apps', []):
    print(f\"  {a.get('app',''):34} {a.get('tool_count'):3}  reachable={a.get('reachable')}\")
" | tee "$RAW/apps.txt"
```

`apps` 배열이 §1 의 (a)/(b) 를 가른다.

**사용자 PAT 로 한 번 더.** 워크벤치 실행기는 위 서비스 토큰이 아니라 **사용자 명의 PAT** 로
게이트웨이를 부른다(PLAN §3). 서비스 시야에서 보이던 허브도 사용자에게 `plat:odbhub` 가 없으면
사라진다. 포털 `/auth/pat` 로 발급한 개인 PAT 로 `list_tool_apps` 를 한 번 부른다.

```bash
PAT=<개인 PAT — 셸 변수로만, 파일에 적지 않는다>
curl -s http://127.0.0.1:9110/mcp -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_tool_apps","arguments":{"app":"'"$ODB_APP"'"}}}' \
  | head -c 600; echo
```

응답에 `error` 가 없으면 접근 가능, `no_access:` 로 시작하면 내 권한 페이지에서 odbhub 를 받아야
S3 실주행이 된다, `unknown app:` 이면 (a) 미등록이다. 결과를 **한 줄**로 `apps.txt` 끝에 적는다.
같은 자리에 허브 버전(`system_capabilities` 류 응답이나 웹 UI 의 버전 표기)도 한 줄 적는다 —
허브가 바뀌면 고정물이 조용히 낡는다.

---

## 3. 응답 표본 ← **두 번째로 중요**

스키마만으로는 **결과가 어떻게 생겼는지** 모른다. 어댑터는 결과에서 값을 꺼내는 일이라
표본이 없으면 만들 수가 없다.

`<도구명>` 과 인자는 §1 의 `tools.json` 을 보고 채운다. 규칙 셋.

- **무인자 읽기 도구는 전부 부른다**(`whoami`·`system_status`·`system_capabilities`·`list_*` 류) —
  가장 싸게 판본·도구 수·연결 힌트를 얻는 자리다. 스택의 다른 앱은 이 삼종을 관례로 둔다.
- **잡 정보 도구(`job_info`·`get_board` 류)를 첫 실호출로**, 부품 목록은 **IC 계열로 좁힌 호출**을
  반드시 넣는다(`category`·`side` 인자가 있으면). 부품 목록은 수천 개를 주지 "이 보드의 AP" 를 주지
  않는다.
- `extract`·`ratio`·`report` 류는 `tools.json` 의 설명을 먼저 읽어 잡 생성·파일 쓰기가 없다고 적혀
  있을 때만 부른다. 게이트가 이름으로 거르지 못하는 것은 사람이 거른다.

```bash
cd ~/Projects/HWAXAgentServer
.venv/bin/python - <<'PY' > "$RAW/samples.json"
import asyncio, json, re, time
from langchain_mcp_adapters.client import MultiServerMCPClient

CONF = json.load(open("mcp_servers.json"))

# ── 여기를 채운다. 실제 도구명(§1 의 exposed_name)과 인자로 바꿀 것 ──────────────
CALLS = [
    # 1) 무인자 읽기 도구 전부
    # ("whoami",               {}),
    # ("system_capabilities",  {}),
    # ("list_jobs",            {}),
    # 2) 잡 정보 — 첫 실호출
    # ("job_info",             {"job_id": "<실제 job_id>"}),
    # 3) 부품 목록 — IC 계열로 좁혀서
    # ("list_components",      {"job_id": "<실제 job_id>", "category": "IC"}),
    # 4) 적층·보드 정보(있으면) — 워피지 3인자의 원천
    # ("get_stackup",          {"job_id": "<실제 job_id>"}),
    # 5) 과제명·리비전으로 필터한 목록(그런 인자가 있으면)
    # 6) 고의 실패 둘 — 없는 잡, 없는 레이어(읽기 전용이라 안전하다)
    # ("job_info",             {"job_id": "0000000000000000"}),
    # ("list_nets",            {"job_id": "<실제 job_id>", "layer": "no_such_layer"}),
]
# ────────────────────────────────────────────────────────────────────────────

# 읽기 전용 게이트 — 이름에 이 단어가 들면 부르지 않는다
DENY = ("ingest", "delete", "remove", "create", "update", "set_", "upload",
        "submit", "run_", "cancel", "purge", "import", "register")

def _text(content):
    # 코루틴은 (content, artifact) 튜플을 준다. content 는 {"type":"text","text":…} 블록 리스트다.
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text")

def _redact(s):
    s = re.sub(r"token=[^&\s\"']+", "token=<redacted>", s)
    return re.sub(r"Bearer\s+\S+", "Bearer <redacted>", s)

async def main():
    tools = {t.name: t for t in await MultiServerMCPClient(CONF).get_tools()}
    out = []
    for name, args in CALLS:
        if any(w in name.lower() for w in DENY):
            out.append({"tool": name, "args": args, "skipped": "not read-only"}); continue
        t = tools.get(name)
        if t is None:
            out.append({"tool": name, "args": args, "error": "not found"}); continue
        t0 = time.perf_counter()
        try:
            # ⚠ t.ainvoke(args) 로 바꾸지 말 것 — MCP 오류(isError)가 정상 결과 모양으로 둔갑한다
            content, artifact = await t.coroutine(**args)
            text = _text(content)
            try:
                result = json.loads(text)      # 응답은 대개 JSON — 구조 그대로 저장(절단 없음)
            except ValueError:
                result = text[:20000]          # JSON 이 아닐 때만 자른다
            rec = {"tool": name, "args": args, "ms": int((time.perf_counter() - t0) * 1000),
                   "bytes": len(text), "is_error": False, "result": result}
            sc = getattr(artifact, "structured_content", None) if artifact else None
            if sc is not None:
                rec["structured_content"] = sc
        except Exception as e:                 # MCP isError → 예외로 여기에 온다
            rec = {"tool": name, "args": args, "ms": int((time.perf_counter() - t0) * 1000),
                   "is_error": True, "error": _redact(f"{type(e).__name__}: {e}")}
        out.append(rec)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

asyncio.run(main())
PY
```

`result` 는 도구가 준 JSON 을 그대로 푼 객체이고, 도구가 오류를 냈으면 `error` 로 남는다(둘 중
하나만 있다). **오류도 표본이니 지우지 말 것** — 허브가 예외형(isError)인지 봉투형(`{ok:false,
error:{code,message}}` 를 정상 응답으로)인지가 여기서 갈린다. 봉투 모양이면 그대로 둔다.

**120초 넘게 걸리는 도구가 있으면** 게이트웨이가 호출당 타임아웃(`GATEWAY_CALL_TIMEOUT`, 기본
120초)으로 끊어 그 항목이 `error`(`backend … unavailable: …`)로 남는다. 클라이언트 read
타임아웃은 300초라 스크립트가 먼저 끊지 않는다. **지우거나 재시도하지 말고 그대로 둔다** — 그
항목이 §5 의 "오래 걸리는 도구" 답이다.

**잡이 하나도 없으면** 목록 도구의 빈 응답만이라도 보내 준다 — 빈 것과 실패를 어떻게 구분하는지가
어댑터 설계에 필요하다.

응답의 `artifacts`·`uri`·`path`·`odb://` 류 필드는 JSON 이면 절단 없이 남는다. 그것을 **받는
도구**(`download`·`fetch`·`read` 류)가 있으면 가장 작은 아티팩트 하나로 실호출해 응답 모양
(base64/text/URL)과 크기 상한을 적는다 — 스택 선례는 StepForge `download_artifact`(base64, 상한
1,000,000 바이트, 넘으면 `too_large`+`rest_path`)와 KooRemapper `download_result`(5 MiB)다. 받는
도구가 없으면 웹 UI 의 다운로드 URL 형태와 그 URL 이 토큰 없이 열리는지 적는다.

---

## 3½. 지우기 — 그 다음에만 리포로

```bash
python3 - <<'PY'
import re, os, glob
RAW = os.path.expanduser("~/odb-hub-raw")
DST = os.path.expanduser("~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub")
os.makedirs(DST, exist_ok=True)
RULES = [
    (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<ip>"),
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "<email>"),
    (r"token=[^&\s\"']+", "token=<redacted>"),
    (r"Bearer\s+\S+", "Bearer <redacted>"),
    (r"/home/[^/\s\"']+", "/home/<user>"),
]
for src in glob.glob(f"{RAW}/*"):
    s = open(src, encoding="utf-8").read()
    for pat, rep in RULES:
        s = re.sub(pat, rep, s)
    open(os.path.join(DST, os.path.basename(src)), "w", encoding="utf-8").write(s)
    print("scrubbed", os.path.basename(src))
PY

cd ~/Projects/HWAXPortal
# 통과 게이트 — 0건이어야 넘어간다. 아는 고객사명·과제명·사번 형식은 -e 로 더한다
grep -nE -e 'token=|Bearer |[0-9]{1,3}(\.[0-9]{1,3}){3}|@' -e '<고객사명>' -e '<미공개 과제명>' \
  docs/workbench/fixtures/odb-hub/* ; echo "exit=$?  (1 이면 통과)"
```

게이트웨이는 백엔드 오류를 예외 repr 그대로 돌려주고 odb-hub URL 은 `?token=` 쿼리를 달고 있어
오류 문자열에 토큰이 실릴 수 있다 — 그래서 §3 의 마스킹과 이 게이트가 둘 다 있다.

`.gitignore` 에 `docs/workbench/fixtures/**/raw/` 한 줄을 넣어 리포 안에 raw 를 두더라도
안 잡히게 한다. 잡 ID·프로젝트명·고객사명은 정규식으로 못 잡는다 — 사람이 본다.

---

## 4. 대조표 — 이게 이번 수집의 목적이다

열충격 SED(`predict_sed`)의 입력이다. ODB 가 이 중 몇 개를 실제로 채워 주는지가 S3 설계 전체를
가른다. **필수 10개는 게이트웨이 `predict_sed` 설명문 기준**이다 — JSON 스키마엔 `sample: object`
만 있어 `tools.json` 의 `required` 로는 대조가 안 된다. 정본은 `ThermalShockMCP/app/schemas.py`
`SedInput`. 2026-09-14 dev 게이트웨이(모델 v20260719_112422, 294건)로 대조했다.

| # | SED 필수 입력 | 형태·단위 | 요약에 있나 / 아티팩트에만 있나 | 어느 ODB 도구가 주나 | 값 예 |
|---|---|---|---|---|---|
| 1 | `board_type` | `INT`(인터포저) / `HALF`(단면 실장) / `FULL`(양면 실장) | | 힌트 — 인터포저 여부 + 부품이 한 면에만 있는지(부품 목록의 side 값). 인터포저 비율 하나로는 INT 만 가려진다 | |
| 2 | `ap_cx` | 수치(보드 좌표계, **mm 추정** — 소스 단위 미표기, 학습 데이터가 mm 스케일) | | | |
| 3 | `ap_cy` | 수치 | | | |
| 4 | `pkg_cx` | 수치 | | | |
| 5 | `pkg_cy` | 수치 | | | |
| 6 | `pkg_x` | 수치(mm, >0, 학습범위 2.35~6.4) | | | |
| 7 | `pkg_y` | 수치(mm, >0, 학습범위 2.4~6.05) | | | |
| 8 | `ball_size` | `"직경/피치"` 문자열, **정수 2~3자리씩**(정규식 `^\d{2,3}/\d{2,3}$` — 소수·mm 값 거부). 단위는 소스에 없고 값으로 보아 µm. 학습값 130/230·147/250·157/260·167/270·130/275 | | ODB 가 mm 로 주면 어댑터가 µm 정수 문자열로 환산 | |
| 9 | `pad_size` | 수치(>0, 단위 미확인 — µm 추정). 180~240 은 검증 범위가 아니라 **학습범위**, 밖이면 거부가 아니라 외삽 경고 | | | |
| 10 | `pkg_type` | `WLP` / `FX` / `DIG` | | **아마 없음** — 패키지 기술 분류 | |

모델은 **AP·PKG 중심의 차이만** 쓴다(중심 절대좌표는 보드 좌표계가 과제마다 달라 사용하지
않는다). 원점은 상관없지만 두 중심이 **같은 좌표계·같은 단위**여야 하고, AP–PKG 거리 14 mm 초과는
외삽 경고가 난다.

**선택 입력 5개** — 함께 대조한다.

| 입력 | 형태 | 메모 |
|---|---|---|
| `ap_x`·`ap_y` | 수치(mm, >0). 학습범위 8.0~15.6 / 9.5~15.6 | 비우면 중앙값 대치 + `ap_size_known=0`. AP 부품 bbox 에서 나오면 채운다 |
| `ap_type` | `POP` / `FO`, 기본 `POP` | 형상에서 유도 불가. 학습 294건 전부 POP 이라 당분간 기본값(FO 는 외삽 경고) |
| `project`·`pkg` | 문자열 메타, 기본 `"unknown"` | 레시피의 과제 키를 여기 싣는다 |

**설계 가정** — 사람이 채우는 칸은 `pkg_type` 하나이고 `ap_type` 은 기본값을 쓴다. 맞는지
확인하는 것이 목적이다. 틀리면 사람이 채우는 칸이 늘 뿐이고 **계획이 깨지지는 않는다**.

이 표를 `fixtures/odb-hub/sed-mapping.md` 로 채워 주면 된다. **"없다" 도 답이다.** 아래 문항도
같은 파일에 적는다.

### 부품 선별 — AP 와 PKG 를 어떻게 고르나

부품 목록 도구는 보드의 부품 **전부**를 주지 "이 보드의 AP" 를 주지 않는다. 표본 보드에서 AP 는
어느 refdes 이고 PKG(메모리 또는 PoP 상단)는 어느 refdes 인가 — 그 부품의 `refdes`·`part_number`·
`footprint`·`pin_count` 행을 그대로 적는다. 이름으로 고를 수 있는 **사내 규칙**(refdes 접두·부품명
패턴)이 있나. `ap_type` 이 POP 일 때 상단 패키지가 ODB 부품 목록에 존재하나 — 없으면 `pkg_c*` 는
AP 좌표에 사람이 주는 오프셋을 더한 값이 된다.

### `board_type` 어휘

ODB 쪽 `board_type` 은 ingest 때 사람이 넣는 자유 문자열일 가능성이 높다. 실제 잡의 값 예시 3개,
`INT`/`HALF`/`FULL` 과 일대일인지, 아니면 판정에 필요한 수치(면별 부품 수·인터포저 부품 수)를 주는
도구가 있는지. 어휘가 다르거나 판정 규칙을 사람이 정해야 하면 그 규칙을 적고 1행은 "사람이
채운다" 로 분류한다.

### 품질 플래그

응답에 `warnings` 류 배열이 있나, 이름은 무엇인가. 잡이 EDA·부품 데이터를 갖는지 알리는 필드
(`has_eda`·`data_type`·`component_count` 류)가 있나. 가능하면 **EDA 가 없는 잡 하나**의 잡 정보
표본도 함께 — 어댑터가 값을 채우기 전에 걸러야 할 것이 이것이다.

### 쓰기·파괴 도구 표

| 도구명 | 무엇을 바꾸나 | 되돌릴 수 있나 | annotations 에 hint 가 있나 |
|---|---|---|---|

이 표가 워크벤치 저장 시점 거절 목록의 **odb 쪽 정본**이다 — 게이트웨이 접두 관문은 원본 이름의
`delete_`·`remove_` 접두만 보므로 `odb_delete_job` 같은 앱 접두 이름은 하나도 걸리지 않는다.
허브 웹 UI 의 삭제·메타 수정 기능이 MCP 로도 노출되는지도 한 줄.

### 덤으로 — 워피지도 같이 본다

`pcb_warpage_surrogate`(ai-data-hub) 의 입력이다. 게이트웨이 스키마엔 인자 설명이 없다(title/type
만). 단위·학습범위는 이 표가 정본이고 출처는 `ExpertAgents/examples/surrogate_pcb_warpage/spec.yaml`
이다. 학습범위 밖은 `out_of_domain` 경고가 붙는다.

| 입력 | 형태 | 어느 ODB 도구가 주나 |
|---|---|---|
| `copper_imbalance_pct` | %, 상하 대칭 대비 잔존 동박 면적 차이, 학습범위 0~40 | (동박률 계열?) |
| `stackup_asymmetry` | 0~1 지수(0=완전 대칭). **계산 정의가 없다** → ODB 적층 원자료(층별 두께·재질·동박)를 표본으로 받고 산식은 dev 에서 정한다 | (적층 계열?) |
| `board_thickness_mm` | mm, 0.6~1.6, 적층 총두께 | (적층 계열?) |
| `diagonal_mm`(선택, 기본 140) | mm, 80~200, 보드 외곽 대각 | ODB 가 줄 수 있으면 |
| `peak_temp_c`(선택, 기본 245) | °C, 230~260 | 공정값 — 사람 칸 |

적층 도구가 있으면 `layers` 표본(두께·구리량·type 어휘)이 `board_thickness_mm`·`stackup_asymmetry`
의 원천이다 — §3 CALLS 에 넣는다.

---

## 5. 마지막 — 메모

표본에서 안 드러나는 것들이라 글로 적어 주는 편이 빠르다.

- **잡(job) 수명·식별** — `ingest` 로 만든 잡이 얼마나 남나? 서버 재기동에도 사나? 잡 ID 가 내용
  해시(같은 파일을 다시 넣으면 같은 ID)인가 무작위인가. 잡 메타에 과제명·모델·리비전 필드가 있나,
  목록 도구가 그것으로 필터되나(있으면 §3 에 필터 호출 한 건). 두 잡을 비교하는 도구가 있나.
  (레시피가 잡 ID 를 변수로 들고 다닐지, 과제명+리비전으로 둘지가 여기서 갈린다)
- **파일을 어떻게 주나** — `ingest` 인자가 경로면 **어느 머신 기준**인가(허브 호스트인가 cae00 포털
  컨테이너인가), 허용 디렉토리는 어디인가, 포털·cae00 과 공유되는 디렉토리가 있나(있으면 마운트
  경로). 경로가 아니면 웹 UI 업로드의 REST 엔드포인트·인증 방식·용량 상한. `*upload_instructions`
  류 안내 도구가 있으면 그 응답도 `samples.json` 에. 포털 업로드 스테이징은 6시간 뒤 지워지고 호스트
  경로 전제라 레시피가 그 경로를 들고 다닐 수 없다 — 미리 올려 둔 것을 참조하는 방식이면 그 참조
  키가 레시피 변수가 된다.
- **오래 걸리는 도구가 있나** — 잡 상태 도구(`job_status`·`get_job` 류)가 따로 있나. 분석 도구가
  즉시 job_id 를 주고 끝나나, 결과를 다 만들고 돌아오나. §3 에서 가장 오래 걸린 도구와 ms, 120초로
  끊긴 도구 이름. **상태 도구의 정확한 이름** — 이름이 `get_`·`list_`·`describe_` 로 시작하면
  게이트웨이가 결과를 300초 캐시해 상태 조회 단계를 다시 눌러도 5분간 첫 응답이 그대로 돌아온다.
  `job_status`·`*_status` 처럼 비캐시 이름이 따로 있는지도 적어 달라.
- **에러 코드 어휘** — 표본에서 본 `code` 값과, 회복 가능(재시도)·불가(예: NO_EDA_DATA·
  NO_COMPONENTS) 구분.
- **목록 상한과 절단 표시** — 부품·넷 목록에 서버 상한이 있나(예 500건), 넘치면 어느 필드로 알리나
  (`count`·`total`·`next_offset`·`truncated`·`warnings` 중 무엇).
- **단위와 면** — 좌표·치수 단위를 허브가 어느 필드로 선언하나(mm 인지 inch 인지, 잡마다 다른지).
  bottom 면 부품 좌표가 top 과 같은 프레임인지 미러인지, side 값 어휘는 무엇인지(양면 실장에서 AP 와
  PKG 가 다른 면이면 차이 계산이 달라진다). 레이어 JSON 의 `"units":"INCH"` 같은 심볼 해석용 힌트가
  좌표 단위로 오해될 여지가 있는지.
- **시야와 쓰기 명의** — odb-hub 는 게이트웨이에 **서비스 토큰 하나**로 붙어 있어 포털의 사용자
  위임 세 갈래 어디에도 들지 않는다. 워크벤치가 사용자 PAT 로 불러도 허브에는 늘 토큰 주인의
  신원으로 간다. `whoami` 류가 있으면 결과를 남기고, 게이트웨이로 부른 잡 목록 개수와 웹 UI 에
  로그인해 보이는 잡 개수를 나란히 적는다 — 둘이 다르면 사용자별 스코프이고 그때 목록 도구의 빈
  배열은 부재 증거가 아니다. 웹 UI 의 기존 잡에서 `uploaded_by` 가 어떤 값(사번·이메일·고정
  문자열)인지 한 줄.
- **resources** — 허브가 MCP resources(`odb://`)를 노출하나. 노출해도 게이트웨이는 tools 만
  중계하고 resources 핸들러가 없으므로 S3 는 도구·REST 로만 간다.

---

## 6. 커밋·push — 이 사이에 `update-all` 을 돌리지 마라

```bash
cd ~/Projects/HWAXPortal
git add docs/workbench/fixtures/odb-hub/tools.json docs/workbench/fixtures/odb-hub/apps.txt \
        docs/workbench/fixtures/odb-hub/samples.json docs/workbench/fixtures/odb-hub/sed-mapping.md
git commit -m "fixtures(odb-hub): cae00 수집"
git push origin main
```

`git add` 는 **파일 단위**다(gotchas §2 의 `git add docs/` 사고). `infra/scripts/update-all.sh` 는
`git stash push -u` 뒤 `git reset --hard origin/<branch>` 를 하므로 push 전에 돌리면 미추적
fixtures 는 stash 로 치워지고 미푸시 커밋은 HEAD 에서 떨어진다(복구는 `git stash pop`·reflog).
push 가 안 되면 `git format-patch -1` 로 만든 패치를 Drive 로 나른다.

---

## 받은 뒤에 dev 에서 할 일

1. `fixtures/odb-hub/` 를 고정물로 삼아 **SedInput 어댑터**를 만든다. 키 15개(필수 10·선택 5) 외에는
   아무것도 `sample` 에 넣지 않는다 — 게이트웨이 스키마의 `additionalProperties: true` 는 믿지 마라.
   서버는 `extra="forbid"` 라 ODB 에서 딸려 온 키가 하나라도 섞이면 E100 으로 통째로 거부한다.
   품질 플래그는 선행 검사로 두고 걸리면 값을 채우지 않고 사유를 런 기록 `notes` 에 남긴다.
2. 허브가 예외형인지 봉투형인지를 표본으로 정한다. 봉투형이면 S1 실행기의 단계 판정 규칙(PLAN §5-6)이
   그것을 실패로 친다.
3. `sed-mapping.md` 의 빈 칸을 레시피 **변수**로 옮긴다(`why` 에 왜 물어보는지). 선별 규칙이 없으면
   `ap_refdes`·`pkg_refdes` 는 `pkg_type` 과 같은 영구 변수다.
4. 레시피는 노출 이름이 아니라 `backend`+`original` 로 저장한다(PLAN §5-8).
5. 쓰기·파괴 도구 표를 워크벤치 저장 시점 거절 목록의 odb 쪽 정본으로 쓴다.
6. `predict_sed_batch` 는 S4 일괄 재생에 쓰지 않는다 — 검증이 전부-아니면-전무라 한 건만 틀려도 결과
   0건이고 과제별 건너뛰기가 안 되며, 응답 모양도 단건 `data` 와 달리 `data.n`+`data.results[]` 다.
   S4 는 런당 `predict_sed` 를 유지한다.
7. `tools.json` 의 도구명을 `HWAXRisk/docs/odb-adapter-contract.md` 의 4도구(`odb_get_board`·
   `odb_list_components`·`odb_list_nets`·`odb_get_stackup`)와 대조해 있음/다른 이름/없음을
   `sed-mapping.md` 에 적고, 다르면 계약 개정을 HWAXRisk 쪽 일감으로 남긴다(같은 허브를 두 어댑터가
   다른 필드명으로 읽지 않게).
8. ODB 잡 메타에 과제 필드가 있으면 S2 매핑표에 ODB 열을 더한다.
9. 허브가 사용자별 스코프면 "S3 는 토큰 주인 시야로만 돌고 감사 귀속도 그 사람으로 찍힌다" 를
   context-notes 에 적는다. 사용자 위임 편입은 v1 밖 별도 결정(PLAN §7 #9).
10. dev 에서는 ODB 단계가 "사람이 채우는 칸" 으로 내려간 상태로 레시피를 완주시켜 본다.
    **실주행 검증은 cae00 에서** 한다.
