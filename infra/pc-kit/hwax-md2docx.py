#!/usr/bin/env python3
# 보고서 마크다운(md)을 그림이 든 Word(docx)로 바꾸는 PC 용 변환기 — 표 칸 안 그림까지 넣고, 하나라도 못 넣으면 docx 를 쓰지 않는다
"""hwax-md2docx — HWAX 보고서 md 를 docx 로 바꾼다(Python 3.9+, python-docx).

    python hwax-md2docx.py 보고서.md [-o 보고서.docx] [--fig-dir 폴더 ...] [--allow-missing]
                           [--max-width-cm 16.0] [--font "맑은 고딕"]

그림 표기 ![캡션](src) 는 어디에 있어도 그림이 된다.
  · 줄에 홀로 있으면 본문 폭(--max-width-cm 까지) 그림과 그 아래 캡션 문단
  · 문단 · 목록 · 제목 안이면 줄 안 그림(제 크기, 남은 폭까지)
  · 표 칸 안이면 그 열 몫의 폭(비율 유지) 그림과 같은 칸 안의 캡션 — 칸의 앞뒤 글은 그대로, 한 칸에 여럿도 된다
  · 작은 그림은 제 크기(96 dpi)의 두 배까지만 키운다. HTML 주석은 뺀다. HTML <img> · 참조 꼴 ![캡션][이름] 은 그림이 못 된다고 알린다
src 는 md 기준 상대 경로 · 절대 경로(/a/b.png · H:/a/b.png · H:\\a\\b.png · \\\\서버\\공유\\a.png) · 그림 ref(fig_… · fig:fig_…)다.
ref 는 (1) md 폴더와 --fig-dir 폴더에서 이름에 ref 가 든 파일(figure_get 의 curl 이 받는 <도구>-<ref>.<확장자>)을 쓰고,
(2) 없으면 환경 변수 HWAX_GATEWAY_PAT · HWAX_PORTAL_BASE(https://<포털 호스트>)가 있을 때 {base}/mcp-gw/fig/<ref> 에서 받아 md 옆에 둔다.
png · jpeg · gif · bmp 는 그대로, webp 는 Pillow, svg 는 cairosvg 로 png 로 바꿔 넣는다(없으면 그렇게 말하고 실패한다).

끝 줄 '그림 표기 N · docx 그림 N · 표 칸 안 M' 은 저장한 docx 를 다시 열어 센 수다.
종료 코드 — 0 됨 · 1 인자 · 입력 · 환경 문제 · 2 그림이 없거나 못 읽음(docx 를 쓰지 않는다. --allow-missing 이면 빨간 자리표로 쓴다)
· 3 저장한 docx 의 그림 수가 md 의 그림 표기 수와 다름(빠진 그림이 있다).
"""
from __future__ import annotations

import argparse
import http.client
import io
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath

EXIT_OK, EXIT_USAGE, EXIT_MISSING, EXIT_MISMATCH = 0, 1, 2, 3

PAGE_W_CM, PAGE_H_CM, MARGIN_CM = 21.0, 29.7, 2.0          # A4 · 네 변 2 cm — 본문 폭 17 cm
TEXT_W_CM = PAGE_W_CM - 2 * MARGIN_CM
MAX_H_CM = (PAGE_H_CM - 2 * MARGIN_CM) * 0.8                # 그림 높이 상한 — 세로로 긴 그림도 캡션과 한 쪽에 든다
CELL_PAD_CM = 0.4                                           # 표 칸 좌우 여백(Word 기본 0.19 cm × 2)에 조금 더
INDENT_CM = 0.75                                            # 목록 · 인용 한 단의 들여쓰기
NATURAL_DPI = 96                                            # 줄 안 그림의 제 크기 — 화면 픽셀 기준
EMU_PER_CM, EMU_PER_INCH = 360000, 914400
MAX_IMAGE_BYTES = 64 * 1024 * 1024
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg")
REF_RE = re.compile(r"fig_[A-Za-z0-9_-]{22}")                # 게이트웨이 그림 ref — fig_ + 무작위 16바이트(22자)
_NAME_REF = re.compile(r"fig_[A-Za-z0-9_-]{22}(?=\.[A-Za-z0-9]{1,5}$|$)")   # 파일 이름 끝의 ref(<도구>-<ref>.<확장자>)


class Problem(Exception):
    """그림 하나를 넣지 못한 까닭 — 줄 번호와 함께 사람에게 그대로 보인다."""


# ── 그림 표기 읽기 ────────────────────────────────────────────────────────────────────────────────────
class Mark:
    """[글](주소 "제목") · ![글](주소 "제목") 표기 하나 — s 안의 자리(start · end)."""
    __slots__ = ("start", "end", "alt", "src", "title")

    def __init__(self, start: int, end: int, alt: str, src: str, title: str):
        self.start, self.end, self.alt, self.src, self.title = start, end, alt, src, title


_TITLE_TAIL = re.compile(r"[ \t]*(?:\"([^\"\n]*)\"|'([^'\n]*)'|\(([^()\n]*)\))?[ \t]*\)")
_TITLE_IN = re.compile(r"(.*?)[ \t]+(?:\"([^\"]*)\"|'([^']*)'|\(([^()]*)\))")


def _bracket_end(s: str, j: int) -> int:
    """s[j:] 가 '[' 바로 뒤일 때 짝 맞는 ']' 의 자리(없으면 -1) — 안의 대괄호는 짝을 맞추고 역슬래시 다음 글자는 건너뛴다. 빈 줄은 넘지 않는다."""
    n, depth = len(s), 1
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return j
        elif c == "\n":
            nl = s.find("\n", j + 1)
            if not s[j + 1:nl if nl >= 0 else n].strip():
                return -1
        j += 1
    return -1


def match_bracket(s: str, i: int, bang: bool = True) -> Mark | None:
    """s[i:] 가 ![글](주소)(bang) 또는 [글](주소) 로 시작하면 그 표기, 아니면 None.

    글 안의 대괄호는 짝을 맞춘다. 주소의 역슬래시는 글자 그대로 둔다(Windows 경로 H:\\a\\b.png). 주소는 <…> 로 감싸면 빈칸을 품고,
    감싸지 않아도 따옴표 · 괄호 제목이 없으면 짝 맞는 닫는 괄호까지가 주소다(H:\\내 문서\\a.png 도 그림이 된다)."""
    n, j = len(s), i + (2 if bang else 1)
    if s[i:j] != ("![" if bang else "["):
        return None
    j = _bracket_end(s, j)
    if j < 0 or s[j + 1:j + 2] != "(":
        return None
    alt, k = s[i + (2 if bang else 1):j], j + 2
    while k < n and s[k] in " \t":
        k += 1
    if s[k:k + 1] == "<":
        e = s.find(">", k + 1)
        if e < 0 or "\n" in s[k + 1:e]:
            return None
        m = _TITLE_TAIL.match(s, e + 1)
        if not m:
            return None
        src, title, end = s[k + 1:e], next((g for g in m.groups() if g is not None), ""), m.end()
    else:
        e, depth = k, 1
        while e < n and s[e] != "\n":
            if s[e] == "(":
                depth += 1
            elif s[e] == ")":
                depth -= 1
                if depth == 0:
                    break
            e += 1
        if e >= n or s[e] != ")":
            return None
        inner = s[k:e].strip()
        m = _TITLE_IN.fullmatch(inner)
        src, title = (m.group(1), next((g for g in m.groups()[1:] if g is not None), "")) if m else (inner, "")
        end = e + 1
    src = src.strip()
    return Mark(i, end, alt, src, title) if src else None


