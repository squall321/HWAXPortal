# GLM 심의 품질 검증 보고서 — 의견 단순화 원인 진단과 조절 지점

> 2026-07-21, ultracode 다단계 검증(판독 4 + 적대적 검증 7 + 종합, 12 에이전트)의 산출물.
> agent-server 심의 튜닝 패치(afd507c·35c1610)와 env-kit 권장값의 근거 문서.

# GLM 심의 의견 단순화 — 원인 진단 및 설정 조절 최종 기술 보고서

대상: HWAXAgentServer 심의 파이프라인(`deliberation.py`)의 GLM 페르소나 발언이 Claude MCP 경로(`hwax-deliberate.js`) 대비 단순한 문제.
결론 요약: **"단순함"의 1차 확정 원인은 샘플링 파라미터가 아니라 (1) 표시 계층의 200~340자 강제 절단, (2) JSON-only 프롬프트 계약에 분량 하한 부재, (3) 기저 정량 근거의 완전 부재다.** 파라미터 튜닝(reasoning effort, temperature)은 2차 레버이며, 그 효과는 위 절단·계약 상한에 갇힌다. 조치 우선순위는 "프롬프트 계약·절단 완화 → thinking/effort(extra_body 경로, 활성 여부 선확인) → temperature → max_tokens(설정 시 8192급 여유값)"이다.

---

## 1) 원인 진단

### 1-A. 확정 (CONFIRMED — 코드로 입증)

| # | 원인 | 근거 (파일:라인) |
|---|------|------------------|
| 1 | **표시·회의록 절단이 사용자가 보는 "단순함"의 1차 원인.** `_say_of`/`_clip_sent`가 lens 260 / recommendation 300 / concede 200 / rebut 240 / deepen 320 / final_position 340 / vote 160 / say 폴백 400자로 절단. `first()`가 concede/rebut 배열의 첫 원소만 취해 나머지 반박·수용 전부 유실. RA 회의록도 `[:400]` 캡. 모델이 길게 써도 여기서 눌린다. | `deliberation.py:163-191, 450` |
| 2 | **프롬프트 계약에 분량 하한 부재 + JSON-only 강제.** 시스템 메시지가 "반드시 유효한 JSON 하나만 출력"을 자유 텍스트로 요구(구조화 출력 강제 아님), R1/R2/R3 어느 필드에도 최소 문장수·수치 개수 요구 없음 — 모델이 짧게 써도 계약 충족. | `deliberation.py:123-131, 396-398, 407-409, 417-420` |
| 3 | **기저 컨텍스트 격차 (가장 큰 구조 격차).** GLM 경로 base는 질문 + (조건부) SF 주입뿐. Claude 경로 BASE는 [정량 근거·분석 결과]+[후보/선택지]+이어하기+인간 의견 포함. 인용할 수치 자체가 없다. | `deliberation.py:390` vs `infra/pipeline/hwax-deliberate.js:55-57` |
| 4 | **temperature=0 하드코딩, 샘플링 env 전무.** 전역 단일 ChatOpenAI 인스턴스(max_tokens/top_p/extra_body 미지정), 조절 가능한 env는 `LLM_DISABLE_STREAMING`뿐. 심의는 이 인스턴스를 라운드·페르소나·의장 분기 없이 그대로 재사용. | `app.py:112-123`, `deliberation.py:334, 118-120` |
| 5 | **reasoning_effort/thinking 전달 통로 부재.** agent-server 소스 전체에 reasoning/chat_template_kwargs/extra_body 출현 0건. 반면 RA에는 검증된 전달 패턴이 이미 있고(`body["chat_template_kwargs"]={"reasoning_effort":...}`), langchain-openai 1.3.2의 `extra_body`로 동일 wire 포맷 이식 가능. | RA `backend/app/ai/llm.py:202-203`, RA `backend/app/config.py:175`, `.venv/.../langchain_openai/chat_models/base.py:927-946, 1731` |
| 6 | **파싱 실패의 복리 손실.** 재시도 없이 `{"say": txt[:800]}` 폴백 → 다음 라운드 컨텍스트에 해당 페르소나가 `{"lens": null, ...}`로 주입(say 원문조차 미전달). 페르소나 개별 실패는 무음 탈락. | `deliberation.py:103-115, 129, 402, 204-210` |
| 7 | **의장 합성 입력 빈약.** R1 전체 누락, r3t는 final_position/vote만(non_negotiable·stance 탈락). Claude 경로는 전 라운드 요약 + 최종 라운드 전체 JSON. | `deliberation.py:425, 430-435` vs `hwax-deliberate.js:140-151` |
| 8 | **R1 `reads`(근거 구체 인용) 필드·지시 부재.** Claude 경로만 "구체 인용해 해석"을 스키마+지시문으로 강제. | `hwax-deliberate.js:60-70, 105` vs `deliberation.py:396-398` |
| 9 | **reasoning_content는 라이브러리 단에서 완전 소실.** langchain-openai 1.3.2는 설계상 미추출(additional_kwargs에도 없음) — GLM이 사고에 토큰을 써도 어디에도 안 나타난다. | `.venv/.../langchain_openai/chat_models/base.py:5-11, 214-240`, `deliberation.py:118-120` |
| 10 | **페르소나 role 400자 절단.** Claude 경로는 무절단. | `deliberation.py:378-381` vs `hwax-deliberate.js:58` |
| 11 | **클라이언트가 명시 전송한 temperature=0은 서버측 generation-config로 못 바꾼다.** vLLM 0.23.0은 요청에 없는 파라미터에만 서버 기본 적용. | `app.py:120-123` + vLLM `protocol.py:560-563` |

### 1-B. 부분 확정 (PARTIAL — 정정 반영)

- **C4 (reasoning 예산→content 압축)**: 코드 사실(content만 사용, 라이브러리 소실, effort 미지정=서버 기본)은 전부 확정. 그러나 "reasoning 예산이 낮아 content가 압축된다"는 인과는 **미검증 보조 가설**이다. reasoning_content 소실 자체는 최종 답 길이에 영향 없음. A/B로만 검증 가능.
- **C5 (프롬프트 동형성)**: 코어 필드는 동일하나 `reads` 비대칭은 실질 차이. **"라운드 간 컨텍스트 압축 차이"는 기각** — 양쪽 모두 무절단 전달(`deliberation.py:402, 412` / `js:93-97`). 실증된 차이는 의장 합성 커버리지·BASE 풍부도·실행 주체(Claude 서브에이전트 vs 단발 greedy 호출).
- **C6 (서버측 레버)**: temperature 무력화는 확정. 단 서버 레버가 "parser/chat template/max-model-len 셋뿐"은 축약 — **generation-config의 repetition_penalty(greedy에서도 logits에 적용)·max_new_tokens(클라 미전송이라 기본 상한으로 유효)**도 서버측 유효 레버다. top_p/top_k/min_p 기본값은 greedy라 무효.
- **C7 (기대효과 서열)**: 교정 서열 적용 — §5 참조.

