# 7차 받은 편지함에 넣을 절 — MCP 현대화(초안)

> 쓰는 쪽 — MCP 현대화 갈래([PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md) MM-6 · 공통 계약 [contract.md](contract.md)). 7차 라운드 글은 다른 포털 세션(87)이
> 쓰고, 이 절은 그 글에 옮겨 싣는다. 옮길 때 87 이 할 것은 넷이다.
>
> 1. **번호** — 이 절의 점검 · 물음은 `MQ-1 ~ MQ-10` 이다. 라운드 글의 Q 번호와 겹치지 않으니(11-25 글의 `R25-Q` 와 같은 까닭) 그대로 쓴다. 아래 「돌려받을 것」 줄은
>    라운드 글 끝의 「돌려받을 것」 목록에 붙인다.
> 2. **「한눈에」 표** — 아래 0절의 세 줄을 그 표에 넣는다.
> 3. **차례** — 1절의 한 줄(update-all 앞에 도구 수를 떠 두기)은 라운드 글의 「0. update-all 앞에」 에 넣는다. 나머지는 update-all 뒤의 절로 둔다.
> 4. **`〔채움:` 칸** — 짓는 중인 판의 값이다. 판이 서면 채우고, 하나라도 남았으면 싣지 않는다(`grep -n '〔채움' docs/mcp-modernize/cae00-7th-section.md`).
>
> 이 절이 기대는 판 — 게이트웨이 stateless 는 가지 `wt1127/stateless` 에서 짓는 중이다(손잡이 이름 `GATEWAY_STATELESS` 도 그 판의 이름이다). 품질 카드
> `mcp_quality_card.py` 는 게이트웨이 master `ea058fd` 에 이미 있다. 고친 날 — 2026-11-27(처음).

---

## MCP 현대화 — 비전 · 이번 판 · 점검 한 벌

### 비전 — 무엇을 왜 바꾸나

이 박스의 게이트웨이에는 백엔드 35 · 도구 1,984개가 모이고(11-26), 그 가운데 약 1,200개가 사내 앱이다. 모델은 도구를 이름 · 설명 · 인자 스키마만 보고 고르고 부르므로,
2,000개 속에서 정밀하려면 모든 MCP 서버가 같은 꼴로 말해야 한다. 그래서 넷을 함께 바꾼다. 첫째는 프로토콜이다 — 2026-07-28 MCP 스펙은 세션(`Mcp-Session-Id`)과
initialize 핸드셰이크를 없앴고, 서버가 세션을 쥐지 않으면 재기동 · 여러 대로 늘리기에 끊기지 않는다. Python SDK 2.x 는 이 새 세대와 옛 세대(initialize)를 같은
자리에서 받으므로(dual-era), 지금의 개인 Claude 같은 옛 클라이언트를 끊지 않고 옮긴다. 둘째는 계약이다 — 도구마다 무엇 · 언제 · 인자 설명 · 단위 · 범위 · enum ·
읽기/쓰기 표지 · 결과 꼴을 스키마에 둔다(공통 계약 아홉 항목). 셋째는 찾기다 — 앱이 아니라 목적 묶음으로 「목적 → 묶음 → 기능 MCP」 를 좁히고, 같은 표에서 검색 ·
보기 · prompts · Skills(`io.modelcontextprotocol/skills`)를 낸다. 넷째는 알림이다 — 잡 끝 · 새 차수 · 보고서 게시를 Events(`io.modelcontextprotocol/events`)로
밀어 준다. 사내 앱도 같은 계약을 따른다 — 2,000개 속 정밀도는 게이트웨이 혼자 만들 수 없다.

| 걸음 | 무엇 | 언제 |
|---|---|---|
| 1단계 stateless | 게이트웨이와 우리 앱이 세션을 쥐지 않는다(SDK 1.x 그대로 · 서버 쪽만 바뀐다) | **이번 7차** |
| 2단계 두 세대 | SDK 2.x 로 옮겨 새 세대 · 옛 세대를 같은 자리에서 — Python 3.11 이상이 든다 | 8차부터(5절 · MQ-8 · MQ-9) |
| 계약 | 읽기 · 쓰기 표지를 게이트웨이 판정으로 노출 · 인자 설명 · 설명 꼴 | 8차부터 |
| 목적 묶음 | `tool_purposes.json` + 박스 덧씌우기 — 검색 · 목록 · 보기 · prompts | 그 뒤 라운드 |
| Skills · Events | 목적 묶음 · 워크플로를 skill 로 · 잡 끝 · 새 차수 · RA 게시를 이벤트로 | 2단계 뒤 |

