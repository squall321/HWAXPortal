# 논문 업로드 중계 — cae00 사람 몫

계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md). 고친 날 2026-11-06(KST — PI-4 ~ PI-7). dev 쪽(Drive 자리 · 당기기 · 인입 cron)은 걸어 두었다 —
cae00 이 앱을 새 SIF 로 받고(0절) 송출 cron 하나만 걸면 업로드가 dev 인입 · 논문 레코드까지 흐른다. 확인 결과는 받은 편지함 [2026-11-06 Q4](../cae00-inbox/2026-11-06.md)로.

## 0. 앱이 떠 있는지 · 새 SIF(PI-5)

11-05 PaperIngest 커밋 뒤 Drive SIF 가 옛 판이라, 그 뒤 허브가 다시 떴다면 PaperIngest 가 꺼져 있을 수 있다(열쇠가 맞지 않아 짓기를 시도하고 cae00 은 못 짓는다).

```bash
curl -s -o /dev/null -w '%{http_code}\n' --noproxy '*' http://127.0.0.1:4180/apps/paper_ingest/health    # 200 이 아니면 꺼져 있다(허브 Caddy 포트는 박스 값)
rclone cat <리모트>:HEAXHub/dist/latest/SHA256SUMS | grep paper-ingest                               # dev 가 e03d6d2 판을 올렸는지(판은 0절 표 줄)
cd ~/Projects/HEAXHub && bash deploy/apptainer/dist-from-drive.sh && bash deploy/apptainer/redeploy-app.sh paper-ingest
```

## 1. 확인(읽기)

```bash
rclone listremotes                                                  # dev 와 같은 Drive 를 보는 리모트 — update-all §3 이 AIDataHub 덤프에 쓰는 것(대개 ApptainerImages:)
rclone lsf <리모트>:paper-ingest/                                    # from-cae00/ 가 보이면 같은 Drive 다(dev 가 만들어 두었다)
ls -d ~/Projects/HEAXHub/var/app_data/paper_ingest /data/appdata/paper_ingest 2>/dev/null   # PaperIngest 의 호스트 app_data — 그 아래 _inbox
ls -d ~/Projects/PaperIngest 2>/dev/null || echo "리포 없음"         # 송출 스크립트가 든 리포
```

- 앱은 컨테이너 안 `/data/_inbox`(매니페스트 launch.env)에 쓰고, HEAX 가 컨테이너 `/data` 를 호스트 `<HEAXHub>/var/app_data/paper_ingest` 에 묶는다 — 호스트 경로는
  `<app_data>/paper_ingest/_inbox` 다(cae00 은 app_data 가 `/data/appdata`). 그 폴더가 없으면 아직 업로드가 한 번도 없는 것이다 — 송출기는 그때도 '업로드 없음' 으로
  0 을 돌려주므로(경로가 틀려도 같다) **폴더가 있는지 먼저 본다**. 포털 `infra/env-kits/paper-ingest.env` 의 값은 호스트로 띄울 때의 것이다(PI-6).
- rclone 이 호스트 cron 의 PATH(`/usr/bin:/bin`)에 없으면 — 송출기 `e03d6d2` 부터는 형제 `~/Projects/HWAXPortal/infra/bin/rclone` 을 저절로 찾는다. 다른 자리면 cron 줄에
  `RCLONE_BIN=<경로>` 를 더한다(PI-7).
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
