# 과제 인사이트 — 박스에서 켜기 · 확인(사람 몫, cae00 · dev 공통)

> 계획 [PLAN.md](PLAN.md) · 결정 [context-notes.md](context-notes.md)(PG-53 ~) · 꼴 [contracts.md](contracts.md) §11.
> 대조 시점 — 포털 가지 `wt1122/insight-m5`(11-22), Report Archive 사본 v0.186.3(`b552f09`). 박스의 지금 상태는 적지 않는다 — 그때 본다.

## 1. RA 투영(M5) — 기본 꺼짐

무엇 — 주인이 '과제 인사이트' 화면에서 조직에 연 확인 카드의 'RA 과제 객체에 달기' 를 누르면 그 카드의 RA 보고서에 SP 과제 객체 태그가 하나
달린다. 그 사람의 RA 연결로만 부른다(위임 또는 '외부 연결' 등록 토큰). 관리자 토큰 · 서비스 자격은 쓰지 않는다(사용자 결정 11-21 L21-6 ③ — 관리자
토큰 사용은 승인되지 않았다). 포털은 스위치를 꺼 둔 채 올라간다(`insight_ra_project` 기본 False).

### 1.1 켜기 전에 볼 것

1. **RA 의 SP 받기가 과제를 싣고 있는가.** RA 가 v0.175 이상이고(SP 받기) 관리 화면 '데이터소스' 의 SP 코어 소스에 `plm_task` 를 받을 축이 매핑돼 있고
   받기가 돈 적이 있어야 한다. RA 에서 과제 객체 하나를 열어 code 가 SP 과제 key 인지 본다 — 투영은 code 가 key 와 글자 그대로 같은 객체만 찾는다.
   key 가 64자를 넘는 과제는 RA 가 code 를 비워 두므로 투영되지 않는다.
2. **포털이 RA 를 그 사람 명의로 부를 수 있는가.** `/보고서` 저장 · 보고서에 그림 넣기가 되는 박스면 된다(같은 함수 하나 — `_ra_user_token`).
3. **같은 code 의 객체가 여럿인 과제는 투영되지 않는다.** 사람이 손으로 만든 사본이나 다른 축에 같은 code 가 있으면 화면이 그 까닭을 말한다 — RA
   관리자가 합치거나 code 를 고친다(포털은 객체를 고치지 않는다).
4. **화면 판.** 단추는 이 판의 `frontend/dist` 가 실린 뒤에 보인다 — cae00 은 Drive 의 빌드를 받는다(`docs/cae00-deploy-guide.md`, cae00 에서
   `pnpm build` 를 돌리지 않는다).

### 1.2 켜기

- `backend/.env` 에 `INSIGHT_RA_PROJECT=true` 를 적고 포털만 다시 띄운다.

```bash
apptainer instance stop hwax_portal && ./infra/scripts/start.sh
```

### 1.3 확인

1. 화면 — '과제 인사이트' 의 내 카드에서 조직에 연 확인 카드(범위 '조직' 하나 — 플랫폼 권한이 붙은 카드는 아니다)에 'RA 과제 객체에 달기' 가
   보인다. 누르면 확인 창이 뜨고, 달면 카드에 'RA 과제 객체에 달림 — <객체 이름>(#<id>) · 보고서 #<번호>' 줄이 선다. 다시 눌러도 RA 를 다시 부르지
   않는다.
2. RA — 그 과제 객체의 화면에서 관련 보고서에 그 심의 보고서가 선다(그 보고서를 볼 수 있는 사람에게만 — 보고서의 공개 범위는 바뀌지 않는다).
3. 감사 — 포털 감사 DB 의 `insight_ra_projected`(ok 는 보고서 · 객체 번호, failed 는 오류 낱말만).
4. 거절 낱말 — `ra_no_task_object`(code 가 key 인 객체가 없다 — SP 받기 꺼짐 · 다음 받기 전 · SP 에서 지워짐) · `ra_task_object_ambiguous`(여럿) ·
   `ra_search_truncated`(key 를 담은 객체가 많아 다 보지 못했다) · `not_editable`(그 보고서의 주인 · 편집자가 아니다 — 옛 박스에서 서비스 계정으로
   저장된 보고서) · `report_not_found` · `ra_token_rejected` · `ra_unreachable` · `ra_outcome_unknown` · `no_ra_connection`. 앞의 넷은 409 · 403 이고
   원장에 적지 않으므로 고친 뒤 다시 누르면 된다.

### 1.4 거두기 · 끄기

- 카드를 거두면 RA 는 부르지 않는다 — 포털 원장의 표지만 바뀌고 화면이 '태그는 RA 에 남는다 — 보고서 편집 화면에서 손으로 뗀다' 고 알린다(PG-55).
- 끄려면 `INSIGHT_RA_PROJECT` 줄을 지우고 포털만 다시 띄운다 — 창구가 없는 창구와 같은 404 가 되고 화면의 단추 · 줄이 사라진다. RA 에 단 태그와 원장
  줄(`insight_meta` 의 `ra:<카드 id>`)은 그대로다(끄기는 거두지 않는다).
