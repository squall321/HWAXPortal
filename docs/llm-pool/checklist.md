# LLM 서버 둘 나눠 쓰기 — 체크리스트

> 차례: 리스크 심사 M3 를 올린 바로 뒤(사용자 결정 10-15). 근거는 PLAN.md · context-notes.md.

- [x] 시작 — 열린 물음 둘(라우터 자리 · …136 의 모델·창이 …137 과 같은가)을 사용자에게 — 10-15 cae00 · 같다(LP-D5·D6)
- [x] L-1 라우터 · `llm-router.sh` · 매니페스트 항목 · `services.py`(`if_env` · `fp_git`) · 시험(가짜 vLLM 둘 — 고르기 · 붙임 · 넘김 · 스트림 · 끊김 전파 · 한쪽 죽음 · 다시 읽기) — 10-15 `63be0e9`·`32b3581`·`1f4a037`(시험 27 · 변이 33/33 · dev vLLM 실주행 — 끊김 0.07초 안 전파, 실제 띄우는 스크립트 확인), 합침 `7e933fe`
- [x] L-2·3 `lib/llm-pool.sh` · update-all 1i(기동 → 답할 때만 사본 바꾸기 · 백업 · 되돌리기) · `update-sites` 미룸 · `apply-envs` 새 키 · §6 한 줄 · `infra/.env.example` · 시험 — 10-15 `279983a`·`7fe321d`·`35d5820`·`ffb31fd`(시험 149 · 변이 9/9), 합침 `854127b` · 실제 라우터 /health 를 lib 로 읽어 봄(도는 스트림 1 → 미룸)
- [x] L-4 절차서의 동시 수 세 줄(자동 아님 — LP-D7) — `server-setup.md` 5절
- [x] L-5 반대 검토 · 변이 검사 — 1라운드(라우터 H1·M2·L12 · 배선 H1·M5·L6 → LP-D13, 변이 36/36 · 29/29) · 2라운드(M4·L7 → LP-D14, 변이 18/18 · 28/28 · 대조기 1,939건 중 갈림 1 → 2,048자 상한으로 0) · 3라운드(풀 끈 박스, LOW 5 → LP-D15, 변이 5/5)
- [x] L-6 절차서(cae00) · 업데이트 이력 · push · Drive(포털) — 10-15 `server-setup.md` · 이력(기술) · 포털 main `c46cb3c` push(전체 2,718 통과). Drive 는 필요 없다(라우터는 포털 리포와 git 으로 가고 portal.sif·frontend 는 그대로다)
- [x] L-7 용량 측정 도구(개선 제안 3 — LP-D16) — 길이 분포 추출기 `llm-lengths.py`(본문 없이 수만) · GuideLLM 0.8.0 이미지 `build-guidellm.sh`(Drive 로 나른다) · 실행 `llm-capacity.sh`(직결 대 측정용 라우터 · 붙임 문턱 2·0) · 계산 `llm-capacity.py`(표 · 세 손잡이 권장) · 절차서 `capacity.md` · 시험 · 변이 · dev vLLM 스모크 — 10-16 작업 트리 `llm-capacity`(아직 main 아님)
- [ ] L-8 용량 측정 실측(사용자 · cae00 · 심의 없는 때) — `capacity.md` 2~8절, 결과는 8절 표에, 세 손잡이는 `server-setup.md` 5절. 그 전에 dev 에서 `build-guidellm.sh` · `images-to-drive.sh`
