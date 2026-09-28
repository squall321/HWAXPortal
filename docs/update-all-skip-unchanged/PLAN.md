# update-all — 바뀌지 않은 것은 받지도, 재기동하지도 않는다

> 사용자 요구(2026-09-27): "배포가 오래 걸리는 다른 서비스들 때문에 update-all 이 엄청 걸린다 — 바뀌지 않았던 거 스킵하는 것도 해줘."
> 이 문서는 무엇을 왜 바꾸는지다. 판단의 이유는 `context-notes.md`, 진행은 `checklist.md`.

## 0. 문제

update-all 한 번이 수십 분이다. 시간이 가는 자리는 둘이다.
- **§2 deploy-all-from-drive** — 여섯 서비스(portal·mxwp·heax·signalforge·aidh·kooremapper)마다 ① Drive 아티팩트(SIF·dist) 전부를
  **매번 새 임시 디렉터리로 다시 내려받고**(rclone 은 비교 대상이 없으니 전량 전송, Drive 는 ~2MB/s — ste 33MB 가 48초였다) ② 바뀐 게 없어도
  **stop → start** 로 재기동한다("start.sh 는 떠 있는 것을 건너뛰어 옛 conf 가 살아남는다" 는 이유로 항상 재기동하게 했다).
- **§4 update-sites** — 챗 스택 셋(signalforge-mcp·mcp-gateway·agent-server)을 `git pull` 결과가 "Already up to date" 여도 down → up 한다.

나머지는 이미 안 바뀌면 건너뛴다 — §2c ste(`--if-stale`)·§3 AIDH 덤프·§5 재프로비저닝(MISSING 일 때만).

## 1. 원칙

- **받는 것과 재기동을 따로 판단한다.** 받기: 영구 캐시에 rclone sync → 안 바뀐 파일은 전송 0. 재기동: 지문(git HEAD + 아티팩트·설정 지문)이
  **마지막으로 띄운 시점**의 것과 같고 서비스가 살아 있으면 생략. 기준은 상태 파일(`infra/.state/restart-fp/<서비스>`, 기동 성공 뒤에만 기록)이다 —
  '블록 전/후' 를 기준으로 하면 블록 밖의 변경(§1 git reset·§1c/1d/1e·운영자 편집)이 전부 안 보인다(1라운드 검토, context-notes D-8).
- **살아 있는 인스턴스 밑의 SIF 를 다시 쓰지 않는다.** 같은 내용이라도 덮어쓰면 squashfs 마운트가 깨진다(mxwp 실사고). `cmp` 가 다를 때만 `cp -p`.
  그래서 재기동을 생략해도 안전하고, 지문(이름·크기·mtime)이 안정된다.
- **기본이 생략, 강제는 한 변수.** `HWAX_RESTART_ALL=1` 이면 종전처럼 전부 재기동. 생략은 **줄로 보인다**("변경 없음 · 살아 있음 → 재기동 생략")
  — 조용한 생략은 이 리포가 여러 번 당한 결함이다([[silent-skips-must-be-logged]]).
- **설정 변경도 변경이다.** `.env`·routes 파일의 내용이 바뀌면 지문이 바뀐다. §3.5 apply-envs 가 agent-server `.env` 를 고쳤으면 §4 가 그 서비스는
  반드시 재기동한다(`HWAX_FORCE_RESTART`).
- **모르면 재기동한다.** 지문을 못 구하거나 health 가 안 답하면 종전 경로(재기동)로 간다 — 생략은 확인된 경우에만.
- **기록은 새 프로세스가 답한 뒤에만.** start 스크립트는 떠 있는 인스턴스를 만나면 'already running' 으로 rc 0 을 낸다. stop 이 실패했거나
  NO_RESTART 면 옛 프로세스가 그대로인데, 그 rc 만 믿고 새 지문을 적으면 **영구 생략**이다(2라운드 검토, context-notes D-9). health 포트를 듣는
  프로세스(pid·시작시각)를 **url 마다** 전/후로 비교해 전부 바뀌었을 때만 적고, 하나라도 같으면 ✗ 로 실패시킨다(3라운드, D-10). start 가 바인드 전에
  돌아오는 스크립트를 위해 짧은 유예(`hwax_wait_up`, 10초 상한)를 둔다.

## 2. 무엇을 바꾸나

