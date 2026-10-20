# 설정 배치가 Claude Code 를 못 찾는 문제

## 증상 (사용자 보고 2026-09-09)

"클로드 경로가 다른 사람들 중 셋업이 안 되는 사람이 있나 보다."

`hwax-claude-setup.bat` 이 Claude Code 등록 단계를 **건너뛴다.** 그리고 이렇게 말한다.

```
[2] Claude Code (CLI) 확인...
     claude 명령 없음 - 건너뜀 (Claude Desktop 만 쓰신다면 정상)
```

## 원인

`TokenPage.tsx` `buildSetupBat()` 이 `where claude` **하나로만** 판정한다.

```
'where claude >nul 2>nul',
'if errorlevel 1 goto :no_cli',
...
':no_cli',
'echo      claude 명령 없음 - 건너뜀 ^(Claude Desktop 만 쓰신다면 정상^)',
```

`where` 는 **PATH 에 있는 것만** 찾는다. Claude Code 가 깔려 있어도 PATH 에 없으면 실패한다.
그리고 그 상황에서 배치는 **"정상"** 이라고 말한다 — 설치해 둔 사용자에게 정반대 안내다.

이 세션 내내 고쳐 온 그 모양이다. **실패가 성공처럼 보인다.**

PATH 에 없을 수 있는 조건(확인해서 채운다).
- 설치 프로그램이 PATH 를 사용자 환경변수에 넣었는데, 이미 열려 있던 Explorer·셸 세션에는
  반영이 안 됨 → 재로그인 전까지 `where` 실패
- npm 전역 설치 prefix 가 PATH 에 없음
- 다른 사용자 계정으로 설치했거나 배치를 다른 권한으로 실행

## 고칠 것

1. **폴백 탐색** — `where` 가 실패하면 알려진 설치 위치를 순서대로 뒤진다. 찾으면 그
   **절대 경로**로 등록을 진행한다(격리 .cmd 안의 `claude` 를 그 경로로 바꾼다).
2. **정직한 안내** — 못 찾았을 때 "정상" 이라고 하지 않는다. 세 가지를 구분한다.
   - 설치 흔적이 없다 → Claude Desktop 만 쓴다면 정상
   - 설치 흔적은 있는데 실행이 안 된다 → 재로그인/PATH 안내
   - 어느 쪽인지 모르겠다 → 수동 명령(페이지에 이미 있다)을 그대로 안내
3. **다음 단계가 이어지게** — 지금도 `goto :desktop` 으로 이어지지만, 사용자가 무엇을
   해야 하는지 화면 끝 요약에 남긴다.

## 원칙

- PATH 가 아니라 **파일이 있느냐**로 판정한다. `where` 는 빠른 길이지 유일한 길이 아니다.
- 찾은 경로를 그대로 등록에 쓴다 — PATH 를 고치라고 시키지 않는다(사용자 PC 환경을
  배치가 바꾸는 것은 범위 밖이고, 되돌리기도 어렵다).
- 못 찾으면 **모른다고 말한다.** 추측으로 "정상" 이라고 하지 않는다.

## 범위 밖

- PATH 자체를 배치가 수정하는 것
- 이미 보류 중인 자체서명·프록시 체인 재설계([[hwax-mcp-bat-registration-backlog]])

## 실측 확인 (2026-09-09)

배치 생성기를 브라우저 없이 떼어 내 산출물을 뽑고, cmd 의 `goto`/`if` 흐름을 그대로
따라가 다섯 경우를 검증했다.

| 경우 | 도달 라벨 |
|---|---|
| PATH 에 있음 | `:cli_go` |
| PATH 없음 · 네이티브 설치(`%USERPROFILE%\.local\bin\claude.exe`) | `:cli_go` |
| PATH 없음 · npm(`%APPDATA%\npm\claude.cmd`) | `:cli_go` |
| PATH 없음 · npm(`.exe`) | `:cli_go` |
| 설치 안 됨 | `:no_cli` |

토큰이 콘솔에 찍히는 줄은 0건이다(`echo` 로 시작하며 토큰을 포함한 줄 없음).

## 근거 — 설치 경로와 PATH 반영 시점

공식 설치 문서 기준.

- 네이티브 설치: `%USERPROFILE%\.local\bin\claude.exe`(실제 바이너리는
  `%USERPROFILE%\.local\share\claude\versions\<VERSION>\claude.exe`)
