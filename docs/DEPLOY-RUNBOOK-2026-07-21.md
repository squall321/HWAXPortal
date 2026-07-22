# cae00 배포 러너북 — 2026-07-21 심의 파이프라인 업그레이드 반영

> dev 박스에서 ssh 직결이 안 되므로(사내망 분리) cae00 콘솔에서 아래를 순서대로 실행한다.
> dev 측 준비(코드 push·프론트 빌드→Drive 업로드)는 완료 상태 전제.

## 0. 이번 배포에 포함된 변경 (요지)

| 레포 | 커밋 | 내용 |
|---|---|---|
| HWAXAgentServer | afd507c·35c1610 | 심의 LLM env 튜닝(LLM_*/DELIB_* 분리)·발언 개행 보존 |
| HWAXPortal | eabdfd7·e9c0839·eabee5c·ffa13a4·03ce8b0 외 | 챗·심의 마크다운/KaTeX 렌더, 버블 개행, 대화 내보내기(HTML/JSON), 워크플로 이어하기·persona 정규화, RA 저장 절단 수정 |
| HWAXMcpGateway | ac40589 | save_conversation 사전 정규화(422 배치 유실 방지) |
| AIDataHub | 2b966fb | agents.updated_at 마이그레이션 0030 — merge-from-drive 침묵 실패 수정 |

## 1. 코드·아티팩트 반영

```bash
cd ~/Projects/HWAXPortal && git pull --ff-only
cd ~/Projects/HWAXAgentServer && git pull --ff-only
cd ~/Projects/HWAXMcpGateway && git pull --ff-only
cd ~/Projects/AIDataHub && git pull --ff-only

# 프론트 번들(dev 에서 Drive 로 업로드됨) 수신 + 표준 업데이트
cd ~/Projects/HWAXPortal
./infra/scripts/deploy-all-from-drive.sh        # 아티팩트 수신
./infra/scripts/update-all.sh                   # 사이트 갱신 + AIDH merge(.last-merged 기준)
```

`update-all.sh` 중 AIDH 데이터 merge 는 이번에 처음으로 agents 테이블을 통과해야 정상이다
(종전엔 `agents.updated_at` 부재로 매번 중단). 로그에서 `✓ agents: +N` 이 나오는지 확인.
AIDataHub 자체 업데이트(`deploy/apptainer/update.sh`)가 alembic 0030 을 자동 적용한다.

## 2. agent-server 심의 튜닝 env 적용 + 재시작

```bash
cd ~/Projects/HWAXPortal
bash infra/env-kits/apply-envs.sh agent-server   # 기본 목록에 없음 — 인자 명시 필수
# 적용 키: DELIB_TEMPERATURE=0.7, DELIB_CLIP_SCALE=1.5, DELIB_PARSE_RETRIES=2, DELIB_TIMEOUT_S=180
# (DELIB_REASONING_EFFORT 는 §4 진단 전까지 주석 유지)
# 신규: 깊이 회복 손잡이 7종(DELIB_EVIDENCE_PREPASS 등)이 킷에 주석 시드됨 — 기본 꺼짐.
# 반드시 §5 A/B 로 한 번에 하나씩만 켤 것(동시 적용 시 상쇄, GLM 리뷰 §5). 순서·가이드는 킷 주석 참조.
cd ~/Projects/HWAXAgentServer && ./start.sh -d   # 재시작 (자가정리: 포트 리스너 종료 후 bind. -d=백그라운드.
                                                 #          기동 자체검증 — '기동 실패' 뜨면 로그 확인)
# .env 위생(운영 안전): ① 절대경로 금지 — MCP_CONFIG 는 start.sh 가 cwd 기준으로 기본 주입하므로
#   .env 에 넣지 말 것(타 박스 복사 시 경로 깨져 mcp:[] → 도구 전멸). ② KEY=VALUE 등호 양옆 공백 금지
#   (소싱은 관대해졌지만 그 줄 변수는 무시됨). ③ 값 조정은 .env 직접 편집 후 재시작해야 반영.
```

## 3. 게이트웨이 재시작 (sanitize 라이브화)

```bash
cd ~/Projects/HWAXMcpGateway && ./start.sh
curl -s http://127.0.0.1:9110/health | head -c 200   # tools 수·backends up 확인
```

## 4. 상암 vLLM reasoning parser 진단 (effort 활성 여부 결정)

cae00 에서 (dev 는 상암 도달 불가). `$LLM` 은 RA `backend/.env` 의 LLM_BASE_URL, 모델명은 LLM_MODEL.

```bash
# A. effort 미전달 기준선
curl -s --noproxy '*' $LLM/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"GLM-5-2","messages":[{"role":"user","content":"PSA 점착제의 박리속도-강도 종형 곡선을 3문장으로 설명하라"}]}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['choices'][0]['message']; \
    print('reasoning_content:', len(d.get('reasoning_content') or '')); \
    print('content<think>혼입:', '<think>' in (d.get('content') or '')); print((d.get('content') or '')[:200])"

# B. effort=high 전달
curl -s --noproxy '*' $LLM/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"GLM-5-2","messages":[{"role":"user","content":"PSA 점착제의 박리속도-강도 종형 곡선을 3문장으로 설명하라"}],
  "chat_template_kwargs":{"reasoning_effort":"high"}}' | python3 -c "동일 파싱"
```

판정 (docs/GLM-DELIB-TUNING-REVIEW.md §2(b)):
- reasoning_content 가 분리돼 오고 content 가 깨끗 → parser 정상. `DELIB_REASONING_EFFORT=high`
  주석 해제(agent-server `.env`) 후 재시작.
- content 에 `<think>` 혼입 → parser 미스매치. effort 켜지 말고 상암 관리자에게
  `--reasoning-parser glm45` 설정 요청. (같이 요청할 것: generation-config 의
  max_new_tokens/repetition_penalty 기본값 확인 — 클라 미전송 파라미터라 서버 기본이 유효.)

## 5. A/B 심의 비교 (품질 회귀 확인)

웹 챗 `/심의` 로 같은 주제 1개를 튜닝 전 저장분(기존 대화)과 비교 — 지표는
발언당 문자수(절단 전)·수치 인용 개수·rebut 항목 수·JSON 폴백("발언 파싱 실패") 횟수·
`<think>` 혼입 여부. 절차 상세: docs/GLM-DELIB-TUNING-REVIEW.md §4.

## 6. 확인 체크리스트

- [ ] 웹 챗에서 마크다운(표·수식·콜아웃) 렌더 확인 — 캐시 이슈 없음(index.html no-cache)
- [ ] 웹 심의 발언 버블에 문단 개행 표시
- [ ] 대화 우상단 HTML/JSON 내보내기 동작
- [ ] MCP 심의 1회 → 웹 대화 목록에 뜨는지(본인 PAT 사용 전제) + RA 보고서 생성
- [ ] update-all 로그에서 agents merge `✓` + cae00 수기 추가 에이전트 보존 확인
