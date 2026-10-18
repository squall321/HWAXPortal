# 10-17 후속 — cae00 에서 사람이 할 일

> 계획 [PLAN.md](PLAN.md) · 결정과 까닭 [context-notes.md](context-notes.md) · 진행 [checklist.md](checklist.md).
> 명령은 따로 적지 않으면 포털 리포 루트(cae00 `~/Projects/HWAXPortal`)에서 돈다. 주소 · 키 값은 여기에 적지 않는다(이 리포는 공개다).
> 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.

## 0. 먼저 — update-all

```bash
cd ~/Projects/HWAXPortal && git pull && ./infra/scripts/update-all.sh
```

이번 판에서 출력이 이렇게 달라진다(무엇이 고쳐졌는지는 PLAN 2절).

| 어디 | 보이는 것 | 뜻 · 할 일 |
|---|---|---|
| §3 AIDataHub 병합 | `⚠ <표>: dev 에만 있는 열 — …` 뒤 `AIDH 데이터 merge 는 됐지만 dev 에만 있는 열이 빠졌다` | 운영 DB 이행이 늦었다. 표식을 안 적으므로 다음 update-all 이 같은 덤프로 다시 병합한다. 바로 받으려면 이행 뒤 `cd ~/Projects/AIDataHub && ./deploy/apptainer/merge-from-drive.sh` |
| AIDataHub 기동 | `⚠ 쉬는 트랜잭션 N개 — …` 와 pid · 트랜잭션 나이 줄 | 이행이 잠금으로 실패하면 이것들이 원인이다. 병합 · 백업이 아닌지 보고 `SELECT pg_terminate_backend(<pid>);` 뒤 `./infra/scripts/deploy-all-from-drive.sh aidh` |
| 이미지 받기 | `· gatus.sif 받지 않음 — status-board 꺼짐` | 꺼진 선택 서비스의 이미지를 받지 않는다(켜면 다음 실행이 받는다) |
| HEAX 미러 | `○ … 미러 없음` | 실패가 아니다(미리 받은 SIF 로 돈다) |
| nginx | `· nginx conf 그대로 — 재기동 생략` | 예전엔 이때도 `reloaded` 라고 찍었다 |
| 게이트웨이 로그 | `HWAXMcpGateway/gateway.log` 한 곳(덧붙임 · 600) | `/tmp/hwax-services/` 는 700 · 파일 600 이다. 토큰이 든 주소는 `***` 로 가려진다 |

## 1. 옛 자동 stash 정리 — 결정 25(리뷰 D7)

새 판 update-all 은 `.env` 손 백업(`*.env.bak*`)을 stash 로 쓸어 가지 않는다(`.gitignore`). 이미 쌓인 19개 중 셋에 비밀이 든
`infra/.env.bak-*` 가 git 객체로 남아 있다. **내용을 보고** 지운다(지우면 되살릴 수 없다).

```bash
cd ~/Projects/HWAXPortal
git stash list | grep -c 'update-all auto-stash'
for s in $(git stash list | grep 'update-all auto-stash' | cut -d: -f1); do
  echo "== $s"; git stash show --include-untracked --name-only "$s"
done
```

되살릴 것(사람이 고친 추적 파일 등)이 없으면 큰 번호부터 지우고, 지운 stash 의 객체까지 저장소에서 없앤다.

```bash
for s in $(git stash list | grep 'update-all auto-stash' | cut -d: -f1 | sort -t'{' -k2 -rn); do git stash drop "$s"; done
git reflog expire --expire-unreachable=now --all && git gc --prune=now -q
git stash list | grep -c 'update-all auto-stash'     # 0
```

## 2. AIDataHub — PG 쉬는 트랜잭션 30분 시한 — 결정 24(리뷰 D4)

병합(`merge-from-drive.sh`) · 백업이 돌지 않을 때 한 번 건다. 새 연결부터 든다(dev 는 10-17 에 걸었다). 명령은 AIDataHub
`deploy/apptainer/README.md` 의 'PG 안전망' 그대로다.

```bash
cd ~/Projects/AIDataHub/deploy/apptainer && ( set -a; . ./.env; set +a
  apptainer exec "instance://${INST_POSTGRES:-aidh_postgres}" psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "ALTER DATABASE \"$POSTGRES_DB\" SET idle_in_transaction_session_timeout = '30min';" )
```

기대 — `ALTER DATABASE`. 새 연결에서 `SHOW idle_in_transaction_session_timeout` 이 `30min`.

## 3. AIDataHub — 서버 안에서만 받기 — 결정 4

