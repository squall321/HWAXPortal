# 10-30 수정 요청 — cae00 에서 사람이 할 일

요청서 정본 [`../request_261030.md`](../request_261030.md) · 플랫폼별 시트 [`platforms/`](platforms/00-INDEX.md) · 받은 답 [`outbound.md`](outbound.md).
이 문서는 판이 올라갈 때마다 고친다. **0절 표에 '올림' 이라 적힌 판만 update-all 로 받는다.** 아직 오지 않은 판은 '예정' 이다.
10-31 에 6절부터를 더했다 — 챗 관문 넷(HA-27 ~ HA-30)의 확인 · 손잡이 · 다시 볼 시험, OB-26 · OB-04, AIDataHub 병합 한 번과 데이터 단계 차례, 아직 오지 않은 것.
바깥 답이 필요한 물음은 이 문서가 아니라 받은 편지함 [`../cae00-inbox/`](../cae00-inbox/README.md) 에 든다(판단 C-20).

> 명령의 경로는 cae00 기준(`~/Projects/<리포>`)이다. 비밀 값은 화면 · 로그 · 채팅에 붙이지 않는다. 에이전트 서버 주소 `127.0.0.1:9009` 는 루프백이라 `--noproxy '*'` 를 붙인다.

## 0. 받는 판

| 리포 | 판 | 무엇 | 상태 |
|---|---|---|---|
| 에이전트 서버 | `e94bc09` · `3cb8cbe` | HA-34(접기 흔적) · HA-26 재시도 몫 · HA-31(전문가 검색 가로채기) · HA-32(타입 이름 대응) · HA-33(VOC 미리보기) · HA-08(위키 꺼짐 문구), 높음 넷의 골격(동작 그대로) | 올림 |
| 에이전트 서버 | `d6c3a84` | HA-27(자기검증 관문) · HA-28(상태 기다리기) · HA-29(확인 카드) · HA-30(다른 허브 id) — 맞물림 시험 I-1 ~ I-8 · 반대 검토 두 차례 | 올림 — 확인 · 손잡이 · 다시 볼 시험은 6절 |
| 게이트웨이 | `c70ec21` · `602bbb2` | HG-21(소수부를 IMEI 로 가리던 것 — dev 출력에서 2,780곳) · HG-22(사람 칸 이름 · 메일 · 성씨 계정 · 사설 IP · `rest_call`), `602bbb2` 는 시험만(어휘표 OB-04 뒤 — 시험 사본 숨김 시험이 실제 표의 셋에 기대지 않게) | 올림 — 가림 범위는 판단 C-11 |
| 포털 | `6a76f58` · `dbbb943` | HP-51(운영자 앱 없음 표지) · HP-52(씨앗 `from: items`) · HP-53(writes · confirm · ARP 함정 줄 · 저장 뒤 500 견딤) · HP-55(update-all 문구) · HP-56 · HA-32(어휘표 types · '전작' · '후속 모델'), 그 뒤 확인 카드 단추 · 짚기만 한 자기검증(화면) · 운영자 목록 C-15 · update-all §7 관문 줄 · env 킷 손잡이 · OB-26(ODB 허브 운영자) · OB-04(어휘표) | 올림 — 화면은 Drive `images-20261030-220551Z`(drive-drift 포털 일치) |
| AIDataHub | `df7d45b` · `6f496fa` | AD-19 · AD-20(추천 · 기록 목록) · AD-21(저장 뒤 500) · AD-03(DRM 머리) · AD-07(`as_of`) · AD-01 코드(하위 절 평탄화 · 다시 짓기 명령), `6f496fa` 는 병합이 표본 임베딩을 전문가 단위로 맞추고 순번을 올린다(AD-21 후속) | 올림 — 받은 뒤 병합 한 번(8절) · 데이터 단계는 5 · 8절 |
| MX 백서 | `bb0a6a1` · `bd2e79b` | MW-12 · MW-01 | 올림(그쪽 세션) |
| SignalForge | `0e2ac46` · `ec40075` · `f004cd0` | SG-19 · SG-04 주의 칸 | 올림(그쪽 세션) — 차례는 3절 |
| SignalForge | `404fe42` | 그쪽 cae00 문서 2026-10-31(그 리포 `docs/DEPLOY_CAE00_2026-10-31.md`) | 올림(그쪽 세션) — 차례는 3절 |
| SmartTwinExplorer | `4f5e0e0` | PA-20 | 올림 — Drive staging 번들(3절) |
| DocForge | `e72cbe5` · `ab5547e`(0.3.1) | HH-14 | 코드 끝 — 배치는 그 세션의 사용자 승인 대기 |
| KooRemapper | `0c1113f` · `f36270f` · `a3eff43` | KR-23 — 레시피 자동 관문을 MCP 설명에 적음(사용자 결정 그대로) · KR-01 · KR-16 — 과제 검색이 별칭을 대조하고 순위를 매긴 뒤 자른다(행마다 match_kind) | 올림(그쪽 세션) — update-all 하나, 재기동 때 이관 0018 · 화면은 다음 Drive |
| StepForge | `b2c70f1` · Drive `dist-20261030-135126Z` | ST-12 — 합치기 진행률(경과 시간) · `work_outlook` · owner 가림(+ 온톨로지 그래프 도구 일곱) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 교체, 교체 전 도는 잡이 없는지 본다 |

