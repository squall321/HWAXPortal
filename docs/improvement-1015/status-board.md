# 상시 상태판(Gatus) — 운영 안내

> 계획 [PLAN.md](PLAN.md) §2-1 · 결정 [context-notes.md](context-notes.md)(IM-D3 · IM-D4 · IM-D6 · IM-D7~IM-D11). 1단계(검사·화면·메일 경보)까지 지었다.

포털 인스턴스가 '떠 있음' 인데 안의 백엔드만 죽어 아무도 몰랐던 2026-10-16 아침의 사례(IM-D4)가 출발점이다. 상태판은 인스턴스가 아니라
**리스너의 응답**을 1분마다 보고, 오래 실패하면 팀 공용 주소로 메일을 보낸다.

## 무엇을 보나

| 대상 | 조건(전부 맞아야 초록) | 왜 |
|---|---|---|
| 이 박스가 다루는 서비스의 리스너 전부(`infra/services.yaml` 의 health + urls) | 연결이 된다 · `expect` 가 있으면 그 상태코드, 없으면 5xx 가 아니다 | 포털처럼 리스너가 둘인 서비스는 둘 다 본다. only_on · unless_env · if_env 를 그대로 따른다 |
| 게이트웨이 `/health` | status ok · 도구 1개 이상 · 백엔드마다 false 가 아니다 · 하나라도 false 가 아니다 | 백엔드 이름이 경보 본문에 찍힌다. 마지막 조건은 설정을 만든 뒤에 생긴 백엔드를 잡는다 |
| 에이전트 서버 `/health` | status ok · 도는 심의·줄 선 심의 칸이 있다 | 그 칸이 없으면 update-all 이 심의를 끊지 않으려고 재기동을 미루지 못한다(옛 판) |
| LLM 라우터 `/health`(풀을 켠 박스만) | status ok · 두 서버의 모델이 같다 · 올라온 서버 수가 전체와 같다 | docs/llm-pool 의 라우터다. `LLM_UPSTREAMS` 가 없는 박스에서는 보지 않는다 |

- 주기는 1분이다(`STATUS_BOARD_INTERVAL`). 성공한 조건도 실제 값을 함께 보인다 — 도구 수, 도는 심의 수가 화면에 숫자로 나온다.
- 상태판 자신은 보지 않는다. 죽으면 이 화면도 없으므로 update-all 의 5b 줄과 `services.sh status status-board` 로 본다.
- 모든 검사의 첫 조건은 '연결이 된다' 이다. Gatus 는 연결 실패만으로는 검사를 실패로 치지 않는다 — 그 조건이 없으면 죽은 포트가
  `[STATUS] (0) < 500` 으로 초록이다(2026-10-16 스모크 실측).

## 켜기 — cae00

1. **(dev, 한 번)** 이미지를 굽고 Drive 에 올린다 — `./infra/scripts/build-gatus.sh` 뒤 `./infra/scripts/images-to-drive.sh`. 둘째는
   portal·nginx 이미지와 프런트 dist 도 함께 올리고, dist 가 지금 소스로 빌드된 것이 아니면 멈춘다. 그때는 `./infra/scripts/build-all-to-drive.sh portal`
   (빌드부터 한다)을 쓴다.
2. **(cae00)** `infra/.env` 에 한 줄 — `STATUS_BOARD=1`. 경보 메일을 받으려면 `STATUS_ALERT_TO=` 에 팀 공용 주소도 적는다(아래 '경보').
3. `./infra/scripts/update-all.sh` — §2 가 Drive 에서 `gatus.sif` 를 받고(images-from-drive), 5b 가 설정을 만들고 띄운다. 끝에
   `✓ 상시 상태판 — http://127.0.0.1:8740` 이 나오면 된 것이다.
4. 재부팅 뒤에는 부팅 유닛(hwax-stack — `services.py up --update`)이 tier 30 에서 띄운다 — 설정은 `infra/.state/status/` 에 남아 있다.

손으로만 하려면 `./infra/scripts/images-from-drive.sh` → `python3 ./infra/scripts/gen-status-config.py` → `./infra/scripts/services.sh up status-board` 순서다.

⚠ `gatus.sif` 가 처음 들어오는 update-all 에서는 포털도 한 번 다시 뜬다 — deploy-all 의 포털 지문이 `infra/apptainer/*.sif` 를 보기 때문이다.
이미지 판을 올릴 때도 같다.

## 보는 곳

