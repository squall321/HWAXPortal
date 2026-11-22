# 문서 → RA 정밀 변환(DocForge) — cae00 설정 · 확인(사람 몫)

> 대상 — cae00 에서 update-all 을 돌리고 관리자 화면을 여는 사람. dev 쪽 배치(DocForge SIF · Drive · 등록 사본)는 끝난 뒤다.
> 결정의 근거는 [context-notes.md](context-notes.md) DF-D17 ~ DF-D20, DocForge 쪽 배치 정본은 DocForge `docs/DEPLOY.md` §4 · §7.
> 비밀 · 내부 주소는 여기 적지 않는다 — 값은 박스 파일(`infra/.env` · `HEAXHub/.env`)에만.

## 0. 이번 배치로 무엇이 열리나

| 무엇 | 어디서 보이나 | 누가 |
|---|---|---|
| 챗 업로드 목적지 「Report Archive — 정밀 변환(배치 유지 · 그림 판독)」 — PPTX · DOCX · XLSX · PDF · PC 도우미 추출본 | 파일을 올린 뒤 '어디로 보낼까요' | `feat:upload` + `plat:reportarchive` + `plat:docforge` |
| '이 대화에서 분석' 을 DocForge 가 읽음(차트 값 · SmartArt · 수식 · 노트 · 병합 표) | 같은 목적지 목록의 맨 앞 | `plat:aidatahub` + `plat:docforge`(없으면 지금처럼 AI 데이터 허브) |
| HE팀 운영자 「DocForge 문서 정밀 변환 운영자」(`he-doc-docforge`) | 전문가 · 조직도 | 페르소나 동기화 뒤(§5) |

⚠ 권한표에서 **CAEG 소속은 `grants: ["*"]`** 이라 `plat:docforge` 를 따로 주지 않아도 갖는다 — DocForge 가 게이트웨이에 실리는 순간 CAEG 사람들에게
바로 열린다. 그 밖의 소속 · 사람은 §4 에서 준다.

## 1. 한 번만 적는 값 — `~/Projects/HEAXHub/.env`

```
APPTAINERENV_DOCFORGE_INPUT_ROOTS=<포털 업로드 스테이징의 호스트 절대경로>
```

- **필수.** 없으면 DocForge 가 '경로 입력이 닫혀 있다 — DOCFORGE_INPUT_ROOTS 가 비었다' 로, 스테이징과 다르면 '허용된 입력 뿌리 밖의 경로다' 로
  모든 변환을 거절한다(포털은 스테이징의 호스트 경로를 넘긴다).
- 값 — 포털 `infra/.env` 에 `HWAX_UPLOAD_STAGING` 이 있으면 그 값, 없으면 `$HOME/.hwax/upload-staging` 의 절대경로(포털 start.sh 의 기본).
- 선택 — `APPTAINERENV_DOCFORGE_HOST_DATA_DIR=<~/Projects/HEAXHub/var/app_data/doc_forge 의 절대경로>`(패키지 요약에 호스트 경로를 싣는 데만 쓴다 —
  포털은 쓰지 않는다).
- 그림 판독(VLM) 끝점은 적지 않는다 — 포털 `infra/.env` 의 `CHAT_LLM_*` 를 update-all 1g2 가 허브로 맞춘다(DF-D16). 챗을 stcx Qwen 으로 쓰는 박스면 이미 있다.
- 선택 — **SP 허브 연결**(보고서 첫 쪽 '연결된 과제 · 모델', DocForge E13 · E14). 허브 관리자가 API 루트 주소와 core:read 토큰을 주면 — 주소는 이 파일에
  `APPTAINERENV_DOCFORGE_SP_CORE_URL=<허브 API 루트>` 한 줄, 토큰은 `~/Projects/HEAXHub/var/app_data/doc_forge/secrets.env` 에 `DOCFORGE_SP_TOKEN=<토큰>`
  한 줄(따옴표 없이 · `chmod 600` · 이 이름은 Drive 백업이 뺀다). 없으면 연결 칸이 생기지 않을 뿐 변환은 같다. 확인 — capabilities 의
  `ontology.sp_configured` 참 · 한 시간 안에 `ontology.last_sync.status` 가 ok.

## 2. 포털 쪽 — 보통 할 일 없음

