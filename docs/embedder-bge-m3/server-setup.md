# 임베더 BGE-M3 — cae00 절차

> 이 문서는 cae00 의 AIDataHub 임베더를 e5-base 에서 BGE-M3 로 옮기는 사람 몫을 적는다. 설계는 [PLAN.md](PLAN.md), 까닭은
> [context-notes.md](context-notes.md)(EM-D1~), 설정과 내부 동작은 AIDataHub `docs/embedder-bge-m3.md` 에 있다.
> 명령은 따로 적지 않으면 AIDataHub 리포 루트(cae00 은 `~/Projects/AIDataHub`)에서 돈다. 근거는 줄 번호가 아니라 **출력 문구**로 가리킨다.

## 0. 이 판을 받기만 하면 — 읽기는 그대로다

update-all 이 AIDataHub(`e036812` 이후)를 받으면 `start_api.sh` 가 이행 0032 를 올린다. 네 표에 빈 BGE-M3 열이 더해질 뿐이고 검색은 e5 그대로다
(`deploy/apptainer/.env` 에 `AIDH_EMBED_*` 를 적지 않은 박스는 예전과 같다).

- **update-all 에 `aidh failed` 가 보이면** — 이행이 옛 API 를 내리기 전에 돈다. 그때 옛 임베딩 스윕이 긴 트랜잭션을 쥐고 있으면 0032 가 잠금을
  10초만 기다리고 실패한다(`deploy/apptainer/logs/alembic.log` 에 `canceling statement due to lock timeout`). 옛 API 는 옛 코드로 계속
  돈다(EM-D13). 다음처럼 푼다(10-17 cae00 에서 실제로 한 길).
  1. 쉬는 트랜잭션을 본다 — 새 판의 기동은 이행 전에 그 pid · 시간을 직접 찍는다(`idle in transaction`).

     ```bash
     cd ~/Projects/AIDataHub
     bash <<'SH'
     . deploy/apptainer/_common.sh; load_env
     apptainer exec "instance://$INST_POSTGRES" psql -h 127.0.0.1 -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
       "SELECT pid, now() - xact_start AS 걸린_시간, left(query, 60) AS 쿼리 FROM pg_stat_activity WHERE state LIKE 'idle in transaction%';"
     SH
     ```
  2. 옛 API 의 것(몇 분 넘게 쉬는 것)이면 `SELECT pg_terminate_backend(<pid>);` 로 끊는다(같은 psql 줄에 쿼리만 바꿔).
  3. `cd ~/Projects/HWAXPortal && ./infra/scripts/deploy-all-from-drive.sh aidh` — 이행이 **먼저** 돌고, 성공해야 옛 API 를 내린다. 또
     실패하면 옛 API 가 그대로 남는다.
  - ⚠ `bash deploy/apptainer/restart.sh --api` 는 쓰지 않는다 — 옛 API 를 **먼저** 내리고 이행을 돌려, 이행이 또 실패하면 AIDataHub 가 멈춘다
    (예전 판 이 줄의 '급하면' 길이었다 — 10-17 리뷰 P2).
  - PG 의 쉬는 트랜잭션 시한(`idle_in_transaction_session_timeout` 30분 — 사용자 결정 10-17)을 건 박스는 이 막힘이 30분 안에 스스로 풀린다.
    거는 한 줄은 AIDataHub `deploy/apptainer/README.md` 의 'PG 안전망'.
- **0032 가 update-all 의 3절 병합보다 늦게 올라갔으면** — 병합은 운영 DB 에 있는 열만 옮긴다. 새 판 병합(AIDataHub `a7a2ee4` 이후)은 그런
  열을 `⚠ <표>: dev 에만 있는 열 — …` 로 이름째 찍고 3 으로 끝나고, update-all §3 은 `AIDH 데이터 merge 는 됐지만 dev 에만 있는 열이 빠졌다`
  로 알리며 '병합함' 표식(`.last-merged`)을 안 적는다 — 다음 update-all 이 같은 덤프로 다시 병합한다. 바로 받으려면 이행 뒤
  `bash deploy/apptainer/merge-from-drive.sh`(약 1시간). 옛 판 병합은 이 경우 ✓ 로 끝나 m3 열이 조용히 빠졌고, 다음 update-all 은 같은
  덤프라 건너뛰었다(10-17 cae00 — 리뷰 P2 · H1).
