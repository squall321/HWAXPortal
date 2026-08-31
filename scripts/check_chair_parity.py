# 리스크 심사 의장·좌석 상수가 두 엔진(PY deliberation.py / JS hwax-deliberate.js)과 앱 자산에서 바이트 동일한지 검사한다.
"""check_chair_parity.py — risk-review 엔진 상수 파리티 검사.

계획 §0.5.4 가 정한 '두 엔진 바이트 동일' 대상만 본다.

    _CHAIR_ITEMS["risk-review"]      ↔ CHAIR_ITEMS['risk-review']
    _CHAIR_ADVERSARY["risk-review"]  ↔ CHAIR_ADVERSARY['risk-review']   (key·role)
    _RISK_SEAT_CONTRACT              ↔ RISK_SEAT_CONTRACT               ↔ 앱 seat-contract.v1.json 의 contract

기존 8종 의장 템플릿은 문면이 이미 다르므로(선존 차이) 검사 대상이 아니다.

추출은 파싱으로 한다 — PY 는 ast(인접 문자열 암묵 연결을 파서가 접어 준다), JS 는 node 로
중괄호 정합 블록을 평가한다(템플릿 리터럴 때문에 정규식으로는 안전하게 못 뽑는다).

종료 코드
    0  일치(또는 --allow-missing 이고 아직 어느 쪽에도 없음)
    1  불일치 — 어느 쪽이 어떻게 다른지 출력한다
    2  파일·구조를 읽지 못함(경로 오류·문법 변화)
    3  아직 미착수 — 세 곳 모두 risk-review 항목이 없다(엔진 additive 전 상태)

사용 예
    python scripts/check_chair_parity.py
    python scripts/check_chair_parity.py --py ../HWAXAgentServer/deliberation.py \
        --js infra/pipeline/hwax-deliberate.js \
        --contract ../HWAXRisk/backend/app/assets/seat-contract.v1.json
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

CHAIR = "risk-review"
REPO = Path(__file__).resolve().parent.parent          # HWAXPortal
CLAUDE = REPO.parent                                    # ~/claude
DEFAULT_PY = CLAUDE / "HWAXAgentServer" / "deliberation.py"
DEFAULT_JS = REPO / "infra" / "pipeline" / "hwax-deliberate.js"
DEFAULT_CONTRACT = CLAUDE / "HWAXRisk" / "backend" / "app" / "assets" / "seat-contract.v1.json"

# JS 쪽 상수를 JSON 으로 뽑아 오는 추출기. 중괄호 정합으로 블록을 잘라 eval 한다.
_NODE_EXTRACT = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');

function block(name) {
  // `const <name> = {` … 대응 중괄호까지. 문자열·템플릿·주석 안의 중괄호는 세지 않는다.
  const m = new RegExp("(?:^|\\n)\\s*(?:const|let|var)\\s+" + name + "\\s*=\\s*\\{").exec(src);
  if (!m) return null;
  let i = src.indexOf('{', m.index);
  let depth = 0, q = null, tpl = 0, esc = false, line = false, blk = false;
  for (let j = i; j < src.length; j++) {
    const c = src[j], n = src[j + 1];
    if (esc) { esc = false; continue; }
    if (line) { if (c === '\n') line = false; continue; }
    if (blk) { if (c === '*' && n === '/') { blk = false; j++; } continue; }
    if (q) { if (c === '\\') { esc = true; } else if (c === q) { q = null; } continue; }
    if (tpl) {
      if (c === '\\') { esc = true; }
      else if (c === '`') { tpl--; }
      continue;
    }
    if (c === '/' && n === '/') { line = true; j++; continue; }
    if (c === '/' && n === '*') { blk = true; j++; continue; }
    if (c === '"' || c === "'") { q = c; continue; }
    if (c === '`') { tpl++; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return src.slice(i, j + 1); }
  }
  return null;
}

const out = {};
for (const name of ['CHAIR_ITEMS', 'CHAIR_ADVERSARY', 'RISK_SEAT_CONTRACT']) {
  const b = block(name);
  if (b === null) { out[name] = null; continue; }
  try { out[name] = eval('(' + b + ')'); }
  catch (e) { out[name] = { __error__: String(e && e.message || e) }; }
}
process.stdout.write(JSON.stringify(out));
"""


