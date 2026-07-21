# 심의 파이프라인 업그레이드 노트 — 2026-07-19 ~ 07-21 세션 토의 기록

> 이 문서는 3일간의 대화형 엔지니어링 세션에서 확정된 설계 결정·사고 부검·계약을 남긴다.
> 상세 근거는 [GLM-DELIB-TUNING-REVIEW.md](GLM-DELIB-TUNING-REVIEW.md)(품질 진단),
> [MCP-TOKEN-SAVING-DESIGN.md](MCP-TOKEN-SAVING-DESIGN.md)(토큰 절약 설계) 참조.

## 1. 워크플로(hwax-deliberate.js) 계약 확장

- **라운드 수 가변**: `rounds`(2~8, 기본 3 = 초기+심화N+수렴). 헤더 주석만 있고 배선이 없던
  죽은 문서를 실제 배선함. 참여 인원은 `personas` 배열 길이가 그대로 결정(상한 없음).
- **이어하기**: `continueFrom:{summary, roundsSoFar}` — 라운드 번호가 이어지고 1라운드가
  "이어하기 개시" 프롬프트로 바뀐다. 반환 `nextRoundOffset`을 다음 호출의 roundsSoFar로.
- **인간 검토자 의견**: `humanNote` — 매 라운드 프롬프트에 [인간 검토자 의견]으로 강제 주입.
  스모크 검증에서 전문가들이 실제로 입장을 수정함(A 지지→조건부 M6 하향 등).
- **보고서 이어붙이기**: `appendToReportId` — 새 RA 보고서 대신 기존 보고서에 새 페이지 추가.
- 반환 스키마 변경: `{round1,round2,round3}` → `{rounds:[...], roundLabels, nextRoundOffset}`.

## 2. 절단 층위 설계 (전 경로 공통 원칙)

| 층위 | 정책 | 근거 |
|---|---|---|
| 모델 입력(role·라운드 직렬화) | 무절단 기본. 다인원 합산만 여유 상한(SER_CLIP 700/값, 의장 6000/라운드) | 모델이 읽는 것을 자르면 발언 깊이가 그 상한에 갇힌다 — GLM 단순화 1차 원인 |
| 기록(RA 회의록·대화 저장) | 온전한 발언(full 합성). 상한은 저장 API 보호용(2000자/발언, 40문단/결정문) | #14·#16 이 400자/12문단 컷으로 잘려 수동 재작성했던 재발 방지 |
| 화면(회의 버블) | 가독성 절단 유지, CLIP_SCALE 배율 | 표시용 |

- 발언 개행 보존: `_clip_sent`가 `\s+`로 개행까지 뭉개던 것을 가로 공백만 정규화로 수정,
  부분 발언(수용/반박/심화)은 빈 줄 문단 구분. 프롬프트 컨텍스트용 compact 와
  기록용 readable 합성을 분리(JS 워크플로).

## 3. GLM 심의 튜닝 — env 손잡이 (agent-server)

- `LLM_*`(챗 포함 전역) / `DELIB_*`(심의 라운드 전용, 챗에 새지 않음) 분리.
  temperature·max_tokens·reasoning_effort(반드시 extra_body 경유 chat_template_kwargs)·timeout.
- 기본값 = 전부 종전 동작(무회귀). cae00 권장값은 env-kit(agent-server.env)에 시드.
- **기각된 통념**: max_tokens 2048~4096 명시는 개선이 아니라 상한 신설(현재 미전송=무상한) —
  thinking 토큰과 겹치면 미완 JSON→폴백으로 악화. 설정 시 8192급만.
- vLLM 서버측에서 temperature는 못 바꿈(클라 명시 전송이 이김). 유효 서버 레버는
  reasoning parser·generation-config(max_new_tokens/repetition_penalty)뿐.
- `DELIB_REASONING_EFFORT=high`는 상암 parser(glm45) raw curl 진단 후 주석 해제 —
  parser 미스매치 상태에서 켜면 <think> 혼입으로 오히려 악화.
