#!/usr/bin/env python3
# db-sync 본체(D0: 읽기 전용) — 레지스트리(services.yaml data:)와 동기화 원장을 읽어 상태·키 지문·manifest 검증을 낸다.
"""
verbs
  status [svc]           서비스×클래스: kind · sync 모드 · 원장 last-applied(없으면 '-')
  keys-check [svc]       keys_with 가 가리키는 키 파일의 sha256 앞 12자 — 원문은 어떤 경우에도 출력하지 않는다
  verify <manifest.json> manifest.files{path: sha256} 전수 검증(rc 0/1)

원장 위치: ${HWAX_DATA_ROOT:-/data}/hwax/state/db-sync/  — 이 디렉터리 생성이 D0 의 유일한 쓰기다(롤백 목록).
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import services as S  # noqa: E402 — 같은 해석기(resolve_dir·_hwax_setting)를 쓴다


def state_dir() -> Path:
    root = S._hwax_setting("HWAX_DATA_ROOT") or "/data"
    d = Path(root) / "hwax" / "state" / "db-sync"
    d.mkdir(parents=True, exist_ok=True)
    (d / "last-applied").mkdir(exist_ok=True)
    return d


def _sha12(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def _items(names: list[str]) -> list[dict]:
    raw = S.yaml.safe_load(S.MANIFEST.read_text(encoding="utf-8")) or {}
    out = [s for s in S.load() if s.get("data") and (not names or s["name"] in names)]
    for n, d in (raw.get("data_only") or {}).items():
        if not names or n in names:
            out.append({"name": n, "data": d, "_data_only": True})
    return out


def cmd_status(names: list[str]) -> int:
    sd = state_dir()
    print(f"  box={S.box_name()} role={S._hwax_setting('HWAX_BOX_ROLE') or '-'} 원장={sd}")
    for s in _items(names):
        print(f"── {s['name']}{'  (data_only)' if s.get('_data_only') else ''}")
        for cname, c in (s["data"].get("classes") or {}).items():
            if not isinstance(c, dict):
                continue
            la = sd / "last-applied" / f"{s['name']}.{cname}"
            last = la.read_text().strip()[:40] if la.exists() else "-"
            print(f"  {cname:<16} {str(c.get('kind', '-')):<9} sync={str(c.get('sync', '-')):<16} last-applied={last}")
    return 0


def cmd_keys_check(names: list[str]) -> int:
    rc = 0
    for s in _items(names):
        data = s["data"]
        sdir = None if s.get("_data_only") else S.resolve_dir(s)
        classes = data.get("classes") or {}
        for cname, c in classes.items():
            if not isinstance(c, dict) or not c.get("keys_with"):
                continue
            for k in c["keys_with"]:
                ref = classes.get(k) or {}
                cur = ref.get("current") or k
                if "#" in str(cur):  # ".env#KEY" — 그 줄의 값만 해시
                    f, key = str(cur).split("#", 1)
                    fp = (sdir / f) if (sdir and not Path(f).is_absolute()) else Path(f)
                    val = None
                    if fp.exists():
                        for ln in fp.read_text(errors="replace").splitlines():
                            if ln.startswith(key + "="):
                                val = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    fpr = hashlib.sha256(val.encode()).hexdigest()[:12] if val else None
                    print(f"  {s['name']}.{cname} ← {k}: {fpr or '없음'}")
                    rc |= 0 if fpr else 1
                    continue
                p = Path(os.path.expandvars(str(cur))).expanduser()
                if not p.is_absolute() and sdir:
                    p = sdir / p
                if p.is_dir():
                    for f in sorted(p.iterdir()):
                        if f.is_file():
                            print(f"  {s['name']}.{cname} ← {k}/{f.name}: {_sha12(f)}")
                elif p.is_file():
                    print(f"  {s['name']}.{cname} ← {k}: {_sha12(p)}")
                else:
                    print(f"  {s['name']}.{cname} ← {k}: 없음 ({p})")
                    rc = 1
    return rc


def cmd_verify(path: str) -> int:
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(m.get("base") or Path(path).parent)
    bad = 0
    for rel, want in (m.get("files") or {}).items():
        f = base / rel
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
        okay = got == want
        bad |= 0 if okay else 1
        print(f"  {'✓' if okay else '✗'} {rel}")
    print("  OK" if not bad else "  sha256 불일치 — 적용 금지")
    return bad


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    verb, rest = argv[1], argv[2:]
    if verb == "status":
        return cmd_status(rest)
    if verb == "keys-check":
        return cmd_keys_check(rest)
    if verb == "verify" and rest:
        return cmd_verify(rest[0])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
