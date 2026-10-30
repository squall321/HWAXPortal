# 10-30 수정 요청 — cae00 에서 사람이 할 일

요청서 정본 [`../request_261030.md`](../request_261030.md) · 플랫폼별 시트 [`platforms/`](platforms/00-INDEX.md) · 받은 답 [`outbound.md`](outbound.md).
이 문서는 판이 올라갈 때마다 고친다. **0절 표에 '올림' 이라 적힌 판만 update-all 로 받는다.** 아직 오지 않은 판은 '예정' 이다.

> 명령의 경로는 cae00 기준(`~/Projects/<리포>`)이다. 비밀 값은 화면 · 로그 · 채팅에 붙이지 않는다. 에이전트 서버 주소 `127.0.0.1:9009` 는 루프백이라 `--noproxy '*'` 를 붙인다.

## 0. 받는 판

| 리포 | 판 | 무엇 | 상태 |
|---|---|---|---|
| 에이전트 서버 | `e94bc09` · `3cb8cbe` | HA-34(접기 흔적) · HA-26 재시도 몫 · HA-31(전문가 검색 가로채기) · HA-32(타입 이름 대응) · HA-33(VOC 미리보기) · HA-08(위키 꺼짐 문구), 높음 넷의 골격(동작 그대로) | 올림 |
| 에이전트 서버 | 예정 | HA-27(자기검증 관문) · HA-28(상태 기다리기) · HA-29(확인 카드) · HA-30(다른 허브 id) | 짓는 중 |
| 게이트웨이 | `c70ec21` | HG-21(소수부를 IMEI 로 가리던 것 — dev 출력에서 2,780곳) · HG-22(사람 칸 이름 · 메일 · 성씨 계정 · 사설 IP · `rest_call`) | 올림 — 가림 범위는 판단 C-11 |
| 포털 | `6a76f58` | HP-51(운영자 앱 없음 표지) · HP-52(씨앗 `from: items`) · HP-53(writes · confirm · ARP 함정 줄 · 저장 뒤 500 견딤) · HP-55(update-all 문구) · HP-56 · HA-32(어휘표 types · '전작' · '후속 모델') | 올림 — 화면은 Drive 이미지(5절 앞) |
| AIDataHub | `df7d45b` | AD-19 · AD-20(추천 · 기록 목록) · AD-21(저장 뒤 500) · AD-03(DRM 머리) · AD-07(`as_of`) · AD-01 코드(하위 절 평탄화 · 다시 짓기 명령) | 올림 — 데이터 단계는 5절 |
| MX 백서 | `bb0a6a1` · `bd2e79b` | MW-12 · MW-01 | 올림(그쪽 세션) |
| SignalForge | `0e2ac46` · `ec40075` · `f004cd0` | SG-19 · SG-04 주의 칸 | 올림(그쪽 세션) |
| SmartTwinExplorer | `4f5e0e0` | PA-20 | 올림 — Drive staging 번들(3절) |
| DocForge | `e72cbe5` · `ab5547e`(0.3.1) | HH-14 | 코드 끝 — 배치는 그 세션의 사용자 승인 대기 |
| KooRemapper | `0c1113f` · `f36270f` · `a3eff43` | KR-23 — 레시피 자동 관문을 MCP 설명에 적음(사용자 결정 그대로) · KR-01 · KR-16 — 과제 검색이 별칭을 대조하고 순위를 매긴 뒤 자른다(행마다 match_kind) | 올림(그쪽 세션) — update-all 하나, 재기동 때 이관 0018 · 화면은 다음 Drive |
| StepForge | 다음 판 | ST-12 | 그쪽 세션 |

## 1. update-all 한 번

평소처럼 돌린다. 도는 심의가 있으면 에이전트 서버 재기동이 미뤄진다(○ 줄) — 끝난 뒤 `cd ~/Projects/HWAXAgentServer && ./start.sh -d`.

- MX 백서는 `migrate.sh` 가 이관 0059 · 0060 을 돈다(위키 표 · 알림 종류만 더한다 — 위키가 꺼진 박스에서는 쓰이지 않는다).
- AIDataHub 는 코드만 바뀐다(이관 · 데이터 작업 없음). API 가 새 판으로 뜨면 1 · 4절 확인으로 본다.

## 2. OB-91 우회 걷기(HA-26)

