# 전문가 · 지식카드를 온톨로지에 잇기 — cae00 절차

> 2026-11-21(KST). 계획은 [PLAN.md](PLAN.md) 6절, 결정은 [context-notes.md](context-notes.md) EO-6 ~ EO-14 다.
> 받을 판 — AIDataHub `8c9506c`(main `85c3f2f`) · 에이전트 서버 `f5b5dd8` · `cf22658`(main `804f6a9`) · 포털 `6a7b367c`(셋 다 main 에 `--no-ff` 로 합쳤다).
> 대조 시점 — dev 11-21: 카드 낱말 254,668줄을 13.5초, 절 1,099,593개를 훑어 잇기 233.5초(임시 스키마 시험 — 가짜 사전 360 낱말).

**기본값에서 바뀌는 것은 없다.** 표 넷이 생기고 명령 셋이 들어올 뿐이다. 고르기는 6절의 스위치를 켜야 달라진다.

리포 자리는 박스마다 다르다 — 아래는 포털 리포 루트에서 형제 리포를 `../AIDataHub` 로 부른다. `$PY` 는 게이트웨이와 같은 파이썬(venv)이다.

## 1. 받기 — update-all 한 번

AIDataHub 가 다시 뜰 때 이행 `0033` 이 올라가 표 넷(`record_mentions` · `record_entities` · `onto_terms` · `onto_state`)이 생긴다. 지금 있는 표는
건드리지 않는다. 확인은 아래다.

```bash
bash ../AIDataHub/deploy/apptainer/onto.sh status     # 표가 없으면 끝 코드 3 과 '이행 0033 을 먼저' — AIDataHub 를 다시 띄운다
```

## 2. 카드 낱말 짓기 — 허브가 필요 없다

```bash
bash ../AIDataHub/deploy/apptainer/onto.sh build      # 레코드 6만 장에 15초 안팎. 지문(규칙 · 레코드 수 · 가장 새 수정 시각)이 같으면 건너뛴다
```

`rows` · `by_source`(keyword · property · card) · `by_type`(카드 종류가 말하는 타입의 카드 수)이 나온다. dev 는 254,668줄 · 고장 사례 3,342 · 재료 2,688 이었다.
이 박스에만 있는 카드도 여기서 뽑힌다 — 그래서 이 표는 동기화로 받지 않고 박스에서 짓는다(EO-7).

## 3. 사전만 지어 보기 — 허브 읽기 둘

```bash
export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT>      # 정본 허브를 읽을 수 있는 사람의 것
$PY infra/scripts/card-entity-bind.py --dry-run
```

타입마다 `객체 · 이름 · exact · candidates · none` 수가 나온다. 부르는 도구는 정본 허브의 `objects_list` · `objects_resolve_many` 둘뿐이다.
- 타입은 어휘표 `types` 의 값 여덟이다. 부품처럼 다른 타입을 더하려면 `--types failure_mode,test_item,<슬러그>` 로 준다(11-03 Q2 의 슬러그).
- `exact_no_key` 가 크면 그 타입의 객체에 키가 없다 — 키 없는 객체는 잇지 않는다(id 는 허브마다 다르다).
- 한 타입에서 `⚠ 목록을 받지 못했다` 가 나오면 그 타입만 빠지고 끝 코드가 3 이다.

## 4. 잇기

```bash
$PY infra/scripts/card-entity-bind.py                 # 절 110만 개에 4분 안팎(dev). 상한은 --timeout(기본 3000초)
```

- 사전 파일은 `infra/.state/card-entity-bind/<시각>/dict.json`(0600)에 잠깐 두었다가 지운다. 남기려면 `--keep-dict` — 사내 객체 이름이 들어 있다.
- 그 허브의 연결을 **통째로 다시 쓴다.** 같은 허브 · 같은 카드면 같은 연결이다. exact 인 이름이 하나도 없으면 쓰지 않고 끝 코드 4 다(있던 연결은 그대로).
- AIDataHub 명령이 실패하면 끝 코드 5 이고 쓴 것이 없다(한 트랜잭션).

**돌려받을 것(수만 — `summary.txt` 그대로)** — 타입별 객체 · 이름 · exact 수, 이어진 카드 / 전체, 타입별 이어진 카드 · 객체 수, 자리별(keyword · property ·
title · summary · section) 연결 수, 문서 종류별 이어진 비율. 이 숫자가 계획 3.1 의 관문 G-EO1(범위)을 본다. 객체 이름 · 카드 글은 적지 않는다.

너무 흔한 낱말이 연결을 부풀리면(자리 `section` 이 압도적이고 문서 종류마다 100% 에 가깝다) 뺄 낱말을 규칙 덧씌우기에 더하고 다시 돈다(8절).

## 5. 전문가 ↔ 코어 타입 연결표

```bash
python3 infra/scripts/persona-domains-build.py            # 셈만 — 줄이 서는 도메인과 타입을 보여 준다
python3 infra/scripts/persona-domains-build.py --write    # 박스 덧씌우기 backend/config/core_vocab.local.json 의 personas.domains 에 적는다
```

도메인 카드의 10% 이상이고 20장 이상인 타입만 선다(`--min-share` · `--min-cards`). 추적 파일은 건드리지 않는다. 적은 뒤 에이전트 서버 `/health` 의
`core_vocab.personas` 에서 `domains` 수가 늘고 `dropped` 가 비었는지 본다. 이 칸을 읽는 것은 그림자 기록뿐이라 고르기는 그대로다.

