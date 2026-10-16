# LLM 풀 용량 측정 — cae00 절차

> 왜 — LP-D7 이 카드 대조 동시 수 세 손잡이(`CARD_REVIEW_CONCURRENCY` · `HWAXRISK_REVIEW_CONCURRENCY` · `CARD_REVIEW_MAX_STREAMS`)를 사람이 정하게 했는데 정할 데이터가 없었다. 이 측정이 그 데이터다(개선 제안 3 — `docs/improvement-1015/PLAN.md` 2절). 설계와 까닭은 `context-notes.md` LP-D16.
> 명령은 포털 리포 루트(cae00 은 `~/Projects/HWAXPortal`)에서 돈다. 서버 주소·키는 `infra/.env` 에만 적는다 — 이 문서와 추적 파일에는 적지 않는다.

## 0. 한눈에

| | |
|---|---|
| 무엇을 재나 | 실제 카드 대조 호출의 길이 분포대로 만든 합성 요청을 동시 수 단계마다 보낸다(기본 1 · 2 · 4 · 8 · 12 · 16 · 24). 변형 셋 — `direct`(서버 하나 직결) · `router-slack2`(측정용 라우터 경유, 붙임 문턱 기본 2) · `router-slack0`(붙임 끔) |
| 무엇이 나오나 | 단계마다 TTFT p50·p95 · 토큰 사이 지연(ITL) · 출력 토큰/초 · 요청/초 표, 세 손잡이 권장값, 붙임 문턱 비교, 서버 하나로 줄어드는 날의 값 |
| 얼마나 | 보통 30~60분(서버 속도에 달렸다 — 변형마다 요청 최대 212건). 상한은 단계 수 × 15분 × 변형 수(단계 하나는 `--max-seconds` 900초에서 끊는다) |
| 무엇을 차지하나 | GPU 다. `direct` 동안 서버 1 에 긴 요청이 최대 24개 동시에, 라우터 변형 동안 두 서버에 걸린다. 그동안 챗 첫 응답이 느려진다 |
| 건드리지 않는 것 | 운영 라우터(:9130) · `infra/.env` · LLM 주소 사본 · 서비스 재기동. 라우터 경로는 이 실행만의 측정용 라우터를 루프백 임시 포트에 띄워 잰다(자기 설정 파일만 읽는다 — 끝나면 내리고 지운다) |
| 키 | `infra/.env` 의 `LLM_API_KEY` 를 환경으로만 넘긴다. 어느 명령줄(argv)에도 싣지 않고 결과·로그에 남지 않는다(GuideLLM 보고서에는 `**********`) |

## 1. 언제 — 심의·카드 대조가 없을 때

측정 요청과 실제 호출이 GPU 를 나눠 쓰면 둘 다 흐려진다. 밤이나 주말처럼 아무도 심의·리스크 검토를 돌리지 않는 때를 고르고, 쓰는 사람들에게 미리 알린다.

```bash
curl -s --noproxy '*' http://127.0.0.1:9009/health \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("카드 대조", d.get("review_active"), "· 심의", d.get("delib_active"), "· 줄 선 심의", d.get("delib_queued"))'
```

셋 다 0 이어야 한다. 스크립트도 시작할 때 같은 것을 묻고 0 이 아니면 재지 않는다(rc 3 — 강행은 `--force`, 권하지 않는다). 리스크 앱 화면에서 돌거나 기다리는 검토 잡이 없는지도 본다 — 측정 도중 잡이 시작하면 그 변형은 흐려진다(스크립트가 변형마다 앞뒤로 에이전트 서버의 카드 대조 누계를 떠서 표에 `⚠ 흐려진 값` 으로 적는다).

## 2. 준비 — 이미지 둘

GuideLLM 이미지(`infra/apptainer/guidellm.sif`, 약 440MB)는 dev 가 굽고 Drive 로 나른다 — update-all(§2 deploy-all 의 images-from-drive)이 다른 이미지와 함께 받는다. 측정용 라우터는 운영 라우터와 같은 `portal.sif` 로 돈다.

```bash
ls -l infra/apptainer/guidellm.sif infra/apptainer/portal.sif
A="$(command -v apptainer || ls -d infra/apptainer/bin-*/usr/bin/apptainer | tail -1)"
"$A" exec infra/apptainer/guidellm.sif guidellm --version          # guidellm version: 0.8.0
```

`guidellm.sif` 가 없으면 `./infra/scripts/images-from-drive.sh` 로 받는다. Drive 에도 없으면 dev 에 굽기를 청한다(10절).

## 3. 길이 분포 — 본문 없이 수만