1. 에이전트 서버가 이번 판인지 본다 — `curl -s --noproxy '*' 127.0.0.1:9009/health` 에 `hub_fold` 칸이 있으면 이번 판(HA-34)이다.
2. 에이전트 서버 `.env` 에서 `CHAT_STABLE_PREFIX=0` 줄을 지운다(10-30 백업은 `~/portal-backups/agent.env.stableprefix-*`).
3. 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d`.
4. 전문가를 고른 챗 · 앱을 핀한 챗 · 문서를 붙인 챗을 하나씩 보낸다. LLM 400 이 없어야 한다. 접두 캐시 적중을 다시 잰다(요청서 7절).
5. 그래도 400 이 오면 이번 판은 자동 재시도에서 안내를 첫 시스템 메시지에 합쳐 다시 보낸다. 에이전트 로그에 `'System message must be at the beginning' 400 — 남은 재시도는 이 턴의 안내를 첫 시스템 메시지에 합쳐 보낸다(HA-26)` 줄이 남는다. 그 줄이 보이면 알려 달라(채팅 틀이 사람 발화 머리의 안내도 거절한다는 뜻이다).

## 3. 다른 플랫폼 반영(그쪽 세션이 알려 온 것)

- **SignalForge** — update-all 로 받은 뒤 sf-mcp · sf-backend 를 워치독 락을 쥐고 하나씩 재기동한다. 명령은 SignalForge `docs/DEPLOY_CAE00_2026-10-30.md` 1절 그대로이고, 'sf-mcp semantic import ok' 를 확인한다. 2절대로 시간과 `plm_caution` 을 본다(실제 이름은 `~/ontology-test/`).
- **SmartTwinExplorer(ste — 24대)** — Drive `ApptainerImages:SmartTwinExplorer/staging` 번들(`4f5e0e0`)을 `STE_DEPLOY=1 infra/scripts/deploy-ste.sh` 로 반영한다(MCP `ste-mcp.service` 도 함께 다시 뜬다). DW-12 다시 보기는 게이트웨이 HG-22 가 든 뒤에 한다.
- **DocForge** — 0.3.1 배치(그 세션의 사용자 승인) 뒤에 한다. 브라우저 `/apps/doc_forge/api/v1/capabilities` 의 version 이 0.3.1 인지, 게이트웨이 `/refresh` 뒤 tools-map 에 `docforge_*` 가 여섯인지 본다. OB-94 시험 파일은 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/` 에 평문 pptx 하나를 둔다(상자의 파일은 DocForge 가 지우지 않는다 — 운영자가 치운다).
- **MX 백서** — 위키가 꺼진 박스라 `mxwp-mcp` `tools/list` 의 `wiki_*` 가 0개여야 한다. MCP 가 API 보다 먼저 떴다면 로그에 '위키 도구를 미루고 다시 본다' 한 줄이 있고 '미뤄 둔 위키 도구 N개를 실었다' 줄은 없어야 맞다.

## 4. 이번 판 확인(올린 것)

| 행 | 볼 것 |
|---|---|
| HA-34 | `/health` 의 `hub_fold`(`count · chars_in · chars_out`)가 큰 허브 응답 뒤 오른다. 에이전트 로그에 `[agent] 허브 응답 접음 — <도구>: 원문 N자 → M자` |
| HA-31 | DW-13 — 'PCB 내부 크랙을 잘 아는 전문가 에이전트를 추천하고, 추천 근거가 된 기록 수를 알려줘.' 를 전문가를 고르지 않은 대화와 AI 데이터 허브 운영자를 고른 대화에서 한 번씩. 두 번 다 LLM 을 거친 답이고 '기록 수' 에 답해야 한다 |
| HA-32 | DW-22 — 없는 타입 이름(`management_standard`)을 지어내지 않는다. update-all §7 '코어 어휘표 지문' 이 게이트웨이와 에이전트에서 같다 |
| HA-33 | 심의 패널 'VOC 먼저 보기' 에 건수가 나오고, 0건이면 까닭 줄('<검색어>' 0건 — …)이 보인다 |
| HA-08 | 지금은 잠복(위키 도구 0개) — 볼 것 없음 |
| AD-19 · AD-20 | DW-13 의 추천 10명에 무관한 사람(로그 플랫폼 · MCP 레지스트리 · 카메라 MIPI)이 오르지 않는다. 의미검색 항이 여전히 올리는지는 이때 갈린다 |
| AD-21 | 운영자 동기화(`python3 infra/scripts/sync-he-personas.py` 미리보기 뒤 `--apply`)가 첫 건에서 멈추지 않는다. 원래 거절 까닭은 AIDataHub 로그에서 읽기만 한다 — `grep -n 'sample embedding sync failed twice\|validation errors for AgentOut' deploy/apptainer/logs/uvicorn.log* \| tail -20` |
| AD-03 | M-6 — [`platforms/90-OURS.md`](platforms/90-OURS.md) 의 'AIDataHub 쪽 M-6 의 바른 길'(NASCA **.xlsx** 로 본다) |
| AD-07 | 게이트웨이 `tools/list` 의 `agent_search` 입력에 `as_of` · `as_of_undated` 가 있다(소스가 아니라 목록으로 본다) |

### 포털 · 게이트웨이(올린 것)

