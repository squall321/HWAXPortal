# 절차 PAT 의 `purpose` 클레임 — 게이트웨이의 파괴 도구 차단을 **이 토큰에만** 면제하는 열쇠다(W-100).
#
# 열쇠가 되려면 **사람이 만들 수 없어야** 한다. `/auth/pat` 은 사람이 준 문자열을 `pat_name` 에만
# 넣고 클레임 집합은 코드가 고정하므로, 이름을 "procedures" 로 지어도 `purpose` 는 안 붙는다.
# 그 성질이 깨지는 순간 누구나 파괴 도구를 범용 실행기로 부를 수 있게 되므로 여기서 못박는다.
import ast
import tempfile
import types
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.keystore import KeyStore
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.procedures.pat import mint

_BACKEND = Path(__file__).resolve().parents[1]


def _claims(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])


@pytest.fixture()
def kit(tmp_path):
    s = Settings(jwt_keys_dir=str(tmp_path / "keys"))
    return KeyStore(s), s


def test_절차_PAT_에는_purpose_가_있다(kit):
    ks, s = kit
    p = types.SimpleNamespace(subject="u1", email="u1@x.io", display_name="U", groups=["feat:procedures"])
    c = _claims(mint(ks, s, p, "run-1", 3))
    assert c["purpose"] == "procedure"
    assert c["pat_name"] == "procedures" and c["jti"] == "wb-run-1-3"


# ── 사람이 만드는 PAT 에는 없어야 한다 ──────────────────────────────────────
@pytest.fixture()
def client(tmp_path):
    s = Settings(user_store_path=str(tmp_path / "users.sqlite"),
                 local_bootstrap_admins="boss@corp.com", gateway_shared_token="gw-test-secret")
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        app.state.user_store = UserStore(s)
        yield c
    app.dependency_overrides.pop(get_settings, None)


def test_사람이_이름을_procedures_로_지어도_purpose_는_안_붙는다(client):
    """이 하나가 깨지면 면제가 **아무나 쓰는 문**이 된다 — 이름은 사용자 입력이다."""
    for e, n in (("boss@corp.com", "Boss"), ("u@corp.com", "U")):
        client.post("/auth/local/signup", json={"email": e, "name": n, "password": "pw123456"})
    client.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"})
    hb = {"X-CSRF-Token": client.cookies.get("hwax_csrf")}
    client.post("/auth/local/users/u@corp.com/approve", json={"groups": []}, headers=hb)
    client.patch("/auth/access/users/u@corp.com", json={"grants": ["feat:api-token"]}, headers=hb)
    client.cookies.clear()
    client.post("/auth/local/login", json={"email": "u@corp.com", "password": "pw123456"})
    hu = {"X-CSRF-Token": client.cookies.get("hwax_csrf")}

    r = client.post("/auth/pat", json={"name": "procedures"}, headers=hu)
    assert r.status_code == 200, r.text
    c = _claims(r.json()["token"])
    assert "purpose" not in c, "사람이 만든 토큰에 purpose 가 붙으면 면제가 통째로 무너진다"
    assert c["pat_name"] == "procedures", "이름 자체는 자유다 — 그래서 이름으로 판정하면 안 된다"


def _purpose_sites(path: Path) -> list[str]:
    """`jwt.encode` 를 부르는 **함수 안에서** `purpose` 를 토큰에 넣을 수 있는 모든 꼴을 찾는다.

    ⚠ 처음엔 `jwt.encode` 에 넘기는 dict **리터럴**의 키만 셌다. 검토에서 잡혔다 — 챗 PAT 발급기에
    `claims["purpose"] = "procedure"` 한 줄을 **뒤에서** 덧붙이면 552개가 전부 초록이었고, 모든 웹 챗
    PAT 이 면제 열쇠를 들게 된다(실제로 그 줄이 죽은 검토 에이전트의 탐침으로 작업트리에 남아 있었다).
    그래서 꼴을 가리지 않는다 — 발급 함수 안의 문자열 `"purpose"`·키워드 `purpose=` 는 전부 센다.
    함수 단위로 보는 이유는 `agent/routes.py` 가 같은 낱말을 **다른 함수에서** MCP 도구 인자로 쓰기
    때문이다(파일 단위로 세면 오탐이다).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = list(ast.walk(fn))
        encodes = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == "encode" and getattr(n.func.value, "id", "") == "jwt"
                      for n in body)
        if not encodes:
            continue
        for n in body:
            if isinstance(n, ast.Constant) and n.value == "purpose":
                out.append(f"{fn.name}:{n.lineno}")
            elif isinstance(n, ast.keyword) and n.arg == "purpose":
                out.append(f"{fn.name}:{n.value.lineno}")
    return out


def test_purpose_를_넣는_자리는_절차_PAT_하나뿐이다():
    """다른 발급 경로가 이 클레임을 복사하기 시작하면 위 시험만으로는 못 잡는다.
    **소스에서** 자리를 센다 — 새 발급기가 생겨도, 넣는 꼴이 달라도 여기서 걸린다."""
    hits = {}
    for f in sorted((_BACKEND / "app").rglob("*.py")):
        if "jwt.encode" not in f.read_text(encoding="utf-8"):
            continue
        sites = _purpose_sites(f)
        if sites:
            hits[f.relative_to(_BACKEND).as_posix()] = sites
    assert list(hits) == ["app/procedures/pat.py"], f"토큰에 purpose 를 넣는 자리가 늘었다: {hits}"
    assert [s.split(":")[0] for s in hits["app/procedures/pat.py"]] == ["mint"], hits


def test_챗_PAT_에는_purpose_가_없다():
    """웹 챗이 **요청마다** 찍어 agent-server 에 넘기는 토큰이다. 여기에 이 칸이 붙으면 챗 LLM 이
    `invoke_tool` 로 보고서를 버릴 수 있다 — 소스 세기와 별개로 **동작으로도** 건다."""
    from app.agent.routes import _chat_user_pat

    ks = KeyStore(Settings(jwt_keys_dir=str(Path(tempfile.mkdtemp()) / "keys")))
    p = types.SimpleNamespace(subject="u1", email="u1@x.io", display_name="U", groups=["feat:chat"])
    tok = _chat_user_pat(ks, Settings(), p)
    assert tok, "챗 PAT 발급이 실패했다 — 시험 전제가 깨졌다"
    assert "purpose" not in _claims(tok)
