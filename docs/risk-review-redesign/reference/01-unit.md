# 현재 구조 — 코드 대조 + 반박 검증 결과 (2026-10-08, dev HEAD: HWAXRisk 7248651 · HWAXAgentServer 7683125)

## 패널이 받는 것 (unit)

### 검증 반영 최종 답
같은 타깃의 패널들은 변경점 자료와 질문 문자열을 똑같이 받고, 좌석 도메인에 따라 변경점을 나누거나 거르거나 순서를 바꾸는 코드는 앱 브리프에도 심의 엔진에도 없다. 타깃 하나는 diff 한 건 전체(또는 스냅샷 한 건)이고 target_key 는 `<kind>:<ref_id>` 문자열이며, 같은 diff 에 타깃을 하나 더 열면 409 로 막히므로 영역별 타깃으로 쪼갤 길도 지금은 없다(routes.py:2025~2027). (a) build_brief 에서 seats 를 받는 것은 E0c 와 E7 뿐이고 E1~E6·E8·E9 는 타깃 문맥만 받는다. E7 은 좌석 dict 의 `agent_key` 를 읽는데 편성기는 `key` 로 적어 코드상 늘 '[착석 좌석 없음]' 이 되므로, 좌석에 따라 달라지는 브리프 항목은 사실상 없다(dev DB 는 타깃·패널이 0건이라 동결본으로는 확인하지 못했다). (b) E2 에 실리는 것은 실제로는 의미(semantic) 이벤트뿐이고, 정렬은 절대 크기가 아니라 부호 있는 delta 의 내림차순이라 단위가 섞인 채 감소 방향 변경과 크기 없는 이벤트가 1100자 상한에서 먼저 잘린다. 구조·파라메트릭 변경은 E1 요약의 [구조]·[치수]·[재료]·[결과] 줄과 E3(700자)·E4(600자)로만 가고, E1 의 [의미] 줄은 change_kind 별 앞 5건씩 700자까지다. (c) personas 는 key 와 origin 만 싣고 role 은 빈 문자열이며, 엔진이 get_agent_session 으로 역할 원문을 복원한 뒤 공통 계약과 그 도메인 계약 줄을 붙인다. (d) 질문은 target_key 만으로 만들어지고 과제코드, target_key, '기준 X 대비 변경'(또는 '현황'), 소스 ref 의 키=값, 요약 앞 200자가 들어가는데, 그 200자는 요약의 [대상]·[비교가능성] 줄(id·해시·parity)이라 변경 내용은 질문에 실리지 않는다. 패널마다 달라지는 것은 앉는 좌석(서로 다른 도메인의 primary 4석과 counter 1석, 엔진이 기준선 옹호석 1석 추가), 그 도메인들의 E0c 줄, E0 의 model, 잡 메모 M, modifiers·rounds·예산에 따른 tools 이고, 패널은 영역 묶음이 아니라 도메인을 섞은 편성이다. 웹 러너 경로에서는 엔진이 좌석마다 지식카드와 역할에 맞춘 조회 도구 묶음을 주고 라운드마다 최대 3회 직접 조회를 시키지만, 그 검색어가 변경 내용 없는 위 질문이고 전체 변경 목록 도구(risk_get_diff)는 apps 에 리스크 앱이 없어 좌석에게 열려 있지 않다. 같은 타깃의 앞 패널 결과는 E5(자기 과제 제외)·E7(자기 타깃 제외)로 들어오지 않으므로 패널들은 같은 변경 전체를 서로 독립으로 다시 본다. 따라서 '변경점이 많으면 영역별로 나눠 분석' 은 구현돼 있지 않고, 지금 있는 것은 같은 변경 요약 한 벌을 여러 도메인 좌석이 각자 제 도구로 확인하며 읽는 구조다. 나눌 축(change_kind 12종·subject_key)은 이벤트에 이미 있으나 좌석 도메인과 잇는 표가 없고, 브리프의 11,000자·12건 예산은 JS 파이프라인의 한도이지 지금 웹 엔진(120건, 컨텍스트 유도 예산)의 한도는 아니다.

