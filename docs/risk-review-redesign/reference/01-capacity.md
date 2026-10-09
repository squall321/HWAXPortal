# 현재 구조 — 코드 대조 + 반박 검증 결과 (2026-10-08, dev HEAD: HWAXRisk 7248651 · HWAXAgentServer 7683125)

## 변경이 많을 때 닿는 양 (capacity)

### 검증 반영 최종 답
변경 이벤트가 수백 건이어도 좌석에 닿는 변경 목록은 타깃 하나에 한 벌이고, E2 에는 보통 6~12건(이름이 아주 짧으면 13건, 이벤트 글이 상한 300자에 가까우면 2건)만 실린다. E2 는 라인 상한 1,100자에서 머리글 75자를 뺀 1,025자가 result 이고 프레이밍 53자를 빼면 약 971자인데, 한 줄에 cid 가 머리와 글 끝에 두 번 찍혀 70~145자를 쓰며, 넘치는 줄부터 뒤는 전부 버리고 끝에 '…(N줄 생략)' 한 줄만 남긴다. 고르는 기준은 (층, −magnitude, cid)인데 rr_diff_events 에는 layer='semantic' 행만 들어가 층 키는 죽어 있고 magnitude 는 부호·단위를 가리지 않는 원값이라, 요소 수 증가(mesh.density_changed, design_relevant=0)나 MPa 증가가 맨 앞, 크기 값이 없는 파트 추가·삭제·계면·재료 변경이 가운데, 두께 감소·간극 축소 같은 음수 변화가 맨 뒤에서 가장 먼저 잘린다(메모리에서 compute_diff 를 돌려 +4000 요소, +0.2 mm, −0.2 mm 순서를 확인했다). 도메인·심각도·design_relevant 는 거름에도 정렬에도 쓰이지 않고 _item_e2·_item_e3·_item_e4 는 좌석을 받지 않으므로, 좌석이나 패널을 늘려도 전 좌석과 의장이 같은 상위 몇 건을 본다. E3(700)·E4(600) 칸에는 diff 타깃에서 실제 값이 실리지 않는데, brief.py 가 diff_json 최상위의 dims_delta·result_delta 와 base/target 필드를 찾지만 실제로는 parametric 아래에 before/after 로 있어 E3 는 '[명명 치수 없음 — rr_dim_defs 0건]', E4 는 '[dyna_result 부재]'(result_parity 가 false 면 '[result_parity=false — 정성만]')가 되고, 그렇게 남은 약 1,000자는 E0 만 빌려 쓴다. 다만 치수·결과가 아예 안 닿는 것은 아니어서, E1 요약(render.diff_summary_text 가 없어 diff.py 폴백이 만든다)에 [의미] 앞 5건(code·cid 순), [치수] 전 항목, [재료] 전 항목, [결과] 최대 5건이 실리고 2,000자에서 표식 없이 끊긴 뒤 result 1,584자로 다시 줄 단위 절단되며, 변한 치수·결과는 dim.named_changed·result.part_metric_shift 이벤트로 E2 경쟁에도 들어간다. 잘린 사실은 좌석과 의장이 같은 글의 '…(N줄 생략)' 으로 줄 수만 알 뿐 무엇이 빠졌는지는 모르고, 원장에는 그 글이 brief_gz 로 동결될 뿐 meta.dropped 는 0 고정이며 패널 quality 에는 evidence_dropped·user_memo_cut·engine_withheld 만 적히고, 전량은 rr_diff_events 와 rr_diffs.diff_json 에 그대로 남는다. G2 게이트 실패(대응 pending_n > 0 포함)나 capture_partial 이면 의미 이벤트가 0건이 되어 E2 는 '[의미·구조 이벤트 0건]' 이 된다. 지정 도구(diff 는 list_interfaces·interface_graph, 보고서가 1건 이상이면 report_part_risk, 2건 이상이면 compare_reports, 상한 6)는 엔진이 심의 전에 도구당 한 번 불러 도구당 2,000자·합 5,000자를 전 좌석과 의장이 함께 보는 것이고, 변경 이벤트를 나열하는 도구는 거기 없다. 자유 조회는 FREE_TOOLS=1·TOOL_BUDGET=3 이라 수렴 라운드를 뺀 라운드마다 좌석당 결과 3건(3라운드면 6건, 예산 게이트로 2라운드가 되면 3건)이 남고, 제 발언에는 호출당 900자·합 3,500자, 다른 좌석에는 공용 풀로 건당 420자까지 돈다. risk_get_diff(events 는 500건까지)는 heax-hwax_risk 가 apps 에 있어야 열리는데 러너는 heax-step_forge·heax-kooremapper_mcp 둘만 넘기므로 웹 러너 좌석은 부를 수 없고 MCP L2 경로는 좌석 도구 호출이 아예 없으며, 허용 접두사 compare_ 로 StepForge 의 compare_revisions·compare_snapshots 가 열릴 여지는 있으나 기준 과제의 소스 id 가 질문과 E0 에 실리지 않아 쓰기 어렵다(게이트웨이 매핑은 확인하지 못했다). 예산 면에서 11,000자·12건·항목 2,000자는 파이썬 엔진(웹 러너 경로)에서는 옛 값이고 지금은 120건·항목 150,000자·합 500,000자 천장에 실제 합계가 128K 창에서 17,967자이지만, MCP L2 가 쓰는 hwax-deliberate.js 에는 EV_MAX_ITEMS=12·EV_BUDGET=11000·EV_ITEM_MAX=2000 으로 그대로 살아 있어, 영역별로 더 실으려면 CAPS(합 10,600)와 128K 창의 여유 약 7,300자, JS 쪽 상한을 함께 고쳐야 한다.

