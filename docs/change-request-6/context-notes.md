# 6차 변경 요청 — 결정과 이유

**D-1 `wantNameId` 는 요청 그대로 설정화, 기본 참(2026-10-01).** 반영만으로는 동작이 안 바뀐다. 운영 `.env` 에 `SAML_WANT_NAMEID=false`.
요청서가 확정하지 못한 것 — `wantNameId=False` 이고 NameID 가 없으면 python3-saml 1.16 의 `get_nameid()` 는 **예외 없이 None** 이다
(`response.py` `get_nameid_data`: strict ∧ wantNameId 일 때만 던진다). e2e 시험이 실제 서명 Assertion 으로 고정한다.

**D-2 운영에서 나던 것은 400 이 아니라 500 이었다(2026-10-01).** 요청서는 `get_errors()` 분기의 400 으로 읽었지만, python3-saml 은
`is_valid()` 에서 NameID 부재를 보지 않는다 — 통과한 뒤 `store_valid_response()` 가 `get_nameid()` 를 부르다 **예외**를 던지고, 그것을
아무도 안 잡아 핸들링 없는 500 트레이스백이 됐다(재현 시험을 쓰다 발견). SAMLResponse 없는 POST 도 같은 꼴이었다. 두 라이브러리 예외
(`OneLogin_Saml2_Error`·`OneLogin_Saml2_ValidationError` — 서로 상속 관계 없다)를 400 과 사유로 낸다. 5차 §1-b 와 같은 모양이다.

**D-3 SAML 이메일을 원장 규칙(`norm_email`)으로 정규화(2026-10-01).** NameID 가 없으면 subject 가 곧 Mail 값이다. AD 의 mail 은
'Koo.Park@…' 처럼 대문자가 섞이는데 로컬 계정은 소문자로 저장되고 subject 가 그 이메일이다 — 정규화하지 않으면 같은 사람이 다른 subject 가
되어 대화·PAT·절차가 통째로 안 보인다. 원장·권한은 이미 정규화해 찾으므로(user_store.get) 그쪽은 멀쩡하고 **소유만** 끊긴다 — 그래서 더
안 보인다. 하위 서비스(HEAX Hub·AIDataHub·MXWP·RA·ste·게이트웨이)는 모두 소문자 비교라 이 정규화와 어긋나지 않는다(전수 점검).

**D-4 `NameIDFormat` 은 바꾸지 않는다(2026-10-01).** 요청서가 판단을 넘겼다. emailAddress 를 요구하는 AuthnRequest 를 ADFS 가 받아 준다는
것은 4차 실측으로 확인돼 있고, 첫 운영 로그인 직전에 검증된 요청 모양을 바꾸면 실패 원인이 하나 더 생긴다. ADFS 가 InvalidNameIDPolicy 로
답하는 날 `unspecified` 로 바꾼다.

**D-5 subject 는 정규화한 이메일 그대로 — LoginId 로 바꾸지 않는다(2026-10-01).** 요청자가 개정판에서 철회했고, 전수 점검도 같은 결론이다.
요청서는 'subject 로 조회하는 곳은 PAT 뿐' 이라 했지만 실제로는 더 많다 — 대화(+검색 벡터)·PAT·절차·런·게이트웨이 `save_conversation`·
에이전트 감사가 전부 subject **정확 일치**다. LoginId 로 바꾸면 기존 사용자는 첫 SAML 로그인부터 그것들이 빈 화면이고, 옛 PAT 은 옛 subject
로 계속 써서 한 사람이 둘로 갈린다(옮기는 도구 없음, 서명된 옛 PAT 은 못 고친다). 반대로 하위 서비스 9곳은 전부 소문자 이메일로 사람을
찾아 sub 를 안 본다 — LoginId 로 바꿔도 하위에서 얻는 안정성이 없다. 이메일이 바뀌는 사람(개명·전배)은 어느 쪽이든 끊기며, 그때는 이관이
따로 필요하다. 참고 — dev 박스는 `AUTH_PROVIDER=oidc` 라 subject 가 OIDC `sub` 다(cae00 과 다르다).

**D-6 이름 Claim 이 없어도 견딘다 — 고치지 않았다(2026-10-01).** 깨지는 곳 없음(전수 점검). 포털 화면 인사말이 이름 없이 나오고(참·거짓
검사로 가린다), 세션·`/auth/me` 는 `display_name: null` 을 그대로 나른다. 하위 서비스는 기존 사용자의 저장된 이름을 유지하고, 새로 만드는
계정만 이메일 앞부분을 이름으로 쓴다(NOT NULL 충족). ste 의 퍼센트 인코딩 이름 자가 치유(5차)는 이름이 들어올 때만 돌아 운영에서는 안
돈다. 원장 이름으로 채우는 대안(세 줄)은 요청 범위 밖이라 넣지 않았다 — 요청하면 넣는다.

**D-7 그룹 Claim 이 없어도 권한은 안 닫힌다 — 요청자 정정이 맞다(2026-10-01).** 권한은 매 요청 이메일 키 원장에서 다시 계산한다.
SAML groups 는 관리자 판정에만 쓰이고 원장 groups 도 함께 본다. 원장에 없는 첫 SSO 사용자는 `note_sso_login` 이 active·groups [] 로 만든다 →
기본 권한(일반 챗). 다만 **API 로 SSO 전용 사용자를 관리자로 만드는 길은 없다** — `approve` 는 pending 행만, `set_groups` 는 호출부가 없다.
소속·개별 허가는 `PATCH /auth/access/users/{email}` 로 active 행에도 준다. 기존 로컬 관리자는 같은 이메일 행이라 그대로 관리자다.
