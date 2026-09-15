

def test_업로드가_중간에_끊겨도_감사가_남는다():
    """각 분기는 도구를 여러 번 부르고 **마지막에** 한 줄을 남긴다. 중간 호출이 502 를
    던지면 그 줄에 못 닿는데, 그 시점에 이미 부작용이 있다 — DynaForge 세션 생성,
    RA 의 pptx 반입, StepForge 파일 첨부. 그러면 남의 앱에는 데이터가 있고 우리 원장에는
    아무것도 없다(= 관측 불가). `judge` 로 바꾸기 전에는 실패가 `created:true` 로 위장돼
    (틀리게라도) 감사가 남았다 — 6차 수정이 만든 구멍이다(7차 감사).
    """
    import inspect

    from app.agent import routes as R

    src = inspect.getsource(R._dispatch_audited)
    assert "except Exception" in src and 'status="failed"' in src
    assert "raise" in src, "남기고 **그대로 올려야** 한다 — 삼키면 502 가 사라진다"
    # 진입점이 실제로 그 래퍼를 지나야 한다 — 함수만 있고 안 꽂히면 아무것도 안 지킨다
    assert "_dispatch_audited(" in inspect.getsource(R.upload_dispatch)