## 1. update-all 한 번

평소처럼 돌린다. 도는 심의가 있으면 에이전트 서버 재기동이 미뤄진다(○ 줄) — 끝난 뒤 `cd ~/Projects/HWAXAgentServer && ./start.sh -d`.

- MX 백서는 `migrate.sh` 가 이관 0059 · 0060 을 돈다(위키 표 · 알림 종류만 더한다 — 위키가 꺼진 박스에서는 쓰이지 않는다).
- AIDataHub 는 코드만 바뀐다(이관 · 데이터 작업 없음). API 가 새 판으로 뜨면 1 · 4절 확인으로 본다. `6f496fa` 는 병합 스크립트 고침이라
  Drive 덤프가 그대로면 이번 update-all 에서 돌지 않는다 — 끝난 뒤 병합을 한 번 손으로 돈다(8절).
- **받은 편지함** — git 받기 뒤 `→ cae00 받은 편지함 — …` 줄이 이 박스에 마지막으로 알린 뒤 새로 들었거나 바뀐 글을 찍고, 끝 요약에서 다시 낸다(경고가 아니다).
  이번 판에는 [`../cae00-inbox/2026-10-31.md`](../cae00-inbox/2026-10-31.md) 가 든다. [`../cae00-inbox/README.md`](../cae00-inbox/README.md) 대로 읽고 답은 사용자에게 준다.
  이 박스에는 아직 알린 기록(`infra/.state/inbox-head`)이 없어 이번 실행은 `… 알린 기록이 없어 편지함의 글 N개를 모두 찍는다` 다 — `git pull` 을 먼저 했어도 같다.
  끝 요약을 낸 뒤 그 판을 적으므로 다음부터는 새로 든 글만 찍는다. 그래도 줄이 아예 없으면 `ls -t ~/Projects/HWAXPortal/docs/cae00-inbox/` 로 본다.

## 2. OB-91 우회 걷기(HA-26)