def _fail(code: int, msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def read_py(path: Path) -> dict:
    """deliberation.py 에서 세 상수를 ast 로 뽑는다. 없으면 None 을 담는다."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        _fail(2, f"PY 파싱 실패: {path} — {exc}")
    want = {"_CHAIR_ITEMS": None, "_CHAIR_ADVERSARY": None, "_RISK_SEAT_CONTRACT": None}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in want:
                try:
                    want[target.id] = ast.literal_eval(node.value)
                except ValueError as exc:
                    _fail(2, f"PY {target.id} 는 리터럴이 아니라 값을 뽑을 수 없다 — {exc}")
    return want


def read_js(path: Path) -> dict:
    """hwax-deliberate.js 에서 세 상수를 node 로 뽑는다."""
    if not path.is_file():
        _fail(2, f"JS 파일 없음: {path}")
    try:
        proc = subprocess.run(
            ["node", "-e", _NODE_EXTRACT, str(path)],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except FileNotFoundError:
        _fail(2, "node 를 찾을 수 없다 — JS 상수를 뽑으려면 node 가 필요하다.")
    if proc.returncode != 0:
        _fail(2, f"JS 추출 실패(node exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        _fail(2, f"JS 추출 결과가 JSON 이 아니다 — {exc}")
    for name, value in data.items():
        if isinstance(value, dict) and "__error__" in value:
            _fail(2, f"JS {name} 평가 실패 — {value['__error__']}")
    return data


def read_contract(path: Path) -> dict | None:
    """앱 자산 seat-contract.v1.json 의 contract 사전. 파일이 없으면 None."""
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(2, f"좌석 계약 자산 읽기 실패: {path} — {exc}")
    contract = doc.get("contract")
    if not isinstance(contract, dict):
        _fail(2, f"좌석 계약 자산에 contract 사전이 없다: {path}")
    return contract


def diff_text(label: str, a: str | None, b: str | None, a_name: str, b_name: str) -> list[str]:
    """두 문자열의 첫 어긋난 위치를 사람이 읽을 수 있게 낸다."""
    if a == b:
        return []
    if a is None or b is None:
        return [f"{label}: {a_name}={'있음' if a is not None else '없음'} · {b_name}={'있음' if b is not None else '없음'}"]
    n = min(len(a), len(b))
    i = next((k for k in range(n) if a[k] != b[k]), n)
    return [
        f"{label}: 길이 {a_name}={len(a)} {b_name}={len(b)}, 첫 차이 {i} 번째 문자",
        f"  {a_name}: …{a[max(0, i - 40):i + 40]!r}",
        f"  {b_name}: …{b[max(0, i - 40):i + 40]!r}",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="risk-review 엔진 상수 파리티 검사")
    ap.add_argument("--py", type=Path, default=DEFAULT_PY, help="HWAXAgentServer/deliberation.py")
    ap.add_argument("--js", type=Path, default=DEFAULT_JS, help="infra/pipeline/hwax-deliberate.js")
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT, help="앱 seat-contract.v1.json")
    ap.add_argument("--allow-missing", action="store_true",
                    help="세 곳 모두 risk-review 가 없어도 0 으로 끝낸다(엔진 additive 전 CI 용)")
    args = ap.parse_args()

    if not args.py.is_file():
        _fail(2, f"PY 파일 없음: {args.py}")
    py = read_py(args.py)
    js = read_js(args.js)
    contract = read_contract(args.contract)

    py_items = (py["_CHAIR_ITEMS"] or {}).get(CHAIR)
    js_items = (js.get("CHAIR_ITEMS") or {}).get(CHAIR)
    py_adv = (py["_CHAIR_ADVERSARY"] or {}).get(CHAIR)
    js_adv = (js.get("CHAIR_ADVERSARY") or {}).get(CHAIR)
    py_seat = py["_RISK_SEAT_CONTRACT"]
    js_seat = js.get("RISK_SEAT_CONTRACT")

    present = [x is not None for x in (py_items, js_items, py_adv, js_adv, py_seat, js_seat)]
    if not any(present):
        msg = f"미착수 — 두 엔진 어디에도 '{CHAIR}' 의장 항목·지정석·좌석 계약이 없다(엔진 additive 전)."
        if args.allow_missing:
            print(msg)
            return 0
        print(msg, file=sys.stderr)
        return 3

    problems: list[str] = []
    problems += diff_text(f"의장 항목 CHAIR_ITEMS['{CHAIR}']", py_items, js_items, "PY", "JS")

    if (py_adv is None) != (js_adv is None):
        problems.append(f"지정 반대석: PY={'있음' if py_adv else '없음'} · JS={'있음' if js_adv else '없음'}")
    elif py_adv and js_adv:
        if py_adv.get("key") != js_adv.get("key"):
            problems.append(f"지정 반대석 key: PY={py_adv.get('key')!r} · JS={js_adv.get('key')!r}")
        problems += diff_text("지정 반대석 role", py_adv.get("role"), js_adv.get("role"), "PY", "JS")

    if (py_seat is None) != (js_seat is None):
        problems.append(f"좌석 계약: PY={'있음' if py_seat else '없음'} · JS={'있음' if js_seat else '없음'}")
    elif isinstance(py_seat, dict) and isinstance(js_seat, dict):
        for key in sorted(set(py_seat) | set(js_seat)):
            problems += diff_text(f"좌석 계약 [{key}]", py_seat.get(key), js_seat.get(key), "PY", "JS")
    elif py_seat is not None:
        problems += diff_text("좌석 계약", py_seat, js_seat, "PY", "JS")

    if contract is None:
        print(f"참고: 앱 좌석 계약 자산이 없어 3자 대조는 건너뛴다({args.contract}).")
    elif isinstance(py_seat, dict):
        for key in sorted(set(py_seat) | set(contract)):
            problems += diff_text(f"좌석 계약 [{key}] 엔진↔앱자산", py_seat.get(key), contract.get(key), "PY", "앱")
    elif py_seat is not None:
        print("참고: 엔진 좌석 계약이 사전이 아니라 문자열이라 앱 자산과 키 단위 대조를 건너뛴다.")

    if problems:
        print(f"파리티 불일치 {len(problems)} 건:", file=sys.stderr)
        for line in problems:
            print("  " + line, file=sys.stderr)
        return 1

    seats = len(py_seat) if isinstance(py_seat, dict) else (1 if py_seat else 0)
    print(f"파리티 통과 — 의장 항목·지정 반대석·좌석 계약 {seats} 키가 PY·JS"
          + ("·앱 자산" if contract is not None else "") + " 에서 동일하다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
