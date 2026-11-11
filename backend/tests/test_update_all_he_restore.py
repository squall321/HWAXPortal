# update-all §3 — AIDataHub 병합이 HE팀 운영자를 덮었으면 백업 · 개수 확인 · --apply · 다시 미리보기를 저절로 하는가(docs/request-1111 HP-64 (나))
"""왜 — 병합이 운영자 행을 매 실행 dev 판으로 덮었다(11-03 · 11-05 · 11-08 · 11-11, 2 ~ 5명). HP-35 의 미리보기가 알리면 사람이 백업을 뜨고
--apply 했는데, 백업이 두 번 빠졌다(11-05 안 뜸 · 11-09 다른 칸으로 걸러 0건). 그 사이 챗 · 심의는 dev 판 운영자 글로 돌았다.

update-all 원문의 그 구획(HP-35 미리보기와 같은 자리)을 떼어 **진짜** sync-he-personas.py 로 돌린다. 게이트웨이 · AIDataHub 는 이 시험이
띄운 가짜 HTTP 서버이고 백업은 임시 BACKUP_ROOT 아래에 적힌다 — 실 AIDataHub · /data 를 건드리지 않는다. 게이트웨이에는 앱 하나만
붙여(he-calc-thermalshock) 그 운영자만 만들어지고 나머지는 건너뛴다.
"""
import http.server
import importlib.util
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
SPEC = json.loads((ROOT / "infra/personas/he-team.json").read_text(encoding="utf-8"))
KEY = "he-calc-thermalshock"
_START = "  # merge 는 updated_at 이 더 새 쪽을 고른다"
_END = '이 박스 판 그대로(미리보기)"\n    fi\n  fi\n'


def _block() -> str:
    i = UA.index(_START)
    return UA[i:UA.index(_END, i) + len(_END)]


def _tmap() -> dict:
    """KEY 운영자 하나만 만들 수 있는 게이트웨이 — 정본에 적은 이름을 그 앱의 도구로 낸다."""
    p = next(p for p in SPEC["personas"] if p["key"] == KEY)
    app = p["apps"][0]
    pre = app.replace("-", "") + "_"
    names = {n[len(pre):] if n.startswith(pre) else n for fld in ("key_tools", "writes", "confirm") for n in p[fld]}
    return {"map": {n: app for n in names}, "areas": {}, "area_meta": [], "apps": [{"app": app, "label": "Thermal Shock"}]}


def _dev_rows(*drop: str) -> dict:
    """정본 운영자 전부를 병합이 dev 판으로 덮은 꼴."""
    return {p["key"]: {"agent_type": p["key"], "name": p["key"], "system_prompt": "dev 판",
                       "response_config": {"persona_kind": "mcp_operator", "mcp_apps": p["apps"]}}
            for p in SPEC["personas"] if p["key"] not in drop}


def _box_rows() -> dict:
    """KEY 는 이미 이 박스 판 — 동기화가 만드는 행 그대로."""
    spec = importlib.util.spec_from_file_location("sync_he_personas_restore", ROOT / "infra/scripts/sync-he-personas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (row,), _skipped, errors = mod.plan({**SPEC, "personas": [p for p in SPEC["personas"] if p["key"] == KEY]}, _tmap())
    assert not errors, errors
    return {**_dev_rows(), KEY: row}


class _Hub:
    """게이트웨이 /tools-map + AIDataHub /api/agents. list_status 로 목록 읽기를, patch_status · saves 로 고치기를 망가뜨린다."""

    def __init__(self, rows: dict, *, list_status: int = 200, patch_status: int = 200, saves: bool = True):
        self.rows = {k: dict(v) for k, v in rows.items()}
        self.calls: list[tuple[str, str]] = []
        hub, tmap = self, _tmap()

        class H(http.server.BaseHTTPRequestHandler):
            def _send(self, code, obj):
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _body(self):
                return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"null")

            def do_GET(self):  # noqa: N802
                hub.calls.append(("GET", self.path))
                if self.path == "/tools-map":
                    return self._send(200, tmap)
                if self.path == "/api/agents":
                    return self._send(list_status, list(hub.rows.values()) if list_status == 200 else {"detail": "boom"})
                key = self.path.rsplit("/", 1)[1]
                return self._send(200, hub.rows[key]) if key in hub.rows else self._send(404, {"detail": "not found"})

            def do_PATCH(self):  # noqa: N802
                hub.calls.append(("PATCH", self.path))
                key, body = self.path.rsplit("/", 1)[1], self._body()
                if saves and patch_status == 200:
                    hub.rows[key] = {**hub.rows[key], **body}
                return self._send(patch_status, hub.rows.get(key) or {"detail": "x"})

            def do_POST(self):  # noqa: N802
                hub.calls.append(("POST", self.path))
                body = self._body()
                if saves:
                    hub.rows[body["agent_type"]] = body
                return self._send(201, body)

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def writes(self) -> list[tuple[str, str]]:
        return [c for c in self.calls if c[0] in ("PATCH", "POST")]


