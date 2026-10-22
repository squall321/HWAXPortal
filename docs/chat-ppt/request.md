# 포털 챗 PPT 요청 — (A) 보낸 결과가 챗 맥락에 안 들어가 이전 그림으로 답한다 · (B) DRM 문서를 PC 의 PowerPoint 로 풀어 웹 챗에 올리기 (2026-10-22)

> 요청서 사본(2026-10-22 사용자가 붙여 넣은 것). 요청자 메일 주소는 이름만 남겼다(이 리포는 GitHub 에 있다). 대조 결과와 정정은
> [context-notes.md](context-notes.md), 계획은 [PLAN.md](PLAN.md).

요청일 2026-10-22 · 요청자 koo.park(HWAX Portal 운영) · 대상 **HWAXPortal**(곁가지 HWAXAgentServer · AIDataHub · Report Archive)

기준 — 포털 `dba4c1e`(= origin/main) · 에이전트 서버 `9d4c931`(cae00 에서 도는 판, origin/main `e436d15` 도 이 자리를 바꾸지 않는다).
근거 — 코드 대조(조사 4 · 합성 1 · 반박 검증 2, 10-22)와 cae00 실측(사용자 본인 대화 · 포털 감사 · 게이트웨이 감사). 아래 `파일:줄` 은 위 판 기준이다.

**한 줄**

- (A) 웹 챗(`hwax.sec.samsung.net`)에서 PPT 를 붙여 'AI 데이터 허브' 나 'Report Archive' 로 보내면 결과가 **패널 안에서만 끝나고 대화에 남지 않는다.** 다음 질문
  「방금 변환한 것 검토해 줘」 앞에는 예전에 올린 그림만 실려 모델이 그 그림을 보고 답했다. DRM 문제가 아니었다 — 그날 올린 PPTX 4개는 서버에서 평문으로 읽혔다.
- (B) DRM(NASCA)이 걸린 문서는 브라우저가 올려도 서버가 못 읽는다. Claude 로는 되는 이유는 PC 의 추출기(`hwax-doc-mcp.mjs` → PowerPoint COM)가 그 PC 에서
  글을 뽑아 대화에 싣기 때문이다. 웹 챗에서도 버튼 하나로 같은 일을 하게 해 달라.

---

## A. 보낸 결과가 챗 맥락에 안 들어간다

### A-0. 실제로 있었던 일(10-22, 대화 `8366a215`)

| 시각 | 일 |
|---|---|
| 06:41:37 | 1번째 발화 「이 이미지를 봐봐」 + 그림 한 장(`/agent/artifacts/c5d2…png`) |
| 06:46:07 · 06:46:10 | PPTX(26.6 MB) 올림 → '어디로 보낼까요' → AI 데이터 허브. 게이트웨이 `convert_file` ok · 355 ms · 결과 15,278자 |
| 06:46:20 | 「방금 변환한거 검토해봐」(패널 안내 문구 그대로). 도구 호출 0회. 답은 「"방금 변환한 것" 이 무엇인지 대화에 남아 있지 않아」 라고 하면서 06:41 의 그림을 검토했다 |
| 이어서 | 「ppt 야」 → 같은 그림을 슬라이드로 보고 다시 검토. 모델이 `search_tools` 를 두 질의로 불러 `convert_file` 을 찾았으나 넣을 파일 이름이 맥락에 없었다 |
| 06:47:59 | 다른 PPTX 를 Report Archive 로 — 보고서 초안 29쪽이 만들어졌으나 29쪽 모두 블록 0 · 파일 0 · 본문 0자였다 |

대화 저장소의 이 대화에는 PPT 업로드 · 보내기 · 변환에 관한 메시지나 meta 가 **한 건도 없다.** 포털 감사의 `upload_stage` · `upload_dispatch` 행은 chat_id 가 비어 있다.

### A-1. 원인(코드)

