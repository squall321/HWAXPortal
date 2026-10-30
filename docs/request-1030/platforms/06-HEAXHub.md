# 06 HEAXHub(DocForge) — 10-30 요청에서 할 일

- **받는 곳** — DocForge 세션 `docforge-f6`(이 박스 `~/claude/DocForge`). HEAXHub 리포(`~/claude/HEAXHub`)는 DocForge 의 등록 사본(`integrations/doc-forge/.portal/manifest.yaml`)만 든다. 이 행으로 HEAXHub 앞에 따로 보낸 것은 없고, 등록 사본의 판 줄을 고치는 일은 DocForge 배치 묶음에 든다('끝나면' 1).
- **어떻게 갔나** — 10-30 KST 포털 세션 `hwaxportal-a5` 가 SendMessage 로 행을 정본 글 그대로 보냈다(덧붙인 것 — HA-28 이 읽을 docforge_status 의 끝 · 도는 중 칸, 새 목록 도구에 readOnlyHint). 같은 날 답을 받았다. 코드는 끝났고 배치는 그 세션의 사용자 승인 대기다(아래 인용 — [`../outbound.md`](../outbound.md) 1절 표의 '답' 칸 그대로).
- **요청서 정본** — [`../../request_261030.md`](../../request_261030.md) 4절 '박스 밖 플랫폼' 의 HH-14 행. 이 행을 가리키는 7절 '다시 볼 시험' 줄은 DW-10 이고, 맞물린 우리 몫은 5절 OB-94 · OB-102 다. 요청서 머리는 HEAXHub(DocForge)를 update-all 로 받는 플랫폼('예')으로 적었다. 같은 요청의 계획 · 판단 · 체크리스트는 [`../PLAN.md`](../PLAN.md) · [`../context-notes.md`](../context-notes.md) · [`../checklist.md`](../checklist.md) 다.
- **cae00 기준 판** — 요청서에 없다(머리의 기준 판과 끝 절의 cae00 HEAD 목록 어디에도 DocForge 가 없다). 그래서 이 박스 HEAD 와 대조했다. DocForge 답과 DocForge `docs/START.md:26` 은 cae00 이 받는 배치 판을 release `3ba0f6f`(0.3.0 · beta — HEAXHub 등록 사본 `5e48b25`)로 적었고, 이 박스의 `origin/release` 도 `3ba0f6f` 다. DW-10 이 본 도구 다섯도 `3ba0f6f` 의 도구 다섯과 같다. cae00 에 실제로 떠 있는 판은 대조 못 함(이 시트는 이 박스의 git · grep · ls 만 썼다).
- **이 박스(dev)에서 대조한 판** — DocForge `559ec87`(main = origin/main, 작업 트리에 고친 파일 0 — `ab5547e` 뒤로는 `docs/checklist.md` 한 줄뿐) · HEAXHub `5e48b25`(main = origin/main) · 포털 `bf5cd94` · 게이트웨이 `67d8d00` · 에이전트 서버 `7ca3a2e` · 대조 시각 2026-10-30 18:04 KST.