```bash
mkdir -p infra/.state/llm-capacity
python3 infra/scripts/llm-lengths.py --out infra/.state/llm-capacity/lengths-$(date -u +%Y%m%d).json
```

읽는 곳(전부 읽기만 — 원장은 SQLite `mode=ro`, 글 열은 SQL 안에서 수로 바꿔 꺼낸다).

| 출처 | 기본 자리 | 쓰임 |
|---|---|---|
| 카드 대조 호출 원장 `rr_review_calls` | `../HEAXHub/var/app_data/hwax_risk/risk_review.db` | **부하를 만든다** — 서버가 센 프롬프트·출력 토큰(보충 시도는 시도 수로 나눈다), 호출 종류별 |
| GLM 심의 잡 원장 | 에이전트 서버 `DELIB_JOB_DIR`(없으면 `artifacts` 의 실제 경로 옆 `delib-jobs`) | 참고 — 좌석 발언·의장 결정문 글자 수. 프롬프트 길이는 어디에도 남지 않는다 |
| 포털 심의 보관소 | `DELIB_ARCHIVE_ROOT`(없으면 `$HWAX_DATA_ROOT/delib-runs`) | 참고 — Claude 워크플로 산출이라 GLM 부하가 아니다 |

다른 자리면 `--risk-db` · `--delib-jobs` · `--delib-runs` 로 준다. 기대 출력 — `카드 대조 원장 … 호출 N줄 · 사용량 있는 줄 M`(M 이 0 이면 그 박스는 카드 대조를 돌린 적이 없어 부하를 만들 수 없다), 종류별 프롬프트·출력 토큰 p50·p95, '돌던 전문가 수'. 결과 파일은 수와 정해 둔 이름뿐이다(`backend/tests/test_llm_lengths.py` 가 원장의 글 열마다 표식을 심어 본다).

## 4. 계획 보기 — dry-run

```bash
L=infra/.state/llm-capacity/lengths-YYYYMMDD.json        # 3절의 파일
./infra/scripts/llm-capacity.sh --lengths "$L" --dry-run
```

서버 목록은 `infra/.env` 의 `LLM_UPSTREAMS` 다. 풀을 아직 켜지 않았으면 직접 준다 — `--upstreams http://<서버1>:<포트>/v1,http://<서버2>:<포트>/v1`(규칙은 `server-setup.md` 2절과 같다 · 운영 라우터 자신의 주소는 받지 않는다). 직결은 목록의 첫 서버다(`--direct` 로 바꾼다).

기대 출력.

```
── LLM 풀 용량 측정 계획
· 서버 2곳 — … · 직결 대상 …
· 변형 — direct router-slack2 router-slack0
· 키 — infra/.env 의 LLM_API_KEY 를 환경으로만 넘긴다
[capacity] 부하 — 카드 대조 all · 프롬프트 P(앞부분 Q × K종) · 출력 O 토큰 · 동시 [1, 2, 4, 8, 12, 16, 24] · 요청 [10, 10, 12, 24, 36, 48, 72]
· 요청 — 변형마다 최대 212건 × 변형 3 = 최대 636건 · 단계마다 최대 900초
✓ dry-run — 아무것도 부르지 않았다
```

`⚠ 앞부분이 2000 토큰보다 짧다` 가 나오면 붙임 문턱 변형끼리 차이가 나지 않는다(9절) — 그래도 동시 수 값은 잰다.

## 5. 재기

```bash
./infra/scripts/llm-capacity.sh --lengths "$L"            # (+ --upstreams … 가 필요하면 4절처럼)
```

변형마다 `── <변형>` 머리 뒤에 GuideLLM 의 진행과 표가 흐르고, 라우터 변형은 `· 측정용 라우터 :<임시 포트> — status=ok 올라옴 2/2 모델 같음=True` 를 먼저 찍는다. 끝에 결과 표와 권장(6절)이 나오고 결과 디렉터리를 알려 준다(기본 `infra/.state/llm-capacity/<UTC 시각>/` — gitignore 다).

| 결과 파일 | 무엇 |
|---|---|
| `summary.md` · `summary.json` | 표 · 변형마다 권장 C · 세 손잡이 권장 · 규칙 |
| `<변형>/benchmarks.json` · `guidellm.log` | GuideLLM 보고서(요청마다의 글은 남기지 않는다 — 수만) · 콘솔 출력 |
| `<변형>/scenario.json` | 보낸 부하(분포 · 앞부분 · 씨앗) — 키는 없다 |
| `<변형>/metrics-before/after.json` · `agent-before/after.json` | 서버 지표(도는 수 · 접두 캐시 누계) · 에이전트 서버의 일(흐려짐 판정) |
| `router-*/router.log` · `router-stats.json` | 측정용 라우터 로그 · 서버별 보낸 수와 붙음·넘침 |