### 바로잡은 것
- (b) 'E2 는 의미·구조 층 이벤트를 층, 크기 내림차순으로 정렬한다, 그래서 크기가 작은 변경이 빠진다' 는 두 군데가 틀렸다. 첫째, rr_diff_events 에는 semantic 행만 쓰인다(HWAXRisk backend/app/diff.py:1743~1752). 구조·파라메트릭 변경은 diff_json 에만 있어 E2 에 오지 않는다. 둘째, 정렬은 절대 크기가 아니라 부호 있는 delta(after − before, diff.py:399)의 내림차순이다(brief.py:487). 단위(mm·rank·요소 수)가 섞인 채 감소 방향 변경(얇아짐·rank 하락)과 magnitude 없는 이벤트가 맨 뒤로 가서 1100자 상한에서 먼저 잘린다. design_relevant=0 인 mesh.density_changed(요소 수 delta)도 걸러지지 않아 앞자리를 차지할 수 있다.
- 결론의 '영역별 분석은 같은 변경점 전체를 각 좌석이 제 역할·계약으로 읽는 것뿐' 은 웹 러너 경로에서는 과소 서술이다. 엔진은 브리프 밖에서 좌석마다 세 가지를 더 준다. 지식카드(agent_search 를 좌석 키로 호출, HWAXAgentServer deliberation.py:4095, 주입 4623~4627), 역할 어휘로 순위를 매긴 자유 조회 도구 묶음(`_tools_for_seat`, 4493), 좌석이 라운드마다 최대 3회 직접 부른 조회 결과(planner.py:23~24 FREE_TOOLS=1·TOOL_BUDGET=3, deliberation.py:4526~4528, 4628~4630)다. 다만 이 셋의 검색어는 모두 같은 질문 문자열이고, 변경점 목록 자체를 좌석별로 나누는 것은 아니라는 결론은 그대로다. MCP L2 경로(hwax-risk-review.js)는 좌석 도구 호출이 없는 evidence_only 라 이 차이도 없다.
- 'E5·E6·E8 은 패널 사이에 원장이 바뀌면 달라진다' 는 조건부로만 맞다. E5 는 자기 과제를 후보에서 빼고(brief.py:1533 `if not pid or pid == project_id`) subject 경로도 자기 타깃을 뺀다(brief.py:669). 그래서 같은 타깃의 앞 패널이 낸 finding 은 E5 로 돌아오지 않는다. 달라질 수 있는 것은 다른 과제의 등록부가 바뀌거나, 패널 종료 뒤 재합산되는 통계 표 rr_delta_priors(E8)의 건수가 움직일 때다.
- '패널마다 달라지는 것' 목록에 tools 가 빠졌다. 패널 예산이 상한을 넘으면 지정 도구가 list_interfaces·interface_graph 둘로 줄어든다(planner.py:278~297). 또 MCP 경로의 '모든 패널' 은 보통 1건이다(routes.py:2601~2605 — planned 가 없을 때 한 건만 편성).

