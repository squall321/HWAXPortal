#!/usr/bin/env python3
# 정본 허브가 exact 로 확인한 이름으로 사전을 지어 AIDataHub 에 넘겨 지식카드를 객체에 잇는 박스 명령(docs/expert-ontology 6.3 — 허브가 있는 박스에서 돈다)
"""카드 ↔ 허브 객체 잇기 — 허브 읽기 둘과 AIDataHub 의 박스 명령 하나.

하는 일(docs/expert-ontology/PLAN.md 6.3 — 사용자 결정 EO-6 · EO-8)
  1. 정본 허브(core_vocab.json 의 canonical)에서 타입마다 `objects_list` 로 객체의 이름 · 키 · 별칭을 받는다.
  2. 그 이름들을 `objects_resolve_many` 에 물어 **exact 이고 키가 있는 이름만** 사전에 남긴다(candidates · none 은 세기만 — OF-14 · EO-4).
  3. 사전 파일(`{hub, dict_version, entries[{type_slug, key, term}]}`)을 박스 자리에 0600 으로 두고 AIDataHub
     `deploy/apptainer/onto.sh bind` 에 넘긴다 — 맞추기 · 쓰기는 AIDataHub 가 한다(카드 낱말 · 제목 · 요약 · 절, 그 허브의 연결을 통째로 다시 쓴다).
  4. 타입별 · 문서 종류별 수를 낸다. 사전 파일은 끝나면 지운다(`--keep-dict` 면 둔다 — 사내 객체 이름이 들어 있다).

허브에서 부르는 도구는 읽기 둘(`objects_list` · `objects_resolve_many`)뿐이고 그 밖은 부르기 전에 거절한다. 허브 자격(PAT)은 이 명령만 쥔다 —
AIDataHub 는 게이트웨이를 모른다. LLM 은 부르지 않는다. 같은 허브 · 같은 카드면 같은 연결이 나온다.

쓰는 법(허브가 있는 박스 — 리포 루트에서, 게이트웨이와 같은 파이썬)
  export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT>     # 그 사람의 권한으로 허브를 읽는다
  $PY infra/scripts/card-entity-bind.py --dry-run             # 사전만 짓고 수를 본다(AIDataHub 를 부르지 않는다)
  $PY infra/scripts/card-entity-bind.py                       # 잇는다 — 결과는 infra/.state/card-entity-bind/<시각>/summary.json
  $PY infra/scripts/card-entity-bind.py --only-types part     # 그 타입만 다시 잇는다 — 다른 타입 연결은 그대로(docs/request-1125 HPO-2)

타입 일부만 잇기(--only-types, 또는 기본 타입보다 적은 --types)는 AIDataHub 의 잇기가 사전에 든 타입의 연결만 다시 쓰는 판(AIDataHub AD-22 —
답에 type_counts)에서만 돈다. 앞 판은 그 허브의 연결을 타입과 상관없이 통째로 다시 써서, 한 타입만 주면 다른 타입 연결(11-23 345,344줄)이 지워진다 —
그 판이면 「다른 타입 연결이 지워진다」 를 찍고 잇기 전에 멈춘다(끝 코드 2). 요약에 타입별 전후 연결 수와 연결이 0 인 타입의 까닭(HPO-3)을 싣는다.

끝 코드 — 0 이었다 · 2 준비 실패(mcp 모듈 · PAT · 허브 도구 · AIDataHub 명령이 없다 — 까닭을 찍는다) · 3 이었지만 실패한 타입 · 호출이 있다 ·
4 사전이 비어 잇지 않았다(연결은 그대로 둔다) · 5 AIDataHub 명령이 실패했다(쓴 것이 없다).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BIND_VERSION = "bind-1"
HUB_TOOLS = ("objects_list", "objects_resolve_many")
# AIDataHub 잇기가 사전에 든 타입의 연결만 다시 쓰는 판의 표지 — 그 판의 답 칸 이름(AIDataHub AD-22). onto.sh 는 리포 소스(api.scripts.onto)로 돈다
PER_TYPE_MARK = "type_counts"


def per_type_bind(aidh: Path) -> bool:
    """이 AIDataHub 의 잇기가 타입별로 다시 쓰는가(AD-22) — 리포 소스에 그 판의 답 칸이 있는가로 본다(onto.sh 가 그 소스로 돈다)."""
    try:
        return PER_TYPE_MARK in (aidh / "api_server" / "src" / "api" / "services" / "onto_svc.py").read_text(encoding="utf-8")
    except OSError:
        return False


def zero_reasons(report: dict, entries: list[dict], bind: dict | None) -> dict[str, str]:
    """연결이 0 인 타입마다 까닭(HPO-3) — 허브 쪽(객체 · exact)인지, 사전 낱말이 다 걸러졌는지, 카드 글에 그 이름이 없는지. 수만 쓴다."""
    terms = Counter(e["type_slug"] for e in entries)
    by_type = (bind or {}).get("links_by_type") or {}
    scope = (bind or {}).get("types")                 # AD-22 판 — 맞출 낱말이 남아 다시 쓴 타입
    out: dict[str, str] = {}
    for t, info in report.items():
        if by_type.get(t):
            continue
        v = info.get("verdicts") or {}
        if info.get("problem") and not info.get("objects"):
            why = f"허브에서 받지 못했다 — {info['problem']}"
        elif not info.get("objects"):
            why = "허브에 그 타입의 객체가 없다"
        elif not v.get("exact"):
            why = "허브가 이름을 하나도 exact 로 확인하지 못했다(" + " · ".join(f"{k} {n}" for k, n in v.items()) + ")"
        elif not bind or not bind.get("written"):
            continue                                   # 잇지 않았다(--dry-run · 실패) — 0 은 까닭이 아니다
        elif isinstance(scope, list) and t not in scope:
            why = f"사전 낱말 {terms.get(t, 0)}개가 AIDataHub 규칙에서 다 걸러졌다(짧음 · 뺄 낱말 · 겹침) — 그 타입 연결은 다시 쓰지 않았다"
        else:
            why = f"카드 글(낱말 · 제목 · 요약 · 절)에 사전 낱말 {terms.get(t, 0)}개가 하나도 나오지 않는다"
        out[t] = why
    return out


def _probe():
    """탐침(card-entity-probe.py)의 부르기 · 이름 풀이를 그대로 쓴다 — 같은 게이트웨이 규칙(드러난 이름 · 읽기만)이다."""
    spec = importlib.util.spec_from_file_location("card_entity_probe", Path(__file__).with_name("card-entity-probe.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def exact_keys(reply: Any) -> tuple[dict[str, str], Counter]:
    """objects_resolve_many 답(SP ResolveManyOut — items[]{name, match, object}) → ({물은 이름: 객체 키}, 판정 수).

    exact 여도 키가 없으면 잇지 않는다 — 키는 허브끼리 같지만 id(UUID)는 허브마다 다르다."""
    rows = (reply.get("results") or reply.get("items") or reply.get("rows")) if isinstance(reply, dict) else reply
    out: dict[str, str] = {}
    counts: Counter = Counter()
    for row in rows or []:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        verdict = str(row.get("match") or row.get("verdict") or "").lower() or "unanswered"
        obj = row.get("object") if isinstance(row.get("object"), dict) else {}
        key = obj.get("key")
        if verdict == "exact" and isinstance(key, str) and key.strip():
            out[row["name"]] = key.strip()
            counts["exact"] += 1
        elif verdict == "exact":
            counts["exact_no_key"] += 1
        else:
            counts[verdict] += 1
    return out, counts


async def collect_names(caller, hub: str, type_slug: str, page: int, max_objects: int) -> tuple[list[str], int, str]:
    """한 타입의 객체 이름 · 키 · 별칭(겹침 없이, 받은 차례) · 객체 수 · 문제(없으면 빈 글)."""
    names: dict[str, None] = {}
    objects = 0
    offset = 0
    while offset < max_objects:
        got = await caller(hub, "objects_list", {"type_slug": type_slug, "limit": page, "offset": offset})
        rows = (got.get("items") or got.get("objects") or got.get("rows") or []) if isinstance(got, dict) else got
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            objects += 1
            aliases = row.get("aliases")
            for name in (row.get("label"), row.get("key"), *(aliases if isinstance(aliases, (list, tuple)) else [aliases])):
                if isinstance(name, str) and name.strip():
                    names.setdefault(name.strip())
        if len(rows or []) < page:
            return list(names), objects, ""
        offset += page
    return list(names), objects, f"객체가 {max_objects} 넘게 있어 앞의 것만 받았다(--max-objects)"


async def build_entries(caller, hub: str, types: list[str], *, page: int = 200, chunk: int = 500, max_objects: int = 50000,
                        log=print) -> tuple[list[dict], dict]:
    """타입마다 이름을 받아 exact 만 남긴 사전 줄과 셈(타입 → objects · names · 판정 수 · problem)."""
    entries: list[dict] = []
    report: dict[str, dict] = {}
    for t in types:
        info: dict[str, Any] = {"objects": 0, "names": 0, "verdicts": {}, "problem": ""}
        report[t] = info
        try:
            names, info["objects"], info["problem"] = await collect_names(caller, hub, t, page, max_objects)
        except Exception as exc:  # noqa: BLE001 — 한 타입이 안 돼도 나머지는 받는다
            info["problem"] = f"목록을 받지 못했다 — {str(exc)[:200]}"
            continue
        info["names"] = len(names)
        counts: Counter = Counter()
        for i in range(0, len(names), chunk):
            part = names[i:i + chunk]
            try:
                exact, c = exact_keys(await caller(hub, "objects_resolve_many", {"type_slug": t, "names": part}))
            except Exception as exc:  # noqa: BLE001
                info["problem"] = f"풀이 실패 — {str(exc)[:200]}"
                counts["unanswered"] += len(part)
                continue
            counts.update(c)
            counts["unanswered"] += len(part) - sum(c.values())
            entries.extend({"type_slug": t, "key": exact[name], "term": name} for name in part if name in exact)
        info["verdicts"] = {k: v for k, v in sorted(counts.items()) if v}
        log(f"· {t} — 객체 {info['objects']} · 이름 {info['names']} · 판정 {info['verdicts']}" + (f" · ⚠ {info['problem']}" if info["problem"] else ""))
    return entries, report


def dict_version(entries: list[dict]) -> str:
    """사전의 지문 — 같은 줄이면 차례와 상관없이 같다."""
    body = sorted((e["type_slug"], e["key"], e["term"]) for e in entries)
    return hashlib.sha256(json.dumps(body, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def write_dict(path: Path, hub: str, entries: list[dict]) -> str:
    """사전 파일을 그 사람만 읽게(폴더 0700 · 파일 0600) 쓴다 → 지문. 사내 객체 이름이 들어 있다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    version = dict_version(entries)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"hub": hub, "dict_version": version, "entries": entries}, f, ensure_ascii=False)
    return version