새 박스의 기본값은 `API_HOST=127.0.0.1` 이 됐지만(설정 킷은 없는 키만 더한다) 이미 있는 `.env` 는 그대로다. 소비처(포털 · 게이트웨이 ·
에이전트 서버 · HEAX 앱)는 모두 같은 박스의 루프백으로 부른다. 바꾸기 전에 지금 붙은 상대가 루프백뿐인지 본다.

```bash
cd ~/Projects/AIDataHub/deploy/apptainer
grep -n '^API_HOST=' .env
ss -tnH state established '( sport = :8001 )' | awk '{print $4}' | sed -E 's/:[0-9]+$//' | sort | uniq -c   # 127.0.0.1 · [::1] 만이어야 한다
```

루프백뿐이면 백업 뒤 바꾸고 새로 띄운다(값 줄 끝에 주석을 붙이지 않는다).

```bash
mkdir -p -m 700 ~/portal-backups && cp -p .env ~/portal-backups/aidh-apptainer.env.$(date -u +%Y%m%dT%H%M%SZ)
sed -i 's/^API_HOST=.*/API_HOST=127.0.0.1/' .env
cd ~/Projects/HWAXPortal && ./infra/scripts/deploy-all-from-drive.sh aidh
ss -tlnH '( sport = :8001 )'                                                          # 127.0.0.1:8001 하나
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/api/system/health    # 200
```

포털 'AI 데이터 허브' 타일과 챗의 지식카드 검색이 그대로 되는지 본다. 다른 박스에서 직접 불러야 하는 곳이 생기면 그때 넓히고 키를 켠다.

## 4. 리스크 앱 — 암호 백업 매일 03:30 — 결정 2(리뷰 D5)

리스크 앱 원장(`risk_review.db`)과 반출(`exports/`)을 age 로 암호화해, **이 앱만** Drive `<HEAXHub>/risk-backup/<박스 이름>/` 에 올린다(최근
5벌). 공유 칸(`app-data` — dev 가 올리고 cae00 이 병합해 받는다)과 다른 앱의 데이터는 건드리지 않는다. 평문 원장은 어느 길로도 Drive 에
가지 않는다(HEAXHub 백업이 `.age` 가 곁에 있는 평문을 뺀다).

### 4-1. 코드 · age

HWAXRisk 체크아웃은 update-all 이 당기지 않는다.

```bash
git -C ~/Projects/HWAXRisk pull --ff-only
grep -c '/home/' ~/Projects/HWAXRisk/backend/scripts/backup-to-drive.sh    # 0 — 새 판(박스 절대경로가 없다)
command -v age || echo 'age 없음'
```

age 가 없으면(이 박스는 apt 가 깨져 있다 — 리뷰 D2) dev 가 Drive 에 둔 우분투 꾸러미를 사용자 공간에 푼다(설치 · sudo 없음).

```bash
R="$(sed -n 's/^HWAX_DRIVE_REMOTE=//p' infra/.env | tail -1)"; R="${R%/images}"
T="$(mktemp -d)" && rclone copy "$R/tools/age/" "$T/" && (cd "$T" && sha256sum -c SHA256SUMS) \
  && mkdir -p ~/.local/opt/age ~/.local/bin && dpkg-deb -x "$T"/age_*.deb ~/.local/opt/age \
  && ln -sfn ~/.local/opt/age/usr/bin/age ~/.local/bin/age && ln -sfn ~/.local/opt/age/usr/bin/age-keygen ~/.local/bin/age-keygen
~/.local/bin/age --version      # 1.0.0
```

### 4-2. 공개키

**dev 와 같은 공개키**를 쓴다 — 개인키는 사용자가 따로 지닌다(박스마다 키를 만들면 그 박스가 죽을 때 키도 함께 사라져 백업을 못 푼다).
공개키(`age1…`)는 비밀이 아니다. 사용자에게 받거나 dev 에서 `age-keygen -y ~/.config/hwax/risk-backup.agekey` 로 본다.

```bash
D=~/Projects/HEAXHub/var/app_data/hwax_risk
grep -c '^HWAXRISK_BACKUP_KEY=' "$D/secrets.env"                 # 0 이면 아래
read -r PUB                                                      # age1… 를 붙여 넣는다
case "$PUB" in age1*) printf 'HWAXRISK_BACKUP_KEY=%s\n' "$PUB" >> "$D/secrets.env"; chmod 600 "$D/secrets.env";; *) echo '공개키가 아니다';; esac
unset PUB
P="$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/Projects/HEAXHub/var/integration_state/hwax_risk.json')))['port'])")"
curl -s "http://127.0.0.1:$P/api/health"                         # 포트는 허브가 정한다 — 상태 파일에서 읽는다
```

기대 — `warnings` 에 `backup_unencrypted` 가 없다(앱이 `secrets.env` 를 그때그때 읽어 재기동이 필요 없다).