멈추기 — Ctrl-C. 측정용 라우터를 내리고 키가 든 임시 설정 파일을 지운 뒤 끝난다(rc 130). 줄이고 싶으면 `--levels "1 4 8 16"` · `--paths router` · `--requests N`. 한 변형이 실패해도(서버가 안 올라옴 · GuideLLM 실패) 나머지를 재고 rc 1 로 끝난다.

## 6. 표 읽기

| 칸 | 뜻 |
|---|---|
| TTFT p50 · p95 (s) | 요청을 보내고 첫 토큰까지 — 기다림 + 미리 채우기(긴 프롬프트). 바쁘면 이것이 먼저 는다 |
| ITL p50 · p95 (ms) | 토큰 사이 지연 — 생성 속도. 한 배치에 요청이 많을수록 조금씩 는다 |
| 출력 tok/s | 전체 생성 처리량 |
| 요청/s | 끝난 호출 수/초 — 카드 대조 셀을 몇 개씩 해치우는가 |
| 완료 · 실패 · 미완료 | 각 단계의 앞 1/3(첫 물결)은 데우기로 빼고 센다. 미완료는 단계 상한(900초)에 걸려 끊긴 것 |
| 판정 | ✓ 받아들임 · ✗ 멈춘 단계와 까닭 · — 멈춘 뒤라 보지 않음 |

권장 규칙(그대로 `summary.md` 에 실린다) — 변형마다 동시 수가 낮은 단계부터 본다. ① 실패한 요청이 0 ② TTFT p95 가 한도(가장 낮은 단계의 TTFT p50 × 3 — `--ttft-ratio` · `--ttft-max-s` 로 바꾼다) 이하 ③ 요청/초가 앞 단계보다 5% 이상 는다(`--growth`). 처음 어긋나는 단계에서 멈추고, 마지막으로 받아들인 단계의 동시 수가 그 변형의 C 다. 세 손잡이는 라우터 변형 가운데 C 가 가장 큰 것(같으면 요청/초가 큰 것, 그래도 같으면 문턱 2)으로 — `CARD_REVIEW_CONCURRENCY = C` · `HWAXRISK_REVIEW_CONCURRENCY = C` · `CARD_REVIEW_MAX_STREAMS = C + ⌈C/2⌉`(기본 8·8·12 와 같은 비 — 중계는 관문보다 넉넉히). `direct` 의 C 는 서버 하나로 줄어드는 날의 값이다.

변형 줄의 덧말 —

- `이 변형 동안 접두 캐시 적중 x%` — 서버 지표 누계의 차(다른 호출이 섞이면 함께 센다). 붙임(slack 2)이 붙임 끔(0)보다 높으면 같은 전문가의 앞부분이 같은 서버의 캐시를 다시 쓰고 있다는 뜻이다.
- `라우터가 보낸 수 서버별 a·b · 붙음 s · 넘침 o` — 붙임이 한쪽으로 기울였는지. 넘침은 붙인 서버가 문턱보다 바빠 다른 서버로 간 수다.
- `⚠ 흐려진 값` — 그 변형 앞뒤로 카드 대조 누계가 늘었거나 심의가 돌았다. 조용할 때 그 변형만 다시 잰다(`--paths router --slack 2` 처럼).

붙임 문턱 — 붙인 서버가 가장 한가한 서버보다 이만큼 이상 바쁘면 떨어진다. **0 이 붙임 끔**(늘 가장 한가한 서버)이고 큰 값은 부하를 보지 않고 늘 붙는다(LP-D16). 기준 변형이 `router-slack0` 이면 권장에 `LLM_ROUTER_STICKY_SLACK=0` 이 함께 나온다 — `infra/.env` 에 그 한 줄을 적으면 운영 라우터가 다음 지표 주기(2초)에 다시 읽는다(재기동 없음).

## 7. 세 손잡이 적용

`server-setup.md` 5절 그대로 하되 16 · 16 · 24 자리에 6절의 권장값을 쓴다. **셋을 함께** 바꾼다(하나만 오르면 사슬이 어긋난다 — 워커가 관문보다 많으면 거절과 재시도, 중계가 관문보다 적으면 중계에서 기다린다). 도는 심의·검토 잡이 없을 때 그 절의 순서대로 다시 띄운다. 한쪽 서버를 정비하는 날에는 `direct` 의 값(없으면 8 · 8 · 12)으로 먼저 되돌린다.

적용한 뒤 카드 대조가 도는 동안 `curl -s --noproxy '*' http://127.0.0.1:9130/stats` 의 두 서버 `waiting` 이 0 근처면 그대로 둔다. 늘 0 보다 크면 셋을 한 단계 내린다(측정과 실제 부하가 다르다는 뜻이다 — 9절의 가정).

