# 심의 도구 유의미화 계획 — StepForge·DynaForge·엔진 배선

2026-09-02 솔더볼 심의 실주행(21석 6라운드, 도구 728회)과 75-에이전트 감사
(wf_5f2384ac — 절단 사냥 5축 + 도구 격차 3축 + 적대 검증 + 완결성 비판)의 산출이다.
가치 기준은 하나 — **"이번 심의의 실제 미결('조회 못함·0일차 항목')을 닫았을 것인가."**
가설적 유용성은 배제했다.

## 이미 반영된 것 (2026-09-02)

| 항목 | 커밋 |
|---|---|
| 읽기 도구 31종 사전 허용(순위 2 전반부) | HWAXPortal 5a5098d |
| 엔진 _FREE_ALLOW 구멍 6종(순위 2 일부) — export_dyna_cards 는 쓰기 여부 미확인이라 보류 | HWAXAgentServer 925953e |
| 게이트웨이 읽기 캐시 + 쓰기 deny(report_ingest·report_fragmentize) | HWAXMcpGateway b80ed52·이번 |
| get_context_bundle 라운드 재조회 억제(§배선 6) | HWAXPortal 6701559 |
| R3 스키마 description(§배선 5 의 원인 제거) | HWAXPortal 5753104 |
| get_section↔get_record_sections 설명 경계(§배선 2 의 완화) | MXWP d723105 · AIDH 58f03b6 |
| 절단·유실 감사 확정분 — 워크플로 19건·엔진 12건·경계 3건 | bccdc9b·08ae2fe·8e690e3·3b26712 |

아래 표의 "완료" 표기는 위와 겹치는 자리다. 나머지는 **각 앱 리포의 작업**이며,
DynaForge(KooRemapper)는 미커밋 작업 25파일이 있어 정리 전 구현 착수 금지 — spec 까지만.

---

# 도구 제안 종합 — 우선순위 표

세 분석(gap-run·gap-stepforge·gap-dynaforge)의 21건을 병합해 17건으로 정리했다. 병합 2건 — ① 라이선스 조회(gap-run `license_status` + gap-dynaforge `license_seats` → 동일 서버·동일 목적), ② LS-DYNA 키워드 지식(gap-run `lsdyna_keyword` + gap-dynaforge `mat_model_lookup` → 같은 미결을 닫는 두 구현안을 단계화). 가치 판단은 "이번 솔더볼 심의의 실제 미결을 닫았을 것인가" 기준으로 재채점했다.

