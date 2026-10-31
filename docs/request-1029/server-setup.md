# 10-29 웹 챗 온톨로지 QA 후속 — cae00 반영 안내(수정 사항 · 받을 때 주의점 · 확인 · 사람 몫)

cae00 에서 이 묶음(1 · 2 · 3차와 4차 일부, 2026-10-29 — 저녁에 더한 검색 고리 E-7 ~ E-9 는 7절)을 받기 전에 읽는다. 무엇을 왜 바꿨는지는 같은 폴더의 [PLAN.md](PLAN.md) ·
[checklist.md](checklist.md) · [context-notes.md](context-notes.md)(C-1 ~ C-40 — E-2 · E-4 는 8절)가 정본이다. 받는 길은 그대로
`git pull && update-all` 이다 — 포털 화면 · StepForge 는 dev 가 올린 Drive 판을 받는다.

## 1. 무엇이 바뀌었나

| 리포 | 받을 판 | 바뀐 것 |
|---|---|---|
| 포털(HWAXPortal) | main — 이 문서가 든 판 | 코어 어휘표 `backend/config/core_vocab.json`(정본) · 챗 중계가 상류 읽기를 화면 쓰기와 뗀다(숨은 탭에서도 답이 끝까지 저장된다) · 챗 침묵 한도 900초(심의와 뗐다) · 서버 대화 id 를 에이전트 서버에 싣는다 · 화면(중지 단추가 곧바로 풀린다 · 숨은 탭에서 돌아오면 서버 사본과 맞춘다) · update-all §6 '새 앱 점검' · env 킷 주석 손잡이 둘 |
| 에이전트 서버(HWAXAgentServer) | main `969e723` | 코어 데이터 규칙을 어휘표로 짓는다 · 챗 스트림에도 15초마다 ping · 자기검증은 바꿀 곳([원문] · [새 글])만 받는다(상한 4,096) · 도구 결과 머리에 앱 이름 · 같은 도구 네 번째에 '앞 결과를 써라' · 허브 큰 응답 접기 · 한자 · 가나 낱말을 자기검증에 짚는다 · 챗 LLM 호출에 대화 머리(`X-Session-Affinity`) · 프롬프트 앞부분 고정 · 도구 설명 예산 손잡이 |
| 게이트웨이(HWAXMcpGateway) | master `44f4b8d` | 코어 낱말 → 허브 읽기 도구(search_tools) · 정본 도구 설명 앞 소개 줄 · 같은 도구 사본은 정본 한 줄로 · 코어 질문은 '심의 · 토의 · 회의' 를 말할 때만 심의 도구를 올린다 · 시험 사본(stepforge-prod · dynaforge-prod)을 목록 · 검색에서 뺀다(10-31 — 두 앱은 운영 앱이라 다시 보인다, 6절) · `tool_usage_report.py`(안 쓴 도구 보고) · DocForge 도구 영역 |
| StepForge | main `ff308d1`(D-648, `c65c92a` D-647 위에 하나) · Drive SIF — **올렸다(10-30 KST — SIF `dist-20261030-034158Z`, sha256 `020a27e1…` · SIF 안 BUILD_INFO = `ff308d1`)**. 이 판 뒤의 update-all 에서 든다 | `find_plm_task` 가 과제가 속한 프로젝트의 이름 · 별칭(마케팅명)으로도 찾는다(`matched_by` `project:<키>`) · 응답의 `sync` 는 요약(타입마다의 줄은 `system_capabilities.plm_hub` 에만) · **D-648** 낙하 트윈 fe_cad 판 열쇠에 짝 · 파트 표가 읽은 DB 값의 지문(`key_parts.tables`)이 든다 — 사람이 이름 · 재질 · 색을 고치면 새 열쇠가 된다(DynaForge 리포트의 받는 쪽 검사가 '같은 열쇠면 같은 바이트' 에 기댄다) |

받는 판에는 이 묶음 밖의 커밋(다른 작업)도 함께 든다. 리포마다 무엇이 드는지는 받기 전에 본다(2절 ①).

## 2. 받기 전에 — 주의점

① **읽기 전용 사전 점검부터.** 작업 트리를 바꾸지 않는다.

```bash
cd ~/Projects/HWAXPortal && git fetch -q origin main && git show origin/main:infra/scripts/update-preflight.py | python3 -
```