차례는 라운드마다 그 글에 적는다. 기본값이 바뀌는 것(검색 순위 · 웹 챗 도구 고르기)은 그림자 · 평가에서 나빠진 쌍이 0 일 때만 켠다.

### 0. 「한눈에」 표에 넣을 줄

| 무엇 | 판 | 받는 길 | 이 박스에서 달라지는 것 |
|---|---|---|---|
| 게이트웨이(MCP 전송) | master `9bbc338`(stateless 병합 — 쓰기 오판 고침 `8094f68` · 감사 원장 실패 사유 `3d776c9` 함께) | update-all | MCP 전송이 세션을 쥐지 않는다(`GATEWAY_STATELESS` 기본 켬, `0` 이면 되돌림) · `/health` 에 `stateless` 칸 |
| 앱 1단계(2-2 표의 아홉) | 앱마다(2-2 표) | update-all §2(허브) · 운영 노드 · stcx 운영 헤드 · RA 팀 | 앱이 세션을 쥐지 않는다 — 도구 · 인자 · 결과는 그대로다 |
| 품질 카드 | 게이트웨이 `mcp_quality_card.py`(master `ea058fd` 부터) | update-all | 점검 MQ-1 · MQ-2 가 한 명령이 된다(읽기만) |

### 1. update-all 앞에 — 지금 도구 수를 떠 둔다(읽기만 · 라운드 글 0절로)

```bash
curl -s --noproxy '*' http://127.0.0.1:9110/tools-map > /tmp/mcp-tm-before.json && echo ok
```

update-all 뒤에 MQ-7 이 이 파일과 견준다. 앱마다 도구 수 · 닿음만 쓰고, 견준 뒤 지운다.

### 2. 이번 판에 오는 것

#### 2-1. 게이트웨이 — 세션을 쥐지 않는다

- **무엇이 바뀌나** — 요청마다 새 전송이 서고 응답에 `mcp-session-id` 머리가 없다. 쥔 세션이 없으니 재기동해도 사람 쪽 연결이 끊기지 않는다 — 지금은 재기동 뒤
  개인 Claude 의 다음 호출이 `404 Session not found` 로 끊긴다. 옛 세션 머리를 실어 오는 클라이언트도 그대로 받는다(머리를 보지 않는다).
- **같은 것** — 도구 목록 · 이름 · 인자 · 결과 · 권한 · 감사 원장. 같은 요청의 진행 알림은 그 요청의 응답 스트림으로 그대로 간다.
- **update-all 이 게이트웨이를 다시 띄우는 동안** — 진행 중인 호출은 끝까지 간다. 새 연결(JSON-RPC `initialize`)만 503 · `Retry-After: 1` 이다. 지금은 「세션 머리 없는
  POST」 를 막았는데, stateless 에서는 모든 POST 에 세션 머리가 없어 본문의 method 를 보고 가린다.
- **보이는 곳** — `/health` 의 `stateless`(true · false) · 기동 로그 한 줄 「MCP 전송 — stateless(…)(GATEWAY_STATELESS)」.
- **되돌리기** — 게이트웨이를 띄우는 환경에 `GATEWAY_STATELESS=0` 을 두고 게이트웨이를 다시 띄운다. 게이트웨이는 `infra/.env` 를 읽지 않고 띄운 셸의 환경만 본다 —
  `./infra/scripts/services.sh down mcp-gateway && GATEWAY_STATELESS=0 ./infra/scripts/services.sh up mcp-gateway` 꼴로 띄우고 `/health` 의 `stateless` 가 `false` 인지 본다. 되돌리면 세션을 쥐는 지금 꼴(재기동 막기 · 근거 원장 열쇠도 지금대로)로 돈다.

#### 2-2. 앱 1단계 — 앱이 세션을 쥐지 않는다

앱 쪽 한 줄(`stateless_http=True`)이다. 도구 · 인자 · 결과는 바뀌지 않는다. 앱을 다시 띄워도 붙어 있던 쪽(게이트웨이 · 다른 클라이언트)의 다음 호출이 「세션 없음」 으로
끊기지 않는다. SIF 숫자는 늘 이름을 붙여 적는다 — 파일 내용 해시(sha256)와 허브 빌드 캐시 열쇠(`.sif.hash`)는 다른 숫자다(받은 편지함 README).

