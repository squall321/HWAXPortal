# HWAX 인터넷 검색·분석 도입 — 합성 실행 계획

> 아래 계획의 근거는 네 관점이 제출한 실측 + 이번 합성 과정에서 재확인한 실측이다. 재확인 결과 **관점 간 사실 충돌 3건을 정정**했다(§3-J).

---

## 1. 결론 한 문단

**HEAXHub 인티그레이션 앱 1개(`web-research-mcp`, fastapi 스택, `mcp.expose:true`)를 만들어 조직 유일의 외부 egress 초크포인트로 삼고, 그 안에 증거 원장(본문은 서버 보관, LLM 에는 `doc_id`+문장 인덱스만) · 3상태 어댑터 계약 · 단일 HTTP 래퍼 · append-only egress 로그를 가둔다.** 게이트웨이가 60초 폴링으로 자동 흡수하므로 챗·심의·ReportArchive 저장까지 기존 코드 수정은 0이다. 착수 순서는 품질이 아니라 **승인 종속성 순**이다 — 무인증·약관 명시허용인 공공 학술 API(arXiv·OpenAlex·Crossref·PubMed·Wikipedia)로 수집→추출→원장→인용검증→심의통합 파이프라인 **전체를 승인 없이 완성·검증**하고, 일반 웹(Brave)은 보안 승인과 시크릿 주입 경로 결정이 끝난 뒤에만 스위치 하나로 켠다. 도달 가능한 수준은 **"출처가 코드로 검증되고, 나간 문자열 전량을 제시할 수 있고, 안 되는 것을 안 된다고 말하는 리서치"** 까지다. **"클로드급"에는 못 미친다** — 재질의 루프 깊이, JS 렌더, PDF 표, 함의 판정이 구조적으로 빠지며(§7), 그 격차는 튜닝이 아니라 별도 투자로만 메워진다.

---

## 2. 단계 계획

승인 대기를 제외한 순수 개발 **약 17 작업일**. P1(승인)은 P2~P6 과 완전 병렬이며, **P7 이전까지 어떤 단계도 승인에 종속되지 않는다.**

| # | 단계 | 산출물 | 검증 방법 (무엇을 돌려 무엇을 보면 성공인가) | 소요 | 선행조건 |
|---|---|---|---|---|---|
| **P0** | cae00 망 실측 | `check-egress.sh` 실행 결과표(dev vs cae00 대조) | `bash /home/koopark/claude/HWAXPortal/infra/scripts/check-egress.sh --json` 을 cae00 에서 실행 + `--sif` 로 컨테이너 내부 CA 상속까지 확인. **issuer 에 사내 CA → MITM 확정 / 전부 000·타임아웃 → 폐쇄망 확정 / 공개 CA+200 → dev 동일.** 3분기 중 하나로 확정되면 성공 | 0.5d | cae00 접근 권한자 30분 |
| **P1** | 승인 착수 (병렬) | 보안 검토 요청서 1부 + HEAXHub 공유 인프라 변경(§5-①) 결정 요청 | 승인이 아니라 **"무엇을 만족하면 승인하겠다"는 조건을 문서로 받는 것**이 성공 기준 | 0.5d + 대기 | P0 결과표 |
| **P2** | 앱 골격 + MCP 등록 (**egress 0**) | upstream 레포 최소 세트 + `HEAXHub/integrations/web-research-mcp/.portal/manifest.yaml` + 도구 2개(`search_internal`, `describe_search_status`) | ① `check-mcp-registration.sh --watch web_research_mcp` 5단계 통과 ② `curl -s :9110/tools-map \| jq '.map \| to_entries[] \| select(.value=="heax-web_research_mcp")'` 에 **프리픽스 없는 원래 이름**으로 등장 ③ `python -c "from deliberation import _free_tool_ok; print(_free_tool_ok('search_internal'))"` → `True` ④ 심의 1건 실행 후 `audit.jsonl` 에 호출이 실제로 찍힘 ⑤ **컨테이너 안 `curl https://example.com` 실패 + 호스트 `ss -tnp \| grep <pid>` 외부 커넥션 0건** | 2d | 없음 |
| **P3** | 증거 원장 코어 (**egress 0, LLM 0**) | fetch→추출→문장분해→원장→독립군 계산, 도구 3개(`get_page`, `search_in_page`, `get_quote`) | 골든셋 20 URL(동일 보도자료 전재본 5 + PDF 3 + SPA 2 + 한↔영 번역쌍 1). ① **전재본 5개가 독립군 1개로 접히는가**(핵심) ② 임의 200개 `(doc_id,i)` 왕복이 **바이트 동일** ③ `get_quote` 에 없는 인덱스 → `ok:false` ④ **dev qwen2.5-7b 로 `get_page`×3 + `search_in_page`×5 실행 시 `maximum context length` 400 미발생**(나면 계약이 틀린 것이므로 여기서 멈춘다) | 3d | P2 |
| **P4** | 1층 공공 API + egress 래퍼·감사 | `_egress()` 단일 래퍼, 3상태 어댑터, `egress.jsonl`, 도구 2개(`search_scholar`, `list_egress_log`) | ① **DDG CAPTCHA 응답(HTTP 202, "Select all squares…")을 픽스처로 먹여 `status:"blocked"` 로 분류**되는가 — `empty` 로 나오면 실패 ② `egress.jsonl` 라인 수 == **독립 관측된 네트워크 요청 수**(호스트 커넥션 카운트로 대조. 자기 신고만 믿지 않는다) ③ arXiv 3초/1회·PubMed 3rps 준수 ④ 카나리 토큰(`ZZQX-CANARY-7731`)을 질문에 심고 전 경로 실행 → 페이로드·로그·프롬프트 어디에도 없음 | 2.5d | P3 |
| **P5** | 캐시·레이트리밋·서킷·`SEARCH_MODE` | SQLite 캐시(WAL), 토큰버킷 3중, 서킷브레이커, 3단 모드 스위치 | 전부 **고장을 인위로 만들어** 본다. ① 동일 질의 2회 → egress 라인 1건 ② `/etc/hosts` 로 `export.arxiv.org`→`127.0.0.1` → `ok:true, status:"blocked"` 로 반환하고 **심의가 계속 진행** ③ 5회 실패 후 6회차는 소켓을 안 염(`ss -tn` 실측) ④ `SEARCH_DAILY_QUOTA=3` 으로 4회차 차단 ⑤ `SEARCH_MODE=offline` → 외부 소켓 0건인데 캐시 질의는 정상 응답 | 2d | P4 |
| **P6** | 심의 통합 + 인용 강제 | 웹 경로에서 `DELIB_CHAIR_CITE=1`, `DELIB_REBUT_QUOTE=1` 강제. 의장 인용 `[W:doc_id#i]` ↔ `get_quote` 대조기 | 심의 10건 실행. ① **날조 인용률 0%**(구조상 보장 — 0이 아니면 배선 버그) ② 존재하지 않는 quote 인위 주입 시 거부 ③ 근거 0 심의에서 `[가설 단계]`·`[무근거]` 태깅 ④ RA 보고서 부록에 **`queries_sent` 전문**이 실림 | 2d | P5 |
| **P7** | 🔒 **2층 Brave + 차단 게이트** | `search_web`, deny-list 로더, 시크릿 주입 경로 구현 | ① deny-list 매치 질의 → 반환은 `status:"blocked"`, **`ss`/`tcpdump` 로 외부 소켓 실제 0건**(로그만 보지 않는다) ② redaction 골든셋 — 민감 400문장 차단율 100% / 정상 400문장 오탐 ≤10% ③ 키 없이 기동 시 크래시가 아니라 `domain_only` 자동 강등 ④ `git grep -iE "brave\|api_key\|X-Subscription"` 로 레포·매니페스트·cluster.yaml 에 키 0건 | 2d | **P1 승인 + §5-① 결정 + Brave 키** |
| **P8** | 배포 파이프라인 편입 | `build-all-to-drive.sh:23` `WANT` / `deploy-all-from-drive.sh:90` 반영, 신규 `check-search.sh`, `update-all.sh` 훅 3곳, **`var/sifs` 스테이징 완전성 검사** | ① dev build → Drive → cae00 deploy → `check-search.sh` 통과 ② 일부러 `var/sifs/web_research_mcp.sif` 를 지우고 검사 → **경고가 뜨는가**(안 뜨면 검사가 무용지물) ③ 앱을 죽인 상태로 `update-all.sh` 완주 → **`exit 0` 이면서 경고 출력**(비치명) | 1.5d | P6 |
| **P9** | 평가 하네스 + 성적표 | 40문항 벤치(공개기술 20 + 사내도메인 20), 자동지표 + 사람평가 15문항 | **웹 없는 베이스라인과 나란히 공표한다.** 인용 유효율·독립군 수·발행일 정확도 자동 집계. 사람 평가에서 유의한 개선이 없으면 **그 사실을 그대로 쓴다** | 1.5d | P6, 도메인 전문가 0.5일 |
| **P+** | (조건부) JS 렌더 | playwright SIF 훅 | P6~P9 운영 중 `render_required:true` 발생률을 계량한 뒤에만 착수. **데이터 없이 chromium 을 굽지 않는다** | — | 발생률 데이터 |

