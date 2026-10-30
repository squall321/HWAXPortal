# 문서 → RA 정밀 변환 — 조사 근거 (2026-10-24, 읽기만)

> 계획 [PLAN.md](PLAN.md). 다섯 리포를 읽기만 했다(쓰기 · 커밋 0). 경로는 `/home/koopark/claude/` 아래 리포 기준이고 줄 번호는 이날의 판이다 —
> 구현 때 다시 대조한다(줄 번호는 낡는다).

## 1. Report Archive(RA) — 목표 형식과 넣는 길

키 파일(`ReportArchive/backend/app/` 아래) — `modules/reports/{schemas,models,services,ai_authoring,routes}.py` · `widgets/{registry,validation}.py` ·
`modules/imports/{routes,pptx_parser}.py` · `modules/files/{routes,services,models}.py` · `modules/entities/models.py` · `mcp_server/server.py`(리포 루트) ·
화면 `frontend/src/modules/reports/ReportDetailPage.jsx`(RDP).

### 1-1. 보고서 · 쪽
- 보고서 ORM `models:70-346`, `pages` 는 JSONB(`:183`). 쓸 수 있는 칸은 `ReportCreate`(`schemas:455-508`).
  - `template_id` · `template_version` 은 `pages[0]` 의 것과 같아야 한다(`services:1264-1275`).
  - `title`(1–255) · `report_date` · `tags[]` · `pages[]` · `report_type_id` · `entity_ids` · `collab_workspace_slugs`.
  - 쪽 설정 `page_width_px`(320–3000) · `page_gap_px`(0–200) · `page_blend_blocks` · `page_slide_guide` · `page_slide_ratio`(16:9 · 4:3 · 16:10 · custom) —
    슬라이드 비율은 점선 안내선일 뿐 캔버스가 아니다(`schemas:290-297`).
  - 최상위 `content` · `layout_overrides` · `props_overrides` 는 0쪽의 옛 사본이다(`:243-245`). `revision` 은 낙관적 동시성 표지(PATCH 의 `expected_revision`).
- ReportPage(`schemas:178-235`) — `template_id` · `template_version` · `name`(≤120) · `content`(블록 id → 내용) · `layout_overrides` · `props_overrides` ·
  `extra_blocks:[{id, type, props, layout?}]` · `blocks_order`(정본 — 목록에 없는 템플릿 블록은 숨는다) · `block_sections` · `block_updated_at`(서버가 찍는다).
- 템플릿 스키마 `{"version":"widget-v1","blocks":[…]}`(`validation:23, 101-180`).
- 저장 검증(`validation:361-441, 533-555` · `services:1103-1150`) — 내용 키는 템플릿이나 extra 블록 id 여야 하고, 블록마다 `content_schema_for(props+override)`
  (Draft7)로 본다. 부분 내용은 된다. extra 블록은 id · type 유일성만 보고 props 는 `props_schema` 로 안 본다. id 정규식 `^[a-z][a-z0-9_]{0,63}$` 은 템플릿 블록에만.
- 배치 — 그릇 위젯이 없다. 블록마다 `{row≥1*, col_span 1–12*, row_span≥1, auto_fit, col_offset 0–11}`(* 필수 · 추가 칸 금지, `validation:27-53`), 한 행 col_span
  합 ≤ 12(`:250-273`). 실제 배치는 `layout_overrides[id] ?? block.layout`(RDP `:9610`). `row` 는 논리 행이고 `row_span` 1 = 8px
  (`frontend/src/shared/reports/reportLayout.js:11`) + `page_gap_px`. 절대 좌표 없음.

### 1-2. 위젯(40종, `registry:4255-4299` — 전부 추가 칸 금지, 대부분 `caption` · `caption_html` · `caption_color` · `caption_position` 공유)
- `heading`(`:374-429`) props `level` 1~3 · 내용 `{text*≤200, text_html, level, bg_color}`.
- `rich_text`(`:439-536`) `{items:[{depth 0–5, text*≤2000, html≤8000, relation}], markdown(옛), outline_numbering, hide_prefix}`. 줄마다 TipTap HTML(`html`)과
  같은 글(`text`). 허용 태그 `p span strong em u s del br a sup sub`, 속성 `style class href data-mention-*`(`frontend/.../widgets/RichText.jsx:40-66`).
  색은 토큰 클래스 `rt-c-{token}`(`registry:144-150`). 옛 `markdown` 은 줄로만 나뉘고 인라인 서식은 안 그려진다.