② **포털 · 에이전트 서버 · 게이트웨이를 같은 판으로 받는다(update-all 한 번).** 포털의 챗 침묵 한도 900초(`AGENT_CHAT_IDLE_TIMEOUT_S`)는
에이전트 서버가 챗 스트림에도 15초마다 ping 을 내야 맞다. ping 없는 옛 에이전트 서버와 붙으면 생각 · 비스트리밍 호출로 15분 넘게 조용한 긴 답이 끊긴다.

③ **심의가 돌고 있으면 update-all 이 에이전트 서버 재기동을 미룬다(종전 동작 — ○ 줄).** 그동안은 위 ② 의 짝이 어긋난 상태다. 심의가 끝나면 에이전트 서버를
다시 띄운다(`cd ~/Projects/HWAXAgentServer && ./start.sh -d`). 그 전에 긴 챗이 끊기면 포털 `backend/.env` 에 `AGENT_CHAT_IDLE_TIMEOUT_S=46800`(종전 값)을
잠시 적고 포털만 다시 띄운다 — 짝이 맞으면 줄을 지운다.

④ **StepForge 는 Drive 의 SIF 가 GitHub 끝과 같아야 뜬다.** 허브는 앱 커밋이 바뀌면 SIF 열쇠(`.sif.hash`)를 견주고, 다르면 cae00 에서 지으려다 실패해 그 회차에
앱을 띄우지 않는다. 받기 전에 본다.

```bash
cd ~/Projects/HWAXPortal && ./infra/scripts/drive-drift.sh heax
```

`step_forge` 줄이 ✗(열쇠가 다르다)면 update-all 을 미루고 dev 에 알린다 — dev 가 그 커밋의 SIF 를 다시 올린다.
dev 는 StepForge · WebDesignAgents 의 SIF 를 GitHub 에서 받아 짓는다. 그래서 dev 가 push 한 뒤 새 SIF 가 Drive 에 닿기까지 몇 분은 열쇠가 어긋난다 —
그 사이에는 update-all 을 돌리지 않는다(dev 가 '올렸다' 고 알린 뒤에 돌린다). 지금 판끼리 맞을 때(✓)는 언제 돌려도 된다.

⑤ **형제 리포 자리.** 게이트웨이 · 에이전트 서버는 `../HWAXPortal/backend/config/core_vocab.json` 을 읽는다(cae00 은 `~/Projects/` 아래 형제). 못 읽으면 막히지는
않고 종전 동작으로 돈다 — 3절의 `/health` 가 말한다.

⑥ **화면은 Drive 판이다.** update-all §6 의 'SPA dist 가 지금 소스와 같다' 줄이 ✓ 여야 한다. ✗(dist 가 소스와 다르다)면 Drive 의 화면 판이 이 판보다 뒤다 — dev 에 알린다.

## 3. 받은 뒤 — 확인

- **update-all 끝 요약** — 새로 보일 줄은 둘이다.
  - `· 새 앱 점검 — 기록이 없어 지금 앱 N개를 전부터 있던 것으로 적었다` — 첫 실행에 한 번만 나온다(정상 — 기록 `infra/.state/app-checks.json`). 다음 실행부터 새로 붙은 앱만 14일 동안 ⚠ 로 짚는다(영역 · 권한 행 · 이름 겹침 · 인자 설명). 막지 않는다.
  - '권한 표 대조' 줄은 종전 그대로다. 허브 셋 · componentcore · plm-search-agent · simengbay · 시험 사본이 박스 권한표(`access.local.yaml`)에 없으면 여기서 ✗(권한 표 구멍)다.
- **게이트웨이** — `curl -s --noproxy '*' 127.0.0.1:9110/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"])'`
  - `loaded: True` · `canonical: rootdesigndatahub` · `canonical_backend: True` · `tagline_applied: True` · `staging_hidden` 에 이 박스의 시험 사본.
    포털 `dbbb943`(10-31) 부터는 `staging_hidden: []` 가 맞다 — dynaforge-prod · stepforge-prod 는 운영 앱이라 어휘표에서 뺐다(10-31 OB-04 사용자 결정으로 뒤집음 — 6절 · [`../request-1030/context-notes.md`](../request-1030/context-notes.md) C-14).
  - `canonical_backend` 가 False 면 이 박스의 정본 허브 백엔드 키가 어휘표와 다르다 — 키를 dev 에 알린다(소개 줄 · 정본 대표 접기가 꺼진 채다).
  - `curl -s --noproxy '*' 127.0.0.1:9110/tools-map | python3 -c 'import json,sys;print(json.load(sys.stdin)["unclassified"])'` 에 `docforge_*` 가 없다.
