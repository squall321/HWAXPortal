# 보고서에 도구 그림 싣기 — 체크리스트

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 가지 — 포털 `wt1102/figures` · 에이전트 서버 `wt1102/figures`(올리지 않음).

## 포털

- [x] DocForge 배달의 RA 올리기를 `RaSession` 하나로 떼기(배달 동작은 그대로 — 기존 시험 그대로 통과)(RF-3)
- [x] `POST /agent/figures/to-report` — 게이트웨이 계약(RF-1 · RF-2 · RF-4 ~ RF-8)
- [x] `POST /agent/figures/upload` — 에이전트 서버용 올리기만(RF-1)
- [x] 시험 — 가짜 RA · 자격 · 읽기 전용 거절 · 꼴 · 크기 · sha256 · RA 오류 · 칸을 버린 RA · 동시 호출
- [x] 계약 시험 — 에이전트 서버의 `report_figures.attach` 를 진짜 포털 앱에 물린다(RF-15)
- [x] 포털 전체 시험 — 11-02 병합 판 4,707 통과 · 29 건너뜀 · 실패 둘은 작업 트리에서만 나는 알려진 것(ste doctor · tlscert)

## 에이전트 서버

- [x] `report_figures.py` — 그림 줄 찾기 · 그 사람 PAT 로 올리기 · 자리 표지 · 그림 칸 · 셈(RF-9 ~ RF-12)
- [x] `/보고서`(`run_report_save`) 에 잇기 — 결과 사건 `figures`
- [x] 심의 보고서(새 보고서 · 이어붙이기)에 잇기 — outcome `figures` · 결정문 끝 안내
- [x] 잡 원장이 outcome 의 `figures` 를 `report_figures` 로 접고 `deliberate_result` 가 낸다
- [x] 시험 — 단위 · `/보고서` · 심의(웹 · PAT 없는 잡)
- [x] 에이전트 서버 전체 시험 — 11-02 4,385 통과 · 2 건너뜀

## 마무리

- [x] 반대 검토(사본에서) — 신원 · 조용히 사라지는 그림 · 크기 · 꼴 · RA 오류 길, 재현한 것만 고침(RF-17 — F1 · F2 · F4 ~ F7 고침, F3 는 게이트웨이 · RA 몫)
- [x] 결정 기록(RF-1 ~ RF-18) 마감

## 표 칸 그림 — PC 키트 변환기 · 게이트웨이 배포(긴급 11-02 '표칸그림 필요해', RF-19 ~)

> 가지 — 포털 `wt1102/md2docx` · 게이트웨이 `wt1102/kit`(올리지 않음).

- [x] `infra/pc-kit/hwax-md2docx.py` — 홀로 선 줄 · 줄 안 · 표 칸 그림, 캡션, 열 몫 · 높이 상한, A4 · 맑은 고딕(RF-19)
- [x] 그림 주소 — 상대 · POSIX · H:/ · H:\ · UNC · `<…>` · 제목, ref 찾기(md 폴더 · `--fig-dir` → PAT 받기 → figure_get 안내)(RF-20)
- [x] 빠진 그림 종료 2 · docx 없음, `--allow-missing` 자리표, 저장 뒤 수 대조 종료 3(RF-21)
- [x] 포털 시험 `backend/tests/test_pc_kit_md2docx.py` — 열다섯, 변이 열여섯이 모두 빨강(3.10 · 3.13)
- [x] 게이트웨이 `kit_get` · `GET /kit/<이름>` — 표 · PAT · 404 · 감사 · README(RF-22)
- [x] 게이트웨이 검색 어휘 docx · 변환기 · 표 칸 — 띄어 쓴 열쇠(RF-23)
- [x] 끝까지 잇기(사본) — 빈 포트의 진짜 `_bearer_gate` 로 키트 받기 · figure_get 꼴 파일 · PAT 받기 → 변환 `그림 표기 3 · docx 그림 3 · 표 칸 안 2`
- [x] 반대 검토(사본에서) — 표 칸 배치 · 조용히 사라지는 그림 · Windows 경로 · PAT 새기 · /kit/ 위조 · 경로 넘기 — 변환기 K1 ~ K11 · S1 · S3 · S4 고침, /kit/ 0건(RF-24)
- [x] 포털 전체 시험(`91652c86` — 4358 통과 · 408 건너뜀 · 실패 둘은 작업 트리에서만 나는 알려진 것 — ste doctor · tlscert) · 게이트웨이 전체 시험(`077d5f8` — 855 통과)