@pytest.fixture()
def serve():
    hubs: list[_Hub] = []

    def make(rows: dict, **kw) -> _Hub:
        hubs.append(_Hub(rows, **kw))
        return hubs[-1]

    yield make
    for h in hubs:
        h.srv.shutdown()


def _run(tmp: Path, hub: _Hub, mrc: str) -> str:
    assert "/home/" not in _block(), "구획에 실물 경로가 박혀 있다"
    script = "\n".join([
        "set -uo pipefail",                                                    # update-all 과 같은 셸 설정(-e 없음)
        'ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; }',
        "_ra_envv() { :; }",                                                   # infra/.env 를 읽는 update-all 함수 — 박스 이름은 환경으로 준다
        f'SELF_REPO="{ROOT}"', f"_aidh_mrc={mrc}", _block(), "echo END",
    ])
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp), "LANG": "C.UTF-8",
           "GATEWAY_HTTP_BASE": hub.base, "AIDH_HTTP_BASE": hub.base,
           "HE_TEAM_LOCAL_PATH": str(tmp / "he-team.local.json"),             # 이 박스의 덧씌우기를 읽지 않는다
           "BACKUP_ROOT": str(tmp / "backups"), "HWAX_BOX": "testbox"}
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=120, env=env)
    assert r.stdout.endswith("END\n") and "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stdout + r.stderr
    return r.stdout[:-len("END\n")]


def _backups(tmp: Path) -> list[Path]:
    return sorted((tmp / "backups/hwax/testbox/he-personas").glob("he-personas-*.json"))


def test_병합이_덮었으면_백업하고_되돌리고_다시_보면_0이다(tmp_path, serve):
    hub = serve(_dev_rows())
    out = _run(tmp_path, hub, "0")
    n = len(SPEC["personas"])
    assert "  · HE팀 운영자 페르소나 1명이 이 박스 판과 다르다(merge 가 dev 판으로 덮었거나 새 운영자) — 백업하고 이 박스 판으로 되돌린다" in out, out
    assert f"    ~ {KEY} 고친다: " in out, out
    (f,) = _backups(tmp_path)
    assert f"    · 백업 {f} — he-* {n}건(agent_type 기준) · 운영자 {n}명 모두 들었다\n" in out, "백업 폴더와 개수가 기록에 찍힌다"
    assert f"OK:HE팀 운영자 페르소나 1명을 이 박스 판으로 되돌렸다" in out and "BAD:" not in out, out
    assert hub.writes() == [("PATCH", f"/api/agents/{KEY}")], hub.writes()
    saved = {r["agent_type"]: r for r in json.loads(f.read_text(encoding="utf-8"))}
    assert saved[KEY]["system_prompt"] == "dev 판" != hub.rows[KEY]["system_prompt"], "백업은 되돌리기 전 판 · 행은 이 박스 판"
    box = _box_rows()[KEY]
    managed = ("name", "description", "common_tags", "sample_queries", "system_prompt", "response_config")
    assert all(hub.rows[KEY][k] == box[k] for k in managed), "동기화가 맡는 칸이 이 박스 판으로 돌아왔다"


def test_조각_길_3_으로_끝난_병합도_되돌린다(tmp_path, serve):
    hub = serve(_dev_rows())
    out = _run(tmp_path, hub, "3")
    assert "OK:HE팀 운영자 페르소나 1명을 이 박스 판으로 되돌렸다" in out and len(_backups(tmp_path)) == 1, out


@pytest.mark.parametrize("mrc", ["", "1", "''"])
def test_병합이_돌지_않았으면_아무것도_부르지_않는다(tmp_path, serve, mrc):
    hub = serve(_dev_rows())
    assert _run(tmp_path, hub, mrc) == "" and hub.calls == [] and not (tmp_path / "backups").exists()


