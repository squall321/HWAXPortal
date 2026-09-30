# 서비스별 접속 이력 — 누가(이메일) 어디서(IP) 언제 어느 서비스에 들어갔나

> 2026-09-30 사용자 요청: "ip와 이메일 계정으로 각 서비스 접속 이력 알수는 있냐". 읽기 전용 조사(정문 nginx·포털 SSO·하위 앱·
> 우회 입구 네 갈래 + 검증)로 **지금은 MCP 호출과 Report Archive 만** 둘 다 남는다는 것을 확인했고, 사용자가 **A·B** 와 함께
> 고칠 것 셋을 골랐다(context-notes D-1).

## A. 포털 진입 원장(포털 리포)
| 무엇 | 어디 |
|---|---|
| 원장 | `agent_audit.sqlite` 에 새 표 `access_log`(ts·email·event·service·ip·ua·uid·detail) — 같은 파일, 같은 잠금 |
| 로그인 | 로컬 성공·실패, SSO(OIDC 콜백·SAML ACS) → `login` / `login_fail` |
| 서비스 진입 | 타일 launch(핸드오프 6종) → `launch` · ste 자격 중계 → `launch`(detail=credential) · 프록시·외부 타일 클릭 → `open`(새 `POST /systems/{id}/open`) |
| 자동 갱신 구분 | 화면의 SSO 미리 로그인(SsoPrimer)은 `?via=primer` → detail=primer(기본 화면에서 숨김) |
| 보기 | 관리자 화면 `/admin/access`(포털 관리자만) — 이메일·서비스·기간으로 거른다 |

IP 는 `request.client.host`(uvicorn 이 nginx 의 X-Forwarded-For 로 이미 실제 주소로 바꿔 둔다) — 주소 형식만 적는다.

## B. 정문 요청마다 계정(포털 리포)
- 로그인할 때 **계정 연결 ID 쿠키** `hwax_uid`(무작위 16자, httpOnly, path=/, 30일 — 하위 서비스 세션만큼, 로그아웃 때 삭제)를 주고 그 값을 A 의 login 행에 적는다.
- nginx `log_format` 끝에 `"$cookie_hwax_uid"` 한 칸 — 정문을 지나는 **모든 서비스의 요청**이 uid 로 계정과 이어진다.
- 관리자 화면에서 한 계정을 고르면 최근 N일(≤14, nginx 로그 보존)의 요청을 **서비스별로**(요청 수·처음·마지막·IP) 보여 준다.
- 쿠키는 자격이 아니다(아무것도 열지 않는다). 대신 **귀속 기록이지 증명이 아니다** — 복사한 쿠키로 남의 이름을 쓸 수 있다.

## 함께 고친 것
- `systems.yaml` 의 사내 IP(arp·odb-hub 직결 URL) → gitignore 된 `backend/config/systems.local.yaml` 로. 주소 없는 외부 타일은
  '곧 공개' 로 정직하게 내린다(주소 없이 열면 SPA 로 떨어져 조용히 깨진다).
- `usage-report.sh` 가 회전된 nginx 로그를 안 읽어 'N일' 이 실제로는 하루치였다 → 회전본(.gz 포함)까지 읽는다.
- SsoPrimer 가 실패하면 5분마다·탭 전환마다 다시 불러 401 이 6천여 건 쌓였다 → 실패가 이어지면 간격을 늘린다(최대 1시간).

## 한계
- A 는 **들어간 순간**이다. 하위 서비스 세션(12시간~30일) 동안의 재방문은 B(14일)로만 보인다.
- 정문을 안 거치는 접속(앱 포트 직결, dev 의 시스템 nginx)·외부 타일의 실제 사용은 허브가 모른다(각 시스템 로그).
- IP 는 사람이 아니다(NAT). cae00 앞단(LB 유무)은 아직 확인하지 않았다.