- 새 백필은 1,024행씩 커밋하고 겹쳐 돌지 않는다 — 예전처럼 API 프로세스가 수십 GB 로 부풀지 않는다.

## 1. 전제 — dev 쪽이 끝났는가

아래가 모두 참일 때만 2절로 간다. 하나라도 아니면 이 박스는 0절 상태로 둔다.

1. dev 에서 견주기(B3)로 전환하기로 했다 — [checklist.md](checklist.md) 의 B3 · B5 가 체크돼 있다.
2. Drive 의 dev 덤프가 **dev 의 BGE-M3 백필 뒤에** 만든 것이다 — 첫 덤프는 `aidh-db-20261016-193902Z.sql.gz`(2026-10-17 04:39 KST,
   약 11GB)이고 그 뒤 매일 04:45 UTC(13:45 KST) 덤프도 그렇다. 이보다 옛 덤프를 merge 하면 BGE-M3 벡터가 오지 않는다(4절에서 보인다).
   덤프가 4.75GB 에서 약 11GB 로 커져 §3 의 받기 · 풀기도 그만큼 길다.
3. 이 박스의 웹 리서치 앱(WebResearchMCP)이 임베딩 공간을 가리는 판(`e6cc2ed` 이후)이다 — 옛 판은 원장에 저장한 e5 문장 벡터를 BGE-M3
   질의와 섞어 `search_in_page` 의 의미 순위를 오류 없이 틀리게 낸다(EM-D15). 새 판은 HEAX 앱 SIF 로 Drive 를 거쳐 온다(update-all §2).

   ```bash
   apptainer exec ~/Projects/HEAXHub/var/sifs/web-research-mcp.sif grep -c WRV2 /app/app/ledger.py   # 1 이상이면 새 판, 0 이면 멈춘다
   ```

## 2. 모델 받기 — 전환 전에

cae00 은 HF 에서 직접 받지 못한다. Drive 에서 받는다(약 2.2GB).

```bash
cd ~/Projects/AIDataHub
AIDH_MODEL_REPOS="BAAI/bge-m3" bash deploy/apptainer/model-from-drive.sh
```

기대 — 처음엔 `→ 캐시에 없는 모델: BAAI/bge-m3` 뒤에 복원, 다시 돌리면 `[INFO] 이미 캐시에 존재: BAAI/bge-m3 — skip`.
모델 없이 6절의 한 줄을 적으면 API 가 뜨지 않는다(활성 슬롯의 모델이 없으면 부팅에서 멈춘다).

## 3. update-all — 코드 · 이행 · merge

```bash
cd ~/Projects/HWAXPortal && ./infra/scripts/update-all.sh
```

§3(AIDataHub 데이터 동기화)이 dev 덤프를 merge 하며 BGE-M3 벡터가 함께 온다. merge 가 평소보다 길다 — staging 에 덤프를 풀 때 BGE-M3
색인(약 2.8GB)도 지어진다. §3 에 `dev 에만 있는 열이 빠졌다` 가 보이면 0절 둘째 항목이다.

## 4. 남은 것 확인 — 여기서 멈출지 정한다

```bash
cd ~/Projects/AIDataHub && bash deploy/apptainer/embed-slot.sh status --slot m3
```

- 기대 — `record_sections` 가 수백~수천(cae00 에서만 생긴 절 + cae00 에서 고친 레코드의 절)이고, `records` 가 수십~수백(cae00 에서만
  생긴 레코드 + cae00 에서 고친 레코드)이다.
- **`records` 가 5만 9천 안팎이면** 병합이 레코드 시그니처를 못 옮긴 것이다 — AIDataHub 가 `722d7a0` 전 판이다(예전 병합이 cae00 의
  `updated_at` 을 병합 시각으로 올려 둬 레코드 갱신이 0건이었다 — 10-17 cae00, 리뷰 H1-b). 그 판에서는 그대로 5절로 가고, 6절 뒤 인앱
  스윕이 CPU 로 채운다(10-17 cae00 — 레코드 59,032건 약 4분).