def test_어긋남이_없으면_백업도_반영도_하지_않는다(tmp_path, serve):
    hub = serve(_box_rows())
    out = _run(tmp_path, hub, "0")
    assert out == "OK:HE팀 운영자 페르소나 — merge 뒤에도 이 박스 판 그대로(미리보기)\n", out
    assert hub.writes() == [] and not (tmp_path / "backups").exists()


def test_백업에_운영자가_빠지면_반영하지_않고_알린다(tmp_path, serve):
    hub = serve(_dev_rows("he-data-arp"))
    out = _run(tmp_path, hub, "0")
    n = len(SPEC["personas"])
    (f,) = _backups(tmp_path)
    assert f"    ✗ 백업 {f} — he-* {n - 1}건(agent_type 기준) · 운영자 {n}명 가운데 {n - 1}명만 들었다(행이 없는 운영자 he-data-arp)" in out, out
    line = next(ln for ln in out.splitlines() if ln.startswith("BAD:"))
    assert line.startswith("BAD:HE팀 운영자 페르소나 1명이 이 박스 판과 다르다 — 백업 확인에서 멈춰(rc 1 · 위 줄) 저절로 되돌리지 않았다") \
        and "--apply" in line, line
    assert hub.writes() == [] and "OK:" not in out and "FAIL:" not in out, (out, hub.writes())
    assert hub.rows[KEY]["system_prompt"] == "dev 판"


def test_he_행이_0건이면_새로_만들지도_않는다(tmp_path, serve):
    hub = serve({"pcb-warpage": {"agent_type": "pcb-warpage", "name": "x"}})
    out = _run(tmp_path, hub, "0")
    assert f"    + {KEY} 새로 만든다" in out and "he-* 0건(agent_type 기준) · 0건이면 저절로 반영하지 않는다" in out, out
    assert "BAD:HE팀 운영자 페르소나 1명이 이 박스 판과 다르다 — 백업 확인에서 멈춰(rc 1" in out and hub.writes() == [], out


def test_AIDataHub_목록을_못_읽으면_모름이라_반영하지_않는다(tmp_path, serve):
    hub = serve(_dev_rows(), list_status=500)
    out = _run(tmp_path, hub, "0")
    assert "    ✗ 백업 못 함 — AIDataHub 전문가 목록을 못 읽었다(500) · 모름이라 저절로 반영하지 않는다" in out, out
    assert "BAD:HE팀 운영자 페르소나 1명이 이 박스 판과 다르다 — 백업 확인에서 멈춰(rc 2" in out, out
    assert hub.writes() == [] and _backups(tmp_path) == []


def test_apply_가_실패하면_백업을_가리키며_알린다(tmp_path, serve):
    hub = serve(_dev_rows(), patch_status=422)
    out = _run(tmp_path, hub, "0")
    assert len(_backups(tmp_path)) == 1 and "    · 백업 " in out, out
    assert "BAD:HE팀 운영자 페르소나 --apply 가 실패했다(rc 1) — 일부만 썼을 수 있다(되돌릴 판은 위 백업 줄)" in out, out
    assert f"    ✗ {KEY} 수정 실패 422" in out and "OK:" not in out, out


def test_apply_뒤에도_다르면_알린다(tmp_path, serve):
    hub = serve(_dev_rows(), saves=False)                                     # 200 으로 답하고 저장하지 않는다
    out = _run(tmp_path, hub, "0")
    assert "BAD:HE팀 운영자 페르소나 1명이 이 박스 판과 다르다(--apply 뒤에도) — 끝난 뒤 확인하고: python3 infra/scripts/sync-he-personas.py --apply" in out, out
    assert out.count(f"    ~ {KEY} 고친다: ") == 2 and "OK:" not in out, out


def test_6_은_그대로다():
    """HP-64 는 §3 에만 더한다 — §6 의 실행마다 점검(--check)은 쓰지 않는다."""
    i = UA.index("# ── HE팀 운영자 점검 — 실행마다")
    s6 = UA[i:UA.index("\nfi\n", i)]
    assert 'sync-he-personas.py" --check 2>&1' in s6
    assert 'sync-he-personas.py" --apply' not in s6 and "--backup" not in s6
