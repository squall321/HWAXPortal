# ste 전각도 낙하 — 판단 기록

## 2026-09-28

**D-1 드라이버 잡 방식.** ste 잡 모델(앱 하나 = sbatch 하나, `--nodes=1`, 상태는 부모 `status` 파일, 취소는 부모만
`scancel`)에 잡 묶음을 넣는 방법은 드라이버뿐이다. 백엔드를 고쳐 다중 잡을 추적하게 하는 길도 있지만, 이 앱 하나를
위해 ste 코어(상태 판정·취소·폴러)를 바꾸는 것은 과하다. stcx 도 같은 드라이버 방식이라 검증된 형태다.
대가 — 드라이버가 1코어를 168h 쥔다. 각도 잡이 `--exclusive` 라 드라이버가 앉은 노드에는 각도 잡이 못 들어간다
(24대 중 1대). 문서에 적는다.

**D-2 자식 잡 추적은 KooChainRun 산출물에서.** `jobs.json` 의 `jobs.<doe>.job_id`(순차 모드는 슬롯마다 같은 ID 가
여러 번 — 중복 제거)와 `submit.log` 의 `→ Sphere Job ID: N`. stcx 드라이버는 `Submitted batch job` 을 grep 해서
자식 ID 를 못 찾았다 — KooChainRun 은 그 문장을 찍지 않는다(`DOE n: submitted (job N)`).

**D-3 대기는 `squeue -u <나>` 의 교집합.** `squeue -j <목록>` 은 목록이 전부 큐에서 빠지면 rc 1(`Invalid job id`)을
낸다 — 그걸 "모름" 으로 읽으면 영원히 기다리고, "없음" 으로 읽으면 squeue 가 진짜 실패했을 때 일찍 끝낸다.
`-u` 는 비어도 rc 0 이라 rc≠0 은 진짜 실패다. 그때는 모름으로 두고 계속 기다린다(없음과 모름을 가른다).

**D-4 취소.** TERM/INT/HUP 에서 ① 진행 중인 submit 을 멈추고 끝날 때까지(최대 10초) 기다린 뒤 ② 기록된 ID 와
③ `squeue` 에서 이름이 `<프로젝트>_` 로 시작하거나 배치 스크립트(`%o`)가 이 잡 폴더 안인 잡을 합쳐 `scancel`.
③ 은 submit 이 죽는 순간 날아가던 sbatch 가 jobs.json 에 못 적힌 잡을 잡는다. 프로젝트 이름에 ste 잡 ID 가 들어 있어
남의 잡을 건드리지 않는다. Slurm KillWait(기본 30초) 안에 끝나야 한다.
(정정 — 검토 1차) 처음엔 "구면 리포트 잡은 submit 이 끝난 뒤에만 생기므로 ID 가 로그에 있다" 고 적었는데 틀렸다.
같은 submit 프로세스가 리포트 sbatch 를 보낸 뒤 ID 를 찍기 전에 죽을 수 있고, 이름은 공용(`sphere_report`)이다.
afterany 는 취소도 종료로 쳐서 놓치면 취소된 실행의 반쪽 결과로 리포트가 돈다. 그래서 스크립트 경로로도 거둔다.
KooChainRun 은 경로를 resolve 하므로 논리(`$PWD`)·물리(`pwd -P`) 경로 둘 다 본다. 이름 청소는 스크립트 경로 청소와
겹치지만 둔다 — `%j` 는 확실하고 `%o` 의 모양은 실박스에서 아직 안 봤다.

**D-5 동시 실행 기본 4.** 라이선스 풀을 stcx 와 공유하고 홀드 하나가 128코어다. 제한 없이 162개를 던지면 한 사람이
풀을 다 쥐어 stcx 사용자까지 멈춘다 — 피해가 제3자에게 가는 쪽을 기본값으로 두지 않는다. `parallel=0` 이면
KooChainRun 기본(각도마다 잡). K>0 은 KooChainRun `--sequential --nodes K`(슬롯 K개가 각도를 순서대로).
순차 모드는 jobs.json 에 같은 ID 를 여러 번 적고 리포트 잡의 `afterany:` 에도 중복이 들어간다 — preflight 가
`sbatch --test-only --dependency=afterany:X:X` 로 중복 허용을 확인한다.

**D-6 라이선스 서버의 정본은 lsdyna 앱.** 새 파일에 IP 를 적지 않는다. `STE_LSTC_LICENSE_SERVER`(백엔드 env →
`--export=ALL` 로 잡 env)가 있으면 그것, 없으면 같은 트리의 `lsdyna/app.yaml` 에서
`${STE_LSTC_LICENSE_SERVER:-<기본>}` 의 기본값을 읽는다. 둘 다 없으면 run 은 시작하지 않고 preflight 는 ✗.
registry 의 `{env.K}` 치환은 `${VAR}` 를 확장하지 않는다(`{env}` 는 확장) — 쓰는 곳이 없어 고치지 않았다.