- `bulleted_list` `{items:[str]}` · `key_value`(`:547-610`) `{items:[{key,label,type}], <key>: 값}`.
- `table`(`:662-791`) props `columns*[{key,label,type∈text|number|integer|date|select,options}]` · 내용 `{columns?, rows:[{열키: 값}], merges:[{r,c,rs,cs}],
  cell_styles{"r::key":{bg,fg,size,align,valign}}, cell_html, header{row_count,cells,merges}, column_widths, note, bordered, border_width 1–3}`.
- `chart`(`:1508-1744`) props `chart_type*` ∈ {bar, line} · `x_column_key*` · `columns*`(≥2 · x 밖은 전부 number) · 내용 `{rows, chart_type, x/y_axis_title,
  y_min/max, visible_series, annotations}`. 원형 · 분산형은 따로 `pie` · `scatter`.
- `image`(`:1164-1236`) props `max_count*` · 내용 `{files:[{file_id*, caption, alt}], aspect_ratio "W:H"}`(`filename` 칸은 거절).
  `attachment` `{files:[{file_id*, filename*, size}]}` · `video` · `doc_viewer` `{file_id, page_count, extracted_text}` · `html_embed` · `card` · `equation` `{latex}`.
- 그 밖 pie · scatter · heatmap · tree · network · sankey · comparison · raci_matrix · fmea · cad_3d 등.

### 1-3. 리소스
- `POST /api/files`(multipart `file`) → `FileMeta{id, filename, mime_type, size, is_image, …}`(`files/routes:170-189`) · `/api/files/from-url` · 업로드 티켓 길
  (`:192-253`) · `/api/files/{id}/extract-images`(pptx 에서 그림 꺼내기, ≤300장) · `GET /api/files/{id}`.
- 저장 `{upload_dir}/{yyyymm}/{uuid}{ext}` · id 는 UUID. 크기 기본 25MB · CAD 200MB · 동영상 1GB(`backend/app/config.py:121-135`). MCP base64 올리기는 256KB.
  서버 쪽 MIME 허용 목록은 없다. 블록은 `*file_id` 칸으로만 가리키고, 안 쓰인 파일은 유예 뒤 지운다(`files/orphans.py`).

### 1-4. 넣는 길
- **엄격 `POST /api/reports`**(`routes:2733-2756`) — 검증만 하고 고치지 않는다. `personal-{uid}` 에 만든다. 배치를 준 그대로 지키는 유일한 길.
- **편집기 JSON 가져오기** `{"_type":"report_archive_draft_v1", title, report_date, tags, pages[]}`(RDP `:3582-3606, 10293-10302`) — `TEMPLATE_ID_HERE` 면
  템플릿을 고르게 한다. 배치 없는 차트형 위젯은 반폭으로 깐다.
- **PPTX `POST /api/imports/pptx`**(`imports/routes:76-158`) — python-pptx 1.0.2 · openpyxl. 슬라이드 하나가 쪽 하나. 묶음은 펼치고 위 → 왼쪽 순.
  제목 개체 → heading 1 · 글 → rich_text(깊이만 · 서식 버림) · 표는 첫 행 머리 · 키 `col_N` · 전부 text · 병합은 복제. 그림은 그대로(EMF 포함) · alt 는 도형 이름.
  박힌 xlsx 표(≤500행). 경고와 함께 버림 — 차트 · SmartArt. 말없이 버림 — 노트 · 링크 · 위치 · 크기(전폭 세로 쌓기). 템플릿 `__import_blank__`@1.
  출력 `{draft:{_type, title, pages}, warnings}` · 블록 id `imp_{p}_{n}` · 보고서는 안 만든다.
- **AI 초안 `POST /api/reports/ai-draft`**(`routes:836-944`) = MCP `create_report_draft`(`mcp:2198-2251`). 입력 `AiDraftCreate`(`schemas:811-838`) — 내용은
  `extra_blocks` 항목 안. 기본 props 채움 · 준 layout 버림 · 빈 블록 건너뜀 · 자동 배치(`ai_authoring:1245-1279, 1120-1220`). 고칠 때 `PATCH …/ai-draft`.
- DOCX · XLSX · PDF 변환기는 없다(python-docx 는 의존성에만 · `docs/[일부] 문서가져오기_설계.md:13-19, 132-197`). PDF 는 doc_viewer 로 저장만.
- LLM — 글만 받는 클라이언트(`backend/app/ai/llm.py`, 기본 mock). 그림을 모델에 보내는 곳은 없다.

