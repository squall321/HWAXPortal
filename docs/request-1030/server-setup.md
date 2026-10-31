# 10-30 수정 요청 — cae00 에서 사람이 할 일

요청서 정본 [`../request_261030.md`](../request_261030.md) · 플랫폼별 시트 [`platforms/`](platforms/00-INDEX.md) · 받은 답 [`outbound.md`](outbound.md).
이 문서는 판이 올라갈 때마다 고친다. **0절 표에 '올림' 이라 적힌 판만 update-all 로 받는다.** 아직 오지 않은 판은 '예정' 이다.
10-31 에 6절부터를 더했다 — 챗 관문 넷(HA-27 ~ HA-30)의 확인 · 손잡이 · 다시 볼 시험, OB-26 · OB-04, AIDataHub 병합 한 번과 데이터 단계 차례, 아직 오지 않은 것, 서비스 감시 켜기(10절 — 사용자 결정 A28).
바깥 답이 필요한 물음은 이 문서가 아니라 받은 편지함 [`../cae00-inbox/`](../cae00-inbox/README.md) 에 든다(판단 C-20).

> 명령의 경로는 cae00 기준(`~/Projects/<리포>`)이다. 비밀 값은 화면 · 로그 · 채팅에 붙이지 않는다. 에이전트 서버 주소 `127.0.0.1:9009` 는 루프백이라 `--noproxy '*'` 를 붙인다.

## 0. 받는 판

