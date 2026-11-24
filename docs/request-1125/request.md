# HWAX 개발 요청 모음 — 2026-11-24 기준, 아직 안 끝난 것 전부



운영 포털 박스(cae00)에서 쓴 요청을 한 곳에 모았습니다. 개발 세션이 아직 받지 않은 것과, 받았지만 끝난 흔적이 없는 것입니다. 주소 · 키 · 사람 이름은 넣지 않았습니다.



**어떻게 골랐나**

- 운영 쪽 요청서를 항목마다 읽었습니다.

- 개발 쪽이 받은 폴더(`docs/request-1015` ~ `request-1123`, `docs/cae00-inbox`, 각 저장소 `docs/requests`)와 대조했습니다.

- 저장소 커밋 기록(10-10 이후)과 지금 HEAD 도 대조했습니다.

- 「이미 받았다 · 이미 됐다」는 판정은 다른 검토자가 한 번 더 반박해 보았습니다.



**기준 HEAD:** 포털 `9b34a4ea` · 게이트웨이 `c43382bc` · 에이전트 서버 `b0fd9229` · HEAXHub `948c98cf` · AIDataHub `d59cf116` · SignalForge `5f97f24d` · KooRemapper `76067368` · MXWhitePaper `d755a009`



**읽는 법**

- 항목마다 다음을 적었습니다.

  - 문제(근거 수치)

  - 바꿀 것

  - 위치

  - 확인 방법

  - 선례 커밋

  - 먼저 할 것

- **새 요청:** 처음 보내는 것입니다.

- **받았으나 안 끝남:** 이미 받은 요청인데 체크리스트 · 커밋에 끝난 흔적이 없는 것입니다. 받은 곳을 함께 적었습니다.

- **번호:** 원 요청서의 번호를 그대로 썼습니다. 개발 쪽에서 번호를 바꿔 받은 것이 있으면 알려 주세요.

  - 서로 다른 요청서가 같은 번호를 쓴 경우는 `번호 [출처]` 꼴로 대괄호 안에 출처(요청서 날짜 또는 문서 번호)를 붙여 구분했습니다.

  - 원 요청서에 번호가 없던 것은 새로 붙였습니다(예: TS-1).

- **3절 상태 표시:** 「보낸 기록 없음」은 우리 쪽 기록에 보낸 흔적이 없다는 뜻입니다. 이미 받은 팀이면 그 항목은 빼고 보시면 됩니다. 「보낸 흔적 있음 · 끝난 흔적 없음」은 보냈지만 반영 여부를 아직 못 본 것입니다.

- **절 구성:**

  - 1절 · 2절: 개발 세션 몫

  - 3절: 다른 팀 몫(각 플랫폼 담당에게 따로 갑니다)

  - 4절: 사용자 결정이 먼저인 것(보내지 않음)

  - 부록 A: 이미 됐거나 대체돼서 뺀 것



## 0. 한눈에



**HWAX 개발 세션 몫 (1절)**



| 저장소 | 항목 | P0 | P1 | P2 | P3 | 새 요청 | 받았으나 안 끝남 |

|---|---|---|---|---|---|---|---|

| 포털 (HWAXPortal) | 29 | 0 | 5 | 16 | 8 | 29 | 0 |

| 게이트웨이 (HWAXMcpGateway) | 10 | 1 | 2 | 4 | 3 | 5 | 5 |

| 에이전트 서버 (HWAXAgentServer) | 18 | 0 | 6 | 7 | 5 | 16 | 2 |

| StepForge (HEAXHub) | 14 | 0 | 4 | 5 | 5 | 10 | 4 |

| DocForge (HEAXHub) | 16 | 0 | 3 | 9 | 4 | 16 | 0 |

| 리스크 앱 (HEAXHub) | 2 | 0 | 0 | 2 | 0 | 1 | 1 |

| HEAXHub 공통 · MaterialTwin | 4 | 0 | 0 | 3 | 1 | 3 | 1 |

| AIDataHub | 12 | 1 | 3 | 4 | 4 | 11 | 1 |

| SignalForge | 5 | 0 | 2 | 2 | 1 | 5 | 0 |

| MXWhitePaper | 3 | 0 | 0 | 0 | 3 | 0 | 3 |

| KooRemapper | 6 | 0 | 0 | 2 | 4 | 3 | 3 |

| 여러 저장소 공통 | 2 | 0 | 0 | 0 | 2 | 2 | 0 |

| **합** | **121** | 2 | 25 | 54 | 40 | 101 | 20 |



여기에 2절 MCP 효율 요청(G-1~G-5 · A-2 · B-1 [11-24] · B-2 [11-24] · P-1 [11-24])이 따로 더해진다. A-1 은 1절의 OF-1~5 에 '위임 실행기가 단계마다 앞선 결과를 줄여 싣기' 하나를 더한 묶음이다. OF-1~5 는 1절 항목으로 세고, 더한 하나만 2절 몫이다.



**다른 팀 몫 (3절)**



| 받는 곳 | 항목 | P0 | P1 | P2 | P3 | 보낸 흔적 있음 |

|---|---|---|---|---|---|---|

| ReportArchive | 27 | 0 | 9 | 11 | 7 | 0 |

| STE · 연계 브리지 (ste 세션) | 21 | 4 | 10 | 7 | 0 | 19 |

| PCB체크리스트서버 | 19 | 0 | 3 | 7 | 9 | 14 |

| SimFlow | 19 | 0 | 1 | 14 | 4 | 0 |

| Datahub 플랫폼 (hwax-batch 공통 엔진) | 15 | 0 | 3 | 4 | 8 | 0 |

| ODB 허브 | 15 | 0 | 2 | 6 | 7 | 0 |

| ARP | 9 | 0 | 1 | 2 | 6 | 0 |

| FMEA | 8 | 0 | 0 | 5 | 3 | 0 |

| PLM 검색 에이전트 | 7 | 0 | 0 | 2 | 5 | 0 |

| SmartTwin MCP · 해석 클러스터 | 4 | 0 | 2 | 1 | 1 | 0 |

| ComponentCore | 3 | 0 | 1 | 1 | 1 | 0 |

| GPU 클러스터 운영 | 3 | 0 | 0 | 0 | 3 | 0 |

| MatNexus | 3 | 0 | 1 | 0 | 2 | 0 |

| SIREN | 3 | 0 | 1 | 2 | 0 | 0 |

| 허브 관리자 — FailureTrace | 3 | 0 | 2 | 0 | 1 | 0 |

| 허브 관리자 — MountSol | 3 | 0 | 0 | 2 | 1 | 0 |

| 허브 관리자 — NCDev | 3 | 0 | 0 | 2 | 1 | 0 |

| TestScope | 2 | 0 | 0 | 0 | 2 | 0 |

| 허브 관리자 — CAE그룹 | 2 | 0 | 0 | 2 | 0 | 0 |

| SimEngBay | 1 | 0 | 0 | 0 | 1 | 0 |

| **합** | **170** | 4 | 36 | 68 | 62 | 33 |



4절 사용자 결정 대기 56건 · 부록 A 빼낸 것 514건.



**개발 세션이 먼저 볼 것 (P0 · P1)**



| ID | 제목 | 저장소 | 우선 | 상태 |

|---|---|---|---|---|

| BG-3 | artifact_to_ste_upload 남은 확인 — 100 MB 급 · cavity_step | 게이트웨이 (HWAXMcpGateway) | P0 | 받았으나 안 끝남 |

| R-01 | AIDataHub 전문가 삭제 API 에 인증이 없음 | AIDataHub | P0 | 새 요청 |

| AD-22 | bind_entities 가 사전에 든 타입의 연결만 지우기 | AIDataHub | P1 | 새 요청 |

| ADO-1 | 코어 key 로 카드를 찾는 읽기 도구 cards_by_core | AIDataHub | P1 | 새 요청 |

| HP-57 | 서비스 감시 heal 이 update-collab · start · restart · stop · 손 down 중에도 서비스를 다시 띄움 | 포털 (HWAXPortal) | P1 | 새 요청 |

| HPO-1 | core_vocab.json ontology.lookup 에 다섯 앱 줄(MountSol · NCDev · ODB 허브 · FMEA · ARP) 옮기기 | 포털 (HWAXPortal) | P1 | 새 요청 |

| IR-01 | '이 대화에서 분석' 도 그림 판독 켜기 | 포털 (HWAXPortal) | P1 | 새 요청 |

| IR-02 | DocForge 에 snapshot_page(쪽 그림)를 넘기기 | 포털 (HWAXPortal) | P1 | 새 요청 |

| IR-03 | 붙인 뒤 문구 · 문서 칩에 그림 수 · 판독 수 · 읽지 못한 것 보이기 | 포털 (HWAXPortal) | P1 | 새 요청 |

| IR-11 | pptx 쪽 그림을 골라서 판독(그림 파일로 못 읽는 쪽만) | DocForge (HEAXHub) | P1 | 새 요청 |

| IR-12 | 잘린 그림은 잘린 대로 싣고 판독하기 | DocForge (HEAXHub) | P1 | 새 요청 |

| IR-13 | 그림으로 채운 도형의 그림을 그림 요소로 꺼내기 | DocForge (HEAXHub) | P1 | 새 요청 |

| IR-31 | AI 데이터 허브 convert_file 에 그림 판독 붙이기 | AIDataHub | P1 | 새 요청 |

| OF-1 | 위임이 보고서 첨부 본문을 못 읽음 | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| OF-2 | 위임이 덜 찾고 멈추는데 결과에 '덜 찾음' 이 드러나지 않음 | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| OF-3 | 숫자 대조가 단위 환산 · 반올림을 어긋남으로 셈 | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| OL-6 | ontology.lookup 앱별 줄 여럿 · 안쪽 칸까지 {key} 채우기 | 게이트웨이 (HWAXMcpGateway) | P1 | 새 요청 |

| SF-4 | part_stack 층 정보의 출처 | StepForge (HEAXHub) | P1 | 받았으나 안 끝남 |

| SF-7 | enclosure_candidates 에서 앞뒤 유리가 빠짐 · 닫힘 추정 칸 | StepForge (HEAXHub) | P1 | 받았으나 안 끝남 |

| SFO-1 | 프로젝트 key 를 코어로 풀고, 못 풀면 넓히지 말고 0건 + reason | SignalForge | P1 | 새 요청 |

| SFO-2 | 과제 → 제품 연결이 없을 때 낱말 검색으로 바꾼 것을 알리고 strict 인자 두기 | SignalForge | P1 | 새 요청 |

| ST-24 | part_ontology.yaml 코어 부품 14칸 채우기(역할 → 코어 부품) | StepForge (HEAXHub) | P1 | 새 요청 |

| ST-26 | identify_part 등 도구 답에 core_part 와 이슈 next 싣기 | StepForge (HEAXHub) | P1 | 새 요청 |

| WD-01 | 심의 근거를 참조로 넘기기(잡 결정문 · 도구 · 대화 · 문서) | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| WD-02 | 웹 챗에 심의 · 리스크 도구를 맥락 따라 늘 묶고, 지어낸 잡 id · 실행 주장 검사 | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| WD-03 | MCP 로 연 심의를 잡 주인의 포털 대화에 자동 기록 | 에이전트 서버 (HWAXAgentServer) | P1 | 새 요청 |

| WD-04 | save_conversation 이 활동을 지키고 다시 열 때 근거로 되살리며 사이드바를 바로 갱신 | 게이트웨이 (HWAXMcpGateway) | P1 | 새 요청 |



---



## 1. HWAX 개발 세션 몫



### 1-1. 포털 (HWAXPortal) — 29건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| HP-57 | 서비스 감시 heal 이 update-collab · start · restart · stop · 손 down 중에도 서비스를 다시 띄움 | P1 | 새 요청 |

| HPO-1 | core_vocab.json ontology.lookup 에 다섯 앱 줄(MountSol · NCDev · ODB 허브 · FMEA · ARP) 옮기기 | P1 | 새 요청 |

| IR-01 | '이 대화에서 분석' 도 그림 판독 켜기 | P1 | 새 요청 |

| IR-02 | DocForge 에 snapshot_page(쪽 그림)를 넘기기 | P1 | 새 요청 |

| IR-03 | 붙인 뒤 문구 · 문서 칩에 그림 수 · 판독 수 · 읽지 못한 것 보이기 | P1 | 새 요청 |

| HP-59 | update-all MCP 점검이 읽기 전용 PAT 길을 부르지 않음 | P2 | 새 요청 |

| HP-60 | STE 배포가 실행 중 잡을 보지 않음 | P2 | 새 요청 |

| HP-72 | gen-nginx-conf 가 경로마다 Host 를 정할 수 없어 MCP 직결 넷에 박스 중계가 필요 | P2 | 새 요청 |

| HP-74 | MCP 직결 경로의 끝 슬래시 307 이 포털 접두를 잃고 셋은 http:// 로 내려감 | P2 | 새 요청 |

| HP-82 | core_vocab types 에 부품(part) · lookup 에 결함 목록 줄 | P2 | 새 요청 |

| HPO-2 | card-entity-bind.py 타입별 증분 모드(--only-types) | P2 | 새 요청 |

| HPO-3 | 개발모델 · 과제 · 관리 기준 링크 0 의 까닭을 summary 에 타입별로 (유도 규칙은 선택) | P2 | 새 요청 |

| HPO-4 | core_vocab.json apps 에 MountSol · NCDev 형제(sibling) 두 줄 | P2 | 새 요청 |

| IR-04 | DocForge 권한이 없는 사람의 AI 데이터 허브 변환 길에도 판독 · 안내 | P2 | 새 요청 |

| IR-05 | 새 대화를 열면 붙인 문서 칩 비우기 | P2 | 새 요청 |

| IR-06 | 보낼 곳 고르기에서 'RA 가져오기' 와 '정밀 변환' 의 차이 보이기 | P2 | 새 요청 |

| IR-07 | DocForge 판단(llm) 옵션을 넘기기 | P2 | 새 요청 |

| IR-08 | vlm · snapshot_page · llm 세 값을 포털 설정으로 빼기 | P2 | 새 요청 |

| SE-2 | §1b 배포 전 백업의 AIDataHub 덤프 시간 줄이기 | P2 | 새 요청 |

| SE-7 | SignalForge 병합에서 덤프를 두 번 받지 않기 · 받는 쪽 보관 개수 | P2 | 새 요청 |

| WD-05 | 웹 '이어하기' 가 엔진 deliberate_continue 를 부르게 | P2 | 새 요청 |

| HP-58 | env-sync 가 AIDataHub deploy/apptainer/.env 를 보지 않음 | P3 | 새 요청 |

| HP-61 | 받은 편지함 · server-setup 의 명령이 운영 박스와 맞지 않음(sqlite3 -readonly · 낡은 app_data 경로) | P3 | 새 요청 |

| HP-68 | update-all 장애 안내 문구가 로컬 :8700 · :8701 과 deploy-all kooremapper 를 권함 | P3 | 새 요청 |

| HP-69 | update-forges.sh stepforge 가 proxy 로 덮어쓴 step_forge 를 다시 지으려다 exit 2 | P3 | 새 요청 |

| HP-75 | MCP 직결 경로가 평문 포트 8088 에도 열림 | P3 | 새 요청 |

| SE-9 | update-all · deploy-all 실행 기록의 단계 제목에 시각 찍기 | P3 | 새 요청 |

| SYNCEFF-3 | aidh-parts-sync 문서끼리 어긋난 두 곳 고치기 | P3 | 새 요청 |

| WD-11 | '이 대화에서 분석' 길의 DRM 감지 | P3 | 새 요청 |



#### HP-57 · 서비스 감시 heal 이 update-collab · start · restart · stop · 손 down 중에도 서비스를 다시 띄움

`P1` · 새 요청



- **문제:** services.py:755-766 `_update_all_running()` 은 명령줄에 update-all.sh 가 있는지만 본다. heal 은 연결 거부 3번(5초 간격)이면 down · up 한다(:768-818). cae00 은 11-01 에 감시를 켰고(운영 쪽 사용자 결정), 그 뒤 update-collab · start · restart · stop · 손 down 중 일부러 내린 서비스가 1분 안에 다시 뜬다.

- **바꿀 것:** update-collab · start · restart · stop 이 도는 동안, 또는 표지 파일(예 infra/.state/maintenance)이 있으면 heal 이 비켜서게 한다. 표지를 두고 거두는 명령을 문서에 적는다.

- **위치:** infra/scripts/services.py:755-818 (_update_all_running · heal) · infra/scripts/update-collab.sh

- **확인:** update-collab 한 번 도는 동안 ~/.local/state/hwax/watchdog.log 에 down/up 줄이 없다 · 표지 파일을 두면 heal 이 건너뛰고 지우면 다시 돈다

- **선례:** HP-01(배포 표지 deploy.lock.d · KooRemapper KR-04 f1ab307 — 같은 꼴의 감시 비켜서기)

- **참고:** update-collab 은 외부 플랫폼 반영의 기본 빠른 길이라 겹칠 일이 잦다.



#### HPO-1 · core_vocab.json ontology.lookup 에 다섯 앱 줄(MountSol · NCDev · ODB 허브 · FMEA · ARP) 옮기기

`P1` · 새 요청



- **문제:** ontology_lookup 이 다음 호출을 넘기는 앱이 저장소 기본표에는 넷뿐이다. 11-24 에 박스 덧씌우기로 다섯 앱을 더해 고장모드 key 7줄 · 과제코드 9줄이 됐지만 박스 파일에만 있다.

- **바꿀 것:** core_vocab.json 의 ontology.lookup 에 아래 다섯 줄을 그대로 넣는다. cae00 박스 덧씌우기와 같은 값이고, 칸은 tool · args · types · _doc 만 쓴다. ① "mountsoldatahub": {"tool": "object_resolve", "args": {"type_slug": "{type_slug}", "name": "{key}"}} ② "ncdevdatahub": {"tool": "object_resolve", "args": {"type_slug": "{type_slug}", "name": "{key}"}} ③ "odb-hub": {"tool": "find_job", "args": {"query": "{key}"}, "types": ["plm_project", "plm_task", "plm_model_code"]} ④ "fmea": {"tool": "find_cases_by_hub_name_tool", "args": {"names": "{key}"}, "types": ["failure_mode", "mechanism", "stress_type", "plm_project", "plm_task", "plm_model", "plm_model_code"]} ⑤ "arp": {"tool": "list_analyses", "args": {"model": "{key}"}, "types": ["plm_project", "plm_task", "plm_model_code"]}. 들어오면 운영 쪽이 박스 덧씌우기 파일을 지운다.

- **위치:** HWAXPortal backend/config/core_vocab.json ontology.lookup — HEAD 9b34a4ea 의 키는 caegroupdatahub · failuretrace · heax-kooremapper_mcp · heax-step_forge 넷

- **확인:** 박스 파일을 지운 뒤 게이트웨이 /health overlay present false, ontology_lookup(고장모드 key) 다음 호출이 여전히 7줄.

- **선례:** d1686bc8(11-17 ontology.lookup — 운영 요청 OL-3)

- **참고:** 들어오면 운영 쪽이 cae00 박스 덧씌우기 core_vocab.local.json 의 lookup 다섯 줄을 걷는다(부록 A 23-BOX-2). 같은 때 들어올 HP-82(types 에 부품 · lookup FailureTrace 결함 목록 줄)와 같은 파일 · 같은 칸을 고친다.



#### IR-01 · '이 대화에서 분석' 도 그림 판독 켜기

`P1` · 새 요청



- **문제:** 웹 챗에서 PPT 를 '이 대화에서 분석' 으로 붙이면 그림은 자리표([그림 N])만 간다. 11-10 시험에서 그림에만 답이 있는 6문항 모두 '안 보임' 이었다. 같은 챗 모델에 그림을 직접 넣으면 0.8초에 정확히 읽고, 판독 켬 잡은 그림 5장 + 둘째 판독 약 12초였다.

- **바꿀 것:** chat 갈래도 vlm: true 로 부른다. 기다림이 걱정이면 (가) 글을 먼저 칩으로 붙이고 판독이 끝나면 칩을 갈아 끼우거나 (나) 그림이 많을 때만 '그림도 읽을까요(약 N초)' 를 묻는다. 판독 캐시가 있어 같은 덱은 다시 붙이면 거의 바로 끝난다.

- **위치:** HWAXPortal backend/app/agent/routes.py:2160-2161(HEAD 9b34a4ea, chat 갈래의 docforge_convert 호출 — 11-10 판 d49d58fe 에서는 :1991)

- **확인:** 시험 덱을 '이 대화에서 분석' 으로 붙이고 2 ~ 4쪽 그림 문항(막대 값 · 최대 응력 · FAIL 행)에 맞게 답한다. 감사 줄 · 잡 옵션에 vlm=true.

- **선례:** 정밀 변환 갈래는 이미 vlm=body.vlm(routes.py:2137-2138)

- **먼저:** IR-08(켜고 끄기를 설정으로)과 함께 넣는다. IR-23 · IR-24(잡 줄)는 기다리지 않는다 — IR-01 이 들어오면 '이 대화에서 분석' 잡이 정밀 변환 잡 뒤에 더 길게 줄을 서니, 그 둘은 다음 차례로 넣는다(원 요청서 순서 넷째).

- **참고:** 박스 쪽 DocForge 판독 동시 수는 11-10 에 2 → 4 로 이미 올렸다(knobs.env, 부록 A S-1 [22-1]). IR-03 · IR-08 과 함께 맨 먼저 넣을 묶음이다 — 웹 챗 증상이 바로 사라지고, IR-08 이 있으면 챗 모델이 바쁜 날 운영 쪽이 끌 수 있다.



#### IR-02 · DocForge 에 snapshot_page(쪽 그림)를 넘기기

`P1` · 새 요청



- **문제:** 포털 어디에도 snapshot_page 가 없어 DocForge 가 쪽 그림을 만들 수 있어도 쓰이지 않는다. 쪽 그림을 챗 모델에 넣으면 흐름 · 빨간 원 · 그림 채움 · TIFF 가 모두 읽혔다(쪽당 1 ~ 4초).

- **바꿀 것:** 정밀 변환 · 대화 분석 두 길에서 snapshot_page: true 를 넘긴다. 보고서에 쪽 그림을 그대로 싣는 것은 IR-16 으로 따로 고른다.

- **위치:** HWAXPortal backend/app/agent/routes.py:2137-2138 · :2160-2161(HEAD)

- **확인:** 잡 옵션에 snapshot_page=true 가 실리고 DocForge 잡 결과에 쪽 그림 자원이 생긴다.

- **먼저:** 짝: DocForge IR-11(쪽 그림 판독)과 함께 넣는다(원 요청서 순서 셋째 — IR-02 · IR-11 · IR-12 · IR-13). IR-02 는 IR-11 의 재료라, 기다리는 쪽은 IR-11 이다.

- **참고:** IR-08 의 설정 값으로 함께 뺀다.



#### IR-03 · 붙인 뒤 문구 · 문서 칩에 그림 수 · 판독 수 · 읽지 못한 것 보이기

`P1` · 새 요청



- **문제:** 붙인 뒤 완료 문구와 문서 칩('발표자료 · 10슬라이드 · 824자')에 그림이 빠졌다는 말이 없어 사람은 그림까지 읽혔다고 믿는다. 처음 신고된 증상('글은 잘 가는데 그림 인식이 하나도 안 된다')이 이것이다.

- **바꿀 것:** 붙인 뒤 문구와 칩에 '그림 N · 판독 M · 읽지 못한 것 K(도형 · TIFF · 그림 채움 …)' 를 보인다. 판독 0 이면 '그림은 읽지 않았습니다 — 그림이 중요하면 슬라이드 캡처를 붙이거나 정밀 변환으로 보내세요'. DocForge 문서 머리의 빠진 것 목록을 그대로 쓴다.

- **위치:** HWAXPortal frontend/src/components/chat/DocDispatchPanel.tsx:189(HEAD) · 문서 칩

- **확인:** 그림이 있는 덱을 판독 없이 붙이면 완료 문구와 칩에 그림 수와 '읽지 않음' 이 보인다.

- **참고:** IR-01 · IR-08 과 함께 맨 먼저 넣을 묶음이다(웹 챗 증상이 바로 사라진다).



#### HP-59 · update-all MCP 점검이 읽기 전용 PAT 길을 부르지 않음

`P2` · 새 요청



- **문제:** 11-01 에 리스크 앱 ECAD 도구가 odb-hub find_job 을 사람의 읽기 전용 PAT 로 부르다 약 48분 막혔는데, odb-hub verify 204 와 스모크 3/3 은 통과였다.

- **바꿀 것:** 기대 시험에 '리스크 앱이 부르는 남의 앱 조회 도구가 읽기 전용 판정을 통과하는가' 를 더한다(/tools-map 의 읽기 표지로 본다).

- **위치:** infra/scripts/update-all.sh (MCP 점검 · §7) · backend/tests/test_update_all_gateway_expectations.py

- **확인:** read_tools.json 에서 odb-hub find_job 한 줄을 빼 둔 사본으로 돌리면 update-all 이 ✗ 를 내고, 원본이면 ✓

- **선례:** HG-25(게이트웨이 58e392a — 같은 사건의 게이트웨이 몫)



#### HP-60 · STE 배포가 실행 중 잡을 보지 않음

`P2` · 새 요청



- **문제:** 11-01 grep 에서 deploy-ste.sh → STE refresh-code.sh · deploy-backend.sh 세 스크립트에 squeue · 실행 중 잡 확인이 0곳이었다. 11-01 에 7일 한도 해석 잡 3개가 돌아 배포를 미뤘고 박스가 따로 '잡 0 일 때 배포' 스크립트로 기다린다. 잡 중 배포는 계산 노드가 읽는 공유 폴더를 덮고 백엔드를 여러 번 다시 띄운다. 그 뒤 11-23 반영 안내(HWAXPortal docs/cae00-inbox/2026-11-23.md:20 · :140)는 update-all §2c(대화형 또는 --with-ste)가 도는 잡이 있으면 staging 을 받아 두고 0 이 되면 저절로 바꾼다고 적었다. 그 검사가 어디에 있는지(deploy-ste.sh 인지 STE 쪽인지) 먼저 가리고, deploy-ste.sh 를 바로 부르는 길처럼 검사가 없는 곳에만 넣는다.

- **바꿀 것:** 배포 전에 STE 실행 중 잡 수를 보고 0 이 아니면 멈춘다(--force 일 때만 넘긴다). 이 멈춤은 deploy-ste.sh 를 바로 부르는 길처럼 검사가 없는 곳에 넣는다. update-all --with-ste 경로는 잡이 도는 동안 바꾸지 않으면 된다 — 11-23 안내의 'staging 을 받아 두고 0 이 되면 바꾸는' 동작이 이미 있으면 그대로 두고 멈춤으로 바꾸지 않는다.

- **위치:** infra/scripts/deploy-ste.sh (STE 리포 deploy/refresh-code.sh · deploy/deploy-backend.sh)

- **확인:** 잡이 1개 이상 도는 상태에서 deploy-ste.sh 를 바로 부르면 rc≠0 으로 멈추고 이유 한 줄을 낸다 · --force 면 진행 · update-all --with-ste 는 잡이 도는 동안 바꾸지 않는다(staging 만 받아 두고 0 이 되면 바꾸는 지금 동작이 있으면 그대로).

- **참고:** STE 리포 쪽 스크립트(deploy/refresh-code.sh · deploy/deploy-backend.sh)에도 같은 검사를 넣을지는 아직 보지 않았다.



#### HP-72 · gen-nginx-conf 가 경로마다 Host 를 정할 수 없어 MCP 직결 넷에 박스 중계가 필요

`P2` · 새 요청



- **문제:** loc_block 이 모든 location 에 Host $host 를 고정한다. 루프백에 바인드한 FastMCP 앱(데이터허브 셋 · MX White Paper)은 DNS rebinding 보호로 포털 도메인 Host 를 421 로 거절했다(11-13 실측). 그래서 박스에 nginx 중계를 하나 더 띄워 Host 만 바꾸며, 이 중계가 죽으면 네 경로가 같이 끊긴다.

- **바꿀 것:** 박스 파일에서 경로별로 Host 를 정하게 한다. 최소안은 '이 id 는 proxy_set_header Host $proxy_host;' 선택 하나. 표시는 routes.local.env 꼬리표 · *-mcp 는 늘 · 박스 덧붙임 include 중 자유.

- **위치:** HWAXPortal infra/scripts/gen-nginx-conf.sh loc_block :90-125 (Host 줄 :105 · :125) · infra/nginx/hwax.conf.tmpl:65

- **확인:** failuretrace-mcp 줄을 중계 대신 터널 포트로 바로 돌린 뒤 gen-nginx-conf.sh · nginx -t 통과, 포털 도메인 Host 로 보낸 initialize 가 200.

- **선례:** 720caa4b — 같은 loc_extras '*-mcp)' 갈래(gen-nginx-conf.sh:86)에 HP-73 묶음이 들어감; HP-70 둘째 안(routes.local.env 경로별 덧붙임)

- **참고:** loc_block 은 location 마다 proxy_set_header 전체를 다시 적는다 — Host 를 갈래별로 바꾸려면 loc_block 안에서 골라야 한다. HP-74 · HP-75 와 한 묶음으로 보내면 좋다. 정책 쪽 Origin 머리 비우기도 같은 자리(MCP-PATHS-P1).



#### HP-74 · MCP 직결 경로의 끝 슬래시 307 이 포털 접두를 잃고 셋은 http:// 로 내려감

`P2` · 새 요청



- **문제:** 앱 MCP 는 '/mcp/' 에 '/mcp' 로 307 을 내는데 Location 이 포털 경로 접두(/<id>-mcp)를 모른다. 중계를 안 거치는 넷은 포털 루트 /mcp(SPA)로 넘어가고, 그중 셋(ReportArchive · ComponentCore · SimEngBay)은 443 으로 불러도 Location 이 http:// 라 따라가는 클라이언트가 평문으로 내려간다(11-13 14:0x 실측).

- **바꿀 것:** -mcp id 묶음에 'location = /<id>/mcp/ { return 308 /<id>/mcp; }' 같은 줄, 또는 앱 Location 을 고쳐 쓰는 proxy_redirect.

- **위치:** HWAXPortal infra/scripts/gen-nginx-conf.sh loc_extras '*-mcp)' :86-94 · loc_block

- **확인:** 중계를 안 거치는 경로 하나에 POST …/mcp/ 로 initialize → 200, 또는 308 의 Location 이 /<id>-mcp/mcp.

- **선례:** 720caa4b (같은 *-mcp 갈래)

- **참고:** 지금은 사용자에게 끝 슬래시 없는 주소만 알려 피한다. 평문 강등 소지가 있어 HP-75 와 함께 보면 좋다.



#### HP-82 · core_vocab types 에 부품(part) · lookup 에 결함 목록 줄

`P2` · 새 요청



- **문제:** types 에 part 가 없어 ontology_lookup('실드캔 부품') 이 부품을 못 고르고 관리 기준 1건만 후보로 준다(type=part 를 주면 exact PRT-SHIELD_CAN). card-entity-bind.py 기본 타입에서도 빠진다. lookup FailureTrace 줄은 object_resolve 하나.

- **바꿀 것:** types 에 '부품': part 를 더한다. lookup.failuretrace 를 사전 하나에서 아래 두 줄의 목록으로 바꾼다. ① {"tool": "object_resolve", "args": {"type_slug": "{type_slug}", "name": "{key}"}} ② {"tool": "objects_list", "types": ["part"], "args": {"type_slug": "pd_defect", "limit": 20, "conditions": [{"field": "ref.part.key", "op": "eq", "value": "{key}"}]}, "_doc": "그 부품의 PLM 결함 — 수는 total, 묶음은 objects_summary"}. 넣기 전에 함께 볼 셋: _onto_pick 이 '부품' 을 타입 낱말로 고름 · card-entity-bind 기본 타입에 part 가 들어 카드가 부품에 이어짐 · 심의 '온톨로지 먼저 보기' 이웃 타입에 part(상한 60 · 4,000자 그대로라 다른 이웃이 밀림).

- **위치:** HWAXPortal backend/config/core_vocab.json:35(types) · :76-80(ontology.lookup) · infra/scripts/card-entity-bind.py:186(--types 기본) — HEAD 9b34a4ea

- **확인:** ontology_lookup('실드캔 부품') 이 exact, next 에 FailureTrace 결함 목록 줄

- **선례:** d1686bc8(OL-3 lookup 칸)

- **먼저:** OL-6(게이트웨이가 lookup 줄의 목록 꼴과 안쪽 {key} 채우기를 받아야 ② 줄이 돈다) · 카드를 다시 잇기 전에는 AD-22(AIDataHub bind_entities 가 허브 연결을 타입과 상관없이 지움)와 HPO-2(--only-types 증분) · 부품 낱말 잡음 정리(뺄 낱말 64개는 11-24 에 운영 박스 덧씌우기 onto_rules.local.json 에 넣었다. 뜻이 섞인 낱말 25개를 뺄지는 운영 쪽이 아직 고르지 않았다)

- **참고:** cae00 박스 덧씌우기로도 더할 수 있으나 HPO-1 이 들어와 박스 파일을 지울 때 사라진다. 그래서 박스 덧씌우기 types 에는 지금 더하지 않고 저장소에 넣기로 운영 쪽 사용자가 정했다(11-24). 부품을 지금 사전으로 이으면 링크 441,460 · 카드 52,098장(뜻이 다른 낱말 49개를 빼면 링크 197,530).



#### HPO-2 · card-entity-bind.py 타입별 증분 모드(--only-types)

`P2` · 새 요청



- **문제:** --types 로 한 타입만 돌려도 링크 전부를 다시 쓴다. 부품 하나를 더하려고 링크 34만 개(11-23 345,344)를 다시 써야 해서 운영 쪽이 미루고 있다.

- **바꿀 것:** --types 를 주면 그 타입의 링크만 지우고 다시 쓰는 증분 모드(--only-types)를 두고, summary 에 타입별 전후 수를 적는다. 포털 쪽 멈춤 장치도 함께 넣는다 — --types 가 기본 타입보다 적으면 「다른 타입 연결이 지워진다」 를 찍고 멈춘다. AD-22 가 먼저 들어오면 멈춤 장치는 필요 없다.

- **위치:** HWAXPortal infra/scripts/card-entity-bind.py(:186 --types) · AIDataHub api_server/src/api/services/onto_svc.py:402-403 bind_entities

- **확인:** card-entity-bind.py --only-types part → 부품 링크만 늘고 다른 타입 수는 그대로.

- **선례:** 6a7b367c(11-20 card-entity-bind.py)

- **먼저:** AD-22(AIDataHub api_server/src/api/services/onto_svc.py:402-403 bind_entities 가 delete(RecordEntity).where(RecordEntity.hub == hub) 로 그 허브의 연결을 타입과 상관없이 통째로 지우고 다시 쓴다)

- **참고:** 포털만 고쳐서는 안 된다 — 지우기가 AIDataHub 안에 있다(AD-22). 다음 카드 잇기 전에 둘이 함께 들어가야 안전하다. 포털 쪽 멈춤 장치도 이 항목에 함께 넣는다 — --types 가 기본 타입보다 적으면 「다른 타입 연결이 지워진다」 를 찍고 멈춘다(AD-22 가 먼저 들어오면 필요 없다). AIDataHub 부품 타입 결합(부록 A D-2 — 11-24 사용자 결정 '증분 뒤', 아직 돌리지 않음)이 이것을 기다린다.



#### HPO-3 · 개발모델 · 과제 · 관리 기준 링크 0 의 까닭을 summary 에 타입별로 (유도 규칙은 선택)

`P2` · 새 요청



- **문제:** 11-23 결합 summary 에서 개발모델 · 과제 · 관리 기준 링크가 0 이다.

- **바꿀 것:** 0 인 까닭(카드에 그 이름이 없는지 · 규칙이 그 타입을 보지 않는지)을 summary 에 타입별로 적는다. 과제는 과제코드 별칭으로, 관리 기준은 이미 묶인 테스트의 코어 관계로 가도록 하는 선택 규칙을 둔다.

- **위치:** HWAXPortal infra/scripts/card-entity-bind.py summary_text(:155)

- **확인:** summary 에 타입별 0 사유 칸, 선택 규칙을 켜면 과제 · 관리 기준 링크가 0 보다 큼.

- **선례:** 6a7b367c

- **참고:** 링크 0 이라는 사실은 개발 쪽이 11-23 에 받아 들고 있다(HWAXPortal docs/leftovers-1121/context-notes.md:440 — L21-24 의 7). 새로 청하는 것은 summary 의 까닭 칸이다. 과제 · 관리 기준 유도 규칙은 낱말 쪽 사용자 결정(23-U1) 뒤에 켜는 선택으로 둔다.



#### HPO-4 · core_vocab.json apps 에 MountSol · NCDev 형제(sibling) 두 줄

`P2` · 새 요청



- **문제:** MountSol · NCDev 를 게이트웨이에서 형제(sibling)로 두기로 운영 쪽 사용자가 정했다(11-24). 그 값이 cae00 박스 덧씌우기 파일에만 있다.

- **바꿀 것:** core_vocab.json 맨 위 apps 에 아래 두 줄을 FailureTrace · CAE그룹 줄과 같은 꼴로 넣는다. "mountsoldatahub": {"role": "sibling", "label": "실장솔루션 Datahub"}, "ncdevdatahub": {"role": "sibling", "label": "NC개발팀 Datahub"}. 에이전트 서버가 읽는 ontology.apps 는 건드리지 않는다.

- **위치:** HWAXPortal backend/config/core_vocab.json apps

- **확인:** 박스 파일을 지운 뒤 /health core_vocab.roles.family 가 여전히 다섯(코어 · FailureTrace · CAE그룹 · MountSol · NCDev).

- **선례:** c398230f(10-29 core_vocab apps 역할 — request-1029 B-1 · C-11)

- **참고:** 형제로 두면 좁힌 MCP 목록 · 포털 보기 셈에서 두 앱 도구가 빠지고 list_tool_apps canonical 이 거짓이 된다(search_tools · invoke_tool 은 그대로).



#### IR-04 · DocForge 권한이 없는 사람의 AI 데이터 허브 변환 길에도 판독 · 안내

`P2` · 새 요청



- **문제:** plat:docforge 가 없는 사람은 AI 데이터 허브 변환기로 가고, 그 글은 그림마다 '그림 내용은 글로 옮기지 않았다' 로 끝나 판독할 길이 아예 없다.

- **바꿀 것:** 이 길에도 판독이 붙게 한다(AIDataHub IR-31 이 되면 그 결과를 쓴다). 그전까지는 이 길에서 IR-03 의 문구를 반드시 보인다.

- **위치:** HWAXPortal backend/app/agent/routes.py chat 갈래의 AIDH 대체 길(HEAD :2172 부근 뒤) · backend/app/agent/upload.py:490

- **확인:** plat:docforge 없는 계정으로 그림 있는 덱을 붙이면 판독 글이 들어가거나, 최소한 IR-03 문구가 보인다.

- **먼저:** IR-31 · IR-03

- **참고:** DocForge 권한(plat:docforge)을 지금 범위 밖으로 넓히지 않고 그대로 두기로 했다(사용자 11-10, §4 S-4 [22-1]). IR-24 가 들어오면 다시 묻는다. 그래서 권한이 없는 사람에게는 이 길이 계속 쓰인다.



#### IR-05 · 새 대화를 열면 붙인 문서 칩 비우기

`P2` · 새 요청



- **문제:** 붙인 문서가 대화가 아니라 입력창에 매여 있어, 새 대화 첫 화면에도 앞 대화의 문서 칩이 남고 다른 주제로 시작한 질문에 앞 문서가 딸려 간다(11-10 실측).

- **바꿀 것:** 새 대화를 열면 붙인 문서를 비운다. 또는 대화마다 따로 들고, 다른 대화로 옮길 때 묻는다.

- **위치:** HWAXPortal frontend/src/state/ChatContext.tsx:1527-1531(newConversation) · :551-557

- **확인:** 문서를 붙인 뒤 새 대화를 열면 칩이 없고 첫 질문에 문서가 실리지 않는다.

- **참고:** 판독과 별개인 결함이다.



#### IR-06 · 보낼 곳 고르기에서 'RA 가져오기' 와 '정밀 변환' 의 차이 보이기

`P2` · 새 요청



- **문제:** 'Report Archive 로 보내기' 를 그림 · 표가 들어가는 길로 소개하지만, 실제로는 이 길이 그림 내용 · 차트 개체 · 발표자 노트 · 그림 채움을 뺀다(시험한 네 길 가운데 가장 많이 빠짐).

- **바꿀 것:** 고르기 전에 두 길의 차이를 보인다. 그림 · 차트 · 노트가 있는 덱이면 정밀 변환을 앞에 두거나 기본으로 한다.

- **위치:** HWAXPortal frontend/src/components/chat/DocDispatchPanel.tsx:20 · DocExtractHint.tsx:140 · UploadRouter.tsx

- **확인:** 차트 · 노트가 있는 덱을 고를 때 정밀 변환이 앞(기본)에 있고, RA 가져오기 설명에 빠지는 것이 적혀 있다.

- **먼저:** IR-42(PPTX 가져오기 /api/imports/pptx 가 차트 개체 · 발표자 노트 · 그림 채움 도형을 옮기게 함)가 들어오면 RA 가져오기 설명 문구를 다시 맞춘다

- **참고:** IR-44(PPTX 가져오기의 그림 판독을 DocForge 에 맡기기)를 따로 만들기보다, 포털이 '정밀 변환' 결과를 넘기는 이 길이 더 쉽다.



#### IR-07 · DocForge 판단(llm) 옵션을 넘기기

`P2` · 새 요청



- **문제:** DocForge 의 LLM 판단(그림 바로 아래 글이 그 그림의 설명인가)은 요청 옵션 llm 이 켜질 때만 돈다(mcp_server.py:66 기본 끔 · structure/mapper.py:28). 포털은 어느 길에서도 이 값을 넘기지 않아, 판단 모델을 따로 정해도 한 번도 불리지 않는다.

- **바꿀 것:** 정밀 변환 · 대화 분석에서 llm: true 를 넘긴다. 판단은 JSON 스키마로 짧게 끝나고 캐시도 있다(decide.py:111-118).

- **위치:** HWAXPortal backend/app/agent/routes.py:2137-2138 · :2160-2161(HEAD)

- **확인:** 정밀 변환 잡 뒤 DocForge 판단 캐시에 새 항목이 생기고, 캡션 판단 실패 줄이 없다.

- **선례:** 박스 설정 S-2 [22-1](부록 A — 11-10, DocForge 판단 모델을 심의 모델로, knobs.env) 뒤 시험 잡에서 판단이 심의 모델로 가고 새 판단 캐시가 생긴 것을 확인했다. 포털이 llm 을 켜지 않아 실제 대화에서는 아직 불리지 않는다.

- **먼저:** IR-08

- **참고:** 그림 바로 아래 글이 그 그림의 설명인지 가리는 판단을 켜는 일이다. 넣는 순서는 일곱째다(첫째 묶음은 IR-01 · IR-03 · IR-08).



#### IR-08 · vlm · snapshot_page · llm 세 값을 포털 설정으로 빼기

`P2` · 새 요청



- **문제:** IR-01 · IR-02 · IR-07 의 값이 코드에 박혀 있어, 챗 모델이 바쁜 날 운영 쪽이 재배포 없이 끄고 켤 수 없다.

- **바꿀 것:** 세 값을 infra/.env 로 빼고 길(대화 분석 · 정밀 변환)마다 따로 둔다.

- **위치:** HWAXPortal backend/app/agent/routes.py:2137-2138(정밀 변환 갈래) · :2160-2161(대화 분석 chat 갈래) — HEAD 9b34a4ea · infra/.env 예시

- **확인:** infra/.env 값만 바꾸고 포털 재기동만으로 대화 분석의 판독을 끄고 켤 수 있다.

- **참고:** 들어오면 운영 쪽이 cae00 포털 infra/.env 에 대화 분석 · 정밀 변환 판독 · 쪽 그림 · 판단 켜기 값을 넣는다(이름은 그 판에서 확인).



#### SE-2 · §1b 배포 전 백업의 AIDataHub 덤프 시간 줄이기

`P2` · 새 요청



- **문제:** 10-28 · 10-29 · 11-01 · 11-03 · 11-05 의 §1b 가 28분 06초 ~ 29분 18초 걸렸고 그중 AIDataHub 덤프가 27 ~ 28분이다. 11-05 에는 03:30 일일 백업(11,168,745,135 바이트)이 끝나고 2시간 27분 뒤 같은 DB 를 다시 떴다(11,168,745,141 바이트). 그 사이 WAL 은 51 kB 뿐이었다.

- **바꿀 것:** 1) §1b 의 AIDataHub 덤프를 백그라운드로 시작하고, deploy-all 의 AIDataHub 재기동(boot.sh --force) 앞에서 끝나기를 기다린다. 실패하면 지금처럼 멈춘다. 2) 압축을 여러 코어로(pg_dump -Fc -Z0 + zstd -T0, 또는 -Fd -j). 운영 서버는 16코어 · zstd 있음 · pigz 없음. 형식을 바꾸면 복원 스크립트도 받게 한다. 3) 정책: 03:30 일일 덤프가 N시간 안이면 배포 전 롤백 지점으로 써도 되는지 사용자와 정한다(그 뒤 쓰기는 롤백 때 잃는다). 4) update-all 이 만드는 덤프 · 병합 전 덤프는 7일 보관과 따로 최근 1 ~ 2개만 남긴다.

- **위치:** HWAXPortal infra/scripts/update-all.sh:515-522(§1b) · infra/scripts/backup-local.sh:117(pg_backup) · infra/scripts/deploy-all-from-drive.sh:460(AIDataHub 재기동) — HEAD 9b34a4ea

- **확인:** 다음 실행 기록에서 AIDataHub 덤프 파일의 수정 시각이 AIDataHub 재기동보다 앞서고 §1b + §2 합계가 줄었다. 새 형식 덤프를 시험 DB 에 복원해 본다.

- **먼저:** 3번은 SYNCEFF-4 의 사용자 결정(03:30 일일 덤프를 배포 전 롤백 지점으로 쓸지 · §1b 와 병합 전 덤프를 따로 두려던 의도가 있었는지)

- **참고:** 1번만으로 최대 약 18분(§2 길이, 추정), 3번을 택하면 약 28분과 11 GB 쓰기가 준다. alembic 이행 전 롤백 지점은 반드시 남기고 sha256 파일은 계속 만든다. 작은 대상은 지금처럼 매번 떠도 된다. 11-05 반영 뒤 가장 큰 남은 몫이다.



#### SE-7 · SignalForge 병합에서 덤프를 두 번 받지 않기 · 받는 쪽 보관 개수

`P2` · 새 요청



- **문제:** deploy-all 이 SignalForge 병합에 동기화 단계가 받은 덤프를 넘기지 않아, 두 단계 사이에 새 덤프가 올라온 실행(11-01 · 10-25)은 다른 덤프 두 개를 받았다. 11-03 이 묶음은 약 8분(추정). 받는 쪽 backups/ 에는 정리 규칙이 없어 267개 · 33,067,645,290 바이트(덤프 94 · sha256 91 · 병합 전 스냅숏 79)가 쌓였다. 11-24 에 다시 세면 291개 · 약 39G(병합 전 스냅숏 87)로 더 늘었다.

- **바꿀 것:** 1) deploy-all-from-drive.sh 의 SF 병합 호출에 SF_MERGE_DUMP="$(readlink -f backups/sf-db-latest.sql.gz)" 를 넘긴다(한 줄). 2) 마지막으로 병합한 덤프의 이름 · 해시를 적어 같으면 스냅숏 · 적재 · 뷰 새로 고침을 건너뛴다. 3) SignalForge 의 thin_dumps 규칙을 받는 쪽 덤프와 sf-db-pre-merge-* 에도 적용한다. 4) 길게는 마지막 병합 뒤 바뀐 행만 내보내기 · 바뀐 원천 표의 뷰만 새로 고치기를 검토한다.

- **위치:** HWAXPortal infra/scripts/deploy-all-from-drive.sh:429-433 · SignalForge scripts/drive-sync/merge-from-drive.sh:71 · scripts/sync-from-drive.sh · scripts/drive-sync/backup-to-drive.sh:78 · :107

- **확인:** 다음 실행 기록에서 SignalForge 덤프 다운로드 줄이 한 번만 나온다. backups/ 파일 수가 정리 규칙을 넘지 않는다.

- **선례:** SignalForge merge-from-drive.sh 의 SF_MERGE_DUMP 입력(:56) · backup-to-drive.sh thin_dumps

- **참고:** 1번은 HWAXPortal, 3번은 SignalForge 몫이다. 디스크 약 28 GB 가 비는 것(추정)이 시간보다 크다 — 운영 서버 /data 가 11-17 · 11-18 에 찼던 일이 있어 우선을 한 단계 올렸다. id 번역 · 300행 표본 대조 · 바뀐 행만 쓰기 · 삭제 반영(11-05 links 3,759건)은 그대로 둔다.



#### WD-05 · 웹 '이어하기' 가 엔진 deliberate_continue 를 부르게

`P2` · 새 요청



- **문제:** 웹 이어하기와 MCP 이어하기가 서로 다른 길이라 이어받는 손잡이가 다르다. MCP 로 연 심의를 웹에서 이으면 같은 잡 계보가 아니라 새 심의가 생긴다.

- **바꿀 것:** 대화에 job_id 가 있으면 웹 이어하기가 deliberate_continue 로 보낸다(새 웹 심의를 열지 않는다).

- **위치:** HWAXPortal frontend/src/state/ChatContext.tsx — 웹 '이어하기' 가 엔진 이어하기가 아니라 새 웹 심의를 여는 자리(11-10 판 d49d58fe 기준 :1206–1290)

- **확인:** MCP 로 연 심의 대화에서 이어하기를 누르면 같은 잡 계보의 다음 잡이 생기고 _CONT_CARRY 손잡이가 이어진다.

- **선례:** 엔진 쪽은 반영됨 — 에이전트 서버 e7df642(10-22 심의 운영 R1~R3: 끊긴 잡을 deliberate_continue(previous_job_id=…) 한 번으로 이음) · F1(남의 잡 이어하기). 포털 ff066412(10-31)는 웹 이어하기가 앞 회차 기준일을 잇게 했을 뿐이고, 그 주석대로 MCP 이어하기는 원장의 _CONT_CARRY 로 따로 잇는다. 포털 쪽 배선만 남았다.

- **먼저:** WD-03(대화에 job_id 가 있어야 한다)



#### HP-58 · env-sync 가 AIDataHub deploy/apptainer/.env 를 보지 않음

`P3` · 새 요청



- **문제:** env-sync.sh 하위 경로가 "" · /infra · /platform 뿐이라 AIDataHub 의 deploy/apptainer/.env 새 키가 조용히 빠진다. 11-01 에 예시가 권하는 AIDH_RECOMMEND_CANDIDATE_SECTIONS=300 이 박스에 없어 50 으로 돌았다(그날 박스에서 300 으로 맞춤).

- **바꿀 것:** 하위 경로에 /deploy/apptainer 를 더한다(자동 추가가 싫으면 --check 에서 알리기만).

- **위치:** infra/scripts/env-sync.sh:65 · :77 · :178-181 (discover)

- **확인:** env-sync.sh --check 가 AIDataHub/deploy/apptainer/.env 에 빠진 키를 이름으로 보인다

- **선례:** env-sync 3ba5fdac · bfab40e3 (같은 스크립트의 앞선 고침)



#### HP-61 · 받은 편지함 · server-setup 의 명령이 운영 박스와 맞지 않음(sqlite3 -readonly · 낡은 app_data 경로)

`P3` · 새 요청



- **문제:** 운영 박스에는 sqlite3 CLI 가 없어 `sqlite3 -readonly` 가 돌지 않고, ~/Projects/HEAXHub/var/app_data/<앱>/ 은 낡은 사본이다(실제는 HWAX_DATA_ROOT 아래 /data/appdata/<앱>/). MaterialTwin 은 7.2 GB 옛 사본이 남아 명령이 조용히 낡은 값으로 답한다(docs/cae00-inbox/2026-10-31.md Q1 — MaterialTwin DB 조회).

- **바꿀 것:** 명령을 python sqlite3.connect('file:…?mode=ro', uri=True) 꼴로 바꾸고, 경로는 ${HWAX_DATA_ROOT:-…}/appdata/<앱> 처럼 박스 값에서 짓는다. 앞으로 쓰는 안내도 같은 꼴로.

- **위치:** HWAXPortal docs/cae00-inbox/*.md · docs/request-1030/server-setup.md (11-01 기준 6곳)

- **확인:** docs/cae00-inbox · docs/request-*/server-setup.md 에 `sqlite3 -readonly` · var/app_data grep 0

- **선례:** HP-40(점검표 경로 고침 0eb5041)

- **참고:** 11-02 받은 편지함은 mode=ro 꼴과 옛 꼴이 섞여 있다.



#### HP-68 · update-all 장애 안내 문구가 로컬 :8700 · :8701 과 deploy-all kooremapper 를 권함

`P3` · 새 요청



- **문제:** 전환 뒤 이 안내대로 하면 멈춰 둔 사본 쪽을 보게 되고, 실제 업스트림(운영 노드)은 안내에 없다.

- **바꿀 것:** 멈춤(또는 바깥 DynaForge)일 때 실제 업스트림(KOORM_BASE 와 그 MCP)을 적고 조치로 '운영 노드 쪽을 본다' 를 적는다. 동작은 그대로.

- **위치:** HWAXPortal infra/scripts/update-all.sh:3633 · :3711-3712 (포털 9f1b3ddc 판에서는 :3466 · :3544)

- **확인:** KOORM_LOCAL_PARKED 상태에서 heax kooremapper_mcp 가 502 · 도구 0 일 때 안내 줄에 :8700 · :8701 과 deploy-all kooremapper 권유가 나오지 않는다.

- **선례:** fc56fb28 의 hwax_koorm_parked 판정(lib/koorm-parked.sh)을 그대로 쓰면 된다

- **참고:** 멈춤 표시가 있으면 안내대로 deploy-all kooremapper 를 돌려도 deploy-all-from-drive.sh:486-513 에서 건너뛰므로 해는 없다. 말만 어긋난다.



#### HP-69 · update-forges.sh stepforge 가 proxy 로 덮어쓴 step_forge 를 다시 지으려다 exit 2

`P3` · 새 요청



- **문제:** 전환 때 step_forge 덮어쓰기가 source 를 비우고 launch.mode: proxy 로 두므로 update-forges.sh stepforge 가 redeploy-app.sh --rebuild 에서 멈춘다.

- **바꿀 것:** manifest.local.yaml 이 있고 proxy(또는 source 없음)면 건너뛰고 '운영 노드 판은 그쪽 묶음 올리기로' 안내. :190 재기동 길도 같게.

- **위치:** HWAXPortal infra/scripts/update-forges.sh:156-166(:162) · :190 · :209; HEAXHub deploy/apptainer/redeploy-app.sh:243-251

- **확인:** 덮어쓰기를 둔 박스에서 update-forges.sh stepforge 가 실패 없이 '건너뜀' 을 찍는다.

- **선례:** HEAXHub redeploy-app.sh:143-146 (proxy 앱 따로 다룸)

- **참고:** 실패가 깨끗한 exit 2 라 피해는 없다. 박스는 update-forges.sh stepforge 를 쓰지 않는 것으로 피한다. 운영 쪽이 처음 매긴 급함은 중간이다.



#### HP-75 · MCP 직결 경로가 평문 포트 8088 에도 열림

`P3` · 새 요청



- **문제:** 새 *-mcp 경로가 8088 평문에서도 답한다(11-13 실측 8 경로 initialize 200). MCP 클라이언트는 Authorization: Bearer 를 매 요청에 실으므로 http 주소를 등록하면 개인 토큰이 사내망에 평문으로 흐른다.

- **바꿀 것:** -mcp 로 끝나는 id(또는 박스 파일에서 고른 id)는 TLS 블록에만 내는 선택. 8088 쪽은 내지 않거나 443 으로 돌린다. 기본값은 지금처럼 둬도 된다.

- **위치:** HWAXPortal infra/scripts/gen-nginx-conf.sh 두 server 블록 생성부(:374 부근) · infra/nginx/hwax.conf.tmpl:78

- **확인:** 선택을 켜고 gen-nginx-conf.sh · nginx -t 뒤 8088 의 /<id>-mcp/mcp 가 404 이거나 443 으로 돌고, 443 은 initialize 200.

- **선례:** 7e300337 (템플릿 · TLS 블록 둘 다 손댄 nginx 고침)

- **참고:** 운영 쪽이 처음 매긴 급함은 낮음이다(지금은 https 주소만 알려 피함). 토큰 평문 소지라 P2 로 올려도 된다.



#### SE-9 · update-all · deploy-all 실행 기록의 단계 제목에 시각 찍기

`P3` · 새 요청



- **문제:** 단계 제목 줄에 시각이 없어, 11-05 동기화 효율 조사(SE-1 ~ SE-8)의 구간 시간은 단계가 만든 파일 이름의 시각 · 그 파일의 수정 시각 · 재기동 지문 파일(infra/.state/restart-fp/*)의 수정 시각으로 다시 맞춰야 했다.

- **바꿀 것:** hr() 와 deploy-all 블록 제목에 [HH:MM:SS] 시각을 함께 찍는다(update-all.sh §4 는 이미 [HH:MM:SS] 를 찍는다). 기존 제목 문구는 그대로 둔다.

- **위치:** HWAXPortal infra/scripts/update-all.sh:119-133(hr) · infra/scripts/deploy-all-from-drive.sh:165(hr)

- **확인:** 다음 실행 기록에서 모든 단계 제목 줄에 시각이 붙고, 기록을 grep 하는 기존 스크립트가 그대로 돈다.

- **선례:** update-all §4 의 [HH:MM:SS] 표기

- **참고:** SE-1 ~ SE-8 의 효과를 실행 기록만으로 재기 위한 것이다.



#### SYNCEFF-3 · aidh-parts-sync 문서끼리 어긋난 두 곳 고치기

`P3` · 새 요청



- **문제:** checklist 는 목록을 7판 둔다고, AP-11 은 3판으로 줄였다고 적는다. AP-8 은 병합 전 덤프를 4.4 GB 로 적지만 운영 서버에서는 약 11.2 GB 다.

- **바꿀 것:** checklist.md:7 을 3판으로, AP-8 의 크기를 약 11.2 GB 로 고친다.

- **위치:** HWAXPortal docs/aidh-parts-sync/checklist.md:7 · context-notes.md:40

- **확인:** 두 문서의 판 수 · 크기가 코드(779e112 3판)와 운영 실측과 맞다.

- **선례:** AIDataHub 779e112(목록 보관 7판 → 3판)

- **참고:** SE-4 5번(backup-local.sh 주석)과 같이 보내면 된다.



#### WD-11 · '이 대화에서 분석' 길의 DRM 감지

`P3` · 새 요청



- **문제:** DRM 으로 잠긴 파일인데도 '이 대화에서 분석' 이 성공 메시지와 함께 260자만 읽었다고 알린다.

- **바꿀 것:** 이 길에서도 DRM 머리를 감지해 '변환 못 함 — DRM' 으로 표시한다(docAttach.ts DRM_HEAD 재사용).

- **위치:** HWAXPortal frontend/src/components/chat/UploadRouter.tsx · destApps.ts(DocForge 부르는 길) · docAttach.ts DRM_HEAD 재사용

- **확인:** 잠긴 PPT 를 넣으면 성공 대신 DRM 안내가 뜬다.

- **선례:** HP-14(2043930 — 첨부 길의 DRM 머리 감지, docAttach.ts:34 DRM_HEAD). 새 대화에 앞 칩이 남는 문제는 IR-05 로 따로 청했다.

- **참고:** 새 대화에서 칩 비우기는 IR-05 로 따로 청한다(같은 일을 두 번 청하지 않으려고 여기서 뺐다).



### 1-2. 게이트웨이 (HWAXMcpGateway) — 10건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| BG-3 | artifact_to_ste_upload 남은 확인 — 100 MB 급 · cavity_step | P0 | 받았으나 안 끝남 |

| OL-6 | ontology.lookup 앱별 줄 여럿 · 안쪽 칸까지 {key} 채우기 | P1 | 새 요청 |

| WD-04 | save_conversation 이 활동을 지키고 다시 열 때 근거로 되살리며 사이드바를 바로 갱신 | P1 | 새 요청 |

| CT-01 | tool_areas.json apps 에 circuittrace 를 품질 영역으로 | P2 | 받았으나 안 끝남 |

| HG-24 | 게이트웨이 시간 한도를 박스 설정으로 줄 자리가 없음 | P2 | 새 요청 |

| MEMORY-1 | 게이트웨이 부팅 경합 — 첫 지문은 재집계를 하지 않음 | P2 | 새 요청 |

| PT-2 | 도구 앱 목록의 StepForge 줄에 build · instance | P2 | 받았으나 안 끝남 |

| CT-02 | 영역 표에 빠진 앱 셋 알림(mountsoldatahub · ncdevdatahub · testscope) | P3 | 받았으나 안 끝남 |

| CT-03 | 도구 등록 점검표에 '영역' 줄 | P3 | 받았으나 안 끝남 |

| OL-7 | ontology_lookup none 답에 StepForge identify_part 로 다시 가라는 한 줄 | P3 | 새 요청 |



#### BG-3 · artifact_to_ste_upload 남은 확인 — 100 MB 급 · cavity_step

`P0` · 받았으나 안 끝남



- **문제:** part_step 155,360 B 와 240,542 B 는 sha256 이 맞게 올라갔고, 그 업로드로 part-study 가 돌았다. 큰 파일(11-17 과제 전체 STEP 129.7 MB)과 cavity_step 종류는 보지 못했다. 같은 업로드에 scenario.json 을 더할 길도 없었다.

- **바꿀 것:** 과제 전체 worked_step(100 MB 급)과 cavity_step 을 artifact_to_ste_upload 로 dev 에서 한 번 옮겨 sha256 이 맞는지 본다. 시나리오 더하기는 ste submit_job 쪽에서 풀기로 해서 게이트웨이에 새 도구는 두지 않는다.

- **위치:** HWAXMcpGateway artifact_to_ste_upload(ec91b62)

- **확인:** 과제 전체 worked_step(100 MB 급)과 cavity_step 을 artifact_to_ste_upload 로 옮기면 sha256 이 맞아야 한다.

- **선례:** HWAXMcpGateway ec91b62(11-18 artifact_to_ste_upload 첫 판)

- **먼저:** cavity_step 확인은 StepForge build_cavity 가 실제 공동을 한 번 내야 할 수 있다 — SF-1(build_cavity 파트 목록 인자 · 접수 검사)은 D-708 에 들어갔으나 공동이 나온 기록은 아직 없다. 100 MB 급 확인은 지금 할 수 있다.

- **받은 곳 · 상태:** 받음 — HWAXPortal docs/ste-stepforge-1117/checklist.md 에 '[x] BG-3 · ST-10 업로드에 scenario.json 더하기 — ste 가 받는다 … 게이트웨이에 새 도구 없음' 이 있다(시나리오 더하기는 ste submit_job 으로 풀림). 아직 안 됨 — 같은 점검표의 '[ ] BG-3 큰 파일(100 MB 급) · cavity_step 을 dev 에서 한 번 옮겨 보기' 가 열려 있다. 100 MB 급 과제 전체 STEP 과 cavity_step 을 artifact_to_ste_upload 로 옮겨 sha256 을 맞추는 확인이 남았다.

- **참고:** 시나리오 더하기는 ste 쪽으로 풀기로 해서 게이트웨이 새 도구는 없다. 남은 것은 큰 파일 · cavity_step 확인 하나다. StepForge 조각마다 파일 전체를 다시 읽던 문제는 D-707 에서 seek · sha 한 번으로 고쳐졌다(HWAXPortal docs/ste-stepforge-1117/context-notes.md SS-7).



#### OL-6 · ontology.lookup 앱별 줄 여럿 · 안쪽 칸까지 {key} 채우기

`P1` · 새 요청



- **문제:** 어휘표 ontology.lookup 은 앱마다 줄 하나(사전 키)이고 칸 채우기는 맨 위 글자 칸만 한다. 그래서 '부품 X 의 PLM 결함 목록'(conditions 목록 안의 key)을 next 로 실을 수 없고, 모델이 둘째 걸음(ref.part.key)을 스스로 알아야 해 11-16 평가처럼 다른 도구로 샌다.

- **바꿀 것:** ontology.lookup.<앱> 이 사전 하나 또는 사전의 목록을 받게 한다 — 목록이면 줄마다 types 로 거르고 차례대로 next 에 싣는다. 칸 모으기 · 채우기를 목록 · 사전 안쪽 글자까지 넓힌다. 바라는 꼴: _onto_slots(v) — 글자면 {m.group(1) for m in _ONTO_SLOT.finditer(v)}, 목록이면 원소마다 · 사전이면 값마다 _onto_slots 를 모아 합치고(비면 set()), 그 밖은 set(). _onto_fill_deep(v, obj) — 목록이면 [_onto_fill_deep(x, obj) for x in v], 사전이면 {k: _onto_fill_deep(x, obj) for k, x in v.items()}, 그 밖은 _onto_fill(v, obj)(맨 위 글자는 지금과 같다).

- **위치:** HWAXMcpGateway gateway.py(HEAD c43382b) :6252 _ONTO_SLOT · :6256 _onto_lookup_rows · :6263 앱별 줄 돌기(rows.items(), 사전만 받음) · :6345 _onto_fill · 맨 위 글자 칸만 모으고 채우는 두 자리(need = … · line = …, e758907 기준 :6366 · :6371)

- **확인:** HP-82 의 FailureTrace 두 줄(object_resolve 줄 + types [part] 인 pd_defect objects_list 줄, conditions [{field ref.part.key, op eq, value "{key}"}])을 넣으면 ontology_lookup('실드캔', type=part) 의 next 에 object_resolve 와 pd_defect objects_list 두 줄이 실리고, conditions 안 value 가 PRT-SHIELD_CAN 으로 채워진다. 기존 사전 꼴 줄은 결과가 같다.

- **선례:** c75bc05(OL-1 · OL-2 첫 판)

- **참고:** 11-17 OL-3 착지(포털 d1686bc8) 때 lookup 줄에 types 칸을 쓰지 않았다 — 어느 앱이 어느 타입을 받는지는 박스 설정으로 두었다(HWAXPortal docs/cae00-inbox/2026-11-17.md OL-3 줄). 그래서 줄별 types 거르기 꼴은 새로 정해야 한다. HP-82 의 결함 목록 줄이 이것을 기다린다.



#### WD-04 · save_conversation 이 활동을 지키고 다시 열 때 근거로 되살리며 사이드바를 바로 갱신

`P1` · 새 요청



- **문제:** MCP 쪽에서 저장한 대화는 meta 에 non_negotiable · rebut 만 남고 도구 활동을 잃는다. 웹에서 열어 '원 도구 결과가 있니?' 라고 물으면 근거가 0건이고, 사이드바는 새로 고쳐야 보인다.

- **바꿀 것:** save_conversation 이 activity(도구 · 인자 · 결과)를 받아 meta 에 둔다. 다시 열 때 그것을 근거로 싣는다. 저장 뒤 사이드바를 새로 고침 없이 갱신한다.

- **위치:** HWAXMcpGateway gateway.py save_conversation(11-10 판 c47e883 기준 :2344–2596 — MCP 쪽 자동 저장이 없고, 저장 때 meta 에 non_negotiable · rebut 만 남김) · HWAXPortal conversations.api.ts:147(meta.activity 가 있어야 근거를 되살림, 11-10 판 d49d58fe) · 대화 목록 사이드바 갱신

- **확인:** MCP 로 저장한 대화를 웹에서 열고 '원 도구 결과가 있니?' 라고 물으면 결과를 원문 그대로 인용한다.

- **선례:** 웹 대화의 앞 턴 근거 되살리기는 이미 반영됐다(포털이 meta.activity 로 근거를 되살림). 같은 되살리기를 MCP 저장 대화에도 적용한다.

- **참고:** 포털 몫(사이드바 갱신 · 근거 싣기)도 함께다.



#### CT-01 · tool_areas.json apps 에 circuittrace 를 품질 영역으로

`P2` · 받았으나 안 끝남



- **문제:** circuittrace 도구 6개가 미분류다. 개인 Claude 묶음 보기와 도구 고르기 묶음에서 빠진다.

- **바꿀 것:** apps 표에 "circuittrace": "quality" 한 줄을 더한다.

- **위치:** HWAXMcpGateway tool_areas.json apps

- **확인:** /tools-map 미분류에서 circuittrace 6 → 0 이 되고, 묶음 보기의 품질 영역에 나온다.

- **선례:** 2185b4c(HG-30)

- **받은 곳 · 상태:** 받음 — dev 가 HWAXPortal docs/cae00-inbox/2026-11-23.md:194 에 '남은 둘(새 앱 넷의 인자 설명 · 도구 영역, 카드 ↔ 허브 잇기의 낱말 판단)은 이번에 싣지 않았다' 고 적었다. 요청 사본은 CircuitTrace docs/requests/REQUEST-20261121-도구영역분류.md 에 있다. 아직 안 됨 — docs/cae00-inbox/2026-11-24.md:11 게이트웨이 줄의 '새 도구 영역'(c43382b)은 31fa1b9(토큰 절감 2판 도구 여섯)뿐이고, 게이트웨이 HEAD c43382b tool_areas.json apps 에 circuittrace 줄이 없다.

- **참고:** 11-23 에 받았으나 싣지 않은 몫이라 다시 청한다.



#### HG-24 · 게이트웨이 시간 한도를 박스 설정으로 줄 자리가 없음

`P2` · 새 요청



- **문제:** _limits_line 주석대로 게이트웨이는 .env 를 읽지 않고, 포털 services.py:83 은 infra/.env 의 HWAX_* 키만 읽는다. 10-31 에 카드 검색을 30분까지 기다리게 하려고 GATEWAY_CALL_TIMEOUT=2400 을 사용자 ~/.bashrc 와 crontab 환경 줄에 넣었다. 그 줄을 안 읽는 셸로 띄우면 말없이 600 으로 돈다.

- **바꿀 것:** start.sh 가 박스 전용 env 파일(git 밖, 예 gateway.local.env)을 읽어 환경에 넣게 한다. 포털 services.yaml 의 env: 로 넘기는 길이어도 된다. 기동 로그의 _limits_line 은 그대로 둔다.

- **위치:** HWAXMcpGateway start.sh · gateway.py:12147 (_limits_line) · 포털 infra/scripts/services.py:83 · infra/services.yaml

- **확인:** ~/.bashrc 줄 없이 손으로 띄워도 기동 로그 _limits_line 이 2400 을 보인다

- **참고:** 반영되면 박스는 ~/.bashrc · crontab 의 우회 줄을 걷는다(운영 쪽 몫).



#### MEMORY-1 · 게이트웨이 부팅 경합 — 첫 지문은 재집계를 하지 않음

`P2` · 새 요청



- **문제:** 11-18 에 게이트웨이가 옛 에이전트(8도구)로 카탈로그를 지은 3초 뒤 새 코드(13도구)가 떴는데, 첫 G3 패스는 지문 씨앗만 되어 다음 재집계 전까지 새 심의 도구가 보이지 않았다(11-19 교체 때 재집계로 풀림).

- **바꿀 것:** 부팅 집계 때 _FP 를 채우거나, prev 가 None 일 때 부팅 때 받은 목록과 견주어 다르면 재집계한다.

- **위치:** HWAXMcpGateway gateway.py G3 생존 확인 루프(prev = _FP.get(key) 자리, :1877 부근) · _FP(:556)

- **확인:** 에이전트를 게이트웨이보다 몇 초 늦게 새 판으로 띄워도, 60초 안에 새 도구 수가 /tools-map 에 나온다.

- **참고:** 11-24 의 /health 와 tools-map 수 차이(게이트웨이 로컬 32개)는 이 버그가 아니다.



#### PT-2 · 도구 앱 목록의 StepForge 줄에 build · instance

`P2` · 받았으나 안 끝남



- **문제:** 도구 앱 목록의 StepForge 줄에는 env prod · canonical true · 별칭은 있지만 build · instance 칸이 없다. 리스크 · 적층 등 다른 앱 줄에는 build 가 있다. build 3404c449 는 StepForge system_status 를 따로 불러야 보인다.

- **바꿀 것:** StepForge 줄에도 build 와 instance(운영 / 동결)를 싣는다. 운영 박스의 StepForge 는 허브가 띄운 인스턴스가 아니라서 허브 서버 목록에는 build 가 없다(11-23 답). 그러니 원격 앱의 build 를 실을 출처를 새로 둔다. 예: 그 앱의 system_status 가 내는 build(문제 칸의 3404c449). 출처는 dev 가 고른다.

- **위치:** HWAXMcpGateway list_tool_apps(629f32c) · HEAXHub /api/v1/mcp/servers build 칸(ec240e1)

- **확인:** 목록 한 번으로 build 와 운영본 여부가 보여야 한다.

- **선례:** PT-R3 · P-3(GW-05 fd1f52d)

- **받은 곳 · 상태:** 받음 — 게이트웨이 629f32c(list_tool_apps 가 build 를 받는 쪽) · HEAXHub ec240e1(/api/v1/mcp/servers build 칸)이 들어갔다. HWAXPortal docs/ste-stepforge-1117/checklist.md 에 '[x] PT-2 … 11-23 답: build 없음 · 그 박스엔 StepForge 인스턴스가 없다(운영 노드에서 돈다)', 같은 폴더 context-notes.md SS-12 에 'build 칸 아니오(허브가 띄우지 않은 앱이라 설계대로 — L21-28 넘김 4)' 가 있다. 아직 안 됨 — 11-23 답 기준 StepForge 줄의 build · instance 가 비어 있고, 원격 앱의 build 를 실을 새 출처가 없다. 같은 점검표의 '[ ] PT-2 까닭 가리기 — 허브 서버 목록의 StepForge 항목에 build 가 있는지(401)' 도 열려 있다.

- **참고:** 개발 답: 운영 박스의 StepForge 는 허브가 띄운 인스턴스가 아니다(원격 운영 노드에 잇기만 한다). 그래서 build 가 비는 것은 설계대로다. 원격 앱의 build 를 실을 새 출처가 필요하며, dev 남은 일(L21-28 넘김 4)에 있다.



#### CT-02 · 영역 표에 빠진 앱 셋 알림(mountsoldatahub · ncdevdatahub · testscope)

`P3` · 받았으나 안 끝남



- **문제:** mountsoldatahub 108 · ncdevdatahub 108 · testscope 99, 모두 315개 도구가 미분류다.

- **바꿀 것:** 알림이다. 값은 각 앱 주인이 정한다. dev 는 이 셋의 값을 누가 정할지(그 앱 세션에 넘길지, 운영 쪽이 묶어 받아 넘길지)를 답한다. 요청 사본(CircuitTrace docs/requests/REQUEST-20261121-도구영역분류.md)에 적힌 짐작 값은 그대로 넣지 않는다.

- **위치:** HWAXMcpGateway tool_areas.json apps

- **확인:** 주인이 정한 값이 들어가 미분류 수가 준다.

- **선례:** 44f4b8d(DocForge 영역)

- **받은 곳 · 상태:** 받음 — CT-01 과 같다(HWAXPortal docs/cae00-inbox/2026-11-23.md:194 '새 앱 넷의 인자 설명 · 도구 영역 … 이번에 싣지 않았다'). 아직 안 됨 — 게이트웨이 HEAD c43382b tool_areas.json apps 에 mountsoldatahub · ncdevdatahub · testscope 줄이 없다.



#### CT-03 · 도구 등록 점검표에 '영역' 줄

`P3` · 받았으나 안 끝남



- **문제:** 점검표에 영역 칸이 없다. 그래서 앱이 붙을 때마다 미분류가 쌓였다(네 앱 모두).

- **바꿀 것:** 점검표에 '영역(tool_areas.json apps 줄)' 한 줄을 더한다.

- **위치:** HWAXMcpGateway docs/tool-registration-checklist.md

- **확인:** 점검표에 그 줄이 있고, tool_registration_scan.py 가 미분류 앱을 알린다.

- **선례:** 44f4b8d(request-1029 E-6)

- **받은 곳 · 상태:** 받음 — CT-01 과 같다(HWAXPortal docs/cae00-inbox/2026-11-23.md:194). 아직 안 됨 — 게이트웨이 HEAD c43382b docs/tool-registration-checklist.md 에 '영역' · tool_areas 가 한 줄도 없다.



#### OL-7 · ontology_lookup none 답에 StepForge identify_part 로 다시 가라는 한 줄

`P3` · 새 요청



- **문제:** CAD 파트 이름(「BRKT_<번호>」 꼴)은 정본에 없어 none 이 맞지만, 다음 걸음을 말하지 않는다.

- **바꿀 것:** type 이 part 이거나 질의가 CAD 이름 꼴(영문 대문자 · 밑줄 · 번호)이면 none 답에 'StepForge identify_part 로 core_part 를 얻고 그 key 로 다시' 한 줄.

- **위치:** HWAXMcpGateway gateway.py ontology_lookup none 답

- **확인:** CAD 이름 꼴 질의의 none 답에 그 한 줄

- **먼저:** ST-26



### 1-3. 에이전트 서버 (HWAXAgentServer) — 18건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| OF-1 | 위임이 보고서 첨부 본문을 못 읽음 | P1 | 새 요청 |

| OF-2 | 위임이 덜 찾고 멈추는데 결과에 '덜 찾음' 이 드러나지 않음 | P1 | 새 요청 |

| OF-3 | 숫자 대조가 단위 환산 · 반올림을 어긋남으로 셈 | P1 | 새 요청 |

| WD-01 | 심의 근거를 참조로 넘기기(잡 결정문 · 도구 · 대화 · 문서) | P1 | 새 요청 |

| WD-02 | 웹 챗에 심의 · 리스크 도구를 맥락 따라 늘 묶고, 지어낸 잡 id · 실행 주장 검사 | P1 | 새 요청 |

| WD-03 | MCP 로 연 심의를 잡 주인의 포털 대화에 자동 기록 | P1 | 새 요청 |

| OF-4 | draft_section 권고를 긴 절에만 쓰거나 빼기 | P2 | 새 요청 |

| OF-5 | delegate_status wait_s 기본값과 줄 안내 | P2 | 새 요청 |

| WD-06 | 심의 확인 카드에 종류 · 라운드 · 좌석 · save_report · 근거 수 보이기 | P2 | 새 요청 |

| WD-07 | RA 보고서 생성 · 고침 · 태그 · 발행을 챗 확인 목록에 | P2 | 새 요청 |

| WD-08 | 심의 잡 목록 · 결정문 보기와 deliberate_list 날짜 · 글 거르기 | P2 | 새 요청 |

| WD-09 | 끝난 결정문을 RA 로 저장하는 deliberate_save_report(job_id) | P2 | 새 요청 |

| WD-10 | 웹 챗 과제 대상 고정과 대상까지 맞대는 수치 대조 | P2 | 새 요청 |

| HA-14 | 자기검증 검토 입력 상한 · 고침을 패치로 | P3 | 받았으나 안 끝남 |

| HA-19 | 모의해석(SIM) 카드를 부품 표로 | P3 | 받았으나 안 끝남 |

| HA-35 | THINK_SEAT_TIMEOUT_S 를 비우면 1800 — 킷 주석은 DELIB_TIMEOUT_S 와 같다고 적음 | P3 | 새 요청 |

| WD-12 | 수치 대조에서 id 꼴 빼기 | P3 | 새 요청 |

| WD-13 | 확인 뒤 진행 카드(6,000자 자르기 대신) | P3 | 새 요청 |



#### OF-1 · 위임이 보고서 첨부 본문을 못 읽음

`P1` · 새 요청



- **문제:** 본문이 보고서 HTML 첨부에만 있는 2과제에서 위임이 '못 읽음' 으로 끝났고, 한 건은 '읽을 수 없다' 고 단정해 모순으로 판정됐다. 기준선은 download_file 뒤 10~21번 찾아 읽었다. 패 8 가운데 첨부 탓이 2다.

- **바꿀 것:** (1) 첨부 본문을 쪽(offset · limit)과 찾기(query → 일치 줄과 앞뒤)로 읽는 읽기 도구를 두고 읽기 목록에 넣는다. download_file 을 통째로 넣는 것은 권하지 않는다. (2) 그 전까지 _DG_START_DESC 에 '본문이 첨부에만 있으면 위임하지 말고 직접 읽는다' 를 넣는다. (3) 울타리 밖이라 못 부른 도구를 결과에 blocked_tools 로 싣고, 답에는 '울타리 밖이라 못 읽음' 으로 적게 한다.

- **위치:** HWAXAgentServer offload.py read_fence(울타리 = 부른 사람 시야 ∩ 게이트웨이 읽기 목록 routine_read) · mcp_server.py:1871 _DG_START_DESC — HEAD b0fd922 · HWAXMcpGateway read_tools.json(c43382b 에 download_file 없음)

- **확인:** 11-24 비교에서 본문이 보고서 HTML 첨부에만 있어 위임이 「못 읽음」 으로 끝난 두 과제를 다시 돌리면, 위임 근거 표(evidence)에 첨부 본문이 실린다.

- **참고:** 읽기 도구를 어디에 둘지(RA 쪽 · 게이트웨이 쪽)는 dev 가 정한다. 2판(서버 위임 · 초안 · 변환 · 결과 묻기, 게이트웨이 결과 손잡이)의 스위치 다섯은 11-24 20:08 에 껐다. OF-1 ~ OF-5 를 고친 뒤 같은 16과제 × 2회 × 2갈래(64회)로 다시 잰다 — 기준은 판정 패배율 10% 이하, 숫자 어긋남이 늘지 않음, 환산 오탐 0. A-1(에이전트 서버 — OF-1 ~ OF-5 반영 + 위임 실행기가 단계마다 앞선 결과를 줄여 싣기)과 같은 묶음이다. 다시 잴 과제 목록(16과제와 첨부 본문 두 과제)은 운영 쪽이 재측정 때 따로 넘긴다.



#### OF-2 · 위임이 덜 찾고 멈추는데 결과에 '덜 찾음' 이 드러나지 않음

`P1` · 새 요청



- **문제:** 한 과제의 두 회차에서 위임이 검색 한 번 뒤 기본 10분에서 멈췄고 Claude 가 빈 사례로 표를 채웠다(패 2). 다른 회차는 위임 요약에 기대어 부품 × 증상 집계를 놓쳤다(패 1).

- **바꿀 것:** 결과에 멈춘 까닭(끝남 · 시간 · 호출 수)과 쓴 호출 수 / 예산을 구조 칸으로 싣는다. 시간이나 호출 수로 멈췄으면 incomplete: true 와 못 채운 항목을 적는다. 설명에 일 크기별 권장 steps · minutes 를 적는다(여러 건으로 표를 채우는 일은 20분 이상). 첫 검색 적중이 적으면 질의를 바꿔 다시 찾게 한다.

- **위치:** HWAXAgentServer offload.py:65-66(기본 12회 · 10분, 상한 30회 · 30분 — HEAD b0fd922) · offload.py 결과 dict · 실행기 지침 · mcp_server.py _DG_START_DESC

- **확인:** 11-24 비교에서 위임이 검색 한 번 뒤 기본 10분에서 멈춘 과제(두 회차)를 다시 돌리면, 결과에 멈춘 까닭과 incomplete 가 바르게 서고 표의 빈칸(원인 · 대책)이 줄어든다.

- **참고:** OF-1 과 같은 A-1 묶음이다. 고친 뒤 OF-1 과 같은 64회로 다시 잰다. 해당 과제 이름은 운영 쪽이 재측정 목록과 함께 넘긴다.



#### OF-3 · 숫자 대조가 단위 환산 · 반올림을 어긋남으로 셈

`P1` · 새 요청



- **문제:** 서버 숫자 대조의 어긋남 표시 33건 가운데 하나씩 본 21건이 모두 오탐이었다(Pa → GPa · MPa 환산 20 — 예: 2,350,000,000 Pa → 2.35 GPa, 근거 수로 계산한 증가율 1, 나머지 12건은 보지 않음). 운영 쪽에서 쓴 검사기에서도 같은 꼴의 반올림 오탐이 나왔다(예: 5717.116 → 5,717.12). 이 오탐을 답에 옮겨 적어 답이 길어졌고, 11-24 비교(같은 16과제를 기준선과 토큰 절감 2판으로 2회씩)의 A/B 판정 1건에서 졌다.

- **바꿀 것:** SI 접두 ×10^(3k), 소수 d자리 반올림, 비 ↔ %, 쉼표 · 공백 제거를 같은 값으로 본다. 계산한 수는 derived 로 따로 적는다. 어긋남마다 종류(원문에 없음 · 환산 의심 · 반올림 의심)를 붙인다. 챗 · 결정문 판정에도 같이 적용할지 정한다.

- **위치:** HWAXAgentServer offload.py numbers · evidence.py:40 unsourced_numbers · sig_numbers

- **확인:** 같은 16과제를 다시 돌린 비교에서 환산 오탐이 0 이다. 짧은 시험으로 2,350,000,000 Pa ↔ 2.35 GPa, 5717.116 ↔ 5,717.12 가 일치로 나온다. 일부러 틀린 수를 넣은 시험에서는 진짜 어긋남이 여전히 잡힌다.

- **참고:** 챗 · 결정문과 함수를 함께 쓰므로 적용 범위는 사람이 정한다. WD-12 와 함께 고친다. OF-1 ~ OF-5 는 한 묶음이다(에이전트 서버 offload.py · mcp_server.py · evidence.py).



#### WD-01 · 심의 근거를 참조로 넘기기(잡 결정문 · 도구 · 대화 · 문서)

`P1` · 새 요청



- **문제:** MCP 로 심의를 열 때 앞 심의 결정문 53,882자 가운데 14,390자(27%)만 실렸다. 챗 모델이 근거를 도구 인자로 손수 다시 쓰다 보니 챗 출력 한도에서 잘린다(엔진 한도는 건당 약 13.5만 자).

- **바꿀 것:** evidence 에 참조 kind 넷을 더한다 — {"ref":"job:<job_id>","view":"decision"}(view 는 decision = 결정문 전문 · full · summary 가운데 하나) · {"tool":"<도구 이름>","args":{…}}(엔진이 사용자 자격으로 불러 결과를 채움) · {"conv":"<conversation_id>","turns":[3,4]}(대화의 그 턴 도구 결과 activity) · {"doc":"<업로드 id>"}(대화에 붙인 문서 본문). 엔진이 그 사람 신원으로 풀어 좌석에게 넘기기 전에 본문을 채우고, 채운 글자 수 · 출처를 원장에 남긴다. 상한은 지금 엔진 상한을 그대로 쓰고 넘으면 잘린 곳을 표시한다. 챗 쪽 도구 설명에 '근거 본문을 다시 쓰지 말고 참조를 넘겨라' 를 넣는다.

- **위치:** HWAXAgentServer mcp_server.py 근거 참조 처리(DL-01 자리) · deliberation.py 엔진 상한(11-10 판 에이전트 서버 5cd1938 기준 :206–235, 건당 약 13.5만 자)

- **확인:** 5만 자 결정문을 job 참조 한 줄로 넘겼을 때 좌석이 전문을 받는다(또는 상한 표지가 붙는다).

- **선례:** DL-01 7da623d(참조 근거 틀)

- **참고:** HWAXPortal docs/token-saving 설계안의 P2(근거 {tool,args} 를 서버가 채움 — 11-02 결정으로 cae00 측정 뒤로 미룸)를 잡 · 대화 · 문서 참조까지 넓히는 항목이다. 이어하기 재실음은 DL-01 로 이미 들어갔으니 남은 일은 참조 kind 를 더하는 것이다.



#### WD-02 · 웹 챗에 심의 · 리스크 도구를 맥락 따라 늘 묶고, 지어낸 잡 id · 실행 주장 검사

`P1` · 새 요청



- **문제:** 11-10 시험에서 도구 · id 를 짚어 준 9단계 가운데 2단계에서 챗이 도구를 부르지 않고 부른 것처럼 썼다. 한 번은 없는 job id 와 표결 변화표까지 지어냈다. 그 턴에 심의 · 리스크 도구가 묶이지 않으면 이렇게 되고, 자기검증이 잡지 못했다.

- **바꿀 것:** 대화에 심의 · 리스크 잡 맥락이 있거나 사용자 글이 도구 이름 · 잡 id 를 말하면 deliberate_* · risk_* 를 그 턴에 늘 묶는다. 답 뒤 검사를 둔다 — ① 답에 <종류>-YYYYMMDD-HHMMSS-<6자> 꼴 잡 id 가 있는데 이번 턴 activity 와 이력 근거에 없음 ② '열었다 · 이어 돌렸다 · 시작했다 · 재조회했다' 같은 행동 주장이 있는데 이번 턴 activity 에 그 도구 호출이 없음. 걸리면 도구를 묶어 한 번 다시 쓰게 하고, 그래도 같으면 답 위에 '도구 호출 없이 쓴 내용' 표지를 단다.

- **위치:** HWAXAgentServer app.py 늘 묶기(HEAD b0fd922 의 _ONTO_CORE :3260 곁) · 도구 스키마 예산(11-10 판 5cd1938 기준 app.py:3106 — 창의 45%) · 예산을 넘으면 관련도 낮은 도구를 그 턴에서 빼는 자리(같은 판 :3336–3340)

- **확인:** 심의 맥락이 있는 대화에서 이어하기 요청과 신뢰 판정 요청(11-10 에 도구 호출 없이 답하거나 '신뢰 판정을 엽니다' 로 턴을 끝낸 두 꼴)을 다시 넣으면 실제 호출이 나가거나 못 불렀다고 쓴다. 이력에 없는 job id 를 답에 쓰면 다시 쓰게 한다. 지어낸 job id 가 0 이고 묶임 기록에 deliberate_start 가 남는다.

- **선례:** HA-01 · HA-21(45cd6ff) · HA-02(35b8478)

- **참고:** 권하는 순서의 첫째다(WD-02 → WD-01 → WD-03 · WD-04 → WD-06 · WD-07 → 나머지).



#### WD-03 · MCP 로 연 심의를 잡 주인의 포털 대화에 자동 기록

`P1` · 새 요청



- **문제:** MCP 로 연 심의가 포털 대화 목록 · 대화 검색에 남지 않는다. 그래서 웹에서 이어 보거나 찾을 수 없다(save_conversation 은 74잡 동안 0회 쓰였고 읽기 전용 PAT 은 거절된다).

- **바꿀 것:** 엔진 잡이 끝나면(이어하기 포함) 잡 주인의 대화에 kind=deliberation · source=mcp 로 쓴다. 행은 화두 → 좌석 턴 → 결정문, meta 는 job_id · 뿌리 job_id · 근거 목록 · subject. 뿌리 job_id 로 멱등하게 하고 이어하기 잡은 같은 대화에 붙인다. 사이드바에서 source=mcp 를 접거나 거를 수 있게 한다.

- **위치:** HWAXAgentServer 엔진 잡 끝 처리 · HWAXPortal 대화 저장소. 11-10 판 게이트웨이(c47e883) gateway.py:2344–2596 에는 MCP 쪽 자동 저장이 없고, 저장할 때 meta 는 non_negotiable · rebut 만 남긴다.

- **확인:** MCP 로 심의 하나를 끝내면 포털 사이드바 · 대화 검색에 한 건이 생긴다. 같은 잡을 다시 끝내도 중복은 0 이고 이어하기 잡은 같은 대화에 붙는다.

- **선례:** save_conversation(수동 — 반영)

- **참고:** 받는 쪽은 에이전트 서버(엔진) · 포털(대화 저장소)이다. 리스크 심사 앱 웹 패널이 이미 결과를 대화로 남기고 있으니 같은 길을 쓰면 된다.



#### OF-4 · draft_section 권고를 긴 절에만 쓰거나 빼기

`P2` · 새 요청



- **문제:** 쓰기 4과제의 Claude 비용 변화가 −0.5% 였다. Claude 가 draft_section 초안을 다시 읽고 고치기 때문이다.

- **바꿀 것:** 위임 설명의 초안 권고를 긴 절에만 쓰라고 줄이거나 뺀다.

- **위치:** HWAXAgentServer mcp_server.py _DR_DESC · 위임 설명

- **확인:** 재측정에서 쓰기 과제의 비용이 기준선보다 늘지 않는다.

- **참고:** OF-1 ~ OF-5 는 한 묶음이다(에이전트 서버 offload.py · mcp_server.py · evidence.py).



#### OF-5 · delegate_status wait_s 기본값과 줄 안내

`P2` · 새 요청



- **문제:** delegate_status 의 wait_s 기본값이 0 이라 첫 호출부터 기다리지 않는다. 32회 동안 상태 호출이 46번이었다. 사람마다 1건 제한이라 한 사람이 여러 대화에서 동시에 맡기면 줄이 길어진다. 이번 비교에서 줄 선 시간은 10회 · 약 1,800초였다.

- **바꿀 것:** wait_s 기본값을 게이트웨이 호출 한도 600초 안의 값(예: 240초)으로 둔다. 설명에 '줄이 길면 직접 읽는다' 를 보탠다(상태에 줄 순번이 이미 실린다).

- **위치:** HWAXAgentServer mcp_server.py delegate_status · _DG_START_DESC

- **확인:** 같은 비교에서 상태 호출 수가 위임 수에 가깝고, 줄이 길면 Claude 가 직접 읽는다.

- **선례:** TS-5 deliberate_status wait_s(5426e0a — 같은 파일 :1289 의 기다림 틀)

- **참고:** OF-1 ~ OF-5 는 한 묶음이다(에이전트 서버 offload.py · mcp_server.py · evidence.py).



#### WD-06 · 심의 확인 카드에 종류 · 라운드 · 좌석 · save_report · 근거 수 보이기

`P2` · 새 요청



- **문제:** 확인 카드가 심의 종류 · 라운드 · save_report 를 접어 둔다. 자연어 판에서 심의 종류를 잘못 골랐는데 카드에서 알아챌 수 없었다.

- **바꿀 것:** _confirm_card 맨 위에 종류 · 라운드 · 좌석(펼침) · save_report · 근거 건수 · 총 글자 · apps 를 고정해 보인다. 카드에서 save_report 를 켜고 종류를 바꿀 수 있게 한다.

- **위치:** HWAXAgentServer app.py:4820 _confirm_card · 포털 카드 화면

- **확인:** deliberate_start 확인 카드만 보고 심의 종류 · 라운드 · 저장 여부를 알 수 있고 바꿀 수 있다.

- **선례:** HA-29(확인 관문 — 반영)



#### WD-07 · RA 보고서 생성 · 고침 · 태그 · 발행을 챗 확인 목록에

`P2` · 새 요청



- **문제:** 웹 챗에서 RA 보고서 생성이 확인 없이 바로 됐다(11-10 시험). 11-11 이후로는 RA 운영자로 대화할 때만 막힌다.

- **바꿀 것:** RA 쓰기(create_report_draft · update_report_draft · add_report_tags · publish_report · create_report_from_format)를 운영자와 관계없는 공통 목록 _CONFIRM_JOB_TOOLS 에 넣거나, RA 도구가 묶일 수 있는 모든 운영자 정의의 writes · confirm 에 넣는다.

- **위치:** HWAXAgentServer app.py:4146 _CONFIRM_JOB_TOOLS · HWAXPortal infra/personas/he-team.json(운영자 정의 writes · confirm)

- **확인:** 운영자를 고르지 않은 웹 챗과 RA 가 아닌 운영자 대화에서도 RA 초안을 만들라고 하면 확인 카드가 먼저 뜬다.

- **선례:** HA-29 · 5d22517e(RA 운영자 정의 — 반영)

- **참고:** 포털 168ab627(11-23)은 리스크 운영자의 RA 초안 도구 선택 칸이라 확인 카드와는 다르다. RA 운영자 정의에는 5d22517e 로 이미 들어갔고, 남은 것은 공통 목록이다.



#### WD-08 · 심의 잡 목록 · 결정문 보기와 deliberate_list 날짜 · 글 거르기

`P2` · 새 요청



- **문제:** deliberate_list 는 최근 창만 보여 주고 날짜 · 글 거르기가 없다. 보름 전 심의는 창 밖이라 못 찾았다. 결정문 전문을 모델을 거치지 않고 볼 화면도 없다.

- **바꿀 것:** deliberate_list 에 since · until · query 인자를 더한다. 포털에는 내 엔진 잡 목록(날짜 · 종류 · 글 거르기, 100건 너머 넘김)과 결정문 전문 보기, '이 대화에 싣기' · '이어하기' 단추를 둔다.

- **위치:** HWAXAgentServer mcp_server.py:1385 deliberate_list · HWAXPortal 화면

- **확인:** 보름 전 심의를 날짜로 찾아 전문을 보고 대화에 실을 수 있다.

- **선례:** HWAXPortal docs/token-saving 설계안 P4b(결과 조회 일부) · deliberate_list subject 거르기(이미 있음)

- **참고:** 화면 몫은 HWAXPortal 이다.



#### WD-09 · 끝난 결정문을 RA 로 저장하는 deliberate_save_report(job_id)

`P2` · 새 요청



- **문제:** 끝난 심의를 나중에 RA 보고서로 남기려면 챗이 결정문 블록을 다시 써야 한다(시작 때 save_report 만 있다).

- **바꿀 것:** job_id 를 받아 엔진 렌더러로 결정문 전문을 RA 에 저장하는 도구를 둔다. 확인 카드를 거친다.

- **위치:** HWAXAgentServer mcp_server.py

- **확인:** 끝난 잡 하나를 저장하면 RA 보고서 id 가 돌아오고, 다시 불러도 중복이 없다.

- **선례:** 심의 시작 때 save_report(반영)

- **먼저:** 없음 — 겹침만 맞춘다. 리스크 앱 RK-01(RA 쓰기 길 — 지식 그래프는 서비스 계정 이름으로 RA 에 쓴다, 사용자 결정 10-31 D-1 (가))은 이미 들어갔다(리스크 앱 7b1042d). 이 도구의 RA 저장은 그 길과 어긋나지 않게 한다.



#### WD-10 · 웹 챗 과제 대상 고정과 대상까지 맞대는 수치 대조

`P2` · 새 요청



- **문제:** 자연어 질문에서 챗이 196초 동안 36번 호출하면서 엉뚱한 보드 판 · 넷을 골랐다. 힌트를 준 실행은 40초 동안 13번 호출로 맞혔다.

- **바꿀 것:** 대화에 '대상' 핀(리스크 과제 → 전작 · 보드 판 · 넷)을 두고 도구 기본값으로 쓴다. 수치 대조가 값과 그 값의 출처 대상을 함께 맞댄다.

- **위치:** HWAXPortal 대화 핀 · HWAXAgentServer app.py(웹 챗 턴) · evidence.py

- **확인:** 같은 자연어 질문이 핀이 있는 대화에서 맞는 보드 판 · 넷 쌍으로 간다. 다른 대상의 값을 쓰면 수치 대조가 짚는다.

- **선례:** HA-30 · 웹 심의 SubjectPicker · DL-04 7da623d

- **참고:** 받는 쪽은 포털(대화 핀) · 에이전트 서버(챗 · 수치 대조)다. 리스크 과제에는 전작 과제 · ECAD 보드 판이 이미 고정돼 있다(risk_next_step 의 facts). 웹 챗 대화에는 그 대상이 붙지 않는다.



#### HA-14 · 자기검증 검토 입력 상한 · 고침을 패치로

`P3` · 받았으나 안 끝남



- **문제:** 자기검증이 끝나야 본문이 나오고 '고침' 이면 답 전체를 다시 써 긴 답의 체감 지연이 커진다(추정). 검토자에 max_tokens 를 보내지 않는다.

- **바꿀 것:** 검토 입력에 별도 상한을 두고 '고침' 은 패치(고친 줄)로 받는다. 상한 값은 ms p95 로 정한다.

- **위치:** HWAXAgentServer app.py `_self_check_stream` · `_self_check_messages`

- **확인:** 긴 답 턴의 자기검증 ms p95 가 정한 상한 안 · '고침' 턴이 전체 재작성 없이 패치로 끝난다

- **선례:** HA-13(/health self_check 1b96a15)

- **먼저:** 운영 박스의 /health self_check ms p95 수치를 모아 넘기는 것(우리 몫)

- **받은 곳 · 상태:** 받은 request-1027/checklist.md:44 `[~] HA-14 자기검증 검토 입력 상한 · 패치 — 상한은 ms p95 를 모은 뒤 정한다(HA-13 의 /health self_check 가 모은다)` · 같은 폴더 context-notes.md:293 도 같은 순서다. 에이전트 서버 HEAD b0fd922 에 검토 입력 상한(SELF_CHECK_ 상한 값)과 검토자 max_tokens 가 없고, HA-14 를 단 커밋도 없다. 아직 안 된 것: 상한 값(운영 박스 /health self_check ms p95 를 우리가 모아 넘긴 뒤)과 '고침' 을 패치로 받기 둘 다.

- **참고:** dev 가 데이터 대기로 둔 행 — 우리가 p95 를 모아 넘기면 진행된다.



#### HA-19 · 모의해석(SIM) 카드를 부품 표로

`P3` · 받았으나 안 끝남



- **문제:** SIM 카드가 「원문(JSON)」 섹션 하나로만 보인다(1,506자/86줄 등).

- **바꿀 것:** content.components 가 dict 목록이면 부품 표(pid · title · elem_class · n_elems · area_ext · volume · material.name)로 싣고, contact_edges · attachments 는 짧은 섹션, 나머지는 마지막 원문(JSON)에 남긴다.

- **위치:** HWAXAgentServer app.py `_record_view` · `_cell` (10-27 기준 :4591-4636)

- **확인:** SIM 카드 하나를 열면 부품 표 섹션이 보이고 남은 JSON 이 따로 붙는다

- **받은 곳 · 상태:** 받은 request-1027/checklist.md:54 `[~] HA-19 SIM 카드 표 — '나중에'`. 에이전트 서버 HEAD b0fd922 app.py 에 components · contact_edges 처리가 없고, HA-19 를 단 커밋도 없다. 아직 안 된 것: 부품 표 섹션 전부.

- **참고:** 받은 request-1027/03-HWAXAgentServer.md:73 에 스스로 (나중에)로 적은 행이다. 같은 문서 :126 은 'SIM 카드 표는 포털이 이미 그린다' 고 적었다.



#### HA-35 · THINK_SEAT_TIMEOUT_S 를 비우면 1800 — 킷 주석은 DELIB_TIMEOUT_S 와 같다고 적음

`P3` · 새 요청



- **문제:** 띵킹 좌석 한도가 비면 1800 으로 돈다. 킷 주석은 심의 호출 한도(DELIB_TIMEOUT_S)와 같은 값이라고 적어, 박스가 DELIB_TIMEOUT_S 만 올리면 둘이 어긋난다. 운영 박스는 10-31 에 DELIB 36000 으로 올렸고 11-01 에 THINK 도 손으로 36000 으로 맞췄다.

- **바꿀 것:** THINK_SEAT_TIMEOUT_S 가 비어 있으면 DELIB_TIMEOUT_S 를 따르게 한다(또는 킷 주석을 '따로 적어야 한다' 로 고친다).

- **위치:** HWAXAgentServer thinking.py:76-77 · 포털 infra/env-kits/agent-server.env:116-120

- **확인:** THINK_SEAT_TIMEOUT_S 를 지우고 DELIB_TIMEOUT_S=36000 으로 띄우면 띵킹 한도가 36000 으로 잡힌다(또는 킷 주석이 동작과 맞다)

- **선례:** HP-39(env 킷 DELIB_TIMEOUT_S 주석 고침)

- **참고:** 포털 킷 주석 고침이면 HWAXPortal 몫이 함께 생긴다.



#### WD-12 · 수치 대조에서 id 꼴 빼기

`P3` · 새 요청



- **문제:** 잡 id · 16진 id · 결함 번호 조각이 '확인 안 된 수치' 로 나와 표시가 늘어난다.

- **바꿀 것:** id 꼴(잡 id · 긴 16진 · 접두 붙은 결함 번호)은 수치 대조에서 뺀다.

- **위치:** HWAXAgentServer evidence.py:40 unsourced_numbers · sig_numbers

- **확인:** id 만 다른 답에서 어긋남 표시가 0 이다.

- **선례:** HA-27 · HA-14(다른 문제)

- **참고:** OF-3 과 같은 함수라 함께 고치는 편이 낫다. DL-04 의 id 원천 대조와 겹치는지 dev 가 본다.



#### WD-13 · 확인 뒤 진행 카드(6,000자 자르기 대신)

`P3` · 새 요청



- **문제:** 확인한 잡의 결과를 6,000자에서 잘라 보여 주고 진행은 보여 주지 않는다.

- **바꿀 것:** 확인 뒤에는 진행 카드(상태 · 단계 · 링크)를 보여 주고 끝나면 결과 링크로 바꾼다.

- **위치:** HWAXAgentServer app.py:4982

- **확인:** 심의를 확인하면 진행 카드가 뜨고, 끝나면 결과 링크로 바뀐다.

- **선례:** HA-28(반영)



### 1-4. StepForge (HEAXHub) — 14건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SF-4 | part_stack 층 정보의 출처 | P1 | 받았으나 안 끝남 |

| SF-7 | enclosure_candidates 에서 앞뒤 유리가 빠짐 · 닫힘 추정 칸 | P1 | 받았으나 안 끝남 |

| ST-24 | part_ontology.yaml 코어 부품 14칸 채우기(역할 → 코어 부품) | P1 | 새 요청 |

| ST-26 | identify_part 등 도구 답에 core_part 와 이슈 next 싣기 | P1 | 새 요청 |

| ST-20 | 단면에서 상자로 걸렸지만 교선이 없는 파트를 이름 없이 missed 에 섞음 | P2 | 새 요청 |

| ST-21 | 자동 단면 평면이 0.002 mm 겹침 띠 한가운데에 놓임 | P2 | 새 요청 |

| ST-23 | 파싱 도중에 잰 파트 대응이 저장돼 계속 쓰임(fresh=true 없음) | P2 | 새 요청 |

| ST-25 | 파트 이름 → 코어 부품 이름 규칙 층(근거 층 human > role+name > role > name) | P2 | 새 요청 |

| ST-27 | pick_role 에서 머리 낱말(첫 유형 낱말) 먼저 | P2 | 새 요청 |

| BBOX-5 | (선택) BSplCLib::Hunt 경계 처리를 OCC 상류에 알릴지 판단 | P3 | 새 요청 |

| SRC-06 | 개정 후보 0 일 때 까닭 싣기 | P3 | 받았으나 안 끝남 |

| ST-19 | (질문) 덱에서 뺀 파트를 보기 도구가 건너뛸 선택 인자 | P3 | 받았으나 안 끝남 |

| ST-22 | 보고용 '정확한 상자'(world_bbox_exact)가 0.006 ~ 0.14 mm 부풂 | P3 | 새 요청 |

| ST-28 | 질문 — 관리자가 확인한 대응표를 한 번에 넣는 길 | P3 | 새 요청 |



#### SF-4 · part_stack 층 정보의 출처

`P1` · 받았으나 안 끝남



- **문제:** part_stack(과제 A 창 유리)이 layers null · editions [] · '저장한 층 장부가 없다' 를 준다. 장부는 사람이 save_part_stack 으로 써 넣는 것뿐이라, 과제 데이터에서 층을 얻을 길이 없다. 그래서 레디쉬 잡 608a24a0c924 가 템플릿 5층을 썼다.

- **바꿀 것:** 층마다 {name, thickness_um, material_id} 를 위에서 아래 순서로 준다. 장부가 비었으면 그 사실과 채우는 길을 함께 준다(쓰기는 사람 확인 뒤). material_id 는 확산 물성 조회 gas_transport_lookup(BG-4 — 층 → material_id 로 층별 D · S 를 주는 보강)에 그대로 들어가야 한다.

- **위치:** StepForge part_stack · save_part_stack

- **확인:** 사람 확인 뒤 한 번 써 넣는다. 그 뒤 part_stack 이 층과 material_id 를 돌려주고, 그 material_id 로 BG-4 조회가 되어야 한다(gas_transport_lookup 에 part_stack 층 id 를 넣으면 층별 D · S 표가 나오는 보강 — 같은 retest-1121-request.md:292).

- **선례:** SF-R3(11-17 레디쉬 연계 요청 — part_stack get/set: 파트 → 층 목록 [{name, thickness_um, material_id}] 위 → 아래, 적층 필름이 파트로 없을 때의 장부, 쓰기는 사람 확인 뒤. HWAXPortal docs/ste-stepforge-1117/reddish-request.md:243)

- **받은 곳 · 상태:** 받은 곳: HWAXPortal docs/ste-stepforge-1117/retest-1121-request.md:99 SF-4(커밋 1c3397a1, 11-21). SF-4 에 대해 받은 답은 같은 폴더 checklist.md:26(StepForge 2차 물음 줄, 아직 [ ])의 'SF-4 material_id 는 MaterialTwin 재료 id 라고 답함' 하나다. StepForge 쪽 반영은 같은 폴더 context-notes.md:83 SS-10(커밋 1abe8671 — StepForge D-708)과 cae00-inbox/2026-11-23.md:18 의 edcddf44(D-708 — 재시험 요청 SF-1 ~ SF-12)인데, D-708 1차 목록(SF-1 · 2 · 3 · 8 · 9 · 11 · 12)에 SF-4 는 없다. 아직 안 된 것: 과제 자료에서 층을 얻는 출처, 장부가 비었을 때 채우는 길 안내.

- **참고:** material_id = MaterialTwin 재료 id 라는 답은 받았다. 과제 자료에서 층을 뽑을 출처는 여전히 없다. 사람이 넣는 장부가 답일 수 있다.



#### SF-7 · enclosure_candidates 에서 앞뒤 유리가 빠짐 · 닫힘 추정 칸

`P1` · 받았으나 안 끝남



- **문제:** 과제 B 결과는 5줄이다. 프레임(cumulative_share 0.941 · +z 1.0 · −z 0.903), 아래 장식 1, 카메라 장식 3 이고, 전면 · 후면 유리가 없다. 상자로 어림해서, 고리 모양 프레임 상자가 ±z 를 다 덮는다. 닫힘 추정 칸이 없다(air_upper_mm3 48,610 은 위끝뿐). 그래서 앞뒤 유리는 사람이 find_parts 이름 · 부피로 골랐다.

- **바꿀 것:** 상자가 아니라 실제 면 가림으로 몫을 셈해 앞뒤 유리를 후보에 넣는다. 닫힘 추정(닫혔나 · 남은 틈) 칸을 둔다.

- **위치:** StepForge enclosure_candidates

- **확인:** 과제 B 에서 프레임 · 전면 유리 · 후면 유리가 함께 후보로 나와야 한다.

- **선례:** F-4(11-17 결로 연계 요청 — enclosure_candidates: project_id → 공기를 가두는 외피 후보 파트(프레임 · 앞뒤 유리 · 커버)와 닫힘 추정 · 내부 부피 어림. HWAXPortal docs/ste-stepforge-1117/condensation-request.md:102)

- **받은 곳 · 상태:** 받은 곳: HWAXPortal docs/ste-stepforge-1117/retest-1121-request.md:117 SF-7(커밋 1c3397a1, 11-21). StepForge 답은 같은 폴더 context-notes.md:83 SS-10(커밋 1abe8671 — StepForge D-708)이고, cae00-inbox/2026-11-23.md:18 은 edcddf44 를 'D-708 — 재시험 요청 SF-1 ~ SF-12' 라고만 적었다. D-708 1차 목록(SF-1 · 2 · 3 · 8 · 9 · 11 · 12)에 SF-7 은 없다. 아직 안 된 것: 실제 면 가림으로 앞뒤 유리를 후보에 넣는 것과 닫힘 추정 칸 — 운영에서 확인한 기록이 없다.

- **참고:** 반영 여부는 재시험 때 확인한다.



#### ST-24 · part_ontology.yaml 코어 부품 14칸 채우기(역할 → 코어 부품)

`P1` · 새 요청



- **문제:** 운영 StepForge 파트 인스턴스 75,426개 가운데 지금 앱 길(역할 → maps_to)로 코어 부품에 닿는 것 0%(maps_to 선 0/17). 17칸 모두 null, 사유 'BOX-12'. 역할 대응만 넣어도 65.2%.

- **바꿀 것:** 14칸(운영 사용자 11-24 확인): display_panel→PRT-DISPLAY · frame→PRT-FRONT_METAL · bracket→PRT-BRACKET · pcb→PRT-PCB · shield_can→PRT-SHIELD_CAN · tim→PRT-TIM · battery→PRT-BATTERY · fastener→PRT-SCREW · cushion_adhesive→PRT-ADHESIVE_GRP · connector→PRT-CONNECTOR · ic_package→PRT-PKG · passive_chip→PRT-PASSIVE · antenna→PRT-ANTENNA · camera→PRT-CAMERA. glass · speaker_mic · analysis_aid 는 null 로 두고 사유를 바꾼다 — glass: 코어에 유리가 셋(전면 윈도우 · 후면 글라스 · 카메라 윈도우)이라 역할 하나로 고르면 틀린다, 이름 규칙(ST-25)이 가른다 / speaker_mic: 코어에 스피커 · 마이크 · 리시버가 따로 있다 / analysis_aid: 해석 보조 형상이고 실물 부품이 아니다. 출처 칸은 '2026-11-24 운영 사용자 확인 — 운영 코어 거울의 part 「<라벨>」'. 사람 선 우선 규칙(onto_model.py:1622-1645) 유지.

- **위치:** StepForge core/data/part_ontology.yaml 칸 '코어 부품'(57 · 73 · 93 · 112 · 130 · 150 · 170 · 188 · 203 · 218 …, 운영 판 r20261123b = StepForge edcddf44 의 줄 번호)

- **확인:** 운영 사본에서 maps_to 선 수 > 0 · check_projection dangling_endpoint 0 · 파트 인스턴스의 코어 부품 비율 약 65%(ST-25 와 함께면 약 75%)

- **선례:** SRC-02(11-09 — 칸 · 관계 구조만 넣고 값은 BOX-12 로 미룸)

- **참고:** 14칸은 운영 사용자가 11-24 확인했다. 같은 날 사용자 결정으로 운영 박스 · 화면에는 넣지 않았다(이 요청으로 저장소 yaml 에 들어가는 것이 정본). frame 은 코어에 프레임이 따로 없어 전면 메탈 프레임(PRT-FRONT_METAL, 별칭에 '메탈 프레임' · 'Metal Frame')으로 정했다. 칩부품이 인스턴스의 45.8% 라 칩부품 뺀 비율(54.3%, 22,202/40,870)도 함께 볼 것.



#### ST-26 · identify_part 등 도구 답에 core_part 와 이슈 next 싣기

`P1` · 새 요청



- **문제:** identify_part 등 답에 role · role_label 만 있고 코어 부품이 없어 사람(또는 모델)이 이슈로 넘어가지 못한다.

- **바꿀 것:** 파트 줄에 core_part {key, label, basis}(basis = human · role+name · role · name)와 next(failuretrace_objects_list type_slug pd_defect, conditions ref.part.key eq key) 추가. 코어 부품이 없으면 core_part null + 까닭(둘 다 없음 · 이름 갈림 · 이름과 역할 어긋남이면 두 후보도).

- **위치:** StepForge app/mcp_server.py identify_part :16006 · identify_parts :16141 · describe_part :27605 · find_parts :2500 · part_index :21026(운영 판 r20261123b = StepForge edcddf44 의 줄 번호)

- **확인:** ST-24 뒤: 역할이 shield_can 인 파트에 identify_part → core_part.key = PRT-SHIELD_CAN · basis = role, next 를 그대로 부르면 결함 목록(11-24 기준 466건). 코어 부품이 없는 파트는 core_part null 과 까닭이 나온다. ST-25 뒤: 역할이 비고 실드캔 이름이 든 파트 → basis = name.

- **먼저:** ST-24. basis 가운데 name · role+name 은 ST-25 가 들어온 뒤에 채운다(그 전에는 human · role 만).

- **참고:** 빈 칸으로 두면 '이슈가 없다' 로 읽히므로 null + 까닭이 필수.



#### ST-20 · 단면에서 상자로 걸렸지만 교선이 없는 파트를 이름 없이 missed 에 섞음

`P2` · 새 요청



- **문제:** 과제 A · B 의 기본 자동 z 평면 단면에서, 상자로는 평면을 지나는 작은 평판 파트가 과제마다 2개씩 그림 · 표에 없었다. 교선이 없는 파트가 상자도 안 닿는 파트와 같은 missed 숫자에 이름 없이 더해진다(section.py:1252, 필드 주석 :960). 그래서 '재료가 없다' 와 'OCC 가 못 잘랐다' 를 가를 수 없다. 단면 지도에서 빠져 보인 파트 넷도 평면이 재료 밖 0.003 ~ 0.1 mm 를 지난 경우였다. 반대로 공차 0.029 mm 파트 하나는 상자 위 끝보다 0.009 mm 높은 평면에서 원호 4개로 그려졌다.

- **바꿀 것:** 상자로는 걸렸지만 교선이 없는 파트를 missed 와 따로 세고, 이름 · 경로 · 상자 끝까지의 거리를 싣는다. 평면이 상자 끝 공차 안을 지나면 '판정 불가' 표시를 단다. 교선이 그 파트의 정확한 상자 밖에서 나오면 별도 표시를 단다.

- **위치:** core/section.py:1189-1192 · :1243-1253 (필드 주석 :960)

- **확인:** 과제 A 의 기본 자동 z 평면 단면 응답에서, 빠졌던 평판 파트 2개가 이름 · 경로 · 거리와 함께 별도 칸으로 나와야 한다. 공차 안의 파트에는 '판정 불가' 표시가 붙어야 한다.

- **참고:** 운영에 남은 가장 오래된 릴리스(10-23)부터 해당 함수가 바이트까지 같다(새 회귀 아님). 11-13 검증마다 다른 사람이 반박 검토를 거쳤다.



#### ST-21 · 자동 단면 평면이 0.002 mm 겹침 띠 한가운데에 놓임

`P2` · 새 요청



- **문제:** 자동 평면이 상자 끝들이 약 0.002 mm 겹치는 띠 한가운데, 면에서 0.001 mm 떨어진 자리에 놓인다. 띠 폭 하한 DISTANCE_BOX_TOL = 1e-6 이 이 띠를 막지 못한다. 그 파트는 STEP 꼭짓점이 아래 면보다 0.002 mm 아래에 있고, 꼭짓점 공차 0.002 로 그 차이를 메운 형상이다. 그 높이에는 재료가 없다.

- **바꿀 것:** 자동 평면을 고를 때, 걸린 파트들의 면 · 공차에서 일정 거리(예: 0.01 mm 또는 공차의 몇 배) 이상 떨어진 자리를 고른다.

- **위치:** core/section.py:1066-1067 자동 평면 · geom.py:141 (DISTANCE_BOX_TOL)

- **확인:** 과제 A · B 의 기본 자동 평면이 걸린 파트 면에서 정한 거리 이상 떨어져야 한다. 빠지던 평판 파트 2개가 단면에 나와야 한다.

- **먼저:** ST-20 과 한 묶음



#### ST-23 · 파싱 도중에 잰 파트 대응이 저장돼 계속 쓰임(fresh=true 없음)

`P2` · 새 요청



- **문제:** 파싱 잡이 도는 중에 match_parts_across(큰 판)를 계산했다. 그때 파싱은 뷰 파일 단계였고, 그 뒤로 10분 넘게 더 돌았다. 이어 받기 저장소(D-630)는 kept: moved 로 답을 남기지 않았다. 반면 대응 저장소(D-610 .call.json)는 계산 전에 뜬 열쇠로 저장했고, 끝난 뒤 다시 확인하지 않는다. 이 답은 파싱이 끝난 뒤에도 67번 from_call 로 돌아갔다. limit · scan_budget · page · offset 을 바꿔도 같은 답이 나온다. 새로 재는 길은 계보 기록을 쓰는 run_job kind=match 뿐이다.

- **바꿀 것:** ① 어느 한쪽 과제에 파싱 잡이 돌거나 대기 중이면 대응을 저장하지 않거나, 저장한 답에 그 사실(파싱 잡 번호)을 적는다. ② 저장하기 전에 열쇠를 다시 떠서, 바뀌었으면 저장하지 않는다. ③ 읽기 도구에 저장된 답을 건너뛰는 인자(예: fresh=true)를 둔다.

- **위치:** app/mcp_server.py:6536-6615 · :6872-6907 (저장 :6541-6544 · :6610-6615, _match_key :6827-6831), kept.py:224-226

- **확인:** 파싱 중인 과제로 match_parts_across 를 부르면 저장되지 않거나 파싱 잡 번호가 표시되어야 한다. fresh=true 로 부르면 from_call 이 아니라 새로 계산한 답이 나와야 한다.

- **참고:** 이번에는 입력이 이미 새것이었고 저장된 열쇠가 지금 열쇠와 같아, 결과가 맞을 가능성이 높다. 다만 새로 잰 값과 맞춰 볼 길이 없었다.



#### ST-25 · 파트 이름 → 코어 부품 이름 규칙 층(근거 층 human > role+name > role > name)

`P2` · 새 요청



- **문제:** 코어 부품으로 가는 길이 역할(17가지) 하나뿐이라 이름에 코어 라벨 · 별칭이 들어도 역할이 비면 끊긴다. 이름만 24.2%, 이름 먼저 + 역할 대응 75.2%(서로 다른 이름 78.2%). 이름 · 역할이 함께 걸린 14.2% 가운데 어긋난 수는 11-24 에 세지 않음.

- **바꿀 것:** 근거 층 차례대로 선을 만든다 — ① human: 사람이 화면에서 정한 선(지금 그대로) ② role+name: 역할 대응표 칸(ST-24)과 이름이 같은 부품이거나, 이름이 역할 부품의 아래 부품(kind_parent · 집합의 한 갈래)일 때 — 좁은 쪽 ③ role: 이름이 코어 부품에 닿지 않을 때 역할 대응표 칸 ④ name: 역할이 비었을 때(대응 없는 glass · speaker_mic · analysis_aid 포함) 이름이 코어 부품 하나로만 풀리면. 역할 부품과 이름 부품이 다르고 위아래도 아니면 conflict — 선 없이 두 후보를 보임. 이름 규칙 5단계(잡음 낱말 빼기 → 코어 라벨 · key · 별칭 사전 → 전체 일치 → 첫 낱말부터 가장 긴 구 → 가장 긴 구, 같은 길이로 갈리면 선 없음). 관계는 새로 만들지 않고 maps_to src_type_slugs 에 cad_part 추가. 들어오기 전에 conflict 수를 함께 세어 달라.

- **위치:** StepForge core/data/ontology/stepforge-core.json:361 maps_to · :322 has_role · 새 규칙 층(part_id_rule.yaml:29-35 잡음 표 재사용)

- **확인:** 운영 사본 파트 코어 부품 비율 약 75%(conflict 만큼 낮음) · conflict 수 보고 · 「… SHIELD MIC …」 꼴은 conflict 로 선 없음 · dangling_endpoint 0

- **선례:** KooRemapper platform/backend/app/modules/reports/bridges.py:9 · platform/core/ontology/dynaforge-core.json:119(cae_part maps_to part, many_to_one) · 커밋 7b671977 · 4aace658

- **먼저:** ST-24. ST-25-KR 과는 같은 판에 함께 넣는다(maps_to 공통 블록은 DynaForge 와 바이트 동일, D-689 — 어느 쪽도 먼저가 아니다).

- **참고:** 측정된 개선이 +10%p(역할 대응만 65.2% → 이름 먼저 + 역할 대응 75.2%)라 P2 로 둔다.



#### ST-27 · pick_role 에서 머리 낱말(첫 유형 낱말) 먼저

`P2` · 새 요청



- **문제:** 꾸밈 낱말이 앞에 오는 이름(「TAPE … SCREW」 꼴)이 CATEGORIES 차례 때문에 뒤 낱말(체결)로 간다(D-490). 11-24 표본 50: 머리 낱말이 맞은 것 45 · 가장 긴 구 3 · 판정 불가 2.

- **바꿀 것:** 맞은 범주가 여럿이면 이름 앞쪽 낱말이 고른 범주를 먼저 둔다. D-490 을 뒤집는 일이라 결정이 필요하면 질문으로 받아 달라.

- **위치:** StepForge core/ontology.py:249 pick_role · core/partid.py:30-73 CATEGORIES

- **확인:** 11-24 표본 50 재판정에서 머리 낱말 쪽 판정과 45건 일치 · 테이프 · 쿠션류 「TAPE … SCREW」 꼴이 체결로 가지 않음

- **참고:** 테이프 · 쿠션류가 대부분. 11-24 표본 50개 이름 목록은 운영 쪽이 따로 넘긴다(이 문서에는 싣지 않음).



#### BBOX-5 · (선택) BSplCLib::Hunt 경계 처리를 OCC 상류에 알릴지 판단

`P3` · 새 요청



- **문제:** 조각 면 실패는 U 범위가 마지막 매듭을 약 1e-11 넘는 유리 B-spline 면에서 났고, 그 뿌리는 OCC 의 BSplCLib::Hunt 경계 처리일 수 있다. StepForge 에 물러설 길(ST-15 [11-13] · ST-16 [11-13])을 둬도 같은 꼴의 면은 다른 CAD 에서 또 나올 수 있다.

- **바꿀 것:** 이 경계 처리 문제를 OCC 상류에 알릴지 StepForge 쪽이 판단한다(선택 항목이다).

- **위치:** OCC BSplCLib::Hunt — StepForge core/occ_compat.py bbox_of 가 부르는 BRepBndLib.Add_s 경로

- **확인:** StepForge 쪽 판단(알린다 / 안 알린다와 까닭)을 받으면 닫는다.

- **먼저:** 없음 — ST-15 [11-13](bbox_of 가 OCC 예외에서 물러설 길)은 이미 들어갔다(StepForge 27b2132b 묶음).

- **참고:** 새로 고칠 코드는 없다. 11-15 안내대로 조각 면 판이 skipped_parts 로 빠진다면 상류 쪽 원인은 그대로 남아 있다. 보냈는지 기록이 없다. 이미 받았으면 빼 주세요.



#### SRC-06 · 개정 후보 0 일 때 까닭 싣기

`P3` · 받았으나 안 끝남



- **문제:** 개정 후보의 첫 출처(코어 개발모델 개정 칸, 5,903 중 5,855 빔)가 비어 후보가 말 없이 0 이다.

- **바꿀 것:** set_revision(dry_run=true) · onto_candidates 에 0 의 까닭(첫 출처 빔 · 과제명 끝 조각 없음 등).

- **위치:** StepForge set_revision · onto_candidates

- **확인:** 칸이 빈 과제에서 까닭이 나온다

- **받은 곳 · 상태:** 받은 곳: HWAXPortal docs/core-link/request.md:69 · checklist.md:16 [x](StepForge 세션에 넘김). 착지 기록은 없다 — cae00-inbox/2026-11-12.md:335-336 의 StepForge 착지 설명은 자동 실행 셋(규칙 단 과제 잇기 · set_revision 뒤 앞 판 match · 채우기 잡)만 말하고, core-link/checklist.md:21 착지 알림은 [ ] 다. 아직 안 된 것: set_revision(dry_run=true) · onto_candidates 가 후보 0 일 때 까닭을 싣는지 StepForge 쪽 착지 기록이 없다.

- **참고:** 들어갔다면 착지한 판(커밋)을 알려 달라. 운영 StepForge 는 11-13 부터 STEPFORGE_CORE_LINK=off 로 돈다. 이 항목이 들어와도 그 스위치를 켜기 전에는 운영에서 보이지 않는다.



#### ST-19 · (질문) 덱에서 뺀 파트를 보기 도구가 건너뛸 선택 인자

`P3` · 받았으나 안 끝남



- **문제:** remove_part 는 덱에서만 뺀다. _geometry_for → _load_geometry → _apply_db_overrides 는 뺀 경로를 돌려주기만 하고 트리 · 인덱스에는 그대로 둔다. section_view 는 tree.leaf_instances() 를 전부 돈다. 그래서 '그 파트를 빼서 임시로 피하기' 가 되지 않았다.

- **바꿀 것:** 보기 도구(단면 · 근접 · 그림)에 skip_excluded 같은 선택 인자를 둘지 정해 달라는 질문이다. D-225 의 뜻이라면 지금 동작이 맞다.

- **위치:** app/mcp_server.py:9905 _geometry_for · core/job_worker.py:127 _load_geometry · :1954 _apply_db_overrides · app/mcp_server.py:10799 section_view

- **확인:** StepForge 쪽 답(둔다 / 안 둔다와 까닭)을 받으면 닫는다.

- **먼저:** 없음 — ST-16 [11-13](파트 하나 실패로 호출 전체를 죽이지 않기 — skipped_parts)은 이미 들어갔다(StepForge 27b2132b).

- **받은 곳 · 상태:** 보낸 기록은 request-1111/checklist.md:31(일곱째 묶음)이다. 받은 편지함 · 계획 문서에서 이 질문의 답(둔다 / 안 둔다)은 찾지 못했다. 박스 HWAXPortal docs 에서 skip_excluded 를 git grep 한 결과도 0건이다.

- **참고:** ST-16 [11-13] 이 들어가 필요가 크게 줄었다. 새로 고칠 것은 없고, 답만 받으면 된다.



#### ST-22 · 보고용 '정확한 상자'(world_bbox_exact)가 0.006 ~ 0.14 mm 부풂

`P3` · 새 요청



- **문제:** list_parts · part_location 이 주는 상자(world_bbox_exact, job_worker.py:988 이 저장)는 평면 · 원통 파트도 공차와 원호 모서리만큼 부푼다(측정 최대 0.104 mm). 곡면 파트는 면의 매개변수 범위를 따라 0.14 mm 까지 부푼다. _add_s_is_exact 의 설명(오차 0)과 다르다. 단면이 파트를 거를 때는 느슨한 상자(geometry.py:156-172)를 써서, 같은 파트를 두고 도구마다 다른 상자를 본다.

- **바꿀 것:** 보고용 상자는 공차를 빼고 다시 재고, 곡면은 삼각화로 확인한다.

- **위치:** core/occ_compat.py:186-196 · :212-213, core/geometry.py:174-223, core/job_worker.py:988

- **확인:** 평면 · 원통 파트의 보고용 상자 부풂이 공차 크기 아래로 줄어야 한다. 곡면 파트의 상자는 삼각화 상자와 맞아야 한다. 이 값은 0.1 mm 아래의 간극 판단에 쓰인다.



#### ST-28 · 질문 — 관리자가 확인한 대응표를 한 번에 넣는 길

`P3` · 새 요청



- **문제:** 서비스 신원은 사람 선을 쓰지 못한다(맞는 설계, onto_local._service_gate). 그래서 운영이 대응 14줄을 넣을 길이 화면에서 14번 누르는 것뿐이다.

- **바꿀 것:** 질문 — 관리자 신원으로 대응표 파일을 한 번에 가져오는 길(사람 선으로 적히고 넣은 사람이 남는)을 둘 뜻이 있는지. 서비스 신원 거절은 바꾸지 않는다.

- **위치:** StepForge core/onto_local.py:12 · :1100-1109

- **확인:** 답

- **참고:** ST-24 가 들어가면 14칸은 저장소로 해결 — 뒤에 역할 · 이름이 늘 때를 위한 질문.



### 1-5. DocForge (HEAXHub) — 16건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| IR-11 | pptx 쪽 그림을 골라서 판독(그림 파일로 못 읽는 쪽만) | P1 | 새 요청 |

| IR-12 | 잘린 그림은 잘린 대로 싣고 판독하기 | P1 | 새 요청 |

| IR-13 | 그림으로 채운 도형의 그림을 그림 요소로 꺼내기 | P1 | 새 요청 |

| DFO-1 | docforge_capabilities 거울 수를 받는 타입만, 옛 행은 stale 로 | P2 | 새 요청 |

| DFO-2 | 변환 태그를 거울 별칭(과제코드 · 과제명 · 개발모델 이름)으로 맞추고 matched_by | P2 | 새 요청 |

| IR-14 | TIFF · EMF · WMF 를 PNG 로 바꿔 싣고 판독 | P2 | 새 요청 |

| IR-15 | 연결선의 시작 · 끝 도형으로 흐름 글 만들기 | P2 | 새 요청 |

| IR-16 | 쪽 그림 블록은 판독 재료로 쓰고 보고서에는 고를 수 있게 | P2 | 새 요청 |

| IR-17 | 판독 캡션에 한 줄 요약 쓰기 | P2 | 새 요청 |

| IR-18 | 판독 블록 라벨을 문서 전체 번호로 | P2 | 새 요청 |

| IR-19 | 표 그림의 둘째 판독은 표 위젯으로 · 같은 글 두 번 싣지 않기 | P2 | 새 요청 |

| IR-23 | 판독 · 판단 동시 수를 잡마다가 아니라 서비스 전체로 세기 | P2 | 새 요청 |

| DFO-3 | (선택) 태그를 {type_slug · key} 로 | P3 | 새 요청 |

| IR-20 | 차트 축 이름이 없으면 빈 칸으로(글자 null 금지) | P3 | 새 요청 |

| IR-21 | 판독 본문에서 머리 줄 · '없음' 줄 빼기 | P3 | 새 요청 |

| IR-22 | 그림 줄이기 기준에 픽셀도 넣기 | P3 | 새 요청 |



#### IR-11 · pptx 쪽 그림을 골라서 판독(그림 파일로 못 읽는 쪽만)

`P1` · 새 요청



- **문제:** 판독 대상이 웹 형식 그림 파일과 PC 묶음 쪽 그림뿐이라, 서버가 pptx 에서 그린 쪽 그림은 판독하지 않는다. 11-10 사람이 올린 실제 덱은 그림 파일 0개 · 글 없는 도형 174개라 정밀 변환에서도 판독 0건이었다.

- **바꿀 것:** '그림 파일로 못 읽는 것이 있는 쪽'(연결선 · 글 없는 도형 · 그림 채움 · 잘린 그림 · 웹 밖 형식 · SmartArt · 묶음)만 골라 쪽 그림을 판독한다. 지금 SLIDE 지시의 '글 내용은 다시 쓰지 마라 — 글은 따로 받았다' 를 빼고, 흐름 · 강조 · 그림 속 글을 묻는 지시로 바꾼 뒤 PROMPT_VERSION 을 올린다. 시험에서 쓴 지시: 「이 슬라이드 그림을 판독하라. ① 상자 · 화살표로 그린 흐름이나 구성이 있으면 상자 이름과 화살표 방향을 'A → B' 꼴로 모두 적어라 ② 색 · 동그라미 · 강조 표시가 있으면 무엇을 가리키는지 ③ 그림 · 사진 안의 글자와 수치를 그대로 ④ 글만 읽어서는 알 수 없고 그림으로만 전하는 내용. 보이지 않는 것은 지어내지 말고, 없으면 '없음'.」 결과는 그 쪽 끝에 '모델 판독 — 쪽 그림' 한 블록.

- **위치:** DocForge vision/stage.py:29-31 · vision/prompts.py(SLIDE) — 0.3.1 기준

- **확인:** 11-10 시험 덱(10쪽 가짜 값, 운영 서버 ~/tmp/imgtest-20261110/)의 5쪽(도형 흐름도 — 상자 3 · 연결선 2 + 한 단계 위 빨간 원) · 7쪽(잘라 넣은 그림 — 보이는 코드 하나 · 잘려 안 보이는 코드 하나) · 8쪽(그림으로 채운 둥근 사각형 안 코드) · 10쪽(TIFF 그림 안 코드)이 쪽 그림 판독 블록에 맞게 나온다 — 흐름 순서('입고검사 → 조립 → 낙하시험') · 빨간 원이 가리키는 단계 · 보이는 코드만 · 그림 채움 안 코드 · TIFF 안 코드.

- **먼저:** 포털 IR-02

- **참고:** 시험에서는 이 한 수로 다섯 가지가 모두 읽혔다(쪽당 0.9 ~ 1.5초). 판독이 챗 모델을 나눠 쓰므로 '고른 쪽만' 이 맞다.



#### IR-12 · 잘린 그림은 잘린 대로 싣고 판독하기

`P1` · 새 요청



- **문제:** 잘린 그림(a:srcRect)을 세기만 하고 원본 전체를 실어, 판독이 잘려 안 보이던 코드까지 본문에 적었다. 사람이 일부러 가린 것이 보고서 · DB 로 간다.

- **바꿀 것:** srcRect 대로 잘라서 싣고, 잘린 그림을 판독한다. 원본 전체는 싣지 않는다.

- **위치:** DocForge parse/pptx_native.py:441-442 · 그림 자원 — 0.3.1 기준

- **확인:** 잘라 넣은 그림(보이는 코드 하나 · 잘려 안 보이는 코드 하나)이 든 쪽(11-10 시험 덱 7쪽, 운영 서버 ~/tmp/imgtest-20261110/)의 그림 자원 · 판독에 보이는 코드만 있고 잘린 코드는 없다.

- **참고:** 가린 내용이 새는 문제라 높음으로 둔다.



#### IR-13 · 그림으로 채운 도형의 그림을 그림 요소로 꺼내기

`P1` · 새 요청



- **문제:** 그림으로 채운 도형(a:blipFill)은 글만 옮기고 그림은 버린다. 11-10 시험 덱 8쪽(그림으로 채운 둥근 사각형) 안의 코드는 그림을 웹 챗에 직접 붙이거나 쪽 그림을 모델에 넣은 길 밖에서는 어디서도 나오지 않았다(정밀 변환은 그림을 버림 · RA 가져오기는 쪽에 제목만 · AI 데이터 허브는 쪽이 비어 있음).

- **바꿀 것:** 그림 채움 도형의 그림을 그림 요소로 꺼낸다(상자 = 도형 상자). 글은 지금처럼 옮긴다.

- **위치:** DocForge parse/pptx_native.py:300-301 — 0.3.1 기준

- **확인:** 그림으로 채운 둥근 사각형(안에 코드)이 든 쪽(11-10 시험 덱 8쪽, 운영 서버 ~/tmp/imgtest-20261110/)의 그림이 그림 요소로 나오고 판독에 안의 코드가 있다.

- **참고:** AIDataHub IR-32 와 같은 일.



#### DFO-1 · docforge_capabilities 거울 수를 받는 타입만, 옛 행은 stale 로

`P2` · 새 요청



- **문제:** 받기는 과제 · 개발모델 둘(설계대로)인데 capabilities 가 거울 35 타입을 보고한다. 받지 않는 33 타입은 옛 행이라 코어보다 적다(고장모드 120/123 · 관리 기준 792/963 · 부품 224/235 등). 「DocForge 코어가 덜 받아졌다」 는 오해를 낳는다.

- **바꿀 것:** 거울 수는 받는 타입만 보이고 옛 행은 stale 로 따로 보인다. 옛 행을 쓰는 곳이 없으면 지운다.

- **위치:** HEAXHub integrations/doc-forge — docforge_capabilities(코드 줄 미확인)

- **확인:** docforge_capabilities → 받는 2 타입 수만 거울로, 나머지는 stale 묶음이거나 없음.



#### DFO-2 · 변환 태그를 거울 별칭(과제코드 · 과제명 · 개발모델 이름)으로 맞추고 matched_by

`P2` · 새 요청



- **문제:** 변환 때 코어 태그가 원문에 과제코드 · 모델 이름이 글자 그대로 있을 때만 첫 쪽에 달린다.

- **바꿀 것:** 받은 거울의 별칭으로 맞추고 태그에 matched_by 를 싣는다. 문서 단위여도 좋다.

- **위치:** HEAXHub DocForge 변환 태그

- **확인:** 과제명만 있는 문서 변환 → 태그에 그 과제 key 와 matched_by task_name.



#### IR-14 · TIFF · EMF · WMF 를 PNG 로 바꿔 싣고 판독

`P2` · 새 요청



- **문제:** TIFF · EMF · WMF 는 웹 형식 목록(_WEB) 밖이라 판독하지 않고 첨부로만 싣는다(변환 머리 'tiff 그림을 아직 PNG 로 바꾸지 않아').

- **바꿀 것:** PNG 로 바꿔 싣고 판독한다. 쪽 그림을 그리는 길과 같은 도구를 쓴다.

- **위치:** DocForge vision/stage.py:16(_WEB) · 그리기 단계 — 0.3.1 기준

- **확인:** TIFF 그림(안에 코드)이 든 쪽(11-10 시험 덱 10쪽, 운영 서버 ~/tmp/imgtest-20261110/)의 TIFF 가 PNG 로 실리고 판독에 안의 코드가 있다.



#### IR-15 · 연결선의 시작 · 끝 도형으로 흐름 글 만들기

`P2` · 새 요청



- **문제:** 연결선(cxnSp)을 세기만 하고 버려 흐름의 방향이 사라진다. 11-10 시험 덱 5쪽(상자 3 · 연결선 2 흐름도)은 변환 네 길(웹 챗 '이 대화에서 분석' · RA 정밀 변환 · RA 가져오기 · AI 데이터 허브 convert_file) 모두 상자 이름 나열뿐이었다.

- **바꿀 것:** 연결선의 a:stCxn · a:endCxn 을 읽어 '입고 → 조립' 꼴 글로 싣는다. 모델 없이도 흐름이 남고 IR-11 판독과 대조할 근거가 된다.

- **위치:** DocForge parse/pptx_native.py:283-284 — 0.3.1 기준

- **확인:** 도형으로 그린 흐름도(상자 3 · 연결선 2)가 든 쪽(11-10 시험 덱 5쪽, 운영 서버 ~/tmp/imgtest-20261110/) 본문에 '입고검사 → 조립 → 낙하시험' 꼴 줄이 판독 없이 생긴다.



#### IR-16 · 쪽 그림 블록은 판독 재료로 쓰고 보고서에는 고를 수 있게

`P2` · 새 요청



- **문제:** snapshot_page 를 켜면 쪽마다 끝에 전폭 그림이 판독 없이 붙는다.

- **바꿀 것:** 쪽 그림은 판독 재료로 쓰고, 보고서에는 고를 수 있게 한다(기본: IR-11 로 고른 쪽만).

- **위치:** DocForge structure/mapper.py:396-401 — 0.3.1 기준

- **확인:** snapshot_page 켬 · 기본값에서 IR-11 로 고른 쪽에만 쪽 그림 블록이 있다.

- **먼저:** IR-11 · IR-02



#### IR-17 · 판독 캡션에 한 줄 요약 쓰기

`P2` · 새 요청



- **문제:** 캡션이 판독의 머리 줄('[모델 판독] ① 그림 종류: 표')이라 정보가 없다.

- **바꿀 것:** 지시에서 '종류' 다음 줄에 '요약: 무엇이 어떤 값인지 한 줄' 을 받고 그 줄을 캡션으로 쓴다.

- **위치:** DocForge structure/mapper.py:291-294 · vision/prompts.py(FIGURE) — 0.3.1 기준

- **확인:** 막대 그래프 그림(PNG)이 든 쪽(11-10 시험 덱 2쪽, 운영 서버 ~/tmp/imgtest-20261110/) 캡션이 '막대 4개 — B 가 82 로 가장 높다' 꼴이다.



#### IR-18 · 판독 블록 라벨을 문서 전체 번호로

`P2` · 새 요청



- **문제:** 쪽마다 번호를 1부터 다시 세서 모든 쪽의 판독 블록이 '모델 판독 — 그림 1' 이고, 대화용 문서의 '[그림 2]' · '[그림 3]' 과 어긋난다.

- **바꿀 것:** 라벨을 문서 전체 번호('그림 3')로 하고, 그림이 여럿인 쪽은 쪽 안 위치(왼쪽 위 등)를 곁들인다.

- **위치:** DocForge structure/mapper.py:385-392 — 0.3.1 기준

- **확인:** 보고서 판독 블록 라벨과 대화 문서의 [그림 N] 번호가 같다.



#### IR-19 · 표 그림의 둘째 판독은 표 위젯으로 · 같은 글 두 번 싣지 않기

`P2` · 새 요청



- **문제:** 둘째 판독이 표 칸을 한 줄에 하나씩(13줄) 실어 행 · 열이 사라지고, 첫 판독 ⑤ 와 같은 글을 또 싣는다(시험 4쪽 25줄 + 13줄).

- **바꿀 것:** 표 그림의 둘째 판독은 표 위젯(행 · 열)으로 싣는다(차트 그림이 차트 위젯으로 가듯). 첫 판독 ⑤ 와 둘째 판독 가운데 하나를 뺀다.

- **위치:** DocForge structure/mapper.py:187-210 — 0.3.1 기준

- **확인:** 표를 캡처한 그림(FAIL 행의 코드 · 값)이 든 쪽(11-10 시험 덱 4쪽, 운영 서버 ~/tmp/imgtest-20261110/)이 표 위젯 하나로 나오고 같은 글이 두 번 실리지 않는다.



#### IR-23 · 판독 · 판단 동시 수를 잡마다가 아니라 서비스 전체로 세기

`P2` · 새 요청



- **문제:** 판독 · 판단 세마포어가 잡마다 따로라, DOCFORGE_MAX_JOBS 를 2 로 올리면 챗 모델에 가는 판독이 2배가 된다(client.py:17 주석이 그렇게 적었다).

- **바꿀 것:** 동시 수를 서비스 전체 상한으로 센다(잡 워커가 따로 떠도 같은 상한을 나누게).

- **위치:** DocForge vision/client.py:17 · :47 · structure/decide.py:97 · jobs/runner.py:102 — 0.3.1 기준

- **확인:** 잡 2개를 동시에 돌려도 챗 모델로 가는 동시 판독 호출이 DOCFORGE_VLM_MAX_CONCURRENCY 를 넘지 않는다.

- **참고:** 운영 박스는 11-10 에 DocForge knobs.env 로 DOCFORGE_VLM_MAX_CONCURRENCY=4 를 넣었다(잡 수가 1 이라 지금은 4 가 곧 전체). 잡 수를 2 로 올리는 날 IR-23 이 없으면 박스 값을 2 로 되돌린다(2 × 2 = 4). IR-24 와 함께 들어와야 한다.



#### DFO-3 · (선택) 태그를 {type_slug · key} 로

`P3` · 새 요청



- **문제:** 태그가 코어 key 인지 글자인지 응답에서 구별되지 않는다.

- **바꿀 것:** 태그를 {type_slug · key} 로 싣는다.

- **위치:** HEAXHub DocForge 변환 결과(docforge_convert)의 코어 태그 — DFO-2 와 같은 자리. 지금은 원문에 과제코드나 모델 이름이 글자 그대로 있을 때만 첫 쪽에 단다.

- **확인:** 변환 결과의 태그가 {type_slug · key} 꼴로 실려 코어 key 인지 글자인지 응답에서 구별된다. 예: (DFO-2 뒤) 과제명만 있는 문서를 변환하면 태그 칸에 그 과제의 type_slug · key 가 실린다.

- **먼저:** DFO-2



#### IR-20 · 차트 축 이름이 없으면 빈 칸으로(글자 null 금지)

`P3` · 새 요청



- **문제:** 스키마가 x_title · y_title 를 필수 string 으로 두어, 축 이름이 없는 그림에서 모델이 글자 'null' 을 넣는다. 보고서 차트에 x_axis_title: "null", 대화 문서에 '가로축 null · 세로축 null' 이 찍혔다.

- **바꿀 것:** 스키마에서 null 을 허용하거나, 'null' · 'None' 글자를 빈 값으로 바꾼다.

- **위치:** DocForge vision/client.py:100-113 · :124-126 — 0.3.1 기준

- **확인:** 축 이름 없는 차트 그림의 보고서 · 대화 문서에 'null' 글자가 없다.



#### IR-21 · 판독 본문에서 머리 줄 · '없음' 줄 빼기

`P3` · 새 요청



- **문제:** ①~⑤ 머리 줄과 '없음' · '해당 없음' 줄까지 21 ~ 25줄의 rich_text 로 실려, 보고서를 읽는 사람에게 절반이 빈 줄이다.

- **바꿀 것:** 머리 줄 · '없음' · '해당 없음' 줄을 빼고 내용 줄만 싣는다.

- **위치:** DocForge 판독 본문(_reading_block) — 0.3.1 기준

- **확인:** 정밀 변환 보고서의 판독 블록에 '없음' · '해당 없음' 줄이 없다.



#### IR-22 · 그림 줄이기 기준에 픽셀도 넣기

`P3` · 새 요청



- **문제:** 8 MiB 를 넘을 때만 줄여, 바이트는 작아도 픽셀이 큰 화면 캡처는 그대로 가서 모델 입력을 크게 쓴다.

- **바꿀 것:** 긴 변이 2048px 를 넘으면 줄인다.

- **위치:** DocForge vision/client.py:36 · :131-132 — 0.3.1 기준

- **확인:** 긴 변 2048px 를 넘는 캡처가 판독 전에 줄어든다(판독 호출 크기로 확인).



### 1-6. 리스크 앱 (HEAXHub) — 2건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| ER-06 | 2단계 — ODB 허브 묶음 읽기로 넘어가기 | P2 | 받았으나 안 끝남 |

| RK-11 | 리스크 앱이 게이트웨이에 내주는 사람 토큰 수명 900초가 호출 한도 2400초보다 짧음 | P2 | 새 요청 |



#### ER-06 · 2단계 — ODB 허브 묶음 읽기로 넘어가기

`P2` · 받았으나 안 끝남



- **문제:** 지금 길로는 보드 1 에 get_part_detail 약 760번, 보드 2 에 약 535번이 든다.

- **바꿀 것:** OH-01 · OH-02 가 들어오면 find_nets 페이지 · list_parts 큰 페이지로 바꾼다.

- **위치:** HWAXRisk backend/app/adapters/ecad.py · docs/odb-adapter-contract.md

- **확인:** 보드 1 캡처의 ODB 허브 호출 수가 수십 번 이하이고, component 좌표 · 넷 · net 노드 · component→net 엣지 · 분류 안 된 부품이 들어와 degraded 의 ecad_nets_deferred · component_xy_deferred · components_unclassified_omitted 표지가 사라진다.

- **먼저:** OH-01 · OH-02 — ODB 허브가 넷 · 핀 수와 부품 좌표를 묶어 내 주는 것(ODB 허브 팀에 따로 청함).

- **받은 곳 · 상태:** 요청은 포털 docs/design-risk-review/ecad-1031 로 받았다(커밋 0fa19a6d 10-30 — 요청서 정본 · ODB 허브에 보낼 글, D-1 = 가: 지금 도구에 묶음 읽기 OH-01 ~ OH-05). 11-24 운영 박스 리스크 앱 읽기: backend/app/adapters/ecad.py 는 아직 list_parts 를 100행씩 넘기고(허브가 page_size 를 100 으로 줄인다는 주석), 계약 문서 docs/odb-adapter-contract.md 는 ER-06 을 「지금은 하지 않는다」 로 적는다. 아직 안 된 것: 선행인 ODB 허브 OH-01 · OH-02 가 11-24 까지 들어오지 않아 2단계 전환 전체가 남았다.

- **참고:** ODB 허브 반영을 기다림. D-1 = 가(ODB 허브가 지금 도구에 묶음 읽기를 더하고 리스크 앱이 거기에 맞춘다). 먼저 들어와야 할 것 — OH-01: find_nets 에 offset · total · has_more, 자를 때 truncated: true 와 상한, 넷마다 pin_count. OH-02: list_parts 에 분류 안 된 부품 포함 선택지 · x · y · rotation · mirror · 넷 이름 칸, page_size 2000 까지. 그 전에 꼭 필요하면 핀 수 상위 부품만 get_part_detail 로 읽고(호출 상한) component_xy_partial 을 남긴다. 이미 받은 요청이라 OH 반영 뒤 후속으로만 알린다.



#### RK-11 · 리스크 앱이 게이트웨이에 내주는 사람 토큰 수명 900초가 호출 한도 2400초보다 짧음

`P2` · 새 요청



- **문제:** 게이트웨이 알림 줄 'user PAT on hwax_risk: 수명 900초가 호출 한도 2400초(GATEWAY_CALL_TIMEOUT)보다 길지 않다' 가 11-01 에 6번 났다. 긴 도구 호출 중에 토큰이 끝날 수 있다.

- **바꿀 것:** 게이트웨이를 거치는 호출용 토큰 수명을 호출 한도 + 여유(2700초 이상)로 내주거나, 긴 호출 전에 남은 수명을 보고 새로 받는다. 수명이 모자라 실패하면 그 호출만 새 토큰으로 다시 건다.

- **위치:** HWAXRisk backend/app/config.py:398 (sso_ttl_s · HWAXRISK_SSO_TTL_S)

- **확인:** 게이트웨이 로그에 'user PAT on hwax_risk … 길지 않다' 줄이 더 나오지 않는다

- **참고:** HWAXRISK_SSO_TTL_S 가 env 로 읽히므로 박스가 knobs 로 2700 이상을 먼저 줄 수 있는지 확인할 만하다(앱 상한 유무는 미확인). 되면 기본값 · 안내만 남는다.



### 1-7. HEAXHub 공통 · MaterialTwin — 4건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| HH-18 | HEAXHub 가 스스로 띄우는 앱이 HEAXHub 기동 때의 옛 .env 값을 씀 | P2 | 새 요청 |

| IR-24 | HEAXHub 매니페스트 launch env 에서 DOCFORGE_MAX_JOBS 빼기 | P2 | 새 요청 |

| SE-8 | HEAXHub 앱 데이터 병합 · 모델 확인 · 배포본 검사에서 반복 줄이기 | P2 | 새 요청 |

| HH-10 | 재료 데이터 중복 · 병합 어긋남 | P3 | 받았으나 안 끝남 |



#### HH-18 · HEAXHub 가 스스로 띄우는 앱이 HEAXHub 기동 때의 옛 .env 값을 씀

`P2` · 새 요청



- **문제:** 자동 재기동(reconcile · 스캐너 전환 · 죽은 앱 되살리기)은 HEAXHub 기동 때 읽은 env 를 넘기고, 손 재기동(redeploy-app.sh)만 .env 를 새로 읽는다. 11-12 DocForge 코어 주소 · NO_PROXY 를 바꾼 뒤 자동 길로 뜨면 이미 연결을 거부하는 옛 주소로 돌아가며, health 200 이라 코어 받기가 실패하기 전에는 안 보인다.

- **바꿀 것:** 런처가 앱을 띄울 때마다 $ROOT/.env 를 새로 읽어 APPTAINERENV_* 와 프록시 변수(NO_PROXY 등)를 싣는다(redeploy-app.sh 와 같은 값). 어렵다면 상태 화면에 '.env 와 프로세스 env 가 다른 키'(이름만)를 보인다.

- **위치:** HEAXHub backend/app/services/integration_launcher.py:475 (요청 때 :472) · backend/app/services/apt_runner.py:214 · :313 · deploy/apptainer/redeploy-app.sh:15-22

- **확인:** .env 의 APPTAINERENV_<X> 하나를 바꾸고 HEAXHub 는 그대로 둔 채 자동 길(인스턴스 멈춘 뒤 되살리기)로 뜬 앱에 새 값이 들어가 있다.

- **참고:** 운영 박스 HEAXHub 본체가 11-24 15:43 에 다시 떠서 지금 프로세스 env 는 11-12 뒤 .env 값이다(당장 피해 없음). 다음 .env 변경 때 같은 틈이 다시 난다.



#### IR-24 · HEAXHub 매니페스트 launch env 에서 DOCFORGE_MAX_JOBS 빼기

`P2` · 새 요청



- **문제:** DocForge 는 환경변수가 박스 knobs.env 를 이기므로(config.py:68-72), 매니페스트에 박힌 잡 수 1 을 운영 쪽이 바꿀 수 없다. 지금도 '이 대화에서 분석' 잡(판독 끔이면 몇 초)이 정밀 변환 잡 뒤에 줄을 서고, IR-01 이 들어오면 더 길어진다.

- **바꿀 것:** launch env 의 DOCFORGE_MAX_JOBS: "1" 을 뺀다. 기본값 1 은 코드에 이미 있다(config.py:154). 운영은 knobs.env 로 정한다(HWAXRisk 매니페스트와 같은 관례).

- **위치:** HEAXHub integrations/doc-forge/.portal/manifest.yaml:31

- **확인:** 등록 사본 매니페스트에 그 줄이 없고, 박스 knobs.env 의 DOCFORGE_MAX_JOBS=2 가 DocForge 능력 조회의 max_jobs 에 보인다.

- **선례:** HWAXRisk 매니페스트의 knobs.env 관례

- **먼저:** IR-23

- **참고:** 들어오면 운영 박스 DocForge knobs.env 에 DOCFORGE_MAX_JOBS=2 를 넣는다. IR-23 이 아직이면 판독 동시 수(DOCFORGE_VLM_MAX_CONCURRENCY)를 4 에서 2 로 되돌린다.



#### SE-8 · HEAXHub 앱 데이터 병합 · 모델 확인 · 배포본 검사에서 반복 줄이기

`P2` · 새 요청



- **문제:** app-data.tar.gz(50,230,882 바이트, 드라이브 수정 2026-10-16)를 매번 새로 받아 병합하고(11-03 · 11-05 모두 0건 추가), DB 마다 남긴 .pre-merge 사본이 316개 · 8,157,257,728 바이트 쌓였다. 모델 285개 객체(14.1 GiB)를 매번 다시 비교하고(약 3 ~ 4분, 추정) 13 GB 캐시 전체에 sha256sum -c 를 돈다. 11-24 에 다시 세면 .pre-merge 사본이 348개로 늘었다.

- **바꿀 것:** 1) 드라이브 tar 해시를 적어 같으면 다운로드 · 백업 사본 · 병합을 건너뛴다. 2) 백업 사본은 DB 마다 최근 N개만. 3) 모델은 앱별 MANIFEST 비교로 같으면 건너뛰고, 비교할 때는 --fast-list · --stats-one-line. 4) sha256sum -c 는 이번에 옮긴 파일에만, 전체 검사는 주 1회. 5) frontend-dist 는 바뀐 때만 풀고 --progress 대신 --stats-one-line.

- **위치:** HEAXHub deploy/apptainer/appdata-merge-from-drive.sh:19 · :36 · :53-64 · models-from-drive.sh · dist-from-drive.sh:63-68

- **확인:** tar 가 그대로인 실행에서 앱 데이터 병합을 건너뛰었다는 줄이 나오고 새 .pre-merge 사본이 생기지 않는다.

- **먼저:** tar 가 같아 건너뛸 때 운영에서 없어진 DB 밖 파일을 다시 채우는 동작(:53-64)도 멈추는데 괜찮은지 결정 필요

- **참고:** 실행 한 번에 약 5분 · 디스크 약 7 GB(추정). 병합 직전 백업 사본은 적어도 하나 남기고, 옮긴 파일의 무결성 검사는 계속한다.



#### HH-10 · 재료 데이터 중복 · 병합 어긋남

`P3` · 받았으나 안 끝남



- **문제:** 출처 1534 와 3184 가 갈리고 물성값 67907~67910(재료 254)이 겹친다. 같은 값 묶음 약 1,100개(다른 출처 691 · 같은 출처 446). 10-18 병합 correction_misses 11 · verdict_misses 1.

- **바꿀 것:** 두 출처를 합치고 중복을 정리한다. misses 가 같은 측정 두 행인지 확인한다.

- **위치:** MaterialTwin DB — 운영 박스 HEAXHub var/app_data/materialtwin_web/materialtwin.db 의 source 표(1534 · 3184) · property_value 표(67907 ~ 67910). id 는 박스마다 다르다.

- **확인:** 같은 값 묶음이 정리되고 다음 병합의 misses 가 0 이다.

- **먼저:** 포털 docs/cae00-inbox/2026-10-31.md Q1 — 운영 박스에서 출처 둘 · 물성값 넷의 자연 키 조회(결과 전달은 운영 쪽 몫)

- **받은 곳 · 상태:** 포털 docs/request-1030/outbound.md:46 「HH-10 그 id 들은 그쪽 DB 에 없다(id 는 박스마다 다르다) — 자연 키를 cae00 에서 받는다(받은 편지함 Q1)」. 그 조회는 docs/cae00-inbox/2026-10-31.md:25-27 Q1(출처 1534 · 3184, 물성값 67907 ~ 67910 의 자연 키). 아직 안 된 것: Q1 결과를 dev 쪽에 넘긴 기록은 포털 docs 에서 찾지 못했다 — 운영 쪽이 먼저 넘겨야 하고, 중복 정리는 그 뒤다.

- **참고:** 다음 손은 운영 쪽이다(자연 키 전달) — 포털 docs/cae00-inbox/2026-10-31.md Q1(출처 둘 · 물성값 넷의 자연 키 조회) 결과를 운영 쪽이 먼저 넘겨야 한다.



### 1-8. AIDataHub — 12건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| R-01 | AIDataHub 전문가 삭제 API 에 인증이 없음 | P0 | 새 요청 |

| AD-22 | bind_entities 가 사전에 든 타입의 연결만 지우기 | P1 | 새 요청 |

| ADO-1 | 코어 key 로 카드를 찾는 읽기 도구 cards_by_core | P1 | 새 요청 |

| IR-31 | AI 데이터 허브 convert_file 에 그림 판독 붙이기 | P1 | 새 요청 |

| AD-02 | '이 대화에서 분석' 변환이 임시 폴더를 지우지 않음 | P2 | 받았으나 안 끝남 |

| ADO-2 | 카드 응답에 묶인 코어 개체(core[]) 싣기 | P2 | 새 요청 |

| IR-32 | AI 데이터 허브 — 그림 채움 도형 · TIFF 처리 | P2 | 새 요청 |

| SE-3 | AIDataHub 병합 — record_sections 두 번째 임베딩 슬롯을 비우지 않기(4번) | P2 | 새 요청 |

| IR-33 | AI 데이터 허브 요약 · agent_hints 를 쪽 제목과 판독 요약으로 | P3 | 새 요청 |

| SE-4 | 전체 덤프 길에서 병합 전 전체 덤프를 쓸 행이 있을 때만 뜨기 · backup-local 주석 고치기 | P3 | 새 요청 |

| SE-6 | AIDataHub 병합 결과에 표별 추가 · 갱신 · 그대로 행 수와 시간 남기기 | P3 | 새 요청 |

| SYNCEFF-1 | 레코드 밖 표에 매일 값만 바뀌는 갱신이 있는지 확인 | P3 | 새 요청 |



#### R-01 · AIDataHub 전문가 삭제 API 에 인증이 없음

`P0` · 새 요청



- **문제:** DELETE /api/agents/{agent_type} 를 로그인 없이 부를 수 있어 누구나 전문가를 지울 수 있다.

- **바꿀 것:** 삭제 경로에 인증과 권한 검사(관리자 또는 주인)를 둔다. 가장 먼저 보낸다.

- **위치:** api_server/src/api/routes/agents.py:208 · router :36

- **확인:** 인증 없는 DELETE 가 401 · 403 을 받는다.

- **선례:** 포털 docs/request-1027/review-10-AIDataHub.md:42 N5 · docs/request-1030/platforms/10-AIDataHub.md:155 — 둘 다 'require_api_key 없음' 을 참고로만 적었다

- **참고:** 보안 빈틈 — 다음 묶음 맨 앞. 사용자 결정 D-01(개발이 고칠 때까지 포털 nginx 의 /ai-data-hub/ 갈래에서 DELETE 를 막을지)의 임시 막기와 함께 본다. AUTH_REQUIRED=false 박스에서는 require_api_key 를 붙여도 빈 동작일 수 있어, 삭제 경로만은 설정과 무관하게 권한을 보게 해 달라고 함께 적는다.



#### AD-22 · bind_entities 가 사전에 든 타입의 연결만 지우기

`P1` · 새 요청



- **문제:** 잇기가 그 허브의 연결을 타입과 상관없이 통째로 지우고 다시 쓴다. 포털 card-entity-bind.py --types part 처럼 도움말대로 일부 타입만 주면 11-23 에 만든 여덟 타입 연결 345,344줄이 지워진다. HPO-2(포털 --only-types 증분)는 지우기가 AIDataHub 안에 있어 포털만 고쳐서는 안 된다.

- **바꿀 것:** 사전에 든 타입의 줄만 지움 — where(RecordEntity.hub == hub, RecordEntity.type_slug.in_(사전의 타입)), OntoTerm 도 같게. 답에 타입별 전후 수.

- **위치:** AIDataHub api_server/src/api/services/onto_svc.py:402-403 bind_entities

- **확인:** 타입 하나로 잇기를 돌리면 그 타입 링크만 바뀌고 다른 타입 수는 그대로 · 답에 타입별 전후 수

- **선례:** 8c9506c(11-20 — '그 허브의 연결을 통째로 다시 씀' 이 지금 설계)

- **참고:** HPO-2 의 밑받침. 포털 쪽 멈춤 장치는 HPO-2 에 함께(AD-22 가 먼저 들어오면 불필요). 11-24 운영은 잇기를 돌리지 않음 — 돌려야 하면 아홉 타입을 함께 주는 박스 감싸개로 피함. 카드 ↔ 부품 잇기는 운영 쪽 사용자 결정(11-24)으로 지금 하지 않고 AD-22 · HPO-2 가 들어온 뒤에 한다(지금 링크 345,344줄은 그대로).



#### ADO-1 · 코어 key 로 카드를 찾는 읽기 도구 cards_by_core

`P1` · 새 요청



- **문제:** 11-23 결합으로 링크 345,344 · 카드 50,294/61,523 장이 코어에 묶였는데 AIDataHub 도구 32개 중 그 링크를 읽는 도구가 0이다. MCP · 웹 챗에서 「고장모드 ○○ 에 관한 전문가 카드」 를 key 로 물을 수 없다.

- **바꿀 것:** 읽기 도구 cards_by_core(type_slug, key, limit) 를 둔다 — 링크 표에서 그 개체에 묶인 카드를 근거 칸(section · 낱말)과 함께 돌려준다.

- **위치:** AIDataHub api_server(mcp_runtime.py) · 링크 표(alembic 0033_onto_links)

- **확인:** cards_by_core(failure_mode, <고장모드 key>) → 카드 목록 + 근거 칸.

- **선례:** 8c9506c · 85c3f2f(카드 ↔ 온톨로지 연결 표 넷, 11-20)

- **참고:** Q-1 — 링크 표 넷은 AIDataHub DB 에 있지만 채우는 것은 포털 스크립트다. 도구가 그 표를 읽는 것이 설계와 맞는지, 정식 표로 옮겨야 하는지.



#### IR-31 · AI 데이터 허브 convert_file 에 그림 판독 붙이기

`P1` · 새 요청



- **문제:** convert_file 결과의 그림 7개 캡션이 모두 'Figure 1: t1_bar.png' 꼴(넣은 파일 이름)이고 판독 단계가 없어, 그림 내용이 지식 DB 에 한 글자도 들어가지 않는다. 실제 덱은 그림 이름이 'image12.png' 꼴이라 더 정보가 없다.

- **바꿀 것:** 그림마다 판독을 붙인다. 캡션에는 파일 이름 대신 판독 요약, 본문 블록에는 판독 전문을 넣어 지식 DB 검색이 그림 내용을 찾게 한다. 가장 쉬운 길은 같은 모델 · 지시 · 캐시를 쓰는 DocForge 에 맡기고 그 문서를 record 로 바꾸는 것이다.

- **위치:** AIDataHub convert_file(pptx · docx · pdf)

- **확인:** 시험 덱(10쪽 가짜 값 덱 — 운영 서버 DocForge inbox 의 imgtest-20261110.pptx. 2쪽 막대 그래프 PNG · 3쪽 응력 지도 그림 · 4쪽 표를 캡처한 그림)을 convert_file 로 바꾸면 2 ~ 4쪽 그림의 캡션 · 본문에 판독 값(막대 값 · 최대 응력 · FAIL 행)이 들어가고, 지식 검색으로 그 값이 찾아진다.

- **먼저:** DocForge 에 맡긴다면 IR-11 ~ IR-13. TIFF 를 PNG 로 바꾸는 IR-14 는 기다리지 않는다 — 이 항목의 확인은 2 ~ 4쪽 그림만 보고, TIFF 는 IR-32 몫이다.

- **참고:** 포털 IR-04 가 이 결과를 쓴다. IR 묶음 안 순서로는 6번째다 — 앞의 다섯은 웹 챗(IR-01 · IR-03 · IR-08), 보고서 글 보기(IR-41), 도형 그림 · 잘림 · 그림 채움(IR-02 · IR-11 ~ IR-13), 잡 수(IR-23 · IR-24), RA 가져오기(IR-06 · IR-42).



#### AD-02 · '이 대화에서 분석' 변환이 임시 폴더를 지우지 않음

`P2` · 받았으나 안 끝남



- **문제:** 포털은 '어디에도 저장하지 않았습니다' 라고 말하는데 변환기가 추출 그림을 /tmp 에 기한 없이 남긴다. 박스 /tmp 에 ai_data_convert_* 2개(10-22 · 10-25, 0700)가 10-27 에도 남아 있었다.

- **바꿀 것:** run_convert 에서 TemporaryDirectory 를 output_dir 로 넘기고 payload 를 만든 뒤 지운다(또는 cleanup 플래그).

- **위치:** api_server/src/api/services/mcp_write_svc.py:452 run_convert · api_server/src/api/services/converter_dispatch.py:118-120

- **확인:** M-3: 포털 웹 챗 '이 대화에서 분석' 뒤 /tmp/ai_data_convert_* 수가 늘지 않는다. 시험으로 run_convert 뒤 임시 폴더가 없음을 고정한다.

- **선례:** 포털 docs/request-1027/review-10-AIDataHub.md:16(AD-02 유효)

- **받은 곳 · 상태:** 포털 docs/request-1027/10-AIDataHub.md:49 로 받았고, docs/request-1027/review-10-AIDataHub.md:16 이 「유효 — MCP run_convert 만 임시 폴더를 지우지 않는다. REST 길은 이미 지운다」 로 판정했다. docs/request-1030/platforms/10-AIDataHub.md 의 다시 보낸 목록에는 없고, AIDataHub 에 해당 커밋이 없다. 운영 박스 HEAD d59cf11 읽기: converter_dispatch.py:118-120 이 output_dir 이 None 이면 tempfile.mkdtemp(prefix='ai_data_convert_') 를 하고, mcp_write_svc.py:452 run_convert 에 output_dir · rmtree · TemporaryDirectory 가 없다. 10-27 뒤 두 파일 커밋은 AD-03 · AD-21 것뿐. 아직 안 된 것: run_convert 의 임시 폴더 지우기 전체.

- **참고:** 남은 /tmp 사본 정리는 운영 쪽 몫(OB-36 · OB-10 — 포털 docs/request-1027/10-AIDataHub.md:101). 포털 짝은 HP-29(~/aidh-inbox 사본 — docs/request-1027/01-HWAXPortal.md:145). AIDataHub 는 살아 있는 세션이 없어 포털 세션이 코드 행을 맡는 길(포털 docs/request-1030/context-notes.md:34 판단 C-7)로 보낸다.



#### ADO-2 · 카드 응답에 묶인 코어 개체(core[]) 싣기

`P2` · 새 요청



- **문제:** fts_search · 카드 조회 응답에 묶인 코어 개체가 없다.

- **바꿀 것:** 카드 응답에 core[{type_slug · key · name · 근거 칸}] 를 상위 몇 개만 싣는다.

- **위치:** AIDataHub api_server/src/api/mcp_runtime.py:957 fts_search · services/search_svc.py:163

- **확인:** 같은 카드를 fts_search 로 찾으면 응답에 core 칸.

- **먼저:** ADO-1



#### IR-32 · AI 데이터 허브 — 그림 채움 도형 · TIFF 처리

`P2` · 새 요청



- **문제:** 그림으로 채운 도형만 있는 쪽은 통째로 빈다(시험 8쪽 블록 0). TIFF 는 파일로만 붙는다.

- **바꿀 것:** DocForge IR-13 · IR-14 와 같은 일 — 그림 채움 도형의 그림을 그림 요소로 꺼내고, TIFF 를 PNG 로 바꿔 싣는다.

- **위치:** AIDataHub convert_file(pptx)

- **확인:** 시험 덱(IR-31 확인의 10쪽 덱) 8쪽(그림으로 채운 둥근 사각형 — 안의 코드)에 그림 블록이 생기고 10쪽 TIFF 그림이 PNG 그림 블록으로 실린다.

- **먼저:** IR-31(판독을 DocForge 에 맡기면 함께 풀린다)



#### SE-3 · AIDataHub 병합 — record_sections 두 번째 임베딩 슬롯을 비우지 않기(4번)

`P2` · 새 요청



- **문제:** record_sections(약 109만 행)의 두 번째 임베딩 슬롯 열은 덮는 열에 들어 있어, dev 쪽이 비고 운영 쪽이 차 있으면 값이 다르므로 dev 의 빈 값으로 덮일 수 있다(추정, DB 질의 없이 확인 못 함). 속도가 아니라 데이터가 맞는지의 문제다.

- **바꿀 것:** record_sections 의 두 번째 슬롯 열을 records 처럼 덮지 않는 열로 두고 비었을 때만 채운다. 또는 dev 판에서는 그 슬롯이 늘 채워져 있다고 확인해 준다.

- **위치:** AIDataHub deploy/apptainer/merge-from-drive.sh:365(record_sections 인자) · :157-162(비교 조건) · :171 부근(m3 채우기, records 전용) — HEAD d59cf11

- **확인:** dev 슬롯이 비고 운영 슬롯이 찬 줄을 시험 병합해 운영 값이 남는다. 바뀐 것이 없는 덤프로 병합하면 upsert 구간 WAL 합이 1 GiB 아래이고 병합 뒤 record_sections 전체 자동 vacuum 이 돌지 않는다(1 · 2번 효과 측정은 우리 몫).

- **선례:** AIDataHub ac6f788(IS DISTINCT FROM) · records 의 m3 빈 곳 채우기 규칙

- **참고:** 'dev 가 이긴다' 규칙은 AP-16 사용자 결정(11-05)으로 레코드 자식 표는 '레코드를 이긴 쪽' 으로 바뀌었다. 확인 질문 '두 번째 슬롯이 dev 판에서 비어 있는 행이 있는가' 와 같은 건이다.



#### IR-33 · AI 데이터 허브 요약 · agent_hints 를 쪽 제목과 판독 요약으로

`P3` · 새 요청



- **문제:** 요약(meta.summary)이 마지막 쪽 글을 이어 붙인 것이고, agent_hints 의 주요 토픽은 'N/A' 다.

- **바꿀 것:** 마지막 쪽 글을 이어 붙이지 말고 쪽 제목과 판독 요약으로 만든다.

- **위치:** AIDataHub convert_file 의 meta.summary · agent_hints

- **확인:** 시험 덱(IR-31 확인의 10쪽 덱) 변환 결과의 요약(meta.summary)이 쪽 제목 · 판독 요약으로 되어 있고 agent_hints 주요 토픽이 'N/A' 가 아니다.

- **먼저:** IR-31



#### SE-4 · 전체 덤프 길에서 병합 전 전체 덤프를 쓸 행이 있을 때만 뜨기 · backup-local 주석 고치기

`P3` · 새 요청



- **문제:** 전체 덤프 길은 병합 때마다 운영 DB 전체를 덤프한다(27분 09초 ~ 28분 13초, 약 11.15 ~ 11.18 GB). 11-03 에는 1시간 47분 앞선 update-all §1b(배포 전 백업) 덤프와 크기 차이가 327바이트였다. backup-local.sh 주석은 파일을 4.4G · :46 으로 적지만 실제는 약 11.2 GB 다.

- **바꿀 것:** 1) staging 적재 뒤 · 병합 전 덤프 앞에서 SE-3 의 비교 조건으로 표마다 쓸 행 수(추가 · 갱신 · merge_samples · 슬롯 채우기 포함)를 세어 모두 0이면 병합 전 덤프와 upsert 를 건너뛴다. 2) 쓸 행이 있으면 전체 덤프 또는 건드릴 행의 사전 이미지만 뜬다. 3) 사전 이미지를 쓰면 되돌리기 명령을 함께 만들고 마지막 줄 안내도 바꾼다. 4) update-all §1b(배포 전 백업) 덤프 재사용은 정책 선택지로만(재사용하면 §1b 뒤의 운영 쓰기와 update-all §2(서비스 배포)의 이행이 롤백 때 함께 되돌아간다). 5) backup-local.sh 의 주석(크기 · 줄 번호)을 고치고, 편입 뒤라 지울 것이 없는 pre-merge 정리 줄은 지우거나 왜 두는지 적는다.

- **위치:** AIDataHub deploy/apptainer/merge-from-drive.sh:97-100(전체 길 병합 전 덤프) · HWAXPortal infra/scripts/backup-local.sh:347(주석) · :364(pre-merge 정리 줄) · :92

- **확인:** 쓸 행이 0인 전체 길 실행에서 병합 전 덤프 파일이 새로 생기지 않는다. 사전 이미지 방식이면 시험 DB 에서 되돌리기 명령으로 병합 전 상태가 돌아온다. backup-local.sh 주석이 실제 크기 · 줄과 맞다.

- **선례:** 조각 길 AP-8(rollback-parts.sh · pre-parts 폴더)

- **먼저:** 없음 — 쓸 행을 세는 비교 조건(SE-3 1 · 2번, IS DISTINCT FROM)은 이미 들어 있다(AIDataHub ac6f788). 바꿀 것 4) 는 사용자 정책 선택이다.

- **참고:** 전체 길은 조각 목록이 없거나 낡았거나(HP-63 dev 예약이 안 걸리면 자주 탄다) 조각 병합이 실패할 때만 쓴다. 5번 주석은 HWAXPortal 몫이다.



#### SE-6 · AIDataHub 병합 결과에 표별 추가 · 갱신 · 그대로 행 수와 시간 남기기

`P3` · 새 요청



- **문제:** 병합은 전후 count(*) 차이만 '+N' 으로 찍어, 덮어쓴 행 수와 표별 시간이 기록에 남지 않는다. 그래서 SE-1 · SE-3 · SE-5 의 효과와 '같은 값만 다시 썼는지' 를 실행 기록으로 잴 수 없다.

- **바꿀 것:** 1) 표마다 추가 · 갱신 · 그대로인 행 수를 찍는다(SignalForge 의 'RETURNING (xmax = 0)' 방식). 2) 표마다 시작 · 끝 시각을 찍는다.

- **위치:** AIDataHub deploy/apptainer/merge-from-drive.sh merge_table(:110~) · NEWER_DIFF 집계(:261 · :378) — HEAD d59cf11

- **확인:** 다음 실행 기록에서 표마다 세 가지 수와 걸린 시간이 찍힌다.

- **선례:** SignalForge scripts/drive-sync/merge-from-drive.sh:285(RETURNING (xmax = 0))

- **참고:** 운영이 더 새로워 건너뛴 행을 세는 기존 집계(NEWER_DIFF)를 깨지 않는다.



#### SYNCEFF-1 · 레코드 밖 표에 매일 값만 바뀌는 갱신이 있는지 확인

`P3` · 새 요청



- **문제:** 레코드는 지난 7일 바뀐 것이 0건이라는 답을 받았지만, 절 · 첨부 · sync_runs 같은 레코드 밖 표에 매일 값만 바뀌는 갱신이 있으면 그 조각을 매일 받게 된다.

- **바꿀 것:** 레코드 밖 표 가운데 매일 값만 바뀌는 표가 있는지 알려 주고, 있으면 그 열을 조각 해시에서 빼거나 따로 다룬다.

- **위치:** AIDataHub 조각 스냅숏의 조각 내용 해시(포털 docs/aidh-parts-sync AP-1 · AP-7 — 조각마다 내용 해시를 적은 목록을 지난 병합 목록과 견줘 다른 조각만 받음) · 레코드 밖 표(절 · 첨부 · sync_runs 등)

- **확인:** dev 답, 또는 조각 길 실행 기록에서 바뀐 것이 없는 날 받은 조각 수가 0.

- **참고:** 질문 항목이다. 레코드 7일 변경 0건 답은 포털 docs/aidh-parts-sync PLAN §1. 참고로 20261103 · 20261104 덤프의 적재 기록(COPY 줄)을 견주면 21개 표 가운데 20개의 행 수가 같았고, 하나(덤프 순서 19번째, 추정 sync_runs)만 13,642행에서 13,740행이 되었다.



### 1-9. SignalForge — 5건



시험 입력은 코어에서 골랐고 실제 이름은 적지 않았다 — 과제 A · 그 과제코드 C1 · 프로젝트 P1(우선순위 P1 과 다른 자리표시) · 과제 A 의 모델코드 X1 · 그 마케팅명 M1. 실제 값은 운영 쪽에 받아 시험한다.



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SFO-1 | 프로젝트 key 를 코어로 풀고, 못 풀면 넓히지 말고 0건 + reason | P1 | 새 요청 |

| SFO-2 | 과제 → 제품 연결이 없을 때 낱말 검색으로 바꾼 것을 알리고 strict 인자 두기 | P1 | 새 요청 |

| SFO-3 | resolve_product_keyword · search_voc 응답에 core_key · matched_by · via 싣기 | P2 | 새 요청 |

| SFO-4 | 받는 타입에 plm_model_code 를 더해 자체 모델코드 사전 밖을 코어로 풀기 | P2 | 새 요청 |

| SFO-5 | (선택) search_voc 에 core_type · core_key 인자 | P3 | 새 요청 |



#### SFO-1 · 프로젝트 key 를 코어로 풀고, 못 풀면 넓히지 말고 0건 + reason

`P1` · 새 요청



- **문제:** search_voc 에 프로젝트 P1 + 증상을 주면 제품 범위 없이 전체 10,410건이 나오고 notes 는 빈칸이다. resolve_product_keyword(P1) 는 no_catalog_match 다. 사용자는 P1 의 VOC 로 믿어 틀린 답으로 이어진다(11-24 실측).

- **바꿀 것:** 받아 둔 코어 거울로 프로젝트 → 과제 → 개발모델 → 모델코드 → 자체 제품코드 순으로 푼다. 못 풀면 넓히지 말고 0건과 reason 을 준다.

- **위치:** SignalForge mcp-server/tools/query.py:369 resolve_product_keyword_tool(:401) · search_voc

- **확인:** resolve_product_keyword(P1) → 제품 하나 이상 + core_key(plm_project · P1) · matched_by: project. search_voc(P1 + 증상) → 결과가 그 제품 범위 안 · notes 에 푼 길 한 줄. C1 + 증상 → 117건 근처(되돌아가지 않음).

- **선례:** ODB 허브 find_job 꼴(이미 들어온 OD-1 ~ OD-3) — 과제명 · 과제코드 · 모델코드를 코어로 풀어 matched_by · via · core_key 를 주고(예: 과제 A → matched_by task_name · via task → project · core_key P1), 0건이면 reason(in_core_no_local_data 등)과 설명을 준다.

- **참고:** Q-1 — 프로젝트 → 제품 풀기에서 국내 · 해외 향이 섞이면 나눠 보이고 notes 에 제품 수를 적자는 것이 운영 권고. 들어온 뒤 운영 쪽이 박스 어휘표에 ontology_lookup 다음 호출 줄을 넣는다(지금 넣으면 프로젝트 key 가 전체 검색으로 바뀌어 미룸). SG-04 남은 몫(포털 docs/request-1029/signalforge-sg04-question.md — 두 제품이 한 제품 코드로 합쳐지는 문제, 제품 행을 따로 둘지 안 A/B/C 데이터 결정)과 같은 문제다. 코드 몫은 이 항목, 데이터 몫은 사용자 결정이다. 함께 보낸다.



#### SFO-2 · 과제 → 제품 연결이 없을 때 낱말 검색으로 바꾼 것을 알리고 strict 인자 두기

`P1` · 새 요청



- **문제:** 제품에 이어지지 않은 과제 + 증상이면 말없이 낱말 · 의미 검색으로 물러나 관계없는 결과가 섞이고, notes 의 같은 줄이 두 번 나온다(11-24 실측).

- **바꿀 것:** 물러날 때 notes 에 「과제 → 제품 연결 없음, 낱말 검색으로 바꿈」 한 줄을 한 번만 적는다. 넓히지 않는 선택 인자 strict 를 둔다.

- **위치:** SignalForge search_voc(mcp-server)

- **확인:** 제품에 이어지지 않은 과제 + 증상 → 0건과 reason, 또는 바꿨다는 한 줄(같은 줄 한 번).

- **참고:** SFO-1 · SG-04 남은 몫(포털 docs/request-1029/signalforge-sg04-question.md — 제품 행을 따로 둘지 데이터 결정)과 함께 본다.



#### SFO-3 · resolve_product_keyword · search_voc 응답에 core_key · matched_by · via 싣기

`P2` · 새 요청



- **문제:** 네 시험 입력(M1 · X1 · P1 · C1) 모두 응답에 코어 key 와 어떻게 풀었는지가 없다.

- **바꿀 것:** 두 도구 응답에 core_key(type_slug · key) · matched_by(task_code · task_name · project · model_code · marketing_name) · via 를 싣는다. ODB 허브 find_job 꼴을 따르면 게이트웨이가 같은 방법으로 읽는다.

- **위치:** SignalForge mcp-server/tools/query.py resolve_product_keyword_tool · search_voc

- **확인:** 응답에 core_key · matched_by · via 칸.

- **선례:** ODB 허브 find_job(이미 들어온 OD-1 ~ OD-3) — 과제명 · 과제코드 · 모델코드를 코어로 풀어 matched_by · via · core_key 를 주고(예: 과제 A → matched_by task_name · via task → project · core_key P1), 0건이면 reason(in_core_no_local_data 등)과 설명을 준다.

- **먼저:** SFO-1

- **참고:** 들어온 뒤 운영 쪽이 박스 어휘표에 ontology_lookup 다음 호출 줄을 넣는다(지금 넣으면 프로젝트 key 가 전체 검색으로 바뀌어 미룸).



#### SFO-4 · 받는 타입에 plm_model_code 를 더해 자체 모델코드 사전 밖을 코어로 풀기

`P2` · 새 요청



- **문제:** 자체 모델코드 사전이 452건으로 코어 plm_model_code 2,942건보다 훨씬 작다.

- **바꿀 것:** 받는 타입에 plm_model_code 를 더하고, 자체 사전에 없는 모델코드를 코어로 풀어 제품코드 후보로 쓴다.

- **위치:** SignalForge crawler/base/plm_mirror.py:41-42 TYPES · CORE_TYPES(env SF_SP_CORE_TYPES)

- **확인:** get_ontology 의 plm 칸에 plm_model_code 가 보이고, 자체 사전에 없는 모델코드로 resolve_product_keyword 가 제품 후보를 낸다.

- **선례:** plm_mirror 의 SF_SP_CORE_TYPES(사용자 결정 11-10)



#### SFO-5 · (선택) search_voc 에 core_type · core_key 인자

`P3` · 새 요청



- **문제:** 코어 key 로 VOC 를 바로 찾는 입력이 없다.

- **바꿀 것:** search_voc 에 core_type · core_key 인자를 둔다. 운영 박스 ontology_lookup 이 이 앱에 다음 호출을 넘길 수 있게 된다.

- **위치:** SignalForge search_voc

- **확인:** search_voc(core_type=plm_project, core_key=P1) → 그 프로젝트 제품 범위 결과.

- **먼저:** SFO-1



### 1-10. MXWhitePaper — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| MW-06 | (선택) 위키 온톨로지 코어 받기 · 대응 글자 | P3 | 받았으나 안 끝남 |

| MW-08 | (질문) restricted 2건이 시드인가 | P3 | 받았으나 안 끝남 |

| MW-09 | (질문) 서비스 계정으로 위키를 켜면 소유자 검사가 약해지나 | P3 | 받았으나 안 끝남 |



#### MW-06 · (선택) 위키 온톨로지 코어 받기 · 대응 글자

`P3` · 받았으나 안 끝남



- **문제:** /api/core · core:read 를 쓰는 코드가 0건이고 대응 글자가 코어 칸과 다르다(plm_task 에 test_kind 없음).

- **바꿀 것:** 필요해지면 받는 코드를 붙이고 대응 글자를 rootdesign 칸으로 고친다.

- **위치:** apps/api/alembic/versions/0056_wiki_ontology.py:52-70

- **확인:** 0056_wiki_ontology.py 의 대응 글자에 test_kind 가 없고 코어 plm_task 칸(task_status · milestone · task_code)을 쓰며, 받는 코드가 /api/core 를 core:read 로 부른다.

- **받은 곳 · 상태:** 10-27 요청은 MXWhitePaper 가 받았다 — 같은 날 커밋 76297b6(MW-01 · MW-02) · 5a41e3a(MW-03) · 06b3d6d(MW-05) · bf316aa(MW-07). MW-06 커밋 · 문서 기록은 없다(HEAD d755a00, 11-23 기준 docs 에 0건). 아직 안 된 것: 선택 항목 전체 — 코어 받는 코드와 대응 글자 고침.

- **참고:** 선택 항목 — 필요할 때.



#### MW-08 · (질문) restricted 2건이 시드인가

`P3` · 받았으나 안 끝남



- **문제:** 소유자가 자리표시라 시드로 보인다. 답에 따라 사용자 결정 D7 ①(MW-10 — restricted 2건을 지움 · 보관 · 소유자 정정 중 하나로 정함)이 보관(시드)과 소유자 정정(실제 소유자) 중 하나로 정해진다.

- **바꿀 것:** 시드인지 답한다.

- **받은 곳 · 상태:** MXWhitePaper docs/llm-wiki/context-notes.md:95 「dev 의 restricted 2 장은 owners 가 사람 id 가 아닌 글」 — 시드 정황만 있다. 아직 안 된 것: MW-08 에 대한 명시 답(시드인가)이 없고 커밋도 없다.

- **참고:** MW-10 결정의 재료.



#### MW-09 · (질문) 서비스 계정으로 위키를 켜면 소유자 검사가 약해지나

`P3` · 받았으나 안 끝남



- **문제:** 우리 추정이다. 맞다면 사용자 결정 D7 ②(MW-10 — 게이트웨이 per_user_sso 에 mx-white-paper · MXWP_SSO_SECRET · <접두>_SEND_PLAT=1 · 재프로비저닝으로 사람별 위임을 켤지)의 '위키를 켜기 전에 사람별 위임' 이 꼭 필요하다.

- **바꿀 것:** wiki_submit_source 소유자 검사가 '서비스 계정 보증' 으로 약해지는지 답한다.

- **위치:** wiki_submit_source

- **받은 곳 · 상태:** MXWhitePaper git log · docs/llm-wiki/context-notes.md 에 MW-09 0건. 같은 파일 :147 WK-D43(사용자 결정 10-24, 커밋 f6e9df2)은 게이트웨이의 신원 없는 내부 호출(서비스 계정 API 토큰)의 위키 시야가 [org] 뿐이라는 결정만 적는다. 아직 안 된 것: wiki_submit_source 소유자 검사가 '서비스 계정 보증' 으로 약해지는지에 대한 답.

- **참고:** MW-10 결정의 재료.



### 1-11. KooRemapper — 6건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| KR-10 | SmartTwin 전각도 낙하 job_status 종료 판정 고정 | P2 | 받았으나 안 끝남 |

| ST-25-KR | DynaForge maps_to 공통 블록에도 cad_part 출발 더하기(ST-25 짝) | P2 | 새 요청 |

| KR-12 | rootdesign 에 없는 타입 · 칸 가정(plm_test_site · model_revision_kind) | P3 | 받았으나 안 끝남 |

| KR-19 | (다음 판) 전각도 낙하 나머지 옵션 · 결과 회수 | P3 | 받았으나 안 끝남 |

| R-04 | KooRemapper 배포 재기동이 옛 인스턴스를 안 기다림 | P3 | 새 요청 |

| R-09 | KooRemapper 자리표시 문구 · 레시피 파일 추적 밖 | P3 | 새 요청 |



#### KR-10 · SmartTwin 전각도 낙하 job_status 종료 판정 고정

`P2` · 받았으나 안 끝남



- **문제:** 폴링 · get_job_details 종료 판정 · external_ref 는 92cb157(10-25)에 들어갔지만 상태 칸 이름을 실물로 못 봐 판정이 고정되지 않았다. 운영 박스 제출은 0건이었다.

- **바꿀 것:** 우리가 보내는 첫 실제 제출 응답 원문으로 '전부 끝남 / 하나라도 실패' 판정을 고정한다.

- **위치:** runner 의 SmartTwin 클라이언트(기준 92cb157)

- **확인:** 전부 끝남과 하나라도 실패가 갈려 잡 상태에 남는다.

- **선례:** 92cb157

- **먼저:** 운영 쪽 몫 — 첫 실제 제출 · KOORM_GATEWAY_PAT 채우기 · 응답 원문 전달

- **받은 곳 · 상태:** KooRemapper docs/04-report/hwax-request-1027.report.md:59 「첫 실제 제출의 job_status 응답 원문이 있어야 종료 판정을 고정한다(KR-10) … 우리 첫 제출이 먼저다」. 10-28 뒤 KR-10 커밋 없음. 아직 안 된 것: 운영 쪽 첫 실제 제출 · 응답 원문 전달(우리 몫), 그 뒤 종료 판정 고정.

- **참고:** KooRemapper 쪽은 기다리는 중이다. 막힌 곳은 우리 첫 제출.



#### ST-25-KR · DynaForge maps_to 공통 블록에도 cad_part 출발 더하기(ST-25 짝)

`P2` · 새 요청



- **문제:** maps_to 관계 정의가 StepForge · DynaForge 에 바이트 동일 공유 블록(D-689)으로 들어 있어, ST-25 가 StepForge 쪽 출발 목록에 cad_part 를 더하면 DynaForge 사본과 어긋난다.

- **바꿀 것:** KooRemapper platform/core/ontology/dynaforge-core.json 의 maps_to 공유 블록 출발 목록에 cad_part 를 같은 판에 함께 더함(칸 · 차례는 StepForge 와 같게).

- **위치:** KooRemapper platform/core/ontology/dynaforge-core.json maps_to(공유 블록)

- **확인:** 두 정의의 maps_to 블록이 바이트 동일 · DynaForge cae_part 다리 결과 변화 0

- **선례:** 81bfbde1(maps_to 공통 블록, SRC-08)

- **먼저:** ST-25 와 같은 판에 함께(maps_to 공유 블록이 바이트 동일해야 하므로 어느 쪽도 먼저가 아니다).

- **참고:** ST-25 를 보낼 때 KooRemapper 에도 한 줄 함께 보냄.



#### KR-12 · rootdesign 에 없는 타입 · 칸 가정(plm_test_site · model_revision_kind)

`P3` · 받았으나 안 끝남



- **문제:** EXTERNAL_TYPES 에 plm_test_site 가 있고 model_revision_kind · base_code · series · plm_derived_from 을 가정하지만 허브에는 없다.

- **바꿀 것:** plm_test_site 를 '허브에 없음' 으로 두거나 빼고, model_revision_kind 대신 쓸 칸(model_kind · rc_marker)을 정한다.

- **위치:** platform/backend/app/runner/ontology_def.py:53(HEAD 76067368) · services.py:95-108 · tests/test_ontology_def.py:110

- **확인:** plm_test_site 가 '허브에 없음' 으로 보이고 개정 종류가 실제 칸으로 채워진다.

- **선례:** 54304cdd

- **먼저:** DP-13(Datahub 플랫폼 팀 알림 — plm_test_site 는 허브에 두지 않는 것으로 봄, 계획이 다르면 알려 달라) — 허브가 그 타입을 둘 계획인지

- **받은 곳 · 상태:** KooRemapper 54304cdd(10-27)는 ontology-graft 계획서 §1-4 표만 실측으로 고쳤다(plm_test_site · model_revision_kind · base_code · series · plm_derived_from 는 허브 공개 목록에 없음 표시). docs/04-report/hwax-request-1027.report.md:54 「대체 필드·plm_test_site 취급은 허브 확인 뒤 결정(미결)」 · 「짐작으로 코드에 안 박음」. 아직 안 된 것: 코드 몫 전체 — ontology_def.py:53 EXTERNAL_TYPES 의 plm_test_site, model_revision_kind 대신 쓸 칸.

- **참고:** 문서 몫은 끝, 코드 몫이 남았다.



#### KR-19 · (다음 판) 전각도 낙하 나머지 옵션 · 결과 회수

`P3` · 받았으나 안 끝남



- **문제:** 피보나치 외 각도 방식 · 공차 · DR · 접촉 · 연속 낙하 옵션과 결과 회수가 없다. 결과가 상대 클러스터 output_dir 에만 남는다.

- **바꿀 것:** 옵션 매핑(병합 규칙 감안) · sphere_report.html 인제스트 · *INCLUDE 덱을 다음 판에 넣는다.

- **확인:** 옵션을 준 제출의 결과가 DynaForge 리포트로 들어온다.

- **먼저:** KR-10 · 운영 쪽 첫 실제 제출

- **받은 곳 · 상태:** KooRemapper docs/04-report/hwax-request-1027.report.md:59 「나머지 옵션·결과 회수(KR-19)는 다음 판 + 저쪽 대기」. 그 뒤 KR-19 커밋 없음. 아직 안 된 것: 옵션 매핑 · sphere_report.html 인제스트 · *INCLUDE 덱 전부(KR-10 과 운영 쪽 첫 실제 제출이 먼저).



#### R-04 · KooRemapper 배포 재기동이 옛 인스턴스를 안 기다림

`P3` · 새 요청



- **문제:** 새 SIF 를 살아 있는 API 밑에 덮고, stop 이 안 기다리고, start 가 내려가는 중인 인스턴스를 already running 으로 봐 10-28 에 52분 멈췄다.

- **바꿀 것:** stop 이 끝날 때까지 기다리고, SIF 교체는 멈춘 뒤에, start 는 내려가는 중을 구분한다.

- **위치:** KooRemapper 배포 스크립트 · 포털 deploy-all

- **확인:** 배포 중 API 멈춤 없이 새 판이 뜬다.

- **선례:** KR-04

- **참고:** 운영 박스 KooRemapper 는 11-24 쉬는 중이라 P3.



#### R-09 · KooRemapper 자리표시 문구 · 레시피 파일 추적 밖

`P3` · 새 요청



- **문제:** 화면 '과제코드' 자리표시 문구가 남고, 레시피 등록 파일이 추적 밖이라 update-all stash 에 쓸려 간다.

- **바꿀 것:** 자리표시 문구를 고치고 레시피 등록 파일을 추적하거나 stash 대상에서 뺀다.

- **위치:** KooRemapper 화면 · 레시피 등록 파일

- **확인:** update-all 뒤에도 등록 레시피가 남는다.

- **선례:** KR-01 · KR-23



### 1-12. 여러 저장소 공통 — 2건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| HP-71 | 예시 .env 파일에 코어 주소 키(포털 경로 꼴)와 NO_PROXY 의 포털 도메인이 없음 | P3 | 새 요청 |

| IR-51 | 생각 끄기를 모델 끝점마다 고를 수 있게(DocForge · 에이전트 서버) | P3 | 새 요청 |



#### HP-71 · 예시 .env 파일에 코어 주소 키(포털 경로 꼴)와 NO_PROXY 의 포털 도메인이 없음

`P3` · 새 요청



- **문제:** 포털 도메인 요청이 사내 프록시를 타면 끊긴다(프록시 경유 curl 56, --noproxy 200). 운영 박스 .env 는 11-12 에 고쳤지만 새 박스 · dev 박스는 예시 파일을 따라 같은 자리에서 막힌다. KooRemapper 예시는 허브 직결 꼴이라 포털 경로의 rootdesign 겹침을 틀리기 쉽다.

- **바꿀 것:** 세 예시 파일에 코어 주소 키를 포털 경로 꼴(https://<포털 도메인>/rootdesign/rootdesign/api)로 적고 rootdesign 이 두 번인 까닭(앞은 포털 경로, 뒤는 허브 API)을 한 줄 적는다. 같은 예시의 NO_PROXY 에 포털 도메인 자리표시를 더한다.

- **위치:** SignalForge .env.example:15 · HEAXHub .env.example · KooRemapper platform/.env.example:99 (요청 때 :94)

- **확인:** 세 예시 파일에 코어 주소 키가 포털 경로 꼴로 있고 NO_PROXY 에 포털 도메인 자리표시가 있다. 그 예시로 만든 새 .env 에서 코어 받기가 프록시 없이 200.

- **참고:** 운영 영향은 없고 새 박스 대비다. SignalForge 예시 NO_PROXY 값은 출력하지 않아 '키 있음' 까지만 봤다.



#### IR-51 · 생각 끄기를 모델 끝점마다 고를 수 있게(DocForge · 에이전트 서버)

`P3` · 새 요청



- **문제:** 모든 호출에 enable_thinking: false 를 싣는데, 챗 모델에는 맞지만 심의 모델에서는 이것이 영어 생각 글을 답 칸 앞에 새게 한다(11-10 네 꼴 비교, 답 400 ~ 580 토큰, 꼬리표 없음). modelcall.py:47-48 의 </think> 자르기로는 못 거른다.

- **바꿀 것:** 끝점마다 생각 끄기를 고를 수 있게 손잡이로 뺀다(기본은 지금대로). 심의 모델 끝점은 끄기를 보내지 않고 reasoning_content 를 버린다.

- **위치:** DocForge modelcall.py:21-22(0.3.1 기준) · HWAXAgentServer vision.py:189 · :287(HEAD b0fd922)

- **확인:** 심의 모델 끝점으로 판독 · 다듬기를 보낼 때 답 칸에 생각 글이 없다.

- **참고:** 에이전트 서버 몫이 함께 있다. 지금 판독은 챗 모델 · 판단은 JSON 스키마라 급하지 않지만, 판독을 심의 모델로 나누기 전에 있어야 한다. 운영 박스는 이 손잡이가 없어(DocForge modelcall.py:22 고정) 판독을 심의 모델로 옮기지 않았다 — 옮기면 판독문에 영어 생각 글이 섞인다. 들어오면 챗 모델이 바쁠 때 판독을 심의 모델로 나눌지 다시 본다.



---



## 2. MCP 효율 — 게이트웨이 · 에이전트 서버 · 백엔드 (11-24 비교 64회 근거)



Claude 가 hwax 도구를 덜 읽고 덜 헤매게 하는 고침입니다. 수치는 11-24 비교 64회와 그 대화 기록에서 쟀습니다. **(추정)** 은 잰 값으로 계산한 어림입니다. B-1 · B-2 · P-1 은 다른 요청서의 같은 번호와 갈라 `[11-24]` 를 붙였습니다.



**가장 큰 낭비 둘**

- **도구 이름 목록:** 1,9xx 개 이름이 세션마다 시작 문맥에 실립니다. 들어올 때 문맥이 36.9k~38.8k 토큰 뜁니다.

- **큰 원문 결과:** 기준선에서 모델이 받은 hwax 결과 2.34M자 가운데, 20,000자 넘는 35건이 1.02M자(44%)입니다. 결과 손잡이는 `stored: 0` 입니다.



둘 다 게이트웨이에 이미 장치(`X-HWAX-View`, `X-HWAX-Result: ref`)가 있습니다. PC 연결이 이 머리를 보내지 않아 쓰인 적이 없습니다.



**받는 순서**

1. A-1 가운데 OF-1 ~ OF-5 몫은 1-3 절 우선순위대로 지금 받습니다.

2. 운영 쪽이 박스 옵션과 연결 머리만으로 한 판(64회, 약 $78 (추정))을 잽니다. 결과 손잡이 켜기(`X-HWAX-Result: ref` 머리 · `GATEWAY_RESULT_REFS=1`), 가벼운 보기 머리(`X-HWAX-View`), 연결 기다림 60 초(`MCP_TIMEOUT=60000`)입니다(아래 '운영 쪽에서 할 것').

3. 나머지(G-1 ~ G-5 · A-1 의 실행기 결과 줄이기 · A-2 · B-1 [11-24] · B-2 [11-24] · P-1 [11-24])는 그 결과를 받은 뒤 시작합니다. 그 판에서 인자 오류나 패배가 늘면 G-1 · G-2 를 먼저 합니다.



**차례(효과 ÷ 노력 순):** 1) G-1 · P-1 [11-24] 2) G-2 3) G-3 4) A-1 5) G-4 6) B-1 [11-24] 7) B-2 [11-24] 8) A-2 9) G-5. P-1 [11-24] 은 G-1 뒤에 넣습니다. A-1 의 OF-1 ~ OF-5 몫은 1-3 절 우선순위를 따릅니다.



| 요청 | 저장소 · 위치 | 바꿀 것 | 예상 효과 | 확인 |

|---|---|---|---|---|

| G-1 | 게이트웨이 `gateway.py` 보기 구성(:9367 근처) | `light` 보기에 다음을 더합니다. 지금 `light` 는 search_tools · invoke_tool 둘뿐입니다.<br>• 패널 도구(`_meta.ui` 17개)<br>• `verify_answer`<br>• `list_tool_apps` | `X-HWAX-View: light` 연결의 시작 문맥 약 −37k 토큰(−42%) | `light` 연결로 tools/list 에 패널 도구 · verify_answer · list_tool_apps 가 있고, 패널이 열림 |

| G-2 | 게이트웨이 `gateway.py` 서버 지침(:1991 근처) · search_tools 응답 꼴 · `test_gateway.py` 지침 시험 | **지침 1번을 한 길로:**<br>• 이름을 알면 바로 부르고, 모르면 search_tools 한 번 → invoke_tool<br>• 낱말 ToolSearch 금지<br>**지침 9 · 10번(권한 · 끈 앱 안내):** `list_tool_apps` 응답의 `how` 로 옮겨 2,048자 상한 안에 자리를 만들고, 그 자리에 손잡이 안내를 넣습니다.<br>**search_tools 행:** 바로 부를 수 있는 꼴(이름 · 필수 인자 · 예시 한 줄) | 기준선 도구 호출의 22.6%인 찾기 호출이 줄어듭니다. ToolSearch 로 스키마를 불러온 도구 315개(약 0.33M자)도 줄어듭니다. | 지침 길이 ≤ 2,048자 시험 통과. 같은 과제에서 찾기 호출 수 감소 |

| G-3 | 게이트웨이 `gateway.py` capabilities | `tools.listChanged: true` 를 둡니다. 백엔드 목록 · 사람별 보기 · 끈 앱이 바뀌면 `notifications/tools/list_changed` 를 보냅니다. | 재기동 뒤 새 도구를 헛찾기 없이 부릅니다. 11-24 2판 갈래에서는 낱말 헛찾기 20회, invoke_tool 감싸기 130회가 나왔습니다. | 게이트웨이 재기동 뒤 재연결 없이 새 도구가 보임. mcp-remote 가 알림을 넘기는지, 포털 경로 침묵 상한에 끊기지 않는지 확인 |

| G-4 | 게이트웨이 `gateway.py` 같은 이름 접두어(:1478 근처) · 옛 이름 별칭(:4371 근처) | 데이터허브 5종의 같은 도구 116개를 한 벌만 싣고, `hub` 인자로 백엔드를 고르게 합니다. 옛 접두 이름은 목록에서 빼되 호출은 계속 받습니다(별칭). 권한은 `hub` 값마다 판정합니다. | 도구 −464개(−23.5%), 이름 목록 약 −10.7k 토큰 (추정) | tools/list 수 감소. 옛 이름 호출 성공. 찾기 평가 hit@1 · MRR 가 떨어지지 않음 |

| G-5 | 게이트웨이 tools/list | 각 도구 `annotations.readOnlyHint` 를 게이트웨이 읽기 판정(`routine_read`)으로 채웁니다. 백엔드 표지가 있으면 그것을 씁니다. 지금은 1,972개 중 83.5% 가 표지 없음입니다. | 클라이언트가 읽기 도구를 구별할 근거가 생깁니다(효과 미측정). | 표지 수, 쓰기 도구가 읽기로 표시되지 않음 |

| A-1 | 에이전트 서버 `offload.py` · `mcp_server.py` · `evidence.py` | 1-3 절의 OF-1 ~ OF-5 를 반영합니다(그 다섯은 1-3 절 항목으로 받고 여기서 따로 세지 않습니다). 덧붙여 위임 실행기가 단계마다 앞선 결과를 줄여 싣게 합니다(예: 결과 하나 6,000자 상한, 근거 원문은 따로). 위임 23건의 서버 LLM 입력이 22.45M(건당 0.98M)으로, Claude 가 아낀 8.55M 의 약 2.6배였습니다. 실행기가 매 단계 앞선 결과 전체를 다시 읽는 것으로 보이지만 추정이고 확인하지 않았습니다. 먼저 실행기가 단계마다 무엇을 다시 싣는지 확인해 주세요. | 11-24 합의 패 8 가운데 6 의 원인 제거가 목표입니다. 상태 호출은 46 → 23 이하 (추정) | 2판을 다시 켠 A/B 에서 다음을 봅니다.<br>• 패배율<br>• `incomplete` 비율<br>• 숫자 어긋남(종류별)<br>• 서버 LLM 토큰 |

| A-2 | 에이전트 서버 `app.py` 코어 데이터 규칙 · 예약 도구 | 「코어 데이터 규칙」 ①–⑦ 과 예약 도구 16개를, 규칙 낱말이 든 턴에만 싣습니다. | 낱말이 없는 웹 채팅 턴마다 약 650자 + 스키마 16개(약 17k자)가 빠집니다. | 웹 채팅 온톨로지 질문 묶음의 정답률이 떨어지지 않음 |

| B-1 [11-24] | 결과 글자 상위 5 도구 — report_worst_cases · deliberate_result · get_material_properties · report_summary · agent_search. deliberate_result 는 에이전트 서버 자기 도구이고, agent_search 는 AIDataHub 도구다. 나머지 셋은 게이트웨이 /tools-map 에서 백엔드 키를 보고 그 저장소에서 고친다. 개발 세션 저장소가 아닌 백엔드의 도구면 알려 주세요. | 다음을 둡니다.<br>• `fields` · `limit` · `brief` 인자<br>• 응답의 `total` · `truncated` · 다음 쪽 손잡이<br>기본값은 지금과 같이 두고, MCP 개인 연결에서만 요약 꼴을 기본으로 합니다(웹 챗 · 루틴 꼴은 그대로). 게이트웨이는 결과 손잡이에서 이미 사람 PAT 연결과 웹 챗 · 절차 · 패널을 가립니다. 그 구분을 백엔드에 어떻게 넘길지는 dev 가 정합니다. | 이 다섯이 결과 글자의 35% 입니다. 기본 꼴을 1/3 로 줄이면 결과 글자 −23% (추정) | 도구별 결과 글자(게이트웨이 감사 `chars`)와 재호출 수 |

| B-2 [11-24] | 설명이 1,000자 넘는 도구를 가진 백엔드 가운데 개발 세션 저장소(포털 · 게이트웨이 · 에이전트 서버 · HEAXHub · AIDataHub · SignalForge · MXWhitePaper · KooRemapper) 몫. 296개는 모든 백엔드를 합한 수다. 게이트웨이 /tools-map 으로 백엔드별 수를 먼저 센다. 다른 팀 백엔드 몫은 이 요청에 들지 않는다. | 첫 문단을 「언제 쓰나 · 필수 인자 · 함정 한 줄」 600자 안으로 줄입니다. 예시 · 긴 규칙은 `get_guide` 나 search_tools detail 로 옮깁니다. | 도구 하나를 불러올 때 평균 1,050자 → 약 750자 (추정) | 설명 글자 분포와 인자 오류 수 |

| P-1 [11-24] | 포털(PC 연결 설정을 만들어 주는 곳이 있다면) | 그 생성 결과에 `X-HWAX-Result: ref` 와 `X-HWAX-View: light`(또는 사람별 설정을 따르는 `portal`) 머리를 기본으로 넣습니다. light 를 기본으로 넣는 것은 G-1 뒤입니다. G-1 전의 light 는 search_tools · invoke_tool 둘뿐이라 패널 도구가 목록에서 빠져 화면이 열리지 않습니다. 그런 생성 코드가 있는지부터 확인해 주세요. | G-1 과 결과 손잡이(`X-HWAX-Result: ref`)의 효과를 모든 사람이 받습니다. | 새로 받은 연결 설정에 두 머리가 들어 있음 |



**운영 쪽에서 할 것(개발 요청 아님, 참고)**

- 게이트웨이 `provision.env` 의 `GATEWAY_RESULT_REFS=1` 과 재기동.

- 게이트웨이 `read_tools.local.json` 에 결함 집계 읽기 4종 추가. 읽기 도구인지 먼저 확인합니다.

- 소스 반영 뒤 에이전트 서버 2판 스위치 넷을 다시 켭니다.

- PC 연결 인자에 머리 둘을 넣고 `MCP_TIMEOUT=60000` 을 둡니다.



**설계 결정이 필요한 것:** 위임 안에서 심의 결과(deliberate_result)를 읽게 할지 정해야 합니다. 지금은 에이전트 서버 자기 도구라 위임 울타리에서 뺐습니다.



---



## 3. 다른 팀 몫



각 플랫폼 담당에게 따로 보냅니다. 운영 쪽 문서에 보낸 기록이 없는 것은 **보낸 기록 없음** 으로 적었습니다. 이미 보냈으면 그 항목은 빼 주세요.



보내기 전에 운영 쪽이 볼 것 — PA-02: nginx 기록으로 지금도 되풀이되는지(근거 수치는 10-23 ~ 10-25). RQ-12: 11-13 이후 새 시도가 없는지.



### 3-1. ReportArchive — 27건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| IR-41 | Report Archive 글 보기(text)에서 rich_text 본문 · 그림 줄 내기 | P1 | 보낸 기록 없음 |

| IR-42 | Report Archive PPTX 가져오기 — 차트 개체 · 발표자 노트 · 그림 채움 옮기기 | P1 | 보낸 기록 없음 |

| RAO-1 | Report Archive 에 sp_core 소스 등록 | P1 | 보낸 기록 없음 |

| RP-01 | 위임 호출에 워크스페이스 헤더가 없을 때 home 적용 · SSO 새 계정에 home 배정 | P1 | 보낸 기록 없음 |

| RP-02 | SSO 토큰 회수 창구(/api/auth/sso/revoke) | P1 | 보낸 기록 없음 |

| RP-03 | DRM PPTX 를 업로드 · 추출에서 알아보기 | P1 | 보낸 기록 없음 |

| RP-04 | 업로드 티켓 · 파일이 평문 http 로 사내 프록시를 지남 | P1 | 보낸 기록 없음 |

| RP-05 | PC 전체 Windows 경로가 파일 이름으로 저장됨 | P1 | 보낸 기록 없음 |

| RP-15 | (질문) 헤더 없는 호출을 지금 어떻게 처리하나 | P1 | 보낸 기록 없음 |

| IR-43 | Report Archive PPTX 가져오기 완료 응답에 빠진 요소를 종류별로 · 그림 블록 이름 | P2 | 보낸 기록 없음 |

| IR-44 | Report Archive PPTX 가져오기의 그림 판독을 DocForge 에 맡기기 | P2 | 보낸 기록 없음 |

| RAO-2 | 관계 셋의 끝 타입 defect 정의 또는 failure_mode 로 고치기 | P2 | 보낸 기록 없음 |

| RAO-3 | 보고서 태그 축에 코어 과제 · 고장모드 · 부품 | P2 | 보낸 기록 없음 |

| RP-06 | /api/me/workspace 를 다시 고를 수 있게 · MCP/REST 로 | P2 | 보낸 기록 없음 |

| RP-07 | X-Heax-Client 단위 재발급 회전 | P2 | 보낸 기록 없음 |

| RP-08 | SSO 토큰 수명 단축(12시간 권장) | P2 | 보낸 기록 없음 |

| RP-09 | 발급 창구 성질 확인(시크릿 · 비교 · 기록) | P2 | 보낸 기록 없음 |

| RP-10 | 기존 보고서 소유자 백필 | P2 | 보낸 기록 없음 |

| RP-11 | ask_ontology 시간 상한 | P2 | 보낸 기록 없음 |

| RP-16 | (질문) PPTX 가져오기 상한 · 오류 문구 | P2 | 보낸 기록 없음 |

| RP-12 | get_guide 'write' 파일 위젯 문장 어긋남 · 크기 문구 | P3 | 보낸 기록 없음 |

| RP-13 | list_folders 가 부서 이름으로 게시판을 못 찾음 | P3 | 보낸 기록 없음 |

| RP-14 | 헤더 없는 호출의 폴백 규칙을 OpenAPI 에 | P3 | 보낸 기록 없음 |

| RP-17 | (질문) /api/me 응답 모양 | P3 | 보낸 기록 없음 |

| RP-18 | (질문) MCP 서버가 X-Workspace-Slug 를 REST 로 어떻게 내리나 | P3 | 보낸 기록 없음 |

| RP-19 | (질문) 추출 그림 workspace_slug 꼴이 원본과 다름 | P3 | 보낸 기록 없음 |

| RP-20 | (질문) has_defect 끝 타입 defect 가 타입 목록에 없음 | P3 | 보낸 기록 없음 |



#### IR-41 · Report Archive 글 보기(text)에서 rich_text 본문 · 그림 줄 내기

`P1` · 보낸 기록 없음



- **문제:** get_report(format="text") 로 읽으면 포털 '정밀 변환' 길로 만든 시험 보고서 2077 은 10쪽 모두 제목과 차트 표만(425자), RA 가져오기로 만든 시험 보고서 2078 은 제목과 '- level: 1' 한 줄뿐(244자)이다. 큰 보고서는 기본이 text 라 챗 · 심의가 본문 · 판독 · 노트를 못 본다.

- **바꿀 것:** rich_text 의 items 를 글로 내 준다. 그림 블록도 '[그림] 이름 · 캡션' 한 줄을 낸다. '- level: 1' 같은 속성 줄은 뺀다.

- **위치:** Report Archive get_report(format="text")

- **확인:** 시험 보고서 2077 · 2078 을 text 로 읽으면 본문 글 · 모델 판독 · 발표자 노트와 그림 줄이 나온다.

- **참고:** widgets 로는 31블록이 모두 있고 search_reports 는 본문을 찾는다 — 글 보기만의 문제다. 이 요청의 Report Archive 몫 가운데 가장 먼저 할 것이다(보고서에 무엇을 싣든 챗 · 심의가 읽을 수 있게). 시험 보고서 2077 · 2078 은 둘 다 본인 공간 초안이고, 지울지는 운영자가 정한다.



#### IR-42 · Report Archive PPTX 가져오기 — 차트 개체 · 발표자 노트 · 그림 채움 옮기기

`P1` · 보낸 기록 없음



- **문제:** 가짜 값으로 만든 10쪽 시험 덱을 RA 가져오기로 올린 시험 보고서 2078 에서 차트 개체(6쪽) · 그림 채움 도형(8쪽, 쪽에 제목만 남음) · 발표자 노트(9쪽)가 통째로 빠졌다. 같은 덱을 DocForge 와 AI 데이터 허브는 차트 값까지 옮겼다.

- **바꿀 것:** 차트 개체 → 차트 위젯(값 그대로), 발표자 노트 → 글 블록, 그림 채움 도형 → 그림 블록으로 옮긴다.

- **위치:** Report Archive PPTX 가져오기(/api/imports/pptx)

- **확인:** 같은 시험 덱(imgtest-20261110.pptx)을 가져오면 6쪽 차트 위젯 값 · 9쪽 노트 글 블록 · 8쪽 그림 블록이 있다.

- **참고:** HWAX 포털이 정밀 변환 결과를 앞에 두는 변경이 들어오면 급함이 줄어든다.



#### RAO-1 · Report Archive 에 sp_core 소스 등록

`P1` · 보낸 기록 없음



- **문제:** 데이터 소스가 SPDM REST 둘뿐(수동, 마지막 07-20 · 07-15)이고 코어 소스가 없어 get_sp_catalog · get_sp_mapping_plan · get_sp_ontology_plan 에 넘길 소스가 없다. 허브에 RA 토큰도 없다.

- **바꿀 것:** RA 관리자가 커넥터 화면에서 코어(rootdesign 허브)를 받는 sp_core 소스를 등록한다. 주소는 운영 쪽이 알리고 토큰은 운영 쪽 사용자가 허브에서 발급을 정한다.

- **위치:** ReportArchive 커넥터 화면 · list_data_sources

- **확인:** list_data_sources → sp_core 소스 하나, 마지막 실행 ok. get_sp_catalog(source_id) → 코어 타입 목록.

- **선례:** 앞선 RA 요청 RP-01 ~ RP-20(같은 문서 — SSO 홈 워크스페이스 · 토큰 회수 · 거절 사유 등)

- **참고:** Q-1 — 코어 개발모델을 RA 기존 model 타입에 붙일지 새 타입으로 둘지 RA 권고 요청(운영 쪽 사용자가 정함). 토큰 발급은 사용자 결정.



#### RP-01 · 위임 호출에 워크스페이스 헤더가 없을 때 home 적용 · SSO 새 계정에 home 배정

`P1` · 보낸 기록 없음



- **문제:** 사람별 위임 호출에는 X-Workspace-Slug 가 없고, RA 는 SSO 로 계정을 만들 때 부서(home)를 배정하지 않아 새 사용자 보고서가 개인함에 쌓일 수 있다. 전체 62명 → 500명 예정.

- **바꿀 것:** 헤더 없는 호출은 그 계정의 home_workspace_slug 를 쓴다. SSO 새 계정에 home 을 반드시 배정하거나 못 하면 응답에 밝힌다.

- **위치:** RA 의 X-Workspace-Slug 없는 호출 처리 · SSO 새 계정 만들기 · POST /api/me/workspace(관리자 길은 PUT /api/users/{id}/home-workspace). 게이트웨이의 사람별 위임 호출은 소속 헤더 2개만 싣고 X-Workspace-Slug 는 싣지 않는다.

- **확인:** 새로 SSO 로 만든 사람의 보고서가 개인함이 아니라 제 부서 함에 들어간다.

- **먼저:** RP-15

- **참고:** 포털 쪽은 위임으로 받은 토큰으로 RA 를 부를 때 X-Workspace-Slug 를 이미 싣지 않는다(11-21 결정).



#### RP-02 · SSO 토큰 회수 창구(/api/auth/sso/revoke)

`P1` · 보낸 기록 없음



- **문제:** 포털에서 사람을 정지해도 RA 가 내준 위임 토큰은 만료(expires_in 172800 = 48시간)까지 산다. 포털 쪽 정리(정지 때 ste 토큰 회수 · 포털이 든 RA 위임 토큰 버리기 · 게이트웨이의 그 사람 토큰 캐시 비우기)는 끝났다. 남은 것은 RA 안에서 회수하는 호출이다.

- **바꿀 것:** POST /api/auth/sso/revoke 를 열어 포털이 정지 때 부른다.

- **위치:** RA /api/auth/sso/revoke

- **확인:** 정지 처리 뒤 그 사람의 기존 RA 토큰 호출이 거절된다.

- **참고:** 창구가 생기면 포털이 정지 처리 때 부른다.



#### RP-03 · DRM PPTX 를 업로드 · 추출에서 알아보기

`P1` · 보낸 기록 없음



- **문제:** DRM PC 기본 업로드 길이 PPTX 암호문(앞 34바이트 사내 DRM 머리, 37,316 B)을 그대로 올리고 추출은 'zip 손상' 이라고만 답해 같은 시도가 되풀이된다.

- **바꿀 것:** 업로드 · 추출이 앞 바이트의 사내 DRM 머리(3C 23 23 20 4E 41 53 43 41)를 알아보고 'DRM 암호화 문서 — 포털 챗 업로드나 PC 도우미(COM 추출)로' 라는 별도 오류를 낸다. pptx 인데 PK 로 시작하지 않으면 업로드에서 거절한다. 가이드에 한 줄 적는다.

- **위치:** prepare_upload · /mcp/files/upload · extract_pptx_images

- **확인:** RA 웹 'PPT에서 불러오기' 와 prepare_upload 길 모두 'DRM 암호화 문서' 오류를 낸다.

- **선례:** AIDataHub 문서 변환(10-30) — 변환기에 넣기 전에 앞 바이트가 사내 DRM 머리(3C 23 23 20 4E 41 53 43 41)나 OLE 머리(D0 CF 11 E0)이면 422 · DRM_PROTECTED 로 따로 알린다.

- **참고:** 포털 첨부는 같은 머리로 암호화 문서를 이미 가려낸다.



#### RP-04 · 업로드 티켓 · 파일이 평문 http 로 사내 프록시를 지남

`P1` · 보낸 기록 없음



- **문제:** prepare_upload 가 만드는 curl 의 upload_url 이 평문 http :3002 이고 curl -v 가 사내 프록시 경유를 보였다. 5분 티켓과 파일 본문이 평문으로 지난다.

- **바꿀 것:** upload_url 을 포털 도메인 https 경로로 바꾼다. 당장은 curl 에 --noproxy 를 붙이고 가이드에 적는다.

- **위치:** prepare_upload 응답 upload_url

- **확인:** 만든 curl 의 -v 에 프록시 경유가 없고 주소가 https 다.



#### RP-05 · PC 전체 Windows 경로가 파일 이름으로 저장됨

`P1` · 보낸 기록 없음



- **문제:** filename 이 드라이브 문자로 시작하고 역슬래시 11개 · 143자다. PC 사용자 폴더명이 첨부 · 내려받기 이름에 드러난다.

- **바꿀 것:** prepare_upload 와 /mcp/files/upload 가 / 와 \ 를 구분자로 보고 basename 만 저장한다.

- **위치:** prepare_upload ?filename= · /mcp/files/upload

- **확인:** RA 에 저장된 파일 이름이 PC 경로가 아니라 파일명뿐이다.

- **참고:** RA 에 남은 10-25 시험 파일 4개(PC 경로가 이름에 든 c7c475ff 포함)를 지울지는 우리 몫이고 우리 쪽에서 정한다.



#### RP-15 · (질문) 헤더 없는 호출을 지금 어떻게 처리하나

`P1` · 보낸 기록 없음



- **문제:** 우리 기록 둘('토큰 기본 워크스페이스' · '개인함')이 엇갈리고 둘 다 실측 아님.

- **바꿀 것:** 답.

- **위치:** RA 가 X-Workspace-Slug 없이 들어온 호출을 처리하는 곳(게이트웨이의 사람별 위임 호출)

- **확인:** 헤더 없는 호출이 어느 워크스페이스로 가는지(토큰의 기본 워크스페이스인지, 개인함인지) RA 가 답한다.

- **참고:** RP-01 · RP-14 가 이 답을 기다린다. HWAX 쪽 기존 등록자 9명의 워크스페이스를 RA home_workspace_slug 로 옮길지도 이 답을 본 뒤 정한다.



#### IR-43 · Report Archive PPTX 가져오기 완료 응답에 빠진 요소를 종류별로 · 그림 블록 이름

`P2` · 보낸 기록 없음



- **문제:** 완료 알림은 '변환하지 못한 요소 1건' 이지만 실제로 빠진 것은 셋(6쪽 차트 개체 · 8쪽 그림 채움 도형 · 9쪽 발표자 노트)이라 사람이 무엇이 빠졌는지 알 수 없다. 그림 블록 이름이 PPT 개체 이름('Picture 2')이다.

- **바꿀 것:** 빠진 요소를 종류별로 센다(차트 · 노트 · 그림 채움 · 연결선 · 글 없는 도형). 그림 블록 이름은 쪽 제목 + 순번으로 한다.

- **위치:** Report Archive PPTX 가져오기 완료 응답

- **확인:** 같은 시험 덱(imgtest-20261110.pptx) 가져오기 응답에 종류별 빠진 수가 실제와 맞고, 그림 블록 이름이 쪽 제목 + 순번이다.



#### IR-44 · Report Archive PPTX 가져오기의 그림 판독을 DocForge 에 맡기기

`P2` · 보낸 기록 없음



- **문제:** RA 가져오기는 그림을 파일로만 싣고 판독이 없어, 지식 DB · 검색 · 챗 어디에서도 그림 내용을 찾을 수 없다.

- **바꿀 것:** 그림 판독을 같은 모델 · 지시 · 캐시를 쓰는 DocForge 에 맡긴다.

- **위치:** Report Archive PPTX 가져오기

- **확인:** 가져온 보고서의 그림 블록에 판독 글이 붙는다.

- **참고:** HWAX 포털이 정밀 변환 결과를 앞에 두는 변경이 더 쉬운 대안이다. 그 변경이 HWAX 쪽에 들어오면 이 요청은 거둘 수 있다.



#### RAO-2 · 관계 셋의 끝 타입 defect 정의 또는 failure_mode 로 고치기

`P2` · 보낸 기록 없음



- **문제:** has_defect · occurs_at · caused_by 가 가리키는 defect 타입이 정의돼 있지 않다(끝이 빈 관계).

- **바꿀 것:** defect 를 정의하거나 관계 끝을 자체 불량 모드(failure_mode)로 고친다.

- **위치:** ReportArchive get_ontology 관계 정의

- **확인:** get_ontology → 관계 셋의 끝 타입이 정의돼 있음.



#### RAO-3 · 보고서 태그 축에 코어 과제 · 고장모드 · 부품

`P2` · 보낸 기록 없음



- **문제:** 축 태그가 1,788 중 440(24.6%)이고 모두 RA 자체 축이다. 코어 부품 이름으로 RA 부품 찾기 0건.

- **바꿀 것:** RAO-1 뒤 과제 · 고장모드 · 부품을 축으로 쓰게 하고 태그 제안 도구가 코어 key 를 후보로 낸다.

- **위치:** ReportArchive get_tagging_coverage · suggest_report_tags

- **확인:** 태그 제안에 코어 key 후보, 코어 축 태그 수가 0 보다 큼.

- **먼저:** RAO-1



#### RP-06 · /api/me/workspace 를 다시 고를 수 있게 · MCP/REST 로

`P2` · 보낸 기록 없음



- **문제:** 「이미 소속이 있으면 거절」 이라 다시 고를 수 없고 MCP · REST 로 부를 수 없다. 위임으로 옮기면 지금 선택 화면이 걷힌다.

- **바꿀 것:** MCP · REST 로 열고 다시 고를 수 있게 한다.

- **위치:** RA POST /api/me/workspace

- **확인:** 소속이 있는 사람이 위임 경로로 워크스페이스를 바꿀 수 있다.



#### RP-07 · X-Heax-Client 단위 재발급 회전

`P2` · 보낸 기록 없음



- **문제:** RA OpenAPI 450 연산이 X-Heax-* 를 읽지 않는다. client 를 가르지 않으면 게이트웨이 발급마다 브라우저 토큰이 죽을 수 있다.

- **바꿀 것:** 같은 (사용자, X-Heax-Client) 재발급은 직전 토큰만 회수하고 다른 client 토큰은 두기.

- **위치:** RA /api/auth/sso

- **확인:** 게이트웨이 발급 뒤에도 같은 사람의 브라우저 토큰이 산다.



#### RP-08 · SSO 토큰 수명 단축(12시간 권장)

`P2` · 보낸 기록 없음



- **문제:** RA 기본 90일, 실측 expires_in 172800(48시간). ste 는 43200초.

- **바꿀 것:** 90일보다 짧게, 12시간 권장.

- **위치:** RA /api/auth/sso

- **확인:** 발급 응답 expires_in ≤ 43200.

- **먼저:** RP-02 와 함께



#### RP-09 · 발급 창구 성질 확인(시크릿 · 비교 · 기록)

`P2` · 보낸 기록 없음



- **문제:** /api/auth/sso/verify 는 204, 주소 제한은 걸려 있으나(프록시 경유 403) 시크릿 길이 · 비교 · 로그 · 빈 시크릿 404 · 발급 기록은 확인 못 했다.

- **바꿀 것:** 32바이트 이상 랜덤 시크릿, hmac.compare_digest, 로그 미기록, 빈 시크릿 404, 발급 기록(이메일 · client · 시각).

- **위치:** RA /api/auth/sso

- **확인:** RA 가 항목별 지켜짐을 답한다.



#### RP-10 · 기존 보고서 소유자 백필

`P2` · 보낸 기록 없음



- **문제:** 위임으로 옮겨도 기존 보고서는 백필 전까지 서비스 계정 명의다.

- **바꿀 것:** 실제 사람으로 백필하거나 못 하면 알린다.

- **위치:** RA 에 이미 있는 보고서의 owner(지금 서비스 계정 명의)

- **확인:** 기존 보고서 owner 가 사람으로 보인다.



#### RP-11 · ask_ontology 시간 상한

`P2` · 보낸 기록 없음



- **문제:** 10-27 ask_ontology(max_hops 3)가 클라이언트 시간 초과였고 게이트웨이 감사에도 없다.

- **바꿀 것:** 시간 상한을 두고 오래 걸리면 진행 응답이나 부분 결과를 돌려준다.

- **위치:** RA MCP ask_ontology

- **확인:** 시간 상한 안에 답이나 진행 응답이 온다.

- **참고:** HWAX 에이전트 쪽은 코어 질문을 RA 로 보내지 않게 따로 고친다.



#### RP-16 · (질문) PPTX 가져오기 상한 · 오류 문구

`P2` · 보낸 기록 없음



- **문제:** 26.2 MB 통과 · 27.5 MB 거절('파일이 너무 큽니다'), 116쪽 · 45 MB 는 400. OpenAPI · 화면에 상한 없음.

- **바꿀 것:** 크기 · 쪽 수 · 그림 수 상한과 400 문구 목록을 알리고 OpenAPI · 화면에 적는다.

- **위치:** POST /api/imports/pptx

- **확인:** 약 27 MB 파일을 보낼 때 보내기 전에 상한 안내가 뜨거나, 거절이면 RA 가 준 사유가 화면에 그대로 보인다.

- **참고:** 포털은 'Report Archive로' 목적지에 크기 상한(기본 25 MB)을 두어 미리 막고, RA 가 준 거절 사유(detail)를 화면에 보인다.



#### RP-12 · get_guide 'write' 파일 위젯 문장 어긋남 · 크기 문구

`P3` · 보낸 기록 없음



- **문제:** '파일 위젯은 비워 둔다' 와 'file_id 를 위젯에 넣는다' 가 어긋나고 '크기 제약 없음' 은 25 MB 기본 한도와 맞지 않을 수 있다.

- **바꿀 것:** 문장을 고치고 경로별 실제 상한을 가이드와 prepare_upload 응답에 싣는다.

- **위치:** get_guide('write') · prepare_upload 설명

- **확인:** 가이드 문장이 하나로 맞고 상한 바이트가 보인다.

- **먼저:** RP-16



#### RP-13 · list_folders 가 부서 이름으로 게시판을 못 찾음

`P3` · 보낸 기록 없음



- **문제:** 이름으로 부르면 '게시판을 찾을 수 없습니다', slug 로는 folders 4개.

- **바꿀 것:** 이름을 정규화해 찾고 후보를 주거나, 도움말에서 '부서 이름' 을 뺀다.

- **위치:** reportarchive_list_folders

- **확인:** 부서 이름으로 부르면 그 게시판 폴더가 나온다.



#### RP-14 · 헤더 없는 호출의 폴백 규칙을 OpenAPI 에

`P3` · 보낸 기록 없음



- **문제:** OpenAPI(450 연산 · 512,003 bytes)에 폴백 규칙 문장 0건.

- **바꿀 것:** RP-15 답을 OpenAPI description 에 적는다.

- **위치:** RA OpenAPI

- **확인:** OpenAPI description 에 헤더 없는 호출의 워크스페이스 폴백 규칙 문장이 있다(지금 0건).

- **먼저:** RP-15



#### RP-17 · (질문) /api/me 응답 모양

`P3` · 보낸 기록 없음



- **문제:** OpenAPI 의 모든 200 이 schema {} 다. 포털이 쓰는 home_workspace_slug · memberships[] 의 workspace_slug · kind · name · role · {success, data:{…}} 봉투는 2026-09-09 실측 기록에서만 나온 것이다.

- **바꿀 것:** 응답 모델 선언.

- **위치:** /api/me

- **확인:** OpenAPI 의 /api/me 200 응답에 이 칸들을 담은 응답 모델이 선언돼 있다.



#### RP-18 · (질문) MCP 서버가 X-Workspace-Slug 를 REST 로 어떻게 내리나

`P3` · 보낸 기록 없음



- **문제:** 게이트웨이는 extra_headers 로 넣을 뿐이고 RA MCP 소스가 박스에 없다.

- **바꿀 것:** 답.

- **위치:** RA MCP 서버 — 게이트웨이가 extra_headers 로 넣은 X-Workspace-Slug 를 REST 호출로 넘기는 곳

- **확인:** RA MCP 서버가 X-Workspace-Slug 를 REST 로 어떻게 내려보내는지 RA 가 답한다.



#### RP-19 · (질문) 추출 그림 workspace_slug 꼴이 원본과 다름

`P3` · 보낸 기록 없음



- **문제:** 원본은 personal-* 꼴, 추출 그림 두 장은 UUID 꼴(owner 같음). 위젯 권한이 어긋날 수 있다(추정).

- **바꿀 것:** 답.

- **위치:** 추출한 그림 파일의 workspace_slug 배정(원본 파일과 견줌)

- **확인:** 원본과 추출 그림이 같은 워크스페이스인지, 다르면 위젯에 붙일 때 권한이 어긋나지 않는지 RA 가 답한다.



#### RP-20 · (질문) has_defect 끝 타입 defect 가 타입 목록에 없음

`P3` · 보낸 기록 없음



- **문제:** list_object_types 는 project · failure_mode · part 뿐.

- **바꿀 것:** 의도인지 답.

- **위치:** list_object_types · get_ontology(관계 has_defect 의 끝 타입)

- **확인:** has_defect 의 끝 타입 defect 가 타입 목록에 없는 것이 의도인지 RA 가 답한다.

- **참고:** 코어 쪽 후속은 같은 문서의 RAO-2(defect 를 정의하거나 관계 끝을 자체 불량 모드 failure_mode 로 고치기)가 다룬다.



### 3-2. STE · 연계 브리지 (ste 세션) — 21건



시험 입력의 과제 이름은 적지 않고 「과제 A」 로 썼다 — 11-21 요청서의 과제 A(BG-1 · ST-8 에 쓴 창 유리가 든 과제, 잡 da723f9ba623 에 올린 STEP)와 같다. 실제 과제 이름이 더 필요하면 운영 쪽이 따로 넘긴다.



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| BG-1 | 레지스트리 fetch 가 운영 StepForge 에서 그 파트만 받게 | P0 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| BG-2 | part-study outline 얇은 판 통과 · outline_source=stepforge | P0 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-1 | (STE) 결로 개구부를 구멍 영역 패치로 | P0 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-2 | (STE) 개구부 미매칭 · 출구 없음이면 잡 실패 | P0 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| BG-6 | part-study STL 단위 m 출력(--units m) | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| PA-02 | STE 결과 d3hsp 를 클라이언트 한 대가 처음부터 되풀이해 받음 | P1 | 보낸 기록 없음 |

| ST-4 | (STE) 요청 단계 실패 = 잡 실패 | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-5 | (STE) ste_job_summary — 정리된 수치 | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-6 | (STE) 판정 기준 criteria · verdict | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-7 | (STE) reddish_case_build — 검사를 거친 case.yaml · placeholders | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-8 | (STE) 변별 경계 h 기본표 | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-9 | (STE) 결로 후처리 단위 · 자릿수 | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-10 [11-21] | (STE) condensation_scenario_build · 업로드에 시나리오 넣기 | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-11 [11-21] | (STE) part-study 단계 고르기 stages | P1 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| PA-15 | (질문) 큰 결과 내려받기가 upstream prematurely closed 로 끊김 | P2 | 보낸 기록 없음 |

| ST-12 [11-21] | (STE) part-study-registry request.json 스키마 노출 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-13 [11-21] | (STE) 레디쉬 결과 수치 칸 이름 · 단위 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-14 [11-21] | (STE) 잡 목록 mine · 시야 표기 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-15 [11-21] | (STE) 레디쉬 environment 절과 D · S 온도 의존 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-16 [11-21] | (STE) get_job_file 앞부분 · 범위 읽기 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| ST-17 [11-21] | (STE) 장시간 결로 모드(준정상 · 들숨날숨) | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |



#### BG-1 · 레지스트리 fetch 가 운영 StepForge 에서 그 파트만 받게

`P0` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** fetch_part.py 가 기본 주소(잡 노드 자신)로 가서 11-17 잡 301e2c766da6 이 Connection refused 로 끝났다. 요청서 part 는 보고서 이름일 뿐이라 과제 전체를 받는다. 실행기에도 주소 · 토큰 설정이 없다(11-21 읽기).

- **바꿀 것:** 잡 환경에 주입된 주소 · 토큰을 쓴다. 요청서 part 로 StepForge export_part_step 을 불러 그 파트만 받는다. 실패하면 원인을 연결 · 인증 · 과제 없음 · 파트 없음으로 나눠 적는다.

- **위치:** KooSolverContainer ste_integration/bridge fetch_part.py · fetch.json

- **확인:** 과제 A · part=창 유리로 레지스트리 잡을 내면 fetch 가 ok 이고, 받은 파일이 그 파트 하나(솔리드 1)여야 한다. 없는 파트 이름을 넣으면 fetch fail 과 '파트 없음' 이 나와야 한다.

- **선례:** BR-R1 · BR-R2

- **먼저:** ST-3 — 레지스트리 잡 환경에 운영 StepForge 주소를 넣는 일(ste 쪽). 11-23 ste 스테이징 859a02d 에는 주소를 넣는 길만 들어갔다. STE 운영 노드의 /opt/ste/.env 에 넣을 STE_STEPFORGE_BASE 한 줄은 사람이 넣고, 토큰은 넣지 않는다.

- **받은 곳 · 상태:** KooSolverContainer 2b1946f(11-22, dev, 미배포) — 주소를 짐작하지 않고 실패를 갈라 fetch.json 에 적는다. 11-18 브리지 답으로 BR-R1 을 고쳐 읽었다(STEPFORGE_BASE 는 이미 읽고, 기본 폴백 주소가 문제다). 아직 안 된 것: 배포, 그 파트만 받기(export_part_step 호출) 확인, ST-3 주소를 넣은 레지스트리 잡으로 확인.

- **참고:** 실패 가름은 dev 에 반영됐고 아직 배포 전이다. 그 파트만 받기(export_part_step 호출)가 들어갔는지는 기록이 없다.



#### BG-2 · part-study outline 얇은 판 통과 · outline_source=stepforge

`P0` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** da723f9ba623(창 유리 0.45 mm 판)은 '닫힌 외곽을 찾지 못했다' 로 끝났다(두께 0.4938 · 종횡 153.7). 007f6a2250e4(후면 유리 0.63 mm 판)은 '외곽이 bbox 단면의 6.7 % — 하한 25 %' 로 끝났다(윤곽 2). StepForge part_outline_2d 는 같은 창 유리를 외곽 1 · 구멍 0 · 75.856×161.368 mm 로 읽는다. part-study 에는 outline_source 인자가 없다.

- **바꿀 것:** 두 판 모두 outline 을 통과시킨다. outline_source=stepforge 로 part_outline_2d JSON 을 그대로 받아 메시를 만드는 길도 연다.

- **위치:** KooSolverContainer 브리지 outline 단계 · part-study params outline_source

- **확인:** 두 잡을 같은 입력으로 다시 낸다. outline ok 이고, 창 유리 상자 약 75.86 × 161.37 mm · 구멍 0, 후면 유리 외곽 1 + 구멍 1 이 나온 뒤 다음 단계로 넘어가야 한다.

- **선례:** BR-R3 · BR-R4

- **받은 곳 · 상태:** KooSolverContainer 0296fab · 41c2cc9(dev, 미배포) — 합성 판으로 재현해 고쳤다(단면 끝점 잇기를 허용오차 사다리로). 아직 안 된 것: 운영 두 판(da723f9ba623 · 007f6a2250e4)이 이 원인인지 운영 박스 진단기 숫자로 가리기(숫자만 내는 진단 절차를 아직 받지 못했다), outline_source=stepforge(들어갔는지 기록 없음), 배포.

- **참고:** 운영 두 판이 이 원인인지는 진단기 숫자로 가려야 한다. 진단기를 운영 박스에서 돌리는 몫이 남았다. outline_source=stepforge 가 들어갔는지는 기록으로 가리지 못했다.



#### ST-1 · (STE) 결로 개구부를 구멍 영역 패치로

`P0` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 잡 1ddbdd7cd769 에서 입구를 반경 4 mm(약 50 mm²)로 줬다. 그런데 fluxes_at_openings 머리에 patch inlet · Faces 235 · Area 4.08e-4 m² 가 찍혔다. 아래 면 전체(408 mm²)가 입구가 된 것이고, 11-17 과 같다.

- **바꿀 것:** openings[{center, radius 또는 area_m2, normal?}] 이면 그 원(또는 cavity_openings 영역) 안의 면만 잘라 새 패치로 만든다. 위치 · 연결성으로 고르고, 패치 넓이 · 면 수를 결과에 남긴다.

- **위치:** STE 결로 앱 래퍼 auto_patch_stl.py(법선 30° 묶음 + 묶음 중심 거리 매칭)

- **확인:** 같은 입력에서 inlet 넓이가 약 50 mm² 이고, 결과에 넓이 · 면 수가 있어야 한다.

- **선례:** S-1

- **먼저:** ST-2 와 같은 원인

- **받은 곳 · 상태:** KooSolverContainer 6b54715 · 843e22d(11-22, dev, 미배포) — 개구부 원 안의 면만 패치로 만든다(합성 상자 반경 4 mm → 50.24 mm², 옛 꼴은 "patch": "face"). 아직 안 된 것: 운영 반입(ste 자동 교체와 그쪽 사용자 확인 뒤)과, 1ddbdd7cd769 와 같은 입력으로 다시 확인.

- **참고:** dev 에 반영됐고 아직 배포 전이다. 운영 반입은 ste 자동 교체와 그쪽 사용자 확인 뒤다. 1ddbdd7cd769 와 같은 입력으로 다시 확인하는 것은 운영 박스에서 한다.



#### ST-2 · (STE) 개구부 미매칭 · 출구 없음이면 잡 실패

`P0` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 같은 잡에서 출구를 일부러 24 mm 빗나가게 했다. auto_mapping 에 outlet 이 없는데 로그는 아무 말이 없고, 잡은 COMPLETED/0 이다. 닫힌 상자를 미는 해석이 되어 입구 sum(phi)가 −2.3157e-4 에서 −5.4695e-4 로 136 % 커졌다. 그런데도 보고서는 내부 15 → 60.8 °C 를 'ΔT +45.84 K 잠열' 로, 응축률 6.59 mg/s(11-17 기준 잡 0.27 mg/s 의 24배)를 정상 결과로 냈다.

- **바꿀 것:** 다음 가운데 하나라도 맞으면 결로 단계 fail + 잡 FAILED + failed_stage 'condensation' + reason_code 를 낸다. 개구부 미부착 → opening_unmatched, 입구 · 출구 중 하나 없음 → no_outlet, 입출 유량 차가 한계 초과 → flux_imbalance.

- **위치:** STE 결로 앱 래퍼(개구부 매칭 · 종료 규칙)

- **확인:** 1ddbdd7cd769 와 같은 입력이 FAILED · no_outlet(또는 opening_unmatched)으로 끝나야 한다.

- **선례:** S-2

- **받은 곳 · 상태:** KooSolverContainer 85256df(11-22, dev, 미배포) — 사유 opening_unmatched · no_outlet · no_inlet · flux_imbalance(기본 50 %) 이면 결로 단계 fail · 잡 FAILED. 11-23 판(ste 스테이징 859a02d · KooSolverContainer 72e8571)의 확인 항목에도 「mm 로 적은 개구부는 메시 전에 opening_unmatched 로 멈춘다」 가 있다. 아직 안 된 것: 운영 반입과, 1ddbdd7cd769 와 같은 입력으로 FAILED · no_outlet 확인.

- **참고:** flux_imbalance 기본 한계는 50 % 로 들어갔다(11-17 요청 예시는 5 %). 배포 전이다.



#### BG-6 · part-study STL 단위 m 출력(--units m)

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** part-study 인자표에 STL 단위 칸이 없다. 브리지 STL 은 mm 이고 결로 쪽에서 줄인다. 그래서 시나리오 개구부 좌표(m)와 단위가 어긋나기 쉽다.

- **바꿀 것:** STL 을 m 로 내는 선택(--units m)을 연다.

- **위치:** KooSolverContainer 브리지 stl 단계 · stl.json units

- **확인:** 단위 m 로 낸 잡의 STL 상자가 m 값이어야 한다.

- **선례:** B-1 [11-17] · S-6

- **먼저:** ST-11 [11-21] 과 짝

- **받은 곳 · 상태:** 브리지가 받았고 Phase 7 차례다(ST-2 · ST-1 · BG-1 · BG-2 먼저). 지었다는 기록은 아직 없다.

- **참고:** dev 가 찾은 1000배 결함(part-study 레디쉬가 mm 를 m 로 읽음)과 같은 단위 계열이다.



#### PA-02 · STE 결과 d3hsp 를 클라이언트 한 대가 처음부터 되풀이해 받음

`P1` · 보낸 기록 없음



- **문제:** 10-25 20:3x 까지 /ste/api/jobs/<id>/result/file/d3hsp 1,873건 · 5,350.7 GB, 모두 Go-http-client 한 대. 10-23 3,975 GB · 10-24 5,740 GB, nginx 오류가 하루 수백 건.

- **바꿀 것:** 그 클라이언트 담당을 찾고 끝난 잡만, Range · If-Modified-Since · 크기 비교로 이어 받게 한다.

- **위치:** /ste/api/jobs/<id>/result/file/<파일>

- **확인:** 같은 d3hsp 를 처음부터 다시 받는 줄이 사라지고 하루 TB 단위 되풀이가 없다.

- **참고:** rate limit 을 걸지는 HWAX 포털 쪽에서 정한다. 그 클라이언트의 주소와 기록 시각은 이 글에 싣지 않고 운영 쪽이 따로 넘긴다.



#### ST-4 · (STE) 요청 단계 실패 = 잡 실패

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** da723f9ba623(outline fail · reddish skip)과 007f6a2250e4(outline fail · cond=1 인데 condensation skip)가 둘 다 COMPLETED · exit 0 으로 끝났다('성공 2 · 실패 1 · 건너뜀 3').

- **바꿀 것:** 요청한 단계 가운데 fail 이 있으면 잡 FAILED + failed_stage 를 낸다. skip 은 사유 코드로 남긴다.

- **위치:** ste 코어 — result/stage.json 읽기 · 잡 상태

- **확인:** 두 잡과 같은 입력이 FAILED · failed_stage 'outline' 으로 끝나야 한다.

- **선례:** ST-R2

- **받은 곳 · 상태:** ste 로컬 main 에 지었다(ST-5 틀 · ST-12 · ST-14 · ST-16 과 함께). 운영 판은 아직 1e53260 그대로다. 아직 안 된 것: 운영 반입과, 두 잡과 같은 입력으로 FAILED · failed_stage 'outline' 확인.

- **참고:** 지었고 아직 운영 전이다(스테이징 자동 교체 대기).



#### ST-5 · (STE) ste_job_summary — 정리된 수치

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** STE 앱 도구 12개 가운데 정리된 수치를 주는 도구가 없다. 레디쉬는 results.json 의 V2 · V3 가 value_html 문자열('37.76 mm')뿐이다. 결로는 report.txt 문자열과 .dat 머리 주석에서 숫자를 뽑아야 한다.

- **바꿀 것:** job_id → {app, state, failed_stage, stages[], validation 또는 openings, metrics(앱별), verdict, report_url, case_digest}. 레디쉬 · 결로가 같은 이름을 쓴다.

- **위치:** ste MCP ste_job_summary(새 도구)

- **확인:** 608a24a0c924 → V2 value 37.76 · reference 34.97 · unit mm · pass null · reason_code 가 나온다. 1ddbdd7cd769 → 입구 패치 넓이 · 유량 · 응축률이 숫자 칸으로 나온다.

- **선례:** ST-R3 · S-3

- **받은 곳 · 상태:** ste 로컬 main 에 틀을 지었다. report_url 대신 경로 · 크기 · job_url 을 싣는다(저장형 XSS 를 피하려고). 운영 전이다. 앱별 metrics 채우기는 브리지 몫으로 남았다.

- **참고:** 앱별 metrics 를 채우는 일은 브리지 몫이다.



#### ST-6 · (STE) 판정 기준 criteria · verdict

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 레디쉬 608a24a0c924 는 V1 true · V2 pass null(짧은 축 반폭 37.9 < 3δ, δ 27.57)이고, verdict · reason_code · criteria 칸이 없다. 결로 report.txt 의 '결로 발생 조건' 문장은 출구 없는 잘못된 해석에도 그대로 나온다.

- **바꿀 것:** case.yaml · scenario.json 에 criteria 를 두고, 결과에 verdict {pass, metric, value, limit, reason_code} 를 낸다. V2 가 null 이면 half_width_lt_3delta 를 낸다.

- **위치:** STE 레디쉬 · 결로 앱 래퍼 · ste_job_summary verdict

- **확인:** criteria 를 넣은 레디쉬 · 결로 잡에서 verdict 가 나와야 한다.

- **선례:** ST-R4 · S-7

- **먼저:** ST-5

- **받은 곳 · 상태:** 브리지 dev 에 들어갔다(11-22, 미배포): criteria [{metric, limit, patch?}] → ste_job_summary 의 verdict, 결로 지표 넷, 레디쉬는 지금 penetration_final_mm 하나. 11-23 판 KooSolverContainer 72e8571 에 「레디쉬 판정」 이 들었다. 그 판의 확인 항목: case.yaml 에 criteria 를 주면 잡 요약에 verdict 가 실리고, 휴대폰 크기 판의 validation.V2 는 pass null · half_width_lt_3delta 다. 아직 안 된 것: 레디쉬 지표 더하기(붉어짐 면적비 · 조사 창 안 P 평균)와 운영 반입.

- **참고:** 레디쉬 지표 추가는 아직 짓는 중이다. 붉어짐 = 열화 분율 P/(P+P_ox) 로 사용자가 11-22 에 정했다.



#### ST-7 · (STE) reddish_case_build — 검사를 거친 case.yaml · placeholders

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 이 도구가 없다. case 템플릿은 11-17 잡 db7bbee75f4f 에서 손으로 받았다. 608a24a0c924 는 형상만 바꾸고 나머지는 템플릿 그대로였다(적층 5층 · 화학 · h · UV 창 17.4~58.4 × 43.2~118.2). 축 배정 · 원점 옮김도 사람이 했다.

- **바꿀 것:** geometry(part_outline_2d 출력 또는 파트 참조) · stack · chemistry 프리셋 · environment · uv_mask · edge_h 를 받아, 검사를 거친 case.yaml 과 placeholders 를 낸다.

- **위치:** STE 레디쉬 앱 래퍼 reddish_case_build(새 도구)

- **확인:** part_outline_2d 출력을 그대로 넣어 case.yaml 이 나오고, placeholders 에 남은 템플릿 칸이 적혀야 한다.

- **선례:** ST-R5

- **먼저:** SF-5(geometry 변환은 StepForge) — StepForge 쪽은 끝났다(11-22 합의).

- **받은 곳 · 상태:** 11-22 합의(SF-5 ↔ ST-7): geometry 절은 StepForge 가 바꾸고, ST-7 은 그 절을 손대지 않고 실어 검사 · 메시 크기 · placeholders 만 맡는다. 11-23 판 KooSolverContainer 72e8571 에 「StepForge 외곽으로 케이스 짓기」 가 들었다. 그 판의 확인 항목: 레디쉬에 outline.json · uv.json · edge_h.json 을 함께 올리면 지은 케이스로 돌고 요약에 placeholders · build_warnings 가 실린다. 아직 안 된 것: 운영 반입.

- **참고:** 11-22 합의에 따라 geometry 절은 StepForge 가 바꾼다. ST-7 은 그 절을 손대지 않고 싣고, 검사 · 메시 크기 · placeholders 만 맡는다.



#### ST-8 · (STE) 변별 경계 h 기본표

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 이 도구가 없다. StepForge 변별 이웃 정보(tied · clearance · gap)는 생겼지만 접촉 넓이가 0 이다(SF-2). corner 변 묶음을 left/right/top/bottom 에 넣는 규칙도 없다.

- **바꿀 것:** 관계 + 실링 종류 → h 기본값을 정하고, StepForge 변별 정보와 합쳐 edge_groups 를 만든다.

- **위치:** STE 레디쉬 앱 래퍼

- **확인:** 과제 A 창 유리 외곽으로 edge_groups 4묶음과 h 값이 나와야 한다.

- **선례:** ST-R6

- **먼저:** SF-2 · SF-5 — 둘 다 StepForge 쪽은 끝났다. SF-2 의 접촉 넓이 0 은 참값으로 보인다.

- **받은 곳 · 상태:** SF-2 의 ST-8 쪽 물음은 브리지에 전했고, 브리지 Phase 7 차례다. 레디쉬에 edge_h.json 을 올리는 입력 길은 11-23 판(KooSolverContainer 72e8571)에 생겼다. 아직 안 된 것: h 기본표(관계 + 실링 종류 → h) — 지었다는 기록이 없다.

- **참고:** StepForge reddish_geometry 가 이미 edge_groups 넷을 낸다(StepForge 쪽 답 — 11-23 판의 레디쉬 꼴 외곽 · 변 묶음). 남는 것은 h 기본표다.



#### ST-9 · (STE) 결로 후처리 단위 · 자릿수

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 1ddbdd7cd769 보고서의 '부피유량 입구 0.547 L/s' 는 sum(phi) 5.4695e-4(질량유량)와 같은 값이다. 'Volume : 0.000 m³', '누적 응축량 0.001 g' 으로 찍힌다. 로그는 'OK (cells: unknown)' 인데 보고서 안에는 '과포화 셀 0/23500' 이 있다.

- **바꿀 것:** phi 를 질량유량으로 읽고, 부피유량은 해석 밀도로 나눈다. 부피는 cm³, 응축량은 mg 로도 찍는다. 로그에 셀 수를 남긴다.

- **위치:** STE 결로 후처리 스크립트

- **확인:** 같은 잡을 다시 처리하면 부피유량이 sum(phi) 와 달라야 하고, 부피 · 응축량이 0 이 아닌 자릿수로 나와야 한다.

- **선례:** S-4(11-17 추정: 부피유량 +13.5 %, 질량유량 +20 % 부풂)

- **받은 곳 · 상태:** 11-21 요청서로 앱 래퍼 · 해석기 스크립트 몫을 브리지에 보냈다. 지었다는 기록은 아직 없다.



#### ST-10 [11-21] · (STE) condensation_scenario_build · 업로드에 시나리오 넣기

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 007f6a2250e4 의 condensation 단계가 'scenario.json 을 올리지 않아 건너뜀' 으로 skip 됐다. artifact_to_ste_upload 는 StepForge 산출물만 옮기고, submit_job 은 files 와 upload_id 를 같이 받지 못한다. 그래서 StepForge STEP 업로드와 시나리오를 한 잡에 줄 MCP 길이 없다.

- **바꿀 것:** 검사를 거친 scenario.json + placeholders 를 낸다. 그리고 upload_id 에 scenario.json 을 더하거나, submit_job 이 files 와 upload_id 를 함께 받게 한다.

- **위치:** ste submit_job · 브리지 condensation_scenario_build

- **확인:** part-study(cond 1)를 업로드 + 시나리오로 내면 condensation 단계가 skip 되지 않아야 한다.

- **선례:** S-5

- **받은 곳 · 상태:** ste 47ed289 · 23f3245(로컬 main · 스테이징) — submit_job 이 files 와 upload_id 를 함께 받는다(같은 이름은 400). 스테이징에서 REST · MCP 로 한 잡씩 내 결로 단계 ok 를 확인했다. 11-23 판의 확인 항목: 결로 check_only=1 이 검사를 거친 시나리오 · placeholders 로 끝난다. 아직 안 된 것: 운영 반입(그쪽 사용자 확인 뒤)과 브리지 condensation_scenario_build(Phase 7).

- **참고:** submit_job 쪽 길은 스테이징에서 REST · MCP 로 한 잡씩 내 결로 단계 ok 를 확인했다. 시나리오 빌더 도구는 브리지 Phase 7 이다. 둘 다 운영 전이다.



#### ST-11 [11-21] · (STE) part-study 단계 고르기 stages

`P1` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** get_app_schema(part-study) 인자 13개(plane ~ ncpu)에 단계 칸이 없다. 결로만 보려 해도 outline · reddish 가 같이 돈다.

- **바꿀 것:** stages 로 돌릴 단계를 고른다.

- **위치:** part-study · part-study-registry params stages(ste 선언) · 브리지 단계 고르기

- **확인:** stages 를 글자 'stl,condensation' 으로 낸 잡의 stage.json 에 outline · reddish 가 not_requested 로 남아야 한다.

- **선례:** S-6

- **먼저:** BG-6 과 짝

- **받은 곳 · 상태:** 브리지 dev 에 part-study stages 가 들어갔다(11-22, 미배포). 제출 파라미터 선언은 ste ce3c864(로컬)이고, 제출 파라미터는 글자 하나다(배열은 400 — ste 783e7e7). 11-23 ste 스테이징 859a02d 에 part-study stages 설명이 들었다. 그 판의 확인 항목: stages "stl,condensation" 이 외곽 · 레디쉬를 not_requested 로 건너뛴다. 아직 안 된 것: 운영 반입.

- **참고:** 주의: 요청서의 배열 꼴 ["stl","condensation"] 은 제출 때 400 이다(잡이 안 생긴다). 글자 하나로 준다. 배열은 part-study-registry 의 request.json 안에서만 쓴다. part-study get_app_schema 에는 params 설명 칸이 없어 쓸 낱말이 보이지 않는다.



#### PA-15 · (질문) 큰 결과 내려받기가 upstream prematurely closed 로 끊김

`P2` · 보낸 기록 없음



- **문제:** 10-23 결과 파일 하나가 'upstream prematurely closed connection while reading upstream' 으로 끊겼다.

- **바꿀 것:** 끊김이 ste 쪽(터널 · 서버)인지 봐 달라.

- **위치:** /ste/api/jobs/<id>/result/file/<파일>

- **확인:** 끊김이 ste 쪽(터널 · 서버)인지 답을 받는다.

- **참고:** 포털 쪽 답은 nginx 시간 한도 탓이 아니라는 것이다. nginx 읽기 시한에 걸리면 'upstream timed out … while reading upstream' 이 남는다. 받은 문구는 위층(ste 서버 · 터널)이 본문을 다 보내기 전에 연결을 먼저 닫았다는 뜻이다. PA-02 의 끊긴 전송과도 같은 뿌리일 수 있다.



#### ST-12 [11-21] · (STE) part-study-registry request.json 스키마 노출

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** get_app_schema(part-study-registry)가 params 13 · inputs *.json 만 준다. request.json 키와 part 의 뜻(보고서 이름일 뿐)이 없다.

- **바꿀 것:** 요청서 키 · 뜻 · part 설명을 스키마에 싣는다.

- **위치:** ste get_app_schema(part-study-registry)

- **확인:** 스키마만 보고 request.json 을 쓸 수 있어야 한다.

- **선례:** ST-R7

- **받은 곳 · 상태:** ste 로컬 main 에 지었다. 운영 전이다(운영 판은 1e53260 그대로).



#### ST-13 [11-21] · (STE) 레디쉬 결과 수치 칸 이름 · 단위

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 608a24a0c924 results.json(15,759 B)에 config.time.total_days 864000.0 · output_interval_days 43200.0 이 있다(일 칸에 초 값). geometry width_mm 0.0759 · corner_radius_mm 0.005835 · stackup thickness_um 7.5e-05 도 있다(mm/µm 칸에 m 값). V2 · V3 는 문자열뿐이다.

- **바꿀 것:** 칸 이름과 단위를 맞추고, V2 · V3 에 value_mm · reference_mm 숫자 칸을 둔다.

- **위치:** STE 레디쉬 앱 results.json

- **확인:** 같은 case 로 다시 내면 total_days 10, width_mm 75.856 꼴로 나와야 한다.

- **선례:** ST-R8

- **받은 곳 · 상태:** 11-21 요청서로 브리지 몫(레디쉬 앱 results.json)을 보냈다. 지었다는 기록은 아직 없다.

- **참고:** dev 가 따로 찾은 결함이 있다. part-study 레디쉬 경로가 mm 좌표를 m 로 읽어 1000배 판을 풀었다(같은 케이스의 침투깊이 0 mm, 좌표만 줄이면 35.49 mm, 기준 34.97). 운영의 part-study reddish ok 잡 수치는 쓰지 않는다.



#### ST-14 [11-21] · (STE) 잡 목록 mine · 시야 표기

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** ste_list_jobs 에 owner · mine 칸이 없다. total 944 · RUNNING 7 로, 전체(관리자 시야)가 보이는지 호출자 잡만 보이는지가 응답에 없다.

- **바꿀 것:** mine(기본 true) 칸을 두고, 시야를 응답에 적는다.

- **위치:** ste MCP ste_list_jobs

- **확인:** 기본 호출에 내 잡만 나오고, 시야 표기가 있어야 한다.

- **선례:** ST-R9 · PT-R4

- **받은 곳 · 상태:** ste 로컬 main 에 지었다. 운영 전이다. owner 칸은 싣지 않고 mine 만 둔다.

- **참고:** 제출자 메일 · owner_id 는 MCP 출력에서 이미 뺐다. 그래서 owner 칸은 싣지 않는다.



#### ST-15 [11-21] · (STE) 레디쉬 environment 절과 D · S 온도 의존

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 608a24a0c924 config 에 environment 키가 없다. 온도 · 습도를 넣을 칸이 없어 시험하지 못했다.

- **바꿀 것:** case 에 environment {temperature_C, rh} 와 D · S 의 온도 의존을 둔다.

- **위치:** STE 레디쉬 앱 case.yaml · 해석 스크립트

- **확인:** environment 를 바꾼 두 잡의 결과가 달라지고, 결과 메아리에 그 값이 남아야 한다.

- **선례:** ST-R10

- **먼저:** BG-5(시험 조건 → 환경 값) — HWAX 쪽 몫이고 게이트웨이 reliability_test_conditions 로 들어갔다.

- **받은 곳 · 상태:** 짓기는 브리지 몫이다(11-22 사용자 결정: 습도에 따른 산소분압 + 층별 온도 의존, 활성화 에너지는 입력, 새 해석 스크립트와 브리지 SIF 는 스테이징 먼저). 11-23 판 KooSolverContainer 72e8571 에 「환경 절」 이 들었다. 그 판의 확인 항목: case.yaml 에 environment 를 주면 잡 요약에 environment 가 실린다. 아직 안 된 것: 운영 반입.

- **참고:** 짓는 중이다.



#### ST-16 [11-21] · (STE) get_job_file 앞부분 · 범위 읽기

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 인자가 job_id · path · tail_lines · max_bytes 뿐이라 꼬리만 읽힌다.

- **바꿀 것:** head_lines 또는 offset 을 둔다.

- **위치:** ste MCP get_job_file

- **확인:** 결로 잡의 controlDict 앞쪽을 읽을 수 있어야 한다.

- **선례:** S-8

- **받은 곳 · 상태:** ste 로컬 main 에 지었다. 운영 전이다.



#### ST-17 [11-21] · (STE) 장시간 결로 모드(준정상 · 들숨날숨)

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** get_app_schema(condensation) 인자가 ncpu · end_time · resolution 뿐이다(11-17 과 같다). 결로 시험은 시간 ~ 일 단위인데, 해석은 초 단위 비정상 흐름이다.

- **바꿀 것:** 시간 ~ 일 단위 시험에 맞는 준정상 · 들숨날숨 모드를 둔다.

- **위치:** STE condensation 앱

- **확인:** 시간 단위 end_time 의 잡이 한도 안에 끝나야 한다.

- **선례:** S-9

- **받은 곳 · 상태:** 11-21 요청서로 브리지 몫을 보냈다. 진행 기록은 아직 없다.



### 3-3. PCB체크리스트서버 — 19건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| RQ-12 | (질문) 13.8 MB 보드 제출 500 의 원인 | P1 | 보낸 기록 없음 |

| RQ-14 | (질문) 30초 한도가 있는가 | P1 | 보낸 기록 없음 |

| RQ-15 | (질문) 왜 이 보드만 실패하는가 | P1 | 보낸 기록 없음 |

| RQ-01 | (질문) 권한 · 용량 · 한도 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-04 | (질문) 로그인 없이 결과가 보이는 것이 의도인가 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-05 | (질문) Power Circuit dat 출처 | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-13 | (질문) 실패한 제출로 작업이 생겼는가 | P2 | 보낸 기록 없음 |

| RQ-16 | (질문) 언제 다시 보내도 되는가 | P2 | 보낸 기록 없음 |

| RR-01 | 응답 스키마 문서(보고서는 text/html) | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RR-02 | 체크리스트 · 규칙 목록 API | P2 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-02 | (질문) 메타 키 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-03 | (질문) 제출 응답 꼴 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-06 | (질문) API 바뀜 알림 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-08 | (질문) odb_check abnormal 읽는 법 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-09 | (질문) resolve-checklists 의 부작용 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-10 | (질문) 위반 그림 shots/*.svg 받는 길 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RQ-11 | (질문) 정식 이름 · '개발실 체크리스트' 써도 되는가 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RR-03 | 가벼운 상태 확인 경로 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |

| RR-04 | status=all 또는 여러 값 | P3 | 보낸 흔적 있음 · 끝난 흔적 없음 |



#### RQ-12 · (질문) 13.8 MB 보드 제출 500 의 원인

`P1` · 보낸 기록 없음



- **문제:** 같은 보드(ODB++ 원본 tgz 13,844,391 바이트 · sha256 앞 16자리 17686bbb7bc17036)가 약 30초 뒤 500 으로 네 번 실패했다. 1차 2026-11-06 22:39:45 → 22:40:16, 2차 11-07 06:42:44 → 06:43:14, 3차 11-09 17:03:26 → 17:03:56(셋 다 HWAX 중계), 4차 11-13 13:58:16 → 13:58:46(검증 서버 웹 화면 「검증 시작」)이다. 모두 KST 이고, 작업 id 는 받지 못했다. 0.5 MB 보드(514,611 바이트)는 11-13 16:51:44 에 HWAX 중계로 내 1초 만에 DONE 이 됐다.

- **바꿀 것:** 네 시각의 서버 기록에서 500 의 원인을 알려 달라. HWAX 쪽에서 고칠 것(meta 꼴 · 파일 · 칸 이름)이 있으면 무엇인지도. 보낸 meta 는 checklists ["hw"] · project {name, pcb_type "MAIN"} · flags {strategic true, layer1_is_top true} · submitter 꼴의 UTF-8 JSON 한 줄이고, 이력 61건 가운데 25건과 키 · 값 꼴이 같다.

- **위치:** 제출 API(POST /api/pcb/jobs · multipart/form-data 칸 file · meta, dat 는 싣지 않음)

- **확인:** 원인 답을 받고, 같은 보드가 DONE 이 된다.

- **참고:** 웹 화면도 실패하므로 중계 쪽 문제가 아닌 것으로 보인다(추정).



#### RQ-14 · (질문) 30초 한도가 있는가

`P1` · 보낸 기록 없음



- **문제:** 실패가 늘 약 30초(30.6 · 30.7 · 30.6 · 30.3초)에 난다. HWAX 쪽 제출 시간 한도는 120초라 이쪽에서 끊은 것이 아니다.

- **바꿀 것:** 요청 처리 · 앞단 프록시 · 내부 호출에 30초 한도가 있는지, 파일 크기와 관계가 있는지 답해 달라.

- **위치:** 제출 API(POST /api/pcb/jobs)의 요청 처리 · 앞단 프록시 · 서버 안 내부 호출

- **확인:** 30초 한도가 있는지, 있으면 그 값과 파일 크기와의 관계를 답으로 받는다. HWAX 중계는 그 값을 제출 크기 상한과 미리 보기 문구에 넣는다.

- **참고:** RQ-01 과 겹침.



#### RQ-15 · (질문) 왜 이 보드만 실패하는가

`P1` · 보낸 기록 없음



- **문제:** 웹 화면(11-13 08:51)과 HWAX 중계(11-13 16:51, 514,611 바이트)로 낸 다른 보드는 끝났는데, 이 보드(13,844,391 바이트)는 두 길(중계 · 웹 화면) 모두 500 이다.

- **바꿀 것:** 이 보드에서만 실패하는 까닭(크기 · 층 수 · 파일 안 구성)과 서버가 받을 수 있는 보드 조건을 답해 달라.

- **위치:** 제출 API(POST /api/pcb/jobs) · 검증 서버 웹 화면 「보드 검증 작업」

- **확인:** 답을 받는다.



#### RQ-01 · (질문) 권한 · 용량 · 한도

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 중계 MCP 가 얼마나 보내도 되는지 모른다.

- **바꿀 것:** 동시 · 하루 · 파일 크기 한도를 숫자로 알려 달라. 대기가 찼을 때 어떤 응답이 오는지, 지금도 운영 중인지도 알려 달라. HWAX 쪽 제안 값은 한 사람 동시 1건 · 하루 10건 · HWAX 전체 동시 2건이다.

- **위치:** 제출 API(POST /api/pcb/jobs) · 처리 묶음 용량(지금 primary 동시 4 · 대기 상한 32, precision 동시 1 · 대기 상한 8)

- **확인:** 한도 수치를 받는다.

- **받은 곳 · 상태:** 11-06 에 담당 팀이 HWAX 의 작업 제출을 허락했다. 동시 · 하루 · 파일 크기 한도 수치는 아직 받지 못했다. 그래서 HWAX 쪽은 아직 제안 값으로 돌린다.

- **참고:** RQ-14(30초 한도)와 함께 묻는 것이 좋다.



#### RQ-04 · (질문) 로그인 없이 결과가 보이는 것이 의도인가

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 로그인 없이 이력 · 결과 · 보고서가 보인다. 이력과 작업 상태에 제출자 값 · 서버 안 파일 경로 · 부품 라이브러리 파일 목록이 실린다.

- **바꿀 것:** 의도인지, 권한을 걸 계획인지 답해 달라. 좁힐 계획이 있으면 그때 HWAX 중계 서버가 쓸 읽기 방법(서비스 키 등)도 알려 달라.

- **위치:** GET /api/pcb/public/history · GET /api/pcb/jobs/{job_id} · GET /api/pcb/jobs/{job_id}/results · 보고서 셋(/report · /report/download · /report/filtered)

- **확인:** 답을 받는다.

- **받은 곳 · 상태:** 답을 아직 받지 못했다.

- **참고:** 보안 관련이라 P2.



#### RQ-05 · (질문) Power Circuit dat 출처

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** Power Circuit 점검에 쓰는 dat 를 어디서 받는지 모른다. 건너뜀 사유는 「요구 입력(dat) 없음」 2건뿐이고, HWAX 의 ODB 허브에는 dat 를 내는 경로가 없다.

- **바꿀 것:** 출처(설계 도구에서 뽑는지, 다른 시스템에 있는지, ODB++ 원본과 함께 오는지)와 넣는 방법을 알려 달라.

- **위치:** 제출 API(POST /api/pcb/jobs) 의 dat 칸

- **확인:** 답을 받는다.

- **받은 곳 · 상태:** 답을 아직 받지 못했다. 그래서 dat 를 함께 올려 powercircuit 1건을 돌려 보는 시험도 아직 못 했다.



#### RQ-13 · (질문) 실패한 제출로 작업이 생겼는가

`P2` · 보낸 기록 없음



- **문제:** 500 뒤 서버에 작업이 남았는지 몰라 중계 세 건이 「모름」 이다. 4차 뒤 14:05 까지 8분 동안 1분마다 보았을 때 이력은 62건 그대로이고 이 보드 작업은 없었다. 서버 상태의 끝남 숫자는 다른 작업 뒤에도 그대로라 그 숫자로는 가늠할 수 없다.

- **바꿀 것:** 네 번 중 작업이나 기록이 생긴 것이 있는지, 있으면 작업 id 를 알려 달라.

- **위치:** 서버 작업 기록 · 이력(GET /api/pcb/public/history)

- **확인:** 답을 받아 HWAX 중계의 「모름」 세 건을 닫는다.



#### RQ-16 · (질문) 언제 다시 보내도 되는가

`P2` · 보낸 기록 없음



- **문제:** 원인을 모른 채 다시 보내면 서버에 짐을 더할 수 있다.

- **바꿀 것:** 다시 내도 되는 때를 알려 달라. 서버 기록을 함께 볼 시각을 정해 한 번 더 내는 방법도 괜찮다.

- **확인:** 답을 받고 다시 낸 제출이 DONE.

- **먼저:** RQ-12

- **참고:** 앞서 보낸 요청의 RQ-07(시험 날짜 · 서버 기록 함께 보기)을 대신한다.



#### RR-01 · 응답 스키마 문서(보고서는 text/html)

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 명세(/api/openapi.json)의 200 응답 스키마가 모두 비어 있다. 보고서 셋은 application/json 으로 적혀 있지만 실제로는 text/html 이다. 그래서 중계가 실측으로 맞추고 있다.

- **바꿀 것:** 엔드포인트별 응답 스키마를 주고, 보고서는 text/html 로 적는다.

- **위치:** OpenAPI 명세(/api/openapi.json) — 제출 · 작업 상태 · 결과 응답, 보고서 셋(/report · /report/download · /report/filtered)

- **확인:** 명세에 제출 · 작업 상태 · 결과 응답 스키마가 있고, 보고서 셋의 응답 형식이 text/html 로 적혀 있다.

- **받은 곳 · 상태:** 반영 기록이 없다. 중계는 아직 실측 응답에 맞춰 읽는다.



#### RR-02 · 체크리스트 · 규칙 목록 API

`P2` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 체크리스트 4개 · 규칙 54개를 목록으로 받을 API 가 없다. HWAX 쪽은 받은 정리 문서의 표(4종 54규칙)를 설정으로 들고 있어야 하고, 규칙 판이 바뀌면 낡는다.

- **바꿀 것:** 체크리스트 id · 이름 · 규칙 id · 이름 · 필요한 입력(dat 등) · 규칙 판을 내는 읽기 API 를 둔다.

- **확인:** API 가 4 · 54 를 돌려준다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈다. 11-06 담당 팀 회신(제출 허락)에 이 항목 답은 없었다. 11-10 에 검증 서버 웹 화면이 체크리스트 목록을 /pcb-api/checklists(따로 도는 읽기 목록)에서 받는 것은 보았으나, Chatbot API 쪽 목록 API 반영 소식은 없다.



#### RQ-02 · (질문) 메타 키

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 제출 메타에 어떤 키가 필수인지 모른다.

- **바꿀 것:** meta 의 필수 키 · 허용 키 · 값 목록을 알려 달라. pcb_type 에 올 수 있는 값, flags 두 키의 뜻과 기본값, submitter 에 넣을 꼴(이메일 @ 앞부분이면 되는지), project 에 name 과 model 중 무엇을 쓸지, HWAX 표지 키(예 meta.source)를 두어도 되는지, 빈 checklists 일 때 서버가 고르는 규칙, 주 보드가 아닌 보드도 받는지가 궁금하다.

- **위치:** POST /api/pcb/jobs 의 meta 칸

- **확인:** 답을 받는다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈다. 11-06 담당 팀 회신(제출 허락)에 meta 키 답은 없었다. 11-13 16:51 HWAX 중계로 낸 약 0.5 MB 보드가 이력 61건 중 25건과 같은 meta 꼴(checklists 1종 · project 의 name 과 pcb_type · flags 두 값 true · submitter)로 바로 DONE 이 되어, 쓸 수 있는 꼴 하나만 실측으로 안다. 필수 · 허용 키 목록은 아직 받지 못했다.



#### RQ-03 · (질문) 제출 응답 꼴

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 제출 응답의 꼴(작업 id 칸 · 오류 꼴 · 상태 값)을 담당 팀이 알려 준 적이 없다. 작업 id 칸만 실측으로 알았다.

- **바꿀 것:** 성공 · 오류 응답 꼴, 파일 크기 상한, 진행 중에 status 가 가질 수 있는 값, cond 의 뜻을 알려 달라.

- **위치:** POST /api/pcb/jobs 응답 · GET /api/pcb/jobs/{job_id} 의 status

- **확인:** 오류 응답 꼴과 상태 값 목록을 받아 중계 설정(terminal_statuses)에 넣는다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈고 답은 없었다. 11-13 16:51 HWAX 중계로 낸 약 0.5 MB 보드가 바로 작업 id 를 받고 1초 만에 DONE 이 되어, 작업 id 가 오는 칸만 실측으로 확인했다. 오류 응답 꼴 · 진행 중 status 값 · 파일 크기 상한 · cond 의 뜻은 아직 답이 없다.

- **참고:** 작업 id 칸은 확인됨. 남은 것은 RR-01 · RQ-12 와 함께 묻는다.



#### RQ-06 · (질문) API 바뀜 알림

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 명세 판이 1.0.0 이고 응답 스키마가 없어, API 가 바뀌어도 HWAX 쪽은 알 길이 없고 중계가 말없이 깨진다. 예: 11-13 에 HWAX 중계가 보드를 받아 오는 ODB 허브가 예고 없이 직접 호출을 막아(403) 제출 미리보기가 깨졌다.

- **바꿀 것:** 바뀜을 미리 알려 줄 길(메일 · 공지 · 명세 판 번호)을 정한다.

- **위치:** /api/openapi.json(명세 판 1.0.0)

- **확인:** 알림 경로를 받는다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈고 답은 없다. 알림 경로는 아직 정해지지 않았다. 답이 오기 전 HWAX 쪽 처리는 중계 서버가 기동할 때 명세를 받아 보관한 사본과 다르면 운영자에게 알리는 것이다.



#### RQ-08 · (질문) odb_check abnormal 읽는 법

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 11-04 에 본 이력 61건의 odb_check 가 abnormal 54 · normal 5 · 없음 2 라, abnormal 의 뜻을 가를 수 없다.

- **바꿀 것:** odb_check 가 abnormal 일 때 결과를 어떻게 읽어야 하는지, 사용자에게 무엇을 알려야 하는지, 거르는 법을 알려 달라.

- **확인:** 답을 받는다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈고 답은 없다. 답이 오기 전 HWAX 중계는 결과에 그 상태와 「ODB++ 추출 점검에서 이상이 보였다. 결과를 읽을 때 주의한다」 한 줄을 함께 싣는다.



#### RQ-09 · (질문) resolve-checklists 의 부작용

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** resolve 호출이 서버에 무엇을 쓰는지 모른다.

- **바꿀 것:** /api/pcb/resolve-checklists 가 기록을 남기거나 작업을 만들지 않는지, 처리 용량을 쓰는지, orchestrated 제출과 무엇이 다른지 답해 달라.

- **위치:** /api/pcb/resolve-checklists

- **확인:** 답을 받으면 중계에서 켤지 정한다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈고 답은 없다. 그 사이 HWAX 중계는 resolve-checklists 를 부르지 않는다(기능을 꺼 둠). 챗이 체크리스트 목록에서 고르고 사용자가 미리보기에서 확인한다.



#### RQ-10 · (질문) 위반 그림 shots/*.svg 받는 길

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 위반의 image 칸이 shots/…svg 꼴 상대 경로인데, 그 그림을 받는 경로가 명세에 없다.

- **바꿀 것:** 그림을 받는 API 경로를 알려 달라.

- **위치:** GET /api/pcb/jobs/{job_id}/results 응답의 위반 image 칸

- **확인:** 경로로 svg 를 받는다.

- **받은 곳 · 상태:** 11-04 자 요청서로 보냈고 답은 없다. 답이 오기 전 HWAX 중계는 그림 이름만 보이고 보고서 링크로 안내한다.



#### RQ-11 · (질문) 정식 이름 · '개발실 체크리스트' 써도 되는가

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** HWAX 포털 · 챗 도구에 이 연결을 「개발실 체크리스트」 라는 표시 이름으로 보이는데, 담당 팀 동의가 필요할 수 있다. HWAX 에는 ODB 허브의 체크리스트(38규칙)도 있어 두 체크리스트가 이름만으로 갈려야 사용자와 챗이 섞지 않는다.

- **바꿀 것:** 공식 시스템 이름(화면 이름 「Spark Chat」 · API 이름 「Chatbot API」 말고 담당 팀이 쓰는 이름)과 「개발실 체크리스트」 표시 이름을 써도 되는지 답해 달라.

- **확인:** 답을 받는다.

- **받은 곳 · 상태:** 11-05 에 요청서에 더한 물음이다. 답은 없다. HWAX 포털 · 챗 도구에는 11-05 부터 「개발실 체크리스트」 로 보이고 있다. 공식 이름을 받으면 도구 설명에 함께 적는다.



#### RR-03 · 가벼운 상태 확인 경로

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** 상태 확인 경로가 없어 무거운 호출로 살아 있는지 본다.

- **바꿀 것:** 서버가 받을 준비가 됐는지만 답하는 가벼운 경로(health)를 둔다.

- **위치:** /api/health

- **확인:** health 가 200.

- **받은 곳 · 상태:** 11-04 에 /api/health · /health 가 404 였다. 11-04 자 요청서로 보냈고 반영 소식은 없다. 그 사이 HWAX 중계는 /api/orchestration/status 로 살아 있는지 본다.



#### RR-04 · status=all 또는 여러 값

`P3` · 보낸 흔적 있음 · 끝난 흔적 없음



- **문제:** status=all 이 400 이라 결과를 다 읽으려면 fail · warn · pass · not_applicable · skipped 로 다섯 번 불러야 한다.

- **바꿀 것:** status=all 이나 여러 값을 받는다.

- **위치:** GET /api/pcb/jobs/{job_id}/results?status=

- **확인:** status=all 이 200.

- **받은 곳 · 상태:** 11-04 에 results?status=all 이 400 이었다. 11-04 자 요청서로 보냈고 반영 소식은 없다.



### 3-4. SimFlow — 19건



시험 입력은 실제 이름 대신 자리표시로 적었다 — 과제코드 C1 · 그 과제가 코어에서 풀리는 프로젝트 P1(우선순위 P1 과 다른 자리표시) · 모델코드 X2. 실제 값은 운영 쪽이 따로 넘긴다.



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SMO-1 | 과제코드 · 과제명 0건이면 ODB 허브 find_job 으로 다시 묻기 | P1 | 보낸 기록 없음 |

| PA-04 | SimFlow 패널 도구 설명 '묻지 않아도 먼저 호출' | P2 | 보낸 기록 없음 |

| PA-12 | (질문) SimFlow 받는 확장자 · 업로드 상한 | P2 | 보낸 기록 없음 |

| PA-13 | (질문) SimFlow 위임 토큰 발급 네 가지 | P2 | 보낸 기록 없음 |

| PA-14 | (질문) 패널이 부르는 도구 · 브리지 메서드 · CSP | P2 | 보낸 기록 없음 |

| Q-S1 | SimFlow 패널 프로토콜 판 · 호스트 메서드 | P2 | 보낸 기록 없음 |

| Q-S2 | SimFlow 패널이 부르는 도구 · 되돌릴 수 없는 것 | P2 | 보낸 기록 없음 |

| Q-S3 | SimFlow 리소스 CSP · permissions | P2 | 보낸 기록 없음 |

| Q-S4 | SimFlow 패널 같은 출처 기능 필요 여부 | P2 | 보낸 기록 없음 |

| Q-S5 | SimFlow 패널이 읽는 결과 칸 · _meta 개인정보 | P2 | 보낸 기록 없음 |

| Q-S6 | SimFlow 패널 업로드 조각 크기 · 상한 · 멱등 | P2 | 보낸 기록 없음 |

| Q-S7 | SimFlow 리소스 HTML 크기 · 바뀌는 때 | P2 | 보낸 기록 없음 |

| Q-S8 | SimFlow _meta.ui.visibility · 패널 전용 도구 | P2 | 보낸 기록 없음 |

| Q-S9 | 패널 도구 '묻지 않아도 먼저 호출' 문구 유지 여부 | P2 | 보낸 기록 없음 |

| SMO-2 | ODB 허브의 matched_by · via · core_key · reason 을 그대로 싣기 | P2 | 보낸 기록 없음 |

| PA-05 | simflow_upload_file 의 큰 파일 안내가 게이트웨이 사용자에게 안 맞음 | P3 | 보낸 기록 없음 |

| PA-06 | 워크플로우 파일 입력 accept · 접두 이름 | P3 | 보낸 기록 없음 |

| PA-07 | (2단계) 패널 전용 업로드 도구 숨김 표지 | P3 | 보낸 기록 없음 |

| PA-18 | (질문) IP 허용목록을 켤 계획 | P3 | 보낸 기록 없음 |



#### SMO-1 · 과제코드 · 과제명 0건이면 ODB 허브 find_job 으로 다시 묻기

`P1` · 보낸 기록 없음



- **문제:** search_odbhub_boards 가 낱말 일치만 봐서 과제코드 C1 → 0건(이유 없음)이다. 같은 C1 을 ODB 허브 find_job 에 주면 P1 으로 풀린다.

- **바꿀 것:** 낱말 일치가 0건이면 ODB 허브 find_job 으로 다시 묻고 그 결과(보드 · by_model)를 돌려준다.

- **위치:** SimFlow search_odbhub_boards

- **확인:** C1 → 보드 33장 근처 · matched_by task_code. P1 → 지금과 같은 33장.

- **선례:** ODB 허브 find_job — 과제명 · 과제코드 · 모델코드를 코어로 풀어 matched_by · via · core_key 를 준다(ODB 허브가 앞서 반영). 11-24 에 C1 을 주면 matched_by task_code · core_key P1.

- **참고:** HWAX 쪽 웹 챗 온톨로지 시험은 이 요청이 반영된 뒤 돌린다.



#### PA-04 · SimFlow 패널 도구 설명 '묻지 않아도 먼저 호출'

`P2` · 보낸 기록 없음



- **문제:** 10-14 포털 챗이 open_resin_panel 1회 · open_workflow_panel 3회를 불렀고(결과 261~1,008자) 화면에 패널이 없었다.

- **바꿀 것:** '패널을 그리는 클라이언트에서만' 으로 다듬거나 못 그리는 환경의 할 일(prepare_run)을 결과에 싣는다.

- **위치:** SimFlow open_resin_panel 설명

- **확인:** 설명에서 '먼저 호출' 문구가 빠지거나 결과에 prepare_run 안내가 있다.

- **참고:** HWAX 포털 챗은 패널을 그릴 수 있는 턴에만 패널 도구를 묶고, 그릴 수 없는 턴에서는 숨긴다.



#### PA-12 · (질문) SimFlow 받는 확장자 · 업로드 상한

`P2` · 보낸 기록 없음



- **문제:** 포털 업로드 요청 500MB, nginx /simflow/ 600MB 로 상한이 다르고 확장자가 정해지지 않아 챗 업로드 첫 실주행을 미루고 있다.

- **바꿀 것:** 넷에 답해 달라. ① SimFlow 가 받는 입력 확장자 전체 목록 ② 한 파일 업로드 상한 ③ 업로드 요청 · 응답 칸 — HWAX 는 multipart 칸 file 로 보내고 응답에서 업로드 id · filename · size_bytes · status 를 읽는다. id 칸이 id 인지 upload_id 인지 ④ 상태 보기가 GET /api/v1/mcp-uploads/{id} 이고 값이 drm_pending → ready 인지, 실패 · 거절 때의 상태 값.

- **위치:** /api/v1/mcp-uploads

- **확인:** ①~④ 답을 물음 번호마다 한두 줄로 받는다.

- **참고:** HWAX 포털의 챗 업로드 목적지 SimFlow 와 nginx /simflow/ 상한을 이 답에 맞춘다. 지금은 임시로 x_t 하나만 받는다.



#### PA-13 · (질문) SimFlow 위임 토큰 발급 네 가지

`P2` · 보낸 기록 없음



- **문제:** expires_in 유무, 무효화 범위, 같은 client 발급처, 10-16 UTC 세 시각의 연속 500.

- **바꿀 것:** 네 가지에 답해 달라. ① 응답에 expires_in(초)을 넣을 수 있는가 ② 발급 때 이전 토큰을 무효화하는 범위가 (사용자, X-Heax-Client) 단위인가, 포털 타일 로그인(portal-callback)이 게이트웨이 토큰을 무효화하지 않는가 ③ 같은 client=gateway 로 발급하는 다른 곳(개발 서버 · 시험 도구)이 있는가 ④ 10-16 UTC 02:44 · 08:32 · 09:14 에 사용자 한 명이 /auth/sso 에서 500 을 연달아 받았다(09:24 성공) — 그 시각 로그를 봐 달라.

- **위치:** POST /api/v1/auth/sso

- **확인:** 네 가지 답을 받는다.

- **참고:** HWAX 게이트웨이는 '401 일 때만, 한 번만 다시 발급' 으로 이미 바꿨다. 이 답으로 그 동작이 맞는지 본다.



#### PA-14 · (질문) 패널이 부르는 도구 · 브리지 메서드 · CSP

`P2` · 보낸 기록 없음



- **문제:** 10-16 리소스 _meta 가 비어 패널 호스트 보안 규칙을 정할 수 없다.

- **바꿀 것:** 패널이 부르는 도구 전체 목록, 필요한 브리지 메서드, 리소스의 CSP 와 외부 도메인 선언을 알려 달라. Q-S1 · Q-S2 · Q-S3 으로 나눠 물었고, 이 셋에 답하면 PA-14 도 닫는다.

- **위치:** SimFlow 패널(MCP Apps) 리소스 · 패널 도구

- **확인:** Q-S1 · Q-S2 · Q-S3 답을 받는다.

- **참고:** HWAX 포털 챗 패널 호스트는 이미 켜져 있고, 이 답으로 보안 규칙 — 패널이 부를 수 있는 도구를 그 앱의 것으로만 묶음 — 을 맞춘다.



#### Q-S1 · SimFlow 패널 프로토콜 판 · 호스트 메서드

`P2` · 보낸 기록 없음



- **문제:** 호스트 브리지가 받을 메서드와 판을 모른다.

- **바꿀 것:** ui/initialize 에 싣는 프로토콜 판과 패널이 호스트에 부르는 메서드 전부를 알려 달라. 후보는 tools/call · resources/read · ui/open-link · ui/message · ui/update-model-context · ui/request-display-mode · notifications/message · ping.

- **위치:** SimFlow 패널(MCP Apps)

- **확인:** 답을 받는다.

- **선례:** PA-14

- **참고:** PA-14 는 Q-S1 ~ Q-S3 으로 나눠 물음.



#### Q-S2 · SimFlow 패널이 부르는 도구 · 되돌릴 수 없는 것

`P2` · 보낸 기록 없음



- **문제:** 패널 도구 허용 목록과 첫 쓰기 확인을 만들 목록이 없다.

- **바꿀 것:** 도구 이름 전부와 잡 제출 · 파일 등록 · 지우기 도구를 알려 달라.

- **위치:** SimFlow 패널

- **확인:** 답을 받는다.

- **선례:** PA-14



#### Q-S3 · SimFlow 리소스 CSP · permissions

`P2` · 보낸 기록 없음



- **문제:** 패널 문서 앞에 넣을 CSP 와 바깥 연결 필요 여부를 모른다.

- **바꿀 것:** 리소스 _meta.ui.csp(connectDomains · resourceDomains · frameDomains · baseUriDomains)와 permissions 를 내는지, 패널이 바깥 주소(앱 서버 직접 fetch · CDN · 글꼴)에 닿아야 하는지 아니면 모두 tools/call 로 하는지 알려 달라.

- **위치:** SimFlow 패널 리소스

- **확인:** 답을 받는다.

- **선례:** PA-14



#### Q-S4 · SimFlow 패널 같은 출처 기능 필요 여부

`P2` · 보낸 기록 없음



- **문제:** srcdoc 샌드박스에서는 localStorage · 쿠키 등을 못 쓴다.

- **바꿀 것:** 같은 출처 기능(localStorage · IndexedDB · 쿠키 · Service Worker · 팝업 · 내려받기)이 패널에 꼭 필요한지 알려 달라.

- **위치:** SimFlow 패널

- **확인:** 답을 받는다.



#### Q-S5 · SimFlow 패널이 읽는 결과 칸 · _meta 개인정보

`P2` · 보낸 기록 없음



- **문제:** 결과 _meta 는 게이트웨이 가림을 지나지 않아 무엇이 실리는지 알아야 한다.

- **바꿀 것:** content · structuredContent · _meta 중 무엇을 읽는지, _meta 에 이름 · 계정 · 메일이 실리는지 알려 달라.

- **위치:** SimFlow 도구 결과

- **확인:** 답을 받는다.



#### Q-S6 · SimFlow 패널 업로드 조각 크기 · 상한 · 멱등

`P2` · 보낸 기록 없음



- **문제:** 포털은 호출 4 MiB · 세션 32 MB 로 두는데 두 탭에서 같은 조각 · 커밋이 되풀이될 수 있다.

- **바꿀 것:** panel_upload_* 의 조각 크기 · 한 파일 상한 · 멱등 동작을 알려 달라.

- **위치:** panel_upload_begin · append · commit

- **확인:** 답을 받는다.



#### Q-S7 · SimFlow 리소스 HTML 크기 · 바뀌는 때

`P2` · 보낸 기록 없음



- **문제:** 패널 문서 상한(2 MiB)과 캐시를 정할 값이 없다.

- **바꿀 것:** 보통 · 최대 크기와 바뀌는 때를 알려 달라.

- **위치:** SimFlow 패널 리소스

- **확인:** 답을 받는다.



#### Q-S8 · SimFlow _meta.ui.visibility · 패널 전용 도구

`P2` · 보낸 기록 없음



- **문제:** 모델에게 숨길 패널 전용 도구를 가릴 표지를 모른다.

- **바꿀 것:** visibility 사용 여부와 패널 전용 도구 목록을 알려 달라.

- **위치:** SimFlow 도구 정의

- **확인:** 답을 받는다.

- **참고:** PA-07 과 같은 표지.



#### Q-S9 · 패널 도구 '묻지 않아도 먼저 호출' 문구 유지 여부

`P2` · 보낸 기록 없음



- **문제:** 포털 챗은 패널을 그릴 수 있는 턴에만 패널 도구를 묶는다.

- **바꿀 것:** 문구를 그대로 둘지 알려 달라.

- **위치:** SimFlow 패널 도구 설명

- **확인:** 답을 받는다.

- **참고:** 문구 다듬기는 PA-04.



#### SMO-2 · ODB 허브의 matched_by · via · core_key · reason 을 그대로 싣기

`P2` · 보낸 기록 없음



- **문제:** 세 입력(C1 · P1 · X2) 모두 어떻게 찾았는지가 응답에 없다.

- **바꿀 것:** ODB 허브가 주는 matched_by · via · core_key · reason 을 그대로 싣고, 0건이면 reason 을 준다.

- **위치:** SimFlow search_odbhub_boards

- **확인:** 없는 과제코드 → 0건과 reason not_in_core. 응답에 matched_by.

- **먼저:** SMO-1

- **참고:** Q-1 — X2 보드 1건은 모델 칸 글자가 잘려 model_code_key 가 비었다. SimFlow 표시에서 잘리는지 ODB 허브 자료가 원래 그런지 확인해 달라(ODB 허브 자료라면 HWAX 운영 쪽이 ODB 허브 요청으로 옮긴다).



#### PA-05 · simflow_upload_file 의 큰 파일 안내가 게이트웨이 사용자에게 안 맞음

`P3` · 보낸 기록 없음



- **문제:** 게이트웨이 사용자는 SimFlow 토큰이 없고 base64 는 수백 KB 이하에서만 실용적이다.

- **바꿀 것:** 큰 로컬 파일용 1회용 업로드 티켓 도구를 검토한다.

- **위치:** SimFlow upload_file

- **확인:** 큰 로컬 파일용 1회용 업로드 티켓 도구를 둘지 검토 결과 또는 계획을 받는다.



#### PA-06 · 워크플로우 파일 입력 accept · 접두 이름

`P3` · 보낸 기록 없음



- **문제:** accept 정보가 모델이 보는 자리에 늘 있지 않고 upload_file 이 게이트웨이에서 simflow_upload_file 로만 보인다.

- **바꿀 것:** 새 워크플로우에도 파일 입력의 accept 를 채운다. 가능하면 get_workflow_detail 의 inputs[] 와 prepare_run 의 다음 질문 설명에도 accept 를 넣는다. run_workflow · approve_gate · prepare_run 설명이 upload_file 이름을 직접 말한다면 게이트웨이 접두 이름(simflow_upload_file)을 감안한다.

- **위치:** SimFlow get_workflow_detail · prepare_run

- **확인:** 새 워크플로우의 파일 입력과 get_workflow_detail inputs[] 에 accept 가 있다. 또는 반영 계획을 받는다.



#### PA-07 · (2단계) 패널 전용 업로드 도구 숨김 표지

`P3` · 보낸 기록 없음



- **문제:** '[패널 전용]' 도구가 모델용으로 올라 있다.

- **바꿀 것:** _meta.ui.visibility: ["app"] 를 붙인다.

- **위치:** SimFlow panel_upload_*

- **확인:** 게이트웨이가 _meta 를 옮긴 뒤 모델 목록에서 빠진다.



#### PA-18 · (질문) IP 허용목록을 켤 계획

`P3` · 보낸 기록 없음



- **문제:** IP 허용목록을 켜는 날, HWAX 쪽 NO_PROXY 에 그쪽 서버 주소가 아직 없으면 HWAX 호출이 사내 프록시를 거쳐 들어가 403 이 난다(10-03 다른 파트너 앱에서 실제로 났다). 그래서 켜는 날을 미리 알아야 HWAX 쪽 설정을 먼저 바꿀 수 있다.

- **바꿀 것:** 미리 알려 달라.



### 3-5. Datahub 플랫폼 (hwax-batch 공통 엔진) — 15건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| DHO-1 | 과제 · 개발모델 · 모델코드도 관계(또는 참조 칸) 받기 | P1 | 보낸 기록 없음 |

| DP-01 | 허브 응답 크기 — ref_labels 행마다 되풀이 · group_options · related | P1 | 보낸 기록 없음 |

| DP-02 | 솔더 접합 불량 분류의 'hip' 글자 오탐(데이터) | P1 | 보낸 기록 없음 |

| DP-04 | resolve 가 질의 안에 낱말로 든 별칭을 못 찾음 | P2 | 보낸 기록 없음 |

| DP-05 | 코어 별칭 보강 — 한국어 마케팅명 · '메인 PBA'(데이터) | P2 | 보낸 기록 없음 |

| DP-07 | failuretrace_whoami 한 번에 27~33 s | P2 | 보낸 기록 없음 |

| DP-08 | pd_defect 행에 검출자 · 작업자 이름이 그대로 | P2 | 보낸 기록 없음 |

| DH-4 | objects_list properties 짧은 꼴의 참조 칸이 코어 key 도 받거나 0건 진단에 ref.<칸>.key 안내 | P3 | 보낸 기록 없음 |

| DP-03 | 허브 넷 도구 설명이 글자까지 같음 — 설치별 tagline · 응답 key | P3 | 보낸 기록 없음 |

| DP-06 | graph_neighbors truncated 가 늘 true | P3 | 보낸 기록 없음 |

| DP-09 | 시험이 드러낸 코어 공백(데이터) | P3 | 보낸 기록 없음 |

| DP-11 | (알림) core_status endpoint 가 루프백 절대 주소 | P3 | 보낸 기록 없음 |

| DP-12 | (알림) 토큰 화면 범위 기본값 read 체크 | P3 | 보낸 기록 없음 |

| DP-13 | (알림) plm_test_site 는 허브에 두지 않는 것으로 봄 | P3 | 보낸 기록 없음 |

| DP-14 | 조건 주소 오류에 바른 주소 예가 없음 | P3 | 보낸 기록 없음 |



#### DHO-1 · 과제 · 개발모델 · 모델코드도 관계(또는 참조 칸) 받기

`P1` · 보낸 기록 없음



- **문제:** 네 허브 모두 46 타입을 받지만 관계까지 받는 타입은 14개이고, 과제 · 개발모델 · 모델코드는 relations: false 다. 허브 안에서 과제 ↔ 개발모델 ↔ 모델코드를 관계로 걸을 수 없다.

- **바꿀 것:** 이 셋도 관계(또는 참조 칸)를 받는다. 받는 행이 많으면 이 셋만 주 1회 처음부터 받기로 둔다.

- **위치:** 각 허브의 코어 소스 46개 중 과제 · 개발모델 · 모델코드 소스의 관계 받기 설정(지금 relations: false)

- **확인:** 허브 하나에서 과제 → 개발모델 → 모델코드를 graph_neighbors 로 걸음.

- **선례:** 앞선 Datahub 플랫폼 요청 DP-01 ~ DP-09 · DP-11 ~ DP-14(같은 문서 — 응답 크기 · 낱말 오탐 등)

- **참고:** Q-1(넷 공통) — FailureTrace 과제 받기가 10-28 뒤 매회 rows_seen 0 이다. 증분이라 바뀐 것이 없는지, 증분 기준 시각이 멈췄는지 확인해 달라(건수는 코어와 같음). HWAX 운영 쪽은 hwax-batch 블록을 손으로 고치지 않는다. 소스 설정 바꾸기는 허브 관리자가 한다.



#### DP-01 · 허브 응답 크기 — ref_labels 행마다 되풀이 · group_options · related

`P1` · 보낸 기록 없음



- **문제:** plm_model objects_list 34행이 135,566자(ref_labels 79%), FailureTrace objects_summary group_options 79,056/104,048자, object_get 약 12만 자. 같은 시기 262,144 토큰 넘침 · GLM 300,000 토큰 넘침으로 챗 오류 2건(10-26 · 10-27).

- **바꿀 것:** ref_labels 는 페이지에 한 번 또는 행에 id 만. objects_summary 는 include_options=true 일 때만 group_options. object_get related 는 관계별 수 + 앞 N줄.

- **위치:** StandardPlatform objects_list · objects_summary · object_get

- **확인:** 10-27 에 잰 같은 호출(plm_model objects_list 34행 · objects_summary · object_get(PRT-PCB))의 응답이 챗 컷 안에 든다.

- **참고:** HWAX 쪽은 에이전트가 허브 응답을 접고, 운영 쪽이 도구 결과 상한을 정한다. 허브가 11-12 운영 서버로 옮겨 수치가 바뀌었을 수 있다. 11-01 다시 본 것: 허브 응답이 여전히 크다 — 10-30 재시험에서 10만 자 넘는 응답이 11건이었다. 10-27 실측은 objects_list 34행 135,566자 가운데 ref_labels 가 79%.



#### DP-02 · 솔더 접합 불량 분류의 'hip' 글자 오탐(데이터)

`P1` · 보낸 기록 없음



- **문제:** JNT-SLD-01 분류 389건 중 HIP 164 · hip 155(약 82%)가 CHIP · CHIPSET · Ship Mode 같은 제목 오탐이다.

- **바꿀 것:** hip 를 (?<![a-z])hip(?![a-z])(대소문자 무시)로 바꾸고 짧은 영문 패턴을 점검한 뒤 FailureTrace pd_defect 연결을 다시 분류한다.

- **위치:** 자주검증 Datahub 관리 입력 JNT-SLD-01 match_pattern

- **확인:** 재분류 뒤 JNT-SLD-01 에 걸린 pd_defect 의 매칭어에 CHIP · CHIPSET · Ship Mode · Chip ID 같은 제목이 없다. 솔더 크랙 문제점 수를 다시 잰다(10-27 13:43 KST 389건).

- **참고:** 코드 변경 없음(관리 화면). 11-01 다시 본 것: 솔더 접합 불량 분류 약 82% 가 'hip' 오탐 — 389건 중 319건이 오탐으로 10-27 과 같았고, HWAX 쪽 허브 건너기 시험도 389건을 정답으로 셌다.



#### DP-04 · resolve 가 질의 안에 낱말로 든 별칭을 못 찾음

`P2` · 보낸 기록 없음



- **문제:** resolve(part, '메인 PBA') 는 none 인데 'PBA' · 'MAIN' 은 각각 PRT-PCB 별칭이다.

- **바꿀 것:** 포함 단계에서 질의 안 낱말 별칭을 candidates 로 낸다.

- **위치:** StandardPlatform resolve

- **확인:** resolve(part, '메인 PBA') 가 PRT-PCB 로 풀린다.

- **먼저:** DP-05 와 둘 중 하나 또는 둘 다

- **참고:** 11-01 다시 본 것(DP-04 · DP-05(다시)): '메인 PBA' · 한국어 마케팅명 resolve 가 none — 10-29 에 다시 쟀고 그대로 none 이었다.



#### DP-05 · 코어 별칭 보강 — 한국어 마케팅명 · '메인 PBA'(데이터)

`P2` · 보낸 기록 없음



- **문제:** 한국어 마케팅명 resolve 는 none, 영문 마케팅명만 프로젝트 별칭에 있다.

- **바꿀 것:** plm_project · pub_dev_code 에 한국어 마케팅명, PRT-PCB 에 '메인 PBA' · '메인 기판' 별칭.

- **위치:** 자주검증 Datahub 관리 입력

- **확인:** resolve 로 한국어 마케팅명이 프로젝트로 풀린다.



#### DP-07 · failuretrace_whoami 한 번에 27~33 s

`P2` · 보낸 기록 없음



- **문제:** 감사 ms 33219 · 27009 · 29110 · 27737. facts 를 읽을 때 센다.

- **바꿀 것:** facts 캐시 또는 근사 건수.

- **위치:** StandardPlatform whoami facts

- **확인:** whoami 가 수 초 안에 답한다.

- **참고:** 11-01 다시 본 것(DP-07(다시)): failuretrace_whoami 한 번이 40초 안팎 — 성공 호출 44,434 ms(10-29) · 39,206 ms(10-30)로, 같은 때 자주검증 whoami 232~521 ms 보다 훨씬 길다.



#### DP-08 · pd_defect 행에 검출자 · 작업자 이름이 그대로

`P2` · 보낸 기록 없음



- **문제:** failuretrace_objects_list(pd_defect) 의 label · content_text 에 사람 이름이 실려 챗으로 간다.

- **바꿀 것:** FailureTrace 출력에서 이름을 가린다.

- **위치:** FailureTrace objects_list 출력

- **확인:** failuretrace_objects_list(pd_defect) 응답의 label · content_text 와 그것으로 만든 챗 답에 사람 이름이 없다.

- **먼저:** 가릴 범위는 HWAX 쪽이 정해 알린다. 권하는 안은 게이트웨이로 나가는 응답에서 이름 · IMEI 꼴 · 일련번호 꼴 · 계정 ID · 작성자 이름을 기본으로 가리는 것이다.

- **참고:** 가릴 곳은 이 플랫폼 출력으로 HWAX 쪽이 정했다. HWAX 챗 어댑터와 게이트웨이는 자유 글 속 이름을 따로 가리지 않는다. 11-01 다시 본 것: pd_defect 글 속 검출자 · 작업자 이름이 그대로 챗으로 나간다 — label · content_text 에 사람 이름이 실린다.



#### DH-4 · objects_list properties 짧은 꼴의 참조 칸이 코어 key 도 받거나 0건 진단에 ref.<칸>.key 안내

`P3` · 보낸 기록 없음



- **문제:** objects_list(type_slug pd_defect, properties={part: PRT-SHIELD_CAN}) → 0건, 진단은 link_missing [p.part] · '조건으로 0건' 뿐. 같은 뜻의 conditions ref.part.key eq PRT-SHIELD_CAN 은 466건. 모델은 코어에서 key 를 먼저 얻어 짧은 꼴을 자주 쓴다.

- **바꿀 것:** 참조 칸 짧은 꼴 값이 id 꼴이 아니면 key 로도 찾거나, 0건 진단에 '참조 칸 — ref.<칸>.key 로 거른다' 한 줄.

- **위치:** Datahub objects_list properties 짧은 꼴 · 0건 진단

- **확인:** properties={part: PRT-SHIELD_CAN} 이 466건이거나 0건 진단에 ref.part.key 한 줄

- **참고:** Datahub 플랫폼 요청 DP-01 ~ DP-09 · DP-11 ~ DP-14 와 같은 묶음으로 보낸다.



#### DP-03 · 허브 넷 도구 설명이 글자까지 같음 — 설치별 tagline · 응답 key

`P3` · 보낸 기록 없음



- **문제:** 약 100종 × 4 허브 도구 설명이 글자까지 같아 챗이 허브를 가르지 못한다. 10-27 HWAX 챗 시험(허브 건너기)에서 자주검증 id 로 부른 failuretrace_graph_neighbors 가 [APP-GRAPH-0001] 이었다.

- **바꿀 것:** 설명 첫 줄에 설치별 tagline(무엇을 · 정본/사본), 응답 줄마다 key 와 '다른 허브에서는 key 로 다시 resolve'.

- **위치:** StandardPlatform 도구 설명 · 응답

- **확인:** 고장모드를 묻는 HWAX 챗 시험에서 챗이 자주검증 허브의 object_resolve 를 고른다(HWAX 에이전트 · 게이트웨이 쪽 반영과 함께 본다).

- **참고:** HWAX 쪽은 게이트웨이 search_tools 가 같은 설명의 허브 도구는 정본 하나만 올리게 했고, 에이전트가 코어 허브 도구를 늘 묶고 '허브를 건널 때 key 로 다시 resolve' 규칙을 넣었다. 운영 쪽이 hwax-batch 앱 설명 문안을 고친다.



#### DP-06 · graph_neighbors truncated 가 늘 true

`P3` · 보낸 기록 없음



- **문제:** 간선 1개만 와도, degree 3 을 다 받아도 truncated true.

- **바꿀 것:** 초점 노드 간선이 잘렸을 때만 true, 이웃의 더 있음은 다른 칸으로.

- **위치:** StandardPlatform graph_neighbors

- **확인:** 간선을 다 받은 초점 노드(예: CRT-VRF-086, degree 3)에서 truncated 가 false 다.

- **참고:** 11-01 다시 본 것: graph_neighbors truncated 가 늘 참 — 간선을 다 받아도 최상위 truncated 가 참이라 챗이 '관계가 잘렸다' 고 답한다.



#### DP-09 · 시험이 드러낸 코어 공백(데이터)

`P3` · 보낸 기록 없음



- **문제:** test_item 에 applies_stress 없음(시험군에만 67건), DRP-FLR-001 detects 에 크랙 없음, PRT-PCB 를 가리키는 tests_part 0건, plm_task 마다 개발모델 1~2개.

- **바꿀 것:** 부하 위치 설명 또는 내려 주기, detects 검토, tests_part 채우기.

- **위치:** 자주검증 Datahub 관리 입력

- **확인:** 시험항목 부하 · 검출 고장모드 · tests_part 를 묻는 HWAX 챗 시험 답이 코어 행으로 나온다.

- **참고:** 11-01 다시 본 것(DP-09(다시)): 코어 공백이 챗 답의 빈칸이 됨 — 시험항목 부하 칸 · 낙하 시험 한 항목의 검출 고장모드 · tests_part 0건이 그대로다.



#### DP-11 · (알림) core_status endpoint 가 루프백 절대 주소

`P3` · 보낸 기록 없음



- **문제:** core_status 와 카탈로그의 endpoint 가 루프백 절대 주소라 그것을 따라가는 소비자는 깨진다. core_status 가 보여 주는 base 는 …/rootdesign/api/core 라 소비자 설정에 그대로 넣으면 /core/core 가 된다.

- **바꿀 것:** endpoint 를 고칠지 판단해 달라(알림 — 요청 아님). 지금 받는 세 앱은 base 에서 경로를 만들어 영향이 없다.

- **위치:** core_status · 카탈로그 endpoint

- **참고:** HWAX 쪽 문서의 base 설명은 이미 바로잡았다.



#### DP-12 · (알림) 토큰 화면 범위 기본값 read 체크

`P3` · 보낸 기록 없음



- **문제:** 코어 동기화용은 core:read 만 남겨야 하는데 기존 소비자 대부분이 read 로 발급돼 있다.

- **바꿀 것:** 토큰 화면의 범위 기본값을 바꿀지 판단해 달라(알림 — 요청 아님). 코어 동기화용은 core:read 만 남기고 read 를 꺼야 '코어 전용' 이 된다.

- **위치:** 허브 웹 토큰 화면의 범위 기본값(지금 '읽기(read)' 체크)



#### DP-13 · (알림) plm_test_site 는 허브에 두지 않는 것으로 봄

`P3` · 보낸 기록 없음



- **문제:** 공개 35종에 plm_test_site 가 없다. HWAX 쪽 DynaForge 가 이 타입을 가정하고 있었다.

- **바꿀 것:** 계획이 다르면 알려 달라.



#### DP-14 · 조건 주소 오류에 바른 주소 예가 없음

`P3` · 보낸 기록 없음



- **문제:** HWAX 챗 온톨로지 시험 두 문항에서 조건 주소 오류 APP-OBJECTS-0073 이 4번 났는데, 오류에 바른 주소 예가 없다.

- **바꿀 것:** 오류 문구에 그 타입에서 쓸 수 있는 주소 예(in.applies_to_part · out.occurs_in_part 꼴)를 싣는다.

- **위치:** 허브 objects 조건 주소 검사

- **확인:** 같은 오류 응답에 주소 예가 나온다.



### 3-6. ODB 허브 — 15건



시험 입력은 실제 이름 대신 자리표시로 적었다 — 과제 A · 과제 A 가 속한 프로젝트 P1(우선순위 P1 과 다른 자리표시) · 과제 A 의 모델코드 X1. 실제 값은 운영 쪽이 따로 넘긴다.



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| OH-01 | find_nets 200건 조용한 잘림 → 페이지 칸 | P1 | 보낸 기록 없음 |

| OH-02 | list_parts 큰 페이지 · 좌표 · 미분류 부품 포함 | P1 | 보낸 기록 없음 |

| OD-5 | 넓은 범위 옛 토큰 → core:read 토큰으로 바꾸고 옛 토큰 지우기 | P2 | 보낸 기록 없음 |

| ODO-1 | 보드 지역 표기를 코어 모델코드로 푸는 규칙(못 풀면 note 에 key 없는 보드 수) | P2 | 보낸 기록 없음 |

| ODO-2 | 대기 부분 일치 162 · 정확 15 목록을 읽는 도구 | P2 | 보낸 기록 없음 |

| OH-03 | 넷 200개 넘는 부품 | P2 | 보낸 기록 없음 |

| OH-04 | 보드 외곽 bbox 를 부품 좌표와 같은 기준으로 | P2 | 보낸 기록 없음 |

| OH-06 | 조회 도구 전부에 readOnlyHint | P2 | 보낸 기록 없음 |

| OD-8 | 부품 분류를 코어 part 와 잇기 | P3 | 보낸 기록 없음 |

| OD-9 | (질문) renamed_from 으로 이름 바뀜 · 합침을 따라가는가 | P3 | 보낸 기록 없음 |

| ODO-3 | find_job note 문장 중복 제거 | P3 | 보낸 기록 없음 |

| ODO-4 | (선택) 보드 응답에서 결함 쪽 다음 호출 안내 | P3 | 보낸 기록 없음 |

| OH-05 | 보드 단위 값(ODB 판 · 플레인 종류 · 동박 두께 · 높이) | P3 | 보낸 기록 없음 |

| PA-09 | (질문) 위임 호출이 ODB 기록에 본인으로 남나 | P3 | 보낸 기록 없음 |

| PA-18 | (질문) IP 허용목록을 켤 계획 | P3 | 보낸 기록 없음 |



#### OH-01 · find_nets 200건 조용한 잘림 → 페이지 칸

`P1` · 보낸 기록 없음



- **문제:** find_nets 가 200건에서 말없이 잘려 심사가 넷 일부만 본다.

- **바꿀 것:** offset · total · has_more · truncated · pin_count 를 준다.

- **위치:** find_nets

- **확인:** 넷이 200개 넘는 보드에서 has_more/truncated 가 참이고 offset 으로 나머지를 받는다.

- **참고:** HWAX 리스크 심사 앱의 다음 단계(ODB 허브 묶음 읽기로 넘어가기)가 이것을 기다린다. 지금은 넷이 200건에서 잘리고 핀 수는 넷마다 get_net 을 한 번씩 불러야 한다.



#### OH-02 · list_parts 큰 페이지 · 좌표 · 미분류 부품 포함

`P1` · 보낸 기록 없음



- **문제:** page_size 가 100 으로 묶이고 x/y/회전/넷이 없으며 미분류 부품을 뺀다 — 보드 1: 목록 748 대 실장 924, 보드 2: 528 대 702.

- **바꿀 것:** page_size 최대 2000, 좌표 · 회전 · 넷 칸, 미분류 포함 옵션.

- **위치:** list_parts

- **확인:** 보드 1 에서 page_size=2000 · 미분류 포함으로 924개가 좌표와 함께 나온다.

- **참고:** HWAX 리스크 심사 앱의 다음 단계(ODB 허브 묶음 읽기로 넘어가기)가 이것을 기다린다. 지금은 부품 좌표를 얻으려고 get_part_detail 을 부품마다 불러 보드 1 에 약 760번, 보드 2 에 약 535번이 든다.



#### OD-5 · 넓은 범위 옛 토큰 → core:read 토큰으로 바꾸고 옛 토큰 지우기

`P2` · 보낸 기록 없음



- **문제:** 옛 토큰은 범위가 넓고(narrow:false) 만료가 없다(10-15 발급).

- **바꿀 것:** core:read 토큰만 쓰고 옛 넓은 토큰을 지운다.

- **위치:** 자주검증 Datahub 웹의 토큰 화면(core_status consumers 의 'odbhub' 토큰)

- **확인:** 코어 허브 토큰 목록에 그 옛 토큰이 없고, 받기는 core:read 토큰으로 ok.

- **참고:** 새 core:read 토큰으로 바꾸기는 끝났다. 남은 것은 옛 넓은 토큰 지우기다. 지운 뒤 HWAX 운영 쪽이 확인한다.



#### ODO-1 · 보드 지역 표기를 코어 모델코드로 푸는 규칙(못 풀면 note 에 key 없는 보드 수)

`P2` · 보낸 기록 없음



- **문제:** P1 보드 33장 중 28장이 모델코드 key 없이 지역 표기만 있어, 과제 A 로 찾으면 33장 전부가 나온다(모델 단위로 좁혀지지 않음).

- **바꿀 것:** 보드 메타의 지역 표기를 코어 plm_model_code 별칭 · 개발모델 향 정보로 푸는 규칙을 둔다. 못 풀면 프로젝트로 넓히되 note 에 「모델코드 key 없는 보드 N장 포함」 을 적는다.

- **위치:** ODB 허브 find_job · 보드 메타 매핑

- **확인:** 과제 A → by_model 에서 key 없는 보드가 줄거나 note 에 「key 없는 보드 N장 포함」.

- **선례:** ODB 허브가 앞서 반영한 OD-1 ~ OD-3 — 코어 4 타입(프로젝트 · 과제 · 개발모델 · 모델코드)을 받고, find_job 이 과제명 · 과제코드 · 모델코드를 코어로 풀어 matched_by · via · core_key 를 준다.

- **참고:** 보드 → 코어 현황: 보드 1,460 · 프로젝트 연결 1,101 · 모델코드 연결 787 · 코어에 없음 182.



#### ODO-2 · 대기 부분 일치 162 · 정확 15 목록을 읽는 도구

`P2` · 보낸 기록 없음



- **문제:** ping 의 mapping 에 대기 부분 162 · 정확 15 라는 수만 있고 사람이 목록을 볼 길이 없다.

- **바꿀 것:** 대기 건 목록 읽기 도구(보드 · 후보 코어 key · 점수, 읽기만)를 둔다. 확정은 지금처럼 화면에서 사람이 한다.

- **위치:** ODB 허브 MCP(ping 의 mapping)

- **확인:** 목록 도구 → 162 · 15 와 같은 수.

- **참고:** Q-1 — 대기 건을 확정하면 보드 → 코어 연결이 바로 늘어나는지, 다음 받기 때 늘어나는지. 확정 자체는 공유 데이터에 쓰는 일이라 HWAX 운영 쪽 사용자 결정 뒤 화면에서 한다.



#### OH-03 · 넷 200개 넘는 부품

`P2` · 보낸 기록 없음



- **문제:** 넷이 200개 넘는 부품의 넷 목록이 잘린다.

- **바꿀 것:** 부품 상세의 넷 목록에도 페이지 · truncated 를 준다.

- **위치:** get_part_detail

- **확인:** 넷 200+ 부품에서 전체 넷을 받는다.



#### OH-04 · 보드 외곽 bbox 를 부품 좌표와 같은 기준으로

`P2` · 보낸 기록 없음



- **문제:** get_volume_result.board 는 폭 · 높이 · 면적만 준다. 부품 · 구멍 좌표는 ODB step 기준이라 보드마다 원점이 다르다(보드 1 은 음수 좌표, 보드 2 는 한쪽으로 치우친 좌표). 보드 외곽을 부품 좌표와 같은 기준으로 받을 수 없다.

- **바꿀 것:** 외곽 bbox(min · max, 부품 좌표와 같은 기준)를 낸다.

- **위치:** get_volume_result 의 board 칸

- **확인:** get_volume_result 응답에 부품 좌표와 같은 기준의 외곽 bbox(min · max)가 있다.



#### OH-06 · 조회 도구 전부에 readOnlyHint

`P2` · 보낸 기록 없음



- **문제:** readOnlyHint 가 없어 11-01 에 ECAD 길이 약 48분 막혔다.

- **바꿀 것:** 조회 도구 전부(find_job · list_jobs · list_parts · get_board_layers · check_job_stackup · get_stackup · get_volume_result · get_odb_download · get_part_detail · find_nets · get_net 등)에 MCP 도구 표지 readOnlyHint: true 를 단다.

- **위치:** ODB 허브 MCP 도구 annotations

- **확인:** tools/list 의 조회 도구가 모두 readOnlyHint: true.

- **선례:** HWAX 게이트웨이 쪽 임시 대안 — 허용 목록에 조회 도구 6개를 넣어 풀어 둠

- **참고:** 게이트웨이 쪽 대안이 있어 급하지 않음. 6개 밖의 새 조회 도구가 생기면 다시 막힐 수 있다.



#### OD-8 · 부품 분류를 코어 part 와 잇기

`P3` · 보낸 기록 없음



- **문제:** 보드 부품 분류가 코어 part 타입과 이어지지 않는다.

- **바꿀 것:** 필요해지면 ODB 부품 분류(IC · Connector · Capacitor · Inductor · Interposer · Shield Can · SIM_Socket)를 코어 part(224종)에 잇고 받을 타입에 더한다.

- **위치:** ODB 허브 부품 분류 · 코어 받을 타입 목록

- **확인:** 부품 조회 응답에 코어 part key 가 있다.

- **참고:** 낮음.



#### OD-9 · (질문) renamed_from 으로 이름 바뀜 · 합침을 따라가는가

`P3` · 보낸 기록 없음



- **문제:** 보드의 project_key · model_code_key 는 승인 때 한 번 붙는다. 코어에서 key 가 바뀌거나 합쳐지면 보드 연결이 끊길 수 있다.

- **바꿀 것:** 개명 · 합침을 지금 어떻게 다루는지 답한다. 안 다루면 받기 때 행 봉투의 renamed_from 으로 붙은 key 를 옮긴다.

- **위치:** 코어 받기 행 봉투의 renamed_from · 보드의 project_key · model_code_key

- **확인:** 답을 받는다.



#### ODO-3 · find_job note 문장 중복 제거

`P3` · 보낸 기록 없음



- **문제:** X1 으로 찾은 응답 note 가 같은 문장을 두 번 싣는다.

- **바꿀 것:** note 를 한 번만 싣는다.

- **위치:** ODB 허브 find_job

- **확인:** X1 응답 note 가 한 번.



#### ODO-4 · (선택) 보드 응답에서 결함 쪽 다음 호출 안내

`P3` · 보낸 기록 없음



- **문제:** 보드에서 결함 · 시장 불량으로 가는 길이 응답에 없다.

- **바꿀 것:** 보드에 model_code_key 가 있으면 그것으로 결함을 찾는 다음 호출 안내(FailureTrace 모델코드 참조)를 note 로 준다. 데이터는 옮기지 않는다.

- **위치:** ODB 허브 find_job 보드 응답

- **확인:** model_code_key 있는 보드 응답에 결함 다음 호출 note.



#### OH-05 · 보드 단위 값(ODB 판 · 플레인 종류 · 동박 두께 · 높이)

`P3` · 보낸 기록 없음



- **문제:** 보드 단위로 있으면 좋은 값을 어느 도구도 내지 않아 심사가 추정한다. 표본 보드 두 장 모두 동박층이 다 SIGNAL 이고, 동박은 도금을 포함한 완성 두께뿐이다. 부품 높이는 get_volume_result 에 면마다 큰 부품 10개뿐이다(서버에는 다 있다 — missing_height=0). revision 은 설계 판이라 ODB++ 형식 판이 아니다.

- **바꿀 것:** ODB 에 있는 것만이라도 낸다 — 넷 총수(OH-01 이 풀리면 된다) · ODB++ 형식 판 · 넷 분류 · 동박층의 plane 구분 · 원판 동박 무게 · 부품 높이 전체. 없는 것은 없다고 도구 문서에 적는다.

- **위치:** ODB 허브 읽기 도구의 보드 단위 응답(get_volume_result 등) · 도구 문서

- **확인:** 보드 응답에 해당 칸이 있다. ODB 에 없어 못 내는 값은 도구 문서에 없다고 적혀 있다. 낼 수 있는 값과 없는 값을 나눈 회신을 받는다.

- **참고:** 낮음.



#### PA-09 · (질문) 위임 호출이 ODB 기록에 본인으로 남나

`P3` · 보낸 기록 없음



- **문제:** 10-28 부터 게이트웨이는 ODB 서비스 토큰을 주소가 아니라 Authorization 헤더로 싣는다(url=<base>/mcp + headers.Authorization). 사람별 호출은 그 사람 토큰으로 가는데, 바뀐 뒤에도 올린 사람 관측값이 anonymous 다. 기록에 누구로 남는지는 ODB 쪽에서만 볼 수 있다.

- **바꿀 것:** 게이트웨이가 사람별로 위임해 부르는 호출이 ODB 쪽 기록에 그 사람 이메일로 남는지 알려 달라.

- **위치:** ODB 허브 /mcp 호출 기록(사람별 토큰이 Authorization 헤더로 온다)

- **확인:** ODB 기록에 그 사람이 찍힌다.



#### PA-18 · (질문) IP 허용목록을 켤 계획

`P3` · 보낸 기록 없음



- **문제:** IP 허용목록을 켜는 날, HWAX 쪽 NO_PROXY 에 그쪽 서버 주소가 아직 없으면 HWAX 호출이 사내 프록시를 거쳐 들어가 403 이 난다(10-03 다른 파트너 앱에서 실제로 났다). 그래서 켜는 날을 미리 알아야 HWAX 쪽 설정을 먼저 바꿀 수 있다.

- **바꿀 것:** 미리 알려 달라.



### 3-7. ARP — 9건



시험 입력은 실제 이름 대신 자리표시로 적었다 — 과제 A · 그 과제코드 C1 · 과제 A 가 속한 프로젝트 P1(우선순위 P1 과 다른 자리표시). 실제 값은 운영 쪽이 따로 넘긴다.



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| AR-10 | ARP MCP 출력에 담당자 실명이 실림 | P1 | 보낸 기록 없음 |

| AR-9 | ARP basicInfo 수치 칸에 단위가 없음 | P2 | 보낸 기록 없음 |

| ARO-1 | 코어 태그 없는 ARP 모델 10개의 코어 후보 화면 | P2 | 보낸 기록 없음 |

| ARO-2 | (선택) 시험항목 · 관리 기준 · 부품 타입 받기 | P3 | 보낸 기록 없음 |

| ARO-3 | (선택) list_analyses 응답에 결함 쪽 다음 호출 안내 | P3 | 보낸 기록 없음 |

| PA-10 | (확인) ARP 서비스 토큰 · 싣는 모양 | P3 | 보낸 기록 없음 |

| PA-11 | (질문) ARP 위임 토큰의 업로드 권한 | P3 | 보낸 기록 없음 |

| PA-18 | (질문) IP 허용목록을 켤 계획 | P3 | 보낸 기록 없음 |

| Q-A1 | arp_upload_open 이 패널을 내는지 | P3 | 보낸 기록 없음 |



#### AR-10 · ARP MCP 출력에 담당자 실명이 실림

`P1` · 보낸 기록 없음



- **문제:** 10-30 디지털 워커 QA(시험 DW-06)에서 ARP MCP 출력의 partOwner 칸에 담당자 실명이 그대로 나왔다.

- **바꿀 것:** MCP 출력의 사람 칸을 원천에서 가린다. 가린 칸 목록을 알려 달라.

- **위치:** ARP MCP 출력 partOwner 등

- **확인:** 같은 조회에서 사람 칸이 원천 응답부터 가려져 있다.

- **참고:** 우리 쪽 중계에도 사람 칸 가림을 청했지만, 원천에서 빼는 것을 함께 청한다.



#### AR-9 · ARP basicInfo 수치 칸에 단위가 없음

`P2` · 보낸 기록 없음



- **문제:** 10-30 시험(디지털 워커 QA DW-06 · 챗 시험 OT-13)에서 ARP basicInfo 의 낙하 높이 152 를 챗이 mm 로 읽었다. 시험 조건은 cm 다.

- **바꿀 것:** basicInfo 수치 칸(낙하 높이 등)에 단위를 싣는다. 단위 칸 이름과 꼴을 알려 달라.

- **위치:** ARP basicInfo

- **확인:** ARP 응답의 낙하 높이 칸에 단위가 함께 나온다.

- **참고:** 고쳐지기 전까지는 우리 쪽 운영자 안내 한 줄로 메운다.



#### ARO-1 · 코어 태그 없는 ARP 모델 10개의 코어 후보 화면

`P2` · 보낸 기록 없음



- **문제:** ARP 모델 42개 중 10개가 코어 연결 태그가 없어 코어 단계에서 찾을 수 없다(linkedModels 32/42).

- **바꿀 것:** 태그 없는 모델마다 코어 후보(모델코드 · 개발모델 이름 일치)를 관리자 화면에 보인다(확정은 사람). 후보도 없는 수를 ontology_status 에 싣는다.

- **위치:** ARP ontology_status · 관리자 화면

- **확인:** ontology_status → linkedModels 가 42 에 가까워지거나 후보 없는 수가 따로 보임. 회귀 — AR-1 ~ AR-3 확인에 쓴 시험 입력(과제 A · 과제코드 C1 · 프로젝트 P1)으로 list_analyses 를 부르면 지금과 같은 matched_by 가 나온다(A → task_name · via task → project, C1 → task_code, P1 → project_key).

- **선례:** AR-1 ~ AR-3(코어 받기 · 과제 → 프로젝트 길 · 0건 이유) — 이미 들어왔다.

- **참고:** Q-1 — ARP 코어 토큰을 core:read 전용으로 바꿀 계획이 있는지(지금 넓은 범위). 바꾸면 운영 쪽이 허브에서 새 토큰을 받는다. 쓰지 않게 된 코어 토큰은 운영 쪽 회수 목록에 올리고 사용자가 허브 화면에서 회수한다. 태그 10개를 다는 일은 ARP 관리자 운영.



#### ARO-2 · (선택) 시험항목 · 관리 기준 · 부품 타입 받기

`P3` · 보낸 기록 없음



- **문제:** 받는 14 타입에 시험항목 · 관리 기준 · 부품이 없어 해석 항목을 그것들과 이을 수 없다.

- **바꿀 것:** 해석 상세구분을 잇고 싶으면 셋을 받는다. 쓰는 곳이 없으면 미룬다.

- **위치:** ARP 코어 받기 타입 설정

- **확인:** ontology_status 받는 타입에 셋이 보임.



#### ARO-3 · (선택) list_analyses 응답에 결함 쪽 다음 호출 안내

`P3` · 보낸 기록 없음



- **문제:** 해석 결과에서 결함 쪽으로 이어지는 안내가 없다.

- **바꿀 것:** 응답에 모델 key 가 있으면 같은 key 로 결함을 찾는 다음 호출을 note 로 준다.

- **위치:** ARP list_analyses

- **확인:** 모델 key 있는 응답에 결함 다음 호출 note.



#### PA-10 · (확인) ARP 서비스 토큰 · 싣는 모양

`P3` · 보낸 기록 없음



- **문제:** 10-27 확인으로 게이트웨이의 ARP 연결은 서비스 토큰을 싣고 정상으로 붙어 있다. 신원 없는 호출(도구 목록 등)은 서비스 토큰으로, 사람 호출은 그 사람 토큰(ARP /api/auth/sso, X-Heax-Client: gateway)으로 간다.

- **바꿀 것:** 서버 사이 /mcp 호출용 서비스 토큰과 싣는 모양이 지금 쓰는 그대로 맞는지 확인만 해 달라.

- **위치:** ARP /mcp(서비스 토큰) · /api/auth/sso

- **확인:** 맞다 · 아니다와 한 줄 까닭을 받는다.



#### PA-11 · (질문) ARP 위임 토큰의 업로드 권한

`P3` · 보낸 기록 없음



- **문제:** 10-16 에 사람별 호출이 그 사람 명의로 나가는 것은 확인했다. 업로드 권한은 ARP 쪽에서만 볼 수 있다.

- **바꿀 것:** 게이트웨이가 ARP /api/auth/sso 로 받아 쓰는 사람별 토큰이 업로드(arp_upload_*) 권한을 갖는지 알려 달라.

- **위치:** arp_upload_*

- **확인:** 맞다 · 아니다와 한 줄 까닭을 받는다.



#### PA-18 · (질문) IP 허용목록을 켤 계획

`P3` · 보낸 기록 없음



- **문제:** IP 허용목록을 켜는 날, HWAX 쪽 NO_PROXY 에 그쪽 서버 주소가 아직 없으면 HWAX 호출이 사내 프록시를 거쳐 들어가 403 이 난다(10-03 다른 파트너 앱에서 실제로 났다). 그래서 켜는 날을 미리 알아야 HWAX 쪽 설정을 먼저 바꿀 수 있다.

- **바꿀 것:** 미리 알려 달라.



#### Q-A1 · arp_upload_open 이 패널을 내는지

`P3` · 보낸 기록 없음



- **문제:** 포털 챗은 패널을 그릴 수 없는 턴에서는 패널 전용 도구를 모델에게서 숨기고, 그릴 수 있는 턴에서만 묶는다. arp_upload_open 이 패널을 여는 도구인지 알 수 없어, 숨길 도구로 둘지 패널 대상으로 둘지 정하지 못했다. 실제 호출로는 아직 재지 못했다.

- **바꿀 것:** 도구 정의에 _meta.ui.resourceUri(또는 옛 키 ui/resourceUri)가 있는지, ui:// 리소스를 내는지 알려 달라. 패널을 낸다면 다른 파트너 앱에 묻는 것과 같은 아래 여덟 물음도 번호마다 한두 줄로 답해 달라. Q-S1 ui/initialize 에 싣는 프로토콜 판과 호스트에 부르는 메서드 전부(후보 tools/call · resources/read · ui/open-link · ui/message · ui/update-model-context · ui/request-display-mode · notifications/message · ping). Q-S2 패널이 부르는 도구 이름 전부와 그중 되돌릴 수 없는 것(잡 제출 · 파일 등록 · 지우기). Q-S3 리소스 _meta.ui.csp · permissions 를 내는지, 패널이 바깥 주소(앱 서버 직접 fetch · CDN · 글꼴)에 닿아야 하는지. Q-S4 같은 출처 기능(localStorage · IndexedDB · 쿠키 · Service Worker · 팝업 · 내려받기)이 꼭 필요한지. Q-S5 패널이 읽는 결과 칸(content · structuredContent · 결과 _meta)과, 결과 _meta 에 사람 이름 · 계정 · 메일이 실리는지. Q-S6 패널 안 업로드가 있다면 조각 크기 · 한 파일 상한, 같은 조각 · 같은 커밋을 두 번 보낼 때 어떻게 되는지(멱등). Q-S7 리소스 HTML 의 크기(보통 · 최대)와 바뀌는 때(배포마다인지). Q-S8 도구 _meta.ui.visibility 를 쓰는지, 모델에게 숨길 패널 전용 도구가 무엇인지.

- **위치:** arp_upload_open

- **확인:** 답을 받는다 — 도구 정의에 _meta.ui.resourceUri 가 있는지 없는지와, 있으면 리소스 주소 꼴(ui://…). 패널이면 Q-S1 ~ Q-S8 의 답.

- **참고:** 답에 따라 우리 쪽에서 패널을 못 그리는 턴에 숨길 도구 목록에 넣거나 패널 대상으로 다룬다. 참고로 포털 호스트의 1단계 기본은 같은 출처 없는 샌드박스 · 문서 맨 앞 CSP(바깥 연결 기본 없음) · 그 앱 도구만 호출 · 패널 세션 첫 쓰기에 사람 확인 · ui/update-model-context · ui/message 는 받지 않음 · 패널 문서 2 MiB · 호출 인자 4 MiB · 세션 누적 32 MB 다.



### 3-8. FMEA — 8건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| FM-01 | FMEA 가 토큰 없이 initialize · tools/list 부터 401 | P2 | 보낸 기록 없음 |

| FM-02 | FMEA 도구 23개에 readOnlyHint 없음 | P2 | 보낸 기록 없음 |

| FM-03 | (질문) FMEA 서버 상시 운영 계획 | P2 | 보낸 기록 없음 |

| FMO-1 | check_server_setup 에 코어 받기 칸 | P2 | 보낸 기록 없음 |

| FMO-2 | 부품 key 로 사례 찾기 · hub_part 칸 | P2 | 보낸 기록 없음 |

| FM-04 | (질문) FMEA 토큰 수명 · 폐기 · 읽기 전용 토큰 | P3 | 보낸 기록 없음 |

| FM-05 | (질문) Host 허용목록에 게이트웨이 주소 · 포트 | P3 | 보낸 기록 없음 |

| FMO-3 | (선택) hub_* 칸 채움 수 읽기 도구 | P3 | 보낸 기록 없음 |



#### FM-01 · FMEA 가 토큰 없이 initialize · tools/list 부터 401

`P2` · 보낸 기록 없음



- **문제:** 토큰 없이 initialize 401, 토큰이 있어야 tools/list 23개. 그래서 목록 전용 FMEA 계정과 포털 계정이 따로 든다.

- **바꿀 것:** initialize · tools/list 를 열고 데이터를 내는 호출만 토큰을 요구한다.

- **위치:** FMEA MCP :5190

- **확인:** 목록 전용 계정 없이 list_auth: open 으로 23개가 보인다.

- **선례:** TestScope 와 MatNexus 는 목록을 열고 데이터를 내는 호출만 토큰을 요구한다(MatNexus 는 토큰 없이 initialize 200 · tools/list 114개).

- **참고:** 열리면 우리 쪽은 박스 설정을 list_auth: open 한 줄로 바꾸고 목록 전용 계정을 걷는다(우리 몫).



#### FM-02 · FMEA 도구 23개에 readOnlyHint 없음

`P2` · 보낸 기록 없음



- **문제:** 10-21 tools/list 23개 중 readOnlyHint 0개다. 게이트웨이는 힌트가 없는 도구를 읽기 전용 자격에서 read_only 로 거절하므로 전부 막힌다. 쓰는 도구는 add_material_baseline_overlay_tool · add_spec_overlay_tool 둘(비파괴 덮개 저장)뿐이다.

- **바꿀 것:** 읽는 도구에 readOnlyHint 를 단다.

- **위치:** FMEA MCP(:5190) 도구 정의의 annotations

- **확인:** 읽기 전용 자격에서 읽는 도구는 통과하고 쓰는 도구 둘만 막힌다.

- **참고:** 그동안 우리 쪽은 박스 connect 블록의 read_tools 를 지금 채울지, FM-02 를 기다릴지 정한다. 쓰기 도구 둘은 read_tools 에 넣지 않는다.



#### FM-03 · (질문) FMEA 서버 상시 운영 계획

`P2` · 보낸 기록 없음



- **문제:** 개인 PC 에서 도는 것으로 보이고(추정) 꺼지면 도구 23개가 사라진다.

- **바꿀 것:** 답.



#### FMO-1 · check_server_setup 에 코어 받기 칸

`P2` · 보낸 기록 없음



- **문제:** 코어 허브 기록으로는 FMEA 토큰이 매일 밤 받아 가지만(마지막 11-24 01:00), FMEA 도구(check_server_setup)로는 ok · 모드 · 지식 DB 경로만 보이고 받기 상태가 안 보인다.

- **바꿀 것:** check_server_setup 에 코어 받기 칸(타입별 건수 · 마지막 시각 · 결과)을 더한다.

- **위치:** FMEA check_server_setup

- **확인:** check_server_setup → 코어 받기 칸, 마지막 시각이 허브 기록과 같은 밤.



#### FMO-2 · 부품 key 로 사례 찾기 · hub_part 칸

`P2` · 보낸 기록 없음



- **문제:** find_cases_by_hub_name_tool 의 받는 이름에 부품이 없어 부품 key 로 사례를 찾을 수 없다(고장모드 key 101건 · 프로젝트 key 13건은 됨).

- **바꿀 것:** names 가 코어 부품 key 도 받게 하고 사례에 hub_part 칸을 둔다.

- **위치:** FMEA find_cases_by_hub_name_tool

- **확인:** find_cases_by_hub_name_tool(names=<부품 key>) → 사례 목록.

- **참고:** 들어오면 운영 박스 lookup 의 fmea 줄 types 에 part 를 더한다(우리 몫).



#### FM-04 · (질문) FMEA 토큰 수명 · 폐기 · 읽기 전용 토큰

`P3` · 보낸 기록 없음



- **문제:** 웹 /tokens 에서 사람이 발급하는 48자 토큰을 포털이 사람마다 보관한다.

- **바꿀 것:** FMEA 토큰의 수명 · 폐기 방법과 읽기 전용 토큰이 있는지 알려 달라.

- **위치:** FMEA 웹 /tokens

- **참고:** 포털은 등록한 토큰을 사람마다 보관하므로 수명과 폐기 방법이 운영 안내에 든다.



#### FM-05 · (질문) Host 허용목록에 게이트웨이 주소 · 포트

`P3` · 보낸 기록 없음



- **문제:** 게이트웨이는 프록시 없이 :5190 에 닿는다.

- **바꿀 것:** Host 허용목록을 쓴다면, 게이트웨이가 부르는 주소(<FMEA 서버>:5190)를 포트까지 그대로 넣었는지 확인해 달라.

- **위치:** FMEA MCP :5190 의 Host 허용목록



#### FMO-3 · (선택) hub_* 칸 채움 수 읽기 도구

`P3` · 보낸 기록 없음



- **문제:** 사내 사례 9,922건 중 hub_* 칸이 몇 건에 붙었는지 볼 도구가 없다.

- **바꿀 것:** 칸마다 채움 수를 돌려주는 읽기 도구를 둔다.

- **위치:** FMEA MCP

- **확인:** 도구 → hub_failure_mode · hub_mechanism · hub_stress · hub_model 칸별 건수.



### 3-9. PLM 검색 에이전트 — 7건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| PL-01 | deptGroup 품질 대분류 필터가 늘 0건 | P2 | 보낸 기록 없음 |

| PL-02 | 구어 질의에 엉뚱한 결과 · 낮은 신뢰 표지 없음 | P2 | 보낸 기록 없음 |

| PL-04 | 부품 변경 검증 내부 사례가 SW 건에 묻힘 | P3 | 보낸 기록 없음 |

| PL-05 | '유사도 순' 표기와 거리 순서 불일치 | P3 | 보낸 기록 없음 |

| PL-06 | 묶음 검색에 묶음 이름 없음 · 대표 건 메타 빔 | P3 | 보낸 기록 없음 |

| PL-07 | 외부 품질 DB 에 직접 항목 없음 표지 | P3 | 보낸 기록 없음 |

| PL-08 | 색인에 시험용 기록이 섞여 상위에 오름 | P3 | 보낸 기록 없음 |



#### PL-01 · deptGroup 품질 대분류 필터가 늘 0건

`P2` · 보낸 기록 없음



- **문제:** 10-25 '충전 중 발열' 에 품질 대분류를 걸면 candidates [], 그 부서 건이 '기타' 로 분류된다.

- **바꿀 것:** 그 품질 부서 이름 계열을 대분류로 매핑 · 재색인, check_plm_search_status 에 값별 문서 수.

- **위치:** 색인 deptGroup 매핑 · KPI 공통 분류

- **확인:** 품질 대분류로 걸어 0건이 아니고 상태 도구에 값별 수가 보인다(enrich=0).



#### PL-02 · 구어 질의에 엉뚱한 결과 · 낮은 신뢰 표지 없음

`P2` · 보낸 기록 없음



- **문제:** '폰이 부풀었다' 5건이 소리 · 덜컹 · 진동 건이고 스웰링 0건, 거리 0.2724~0.279, low_confidence · desc_match 칸 없음.

- **바꿀 것:** 구어 동의어(부풀다 → 스웰링) 사전, 핵심어 포함률로 low_confidence 와 현장 용어 예.

- **위치:** search_plm_issues

- **확인:** '폰이 부풀었다' 가 스웰링 건을 올리거나 low_confidence 를 단다.



#### PL-04 · 부품 변경 검증 내부 사례가 SW 건에 묻힘

`P3` · 보낸 기록 없음



- **문제:** 배터리 · 셀 공급사 교체 질의에서 전작 대표 6건 중 5건이 SW 건, 검출 시험 1위가 음성 비서 발화 시험(19건).

- **바꿀 것:** change_description HW 낱말로 다시 순위, 앞부분 일치는 낱말 경계, SW 부서 건은 아래로.

- **위치:** suggest_verification_items

- **확인:** HW 사례가 위로 온다.



#### PL-05 · '유사도 순' 표기와 거리 순서 불일치

`P3` · 보낸 기록 없음



- **문제:** 무관 결과(0.27대)가 관련 결과(0.30~0.34)보다 작아 '0.5 넘으면 관련 낮음' 안내와 맞지 않는다.

- **바꿀 것:** '종합 순위' 표기와 융합 점수, 0.5 문구 재조정.

- **위치:** search_plm_issues 결과의 순위 표기 · 거리 안내 문구

- **확인:** 결과에 '종합 순위' 표기와 융합 점수가 따로 보이고, 0.5 기준 문구가 실측에 맞게 바뀌어 있다.



#### PL-06 · 묶음 검색에 묶음 이름 없음 · 대표 건 메타 빔

`P3` · 보낸 기록 없음



- **문제:** 유형 1~4 번호만 있고 대표 건 등록일 · 부서가 '(없음)'.

- **바꿀 것:** 대표 대책문에서 유형 이름, 메타는 일반 검색 경로로.

- **위치:** search_plm_issues_clustered



#### PL-07 · 외부 품질 DB 에 직접 항목 없음 표지

`P3` · 보낸 기록 없음



- **문제:** 외부 5건 중 배터리 직접 항목 2건뿐인데 표지 없음.

- **바꿀 것:** no_direct_match 표시, 배터리 스웰링 · 가스 항목 보강.

- **위치:** External Quality Knowledge

- **확인:** 직접 항목이 없으면 no_direct_match 가 붙는다.



#### PL-08 · 색인에 시험용 기록이 섞여 상위에 오름

`P3` · 보낸 기록 없음



- **문제:** '충전 중 발열' 1위가 'Issue Manager 동작 테스트 폴더' 기록.

- **바꿀 것:** '동작 테스트' · '[개발자체 검증]' 폴더를 빼거나 내린다.

- **위치:** 색인 대상 필터

- **확인:** 1위가 시험용 기록이 아니다.



### 3-10. SmartTwin MCP · 해석 클러스터 — 4건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SM-01 | 직접 sbatch 도구 셋에 호출자 · 작업 폴더 확인이 없음 | P1 | 보낸 기록 없음 |

| SM-04 | SSO 꺼진 대시보드가 위임 PAT 를 보지 않아 모두 admin 으로 풀림 | P1 | 보낸 기록 없음 |

| SM-02 | SmartTwin MCP 도구에 readOnlyHint 표지 | P2 | 보낸 기록 없음 |

| SM-03 | 설치 스크립트 · 유닛 예시의 고정 경로와 wheel 해시 | P3 | 보낸 기록 없음 |



#### SM-01 · 직접 sbatch 도구 셋에 호출자 · 작업 폴더 확인이 없음

`P1` · 보낸 기록 없음



- **문제:** 1.1.0 판 세 도구가 PAT 를 보지 않고 subprocess.run(["sbatch", sbatch_path]) 로 서비스 계정 명의 sbatch 를 부른다. 게이트웨이에서 이 도구를 부를 수 있는 사람이면 누구든 GPU 잡을 낼 수 있고, 감사 원장과 잡 레지스트리에 호출자가 남지 않는다. work_dir 가 그 사람의 허용 루트 안인지 보지 않고 train.sbatch 를 쓴다(dry_run 에서도 쓴다). 세 도구는 운영 판에 그대로 들어가 있어 급하다. 운영 /mcp 는 루프백에서만 듣고 게이트웨이만 부르며 사람 확인은 도구가 PAT(위임 kst_)로 한다. 그래서 /mcp 자체 인증은 청하지 않는데, 이 판단은 'PAT 를 보지 않는 쓰기 도구가 없다' 는 전제 위에 있고 이 셋이 그 전제를 깬다.

- **바꿀 것:** sbatch 파일을 쓰기 전에 caller = job_helpers.caller_name() 을 받고 check_under(work_dir, work_roots(caller), kind="dir") 로 확인한다(StmcError 면 job_helpers.fail(str(e))). sbatch 호출에 --comment=stmc:{caller} 를 더한다(예시다 — 잡에 호출자를 남기는 다른 관례가 있으면 그쪽을 따른다). submit_distributed_train/1.1.0 에도 같은 꼴로 넣는다(147행 뒤, 158행). 가장 좋은 것은 backend_submit 길로 옮기는 것이다. submit_lsdyna_remote/1.1.0 은 원격 헤드에서 ssh 로 돌아 _shared · /api/me 를 못 쓰므로, 1.0.0 처럼 닫거나(같은 헤드에 submit_lsdyna_job 이 있다) ssh 로 넘기기 전에 서버 쪽(runner)에서 PAT 를 확인한다.

- **위치:** dashboard/smarttwin_mcp/tools/ 아래(origin/main ea9ebe5 기준) — train_pytorch_gpu/1.1.0/script.sh:117-127 · submit_distributed_train/1.1.0/script.sh:148-158 · submit_lsdyna_remote/1.1.0/script.sh:169-182

- **확인:** 남의 work_dir 을 주면 dry_run 에서도 거절되고, 잡 comment 에 호출자가 남는다.

- **선례:** 5aa61b6 이 같은 세 도구의 1.0.0 을 닫고 job_* 는 PAT 호출자의 잡만 다루게 했다. single_drop_simulation/1.1.2 · fullangle_drop_simulation/1.1.2 는 prepare_model_workdir(…, job_helpers.caller_name()) 로 작업 폴더를 work_roots 안으로 묶고 job_helpers.backend_submit 으로 낸다.

- **먼저:** SM-04(호출자가 바르게 풀려야 의미가 있다)

- **참고:** 운영 유지는 사용자 결정(11-24)이다.



#### SM-04 · SSO 꺼진 대시보드가 위임 PAT 를 보지 않아 모두 admin 으로 풀림

`P1` · 보낸 기록 없음



- **문제:** SSO_ENABLED=false 이면 어떤 PAT 든, 토큰이 없어도 admin 으로 풀린다. 운영 판에서 게이트웨이로 list_recent_jobs 를 부르니 caller 가 "admin" 이었다. 그래서 list_recent_jobs 의 내 잡 거르기도 사람별로 갈리지 않는다.

- **바꿀 것:** jwt_required · optional_jwt 에서 kst_ 확인을 SSO 꺼짐 확인보다 앞에 둔다. caller_identity 는 kst_ 를 요구하고, 전체 권한 · 익명 · root 류 이름을 거절한다. 대안은 /api/me 에 auth: pat|jwt|sso_off 칸을 더하는 것이다.

- **위치:** dashboard/backend_5010/middleware/jwt_middleware.py · tools/_shared/stmc_exec.py caller_identity

- **확인:** 위임 kst_ 로 부르면 그 사람 이름이 나온다. 머리가 없으면 웹은 그대로 admin 이고 MCP 는 거절된다. 틀린 kst_ 는 401 이다.

- **참고:** 그동안 운영 쪽은 포털 권한에서 SmartTwin 실행(MCP)을 이름을 적어 준 사람만 쓰게 묶었다(게이트웨이 grant_only plat:smarttwin-run). 웹 대시보드의 SSO 꺼짐 운영은 그대로 둔다. 고친 커밋이 오면 묶음을 푼다.



#### SM-02 · SmartTwin MCP 도구에 readOnlyHint 표지

`P2` · 보낸 기록 없음



- **문제:** 도구에 읽기 표지가 없다. 그래서 게이트웨이 읽기 목록을 박스 덧씌우기로 손수 메운다(read_tools.local.json 9 → 19, 11-24).

- **바꿀 것:** server.py 의 175 catalog_search · 185 catalog_describe · 194 catalog_versions 는 annotations readOnlyHint: true, 200 catalog_run · 210 catalog_reload 는 false 로 단다. 241 _register_direct 는 meta 의 mode-read 태그를 따른다(모든 meta.yaml 을 세면 mode-read 41 · mode-own 75).

- **위치:** src/smarttwin_mcp/server.py:175-241(fastmcp annotations)

- **확인:** tools/list 의 annotations 에 readOnlyHint 가 붙고, 게이트웨이 routine_read 가 덧씌우기 없이 같은 수를 본다.

- **참고:** fastmcp==3.3.1 의 tool(annotations=…) 가 dict 를 받는지 확인해 달라. 안 받으면 mcp.types.ToolAnnotations(readOnlyHint=…) 로 넘긴다.



#### SM-03 · 설치 스크립트 · 유닛 예시의 고정 경로와 wheel 해시

`P3` · 보낸 기록 없음



- **문제:** 설치 스크립트와 서비스 예시가 리포 배치를 박아 두었다. 오프라인 wheel 의 해시가 git 에 없다.

- **바꿀 것:** 유닛 예시의 네 곳(21 · 22 · 24 · 29행)을 __APP_HOME__ 하나로 묶고, 설치기는 APP_HOME="${STMC_APP_HOME:-$SCRIPT_DIR}" 로 바꾼다. offline_packages_2404/python_wheels/smarttwin_mcp/python3.12/SHA256SUMS(파일 이름 + sha256)를 git 에 둔다. 바퀴 파일은 git 밖이어도 된다.

- **위치:** install_offline.sh:16,60-62 · smarttwin-mcp.service.example:21-29

- **확인:** 다른 경로에 풀어도 설치가 되고, sha256sum -c 가 통과한다.



### 3-11. ComponentCore — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| CCO-1 | ComponentCore 에 sp_core 소스(코어 개발모델 · 부품) 등록 | P1 | 보낸 기록 없음 |

| CCO-2 | 데이터 소스 목록 · 마지막 결과를 위임 토큰에도 열기 | P2 | 보낸 기록 없음 |

| DP-10 | (질문) componentcore 계정이 SSO 클레임을 채우나 | P3 | 보낸 기록 없음 |



#### CCO-1 · ComponentCore 에 sp_core 소스(코어 개발모델 · 부품) 등록

`P1` · 보낸 기록 없음



- **문제:** 안내에는 「SP 에서 받은 모델 · 부품」 이 있어야 한다는데 코어 타입 0 · 객체 5(부품 0)다. 허브에 ComponentCore 토큰이 없다.

- **바꿀 것:** ComponentCore 관리자가 sp_core 소스를 등록한다. 주소는 운영 쪽이 알리고 토큰은 운영 쪽 사용자가 허브에서 발급을 정한다.

- **위치:** ComponentCore 데이터 소스 설정

- **확인:** componentcore_graph_overview → 코어 타입이 보임.

- **참고:** Q-1 — 받은 뒤 기본 관계(ontology_link_defaults)를 ComponentCore 쪽이 할지 운영 쪽이 사용자 결정 뒤 할지.



#### CCO-2 · 데이터 소스 목록 · 마지막 결과를 위임 토큰에도 열기

`P2` · 보낸 기록 없음



- **문제:** componentcore_datasources_list 가 포털 위임 토큰으로는 관리자 기능이라며 거절한다(CCR-AUTH-0104).

- **바꿀 것:** 소스 목록 · 마지막 실행 결과 읽기는 위임 토큰에도 연다(설정 값 · 토큰 칸은 뺀다).

- **위치:** ComponentCore componentcore_datasources_list 권한

- **확인:** componentcore_datasources_list(위임 토큰) → 소스 목록과 마지막 결과.



#### DP-10 · (질문) componentcore 계정이 SSO 클레임을 채우나

`P3` · 보낸 기록 없음



- **문제:** whoami display_name 이 이메일 앞부분, memberships [] (10-25). 부서 허브는 실명.

- **바꿀 것:** componentcore 계정이 다른 허브처럼 SSO 클레임으로 계정 정보를 채우는지 답해 달라. 소속이 필요한 쓰기는 거절될 수 있다(추정).

- **위치:** componentcore whoami(display_name · memberships)



### 3-12. GPU 클러스터 운영 — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SC-1 | CPU 렌더 잡이 낙하 해석 잡과 노드를 함께 써도 되는지 | P3 | 보낸 기록 없음 |

| SC-2 | 렌더용 파티션 · 시간대 · 코어 상한 | P3 | 보낸 기록 없음 |

| SC-3 | 렌더 잡 계정 · QoS · 우선순위 구분 | P3 | 보낸 기록 없음 |



#### SC-1 · CPU 렌더 잡이 낙하 해석 잡과 노드를 함께 써도 되는지

`P3` · 보낸 기록 없음



- **문제:** CPU 파티션 넷(346대)이 노드당 128코어 · OverSubscribe=NO 이고 11-01 11시 무렵 거의 다 할당 중이었다.

- **바꿀 것:** 같은 파티션 · 노드를 함께 써도 되는지 알려 달라.

- **위치:** GPU 클러스터 CPU 파티션

- **확인:** 답을 받는다.



#### SC-2 · 렌더용 파티션 · 시간대 · 코어 상한

`P3` · 보낸 기록 없음



- **문제:** 렌더 잡 기본 요청을 정할 값이 없다.

- **바꿀 것:** 안 되면 쓸 파티션 · 시간대 · 코어 상한을 알려 달라.

- **위치:** GPU 클러스터 CPU 파티션

- **확인:** 답을 받는다.

- **먼저:** SC-1



#### SC-3 · 렌더 잡 계정 · QoS · 우선순위 구분

`P3` · 보낸 기록 없음



- **문제:** 해석 잡과 우선순위를 다투지 않게 할 구분이 정해지지 않았다.

- **바꿀 것:** 따로 쓸 계정 · QoS 가 필요한지 알려 달라.

- **위치:** GPU 클러스터 계정 · QoS

- **확인:** 답을 받는다.



### 3-13. MatNexus — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| MNO-1 | MatNexus 코어 받기 소스 등록 | P1 | 보낸 기록 없음 |

| FM-06 | (질문) MatNexus /api/auth/me 로 토큰 확인 가능? | P3 | 보낸 기록 없음 |

| MNO-2 | (선택) 등록 뒤 match_sp_core 후보 확정 | P3 | 보낸 기록 없음 |



#### MNO-1 · MatNexus 코어 받기 소스 등록

`P1` · 보낸 기록 없음



- **문제:** MatNexus 가 코어를 받지 않는다. 허브에 MatNexus 용 토큰 둘이 있지만 한 번도 쓰이지 않았다. 반대 방향(코어 물성 278건의 matnexus_key)은 표본 key · 값 수 87 = 87 로 맞는다.

- **바꿀 것:** MatNexus 관리자가 화면에서 SP 코어 소스(주소 · 토큰)를 등록한다. 주소는 운영 쪽이 따로 알리고 토큰은 허브에 이미 발급된 것 중 하나를 쓴다(값은 문서에 적지 않음).

- **위치:** MatNexus 관리자 화면 · sp_core_status

- **확인:** sp_core_status → configured true · 타입 수 · 마지막 결과 ok.

- **참고:** Q-1 — 발급된 둘(넓은 범위 · core:read 전용) 중 어느 것을 쓸지, 새로 받을지 정해 달라. 받기 소스가 생기면 core:read 전용 쪽을 쓰고 넓은 쪽만 회수해도 된다. 쓰지 않을 쪽은 운영 쪽 사용자가 허브 화면에서 회수한다.



#### FM-06 · (질문) MatNexus /api/auth/me 로 토큰 확인 가능?

`P3` · 보낸 기록 없음



- **문제:** 지금 MatNexus 연결은 verify: none. /api/auth/me 응답 모양 미확인.

- **바꿀 것:** /api/auth/me 가 유효 토큰에 200, 틀린 토큰에 401 을 주는지와 응답 모양을 알려 달라. 그렇다면 우리 쪽이 토큰 등록 때 이 주소로 확인하게 바꾼다.

- **위치:** MatNexus :8010/api/auth/me

- **확인:** 유효 토큰 200 · 틀린 토큰 401 여부와 응답 모양을 답으로 받는다.



#### MNO-2 · (선택) 등록 뒤 match_sp_core 후보 확정

`P3` · 보낸 기록 없음



- **문제:** 소스 등록 뒤 잇기 후보를 사람이 확인해야 한다.

- **바꿀 것:** match_sp_core 후보를 화면에서 확정한다. 운영 쪽은 확정 뒤 links 수로 확인한다.

- **위치:** MatNexus match_sp_core · 화면

- **확인:** sp_core_status links 수가 0 보다 큼.

- **먼저:** MNO-1



### 3-14. SIREN — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| SRO-1 | 사례 추출 · 확정 때 부품 · 프로젝트 코어 key 저장 | P1 | 보낸 기록 없음 |

| SRO-2 | 사례에 고장모드 칸 · 코어 고장모드 후보 제안 | P2 | 보낸 기록 없음 |

| SRO-3 | siren_get_case · siren_search_cases 응답과 검색에 코어 key | P2 | 보낸 기록 없음 |



#### SRO-1 · 사례 추출 · 확정 때 부품 · 프로젝트 코어 key 저장

`P1` · 보낸 기록 없음



- **문제:** SIREN 은 코어를 받지 않고 사례에 코어 key 가 없다. 부품은 자유 글, 프로젝트는 목록, 확정은 34,679건 중 632건(1.8%)이라 읽을 때마다 이름을 맞춰야 한다.

- **바꿀 것:** 추출 · 확정 때 부품 · 프로젝트를 코어로 풀어 key(type_slug · key)를 함께 저장한다. 못 푼 이름은 그대로 두고 「풀지 못함」 으로 표시한다.

- **위치:** SIREN 사례 추출 · 확정

- **확인:** 확정 사례 하나 → 부품 · 프로젝트 key 가 응답에 있음.

- **참고:** Q-1 — 코어 자료를 허브 읽기 토큰으로 받을지 운영 게이트웨이 ontology_lookup 을 부를지(토큰이 필요하면 운영 쪽 사용자가 허브에서 발급을 정한다). 운영 박스 SIREN 페르소나에 「이름 → 코어 풀기」 단계를 넣는 일은 우리 몫이고, 이 요청 뒤에 사용자 결정으로 한다.



#### SRO-2 · 사례에 고장모드 칸 · 코어 고장모드 후보 제안

`P2` · 보낸 기록 없음



- **문제:** 사례에 고장모드 칸이 없다(표본 낱말은 코어 판별 패턴에만 걸림).

- **바꿀 것:** 사례에 고장모드 칸을 두고 코어 고장모드 key 를 후보로 제안한다(확정은 사람).

- **위치:** SIREN 사례 스키마

- **확인:** 사례 응답에 고장모드 칸과 후보 key.

- **먼저:** SRO-1



#### SRO-3 · siren_get_case · siren_search_cases 응답과 검색에 코어 key

`P2` · 보낸 기록 없음



- **문제:** 사례 조회 응답에 코어 key 가 없고 코어 key 로 찾을 수 없다.

- **바꿀 것:** SRO-1 의 key 를 응답에 싣고 siren_search_cases 가 코어 key 로도 찾게 한다.

- **위치:** SIREN siren_get_case · siren_search_cases

- **확인:** siren_search_cases(core_type=part, core_key=<부품 key>) → 그 부품 사례.

- **먼저:** SRO-1



### 3-15. 허브 관리자 — FailureTrace — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| DHO-2 | FailureTrace PLM 문제점에 과제 · 모델코드 참조 유도 | P1 | 보낸 기록 없음 |

| DHO-3 | FailureTrace 고장모드 낱말 → 참조 대응 다시 돌리기(약 18.6만 건) | P1 | 보낸 기록 없음 |

| DHO-4 | FailureTrace 자기소개 채우기 | P3 | 보낸 기록 없음 |



#### DHO-2 · FailureTrace PLM 문제점에 과제 · 모델코드 참조 유도

`P1` · 보낸 기록 없음



- **문제:** PLM 문제점 426,958건에 개발모델 참조(약 71%)는 있으나 과제 · 모델코드 참조 칸이 없다(과제는 폴더 글자뿐).

- **바꿀 것:** 이미 있는 개발모델 참조로 코어 개발모델 → 과제 · 모델코드를 유도해 참조로 단다(폴더 글자를 다시 읽지 않는다).

- **위치:** FailureTrace PLM 문제점 타입

- **확인:** 문제점 하나 → 과제 · 모델코드 참조.

- **먼저:** Datahub 플랫폼 쪽 변경 — 허브가 과제 · 개발모델 · 모델코드도 관계(또는 참조 칸)로 받아야 한다. 지금은 이 셋의 관계를 받지 않아 허브 안에서 과제 ↔ 모델 ↔ 모델코드를 걸을 수 없다. 이 변경은 Datahub 플랫폼 쪽에 따로 청했다.



#### DHO-3 · FailureTrace 고장모드 낱말 → 참조 대응 다시 돌리기(약 18.6만 건)

`P1` · 보낸 기록 없음



- **문제:** 고장모드 낱말이 약 333,162건에 걸렸는데 실제 참조는 146,951건이라 약 18.6만 건이 낱말만 걸렸다(고장모드 참조 146,530 · 34.3% · 107종).

- **바꿀 것:** 낱말 → 고장모드 대응 규칙을 다시 돌리고, 못 이은 까닭(여러 고장모드에 걸림 · 대응 없음)을 건수로 보인다.

- **위치:** FailureTrace 고장모드 태깅 규칙

- **확인:** 고장모드 참조 수가 146,530 보다 늘고, 못 이은 까닭 건수가 보임.



#### DHO-4 · FailureTrace 자기소개 채우기

`P3` · 보낸 기록 없음



- **문제:** FailureTrace 자기소개가 비어 있다(게이트웨이 · 웹 챗이 이 글로 허브를 고른다).

- **바꿀 것:** 받는 코어 타입 · 기록 타입 · 잇는 길을 적는다.

- **위치:** FailureTrace platform_profile

- **확인:** platform_profile 에 소개 글.



### 3-16. 허브 관리자 — MountSol — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| DHO-7 | MountSol 사례 모델 글자 · 휨 측정 회차를 코어로 풀기 | P2 | 보낸 기록 없음 |

| DHO-8 | MountSol 소스 목록 · 마지막 결과를 위임 토큰에도 | P2 | 보낸 기록 없음 |

| DHO-9 | (선택) MountSol 사례를 굵은 부품 노드보다 좁게 잇는 규칙 | P3 | 보낸 기록 없음 |



#### DHO-7 · MountSol 사례 모델 글자 · 휨 측정 회차를 코어로 풀기

`P2` · 보낸 기록 없음



- **문제:** MountSol 사례 978건의 모델 · 단계가 글자뿐이고, 휨 측정 114건의 모델코드 참조가 0이다.

- **바꿀 것:** 사례의 모델 글자를 코어 개발모델로, 휨 측정 회차를 모델코드로 푼다.

- **위치:** MountSol Datahub 사례 · 휨 측정

- **확인:** 휨 측정 모델코드 참조 0 → 늘음, 사례 → 개발모델 참조가 생김.



#### DHO-8 · MountSol 소스 목록 · 마지막 결과를 위임 토큰에도

`P2` · 보낸 기록 없음



- **문제:** MountSol 수신 상태를 위임 토큰으로 볼 수 없다(소스 목록 403 APP-AUTH-0103). 다른 세 허브는 보인다.

- **바꿀 것:** 소스 목록 · 마지막 결과 읽기를 위임 토큰에도 열거나 다른 셋과 같은 권한으로 맞춘다.

- **위치:** MountSol datasources_list 권한

- **확인:** MountSol 소스 목록이 위임 토큰으로 보임.



#### DHO-9 · (선택) MountSol 사례를 굵은 부품 노드보다 좁게 잇는 규칙

`P3` · 보낸 기록 없음



- **문제:** 사례 하나를 걸면 코어 쪽 부품 노드 하나(선 2,441개)에만 이어지고 고장모드 · 모델 · 과제 선이 없다.

- **바꿀 것:** 사례를 그 노드보다 좁은 부품 · 고장모드로 잇는 규칙을 둔다.

- **위치:** MountSol 사례 관계 규칙

- **확인:** 사례 하나 → 좁은 부품 · 고장모드 선.



### 3-17. 허브 관리자 — NCDev — 3건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| DHO-10 | NCDev 기록 6 타입 적재 · 문서 모델 글자 풀기 | P2 | 보낸 기록 없음 |

| DHO-11 | NCDev 자기소개에 새 타입 17개 · 소스 이름 맞추기 | P2 | 보낸 기록 없음 |

| DHO-12 | (선택) NCDev 문서 태깅 규칙 다시 돌리기 | P3 | 보낸 기록 없음 |



#### DHO-10 · NCDev 기록 6 타입 적재 · 문서 모델 글자 풀기

`P2` · 보낸 기록 없음



- **문제:** NCDev 기록 6 타입(이슈 · 시험 결과 · 통신사 요구 · 인증 항목 · BOM 변경 · 부품 승인)이 0건이고, 문서 2,931 중 모델 참조는 1건(모델 글자 1,813)이다.

- **바꿀 것:** 문서에서 뽑은 기록을 적재하고 모델 글자를 코어 개발모델로 푼다.

- **위치:** NCDev Datahub 기록 타입 · 문서

- **확인:** 근거 문서 → 모델 참조 수가 1 보다 늘고 기록 타입 수가 0 보다 큼.



#### DHO-11 · NCDev 자기소개에 새 타입 17개 · 소스 이름 맞추기

`P2` · 보낸 기록 없음



- **문제:** NCDev 자기소개에 새 타입 17개가 빠졌고, 소스 이름이 다른 셋과 달리 「hub」 다.

- **바꿀 것:** 자기소개를 고치고, 소스 이름을 맞출지 정한다(바꾸면 다시 받기가 필요한지 함께 알린다).

- **위치:** NCDev platform_profile · 코어 소스 이름

- **확인:** platform_profile 에 새 타입 17개, 소스 이름 결정 회신.



#### DHO-12 · (선택) NCDev 문서 태깅 규칙 다시 돌리기

`P3` · 보낸 기록 없음



- **문제:** NCDev 문서의 코어 관계가 3% 밑이다.

- **바꿀 것:** 태깅 규칙을 다시 돌린다.

- **위치:** NCDev 문서 태깅

- **확인:** 문서 코어 관계 비율이 3% 보다 늘음.



### 3-18. TestScope — 2건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| PA-18 | (질문) IP 허용목록을 켤 계획 | P3 | 보낸 기록 없음 |

| TS-1 | TestScope 도구 표지 없음 · 쓰기 도구 일부가 HWAX 쓰기 목록 밖 | P3 | 보낸 기록 없음 |



#### PA-18 · (질문) IP 허용목록을 켤 계획

`P3` · 보낸 기록 없음



- **문제:** IP 허용목록을 켜는 날, HWAX 쪽 NO_PROXY 에 그쪽 서버 주소가 아직 없으면 HWAX 호출이 사내 프록시를 거쳐 들어가 403 이 난다(10-03 다른 파트너 앱에서 실제로 났다). 그래서 켜는 날을 미리 알아야 HWAX 쪽 설정을 먼저 바꿀 수 있다.

- **바꿀 것:** 미리 알려 달라.



#### TS-1 · TestScope 도구 표지 없음 · 쓰기 도구 일부가 HWAX 쓰기 목록 밖

`P3` · 보낸 기록 없음



- **문제:** 도구에 annotations 가 없다. 그래서 HWAX 게이트웨이는 쓰기 도구를 따로 적은 목록(46개)으로 가리는데, 쓰기 도구 여섯이 그 목록에 없고 읽기 도구 import_columns 가 들어 있다(참고).

- **바꿀 것:** readOnlyHint · destructiveHint 를 붙인다.

- **위치:** TestScope MCP 도구 정의(annotations)

- **확인:** tools/list annotations 로 쓰기 51개가 갈린다.

- **참고:** 쓰기로 다룰 도구 51개는 HWAX 게이트웨이 쓰기 목록 46개에서 import_columns(읽기)를 빼고 admin_action · detach_term_reference · extract_document_images · link_series · promote_free_spec · suggest_property_link 를 더한 것이다.



### 3-19. 허브 관리자 — CAE그룹 — 2건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| DHO-5 | CAE그룹 기록 타입(해석 결과 · 측정) 적재 | P2 | 보낸 기록 없음 |

| DHO-6 | CAE그룹 근거 문서 → 모델 참조 · 기준 문장 → 관리 기준 대응 | P2 | 보낸 기록 없음 |



#### DHO-5 · CAE그룹 기록 타입(해석 결과 · 측정) 적재

`P2` · 보낸 기록 없음



- **문제:** CAE그룹 기록 타입(해석 결과 · 측정 · 규칙 점검 · 해석 묶음)이 0건이다.

- **바꿀 것:** 해석 결과 · 측정 기록을 적재한다(원천 · 주기는 CAE그룹 관리자).

- **위치:** CAE그룹 Datahub 기록 타입

- **확인:** objects_census 에서 기록 타입 수가 0 보다 큼.

- **참고:** 10-29 HWAX 쪽 시험에서도 해석 기록 타입이 비어, 시험한 고장모드(코어 key 로 고름)에 이어진 해석 기록이 0건이었다. 적재 계획(할지 · 언제 · 어떤 기록을)과 일정을 알려 달라.



#### DHO-6 · CAE그룹 근거 문서 → 모델 참조 · 기준 문장 → 관리 기준 대응

`P2` · 보낸 기록 없음



- **문제:** 근거 문서 → 모델 참조가 0(모델 글자 1,503건)이고, 기준 문장 1,253건 중 코어 관리 기준에 이어진 것은 9건이다.

- **바꿀 것:** 모델 글자를 코어 개발모델로 풀어 참조로 달고, 기준 문장 → 관리 기준 대응을 다시 돌린다.

- **위치:** CAE그룹 Datahub 근거 문서 · 기준 문장

- **확인:** 근거 문서 → 모델 참조 수가 0 보다 늘고 관리 기준 대응이 9 보다 늘음.



### 3-20. SimEngBay — 1건



| ID | 제목 | 우선 | 상태 |

|---|---|---|---|

| PA-08 | (선택) SimEngBay 코어 받기 | P3 | 보낸 기록 없음 |



#### PA-08 · (선택) SimEngBay 코어 받기

`P3` · 보낸 기록 없음



- **문제:** :3070 /api/core 404, 도구 26개에 datasource · core 없음(10-27).

- **바꿀 것:** 필요해지면 붙이고, Component Core 연결로 충분한지 먼저 알린다.

- **위치:** SimEngBay 코어 받기(:3070 /api/core)



---



## 4. 사용자 결정이 먼저인 것 (보내지 않음)



결정이 나면 해당 항목을 1절 · 3절로 옮겨 보냅니다. 운영 쪽(우리)이 답하거나 할 일도 여기에 두었습니다.



| ID | 제목 | 받을 곳 | 기다리는 결정 · 근거 |

|---|---|---|---|

| D-01 | AIDataHub 삭제 API 를 nginx 에서 막을지 | 운영 쪽(우리) | R-01 이 AIDataHub HEAD d59cf11 에서 아직 열림(agents.py:208 인증 없음). |

| R-3 | 동시 2건 한도 | SIREN | 19 미발송 · 사용자 보류. 메모리 — 보내기 전에 ④ · R-3 를 다시 써야 한다고 적음. |

| SF-6 | uv_mask_from_region 실제 UV 창의 출처 | StepForge (HEAXHub) | checklist.md — '[ ] StepForge 2차 물음 — SF-10 테이프 이름 꼴 · SF-6 인쇄 도면 그림(받은 편지함 물음 9 · 10) — 운영 박스에서 볼 수 없어 과제 자료를 아는 사람에게 넘김(사용자 경유, SS-11)'. context-notes.md SS-11 같은 내용. |

| SG-04(다시) | 제품 해석이 다른 프로젝트 제품 코드로 풀림 | SignalForge | 임시 주의 칸은 SignalForge ec40075 로 들어옴. 제품 행을 나눌지(안 A/B/C) 데이터 결정은 사용자 몫으로 남음(포털 docs/request-1029/signalforge-sg04-question.md). |

| 19-SIREN-1 | SIREN 쪽 물음 ①~⑦ 답 · 시험 날짜 | SIREN | 00-INDEX 의 19 행 「아직 보내지 않음」. 메모리 project-siren-connect — 사용자가 보류(11-04 밤 결정), 그 뒤에도 보내지 않음. |

| AD-05 | 빈 전문가 dynaforge-report 지우기 | AIDataHub | request-1030/checklist.md '[ ] AD-05/06 dev 지우기 — 사용자가 apply.sh(C-17) → OB-73 → 병합 → OB-87'. gitlog HWAXPortal 3ef678a4 'AD-05/06 dev 지우기는 사용자 몫'. 새 껍데기 방지는 AIDataHub 6b0d06c(strict 검증)로 끝. |

| AD-06 | kooremapper-modelmeta 데모 카드 3장 · 행 지우기 | AIDataHub | request-1030/checklist.md '[ ] AD-05/06 dev 지우기(사용자 apply.sh, C-17)'. KooRemapper 6d63038b 가 운영 몫 순서(레코드 3건 → 행)를 적음(gitlog). |

| CDR-PLM-ID | PLM 호출을 사람 본인 신원으로 · 공유 PLM 호출 한도 | 여러 저장소 공통 | §4 보류에 사용자 보류로 적힘 · 10-25 사용자 결정 기록에서도 보류(ON HOLD) 그대로 · 그 뒤 결정 기록 없음. |

| D-3 | 쓰지 않는 코어 토큰 회수(목록은 만듦, 회수는 사용자가 허브 화면에서) | 운영 쪽(우리) | 감사서 D-3 「정함 — 회수 목록만(11-24)」 · §4-1 목록(11-24 16:18 core_status consumers). 회수 실행 기록 없음. |

| DF-REPLY-4 | DynaForge 답신 §4 — 요청 쪽(리포트를 만드는 쪽)이 줄 꼴 · 표본 · 기준값 10가지 | 운영 쪽(우리) | 개발 쪽이 운영 쪽에 되물은 10가지(꼴 · 표본 · 기준값). 누가 무엇을 줄지 정한 기록 없음 — 보낼 것이 아니라 우리가 답할 것. |

| HP-63 | AIDataHub 조각 목록이 11-08 뒤로 안 나옴 | 포털 (HWAXPortal) | recv/request-1111 답 — dev cron 은 사용자가 거는 몫(docs/aidh-parts-sync/checklist.md:8). drive-drift aidh 와 손 조각 목록(11-11)은 끝남. |

| KR-20 | (질문) 틀린 주응력을 쓴 기존 결과 재실행 범위 | KooRemapper | KooRemapper report.md:60 권장 — 주응력(min/maxPrincipalStress)을 소비한 결과 중 퇴행 고유값 요소가 있던 것만 다시 돌림(prestress 재실행은 싸다). 범위는 사용자 결정으로 남김. |

| KR-VERIFY-1122 | DynaForge 운영 반영 + 검증런(미룬 결함 3차 1~7판 · DF 2차 ①~⑥) | 운영 쪽(우리) | 개발 쪽이 운영 쪽에 청한 검증런. 운영 노드 반영은 교체 시점(잡 0 · 사용자 OK)이 먼저다. 검증런 결과를 넘긴 기록 없음. |

| MCP-PATHS-P1 | 포털 MCP 직결 경로의 정책 — 게이트웨이 우회 · Origin 머리 · 토큰 없는 요청 | 포털 (HWAXPortal) | dev 쪽 문서에 언급 0건(박스 docs git grep). DATAHUB-MOVE.md:117 은 데이터허브 운영 안내로 'MCP 는 정책 검토 전까지 게이트웨이로만 쓴다' 고 적었는데, 11-13 사용자 지시('DynaForge 처럼')로 연 직결 여덟에 데이터허브 셋이 들어 있다. |

| MEMORY-4 | MCP 정책 준비 빈틈 1–6 | 게이트웨이 (HWAXMcpGateway) | 11-05 에 사용자가 요청서는 '나중에' 쓰자고 했다. 11-09 에는 포털 읽기/쓰기 분리도 나중에 하기로 했다. recv 에 요청 흔적이 없다. |

| MEMORY-8 | StepForge 직접 MCP 경로가 게이트웨이 전용 규칙을 비켜감 | HEAXHub 공통 · MaterialTwin | 메모(11-13)에 '닫는 것은 사용자 몫' 으로 적혀 있다. 직접 /apps/step_forge/mcp 길은 아무 허브 PAT 로 forward_auth 를 지나고, /apps/kooremapper_mcp/mcp 에는 forward_auth 가 없다. recv 에 요청 흔적이 없다. |

| MEMORY-18 | StepForge SSO 비밀 줄 넣기와 SSO 주소 켜기 | 운영 쪽(우리) | 메모에 '사용자가 비밀을 만들어 두 파일(운영 포털 박스 provision.env · 운영 노드 secrets.env)에 덧붙인다 — 그 뒤 STEPFORGE_SSO_URL 줄을 더하고 update-collab 을 돈다' 로 남아 있다. 11-19 교체 뒤 관측에서도 운영 노드 secrets.env 에 SSO 줄이 없었다(메모 forge-prod-plan). 같은 비밀을 기다리는 UD-SSOSECRET 과 함께 정한다. |

| MW-04 | 사람별 위임 없이 서비스 계정 하나로 불림 | MXWhitePaper | MXWhitePaper git log · context-notes 에 MW-04 0건. 요청서가 MW-10(D7) 결정을 먼저로 둠. |

| MW-10 | (결정 D7) restricted 2건 · 사람별 위임 · 전환 점검표 | MXWhitePaper | 이 배치에서 D7 결정 기록을 못 찾음. MXWP 쪽 커밋 0. |

| PA-03 | TestScope 사람별 위임 켜기 마지막 단계 | TestScope | memory(TestScope 연결 11-13): 박스는 11-13 내장 사람별 토큰 백엔드로 붙임(100 도구, SSO 시크릿 설정이 비어 토큰 방식). TestScope v0.65.2 에 /api/auth/sso 가 있어 PA-03 · OB-86 은 낡음. SSO 전환은 대기. |

| PL-03 | 검색 결과 제목의 개인정보 가림 | PLM 검색 에이전트 | 00-INDEX.md: 보내기 전 사용자 결정 목록(PL-03 · D5), PLM 보류 범위에 넣을지도 사용자 판단. 90-OURS OB-07 결정 기록 없음. |

| PL-10 | 챗으로 나가는 응답의 개인정보 가림 범위(결정 D5) | PLM 검색 에이전트 | 90-OURS-box-todo.md OB-07 결정 행 열려 있음(권고 (가)). |

| R-1 | readOnlyHint · idempotentHint | SIREN | 19 미발송 · 사용자 보류(00-INDEX, 메모리). |

| R-2 | 토큰 확인(initialize 401 또는 주인 조회) | SIREN | 19 미발송 · 사용자 보류. |

| R-4 | 최종 오류 꼴 · Retry-After 위치 · 하루 2,000 셈법 | SIREN | 19 미발송 · 사용자 보류. 11-05 에 다른 등록자가 약 2,350번 부름(메모리). |

| R-6 | 사양 차이(siren_ 접두 · 단건 get · 문서 도구 · trust 문자열 · 토큰 접두) | SIREN | 19 미발송 · 사용자 보류. |

| R-7 | 도구 설명에 신뢰 규칙 | SIREN | 19 미발송 · 사용자 보류. |

| R-8 | 인자 12개 설명 | SIREN | 19 미발송 · 사용자 보류. |

| RP-21 | 기존 금고 등록자 9명 워크스페이스 이관(결정) | ReportArchive | 90-OURS-box-todo.md OB-23 같은 결정, 'RA 회신을 먼저 받는다'. 정한 기록 없음. |

| SF-10 | 역할 축 — 창 접착 테이프가 glass 로 분류됨 | StepForge (HEAXHub) | checklist.md — '[ ] StepForge 2차 물음 — SF-10 테이프 이름 꼴 …(받은 편지함 물음 9) — 과제 자료를 아는 사람에게 넘김(사용자 경유, SS-11)'. |

| SYNCEFF-4 | 03:30 일일 덤프를 배포 전 롤백 지점으로 써도 되는지 · §1b 와 병합 전 덤프를 따로 둔 의도 | 포털 (HWAXPortal) | HEAD 9b34a4ea update-all.sh:515-522 가 실행마다 backup-local.sh 로 새 덤프를 뜨고(backup-local.sh:117) 일일 덤프를 다시 쓰는 길이 없다. 이 질문의 답 · 결정 기록이 dev 문서 · dev 답신 폴더 에 없다. |

| UD-CORELINK | 운영 StepForge 앱 안 자동 잇기(STEPFORGE_CORE_LINK) 켤지 | 운영 쪽(우리) | HWAXProd 추적 유닛 deploy/units/node/cutover/hwaxprod-stepforge.service:22 · deploy/units/node/hwaxprod-stepforge-plmsync.service:4 · :16 에 STEPFORGE_CORE_LINK=off. git log -S 로 이 줄을 건드린 커밋은 f311eed(11-13, 사용자 결정) · e166a02(94eaa05 교체를 CORE_LINK=off 로) 둘뿐이고 지운 커밋은 없다 → 11-23 r20261123b 교체 뒤에도 꺼짐(v2, 추적 유닛 기준 — 실행 중 환경은 읽지 않음). |

| UD-SSOSECRET | STEPFORGE_SSO_SECRET 설정(서비스 단언 · REST 다리 쓰기 켜기) | 운영 쪽(우리) | core-link checklist.md:58 [ ] 맞물림 실호출 — 비밀이 없어 쓰기는 '꺼져 있다' 로 거절 · :59 [ ] 받은 편지함에 STEPFORGE_SSO_SECRET 차례. PART-ISSUE 문서(11-24): 서비스 단언 길은 미설정이라 꺼짐. 운영 기록(11-24): StepForge SSO 는 사용자 비밀 대기. 같은 비밀을 기다리는 MEMORY-18 과 함께 정한다. |

| 23-U1 | 전문가 고르기 그림자 → 순위 전환 · 멈춤 낱말 고르기 · 페르소나 링크 표 쓰기(그림자 셈 뒤) | 운영 쪽(우리) | 23-7 §4 · 23-14 §4 가 「좌석 고르기 그림자 → 순위 전환(~11-30 기록 보고) · 멈춤 낱말 — 사용자 결정」 으로 적음. SEAT_ONTO=shadow 는 11-23 에 켰고 일주일 셈은 11-30 무렵(HWAXPortal/docs/cae00-inbox/2026-11-23.md:104-113 · :213 → expert-ontology/context-notes.md EO-16 · EO-18). 페르소나 링크 표 --write 도 같은 셈 뒤(EO-15 ①). |

| AD-05 · AD-06(다시) | 빈 전문가 · 데모 전문가 지우기 | AIDataHub | request-1030 C-17 — 지우는 apply.sh 를 사용자가 돌릴 몫으로 넘어옴. |

| AD-18 | 글 없는 MX 백서 카드를 내릴지(결정) | AIDataHub | request-1027/checklist.md 의 AD-17 · AD-18 사용자 결정 줄 미체크(AD-17 은 뒤에 정함). review 권고 (나). gitlog AIDataHub(줄 295) 'org 밖 문서의 카드는 다시 받아도 그대로 남는다(AD-18 몫)'. |

| CDR-SELFCHECK | 자기검증 건너뛰기 넓히기(QA-1029 W-4 셋째) | 에이전트 서버 (HWAXAgentServer) | §4 보류 — SC-D1(10-23 '항상, 근거도 수치도 없는 짧은 답만 건너뜀') 을 건드리는 일이라 사용자 결정 대기 · gitlog 에 넓히는 커밋 없음. |

| CL-INBOX-Q6Q7 | dev 받은 편지함 Q6(코어 part 가 종류인지 인스턴스인지) · Q7(운영 사본이 새 판을 받는 길) 답 | 운영 쪽(우리) | 박스 HEAD core-link checklist.md:23 [ ] Q6 '사용자도 모름 11-10' · :24 [ ] Q7. dev 쪽에 답이 적힌 기록 없음. |

| D-5 | ODB 허브 대기 부분 일치 162건 확정 | 운영 쪽(우리) | 감사서 D-5 남음(「23-2 ODO-2 목록 도구 뒤」). |

| D-6 | SIREN 페르소나에 「이름 → 코어 풀기」 단계 넣기 | 운영 쪽(우리) | 감사서 D-6 남음(「23-10 뒤」). |

| D-7 | TestScope 개인 토큰 등록 뒤 코어 연결 재기 | 운영 쪽(우리) | 감사서 현황표 TestScope 「잴 수 없음 — needs_connect」 · D-7 남음. |

| D-07 | /ste/ 결과 파일 속도 · 연결 제한 | 운영 쪽(우리) | TODO 행 그대로 · 결정 기록 못 찾음. 손잡이는 HP-47 로 이미 들어왔고 기본은 꺼져 있다(부록 A). 남은 결정은 켤지와 어느 값(NGINX_STE_RESULT_RATE=20m · NGINX_STE_RESULT_CONN=2)을 쓸지다. |

| D-09 | 그 밖의 박스 결정 묶음 | 운영 쪽(우리) | 90-OURS 5절 행들 · 이번에 행별로 보지 않음. |

| HG-15 | 게이트웨이 금고 방식 리터럴 제거 | 게이트웨이 (HWAXMcpGateway) | 받은 answers.md HG-15 「지우지 않았다. 지금 gateway.py:351 이고 아직 쓰는 길이다 — 첫 단계(RA 홈 워크스페이스 보장)부터 남아 있다」 · 이후 제거 커밋은 gitlog grep 에서 못 찾음(현재 줄은 이 배치에서 다시 보지 않음) · answers.md:65-71 — 리터럴은 PORTAL_CONN_BACKENDS 이고, 위임 비밀이 빈 박스의 토큰 등록 길로 쓴다. 순서의 둘째(등록자 9명 이전)는 사용자 결정이다. HEAD c43382b gateway.py:436 정의 · 쓰는 곳 11 · :450 주석 '선언 키는 PORTAL_CONN_BACKENDS · PORTAL_CONN_META 에 들어가 … 등록 토큰 길을 그대로 탄다' |

| HP-34 | DRM 문서를 버튼 하나로 PC PowerPoint 에서 가져오기 | 포털 (HWAXPortal) | 받은 checklist.md `[~] HP-34 DRM 버튼 하나 — 정보보호 지침(우리 몫) 뒤 · 보류` |

| IR-T | 11-10 그림 판독 시험 흔적을 지울지 정하기 | 운영 쪽(우리) | 22 문서 부록 B '지우는 것은 운영자가 정한다'. 정한 기록이 22 · 00-INDEX 에 없다. 11-24 에 흔적이 아직 있는지는 열어 보지 않았다. |

| MW-11 | (결정 D9) 소속 분할 · wiki_aff_team_map | MXWhitePaper | MXWhitePaper context-notes.md:277 「aff:* 를 보이기 토큰에서 뺄지는 소속 분할(D9)과 함께 정한다」 — 결정 대기. |

| OUTSTANDING-4.4 | 사내 인증(ADFS) 이름 · 부서 클레임 릴리즈 VOC | IT(ADFS) | 문서 상태가 '초안 — 보내기 전 확인 2건(과제코드 · 이전 회신 여부)' 이다. knox-bridge docs/SSO-CLAIM-RELEASE-VOC.md 도 초안으로 남아 있다. |

| OUTSTANDING-15 | 정지 검사를 LoginId 로도 하기(조건부) | 포털 (HWAXPortal) | 문서가 '사번 없이 LoginId 만 오는 로그인이 실측되면 보낸다' 는 조건을 달았다(포털 D-11). 사번 몫은 d6f49e0 · c0de1fb 로 반영됐다. HEAD 9b34a4ea backend/app/config.py:146 은 'LoginId 로는 보지 않는다' 이다(추출 q1). 받은 편지함에 LoginId 실측 보고가 없다(q4). |

| PL-09 | 안내문 · 설명의 고정 색인 건수 | PLM 검색 에이전트 | PLM 신원 · 한도 일은 아니지만, 이것까지 PLM 보류 묶음에 넣을지는 사용자가 정한다(그래서 3절에서 이 4절로 옮겼다). 보내기로 정하면 3절 PLM 검색 에이전트에 넣되, 내부 보류 사정을 적은 문장은 넣지 않는다. 11-24 서버 안내문은 아직 고정 숫자 '8,494,719건'. |

| R-5 | 만료 안내 문구 | SIREN | 19 미발송 · 사용자 보류. |

| R-9 | 링크를 호스트 이름이나 link_path 로 | SIREN | 19 미발송 · 사용자 보류. 박스 쪽 대안 — 게이트웨이 HG-29 mask_keep_hosts 를 11-07 09:26 에 켬(메모리). 그 뒤 SIREN 링크가 가려지지 않는다. |

| R1111-Q5-2 | 포털 개인 토큰 화면의 '읽기만' 선택지 | 포털 (HWAXPortal) | REQUEST-20261111 이 11-09 사용자 결정으로 미뤘다고 적고 요청에서 뺐다 · 그 뒤 결정 기록 없음. |

| S-4 [22-1] | 포털 DocForge 권한(plat:docforge)을 지금 소속 그룹 밖으로 넓힐지 | 운영 쪽(우리) | 22-1 §5 '결정(사용자 11-10) — (가) 그대로', 권한 표 손대지 않음. IR-24 가 들어오면 다시 묻기로 함. IR-24 는 아직 안 들어옴(HEAD manifest.yaml:31). |

| SYNCEFF-2 | org_teams · org_groups · external_id_map 병합에 updated_at 을 넘길지 | AIDataHub | HEAD d59cf11 merge-from-drive.sh:351-352 · :371 의 try_merge org_teams · org_groups · external_id_map 이 여전히 updated_at 인자를 넘기지 않는다(그래서 늘 dev 판이 이긴다). |

| UD-STOP25 | 뜻이 섞인 낱말 25개를 뺄지 고르기 | 운영 쪽(우리) | §8 '뜻이 섞인 낱말 25개는 아직 고르지 않았다'(11-24). |



---



## 부록 A. 빼낸 것 — 이미 됨 · 대체됨 · 운영 쪽에서 함



다시 보내지 않으려고 남깁니다. 근거는 줄였습니다.



| ID | 제목 | 판정 | 근거 |

|---|---|---|---|

| 23-BOX-1 | DynaForge 운영 받는 코어 타입 3 → 46(systemd drop-in) | 운영 쪽에서 함 | HWAXProd main 에 d8428c8(11-24) — deploy/units/node/dropins/hwaxprod-koorm-api.service.d/core-types.conf · PLAN.md · make-env.sh(q2). 감사서: 받기 run 559 ok(15:00) · 46 타입 건수 코어와 같음. |

| 23-BOX-2 | 게이트웨이 어휘표 박스 덧씌우기 — ontology.lookup 다섯 줄 | 운영 쪽에서 함 | 박스 HWAXPortal/backend/config/core_vocab.local.json 있음, ontology.lookup = arp · fmea · mountsoldatahub · ncdevdatahub · odb-hub(q2, 키만 읽음). 덧씌우기 장치는 dev 가 10-29 에 만듦(8dc2719 · ab… |

| 23-BOX-3 | MountSol · NCDev 형제 역할을 박스 덧씌우기에(23 문서의 D-1 로 정함) | 운영 쪽에서 함 | core_vocab.local.json apps = mountsoldatahub · ncdevdatahub(q2). 감사서: /health 가족 다섯 · ontology_lookup 형제 셋 모두 role sibling(16:16). |

| 23-BOX-4 | SignalForge · CircuitTrace · PLM 결함 허브 lookup 줄은 그 앱 반영 뒤 우리가 넣기 | 운영 쪽에서 함 | 박스 덧씌우기 lookup 에 세 앱 줄 없음(q2) — 일부러 미룸(지금 넣으면 프로젝트 key 가 전체 검색 · 잡음 결과로 넘어감). |

| AD-01 | MX 백서 전문가 카드 154장 본문 절 빔 | 이미 됨 | gitlog AIDataHub 절 76af3a4 · a628149 · 9e8f1da · df7d45b(AD-01 flatten · 다시 색인 명령). request-1030/checklist.md '[x] AD-01 다시'. 남은 것은 박스에서 다시 색인 명령을 돌리는 사람 단계(사용자 OK 뒤, server-set… |

| AD-01(다시) | MX 백서 분석가 카드 154장의 1번 절이 빔 | 이미 됨 | AIDataHub df7d45b · 6f496fa. 박스 색인 다시 짓기 a628149 는 우리 몫으로 처리. |

| AD-03 | 사내 DRM 문서를 변환 앞에서 알아보기 | 이미 됨 | gitlog AIDataHub facd6db(사내 DRM · OLE 머리 → DRM_PROTECTED) · 34d84d1(error 칸 문구). request-1030/checklist.md '[x] AD-03 다시 → DRM_PROTECTED'. 박스 HEAD 로그에도 두 커밋(q2). |

| AD-03(다시) | 분석 변환이 문서 DRM 파일을 손상으로 안내 | 이미 됨 | recv/request-1030 체크리스트 완료 · AIDataHub HEAD d59cf11. |

| AD-04 | 본문 검색 스위치 속도 측정 | 이미 됨 | request-1030/checklist.md '[x] AD-04 측정 10-31: 끔 8 ms · 켬 따뜻할 때 6.4 s · 처음 >45 s → OB-89 꺼 둠(C-16)'. |

| AD-04(다시) | 지식카드 본문 검색 속도 실측 | 이미 됨 | 잰 값 회신 — 끔 8 ms, 켬 6.4초(데운 뒤) · 45초 넘음(찬 기동). |

| AD-07 | 심의 근거 검색 날짜 컷오프(as_of) | 이미 됨 | gitlog AIDataHub d7e29d7 · 63baf15(as_of). request-1030/checklist.md '[x] AD-07 다시(as_of)'. |

| AD-07(다시) | agent_search 가 as_of 를 받지 않음 | 이미 됨 | recv/request-1030 체크리스트 완료 · AIDataHub HEAD d59cf11. |

| AD-08 | 최근 inbox 파일 목록 읽기 도구 | 대체됨 | request-1027 review-10-AIDataHub.md — 범위가 옮겨 감(포털 먼저), 미룸. request-1030 다시 보낸 목록에 없음. 박스 AIDataHub HEAD d59cf11 git grep list_inbox 0건(q1). |

| AD-09 | 덤프 병합이 레코드 m3 시그니처를 옮기지 않음 | 이미 됨 | request-1027 review-10-AIDataHub.md — 이미 반영(a7a2ee4 · 722d7a0). |

| AD-10 | (선택) 심의 좌석 키 delib-baseline-defender 등록 | 대체됨 | request-1027 review-10-AIDataHub.md — 등록만으로는 효과 없음, 심의 오류는 엔진 쪽에서 반영. 박스 HEAD git grep delib-baseline-defender 0건(q2, 데이터 행이라 코드에 없는 것이 정상). |

| AD-11 | materialtwin 동기화가 기존 content 를 덮는가(질문) | 이미 됨 | request-1027 review-10-AIDataHub.md 가 답함. |

| AD-12 | update-all 병합에서 updated_at 빈 행은 dev 가 이기나(질문) | 이미 됨 | request-1027 review-10-AIDataHub.md — 전제가 틀렸다고 답함. 포털은 sync-he-personas.py 미리보기로 어긋남만 알림(gitlog HWAXPortal 'AIDataHub 검토 AD-12'). |

| AD-13 | AD-05·06 지우기를 어디서 할지(질문) | 이미 됨 | request-1027 review 답 · request-1030 C-17 — dev 원본에서 사용자가 지우고, 박스는 병합으로 받는다. |

| AD-14 | 동기화를 끄면 154장은 어느 길로 고치나(질문) | 이미 됨 | request-1027 review 가 답함. 길은 AD-01 의 flatten + 다시 색인(request-1030 체크리스트 [x]). |

| AD-15 | 동기화를 켜면 키를 어느 env 에 두나(질문) | 이미 됨 | request-1027 review 가 답함(SF_API_KEY 도 빠졌다고 덧붙임). AD-17 (나)로 켜지 않아 쓰일 일 없음. |

| AD-16 | (알림) BGE-M3 전환 끝 — dev 체크리스트 반영 | 이미 됨 | gitlog HWAXPortal b14abc43 'AD-16 … BGE-M3 전환을 임베더 체크리스트 B6 에'. request-1027/checklist.md 반영 표시. |

| AD-17 | 정기 동기화 3곳을 다시 켤지(결정) | 이미 됨 | gitlog AIDataHub 684765b — 10-31 사용자 결정 AD-17 (나), 예시 .env 의 AIDH_SYNC_ALLOW_INTERNAL 끔, 덤프 병합이 정본(C-24). request-1030/checklist.md '[x] AD-17'. |

| AD-19 | 추천 점수 낱말 겹침이 요청 낱말에도 가점 | 이미 됨 | recv/request-1030 체크리스트 완료 · AIDataHub HEAD d59cf11. |

| AD-20 | 카드-전문가 잇기 저장소가 둘 | 이미 됨 | recv/request-1030 체크리스트 완료 · AIDataHub HEAD d59cf11. |

| AD-21 | 전문가 저장 뒤 500 으로 운영자 동기화 멈춤 | 이미 됨 | recv/request-1030 체크리스트 완료 · AIDataHub 97ecb9c(10-30, 저장 응답) 박스 git log. |

| AR-1 | ARP 코어 온톨로지 받기 클라이언트 | 이미 됨 | 23-3-ARP-core-ontology.md 「16 의 AR-1 ~ AR-3 은 들어왔다. 코어 14 타입을 매일 받고(마지막 11-24 01:00 KST, ok, 6.3 초)」. 발송: 회신함 2026-10-31 Q7(AR-1 ~ 4 를 16 에 붙여 보낼 것) → OUTBOUND-20261101 3절로 사람이 … |

| AR-2 | model 인자 하나의 공통 해석기 · matched_by | 이미 됨 | 23-3 §1 표 — 과제 A 는 matched_by task_name · via task → project, C1 은 task_code, P1 은 project_key(list_analyses, 11-24 실측). |

| AR-3 | 0건 이유 네 가지 | 이미 됨 | 23-3 한 줄 — 데이터가 없으면 modelMatch.reason: in_core_no_local_data 와 설명 문장을 준다(11-24 실측). |

| AR-4 | 받기 상태 노출 · 하루 1번 이상 받기 | 이미 됨 | 23-3 §1 — ontology_status: configured · role live · 14 타입 · 마지막 11-24 01:00 KST ok(6.3 초), 건수가 코어와 같음. |

| AR-5 | 모델 등록 때 코어 key 고르기 | 대체됨 | 23-3 ARO-1 이 대신한다 — linkedModels 32/42. 태그 없는 모델 10개의 코어 후보를 관리자 화면에 보여 달라는 요청. |

| AR-6 | 해석방법 · 해석역량 · 부품 · 고장모드와 잇기 | 대체됨 | 23-3 ARO-2 가 대신한다(부품 · 시험항목 · 관리 기준 받기, 선택). 고장모드는 이미 14 타입 안에서 받는다(고장모드 123, 23-3 §1). |

| AR-7 | (질문) ARP 서버에서 코어 허브로 연결되는가 | 이미 됨 | 23-3 — 매일 받기가 ok 로 돈다(11-24 01:00 KST). 연결된다는 실측. |

| AR-8 | (질문) 코어 토큰 발급 주체 | 이미 됨 | 토큰이 이미 있어 받기가 돈다(23-3). 남은 범위 문제는 23-3 Q-1(넓은 범위 토큰 → core:read 전용으로 바꿀 계획)로 옮겨 감. / 정리 11-25: 질문은 답을 얻음 — 토큰이 발급돼 받기가 돈다. 남은 범위 문제는 ARO 행과 23-3 Q-1 로 옮겨 감. |

| B-1 [11-17] | (브리지) stl --units m(11-17 초안) | 대체됨 | 11-18 전달. REMAINING BG-6 으로 넘어갔다. |

| B-2 [11-17] | (브리지) 공동 솔리드 STL 확인 --max-open-edges(선택) | 운영 쪽에서 함 | checklist.md 11-18 — '[x] BR-R3 입력 STEP(잡 3fa9415132b7) · B-2 공동 STEP 표본 — 사용자 결정 11-18: dev 로 꺼내지 않고 운영 박스에서 시험한다'. 공동이 아직 한 번도 나오지 않아 시험할 표본이 없다(REMAINING SF-1). |

| BBOX-6 | 고친 판 뒤 운영 쪽 할 일 — 원본 STEP 되돌림 여부 · section_atlas | 운영 쪽에서 함 | 문서 §6 — '고친 판이 들어온 뒤에도 원본 파일로 되돌릴지는 과제 주인과 정합니다'. gitlog HWAXProd 7f8f644 에 11-13 우회 기록이 있다. 27b2132b(11-15) 이후의 되돌림 · section_atlas 기록은 받은 문서에서 찾지 못했다. 전제(고친 판)는 이미 들어왔다 — 27b2… |

| BG-4 | gas_transport_lookup 보강 — S = P/D 추정 · Δ온도 · 층별 | 이미 됨 | gitlog HWAXMcpGateway b571f36(11-21 — S = P/D 추정). HWAXPortal 11094826. checklist.md — 'BG-4 — 지음 · 올림(b571f36 — 같은 시료 · 온도 1 K 안 · O2 일 때만, dev 게이트웨이 반영 11-22) · 온도 차 칸은 이미 있다(… |

| BG-5 | 신뢰성 시험 조건 → 해석 환경 값 | 운영 쪽에서 함 | gitlog HWAXMcpGateway dd304eb(reliability_test_conditions). checklist.md — '[ ] BG-5 · PT-1 토큰이 없을 때의 답(등록 방법) 확인 … 공용 프리셋은 만들지 않는다(사용자 결정 11-22) — 11-23 못 봄(토큰을 등록하지 않은 계정이 있어야… |

| BOX-01 | DynaForge 받을 타입 넓히기 | 운영 쪽에서 함 | 21번 §4-1 '11-09 끝냄' — 35 타입 모두 ok · 18,884건 · 고장모드 120 · 원인 22. |

| BOX-02 | StepForge 개정 지정 | 운영 쪽에서 함 | 21번 §4-1 — 업데이트 뒤 하기를 권함. 지금 상태 확인 안 함. |

| BOX-03 | StepForge 같은 파트 기록(match lineage) | 운영 쪽에서 함 | 21번 §4-1. SRC-04 자동 실행은 들어왔으나 운영은 STEPFORGE_CORE_LINK=off 라 돌지 않음 — 지금은 사람이 걸어야 함. |

| BOX-04 | StepForge 부품 채우기 잡 | 운영 쪽에서 함 | 21번 §4-1. PART-ISSUE 문서(11-24): instance_of 0줄. |

| BOX-05 | StepForge 후보 확정 · 거절 | 운영 쪽에서 함 | 21번 §4-1 — 웹 화면에서 사람이 함. |

| BOX-06 | DynaForge 해석 리포트 올리기 | 운영 쪽에서 함 | 21번 §4-1 — 데이터 주인 몫. |

| BOX-10 | 업데이트 받기 · SRC 완료 기준 운영 재확인 | 운영 쪽에서 함 | StepForge 94eaa05b 반입(docs/cae00-inbox/2026-11-12.md:36) · KooRemapper 8b49d2a. 각 SRC 완료 기준 운영 재확인 기록은 못 찾음. |

| BOX-11 | 서비스 토큰 발급 | 운영 쪽에서 함 | docs/core-link/checklist.md:59 [ ] 받은 편지함 — 서비스 토큰 발급 · service_tools.local.json 예시 · STEPFORGE_SSO_SECRET 차례 남음. |

| BOX-12 | 역할 → 코어 부품 대응표 확인 | 대체됨 | 운영 사용자가 11-24 14칸 확인(PART-ISSUE 부록 A) · §8(:292) '이 요청(ST-24)으로 개발에 보낸다. 운영에서 쓰지 않는다' → 저장소 반영은 ST-24. |

| BOX-13 | 플랫폼별 dry-run 표 | 운영 쪽에서 함 | 21번 §4-2 · HWAXPortal docs/core-link/server-setup.md:93. 실행 기록 못 찾음. |

| BOX-14 | 확인한 것만 적용(백업 먼저) | 운영 쪽에서 함 | 21번 §4-2. |

| BOX-15 | post-update 훅 50-core-link.local.sh | 운영 쪽에서 함 | 훅 자리는 SRC-12 로 착지. HWAXPortal docs/core-link/context-notes.md:177 — 박스 훅은 plm-sync 하나로 충분(규칙 잇기는 앱 안) · server-setup.md:68 · :104 같은 내용. |

| BOX-16 | 플랫폼별 ④ 선 수 · onto_path 한 줄 확인 | 운영 쪽에서 함 | PART-ISSUE 문서(11-24): StepForge 파트 → 코어 부품 0%(maps_to 0) — onto_path 는 ST-24 뒤에야 나옴. |

| BOX-OL2 | 박스에서 onto_lookup_first 켜기와 /search-eval 확인 | 운영 쪽에서 함 | 켜기 끝남 — 박스 search_tuning.local.json:5 onto_lookup_first true(파일 마지막 변경 11-24 10:24, v2). /search-eval 비교 기록은 이번에 못 봄. dev ontology-first checklist 마지막 줄 [ ] 는 아직 닫히지 않음(우리가 알리지 … |

| BOX-OL5 | 박스 search_tuning.local.json 의 동의어 둘 걷기(noncore_demote 는 남김) | 운영 쪽에서 함 | 끝남 — 박스 HWAXMcpGateway search_tuning.local.json(488바이트, 마지막 변경 11-24 10:24) grep 에 '온톨로지' · 'ontology' 키 0, :4 noncore_demote true. 동의어는 기본값 search_tuning.json:640 · :652 에만 있음(… |

| BOX-STOP64 | 뺄 낱말 64개 박스 덧씌우기(onto_rules.local.json) 유지 | 운영 쪽에서 함 | 끝남 — 문서 :263: 11-24 운영 사용자 결정으로 64개를 넣고 load_rules() 가 64개를 돌려줌을 확인. 박스 AIDataHub api_server/config/onto_rules.local.json 있음(990바이트, 마지막 변경 11-24 18:20) · onto_svc.py:96 이 덧씌우기를… |

| BR-R1 | (브리지) fetch 가 운영 StepForge 에 닿게(11-17 초안) | 대체됨 | 11-18 전달. checklist.md 11-18 — 'BR-R1 정정(STEPFORGE_BASE 는 이미 읽는다, 기본 폴백 주소가 문제)'. REMAINING BG-1 · ST-3 으로 넘어갔다. |

| BR-R2 | (브리지) 요청서 part 로 그 파트만 받기(11-17 초안) | 대체됨 | 11-18 전달. REMAINING BG-1(export_part_step 으로 그 파트만)로 넘어갔다. |

| BR-R3 | (브리지) outline 얇은 판 수정(11-17 초안) | 대체됨 | 11-18 전달. checklist.md — 'BR-R3 합성 재현은 통과', 실물(잡 3fa9415132b7 입력)은 운영 박스에서 시험하기로 했다. 11-21 재시험에서 두 판이 다시 실패해 REMAINING BG-2 로 넘어갔다. |

| BR-R4 | (브리지) outline_source=stepforge(11-17 초안) | 대체됨 | 11-18 전달. REMAINING BG-2 로 넘어갔다. |

| CL-01 | update-all 끝 박스 훅 자리 | 대체됨 | 20번 머리 '21번으로 합쳤다. 보내지 않는다' · 00-INDEX.md:35 · 21번 §8: CL-01 → SRC-12(같다). SRC-12 는 포털 99f42a24 로 착지. |

| CL-02 | StepForge 받기 뒤 규칙 단 잇기 | 대체됨 | 21번 §8: CL-02 → SRC-03 · SRC-05(과제 연결과 채우기 잡 둘로 나눔). |

| CL-03 | 받기 뒤 채움 규칙 실행 | 대체됨 | 21번 §8: CL-03 → SRC-05(같다). |

| CL-04 | 자체 부품 → 코어 part 관계 종류 | 대체됨 | 21번 §8: CL-04 → SRC-01 · SRC-02(파트 → 역할, 역할 → 코어 부품 두 걸음). |

| CL-05 | 프로젝트 → 과제 잇기 매칭 차례 | 대체됨 | 21번 §8: CL-05 → SRC-03(매칭 차례를 규칙 단 안에). |

| CL-06 | 개정 후보 0 의 이유 싣기 | 대체됨 | 21번 §8: CL-06 → SRC-06(같다). |

| CL-07 | plan_task_links 일반 사용자 읽기 | 대체됨 | 21번 §8: CL-07 → SRC-10(같다). SRC-10 은 5ec314eb 착지. |

| CL-08 | 리포트 과제 별칭 규칙 단 잇기 | 대체됨 | 21번 §8: CL-08 → SRC-09(인제스트 때 잇기는 이미 있어 과거 리포트 붙이기로 좁힘). |

| CL-09 | 질문 — cae_* → 코어 대응을 DynaForge 안에만 둘지 | 대체됨 | 21번 §8: CL-09 → SRC-08 · Q-5(질문을 요청으로, 다리를 자체 정의에). |

| CL-10 | 게이트웨이 서비스 신원 경로 | 대체됨 | 21번 §8: CL-10 → SRC-13 · SRC-07(게이트웨이와 StepForge 받는 일을 나눔). |

| CL-11 | 질문 — tools-map 쓰기 목록에서 link_ 짝이 빠진 까닭 | 대체됨 | 21번 §8: CL-11 → SRC-14(같다). SRC-14 는 3445a4b 착지. |

| CL-12 | 코어 plm_model 모델 개정 칸 채움 보강 | 대체됨 | 21번 §8: CL-12 → §7 로 뺌(허브 안의 일 — 허브가 스스로 한다). 21번은 까닭 싣기(SRC-06)만 청함. |

| CTO-1 | 모델코드로 보드를 고를 때 model_code_key 가 같은 보드만 | 운영 쪽에서 함 | 받은 CircuitTrace 요청은 REQUEST-20261121-도구영역분류.md 하나(CT-01~03 도구 영역), CTO- 0건(q3). 코드(박스 폴더, git 없음): core/modelcode.py board_keys 가 model · model_code_key · project · job_name · f… |

| CTO-2 | 0장일 때 reason 과 같은 프로젝트 보드 안내(스스로 넓히지 않음) | 운영 쪽에서 함 | CTO- 0건(q3). boards_for_model 은 model_code · n · boards 만 돌려주고 reason 칸 없음(jobs/lookup.py:178-189, q4). / 검증: 우리 앱이다 — 23-5 머리 「대상 저장소 CircuitTrace(운영판은 운영 노드, 개발판은 운영 박스)」, 11-… |

| CTO-3 | 보드 · 결함 응답에 core_key · matched_by | 운영 쪽에서 함 | CTO- 0건(q3). CircuitTrace 소스(.venv 밖) grep core_key 0건(q3). / 검증: 우리 앱이다 — 23-5 머리 「대상 저장소 CircuitTrace(운영판은 운영 노드, 개발판은 운영 박스)」, 11-21 요청서 recv CircuitTrace/docs/requests/REQUE… |

| CTO-4 | 사례 집합 밖 결함이라는 note | 운영 쪽에서 함 | CTO- 0건(q3). / 검증: 우리 앱이다 — 23-5 머리 「대상 저장소 CircuitTrace(운영판은 운영 노드, 개발판은 운영 박스)」, 11-21 요청서 recv CircuitTrace/docs/requests/REQUEST-20261121-도구영역분류.md:14 「CircuitTrace 한 줄만 … 청… |

| CTO-5 | (선택) 과제명 · 과제코드 · 프로젝트로 보드 찾기 | 운영 쪽에서 함 | CTO- 0건(q3). / 검증: 우리 앱이다 — 23-5 머리 「대상 저장소 CircuitTrace(운영판은 운영 노드, 개발판은 운영 박스)」, 11-21 요청서 recv CircuitTrace/docs/requests/REQUEST-20261121-도구영역분류.md:14 「CircuitTrace 한 줄만 … 청… |

| D-1 | (사용자 결정) 2단계 경로 | 이미 됨 | 회신함 2026-10-31 Q6 — ODB 허브 요청은 사람이 보내고 D-1 = 가. recv gitlog 0fa19a6d(10-30)도 D-1 가로 적음. |

| D-2 | AIDataHub 부품 타입 카드 결합 — 증분 뒤에 돌리기 | 운영 쪽에서 함 | 감사서 D-2 「정함 — 증분 뒤(11-24), 결합은 돌리지 않았다」. 증분 모드는 아직 없음(HPO-2 · AD-22 미반영, q2). |

| D-02 | DocForge 를 코어 온톨로지에 이을지 | 이미 됨 | 00-INDEX 23-8 에 DocForge 가 코어에 붙었다고 적힘. |

| D-03 | ODB 허브 운영자를 둘지 | 이미 됨 | '둔다' 결정 7067f94. |

| D-4 | 웹 챗 온톨로지 하네스 시험 — 23-1 · 23-4 · 23-14 반영 뒤 한 번에 | 운영 쪽에서 함 | 감사서 D-4 「정함 — 요청 반영 뒤에(11-24)」 · §3 웹 챗 「돌리지 않음」(하네스 브라우저에 사람 SSO 로그인 필요). |

| D-04 | 운영 앱 둘의 '(시험)' 라벨 | 운영 쪽에서 함 | OB-04 와 같음 — 개발 dbbb943 반영, 박스 라벨 남음. |

| D-05 | AIDataHub 정기 동기화 3개 켤지 | 이미 됨 | request-1030 context-notes.md:153 — C-24 AIDataHub 정기 동기화는 이 박스에서 켜지 않는다, 덤프 병합이 정본(사용자 결정 10-31 AD-17 (나)). |

| D-06 | 운영 노드 새 판 묶음 내보내기 | 대체됨 | 11-12 전환 뒤 운영 노드는 r20261123b(11-23)로 돌고 있어 10-29 판 질문은 지나감. |

| D-8 | HWAXProd drop-in · PLAN.md 행 커밋 | 이미 됨 | HWAXProd d8428c8(11-24) — 3 파일(PLAN.md · make-env.sh · core-types.conf), HEAD ad07a76, git status 에 ahead 표시 없음(q1 · q2). / 검증: HWAXProd main ad07a76 = origin/main(박스 로컬 bare 저장… |

| D-08 | 챗 응답 개인정보 가림 범위(REST 다리) | 이미 됨 | HG-22 가 REST 다리 출력까지 가림(E-2 9b37b31). |

| DF-02~15 | DynaForge 요청서 v1.0 남은 행(출처 · 유효성 · 추출 완전성 · 보고서 묶음 · 캠페인 집계 · 핫스팟 · 세션) | 이미 됨 | 개발 쪽 답신(11-21)이 DF-02~15 를 반영했다고 적음. 원 요청서 v1.0 원본은 저장소 밖에 있어 줄마다 수용 기준과 대조하지는 않음. |

| E-2 | 게이트웨이가 어휘표 앱 역할을 순위 · 접기 · 노출에 씀 | 이미 됨 | 게이트웨이 9b37b31(10-31) — 어휘표 역할을 다 읽어 순위 · 접기 · 노출에 쓴다, 가족(정본 + 형제)은 원래 이름으로 접고 늘 접두, 비코어 낮추기 손잡이(기본 끔). |

| E-5 | 전문가 고르기 기준선(1단계) | 이미 됨 | 에이전트 ec83e51 · 포털 3344df20(10-31) — 평가셋 · /seat-eval 창구와 러너(읽기 전용) · 실사용 질문 모으기(기본 끔) · personas 칸(동작 변화 0) · 관리자 '전문가 고르기 검토' 화면, 사용자 결정 10-31 D-E5-1 ~ 8 (가). |

| ER-01 | 리스크 심사 과제에 ECAD 보드 칸(사람이 find_job 결과에서 고름) | 이미 됨 | recv gitlog 1f8efe7c(10-31) 리스크 앱 ECAD 1단계 반영 · 앱 main 9bd5f48. 5ae27162(보드 고르는 화면 요청) · 9059f9d8(risk_set_ecad_board 를 쓰기 도구에 넣음). 게이트웨이에 risk_set_ecad_board · risk_find_ecad_b… |

| ER-02 | ODB 허브 도구를 이름 4개가 아니라 백엔드 odb-hub 로 찾기 | 이미 됨 | recv gitlog 1f8efe7c — 1단계 반영(9bd5f48)에 /tools-map 의 backend 기준 찾기 포함. 박스 읽기(11-24): 리스크 앱 계약 문서가 백엔드 기준 이름 풀기(adapters/base.backend_tool_name)와 도구 지도를 못 읽을 때 409 ecad_gateway_u… |

| ER-03 | 1단계 ECAD 어댑터(보드당 호출 약 13번) | 이미 됨 | recv gitlog 1f8efe7c(10-31) — adapters/ecad.py 1단계, 앱 main 9bd5f48. 박스 읽기(11-24): HEAXHub 리스크 앱 작업 사본 backend/app/adapters/ 에 ecad.py 가 있고 ecad_stub.py 는 없다. 계약 문서 1단계 표 — 보드 1 … |

| ER-04 | 모자란 자료 표시(degraded 칸) | 이미 됨 | recv gitlog 3d2cde59 — 결정 409 ecad_pat_absent · ecad_nets_deferred 등. 박스 읽기(11-24): adapters/ecad.py 가 degraded 에 ecad_nets_deferred · odb_version_absent · outline_origin_unknow… |

| ER-05 | 계약 문서 · 포털 plan.md 고치기 | 이미 됨 | recv gitlog 76ee0507(10-31) — 포털 plan.md §2.5.3 · §2.13.5 를 다시 씀. 1f8efe7c(리스크 앱 1단계 반영)와 같은 날. |

| F-1 | cavity_openings — 공동 개구부 · 공기 안 점(11-17 초안) | 대체됨 | 11-18 전달 — HWAXPortal docs/ste-stepforge-1117/checklist.md '[x] 원문 둘을 StepForge · ste · 브리지 세션에 나눠 보냄', gitlog HWAXPortal 5041b9d9. context-notes.md SS-7 — D-707 1차 F-1(조사부터). 실… |

| F-2 | artifact_to_ste_upload — StepForge 산출물 쪽(11-17 초안) | 이미 됨 | gitlog HWAXMcpGateway ec91b62(게이트웨이 artifact_to_ste_upload, 11-18). 초안 자신이 '11-18 생김, 11-19 시험 통과' 라고 적었다. context-notes.md SS-7 — StepForge 는 to_ste_upload 를 만들지 않고 게이트웨이 한 길로 … |

| F-3 | cold_surface_from_parts(11-17 초안) | 대체됨 | 11-18 전달. context-notes.md SS-7 — D-707 2차에 F-3 이 들어갔다. 실제 공동에서의 확인은 REMAINING SF-3 으로 넘어갔다. |

| F-4 | enclosure_candidates(11-17 초안) | 대체됨 | 11-18 전달. SS-7 — D-707 2차에 F-4 가 들어갔다. 앞뒤 유리가 빠지는 문제는 REMAINING SF-7 로 넘어갔다. |

| F-5 | 잡 대기 정보 · 짧은 잡 줄(11-17 초안) | 이미 됨 | context-notes.md SS-7 — D-707 2차에 F-5 가 들어갔다. REMAINING SF-12 는 job_status.queue 를 '볼 기회가 없었다' 며 확인만 청했다. |

| F-6 | leak_report 넓은 창(11-17 초안) | 대체됨 | 11-18 전달. SS-7 — D-707 2차에 F-6(parts= 로 좁히기)이 들어갔다. 외피 3파트가 1.1배로 멈추는 남은 문제는 REMAINING SF-11 로 넘어갔다. |

| F-7 | 산출물 경로 표시(11-17 초안) | 이미 됨 | SS-7 — D-707 1차에 F-7. REMAINING '풀린 것' — list_artifacts 의 path_note(노드 안 경로임을 밝히고 받는 길 셋을 안내)가 된다. |

| F-8 | leak_report 제안값과 build_cavity 검출 범위 맞추기 · 제출 때 검사(11-17 초안) | 대체됨 | 11-18 전달. SS-7 D-707 1차에 F-8. REMAINING '풀린 것' — leak_report 제안 노트(suggested 0.525 · table_covers_mm 0.5)가 나온다. 접수 검사는 SF-1 에 남았다. |

| F-9 | build_cavity 큰 판 — 규모 점검 · 진행 · 깨진 파트 · 외피만 공동(11-17 초안) | 대체됨 | 11-18 전달. REMAINING SF-1(파트 목록 · 접수 검사 · 진행 · 깨진 파트 이름 · 범위 안 마개)로 넘어갔다. SF-1 은 D-708 edcddf44 에 들어갔다. |

| FM-07 | (알림) MatNexus 는 코어를 받지 않음 | 대체됨 | 23-9-FMEA-MatNexus-core-ontology.md(11-24) MNO-1 이 MatNexus 에 코어 소스 등록을 청한다(sp_core_status configured false 재확인). |

| FM-08 | (알림) FMEA resolve_model_tool 은 정적 레지스트리 | 대체됨 | 23-9 문서(11-24): FMEA 는 코어를 매일 밤 받고 사례에 hub_* 칸이 있다 — 후속은 FMO-1 ~ FMO-3. |

| FORGE-CUTOVER-B1 | 박스 셸 시작 파일의 export KOORM_BASE 줄을 둘지 정하기 | 운영 쪽에서 함 | 운영 박스 ~/.bashrc 에 'export KOORM_BASE=' 살아 있는 줄 1개(11-24, 값은 출력하지 않음) — 23행으로 대화형 셸 가드(26-28행 case $- / return) 위에 있어 ssh 로 돈 비대화형 셸에도 실린다. 11-23~11-24 update-all 로그 네 개에서 '건너뜀' … |

| H-01 | 웹 챗 온톨로지 시험 16개 | 운영 쪽에서 함 | 10-30 재시험(PASS 12 · PARTIAL 3 · FAIL 1)을 돌림 · 고침 뒤 재시험은 남음. |

| H-02 | 업로드 목적지 · 큰 파일 · DRM 파일 손 시험 | 운영 쪽에서 함 | OB-60 ~ 62 '돌리지 않았다'. |

| H-03 | 자기검증 · 위키 버튼 · MX 진입 · VOC 화면 손 시험 | 운영 쪽에서 함 | OB-63 ~ 68 남음. |

| H-04 | Desktop 패널 손 시험 | 운영 쪽에서 함 | 기록 못 찾음. |

| H-05 | DocForge 정밀 변환 한 번 | 운영 쪽에서 함 | OB-102 남음. |

| H-06 | '예고만 하는' 호출 재측정 | 운영 쪽에서 함 | OB-71 남음. |

| H-07 | FMEA · MatNexus · 신규 SSO 사용자 RA · 지식카드 화면 손 시험 | 운영 쪽에서 함 | 기록 못 찾음. |

| HA-01 | 무캡 경로 도구 캐시 키 | 이미 됨 | checklist.md [x] HA-01 (45cd6ff) |

| HA-02 | _ONTO_CORE 늘 묶기 | 이미 됨 | checklist.md [x] HA-02 (35b8478) |

| HA-03 | SYSTEM_PROMPT 코어 규칙 | 이미 됨 | checklist.md [x] HA-03 (cccab32) |

| HA-04 | 허브 응답 접기 | 이미 됨 | checklist.md [x] HA-04 (2a50cf3) |

| HA-05 | 패널 전용 도구 막기 | 이미 됨 | checklist.md [x] HA-05 (c02e05e) |

| HA-06 | 남의 심의 이어하기 | 이미 됨 | checklist.md [x] HA-06 (3e7f00b) |

| HA-07 | 토큰화 잡음 · IDF | 이미 됨 | checklist.md [x] HA-07 (504c150) |

| HA-08 | 위키 꺼짐 때 _wiki_submit 건너뜀 | 이미 됨 | checklist.md [x] HA-08 (8d519ec) |

| HA-08(다시) | 위키 꺼짐 글귀와 MX 백서 문구 어긋남 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922. |

| HA-09 | 끊긴 심의 체크포인트 이어하기 | 이미 됨 | checklist.md 는 [~] 였으나 HEAD 에이전트 git log --grep HA-09 에 27f0229 merge(HA-09 S1 ~ S4, 10-31) · 07981fd S0 · b541787 |

| HA-10 | 잡 폴더 · 원장 권한 | 이미 됨 | checklist.md [x] HA-10 (b6e90c4) |

| HA-11 | 심의 날짜 기준일 as_of | 이미 됨 | checklist.md [x] HA-11 (88a4b5b · 포털 734cef7 · merge a014b0c) |

| HA-12 | 자기검증 도구 없는 턴 ② | 이미 됨 | checklist.md [x] HA-12 (89d4f69) |

| HA-13 | /health self_check | 이미 됨 | checklist.md [x] HA-13 (1b96a15) |

| HA-15 | 질문 언어로 답 | 이미 됨 | checklist.md [x] HA-15 (83b4927) |

| HA-16 | 도구 의미 색인 LRU | 이미 됨 | checklist.md [x] HA-16 (862ea74) |

| HA-17 | 좌석 그림 판독 손잡이 | 이미 됨 | checklist.md [x] HA-17 (f01286e — DELIB_SEAT_VISION_MAX) |

| HA-18 | 긴 카드 절단점 | 이미 됨 | checklist.md [x] HA-18 (44f3d20) |

| HA-20 | ui_resource SSE(패널 2단계) | 이미 됨 | checklist.md 는 [~] 브랜치였으나 HEAD 에이전트 git log 에 1159376 merge(HA-20 · HP-42 P1) · app.py:114 `import ui_panels` · 포털 a694e19c(P2 ~ P4) |

| HA-21 | agent_cache 기한 | 이미 됨 | answers.md HA-21 30분 수명(45cd6ff) |

| HA-22 | 도구 미호출(예고만) 재시도 | 이미 됨 | answers.md HA-22 「아는 것은 셋 … OB-71 로 다시 잴 때 볼 자리를 적었다」 |

| HA-23 | '(시험)' 라벨 prod 앱 묶음 후보 | 운영 쪽에서 함 | checklist.md [-] HA-23 「D-1 라벨 바로잡기(박스, 코드 없음)」 |

| HA-24 | 챗 plm_defect_search enrich 기본 0 | 이미 됨 | checklist.md [x] HA-24 (D-3 · 1b42bbd) |

| HA-25 | FailureTrace 검출자 · 작업자 이름 가림 위치 | 대체됨 | checklist.md [-] HA-25 「D-4 원천(FailureTrace DP-08)」 — 에이전트 몫 없음, 12-Datahub-platform.md DP-08 로 대체 |

| HA-26 | 이 턴 안내가 든 챗이 LLM 400 으로 실패 | 이미 됨 | recv/request-1030 체크리스트 완료 · 에이전트 서버 커밋 7ca3a2e · e94bc09 가 박스 HEAD b0fd922 에 들어 있음. |

| HA-27 | 자기검증이 맞는 초안 값을 틀리게 고침 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 에이전트 서버 HEAD b0fd922 에 들어 있음. |

| HA-28 | 잡 상태를 LLM 으로 폴링 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922 에 들어 있음. |

| HA-29 | 사람 확인 없이 무거운 잡을 시작 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922 에 들어 있음. |

| HA-30 | 허브를 건널 때 앞 허브 id 를 그대로 넘김 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922 에 들어 있음. |

| HA-31 | 전문가 검색 가로채기가 질문을 목록으로만 답함 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922 에 들어 있음. |

| HA-32 | 없는 코어 타입 이름을 지어내 부름 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922 에 들어 있음. |

| HA-33 | 심의 VOC 미리보기가 새 반환 꼴을 못 펼쳐 0건 | 이미 됨 | recv/request-1030 체크리스트 완료 · 박스 HEAD b0fd922. |

| HA-34 | 허브 응답 접기가 기록에 남지 않음 | 이미 됨 | 에이전트 서버 0d760ea(박스 git log). |

| HA-36 | 좌석 자유 조회에 외부 연결의 확인된 읽기 도구 | 이미 됨 | recv gitlog 5cd1938 / a7980a8(11-05) — 「HA-36 좌석 자유 조회에 선언 백엔드 … 확인된 읽기를 들인다」. 00-INDEX: 11-06 반영. |

| HA-37 | 지정 도구 차례 | 이미 됨 | recv gitlog a7980a8 — 「HA-37 지정 도구 차례를 원래 이름 · 제 앱 키 머리를 뗀 꼴로(siren_list_groups · siren_search_cases 먼저, 안정 정렬)」. 5cd1938 묶음으로 11-06 운영 박스 반영. |

| HA-38 | 심의 수치 대조에서 쪽 번호 다루기 | 이미 됨 | recv gitlog a7980a8(11-05) 「HA-38 천 단위 쉼표는 뒤 묶음이 모두 세 자리일 때만 수 하나(쪽 번호 p.2,3,10 을 큰 수로 읽지 않는다)」, 병합 5cd1938(요청 폴더 HWAXPortal docs/siren-delib). 00-INDEX 보관 줄 — 11-06 운영 박스 반영. |

| HG-01 | search_tools 순위 | 이미 됨 | checklist.md [x] HG-01 (93cda53) |

| HG-02 | ODB 토큰을 헤더로 | 이미 됨 | checklist.md [x] HG-02 (ecde6e2 · dccb620) |

| HG-03 | 401 일 때만 재발급 | 이미 됨 | checklist.md [x] HG-03 (c605b84) |

| HG-04 | REST 중계 SimFlow | 이미 됨 | checklist.md [x] HG-04 (ce31ed1) |

| HG-05 | 영역 분류 미분류 61.8% | 이미 됨 | checklist.md [x] HG-05 (7845ccf) |

| HG-06 | 감사 오류 봉투 ok=false | 이미 됨 | checklist.md [x] HG-06 (be7570f) |

| HG-07 | _meta · ui:// 리소스 중계 | 이미 됨 | checklist.md [x] HG-07 (bbd5c87 — Desktop 확인은 사람) |

| HG-08 | heax PAT 발급 뒤 지우기 | 이미 됨 | checklist.md [x] HG-08 |

| HG-09 | 외부 연결 재시도 백오프 | 이미 됨 | checklist.md [x] HG-09 (bde1017) |

| HG-10 | list_tool_apps needs_connect | 이미 됨 | checklist.md [x] HG-10 (5fe6ea0) |

| HG-11 | graceful shutdown | 이미 됨 | checklist.md [x] HG-11 (177c22a) |

| HG-12 | search_tools 응답 요약 | 이미 됨 | checklist.md [x] HG-12 (93cda53) |

| HG-13 | 안내문 유사도 수치 | 이미 됨 | checklist.md [x] HG-13 (9bb5b17) |

| HG-14 | MCP 세션 클라이언트 trust_env | 이미 됨 | answers.md HG-14 「따른다 … trust_env=False 는 하지 않는다」 |

| HG-17 | connect 반영 지연 | 이미 됨 | answers.md HP-46 · HG-17 |

| HG-18 | /health 에 NO_PROXY 보정 결과 | 이미 됨 | answers.md HG-18 · 519358f |

| HG-19 | '(시험)' 라벨 prod 앱의 검색 처리 | 운영 쪽에서 함 | checklist.md [-] HG-19 「D-1 라벨 바로잡기」(박스 권한표 label, 코드 없음) |

| HG-20 | 나가는 응답 개인정보 가림 | 이미 됨 | checklist.md [x] HG-20 (D-2 · 2a2cba6, 끄기 GATEWAY_PII_MASK=0) |

| HG-21 | 개인정보 가림이 계산 결과 숫자를 망가뜨림 | 이미 됨 | recv/request-1030 체크리스트 완료 · 게이트웨이 HEAD c43382b 에 들어 있음. |

| HG-22 | 담당자 실명 · 메일 · 계정 · 사설 IP 가 답에 나감 | 이미 됨 | recv/request-1030 체크리스트 완료 · REST 다리 몫은 E-2 9b37b31 · 게이트웨이 HEAD c43382b 에 들어 있음. |

| HG-23 | 계산 앱 결과는 IMEI 숫자 꼴 검사 건너뛰기(보조 안) | 대체됨 | HG-21 본안으로 DW-07 이 풀려 넣지 않기로 함(request-1030 C-1). |

| HG-25 | odb-hub 조회 도구 여섯을 git read_tools.json 에 | 이미 됨 | 게이트웨이 58e392a(11-14, HEAD c43382b 포함) — read_tools.json:37-42 에 odb-hub:check_job_stackup · find_job · get_board_layers · get_odb_download · get_volume_result · list_parts. 답장 1… |

| HG-26 | 외부 연결 실패를 상대가 준 상태로 가르기 | 이미 됨 | recv gitlog fb87360 「HG-26 등록 토큰 길 실패를 그쪽이 준 상태로 가른다 — JSON-RPC 오류 문구 맨 앞(SIREN 은 HTTP 200 + '401 token_invalid' 꼴) · HTTP 상태 …」, 병합 469f724(요청 폴더 HWAXPortal docs/siren-delib). … |

| HG-27 | 외부 연결 호출에 요청 id(X-Request-Id) | 이미 됨 | recv gitlog fb87360 「HG-27 선언 백엔드 호출(도구 · UI 자원)마다 X-Request-Id(새 UUID) — 감사 줄 rid 에 같은 값, 선언 칸 request_id: false 로 끈다」, 병합 469f724. 포털 쪽 선언 칸 41e22488 / 518190d3. 00-INDEX 보관 줄… |

| HG-28 | tool_areas.json 에 siren 영역 | 이미 됨 | recv gitlog 469f724 / fb87360(11-05) — 「HG-28 tool_areas.json — siren 은 이미 있는 영역 quality」. 00-INDEX REQUEST-20261104-SIREN 보관 줄: 11-06 07:35 운영 박스 반영. |

| HG-29 | 사설 주소 가림에서 지정 호스트 빼기(mask_keep_hosts) | 이미 됨 | recv gitlog fb87360 「HG-29 선언 칸 mask_keep_hosts(기본 비움) — 그 주소가 http(s):// 바로 뒤에 올 때만 가리지 않는다」, 병합 469f724. 포털 쪽 선언 칸 41e22488 / 518190d3. 11-06 07:35 운영 박스 반영, 박스 값은 사용자 결정에 따라 … |

| HG-30 | tool_areas.json 에 devlab-checklist 가 없음 | 이미 됨 | 게이트웨이 2185b4c(request-1111). |

| HH-01 | 재료 카드 본문 6만 자 절단 → 절 여러 개로 | 이미 됨 | 포털 request-1030/outbound.md:46 — MaterialTwinWeb a3563b6 에서 고침(그쪽 실 DB 153장 분할, 6만 자 넘는 절 0, 바뀐 글 0) · server-setup.md:32 Drive dist-20261031-055937Z. 박스 사본 upstream 448dfa6 에 c… |

| HH-02 | 도는 SIF 를 제자리 cp -p 로 덮어쓰기 | 이미 됨 | HEAXHub e46b8aa · docs/2026-10-27-ops-fixes/checklist.md HH-02 [x]. |

| HH-03 | DocForge SP 거울(코어 받기) 구현 | 이미 됨 | 포털 request-1030/outbound.md:47 — DocForge 8444575(SP 거울을 실제 공개에 맞춤) · 213c411(SP 킷 2026-10-21). HEAXHub d35fa89(11-07 등록 사본 0.3.1 · release bd79e79) · d7098ad(11-12 0.3.2 · rele… |

| HH-04 | 부분 배포가 latest/SHA256SUMS 를 통째로 덮음 | 이미 됨 | HEAXHub 9ce7ee7 · checklist HH-04 [x]. |

| HH-05 | app-data 배포가 knobs.env 를 심을 수 있음 | 이미 됨 | HEAXHub d33457f · checklist HH-05 [x]. |

| HH-06 | 데모 앱 기동 실패 되풀이 · 앱 없는 인스턴스 셸 | 이미 됨 | HEAXHub da9dc3d(_sif_fail · 헬스 영구실패 경로에서 instance_stop) · checklist HH-06 [x] · backend/app/services/integration_launcher.py:613. 10-31 사용자 결정 — HH-06 을 좁힌 5c4e8e7 은 합치지 않음(docs… |

| HH-07 | --root-path 앱 헬스 URL 접두 두 번 | 이미 됨 | HEAXHub b756d44 · checklist HH-07 [x]. |

| HH-08 | 데모 · 원본 저장소 로그 소음 | 이미 됨 | HEAXHub e032f20 · checklist HH-08 [x]. |

| HH-09 | (선택) 형제 앱 주소 HEAX_APP_URL_<slug> | 이미 됨 | HEAXHub fed086f · checklist HH-09 [x]. |

| HH-10-OURS | MaterialTwin 중복 정리용 자연 키 조회 결과를 개발 쪽에 넘기기 | 운영 쪽에서 함 | HH-10 이 막힌 까닭 — 박스마다 id 가 달라 출처 둘 · 물성값 넷의 자연 키를 운영 박스에서 조회해 넘겨야 한다. 넘긴 기록 없음. |

| HH-11 | (선택) MaterialTwin 코어 받기 코드 | 대체됨 | 포털 request-1030/outbound.md:46 — 그쪽 10-31 답 '지금은 필요 없다'. 코드 반영은 없다. |

| HH-12 | (질문) reconcile 과 scan 이 같은 앱을 동시에 띄우나 | 이미 됨 | HEAXHub 1dab32a(잠금, flock) · checklist HH-12 [x]. |

| HH-13 | (질문) MaterialTwinWeb 최신판이 박스 사본 6e45b40 과 같은가 | 이미 됨 | 포털 request-1030/outbound.md:46 「main a3563b6 은 박스 사본 6e45b40 보다 61 커밋 앞」. 박스 사본 upstream 은 지금 448dfa6(11-12). |

| HH-14 [06] | StepForge · DynaForge 운영 전환 매니페스트 넷 | 대체됨 | HEAXHub 5e2cafa(10-31 사용자 결정 — 추적 매니페스트는 그대로, 운영 박스는 docs/2026-10-31-prod-cutover/<박스>-local-overrides/*) · 덮어쓰기 장치 HH-15(0b02759 · 6b53981 · cad8b2b) · 948c98c(11-23 넷째 보류 풀림, … |

| HH-14 [10-30] | DocForge 입력 뿌리 파일을 볼 도구가 없음 | 이미 됨 | DocForge e72cbe5 · ab5547e, HEAXHub 055b023 · d35fa89(등록 사본 0.3.1, bd79e79 — 입력 목록 도구) 박스 git log. |

| HH-15 | (질문) 매니페스트 넷을 당기는 다른 박스가 있나 | 이미 됨 | HEAXHub 0b02759 · 6b53981 · cad8b2b(.portal/manifest.local.yaml 덮어쓰기 장치). |

| HH-16 | (질문) proxy 로 바꾼 뒤 step_forge 서비스 인스턴스를 내리나 | 이미 됨 | HEAXHub c33a9f6 · 27d89fd · 3d16b7a. |

| HH-17 | docforge_list_inputs 의 root_host 가 비어 있음 | 이미 됨 | DocForge 0.3.2 bfa1977 · HEAXHub 등록 사본 d7098ad(11-12, '목록 응답의 note'). |

| HP-01 | deploy-all KooRemapper 재기동 표지(감시 겹침) | 이미 됨 | checklist.md [x] HP-01 deploy.lock.d · 감시 쪽 KooRemapper KR-04 f1ab307 |

| HP-02 | RA 보내기 크기 한도 · 거절 사유 표시 | 이미 됨 | checklist.md [x] HP-02 (2043930) |

| HP-03 | RA 보내기 실패 감사 | 이미 됨 | checklist.md [x] HP-03 (2043930) |

| HP-04 | 일일 백업 KooRemapper 덤프 실패(DBUS) | 이미 됨 | checklist.md [x] HP-04 |

| HP-05 | 등록 토큰 평문 · sqlite 644 | 이미 됨 | checklist.md [x] HP-05 (f2ffa60 — sqlite 600 · 연결 토큰 암호화) |

| HP-06 | 헬스게이트 도구 지도 환경 변수 초과 | 이미 됨 | checklist.md [x] HP-06 |

| HP-07 | TOOL_MAX 덮어쓰기 | 이미 됨 | checklist.md [x] HP-07 |

| HP-08 | repair_mcp 앞 심의 확인 | 이미 됨 | checklist.md [x] HP-08 |

| HP-09 | heax 재검증을 백엔드 수로 | 이미 됨 | checklist.md [x] HP-09 |

| HP-10 | MX 백서 --reload 와 deploy-all git reset | 대체됨 | checklist.md [-] HP-10 「MX 백서 MW-03 이 고쳤다(APP_ENV=development 일 때만 --reload) · 포털 할 일 없음」 |

| HP-11 | services.py 기동 서비스에 NO_PROXY | 이미 됨 | checklist.md [x] HP-11 · HEAD git log services.py 383263ba(docs/request-1027 HP-11) |

| HP-12 | nginx /ste/ read timeout 손잡이 | 이미 됨 | checklist.md [x] HP-12 NGINX_STE_READ_TIMEOUT |

| HP-13 | nginx simflow · 분석 클러스터-llm 갈래 | 이미 됨 | checklist.md [x] HP-13 |

| HP-14 | 사내 DRM 머리 판정 | 이미 됨 | checklist.md [x] HP-14 (2043930) |

| HP-15 | 챗 업로드 목적지 SimFlow | 이미 됨 | checklist.md [x] HP-15 (ff585d2) |

| HP-16 | 위키 꺼짐 때 버튼 · 심의 옵션 숨김 | 이미 됨 | checklist.md [x] HP-16 (138970f) |

| HP-17 | 비밀 백업 자리 겹침 · 박스 파일 누락 | 이미 됨 | checklist.md [x] HP-17 |

| HP-18 | --install-cron 의 crontab 덮어쓰기 | 이미 됨 | checklist.md [x] HP-18 |

| HP-19 | 페르소나 정본 접두 이름 | 이미 됨 | checklist.md [x] HP-19 (42e6648) |

| HP-20 | he-data-coreontology 페르소나 | 이미 됨 | checklist.md [x] HP-20 (62ed7b2 — --apply 는 운영 박스 사람) |

| HP-21 | 카드 본문 검색 스위치를 켜도 검색칸 문구가 그대로 | 대체됨 | 받은 checklist.md `[~] HP-21 … 보류: 화면이 AIDataHub 스위치를 볼 길이 없다. OB-89 로 켤 때 맞추거나 AIDH 가 응답에 스위치 상태를 싣게 청한다` · HEAD AgentDeepView.tsx:323 placeholder 「제목·요약에서 낱말로 찾기」 그대로 · 다시 보낸 re… |

| HP-22 | check-egress NO_PROXY 거짓 알림 | 이미 됨 | checklist.md [x] HP-22 (게이트웨이 519358f — HG-18) |

| HP-23 | 출구 점검에 선언 플랫폼 호스트 | 이미 됨 | checklist.md [x] HP-23 |

| HP-24 | §7 스모크가 self_check 읽기 | 이미 됨 | checklist.md [x] HP-24 (847c403) |

| HP-25 | update-sites 재기동 순서 | 이미 됨 | checklist.md [x] HP-25 고칠 것 없음(회귀 시험 게이트웨이 054d397) |

| HP-26 | 위임 앱 /verify 확인 | 이미 됨 | checklist.md [x] HP-26 |

| HP-27 | install-ste-tunnel --check 15812 | 이미 됨 | checklist.md [x] HP-27 |

| HP-28 | ODB 헤더 꼴 기대 시험 | 이미 됨 | checklist.md [x] HP-28 (40f6b76 · 92ae8d7) |

| HP-29 | AIDH inbox 사본 지우기 | 이미 됨 | checklist.md [x] HP-29 (2043930) |

| HP-30 | 문서 칩 H1 임시 이름 | 이미 됨 | checklist.md [x] HP-30 (2043930) |

| HP-31 | extractedBy 표시 aidh-convert | 이미 됨 | checklist.md [x] HP-31 (2043930) |

| HP-32 | 마지막 도구 지도 유지 | 이미 됨 | checklist.md [x] HP-32 (2043930) |

| HP-33 | 위임 토큰 RA 호출에서 X-Workspace-Slug 빼기 | 이미 됨 | checklist.md 에선 [~] RP-01 회신 뒤였으나 HEAD backend/app/agent/routes.py:1865 「위임으로 받은 토큰이면 싣지 않는다(빈 글, 사용자 결정 2026-11-21 · docs/leftovers-1121 L21-6)」 |

| HP-35 | AIDH merge 뒤 페르소나 미리보기 | 이미 됨 | checklist.md [x] HP-35 |

| HP-36 | 대화 검색 표지 aidh-768 기동값 | 이미 됨 | checklist.md [x] HP-36 (075472f) |

| HP-37 | embedder 절차서 8절 | 이미 됨 | checklist.md [x] HP-37 (78ed68c) |

| HP-38 | 리스크 자격 절차서 기대값 | 이미 됨 | checklist.md [x] HP-38 (78ed68c) |

| HP-39 | env 킷 DELIB_TIMEOUT_S 주석 | 이미 됨 | checklist.md [x] HP-39 |

| HP-40 | 점검표 경로 | 이미 됨 | checklist.md [x] HP-40 (0eb5041) |

| HP-41 | StartPicker 「전체 보기 →」 | 이미 됨 | checklist.md [x] HP-41 (a05fbda) |

| HP-42 | 포털 챗 MCP Apps 패널 호스트 | 이미 됨 | checklist.md 에선 [~] P3 · P4(브랜치)였으나 HEAD git log 에 a694e19c merge(HA-20 · HP-42 P2 ~ P4) · frontend/src/components/chat/McpAppPanel.tsx 있음 · config.py:358 MCP_APPS_HOST 기본 켬(사용자… |

| HP-42(다시) | 웹 챗 MCP Apps 패널 호스트(2단계) | 이미 됨 | 사용자 결정 10-31(B-1 ~ B-7 전부 (가)) 뒤 반영 — 포털 a694e19c backend/app/agent/panel.py(/agent/panel/open · call · read · confirm · close, 패널 PAT, sandbox iframe) · 에이전트 5ee8e79 · a78778b … |

| HP-43 | /ste/ 큰 결과 내려받기 끊김 | 이미 됨 | answers.md HP-43 「nginx 시한 탓이 아니다 … 파트너에게 묻는 것이 맞다(PA-02 · PA-15)」 |

| HP-44 | 거짓 종료코드가 repair_mcp 로 이어지는지 | 이미 됨 | answers.md HP-44 · 고침 099eff2 |

| HP-45 | procedures_concurrency 2 를 6 에 맞출지 | 이미 됨 | answers.md HP-45 「맞추지 않는다 — 2 그대로, 주석만(0b787d5)」 · HEAD config.py:219 주석 |

| HP-46 | 선언 플랫폼 반영 지연 | 이미 됨 | answers.md HP-46 · HG-17 「POST /refresh 한 번이면 바로 붙는다」 |

| HP-47 | /ste/ 결과 파일 속도 · 연결 제한 | 이미 됨 | checklist.md [x] HP-47 손잡이(기본 끔 — D-6) |

| HP-48 | 절차 사전 점검에 선언 플랫폼 토큰 | 이미 됨 | checklist.md [x] HP-48 (D-7 · 3e020aa) |

| HP-49 | 웹 심의 좌석 상한 20 | 이미 됨 | checklist.md [-] HP-49 웹 좌석 20 그대로(D-8) |

| HP-50 | 사용자 정지 때 RA 회수 창구 호출 | 이미 됨 | checklist.md 에선 [~] RP-02 뒤였으나 HEAD backend/app/auth/ra_sso.py:146 「RA 에서 그 사람의 위임 토큰을 지운다(RA v0.170.0 POST /api/auth/sso/revoke) — 계정 정지(auth/routes/local.py)가 쓴다」 |

| HP-51 | 운영자 앱이 게이트웨이에 없는지 미리 알 길이 없음 | 이미 됨 | recv/request-1030 체크리스트 완료 · 포털 HEAD 9b34a4ea 에 들어 있음. |

| HP-52 | 씨앗 절차 둘이 find_reports 봉투를 목록으로 읽어 멈춤 | 이미 됨 | recv/request-1030 체크리스트 완료 · 포털 HEAD 9b34a4ea. |

| HP-53 | 운영자 정의 writes · confirm 이 비었거나 모자람 | 이미 됨 | 10-30 몫은 request-1030 체크리스트 완료, 11-11 다시 몫은 38ac79f(request-1111). 남은 것은 문서대로 정상인 he-cad-stepforge onto_* 3개(C-30), Laminate 는 0.29.0 에서 고침. |

| HP-54 | SmartTwin 운영자 정본에 클러스터 앱 선택 몫 | 대체됨 | OB-92 의 둘째 길(정의 바꾸기)을 고를 때만 청하는 조건부 행. 11-24 잇기 길로 SmartTwin MCP 가 붙어 조건이 사라짐. |

| HP-55 | update-all 챗 도구 문구가 실제와 다름 | 이미 됨 | recv/request-1030 체크리스트 완료 · 포털 HEAD 9b34a4ea. |

| HP-56 | '전작' · '후속' 이 코어 규칙 발동 낱말에 없음 | 이미 됨 | recv/request-1030 체크리스트 완료. |

| HP-62 | he-team.json 에 SIREN 페르소나 넣기(포털 개발 요청) | 대체됨 | SIREN-AGENT-DRAFT.md — 새 판이 박스 설정을 받으면 개발 요청이 아니게 되어 HP-62 는 보내지 않고 둔다. 박스 덧씌우기로 반영됨(SIREN-AGENT-DRAFT-1). |

| HP-64 | 병합이 HE팀 운영자 글을 매번 dev 판으로 덮음 | 이미 됨 | 포털 c0f454ba(request-1111). |

| HP-65 | update-all kr_ 토큰 확인이 provision.env 의 KOORM_BASE 를 읽지 않음 | 대체됨 | 받은 폴더 · 박스 HWAXPortal docs 에서 'HP-65' 0건, 넘김 기록 :526 열 가지에도 없음. 대신 fc56fb28(11-23, 병합 8c63def3, HEAD 9b34a4ea 포함)이 박스 키 KOORM_LOCAL_PARKED 로 같은 증상을 막음 — update-all.sh:2160-2165 … |

| HP-66 | heax-kooremapper_mcp 사후 복구가 멈춰 둔 KooRemapper 를 되살림 | 이미 됨 | dev 에 간 길: 넘김 기록 :526 열 가지 중 2번 · :551-556 '넘김 2' 상세(답장 11-15:12 는 'HP-66 · HP-67 이번 판에 없다' 였고 11-23 넘김으로 들어감). 코드: fc56fb28(11-23, 본문이 HP-66 · HP-67 을 이름으로 듦) · 병합 8c63def3, HE… |

| HP-67 | deploy-all 기본 목록에 늘 kooremapper 가 들어 감독 크론을 다시 넣음 | 이미 됨 | 넘김 기록 :551-556 '넘김 2'(HP-66 과 함께). fc56fb28(HEAD 포함): deploy-all-from-drive.sh:486-513 멈춤 판정 뒤 띄우기 · 이관 · install-autostart 건너뛰고 ○(exit 5), :661 :8700 probe 건너뜀. :163 기본 WANT 는 … |

| HP-70 | 데이터허브 세 nginx 경로가 기본 한도(60 s · 1 MB)로 돈다 | 대체됨 | recv request-1123/request.md:24 가 HP-70 과 이어 짐을 적고, 답장 11-23:250 'HP-70(시간 한도)은 HP-79 로 닫는다'. 720caa4b · 병합 4cf8e6ff(HEAD 포함)가 템플릿 http 수준 proxy_read/send_timeout(기본 600s, hwax.… |

| HP-73 | *-mcp 경로에 스트리밍 묶음(침묵 한도 · 버퍼링 끔) | 이미 됨 | recv request-1123/checklist.md [x] HP-73. 720caa4b(병합 4cf8e6ff, HEAD 포함): gen-nginx-conf.sh:86 '*-mcp)' 갈래에 proxy_buffering off · proxy_cache off · gzip off · proxy_read/send_ti… |

| HP-76 | 백업 세대 정리가 그날 건너뛴 대상의 마지막 덤프까지 지움 | 이미 됨 | 포털 ed7c8014(11-14, HEAD 포함). backup-local.sh:41 KEEP_MIN=3 · :353 '· 보존:' 줄(이번 실행에서 덤프를 못 떠 정리하지 않는다). 답장 11-15:8. fc56fb28 이 멈춘 kooremapper daily 도 hold(:184-187). |

| HP-77 | 걷어 낸 앱의 HEAX 상태 파일이 update-all 을 ✗ 로 만듦 | 이미 됨 | 포털 af74ffd8(11-14, HEAD 포함). update-all.sh:3328 · :3620 매니페스트 없는 상태 파일은 ⚠ '남은 상태 파일 — _deprovision_app.py' 안내. 답장 11-15:9. 운영 박스 HEAXHub var/integration_state 에 *_prod 상태 파일 0(1… |

| HP-78 | Drive 포털 화면 빌드가 HEAD 보다 오래됨 | 이미 됨 | 답장 11-15:10 — Drive images-20261114-163859Z 로 다시 빌드(00023ac7 포함). 이후 라운드도 새 묶음(images-20261124-000907Z, 답장 11-24:10). |

| HP-79 | nginx http 수준 기본 proxy_read/send_timeout(600s) | 이미 됨 | dev 가 request-1123 으로 받음(request.md 가 이 문서 사본). recv request-1123/checklist.md [x] HP-79. 720caa4b · 병합 4cf8e6ff(HEAD 포함): 템플릿 infra/nginx/hwax.conf.tmpl:63-64 proxy_read/send_t… |

| HP-80 | nginx worker_rlimit_nofile(65536) | 이미 됨 | recv request-1123/checklist.md [x] HP-80. 720caa4b(HEAD 포함): 템플릿 hwax.conf.tmpl:9 worker_rlimit_nofile(NGINX_WORKER_RLIMIT_NOFILE, 셸 hard 한도로 낮춤). 운영 박스 생성 conf(11-24 15:55) 지시어… |

| HP-81 | 데이터허브 웹 경로의 큰 응답 버퍼 선택 | 이미 됨 | recv request-1123/checklist.md [x] HP-81. 720caa4b(HEAD 포함): gen-nginx-conf.sh:96-104 · :229-236 NGINX_LARGE_BUFFER_ROUTES(기본 끔). 운영 박스 생성 conf(11-24) 'proxy_buffers 32 64k' 0건 … |

| KR-01 | 과제코드로 과제 잇기 · list_tasks 가 task_code · 별칭을 보고 matched_by 를 단다 | 이미 됨 | KooRemapper ca47363c(KR-01 · KR-02 · KR-17) · docs/01-plan/features/hwax-request-1027.checklist.md KR-01 [x]. 10-30 다시 요청(KR-01 다시, request-1030 04 장)은 f36270f8(sp-receive, 과제 검… |

| KR-01(다시) | DynaForge 과제 검색이 허브 별칭을 안 봄 | 이미 됨 | KooRemapper f36270f(받은 폴더 · gitlog 대조). |

| KR-02 | key 에 '/' 가 든 과제의 개정 조회 404 | 이미 됨 | KooRemapper ca47363c · checklist KR-02 [x]. |

| KR-03 | prestress --csv 주응력이 겹친 고유값 요소에서 틀림 | 이미 됨 | KooRemapper b8eb309e(KR-03 · 회귀 시험 5개) · Drive 070bfb16 dist-20261027-220420Z · checklist KR-03 [x]. |

| KR-04 | 감시 cron 이 배포 중이면 건너뛰기 | 이미 됨 | KooRemapper c2a124b5(KR-04 · KR-05 · KR-09) · f1ab3072(KR-04 버그 둘) · checklist KR-04 [x]. |

| KR-05 | 크론 자체 DB 백업의 세션 버스 변수 | 이미 됨 | KooRemapper c2a124b5 · checklist KR-05 [x]. |

| KR-06 | 받을 코어 타입 고르기(KOORM_SP_CORE_TYPES) | 이미 됨 | KooRemapper 0012f97a(KR-06 · KR-13) · report.md 확장 표 KR-06. |

| KR-07 | 모르는 과제와 '개정 없음' 가르기 | 이미 됨 | KooRemapper e2075f40(KR-07 · KR-16) · 54304cdd(KR-07 고침). |

| KR-08 | find_reports 0건 봉투 | 이미 됨 | KooRemapper d433239d(KR-08). |

| KR-09 | install-autostart.sh 의 crontab -l 실패 처리 | 이미 됨 | KooRemapper c2a124b5 · checklist KR-09 [x]. |

| KR-11 | (유지 요청) prod 이전은 설정으로 — 루프백 바인드 · 웹 접두 · 연동 끄기 | 이미 됨 | KooRemapper report.md:65 「KR-11 은 불변 조건으로 지켰다」. |

| KR-13 | 수동 받기 부분 실패가 409 | 이미 됨 | KooRemapper 0012f97a(KR-06 · KR-13). |

| KR-14 | 코어 받기 클라이언트 프록시 우회 고정 | 이미 됨 | KooRemapper 80312afc(KR-14 · KR-15). |

| KR-15 | plm_sync 머리말 · .env.example 바로잡기 | 이미 됨 | KooRemapper 80312afc. |

| KR-16 | list_tasks 부분 일치로 다른 프로젝트 과제가 섞임 | 이미 됨 | KooRemapper e2075f40(앞부분 · 낱말 경계 순위 · project 거르개 · matched_by). 10-30 다시 요청(KR-16 다시)은 f36270f8. |

| KR-16(다시) | list_tasks 가 key 순으로 먼저 자르고 순위 | 이미 됨 | KooRemapper a3eff43(받은 폴더 · gitlog 대조). |

| KR-17 | 일반 사용자의 ontology_sync_state 읽기 | 이미 됨 | KooRemapper ca47363c · checklist KR-17 [x] · 59240e62(11-11 — 사유 줄 · 오류 글은 관리자만, 일반 사용자는 problem_count 까지). |

| KR-18 | 표준 위임 계약 — /auth/sso/verify · X-Heax-Client 에 gateway | 이미 됨 | KooRemapper e533be8d · report.md 확장 표 KR-18(204/401/404 · gateway 허용). |

| KR-21 | (질문) SmartTwin 잡 소유자를 누가 가를지 | 대체됨 | KooRemapper report.md:61 「상대 클러스터와 합의할 일 — 우리 코드 몫 아님」. 요청서 6절 「잡 소유자 질문(KR-21)은 14-Partner-apps.md PA-17 과 같다」 — PA-17 로 대체. |

| KR-22 | (질문) 공유 NFS 출력 판정 누락 대비 | 운영 쪽에서 함 | KooRemapper report.md:62 「측정 뒤 결정 · 앱 쪽 선택지: 짧은 재시도 · 실행기 출력 목록 읽기」. 먼저 할 일은 우리 몫 OB-49(H5 — /data3 soft→hard 마운트 뒤 측정). |

| KR-23 | 챗이 올린 레시피가 사람 검토 없이 등록됨 | 이미 됨 | 사용자가 자동 관문 유지로 결정, MCP 설명 · TOOLS · SKILL 에 적음(KooRemapper 0c1113f8). |

| KR-24 | 배포 바이너리가 dirty 작업 트리에서 지어짐 | 이미 됨 | KooRemapper ba34e8bc(11-11) — BUILD_INFO 의 describe · worktree 를 소스 변경만 dirty 로, 툴 상태(.bkit/)는 따로 · 7cc8074e(11-11) 빈 갈래에서 게시가 말없이 멈추던 후속 고침. 둘 다 박스 KooRemapper HEAD 76067368 에 … |

| MCP-PATHS-B1 | 박스 중계 mcp-relay 걷기 — HP-72 · HP-74 반영 뒤 | 운영 쪽에서 함 | 운영 박스 systemctl --user is-active mcp-relay = active(11-24). HP-72 · HP-74 는 아직 dev 에 안 감(위 항목). |

| MEMORY-2 | SM-04 그동안의 박스 처리 — grant_only plat:smarttwin-run | 운영 쪽에서 함 | 11-24 16:51 에 박스 권한 덧씌우기에서 smart-twin-mcp 를 grant_only 플랫폼 smarttwin-run 으로 바꿨다(백업 있음). 이름을 적은 사람만 부여했다. HWAXProd ad07a76 README §8 에 되돌리기가 적혀 있다. 요청서 '운용 쪽 처리' 절도 같다. |

| MEMORY-3 | 서버 LLM 카드 검증 하네스 결함 셋 | 대체됨 | recv 운영박스-inbox/2026-11-14.md:28-31 에 '서버 LLM 카드 검증 — 평가 끝, 결과 불가' 와 과제 2 를 하지 않고 Drive 에서 걷었다는 말이 있다. 평가가 닫혀 하네스를 다시 돌릴 일이 없어졌다. |

| MEMORY-7 | report_upload_instructions 가 이름 경로를 박아 둠 | 대체됨 | 11-12 진단의 전제는 '/apps/kooremapper_api 가 되돌림 사본(:8700)으로 간다' 였다. 11-12 밤 전환 창이 /apps/kooremapper · kooremapper_api 를 박스 덮어쓰기 둘로 운영본(16120)에 돌렸고(HWAXProd CUTOVER.md:13 · §11 B-10 기… |

| MEMORY-10 | update-all 이 동결한 step_forge.sif 를 Drive 판으로 덮음 | 이미 됨 | gitlog 168ab627(11-23) 'Merge … 동결한 허브 앱 SIF(HEAX_FROZEN_SIFS)' 와 그 본문(dist-from-drive 에 앱 하나를 빼는 손잡이)이 근거다. recv 운영박스-inbox/2026-11-24.md:36 에 'HEAX_FROZEN_SIFS=step_forge 그대로'… |

| MEMORY-11 | 웹챗 심의 격차 시험 찌꺼기 지우기(RA 2079 · 시험 잡) | 운영 쪽에서 함 | 메모(11-10)에 'delete RA 2079 + test jobs' 로 남아 있고, 초안 §5 도 '시험 찌꺼기는 요청자가 지운다' 고 적었다. 지웠다는 기록은 없다. |

| MEMORY-12 | HWAXProd d8428c8(make-env 가 StepForge SSO 비밀 줄 유지) push | 이미 됨 | 운영 박스의 ~/Projects/HWAXProd 체크아웃 HEAD 가 ad07a76(11-24)이고 d8428c8 이 그 체크아웃에 커밋으로 있다(git cat-file -t → commit, q7). gitlog 차례상 ad07a76 이 d8428c8 보다 뒤다. 메모의 'push 안 함' 은 그 뒤 풀렸다. |

| MEMORY-13 | HWAXProd 배포 스크립트 정리(bundle.sh DF_BASE · release-sf.sh SIF 경로) | 운영 쪽에서 함 | 메모 색인에 'bundle.sh DF_BASE stale' 이 있고, 본문에 release-sf.sh 의 SIF 경로 고정이 있다. 고친 기록은 없다. |

| MEMORY-14 | knox-bridge /internal/notify 배포 | 운영 쪽에서 함 | 메모(11-06)에 'PC 에서 지음, 배포 안 함(사용자 OK 필요)' 으로 적혀 있다. |

| MEMORY-15 | 토큰 절감 2판 다시 켜기와 재측정 | 운영 쪽에서 함 | 11-24 20:08 에 스위치 다섯을 1 → 0 으로 바꿨다(백업 둘). /health 의 offload 는 모두 false, tools-map 은 1978 → 1970 이다(메모). |

| MEMORY-16 | PLM 첨부 받기가 0바이트 파일을 따로 표시하지 않음 | 운영 쪽에서 함 | 메모에 '전체 29,323 중 2,936(10%)이 0바이트 — PLMDefectHub/app/attach.py 가 0 검사를 안 한다' 가 있다. 박스 HEAD app/attach.py 에서 크기 0 · empty 검사 줄을 찾지 못했다(q7). 이 코드는 운영 박스에서 우리가 고치는 것이라 dev 요청이 아니다. |

| MEMORY-17 | 게이트웨이 박스 읽기 덧씌우기의 죽은 dynaforge-prod 줄 셋 | 운영 쪽에서 함 | 박스 HWAXMcpGateway read_tools.local.json 에 dynaforge-prod: 줄이 3개 남아 있다(q7). 그 백엔드는 11-12 전환 창에서 걷혔다. 메모의 '추적 파일 read_tools.json 의 커밋 안 한 +7/-1' 은 지금 git status 가 깨끗해 이미 없다(q7). |

| MW-01 | 위키가 꺼졌을 때 wiki_* 14개 노출 · 환경 변수 이름 노출 | 이미 됨 | MXWhitePaper 76297b6(WK-D70) · 10-30 다시 요청은 bd2e79b(켜짐을 모르면 싣지 않고 다시 보고 싣기). |

| MW-01(다시) | mxwp-mcp 가 API 를 못 보면 위키 도구를 실음 | 이미 됨 | MXWhitePaper bd2e79b(10-30) 박스 git log. |

| MW-02 | pptx 그림 꺼내기가 서버 경로를 제한 없이 받음 | 이미 됨 | MXWhitePaper 76297b6 — http 모드에서 서버 경로를 읽는 도구 셋(extract_pptx_images · import_file · upload_image)을 싣지 않음(stdio 는 그대로). 설명 정리는 bb0a6a1(MW-12). |

| MW-03 | 운영 startscript 의 --reload | 이미 됨 | MXWhitePaper 5a41e3a(WK-D72 — APP_ENV=development 일 때만 --reload · 멈춘 API 로 이관) · deployment-playbook.md:361. |

| MW-05 | claims_affiliation 경로가 운영에서 한 번도 안 돎 | 이미 됨 | MXWhitePaper 06b3d6d(WK-D71 — 소속 '*' 는 팀을 고르는 데 쓰지 않음). |

| MW-07 | (질문) MX 원문 summary · 상세 | 이미 됨 | MXWhitePaper bf316aa · docs/llm-wiki/context-notes.md:292 — 427장 · 요약 빈 320장은 허브와 맞고 원천 탓, 본문 빈 154장은 AIDataHub 평탄화, 보관 상세는 200. |

| MW-12 | 이미지 도구 설명이 없는 upload_image 를 가리킴 | 이미 됨 | MXWhitePaper bb0a6a1(10-30) 박스 git log. |

| NGINX-LIMITS-B1 | nginx 손 넣기 멈춤 확인 · Q31 답 · HP-81 켤지 고르기 | 운영 쪽에서 함 | 답장 11-24:34-35(손 넣기를 멈춘다 — 두 번 들어가면 nginx -t 가 duplicate 로 실패) · :55-61(Q31 확인 넷과 HP-81 켜기 줄), 답장 11-23:253 Q28 '답 없음 — 다음 라운드에 다시'. 운영 박스(11-24 읽기만): 손 넣기 훅 50-ngx-relax.local.… |

| OB-01 · OB-02 · OB-03 | GPU 클러스터 챗 LLM 잡 재기동 · 사전 알림 | 운영 쪽에서 함 | 요청서 '11-14 전' · 끝냈다는 기록을 이번에 못 찾음. |

| OB-04 | 운영 앱 둘의 '(시험)' 라벨 바로잡기 | 운영 쪽에서 함 | 개발 몫 dbbb943 반영 · 박스 권한표 라벨은 남음. |

| OB-26 | ODB 허브 운영자 두기 | 운영 쪽에서 함 | '둔다' 결정 7067f94 · 박스 key_tools 채우기는 남음. |

| OB-33 | hwax-batch 앱 설명 문안 고치기 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-34 · OB-25 | SmartTwinMCP 게이트웨이 등록 · 둘째 터널 | 이미 됨 | 11-24 SmartTwin MCP 게이트웨이 등록 완료(우리 운영 기록). |

| OB-59 | StepForge 과제 찾기 이름 길 SIF 대조 | 운영 쪽에서 함 | 요청서 상태 '개발 SIF 대기' · 이번에 재시험 기록 못 찾음. |

| OB-60 · OB-61 · OB-62 | 챗 업로드 손 시험(M-1 ~ M-6) | 운영 쪽에서 함 | 요청서 상태 '돌리지 않았다'. |

| OB-63 | 자기검증 손 시험(M-7 ~ M-10) | 운영 쪽에서 함 | 요청서 상태 남음. |

| OB-64 · OB-65 | 위키 버튼 숨김 · 위키 질문 확인 | 운영 쪽에서 함 | 요청서 상태 남음 · HA-08(다시) · MW-01(다시) 는 반영됨. |

| OB-68 | VOC 화면 손 시험 · get_voc_summary 한 번 | 운영 쪽에서 함 | 요청서 상태 남음. |

| OB-71 | '예고만 하는' 호출 재측정 | 운영 쪽에서 함 | 요청서 상태 남음 · 두 QA 에 기록 없음. |

| OB-85 | 챗 사용자 우회 안내 걷기 | 운영 쪽에서 함 | 요청서 '걷을 조건이 찼다'(OT-06 ~ 10 첫 도구 코어 5/5 · 정본 허브 14/16). |

| OB-87 | 빈 전문가 · 데모 카드 운영 박스 몫 지우기 | 운영 쪽에서 함 | AD-05 · AD-06(다시) 이 사용자 결정 상태라 대기. |

| OB-89 | 지식카드 본문 검색 스위치 켤지 | 대체됨 | AD-04(다시) 실측(끔 8 ms · 켬 6.4초, 찬 기동 45초 넘음)으로 끈 채 두기로 정리됨(request-1030 C-3 · C-16). |

| OB-91 | 박스 우회 CHAT_STABLE_PREFIX=0 걷기 | 운영 쪽에서 함 | HA-26 이 들어옴(7ca3a2e · e94bc09). 박스 .env 는 읽지 않아 우회 줄이 남았는지는 못 봄. |

| OB-92 | SmartTwin 운영자 잇기 | 이미 됨 | 11-24 GPU 클러스터 SmartTwin MCP 운영 배포 · 게이트웨이 등록(우리 운영 기록). 실행 권한은 지정 인원에게만 줌. |

| OB-93 | 도구 설명 예산 40000 → 30000 비교 | 운영 쪽에서 함 | 요청서 상태 '남았다' · 뒤 기록 없음. |

| OB-94 | DocForge 입력 뿌리에 시험 파일 하나 | 운영 쪽에서 함 | 요청서 상태 '남았다' · 뒤 기록 없음. |

| OB-95 | 생각 강도 high · medium 비교 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-96 | 허브 큰 응답 견본을 이름 지워 개발에 넘김 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-97 | SimFlow 패널 길 · arp_upload_open 반환 확인 | 운영 쪽에서 함 | 요청서 상태 '남았다' · Q-A1 답 기록 없음. |

| OB-98 | 외부 연결 앱 손 시험 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-99 | 실제 search_tools 질의 8건으로 순위 재측정 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-100 | 15자리 번호가 Luhn 우연 통과로 가려지는지 확인 | 운영 쪽에서 함 | 요청서 상태 '남았다'. |

| OB-101 | StepForge 코어 받기 cron 에 주 1회 --full | 운영 쪽에서 함 | 요청서 상태 '남았다' · T-17 과 같은 건. |

| OB-102 | DocForge 평문 pptx 길 한 번 | 운영 쪽에서 함 | 요청서 상태 '남았다' · H-05 와 같은 건. |

| OB-103 | SimFlow 목적지 첫 실주행 | 운영 쪽에서 함 | 회신 대기 · PA-12 답 기록 없음. |

| OD-1 | ODB 허브 코어 받기(plm_task · plm_model) | 이미 됨 | 23-2 §1 — ping: enabled · ready, 4 타입 모두 ok(마지막 11-24 03:30 KST). 프로젝트 635 · 과제 5,663 · 개발모델 5,903 · 모델코드 2,942(코어와 같음). OUTBOUND-20261101 1절도 11-01 에 들어온 것으로 적음. |

| OD-2 | find_job 이 코어로 풀기 | 이미 됨 | 23-2 §1 — 과제 A 는 matched_by task_name · via task → project · core_key P1, C1 은 task_code, X1 은 model_code(find_job, 11-24 실측). |

| OD-3 | 보드 행에 ontology{project_key, model_code_key} | 이미 됨 | 23-2 「16 의 OD-1 ~ OD-3 은 들어왔다」, §4 에서 뺀 것으로 적음. OUTBOUND-20261101 1절 — 11-01 에 행의 코어 key 와 두 key 로 거르는 list_jobs 인자가 들어온 것을 확인. |

| OD-4 | 보드 → 코어 연결률 높이기 · 이유 집계 | 대체됨 | 23-2 ODO-1(지역 표기 → 모델코드, P1 보드 33장 중 28장 key 없음) · ODO-2(대기 건 목록 도구)가 대신한다. 11-24 ping: 보드 1,460 · 프로젝트 연결 1,101 · 모델코드 연결 787 · 대기 정확 15 · 대기 부분 162 · 코어에 없음 182. |

| OD-6 | ping 에 받기 상태 · 연결 수 | 이미 됨 | 23-2 §1 — ping 에 받기 상태(4 타입 ok)와 mapping(보드 1,460 · 연결 1,101/787 · 대기 15/162 · 없음 182)이 있다. |

| OD-7 | find_job 설명 고치기(과제명 ≠ 프로젝트 코드) | 이미 됨 | OUTBOUND-20261101 1절 — 11-01 에 OD-7 설명이 바뀐 것을 확인. |

| OL-1 | 게이트웨이 로컬 도구 ontology_lookup | 이미 됨 | dev 가 HWAXPortal docs/ontology-first/request-1116.md 로 받음(cae00-inbox/2026-11-17.md:3 · :8-12 OL 표). 운영 박스 HWAXPortal docs/ontology-first/checklist.md:86-92 모두 [x] — 게이트웨이 c75bc… |

| OL-2 | search_tools 에서 ontology_lookup 첫 줄 · object 인자 · hint | 이미 됨 | ontology-first/checklist.md:88 [x] OL-2 — 게이트웨이 c75bc05, 스위치 onto_lookup_first 기본 끔(OF-36). |

| OL-3 | 포털 어휘표에 앱별 lookup 칸 | 이미 됨 | 포털 d1686bc8 · 92069119(ontology-first/checklist.md:86 [x] OL-3). HEAD 9b34a4ea backend/config/core_vocab.json:76-80 lookup 에 failuretrace · caegroupdatahub · heax-kooremapper_mc… |

| OL-4 | 온톨로지 정답쌍 36 평가셋 추가 | 이미 됨 | ontology-first/checklist.md:90 [x] OL-4 정답쌍 36 — 게이트웨이 8b35e18. |

| OL-5 | 동의어 둘(온톨로지 · ontology) 기본값으로 옮기기(질문) | 이미 됨 | ontology-first/checklist.md:92 [x] OL-5 — 사용자 결정 11-17 옮김, 게이트웨이 38769b7(OF-42). cae00-inbox/2026-11-17.md:22 — 박스 덧씌우기의 동의어는 박스가 걷을 일. |

| ONTOLOOKUP-1 | 질문 1 — StepForge 코어 개체 키 꼴 · lookup 도구 선택 | 이미 됨 | 답: HWAXPortal docs/cae00-inbox/2026-11-17.md:15-17. HEAD core_vocab.json:80 heax-step_forge → onto_search(q={key}, type_slug, resolve=true). |

| ONTOLOOKUP-2 | 질문 2 — 타입 고르기를 게이트웨이 코드로 할지 objects_resolve_many 로 할지 | 이미 됨 | 답: HWAXPortal docs/cae00-inbox/2026-11-17.md:19-20(c75bc05 에 타입 고르기 · 세 판정 착지). |

| OP-1 [20] | CL-01 전에는 받기는 cron · 워커, 잇기는 사람이 화면에서 | 운영 쪽에서 함 | 20번 §5 우리 몫(보내지 않음). 훅 자리는 SRC-12 로 착지(포털 99f42a24) — 이제 BOX-15 가 이어받음. |

| OP-1 [16] | (우리 몫) ARP 용 core:read 토큰 발급 | 운영 쪽에서 함 | 23-3 — ARP 가 토큰으로 매일 받기를 하므로 토큰은 있다. 그러나 23-3 Q-1 에 「지금은 넓은 범위 토큰이다」 — core:read 전용 발급은 아직이다. |

| OP-2 | (우리 몫) 기준 주소 · 경로 함정 안내 보내기 | 운영 쪽에서 함 | ARP · ODB 허브 모두 받기가 ok(23-2 · 23-3) — 안내가 전달돼 쓰이고 있다. |

| OP-3 | (우리 몫) ODB 허브 옛 토큰 지움 확인 | 운영 쪽에서 함 | OUTBOUND-20261101 — 11-01 에 옛 넓은 토큰이 남아 있었다. 23 §4-1(11-24) 목록은 범위가 좁아(안 쓰는 것 · 30일 넘은 것 · 고른 것) 옛 토큰이 거기 없다고 지워졌다고 볼 수 없다. 직접 확인한 기록이 없다. |

| OP-4 | (우리 몫) 플랫폼 바뀐 뒤 게이트웨이 도구 목록 확인 | 운영 쪽에서 함 | 게이트웨이 HG-25(58e392a, 11-14)로 read_tools 에 odb-hub 조회 도구 6개가 들어갔고, 회신함 2026-11-15 에 HG-25 끝남. |

| OP-5 | (우리 몫) 확인 시험 T-1 ~ T-12 돌리고 문서 갱신 | 운영 쪽에서 함 | 11-24 실측으로 23-2 · 23-3 을 새로 썼다(과제 A · C1 · P1 · X1 시험). T-1 ~ T-12 전부를 돌린 기록은 없다. |

| OUTSTANDING-4.1 | RA 가 SSO 새 계정에 home 워크스페이스 배정 | 대체됨 | 10-27 플랫폼별 묶음 platform-requests/11-ReportArchive.md RP-01 · RP-15 · RP-14 로 옮겨졌다(00-INDEX 1절 11번 행 'SSO 계정 홈 워크스페이스'). |

| OUTSTANDING-4.2 | TestScope SSO 판 배포 | 대체됨 | 14-Partner-apps.md:10 에 '10-27 에 v0.65.0 이고 /api/auth/sso 가 있다' 고 적혀 있다. 메모(11-13)에는 v0.65.2 로 적혀 있다. 남은 것은 PA-03(시크릿 설정)뿐이다. |

| OUTSTANDING-4.3 | ARP 서버 간 /mcp 서비스 토큰 | 대체됨 | recv request-1027/02-HWAXMcpGateway.md:194 에 '10-27 박스 실측으로 게이트웨이의 arp 백엔드가 토큰을 싣고 정상' 이라고 적혀 있다. 상대 팀 확인만 14-Partner-apps.md PA-10 에 남았다. |

| OUTSTANDING-5.1 | 소속 공란 16명 CAEG 지정과 대기 33건 | 운영 쪽에서 함 | 문서가 '요청 대상 아님 — 저희가 정할 것' 으로 분류했다(10차 §2). |

| OUTSTANDING-5.2 | 금고 등록자 9명 워크스페이스를 RA home 으로 옮길지 | 운영 쪽에서 함 | 같은 결정이 platform-requests/11-ReportArchive.md RP-21 과 90-OURS-box-todo.md OB-23 에도 있다. |

| OUTSTANDING-5.3 | 신규 SSO 사용자의 RA 보고서 함 확인 | 운영 쪽에서 함 | 문서의 '저희가 확인할 것' 이다(8차 §9-②). RP-15 답과 이어진다. |

| OUTSTANDING-5.4 | mock 시절 공용 계정 PAT 27개(무기한 9개) 정리 | 운영 쪽에서 함 | 문서의 '저희가 정할 것' 이다(10차 §4). 메모 cutover-1112 에는 PAT id 1 을 2027-02-15 까지 두기로 적혀 있다. |

| P-1 [11-17] | artifact_to_ste_upload — 스테이징 쪽(게이트웨이, 11-17 초안) | 이미 됨 | HWAXMcpGateway ec91b62(11-18 「feat(P-1 artifact_to_ste_upload …)」)는 박스 HWAXMcpGateway HEAD c43382b 의 조상(merge-base 확인). HWAXPortal docs/ste-stepforge-1117/PLAN.md P-1 「지음 ec91b6… |

| P-2 | 시험 조건 → 환경 값(11-17 초안) | 이미 됨 | gitlog HWAXMcpGateway dd304eb(reliability_test_conditions, 11-18). PLAN.md PT-R2 · P-2 '지음 dd304eb'. |

| P-3 | 운영본 표시(11-17 초안) | 대체됨 | PLAN.md PT-R3 · P-3 — GW-05(게이트웨이 fd1f52d)가 env · canonical · aliases 를 싣고, build 받는 쪽은 629f32c · HEAXHub ec240e1. StepForge 줄의 build 가 비는 남은 문제는 REMAINING PT-2 로 넘어갔다. |

| PA-01 | 해석 클러스터 대시보드 파일 반입 init 권한 거절 | 운영 쪽에서 함 | memory(SmartTwin MCP 배포 11-24): 사용자 OK 로 업로드 베이스 /shared/uploads 소유를 root 에서 대시보드 서비스 계정으로 바꿈(백업 · 되돌리기 명령 기록). 수락 실주행(init → chunk → complete) 기록 없음 — 우리 쪽 확인으로 남김. |

| PA-16 | SmartTwinMCP(:5013) 운영 배포 | 이미 됨 | memory(SmartTwin MCP 배포 11-24): HWAXProd deploy/stm 으로 운영 배포(release r20261124b-ea9ebe5), 게이트웨이 23 도구 등록, 위임 verify 204. |

| PA-17 | (질문) 스마트트윈 잡 소유자를 누가 가르나 | 대체됨 | memory(SmartTwin MCP 배포 11-24): 대시보드 SSO 꺼짐으로 /api/me 가 모두에게 admin(SM-04) — 고침은 deploy/stm/KOOSLURM-REQUEST-1124.md SM-04, 아직 보내지 않음. 그동안 grant_only plat:smarttwin-run 으로 이름 적은 … |

| PA-19 | SmartTwinMCP extra_scenario_overrides 의 environment 잠금 | 이미 됨 | request-1030/outbound.md: 10-30 · 10-31 SmartTwinMCP 세션에 보냄. 박스 읽기(q2) 배포 소스 src/dashboard/smarttwin_mcp/tools/_shared/scenario_builder.py:89-93 LOCKED_SCENARIO_KEYS = {environm… |

| PA-20 | 클러스터 조회가 사설 IP · 제출자 메일을 줌 | 이미 됨 | 4f5e0e0 반영(받은 폴더 · gitlog 대조). |

| PA-21 | ste 해석기 SIF 자리가 계산 노드에서 안 보임 | 이미 됨 | recv/request-1111 — 결정 (가) 11-12 · main 1e53260. 11-17 배포 끝남(우리 운영 기록). |

| PLO-1 | 결함 응답에 코어 key(etcModel → plm_model → 과제 · 프로젝트 · 모델코드) | 운영 쪽에서 함 | 받은 폴더 · 전 리포 PLO- 0건(q1). 박스 PLMDefectHub 폴더는 git 이 아니고 소스(.venv 밖) grep core_key · core_type · rootdesign 0건(q2 · q3). / 검증: 우리 앱이다 — 박스 PLMDefectHub 는 git 없는 폴더이고 README 가 「포털… |

| PLO-2 | plm_defect_search 에 core_type · core_key 인자 | 운영 쪽에서 함 | 받은 폴더 · 전 리포 PLO- 0건(q1). / 검증: 우리 앱이다 — 박스 PLMDefectHub 는 git 없는 폴더이고 README 가 「포털 코드는 건드리지 않는다 — 설정 6곳으로 붙는다」 는 운영 쪽 감싸기 서비스로 적는다(vq4 A). memory(PLM 덤프 쓰기 메모 · 10-25 운영 결정 메모)… |

| PLO-3 | (선택) 개발모델 폴더에 코어 key | 운영 쪽에서 함 | 받은 폴더 · 전 리포 PLO- 0건(q1). / 검증: 우리 앱이다 — 박스 PLMDefectHub 는 git 없는 폴더이고 README 가 「포털 코드는 건드리지 않는다 — 설정 6곳으로 붙는다」 는 운영 쪽 감싸기 서비스로 적는다(vq4 A). memory(PLM 덤프 쓰기 메모 · 10-25 운영 결정 메모)… |

| PT-1 | 개인 토큰이 없을 때의 안내(등록 방법) | 운영 쪽에서 함 | HWAXPortal docs/ste-stepforge-1117/PLAN.md PT-R2 — '토큰이 없으면 needs_connect 와 등록 안내, 그리고 "사람에게 묻는다" 를 답한다'(dd304eb). checklist.md BG-5 · PT-1 '[ ]' — 토큰 미등록 계정으로 확인 대기, 사람 몫. 공용 프… |

| PT-R1 | material_gas_transport → gas_transport_lookup(11-17 초안) | 이미 됨 | gitlog HWAXMcpGateway 6dcef62. PLAN.md PT-R1 '지음 6dcef62', checklist '[x] dev 실호출(11-18) — D · S · P 셋이 다 있는 재료 둘'. |

| PT-R2 | 시험 조건 → 해석 환경 값(11-17 초안) | 이미 됨 | gitlog HWAXMcpGateway dd304eb. PLAN.md PT-R2 · P-2 '지음 dd304eb'. |

| PT-R3 | 운영본 표시(11-17 초안) | 대체됨 | PLAN.md PT-R3 — GW-05 fd1f52d(env · canonical · aliases), build 받는 쪽 629f32c, HEAXHub ec240e1. StepForge 줄 build 가 비는 문제는 REMAINING PT-2 로 넘어갔다. |

| PT-R4 | STE 잡 목록 '내 잡' 표시(11-17 초안) | 대체됨 | PLAN.md PT-R4 — 게이트웨이는 바꿀 것이 없고, ste 판이 나오면 확인만 한다. checklist '[ ] ste ST-R9 판이 나오면 게이트웨이를 거친 답에 mine 이 오는지 확인'. ste 쪽은 REMAINING ST-14 로 넘어갔다. |

| Q-1 | DynaForge 가 받을 타입 | 이미 됨 | 21번 §6 '11-09 답: 전부' · BOX-01 반영 · 포털 5f28bf36 CK-2(core-link checklist.md:10 [x] 사용자 결정 여섯). |

| Q-2 | SignalForge 를 코어 잇기에 넣을지 | 이미 됨 | CK-2 결정 '다시 엶' → SignalForge 47226ac · 5074c99(checklist.md:54). |

| Q-3 | StepForge 개정 지정을 남의 과제까지 할지 | 이미 됨 | CK-2 결정 — 규칙은 모든 과제, 사람 선은 맡은 과제만(StepForge 세션에 알림, checklist.md:16). |

| Q-4 | 다른 운영 인스턴스까지 같은 차례로 할지 | 이미 됨 | CK-2 결정 '둘 다 같이' — HWAXPortal docs/core-link/context-notes.md:96(사본에 같은 판). |

| Q-5 | DynaForge 다리(SRC-08) 가운데 무엇을 넣을지 | 이미 됨 | CK-2 결정 — 다리 셋 모두(KooRemapper 계획 ed38722 · 착지 5d4b1f94). |

| R-02 | 전문가 저장 뒤 500 | 이미 됨 | AD-21 로 들어옴(request-1030). |

| R-03 | AIDataHub 10-27 미반영 7건 | 이미 됨 | AD-01 · 03 · 04 · 07 등이 request-1030 으로 들어옴 · AD-05 · 06 만 사용자 결정. |

| R-05 | find_reports 봉투로 씨앗 절차 멈춤 | 이미 됨 | HP-52 로 들어옴(request-1030). |

| R-06 | 심의 VOC 미리보기가 results 를 안 풂 | 이미 됨 | HA-33 으로 들어옴. |

| R-07 | invoke_tool 허브 응답 접기 · 남의 심의 이어하기 · 위키 문구 | 이미 됨 | HA-34 0d760ea · HA-06 3e7f00b(10-27) · HA-08(다시) 반영. |

| R-08 | 정본 허브 고르기 · REST 다리 개인정보 | 이미 됨 | HG-22 + E-2 9b37b31 반영. |

| R-10 | MX 백서 미반영 5건 | 대체됨 | fail open 몫은 MW-01(다시) bd2e79b 로 닫힘. 10-10 뒤 MX 커밋은 bd2e79b · bb0a6a1 · bf316aa · 5a41e3a · 06b3d6d · 76297b6 뿐이고 나머지 5건이 어느 것인지 이번에 가리지 못함. / 정리 11-25: MXWhitePaper MW-* 개별 행으로… |

| R-11 | HEAXHub SHA256SUMS 9줄 · 미반영 2건 | 이미 됨 | HEAXHub HH-04 9ce7ee7(10-27) 부분배포가 latest/SHA256SUMS 과거분을 지우지 않게 · 박스 캐시 .drive-dist/SHA256SUMS 30줄(11-24 박스 확인, 9줄 아님) · HH-06 은 사용자 결정으로 안 합침(beebec5) · HEAXHub 10-27 행은 10-31… |

| R-12 | 리스크 앱 새 판 없음(RK-02 등 5건 · RK-01) | 대체됨 | 리스크 앱 리포가 박스에 없음. 포털 git 에 11-17 리스크 앱 RK-01 ~ 07 쓰기 도구 반영(7c762873)이 있어 '새 판 없음' 전제는 낡음 — 옛 RK 행과 같은 번호인지 못 가림. / 정리 11-25: 리스크 앱 RK-01~06 개별 행이 done 으로 확인됨 — 낡은 묶음 행은 뺀다. |

| R1111-BOX4 | 11-11 박스 몫 넷(코어 미러 주소 · 운영 사본 env 값 · 되돌림 절차 · 운영 박스 전용 연산자 두 개의 쓰기 · 확인) | 운영 쪽에서 함 | REQUEST-20261111 이 우리 몫으로 적고 요청에서 뺐다 · 처리 기록은 이번에 찾지 못함. |

| R1111-DEVLAB-ARGS | 개발실 체크리스트 도구 인자 설명 0/26 | 운영 쪽에서 함 | REQUEST-20261111 이 우리 중계 서버 몫으로 적고 뺐다 · 처리 기록은 이번에 찾지 못함. |

| RK-01 | RA 반영 보내는 쪽(서비스 계정) | 이미 됨 | 리스크 앱 사본 git log 7b1042d `merge(RK-01 — 리스크 앱 → Report Archive 보내는 쪽 · 거두기): 서비스 계정으로 지식 그래프 op 를 보낸다 … 사용자 결정 10-31 D-1 (가)` · main.py:208 external_sync_send=ra_sender · ra_cli… |

| RK-02 | PAT 발급 청중에 step-forge | 이미 됨 | 사본 HEAD frontend/src/api/portalPat.ts:31 audiences ["mcp-gateway", "step-forge"] · SettingsPage.tsx:52 · :407 안내에 step-forge |

| RK-03 | 웹 경로 포털 PAT 자동 등록 · 갱신 화면 | 이미 됨 | 사본 HEAD frontend/src/components/AutoPortalPat.tsx · api/autoPortalPat.ts:12 autoRegisterWanted(portal_pat.auto 의 enabled && due) · risk.api.ts:292 PUT me/portal-pat-auto · 갱신 문턱… |

| RK-04 | RA 반영 안 됨과 사유를 화면에 | 이미 됨 | 사본 HEAD Badge.tsx:133-140 ExternalSyncBadge 가 `RA {sync.ra.state}` 와 note 를 그림(객체를 그대로 그리던 꼴 고침) · TargetPage.tsx · ProjectPage.tsx 에서 씀 |

| RK-05 | cred.key 개발 폴백 사용을 설정 화면에 | 이미 됨 | 사본 HEAD SettingsPage.tsx:511-519 cred_key 칸 · 키 출처(cred_key_source) 칸 · :500 BoxReasons |

| RK-06 | secrets_valid=false 까닭을 나눠 보이기 | 이미 됨 | 사본 HEAD SettingsPage.tsx:500 `<BoxReasons reasons={me.data.box.reasons} />` |

| RK-07 | backup_unencrypted 알림 — 백업 키 운영 전제 | 운영 쪽에서 함 | review-07-hwax-risk.md RK-07 「10-17 결정 2 로 이미 정했다(암호화해 매일). 박스 몫」 · 사본 config.py:84 에 'HWAXRISK_BACKUP_KEY 없으면 평문, /api/health 에 backup_unencrypted' 설명 있음 |

| RK-08 | risk_concurrency 2 를 심의 6 에 맞출지 | 이미 됨 | review-07 RK-08 「두 값은 서로 다른 것을 센다. 맞출 까닭이 없다」 · 사본 config.py:405 HWAXRISK_CONCURRENCY 기본 2 · 포털 config.py:219 주석 고침(HP-45 0b787d5) |

| RK-09 | 필수 비밀 키 목록 | 이미 됨 | review-07 RK-09 「필수는 HWAXRISK_CRED_KEY 하나다」(8d672c7 이 하나로 줄임) |

| RK-12 | 리스크 심사 러너가 지정 도구로 SIREN 셋을 싣기 | 이미 됨 | recv gitlog 5cd1938(엔진 몫, 11-05). 00-INDEX REQUEST-20261104-SIREN 보관 줄 — 리스크 앱 97d5aef, 11-06 07:35 운영 박스 반영. |

| RQ-07 | (질문) 시험 날짜 · 보드 | 대체됨 | 실제 제출이 11-06 · 11-07 · 11-09 · 11-13 에 이뤄짐(메모리, 18-1). 남은 다시 보내기 시점은 18-1 RQ-16 으로 옮겨 감(18-1 RQ-16 행이 RQ-07 을 근거로 적음). |

| S-1 [11-17] | (STE) 개구부를 구멍 영역 패치로(11-17 초안) | 대체됨 | 11-18 전달(checklist.md, gitlog 5041b9d9). 11-21 재시험에서 같은 결함이 다시 나와 REMAINING ST-1 로 넘어갔다. |

| S-1 [22-1] | DocForge 판독 동시 수 2 → 4(박스 knobs.env) | 운영 쪽에서 함 | 11-10 16:17 적용(22-1 §7-5). 11-24 박스 /data/appdata/doc_forge/knobs.env(644 · 221바이트 · 11-10 16:17)에 DOCFORGE_VLM_MAX_CONCURRENCY 키가 있다(이름만 읽음). |

| S-2 [11-17] | (STE) 개구부 미매칭이면 결로 단계 · 잡 실패(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-2 로 넘어갔다(브리지 85256df dev). |

| S-2 [22-1] | DocForge 판단 모델을 심의 모델로(박스 knobs.env) | 운영 쪽에서 함 | 11-10 16:17 적용 · 시험 잡에서 판단 캐시가 심의 모델로 남는 것 확인(22-1 §7-5). 11-24 knobs.env 에 DOCFORGE_LLM_BASE_URL · DOCFORGE_LLM_MODEL 키가 있다(값은 읽지 않음). |

| S-3 [11-17] | (STE) ste_job_summary(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-5 로 넘어갔다. |

| S-3 [22-1] | DocForge 동시 잡 수 1 → 2 | 대체됨 | 설정으로 안 됨 — 매니페스트 launch env(HEAD 948c98c manifest.yaml:31)가 knobs.env 를 이긴다. 22 IR-24 로 대체. |

| S-4 [11-17] | (STE) 결로 후처리 단위 · 자릿수(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-9 로 넘어갔다. |

| S-5 [11-17] | (STE) condensation_scenario_build(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-10 으로 넘어갔다. |

| S-5 [22-1] | 판독 동시 수 4 뒤 웹 챗 첫 답 시간 · 새 덱 걸린 시간 재기 | 운영 쪽에서 함 | 22-1 §7-5 에 '아직 볼 것' 으로 남아 있고, 잰 기록이 22-1 · 00-INDEX 에 없다. |

| S-6 | (STE) part-study 단계 고르기(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-11 로 넘어갔다. |

| S-7 | (STE) 결로 판정 기준 · 판정(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-6 으로 넘어갔다(브리지 dev 반영). |

| S-8 | (STE) get_job_file 앞부분 · 범위(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-16 으로 넘어갔다. |

| S-9 | (STE) 장시간 결로 모드(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-17 로 넘어갔다. |

| SE-1 | AIDataHub 병합을 파일 이름이 아니라 내용으로 건너뛰기 | 이미 됨 | 조각 길로 반영됨. gitlog: AIDataHub 2f6d60b · 7e98ad6(11-04 조각 스냅숏), 9b1538f · 5abff48(AP-14 낡은 목록이면 전체 길), 포털 e84d1d0c(update-all §3 조각 길 먼저) · de25d721. 박스 /data/backups/aidh 에 pre-p… |

| SE-5 | staging 적재를 병합할 표만, 색인 없이 | 이미 됨 | 조각 길로 반영 — AIDataHub 2f6d60b(11-04): '스키마로 빈 스테이징(색인 · 제약 없음) → 받은 조각만 싣기'(gitlog :136), AP-2 · AP-9. 3번(TEMP 표로 바로)은 요청서가 스스로 거둠. 전체 길은 대비 길이라 그대로. |

| SF-1 | build_cavity 파트 목록 인자 · 접수 때 검사 | 이미 됨 | HWAXPortal docs/ste-stepforge-1117/checklist.md(박스 HEAD 9b34a4ea) — 'SF-1 ~ SF-12 보냄 — 받음 · D-708 1차(SF-1 · 2 · 3 · 8 · 9 · 11 · 12)'. cae00-inbox/2026-11-23.md:18 — main edcddf… |

| SF-2 | part_outline_2d 코너가 deflection 에 따라 바뀜 · 복합 코너 · 접촉 넓이 0 | 이미 됨 | checklist.md — D-708 1차에 SF-2. 'SF-2 의 접촉 넓이 0 은 참값으로 보임(contact_zero_why)'. context-notes.md SS-10 — 창 유리와 틀이 테이프를 사이에 두고 떨어져 있다. 이번 판부터 contact_zero_why · relation_status 를 싣는… |

| SF-3 | cavity_openings · cold_surface_from_parts 실제 공동에서 확인 · 바깥 셸 구멍 | 이미 됨 | checklist.md — D-708 1차에 SF-3. cae00-inbox/2026-11-23.md:18 edcddf44(SF-1 ~ SF-12). |

| SF-5 | 둥근 사각형 출력 ↔ 레디쉬 geometry 규약(format=reddish_geometry) | 이미 됨 | checklist.md — '[x] SF-5 ↔ ST-7 — StepForge 가 geometry 절 변환(축 · 원점 · 변 4묶음 · UV 창), ST-7 은 손대지 않고 싣고 검사만(두 세션 합의 11-22)'. context-notes.md SS-12 — 운영 노드 reddish_geometry 가 geome… |

| SF-8 | list_artifacts part 필터가 0행 | 이미 됨 | checklist.md — D-708 1차에 SF-8, '짚은 것 — SF-8 원인(산출물 열쇠 글롭)'. cae00-inbox/2026-11-23.md:18 edcddf44. |

| SF-9 | uv_mask_from_region 응답 접기 | 이미 됨 | checklist.md — D-708 1차에 SF-9. cae00-inbox/2026-11-23.md:18 edcddf44. |

| SF-11 | leak_report — 외피 3파트가 예산 1.1배로 멈춤 · 서명에 parts | 이미 됨 | checklist.md — D-708 1차에 SF-11. '[ ] SF-11 … 11-23 답: 지금 인자 목록에 parts 있음(array 또는 null) · StepForge 줄 1. 재시험 때 안 보인 까닭은 못 가림(SS-11)'. |

| SF-12 | 확인만 — export_part_step source · to_ste_upload, job_status.queue, stl 요약 | 이미 됨 | checklist.md — '짚은 것 — SF-12 의 source · to_ste_upload 는 11-18 결정으로 없다(옮기기는 게이트웨이 한 길)'. context-notes.md SS-10 같은 내용. SS-7 — D-707 2차에 F-5(잡 대기 정보), 1차에 SF-R6(stl 요약). |

| SF-R1 | export_part_step — 파트 하나 STEP 반출(11-17 초안) | 이미 됨 | context-notes.md SS-7 — D-707 1차 SF-R1(산출물 kind part_step, to_ste_upload 는 안 만든다). REMAINING '풀린 것' — 과제 A 창 유리 part_step 155,360 B, 되읽기 check same true(솔리드 1 · 부피 5,487.263996 … |

| SF-R2 | part_outline_2d — 평면 외곽(11-17 초안) | 이미 됨 | SS-7 — D-707 1차 SF-R2. REMAINING '풀린 것' — part_outline_2d 가 외곽 다각형 · 구멍 · 변별 이웃을 준다(deflection 0.1). 남은 것은 SF-2 · SF-5 로 넘어갔다. |

| SF-R3 | part_stack get/set(11-17 초안) | 이미 됨 | SS-7 — D-707 2차 SF-R3. REMAINING SF-4 가 part_stack · save_part_stack 이 있다고 적었다(장부는 사람이 쓴다). |

| SF-R4 | uv_mask_from_region(11-17 초안) | 이미 됨 | SS-7 — D-707 2차 SF-R4. REMAINING SF-6 '기능은 돈다'(고리 1 · 2,343.8 mm², rect 12.3×26.5 mm). |

| SF-R5 | 역할 축 display_panel(11-17 초안) | 이미 됨 | SS-7 — D-707 2차 SF-R5. REMAINING SF-10 — 'display_panel 역할은 축에 들어왔다'. |

| SF-R6 | list_artifacts(kind=stl) 요약 기본값(11-17 초안) | 이미 됨 | SS-7 — D-707 1차 SF-R6. REMAINING SF-12 는 확인만 청했다. |

| SG-01 | sf-mcp 이미지에 numpy 넣어 다시 짓기 | 이미 됨 | SignalForge 46c43fa(SG-01) · 5c66b45(기동 스모크) · docs/<박스>-fix-2026-10-27/checklist.md 전부 [x]. |

| SG-02 | VOC 제품 · 플랫폼 ID 를 원천 code 로 다시 매핑 | 이미 됨 | SignalForge 396af7c(SG-02 · SG-15 · SG-17) · 89a0583 · checklist [x] — 1.23M 행 실규모 병합(첫 27분 · 둘째 6분), 표본 5,000/5,000. |

| SG-03 | 코어 거울 과제코드 색인(by_code ← task_code) | 이미 됨 | SignalForge 91e3e84(SG-03 · SG-09 · SG-12). |

| SG-04 | 카탈로그 최신 제품군 · 마케팅명 별칭 — 남은 다시 태깅 범위 | 이미 됨 | SignalForge 9e8dede(10-30 — 본문 '안 A(사용자 결정)' 의 다시 태깅 도구) · 7d9e3b5 · 404fe42(운영 박스 적용 문서 10-31 — 카탈로그 행은 병합으로, 적용은 dev) · aab838c(dev 적용 11-03, 고침 9,603) · f44cf73(retag_delta) … |

| SG-05 | 결함 도구 빈 배열 · 결함률 0.0% 에 pipeline_status | 이미 됨 | SignalForge 89a0583(SG-02 · 04 · 05 · 06) · checklist [x] · DEPLOY_<박스>_2026-10-27.md(7e0aee9). |

| SG-06 | Redis 없는 박스의 worker · beat · 뷰 오류 | 이미 됨 | SignalForge b6d8c7b · checklist [x]. |

| SG-07 | 키워드 폴백 auto 가 여러 낱말 질의를 0건으로 | 이미 됨 | SignalForge 89529b0. |

| SG-08 | site_health 수집 정체 판정 | 이미 됨 | SignalForge cee09d0. |

| SG-09 | 모델코드 칸을 model_code 로 | 이미 됨 | SignalForge 91e3e84. |

| SG-10 | 카테고리 차트 1위가 메타 태그 comparison | 이미 됨 | SignalForge fe2ecca · checklist [x](분류 기준 자체는 정책 결정으로 남김). |

| SG-11 | VOC 결과의 author_name 가림 | 이미 됨 | SignalForge b5e2fa6(SG-11 · SG-18 안 가). |

| SG-12 | renamed_from 을 옛 키로 | 이미 됨 | SignalForge 91e3e84. |

| SG-13 | Redis 없이 한 번 받는 스크립트 · 안내서 | 이미 됨 | SignalForge 4ac0161. |

| SG-14 | PG 재기동마다 seed | 이미 됨 | SignalForge 8f15aed. |

| SG-15 | (질문) ID 어긋남이 생긴 경로 | 이미 됨 | SignalForge docs/DEPLOY_<박스>_2026-10-27.md:175-177 — merge-from-drive.sh 가 dev 덤프의 voc_records 를 ID 그대로 옮긴 것이 원인. |

| SG-16 | (질문) /crawler 바인드가 레포 정의인가 | 이미 됨 | DEPLOY_<박스>_2026-10-27.md:183 — 바인드는 레포 정의(scripts/up.sh 의 sf-mcp 줄). |

| SG-17 | (질문) 덤프로만 받으면 결함 · 태깅이 오는가 | 이미 됨 | DEPLOY_<박스>_2026-10-27.md:187 — 이제 온다(병합이 voc_defects 등도 옮김, 396af7c). |

| SG-18 | (결정) VOC 응답 개인정보 가림 범위 | 이미 됨 | SignalForge b5e2fa6 — 권고안 (가)(기본 가림, 원문은 필요한 화면만) 반영. |

| SG-19 | search_voc · resolve_product_keyword 가 느림 | 이미 됨 | SignalForge 0e2ac46(받은 폴더 · gitlog 대조). |

| SIREN-AGENT-DRAFT-1 | he-data-siren 전문가 페르소나 박스 반영 | 운영 쪽에서 함 | SIREN-AGENT-DRAFT.md 상태 줄 — 11-05 13:38 반영, v2 11-05 17:12, v3 11-06 10:50. 정본은 박스 덧씌우기 파일 infra/personas/he-team.local.json. |

| SIREN-AGENT-DRAFT-2 | (우리 몫) 페르소나 남은 손질 | 운영 쪽에서 함 | SIREN-AGENT-DRAFT §9 남은 것 — 개념의 값 이름을 실제 trust 문자열과 맞추기. 링크 가림 규칙은 mask_keep_hosts(11-07) 뒤로 쓰이지 않는 채 남아 있음(메모리, 박스 server-setup 안내가 빼기를 권함 · 아직 안 함). |

| SRC-01 | StepForge 파트 → 부품 역할 선(has_role) | 이미 됨 | dev 수령: 포털 5f28bf36(11-09 제안서 옮김) · docs/core-link/checklist.md:16 [x] StepForge 세션에 SRC-01~06 넘김. StepForge main 94eaa05b(코드 50b96304) 착지 — docs/cae00-inbox/2026-11-12.md:36. P… |

| SRC-02 | 부품 역할 → 코어 부품(maps_to · 대응표 칸) | 이미 됨 | checklist.md:16 [x] 넘김 · 94eaa05b 착지. cae00-inbox/2026-11-09.md:96 'StepForge SRC-02 — 부품 역할 16 → 코어 part(BOX-12 에서 운영 사용자가 확인)'. PART-ISSUE 문서(11-24): stepforge-core.json:361 m… |

| SRC-03 | 과제 → PLM 과제 연결을 규칙 단으로 | 이미 됨 | docs/cae00-inbox/2026-11-12.md:335-336 — 94eaa05b 가 앱 안 자동 실행(규칙 단 과제 잇기 · set_revision 뒤 앞 판 match · 채우기 잡(proof 만))을 더함, 앱 환경 변수 STEPFORGE_CORE_LINK=off 로 끔. request-1111/cont… |

| SRC-04 | 앞 판이 서면 파트 대응 잡 자동 | 이미 됨 | docs/cae00-inbox/2026-11-12.md:335-336 — set_revision 뒤 앞 판 match 자동 실행 착지(94eaa05b). |

| SRC-05 | 채우기 규칙을 잡 뒤에 자동 | 이미 됨 | docs/cae00-inbox/2026-11-12.md:335-336 — 채우기 잡(proof 만) 자동 실행 착지(94eaa05b). |

| SRC-07 | StepForge 가 서비스 신원으로 규칙 단 적용을 받기 | 이미 됨 | 게이트웨이 5cd9408 — StepForge 가 서비스 단언을 onto-link(규칙 단) · onto-fill 에만 받음. checklist.md:16 [x] 넘김(design §6) · StepForge 50b96304 착지. |

| SRC-08 | DynaForge cae_* → 코어 다리 셋 | 이미 됨 | KooRemapper 5d4b1f94(다리 셋) · 81bfbde1(maps_to 공통 블록) — main 8b49d2a(docs/cae00-inbox/2026-11-15.md:73~). checklist.md:17 [x] KooRemapper 세션에 넘김. PART-ISSUE 문서가 dynaforge-core.js… |

| SRC-09 | 과거 리포트 과제 잇기를 받기 뒤 자동 | 이미 됨 | KooRemapper e7f8d35b — main 8b49d2a(docs/cae00-inbox/2026-11-15.md:73~). |

| SRC-10 | plan_task_links 일반 사용자 읽기 | 이미 됨 | KooRemapper 5ec314eb — main 8b49d2a. docs/cae00-inbox/2026-11-15.md:86 — 로그인 사용자 누구나 미리 보기. |

| SRC-11 | 받을 타입 밖 멈춘 타입 표시 | 이미 됨 | KooRemapper ae27a328 — main 8b49d2a(docs/cae00-inbox/2026-11-15.md:73~). |

| SRC-12 | update-all 끝 박스 훅 자리(post-update.d) | 이미 됨 | 포털 68826403 · a5ff0f2b → main 99f42a24(docs/core-link/checklist.md:28-29 · 34 · 54 [x]). |

| SRC-13 | 게이트웨이 서비스 신원 경로(서비스 PAT) | 이미 됨 | 포털 494b88cf · 9e58191f · 69cba3e6 → 4de59fb4, 게이트웨이 57732f4 · f333a46 · 7c14a63 · 08d14a0 → master 96d0134(checklist.md:30-31 · 35 · 42 · 54 [x]). |

| SRC-14 | 질문 — tools-map 쓰기 목록 link_ 짝 | 이미 됨 | 게이트웨이 3445a4b — 낱말 셋 + 읽기 목록 둘 + 시험(checklist.md:41 [x]) → 96d0134. |

| SRC-15 | 질문 — REST 다리로 StepForge 포털 신원 길 쓰기 열기 | 이미 됨 | 게이트웨이 f7babcc(rest_sso.step_forge) · 80df26f(write_paths 다섯) · 5cd9408, 에이전트 서버 4624d12 · d24ed86 → 32bf3ae, 포털 27d751ed · f2930226(checklist.md:20 · 32-33 · 43 · 48-49 [x]). |

| ST-01 | 과제코드로 허브 과제 찾기(find_plm_task · get_project_meta) | 이미 됨 | HWAXAgentServer tests/fixtures/subject/find_plm_task.json(StepForge 4253453 의 core/sp_core.py find_tasks 실제 응답)에서 과제코드로 찾은 행이 matched_by ['task_code'] 와 key=과제명으로 온다(tests/test_… |

| ST-02 | find_plm_task 응답이 자기 챗 컷을 넘음 | 이미 됨 | 포털 request-1029/context-notes.md:196-199 C-28 — D-637(10-27)은 챗 접기만, 10-29 에 본문 sync 를 요약으로 바꿈(StepForge main). 그 판(ff308d1) SIF dist-20261030-034158Z 가 Drive 에 올라감(request-1030… |

| ST-3 | (STE) 레지스트리 잡 환경에 StepForge 주소 · 잡 한정 토큰 | 운영 쪽에서 함 | checklist.md — '[x] ST-3 — ste 세션에서 사용자 결정(11-22 밤): 주소만 먼저(STEPFORGE_BASE) · 잡 한정 토큰은 발급처가 생긴 뒤', '[ ] ST-3 주소 넣기 — ste 헤드 .env 의 STE_STEPFORGE_BASE(사람 — 받은 편지함 물음 15, 11-23 아직… |

| ST-03 | (유지 요청) prod 이전은 설정으로 — 루프백 바인드 · ROOT_PATH · 직렬화 | 대체됨 | StepForge 답신 기록을 이 배치에서 찾지 못했다(StepForge 소스 없음, 포털 docs 에 ST-03 줄 0). / 정리 11-25: 11-12 운영 전환은 운영 유닛 설정 덮어쓰기로 이뤄졌고, 불변 조건(루프백 바인드 · ROOT_PATH · 직렬화)은 운영 유닛이 지킨다. '동기화 끄기' 낡은 문구 … |

| ST-04 | 받을 타입 고르기 · 한 타입 실패에도 계속 | 이미 됨 | 포털 docs/core-link/server-setup.md:78(11-09 대조) — StepForge 코드에 배포 설정 STEPFORGE_SP_TYPES 가 있고, 비어 있으면 카탈로그의 열린 타입을 모두 받는다. |

| ST-05 | 정해진 받기 주기(앱 안 설정 또는 문서) | 이미 됨 | request-1030/platforms/05-StepForge.md:39 — StepForge ff308d1 scripts/plm_sync.py:16 머리가 바깥 cron · systemd 타이머로 '매일 증분 · 주 1회 --full' 을 권한다(문서만으로도 된다는 요청 충족). |

| ST-06 | plm_hub.configured 판정을 두 칸으로 | 대체됨 | HEAXHub docs/2026-10-31-prod-cutover/request.md:403 — 10-27 에 두 박스 모두 코어 주소 · 토큰 · 프록시 예외 · 재기동을 끝낸 뒤 plm_hub.configured=true · last_sync ok 였다. 수락 기준(configured=true 와 last_syn… |

| ST-07 | MaterialTwin 기본 주소를 허브가 띄운 자리로 | 이미 됨 | 포털 docs/followups-1017/requests.md:72 「풀림 StepForge f82e11e(D-637 · ST-07 · ST-11 — 주소 차례 · 닿지 않음을 null 과 가름)」 · HEAXHub fed086f(HH-09 HEAX_APP_URL_<SLUG>). |

| ST-08 | part_history 필수 조건을 스키마로 | 이미 됨 | 포털 docs/followups-1017/requests.md:6 「풀림 StepForge f82e11e(10-27 D-637 · ST-08 — 인자 없이 부르면 거절 대신 needs_input 안내)」. |

| ST-09 | (질문) set_project_meta(code=…) 에 적을 값 | 대체됨 | 포털 docs/core-link/request.md:66 SRC-03(11-09 제안서 — 개발 세션이 받아 PLAN · checklist 를 두었다)이 'set_project_meta 의 code 나 이름이 코어 plm_task 하나에 정확히 맞으면 잇는다' 는 규칙 단으로 이 질문을 대체했다. 포털 docs/pr… |

| ST-10 [05] | (질문) 공유 NFS 충돌 표식 누락 대비 | 운영 쪽에서 함 | 요청서가 '우리 측정 뒤 다시 알린다' 로 적었고 먼저 할 일은 우리 몫 OB-49(H5 — /data3 soft→hard 측정). 측정 결과 전달 기록 없음. |

| ST-11 [05] | (질문) MaterialTwin 주소를 어느 쪽이 맡을지 | 이미 됨 | 포털 docs/followups-1017/requests.md:72 StepForge f82e11e(D-637 · ST-07 · ST-11) · HEAXHub fed086f(HH-09). |

| ST-12 [10-30] | 판 전체 drop_check 진행률이 10% 에 멈춤 | 이미 됨 | StepForge b2c70f1(D-650) 반영 — 받은 폴더 · gitlog 대조. |

| ST-13 [11-11] | StepForge disclosure.tools 184 · mcp_tools 192 | 이미 됨 | 답 R11-7 · StepForge 4c56486(request-1111). |

| ST-14 [11-11] | 새 판이 옮긴 DB 로 옛 판이 뜨는지(질문) | 이미 됨 | OPS-ROLLBACK.md 94eaa05b 로 답(request-1111). |

| ST-15 [11-13] | bbox_of 가 OCC 예외에서 물러설 길(AddOptimal_s → 면 단위 → None + 까닭) | 이미 됨 | HWAXPortal docs/request-1111/checklist.md:31 — 'StepForge 일곱째 묶음 … ST-15 ~ ST-19(사용자가 그 세션에 붙여 넣음)', gitlog HWAXPortal a99f2f73(11-12). HWAXPortal docs/cae00-inbox/2026-11-15.md… |

| ST-16 [11-13] | 파트 하나 실패로 호출 전체를 죽이지 않기(skipped_parts) | 이미 됨 | HWAXPortal docs/cae00-inbox/2026-11-15.md:70 — '이 판(27b2132b)을 받은 뒤 조각 면 판이 있던 과제 둘에 단면 · 근접 · part_index · render_3d · section_area 를 다시 돌리면 그 판 하나가 skipped_parts 로 빠지는 것이 정상'.… |

| ST-17 [11-13] | obb_of(AddOBB_s)에도 같은 보호 | 이미 됨 | request-1111/checklist.md:31 — 일곱째 묶음 = ST-15 ~ ST-19. cae00-inbox/2026-11-15.md:47-48 — 그 묶음이 StepForge 27b2132b 에 들어 있다. 항목별 반영은 확인하지 못했다(StepForge 소스가 박스에 없음). |

| ST-18 | 자동 단면 지도 실패를 과제 상태에 보이게 | 이미 됨 | request-1111/checklist.md:31(일곱째 묶음 ST-15 ~ ST-19) · cae00-inbox/2026-11-15.md:47-48(27b2132b 에 그 묶음). what_next · geometry_health 에 실린 것은 확인하지 못했다(소스 없음). 같은 판의 C30 이 geometry_… |

| ST-R1 | (STE) 잡에 StepForge 주소 · 토큰 주입(11-17 초안) | 대체됨 | 11-18 전달. context-notes.md SS-2 — 잡 안에 StepForge 자격을 넣지 않기로 보류했다(같은 계정 잡끼리 읽힘). 11-22 사용자 결정(주소 먼저)으로 REMAINING ST-3 으로 넘어갔다. |

| ST-R2 | (STE) 단계 실패 = 잡 실패(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-4 로 넘어갔다. |

| ST-R3 | (STE) ste_job_summary(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-5 로 넘어갔다. |

| ST-R4 | (STE) 레디쉬 판정 기준 · 판정(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-6 으로 넘어갔다. |

| ST-R5 | (STE) reddish_case_build(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-7 로 넘어갔다. |

| ST-R6 | (STE) 변별 경계 h 기본표(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-8 로 넘어갔다. |

| ST-R7 | (STE) request.json 스키마 노출(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-12 로 넘어갔다. |

| ST-R8 | (STE) 결과 숫자 칸 · 단위(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-13 으로 넘어갔다. |

| ST-R9 | (STE) 잡 목록 소유자(11-17 초안) | 대체됨 | 11-18 전달. SS-3 — owner 는 빼고 mine 만(PA-20). REMAINING ST-14 로 넘어갔다. |

| ST-R10 | (STE) 레디쉬 환경 절(11-17 초안) | 대체됨 | 11-18 전달. REMAINING ST-15(STE)로 넘어갔다. |

| T-01 | GPU 클러스터 챗 LLM 잡 재기동(11-14 전) | 운영 쪽에서 함 | 기한 11-14 지남 · 끝냈다는 기록을 이번에 못 찾음. |

| T-02 | 챗 LLM 다른 사용 서비스 담당에게 재기동 사전 알림 | 운영 쪽에서 함 | 기한 11-10 무렵 지남 · 기록 못 찾음. |

| T-10 | 백업 · 덤프 · plm-sync 다음 날 확인 | 운영 쪽에서 함 | TODO 행 그대로 · 뒤 기록 없음. |

| T-11 | ~/aidh-inbox 옛 사본 · 변환 임시 폴더 치우기 | 운영 쪽에서 함 | TODO 행 그대로 · 사용자 확인 필요. |

| T-12 | KooRemapper 사람별 위임을 표준 스크립트로 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-13 | provision.env HEAX_MCP_TOKEN 고정 걷기 검토 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-14 | NO_PROXY 임시 조치 걷기 검토 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-15 | crontab XDG · DBUS 두 줄 유지 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-16 | update-collab.sh 로그 덧붙임 우회 걷기 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-17 | StepForge 코어 받기 cron 주 1회 --full | 운영 쪽에서 함 | TODO 행 · OB-101 도 '남았다'. |

| T-18 | HEAXHub 데모 등록 내리기 | 운영 쪽에서 함 | 11-11 update-all 도 heax_demo_nextjs 미서빙(REQUEST-20261111 1부). |

| T-19 | 허브 셋 · SimEngBay 위임 비밀 대조 403 문의 | 운영 쪽에서 함 | TODO 행 그대로. |

| T-20 | DELIB_JOB_MAX_RUNNING 고정 걷기 결정 | 운영 쪽에서 함 | TODO 행 그대로. |

| W-01 | StepForge 다음 판 · 과제코드 실데이터 확인 | 운영 쪽에서 함 | OB-59 와 같음 · 확인 기록 못 찾음. |

| W-02 | SmartTwin 새 판 · MCP 등록 · 첫 실제 제출 | 운영 쪽에서 함 | 등록 몫은 11-24 끝남. 첫 실제 제출(OB-74) 기록은 못 찾음. |

| W-03 | SimFlow 답 대기(확장자 · 상한) | 운영 쪽에서 함 | PA-12 답 기록 없음. |

| W-04 | RA 가져오기 상한 답 대기 | 운영 쪽에서 함 | 답 기록 못 찾음. |

| W-05 | 박스 밖 플랫폼 답 반영 확인 | 운영 쪽에서 함 | TODO 행 그대로. |

| W-06 | AIDataHub 본문 검색 속도 실측 대기 | 이미 됨 | AD-04(다시) 실측이 옴(끔 8 ms · 켬 6.4초 · 찬 기동 45초 넘음). |

| W-07 | TestScope 위임 설정 완료 알림 대기 | 운영 쪽에서 함 | TestScope SSO 전환 대기 그대로(우리 운영 기록 11-13). |