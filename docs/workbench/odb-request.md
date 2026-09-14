# cae00 에서 받아 올 것 — ODB 허브 API 정보

워크벤치 [S3(ODB 어댑터)](checklist.md) 를 설계하려면 cae00 `odb-hub` 가 **무엇을 내주는지**
알아야 한다. dev 에서는 알 방법이 없다.

| 왜 dev 에서 못 하나 | |
|---|---|
| 게이트웨이 도구 465종 중 odb **0종** | 실제로 세어 확인했다 |
| `10.252.38.121:8000` | dev 에서 차단(`http=000`) |
| 소스가 이 박스에 없다 | 스키마를 읽어서 알 수 없다 |
| 페르소나 `he-cad-odbhub` 의 `key_tools` 가 비어 있다 | **도구 이름조차 모른다** |

**이 문서 하나만 보고 cae00 에서 실행할 수 있게** 썼다. 계획 전체는 [PLAN.md](PLAN.md).

소요 — 30분 안팎. **읽기 전용이다.** 아래 어느 것도 데이터를 바꾸지 않는다.

---

## 0. 먼저 — 결과를 둘 곳

```bash
mkdir -p ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub
cd ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub
```

받은 파일은 여기에 두고 **커밋해서 dev 로 넘긴다.** 이게 dev 에서 어댑터를 만드는 재료다.

> ⚠ **지우고 넣을 것** — 내부 IP·토큰·사번·고객사명·미공개 과제명. 이 리포는 GitHub 에 있다.
> 좌표·치수·층 구조 같은 **형상 수치는 그대로 둬도 된다**(그게 정작 필요한 것이다).

---

## 1. 도구 목록과 스키마 ← **가장 중요**

게이트웨이에 붙어 `odb` 가 이름에 든 도구를 전부 덤프한다.

```bash
cd ~/Projects/HWAXAgentServer
.venv/bin/python - <<'PY' > ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub/tools.json
import asyncio, json
from langchain_mcp_adapters.client import MultiServerMCPClient

CONF = json.load(open("mcp_servers.json"))

async def main():
    tools = await MultiServerMCPClient(CONF).get_tools()
    hit = [t for t in tools if "odb" in t.name.lower()]
    out = [{"name": t.name,
            "description": t.description or "",
            "args_schema": getattr(t, "args_schema", None)} for t in hit]
    print(json.dumps({"total_tools": len(tools), "odb_tools": len(hit), "tools": out},
                     ensure_ascii=False, indent=2, default=str))

asyncio.run(main())
PY
head -30 ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub/tools.json
```

**확인할 것.** `odb_tools` 가 0이면 그 박스 게이트웨이에도 안 붙어 있다는 뜻이다 — 그러면
아래는 전부 건너뛰고 **그 사실만 알려 주면 된다**(설계가 통째로 달라진다).

`odb` 로 0건인데 허브는 붙어 있다면 이름 규칙이 다른 것이다. 그때는 앱 키로 찾는다(§2).

---

## 2. 앱 키 확인

어느 백엔드 키로 등록돼 있는지, 그 앱의 도구가 몇 종인지 본다.

```bash
curl -s http://127.0.0.1:9110/tools-map | python3 -c "
import sys, json
from collections import Counter
d = json.load(sys.stdin); m = d.get('map') or {}
print('전체', len(m), '종')
for app, n in Counter(m.values()).most_common():
    mark = '  ← 이것인가?' if any(k in app.lower() for k in ('odb', 'ecad', 'pcb')) else ''
    print(f'  {app:34} {n:3}{mark}')
" | tee ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub/apps.txt
```

**§1 이 0건이었다면** 여기서 짐작되는 앱 키를 찾아, 그 앱의 도구 이름을 전부 뽑아 보내 준다.

```bash
APP=<위에서 찾은 앱 키>
curl -s http://127.0.0.1:9110/tools-map | python3 -c "
import sys, json; d=json.load(sys.stdin)
print('\n'.join(sorted(k for k,v in d['map'].items() if v=='$APP')))
"
```

---

## 3. 응답 표본 ← **두 번째로 중요**

스키마만으로는 **결과가 어떻게 생겼는지** 모른다. 어댑터는 결과에서 값을 꺼내는 일이라
표본이 없으면 만들 수가 없다.

아래에서 `<도구명>` 과 인자는 §1 의 `tools.json` 을 보고 채운다. **읽기 계열만** 부른다
(`list`·`get`·`describe`·`extract`·`ratio`·`report` 류). `ingest`·`delete` 는 부르지 않는다.

