# 서버(cae00)에서 할 일 — 리스크 심사 앱 사람 자격(SSO 로 들어온 사람의 PAT 가 저절로)

> 대상: cae00 운영자 · **대조 시점 2026-10-14** · 보낸 쪽: dev(이 리포 `docs/risk-credentials/`).
> 반영되는 커밋 — HWAXRisk `3aea93b`(리스크 앱 SIF, M2 카드 대조 포함·스키마 v4 — 반대 검토 3라운드까지) · HWAXPortal `f4aced3` 이후 · HWAXMcpGateway `f8e7920`.
> dev 에서 같은 커밋으로 세 구성 요소를 다시 띄워 §3 의 ①②④⑤ 를 확인했다(③ 은 cae00 의 키 상태라 dev 와 다르다).
> 리스크 앱 SIF 는 10-14 Drive `latest/` 에 올렸다 — `hwax-risk.sif.hash` 앞 8자 `5896e0cd`(cae00 `--check` 가 이 값과 맞으면 된다).
> (10-15 덧붙임) 보안 핫픽스 `12130f9`(남의 대상으로 등록부 병합을 부르던 길 — 없는 대상과 같은 404)를 얹은 SIF 로 바꿔 올렸다 — 이제 앞 8자는 `e7b78675` 다. 위 값과 다르면 이 값과 맞는지 본다.
> 명령은 각 리포 루트에서 돈다(cae00 은 `~/Projects/<Repo>`). 이 박스의 지금 상태는 이 문서가 알지 못한다 — 확인마다 재는 명령을 적었다.

## 0. 한눈에

요청서(2026-10-14 R1~R5)의 반영이다. 사람이 할 일은 돌리기 전 확인 하나, `update-all` 과 리스크 앱 SIF 맞추기, `cred.key` 옮기기, 돌린 뒤 확인이다.

달라지는 것.
- **Claude 로 리스크 앱을 부르면 그 사람의 포털 PAT 가 저절로 등록·갱신된다.** 게이트웨이가 호출자 본인의 PAT 로 포털에서 더 좁은 PAT(이름 `hwax-risk`, 읽기, 최대 90일·원 PAT 수명 이하)를 바꿔 받아 앱에 넘긴다. 포털 토큰 화면에 '교환으로 생김' 표지로 보인다.
- **사람이 시작한 패널 잡도 서비스 계정으로 내려가지 않는다.** 그 사람(또는 과제 owner)의 PAT 가 없으면 멈추고 까닭과 등록 길을 말한다(카드 대조와 같다).
- **Claude 로 캡처해도 StepForge REST 를 그 사람 PAT 로 읽는다**(게이트웨이 `step-forge` 다리). 그 PAT 에 `step-forge` 청중이 있어야 한다(§4).
- **RA 로 아직 보내지 않은 일이 '반영 안 됨 — 보내는 쪽이 아직 없다(M4)' 로 보인다.** RA 쓰기 자체는 M4 다.
- **설정 화면 '이 박스' 가 까닭별로 말한다.** 필수 키는 `HWAXRISK_CRED_KEY` 하나다. 나머지는 없으면 무엇이 닫히는지만 알린다.
- **리스크 앱 DB 가 스키마 v4 로 오른다**(M2 카드 대조). 새 SIF 가 처음 뜰 때 스스로 올리고 직전 사본(`risk_review.db.pre-migrate-v3-*`)을 남긴다.

## 1. 돌리기 전 확인

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 1 | 도는 심의·리스크 잡이 없다 | `./infra/scripts/risk-review-inventory.sh` | `delib_active`·`delib_queued` 가 0, 리스크 잡 `running` 이 없다 |

## 2. 돌리기

```bash
./infra/scripts/update-all.sh            # 포털·게이트웨이 코드 + 게이트웨이 hwax_risk 위임 항목 다시 쓰기(아래 '기대')
./infra/scripts/update-collab.sh         # 리스크 앱 SIF 를 Drive latest 와 맞춘다(요청서의 반영 확인 길)
./infra/scripts/update-collab.sh --check # 리스크 앱 SIF 해시 · 스키마
```

기대.
- update-all 로그에 재프로비저닝 대상으로 `hwax_risk_sso` 가 한 번 잡힌다. 이번 판정은 위임 항목에 `portal_pat_url`·`portal_pat_spec` 이 없어도 잡는다(이미 항목이 있던 박스라도 이번 한 번은 다시 쓴다).
- `--check` 의 리스크 앱 SIF 가 `3aea93b` 판이고 스키마가 4 다.

## 3. 돌린 뒤 확인