| 값 | 기본 | 바꿀 때 |
|---|---|---|
| `DOCFORGE_PACKAGE_ROOT`(포털이 패키지를 읽는 곳) | start.sh 가 `<포털 리포>/../HEAXHub/var/app_data/doc_forge` 의 호스트 경로로 넘긴다 | HEAXHub 가 형제 자리가 아니면 `infra/.env` 에 `HWAX_DOCFORGE_DATA=<절대경로>` |
| `DOCFORGE_RA_FILE_MAX_MB`(RA 에 올릴 리소스 상한) | 25(RA `upload_max_bytes` 기본) | RA 상한을 바꾼 박스면 `backend/.env` 에 같은 값 — 넘는 리소스는 올리지 않고 그 칸을 비우고 알린다 |
| RA 명의(정밀 변환 배달) | 'Report Archive 로 보내기' 와 같은 길 — `RA_SSO_SECRET`(위임) 또는 사람마다 '외부 연결' 토큰 | 이미 RA 보내기가 되는 박스면 그대로 |

HEAXHub 가 `$HOME` 밑이어도 그 `var/app_data` 가 `/data` 로 가는 심링크면(/data 이관 뒤의 dev · cae00) 링크 끝이 포털 컨테이너에 없다 —
10-25 점검 전까지 이 줄은 'cae00 은 `~/Projects` 라 해당 없다' 였고 틀렸다(dev 컨테이너 실측: `/data` 에 appdata 가 없어 모든 배달이
'패키지를 찾지 못했다'). 이제 `start.sh` 가 데이터 루트를 끝까지 따라가 `$HOME` 밖이면 그 경로를 **읽기 전용**으로 바인드한다(사람이 할 일 없음 —
포털을 다시 띄우면 선다). 확인: `readlink -f ~/Projects/HEAXHub/var/app_data` 가 `/data/...` 면 바인드가 붙고, 포털 재기동 뒤
`apptainer exec instance://hwax_portal ls <그 경로>/doc_forge` 가 보인다.

## 3. update-all

1. **처음 한 번만** — PDF 를 읽는 Docling 모델 무게를 받는다(PPTX · DOCX · XLSX 는 필요 없다).
   ```bash
   cd ~/Projects/HEAXHub && HEAX_MODEL_APPS="doc_forge" bash deploy/apptainer/models-from-drive.sh
   ```
2. `~/Projects/HWAXPortal/infra/scripts/update-all.sh` — 순서가 안전하다. 맨 처음(1)에 포털 리포를 받고, 포털은 권한표를 파일 시각으로 다시 읽으며,
   게이트웨이는 그 정책을 60초마다 받는다. 허브 앱 배치(§2 — DocForge SIF · status beta)는 몇 분 뒤라 게이트웨이가 `heax-doc_forge` 의 권한
   (`plat:docforge`)을 먼저 안다(표에 없는 키는 '전체 공개' 라 이 순서가 중요하다).
3. 화면(SPA)은 dev 가 지어 Drive 로 보낸다. update-all 의 헬스게이트가 '화면이 지금 소스로 지은 것이 아니다' 를 찍으면 dev 에서
   `./infra/scripts/build-all-to-drive.sh portal` 을 다시 돌린 뒤 update-all 을 한 번 더 한다.

## 4. 권한 — 관리자

- CAEG 소속은 할 일 없음(`*`).
- 다른 소속 · 사람 — 관리자 화면 `/admin/users` 에서 소속 기본 허가 또는 개별 허가로 `plat:docforge` 를 준다. 정밀 변환 목적지는 `feat:upload` ·
  `plat:reportarchive` 도 있어야 보인다.
- 끄려면 — 허가를 거두면 목적지가 사라지고, '이 대화에서 분석' 은 AI 데이터 허브 길로 돌아간다.

## 5. 페르소나 동기화

update-all 은 페르소나를 만들지 않는다. DocForge 가 게이트웨이에 실린 뒤(§6-②) 한 번.

```bash
cd ~/Projects/HWAXPortal
python3 infra/scripts/sync-he-personas.py           # 미리보기 — he-doc-docforge 가 '새로' 로 보여야 한다
python3 infra/scripts/sync-he-personas.py --apply   # 반영
```

미리보기에 다른 운영자의 '고친다' 가 같이 보이면 그것은 정본과 AIDataHub 사본의 어긋남이다 — 함께 반영해도 정본대로 맞춰질 뿐이지만, 낯선
변경이 있으면 그 운영자 담당에게 먼저 묻는다.