1. 평문 `.pptx` 는 `Composer.tsx:126-132` 에서 `uploadFile()` → `setStaged` 로만 간다. 다음 발화의 `documents` 가 되는 `attachedDocs` 는 'text' 갈래에서만 채운다(`:141-151`).
2. `UploadRouter.tsx:39-63` 에서 목적지를 고르면 `DocDispatchPanel` 이 `POST /agent/upload/dispatch` 를 부른다. AI 데이터 허브 갈래(`backend/app/agent/routes.py:1327-1342`)는
   파일을 `~/aidh-inbox/<메일 앞부분>-<파일명>` 으로 복사하고 `convert_file` 을 불러 `{stage:'done', inbox_name, result}` 를 **브라우저에만** 돌려준다. AIDH 의 변환은
   저장하지 않는다(`run_convert`, `auto_save=False`).
3. `DocDispatchPanel.tsx:37` `setDone(r)` 이 결과를 패널 지역 상태에만 둔다. `:50-60` 은 '변환했습니다' 와 「챗에서 "방금 변환한 것 검토해 줘" 라고 하라」 를 띄운다.
   이 파일은 `dispatchUpload` 만 가져오고(`:3`) ChatContext · 입력창 · 대화 저장소에 아무것도 쓰지 않는다. 15,278자 초안은 버려진다.
4. 다음 발화에서 `ChatContext.tsx:551` 은 `buildHistory(…, {images:true})` 로 앞 대화를 보낸다. `history.ts:62` 가 1번째 발화의 그림 주소를 다시 싣는다. `docs`(`:568`) ·
   `imgs`(`:577`)는 비어 있다 — PPT 내용도 식별자도 가지 않는다.
5. 에이전트 서버 `app.py:3628-3662` 가 그 그림을 「[시스템 첨부 — 앞 대화에 나온 그림 1장 · 1번째 발화에 사람이 올린 그림 … 질문에 이 그림이 걸리면 직접 보고
   판단하라]」 로 다시 만들고, `app.py:4027` 이 `messages=[system, *history, recap, user_msg]` 로 **질문 바로 앞**에 둔다. 시스템 프롬프트에는 업로드 · 변환 개념이 없다.
   그래서 「방금 변환한 것」 이 가리킬 수 있는 것은 그 그림뿐이었다.

함께 확인한 것:

- 커밋 `b883543`(09-12) 메시지에 「aidatahub 는 저장까지 하지 않는다 — 그 확인을 챗에 남긴다」 는 의도가 있으나 구현이 없다.
- 변환 **실패**는 이미 오류로 뜬다 — `mcp_call`(`upload.py:285-340`)의 판정(`procedures/judge.py:298-326`)이 `status:'error'` 를 502 로 바꾼다. 성공했는데 맥락이 끊기는 것이 문제다.
- `upload.api.ts:25-34` `DispatchResult` 는 `stage` 를 `'dispatched'|'failed'` 로 적었지만 서버는 `'done'` 을 준다. `inbox_name` · `result` · `pages` 칸이 타입에 없다.
- Report Archive 갈래(`routes.py:1251-1325`)는 `create_report_draft` 에 `blocks:{}` 와 가져오기 초안의 `pages` 만 넘긴다. 만들어진 보고서가 0블록인데도 「페이지 29장이 들어갔습니다」 로 성공 표시한다. 0블록의 직접 원인은 RA 응답 모양을 봐야 확정된다(RA 코드는 cae00 에 없다).
- `Composer.tsx:286` `<UploadRouter staged={staged} …/>` 에 `key` 가 없다. 패널이 열린 채 다른 파일을 붙이면 고른 목적지 · 완료 표시가 새 파일 이름 아래로 이어질 수 있다(그날 감사에 '올리고 보내지 않은 파일 → 새 파일 → 3초 뒤 보내기' 가 두 번 있다. 로그로 증명하지는 못했다).

### A-2. 고칠 곳