| 리포 | 판 | 무엇 | 상태 |
|---|---|---|---|
| 에이전트 서버 | `e94bc09` · `3cb8cbe` | HA-34(접기 흔적) · HA-26 재시도 몫 · HA-31(전문가 검색 가로채기) · HA-32(타입 이름 대응) · HA-33(VOC 미리보기) · HA-08(위키 꺼짐 문구), 높음 넷의 골격(동작 그대로) | 올림 |
| 에이전트 서버 | `d6c3a84` | HA-27(자기검증 관문) · HA-28(상태 기다리기) · HA-29(확인 카드) · HA-30(다른 허브 id) — 맞물림 시험 I-1 ~ I-8 · 반대 검토 두 차례 | 올림 — 확인 · 손잡이 · 다시 볼 시험은 6절 |
| 에이전트 서버 | `8dd579a` | HA-33 덧붙임(SignalForge '주의 —' 줄을 행이 있어도 VOC 미리보기에) · SP 0.4.67 응답 꼴 시험(코드는 그대로) | 올림 — 에이전트 서버 재기동으로 켜진다(4절 HA-33 줄) |
| 게이트웨이 | `c70ec21` · `602bbb2` | HG-21(소수부를 IMEI 로 가리던 것 — dev 출력에서 2,780곳) · HG-22(사람 칸 이름 · 메일 · 성씨 계정 · 사설 IP · `rest_call`), `602bbb2` 는 시험만(어휘표 OB-04 뒤 — 시험 사본 숨김 시험이 실제 표의 셋에 기대지 않게) | 올림 — 가림 범위는 판단 C-11 |
| 게이트웨이 | `bbd5aef` | 루틴 울타리 닫기 목록에 StepForge `mesh_size_advice`(이름의 'advice' 로 읽기로 열렸지만 기본값으로 메타데이터를 쓴다) | 올림 — 게이트웨이 재기동으로 켜진다(읽기 목록은 기동 때 읽는다) |
| 포털 | `6a76f58` · `dbbb943` | HP-51(운영자 앱 없음 표지) · HP-52(씨앗 `from: items`) · HP-53(writes · confirm · ARP 함정 줄 · 저장 뒤 500 견딤) · HP-55(update-all 문구) · HP-56 · HA-32(어휘표 types · '전작' · '후속 모델'), 그 뒤 확인 카드 단추 · 짚기만 한 자기검증(화면) · 운영자 목록 C-15 · update-all §7 관문 줄 · env 킷 손잡이 · OB-26(ODB 허브 운영자) · OB-04(어휘표) | 올림 — 화면은 Drive `images-20261030-220551Z`(drive-drift 포털 일치) |
| 포털 | 이 문서가 든 판 | 받은 편지함(`docs/cae00-inbox/` · update-all §1 알림) · StepForge 확인 목록(늘 확인 8 · 시킨 때만 33) · 점검 스크립트 둘(효과 매니페스트 · 상대경로) · 리스크 ECAD 화면 요청서 · 설계서 셋 | 올림 — 운영자 동기화(7절)로 켜진다 |
| AIDataHub | `df7d45b` · `6f496fa` · `684765b` | AD-19 · AD-20(추천 · 기록 목록) · AD-21(저장 뒤 500) · AD-03(DRM 머리) · AD-07(`as_of`) · AD-01 코드(하위 절 평탄화 · 다시 짓기 명령), `6f496fa` 는 병합이 표본 임베딩을 전문가 단위로 맞추고 순번을 올린다(AD-21 후속), `684765b` 는 `.env.example` 의 내부 주소 예외를 끈다(AD-17 (나) — 이미 있는 `.env` 는 그대로, 판단 C-24) | 올림 — 받은 뒤 병합 한 번(8절) · 데이터 단계는 5 · 8절 |
| MX 백서 | `bb0a6a1` · `bd2e79b` | MW-12 · MW-01 | 올림(그쪽 세션) |
| SignalForge | `0e2ac46` · `ec40075` · `f004cd0` | SG-19 · SG-04 주의 칸 | 올림(그쪽 세션) — 차례는 3절 |
| SignalForge | `404fe42` · `06a506b` · 지금 main `da8f4b6` | 그쪽 cae00 문서 2026-10-31 · 2026-10-31-plm-kit(PLM 거울 받기를 SP 키트 2026-10-21 로) | 올림(그쪽 세션) — **update-all 이 sf-mcp 를 곧바로 다시 띄운다 — 사용자 결정 대기**(3절) |
| SmartTwinExplorer | `4f5e0e0` | PA-20 | 올림 — Drive staging 번들(3절) |
| DocForge | `e72cbe5` · `ab5547e`(0.3.1) · `8444575` · `213c411` | HH-14 · HH-03(SP 거울을 실제 공개에) · SP 킷 2026-10-21 | 코드 끝(main `9eb9a52` — `3e4e677` StepForge 수신부에 맞춤 · `b3e1b46` 시험장 회귀 · CLAUDE.md SP 규칙) — 배치는 그 세션의 사용자 승인 대기(release 는 `3ba0f6f` 0.3.0) |
| KooRemapper | `0c1113f` · `f36270f` · `a3eff43` | KR-23 — 레시피 자동 관문을 MCP 설명에 적음(사용자 결정 그대로) · KR-01 · KR-16 — 과제 검색이 별칭을 대조하고 순위를 매긴 뒤 자른다(행마다 match_kind) | 올림(그쪽 세션) — update-all 하나, 재기동 때 이관 0018 · 화면은 다음 Drive |
| StepForge | `b2c70f1` · Drive `dist-20261030-135126Z` | ST-12 — 합치기 진행률(경과 시간) · `work_outlook` · owner 가림(+ 온톨로지 그래프 도구 일곱) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 교체, 교체 전 도는 잡이 없는지 본다 |
| StepForge | `a166d2a` · `51c8788` · Drive `dist-20261031-014632Z` | SP 키트 2026-10-21 수신부 · 그래프 따라잡기 · CLAUDE.md SP 규칙(빌드는 main 끝 — `005407Z` 는 코드가 같은 앞 판) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 `014632Z` 를 받는다 |
| HEAXHub | `055b023` · `5e2cafa` · `beebec5` | HH-15 박스 덮어쓰기 · HH-16 남은 서비스 정리 · 검토 아홉 고침, cae00 박스 파일 넷과 전환 차례, 시험 가드 | 올림 — update-all §2 가 받는다. 받기 전 점검과 전환은 9절 · 받은 편지함 Q8 |
| 리스크 앱(HWAXRisk) | `9bd5f48` · Drive(HEAXHub) `dist-20261031-021740Z` | ECAD 1단계(ODB 보드 싣기 · 사람이 고르는 보드 · 보드 노드 · 정직한 표지) + 사용자 결정 셋(그 사람 PAT 만 · pwr/rf 2단계까지 · 상한에 ECAD 부품) — MCP 도구 31 → 33 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk` 로 바꾼다. 화면은 리스크 화면 세션 몫(`docs/design-risk-review/ecad-1031/frontend-request.md`) |
| MaterialTwinWeb | `a3563b6` · `4273720` · Drive(HEAXHub) `dist-20261031-055937Z` | HH-01(긴 재료 카드를 절 여러 개로) · 저장소 비공개 전환 적용 문서 | 올림(그쪽 세션) — 비공개 전환 차례는 9절(먼저 받고 → 사용자가 비공개 → 토큰). `4273720` 판 SIF 는 10-31 포털 세션이 Drive 에 올렸다(문서 커밋 뒤 다시 지은 SIF — 앱 커밋과 캐시 열쇠가 맞아야 이 박스 허브가 띄운다) |
| 에이전트 서버 | `ec83e51`(병합 — HA-09 S0 `07981fd` · HA-30 R9 `64811fa` · HA-11 `a014b0c` · E-5) | 끊긴 심의를 끝난 라운드 뒤부터 잇는다(진행 일지 · start.sh 가 옛 프로세스가 끝난 뒤 띄운다 · `AGENT_GRACEFUL_S` 1초 — 사용자 결정 A-7) · 게시판 글에만 나온 id 를 배우지 않는다 · 심의 기준일(`delib_opts.as_of`) · 전문가 고르기 기준선(`/seat-eval` · 실사용 질문 모으기와 그림자 기록은 기본 꺼짐) | 올림 — 에이전트 서버 재기동으로 켜진다. `/health` 에 `delib_as_of: true` · `core_vocab.personas` · `seat_questions.collect: false`. 끊긴 심의 잇기 확인은 사람 몫(2라운드 중간에 `AGENT_RESTART_FORCE=1 ./start.sh -d` → `deliberate_status` 의 `resume.rounds_done` 이 0 보다 크다 → `deliberate_continue`) · 운영 물음은 받은 편지함 Q13. E-5 모으기 켜기는 [`../request-1029/server-setup.md`](../request-1029/server-setup.md) 9절(사람) |
| 포털 | `e2a3c6a`(env 킷 병합) · `b4b19ec`(HA-11 병합) · `9e17e08`(E-5 · 이력) · 옛 남은 일 병합 · A31 · Drive `images-20261031-073252Z` | 에이전트 env 킷(`AGENT_STOP_GRACE_S` 4 · `AGENT_GRACEFUL_S` 1) · 심의 옵션 '기준일' · 관리자 '전문가 고르기 검토' · 어휘표 `personas` 칸 · 옛 남은 일 정리(A1 ~ A32 · 받은 편지함 backlog Q1 ~ Q22) · 데모 메일 자리표시(A31 — 이 박스는 설정에 따로 적어 영향 없음) | 올림 — 화면은 Drive 판 |
| StepForge | `e8bf3d8` · Drive `dist-20261031-072639Z` | `mesh_size_advice` 기본 `store=false`(쓰기는 `store=true` 를 줄 때만) · 도구 176 전부 표지(readOnlyHint · destructiveHint) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다 |
| MX 백서 | `48da3fd` 까지 · Drive `images-20261031-073148Z` | 위키 화면 W7 · 어두운 모드 링크 색 — 위키가 꺼진 이 박스에서는 보이는 차이가 없다 | 올림(그쪽 세션) — update-all 이 latest/ 를 받는다 |
| HEAXHub | `7b9a8ed` | Drive 되돌림 판 보존 3 → 5(dev 의 올리기 스크립트만 — 이 박스에는 영향 없음, 사용자 결정 10-31) | 올림 |
| 게이트웨이 | `63fbc4f`(병합 — B16 ① `c9c3419` · HA-20 `0bef377` 계열) | `KOORM_SEND_PLAT`(KooRemapper 위임에 plat 서명 머리 — provision.env 에 적으면 update-all 이 싣는다) · 패널 PAT 검증 · `/tools-map` 의 `panel_read`(HA-20 — 포털 손잡이 `MCP_APPS_HOST` 가 꺼져 있으면 패널은 뜨지 않는다) | 올림 — 게이트웨이 재기동으로 켜진다 |
| WebResearchMCP | `d76911a` · Drive(HEAXHub) `dist-20261031-075456Z` | 호스트별 잠금으로 나감 간격 · 줄 상한 · 한 연결씩 · 서킷 다시 보기(B20 · B21) | 올림 — `dist-from-drive.sh` 로 받는다 |
| LaminateAnalyzerMCP | `113405d` · Drive(HEAXHub) `dist-20261031-081703Z` | 절차 씨앗이 쓰는 도구 넷의 인자 설명 22개(B37 §2-1 — 형 · 기본값 그대로) | 올림(그쪽 세션 · Drive 는 포털 세션) — `dist-from-drive.sh` 로 받는다 |
| 에이전트 서버 | `1159376`(2차 — 백로그 B17 ~ B19 `460d2e0` · HA-20 P1 `1159376`) | 막힘 · 빈 웹 결과는 근거로 세지 않는다([가설 단계]가 바르게 붙는다) · 이어하기 좌석 프롬프트 · 1라운드 조회 턴도 이전 결론을 가린다 · 챗 MCP Apps 패널의 SSE `ui_resource`(포털 손잡이가 꺼져 있으면 묶이지 않는다 — HA-05 그대로) | 올림 — 에이전트 서버 재기동 |
| 포털 | `a694e19c`(2차 — B1 · A25 · B3 · B8 ~ B15 · HA-20 P2 ~ P4) · `fb640a3a` · Drive `images-20261031-083656Z` | update-all 의 심의 기다림 하나가 에이전트 서버 · 게이트웨이 · SignalForge 재기동을 덮는다(A25 — 받은 뒤 다음 update-all 부터) · drive-drift 가 짓지 않은 앱을 짚는다 · 절차 게시 미리보기 게이트 · 전문가 색을 키 하나로 · 패널 창구(손잡이 `MCP_APPS_HOST` 기본 꺼짐 — 끄면 404) · index.html `frame-src 'self'` | 올림 — 화면은 Drive 판. A25 동작은 [`../delib-ops/server-setup.md`](../delib-ops/server-setup.md) · [`../cae00-deploy-guide.md`](../cae00-deploy-guide.md) 에 적었다 |
| 리스크 앱(HWAXRisk) | `be8d974`(웹 심의 멈춤 A24 몫) · Drive(HEAXHub) `dist-20261031-083405Z` | 엔진이 사람이 멈춘 패널 심의를 알리면 결정문 없는 done 이 아니라 패널을 닫고(error) 잡을 멈춘다 — 에이전트 서버 a24 와 같이 또는 먼저 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk` |
| 에이전트 서버 | `c6aad34`(3차 — 웹 심의 멈춤 A24 (나)) | 끊긴 웹 심의를 대화 id 로 멈추는 엔진 창구(포털 중계 경유) · 결정문이 나온 뒤(마무리 중)에는 409 finishing · 멈춘 실행은 cancelled 로 남는다 | 올림 — 에이전트 서버 재기동. 리스크 앱 `be8d974` 와 같이 또는 먼저 받는다 |
| 포털 | `e8b01282`(3차 — A24) · `52ccb245` · Drive `images-20261031-085839Z` | 멈춤 창구(세션 + CSRF · 그 대화의 주인만) · 심의 화면 '멈춤' 버튼 · 멈춤 기록이 대화에 남는다 · 낡은 화면이 새 심의를 멈추지 않는다 | 올림 — 화면은 Drive 판 |
| AIDataHub | `048ff6a` | 병합 끝 요약에 '운영이 더 새롭다며 건너뛴 행 중 내용이 다른 수(그중 조회로 올라간 수)' 한 줄(셈만 — 병합 판단은 그대로) · 한국어 검색 재정렬기 견주기 기록(이 박스는 GPU 가 없어 끈 채 둔다) | 올림 — update-all 이 받는다. 조회가 updated_at 을 올리지 않게 하는 고침은 다음 판(사용자 결정 10-31) |
| 리스크 앱(HWAXRisk) | `7b1042d`(백로그 B22 ~ B32 · A18 + RK-01 보내기 · 거두기) · Drive(HEAXHub) `dist-20261031-091813Z` | 원천 겹침 알림 · 대상 감사 · 근거 빼기와 사람 개입 요약 · 분류 어휘 검사 · 요구 여유 · rekey · 큰 배정 건너뜀 · 잘린 계면 제외 · 지식 그래프를 서비스 계정으로 RA 에 보내기(비공개는 보류 · 비공개 · 폐기 · 주인 변경에 거두기) | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`. RA 보내기 확인은 리스크 앱 checklist 2장 'RK-01 cae00 확인'(쓰기 PAT 주인이 RA 시스템 관리자인가 · 온톨로지 부트스트랩) |
| 리스크 앱(HWAXRisk) 화면 | `dbe5f93`(A32 화면 세션) · Drive(HEAXHub) `dist-20261031-094206Z` | 웹 '과제 만들기' 가 늘 422 이던 결함(B33 — 등급 칸) · 사람 자격 화면(포털 PAT 자동 등록 · 끄기, B35) · 패널 잡의 Claude 판단 선택(동의 칸은 미리 체크하지 않는다, B36) · ECAD 보드 화면 · 과제 · 대상 · 홈 화면 몫(B34) · M3 화면 일곱 절 · 대상 · 과제 화면이 비던 타입 결함 | 올림 — 위 리스크 앱 줄과 같은 길로 받는다. 화면이 '모름' 으로 비우는 칸은 백엔드 후속(진행 중)이 채운다 |
| KooRemapper(DynaForge) | `3929a4e` | 인자 설명 36(B37 ①) · MCP → REST 한도 손잡이 `KOORM_MCP_API_TIMEOUT_S`(기본 540 — 게이트웨이 600 안쪽) · 도구 호출마다 벽시계 기한 · 시간 넘긴 잡 요약에 `KOORM_JOB_TIMEOUT_SEC`(B38 ②). plat 서명 헤더로 막기(③)는 그쪽 사용자 결정으로 이번에 안 함 | 올림(그쪽 세션) — 파이썬만 바뀌어 update-all 재기동으로 MCP 도 새로 뜬다 |
| 게이트웨이 | `5f4ba5f`(병합 — `9b37b31` ~ `10bb6ec`) | 10-29 4차 E-2 · E-4 — 앱 역할로 검색 순위 · 접기 · 노출(허브 가족은 늘 접두 · 옛 맨 이름은 호출 별칭) · 개인 Claude 보기 셋(전체 · 묶음 · 가벼운) | 올림 — 게이트웨이 재기동으로 켜진다. 받은 뒤 확인은 [`../request-1029/server-setup.md`](../request-1029/server-setup.md) 8절 · 받은 편지함 Q14 |
| 포털 | `d31bca1` · `4034845` · Drive `images-20261031-055500Z` | 같은 묶음의 포털 몫 — 사람 설정 `users.hub_view` · 토큰 화면 보기 고르기 · 등록 배치 머리 `X-HWAX-View: portal` · Q-2 확인(목록은 늘 접두, 사용자 10-31) | 올림 — 화면은 Drive 판. 확인은 위와 같다 |

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
  - 10-31 — SignalForge 10-31 cae00 문서 둘(그 리포 `docs/DEPLOY_CAE00_2026-10-31.md` · `docs/DEPLOY_CAE00_2026-10-31-plm-kit.md`)대로 한다. 그 문서의 `--apply` 는
    cae00 에서 하지 않는다(dev 에서만). 2절 dry-run 은 읽기 전용이다 — 받은 편지함 2026-10-31 Q9 가 그 결과를 묻는다.
  - ⚠ **update-all 이 그 문서의 재기동 차례를 앞당긴다.** 그 문서는 'sf-mcp 재기동은 다시 태깅이 병합으로 들어온 뒤(4절) — 코드는 지금 받아도 떠 있는 인스턴스는
    재기동 전까지 옛 코드' 를 전제로 한다(손 `git pull`). 그런데 update-all §2(deploy-all signalforge)는 받은 git 판이 지문을 바꿔 `scripts/down.sh` → `scripts/up.sh` 로
    sf-mcp 까지 새 코드로 다시 띄우고, §4 의 update-sites signalforge-mcp 도 지문으로 재기동한다.
    - 새 매처로 뜬 sf-mcp 는 그 문서 '순서' 절이 적은 빈 결과를 낸다 — dev 적용 → 덤프 → 다음 병합까지(그 문서 3 · 4절).
    - plm-kit 문서의 새 PLM 받기도 같은 재기동에 걸린다. 새 코드는 새 거울 자리(`crawler/data/plm/sp-core/`)만 읽고(30초마다 다시 본다) 그 자리는 처음 받기 전까지 비어,
      그동안 PLM 칸(과제 · 개발모델 검색 · `plm_caution`)이 빈다. 박스 cron(6시간마다)을 기다리지 말고 update-all 바로 뒤에 처음 받기를 한다(아래).
    - **사용자 결정(10-31) — 빈 결과 창을 받아들인다.** update-all 바로 뒤 처음 받기(`plm-sync.sh --full`)를 하고, 10-31 문서 2절 dry-run(읽기)을 돌려 결과를
      사용자에게만 알린다(받은 편지함 Q9). 사용자가 '적용' 하면 dev 에서 적용하고 다음 덤프 병합(약 30분 간격)으로 창이 닫힌다. 새 매처를 손잡이 뒤로 숨기지 않는다.
      ⚠ update-all 없이 손으로 `git pull` 만 하면 sf-mcp 가 옛 코드로 남는다. 그 채로 다시 태깅이 병합되면 옛 매처가 'Fold8 Ultra' 를 GZF8 로 풀어, 비는 것이
      아니라 Ultra 글이 빠진 답(틀린 답)이 나온다 — 그때는 sf-mcp 재기동을 꼭 한다(SignalForge `4859b0d` 문서 4절). update-all 4단계는 새 코드로 다시 띄우므로
      이 일이 없다.
  - plm-kit 문서의 cae00 몫(받은 뒤 — 그 문서 1 · 3 · 4절) — ① 처음 받기 `cd ~/Projects/SignalForge && bash scripts/plm-sync.sh --full; echo "exit=$?"`(연결 점검을 겸한다 —
    0 정상 · 2 확인 필요(`problems` 를 본다) · 1 멈춤(`error` 가 까닭)) → ② 옛 거울과 건수 대조(그 문서 1절 명령 — 거의 같은 수) → ③ get_ontology 의 plm 이 새 수 ·
    `last_result` ok(그 문서 3절) → ④ 맞으면 옛 거울 파일 `crawler/data/plm/sp_mirror.sqlite` 를 지운다(그 문서 4절 — 쓰기라 사람이 한다). sf-mcp 를 따로 다시 띄울
    일은 없다 — update-all 이 이미 띄웠으면 새 코드가 30초 안에 새 거울을 읽는다.
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

아래는 명령만 지어 두었고 어느 박스에서도 돌리지 않았다(10-30). 사용자 OK 뒤에 한다. 10-31 에 넷이 정해졌다 — 줄마다 적었다.

- **AD-01 다시 짓기** — 154장은 평탄화 고침과 다시 짓기로는 고쳐지지 않는다. MX 백서 동기화 자리표시(본문 한 절 · 글 없음)라 원천을 다시 받아야 한다. 그런데 dev 의 MX 백서 정기 동기화는 10-18 21:26 UTC 뒤 1,122번이 모두 401 이다(AIDataHub 의 `MXWP_INTERNAL_KEY` 가 없다). cae00 은 URL 가드가 막는다 — **10-31 사용자 결정 AD-17 (나)로 그대로 둔다**(cae00 은 정기 동기화를 켜지 않고 덤프 병합이 정본이다, 판단 C-24 · AIDataHub `684765b` 는 예시만 바꿔 이 박스 `.env` 는 그대로다). 그래서 남은 것은 dev 의 키다 — dev 가 다시 받은 뒤 `deploy/apptainer/reindex-sections.sh`(기본은 셈만 · `--apply` 앞에 백업)를 돌고, cae00 은 그 덤프를 병합한 뒤 이 박스에서 같은 명령을 돈다(병합이 절을 dev 값으로 쓰지만 이 박스에 남은 절은 다시 짓기로만 걷힌다 — 10-27 검토 AD-01 '권하는 길' 4).
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
| `status_wait.on` | `true` · `poll_s` 10.0 · `max_s` 600.0(값은 실수로 온다) | `false` 면 `.env` 의 `CHAT_STATUS_WAIT_MAX_S=0` |
| `confirm_gate.on` · `lists.loaded` | 둘 다 `true` · `lists.error` 는 `null`. 같은 포털 판이면 목록은 잡 25 · 쓰기 115 · 확인 59(dev 10-31) | `loaded: false` 면 `lists.error` 가 까닭이다 — 형제 리포 `../HWAXPortal/infra/personas/he-team.json`(또는 `CONFIRM_LISTS_PATH`)부터 본다. 그동안 관문은 잡 바닥 목록만으로 돈다 |
| `xhub_gate.on` | `true` | `false` 면 `.env` 의 `CHAT_XHUB_ID_GATE=0` |

update-all §7 도 같은 칸을 한 줄씩 찍는다 — `· 자기검증 관문: 모드 1 · …` · `· 상태 기다림: 10.0초 간격 · 턴 합 600.0초 · …` · `· 확인 관문: 목록 잡 25 · …` ·
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
4. 확인 — 게이트웨이는 포털 정책을 60초마다 다시 받고, 라벨은 따로 도는 재활 주기(60초)에서 바뀐다 — 고친 뒤 길면 2분쯤 걸린다. 2분 뒤에 보거나,
   곧바로 보려면 게이트웨이 `/refresh`(두 주기를 한 번에 돈다 — 토큰은 화면에 내지 않는다) 뒤에 본다.

   ```bash
   python3 -c 'import json,os;print("header = \"Authorization: Bearer %s\"" % json.load(open(os.path.expanduser("~/Projects/HWAXMcpGateway/gateway_config.json")))["_gateway"]["token"])' \
     | curl -s --noproxy '*' -K - -X POST http://127.0.0.1:9110/refresh      # 선택 — 2분을 기다리지 않을 때
   curl -s --noproxy '*' 127.0.0.1:9110/tools-map | python3 -c 'import json,sys
   for a in json.load(sys.stdin)["apps"]:
       if a["app"] in ("dynaforge-prod", "stepforge-prod"): print(a["app"], "—", a["label"], "· 도구", a["tool_count"])'
   ```

   **두 줄이 나와야 한다.** 줄이 모자라면(하나도 없거나 하나뿐) 빠진 앱의 백엔드가 이 박스 게이트웨이에 없다는 뜻이다 — 그 앱의 라벨은 볼 수 없었으니 '못 봄' 과
   함께 그 출력을 알린다(빈 출력은 통과가 아니다). 나온 줄의 라벨에 '(시험)' 이 없으면 된다. 2분(또는 `/refresh`) 뒤에도 그대로면 그 라벨은 다른 자리(게이트웨이 백엔드 설정 · 허브 등록)에서 온다 —
   어느 자리인지 dev 에 알린다.
   라벨의 '(시험)' 은 게이트웨이가 같은 도구 사본의 정본을 고를 때 사본 표지로도 읽는다 — 걷어야 점수가 같을 때 두 앱이 뒤로 가지 않는다.

## 8. AIDataHub — 받은 뒤 병합 한 번(`6f496fa`) · 데이터 단계 차례(사용자 결정 10-31)

### 8-1. 병합 한 번(결정 A — 판단 C-18)

**먼저 8-3 의 K9 차례를 본다.** dev 에서 `apply.sh`(데모 카드 지우기)가 돌았으면 그 지우기가 실린 덤프가 update-all 의 자동 병합이나 이 병합으로 든다.
그러면 K9 의 카드 `…012` 가 목록에서 빠지니 K9 은 **update-all 을 돌리기 전에**(지금 판 화면으로) 본다. 돌았는지는 사용자에게 묻는다(10-31 09시 KST 대조 — dev 에는 아직 돌지 않았다, `apply.log` 없음).

update-all 은 Drive 덤프가 바뀌었을 때만 병합한다. 덤프가 그대로면 `AIDH 덤프 변화 없음 — merge 생략` 이 찍히고 새 병합 코드가 돌지 않는다.
그래서 받은 뒤 한 번 손으로 돈다 — 도는 심의가 없고, 디스크에 운영 직전 스냅샷(몇 GB) 자리가 있을 때. 덤프는 update-all 이 받아 둔 것을 그대로 쓴다 —
`AIDH_MERGE_DUMP` 를 주지 않으면 스크립트가 Drive 최신(약 11 GB)을 임시 자리에 다시 받아 staging DB 에 푼다.

```bash
cd ~/Projects/AIDataHub && AIDH_MERGE_DUMP="$(readlink -f "$(find deploy -maxdepth 3 -name latest.sql.gz | head -1)")" ./deploy/apptainer/merge-from-drive.sh
cd ~/Projects/HWAXPortal && python3 infra/scripts/sync-he-personas.py    # 미리보기(쓰지 않는다) — update-all 은 제 병합 뒤에만 이것을 돈다
```

받아 둔 덤프가 없거나 심링크만 있으면 스크립트가 알아서 Drive 에서 받는다(같은 명령). 레코드 · 전문가 행은 지우지 않는다 — 양쪽에 있으면 updated_at 이 새 쪽이고,
dev 의 소프트 삭제는 옮겨 온다. 표본 임베딩(`agent_sample_embeddings`)만은 전문가 단위로 지우고 덤프 판으로 다시 넣는다(아래 줄의 '지우기만 M'). 운영 직전
스냅샷을 `/data/backups/aidh/pre-merge-<시각>.sql.gz` 에 남긴다. 미리보기에 `+` · `~` 줄이 있으면 병합이 이 박스 판의 운영자(he-*)를 덮은 것이다 — 4절 HP-53 ·
HP-51 줄대로 보고 `--apply` 한다. 병합의 볼 줄 —

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
     옮겨 카드가 목록에서 빠진다(10-27 AD-13 'dev 에서만 지우면'). 1 이 돌았으면 **update-all 을 돌리기 전에**(지금 판 화면으로) 본다 — update-all §3 은 새
     덤프를 스스로 병합하고, 8-1 의 손 병합도 같은 덤프를 쓴다. 그래서 8-1 은 K9 뒤다. 이미 병합됐으면 볼 수 없었다고 적는다.
   - K2 — 로그인이 만료되면 전문가 상세 · 카드 화면이 로그인 화면으로 가고, 상세 실패는 공용 문구와 '다시 시도' 로 보인다.
   - K6-5 — 설명도 역할 문서도 없는 전문가(dynaforge-report)의 상세에 '아직 등록되지 않은 전문가' 가 보인다.
   - K7 — 역할이 빈 전문가가 심의 좌석에 이름 · 키로 앉고 `persona_role_empty` 경고가 난다.
   - 빈 전문가 행은 병합이 지우지 않아 OB-87 까지 남는다 — K6-5 · K7 은 병합 뒤에도 볼 수 있다.
3. **cae00 — 병합.** dev 지우기가 실린 덤프를 update-all(또는 K9 뒤의 8-1)이 병합한다. 0 으로 끝나 표식이 적혔는지 본다 — 3 으로 끝나면 표식이 남지 않아 옛 덤프가
   다시 든다(10-27 AD-13). 손으로 병합했으면 8-1 의 운영자 미리보기도 돈다.
4. **cae00 — OB-87.** 이 박스에서 두 전문가를 지운다(AD-13 순서 5 — 병합은 행을 지우지 않는다). dev 와 같은 길이다 — AIDataHub API 의
   `DELETE /api/agents/<키>`(쓰기 — 사람이 한다). 다음 병합 뒤 다시 들어오지 않았는지 본다(순서 6).

## 9. 아직 오지 않은 것

- **받은 편지함** — 바깥 답이 필요한 물음은 [`../cae00-inbox/`](../cae00-inbox/README.md) 에 날짜별로 든다(판단 C-20). 이번 판에는 `2026-10-31.md`(Q1 ~ Q10 — Q3 은 걷음)가 든다.
  모두 읽기만 하는 물음이고 답은 리포가 아니라 사용자에게 간다.
- **HEAXHub 운영 노드 터널 전환(HEAXHub 10-31 HH-14 ~ HH-16)** — 사용자 결정(10-31) — 추적 매니페스트는 그대로 두고 전환 창에 이 박스만 박스 덮어쓰기
  넷으로 넘긴다. 정본 차례는 HEAXHub `docs/2026-10-31-prod-cutover/cae00-local-overrides/README.md` 다.
  ① 전환 창 **전에** HEAXHub `055b023` 이후 판을 받는다 — 받기 전에 그 리포 `context-notes.md` 「받기 전 점검」의 읽기 스크립트로 첫 reconcile 이 내릴 상태 파일을
  본다(받은 편지함 Q8 ①). ② `var/run/backend.rev` 가 그 판인지 본다. ③ 전환 창에 터널 세 포트(16110 · 16120 · 16121)가 답하는지 본다. ④ 파일 넷을
  `integrations/<폴더>/.portal/` 로 복사한다. ⑤ 45초 안에 라우트가 바뀌고 `heax_app_step_forge` 가 내려간다 — 손으로 먼저 멈추지 않는다. ⑥ 확인 다섯 줄 ·
  `provision.env` 의 `KOORM_BASE`. 되돌리기는 파일 넷을 지우는 것이다. 가지 `cutover/prod-1031` 은 합치지 않는다.
- **DocForge 0.3.1** — 배치(release · HEAXHub 등록 사본 · SIF · Drive)가 그 세션의 사용자 승인을 기다린다. Drive 판이 오면 3절 DocForge 줄과 C-8 고침 셋을 더한다.
- **MaterialTwinWeb — 저장소 비공개 전환(사용자 결정 · 그 리포 `4273720` 의 `docs/운영_저장소_비공개전환_적용_20261031.md`)** — 차례를 지킨다. 비공개 뒤에는 익명으로
  그 문서를 못 읽으니 ① 전에 읽어 둔다.
  ① 공개인 동안 이 박스가 지금 판을 먼저 받는다(update-all — 받기가 막혀도 받은 SIF 로 뜬다). ② 사용자가 GitHub 에서 비공개로 돌린다. ③ 이 박스에 그 저장소 하나만
  읽는 토큰(Contents 읽기 전용 · 만료일)을 허브 비밀 파일에 둔다 — 주소에 박지 않는다. ④ 확인 — 통합 작업 폴더 받기에 `source_unavailable` 이 없다 · 앱 `/api/health` ·
  재료 카드 내보내기가 절 여러 개로 나간다. ①을 건너뛰면 앱은 받은 SIF 로 뜨지만 통합 폴더 받기가 익명으로 막혀 경고가 이어진다.
  그 문서 ①의 확인값은 `upstream commit` `a3563b6` 이다. dev 허브는 10-30 23:04 UTC 에 문서만 더한 `4273720` 판으로 SIF 를 다시 지었다 — 받은 SIF 가 그 판이어도
  코드는 같다. HH-01(긴 재료 카드를 절 여러 개로 — `a3563b6`, cae00 사본 `6e45b40` 보다 61 커밋 앞)이 같은 판에 든다. HH-10(박스마다 다른 id)은 받은 편지함 Q1 이다.
- **SmartTwinMCP PA-16 · PA-19** — 10-31 다시 청했다. 답이 오면 OB-92 · OB-34 · OB-25 의 길을 더한다.
- **HA-33 덧붙임**(SignalForge 주의 줄을 VOC 미리보기에) — 에이전트 `8dd579a` 에 들었다(dev 재기동 10-31 01:06 UTC). cae00 은 에이전트 서버를 받은 뒤 심의 VOC 미리보기에서 '주의 —' 줄이 행이 있어도 보이는지 본다(그 제품 코드가 여러 프로젝트에 걸리는 질문으로).

## 10. 서비스 감시 켜기(사용자 결정 10-31 A28)

cae00 도 서비스 감시를 켠다 — [`../followups-1017/server-setup.md`](../followups-1017/server-setup.md) 9절 그대로다. 포털 · 게이트웨이 · 에이전트 서버 ·
mxwp-mcp · searxng 가 **죽었을 때만**(그 포트에 연결 거부 세 번) 다시 띄우고, update-all 이 도는 동안은 건너뛴다.

```bash
cd ~/Projects/HWAXPortal
echo 'HWAX_WATCHDOG=1' >> infra/.env      # 줄 끝에 주석을 붙이지 않는다 — 다음 update-all 부터는 이 줄을 보고 스스로 건다
./infra/scripts/install-watchdog.sh       # 지금 건다(update-all 을 다시 돌리지 않아도 된다)
crontab -l | grep hwax-watchdog           # 한 줄이 나오면 된다
```

- **손으로 오래 내릴 때는 감시를 먼저 끈다** — `./infra/scripts/install-watchdog.sh --remove`. 끄지 않으면 일부러 내려 둔 서비스를 감시가 몇 분 안에
  다시 띄운다. 다 올린 뒤 `./infra/scripts/install-watchdog.sh` 로 다시 건다(`infra/.env` 의 줄이 남아 있으면 다음 update-all 도 다시 건다).
- 일이 있을 때만 `~/.local/state/hwax/watchdog.log` 에 `✗ <이름> 죽었다 … → down · up` · `✓ … 복구 성공` 이 남는다.
