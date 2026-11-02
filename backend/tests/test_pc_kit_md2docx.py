# PC 키트 변환기(infra/pc-kit/hwax-md2docx.py)가 표 칸 · 문단 · 홀로 선 줄의 그림을 docx 에 빠짐없이 넣는지 보는 시험
"""사용자 보고(2026-11-02 KST '표칸그림 필요해') — 현장 변환기(md2docx_z.py)는 줄 하나에 홀로 선 그림 표기만 그림으로 넣고 표 칸 · 문단 안
그림은 글자로 남겼으며, 없는 파일은 '[그림 없음]' 으로 넘기고 수를 대조하지 않았다. 이 시험은 그 셋을 막는 것을 본다 — 표 칸 그림은
<w:tc> 안의 <w:drawing>, 빠진 그림은 종료 2 와 docx 없음, 저장 뒤 수 대조(종료 3). 변환기는 PC 에서 혼자 도는 파일이라 경로로 읽는다."""
import http.server
import importlib.util
import os
import struct
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra" / "pc-kit" / "hwax-md2docx.py"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
REF = "fig_Ab3_dE-fGh1JkLmN0pQrSt"          # 게이트웨이 ref 꼴 — fig_ + 22자
CM = 360000                                 # EMU


def _load():
    spec = importlib.util.spec_from_file_location("hwax_md2docx_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # infra/pc-kit 에 __pycache__ 를 남기지 않는다(게이트웨이가 내려주는 폴더)
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


md2 = _load()


def png(w: int, h: int, rgb=(200, 30, 30)) -> bytes:
    """Pillow 없이 짓는 진짜 PNG(python-docx 가 머리에서 크기를 읽는다)."""
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


A_PNG, B_PNG, C_PNG = png(800, 600), png(300, 600), png(400, 300)


@pytest.fixture(autouse=True)
def _no_gateway_env(monkeypatch):
    """박스 · 개발자 셸의 PAT 환경으로 시험이 게이트웨이를 부르지 않게 — 받기를 보는 시험만 제 가짜 서버 주소를 준다."""
    for k in ("HWAX_GATEWAY_PAT", "HWAX_PORTAL_BASE"):
        monkeypatch.delenv(k, raising=False)


def _md(tmp_path: Path, text: str, files=(("a.png", A_PNG), ("b.png", B_PNG), ("c.png", C_PNG)), name="보고서.md") -> Path:
    for fname, blob in files:
        (tmp_path / fname).write_bytes(blob)
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _convert(tmp_path, text, *args, files=(("a.png", A_PNG), ("b.png", B_PNG), ("c.png", C_PNG))):
    p = _md(tmp_path, text, files)
    return md2.main([str(p), *args]), p.with_suffix(".docx")


def _cli(md: Path, *args, env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("HWAX_")}
    e.update(env or {}, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(md), *args], capture_output=True, text=True, encoding="utf-8",
                          env=e, timeout=120)


def _root(docx: Path):
    with zipfile.ZipFile(docx) as z:
        return ET.fromstring(z.read("word/document.xml"))


def _parents(root):
    return {c: p for p in root.iter() for c in p}


def _in_tc(el, parents) -> bool:
    while el in parents:
        el = parents[el]
        if el.tag == W + "tc":
            return True
    return False


