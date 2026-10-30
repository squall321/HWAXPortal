# StepForge 가 운영에 묻는 글 — cae00 설정 셋 · 알림 하나 · 확인 하나

StepForge 를 cae00 에서 쓸 때 **운영이 정하거나 설정하거나 확인해야 하는 것**만 모았다(2026-10-29 · StepForge main `ff308d1` — Drive 판 `dist-20261030-034158Z`).
StepForge 코드는 1 · 2 · 3 모두 "있으면 쓰고, 없으면 그렇다고 말한다" 로 지어 두었다 — 설정이 없어도 앱은 뜨고 답한다. 정하면 그 칸이 채워진다.
제품 · 해석 쪽 결정(인스턴스 색을 읽을지 · 큰 판 계산을 C++ 로 옮길 때 등)은 여기 넣지 않았다 — 그것은 개발 쪽 사용자가 정한다.

| # | 무엇 | 지금 cae00 | 고르실 것 | 권고 |
|---|---|---|---|---|
| 1 | 응답의 공개 주소(`public_url`) | 설정 없음 — 내려받기 · 3D 보기 응답의 `public_url` 이 null(까닭 글이 함께 나간다) | 넣을지 · 어떤 오리진 | 넣는다 — 포털 `PUBLIC_BASE_URL` 과 같은 오리진 |
| 2 | MaterialTwin 주소의 정본 | HEAXHub `.env` 의 `APPTAINERENV_STEPFORGE_MATERIALTWIN_URL` | 그대로 둘지 · 허브가 형제 앱 주소를 넣게 할지 | 허브가 넣는 쪽(정해지면 StepForge 는 한 줄) |
| 3 | 관리자 판정의 게이트웨이 비밀 머리 | 허브가 내부 앱 라우트에 `X-Heax-Gateway-Secret` 을 안 싣는다 | 언제 닫을지 | 막는 도구를 붙이기 전에 닫는다 |
| 4 | 끊긴 계산의 이어 받기 시한 | 45초(`RETURN_AFTER_S`) — 받는 쪽에서 잰 창보다 짧게 잡았다 | 바꿀 일 없음 — 챗 · 게이트웨이 시한을 바꾸면 알려 주실 것 | 알림만 |
| 5 | 챗에서 실사용 1건(확인) | 사람이 아직 안 봤다 | — | 아래 '확인' 대로 한 번 |

## 1. 응답의 공개 주소

- **무엇** — 내려받기(`download_artifact`) · 3D 보기(`view_3d`) · 파일 출처(`model_provenance`) 응답이 사람이 누를 수 있는 전체 주소(`public_url`)를 싣는다. 오리진은 배포 설정에서만 읽는다(요청 머리로 짓지 않는다 — 앞단이 바꿔 쓴 머리를 믿지 않으려고).
- **지금** — 설정이 없어 `public_url` 이 null 이고 `public_url_why` 가 까닭을 말한다. 챗은 경로만 받아 사람이 주소를 손으로 잇는다.
- **하는 법** — cae00 의 HEAXHub `.env` 에 한 줄 → 앱 인스턴스를 다시 띄운다(`.env` 는 인스턴스를 띄울 때만 든다).

  ```
  APPTAINERENV_STEPFORGE_PUBLIC_BASE=https://<포털 오리진>
  ```

  오리진만 적는다 — 앱 경로(`/apps/step_forge`)는 앱이 붙인다. 포털 `PUBLIC_BASE_URL`(TLS 문서의 값)과 같은 오리진을 권한다.
- **확인** — `system_capabilities` 의 `public_base.known` 이 true · `origin` 이 그 값 · 내려받기 응답의 `public_url` 이 그 오리진 + `/apps/step_forge/…`.

## 2. MaterialTwin 주소의 정본