## 8. 결과 기록

아래 표에 한 줄 더한다 — 서버 주소는 적지 않는다(서버 1 · 2). `summary.md` 의 표는 주소가 없어 그대로 붙여도 된다. 결과 디렉터리는 cae00 에 남겨 둔다(gitignore).

| 날짜(KST) | 박스 | 서버 · 모델 | 길이 분포 | 기준 변형 | 권장 C(직결 C) | 적용 | 결과 디렉터리 |
|---|---|---|---|---|---|---|---|
| 2026-10-16 | dev — **스모크(파이프라인 확인, 용량 값 아님)** | 로컬 vLLM 1대 · qwen2.5-7b-dev | 합성 원장 40호출(짧은 프롬프트) · 단계 1·2 · 단계마다 3건 — 변형 셋 18건 · 48초 · rc 0 · 흐려짐 없음 · 접두 캐시 적중 직결 16% · 라우터 28%·28% | router-slack0(서버 하나라 문턱 차이는 잡음) | 2(2) — 단계 둘만 쟀다 | 적용 안 함 | 스크래치 |

## 9. 알아 둘 것 — 가정과 한계

- **합성 부하다.** 프롬프트는 영어 합성 글(GuideLLM faker)이고 길이는 GLM-5.2 토크나이저(이미지에 고정 리비전으로 구웠다)로 정확히 맞춘다. 실제 카드 대조의 한국어 글과 토큰 수는 같고 글자 수는 다르다. 서버가 센 토큰은 `benchmarks.json` 의 `prompt_token_count` 에 있다.
- **앞부분(공유) 몫은 가정이다.** 카드 대조 프롬프트는 [당신]→[카드]→[단위]→[지시] 차례라 같은 전문가·같은 묶음의 호출이 앞을 공유하는데, 원장에 그 몫이 따로 없다. 그래서 프롬프트 중앙값 × `--prefix-share`(기본 0.5)를 앞부분으로, 서로 다른 앞부분 수를 '돌던 전문가 수' 중앙값(없으면 4, `--prefix-count`)으로 둔다. 실제 몫은 운영 서버의 `vllm:prefix_cache_hits_total / vllm:prefix_cache_queries_total` 이 카드 대조 동안 얼마나 느는지로 가늠한다.
- **붙임 효과는 앞부분이 2,000 토큰쯤 넘어야 잰다.** 라우터의 붙임 열쇠는 메시지 앞 8,000자다(`LLM_ROUTER_PREFIX_CHARS`). 앞부분이 그보다 짧으면 요청마다 다른 글이 열쇠에 섞여 붙임 문턱 변형끼리 차이가 없다.
- **변형마다 씨앗이 다르다.** 같은 씨앗이면 다음 변형이 앞 변형의 프롬프트를 그대로 보내 접두 캐시에 거저 맞는다(dev 스모크 실측 18% → 96%). 같은 분포의 다른 글이다.
- **첫 물결은 빼고 잰다.** 단계마다 요청의 앞 1/3 을 데우기로 뺀다 — 카드 대조는 잡이 시작할 때만 한꺼번에 몰리고 그 뒤로는 끝나는 대로 하나씩 들어온다.
- **카드 대조만 잰다.** 챗·심의는 부하에 넣지 않는다(심의는 프롬프트 길이 기록이 없다). 관문이 사람이 띄운 심의 동안 절반으로 줄어드는(`CARD_REVIEW_CONCURRENCY_WITH_DELIB`) 몫이 심의 자리다.
- **Drive 비용.** `images-to-drive.sh` 가 올릴 때마다 약 440MB 가 더 간다(보관 3벌). cae00 은 영구 캐시라 바뀔 때만 받는다.

## 10. dev — 이미지 굽기

```bash
./infra/scripts/build-guidellm.sh          # → infra/apptainer/guidellm.sif (2분 남짓)
./infra/scripts/images-to-drive.sh         # portal.sif 들과 함께 Drive 로
```

판은 스크립트 머리의 상수가 정본이다 — GuideLLM 0.8.0 · torch 2.14.1+cpu · 기반 `python:3.12.14-slim-bookworm` · 나머지 의존성은 2026-10-01 이전에 올라온 판만(`pip --uploaded-prior-to` — 언제 다시 구워도 같은 묶음) · GLM-5.2 토크나이저 `zai-org/GLM-5.2@cf457fa7…`(sha256 대조). 이미지 안의 `/opt/hwax/guidellm-freeze.txt` 가 실제로 든 판 전부다. 판을 바꾸면 그 상수를 커밋하고 다시 굽는다.
