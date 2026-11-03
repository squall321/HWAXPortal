#!/usr/bin/env python3
# 지식카드 표본이 정본 허브 객체에 얼마나 정확히 이어지는지 재는 읽기 전용 탐침(docs/expert-ontology O0a — cae00 에서 사람이 돌린다)
"""카드 ↔ 허브 객체 연결의 범위를 잰다 — 짓지 않고 세기만 한다.

하는 일(docs/expert-ontology/PLAN.md 2.2 · 3절 O0a, 사용자 결정 EO-2 · EO-4)
  1. 정본 허브(core_vocab.json 의 canonical)에서 타입마다 `objects_list` 로 객체 이름 · 식별자 · 별칭(목록 줄 ObjectOut.aliases)을 받아 사전을 짓는다.
  2. AIDataHub 카드를 문서 종류로 층화해 뽑고(`list_records` 의 total · offset) 제목 · 요약 · 절(`get_record` · `get_record_sections`)을 읽는다.
  3. 사전 낱말을 맞춘다 — NFKC · 대소문자 무시 · 낱말 단위(영문 · 숫자 덩어리와 한글 덩어리), 끝 낱말은 조사를 뗀 꼴도 본다.
  4. 맞춘 이름을 `objects_resolve_many` 로 물어 **exact 만** 이은 것으로 센다(candidates · none 은 세기만 — OF-14).
  5. 타입별 · 문서 종류별 연결 비율, 카드당 수, 흔한 낱말 상위, 이미 있는 칸(과제 코드 · 규격 참조)의 수를 낸다.

읽기만 한다 — 부르는 도구는 아래 READ_TOOLS 다섯뿐이고 그 밖은 부르기 전에 거절한다. 카드 글 · 사람 이름은 내지 않는다(흔한 낱말 상위는 허브 객체 이름이라
보고서 파일에만 — 추적 파일에 옮기지 않는다).

쓰는 법(cae00 — 리포 루트에서, 게이트웨이와 같은 파이썬)
  export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT>     # 그 사람의 권한으로 읽는다(AIDataHub · 정본 허브)
  $PY infra/scripts/card-entity-probe.py                     # 표본 300 · 씨앗 20261103 · 결과는 infra/.state/card-entity-probe/<시각>/
  $PY infra/scripts/card-entity-probe.py --stop stop.txt     # 흔한 낱말을 빼고 다시(한 줄에 하나)

끝 코드 — 0 다 잼 · 2 준비 실패(mcp 모듈 · PAT · 허브 도구가 없다 — 그 까닭을 찍는다) · 3 잰 것은 냈지만 실패한 호출이 있다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[2]
CORE_VOCAB = ROOT / "backend" / "config" / "core_vocab.json"
PROBE_VERSION = "o0a-1"
AIDH_APP = "ai-data-hub"
HUB_TOOLS = ("objects_list", "objects_resolve_many")
AIDH_TOOLS = ("list_records", "get_record", "get_record_sections")
READ_TOOLS = frozenset(HUB_TOOLS + AIDH_TOOLS)
DEFAULT_STRATA = "paper:60,expert_knowledge_card:80,patent:40,material_card:40,standard:40,whitepaper:40"
RESOLVE_CHUNK = 500            # objects_resolve_many 한 번의 상한(SP 도구 설명)
LIST_PAGE = 200
SECTION_PAGE = 50
MAX_NGRAM = 8
TOP_TERMS = 30
# 한국어 조사 · 어미 — 끝 낱말에서만 뗀 꼴을 함께 본다(긴 것부터). 떼고 남은 것이 두 글자 아래면 떼지 않는다.
PARTICLES = tuple(sorted((
    "에서는", "으로는", "에서도", "이라는", "에서", "으로", "에게", "까지", "부터", "처럼", "보다", "이며", "이고", "에는", "에도", "과의", "와의",
    "라는", "이다", "의", "이", "가", "은", "는", "을", "를", "에", "로", "와", "과", "도", "만"), key=len, reverse=True))
_TOKEN = re.compile(r"[0-9a-z]+|[가-힣]+")
_HANGUL = re.compile(r"[가-힣]")


# ── 글 다루기 ─────────────────────────────────────────────────────────────
def tokens(text: str) -> list[str]:
    """NFKC · 대소문자 무시 뒤 영문 · 숫자 덩어리와 한글 덩어리."""
    return _TOKEN.findall(unicodedata.normalize("NFKC", text or "").casefold())


def strip_particle(tok: str) -> str:
    """한글 낱말 끝의 조사 하나를 뗀다 — 남는 것이 두 글자 아래면 그대로."""
    if not _HANGUL.search(tok):
        return tok
    for p in PARTICLES:
        if tok.endswith(p) and len(tok) - len(p) >= 2:
            return tok[: -len(p)]
    return tok


def term_ok(toks: tuple[str, ...], min_hangul: int = 2, min_latin: int = 3) -> bool:
    """사전에 넣을 만한 낱말인가 — 한글이 들면 글자 수 min_hangul 이상, 영문만이면 min_latin 이상, 숫자뿐이면 빼고 너무 긴 꼴(MAX_NGRAM 넘게)도 뺀다."""
    if not toks or len(toks) > MAX_NGRAM:
        return False
    joined = "".join(toks)
    if joined.isdigit():
        return False
    if _HANGUL.search(joined):
        return len(joined) >= min_hangul
    return len(joined) >= min_latin


# ── 사전 ─────────────────────────────────────────────────────────────────
class Dictionary:
    """낱말(토큰 묶음) → {(타입, 허브에 물을 이름)}. 이름은 사전이 받은 그대로(이름 · 식별자 · 별칭)라 풀이가 exact 로 나와야 맞다."""

    def __init__(self, stop: set[str] | None = None, min_hangul: int = 2, min_latin: int = 3):
        self.terms: dict[tuple[str, ...], set[tuple[str, str]]] = defaultdict(set)
        self.stop = {tuple(tokens(s)) for s in (stop or set()) if tokens(s)}
        self.min_hangul, self.min_latin = min_hangul, min_latin
        self.skipped: Counter = Counter()          # 까닭 → 수(short · stop)
        self.objects: Counter = Counter()          # 타입 → 객체 수
        self.with_aliases: Counter = Counter()     # 타입 → 별칭이 하나라도 있는 객체 수
        self._first: set[str] | None = None        # 낱말의 첫 토큰 — 맞추기의 거름(사전이 바뀌면 다시 짓는다)

    def add_object(self, type_slug: str, label: Any, key: Any, aliases: Any = ()) -> None:
        self.objects[type_slug] += 1
        names = [n for n in (label, key) if isinstance(n, str) and n.strip()]
        al = [a for a in (aliases if isinstance(aliases, (list, tuple)) else [aliases]) if isinstance(a, str) and a.strip()]
        if al:
            self.with_aliases[type_slug] += 1
        for name in dict.fromkeys(names + al):
            toks = tuple(tokens(name))
            if toks in self.stop:
                self.skipped["stop"] += 1
                continue
            if not term_ok(toks, self.min_hangul, self.min_latin):
                self.skipped["short"] += 1
                continue
            self.terms[toks].add((type_slug, name.strip()))
            self._first = None

    @property
    def max_n(self) -> int:
        return max((len(t) for t in self.terms), default=0)

    def match(self, text: str) -> dict[tuple[str, ...], int]:
        """글에서 맞은 낱말 → 몇 번. 끝 낱말은 조사를 뗀 꼴도 본다(앞 낱말은 그대로 — 조사는 끝에 붙는다)."""
        toks = tokens(text)
        found: Counter = Counter()
        n_max = self.max_n
        if self._first is None:
            self._first = {t[0] for t in self.terms}
        first = self._first
        for i in range(len(toks)):
            if toks[i] not in first and strip_particle(toks[i]) not in first:
                continue
            for n in range(1, min(n_max, len(toks) - i) + 1):
                head = tuple(toks[i:i + n - 1])
                last = toks[i + n - 1]
                for cand in dict.fromkeys((head + (last,), head + (strip_particle(last),))):
                    if cand in self.terms:
                        found[cand] += 1
        return dict(found)


# ── 표본 ─────────────────────────────────────────────────────────────────
def parse_strata(spec: str) -> list[tuple[str, int]]:
    out = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        name, _, n = part.partition(":")
        if not name or not n.isdigit() or int(n) <= 0:
            raise ValueError(f"층 꼴이 틀렸다 — {part!r}(문서종류:수)")
        out.append((name.strip(), int(n)))
    return out


def sample_offsets(total: int, n: int, seed: int, doc_type: str) -> list[int]:
    """그 층의 offset n 개 — 씨앗과 문서 종류로 정해지는 무작위(같은 씨앗이면 같은 표본). total 이 n 이하면 전부."""
    if total <= 0:
        return []
    if total <= n:
        return list(range(total))
    rng = random.Random(f"{seed}:{doc_type}")
    return sorted(rng.sample(range(total), n))


def card_fields(record: dict) -> dict[str, Any]:
    """이미 있는 칸 — 과제 코드(eng_meta.project) · 규격 참조(card.standard_refs) · 물성 줄 수. 값은 내지 않고 있느냐 · 몇 개냐만."""
    content = record.get("content") if isinstance(record.get("content"), dict) else {}
    eng = content.get("eng_meta") if isinstance(content.get("eng_meta"), dict) else {}
    card = content.get("card") if isinstance(content.get("card"), dict) else {}
    props = content.get("properties")
    project = eng.get("project")
    return {"project": project if isinstance(project, str) and project.strip() else None,
            "standard_refs": len(card.get("standard_refs") or []) if isinstance(card.get("standard_refs"), list) else 0,
            "properties": len(props) if isinstance(props, list) else 0}


# ── 풀이 ─────────────────────────────────────────────────────────────────
def verdicts(reply: Any) -> dict[str, tuple[str, str | None]]:
    """objects_resolve_many 답(SP ResolveManyOut — items[]{name, match, object}) → {물은 이름: (판정, exact 면 객체 키 — 키가 없으면 id)}."""
    rows = reply.get("results") or reply.get("items") or reply.get("rows") if isinstance(reply, dict) else reply
    out: dict[str, tuple[str, str | None]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        verdict = str(row.get("match") or row.get("verdict") or "").lower()
        obj = row.get("object") if isinstance(row.get("object"), dict) else {}
        if isinstance(name, str):
            out[name] = (verdict, (obj.get("key") or obj.get("id")) if verdict == "exact" else None)
    return out


# ── 부르기 ───────────────────────────────────────────────────────────────
class ReadOnlyCaller:
    """원래 이름으로 부른다 — 게이트웨이의 드러난 이름은 /tools-map 으로 찾고, READ_TOOLS 밖의 이름은 부르기 전에 거절한다."""

    def __init__(self, call: Callable[[str, dict], Awaitable[Any]], exposed: dict[tuple[str, str], str], sleep: float = 0.0):
        self._call, self.exposed, self.sleep = call, exposed, sleep
        self.calls: Counter = Counter()
        self.failures: Counter = Counter()

    async def __call__(self, app: str, original: str, args: dict) -> Any:
        if original not in READ_TOOLS:
            raise PermissionError(f"읽기 목록 밖의 도구 — {original}")
        name = self.exposed.get((app, original))
        if not name:
            raise LookupError(f"이 게이트웨이에 {app}:{original} 가 없다")
        self.calls[original] += 1
        try:
            return await self._call(name, args)
        except Exception:
            self.failures[original] += 1
            raise
        finally:
            if self.sleep:
                await asyncio.sleep(self.sleep)


def exposed_names(tools_map: dict, wanted: dict[str, tuple[str, ...]]) -> dict[tuple[str, str], str]:
    """/tools-map 의 map(드러난 이름 → 앱) · orig(드러난 이름 → 원래 이름, 다를 때만)에서 (앱, 원래 이름) → 드러난 이름."""
    m = tools_map.get("map") or {}
    orig = tools_map.get("orig") or {}
    out: dict[tuple[str, str], str] = {}
    for exposed, app in m.items():
        original = orig.get(exposed, exposed)
        if app in wanted and original in wanted[app]:
            out.setdefault((app, original), exposed)
    return out


def load_core_vocab(path: Path = CORE_VOCAB) -> dict:
    """어휘표 + 박스 덧씌우기(core_vocab.local.json — JSON merge patch)."""
    base = json.loads(path.read_text(encoding="utf-8"))
    local = path.with_name("core_vocab.local.json")
    if local.exists():
        def patch(a: Any, b: Any) -> Any:
            if not isinstance(b, dict):
                return b
            out = dict(a) if isinstance(a, dict) else {}
            for k, v in b.items():
                if v is None:
                    out.pop(k, None)
                else:
                    out[k] = patch(out.get(k), v)
            return out
        base = patch(base, json.loads(local.read_text(encoding="utf-8")))
    return base


def as_json(reply: Any) -> Any:
    """도구 답(글 덩어리 하나 또는 여럿)을 JSON 으로 — 여럿이면 목록."""
    texts = [getattr(c, "text", "") for c in getattr(reply, "content", []) if getattr(c, "type", "") == "text"]
    if getattr(reply, "isError", False):
        raise RuntimeError((texts[0] if texts else "도구 오류")[:300])
    if len(texts) == 1:
        return json.loads(texts[0])
    return [json.loads(t) for t in texts]


async def build_dictionary(caller: ReadOnlyCaller, hub: str, types: list[str], dic: Dictionary, max_objects: int) -> dict[str, str]:
    """타입마다 objects_list 를 쪽으로 넘겨 사전을 짓는다. 돌려주는 것은 타입 → 문제(없으면 빈 글)."""
    problems: dict[str, str] = {}
    for t in types:
        offset = 0
        try:
            while offset < max_objects:
                page = await caller(hub, "objects_list", {"type_slug": t, "limit": LIST_PAGE, "offset": offset})
                rows = page.get("items") or page.get("objects") or page.get("rows") or [] if isinstance(page, dict) else page
                for row in rows:
                    dic.add_object(t, row.get("label"), row.get("key"), row.get("aliases") or ())
                if len(rows) < LIST_PAGE:
                    break
                offset += LIST_PAGE
            else:
                problems[t] = f"객체가 {max_objects} 넘게 있어 앞의 것만 사전에 넣었다(--max-objects)"
        except Exception as exc:  # noqa: BLE001 — 한 타입이 안 돼도 나머지는 잰다
            problems[t] = f"목록을 받지 못했다 — {str(exc)[:200]}"
    return problems


async def sample_cards(caller: ReadOnlyCaller, strata: list[tuple[str, int]], seed: int) -> tuple[list[tuple[str, str]], dict[str, int], dict[str, str]]:
    """층마다 total 을 보고 offset 을 뽑아 카드 id 를 받는다 — (문서 종류, id) 목록 · 층 → total · 층 → 문제. 한 층이 안 돼도 나머지는 뽑는다."""
    picked: list[tuple[str, str]] = []
    totals: dict[str, int] = {}
    problems: dict[str, str] = {}
    for doc_type, n in strata:
        try:
            head = await caller(AIDH_APP, "list_records", {"doc_type": doc_type, "limit": 1, "offset": 0})
        except Exception as exc:  # noqa: BLE001
            problems[doc_type] = f"total 을 받지 못했다 — {str(exc)[:200]}"
            continue
        totals[doc_type] = int(head.get("total") or 0)
        missed = 0
        for off in sample_offsets(totals[doc_type], n, seed, doc_type):
            try:
                got = await caller(AIDH_APP, "list_records", {"doc_type": doc_type, "limit": 1, "offset": off})
            except Exception:  # noqa: BLE001
                missed += 1
                continue
            items = got.get("items") or []
            if items and items[0].get("id"):
                picked.append((doc_type, str(items[0]["id"])))
            else:
                missed += 1
        if missed:
            problems[doc_type] = f"offset {missed}개에서 카드를 받지 못했다"
    return picked, totals, problems


async def card_text(caller: ReadOnlyCaller, record_id: str, sections_max: int) -> tuple[dict[str, str], dict[str, Any]]:
    """카드 하나의 글(제목 · 요약 · 절)과 이미 있는 칸."""
    rec = await caller(AIDH_APP, "get_record", {"record_id": record_id})
    parts = {"title": str(rec.get("title") or ""), "summary": str(rec.get("summary") or "")}
    chunks: list[str] = []
    offset = 0
    while offset < sections_max:
        got = await caller(AIDH_APP, "get_record_sections", {"record_id": record_id, "limit": SECTION_PAGE, "offset": offset})
        rows = got if isinstance(got, list) else ([got] if isinstance(got, dict) and "section_id" in got else got.get("sections") or [])
        for r in rows:
            chunks.append(f"{r.get('title') or ''}\n{r.get('content_text') or ''}")
        if len(rows) < SECTION_PAGE:
            break
        offset += SECTION_PAGE
    parts["sections"] = "\n".join(chunks)
    return parts, card_fields(rec)


async def run_probe(caller: ReadOnlyCaller, *, hub: str, types: list[str], strata: list[tuple[str, int]], seed: int,
                    stop: set[str], max_objects: int, sections_max: int, log: Callable[[str], None] = print) -> dict:
    t0 = time.time()
    dic = Dictionary(stop=stop)
    log(f"· 사전 — 허브 {hub} · 타입 {len(types)}")
    dict_problems = await build_dictionary(caller, hub, types, dic, max_objects)
    log(f"· 사전 낱말 {len(dic.terms)} · 객체 {sum(dic.objects.values())} · 뺀 낱말 {dict(dic.skipped)}")
    picked, totals, sample_problems = await sample_cards(caller, strata, seed)
    log(f"· 표본 카드 {len(picked)} — 층 total {totals}")
    per_card: list[dict] = []
    term_cards: Counter = Counter()
    card_failures = 0
    for doc_type, rid in picked:
        try:
            parts, fields = await card_text(caller, rid, sections_max)
        except Exception:  # noqa: BLE001 — 그 카드는 실패로 세고 다음
            card_failures += 1
            continue
        hits: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)
        for field, text in parts.items():
            for term, cnt in dic.match(text).items():
                hits[term][field] = cnt
        for term in hits:
            term_cards[term] += 1
        per_card.append({"doc_type": doc_type, "terms": hits, "fields": fields})
    # 풀이 — 타입마다 맞은 이름을 한 번씩만 묻는다
    asked: dict[str, set[str]] = defaultdict(set)
    for card in per_card:
        for term in card["terms"]:
            for t, name in dic.terms[term]:
                asked[t].add(name)
    verdict_of: dict[tuple[str, str], tuple[str, str | None]] = {}
    resolve_problems: dict[str, str] = {}
    for t, names in asked.items():
        ordered = sorted(names)
        for i in range(0, len(ordered), RESOLVE_CHUNK):
            chunk = ordered[i:i + RESOLVE_CHUNK]
            try:
                got = verdicts(await caller(hub, "objects_resolve_many", {"type_slug": t, "names": chunk}))
            except Exception as exc:  # noqa: BLE001
                resolve_problems[t] = f"풀이 실패 — {str(exc)[:200]}"
                got = {}
            for name in chunk:
                verdict_of[(t, name)] = got.get(name, ("unanswered", None))
    report = summarize(per_card, dic, verdict_of, totals, term_cards)
    report["meta"] = {"version": PROBE_VERSION, "hub": hub, "types": types, "strata": strata, "seed": seed,
                      "sample": len(picked), "read": len(per_card), "card_failures": card_failures, "seconds": round(time.time() - t0, 1),
                      "calls": dict(caller.calls), "call_failures": dict(caller.failures), "dictionary_problems": dict_problems,
                      "resolve_problems": resolve_problems, "sample_problems": sample_problems,
                      "dictionary": {"terms": len(dic.terms), "objects": dict(dic.objects), "objects_with_aliases": dict(dic.with_aliases),
                                     "skipped": dict(dic.skipped)}}
    return report


def summarize(per_card: list[dict], dic: Dictionary, verdict_of: dict, totals: dict, term_cards: Counter) -> dict:
    """타입별 · 문서 종류별 exact 연결 비율 · 카드당 수 · 판정 수 · 흔한 낱말 상위 · 이미 있는 칸."""
    by_type: dict[str, dict] = {}
    types = sorted({t for v in dic.terms.values() for t, _ in v} | set(dic.objects))
    n_cards = len(per_card)
    by_doc = Counter(c["doc_type"] for c in per_card)
    for t in types:
        linked_cards = Counter()
        per_card_links = []
        exact_terms = Counter()
        for card in per_card:
            keys = set()
            for term in card["terms"]:
                for tt, name in dic.terms[term]:
                    if tt != t:
                        continue
                    verdict, key = verdict_of.get((t, name), ("unasked", None))
                    if verdict == "exact" and key:
                        keys.add(key)
                        exact_terms[" ".join(term)] += 1
            if keys:
                linked_cards[card["doc_type"]] += 1
                per_card_links.append(len(keys))
        verdict_counts = Counter(v for (tt, _), (v, _) in verdict_of.items() if tt == t)
        linked = sum(linked_cards.values())
        per_card_links.sort()
        by_type[t] = {
            "objects": dic.objects.get(t, 0),
            "cards_linked": linked, "cards_linked_pct": round(100 * linked / n_cards, 1) if n_cards else 0.0,
            "by_doc_type": {d: {"linked": linked_cards.get(d, 0), "read": by_doc[d],
                                "pct": round(100 * linked_cards.get(d, 0) / by_doc[d], 1) if by_doc[d] else 0.0} for d in sorted(by_doc)},
            "links_per_linked_card": {"median": per_card_links[len(per_card_links) // 2] if per_card_links else 0,
                                      "max": per_card_links[-1] if per_card_links else 0},
            "verdicts": dict(verdict_counts),
            "top_exact_terms": exact_terms.most_common(TOP_TERMS),
        }
    fields = {"project": sum(1 for c in per_card if c["fields"]["project"]),
              "standard_refs": sum(1 for c in per_card if c["fields"]["standard_refs"]),
              "properties": sum(1 for c in per_card if c["fields"]["properties"])}
    any_linked = sum(1 for card in per_card if any(verdict_of.get((t, name), ("", None))[0] == "exact"
                                                       for term in card["terms"] for t, name in dic.terms[term]))
    return {"cards_read": n_cards, "totals": totals, "any_type_linked": any_linked,
            "any_type_linked_pct": round(100 * any_linked / n_cards, 1) if n_cards else 0.0,
            "by_type": by_type, "existing_fields": fields,
            "top_matched_terms": [(" ".join(t), n) for t, n in term_cards.most_common(TOP_TERMS)]}


def summary_text(report: dict) -> str:
    """사람이 읽을 요약 — 수만(카드 글 · 객체 이름은 report.json 에만)."""
    m = report["meta"]
    lines = [f"카드 ↔ 허브 객체 연결 범위(O0a {m['version']}) — 허브 {m['hub']} · 표본 {m['read']}/{m['sample']} · 씨앗 {m['seed']} · "
             f"{m['seconds']}초",
             f"어느 타입이든 exact 로 이어진 카드 {report['any_type_linked']}장({report['any_type_linked_pct']}%)"]
    for t, row in report["by_type"].items():
        docs = " · ".join(f"{d} {v['linked']}/{v['read']}" for d, v in row["by_doc_type"].items())
        lines.append(f"- {t} — 객체 {row['objects']} · 이어진 카드 {row['cards_linked']}장({row['cards_linked_pct']}%) · 판정 {row['verdicts']} · {docs}")
    f = report["existing_fields"]
    lines.append(f"이미 있는 칸 — 과제 코드 {f['project']} · 규격 참조 {f['standard_refs']} · 물성 줄 {f['properties']}")
    d = m["dictionary"]
    lines.append(f"사전 — 낱말 {d['terms']} · 별칭 있는 객체 {d['objects_with_aliases']} · 뺀 낱말 {d['skipped']}")
    if m["dictionary_problems"] or m["resolve_problems"] or m["sample_problems"] or m["card_failures"] or m["call_failures"]:
        lines.append(f"문제 — 사전 {m['dictionary_problems']} · 풀이 {m['resolve_problems']} · 표본 {m['sample_problems']} · 카드 실패 {m['card_failures']} · "
                     f"호출 실패 {m['call_failures']}")
    return "\n".join(lines)


def _tools_map(base: str, token: str) -> dict:
    """게이트웨이 /tools-map — 포털처럼 무인증으로 먼저, 거절(401 · 403)이면 PAT 로 다시."""
    url = base.rstrip("/").removesuffix("/mcp") + "/tools-map"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403):
            raise
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=30) as r:
        return json.load(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="카드 ↔ 허브 객체 연결 범위(읽기 전용)")
    ap.add_argument("--gateway", default=os.environ.get("HWAX_GATEWAY_URL", "http://127.0.0.1:9110/mcp"))
    ap.add_argument("--token-env", default="HWAX_GATEWAY_PAT", help="PAT 를 담은 환경변수 이름")
    ap.add_argument("--strata", default=DEFAULT_STRATA, help="문서종류:수,… (기본 300장)")
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--types", default="", help="허브 타입 슬러그,… (기본 core_vocab types)")
    ap.add_argument("--stop", default="", help="사전에서 뺄 낱말 파일(한 줄에 하나)")
    ap.add_argument("--max-objects", type=int, default=20000, help="타입당 사전에 넣을 객체 상한")
    ap.add_argument("--sections-max", type=int, default=400, help="카드당 읽을 절 상한")
    ap.add_argument("--sleep", type=float, default=0.05, help="호출 사이 쉼(초)")
    ap.add_argument("--out", default="", help="결과 폴더(기본 infra/.state/card-entity-probe/<시각>)")
    a = ap.parse_args(argv)
    try:
        strata = parse_strata(a.strata)
    except ValueError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    token = os.environ.get(a.token_env, "").strip()
    if not token:
        print(f"✗ {a.token_env} 가 비었다 — 포털 /auth/pat 로 발급한 PAT 를 그 환경변수에 넣고 다시", file=sys.stderr)
        return 2
    vocab = load_core_vocab()
    hub = ((vocab.get("canonical") or {}).get("app") or "").strip()
    types = [t.strip() for t in a.types.split(",") if t.strip()] or sorted(set((vocab.get("types") or {}).values()))
    stop = {line.strip() for line in Path(a.stop).read_text(encoding="utf-8").splitlines() if line.strip()} if a.stop else set()
    try:
        tmap = _tools_map(a.gateway, token)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 /tools-map 을 읽지 못했다 — {exc!r}", file=sys.stderr)
        return 2
    exposed = exposed_names(tmap, {hub: HUB_TOOLS, AIDH_APP: AIDH_TOOLS})
    need = [f"{hub}:{t}" for t in ("objects_list", "objects_resolve_many") if (hub, t) not in exposed]
    need += [f"{AIDH_APP}:{t}" for t in AIDH_TOOLS if (AIDH_APP, t) not in exposed]
    if need:
        print(f"✗ 이 게이트웨이에 없는 도구 — {', '.join(need)}. 정본 허브가 없는 박스(dev)에서는 잴 수 없다 — cae00 에서 돌린다", file=sys.stderr)
        return 2
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        print(f"✗ mcp 모듈 없음({exc}) — 게이트웨이와 같은 파이썬(venv)으로 돌린다", file=sys.stderr)
        return 2
    out_dir = Path(a.out) if a.out else ROOT / "infra" / ".state" / "card-entity-probe" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    async def go() -> dict:
        headers = {"Authorization": f"Bearer {token}", "X-HWAX-Corr": "card-entity-probe"}
        async with streamablehttp_client(a.gateway, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()

                async def call(name: str, args: dict) -> Any:
                    return as_json(await s.call_tool(name, args))
                caller = ReadOnlyCaller(call, exposed, sleep=a.sleep)
                return await run_probe(caller, hub=hub, types=types, strata=strata, seed=a.seed, stop=stop,
                                       max_objects=a.max_objects, sections_max=a.sections_max,
                                       log=lambda m: print(m, file=sys.stderr))

    report = asyncio.run(go())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    text = summary_text(report)
    (out_dir / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\n결과 — {out_dir}(report.json 의 흔한 낱말은 허브 객체 이름이다 — 추적 파일에 옮기지 않는다)")
    m = report["meta"]
    return 3 if (m["call_failures"] or m["card_failures"] or m["dictionary_problems"] or m["resolve_problems"] or m["sample_problems"]) else 0


if __name__ == "__main__":
    sys.exit(main())