```bash
cd ~/Projects/HWAXAgentServer
.venv/bin/python - <<'PY' > ~/Projects/HWAXPortal/docs/workbench/fixtures/odb-hub/samples.json
import asyncio, json
from langchain_mcp_adapters.client import MultiServerMCPClient

CONF = json.load(open("mcp_servers.json"))

# ── 여기를 채운다. 실제 도구명과 인자로 바꿀 것 ──────────────────────
CALLS = [
    # ("odb_list_jobs",       {}),
    # ("odb_list_components", {"job_id": "<실제 job_id>"}),
    # ("odb_extract_parts",   {"job_id": "<실제 job_id>"}),
    # ("odb_copper_ratio",    {"job_id": "<실제 job_id>"}),
]
# ────────────────────────────────────────────────────────────────

async def main():
    tools = {t.name: t for t in await MultiServerMCPClient(CONF).get_tools()}
    out = []
    for name, args in CALLS:
        t = tools.get(name)
        if t is None:
            out.append({"tool": name, "error": "not found"}); continue
        try:
            r = await t.coroutine(**args) if t.coroutine else t.func(**args)
            out.append({"tool": name, "args": args, "result": str(r)[:20000]})
        except Exception as e:
            out.append({"tool": name, "args": args, "error": f"{type(e).__name__}: {e}"})
    print(json.dumps(out, ensure_ascii=False, indent=2))

asyncio.run(main())
PY
```

**잡이 하나도 없으면** 목록 도구(`*_list_*`)의 빈 응답만이라도 보내 준다 — 빈 것과 실패를
어떻게 구분하는지가 어댑터 설계에 필요하다.

---

## 4. 대조표 — 이게 이번 수집의 목적이다

열충격 SED(`predict_sed`)의 **필수 입력 10개**다. ODB 가 이 중 몇 개를 실제로 채워 주는지가
S3 설계 전체를 가른다.

| # | SED 필수 입력 | 형태 | 어느 ODB 도구가 주나 | 값 예 |
|---|---|---|---|---|
| 1 | `board_type` | `INT` / `HALF` / `FULL` | | |
| 2 | `ap_cx` | 수치(보드 좌표) | | |
| 3 | `ap_cy` | 수치 | | |
| 4 | `pkg_cx` | 수치 | | |
| 5 | `pkg_cy` | 수치 | | |
| 6 | `pkg_x` | 수치(패키지 치수) | | |
| 7 | `pkg_y` | 수치 | | |
| 8 | `ball_size` | `"147/250"`(직경/피치 µm) | | |
| 9 | `pad_size` | 수치(180~240) | | |
| 10 | `pkg_type` | `WLP` / `FX` / `DIG` | **아마 없음** — 패키지 기술 분류 | |

이 표를 `fixtures/odb-hub/sed-mapping.md` 로 채워 주면 된다. **"없다" 도 답이다** — 없는 칸은
레시피에서 사람이 채우는 변수가 된다.

**설계 가정** — 이 중 `pkg_type` 하나만 사람이 채우고 나머지 아홉은 ODB 가 준다. 맞는지
확인하는 것이 목적이다. 틀리면 사람이 채우는 칸이 늘 뿐이고 **계획이 깨지지는 않는다**
(공급자 없는 슬롯은 실패가 아니라 물어보는 칸이다).

### 덤으로 — 워피지도 같이 본다

`pcb_warpage_surrogate` 의 필수 3개다. 같은 다리로 열릴 가능성이 높다.

| 입력 | 어느 ODB 도구가 주나 |
|---|---|
| `copper_imbalance_pct` | (동박률 계열?) |
| `stackup_asymmetry` | (적층 계열?) |
| `board_thickness_mm` | (적층 계열?) |

---

## 5. 마지막 — 세 줄짜리 메모

표본에서 안 드러나는 것들이라 글로 적어 주는 편이 빠르다.

- **잡(job) 수명** — `odb_ingest` 로 만든 잡이 얼마나 남나? 서버 재기동에도 사나?
  (레시피가 잡 ID 를 변수로 들고 다닐지, 매번 새로 만들지가 여기서 갈린다)
- **파일을 어떻게 주나** — 절대경로? 업로드? 미리 올려 둔 것만 참조?
  (MCP 로 파일 본문을 나르는지 아닌지가 레시피 입력 모양을 정한다)
- **오래 걸리는 도구가 있나** — 있다면 비동기(잡 제출 → 폴링)인지 동기인지.

---

## 받은 뒤에 dev 에서 할 일

1. `fixtures/odb-hub/` 를 고정물로 삼아 **SedInput 어댑터**를 만든다.
2. `sed-mapping.md` 의 빈 칸을 레시피 **변수**로 옮긴다(`why` 에 왜 물어보는지 적는다).
3. dev 에서는 ODB 단계가 "사람이 채우는 칸" 으로 내려간 상태로 레시피를 완주시켜 본다.
4. **실주행 검증은 cae00 에서** 한다 — dev 에서는 이 경로를 끝까지 돌릴 수 없다.