def run_bind(onto_sh: Path, hub: str, dict_path: Path, timeout: int) -> tuple[int, dict | None, str]:
    """AIDataHub 의 박스 명령을 부른다 → (끝 코드, 표준 출력의 JSON, 표준 오류 끝줄들)."""
    proc = subprocess.run(["bash", str(onto_sh), "bind", "--hub", hub, "--dict", str(dict_path)],
                          capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else None
    except ValueError:
        out = None
    return proc.returncode, out if isinstance(out, dict) else None, "\n".join(proc.stderr.strip().splitlines()[-5:])


def summary_text(summary: dict) -> str:
    """수만 — 카드 글 · 객체 이름은 내지 않는다."""
    lines = [f"카드 ↔ 허브 객체 잇기 — 허브 {summary['hub']} · 사전 {summary['dict_version']} · 줄 {summary['entries']}"]
    for t, info in summary["types"].items():
        v = info.get("verdicts") or {}
        lines.append(f"  {t:22s} 객체 {info['objects']:>6} · 이름 {info['names']:>6} · exact {v.get('exact', 0):>6}"
                     + "".join(f" · {k} {n}" for k, n in v.items() if k != "exact")
                     + (f"  ⚠ {info['problem']}" if info.get("problem") else ""))
    bind = summary.get("bind")
    if not bind:
        lines.append("  (잇지 않았다 — " + summary.get("why", "--dry-run") + ")")
        lines += [f"  연결 0 — {t}: {why}" for t, why in (summary.get("zero") or {}).items()]
        return "\n".join(lines)
    if not bind.get("written"):
        lines.append(f"  AIDataHub — 쓰지 않았다: {bind.get('why', '')}")
        return "\n".join(lines)
    lines.append(f"  이어진 카드 {bind['records_linked']} / {bind['records']} · 연결 {bind['links']} · 절 {bind['sections_scanned']}개를 훑음")
    lines.append("  타입별 카드 " + json.dumps(bind.get("records_by_type") or {}, ensure_ascii=False)
                 + " · 객체 " + json.dumps(bind.get("objects_linked") or {}, ensure_ascii=False))
    lines.append("  자리 " + json.dumps(bind.get("links_by_where") or {}, ensure_ascii=False))
    for doc, n in (bind.get("records_by_doc_type") or {}).items():
        share = (n["linked"] / n["total"] * 100) if n.get("total") else 0.0
        lines.append(f"  {doc or '(종류 없음)':24s} {n['linked']:>6} / {n['total']:>6}  {share:5.1f}%")
    d = bind.get("dictionary") or {}
    lines.append(f"  사전 — 쓴 낱말 {d.get('terms', 0)} · 짧아서 뺌 {d.get('short', 0)} · 뺄 낱말 {d.get('stop', 0)} · 겹쳐서 뺌 {d.get('ambiguous', 0)}")
    tc = bind.get("type_counts") or {}
    if tc:                                             # AIDataHub AD-22 판 — 타입별 전후(HPO-2)
        lines.append("  타입별 연결(전 → 후)")
        for t, n in tc.items():
            lines.append(f"    {t:22s} {n.get('before', 0):>7} → {n.get('after', 0):>7}  {'다시 씀' if n.get('rewritten') else '그대로'}")
        if "links_hub_total" in bind:
            lines.append(f"    허브 전체 연결 {bind['links_hub_total']}")
    for t, why in (summary.get("zero") or {}).items():
        lines.append(f"  연결 0 — {t}: {why}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="카드 ↔ 허브 객체 잇기(허브 읽기 둘 + AIDataHub onto.sh bind)")
    ap.add_argument("--gateway", default=os.environ.get("HWAX_GATEWAY_URL", "http://127.0.0.1:9110/mcp"))
    ap.add_argument("--token-env", default="HWAX_GATEWAY_PAT", help="PAT 를 담은 환경변수 이름")
    ap.add_argument("--types", default="", help="허브 타입 슬러그,… (기본 core_vocab types — 그보다 적으면 AIDataHub AD-22 판에서만)")
    ap.add_argument("--only-types", default="", help="이 타입만 다시 잇는다 — 다른 타입 연결은 그대로(AIDataHub 가 타입별로 다시 쓰는 판에서만, HPO-2)")
    ap.add_argument("--aidh", default=str(ROOT.parent / "AIDataHub"), help="AIDataHub 리포 자리(기본 형제 폴더)")
    ap.add_argument("--max-objects", type=int, default=50000, help="타입당 받을 객체 상한")
    ap.add_argument("--sleep", type=float, default=0.05, help="호출 사이 쉼(초)")
    ap.add_argument("--timeout", type=int, default=3000, help="AIDataHub 명령 상한(초) — 절 백만 개에 몇 분")
    ap.add_argument("--dry-run", action="store_true", help="사전만 짓고 수를 본다(AIDataHub 를 부르지 않는다)")
    ap.add_argument("--keep-dict", action="store_true", help="사전 파일을 지우지 않는다(사내 객체 이름이 들어 있다)")
    ap.add_argument("--out", default="", help="결과 폴더(기본 infra/.state/card-entity-bind/<시각>)")
    a = ap.parse_args(argv)
    token = os.environ.get(a.token_env, "").strip()
    if not token:
        print(f"✗ {a.token_env} 가 비었다 — 포털 /auth/pat 로 발급한 PAT 를 그 환경변수에 넣고 다시", file=sys.stderr)
        return 2
    onto_sh = Path(a.aidh) / "deploy" / "apptainer" / "onto.sh"
    if not a.dry_run and not onto_sh.is_file():
        print(f"✗ AIDataHub 의 잇는 명령이 없다 — {onto_sh}(AIDataHub 를 새 판으로 받은 뒤 다시, 자리가 다르면 --aidh)", file=sys.stderr)
        return 2
    probe = _probe()
    vocab = probe.load_core_vocab()
    hub = ((vocab.get("canonical") or {}).get("app") or "").strip()
    defaults = sorted(set((vocab.get("types") or {}).values()))
    given = [t.strip() for t in a.types.split(",") if t.strip()]
    only = [t.strip() for t in a.only_types.split(",") if t.strip()]
    if given and only:
        print("✗ --types 와 --only-types 는 하나만 준다", file=sys.stderr)
        return 2
    types = only or given or defaults
    dropped = sorted(set(defaults) - set(types))
    if (only or dropped) and not a.dry_run and not per_type_bind(Path(a.aidh)):
        print("✗ 다른 타입 연결이 지워진다 — 이 AIDataHub 의 잇기는 그 허브의 연결을 타입과 상관없이 통째로 다시 쓴다(AIDataHub AD-22 앞 판)."
              + (f" 기본 타입 가운데 빠진 것: {', '.join(dropped)}." if dropped else "")
              + " --types 없이 전부 잇거나, AIDataHub 를 타입별로 다시 쓰는 판으로 받은 뒤 다시(--dry-run 은 된다)", file=sys.stderr)
        return 2
    try:
        tmap = probe._tools_map(a.gateway, token)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 /tools-map 을 읽지 못했다 — {exc!r}", file=sys.stderr)
        return 2
    exposed = probe.exposed_names(tmap, {hub: HUB_TOOLS})
    need = [f"{hub}:{t}" for t in HUB_TOOLS if (hub, t) not in exposed]
    if need:
        print(f"✗ 이 게이트웨이에 없는 도구 — {', '.join(need)}. 정본 허브가 없는 박스(dev)에서는 이을 수 없다 — 허브가 있는 박스에서 돌린다",
              file=sys.stderr)
        return 2
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        print(f"✗ mcp 모듈 없음({exc}) — 게이트웨이와 같은 파이썬(venv)으로 돌린다", file=sys.stderr)
        return 2
    out_dir = Path(a.out) if a.out else ROOT / "infra" / ".state" / "card-entity-bind" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    t0 = time.time()

    async def go():
        headers = {"Authorization": f"Bearer {token}", "X-HWAX-Corr": "card-entity-bind"}
        async with streamablehttp_client(a.gateway, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()

                async def call(name: str, args: dict) -> Any:
                    return probe.as_json(await s.call_tool(name, args))
                caller = probe.ReadOnlyCaller(call, exposed, sleep=a.sleep)
                entries, report = await build_entries(caller, hub, types, max_objects=a.max_objects,
                                                      log=lambda m: print(m, file=sys.stderr))
                return entries, report, dict(caller.calls), dict(caller.failures)

    entries, report, calls, failures = asyncio.run(go())
    summary: dict[str, Any] = {"version": BIND_VERSION, "hub": hub, "types": report, "entries": len(entries),
                               "dict_version": dict_version(entries), "calls": calls, "call_failures": failures,
                               "scope": "only-types" if (only or dropped) else "all"}
    rc = 3 if failures or any(i["problem"] for i in report.values()) else 0
    dict_path = out_dir / "dict.json"
    if not entries:
        summary["why"] = "exact 인 이름이 하나도 없다 — 연결은 그대로 둔다"
        rc = 4
    elif a.dry_run:
        summary["why"] = "--dry-run"
    else:
        write_dict(dict_path, hub, entries)
        try:
            code, bound, err = run_bind(onto_sh, hub, dict_path, a.timeout)
        except subprocess.TimeoutExpired:
            code, bound, err = 124, None, f"상한 {a.timeout}초를 넘겼다(--timeout)"
        finally:
            if not a.keep_dict:
                dict_path.unlink(missing_ok=True)
        if code != 0 or not bound:
            print(f"✗ AIDataHub 잇는 명령이 실패했다(rc {code}) — 쓴 것이 없다\n{err}", file=sys.stderr)
            summary["why"] = f"AIDataHub 명령 실패(rc {code})"
            rc = 5
        else:
            summary["bind"] = bound.get("bind") or {}
            summary["mentions"] = bound.get("mentions") or {}
    summary["zero"] = zero_reasons(report, entries, summary.get("bind"))
    summary["seconds"] = round(time.time() - t0, 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    text = summary_text(summary)
    (out_dir / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n결과 — {out_dir}(수만 들어 있다)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