| # | 무엇 | 어떻게 | 기대 |
|---|---|---|---|
| ① | 게이트웨이 위임 항목에 새 두 칸 | 아래 명령 A | `portal_pat_url` 이 `…/apps/hwax_risk/api/auth/portal-pat`, `portal_pat_spec` 이 이름 `hwax-risk`·청중 둘·범위 `read`·90 |
| ② | 게이트웨이 기동 경고 없음 | `grep -a "portal_pat_spec 이 없거나" <게이트웨이 리포>/gateway.log \| tail -1` | 아무것도 안 나온다(마지막 기동 뒤) |
| ③ | `cred.key` 폴백을 옮겼다 | 리스크 앱 설정 화면 '이 박스' — 또는 앱 기동 로그의 `박스 자격` 줄 | `cred_key_dev_fallback` 이 없다(없애려면 [M1 절차서 7-1](../risk-review-redesign/server-setup-m1.md)) |
| ④ | 리스크 도구 29종 | `python3 ~/Projects/HWAXRisk/backend/scripts/rr_gateway_check.py` | `판정 0` |
| ⑤ | Claude 길 실호출 | 운영자 Claude 에서 hwax `risk_next_step` 을 한 번 부르고 게이트웨이 감사의 그 줄 `note` 를 본다(아래 명령 B) | 아래 표 |

명령 A(비밀 값은 찍지 않는다 — 게이트웨이 리포 루트에서).

```bash
python3 -c 'import json;e=json.load(open("gateway_config.json"))["heax_registry"]["per_user_sso"]["hwax_risk"];print({k:e.get(k) for k in ("sso_url","portal_pat_url","portal_pat_spec")})'
```

명령 B(게이트웨이 리포 루트에서).

```bash
tail -2000 audit.jsonl | grep -a '"risk_next_step"' | tail -1 | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print(d.get("via"), d.get("mode"), d.get("note"))'
```

⑤ 의 `note` 읽기.

| note | 뜻 | 할 일 |
|---|---|---|
| `portal-pat:registered` | 교환해 등록했다 | 없음. 포털 토큰 화면에 '교환으로 생김' `hwax-risk` 가 하나 생겼다 |
| (없음) | 앱이 PAT 를 바라지 않았다 — 이미 쓸 만한 PAT 가 있다 | 없음 |
| `portal-pat:skipped-aud-unavailable` | 등록된 PAT 에 `step-forge` 가 없어 바꾸려 했으나 Claude 에 넣은 PAT 에도 없다 | §4 — 그 사람이 청중 전부로 PAT 를 새로 발급해 Claude 에 넣는다 |
| `portal-pat:exchange-permission_denied` | 그 사람에게 `feat:api-token` 권한이 없다 | 포털 '내 권한' 에서 요청 → 관리자 승인 |
| `portal-pat:exchange-source_expiring` | Claude 에 넣은 PAT 가 곧 끝난다 | 그 사람이 PAT 를 새로 발급해 Claude 에 넣는다 |
| `portal-pat:exchange-too_many_children` | 그 PAT 로 바꿔 받은 것이 이미 다섯 | 토큰 화면에서 '교환으로 생김' 옛것을 지운다 |
| `portal-pat:skipped-no-spec` · `skipped-bad-spec` | 게이트웨이 위임 항목에 명세가 없다 | ① 이 틀렸다 — `update-all` 을 다시 돌린다 |
| `portal-pat:register-<상태>` | 앱이 거절했다(앱 설정 화면 '자동 등록' 의 마지막 실패에 까닭) | 그 까닭대로 |

## 4. 사용자에게 알릴 것

- Claude 로 리스크 앱을 쓰면 앱 설정에서 PAT 를 손으로 등록하지 않아도 된다. 첫 호출에 저절로 등록되고 만료 7일 전쯤 저절로 바뀐다.
- **Claude 에 넣는 포털 PAT 는 청중을 고르지 않고(전부) 발급한다.** `step-forge` 가 없으면 Claude 로 캡처할 때 StepForge REST 를 못 읽어 G6 이 「모름」으로 막힌다(길잡이가 그렇게 말한다).
- 토큰 화면의 '교환으로 생김 · hwax-risk' 는 리스크 앱이 쓰는 것이다. 지워도 자동 등록이 켜져 있으면 다음 호출에 다시 생긴다 — 멈추려면 리스크 앱 설정의 '자동 등록' 을 끈다(그 스위치는 화면 갱신과 함께 생긴다 — 그 전에는 운영자가 [M1 절차서 7-2](../risk-review-redesign/server-setup-m1.md) 의 명령으로 끈다).
- PAT 가 없는 사람의 패널 잡은 이제 서비스 계정으로 돌지 않고 멈춘다. 그 사람이 Claude 에서 리스크 도구를 한 번 부르거나 웹 설정의 「포털에서 발급해 등록」을 누르면 풀린다.

## 5. 되돌리기

- 리스크 앱 — Drive 의 직전 SIF 로 돌리면 v4 DB 를 옛 SIF 가 열지 못한다. 되돌리려면 직전 사본(`risk_review.db.pre-migrate-v3-*`)으로 DB 도 함께 돌린다(그 뒤의 기록은 잃는다).
- 게이트웨이 자동 등록만 끄기 — 게이트웨이 설정의 `per_user_sso.hwax_risk` 에서 `portal_pat_url` 을 지우고 게이트웨이를 다시 띄운다(교환을 하지 않는다 — 사람은 웹에서 손으로 등록한다). 다음 update-all 이 다시 채우므로 오래 끌 일이면 dev 에 알린다.