def _ptext(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _style(p) -> str | None:
    s = p.find(f"{W}pPr/{W}pStyle")
    return None if s is None else s.get(W + "val")


def _extent(drawing) -> tuple[int, int]:
    e = drawing.find(f".//{WP}extent")
    return int(e.get("cx")), int(e.get("cy"))


# ── 표 칸 ────────────────────────────────────────────────────────────────────────────────────────────
def test_표_칸_그림은_w_tc_안의_w_drawing_이고_그_열_몫의_폭에_캡션이_같은_칸에_든다(tmp_path):
    rc, docx = _convert(tmp_path, "| 항목 | 그림 |\n|---|---|\n| 응력 | ![최대 응력](a.png) |\n")
    assert rc == 0
    root = _root(docx)
    parents = _parents(root)
    (d,) = list(root.iter(W + "drawing"))
    assert _in_tc(d, parents), "현장 변환기는 표 칸 그림을 글자로 남겼다 — 그림이 칸 안에 들어야 한다"
    tc = d
    while tc.tag != W + "tc":
        tc = parents[tc]
    paras = tc.findall(W + "p")
    assert [_ptext(p) for p in paras] == ["", "최대 응력"] and _style(paras[1]) == "Caption", "캡션은 그림 아래 같은 칸이다"
    # 폭 — 그 열의 몫(본문 17 cm 를 열 무게로 나눈 것)에서 칸 여백을 뺀 만큼, 비율 유지
    col_w = int(tc.find(f"{W}tcPr/{W}tcW").get(W + "w")) * 635          # twip → EMU
    cx, cy = _extent(d)
    assert col_w - int(0.5 * CM) < cx <= col_w - int(0.39 * CM) and cx < int(16 * CM), (cx, col_w)
    assert abs(cy / cx - 600 / 800) < 0.01
    grid = [int(g.get(W + "w")) for g in root.iter(W + "gridCol")]
    assert len(grid) == 2 and grid[1] > 3 * grid[0], "그림 열이 짧은 글 열보다 넓다"
    assert "![" not in "".join(_ptext(p) for p in root.iter(W + "p")), "표기 글자가 남지 않는다"


def test_한_칸에_그림_여럿은_차례대로_각각의_캡션과_든다(tmp_path):
    rc, docx = _convert(tmp_path, "| 두 장 | 설명 |\n|---|---|\n| ![위](a.png) ![아래](c.png) | 둘 |\n")
    assert rc == 0
    root = _root(docx)
    (tc,) = [tc for tc in root.iter(W + "tc") if list(tc.iter(W + "drawing"))]
    assert len(list(tc.iter(W + "drawing"))) == 2
    seq = [("IMG" if list(p.iter(W + "drawing")) else _ptext(p)) for p in tc.findall(W + "p")]
    assert seq == ["IMG", "위", "IMG", "아래"], seq
    (d1, d2) = list(tc.iter(W + "drawing"))
    assert _extent(d1)[0] == _extent(d2)[0], "같은 칸의 그림은 같은 열 폭이다"
    assert abs(_extent(d2)[1] / _extent(d2)[0] - 0.75) < 0.01
    # 세로로 긴 그림은 높이 상한(쪽 높이의 8할)에 걸려 폭이 줄되 비율은 그대로다 — 한 쪽을 넘지 않는다
    rc, docx = _convert(tmp_path, "| 세로 |\n|---|\n| ![긴](b.png) |\n")
    cx, cy = _extent(next(_root(docx).iter(W + "drawing")))
    assert rc == 0 and cy == int(md2.MAX_H_CM * CM) and abs(cy / cx - 2.0) < 0.01


def test_글과_그림이_섞인_칸은_앞뒤_글을_그대로_둔다(tmp_path):
    rc, docx = _convert(tmp_path, "| 결과 |\n|---|\n| 최대 **120** MPa ![변형](a.png) 아래 설명 |\n")
    assert rc == 0
    root = _root(docx)
    (tc,) = [tc for tc in root.iter(W + "tc") if list(tc.iter(W + "drawing"))]
    seq = [("IMG" if list(p.iter(W + "drawing")) else _ptext(p)) for p in tc.findall(W + "p")]
    assert seq == ["최대 120 MPa", "IMG", "변형", "아래 설명"], seq
    bold = [r for r in tc.iter(W + "r") if r.find(f"{W}rPr/{W}b") is not None]
    assert [_ptext(r) for r in bold] == ["120"], "칸 안의 굵게도 남는다"


def test_이스케이프한_파이프는_칸_안의_글이다(tmp_path):
    assert md2.split_table_row(r"| a \| b | c |") == ["a | b", "c"]
    assert md2.split_table_row("a | b") == ["a", "b"] and md2.split_table_row(r"| x\|y |") == ["x|y"]
    rc, docx = _convert(tmp_path, "| 식 | 값 |\n|---|---|\n| a \\| b | `c \\| d` |\n")
    assert rc == 0
    cells = [_ptext(tc) for tc in _root(docx).iter(W + "tc")]
    assert cells == ["식", "값", "a | b", "c | d"], cells


# ── 홀로 선 줄 · 줄 안 ──────────────────────────────────────────────────────────────────────────────────
def test_홀로_선_그림은_본문_폭_그림과_그_아래_캡션_문단이다(tmp_path):
    rc, docx = _convert(tmp_path, "# 제목\n\n![응력 분포 — 전체](a.png)\n\n본문.\n")
    assert rc == 0
    body = _root(docx).find(W + "body")
    paras = body.findall(W + "p")
    i = next(k for k, p in enumerate(paras) if list(p.iter(W + "drawing")))
    (d,) = list(paras[i].iter(W + "drawing"))
    assert _extent(d) == (16 * CM, 12 * CM), "본문 폭(17 cm)을 --max-width-cm 16 이 막는다 · 비율 유지"
    assert _ptext(paras[i + 1]) == "응력 분포 — 전체" and _style(paras[i + 1]) == "Caption"
    assert paras[i].find(f"{W}pPr/{W}jc").get(W + "val") == "center"
    assert d.find(f".//{WP}docPr").get("descr") == "응력 분포 — 전체", "대체 글도 단다"
    rc, docx = _convert(tmp_path, "![작게](a.png)\n", "--max-width-cm", "8")
    assert rc == 0 and _extent(next(_root(docx).iter(W + "drawing"))) == (8 * CM, 6 * CM)


def test_문단_목록_안_그림은_같은_문단의_줄_안_그림이다(tmp_path):
    rc, docx = _convert(tmp_path, "앞 글 ![아이콘](b.png) 뒤 글\n\n- 항목 ![목록 그림](b.png)\n")
    assert rc == 0
    paras = [p for p in _root(docx).iter(W + "p") if list(p.iter(W + "drawing"))]
    assert len(paras) == 2
    assert _ptext(paras[0]) == "앞 글  뒤 글" and _ptext(paras[1]).endswith("항목 ")
    kids = [("IMG" if list(r.iter(W + "drawing")) else _ptext(r)) for r in paras[0].findall(W + "r")]
    assert kids == ["앞 글 ", "IMG", " 뒤 글"], kids
    cx, cy = _extent(next(paras[0].iter(W + "drawing")))
    assert cx == round(300 / 96 * 914400) and cy == 2 * cx, "줄 안 그림은 제 크기(96 dpi)다"
    assert not [p for p in _root(docx).iter(W + "p") if _style(p) == "Caption"], "줄 안 그림은 캡션 문단을 따로 두지 않는다"


# ── 그림 주소 ────────────────────────────────────────────────────────────────────────────────────────
def test_Windows_경로_꼴을_가른다():
    c = md2.classify_src
    assert c("H:/a/b.png") == ("windows", "H:/a/b.png") and c("H:\\a\\b.png")[0] == "windows"
    assert c("\\\\srv\\share\\a.png")[0] == "unc" and c("//srv/share/a.png")[0] == "unc"
    assert c("/abs/a.png")[0] == "posix" and c("figs\\a.png")[0] == "relative" and c("a b.png")[0] == "relative"
    assert c(REF) == ("ref", REF) and c("fig:" + REF) == ("ref", REF) and c("fig_short.png")[0] == "relative"
    assert c("https://x/a.png")[0] == "url"
    win, rep = PureWindowsPath("C:/rep"), PurePosixPath("/rep")
    sp = md2.src_path
    assert sp("H:/a/b.png", win, True) == PureWindowsPath("H:/a/b.png") == sp("H:\\a\\b.png", win, True)
    assert sp("\\\\srv\\share\\a.png", win, True) == PureWindowsPath("//srv/share/a.png") == sp("//srv/share/a.png", win, True)
    assert sp("figs\\a.png", win, True) == PureWindowsPath("C:/rep/figs/a.png") == sp("figs/a.png", win, True)
    assert sp("figs\\a.png", rep, False) == PurePosixPath("/rep/figs/a.png")
    assert sp("H:/a/b.png", rep, False) is None and sp("\\\\srv\\s\\a.png", rep, False) is None, "리눅스에서는 닿을 수 없는 자리"
    assert sp(REF, win, True) is None
    # 표기 안의 경로 — 역슬래시는 글자 그대로, 빈칸은 <…> 로도 · 그냥도, 제목은 뗀다
    m = md2.match_bracket(r"![a](H:\내 문서\figs\a.png)", 0)
    assert (m.alt, m.src, m.title) == ("a", r"H:\내 문서\figs\a.png", "")
    m = md2.match_bracket(r'![a](<H:\my figs\(1).png> "제목")', 0)
    assert (m.src, m.title) == (r"H:\my figs\(1).png", "제목")
    assert md2.match_bracket("![a](fig(1).png 'title')", 0).src == "fig(1).png"
    assert md2.match_bracket(r"![a](\\srv\share\a.png)", 0).src == r"\\srv\share\a.png"


def test_ref_는_md_폴더나_fig_dir_의_이름에_ref_가_든_파일로_찾는다(tmp_path, capsys):
    figs = tmp_path / "받은 그림"
    figs.mkdir()
    (figs / f"render_3d-{REF}.png").write_bytes(A_PNG)            # figure_get 의 curl 이 받는 이름
    rc, docx = _convert(tmp_path, f"| 칸 |\n|---|\n| ![칸](fig:{REF}) |\n\n![홀로]({REF})\n", "--fig-dir", str(figs), files=())
    assert rc == 0, capsys.readouterr().err
    root = _root(docx)
    assert len(list(root.iter(W + "drawing"))) == 2
    assert "그림 표기 2 · docx 그림 2 · 표 칸 안 1" in capsys.readouterr().out
    rc, _ = _convert(tmp_path, f"![홀로]({REF})\n", files=())                      # --fig-dir 없이는 못 찾는다(md 폴더에 없다)
    assert rc == 2 and "figure_get" in capsys.readouterr().err


class _FakeGateway:
    """게이트웨이 /mcp-gw/fig/<ref> 가짜 — 받은 경로 · Authorization 을 적는다. 남는 프로세스 · 스레드가 없게 with 로 쓴다."""

    def __init__(self, routes):
        self.seen, self.routes = [], routes
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.seen.append((self.path, self.headers.get("Authorization")))
                status, headers, body = outer.routes.get(self.path, (404, {}, b'{"error":"not found"}'))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v.replace("{port}", str(outer.port)))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()
        self.thread.join(timeout=5)