### 놓쳤던 사실
- 영역별로 타깃을 쪼갤 길이 지금은 없다. target_key 가 `<kind>:<ref_id>` 이고 같은 키가 있으면 409 로 막는다(HWAXRisk backend/app/routes.py:2025~2027). diff 한 건(과제 전체의 기준 대비 변경)이 곧 타깃 하나다.
- 패널은 영역 묶음이 아니라 도메인을 섞은 편성이다. 로스터는 기본 15개 도메인(config.py:40)의 전문가 전원이고, 패널 한 건은 잔량이 큰 도메인부터 서로 다른 도메인에서 primary 4석을 뽑고 인접 표로 counter 1석을 더한다(planner.py:404~455). Tier 는 도메인 안 순위로 나뉜다(A=1위, B=ceil(0.3×도메인 크기), C=전원, planner.py:231~239). 패널 번호와 '영역' 사이에는 대응이 없다.
- 질문 문자열에는 변경 내용이 없다. 요약의 섹션 순서가 [대상]·[비교가능성]·[구조]·[의미]… 라서(render.py:773~780) 앞 200자는 id·해시·parity 표기다. 이 질문이 엔진에서 좌석별 지식카드 검색어(deliberation.py:4095)와 좌석별 도구 순위(4493)의 입력이므로, 좌석마다 달라지는 재료들도 '무엇이 바뀌었나' 가 아니라 과제 식별자로 찾아진다. 로스터 순위를 매기는 recommend_agents 질의도 summary_text 앞 500자(roster.py:21, 195~203)라 같은 한계가 있다.
- 변경을 나눌 축은 데이터에 이미 있지만 좌석과 이어져 있지 않다. 이벤트마다 change_kind(dimension·placement·topology·material·type·count·discretization·result·load_path·consistency·electrical·none 12종, assets/taxonomy.v1.json)와 subject_key 가 있고(risk_store.py:208~216) E1 요약의 [의미] 줄은 change_kind 별로 앞 5건씩 700자까지 묶는다(render.py:726~741, 776). change_kind 나 subject 를 좌석 도메인에 잇는 표나 코드는 없다.
- 구조·파라메트릭 변경은 브리프에 요약으로만 간다. E1 요약의 [구조] 260자·[치수] 420자·[재료] 100자·[결과] 160자(render.py:775~779)와 E3(700자)·E4(600자)가 전부다. E1 라인 상한 1650(brief.py:29)이 요약 상한 2000(render.py:44)보다 작아, 요약이 길면 뒤 섹션(씨앗·결과·재료·치수 순)부터 줄째 잘린다.
- 잘린 변경을 좌석이 도구로 되찾을 길도 웹 러너 경로에는 없다. 전체 이벤트를 주는 risk_get_diff 는 엔진의 `_RISK_READ_TOOLS["heax-hwax_risk"]`(deliberation.py:732~733)에 있지만, 러너가 보내는 apps 는 어댑터 앱 둘(heax-step_forge·heax-kooremapper_mcp, adapters/registry.py:26~30, runner.py:302~310)뿐이라 그 도구는 좌석 조회 후보에 들지 못한다(deliberation.py:3752~3758, 접두사 허용 목록 2604~2618 에 risk_ 없음).
- 1R 자유 조회 단계에서 좌석이 보는 문맥은 base 앞 4000자뿐이다(deliberation.py:4487). base 는 질문, 지정 도구 결과, 브리프 순이라(4315~4319) 지정 도구 결과가 길면 좌석은 E1·E2 를 보지 못한 채 무엇을 조회할지 정한다.
- 브리프의 11,000자·12건 예산은 지금의 웹 엔진 한도가 아니다. brief.py:16~19 는 엔진 클램프를 2000자·11000자·12건으로 적지만, 파이썬 엔진은 근거 120건·항목 천장 150,000자·합계는 모델 컨텍스트에서 유도(천장 500,000자)로 올라가 있고(deliberation.py:175~176, 194, 231~234) 포털 스키마도 120건이다(HWAXPortal backend/app/agent/routes.py:146). 11,000자·2000자·12건을 여전히 지키는 것은 JS 파이프라인이다(HWAXPortal infra/pipeline/hwax-deliberate.js:229~230). E2 의 1100자는 앱이 스스로 건 상한이다.
- 같은 타깃의 패널들은 서로의 결과를 브리프로 받지 않는다. E5 는 자기 과제를 빼고(brief.py:1533, 669) E7 은 자기 타깃을 뺀다(brief.py:1037 `o.target_key <> ?`). 패널 1·2·3 은 같은 변경 전체를 독립으로 다시 보고, 합치는 일은 뒤의 등록부 병합(cluster_key)이 한다.
- E7 이 죽어 있으므로 E1~E9 가운데 좌석에 따라 달라지는 항목은 현재 하나도 없다. 좌석 때문에 달라지는 evidence 는 러너가 끼우는 E0c 뿐이고, 그것도 패널의 모든 좌석이 함께 본다.
- JS 파이프라인이 최상위 evidence 와 panels[].delib_opts.evidence 중 어느 쪽을 좌석에 싣는지는 코드로 정해지지 않는다. risk_get_brief 응답을 LLM 에이전트가 패널별 스키마(panels[].evidence·question·seats)로 '그대로 옮기는' 단계다(hwax-risk-review.js:139~208, 294~298).