- 상태판은 **루프백에만** 듣는다. 화면과 API 에 로그인이 없어서다(Gatus 의 기본 주소는 0.0.0.0 이다 — 생성기가 127.0.0.1 로 묶고, 띄우는
  스크립트는 설정이 그렇지 않으면 띄우지 않는다). 정문(nginx)에 라우트를 걸지 않는다.
- 사람은 자기 PC 에서 SSH 터널로 본다 — `ssh -N -L 8740:127.0.0.1:8740 <cae00 접속 별칭>` 을 띄워 두고 브라우저로 `http://localhost:8740` 을 연다.
- 박스 안에서는 `curl -s http://127.0.0.1:8740/api/v1/endpoints/statuses` 가 JSON 으로 준다. 상태판 자체는 `./infra/scripts/services.sh status status-board` 로 본다.
- 로그는 `/tmp/hwax-services/status-board.log` 이다. WARN 이상만 남긴다 — 검사마다 쓰는 INFO 는 하루 수 MB 라 뺐다. 메일 발송 실패는 ERROR 줄
  (`Failed to send an alert`)로 남는다.
- 기록은 메모리에만 둔다. 상태판이 다시 뜨면 지난 기록이 사라진다(설정·이미지·스크립트가 바뀐 update-all 뒤).

## 경보(메일)

- **켜지는 조건** — `infra/.env` 의 `STATUS_ALERT_TO` 와 포털 `backend/.env` 의 메일 설정이 다 있어야 한다. 메일 설정은 `MAIL_BACKEND=smtp` ·
  `SMTP_HOST` · `MAIL_FROM` 이 필수이고, `SMTP_PORT`(기본 587) · `SMTP_USERNAME`·`SMTP_PASSWORD`(있으면 로그인) · `SMTP_STARTTLS`(기본 참)를 그대로
  가져온다. 받는 곳만 있고 메일 설정이 모자라면 화면만 돌고 update-all 5b 가 ⚠ 로 그 까닭을 말한다.
- **포털에 맡기지 않는다**(IM-D3) — Gatus 가 그 SMTP 서버로 직접 보낸다. 포털이 죽은 순간에도 경보는 나간다. 자격은 생성 설정
  (`infra/.state/status/config.yaml`, 디렉터리 700 · 파일 600, gitignore)에만 들어간다. 화면과 로그에는 찍지 않는다.
- **받는 곳** — 팀 공용 주소를 `STATUS_ALERT_TO` 에 쓴다(IM-D6). 여럿이면 쉼표로만 나눈다 — 이 파일은 bash 로 소싱되므로 공백을 넣지 않는다.
  추적 파일에는 적지 않는다.
- **언제** — 같은 검사가 연속 5번 실패하면(주기 1분이면 5분) 메일을 보내고, 연속 2번 성공하면 풀림 메일을 보낸다. update-all 의 재기동
  (대개 1~2분)으로는 나가지 않는다. 여러 리스너가 함께 내려가면(박스 메모리 바닥 같은 때) 검사마다 한 통씩 온다 — Gatus 는 묶어 보내지 않는다.
- **무엇이 오나** — 제목에 `<서비스>/<호스트:포트/경로>` 가, 본문에 조건마다 ✅·❌ 와 실제 값이 온다(예를 들면 게이트웨이 백엔드 하나가
  내려가면 `❌ [BODY].backends.<그 이름> (false) != false`). 본문 끝에 확인 명령(`./infra/scripts/services.sh status <서비스>`)을 붙였다.
- **STARTTLS** — 포털이 `SMTP_STARTTLS` 참(기본)이면 Gatus 도 서버가 내밀면 STARTTLS 를 쓰고 인증서를 검증한다. 사내 CA 로 서명한 서버면
  호스트의 CA 묶음(`/etc/ssl/certs/ca-certificates.crt` 또는 `/etc/pki/tls/certs/ca-bundle.crt`)에 그 CA 가 있어야 한다 — 띄우는 스크립트가
  그 파일을 컨테이너의 CA 묶음 자리에 읽기 전용으로 덮는다. 거짓이면 Gatus 는 STARTTLS 를 끌 수 없어(서버가 내밀면 쓴다) 검증 없이 쓴다.
- **Graph 박스** — Gatus 는 Graph 로 못 보낸다. 독립 발신기는 2단계다(IM-D3).
- **시험 발송** — Gatus 에는 '지금 보내기' 단추가 없다. 운영 박스에서 서비스를 일부러 내리지 말고, 첫 실제 경보를 기다리거나 같은 SMTP 설정으로
  dev 에서 확인한다. 발송이 실패하면 위 로그의 ERROR 줄로 보인다.

## 끄기