def test_ref_는_PAT_로_게이트웨이에서_받아_md_옆에_두고_PAT_는_어디에도_찍지_않는다(tmp_path):
    pat = "hwax-pat-SECRET-0123456789abcdef"
    gone, moved = "fig_" + "G" * 22, "fig_" + "M" * 22
    routes = {f"/mcp-gw/fig/{REF}": (200, {"Content-Type": "image/png"}, A_PNG),
              f"/mcp-gw/fig/{moved}": (302, {"Location": "http://127.0.0.1:{port}/steal"}, b"")}
    with _FakeGateway(routes) as gwy:
        env = {"HWAX_GATEWAY_PAT": pat, "HWAX_PORTAL_BASE": f"http://127.0.0.1:{gwy.port}"}
        md = _md(tmp_path, f"| 칸 |\n|---|\n| ![받은 그림]({REF}) |\n", files=())
        r = _cli(md, env=env)
        assert r.returncode == 0, r.stderr
        assert gwy.seen == [(f"/mcp-gw/fig/{REF}", f"Bearer {pat}")], "그 사람의 PAT 를 Authorization 으로만 싣는다"
        assert (tmp_path / f"{REF}.png").read_bytes() == A_PNG, "md 옆에 두어 다음엔 파일로 찾는다"
        assert "그림 표기 1 · docx 그림 1 · 표 칸 안 1" in r.stdout
        assert pat not in r.stdout + r.stderr
        # 실패 — 없는 그림(404) · 다른 주소로 넘김(302 — 따라가지 않아 토큰이 /steal 로 가지 않는다)
        md = _md(tmp_path, f"![없음]({gone})\n\n![넘김]({moved})\n", files=(), name="실패.md")
        gwy.seen.clear()
        r = _cli(md, env=env)
        assert r.returncode == 2 and not md.with_suffix(".docx").exists()
        assert "HTTP 404" in r.stderr and "HTTP 302" in r.stderr and r.stderr.count("figure_get") >= 2
        assert sorted(p for p, _a in gwy.seen) == sorted([f"/mcp-gw/fig/{gone}", f"/mcp-gw/fig/{moved}"]), "넘김을 따라가지 않는다"
        assert pat not in r.stdout + r.stderr
    # 받을 곳을 모르면 받지 않고 figure_get 을 말한다(주소 · 토큰 하나라도 비면)
    r = _cli(_md(tmp_path, f"![x]({gone})\n", files=(), name="주소없음.md"), env={"HWAX_GATEWAY_PAT": pat})
    assert r.returncode == 2 and "figure_get" in r.stderr and pat not in r.stdout + r.stderr


