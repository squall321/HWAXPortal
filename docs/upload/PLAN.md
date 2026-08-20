# 챗 파일 업로드 — 계획

원래 계획 문서는 2026-08-19 deploy-all 사고(레포 origin 리셋)로 유실됐다. 이 문서는
그 사이 확인된 실제 인프라 위에서 다시 세운 것이다.

## 무엇을 왜 만드는가

사용자가 **포탈 챗에서 파일을 올려** 사내 데이터베이스에 데이터를 넣을 수 있게 한다.
지금은 데이터를 넣으려면 각 백엔드(MaterialTwin·AIDataHub·ReportArchive)의 도구를
개인 Claude 로 직접 불러야 한다 — 포탈 사용자는 못 한다.

요구(사용자 원문 정리).
- 챗에 파일을 그대로 올릴 수 있어야 한다.
- **메타데이터는 AI 가 채우고**, 못 채우는 것은 사용자가 직접 입력한다.
- 파일 종류는 다양하다(시험보고서·물성 원시데이터·문서·이미지 등).

## 확인된 인프라 — 새 저장 계층을 만들지 않는다

업로드 대상은 전부 이미 있는 백엔드 MCP 도구다. 포탈은 **받아서 → 검사·추출 → 확인 →
해당 백엔드 도구로 넘기는** 오케스트레이터만 된다.

| 대상 | 쓰기 도구 | 스키마 안내 도구 | 파일 검사 |
|---|---|---|---|
| 물성 DB(MaterialTwin) | `register_material` · `register_tensile_test` · `register_relaxation_test` | `list_property_definitions` · `how_to_measure` | — |
| AIDataHub 레코드 | `import_record(record: dict, dry_run=True)` | `describe_record_schema` | `inspect_file` · `convert_file` |
| ReportArchive | `upload_file` · `upload_from_url` · `prepare_upload` | `describe_template` · `describe_metadata` | — |
| 원시 표 데이터 | — | — | `parse_raw_rows`(thermal-shock) |

핵심 — `import_record` 는 **dry_run=True 가 기본**이다. AI 가 채운 메타데이터를 넣기 전에
검증만 돌려 사용자에게 보여줄 수 있다. 이게 "AI 가 채우고 사람이 확인" 의 자연스러운 축이다.

## 흐름 (4단계)

```
[A] 첨부·수신        챗 입력에 파일 첨부 → 포탈이 multipart 로 받아 스테이징에 저장
[B] 검사·메타추출    파일 종류 판별 → inspect_file/convert_file/parse_raw_rows 로 구조 파악
                     → 대상 백엔드 스키마(describe_*)를 받아 AI 가 메타데이터 초안 작성
[C] 확인·보완        추출 결과를 폼으로 보여줌 → 못 채운 필드는 사용자 입력
                     → dry_run 으로 검증 결과 미리보기
[D] 확정·기록        해당 백엔드 쓰기 도구로 넘김(dry_run=False) → 결과·링크 반환
```

## 범위 — 1차에 하는 것 / 안 하는 것

**한다.**
- 챗 첨부 UI + 포탈 수신 엔드포인트(`POST /agent/upload`, multipart).
- 스테이징 저장(디스크, TTL 로 정리 — 무기한 누적 금지).
- 대상 백엔드 1곳 먼저 — **물성 DB**(이번 세션 내내 초점이었고 수요가 명확).
- AI 메타 추출 + 사용자 보완 폼 + dry_run 미리보기.

**안 한다(2차).**
- 나머지 백엔드(AIDataHub 레코드·ReportArchive) — 같은 틀에 대상만 늘리면 된다.
- 대용량 스트리밍 업로드(수백 MB). 1차는 상한을 둔다.
- 이미지 OCR·표 자동 인식의 고도화 — 1차는 파싱 도구가 주는 만큼만.

## 확정 결정 (2026-08-20, 사용자 승인)

- **1차 대상 — 물성 DB(MaterialTwin) 만.** register_material·register_tensile_test·
  register_relaxation_test. 나머지 백엔드는 2차에 같은 틀에 대상만 교체.
- **업로드 권한 — 특정 그룹만.** 물성 DB 는 정본이라 오염되면 파급이 크다. 업로드 권한
  그룹(예: 물성 담당)에게만 챗 첨부 버튼이 보이고 쓰기가 된다. 그룹 밖 사용자는 첨부
  UI 자체가 안 뜨고, 백엔드도 그룹을 재검증해 거부한다(프론트 숨김만으론 부족 — 두 층).
- **dry_run 검증 — 필수 통과.** dry_run 이 통과하고 사람이 명시 승인해야만 확정된다.
  dry_run 이 오류를 내면 확정 버튼 자체가 비활성. AI 초안을 사람이 안 보고 확정하는
  경로를 만들지 않는다.

## 결정과 제약 (이 세션 교훈 반영)

- **크기 상한 필수.** 422 가 페이로드를 통째로 되싣던 사고(5MB→5MB)가 있었다.
  업로드도 상한을 넘으면 파일을 응답에 안 싣고 사유만 반환한다.
- **스테이징 정리.** 임시파일을 안 지워 /tmp 에 쌓인 사고가 있었다. TTL + 확정 후 삭제.
- **인증은 기존 PAT 흐름을 탄다.** 업로드는 쓰기라 사용자 자격증명이 반드시 필요하다 —
  서비스 계정으로 강등되면 안 된다(무음 강등 가시화와 같은 원칙). 강등 시 업로드는 거부한다.
- **dry_run 을 건너뛰지 않는다.** 사람이 확인 안 한 데이터가 DB 에 들어가면 안 된다.
- **VERIFY.** 각 단계는 "무엇을 호출해 무엇을 보는가" 로 검증한다 — checklist.md 참조.