### 1-5. 검증 자료 · 판
- 정적 OpenAPI · JSON Schema 파일 없음 — 실행 중 `/api/openapi.json` · `GET /api/widgets`(`schema_version` · props 스키마). 내용 스키마는 파이썬 함수
  (`app.widgets` 는 jsonschema 에만 기대 — 읽기만 할 것, 리포는 고치지 않는다).
- 예제 — `report_578_platform_guide.json`(5쪽 · 위젯 10종 · 옛 markdown) · `backend/app/widgets/authoring_rules.json`(40종 props · 내용 예 — MCP 와 화면이
  읽는다, 스키마와 두 곳 어긋남 — html_embed `{url}` 은 거절 · table `border_width` 상한 3) · `backend/tests/test_import_pptx.py` · `test_ai_authoring.py:285-356`.
- 판 — 템플릿 `widget-v1` · 가져오기 `_type` · 보고서별 스키마 판은 없다. 쪽 안 칸(`extra_blocks` 등)은 마이그레이션 없이 늘었다. 현재 v0.167.0.

### 1-6. RA 엔티티(자체 온톨로지, `modules/entities/models.py`)
- 축(`entity_types`, 화면 용어 '타입') 7 — 모델명 · 부품명 · BOM Code · 개발 단계 · 불량 종류 · 신뢰성 시험 · 시뮬레이션 종류. 값(`entities`, '객체')은 누구나
  더할 수 있다. 보고서와는 `report_entities`(M:N). 별칭 `entity_aliases` · 관계 `relation_types` · `entity_relations` · 속성 `property_defs`.
- `ObjectLink`(`:535`) — 엔티티 ↔ 시스템 객체(부서 = workspace 등) 링크, 근거 보고서 · 메모.
- `EntityTagSuggestion`(`:578`) — 자동 태깅 제안 큐. 확실한 것(source=deterministic — 정식명 · 코드가 글자 그대로)은 바로 accepted, 애매한 유사도 제안은
  pending 으로 사람이 수락 · 기각. 그래프 · 객체 프로필 · GraphRAG · MCP resolve 가 이 태그를 전제로 한다.

## 2. 지금 변환 · VLM 경로

### 2-1. AIDataHub `convert_file`
- MCP 도구 `api_server/src/api/mcp_runtime.py:1375-1399` → `services/mcp_write_svc.py:415-488`(`run_convert`). `AIDH_CONVERT_INBOX`(기본 `~/aidh-inbox`)
  밑만 읽는다. 결과 `{status, format, record, note}`. 출력 폴더 없이 만들어 뽑은 그림이 `tempfile.mkdtemp` 에 남고 돌려주지도 지우지도 않는다
  (`converter_dispatch.py:109-115`).
- 라이브러리 — python-docx · openpyxl(`data_only=True` — 수식 없이 캐시 값만) · python-pptx · pypdf · pdfplumber · markdown-it-py · (선택) pytesseract + pdf2image
  (`requirements.txt` 에서 주석). LibreOffice 는 글에만 나온다(EMF → PNG).
- record — `schema_version, meta, toc, sections, figures, tables, sources, attachments`(+ warnings) · 절 `{id, level, title, blocks, figure_refs, table_refs,
  children}` · 블록 `paragraph | code | table | figure | list_item` · 그림 `{id, number, caption, section_ref, image_path?}`(`converter/models.py`).
- PPTX — 슬라이드 = 절 · 도형 순서 · 좌표 없음 · 노트는 `[Speaker Notes]` 표시 뒤 · 그림은 Figure + Attachment(캡션은 alt 나 이웃 글상자 추정) · 차트는 그림 자리
  + 계열 → 표 + Attachment(그리지 않는다) · OLE · SmartArt 없음. XLSX — 시트마다 `data.v1`, 차트 · 그림 버림. 그림 내용은 늘 자리만.

### 2-2. VLM(HWAXAgentServer)
- `vision.py:29-35` — `VISION_MAX_IMAGES` 12 · `VISION_MAX_BYTES` 8MiB · `VISION_HISTORY_IMAGES` 6 · `VISION_TRANSCRIBE_MAX` 8 · 동시 4 · 탐침 한도 120초.
- 그림 조각 `{"type":"image_url","image_url":{"url":"data:<mime>;base64,…"}}`(`:126-150`), 줄이지 않는다. 마법 바이트로 형식 확인.
- 탐침(`:165-209`) — 빨간 PNG · `max_tokens:1` · 생각 끔. 200 = 받는다 · 그림을 말하는 400/422 = 못 받는다 · 그 밖 = 모름(60초 뒤 다시). 손잡이
  `CHAT_LLM_VISION` / `LLM_VISION` = auto · 1 · 0(`app.py:422-443`).
