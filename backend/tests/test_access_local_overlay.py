# 권한 표의 박스 오버레이(access.local.yaml) — 플랫폼은 id 로 합치고, 깨지면 직전 정책을 쓰되 그 상태가 관리자에게 보인다(8차 요청 §4-(1))
"""systems.local.yaml·routes.local.env 는 오버레이가 있는데 access.yaml 에만 없어서, 박스에만 있는 앱을 붙일 때마다 추적 파일을
고쳐야 했다. 오버레이는 조용히 어긋나기 쉽다 — 깨진 파일이 '오버레이가 없는 것' 과 똑같이 보이면 그 박스의 백엔드는 표에서 빠진 채
(게이트웨이는 표에 없는 백엔드를 전체 공개로 본다) 아무도 모른다. 그래서 여기서 고정하는 것은 합치는 규칙과 **보이는 것**이다.

모든 파일은 임시 폴더에 쓴다 — 리포의 backend/config 는 건드리지 않는다. 코드·소속은 지어낸 값이다.
"""
import logging
import os
import shutil
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.access.policy import AccessPolicy, load_raw, parse_policy
from app.auth.user_store import UserStore
from app.config import Settings, get_settings
from app.main import app
from app.setup_requests import parse_requests, run_check

_BACKEND = Path(__file__).resolve().parents[1]

BASE = """
default_grants: [feat:chat]
affiliations:
  - {id: CAEG, label: CAE그룹, grants: ["*"]}
  - {id: LAB, label: 시험실, grants: [plat:alpha]}
features:
  - {id: chat, label: 일반 챗}
platforms:
  - {id: alpha, label: Alpha, systems: [alpha], gateway: [alpha]}
  - {id: beta, label: Beta, gateway: [beta]}
"""
LOCAL = """
platforms:
  - {id: beta, label: Beta(박스), gateway: [beta, beta-box]}
  - {id: gamma, label: Gamma, gateway: [gamma]}
"""


def _write(p: Path, text: str, *, tick: int = 0) -> Path:
    """파일을 쓰고 mtime 을 확실히 옮긴다 — 같은 초에 두 번 쓰면 mtime 캐시가 못 알아챈다(시험만의 문제)."""
    p.write_text(text, encoding="utf-8")
    if tick:
        st = p.stat()
        os.utime(p, (st.st_atime + tick, st.st_mtime + tick))
    return p


@pytest.fixture()
def box(tmp_path):
    base = _write(tmp_path / "access.yaml", BASE)
    return base, tmp_path / "access.local.yaml"


# ── 합치는 규칙 ──────────────────────────────────────────────────────────────
def test_오버레이가_없으면_추적_파일_그대로다(box):
    base, _ = box
    assert load_raw(base) == yaml.safe_load(BASE)
    pol = parse_policy(load_raw(base))
    assert sorted(pol.gateway_policy()) == ["alpha", "beta"] and not pol.warnings


def test_플랫폼은_id_로_더하고_바꾼다(box):
    base, local = box
    _write(local, LOCAL)
    pol = parse_policy(load_raw(base))
    assert pol.gateway_policy() == {"alpha": ["plat:alpha"], "beta": ["plat:beta"], "beta-box": ["plat:beta"],
                                    "gamma": ["plat:gamma"]}
    assert pol.item("plat:beta").label == "Beta(박스)", "같은 id 는 박스 파일 것이 이긴다"
    assert pol.system_key("alpha") == "plat:alpha", "오버레이에 없는 플랫폼은 그대로"
    assert not pol.warnings


# ── 같은 id 를 바꿔 쓰면서 추적 파일의 타일·백엔드를 떨군 박스 파일 ─────────────────────────────────────────
# 같은 id 는 합치지 않고 **통째로 바꾼다**. "박스 전용 백엔드를 붙이려고" 추적 플랫폼의 id 에 gateway 한 줄만 적으면 추적 파일의
# systems·gateway 가 사라진다 — 그 타일은 표에 없어 모두에게 보이고, 게이트웨이는 표에 없는 백엔드를 전체 공개로 본다
# (사본에서: 허가 0개인 사람에게 ste 타일이 보이고 ste 자격 중계의 유일한 문이 열렸다). 그런데 warnings 는 비어 있었다.
def test_같은_id_로_바꾸며_추적_파일의_타일과_백엔드를_떨구면_알린다(box):
    base, local = box
    _write(local, "platforms:\n  - {id: alpha, label: Alpha, gateway: [alpha-box]}\n")
    pol = parse_policy(load_raw(base))
    assert pol.system_key("alpha") is None and "alpha" not in pol.gateway_policy(), "바꿔 쓰는 규칙 자체는 그대로다"
    assert pol.gateway_policy()["alpha-box"] == ["plat:alpha"]
    (note,) = pol.warnings
    assert "access.local.yaml" in note and "alpha" in note, note
    assert "타일" in note and "게이트웨이" in note, "무엇이 빠졌는지 종류와 함께 말한다"
    assert "통째로" in note, "왜 빠졌는지(합치지 않는다)와 무엇을 해야 하는지 말한다"