_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_QUOTE_ONE = re.compile(r" {0,3}>[ \t]?")
_CODE_SPAN = re.compile(r"(`+)(?!`)((?:(?!\n[ \t]*\n).)+?)(?<!`)\1(?!`)", re.S)
# 세기용 줄 안 코드 — 줄을 넘지 않고 이스케이프 안 한 | 도 넘지 않는다(GFM 은 표 칸을 먼저 가른다). 렌더러보다 덜 가린다 — 더 세면 보이는 종료 3
# 이지만, 덜 세면 렌더러가 놓친 그림과 맞비겨 말없이 빠진다(반대 검토 K2 — 표의 다른 줄끼리 짝지은 ` 가 그림을 가렸다).
_CODE_SPAN_LINE = re.compile(r"(`+)(?!`)((?:\\\||[^|\n])+?)(?<!`)\1(?!`)")
_ESCAPABLE = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_REF_DEF = re.compile(r"^ {0,3}(?:>[ \t]?)*\[([^\]\n]+)\]:[ \t]*\S", re.M)
_LOOKS_IMG = re.compile(r"\.(?:png|jpe?g|gif|bmp|webp|svg)\b|fig_[A-Za-z0-9_-]{22}", re.I)
_HTML_IMG = re.compile(r"<img\b[^>\n]*>?", re.I)
WHY_BROKEN = "그림 표기로 읽지 못했다 - ![캡션](경로) 꼴인지 본다(닫는 ] · ( · ) 가 빠졌나)"
WHY_REFSTYLE = "참조 꼴 ![캡션][이름] 은 읽지 않는다 - ![캡션](경로) 로 쓴다"
WHY_HTML = "HTML <img> 는 그림으로 넣지 않는다 - ![캡션](경로) 로 쓴다"


def _fence_open(line: str) -> str | None:
    m = _FENCE.match(line)
    if not m or (m.group(1)[0] == "`" and "`" in m.group(2)):
        return None
    return m.group(1)


def _fence_close(line: str, fence: str) -> bool:
    m = _FENCE.match(line)
    return bool(m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip())


def code_lines(lines: list[str]) -> list[bool]:
    """줄마다 울타리 코드(여는 줄 · 안 · 닫는 줄)인가. 인용 안의 울타리도 울타리이고 그 인용이 끝나면 함께 끝난다. 닫는 줄은 여는 줄의 인용 깊이만큼만
    떼고 본다 — 깊이 0 의 울타리 안 '> ```' 는 글이다(반대 검토 K3). 렌더러의 인용 · 울타리 읽기와 같은 끝이다."""
    out, fence, depth = [], None, 0
    for ln in lines:
        if fence is not None:
            body, got = ln, 0
            while got < depth and _QUOTE_ONE.match(body):
                body, got = body[_QUOTE_ONE.match(body).end():], got + 1
            if got == depth:
                out.append(True)
                if _fence_close(body, fence):
                    fence = None
                continue
            fence = None                                     # 인용이 끝났다 — 울타리도 끝, 이 줄은 새로 본다
        body, depth = ln, 0
        while _QUOTE_ONE.match(body):
            body, depth = body[_QUOTE_ONE.match(body).end():], depth + 1
        fence = _fence_open(body)
        out.append(fence is not None)
    return out


def _why_not_image(rest: str, defs: set) -> str | None:
    """그림 표기가 못 된 '![…' 의 까닭 — 그림을 뜻한 꼴만 잡는다. 정의된 이름의 참조 꼴 · 대괄호 뒤 '(' 가 열렸는데 못 닫힘 · 대괄호가 안 닫혔는데 그림
    경로 · ref 가 있음. '좋다![1]' · '것![^1]'(인용 번호 · 각주)는 글이다(CommonMark 도 글로 둔다 — 반대 검토 K8)."""
    e = _bracket_end(rest, 2)
    if e < 0:
        return WHY_BROKEN if _LOOKS_IMG.search(rest) else None
    after = rest[e + 1:]
    m = re.match(r"\[([^\]\n]*)\]", after)
    label = ((m.group(1) if m else "") or rest[2:e]).strip().lower()
    if label and not label.startswith("^") and label in defs:
        return WHY_REFSTYLE
    return WHY_BROKEN if re.match(r"[ \t]*\(", after) else None


def count_marks(text: str) -> tuple[list[tuple[int, Mark]], list[tuple[int, str, str]]]:
    """md 전체의 그림 표기를 블록 해석과 **따로** 센다 — 울타리 코드 · 줄 안 코드 · 역슬래시 escape 밖만. 저장 뒤 docx 의 그림 수와 견줘
    변환기가 놓친 표기(표 · 목록 · 인용 어디서든)를 잡는다. 돌려주는 것 — [(줄, 표기)] 와 그림이 되지 못할 표기 [(줄, 앞 40자, 까닭)] —
    깨진 '![' · 참조 꼴 ![캡션][이름] · HTML <img>(글자로 남아 그림이 말없이 빠진다)."""
    lines = text.split("\n")
    orig = "\n".join("" if code else ln for ln, code in zip(lines, code_lines(lines)))
    s, i, n = list(orig), 0, len(orig)
    while i < n:                                             # 왼쪽부터 — 역슬래시 escape 와 줄 안 코드를 빈칸으로
        if orig[i] == "\\" and i + 1 < n and orig[i + 1] in _ESCAPABLE:
            s[i] = s[i + 1] = " "
            i += 2
        elif orig[i] == "`":
            m = _CODE_SPAN_LINE.match(orig, i)
            if m:
                for k in range(i, m.end()):
                    s[k] = " "
                i = m.end()
            else:
                while i < n and orig[i] == "`":
                    i += 1
        else:
            i += 1
    flat = "".join(s)
    defs = {m.group(1).strip().lower() for m in _REF_DEF.finditer(flat)}
    marks, broken, i = [], [], 0
    while True:
        i = flat.find("![", i)
        if i < 0:
            break
        line = flat.count("\n", 0, i) + 1
        mk = match_bracket(flat, i, True)
        if mk:
            marks.append((line, mk))
            i = mk.end
            continue
        rest = flat[i:].split("\n", 1)[0]
        why = _why_not_image(rest, defs)
        if why:
            broken.append((line, rest[:40], why))
        i += 2
    for m in _HTML_IMG.finditer(flat):
        broken.append((flat.count("\n", 0, m.start()) + 1, m.group(0)[:40], WHY_HTML))
    return marks, sorted(broken, key=lambda b: b[0])


def drop_comments(text: str) -> str:
    """HTML 주석(<!-- … -->)을 뺀다 — 렌더된 md 에서 보이지 않는 글이다(반대 검토 K8 — docx 에 글로 실렸고, 그 안의 예시 그림 표기가 '파일이 없다' 로
    docx 를 막았다). 울타리 코드 · 줄 안 코드 안은 그대로 두고, 줄바꿈은 남겨 줄 번호가 그대로다. 렌더러와 세기가 같은 글을 본다."""
    if "<!--" not in text:
        return text
    code = code_lines(text.split("\n"))
    out, i, n, li = list(text), 0, len(text), 0
    while i < n:
        c = text[i]
        if c == "\n":
            li, i = li + 1, i + 1
        elif code[li]:
            i += 1
        elif c == "\\" and i + 1 < n and text[i + 1] in _ESCAPABLE:
            i += 2
        elif c == "`":
            m = _CODE_SPAN.match(text, i)
            if m:
                li, i = li + text.count("\n", i, m.end()), m.end()
            else:
                while i < n and text[i] == "`":
                    i += 1
        elif text.startswith("<!--", i) and text.find("-->", i + 4) >= 0:
            e = text.find("-->", i + 4) + 3
            nl = text.count("\n", i, e)
            if any(code[li:li + nl + 1]):                    # 울타리를 넘는 주석은 주석으로 보지 않는다
                i += 1
                continue
            for k in range(i, e):
                if text[k] != "\n":
                    out[k] = ""
            li, i = li + nl, e
        else:
            i += 1
    return "".join(out)


