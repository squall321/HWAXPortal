# update-all §5 의 StepForge 단언 쓰기 배선(docs/core-link SRC-15) — provision 으로 넘기는 비밀 · 드리프트 판정 · 재검증 · ○ 한 줄
"""게이트웨이는 heax_registry.rest_sso.step_forge 와 rest.step-forge 의 delegate · write_paths 를 provision 에서 만든다(게이트웨이 가지
wt1109/core-link). update-all 은 provision.env 의 STEPFORGE_SSO_SECRET(· STEPFORGE_SSO_URL)을 넘기고, 비밀이 있는데 칸이 어긋나면 재프로비저닝한다."""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UA = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    m = re.search(rf"(?ms)^{name}\(\) \{{[^\n]*\n.*?^\}}\n", UA)   # 첫 줄 꼬리에 주석이 붙는다
    assert m, name
    return m.group(0)


def _ok(tmp_path: Path, cfg, *, secret="s3cret", url=""):
    p = tmp_path / "gateway_config.json"
    p.write_text(cfg if isinstance(cfg, str) else json.dumps(cfg), encoding="utf-8")
    script = f'set -uo pipefail\n{_fn("_sf_rest_sso_ok")}STEPFORGE_SSO_SECRET="{secret}" STEPFORGE_SSO_URL="{url}"\n' \
             f'_sf_rest_sso_ok "{p}"; echo "rc=$?"\n'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


GOOD = {"heax_registry": {"rest_sso": {"step_forge": {"sso_url": "http://hub/apps/step_forge/api/auth/sso", "secret": "s3cret",
                                                       "client": "gateway", "auth": "heax", "token_header": "X-Heax-Sso-Assertion"}}},
        "rest": {"step-forge": {"base": "http://hub/apps/step_forge", "delegate": "step_forge",
                                "write_paths": ["/api/onto-link", "/api/onto-put", "/api/onto-define"]}}}


def _with(**chg):
    d = json.loads(json.dumps(GOOD))
    for path, v in chg.items():
        cur = d
        keys = path.split("__")
        for k in keys[:-1]:
            cur = cur[k.replace("_dash_", "-")]
        if v is None:
            cur.pop(keys[-1].replace("_dash_", "-"), None)
        else:
            cur[keys[-1].replace("_dash_", "-")] = v
    return d


def test_맞으면_0(tmp_path):
    assert _ok(tmp_path, GOOD) == "rc=0"
    assert _ok(tmp_path, GOOD, url="http://hub/apps/step_forge/api/auth/sso") == "rc=0"


@pytest.mark.parametrize("cfg, kw", [
    (_with(heax_registry__rest_sso__step_forge__secret="other"), {}),          # 비밀을 바꿨다
    (_with(heax_registry__rest_sso=None), {}),                                  # 위임 칸이 없다(옛 게이트웨이 · 첫 실행)
    (_with(rest__step_dash_forge__write_paths=None), {}),                       # 쓰기 경로가 없다
    (_with(rest__step_dash_forge__delegate=None), {}),
    (GOOD, {"url": "http://elsewhere/sso"}),                                   # 주소를 바꿨다
    ("{not json", {}),                                                          # 못 읽으면 어긋남 — 재프로비저닝이 고친다
])
def test_어긋나면_1(tmp_path, cfg, kw):
    assert _ok(tmp_path, cfg, **kw) == "rc=1"


def _block(start: str, end: str) -> str:
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


def test_provision_으로_비밀과_주소를_넘긴다():
    chain = _block('if ( cd "$GW_DIR" && export PER_USER_SSO_APPS', "bash provision-config.sh --force )")
    assert 'STEPFORGE_SSO_SECRET="${STEPFORGE_SSO_SECRET:-}" STEPFORGE_SSO_URL="${STEPFORGE_SSO_URL:-}"' in chain
    assert "#" not in chain.replace("${#", ""), "대입어 사슬 안에 주석을 두지 않는다(백틱 주석이 사슬을 죽인다)"


def test_비밀이_있는데_칸이_어긋나면_재프로비저닝하고_뒤에서_다시_본다():
    pre = _block('MISSING="hwax_risk_sso${MISSING:+ $MISSING}"', "# 키는 있는데 **주소가 틀려서**")
    assert '[ -n "${STEPFORGE_SSO_SECRET:-}" ]' in pre and '! _sf_rest_sso_ok "$GW_DIR/gateway_config.json"' in pre
    assert 'MISSING="step_forge_rest_sso${MISSING:+ $MISSING}"' in pre
    post = _block("# 재검증 ② 재프로비저닝으로 실제 해소됐는지", "주소 드리프트 해소")
    assert "_sf_rest_sso_ok" in post and "step_forge_rest_sso(" in post
    assert UA.index("_sf_rest_sso_ok() {") < UA.index('&& ! _sf_rest_sso_ok "$GW_DIR/gateway_config.json"'), "판정 함수가 먼저 정의된다"
    assert UA.index('. "$PROV_ENV"') < UA.index('MISSING="step_forge_rest_sso'), "provision.env 를 소싱한 뒤에 본다"


def test_허브가_있고_비밀이_없으면_안_켠_줄을_남긴다():
    blk = _block("# StepForge 단언 쓰기(docs/core-link SRC-15 · SRC-07) — 게이트웨이 provision.env 에", "# ARP(AI Ready Portal) MCP")
    assert '[ -n "${HEAX_DIR:-}" ]' in blk and '_envfile_value "$GW_DIR/provision.env" STEPFORGE_SSO_SECRET' in blk
    assert 'hwax_skip "StepForge 단언 쓰기' in blk and "STEPFORGE_SSO_SECRET=" in blk
    assert UA.index("_envfile_value() {") < UA.index(blk), "파일 읽기 함수가 먼저 정의된다"


def test_머리_준비물에_적는다():
    head = UA[:UA.index("set -uo pipefail")]
    assert "STEPFORGE_SSO_SECRET=" in head and "secrets.env 의 STEPFORGE_SSO_SECRET" in head, "StepForge 쪽 줄 이름을 같이 적는다"
