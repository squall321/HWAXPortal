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

## D-8. 1라운드 검토가 설계를 뒤집었다 — 기준은 '블록 전/후' 가 아니라 '마지막으로 띄운 시점' (2026-09-27)

확인 5(high 4)·기각 1·미검증 22. 넷이 한 뿌리다: 지문 '전' 을 **블록 진입 시점**에 재니, 블록 밖에서 일어난 변경이 하나도 안 보인다.
① update-all §1 이 포털 리포를 이미 `reset --hard` 하고 재실행하므로 §2 의 git_update 는 늘 "up to date" — **백엔드 커밋이 포털을 영원히
재기동시키지 못한다**(바인드 마운트·--reload 없음이라 재기동 없이는 새 코드가 안 뜬다). ② §1c/1d/1e 가 §2 보다 앞서 .env·routes.local.env 를
고치는데(§1e 는 "§2 가 포털을 stop→start 하며 읽는다" 고 ✓ 까지 찍는다) 그것도 블록 밖. 운영자가 "infra/.env 한 줄 고치고 update-all" 하는
바로 그 사용법이 생략된다. ③ §4 의 `_ae0` 도 §3.5 직전에 찍혀 §1c 가 agent-server .env 에 넣은 키를 못 본다. ④ signalforge-mcp 는 §2 가 이미
reset 한 리포를 쓰니 §4 의 HEAD 전/후가 늘 같다. 종전엔 무조건 재기동이라 전부 가려졌던 자리 — **생략 기능이 무음 결함을 만들 뻔했다.**