1. 에이전트 서버가 이번 판인지 본다 — `curl -s --noproxy '*' 127.0.0.1:9009/health` 에 `hub_fold` 칸이 있으면 이번 판(HA-34)이다.
2. 에이전트 서버 `.env` 에서 `CHAT_STABLE_PREFIX=0` 줄을 지운다(10-30 백업은 `~/portal-backups/agent.env.stableprefix-*`).
3. 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d`.
4. 전문가를 고른 챗 · 앱을 핀한 챗 · 문서를 붙인 챗을 하나씩 보낸다. LLM 400 이 없어야 한다. 접두 캐시 적중을 다시 잰다(요청서 7절).
5. 그래도 400 이 오면 이번 판은 자동 재시도에서 안내를 첫 시스템 메시지에 합쳐 다시 보낸다. 에이전트 로그에 `'System message must be at the beginning' 400 — 남은 재시도는 이 턴의 안내를 첫 시스템 메시지에 합쳐 보낸다(HA-26)` 줄이 남는다. 그 줄이 보이면 알려 달라(채팅 틀이 사람 발화 머리의 안내도 거절한다는 뜻이다).

## 3. 다른 플랫폼 반영(그쪽 세션이 알려 온 것)

- **SignalForge** — update-all 로 받은 뒤 sf-mcp · sf-backend 를 워치독 락을 쥐고 하나씩 재기동한다. 명령은 SignalForge `docs/DEPLOY_CAE00_2026-10-30.md` 1절 그대로이고, 'sf-mcp semantic import ok' 를 확인한다. 2절대로 시간과 `plm_caution` 을 본다(실제 이름은 `~/ontology-test/`).
  - 10-31 — SignalForge 10-31 cae00 문서(그 리포 `docs/DEPLOY_CAE00_2026-10-31.md`)대로 한다. **sf-mcp 재기동 차례는 그 문서를 따른다**(그 문서 4절 — 병합으로 들어온 뒤).
    그 문서의 `--apply` 는 cae00 에서 하지 않는다(dev 에서만). 2절 dry-run 은 읽기 전용이다 — 받은 편지함 2026-10-31 Q9 가 그 결과를 묻는다.
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

아래는 명령만 지어 두었고 어느 박스에서도 돌리지 않았다(10-30). 사용자 OK 뒤에 한다. 10-31 에 셋이 정해졌다 — 줄마다 적었다.

- **AD-01 다시 짓기** — 154장은 평탄화 고침과 다시 짓기로는 고쳐지지 않는다. MX 백서 동기화 자리표시(본문 한 절 · 글 없음)라 원천을 다시 받아야 한다. 그런데 dev 의 MX 백서 정기 동기화는 10-18 21:26 UTC 뒤 1,122번이 모두 401 이다(AIDataHub 의 `MXWP_INTERNAL_KEY` 가 없다). cae00 은 URL 가드가 막는다. 키 · 가드를 먼저 정하고, 다시 받은 뒤 `deploy/apptainer/reindex-sections.sh`(기본은 셈만 · `--apply` 앞에 백업)를 돈다.
- **AD-05 · AD-06** — dev 원본의 빈 전문가 둘과 데모 카드 셋 지우기(그 뒤 cae00 은 OB-87). **10-31 — 사용자가 dev 에서 직접 돌린다**(`apply.sh` · 판단 C-17). cae00 차례는 8-3.
- **AD-04** — dev DB 사본에서 본문 검색 속도 재기(`EXPLAIN ANALYZE`). **10-31 — 쟀다**(끔 8 ms · 지금 코드로 켜면 6.4 s / 찬 상태 45 s 넘게) → OB-89 는 끈 채로 둔다(판단 C-16).
- **AD-21 의 cae00 원인 후보 — 고쳤다(AIDataHub `6f496fa`, 사용자 결정 A · B · C — 판단 C-18).** 예전 `merge-from-drive.sh` 는 `agent_sample_embeddings` 를 dev 의 대리 키(id)로 덮어쓰고 순번을 올리지 않아, cae00 의 다음 표본 행이 겹친 id 로 거절될 수 있었다(검토 에이전트가 버리는 PG 에서 재현). 이제 전문가 단위로 맞추고 순번을 표의 가장 큰 id 뒤로 민다. cae00 은 받은 뒤 병합을 한 번 손으로 돈다(8-1).

## 6. 챗 관문 넷(HA-27 ~ HA-30) — 받은 뒤 확인 · 손잡이 · 다시 볼 시험

에이전트 서버 `d6c3a84` 와 포털 `dbbb943`(화면은 Drive `images-20261030-220551Z`)을 같은 update-all 로 받는다. 네 관문은 모두 기본 켬이고 **웹 챗에만** 걸린다 —
개인 Claude(게이트웨이 MCP 직결) · 분석 루틴 · 띵킹 · 심의 좌석에는 없다(design-integration 9절 10).

### 6-1. `/health` — 넷이 섰나

```bash
curl -s --noproxy '*' 127.0.0.1:9009/health | python3 -c 'import json,sys
d = json.load(sys.stdin)
for k in ("self_check", "status_wait", "confirm_gate", "xhub_gate"):
    print(k, json.dumps(d.get(k), ensure_ascii=False))'
