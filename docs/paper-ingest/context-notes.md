# 논문 업로드 중계 — 결정 기록

계획은 [PLAN.md](PLAN.md), 할 일은 [checklist.md](checklist.md)다. 날짜는 KST.

**PI-1 조사 · 사용자 결정(11-04 · 11-05) — 지금 길을 잇는다.** dev 의 받는 폴더(`/data/paper_patent_corpus/_inbox`)는 8-12 뒤 그대로였고, Drive 에 중계 자리가 없었고
(문서가 적은 리모트 `HeaxDrive` 는 dev 에 없다), dev cron 에 당기기 · 인입이 없었다. 코퍼스는 8-26 뒤로 자라지 않았다. 사용자 확인 — cae00 PaperIngest 는 비어 있다.
고른 안은 '지금 길을 잇는다'(버린 것 — cae00 에 먼저 묻기 · 그대로 두기).

**PI-2 업로드 하나는 한 번만 — 양쪽 move.** cae00 송출(`to_drive_pusher.sh move` — 올린 것은 로컬에서 비움) · dev 당기기(`from_drive_poller.sh move` — 당긴 것은
Drive 에서 지움, 이번에 모드를 더했다). 한쪽이 copy 면 루프가 생긴다 — dev copy 면 인입이 `_inbox` 에서 옮긴 논문을 다음 틱이 다시 당기고, cae00 copy 면 Drive 에서
사라진 것을 다시 올린다. Drive 자리는 `ApptainerImages:paper-ingest/from-cae00`(dev — AIDataHub 덤프와 같은 Drive)로 만들었다. cae00 의 리모트 이름은 박스에서 본다.

**PI-3 dev 한 틱(PaperIngest `scripts/dev_relay_tick.sh` — `dc51ccb` · `4a6f5c7`, dev cron 30분).** ① 당기기 ② 논문이 있으면 ExpertGrounding `run_inbox.sh`
(분류 · 증분 색인 · 그라운딩 — LLM 없음, CPU) ③ `agent_papers.json` 이 바뀌면 `erag export-papers --upload --bind`. 판단 —
- 인입의 `python3` 는 cron 의 PATH 로는 시스템 python 이라 FlagEmbedding · qdrant_client 가 없다(dev 실측 — ExpertAgents `.venv` 에만 있다) → 그 venv 를 PATH 앞에.
  qdrant 는 내장(경로) 모드라 서버가 없어도 된다.
- 논문 레코드 내기는 전체를 다시 내는 명령뿐인데(새것만 고르는 칸이 없다), AIDataHub 가 내용이 같은 레코드를 건너뛰어(`content_hash` — 가져오기 · 동기화 둘 다)
  바뀐 날짜가 오르지 않는다 → 매핑이 바뀐 틱에만 돌린다. 처음 틱은 지금 매핑을 기준(표식)으로 두어 2만여 편을 다시 내지 않는다. 실패면 표식을 두지 않아 다음 틱이 다시 한다.
- AIDataHub 키는 형제 리포 `AIDataHub/deploy/apptainer/.env` 의 `BOOTSTRAP_API_KEY` 를 실행 때 읽는다(그쪽 `import-from-drive.sh` 와 같은 선례) — 추적 파일에 비밀 없음.
- 카드 근거 반영(판정 → `apply_refs.py`) · 카드 레코드(`erag export-records`)는 사람이 본 뒤 — 틱에 넣지 않았다.
- 시험 다섯(빈 틱 · 새 논문이 끝까지 · 내기 실패 뒤 다시 · 앞 틱이 돌면 건너뜀 · 당기기 모드) — 변이 다섯이 붉다. dev 에서 cron 환경으로 한 틱을 돌려 표식이
  지금 매핑(8-25)으로 섰다.