| 앱 | 받는 길 | 판(커밋) | SIF 파일 sha256 · 허브 캐시 열쇠 · Drive |
|---|---|---|---|
| DynaForge | 운영 노드 반입(update-all 또는 `dist-from-drive.sh --restart`) — 이 박스는 `KOORM_LOCAL_PARKED` 라 운영 노드만 | 〔채움: KooRemapper 커밋〕 | 〔채움: Drive `dist-…` · 바뀐 파일 · 되돌릴 판〕 |
| 리포트 아카이브 | RA 팀이 그 서버 쌍에 배포(이 박스 밖) — 그 세션의 사용자 승인 뒤 | 〔채움: 커밋 — 지금 후보 `b929a66`〕 | 없음(RA 는 SIF 가 아니다) |
| SignalForge | update-all → sf-mcp 다시 띄우기(자체 빌드 — Drive `SignalForge/sif/latest/`) | 〔채움: 커밋〕 | 〔채움: `mcp.sif` 파일 sha256〕 · 허브 캐시 열쇠 없음(자체 빌드) |
| MaterialTwin | update-all §2(허브) | 〔채움: 커밋〕 | 〔채움: 파일 sha256 · 캐시 열쇠 · `dist-…`〕 |
| Laminate | update-all §2(허브) | 〔채움: 커밋〕 | 〔채움: 파일 sha256 · 캐시 열쇠 · `dist-…`〕 |
| WebDesignAgents | update-all §2(허브) | 〔채움: 커밋〕 | 〔채움: 파일 sha256 · 캐시 열쇠 · `dist-…`〕 |
| SmartTwin MCP | stcx 운영 헤드(사람 — KooSlurm `git pull && sudo ./dashboard/start_production.sh`, 시점은 그쪽 사용자) | 〔채움: KooSlurm 커밋〕 | 없음(코드만) |
| ThermalShock | update-all §2(허브) — 이 박스에 붙어 있을 때만 | main `99905fb`(stateless `7cd9297` + 공통 계약 병합) | 〔채움: 파일 sha256 · 캐시 열쇠 · `dist-…`(Drive 에 올린 뒤)〕 |
| 웹 리서치 | update-all §2(허브) — 이 박스에 붙어 있을 때만(붙어 있는지 모른다 — MQ-1 카드의 앱 줄로 본다) | main `dafd506`(stateless `29d67f0` + 공통 계약 병합) | 〔채움: 파일 sha256 · 캐시 열쇠 · `dist-…`(Drive 에 올린 뒤)〕 |

서버 발 채널(대기 스트림의 알림 · sampling · elicitation · roots)을 쓰는 곳이 없음을 확인한 앱 — 게이트웨이 · 리포트 아카이브 · WebDesignAgents · Laminate · MaterialTwin · DynaForge · MX 백서 · ThermalShock · 웹 리서치(각 세션 · 포털이 소스를 찾아 0 건). 그래서 stateless 로 잃는 기능이 없다.

#### 2-3. 이미 stateless — 바뀌지 않는다

StepForge · AI 데이터 허브 · 리스크 앱 · DocForge · PaperIngest · ste · 심의(에이전트 서버) — stateless 로는 받을 것이 없다. 다만 사용자 지시(11-27 「남기지 말고 최대한 많이」)로 공통 계약(2단계 C1 ~ C9)도 함께 실리는 판이 있다 — AI 데이터 허브 main `7ed5dd0`(도구 32 · 인자 설명 · 표지 100%) · 리스크 앱 main `f534ab1`(표지 · 허용값 + 바깥 도구 인자 꼴 고침 둘 — 문헌 근거 · 태그 검색) · 에이전트 서버 main `234d016`(심의 MCP 표지 · `deliberate_start` 설명 줄임 + 루틴 실행기가 stateless 게이트웨이에서 호출마다 다시 열지 않음 `df32ed2`) · PaperIngest main `210dc1d`(계약 + 보안 — 전문가 이름이 경로를 벗어나지 못함). 도구 · 인자 이름 · 기본값 · 동작은 그대로이고, 읽기 · 쓰기 표지가 붙어 게이트웨이 판정이 바뀌는 도구가 있다(루틴 · 읽기 전용 PAT 에 새로 열림 일곱 · 닫힘 둘 — `risk_get_brief` · `deliberate_batch_status`, HE팀 운영자 정의는 포털 `93d59a3b` 로 맞춤).

#### 2-4. 받는 차례 · 개인 Claude

- **차례는 update-all 그대로다.** 따로 손일이 없다. 1단계는 서버 쪽만 바뀌고 옛 클라이언트가 그대로 붙으므로, 게이트웨이 · 앱 가운데 어느 쪽이 먼저 바뀌어도 된다.
  운영 노드(DynaForge) · stcx 운영 헤드(SmartTwin MCP) · RA 는 그쪽 시점에 따른다.