```

| 칸 | 기대 | 다르면 |
|---|---|---|
| `self_check.gate.mode` | `"1"` | `"num"` · `"0"` 이면 에이전트 서버 `.env` 의 `CHAT_SELF_CHECK_GATE` 줄 |
| `status_wait.on` | `true` · `poll_s` 10 · `max_s` 600 | `false` 면 `.env` 의 `CHAT_STATUS_WAIT_MAX_S=0` |
| `confirm_gate.on` · `lists.loaded` | 둘 다 `true` · `lists.error` 는 `null`. 같은 포털 판이면 목록은 잡 25 · 쓰기 115 · 확인 59(dev 10-31) | `loaded: false` 면 `lists.error` 가 까닭이다 — 형제 리포 `../HWAXPortal/infra/personas/he-team.json`(또는 `CONFIRM_LISTS_PATH`)부터 본다. 그동안 관문은 잡 바닥 목록만으로 돈다 |
| `xhub_gate.on` | `true` | `false` 면 `.env` 의 `CHAT_XHUB_ID_GATE=0` |

update-all §7 도 같은 칸을 한 줄씩 찍는다 — `· 자기검증 관문: 모드 1 · …` · `· 상태 기다림: 10초 간격 · 턴 합 600초 · …` · `· 확인 관문: 목록 잡 25 · …` ·
`· 다른 허브 id 막이: 켬 · …`. 손잡이로 끈 관문은 `○ … 켜려면` 으로 찍히고 끝 요약에서 다시 나온다(실패가 아니다). 운영자 목록을 못 읽었으면 `⚠ 확인 관문` 이다.

### 6-2. 손잡이 — 모두 에이전트 서버 재기동 뒤에 먹는다

start.sh 가 에이전트 서버 `.env` 를 기동 때 한 번 싣고 서버는 다시 읽지 않는다. 자기검증 관문의 두 손잡이도 코드는 턴마다 환경을 읽지만, 떠 있는
프로세스의 환경은 `.env` 를 고쳐도 그대로다(판단 C-21). 아래 기본값은 코드 기본값이고 `infra/env-kits/agent-server.env` 챗 절에 주석으로 있다.
바꾼 뒤 재기동은 도는 심의가 없을 때 `cd ~/Projects/HWAXAgentServer && ./start.sh -d` 다.

| 관문 | 손잡이 | 기본 | 바꾸면 | 반영 |
|---|---|---|---|---|
| 자기검증(HA-27) | `CHAT_SELF_CHECK_GATE` | `1` | `num` — 수만 본다(다른 항목의 값으로 바꾸는 고침 규칙을 끈다 — 짚음이 너무 많을 때). `0` — 끈다(검토자의 고침을 종전대로 다 넣는다) | 재기동 |
| 자기검증(HA-27) | `CHAT_SELF_CHECK_RAW_CHARS` | `6000000` | 턴마다 붙잡는 원문 합(자). `0` 이면 붙잡지 않고 모델이 본 사본과만 견준다. §7 줄에 '원문이 잘린 턴' 이 보이면 올린다 | 재기동 |
| 상태 기다림(HA-28) | `CHAT_STATUS_WAIT_MAX_S` | `600` | 한 턴에 기다리는 시간의 합(초). `0` 이면 끈다(LLM 이 되풀이해 묻는 종전 길) | 재기동 |
| 상태 기다림(HA-28) | `CHAT_STATUS_WAIT_POLL_S` | `10` | 다시 묻는 간격(초) — 2 보다 작게 주면 2 다 | 재기동 |
| 상태 기다림(HA-28) | `CHAT_STATUS_TOOLS` | 빈칸 | 더할 상태 도구 이름(쉼표). 게이트웨이가 읽기로 확인한 도구에만 먹는다 | 재기동 |
| 확인 카드(HA-29) | `CHAT_CONFIRM_GATE` | `1` | `0` 이면 끈다(종전 프롬프트 규칙 '먼저 확인하고 호출' 로 돌아간다) | 재기동 |
| 확인 카드(HA-29) | `CONFIRM_LISTS_PATH` | 빈칸 = `../HWAXPortal/infra/personas/he-team.json` | 다른 운영자 정의 파일(상대 경로는 에이전트 서버 리포 루트가 앵커). **파일 내용**은 바뀐 시각을 보고 재기동 없이 다시 읽는다 | 재기동(경로만) |
| 다른 허브 id(HA-30) | `CHAT_XHUB_ID_GATE` | `1` | `0` 이면 끈다(복제 설치처럼 막음이 잘못 들 때) | 재기동 |

### 6-3. 다시 볼 시험(요청서 7절 · design-integration 12절)

cae00 에서 사람이 SSO 로 로그인한 웹 챗으로 본다(두 QA 와 같은 길).

| 시험 | 볼 것 |
|---|---|
| OT-04 · OT-08 · OT-09 · DW-05 | 초안의 맞는 값이 그대로 나간다(개발모델 수 · 부서 · '20' · 직전 기간 값). 짚기만 한 답은 아래에 '짚었습니다 — 답은 고치지 않았습니다' 와 짚은 곳이 뜬다. `/health` `self_check.gate.counts` 의 `drop_*` · `demote_*` 가 늘고 `fixed_ratio` 가 10-30 재시험(16문항 중 고침 12)보다 내려간다 |
| DW-02 후속 | '체크리스트 돌려서 결과 알려줘' 는 **확인 카드가 먼저 서는 것이 맞다**(말에 도구 이름이 없어 관문이 '시킨 잡' 으로 보지 않는다 — design-integration 9절 9). '실행' 을 누르면 그 턴에 잡이 나가고 첫 상태 조회부터 코드가 기다린다 — 상태 줄의 진행이 30초 안팎으로 오르고 LLM 왕복이 없다. 끝나면 마지막 결과로 답한다. `/health` `confirm_gate.counts` 의 `approved` · `executed` 와 `status_wait.waits` · `ended` 가 는다 |
| DW-03(후속 포함) | 사람이 시키지 않은 StepForge `run_job` 은 카드로 멈춘다. 카드의 작업량 줄은 StepForge `work_outlook` 이다 — 모형 값은 예상 시간이 아니고(하한도 상한도 아니다), 같은 인자로 끝난 잡의 시간이 가장 나은 근거다. '취소' 면 잡이 나가지 않는다(`declined` 가 는다) |
| OT-07 | 다른 허브 결과의 id 를 실은 허브 호출이 나가지 않고 'object_resolve(type_slug, key) 로 다시 풀라' 는 글을 받은 뒤 그 허브에서 다시 푼다. 에이전트 로그에 `[gate] … 다른 허브 id N개` 줄(`grep -a '다른 허브 id' ~/Projects/HWAXAgentServer/agent-server.log \| tail -5`), `/health` `xhub_gate.blocked` 가 는다 |

- 카드는 에이전트 서버 메모리에 30분 산다. 재기동하면 그 전 카드는 없어지니 다시 물어 새 카드를 받는다. 답했거나 30분이 지난 카드는 화면에서 잠긴다.
- 카드 목록은 운영자 정의(`infra/personas/he-team.json`)의 `writes` · `confirm` 과 에이전트 서버의 잡 바닥 목록이다. 운영자 동기화 미리보기의 '읽기를 쓰기로'
  줄은 관문이 그 조회마다 카드를 세운다는 뜻이다 — 사람이 보고 정본을 고칠지 정한다(미리보기는 4절 HP-53 · HP-51 줄 그대로).
- 카드가 지나치게 자주 서면(`confirm_gate.counts` 의 `cards` 가 `ordered` 보다 훨씬 많으면) dev 에 알린다. 잡 이름의 한국어 별칭(체크리스트 → `run_checklist` 등)을
  둘지는 그 수를 보고 정한다(지금은 두지 않는다 — design-integration 9절 9).

## 7. 운영자 정의 · 어휘표 — OB-26 · OB-04(사용자 결정 10-31)

### 7-1. OB-26 — ODB 허브 운영자(he-cad-odbhub)

포털 `7067f94` 가 이 운영자를 둔다(판단 C-15). 입구 도구 다섯은 선택 칸이라 이 박스 게이트웨이에 없어도 동기화가 멈추지 않는다.
미리보기 · `--apply` 는 4절 HP-53 · HP-51 줄 그대로다. 이번 판에서 더 볼 것은 둘이다.

1. 미리보기에서 `he-cad-odbhub` 가 `+`(새로 만든다) 또는 `~` 로 보이고 그 운영자에 `✗` 줄이 없다. `· 일부 he-cad-odbhub: odb-hub 의 <이름> 없이 만든다(선택 앱)` 는
   그 입구 도구가 이 게이트웨이에 없다는 뜻이다(멈추지 않는다).
2. 다섯 이름이 맨 이름으로 나오는지 접두(`odbhub_`)로 나오는지 —

   ```bash
   curl -s --noproxy '*' 127.0.0.1:9110/tools-map | python3 -c 'import json,sys
   m = json.load(sys.stdin)["map"]
   for n in ("get_task", "find_job", "list_jobs", "list_results", "get_checklist_result"):
       how = "맨 이름" if m.get(n) == "odb-hub" else "접두 odbhub_" if m.get("odbhub_" + n) == "odb-hub" else "없음"
       print(n, "—", how)'
   ```

   다섯 줄을 받은 편지함 [`../cae00-inbox/2026-10-31.md`](../cae00-inbox/2026-10-31.md) Q4 의 답으로 사용자에게 준다. 포털이 그 꼴대로 필수 `key_tools` 를 채운다(운영자 todo).

### 7-2. OB-04 — 운영 앱 둘의 '(시험)' 라벨

포털 `dbbb943` 가 dynaforge-prod · stepforge-prod 를 어휘표의 시험 사본에서 뺐다(판단 C-14). 라벨은 이 박스 권한표의 몫이다.

1. 받은 뒤 — `curl -s --noproxy '*' 127.0.0.1:9110/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["core_vocab"]["staging_hidden"])'` 가 `[]` 다.
   두 앱이 웹 챗 묶음 · 개인 Claude 목록 · `search_tools` 에 보통 앱으로 다시 보인다.
