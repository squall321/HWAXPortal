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
| 게이트웨이 | `63fbc4f`(병합 — B16 ① `c9c3419` · HA-20 `0bef377` 계열) | `KOORM_SEND_PLAT`(KooRemapper 위임에 plat 서명 머리. **KooRemapper 가 머리 두 장을 나르고 검증하는 몫(요청서 [§2](../followups-1017/requests.md) 의 ① · ②)을 올리기 전에는 provision.env 에 적지 않는다 — 빈 자리표시도 적지 않는다**(빈 값은 '끔' 으로 넘어간다 · 그쪽 10-31 답 — 이번에 안 한다). 올린 뒤 `KOORM_SEND_PLAT=1` 을 적고 update-all 하면 §5 가 넘기고, DynaForge 사람별 위임이 있는데 게이트웨이 설정과 다르면 재설치한다 — 포털 10-31 갭 고침부터다. 그 전 포털 판은 §5 가 넘기지 않아 MCP 스모크가 실패할 때 도는 자동 복구만 실었다. 두 머리가 오는 것을 본 뒤 그쪽이 막기(③)를 켠다) · 패널 PAT 검증 · `/tools-map` 의 `panel_read`(HA-20 — 포털 손잡이 `MCP_APPS_HOST` 가 꺼져 있으면 패널은 뜨지 않는다) | 올림 — 게이트웨이 재기동으로 켜진다 |
| WebResearchMCP | `d76911a` · Drive(HEAXHub) `dist-20261031-075456Z` | 호스트별 잠금으로 나감 간격 · 줄 상한 · 한 연결씩 · 서킷 다시 보기(B20 · B21) | 올림 — `dist-from-drive.sh` 로 받는다 |
| LaminateAnalyzerMCP | `113405d` · Drive(HEAXHub) `dist-20261031-081703Z` | 절차 씨앗이 쓰는 도구 넷의 인자 설명 22개(B37 §2-1 — 형 · 기본값 그대로) | 올림(그쪽 세션 · Drive 는 포털 세션) — `dist-from-drive.sh` 로 받는다 |
| 에이전트 서버 | `1159376`(2차 — 백로그 B17 ~ B19 `460d2e0` · HA-20 P1 `1159376`) | 막힘 · 빈 웹 결과는 근거로 세지 않는다([가설 단계]가 바르게 붙는다) · 이어하기 좌석 프롬프트 · 1라운드 조회 턴도 이전 결론을 가린다 · 챗 MCP Apps 패널의 SSE `ui_resource`(포털 손잡이가 꺼져 있으면 묶이지 않는다 — HA-05 그대로) | 올림 — 에이전트 서버 재기동 |
| 포털 | `a694e19c`(2차 — B1 · A25 · B3 · B8 ~ B15 · HA-20 P2 ~ P4) · `fb640a3a` · Drive `images-20261031-083656Z` | update-all 의 심의 기다림 하나가 에이전트 서버 · 게이트웨이 · SignalForge 재기동을 덮는다(A25 — 받은 뒤 다음 update-all 부터) · drive-drift 가 짓지 않은 앱을 짚는다 · 절차 게시 미리보기 게이트 · 전문가 색을 키 하나로 · 패널 창구(손잡이 `MCP_APPS_HOST` 기본 꺼짐 — 끄면 404) · index.html `frame-src 'self'` | 올림 — 화면은 Drive 판. A25 동작은 [`../delib-ops/server-setup.md`](../delib-ops/server-setup.md) · [`../cae00-deploy-guide.md`](../cae00-deploy-guide.md) 에 적었다 |
| 리스크 앱(HWAXRisk) | `be8d974`(웹 심의 멈춤 A24 몫) · Drive(HEAXHub) `dist-20261031-083405Z` | 엔진이 사람이 멈춘 패널 심의를 알리면 결정문 없는 done 이 아니라 패널을 닫고(error) 잡을 멈춘다 — 에이전트 서버 a24 와 같이 또는 먼저 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk` |
| 에이전트 서버 | `c6aad34`(3차 — 웹 심의 멈춤 A24 (나)) | 끊긴 웹 심의를 대화 id 로 멈추는 엔진 창구(포털 중계 경유) · 결정문이 나온 뒤(마무리 중)에는 409 finishing · 멈춘 실행은 cancelled 로 남는다 | 올림 — 에이전트 서버 재기동. 리스크 앱 `be8d974` 와 같이 또는 먼저 받는다 |
| 포털 | `e8b01282`(3차 — A24) · `52ccb245` · Drive `images-20261031-085839Z` | 멈춤 창구(세션 + CSRF · 그 대화의 주인만) · 심의 화면 '멈춤' 버튼 · 멈춤 기록이 대화에 남는다 · 낡은 화면이 새 심의를 멈추지 않는다 | 올림 — 화면은 Drive 판 |
| AIDataHub | `048ff6a` | 병합 끝 요약에 '운영이 더 새롭다며 건너뛴 행 중 내용이 다른 수(그중 조회로 올라간 수)' 한 줄(셈만 — 병합 판단은 그대로) · 한국어 검색 재정렬기 견주기 기록(이 박스는 GPU 가 없어 끈 채 둔다) | 올림 — update-all 이 받는다. 조회가 updated_at 을 올리지 않게 하는 고침은 다음 판 — 아래 `fccb0e5` 줄(사용자 결정 10-31) |
| 리스크 앱(HWAXRisk) | `7b1042d`(백로그 B22 ~ B32 · A18 + RK-01 보내기 · 거두기) · Drive(HEAXHub) `dist-20261031-091813Z` | 원천 겹침 알림 · 대상 감사 · 근거 빼기와 사람 개입 요약 · 분류 어휘 검사 · 요구 여유 · rekey · 큰 배정 건너뜀 · 잘린 계면 제외 · 지식 그래프를 서비스 계정으로 RA 에 보내기(비공개는 보류 · 비공개 · 폐기 · 주인 변경에 거두기) | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`. RA 보내기 확인은 리스크 앱 checklist 2장 'RK-01 cae00 확인'(쓰기 PAT 주인이 RA 시스템 관리자인가 · 온톨로지 부트스트랩) |
| 리스크 앱(HWAXRisk) 화면 | `dbe5f93`(A32 화면 세션) · Drive(HEAXHub) `dist-20261031-094206Z` | 웹 '과제 만들기' 가 늘 422 이던 결함(B33 — 등급 칸) · 사람 자격 화면(포털 PAT 자동 등록 · 끄기, B35) · 패널 잡의 Claude 판단 선택(동의 칸은 미리 체크하지 않는다, B36) · ECAD 보드 화면 · 과제 · 대상 · 홈 화면 몫(B34) · M3 화면 일곱 절 · 대상 · 과제 화면이 비던 타입 결함 | 올림 — 위 리스크 앱 줄과 같은 길로 받는다. 화면이 '모름' 으로 비우는 칸은 백엔드 후속(진행 중)이 채운다 |
| KooRemapper(DynaForge) | `3929a4e` | 인자 설명 36(B37 ①) · MCP → REST 한도 손잡이 `KOORM_MCP_API_TIMEOUT_S`(기본 540 — 게이트웨이 600 안쪽) · 도구 호출마다 벽시계 기한 · 시간 넘긴 잡 요약에 `KOORM_JOB_TIMEOUT_SEC`(B38 ②). plat 서명 헤더로 막기(③)는 그쪽 사용자 결정으로 이번에 안 함 | 올림(그쪽 세션) — 파이썬만 바뀌어 update-all 재기동으로 MCP 도 새로 뜬다 |
| 게이트웨이 | `5f4ba5f`(병합 — `9b37b31` ~ `10bb6ec`) | 10-29 4차 E-2 · E-4 — 앱 역할로 검색 순위 · 접기 · 노출(허브 가족은 늘 접두 · 옛 맨 이름은 호출 별칭) · 개인 Claude 보기 셋(전체 · 묶음 · 가벼운) | 올림 — 게이트웨이 재기동으로 켜진다. 받은 뒤 확인은 [`../request-1029/server-setup.md`](../request-1029/server-setup.md) 8절 · 받은 편지함 Q14 |
| 포털 | `d31bca1` · `4034845` · Drive `images-20261031-055500Z` | 같은 묶음의 포털 몫 — 사람 설정 `users.hub_view` · 토큰 화면 보기 고르기 · 등록 배치 머리 `X-HWAX-View: portal` · Q-2 확인(목록은 늘 접두, 사용자 10-31) | 올림 — 화면은 Drive 판. 확인은 위와 같다 |
| StepForge | `4253453` · Drive(HEAXHub) `dist-20261031-101810Z` | 인자 설명(B37 §2-2) — find_parts 11 · stackup_profile 6 · bend_profile 3, 그리고 접는 도구 78 이 함께 받는 `full` 한 자리(dev `/tools-map` described 0 → 98 / 827) · 측정 잡 접수가 `Annotated` 형을 글로 읽어 bool 인자의 "yes" 를 받던 이음매 고침(형 · 기본값 · 필수 · 차례는 그대로) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 교체 |
| AIDataHub | `fccb0e5`(`3dc1bb5` 포함) | 조회는 read_count · last_accessed_at 만 올리고 updated_at 은 그대로(사용자 결정 10-31) · 병합이 이미 있는 행을 dev 판으로 덮어도 이 박스의 read_count · last_accessed_at 은 지킨다(새 행만 dev 값 — 반대 검토 고침) · 병합 끝 요약의 조회 몫은 updated_at 과 last_accessed_at 이 서로 1초 안일 때만 센다 | 올림 — update-all 이 받는다(API 재기동 · 이관 없음 — 이관 0032 트리거에 기댄다). 예전 조회로 올라간 행은 그대로 남아 계속 센다. dev 는 10-31 10:21 UTC 재기동 |
| 에이전트 서버 | `82e3729`(병합 — B17 `f3a714f` · `458eced` · `81589ae`) | 이어하기 좌석 재심사가 사람 의견(없으면 원 질문)에서 짓는 짧은 축으로 묻는다 — 축마다 추천 40명 · 넓은 접두(sw · xd)는 둘째 마디까지를 앉은 도메인으로 · 축은 하나씩 묻다 자리가 차면 멈춤 · 기한 `DELIB_RESCREEN_TIMEOUT_S` 600초. 끊긴 잡 잇기는 재심사를 걸지 않고, 첫 실행(이전 결론 없음)은 예전 한 덩이 그대로(사용자 결정 10-31). 포털 정본 파이프라인 `hwax-deliberate.js` 의 좌석 계약 주석도 같은 뜻으로 고쳤다 | 올림 — 에이전트 서버 재기동(dev 10-31 10:37 UTC) · 포털 쪽은 update-all 의 sync 가 받는다. 받아들임은 4절 B17 줄 |
| 리스크 앱(HWAXRisk) | `b71a262`(병합 — 사람 조작 감사 `e21ca9a` · `bcff65e` · `69e18d6` · `6f345d0`) · Drive(HEAXHub) `dist-20261031-112337Z` | 잡 멈춤 · 재개 · 취소 · 등록부 status · verdict 확정이 감사 행을 남긴다(바뀜과 같은 트랜잭션 · 코드 어휘만, 사용자 결정 10-31 '남긴다 — 계획서대로') · 포털 화면 '멈춤'(A24)으로 멈춘 패널 잡도 job.pause 한 행 — 대상 감사와 보고서 '사람 개입 요약' 에 선다 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 10-31 11:23 UTC). 이력 탭의 새 이름표는 다음 판(가지 `wt1031/risk-gaps`) |
| 리스크 앱(HWAXRisk) | `4145b2c`(감사 틈 셋 — `4eea6b6` · `c232e55` · `29a3bc3` · `77e5480`) · Drive(HEAXHub) `dist-20261031-121154Z` | MCP 도구가 남기는 감사 행은 입구 mcp · 검증되지 않은 행위자로(종전엔 job.create · gate.ack · finding.create 등이 검증됨으로 적혔다) · MCP 잡 제어의 changed 가 감사 행과 같은 판정(코드 보류 잡을 사람이 멈춰도 바뀜으로) · 대상 감사 이력 탭에 새 감사 다섯의 이름표와 앞 → 뒤 글 표시 — 사용자 결정 10-31 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 10-31 12:11 UTC). 웹 쪽 행의 입구는 이제 rest 대신 web 으로 적힌다(채널로 거르는 곳은 없다) |
| 에이전트 서버 | `27f0229`(병합 — HA-09 S1 ~ S4 · 반대 검토 고침 `d66d7d9`) | 재기동으로 끊긴 심의를 같은 잡에서 제자리로 잇는다 — 끝난 라운드는 되살리고 끊긴 라운드는 남은 좌석만 · 결정문 · 보고서 · 위키는 한 번만 · 다단 · 시험 설계는 끊긴 단 안에서(사용자 결정 10-31 권장안). 주인이 값을 바꾸거나 남이 이으면 까닭과 함께 요약 길 | 올림 — 에이전트 서버 재기동(dev 10-31 12:56 UTC). `/health` 에 `delib_journal{on, max_mb, errors}` · `delib_folded`. 확인은 4절 HA-09 줄 |
| 리스크 앱(HWAXRisk) | `3a188f3`(병합 — 화면 읽기 `2beb7e2` · 흐름 `cee55fd` · 이력 탭 이름표 `f32e0fb`) · Drive(HEAXHub) `dist-20261031-125835Z` | 과제 상세 · 목록을 구성원이 연다 · 들여오기가 남의 과제에 줄을 매달지 못한다(High — 남의 부모 · 남의 owner 멤버 행은 그 줄만 거절) · 키 대장 읽기(mine) · 게이트 ack 를 지금 값으로 · sameas pair_key · 잡 signals · 병합된 키 확정 409 · 쟁점 outcome · 마감 갱신 · 요구 여유 · 잡 차례 · 보류 코드 · 동의 문구 · 등록 실패 기록(길마다 쉼) · 감사 이력 탭의 모든 행위 이름표 · '미확인' 풍선 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 10-31 12:58 UTC). 받은 뒤 4절 리스크 줄의 셈 둘 |
| 포털 | `bfa80d1d`(병합 — 절차 · update-all 틈 `42960126` 까지 · 심의 화면 틈 `b9654976` 까지) · Drive `images-20261031-132245Z` | 챗 턴을 절차로 기록해도 RA 게시 확인 토큰이 원장에 남지 않는다 · 중단한 실행은 중단 그대로 · 끝난 실행은 중단으로 덮지 않는다(409) · update-all §5 가 `KOORM_SEND_PLAT` 을 넘기고 어긋나면 다시 등록한다(DynaForge 위임이 있을 때만 — 박스에 적는 것은 KooRemapper 막기 뒤, 위 KooRemapper 줄) · 심의 페이지에서 고른 시뮬 · 시험 · 구축 계획이 일반 심의로 돌던 결함 · 다단 심의를 앞 단 결정 뒤에도 멈춘다 · 끊김 상자 · 다른 화면에서 멈춘 것 · VOC 머리만 받고 끊긴 심의 — 사용자 결정 10-31 | 올림 — 화면은 Drive 판, 백엔드 · update-all 은 git(dev 포털 10-31 13:22 UTC 재기동) |
| 에이전트 서버 | `fdfd7dd`(`57ccf1f` · `2fc01f1` · `b541787` · `4025a6e`) | 결정문이 나온 뒤(마무리 중)의 MCP `deliberate_cancel` 은 거절하고 끝까지 돈다(웹 409 와 같은 뜻) · /시뮬심의 · 구축 계획 스트림은 끝 신호(done)를 한 번만 · 끊긴 심의를 되살릴 때 조회 · 결정 단계 알림을 한 번만(일지 `e:round_in` · `e:note`) · RA 게시 확인 토큰을 확인 카드 글 · 심의 근거 · `/보고서` 에서 가린다(사용자 결정 10-31) | 올림 — 에이전트 서버 재기동(dev 10-31 20:55 UTC) |
| 포털 | `1fa76c8f` | 위키로 보내는 대화 근거 발췌에서 RA 게시 확인 토큰을 가린다(대화 저장소 원본은 다음 턴 게시가 읽어 그대로 — 사용자 결정 10-31) | 올림 — 백엔드만(git) · 포털 재기동(dev 10-31 20:55 UTC) |
| KooRemapper(DynaForge) | `57a41bf` · Drive `dist-20261031-214338Z` | 해석 온톨로지(사용자 결정 10-31 (가) — 후처리 꾸러미를 리포트에, `0e9c9da` · `220df28` · `4ada7ba`) · 이관 0020(null 허용 칸 셋) · MCP 89(`report_cae` · `find_cae_parts` 등 넷 더함) — 인자 설명 · 시간 한도(`3929a4e`)도 이 판에 든다 | 올림(그쪽 세션) — update-all 이 Drive 판을 받는다. 확인은 `../cae00-deploy-guide.md` 「2026-10-30 반영분 — 낙하 트윈」 1 · 1-2 |
| 리스크 앱(HWAXRisk) | `2460cd0`(병합 — 구성원 · 쓰기 `224b04e` 까지 · 동시 실행 `33c0d85` 까지) · Drive(HEAXHub) `dist-20261031-234240Z` | 구성원(편집자 · 보기)이 과제가 보이는 것 전부를 읽는다 · 편집자는 계획서대로 쓴다(주인 전용 — 멤버 · 이양 · 폐기 · 공개 범위 등은 그대로) · 같은 짝 확정 · 거절은 짝의 두 과제 편집자 이상만, 주인 원장으로 지킨다(남의 행을 뒤집던 구멍 High) · 들여오기는 제 과제가 참조하는 부품 키만(선점 막기) · 두 과제를 모두 넘겨받으면 비교도 옮긴다 · 남이 과제에 매단 대상 · 줄은 열리지 않는다 · 잡의 동시 실행(1 ~ 2)이 실제로 돈다(같은 잡의 패널 둘까지, Claude · 쟁점 잡은 1) — 사용자 결정 10-31 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 11-01 KST 08:42). **받기 전에** 4절 리스크 줄 둘(셈 · 동시 2 로 저장된 잡) |
| 에이전트 서버 | `63ad54b`(`7eb1258` · `3590e6d`) | MCP `deliberate_status` · `deliberate_list` 행에 `finishing`(접기가 거절되는 동안만 true — 결정문 · 보고서까지 끝난다) · 루틴의 심의 접기가 마무리 중으로 거절되면 생각 칸에 그 까닭(다른 실패는 종전 안내) · 진행 조회의 `quiet_ok_s` 가 셀 수 없이 큰 한도에서 넘어지지 않고 null · 시험 순서 격리(동작 그대로) — 사용자 승인 11-01 | 올림 — 에이전트 서버 재기동(dev 11-01 05:22 UTC) |
| 리스크 앱(HWAXRisk) | `45aba34`(병합 — 남은 일 다섯 `557fa37` ~ `62970cd`) · `bcfa535`(문서) · Drive(HEAXHub) `dist-20261101-073047Z` | 비교 본문 계약을 실제 생산자에 맞춤(pair_kind 필수 · 의미층 차단 capture_partial · 제외 사유 13 · 사건 주체 열쇠 code 마다 — 본문은 그대로) · 과제 · 대상 · 비교 · 스냅샷 화면이 서버가 준 역할로 쓰기 단추를 잠그고 까닭을 보인다 · MCP 다음 걸음 안내(risk_next_step)를 구성원에게 · MCP 가 살아 있는 패널 잡을 돌려줄 때 그 잡의 concurrency 와 differs · 관리자는 계획서대로 전 과제를 편집자처럼 읽는다(목록 · MCP 는 그대로) — 사용자 결정 11-01. 이관 · 새 설정 없음 | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 11-01 KST 16:07) |
| 포털 | `d56d7434`(병합 — 절차 · 루틴 열린 틈 `0fd6c16d` ~ `b0d8b032`) · Drive `images-20261101-082333Z` | 절차의 상태 쓰기가 중단을 덮지 않는다 · 같은 실행에 실행기 둘을 막는다(승인 · 재개 · 고르기 · 즉석 단계 — 늦은 요청은 409 '이미 진행 중인 실행입니다', 화면은 도는 동안 단추를 잠근다) · 승인은 한 번 쓴다(보내기 직전에 쓴 것으로 적는다 — 결과를 모르는 단계의 재개 · 끝난 실행의 다시 고르기는 확인 카드가 다시 묻는다) · 루틴 멈춤이 마무리 중인 심의에 접으라고 하지 않는다 — 사용자 결정 11-01. 절차 원장의 새 칸 `run_gate_acks.used_at` 은 포털 기동 때 저절로 더해진다(이미 있던 승인은 안 쓴 것으로). 펼치기 두 번 보내기는 열린 항목(`docs/procedures/checklist.md` S5) | 올림 — 화면은 Drive 판, 백엔드는 git(dev 포털 11-01 08:23 UTC 재기동) |
| HEAXHub | `385783f` | WebDesignAgents 를 포털 로그인 뒤에만 연다(`integrations/web-design-agents/.portal/manifest.yaml` 의 `launch.portal_auth: true` — dev 실측 11-01, 익명 요청에 run 목록 · 웹 화면 · /mcp 가 200 이던 것, 사용자 결정 11-01). 라우트 · SIF 는 그대로라 재빌드 · Drive 없음 — 허브의 다음 훑기(5분 안)에 켜진다 | 올림 — update-all §2 가 받는다. **update-all 앱 점검에 `web_design_agents → 401(로그인 필요 — 정상 정책)` 이 서는 것이 정상**이다. 게이트웨이의 WDA 도구 수는 그대로(dev 16). 로그인 없이 북마크 · 스크립트로 쓰던 사람은 401 을 받는다. WDA 커밋이 GitHub 에 올라가면 dev 가 이 매니페스트로 SIF 를 다시 지어 Drive 에 같이 올린다(`docs/wda-deck/`) |
| 리스크 앱(HWAXRisk) | `a8aaafc`(병합 — 관리자 접근 감사 `2d7aae2` ~ `5b349da`) · `d30bef6`(문서) · Drive(HEAXHub) `dist-20261101-095354Z` | 관리자가 구성원이 아닌 과제를 관리자 권한으로만 열거나 고치면 (관리자, 과제, 한국 날)마다 `admin.read` · `admin.write` 한 줄이 과제 이력에 남고, 그 쓰기의 감사 줄에는 `via: admin`(이력 탭 '관리자 권한' 표지) — 대상 감사 · '사람 개입 요약' · RA 회의록 · 반출에는 들지 않는다. 관리자 목록 · MCP 는 그대로. 스키마 변경 없음(사용자 결정 11-01 — 계획서 §5.2.1 대로) | 올림 — `dist-from-drive.sh` 로 받고 `redeploy-app.sh hwax-risk`(dev 11-01 KST 18:53) |
| HEAXHub | `e4d56c4` · `d81d7b5` | 매니페스트 칸 `launch.forward_authorization`(기본 true — 종전대로) — false 면 허브 게이트가 토큰을 쓴 뒤 앱으로 가는 요청에서 `Authorization` 을 지운다(신원은 검증된 `X-Heax-User-*` 로). WebDesignAgents 에 켰다 — 포털이 찍는 그 사람의 `heax-hub` 토큰(모든 허브 앱에 통한다)이 WDA 에 닿지 않는다(사용자 결정 11-01). 다른 앱의 라우트는 바이트까지 같다 · 재빌드 · Drive 없음 | 올림 — update-all 이 HEAXHub 가 바뀌면 허브 스택을 다시 띄워 켜진다(심의가 돌아 'heax 재기동 건너뜀' 이면 다음 실행까지 옛 동작). 확인 `curl -s localhost:2019/id/app-web_design_agents` 의 마지막 처리기에 `"delete":["Authorization"]` · WDA 도구 수 그대로(dev 16). `var/logs/worker.log` 에 'Caddy admin unreachable … forward_authorization' 이 서면 옛 코드의 일꾼이라 허브 일꾼을 다시 띄운다 |
| 에이전트 서버 | `9f08507`(병합 — `291bbb9` · `d010346` · `d590d0b`) | '/보고서' 저장 결과에 `ra_report {id, title}` · 이어하기의 보고서 덧붙이기가 도구 밖 예외로 실패해도 결정문에 보이는 글 · 심의 outcome 과 재개 일지에 RA 가 준 보고서 주소(`/w/<공간>/reports/<번호>` — 꼴 · 번호가 맞을 때만) — 포털 '발표자료로'(docs/wda-deck) | 올림 — 에이전트 서버 재기동(dev 11-01 14:39 UTC) |
| 포털 | `e24f510f`(병합 — 발표자료로 M1 · 적대 검토 세 차례 WD-D44 ~ WD-D80) · Drive `images-20261101-144037Z` | **'발표자료로' 는 꺼진 채 들어간다** — 박스 스위치 `WDA_DECK_ENABLED`(기본 꺼짐)와 WDA 의 주인 기능(`/api/health` features `owner`)이 둘 다 서야 단추가 보인다(WDA 새 판은 사용자 push 뒤). 켜지 않아도 닿는 것 — 새로고침한 심의의 결과 카드 · 챗 글의 포털 경로 링크([이름](/…)) · 심의 카드가 RA 가 준 보고서 주소(그 보고서의 공간)로 바로 연다 · 답이 끝난 직후 브라우저가 떠나도 답을 저장한다(원래 결함 — 사용자 결정) · 중계가 대화별 턴을 센다 | 올림 — 화면은 Drive 판, 백엔드는 git(dev 포털 11-01 14:40 UTC 재기동). 켜는 법 · 실주행은 `docs/wda-deck/server-setup.md` |
| 포털 | `b71bffd4`(병합 — 3차 적대 검토의 낮음 넷 `2a3a7ea6` ~ `dc71db24`) · Drive `images-20261101-154211Z` | 켜지 않아도 닿는 중계 · 카드 고침 — 답을 끝맺는 저장을 기다리는 데 상한 120초(넘으면 응답을 닫고 저장은 뒤에서 끝까지) · 남의 대화는 주인부터 보고 도는 턴으로 세지 않는다 · 루틴 상한 로그는 실제로 끊을 때만 · 팝업이 막혀도 옛 심의 카드는 링크대로 RA 를 연다(WD-D81 ~ WD-D84) | 올림 — 화면은 Drive 판, 백엔드는 git(dev 포털 11-01 15:41 UTC 재기동) |
| 포털 | `6327d0fb` | 워크플로 다섯(hwax-deliberate · sim-deliberate · test-plan · risk-review · risk-claude)의 설명 첫머리에 '기본 길은 서버 엔진(deliberate_start · 리스크 잡 llm=glm · 리스크 앱 러너) — 이 워크플로는 Claude 로 품질을 따로 잴 때만'(사용자 결정 11-02, `docs/token-saving` TS-5) | 올림 — update-all 의 sync 가 받는다 |
| 포털 | `9085958d`(병합 — 이용 통계 M1) · Drive `images-20261101-230046Z` | 관리자 `/admin/usage` · `GET /auth/admin/usage?days`(1 ~ 400) — 포털 안 원장을 읽기 전용으로: 로그인 · DAU/WAU/MAU(로그인 기준) · 타일 진입 · 챗 · 사건 · 대화 · 절차/루틴 · 계정(소속 5명 미만은 '기타') · PAT · 권한 요청, KST 날 · 자동 예열 줄은 늘 뺀다 · `agent_audit` ts 색인(기동 때 저절로) · 합계도 관리자만(사용자 결정 11-02, `docs/ops-dashboard` OD-4 · OD-5 ~ OD-12) | 올림 — 화면은 Drive 판. 시험 · 서비스 계정을 빼려면 `backend/.env` 에 `USAGE_EXCLUDE_ACCOUNTS=<메일,…>`(박스 파일 — 추적 안 됨) |
| 포털 | `655dc635`(병합 — LLM · GPU 현황 M1 · M2) · `8bbaef62`(이력) · Drive `images-20261102-031105Z` | 관리자 `/admin/llm-status` · `GET /auth/admin/llm-status` · `/series` — 호스트 수집기 `infra/llm-status`(시스템 python3 · 루프백 8760 · **기본 꺼짐**, `infra/.env` 의 `LLM_STATUS` 한 줄로 수집기와 화면이 함께 켜진다 · update-all 5d · 켠 박스만 감시) · 서버별 주소는 `LLM_STATUS_TARGETS` 에 `#glm` · `#chat` 키 표지 · 묶음 주소는 그때 답한 한 대의 숫자(속도 · 지연은 같은 서버 프로세스끼리) · 반대 검토 반영(`docs/ops-dashboard` OD-13 ~ OD-40) | 올림 — 받기만 하면 아무것도 바뀌지 않는다(5d 의 ○ 한 줄 · 화면은 '수집기가 꺼져 있다'). 켜기 전에 8760 을 듣는 것이 없는지 보고(`docs/ops-dashboard/server-setup.md` 2절), 서버별 주소는 받은 편지함 2026-11-02 Q4 · Q5 답 뒤 |
| 에이전트 서버 | `c658f85`(병합 — `00e419f` · `beb73d8` · `639f2b8` · `23fda6b`) | 리스크 심사 D-18 새는 길 막기(사용자 결정 11-02 — `docs/risk-review-redesign/context-notes.md` D-58) — 지정 도구는 리스크 앱의 변경 · 스냅숏만(다른 리스크 앱 도구 · RA 보고서 읽기 · 범용 실행기 · 심의 잡 기록 읽기 거절) · RA 온톨로지 읽기에서 같은 과제의 risk_finding 빼기(**RK-01 을 켜기 전에 이 판이어야 한다**) · 포털 대화 검색의 앞 패널 대화 · 과제를 읽을 수 없는 쟁점 패널 초안 빼기 · 과제를 모르면 전부 · 비리스크 잡은 그대로 | 올림 — 에이전트 서버 재기동으로 켜진다(update-all 이 도는 심의를 기다린다). 리스크 심사 좌석 기록에 '지정 도구 거절 · 가림' 줄이 새로 보일 수 있다 |
| 포털 | `adde594c`(병합 — 워크플로 · D-58) · `29c5d943`(이력) | `hwax-deliberate.js` 의 리스크 심사 좌석(`hwax-risk-review` 패널 좌석 포함)에 D-18 한 줄 · 보고서 조회 안내 빼기 — 지시일 뿐 강제는 엔진 길 | 올림 — update-all 의 워크플로 동기화로 켜진다(SIF · Drive 없음) |
| 에이전트 서버 | `0e63a65`(병합 — 과제 인사이트 그래프 M1) | 심의 주제 — `deliberate_start` · `deliberate_continue` · `deliberate_list` 의 `subject`(과제 · 차수 · 설계 자료) · 잡 원장 · 목록 색인 칸 · 과제 key 는 서버가 StepForge `find_plm_task`(게이트웨이 호출 전용 별칭 `heaxstep_forge_find_plm_task`)로 심의의 제 자격으로 확인해 같은 key 의 살아 있는 행이 꼭 하나일 때만 confirmed · 웹 주제는 엔진 앞에서 다시 확인해 사건으로만(결정문 · RA 에 안 간다 · 새 LLM 호출 0) — `docs/project-insight-graph` PG-19 ~ PG-27 | 올림 — 에이전트 서버 재기동으로 켜진다. 확인 — 실제 과제 하나로 심의 시작의 주제가 '확인됨' 인지 · 게이트웨이 `tools/list`(호출 전용 별칭은 목록에 없어도 부른다 — 받은 편지함 Q19) · `stepforge-prod` 권한만 가진 사람은 '확인 안 됨'(Q19 답 뒤) |
| 포털 | `ea233cc8`(병합 — M1 주제 고르기) · `1d569fd8`(이력) · Drive `images-20261102-064102Z` | 심의 시작 · 챗→심의 브리프의 주제 칸(후보는 그 사람의 그 대화 도구 결과에서만 · 고를 때 다시 확인) · `DelibOpts.subject` · 답의 `meta.subject`(중계만 적는다 — 대화 REST 로 들어온 것은 버린다) · `POST /agent/deliberate/subject/search` | 올림 — 화면은 Drive 판 · 포털 재기동. 과제 대상이 아닌 질문은 주제를 비워 두면 어디에도 잇지 않는다 |
| 에이전트 서버 · 게이트웨이 · 포털 · 리스크 앱 | 에이전트 `e13e3e3b` · 게이트웨이 `5798ae53` · 포털 `c33c511a`(Drive `images-20261102-141703Z`) · 리스크 앱 `842a691c`(Drive `dist-20261102-142142Z`) — 과제 인사이트 그래프 M2 · M2b | 단마다 결정 카드(주제를 단 일반 심의만 · 새 LLM 호출 0) · 포털 인사이트 원장(procedures.sqlite 안 표 셋) · 들이기 셋(웹 중계 · MCP 잡 당기기 · Claude 워크플로 저장) · 읽을 때 거르는 API · `/insights` 화면 · 게이트웨이 `insight_find` · `insight_get` · 리스크 앱 스키마 v6(`rr_projects.sp_task` — 기동 때 백업 뒤 이관) · `risk_set_project_subject` · `risk_find_projects_by_subject` · D-18 거절에 insight_* | 올림 — 네 서비스 재기동(리스크 앱은 허브가 새 SIF 로). 확인 — 포털 `GATEWAY_SHARED_TOKEN` 이 에이전트 서버의 게이트웨이 비밀(GW_TOKEN)과 같아야 MCP 잡 카드를 당긴다(좌석 질문 수확과 같은 값) · 권한 `feat:insights` 는 CAEG(`"*"`)에 열린다 — 좁히려면 `access.local.yaml` · 실제 과제 하나로 웹 · MCP 잡 · 워크플로 카드 하나씩 · 리스크 과제 하나에 주제를 달아 과제 보기에서 |
| 게이트웨이 · 에이전트 서버 · 포털 | 게이트웨이 `844f91af` · 에이전트 `6a4c6b42` · 포털 `9468bef4`(화면 변화 없음 — Drive 없음) — **긴급 11-02 그림이 보고서로** | 도구 결과의 그림을 게이트웨이가 주인별로 보관(`GATEWAY_FIG_STORE` 기본 켜짐 · 감사 원장 옆 `figures/` · 7일 · 주인 1 GiB · 전체 20 GiB) · 결과에 '그림 저장 — fig_…' 표지 · `GET /mcp-gw/fig/<ref>`(주인 PAT 또는 1시간 서명 주소) · `figure_get` · `figure_list` · `figure_to_report`(포털 `POST /agent/figures/to-report` — 그 사람의 RA 토큰) · 웹 챗 `/보고서` · 심의 RA 보고서가 그림을 RA 그림 블록으로 · 도구 그림 프록시에 sandbox · nosniff — `docs/report-figures` | 올림 — 세 서비스 재기동(nginx 바꿀 것 없음). 확인 — 개인 Claude 로 StepForge 그림 도구 한 번 → 표지 · `figure_get` 의 curl 로 PC 에 파일 · `figure_to_report` 로 RA 보고서 하나에 그림 블록 · 웹 챗 `/보고서` 에 그림 · `figures/` 디스크 사용량. dev 확인 11-02 — render_3d 표지 · 서명 주소 받기(nginx 경유 200 · 틀린 서명 404) |
| 게이트웨이 · 포털 | 게이트웨이 `fe5e14c0` · 포털 `58e6e680`(화면 변화 없음 — Drive 없음) — 표 칸 그림 docx 변환기 | PC 변환기 `infra/pc-kit/hwax-md2docx.py`(문단 · 목록 · 표 칸 그림 · `fig_` 참조 · 없으면 exit 2 · 수 대조 exit 3) · 게이트웨이 `kit_get` · `GET /mcp-gw/kit/<name>`(1시간 서명 주소 또는 PAT — 파일은 포털 리포 `infra/pc-kit` 에서 읽는다) | 올림 — update-all 뒤 게이트웨이 재기동. **바뀌는 것** — 검색 덧씌우기(`search_tuning.local.json`)의 띄어쓰기 든 동의어 열쇠(예 '메인 PBA')가 이제 먹어 그 검색 순위가 바뀐다(전에는 말없이 무시) — 덧씌우기를 둔 박스는 `/search-eval` 로 한 번 본다. dev 확인 11-02 — StepForge 그림 둘 → 서명 주소 받기 → kit 으로 변환기 받기(리포 파일과 같음) → 표 칸 그림 md → `그림 표기 3 · docx 그림 3 · 표 칸 안 2` |
| 게이트웨이 | `6e005a87` — MX 백서 문서에 그림 `figure_to_doc` | 보관한 그림을 그 사람의 위임 토큰으로 MX 백서 `upload_image_bytes` → `insert_image_block`(MX 백서 `9842648` 필요) · MX 백서의 401 꼴도 토큰 거절로(새 토큰으로 한 번만 다시) | 올림 — update-all 뒤 게이트웨이 · mxwp-mcp 재기동. 확인 — 박스 게이트웨이 설정에 `PER_USER_SSO_APPS` 의 `mx-white-paper:MXWP` 가 있어야 한다(없으면 서비스 계정으로 쓰지 않으려고 거절한다) · 넣는 사람은 MX 백서 편집자 · 실제 문서 하나에 그림 블록. dev 확인 11-02 — 시험 문서에 그림 블록 · 다시 넣기 deduped |
| DynaForge(KooRemapper) | `a7904f7` · `84715c6`(KooRemapper 세션) — **운영 Drive 는 사용자가 그 세션(kooremapper-fd)에 직접 '진행' 뒤** | 메시 그림 도구(`mesh_section_figure` · `mesh_surface_figure` · `mesh_stack_diagram`)가 SVG 를 PNG 로 그려 그림 블록을 덧붙인다(`figure_png` · 256 KB 넘으면 단계적으로 줄임 · 실패는 `figure_png_error` 짧은 까닭) · `report_image` · `report_compare` 에 출처 줄(report · case · file_id · sha256) — 새 mcp.sif(librsvg · 나눔 글꼴 · pillow) | dev 반영(그쪽 점검 그림 26/26 · 리포트 56/56). cae00 — Drive 뒤 `dist-from-drive.sh` → `apptainer instance stop koorm_mcp && infra/scripts/start.sh`. 확인 — 실제 사람으로 메시 그림 하나를 게이트웨이로 불러 그림 블록 · '그림 저장 — fig_…' 표지 · `figure_to_report` 로 RA 에 |
| MX 백서 | `9842648` · `f6fe556`(MX 백서 세션) | 게이트웨이 `figure_to_doc` 이 쓸 서버용 `upload_image_bytes`(http 전용 · png/jpeg/gif/webp · SVG 거절 · 20 MB · 편집자 · 쓰기 범위) | git 으로 받는다(Drive 없음). cae00 — update-all 뒤 mxwp-mcp 재기동(그 프로세스가 server.py 를 기동 때 한 번 읽는다). dev 는 11-02 21:23 UTC 재기동 · 게이트웨이 목록에 보임 |
| ste(SmartTwinExplorer) | `1b9e1bbb1cba` · Drive `SmartTwinExplorer/staging`(11-02 — ste 세션, 처음 올린 `b059413b7ece` 뒤 문서 커밋 하나로 다시 올림 · 코드는 같다) | Drive 의 ste 스테이징이 옛 판(`4f5e0e0`)이던 것을 dev HEAD 로 다시 올림(차이는 문서 한 줄 — 코드는 PA-20 그대로, 백엔드 시험 173 · 에이전트 go test 통과) | 올림 — update-all 뒤 확인: ste 헤드의 `/opt/ste/.deployed-commit` 이 `1b9e1bbb1cba` 인지 · 로그에 `옛 DB 를 이어받았다`(계정 유지) · PA-20 — `GET /api/cluster` 의 controller 가 호스트 이름만이고 MCP `cluster_info` · `list_jobs` · `get_job_status` 출력에 사설 주소 · 메일이 없는지(DW-12 재시험) · 에이전트 exe 새 빌드(1b9e1bb.20261102) · 업로드 상한 기본 10GB(`STE_MAX_UPLOAD_MB`) — stcx 앞단 nginx 조각도 10240m |
| 에이전트 서버 | `aadd591`(병합 — `42b2acf` ~ `5426e0a`) | `deliberate_status(wait_s, brief)` — 서버가 원장을 0.5초마다 보며 끝 · 상태/단계/라운드 바뀜 · 상한(`DELIB_STATUS_WAIT_MAX_S` 기본 240, 540 까지) · 종료 · 새 심의 멈춤에서 돌아온다(brief 는 질문 앞 80자) · `deliberate_result(view="summary")` — 결정 · 투표 · 소수 의견 · 숫자 대조 · RA 주소(기본 full 그대로) · 원장이 투표 집계 · RA 주소를 잃던 것과 숫자 대조를 칸으로 남긴다(사용자 결정 11-02, TS-5) | 올림 — 에이전트 서버 재기동(dev 11-01 23:36 UTC). 이 판 앞에 끝난 잡의 요약은 투표 · 숫자 대조 · 주소가 null(까닭과 함께) |
| 게이트웨이 | `6dc4abc`(병합 — `00d8e30` ~ `95fdbe9`) | `search_tools` 촘촘한 JSON(중간값 1.55배 줄음) · `detail=true` 상한 `GATEWAY_SEARCH_DETAIL_MAX_CHARS` 25,000(넘으면 `detail_capped` 로 알림 · 한 도구 전문은 그 이름으로) · 서버 지침 13번(새 심의는 서버 엔진 · `wait_s` 로 한 번 · 결과는 요약부터 — 그 인자가 지금 스키마에 있을 때만) · `risk_start_job` 은 `llm=glm` · `routine_call` 은 `deliberate_result` 의 `view` 를 버린다(루틴은 전문 — TS-4) | 올림 — 게이트웨이 재기동(dev 11-01 23:37 UTC). **에이전트 서버 `aadd591` 과 함께 받는다** — 지침 문장은 에이전트의 새 인자를 볼 때만 켜진다 |
| 리스크 앱(HWAXRisk) | `4d346316` · Drive(HEAXHub) `dist-20261102-233903Z` — 긴급 11-02 F2 단면 자리 찾기 | `risk_locate_for_section`(리스크 항목 · refdes · 넷 · ECAD 좌표 → MCAD 좌표와 단면 두 장 — StepForge F1 `section_pair_view` 에 넘길 자리) · `risk_propose_board_transform` · `risk_set_board_transform` · `risk_set_item_location`(넷 다 게이트웨이 위임으로 확인된 신원만 · 리스크 심사 좌석에는 D-18 문이 닫는다) · 스키마 v7(보드 ↔ CAD 변환 등록부 `rr_board_transforms` · 항목 `location_json`) · REST `…/locate` · `…/board-transforms` · `…/item-location` — HWAXRisk `docs/f2-locate-for-section.md` | 올림 — `dist-from-drive.sh` 로 hwax-risk 를 받는다(기동 때 v6 → v7 이관 · 그 전 DB 사본 `risk_review.db.pre-migrate-v6-<시각>`). 확인 — 게이트웨이 `tools/list` 에 도구 넷 · 앱 `/api/health` 의 `schema_version` 7 · 그 문서 6절의 cae00 몫(ODB `get_part_detail.side` · bottom 부품 좌표 · `get_net` 핀 좌표 · 구멍 쪽 넘김 · 실제 메인 보드 하나로 손 셈(82.13 · 2.82 · 아래 면)을 제안이 되찾는지). 외곽 자리 검사는 ODB 허브 OH-04(외곽 bbox) 뒤 — 그 전에는 구멍이 유일한 자리 근거다. F1 은 StepForge 세션 몫(받으면 따로 줄). dev 확인 11-02 — 도구 넷 보임 · v7 · 이관 사본 하나 |
| 에이전트 서버 · 게이트웨이 · 포털 | 에이전트 `332f70e3` · 게이트웨이 `5bb79e09` · 포털 `06860be0`(병합) · `32d03bf6`(이력) · Drive `images-20261102-235509Z` — 온톨로지 먼저(사용자 결정 11-02 OF-14) | F0 — 겹침 때문에 게이트웨이가 접두를 단 읽기(`aidatahub_semantic_search` 등)를 좌석 자유 조회가 원래 이름으로 판정(`/tools-map` 의 `orig` · `declared` — 리스크 심사 · 앱이 띄운 패널 · 기준일 심의 · 선언 백엔드 · 허브 가족은 그대로) · 챗 칸 — 어휘표 `ontology`(기본 표는 옛 고정 몫과 바이트까지 같다 — 입구 `entry` 는 박스 덧씌우기로) · 게이트웨이 `onto_first`(기본 끔) · 심의 시작 · 챗→심의 브리프의 '온톨로지 먼저 보기'(주제 과제가 있을 때만 · 정본 허브 도구 둘이 이 박스에서 읽기로 확인돼야 부른다) — `docs/ontology-first` | 올림 — update-all 뒤 세 서비스 재기동(화면은 Drive 판). 할 일 · 확인은 [`../ontology-first/server-setup.md`](../ontology-first/server-setup.md) — 받기 전 받은 편지함 Q20 · Q21(F0 셈의 앞), 받은 뒤 읽기 표지(`read_tools.local.json` 에 정본 허브 `object_resolve` 등 — 미리보기 전) · `/tools-map` 의 `orig` · `/health` 의 `core_vocab.ontology` · Q21 다시, 입구 · `onto_first` 는 재기 뒤에만. dev 확인 11-02 — `/tools-map` 의 `orig` 21 · 새 심의의 '전문가 자유 조회 활성 — 187종'(엔진 판정을 떠 있는 지도에 대 셈하면 F0 몫은 `aidatahub_semantic_search` · `signalforge_semantic_search` · `heaxstep_forge_list_jobs` · `ste_list_jobs` 넷 · 빠지는 것 0) · `core_vocab.ontology`(entries 0 · dropped 0 · 이 박스에 없는 SP 허브 이름 12) · 미리보기 창구가 섰다(무인증 401) |
| StepForge | `5979a26`(코드) · `8a06681`(문서 · 끝) · Drive(HEAXHub) `dist-20261103-004526Z` — F1 짝 단면(그쪽 세션 a72 · D-655) | `section_pair_view`(과제 2 ~ 6 을 같은 자리에서 자른 짝 단면 한 장 + 측정 JSON · mm 만 · 창 안 파트 먼저 60 상한) · `section_batch_result` · 잡 종류 `section_batch`(읽기) · REST `/api/section-pair-view` · `/api/section-batch-result` — 있던 도구의 인자 · 답은 그대로 | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). 확인 — 게이트웨이 `tools/list` 에 두 도구 · 실제 두 개정으로 한 번(그림 · '그림 저장 — fig_…' 표지). dev 확인 11-03 — 게이트웨이 경유 0.37 초 · JPEG 111 KB · 그림 보관 |
| StepForge | `ed0ca60`(F3) · `a218962`(SP 서브모듈 `b23c392` · 0.4.71 — 킷 판 그대로) · `20b72a7`(문서 · 끝) · Drive(HEAXHub) `dist-20261103-025507Z` — F3 짝 단면 묶음(그쪽 세션 a73 · D-656) — **위 F1 줄의 판을 덮는다(받을 것은 이 판)** | `section_batch(rows)`(읽기 — 줄마다 `section_pair_view` 와 같은 인자 · 1 ~ 50줄 · 잡이 50 MB 를 쓰면 남은 줄은 까닭과 함께 그리지 않는다 · 틀린 줄이 하나라도 있으면 잡을 만들지 않고 그 줄 번호로 거절 · 같은 줄로 다시 부르면 같은 잡) · REST `POST /api/section-batch` · `section_pair_view` 설명에 '비교' | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). 확인 — 실제 항목 하나의 `f1.calls` 두 줄(견줄 판 id 를 더한 꼴)을 `section_batch` 로 → 그림 두 장. 진행은 `section_batch_result` 의 `ready: false` 로 본다 — 게이트웨이에서 StepForge 의 `job_status` 는 SmartTwinMCP 와 이름이 겹쳐 `heaxstep_forge_job_status` 다(맨 이름은 없다). dev 확인 11-03 — F2 의 calls 두 줄 → 잡 4.1 초 · 그림 둘(게이트웨이 보관) · 같은 줄 다시 → 같은 잡 |
| StepForge | `5366950`(D-657 — fold · stackup_figure · 진행 안내 · '묶음') · `dc7b447`(D-658 — 적층 측정 잡 스스로) · `cce849c`(문서 · 끝) · Drive(HEAXHub) `dist-20261103-073959Z` — F6 · 사용자 결정 11-03 RF-29(그쪽 세션 a74 · a75) — **위 F1 · F3 줄의 판을 덮는다(받을 것은 이 판)** | `section_pair_view` · `section_batch` 줄의 `fold`(접힌 상태로 돌려 자른다 — 아무 파트도 안 가리키면 거절) · 새 읽기 도구 `stackup_figure`(적층 비교를 그림 한 장 — `job_id` 또는 두 과제) · `compare_stackup` · `stackup_figure` 가 예산에서 멈추고 두 과제가 파싱돼 있으면 측정 잡을 스스로 넣고 `job` 을 준다(읽기 토큰도 — `job_call` 그대로, 파싱 안 된 과제는 `job_not_queued`) · `section_batch` 안내가 `section_batch_result` · `heaxstep_forge_job_status` | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). 확인 — 실제 폴더블 두 개정으로 `fold` 단면 한 번(그림 제목 `CLOSED STATE`) · 실제 두 보드로 `stackup_figure` · 큰 보드 짝에서 `compare_stackup` 의 `job` → 끝난 뒤 `stackup_figure(job_id)` 그림. 측정 잡은 한 번에 하나씩 돈다(뒤 잡은 pending). dev 확인 11-03 — fold 0.44 초 · 판마다 1 파트 · 그림 보관, stackup 바로 0.42 초, 211 파트 보드 짝이 예산에서 멈춰 잡이 저절로 · 같은 부름은 같은 잡 · 그 잡의 그림(`stackup_figure(job_id)`)은 dev 에서 아직 — 첫 측정 잡이 33분째 진행 10%(바로 길 어림은 61초 이상 — 하한), StepForge 세션에 알림 · run_job 길의 그림은 그쪽이 작은 보드로 확인 |
| StepForge | `164c99c`(D-659) · `01bb4a0`(문서 · 끝) · Drive(HEAXHub) `dist-20261103-104015Z` — a76(그쪽 세션) — **위 F1 · F3 · F6 줄의 판을 덮는다(받을 것은 이 판)** | `compare_stackup` · `stackup_figure` 가 쌓임 축을 정하기 전에 멈추면 잡을 넣지 않고 `job_not_queued`(축 주기 · 파트 좁히기 · 쓰기 토큰의 `job_call`) · 축이 확실해진 뒤 멈추면 그 축으로 잡(`job.axis_from_stop`) · 측정 잡 진행이 10 ~ 90 으로 움직이고 로그에 '[측정] 시작' · 1분마다 살아 있음 · 짝 단면 설명에 '폴더블' · '힌지' · '닫힌 상태' | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). 확인 — 받은 편지함 Q4 의 적층 걸음은 축을 준다(`--axis-a z --axis-b z`). dev 확인 11-03 — 축 없이 211 파트 짝 5.0초 · 잡 없음 · `job_not_queued`, 축 z 로 1.8초에 잡이 저절로 → 진행 26 · 54 · 100(2분) → `stackup_figure(job_id)` 그림 보관(211 줄 · 1500 × 5743 · 583 KB — `over_cap` 표지, 256 KB 를 넘는다) |
| StepForge | `143dd42`(D-660 — 적층 그림 쪽 나눔) · `969e7fb`(짧은 꼴의 한쪽 층 이름을 수로) · `9c8946e`(문서 · 끝) · Drive(HEAXHub) `dist-20261103-130959Z` — a77(그쪽 세션) — **위 F1 · F3 · F6 · a76 줄의 판을 덮는다(받을 것은 이 판)** | `stackup_figure` 에 `page`(1부터) — 줄이 60 넘으면 쪽마다 그림 한 장 · 답의 `page{page, pages, rows, next}`(`next` 는 다음 쪽을 부르는 글, 끝 쪽은 null) · 줄 번호 · 색은 전체 결과 그대로 · 짧은 꼴의 `totals.layers.only_a` · `only_b` 가 이름 목록 대신 수(이름은 `full=true` · `files.json`) | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). 확인 — 받은 편지함 Q4 의 적층 걸음이 쪽을 끝까지 받는다(포털 점검 스크립트가 따라간다). dev 확인 11-03 — 게이트웨이로 211 줄 결과를 넷 쪽으로(1–60 · 61–120 · 121–180 · 181–211) · 쪽마다 그림 보관 · 239 ~ 256 KB · over_cap 없음 · 끝 쪽 next null. 운영 사본(stepforge-prod)도 바깥 주인이 따로 있는 사본이 아니라 cae00 이 같은 Drive 판으로 짓는다 — 이 판으로 지으면 F1 · F3 · F6 · a76 · a77 이 운영에 닿고 따로 넘길 곳이 없다(사용자 답 11-03, StepForge 세션 경유) |
| 리스크 앱(HWAXRisk) | `fc384f4b`(병합 — 코드 `8c4a6d1` · 문서 `742c4d3`) · Drive(HEAXHub) `dist-20261103-011742Z` — F2 → F1 넘김 | `risk_locate_for_section` 답의 `f1.calls` — 평면마다 F1 `section_pair_view` 에 그대로 부를 인자(projects = 이 과제의 CAD 하나 · point [x, y, z] 목록 · axis · window_mm · unit · 몸체는 highlight — offset 없음). 그 전에는 `f1` 칸을 그대로 넘기면 F1 이 거절했다(점 사전 · offset + 창). note · 도구 설명도 고침, 스키마 그대로(v7) | 올림 — `dist-from-drive.sh` 로 hwax-risk 를 받는다. 확인 — 실제 항목 하나의 답에 `f1.calls` 두 줄 · 견줄 판 id 를 더해 F1 을 부르면 그림 두 장. dev 확인 11-03 — 시험 과제의 실제 bbox 로 지은 calls 를 F1 에 그대로 → 두 평면 그림 · 평면 = 그 점 · 강조가 두 판에서 맞음 |
| 게이트웨이 | `1c933629` — 검색 낱말(F1) | 띄어 쓴 열쇠 '짝 단면' · '단면 비교' → `section_pair_view`('짝' 한 글자가 질의에서 버려져 단면 도구가 같은 점수였다 — dev 평가 8위 → 1위 · 10위 → 2위, 추적 147쌍 순위 그대로, 동의어 81) | 올림 — update-all 뒤 게이트웨이 재기동. 검색 덧씌우기를 둔 박스는 `/search-eval` 로 한 번 본다 |
| 포털 | `46740dd0`(병합 — 탐침 `d9d92bbd` · 운영자 `6de751ee`) — 전문가 고르기 · 지식카드 온톨로지 잇기 O0a(사용자 결정 11-03 EO-1 ~ EO-4) · F2 쓰기 둘 | 읽기 전용 탐침 `infra/scripts/card-entity-probe.py`(카드 표본 300장이 정본 허브 객체에 exact 로 이어지는 비율 — 짓기 전에 잰다) · HE팀 운영자 `he-expert-risk` writes 에 `risk_set_board_transform` · `risk_set_item_location`(F2 의 새 쓰기 — 목록 밖이면 확인 관문이 부류 없음으로 본다) — `docs/expert-ontology` | 올림 — update-all 로 받는다(재기동 없음). 할 일 — 받은 편지함 [`../cae00-inbox/2026-11-03.md`](../cae00-inbox/2026-11-03.md) Q1 ~ Q3(탐침 실행 · 부품 슬러그와 별칭 · 뺄 낱말). 쓰기 둘은 받기만으로 켜진다 — 에이전트 서버의 확인 관문이 `he-team.json` 을 바뀐 시각으로 다시 읽는다(재기동 · 동기화 없음) |
| 포털 | `2cc6707d`(병합 — `bf528ef4`) — CAD 위치 가시화 끝에서 끝까지 점검(사용자 요청 11-03) | 점검 스크립트 `infra/scripts/cad-figure-check.py` — 실제 리스크 항목 하나로 `risk_locate_for_section` → 짝 단면(견줄 판 · 접힘) → 묶음 → 적층 그림 → `figure_get` 주소로 받아 크기 · sha256 대조 → 대상을 주면 RA 보고서 · MX 백서 문서에 넣기. 읽기가 기본, 요약은 상태 · 수만 — `docs/report-figures` RF-31 | 올림 — update-all 로 받는다(재기동 없음). 할 일 — 받은 편지함 [`../cae00-inbox/2026-11-03.md`](../cae00-inbox/2026-11-03.md) Q4(위 Drive 받기 뒤 — 고르기 · 점검 · 그림을 사람이 보기 · 고르면 시험 보고서에 넣기) · Q5(Windows PC 변환기) |
| 포털 | `a262ee21`(병합 — `7de9d3ae`) — CAD 점검이 적층 그림 쪽을 끝까지 | `infra/scripts/cad-figure-check.py` 의 적층 걸음이 답의 `page` 를 보고 끝 쪽까지 부르고 쪽마다 그림을 받는다(StepForge a77) — `docs/report-figures` RF-33 | 올림 — update-all 로 받는다(재기동 없음). 받은 편지함 Q4 그대로 |
| 게이트웨이 | `a3ae08b2`(병합 — `f37aa44`) — 쓰기 낱말 `repin`(SP 0.4.72) | SP 의 새 허브 도구 `lineage_repin`(계보 다시 고정 — 되돌릴 길이 없는 사람 판단)이 쓰기로 읽힌다(SP 도구에는 표지가 없어 이름으로 가른다 — `docs/sp-latest` SL-1). 새 읽기 넷(object_explode · object_lineage · graph_reach · relation_proposals)은 루틴 · 좌석 읽기로 열리지 않는다(모르면 막기). 검색 열쇠 '단면 비교' 의 원천 고침 표시를 걷었다(StepForge 설명에 그 말이 들어갔다) | 올림 — update-all 뒤 게이트웨이 재기동 |
| 포털 | `1dd1bd71`(병합 — `4ce5eb71`) — 허브 운영자의 SP 0.4.72 쓰기(사용자 결정 11-04 `docs/sp-latest` SL-2 · SL-3) | `he-data-coreontology` 의 선택 칸에 바꾸는 도구 마흔둘(confirm 27 · writes 15 — 도구마다 `needs_tool` 이라 허브가 옛 판이면 그 도구만 빠진다) · 운영자 미리보기의 '목록 밖 쓰기' 를 확인 관문과 같은 셈으로(형제 허브의 같은 도구를 거짓 알리지 않는다) · 빠진 도구 알림은 앞 여덟만 | 올림 — update-all 로 받는다(에이전트 서버는 재기동 없이 운영자 정의를 다시 읽는다). 허브 판 · 반영은 `docs/sp-latest/server-setup.md` · 받은 편지함 2026-11-04 |
| KooRemapper | `225da1b` — SP 받는 쪽을 키트 2026-11-03(서브모듈 `ab41cff` · 0.4.72)으로(그쪽 세션, `docs/sp-latest` SL-5) | 층 1 판 표시 · 시험장 8/8 · §8.1 선 확인표 — 받기 규칙은 10-21 판과 같아 동작은 그대로다(SP 에서 온 연결만 끊고 사람이 이은 것은 둔다) | 올림 — update-all 2단계(`deploy-all-from-drive.sh`)로 코드를 받는다(Drive 판 그대로). 실제 SP 연결 점검은 허브 주소 · `core:read` 토큰 뒤 |
| StepForge | `b9db3d0`(D-661 키트) · `ec721ef`(D-662 그래프) · `ce478ca`(문서) · Drive(HEAXHub) `dist-20261103-234515Z` — a78(그쪽 세션, `docs/sp-latest` SL-5) — **위 F1 · F3 · F6 · a76 · a77 줄의 판을 덮는다(받을 것은 이 판)** | 키트 2026-11-03(받기 규칙 그대로 · 시험장 8/8 · §8.1 선 확인표 자동 시험) · SP 그래프 기능을 옮긴 새 읽기 셋 `onto_reach`(영향 범위) · `onto_explode`(BOM 총수량 — 수량은 카탈로그 `quantity_key` 의 선 칸, 없으면 1개로 세고 `quantity_note`) · `onto_lineage`(원천 → 파생물 — 낡음은 늘 null, 허브 판정) · `onto_neighbors` 의 `direction`(기본 both — 예전과 같다)과 선마다 `properties` · `onto_walk` 의 rollup `weighted` · `leaves_only` · `fn product`(끄면 예전 값) · `onto_query` 의 선 칸 주소 `out.<관계>~<칸>` · 조건 `edge` 묶음 — ⚠ `fields` 는 주소 10개 · 줄마다 값 20개까지(넘는 수는 `fields_more`). 포털 · 에이전트 · 게이트웨이 · 리스크 앱 코드에는 `onto_*` 를 직접 부르는 곳이 없어(모델만 부른다) 고칠 것이 없다 | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). dev 확인 11-04 — 게이트웨이에 도구 183 · 새 셋 읽기(루틴 · 좌석 읽기로 열림). cae00 확인은 받은 편지함 2026-11-04 Q3. 운영 허브의 PLM 정의가 `quantity_key` · `lineage_source` · `effectivity` 를 켜기 전에는 `kind_meanings` 가 비고 `onto_lineage` 는 '계보 관계 종류가 없다' 가 정상이다(켜지는 날 코드는 그대로 — 매 호출 카탈로그에서 읽는다) |
| StepForge | `064ec41`(SP 서브모듈 `d3b5aa1` — 키트 판 그대로 · 시험장 통과) · `e4d7bd8`(D-663 기능) · `d0126cd`(문서) · Drive(HEAXHub) `dist-20261104-135504Z` — a79(그쪽 세션, 사용자 제안 11-04 — `docs/report-figures` RF-34) — **위 F1 · F3 · F6 · a76 · a77 · a78 줄의 판을 덮는다(받을 것은 이 판)** | 단면 지도 — 파싱 뒤 작업량 어림 위쪽이 900초 안이면 읽기 전용 그림 잡 `section_atlas` 를 스스로 건다(축마다 판 외곽 12칸 가운데 + 그 간격에 안 걸린 얇은 파트 가운데 · 장마다 png · 정의 JSON · 곡선) · 새 읽기 도구 `section_atlas`(상태 · 장 목록 · 자리에 가장 가까운 장 · 파트만 자홍 강조로 다시 그림 — 한 호출에 한 장) · `section_view` 에 `highlight`(`through` 와 함께만 · 기본 꺼짐 — 예전과 같다) · 끄기 `STEPFORGE_SECTION_ATLAS=off` · 기존 과제는 다시 파싱하거나 `run_job(kind="section_atlas")` | 올림(그쪽 세션) — `dist-from-drive.sh` 로 step_forge 를 받는다(교체 전 도는 잡이 없는지 본다). dev 확인 11-04 — 게이트웨이 도구 184 · `section_atlas` 읽기(루틴 · 좌석 읽기로 열림). cae00 확인은 받은 편지함 2026-11-04 Q4. 장마다 치수 8초 상한(넘으면 정의의 `skipped_work` — 끝까지는 `section_report(dims=true)`) · 한 장 60 파트 상한 · 월드 x · y · z 축만 |
| StepForge | `562e8de`(SP 서브모듈을 `ab41cff` 로 되돌림 — SP main 이 되돌려졌다, `docs/sp-latest` SL-7) · `8e711c4`(D-664 기능) · `7c71d7a`(문서) · Drive(HEAXHub) `dist-20261105-015533Z` — a80(그쪽 세션, 그쪽 사용자 11-04 — `docs/report-figures` RF-35) — **위 a79 줄의 판을 덮는다(받을 것은 이 판)** | 단면 그림이 CAD 단면도 꼴 — 흰 바탕 · 재료 면을 파트 색조로 채우고 해칭 · 구멍과 빈 곳은 흰색, 강조 그림은 타겟만 자홍 · 이웃 회색(section_view · section_pair_view · section_batch · compare_part_view · dimension_view 확대 · section_atlas). 도구 · 인자 · 응답 칸 · 수치는 그대로(도구 184). 옛 단면 지도는 그림 꼴이 바뀌어 status stale · rebuild 호출문을 낸다 — 새 반입은 스스로 새 꼴. 단면 한 장 시간이 는다(RC 55파트 3.2 → 8.6초 · 지도 65장 249.8 → 399.2초) | 올림 — update-all 이 Drive 판을 받는다 |
| StepForge · 포털 | StepForge `e13bd08`(D-665 기능) · `d776e71`(문서) · Drive(HEAXHub) `dist-20261105-045500Z` — a81(그쪽 세션, 그쪽 사용자 11-05 — `docs/report-figures` RF-37) — **위 a80 줄의 판을 덮는다(받을 것은 이 판)** · 포털 `2ff8d56d`(챗이 같은 출처 SVG 를 격리 iframe 으로 — RF-36) · 에이전트 서버 `79953ac`(도구 그림 저장 — 내용으로 꼴 · 8 MiB 상한) | 상호작용 SVG `format="svg_live"`(section_view · section_atlas · section_pair_view · section_batch — 기본은 png 그대로) — 파트 위 이름 · 경로 풍선 · 간극 치수 호버(CSS 만 · 스크립트 없음), section_atlas 에 `format` · `viewer`(지도 HTML 뷰어 `GET /view/{project_id}/atlas` — viewer.route · public_url), 도구 184 그대로. 포털 챗은 그 SVG 를 `<iframe sandbox="">` 로 그려 호버가 산다 (포털 화면은 Drive 이미지 판으로 받는다) | 올림 — update-all 이 받는다(확인은 받은 편지함 2026-11-05 Q4 · Q5) |
| SignalForge | `07b3f1a` — SP 받기 키트를 2026-11-03(SP `ab41cff`)으로(그쪽 세션, `docs/sp-latest` SL-5) | 키트 파일 · 판 표시만 — 받는 규칙 그대로, 받은 선은 사본에만 두고 색인에 안 쓴다(사용자 결정 11-04 '지금대로 안 쓴다') | 올림 — update-all 로 받는다(사람 몫 없음). 다음 plm-sync 가 새 키트 파일로 돈다 |
| 포털 · 에이전트 서버 | 포털 `e871b3c1`(병합 — `c5c7c2bc`) · 에이전트 서버 `a3d441f`(병합 — `550a42d`) — HE팀 운영자 박스 덧씌우기(사용자 결정 11-04, `docs/he-team-overlay`) | git 의 `infra/personas/he-team.json` 은 기본값, 이 박스에만 있는 앱의 운영자는 `infra/personas/he-team.local.json`(gitignore)으로 더하고 덮고 뺀다 — 동기화 · 포털 접근 검사 · 확인 관문이 같은 합친 정의를 보고, update-all §6 · §7 이 덧씌우기 줄과 지문 대조를 찍는다. 파일이 없으면 지금과 같다 | 올림 — update-all 로 받는다(에이전트 서버 재기동으로 `/health` 에 overlay 칸이 생긴다). 만드는 법 · 고칠 때마다는 `docs/he-team-overlay/server-setup.md` — **이 판을 받은 뒤에** 만든다(옛 `.gitignore` 의 첫 stash 가 치운다) |
| PaperIngest | `dc51ccb` · `4a6f5c7` — 논문 업로드 중계(사용자 결정 11-04 '지금 길을 잇는다', `docs/paper-ingest`) | dev 한 틱(당기기 move → ExpertGrounding 인입 → 매핑이 바뀌면 논문 레코드) · 당기기 move 모드 — dev 쪽은 걸어 두었다(Drive 자리 `paper-ingest/from-cae00` · cron 30분) | **사람 몫** — cae00 호스트에 송출 cron(`to_drive_pusher.sh move`) 하나 — `docs/paper-ingest/server-setup.md`. 지금 PaperIngest 는 비어 있어 걸어도 흐를 것이 없다 — 첫 실제 업로드가 끝까지의 확인이다 |
| AIDataHub · 포털 | AIDataHub `918681d`(병합 — `ac6f788` · `2f6d60b` · `ac05f65` · `779e112` · `090b2a2` · `9b1538f` · `0a88950`, 앞선 병합 `7e98ad6` · `190ca57` · `5abff48`) · 포털 `e84d1d0c` · `de25d721` — AIDataHub 동기화를 바뀐 조각만(사용자 결정 11-05, `docs/aidh-parts-sync`) | update-all §3 이 조각 길을 먼저 — 바뀐 것이 없으면 목록 하나만 받고 끝, 실패 · 목록 없음 · 목록이 하루 넘게 낡음(⚠)은 예전 전체 덤프 길 · 같은 줄은 다시 쓰지 않기(두 길 모두) · 절 · 첨부 · 전문가 연결은 레코드를 이긴 쪽(사용자 결정 11-05 — 이 박스가 더 새로운 카드의 것은 dev 판으로 안 덮음) · 앞 모습 폴더 7일 보관. 설정 없음 — 첫 실행은 조각 전부(dev 첫 내기 크기는 `docs/aidh-parts-sync/server-setup.md` 1절) | 올림 — update-all 이 받는다(첫 두 실행의 §3 줄은 받은 편지함 2026-11-05) |

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
    - **11-04 — dev 에 적용됐다**(사용자가 SignalForge 세션에서 '적용' — 2026-11-03 22:55 UTC, 그쪽 문서 `aab838c`). 쓰기 전에 dry-run 을 다시 돌려(고침 9,603) 적용했고,
      적용 뒤 dry-run 은 고침 0 이다. 되돌리기 CSV 는 dev 의 SignalForge `crawler/logs/` 에 있다 — 사용자가 11-04 그대로 두기로 확인했다(되돌리지 않음). 실린 덤프는
      11-03 23:02 UTC 에 Drive 로 나갔다. cae00 은 dev 의 다음 덤프 병합(약 30분 간격)으로 받고 그때 빈 창이
      닫힌다 — 병합 뒤 그 문서 4절의 수와 5절의 질의, DW-21 · OT-15 로 본다. update-all 로 sf-mcp 가 이미 새 코드면 재기동은 필요 없다. 남은 결정 하나 — 세대 표지
      없이 쓴 글을 더 가를지는 사용자가 cae00 표본을 본 뒤 정한다.
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
| B17 | deliberation-quality 42 줄의 심의(경시성 — 원 질문 · 원 사람 의견 그대로)를 이어하기로 한 번 다시 돌린다. 상태줄 `이어하기 재심사 — 신규 좌석 <키>(<축>)` 에 서비스 운영 · 필드 데이터 계열이 1명 이상 오르고, 이전 좌석은 전원 유임(좌석 사건 personas)이다. `검색 축을 짓지 못해(…)` 가 나오면 GLM 이 답하는지 먼저 본다. 결과(신규 좌석 키 · 축)는 사용자에게 알린다 — dev 는 축 LLM 이 없어 보지 못했다 |
| HA-09 | 시험 심의 하나(작게 — 좌석 둘 · 라운드 셋)를 MCP 로 띄우고 2라운드 도중 `AGENT_RESTART_FORCE=1 ./start.sh -d`. `deliberate_status` 의 `resume.seat_resume`(spoken · todo)를 보고 `deliberate_continue` 한 번 — 같은 잡 id 로 잇고, 전사에 좌석마다 라운드당 한 번, 끝난 라운드의 LLM 호출은 다시 없다. 보고서를 켠 심의는 보고서 저장 뒤에 끊어 이으면 같은 RA 번호 하나다 |
| 리스크 앱 셈(받기 전) | 읽기만(앱 데이터 디렉터리에서 `sqlite3 -readonly risk_review.db`) — 구성원 읽기 · 편집자 쓰기가 열려 고침 전 들여오기가 남긴 행이 닿는 곳이 넓어졌다. 질의는 HWAXRisk context-notes **MB-9** — ① 이양으로 다시 찍히지 않은 남의 편집자 · 보기 멤버 행 ② 만든 흔적(member.put · project.transfer 감사)이 없는 편집자 · 보기 행 ③ 주인 아닌 사람의 owner 멤버 행, 그리고 RD-6 의 확정인데 병합 대상이 남은 부품 키. 나오면 지울지 사용자에게 알린다(dev 는 모두 0) |
| 리스크 앱 동시 2 로 저장된 잡(CC-25) | 받기 전에 센다 — `sqlite3 -readonly risk_review.db "SELECT id, target_key, tier, state, concurrency FROM rr_jobs WHERE state IN ('queued','running','paused') AND COALESCE(mode,'panels') = 'panels' AND concurrency > 1"`. 칸이 아무 일도 않던 동안 동시 2 로 만든 살아 있는 잡은 이 판부터 패널 둘을 함께 돈다(전역 자리는 그대로, Claude 잡은 늘 1). 묶으려면 그 잡을 취소하고 동시 1 로 다시 만든다(화면). 박스 전체는 `HWAXRISK_CONCURRENCY=1` 인데 이 앱의 env 는 매니페스트 `launch.env` 로만 닿아 dev 에 알린다. 앱이 떠 있는 동안 DB 를 손으로 고치지 않는다 |

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