### 1-C. 기각 (REFUTED)

- **"max_tokens 2048~4096 명시가 개선 효과 2위"** — 기각. 현재는 max_tokens 미전송=사실상 무상한(`base.py:1294-1322` None 생략)이므로 명시는 **상한 신설**이며, 사내 실증(RA `config.py:186-189` — 1024 상한에서 finish_reason=length로 미완 JSON 반복)상 오히려 `txt[:800]` 폴백을 유발해 **악화** 가능. thinking 활성 시 reasoning 토큰이 예산을 잠식해 2048은 특히 위험.
- **"reasoning_content를 additional_kwargs로 접근 가능한데 안 쓰는 것"** — 기각. 라이브러리가 폐기한다(`base.py:214-240`).
- **"서버 설정만으로 temperature 교정 가능"** — 기각(위 #11).
- **미확정 전제 경고**: 이 dev 박스는 `VLLM_*` 미설정이라 기본 **qwen2.5-7b-dev**다(`HWAXAgentServer/.env:1-5`, `app.py:52-55`). "단순한 의견" 관찰이 dev(qwen 7B AWQ)에서 나온 것이라면 **모델 급 차이가 지배적**이며 아래 튜닝의 우선순위가 달라진다. 검증 0단계에서 반드시 구분(§4).

---

## 2) 조절 지점 매트릭스

### (a) agent-server 코드+env 레벨 — 즉시 가능

| 항목 | 현재값 | 권장값 | 기대효과 |
|------|--------|--------|----------|
| 심의 경로 temperature | 0 고정 (`app.py:121`) | 심의 한정 `bind(temperature=0.6~0.8)` (env `DELIB_TEMPERATURE`), ReAct 도구호출은 0 유지 | greedy의 짧고 보수적 완성 완화, 페르소나 간 다양성 회복. GLM 계열 권장 0.6~1.0 |
| reasoning effort | 미전달 (grep 0건) | `extra_body={"chat_template_kwargs":{"reasoning_effort": ...}}` (env `LLM_REASONING_EFFORT`, 빈 값=미전달 — RA 규약) | 페르소나 답변 전 사고 심화. **단 B300 GLM이 thinking 기본 활성인지 선확인 필요**(이미 활성이면 "활성화"가 아니라 effort 조절) |
| max_tokens | 미전송(무상한) | 미설정 유지, 설정한다면 `DELIB_MAX_TOKENS=8192`급 여유값 (RA `llm_author_max_tokens=8192` 패턴, `config.py:186-197`) | 서버 기본 변화 방어용. 2048~4096은 절단 위험으로 금지 |
| timeout | 라이브러리 기본 | `VLLM_TIMEOUT_S=180` | effort 상향 후 타임아웃성 빈/잘린 폴백 방지. effort·max_tokens와 반드시 세트 |
| `_say_of`/`_clip_sent` 절단 | 200~340자, `first()` 첫 원소만, transcript `[:400]` (`deliberation.py:163-191, 450`) | 상한 1.5~2배 상향(또는 env화), `first()`→`'; '.join`, transcript 800 | **사용자 체감 "단순함"의 절반을 직접 회복.** 라운드 간 입력은 이미 무절단이므로 표시·RA 기록 품질 전용 |
| role 컨텍스트 절단 | 400자 (`deliberation.py:380`) | 1200~2000자(컨텍스트 예산 확인 후) | 도메인 정체성·배경지식 주입 강화 |
| 파싱 실패 처리 | 재시도 없음, `txt[:800]` 폴백, 다음 라운드 null 주입 (`deliberation.py:129, 402`) | 필수 키 검증 + 에러 피드백 재호출 1~2회, 폴백 시 say 원문을 r1t/r2t에 포함 | 복리 손실 제거 — Claude 경로 schema 재시도와 등가 |
| 의장 합성 입력 | r2t+r3t만, r3t는 2키 (`deliberation.py:425, 430-435`) | r1t 포함 + r3t 키를 (final_position, non_negotiable, vote, stance)로 확장 | 결정문의 합의근거·소수의견 실질화 |
| 배포 경로 | env-kit에 튜닝 키 없음 (`infra/env-kits/agent-server.env:10-12`) | 신규 키 추가 후 `apply-envs.sh agent-server` **명시 실행**(기본 SVCS 목록에 agent-server 없음, `apply-envs.sh:92`) | 운영 반영의 유일한 표준 경로 |

### (b) vLLM 서버 레벨 — 상암 관리자 필요 (기동 플래그 실값은 로컬 근거로 확인 불가)

| 항목 | 현재값 | 권장 조치 | 기대효과 |
|------|--------|-----------|----------|
| `--reasoning-parser glm45` | 미확인 | 설정 여부 확인이 최우선. (a) parser ON+thinking ON이면 클라이언트가 reasoning_content를 버려 짧은 결론만 보임(현상과 정확히 부합), (b) thinking OFF면 깊이 자체 하락, (c) parser OFF면 `<think>`가 content 오염 — 관찰상 깨끗한 JSON이면 (a)/(b) | 판독 분기 확정 |
| `--default-chat-template-kwargs` (vLLM 0.23.0 `cli_args.py:96`) | 미확인 | thinking/effort 서버 기본값 설정 — 클라 무수정 전 서비스 적용. 단 RA 등 공유 소비자 전체 영향이라 클라별 `chat_template_kwargs`(위 (a))가 더 안전 | 폴백 관계의 전역 기본 |
| generation-config `max_new_tokens` / `repetition_penalty` | 미확인 | 클라 미전송 파라미터라 서버 기본이 유효. max_new_tokens가 작게 박혀 있으면 미전송 요청의 답이 짧게 잘림 — **"의견 단순"의 유력 서버측 원인 후보**. `--override-generation-config`로 무배포 조정 가능 | 기본 생성 상한·반복 억제 조정 |
| temperature/top_p/top_k/min_p 서버 기본 | — | **조정 불가 칸.** temperature는 클라가 명시 전송(0), 나머지는 greedy라 무의미 | — |
| `--max-model-len` | dev 16384 (`docs/start-dev-vllm.sh:25`), 상암 미확인 | 상향 검토 — max_tokens 미전송 시 암묵 상한 = max_model_len − prompt | 라운드 누적 프롬프트 뒤 생성 여유 확보 |
| 모델/양자화 스왑 | GLM-5-2 (`infra/env-kits/agent-server.env:5-12`) | `--served-model-name` 유지 교체 | 깊이 상한 자체를 올리는 근본 레버 |

### (c) 프롬프트/구조 레벨

| 항목 | 현재 | 권장 | 기대효과 |
|------|------|------|----------|
| R1 `reads` 필드 | 없음 (`deliberation.py:396-398`) | Claude 경로 동형 복원: `{lens, reads:[], recommendation, concerns:[], position_short}` + "구체 인용해 해석, 수치엔 (도구)/(경험칙) 표기" 지시, r1t 직렬화에 reads 포함 | R1부터 근거 인용 슬롯 생성, R2 반박 재료 증가 |
| 분량 하한 | 없음 | "각 문자열 필드 2~4문장, 수치·표준 1개 이상 인용, concerns 최소 2개, rebut 최소 1개" (position_short만 한 줄 유지) | **GLM은 하한 명시에 민감 — 단순함을 가장 직접 겨냥** |
| JSON 강제 방식 | 자유 텍스트 "JSON만" (`deliberation.py:127`) | vLLM guided_json/response_format json_schema로 이관(형식은 서버 보장), 또는 "산문 논증 후 마지막에 JSON"(`_parse_json`이 첫`{`~막`}` 추출이라 앞 산문 허용, `deliberation.py:103-115`) | JSON 강박 제거로 필드 내용 풍부화 + 파싱 실패 0 |
| 기저 컨텍스트 | 질문만 (`deliberation.py:390`) | 심의 전 게이트웨이 도구 1~2개 호출 결과 요약을 `[정량 근거·분석 결과]` 블록으로 주입, 또는 챗 이전 맥락 포함 | 인용할 데이터 자체가 생김 — 근거 부재 해소 |
| 라운드 수 | 3 고정 (`deliberation.py:393-425`) | 트리거 파싱으로 가변화(Claude 경로는 2~8, `js:50-51`) | 반박-재반박 누적 깊이. 단 지연 트레이드오프 — 부차적 |

### (d) 설정으로 안 되는 한계

- **모델 역량 상한**: dev qwen2.5-7B AWQ라면 어떤 튜닝으로도 Claude급 불가(4bit 양자화는 장문 추론 품질 저하). GLM-5-2라도 Claude와의 급차는 파이프라인 밖 요인.
- **reasoning_content 소실**: langchain-openai 1.3.2 설계상 폐기 — env/서버 설정으로 못 고침. 쓰려면 openai SDK 직접 호출, provider 전용 래퍼, 또는 thinking을 끄고 토큰을 최종 답에 쓰는 선택(코드 변경 필요).
- **실행 주체 구조**: Claude 경로는 서브에이전트가 자유 추론 후 StructuredOutput으로 구조만 회수 — 단발 JSON-only 호출로는 설정만으로 등가 불가.
- **클라 명시 temperature=0**: 서버 관리자만으로는 조정 불가 — (a) 관할의 코드 수정 필수.

---

## 3) 구체 패치 스케치

### 3-1. `app.py` — ChatOpenAI 초기화 env 주도화 (전역은 보수적으로)

```diff
--- /home/koopark/claude/HWAXAgentServer/app.py  (lifespan, 현재 120-123행)
+    # LLM 생성 파라미터 env 주도화 — 기본값은 현행 동작 보존(temp 0, max_tokens 미전송)
+    _eff = os.environ.get("LLM_REASONING_EFFORT", "")   # RA 규약: 빈 값=전달 안 함
+    _mt = int(os.environ.get("LLM_MAX_TOKENS", "0"))    # 0=미전송(무상한 유지)
     app.state.llm = ChatOpenAI(
-        base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, model=VLLM_MODEL, temperature=0,
+        base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, model=VLLM_MODEL,
+        temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),  # ReAct 결정성: 기본 0 유지
+        max_tokens=_mt or None,
+        extra_body=({"chat_template_kwargs": {"reasoning_effort": _eff}} if _eff else None),
+        timeout=float(os.environ.get("VLLM_TIMEOUT_S", "180")),
         disable_streaming=disable_stream,
     )
```

주의 — `ChatOpenAI` 톱레벨 `reasoning_effort` 필드는 OpenAI 표준 최상위 파라미터로 나가므로 쓰지 말 것. GLM chat_template용은 반드시 `extra_body` 경유 `chat_template_kwargs`(RA 검증 wire 포맷, `base.py:927-946`, RA `llm.py:202-203`).

### 3-2. `deliberation.py` — 심의 전용 파라미터 분리 (권장 옵션 B)

`bind` kwargs는 `payload = {**self._default_params, **kwargs}`(`base.py:1731`)로 병합되므로 요청별 적용이 보장된다. 도구호출 경로의 temp 0은 건드리지 않는다.

```diff
--- /home/koopark/claude/HWAXAgentServer/deliberation.py  (현재 334행)
-    llm = app.state.llm
+    _kw = {"temperature": float(os.environ.get("DELIB_TEMPERATURE", "0.7"))}
+    if int(os.environ.get("DELIB_MAX_TOKENS", "0")):
+        _kw["max_tokens"] = int(os.environ["DELIB_MAX_TOKENS"])   # 설정 시 8192급 권장
+    _eff = os.environ.get("LLM_REASONING_EFFORT", "")
+    if _eff:
+        _kw["extra_body"] = {"chat_template_kwargs": {"reasoning_effort": _eff}}
+    llm = app.state.llm.bind(**_kw)
```

### 3-3. env-kit 반영 — `/home/koopark/claude/HWAXPortal/infra/env-kits/agent-server.env`

```ini
# --- 심의 LLM 튜닝 (기존 10-12행 VLLM_* 상속 아래에 추가) ---
LLM_REASONING_EFFORT=@FROM_RA:LLM_REASONING_EFFORT@   # RA backend/.env(cae00)에 키가 먼저 있어야 상속됨 — 없으면 skip(apply-envs.sh:42-49)
DELIB_TEMPERATURE=0.7
DELIB_MAX_TOKENS=8192
VLLM_TIMEOUT_S=180
```

배포 절차(cae00): RA `backend/.env`에 `LLM_REASONING_EFFORT=high` 선기입(운영 파일 — RA 레포 커밋 대상 아님) → `bash infra/env-kits/apply-envs.sh agent-server`(**기본 SVCS 목록에 agent-server 없음** — 인자 명시 필수, `apply-envs.sh:92`) → agent-server 재시작. 멱등이라 재실행 안전.

### 3-4. 절단·프롬프트 패치 (동시 권장 — 실제 1순위)

- `deliberation.py:163-191` — `_clip_sent` 상한 1.5~2배 상향(또는 `DELIB_CLIP_SCALE` env), `first()`→`'; '.join`, 450행 transcript 캡 400→800.
- `deliberation.py:396-398` — R1에 `reads:[]` + "구체 인용" 지시 + 필드별 "2~4문장, 수치·표준 1개 이상" 하한 추가, 402행 r1t 직렬화 키에 reads 포함.
- `deliberation.py:129` — 파싱 실패/필수 키 결손 시 1~2회 재호출, 최종 폴백의 say를 402/412행 직렬화에 포함.
- `deliberation.py:425, 430-435` — 의장 입력에 r1t 추가, r3t 키 확장.

---

## 4) 검증 방법 — 패치 후 A/B 절차

**0단계 — 관찰 출처 확정 (필수 선행).** `curl $VLLM_BASE_URL/models`로 실제 서빙 모델 확인. 이 dev 박스는 `VLLM_*` 미설정이라 qwen2.5-7b-dev다(`HWAXAgentServer/.env:1-5`). 관찰이 qwen에서 나온 것이면 모델 급 차이가 지배적이므로 파라미터 A/B 전에 운영 GLM에서 재현부터 확인한다.

**1단계 — thinking 활성 여부 진단.** langchain을 우회한 raw curl로 `/v1/chat/completions` 호출(effort 미전달/`chat_template_kwargs.reasoning_effort=high` 각 1회), 응답의 `reasoning_content` 유무·길이와 content 내 `<think>` 혼입을 확인(RA `llm.py:253-268` 파싱 선례). 이것으로 §2(b)의 (a)/(b)/(c) 분기를 확정한다.

**2단계 — 베이스라인 채록.** 동일 심의 주제 1개를 현행 설정으로 3회 실행. 절단 전 원본 JSON을 관측할 수 있도록 라운드 로그에 raw 필드 길이를 임시 기록(진단용으로 `reasoning_content` 길이도 — RA "진단 탭" 패턴과 대칭).

**3단계 — 단일 변수 A/B.** 같은 주제로 한 번에 하나씩 적용·3회 실행.
1. 프롬프트 계약(reads+분량 하한) — §3-4
2. 절단 완화(`_say_of`/`first()`)
3. `LLM_REASONING_EFFORT=high` (extra_body 경로)
4. `DELIB_TEMPERATURE=0.7`
5. (필요 시) `DELIB_MAX_TOKENS=8192`

**측정 지표.**
- 품질: 필드별 원본 문자수(절단 전), 발언당 구체 수치·표준 인용 개수, R2 rebut 항목 수, 의사결정문의 소수의견·제약 반영 여부.
- 건전성(가드레일): JSON 파싱 실패율(`{"say"}` 폴백 횟수), 무음 탈락 페르소나 수, `finish_reason=length` 발생, content 내 `<think>` 혼입, 라운드당 지연·타임아웃.
- 판정: 품질 지표 상승 + 가드레일 무악화면 채택. 파싱 실패율이 오르면(특히 effort 적용 후) 서버 reasoning parser 설정을 먼저 의심한다(§2(b)).

---

## 5) 주의사항 — 검증 정정 반영 (PARTIAL 항목)

1. **(C7 정정) 서열 교정.** "reasoning_effort > max_tokens > temperature"가 아니라 **"프롬프트 계약·절단 완화 > thinking/effort > temperature > max_tokens"**다. 프롬프트 계약과 `_say_of` 절단이 코드로 확정된 1차 원인이며, 어떤 샘플링 튜닝도 이 상한을 못 넘는다.
2. **(C7 정정) max_tokens는 개선 레버가 아니다.** 현재 미전송=무상한이므로 명시는 상한 신설. 설정한다면 절단 방지용 8192급(RA `config.py:186-197` 선례). 2048~4096은 thinking 토큰 잠식과 겹쳐 미완 JSON→`txt[:800]` 폴백으로 **단순화를 악화**시킬 수 있다.
3. **(C4 정정) "reasoning 예산→content 압축"은 미검증 보조 가설.** reasoning_content 소실 자체는 답 길이에 영향 없음. effort의 효과는 §4의 A/B로만 판정하고, 사전 확신으로 다른 레버를 미루지 말 것.
4. **(C4/C1 조건) effort 전달 경로와 활성 전제.** 반드시 `extra_body={"chat_template_kwargs":{...}}` 경로(톱레벨 필드 금지). B300 GLM-5.2가 thinking을 이미 기본 활성 중일 가능성이 미검증이라 이 조치는 "활성화"가 아닌 "effort 조절"에 그칠 수 있다 — 1단계 진단 선행.
5. **(C5 정정) 라운드 간 컨텍스트 절단은 원인이 아니다.** r1t/r2t는 무절단(`deliberation.py:402, 412`) — 절단 완화 패치는 표시·RA 기록 품질용이지 심의 내부 품질용이 아니다. 내부 품질 격차의 실체는 reads 부재·BASE 빈약·의장 입력 커버리지다.
6. **(C6 정정) 서버측 "조정 불가"를 과대평가하지 말 것.** temperature만 무력이고, generation-config의 `max_new_tokens`·`repetition_penalty`는 서버측 유효 레버다. 단 이 결론은 agent-server 클라이언트 한정 — RA는 temperature를 조건부 전송하는 별도 클라이언트(RA `llm.py:192-193`)라 서버 기본 temperature가 적용될 수 있으므로, 상암 서버 기본값 변경 시 RA 등 공유 소비자 영향을 함께 본다.
7. **회귀 위험 2건.** (i) thinking ON + reasoning parser 미스매치면 `<think>`가 content에 섞여 파싱 실패율 상승 → 폴백 절단으로 오히려 단순화(§2(b) 분기 (c)). (ii) effort·컨텍스트 확대 후 프롬프트가 max-model-len을 넘으면 절단이 아니라 400 에러 — RA의 `LLMContextError` 휴리스틱(RA `llm.py:229-241`)이 처리 선례.
8. **운영 절차 함정.** `apply-envs.sh` 기본 서비스 목록에 agent-server가 없어 인자 명시 필수(`apply-envs.sh:92`). `@FROM_RA` 상속은 cae00 RA `backend/.env`에 키가 선존재해야 하며(없으면 무음 skip), RA 레포는 hands-off 대상이므로 커밋 없이 운영 파일로만 기입한다.

---

## 부록 — 적대적 검증 판정 원문

**CONFIRMED** — C1: agent-server의 ChatOpenAI는 temperature=0으로 하드코딩되어 있고 max_tokens·top_p는 미지정이다(app.py lifespan). 조절용 env 변수는 LLM_DISABLE_STREAMING뿐이다.

/home/koopark/claude/HWAXAgentServer/app.py:112-123 — lifespan 내 `app.state.llm = ChatOpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, model=VLLM_MODEL, temperature=0, disable_streaming=disable_stream)`. temperature는 리터럴 0 하드코딩, max_tokens/top_p는 kwargs에 없음(langchain-openai 기본 None). app.py:119 `disable_stream = os.environ.get("LLM_DISABLE_STREAMING", "0") == "1"` 이 생성 동작을 조절하는 유일한 env 토글. 반증 시도 결과: 비-venv 코드 전체(app.py, deliberation.py)에서 max_tokens/top_p/bind()/with_config/model_kwargs/extra_body 출현 0건; 런타임 ChatOpenAI 인스턴스는 1개뿐(test_app.py:75는 더미 URL 테스트 전용); 호출부(app.py:247 create_react_agent, deliberation.py:118-119 _llm_text의 ainvoke)는 호출별 kwargs 없이 동일 인스턴스 사용; .env에도 샘플링 관련 키 없음(LLM_DISABLE_STREAMING=0만 존재). 참고: VLLM_BASE_URL/VLLM_MODEL/VLLM_API_KEY(app.py:52-55)도 ChatOpenAI 생성자에 들어가는 env지만 접속·모델 선택용이며 샘플링/생성 파라미터 조절 통로는 아니므로 주장과 상충하지 않음.

**CONFIRMED** — C2: deliberation.py의 페르소나 라운드는 app.state.llm 단일 인스턴스를 그대로 재사용하며, 라운드별·페르소나별 샘플링 파라미터 분기가 전혀 없다.

(1) /home/koopark/claude/HWAXAgentServer/app.py:120-123 — ChatOpenAI 생성은 이곳 단 한 곳: `app.state.llm = ChatOpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, model=VLLM_MODEL, temperature=0, disable_streaming=disable_stream)`. (2) /home/koopark/claude/HWAXAgentServer/deliberation.py:334 — `llm = app.state.llm` 이 유일한 획득 지점이고, 이 객체가 R1/R2/R3 라운드(396, 407, 417행 `_round_live(llm, ...)`), SF 연관성 판정(303-304행), 의장 합성(430-431행)에 전부 그대로 전달됨. (3) deliberation.py:118-120 `_llm_text` 는 `await llm.ainvoke([("system",...),("human",...)])` 로 호출별 kwargs 없음. (4) deliberation.py:199-202 `_round_live` 는 페르소나별로 같은 llm 에 태스크만 생성. (5) 두 파일 전체에서 `bind(`/`with_config`/`top_p`/`max_tokens`/`extra_body`/`model_kwargs` 그렙 0건 — 라운드 번호(rnd)는 프롬프트 문구와 SSE 이벤트에만 쓰이고 샘플링 파라미터 분기는 존재하지 않음.

**CONFIRMED** — C3: agent-server에는 reasoning_effort(또는 thinking 제어)를 GLM에 전달하는 코드가 없다. 반면 ReportArchive backend/app/ai/llm.py에는 LLM_REASONING_EFFORT→chat_template_kwargs 전달 패턴이 이미 구현되어 있어 이식 가능하다.

[전반부] HWAXAgentServer 전체(.venv 제외: app.py, deliberation.py, mcp_demo_server.py, test_app.py)를 reasoning|thinking|chat_template_kwargs|extra_body 로 grep → 0건. 유일한 LLM 초기화 /home/koopark/claude/HWAXAgentServer/app.py:120-123 은 "ChatOpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, model=VLLM_MODEL, temperature=0, disable_streaming=disable_stream)" 만 — extra_body/model_kwargs 미사용이라 GLM 에 chat_template_kwargs 를 실어 보낼 통로 자체가 없음. [후반부] ReportArchive: config.py:175 "llm_reasoning_effort: str = Field(default=\"\")" (BaseSettings, env_prefix 없음 → LLM_REASONING_EFFORT 매핑; llm.py:23 docstring "LLM_REASONING_EFFORT = low|medium|high (빈 값=전달 안 함)"), llm.py:202-203 및 스트리밍 경로 412-413 "if reasoning_effort: body[\"chat_template_kwargs\"] = {\"reasoning_effort\": reasoning_effort}", 기본값 해석 llm.py:514-515/561-562 (settings.llm_reasoning_effort or None). 응답측 reasoning_content 분리 파싱도 구현(llm.py:259-268, 456-462). [이식 가능 판단] ReportArchive 는 httpx 직접 POST, agent-server 는 langchain-openai 라 코드 복붙은 아니지만, 설치된 langchain-openai 1.3.2 가 extra_body 를 정식 지원(.venv/.../langchain_openai/chat_models/base.py:927)하므로 ChatOpenAI(extra_body={"chat_template_kwargs": {"reasoning_effort": ...}}) 로 동일 패턴 이식 가능 — 판단도 타당.

**PARTIAL** — C4: GLM이 reasoning_content(사고 과정)를 별도 필드로 반환해도 agent-server 경로에서는 본문(content)만 사용되며, reasoning 예산을 낮게/기본으로 쓰면 content가 압축될 수 있다 — 이것이 "의견 단순화"의 유력 원인 중 하나다.

[코드 사실 — 전부 확인됨] (1) content만 사용: /home/koopark/claude/HWAXAgentServer/deliberation.py:118-120 `_llm_text`가 `r.content`만 반환, 소스 전체 reasoning/additional_kwargs 참조 0건(grep), 유일한 다른 접근점도 app.py:308 `chunk.content`. (2) 라이브러리 단 소실: .venv langchain_openai 1.3.2 base.py:5-11 docstring "reasoning_content ... are **not** extracted or preserved", _convert_dict_to_message(base.py:214-240) assistant 분기는 function_call/tool_calls/audio만 추출 — reasoning_content는 접근조차 불가. (3) reasoning 예산 미지정: app.py:120-123 ChatOpenAI(temperature=0, disable_streaming)만, reasoning_effort(base.py:748 기본 None)/extra_body/chat_template_kwargs 미사용(소스·.env·infra/env-kits grep 0건) → 운영 GLM-5-2는 서버측 기본 reasoning 동작 적용. (4) 전제 타당: 동일 GLM 엔드포인트를 쓰는 ReportArchive/backend/app/ai/llm.py:253-268이 reasoning_content/reasoning을 분리 파싱하고 llm.py:201-203이 chat_template_kwargs.reasoning_effort(low|medium|high, config.py:173-175)를 전달 — 이 배포의 GLM이 reasoning 분리 필드 모델임을 입증.

정정: 코드 사실부(content만 사용, 라이브러리 단 reasoning_content 소실, reasoning 예산 미지정→서버 기본값)는 전부 맞다. 그러나 "유력 원인 중 하나"라는 판단은 과하다. ① "reasoning 예산 기본 → content 압축" 인과는 코드·설정 어디에서도 입증 불가한 모델 행동 가설이고, reasoning_content 소실 자체는 최종 답변(content) 길이에 영향을 주지 않는다(reasoning은 원래 표시 대상이 아님). ② 코드로 입증되는 훨씬 직접적인 "의견 단순화" 원인이 별도로 존재한다 — deliberation.py의 _say_of/_clip_sent가 표시 발언을 필드별 200~340자로 강제 절단, 페르소나 프롬프트의 JSON-only 계약에 최소 분량 요구 부재(123-131행), 파싱 실패 시 txt[:800] 절단 폴백. 정정: "유력 원인" → "검증되지 않은 보조 가설"로 강등하고, 검증하려면 ReportArchive처럼 chat_template_kwargs.reasoning_effort를 명시 설정(ChatOpenAI extra_body 경유)해 A/B 비교가 필요하다.

**PARTIAL** — C5: GLM 심의 경로와 Claude MCP 경로의 페르소나 요구 필드는 실질적으로 동일하다. 그러나 구조 강제 방식(스키마 검증+재시도 vs 프롬프트 JSON 요청)과 이전 라운드 컨텍스트 압축 정도는 다를 수 있으며, 이 차이가 출력 깊이에 기여할 수 있다.

[필드 동일성 — 코어는 동일, 주변부 차이 존재] MCP R1 스키마 OP_SCHEMA(/home/koopark/claude/HWAXPortal/infra/pipeline/hwax-deliberate.js:60-70)는 {persona,lens,reads[],recommendation,concerns[]}에 required=[persona,lens,recommendation,concerns]. GLM R1(/home/koopark/claude/HWAXAgentServer/deliberation.py:396-398)은 "JSON {lens,recommendation,concerns:[],position_short} 로." — MCP만 reads(근거 구체 인용 해석), GLM만 position_short. R2는 양쪽 {concede,rebut,deepen} 동일(js:71-80 vs py:407-409). R3는 MCP {persona,final_position,non_negotiable,vote}, required=[persona,final_position,vote](js:81-90) vs GLM {final_position,non_negotiable,vote,stance,position_short}(py:417-420) — GLM만 stance/position_short 추가. [구조 강제 — 방향 확인] GLM: sysmsg "반드시 유효한 JSON 하나만 출력하세요"(py:127) + 관대 파싱 후 실패 시 {"say": txt[:800]} 폴백(py:129), 재시도 없음. MCP: agent(..., {schema: OP_SCHEMA/R2_SCHEMA/R3_SCHEMA})로 JSON 스키마 전달(js:108, 122, 135). [컨텍스트 압축 — 라운드 간은 양쪽 다 무절단] GLM r1t/r2t는 서브셋 필드의 원본 json.dumps 무절단(py:402, 412). MCP priorText도 summarize()가 같은 서브셋(lens/recommendation/concerns; concede/rebut/deepen)을 절단 없이 결합(js:93-97, 112, 125). 실제 차이는 의장 합성 입력 — MCP는 전 라운드 요약 + JSON.stringify(rFinal, null, 1) 최종 라운드 원본 전체(js:140-151), GLM은 r2t+r3t만이고 R1 배제·r3t는 final_position/vote만(py:425, 430-435) — 과 BASE 풍부도 — MCP BASE는 [정량 근거·분석 결과]+[후보/선택지] 포함(js:57), GLM base는 질문+선택적 SF 환기뿐(py:390). 두 워크플로 사본(.claude/workflows/ 와 infra/pipeline/)은 diff 결과 동일(17319바이트).

정정: 3가지 정정. (1) "요구 필드 실질 동일"은 코어(lens/recommendation/concerns, concede/rebut/deepen, final_position/non_negotiable/vote)에 한해 맞다 — MCP R1에만 reads(근거 구체 인용 해석)가 있고 R1 지시문도 "구체 인용해 해석"을 명시적으로 요구하며(js:105), GLM에만 position_short/stance(UI 버블·수렴 집계용)가 있다. reads 비대칭은 출력 깊이와 무관하지 않은 실질 차이다. (2) "스키마 검증+재시도" 중 리포 코드에서 확인되는 것은 스키마 전달(agent options)까지다 — 검증·재시도 동작은 워크플로 하니스(Claude Code 러너) 구현 소관으로 이 리포에서 직접 검증 불가. "프롬프트 JSON 요청 vs 구조화 스키마 전달"이라는 방향성 자체는 확인. (3) "이전 라운드 컨텍스트 압축 정도 차이"는 페르소나 라운드 레벨에서는 성립하지 않는다 — 양쪽 모두 같은 필드 서브셋을 무절단으로 전달한다. 출력 깊이에 기여할 수 있는 실증된 컨텍스트 차이는 압축이 아니라 (a) 의장 합성 단계 커버리지(MCP: 전 라운드+최종 라운드 원본 JSON vs GLM: R2·R3 서브셋만, R1 배제), (b) BASE 입력 풍부도(MCP: 정량 근거+선택지 주입 vs GLM: 질문+선택적 SF 환기), (c) 실행 주체(Claude 서브에이전트 vs temperature=0 단발 GLM 호출)다.

**PARTIAL** — C6: 클라이언트가 temperature=0을 명시 전송하므로 vLLM 서버측 generation-config 기본값으로는 temperature를 바꿀 수 없다. 서버측에서 유효한 레버는 reasoning parser 설정, chat template 기본 kwargs, max-model-len 정도다.

[전반부 사실 — 확인] (1) HWAXAgentServer/app.py:120-123 ChatOpenAI(..., temperature=0) 단일 인스턴스, deliberation.py:334 그대로 사용, _llm_text(deliberation.py:118-120)는 kwargs 없는 ainvoke. (2) langchain_openai 1.3.2 base.py:1292-1322 _default_params의 필터는 `if v is not None`이라 temperature=0.0이 모든 chat completions 페이로드에 포함됨(0이 falsy라 누락된다는 반증 실패). base.py:4175의 temperature 제거는 responses API 전용(base.py:4116-4128 조건상 이 스택은 미해당). (3) dev SIF(vllm-openai-latest.sif) 내 vLLM 0.23.0 소스 — app.py:116-117 주석상 운영 GLM 서버도 vLLM 0.23.0: vllm/entrypoints/openai/chat_completion/protocol.py:560-563 `if (temperature := self.temperature) is None: temperature = default_sampling_params.get("temperature", ...)` — 요청에 temperature가 있으면 서버 generation-config 기본값은 적용 불가. --override-generation-config도 get_diff_sampling_param(vllm/config/model.py:1458-1488)을 거쳐 '기본값'으로만 쓰여 강제 불가. [후반부 레버 실재 — 확인] --reasoning-parser(vllm/engine/arg_utils.py:931), default_chat_template_kwargs(vllm/entrypoints/openai/cli_args.py:96, 요청 chat_template_kwargs와 병합), --max-model-len 모두 0.23.0에 실재. [후반부 '정도다' 반증 근거] get_diff_sampling_param(config/model.py:1480-1487)은 repetition_penalty/top_k/top_p/min_p/max_new_tokens를 서버 기본값으로 주입하며, 이 클라이언트는 temperature 외 파라미터를 전혀 안 보냄(exclude_if_none) → repetition_penalty는 greedy에서도 argmax 전 logits에 적용되고(vllm/v1/sample/sampler.py:403-408 주석 "Apply logits processors which can impact greedy sampling"; protocol.py:555-558이 generation-config 기본값 사용), max_new_tokens 기본 출력 상한도 유효(chat_completion/serving.py:154-157).

정정: 첫 문장(명시 전송된 temperature=0은 서버 generation-config로 못 바꿈)은 코드로 완전 확인됨. 그러나 둘째 문장의 '서버측 유효 레버는 그 셋 정도'는 과한 축약 — generation-config는 temperature에만 무력할 뿐, 클라이언트가 전송하지 않는 repetition_penalty(temp=0 greedy에서도 logits에 적용되어 출력에 영향)와 max_new_tokens 기본 출력 상한은 generation-config/--override-generation-config로 여전히 서버측에서 조정 가능한 유효 레버다. top_p/top_k/min_p 기본값은 greedy라 무효인 것이 맞음. 정정 문장: '서버측 레버는 reasoning parser, chat template 기본 kwargs(--default-chat-template-kwargs), max-model-len에 더해, generation-config 기본값 중 repetition_penalty·max_new_tokens도 유효하다(temperature·top_p·top_k·min_p는 무효).' 부가 스코프 주의: 이 결론은 agent-server(심의 체인) 클라이언트에 한정 — ReportArchive backend/app/ai/llm.py는 temperature가 None이면 아예 전송하지 않는 별도 클라이언트(llm.py:192-193)라 그 경로에서는 서버 기본 temperature가 적용될 수 있다.

**PARTIAL** — C7: 기대효과 서열 — (1) reasoning_effort/thinking 활성 전달, (2) max_tokens 명시(2048~4096), (3) temperature 0→0.6~0.8 상향 순으로 '의견 단순화' 개선 효과가 클 것이다. temperature 단독 상향은 다양성만 늘리고 깊이는 못 늘릴 수 있다.

전제 사실은 확인됨 — HWAXAgentServer/app.py:120-123 (ChatOpenAI temperature=0만 명시, max_tokens/reasoning/extra_body 미지정), langchain_openai/chat_models/base.py:1294-1322 (None 파라미터는 요청 페이로드에서 완전 생략 → 현재 요청에 max_tokens 자체가 없음 = vLLM에서 컨텍스트 한도까지 무제한). 서열 반증 근거 — ① ReportArchive/backend/app/config.py:186-189 "llm_max_tokens(1024)로는 쉽게 잘려(finish_reason=length) 미완 JSON → 파싱 실패가 매번 반복" (같은 GLM-5-2 서버 사내 실증: max_tokens 명시는 깊이 부스터가 아니라 절단 유발 상한) + deliberation.py:129 파싱 실패 시 txt[:800] 폴백 → 단순화 악화 경로. ② ReportArchive/backend/app/ai/llm.py:201-203 및 docs/[완료] B300_보조AI_설계.md:245,264 — 이 배포의 reasoning 제어는 chat_template_kwargs.reasoning_effort 경유(ChatOpenAI 톱레벨 reasoning_effort 필드 아님, extra_body 필요), llm.py:11-13·설계서 273행 has_reasoning — 운영 서버가 reasoning_content를 기본 반환한다고 전제(thinking 이미 활성일 가능성, dev 박스에서 B300 접근 불가·fixture 미반입으로 미검증). ③ deliberation.py:163-191 _say_of/_clip_sent 200~340자 절단 + 125-127 JSON-only 계약 — 어떤 샘플링 파라미터로도 가시 출력은 이 상한을 못 넘음. ④ (3)의 판단(temperature=다양성, 깊이 아님)은 반증 근거 없음.

정정: 서열 정정: (2) max_tokens 명시(2048~4096)는 '개선 효과 2위'가 아니라 효과 없음~역효과다 — 현재 클라이언트는 max_tokens를 아예 보내지 않아(무상한) 명시는 상한 신설이며, 사내 실증(RA config.py:186-189)상 상한은 미완 JSON 절단 → txt[:800] 폴백으로 의견 단순화를 오히려 악화시킬 수 있다(thinking 활성 시 reasoning 토큰이 예산을 잠식해 2048은 특히 위험). (1)은 방향은 타당하나 두 조건부 — 전달 경로는 ChatOpenAI reasoning_effort 필드가 아닌 extra_body={"chat_template_kwargs":{"reasoning_effort":...}}여야 하고(RA 검증 경로), B300 GLM-5.2가 thinking을 이미 기본 활성 중일 가능성이 미검증이라 '활성 전달'이 아닌 effort 조절에 그칠 수 있다. 또한 서열 전체보다 지배적인 레버가 누락됨 — 프롬프트 계약(JSON-only·한 줄 요약 요구·최소 분량 없음)과 _say_of 200~340자 표시 절단이 코드로 확정된 단순화의 1차 원인이며, 파라미터 튜닝 효과는 이 절단 상한에 갇힌다. 교정 서열: 프롬프트 계약·절단 완화 > (1) thinking(extra_body 경로, 활성 여부 선확인) > (3) temperature > (2) max_tokens(설정한다면 절단 방지용 여유값 8192급, 2048~4096 아님).
---

## §5. 하네스·프롬프트 회복 가능성 패널 (2026-07-21 증보)

> 질문: 잔여 깊이 격차를 하네스(오케스트레이션)·프롬프트로 어디까지 좁힐 수 있나?
> 방법: 4렌즈(프롬프트 공학/하네스/모델한계 회의론/실증설계) 독립 제안 → 렌즈별 반박 검증(8 에이전트).

### 결론 — 격차는 삼분된다

| 몫 | 회복 가능성 | 수단 |
|---|---|---|
| 수치 인용 | **대부분 회복** | 근거 팩 선주입(도구 정량결과를 base에) — 기억 인출→컨텍스트 발췌로 과제 전환 |
| 반박 표적 특정성·사고의 양 | **절반 회복** | verbatim 인용 반박 계약+코드 검증, 산문 후 JSON, 교차심문 페어링 |
| 자발적 경험칙 인출·다단 인과 링크 타당성·판정자 능력 | **불가(가중치 소관)** | 모델 교체 외 없음 |

4렌즈가 독립적으로 같은 2개를 1순위로 수렴: **근거 팩 선주입**(수치 부재의 뿌리 해소, _defect_briefing 패턴 재사용)과 **반박 인용 강제**(quote가 상대 발언에 실재하는지 프로그램 검증 — 깊이 지표 중 유일하게 코드로 검증 가능).

### 검증 통과 기법 (유효 판정)

1. **근거 팩 선주입** — 심의 전 도구 1~3콜로 정량 근거를 base에 주입. 수치 하한 계약은 근거 블록이 있을 때만 순효과(없으면 환각 압력).
2. **반박 인용 강제** — rebut을 {target, quote(원문 20자+), counter, basis} 객체로. 검증 대상은 모델이 실제 본 r1t(직렬화·절단 후) 문자열, 공백 정규화 후 부분 문자열 비교. _ser_val dict→json.dumps, _say_of 합성 보강 필요.
3. **산문 논증 후 JSON** — JSON-only 계약 해제(Tam et al. 2024). 조건: thinking 진단(러너북 §4) 선행 — thinking 이미 활성이면 효과 중복 소멸. _parse_json이 산문 중 '{' 등장 시 오추출하는 엣지 → 균형 괄호 역스캔 보강 + RETRIES 2.
4. **교차심문 페어링** — R2를 '5인 요약→일반론 반박'에서 '지목 표적의 원본 전체→표적 반박'으로. 거의 비용 중립.
5. **입장 앵커 재주입** — R3 수렴 시 자기 R1 핵심 주장을 재주입해 동조 붕괴(sycophantic collapse) 방어. **라운드 늘리기보다 선행 필수** — 방어 없는 라운드 추가는 희석을 늘린다.
6. **의장 보강** — best-of-n(의장 한정 +2~3콜) / 결정문 출처 태깅(항목마다 어느 라운드 발언 유래인지 — 절충형 뭉개기 가시화).

### 조건부 (성립 조건 붙음)

- 수치 앵커 전 라운드 확장 — 근거 팩 선주입 이후에만(없으면 (경험칙) 남발·환각 표준명 위험).
- 발언 분해(초안→자기비판→구조화 2~3콜) — 자기비판이 환각 수치 펌프가 될 수 있음, 벽시계 2~3배.
- Socratic 프로브·수치 원장·전담 챌린저 — 전부 판정자가 같은 GLM이라는 상한 + 근거 팩 전제.
- 의장 2-pass — evidence back-fill로 한정, '수정본 전문만·메타 코멘트 금지' 출력 계약 필수.

### 실행 순서 (실증 렌즈 T-서열)

**T0 계측 하네스(비용 0, 선행 필수)** — 수치 인용 밀도(근거 유래/비유래 분리)·반박 타겟률·신규 개념 도입률·결정문 수치 밀도 + 가드레일(파싱 실패율·필드 원본 길이). → **T1 근거 주입 → T2 반박 계약 → T3 산문 선행(T4 thinking 진단 후) → T4 effort A/B → T5 의장 2-pass → T6 라운드 가변·레드팀(후순위)**. 조건당 3문항×3회, cae00 배치(러너북 §5 연계). **동시 적용 금지** — GLM급은 다중 제약에서 지시 추종 예산이 분산돼 기법 적층이 상쇄된다(단일 변수 A/B만).

### 원리적 한계 (모델 교체 없이 불가)

- 0.7R급 실무 감각의 자발적 인출 — 근거 주입은 지식을 '조달'할 뿐 '이식' 못함.
- 다단 인과 사슬(K-지배→z-open→장피치 집중류)의 링크 조합 타당성 — 형태만 강제되면 링크가 틀린 채 형식을 갖춘 장문. 전원 같은 GLM이라 상관 맹점으로 상호 검토 통과.
- verbose-but-shallow 자동 판별 불가 — 대리 지표는 계약이 생기는 순간 게임됨. 결론 미주입 홀드아웃 재현(§7 프로브)이 유일한 실측 장치이나, 정답이 RA #10·#14에 저장돼 있어 근거 팩과 병용 시 오염 통제 필요.
