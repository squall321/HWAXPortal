# checklist — update-all 바뀌지 않은 것 생략

## 포털
- [x] `lib/change-detect.sh` — hwax_fp · hwax_alive · hwax_restart_needed · hwax_install_if_changed (+ 시험)
- [x] `images-from-drive.sh` — 영구 캐시 + cmp 뒤 cp -p (+ gitignore `infra/apptainer/.drive-cache/`)
- [x] `deploy-all-from-drive.sh` — 여섯 블록 지문 전/후·판정, nginx bounce 조건, 끝 요약
- [x] `services.py update_one` — unchanged 마커 (+ 시험)
- [x] `update-sites.sh restart_svc` — update 먼저, unchanged+살아 있음+강제 아님 → 생략 (+ 슬라이스 시험)
- [x] `update-all.sh` — §3.5 전/후 agent-server .env 지문 → `HWAX_FORCE_RESTART`
- [x] 가이드 §2·§4 행, `HWAX_RESTART_ALL=1`, changelog(배포)
- [x] 스위트(808)·변이(아래 D-7)

## 형제 리포(파일 단위 커밋 — 다른 세션의 미커밋 변경을 쓸어 담지 않는다)
- [x] MXWhitePaper `infra/scripts/images-from-drive.sh` + gitignore
- [x] HEAXHub `deploy/apptainer/dist-from-drive.sh` + gitignore
- [x] SignalForge `scripts/sync-from-drive.sh` + gitignore
- [x] KooRemapper `platform/infra/scripts/dist-from-drive.sh` + gitignore

## 검증
- [ ] dev 에서 update-all 두 번 — 두 번째 §2·§4 전부 생략, Drive 전송 0
- [ ] 적대 검토 1라운드
- [ ] cae00 실측(사용자)