| 순위 | 도구 | 앱 | 유형 | effort | value | 닫는 실제 미결 | 출처 |
|---|---|---|---|---|---|---|---|
| 1 | `license_status` | STC/SmartTwinMCP (:5012) | 신규 | 소 | high | implicit 좌석 수 — 좌석 1이면 직렬 시간이 곧 일정 | run+dynaforge 병합 |
| 2 | 읽기전용 사전허용 + 좌석 화이트리스트 | 게이트웨이/심의 엔진 | 정책 | 소 | high | 차단 304회·get_context_bundle 96/97 차단이 만든 근거 결손 | run+stepforge 병합, §엔진 배선 참조 |
| 3 | `pipeline_status` | StepForge | 신규 | 소 | high | 계면 검출 여부·진행 단계 — 에러 시행착오 역추정 제거 | stepforge |
| 4 | `search_reports` | DynaForge | 신규 | 소 | high | 과거 유사 해석 유무 — user_id 스코프 빈 배열 오독 해소 | dynaforge |
| 5 | LS-DYNA 키워드/재료모델 조회 (`mat_model_lookup` → `lsdyna_keyword`) | DynaForge 1차, KooDynaAdvanced 2차 | 신규 | 중 | high | 크리프 *MAT 번호·ELFORM·아워글래스·이력변수 인덱스 — 3세션 연속 회수 실패, 잠금조항을 게이트로 복원 | run+dynaforge 병합 |
| 6 | `fetch_source_document` | AIDataHub | 신규 | 중 | high | Motalab K1·K2 규약, Darveaux 1층/3층 — tier 1 등급 승계가 걸린 문서 조회 | run |
| 7 | `search_assets` | StepForge | 신규 | 중 | high | 사내 지오메트리 자산 유무 — N+1 순회 제거 | stepforge |
| 8 | `mesh_report` 확장 (min_edge·Δt) | StepForge | 확장 | 중 | high | 최소 특성길이→명시적 타임스텝 | stepforge |
| 9 | `lab_channel_registry` | AIDataHub | 신규 | 소 | medium | 외주 4채널 리드타임·원가 — 6라운드 미계상 임계경로 | run |
| 10 | `postproc_capabilities` | KooD3plotReader | 신규 | 소 | medium | 레벨셋 V_avg 부분체적 구적 지원 여부 | run |
| 11 | 설명 개선 묶음 | StepForge·DynaForge | 설명만 | 소 | medium | 미결 직접 닫진 않으나 노이즈 원천 제거 | stepforge+dynaforge, §설명 개선 참조 |
| 12 | `dataset_design_matrix` | AIDataHub | 신규 | 중 | medium | 미결 아님 — 수작업 26콜로 이미 답한 계산의 재사용화 | run |
| 13 | `template_deck_inventory` | DynaForge | 신규 | 중 | medium | 물리별 사내 템플릿 덱 유무 — 단 태깅 운영이 본체 | dynaforge |
| 14 | `deck_lint` | DynaForge | 신규 | 중 | medium | 덱 카드 유효성 1차 정적 검증 — #5 인덱스 재사용처 | dynaforge |
| 15 | `test_asset_inventory` | AIDataHub | 신규 | 대 | medium | 기존 시험 자산 재고 — 경로 γ 가부 | run |
| 16 | `extract_parts` | StepForge | 신규(잡) | 대 | medium | 서브어셈블리 추출 가능성 | stepforge |
| 17 | 공정 사양/도금·리플로우 이력 조회 | (신규 원장 필요) | 미배정 | 대 | medium | M10 4항·공정점 5숫자 — 원장 자체가 부재, 도구보다 데이터 소유부서 협의가 선행 | run(미결만 있고 제안 없음, 명시적 기록) |

---

## 신규 도구 spec

**1. `license_status` (STC MCP :5012, 병합)** — 무인자(또는 feature명 옵션) 읽기 도구. stc 헤드노드에서 `lstc_qrun -s`/`lmstat -a`를 라이선스 서버(10.228.132.74:31010)로 쏘아 프로그램별(MPP/SMP) 총 좌석·사용 중·가용·점유 잡 목록을 반환. 기존 slurm_* 와 같은 ssh 경로라 신규 배선 없음, `slurm_cluster_health` 패턴으로 함수 하나 추가. gap-dynaforge의 정직한 한계를 채택한다 — LS-DYNA 라이선스는 implicit/explicit 좌석이 분리되지 않은 코어 기반일 수 있으므로, 도구는 실제 라이선스 모델을 그대로 보여주고 심의가 질문을 교정하게 한다. `_FREE_ALLOW` 등재 필수.

**3. `pipeline_status` (StepForge)** — 입력 project_id. 단계별(parse/detect/mesh/export/cavity) 최근 잡 status·finished_at, 산출물 유무(tree.json·graph.json·mesh_report.json), interfaces의 kind×status(auto/confirmed/manual) 이중 집계, part_mesh 상태 집계, step_files 등록 시각 대비 stale 플래그. jobs·interfaces·part_mesh 표 조회+파일 존재 확인뿐이라 `app/mcp_server.py` ANALYSIS 등록 하나로 끝. "auto인가 confirmed인가" 미결도 이 도구의 이중 집계가 함께 닫는다.

**4. `search_reports` (DynaForge)** — 입력 query(프로젝트/라벨/파트 키워드)·kind?·scope?(mine|org). mine은 report_id·session·kind·케이스 수·전역 최악값 목록, org는 개인 식별 없는 집계(매칭 수·kind 분포)만 — corpus 층의 기존 프라이버시 선 유지. 이미 인제스트된 reports 테이블 LIKE/FTS 백엔드 1개+MCP 도구 1개. 부속으로 report_* 독스트링에 "user_id 스코프" 한 줄 추가(§설명 개선).