재설계: 기준을 **마지막으로 띄운 시점의 지문**(상태 파일 `infra/.state/restart-fp/<서비스>`)으로. 받은 뒤 지문을 한 번 재서 그것과 비교하고,
기동이 **성공한 뒤에만** 기록한다(실패한 기동은 기준이 되지 않아 다음 실행이 다시 시도한다 — 기각된 지적 R1 이 걱정한 '재기동 전에 죽은 뒤
영구 생략' 도 이걸로 닫힌다). §4 는 `services.py fp <이름>`(git HEAD + .env 내용)을 같은 방식으로 — §3.5 전/후 창(`_ae0`)은 뗐다. 실 git 리포에
포털 블록을 통째로 돌리는 시험이 "§1 이 먼저 당긴 커밋·§1e 가 먼저 쓴 .env·§1d 의 routes 가 재기동을 일으키는가" 를 못 박는다.

함께 반영한 것: 인스턴스가 여럿인 서비스는 url 둘 다 답해야 생략(mxwp api+web·sf api+front·koorm api+mcp) · nginx 지문에 conf 가 경로로만
가리키는 인증서·키를 넣는다(갱신된 인증서가 메모리에 남던 것) · heax 지문에서 캐시 디렉터리를 뺐다(재업로드만으로 전 인스턴스 재기동) ·
heax SIF_DIR 판독은 작은따옴표도 벗긴다 · KooRemapper `BUILD_INFO.txt` 의 `cp -f`(mtime 리셋)와 heax mirror 의 node tarball `cp` 를 cmp 뒤 cp -p 로
(koorm 은 매 회 재기동될 판이었다) · 캐시는 `rclone sync`(원격에서 뺀 파일이 캐시에 남아 되살아나지 않게) · 설치 실패는 '같음' 이 아니라
✗ + rc 2(포털은 exit 1, 형제 리포는 set -e·SF 는 audit fail) · dist 가 지워졌으면 같은 tar 라도 다시 푼다 · `no-git` 은 unchanged 가 아니다(상태
기준 fp 는 nogit 도 지문에 넣어 비교) · 장부 임시파일을 EXIT trap 에 · KooRemapper .gitignore 를 CRLF 로 되돌림(python write_text 가 줄끝을
LF 로 갈아 208줄 diff 를 만들었다 — 파일 단위 커밋 규율 위반이었다).

남긴 것(low, 기록): 캐시가 latest/ 를 한 벌 더 든다(dev 14GB, heax 가 대부분 — `*_DRIVE_CACHE` 로 위치 변경 가능, 정리 명령은 없다) ·
update-sites 의 fp 는 .env 와 HEAD 만이라 custom update 가 아티팩트를 갈아 넣는 서비스(kooremapper 류)엔 §2 의 아티팩트 지문이 맡는다(§4 대상 셋은
git pull 만) · 시험은 포털 블록만 통째로 돌린다(다른 다섯 블록은 텍스트 배선 검사).

## D-9. 2라운드 — '기동 성공' 이 거짓일 수 있다: 기록 조건은 rc 가 아니라 '새 프로세스가 답한다' (2026-09-27)

확인 6(high 2). 뿌리 하나: start 스크립트(포털 start.sh·services.py up·mxwp/heax/sf/koorm 의 start)는 **떠 있는 인스턴스를 만나면 'already
running' 으로 rc 0** 을 낸다. stop 이 실패했거나(권한·apptainer 오류) `NO_RESTART=1` 이면 옛 프로세스가 그대로인데, D-8 은 "기동이 성공한 뒤에만
기록" 을 rc 0 으로 판정해 **새 지문을 적었다 → 그 서비스는 옛 코드로 영구 생략**. §2(deploy-all)와 §4(update-sites `already-up`) 둘 다.

고침 — 기록 조건을 프로세스로: health 포트를 듣는 프로세스의 (pid, /proc 시작시각) 을 stop 전/start 후로 비교(`hwax_listener_ids`, `ss -ltnp`),
**바뀌었을 때만** `hwax_mark_started`. 같으면 ✗ "재기동이 되지 않았다 — 같은 프로세스가 답한다" 로 블록 실패(rc 1), NO_RESTART=1 이면 · 로
"기록하지 않는다"(다음 정상 실행이 재기동). start 가 rc 0 인데 아무도 안 들으면 ✗. 답은 하는데 pid 를 못 보면(ss 없음·다른 사용자 소유) ⚠ 무기록
→ 매 회 재기동하되 보이게. `hwax_restart_cycle <이름> <지문> <stop> <start> <url…>` 하나로 묶어 여섯 블록·nginx·update-sites 가 같은 규율을 탄다.
AIDH 는 `boot.sh --force` 가 스스로 uvicorn 을 갈아 끼우므로 stop 자리에 `:` — 이때 내려감 대기(최대 20초)를 건너뛴다(살아 있는 서비스 앞에서
헛되이 세던 것).

함께 확인된 것: ③ kooremapper `:8701/` 은 MCP 루트라 404 → 매 회 "죽었다 → 기동" 이었다(생략이 한 번도 안 됐다) → `/mcp`(406). ④ 인자 없는
update-sites 는 portal 도 대상이라 §2 와 **같은 상태 파일**을 다른 형식의 지문으로 번갈아 덮어 핑퐁 재기동 → `restart-fp/sites/` 로 분리.
⑤ aidh 지문이 `api_server/.env`(boot.sh 가 기동 때 다시 쓰는 파일)라 매 회 달랐다 → `deploy/apptainer/.env`. ⑥ 게이트웨이 fp 에 .env 가 없어
`gateway_config.json`·`provision.env` 변경이 안 보였다 → 매니페스트 `data.identity` 의 비글롭 파일을 fp 에 넣는다. ⑦ `( … ) && ok || skip`
안은 set -e 가 꺼져 있어 `*-from-drive.sh` 실패가 삼켜지고 옛 SIF 로 기동해 초록이었다 → `|| exit 1`. ⑧ 상태 파일을 못 적으면(sudo 로 한 번 돌려
root 소유) 조용히 실패 → ⚠ + rc 0(재기동은 됐다).

시험 규율(이 문서의 D-8 시험이 못 잡은 이유): 하네스의 start.sh 스텁이 "늘 새로 뜬다" 였다. 실물은 "떠 있으면 안 띄운다". 이번 하네스는 리스너를
**진짜 프로세스**(lib 시험은 python http.server + 실제 curl·ss, 포털 블록은 sleep pid + ss/curl 셈)로 두고 start 스텁도 실물처럼 already-running
을 낸다 — "stop 실패 → already running → 기록 없음 → 다음 정상 실행이 재기동·기록" 이 한 시험에 든다. 하네스가 띄운 백그라운드 프로세스는
stdout 을 물면 subprocess 가 끝나지 않는다(실측 90초 timeout) — `>/dev/null 2>&1 </dev/null` 필수.

남긴 것: `hwax_listener_ids` 는 가장 작은 pid 하나만 본다(nginx 워커 여럿) — pid 재사용으로 우연히 같아질 확률은 무시했다. `ss -p` 는 같은 사용자의
프로세스만 보인다 — 다른 사용자로 띄운 서비스는 ⚠ 무기록(매 회 재기동, 보임). dev 실주행은 여전히 못 한다(deploy-all 은 dev 금지).

## D-10. 3라운드 — 리스너가 여럿이면 **전부** 갈려야 기록, start 뒤 유예, nginx rc 집계, §4 의 health 경로 (2026-09-28)

확인 17(중복 제거 열 갈래, high 3)·기각 1. 3라운드가 대상으로 삼은 것은 D-9 의 수정 자체다.

- **(high) url 이 둘인 서비스에서 하나만 갈려도 기록됐다.** 식별자 문자열("포트:pid:시각 포트:pid:시각")을 통째로 비교해 한 항목만 달라도 "바뀌었다"
  였다. 포털 stop.sh 가 hwax_nginx 만 못 내리면(인스턴스마다 `|| true`) start.sh 는 포털만 새로 띄우고 8088 은 옛 nginx 인데 새 지문 + nginx 기준 지문까지
  적혀 다음 실행부터 영구 생략. mxwp·sf·koorm 도 같은 구조. → url 마다 비교해 **하나라도 같으면 ✗ rc 1·무기록**(NO_RESTART 면 · 무기록), 하나라도 `?` 면
  답하는지 보고 답하면 ⚠ 무기록·안 답하면 ✗. 시험은 리스너 둘(진짜 http.server 둘)로 '하나만 갈림' 을 별도 케이스로 박았고, 포털 하네스의 ss·curl 셈은
  **포트별** 리스너 파일로 바꿨다(포트를 무시하는 셈은 이 갈래를 원리적으로 못 본다).
- **(high) nginx 블록이 사이클의 ✗ 를 `|| true` 로 삼켰다.** "같은 프로세스가 답한다" 인데 /health 200 만 보고 "reloaded" 초록·exit 0 — 옛 conf 로 돌면서
  update-all 전체가 초록. → rc 를 `_ngrc` 로 받아 0 이 아니면 skip(DEPLOY_FAILED 집계). nginx 블록도 행동 시험을 얻었다(conf 변경→bounce·같음→생략·정지 실패→skip).
- **start 뒤 유예 0.** start 가 포트 바인드 전에 돌아오는 스크립트(SignalForge up.sh 의 프론트 — instance start 뒤 배너만 찍고 끝)에서 정상 기동을
  "답하지 않는다(리스너 없음)" ✗ 로 오탐 → 블록 skip·무기록·다음 실행 재기동. cae00 첫 실행의 "배포 항목 2건 skip" 이 이 모양일 가능성이 크다.
  → `hwax_wait_up`(기본 10초, 전부 답하면 즉시) 을 id1 산출 전에 둔다.
- **성공 갈래가 health 를 안 봤다**(medium→low 로 확인). 새 리스너가 404/502 여도 기록·✓. 반박 에이전트의 판정: 다음 실행의 생존 검사가 곧바로 다시
  띄우므로 영구 생략은 아니고, 여기서 ✗ 로 막으면 늦게 뜨는 백엔드(heax caddy→업스트림)가 매 회 재기동된다. → 기록은 유지하고 ⚠ 로 표면화.
- **§4 update-sites**: 내려감 대기·생존을 포트 루트(/)로 두드려 루트가 404 인 agent-server 는 살아 있어도 '내려갔다' — 'down 실패' 진단이 구조적으로
  안 나왔다 → `services.py health <이름>` 을 두고 그 url 로 대기(리스너 식별은 `port`). `?` 갈래가 lib 와 달리 생존을 안 봐 죽은 서비스에 "✓ 완료" rc 0 →
  이 박스 대상(`enabled`)인데 안 답하면 ✗ rc 1(대상 아닌 searxng 류는 ⚠ rc 0 유지 — 반박 에이전트가 이 함정을 미리 잡았다). 갱신(git pull) 실패 시
  변경 없고 살아 있는 서비스도 down→up 을 탔다(GitHub 이 며칠 안 닿으면 update-all 마다 챗 스택 절단) → 생략하고 rc 1 만 올린다.
- **(medium) services.py fp 가 identity 디렉터리를 넣었다.** heax-hub `var/integration_state` 는 celery 가 45초마다 다시 쓰는 런타임 상태라
  `update-sites.sh heax-hub` 는 매 회 전체 스택 재기동이었다(update-all §4 대상 셋은 무영향). → identity 는 **파일만**, 디렉터리는 `fp:` 에 명시할 때만.
- HEAXHub stop.sh 가 `_common.sh` 를 소싱하지 않아 `instance_running` 이 rc 127 → '모름' 갈래로 인프라 인스턴스 넷을 무조건 stop(결과는 무해, 가드가
  죽은 코드). 배포 스크립트의 `2>/dev/null` 이 오류를 숨겼다. → 소싱 한 줄(형제 리포, 파일 단위 커밋).

시험 36(28→36): 리스너 둘 사이클 3갈래 · 늦은 바인드 · start 실패인데 새 프로세스 · 미건강 새 프로세스 ⚠ 기록 · 포털 블록 '하나만 갈림'·아티팩트(SIF·dist)
변경 · nginx 블록 행동 4갈래 · update-sites pull 실패 무바운스·`?`+무응답 ✗·대상 아님 ⚠ · identity 디렉터리 제외 · `health` 명령. 텍스트 단언은 `|| exit 1`
까지 포함(3라운드 변이 5종이 전부 생존했던 자리).

**사고(검토 중, dev).** 탐색 에이전트 하나가 nginx 블록 하네스를 상대경로로 불러 `$T` 가 상대경로가 됐고, 블록 안 `cd "$PORTAL_DIR"` 뒤 PATH 의 셈 항목이
풀려 **실 `apptainer instance stop hwax_nginx` 가 dev 에서 실행됐다**(:8088 → 000). 멱등 `start.sh` 로 복구. 규칙: 하네스 경로는 전부 절대경로,
PATH 셈은 `cd` 뒤에도 살아 있어야 하며, 실물 명령이 PATH 에 있는 하네스는 `command -v` 로 셈이 먼저 잡히는지 단언한다([[review-agents-leave-probes]]).

남긴 것(low, 기록): `hwax_listener_ids` 는 포트당 최소 pid 하나 — nginx 워커 여럿·pid 재사용은 무시. `hwax_wait_up` 은 새 프로세스가 미건강하면 매 재기동에
최대 10초를 더 쓴다(정상 기동엔 0). heax 블록의 start.sh 는 백엔드가 죽어도 rc 0 이라 'ok heax up' 이 되는 것은 이 작업 전부터의 모양 — 별건.
