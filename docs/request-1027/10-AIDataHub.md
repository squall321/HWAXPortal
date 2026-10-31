# AIDataHub — 수정 요청 (2026-10-27 · cae00 운영 기준)


요청 HWAX Portal 운영(cae00) · 대상 저장소 AIDataHub(`api_server` · `config/sync_sources.yml` · `deploy/apptainer`) · 기준 판 `ac42bc6`(10-25 피드백의 `파일:줄` 기준, 10-27 cae00 도 같은 판) · `b401f88`(지식카드 요청의 `파일:줄`) · `57a5a4b`(10-17 수정 목록) · 심의엔진 · PPT 요청은 판 표기 없음 · update-all 로 받는 플랫폼: 예.


항목 번호 가운데 제품 코드처럼 읽힐 수 있는 것(S · A · M · X · P 로 시작하는 짧은 번호)은 원문 번호에 '-' 를 넣어 적었다(예 10-25 시험 M-14).


**한 줄**


- 정기 동기화 3곳(mxwp · signalforge-gs · materialtwin)이 SSRF 포트 가드에 막혀 10-01 부터 성공이 0건이다. 다시 켤지 끌지를 먼저 정해야 한다(AD-17). 두 문서의 권고가 맞선다.


- mx-whitepaper-analyst 카드 154장은 허브 안의 본문이 비었다. 동기화를 정한 뒤 사유를 보고 다시 받거나 내린다(AD-01).


- '이 대화에서 분석'(저장하지 않음)인데 변환기가 그림을 /tmp 에 남긴다. 포털은 '어디에도 저장하지 않았습니다' 라고 말한다(AD-02).


- DRM(NASCA) 문서를 변환에 넣으면 알아보지 못한다. 앞 바이트로 판정해 따로 알린다(AD-03).


- 빈 전문가 둘(dynaforge-report · kooremapper-modelmeta)을 정리한다. KooRemapper 쪽 전제(`826054f` · `6d63038`)는 10-27 cae00 판에 들어 있다(AD-05 · AD-06).


**건수**


| 높음 | 중간 | 낮음 · 선택 | 질문 | 결정 필요 |
|---|---|---|---|---|
| 1 | 6 | 3 | 6 | 2 |


## 1. 높음 — 먼저 고칠 것


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| AD-01 | mx-whitepaper-analyst 427장 중 154장은 「본문」 한 절의 글이 비어 있다(148장은 요약도 빔).<br>사용자는 제목 한 줄만 본다. | 154장 모두 06-12 생성 · `…0109` · `…0113` 은 1번 절만 비고 2번 「개요」 · 4번 「응용」 에는 본문이 남음 · 모든 절을 다시 넣는 `_resync_sections`(`:602-614`)와 맞지 않음(까닭 미확인) · 목록 필터 `sync_sources.yml:137-138`(`status: published`, `b401f88` 기준 · HEAD `ac42bc6` 기준 :138-139). | 동기화를 다시 돌리면(§5 AD-17) 첫 mxwp run 의 failed · dead_letter 사유를 본다(`GET /api/sync/sources/{id}/runs`, `routes/sync.py:309`).<br>`…0109` 의 MXWP 상세 조회가 키를 넣고 200 인지 본다.<br>상세가 되는데도 그대로면 목록 필터에서 빠진 문서다.<br>원본에서 내린 문서면 허브에서도 내리고, 아니면 154장만 다시 동기화한다. | 지식카드 K6-4 요청 4 · K1 요청 4 · 운영 쪽 8 |