### 바로잡은 것
- '좌석에 닿는 변경점 목록은 E2 한 칸의 5~12건뿐' 은 과장이다. E1 요약에도 변경 줄이 실린다 — [의미] 앞 5건(HWAXRisk/backend/app/diff.py:1608), [치수] 명명 치수 전 항목(변했든 아니든, diff.py:1613-1614), [재료] 전 항목(diff.py:1615-1616), [결과] 최대 5건(diff.py:1618-1620). E2 건수도 같은 식으로 다시 재면 2~13건이다(줄 70자 → 13건, 75자 → 12건, 121자 → 7건, 144자 → 6건, 347자 → 2건 — clip_lines 를 그대로 옮겨 계산).
- 'E4 는 늘 [dyna_result 부재]' 는 한 경우를 빠뜨렸다. comparability.result_parity 가 False 면 '[result_parity=false — 정성만]' 이 실린다(HWAXRisk/backend/app/brief.py:548-549). 어느 쪽이든 결과 값 자체는 E4 에 실리지 않는다는 결론은 그대로다.
- '치수·결과 변화가 몇 건이든 빈 문구' 는 E3·E4 두 칸에 한해서만 맞다. 변한 명명 치수는 dim.named_changed 이벤트(diff.py:1451)로, 결과 변화는 result.part_metric_shift 이벤트(diff.py:1486)로 rr_diff_events 에 들어가 E2 경쟁에 서고, E1 의 [치수]·[결과] 줄로도 간다. 비는 것은 '항목별 before→after 전용 표' 이지 치수·결과의 가시성 전체가 아니다.
- '11,000자·12건·항목 2,000자는 엔진의 옛 값' 은 절반만 맞다. 파이썬 엔진(HWAXAgentServer/deliberation.py:168-194, 웹 러너 경로)에서는 옛 값이지만, MCP L2 경로의 HWAXPortal/infra/pipeline/hwax-deliberate.js:228-230 에는 EV_MAX_ITEMS = 12 · EV_BUDGET = 11000 · EV_ITEM_MAX = 2000 이 지금도 걸려 있다. CAPS 만 올리면 MCP L2 경로에서 뒤쪽 항목이 통째로 빠진다(hwax-deliberate.js:242, 263). 파이썬 엔진의 종전 건수 상한은 12 가 아니라 40 이었다(deliberation.py:171).
- '자유 조회 결과는 그 좌석의 발언 프롬프트에만 실린다' 는 불완전하다. 결과는 공용 풀에도 들어가 다른 좌석이 건당 420자까지 받는다(deliberation.py:4569, _SHARE_ITEM_MAX :2749, 몫은 _share_budget :2767 — 128K 창에서 3,850자). 또 '좌석당 3회' 는 남기는 결과 수(calls[:budget], :3084)이고 ReAct 루프의 실제 한도는 recursion_limit = budget*2+5 다.
- claims 가운데 '패널 quality 에 옮겨 적는 손실은 항목 통째 탈락과 메모 절단뿐' 은 틀렸다. engine_withheld 도 같은 자리에 적는다(HWAXRisk/backend/app/runner.py:1361-1364). E2 의 줄 생략이 어디에도 구조화돼 남지 않는다는 결론은 맞다.

