# AI Ready Portal(ARP) 연결 — 주소 한 줄로 묶기(RA_HOST 와 같은 방식)

> 2026-10-01 사용자 요청: "ARP 주소가 local 에 원래 있던 건데 바인딩을 해야 할 것 같다 — report archive 처럼 하려면".
> 같은 ARP 서버 주소가 두 곳(포털 타일 `backend/config/systems.local.yaml` · 게이트웨이 `provision.env` 의 `ARP_BASE`)에
> 손으로 있었다. RA 는 `infra/.env` 의 `RA_HOST` 한 줄로 update-all 1e 가 라우트·백엔드·게이트웨이를 유도한다.

## 단계(context-notes D-1)
| | 무엇 | 상태 |
|---|---|---|
| ① 주소 한 줄 | `infra/.env` `ARP_HOST`(+`ARP_PORT`, 기본 3001) → update-all **1f** 가 타일 주소(systems.local.yaml `arp.url`)와 게이트웨이 `ARP_BASE`(provision.env)를 같이 쓴다 · §5 가 게이트웨이 config 의 arp 주소가 다르면 재프로비저닝 | 이번 |
| ② 포털 경유(`/arp/`) | RA 처럼 nginx 가 ARP 로 넘긴다 — 사용자는 포털 주소만, 접속 이력에 남는다 | **보류** — ARP 가 `/login.html` 같은 절대경로로 보낸다(cae00 실측). 하위 경로에서 깨지는지 로그인 화면을 보고 정한다 |
| ③ SSO | 포털 로그인으로 ARP 로그인 | ARP 앱 쪽 작업(포털 토큰을 받는 엔드포인트) — 우리 리포 밖 |

## 하지 않는 것
- 주소를 추적 파일에 적지 않는다(공개 리포). 같은 김에 update-all·provision-config 주석의 사내 IP 예시를 지운다.