## 2. 중간


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| AD-02 | '이 대화에서 분석'(저장하지 않음)인데 변환기가 추출한 그림을 /tmp 에 기한 없이 남긴다. | `api_server/src/api/services/converter_dispatch.py:109-113` 은 output_dir 이 None 이면 `tempfile.mkdtemp(prefix='ai_data_convert_')` 만 한다 · `mcp_write_svc.py` 에 output_dir · rmtree · TemporaryDirectory grep 0건 · 박스 /tmp 에 `ai_data_convert_*` 2개(10-22 06:46 · 10-25 20:05, 0700, 10-27 에도 2개). | run_convert 에서 TemporaryDirectory 를 output_dir 로 넘긴다.<br>payload 를 만든 뒤 지운다(또는 cleanup 플래그를 둔다). | 10-25 피드백 AIDH-1 |
| AD-03 | ppt 변환이 DRM(NASCA) 암호문을 알아보지 못한다.<br>같은 파일을 RA 추출에 넣으면 'zip 손상' 이라고만 답했다. | PC 시험 파일(37,316 B)의 앞 34바이트가 NASCA DRM 머리 · RA 추출 '유효한 .pptx 파일이 아닙니다(zip 손상).' · AIDataHub `api_server/src` 에 NASCA grep 0건(10-27 HEAD `ac42bc6`) · AIDH 변환기에 넣었을 때의 문구는 아직 보지 않았다(추정). | 앞 바이트에서 NASCA 머리(`3C 23 23 20 4E 41 53 43 41`)를 알아본다.<br>'DRM 암호화 문서 — 포털 챗 업로드나 PC 도우미(COM 추출)로' 라는 별도 오류를 낸다.<br>RA · 포털과 같은 판정을 쓴다. | 10-25 피드백 RA-1(AIDataHub 몫) |
| AD-04 | 요약이 빈 카드는 제목 몇 글자로만 검색에 걸린다.<br>본문 일치 코드는 들어갔지만 스위치 `AIDH_RECORDS_Q_BODY_SEARCH` 가 기본 꺼짐이다. | `config.py:42` · `record_query_svc.py:91`(`375560d`) · mx-whitepaper-analyst 빈 요약 320장 중 319장은 본문 있음 · 본문까지 넣으면 `모바일` 2→73 · `반도체` 3→32 · `소프트웨어` 2→54건(10-14) · `record_sections` 862,910행(09-09), 전수 스캔 25.6초(`alembic/versions/0031_fts_gin_index.py:12-14`) · `trgm` 인덱스 0건. | 운영 DB 사본에서 `EXPLAIN ANALYZE` 를 잰다(기준 material-twin-analyst 2,729장).<br>잰 값을 알려 주면 우리가 cae00 에서 스위치를 켠다(박스 설정 — 90-OURS-box-todo.md OB-89).<br>느리면 `pg_trgm` GIN 인덱스를 달고 다시 잰다. | 지식카드 K5 요청 2 · 운영 쪽 14 |
| AD-05 | 이름=키 · 설명 0자 · 카드 0건인 빈 전문가 `dynaforge-report` 가 전문가 목록에 뜬다.<br>고르면 빈 역할과 '일반 지식으로 답변' 이 나온다. | 08-15 스모크 등재가 남긴 자동 껍데기(`recommend_svc.py:833-839` 'Help the user with: (no description)') · 10-27 에도 행이 있고 sim-drop-impact 의 data_types 는 `["DOC"]` · 전제인 KooRemapper `826054f` 는 10-27 cae00 판(`a9179a3`)에 들어 있다. | sim-drop-impact 의 data_types 에 `SIM` 을 더한다(10-15 결정).<br>그 뒤 `DELETE /api/agents/dynaforge-report`(`routes/agents.py:208`)로 행을 지운다(`agent_records` 2행은 FK cascade 로 같이 지워진다).<br>어디서 지울지는 AD-13 답을 따른다(cae00 이면 우리가 지운다 — 90-OURS-box-todo.md OB-87). | 지식카드 K6-1 · 운영 쪽 9 |
| AD-06 | `kooremapper-modelmeta` 는 이름=키 · 설명 0자이고 카드 3장이 모두 07-31 데모 업로드다.<br>그중 하나는 실제 재료 카드에 이어져 진짜 모델 메타로 읽힐 수 있다. | 카드 `…0010` · `…0011` · `…0012`(데모 deck.k · nbr_board.k, 07-31 23:37~23:44Z) · `status: draft` 로는 가를 수 없음(`api_server/src/api/ingest/normalizer.py:501` 기본값) · 10-27 에도 3장 · 업로더 `6d63038` 은 cae00 판에 들어 있다. | 레코드 3건을 `DELETE /api/records/{id}`(`routes/records.py:239`, 소프트 삭제)로 먼저 지운다.<br>그다음 `DELETE /api/agents/kooremapper-modelmeta` 로 행을 지운다.<br>지우기 전에 우리가 박스 확인(K9 `…012` · K6-5 · K7 화면)을 마친다(90-OURS-box-todo.md OB-73).<br>어디서 지울지는 AD-13 답을 따른다(cae00 이면 우리가 지운다 — 90-OURS-box-todo.md OB-87). | 지식카드 K6-2 · 운영 쪽 10 |
| AD-07 | 심의 근거 검색(`agent_search`)에 날짜 컷오프가 없다.<br>소급 검증에서 출시 뒤에 들어온 레코드도 근거로 잡힌다. | 검색 범위는 좌석 키로 좁힌 records(`recommend_svc.py:450`) · `search_svc.py` 에 날짜 필터 grep 0건 · `Record.created_at` 은 원문 날짜가 아니라 허브 반입일(MX 백서 카드 154장 모두 06-12) · updated_at 은 단건 조회에도 바뀐다(`records.py:52-68` · `models.py:242`). | `as_of` 인자를 받아 믿을 날짜로 거른다(`Record.created_at <= as_of` 꼴).<br>믿을 날짜 칼럼이 없으면 먼저 알려 준다.<br>그때는 스키마 작업이라 다른 항목과 떼어도 된다. | 심의엔진 2-2 · 6-3 |


