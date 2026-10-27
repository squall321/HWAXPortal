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

**DF-D9 사용자 결정 셋(2026-10-24).** ① VLM 은 stcx Qwen ② 새 HEAX 앱(DocForge) ③ 뼈대는 dev 에서 짜 두고 **상세 개발은 cae00 에서** — 새 앱을 배치해
넣는 것까지 포털에 계획서로 넘기면 그쪽 세션이 개발한다(인계 [cae00-handoff.md](cae00-handoff.md)). 사용자 덧붙임 「되도록 상세한 것들을 넣어서 — 그쪽에서
개발을 시킬 테니까」 — 그래서 뼈대에 계약 · 단계 명세(모듈 머리) · 명세 시험(xfail strict) · M0 탐침 · 배치 절차까지 넣었다.

**DF-D10 개발은 main, 배치는 release(2026-10-24).** cae00 은 이 앱의 SIF 를 지을 수 없다(apt · torch — HEAX 허브 조사). cae00 의 스캔은 캐시 열쇠
(커밋 + 매니페스트 + 틀)가 Drive 로 받은 SIF 와 같을 때만 띄운다 — cae00 세션이 개발 중에 올린 커밋이 운영 인스턴스를 흔들지 않게 매니페스트
`source.ref: release` 로 두고, dev 가 지어 올린 커밋만 release 로 옮긴다. 배치 한 번마다 dev 의 손이 한 번 든다(DocForge docs/DEPLOY.md §7).

**DF-D11 cae00 개발 환경은 두 길(2026-10-24).** cae00 은 사내 프록시가 TLS 를 다시 서명한다 — PyPI · Hugging Face 가 사내 CA 로 열리면 venv(길 A),
아니면 dev 가 지은 앱 SIF 에 작업 사본을 얹어 쓴다(길 B — `scripts/dev-in-sif.sh`, editable 설치라 그대로 import). 어느 길인지는 cae00 에서
`scripts/check-cae00-env.sh` 로 잰다(dev 에서 돌려 판정 논리를 확인했다 — 404 도 '닿았다' 로 셈한다).

**DF-D12 포털 ↔ DocForge 는 경로로 주고받는다(2026-10-24).** StepForge 보내기와 같은 꼴 — 포털이 받아 둔 파일의 **호스트 경로**를 MCP `docforge_convert` 에
넘기고(본문을 MCP 로 나르지 않는다), 패키지는 데이터 루트 기준 경로(`package_rel`)를 돌려줘 포털이 형제 리포 `../HEAXHub/var/app_data/doc_forge/…` 로 읽는다.
DocForge 는 입력을 `DOCFORGE_INPUT_ROOTS` 밑만 받는다(아무 경로나 읽히면 $HOME 밑 비밀까지 읽힌다).

**DF-D13 포털 배달은 포털 리포의 일이고 운영 체크아웃에서 하지 않는다(2026-10-24).** cae00 의 `~/Projects/HWAXPortal` · `HEAXHub` 는 update-all 이 pull ·
재기동하는 운영 사본이다 — 거기 커밋하지 않은 변경이 남으면 배치가 깨진다. 포털 배달(목적지 · 진행 · 사용자 명의 엄격 생성 · 알림)은 포털 세션이 dev 에서
하거나 cae00 의 **따로 clone 한 사본**에서 하고 push 한다(cae00-handoff §4 · §5).

**DF-D14 dev 먼저, 실데이터가 필요해지면 cae00(2026-10-24, 사용자 결정 — DF-D9 ③ 을 고쳐 씀).** 사용자 「일단 로컬로 개발하다가 데이터가 필요해진 시점부터
내부 개발도 가능한가?」 → 「계획 써 두면 그쪽 VS Code 에서 md 시작점을 보고 만들기 시작하면 좋겠어」. dev 는 인터넷 직결(pip · Hugging Face · GPU ·
LibreOffice)이고 SIF 를 직접 지어 고리가 빠르다. cae00 은 지을 수 없어 배치마다 dev 의 손이 든다. 사내 문서는 cae00 에만 둔다(dev 는 외부에 노출된 박스).
dev 에서는 M1 의 코드를 합성 · 공개 문서로(RA 계약은 RA 자신의 검증 모듈을 읽기 전용으로, VLM · LLM 은 가짜 서버로) 끝까지 만들고, 실문서로 정할 것 ·
stcx Qwen 진짜 호출 · 실제 RA · SP 허브 · DRM 은 cae00 에서. 합성 문서의 한계 때문에 첫 배치 직후 cae00 에서 작은 M0 를 일찍 권한다.
시작점은 DocForge `docs/START.md`(새 세션이 CLAUDE.md 에서 그리로 간다).