### 확인된 코드 근거(파일:줄 — 인용)
- target_key 는 해시가 아니라 kind 와 ref_id 를 쌍점으로 이은 문자열이다. — `HWAXRisk/backend/app/routes.py:2025` — `target_key = f"{body.kind}:{body.ref_id}"`
- 타깃 kind 는 snap 과 diff 둘뿐이다. — `HWAXRisk/backend/app/routes.py:1984` — `if body.kind not in ("snap", "diff"):`
- diff 타깃이면 rr_diffs 행을 읽고, 아니면 ref_id 가 곧 스냅샷 id 다(타깃 문맥은 target_key 하나로 정해진다). — `HWAXRisk/backend/app/brief.py:281` — `ctx["snapshot_id"] = target["ref_id"]`
- (a) E2 는 seats 인자를 받지 않는다(store 와 ctx 만). — `HWAXRisk/backend/app/brief.py:472` — `def _item_e2(store, ctx) -> dict:`
- (a) E3 는 seats 인자를 받지 않는다(ctx 만). — `HWAXRisk/backend/app/brief.py:509` — `def _item_e3(ctx) -> dict:`
- (a) E4 는 seats 인자를 받지 않는다(ctx 만). — `HWAXRisk/backend/app/brief.py:542` — `def _item_e4(ctx) -> dict:`
- E1(요약)도 ctx 만 받는다. — `HWAXRisk/backend/app/brief.py:449` — `def _item_e1(ctx) -> dict:`
- build_brief 조립부에서 E2 호출에 seats 가 넘어가지 않는다. — `HWAXRisk/backend/app/brief.py:1327` — `_item_e2(store, ctx),`
- build_brief 에서 seats 를 받는 첫 항목은 E0c(좌석 계약)다. — `HWAXRisk/backend/app/brief.py:1325` — `_item_e0c(seats),`
- build_brief 에서 seats 를 받는 다른 한 항목은 E7(좌석 개인 기억)이다. — `HWAXRisk/backend/app/brief.py:1332` — `_item_e7(store, ctx, seats, adh),`
- (b) E2 는 층이 semantic·structural 인 이벤트만 조회한다. 도메인 조건은 없고 parametric 층은 실리지 않는다. — `HWAXRisk/backend/app/brief.py:481` — `"WHERE diff_id = ? AND layer IN ('semantic','structural')",`
- 변경점 항목의 라인 상한은 E2 1100자, E3 700자, E4 600자로 고정이다. — `HWAXRisk/backend/app/brief.py:29` — `"E0": 500, "E0c": 1000, "E1": 1650, "E2": 1100, "E3": 700, "E4": 600,`
- 상한을 넘는 항목은 줄 단위로 뒤에서부터 잘린다. 변경점이 많으면 정렬 뒤쪽 줄이 모든 패널에서 똑같이 빠진다. — `HWAXRisk/backend/app/brief.py:1357` — `item["result"] = clip_lines(item["result"], min(CLAMP_RESULT, cap - line_overhead(item)))`
- (c) personas 에는 key 와 origin 만 실리고 role 은 빈 문자열이다. — `HWAXRisk/backend/app/runner.py:445` — `"personas": [{"key": s["key"], "role": "", "origin": s["origin"]} for s in seats],`
- (d) 질문 문자열을 만드는 함수는 target_key 만 받는다. 좌석·패널 인자가 없어 같은 타깃의 패널은 같은 질문을 받는다. — `HWAXRisk/backend/app/runner.py:337` — `def panel_question(store: Any, target_key: str) -> str:`
- (d) 질문 앞부분에는 과제코드, target_key, '기준 X 대비 변경' 또는 '현황' 머리말이 들어간다. — `HWAXRisk/backend/app/runner.py:375` — `f"[리스크심사 {code_of(target['project_id'])} {target_key}] {head}이 각 도메인에서 어떤 리스크와 개선을 "`
- (d) 질문 가운데에는 등록된 소스의 kind 와 id 목록이 들어간다. — `HWAXRisk/backend/app/runner.py:376` — `f"낳는가를 도구 근거로 판정하라. 소스 {'; '.join(parts) if parts else '(등록된 소스 없음)'}. "`
- (d) 질문 끝에는 diff(또는 현황) 요약 첫 줄이 들어간다. — `HWAXRisk/backend/app/runner.py:377` — `f"{'diff' if target['kind'] == 'diff' else '현황'} 요약 첫 줄: {summary}"`
- 질문에 싣는 요약은 summary_text 의 앞 200자다. — `HWAXRisk/backend/app/runner.py:358` — `summary = (row["summary_text"] if row and row["summary_text"] else "")[:200]`
- delib_opts 의 question 은 패널의 target_key 로만 만든다. — `HWAXRisk/backend/app/runner.py:459` — `"question": panel_question(store, panel["target_key"]),`
- 패널마다 달라지는 E0c 는 러너가 그 패널 좌석의 도메인 목록으로 만들어 E0 바로 뒤에 끼운다. — `HWAXRisk/backend/app/runner.py:427` — `evidence.insert(1 if evidence else 0, seat_contract_evidence([s["domain"] for s in seats]))`
- 브리프가 만든 E0c 는 prior_evidence 가 빼고 돌려준다(러너가 다시 끼우므로). — `HWAXRisk/backend/app/narrative.py:1441` — `items = [item for item, key in zip(built["evidence"], built["keys"]) if key != "E0c"]`
- E7 은 좌석 dict 에서 agent_key 라는 키를 읽고, 그 값이 없는 좌석은 건너뛴다. — `HWAXRisk/backend/app/brief.py:1016` — `agent_keys = [_s(s.get("agent_key")) for s in seats`
- 편성기가 만드는 좌석 dict 의 키 이름은 agent_key 가 아니라 key 다. E7 이 읽는 이름과 어긋난다. — `HWAXRisk/backend/app/planner.py:425` — `"key": row["agent_key"],`
- seats_json 을 쓰는 곳은 편성기의 이 INSERT 하나뿐이다(grep 으로 확인). 좌석 dict 가 뒤에 agent_key 로 바뀌는 경로는 없다. — `HWAXRisk/backend/app/planner.py:519` — `"INSERT INTO rr_panels(id, target_key, owner_sub, panel_no, tier, seats_json, chair_template,"`
- agent_keys 가 비면 E7 본문은 이 자리표시 한 줄이 된다. — `HWAXRisk/backend/app/brief.py:1027` — `lines = ["[착석 좌석 없음]"]`
- E0 에는 그 패널의 모델명이 실린다. 패널별로 다를 수 있지만 좌석·도메인과는 무관하다. — `HWAXRisk/backend/app/brief.py:1324` — `_item_e0(store, ctx, external_ok, _panel_model(store, target_key, panel_id)),`
- M(메모)은 그 패널을 돌리는 잡의 user_memo 로 채운다. 잡에 따라 다르고 좌석과는 무관하다. — `HWAXRisk/backend/app/runner.py:1009` — `store, settings, panel, user_memo=params.get("user_memo") or "", narrative_mod=narrative_mod, loss=loss`
- 브리프는 조립 시점의 원장에 따라 달라지는 조립물이라 패널마다 동결하고 이전 패널과 항목 해시를 견준다. — `HWAXRisk/backend/app/runner.py:481` — `브리프는 시변 조립물이라 원문이 없으면 quote·인용 재현이 불가하다. 같은 타깃의 이전 패널과 항목 해시를`
- 패널 사이에 좌석이 달라지는 것은 편성 규칙 때문이다. 한 패널은 primary 4석과 counter 1석이다. — `HWAXRisk/backend/app/planner.py:405` — `"""primary 4석(서로 다른 도메인, 잔량 최대부터 라운드로빈) + counter 1석(인접 표)."""`
- 지정 도구(tools)는 타깃 kind 와 report_ids 로 정하는 패널 공통값이다. 좌석 도메인으로 고르지 않는다. — `HWAXRisk/backend/app/planner.py:256` — `"""패널 공통 지정 도구(≤6) — diff 는 pair 조합, snap 은 single 조합. 전사 분포 도구는 넣지 않는다."""`
- MCP 도구 risk_get_brief 는 routes.brief_by_token 을 부른다. — `HWAXRisk/backend/app/mcp_server.py:178` — `return _guarded(routes.brief_by_token, target_key, brief_token, tier)`
- MCP·REST 브리프 경로는 첫 planned 패널의 좌석으로 브리프를 한 번만 조립한다. — `HWAXRisk/backend/app/routes.py:2607` — `seats = panels[0]["seats"] if panels else None`
- MCP·REST 브리프 경로는 그 한 벌의 evidence 를 모든 패널의 delib_opts 에 넣는다. 패널별로 다시 끼우는 것은 build_delib_opts 안의 E0c 뿐이다. — `HWAXRisk/backend/app/routes.py:2630` — `"delib_opts": runner.build_delib_opts(store, config.settings, panel, evidence=engine_evidence,`
- 엔진은 빈 role 로 온 지정 좌석의 역할 원문을 get_agent_session 으로 복원한다. — `HWAXAgentServer/deliberation.py:3983` — `p["role"] = await _restore_role(tools, p["key"], p.get("role") or "", why=_rr_why)`
- 리스크 심사에서는 복원한 역할 뒤에 공통 계약과 그 좌석 도메인의 계약 줄을 붙인다. 좌석별 차이는 여기서 생긴다. — `HWAXAgentServer/deliberation.py:3990` — `p["role"] = ((p["role"] or "") + "\n" + _RISK_SEAT_CONTRACT["_common"]`
- 엔진은 질문과 근거 블록(_tail 안의 chat_ev_inject)을 좌석 공통 base 하나로 만든다. 좌석별로 근거를 나누지 않는다. — `HWAXAgentServer/deliberation.py:4319` — `base = f"[심의 주제]\n{question}\n" + cont + _tail`

