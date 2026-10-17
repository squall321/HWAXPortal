# 도구 인구조사 갱신기(refresh-census.py)의 판정 — 백엔드째 안 보이는 도구를 '사라짐' 과 가르고 그때의 갱신을 막는다
#
# 지키는 것: 백엔드 하나가 내려가 그 도구가 통째로 빠지는데 다른 백엔드가 그만큼 늘면, '크게 줄면 막는다'
# 를 지나쳐 갱신이 그 도구를 고정물에서 조용히 지운다(dev 10-17 — reportarchive · smart-twin-cluster 88종).
import datetime
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location("refresh_census", ROOT / "backend" / "scripts" / "refresh-census.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _t(name: str, backend, dry: bool = False) -> dict:
    return {"name": name, "backend": backend, "dry_run": dry, "args": 0, "args_documented": 0}


def _old(days_ago: int = 3) -> dict:
    gen = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
    return {"_why": "시험", "generated": gen, "gateway_tools": 5, "tools": [
        _t("ra_a", "reportarchive", dry=True), _t("ra_b", "reportarchive"),
        _t("sf_a", "signalforge", dry=True), _t("sf_old", "signalforge"), _t("gw", "_gateway")]}


def _fresh() -> dict:
    """reportarchive 가 내려갔고 signalforge 가 셋 늘었다 — 총수는 5 → 5 라 '크게 줄면' 은 안 걸린다."""
    return {"_why": "시험", "generated": datetime.date.today().isoformat(), "gateway_tools": 5, "tools": [
        _t("sf_a", "signalforge", dry=True), _t("sf_n1", "signalforge"), _t("sf_n2", "signalforge"),
        _t("sf_n3", "signalforge"), _t("gw", "_gateway")]}


def test_사라진_도구를_백엔드째_안_보이는_것과_정말_없어진_것으로_가른다():
    c = _mod().compare(_old(), _fresh())
    assert c["absent"] == {"reportarchive": ["ra_a", "ra_b"]}
    assert c["gone"] == ["sf_old"]
    assert c["added"] == ["sf_n1", "sf_n2", "sf_n3"]
    # ra_a 는 dry_run 을 잃은 게 아니라 안 보일 뿐이다 — 위 갈래에 이미 있다.
    assert c["dry_removed"] == [] and c["dry_added"] == []


def test_dry_run_을_잃은_것은_지금_있는_도구만이다():
    f = _fresh()
    f["tools"][0]["dry_run"] = False                       # sf_a 는 있는데 dry_run 이 없어졌다
    assert _mod().compare(_old(), f)["dry_removed"] == ["sf_a"]


def test_백엔드를_모르는_옛_행은_안_보이는_백엔드로_치지_않는다():
    o = _old()
    o["tools"].append(_t("orphan", None))
    c = _mod().compare(o, _fresh())
    assert "orphan" in c["gone"] and None not in c["absent"]


@pytest.fixture()
def run(tmp_path, monkeypatch, capsys):
    """고정물을 임시 파일로 두고 main 을 돌린다 — 게이트웨이(pull · health_down)는 갈아 끼운다."""
    m = _mod()
    census = tmp_path / "catalog-census.json"

    def go(*argv, old=None, fresh=None, down=frozenset()):
        census.write_text(json.dumps(old or _old(), ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(m, "CENSUS", census)
        monkeypatch.setattr(m, "pull", lambda: fresh or _fresh())
        monkeypatch.setattr(m, "health_down", lambda: set(down))
        monkeypatch.setattr(sys, "argv", ["refresh-census.py", *argv])
        rc = m.main()
        return rc, capsys.readouterr().out, json.loads(census.read_text(encoding="utf-8"))
    return go


def test_백엔드째_안_보이면_총수가_늘어도_갱신을_막는다(run):
    rc, out, after = run(down={"reportarchive"})
    assert rc == 2, out
    assert after == _old(), "막았으면 고정물은 그대로다"
    assert "reportarchive" in out and "--force" in out


def test_force_면_사람이_확인한_것으로_보고_덮어쓴다(run):
    rc, out, after = run("--force")
    assert rc == 0, out
    assert {t["name"] for t in after["tools"]} == {t["name"] for t in _fresh()["tools"]}


def test_check_는_나이와_안_보이는_까닭을_보이고_쓰지_않는다(run):
    rc, out, after = run("--check", old=_old(days_ago=32), down={"reportarchive"})
    assert rc == 1
    assert "32일 전" in out
    assert "백엔드째 안 보임 — reportarchive 2종: 게이트웨이 /health 가 내려갔다고 한다" in out
    assert after == _old(days_ago=32)


def test_health_가_모르면_까닭을_단정하지_않는다(run):
    _, out, _ = run("--check")
    assert "reportarchive 2종: 도구가 하나도 안 보인다(내려갔거나 빠졌다)" in out


def test_같으면_check_는_0_이다(run):
    rc, _, _ = run("--check", old=_fresh(), fresh=_fresh())
    assert rc == 0


def test_check_는_백엔드째_안_보이는_것만_달라도_1_이다(run):
    f = _fresh()
    rc, out, _ = run("--check", old={**f, "tools": [*f["tools"], _t("ra_a", "reportarchive")]}, fresh=f)
    assert rc == 1, out


def test_health_down_은_false_로_적힌_백엔드만_고른다(monkeypatch):
    m = _mod()

    class R:
        def read(self):
            return b'{"backends": {"reportarchive": false, "signalforge": true, "odd": null}}'
    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: R())
    assert m.health_down() == {"reportarchive"}

    def boom(*a, **k):
        raise OSError("연결 거부")
    monkeypatch.setattr(m.urllib.request, "urlopen", boom)
    assert m.health_down() == set()
