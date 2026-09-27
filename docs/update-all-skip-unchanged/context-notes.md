# context-notes — update-all 바뀌지 않은 것 생략

## D-1. 시간이 가는 자리는 다운로드와 무조건 재기동 둘이다 (2026-09-27)

cae00 두 번째 update-all 꼬리(D-28)를 보면 §2 는 여섯 서비스가 각각 Drive 에서 아티팩트 전량을 받고 stop→start 했고, §4 는 셋이 "Already up
to date" 인데 down→up 했다. Drive 가 ~2MB/s 라(ste 33MB 48초) SIF 수백 MB 짜리 서비스 하나가 수 분이다. 코드가 바뀐 날엔 정당한 비용이지만
대부분의 실행은 바뀐 게 없다 — 사용자는 ste 시크릿 하나 심으려고 그 전부를 기다렸다.

## D-2. 왜 지문(이름·크기·mtime)인가, 왜 내용 해시가 아닌가

SIF 는 수백 MB 라 매 실행 sha256 을 두 번(전/후) 재는 것은 heax(앱 SIF 여럿)에서 수십 초다. 이름·크기·mtime 은 즉시다. 그런데 오늘 다섯 스크립트가
전부 임시 디렉터리에 받아 `cp`(mtime 리셋)로 놓으므로 mtime 이 매번 바뀐다 — 그대로면 지문이 늘 다르고 생략은 한 번도 안 일어난다. 그래서
**받는 쪽을 먼저 고친다**: 영구 캐시에 `rclone copy`(원격 modtime 보존, 안 바뀐 파일 전송 0) → `cmp` 가 다를 때만 `cp -p`(modtime 보존).
`.env` 같은 작은 파일은 내용 해시로 지문에 넣는다.

## D-3. 살아 있는 인스턴스 밑의 SIF 를 같은 내용으로 덮어써도 깨진다

mxwp 블록 주석이 실사고를 적었다 — apptainer 인스턴스가 쓰는 SIF 를 덮어쓰면 squashfs 마운트가 깨져 그 안의 exec 가 전부 죽는다. 종전엔 항상
재기동해서 가려졌다. 재기동을 생략하려면 **덮어쓰지 않아야** 한다 → `hwax_install_if_changed`(cmp 같으면 손대지 않음). `cp -u` 는 안 된다 —
전환 첫 회에 설치본의 mtime(cp 시각, 최근)이 캐시(원격 modtime, 빌드 시각)보다 새로워 바뀐 SIF 를 건너뛴다.

## D-4. 재기동 생략의 조건 셋 — 지문 같음 · 살아 있음 · 강제 아님

지문이 같아도 죽어 있으면 띄운다(start 는 멱등). 지문을 못 구하면(경로 없음 등) 지문 문자열에 `missing:` 이 들어가 전/후가 같아도 —
같으니 생략된다 — 이건 맞다: 없던 것이 계속 없는 것은 변화가 아니다. 강제는 `HWAX_RESTART_ALL=1` 하나. 생략은 반드시 한 줄로 보이고 끝에 모아
다시 낸다(장부 파일 `HWAX_RESTART_SKIPPED_FILE`).

## D-5. §4 는 git 결과로, 단 §3.5 가 .env 를 고쳤으면 강제

services.py `update_one` 이 HEAD 전/후를 비교해 `unchanged` 를 말한다(문자열 "Already up to date" 를 믿지 않는다 — 커스텀 update 명령이 있는
서비스는 그 문구를 안 낸다). update-sites 는 `update` 를 먼저 돌리고 unchanged·살아 있음이면 down/up 을 건너뛴다. §3.5 apply-envs 가
agent-server `.env` 를 바꿨는데 코드가 안 바뀌었으면 §4 가 그 서비스를 건너뛰어 **옛 env 로 계속 도는** 구멍이 생긴다 → update-all 이 §3.5
전/후 `.env` 지문을 비교해 `HWAX_FORCE_RESTART=agent-server` 를 넘긴다. 게이트웨이 config 변경은 §5 가 이미 재기동한다.

## D-6. nginx bounce 도 conf 지문으로

