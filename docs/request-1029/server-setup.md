# 10-29 웹 챗 온톨로지 QA 후속 — cae00 반영 안내(수정 사항 · 받을 때 주의점 · 확인 · 사람 몫)

cae00 에서 이 묶음(1 · 2 · 3차와 4차 일부, 2026-10-29)을 받기 전에 읽는다. 무엇을 왜 바꿨는지는 같은 폴더의 [PLAN.md](PLAN.md) ·
[checklist.md](checklist.md) · [context-notes.md](context-notes.md)(C-1 ~ C-29)가 정본이다. 받는 길은 그대로
`git pull && update-all` 이다 — 포털 화면 · StepForge 는 dev 가 올린 Drive 판을 받는다.

## 1. 무엇이 바뀌었나

| 리포 | 받을 판 | 바뀐 것 |
|---|---|---|
| 포털(HWAXPortal) | main — 이 문서가 든 판 | 코어 어휘표 `backend/config/core_vocab.json`(정본) · 챗 중계가 상류 읽기를 화면 쓰기와 뗀다(숨은 탭에서도 답이 끝까지 저장된다) · 챗 침묵 한도 900초(심의와 뗐다) · 서버 대화 id 를 에이전트 서버에 싣는다 · 화면(중지 단추가 곧바로 풀린다 · 숨은 탭에서 돌아오면 서버 사본과 맞춘다) · update-all §6 '새 앱 점검' · env 킷 주석 손잡이 둘 |
| 에이전트 서버(HWAXAgentServer) | main `969e723` | 코어 데이터 규칙을 어휘표로 짓는다 · 챗 스트림에도 15초마다 ping · 자기검증은 바꿀 곳([원문] · [새 글])만 받는다(상한 4,096) · 도구 결과 머리에 앱 이름 · 같은 도구 네 번째에 '앞 결과를 써라' · 허브 큰 응답 접기 · 한자 · 가나 낱말을 자기검증에 짚는다 · 챗 LLM 호출에 대화 머리(`X-Session-Affinity`) · 프롬프트 앞부분 고정 · 도구 설명 예산 손잡이 |
| 게이트웨이(HWAXMcpGateway) | master `44f4b8d` | 코어 낱말 → 허브 읽기 도구(search_tools) · 정본 도구 설명 앞 소개 줄 · 같은 도구 사본은 정본 한 줄로 · 코어 질문은 '심의 · 토의 · 회의' 를 말할 때만 심의 도구를 올린다 · 시험 사본(stepforge-prod · dynaforge-prod)을 목록 · 검색에서 뺀다 · `tool_usage_report.py`(안 쓴 도구 보고) · DocForge 도구 영역 |
| StepForge | main `6907f8e`(D-647) · Drive SIF — **dev 가 push · SIF 를 올린 뒤에 든다**(그 전 update-all 은 지금 판 `dc0f697` 그대로 정상으로 뜬다) | `find_plm_task` 가 과제가 속한 프로젝트의 이름 · 별칭(마케팅명)으로도 찾는다(`matched_by` `project:<키>`) · 응답의 `sync` 는 요약(타입마다의 줄은 `system_capabilities.plm_hub` 에만) |

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
- 시험 사본(stepforge-prod · dynaforge-prod)을 일부러 쓰는 사람은 도구 이름으로 부른다 — 목록 · 검색에서만 빠졌다(C-18).
- 자기검증이 고칠 곳을 초안에서 못 찾으면 고치지 않고 초안을 그대로 낸다 — 답 아래 '검증하지 못해 초안을 그대로 보였습니다' 와 까닭이 뜬다(정상 동작).