- **개인 Claude 는 다시 붙을 필요가 없을 것이다.** 게이트웨이가 옛 세션 머리를 실어 오는 호출도 받기 때문이다. 이번 update-all 이 게이트웨이를 처음 stateless 로
  다시 띄우는 순간에도 열린 창이 그대로 이어져야 한다. dev 확인(11-27) — 직접 HTTP 연결로 재기동 뒤 initialize 에 세션 번호가 없고, 세션 없이 · 재기동 전의 옛 세션 번호를 실은 채로 둘 다 tools/list(797) · tools/call 이 200 이었다. PC 킷(mcp-remote) 연결로는 아직 보지 않았다 — 이 박스에서 붙은 PC 하나로 재기동 앞뒤 도구 호출을 한 번 봐 달라(답에 「이어짐 / 다시 붙여야 함」).

#### 2-5. 알고 받을 것

- **버리는 것** — 대기 스트림(GET)으로 가던 서버 발 알림 · 요청(목록 바뀜 · sampling · elicitation · 로그 알림)이다. 게이트웨이와 위 앱들은 그 길을 쓰지 않는다.
- **근거 원장(`verify_answer`)** — 지금은 신원이 없으면 세션 번호로 칸을 갈랐다. stateless 에서는 세션이 없어 **신원 없는 호출의 근거는 쌓지 않는다**(섞느니 안 쌓는다).
  개인 Claude 는 PAT 의 이메일로 늘 신원이 있어 그대로다. 사람 머리 없는 내부 호출 · 서비스 토큰(`system:<작업>`) · 이메일 없는 PAT 만 해당한다.
- **상호작용 기록의 클라이언트 칸** — 이 박스는 수집을 켜지 않았다(11-26 글). 켜게 되면 initialize 가 아닌 호출의 클라이언트 이름 칸이 빈다(1단계의 알려진 손실 —
  2단계에서 다시 본다).

### 3. 받은 뒤 확인 — MQ-7(읽기만)

1. 게이트웨이가 stateless 로 떴나.

   ```bash
   curl -s --noproxy '*' http://127.0.0.1:9110/health | python3 -c 'import json,sys; print("stateless =", json.load(sys.stdin).get("stateless"))'
   grep -a "MCP 전송 —" ~/Projects/HWAXMcpGateway/gateway.log | tail -1
   ```

   기대 — `stateless = True` · 로그 줄이 「MCP 전송 — stateless(…)」 로 시작한다. `None` 이면 옛 판이 떠 있다(재기동이 안 됐다). `False` 면 되돌림 값이 들어 있다.
2. 앱마다 도구 수 · 닿음이 그대로인가(1절에서 떠 둔 파일과 견준다).

   ```bash
   curl -s --noproxy '*' http://127.0.0.1:9110/tools-map > /tmp/mcp-tm-after.json && python3 - /tmp/mcp-tm-before.json /tmp/mcp-tm-after.json <<'EOF'
   import json, sys
   a, b = ({x["app"]: (x.get("tool_count"), x.get("reachable")) for x in json.load(open(p))["apps"]} for p in sys.argv[1:3])
   diff = [f"{k}: {a.get(k)} → {b.get(k)}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
   print(f"앱 {len(a)} → {len(b)} · 도구 {sum((v[0] or 0) for v in a.values())} → {sum((v[0] or 0) for v in b.values())}")
   print("\n".join(diff) or "바뀐 앱 없음")
   EOF
   rm -f /tmp/mcp-tm-before.json /tmp/mcp-tm-after.json
   ```

   기대 — 「바뀐 앱 없음」, 또는 이 라운드의 다른 절이 도구 수가 바뀐다고 적은 앱만. 줄은 `앱키: (도구 수, 닿음) → (도구 수, 닿음)` 꼴이다.
3. **사람** — update-all 전에 열어 둔 개인 Claude 창에서 update-all 뒤 도구 하나(예 `list_tool_apps`)를 다시 붙지 않고 부른다. 되면 「됨」, 안 되면 오류 글의 첫 줄
   (주소 · 토큰은 빼고).

### 4. 점검 한 벌 — MQ-1 ~ MQ-6(읽기만)

쓰기 · 재기동 · 설정 바꾸기는 하지 않는다. 결과 파일은 리포 밖(`/tmp`)에 쓴다 — update-all 이 리포 안의 새 파일을 stash 로 쓸어 간다. 아래 명령은 모두 이 박스의
루프백 게이트웨이만 부른다. 셸의 프록시가 그것까지 삼키지 않게 명령 앞에 `$LO` 를 붙인다(11-23 점검 — 프록시가 셸에 있다).

```bash
LO='env NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost'
```