# ── 줄 안 글 읽기 — 굵게 · 기울임 · 코드 · 취소선 · 줄바꿈 · 링크 · 그림 ───────────────────────────────────
class Text:
    __slots__ = ("text", "bold", "italic", "code", "strike")

    def __init__(self, text, bold=False, italic=False, code=False, strike=False):
        self.text, self.bold, self.italic, self.code, self.strike = text, bold, italic, code, strike


class Img:
    """그림 표기 하나 — 캡션(alt) · 주소 · 제목 · md 의 줄."""
    __slots__ = ("alt", "src", "title", "line")

    def __init__(self, alt: str, src: str, title: str, line: int):
        self.alt, self.src, self.title, self.line = alt, src, title, line


BREAK = object()                                             # 줄바꿈(<br> · 끝 빈칸 둘 · 끝 역슬래시)
_EMPH = (("***", True, True, False), ("**", True, False, False), ("*", False, True, False), ("~~", False, False, True))


def _emph_end(s: str, i: int, d: str) -> int:
    """s[i:] 의 강조 표지 d(*** · ** · * · ~~)가 닫힌 자리 다음(없으면 -1). 줄 안 코드 · 그림 · 링크 · escape 는 통째로 건너뛴다 — 그 안의 * 로
    닫지 않는다(CommonMark 도 그것들이 강조보다 먼저 묶인다 — 반대 검토 K3 '*결과: ![σ* 분포](…)*' 의 그림이 글로 깨졌다)."""
    n, k = len(s), len(d)
    if not s.startswith(d, i) or i + k >= n or s[i + k].isspace() or s[i + k] == d[0]:
        return -1
    j = i + k
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            m = _CODE_SPAN.match(s, j)
            if m:
                j = m.end()
                continue
        elif c in "![":
            mk = match_bracket(s, j, c == "!")
            if mk:
                j = mk.end
                continue
        if s.startswith(d, j) and not s[j - 1].isspace() and s[j - 1] != d[0] and s[j + k:j + k + 1] != d[0]:
            return j + k
        j += 1
    return -1


_BR = re.compile(r"<br\s*/?>", re.I)
_AUTOLINK = re.compile(r"<((?:https?|ftp|mailto):[^<>\s]+)>")


def parse_inline(s: str, line: int = 1, *, bold=False, italic=False, strike=False, images=True) -> list:
    """줄 안 글 → [Text · BREAK · Img]. '_' 강조는 읽지 않는다(fig_… · 파일 이름의 밑줄을 지킨다). images=False 면 그림 표기도 글이다(캡션)."""
    out, buf, i, n = [], [], 0, len(s)

    def flush():
        if buf:
            out.append(Text("".join(buf), bold, italic, False, strike))
            buf.clear()

    def sub(text, at, **kw):
        style = {"bold": bold, "italic": italic, "strike": strike, "images": images}
        style.update(kw)
        return parse_inline(text, line + s.count("\n", 0, at), **style)

    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            if s[i + 1] == "\n":
                flush()
                out.append(BREAK)
                i += 2
                continue
            if s[i + 1] in _ESCAPABLE:
                buf.append(s[i + 1])
                i += 2
                continue
        elif c == "`":
            m = _CODE_SPAN.match(s, i)
            if m:
                flush()
                code = m.group(2).replace("\n", " ")
                if len(code) > 2 and code[0] == code[-1] == " " and code.strip():
                    code = code[1:-1]
                out.append(Text(code, bold, italic, True, strike))
                i = m.end()
                continue
            j = i
            while j < n and s[j] == "`":
                j += 1
            buf.append(s[i:j])
            i = j
            continue
        elif c == "!" and images:
            mk = match_bracket(s, i, True)
            if mk:
                flush()
                out.append(Img(mk.alt, mk.src, mk.title, line + s.count("\n", 0, i)))
                i = mk.end
                continue
        elif c == "[":
            mk = match_bracket(s, i, False)
            if mk:
                flush()
                inner = sub(mk.alt, i)
                out.extend(inner)
                if mk.src != "".join(t.text for t in inner if isinstance(t, Text)).strip():
                    out.append(Text(f" ({mk.src})", bold, italic, False, strike))
                i = mk.end
                continue
        elif c == "<":
            m = _BR.match(s, i) or _AUTOLINK.match(s, i)
            if m:
                if m.re is _BR:
                    flush()
                    out.append(BREAK)
                else:
                    buf.append(m.group(1))
                i = m.end()
                continue
        elif c in "*~":
            for d, b, it, st in _EMPH:
                end = _emph_end(s, i, d) if d[0] == c else -1
                if end > 0:
                    flush()
                    out.extend(sub(s[i + len(d):end - len(d)], i + len(d), bold=bold or b, italic=italic or it, strike=strike or st))
                    i = end
                    break
            else:
                buf.append(c)
                i += 1
            continue
        elif c == "\n":
            if len(buf) >= 2 and buf[-1] == buf[-2] == " ":
                while buf and buf[-1] == " ":
                    buf.pop()
                flush()
                out.append(BREAK)
            else:
                buf.append(" ")
            i += 1
            continue
        buf.append(c)
        i += 1
    flush()
    return out


def plain(toks: list) -> str:
    return "".join(t.text for t in toks if isinstance(t, Text))


def caption_of(img: Img) -> str:
    """캡션 글 — alt, 비면 제목. 마크다운 escape · 강조 표지는 뗀다."""
    return plain(parse_inline((img.alt or img.title).replace("\n", " "), images=False)).strip()


# ── 블록 읽기 — 제목 · 문단 · 목록(한 단 중첩) · GFM 표 · 인용 · 가로줄 · 울타리 코드 · 홀로 선 그림 줄 ────────────────
class Block:
    def __init__(self, kind: str, line: int, **kw):
        self.kind, self.line = kind, line
        self.__dict__.update(kw)


_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_HR = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_QUOTE = re.compile(r"^ {0,3}>[ \t]?(.*)$")
_LIST = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])(?:[ \t]+(.*))?$")
_TASK = re.compile(r"\[([ xX])\][ \t]+")
_DELIM_CELL = re.compile(r":?-+:?")
_PIPE = re.compile(r"(?<!\\)\|")


def split_table_row(line: str) -> list[str]:
    """GFM 표 줄 → 칸 글. 이스케이프한 \\| 는 칸 안의 | 다. 앞뒤 | 는 있어도 없어도 된다. 그림 표기는 통째로 한 칸에 둔다 — 캡션 · 경로의 | 로
    가르지 않는다(GFM 은 가른다 — 그 그림이 글자로 깨졌다, 반대 검토 K2)."""
    s = line.strip()
    cells, cur, i = [], [], 0
    while i < len(s):
        if s[i] == "\\" and s[i + 1:i + 2] == "|":
            cur.append("|")
            i += 2
            continue
        mk = match_bracket(s, i, True) if s.startswith("![", i) else None
        if mk:
            cur.append(s[i:mk.end])
            i = mk.end
            continue
        if s[i] == "|":
            cells.append("".join(cur))
            cur = []
        else:
            cur.append(s[i])
        i += 1
    cells.append("".join(cur))
    if s.startswith("|"):
        cells = cells[1:]
    if len(cells) > 1 and s.endswith("|") and not s.endswith("\\|"):
        cells = cells[:-1]
    return [c.strip() for c in cells]