---

## 3. 아키텍처 결정과 근거

### A. 배치 — 새 MCP 앱 1개 `web-research-mcp`

| 결정 | 한 줄 근거 |
|---|---|
| HEAXHub 인티그레이션 앱으로 만든다 | 매니페스트 1파일 커밋으로 게이트웨이·챗·심의·`pinned_tools`·RA 저장이 전부 코드 수정 0으로 붙는다(현재 5앱 97도구가 이 경로다). |
| agent-server 내장을 버린다 | agent-server 는 원문 질문·대화이력을 메모리에 들고 있다 — 같은 프로세스에 외부 HTTP 를 두면 "원문이 안 나간다"는 보장이 **코드 리뷰의 성실성**에만 의존한다. 프로세스를 나누면 감사 대상이 "코드 전체"에서 "브로커 입력 한 지점"으로 줄고, 검색 라이브러리 hang 이 챗을 죽이지 않는다. |
| 별도 파이프라인을 버린다 | `deliberation.py` 가 이미 근거조달→라운드→의장합성을 하고, `[가설 단계]` 강제·출처 태깅·인용 실재검증이라는 **모델 정직성에 기대지 않는 구조적 자산**을 갖고 있다. 포크하면 이걸 다시 만들어야 한다. |
| 이름은 `web-research-mcp` / id `web_research_mcp` | 4개 안 중 3개가 이 이름이고 `^[a-z][a-z0-9_]{2,63}$` 를 통과한다. "브로커" 성격은 이름이 아니라 `_egress()` 단일 함수 구조로 보장한다. |

### B. 검색 백엔드 — 3층 사다리, DDG 폐기

```
0층  로컬 캐시 · 사내 자산(RA 보고서·과거 심의)          유출 0     P2부터 상시
1층  공공 도메인 API (arxiv·openalex·crossref·pubmed·wikipedia)  유출 A-   P4
2층  Brave Search API                                     유출 B+    P7(승인 후)
✗    DDG HTML — 폐기. 픽스처로만 보존
✗    SearxNG — 폐기
✗    Tavily/Exa — 배제(조건부 재검토, §5-③)
```

| 결정 | 한 줄 근거 |
|---|---|
| **DDG 를 폴백에서도 제외한다** | 두 실측이 정면 충돌했다 — 문제 진술은 "200+실결과", quality 관점은 "**HTTP 202 + CAPTCHA 본문 + 결과 0건**". 충돌 자체가 결론이다. **2xx 로 오는 차단**은 순진한 코드가 "결과 없음"으로 읽는, 리서치에서 가장 위험한 실패이며, 여기에 약관 위반이 겹친다. |
| DDG CAPTCHA 응답 본문은 **회귀 테스트 픽스처로 보존한다** | DDG 에서 살릴 유일한 가치다. 3상태 어댑터 계약이 실제로 `blocked` 를 뽑아내는지 검증하는 유일한 실물 샘플이다. |
| 1층을 **선택이 아니라 기본 장착**으로 둔다 | 무인증·무료·약관 명시허용이라 **승인 없이 P4 에서 파이프라인 전체를 검증**할 수 있고, 초록 자체가 고품질 스니펫이라 7B 에도 그대로 먹으며, **벌크 스냅샷이 가능한 유일한 층이라 cae00 이 폐쇄망으로 판정나도 살아남는다.** |
| 일반 웹은 Brave 1개 | 자체 인덱스라 Google 로그에 사내 질의가 안 쌓이고, "Data for AI" 플랜이 LLM 투입을 명시 허용하며, 단일 호스트라 allowlist·MITM 프록시 뒤에서 다루기 쉽다. |
| SearxNG 를 버린다 | 자체 인덱스가 없어 질의는 그대로 외부로 나간다. 스크래핑 엔진을 끄면 남는 건 Brave+공공 API 인데 그건 우리가 직접 하는 것과 같고, 프록시 일원화라는 유일한 이점은 `_egress()` 래퍼로 이미 얻는다. |
| **비용으로 벤더를 고르지 않는다** | 월 9천 질의 기준 Brave/Google/Tavily 전부 $45~$75 구간이다. 100달러 미만 차이로 아키텍처를 정하지 않는다 — 약관과 egress 로만 고른다. |