**DF-D15 허브 등록은 첫 SIF 를 Drive 에 올리는 것과 한 묶음(2026-10-24).** 등록 사본은 HEAXHub 리포에 있어 push 하면 cae00 의 다음 update-all 이 받는다 —
SIF 가 Drive 에 없으면 그 앱을 띄우지 못해 실패나 경고를 남길 수 있다(확인하지 않았다). dev 단계는 venv 로 루프백에 띄워 개발하고, 등록 · SIF · 모델 · Drive 는
한 날에 한다(DocForge R-D15 · DEPLOY §4).

**DF-D16 모델 끝점은 cae00 에서 공유받는다(2026-10-24, 사용자 「실제 운용은 cae00 의 조건 — 환경변수를 공유받고」).** DocForge 는 전용 값이 없으면
공유 이름을 읽는다 — VLM `DOCFORGE_VLM_*` → `CHAT_LLM_*`(포털 챗 서버 stcx Qwen — 그림을 읽는다), LLM 판단 `DOCFORGE_LLM_*` → VLM 과 같은 끝점 →
허브가 모든 앱에 넘기는 `LLM_*`(RA 의 GLM). 출처마다 주소 · 모델 · 키를 한 묶음으로 고르고 그림 판독은 GLM 으로 넘기지 않는다(DocForge R-D29).
허브 앱이 `CHAT_LLM_*` 를 받는 길은 포털 update-all 1g2(`infra/.env` → `HEAXHub/.env` 의 `APPTAINERENV_CHAT_LLM_*`, chat-llm-stcx CL-D10)다 —
cae00 에서 따로 적을 값은 DocForge 고유 경로 둘(`DOCFORGE_INPUT_ROOTS` · `DOCFORGE_HOST_DATA_DIR`)뿐이다.

## 조사에서 확인한 사실(계획의 전제)

- RA 의 PPTX 가져오기는 차트 · SmartArt 를 경고와 함께, 노트 · 링크 · 위치를 말없이 버린다. EMF 그림을 그대로 올린다(브라우저가 못 연다). Word · Excel ·
  PDF 변환기는 RA 에 없다. RA 안에 그림을 모델에 보내는 곳이 없다.
- AIDH `convert_file` 은 그림을 자리만 남기고, 뽑은 그림을 임시 폴더에 남긴 채 지우지 않는다. Excel 은 수식 없이 캐시 값만 읽는다.
- Docling · Pydantic AI · Instructor · MarkItDown · Unstructured 는 어느 리포에도 없다. LibreOffice 는 dev 호스트에만 있다.
- cae00 SP 허브에는 아직 아무 앱도 붙지 않았다(StepForge 도 가짜 허브 회귀까지).
- `GalaxyOntology` 는 이 일과 무관하다.

