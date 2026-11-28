# 받은 편지함 · 요청 폴더 server-setup 의 명령이 운영 박스에서 도는 꼴인가 — sqlite3 CLI · HEAXHub 옛 앱 데이터 자리를 쓰지 않는다(docs/request-1125 HP-61)
"""왜 — 운영 박스에는 sqlite3 CLI 가 없어 `sqlite3 -readonly` 가 돌지 않고, HEAXHub 리포 안의 옛 앱 데이터 자리는 낡은 사본이라(실제는 HWAX_DATA_ROOT 아래
appdata/<앱>) 명령이 조용히 낡은 값으로 답했다(MaterialTwin 7.2 GB 옛 사본). 꼴은 받은 편지함 README 의 '명령 꼴' 절이다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAD = ("sqlite3 -readonly", "var/app_data")


def test_받은_편지함과_server_setup_에_옛_꼴이_없다():
    files = sorted((ROOT / "docs/cae00-inbox").glob("*.md")) + sorted((ROOT / "docs").glob("request-*/server-setup.md"))
    hits = [f"{f.relative_to(ROOT)}:{i}" for f in files
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1) if any(b in line for b in BAD)]
    assert not hits, "옛 꼴 — README '명령 꼴' 대로 ${HWAX_DATA_ROOT:-/data}/appdata/<앱> · roq(python mode=ro) 로: " + ", ".join(hits)


def test_README_의_roq_는_읽기_전용으로_연다():
    s = (ROOT / "docs/cae00-inbox/README.md").read_text(encoding="utf-8")
    line = next(l for l in s.splitlines() if l.startswith("roq() {"))
    assert "mode=ro" in line and "uri=True" in line
