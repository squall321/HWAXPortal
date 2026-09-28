# checklist — update-all 바뀌지 않은 것 생략

## 포털
- [x] `lib/change-detect.sh` — hwax_fp · hwax_alive · hwax_restart_needed(마지막 기동 지문 기준, url 여럿) · **hwax_restart_cycle(리스너 pid 전/후 — 새 프로세스일 때만 기록, `:` 정지)** · hwax_listener_ids · hwax_mark_started(못 적으면 ⚠) · hwax_install_if_changed(0/1/2) (+ 시험, 진짜 리스너)
- [x] `images-from-drive.sh` — 영구 캐시 + cmp 뒤 cp -p (+ gitignore `infra/apptainer/.drive-cache/`)
- [x] `deploy-all-from-drive.sh` — 여섯 블록 + nginx 가 `hwax_restart_cycle`(받은 뒤 지문 → 마지막 기동 지문과 비교 → 새 프로세스가 답할 때만 기록), 받기 실패는 `|| exit 1`, koorm MCP 는 `/mcp`, aidh 는 `deploy/apptainer/.env` + `:` 정지, 끝 요약, trap 정리 (+ 실 git 하네스 시험 4)
- [x] `services.py` — `fp <이름>`(git HEAD + .env + `data.identity` 비글롭 파일) · `port <이름>` (+ 시험); update_one 의 unchanged 마커는 정보용
- [x] `update-sites.sh restart_svc` — update → fp 를 마지막 기동 지문과 비교 → 같고 살아 있고 강제 아님이면 생략; 재기동은 `port` 리스너 pid 전/후로 확인해 바뀌었을 때만 기록(같으면 ✗ rc 1); 상태는 `restart-fp/sites/` (+ 슬라이스 시험, 진짜 리스너)
- [x] `update-all.sh` — §3.5 전/후 창은 뗐다(상태 기준이 .env 를 본다); `HWAX_FORCE_RESTART` 는 수동 강제로 남김
- [x] 가이드 §2·§4 행, `HWAX_RESTART_ALL=1`, changelog(배포)
- [x] 스위트 · 적대 검토 1~4라운드 반영(D-8·D-9·D-10·D-11)

## 형제 리포(파일 단위 커밋 — 다른 세션의 미커밋 변경을 쓸어 담지 않는다)
- [x] MXWhitePaper `infra/scripts/images-from-drive.sh` + gitignore
- [x] HEAXHub `deploy/apptainer/dist-from-drive.sh` + gitignore · `stop.sh` 가 `_common.sh` 를 소싱(instance_running rc 127 — D-10)
- [x] SignalForge `scripts/sync-from-drive.sh` + gitignore
- [x] KooRemapper `platform/infra/scripts/dist-from-drive.sh` + gitignore

## 검증
- [ ] dev 에서 update-all 두 번 — 두 번째 §2·§4 전부 생략, Drive 전송 0
- [x] 적대 검토 1라운드 — 설계 결함(전/후 기준) 잡힘 → 상태 기준으로 재설계(D-8)
- [x] 적대 검토 2라운드(재설계 대상) — 확인 6 → 기록 조건을 '새 프로세스가 답한다' 로(D-9)
- [x] 적대 검토 3라운드(2라운드 수정 대상) — 확인 17(열 갈래, high 3) → url 별 비교·wait_up·nginx rc·§4 health(D-10)
- [x] 적대 검토 4라운드(3라운드 수정 대상) — 확인 9(medium 6·low 3)·기각 5 → 포털 게이트 회귀·nginx gen rc·NG_PORT 인용·없는 이름·health 없는 서비스·글롭·시험 공백 둘(D-11)
- [~] cae00 실측(사용자) — 1차 실행 2026-09-28: aidh·koorm·nginx '기록 없음 → 재기동' 정상, §4 셋 첫 재기동 정상, **배포 2건 skip**(원인 줄 미확인 — 늦은 바인드 오탐 의심, D-10 로 고침) · 2차 실행 대기
