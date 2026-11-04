# 논문 업로드 중계 — cae00 PaperIngest → Drive → dev 인입 · 논문 레코드

사용자 물음 11-04 「논문 본문을 저장하는 프로젝트 — paper ingest 는 실제 데이터가 올라가서 동기화도 되고 있나」 → 사용자 결정 「지금 길을 잇는다」.
판단 기록은 [context-notes.md](context-notes.md), 할 일은 [checklist.md](checklist.md), cae00 사람 몫은 [server-setup.md](server-setup.md)다. 날짜는 KST.

## 1. 지금(11-04 조사)

- 논문 본문은 dev 의 코퍼스 `/data/paper_patent_corpus/`(분야별 원문 · `structured/` 아래 논문마다 md — md 118,096 · PDF 27,772 · 229 GB)에 있다. 8월 중순 ~
  8-26 에 한꺼번에 모았고 10-01 뒤로 새로 든 것은 0편이다.
- 챗 · 심의는 AIDataHub 의 `doc_type:paper` 레코드(메타 + 본문 절 전체)로 읽는다 — dev 논문 26,224건(ExpertAgents `erag export-papers` 로 8-19 ~ 8-20 적재).
- cae00 웹 업로드(PaperIngest — HEAX 앱 `paper_ingest`)에서 dev 까지의 길은 끊겨 있었다. cae00 송출 cron 도, Drive 자리도, dev 당기기 · 인입 cron 도 없었다.
  사용자 확인 — cae00 의 PaperIngest 는 비어 있다(옮길 밀린 업로드가 없다).

## 2. 이은 길

```
[cae00]  웹 업로드 → PaperIngest _inbox(app_data)
           │ 호스트 cron 30분 — PaperIngest scripts/to_drive_pusher.sh move(올린 것은 로컬에서 비움)      ← 사람 몫(server-setup)
[Drive]  <리모트>:paper-ingest/from-cae00                                                               ← 만듦(11-05)
           │ dev cron 30분 — PaperIngest scripts/dev_relay_tick.sh                                       ← 걸음(11-05)
[dev]    ① 당기기 move → 코퍼스 _inbox  ② ExpertGrounding run_inbox.sh(분류 · 증분 색인 · 그라운딩, LLM 없음)
         ③ 매핑(agent_papers.json)이 바뀌면 erag export-papers --upload --bind(같은 내용은 AIDataHub 가 건너뜀)
           │ 하루 한 번 — AIDataHub backup-to-drive → cae00 update-all §3 병합
[cae00]  논문이 챗 · 심의 검색에 든다
```

- 카드 근거 반영(판정 → `apply_refs.py`)과 카드 레코드(`erag export-records`)는 사람이 본 뒤 한다 — 틱은 하지 않는다.
