# 로그인 업데이트 안내 팝업

사용자가 로그인하면 **아직 못 본 업데이트**를 한 번 띄운다. 다 봤으면 아무것도 안 뜬다.

## 항목 추가하기

`backend/config/changelog.yaml` 맨 위에 한 덩이를 얹는다. **그게 전부다** — 재기동도,
배포도 필요 없다(요청마다 파일 mtime 을 확인한다).

```yaml
entries:
  - date: 2026-09-10
    title: 한 줄 제목
    tag: 챗                      # 챗·심의·연결·배포·수정 이면 배지에 색이 붙는다
    items:
      - "사용자가 겪는 변화를 한 문장으로. **굵게** 가 된다."
```

⚠ **items 는 반드시 큰따옴표로 감싼다.** 따옴표 없이 쓰면 `'/전문가' 로 …` 처럼
작은따옴표로 시작하는 줄이 YAML 스칼라로 열려 **파일 전체가 파싱에 실패한다.** 그러면
팝업이 조용히 안 뜬다. `backend/tests/test_changelog.py` 가 배포되는 파일을 실제로
파싱해 보므로, 깨뜨리면 테스트가 잡는다.

무엇을 쓰나 — 커밋 제목이 아니라 **달라진 것**이다.

| 나쁨 | 좋음 |
|---|---|
| `feat(chat): AgentCatalogBlock 추가` | `'/전문가' 로 찾은 사람을 그 자리에서 바로 고를 수 있습니다.` |
| 내부 모듈·파일 이름 | 화면에서 보이는 이름(칸·버튼·메뉴) |

## 동작

- 화면은 사용자별로 `hwax.changelog.seen.<이메일>` 에 **마지막으로 본 날짜**를 적어 둔다.
  다음 로그인에 `GET /changelog?since=<그 날짜>` 로 물어 그 뒤 항목만 받는다.
- 닫을 때 적는 것은 **전체의 최신 날짜**(`latest`)다. 받아온 것 중 최신이 아니다 —
  한 번에 5건(`DEFAULT_LIMIT`)까지만 주므로, 잘려 나간 옛 항목이 다음에 또 뜨면 안 된다.
- 처음 로그인한 사람(기록 없음)에게는 최신 5건만 준다. 이력을 통째로 쏟지 않는다.
- 한 탭에서 한 번만 뜬다. `AppShell` 은 라우트마다 다시 마운트되므로, 이 플래그가 없으면
  닫자마자 페이지를 옮길 때 또 뜬다.
- 저장이 막힌 브라우저(사생활 모드 등)에서도 팝업은 정상 동작한다 — 탭마다 한 번 뜬다.

## 파일

| 무엇 | 어디 |
|---|---|
| 항목 원본 | `backend/config/changelog.yaml` |
| 읽기·필터 + `GET /changelog` | `backend/app/changelog.py` |
| 팝업 | `frontend/src/components/layout/ChangelogPopup.tsx` (`AppShell` 에서 그린다) |
| 조회 | `frontend/src/api/changelog.api.ts` |
| 스타일 | `frontend/src/styles/changelog.css` |
| 테스트 | `backend/tests/test_changelog.py` (13건) |
