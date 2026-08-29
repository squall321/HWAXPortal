<!-- 챗 워크스페이스 → 심의 핸드오프 설계 (강건판) — 실데이터로 정리 후 버튼식으로 심의로 넘기기 -->
# 챗 워크스페이스 → 심의 핸드오프 설계 (2026-08-28)

## 0. 문제·목적

cold-start 심의는 좌석·근거·프레이밍이 없어 **"상한 스크리닝"** 만 낸다(실측: 폴더블 sim 이 personas 비어 실패, 메커니즘 결정문이 "정량 근거 공란"을 명시). 목적 — 챗에서 **실데이터를 먼저 정리·디벨롭**한 뒤, Word 출력처럼 **버튼 하나로 현 상태를 심의로** 넘겨 퀄리티 있는 지점에서 심의를 시작한다. 기존 직행 심의는 그대로 둔다(보고서 통째 복사 기반 심의 등).

## 1. 설계 헌법 (이걸 어기면 "비싼 거수기"가 된다)

- **P1 — 브리프는 원천 데이터·출처를 싣되 결론을 싣지 않는다.** ⭐ AI가 데이터를 미리 씹어 요약을 "정본"으로 넘기면 좌석(rigor-review·validation)이 반박할 대상을 잃는다. 심의로 건너가는 것은 **원천 도구결과 + 출처**이지 판정이 아니다.
- **P2 — prep은 무대를 깔고, 심의가 판단한다.** prep은 결론을 내지 않는다. 심의의 부가가치는 다중 전문가 적대 라운드다.
- **P3 — pinned tools/apps = 힌트, 제약 아님.** 좌석은 이미 게이트웨이 도구를 다 부른다(sim 294회). pinned은 사전충전·우선순위일 뿐 터널링 강제 금지.
- **P4 — 좌석 제안엔 근거 필수.** 사용자가 좌석을 확정하려면 "왜 이 전문가"가 있어야 한다. 빠진 전문가 추가 여지도.
- **P5 — 스냅샷 = AI 증류 + 사용자 확정(편집 가능).** 지저분한 챗을 AI가 증류하되, 사용자가 편집·확정한 것만 넘어간다. "본 것 = 넘어간 것".
- **P6 — 범용 워크스페이스 + 심의는 한 핸드오프.** Word 출력 옆 버튼. VOC "정리하면 방향이 보인다"도 심의만이 목적지가 아니다.
- **P7 — 직행 심의 무손상(additive).** 새 prep은 `extraDelibOpts` 채우는 추가 진입점.
- **P8 — 앱 하드코딩 금지, MCP 레지스트리 기반 일반화.** 앱은 계속 MCP로 늘어난다. "그때 호출한 것 + 주변 명령"을 레지스트리로 재활용, 코드 무변경.

## 2. 아키텍처 — 두 갈래 유지 + 새 핸드오프

```
[챗 워크스페이스 (ChatPage)] ── 실데이터 정리·디벨롭 (MCP 도구 호출)
      ├─ [Word 출력]          (기존 ExportBar)
      ├─ [RA 보고서 저장]      (기존)
      └─ [🎛 심의로 넘기기]     (신규) → AI 브리프 제안 → 사용자 확정 → /심의 핸드오프
[직행 심의 (DeliberatePage / 챗 /심의 타이핑)]  (기존, 무손상)
```

## 3. 브리프 스키마 (2층 분리 — P1 의 구현)

버튼을 누르면 AI가 아래를 채워 제시, 사용자가 편집·확정한다.

```
심의 브리프
─ [증류층 — 사용자용, 심의로는 '제안/비구속'만] ─
├─ 목적·결정        이 심의가 막고 있는 결정 한 문장            → question 생성 재료
├─ 질문(제안)       날카로워진 핵심 질문                       → question (확정본만)
├─ 좌석(제안+근거)   recommend_agents + "왜 이 좌석" 근거        → personas (확정본만)
├─ 템플릿(제안)      chairTemplate                            → chair_template
├─ 자유 요약        ↑을 엮은 서사 (맨 끝, 사람이 읽는 정본)      → 심의엔 '비구속 배경'으로만(또는 미전달)
─ [원천층 — 심의로 그대로 건너감, 결론 아님] ─
├─ 데이터·근거      [MCP 근거 항목] 각 {source_app, tool, args, result 요지} — 날것·출처태그  → delib_opts.evidence (구조화)
├─ 재활용 도구      좌석이 이어 부를 MCP 명령(호출분 + 레지스트리 인접)                        → delib_opts.tools/apps (힌트)
└─ 가정·제약        사용자 명시 양보 불가·범위                                              → human_note / non_negotiables
```