### 4-3. 크론 · 한 번 돌려 보기

```bash
mkdir -p ~/.local/state/hwax
( crontab -l 2>/dev/null | grep -vF '# hwax-risk-backup'
  echo '30 3 * * * cd $HOME/Projects/HWAXRisk && PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin bash backend/scripts/backup-to-drive.sh >> $HOME/.local/state/hwax/risk-backup.log 2>&1  # hwax-risk-backup'
) | crontab -
cd ~/Projects/HWAXRisk && bash backend/scripts/backup-to-drive.sh | tail -4
```

기대 — `· 제외(요청) hwax_risk/risk_review.db` · `→ 업로드 …/risk-backup/<박스>/app-data-<시각>/` · `✓ 리스크 앱 백업 → Drive risk-backup/<박스> (암호=1)`.

### 4-4. 풀어 보기(개인키가 있는 곳에서)

풀 수 없는 백업은 백업이 아니다. 개인키를 지닌 곳(dev 또는 사용자 PC)에서 한 번 본다.

```bash
T="$(mktemp -d)" && cd "$T" && rclone copy "<remote>:HEAXHub/risk-backup/<박스>/latest/app-data.tar.gz" . \
  && tar -tzf app-data.tar.gz && tar -xzf app-data.tar.gz ./hwax_risk/risk_review.db.age \
  && age -d -i <개인키 파일> -o restored.db hwax_risk/risk_review.db.age \
  && python3 -c "import sqlite3; c=sqlite3.connect('restored.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0], c.execute('PRAGMA user_version').fetchone()[0])"
```

기대 — 목록에 `risk_review.db`(평문) · `secrets.env` · `cred.key` 가 없다. 마지막 줄이 `ok <스키마 판>`(10-17 dev — `ok 5`).
되살리기는 `docs/design-risk-review/plan.md` §5.2.5 (4)의 순서(앱 정지 → 라이브 원장 옮기기 → 푼 파일을 `risk_review.db` 로 → 기동)다.

### 4-5. `cred.key` 폴백 정리(리뷰 D5 의 나머지)

설정 화면 '이 박스' 의 `cred_key_source` 가 `dev_fallback` 이면 `docs/risk-review-redesign/server-setup-m1.md` 7-1 대로 `secrets.env` 로 옮긴
뒤 `cred.key` 를 치운다(새 키를 만들면 등록된 PAT 가 풀리지 않는다 — **옮긴다**).

## 5. stcx LLM 잡 만료 — 11-14 전에

Slurm 잡 한도가 30일이라 2026-11-15 전후에 끝난다. 끝나도 챗은 GLM 으로 넘어간다(느려질 뿐 멈추지 않는다 — `/health` 의
`chat_llm.fallback.count`).

```bash
~/stcx-llm/llmctl.sh rolling      # 또는 start-all
```

Qwen 을 1M 창으로 올리는 rolling(`docs/chat-llm-stcx/server-setup.md` 9.5)을 11-14 전에 하면 이 rolling 을 겸한다 — 다음 만료는 그 rolling
한 날 + 30일이다.

## 6. 지켜볼 것

- **AIDataHub 병합 시간** — 절(109만 행)은 바뀌지 않은 행까지 매번 다시 쓰고, 이제 m3 색인(약 2.8GB)도 같이 갱신한다. update-all §3 의
  시간이 크게 늘면 알린다(바뀐 행만 쓰게 고칠 수 있다 — `docs/embedder-bge-m3/server-setup.md` 9절).
- **통합 앱 기동 실패 억제** — 늘 실패하는 앱(예: `heax_demo_nextjs`)은 `var/logs/integration_<앱>.log` 에 `기동 실패 N번째 — 다음 시도 M초
  뒤` 가 찍히고 시도가 60초부터 두 배씩(최대 1시간) 줄어든다. 고친 뒤 곧바로 다시 하려면 `deploy/apptainer/redeploy-app.sh <앱>`.
- **Caddy 로그** — 다음 Caddy 재기동부터 `var/caddy/caddy.log` 를 Caddy 가 64MB 마다 돌린다(5벌 · gzip). 그 전까지는 예전처럼 자란다.
- **logrotate 에 넣지 않은 로그** — HEAX 백엔드 · 워커 · beat, AIDataHub uvicorn, `/tmp/hwax-services/*.log` 는 이제 덧붙여 쓰지만(기동 때
  크면 한 벌 넘김) 떠 있던 프로세스는 옛 fd 다. 편입은 dev 가 박스마다 쓰기자가 새로 뜬 것을 보고(`/proc/<pid>/fdinfo/1` 의 02000) 한다.

