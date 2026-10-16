# 서버(cae00)에서 할 일 — 리스크 심사 M3(전원 · 거르기 · 쟁점 · 종합 보고서)

> 대상: cae00 운영자와 사용자 · **대조 시점 2026-10-15 · 리스크 앱 대조 커밋 `a27e569`(가지 `m3`, 단계 D)** · 보낸 쪽: dev(이 리포 `docs/risk-review-redesign/`).
> 이 문서는 세 꾸러미(엔진·운영 · 셀 · 쟁점·종합)의 cae00 몫을 한 파일에 모은다. 1절(엔진·포털)과 3절(M0-b 보강)은 지금 할 수 있다. 2절 이하는 리스크 앱 M3 가 이 박스에 닿은 뒤다 — dev 가 `m3` 를 main 에 합쳐 push 하고 hwax-risk SIF 를 Drive 에 올렸다고 알리면(SIF 해시 앞 8자와 함께) 시작한다. 그 판은 `a27e569` 를 품고, 2절 이하의 칸 이름·기본값·문구는 그 커밋의 코드와 대조했다.
> 대조한 판 — 리스크 앱 `a27e569`(스키마 v5 · MCP 도구 31종) · 에이전트 서버 `c4e4823`(카드 대조 M3 엔진 · 비우기) · 포털 `ce9bdbc`(update-all 비우기). 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.
> 이 박스의 지금 상태는 이 문서가 알지 못한다. 그래서 확인마다 재는 명령을 적었다.

## 0. 한눈에

> **먼저 — 보안 핫픽스(10-15).** M2 리스크 앱에 남이 다른 사람의 대상으로 등록부 병합을 부를 수 있는 길이 있었다(대상의 존재·크기가 새고 그 원장 행이 바뀐다). main `12130f9` 로 고쳤고 SIF 를 Drive `latest/` 에 올렸다(`hwax-risk.sif.hash` 앞 8자 `e7b78675`). M3 와 상관없이 다음 update-all 에 들어간다. (같은 날 뒤에 M3 판 `a368c86` 의 SIF 가 Drive `latest/` 를 이어받았다 — 그 판이 핫픽스를 담는다. 그 뒤 M3 뒤처리 넷을 담은 `d18e9d6`(D-55), 다시 Claude 길 X-2 를 담은 `54c4385`(10-16 — 판단 LLM 선택, 기본 GLM)가 이어받았다 — 지금 Drive 의 해시 앞 8자는 `eee3240f` 이고, M3 를 받으면 2절의 v5 이행이 함께 온다.)

M3 는 M2 의 카드 대조를 대표 9명에서 **전원(359명)** 으로 넓히고, 관련 없는 영역을 거르되 누락을 막는 장치를 두고, 갈린 판정을 **쟁점 패널**로 다시 보고, 영역 요약과 **종합 보고서**를 낸다(M3.md 1절).

- **지금 할 수 있는 것** — 1절(에이전트 서버 카드 대조 엔진과 포털의 update-all 비우기 반영) · 3절(M0-b 탐침 보강 팔). 리스크 앱이 M2 인 동안은 새 엔진의 카드 대조 상한이 8 이어도 앱 워커가 4 라 실제로는 4건까지 돈다.
- **리스크 앱 M3 가 닿은 뒤** — 2절(리스크 앱 M3 반영 · 손잡이 · 배정표 승인) · 4절(M2 파일럿을 M3 엔진·앱으로) · 5절(M3 전원 실주행) · 6절(종합 보고서 읽기 — 사용자).
- 차례 — 1절 → 3절(M0-b) → K·출력 상한 적기(dev 가 M0-b 로 정한 값) → M0-d(실제 변경 비교) → 2절 → 4절 → 1-5(챗 지연 기준선) → 5절 → 6절. M3.md 9절은 파일럿을 앱 M3 앞에 두었지만 단계 D 가 끝나 앱이 먼저 준비됐다(4절 머리). 배정표 승인(2-6)은 5절 전이 좋다 — 늦으면 첫 전원 실주행은 거르기 없이 돈다.
- 바뀌는 것 — 1절은 에이전트 서버 코드(카드 대조 프롬프트 판이 오른다)와 포털 update-all 의 한 절, 2절은 리스크 앱 SIF 와 원장 스키마(v4 → v5 — 이행 전 사본이 남는다)다. 설정 파일은 바꾸지 않는다. 손잡이는 전부 선택이다(2-5 · 7절).

## 1. 엔진·포털 반영 — 지금

### 1-1. 전제 — 도는 검토 잡이 없을 때