### C. 리서치 루프의 위치 — 앱 내부

| 결정 | 한 줄 근거 |
|---|---|
| 계획→검색→수집→추출→랭킹을 **도구 호출 1회 안에서** 코드가 돈다 | **실측 재확인**: `deliberation.py:185` 가 `tool_budget = max(1, min(6, ...))` 로 하드 클램프하고 기본값은 3(`:138`), 자유조회는 ReAct 1턴이다. 웹 리서치의 재질의는 5~15턴이 정상이므로 심의 예산 안에 넣으면 **첫 검색 결과만 보고 끝난다.** |
| 동시에 `queries: list[str]`(1~4개) 인자도 유지한다 | 호출 모델이 좋은 팬아웃을 주면 쓰고, 못 주면 서버가 규칙 기반 변형으로 메운다. 두 방식은 배타적이지 않다. |
| **심의 예산 구조는 건드리지 않는다** | 공유 자산이고, 도구 1회로 접으면 건드릴 이유가 없다. |

### D. 본문 미반환 계약 — 이 설계의 심장

| 결정 | 한 줄 근거 |
|---|---|
| `get_page` 는 **기본 `max_sentences=0`** — 본문 대신 `doc_id`+개요+메타만 준다 | ① 위키 1페이지 원본이 1,144,367자(실측)다. 전량 반환은 dev 16K 에서 첫 호출에 죽고 GLM 에서도 10페이지를 못 넘는다(같은 사고가 `app.py:274,482,596` 에 3번 기록됨). ② 인용이 `doc_id+문장인덱스`가 되어 **`DELIB_REBUT_QUOTE` 방식의 코드 검증이 성립한다.** ③ 외부 콘텐츠가 프롬프트에 원문으로 들어가는 양이 줄어 **프롬프트 인젝션 표면이 좁아진다.** |
| 본문은 `$HEAX_DATA_DIR/` 아래에만 남긴다 | **실측 재확인**: SIF rootfs 는 read-only, bind 는 `/workspace`·`/data`(=`var/app_data/<id>`) **2개뿐**(`integration_launcher.py:503-505`). 여기가 유일한 쓰기 경로다. |
| **raw HTML 은 저장하지 않는다.** 추출 text+문장 30일, 원장 메타+egress 로그 1년 | dev 박스는 이미 OOM 이력과 스왑 40G 조치가 있는 기계다. 인용 검증에 필요한 건 문장이지 raw HTML 이 아니다. 대가는 재추출 불가다(§7). |

### E. 독립 출처군 — 모델 능력이 0으로 필요한 최고 레버리지

| 결정 | 한 줄 근거 |
|---|---|
| URL 정규화 → eTLD+1 그룹핑 → SimHash → 임베딩(코사인 ≥0.93) → 연속 3문장 동일 → 퍼블리셔 표. **교차검증 수치는 항상 문서 수가 아니라 독립군 수로 보고한다** | 이게 없으면 같은 보도자료 8부가 "8개 출처 일치"가 되는데, **사용자 눈에는 신뢰도가 오히려 올라가 보인다.** 전부 결정적 코드라 dev/prod 모델 차이와 무관하다. |
| 임베딩은 CPU 로 돈다 | multilingual-e5-base 가 이미 로컬(`~/.cache/huggingface`, 1.1G)에 있고 **CPU 240문장 0.98초 = 4.1ms/문장** 실측이다. 12문서 500문장 ≈ 2.1초. GPU 불필요. |
| **함의 판정은 하지 않는다.** 상충 출처는 병기만 하고 합치지 않는다 | "숫자는 같은데 정의가 다르다"(공칭 두께 vs 실측 두께)를 가르는 건 능력이지 프롬프트가 아니다. 7B 불가, GLM 도 신뢰하지 않는다. **틀리게 합치는 것보다 안 합치는 게 낫다** — 다만 이건 트레이드오프이지 정답이 아니다(§7). |

### F. 3상태 계약 — `blocked` 와 `empty` 를 절대 합치지 않는다

| 결정 | 한 줄 근거 |
|---|---|
| 모든 검색 도구는 `ok:true` 로 반환하되 **`status: "ok" \| "blocked" \| "degraded" \| "empty"`** 를 필수 필드로 싣는다 | 도구가 예외를 던지면 그 라운드의 근거 조달이 통째로 날아가고 의장은 이유도 모른 채 합성한다. `ok:true` 로 반환하면 `ev_count["tool"]==0` 경로가 살아나 `[가설 단계]` 가 강제된다. **동시에** `blocked`(차단·CAPTCHA·서킷개방)를 `empty`(정말 없음)와 합치면 차단이 "그런 사실 없음"으로 둔갑한다 — 이게 DDG 사고의 교훈이다. |
| `status != "ok"` 면 `warnings` 에 끌 수 없는 문구를 싣는다 | 모델이 `warnings` 를 읽는다는 보장은 없지만, 안 싣는 것보다는 낫다(§7 에 한계로 남김). |

### G. 도구 명명 — 여기서 틀리면 챗에서만 되고 심의에서 조용히 죽는다

