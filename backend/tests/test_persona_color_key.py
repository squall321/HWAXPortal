# 전문가 색의 입력이 화면마다 같은지 소스로 본다 — colorOf 는 한 곳에만 있고, 부르는 자리는 모두 키를 넘긴다(docs/leftovers-1017 B12)
"""왜 — 색은 키 해시 하나로 정해지는데, 같은 함수라도 입력이 갈리면 같은 사람이 다른 색이 된다. 챗 말풍선 · 고르기 화면 · 입력창
알약은 이름(원래 이름 · 축약형)을, 회의록 · 관계도 · 띵킹은 키를 넣어 왔고, 띵킹은 colorOf 사본을 따로 들고 있었다(사본은 고쳐도
같이 안 고쳐진다). 화면 시험(test_persona_chat_in_browser)은 계산된 색을 보고, 이 시험은 새 자리가 이름을 넣는 것을 빌드 전에 잡는다.

키가 아닌 이름으로 뽑으면 안 되는 까닭 — 이름은 화면마다 다른 꼴로 온다(카탈로그 원래 이름 · shortName 축약형 · 명부에 없으면 키).
심의 발언에는 처음부터 키만 실린다(엔진 deliberation.py 의 `d["persona"] = persona["key"]`, MCP 워크플로 hwax-deliberate.js 의 withKey).
"""
import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"

# 키를 들고 있는데 이름이 `key` 로 끝나지 않는 자리 — 파일마다 무엇이 키인지 적는다. 새 자리는 되도록 `….key` 를 넘긴다.
_KEY_EXPR = {
    "DelibView.tsx": {"t.persona"},          # 발언의 persona — 엔진 · MCP 워크플로가 좌석 키를 싣는다
    "DelibGraph.tsx": {"s", "e.from", "e.to"},  # 좌석 목록(personas 의 키 + 발언의 persona)과 그 사이의 반박
    "ExpertToggle.tsx": {"pinnedAgent"},     # 고른 전문가 — 서버로 가는 pinned_agent(agent_type)
}


def _calls(line: str) -> list[str]:
    """한 줄의 colorOf(…) 인자들 — 괄호 짝을 세어 자른다(`colorOf(nameOf(s.key))` 처럼 안에 호출이 든 인자도 놓치지 않게)."""
    out = []
    for m in re.finditer(r"\bcolorOf\(", line):
        depth, i = 1, m.end()
        while i < len(line) and depth:
            depth += {"(": 1, ")": -1}.get(line[i], 0)
            i += 1
        out.append(line[m.end():i - 1].strip())
    return out


def _sources() -> list[Path]:
    return sorted(p for p in _SRC.rglob("*") if p.suffix in (".ts", ".tsx"))


def test_colorOf_는_personaColor_한_곳에만_있다():
    """사본은 고쳐도 같이 안 고쳐진다 — 띵킹(ThinkView)이 팔레트까지 든 사본을 들고 있었다."""
    defs = [f"{p.relative_to(_SRC)}:{i}" for p in _sources()
            for i, line in enumerate(p.read_text("utf-8").splitlines(), 1)
            if re.search(r"\bfunction colorOf\b|\bconst colorOf\b|\bconst PALETTE\b", line)]
    assert defs == ["components/chat/personaColor.ts:2", "components/chat/personaColor.ts:10"], defs


def test_전문가_아바타와_테두리의_colorOf_인자는_키다():
    calls, bad = [], []
    for p in _sources():
        if p.name == "personaColor.ts":
            continue
        for i, line in enumerate(p.read_text("utf-8").splitlines(), 1):
            for arg in _calls(line):
                calls.append(f"{p.name}:{i}")
                if not (re.fullmatch(r"(?:[A-Za-z_]\w*\.)?key", arg) or arg in _KEY_EXPR.get(p.name, ())):
                    bad.append(f"{p.relative_to(_SRC)}:{i} colorOf({arg})")
    # 비어서 통과하지 않게 — 말풍선 · 회의록 · 관계도 · 띵킹 · 알약 · 고르기 화면 · 조직도 · 심층 보기 · 좌석 고치기가 다 부른다
    assert len(calls) >= 18, calls
    assert not bad, "전문가 색을 키가 아닌 값으로 뽑는다 — 같은 사람이 화면마다 다른 색이 된다:\n" + "\n".join(bad)


def test_말풍선과_띵킹은_공용_모듈을_쓴다():
    for name in ("MessageList.tsx", "ThinkView.tsx", "DelibView.tsx", "ExpertToggle.tsx"):
        src = (_SRC / "components" / "chat" / name).read_text("utf-8")
        assert re.search(r"import \{[^}]*\bcolorOf\b[^}]*\} from '\./personaColor'", src), name
