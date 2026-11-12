# 스마트트윈 낙하 파이프라인 개선 — 결정 · 까닭

> 계획 [PLAN.md](PLAN.md) · 할 일 [checklist.md](checklist.md).

## SP-1 조사(2026-11-12) — 사람 손에 남은 까닭과 고칠 자리

- 사용자가 "스마트트윈 전처리 · 솔버 · 후처리는 다 제대로 되나" 물었고, 답은 '아직 아니다' 였다(stcx 이미지 둘이 옛 판 · 운영 끝까지 한 번 기록 없음).
  이어서 "우리가 해 줄 수 있는 건 개선해야지" 라고 지시했다.
- 읽기 전용 조사를 맡겼다(여러 리포 — KooSlurm · KooRemapper · KooD3plotReader · pyKooCAE · 포털). 받은 것 가운데 셋은 손대기 전에 직접 확인했다.
  - Drive `SmartTwinPreprocessor/` — `SmartTwinPreprocessor.sif` 1,615,892,480 B(11-11) = dev 헤드 사본 · sha256 `1c973c25dc14…` · 안의 KooRemapper `c5f74c18…`.
    v135(`da892a35…`)는 dev 헤드 백업으로만 남았다. v135 · v136 tar 는 둘 다 Drive 에 있다.
  - KooSlurm `cluster/setup/phase8_containers.sh` 1155 ~ 1158행 — `stat -c%s` 크기가 같으면 '동일, 스킵'.
  - `apptainer/deploy_compute_images.sh` 22행 — `TARGET_DIR="/opt/apptainers/compute"`. 소비처는 `/opt/apptainers/*.sif` 를 읽는다.
- 조사가 짚은 운영 쪽 사실(확인은 cae00 몫) — SmartTwinMCP(정본은 KooSlurm `dashboard/smarttwin_mcp`, stcx 헤드에서 돈다)가 cae00 게이트웨이에 없다
  (HP-51 · OB-92 — PA-16). 그래서 cae00 에서는 포털 R2a 씨앗의 stcx 단계와 DynaForge 의 stcx 제출이 돌지 못할 가능성이 크다. 사람이 `ssh stcx` 로 제출하는
  길과 DynaForge 후처리 예약(REST 직결)은 된다.
- dev 에서 끝까지 돌릴 수 없다 — LS-DYNA 라이선스 만료 · 계산 노드 VM 둘이 꺼짐(켜려면 사용자 확인 · 호스트 여유 30 GB 이상) · DynaForge stcx 설정 비어
  있음 · KooSlurm dev 백엔드에 위임 비밀 없음. 해석기 없이 이미 있는 결과 사본으로 후처리 → 반입은 해 볼 수 있다.
- 고칠 차례는 조사 권고(1 · 2 · 4a/4c · 5 · 3 · 6 · 7 · 8 · 9)를 따랐다(PLAN §3 — 포털 번호로 다시 매김). 포털 문서 정정이 가장 싸고 운영 실수를 바로 막는다.

## SP-2 사용자 결정 셋(11-12) · 맡김 · 첫 답

- D1 — 운영에 넘길 전처리는 **v136**(권장안). Drive 에 있는 그대로이고 v135 에 KMM 리더 충돌 고침만 더해졌다(안의 KooRemapper 같음).
- D2 — dev 노드 VM 을 **켜서** 해석기 없이 후처리 → DynaForge 반입을 돌린다(권장안). LS-DYNA 는 라이선스가 끝나 뺀다. KooSlurm 이 node001 하나면 된다고 했다.
- D3 — dev 값은 **세션들이 dev 전용으로 맞춘다**(권장안). DynaForge 가 해석기 없는 반입에 드는 칸은 둘뿐이라고 확인했다 — `KOORM_STCX_BACKEND_URL` ·
  `KOORM_KOOSLURM_SSO_SECRET`(KooSlurm `HEAX_GATEWAY_SECRET` 과 같은 값). `KOORM_GATEWAY_PAT` 는 stcx 제출에만 써서 서비스 토큰 발급은 필요 없다. 공유 비밀은
  KooSlurm 이 dev 전용 파일(0600)로 두고 양쪽이 그 파일을 읽는다 — 값은 전언 · 리포에 싣지 않는다.
- pyKooCAE 답 — v136 값 확인(Drive 를 직접 해시). **NFS 도 풀어야 한다** — 드라이버 · 제출 · 후처리는 NFS 의 `KooChainRun`(sha256 `35511107…`)을 직접 부른다.
  2026-11-09 Q5 의 'tar 는 넘기지 말 것' 은 틀렸다(그 tar 가 바로 NFS 몫이다). 판 이름 산출 · sha256 알림은 굽기 스크립트를 바꾸는 일이라 그쪽 사용자 결정으로
  올린다.
- KooSlurm(-35) — 이미지 점검 스크립트와 dev E2E 준비를 가지에 지었다. 노드 배포 안전은 -de 가 그쪽 사용자 확인 뒤 맡는다.
- DynaForge(fd) — API 셋 · 점검 스크립트 · 절차를 가지 `dropline-1112` 에 올렸다. `external_job_key` 는 `stcx:<Slurm 잡 id>` 가 맞다.
- 이미지 점검 스크립트는 가지에만 있어 cae00 이 이번에 받을 수 없다. 그래서 Q15 는 pyKooCAE 가 준 확인 명령 일곱 줄을 싣고, 표로 보는 점검은 다음 라운드로 넘겼다.

## SP-3 dev E2E — ① 노드 이미지 배포까지 하고 멈춤(사용자 결정 11-12)

- DynaForge(fd)가 dev 값 두 칸 · 예약자 e2etest · 세션을 갖추고 점검 스크립트가 '갖춰졌다' 로 나온 뒤, 포털이 node001 을 켰다(4 CPU · 8 GB · Slurm idle). node002 는 그대로 꺼 뒀다.
- KooSlurm(-35)이 ① node001 에 Pre v136(7초) · Post v51(4초)을 배포했다. 그때 결함을 하나 더 찾았다 — dev 배포 스크립트 `deploy_apptainers.sh --image` 는 헤드
  사본을 견주지 않고 `sudo cp` 로 제자리 덮어쓴다(쓰는 중이면 squashfs 가 깨진다). 헤드는 이미 같은 판이라 노드 단계만 했고, 노드는 같은 파일시스템에 `.part` 로
  올린 뒤 `sudo mv` 로 원자 교체했다(node001 의 /tmp 는 다른 파일시스템이다). 이 사례는 노드 배포 안전(-de)에 넘겼다.
- 그 사이 호스트 여유 메모리가 30.7 → 28.5 GiB 로 내려갔다. 게스트가 만진 페이지는 비워도 호스트로 돌아오지 않아 VM RSS 가 3.9 GiB 로 늘었다. ② · ③ 이 최악
  24 ~ 25 GiB 까지 내릴 수 있었다(메모리 부족 보호선 약 7.4 GiB 와는 멀다). 진행을 권했으나 사용자가 **멈추고 VM 을 끄기**를 골랐다.
- node001 을 정상 종료했다(여유 32 GB 로 돌아옴). 결과 사본 · 시험 잡 9000001 · dev 공유 비밀 파일 · DynaForge dev 값 · node001 디스크의 v136 · v51 은 남겨 다음에
  ② 부터 다시 돌릴 수 있다. 다시 돌릴 때는 메모리를 넉넉히 확보한 뒤 사용자에게 다시 묻는다.