**5. LS-DYNA 키워드/재료모델 조회 (병합, 2단계)** — 1차는 gap-dynaforge 안. `mat_index.json`(Keyword Manual Vol II 재료 목차 ~300 카드를 번호·이름·물리 태그로 큐레이션)을 DynaForge에 얹어 `mat_model_lookup`으로 노출 — 입력 자유텍스트('Anand')/카드명/물리 태그, 출력 MAT 번호·정식 카드명·태그·전사 사용 수·사내 물성 보유 여부. 2차는 gap-run 안 — Keyword Manual 원문(Vol I/II)을 카드 단위로 파싱·색인한 `lsdyna_keyword`를 KooDynaAdvanced에 얹어 필드 정의·기본값·판·권·절 좌표까지 반환(동일 상수의 전 출현 병기). 1차만으로 "카드가 있는가"는 닫히고, 잠금조항 게이트화(필드·이력변수 인덱스 인용)에는 2차가 필요하다. heax-hub manifest `mcp:{}`로 게이트웨이 자동 발견.

**6. `fetch_source_document` (AIDataHub)** — 입력 원장 set_id 또는 URL/record_id+자연어 질의, 출력 해당 절 원문 발췌·페이지 번호·표/그림 캡션(실패 시 '미수록' 명시). PaperIngest 하네스에 온디맨드 ingest(외부 URL은 relay 경유)와 페이지 좌표 보존 색인을 추가하고, `get_record_sections`가 못 하는 페이지 단위 정밀 인용을 별도 도구로 노출. 물성 원장에 source_url 필드가 이미 있어 조인은 공짜.

**7. `search_assets` (StepForge)** — 입력 query(글롭/키워드)+category?. 전 프로젝트 횡단으로 projects.name/purpose/code/note와 nodes.name을 검색, 프로젝트별 {project_id, name, purpose, 적중 파트(이름·bbox·분류), 진행 카운트}를 반환. `core.rules.glob_match`와 SQL 재사용, OCC 불필요, MAX_ROWS 규율 동일.

**8. `mesh_report` 확장 (StepForge)** — `core/meshing.py` `_quality()`에 최소 요소 변 길이(minEdge, gmsh getElementQualities) 추가, 응답에 판 전체 min_edge·추정 임계 Δt(사용자가 준 음속 c로만 계산, 없으면 min_edge만) 필드. 독스트링도 함께 — SICN·슬리버·min_volume이 이미 나온다는 사실이 좌석에게 보이도록 지표 이름과 용도를 명시.

**9. `lab_channel_registry` (AIDataHub)** — 입력 계측 채널명(염료침투/이온밀링 단면/FE-SEM+EDS/C-SAM). 출력 사내 보유 여부·외주 후보(업체·표준 리드타임·단가 자릿수·계약 상태). `instrument_summary`가 있는 장비 원장에 외주 채널 테이블 하나 추가. 초기 데이터는 구매·품질 스프레드시트 수십 행.

**10. `postproc_capabilities` (KooD3plotReader)** — 입력 기능 질의(부분체적 구적·PartSelector·지원 이력변수 인덱스·NEIPH 상한). 출력 지원 여부·버전·제약('슬롯은 있으나 솔버 미기록 시 0 반환' 경고 포함). `heaxkooremapper_mcp_system_capabilities`와 동일 패턴으로 빌드에서 기능 매니페스트 생성 — 코드가 아는 자기 능력을 선언으로.

**12. `dataset_design_matrix` (AIDataHub)** — 입력 dataset id+축 목록. 출력 축별 수준 분포·축쌍 교차표·앨리어싱/교락 플래그(단일 프로젝트 블록 검출)·비대각 결손 칸. `get_dataset_summary` 옆 pandas 크로스탭 수준 엔드포인트. 이번 심의 최대급 발견(표본 설계가 대리모델 퇴화의 원인)이 이 계산이라 재사용 가치는 검증됐으나, 미결을 닫는 게 아니라 26콜 노이즈를 1콜로 줄이는 것이므로 high 아래에 둔다.

**13. `template_deck_inventory` (DynaForge)** — 세션 meta에 is_template+physics_tags[]를 얹는 방식(`update_session` 확장)+태그된 세션의 캐시된 키워드 파싱을 롤업하는 GET /api/v1/templates. 초기 시딩(battery 프리셋·검증 덱) 없이는 심의에서 또 빈 배열 소음이 된다 — 도구보다 태깅 운영이 본체.