| 번호 | 받는 곳 | 무엇 | 돌려받을 것 |
|---|---|---|---|
| MQ-1 · MQ-2 | 이 박스 — 게이트웨이 | 앱별 품질 카드 — 카탈로그(표지 · 설명 · 인자 · 결과 꼴) + 감사 30일(호출 · 실패 · 지연 · 크기), 한 명령 | JSON 파일 하나 |
| MQ-3 | 이 박스 — 게이트웨이 | 플랫폼 피드백 보고서 · 안 불린 도구 | 마크다운 둘(**사용자에게만**) |
| MQ-4 | 이 박스 — 포털 | 실호출 스모크(상태판과 같은 판) | JSON 하나 |
| MQ-5 | 이 박스 — 게이트웨이 · 포털 | 붙는 길 · 권한 행(키만) | 목록 셋 · 로그 한 줄 |
| MQ-6 | 사람(관리자) | 사내 앱 정답쌍 달기 → 검색 평가 | 단 쌍 수 · 평가 요약 |

#### MQ-1 · MQ-2 — 앱별 품질 카드(한 명령)

- **까닭** — `/tools-map` 은 인자 설명 · 쓰기 판정을 주지만 표지 원값 · 설명 길이 · 앱 사이 같은 설명 · 지연 백분위를 주지 않는다. 11-24 의 「표지 없음 83.5%」 ·
  「1,000자 넘는 설명 296개」 를 앱마다 다시 재고, 사내 앱 요청서의 「이 박스 카드로 잼」 칸을 채운다. 감사 5-1 초안의 두 스크립트는 이제 게이트웨이 리포의
  `mcp_quality_card.py` 하나로 된다.
- **명령** — 게이트웨이 리포 루트에서 에이전트 venv 파이썬으로.

  ```bash
  cd ~/Projects/HWAXMcpGateway
  $LO ../HWAXAgentServer/.venv/bin/python mcp_quality_card.py --out /tmp/mcp-card.json; echo "rc=$?"
  ```

  읽는 것은 셋이다 — 무인증 `/tools-map`, `tools/list` 전부(서비스 시야 — `gateway_config.json` 의 `_gateway.token` 을 읽고 찍지 않는다), 감사 원장 30일(`audit.jsonl` —
  감사 경로를 `GATEWAY_AUDIT` 로 따로 두었으면 `--audit <경로>`). 쓰는 것은 `--out` 파일 하나다. 세션을 쥐는 게이트웨이 · 쥐지 않는 게이트웨이 둘 다 받으므로
  update-all 뒤에 돌린다. dev 에서는 1초 남짓 · 19KB 였다(도구 797) — 이 박스는 몇 초 · 수십 KB 로 어림한다.
- **기대 꼴** — `{"generated_at", "total": {tools, args, args_described, ro_true, ro_false, nested_args, nested_described, arg_described_ratio, ro_annotated_ratio},
  "apps": [앱마다 한 줄]}`. 앱 줄의 칸은 다음과 같다.
  - 표지 — `ro_true · ro_false · ro_none · destructive · idempotent · ro_annotated_ratio`.
  - 게이트웨이 판정 — `gw_write · routine_read · panel_read · unclassified · prefixed`.
  - 설명 — `desc_empty · desc_lt100 · desc_gt1000 · desc_gt2400 · desc_history · desc_shared_other_app · desc_p50 · desc_p95 · desc_max`.
  - 인자 — `args · args_described · arg_described_ratio · nested_args · nested_described · nested_described_ratio · numeric_args · numeric_bounded ·
    numeric_bounded_ratio · enum_args · free_objects · worst_args`(인자 설명이 가장 빈 도구 이름 다섯까지).
  - 결과 꼴 — `output_schema_real`. 앱 이름 — `app · label`(`label` 은 비어 있어도 된다).
  - 감사 — `audit: {calls, fail, fail_rate, fail_no_reason, ms_p50, ms_p95, ms_max, chars_p50, chars_p95, over_50k}`(기간 안 호출이 없으면 null).
- **견줄 값** — `total.tools` 는 1,984 근처, 앱 줄은 35 남짓(+ 게이트웨이 `_gateway`)이다. 훨씬 적으면 닿지 않은 앱이 빠진 것이다 — MQ-7 견주기의 닿음 칸으로
  어느 앱인지 본다. dev 는 도구 797 · `arg_described_ratio` 0.379 · `ro_annotated_ratio` 0.343 이다.
- **돌려받을 것** — `/tmp/mcp-card.json` 그대로. 설명 원문 · 사람 · 주소는 스크립트가 싣지 않는다(수와 도구 이름만). 보내기 전에 `app` · `label` · `worst_args`
  에 실제 제품 · 과제 이름이 섞였는지만 한 번 본다 — 섞였으면 그 파일은 사용자에게만. 실패했으면 `rc` 와 오류 첫 줄(주소는 빼고). 보낸 뒤 파일을 지운다.

