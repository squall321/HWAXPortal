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

- **받는 것과 재기동을 따로 판단한다.** 받기: 영구 캐시에 rclone copy → 안 바뀐 파일은 전송 0. 재기동: 지문(git HEAD + 아티팩트·설정 지문)이
  같고 서비스가 살아 있으면 생략.
- **살아 있는 인스턴스 밑의 SIF 를 다시 쓰지 않는다.** 같은 내용이라도 덮어쓰면 squashfs 마운트가 깨진다(mxwp 실사고). `cmp` 가 다를 때만 `cp -p`.
  그래서 재기동을 생략해도 안전하고, 지문(이름·크기·mtime)이 안정된다.
- **기본이 생략, 강제는 한 변수.** `HWAX_RESTART_ALL=1` 이면 종전처럼 전부 재기동. 생략은 **줄로 보인다**("변경 없음 · 살아 있음 → 재기동 생략")
  — 조용한 생략은 이 리포가 여러 번 당한 결함이다([[silent-skips-must-be-logged]]).
- **설정 변경도 변경이다.** `.env`·routes 파일의 내용이 바뀌면 지문이 바뀐다. §3.5 apply-envs 가 agent-server `.env` 를 고쳤으면 §4 가 그 서비스는
  반드시 재기동한다(`HWAX_FORCE_RESTART`).
- **모르면 재기동한다.** 지문을 못 구하거나 health 가 안 답하면 종전 경로(재기동)로 간다 — 생략은 확인된 경우에만.

## 2. 무엇을 바꾸나

| 자리 | 변경 |
|---|---|
| `infra/scripts/lib/change-detect.sh`(새) | `hwax_fp <경로…>`(이름·크기·mtime 지문, 파일은 내용 해시) · `hwax_alive <url>` · `hwax_restart_needed <이름> <전> <후> <url>`(판정+문구+장부) · `hwax_install_if_changed <src> <dst>`(cmp 뒤 cp -p) |
| 포털 `images-from-drive.sh` | 임시 디렉터리 → 영구 캐시 `infra/apptainer/.drive-cache/`(rclone 이 안 바뀐 파일을 건너뛴다) · SIF 는 `hwax_install_if_changed` |
| 형제 4 리포의 `*-from-drive.sh`(mxwp·heax·signalforge·kooremapper) | 같은 두 가지(영구 캐시·cmp 뒤 cp -p). 각 리포 gitignore 에 캐시 경로 |
| `deploy-all-from-drive.sh` | 서비스 블록마다 지문 전/후 → `hwax_restart_needed` 가 참일 때만 stop/start. nginx 갱신 블록은 conf 지문이 같고 살아 있으면 bounce 생략. 끝에 "재기동 생략: …" 요약 |
| `services.py update_one` | git HEAD 전/후를 비교해 `updated: unchanged (sha)` / `updated: a→b` 로 보고 |
| `update-sites.sh restart_svc` | `update` 먼저 → unchanged 이고 살아 있고 `HWAX_FORCE_RESTART` 에 없으면 down/up 생략 |
| `update-all.sh` §3.5→§4 | agent-server `.env` 지문이 §3.5 로 바뀌었으면 `HWAX_FORCE_RESTART=agent-server` |
| 가이드 §2·§4 행 · changelog(배포) | 생략 규칙과 `HWAX_RESTART_ALL=1` |

## 3. 성공 기준

- dev 에서 update-all 두 번 연속: 두 번째는 §2 여섯 서비스 전부 "재기동 생략", Drive 전송 0(rclone `Transferred: 0`), §4 셋 "재기동 생략".
- 아티팩트 하나를 바꾸면(Drive 재발행) 그 서비스만 재기동. `.env` 한 줄을 바꾸면 그 서비스만 재기동.
- 시험: 지문 함수(변경/불변/누락)·설치 함수(같으면 안 쓴다·다르면 mtime 보존)·판정 함수(변경/불변+생존/불변+죽음/강제)·update-sites 슬라이스(unchanged→생략, 변경→down/up, 강제→down/up)·services.py unchanged 마커·deploy-all 여섯 블록과 nginx 블록이 판정을 부르는지·update-all 이 §3.5 지문을 §4 에 넘기는지.