**14. `deck_lint` (DynaForge)** — 입력 session_id·file_id. 업로드 시 캐시되는 키워드 파싱을 #5 인덱스와 대조 — 인덱스에 없는/오타 의심 카드, 물리 태그 롤업, *CONTROL_IMPLICIT 유무. 1차는 *MAT+*CONTROL만. '이 버전 솔버가 받는다'는 정적으로 못 주며 진짜 dry-run은 stc(SmartTwin) 소관.

**15. `test_asset_inventory` (AIDataHub)** — 시험 캠페인 레코드 타입 신설+과거 시험 보고서 ingest. 출력 부품·조건·표본수·와이블 η/β·원시데이터 위치·recipe 메타 유무, '부품 종류·조건이 다른 최소 3~5 케이스' 판정 필드 내장. 도구 코드는 얇지만 데이터 수집·정규화가 본체라 effort 대.

**16. `extract_parts` (StepForge, 잡)** — 입력 parts 글롭 또는 container 서브트리, 출력 선택 파트만 담은 STEP artifacts(+as_project:true면 새 프로젝트 반입). XCAF 서브트리 추출의 변환·정의 공유 처리와 부피 보존 검산이 필요해 대. `core/export/`·`core/job_worker.py` 양쪽.

**17. 공정 사양/도금 이력 (미배정)** — gap-run 미결에 있으나 세 분석 모두 제안을 내지 못한 유일한 축. 도금 인 함량·금 두께·리플로우 횟수·리워크 이력은 조회할 원장 자체가 없다. 도구 설계 전에 공정/품질 부서의 데이터 소유·반출 협의가 선행돼야 하므로 이번 라운드 범위 밖으로 명시 이관.

---

## 설명만 고치면 되는 것 (코드 도구 신설 없음, 전부 effort 소)

| 대상 | 앱 | 수정 |
|---|---|---|
| `list_projects` | StepForge | SELECT에 code·owner·purpose 추가+독스트링 "사내 지오메트리 자산 목록 — 과제번호·목적·진행 카운트 포함. 훑는 첫 도구" |
| `inspect_report` | StepForge | 첫 줄 "CAD 위생 점검 — 메시 굽기 전 침투·단위 의심을 본다" |
| `mesh_size_advice` | StepForge | "store:false면 읽기 전용" 명시 또는 기본값 반전 — MODIFY 분류 기피 해소 |
| `view_3d` | StepForge | 첫 줄에 "사람용 브라우저 링크. 심의 좌석은 render_3d(이미지)를 쓸 것" |
| `report_*` 12종 | DynaForge | "reports는 user_id 스코프" 한 줄 — 빈 배열을 '전사에 없음'으로 오독하는 패턴 차단 |

`list_projects`만 SELECT 필드 추가가 섞여 있고 나머지는 순수 독스트링이다. 이 묶음은 반나절 작업으로 gap-stepforge 노이즈 5건 중 3건, gap-dynaforge 노이즈 1건의 원천을 제거한다.

---

## 심의 엔진 쪽 배선 (도구를 좌석에게 알려주는 일)

도구를 만드는 것과 좌석이 그것을 찾아 쓰는 것은 별개다. 이번 주행의 노이즈 상당수(728회 중 124회 중복, 차단 304회, 동명 도구 오호출, view_3d 오용)는 도구 부재가 아니라 배선 부재였다.

1. **사전허용 목록(`_FREE_ALLOW`) 등재** — 엔진이 이미 읽기 전용으로 판정한 25종+누락 7종(recommend_agents·instrument_summary·section_contact_usage·slurm_cluster_health·slurm_list_nodes·slurm_list_partitions·export_dyna_cards)을 settings 허용목록에 사전 등재해 auto-mode 모델 판정을 우회한다(사용자 승인 필요). 위 신규 도구 17건도 만들 때마다 여기 함께 등재하는 것을 체크리스트화 — 안 하면 2단 차단율 33.6%의 재연이다. get_context_bundle 96/97 차단이 그 증거다.

2. **좌석별 도구 노출 필터** — StepForge는 catalog의 ANALYSIS+VIEW 분류만, DynaForge는 쓰기/CRUD 13종 제외 목록을 심의 좌석에 준다. gap-stepforge가 제시한 좌석용 집합(진입 6·신원 7·계면 4·메시 4·재질 5·측정 7·그림 2·개정 1, MODIFY 22종·view_3d·system 3종 제외)을 hwax-deliberate의 도구 노출부에 반영. 326개 평면 네임스페이스의 동명 도구 오호출(N-4)도 좌석당 노출 수를 줄이면 구조적으로 완화된다.