#### MQ-3 — 플랫폼 피드백 보고서 · 안 불린 도구

- **명령** —

  ```bash
  cd ~/Projects/HWAXMcpGateway
  $LO python3 platform_feedback_report.py --out /tmp/mcp-feedback.md; echo "rc=$?"
  $LO python3 tool_usage_report.py --days 30 --out /tmp/mcp-unused.md; echo "rc=$?"
  ```

- **기대 꼴** — 플랫폼(백엔드 키)마다 절 하나. 피드백 보고서는 ① 보정 덕에만 찾아진 질의 ② 보이고도 안 불림 ③ 밖에서 불림 ④ 실패(플랫폼 쪽 · 관문 쪽 가름) ⑤ 큰 응답
  ⑥ 인자 설명 ⑦ 안 불린 도구다. 안 불린 도구 보고서는 30일 동안 감사에 한 번도 안 나온 도구 이름이다.
- **돌려받을 것** — 두 파일, **사용자에게만**. 부른 사람 · 주소는 스크립트가 싣지 않지만 질의 원문은 싣는다(그쪽이 고칠 낱말이 거기 있다) — 질의에 제품 · 과제
  이름이 섞일 수 있다. 사내 팀에 건넬 때는 사용자가 그 팀 절만 떼어 낸다.

#### MQ-4 — 실호출 스모크

- **명령** — 상태판이 30분마다 부르는 판과 같다(읽기 낱말 허용 목록 · 백엔드당 하나 · 감사 묶음 표지).

  ```bash
  cd ~/Projects/HWAXPortal
  $LO ../HWAXAgentServer/.venv/bin/python infra/scripts/mcp-smoke.py --periodic --json > /tmp/mcp-smoke.json; echo "rc=$?"
  ```

- **기대 꼴** — `{"backends": {백엔드: {ok, err, probed, why}}, "dead": [...], "drift": {...}}`. 끝 코드 0 이상 없음 · 1 성공 0 인 백엔드 있음 · 2 게이트웨이에 못
  붙음 · 3 판 드리프트. 사람 토큰이 있어야 하는 선언 백엔드(FMEA · MatNexus · SIREN · 운영 사본)는 「검사 못 함」 이 정상이다.
- **돌려받을 것** — 끝 코드와 그 JSON. `why` 칸에 주소가 섞였으면 그 부분은 빼고.

#### MQ-5 — 붙는 길 · 권한 행(키만, 값은 빼고)

- **명령** —

  ```bash
  cd ~/Projects/HWAXMcpGateway && python3 - <<'EOF'
  import json
  c = json.load(open("gateway_config.json", encoding="utf-8"))
  for k, v in sorted(c.items()):
      if k in {"_gateway", "rest", "portal", "heax_registry"} or not isinstance(v, dict) or "url" not in v:
          continue
      print(f"정적  {k:28s} transport={v.get('transport')}  머리 이름={sorted((v.get('headers') or {}).keys())}")
  reg = c.get("heax_registry") or {}
  print("위임(per_user_sso) 키 =", sorted((reg.get("per_user_sso") or {}).keys()))
  print("허브 앱 토큰(app_tokens) 키 =", sorted((reg.get("app_tokens") or {}).keys()))
  EOF
  curl -s --noproxy '*' http://127.0.0.1:9110/health | python3 -c 'import json,sys; print("선언(conn_platforms) =", sorted((json.load(sys.stdin).get("conn_platforms") or {}).keys()))'
  ```

  덧붙여 이번 update-all 로그의 「권한 표 대조」 줄 하나(「게이트웨이 백엔드가 전부 access.yaml 에 있다」 또는 「권한 표 구멍 … 없는 게이트웨이 백엔드: …」).
- **돌려받을 것** — 위 출력 그대로(백엔드 키 · 머리 이름 · 키 목록뿐이다)와 그 로그 줄. 사내 앱 요청서의 「붙는 길」 칸을 이것으로 고친다.

#### MQ-6 — 사내 앱 정답쌍(사람 · 이번 라운드가 아니어도 된다)

- **까닭** — 게이트웨이 추적 정답쌍 186쌍 가운데 사내 앱 정답은 정본 허브 30 · MatNexus 1 · ComponentCore 1 뿐이다. 검색 고리를 이 박스에서 닫으려면 박스 정답쌍이
  있어야 한다.
- **할 일** — 포털 관리 › 「도구 검색 검토」(`/admin/tool-search`)에서 실사용 질의를 골라 정답 도구를 단다. 사내 앱마다 5 ~ 10쌍. 그 뒤 평가를 한 번 돌린다(한 번에
  하나만 돈다 — 겹치면 409).

  ```bash
  cd ~/Projects/HWAXMcpGateway && $LO ../HWAXAgentServer/.venv/bin/python tool_search_eval/run.py live --detail > /tmp/mcp-search-eval.txt; echo "rc=$?"
  ```

