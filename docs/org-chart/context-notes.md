# 조직도 재편 · HE팀 · 심층 보기 — 결정 기록

## D-1. HE팀은 '플랫폼 에이전트' 안이다
"별도 폴더에 플랫폼 에이전트를 만들어뒀으면 해. mcp를 통해 도구 조회를 해서 하는게 기본이긴 하지만,
여기에 HE팀 폴더를 만들어서…" — '여기에'를 플랫폼 에이전트 안으로 읽었다. 기존 앱 지식 분석가 6명
(material-twin-analyst 등)도 같은 루트의 다른 분류로 둔다. 둘은 다르다 — 분석가는 지식카드로 답하고,
HE 페르소나는 앱 도구를 몰아 답한다.

## D-2. HW·SW 에 안 맞는 도메인은 '공통·업무 지식'
xd(업무·프로세스 교차 122명 — CAE 방법론 등)·std·misc·oss·market 은 스마트폰 HW/SW 어느 쪽도 아니다.
전문 지식 에이전트 아래 세 번째 분류로 둔다. 모르는 도메인 코드는 '미분류'로 보여 준다 — 표에 한 줄이
빠졌다고 사람이 조직도에서 사라지면 안 된다(도구 영역 D-14 와 같은 이유).

## D-3. HE팀 키는 he-<묶음>-<앱>, 묶음은 게이트웨이 도구 영역을 따른다
17명을 한 목록에 두면 이름순 나열이다. 둘째 세그먼트를 묶음으로 두면 조직도가 그대로 접는다
(그룹은 2명 이상일 때만 선다). 묶음은 도구 영역 분류(D-14 계열)와 같은 결로 — 설계 데이터·
시뮬레이션·해석 계산·물성·데이터 허브·VOC·보고서·문서·발표·조사·심의·리스크. 라벨 정본은
he-team.json groups 이고 personaCatalog.ts HE_GROUP_LABEL 과 test_he_personas 가 대조한다.
MaterialTwin 은 '해석 계산·물성', SignalForge 는 '데이터 허브·VOC' 로 — 한 명짜리 묶음을 안 만들려고.

## D-4. 정본은 포털 리포 JSON, AIDataHub 는 사본 — 동기화 스크립트가 도구 이름을 대조한다
AIDataHub 에 손으로 넣으면 박스마다(dev·cae00) 다시 넣어야 하고, 앱 도구 이름이 바뀌어도 모른다.
정본(infra/personas/he-team.json)을 git 에 두고 sync-he-personas.py 가 게이트웨이 /tools-map 과
대조해 없는 도구 이름이면 멈춘다(모델이 없는 도구를 부르는 것보다 동기화가 멈추는 게 낫다).
바뀐 칸만 PATCH 한다 — 안 바뀐 것까지 쓰면 에이전트 이력이 매번 쌓인다. system_prompt 앞에
`<!-- no-tool-guide -->` — 없으면 AIDataHub 가 'agent_search 로 검색하라' 안내를 덧붙여 운영자의
행동과 정면으로 부딪친다. 상한 4000자는 에이전트서버 PERSONA_ROLE_MAX 와 같다(테스트가 대조).
도구 지도(영역별 도구 이름)는 사전 지식이 얇은 cae00 전용 앱(ARP·ODB)에만 싣는다 — 나머지는
'할 수 있는 일'이 이미 도구를 영역별로 부르고, 이름 목록은 프롬프트만 불린다.

## D-5. 운영자를 고르면 그 앱을 핀하고, 입구 도구는 캡에서 먼저 산다
에이전트서버가 response_config.mcp_apps 를 도구 선별 **전에** 읽어 앱 도구를 핀한다(사용자 앱
지정과 같은 경로). 앱 통째 핀은 dev 캡 40 을 넘어서(StepForge 81·RA 70) 핀끼리 관련도로만 갈리면
입구 도구(get_guide·list_projects…)가 밀려났다 — key_tools 를 first 로 먼저 산다. 상시 예약은
안내대 4개(search_tools·invoke_tool·list_tool_apps·recommend_agents)로 줄인다: 핵심 38개를 예산 밖에서
덧붙이자 dev 16K 에서 16,385토큰으로 400 이 났고(실측), GLM 에서도 무관한 도구가 절반이 된다.
바인딩 밖 도구는 invoke_tool 로 부른다(페르소나 '답하는 법'에 적었다). 지식카드 선조회는 하지
않는다 — 0건이면 "사내 지식카드에 없다"를 먼저 밝히게 되어 있어, 도구로 답할 질문에 엉뚱한
단서가 붙는다.

## D-6. 운영자는 자동 발굴에 안 나온다, 조직도 수동 선택은 된다
도구 운영자는 도메인 전문가가 아니다. 좌석 발굴(_discover — 주 좌석·반대 도메인·재심사)·띵킹
소집·좌석 추천 화면의 추천/후보에서 뺀다. 풀(list_agents)에는 남긴다 — 사람이 앉히겠다면 막을
이유가 없다. 판정은 키 도메인(he)으로 한다(recommend_agents 응답에 response_config 가 없다).

## D-7. ARP·ODB 는 cae00 에서 같은 스크립트로 생긴다
게이트웨이 백엔드 키는 arp·odb-hub(provision-config.sh). dev 게이트웨이엔 없어 건너뛴다. cae00 에서
`python3 infra/scripts/sync-he-personas.py` 로 미리보기 → `--apply`. 사전 지식은 매니페스트 설명으로
만든 뼈대 + 도구 지도라 얇다 — 실제 도구를 보고 he-team.json 의 workflow·pitfalls·key_tools 를
보강한다(todo 칸). 다른 박스에서 이 둘을 고르면 에이전트서버가 operator_app_missing 경고를 낸다.
