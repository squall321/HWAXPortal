# 일괄 개명이 **한국어 낱말 속**을 깨뜨린 자국을 찾는다
#
# 2026-09-14 워크벤치 → 절차 개명에서 `런` → `실행` 을 통째로 치환해 흔한 낱말이 깨졌다.
# 12개 파일을 되돌렸다고 **보고했는데** `DeliberatePage.tsx` 하나가 빠졌고, 하필 그 줄이
# 심의 화면의 **예시 질문**이라 사용자 눈에 그대로 보였다. 이틀 뒤 다른 일을 확인하다
# 우연히 발견했다.
#
# 무서운 점은 **아무것도 안 터진다는 것**이다. 타입도 맞고 테스트도 통과하고 화면도
# 그려진다 — 글자만 틀렸다. 사람이 읽기 전엔 아무도 모른다. 그래서 코드가 본다.
#
# 방법 — 규칙(정규식)이 아니라 **실제 낱말에서 깨진 꼴을 만들어** 찾는다. 규칙으로 하면
# `선실행해`·`오실행된다` 같은 멀쩡한 낱말까지 잡아 못 쓴다(처음에 그렇게 짰다가 걸렸다).
# 이 파일에 깨진 문자열을 **적지 않는 것**도 그래서다 — 적으면 자기를 잡는다.
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTS = {".ts", ".tsx", ".py", ".md", ".json", ".yaml", ".yml", ".js", ".css", ".html"}
SKIP = {"node_modules", "dist", ".git", ".venv", "__pycache__", "var", "build", "fixtures"}

# 이 리포 문서·화면에 실제로 나오는, 치환에 걸릴 수 있는 낱말들
WORDS = ("그런", "이런", "저런", "어떤런", "밸런스", "런타임", "런처", "런치",
         "프런트", "런던", "트런케이트", "벤치마크", "워크벤치", "블런트")
# 지금까지 이 리포에서 실제로 돈 일괄 치환
SUBS = (("런", "실행"), ("벤치", "절차"))


def _scars() -> dict[str, str]:
    """깨진 꼴 → 원래 낱말. 문자열을 **여기서 만든다**(소스에 안 적는다)."""
    out = {}
    for w in WORDS:
        for a, b in SUBS:
            if a in w:
                broken = w.replace(a, b)
                if broken != w:
                    out[broken] = w
    return out


def _files():
    for p in ROOT.rglob("*"):
        if p.suffix not in EXTS or not p.is_file():
            continue
        if any(part in SKIP for part in p.parts):
            continue
        yield p


def test_일괄_개명이_낱말_속을_깨뜨린_자국이_없다():
    scars = _scars()
    bad = []
    for p in _files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for broken, orig in scars.items():
                if broken in line:
                    bad.append(f"{p.relative_to(ROOT)}:{n}  '{broken}' → '{orig}' 이어야 한다")
    assert not bad, "일괄 치환이 한국어 낱말 속을 깨뜨렸다:\n  " + "\n  ".join(bad)


def test_검사기가_실제로_그런_줄을_잡는다():
    """빈 목록을 훑고 통과하는 사고를 막는다 — 위 테스트의 안전장치다."""
    scars = _scars()
    assert len(scars) >= 10, f"찾을 꼴이 {len(scars)}개뿐이다 — 낱말 목록이 비었나"
    # 실제 사고 문자열을 런타임에 만들어 확인한다
    real = "리플로우 warpage 산포를 줄이려면 대칭 적층과 동박 " + "밸런스".replace("런", "실행") + " 중"
    assert any(b in real for b in scars), "실제로 났던 사고 문자열을 못 잡는다"
    # 멀쩡한 낱말은 안 잡아야 한다 — 이것 때문에 정규식판을 버렸다
    for ok in ("이 실행을 다시 돌린다", "실행 이력이 절차에 묶인다", "재실행 경로",
               "선실행해 두면", "오실행된다", "절차를 저장한다"):
        assert not any(b in ok for b in scars), f"멀쩡한 문장을 잡는다: {ok}"


def test_스캔_대상이_실제로_있다():
    """`_scars()` 는 가드가 있는데 `_files()` 는 없었다 — SKIP·EXTS 를 잘못 건드리거나
    ROOT 가 밀리면 **0개를 훑고 통과**한다. 초록인데 아무것도 안 지키는 상태다."""
    n = len(list(_files()))
    assert n > 300, f"훑을 파일이 {n}개뿐이다 — 대상 선정이 깨졌다"