| 결정 | 한 줄 근거 |
|---|---|
| 전 도구명을 `_FREE_ALLOW` 접두사에 맞춘다 | **실측 재확인**(`deliberation.py:630-646`): deny-by-default 접두사 화이트리스트다. `fetch_page`·`browse_url`·`read_url`·`crawl_site`·`extract_text`·`summarize_page`·**`scholar_search` 는 전부 차단**된다(조사안 §10 의 `scholar_search` 제안은 규칙 위반 — `search_scholar` 로 정정). |
| 게이트웨이 **최종 노출명**을 등록 직후 반드시 재확인한다 | 이름이 충돌하면 게이트웨이가 `<앱키>_<도구명>` 프리픽스를 붙이고(`gateway.py:148-156`), 그 순간 `heax_web_research_mcp_get_page` 가 되어 **어떤 허용 접두사로도 시작하지 않아 자유조회에서 사라진다.** CI 에서 라이브 `/tools-map` 유일성 + `_free_tool_ok()` 통과를 둘 다 단언한다. |
| 도구는 8개로 고정한다 | `TOOL_MAX=80` 캡(실측 `app.py:661`)이 있고 현재 게이트웨이 도구가 225개다. 초기에는 `pinned_apps` 로 검증하고 자동 선택 의존은 나중에 확인한다. |

### H. egress 통제 — 브로커가 유일한 출구

| 결정 | 한 줄 근거 |
|---|---|
| 모든 외부 호출이 `_egress()` 함수 하나를 통과한다 | 백엔드별 SDK 가 각자 소켓을 열면 cae00 프록시·사내 CA 환경에서 반드시 터지고 감사로그에 구멍이 난다. |
| **`verify=False` 는 코드에 존재해서는 안 된다** | MITM 방어를 스스로 끄는 짓이고 한번 들어가면 영구히 남는다. 프록시를 못 뚫는 건 `SEARCH_MODE=offline` 으로 답할 문제다. |
| 앱이 자체 `egress.jsonl` 을 갖는다(게이트웨이 로그로 대체 불가) | **실측 재확인**(`gateway.py:71-84`): `_audit()` 이 남기는 필드는 `{ts,tool,backend,ok,ms,caller,error}` 뿐 — **도구 인자가 없다.** 기존 감사만으로는 "무엇을 검색했는가"에 답할 수 없다. 게이트웨이 로그는 호출량 상관검증용으로만 쓴다. |
| **원문 재작성은 앱 밖(호출 모델)에서 한다.** 앱은 `queries: list[str]`(각 400자·최대 4개) 만 받는다 | 앱에 LLM 재작성을 넣으면 앱이 원문을 받게 되어 "원문을 받는 인자가 존재하지 않는다"는 타입 수준 방어가 깨진다. 대신 dev 7B 의 재작성 품질이 검색 품질 상한이 된다 — **§5-④ 결정 사항으로 올린다.** |

### I. 의도적으로 하지 않는 것

| 항목 | 근거 |
|---|---|
| JS 렌더(playwright/chromium) | chromium ~500MB 로 Drive 왕복이 배포마다 늘고, 브라우저 fetch 는 **그 페이지의 서드파티 트래커까지 사내 IP 로 전부 로드**해 curl 보다 유출 표면이 훨씬 넓으며, headless chromium 은 OOM·좀비 단골인데 dev 는 이미 OOM 이력이 있다. `render_required:true` 로 **사각지대를 계량**한 뒤에만 착수한다. |
| PDF 표 추출 | 실질 미해결 영역이다. 텍스트만 뽑고 표는 원문 링크로 넘긴다 — 행/열이 어긋나 **조용히 틀린 숫자를 인용**하는 게 최악이다. |
| 크롤링·링크 추종 | 주어진 URL 1개만 받는다. |
| 로그인·페이월 우회 | 능력이 아니라 정책 문제다. |
| 특허 DB(EPO/KIPRIS) | 질의 문자열 자체가 경쟁 인텔리전스 신호다. **이번 승인 요청에 섞지 않는다**(섞으면 전체가 늦어진다). |
| 리랭커 모델 | P9 nDCG 측정에서 BM25+임베딩 대비 +0.10 이 안 나오면 안 붙인다. SIF 568MB 를 아낀다. |

### J. 관점 간 사실 충돌 — 이번에 정정한 3건

| 충돌 | 판정 | 근거 |
|---|---|---|
| DDG 가 200+결과인가, 202+CAPTCHA 인가 | **불안정하다는 것이 합의.** 2xx 차단 실패모드가 실재하므로 폴백 자격 없음 | 두 실측이 같은 날 다른 결과 |
| 게이트웨이 도구 225개인가 241개인가 | **225개.** 보안 관점의 241 은 오기 | 이번 재측정 — `/tools-map` 의 `map` 키 225개 |
| `fetch_rerank_model` 이 리랭커 자산인가 | **아니다.** 소속 백엔드는 `ai-data-hub` 이고 `mcp_upload_svc.py` 의 도구 allowlist 항목이다. 범용 웹 문서 리랭커로 전용 불가 | 이번 재측정 |

**추가 재확인(전부 참으로 확정).** binds 2개 + `cleanenv=True`(`:546,576`), `_inherited_env()` 는 `HEAX_APP_LLM_*` 4개 고정 allowlist(`:641-659`), `/data/hwax` 디렉터리 **dev 에 없음**, `check-egress.sh` **존재·실행가능**(8/8 13:48), `TOOL_RESULT_MAX=120000`·`TOOL_MAX=80`, `_REBUT_QUOTE`/`_CHAIR_CITE` **둘 다 기본 0**, 제안 도구명 8개 전부 **기존 225개와 충돌 0**.

---

## 4. 도구 계약 (8개)

공통 envelope 는 기존 규약을 따른다 — `{ok, data, errors, warnings, server}`, `errors[].suggestion` 은 LLM 자가복구용이라 필수다. **모든 검색·수집 도구의 `data` 에는 `status` 와 `egress` 블록이 항상 존재한다.**

```jsonc
"egress": {
  "occurred": true,
  "egress_id": "eg_20260808_...",
  "destination": "api.search.brave.com",
  "queries_sent": ["lithium-ion pouch cell swelling mechanism"],  // ★ 실제로 나간 문자열 전문
  "mode": "full",            // full | domain_only | offline
  "caller": "<PAT sub>",
  "ts": "2026-08-08T14:02:11Z"
}
```

`queries_sent` 가 UI 고지·심의 보고서 부록·`egress.jsonl` 레코드의 **단일 소스**다. 세 곳이 1:1 대응하지 않으면 배선 버그다.

### 1) `search_internal` — 0층. egress 0. 항상 먼저

```
search_internal(query: str,
                sources: ["reports","deliberations","cache"] = 전체,
                max_results: int = 10)
→ { status, results: [{doc_id, title, source, date, snippet}] }
```
사내 자산에서 먼저 답이 나오면 외부로 나갈 이유가 없다. **이 도구만 원문 `query` 를 받는다** — 외부로 나가지 않기 때문이다.

