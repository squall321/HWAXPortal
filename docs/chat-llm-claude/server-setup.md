# 웹 챗 Claude — cae00 에서 지정한 사람만 켜기(사람 몫)

> 기본 챗 LLM 은 그대로(챗 전용 LLM Qwen → GLM)이고, 운영자가 개별 허가로 `feat:chat-claude` 를 준 사람의 웹 챗 턴만 Claude 로 간다(PLAN · CC-1 ~ CC-8).
> 대조 시점 2026-11-22 — 에이전트 서버 `5f8931d` · 포털 `829cef16`. 이 판을 update-all 로 받은 뒤에 한다. 박스 상태는 적지 않는다(그때그때 본다).
> 키 · 프록시 주소 · 사내 인증서 경로는 이 문서 · 추적 파일 · 받은 편지함 답에 적지 않는다 — 그 박스의 `.env` 와 0600 파일에만 둔다.

## 0. 먼저 — 사람이 정할 것

- **회사 정책.** 지정한 사람의 웹 챗 내용(질문 · 도구 결과 · 붙인 문서의 글 · 그림)이 사외 API(Anthropic)로 나간다. 띵킹 · 심의 · 카드 대조 · 루틴은
  지금 LLM 그대로라 나가지 않는다. 나가도 되는지 사람이 확인한다.
- **누구에게.** 처음엔 한두 사람으로 시작한다(비용 — Opus 5.5 입력 1M 토큰 $4 · 출력 $20, 도구를 많이 부르는 긴 턴은 한 번에 몇 달러가 될 수 있다).
- **어느 모델을 고르게 할지.** 적지 않으면 기본 모델 하나다(4절).

## 1. 점검 — 키 없이(읽기 전용)

```bash
cd ~/Projects/HWAXPortal && ./infra/scripts/claude-chat-check.sh
```

2(curl) · 3(에이전트 서버의 파이썬)이 ✓ 여야 다음으로 간다. 결과 줄은 주소 · 키를 찍지 않으므로 그대로 받은 편지함 답에 옮겨도 된다.

| 결과 | 다음 |
|---|---|
| 2 · 3 모두 연결 실패(curl 6 · 7 · 28, ConnectError) | 바깥으로 나가려면 프록시를 거쳐야 하는 박스다. 에이전트 서버 `.env` 에 `HTTPS_PROXY=<사내 프록시>` 를 적는다 — 셸에만 있으면 update-all 이 다시 띄울 때 빠진다. **`NO_PROXY` 에 사내 목적지(LLM · 게이트웨이 · 127.0.0.1 · localhost)가 그대로 있는지 본다** — 없으면 사내 LLM 호출까지 프록시로 가서 챗 전체가 죽는다(docs/gotchas · 07-16 사고) |
| 2 는 ✓ · 3 은 「인증서를 믿지 못한다」 | 사내 프록시가 TLS 를 바꿔 낀다 — curl 은 시스템 인증서 묶음을 써서 되지만 파이썬(httpx)은 자기 묶음(certifi)을 쓴다. 에이전트 서버 `.env` 에 `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt`(시스템 묶음 — 공개 루트 + 사내 루트). 그 프로세스의 모든 httpx 호출이 이 묶음을 쓴다 — 시스템 묶음이라 공개 루트도 들어 있다 |
| 403 · curl 56 | 프록시 · 회사 정책이 막는다 — 사람이 확인한다(이 경우 이번엔 켜지 않는다) |

고친 뒤 다시 돌린다. `.env` 를 고쳤으면 에이전트 서버를 다시 띄워야 실제 서버에 먹는다(점검은 `.env` 를 직접 읽어 미리 본다).

## 2. 설치 — `requirements-anthropic.txt`

update-all 은 이 꾸러미를 깔지 않는다(켜는 박스만). 에이전트 서버 venv 에 넣는다 — 꾸러미 셋(anthropic 0.125.0 · langchain-anthropic 1.4.8 ·
docstring-parser 0.18.0)이고 나머지 의존(httpx · pydantic · langchain-core 1.4.7 …)은 이미 있다. langchain-core 판은 바뀌지 않는다.

먼저 바깥에서 받기를 해 본다.

```bash
cd ~/Projects/HWAXAgentServer && .venv/bin/pip install -r requirements-anthropic.txt
```

pip 가 PyPI 에 닿지 못하면(사내 프록시 · 인증서) Drive 의 꾸러미 묶음으로 깐다 — dev 가 받아 올린 바퀴 넷(모두 순수 파이썬 · 어느 파이썬 판이든 같다)과 `SHA256SUMS`.