### 놓쳤던 사실
- E2 한 줄에 cid 가 두 번 찍힌다 — 이벤트 text 가 이미 ' [c:…]' 로 끝나는데(HWAXRisk/backend/app/diff.py:1235) 브리프가 머리에 '[c:…]' 를 또 붙인다(brief.py:502). 줄당 약 17자, 971자 몫에서 한두 건어치가 중복으로 나간다.
- E3·E4 가 diff 타깃에서 비워 두는 자리(E3 552자 + E4 455자 = 약 1,007자)는 E0 만 빌려 쓴다(brief.py:1362-1367). E2 는 제 상한 1,100자에 묶여 있어 남는 자리를 받지 못한다.
- 의미 이벤트가 통째로 0건이 되는 경로가 있다. G2 게이트 실패에는 대응 pending_n > 0 이 포함되고(diff.py:534) 그러면 _semantic 이 빈 목록을 돌려준다(diff.py:1241-1243). capture_parity 가 깨져도 events 를 비운다(diff.py:1545). 이때 E2 는 '[의미·구조 이벤트 0건]'(brief.py:504)이고 구조·파라메트릭 변화가 몇 건이든 좌석 목록에는 없다.
- 크기 값이 없는 이벤트의 자리 — 파트 추가·삭제·교체, 계면 추가·삭제, contact.*, part.material_changed, asm.rollup_changed 는 magnitude 가 None 이라(diff.py:1229 기본값) 정렬에서 0 이다. 양의 수치 변화가 12건만 넘어도 이들은 전부 잘린다. 반대로 같은 앱의 metrics.py:997 은 design_relevant = 1 AND excluded_reason IS NULL 로 거르므로, 거름 기준은 이미 원장에 있는데 E2 만 쓰지 않는다.
- 좌석은 전체 건수를 직접 받지 못한다. E0 에는 이벤트 통계가 없고(brief.py:420-429), E1 폴백 요약에는 구조 건수(+N파트 −N파트·계면 ±N, diff.py:1605)만 있고 stats.events 는 없다. 전체 건수는 E2 의 '실린 줄 + N줄 생략' 을 더해야만 안다.
- 영역별로 가를 재료는 원장에 있으나 도메인 열은 없다. rr_diff_events 에는 change_kind·subject_key·design_relevant 열과 색인이 있다(risk_store.py:208-219). 좌석 도메인(mech·sim·material …)과 이벤트를 잇는 대응표는 코드에 없고, 좌석 계약(assets/seat-contract.v1.json)은 도메인별로 '현재 상태' 조회 도구를 지정할 뿐 변경 목록을 가르지 않는다.
- 엔진 쪽 여유는 생각보다 작다. 128K 창에서 근거 합계 예산은 17,967자이고 브리프 Σ CAPS 는 10,600자라 남는 것은 약 7,300자다. 창이 약 117K 토큰보다 작으면 지금 브리프도 뒤쪽 항목부터 통째로 빠지고(deliberation.py:4236-4238), dev 16K 창은 바닥값 2,000자라 E0 뒤가 거의 다 빠진다. 운영 GLM 의 창 값은 확인하지 못했다.
- 조회 단계의 좌석은 브리프 전체를 보고 도구를 고르지 않는다. 1라운드는 base 앞 4,000자, 그 뒤는 직전 라운드 전사 끝 4,000자만 받는다(HWAXAgentServer/deliberation.py:4487). 질문에 실리는 'diff 요약 첫 줄' 은 summary_text 앞 200자(runner.py:358)인데 폴백 요약의 첫 줄은 '[대상] base … ir_hash=…' 머리줄이라 변경 내용이 없다. 좌석 발굴 질의도 summary_text 앞 500자다(roster.py:21).
- 도구로 변경을 더 볼 수 있는 열린 접두사가 하나 있다. _FREE_ALLOW 에 'compare_' 가 있고(deliberation.py:2605) 러너가 heax-step_forge 를 apps 로 넘기므로, StepForge 의 compare_revisions·compare_snapshots(StepForge/app/mcp_server.py:4633, 5489, 기본 limit 100)는 자유 조회 후보에 남을 수 있다. 다만 기준 과제의 소스 id 는 질문(runner.py:361-372, target 과제 소스만)에도 E0(target 스냅샷 소스만)에도 실리지 않아 좌석이 두 과제 id 를 맞춰 부르기 어렵다. 게이트웨이 /tools-map 의 실제 매핑과 좌석별 도구 선정(_tools_for_seat) 결과는 확인하지 못했다.