## 3. 낮음 · 선택


| # | 무엇이 | 근거 (파일:줄 · 실측 숫자) | 할 일 | 출처 |
|---|---|---|---|---|
| AD-08 | 포털 연결이 빠지면 모델이 inbox 파일 이름을 몰라 `convert_file` 을 부르지 못한다. | 10-22 대화에서 모델이 search_tools 로 `convert_file` 을 찾았지만 넣을 파일 이름이 맥락에 없었다. | 호출자의 최근 inbox 파일을 돌려주는 읽기 도구(예 `list_inbox`)를 `mcp_runtime.py`(convert_file 근처)에 둔다.<br>게이트웨이에 같은 이름 도구가 이미 보이니 이름 충돌에 주의한다. | PPT A-7(3순위) |
| AD-09 | 덤프 병합이 레코드 m3 시그니처를 옮기지 않는다.<br>dev 에서 바뀐 레코드의 m3 는 병합으로 오지 않는다. | 10-17 재병합 뒤 절 m3 1,090,100행은 왔지만 레코드 시그니처 0건 · 새 레코드는 인앱 30분 스윕(fill 에 m3)이 채운다 · cae00 읽기는 10-17 11:15 부터 m3. | `merge-from-drive.sh` 가 레코드 m3 시그니처도 옮기게 한다.<br>일부러 뺀 것이면 그렇다고 알려 준다. | 10-17 수정 목록 H1-b · 7절 |
| AD-10 | (선택) 심의 좌석 키 `delib-baseline-defender` 가 AIDataHub 에이전트로 없다. | 이 키 때문에 생긴 심의 오류(심의엔진 1-1)는 엔진 쪽에서 반영됐다.<br>등록은 그 근본 해결이다. | `delib-baseline-defender` 를 에이전트로 등록한다. | 심의엔진 2-3 · 6-2 |


## 4. 질문 · 확인 요청