- 판독 지시(`:240-244`) — 공학 그림 판독자 · 지어내지 않는다 · ① 그림 종류 ② 축 · 단위 · 범위 ③ 범례 · 컬러바 ④ 읽히는 수치 전부(최대 · 최소 · 위치 · 표 칸)
  ⑤ 글은 그대로 · 못 읽으면 「판독 불가」 · 선택 `맥락:` 단서.
- `transcribe()`(`:253-279`) — LangChain `ainvoke` · 생각 끔 · `<ARTIFACT_DIR>/.transcripts/<sha256>.txt` 캐시 · 실패면 빈 글.
- 판독 모델(`_transcriber`, `app.py:446-454`) — 챗 LLM(`CHAT_LLM_*` — cae00 은 stcx Qwen3.8-Flash-Next)이 탐침을 통과하면 그것, 아니면 `VLLM_*`(GLM), 아니면 없음.
- PaperAuthor — `claude -p`(Read 도구가 PDF 쪽을 그림으로) · dev 전용. PaperIngest 는 PyMuPDF 글만.

### 2-3. 포털 업로드 · PC 도우미
- 목적지(`backend/app/agent/upload.py:27-73`) — `chat`(pptx · docx · pdf · xlsx, AIDH 권한) · `reportarchive`(pptx 만).
- `reportarchive` 보내기(`routes.py:1256-1343`) — RA `/api/imports/pptx` → `ra_import_pages_to_ai`(내용을 블록 안으로 · 배치 버림) → MCP `create_report_draft`
  (템플릿 `__import_blank__` v1).
- `chat`(`routes.py:1345-1367`) — inbox 에 복사 → `convert_file` → 복사본 삭제 → `record_markdown` → `{doc:{name:"<stem>.hwax.md", text, chars}}`, 저장 없음.
- PC 도우미(`frontend/public/doc-extract/hwax-doc-extract.ps1`) — `hwax-doc/1` · Word · PPT · PDF · HTML(Excel 없음) · `MaxChars` 2,000,000 ·
  PowerPoint COM — 묶음 포함 모든 도형 글 · 표는 마크다운 · TextFrame2 로 SmartArt · 차트 제목 · 노트 `> 발표자 노트:` · 슬라이드 머리 `## [s.N]` ·
  슬라이드 PNG `Slide.Export(…,'PNG',1280,…)`(앞 SlideMax 장 · DRM 이 막으면 경고만) · 차트 값 · 박힌 그림 없음 · PDF 는 Word 재배열로 읽는다.
  머리말 칸 `schema, source, kind, bytes, sha256, extracted_at, extracted_by, units, chars, truncated` + 추출 경고.
- `pc_upload.py:24-30` — 표 유효 600초 · 사람당 열린 표 5 · 글 8MiB · 슬라이드 12장 · 장당 8MiB. 원본 파일은 받지 않는다.

### 2-4. 있는 것 · 없는 것
- 어디에도 없음 — pydantic-ai · instructor · docling · markitdown · unstructured · easyocr · rapidocr · paddleocr.
- Tesseract · pdftoppm · LibreOffice(`soffice`)는 dev 호스트에만(어느 SIF · 틀에도 없다). pymupdf 는 PaperIngest. 에이전트 서버 venv 에는 openai 2.42 ·
  pydantic 2.12 · langchain_openai · langgraph(구조화 출력은 안 쓴다).

### 2-5. HEAX Hub 앱 바탕
- 틀(`HEAXHub/backend/app/services/sif_templates/`) — fastapi · fastapi_react · flask · streamlit · python_cli 등 15. `fastapi.def` 는 `python:3.12-slim` +
  `pip install -e`, 무거운 것은 `scripts/heaxhub-build.sh`. 굵은 SIF 는 온라인 박스에서 지어 `dist-to-drive` 로(선례 `voice-recorder.sif` 5.2GB · torch).
- 바탕 이미지 `config/base_images.yaml` → `~/serviceApptainers/base_*.sif`, CUDA 바탕 없음.
- 매니페스트 예 `paper-ingest/.portal/manifest.yaml` — `build:{type:python_venv, stack:fastapi}` · `resources:{cpu, memory_gb, gpu:true}` ·
  `mcp:{expose:true, path:/mcp, transport:streamable_http}`(스키마 `schemas/manifest.schema.v2.json:260-280`). GPU 는 `/dev/nvidia*` 가 있을 때만 `--nv`.