def test_타일_없는_플랫폼의_백엔드만_떨궈도_알린다(box):
    """타일이 없는 백엔드(대부분의 플랫폼이 그렇다)는 '표 밖의 타일' 확인에도 안 걸려, 실행 중에 알릴 자리가 여기뿐이다."""
    base, local = box
    _write(local, "platforms:\n  - {id: beta, label: B}\n")
    pol = parse_policy(load_raw(base))
    assert "beta" not in pol.gateway_policy()
    (note,) = pol.warnings
    assert "beta" in note and "게이트웨이" in note and "타일" not in note


@pytest.mark.parametrize("overlay", [
    "platforms:\n  - {id: alpha, label: Alpha(박스), systems: [alpha], gateway: [alpha, alpha-box]}\n",      # 다시 적었다
    "platforms:\n  - {id: alpha, label: Alpha}\n  - {id: moved, label: M, systems: [alpha], gateway: [alpha]}\n",   # 다른 플랫폼으로 옮겼다
    "platforms:\n  - {id: gamma, label: Gamma, gateway: [gamma]}\n",                                         # 새 id 만 더했다
], ids=["다시_적음", "옮김", "더하기만"])
def test_떨군_것이_없으면_조용하다(box, overlay):
    """어느 플랫폼으로든 표에 남아 있으면 막힌 채다 — 바꿔 쓰기는 타일·백엔드를 다른 플랫폼으로 옮기는 길이기도 하다."""
    base, local = box
    _write(local, overlay)
    pol = parse_policy(load_raw(base))
    assert not pol.warnings, pol.warnings
    assert pol.system_key("alpha") is not None and "alpha" in pol.gateway_policy()


def test_기능이_같은_백엔드를_쥐고_있으면_떨군_것이_아니다(tmp_path):
    """게이트웨이 정책은 기능·플랫폼을 가리지 않고 모은다 — 기능 쪽에 남아 있는 백엔드는 여전히 표 안이다."""
    base = _write(tmp_path / "access.yaml", BASE.replace("{id: chat, label: 일반 챗}", "{id: chat, label: 일반 챗, gateway: [beta]}"))
    _write(tmp_path / "access.local.yaml", "platforms:\n  - {id: beta, label: B}\n")
    pol = parse_policy(load_raw(base))
    assert pol.gateway_policy()["beta"] == ["feat:chat"] and not pol.warnings


def test_플랫폼_밖의_절은_추적_파일_것이고_박스_파일에_적으면_알린다(box):
    """소속·기본 허가를 박스 파일로 바꿀 수 있으면 추적되지 않는 파일 한 줄이 전원의 권한이 된다. 읽지 않되 **말한다** —
    적었는데 아무 일도 없으면 사람은 오타를 찾는다."""
    base, local = box
    _write(local, LOCAL + 'affiliations:\n  - {id: ROGUE, grants: ["*"]}\ndefault_grants: ["*"]\nfeatures: []\n')
    pol = parse_policy(load_raw(base))
    assert sorted(pol.affiliations) == ["CAEG", "LAB"] and pol.default_grants == ["feat:chat"]
    assert pol.item("feat:chat") is not None
    (note,) = pol.warnings
    assert all(k in note for k in ("affiliations", "default_grants", "features")), note


def test_박스_파일을_나중에_만들거나_고치거나_지우면_다음_요청부터_반영된다(box, tmp_path):
    """캐시 열쇠가 추적 파일 mtime 하나면 박스 파일을 고쳐도 재기동 전까지 옛 정책이다 — 두 파일을 함께 본다."""
    base, local = box
    ap = AccessPolicy(Settings(access_path=str(base)))
    assert "gamma" not in ap.get().gateway_policy()
    _write(local, LOCAL)
    assert "gamma" in ap.get().gateway_policy(), "새로 만든 박스 파일"
    _write(local, LOCAL.replace("gamma", "delta"), tick=5)
    assert "delta" in ap.get().gateway_policy() and "gamma" not in ap.get().gateway_policy(), "고친 박스 파일"
    local.unlink()
    assert sorted(ap.get().gateway_policy()) == ["alpha", "beta"], "지운 박스 파일"
    assert ap.problems() == []