- **무엇** — StepForge 는 재질 원장(MaterialTwin)에서 물성을 찾는다. 주소를 찾는 차례는 ① 사람이 준 `STEPFORGE_MATERIALTWIN_URL` ② 허브가 넣는 형제 앱 주소 `HEAX_APP_URL_MATERIALTWIN_WEB` ③ 기본값 `http://127.0.0.1:9233` 이다.
- **지금** — cae00 은 ①(HEAXHub `.env` 의 `APPTAINERENV_STEPFORGE_MATERIALTWIN_URL`)이다. 닿는지는 `system_capabilities.materialtwin` 의 `reachable` 이 말한다.
- **고르실 것**

  | 안 | 하는 일 | 대가 |
  |---|---|---|
  | A | 지금처럼 `.env` 한 줄 | MaterialTwin 의 포트 · 프록시가 바뀌면 사람이 그 줄을 고친다 |
  | B | 허브가 형제 앱 주소를 `HEAX_APP_URL_<SLUG 대문자>` 꼴로 앱에 넣는다 | HEAXHub 쪽 일. 허브가 배정 포트 · 프록시 · 앞단 인증을 알아 앱이 짐작하지 않는다 |

  권고는 B 다. 이름 꼴이 위와 다르게 정해져도 StepForge 쪽은 한 줄(`core/materials.py` 의 `TWIN_HUB_ENVS`)이다. B 가 들어가면 ① 줄은 지워도 된다(남겨 두면 ① 이 먼저다).

## 3. 관리자 판정의 게이트웨이 비밀 머리

- **무엇** — StepForge 는 웹 · REST 의 포털 신원으로 관리자를 가른다(`whoami` 의 `is_admin`). 게이트웨이를 거친 호출은 늘 일반 사용자다.
- **지금** — 허브(Caddy)가 앱 라우트에 `X-Heax-User-Email` 은 싣고 `X-Heax-Gateway-Secret` 은 싣지 않는다. 그래서 앱 직통 포트에 닿는 사람은 신원 머리를 지어낼 수 있다.
  지금 관리자만 하는 일은 **관리자 목록 고치기 하나**라 피해는 작다. 다른 도구를 관리자만 쓰게 막는 일은 아직 없다.
- **하는 법(닫을 때)** — ① HEAXHub 가 내부 앱 라우트에도 `X-Heax-Gateway-Secret` 을 싣는다(포털 인증 앱과 같은 꼴 — HEAXHub 쪽 일) ② StepForge 데이터 폴더의 `secrets.env` 에 `STEPFORGE_GATEWAY_SECRET=<같은 값>` 한 줄.
  값은 이 문서에 적지 않는다.
- **고르실 것** — 지금 닫을지, 막는 도구를 붙일 때 닫을지. 권고는 **막는 도구를 붙이기 전에는 반드시** 닫는 것이다.

## 4. 끊긴 계산의 이어 받기 시한

- **무엇** — 오래 걸리는 도구 호출은 45초가 지나면 `in_progress` 로 먼저 답하고 계산을 이어 간다. 같은 호출이 다시 오면 끝난 답을 그대로 준다(`from_call`). 클라이언트가 먼저 끊으면 답을 잃지 않으려는 것이다.
- **지금** — 45초는 받는 쪽에서 잰 창에 맞췄다(10-27 StepForge 통합 요청서의 실측 — 닿은 호출 46.1 · 53.6초 · 못 닿은 호출 67.5초 · TS SDK 60초 · 게이트웨이 120초). 그 창보다 짧다.
- **알려 주실 것** — 챗 · 게이트웨이 · SDK 의 도구 호출 시한을 바꾸면 알려 주십시오. 그보다 짧게 다시 맞춘다. 늦게 알려도 답이 틀리지는 않는다(늦을 뿐이다).

## 5. 확인 — 챗에서 실사용 1건

cae00 챗에서 한 번 묻고 답을 본다. 예 — 「StepForge 에 있는 과제 하나의 파트 수와 가장 얇은 벽을 알려 줘」. 확인할 것은 셋이다.
- 답에 과제 이름 · 파트 수가 실제와 같은가(`list_projects` · `part_index`).
- 도구 오류 없이 끝났는가.
- 응답이 챗 화면에서 잘리지 않았는가.

## 답을 주실 곳

이 문서 아래에 '답' 절을 더해 적어 주시거나, 포털 `docs/request-1029/checklist.md` 의 '관련 프로젝트' 절에 적어 주시면 StepForge 가 받아 반영한다.
설정 1 · 2 를 넣은 뒤에는 앱 인스턴스를 다시 띄워야 든다.