새 엔진은 카드 대조 프롬프트 판을 올린다(`cr-sweep-2` · `cr-verdict-2` · `cr-offcard-2` · 공식 `cr-l2`). 도는 M2 검토 잡이 있으면 그 잡의 셀이 판이 바뀐 것을 보고 **처음부터 다시 돈다**(끝난 셀의 호출이 버려진다 — M3.md #37). 그래서 검토 잡이 없을 때 반영한다.

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | 살아 있는 리스크 잡이 없다 | 포털 리포 루트에서 `./infra/scripts/risk-review-inventory.sh` | `잡 상태별:` 에 `queued`·`running`·`paused`·`cancelling` 이 없다(패널 잡도 함께 세므로 넉넉하게 막는다). 있으면 끝난 뒤에 한다 |
| 2 | 지금 엔진이 무엇을 아는가(전) | 아래 명령 | 반영 전이면 `"capabilities":["card_review"]` 이고 `drain` 이 없다 |

```bash
curl -s --noproxy '*' http://127.0.0.1:9009/health | grep -oE '"capabilities": *\[[^]]*\]|"draining": *(true|false)'
```

### 1-2. update-all 한 번

평소처럼 update-all 을 돌린다. 이번 실행에서 볼 줄.

- `1h) 리스크 검토 비우기` 절 — **첫 실행은 ○ 다.** update-all 이 이 절을 지날 때는 아직 옛 엔진이 떠 있어서 `○ 리스크 검토 비우기 — 에이전트 서버가 /drain 을 모른다(옛 판) — 이번 재기동에 끊긴 카드 대조는 리스크 앱이 차감 없이 다시 돌린다` 가 정상이다. 엔진은 뒤의 재기동에서 바뀐다.
- 에이전트 서버 재기동 — 도는 심의가 있으면 `○ agent-server 재기동 건너뜀 — 심의 N건 진행 중, M건 대기` 로 미룬다. 그러면 1-3 의 확인이 반영 전 값을 보인다. 심의가 끝난 뒤 update-all 을 한 번 더 돌린다.
- §6 끝 상태 점검 — 반영됐으면 `리스크 검토` 줄이 생긴다(1-4).

### 1-3. 반영 확인

```bash
curl -s --noproxy '*' http://127.0.0.1:9009/health > /tmp/h.json
grep -oE '"capabilities": *\[[^]]*\]' /tmp/h.json
grep -oE '"rev": *"[^"]*", *"kinds": *\[[^]]*\]' /tmp/h.json
grep -oE '"limit": *[0-9]+, *"limit_reason": *"[a-z_]*"' /tmp/h.json
grep -oE '"request_worst_s": *([0-9.]+|null)' /tmp/h.json
grep -oE '"prompt_rev": *\{[^}]*\}' /tmp/h.json | head -1
```

| 줄 | 기대 |
|---|---|
| `capabilities` | `["card_review", "drain"]` |
| `kinds` | `noinput`·`summary` 를 포함한 다섯 |
| `limit` · `limit_reason` | `8` · `normal`(사람이 띄운 심의가 돌면 `4` · `delib_human`, 비우기 중이면 `0` · `draining`) |
| `request_worst_s` | 18000 보다 작다(리스크 앱의 호출 벽시계 — 크면 앱이 먼저 끊는다) |
| `prompt_rev` | `sweep` 이 `cr-sweep-2`, `verdict` 가 `cr-verdict-2` |

`drain` 이 없으면 에이전트 서버가 아직 옛 판이다(1-2 의 재기동이 미뤄졌다).

### 1-4. 비우기 읽는 법

update-all 이 재기동 전에 카드 대조를 비우고 끝에서 정리한다. 실패해도 배포는 간다(비치명). 두 번째 실행부터 보이는 줄.

| 어디서 | 줄 | 뜻 |
|---|---|---|
| 1h | `· 세웠다 — 깃발 on(scope all · by update-all · 남은 N초) · 카드 대조 N건 · 심의 a건 진행·q건 대기. …` | 새 카드 대조·새 패널을 멈췄다. § 머리마다 1800초로 늘린다 |
| 1h | `· 도는 카드 대조 N건 — 끝나기를 최대 300초 기다린다(HWAX_DRAIN_WAIT_S)` → `· 카드 대조가 비었다(N초) — 재기동으로 넘어간다` | 정상 |
| 1h | `· 300초 안에 끝나지 않은 카드 대조 N건은 재기동에 끊길 수 있다 — 리스크 앱이 차감 없이 다시 돌린다` | 정상(⚠ 아님). 끊긴 호출의 LLM 시간만 버려진다 |
| 1h | ○ `… 사람이 고정한 깃발(by X · scope all · drain_held) — 건드리지 않는다(…)` | 사람의 고정이다. update-all 은 늘리지도 내리지도 않는다 |
| 1h | ○ `… 다른 주체가 세운 깃발(by X · scope … · drain_owned) — 건드리지 않는다(그 깃발이 풀리면 § 머리에서 update-all 이 제 깃발을 세운다)` | 누가 손으로 세운 수명 있는 깃발이다. 그것이 풀리면 update-all 이 이어받는다 |
| § 머리 | `· 리스크 검토 비우기 — 다른 주체의 깃발이 없어져 update-all 이 깃발을 세웠다 — 깃발 on(…)` | 위의 이어받기. 그 뒤는 평소대로 늘리고 끝에서 정리한다 |
| § 머리 | ○ `리스크 검토 비우기 — update-all 의 깃발이 수명 전에 내려갔다(누군가 내렸다) — 다시 세우지 않고 끝에서도 건드리지 않는다` | 실행 중에 누가 `off --force` 했다. 이번 실행은 비우기 없이 간다 |
| § 머리 | ○ `… update-all 의 깃발이 수명 전에 다른 주체(by X)의 것이 됐다 — 더 늘리지 않고 끝에서도 건드리지 않는다` | 실행 중에 누가 깃발을 고정으로 가져갔다 |
| § 머리 | ○ `… 수명 전에 다른 주체(by X)의 것이 됐다(고정 아님) — 건드리지 않는다(그 깃발이 풀리면 § 머리에서 다시 세운다)` | 실행 중에 누가 수명 있는 깃발로 가져갔다. 풀리면 update-all 이 다시 세운다 |
| § 머리 | ○ `… 늘리려다 다른 주체가 세운 깃발(…) 을 만났다 — 건드리지 않는다(그 깃발이 풀리면 § 머리에서 다시 세운다)` | 위와 같다(늘리는 순간에 만났다) |
| § 머리 | ○ `… 늘리려다 사람이 고정한 깃발(…) 을 만났다 — 더 늘리지 않고 끝에서도 건드리지 않는다` · ○ `… 세우려다 사람이 고정한 깃발(…) 을 만났다 — …` | 사람의 고정 — 이번 실행은 그 깃발에 맡긴다 |
| 1h | ○ `… 에이전트 서버가 받지 않는다(내려가 있다 — 끊길 카드 대조가 없다)` | 정상 |
| 1h | ⚠ `… 4초 안에 답하지 않았다(매달림). 깃발 없이 간다(비치명)` | 에이전트 서버가 바쁘거나 멈췄다. 배포는 간다 |
| 1h | ⚠ `리스크 검토 비우기 실패 — 에이전트 서버가 요청을 거절했다(HTTP 422 …)` | 옛 판이 아니라 진짜 거절이다. `../HWAXAgentServer/agent-server.log` 의 `[drain]` 줄을 dev 에 보낸다 |
| 끝 | `· 리스크 검토 비우기 — 깃발을 내렸다(카드 대조·새 패널이 이어 돈다)` | 정상 |
| 끝 | ○ `리스크 검토 비우기 유지(새 패널만 멈춤) — 미룬 재기동이 있다(<이름>). …` | 심의 때문에 재기동을 미뤘다. 카드 대조는 곧 다시 돌고 새 패널만 멈춘다. 심의가 끝나면 30분 창이 열리고, 그 안에 update-all 을 다시 돌리면 미룸 없이 지나가며 깃발이 내려간다 |
| 끝 | ⚠ `… 깃발을 내리지 못했다(…). 수명(1800초)이 지나면 스스로 풀린다(비치명)` | 30분 뒤 저절로 풀린다 |
| §6 | ✓ `리스크 검토      비우기 깃발 … · 도는 카드 대조 N건 · 챗 첫 조각 p50 Xms(평소 Yms)` | 정상 |
| §6 | ⚠ 같은 줄 + `· 챗 첫 조각 지연이 평소의 2배를 넘는다(…) — 카드 대조가 챗을 밀어낸다. …` | 1-6 |

손으로 보고 다루기(포털 리포 루트).

```bash
./infra/scripts/review-drain.sh status          # 지금 깃발
./infra/scripts/review-drain.sh on --ttl 3600   # 1시간 비우기(최대 21600 — 넘기면 21600 으로 자른다)
./infra/scripts/review-drain.sh on --hold       # 사람의 고정 — 내릴 때까지(update-all 도 건드리지 않는다)
./infra/scripts/review-drain.sh off             # 내 깃발 내리기 · 남의 깃발이나 고정은 off --force
```

알려진 한계 둘 — ① update-all 은 깃발이 꺼진 것을 '누가 내렸다' 로 볼지 시각으로 가른다(제 수명 끝 30초 안에 내린 것은 다시 세운다). ② 깃발 파일을 잃는 재기동(경로를 바꿔 띄움)은 '누가 내렸다' 로 읽혀 그 실행은 비우기 없이 간다. 둘 다 끊긴 카드 대조는 리스크 앱이 차감 없이 다시 돌린다.

`review-drain.sh` 의 종료코드 — 0 됐다 · 2 에이전트 서버가 받지 않는다 · 3 옛 판(`/drain` 없음) · 4 매달림 · 5 사람의 고정 · 6 거절(422·503 — 진짜 실패) · 7 다른 주인의 깃발.

### 1-5. 챗 지연 기준선 — 실주행 전 한 시간

전원 실주행(5절) 동안 카드 대조가 챗을 얼마나 늦추는지 보려면 평소 값이 있어야 한다. 실주행 한 시간 전부터 끝까지 켜 둔다(에이전트 서버 리포 루트).

```bash
.venv/bin/python scripts/llm_ttft_probe.py --dry-run --count 3      # 계획만(LLM·/health 를 부르지 않는다)
.venv/bin/python scripts/llm_ttft_probe.py --out ttft-<날짜>.jsonl   # Ctrl-C·TERM 이면 요약을 쓰고 끝낸다
```

1분마다 1토큰짜리 요청을 보내 첫 조각까지의 초와 그때의 카드 대조·심의 수를 적는다. 카드·과제 원문은 보내지 않는다. 끝나면 파일을 dev 에 보낸다.

### 1-6. 챗이 느리다는 ⚠ 를 봤을 때

카드 대조 동시 수를 낮춘다. **재기동 없이는 바뀌지 않는다.** 에이전트 서버 리포의 `.env` 에 적고, 도는 심의가 없을 때 다시 띄운다.

```bash
# ../HWAXAgentServer/.env
CARD_REVIEW_CONCURRENCY=4          # 기본 8. 사람이 띄운 심의 중 값은 따라서 절반(2)이 된다
```

```bash
cd ../HWAXAgentServer && ./start.sh -d
```

`start.sh` 는 심의가 돌면 `○ agent-server 재기동 건너뜀 — …` 로 멈춘다. 그때는 끝난 뒤 다시 한다.

### 1-7. 되돌리기 — 가벼운 것부터

1. **깃발** — `./infra/scripts/review-drain.sh on --hold` 로 카드 대조를 통째로 멈춘다(챗·심의는 그대로). 푸는 것은 `off --force`.
2. **손잡이** — 1-6 의 `CARD_REVIEW_CONCURRENCY` 를 1 로.
3. **판** — 엔진을 앞 판으로 돌려야 하면 dev 에 알린다. dev 가 되돌림 커밋을 올리고 update-all 로 받는다(박스에서 직접 `git checkout` 하지 않는다 — 다음 update-all 이 다시 덮는다).

## 2. 리스크 앱 M3 반영

스키마 v5 · MCP 도구 31종(`risk_get_issues` · `risk_get_report` 를 더했다) · 앱 워커 기본 8 · 실패 셀 처분 · 쟁점과 종합 보고서의 사슬이 이 판에 든다. 앱은 update-all 이 Drive 의 hwax-risk SIF 로 바꾼다(박스에서 빌드하지 않는다). 매니페스트(`launch.env`)는 바뀌지 않았다.

### 2-1. 전제 — 재는 것

데이터 디렉터리를 먼저 정한다(`server-setup-m2.md` 2-1 과 같다).

```bash
cd ~/Projects/HEAXHub
D="$(readlink -f var/app_data/hwax_risk)" && echo "$D"
```

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | 1절이 들어와 있다 | 1-3 의 명령 | `capabilities` 에 `drain`, `limit` 8(사람이 띄운 심의 중이면 4) |
| 2 | 카드 대조 스위치가 켜져 있다 | `grep -n '^HWAXRISK_REVIEW_ENABLED' "$D/knobs.env"` | `HWAXRISK_REVIEW_ENABLED=1`. 없으면 `server-setup-m2.md` 2절 |
| 3 | 살아 있는 리스크 잡이 없다 | 포털 리포 루트에서 `./infra/scripts/risk-review-inventory.sh` | `잡 상태별:` 에 `queued`·`running`·`paused`·`cancelling` 이 없다. 있으면 끝난 뒤에 한다 — 새 앱은 셀 지문을 그 셀이 부르는 종류의 판으로 다시 세어, 도는 M2 셀을 처음부터 돌린다(차감은 없다) |
| 4 | 이행 사본을 뜰 자리가 있다 | 아래 명령 | 남은 바이트가 원장과 `-wal` 합의 1.2배 이상 |
| 5 | dev 가 판을 올렸다 | 아래 값 | 리스크 앱 main `54c4385`(M3 `a368c86` · 뒤처리 D-55 `d18e9d6` 에 Claude 길 X-2 — 판단 LLM 선택은 기본 GLM, 켜지 않으면 동작 그대로 · 보안 핫픽스 `12130f9` 포함), hwax-risk SIF 해시 앞 8자 `eee3240f`(10-16 Drive `latest/`) |

```bash
du -cb "$D"/risk_review.db "$D"/risk_review.db-wal 2>/dev/null | tail -1   # 원장과 -wal 의 합(바이트)
df -B1 --output=avail "$D" | tail -1                                       # 남은 바이트
ls -l "$D"/risk_review.db.pre-* 2>/dev/null                                 # 이미 있는 사본(갈래마다 새것 둘만 남긴다)
```

(권고) 파일럿 대상이 패널을 돌린 뒤 cells 로 바꾼 것이면, M3 의 첫 병합이 그 등록부를 카드 대조 finding 까지 넣어 다시 세운다(M3.md 8절). 이행이 원장 전체를 `pre-migrate-v4-*` 로 떠 두므로 따로 할 일은 없고, 바꾸기 전 모양은 M3 뒤에 웹·REST 의 `registry?source=panels`(저장 없는 비교 보기)가 보인다. 사람이 읽을 사본을 따로 원하면 대상 소유자가 로그인한 브라우저에서 `/apps/hwax_risk/api/export?since=0` 을 열어 JSONL 을 받는다(이 박스에 반출 자격 그룹이 정해져 있고 그 밖의 계정이면 403 `export_not_allowed`).

### 2-2. update-all 한 번

평소처럼 update-all 을 돌린다. 이번 실행에서 볼 줄.

- `2) deploy-all-from-drive` 의 HEAX Hub 구획 — 도는·줄 선 심의(리스크 앱의 패널 포함)가 있으면 `heax 재기동 건너뜀` 줄과 '새 앱 SIF·frontend/dist 를 받지 않았고 … 허브와 앱은 옛 것 그대로다' 로 미룬다. 그러면 2-3 의 확인이 4 를 보인다 — 심의가 끝난 뒤 update-all 을 한 번 더 돌린다.
- 리스크 앱은 새 SIF 로 처음 뜰 때 v5 이행을 돌린다(2-3). 기동이 실패하면 `var/logs/integration_hwax_risk.log`(HEAXHub 리포) 끝에서 아래 문구를 찾는다.

| 문구 | 뜻 | 할 일 |
|---|---|---|
| `이행 전 사본을 뜰 여유 공간이 없다 — 남은 …바이트 < 필요 …바이트(DB × 1.2). v4 에서 올리지 않고 기동을 멈춘다.` | 사본 자리가 모자란다(아무것도 바꾸지 않았다) | 데이터 디렉터리의 디스크를 비우고 앱만 다시 띄운다(2-5 의 `redeploy-app.sh`) |
| `이행 전 사본을 뜨지 못했다(…) — v4 에서 올리지 않고 기동을 멈춘다.` | 복사가 실패했다 | 같다. 그래도면 줄 전체를 dev 에 보낸다 |
| `마이그레이션 v5 실패: …` | v5 한 트랜잭션이 되돌아갔다(원장은 v4 그대로, 사본은 남는다) | 줄 전체를 dev 에 보낸다 |
| `DB 스키마 버전(5)이 앱 코드(4)보다 높습니다 — 앱을 갱신하세요.` | 옛(M2) SIF 가 v5 원장을 열었다 | 새 SIF 가 아직 닿지 않았다 — update-all 을 다시 돌린다 |

### 2-3. v5 이행 — 무엇이 일어나고 어떻게 보나

새 SIF 로 처음 뜰 때 한 번 돈다(같은 데이터 디렉터리에 둘이 떠도 `migrate.lock` 이 줄 세운다).

1. 쓰기 앞 로그(WAL)를 원장에 접고, 남은 자리가 원장과 `-wal` 합의 1.2배 이상인지 본다.
2. 원장 전체를 `risk_review.db.pre-migrate-v4-<에포크 초>` 로 뜬다(`.tmp` 로 쓰고 다 쓰면 이름을 바꾼다). 같은 v4 사본이 있고 그 뒤로 원장이 바뀌지 않았으면 다시 뜨지 않는다.
3. v5 를 한 트랜잭션으로 적용한다 — 새 표 다섯(`rr_issues` · `rr_summaries` · `rr_reports` · `rr_close_acks` · `rr_unit_live`), 새 열 열셋(잡 · 패널 · 등록부 · 대상), 새 색인, 그리고 클러스터 별칭 표 `rr_cluster_alias` 를 소유자별 열쇠로 다시 짓는다(있던 별칭 행은 그 행의 주인 것으로 옮긴다). 그 밖의 원장 행은 그대로다 — 패널 대상의 등록부는 바이트로 같다.
4. 사본은 갈래(pre-migrate · pre-merge)마다 새것 둘만 남긴다.

확인(`D` 는 2-1 에서 정한 값이다).

```bash
cd ~/Projects/HWAXPortal
./infra/scripts/risk-review-inventory.sh | grep -E '스키마 버전|잡 상태별'
ls -l "$D"/risk_review.db.pre-migrate-v4-*
cut -c1-8 ../HEAXHub/var/sifs/hwax-risk.sif.hash
apptainer exec instance://heax_app_hwax_risk grep -c '^@mcp.tool' /app/backend/app/mcp_server.py
```

| 줄 | 기대 |
|---|---|
| `스키마 버전:` | `5` |
| `risk_review.db.pre-migrate-v4-…` | 하나 있고 크기가 이행 전 원장과 비슷하다 |
| SIF 해시 앞 8자 | `eee3240f`(10-16, `54c4385`) |
| `@mcp.tool` 수 | `31`(떠 있는 앱의 소스) |

관리자 계정으로 로그인한 브라우저의 `/apps/hwax_risk/api/meta/runtime` 에서도 `schema_version` 이 5 다(2-5 의 손잡이도 거기 보인다).

되돌리기 — 옛 SIF 는 v5 원장을 열지 못한다(2-2 표의 마지막 문구). 내려야 하면 dev 에 알린다. 옛 SIF 와 사본 되돌림(`pre-migrate-v4-…` → `risk_review.db`)을 함께 하고, 그 사이에 쓴 것은 잃는다(`server-setup-m2.md` 9절과 같은 방식).

### 2-4. 게이트웨이 — 도구 31종과 새 인자

배포본 게이트웨이에 실제로 뜨는지 게이트웨이에 묻는다(`server-setup-m2.md` 7절의 대조 스크립트 그대로). 떠 있는 앱의 사본(`/app/backend/scripts/rr_gateway_check.py`)을 돌리면 그 기대 목록이 곧 배포본이다.

```bash
read -rs HWAX_GATEWAY_PAT && export HWAX_GATEWAY_PAT       # 포털 개인 토큰 — 화면·기록에 남지 않는다
apptainer exec instance://heax_app_hwax_risk python3 /app/backend/scripts/rr_gateway_check.py
```

기대 — `[기대] app/mcp_server.py 의 도구 31종` 과 `판정 0 — 이상 없음: 도구 31종이 게이트웨이에 있고 risk_get_units 이 실제로 답한다`. 다른 판정은 `server-setup-m2.md` 7절의 표를 따른다.

이어서 같은 셸에서 새 인자와 근거 꾸러미 도구 둘이 그 PAT 의 시야에 있는지 본다(읽기만 한다).

```bash
apptainer exec instance://heax_app_hwax_risk python3 - <<'PY'
import os, sys
sys.path.insert(0, "/app/backend/scripts")
import rr_gateway_check as g
c = g.McpClient(os.environ.get("HWAX_GATEWAY_URL") or g.DEFAULT_URL, os.environ["HWAX_GATEWAY_PAT"])
try:
    init = c.request("initialize", {"protocolVersion": g.PROTOCOL_VERSION, "capabilities": {},
                                    "clientInfo": {"name": "m3-args", "version": "1"}})
    c.version = str(init.get("protocolVersion") or g.PROTOCOL_VERSION)
    c.notify("notifications/initialized")
    tools, cursor = [], None
    for _ in range(50):
        page = c.request("tools/list", {"cursor": cursor} if cursor else {})
        tools += [t for t in page.get("tools") or () if isinstance(t, dict)]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    by_name = {str(t.get("name")): t for t in tools}
    for want in ("risk_job_action", "compare_reports", "compare_materials"):
        got = g.exposed_as(want, sorted(by_name))
        props = sorted(((by_name.get(got) or {}).get("inputSchema") or {}).get("properties") or {}) if got else []
        print(want, "→", got or "없음", props if want == "risk_job_action" else "")
finally:
    c.close()
PY
unset HWAX_GATEWAY_PAT
```

| 줄 | 기대 | 다르면 |
|---|---|---|
| `risk_job_action → …` | 인자에 `action` · `consent` · `filter` · `job_id` · `reason` | `consent`·`filter`·`reason` 이 없으면 게이트웨이가 옛 목록을 쥐고 있다 — 1분 뒤 다시, 그래도면 앱만 다시 띄운다(2-5) |
| `compare_reports → …` · `compare_materials → …` | 이름이 나온다 | `없음` 이면 그 계정의 시야에 그 도구가 없다. 근거 꾸러미(B 층)가 그 호출을 `live_denied` 로 적고 단위를 `partial` 로 얼린다(잡은 돈다). 그 계정의 포털 권한과 토큰 화면에서 그 앱이 켜져 있는지 본다 |

M2 의 `risk_job_action` 은 `job_id` · `action` 둘뿐이었다. 새 action `retry_failed` · `skip_failed` 와 `consent` 는 4-2 · 5-5 에서 쓴다.

### 2-5. 손잡이 — 이 박스의 값

리스크 앱 손잡이는 `$D/knobs.env` 에 적는다(환경변수 > `knobs.env` > 코드 기본값 — 매니페스트 `launch.env` 에는 적지 않는다). 기동 때 한 번 읽으므로 고친 뒤에는 앱을 다시 띄운다(도는 검토 셀 · 요약은 차감 없이 이어 돌지만 도는 쟁점 패널은 닫혀 그 잡이 멈춘다 — 5-5). 값과 출처는 관리자 `/apps/hwax_risk/api/meta/runtime` 의 `knobs` 가 `{value, source}` 로 보인다. 잡은 만들 때의 값을 얼린다 — 도는 잡은 손잡이를 바꿔도 그대로다.

```bash
grep -n '^HWAXRISK_' "$D/knobs.env" 2>/dev/null                          # 이 박스가 적어 둔 것(없으면 전부 코드 기본값)
cd ~/Projects/HEAXHub && deploy/apptainer/redeploy-app.sh hwax-risk       # 고친 뒤 앱만 다시 — 쟁점 패널이 돌지 않을 때
```

| 이름 | 코드 기본 | 뜻 |
|---|---|---|
| `HWAXRISK_REVIEW_CONCURRENCY` | **8**(M2 는 4) | 앱의 검토 워커 수. 에이전트 서버 관문(`limit`)을 넘겨 띄우지 않는다. M2 때 `knobs.env` 에 4 를 적어 두었으면 그 줄이 이긴다 — 8 로 돌리려면 줄을 지우거나 고친다 |
| `HWAXRISK_REVIEW_FILTER` | `on` | 관련 없는 셀 거르기 — `off` · `shadow`(분류만 적고 거르지 않는다) · `on`. **배정표가 초안인 동안은 손잡이와 상관없이 아무것도 거르지 않는다**(2-6) — `shadow` 도 그동안은 거를 수 있던 셀을 0 으로 잰다 |
| `HWAXRISK_FILTER_AUDIT_PCT` | 5 | 거를 셀 가운데 끝까지 판정하는 표본(%). 바닥 59건 · 영역마다 1건은 코드 상수다 |
| `HWAXRISK_REVIEW_DUAL` | `flagged` | 이중 판정 — `flagged`(걸린 카드만 순서를 뒤집어 다시 보고, 영역 1순위는 보정용으로 묶음 전체) · `all`(M2 동작) |
| `HWAXRISK_REVIEW_DUAL_NEG_PCT` | 10 | 1순위 보정에서 '걸림 없음 → 걸림' 이 5% 를 넘은 대상에서 걸림 없는 묶음을 무작위로 다시 보는 비율(%). 0 이면 켜지지 않는다 |
| `HWAXRISK_EVIDENCE_LIVE` | 1 | 근거 꾸러미 실호출(B 층) — 단위마다 `compare_reports` · `compare_materials` 를 그 잡의 사용자 PAT 로 한 번 불러 언다(잡 단계 `live`). 0 이면 호출 0 이고 단위가 `none` 이다 |
| `HWAXRISK_REVIEW_CONSENT_CALLS` | 1,500 | 잡을 만들 때 동의가 필요한 호출 추정(`calls_estimate.expected` — 거르기 없음 가정과 견준다) |
| `HWAXRISK_REVIEW_MAX_CALLS` | 30,000 | 넘으면 잡을 만들지 않는 상한(409 `review_too_large`). 도는 잡의 추정 합(처음 추정 + 다시 연 셀 몫)도 이것을 넘지 않는다(보류 `max_calls`) |
| `HWAXRISK_ISSUE_PANEL_CAP` · `HWAXRISK_ISSUE_PANEL_HARD_CAP` | 24 · 48 | 과제당 쟁점 패널 — P1 을 48 까지 먼저, P2 · P3 은 합계가 24 에 닿을 때까지. 상한 밖은 '미토의 쟁점' |
| `HWAXRISK_ISSUE_SPLIT_MIN_OPPOSERS` | 2 | '갈린 판정' 쟁점의 최소 반대자 수 |
| `HWAXRISK_ISSUE_MAX_CHARGED` | 2 | 쟁점 하나의 내용 탓 실패 한도(넘으면 판정 못 함) |
| `HWAXRISK_SUMMARY_MAX_CHARGED` · `HWAXRISK_SUMMARY_INFRA_MAX` | 2 · 6 | 요약 하나의 내용 탓 · 인프라 실패 한도(넘으면 서술 없이 코드 조립본) |

쟁점 패널은 하루 패널 상한(`HWAXRISK_DAILY_PANEL_CAP` 24 — 매니페스트 손잡이)에 세지 않는다. 다시 연 셀의 여유(`max(ceil(0.2 × 동의받은 추정), 30)`)는 코드 상수다.

### 2-6. 배정표 승인 — 사용자

거르기의 코드 신호는 두 표에서 나온다 — 메커니즘 → 영역 배정표(`mech-owners.v1.json`, 52행)와 변경 → 메커니즘 · 부품 역할 표(`change-routing.v1.json`, 변경 코드 97). `a27e569` 에서 둘 다 `review_status: "draft"` 다.

- **승인 전** — 코드 신호가 모든 영역에 '모름' 을 내어 아무 셀도 걸러지지 않는다. 진행판 `review.filter.approved` 가 `false` 이고 `filtered` 가 0 이다. 전원 실주행은 약 1만 5천 호출 이상(동시 8 · 호출 5분이면 약 7일)이다(5-7).
- **누가** — 사용자가 [review-tables.md](review-tables.md) 를 훑고 '고르실 것' 넷(이대로 승인 · `drop_stress` 의 관련 영역 좁히기 · xd 좁히기 · 고칠 칸 직접) 가운데 하나를 dev 에 알린다. dev 가 두 파일의 `review_status` 를 `approved` 로 바꾸는 커밋 하나(`reviewed_by` · `reviewed_at` 과 함께)를 만들어 SIF 와 함께 올린다. 표는 SIF 안의 자산이라 박스에서 고치지 않는다.
- **승인 뒤 바뀌는 것** — 그 SIF 가 뜬 뒤 **새로 만드는 검토 잡부터** 거른다. 잡은 만들 때 승인 상태를 얼리므로 도는 잡은 그대로다. 영역 1순위 대표는 어느 경우에도 거르지 않고, 코드 신호와 그 전문가의 훑기가 둘 다 무관일 때만 거르며, 거를 셀의 5%(최소 59건 · 영역마다 1건)는 끝까지 판정해 놓친 걸림을 잰다. 놓친 걸림이 나온 영역은 그 대상에서 넓혀(거른 셀을 다시 연다) 셋째 영역에서 대상 전체 거르기를 끈다. 거른 셀은 보고서와 완결 표기에 '거름 — 까닭' 으로 남는다.

이 박스에 떠 있는 표의 상태를 잰다.

```bash
apptainer exec instance://heax_app_hwax_risk python3 -c 'import json; [print(f, json.load(open("/app/backend/app/assets/" + f)).get("review_status")) for f in ("mech-owners.v1.json", "change-routing.v1.json")]'
```

기대 — 지금은 두 줄 다 `draft`, 승인 SIF 가 뜬 뒤에는 둘 다 `approved` 다. 잡을 만든 뒤에는 Claude `risk_get_coverage(target_key='diff:…', with_seats=false)` 의 `review.filter.approved` 가 그 잡이 얼린 값이다.

## 3. M0-b 탐침 보강 팔 — 지금

M2 의 M0-b 를 `server-setup-m0b.md` 대로 돌리되, 1절을 반영한 뒤 보강 팔 셋을 더한다(탐침 판 `m0b-2`). 기본 탐침의 계획은 그대로이고 고른 팔만 더한다.

| 팔 | 재는 것 |
|---|---|
| `agree` | 같은 점검 카드 K 장을 한 묶음으로 한 번, 한 장씩 K 번 불러 카드별 판정 일치율과 '걸림 → OK·na' 뒤집힘 수 — K 가 판정을 바꾸는가 |
| `merged` | 판정과 카드 밖을 한 프롬프트로 묻는 틀(탐침 안에만 있다)과 따로 부른 두 호출의 견줌 — 합치면 호출이 줄어드는가 |
| `summary` | 합성 등록부 행 300·1,500·3,000개로 요약을 불러 초·빠진 꼭 다룰 행 — 종합 보고서의 꼬리 |

```bash
cd ../HWAXAgentServer
.venv/bin/python scripts/m0b_probe.py --agent <전문가 키> --extra all --dry-run
.venv/bin/python scripts/m0b_probe.py --agent <전문가 키> --extra all --out m0b-m3-<날짜>.jsonl
```

토큰·멈춤·결과 보내기·지우기는 `server-setup-m0b.md` 2-2 · 2-5 · 3 · 4절 그대로다. 결과로 dev 가 K·출력 상한·호출 초를 다시 정해 이 문서 최종본(7절)에 적는다.

## 4. M2 파일럿을 M3 엔진·앱으로

`server-setup-m2.md` 의 파일럿을 1절(엔진)과 2절(앱)을 반영한 박스에서 돈다. M3.md 9절은 파일럿을 앱 M3 전에 두었지만 단계 D 가 끝나 앱이 준비됐다 — 파일럿도 M3 앱에서 돌아 보고서를 M3 모양(`expert-report-2`)으로 읽는다. 엔진이 먼저 올라 있어야 하는 것(파일럿이 판정 틀 `cr-verdict-2` 로 돌아 걸린 줄에 메커니즘을 갖는다 — M3.md #37)은 그대로다. 이미 M2 앱으로 돌았으면 4-3 이다.

### 4-1. M2 절차서와 다른 곳

| M2 절차서의 자리 | M3 에서 |
|---|---|
| 1절 확인 1 · 5 `스키마 버전:` | `5` 다 |
| 1절 확인 6 `/health` | `capabilities` 가 `["card_review", "drain"]`, `limit` 8(1-3) |
| 1절 확인 7 · 7절 게이트웨이 대조 | 기대 도구 31종과 새 인자(2-4) |
| 2절 켜기 · 2-4 들었는지 | `HWAXRISK_REVIEW_ENABLED=1` 그대로다. `/api/meta/runtime` 의 `schema_version` 이 5 이고 `knobs` 에 2-5 의 손잡이가 보인다 |
| 3-1 카드 대조로 열기 | 같은 호출이다. 이 판에서 cells 로 열거나 바꾼 대상은 마감 레벨이 `C3` 다(`risk_get_coverage` 의 `close_level`). M2 앱이 cells 로 연 대상은 `C2` 로 남는다 |
| 4절 9명 고르기 | 입력 결손 영역(ECAD 의존 — 행의 `input_gaps` 에 `ecad_absent`)의 대표도 고를 수 있다 — `input_gap_m3` 거절이 없어졌다. 그 셀은 판정 대신 입력 결손 두 질문(지금 변경으로 말할 수 있는 영향 · ECAD 가 오면 확인할 것)으로 닫히고 보고서에 '입력 결손' 절이 선다. 범위 안의 `deferred` 좌석은 잡을 만들 때 저절로 풀린다 |
| (같은 자리) M2 설정 | 영역 1순위(`rank_in_domain` 1)를 고르면 M3 기본값으로도 M2 설정과 같다 — 1순위 셀은 거르지 않고 이중 판정을 묶음 전체로 한다(보정용). 1순위가 아닌 사람도 전량 이중 판정을 원하면 잡 전에 `HWAXRISK_REVIEW_DUAL=all`(2-5) |
| 5절 잡 시작 | 응답의 `calls_estimate` 가 `{low, expected, high, basis}` 이고 동의 문턱(1,500)은 `expected` 와 견준다. `undeferred` 가 풀린 보류 좌석 수다. 거절 표에서 `input_gap_m3` 줄이 빠진다 |
| 6-1 진행판 | `review.job.phase` 가 먼저 `live`(근거 꾸러미 실호출)일 수 있다. `review.filter`(승인 전이면 `approved: false` · `filtered` 0) · `review.noinput` · `review.dispositions` · `review.job.progress.reopened_extra` 가 는다 |
| 6-2 보류 표 | `consent_extra` · `max_calls` 와 기다림 `health_unknown` · `draining` 이 는다(5-5) |
| 6-3 재기동 | 같다. update-all 의 비우기(1-4)가 지나가도 차감 없이 이어 돈다 |
| 8절 4 품질 수치 | 품질 기준판이 `rq-2` 다 — 거름 · 입력 결손 줄과 보정 뒤집힘이 는다 |
| 8절 5 사용자 판정 | 같다. 보고서가 M3 판(`expert-report-2`)이라 걸린 줄에 메커니즘, 입력 결손 절, 엔진이 알린 다툼 표지가 는다 |

### 4-2. 끝난 뒤 — M2 에 없던 것

- **실패 셀 처분.** 잡이 끝났는데 `review.job.error` 가 '범위 안 셀 N개가 실패로 끝났다(…) — 사람이 처분한다(…)' 면 Claude 에서 `risk_job_action(job_id='…', action='retry_failed')`(다시 — 까닭을 고친 뒤, 호출 추정이 동의 문턱을 넘으면 `consent_required` 로 돌아온다) 또는 `risk_job_action(job_id='…', action='skip_failed', reason='<4~300자>')`(넘김)이다. 길잡이의 `next` 에도 두 걸음이 있다. 사용자에게 확인한 뒤 부른다.
- **보고서 판.** 잡이 끝나면 사슬이 등록부 병합과 코드 조립 판(`reviews_partial`)을 세운다. 9명이라 마감 범위가 닫히지 않으므로 쟁점 패널과 영역 요약은 돌지 않는다. `risk_get_report(target_key='diff:…', part='summary')` 의 머리에 '마감 범위 미완 — 열린 셀 N' 이 선다.
- **완결 표기.** `risk_get_coverage` 의 `level_label` 이 `C0(…)` 이나 `C1(…)` 이고 괄호에 '열린 셀 N' 과 잔여가 붙는다 — 파일럿에서는 그것이 정상이다.

### 4-3. 파일럿이 이미 M2 앱으로 돌았다면

- 그 잡은 M2 코드가 세운 것이라 사슬이 서지 않는다(보고서 판도 없다). 그 대상에서 이어 돌리려면 5절처럼 검토 잡을 세운다 — 그 잡이 끝날 때 사슬이 선다. 다만 M2 앱이 cells 로 연 대상은 마감 레벨이 `C2` 라 전원을 돌려도 C2 마감이다(5-1 의 대상 고르기).
- 파일럿 셀이 1절 반영 **전**의 엔진으로 끝났으면 걸린 줄에 메커니즘(`mech`)이 없다 — 그 finding 은 `unclassified~` 로 갈려 남는다(받아들인다 — m3-synthesis 3.3). 어느 판으로 돌았는지 잰다(원장을 읽기 전용으로 연다).

```bash
python3 - "$D/risk_review.db" 'diff:<diff id>' <<'PY'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True, timeout=5)
for row in c.execute("SELECT state, prompt_rev, COUNT(*) FROM rr_review_cells WHERE target_key = ? AND prompt_rev IS NOT NULL"
                     " GROUP BY 1, 2 ORDER BY 1, 2", (sys.argv[2],)):
    print(*row)
PY
```

`verdict=cr-verdict-1` 이 든 줄이 옛 판으로 돈 셀이다. 새 판으로 다시 보려면 그 셀을 `force` 로 다시 연다(REST `POST /api/targets/{key}/cells/retry {filter: {agent_key: '…'}, force: true, reason: '…'}` — 판정 행을 지우고 다시 돈다). force 다시는 웹 · REST 만이고 Claude 의 `retry_failed` 에는 없다 — 웹 화면(`m3-frontend-request.md` 3-3)이 생기기 전에는 dev 에 부탁한다.

- 그 대상이 패널을 돌린 뒤 cells 로 바꾼 것이면 M3 의 첫 병합에서 등록부가 카드 대조 finding 까지 넣어 다시 선다. 바꾸기 전 모양은 이행 사본(`pre-migrate-v4-*`)과 비교 보기(`registry?source=panels`)에 있다.

## 5. M3 전원 실주행

실제 대상 1건에 로스터 전원(359명)이 카드 대조를 끝내고, 쟁점 패널과 영역 요약 · 종합 보고서가 이어 돈다. 나갈 기준은 M3.md 1절 · 6절이다.

### 5-1. 전제 — 재는 것

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | 2절이 들어와 있다 | 2-3 · 2-4 | 스키마 5 · 도구 31 · 새 인자 |
| 2 | K · 출력 상한을 적었다(M0-b 뒤 dev 가 정한 값) | `grep -n -e '^CARD_REVIEW_K=' -e '^CARD_REVIEW_MAX_TOKENS=' ../HWAXAgentServer/.env` | dev 가 알린 값. 없으면 엔진 기본(K 8)으로 돈다 — 막히지는 않는다. 실주행 중에는 바꾸지 않는다(판이 올라 도는 셀이 처음부터 돈다) |
| 3 | 배정표 상태를 안다 | 2-6 의 명령 | `approved` 면 거르며 돌고, `draft` 면 거르기 없이 돈다(시간 어림이 다르다 — 5-7) |
| 4 | 챗 지연 기준선이 돈다 | `pgrep -af llm_ttft_probe` | 1-5 의 탐침이 떠 있다(실주행 한 시간 전부터 끝까지) |
| 5 | 대상 | 아래 | 마감 레벨 `C3` 인 cells 대상 |
| 6 | 그 대상에 살아 있는 잡이 없다 | `risk_get_coverage(target_key='diff:…', with_seats=false)` | `review.job` 이 없거나 끝났고, `stage` 가 없거나 끝났다 |
| 7 | 원장 크기(시작 전) | `ls -l "$D"/risk_review.db*` | 적어 둔다(5-9) |

대상 — 전원 실주행은 마감 레벨 `C3` 인 cells 대상에서 돈다(M3 에는 단위 재빌드 `force` 나 셀 비우기가 없다 — m3-cells a-14). 4절 파일럿 대상이 이 판에서 cells 로 열린 것(`close_level` `C3`)이면 그 대상을 이어 써도 된다 — 파일럿이 본 셀은 다시 돌지 않는다. M2 앱이 cells 로 연 대상(`C2`)이면 M0-d 의 다른 실제 변경 비교로 새 대상을 연다.

```text
risk_open_target(kind='diff', ref_id='<diff id>', consent=true, flow='cells', reason='M3 전원 실주행')
```

### 5-2. 잡 시작 — 동의 한 번

Claude 에서 길잡이부터 본다 — `risk_next_step(project_id='<과제 id>')` 의 `where` 가 `review` 이고 `next` 에 `risk_start_job(mode='reviews')` 걸음이 있다. 먼저 동의 없이 불러 추정을 받는다(동의 문턱을 넘으면 아무것도 만들지 않고 `consent_required` 로 돌아온다).

```text
risk_start_job(target_key='diff:<diff id>', mode='reviews')
```

`consent_required` 에 실린 `calls_estimate{low, expected, high, basis}` 를 사용자에게 보인다. `expected` 는 거르기 없음 가정이라 실제보다 크다(359명 × 단위 20 이면 약 2만 — M3.md #33). 동의를 받으면 `consent=true` 로 다시 부른다(`scope` 를 빼면 로스터 전원이다).

```text
risk_start_job(target_key='diff:<diff id>', mode='reviews', consent=true)
```

- 응답 — `job_id` · `cells_total`(로스터 × 검토 대상 단위) · `cells_in_scope` · `experts_in_scope` · `units` · `calls_estimate` · `credential{kind, email, exp}` · `undeferred`(풀린 보류 좌석), 있으면 `credential_note`(검토자 PAT 의 남은 수명이 추정 소요보다 짧다 — 다시 등록하고 시작하거나, 도중에 `credential` 로 멈추면 등록 뒤 재개한다).
- 거절 — `review_too_large`(추정이 30,000 을 넘는다 — `scope.tiers` 나 `scope.domains` 로 나눠 차례로 돈다) · `pat_unavailable`(웹 설정에서 PAT 를 등록하거나 Claude 에서 hwax_risk 도구를 한 번 불러 자동 등록) · 그 밖은 `server-setup-m2.md` 5절의 표 그대로다(`input_gap_m3` 는 없어졌다).

### 5-3. 사슬 — 사람 손 없이 이어 도는 것

```text
검토 잡 ──끝(completed)──▶ 등록부 병합 → 보고서 판(reviews_closed) → 쟁점 선정 → 쟁점 잡(고른 것이 없으면 종합 잡)
쟁점 잡 ──끝(completed · failed)──▶ 병합 → 보고서 판(issues_closed) → 종합 잡
종합 잡 ──끝──▶ 영역 요약 → 과제 종합 → 보고서 판(synth_done) · 완결 갱신
```

- **검토 잡의 끝.** 범위 안 셀이 전부 닫히면(`reviewed` · 거름 · 입력 결손 · `failed` · 넘김 — `failed` 도 닫힌 것이다) 끝난다. 거르기가 켜졌으면 끝나기 전에 보충 표본을 채우느라 셀을 몇 개 다시 연다. 실패 셀이 남아도 잡은 `completed` 이고 `error` 가 '범위 안 셀 N개가 실패로 끝났다(…) — 사람이 처분한다' 이며, 실패는 막음 잔여 '실패 N셀' 로 남는다. 처분하면(다시) 그 셀의 검토 잡이 돌고, 끝나면 사슬이 다음 회차로 다시 고른다.
- **쟁점 잡.** 쟁점 패널(3라운드 심의 — 좌석은 제기 둘과 반대 또는 인접 영역 둘)을 한 대상 안에서 한 줄로 돈다. 패널 하나가 LLM 을 31~87번 부르고(실측 전 어림) 포털 대화를 하나 만든다 — 카드 대조와 요약은 대화를 만들지 않는다. 쟁점 패널은 하루 패널 상한에 세지 않고 카드 대조 관문을 절반으로 줄이지도 않는다(관문을 줄이는 것은 사람이 띄운 심의뿐이다). 그래도 도는 심의로 세므로 그동안 update-all 은 재기동을 미룬다(1-4 의 '미룬 재기동').
- **종합 잡.** 로스터 영역마다 요약 하나(제기한 클러스터가 없는 영역은 LLM 없이 '서술 없음')와 과제 종합 하나를 차례로 부르고 판을 세운다.
- 마감 범위에 열린 셀을 남긴 채 끝난 검토 잡(좁은 범위)은 판(`reviews_partial`)만 세운다. 사람이 취소한 잡 뒤에는 잇지 않는다. 재기동으로 다음 잡을 못 세운 사슬은 앱이 30초마다 메운다.

### 5-4. 길잡이가 보이는 것 — `risk_next_step`

| `where` | 뜻 | `next` 의 첫 걸음 |
|---|---|---|
| `review` | 검토 잡 전, 또는 범위 밖 셀이 남았다 | `risk_start_job(mode='reviews')` |
| `running` | 검토 잡이 돈다 | 지켜볼 도구 — `risk_get_coverage` · `risk_get_cells`(그 잡 범위 · 실패 셀) · `risk_get_expert_report` |
| `paused` | 검토 잡이 보류로 멈췄다 | `blocked` 의 `fix` 를 고친 뒤 `risk_job_action(action='resume')`. 자동 재개 보류면 걸음 없이 기다린다 |
| `issues` | 쟁점 잡이 살아 있다 | `risk_get_issues` 로 지켜본다. 멈췄으면 `blocked` 의 `chain_paused` 와 재개가 맨 앞이다 |
| `synth` | 종합 잡이 살아 있다 | `risk_get_coverage`(`stage` · `report`) |
| `done` | 검토 잡과 사슬이 끝났다 | `risk_get_report(part='summary')`. 막음 잔여가 남았으면 `blocked` 의 `residual_unacked` |

- `facts` — `level_label` · `stage` · `report` · `filter{mode, approved, would_filter, filtered, audited, widened, off, audit{risk_miss, upper95, floor_met}}` · `failed_cells{n, by_code}` · `no_input` · `review_job`(범위 · 워커는 수와 앞 몇) · `review_order`(영역마다 순위 1~3).
- `notes` 에 붙는 줄 — '검토 잡이 기다린다 — health_unknown: …' 같은 기다림, 단계 `live` 의 뜻, '최근 쟁점 패널 다섯이 전부 기각·불명이다(issue_yield_low)', 다시 토의가 필요한 쟁점('패널 판정 — 근거 바뀜, 다시 토의 필요')과 올리는 길, 서술 없이 표만 선 요약의 까닭.
- `next` 의 쓰기 걸음은 동의 칸(`consent`)을 채우지 않는다 — 사용자에게 보이고 확인받은 뒤 부른다.

### 5-5. 멈춤과 기다림 — 할 일

M2 의 보류(user · credential · ctx_too_small · contract · llm_misconfigured · content_fail_rate · llm_outage · aidh_unreachable · agent_outdated · ctx_unknown)는 `server-setup-m2.md` 6-2 그대로다. M3 에서 더한 것이다.

| 무엇 | 어디서 보이나 | 뜻 | 할 일 |
|---|---|---|---|
| 보류 `consent_extra` | `review.job.hold_code` · 길잡이 `blocked` | 다시 연 셀(넓힘 · 늦은 넘김 · 보충 표본 · 사람의 다시)의 추정 호출이 동의받은 몫의 여유(20% · 최소 30회)를 넘었다. 아무것도 차감하지 않았고 그 셀은 잡에 묶인 채 기다린다 | `review.job.progress.reopened_extra.unconsented{cells, calls_est}` 를 사용자에게 보이고, 동의하면 `risk_job_action(job_id='…', action='resume', consent=true)`. 동의하지 않으면 `risk_job_action(job_id='…', action='skip_failed', filter={'state': 'pending'}, reason='…')` — 기다리는 셀만 넘기고 여유 안으로 돌아오면 잡이 이어 돈다 |
| 보류 `max_calls` | 같다 | 잡의 추정 합이 `HWAXRISK_REVIEW_MAX_CALLS`(30,000)를 넘는다 — 동의로 풀리지 않는다(재개는 409 `max_calls`) | 기다리는 셀을 위처럼 넘기거나, 상한을 올리고(2-5 — 앱을 다시 띄운다) 재개한다 |
| 보류 `credential` · 사슬 잡의 `pat_unavailable` | `hold_code` · `stage.error` | 검토자 PAT 가 만료 · 폐기 · 거절됐다(서비스 계정으로 내려가지 않는다) | PAT 를 다시 등록한다(웹 설정, 또는 Claude 에서 hwax_risk 도구를 한 번 불러 자동 등록). 검토 잡은 등록 뒤 `resume`, `pat_unavailable` 로 줄에 선 사슬 잡은 등록하면 저절로 집힌다 |
| 기다림 `health_unknown` | `review.job.waiting.reason` · 길잡이 `notes` | 앱이 에이전트 서버 `/health` 에서 카드 대조 관문을 읽지 못한다 — 새 카드 대조 호출을 내지 않는다(마감 · 근거 꾸러미는 돈다) | 1-3 의 `curl … /health` 가 답하는지 본다. 읽히면 저절로 이어 돈다 |
| 기다림 `draining` | 같다 · 쟁점 · 종합 잡의 `stage.error` 가 `draining: …` | update-all 의 비우기(1-4)이거나 엔진의 비우기 거절이다 — 비우기가 끝나면(거절이면 그 뒤 60초) 저절로 이어 돈다 | 오래 가면 `./infra/scripts/review-drain.sh status`. 사람의 고정(`hold`)이면 `off --force` 로 푼다 |
| 쟁점 잡 멈춤(재기동) | `stage.state` 가 `paused` · `stage.error` 가 `restart: 앱이 재기동해 도는 패널을 닫았다 — …` · 길잡이 `chain_paused` | 리스크 앱이 다시 뜨며 도는 쟁점 패널을 닫았다. 그 쟁점은 차감 없이 대기로 돌아왔고, M4 전에는 저절로 재개하지 않는다 | 길잡이에 `repersist_pending` 이 있으면 `risk_repersist_panel(panel_id='…')` 이 먼저다. 그 뒤 `risk_job_action(job_id='<stage.job_id>', action='resume')` |
| 쟁점 잡 실패 | `stage.state` 가 `failed` | 쟁점 패널이 잇달아 셋 실패했다 | 남은 대기 쟁점은 '미토의'(`untried_cap`)가 되고 사슬은 종합으로 넘어간다. 에이전트 서버 로그를 dev 에 보낸다 |
| 알림 `issue_yield_low` | `stage.advice` · 길잡이 `notes` | 최근 쟁점 패널 다섯이 전부 기각 · 판정 못 함이다(잡은 돈다) | 계속할지 사용자가 정한다. 멈추려면 `risk_job_action(action='pause')` |
| `external_worker` | — | 이 판에 없다(순수 Claude 길은 M3 뒤 — 포털 D-48) | — |

검토 잡과 종합 잡은 앱 · 에이전트 서버가 다시 떠도 차감 없이 저절로 이어 돈다(끊긴 호출 · 요약은 다시 낸다). 사람이 이어야 하는 것은 쟁점 잡뿐이다.

### 5-6. 진행 읽기

```text
risk_get_coverage(target_key='diff:<diff id>', with_seats=false)
```

| 칸 | 읽는 법 |
|---|---|
| `review.job.phase` | `live`(근거 꾸러미 실호출) → `pack` → `review` — 전문가마다 따로 간다 |
| `review.job.progress.cells` · `.in_scope.by_state` | 범위 안 셀 상태. `pending + running` 이 0 에 가까워지면 끝이 가깝다 |
| `review.job.progress.calls.ok` · `.avg_ok_s` | 끝난 호출 수와 호출 하나의 평균 초. 남은 어림 ≈ (`review.job.progress.reopened_extra.expected` − `ok`) × `avg_ok_s` ÷ 8 — `expected` 는 잡을 만들 때의 추정(거르기 없음 가정)이라 거르기가 켜졌으면 실제는 이보다 짧다 |
| `review.filter` | `approved` · `filtered`(거른 셀) · `audited`(표본) · `audit.risk_miss`(놓친 걸림) · `audit.upper95` · `widened` · `off` |
| `review.noinput` | 입력 결손 전문가 · 셀과 결과별 수 |
| `review.job.progress.reopened_extra` · `review.job.waiting` | 다시 연 셀 몫 · 기다림(5-5) |
| `level_label` · `qualifiers` · `stage` · `report` | 완결 표기 · 잔여(목록 칸은 앞 5개와 수) · 사슬 단계 · 마지막 보고서 판 |

- 실패 셀 — `risk_get_cells(target_key='diff:…', job_id='<검토 잡>', state='failed')` 의 `error_code`.
- 쟁점 단계 — `risk_get_issues(target_key='diff:…')` 의 `cap{base, hard, run}` 과 행의 `state` · `outcome`. 줄 선 것만 보려면 `state='queued,planned,running'`.
- 근거 꾸러미(B 층) — 단위마다 언 상태와 못 받은 호출을 원장에서 읽기 전용으로 센다(재질명은 찍지 않는다).

```bash
python3 - "$D/risk_review.db" 'diff:<diff id>' <<'PY'
import collections, json, sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True, timeout=5)
rows = c.execute("SELECT status, gaps_json FROM rr_unit_live WHERE target_key = ?", (sys.argv[2],)).fetchall()
print("상태:", dict(collections.Counter(r[0] or "아직" for r in rows)))
print("못 받은 호출:", dict(collections.Counter(f"{g.get('tool')} {g.get('code')}" for r in rows for g in json.loads(r[1] or "[]"))))
PY
```

상태는 `ok` · `partial`(못 받은 호출이 있다 — `live_denied` 는 그 계정의 시야에 도구가 없다, 2-4) · `none`(손잡이 0) · `skipped`(셀이 이미 돈 단위) · `아직` 이다.

- 박스 — `./infra/scripts/risk-review-inventory.sh` 의 `잡 상태별:`, 1-3 의 `/health`(`review_active` · `limit`), update-all §6 의 `리스크 검토` 줄.
- 웹 화면이 생기기 전에는 쟁점 올리기 · 건너뛰기, 잔여 확인, force 다시를 REST 로만 할 수 있다(`m3-frontend-request.md`). 그때까지 필요하면 dev 에 부탁한다.

### 5-7. 걸리는 시간 — 어림

| 단계 | 어림 | 근거 |
|---|---|---|
| 셀 일(검토 잡) — 배정표 승인 뒤(거르기) | 약 8,000~10,000 호출 · 동시 8 · 호출 5분이면 3~4일 | M3.md #33 · 7절 |
| 셀 일 — 승인 전(거르기 없음) | 약 15,000 호출 이상 · 약 7일 | 같다 |
| 쟁점 패널 | 24건이면 반나절~하루, P1 이 48건이면 하루~이틀(대상 안에서 한 줄) | M3.md 7절 |
| 영역 요약 · 종합 | 요약 열여섯 번(영역 15 + 종합 1)을 차례로 — 한 시간 남짓 | M3.md #51 |

호출 하나가 가정(5분)의 3배면 셀 일도 3배다. 실제 초는 5-6 의 `avg_ok_s` 로 다시 어림한다. 사람이 띄운 심의가 도는 동안은 관문이 4 로 줄어 그만큼 늦다.

### 5-8. 도는 중 update-all 한 번(나갈 기준 6)

셀 일이 도는 동안 update-all 을 한 번 돌린다. 1-4 의 `1h` 줄(세웠다 · 비었다 또는 '300초 안에 끝나지 않은 카드 대조 N건')과 끝의 '깃발을 내렸다', §6 의 `리스크 검토` 줄을 적는다. 그동안 `review.job.waiting.reason` 이 `draining` 이었다가 지워진 뒤 이어 돈다. 전후의 `review.job.progress.calls`(특히 `content_fail`)와 `review.cells.by_state.failed` 가 비우기 때문에 늘지 않는지 본다. 1-5 의 탐침이 그동안의 챗 첫 조각 지연을 남긴다.

### 5-9. 끝 — 나갈 기준 대조와 보내기

| 나갈 기준(M3.md 1절) | 보는 곳 | 기대 |
|---|---|---|
| 1 모든 셀이 종결이거나 사유 있는 실패 | `risk_get_coverage` 의 `review.cells.by_state` · `risk_get_report(part='summary')` 머리의 '수:' 줄 | `pending` · `running` 0, 실패가 있으면 그 수와 코드가 머리에 있다 |
| 2 전문가 보고서가 로스터 수만큼 | 보고서 머리의 '전문가 보고서: 기대 N · ready … · partial … · blocked … · 누락 …' | `blocked` 0 · 누락 0 |
| 3 쟁점 패널이 상한 안에서 끝 | `risk_get_issues(target_key='diff:…', state='queued,planned,running')` | `total` 0, 상한 밖은 보고서 '미토의 쟁점' 행 |
| 4 영역 요약 · 종합 · 수 = 완결 판정 | `risk_get_report(part='domains')` · 머리의 `trigger` · `narrative_state` | 영역마다 한 쪽, `synth_done` 판 |
| 5 잔여를 달고 나옴 | `level_label` | 괄호에 잔여 — 맨 `C3` 는 나오지 않는다(6-2) |
| 6 update-all 비우기 · 챗 지연 | 5-8 · 1-5 | 비우기로 지나가고, 지연이 평소의 2배 안 |

dev 에 보낸다(토큰 · 사내 주소는 빼고) — 진행판 `review` 칸의 끝 모양, `risk_get_issues` 전부, 보고서 `part='summary'`, 시작 전 · 끝난 뒤의 `ls -l "$D"/risk_review.db*`, 1-5 의 `ttft-<날짜>.jsonl`, 5-5 의 멈춤 기록(시각 · 코드), 5-8 의 update-all 줄. dev 가 실측표(PLAN 6절 — 호출 초 · 셀당 호출 수 · 거르는 비율 · 표본 놓침 · 보정 뒤집힘 · 쟁점 수와 결과 · 요약 초 · DB 증가분 · 챗 첫 조각 지연)를 고친다.

## 6. 종합 보고서 읽기 — 사용자

웹 화면(`m3-frontend-request.md` 5 · 6절)이 생기기 전에는 Claude 에서 읽는다.

```text
risk_get_report(target_key='diff:<diff id>', part='summary')            # next_page 가 있으면 page 로 주어 이어 받는다
risk_get_report(target_key='diff:<diff id>', part='domains', page=1)    # 영역마다 한 쪽 · mechanisms · appendix · full 도 있다
```

### 6-1. 판

- 사슬의 단계마다 판이 선다 — `reviews_closed`(검토 끝 · 코드 조립) → `issues_closed`(쟁점 끝) → `synth_done`(영역 요약 · 종합 서술까지). 좁은 범위 검토 뒤에는 `reviews_partial`, 잔여 확인 · 확인 취소 뒤에는 `ack`, 사람이 다시 내면 `manual` 판이다. 내용이 직전 판과 같으면 새 판을 만들지 않는다.
- 읽히는 것은 마지막 판뿐이다. 둘째 쪽부터 첫 쪽의 `version` 을 함께 주면(`risk_get_report(…, version=<n>, page=2)`) 그사이 새 판이 섰을 때 `report_version_moved` 로 알려 준다 — 그러면 1쪽부터 다시 읽는다.
- 제목은 `리스크 심사 보고서 v{n} [{완결 표기}] — {대상}` 이고, 근거 등급이 전부 경험칙이면 앞에 `[가설 단계]` 가 붙는다.
- 표와 수는 전부 코드가 원장에서 센 것이고, 서술(머리 · 걸림 · 갈림 · 개선 · 지켜볼 것 · 정보 요청 · 이야기)만 LLM 이 쓴 것이다. 서술 앞에 '서술은 LLM(요약 서기), 근거는 아래 표다' 가 붙고, 서술이 없으면 굵게 '서술 없음 — 까닭' 이 선다(까닭 — 이 영역이 제기에 참여한 클러스터가 없다 · 엔진이 내용 탓으로 거듭 실패했다 · 엔진·포털이 거듭 응답하지 않았다 · 이 박스의 창이 요약 입력을 담지 못한다 · 서술이 꼭 다룰 행을 빠뜨렸거나 출처 없는 수를 냈다).
- 쪽 — 본문(완결 · 잔여 · 수 · 종합 서술 · 주의 A 전부 · B 상위 30 · 개선 · 넘김 · 쟁점 결과 / 판정 후보 · 미토의 쟁점 · 카드 FAIL 수 · 정보 요청 / 쟁점 패널 · 영역 × 셀 상태 · 거름 표본 · 품질 · 사람 확인), 영역마다 한 쪽, 메커니즘, 부록(전문가 색인).

### 6-2. 레벨 C1 · C2 · C3

| 레벨 | 조건(앞 레벨에 더해) |
|---|---|
| C1 대표 완료 | 검토 대상 단위 ≥ 1 · 미배정 0 · 격자(로스터 × 단위) 완전 · 영역마다 1순위 대표의 셀이 다 닫힘 · 보고서 누락 0 · 판정 누락 0 · 불변식 위반 0 |
| C2 심층 완료 | Tier A · B 셀이 다 닫힘 · 영역마다 깊이(카드로 본 전문가가 3명 미만이면 전원, 아니면 max(3, 30%)) · 쟁점 단계가 지금 셀로 돌았고 P1 쟁점이 열려 있지 않다 |
| C3 전원 완료 | 격자 전부 닫힘 · 넘긴 셀이 (거르지 않고 입력 결손도 아닌 셀의) 5% 이하 · 쟁점 열림 0 · 마지막 종합 판이 지금 셀 · 등록부로 돌았다 · 막음 잔여가 0 이거나 전부 확인됐다 |

- 저장 레벨은 내려가지 않는다. 지금 계산이 낮으면 표기에 '재개방 N셀' 같은 표지가 붙는다.
- 완결 표기는 `"<레벨>(<막힌 까닭 · 잔여>)"` 이다. 예 — `C2 · C3 대기(입력 결손 110명·250셀(mem·pcb) · 미토의 쟁점 7건(주장 FAIL 7) · 2차 영향 미실행(넘김 0건 표만) · 결손 사냥 미실행)`. 머리 `C2 · C3 대기` 는 C3 조건이 다 됐고 막음 잔여 확인만 남았다는 뜻이다(마감 레벨이 C2 인 대상은 `C2 · 마감 대기`).
- M3 의 cells 대상에는 '2차 영향 미실행' · '결손 사냥 미실행' 이 늘 붙어 **맨 `C3` 는 나오지 않는다**. 최선은 `C3(2차 영향 미실행(넘김 N건 표만) · 결손 사냥 미실행)` 이다(그 둘은 M4 가 돌린다).
- 괄호 앞쪽의 '열린 셀 N' · '쟁점 진행 N건' · '깊이 미달 …' · '후속 낡음(…)' 은 일이 덜 끝났다는 표지라 확인으로 넘길 수 없다.

### 6-3. 잔여와 확인

| 잔여 | 막음 | 읽는 법 |
|---|---|---|
| 입력 결손 N명·N셀(영역) | 막음 | ECAD 가 없어 판정 대신 두 질문으로 닫힌 셀이다. 보고서 '입력이 오면 확인할 것' 을 본다 |
| 실패 N셀 | 막음 | 처분(다시 · 넘김)하거나 까닭과 함께 확인한다 |
| 사람 넘김 N셀 | 막음 | 넘긴 셀이 이미 받은 걸림은 '넘긴 셀 — 일부만 판정' 으로 남아 있다 |
| 미토의 쟁점 N건(주장 FAIL k) | 막음 | 상한 밖 · 판정 못 함 · 건너뛴 쟁점이다. '전문가 N명이 FAIL 로 봤으나 미토의' 줄을 본다 |
| 패널 판정 — 근거 바뀜, 다시 토의 필요 N건 | 막음 | 6-4 |
| 거름 N셀(표본 · 놓친 걸림 · 95% 상한) | 표본이 바닥(59건 · 영역마다 1건)을 못 채웠거나, 상한이 5% 를 넘거나, 대상 거르기가 꺼졌으면 막음 | 놓친 걸림 0 · 상한 5% 아래면 표기다 |
| 부분 캡처 — 제외 N건 | 막음 | 캡처가 일부만 읽혀 뺀 단위다 |
| 검토 품질 기준 밖 N항 | 막음 | 보고서 '검토 품질' 블록을 본다 |
| 보류 n/m(%) | 20% 를 넘으면 막음 | 적용 판정 가운데 '모름' · '판정 못 함' 이다 |
| 카드 0장 N명 · 카드 없는 영역 — 역할 판단만 | 표기 | 카드 없이 역할로 답한 사람 · 영역이다 |
| 2차 영향 미실행 · 결손 사냥 미실행 | 표기 | M3 에서 늘 있다 |

- 막음 잔여는 과제 소유자나 관리자가 **웹에서** 한 종류씩 사유(300자 안)와 함께 확인한다. Claude 에는 확인 도구가 없다. 확인하면 레벨이 다시 셈해지고 보고서 판(`ack`)이 선다.
- 확인한 뒤 그 잔여의 집합이 바뀌면(실패가 하나 늘었다 따위) 그 확인은 낡아 다시 받아야 한다. 확인 취소는 이력을 지우지 않는다.
- 웹 화면이 생기기 전에는 dev 에 부탁한다(REST `POST /api/targets/{key}/closure/acks/{item}` — `m3-frontend-request.md` 6절).

### 6-4. 쟁점과 다시 토의 표시

- 쟁점 결과 줄은 원래 분포와 패널 결과를 한 줄에 싣는다 — `reg:<클러스터> · 제기 12명(judgement=FAIL 9 · judgement=WARNING 3) · 반대 2명 → 쟁점 패널 하향 severity=중대 · judgement=WARNING`. 결과 낱말은 유지 · 하향 · 상향 · 기각 · 판정 못 함이다. 패널 결론이 등록부 행을 덮고, 덮기 전 값은 등록부 행에 남는다(사용자 결정 D-34).
- **'패널 판정 — 근거 바뀜, 다시 토의 필요'** — 패널이 판정한 뒤 그 쟁점의 근거(제기자 · 반대자 · 주장값)가 바뀌었다는 표시다. 바뀐 사람이 '(제기 + … · 반대 − …)' 로 붙는다. 상한에 자리가 있으면 새 근거로 다시 줄을 서고(' · 새 패널 대기'), 새 패널이 정할 때까지 옛 판정이 보인다. 새 패널이 결정을 못 내면 '(새 패널 결정 못 함)' 이 붙고 옛 판정이 남는다. 상한에 자리가 없어 다시 돌지 못한 것은 잔여 '다시 토의 필요' 로 막는다 — 웹에서 그 쟁점을 올리거나(사람의 결정은 상한 밖이어도 된다, 사유 필수) 잔여를 확인해 넘긴다.
- '미토의 쟁점' 은 상한 밖(과제당 24건 — P1 은 48건까지 먼저) · 판정 못 함 · 건너뛴 쟁점이다. 웹에서 올리면(사유 필수) 쟁점 잡이 그것을 돈다.

### 6-5. 함께 볼 것

- 본문의 '카드 대조가 FAIL 로 본 판정 n건 · 그 가운데 severity=치명 k건(등록부에는 hold 로 주의)' — 등록부가 hold 로 묶은 FAIL 의 원래 수다.
- 본문 끝의 '거름 N셀 · 표본 S · 놓친 걸림 M' — 거른 셀 가운데 끝까지 본 표본과 그 표본에서 나온 걸림이다. 놓친 걸림이 나온 영역은 넓혀 다시 봤다.
- 쪽의 '서술은 주의 A 상위 N건 — 나머지 M건은 표에만 있다' — 서술이 다 다루지 못한 A 행은 표에 있다.
- 부록 — 전문가 한 사람씩 검토 · 거름 · 입력 결손 · 실패 · 넘김 셀 수와 판정 수 · 걸림 · 카드 밖 · 인용 통과 · 보고서 상태다. 한 사람의 보고서는 `risk_get_expert_report(target_key='diff:…', agent_key='…', part='summary')` 로 읽는다.

## 7. 손잡이 (전부 선택 — 안 적으면 기본값)

| 어디 | 이름 | 기본 | 뜻 |
|---|---|---|---|
| 에이전트 서버 `.env` | `CARD_REVIEW_CONCURRENCY` | 8 | 카드 대조 동시 호출 |
| 에이전트 서버 `.env` | `CARD_REVIEW_CONCURRENCY_WITH_DELIB` | 위의 절반 | 사람이 띄운 심의가 돌 때(위보다 크면 위로 묶는다) |
| 에이전트 서버 `.env` | `CARD_REVIEW_MAX_TOKENS` | 0 | 카드 대조만의 출력 상한(0 = `DELIB_MAX_TOKENS`). 바꾸면 카드 대조 판이 오른다 — 도는 검토 잡이 없을 때 |
| update-all 을 띄우는 셸 | `HWAX_DRAIN_TTL_S` | 1800 | 깃발 수명(초) — § 머리마다 다시 늘린다. 21600 에서 자른다 |
| update-all 을 띄우는 셸 | `HWAX_DRAIN_WAIT_S` | 300 | 도는 카드 대조를 기다리는 한도(0 = 기다리지 않는다) |
| update-all 을 띄우는 셸 | `HWAX_DRAIN_GRACE_S` · `HWAX_DRAIN_MAX_S` | 1800 · 46800 | 재기동을 미룬 실행의 끝 — 심의가 끝난 뒤 새 패널을 멈춰 두는 창 · 그 깃발의 최대 수명 |

`AGENT_RESTART_FORCE=1` 이면 update-all 은 도는 카드 대조를 기다리지 않는다(심의 보호를 건너뛰는 것과 같은 손잡이).

리스크 앱의 손잡이(`$D/knobs.env` — 워커 수 · 거르기 · 이중 판정 · 근거 꾸러미 실호출 · 동의 문턱과 상한 · 쟁점 상한 · 요약 한도)는 2-5 의 표다. 고친 뒤에는 쟁점 패널이 돌지 않을 때 앱만 다시 띄운다.
