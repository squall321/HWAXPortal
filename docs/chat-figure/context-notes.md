# 챗 그림 — 판단 기록

계획은 [PLAN.md](PLAN.md).

---

## D0 (2026-09-09) — 표면이 셋이라 껍데기를 하나로 뒀다

챗 본문에 그림이 나오는 자리가 셋이다(`md-img` 도구 산출 차트 · `md-mermaid` 구조도 ·
`preview-frame` html/svg 미리보기). 표면마다 확대를 따로 만들면 조작감이 갈리므로
`FigureShell` + `Lightbox` 하나를 셋이 공유한다. html 미리보기는 확대해도 격리를 낮추지
않는다 — 라이트박스의 iframe 도 `sandbox="allow-scripts"` 뿐이다.

---

## D1 — 가로로 긴 그림은 '축소'가 아니라 '스크롤'이다

`max-width:100%` 는 2,600px 짜리 차트를 645px 로 눌러 축 라벨을 못 읽게 만든다. 원본이
칼럼보다 1.5배 넘게 넓으면 축소를 포기하고 가로 스크롤로 둔다. 그 판정은 **로드된 뒤에만**
가능하다(`naturalWidth` vs 컨테이너 `clientWidth`).

실측 — 2,600px 원본이 스크롤 가능(`scrollWidth 2600 > clientWidth 645`), 560px 원본은
프레임이 563px 로 딱 맞는다.

---

## D2 — `<figure>` 를 쓰면 안 된다

처음에 `<figure>`/`<figcaption>` 으로 짰다가 걷어냈다. 마크다운 이미지는 `<p>` 안에서
렌더되고, 거기에 블록 요소를 넣으면 유효하지 않은 HTML 이다. 같은 파일의 영상 플레이어가
`<span className="md-video-wrap">` 를 쓰는 이유가 그것이고 주석에도 적혀 있었다.
`InlineMd`(심의 발언 버블)도 같은 렌더러를 타므로 span 이어야 안전하다.

프레임은 `display: table` 로 내용 폭에 맞춘다 — `block` 이면 그림보다 넓게 늘어나 옆에
빈 칸이 생겨 어설프다. 가로로 긴 경우만 `is-wide` 가 다시 `block; width:100%` 로 되돌린다.

---

## D3 — 실제 컴포넌트를 띄워 보고서야 잡힌 결함 셋

CSS 만 정적 HTML 로 확인하다가, 임시 vite 진입점으로 **실제 렌더러**를 띄웠다.
React 의 `validateDOMNesting` 과 콘솔이 바로 셋을 잡았다.

1. **오버레이가 `<p>` 안에 렌더됐다.** `FigureShell` 의 마크업만 span 으로 고쳤지 라이트박스
   자신은 그 자리에 `<div>` 트리로 붙는다. → `createPortal(…, document.body)`.
   포털은 유효성만이 아니라 **위치**도 고친다 — 조상에 `transform` 이 있으면
   `position: fixed` 가 뷰포트가 아니라 그 조상 기준이 된다. 그림 프레임에 호버
   `transform: translateY(-1px)` 이 있으므로 실제로 걸릴 수 있는 함정이었다.
2. **`<p className="lb-hint">` 이 `<p>` 안의 `<p>`** 였다. 포털로 나가며 함께 해소됐고
   의미상으로도 문단이 아니라 `<div>` 로 바꿨다.
3. **휠 `preventDefault` 가 무시됐다.** React 의 `onWheel` 은 루트에 **passive** 로 붙는다
   ("Unable to preventDefault inside passive event listener"). 확대하려고 굴린 휠이 뒤
   문서를 스크롤시킨다. → `addEventListener('wheel', h, { passive: false })` 로 직접 건다.

셋 다 정적 HTML 하네스로는 절대 안 나온다. **CSS 는 정적으로, 동작은 실제 컴포넌트로**
본다는 것이 이번의 교훈이다.

수정 후 재확인 — 콘솔 오류 0건, 오버레이가 `document.body` 직속, 뷰포트 전체를 덮음
(0,0 1696x693 = 화면 크기), Esc 로 닫히고 본문 스크롤 잠금도 복구된다.

---

## D4 — 검증하지 못한 것

**실제 챗 화면에서는 못 봤다.** 포털이 로그인을 요구하고 자격이 없다. 대신 임시 vite
진입점으로 같은 렌더러를 같은 CSS 로 띄워 확인했다(그 진입점은 커밋하지 않았다).
남은 위험은 챗 말풍선 안에서의 여백·정렬 정도다.
