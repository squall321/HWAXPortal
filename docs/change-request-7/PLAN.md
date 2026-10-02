# 7차 변경 요청 반영 — 운영 SSO 로그인 성공, 그 패치(NameIDPolicy)와 SLO 광고 정합

> 2026-10-02 요청서(요청자 koo.park, 기준 HEAD `4688f14`). 원문은 요청자 리포의 PORTAL-CHANGE-REQUEST-7.md.
> 요청자가 §1 을 cae00 추적 파일에 직접 얹어 **운영 로그인 성공**까지 확인한 뒤 쓴 요청서다 — 다음 update-all 이 그 패치를 stash 로 쓸어 간다.

## 반영 표
| § | 무엇 | 어디 | 비고 |
|---|---|---|---|
| 1 | `SAML_SEND_NAMEID_POLICY`(기본 참) → `auth.login(set_nameid_policy=…)` | `config.py` · `saml_provider.py` | 요청 diff 그대로(설정 이름 같음 — 박스 패치가 그대로 갈음) |
| 2 | `SAML_ADVERTISE_SLO`(기본 참) — 끄면 SP 메타데이터에서 SingleLogoutService 블록을 **통째로** 뺀다 | `config.py` · `saml_sp.py` | url 만 비우면 빈 주소로 광고된다 |
| — | 정식 SLO·'SSO 까지 로그아웃' 링크 | 요청 없음 | 요청자가 별건으로 |

## 시험
`backend/tests/test_saml_adfs_shape.py` — 로그인 리다이렉트의 AuthnRequest 를 디코드해 NameIDPolicy 유무와 Destination·ACS·Issuer 동일성을,
SP 메타데이터의 SingleLogoutService 유무와 유효성을 본다. 둘 다 끈 채로 실제 서명 Assertion 로그인이 된다.