- **돌려받을 것** — 앱별 단 쌍 수 · 출력의 판별 hit@1 · hit@5 · MRR 요약 줄(덧씌운 값 · 기본값). `--detail` 줄의 질의 원문은 **사용자에게만**.

### 5. 다음 라운드(8차부터)에 오는 것 · 미리 답할 물음 MQ-8 ~ MQ-10

- **SDK 2.x(2단계)** — 게이트웨이 · 에이전트 서버가 쓰는 에이전트 venv 를 Python 3.11 이상으로 다시 만든다(dev 는 지금 3.10). 이 박스에 3.11 이상이 있는지,
  꾸러미를 바깥에서 받을 수 있는지가 그 라운드의 길을 정한다(MQ-8 · MQ-9).
  게이트웨이는 전용 venv(`HWAXMcpGateway/.venv`)로 옮긴다 — 그 판을 받는 update-all 은 게이트웨이를 내리기 **전에** venv 를 맞추고(없거나 판이 다르면 Drive
  `tools/gateway-wheels/<열쇠>/` 바퀴 꾸러미로 짓는다), 못 맞추면 내리지 않고 ✗ · 사람 몫을 남긴다(옛 프로세스가 돈다 — context-notes MM-9). 받기 전에 이 박스에서
  `./infra/scripts/gateway-venv.sh check` 로 무엇이 일어날지 읽기만으로 본다. 지을 파이썬을 따로 두려면 infra/.env 에 `GATEWAY_VENV_PYTHON=<경로>`(MQ-8 의 답).
- **표지를 게이트웨이 판정으로 노출**(사용자 결정 MM-5) — 앱 표지 ∪ 확인된 읽기 목록을 클라이언트가 보는 `readOnlyHint` 로 싣는다. 그러면 박스 덧씌우기
  `read_tools.local.json` 의 `tools` 줄이 개인 Claude 에게 「읽기」 로 보인다. 확인되지 않은 줄이 있으면 그 전에 걷는다(MQ-10).
- **목적 묶음** — 게이트웨이 `tool_purposes.json` + 박스 덧씌우기 `tool_purposes.local.json`(지금의 `search_tuning.local.json` · `core_vocab.local.json` 과 같은 꼴 —
  merge patch · 깨지면 통째로 버리고 기본으로).
- **Skills · Events** — 게이트웨이가 허브다. 앱은 「바뀐 것 목록」 읽기 도구만 내고, 게이트웨이가 커서로 묻고 확장 꼴로 다시 낸다.

#### MQ-8 — Python 3.11 이상이 있나

```bash
ls /usr/bin/python3.1* /usr/local/bin/python3.1* 2>/dev/null
~/Projects/HWAXAgentServer/.venv/bin/python -V
for p in ~/Projects/HEAXHub/deploy/apptainer/.tools/python-*/bin/python3; do [ -x "$p" ] && echo "$p $("$p" -V 2>&1)"; done
uname -m; ldd --version 2>&1 | head -1
```

- 셋째 줄은 HEAXHub 가 푼 standalone 파이썬(`install-python.sh` — root 없이 풀기만 한다)이다. 시스템에 3.11 이상이 없어도 이것이 있으면 새 venv 의 바탕이 될 수 있다.
- 넷째 줄(아키텍처 · glibc)은 SDK 2.x 의 바이너리 의존(pydantic-core 등) 바퀴를 고르는 데 쓴다.
- **돌려받을 것** — 네 명령의 출력 그대로(경로 · 판 번호뿐이다).

#### MQ-9 — pip 가 바깥에 닿나(바퀴 꾸러미를 Drive 로 보내야 하나)

```bash
T="$(mktemp -d)"; ~/Projects/HWAXAgentServer/.venv/bin/pip download --no-deps --only-binary=:all: --python-version 3.12 -d "$T" "mcp==2.3.0" 2>&1 | tail -2; rm -rf "$T"
~/Projects/HWAXAgentServer/.venv/bin/pip config list 2>/dev/null | sed 's/=.*/=…/'
```

- 받기만 해 보고 지운다 — venv 에 아무것도 깔지 않는다. 지금 venv 판과 상관없이 받게 `--python-version 3.12` 를 준다.
- 갈래 — 「Successfully downloaded mcp」 면 닿는다. `CERTIFICATE_VERIFY_FAILED` 면 인증서(11-23 점검의 httpx 와 같은 까닭), `ProxyError` · 연결 오류면 프록시,
  「No matching distribution」 이면 받는 곳(미러)에 그 판이 없다.