### 2) `search_web` — 2층. 승인 후 활성

```
search_web(queries: list[str],          # 1~4개, 각 400자 이하. 재작성 결과만
           max_results: int = 8,
           freshness: "d"|"w"|"m"|"y"|null = null,
           lang: "ko"|"en"|"auto" = "auto",
           purpose: str,                # 감사 필수. 없으면 거부
           ack_egress: bool = false)
→ { status: "ok"|"blocked"|"degraded"|"empty",
    backend_used, degraded_reason, cache: "hit"|"miss"|"partial",
    independent_groups: int,            # ★ 문서 수가 아니다
    results: [{rank, title, url, domain, registrable_domain,
               domain_tier: "primary"|"secondary"|"vendor"|"blog"|"unknown",
               published_at, date_source: "meta"|"jsonld"|"url"|"unknown",
               snippet(≤400자), independence_group: int, dup_of: int|null,
               doc_id: null}],
    egress: {...} }
```
- **원문 질문을 받는 인자가 없다.** 400자 초과·5개 이상은 원문 유출 시도로 간주하고 거부한다.
- `ack_egress:false` → 외부로 나가지 않고 0층 결과 + `requires_ack:true` 반환. 세션 최초 1회 동의, 동의 이력은 감사로그에 남는다.
- `purpose` 없으면 거부. 감사자가 "왜 나갔는가"를 물을 때 답이 있어야 한다.
- `caller` 가 비면 0층으로 강등. 책임 소재 없는 egress 는 만들지 않는다.

### 3) `search_scholar` — 1층. 승인 없이 P4 부터 동작

```
search_scholar(queries: list[str],
               source: "auto"|"arxiv"|"openalex"|"crossref"|"pubmed" = "auto",
               max_results: int = 10, year_from: int|null = null, purpose: str)
→ search_web 과 동일 스키마 + {authors[], doi, venue, cited_by, abstract}
```
초록이 곧 고품질 스니펫이라 7B 에도 그대로 먹인다.

### 4) `get_page` — 본문을 반환하지 않는 것이 요점

```
get_page(url: str, max_sentences: int = 0, mode: "static"|"auto" = "static", purpose: str)
→ { status, doc_id, url_canonical, title, published_at, date_source, author,
    domain, registrable_domain, domain_tier, lang, content_type,
    fetched_at, cache, n_sentences, n_chars,
    outline: [str],                    # h1~h3
    sentences: [],                     # max_sentences=0 이면 빈 배열
    render_required: bool,             # 본문 <400자 → JS 렌더 필요 추정
    truncated: bool, egress: {...} }
```
응답 8KB 캡. **기본 `max_sentences=0` 을 바꾸지 마라** — 이 값이 dev 16K 생존과 인용 코드검증의 전제다.

### 5) `search_in_page` — 30페이지를 컨텍스트 없이 읽는 방법

```
search_in_page(doc_id: str, query: str, top_k: int = 5)
→ { hits: [{i: int, text: str, score: float}] }
```
서버가 BM25(+임베딩)로 고른다. 모델은 필요한 문장만 본다.

### 6) `get_quote` — 인용 검증의 유일한 진실 원천

```
get_quote(doc_id: str, i: int, span: int = 1)
→ { doc_id, i, text, char_offset, url, title, published_at, sha256 }
```
저장된 문장을 **바이트 그대로** 반환한다. 없는 인덱스면 `ok:false`. 의장 결정문의 `[W:doc_id#i]` 태그를 코드가 이걸로 대조한다. **날조 인용은 구조적으로 0이 된다. 잘못된 문장을 고르는 것은 못 막는다** — 이 구분을 출력에도 명시한다.

### 7) `describe_search_status` — 운영 관측

```
describe_search_status()
→ { mode, search_backend, deny_rules_version, allowed_hosts: [str],
    backends: [{name, circuit: "closed"|"open"|"half_open", quota_used, quota_limit,
                last_error, p50_ms}],
    cache: {entries, bytes, hit_rate_24h},
    egress_24h: {queries, unique_hosts, blocked, degraded} }
```
`describe_` 접두사라 심의에서도 호출 가능하다. 운영자가 챗에서 "검색 상태"만 물어도 나온다.

### 8) `list_egress_log` — 감사 제출물

```
list_egress_log(since: str = "24h", limit: int = 200, caller: str|null = null)
→ { entries: [{ts, caller, backend, queries_sent, purpose, blocked_rule,
                n_results, ms, egress_id}], truncated: bool }
```
- **차단된 질의는 원문을 저장하지 않는다** — `sha256` + 룰 ID 만 남긴다. 감사로그 자체가 유출 경로가 되면 안 된다.
- 반환에 매치된 사내 문자열은 싣지 않는다. `blocked_rule` 은 룰 이름만이다.
- 기본은 호출자 본인 것, 감사 그룹은 전체.

### egress 게이트 순서 (모든 도구 공통, `app/egress.py` 단일 경로)

1. `caller`/`purpose` 검증 → 없으면 거부.
2. deny-list 정규식 매치 → 즉시 `status:"blocked"`. `suggestion` 은 "사내 고유명사를 제거한 일반화 검색어로 다시 호출하거나 `search_internal` 로 답하라".
3. 목적지 호스트 allowlist 검사.
4. `get_page` 는 DNS 해소 후 RFC1918·loopback·사내 도메인 차단(SSRF + 역방향 유출 동시 방어).
5. 레이트리밋 토큰버킷 → 서킷브레이커 상태 확인.
6. `HTTPS_PROXY`/`SSL_CERT_FILE` 존중, 타임아웃 강제(connect 5s / read 15s / total 20s).
7. 성공·실패 무관하게 `egress.jsonl` 기록.
8. 반환 전 `sentences[].text` 의 지시문 패턴(`ignore previous`, `system:`, 도구호출 유사 문자열)을 무력화한다. **웹 검색은 이 시스템에 신뢰할 수 없는 텍스트가 들어오는 첫 경로다.**

**deny-list 룰 파일은 레포에 두지 않는다** — 프로젝트 코드명·고객사명 목록 자체가 기밀이다. `/data/hwax/secrets/search-denylist.txt` 에만 둔다.

---

## 5. 사용자가 결정해야 할 것