3. **게이트웨이 캐시 운영 반영** — 인자 없는 전역 조회 중복 124회는 b80ed52로 사후 수리됐으나 재기동해야 반영된다. 신규 도구 추가 시에도 매번 API 재기동·erag 재색인·워크플로 sync가 필요하다(sim-deliberation spine 반영 절차와 동일).

4. **좌석 지식카드/whenToUse에 신규 도구 안내** — `search_reports`·`pipeline_status`·`mat_model_lookup` 류는 "언제 이걸 부르나"가 독스트링에 있어도 좌석 프롬프트에 진입 도구로 안내돼야 첫 라운드에 쓰인다. 특히 "코퍼스 사용 분포(material_usage)는 지원 여부의 부정 증거가 아니다 — 지원 여부는 mat_model_lookup으로" 같은 오용 교정 문구를 좌석 공통 지침에 넣는다.

5. **R3_SCHEMA 제출 검증 피드백** — final_position 필드 발명으로 좌석 2개가 동일하게 거부·재시도를 밟았다(N-5). 스키마 거부 응답에 허용 필드 목록을 되돌려주는 엔진 수정으로 왕복 1회를 0회로.

6. **불변 자기 지식카드 재조회 억제** — 같은 좌석이 라운드마다 자기 카드를 5~6회 재조회하는 패턴(N-10)은 엔진이 라운드 컨텍스트에 카드를 고정 주입하면 사라진다 — 도구 문제가 아니라 프롬프트 구성 문제.

---

# 완결성 비판 — 이번 감사가 못 본 것 (후속 원장)

아래는 비판자가 코드로 실증했거나 확인 방법까지 지정한 후속 항목이다. 1-B 는 즉시
수정했고(캐시 deny), 1-D 는 finish_reason 검출로 수정했다. 나머지는 미착수 원장이다.

## (1) 아무 감사자도 안 본 구간 — 8곳 확인, 그중 2곳은 코드로 실증함

**1-A. [실증] 게이트웨이 save_conversation 심이 메시지당 20,000자로 자른다 — "대화 저장소에 전문" 주장의 세 번째 붕괴 지점.**
`/home/koopark/claude/HWAXMcpGateway/gateway.py` L614: `"content": str(m.get("content") or "")[:20000]`, L634: `messages [:200]`, L631: `title [:200]`. 감사는 파이프라인 쪽 conv-save(hwax-deliberate.js 617~641)와 엔진 쪽만 봤는데, 그 사이의 게이트웨이 심이 포털 422 방어를 이유로 **모든 메시지를 20K에서 무표식 절단**한다. 즉 conv-save 가 성공해도 61,246자 결정문은 저장소에 33%만 남는다. 490~493행의 saveReport 기본 꺼짐 근거가 게이트웨이 층에서도 무너진다.
확인 방법: 25K자 메시지 1건으로 save_conversation 을 게이트웨이 경유 호출 → 포털 `/agent/conversations/{id}` 를 읽어 길이 비교. 단위로는 `_msg()` 에 25K 입력 후 len==20000 확인.

**1-B. [실증] 게이트웨이 캐시 — isError 만 거르고, `report_` 접두사가 쓰기 도구까지 캐시 대상으로 연다.**
`gateway.py` L102 `_CACHEABLE` 에 `"report_"` 가 있는데 도구 목록에는 `report_ingest`·`report_fragmentize`(쓰기)가 존재한다. TTL 300초 내 동일 인자 재호출은 **백엔드에 도달하지 않고 캐시 응답을 받는다** — 쓰기가 무음 드롭되고, `_cache_flush_backend` 도 안 탄다(캐시 대상 = 읽기로 간주되므로). 또 `_cache_put`(L159~161)은 `isError` 만 거른다 — 백엔드가 성공 프레임에 오류/부분 결과 텍스트를 담아 주면(agent-server `_call` 식 "(tool … error)" 패턴이 백엔드에도 흔함) 그 오염 결과가 300초 동안 **21석 전원에게 동일하게** 서빙된다. 좌석 교차검증이 무력화되는 상관 오염이라 단일 좌석 오류보다 질이 나쁘다.
확인 방법: (a) 게이트웨이 tools-map 에서 `report_`·`get_`·`list_` 접두사 도구 중 실제 쓰기인 것을 목록화, (b) `report_ingest` 를 같은 인자로 2회 연속 호출하고 audit.jsonl 에서 두 번째가 `cache-hit` 인지 확인, (c) 성공 프레임+오류 텍스트를 돌려주는 목 백엔드로 cache-hit 재현.