- 폐쇄망 — `_BUILD_ENV_MAP`(`integration_sif_builder.py:122-162`)이 `BUILD_PIP_INDEX_URL` 등을 `%post` 에 넣는다 · 휠 거울(`build-requirements.txt` →
  `mirror-to-drive.sh` → `var/pkg-mirror/pip/`)은 지금 비었다 · 모델은 틀이 없다(선례 `AIDataHub/deploy/apptainer/model-to-drive.sh` — HF 캐시 tar → Drive).
- 앱 SIF 를 Drive 에 몇 개만 올릴 때는 `latest/SHA256SUMS` 를 합쳐 맨 끝에 올린다(cae00 이 대조하고 멈춘다 — 10-24 실제로 밟음).

## 3. StandardPlatform(SP) · StepForge

- `StepForge/docs/STANDARD_PLATFORM.md` — SP 는 도메인이 빈 사내 공통 틀(FastAPI · SQLAlchemy · **PostgreSQL 16** · React · MCP 76도구, 판 0.4.52 ·
  커밋 `f7485c0`). 온톨로지 엔진 `object_types` · `property_defs` · `relation_types` · 범용 `objects`(key · label · properties JSONB · previous_keys · 별칭).
- 과제 정보 — `plm_project` · `plm_task`(key = 과제코드 · label = 과제명 · project · task_status · test_site · test_kind …) · `plm_model`(key = 모델명 원문 ·
  task · 모델명 해석 base_code · series · region · model_revision …) · 관계 `plm_derived_from` · 담당 부서 · 담당자 · 참여는 관계(`work-core.json`).
  > 10-31 정정(cae00 HH-03 · DocForge R-D48) — 위는 SP `f7485c0` 의 정의다. 실제 공개(rootdesign)는 `plm_task` 의 key 가 **과제명**이고 과제코드는
  > `properties.task_code`(별칭은 `properties.aliases`), 관계는 `plm_project` 의 `compare_baseline` · `predecessor` · `predecessor_by_name` 셋뿐, 타입은 35종쯤이다.
- 받는 길 — 허브의 Core API(`GET /api/core` 카탈로그 · `/api/core/{type}?since=&cursor=` · `/relations` · 토큰 범위 `core:read`). 수신 키트
  `backend/app/modules/coreapi/kit/sp_core_pull.py`(requests + sqlite3 · 증분 · 삭제 · reset) · 수신 규칙 열하나.
- StepForge 가 한 것 — 키트를 `core/sp_core.py` 로 옮김 · 자체 정의 `core/data/ontology/stepforge-core.json`(SP 정의 꼴 — `cad_revision` · `revision_of` ·
  `supersedes` · `same_part_as`) · SQLite 표 넷(`onto_types` · `onto_objects` · `onto_relations` · `onto_sync_state`) · MCP `find_plm_task` 등.
  남은 것 — **cae00 SP 허브에 붙여 한 번 받기(주소 · `core:read` 토큰 — 사람)**.
- `GalaxyOntology` 리포는 이 일과 무관하다(폰 · 탭 · 버즈 신호로 사용자 맥락을 찾는 기기 온톨로지).

## 4. 바깥 도구(웹, 2026-10-24 확인)

- Docling 2.95.0(2026-05-21) — PDF · DOCX · PPTX · XLSX · HTML · 그림 등을 읽고 사내망만으로 돈다. VLM 길은 로컬 모델과 원격(vLLM · Ollama)을 둔다.
  그림 설명을 원격 VLM 으로 하는 설정은 이번에 문서로 확인하지 못했다(M0 에서 실측). 출처 — [PyPI 거울](https://simple-repository.app.cern.ch/project/docling) ·
  [VLM 안내](https://www.mintlify.com/docling-project/docling/guides/vlm-models) · [2026 발표](https://opensource.siemens.com/events/2026/slides/Panos_Vagenas__Docling_The_Open-Source_Document_AI_Engine.pdf).
- Pydantic AI — 출력 재시도(`NativeOutput` · `PromptedOutput` · `ToolOutput`)와 HTTP 재시도가 따로다. OpenAI 호환 끝점에서 `NativeOutput` 이 json_schema 로 나간다는
  사용자 실험은 있으나 vLLM 에서의 확인은 못 찾았다(M0 에서 실측). 출처 — [재시도 문서](https://pydantic.dev/docs/ai/core-concepts/retries/index.md) ·
  [OpenAI 호환 끝점 실험](https://dev.to/kasir-barati/does-pydantic-ais-structured-output-api-actually-work-against-ollamas-openai-compatible-endpoint-44aa).