> 보안 관점이 "하면 안 된다"고 한 항목은 아래에 그대로 남겼다. 다른 관점의 속도 논리로 덮지 않았다.

### ① 시크릿 주입 경로 — **P7 의 하드 블로커. 지금 결정해야 한다**

실측으로 확인된 문제다. 인티그레이션 앱 컨테이너에 API 키를 넣을 수 있는 **기존 경로가 하나도 없다.** binds 는 `/workspace`·`/data` 2개뿐이고, `cleanenv=True` 이며, `_inherited_env()` 는 `HEAX_APP_LLM_*` 4개 고정 allowlist 다. `launch.env` 는 매니페스트에 있고 매니페스트는 레포에 커밋된다.

| 선택지 | 트레이드오프 |
|---|---|
| **A. `integration_launcher.py` 에 조건부 read-only bind 3줄 추가** (`/data/hwax/secrets` → `/secrets:ro`) — **권고** | 확립된 보안 규칙을 그대로 지키고, 다른 앱도 재사용하며, read-only 라 앱이 시크릿을 수정 못 한다. 대가는 **HEAXHub 공유 인프라 변경 승인**이 필요하다는 것. |
| B. `HEAX_APP_SECRET_*` prefix allowlist 추가 | 변경량이 비슷하고 bind 보다 노출이 좁지만, 시크릿이 프로세스 환경변수로 들어가 `/proc/<pid>/environ` 에 남는다. |
| C. 시크릿을 `var/app_data/web_research_mcp/search.env` 로 **복사** (HEAXHub 무수정) | 착수는 가장 빠르지만 **시크릿 사본이 0700 디렉터리 밖으로 나간다** — 확립된 규칙과 정면 충돌하고, 권한·로테이션·백업 유출 부담이 영구히 남는다. |

**Phase 0~6 은 키가 필요 없으므로 이 결정이 착수를 막지는 않는다.** 다만 P7 전까지 결론이 나야 한다.

### ② 사내 질의의 외부 송출 — **이 계획 전체에서 가장 무거운 결정**

이 조직은 삼성 MX 사내망이고, 사내 질문 텍스트를 외부 검색 API 로 보내는 것은 **데이터 유출 사건이 될 수 있다.**

| 선택지 | 얻는 것 | 잃는 것 |
|---|---|---|
| **가. 0·1층만 운영** (공공 학술 API + 사내 자산) | 승인 리스크 최소, 약관 명시허용, 폐쇄망에서도 벌크 스냅샷으로 생존 | **일반 웹 검색이 없다.** 사용자 기대("구글처럼 찾아서 읽어주는 것")와 정면으로 어긋난다 |
| 나. 2층까지 (Brave, 재작성+deny-list+감사) | 실용적 커버리지 확보 | 재작성해도 **IP 대역은 못 가린다** — "이 조직이 지금 이 주제를 파고 있다"는 신호는 남는다. deny-list 는 원리적으로 불완전하고, "적층형 셀 덴트 거동"처럼 **개별 단어는 전부 일반명사인데 조합이 곧 기밀**인 질의는 통과한다 |
| 다. 전면 도입(원문 그대로 송출) | 검색 품질 최대 | **권고하지 않는다.** 가장 좋은 쿼리는 대개 원문이지만, 그 대가가 유출 사건이다 |

승인 대화에 들고 갈 물건은 딱 하나다 — **나간 문자열 전체를 언제든 제시할 수 있다는 것.** 이걸 못 보여주면 어떤 벤더를 골라도 진다. 그리고 **정규식 deny-list 가 뚫린다는 사실을 승인 대화에서 먼저 자백해야 한다.** 진짜 방어선은 정규식이 아니라 감사로그와 사람의 사후 검토다. 감추면 나중에 더 크게 터진다.

### ③ Tavily/Exa 를 정말 배제할 것인가

보안 관점은 DPA 없이 금지(N6)로 못 박았다. 합성 판정도 배제 유지다 — **이들의 핵심 가치가 "질의와 결과를 자체 LLM 으로 가공"하는 것이라, 사내 질문 텍스트가 제3자 모델의 입력이 된다.** 다만 정직하게 말하면 이들이 **합성 편의성 1위**이고 7B 에게 가장 친절하다. **품질이 좋아서 더 위험하다** — 편해서 손이 가고, 손이 갈수록 민감한 원문을 그대로 던지게 된다. 사내 DPA 를 확보할 수 있다면 재검토 사유가 된다.

### ④ 질의 재작성을 앱 안에 넣을 것인가

현재 판정은 "앱 밖(호출 모델)". 근거는 보안 N2 의 타입 수준 방어다. 그러나 **dev 의 qwen2.5-7b 는 좋은 질의 변형 4개를 못 만든다** — 즉 dev 데모의 검색 품질 상한이 백엔드가 아니라 질의 생성에서 결정될 가능성이 높다. `_inherited_env()` 가 `LLM_BASE_URL`/`LLM_MODEL` 을 앱에 물려주므로 서버측 재작성은 **새 인프라 없이 가능**하다. 넣으면 품질이 오르고 원문이 앱에 들어온다. 사용자 결정 사항이다.

### ⑤ 범위 — 어디까지가 "이번"인가

| 선택지 | 트레이드오프 |
|---|---|
| **가. 위 P0~P9** (권고) | 17 개발일 + 승인 대기. 인용이 코드로 검증되고 나간 문자열을 전량 제시할 수 있다 |
| 나. 얕게 2주 (mvp 안) | 빠르지만 **2주 뒤에 인상적인 데모와 함께 "그런데 아직 못 쓰십니다"를 내놓을 위험**이 있고, 재질의 루프·독립군 계산·평가 하네스가 전부 빠진다 |
| 다. JS 렌더+PDF 를 v1 에 포함 | +1주. **이 조직 도메인(CAE·재료·규격)의 1차 자료가 거의 PDF 이고 요즘 기술 문서 상당수가 SPA** 라는 점에서 이 주장은 타당하다. 대가는 chromium 500MB·유출 표면 확대·OOM 리스크다 |

---

## 6. 착수 전 확인 목록

전부 명령으로 확인 가능한 형태다. **①은 크리티컬 패스이고, 나머지는 P2 착수와 병렬로 진행 가능하다.**

