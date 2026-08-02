# 클러스터 배포 — 컨텍스트 노트

결정과 그 이유의 축적 기록. plan.md 가 "무엇을" 이라면 여기는 "왜". 세션이 바뀌어도
같은 논쟁을 다시 하지 않기 위한 문서 — 결정을 뒤집을 때는 여기의 근거를 먼저 반박할 것.

## 2026-07-18 (v1 작성 시점)

- k8s/nomad 배제 — apptainer+bash 유지. 1노드 하위호환 절대 보장 원칙 수립.
- endpoints 파생 규칙(같은 노드=127.0.0.1) 확정 — 1노드 diff 0 의 근거.
- 포털 복제·DB HA 는 비목표로 미룸 (당시 1인·1노드 전제).

## 2026-08-02 (v2 — 전제 변경)

### 규모 전제가 바뀌었다
- 신규 18대 + /data 공유 NFS(1PB, 스토리지 자체 이중화) 구매 확정.
- 동시 100명, 남이 만든 AI 앱 서빙(HEAX Hub = 앱 플랫폼화), 시뮬 7GB/건, 보고서 10만 건.
- 노드별 검색용 소형 LLM + HPC GLM 5.2.

### Drive → /data (내부 채널 교체)
- Drive 는 dev→배포서버 반입 채널로만 남긴다. 이유: 사내 TLS 프록시가 공개 레지스트리를
  MITM 해 노드별 온라인 접근이 불안정(기실측)하고, 18노드가 각자 Drive pull 하는 것은
  대역·복잡도 낭비. /data 가 있으면 스테이징 1회로 끝난다.

### 버전 스테이징 + current 심볼릭이 제1 전제인 이유
- 2026-08-01 실사고: 가동 중 SIF 덮어쓰기 → squashfs 파손 → SF 502. 공유 /data 에서
  같은 사고는 **18노드 동시 장애**가 된다. versions append-only + ln -sfn 원자 스위치로
  구조적으로 차단. 롤백도 링크 되돌리기로 수렴.

### DB 를 /data 에 올리는 결정의 왜곡 이력 (중요 — 재논쟁 방지)
1. 처음엔 "NFS 위 Postgres 금지" 로 단정 → **과했다.** PostgreSQL 공식 입장은 hard mount +
   정직한 fsync 면 지원. 현재 DB 크기(aidh 1.2GB·SF 1.7GB)와 소수 사용자면 성능 논점 없음.
2. 100명·7GB 파일 전제가 나오자 "I/O 경합 때문에 분리" 로 재수정 → 사용자가 "NFS 는
   이중화돼 안전, /data 서브 경로" 방침 확정.
3. **최종**: /data/pg/<svc> 허용. 단 3중 가드(파서 singleton 거부·락파일·hard mount preflight)
   없이는 기동 금지. I/O 경합이 실측되면 PGDATA 만 로컬 NVMe 로 후퇴(레이아웃 불변) —
   후퇴 경로를 미리 명시해 뒀으므로 이 결정은 되돌리기 싸다.
- **공유 스토리지 ≠ DB 이중화.** 같은 PGDATA 동시 오픈은 복제가 아니라 파손. 얻는 것은
  콜드 페일오버(다른 노드에서 마운트·기동)다. 스트리밍 복제는 별도 트랙.

### SQLite 는 NFS 금지 (예외 없음)
- 포털 PAT store(token_store.sqlite)·materialtwin SQLite — NFS 잠금 신뢰 불가.
  PAT store 는 Postgres 이관(Phase 4.2), materialtwin 은 단일 노드 고정(singleton).

### 포털 이중화가 싸진 이유 (비목표 → 목표 승격 근거)
- 실측: 포털 상태 = session_secret(HS256 문자열 1개) + jwt 키쌍 파일 + SQLite 테이블 2개.
  앞의 둘은 /data 공유로 자동 해결 — 남는 코드 작업은 PAT Postgres 이관 하나.
- 가장 위험한 순간: PAT 이관(개인 Claude 등록 토큰 무효화 가능)과 session_secret 통일
  (전원 로그아웃 1회). 완충: /tokens 설정 배치파일(2026-08-02 구축, claude/desktop/gemini/
  codex 4종 자동 재등록)이 재설정 비용을 낮춰 놓았다.

### 데이터 배치 원칙 (실측으로 확정)
- "DB 는 찾는 일, 파일시스템은 담는 일". AIDH(`/attachments` file_path)·RA(files.storage_path
  + 본문 JSONB + 버전 gzip dedup) 모두 이미 이 구조 — 설계 변경 불요, 확장만.
- 시뮬 7GB 는 Postgres 필드 한계(1GB)로 애초 불가. DB 에는 경로·sha256·메타·임베딩만.
- 대용량 서빙은 앱 스트리밍 금지 → X-Accel-Redirect (별도 트랙).

### RA 취급
- 소스 무수정 원칙 유지. placement 등록만 하고 기동은 자체 start.sh.
- **현행 backup-local.sh 가 RA 를 통째로 제외 중 — 실데이터가 있는 유일한 서비스인데
  백업이 없다.** RA DB pg_dump 편입이 전체 계획의 첫 실행 항목(0.2)인 이유.

### 100명 대비 실측 근거
- aidh PG: max_connections=100, shared_buffers=128MB(기본값), 앱 풀 미설정(SQLAlchemy 암묵).
  → pgbouncer + 튜닝 없이는 다중 노드에서 커넥션 고갈이 먼저 온다 (Phase 4.4).

### HEAX 앱 플랫폼화 실측 (Phase 5 근거)
- 이미 있는 것: proxy_manager 임의 host 프록시, port_allocator DB 기반(노드 간 충돌 없음),
  manifest resources → cgroup(SRV-04).
- 없는 것: 앱 상태가 노드 로컬 JSON, 원격 기동, 배치 결정, resources 필수화.
- 2026-08-02 dev 박스 OOM(프로세스 2,671개·RSS 합 247GiB·code 638개 100GiB) — 자원 상한
  없는 앱 수용은 반드시 재발한다는 실증.

### 작업 방식 결정
- 타인 소유 레포(RA·외부 반입 앱)는 PR 경유. 자기 소유 레포는 PR 대신 세션별 브랜치/worktree
  분리 — 실사고 2회(미커밋 리버트 동반 커밋, 미푸시 커밋 방치)가 모두 같은 체크아웃 공유에서
  났고, PR 은 이를 막지 못한다.
- cae00 은 클러스터 검증 완료까지 불간섭. 모든 커밋에서 update-all 동작(반쯤 이관 금지).

## 미결 (결정 나면 여기에 결론 추가)

- 18노드 OS/Python 동질성 (venv 공유 vs 노드별 빌드)
- 진입점 VIP(keepalived) — 사내 네트워크 협의
- 검색용 소형 LLM 모델·서빙 방식
- NFS fsync 정직성 (스토리지 사양서 확인)
- 배포 서버 노드 지정 · cae00 전환 시점