# ── 빠진 그림 · 수 대조 ─────────────────────────────────────────────────────────────────────────────
def test_빠진_그림은_종료_2_로_줄마다_알리고_docx_를_쓰지_않는다(tmp_path):
    md = _md(tmp_path, "# 제목\n\n![없음 하나](nope.png)\n\n| a |\n|---|\n| ![칸 안 없음](gone.png) |\n\n![있음](a.png)\n")
    r = _cli(md)
    assert r.returncode == 2
    assert "줄 3: nope.png" in r.stderr and "줄 7: gone.png" in r.stderr and "그림 2개" in r.stderr
    assert not md.with_suffix(".docx").exists() and not list(tmp_path.glob("*.docx*")), "반쪽 docx 도 남기지 않는다"


def test_allow_missing_은_빨간_자리표를_쓰고_그래도_알린다(tmp_path, capsys):
    rc, docx = _convert(tmp_path, "| a |\n|---|\n| ![칸 안 없음](gone.png) |\n\n![있음](a.png)\n", "--allow-missing")
    cap = capsys.readouterr()
    assert rc == 0 and "줄 3: gone.png" in cap.err
    assert "그림 표기 2 · docx 그림 1 · 표 칸 안 0 · 그림 없음 1" in cap.out
    root = _root(docx)
    (run,) = [r for r in root.iter(W + "r") if _ptext(r) == "[그림 없음: gone.png]"]
    assert run.find(f"{W}rPr/{W}color").get(W + "val") == "FF0000" and run.find(f"{W}rPr/{W}b") is not None