| # | 우선 | 자리 | 할 일 |
|---|---|---|---|
| A1 | P1 | `DocDispatchPanel.tsx:29-60` · `UploadRouter.tsx:13,62-63` · `Composer.tsx:286` · `upload.api.ts:25-34` | 보내기가 성공하면 **이름이 박힌 지시문으로 입력창을 채운다**(Composer 의 `onFill` 꼴 `:342-347` 을 내려 준다). AIDH: 「AI 데이터 허브 inbox 파일 `<inbox_name>` 을 convert_file 로 변환한 초안을 검토하고, 모자란 항목은 import_record(dry_run=true)로 물어봐 줘」. RA: 결과에서 report_id · url 을 꺼내 「보고서 <report_id> 를 get_report_outline · get_report 로 읽고 검토해 줘」. `:58` 의 「"방금 변환한 것 검토해 줘" 라고 하라」 문구를 이 단추로 바꾼다. `DispatchResult` 타입을 서버 응답에 맞춘다 |
| A2 | P1 | `DocDispatchPanel.tsx`(성공 처리) · `ChatContext.tsx` | 보내기 성공을 **대화에 남긴다** — 활성 대화에 어시스턴트 알림 메시지 하나(예 「PPT <파일명> 을 AI 데이터 허브로 변환했다(inbox <inbox_name>)」)를 기존 `POST /agent/conversations/{cid}/messages`(`routes.py:463`, `ConvMessageIn` 은 role=assistant · meta 를 받는다)로 저장하고, meta.activity 에 `{tool:'convert_file', detail:{file:inbox_name}, result_full:<요약>}` 또는 `{tool:'create_report_draft', result_full:{report_id,title,pages,url}}` 를 싣는다. 그러면 `history.ts` 의 근거 길로 다음 턴에 간다. ⚠ 대화가 아직 없는 화면(첫 화면 · 새 챗)에서도 패널이 뜨므로, 대화를 만들거나 첫 전송까지 알림을 들고 있어야 한다. 근거 머리가 「어시스턴트가 도구로 조회한 결과」 로 붙으니(`app.py:2800-2804`) 보내기 근거용 머리를 따로 두는 편이 낫다 |
| A3 | P2 | 에이전트 서버 `app.py:3657-3660`(앞 대화 그림 다시 싣기 문구) · 시스템 프롬프트 | 문구에 상대 시점(「N턴 전」)과 단서를 더한다 — 「이번 질문이 이 그림이 아니라 업로드 · 변환한 파일이나 보고서를 가리키면 그림으로 대신 답하지 말고 무엇인지 되묻거나 도구로 찾아라」. 시스템 프롬프트에 「'방금 올린 것 · 변환한 것' 은 이력의 업로드 근거를 먼저 보고, 없으면 파일 이름을 물어라」. ⚠ 다시 싣기를 통째로 빼거나 그림이 나온 턴 뒤로 옮기는 안은 그림과 새 문서를 비교하는 정상 질문, 이력 압축(`_compact_turns`)과 부딪친다 — 문구 보강을 먼저 한다 |
| A4 | P2 | `routes.py:1317-1325`(RA 갈래) · `DocDispatchPanel.tsx:46,55-57` · `test_ra_sso.py:218` 근처 | `create_report_draft` 응답에서 report_id · url · 블록 수 · warnings 를 읽어, 블록 0 이면 「내용이 비었다」 로 알리고 warnings 를 화면에 보인다. 먼저 RA `/api/imports/pptx` 응답 모양을 확인해 블록 · 그림이 `pages` 밖 어디에 있는지 보고 옮기거나, RA 웹 가져오기와 같은 저장 길을 쓴다. 시험 픽스처에 실제 블록이 든 초안을 넣고 '만들어진 보고서 블록 수 > 0' 을 본다 |
| A5 | P3 | `Composer.tsx:286` | `<UploadRouter key={staged.staging_id} …/>` — 새 파일마다 고른 목적지 · 완료 표시를 새로 시작 |
| A6 | P3 | `ChatContext.tsx:370-377 · 639` | 주석은 「보낸 뒤 비운다」 인데 `attachedDocs` 는 비우지 않는다(그림만 비운다). A2 의 요약을 이 길로 싣는다면 한 턴만 가게 맞춘다 |
| A7 | P3 | AIDataHub `mcp_runtime.py`(convert_file 근처) | 호출자의 최근 inbox 파일을 돌려주는 읽기 도구(예 `list_inbox`) — 포털 연결이 빠져도 모델이 파일 이름을 찾을 수 있게(도구는 닿았지만 이름을 몰랐다) |