## 6. 확인

1. DocForge — `curl -s http://127.0.0.1:<포트>/health`(포트는 `~/Projects/HEAXHub/var/integration_state/doc_forge.json`). 브라우저
   `/apps/doc_forge/api/v1/capabilities` 에서 `version` 0.3.0 · `input_roots` 1 이상 · `soffice` · `korean_fonts` 참 · `vlm.source` 가 `chat_llm`.
2. 게이트웨이 — `bash infra/scripts/check-mcp-registration.sh doc_forge` → `curl -X POST localhost:9110/refresh` → `curl -s localhost:9110/tools-map` 에
   `docforge_` 다섯(capabilities · convert · status · package · cancel). 정책 캐시(`HWAXMcpGateway/.access_policy_cache.json`)에
   `"heax-doc_forge": ["plat:docforge"]`.
3. 끝에서 끝 — 챗에서 PPTX 하나를 올려 「Report Archive — 정밀 변환」 → 진행 표시 → '정밀 변환 보고서를 만들었습니다' 와 대화 알림(쪽 · 블록 ·
   버린 요소 · 모델 판독 · 무음 누락 0) → 링크로 RA 보고서(내 공간 · 초안).
4. DRM — 'PC 의 PowerPoint 로 열어 가져오기' 로 받은 뒤 다음 단계에서 정밀 변환 → 알림에 'PC 추출본으로 만들어 충실도가 낮습니다'.
5. 이 대화에서 분석 — 같은 PPTX 로 → '문서를 읽는 중' → 문서 칩(머리말 `extracted_by: DocForge 0.3.0`).

## 7. 막히면

| 보이는 것 | 까닭 · 할 일 |
|---|---|
| 'DocForge 가 변환을 맡지 않았습니다 — 경로 입력이 닫혀 있다 …' · '… 허용된 입력 뿌리 밖의 경로다' | §1 의 `APPTAINERENV_DOCFORGE_INPUT_ROOTS` 가 없거나 스테이징 경로와 다르다 → 고치고 허브 재기동(update-all) |
| 'RA 가 보고서를 만들지 않았습니다 … __import_blank__' | 이 RA 에서 문서 가져오기를 한 번도 안 썼다 → RA 웹 '가져오기' 또는 'Report Archive 로 보내기' 를 한 번 쓰면 템플릿이 생긴다 |
| '패키지를 찾지 못했습니다 — 포털이 DocForge 데이터 루트를 보는지' | §2 의 DOCFORGE_PACKAGE_ROOT — 포털 컨테이너에서 `HEAXHub/var/app_data/doc_forge` 가 보이는지 |
| 'DocForge 가 읽을 글(document.md)을 만들지 않았습니다' | DocForge 가 0.3.0 보다 낡았다 → Drive 의 doc-forge.sif 판 확인(capabilities 의 version) |
| 목적지가 안 보인다 | §4 권한 — 그리고 DocForge 가 게이트웨이에 실렸는지(§6-②) |
| 리소스 'RA 상한을 넘어 올리지 않았습니다' 경고 | 25MB 넘는 그림 · 원본 첨부 — 보고서의 그 칸이 비었다. RA 에서 원본을 직접 붙인다 |

되돌리기 — 게이트웨이에서 내리려면 HEAXHub 등록 사본의 `status: draft` 로 update-all(DocForge `docs/DEPLOY.md` §8). 정밀 변환 목적지만 숨기려면 §4 의 허가를 거둔다.

## 8. 금 표본 기준선 둘 — 돌리는 명령 · 채점은 아직 없다(11-22)

> PLAN §10 · DocForge `docs/EVAL.md` §3 · `docs/M0.md` §9 의 기준선 ① 포털 'Report Archive 로 보내기' ② AIDH `convert_file` 을 금 표본에 돌리는 법이다.
> 대조 — 포털 `09693c6f`(`backend/app/agent/routes.py` `_dispatch_inner` · `upload.py`) · AIDataHub `b2f1b72`(`mcp_runtime.convert_file` →
> `mcp_write_svc.run_convert`) · DocForge `21ec48c`(`scripts/eval/run.py` · `edits.py`). 코드로 맞춘 명령이고 실호출로 돌려 보지는 않았다 — 금 표본 첫 회에
> 문서 하나로 먼저 돌린다.