| # | 물음 | 왜 묻나 | 출처 |
|---|---|---|---|
| AD-11 | materialtwin 6시간 동기화(`config/sync_sources.yml:171`, `b401f88` 기준 · HEAD `ac42bc6` 기준 :172)가 이미 있는 레코드의 `content` 를 덮어쓰는가. | 재료 카드를 원천에서 절로 나눠 내보내기로 정했다(K3-9 (가)).<br>덮어쓰지 않으면 고친 원천이 허브에 오지 않는다. | 지식카드 K3 미확인 |
| AD-12 | update-all 병합(`deploy/apptainer/merge-from-drive.sh:4` · `:54` · `:119`)에서 cae00 행의 updated_at 이 비어 있으면 dev 가 이기는가. | 코드만 읽은 판단이고, 실제로 덮인 예는 아직 없다.<br>맞으면 cae00 에서 만든 운영자(he-*) 판이 dev 판으로 덮일 수 있다. | 지식카드 K8 요청 5 |
| AD-13 | AD-05 · AD-06 의 지우기를 dev 원본에서 할지, cae00 에서 할지. | update-all 은 돌 때마다 dev 덤프를 병합한다.<br>한쪽에서만 지우면 다음 병합 뒤 어떻게 되는지 알려 달라. | 지식카드 K6-1 · K6-2 · K8 요청 5 |
| AD-14 | 동기화를 켜지 않기로(§5 AD-17 (나)) 하면 154장(AD-01)은 어느 길로 고치는가.<br>그리고 1번 절만 빈 까닭은 무엇인가. | 지식카드 요청은 동기화 재개를 전제로 했다.<br>1번 절만 바뀐 까닭은 미확인이다. | 지식카드 K6-4 요청 4 · 10-25 피드백 D14 |
| AD-15 | 동기화를 켜기로 하면 `AIDH_SYNC_ALLOW_INTERNAL` 과 `MXWP_INTERNAL_KEY` 를 `deploy/apptainer/.env` 에 두면 되는가. | 10-17 목록은 `api_server/.env` 가 기동마다 다시 써져 소용없다고 적었다.<br>지식카드 요청은 서버가 어느 파일에서 받는지를 미확인으로 남겼다.<br>부팅할 때마다 'MXWP_INTERNAL_KEY not set' 이 남고, 키 없이 부르면 MXWP 는 401 이다. | 10-17 수정 목록 D3 · 지식카드 K6-4 요청 0 |
| AD-16 | 알림 — cae00 BGE-M3 전환(체크리스트 B6)은 10-17 11:15 에 끝났다.<br>dev 쪽 체크리스트에 반영해 달라. | 답은 필요 없다.<br>되돌리기는 박스 `.env` 한 줄이다. | 10-17 수정 목록 §9 |


## 5. 결정 필요 (사용자)


| # | 정할 것 · 지금 | 선택지 | 권고 | 출처 |
|---|---|---|---|---|
| AD-17 | 정기 동기화 3곳(mxwp · signalforge-gs · materialtwin)을 다시 켤지.<br>10-01~10-15 mxwp 525번이 'non-standard port blocked: 8800' 으로 실패했고, signalforge-gs 525번 · materialtwin 45번도 같은 가드에 막혔다(10-27 로그로는 포트 18000 · 4180).<br>10-19~10-26 성공 0건이고, 10-27 로그도 차단 1,279줄 · 성공 0줄이다(`url_safety.py:110-122`, HEAD `ac42bc6` 그대로). | (가) 다시 켠다 — 박스 `deploy/apptainer/.env` 에 `AIDH_SYNC_ALLOW_INTERNAL=true` 와 `MXWP_INTERNAL_KEY` 를 넣거나(운영 몫, 값은 화면에 띄우지 않는다), AIDataHub 가 내부 주소 몇 개만 허용하는 코드로 바꾼다(`url_safety.py:18-20`).<br>(나) 켜지 않는다 — 그대로 두거나 enabled=false 로 소음을 없애고, Drive 덤프 병합을 정본으로 둔다. | 두 문서의 권고가 맞선다.<br>지식카드 요청은 (가)다 — AD-01, 재료 카드 재반입(K3-9), 빈 요약 줄이기(K6-4 요청 1~3)의 효과가 이것에 걸린다.<br>10-25 피드백 D14 와 10-17 D3 은 (나)다 — 덤프 병합이 정본이면 동기화는 필요 없다.<br>기준은 'cae00 이 원천에서 직접 받아야 하는가' 다.<br>(가)를 고르면 env 로 넓게 열지, 코드로 몇 주소만 열지는 AIDataHub 담당이 정한다(보안 설정). | 지식카드 K6-4 요청 0 · 운영 쪽 7 · 10-25 피드백 AIDH-2 · D14 · 10-17 수정 목록 D3 |
| AD-18 | 어디에도 글이 없는 MX 백서 카드를 내릴지. | (가) 내린다.<br>(나) 둔다. | 권고는 없다.<br>MXWP 원문에 summary 값이 있는지 MXWhitePaper 담당의 답을 본 뒤 정한다.<br>수는 K1 기준 5장, findings 기준 7장이다(미확인). | 지식카드 운영 쪽 12 |