**핵심(P1)**: 증류층의 "자유 요약"은 심의에 **정본으로 안 넘긴다**. 넘겨도 `[사전 정리 — 검증 대상, 결론 아님]` 으로 명시 태그. 심의가 추론하는 근거는 **원천층(날것 데이터)** 이다.

## 4. 핸드오프 계약 (매핑 기반 — 재사용 + 신설)

심의는 별도 엔드포인트가 아니라 **`/agent/chat` + `/심의 ` 프리픽스 + `delib_opts`**. `continueDeliberation`(ChatContext.tsx:499)이 검증된 마셜링 예시.

| 브리프 | → 전달 | 재사용/신설 |
|---|---|---|
| 질문(확정) | `sendMessage('/심의 '+질문, opts)` | 재사용 |
| 좌석(확정) | `delib_opts.personas` [{key,role}] | 재사용(발굴 생략) |
| 템플릿 | `delib_opts.chair_template` | 재사용 |
| 가정·제약 | `delib_opts.human_note` / `non_negotiables` | 재사용 |
| 재활용 도구 | `delib_opts.tools`(≤6) / `apps`(≤3) | 재사용(힌트) |
| **데이터·근거(원천)** | **`delib_opts.evidence`(신설, 구조화)** | **신설** ⭐ |

⚠ **결정적 갭(매핑)**: `run_deliberation`/`_deliberation_stream` 은 `history` 를 **안 받는다** — 챗의 실데이터·도구결과를 못 본다. `conv_store.meta`(JSON) 슬롯은 **비어 있음**. 그래서 원천 데이터를 텍스트로 압축(`continue_summary`)하면 = P1 위반(거수기). → **구조화 `evidence` 채널 신설**이 값의 핵심이다.

## 5. 일반화된 도구 컨텍스트 (P8)

- **캡처**: prep 중 챗이 부른 MCP 호출을 앱 무관하게 기록 — `{source_app, tool, args, result 요지}`. (DynaForge=dyna/d3plot 집계·StepForge=heaxstep_forge_*·ODB Hub=odb_hub·VOC=signalforge 는 예시일 뿐, 하드코딩 안 함.)
- **주변 명령**: 게이트웨이 `/tools-map`(`_group_of`/`_app_catalog`)로 **같은 앱/백엔드**의 인접 도구를 재활용 후보로. 의미 인접(fuzzy)이 아니라 **앱/백엔드 단위로 바운드**(노이즈 방지).
- **재주입**: `_deliberation_stream` 이 `evidence` 를 근거로 주입 + `tools/apps` 를 free-tools 우선순위로 재주입 → 좌석이 (a) 뽑힌 결과를 근거로 받고 (b) 이어 호출.

## 6. 배선 (파일단위 — 어디를 건드리나)

**프론트 `HWAXPortal/frontend/src`**
- `components/chat/ExportBar.tsx` — "🎛 심의로 넘기기" 버튼 추가(exportDocx 미러: 활성 `conv` 스냅샷 확보).
- (신규) `components/chat/HandoffBrief.tsx` — 브리프 미리보기·편집 패널(P5). AI 제안 → 사용자 확정.
- `state/ChatContext.tsx` — `startHandoff(conv)` 신설: 브리프 생성 요청 → 확정 후 `sendMessage('/심의 '+q, extraDelibOpts)`. `continueDeliberation`(:499) 패턴 확장.
- (브리프 생성) `api/chat.api.ts` — `/agent/deliberate/experts`(좌석) 재사용 + (신설) 브리프 제안 엔드포인트(증류 초안).

**챗 도구결과 저장 (스냅샷을 진짜로)**
- `backend/app/agent/conv_store.py` — `messages.meta`(JSON) 슬롯에 **도구결과 구조 저장**(현재 미사용). 저장 경로 `routes.py::gen()`(:852) 확장.