- **에이전트 서버** — `curl -s --noproxy '*' 127.0.0.1:9009/health | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["core_vocab"]);print(d["self_check"])'`
  - `core_vocab.loaded: True`. False 면 `error` 가 까닭이다(`없음` 이면 포털 리포가 형제 자리에 없다).
  - `self_check` 의 `counts`(fixed · suspect · ok)와 `ms.p95` 를 지난 재시험 값과 견준다. `suspect` 의 까닭이 '바꿀 곳을 초안에서 찾지 못했다' 로 많으면 dev 에 보낸다.
- **화면** — 답을 기다리며 다른 탭에 20초 넘게 있다 돌아오면 끝난 답이 보인다. 중지 단추가 곧바로 풀린다.
- **StepForge**(D-647 이 든 뒤) — 챗에서 과제의 마케팅명으로 물으면 `find_plm_task` 가 `matched_by` `project:<프로젝트 키>` 로 과제를 낸다. 응답의 `sync` 에 `types` 가 없다.

## 4. 사람 몫 — 박스 설정 · 시험

- **O-2 챗 LLM 부하분산기의 대화 고정** — stcx 챗 LLM 앞 nginx(`~/stcx-llm/nginx.conf`)가 `X-Session-Affinity` 로 복제본을 고르게 한다. `map` 은 http 블록에,
  `hash` 는 그 upstream 블록 맨 위에 둔다. `nginx -t` 뒤 `nginx -s reload`.

  ```nginx
  map $http_x_session_affinity $chat_affinity {
      ""      $request_id;                  # 머리가 없는 요청은 요청마다 다른 값 — 지금처럼 고르게 퍼진다
      default $http_x_session_affinity;
  }
  upstream <지금 이름 그대로> {
      hash $chat_affinity consistent;
      server …;                               # 지금 줄 그대로
  }
  ```

- **O-3 도구 설명 예산 견주기** — 에이전트 서버 `.env` 에 `CHAT_TOOL_SCHEMA_BUDGET=30000` → 도는 심의가 없을 때 `./start.sh -d` → 같은 16문항. `40000` 으로 한 번 더.
  나은 값을 남기거나 줄을 지운다(비면 종전대로 챗 창의 45% — 호출마다 약 8.8만 토큰). 줄이면 `search_tools` → `invoke_tool` 왕복이 늘 수 있다.
- **재시험** — 같은 정답표 16문항(OT-01 ~ 16). 보는 것은 OT-06 ~ 10 의 정본 허브 호출 · 첫 도구가 코어인지 · 자기검증 ms p95 · 숨은 탭 시간이다.
  결과로 4차의 남은 셋(E-2 앱 역할 순위 · E-4 개인 Claude 묶음 · E-5 페르소나 연결)을 정한다(결정 D-7).
- **안 쓴 도구 보고(E-3)** — `cd ~/Projects/HWAXMcpGateway && python3 tool_usage_report.py --out ~/unused-tools-$(date +%F).md` → 앱 주인에게 넘긴다(부른 사람 · 주소는 싣지 않는다).
- **SignalForge SG-04** — [signalforge-sg04-question.md](signalforge-sg04-question.md) 를 SignalForge 주인에게 넘긴다(P8 · PH8 제품 코드 — 데이터 결정, 안 셋).
- **StepForge 운영 결정** — [stepforge-ops-decisions.md](stepforge-ops-decisions.md)(StepForge 세션이 쓴 글, 10-29). 운영이 정할 것 셋 — ① 응답 공개 주소
  `APPTAINERENV_STEPFORGE_PUBLIC_BASE` ② MaterialTwin 주소의 정본(`.env` 그대로 · 허브가 `HEAX_APP_URL_<SLUG>` 로 넣기) ③ 게이트웨이 비밀 머리
  `X-Heax-Gateway-Secret`(막는 도구를 붙이기 전에 닫는다) — 와 알림 하나(이어 받기 시한 45초) · 확인 하나(cae00 챗 실사용 1건).

## 5. 되돌리기 — 손잡이

| 무엇 | 끄는 법 | 반영 |
|---|---|---|
| 챗 자기검증 전체 | 에이전트 서버 `.env` `CHAT_SELF_CHECK=0` | 에이전트 서버 재기동 |
| 프롬프트 앞부분 고정(바뀌는 안내의 자리) | 에이전트 서버 `.env` `CHAT_STABLE_PREFIX=0`(종전 자리) — 재시험에서 지시를 따르는 정도가 떨어지면 | 에이전트 서버 재기동 |
| 도구 설명 예산 | `CHAT_TOOL_SCHEMA_BUDGET` 줄을 지운다(종전 45%) | 에이전트 서버 재기동 |
| 챗 침묵 한도 | 포털 `backend/.env` `AGENT_CHAT_IDLE_TIMEOUT_S=<초>`(종전 46800) | 포털 재기동 |
| 부하분산기 대화 고정 | nginx 의 `hash` 줄을 지우고 `nginx -s reload` | 즉시 |

