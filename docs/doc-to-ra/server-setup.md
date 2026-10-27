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
