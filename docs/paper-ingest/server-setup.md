# 논문 업로드 중계 — cae00 사람 몫

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 고친 날 2026-11-05(KST). dev 쪽(Drive 자리 · 당기기 · 인입 cron)은 걸어 두었다 —
cae00 이 송출 cron 하나만 걸면 업로드가 dev 인입 · 논문 레코드까지 흐른다.

## 1. 확인(읽기)

```bash
rclone listremotes                                                  # dev 와 같은 Drive 를 보는 리모트 — update-all §3 이 AIDataHub 덤프에 쓰는 것(대개 ApptainerImages:)
rclone lsf <리모트>:paper-ingest/                                    # from-cae00/ 가 보이면 같은 Drive 다(dev 가 만들어 두었다)
ls -d ~/Projects/HEAXHub/var/app_data/paper_ingest /data/appdata/paper_ingest 2>/dev/null   # PaperIngest 의 호스트 app_data — 그 아래 _inbox
ls -d ~/Projects/PaperIngest 2>/dev/null || echo "리포 없음"         # 송출 스크립트가 든 리포
```

- 앱은 컨테이너 안에서 `INBOX_DIR=/data/appdata/paper_ingest/_inbox`(포털 `infra/env-kits/paper-ingest.env`)로 받는다 — 그것에 맞는 **호스트 경로**를 쓴다.
- 리포가 없으면 `cd ~/Projects && git clone https://github.com/squall321/PaperIngest.git` — 스크립트만 쓴다(앱은 HEAX 가 띄운 그대로).

## 2. 송출 cron 걸기(박스 바꾸기)

```bash
crontab -e   # 한 줄 더한다 — <리모트> · <app_data> 는 1절에서 본 값
*/30 * * * * DRIVE_OUTBOX=<리모트>:paper-ingest/from-cae00 INBOX_DIR=<app_data>/paper_ingest/_inbox /bin/bash $HOME/Projects/PaperIngest/scripts/to_drive_pusher.sh move >> $HOME/paper-ingest-push.log 2>&1  # PaperIngest 중계
```

- **move 로 건다** — 올린 것은 cae00 에서 지운다. dev 가 Drive 에서 move 로 당기므로 copy 면 같은 업로드가 다시 올라간다.
- 업로드가 없으면 `송출할 신규 업로드 없음` 한 줄로 끝난다(비어 있는 지금 상태).

## 3. 확인

- 시험 업로드 하나(되도록 실제로 넣을 논문) → 30분 안에 `paper-ingest-push.log` 에 송출 줄 → dev 틱이 당겨 인입 → 다음 날 update-all §3 병합 뒤 챗에서
  그 논문 제목으로 찾힌다. 송출이 됐는지까지만 받은 편지함으로 알린다(dev 쪽 기록은 dev 세션이 본다 — `~/paper-ingest-relay.log` · 코퍼스 `_index/inbox.log`).