2. 백업 — `cp ~/Projects/HWAXPortal/backend/config/access.local.yaml ~/portal-backups/access.local.yaml.ob04-$(date +%Y%m%d)`.
3. `backend/config/access.local.yaml` 에서 게이트웨이 백엔드 `dynaforge-prod` · `stepforge-prod` 를 든 플랫폼 항목의 `label:` 에서 '(시험)' 을 걷는다. 새 이름은 사람이 정한다.
   같은 항목의 안내 문구(10-27 HG-19 가 짚은 줄)에 '시험 사본' 이 있으면 함께 고친다. `id` · `gateway` · 주소 · 토큰 칸은 건드리지 않는다.
   포털은 이 파일을 요청마다 바뀐 시각으로 다시 읽는다(재기동 없음).
4. 확인 — 게이트웨이는 포털 정책을 60초마다 다시 받는다. 1분 뒤에 아래로 본다.

   ```bash
   curl -s --noproxy '*' 127.0.0.1:9110/tools-map | python3 -c 'import json,sys
   for a in json.load(sys.stdin)["apps"]:
       if a["app"] in ("dynaforge-prod", "stepforge-prod"): print(a["app"], "—", a["label"], "· 도구", a["tool_count"])'
   ```

   라벨에 '(시험)' 이 없으면 된다. 그대로면 그 라벨은 다른 자리(게이트웨이 백엔드 설정 · 허브 등록)에서 온다 — 어느 자리인지 dev 에 알린다.
   라벨의 '(시험)' 은 게이트웨이가 같은 도구 사본의 정본을 고를 때 사본 표지로도 읽는다 — 걷어야 점수가 같을 때 두 앱이 뒤로 가지 않는다.

