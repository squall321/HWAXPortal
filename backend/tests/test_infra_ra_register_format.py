# RA 형식 등록 명령(infra/scripts/ra-register-format.py)의 시험 — 미리보기가 기본 · 등록과 쓰기 시작은 따로 · 두 리포가 같은 박스 파일을 읽는다
"""docs/leftovers-1121 L21-6 ①(사용자 결정 2026-11-21 — 스스로 등록하는 길을 지어 두되 기본은 끈다). dev 에는 RA 가 떠 있지 않아 RA MCP
`register_report_format` 의 답 꼴(v0.186.3 `mcp_server/server.py`)을 그대로 흉내 낸다. 고정하는 것.

  · 인자 없이는 미리보기뿐이다 — RA 에 쓰지 않고 박스 파일도 안 만든다.
  · `--apply` 는 등록만, `--use` 가 있어야 박스 파일에 적는다. 쓸 판을 모르면(등록 전) 적지 않는다.
  · RA 의 거절(남의 틀 · 권한)은 까닭과 함께 끝 코드 3 이다.
  · 형식 파일의 블록 id 가 엔진이 채우는 칸과 같다. 블록 종류 · props 가 RA 위젯 등록부에 있다(형제 RA 리포가 있을 때).
  · 에이전트 서버와 게이트웨이가 같은 기본값 · 같은 파일 이름을 쓴다.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ra_register_format", ROOT / "infra" / "scripts" / "ra-register-format.py")
reg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reg)

FMT = reg.load_format("deliberation")
AGENT = ROOT.parent / "HWAXAgentServer"
GATEWAY = ROOT.parent / "HWAXMcpGateway" / "gateway.py"
RA = ROOT.parent / "ReportArchive"


class FakeRA:
    """RA MCP register_report_format 의 답 — 미리보기(dry_run · would) · 적용(action · version) · 거절(error)."""

    def __init__(self, *, existing=None, deny=""):
        self.existing = existing            # {"blocks": […], "name": …, "version": n} 또는 None
        self.deny = deny
        self.calls: list[dict] = []

    async def __call__(self, args: dict):
        self.calls.append(args)
        if self.deny:
            return {"error": self.deny}
        tid = f"sys.{args['system']}.{args['kind']}"
        same = self.existing is not None and self.existing["blocks"] == args["blocks"] and self.existing["name"] == args["name"]
        if not args["apply"]:
            if self.existing is None:
                return {"dry_run": True, "template_id": tid, "would": "created", "note": "새 틀이 만들어진다."}
            return {"dry_run": True, "template_id": tid, "would": "unchanged" if same else "new_version",
                    "current_version": self.existing["version"], "note": "…"}
        if same:
            return {"template_id": tid, "version": self.existing["version"], "action": "unchanged", "registered_by_system": args["system"]}
        ver = (self.existing or {}).get("version", 0) + 1
        action = "created" if self.existing is None else "new_version"
        self.existing = {"blocks": args["blocks"], "name": args["name"], "version": ver}
        return {"template_id": tid, "version": ver, "action": action, "registered_by_system": args["system"], "next_steps": []}


def _run(ra, tmp_path, **kw):
    log: list[str] = []
    box = tmp_path / "ra-formats.local.json"
    code, out = asyncio.run(reg.run(ra, FMT, owner_board="mx", box_file=box, log=log.append,
                                    apply=kw.get("apply", False), use=kw.get("use", False)))
    return code, out, box, "\n".join(log)


def test_기본은_미리보기뿐이다(tmp_path):
    ra = FakeRA()
    code, out, box, said = _run(ra, tmp_path)
    assert code == 0 and out["would"] == "created" and out["template_id"] == "sys.hwax.deliberation"
    assert [c["apply"] for c in ra.calls] == [False], "쓰는 호출이 나갔다"
    assert not box.exists() and "미리보기만" in said
    assert ra.calls[0]["owner_boards"] == ["mx"] and ra.calls[0]["blocks"] == FMT["blocks"]
    assert all("content" not in b for b in ra.calls[0]["blocks"])


def test_apply_는_등록만_하고_올리는_곳은_그대로다(tmp_path):
    ra = FakeRA()
    code, out, box, said = _run(ra, tmp_path, apply=True)
    assert code == 0 and (out["action"], out["version"]) == ("created", 1)
    assert [c["apply"] for c in ra.calls] == [False, True]
    assert not box.exists() and "등록만" in said


def test_apply_use_는_등록하고_박스_파일에_적는다(tmp_path):
    ra = FakeRA()
    code, out, box, _ = _run(ra, tmp_path, apply=True, use=True)
    assert code == 0 and out["box_file"] == "ra-formats.local.json"
    doc = json.loads(box.read_text(encoding="utf-8"))
    assert doc["deliberation"] == {"template_id": "sys.hwax.deliberation", "template_version": 1}
    assert not box.with_name(box.name + ".tmp").exists()


def test_이미_같은_내용이_등록돼_있으면_쓰지_않고_그_판을_쓴다(tmp_path):
    ra = FakeRA(existing={"blocks": FMT["blocks"], "name": FMT["name"], "version": 3})
    code, out, box, said = _run(ra, tmp_path, apply=True, use=True)
    assert code == 0 and [c["apply"] for c in ra.calls] == [False], "내용이 같은데 등록을 다시 불렀다"
    assert json.loads(box.read_text(encoding="utf-8"))["deliberation"]["template_version"] == 3
    assert "등록할 것이 없다" in said
    # --use 만으로도 된다 — 이미 등록돼 있고 내용이 같으면 판을 안다
    box.unlink()
    code, _, box, _ = _run(FakeRA(existing={"blocks": FMT["blocks"], "name": FMT["name"], "version": 3}), tmp_path, use=True)
    assert code == 0 and json.loads(box.read_text(encoding="utf-8"))["deliberation"]["template_version"] == 3


def test_내용이_달라졌으면_새_판을_등록하고_그_판을_쓴다(tmp_path):
    ra = FakeRA(existing={"blocks": FMT["blocks"][:3], "name": FMT["name"], "version": 2})
    code, out, box, _ = _run(ra, tmp_path, apply=True, use=True)
    assert code == 0 and (out["action"], out["version"]) == ("new_version", 3)
    assert json.loads(box.read_text(encoding="utf-8"))["deliberation"]["template_version"] == 3


def test_등록_전에_use_만_주면_적지_않는다(tmp_path):
    code, _, box, said = _run(FakeRA(), tmp_path, use=True)
    assert code == 4 and not box.exists() and "--apply" in said
    code, _, box, _ = _run(FakeRA(existing={"blocks": [], "name": "옛 이름", "version": 5}), tmp_path, use=True)
    assert code == 4 and not box.exists(), "내용이 달라진 옛 판을 쓰면 엔진이 채우는 칸과 어긋난다"


def test_RA_의_거절은_까닭과_함께_끝_코드_3(tmp_path):
    ra = FakeRA(deny="'sys.hwax.deliberation' 는 사람이 만든 템플릿입니다 — 시스템이 덮어쓸 수 없습니다.")
    code, out, box, said = _run(ra, tmp_path, apply=True, use=True)
    assert code == 3 and "사람이 만든 템플릿" in out["error"] and "거절" in said and not box.exists()


def test_박스_파일은_다른_줄을_지키고_틀린_값은_쓰지_않는다(tmp_path):
    box = tmp_path / "ra-formats.local.json"
    box.write_text(json.dumps({"_doc": "손으로 쓴 메모", "other": {"template_id": "sys.x.y", "template_version": 9}}), encoding="utf-8")
    doc = reg.write_box("deliberation", "sys.hwax.deliberation", 2, box)
    assert doc["_doc"] == "손으로 쓴 메모" and doc["other"]["template_version"] == 9
    for tid, ver in (("../x", 1), ("", 1), ("sys.hwax.deliberation", 0), ("sys.hwax.deliberation", True), ("sys.hwax.deliberation", "2")):
        with pytest.raises(ValueError):
            reg.write_box("deliberation", tid, ver, box)
    assert json.loads(box.read_text(encoding="utf-8"))["deliberation"]["template_version"] == 2
    box.write_text("{ 깨진", encoding="utf-8")
    assert reg.write_box("deliberation", "sys.hwax.deliberation", 4, box)["deliberation"]["template_version"] == 4


def test_형식_파일의_꼴을_본다(tmp_path):
    def w(doc):
        (tmp_path / "x.json").write_text(json.dumps(doc), encoding="utf-8")
        return reg.load_format("x", tmp_path)
    ok = {"system": "hwax", "kind": "x", "name": "이름", "blocks": [{"id": "a", "type": "rich_text"}]}
    assert w(ok)["kind"] == "x"
    for bad in ({**ok, "system": "HWAX"}, {**ok, "kind": "a" * 25}, {**ok, "name": " "}, {**ok, "blocks": []},
                {**ok, "blocks": [{"id": "a", "type": "rich_text"}, {"id": "a", "type": "rich_text"}]},
                {**ok, "blocks": [{"id": "a", "type": "rich_text", "content": {"items": []}}]}, {**ok, "blocks": [{"id": "a"}]}):
        with pytest.raises(ValueError):
            w(bad)
    with pytest.raises(ValueError):
        reg.load_format("../deliberation")
    with pytest.raises(ValueError):
        reg.load_format("없는형식", tmp_path)


# ── 두 리포 · RA 와 맞대기 ─────────────────────────────────────────────────────
def _engine_block_keys() -> set[str]:
    """심의 엔진이 RA 초안에 채우는 칸 — deliberation.py 의 `blocks = {…}` 가운데 background 를 가진 dict 들의 글자 키."""
    tree = ast.parse((AGENT / "deliberation.py").read_text(encoding="utf-8"))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            ks = {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if {"background", "recommendation", "minutes"} <= ks:
                keys |= ks
    return keys


def test_형식의_블록_id_가_엔진이_채우는_칸과_같다():
    if not (AGENT / "deliberation.py").is_file():
        pytest.skip("형제 리포 HWAXAgentServer 가 이 박스에 없다")
    engine = _engine_block_keys()
    assert engine, "엔진에서 RA 블록 dict 를 못 찾았다 — 꼴이 바뀌었나"
    ids = {b["id"] for b in FMT["blocks"]}
    assert engine <= ids, f"엔진이 채우는데 형식에 없는 칸 {sorted(engine - ids)} — 그 칸의 글이 RA 에서 버려진다"
    assert ids <= engine, f"형식에만 있는 칸 {sorted(ids - engine)} — 늘 빈 칸이 된다"


def test_블록_종류와_props_가_RA_위젯_등록부에_있다():
    registry = RA / "backend" / "app" / "widgets" / "registry.py"
    if not registry.is_file():
        pytest.skip("형제 리포 ReportArchive 가 이 박스에 없다")
    src = registry.read_text(encoding="utf-8")
    for b in FMT["blocks"]:
        m = re.search(r'"type": "%s",.*?"props_schema": \{(.*?)"additionalProperties": False' % re.escape(b["type"]), src, re.S)
        assert m, f"RA 위젯 등록부에 `{b['type']}` 이 없다"
        known = set(re.findall(r'^\s{12}"([a-z_]+)": ', m.group(1), re.M))
        extra = set(b.get("props") or {}) - known
        assert not extra, f"`{b['id']}` 의 props {sorted(extra)} 를 RA 가 모른다(additionalProperties 가 닫혀 있어 등록이 거절된다)"


def _literal(path: Path, name: str):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{path.name} 에 {name} 이 없다")


def test_에이전트_서버와_게이트웨이가_같은_기본값과_같은_파일을_본다():
    if not (AGENT / "ra_formats.py").is_file() or not GATEWAY.is_file():
        pytest.skip("형제 리포(HWAXAgentServer · HWAXMcpGateway)가 이 박스에 없다")
    a = _literal(AGENT / "ra_formats.py", "DEFAULTS")
    g = _literal(GATEWAY, "_RA_FORMAT_DEFAULTS")
    assert a == g == {"deliberation": ("deliberation", 1)}, "기본값이 갈리면 박스 파일 없는 박스에서 두 길이 다른 템플릿에 올린다"
    assert _literal(AGENT / "ra_formats.py", "FILE_NAME") == reg.BOX_FILE.name
    assert f'/ "infra" / "{reg.BOX_FILE.name}"' in GATEWAY.read_text(encoding="utf-8")
    assert set(a) == {FMT["kind"]}, "형식 파일의 kind 가 두 리포가 아는 종류와 같아야 박스 파일의 줄이 읽힌다"


def test_박스_파일은_추적하지_않는다():
    ig = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "infra/ra-formats.local.json" in ig


def test_형식의_이름과_칸_라벨은_손으로_둔_템플릿과_같다():
    """RA 에 손으로 둔 `deliberation` v1 템플릿(dev RA DB 에서 읽었다 — 2026-11-22)과 이름 · 블록 차례 · 라벨 · props 가 같아야, 스스로 등록한
    형식으로 바꿔도 보고서가 같은 모습으로 보인다. 고치려면 까닭을 형식 파일의 `_doc` 에 적는다."""
    assert FMT["name"] == "심의 보고서"
    assert [(b["id"], b["type"], b.get("props")) for b in FMT["blocks"]] == [
        ("background", "rich_text", {"label": "심의 주제", "required": True}),
        ("results", "rich_text", {"label": "심화 논의(2R)"}),
        ("recommendation", "rich_text", {"label": "의사결정문"}),
        ("minutes", "rich_text", {"label": "회의록(참여·라운드)"})]
    assert all("layout" not in b for b in FMT["blocks"]), "배치는 RA 가 차례대로 놓는다(손으로 둔 템플릿도 layout 이 없다)"


def test_board_를_주면_그_줄에_게시판까지_적고_다시_use_해도_남는다(tmp_path):
    """심의 보고서 표준(docs/ra-delib-standard) — --use --board 가 줄에 게시판을 적는다. 그 뒤 --use 만 다시 돌려도(판이 바뀌어도) 게시판이 남는다."""
    box = tmp_path / "ra-formats.local.json"
    doc = reg.write_box("deliberation", "sys.hwax.deliberation", 1, box, board="sys-hwax")
    assert doc["deliberation"] == {"template_id": "sys.hwax.deliberation", "template_version": 1, "board": "sys-hwax"}
    assert reg.write_box("deliberation", "sys.hwax.deliberation", 2, box)["deliberation"] == {
        "template_id": "sys.hwax.deliberation", "template_version": 2, "board": "sys-hwax"}
    for bad in ("../x", "", "a/b", ".."):
        with pytest.raises(ValueError):
            reg.write_box("deliberation", "sys.hwax.deliberation", 3, box, board=bad)
    assert json.loads(box.read_text(encoding="utf-8"))["deliberation"]["template_version"] == 2


def test_run_의_board_는_박스_파일에_실린다(tmp_path):
    box = tmp_path / "ra-formats.local.json"
    log: list[str] = []
    code, out = asyncio.run(reg.run(FakeRA(), FMT, owner_board="mx", box_file=box, log=log.append, apply=True, use=True, board="sys-hwax"))
    assert code == 0 and out["board"] == "sys-hwax"
    assert json.loads(box.read_text(encoding="utf-8"))["deliberation"]["board"] == "sys-hwax"
    assert any("게시판 sys-hwax" in m for m in log)


def test_board_는_use_없이_받지_않는다(monkeypatch, capsys):
    monkeypatch.setenv("HWAX_GATEWAY_PAT", "x")
    assert reg.main(["--owner-board", "mx", "--board", "sys-hwax"]) == 2
    assert reg.main(["--owner-board", "mx", "--use", "--board", "../x"]) == 2
    assert "--board" in capsys.readouterr().err


def test_포털_리더와_등록_스크립트의_게시판_꼴이_같다():
    from app.agent import ra_post
    assert reg._BOARD_RE.pattern == ra_post._BOARD_RE.pattern
