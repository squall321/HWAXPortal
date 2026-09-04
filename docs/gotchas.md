# 함정 — 실제로 사고가 났던 것들

이 문서가 존재하는 이유가 있다. 이 내용들은 원래 **에이전트 개인 메모리**에만 있었다.
그 저장 경로가 프로젝트 절대경로를 키로 쓰기 때문에(`~/.claude/projects/-home-koopark-claude-HWAXPortal/`),
리포 경로가 다른 박스(cae00 = `~/Projects/…`)에서는 **한 건도 안 보인다.** 같은 모델이
같은 도구를 물고도 결과가 나빠지던 원인 중 하나였다. 박스를 안 타도록 리포로 옮긴다.

새로 얻은 교훈은 여기 추가한다. 규칙은 하나다 — **실제로 겪은 것만 적는다.**

---

## 1. 포트로 프로세스를 죽일 때 `-sTCP:LISTEN` 을 빠뜨리면 남을 죽인다

포털 `restart.sh` 의 `lsof -ti tcp:8723` 이 그 포트에 **연결 중이던** MCP 게이트웨이
(:9110, 상시 서비스)를 함께 죽였다. 수정 커밋 `fc314b6`.

`lsof tcp:PORT` 는 **리스너와 클라이언트 소켓을 구분하지 않는다.** 이 박스는 서비스들이
서로 로컬 포트로 붙어 있어서, 재시작 하나가 무관한 상시 서비스를 조용히 내린다.

```bash
lsof -t -i:8723 -sTCP:LISTEN     # ✅ 리스너만
ss -ltnp | grep ':8723 '          # ✅ 대안
lsof -ti tcp:8723                 # ❌ 붙어 있는 클라이언트까지 잡힌다
```

`pkill` 은 이 환경에서 막혀 있다(종료코드 144). 포트 → PID → `kill` 로 간다.

## 2. `git status` 를 자르면 남의 미커밋 작업을 무효화한다

여러 세션이 같은 리포를 동시에 만진다. `git status | head -N` 으로 자르거나 `git add` 전에
그 파일의 unstaged diff 를 안 보면, 작업트리에 남아 있던 **다른 세션의 변경(또는 리버트)** 을
내 커밋에 함께 실어 남의 수정을 되돌린다.

- **2026-07-29** — WDA 매니페스트의 `health_check` 위치만 고치려다, 남아 있던 리버트를 같이
  커밋해 다른 세션의 진단을 무효화했다. SIF 빌드가 `ERR_PNPM_NO_PKG_MANIFEST` 로 실패했고
  복구에 별도 커밋이 필요했다.
- **2026-08-07** — `git add docs/` 로 **디렉터리를 통째 스테이징**해, 세션 시작 시점부터
  untracked 였던 다른 세션 작업물을 함께 커밋했다. `git add -A` 를 피해도 **디렉터리 인자**면
  같은 사고가 난다.

```bash
git status --porcelain          # 자르지 않는다
git diff -- <파일>              # 내가 만든 변경이 맞는지 본다
git add <파일> <파일>            # 디렉터리 말고 파일로
```

## 3. dev 박스에서 `deploy-all-from-drive.sh` 를 돌리면 리포가 리셋된다

`git_update()` 가 각 리포에서 **stash + `git reset --hard origin/$branch`** 를 한다.
cae00(배포 대상)에서는 맞는 동작이지만, **dev 에서 시험 삼아 돌리면 미푸시 커밋과 작업 중
편집이 통째로 날아간다.** `want portal` 이면 HWAXPortal 자신도 대상이다.

**2026-08-19 실사고** — 종료코드를 확인하려고 dev 에서 몇 번 돌렸다가 로컬 커밋 3개와
미커밋 편집이 사라졌다. reflog 에 `reset: moving to origin/main` 만 12줄 남는다.

복구는 된다. 커밋은 객체로 살아 있어 `git reset --hard <lost-sha>`, 편집은 `git stash list`
의 `deploy-all auto-stash`.

⚠ **환경변수로 우회가 안 된다.** `MXWP_DIR=/nonexistent` 를 줘도
`find_repo "${MXWP_DIR:-}" MXWhitePaper` 가 못 찾으면 **스스로 찾아낸다.** 그래서 "안 건드리게
하려고" 준 값이 무시되고 실제로 MXWhitePaper 가 재배포돼 서비스가 내려갔다.

빌드 경로만 시험하려면 `build-all-to-drive.sh` 를 쓴다 — 이건 안전하다.

## 4. ReportArchive 리포는 손대지 않는다

RA 는 federation 자동화의 **제외 대상**이다 — `services.yaml` 에서 `update: false`,
`update-sites.sh` 의 `EXCLUDE="report-archive"`. 사용자가 반복해서 못박은 사항이다.