def _indent(line: str) -> int:
    t = line.expandtabs(4)
    return len(t) - len(t.lstrip())


def _standalone(line: str) -> Mark | None:
    """그 줄이 그림 표기 하나뿐이면 그 표기."""
    s = line.strip()
    mk = match_bracket(s, 0, True) if s.startswith("![") else None
    return mk if mk and mk.end == len(s) else None


def _table_start(lines: list[str], i: int) -> bool:
    if i + 1 >= len(lines) or not _PIPE.search(lines[i]) or not _PIPE.search(lines[i + 1]):
        return False
    cells = split_table_row(lines[i + 1])
    return bool(cells) and all(_DELIM_CELL.fullmatch(c) for c in cells)


def _interrupts(lines: list[str], i: int) -> bool:
    """이 줄이 앞 문단을 끊고 다른 블록을 시작하나 — 목록은 글머리표와 1 로 시작하는 번호만 끊는다."""
    ln = lines[i]
    if (_fence_open(ln) or _HEADING.match(ln) or _HR.match(ln) or _QUOTE.match(ln) or _table_start(lines, i)
            or _standalone(ln)):
        return True
    m = _LIST.match(ln)
    return bool(m and (m.group(3) or "").strip() and (not m.group(2)[0].isdigit() or m.group(2)[:-1] == "1"))


def _parse_table(lines: list[str], i: int, base: int) -> tuple[Block, int]:
    header, delim = split_table_row(lines[i]), split_table_row(lines[i + 1])
    rows, row_lines, j = [], [], i + 2
    while (j < len(lines) and lines[j].strip() and _PIPE.search(lines[j])
           and not (_fence_open(lines[j]) or _HEADING.match(lines[j]) or _QUOTE.match(lines[j]))):
        rows.append(split_table_row(lines[j]))
        row_lines.append(base + j)
        j += 1
    # 칸이 머리보다 많은 줄도 버리지 않는다(GFM 은 넘는 칸을 버린다 — 그 칸의 그림이 말없이 사라진다)
    ncols = max([len(header), len(delim)] + [len(r) for r in rows])
    pad = lambda r: r + [""] * (ncols - len(r))  # noqa: E731
    aligns = []
    for c in pad(delim):
        aligns.append("center" if len(c) > 1 and c[0] == c[-1] == ":" else "right" if c.endswith(":") else "left")
    return Block("table", base + i, header=pad(header), aligns=aligns, rows=[pad(r) for r in rows], row_lines=row_lines), j


def _parse_list(lines: list[str], i: int, base: int) -> tuple[Block, int]:
    """글머리표 · 번호 목록. 첫 항목보다 2칸 이상 들여 쓴 항목은 한 단 아래(그보다 깊어도 한 단). 들여 쓴 줄 · 게으른 줄은 항목 글을 잇고,
    빈 줄 뒤 들여 쓴 줄은 항목 안 새 문단이다. 항목 안에서 그림 하나뿐인 줄은 앞뒤를 줄바꿈으로 띄운다."""
    items, n, first = [], len(lines), None
    while i < n:
        ln = lines[i]
        m = None if _HR.match(ln) else _LIST.match(ln)
        if m:
            ind = _indent(ln)
            first = ind if first is None else first
            text, task, mark = m.group(3) or "", None, m.group(2)
            t = _TASK.match(text)
            if t:
                task, text = t.group(1) != " ", text[t.end():]
            items.append(Block("item", base + i, level=1 if ind >= first + 2 else 0, ordered=mark[0].isdigit(),
                               number=int(mark[:-1]) if mark[0].isdigit() else None, task=task, paras=[[base + i, text]]))
            i += 1
            continue
        if not ln.strip():
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and not _HR.match(lines[j]) and _LIST.match(lines[j]):
                i = j
                continue
            if j < n and _indent(lines[j]) >= first + 2 and not _fence_open(lines[j]) and not _table_start(lines, j):
                items[-1].paras.append([base + j, ""])
                i = j
                continue
            break
        # 들여 쓴 표도 목록을 끝낸다 — 표로 읽는다(목록 글로 이으면 표 칸 그림이 문단 그림이 됐다, 반대 검토 K5)
        if (_indent(ln) < 2 and _interrupts(lines, i)) or _fence_open(ln) or _table_start(lines, i):
            break
        para, piece = items[-1].paras[-1], ln.strip()
        if _standalone(piece):
            para[1] = (para[1].rstrip() + "  " if para[1].strip() else para[1]) + "\n" + piece + "  "
        elif para[1]:
            para[1] += "\n" + ln.lstrip()
        else:
            para[1] = ln.lstrip()
            para[0] = base + i
        i += 1
    return Block("list", items[0].line, items=items), i


def parse_blocks(lines: list[str], base: int = 1) -> list[Block]:
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        fence = _fence_open(ln)
        if fence:
            j = i + 1
            while j < n and not _fence_close(lines[j], fence):
                j += 1
            out.append(Block("code", base + i, text="\n".join(lines[i + 1:j])))
            i = j + 1
            continue
        m = _HEADING.match(ln)
        if m:
            out.append(Block("heading", base + i, level=len(m.group(1)), text=(m.group(2) or "").strip()))
            i += 1
            continue
        if _HR.match(ln):
            out.append(Block("hr", base + i))
            i += 1
            continue
        if _QUOTE.match(ln):
            j, sub = i, []
            while j < n and _QUOTE.match(lines[j]):
                sub.append(_QUOTE.match(lines[j]).group(1))
                j += 1
            out.append(Block("quote", base + i, blocks=parse_blocks(sub, base + i)))
            i = j
            continue
        if _table_start(lines, i):
            blk, i = _parse_table(lines, i, base)
            out.append(blk)
            continue
        if _LIST.match(ln):
            blk, i = _parse_list(lines, i, base)
            out.append(blk)
            continue
        mk = _standalone(ln)
        if mk:
            out.append(Block("figure", base + i, img=Img(mk.alt, mk.src, mk.title, base + i)))
            i += 1
            continue
        j = i + 1
        while j < n and lines[j].strip() and not _SETEXT.match(lines[j]) and not _interrupts(lines, j):
            j += 1
        text = "\n".join(x.lstrip() for x in lines[i:j]).rstrip()
        if j < n and _SETEXT.match(lines[j]):                # 글 줄 밑의 === · --- 는 제목이다(CommonMark setext — 반대 검토 K11)
            out.append(Block("heading", base + i, level=1 if lines[j].strip()[0] == "=" else 2, text=text))
            i = j + 1
            continue
        out.append(Block("para", base + i, text=text))
        i = j
    return out


def cell_texts(b: Block) -> list[tuple[str, int, bool]]:
    """표의 칸 글 — (글, 줄, 머리 줄인가)."""
    out = [(c, b.line, True) for c in b.header]
    for row, line in zip(b.rows, b.row_lines):
        out += [(c, line, False) for c in row]
    return out


def collect_images(blocks: list[Block]) -> list[Img]:
    """그릴 차례대로 모든 그림 표기 — 렌더러가 읽는 것과 같은 해석이다(넣기 전에 모두 찾아 둔다)."""
    out: list[Img] = []

    def toks(text, line):
        return [t for t in parse_inline(text, line) if isinstance(t, Img)]

    for b in blocks:
        if b.kind in ("para", "heading"):
            out += toks(b.text, b.line)
        elif b.kind == "figure":
            out.append(b.img)
        elif b.kind == "list":
            for it in b.items:
                for line, text in it.paras:
                    out += toks(text, line)
        elif b.kind == "table":
            for text, line, _h in cell_texts(b):
                out += toks(text, line)
        elif b.kind == "quote":
            out += collect_images(b.blocks)
    return out


