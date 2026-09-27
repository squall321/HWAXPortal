# Report Archive 재연결 — RA 가 포털 박스를 떠났다, update-all 한 번에 새 주소로 잇는다

> 요청서 정본: `../ReportArchive/docs/[참고] HWAX포탈_연동_요청서.md`(RA 리포, 2026-09-26). 이 문서는 **포털 쪽 답**이다.
> RA 리포에는 쓰지 않는다(hands-off). 내부 주소는 추적 파일에 적지 않는다 — 요청서 §1 을 가리킨다.

## 0. 문제

RA 가 cae00(포털 박스)에서 새 서버쌍(A 주 · B 대기)으로 이사했고 공개 주소는 `https://hwax.sec.samsung.net/report-archive/` 다.
포털은 RA 를 **"같은 박스의 :3000"** 으로 알고 있는 곳이 여덟이다(요청서 §2) — 그대로 두면 ① 스택 재기동이 **구 RA 를
되살려** 두 DB 가 갈라지고 ② 챗의 RA 도구·PAT 연결이 구 DB 를 보고 ③ 구 설치본을 지우는 날 포털 챗·심의·PaperIngest 의
**LLM 설정이 조용히 빈다**(env-kit 이 RA `.env` 를 상속한다).

## 1. 원칙

- **운영자 값은 하나** — `infra/.env` 의 `RA_HOST`(A 서버 주소). 나머지(라우트·`RA_BASE_URL`·`RA_MCP_URL`)는 update-all 이 **유도**한다.
  손으로 세 파일을 맞추라고 하면 하나가 빠진다(ste 의 `STE_SSO_URL` 이 그렇게 죽어 있었다 — docs/one-token D-12).
- **박스를 가르지 않고 설정으로 가른다** — `RA_HOST` 가 있으면 "RA 는 원격", 없으면 "같은 박스"(dev). 호스트명 분기 없음.
- **정본은 포털 쪽에** — LLM 설정을 RA `.env` 에서 한 번 떼어 `infra/.env` 로. RA 는 공용 LLM 의 정본일 이유가 없다.
- **RA 코드는 건드리지 않는다** — 요청서가 맞다: 포털에 RA 전용 코드는 생기지 않는다. 설정·오케스트레이션·문서만.

## 2. 무엇을 바꾸나 (요청서 항 ↔ 포털 변경)

| 요청 | 변경 | 자동/1회 |
|---|---|---|
| 3-1 구 RA 를 오케스트레이터에서 뺀다 | `services.yaml` 두 항목에 `unless_env: RA_HOST`(services.py 가 읽는다) — RA_HOST 있는 박스에서 "이 박스 대상 아님" | 자동 |
| 3-2 라우트 | update-all **1e** 가 `routes.local.env` 에 `report-archive=http://<RA_HOST>:3000/` upsert(끝 `/` = STRIP) | 자동 |
| 3-3 대용량·장시간 | `gen-nginx-conf.sh` `loc_extras()` 에 `report-archive` | 코드 |
| 3-4 주소 | 1e 가 `backend/.env` 의 `RA_BASE_URL`, 게이트웨이 `provision.env` 의 `RA_MCP_URL` upsert · §5 가 config 와 다르면 재프로비저닝(`RA_MCP_URL` 을 provision 에 넘긴다 — 전엔 안 넘겼다) | 자동 |
| 3-5 LLM 상속 떼기 | `apply-envs.sh` 가 `@FROM_RA:LLM_*@` 를 **`infra/.env` 먼저**, 없으면 RA `.env` 로 푼다 · 1e 가 RA `.env` 에서 `infra/.env` 로 한 번 복사 | 자동(1회 이관) |
| 3-6 update-all RA 분기 | RA_HOST 있으면 로컬 기동 금지·헬스는 원격으로 | 코드 |
| 4-1 타일 세 줄 | `systems.yaml`: `jwt-handoff` · `audience: report-archive` · `url: /report-archive/api/auth/portal-callback` | 코드 |
| 4-2 JWKS 주소 | 1e 가 후보 둘을 **찍어 준다**(사내망 http · 공개 https) + 로컬 프로브. 사람이 RA 담당에게 준다 | 1회(사람) |
| HTTPS | 포털 nginx 가 종단이다(ENABLE_TLS). 인증서 종류는 `/tls/info`·`ste-doctor tls` 행 — 사내 CA 면 RA 서버에 `/tls/ca.crt` | 판정은 cae00 |

## 3. 검증

- dev: 시험(1e 하네스 — TEST-NET 주소로 세 파일 upsert·멱등·LLM 이관, `unless_env`, loc_extras, 타일, §5 전달) + 전체 스위트.
- dev 실주행: `RA_HOST` 없이 update-all 의 ○ 장부에 "Report Archive 원격 재연결 — RA_HOST 미설정" 한 줄(dev 는 같은 박스라 정상).
- cae00(사용자): `infra/.env` 에 `RA_HOST=<A>` → `update-all` → 요청서 §8 체크리스트 8줄. 그리고 RA 담당에게 JWKS 주소 전달.

## 4. 하지 않는 것

- B(부) 자동 전환 — 요청서 §5·§6 대로 지금은 사람이 `RA_HOST` 를 B 로 바꾸고 재실행한다(그러면 셋이 같이 따라간다).
- RA 리포 수정·`PORTAL_JWKS_URL` 설정(RA 몫).