> 받은 답(`outbound.md` 그대로) — 10-30 끝 — DocForge main `e72cbe5`(도구) · `ab5547e`(판 0.3.1), **배치(release · HEAXHub 등록 사본 · SIF · Drive)는 그 세션의 사용자 승인 대기**(cae00 release 는 아직 `3ba0f6f` 0.3.0). ① 새 도구 `docforge_list_inputs()`(인자 없음 · readOnlyHint) — 운영자 입력 상자(SIF `/data/inbox`, 호스트 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/`)와 바로 밑 폴더, 응답 `{root, root_host, total, truncated, files:[{path, name, folder, bytes, format, modified}]}` 새것부터 200개, `files[].path` 를 convert 에 그대로. 업로드 스테이징은 나열하지 않음(남의 파일 이름이 보여서 — 요청과 다른 점, 근거 DocForge R-D47). ② docforge_status — `status` queued · running / done · failed · cancelled, `progress` 0 ~ 100, `stage` S0 ~ S7, `error`; **도구 오류는 `{ok:false, error, status:403}` 처럼 `status` 가 숫자 — 숫자면 기다리기를 끝낸다**, 잡은 한 번에 하나라 queued 는 앞 잡 대기. ③ readOnlyHint 는 읽기 넷(capabilities · list_inputs · status · package)에만. ④ 페르소나 `he-doc-docforge` 고침 셋(key_tools 에 list_inputs · can 의 맡기기 줄 · pitfalls 의 path 줄)은 **0.3.1 이 cae00 게이트웨이에 실린 뒤**(동기화가 없는 도구 이름에서 멈춘다 — 판단 C-8). ⑤ cae00 사람 몫 — 새 박스 값 없음, 0.3.1 받은 뒤 `/apps/doc_forge/api/v1/capabilities` version 0.3.1 · 게이트웨이 `/refresh` 뒤 `docforge_*` 여섯, OB-94 시험 파일은 위 상자에 평문 pptx 하나, dev 상자는 비워 둔다(build-all 이 dev 앱 데이터를 cae00 에 심는다)

## 할 일

### HH-14 · 중간 — 입력 뿌리의 파일을 고를 읽기 도구

- **대상** — HEAXHub DocForge
- **무엇이** — 입력 뿌리의 파일을 볼 도구가 없어 운영자가 변환할 파일을 고르지 못한다.
- **근거** — DW-10 — 도구 5개(convert · status · package · capabilities · cancel)뿐이고, 경로 '/' 접수는 '허용된 입력 뿌리 밖' 이었다.
- **할 일** — 입력 뿌리의 파일 목록(이름 · 크기 · 형식 · 수정 시각, 하위 폴더 한 단계)을 주는 읽기 도구를 더한다.
- **다시 볼 시험** — 4절 표에는 이 칸이 없다. 7절 표에서 이 행을 가리키는 줄(정본 그대로)은 아래와 같다.
  - 시험 — DW-10
  - 언제 — HH-14 뒤
  - 볼 것 — 입력 파일을 골라 변환까지 한다.

#### 지금 판에서의 자리

줄 번호는 DocForge `ab5547e` 의 것이다(코드는 HEAD `559ec87` 과 같다). 행이 `파일:줄` 을 들지 않아, 행이 이름 댄 것(도구 다섯 · '허용된 입력 뿌리 밖' 거절 · 목록 도구)을 코드에서 찾았다. 비교의 아래 끝은 배치 판 `3ba0f6f` 다.

- **이미 고쳤다 — `e72cbe5`(10-30 17:48 KST)가 도구를, `ab5547e`(17:49 KST)가 판 0.3.1 을 올렸다. 배치는 아직이다.** `3ba0f6f..559ec87` 사이 커밋은 이 둘과 체크리스트 한 줄(`559ec87`)뿐이다(`git rev-list` · `git log`).
- **근거 대조 — `3ba0f6f`(0.3.0).** 도구는 표지 없는 `@mcp.tool()` 다섯이다 — `docforge/mcp_server.py` capabilities `:46-47` · convert `:52-53` · status `:66-67` · package `:72-73` · cancel `:78-79`. DW-10 의 다섯과 같다. 경로 '/' 거절은 `docforge/service.py:40-41`(`submit_path` — `"허용된 입력 뿌리 밖의 경로다"`, 403)이다. 바로 앞 `:37-38` 은 `DOCFORGE_INPUT_ROOTS` 가 비면 '경로 입력이 닫혀 있다' 로 먼저 거절한다. 그러니 DW-10 이 뿌리 밖 문구를 받았다면 그때 cae00 의 `DOCFORGE_INPUT_ROOTS` 는 비어 있지 않았다(코드로 본 추론 — cae00 값은 대조 못 함). DW-10 보고서(`qa-digital-worker/QA-DIGITAL-WORKER-20261030.md`)는 cae00 문서라 이 박스에 없어, 근거 글은 요청서 글로만 대조했다.
- **새 도구 `docforge_list_inputs()`(인자 없음).** 등록은 `docforge/mcp_server.py:57-62`, 본체는 `docforge/service.py:56-83`(`list_inputs`)이다. 운영자 입력 상자 `config.inbox_dir()` = `<데이터>/inbox`(`docforge/config.py:165-167`, 기동 때 `ensure_dirs` `:170-176` 이 만든다)와 그 바로 밑 폴더의 파일을 새것부터 `LIST_MAX` 200개(`service.py:52`)까지 준다. 칸은 `root` · `root_host` · `total` · `truncated` · `files[]`(`path` · `name` · `folder` · `bytes` · `format` · `modified`)다 — 요청의 이름 · 크기 · 형식 · 수정 시각 · 하위 폴더 한 단계가 다 있다. 숨김 · Office 잠금(`_HIDDEN`, `:53`) · 더 깊은 폴더 · 상자 밖을 가리키는 링크는 싣지 않는다.
- **맡기기 길.** `submit_path`(`service.py:38-45`)가 상자를 늘 입력 뿌리로 받고(`:41`), 거절 문구가 목록 도구를 가리킨다(`:42` — `"허용된 입력 뿌리 밖의 경로다 — 고를 수 있는 파일은 docforge_list_inputs 로 본다"`). `3ba0f6f` 의 '뿌리가 비면 닫혀 있다' 거절(`:37-38`)은 없어졌다 — 상자 길은 `DOCFORGE_INPUT_ROOTS` 가 비어도 열린다.
- **readOnlyHint.** `_READ`(`mcp_server.py:48`)를 capabilities `:51` · list_inputs `:57` · status `:79` · package `:85` 에 달았다. convert(`:65`) · cancel(`:91`)에는 표지가 없다.
- **시험.** `tests/test_app.py:35`(도구 여섯 · 읽기 넷에만 readOnlyHint) · `:99`(목록 — 바로 밑 폴더까지 · 새것부터 · 숨김 · 잠금 · 깊은 폴더 · 링크 빼기 · 상한) · `:135`(목록의 path 맡기기, '/' 와 상자 밖은 403 이고 문구에 docforge_list_inputs)다. 커밋 글은 '시험 276 통과' 라 적었다 — 이 시트는 시험을 돌리지 않았다.
- **요청과 다른 점 — 목록은 운영자 상자만 보인다.** 요청은 '입력 뿌리의 파일 목록' 인데 `DOCFORGE_INPUT_ROOTS`(cae00 에서는 포털 업로드 스테이징)는 나열하지 않는다. 안이 `<사용자>/<상자>/<파일>` 이라 남이 챗에 올린 파일 이름이 보이기 때문이라고 DocForge 판단 R-D47(DocForge `docs/context-notes.md:317`)이 적었고, 답에서도 '요청과 다른 점' 으로 밝혔다. 목록은 부른 사람을 보지 않는다(인자 · 호출 문맥 없음) — DocForge 도구가 열린 사람은 모두 같은 목록을 본다.
- **배치 자리 — 아직 0.3.0 이다.** `origin/release` 는 `3ba0f6f` 다. HEAXHub 등록 사본 `integrations/doc-forge/.portal/manifest.yaml:5` 는 `version: 0.3.0`(`5e48b25`, 그 폴더의 작업 트리도 깨끗하다)이고, DocForge HEAD 의 `.portal/manifest.yaml` 과는 이 판 줄 하나만 다르다. 이 박스 dev 허브의 `var/sifs/doc-forge.sif` 는 10-27 23:22(박스 시각 UTC)에 지은 것이라 10-30 커밋이 들 수 없다. DocForge `docs/checklist.md:84-85` 의 '0.3.1 배치(사람 승인 — release · HEAXHub 등록 사본 · SIF · Drive)' 는 열려 있다. Drive 의 doc-forge 판은 대조 못 함(Drive 를 읽지 않았다).
- **docforge_status 칸(HA-28 이 읽을 것).** `service.status`(`service.py:119-122`)가 `id` · `status` · `stage` · `progress` · `error` · `source_name` · `created_at` · `started_at` · `finished_at` 을 준다. 상태 값은 `docforge/jobs/ledger.py:15` 의 다섯(queued · running · done · failed · cancelled)이고, done 이면 progress 가 100 이 된다(`ledger.py:119`). 도구 오류는 `_guard`(`mcp_server.py:41-45`)가 `{"ok": False, "error": …, "status": <HTTP 숫자>}` 로 돌려준다 — 같은 `status` 칸이 숫자가 된다. 이 칸들은 `3ba0f6f` 와 같다(`e72cbe5` 는 status 에 표지만 달았다).

#### 우리 쪽 맞물림

이 요청의 우리 리포 행은 포털 세션 `hwaxportal-a5` 가 지금 고치는 중이다. 아래는 계획이고 아직 들어가지 않았다.

- **HA-28(에이전트 서버)** — 할 일 칸이 docforge_status 를 상태 조회 도구로 이름 짚었다. 에이전트가 코드로 간격 · 상한까지 기다렸다가 끝났거나 상한에 닿은 결과만 LLM 에 넘기고, 기다리는 동안 화면에 진행률을 흘리게 고치는 중이다. 읽는 기준은 답 ②다 — queued · running 이면 도는 중, done · failed · cancelled 면 끝, `status` 가 숫자면 도구 오류라 기다리기를 끝낸다. 잡은 한 번에 하나(HEAXHub 등록 사본 `manifest.yaml:31` `DOCFORGE_MAX_JOBS: "1"`)라 queued 는 앞 잡을 기다리는 중이고, 앞 잡이 길면 상한에 닿을 수 있다. 이 박스 에이전트 서버 main `7ca3a2e` 에는 아직 없다 — 높음 넷(HA-27 ~ HA-30)은 설계가 먼저다([`../PLAN.md`](../PLAN.md) '어떻게 하나' 1). 포털 업로드 길은 이미 코드가 docforge_status 를 본다(화면이 1.5초마다 — 포털 `backend/app/agent/docforge_delivery.py:6`). HA-28 은 챗 에이전트가 부르는 길이다.
- **HA-29(에이전트 서버)** — 할 일 칸이 잡을 시작하는 도구로 docforge_convert 를 이름 짚었고, 사람이 시키지 않았으면 코드 단에서 확인 카드로 멈추게 고치는 중이다. 운영자 정의 `he-doc-docforge` 의 `writes` 에도 이미 있다(포털 `infra/personas/he-team.json:560`, confirm 은 docforge_cancel `:561` — 이 파일은 `aec8e29` 뒤 바뀌지 않았다). HP-53 이 채우는 운영자 목록(요청서 끝 절)에 이 운영자는 없다 — 이미 차 있다. docforge_convert 에는 MCP 표지가 없고, 이름의 'convert' 는 게이트웨이 쓰기 이름 꼴(`_WRITE_NAME`, 게이트웨이 `gateway.py:2938-2941`)에도 없다. 그래서 관문이 표지나 이름 꼴만 보면 놓치고, 이름 목록이나 `writes` 로는 잡힌다. DocForge 에는 시작 전 작업량을 세는 도구가 없다 — 확인 문구에 실을 만한 것은 목록이 주는 파일의 `bytes` · `format` 이다. DocForge 는 'HA-29 관문이 readOnlyHint 를 먼저 본다' 고 보고 표지를 달았다(R-D47). 관문이 표지를 읽을지는 HA-29 설계가 정한다 — 에이전트 서버 main 의 `app.py` 에 readOnlyHint 를 읽는 코드는 아직 0건이다(`git grep`).
- **분석 루틴 울타리(게이트웨이 main `67d8d00` — cae00 기준 판 `44f4b8d` 뒤의 R3, 이 요청서의 행은 아니다)** — `_routine_read`(`gateway.py:4703-4719`)는 박스 닫기 목록에 없고 readOnlyHint=True 면 연다. 그래서 0.3.1 에서 표지를 단 읽기 넷은 루틴 단계에서 열리고, docforge_convert 는 '표지 없는 잡 시작' 으로 막힌다(`gateway.py:4625-4627` 주석 · `test_gateway.py:9040`). 도구 영역은 앱 줄(`tool_areas.json:43` `"heax-doc_forge": "report"`)이라 새 도구도 같은 영역에 든다.
- **HG-22(게이트웨이)** — 할 일 칸은 '메일 꼴 · 사내 계정 꼴(영문.영문숫자)과 사설 IP 꼴(10.x · 172.16-31.x · 192.168.x)은 칸 이름과 상관없이 가린다' 이고, 그렇게 고치는 중이다. 목록의 `name` · `path`(예 `deck.pptx` · `/data/inbox/deck.pptx`)는 '영문.영문숫자' 꼴과 닮았고, 가려진 path 는 docforge_convert 가 받지 못한다. DW-10 을 다시 보기 전에 HG-22 의 꼴이 파일 이름 · 경로를 비켜 가는지 본다(HG-22 의 실제 꼴은 고치는 중이라 대조 못 함). 지금 게이트웨이의 칸 이름 목록(`_PII_KEYS`, `gateway.py:613-620`)에는 `name` · `path` · `folder` 가 없다.
- **C-8 — `he-doc-docforge` 고침 셋(우리 몫, [`../checklist.md`](../checklist.md) 3c)** — 답 ④가 청한 key_tools 의 list_inputs · can 의 맡기기 줄(`he-team.json:530`) · pitfalls 의 path 줄(`:553`)이다. [`../context-notes.md`](../context-notes.md) C-8 대로 0.3.1 이 cae00 게이트웨이에 실린 뒤로 미루고, DocForge 가 Drive 판 이름을 알린 뒤에 커밋한다(DocForge `docs/checklist.md:85` 가 그 알림을 약속했다). 운영자 동기화는 이 앱에 없는 도구 이름을 오류로 모아 멈춘다(포털 `infra/scripts/sync-he-personas.py:147-150` → `:193-196` 이 2 로 끝난다). 셋에 workflow 의 '변환 요청이면 직접 부르지 말고 챗 업로드의 「Report Archive — 정밀 변환」 을 안내한다' 줄(`he-team.json:539`)은 들지 않았다 — DW-10 처럼 상자 파일을 맡기는 요청과 어떻게 맞출지 그때 함께 본다. 같은 동기화가 AIDataHub 저장 뒤 500 에 첫 건에서 멈추는 문제(AD-21 — 이 세션이 맡는다, C-7)도 이 길에 있다.
- **OB-94(우리 몫 — 보내지 않음, cae00 사람)** — 5절 글(정본 그대로)은 아래다.

  > DocForge 입력 뿌리에 시험 파일 하나(DW-10 다시 보기). — 남았다.

  0.3.1 의 목록은 운영자 상자만 보이므로 파일을 `~/Projects/HEAXHub/var/app_data/doc_forge/inbox/`(DocForge `docs/DEPLOY.md:71`)에 둬야 한다. 포털 스테이징(`DOCFORGE_INPUT_ROOTS`)에 두면 목록에 안 나온다. 상자 목록은 DocForge 도구가 열린 사람 모두에게 보이니 평문 pptx 하나로 한다(답 ⑤). dev 상자는 비워 둔다 — build-all 이 dev 앱 데이터를 Drive 에 올리고 cae00 app-data merge 가 없는 파일을 심는다(DocForge `docs/DEPLOY.md:137-138`). 이 박스의 dev 상자 `HEAXHub/var/app_data/doc_forge/inbox/` 는 아직 없다(0.3.0 이 떠 있다).
- **OB-102(우리 몫 — 보내지 않음, cae00 사람)** — 5절 글(정본 그대로)은 아래다.

  > DocForge 길 한 번 — 평문 pptx 를 'Report Archive — 정밀 변환' 과 '이 대화에서 분석' 으로 보낸다. DRM 파일은 PC 에서 만들지 않는다. — 남았다(TODO-20261029 H-05).

  두 길은 포털 백엔드가 스테이징의 호스트 경로로 게이트웨이 `docforge_convert` 를 바로 부른다(포털 `backend/app/agent/routes.py:1766` · `:1789`, cae00 `aec8e29` 에서는 `:1698` · `:1721`). 챗 에이전트를 지나지 않으니 HA-29 확인 카드와는 무관하다. `e72cbe5` 가 이 길이 지나는 `submit_path` 도 고쳤으니 0.3.1 뒤에 한 번 보는 것이 순서다. '이 대화에서 분석' 은 DocForge 가 맡지 않으면 AI 데이터 허브 변환기로 넘어가므로(`routes.py:1799-1800`) 응답의 `via` 가 `docforge` 인지 본다.

## 끝나면

DocForge 세션 `docforge-f6` 이 배치를 마치면 포털 세션 `hwaxportal-a5` 에 아래를 알린다. 코드 커밋(`e72cbe5` · `ab5547e`)은 이미 알렸다(답).

1. **배치 커밋** — DocForge `docs/DEPLOY.md` §7(사람 승인 뒤 dev) 대로 release 를 옮긴 커밋(`git -C DocForge push origin origin/main:release`, 빠른 감기만)과 HEAXHub 등록 사본을 `version: 0.3.1` 로 고친 커밋. 등록 사본은 release 를 옮긴 뒤에 올린다 — 먼저 올리면 스캐너가 옛 release 로 한 번 더 짓는다(`DEPLOY.md:101`). HEAXHub 리포의 몫은 이 판 줄 하나다.
2. **SIF · Drive** — `redeploy-app.sh doc-forge --rebuild`(로그 끝 '✓ DocForge 빌드 훅 끝') 뒤 `scripts/drive-push-sif.sh --dry-run` 과 본 실행(`dist-to-drive.sh` 는 쓰지 않는다 — `DEPLOY.md:43`). 알릴 것은 Drive `dist-<시각>` 이름과 `drive-drift.sh heax` 의 doc-forge 일치다. 이 이름이 오면 포털이 C-8 고침 셋과 cae00 확인 줄을 `docs/request-1030/server-setup.md` 에 넣는다(DocForge `docs/checklist.md:85`).
3. **cae00 사람 몫(포털이 `server-setup.md` 에 옮긴다 — 답 ⑤ · DocForge `docs/DEPLOY.md:68-72`)** — update-all(새 박스 값은 없다) → 브라우저 `/apps/doc_forge/api/v1/capabilities` 의 version 이 0.3.1 → 게이트웨이 `curl -X POST localhost:9110/refresh` 뒤 `curl localhost:9110/tools-map` 에 docforge_* 여섯 · `bash ~/Projects/HWAXPortal/infra/scripts/check-mcp-registration.sh doc_forge` → OB-94(상자에 평문 pptx 하나) → C-8 고침 셋이 든 포털 판을 받은 뒤 운영자 동기화가 멈추지 않는지 → OB-102(두 길을 한 번씩, `via` 가 `docforge`).
4. **다시 볼 시험** — 아래 DW-10 을 0.3.1 이 cae00 에 뜨고(상자가 생긴다) OB-94 · C-8 을 마친 뒤에 본다. 그때 HA-28 · HA-29 가 들어가 있으면 같은 시험에서 docforge_convert 확인 카드와 docforge_status 기다리기도 보인다. 7절의 'DW-02 후속 · DW-03(후속 포함)' 줄은 이 플랫폼 몫이 아니다.

결과는 `hwaxportal-a5` 에 알린다. 포털이 [`../outbound.md`](../outbound.md) 표의 '답' 칸과 [`../checklist.md`](../checklist.md) 에 옮긴다.

### 7절에서 이 플랫폼에 닿는 다시 볼 시험(정본 그대로)

| 시험 | 언제 | 볼 것 |
|---|---|---|
| DW-10 | HH-14 뒤 | 입력 파일을 골라 변환까지 한다. |