**심의 입력 채널 (신설)**
- `HWAXAgentServer/deliberation.py::_resolve_opts`(:191) — 화이트리스트에 `evidence` 추가(구조화 근거 항목, 항목당·총량 클램프).
- `_deliberation_stream`(:1603) — `opts.evidence` 를 근거로 주입(_evidence_prepass 와 병합) + `tools/apps` 재주입.
- `backend/app/agent/routes.py::DelibOpts`(:58) — `evidence` 필드 통과.

**보고서 출력 참고**: `docx_export.py`(스냅샷→산출물 원형), 심의 자동 RA 저장(deliberation.py:2184).

## 7. 페이즈 로드맵 (P1→P4, 각 게이트 수치/판정)

| P | 산출 | 게이트 |
|---|---|---|
| **P1** | `delib_opts.evidence` 구조화 채널 신설(백엔드) — 심의가 챗이 넘긴 원천 근거를 받아 좌석에 주입 | 근거가 결정문에 인용됨 + 텍스트압축 아닌 구조 전달 |
| **P2** | conv_store.meta 에 도구결과 저장 + "🎛 심의로 넘기기" 버튼 + 최소 브리프(질문·좌석·근거) 핸드오프 | 챗→심의 end-to-end, 원천 데이터가 심의에 도달 |
| **P3** | 브리프 편집 UI(HandoffBrief) — AI 제안 → 사용자 확정, 좌석 근거·원천/증류 분리 표시 | P1 준수(요약 비구속), P4·P5 충족 |
| **P4** | 재활용 도구 일반화(레지스트리 인접) + VOC/DynaForge/StepForge/ODB 실데이터 시연 | 앱 하드코딩 0, 새 앱 자동 편입 |

## 8. 체크리스트 (시작 준비)

- [x] P1: `deliberation.py::_resolve_opts` 에 `evidence` 화이트리스트 + 클램프 (d7b83f0)
- [x] P1: `_deliberation_stream` 이 `evidence` 주입(base _tail, 예산드롭) — tools/apps 재주입은 기존 채널
- [x] P1: `routes.py::DelibOpts` 에 `evidence` 통과 + relay(model_dump) 자동 포워딩 (679d672)
- [~] P2: (대체) 서버 meta 대신 클라이언트 영속 `Message.activity[]`(도구호출·결과)에서 evidence 추출 — 더 깔끔·P1 준수. 서버 meta 영속은 후속(리로드 생존)
- [x] P2: `ExportBar` "🎛 심의로 넘기기"(근거 있을 때만) + `ChatContext.startHandoff` + `handoff.ts::conversationEvidence`
- [x] P3: `HandoffBrief` 모달 — AI 제안(질문·좌석·근거·템플릿)→사용자 확정. 좌석 근거(why) 표시, 근거 "검증 대상" 명시
- [x] P4: 재활용 도구 일반화 — 챗이 부른 도구의 앱을 레지스트리 그룹에서 도출해 delib_opts.apps(free-query)로, 앱 바운드·하드코딩 0
- [x] 두 엔진 정합: MCP 워크플로(hwax-deliberate.js)도 evidence 주입(7446f18). 직행 심의 무손상.
- [x] (후속) 서버 meta 영속: gen()→conv_store.meta, 클라 복원(8b671bf) — 리로드 생존
- [ ] (후속·vLLM 필요) 질문 AI-증류: 현재 첫 발화 기반+브리프 편집. dev vLLM 꺼져 미구현
- [ ] (검증) e2e: 실제 심의로 좌석이 evidence 인용 — 진행 중

## 9. 비목표·미결

- **비목표**: 새 전문가 저작(좌석 실재), 직행 심의 변경, 심의 라운드 로직 변경.
- **미결**: `evidence` 총량 상한(RA 1900자/항목류 제약 참고)·도구결과 요지 압축 규칙(구조 보존 vs 크기), 브리프 제안용 LLM 프롬프트(증류가 결론화되지 않게 하는 제약), MCP 워크플로(JS) 측 evidence 대응 여부(웹 우선).
- **정합 주의**: 반영에 에이전트서버 API 재기동 필요, 워크플로 sync.