- npm 전역: prefix 기본값이면 `%APPDATA%\npm\claude.cmd`(또는 `.exe`). prefix 를 바꾼
  사람은 그 경로가 PATH 에 있을 것이므로 `where` 로 잡힌다.
- WinGet: 경로가 문서에 없다. 다만 PATH 에 자동 등록되므로 `where` 로 잡힌다.
- **PATH 는 사용자 PATH 에 추가되고, 이미 열려 있던 셸 세션에는 반영되지 않는다.**
  문서가 "새 터미널을 열라"고 명시한다. 설치 직후 Explorer 에서 배치를 더블클릭하면
  `where` 가 실패하는 정확한 이유다.

---

# 10-20 — 설치 파일 개선 요청 다섯(염종섭 님, 2026-10-20)

> 체크리스트 [checklist.md](checklist.md) · 결정과 까닭 [context-notes.md](context-notes.md)(TB-D1~). 사용자 결정 10-20 —
> "고친다 · 인증서는 윈도우 저장소에서", '우리쪽 토큰 발급 오류' 는 이 배치 문제와 같은 것.

| # | 요청 | 지금(고치기 전) | 고친 것 |
|---|---|---|---|
| 1 | Microsoft Store 판 Claude 의 설정 위치 | `%APPDATA%\Claude\claude_desktop_config.json` 하나만 고친다 — Store 판은 `%LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\Claude\` 를 읽어 '완료' 인데 hwax 가 안 보인다 | 두 위치를 다 찾아 설정 폴더가 있는 곳마다 반영하고, 어디를 고쳤는지 줄마다 찍는다 |
| 2 | 대소문자만 다른 키(NO_PROXY · no_proxy) | Desktop 은 `ConvertFrom-Json`(5.1)이 중복 키로 보고 멈춘다. Claude Code 설정도 같은 이유로 멈춘다(그쪽은 실패를 알리고 원본은 그대로) | 대소문자를 구분하는 .NET `JavaScriptSerializer` 로 읽고 쓴다(두 파일 모두). 고치기 전 원본 백업은 그대로 |
| 3 | 사내망 설정(NODE_EXTRA_CA_CERTS · NO_PROXY) | `NODE_EXTRA_CA_CERTS` 는 포털 인증서만, `NO_PROXY` 는 배치 창 안에서만 | hwax env 에 `NO_PROXY=<포털 호스트>,localhost,127.0.0.1` 를 기본으로. `NODE_EXTRA_CA_CERTS` 는 포털 인증서 + 이 PC 의 윈도우 신뢰 저장소(회사 루트 인증서 포함)를 한 파일(`%USERPROFILE%\.hwax\hwax-ca-bundle.pem`)로 묶어 가리킨다 — 사람마다 다른 '회사 인증서 경로' 를 몰라도 된다 |
| 4 | 토큰 갱신 때 손으로 맞춘 설정이 지워짐 | hwax 항목을 통째로 덮어쓴다 | 이미 있으면 그 항목을 바탕으로 토큰(AUTH)과 우리가 정하는 칸(명령 · 주소)만 바꾼다. 손으로 넣은 env 는 남고, `NO_PROXY` · `NODE_EXTRA_CA_CERTS` 를 이미 적어 뒀으면 그 값을 쓴다(예전 배치가 넣은 포털 인증서 경로만 새 묶음으로 바꾼다) |
| 5 | Claude 가 켜진 채 설치하면 되돌아감 | '켜져 있으면 끄고 다시 켜라' 안내만 | 설정을 바꾸기 전에 실행 중인 Claude Desktop(설치판 · Store 판)을 찾으면 아무것도 바꾸지 않고 멈춰 '트레이 아이콘까지 종료' 를 안내한다 |

대상은 Claude 쪽이다(Desktop · Claude Code). Gemini · Codex 는 자기 CLI 로 등록해 쉼표가 든 `NO_PROXY` 값을 어떻게 나누는지 여기서 재 볼 수 없어
그대로 둔다(인증서 묶음 경로만 같이 쓴다). 이 배치는 dev 에 PowerShell 이 없어 산출물의 글만 시험한다 — 실제 Windows 확인은 염종섭 님 PC
(Store 판 · 대소문자 중복 키가 있는 설정)에서 받는다.