## 8. AIDataHub — 받은 뒤 병합 한 번(`6f496fa`) · 데이터 단계 차례(사용자 결정 10-31)

### 8-1. 병합 한 번(결정 A — 판단 C-18)

update-all 은 Drive 덤프가 바뀌었을 때만 병합한다. 덤프가 그대로면 `AIDH 덤프 변화 없음 — merge 생략` 이 찍히고 새 병합 코드가 돌지 않는다.
그래서 받은 뒤 한 번 손으로 돈다 — 도는 심의가 없고, 디스크에 운영 직전 스냅샷(몇 GB) 자리가 있을 때.

```bash
cd ~/Projects/AIDataHub && ./deploy/apptainer/merge-from-drive.sh
```

비파괴 병합이다(행을 지우지 않는다 · 운영 직전 스냅샷을 `/data/backups/aidh/pre-merge-<시각>.sql.gz` 에 남긴다). 볼 줄 —

- `✓ agent_sample_embeddings: 덤프 판으로 다시 지은 agent N · 지우기만 M · 순번을 X 로 올림 (총 K행)` — '순번을 … 로 올림' 은 예전 병합이 남긴 겹침을
  걷었다는 뜻이다(보통 첫 번에만 나온다). 같은 덤프로 다시 돌리면 바꿀 것이 없다.