def test_저장_뒤_수가_어긋나면_종료_3(tmp_path, capsys, monkeypatch):
    # 대조기 — md 표기 = 넣은 것 + 자리표, docx 그림 = 넣은 것, 표 칸 안 = 표 칸에 넣은 것
    assert md2.check_counts(3, 3, 0, 1, 3, 1) == []
    assert md2.check_counts(3, 3, 0, 1, 2, 1) and md2.check_counts(3, 2, 0, 1, 2, 1) and md2.check_counts(3, 3, 0, 1, 3, 0)
    assert md2.check_counts(3, 2, 1, 0, 2, 0) == [], "자리표는 표기 수에 든다"
    # docx 를 다시 열어 세는 쪽 — 표 칸 안을 따로 센다
    rc, docx = _convert(tmp_path, "| a |\n|---|\n| ![x](a.png) |\n\n![y](b.png)\n")
    assert rc == 0 and md2.docx_counts(docx) == (2, 1)
    capsys.readouterr()
    # 렌더러가 그림 하나를 말없이 흘리면(현장 변환기의 표 칸 꼴) 저장 뒤 대조가 잡는다
    real = md2.Renderer._picture

    def drop_in_cells(self, p, img, width, natural=False, in_cell=False):
        if not in_cell:
            real(self, p, img, width, natural, in_cell)
    monkeypatch.setattr(md2.Renderer, "_picture", drop_in_cells)
    rc, docx = _convert(tmp_path, "| a |\n|---|\n| ![x](a.png) |\n\n![y](b.png)\n")
    err = capsys.readouterr().err
    assert rc == 3 and "그림 수가 맞지 않는다" in err and "md 의 그림 표기 2" in err