에이전트 서버 재기동은 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d` 다.

## 6. 알아 둘 것

- '낙하 해석 담당' 질의는 코어 낱말이 없어 어휘표가 닿지 않는다 — 다시 코어를 건너뛰어도 이 묶음과 무관하다(C-14).
- 시험 사본은 목록 · 검색에서만 빠지고, 도구 이름으로 부르면 그대로 닿는다(C-18). stepforge-prod · dynaforge-prod 는 10-31 부터 시험 사본이 아니다 — 운영 앱이라
  어휘표에서 뺐고 목록 · 검색에 보통 앱으로 보인다(10-31 OB-04 사용자 결정으로 뒤집음, 포털 `dbbb943`). 박스 권한표의 '(시험)' 라벨은 사람이 고친다
  ([`../request-1030/server-setup.md`](../request-1030/server-setup.md) 7절).
- 자기검증이 고칠 곳을 초안에서 못 찾으면 고치지 않고 초안을 그대로 낸다 — 답 아래 '검증하지 못해 초안을 그대로 보였습니다' 와 까닭이 뜬다(정상 동작).

## 7. 검색 고리 — 손잡이 · 기록 · 검토 · 평가 · 피드백 보고서(E-7 ~ E-9, 10-29 저녁)

게이트웨이 `search_tools` 의 보정(손 동의어 · 코어 어휘표 · 품질 가중 …)을 cae00 에서 커밋 없이 고치고, 실사용 질의로 재고, 우리가 다루지 않는 플랫폼에
돌려줄 보고서를 cae00 에서 짓는다(고리는 cae00 에서 닫힌다 — C-31). **기본값은 지금 순위와 바이트까지 같다** — 덧씌우기 파일을 만들기 전에는 검색 답이
바뀌지 않는다. 바뀐 것은 질의 기록의 꼴(날짜 파일 · 결과 줄)과 창구 · 화면 · 보고서가 생긴 것이다.

| 리포 | 받을 판 | 바뀐 것 |
|---|---|---|
| 게이트웨이 | master `f4d9546` | `search_tuning.json`(손잡이 기본값) + 박스 덧씌우기 `search_tuning.local.json` · 코어 어휘표 덧씌우기 읽기 · `/health` 의 `search_tuning` · `core_vocab.fingerprint` · 질의 기록을 날짜 파일의 굴러가는 창(30일)으로 · 찾은 뒤 600초 안의 호출을 결과 줄로 · 창구 `/search-log` · `/search-review` · `/search-eval`(공유 비밀) · `tool_search_eval/run.py live` · `platform_feedback_report.py` |
| 에이전트 서버 | main `ab87137` | 코어 어휘표 덧씌우기를 게이트웨이와 같은 규칙으로 읽는다 · `/health` `core_vocab.fingerprint` |
| 포털 | main — 이 문서가 든 판 | 관리자 메뉴 '도구 검색 검토'(`/admin/tool-search`) · `.gitignore` 에 `backend/config/core_vocab.local.json` · update-all §7 에 지문 두 줄 |

### 7.1 받기 전에

- **덧씌우기 파일은 이 판을 받은 뒤에 만든다.** update-all §1 의 stash 는 받기 전의 `.gitignore` 로 돈다 — 그 전에 만든 `search_tuning.local.json`(게이트웨이) ·
  `backend/config/core_vocab.local.json`(포털)은 git 이 모르는 파일이라 치워진다(gotchas 'update-all stash 가 박스 파일을 치운다'). 이미 만들었으면 받기 전에
  그 리포의 `.git/info/exclude` 에 한 줄씩 적는다. 2절 ① 의 사전 점검이 치워질 파일을 찍는다.
- 질의 기록 · 박스 정답쌍(`tool_search_eval/queries-*.local.jsonl` · `pairs.local.jsonl`)은 옛 `.gitignore`(`tool_search_eval/*.local.*`)에도 걸려 그대로 남는다.
- 게이트웨이 · 에이전트 서버 · 포털을 같은 판으로 받는다(update-all 한 번). 포털의 검토 화면은 새 게이트웨이의 창구를 부른다 — 게이트웨이가 옛 판이면 화면이
  '게이트웨이에 검색 고리 창구가 없다 — 게이트웨이가 이 판보다 낡았다' 고 말한다.

### 7.2 받은 뒤 — 확인

- **update-all 끝 요약** §7 에 두 줄이 새로 보인다.
  - `· 검색 손잡이: 지문 <12자>(기본값 <12자> · 덧씌우기 없음)` — 덧씌우기를 만들기 전에는 두 지문이 같다. ⚠ 와 까닭이 붙으면 덧씌우기를 버렸다(아래 7.3).
  - `· 코어 어휘표 지문: 게이트웨이 <12자> · 에이전트 <12자>` — 둘이 같아야 한다. ⚠ '다르다' 면 한쪽이 옛 판(재기동 전)이거나 덧씌우기를 버렸다.
- **게이트웨이** — `curl -s --noproxy '*' 127.0.0.1:9110/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["search_tuning"])'` 에
  `fingerprint` · `base` · `switches_off: []` · `synonyms: 73` · `overlay.present: False`.
- **질의 기록** — 챗에서 도구를 찾는 질문을 하나 한 뒤 `ls ~/Projects/HWAXMcpGateway/tool_search_eval/` 에 `queries-<오늘>.local.jsonl` 이 생긴다.
  10-18 의 일회성 파일 `queries.local.jsonl` 은 그대로 두고 읽기만 한다.
- **화면** — 관리자 계정의 머리 메뉴(관리)에 '도구 검색 검토'. 최근 질의 · 상위 다섯 · '보정 덕에만' 표지 · 뒤이은 호출이 보인다.
  '게이트웨이 공유 비밀 … 없다' 면 포털 `backend/.env` 의 `GATEWAY_SHARED_TOKEN` 이 비었고, '공유 비밀을 거절했다' 면 그 값이 게이트웨이 `gateway_config.json` 의
  `_gateway.token` 과 다르다(연결 설정 저장 · 권한 표 대조가 쓰는 값과 같다). 둘 다 `./infra/scripts/wire-gateway-shared-token.sh` 가 맞추고, 그 뒤 포털 ·
  게이트웨이를 다시 띄운다(둘 다 기동 때 읽는다).

### 7.3 쓰는 법 — 사람 몫

- **보정 고치기** — `~/Projects/HWAXMcpGateway/search_tuning.local.json` 에 바꿀 칸만 적는다. 규칙은 JSON merge patch 다 — 객체는 합치고, 그 밖은 바꾸고, `null` 은
  지운다(목록은 통째로 바뀐다). 저장하면 **재기동 없이** 다음 검색부터 탄다.

  ```json
  {"switches": {"quality": false},
   "synonyms": {"메인 PBA": {"to": ["pba", "board"], "owner": null, "source_fix": null}, "리포트": null},
   "weights": {"desc_cap": 2}}
  ```

  `/health` 의 `search_tuning.overlay` 가 `present: True` · `changed`(건드린 칸) · 덧씌우기 지문을 말한다. JSON 이 아니거나 꼴이 틀리면 덧씌우기를 버리고 기본값으로 돌며
  `overlay.error` 에 까닭이 실린다(검색은 멈추지 않는다).
- **코어 어휘표 고치기** — `~/Projects/HWAXPortal/backend/config/core_vocab.local.json` 에 같은 규칙으로. 게이트웨이 · 에이전트 서버가 함께 읽는다 — 두 `/health` 의
  `core_vocab.fingerprint` 가 같은지 본다(update-all §7 의 줄도 같다).
- **정답 달기** — 관리 → '도구 검색 검토' 에서 질의마다 '정답 달기' → 맞는 도구를 고르거나(목록에 없으면 `앱키:원래 이름` 으로 적는다) '1위가 맞다'.
  표시는 이 박스의 `tool_search_eval/pairs.local.jsonl`(`source: box`)에 남는다 — dev 로 보내지 않는다.
- **재기** — 화면의 '평가 돌리기', 또는 `cd ~/Projects/HWAXMcpGateway && ../HWAXAgentServer/.venv/bin/python tool_search_eval/run.py live --detail`.
  덧씌운 값 · 기본값 · 보정 끔 · 묶음 하나씩 끔을 정답쌍(추적 + 박스)으로 잰다. 정답쌍이 150쌍쯤이면 십수 초 걸리고, 그동안 게이트웨이 응답이 조금 느려질 수 있다 —
  사람이 적은 때 돌린다. 한 번에 하나다.
- **플랫폼별 피드백 보고서** — `cd ~/Projects/HWAXMcpGateway && python3 platform_feedback_report.py --platform <백엔드 키> --out ~/feedback-<키>-$(date +%F).md` →
  그 플랫폼 주인에게 넘긴다(보정 덕에만 찾아진 질의와 고칠 낱말 · 보이고도 안 불린 도구 · 결과에 없었는데 불린 도구 · 실패 · 큰 응답 · 인자 설명 · 안 불린 도구).
  질의 원문은 실리고 부른 사람 · 주소는 실리지 않는다. 그쪽이 설명을 고쳐 보정이 필요 없어지면 그 동의어를 덧씌우기에서 `null` 로 지운다(보정은 비계다).
- 잘 된 덧씌우기를 모두의 기본값으로 올리려면 dev 에 덧씌우기 파일을 보낸다(선택 — 박스에서 도는 것으로 충분하면 그대로 둔다).

### 7.4 되돌리기

| 무엇 | 끄는 법 | 반영 |
|---|---|---|
| 검색 보정 덧씌우기 | `search_tuning.local.json` 을 지운다 | 다음 검색부터 |
| 코어 어휘표 덧씌우기 | `backend/config/core_vocab.local.json` 을 지운다 | 다음 검색 · 챗 턴부터 |
| 질의 기록 모으기 | 게이트웨이를 띄우는 프로세스의 env 에 `GATEWAY_TOOL_QUERY_LOG=0`(창은 `GATEWAY_TOOL_QUERY_LOG_DAYS`, 기본 30) | 게이트웨이 재기동 |
| 박스 정답 하나 | 화면의 '표시 지우기' | 즉시 |

## 8. 앱 역할 · 개인 Claude 보기(E-2 · E-4, 10-31)

어휘표의 앱 역할(가족 = 정본 + 형제 · 비코어 · 시험)을 게이트웨이가 다 읽어 검색 순위 · 접기 · 노출에 쓰고(E-2), 개인 Claude 의 허브 도구 목록을 보기 셋
(전체 · 묶음 · 가벼운)으로 고르게 한다(E-4). 설계는 [design-e2-e4.md](design-e2-e4.md), 결정은 [context-notes.md](context-notes.md) C-32 ~ C-40, 반대 검토
반영은 C-41 ~ C-47 이다. **기본값에서는 검색 답 · 목록이 지금과 같다** — 비코어 낮추기는 꺼진 채 들어오고, 보기는 모두 전체로 시작한다. 포털 보기는
이 판의 등록 배치 · 명령으로 붙인 Claude Code · Desktop(연결 머리 `X-HWAX-View: portal`)에만 먹는다 — 머리가 없는 연결(예전 등록 · 내 토큰으로 서버에서
도는 앱 · 스크립트)은 늘 전체다. 바뀌는 것은 허브 가족 도구의 이름 규칙(늘 접두 — cae00 은 셋 다 이미 접두라 바뀔 이름 0 으로 본다)과 새 칸들이다.

| 리포 | 받을 판 | 바뀐 것 |
|---|---|---|
| 게이트웨이 | 이 묶음이 든 master(`9b37b31` · `4c17be8` · `8186d9a` · 반대 검토 `f9b75c6` · `2651020` · `1ff9d74` · `58f7dad` · `0a0a0c0` · 문서 `cfb32a8` · `19895c2` · `10bb6ec`) | 역할 읽기 · `/health core_vocab.roles` · `role` 칸 · 가족 접기(가족 밖 사본도 같은 설명이면 그 무리) · 가족은 늘 접두(옛 맨 이름은 호출 별칭 · 표를 못 읽어도 가족을 쥔다) · 형제 소개 줄 칸(순위 밖 — 접힌 형제의 `same_in` 에 `tagline`) · 비코어 낮추기 손잡이(끔 — 앱 이름은 어휘표 라벨 · 키로도 본다) · 보기 셋(tools/list 에만 — 포털 설정은 머리 `portal` 로 청한 연결에만) · `list_tool_apps` 의 `view` · `/health tools_list_by_view` · `/tools-map` 의 `views` · 피드백 보고서가 감점 규칙(`demote:noncore`)을 '보정 덕에만' 에 싣지 않는다 |
| 포털 | 이 문서가 든 main | `users.hub_view` 칸(기동 때 저절로 생긴다) · `GET · PUT /auth/access/view`(게이트웨이가 보기를 아나 — `view_supported`) · 권한 응답 `view` · 토큰 화면 '허브에 보일 앱' 탭 위 보기 고르기(화면은 Drive 판) · 등록 배치 · 명령이 Claude Code · Desktop 에 `X-HWAX-View: portal` · 리포 `.mcp.json` 의 `X-HWAX-View` · 어휘표 꼴 시험(형제 소개 줄) |
| 에이전트 서버 | 바뀐 것 없음 | 웹 챗은 GW_TOKEN 이라 늘 전체다. `/tools-map` 의 앱 줄에 `role` 이 더 붙는다(읽지 않는다) |

### 8.1 받기 전에

- **게이트웨이 · 포털을 같은 판으로 받는다(update-all 한 번).** 새 포털 화면이 옛 게이트웨이와 붙으면 보기 칸의 영역 수에서 형제 허브가 빠지지 않고(옛 `/tools-map` 에
  `role` 이 없다), 고른 보기는 저장되지만 게이트웨이가 읽지 않아 전체로 돈다 — 그때 화면이 칸 위에 '지금 허브는 보기를 아직 모릅니다' 를 띄운다(`/tools-map`
  의 `views` 가 없다, C-42). 옛 포털과 새 게이트웨이는 권한 응답에 `view` 가 없어 전체로 돈다(안전한 쪽).
- 받기 전 5절의 M-2(허브 가족 이름)를 한 번 재 두면 받은 뒤 바뀐 이름을 바로 견줄 수 있다(재지 않았어도 받은 뒤 `/health` 가 말한다 — 8.2).

### 8.2 받은 뒤 — 확인

- **허브 가족 이름** — `curl -s --noproxy '*' 127.0.0.1:9110/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"]["roles"])'`
  - `family` — `rootdesigndatahub` · `failuretrace` · `caegroupdatahub` 가 모두 `True`(이 박스 백엔드에 있다). `False` 면 어휘표 키가 박스의 백엔드 키와 다르다 —
    덧씌우기(`backend/config/core_vocab.local.json`)의 키를 고친다.
  - `noncore` — 박스에 붙은 비코어 앱(fmea · arp · odb-hub · matnexus · reportarchive · componentcore)이 `True`.
  - `family_prefixed.count` — **0 이어야 한다**(허브 셋이 같은 판의 같은 도구를 내면 셋 다 이미 접두다). 0 이 아니면 `names` 의 도구가 이번에 맨 이름에서 접두
    이름으로 바뀌었다 — 한 허브만 판을 올렸거나(판 어긋남) 허브가 하나만 붙어 있다. 옛 맨 이름도 게이트웨이를 거쳐 **부르면** 닿는다(호출 별칭 — 직접 호출 ·
    `invoke_tool`). 목록 이름에 묶는 쪽은 접두 이름으로 고친다 — Claude Code · Desktop 의 도구 이름(`mcp__hwax__<이름>`)과 허용 규칙(쓰는 사람은 재연결),
    `infra/personas/he-team.json` 의 key_tools · writes · confirm(운영자 동기화가 접두 도구의 맨 이름을 '이 앱에 없는 도구' 로 막는다). 게이트웨이 로그에도 '허브
    가족은 늘 접두를 단다' 한 줄이 있다. 0 이 아니면 그 이름들을 dev 세션에 옮긴다 — 목록은 늘 접두로 둔다(사용자 확인 10-31, C-47). 이 수는 받은 편지함
    2026-10-31 Q14 로 돌려준다.
  - 어휘표를 잠깐 못 읽어도(update-all 의 받기와 재활 회차가 겹침 등) 이름은 그대로다 — 마지막으로 온전히 읽은 표의 가족을 쥐고 소개 줄만 빠진다(C-46). 그때
    로그에 '허브 가족 접두(노출 이름)는 마지막으로 온전히 읽은 표대로 둔다' 가 붙는다.
- **검색 손잡이** — `/health` 의 `search_tuning` 에 `switches_off: []` 그대로이고 `switches_on` 이 없다(비코어 낮추기는 꺼져 있다). 지문(`fingerprint`)은 새
  손잡이 칸 때문에 바뀐다 — update-all §7 의 '검색 손잡이' 줄에 새 지문이 보인다(덧씌우기가 없으면 기본값 지문과 같다).
- **보기** — 토큰 화면 '허브에 보일 앱' 탭 위에 '개인 Claude 보기' 칸이 보인다(화면 Drive 판을 받은 뒤). 칸 위에 '지금 허브는 보기를 아직 모릅니다' 가 뜨면
  게이트웨이가 이 판이 아니다(`/tools-map` 의 `views`). `/health` 의 `tools_list_by_view` 가 기동 뒤 보기별 tools/list 수를 센다(처음엔 모두 `full`). 포털
  보기는 머리 `X-HWAX-View: portal` 로 청한 연결에만 먹으므로, 리스크 심사 · 위키처럼 사람의 토큰으로 서버에서 도는 앱은 그 사람이 가벼운을 골라도 전체를 받는다(C-41).

### 8.3 사람 몫

- **비코어 낮추기를 켤지(결정 Q-1)** — 5절 M-6 의 정답(HG-01 원문 여덟 등)을 단 뒤 관리 → '도구 검색 검토' 의 '평가 돌리기'(또는 `run.py live --detail`)에서
  `+noncore_demote` 판을 본다. doc · box 의 hit@5 를 떨어뜨리지 않고 코어 box 쌍을 올리면 게이트웨이 `search_tuning.local.json` 에
  `{"switches": {"noncore_demote": true}}` 를 적는다(재기동 없이 다음 검색부터). 켜면 `/health` 에 `switches_on: ["noncore_demote"]` 가 붙고, 질의 기록 `via` 에
  `demote:noncore` 가 남는다. 그 뒤 16문항 재시험(OT-06 ~ 10 의 첫 도구가 코어인지). 앱 이름을 부른 질의('FMEA …' · 'ARP …')에는 그 앱 도구에
  `demote:noncore` 가 붙지 않아야 한다 — 어휘표 라벨 · 백엔드 키로 알아본다(C-44). 끄려면 그 줄을 지운다.
- **형제 소개 줄 문안(결정 Q-3)** — 운영자가 `~/Projects/HWAXPortal/backend/config/core_vocab.local.json` 에 쓴다. 라벨로 시작하고 120자 이내로, 사내 과제 이름 ·
  사람 이름은 넣지 않는다(에이전트 서버는 '[' 로 시작하는 설명에 앱 라벨을 다시 붙이지 않는다).

  ```json
  {"apps": {"failuretrace": {"tagline": "FailureTrace — <이 허브가 담은 것 한 줄>"},
            "caegroupdatahub": {"tagline": "CAE 그룹 Datahub — <이 허브가 담은 것 한 줄>"}}}
  ```

  저장하면 다음 재활 회차(60초)에 다시 집계해 그 형제 도구 설명 앞에 붙는다. `/health core_vocab.roles.sibling_taglines` 에 그 키가 보인다. 웹 챗 묶음의
  FailureTrace 도구 넷의 설명이 줄 길이만큼 는다. `search_tools` 의 순위는 바뀌지 않는다(줄은 점수에 들지 않는다) — 형제가 정본 아래로 접히면 `same_in` 의
  그 형제 칸에 `differs` 와 `tagline` 이 실린다(C-43). 바탕은 5절 M-8(허브의 자기소개)이다. Datahub DP-03(설치 소개를 도구 설명에)이 들어오면 이 줄을 걷는다.
- **보기 안내** — 개인 Claude 를 쓰는 사람에게 '허브에 보일 앱' 탭의 보기 칸을 알린다(기본은 모두 전체 — 결정 Q-9). 열린 세션은 재연결해야 목록이 바뀐다.
  보기는 이 판의 등록 배치 · 명령으로 붙인 Claude Code · Desktop 에만 먹는다 — 예전에 등록한 사람은 새 토큰으로 배치를 다시 받아 돌리거나 등록 설정의 hwax
  머리에 `X-HWAX-View: portal` 을 더한다(C-41). 리포에서 Claude Code 로 심의 · 리스크 워크플로를 돌리는 사람은 리포 `.mcp.json` 이 늘 full 을 청하므로
  영향이 없다(`HWAX_GATEWAY_VIEW` 로만 바꾼다 — `portal` 이면 사람 설정을 따른다).

### 8.4 되돌리기

| 무엇 | 끄는 법 | 반영 |
|---|---|---|
| 비코어 낮추기 | `search_tuning.local.json` 의 `noncore_demote` 줄을 지운다 | 다음 검색부터 |
| 형제 소개 줄 | `core_vocab.local.json` 의 그 `tagline` 을 지운다(`null`) | 다음 재활 회차 |
| 한 사람의 보기 | 그 사람이 토큰 화면에서 '전체' 로 저장(또는 연결 머리 `X-HWAX-View: full` · 머리를 지우면 그 연결은 전체) | 새 연결부터 |
| 허브 가족의 늘 접두 | 손잡이가 없다 — 옛 맨 이름은 호출 별칭으로 부르면 닿는다(목록 이름에 묶는 쪽은 아니다 — C-33 · C-47). 목록에서도 옛 이름이 꼭 필요하면 dev 에 알린다 | — |