### 8-1. 무엇이 있고 무엇이 없나

| | 돌리기(변환 결과 받기) | 채점(EVAL §2 지표) |
|---|---|---|
| ① 'Report Archive 로 보내기' | **있다** — 챗 업로드와 같은 포털 창구 둘(`POST /agent/upload` → `POST /agent/upload/dispatch`, 목적지 `reportarchive`). PPTX 만(RA `/api/imports/pptx` 가 받는 것이 이것뿐) | **없다** |
| ② AIDH `convert_file` | **있다** — 같은 창구, 목적지 `aidatahub`(포털이 파일을 AIDH inbox 에 두고 그 사람 PAT 로 `convert_file` 을 부른다 — 저장하지 않는다). PPTX · DOCX · XLSX | **없다** |
| 사람 편집량(EVAL §5) | ① 만 — 가져오기 **직후** `edits.py snap` | 있다 — `edits.py diff`(갈래 `baseline`) |

채점이 없는 까닭 — DocForge `scripts/eval/run.py` 는 DocForge 패키지만 읽는다(`Delivered` 가 `report.json` · `conversion.json` · `ir.json` 을 함께 연다).
①의 결과는 RA 보고서(저장 꼴 — `snap` 사본), ②의 결과는 AIDH record(`sections` · `tables` · `figures` · `meta`)라 그대로는 못 넣는다.
**지어야 할 것**(DocForge 몫 — 그쪽 `docs/checklist.md` 의 `[ ] 기준선 — 포털 RA 보내기 · AIDH convert_file`) —

- 기준선 채점기 — 같은 `<파일>.truth.json`(`scripts/m0/truth.py`)과 `run.py` 머리의 견주는 규칙으로 RA 보고서 사본 · AIDH record 를 잰다.
- 셀 수 있는 지표 — 글(text) · 수치(nums) · 표 칸(cells) · 병합(merges) · 차트 값(chart) · 그림(pics · emf) · 시간(아래 `seconds.tsv`).
- 기준선에 없는 지표 — 글 회계(acct)와 무음 누락(unacc)은 DocForge 변환 보고서의 회계로 센다. 기준선에는 그 보고서가 없다(①은 RA 가져오기의
  경고 `warnings` 만 있다 — 그것으로 셀지는 확인 필요). ②는 RA 보고서를 만들지 않아 RA 저장 검증 · 배치를 셀 것이 없다.
- 규칙을 새로 정할 곳 — XLSX 표 칸은 `run.py` 가 IR 범위(`Locator.path`)로 RA 표를 시트 좌표에 놓는데 기준선에는 IR 이 없다(확인 필요 — 표를
  어떻게 시트에 맞출지).
- DRM 5 — EVAL 에 기준선 · 정답 규칙이 없다(확인 필요).

### 8-2. 준비

- 돌리는 사람 — 포털 PAT(`/auth/pat`) 하나. 그 사람이 `feat:upload` · `plat:reportarchive`(①) · `plat:aidatahub`(②)를 가져야 하고, RA 를 그 사람
  명의로 부를 수 있어야 한다(위임 `RA_SSO_SECRET` 또는 '외부 연결' 토큰 — §2 의 'RA 명의' 줄과 같다).
- ①은 RA 에 **보고서를 실제로 만든다**(PPTX 하나에 하나). 자리는 그 사람의 RA 연결이 정한다 — 위임 토큰이면 RA 가 홈 부서 → 첫 조직 → 개인 공간 순으로
  고른다(포털 `_ra_workspace`). 금 표본이 부서 공간에 보이면 안 되면 돌리기 전에 정한다(사람). 이 RA 에서 가져오기를 한 번도 안 썼으면 §7 의
  `__import_blank__` 줄을 먼저.
- ②는 AIDH 에 저장하지 않는다. 포털이 inbox 에 둔 사본은 `AIDH_INBOX_TTL_HOURS`(기본 24시간) 뒤 지운다. 포털 스테이징은 `UPLOAD_STAGING_TTL_HOURS`
  (기본 6시간) 뒤.
- 시간 한도 — ②의 `convert_file` 과 ①의 보고서 만들기(`create_report_draft`)는 포털의 MCP 한 번 한도(90초 — `upload.mcp_call` 기본), ①의 RA 가져오기는
  600초에 걸린다. 넘으면 그 문서는 실패로 남는다(사람이 겪는 것과 같다 — 기준선의 몫이다). ①의 크기 한도는 `RA_IMPORT_MAX_MB`(기본 25).
