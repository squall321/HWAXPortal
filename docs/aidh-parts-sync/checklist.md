# AIDataHub 조각 스냅숏 — 할 일

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 날짜는 KST.

## AIDataHub(dev 내기)

- [x] `parts-to-drive.sh` — 표 · 열 · 조각 규칙, 이진 COPY + gzip 시각 0 + 내용 해시 이름, pre-data 스키마, 목록(JSON), 새 조각만 올리기, 목록 7판 · 안 가리키는 조각 지우기 · 한 시점(AP-4) — AIDataHub `2f6d60b`
- [ ] dev cron(전체 덤프 뒤) — **사용자 몫**: 넣으려던 줄은 자동 모드 분류기가 막았다(AP-15). 그동안은 낡음 검사(AP-14)가 cae00 을 전체 덤프 길로 돌린다

## AIDataHub(cae00 받기 · 병합)

- [x] `fetch-parts.sh` — 목록 받기 · 지난 목록과 견주기 · 다른 조각만 받기(박스 캐시) · 계획 파일 · 변화 없음은 끝 코드로(10 · 목록 없음 4) · 병합 뒤 `--commit` 으로 표식
- [x] `merge-from-drive.sh` 조각 길(`AIDH_MERGE_PARTS=1` · `AIDH_MERGE_PARTS_PLAN`) — 스키마로 빈 스테이징 · 받은 조각만 싣기 · 병합 규칙 그대로 · 표본은 전문가 조각이 바뀌어도
- [x] 덮을 줄의 앞 모습 · 새 키 남기기(조각 길) + `rollback-parts.sh`(순번은 앞으로만) · 보관은 포털 `backup-local.sh` 가 같은 일수로(AP-8)
- [x] 같은 줄은 다시 쓰지 않기(바뀐 시각 칸이 없는 표 — 두 길 모두) — AIDataHub `ac6f788`

## 포털

- [x] update-all §3 — 조각 길 먼저(목록 · 스크립트가 있으면), 없거나 실패면 전체 병합(AP-7) · 잠깐 끄기 `AIDH_SYNC_MODE=full`
- [x] 시험 — §3 갈래(조각 · 변화 없음 · 3 · 실패에서 전체로 · 목록 없음 · 받기 실패 · 끄기 · 옛 판 · 표식 실패) `test_update_all_aidh_merge` · 앞 모습 보관 `test_request_1027_backup`

## 시험(AIDataHub)

- [x] 실제 PG16 + pgvector 임시 클러스터 — 내기 → 받기 → 병합이 전체 병합과 같은 결과 · 변화 없음 · 레코드 하나 · dev 에만 있는 열 3 · 표본 · 되돌리기 · 해시 결정성 · 목록 없음 · 해시 다름 · KEEP · 한 시점(`test_parts_sync_pg` 9, 변이 11 붉음)
- [x] 대역 시험(지금의 test_merge_from_drive 꼴) — 같은 줄 덮기 조건(조각 길의 스테이징 · 스냅숏 생략은 실 PG 시험이 본다)

## 반영

- [x] dev 실데이터로 내기 한 번(크기 · 시간) · Drive 에 첫 목록 — 264 파일 · 6.4 GiB · 1,719초 + 올리기 708초, 실 Drive 받기 확인(같은 목록 10 · 바뀐 조각만 38 MB · 낡지 않음)
- [ ] cae00 — server-setup(첫 조각 병합은 조각 전부 — 지금 병합보다 빠르다), update-all 로 받기
- [x] 업데이트 이력 · CLAUDE.md · 메모리 · 0절 줄(`docs/request-1030/server-setup.md`) · 받은 편지함 2026-11-05

## 자식은 레코드를 이긴 쪽을 따른다(사용자 결정 11-05, AP-16)

- [x] `merge_table` — 자식 표(record_sections · record_attachments · agent_records)는 운영이 더 새로운 레코드의 dev 줄을 덮지도 넣지도 않는다(두 길 모두) · 건너뛴 수를 말한다 — AIDataHub `0a88950`
- [x] `aidh_parts.py plan` — 자식 조각을 실으면 같은 k 의 레코드 조각도
- [x] 시험 — 실 PG(두 길이 같은 결과 · 이 박스가 이긴 카드의 절 · 첨부 · 연결은 그대로 · 자식 조각만 바뀌어도 레코드 조각을 싣는다 · 되돌리기) · 대역 · 변이 넷 붉음 · 전체 490
- [x] 올리기(AIDataHub `918681d`) · 0절 줄 · 업데이트 이력