§2 끝의 "Portal routing refresh" 는 conf 를 다시 만들고 무조건 nginx 를 내렸다 올렸다. 생성 전/후 conf 지문이 같고 nginx 가 살아 있으면 생략.
포털을 재기동했으면 start.sh 가 이미 conf 를 새로 썼다.

## D-7. 구현 기록 — 무엇을 어디에, 그리고 남긴 한계 (2026-09-27)

- 포털: `lib/change-detect.sh`(hwax_fp·hwax_install_if_changed·hwax_alive·hwax_restart_needed) · `images-from-drive.sh`(영구 캐시 `infra/apptainer/.drive-cache/`,
  SIF 는 cmp 뒤 cp -p, frontend dist 는 마지막으로 푼 tar 사본과 같으면 다시 풀지 않는다) · `deploy-all-from-drive.sh`(여섯 블록 지문 전/후 →
  판정 안에서만 stop/start, nginx 는 conf 지문, Done 에 생략 요약) · `services.py update_one`(`updated: unchanged (sha)` / `a→b`) ·
  `update-sites.sh restart_svc`(update 먼저 → unchanged·살아 있음·강제 아님이면 생략, 갱신 실패는 rc 로) · `update-all.sh`(§3.5 전/후
  agent-server .env 지문 → `HWAX_FORCE_RESTART`). 형제 4 리포는 `*-from-drive.sh` 만(영구 캐시 + cmp 뒤 cp -p) 파일 단위로 커밋 —
  다른 세션의 미커밋 변경(SignalForge 275·KooRemapper 21·HEAXHub 5)은 건드리지 않았다(git status 절단 사고의 규율).
- **지문의 한계(의도)**: 32MB 넘는 파일은 크기·mtime 만 본다 — 같은 크기·같은 mtime 으로 내용만 바뀐 SIF 는 못 본다. 설치 경로가 cp -p(원격
  modtime)·cmp 뒤에만 쓰기라 실제로는 일어나지 않는다(원격이 바뀌면 modtime 이 바뀐다). 시험이 이 한계를 그대로 못 박는다.
- **첫 실행은 전부 재기동**한다 — 설치본의 mtime 이 옛 cp 시각이라 캐시(원격 modtime)와 다르고, cmp 가 같아도 지문 '전' 은 옛 mtime 이다…
  아니다: cmp 가 같으면 손대지 않으므로 '후' 도 옛 mtime 그대로 = 전후 같음 → 첫 실행부터 생략된다. 단 dist tar 사본(.frontend-dist.applied)이
  처음엔 없어 dist 를 한 번 다시 풀고(mtime 은 tar 것으로 보존되니 지문 불변) 사본을 만든다.
- **형제 리포의 tar 풀기**(heax frontend-dist·koorm bin/dist)는 매 실행 다시 푼다 — tar 가 mtime 을 보존해 지문은 안정되고, 비용은 수 초라 두었다.
  heax 앱 SIF(`var/sifs/*.sif`)는 `hwax_fp var/sifs` 로 디렉터리 지문(이름·크기·mtime) — cmp 뒤 cp -p 라 안정.
- `hwax_alive` 는 curl 의 rc 가 아니라 코드로 판정(000 폴백 없음) — deploy-all 의 `probe()` 주석이 적은 '000000' 함정과 같은 이유.
- 시험 9(지문 변/불변/누락·큰 파일·설치 함수·판정 네 갈래·deploy-all 여섯 블록+nginx 텍스트·images-from-drive 텍스트·services.py 실 git·
  update-sites 슬라이스 여섯 시나리오·update-all §3.5→§4). 변이는 리뷰 라운드에 맡긴다(형제 리포 변경까지 한 번에 보게).
- **dev 에서 실주행은 못 했다** — deploy-all-from-drive 는 dev 에서 돌리면 리포를 리셋한다(금지). 첫 실측은 cae00 의 다음 update-all 이다:
  §2 여섯 서비스에 "변경 없음 · 살아 있음 → 재기동 생략" 과 rclone `Transferred: 0`, §4 셋에 "코드 변경 없음 → 재기동 생략" 이 보여야 한다.