# ── 깨진 박스 파일 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("broken", [
    "platforms: [oops\n",                                             # YAML 문법
    "- 목록이지 매핑이 아니다\n",                                        # 모양
    "platforms:\n  - {label: id 가 없다}\n",                            # 필수 칸
    "platforms:\n  - {id: beta, hide_unless_routed: true}\n",          # parse_policy 가 거절하는 값
])
def test_깨지면_직전_정책을_쓰고_그_상태가_보인다(box, broken, caplog):
    base, local = box
    _write(local, LOCAL)
    ap = AccessPolicy(Settings(access_path=str(base)))
    before = ap.get().gateway_policy()
    _write(local, broken, tick=5)
    with caplog.at_level(logging.ERROR):
        assert ap.get().gateway_policy() == before, "권한이 통째로 사라지지 않게 직전 정책"
    (why,) = ap.problems()
    assert "access.local.yaml" in why and "직전 정책" in why, "오버레이가 없는 것처럼 보이면 안 된다"
    assert any(r.levelno >= logging.ERROR for r in caplog.records)
    _write(local, LOCAL.replace("gamma", "delta"), tick=10)
    assert "delta" in ap.get().gateway_policy() and ap.problems() == [], "고치면 저절로 낫는다"


def test_문법_오류의_사유에_파일_내용을_싣지_않는다(box):
    """YAML 오류 원문은 그 줄의 내용을 인용한다 — 박스 파일에는 사내 코드가 있다. 어느 줄인지만 말한다."""
    base, local = box
    ap = AccessPolicy(Settings(access_path=str(base)))
    ap.get()
    _write(local, 'sso_affiliation_map:\n  - {claim: CompId, value: "C999-SECRET", affiliation: [CAEG\n', tick=5)
    ap.get()
    (why,) = ap.problems()
    assert "C999-SECRET" not in why and "행" in why, why


def test_처음부터_깨진_박스_파일은_추적_파일만으로_넘어가지_않는다(box):
    """직전 정책이 없을 때 추적 파일만으로 뜨면 박스 전용 백엔드가 표에서 빠진다 — 게이트웨이는 표에 없는 백엔드를
    **전체 공개**로 본다. 추적 파일이 깨졌을 때와 같이 크게 실패한다(조용히 열리는 쪽보다 낫다)."""
    base, local = box
    _write(local, "platforms: [oops\n")
    with pytest.raises(Exception):  # noqa: B017, PT011 — 어떤 파싱 오류든 삼키지 않는다는 것만 본다
        AccessPolicy(Settings(access_path=str(base))).get()


# ── SSO Claim → 소속 표(박스 파일에서만) ─────────────────────────────────────
def test_sso_소속_표는_박스_파일에서만_읽고_파일_순서대로_둔다(box):
    base, local = box
    _write(local, 'sso_affiliation_map:\n'
                  '  - {claim: CompId, value: " C999 ", affiliation: CAEG}\n'
                  '  - {claim: "http://idp.example/claims/DeptId", value: "D12345", affiliation: LAB}\n')
    pol = parse_policy(load_raw(base))
    assert [(r.claim, r.value, r.affiliation) for r in pol.sso_affiliation_map] == [
        ("CompId", "C999", "CAEG"), ("http://idp.example/claims/DeptId", "D12345", "LAB")]
    assert not pol.warnings


def test_추적_파일에_적은_sso_소속_표는_읽지_않고_알린다(tmp_path):
    """Claim 값(회사·부서 코드)은 사내 식별자다 — 추적 파일에 적힌 표가 먹으면 다음 사람은 거기에 실값을 적는다."""
    base = _write(tmp_path / "access.yaml",
                  BASE + 'sso_affiliation_map:\n  - {claim: CompId, value: "C999", affiliation: CAEG}\n')
    pol = parse_policy(load_raw(base))
    assert pol.sso_affiliation_map == ()
    (note,) = pol.warnings
    assert "access.local.yaml" in note


def test_sso_소속_표의_틀린_행은_버리고_크게_알린다(box, caplog):
    """모르는 소속·빈 칸·숫자로 읽힌 코드는 조용히 안 맞는 행이 된다 — 버리고, 몇 번째 행이 왜 버려졌는지 남긴다.
    ⚠ Claim **값**은 알림에 싣지 않는다(사내 코드)."""
    base, local = box
    _write(local, 'sso_affiliation_map:\n'
                  '  - {claim: CompId, value: "C999", affiliation: CAEG}\n'      # 1 정상
                  '  - {claim: CompId, value: "C998", affiliation: NOPE}\n'      # 2 모르는 소속
                  '  - {claim: CompId, value: 0123, affiliation: CAEG}\n'        # 3 숫자로 읽힌 코드(8진수 83 이 된다)
                  '  - {claim: "", value: "C997", affiliation: CAEG}\n'          # 4 빈 Claim
                  '  - [CompId, C996, CAEG]\n'                                   # 5 모양
                  '  - {claim: DeptId, value: "D12345", affiliation: LAB}\n')    # 6 정상
    with caplog.at_level(logging.WARNING):
        pol = parse_policy(load_raw(base))
    assert [(r.claim, r.affiliation) for r in pol.sso_affiliation_map] == [("CompId", "CAEG"), ("DeptId", "LAB")]
    assert len(pol.warnings) == 4
    joined = "\n".join(pol.warnings)
    assert all(f"{n}번째" in joined for n in (2, 3, 4, 5)) and "NOPE" in joined
    assert not any(v in joined for v in ("C998", "C997", "C996", "83")), "Claim 값이 알림에 실렸다"
    assert sum("sso_affiliation_map" in r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING) == 4