### 확인하지 못한 것
- E7 이 실제 패널에서 '[착석 좌석 없음]' 으로 실렸는지는 동결 브리프(rr_panels.brief_gz)로 확인하지 못했다. /data/appdata/hwax_risk/risk_review.db 본 파일에는 패널이 0건이었고(immutable 읽기), WAL 은 -shm 을 건드려야 해서 읽지 않았다. 키 이름 불일치(brief.py:1016 과 planner.py:425)는 코드 읽기로만 내린 결론이다.
- rr_diff_events 에 도메인 열이나 태그가 있는지, 이벤트를 만드는 diff 모듈이 도메인을 붙이는지는 읽지 않았다. E2 의 SELECT 열 목록과 WHERE 에 도메인이 없다는 것만 확인했다.
- 엔진이 좌석마다 따로 넣는 '페르소나별 주제 지식 주입'(deliberation.py:4064 주석)이 리스크 심사 패널에서 실제로 무엇을 싣는지는 확인하지 않았다. 브리프와 별개로 좌석별 차이가 여기서 더 생길 수 있다.
- JS 파이프라인(infra/pipeline/hwax-risk-review.js)이 risk_get_brief 응답에서 최상위 evidence 와 panels[].delib_opts.evidence 중 어느 쪽을 좌석에 싣는지는 읽지 않았다.
- E5·E6·E8 이 같은 타깃의 패널 사이에서 실제로 얼마나 달라지는지(brief_drift 실측)는 보지 않았다. 원장 조회 결과에 달린 항목이라는 것만 코드로 확인했다.
- 확인한 것은 dev 박스의 현재 HEAD(HWAXRisk 7248651, HWAXAgentServer 7683125) 소스다. cae00 에 배포된 SIF 가 같은 코드인지는 모른다.
- DB 를 찾으려던 find 한 건이 시간 초과로 백그라운드로 넘어가 pkill 로 종료했다. 리포·DB·서비스에는 쓰지 않았다.