**DF-D17 포털 배달 — 「Report Archive — 정밀 변환」(2026-10-24, DocForge E7).** cae00-handoff §4 를 그대로 붙였다. 정한 것 —
① 목적지 `reportarchive_precise`(PPTX · DOCX · XLSX · PDF — DocForge 가 넷 다 돈다) · 권한은 RA **와** DocForge 둘 다(`upload.py` 의 `also` — 기존
목적지는 그대로 하나). 권한표에 `docforge`(게이트웨이 `heax-doc_forge`)를 **앱을 beta 로 올리기 전에** 더했다(표에 없는 키는 '전체 공개').
② 맡기기는 StepForge 꼴 — 스테이징 **호스트 경로**를 사용자 PAT 로 `docforge_convert(path, parser=auto, vlm)` · vlm 은 기본 켬(목적지 이름이 '그림
판독' 이다 · DocForge 가 동시 2 로 묶는다). 맡긴 사람을 스테이징 아래 `#docforge-jobs/<job>.json` 에 남기고 진행(`docforge_status`) · 배달 · 취소는
그 사람만(남의 것 · 없는 것은 똑같이 404). ③ 배달은 **화면이 끝난 것을 보고 부른다**(포털이 뒤에서 기다리는 일감을 만들지 않는다 — 창을 닫으면
잡은 끝나도 안 넣는다, 다시 열 길은 아직 없다). 패키지는 `docforge_package` 의 `package_rel` 을 포털 설정 `docforge_package_root`(start.sh 가 형제
리포 `HEAXHub/var/app_data/doc_forge` 의 호스트 경로로 넘긴다 — $HOME 밑이라 컨테이너에서도 같게 보인다) 밑에서만 읽는다(realpath 검사).
④ 넣기 — RA 토큰은 RA 가지와 같은 함수(`_ra_user_token`, 위임 먼저 · 등록 토큰 다음)로 떼어 같이 쓴다. report.json 이 가리키는 리소스만
`POST /api/files`(쓰지 않는 리소스는 올리지 않는다) → `res://` 를 받은 id 로 → template 을 pages[0] 에서 올려 `POST /api/reports`. RA 상한
(`docforge_ra_file_max_mb`, 25)을 넘는 리소스는 올리지 않고 그 파일 칸을 빼고 경고 · 위임 토큰 401 은 한 번만 새로 받는다 · RA 가 템플릿을
모르면 'RA 웹 가져오기를 한 번' 안내. ⑤ 한 잡은 한 번만 — 잡마다 잠금 + 기록의 `delivered`(두 번 눌러도 보고서 하나). ⑥ 알림은 화면 몫(종전
꼴) — 보고서 링크 · 쪽 · 블록 · 버린 요소 · 모델 판독 · 무음 누락 · '모델 판독' 확인 문구 · PC 추출본이면 충실도. 남은 것 — DocForge status beta
(게이트웨이 tools/list 확인) · dev 실주행 · 브라우저 시험 · PC 도우미 묶음(글 + 슬라이드 그림을 zip 으로 묶어 넘기기, DocForge R-D35)을 이 목적지에.

**DF-D18 PC 도우미 추출본도 정밀 변환으로(2026-10-25, DocForge E5 의 포털 몫).** 받은 글(.hwax.md)의 다음 단계에 「Report Archive — 정밀 변환」 을
더했다(목적지 `exts` 에 md — 화면은 .md 를 브라우저에서 읽으므로 스테이징의 .md 는 도우미가 올린 것이고, dispatch 가 추출기 머리말을 다시 본다 ·
아니면 맡기지 않고 까닭). 슬라이드 그림이 왔으면 글과 함께 **zip 하나**로 묶어 넘긴다(DocForge 는 파일 하나를 받는다 — R-D35). 정한 것 —
① 글 상자 → 그림 상자 색인은 `#pc-slides/<글 상자>.json`(주인 · 그림 상자 · 수). 글 상자 안에 두지 않는다 — `staged_path` 가 상자의 **첫 파일**을
집으므로 다른 파일(색인 · zip)이 끼면 AI 데이터 허브로 보낼 때 글 대신 그것이 간다. ② zip 은 새 상자에 만들어 `docforge_convert` 뒤 지운다(DocForge 는
맡을 때 입력을 제 잡 폴더로 링크 · 복사해 둔다). zip 안의 글 이름은 늘 `*.hwax.md`(DocForge 가 그 꼴로 찾는다). ③ 색인 · 그림이 청소됐으면(6시간)
글만 넘긴다 — DocForge 가 '슬라이드 그림이 없다' 를 경고로 말한다. ④ PP-D11 의 '다음 단계는 AI 데이터 허브만' 시험을 이 결정으로 고쳤다.

**DF-D19 '이 대화에서 분석' 을 DocForge 로(2026-10-25, DocForge E10).** `plat:docforge` 가 있는 사람의 '이 대화에서 분석' 은 DocForge 에 맡긴다
(차트 값 원본 캐시 · SmartArt · 수식 · 발표자 노트 · 병합 표까지 원문에서 — AI 데이터 허브 변환기보다 덜 잃는다). 정한 것 — ① 그림 판독은 끈다
(대화에서 바로 묻는 길이라 빨라야 하고 stcx Qwen 을 챗과 나눠 쓴다 — 그림이 필요하면 정밀 변환). ② 같은 잡 길(맡긴 사람 기록 · 1.5초 진행)을 쓰고
끝나면 `…/jobs/{id}/document` 가 패키지의 `document.md`(DocForge R-D40 — 포털이 이미 읽는 hwax-doc/1 꼴)를 돌려준다 → 화면이 문서 칩으로 붙인다.
대화에 '보냈다' 알림은 없다(읽어 온 것 — PP-D17 그대로). ③ DocForge 가 맡지 않으면(게이트웨이에 없음 · 거절) 같은 요청 안에서 지금 길(AI 데이터
허브)로 간다 — beta 전 · 권한 전에도 이 목적지가 멈추지 않는다. ④ 대화용 잡(purpose chat)은 RA 배달을 409 로 거절한다. ⑤ 창을 닫으면 붙이지
않는다(받을 곳이 없다) — 패널이 그렇게 말한다. ⑥ document.md 는 DocForge 0.3.0 부터다 — 0.2.0 이 깔린 채 beta · 권한을 열면 그 사람들의
분석이 끝에서 '글이 없다' 로 멈춘다. 그래서 beta 는 0.3.0 배치 뒤에 연다(DocForge DEPLOY §4-10 ⓪).

**DF-D20 DocForge 운영자 페르소나(2026-10-25, 사용자 「그 역할을 다 할 수 있는 페르소나를 잘 정리해서 추가」).** HE팀 MCP 운영자 정본(infra/personas/
he-team.json)에 `he-doc-docforge`(보고서·문서·발표 묶음)를 더했다. 역할 — 변환은 **직접 부르지 않고** 챗 업로드 「Report Archive — 정밀 변환」 으로
안내한다(호스트 경로 · 사람 명의 엄격 생성 · 진행 · 알림을 포털이 잇는다 — docforge_convert 는 서버 입력 경로를 이미 알 때만) · 진행(status) ·
변환 보고서 풀이(package — 버린 요소 · 모델 판독 · 경고) · 취소(확인받고) · DRM 은 PC 도우미 → 정밀 변환 · 저장 없이 묻기는 '이 대화에서 분석'.
개념에 원문 유지 + 모델 보강 · 차트 값은 원본 캐시 · 무음 누락 0 · RA 에 넣지 않음 · 충실도 셋 · 형식별 규칙을 적었다. 만든 보고서를 읽는
RA 도구(get_report_outline · get_report)는 **선택 앱**이다 — RA 가 안 붙은 박스에서도 운영자는 생긴다. DocForge 가 게이트웨이에 없으면(지금 draft)
동기화가 건너뛴다 — beta 뒤 update-all 의 동기화(또는 `sync-he-personas.py --apply`)가 만든다. 조립한 프롬프트 약 3,000자(상한 8,000).
화면 행선지 표(destApps)의 `reportarchive_precise` 에 `heax-doc_forge` 가 있어, 이 운영자와 대화 중이면 정밀 변환 목적지가 '지금 전문가' 로 앞선다.

**DF-D21 DocForge 가 게이트웨이에 없으면 정밀 변환 목적지를 숨긴다(2026-10-25, cae00 업데이트 점검 · 포털 `2a27208`).** 등록이 draft
(게이트웨이에 안 실림)인 박스 — 지금의 dev · cae00 — 에서 「Report Archive — 정밀 변환」 은 권한만 보고 떠서, 고를 때마다
`docforge_convert` 에서 실패했다. ① 목적지에 `needs_tool: docforge_convert` 를 두고, 업로드 · PC 도우미 다음 단계의 목적지 계산이
게이트웨이 `/tools-map`(인증 없음)의 이름을 받아 그 도구가 없으면 뺀다. ② 이름은 60초 붙잡는다. 못 읽으면 '모름' 이라 숨기지
않는다 — 게이트웨이가 잠깐 안 닿는다고 목적지를 지우면 그 사이 올린 사람이 '보낼 곳이 없다' 를 본다. ③ 게이트웨이는 이름이 겹칠
때만 접두를 단다(StepForge 의 `cancel_job` 등은 `heaxstep_forge_` 가 붙었다) — `docforge_*` 는 겹치지 않아 맨 이름이고 포털이
부르는 이름과 같다. ④ '이 대화에서 분석' 은 가리지 않는다 — DocForge 가 없으면 같은 요청이 AI 데이터 허브로 간다(DF-D19 ③).

**DF-D22 DocForge 데이터 루트를 포털 컨테이너에 읽기 전용으로(2026-10-25, 포털 `e38be9a`).** server-setup §2 는 'cae00 은
`~/Projects` 라 해당 없다' 였다 — 틀렸다. `$HOME` 은 자동 마운트라 `HEAXHub/var/app_data` 링크 자체는 보이지만, /data 이관 뒤엔
그것이 `/data/appdata` 로 가는 심링크라 끝이 컨테이너에 없다(dev 실측 — 모든 배달이 '패키지를 찾지 못했다'). start.sh 가
`DOCFORGE_PACKAGE_ROOT` 를 끝까지 따라가 `$HOME` 밖이면 그 경로를 같은 자리에 `:ro` 로 묶는다. 쓰기는 주지 않는다 — 포털은
패키지를 읽기만 하고, 쓰는 쪽은 DocForge 다. 앱에는 링크 경로를 그대로 넘긴다(그쪽이 남기는 경로와 같은 꼴).

**DF-D23 창을 닫아 넣지 못한 정밀 변환을 다시 연다(2026-10-27, DocForge E15).** 정밀 변환은 화면이 진행을 보다가 끝나면 넣는다 — 창을 닫으면 DocForge
변환은 끝나도 RA 에 들어가지 않았고 되찾을 길이 없었다(패널이 '닫아도 변환은 계속' 이라고만 했다). ① 맡긴 사람의 잡 목록
`GET …/docforge/jobs`(새것부터 20 · 대화용 · 숨긴 것 빼고) — 아직 넣지 않은 잡만 DocForge 에 지금 상태를 묻는다(못 물으면 st 없음). ② 입력창 위
「끝나지 않은 정밀 변환 N건」 — 줄 서는 중 · 변환 중 · 끝난 잡만 보이고(넣은 · 실패 · 취소 · 못 물은 잡은 안 보인다) '이어 보기' 는 맡기기를 건너뛰고
그 잡의 진행부터 같은 패널로 본다 — 끝나면 넣고 **지금 대화**에 알림. 저절로 넣지 않는다(사람이 고른다). '숨기기' 는 목록에서만 뺀다(잡은 그대로).
③ 잡 기록을 스테이징 청소(6시간)에서 빼고 `docforge_job_days`(7 — DocForge 잡 보존 기한과 같게) 뒤 지운다. 6시간이면 다음 날 돌아온 사람은 기록이
없어 다시 열 수 없다 · 7일이 지나면 DocForge 가 패키지를 지워(410) 열어도 넣을 것이 없다.

**DF-D24 RA 요청서 — 엔티티는 RA 자동 태깅을 길로(2026-10-27, DocForge E17 · [ra-requests.md](ra-requests.md)).** RA v0.167.0 을 읽어 확인한 것 —
① `__import_blank__` 은 PPTX 가져오기가 처음 불릴 때만 생기고 바깥에서 만들 길이 없다(새 RA 의 첫 배달 400) → 시드 요청(R1). ② 보고서와 파일을 한 번에
만드는 창구도 엄격 생성의 검증만(dry_run)도 없어 거절된 배달의 파일이 고아로 남는다(밤 청소 48시간 · 타이머가 깔린 박스만) → R2. ③ RA 는 **모든 저장**
(API 생성 포함)에서 본문에 엔티티의 값 · 코드 · 별칭이 글자 그대로 나오면 엔티티를 붙인다(자동 태깅). 그래서 `entity_ids` 를 우리가 고르는 길(§12-10 의
처음 생각)보다, RA 가 SP key 를 엔티티 `code`(또는 별칭)로 두고 DocForge 의 '연결된 과제 · 모델' 칸(지금 key)이 그것을 걸게 하는 쪽이 짓는 것도
틀릴 곳도 적다 → R3(축 · 유일성 · 외부 키를 RA 가 정한다). key_value `meta.is_entity_id` 는 읽는 잡이 없어 쓰지 않는다. ④ 파일 상한은 확장자로만 갈려
Office · PDF 는 25MB → R4. ⑤ `create_report` 는 `entity_ids` 를 커밋 뒤에 검증한다(틀린 id 면 400 인데 보고서는 남는다) — 우리는 보내지 않는다(R5).
요청서를 RA 쪽에 건네는 것은 사람 몫이다.