- 파일 이름에 `;` · `,` · `"` 가 들면 `curl -F` 가 옵션으로 읽는다 — 그런 이름은 먼저 바꾼다.

### 8-3. 돌리기

포털 리포 루트에서. 결과 폴더는 리포 밖이고 파일 이름이 든다(EVAL §4 와 같이 표에는 지문만).

```bash
G=../DocForge/var/dev-data/gold                      # 금 표본(DocForge docs/M0.md §2) — 사람이 다른 곳에 두었으면 그 경로
O="$HOME/docforge-baseline-$(date +%Y%m%d)"; mkdir -p "$O/ra" "$O/aidh"; chmod 700 "$O"
H="$O/auth.hdr"; ( umask 077; printf 'Authorization: Bearer %s\n' "$HWAX_GATEWAY_PAT" > "$H" )   # PAT 는 명령줄에 싣지 않는다
P=http://127.0.0.1:8723/agent/upload
send() {   # send <파일> <목적지> <결과 폴더> — 올리기 → 보내기, 답과 걸린 초를 남긴다
  local f="$1" n t0; n=$(basename "$1"); t0=$(date +%s)
  curl -s --noproxy '*' -H @"$H" -F "file=@$f" "$P" > "$3/$n.upload.json"
  python3 -c 'import json,sys; u=json.load(open(sys.argv[1])); print(json.dumps({"staging_id": u["staging_id"], "filename": u["filename"], "destination": sys.argv[2]}))' \
    "$3/$n.upload.json" "$2" > "$3/$n.req.json"
  curl -s --noproxy '*' -H @"$H" -H 'Content-Type: application/json' --data-binary @"$3/$n.req.json" "$P/dispatch" > "$3/$n.json"
  printf '%s\t%s\n' "$n" "$(( $(date +%s) - t0 ))" >> "$3/seconds.tsv"
}
find "$G" -type f -name '*.pptx' | sort | while IFS= read -r f; do send "$f" reportarchive "$O/ra"; done                        # ①
find "$G" -type f \( -name '*.pptx' -o -name '*.docx' -o -name '*.xlsx' \) | sort | while IFS= read -r f; do send "$f" aidatahub "$O/aidh"; done   # ②
```

- 답 — ①은 `<이름>.json` 에 `stage: done` · `report_id` · `pages` · `blocks` · `warnings`, ②는 `stage: done` · `result.record`(AIDH 변환 결과).
  실패는 `stage: failed` · `error`, 포털 오류 본문 `{"detail": …}`(MCP 호출 실패는 502), 또는 `<이름>.upload.json` 의 오류(권한 · 크기)다.
- `send` 의 머리 파일 · 요청 꼴은 dev 의 가짜 받는 쪽으로 확인했다(11-22 — 머리 `Bearer` · 여러 부분 `file` · JSON 본문). 포털 · RA · AIDH 실호출은 아니다.

①의 RA 보고서를 **누가 고치기 전에** 사본으로 받는다 — 편집량(EVAL §5)의 처음 것이자 채점기의 입력이다. DocForge 리포에서(길 A — 길 B 면
`.venv/bin/python` 대신 `bash scripts/dev-in-sif.sh python` 이고 `--to` 는 `var/dev-data` 아래 — DocForge `docs/CAE00-DEV.md`). RA 주소 · 읽기 토큰은
DocForge 의 `DOCFORGE_EVAL_RA_URL` · `DOCFORGE_EVAL_RA_TOKEN`(EVAL §5 — 명령줄에 쓰지 않는다)이고, 토큰은 보고서를 만든 그 사람의 것이다.

```bash
cd ../DocForge
for j in "$O"/ra/*.pptx.json; do
  rid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("report_id") or "")' "$j")
  [ -n "$rid" ] && .venv/bin/python scripts/eval/edits.py snap --report "$rid" --to "${j%.json}.report.json"
done
```

끝나면 `rm -f "$H"`. 수치는 DocForge `docs/m0-results.md` 에(EVAL §4 처럼 이름 대신 지문), 결정은 DocForge `docs/context-notes.md` 와 이 폴더
context-notes 에 한 줄.