| 자리 | 변경 |
|---|---|
| `infra/scripts/lib/change-detect.sh`(새) | `hwax_fp <경로…>`(이름·크기·mtime 지문, 파일은 내용 해시) · `hwax_alive <url>` · `hwax_restart_needed <이름> <지문> <url…>`(마지막 기동 지문과 비교, 문구+장부) · `hwax_restart_cycle <이름> <지문> <stop> <start> <url…>`(판정→stop→내려감 대기→start→**리스너 프로세스가 바뀌었을 때만 기록**; stop 자리에 `:` 면 start 가 스스로 갈아 끼우는 서비스) · `hwax_listener_ids` · `hwax_install_if_changed <src> <dst>`(cmp 뒤 cp -p, 0/1/2) |
| 포털 `images-from-drive.sh` | 임시 디렉터리 → 영구 캐시 `infra/apptainer/.drive-cache/`(rclone 이 안 바뀐 파일을 건너뛴다) · SIF 는 `hwax_install_if_changed` |
| 형제 4 리포의 `*-from-drive.sh`(mxwp·heax·signalforge·kooremapper) | 같은 두 가지(영구 캐시·cmp 뒤 cp -p). 각 리포 gitignore 에 캐시 경로 |
| `deploy-all-from-drive.sh` | 서비스 블록마다 받은 뒤 지문 → `hwax_restart_cycle`(마지막 기동 지문과 다르거나 죽어 있으면 stop/start, 새 프로세스가 답할 때만 기록). 받기 실패(`*-from-drive.sh`)는 `\|\| exit 1` 로 블록을 끊는다(서브셸 안은 set -e 가 꺼져 있다). nginx 갱신 블록은 conf+인증서 지문으로 같은 사이클. 끝에 "재기동 생략: …" 요약 |
| `services.py` | `fp <이름>`(git HEAD + .env + 매니페스트 `data.identity` 의 비글롭 파일) · `port <이름>`(health 포트) · `update_one` 은 `updated: unchanged (sha)` / `a→b` 보고(정보용) |
| `update-sites.sh restart_svc` | `update` → `fp` 를 마지막 기동 지문과 비교 → 같고 살아 있고 `HWAX_FORCE_RESTART` 에 없으면 down/up 생략. 재기동하면 `port` 의 리스너 pid 전/후를 비교해 바뀌었을 때만 기록, 같으면 ✗ rc 1. 상태는 `infra/.state/restart-fp/sites/`(§2 와 형식이 달라 분리) |
| `update-all.sh` §3.5→§4 | 전/후 창(`_ae0`)은 뗐다 — 상태 기준 지문이 .env 를 본다. `HWAX_FORCE_RESTART` 는 수동 강제로 남김 |
| 가이드 §2·§4 행 · changelog(배포) | 생략 규칙과 `HWAX_RESTART_ALL=1` |

## 3. 성공 기준

- dev 에서 update-all 두 번 연속: 두 번째는 §2 여섯 서비스 전부 "재기동 생략", Drive 전송 0(rclone `Transferred: 0`), §4 셋 "재기동 생략".
- 아티팩트 하나를 바꾸면(Drive 재발행) 그 서비스만 재기동. `.env` 한 줄을 바꾸면 그 서비스만 재기동.
- 시험: 지문 함수(변경/불변/누락·큰 파일)·설치 함수(같으면 안 쓴다·다르면 mtime 보존·실패는 rc 2)·판정 함수(변경/불변+생존/불변+죽음/강제)·**재기동 사이클을 진짜 리스너(python http.server, 실제 curl·ss)로**(새 프로세스→기록 · 같은 프로세스→✗ 기록 없음 · NO_RESTART→기록 없음 · `:` 정지→대기 없음 · 답 없음→✗)·포털 블록을 실 git 리포+스텁으로 통째로(첫 실행 재기동→생략→§1 커밋·§1e .env·§1d routes 가 재기동을 일으킴 · 기동 실패 무기록 · **stop 실패+already running 무기록** · 받기 실패에 블록 끊김)·update-sites 슬라이스(여덟 시나리오 + down 실패 무기록 + 상태 디렉터리 분리)·services.py fp(HEAD·.env·identity·글롭 제외)·`port`(실 매니페스트)·deploy-all 배선 텍스트.