**D-7 성공 판정은 결과 파일로.** 드라이버 rc 0 = 모든 각도 completed AND `sphere_report.html` 있음.
하나라도 빠지면 rc 1 이고 `fullangle_verdict.json` 에 몇 개가 왜 빠졌는지 남긴다. ste 는 accounting 이 없어
sacct 로 자식 종료 코드를 볼 수 없다.

**D-8 KooChainRun 에 넘기는 env 에서 `STE_*` 를 지운다.** ste 백엔드는 sbatch 를 `--export` 없이 불러 잡 env 에
자기 env(시크릿 포함)가 들어간다. 이 앱은 그 env 를 자식 잡 수백 개로 다시 넘긴다. 같은 사용자라 권한 경계는
안 넘지만 퍼뜨릴 이유가 없다. 근본 수정(`--export=NONE` 등)은 ste 전반 변경이라 범위 밖.

**D-9 ste 공유 템플릿이 페이로드를 기다리게 고쳤다(ste 3a420db).** 배치 스크립트가 끝나면 Slurm 이 남은 프로세스를
죽인다. 종전 cleanup 은 페이로드에 TERM 만 보내고 곧장 exit 해서 드라이버의 TERM 트랩(자식 scancel)이 돌 틈이 없었다 —
그대로면 ste 에서 취소해도 자식 잡이 계속 돈다. status 를 먼저 쓰고 나서 기다린다(SIGKILL 로 끊겨도 종료 코드는 남는다).
e2e 시험이 scancel 을 일부러 0.5초 늦춰서 이 순서를 지킨다.
(검토 1차 보강) proctrack/cgroup(dev·ste 설치 계획)에서 scancel 의 TERM 은 **배치 스크립트에만** 간다(Slurm 23.11
proctrack_cgroup.c — SignalChildrenProcesses 미설정). 드라이버가 취소를 아는 길은 템플릿 cleanup 의 전달 하나뿐이고,
그 전달이 드라이버에 닿으려면 command 가 `exec bash …` 여야 한다(PAYLOAD_PID 가 드라이버 자신).

**D-10 드라이버 168h 가 전체 예산이다.** 순차 모드의 슬롯 잡 시간은 KooChainRun 이 `각도당 12h × 슬롯당 각도 수` 로 잡고
파티션 최대로 자른다. 드라이버가 168h 에 TERM 을 받으면 자식을 전부 취소하므로, `angles/parallel × 각도당 실제 시간` 이
168h 를 넘지 않게 parallel 을 고른다. Slurm 은 취소와 시간 초과를 같은 TERM 으로 보내 둘을 가를 수 없다.

**D-11 render 주입(ste 4637d25) — 이 앱이 드러낸 기존 결함.** render 가 자리표시자를 차례로 replace 해서, 업로드 이름
`m{t_final}.k` 가 따옴표째 들어간 뒤 안의 `{t_final}` 이 다시 치환돼 파라미터 값이 따옴표 밖에서 실행됐다. lsdyna·
koo-sph·koo-openlb·condensation 도 같은 모양이었다. 정규식 한 번으로 치환하고, 종전 우선순위(내장 > 같은 이름
파라미터, `{env.<param>}` 은 파라미터 > env)를 지켰다.

**D-12 올라온 jobs.json 을 믿지 않는다.** 입력 묶음은 잡 폴더(=드라이버 WORK)로 복사된다. 진짜 submit 은 노드 점검
(sinfo·scontrol·노드마다 ssh)을 마친 뒤에야 jobs.json 을 새로 쓰므로, 그 사이의 취소가 올라온 파일의 ID 를 scancel
했다 — ste 잡은 전부 한 서비스 계정이라 남의 잡도 취소된다. 트랩 전에 `jobs.json`·`.bak`·`submit.log` 를 지운다.
백엔드 예약 이름에 넣는 길도 있지만 앱 하나를 위한 ste 전반 변경이라 택하지 않았다.

**D-13 deep_report 가 빠진 각도는 실패다.** KooChainRun 은 inline deep_report 가 실패·시간초과해도 경고만 찍고
completed 로 적는다(실사례 dev `/data/single/admin/MemFix_Verify_2angle_1092`: OOM → deep_report rc=3 → Completed).
sphere_report.sh 는 `Output/report/{result,analysis_result}.json` 이 있는 Run 만 넣고 하나라도 있으면 rc 0 이다.
그대로면 리포트가 각도를 빠뜨려도 COMPLETED 다. 판정이 같은 기준으로 세어 `no_deep_runs` 로 남긴다.

**D-14 재시도는 끄지 않았다.** prepare 가 `retry_on_failure=true, max_retries=2` 를 박는다. 발산 각도는 보통 재시도
중에 Slurm 이 12h 에 죽여 색인에 running 으로 남고, 판정은 그것을 "끝나지 않은 채 멈춘 것" 으로 실패에 센다.
재시도는 라이선스 경합 같은 일시 실패를 살리므로 그대로 두고 주석만 사실대로 고쳤다.