- 닿지 않으면 dev 가 바퀴 묶음을 Drive `tools/<이름>/` + `SHA256SUMS` 로 보낸다 — 앞선 사례가 웹 챗 Claude 의 `tools/claude-chat-wheels/` 다. 다만 SDK 2.x 는 바이너리 바퀴가
  섞여 MQ-8 의 판 · 아키텍처에 맞춰 지어야 한다.
- **돌려받을 것** — 첫 명령의 갈래(위 넷 가운데 하나 — 오류 글의 주소는 빼고)와 둘째 명령의 키 이름(값은 sed 가 지운다).

#### MQ-10 — 박스 덧씌우기 파일 다섯

```bash
cd ~/Projects && python3 - <<'EOF'
import json
from pathlib import Path
for f in ["HWAXPortal/backend/config/core_vocab.local.json", "HWAXPortal/infra/personas/he-team.local.json",
          "HWAXMcpGateway/search_tuning.local.json", "HWAXMcpGateway/read_tools.local.json", "HWAXMcpGateway/app_keys.local.json"]:
    p = Path(f)
    if not p.exists():
        print(f"없음  {f}"); continue
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"깨짐  {f} ({type(e).__name__})"); continue
    parts = [f"{k}={len(v)}" if isinstance(v, (list, dict)) else k for k, v in d.items()] if isinstance(d, dict) else [type(d).__name__]
    print(f"있음  {f}  — " + " · ".join(parts))
EOF
ls ~/Projects/HWAXMcpGateway/*.local.json 2>/dev/null | xargs -r -n1 basename
```

- 값은 찍지 않는다 — 맨 위 키 이름과 그 아래 개수만이다. 둘째 명령은 게이트웨이 곁의 다른 박스 파일 이름까지 본다.
- **사람이 한 줄로 답할 것** — `read_tools.local.json` 의 `tools` 줄은 모두 앱 소스 · 문서로 읽기임을 확인한 것인가(예 · 아니오 · 모름). 다음 라운드부터 그 줄이
  클라이언트에 「읽기」 로 보인다.
- **돌려받을 것** — 두 명령의 출력과 그 한 줄.

### 6. 사내 앱 주인에게 건넬 것

- 공통 계약 [contract.md](contract.md)(프로토콜 셋 · 도구 계약 아홉 · 로드맵 셋 · 답하는 꼴)과 앱별 요청서 [requests/](requests/README.md) 가 있다. **건네는 것은 사용자다.**
  11-24 요청 모음 3절을 담당에게 보내는 길이 이 박스에 있어 사용자가 그 길에 함께 실어 달라고 하면, 그 말을 따른다.
- 이 박스가 할 일은 MQ-1 카드를 돌려주는 것뿐이다. 카드가 오면 dev 가 요청서의 「이 박스 카드로 잼」 칸을 그 앱의 줄로 채운 뒤 사용자에게 넘긴다.
- 이 박스가 주인인 둘 — CircuitTrace 와 개발실 체크리스트 중계 MCP 는 운영 쪽 앱이라, 그 요청서([circuittrace](requests/circuittrace.md) · [devlab-checklist](requests/devlab-checklist.md)
  1절)는 이 박스 몫으로 읽는다.

### 돌려받을 것(이 절 몫 — 라운드 글 끝 목록에 붙인다 · 주소 · 키 · 이름은 빼고)

- **MQ-7** 이번 판 — `stateless =` 값 · 로그 줄(있음 · 없음, 「stateless」 · 「세션 방식」) · 도구 수 견주기 출력 · 개인 Claude 이어짐(됨 · 안 됨과 오류 첫 줄).
- **MQ-1 · MQ-2** `/tmp/mcp-card.json` 파일 그대로(제품 · 과제 이름이 섞였으면 사용자에게만) · 실패면 `rc` 와 오류 첫 줄.
- **MQ-3** 피드백 · 안 불린 도구 마크다운 둘 — **사용자에게만**.
- **MQ-4** 스모크 끝 코드 · JSON.
- **MQ-5** 키 목록 셋 · 「권한 표 대조」 로그 줄.
- **MQ-6** 앱별 단 쌍 수 · 평가 요약(사람이 단 뒤 — 다음 라운드여도 된다).
- **MQ-8** 파이썬 경로 · 판 · 아키텍처 · glibc.
- **MQ-9** pip 받기 갈래 · pip 설정 키 이름.
- **MQ-10** 덧씌우기 다섯 줄 · 게이트웨이 곁 `.local.json` 이름 · `read_tools.local.json` 확인 한 줄.