# ── 그림 주소 → 파일 ─────────────────────────────────────────────────────────────────────────────────
def classify_src(src: str) -> tuple[str, str]:
    """그림 주소의 꼴 — ('ref', fig_…) · ('url', 주소) · ('windows', H:\\…) · ('unc', \\\\서버\\…) · ('posix', /…) · ('relative', …)."""
    s = src.strip()
    r = s[4:] if s.lower().startswith("fig:") else s
    if REF_RE.fullmatch(r):
        return "ref", r
    if re.match(r"^[A-Za-z]:", s):
        return "windows", s
    if s.startswith(("\\\\", "//")):
        return "unc", s
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", s):
        return "url", s
    if s.startswith(("/", "\\")):
        return "posix", s
    return "relative", s


def src_path(src: str, base: PurePath | str, windows: bool) -> PurePath | None:
    """그림 주소 → 이 컴퓨터의 경로(순수 함수 — 파일을 보지 않는다). Windows 가 아닌 곳에서 드라이브 · UNC 경로는 None(닿을 수 없는 자리)."""
    kind, s = classify_src(src)
    if kind in ("ref", "url"):
        return None
    if windows:
        return PureWindowsPath(s) if kind != "relative" else PureWindowsPath(str(base)) / PureWindowsPath(s)
    if kind in ("windows", "unc"):
        return None
    if kind == "posix":
        return PurePosixPath(s.replace("\\", "/"))
    return PurePosixPath(str(base)) / s.replace("\\", "/")


def sniff(blob: bytes) -> str | None:
    """바이트로 그림 꼴을 가린다 — 이름 · 확장자는 믿지 않는다."""
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if blob.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if blob[:2] == b"BM" and len(blob) > 26:
        return "bmp"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp"
    head = blob[:4096].lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"<svg") or (head.startswith((b"<?xml", b"<!--", b"<!DOCTYPE")) and b"<svg" in head):
        return "svg"
    return None


class Picture:
    """넣을 그림 — docx 가 받는 바이트(png · jpeg · gif · bmp) · 제 크기(96 dpi 픽셀) · 어디서 왔나."""
    __slots__ = ("blob", "size", "origin")

    def __init__(self, blob: bytes, size: tuple[float, float], origin: str):
        self.blob, self.size, self.origin = blob, size, origin


def _webp_to_png(blob: bytes) -> bytes:
    try:
        from PIL import Image as PILImage
    except ImportError:
        raise Problem("webp 그림은 Pillow 가 있어야 png 로 바꿔 넣는다 - pip install Pillow (또는 도구를 png 로 다시 부른다)") from None
    try:
        with PILImage.open(io.BytesIO(blob)) as im:
            out = io.BytesIO()
            im.save(out, "PNG")
            return out.getvalue()
    except Exception as exc:  # noqa: BLE001 — 깨진 webp 도 그 그림 하나의 문제다
        raise Problem(f"webp 를 png 로 바꾸지 못했다({type(exc).__name__})") from None


def _svg_to_png(blob: bytes) -> bytes:
    try:
        import cairosvg  # Windows 는 Cairo 라이브러리(DLL)가 없으면 import 에서 OSError 다
    except (ImportError, OSError):
        raise Problem("svg 그림은 cairosvg 가 있어야 png 로 바꿔 넣는다 - pip install cairosvg (Windows 는 Cairo 라이브러리도 필요) "
                      "· 또는 도구를 png 로 다시 불러 받는다") from None
    try:
        return cairosvg.svg2png(bytestring=blob, scale=2.0)
    except Exception as exc:  # noqa: BLE001
        raise Problem(f"svg 를 png 로 바꾸지 못했다({type(exc).__name__})") from None


def complete(kind: str, blob: bytes) -> bool:
    """파일이 끝까지 있나 — python-docx 는 jpeg · gif · bmp 의 머리만 읽어 반쪽 파일도 넣고 Word 는 깨진 그림을 그린다(반대 검토 K4 — 끊긴
    curl -o · 받기가 남긴 꼴). png 는 python-docx 가 IEND 까지 조각을 걸어 이미 거른다. jpeg 은 표지를 길이로 건너 SOS 뒤에 EOI(FFD9)가 있어야 한다 —
    EXIF 안의 작은 그림 · 뒤에 붙은 영상(모션 사진)에 속지 않는다."""
    if kind == "jpeg":
        i, n = 2, len(blob)
        while i + 4 <= n and blob[i] == 0xFF:
            while i < n and blob[i] == 0xFF:
                i += 1
            if i >= n:
                return False
            m, i = blob[i], i + 1
            if m == 0xD9:
                return True
            if m == 0x01 or 0xD0 <= m <= 0xD7:
                continue
            seg = int.from_bytes(blob[i:i + 2], "big")
            if m == 0xDA:
                return blob.find(b"\xff\xd9", i + seg) >= 0
            i += seg
        return False
    if kind == "gif":
        return blob.rstrip(b"\x00").endswith(b"\x3b")
    if kind == "bmp":
        return len(blob) >= int.from_bytes(blob[2:6], "little")
    return True


def load_picture(blob: bytes, origin: str) -> Picture:
    """바이트 → 넣을 그림. png · jpeg · gif · bmp 는 그대로, webp · svg 는 png 로 바꾼다. 그 밖 · 깨진 것은 Problem."""
    kind, scale = sniff(blob), 1.0
    if kind is None:
        raise Problem("그림 파일이 아니다(png · jpeg · gif · bmp · webp · svg 만 넣는다)")
    if kind == "webp":
        blob = _webp_to_png(blob)
    elif kind == "svg":
        blob, scale = _svg_to_png(blob), 2.0
    try:
        from docx.image.image import Image as DocxImage
        im = DocxImage.from_blob(blob)
        w, h = im.px_width, im.px_height
    except Exception as exc:  # noqa: BLE001 — 머리를 못 읽는 그림은 넣지 않는다
        raise Problem(f"그림을 읽지 못했다({type(exc).__name__} - 깨진 파일?)") from None
    if w <= 0 or h <= 0:
        raise Problem("그림 크기가 0 이다")
    if not complete(kind, blob):
        raise Problem("파일이 끝까지 있지 않다(받다가 끊긴 파일?) - 다시 받는다")
    return Picture(blob, (w / scale, h / scale), origin)


