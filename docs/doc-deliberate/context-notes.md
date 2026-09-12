# 문서 심의 — 결정 기록

작업하면서 내린 판단과 **왜 그렇게 했는지**. 다음 세션이 같은 판단을 다시 하지 않도록.

---

## D-1. 추출은 클라이언트에서 — 이게 전부를 정한다

사용자 요구: "업로드하는 PC 의 오피스 COM 을 이용해서 한번 읽고 출력하는게 되었으면 해
그걸 전제로 해야 DRM 이 안 걸리거든."

DRM 문서는 **그 PC, 그 사용자 세션**에서만 복호화된다. 서버가 원본을 받아 파싱하면 암호화된
바이트만 본다. 그래서 서버로 가는 것은 원본이 아니라 **추출된 글**이다.

**사용자가 2026-09-12 에 COM 동작을 실측 확인했다** — 가장 큰 미지수였고, 풀렸다.

## D-2. 이미 있던 두 경로가 왜 못 쓰이나 (코드로 확인)

사용자가 "ReportArchive 에서 올릴 수 있었던 것 같은데" 라고 해서 코드를 봤다. 둘 다 있다.

| 경로 | 무엇을 하나 | 왜 DRM 에서 막히나 |
|---|---|---|
| RA `POST /imports/pptx` | PPTX → 보고서 draft(슬라이드 1장=페이지 1장) | `routes.py` 가 `parse_pptx(data)` 를 **서버에서 python-pptx 로** 돈다. DRM PPTX 는 zip 이 아니라 암호화된 OLE 컨테이너라 여기서 400 |
| AIDataHub `convert_file` | docx/xlsx/pdf/pptx 정밀 변환 | 설명 그대로 "서버 inbox 에 파일을 두면 서버가 변환" |
| RA `prepare_upload` | 티켓+URL 발급 → PC 에서 curl 로 바이트 POST | **업로드는 된다.** 다만 첨부 저장(file_id)이고 내용 추출이 아니다 |

즉 **취입 기능은 이미 있었고, DRM 문서에서만 못 쓴다.** 이 작업은 새 기능이 아니라
변환 지점을 서버에서 PC 로 옮기는 것이다.

## D-3. 왜 마크다운을 먼저 만들었나 (RA 세그먼트가 더 좋은데)

RA 파서의 출력(heading/rich_text/table/image)은 `create_report_draft(extra_blocks=…)` 가
받는 모양과 같다. 추출기가 그 모양으로 뱉으면 DRM 문서도 보고서로 그대로 들어간다 —
**RA 리포를 건드리지 않고**(커밋 금지 대상) 기존 MCP API 만으로.

그런데 원래 요청은 "내용을 읽고 **심의**" 다. 심의 근거는 글이면 되고, 페이지·슬라이드
번호만 있으면 인용이 된다. 그래서 1차는 마크다운, 2차가 세그먼트다. 순서를 뒤집으면
쓰지도 않을 위젯 변환을 먼저 만들게 된다.

## D-4. Word·PowerPoint 를 함부로 Quit 하면 사용자 문서가 닫힌다

둘 다 **단일 인스턴스 자동화 서버**다. 사용자가 문서를 편집 중이면 `New-Object` 는 그
인스턴스에 붙고, 거기서 `Quit()` 을 부르면 **작업 중인 창이 닫힌다.**

→ 실행 전 프로세스(WINWORD/POWERPNT) 존재 여부로 `Owned` 를 판정하고, 우리가 띄운 것만
우리가 끈다. PowerPoint 는 다른 발표자료가 남아 있으면 아예 안 끈다.

`Marshal::GetActiveObject` 를 쓰려다 버렸다 — **.NET Core 에서 삭제돼 PowerShell 7 에서
터진다.** 프로세스 유무 판정은 5.1·7 양쪽에서 똑같이 된다.

## D-5. PowerShell 5.1 은 BOM 없는 UTF-8 .ps1 을 ANSI 로 읽는다

한글 출력 문자열이 전부 깨진다. `.ps1` 은 **BOM + CRLF** 로 배치한다.
`.bat` 은 반대로 **ASCII 만** 쓴다 — cmd 코드페이지(cp949/65001)에 따라 한글이 깨지므로,
안내 문구는 전부 `.ps1` 이 낸다.

## D-6. 페이지 단위로 읽는다(문단 단위 아님)