- `⚠ agent_sample_embeddings: 색인된 표본 글이 sample_queries 와 다른 agent N개 — … 이 박스의 임베더로 다시 지어야 한다: <이름들> — 끝난 뒤 이 박스에서:
  curl -fsS -X POST http://127.0.0.1:<API 포트>/api/agents/resync-samples-all` — 병합 실패가 아니다(결정 B — 알리기만 한다). 다시 지을지는 사람이 정한다.
  지으면 그 curl 한 번이다(쓰기 — 모든 전문가의 표본 임베딩을 이 박스의 임베더로 다시 계산한다). update-all 은 이 줄을 경고로 세지 않는다(결정 C).
- 끝이 `✗ merge 일부 실패` 면 `/tmp/aidh-merge.log` 를 본다(나머지 표는 반영됐다). `⚠ merge 는 됐지만 dev 에만 있는 열이 빠졌다` 면 API 가 이관을 마친 뒤 한 번 더 돈다.

### 8-2. 읽기 확인(쓰지 않는다)

```bash
cd ~/Projects/AIDataHub/deploy/apptainer && ( source ./_common.sh && load_env &&
  apptainer exec "instance://$INST_POSTGRES" psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c \
  "SELECT (SELECT max(id) FROM public.agent_sample_embeddings), s.last_value FROM pg_sequences s
    WHERE format('%I.%I', s.schemaname, s.sequencename) = pg_get_serial_sequence('public.agent_sample_embeddings', 'id')" )
```

`가장 큰 id|순번` 한 줄이 나온다. 순번이 가장 큰 id 보다 작지 않으면 맞다. 그 뒤 운영자 동기화(4절 AD-21 줄)에서 저장 뒤 500 · 표본 색인 실패가 다시 나오지
않는지, 같은 줄의 로그 grep 에 새 줄이 없는지 본다.

### 8-3. 데이터 단계 차례 — dev 지우기 → OB-73 → 병합 → OB-87(판단 C-17)

1. **dev — 사용자가 직접.** `bash /data/backups/aidh/ad05-ad06-20261030T211507Z/apply.sh`(dev 박스, 13:45 KST 매일 덤프 전). 적용 직전 목록이 백업 때와 다르면
   멈춘다. 되돌리기는 같은 폴더의 `restore.sql` 이다. 데모 레코드 셋을 소프트 삭제하고 두 전문가(kooremapper-modelmeta · dynaforge-report)를 지운다.
