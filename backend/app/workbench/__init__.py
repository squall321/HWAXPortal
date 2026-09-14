"""워크벤치 — 업무 절차 인벤토리. 도구를 한 단계씩 돌린 기록을 레시피로 굳혀 재생한다.

계획은 docs/workbench/PLAN.md, 정본 예제는 docs/workbench/recipes.md.

이 모듈은 **포털 안의 격리 모듈**이다 — 챗·심의와 자원을 공유하지 않는다
(자기 세마포어·자기 httpx·자기 sqlite). 자세한 이유는 context-notes W-10.
"""