def _read(p: Path) -> bytes:
    try:
        if p.stat().st_size > MAX_IMAGE_BYTES:
            raise Problem(f"그림 파일이 {MAX_IMAGE_BYTES // (1024 * 1024)} MB 를 넘는다")
        return p.read_bytes()
    except OSError as exc:
        raise Problem(f"파일을 읽지 못했다({exc.strerror or type(exc).__name__})") from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """넘김(30x)을 따라가지 않는다 — urllib 은 넘김에도 Authorization 을 실어 다른 호스트로 토큰이 샐 수 있다."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def fetch_ref(ref: str, base: str, pat: str, timeout: float = 60.0) -> bytes:
    """{base}/mcp-gw/fig/<ref> 를 그 사람의 PAT 로 받는다. 실패는 Problem(토큰은 어떤 말에도 싣지 않는다)."""
    if not re.match(r"^https?://[^/\s?#]+", base, re.I):
        raise Problem("HWAX_PORTAL_BASE 는 https://<포털 호스트> 꼴이어야 한다")
    url = base.rstrip("/") + "/mcp-gw/fig/" + urllib.parse.quote(ref, safe="")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + pat, "User-Agent": "hwax-md2docx/1"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=timeout) as r:
            want = (r.headers.get("Content-Length") or "").strip()
            blob = r.read(MAX_IMAGE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        why = {401: "토큰을 받지 않았다(만료 · 폐기 - 포털 /tokens 에서 다시 발급)",
               404: "게이트웨이에 없다(7일이 지났거나 내 그림이 아니다 - figure_list 로 내 그림을 본다)"}.get(exc.code, "")
        if 300 <= exc.code < 400:
            why = "다른 주소로 넘기려 했다 - 토큰을 따라 보내지 않는다(HWAX_PORTAL_BASE 를 https://… 로 고친다)"
        raise Problem(f"게이트웨이에서 받지 못했다(HTTP {exc.code}{' - ' + why if why else ''}) - "
                      f"개인 Claude 에서 figure_get(ref=\"{ref}\") 을 먼저 불러 curl 로 받는다") from None
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as exc:
        # 까닭은 꼴 이름과 OS 글만 — 서버가 보낸 글(깨진 상태 줄 · 머리)은 싣지 않는다. 받은 머리를 되비추는 서버면 토큰이 거기 있다(반대 검토 K6)
        r = exc.reason if isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, BaseException) else exc
        reason = type(r).__name__ + (f" {r.strerror}" if isinstance(r, OSError) and r.strerror else "")
        raise Problem(f"게이트웨이에 닿지 못했다({reason}) - 개인 Claude 에서 figure_get(ref=\"{ref}\") 을 먼저 불러 curl 로 받는다") from None
    if len(blob) > MAX_IMAGE_BYTES:
        raise Problem(f"받은 그림이 {MAX_IMAGE_BYTES // (1024 * 1024)} MB 를 넘는다")
    if want.isdigit() and len(blob) < int(want):
        raise Problem(f"받다가 끊겼다({len(blob)}/{want} 바이트) - 다시 돌리거나 figure_get 의 curl 로 받는다")
    return blob


class Resolver:
    """그림 주소 → Picture. ref 는 md 폴더 · --fig-dir 의 파일 먼저, 없으면 PAT 로 게이트웨이에서 받아 md 옆에 둔다."""

    def __init__(self, md_dir: Path, fig_dirs: list[Path], env=None, windows: bool | None = None):
        self.md_dir, self.fig_dirs = md_dir, list(fig_dirs)
        self.env = os.environ if env is None else env
        self.windows = (os.name == "nt") if windows is None else windows
        self.notes: list[str] = []                          # 받은 그림 · 못 둔 사본 — 끝에 알린다
        self.warned_http = False

    def resolve(self, src: str) -> Picture:
        kind, val = classify_src(src)
        if kind == "ref":
            return self._ref(val)
        if kind == "url":
            raise Problem("인터넷 주소의 그림은 받지 않는다 - 파일로 받아 경로나 fig_ ref 로 쓴다")
        bases = [self.md_dir, *self.fig_dirs] if kind == "relative" else [self.md_dir]
        for s in dict.fromkeys([src, urllib.parse.unquote(src)]):          # %20 꼴 주소도 본다
            for b in bases:
                p = src_path(s, b, self.windows)
                if p is not None and Path(str(p)).is_file():
                    return load_picture(_read(Path(str(p))), str(p))
        m = _NAME_REF.search(PurePosixPath(src.replace("\\", "/")).name)
        if m:                                                # 파일은 없지만 이름에 ref 가 있다(figure_get 이 줄 이름을 미리 적은 md)
            try:
                return self._ref(m.group(0))
            except Problem as exc:
                raise Problem(f"파일이 없고 이름의 ref 로도 못 찾았다 - {exc}") from None
        if kind in ("windows", "unc") and not self.windows:
            raise Problem("Windows 경로라 이 컴퓨터에서는 열 수 없다(Windows PC 에서 돌린다)")
        where = " · ".join(str(b) for b in bases)
        raise Problem(f"파일이 없다(찾은 곳 {where})")

    def _ref(self, ref: str) -> Picture:
        for d in [self.md_dir, *self.fig_dirs]:
            try:
                names = sorted(os.listdir(d))
            except OSError:
                continue
            hits = [x for x in names if ref in x and not x.endswith((".part", ".md", ".docx")) and (Path(d) / x).is_file()]
            hits.sort(key=lambda x: (os.path.splitext(x)[1].lower() not in IMAGE_EXTS, x))
            if hits:
                p = Path(d) / hits[0]
                return load_picture(_read(p), str(p))
        pat = (self.env.get("HWAX_GATEWAY_PAT") or "").strip()
        base = (self.env.get("HWAX_PORTAL_BASE") or "").strip()
        if not (pat and base):
            raise Problem(f"이 PC 에 {ref} 파일이 없다 - 개인 Claude 에서 figure_get(ref=\"{ref}\") 을 먼저 불러 나온 curl 한 줄로 "
                          f"md 폴더(또는 --fig-dir)에 받는다. 환경 변수 HWAX_GATEWAY_PAT · HWAX_PORTAL_BASE 를 두면 변환기가 받는다")
        u = urllib.parse.urlsplit(base)
        if u.scheme.lower() == "http" and u.hostname not in ("127.0.0.1", "localhost", "::1") and not self.warned_http:
            self.warned_http = True
            self.notes.append("HWAX_PORTAL_BASE 가 http:// 다 - 토큰이 암호화 없이 간다(https:// 로 바꾼다)")
        blob = fetch_ref(ref, base, pat)
        pic = load_picture(blob, f"게이트웨이 {ref}")
        dest = self.md_dir / f"{ref}.{sniff(blob)}"
        try:                                                 # md 옆에 둔다 — 다음엔 (1) 에서 찾는다. 못 써도 이번 변환은 된다
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(blob)
            os.replace(tmp, dest)
            self.notes.append(f"받음 {ref} -> {dest}")
        except OSError as exc:
            self.notes.append(f"받음 {ref} (md 옆에 두지 못함 - {exc.strerror or type(exc).__name__})")
        return pic


# ── docx 쓰기 ──────────────────────────────────────────────────────────────────────────────────────
def _set_font(doc, style_name: str, font: str) -> None:
    from docx.oxml.ns import qn
    try:
        st = doc.styles[style_name]
    except KeyError:
        return
    rf = st.element.get_or_add_rPr().get_or_add_rFonts()
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)                           # 테마 글꼴이 남으면 한글이 테마의 동아시아 글꼴로 나온다
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        rf.set(qn(a), font)


def new_document(font: str):
    from docx import Document
    from docx.shared import Cm
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(PAGE_W_CM), Cm(PAGE_H_CM)
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(MARGIN_CM)
    for name in ("Normal", "Title", "Caption", *(f"Heading {k}" for k in range(1, 7))):
        _set_font(doc, name, font)
    return doc


def _disp_len(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def column_shares(header: list[str], rows: list[list[str]]) -> list[float]:
    """열마다 본문 폭의 몫 — 그림이 든 열은 긴 글 열만큼(32), 글 열은 가장 긴 칸 글의 너비 + 칸 여백(6 ~ 32)으로 나눈다(한글 한 자는 2)."""
    weights = [6.0] * len(header)
    for row in [header, *rows]:
        for j, text in enumerate(row):
            if any(isinstance(t, Img) for t in parse_inline(text)):
                w = 32.0
            else:
                w = float(min(32, 2 + _disp_len(plain(parse_inline(text, images=False)).strip())))
            weights[j] = max(weights[j], w)
    total = sum(weights)
    return [w / total for w in weights]


class Renderer:
    """블록 → docx. 그림을 넣을 때마다 센다(넣은 것 · 표 칸 안 · 자리표) — 저장 뒤 docx 를 다시 세어 견준다."""

    def __init__(self, doc, pictures: dict, max_width_cm: float, font: str):
        from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
        self.doc, self.pictures, self.font = doc, pictures, font
        self.align = {"left": AL.LEFT, "center": AL.CENTER, "right": AL.RIGHT}
        self.text_w = int(TEXT_W_CM * EMU_PER_CM)
        self.max_w = int(min(max_width_cm, TEXT_W_CM) * EMU_PER_CM)
        self.max_h = int(MAX_H_CM * EMU_PER_CM)
        self.styles = {s.name for s in doc.styles}
        self.placed = self.in_cells = self.placeholders = 0

    def render(self, blocks: list[Block], indent: int = 0) -> None:
        prev = None
        for b in blocks:
            if b.kind == prev == "table":
                self.doc.add_paragraph()                     # 붙은 두 표를 Word 가 한 표로 합쳐 보인다(반대 검토 K7)
            getattr(self, "_" + b.kind)(b, indent)
            prev = b.kind

    # 블록
    def _para(self, b, indent):
        p = self._p(indent)
        self._runs(p, parse_inline(b.text, b.line), self.text_w - indent)

    def _heading(self, b, indent):
        p = self.doc.add_paragraph(style=f"Heading {b.level}")
        self._runs(p, parse_inline(b.text, b.line), self.text_w)

    def _figure(self, b, indent):
        p = self._p(indent)
        p.alignment = self.align["center"]
        p.paragraph_format.keep_with_next = True
        self._picture(p, b.img, min(self.max_w, self.text_w - indent))
        self._caption(lambda: self._p(indent), b.img)

    def _list(self, b, indent):
        from docx.shared import Emu
        count, kind = {}, {}
        for it in b.items:
            if it.level == 0:
                count.pop(1, None)
                kind.pop(1, None)
            if it.ordered:
                count[it.level] = count[it.level] + 1 if kind.get(it.level) == "ordered" else it.number
                marker = f"{count[it.level]}."
            else:
                marker = "•" if it.level == 0 else "◦"
            kind[it.level] = "ordered" if it.ordered else "bullet"
            if it.task is not None:
                marker += " " + ("☑" if it.task else "☐")
            left = indent + int(INDENT_CM * (it.level + 1) * EMU_PER_CM)
            for k, (line, text) in enumerate(it.paras):
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Emu(left)
                if k == 0:
                    p.paragraph_format.first_line_indent = Emu(-int(0.5 * EMU_PER_CM))
                    p.add_run(marker + "\t")
                self._runs(p, parse_inline(text.rstrip(), line), self.text_w - left)

    def _table(self, b, indent):
        from docx.shared import Emu
        widths = [int((self.text_w - indent) * s) for s in column_shares(b.header, b.rows)]
        t = self.doc.add_table(rows=1 + len(b.rows), cols=len(widths))
        if "Table Grid" in self.styles:
            t.style = "Table Grid"
        t.autofit = False
        for j, w in enumerate(widths):
            t.columns[j].width = Emu(w)
        lines = [b.line, *b.row_lines]
        for r, cells in enumerate([b.header, *b.rows]):
            row = t.rows[r].cells
            for j, text in enumerate(cells):
                row[j].width = Emu(widths[j])
                self._cell(row[j], text, lines[r], b.aligns[j], widths[j], r == 0)

    def _quote(self, b, indent):
        self.render(b.blocks, indent + int(INDENT_CM * EMU_PER_CM))

    def _code(self, b, indent):
        from docx.shared import Pt
        p = self._p(indent + int(0.5 * EMU_PER_CM))
        r = p.add_run(b.text)                                # \n 은 줄바꿈으로 들어간다
        self._code_font(r)
        r.font.size = Pt(9)

    def _hr(self, b, indent):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        p = self.doc.add_paragraph()
        bdr, bottom = OxmlElement("w:pBdr"), OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "auto")):
            bottom.set(qn(k), v)
        bdr.append(bottom)
        p._p.get_or_add_pPr().append(bdr)

    # 칸 · 글 · 그림
    def _cell(self, cell, text, line, align, col_w, header):
        """표 칸 — 그림은 제 문단(가운데, 열 폭)과 그 아래 캡션 문단으로, 앞뒤 글은 제 문단으로 둔다. 한 칸에 그림 여럿도 차례대로."""
        used = [0]

        def para(al):
            p = cell.paragraphs[0] if used[0] == 0 else cell.add_paragraph()
            used[0] += 1
            p.alignment = al
            return p

        seg: list = []

        def put_text():
            while seg and (seg[0] is BREAK or (isinstance(seg[0], Text) and not seg[0].text.strip())):
                seg.pop(0)
            while seg and (seg[-1] is BREAK or (isinstance(seg[-1], Text) and not seg[-1].text.strip())):
                seg.pop()
            if seg:                                          # 그림 옆에 붙어 있던 빈칸은 떼어 낸다
                seg[0].text = seg[0].text.lstrip()
                seg[-1].text = seg[-1].text.rstrip()
                self._runs(para(self.align[align]), list(seg), col_w)
            seg.clear()

        img_w = max(min(self.max_w, col_w - int(CELL_PAD_CM * EMU_PER_CM)), int(0.5 * EMU_PER_CM))
        for tok in parse_inline(text, line, bold=header):
            if isinstance(tok, Img):
                put_text()
                self._picture(para(self.align["center"]), tok, img_w, in_cell=True)
                self._caption(lambda: para(self.align["center"]), tok)
            else:
                seg.append(tok)
        put_text()

    def _p(self, indent):
        from docx.shared import Emu
        p = self.doc.add_paragraph()
        if indent:
            p.paragraph_format.left_indent = Emu(indent)
        return p

    def _caption(self, new_p, img):
        """캡션이 있으면 그림 아래 문단 하나(Caption 꼴 · 가운데)."""
        cap = caption_of(img)
        if not cap:
            return
        p = new_p()
        if "Caption" in self.styles:
            p.style = "Caption"
        p.alignment = self.align["center"]
        p.add_run(cap)

    def _code_font(self, r):
        from docx.oxml.ns import qn
        r.font.name = "Consolas"
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), self.font)

    def _runs(self, p, toks, avail):
        for t in toks:
            if t is BREAK:
                p.add_run().add_break()
            elif isinstance(t, Img):
                self._picture(p, t, min(self.max_w, avail), natural=True)
            else:
                r = p.add_run(t.text)
                if t.bold:
                    r.bold = True
                if t.italic:
                    r.italic = True
                if t.strike:
                    r.font.strike = True
                if t.code:
                    self._code_font(r)

    def _picture(self, p, img: Img, width: int, natural: bool = False, in_cell: bool = False):
        """그림 하나를 문단 p 에 — width 폭(natural 이면 제 크기와 그 폭 중 작은 것), 비율 유지, 높이 상한. 못 넣은 그림은 빨간 자리표."""
        from docx.shared import Emu, RGBColor
        pic = self.pictures.get(img.src)
        if pic is None:
            r = p.add_run(f"[그림 없음: {img.src}]")
            r.bold = True
            r.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
            self.placeholders += 1
            return
        w_px, h_px = pic.size
        nat = int(w_px / NATURAL_DPI * EMU_PER_INCH)
        # 줄 안은 제 크기까지, 홀로 선 줄 · 표 칸은 제 크기의 두 배까지 — 16 px 아이콘이 칸 폭 14 cm 로 33배 커졌다(반대 검토 K10)
        width = min(width, nat if natural else 2 * nat)
        width = max(width, int(0.3 * EMU_PER_CM))
        height = int(width * h_px / w_px)
        if height > self.max_h:
            width, height = int(width * self.max_h / height), self.max_h
        shape = p.add_run().add_picture(io.BytesIO(pic.blob), width=Emu(width), height=Emu(height))
        shape._inline.docPr.set("descr", caption_of(img))
        self.placed += 1
        self.in_cells += 1 if in_cell else 0


# ── 저장 뒤 대조 ──────────────────────────────────────────────────────────────────────────────────────
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_XML_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def docx_counts(path: Path | str) -> tuple[int, int]:
    """저장한 docx 를 zip 으로 다시 열어 word/document.xml 의 <w:drawing> 수와 그 가운데 <w:tc>(표 칸) 안의 수를 센다."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    total = in_cells = 0
    stack = [(root, False)]
    while stack:
        el, in_tc = stack.pop()
        for ch in el:
            if ch.tag == _W + "drawing":
                total += 1
                in_cells += 1 if in_tc else 0
            stack.append((ch, in_tc or ch.tag == _W + "tc"))
    return total, in_cells


