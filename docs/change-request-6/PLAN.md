# 6차 변경 요청 반영 — 운영 ADFS 는 NameID 가 없다 · 이름·그룹 Claim 이 없다

> 2026-10-01 요청서(요청자 koo.park, 기준 HEAD `0e9ef99`). 원문은 요청자 리포의 PORTAL-CHANGE-REQUEST-6.md.
> 근거는 SSO 운영팀 핸드오프(진단 앱 로그인 성공, `nameIdPresent=false`, Claim 다섯 개 LoginId·CompId·DeptId·Sabun·Mail).
> 요청서는 같은 날 두 번 개정됐다 — 2판에서 §3(식별자를 LoginId 로)을 철회하고 '그룹이 비면 권한이 닫힌다' 를 정정했고,
> 3판에서 §3 을 'subject 를 못박아 달라' 로 다시 쓰고 §4-B(이름·조직명 대체 사슬)를 더했다.

## 반영 표
| § | 무엇 | 어디 | 비고 |
|---|---|---|---|
| 2 | `wantNameId` 를 설정으로(`SAML_WANT_NAMEID`, 기본 참) | `config.py` · `saml_sp.py` · `.env.example` | 요청 그대로. 운영은 `.env` 에 false |
| 2 (발견) | NameID 부재가 400 이 아니라 **500** 이었다 — 라이브러리 예외를 400 과 사유로 | `saml_provider.py` | D-2 |
| 2 (발견) | SAML 이메일 정규화(소문자·공백) — 로컬 계정 시절 소유가 이어지게 | `saml_provider.py` | D-3 |
| 2 (같이) | `NameIDFormat` | 바꾸지 않음 | D-4 |
| 3 | 식별자를 LoginId Claim 에서 | **넣지 않음**(요청자 철회) | subject=정규화한 이메일 유지 — D-5 |
| 3 (3판) | subject 출처를 **못박기**(`SAML_SUBJECT_SOURCE`, 기본 email) | `config.py` · `saml_provider.py` | 다른 출처가 없으면 거절 — D-8 |
| 4 | 이름·그룹 Claim 없음 — 화면·감사·권한이 견디는가 | 전수 점검(포털·하위 9곳) | D-6 · D-7 |
| 4-B-1 | 이름 대체 사슬 IdP → 원장 → 이메일 | `deps.py` entitled | D-9 |
| 4-B-2·3·4 | 부서 수확(`SAML_ATTR_DEPARTMENT`)·원장 upsert(이름 빈 때만·부서 덮기·권한 칸 불가침) | `session.py` · `user_store.py` | D-10 |
| 4-B-5 | 지정한 Claim 이 없으면 경고(이름만) | `saml_provider.py` | D-11 |
| 5 | nginx 리로드로 `/auth/callback` 전환 | 포털 코드 아님 — 요청자·SSO 운영팀 몫 | 손대지 않는다 |

## 시험
`backend/tests/test_saml_adfs_shape.py` — dev mock IdP 가 **실제로 서명한** Assertion 에서 NameID 를 빼고 Claim 을 운영 모양
(URI 이름 다섯 개, 이름·그룹 없음)으로 바꿔 실제 SP 검증 경로로 끝까지 돌린다.