### A-3. 고치기 전 사용자가 할 수 있는 것

- '변환했습니다' 뒤에 「방금 변환한 것」 이라고 쓰지 말고, 패널에 보이는 **inbox 파일 이름을 넣어** 청한다 — 「AI 데이터 허브 inbox 파일 `<이름>` 을 convert_file 로 변환해 초안을 검토해 줘」. 파일은 inbox 에 남아 있고 변환은 저장하지 않으니 다시 불러도 된다.
- 앞에서 그림을 올린 대화에서는 그 그림이 매 턴 다시 실린다 — PPT 검토는 **그림 없는 새 대화**에서 시작하는 것이 가장 확실하다.
- Report Archive 로 보낸 초안은 지금 0블록이라 읽을 내용이 없다 — 내용 검토는 AI 데이터 허브 쪽으로 한다.

---

## B. DRM(NASCA) 문서를 PC 의 PowerPoint 로 풀어 웹 챗에 올리기

### B-0. 지금 있는 것과 차이

| 길 | 어떻게 읽나 | DRM 문서 |
|---|---|---|
| Claude(Code · Desktop) | PC 의 `hwax-doc-mcp.mjs`(포털이 `/doc-extract/` 로 배포)가 `hwax-doc-extract.ps1` 을 띄워 **PowerPoint · Word COM 으로 읽기 전용으로 열고** 슬라이드별 글 · 표 · 메모를 뽑아 그 PC 의 Claude 대화에 싣는다 | 된다 — DRM 이 허용한 앱(PowerPoint)이 연다 |
| 웹 챗 — 평문 파일 | 브라우저가 원본을 `/agent/upload` 로 올리고 서버가 파싱 | 해당 없음(그날 PPTX 4개는 첫 바이트 `PK` · 서버에서 3만 자까지 읽혔다) |
| 웹 챗 — 암호 파일 | `docAttach.ts:36` `isEncryptedOffice` 가 첫 바이트로 가른다(`PK` 평문 · `D0 CF 11 E0` OLE = 암호). 암호면 `DocExtractHint` 가 「`.bat` 위로 파일을 끌어다 놓아 `.hwax.md` 를 만들고 그것을 여기 붙여라」 로 안내 | 손으로 세 걸음(내려받기 · 끌어 놓기 · 다시 붙이기) |

요청은 웹 챗의 셋째 줄을 **버튼 하나**로 만드는 것이다 — 「PC 의 PowerPoint 로 열어 가져오기」 → PC 도우미가 COM 으로 열어 뽑고 → 포털로 바로 올려 → 지금 대화에 붙는다.
브라우저는 COM 을 부를 수 없고 PC 파일 경로도 모른다. 그래서 PC 쪽 도우미와 그 도우미를 부르는 길, 도우미가 로그인 없이 올리는 길이 든다.

### B-1. 포털이 해 줄 것