## 현장 계획서의 CAD 단면(F1 ~ F3 · F6 — 긴급 11-02)
- [x] F2 단면 자리 찾기 — 리스크 앱 `risk_locate_for_section` 등 도구 넷 · 스키마 v7(변환 등록부 · `location_json`), HWAXRisk `4d346316` · Drive(HEAXHub) `dist-20261102-233903Z` — 설계 · cae00 몫은 HWAXRisk `docs/f2-locate-for-section.md`, dev 확인 11-02(도구 넷 · v7 · 이관 사본)
- [x] F1 짝 단면 — StepForge `section_pair_view` · `section_batch_result`(읽기) · 잡 종류 `section_batch`, 그쪽 main `5979a26`(문서 끝 `8a06681`) · Drive(HEAXHub) `dist-20261103-004526Z` — 게이트웨이 tools/list 에 둘 · 경유 실호출에 그림 보관 표지(RF-27)
- [x] F2 → F1 실호출(dev 11-03) — 답의 `f1` 칸을 그대로 넘기면 거절이던 것을 리스크 앱 `f1.calls` 로 고침(`fc384f4b`(병합 — 코드 `8c4a6d1` · 문서 `742c4d3`)) · 두 평면 그림 · 강조가 두 판에서 맞음(RF-27)
- [x] 게이트웨이 검색 낱말 — '짝 단면' · '단면 비교' → `section_pair_view`(`1c933629` · 추적 평가 147쌍 그대로, RF-27)
- [x] F3 `section_batch` — 그쪽 main `ed0ca60`(문서 끝 `20b72a7`) · Drive(HEAXHub) `dist-20261103-025507Z`, F2 의 `f1.calls` 줄(견줄 판만 더함)이 그대로 rows 로 들어가 잡 · 그림 둘(dev 11-03, RF-28)
- [x] F6 접힘 변환(`fold`) · 적층 그림 `stackup_figure` — 그쪽 main `5366950` · Drive(HEAXHub) `dist-20261103-073959Z`, dev 게이트웨이 확인(RF-30)
- [x] F6 후속 — 적층 그림의 측정 잡을 읽기 토큰으로도(사용자 결정 RF-29) — 그쪽 `dc7b447`, dev 에서 큰 보드 짝이 잡을 저절로 넣음 · 같은 부름은 같은 잡 · 게이트웨이 읽기 분류에 넷 다 (RF-30) — 그 잡의 그림까지는 아래 줄
- [x] 저절로 넣은 측정 잡의 그림까지 — StepForge a76(`164c99c` · Drive `dist-20261103-104015Z`) 뒤 dev 에서 축 z 로 211 파트 짝 → 잡 2분(진행 26 · 54 · 100) → `stackup_figure(job_id)` 그림 보관, 축 없이는 잡 없이 `job_not_queued`(RF-32)
- [ ] F2 cae00 — ODB 허브 몫 확인(그 문서 6절 — `get_part_detail.side` · bottom 좌표 · `get_net` 핀 · 구멍 쪽 넘김 · 실제 메인 보드로 손 셈) · 외곽 bbox(ODB 허브 OH-04)

## cae00 실제 데이터로 끝에서 끝까지(사용자 요청 11-03 — RF-31)
- [x] 점검 스크립트 `infra/scripts/cad-figure-check.py`(`bf528ef4`) — 리스크 항목 → 위치 → 짝 단면 · 묶음 · 접힘 · 적층 → 그림 받기(크기 · sha256) → 고르면 보고서 · 문서, 읽기가 기본 · 쓰기는 대상을 줄 때만 · 요약은 상태 · 수만, 시험 11 · 변이 넷 붉음 · dev list 끝 0
- [x] 받은 편지함 [`../cae00-inbox/2026-11-03.md`](../cae00-inbox/2026-11-03.md) Q4(실제 항목으로 끝까지 — 사람이 그림을 본다) · Q5(Windows PC 변환기)
- [x] 적층 그림 쪽 나눔(StepForge a77 `143dd42` · `969e7fb` · Drive `dist-20261103-130959Z`) — 게이트웨이로 211 줄 결과를 넷 쪽 · 쪽마다 그림 보관 · 256 KB 안, 점검 스크립트가 끝 쪽까지 따라간다(RF-33)
- [ ] cae00 답 — Q4 · Q5(사람)

## 하지 않은 것(다음 몫)