- 파싱 재시도: required 키 검증 + 재시도마다 문구 가변(temperature 0에서 동일 실패 반복 방지),
  실패해도 say 원문 보존(_ser) — 무음 유실 제거.

## 4. 사고 부검 2건

### 4-1. agents 테이블 merge 침묵 실패 (AIDataHub)
merge-from-drive.sh 가 `agents.updated_at`(존재하지 않던 컬럼)을 참조 → 매 배포마다
SQL 에러로 스크립트 전체 중단 → agents 이후 순번 테이블 전부 동기화 정지.
부작용으로 cae00 수기 추가분은 "보호"됐지만 dev→cae00 전파도 죽어 있었음.
수정: 마이그레이션 0030(updated_at + BEFORE UPDATE 트리거, 0002의 set_updated_at 재사용).

### 4-2. 심의 대화 422 배치 유실 (포털 대화 저장소)
LLM이 persona 필드에 긴 역할 설명을 붙여 반환 → 포털 `persona ≤120자` 검증에 걸리면
**배치 전체 거부** → 전기박리 테이프 심의 대화 통째 유실(CONV_UNAVAILABLE: portal 422).
수정 2겹: ①워크플로가 전 라운드 persona를 정본 키로 강제(withKey) ②게이트웨이가 포워딩 전
role/content/persona/messages 상한 정규화. 유실분은 워크플로 journal에서 재조립해 복구.

## 5. MCP → 웹 소유권 규칙

- 대화 저장소 소유권 = **호출자 PAT의 sub** (게이트웨이는 Authorization을 그대로 포워딩).
- 웹에서 보이려면 MCP 연결 PAT가 웹 로그인 계정 발급이어야 한다. dev에서
  claude-code-hwax@local PAT로 저장된 심의는 hwax.demo 웹에 안 보였음 → 데모 계정 PAT
  발급(백엔드 keystore로 _mint_pat 동일 클레임, aud에 mcp-gateway 필수) 후 토큰 교체.
- cae00 운영은 사용자 본인 PAT라 원래 정합.
- 웹 렌더: persona 메시지 묶음 → delib(turns/decision) 재조립(serverMessagesToLocal) →
  DelibView가 라이브 심의와 동일하게 그림.

## 6. 프론트 렌더 (챗·심의 공통)

- 마크다운 블록 렌더(의존성 없는 md.ts): 제목/표(정렬·zebra)/목록/체크리스트/인용/콜아웃
  ([!NOTE]·이모지)/구분선/링크(http·https만, noopener). HTML 미주입 — XSS 표면 없음.
- 구문 강조: 경량 토크나이저(highlight.ts) — python/js/json/sql/bash/yaml, GitHub Dark 근사.
- KaTeX 수식: 번들 동봉(빌드는 dev, cae00은 dist만 받으므로 오프라인 제약과 무충돌).
- 심의 버블: InlineMd → TextBlock(블록) 전환으로 문단·목록 표시.
- 대화 내보내기: 보이는 그대로 HTML(사이트 CSS 인라인+애니메이션 비활성+폰트 절대 URL) /
  구조화 JSON(hwax.chat.export/1 — 라운드 그룹·표결 포함).

## 7. 사전지식 없는 재현 검증 (심의 파이프라인의 실증)

사내 실무로 확인돼 있던 결론 2건을, 결론을 입력하지 않은 심의가 독립 재현:
- AP 중앙볼 크랙 = 수지 비압축(K-지배) 팽창의 z방향 open + 저밀도(장피치) 볼 집중 (보고서 #14)
- 폴더블 FPCB: 단층 동박도 굴곡반경 0.7R 미만이면 고위험 (보고서 #10, R_transit=0.7×R_nom)
비교 슬라이드: claude.ai/code/artifact/07e1681a-8a9c-485b-8559-9095b14248a5