def test_svg_는_cairosvg_가_없으면_webp_는_Pillow_가_없으면_분명히_실패한다(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "cairosvg", None)               # import 가 ImportError 를 낸다(깔려 있는 박스에서도)
    monkeypatch.setitem(sys.modules, "PIL", None)
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'
    webp = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\x00" * 8
    rc, docx = _convert(tmp_path, "![벡터](v.svg)\n\n![웹피](w.webp)\n", files=(("v.svg", svg), ("w.webp", webp)))
    err = capsys.readouterr().err
    assert rc == 2 and not docx.exists()
    assert "줄 1: v.svg - svg 그림은 cairosvg 가 있어야" in err and "pip install cairosvg" in err
    assert "줄 3: w.webp - webp 그림은 Pillow 가 있어야" in err
    # 확장자가 아니라 바이트로 가린다 — svg 를 .png 라고 이름 붙여도 svg 다
    rc, _ = _convert(tmp_path, "![이름만 png](fake.png)\n", files=(("fake.png", svg),))
    assert rc == 2 and "cairosvg" in capsys.readouterr().err


# ── 한글 · 글꼴 · 코드 ─────────────────────────────────────────────────────────────────────────────────
def test_한글이_그대로_남고_본문_글꼴은_주어진_동아시아_글꼴이다(tmp_path):
    md = _md(tmp_path, "# 낙하 해석 보고서\n\n응력이 **집중**된 곳은 모서리다.\n\n| 항목 | 값 |\n|---|---|\n| 최대 응력 | 120 MPa |\n\n"
                       "```\n![코드 안 표기](없음.png)\n```\n")
    r = _cli(md, "--font", "나눔고딕")
    assert r.returncode == 0, r.stderr
    text = "".join(_ptext(p) for p in _root(md.with_suffix(".docx")).iter(W + "p"))
    for s in ("낙하 해석 보고서", "응력이 집중된 곳은 모서리다.", "최대 응력", "120 MPa", "![코드 안 표기](없음.png)"):
        assert s in text, s
    assert "그림 표기 0 · docx 그림 0 · 표 칸 안 0" in r.stdout, "울타리 코드 안의 표기는 그림이 아니다"
    with zipfile.ZipFile(md.with_suffix(".docx")) as z:
        styles = ET.fromstring(z.read("word/styles.xml"))
    normal = next(s for s in styles.iter(W + "style") if s.get(W + "styleId") == "Normal")
    assert normal.find(f"{W}rPr/{W}rFonts").get(W + "eastAsia") == "나눔고딕"
    sect = _root(md.with_suffix(".docx")).find(f"{W}body/{W}sectPr/{W}pgSz")
    assert (int(sect.get(W + "w")), int(sect.get(W + "h"))) == (11906, 16838), "A4"


def test_인자_오류는_종료_1_이다(tmp_path):
    r = _cli(_md(tmp_path, "글\n"), "--max-width-cm", "0")
    assert r.returncode == 1
    r = _cli(tmp_path / "없는.md")
    assert r.returncode == 1 and "md 를 읽지 못했다" in r.stderr