| 행 | 할 일 · 볼 것 |
|---|---|
| HP-52 | 두 씨앗을 이미 가져간 사람은 절차 목록 '함께 오는 정본 예제' 에서 **'전각도 낙하 — 부품 보고서 (회수·판독) 최신으로'** · **'전위치 부분충격 — 부품 보고서 (회수·판독) 최신으로'** 를 눌러 판본을 올린다. 올리지 않으면 첫 단계가 '봉투다 … from: items 로 고친다' 안내와 함께 멈춘다. 올린 뒤 리포트 0건은 `select:none`(아직 DynaForge 에 반입되지 않음)이다 |
| HP-53 · HP-51 | update-all 은 미리보기만 한다. `python3 infra/scripts/sync-he-personas.py` 로 미리보기 → ✗ 줄이 없는지(특히 he-data-arp 의 key_tools 와 he-cad-odbhub 의 이름 여섯) → '· 목록 밖 쓰기' · '! 운영자 앱이 이 게이트웨이에 없다' 줄을 읽고 → `python3 infra/scripts/sync-he-personas.py --apply`. AIDataHub 가 저장 뒤 500 을 내도 '⚠ … 다시 읽으니 저장됐다' 를 찍고 이어 간다 |
| HP-55 | 할 일 없음. update-all §1 은 박스 값이 0 이면 'TOOL_MAX=0 그대로(무캡)' 로, §7 '챗 도구 절단' 줄은 예산의 출처를 적는다. OB-93 때 '— CHAT_TOOL_SCHEMA_BUDGET' 이면 손잡이가 먹은 것이다 |
| HP-56 · HA-32 | update-all §7 '코어 어휘표 지문' 이 게이트웨이와 에이전트에서 같고, 에이전트 `/health` 의 `core_vocab.rule_words` 가 17 이다. 다른 타입(예 부품)의 slug 를 허브에서 확인하면 받은 뒤 `backend/config/core_vocab.local.json` 에 `{"types": {"부품": "<slug>"}}` 로 더한다 |
| HG-21 · HG-22 | 요청서 7절의 DW-07 · DW-03 · 06 · 12 · 22 를 다시 본다 — 숫자가 그대로 나오고 사람 이름 · 메일 · 사설 IP 가 가려진다. `/health` 의 `pii_mask.masked` 가 는다 |
| HG-22 링크(C-11) | RA 의 업로드 주소가 깨지지 않는지 본다. `infra/.env` 의 `RA_HOST` 가 사설 IP 꼴이면 RA 쪽 `MCP_PUBLIC_BASE` 를 호스트 이름으로 둔다(RA 리포는 고치지 않고 그 박스 설정만) |
| OB-98(C-11) | whoami 의 본인 메일은 이제 '[가림:메일]' 이다 — 표시 이름이 보이면 맞다 |
| R-08(C-11) | `/api/<site>/…` 바이트 프록시는 가리지 않는다. cae00 의 TODO-20261029 R-08 원문이 이 길을 뜻하는지 확인한다 |

## 5. 사용자 OK 를 기다리는 데이터 단계(AIDataHub)

아래는 명령만 지어 두었고 어느 박스에서도 돌리지 않았다. 사용자 OK 뒤에 한다.

- **AD-01 다시 짓기** — 154장은 평탄화 고침과 다시 짓기로는 고쳐지지 않는다. MX 백서 동기화 자리표시(본문 한 절 · 글 없음)라 원천을 다시 받아야 한다. 그런데 dev 의 MX 백서 정기 동기화는 10-18 21:26 UTC 뒤 1,122번이 모두 401 이다(AIDataHub 의 `MXWP_INTERNAL_KEY` 가 없다). cae00 은 URL 가드가 막는다. 키 · 가드를 먼저 정하고, 다시 받은 뒤 `deploy/apptainer/reindex-sections.sh`(기본은 셈만 · `--apply` 앞에 백업)를 돈다.
- **AD-05 · AD-06** — dev 원본의 빈 전문가 둘과 데모 카드 셋 지우기(그 뒤 cae00 은 OB-87).
- **AD-04** — dev DB 사본에서 본문 검색 속도 재기(`EXPLAIN ANALYZE`).
- **AD-21 의 cae00 원인 후보** — `merge-from-drive.sh` 가 `agent_sample_embeddings` 를 dev 의 대리 키(id)로 덮어쓰고 순번을 올리지 않는다. 그래서 cae00 의 다음 표본 행이 겹친 id 로 거절될 수 있다(검토 에이전트가 버리는 PG 에서 재현). 스크립트 고침은 cae00 데이터 흐름을 바꾸므로 결정 뒤에 한다.

## 6. 다음 판에서 더할 것

게이트웨이(HG-21 · HG-22) · 포털(HP-51 · 52 · 53 · 55 · 56) · 에이전트 높음 넷이 올라가면 이 문서에 손잡이(새 환경 값과 기본값) · 확인 · 다시 볼 시험(요청서 7절)을 더한다.