### 확인된 코드 근거(파일:줄 — 인용)
- 브리프 전체 예산은 11,000자다(엔진 누적 예산으로 가정한 값). — `HWAXRisk/backend/app/brief.py:18` — `ENGINE_BUDGET = 11000`
- 브리프 항목 수 상한은 12건이다. — `HWAXRisk/backend/app/brief.py:19` — `EVIDENCE_MAX_ITEMS = 12`
- 항목 result 는 2,000자, args 는 400자로 클램프한다. — `HWAXRisk/backend/app/brief.py:16` — `CLAMP_SOURCE, CLAMP_TOOL, CLAMP_ARGS, CLAMP_RESULT = 120, 80, 400, 2000`
- 항목별 라인 상한은 E1 1650 · E2 1100 · E3 700 · E4 600 이다(머리글 포함 라인 길이 기준). — `HWAXRisk/backend/app/brief.py:29` — `"E0": 500, "E0c": 1000, "E1": 1650, "E2": 1100, "E3": 700, "E4": 600,`
- 항목마다 result 를 min(2000, CAP − 머리글 길이) 로 줄 단위 절단한다. E2 는 diff id 가 hex 32자라 머리글 75자 → result 1,025자다(산술은 이 식을 그대로 옮겨 계산). — `HWAXRisk/backend/app/brief.py:1357` — `item["result"] = clip_lines(item["result"], min(CLAMP_RESULT, cap - line_overhead(item)))`
- 절단은 줄 경계에서 하고, 넘치는 줄부터 뒤를 전부 버린다. — `HWAXRisk/backend/app/brief.py:105` — `한 줄이 남은 자리를 넘으면 그 줄부터 통째로 뺀다 — 참조 id 가 잘린 채 실리지 않게 한다.`
- 잘린 줄 수는 본문 끝에 '…(n줄 생략)' 한 줄로만 남는다(무엇이 빠졌는지는 적지 않는다). — `HWAXRisk/backend/app/brief.py:99` — `return f"…({n}줄 생략)"`
- E2 는 rr_diff_events 에서 semantic·structural 층만 읽는다(parametric 층 제외, 도메인·심각도·design_relevant 조건 없음). — `HWAXRisk/backend/app/brief.py:481` — `"WHERE diff_id = ? AND layer IN ('semantic','structural')",`
- E2 정렬 키는 (층 순서, −magnitude, cid) 이고 magnitude 는 부호·단위를 가리지 않는 원값이다 — 양의 큰 값이 앞, None 은 0, 음수(감소)는 맨 뒤다. — `HWAXRisk/backend/app/brief.py:487` — `-(r["magnitude"] if isinstance(r["magnitude"], (int, float)) else 0.0),`
- 층 순서는 semantic 0 → structural 1 → parametric 2 로 정의돼 있다. — `HWAXRisk/backend/app/brief.py:469` — `_LAYER_ORDER = {"semantic": 0, "structural": 1, "parametric": 2}`
- E2 한 줄의 모양은 '[c:cid] code «text» conf=…' 이다. — `HWAXRisk/backend/app/brief.py:502` — `lines.append(f"[{ref}] {_s(row['code'])} {text} conf={_s(row['confidence'], '-')}{tail}")`
- rr_diff_events 에는 layer='semantic' 행만 들어간다 — E2 의 structural 조건과 층 정렬 키는 실제로는 작동하지 않는다. — `HWAXRisk/backend/app/diff.py:1748` — `diff_id, event["cid"], owner_sub, "semantic", event["code"], event["change_kind"],`
- 구조·파라메트릭 항목은 펼침 표가 아니라 diff_json 안에만 남는다. — `HWAXRisk/backend/app/diff.py:1744` — `"""의미 이벤트를 펼침 표 행으로 편다(구조·파라메트릭 항목은 diff_json 안에만 산다)."""`
- 이벤트 magnitude 의 원천인 delta 는 after − before 의 부호 있는 값이다(얇아지면 음수). — `HWAXRisk/backend/app/diff.py:399` — `delta = a - b`
- 설계 관련성이 없는 메시 밀도 이벤트(design_relevant=False, magnitude 는 요소 수 변화)도 같은 표에 들어가 E2 정렬에서 함께 경쟁한다. — `HWAXRisk/backend/app/diff.py:1400` — `derived_from=[n_elems["cid"]], confidence=conf, design_relevant=False,`
- E2 이벤트 글은 'note' 종류로 위생 처리되어 300자까지 허용된다(한 줄이 길면 실리는 건수가 더 준다). — `HWAXRisk/backend/app/render.py:113` — `"label": 120, "note": 300, "title": 200, "message": 350,`
- E3 는 diff_json 최상위에서 dims_delta 를 찾는다. — `HWAXRisk/backend/app/brief.py:514` — `for item in _j(ctx["diff"]["diff_json"], {}).get("dims_delta") or []:`
- 그러나 dims_delta·result_delta 는 parametric 딕셔너리 안에 만들어진다. — `HWAXRisk/backend/app/diff.py:1017` — `"dims_delta": dims_delta, "result_delta": result_delta, "rollup_delta": rollup_delta}`
- diff 봉투는 그 딕셔너리를 'parametric' 키 아래에 싣고, 그 봉투 전체가 diff_json 으로 저장된다(최상위에 dims_delta 없음). — `HWAXRisk/backend/app/diff.py:590` — `"parametric": parametric,`
- rr_diffs.diff_json 의 유일한 기록 지점은 봉투 전체를 canonical_json 으로 넣는다. — `HWAXRisk/backend/app/diff.py:1730` — `kind, DIFF_VERSION, canonical_json(diff), diff["summary_text"], diff["summary_status"],`
- E3 는 항목에서 base·target 필드를 읽는데 diff 항목의 필드 이름은 before·after 다(경로가 맞아도 값이 '미측정' 으로 찍힌다). — `HWAXRisk/backend/app/brief.py:520` — `f"[d:{_ref_name(item.get('name'))}] {_s(item.get('base'), '미측정')}"`
- diff 파라메트릭 항목의 실제 필드는 before·after 다. — `HWAXRisk/backend/app/diff.py:430` — `"before": before, "after": after,`
- E3 는 줄이 0개면 '명명 치수 없음' 문구를 싣는다 — diff 타깃에서는 위 경로 불일치로 늘 이 문구가 된다. — `HWAXRisk/backend/app/brief.py:537` — `lines = ["[명명 치수 없음 — rr_dim_defs 0건]"]`
- E4 도 diff_json 최상위에서 result_delta 를 찾는다. — `HWAXRisk/backend/app/brief.py:551` — `for item in _j(ctx["diff"]["diff_json"], {}).get("result_delta") or []:`
- E4 는 줄이 0개면 'dyna_result 부재' 문구를 싣는다. — `HWAXRisk/backend/app/brief.py:570` — `lines = ["[dyna_result 부재]"]`
- E2~E4 조립 함수는 좌석·패널을 인자로 받지 않는다 — 타깃 하나에 같은 내용이다. — `HWAXRisk/backend/app/brief.py:1327` — `_item_e2(store, ctx),`
- diff 요약(E1 원천)은 render.diff_summary_text 를 찾지만 render.py 에 그 이름의 함수가 없어 diff.py 의 최소 표기 폴백이 돈다. — `HWAXRisk/backend/app/diff.py:1586` — `builder = getattr(render, "diff_summary_text", None) if render is not None else None`
- 폴백 요약은 의미 이벤트를 앞 5건만 싣는다. — `HWAXRisk/backend/app/diff.py:1608` — `for event in diff["semantic"]["events"][:5]:`
- 그 5건의 순서는 (code, cid) 정렬이다 — 크기·심각도 순이 아니다. — `HWAXRisk/backend/app/diff.py:1498` — `events.sort(key=lambda e: (e["code"], e["cid"]))`
- 폴백 요약은 2,000자에서 표식 없이 끊는다. — `HWAXRisk/backend/app/diff.py:1628` — `return (text[:2000], "ok")`
- '… 외 N건' 을 남기는 섹션 요약기는 render.py 에 있으나 이름이 summarize/_summarize_diff 라 diff.py 의 조회에 걸리지 않는다. — `HWAXRisk/backend/app/render.py:736` — `body = " · ".join(texts) + (f" · … 외 {extra}건" if extra > 0 else "")`
- 러너의 칸 수 상한은 12 다. — `HWAXRisk/backend/app/planner.py:27` — `MAX_EVIDENCE = 12`
- fit_evidence_slots 는 12칸 이하면 아무것도 빼지 않는다(E0~E9+E0c+M 이 정확히 12칸이라 E2~E4 는 칸 맞춤으로 빠지지 않는다). — `HWAXRisk/backend/app/runner.py:389` — `if len(items) <= planner.MAX_EVIDENCE:`
- 브리프 meta 의 dropped 는 0 으로 고정이다 — 줄 단위 절단 건수는 구조화된 값으로 남지 않는다. — `HWAXRisk/backend/app/brief.py:1387` — `"dropped": 0,`
- 패널 quality 에 옮겨 적는 손실은 항목 통째 탈락과 메모 절단뿐이다(E2 의 줄 생략은 대상이 아니다). — `HWAXRisk/backend/app/runner.py:1357` — `for lost in ("evidence_dropped", "user_memo_cut"):`
- 패널이 실제로 받은 근거 전문(절단 표식 포함)은 brief_gz 로 동결되어 원장에 남는다. — `HWAXRisk/backend/app/runner.py:500` — `"UPDATE rr_panels SET brief_gz = ?, brief_hash = ?, brief_item_hashes_json = ? WHERE id = ?",`
- 엔진은 근거 블록을 좌석 공통 프롬프트(base)의 꼬리에 싣는다. — `HWAXAgentServer/deliberation.py:4317` — `+ (f"\n{chat_ev_inject}" if chat_ev_inject else "") + chat_ctx_inject`
- 의장 프롬프트도 같은 base 로 시작하므로 의장도 같은 근거 글(생략 표식 포함)을 본다. — `HWAXAgentServer/deliberation.py:4798` — `chair_human = base + f"\n{rounds_block}\n\n" + chair_tail`
- diff 타깃의 지정 도구는 list_interfaces·interface_graph 가 기본이다. — `HWAXRisk/backend/app/planner.py:266` — `tools = ["list_interfaces", "interface_graph"]`
- 보고서가 2건 이상이면 compare_reports 가 더해진다(1건 이상이면 report_part_risk). — `HWAXRisk/backend/app/planner.py:270` — `tools.append("compare_reports")`
- 지정 도구 수 상한은 6 이다. — `HWAXRisk/backend/app/planner.py:25` — `MAX_TOOLS = 6`
- 엔진은 지정 도구 결과를 도구당 2,000자·합 5,000자로 좌석에 싣는다(심의 전 사전 호출, 전 좌석 공용). — `HWAXAgentServer/deliberation.py:109` — `_TOOL_CHUNK_MAX, _TOOL_INJECT_MAX = 2000, 5000`
- 지정 도구는 도구마다 1회 호출이다(LLM 이 인자를 짜서). — `HWAXAgentServer/deliberation.py:3910` — `+ "\n주제의 정량 분석에 맞게 이 도구를 1회 호출할 인자 JSON 을 출력하라. "`
- 리스크 앱의 자유 조회 스위치 값은 1 이다. — `HWAXRisk/backend/app/planner.py:23` — `FREE_TOOLS = 1`
- 좌석당 자유 조회 호출 상한으로 3 을 보낸다. — `HWAXRisk/backend/app/planner.py:24` — `TOOL_BUDGET = 3`
- 러너는 그 두 값을 delib_opts 에 그대로 싣는다. — `HWAXRisk/backend/app/runner.py:444` — `"tool_budget": planner.TOOL_BUDGET,`
- 엔진은 tool_budget 을 1~6 으로 죄고 '1인당 호출 상한' 으로 쓴다. — `HWAXAgentServer/deliberation.py:1094` — `o.tool_budget = max(1, min(6, o.tool_budget))        # 자유 조회 1인당 호출 상한`
- 자유 조회는 수렴 라운드를 뺀 매 라운드 발언 전에 돈다. — `HWAXAgentServer/deliberation.py:4486` — `if g_agent is not None and kind != "converge":`
- 라운드 성격은 1=initial, 마지막=converge, 그 사이=deepen 이다(3라운드면 조회 가능한 라운드는 둘). — `HWAXAgentServer/deliberation.py:4339` — `return "initial" if r == 1 else "converge" if r == N else "deepen"`
- 패널 라운드 수 기본은 3 이다. — `HWAXRisk/backend/app/planner.py:22` — `ROUNDS = 3`
- 한 라운드의 한 좌석 호출은 budget 개로 자른다. — `HWAXAgentServer/deliberation.py:3084` — `calls = calls[:budget]`
- 자유 조회 결과는 호출당 900자·블록 합 3,500자까지만 그 좌석 발언 프롬프트에 실린다. — `HWAXAgentServer/deliberation.py:3098` — `block = "\n".join(f"- {n}({ap}): {b[:900]}" for n, ap, b in good)[:3500]`
- risk_get_diff 는 MCP 도구로 있고 events 는 500건까지 준다. — `HWAXRisk/backend/app/mcp_server.py:151` — `"""diff 조회(part ∈ diff|summary|events, events 는 ≤500 + truncated)."""`
- 이벤트 조회 상한 상수는 500 이다. — `HWAXRisk/backend/app/mcp_server.py:38` — `EVENT_LIMIT = 500`
- 엔진은 risk_get_diff 를 heax-hwax_risk 앱의 읽기 도구로 등록해 두었다. — `HWAXAgentServer/deliberation.py:732` — `"heax-hwax_risk": ("risk_get_snapshot", "risk_get_diff", "risk_get_registry",`
- 그 도구는 소속 앱이 요청의 apps 에 들어 있을 때만 열린다. — `HWAXAgentServer/deliberation.py:3757` — `or (_amap.get(n) in _apps and n in _RISK_READ_TOOLS.get(_amap.get(n), ()))`
- 자유 조회 접두사 허용 목록에 'risk_' 는 없다. — `HWAXAgentServer/deliberation.py:2604` — `_FREE_ALLOW = ("list_", "get_", "search_", "find_", "query_", "compute_", "analyze_",`
- 러너가 넘기는 apps 는 어댑터 레지스트리의 앱키뿐이고 최대 3개다. — `HWAXRisk/backend/app/runner.py:310` — `return keys[:planner.MAX_APPS]`
- 어댑터 앱키는 heax-step_forge 와 heax-kooremapper_mcp 이고 heax-hwax_risk 는 없다. — `HWAXRisk/backend/app/adapters/registry.py:27` — `IrAdapter(kind="mcad", app_key="heax-step_forge", status="planned"),`
- MCP L2 경로(hwax-risk-review)는 좌석 도구 호출이 아예 없다. — `HWAXPortal/infra/pipeline/hwax-risk-review.js:11` — `// 이 경로의 등급은 evidence_only 다. hwax-deliberate.js 에는 좌석 도구 호출 경로(free_tools·tools·`
- 엔진의 근거 건수 상한은 지금 120 이다. — `HWAXAgentServer/deliberation.py:175` — `_EVID_ITEMS = _env_int("DELIB_EVID_ITEMS", 120)           # 근거 항목 수 상한`
- 엔진의 항목당 천장은 150,000자다. — `HWAXAgentServer/deliberation.py:176` — `_EVID_ITEM_MAX = _env_int("DELIB_EVID_ITEM_MAX", 150000)  # 항목당 **천장**(자) — 큰 발표자료 한 건`
- 엔진의 합계 천장은 500,000자다. — `HWAXAgentServer/deliberation.py:194` — `_EVID_BUDGET = _env_int("DELIB_EVID_BUDGET", 500000)      # 주입 합계 **천장**(자) — 1M 창 기준`
- 브리프가 박아 둔 2,000자·11,000자는 엔진의 종전 값이다. — `HWAXAgentServer/deliberation.py:168` — `# 종전 값(항목 2,000자 · 합계 11,000자)은 챗 도구결과 몇 건을 나르려고 잡은 것이라, 발표자료나`
- 엔진의 실제 합계 예산은 모델 컨텍스트에서 유도한 값과 천장 중 작은 쪽이다. — `HWAXAgentServer/deliberation.py:234` — `return min(_EVID_BUDGET, max(2000, int(_pre_budget() * (1.0 - _CHAT_CTX_SHARE))))`
- 포털 스키마도 근거를 120건까지 받는다. — `HWAXPortal/backend/app/agent/routes.py:146` — `evidence: list[dict] | None = Field(default=None, max_length=120)`