**1-C. SSE 생존 = 심의 생존 — 클라이언트 절단이 4시간 심의를 무저장으로 죽인다.**
`deliberation.py` 의 심의 전체가 `StreamingResponse` 제너레이터 안에서 돈다(app.py L2237). RA 저장(L2729)·tally·결정문 방출이 전부 **스트림 끝**에 있고 `asyncio.shield`/백그라운드 이관이 없다 — 브라우저 탭 닫힘, nginx `proxy_read_timeout`, 사내 프록시 idle 절단이 3라운드에서 나면 제너레이터가 취소되고 저장 0·로그는 취소 스택뿐이다. 질문의 "SSE 스트림 중단" 그대로이며 아무 발견도 이를 다루지 않았다.
확인 방법: 심의 시작 후 2라운드째에 `curl` 클라이언트를 kill → 서버 로그에서 이후 라운드 진행 여부·RA 저장 유무 확인. nginx 설정에서 해당 라우트의 read timeout 값도 함께 확인(`/home/koopark/claude/HWAXPortal/infra/nginx`).

**1-D. GLM 응답 자체의 max_tokens — `finish_reason` 을 아무도 안 읽는다.**
`deliberation.py` L1077~1079 `_llm_text` 는 `r.content` 만 반환하고 `finish_reason` 을 버린다. app.py L208 주석이 스스로 "2048~4096은 (위험)…8192급 권장"이라며 절단 가능성을 알면서, `finish_reason=="length"` 검출이 어디에도 없다 — 의장 결정문이 max_tokens 에서 문장 중간 절단돼도 정상 반환으로 흐른다. `_parse_json` 실패 시엔 감사 발견의 say[:800] 강등 경로로 떨어져 이중으로 숨는다. 워크플로 경로(agent())도 마찬가지로 하네스의 턴당 출력 상한을 계약으로만 믿는다.
확인 방법: `DELIB_MAX_TOKENS=300` 으로 1라운드 심의를 돌려 절단 발언이 무표식으로 통과하는지 관찰. 수리 검증은 `_llm_text` 에서 `r.response_metadata.get("finish_reason")` 로그 추가 후 재실행.

**1-E. 워크플로 경로의 Claude Code MCP 결과 상한.** hwax-deliberate.js 좌석은 Claude Code 서브에이전트로서 게이트웨이 MCP 를 직접 부른다 — 이 경로의 도구 결과는 agent-server 의 `_prep_tool` 이 아니라 **Claude Code 하네스의 MCP 출력 토큰 상한**(기본 25K 토큰)으로 잘린다. 두 엔진의 절단 정책이 다른데 어느 감사도 워크플로 쪽 도구결과 상한을 안 봤다.
확인 방법: 큰 `get_context_bundle` 결과(카드 대형 좌석)를 워크플로 좌석에서 호출해 전사에서 잘림 배너 유무 확인, `MAX_MCP_OUTPUT_TOKENS` 설정값 확인.

**1-F. 형제 파이프라인 2본 미감사.** `/home/koopark/claude/HWAXPortal/infra/pipeline/hwax-risk-review.js` 는 실증으로 `SAY_CAP` 절단(L87~89)·`TURN_CAP`(L94)·`MAX_PANELS`(L170)·오류 300자 절단(L209)이 있고, `hwax-test-plan.js` 와 `viz_module.py` 는 아예 안 열렸다. 특히 risk-review 는 risk_spec 을 원장에 기계 병합하는 경로라 절단이 원장 오염이 된다.
확인 방법: 두 파일에 동일 감사 프로토콜(slice/[:N] 전수 + null 경로 + 실측 규모 대입)을 적용.

**1-G. 저장소 수신측 상한.** RA `RA_PAGE_BUDGET` 은 파이프라인의 추정치일 뿐, RA API 의 실제 본문 상한·초과 시 응답(413/422/무음 절단)은 미확인. 포털 conversations 의 검증 상한(persona 120·content 20000)은 게이트웨이 주석으로만 알려져 있다.
확인 방법: RA `update_report_draft` 에 예산 초과 blocks 를 직접 POST 해 응답 코드·저장 상태 확인.