## 6. 다른 플랫폼과 맞물린 것


| # | AIDataHub 몫 | 다른 쪽 몫 · 문서 | 출처 |
|---|---|---|---|
| AD-04 | 속도를 재고 스위치를 켤 수 있게 한다. | 01-HWAXPortal.md HP-21 — 스위치를 켤 때 검색칸 문구(`AgentDeepView.tsx:323`)를 「제목·요약·본문에서 낱말로 찾기」로 바꾼다.<br>90-OURS-box-todo.md OB-89 — 잰 값을 보고 cae00 에서 스위치를 켠다. | 지식카드 K5 요청 2 · 운영 쪽 14 |
| AD-07 | `as_of` 를 받는다. | 03-HWAXAgentServer.md HA-11 — 심의 엔진(`deliberation.py:1830`)이 `as_of` 를 함께 보낸다. | 심의엔진 2-2 |
| AD-03 | 변환이 NASCA 머리를 알아본다. | 11-ReportArchive.md RP-03 — 업로드와 추출이 같은 머리를 알아본다(RA-1).<br>01-HWAXPortal.md HP-14 — `docAttach.ts` isEncryptedOffice 에 같은 접두를 넣는다. | 10-25 피드백 RA-1 |
| AD-01 · AD-18 | 154장과 글 없는 카드를 정리한다.<br>`…0109` 의 MXWP 상세 조회가 키로 200 인지는 AIDataHub 담당이 본다(K6-4 요청 4 ②). | 09-MXWhitePaper.md MW-07 — 원문에 summary 값이 있는지 답한다.<br>동기화 결정(AD-17)에는 MXWP 쪽 할 일이 없다(09-MXWhitePaper.md 5절). | 지식카드 K6-4 요청 4 · 운영 쪽 12 |
| AD-05 · AD-06 | 빈 전문가 행과 데모 카드 3장을 지운다. | 04-KooRemapper-DynaForge.md — 바꿀 것 없다(`826054f` · `6d63038` 이 cae00 `a9179a3` 에 들어 있다).<br>90-OURS-box-todo.md OB-73 — 지우기 전에 박스 화면 확인(K9 `…012` · K2 · K6-5 · K7)을 마친다.<br>90-OURS-box-todo.md OB-87 — 지우는 곳이 cae00 이면(AD-13 답) 우리가 지운다. | 지식카드 K6-1 · K6-2 · 운영 쪽 9 · 10 |
| AD-11 · AD-17 | materialtwin 규칙 몫(`57397d9`)은 들어 있다.<br>재반입은 동기화 결정에 걸린다. | 06-HEAXHub.md HH-01(MaterialTwinWeb) — 본문을 6만 자에서 자르지 말고 절 여러 개로 내보낸다(`hub_export.py:28` · `:79-80`). | 지식카드 K3 요청 9 |
| AD-12 | 병합 규칙을 확인한다. | 01-HWAXPortal.md HP-35 — update-all 이 병합 뒤 `sync-he-personas.py` 미리보기를 돌려 알린다. | 지식카드 K8 요청 5 |
| AD-02 | 변환 부산물을 지운다. | 01-HWAXPortal.md HP-29 — 'AI 데이터 허브' 목적지가 `~/aidh-inbox` 사본을 지우지 않는다(PT-4).<br>90-OURS-box-todo.md OB-36 · OB-10 — 남은 `/tmp/ai_data_convert_*` 와 `~/aidh-inbox` 사본을 정리한다(D10). | 10-25 피드백 AIDH-1 · PT-4 · D10 |
| AD-17 | (가)라면 코드 허용 목록을 둘지 정한다. | 90-OURS-box-todo.md OB-05 — 박스 env 값 넣기(가) 또는 그대로 두기(나).<br>06-HEAXHub.md · 08-SignalForge.md · 09-MXWhitePaper.md — 할 일 없음. 재반입 확인만 이 결정에 걸린다. | 지식카드 운영 쪽 7 · 10-17 수정 목록 D3 |


