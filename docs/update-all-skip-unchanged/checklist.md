# checklist — update-all 바뀌지 않은 것 생략

## 포털
- [x] `lib/change-detect.sh` — hwax_fp · hwax_alive · hwax_restart_needed(마지막 기동 지문 기준, url 여럿) · hwax_mark_started · hwax_install_if_changed(0/1/2) (+ 시험)
- [x] `images-from-drive.sh` — 영구 캐시 + cmp 뒤 cp -p (+ gitignore `infra/apptainer/.drive-cache/`)
- [x] `deploy-all-from-drive.sh` — 여섯 블록: 받은 뒤 지문 → 마지막 기동 지문과 비교 → 기동 성공 뒤 기록, nginx conf+인증서 지문, 끝 요약, trap 정리 (+ 실 git 하네스 시험)
- [x] `services.py` — `fp <이름>`(git HEAD + .env 내용) (+ 시험); update_one 의 unchanged 마커는 정보용
- [x] `update-sites.sh restart_svc` — update → fp 를 마지막 기동 지문과 비교 → 같고 살아 있고 강제 아님이면 생략, 기동 성공 뒤 기록 (+ 슬라이스 시험)
- [x] `update-all.sh` — §3.5 전/후 창은 뗐다(상태 기준이 .env 를 본다); `HWAX_FORCE_RESTART` 는 수동 강제로 남김
- [x] 가이드 §2·§4 행, `HWAX_RESTART_ALL=1`, changelog(배포)
- [x] 스위트(813) · 적대 검토 1라운드 반영(D-8) · 2라운드 진행

## 형제 리포(파일 단위 커밋 — 다른 세션의 미커밋 변경을 쓸어 담지 않는다)
- [x] MXWhitePaper `infra/scripts/images-from-drive.sh` + gitignore
- [x] HEAXHub `deploy/apptainer/dist-from-drive.sh` + gitignore
- [x] SignalForge `scripts/sync-from-drive.sh` + gitignore
- [x] KooRemapper `platform/infra/scripts/dist-from-drive.sh` + gitignore

## 검증
- [ ] dev 에서 update-all 두 번 — 두 번째 §2·§4 전부 생략, Drive 전송 0
- [x] 적대 검토 1라운드 — 설계 결함(전/후 기준) 잡힘 → 상태 기준으로 재설계(D-8)
- [ ] 적대 검토 2라운드(재설계 대상)
- [ ] cae00 실측(사용자)
