#!/usr/bin/env python3
# AIDataHub 의 전문가 프로필(도메인별 코어 타입 셈)에서 어휘표 personas.domains 의 core_types 줄을 지어 박스 덧씌우기에 적는 명령(docs/expert-ontology 6.4)
"""전문가 ↔ 분야 ↔ 코어 타입 연결표를 카드에서 짓는다 — 손 줄을 쓰지 않는다(design-e5 3.4 · EO-10).

재료는 AIDataHub `deploy/apptainer/onto.sh profile --domains` 다 — 도메인(전문가 키의 첫 마디)마다 타입별로
structural(카드 종류가 말하는 타입의 카드 수) · linked(그 타입의 허브 객체에 이어진 카드 수)를 준다. 한 도메인의 카드 가운데 그 타입 카드가
문턱(--min-share 기본 10% 이고 --min-cards 기본 20장)을 넘으면 그 도메인의 core_types 에 넣는다.

적는 곳은 **박스 덧씌우기**(`backend/config/core_vocab.local.json` — JSON merge patch, git 이 모른다)뿐이다. 추적 파일(`core_vocab.json`)의 도메인 줄은
도메인 검토로 짓는 칸이라(D-E5-3) 이 명령이 건드리지 않는다. 허브에 잇기 전에는 linked 가 0 이라 카드 종류만으로 갈리는 줄(재료 → 물성)만 나온다 —
뜻 있는 표는 `card-entity-bind.py` 로 이은 뒤에 짓는다. 실사용 질문(H) · 평가셋(A-test)은 보지 않는다(누설 규칙 L7).

쓰는 법(리포 루트에서)
  python3 infra/scripts/persona-domains-build.py                 # 셈만 — 적을 줄을 보여 준다
  python3 infra/scripts/persona-domains-build.py --write         # 박스 덧씌우기에 적는다(있는 줄에 타입을 더한다)
  python3 infra/scripts/persona-domains-build.py --write --replace   # 이 명령이 정한 타입으로 바꾼다(다른 칸 areas · apps 는 그대로)

끝 코드 — 0 끝 · 2 준비 실패(프로필을 못 받았다 — 까닭을 찍는다).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOCAB = ROOT / "backend" / "config" / "core_vocab.json"
ORG = ROOT / "frontend" / "src" / "components" / "chat" / "orgTaxonomy.json"
OPERATOR_DOMAIN = "he"


def _patch(a, b):
    if not isinstance(b, dict):
        return b
    out = dict(a) if isinstance(a, dict) else {}
    for k, v in b.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = _patch(out.get(k), v)
    return out


def load_profile(aidh: Path, profile_file: str = "") -> dict:
    """도메인 프로필 — 파일을 주면 그것을, 아니면 AIDataHub 의 박스 명령을 부른다."""
    if profile_file:
        doc = json.loads(Path(profile_file).read_text(encoding="utf-8"))
    else:
        sh = aidh / "deploy" / "apptainer" / "onto.sh"
        if not sh.is_file():
            raise RuntimeError(f"AIDataHub 의 명령이 없다 — {sh}(새 판을 받은 뒤 다시, 자리가 다르면 --aidh)")
        proc = subprocess.run(["bash", str(sh), "profile", "--domains"], capture_output=True, text=True, timeout=600,
                              stdin=subprocess.DEVNULL)
        if proc.returncode != 0:
            raise RuntimeError(f"onto.sh profile 실패(rc {proc.returncode}) — " + " / ".join(proc.stderr.strip().splitlines()[-3:]))
        doc = json.loads(proc.stdout)
    domains = doc.get("domains") if isinstance(doc, dict) else None
    if not isinstance(domains, dict):
        raise RuntimeError("프로필 꼴이 틀렸다 — {domains: {…}} 여야 한다")
    return domains


def pick(domains: dict, *, known_domains: set[str], known_types: set[str], min_share: float, min_cards: int) -> tuple[dict, dict]:
    """도메인 → core_types(문턱을 넘은 타입, 이름순) 와 건너뛴 것의 셈."""
    lines: dict[str, list[str]] = {}
    skipped = {"unknown_domain": [], "operator": 0, "below": 0, "unknown_type": 0}
    for dom in sorted(domains):
        info = domains[dom] if isinstance(domains[dom], dict) else {}
        if dom == OPERATOR_DOMAIN:
            skipped["operator"] += 1
            continue
        if dom not in known_domains:
            skipped["unknown_domain"].append(dom)
            continue
        cards = int(info.get("cards") or 0)
        got = []
        for t, n in sorted((info.get("types") or {}).items()):
            if t not in known_types:
                skipped["unknown_type"] += 1
                continue
            count = max(int((n or {}).get("structural") or 0), int((n or {}).get("linked") or 0))
            if cards and count >= min_cards and count / cards >= min_share:
                got.append(t)
            else:
                skipped["below"] += 1
        if got:
            lines[dom] = got
    return lines, skipped


def merge_overlay(overlay: dict, lines: dict[str, list[str]], *, replace: bool) -> dict:
    """덧씌우기에 줄을 넣는다 — 기본은 있는 타입에 더하고, replace 면 이 명령이 정한 타입으로 바꾼다(areas · apps 는 그대로)."""
    out = json.loads(json.dumps(overlay)) if isinstance(overlay, dict) else {}
    doms = out.setdefault("personas", {}).setdefault("domains", {})
    if replace:
        for dom in list(doms):
            if isinstance(doms[dom], dict) and dom not in lines:
                doms[dom].pop("core_types", None)
                if not doms[dom]:
                    del doms[dom]
    for dom, types in lines.items():
        line = doms.get(dom) if isinstance(doms.get(dom), dict) else {}
        have = [] if replace else [t for t in line.get("core_types") or [] if isinstance(t, str)]
        line["core_types"] = sorted(set(have) | set(types))
        doms[dom] = line
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="카드 프로필에서 personas.domains 의 core_types 를 지어 박스 덧씌우기에 적는다")
    ap.add_argument("--aidh", default=str(ROOT.parent / "AIDataHub"), help="AIDataHub 리포 자리(기본 형제 폴더)")
    ap.add_argument("--profile", default="", help="받아 둔 프로필 파일(JSON) — 없으면 onto.sh profile --domains 를 부른다")
    ap.add_argument("--vocab", default=str(VOCAB), help="어휘표 자리(덧씌우기는 같은 폴더의 core_vocab.local.json)")
    ap.add_argument("--min-share", type=float, default=0.10, help="도메인 카드 가운데 그 타입 카드의 비율 문턱")
    ap.add_argument("--min-cards", type=int, default=20, help="그 타입 카드 수 문턱")
    ap.add_argument("--write", action="store_true", help="박스 덧씌우기에 적는다(없으면 셈만)")
    ap.add_argument("--replace", action="store_true", help="있는 core_types 에 더하지 않고 이 명령이 정한 것으로 바꾼다")
    a = ap.parse_args(argv)
    vocab_path = Path(a.vocab)
    local = vocab_path.with_name("core_vocab.local.json")
    try:
        domains = load_profile(Path(a.aidh), a.profile)
        base = json.loads(vocab_path.read_text(encoding="utf-8"))
        overlay = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
        org = set(json.loads(ORG.read_text(encoding="utf-8"))["domain_label"])
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    types = set((_patch(base, overlay).get("types") or {}).values())
    lines, skipped = pick(domains, known_domains=org, known_types=types, min_share=a.min_share, min_cards=a.min_cards)
    print(f"도메인 {len(domains)} 가운데 줄이 서는 도메인 {len(lines)} — 문턱 {a.min_share:.0%} · {a.min_cards}장")
    for dom, got in lines.items():
        info = domains[dom]
        cells = ", ".join(f"{t}({max(info['types'][t].get('structural', 0), info['types'][t].get('linked', 0))}/{info['cards']})" for t in got)
        print(f"  {dom:10s} {cells}")
    if skipped["unknown_domain"]:
        print(f"  조직도에 없는 도메인 {len(skipped['unknown_domain'])} — {', '.join(skipped['unknown_domain'][:12])}")
    print(f"  문턱 아래 {skipped['below']} · 어휘표에 없는 타입 {skipped['unknown_type']} · 운영자 도메인 {skipped['operator']}")
    if not a.write:
        print("셈만 했다(적지 않았다) — 적으려면 --write")
        return 0
    merged = merge_overlay(overlay, lines, replace=a.replace)
    local.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"적었다 — {local.name}(박스 파일 · personas.domains {len(merged['personas']['domains'])}줄). 에이전트 서버 /health 의 "
          "core_vocab.personas 에서 버린 줄(dropped)이 없는지 본다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