## 6. 고르기에 쓰기 — 스위치(기본 끔)

에이전트 서버 `.env` 에 한 줄을 넣고 다시 띄운다.

```
SEAT_ONTO=shadow      # 추천 줄에 신호만 받고 순위는 그대로 — 먼저 이것으로 본다
SEAT_ONTO=rank        # 질문의 객체에 카드가 이어진 전문가에게 덧점
```

- 닿는 곳은 심의 첫 좌석 · 띵킹 첫 소집 · 심의 미리보기(전문가 고르기 화면) 셋이다. 리스크 심사에는 넘기지 않는다(D-18).
- **게이트웨이가 AIDataHub 의 새 도구 꼴을 알아야 한다.** `recommend_agents` 의 인자에 `onto` 가 보이지 않으면 에이전트 서버는 넘기지 않는다(옛 꼴에
  모르는 인자를 주면 추천이 실패한다). AIDataHub 를 받은 뒤 게이트웨이 · 에이전트 서버를 다시 띄운다 — update-all 이 그 차례로 한다.
- **먹었는지 보는 법** — 에이전트 서버 `/health` 의 `seat_onto` 가 `{mode, sent, skipped, why}` 를 낸다. 좌석을 한 번 고른 뒤 `sent` 가 늘면 넘긴 것이고,
  `skipped` 가 늘고 `why` 가 차 있으면 넘기지 못한 것이다(로그 `agent-server.log` 에도 `[seat-onto] … 넘기지 않는다 — <까닭>` 이 한 번 찍힌다).
- `shadow` 에서 무엇이 달라졌을지 적으려면 `PERSONA_SHADOW_LOG=1` 을 함께 둔다(사용자 허락 범위 — request-1029 server-setup 9절과 같다). 박스 자리
  `<seat-eval>/shadow/` 의 `"u": "onto"` 줄이 자리 · 신호가 붙은 전문가 수 · 들고 나는 전문가 키를 적는다(질문 글 · 시각은 없다).
- 덧점의 무게는 AIDataHub `.env` 의 `AIDH_ONTO_SEAT_WEIGHT`(기본 1.0)다. 다루는 전문가가 많은 객체일수록 덧점이 준다(EO-13).
- 켜느냐는 4절의 수와 `shadow` 기록을 보고 정한다 — 관문 G-EO 는 사람이 본다.

## 7. 다시 잇기 — 박스 훅(선택)

카드나 허브 객체가 바뀌면 3 ~ 4절을 다시 돈다. update-all 끝에 저절로 돌리려면 박스 훅을 하나 둔다(`infra/hooks/post-update.d/README.md`).

```bash
# infra/hooks/post-update.d/50-card-onto.local.sh   (박스 파일 · 권한 600 — PAT 가 들어 있다)
export HWAX_GATEWAY_PAT=<허브를 읽는 PAT>
bash ../AIDataHub/deploy/apptainer/onto.sh build && <게이트웨이 venv 의 python> infra/scripts/card-entity-bind.py
```

PAT 는 수명이 있다 — 만료되면 훅이 끝 코드 2 로 끝나고 끝 요약의 '박스 훅' 줄에 뜬다. 연결은 그대로 남는다.

## 8. 뽑는 규칙 고치기 — 박스 덧씌우기

`../AIDataHub/api_server/config/onto_rules.local.json`(git 이 모른다 · JSON merge patch)에 적는다. 다음 `build` 가 지문이 바뀐 것을 보고 다시 짓는다.

```json
{
  "card_types": {"expert_knowledge_card": {"type": {"design-rule": ["criterion"], "data": ["test_item"]}}},
  "stop": ["faq", "checklist", "boundary", "standard", "data", "design-rule", "failure", "scope", "standard-summary",
           "delegation", "failure-case", "rule", "concept", "open-observation", "tradeoff", "<이 박스에서 너무 흔한 낱말>"]
}
```

- `card_types` 는 카드 종류 · 티어 → 코어 타입이다. 기본값은 뜻이 분명한 둘(고장 사례 → `failure_mode`, 재료 카드 → `material_property`)뿐이다(EO-11).
  허브의 확장 타입 뜻을 본 사람이 더한다. 이 대응은 연결을 막지 않고 5절의 셈에만 쓰인다.
- `stop` 은 목록째 바뀐다(merge patch 는 목록을 합치지 않는다) — 기본 낱말을 함께 적는다.

## 9. 되돌리기

| 무엇 | 어떻게 |
|---|---|
| 고르기 | 에이전트 서버 `.env` 의 `SEAT_ONTO` 줄을 지우고 다시 띄운다 |
| 연결표 | `core_vocab.local.json` 의 `personas.domains` 를 지운다 |
| 연결 · 낱말 | 그대로 두어도 읽는 곳이 없다. 비우려면 AIDataHub DB 에서 `TRUNCATE record_entities, onto_terms, record_mentions; DELETE FROM onto_state;` |
| 표까지 | `alembic downgrade 0032`(AIDataHub `api_server`) — 그 뒤 옛 코드로 돌려도 된다 |

DB 를 dev 덤프로 통째로 되살리면(`import-from-drive.sh`) 이 표들도 dev 것으로 바뀐다 — 연결이 비니 2 ~ 4절을 다시 돈다. 조각 동기화 · 병합은 이 표를
건드리지 않는다.
