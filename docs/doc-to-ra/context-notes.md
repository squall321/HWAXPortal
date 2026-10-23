# 문서 → RA 정밀 변환 — 결정과 까닭

> 계획 [PLAN.md](PLAN.md) · 체크리스트 [checklist.md](checklist.md) · 조사 [research.md](research.md).
> 아래는 계획을 세우며 내린(권장한) 결정이다. **사람이 정할 것은 PLAN §12** — 거기서 뒤집히면 여기 덧붙인다.

**DF-D1 원문 유지 + 모델 보강(10-24, 10-23 제안을 원칙으로).** 모델은 원본 글을 고쳐 쓰지 않고, 판독 · 요약 · 분류는 덧붙이고 표시한다. RA 의 결과를 사람이
고쳐야 하고(고친 것을 원본과 견줄 수 있어야 한다), 숫자는 원본에서 와야 하며(지어낸 수치가 보고서에 들어가면 찾을 길이 없다), 블록마다 어디서
왔는지가 남아야 하기 때문이다.

**DF-D2 변환과 배달을 나눈다(10-24).** 변환기는 RA 패키지(`report.json` + `resources/` + `conversion.json`)를 만들 뿐 RA 자격을 쥐지 않는다. 사용자 명의의 RA
연결은 이미 포털이 다룬다(RA 가져오기 · ai-draft 를 사용자 토큰으로 부른다). 패키지는 RA 인스턴스와 무관해 dev RA · cae00 RA 어디든 넣을 수 있고,
평가 · 재현 · 문제 추적이 이 파일 하나로 된다.

**DF-D3 엄격 생성 길로 넣는다(10-24).** RA 로 넣는 길 셋 중 배치를 준 그대로 지키는 것은 `POST /api/reports` 뿐이다. ai-draft(오늘 포털이 쓰는 길)는 준
layout 을 버리고 자동으로 깔며 빈 블록을 건너뛴다 — 슬라이드 배치를 옮기는 일(§6)이 거기서 지워진다. 엄격 생성은 검증만 하므로 우리 쪽 검증(S6)이
먼저 통과해야 한다.

**DF-D4 새 HEAX 앱으로 둔다(10-24, 권장 — §12-1).** Docling 모델 무게 · LibreOffice · 한글 글꼴은 수 GB 의 의존성이다. 포털 · 에이전트 서버에 넣으면 그 둘이
무거워지고, AIDH 는 남의 리포이며 목적(지식카드)이 다르다. StepForge 와 같은 꼴(HEAX 앱 · MCP · 잡 · 원장 · SP 거울)이면 게이트웨이에 저절로 실리고 굵은
SIF 배포 선례(5.2GB)도 있다.

**DF-D5 Pydantic 모델이 계약이고 도구는 M0 에서 잰다(10-24).** 사용자는 Pydantic AI 를 말하고 대체재도 괜찮다고 했다. vLLM(GLM · Qwen)에서 `NativeOutput`
(json_schema)이 지켜지는지는 확인된 출처가 없다(research §4). 그래서 계약(RA 위젯 내용 · IR · 판독 · 온톨로지 후보)은 Pydantic 모델로 먼저 박고, 그 계약을 채우는
도구(Pydantic AI · vLLM json_schema 직접 · Instructor · LangChain)는 M0 의 준수율로 고른다. GLM 은 스트리밍에서 도구 호출을 잃은 적이 있어(에이전트 서버
`LLM_DISABLE_STREAMING`) 구조화 호출은 비스트리밍으로 잰다.

**DF-D6 정해진 일은 코드, 판단만 모델(10-24).** 차트 값은 원본의 차트 XML 캐시(`c:numCache`)에 이미 있다 — VLM 에게 차트 그림을 읽히면 맞는 값을 틀리게
읽을 길만 생긴다. VLM 은 그림으로 박힌 차트 · 사진 · 도면처럼 원본에 데이터가 없는 것만 읽는다. LLM 은 '이 글상자는 저 그림의 설명인가' 같은 판단을
주어진 id · 원문 구절 안에서만 고른다.

**DF-D7 온톨로지는 둘이고 세 번째 저장소를 만들지 않는다(10-24).** 사내 온톨로지는 SP(과제 · 모델 · 프로젝트 · 부서 — 정본은 SP 허브)와 RA 자체 엔티티
(보고서 태깅 축 7 · 별칭 · 자동 태깅 제안 큐)다. 변환기는 후보와 근거를 내고, RA 에 이미 있는 값은 `entity_ids` 로, 없는 값은 RA 제안 큐에 맡기며, 보이는
자리(첫 쪽 `key_value`)에 적는다. SP key 를 RA 엔티티에 잇는 것은 RA 의 데이터 관리 영역이라 RA 주인과 합의한다(§12-10).

**DF-D8 SP 거울은 변환기에 둔다(10-24, 권장 — 뒤집을 수 있다).** StepForge 의 `find_plm_task` 에 물으면 코드가 줄지만 StepForge 가 떠 있어야만 변환이 된다.
수신 키트는 의존성이 requests · sqlite3 뿐이고 StepForge 가 이미 옮겨 다듬었다(`core/sp_core.py` — 출처 머리 주석을 따라 다시 옮긴다). 허브 주소 · 토큰은
StepForge 와 같은 미결(사람)이다.

## 조사에서 확인한 사실(계획의 전제)

- RA 의 PPTX 가져오기는 차트 · SmartArt 를 경고와 함께, 노트 · 링크 · 위치를 말없이 버린다. EMF 그림을 그대로 올린다(브라우저가 못 연다). Word · Excel ·
  PDF 변환기는 RA 에 없다. RA 안에 그림을 모델에 보내는 곳이 없다.
- AIDH `convert_file` 은 그림을 자리만 남기고, 뽑은 그림을 임시 폴더에 남긴 채 지우지 않는다. Excel 은 수식 없이 캐시 값만 읽는다.
- Docling · Pydantic AI · Instructor · MarkItDown · Unstructured 는 어느 리포에도 없다. LibreOffice 는 dev 호스트에만 있다.
- cae00 SP 허브에는 아직 아무 앱도 붙지 않았다(StepForge 도 가짜 허브 회귀까지).
- `GalaxyOntology` 는 이 일과 무관하다.