```bash
cd ~/Projects/HWAXPortal
R="$(sed -n 's/^HWAX_DRIVE_REMOTE=//p' infra/.env | tail -1)"; R="${R%/images}"
T="$(mktemp -d)" && rclone copy "$R/tools/claude-chat-wheels/" "$T/" && (cd "$T" && sha256sum -c SHA256SUMS) \
  && ../HWAXAgentServer/.venv/bin/pip install --no-index --find-links "$T" -r ../HWAXAgentServer/requirements-anthropic.txt
rm -rf "$T"
```

`./infra/scripts/claude-chat-check.sh` 의 4 가 ✓(anthropic 0.125.0 · langchain-anthropic 1.4.8)면 된다.

## 3. 키 파일 — 사람이

```bash
mkdir -p ~/.config/hwax && install -m 600 /dev/null ~/.config/hwax/anthropic.key
# 그 파일에 API 키 한 줄을 넣는다(편집기로 — 셸 기록에 남지 않게 echo 로 넣지 않는다)
```

## 4. 에이전트 서버 `.env`

```bash
CLAUDE_CHAT_MODEL=claude-opus-5-5
CLAUDE_CHAT_API_KEY_FILE=/home/<사용자>/.config/hwax/anthropic.key
CLAUDE_CHAT_FOR=feat:chat-claude        # 기본값이지만 적어 둔다 — all 로 쓰면 모든 사람이 Claude 가 된다
# 고를 수 있는 모델을 넓히려면(비우면 위 기본 하나):
# CLAUDE_CHAT_MODELS=claude-opus-5-5,claude-sonnet-5-5,claude-haiku-5-5
# CLAUDE_CHAT_EFFORTS=low,medium,high   # 비우면 low ~ max 다섯
```

- 한 줄에 `KEY=값` 하나 · 줄 끝 주석은 `start.sh` 가 값으로 읽는다(위 예의 줄 끝 주석은 옮길 때 뺀다).
- Fable 5.2(`claude-fable-5-2`)는 30일 보존이 필요한 모델이라 데이터 무보존(ZDR) 조직이면 400 이다 — 목록에 넣기 전에 조직 설정을 본다.

## 5. 다시 띄우기

```bash
cd ~/Projects/HWAXAgentServer && ./start.sh -d     # 도는 심의가 있으면 건너뛴다(끝 코드 3) — 끝난 뒤 다시
../HWAXPortal/infra/scripts/claude-chat-check.sh     # 6 이 「켜짐 — 모델 claude-opus-5-5 · 대상 feat:chat-claude」
```

켜려다 못 켰으면 6 이 까닭을 말한다(키 파일 없음 · 꾸러미 없음 · 모르는 값). 그 사이에도 모든 사람은 기본 챗 길로 간다.

## 6. 사람 지정

관리 › 사용자 → 그 사람 → 권한 「웹 챗 Claude 모델」 을 켠다.

- 이 권한은 소속의 「전부」(CAEG 의 `"*"`) · 관리자 전권에 **딸려 오지 않는다** — 사람마다 따로 준다. 관리자 자신도 쓰려면 자기에게 준다.
- 권한은 요청마다 다시 셈하므로 포털 재기동이 필요 없다. 그 사람이 챗 화면을 새로 고치면 입력창 도구 줄에 모델 · 생각 깊이 칸이 보인다(모델이 하나면
  이름만 보인다).

## 7. 확인

- 지정한 사람으로 웹 챗 한 턴 — 답 아래 「답한 모델」 이 `claude-…` 다.
- 지정하지 않은 사람으로 한 턴 — 지금처럼 챗 전용 LLM(Qwen) 이름이고, 입력창에 모델 칸이 없다.
- 관리 › 이용 통계의 「LLM 토큰」 에 그 사람 · 모델로 쌓인다.

## 8. 되돌리기

| 무엇 | 어떻게 |
|---|---|
| 한 사람만 끄기 | 관리 › 사용자에서 그 권한을 끈다(곧바로) |
| 전부 끄기 | 에이전트 서버 `.env` 의 `CLAUDE_CHAT_MODEL` 줄을 지우고 `./start.sh -d` |
| 고를 모델 줄이기 | `CLAUDE_CHAT_MODELS` 를 고치고 재기동 — 이미 고른 값이 목록 밖이면 기본 모델로 답하고 답 아래에 알린다 |

## 9. 돌려받을 것(받은 편지함 답 — 주소 · 키는 빼고)

- 1절 점검의 결과 줄(✓ ✗ ○) — 처음 그대로, 그리고 고친 뒤.
- 설치 길 — pip 로 됐나 · Drive 묶음으로 했나.
- 지정한 사람 수와, 7절의 두 턴 결과(답한 모델 이름).