**① cae00 egress 실사 — 최우선. 이것 없이 P7 착수 금지**
```bash
# cae00 에서 (스크립트는 이미 존재·커밋됨)
bash /home/koopark/claude/HWAXPortal/infra/scripts/check-egress.sh --json > /tmp/egress-cae00.json
bash /home/koopark/claude/HWAXPortal/infra/scripts/check-egress.sh --sif <임의 fastapi SIF>
# 판정: issuer 에 사내 CA → MITM / 전부 000·타임아웃 → 폐쇄망 / 공개 CA+200 → dev 동일
# --sif 결과가 호스트와 다르면 컨테이너 CA 번들 문제 — P4 에서 반드시 잡는다
```

**② 시크릿 디렉터리 부재 확인 (현재 dev 에 없음)**
```bash
ls -ld /data/hwax /data/hwax/secrets   # → No such file or directory
# §5-① 결정 후 0700 으로 생성
```

**③ 도구 이름 충돌·화이트리스트 통과 (P2 등록 직후 필수)**
```bash
curl -s :9110/tools-map | python3 -c "
import sys,json; m=json.load(sys.stdin)['map']
cand=['search_web','search_scholar','search_internal','get_page','search_in_page',
      'get_quote','describe_search_status','list_egress_log']
print('총 도구:',len(m)); print('충돌:',[(n,m[n]) for n in cand if n in m])
print('최종 노출명:',[k for k,v in m.items() if v=='heax-web_research_mcp'])"
cd /home/koopark/claude/HWAXAgentServer && python3 -c "
from deliberation import _free_tool_ok
for n in ['search_web','search_scholar','search_internal','get_page','search_in_page',
          'get_quote','describe_search_status','list_egress_log']:
    print(n, _free_tool_ok(n))"   # 전부 True 여야 한다
```

**④ 심의 인용·출처 플래그 현재값 (둘 다 0 — 웹 경로에서 1 강제 필요)**
```bash
grep -n "DELIB_REBUT_QUOTE\|DELIB_CHAIR_CITE" /home/koopark/claude/HWAXAgentServer/deliberation.py
env | grep -E "DELIB_(REBUT_QUOTE|CHAIR_CITE)"    # 비어 있으면 기본 0
```

**⑤ 컨텍스트 캡과 실제 GLM 윈도우의 적합성 — 미확인**
```bash
grep -n "TOOL_RESULT_MAX\s*=\|TOOL_MAX\s*=" /home/koopark/claude/HWAXAgentServer/app.py
# TOOL_RESULT_MAX=120000(≈35K 토큰) 이 운영 GLM 윈도우 안에 들어가는지 별도 확인 필요
```

**⑥ 매니페스트 함정 체크리스트 (전부 조용히 실패한다)**
```bash
python3 - <<'PY'
import yaml,sys
m=yaml.safe_load(open('/home/koopark/claude/HEAXHub/integrations/web-research-mcp/.portal/manifest.yaml'))
b,l=m.get('build',{}),m.get('launch',{})
chk=[('build.stack',b.get('stack')=='fastapi'),      # 없으면 앱이 통째로 skip
     ('build.type',b.get('type')=='python_venv'),
     ('build.python_version',b.get('python_version')=='3.12'),
     ('launch.health_check',bool(l.get('health_check'))),   # top-level 이면 조용히 무시
     ('launch.restart_policy',bool(l.get('restart_policy'))),
     ('max_attempts 키',('max_attempts' in str(l.get('restart_policy')))),  # max_retries 는 안 읽힘
     ('mcp.expose',(m.get('mcp') or {}).get('expose') is True),
     ('mcp.description',bool((m.get('mcp') or {}).get('description')))]
for k,v in chk: print(('OK ' if v else 'FAIL '),k)
sys.exit(0 if all(v for _,v in chk) else 1)
PY
grep -n "mcp>=1.10,<2" <upstream>/pyproject.toml   # 상한 없으면 hermetic SIF 에서 mcp 2.0 이 깔려 크래시
```

**⑦ 배포 누락 방지 — `var/sifs` 글롭 무언 탈락 (기록된 실측 함정)**
```bash
sed -n '85,92p' /home/koopark/claude/HWAXPortal/docs/cluster-deploy/checklist.md
grep -n "^WANT=" /home/koopark/claude/HWAXPortal/infra/scripts/build-all-to-drive.sh
grep -n "web_research\|WANT" /home/koopark/claude/HWAXPortal/infra/scripts/deploy-all-from-drive.sh | head
```

**⑧ 승인·조달 (코드 아님, 리드타임이 가장 길다)**
- 정보보호 서면 승인 — 제출물은 §1-A 금지선 표, `egress.jsonl` 스키마 샘플, redaction 골든셋 결과, 고지 UI 캡처.
- 법무 — Brave 약관의 **결과 저장기간 제한**(캐시 TTL 상한이 여기서 정해진다)과 AI 투입 허용 범위. **2026 단가는 지식 컷오프 이후 변동 가능하므로 반드시 재확인.**
- 사내 **Azure MSA/DPA 존재 여부** — 있으면 백엔드 선택 재검토 사유다.
- 네트워크 — cae00 아웃바운드 호스트 allowlist(`api.search.brave.com`, `export.arxiv.org`, `api.openalex.org`, `api.crossref.org`, `eutils.ncbi.nlm.nih.gov`, `*.wikipedia.org`). 와일드카드 개방은 요청하지 않는다.
- **정직한 User-Agent 문자열과 연락처 메일** — 실측상 크롬 위장은 위키피디아 403, 설명형 UA 는 200 이다. 위장은 비윤리적일 뿐 아니라 **덜 작동한다.**
- OpenAlex/Crossref polite pool 용 **부서 대표 메일 별칭**(개인 메일 금지), PubMed 무료 키.
- **Brave 키는 P0 결과 전에 구매하지 마라** — 폐쇄망으로 판정나면 예산 자체가 불필요하다.

**⑨ 사람**
- cae00 접근 권한자 30분(P0), 보안 검토 담당 1회+파일럿 검토 1회, 개발 1인(P2~P9 약 3.5주), **도메인 전문가 0.5일**(P9 벤치 40문항·관련성 라벨 — 이게 없으면 검증 기준이 전부 "좋아진 것 같다"로 끝난다).

---

## 7. 이 계획으로도 클로드에 못 미치는 부분

### 7-1. 모델 한계 — 계획을 어떻게 짜도 안 없어진다

