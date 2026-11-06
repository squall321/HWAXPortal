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

## 11-06 — 왜 Drive 에 아무것도 없었나(사용자 물음 「paper ingest 구글 드라이브에 올리는 건 왜 안 됐나 — 실제 데이터가 없다」)

**PI-4 사실 넷.** ① Drive `ApptainerImages:paper-ingest/from-cae00/` 는 비어 있다 — cae00 이 한 번도 올리지 않았다. ② dev 틱은 30분마다 정상으로 돌고
(`~/paper-ingest-relay.log`) dev 받는 폴더도 비어 있다(기록의 '대기 폴더 1 항목' 은 셈 결함 — PI-7). ③ cae00 송출 cron 은 '사람 몫' 으로 `server-setup.md` 와
0절 줄에만 적었고 **받은 편지함에 싣지 않았다** — cae00 세션이 update-all 에서 보는 것은 받은 편지함이라 알 길이 없었다(11-05 내 빠뜨림). ④ 사용자 확인
(11-04) — cae00 PaperIngest 에는 업로드가 없다. 송출 cron 이 있었어도 올릴 것이 없었다. 받은 편지함 [2026-11-06 Q4](../cae00-inbox/2026-11-06.md).

**PI-5 11-05 커밋 뒤 SIF 를 Drive 로 보내지 않았다.** 앱 리포에 무엇이든 push 하면 cae00 허브는 커밋이 바뀐 것을 보고 SIF 열쇠를 견주는데(앞 판 SIF 는 옛 커밋
열쇠), 맞지 않으면 짓기를 시도하고 cae00 은 못 지어 그 회차에 앱을 띄우지 않는다. drive-drift(11-06)가 ✗ — Drive `paper-ingest.sif` 는 옛 판(93 MB), dev 는
`4a6f5c7` 판(186 MB)이었다. 11-05 뒤 cae00 허브가 다시 떴다면 PaperIngest 가 꺼져 있을 수 있다 — 업로드 창구 자체가 없었을 수 있다. 11-06 `e03d6d2` 로 다시
지었고(dev 새 인스턴스 정상) Drive 에 올리는 것은 사람 몫이다(자동 모드가 막음 — `SLUG=paper-ingest bash ../DocForge/scripts/drive-push-sif.sh`).

**PI-6 절차서의 컨테이너 경로가 틀렸다.** server-setup 은 앱이 컨테이너 안 `/data/appdata/paper_ingest/_inbox` 로 받는다고 적었지만 매니페스트 launch.env 는
`INBOX_DIR: /data/_inbox` 이고 HEAX 가 컨테이너 `/data` 를 호스트 `<HEAXHub>/var/app_data/paper_ingest` 에 묶는다 — 호스트 경로는 `<app_data>/paper_ingest/_inbox`
(cae00 은 app_data 가 `/data/appdata`)로 같아 cron 의 값은 맞았다. 다만 송출기는 그 폴더가 없으면 '업로드 없음' 으로 0 을 돌려준다 — 경로가 틀려도 조용하다.
절차서에 폴더가 있는지 먼저 보는 걸음을 넣었다. 포털 `infra/env-kits/paper-ingest.env` 의 값은 PaperIngest 를 호스트로 띄울 때의 것이다(HEAX SIF 는 안 읽는다).

**PI-7 송출 스크립트 결함 둘(PaperIngest `e03d6d2`).** ① PATH 에 rclone 이 없을 때의 대체 길이 dev 절대경로(`/home/koopark/claude/HWAXPortal/infra/bin/rclone`)였다 —
리포가 `~/Projects` 인 cae00 에서 호스트 cron(PATH `/usr/bin:/bin`)이 rclone 을 못 찾으면 송출이 늘 '없음' 으로 멈춘다. 이 파일 자리에서 유도한 형제
`HWAXPortal/infra/bin/rclone`(bootstrap-rclone.sh 가 sudo 없이 두는 자리)으로 고쳤다. ② 당기기의 '대기 폴더 N 항목' 이 받는 폴더 자신까지 세어 비어도 1 이었다 —
이 진단에서 dev 에 무엇이 걸린 줄 알게 만들었다. 시험 셋을 더했다(전체 14).