def test_sso_소속_표가_목록이_아니면_통째로_버리고_알린다(box):
    base, local = box
    _write(local, "sso_affiliation_map: {claim: CompId}\n")
    pol = parse_policy(load_raw(base))
    assert pol.sso_affiliation_map == () and len(pol.warnings) == 1


def test_추적_파일의_예시는_주석이라_아무_표도_만들지_않는다(tmp_path):
    """예시(지어낸 값)는 주석으로만 둔다 — 풀려 있으면 박스 파일 없이도 위의 '읽지 않는다' 알림이 늘 뜬다."""
    shutil.copy(_BACKEND / "config" / "access.yaml", tmp_path / "access.yaml")
    pol = parse_policy(load_raw(tmp_path / "access.yaml"))
    assert pol.sso_affiliation_map == () and not pol.warnings
    text = (_BACKEND / "config" / "access.yaml").read_text(encoding="utf-8")
    assert "sso_affiliation_map" in text and "access.local.yaml" in text, "어디에 어떻게 적는지 추적 파일이 말해야 한다"


# ── 관리자에게 보이는 자리(배선 설정) ─────────────────────────────────────────
@pytest.mark.anyio
async def test_배선_확인은_정책_문제가_있으면_todo_없으면_ok(box):
    base, local = box
    ap = AccessPolicy(Settings(access_path=str(base)))
    assert await run_check("access_overlay", Settings(), ap) == "ok"
    _write(local, "sso_affiliation_map:\n  - {claim: CompId, value: \"C999\", affiliation: NOPE}\n")
    assert await run_check("access_overlay", Settings(), ap) == "todo"
    assert await run_check("access_overlay", Settings(), None) == "unknown", "모르면 모른다고 한다"


def test_추적된_배선_목록에_이_확인이_있다():
    doc = yaml.safe_load((_BACKEND / "config" / "setup_requests.yaml").read_text("utf-8"))
    (row,) = [r for r in parse_requests(doc) if r["check"] == "access_overlay"]
    assert "access.local.yaml" in row["body"] and not row["manual"]


@pytest.fixture()
def admin(box):
    base, local = box
    s = Settings(user_store_path=str(base.parent / "u.sqlite"), local_bootstrap_admins="boss@corp.com",
                 access_path=str(base))
    app.dependency_overrides[get_settings] = lambda: s
    from app.auth.routes.local import _rl
    _rl.clear()
    with TestClient(app) as c:
        keep = app.state.access
        app.state.user_store = UserStore(s)            # 컨텍스트 진입 후 교체(실DB 오염 방지)
        app.state.access = AccessPolicy(s)
        c.post("/auth/local/signup", json={"email": "boss@corp.com", "name": "B", "password": "pw123456"})
        assert c.post("/auth/local/login", json={"email": "boss@corp.com", "password": "pw123456"}).status_code == 200
        yield c, local
        app.state.access = keep
    app.dependency_overrides.pop(get_settings, None)


def _overlay_item(c):
    return next((i for i in c.get("/setup/requests").json()["items"] if i.get("check") == "access_overlay"), None)


def test_관리자_화면은_멀쩡하면_조용하고_깨지면_무엇이_문제인지_말한다(admin):
    c, local = admin
    assert _overlay_item(c) is None, "된 것은 화면에서 사라진다"
    _write(local, LOCAL)
    assert _overlay_item(c) is None
    _write(local, "platforms: [oops\n", tick=5)
    item = _overlay_item(c)
    assert item and item["state"] == "todo"
    assert any("직전 정책" in n for n in item["notes"]), item["notes"]
    _write(local, LOCAL + 'sso_affiliation_map:\n  - {claim: CompId, value: "C999", affiliation: NOPE}\n', tick=10)
    item = _overlay_item(c)
    assert item and any("1번째" in n and "NOPE" in n for n in item["notes"]), item
    assert "C999" not in str(item)
    # 추적 플랫폼을 바꿔 쓰며 타일 없는 백엔드를 떨궜다 — '표 밖의 타일' 확인에는 안 걸리는 경우다
    _write(local, "platforms:\n  - {id: beta, label: B}\n", tick=15)
    item = _overlay_item(c)
    assert item and item["state"] == "todo" and any("beta" in n and "게이트웨이" in n for n in item["notes"]), item