| 항목 | 왜 못 넘는가 | 이 계획이 하는 것 |
|---|---|---|
| **컨텍스트 예산** | 진짜 웹 리서치는 10~30페이지를 읽는다. 위키 1페이지 원본이 1.14MB(실측), 추출 본문도 3,687자 ≈ 2K 토큰이다. dev 16K 는 3~5페이지에서 죽고, GLM 도 `TOOL_RESULT_MAX=120000`(≈35K 토큰) 기준 10페이지 수준이다 | 본문 미반환 + 문장 ID. **우회이지 해결이 아니다** |
| **함의 판정 (교차검증)** | "두 문장이 같은 주장인가"는 정의·단위·조건 차이를 다 봐야 한다. 7B 불가, **GLM 도 기대하지 않는다** | 독립성만 코드로 판정하고 **상충 출처를 병기만 한다.** 사용자가 원하는 "그래서 뭐가 맞는데"에 답하지 않는다 |
| **문장 선택 정확도 (인용)** | 어느 문장이 이 주장을 지지하는지 고르는 것은 attribution 능력이다 | **날조는 100% 막는다. 잘못된 문장을 고르는 것은 못 막는다.** 이 격차를 출력에 명시하지 않으면 "코드로 검증된 인용"이라는 라벨이 곧 과신의 근거가 된다 |
| **캘리브레이션** | 모델이 자기 무지를 아는 능력. 7B 는 거의 없고 GLM 도 기대하면 안 된다 | 모델의 정직성에 기대지 않고 **구조로 대체한다** — 근거 카운트 게이트 + `[가설 단계]` + `[무근거]` 태깅. 이미 구현돼 있으니 웹 경로에서는 켜는 게 아니라 **끌 수 없게** 만든다 |
| **질의 생성 (재작성)** | dev 7B 는 좋은 팬아웃 변형 4개를 못 만든다 | 서버측 규칙 기반 변형이 폴백. 근본 해결은 §5-④ 결정에 달렸다 |

**그리고 dev 에서는 품질을 증명할 수 없다.** qwen2.5-7b 로 검증되는 건 파이프라인 형태뿐이고, 성적표는 GLM 에서만 의미가 있는데 그 박스의 egress 를 아직 모른다. 최악의 경우 이 설계는 **품질을 증명할 수 없는 환경에 배포된다.**

### 7-2. 데이터 접근 한계 — 투자하면 메울 수 있다

| 항목 | 격차 | 메우는 비용 |
|---|---|---|
| **JS 렌더 부재** | 요즘 API·제품 문서 상당수가 SPA 다. 정적 fetch 로는 빈 페이지가 오고, 모델은 "해당 내용 없음"이라 답한다. `render_required` 로 드러내지만 **드러내는 것과 읽는 것은 다르다** | playwright SIF(자산 존재) +1주, chromium 500MB, 유출 표면 확대 |
| **PDF 표 추출 부재** | **이 조직 도메인의 1차 자료가 거의 PDF 다.** 텍스트는 뽑아도 표는 못 뽑는다 | 실질 미해결 영역. 부분 실패를 선언하고 원문 링크로 넘기는 게 정직하다 |
| **재질의 루프 깊이** | 도구 호출 1회 안에서 1라운드를 돌지만, 클로드는 계획→수집→판단→**재계획**을 10~30페이지에 걸쳐 돈다. 사용자가 "찾아봤는데 없습니다"를 받았을 때 **정말 없어서인지 한 라운드로 끝나서인지 구분이 안 된다** | `research_id` 로 이어하기를 넣었지만, 모델이 스스로 "부족하다"를 판정해야 작동한다 |
| **페이월·로그인 콘텐츠** | 유료 표준·논문 본문에 접근 불가 | 능력이 아니라 **정책으로 안 한다.** 기관 구독 정식 API 가 있으면 별건으로 검토 |
| **특허 DB** | 이번 범위에서 제외 | 질의 자체가 경쟁 인텔리전스 신호다. IP 부서 별도 승인 |
| **일반 웹 자체** | P7 승인 전까지 학술 검색만 있다. 승인이 몇 달 걸리면 그 기간 내내 일반 웹이 없다 | **승인 리드타임.** 이게 이 로드맵의 가장 큰 도박이다 — 품질 관점에서 보면 실패한 순서다 |

### 7-3. 이 설계 자체가 감수하는 것

- **재작성 게이트가 검색 품질을 직접 깎는다.** 가장 좋은 쿼리는 대개 원문이다. 손실이 얼마인지는 파일럿 전에는 모르므로, **재현율 A/B 를 측정하지 않고 배포하면 안 된다.** 30% 이상 떨어지면 조용히 열화된 도구를 파는 대신 정책 논의로 되돌린다.
- **deny-list 는 보안 극장이 될 수 있다.** 게이트가 있다는 사실이 심리적 안전감을 주고, "게이트가 통과시켰으니 괜찮다"며 더 민감한 질문을 던지게 만들 수 있다. 이 계획은 그걸 방어하지 못한다.
- **단일 egress 앱은 SPOF 다.** 감사 관점의 장점이 가용성 관점의 단점이다. 이중화하면 감사 지점이 둘로 늘어 원래 목적이 약해진다 — 이 긴장은 해소하지 못했다.
- **`ok:true` 반환이 조용한 실패를 만들 수 있다.** `status` 필드와 `warnings` 가 완화책이지만 모델이 그걸 읽는다는 보장은 없다.
- **캐시 TTL 이 최신성과 정면 충돌한다.** 7일 페이지 캐시는 폐쇄망 생존에 좋지만 최신성 질문에 **오래된 답을 확신 있게** 준다.
- **도메인 티어표는 부패한다.** 영미권 중심이 되기 쉽고, 한국어 1차 자료(국가기술표준원·학회지)가 조직적으로 저평가되면 **가장 관련성 높은 출처를 시스템이 스스로 눌러버린다.** 유지보수 주체를 정하지 않으면 1년 뒤 거짓말을 한다.
- **가장 현실적인 실패 모드는 유출이 아니라 방치다.** `ack_egress` 동의·`purpose` 필수·0층 우선·차단 시 강등 — 사용자 입장에서는 "검색이 잘 안 되는 도구"다. 안 쓰이는 도구는 개인 PC 검색 후 붙여넣기라는 통제 밖 우회를 낳고, 그건 막으려던 것보다 나쁘다.