def check_counts(marks: int, placed: int, placeholders: int, in_cells: int, drawings: int, drawings_in_cells: int) -> list[str]:
    """어긋남 — 비면 맞다. md 표기 = 넣은 그림 + 자리표, docx 그림 = 넣은 그림, docx 표 칸 안 = 표 칸에 넣은 그림."""
    errs = []
    if marks != placed + placeholders:
        errs.append(f"md 의 그림 표기 {marks} 와 넣은 그림 {placed} + 자리표 {placeholders} 가 다르다(변환기가 읽지 못한 표기가 있다)")
    if drawings != placed:
        errs.append(f"docx 의 그림 {drawings} 와 넣은 그림 {placed} 가 다르다")
    if drawings_in_cells != in_cells:
        errs.append(f"docx 표 칸 안 그림 {drawings_in_cells} 와 표 칸에 넣은 그림 {in_cells} 가 다르다")
    return errs


# ── 실행 ──────────────────────────────────────────────────────────────────────────────────────────────
class _Args(argparse.ArgumentParser):
    def error(self, message):                                # 인자 오류는 1 — 2 는 '그림이 없다' 다
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: 인자 오류 - {message}\n")


def _say(msg: str, err: bool = False) -> None:
    print(msg, file=sys.stderr if err else sys.stdout, flush=True)


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")                           # 메모장의 ANSI 저장 — 못 읽으면 UnicodeDecodeError 가 올라간다
        _say("md 가 UTF-8 이 아니어서 cp949 로 읽었다", err=True)
        return text