**1-H. agent() 하네스 자체.** "null 계약"·64K 출력 상한·`agent-*.jsonl` 복원 경로 전부 주석 전언이지 하네스 소스 검증이 아니다.
확인 방법: 워크플로 하네스 소스 위치 확인 후 반환값 조립부를 읽거나, 강제 장문 출력 합성 agent() 호출로 반환값 vs 전사 비교.

## (2) 기각 이유가 약한 것

전제: **기각 원장이 입력에 없다** — 확인된 발견만 받았다. 기각 목록 없이 기각 심사는 불가능하므로, 검증자에게 기각 항목+사유를 반출시켜 재심하라(방법: 각 기각 사유에 "이 기각을 뒤집을 구체 입력"을 요구하고, 실측 규모 — 결정문 61,246자·21석·6R — 를 대입해 재검).

다만 확인된 발견 **내부의 자기 기각(하향 판정)** 중 약한 것이 둘 있다.

**2-a. 발견 13-(2) "현재 주 소비는 결정문 반환값이라 실해 제한" — 약하다.** 3단 체인의 build-plan 항목 (2)가 "context 에 [2단 sim_spec] 기계판독 규격이 있으면 **재파싱 없이 정본으로 승계**"를 명시한다(hwax-deliberate.js CHAIR_ITEMS). 즉 ```json 펜스는 이미 기계 소비 대상이고, 2단→3단 승계가 `String(sim.decision).slice(0,20000)`(발견 16)을 지나므로 6만자급 결정문 후미의 sim_spec 펜스는 **절단 지점 뒤에 있어 통째 유실되거나 반쪽 펜스로 승계**된다. raSplit 펜스 쪼개짐과 결합하면 실해가 "제한"이 아니라 3단 퇴화의 직접 원인 후보다.
확인 방법: 실측 2단 결정문에서 sim_spec 펜스의 시작 오프셋을 재고 20,000과 비교. risk_spec 도 hwax-risk-review.js 의 원장 병합 경로에서 같은 검사.

**2-b. 발견 12 "실해 없음" — 절반만 맞다.** checkpoint positions 는 **사람이 이어하기 방향을 정하는 유일한 화면**이다(stopAfterRound 설계 목적). lens 폴백으로 얇아진 positions 는 사람의 개입 품질을 직접 깎는다 — 이 파이프라인 스스로 "가장 큰 품질 개선이 사람의 중간 개입"(주석)이라 했으므로, 실해 없음이 아니라 "개입 품질 저하"로 상향해야 한다.
확인 방법: stopAfterRound:1 실주행의 checkpoint 페이로드와 rounds 원본을 나란히 놓고 사람이 놓치는 정보량 비교.

## (3) "인용 강제" 방향 — 예, 구조적으로 빠져 있다

부르게 만드는 쪽은 겹겹이다(그라운딩 블록, risk 좌석 계약의 필수 도구, free_tools 예산, _asset_snapshot). 반대 방향의 검증은 단 두 개뿐이고 둘 다 부분적이다.

- `_verify_web_citations`(deliberation.py L1682, L2744~) — **[W:doc_id#n] 웹 인용만**, **챗 엔진 경로만**, 결과도 배너 첨부뿐. 도구 결과 수치·카드 인용·EV 항목은 대상이 아니다. 워크플로 경로엔 대응물이 0.
- `_quote_validator` — 좌석 간 **반박 인용**의 실재 검증이지 도구결과→결정문 검증이 아니고, 대조 원문 자체가 _SER_CLIP 700자 절단본이다(발견 25가 이미 지적).

구조적 공백 세 가지.
(a) **EV 항목에 id 가 없다** — hwax-deliberate.js EV_BLOCK 은 `[출처·도구]` 라벨뿐이라 의장에게 "[e:N] 을 인용하라"고 강제할 참조 체계 자체가 없다(risk-review 만 [c:]/[e:] 체계 보유).
(b) **의장은 도구 결과를 아예 못 본다** — 좌석의 도구 호출 결과는 summarize/allRoundsText 에서 탈락하고(감사 발견 6의 reads 유실이 정확히 이 채널의 죽음), 의장 프롬프트에는 EV_BLOCK(이미 3겹 절단)만 남는다. 인용을 강제해도 인용할 원문이 프롬프트에 없다.
(c) **(경험칙) 표기가 미검증** — 표기 지시만 있고, 표기 없는 무근거 수치를 잡는 후검증이 없다.

제안 + 확인 방법: EV 항목·도구 결과에 안정 id 를 부여하고, 결정문 생성 후 **결정적 후검증 패스**(LLM 아님)로 결정문의 수치·id 를 근거 저장분과 대조해 미대조 수치에 `[미대조]` 를 박는다. 검증은 카나리아로 한다 — evidence 한 항목에만 존재하는 고유 수치(예: 7371.3MPa)를 심어 심의를 돌리고, 결정문이 (i) 그 수치를 id 와 함께 인용하거나 (ii) 안 썼으면 후검증이 "근거 미인용 항목 N건"을 반환값에 싣는지 확인. 역카나리아(근거 어디에도 없는 수치가 결정문에 등장)도 같은 패스가 잡아야 한다 — 현재는 웹 인용 외엔 둘 다 안 잡힌다.

## 후속 상태 주석 (문서 작성 시점)

- **1-A** 게이트웨이 save_conversation content[:20000] — 워크플로·결정적 저장 스크립트가
  19,500자로 사전 분할하므로 실경로는 안전. 분할 없이 부르는 제3 호출자만 걸린다. 원장 유지.
- **1-B** 캐시 쓰기 접두사 — **수정 완료**(_CACHE_DENY, 단위 시험 통과). 오류-텍스트 캐시
  오염은 isError 만 거르는 한계로 남는다 — 백엔드가 성공 프레임에 오류 텍스트를 담는 사례가
  관측되면 그때 휴리스틱을 넣는다(지금 넣으면 오탐으로 정상 결과를 캐시에서 떨어뜨린다).
- **1-C** SSE 취소 = 심의 사망 — 포털 쪽 finally 가 부분 turns 는 저장하지만, 엔진의 RA
  저장·결정문은 스트림 꼬리라 유실된다. 근본 수리는 심의를 백그라운드 태스크로 옮기고
  SSE 는 구독만 하는 구조 변경 — 별도 작업으로 원장 유지.
- **1-D** finish_reason — **수정 완료**(_llm_text 검출 + 절단 표식).
- **1-E** 워크플로 좌석의 MCP 출력 상한 — **실측 종결(2026-09-03)**: 상한 초과 결과는
  무음 절단이 아니라 **파일로 우회 저장 + "전량 읽으라" 지시**가 좌석에게 간다(당일 실측
  3건: 159K/531K/665K자 search_voc·query_voc). 잔존 리스크는 좌석이 파일을 안 읽는
  행동 편차뿐 — 구조 결손 아님.
- **1-F** hwax-risk-review.js·hwax-test-plan.js·viz_module.py 미감사 — 같은 프로토콜로
  후속 감사 필요. risk-review 는 원장 병합 경로라 절단이 원장 오염이 된다.
- **1-G** RA 본문 상한 — **실측 종결(2026-09-03)**: rich_text **항목당 2,000자 하드
  상한, 초과는 명시적 스키마 거부**(무음 절단 아님 — 260K/100K/50K/20K/10K 전부 깨끗이
  거부됨). 파이프라인 raSplit(1900) 분할과 정합 — 주석이 사실로 확인됐다.
- **1-H** agent() 하네스 계약 — **부분 실측**: ADC12 실주행에서 전사(13,097자) ⊂ 반환
  결정문 재검증(무손실), null 계약은 종전 실측 유지. 64K 상한 수치만 미검증 원장.
- **2-a** sim_spec 펜스 승계 — parseSimSpec 이 전문에서 추출해 3단에 별도 주입하므로
  구조적으로 안전 확인. 추출 실패 시 무로그만 보완했다(퇴화 위험 경고 추가).
- **(3) 인용 강제 부재** — 정확한 지적. EV 항목 안정 id([e:N]) 부여 + 결정문 후검증
  패스(결정적, LLM 아님)는 **다음 라운드의 본 작업**으로 올린다. risk-review 의
  [c:]/[e:] 체계를 default 템플릿으로 일반화하는 방향.
