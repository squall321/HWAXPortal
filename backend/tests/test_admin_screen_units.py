# 관리자 화면의 판정 조각을 node 로 실제로 돌려 본다 — 소속 미지정 판정 · 관리자 스위치의 갈래 · 접속 이력의 사유 문장
"""왜 — 8·9·10차 #1 ⓒ · #5 · #16 의 서버 쪽은 시험이 촘촘한데 화면 쪽 판정은 한 줄도 실행되지 않았다. 고정 관리자를
'소속 미지정' 에서 빼는 조건을 지우거나, 고정 관리자 줄에 스위치를 그리거나, 사유 코드의 문장을 뒤바꿔도 타입 검사·린트·전체
시험이 그대로 초록이었다(사본에서 변이 일곱을 한꺼번에 넣어 확인, 2026-10-07).

프론트에 단위 시험 러너가 없어 TypeScript 를 한 파일씩 옮겨 적어(transpile) node 로 부른다(test_handoff_evidence_cap 과 같은 길).
`tsc <파일>` 로는 안 된다 — auth.api.ts 가 client.ts → config.ts 의 `import.meta` 를 끌어와 CommonJS 로 컴파일되지 않는다.
그래서 네트워크 층(api/client)만 대역으로 둔다. 상태가 있는 화면 동작(필터·오류 표시·확인창)은 test_admin_pages_in_browser 가 본다.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"

pytestmark = pytest.mark.skipif(
    not (FE / "node_modules/typescript").exists() or not shutil.which("node"),
    reason="frontend node_modules(typescript) 또는 node 가 없다 — 화면 조각을 돌려 볼 수 없다",
)

_DRIVER = r"""
const ts = require('typescript'); const fs = require('fs'); const path = require('path');
const SRC = process.argv[2];
for (const rel of ['api/auth.api.ts', 'api/access.api.ts', 'pages/admin/AccessAdmin.tsx', 'lib/accessDetail.ts']) {
  const js = ts.transpileModule(fs.readFileSync(path.join(SRC, rel), 'utf8'), { fileName: rel, compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019, jsx: ts.JsxEmit.ReactJSX } });
  const dst = path.join(__dirname, rel.replace(/\.tsx?$/, '.js'));
  fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.writeFileSync(dst, js.outputText);
}
fs.writeFileSync(path.join(__dirname, 'api/client.js'), "exports.apiFetch = () => { throw new Error('network'); };\n");
fs.mkdirSync(path.join(__dirname, 'styles'), { recursive: true }); fs.writeFileSync(path.join(__dirname, 'styles/admin.css'), '');
require.extensions['.css'] = () => {};
const { renderToStaticMarkup } = require('react-dom/server'); const { createElement } = require('react');
const { isUnassigned } = require('./api/auth.api.js');
const { AdminToggle } = require('./pages/admin/AccessAdmin.js');
const { detailText } = require('./lib/accessDetail.js');
const req = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify({
  unassigned: req.rows.map((r) => isUnassigned(r)),
  toggle: req.toggles.map(([r, self]) => renderToStaticMarkup(createElement(AdminToggle, { row: r, self, onSaved() {}, onError() {} }))),
  detail: req.details.map((d) => detailText(d)),
}));
"""


def _row(**over) -> dict:
    return {"email": "a@corp.example", "name": "", "department": "", "groups": [], "status": "active", "auth_source": "sso",
            "created_at": 0, "approved_at": None, "last_login_at": None, "locked_until": 0, **over}


@pytest.fixture(scope="module")
def screen(tmp_path_factory):
    out = tmp_path_factory.mktemp("adminscreen")
    (out / "drive.cjs").write_text(_DRIVER, encoding="utf-8")

    def run(rows=(), toggles=(), details=()) -> dict:
        r = subprocess.run(["node", "drive.cjs", str(FE / "src")], cwd=str(out), capture_output=True, text=True, timeout=120,
                           input=json.dumps({"rows": list(rows), "toggles": list(toggles), "details": list(details)}),
                           env={"PATH": "/usr/bin:/bin:" + str(Path(shutil.which("node")).parent),
                                "NODE_PATH": str(FE / "node_modules")})
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return run


def test_소속_미지정은_활성이고_소속이_없고_관리자가_아닌_사람뿐이다(screen):
    """배너의 수 · '소속 미지정만 보기' · '모두 이 소속으로' 가 이 한 함수로 같은 사람을 센다. 고정 관리자는 원장 groups 에
    portal-admin 이 없어도 관리자다 — 빼지 않으면 미지정으로 세고 일괄 지정이 그 사람에게 소속을 준다."""
    cases = [(s, a, adm, pin) for s in ("active", "pending", "disabled") for a in ("", "CAEG")
             for adm in (False, True) for pin in (False, True)]
    got = screen(rows=[_row(status=s, affiliation=a, groups=["portal-admin"] if adm else [], admin_pinned=pin)
                       for s, a, adm, pin in cases])["unassigned"]
    assert [c for c, g in zip(cases, got, strict=True) if g] == [("active", "", False, False)]
    assert screen(rows=[_row()])["unassigned"] == [True], "affiliation·admin_pinned 칸이 아예 없는 옛 응답도 미지정이다"


def test_관리자_스위치의_갈래(screen):
    on = ["portal-admin"]
    pinned, pinned_off, me, other, plain, pending, disabled, disabled_on = screen(toggles=[
        (_row(admin_pinned=True), False), (_row(admin_pinned=True, status="disabled"), False),
        (_row(groups=on), True), (_row(groups=on), False), (_row(), False),
        (_row(status="pending"), False), (_row(status="disabled"), False), (_row(status="disabled", groups=on), False)])["toggle"]
    assert "<input" not in pinned and "고정" in pinned, "고정 관리자 줄에는 스위치가 없다(눌러도 서버가 거절한다)"
    assert "<input" not in pinned_off and "정지 중" in pinned_off
    assert 'disabled=""' in me and 'checked=""' in me, "본인 줄은 켜진 채 잠긴다"
    assert 'disabled=""' not in other and 'checked=""' in other, "다른 관리자는 해제할 수 있다"
    assert "<input" in plain and 'checked=""' not in plain and 'disabled=""' not in plain
    assert "<input" not in pending and "<input" not in disabled, "지정은 활성 계정에만 한다"
    assert "<input" in disabled_on and 'checked=""' in disabled_on, "남아 있는 표지는 상태와 무관하게 뗄 수 있다"


def test_접속_이력의_사유_코드는_문장으로_나온다(screen):
    codes = ["sso:disabled", "sso:disabled:sabun", "sso:aff:map:CAEG", "sso:aff:default:CAEG", "sso", "local:bad-password", None]
    got = dict(zip(codes, screen(details=codes)["detail"], strict=True))
    for code in codes[:4]:
        assert got[code] and code not in got[code], f"{code} 가 코드 원문으로 나온다"
    assert "CAEG" in got["sso:aff:map:CAEG"] and "CAEG" in got["sso:aff:default:CAEG"]
    assert "기본 소속" in got["sso:aff:default:CAEG"] and "기본 소속" not in got["sso:aff:map:CAEG"], "두 출처를 뒤바꾸지 않는다"
    assert got["sso:disabled"] != got["sso:disabled:sabun"]
    assert (got["sso"], got[None]) == ("SSO", "") and got["local:bad-password"].endswith("bad-password")
    assert screen(details=["no-such-code"])["detail"] == ["no-such-code"], "모르는 코드는 숨기지 않고 그대로 보인다"
