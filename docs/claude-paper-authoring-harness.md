# Claude Code 논문 저작 하네스 — 설계 (step 1)

작성 2026-08-28 · 대상: dev(온라인·Claude API) · 산출: ExpertAgents 지식카드 · 소비: AIDataHub→cae00
목표 — **논문을 정보손실 최소로 카드화**한다. 기계적 텍스트추출(pymupdf)·템플릿 조립(cardgen)을
**Claude(비전)** 저작으로 대체/보강하고, cae00 는 MCP 로 원격 하네스한다(Claude API 는 dev).

---

## 0. 왜 — 손실은 "읽기"와 "조립"에서 난다

- 지금 경로: PDF→텍스트추출(표·수식·그림 소실)→임베딩 군집→**템플릿 조립**(cardgen)→fact_refs(apply_refs).
- Claude 는 **PDF 페이지를 이미지로 읽어**(Read 비전) 표·수식·그림 캡션까지 이해하고, 카드 스키마에 맞춰
  **주장·근거·경계**를 직접 저작한다. 조립이 아니라 이해 기반 저작이라 손실이 최소다.
- Claude API 는 dev 에만 있다(cae00 airgap·github 차단 확인됨). 그래서 **두뇌=dev, 데이터·도구=cae00 MCP**.

## 1. 아키텍처

```
[dev, Claude API]
  relay/_inbox 의 PDF ──▶ Claude Agent SDK 하네스(headless, 논문당 1세션)
     1) Read(PDF, 비전)         — 페이지 이미지로 고충실도 판독(표→md표, 수식→LaTeX, 그림→캡션)
     2) recommend_agents(MCP)   — 대상 전문가 분류(기존 EG 임베딩 NN 대체/보완)
     3) get_context_bundle(MCP) — 그 전문가의 기존 카드 조회 → 중복·경계 회피, 교차인용 배선
     4) 카드 저작               — ExpertAgents 카드 스키마(frontmatter+섹션+fact_refs), review_status: draft
     5) write knowledge/<expert>/cards/<ABBR>-X-NNN.md + facts/manifest.yaml(DOI 서지)
        │
        ▼  (기존 하류 그대로)
     GLM/Claude 게이트(claim↔근거) → review_status: fact-checked
     → erag export-records/export-aidatahub → AIDataHub → backup-to-drive → cae00 update-all §3 merge
```

- **하네스 형태**: Claude Agent SDK headless 앱(python/TS). dev 서비스/cron 으로 `_inbox` 를 돌며 논문당 1세션.
  Workflow(팬아웃)로도 가능하나, 배치·재시도·멱등(ledger)이 필요해 SDK 앱이 자연스럽다.
- **MCP 접속**: 게이트웨이(:9110) 도구를 SDK `mcpServers` 로 물린다 — recommend_agents·get_context_bundle·
  semantic_search·(선택)add_training_data/import_record. cae00 데이터를 원격 하네스하는 지점.
- **입력**: PaperIngest relay 의 `DRIVE_OUTBOX`→dev pull 로 온 PDF(원본 PDF 를 relay 가 함께 나르게 조정 필요 —
  현재는 .md 만. §5 참조).

## 2. 카드 저작 계약 (Claude 산출 스키마)

Claude 가 논문당 낼 것 — 기존 카드 형식과 동일해 하류 무변경.
- **frontmatter**: `id`(ABBR-X-NNN, 발급규칙 준수)·`expert_id`·`title`·`type`(concept/faq/design-rule/…)·
  `confidence`·`tags`·`review_status: draft`·`tier`·`fact_refs: [DOI→DOC-* 는 apply_refs 가 배선]`.
- **본문 섹션**: 표는 **md 표**로, 수식은 **LaTeX/텍스트**로, 그림 근거는 캡션·수치로 보존. 주장마다 논문 근거를
  명시(페이지·표·식 번호). 기존 카드로 위임되는 경계는 `[ABBR-C-NNN]` 교차인용.
- **금지**: 원문에 없는 값 지어내기(환각). 불명확은 `(원문 미상)` 표기. 카드=주장+근거, 근거 없는 수치 금지.

## 3. 품질 게이트 (환각 방어)

1. **Claude 자기검증 2-pass** — 저작 후 별도 세션이 "각 수치·주장이 원문 PDF 에 실재하는가"를 대조(비전 재확인).
2. **기존 GLM 게이트 재사용** — claim↔근거 지지 판정(사외호출 0). 통과분만 `review_status: fact-checked`.
3. **사람 검토** — PaperIngest 웹 UI(또는 신설)에서 draft 카드 승인. fact-checked 만 AIDataHub 업로드(기존 규칙).

## 4. 페이즈 (P1→P4)

| P | 산출 | 게이트 |
|---|---|---|
| **P1** | dev 에서 **PDF 1건 → 카드**(Claude 비전, 수동 실행). 알려진 논문으로 충실도 대조 | 표·수식 보존 + 환각 0(자기검증) |
| **P2** | `_inbox` **배치**(논문당 1세션·ledger 멱등·실패격리) | 기존 cardgen 대비 충실도·커버리지 향상 |
| **P3** | **MCP 하네스** — recommend_agents 분류 + get_context_bundle 중복회피 + 배선 | cae00 코퍼스와 정합(중복·경계 오류 0) |
| **P4** | 게이트(자기검증+GLM)·사람 승인 UI·export 자동화 | fact-checked→AIDataHub→cae00 end-to-end |

## 5. 선결·미결

- **원본 PDF 를 dev 까지 나르기** — 현재 PaperIngest 는 업로드 즉시 `.md`(pymupdf)로 변환해 스테이징한다.
  고충실도 비전 저작을 하려면 **원본 PDF 도 함께 relay**(to_drive_pusher 가 PDF 원본 포함)하고 dev 하네스가 PDF 를 읽어야 한다.
  → PaperIngest `POST /papers` 가 PDF 원본도 보관하도록 소폭 조정(현재 md 만 저장).
- **하네스 위치**: 신규 소형 리포/디렉토리(Agent SDK 앱) vs ExpertGrounding 안. dev 전용이므로 EG 인접이 자연스러우나
  Claude API·SDK 의존이 추가되니 **독립 컴포넌트** 권장.
- **id 발급·멱등**: 카드 id(ABBR-X-NNN) 충돌·중복 저작 방지 — ledger + 기존 카드 스캔(get_context_bundle).
- **비용·속도**: 논문당 비전 세션은 pymupdf 보다 느리고 비싸다. dev 배치·야간 처리로 흡수.
- **cae00 무관**: 이 하네스는 cae00 에 아무 것도 안 깐다(Claude=dev). cae00 는 MCP 를 노출만 하면 된다(기존 게이트웨이).

## 6. 다음

P1(단일 PDF→카드 하네스, dev)부터. Agent SDK 앱 골격 + 카드 저작 프롬프트(스키마·근거강제·환각금지) +
Read 비전 판독 + 알려진 논문 1건 충실도 대조. 유효하면 P2 배치 → P3 MCP → P4 게이트.