| # | 자리 | 할 일 |
|---|---|---|
| B1 | 백엔드(새) `POST /agent/upload/pc-ticket` | 브라우저 세션 + CSRF 로만 연다. 일회용 업로드 표(무작위 32바이트 · 수명 10분 · 주인 이메일 · 대화 id · 원 파일 이름 · 크기 상한)를 만들어 `{ticket, upload_url, expires_at}` 를 돌려준다. SSO 로 이미 로그인한 사람이 표를 받는다 — PC 에 포털 토큰을 새로 두지 않는다 |
| B2 | 백엔드(새) `POST /agent/upload/pc/{ticket}` | 표로만 받는다(세션 · PAT 불필요). 한 번 쓰면 닫는다. 받는 것: 추출 결과 `.hwax.md`(글 · 표 · 메모 · 슬라이드 번호) + (선택) 슬라이드 그림 PNG + (선택, B6) 다시 저장한 PPTX. 확장자 · 첫 바이트 · 크기를 본다. 받은 것은 그 사람의 스테이징에 두고, 표의 대화에 A2 와 같은 꼴의 메시지(문서 근거)로 붙인다 |
| B3 | 백엔드(새) `GET /agent/upload/pc-ticket/{ticket}` | 세션으로 상태를 본다(대기 · 받음 · 실패 · 만료). 화면이 몇 초마다 묻는다 |
| B4 | 화면 `DocExtractHint.tsx` · `UploadRouter.tsx` | 암호 파일이면(그리고 평문이라도 원하면) 「PC 의 PowerPoint 로 열어 가져오기」 단추. 누르면 B1 → `hwax-doc://extract?t=<ticket>&name=<파일 이름>` 을 연다 → B3 로 기다리다 받으면 `.hwax.md` 를 `attachedDocs` 칩으로 붙이고(또는 A2 메시지), 원하면 그 결과를 그대로 AI 데이터 허브 · Report Archive 로 보내는 다음 단계를 띄운다. 도우미가 없으면(몇 초 안에 상태가 안 바뀌면) 지금의 내려받기 안내로 돌아간다 |
| B5 | 셋업 배치(`frontend/src/lib/setupBat.ts`) · `/doc-extract/` | `hwax-doc-extract.ps1` 을 사용자 폴더(예 `%LOCALAPPDATA%\HWAX\`)에 두고, `HKCU\Software\Classes\hwax-doc`(URL Protocol)를 등록해 `powershell -NoProfile -File …\hwax-doc-extract.ps1 -Url "%1"` 로 잇는다. 관리자 권한이 필요 없는 HKCU 다. 판(버전) 확인 주소를 두어 낡은 도우미를 알린다 |
| B6 | `hwax-doc-extract.ps1` | `-Url` 모드를 더한다 — 표 · 파일 이름을 읽고, 파일 고르기 창(그 이름으로 걸러 연다)으로 사람이 파일을 고른다 → 지금의 COM 추출(읽기 전용으로 열기, `:310` 근처) → (선택) `Slide.Export` 로 슬라이드 PNG → B2 로 올린다(사내 인증서 · `NO_PROXY` 는 셋업이 이미 맞춘다) → 임시 파일을 지운다. **다시 저장(SaveAs)한 PPTX 를 보내는 것은 선택으로 두고 기본은 끈다** — 아래 B-2 |
| B7 | 감사 | 표 발급 · 사용 · 만료를 감사에 남긴다(주인 · 대화 · 파일 이름 · 크기 · 무엇을 받았나). 본문은 남기지 않는다 |

### B-2. 정해야 할 것(보내기 전에)

1. **다시 저장한 PPTX 가 정말 풀리나.** DRM 은 허용 앱이 저장할 때 다시 걸어 두는 정책이 흔하다. 셋업의 자가 시험(`hwax-doc-extract.ps1:473-507` 이 임시 폴더에 문서를 만들어 본다)에 'NASCA 문서를 열어 다른 이름으로 저장 → 첫 바이트가 `PK` 인가' 를 더해 PC 한 대에서 먼저 잰다. 다시 걸리면 PPTX 보내기는 접고 **글(`.hwax.md`) + 슬라이드 그림**만 보낸다 — AI 데이터 허브 변환과 챗 근거에는 그것으로 충분하다. Report Archive 페이지 가져오기는 PPTX 가 필요하니, 그쪽은 PPTX 가 풀리는 경우에만 연다.
2. **보안 정책 확인.** DRM 문서를 PC 에서 풀어 사내 서버로 올리는 일이 정보보호 지침에 맞는지 담당 부서에 확인한다. 공식 길이 있다면(NASCA 서버 연동 · 복호화 모듈을 시스템 단위로 신청) 그쪽이 더 낫다 — 그러면 B 전체가 서버 한 곳(업로드 파싱 앞)으로 줄어든다.
3. **무엇을 남기나.** 풀린 원본은 PC 임시 폴더에도 서버에도 남기지 않는다(올린 뒤 지운다). 서버 스테이징은 지금처럼 그 사람 폴더에 두고 보관 기한을 정한다.

---

담당: HWAX Portal (koo.park)