- 커밋·push 금지. 원격을 건드리지 않는다. 쓰려면 **API 로만** 쓴다.
- untracked 로컬 파일(`start.sh` 등)의 하드코딩을 로컬에서 고치는 건 되지만 **push 하지 않는다.**
- ⚠ untracked 파일을 `git add` → commit 한 뒤 `git restore --source=HEAD` 하면 HEAD 에 없어서
  **파일이 삭제된다.**

## 5. e5 임베더는 코사인 절대값이 원래 높다 — 임계값을 쓰지 마라

AIDataHub `/api/embed` 는 multilingual-e5-base(768차원)를 서비스한다
(`EMBEDDING_PROVIDER=e5_base`).

실측(2026-08-19).

| 쌍 | 코사인 |
|---|---|
| "번인과 붉은 얼룩의 경시 열화" vs **"김치찌개 끓이는 법"** | 0.895 |
| "번인과 붉은 얼룩의 경시 열화" vs "OLED 디스플레이 번인 열화" | 0.903 |

무관한 쌍과 유사한 쌍의 차이가 **0.008** 이다. 이걸 보고 "임베더가 변별을 못 한다"고
판단하면 **틀린다.**

> **질의별 절대값을 가로로 비교하는 것은 무의미하고, 한 질의 안에서의 순위가 신호다.**

제대로 된 평가는 코퍼스에 있는 알려진 청크의 일부를 질의로 넣어 그 청크의 순위를 보는
것이다. 그렇게 재면 1096청크에서 1위 적중 8/12, 5위 내 12/12, 미검출 0 이 나온다.

`EMBEDDING_PROVIDER` 미설정이면 조용히 `HashEmbedder` 로 떨어진다 — 그 경우 무관한 쌍의
코사인이 0 근처로 흩어지므로 위 baseline 과 구분된다.

## 6. 긴 질의로는 다른 좌석을 못 찾는다 — 부정은 검색이 아니라 추론이다

심의 좌석 발굴에서, 원 질문에 "이 분야들 밖"을 덧붙이는 **역질의는 작동하지 않는다.**
질의의 대부분이 원 질문이라 임베딩 이웃이 그대로 돌아온다.

**실측 2026-08-07** — S26U 화두 역질의 상위 5 중 4가 기존 좌석과 동일했고, 신규 1명도 같은
도메인이었다. 같은 실측에서 **짧은 도메인 질의는 정확히 다른 좌석을 돌려줬다.**

| 질의 | 찾은 좌석 |
|---|---|
| "봉지 수분 산소 침투 신뢰성" | `rel-chemical-corrosion` |
| "접착제 OCA 경화 잔류물" | `disp-module-bonding` |

풀에는 있는데 질의가 못 닿고 있었을 뿐이다. **긴 텍스트를 한 벡터로 만들면 평균값이 되어
변별이 죽는다.** 대화 전체로 좌석을 찾고 싶으면 통째로 던지지 말고 **축으로 쪼개
축마다 짧은 질의**를 돌린다(`_counter_seats` 가 쓰는 방식).

## 7. 도구는 소스에 있다고 쓸 수 있는 게 아니다

게이트웨이는 **실행 중인 앱이 가진 도구**만 노출한다. 앱 소스에 있어도 배포된 SIF 가
커밋보다 낡으면 없다.

**2026-09-01** — StepForge `intake` 가 소스에 분명히 있었는데 첫 e2e 가
`unknown tool: intake` 로 터졌다. 그날 23:16 커밋이었고 SIF 는 그보다 낡았다.
`set_project_meta`·`get_project_meta` 도 같은 커밋이라 함께 없었다.

도구 이름은 **게이트웨이 `tools/list` 로 대조한다.** 자세한 경위는
[upload/context-notes.md](upload/context-notes.md) D-8.

## 8. Drive 업로드에 타임아웃을 걸면 조용히 낡은 채로 남는다

`dist-to-drive.sh` 를 `timeout 1800` 으로 감쌌다가 11GB 짜리가 매번 시간 초과로 죽어
(종료코드 143) `latest/` 가 갱신되지 않았다. 소비자는 `latest/` 를 선호하므로 **에러 없이
옛 산출물을 가져간다.**

수리는 서버사이드 `rclone copyto`(대역폭 0)로 했고, 이때 `SHA256SUMS` 를 함께 새로 만들어야
한다 — 안 그러면 소비자의 `sha256sum -c` 가 실패한다.

그리고 **코드는 Drive 로 가지 않는다.** 코드는 git push, 산출물만 Drive 다.

## 9. 워크플로 journal 스키마 — `completed` 가 아니라 `result` 다

심의 진행을 스크립트로 지켜볼 때 매번 헛짚는 자리다. 트랜스크립트 디렉터리의
`journal.jsonl` 은 이 모양이다.