`$doc.Paragraphs` 를 돌면 COM 왕복이 문단 수만큼이라 100쪽짜리에서 몇 분 걸린다.
`GoTo(wdGoToPage, …)` 로 페이지 경계만 잡아 `Range(start,end).Text` 로 한 번에 읽으면
호출이 페이지 수에 비례한다. 대신 heading 구조는 포기했다 — `[p.N]` 표지만으로 인용이 된다.

표는 예외다. 본문 `Range.Text` 에선 셀 구분자(CR+BEL)로만 남아 읽을 수 없으므로
`$doc.Tables` 에서 따로 뽑아 마크다운으로 복원한다(표당 COM 1회).

## D-7. PowerPoint 는 `Visible=$false` 를 거부한다

버전에 따라 예외가 난다. 대신 `Presentations.Open(file, ReadOnly, Untitled, WithWindow=msoFalse)`
의 네 번째 인자로 창 없이 연다 — 이게 정석이다.

## D-8. 심의 사전 근거 예산이 **문서 한 건도 못 담고 있었다**

종전: 12항목 · 항목당 2,000자 · 합계 11,000자. 발표자료를 추출하면 보통 30,000~80,000자다.
**첫 항목에서 잘렸다.** 그런데 심의는 정상적으로 돌고 결론도 나온다 — 좌석이 표지만 보고
논의한 것을 아무도 모른다. 이 기능을 만들기 전에 이걸 먼저 고쳐야 했다.

새 값(전부 env 손잡이): `_EVID_ITEMS` 40 · `_EVID_ITEM_MAX` 12,000 · `_EVID_BUDGET` 60,000.

**같이 올려야 하는 것이 하나 더 있었다** — `HANDOFF_RESULT_CHARS`(1,200→4,000).
예산만 올리고 발췌 길이를 그대로 두면 예산은 크고 실제로 실리는 건 그대로다.
`test_doc_attach.py::test_핸드오프_발췌가_심의_예산에_맞다` 가 이 짝을 본다.

## D-9. 상한은 세 계층에 있고, 어긋나도 아무 신호가 없다

프론트 `handoff.ts` → 포털 `DelibOpts` → 엔진 `_EVID_*`. **가장 작은 곳에서 잘린다.**
좌석 상한과 달리 여기는 422 도 안 나고 심의도 멀쩡히 돈다.
→ `backend/tests/test_evidence_budget_contract.py` 가 세 값이 같은지 본다.

## D-10. 문서는 sys_prompt 에 싣는다(user 메시지 아님)

챗 경로는 세 갈래다 — 첫 호출 · 오류 재시도 · 강제 도구호출. **셋 다 `sys_prompt` 를
공유하고 `req.message` 를 따로 쓴다.** user 메시지에 붙이면 재시도 경로에서 조용히 빠진다.

## D-11. 예산은 문서 **건수로 균등 분배**한다

앞 문서가 예산을 다 먹으면 사용자는 두 건을 붙였는데 답이 한 건만 본 채로 나온다. 그 실패는
화면에 아무 흔적도 안 남는다. → `_doc_block` 이 몫을 나누고, 자른 문서마다 원문 길이와
"앞 N자만 실림" 을 적는다. 모델이 못 본 구간을 알아야 지어내지 않고 되묻는다.

## D-12. 본문은 대화에 저장하지 않는다

`Message.docs` 에는 **이름·길이·종류만** 남긴다. 수만 자 본문까지 localStorage 에 넣으면
쿼터를 바로 먹는다(`agentCatalog` 를 안 남기는 것과 같은 이유). 본문은 전송 1회성이고,
`attachedDocs` 는 보낸 뒤 비운다 — 안 비우면 매 턴 수만 자가 다시 실린다.

## 남은 것

- **2차 — RA 세그먼트 출력**: `.hwax.json`(heading/rich_text/table/image) → `create_report_draft`.
  슬라이드 그림은 COM 의 `Slide.Export` 로 PNG 를 뽑아 `prepare_upload` 로 올려 file_id 를 얻는다.
- 목적지 선택 UI: 지금은 "읽고 심의" 하나뿐이다. `upload.py DESTINATIONS` 에 문서 목적지
  (`import_record`·`create_report_draft`·`ingest_report`)를 더하면 종전 되묻기 화면이 그대로 쓰인다.
- 띵킹 모드 경로에는 문서가 안 들어간다(챗·심의만). 필요하면 같은 `_doc_block` 을 붙인다.
- **실제 DRM 문서로 `-SelfTest` 후 본 시험** — 이 박스에는 PowerShell 도 Office 도 없어
  문법 검사조차 못 했다. 첫 실행은 사용자 PC 에서다.