`infra/.env` 에서 `STATUS_BOARD` 줄을 지운다. 값을 0 으로 두면 켜짐으로 읽힌다(값이 있으면 켜는 if_env 다 — update-all 이 ⚠ 로 알린다).
다음 update-all 의 5b 가 떠 있는 상태판을 내리고 ○ 를 남긴다. 바로 내리려면 `./infra/scripts/status-board.sh stop` 이다.

## 포트·주기 바꾸기

- `STATUS_BOARD_PORT`(기본 8740) — 9100~9999 는 HEAXHub 앱 포트 풀이라 쓰지 않는다([PORT-MAP](../PORT-MAP.md)). 바꾼 뒤 update-all 을 돌리면
  새 포트로 뜬다. 옛 포트의 상태판은 손으로 내린다 — `STATUS_BOARD_PORT=<옛 포트> ./infra/scripts/status-board.sh stop`(stop 만 환경의 포트를
  먼저 본다. update-all · update-sites 는 물려받은 이 값을 버린다).
- `STATUS_BOARD_INTERVAL`(기본 1m) — 수와 s·m·h 하나다(30s · 1m · 5m). 짧게 하면 경보도 그만큼 빨라진다(연속 5번).
- 틀린 값(포트가 수가 아니다 · 길이 모양이 아니다 · 받는 곳이 주소 모양이 아니다)이면 생성기가 설정을 쓰지 않는다. 옛 설정이 있으면 그대로 돌고
  update-all 은 ✗ 로 센다.

## 무엇이 어디에

| 무엇 | 어디 |
|---|---|
| 이미지 굽기(판 고정 — 태그와 다이제스트) | `infra/scripts/build-gatus.sh` → `infra/apptainer/gatus.sif` |
| Drive 운반 | `images-to-drive.sh` · `images-from-drive.sh`(latest/ 의 gatus.sif) · `drive-drift.sh` |
| 설정 생성기 | `infra/scripts/gen-status-config.py` |
| 생성 설정(메일 자격 포함, gitignore) | `infra/.state/status/config.yaml`(디렉터리 700 · 파일 600) |
| 띄우기·내리기 | `infra/scripts/status-board.sh {run\|stop}` |
| 매니페스트 항목 | `infra/services.yaml` 의 `status-board`(tier 30, `if_env: STATUS_BOARD`) |
| update-all | 5b(§5 뒤 · §6 앞) |
| 시험 | `backend/tests/test_status_board.py` |

## 판

지금 판은 **Gatus v5.37.0**(2026-09-24 공개)이다. 다이제스트는 `build-gatus.sh` 에 적혀 있다(그 태그의 다중 아키텍처 목록). 올릴 때는
`GATUS_VERSION` · `GATUS_DIGEST` 두 줄을 함께 고치고 굽는다 — 받은 이미지의 판 라벨이 태그와 다르면 굽기가 멈춘다. 새 판에서 다시 볼 것은
설정 키(web · ui · endpoints · alerting.email · skip-invalid-config-update), 조건 문법(has() · pat() · any()), 설정 글의 `$` 풀이다.

## 2단계(아직 아니다)

- **스크립트가 필요한 검사** — `infra/scripts/mcp-smoke.py`(실제 도구 호출)와 Drive `latest/` 의 나이(마지막으로 올린 때)는 Gatus 가 직접 못
  본다. 주기 스크립트가 결과를 Gatus 의 외부 끝점(external-endpoints)으로 밀어 넣는다. 검사용 PAT 는 읽기 전용 그룹으로 따로 발급한다(사람 몫).
- **Graph 박스의 독립 발신기**(IM-D3).
- **기록 보존** — 필요하면 Gatus 저장소(sqlite)를 `infra/.state/status/` 아래에 둔다.
- **update-all 동안 경보 멈춤** — 지금은 연속 5번 문턱으로만 피한다.

## 함정

- 생성 설정을 손으로 고치면 다음 update-all 이 덮는다. 손잡이는 `infra/.env` 에만 둔다.
- 생성 설정의 `$` 는 두 번 적혀 있다 — Gatus 가 설정 글 전체에서 `$이름` 을 환경변수로 풀기 때문이다(두 번 적으면 하나로 읽는다). 비밀번호를
  손으로 옮겨 적을 때 하나로 줄이지 않는다.
- 게이트웨이 백엔드 이름은 설정을 만들 때 떠 있는 게이트웨이에서 읽는다. 그때 게이트웨이가 답하지 않았으면 이름 없이 '하나라도 false' 한 줄만
  싣는다(생성기가 그렇게 말한다) — 다음 update-all 이 채운다.