2. **cae00 — OB-73 먼저.** 박스 화면 확인(10-27 표의 넷 — 원문 [`../request_1015.md`](../request_1015.md)).
   - K9 — 데모 카드 `…012` 를 열면 JSON 원문이 코드 칸으로 보인다. **dev 지우기가 실린 덤프가 이 박스에 병합되기 전에** 본다 — 병합이 레코드의 소프트 삭제를
     옮겨 카드가 목록에서 빠진다(10-27 AD-13 'dev 에서만 지우면'). 이미 병합됐으면 볼 수 없었다고 적는다.
   - K2 — 로그인이 만료되면 전문가 상세 · 카드 화면이 로그인 화면으로 가고, 상세 실패는 공용 문구와 '다시 시도' 로 보인다.
   - K6-5 — 설명도 역할 문서도 없는 전문가(dynaforge-report)의 상세에 '아직 등록되지 않은 전문가' 가 보인다.
   - K7 — 역할이 빈 전문가가 심의 좌석에 이름 · 키로 앉고 `persona_role_empty` 경고가 난다.
   - 빈 전문가 행은 병합이 지우지 않아 OB-87 까지 남는다 — K6-5 · K7 은 병합 뒤에도 볼 수 있다.
3. **cae00 — 병합.** dev 지우기가 실린 덤프를 update-all(또는 8-1)이 병합한다. 0 으로 끝나 표식이 적혔는지 본다 — 3 으로 끝나면 표식이 남지 않아 옛 덤프가
   다시 든다(10-27 AD-13).
4. **cae00 — OB-87.** 이 박스에서 두 전문가를 지운다(AD-13 순서 5 — 병합은 행을 지우지 않는다). dev 와 같은 길이다 — AIDataHub API 의
   `DELETE /api/agents/<키>`(쓰기 — 사람이 한다). 다음 병합 뒤 다시 들어오지 않았는지 본다(순서 6).

## 9. 아직 오지 않은 것

- **받은 편지함** — 바깥 답이 필요한 물음은 [`../cae00-inbox/`](../cae00-inbox/README.md) 에 날짜별로 든다(판단 C-20). 이번 판에는 `2026-10-31.md`(Q1 ~ Q8)가 든다.
  모두 읽기만 하는 물음이고 답은 리포가 아니라 사용자에게 간다.
- **HEAXHub 운영 노드 터널 전환(HEAXHub 10-31 HH-14 ~ HH-16)** —
  ⟪자리 — 다른 워크플로가 짓는 중이다. 결과(커밋 · 운영 노드 터널로 가는 매니페스트 넷 · dev 박스의 박스별 매니페스트 덧씌우기 · HH-16 · 전환 창의 차례 ·
  되돌리기)가 오면 이 줄을 절로 바꿔 채운다. 그때까지 이 박스에서 할 것은 없다 — 매니페스트는 전환 창에서만 합친다.⟫
- **DocForge 0.3.1** — 배치(release · HEAXHub 등록 사본 · SIF · Drive)가 그 세션의 사용자 승인을 기다린다. Drive 판이 오면 3절 DocForge 줄과 C-8 고침 셋을 더한다.
- **MaterialTwinWeb HH-01**(긴 재료 카드를 절 여러 개로 — MaterialTwinWeb `a3563b6`) — cae00 사본(`6e45b40`)보다 61 커밋 앞이다. SIF · Drive 판이 오면 받는 법을 더한다.
  HH-10(박스마다 다른 id)은 받은 편지함 Q1 이다.
- **SmartTwinMCP PA-16 · PA-19** — 10-31 다시 청했다. 답이 오면 OB-92 · OB-34 · OB-25 의 길을 더한다.
- **HA-33 덧붙임**(SignalForge 주의 줄을 VOC 미리보기에) — 짓는 중이다. 들어오면 4절 HA-33 줄에 볼 것을 더한다.