## 7. 다시 볼 시험


| 시험 | 언제 · 무엇을 보나 | 걸린 항목 |
|---|---|---|
| M-3(사람 손 시험) | 포털 웹 챗에서 '이 대화에서 분석' 을 고른 뒤 박스 `/tmp/ai_data_convert_*` 가 늘지 않아야 한다. | AD-02 |
| M-6(사람 손 시험) | NASCA 로 암호화된 .pptx 를 넣고 오류 문구를 그대로 적는다.<br>DRM 문서라는 별도 문구가 나와야 한다. | AD-03 |
| 지식카드 K6-4 확인 | 목록 조회로 '427 · 빈 요약 320 · 속 빈 154' 를 다시 센다.<br>동기화 뒤 빈 요약이 줄고, 154장 정리 뒤 속 빈 카드가 0이어야 한다. | AD-01 · AD-17 |
| 지식카드 K6-1 · K6-2 확인 | `GET /api/agents/` 에서 이름=키 전문가가 빠지고, `?agent=kooremapper-modelmeta` 의 total 이 3 → 0 이어야 한다. | AD-05 · AD-06 |
| 지식카드 K5 확인 | 스위치를 켜고 5분 지나서(게이트웨이 `list_*` 캐시 300초) 본문 낱말로 찾는다. | AD-04 |
| 전수 점검 | 모두 들어간 뒤 cae00 `~/kc-check/kc_sweep.py`(읽기만)를 다시 돌린다.<br>확인에는 목록 조회만 쓴다(단건 조회는 read_count 를 바꾼다 — updated_at 은 AIDataHub `fccb0e5`(10-31) 부터 그대로). | AD-01 · AD-04 · AD-05 · AD-06 |


## 8. 이 문서에서 뺀 것


- 지식카드 K6-4 요청 1~3(요약 폴백 · 같을 때만 건너뛰기 · 상세 실패 때 덮어쓰지 않기) — 반영됐다(`5ca5c45` · `13ae431` · `84f4ffc`, 10-27 cae00 판에 들어 있음).


- 10-17 D3 선행 조건(`84f4ffc` 가 다시 켜기 전에 들어가야 함) — 들어갔다(10-27 확인).


- 지식카드 K5 요청 1 · 3 · 4 · 5 — 반영됐다(`4461aaf` · `375560d`). 요청 2 의 스위치를 cae00 에서 켜는 일은 운영 몫이다(90-OURS-box-todo.md OB-89).


- 재료 카드 materialtwin 규칙(K3-9 의 AIDataHub 몫) — 반영됐다(`57397d9`).


- SIM 카드 부품 표(K9 요청 2) — HWAXAgentServer 몫이다. AIDataHub 는 근거(`schemas/sim.py:30-53`)만이고 바꿀 것이 없다.


- BGE-M3 전환 — 10-17 11:15 박스에서 끝냈다(운영 몫).


- 이행 0032 잠금 — 10-17 재배포로 풀렸다.


- PG 안전망 시간 한도(10-17 D4) — 박스에서 고르는 선택 강화라 운영 몫이다(90-OURS-box-todo.md OB-16).


- 남은 `/tmp/ai_data_convert_*` 2개와 `~/aidh-inbox` 사본 정리 — 운영 몫이다(90-OURS-box-todo.md OB-36 · OB-10, D10).


- `~/kc-check/kc_sweep.py` 에 '절은 있는데 글이 0자인 카드' 검사 더하기(지식카드 운영 쪽 18) — 우리 도구라 요청이 아니다(90-OURS-box-todo.md OB-44).


- 포털 대화 검색 표지(10-17 P-10) · 서버 변환 문서의 근거 표시 이름(10-25 PT-9) — HWAXPortal 몫이다(01-HWAXPortal.md HP-36 · HP-31). AIDataHub 는 바꿀 것이 없다.


- 동기화 스위치 · 키 값 넣기 — 박스 env 라 운영 몫이다(AD-17 을 정한 뒤, 90-OURS-box-todo.md OB-05).


- PLM 사람 신원 · 공유 한도 — 사용자 보류다. AIDataHub 에는 이 범위의 요청이 없다.
