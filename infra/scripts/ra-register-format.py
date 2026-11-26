#!/usr/bin/env python3
# HWAX 의 보고서 형식을 Report Archive 에 스스로 등록하고(미리보기가 기본) 그 id · 판을 박스 파일에 적는 명령(docs/leftovers-1121 L21-6 ①)
"""RA 형식 등록 — 손으로 둔 `deliberation` 템플릿 대신 스스로 등록한 형식으로 올리게 하는 박스 명령.

심의 보고서 · `/보고서` · 분석 루틴 보고서는 RA 의 `template_id="deliberation"`(v1)에 초안을 만든다. 그 템플릿은 RA 데이터베이스에 손으로
만들어 둔 것이라 없는 박스에서는 저장이 실패한다. RA v0.176.0 부터는 시스템이 자기 형식을 등록할 수 있다(`register_report_format` —
id 는 RA 가 `sys.<system>.<kind>` 로 만들고, 같은 내용으로 다시 부르면 아무것도 바뀌지 않는다).

하는 일
  1. `infra/ra/formats/<형식>.json` 을 읽어 게이트웨이의 RA 도구 `register_report_format` 에 **미리보기**로 묻는다(쓰지 않는다).
  2. `--apply` 면 등록한다. 등록은 그 PAT 주인의 RA 권한으로 된다 — `--owner-board` 의 부서에 템플릿을 만들 수 있는 사람이어야 한다.
  3. `--use` 면 그 id · 판을 박스 파일 `infra/ra-formats.local.json`(gitignore)에 적는다. 에이전트 서버 · 게이트웨이가 그 파일을 재기동 없이
     읽어 그때부터 그 형식으로 올린다(각자의 `/health` `ra_formats` 로 확인한다). 파일을 지우면 종전 `deliberation` v1 로 돌아간다.

**기본은 아무것도 바꾸지 않는다** — 인자 없이 부르면 미리보기뿐이고, `--use` 없이 등록만 해서는 올리는 곳이 바뀌지 않는다.

쓰는 법(RA 가 붙은 박스 — 리포 루트에서, 게이트웨이와 같은 파이썬)
  export HWAX_GATEWAY_PAT=<포털 /auth/pat 로 발급한 PAT>
  $PY infra/scripts/ra-register-format.py --owner-board <부서 slug>                  # 미리보기
  $PY infra/scripts/ra-register-format.py --owner-board <부서 slug> --apply --use    # 등록하고 쓰기 시작
  $PY infra/scripts/ra-register-format.py --owner-board <최상위 조직 slug> --apply --use --board sys-hwax
      # 심의 보고서 표준(docs/ra-delib-standard) — 소유는 최상위 조직(RA 는 소유 부서 트리 밖 사람에게 형식을 보이지 않는다),
      # 게시판은 RA 시스템 공간. 심의 결과 카드에 「시스템 공간에 올리기」 단추가 생기고 사람이 확인한 뒤 게시한다.

끝 코드 — 0 끝 · 2 준비 실패(형식 파일 · PAT · mcp 모듈 · RA 도구가 없다 — RA 가 v0.176 전이면 도구가 없다) · 3 RA 가 거절했다(까닭을 찍는다) ·
4 `--use` 인데 쓸 판을 알 수 없다(등록 전이다 — `--apply` 를 함께 준다).
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[2]
FORMATS_DIR = ROOT / "infra" / "ra" / "formats"
BOX_FILE = ROOT / "infra" / "ra-formats.local.json"
RA_APP = "reportarchive"
TOOL = "register_report_format"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_BOARD_RE = re.compile(r"(?!\.{1,2}$)[A-Za-z0-9._-]{1,64}")         # RA 공간 slug — 포털 app/agent/ra_post.py 와 같은 꼴(fullmatch)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,23}$")


def _probe():
    """탐침(card-entity-probe.py)의 /tools-map 읽기 · 드러난 이름 풀이 · 답 풀기를 그대로 쓴다."""
    spec = importlib.util.spec_from_file_location("card_entity_probe", Path(__file__).with_name("card-entity-probe.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_format(name: str, formats_dir: Path = FORMATS_DIR) -> dict:
    """형식 파일을 읽어 꼴을 본다 — system · kind(RA 의 꼴) · name · blocks[{id, type}]. 내용(content)은 받지 않는다(틀이지 보고서가 아니다)."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", name or ""):
        raise ValueError(f"형식 이름 꼴이 아니다 — {name!r}")
    path = formats_dir / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"형식 파일이 없다 — {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    for k in ("system", "kind"):
        if not isinstance(doc.get(k), str) or not _SLUG_RE.fullmatch(doc[k]):
            raise ValueError(f"`{k}` 는 소문자 · 숫자 · `-` · `_` 24자 이하여야 한다(RA 의 꼴) — {doc.get(k)!r}")
    if not isinstance(doc.get("name"), str) or not doc["name"].strip():
        raise ValueError("`name` 이 비었다")
    blocks = doc.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("`blocks` 가 비었다")
    seen = set()
    for b in blocks:
        if not isinstance(b, dict) or not isinstance(b.get("id"), str) or not isinstance(b.get("type"), str):
            raise ValueError(f"블록은 {{id, type, props?}} 여야 한다 — {b!r}")
        if "content" in b:
            raise ValueError(f"블록 `{b['id']}` 에 content 가 있다 — 형식에는 내용을 넣지 않는다")
        if b["id"] in seen:
            raise ValueError(f"블록 id `{b['id']}` 가 두 번 나온다")
        seen.add(b["id"])
    return doc