def main(argv: list[str] | None = None) -> int:
    for st in (sys.stdout, sys.stderr):                      # cp949 콘솔에서도 죽지 않게
        try:
            st.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = _Args(prog="hwax-md2docx", description="HWAX 보고서 md 를 그림이 든 docx 로 바꾼다(표 칸 안 그림 포함).")
    ap.add_argument("input", help="보고서 md 파일")
    ap.add_argument("-o", "--output", help="쓸 docx(기본은 md 와 같은 이름의 .docx)")
    ap.add_argument("--fig-dir", action="append", default=[], metavar="DIR", help="그림 파일을 찾을 폴더(여러 번 줄 수 있다)")
    ap.add_argument("--allow-missing", action="store_true", help="못 넣은 그림을 빨간 자리표로 두고 docx 를 쓴다")
    ap.add_argument("--max-width-cm", type=float, default=16.0, help="그림 폭 상한(cm, 기본 16)")
    ap.add_argument("--font", default="맑은 고딕", help='본문 글꼴(동아시아 글꼴, 기본 "맑은 고딕")')
    a = ap.parse_args(argv)
    if not a.max_width_cm > 0:
        ap.error("--max-width-cm 은 0 보다 커야 한다")
    try:
        import docx  # noqa: F401
    except ImportError:
        _say("python-docx 가 없다 - pip install python-docx", err=True)
        return EXIT_USAGE
    md = Path(a.input)
    try:
        text = _decode(md.read_bytes()).replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeDecodeError) as exc:
        _say(f"md 를 읽지 못했다 - {md} ({getattr(exc, 'strerror', None) or type(exc).__name__})", err=True)
        return EXIT_USAGE
    text, bad = _XML_BAD.subn("", text)
    if bad:                                                  # lxml 이 docx 에 못 싣는다(반대 검토 K9 — 그대로 두면 traceback 으로 죽었다)
        _say(f"XML 에 못 싣는 제어 문자 {bad}개를 뺐다", err=True)
    text = drop_comments(text)
    out = Path(a.output) if a.output else md.with_suffix(".docx")
    if out.resolve() == md.resolve():
        _say("출력이 md 자신이다 - -o 로 .docx 를 준다", err=True)
        return EXIT_USAGE
    fig_dirs = [Path(d) for d in a.fig_dir]
    bad = [str(d) for d in fig_dirs if not d.is_dir()]
    if bad:
        _say(f"--fig-dir 폴더가 없다 - {' · '.join(bad)}", err=True)
        return EXIT_USAGE

    blocks = parse_blocks(text.split("\n"))
    marks, broken = count_marks(text)
    resolver = Resolver(md.resolve().parent, fig_dirs)
    pictures: dict = {}
    reasons: dict = {}
    problems = []
    for img in collect_images(blocks):
        if img.src not in pictures:
            try:
                pictures[img.src] = resolver.resolve(img.src)
            except Problem as exc:
                pictures[img.src], reasons[img.src] = None, str(exc)
        if pictures[img.src] is None:
            problems.append((img.line, img.src, reasons[img.src]))
    problems += broken
    problems.sort(key=lambda x: x[0])
    for note in resolver.notes:
        _say(note)
    if problems:
        head = (f"그림 {len(problems)}개를 넣지 못했다 - 빨간 자리표 [그림 없음: …] 로 두고 docx 를 쓴다" if a.allow_missing else
                f"그림 {len(problems)}개를 넣지 못해 docx 를 쓰지 않았다(있던 docx 는 그대로다 · --allow-missing 이면 자리표로 쓴다)")
        _say(head, err=True)
        for line, src, why in problems:
            _say(f"  줄 {line}: {src} - {why}", err=True)
        if not a.allow_missing:
            return EXIT_MISSING

    doc = new_document(a.font)
    r = Renderer(doc, pictures, a.max_width_cm, a.font)
    r.render(blocks)
    tmp = out.with_name(out.name + ".part")
    try:
        doc.save(str(tmp))
        os.replace(tmp, out)
    except OSError as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        _say(f"docx 를 저장하지 못했다({exc.strerror or type(exc).__name__}) - Word 에서 열려 있으면 닫고 다시 돌린다 · {out}", err=True)
        return EXIT_USAGE
    drawings, drawings_in_cells = docx_counts(out)
    _say(f"docx 를 썼다 - {out}")
    _say(f"그림 표기 {len(marks)} · docx 그림 {drawings} · 표 칸 안 {drawings_in_cells}"
         + (f" · 그림 없음 {r.placeholders}" if r.placeholders else ""))
    errs = check_counts(len(marks), r.placed, r.placeholders, r.in_cells, drawings, drawings_in_cells)
    if errs:
        _say("그림 수가 맞지 않는다 - 이 docx 에는 빠진 그림이 있다(쓰지 말고 md 를 고친다)", err=True)
        for e in errs:
            _say(f"  {e}", err=True)
        seen = {i.line for i in collect_images(blocks)}
        for line, mk in marks:
            if line not in seen:
                _say(f"  줄 {line}: {mk.src} - 변환기가 이 줄의 그림 표기를 넣지 않았다", err=True)
        return EXIT_MISMATCH
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