### 확인하지 못한 것
- 운영 DB 의 실제 diff 행으로 브리프를 조립해 보지는 않았다. dev 의 HWAXRisk/data/risk_review.db 에는 rr_diffs 가 0건이었다. E3·E4 가 늘 빈 문구라는 것은 양쪽 코드 판독과 메모리 안 compute_diff 실행(최상위 키에 dims_delta 없음, render.diff_summary_text 없음 확인)에 근거한다.
- E2 에 실리는 5~12건은 brief.py 의 식(clip_lines·line_overhead)을 그대로 옮겨, 줄 길이 77·123·161자를 가정해 계산한 값이다. 실제 부품명·경로 길이에 따라 달라지고 이벤트 글 상한(300자)에 가까우면 2~3건까지 줄 수 있다.
- 게이트웨이의 도구→앱 매핑(_app_of_tools) 실값은 네트워크 금지라 보지 않았다. 웹 러너 경로에서 좌석이 risk_get_diff 를 못 부른다는 것은 엔진 조건식과 러너가 넘기는 apps 를 읽어 내린 결론이고, 실심의 로그로 확인한 것이 아니다.
- 엔진의 실제 근거 예산(_evid_budget)은 운영 모델(GLM)의 컨텍스트 창 값에 달려 있어 확정하지 못했다. 128K 창 17,967자·200K 창 67,183자는 코드 식에 기본값(_SEAT_CTX 48000·예약 56000·안전 0.93·챗 몫 0.3)을 넣은 산술이고 env 로 바뀔 수 있다.
- 자유 조회에서 좌석 ReAct 에이전트가 도구 결과를 몇 자까지 직접 읽는지(_free_result_chars)는 모델 창과 TOOL_RESULT_MAX(기본 200000)에 달려 있어 숫자를 확정하지 못했다. 확정한 것은 발언 프롬프트에 실리는 몫(호출당 900자·합 3,500자)이다.
- 리스크 앱 화면이 '…(N줄 생략)' 을 사람에게 따로 강조해 보여 주는지는 프론트엔드를 읽지 않아 확인하지 못했다.
- 예산 게이트(panel_budget)가 라운드를 2로 줄이는 경우(est_high > HWAXRISK_PANEL_LLM_CAP 기본 120)에는 조회 가능한 라운드가 하나라 좌석당 최대 3회가 된다. 기본 편성(6석·3라운드·도구 4개)은 est_high 95 라 3라운드가 유지되는 것으로 계산했으나 운영 설정값은 확인하지 못했다.