## 7. 심의 품질 T1 — 근거 선주입을 재고, 나으면 켠다 — 결정 11

T1 은 `DELIB_EVIDENCE_PREPASS`(기본 0)다. 켜면 1라운드 전에 근거 도구 넷(`hybrid_search` · `search_knowledge` · `search_reports` ·
`query_rules`)을 각 3건씩 부르고, LLM 한 번으로 정량 근거만 추려 좌석마다 `[정량 근거]` 블록(3,000자 이하)으로 싣는다. 도구가 없거나
실패하면 건너뛴다. 봉인 심의는 늘 끈다. 손잡이는 한 번에 하나만 바꾼다(`docs/deliberation-quality/checklist.md` — 동시 적용 금지).

### 7-1. 먼저

- update-all 을 마친 판이다 — 에이전트 서버 `3ca9894` 이후(그 전 러너는 결정문을 못 잡아 결정문 지표가 양쪽 다 0 이었고, 재는 심의마다 RA
  보고서 초안을 남겼다).
- GLM 이 답한다 — 심의 하나가 끝까지 돈다.
- 근거 도구가 게이트웨이에 있다(`없음` 인 것은 T1 이 건너뛴다 — `search_reports` 는 RA 가 붙어 있어야 있다):

```bash
curl -s http://127.0.0.1:9110/tools-map | python3 -c 'import json,sys; m=json.load(sys.stdin)["map"]; print({t: m.get(t, "없음") for t in ("hybrid_search", "search_knowledge", "search_reports", "query_rules")})'
```

- 심의가 한가한 때다 — 심의 18회(조건 둘 × 질문 셋 × 3회)라 몇 시간 걸린다. 그동안 update-all 은 재기동을 미룬다.

### 7-2. 재기(A/B)

```bash
cd ~/Projects/HWAXAgentServer
OUT=~/portal-backups/ab-t1-$(date +%Y%m%d)
nohup .venv/bin/python -m tools.delib_ab --knob evidence_prepass --questions tools/ab_questions.txt --repeat 3 --out "$OUT" > "$OUT.log" 2>&1 &
```

- 손잡이는 요청마다 켜고 끈다(`delib_opts.evidence_prepass`) — `.env` 를 바꾸지 않는다. 대조군(0) 9회 뒤 실험군(1) 9회.
- RA 보고서는 남기지 않는다(러너 기본 — `--save-report` 를 주면 남긴다). 질문 셋은 `tools/ab_questions.txt`(RA 에 결론이 저장된 주제는
  넣지 않는다 — 정답 유출).
- 한 회가 실패해도 이어 간다(로그의 `✗ 실패` 줄). 끝나면 `$OUT.log` 끝에 대조표, `$OUT/summary.json` 에 수치. 다시 집계 —
  `.venv/bin/python -m tools.delib_ab --report "$OUT"`.

### 7-3. 판정(사람)

- 대조표 — 발언당 수치 인용 · 반박 인용률 · 파싱 실패율 · 결정문 수치 밀도(대조군 · 실험군 · 변화).
- 결정문 두세 쌍을 나란히 읽는다 — `$OUT/evidence_prepass=0_q0_r0.json` 과 `$OUT/evidence_prepass=1_q0_r0.json` 의 `decision`. 실험군의
  수치가 `[정량 근거]` 의 출처에 닿는가, 출처 없는 수치가 늘지 않았는가.
- 켜는 기준 — 근거 붙은 수치가 늘고, 출처 없는 수치 · 파싱 실패 · 실패 회차가 늘지 않는다. 애매하면 켜지 않는다(기본 꺼짐 그대로).

### 7-4. 켜기

```bash
cd ~/Projects/HWAXAgentServer
echo 'DELIB_EVIDENCE_PREPASS=1' >> .env      # 줄 끝에 주석을 붙이지 않는다 — start.sh 는 주석까지 값으로 읽는다
```

도는 심의가 없을 때 update-all(에이전트 서버 `.env` 가 지문이라 다시 띄운다) 또는 `./start.sh -d`. 확인 — 새 심의의 상태 줄에 `정량 근거
수집 — 지식·보고서 검색` · `정량 근거 수집 완료`, 근거 카드에 `지식·보고서 검색`.

### 7-5. 되돌리기 · 남기기

- 되돌리기 — 그 줄을 지우거나 `=0` 으로 두고 다시 띄운다.
- 남기기 — `docs/deliberation-quality/checklist.md` 의 T1 줄에 날짜 · 판정 · `summary.json` 요약을 적는다. 다음 손잡이(T2 `DELIB_REBUT_QUOTE`)
  는 T1 을 정한 뒤에 같은 러너로(`--knob rebut_quote`).