def call_args(fmt: dict, owner_board: str, apply: bool) -> dict:
    return {"system": fmt["system"], "kind": fmt["kind"], "name": fmt["name"], "description": fmt.get("description") or "",
            "blocks": fmt["blocks"], "owner_boards": [owner_board], "apply": bool(apply)}


def read_box(path: Path = BOX_FILE) -> dict:
    """박스 파일의 지금 내용 — 없거나 깨졌으면 빈 것(쓸 때 새로 짓는다)."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def write_box(kind: str, template_id: str, version: int, path: Path = BOX_FILE, board: str | None = None) -> dict:
    """그 종류의 줄만 바꿔 쓴다(다른 종류 · 메모 칸은 그대로, 그 줄의 다른 칸 — 손으로 둔 board 등 — 도 그대로). board 를 주면 그 줄에 게시판
    (심의 보고서가 올라갈 RA 시스템 공간 — docs/ra-delib-standard)까지 적는다. 임시 파일에 쓰고 바꿔 끼운다 — 읽는 쪽이 반쯤 쓴 파일을 보지 않게."""
    if not _ID_RE.fullmatch(template_id or "") or not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError(f"쓸 수 없는 id · 판 — {template_id!r} v{version!r}")
    if board is not None and not _BOARD_RE.fullmatch(board):
        raise ValueError(f"쓸 수 없는 게시판 — {board!r}")
    doc = read_box(path)
    doc.setdefault("_doc", "RA 에 스스로 등록한 형식의 id · 판 — infra/scripts/ra-register-format.py --use 가 쓴다. 지우면 종전 템플릿으로 돌아간다.")
    row = dict(doc[kind]) if isinstance(doc.get(kind), dict) else {}
    row.update(template_id=template_id, template_version=version)
    if board is not None:
        row["board"] = board
    doc[kind] = row
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return doc


async def run(call: Callable[[dict], Awaitable[Any]], fmt: dict, *, owner_board: str, apply: bool, use: bool,
              box_file: Path = BOX_FILE, log: Callable[[str], None] = print, board: str | None = None) -> tuple[int, dict]:
    """미리보기 → (--apply) 등록 → (--use) 박스 파일. call 은 register_report_format 을 부르고 답을 dict 로 돌려준다."""
    out: dict = {"format": fmt["kind"], "owner_board": owner_board}
    pre = await call(call_args(fmt, owner_board, False))
    if not isinstance(pre, dict) or pre.get("error") or not pre.get("template_id"):
        log(f"✗ RA 가 미리보기를 거절했다 — {(pre or {}).get('error') if isinstance(pre, dict) else pre!r}")
        return 3, {**out, "error": (pre or {}).get("error") if isinstance(pre, dict) else str(pre)[:300]}
    out.update(template_id=pre["template_id"], would=pre.get("would"), current_version=pre.get("current_version"))
    log(f"· 미리보기 — {pre['template_id']} 는 {({'created': '새로 만들어진다', 'unchanged': '그대로다(내용이 같다)', 'new_version': '새 판이 된다'}).get(pre.get('would'), pre.get('would'))}"
        + (f"(지금 v{pre['current_version']})" if pre.get("current_version") else ""))
    version = pre.get("current_version") if pre.get("would") == "unchanged" else None
    if apply and pre.get("would") != "unchanged":
        made = await call(call_args(fmt, owner_board, True))
        if not isinstance(made, dict) or made.get("error") or not made.get("version"):
            log(f"✗ RA 가 등록을 거절했다 — {(made or {}).get('error') if isinstance(made, dict) else made!r}")
            return 3, {**out, "error": (made or {}).get("error") if isinstance(made, dict) else str(made)[:300]}
        version = made["version"]
        out.update(action=made.get("action"), version=version)
        log(f"✓ 등록했다 — {made.get('template_id')} v{version}({made.get('action')})")
    elif apply:
        out.update(action="unchanged", version=version)
        log("○ 등록할 것이 없다 — 내용이 같다")
    if use:
        if not isinstance(version, int) or isinstance(version, bool):
            log("✗ 쓸 판을 알 수 없다 — 아직 등록되지 않았거나 내용이 달라졌다. --apply 를 함께 준다")
            return 4, out
        write_box(fmt["kind"], pre["template_id"], version, box_file, board=board)
        out["box_file"] = box_file.name
        if board:
            out["board"] = board
        log(f"✓ {box_file.name} 에 적었다 — {fmt['kind']} → {pre['template_id']} v{version}"
            + (f" · 게시판 {board}(심의 결과 카드에 「시스템 공간에 올리기」 단추)" if board else "")
            + ". 에이전트 서버 · 게이트웨이의 /health ra_formats 로 확인한다")
    elif not apply:
        log("○ 미리보기만 했다 — 등록은 --apply, 그 형식으로 올리기 시작하려면 --use")
    else:
        log("○ 등록만 했다 — 올리는 곳은 그대로다(--use 로 바꾼다)")
    return 0, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HWAX 의 보고서 형식을 Report Archive 에 스스로 등록한다(미리보기가 기본)")
    ap.add_argument("--format", default="deliberation", help="infra/ra/formats/<이름>.json")
    ap.add_argument("--owner-board", required=True, help="이 형식을 소유할 RA 부서 slug(비울 수 없다 — RA 의 규칙)")
    ap.add_argument("--apply", action="store_true", help="등록한다(없으면 미리보기)")
    ap.add_argument("--use", action="store_true", help="그 id · 판을 박스 파일에 적어 그 형식으로 올리기 시작한다")
    ap.add_argument("--board", default=None, help="--use 와 함께 — 심의 보고서를 올릴 RA 시스템 공간 slug(예 sys-hwax). 사람이 확인한 뒤 게시한다")
    ap.add_argument("--gateway", default=os.environ.get("HWAX_GATEWAY_URL", "http://127.0.0.1:9110/mcp"))
    ap.add_argument("--token-env", default="HWAX_GATEWAY_PAT", help="PAT 를 담은 환경변수 이름")
    a = ap.parse_args(argv)
    try:
        fmt = load_format(a.format)
    except (ValueError, OSError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", a.owner_board or ""):
        print(f"✗ --owner-board 가 부서 slug 꼴이 아니다 — {a.owner_board!r}", file=sys.stderr)
        return 2
    if a.board is not None and (not a.use or not _BOARD_RE.fullmatch(a.board)):
        print(f"✗ --board 는 --use 와 함께, 공간 slug 꼴로 준다 — {a.board!r}", file=sys.stderr)
        return 2
    token = os.environ.get(a.token_env, "").strip()
    if not token:
        print(f"✗ {a.token_env} 가 비었다 — 포털 /auth/pat 로 발급한 PAT 를 그 환경변수에 넣고 다시", file=sys.stderr)
        return 2
    probe = _probe()
    try:
        tmap = probe._tools_map(a.gateway, token)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ 게이트웨이 /tools-map 을 읽지 못했다 — {exc!r}", file=sys.stderr)
        return 2
    exposed = probe.exposed_names(tmap, {RA_APP: (TOOL,)}).get((RA_APP, TOOL))
    if not exposed:
        print(f"✗ 이 게이트웨이에 {RA_APP}:{TOOL} 가 없다 — RA 가 붙어 있지 않거나(dev) v0.176.0 전이다. 올리는 곳은 그대로 둔다", file=sys.stderr)
        return 2
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        print(f"✗ mcp 모듈 없음({exc}) — 게이트웨이와 같은 파이썬(venv)으로 돌린다", file=sys.stderr)
        return 2

    async def go() -> tuple[int, dict]:
        headers = {"Authorization": f"Bearer {token}", "X-HWAX-Corr": "ra-register-format"}
        async with streamablehttp_client(a.gateway, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()

                async def call(args: dict) -> Any:
                    return probe.as_json(await s.call_tool(exposed, args))
                return await run(call, fmt, owner_board=a.owner_board, apply=a.apply, use=a.use,
                                 log=lambda m: print(m, file=sys.stderr), board=a.board)

    code, out = asyncio.run(go())
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