- **100만 안팎이면 멈춘다** — 덤프가 dev 백필 전 것이다(1절 2). 이대로 전환하면 이 박스가 CPU 로 109만 절을 임베딩한다(dev CPU 로 1.9 절/초 —
  약 6.6일, 그동안 같은 모델을 쓰는 검색 질의가 묶음마다 기다린다). 다음 덤프 뒤 3절부터 다시 한다.

## 5. 색인

```bash
bash deploy/apptainer/embed-slot.sh index --slot m3 --maintenance-work-mem 4GB --workers 2
```

`CREATE INDEX CONCURRENTLY` 라 표의 쓰기를 막지 않는다. 이미 있으면 건너뛰고, 실패가 남긴 INVALID 색인은 지우고 다시 짓는다. 끝나면 색인마다
`지었다 — N초, 크기` 가 찍힌다. 진행은 psql 에서 `SELECT phase, blocks_done, blocks_total FROM pg_stat_progress_create_index;`.

## 6. 전환 — `.env` 한 줄

`~/Projects/AIDataHub/deploy/apptainer/.env` 에 한 줄을 더한다.

```
AIDH_EMBED_ACTIVE=m3
```

```bash
cd ~/Projects/HWAXPortal && ./infra/scripts/deploy-all-from-drive.sh aidh   # 0절과 같은 길 — restart.sh --api 는 쓰지 않는다
curl -s http://127.0.0.1:8001/api/system/health \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["embed_slot"], d.get("embed_backlog_by_slot"))'
```

기대 — `{'active': 'm3', 'fill': ['v1', 'm3'], 'model': 'BAAI/bge-m3', 'dim': 1024}`. `AIDH_EMBED_FILL` 은 적지 않는다 — 활성 슬롯은 늘
채우고 v1 은 기본으로 채우므로 두 슬롯이 다 최신으로 남는다(되돌리기가 그대로 산다). 4절의 남은 행은 인앱 스윕(30분마다)이 채운다.

## 7. 포털 · 에이전트 서버 — 할 일 없음

둘 다 AIDataHub `/api/embed` 응답의 모델 · 차원을 보고 따라간다(EM-D8). 포털 대화 검색은 사람마다 **다음 검색 때** 그 사람의 대화를 BGE-M3 로
다시 색인한다 — 한 번에 시간 예산만큼 하고 남은 수는 응답의 `index.not_indexed_yet` · `partial` 로 알린다. 하한은 BGE-M3 용(0.58 · 0.30,
EM-D14)이 이미 들어 있다. 포털 · 에이전트 서버 코드는 3절의 update-all 이 이미 올렸다.

## 8. 되돌리기

`.env` 의 `AIDH_EMBED_ACTIVE=m3` 줄을 지우거나 `v1` 로 바꾸고 `cd ~/Projects/HWAXPortal && ./infra/scripts/deploy-all-from-drive.sh aidh`.
v1 열은 6절 동안에도 계속 채워졌으므로 그대로 쓴다. 포털 대화 검색은 옛 색인을 다시 쓰지 **않는다** — 색인 표가 조각마다 한 줄
(`message_vectors` 의 키가 message_id · chunk_ix, `INSERT OR REPLACE`)이라 BGE-M3 행이 옛 e5 행을 덮었다. 되돌리면 사람마다 다음 검색 때
e5(aidh-768)로 **다시 색인한다** — 7절과 같이 한 번에 시간 예산만큼, 남은 수는 `index.not_indexed_yet` · `partial`(docs/request-1027 HP-37).

## 9. 지켜볼 것

- **질의 지연** — 이 박스가 CPU 로 질의를 임베딩하면 BGE-M3 가 e5 보다 느리다(dev CPU 의 짧은 질의 p50 — BGE-M3 71ms · e5 18ms).
- **merge 시간** — merge 는 원래부터 절 109만 행을 바뀌지 않은 것까지 매번 다시 쓴다. BGE-M3 색인이 생긴 뒤에는 행마다 그 색인도 갱신해
  merge 가 길어진다. update-all §3 의 시간을 전환 전과 견준다. 너무 길어지면 바뀐 행만 쓰게 merge 를 고칠 수 있다(후속 제안).
- **디스크** — BGE-M3 열(약 2.2GB) · 색인(약 2.8GB)이 늘어난다. v1 열 · 색인은 한동안 돌려 본 뒤 정리한다(B7).