```
{"type":"started", "agentId":"a1b2…", "key":"v2:…"}
{"type":"result",  "agentId":"a1b2…", "key":"v2:…", "result":"<에이전트 반환값 문자열>"}
```

- 완료는 **`result`** 다. `completed` 를 기다리면 영원히 안 온다.
- **`label`·`phase` 가 없다.** 어느 좌석·어느 라운드인지 알려면 `result` 를 파싱해
  키로 가려야 한다 — `reads` 있으면 초기, `concede` 있으면 심화, `final_position` 있으면 수렴.
- 짧은 `"OK"` 결과는 RA 페이지 저장 에이전트다(정상). 숫자 하나는 `create_report_draft` 가
  돌려준 `report_id` 다.

진행률은 `started` 수 − `result` 수로 본다.

## 10. 의장 결정문이 잘려서 돌아올 수 있다

의장이 응답을 여러 턴에 나눠 쓰면 **마지막 턴만 반환값이 된다.** 실측(2026-09-02):
2단 해석 계획서 61,246자 중 **709자만** 돌아왔다.

- 감지는 자동이다 — 결정문이 `## `/`# ` 로 시작하지 않으면 워크플로가 경고를 띄우고
  반환값에 `decisionTruncated: true` 를 싣는다.
- **복원은 사람 몫이다.** 워크플로가 전사에 접근할 수 없다. 트랜스크립트 디렉터리의
  `agent-<id>.jsonl` 에서 assistant 텍스트 블록을 순서대로 이어 붙이면 전문이 나온다.
- 프롬프트로 "한 응답에 끝내라"고 지시해 뒀지만 지켜지지 않는다. 지시가 아니라 감지를 믿는다.

## 11. 도구 이름이 앱을 넘어 겹친다

게이트웨이는 326개 도구를 한 네임스페이스에 평평하게 노출하고, **완전 동명일 때만**
프리픽스를 붙인다. 의미가 겹치는 다른 이름은 안 걸린다.

| 도구 | 소속 | 첫 인자 |
|---|---|---|
| `get_section` | 문서 편집 앱 | `slug` |
| `get_record_sections` | AIDataHub | `record_id` |

실측 — 좌석이 AIDataHub `record_id` 를 들고 이름이 그대로인 `get_section` 을 불러 오류 4회.
두 설명에 앱 경계를 박아 두었지만, **새 앱을 붙일 때 이름 충돌을 먼저 확인하는 편이 낫다.**

## 12. Node CLI 를 배치(.bat)에서 직접 부르면 배치가 조용히 죽는다

사내 PC 실측(2026-09-04). PAT 발급 시 내려주는 `hwax-claude-setup.bat` 이
`claude mcp add` 줄에서 **아무 에러 없이** 끝나 이후 단계가 통째로 실행되지 않았다.

- `claude mcp add` **자체는 성공**한다 — `~/.claude.json` 도 정상 수정되고 CLI 가
  "Added stdio MCP server" 까지 찍는다. 그런데 **그것을 호출한 배치 프로세스**가
  다음 줄로 못 넘어간다. `echo AFTER` 조차 안 찍힌다.
- 같은 명령을 **터미널에 직접 타이핑하면 100% 정상**이다. 즉 "배치 안에서 직접 호출"
  만의 문제다(claude 가 콘솔 raw mode/VT 를 건드리는 것으로 추정 — 내부 기전 미확인).
- 화면에는 에러가 없고 프롬프트로 돌아가서 **"조용히 끝났나 보다"로 오해**한다.
  PAT 를 재발급해도 뒷단계가 안 돌아 **옛 토큰이 그대로 남는다**.

**해결(실측 검증)** — 호출부를 임시 `.cmd` 로 떼어내 격리 실행한다.

```bat
>>"%TMPCMD%" echo claude mcp add -s user hwax ... --header "Authorization:${AUTH}"
start "" /wait cmd /c "%TMPCMD%"
set "HWAX_RC=%errorlevel%"        rem del 보다 먼저 — del 이 errorlevel 을 덮는다
del "%TMPCMD%" >nul 2>nul         rem 임시파일에 PAT 평문이 들어간다. 반드시 지운다
```

`gemini`/`codex` 도 같은 Node CLI 라 동일하게 격리한다(`frontend/src/pages/TokenPage.tsx`
의 `isolatedCli`). `claude mcp get` 은 배치에서 직접 불러도 됐다는 관측이 있으나 표본이
적어 같이 격리했다.

곁들여 확인된 것 — 네트워크 점검을 **로그인 필요한 `/`** 로 하면 `Invoke-WebRequest` 가
4xx/302 에 예외를 던져 "직접 연결 실패(VPN 확인)" 오탐이 난다. 무인증 `/health` 를 찌르고,
응답을 받았으면(`$_.Exception.Response`) 도달로 판정한다.