- [x] 반영 — 11-02 올림 · dev 재기동(게이트웨이 `844f91af` · 에이전트 서버 `6a4c6b42` · 포털 `9468bef4`)
- [x] 업데이트 이력(`docs/changelog.md`) 항목 — `9468bef4`(날짜는 `86caab20` 에서 KST 11-03 으로 — 쓴 때가 한국 날짜로 11-03)
- [x] CLAUDE.md 문서 표 한 줄 — `8ac1be8c`
- [ ] `/ai-data-hub/attachments/…` 그림(AIDataHub 첨부)은 아직 싣지 않는다(RF-13)
- [ ] 분석 루틴의 RA 초안 · 챗에 사람이 올린 그림은 이 길을 타지 않는다(RF-13)
- [ ] 포털 잠금 밖의 RA 쓰기가 그림 칸을 지우는 경합 — 게이트웨이가 보고서마다 RA 쓰기를 줄 세우거나 RA 가 expected_revision 을(RF-6 · F3)
- [ ] RA 병합의 곁효과(배치 다시 짓기 · 여러 템플릿 보고서) RA 담당 확인(RF-18)
- [ ] 에이전트 서버 `vision.IMG_URL_RE` 의 `\b`(조사 앞 그림 주소를 놓친다) — 챗 그림 읽기 쪽 세션 몫(RF-13)
- [x] PC 키트 반영 — 포털 · 게이트웨이 push · 병합 · 게이트웨이 재기동(kit_get 이 생긴다 · 변환기 파일은 포털 리포 받기만으로 새 판), 업데이트 이력 항목 — 게이트웨이 `fe5e14c0` · 포털 `bcdc1cb1` · 이력 `58e6e680`, dev 확인 11-02(kit 으로 받은 변환기가 리포 파일과 같음)
- [ ] 실제 Windows PC 에서 한 번 — UNC · 드라이브 경로 · cp949 콘솔 · 사내 인증서(PAT 받기) · Word 로 열어 표 칸 그림 보기(RF-20)
- [ ] 현장 변환기(md2docx_z.py) 정리 · 개인 Claude 지침에 'docx 는 kit_get 의 변환기로' — 사용자 PC 몫
- [x] MX 백서 문서에 그림 — 게이트웨이 `figure_to_doc`(그 사람 위임 토큰 · upload_image_bytes → insert_image_block) · MX 백서 401 꼴도 토큰 거절 — 11-02
- [x] dev 끝에서 끝까지(11-02, 사용자 승인 — 시험 신원 figsmoke 가 MX 백서 dev 에 편집자로 저절로 생김) — render_3d → figure_to_doc ok · 개요에 그림 블록 · 같은 그림 다시는 deduped · 블록 둘 지움, 빈 시험 문서 하나는 MX 백서 세션에 지워 달라고 함(도구집에 문서 지우기 없음)
- [x] 단면 지도 · 타겟 파트 강조 색(StepForge a79 `e4d7bd8` · Drive `dist-20261104-135504Z`, RF-34) — dev 게이트웨이 도구 184 · `section_atlas` 읽기
- [ ] cae00 — 단면 지도 도구 · 새 반입의 지도 상태(받은 편지함 2026-11-04 Q4)
- [ ] 후속 — 일회성 세션의 결과 뒤 tools/list 401 로 쓰기 도구가 두 번 도는 틈(RF-26)


## SVG 그림을 격리 iframe 으로(사용자 결정 11-05, RF-36)

- [x] `renderers/svgFrame.ts` — 같은 출처 `.svg` 판정 · 칸 맞춤 배율 · 확대 무대 맞춤(순수 셈)
- [x] `Figure.tsx` — SVG 는 원래 크기 iframe(sandbox="") + 변형 · 넓으면 가로 스크롤 · 확대 아이콘만 눌림 / `Lightbox.tsx` — SVG iframe 갈래 · 원본 링크 — 포털 `2ff8d56d`
- [x] 에이전트 서버 `_stash_image_items` — 내용으로 꼴 · 8 MiB 상한 — `79953ac`(dev 재기동 — 도는 심의 0)
- [x] 시험(node 로 셈 · 소스 단언 · 에이전트 서버) · 빌드(dev main 체크아웃 — 표식 맞음) · 올리기
- [x] Drive 이미지 판(cae00 화면 — `images-to-drive.sh`) — `images-20261105-092549Z`(뷰어 카드와 묶음)

## StepForge 단면 · 적층 도구 넷의 읽기 표지(사용자 결정 11-08, RF-39)

- [x] 영향 조사 — 읽기 전용 PAT · 루틴이 넷을 거절(RF-29 와 어긋남) · 챗 확인 관문 · 심의 · 리스크 앱은 그대로
- [x] 사용자 결정 — RF-29 유지(게이트웨이 읽기 목록 덧씌우기)
- [x] 게이트웨이 `read_tools.json` override 칸 · 읽기 전용 PAT · 루틴 단계 · 쓰기 분류가 먼저 본다 — `290f324`(병합 `2d0ec28`) · 참조 고침 `c47e883` ·
      시험 하나 더 · 변이 셋 붉음 · 전체 940 통과
- [x] dev 재기동 · `/tools-map` 확인(넷이 routine_read · panel_read, write 밖)
- [ ] cae00 — update-all 로 받는다(게이트웨이 재기동) · 확인은 받은 편지함 2026-11-07 Q5

## 챗 단면을 기본 호버 SVG 로 — PNG + SVG 짝(사용자 결정 11-13, RF-40)
- [ ] StepForge — 네 도구에 `format="png+svg_live"`(글 + PNG + SVG 짝 · 짝 표지 · 기본은 png 그대로) — 요청 보냄, 일곱째 묶음 뒤
- [ ] 에이전트 서버 — `_CHAT_ARG_DEFAULTS` 에 네 도구 · 짝을 같은 줄기로 저장 · 모델에게 SVG 는 답에, PNG 는 판독용 · `/보고서` 는 짝 PNG 로 — StepForge 착지 뒤
- [ ] 게이트웨이 그림 보관 — 짝이 오면 `figure_to_report` 가 PNG 를 고르는지
- [ ] dev 실호출 — 챗에서 단면을 부르면 호버 SVG 가 보이고 모델이 그림을 읽는지 · `/보고서` 그림이 PNG 인지

