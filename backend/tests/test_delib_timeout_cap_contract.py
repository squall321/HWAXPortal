# 심의 호출당 타임아웃(timeout_s)의 요청 상한이 엔진 기본값·포털 스키마·프론트 클램프·입력칸에서 같은 수인지 — 어긋나면 422 가 나거나 말없이 죄인다
"""`delib_opts.timeout_s` 의 상한은 네 곳에 있다. **LLM 호출 1회** 기준이고 심의 전체 시간이 아니다.

  엔진   HWAXAgentServer/deliberation.py   DELIB_TIMEOUT_MAX_S 의 **기본값**   (넘으면 죄고 카드로 알린다)
  포털   backend/app/agent/routes.py       DelibOpts.timeout_s 의 le           (넘으면 요청 전체가 422)
  프론트 state/chatStore.ts                DELIB_TIMEOUT_MAX_S                 (보내기 전 클램프)
  프론트 components/chat/DelibOptsPanel    입력칸 max                          (같은 상수를 쓴다)

종전에는 네 곳이 리터럴 1800 을 따로 들고 있었고 묶는 시험이 없었다. 엔진 쪽 값만 아는 호출자가 그보다 큰 값을
보내자 포털에서 요청 전체가 422 로 떨어져 패널이 전부 닫혔다(2026-10-07). 20석 넘는 패널은 공유 LLM 에 줄을 서는
시간까지 이 시계에 들어가므로 상한을 14400 으로 올렸고, 다시 따로 놀지 않게 여기서 묶는다(test_seat_cap_contract 와 같은 방식).

엔진은 환경값(DELIB_TIMEOUT_MAX_S)으로 더 올릴 수 있다. 포털이 더 좁은 쪽이어도 초과는 422 로 **소리 내** 막히니
안전하다 — 그래서 대조하는 것은 엔진의 **기본값**(소스에 적힌 수)이지 그 박스의 환경값이 아니다.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.agent.routes import DelibOpts

_ROOT = Path(__file__).resolve().parents[2]
_FE = _ROOT / "frontend"
_STORE = _FE / "src" / "state" / "chatStore.ts"
_PANEL = _FE / "src" / "components" / "chat" / "DelibOptsPanel.tsx"
_ENGINE_DIR = _ROOT.parent / "HWAXAgentServer"


def _portal_cap() -> float:
    caps = [m.le for m in DelibOpts.model_fields["timeout_s"].metadata if getattr(m, "le", None) is not None]
    assert caps, "DelibOpts.timeout_s 에 le 가 없다 — 상한이 없으면 호출 하나가 영영 매달려도 된다는 뜻이 된다"
    return float(caps[0])


def _front_cap() -> float:
    m = re.search(r"^export const DELIB_TIMEOUT_MAX_S\s*=\s*(\d+)\s*;", _STORE.read_text(encoding="utf-8"), re.M)
    assert m, "chatStore.ts 에서 DELIB_TIMEOUT_MAX_S 를 못 찾았다 — 이름이 바뀌었으면 이 시험도 고쳐라"
    return float(m.group(1))


def _engine_default() -> float | None:
    """엔진 요청 상한의 **기본값** — `…("DELIB_TIMEOUT_MAX_S", N)` 의 N. 환경변수 이름 바로 뒤의 수만 읽는다
    (줄에서 처음 나오는 숫자를 집으면 이름 안의 숫자나 다른 인자를 집는다 — test_procedures_census 의 같은 경고)."""
    for path in (_ENGINE_DIR / "deliberation.py", _ENGINE_DIR / "app.py"):
        m = re.search(r"""["']DELIB_TIMEOUT_MAX_S["']\s*,\s*["']?(\d+(?:\.\d+)?)""", path.read_text(encoding="utf-8"))
        if m:
            return float(m.group(1))
    return None


def test_포털과_프론트의_상한이_같다():
    portal, front = _portal_cap(), _front_cap()
    assert front == portal, (
        f"프론트 클램프 {front:.0f} ≠ 포털 {portal:.0f} — 프론트가 크면 그 사이 값이 422 로 심의를 죽이고, "
        "작으면 화면에서만 상한이 낮다")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "max={DELIB_TIMEOUT_MAX_S}" in panel, "입력칸 max 가 같은 상수를 안 쓴다 — 숫자를 따로 적으면 다시 어긋난다"
    blk = panel[panel.index("호출 타임아웃"):]
    assert not re.search(r"max=\{\d+\}", blk[:blk.index("</li>")]), "타임아웃 입력칸에 숫자 max 가 따로 남아 있다"


def test_엔진_기본값도_같다():
    # 형제 리포가 없는 박스(부분 체크아웃)에서는 건너뛴다 — 없는 파일로 실패시키지 않는다.
    if not (_ENGINE_DIR / "deliberation.py").exists():
        pytest.skip(f"형제 리포 없음: {_ENGINE_DIR}")
    engine, portal = _engine_default(), _portal_cap()
    assert engine is not None, (
        "엔진에서 DELIB_TIMEOUT_MAX_S 의 기본값을 못 찾았다 — 엔진이 아직 리터럴 1800 으로 죄고 있으면 포털을 통과한 "
        f"큰 값({portal:.0f}까지)이 엔진에서 말없이 1800 으로 돈다. 손잡이 이름이나 줄 모양이 바뀌었으면 이 시험도 고쳐라")
    assert engine == portal, (
        f"호출당 타임아웃 상한 불일치 — 엔진 기본값 {engine:.0f} · 포털 {portal:.0f}. "
        + ("엔진 기본값을 올렸으면 포털 le(routes.py DelibOpts.timeout_s)와 프론트 chatStore DELIB_TIMEOUT_MAX_S 를 같이 올린다. "
           "한 박스에서만 더 받으려는 것이면 기본값은 두고 환경값(DELIB_TIMEOUT_MAX_S)을 올린다."
           if engine > portal else
           "포털이 엔진 기본값보다 넓다 — 포털을 통과한 초과분을 엔진이 죈다(알림은 카드 한 장뿐이다)."))


def test_포털은_상한까지_받고_넘으면_소리_내_막는다():
    """포털이 더 좁은 쪽이어도 되는 전제 — 초과는 422 로 드러난다. 그리고 그 본문이 **어느 칸이 얼마를 넘었는지** 말한다
    (화면은 이 loc·msg 를 읽어 보인다)."""
    from fastapi.testclient import TestClient

    from app.auth.provider import Principal
    from app.deps import principal_pat_or_session
    from app.main import app

    cap = _portal_cap()
    assert DelibOpts(timeout_s=cap).model_dump(exclude_none=True)["timeout_s"] == cap
    assert DelibOpts(timeout_s=3600).timeout_s == 3600, "종전 상한 1800 을 넘는 값이 아직 거절된다"
    app.dependency_overrides[principal_pat_or_session] = lambda: Principal(
        subject="u1", email="u1@hwax.local", display_name="U", groups=["feat:deliberation"])
    try:
        with TestClient(app) as c:
            r = c.post("/agent/chat?mode=echo", json={"message": "x", "delib_opts": {"timeout_s": cap + 1}})
            ok = c.post("/agent/chat?mode=echo", json={"message": "x", "delib_opts": {"timeout_s": cap}})
    finally:
        app.dependency_overrides.pop(principal_pat_or_session, None)
    assert ok.status_code == 200
    assert r.status_code == 422
    (err,) = r.json()["detail"]
    assert err["loc"] == ["body", "delib_opts", "timeout_s"] and f"{cap:.0f}" in err["msg"]


@pytest.mark.skipif(not (_FE / "node_modules/typescript").exists() or not shutil.which("node"),
                    reason="frontend node_modules(typescript) 또는 node 가 없다 — 클램프를 돌려 볼 수 없다")
def test_프론트_클램프를_실제로_돌린다(tmp_path):
    """입력칸의 min/max 는 키보드 입력을 못 막는다 — 보내기 전 클램프가 마지막 관문이다. chatStore.ts 를 옮겨 적어 node 로 부른다."""
    (tmp_path / "run.cjs").write_text(
        "const ts = require('typescript'); const fs = require('fs');\n"
        f"const js = ts.transpileModule(fs.readFileSync({json.dumps(str(_STORE))}, 'utf8'),\n"
        "  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } });\n"
        "fs.writeFileSync(__dirname + '/chatStore.js', js.outputText);\n"
        "const { delibOptsToWire, DELIB_TIMEOUT_MAX_S } = require('./chatStore.js');\n"
        "const sent = JSON.parse(process.argv[2]).map((v) => delibOptsToWire({ timeout_s: v }).timeout_s ?? null);\n"
        "process.stdout.write(JSON.stringify({ sent, cap: DELIB_TIMEOUT_MAX_S }));\n", encoding="utf-8")
    r = subprocess.run(["node", "run.cjs", json.dumps([5, 600, 3600, 14400, 99999, 0])], cwd=str(tmp_path),
                       capture_output=True, text=True, timeout=120,
                       env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                            "NODE_PATH": str(_FE / "node_modules")})
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    cap = _portal_cap()
    assert got["cap"] == cap
    assert got["sent"] == [10, 600, 3600, cap, cap, None], "하한 10 · 상한까지 그대로 · 넘으면 상한 · 0 은 안 보낸다(서버 기본값)"
    for v in got["sent"][:-1]:
        DelibOpts(timeout_s=v)  # 클램프를 지난 값은 포털이 전부 받는다 — 하나라도 거절되면 심의가 422 로 시작조차 안 된다
