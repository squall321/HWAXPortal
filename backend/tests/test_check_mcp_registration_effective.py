# check-mcp-registration.sh 가 허브와 같은 효과 매니페스트(추적 manifest.yaml + 박스 덮어쓰기 manifest.local.yaml)로 업스트림 · 선언을 보는지 — 가짜 허브 · 가짜 curl 로 본다
"""왜 — HEAXHub HH-15(10-31, main 055b023)부터 통합 앱 폴더의 `.portal/manifest.local.yaml` 이 추적 매니페스트 위에 RFC 7386 병합 패치로
얹힌다(허브의 스캐너 · reconcile · 런처가 모두 그 효과 값으로 돈다). 이 점검은 추적 파일을 grep 해 `mode: proxy` · `upstream:` 을 두드렸다 —
운영 전환(HH-14) 뒤 dev 는 추적 업스트림(운영 노드 16121 · 16110)이 아니라 덮어쓴 8701 · 서비스로 돌아, 멀쩡한 앱을 '업스트림 무응답' NG ·
rc 1 로 읽는다. id 를 찾는 grep 도 줄 끝에 앵커를 걸어 꼬리 주석이 달린 `id: step_forge   # …` 를 '매니페스트 없음' 으로 읽었다
(HEAXHub cutover context-notes 「포털에 알릴 것」 · 검토 #4).

  · 덮어쓴 업스트림을 두드린다 — 추적 값은 두드리지 않는다.
  · 꼬리 주석이 달린 id 를 찾고, 서비스로 덮어쓴 앱은 상태 파일로 본다(추적 proxy 업스트림을 두드리지 않는다).
  · 덮어쓰기를 못 얹으면(허브가 그 앱을 보류한다) 보류를 NG 로 알리고, 지금 걸린 업스트림(상태 파일의 마지막 proxy 기록)을 두드린다.
  · 로더가 없으면(venv 없음 · HH-15 전의 HEAXHub) 한 줄 알리고 예전처럼 추적 파일로 읽는다.
  · 허브는 이 리포의 형제(../HEAXHub)에서 찾는다 — 박힌 절대경로는 리포 루트가 다른 박스(cae00)에서 못 찾는다.
로더는 형제 HEAXHub 의 진짜를 쓴다(가짜는 진짜 꼴이어야 한다) — 없으면 그 시험만 건너뛴다.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra/scripts/check-mcp-registration.sh"
REAL_APP = Path(__file__).resolve().parents[3] / "HEAXHub" / "backend" / "app"
_LOADER_FILES = ("core/logger.py", "core/errors.py", "services/integration_manifest.py", "services/stack_resolver.py")

_FAKE_CURL = r'''#!/usr/bin/env bash
# 시험용 대역 — 받은 주소를 적고, 살아 있다고 한 주소(FAKE_LIVE)만 답한다. 실제 허브 · 게이트웨이에 닿지 않는다.
url="" hdr="" w=""
while [ $# -gt 0 ]; do
  case "$1" in
    -D) hdr="$2"; shift 2 ;;
    -D*) hdr="${1#-D}"; shift ;;
    -w) w="$2"; shift 2 ;;
    -o|-H|-X|-d|--max-time) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
echo "$url" >> "$CURL_LOG"
case "$url" in
  */tools-map) cat "$FAKE_DIR/tools-map.json"; exit 0 ;;
  */api/v1/mcp/servers) cat "$FAKE_DIR/servers.json"; exit 0 ;;
  */apps/*/mcp) printf 'HTTP/1.1 200 OK\r\nmcp-session-id: s1\r\ncontent-type: application/json\r\n\r\n' > "$hdr"; exit 0 ;;
esac
for u in $FAKE_LIVE; do
  if [ "$u" = "$url" ]; then [ -n "$w" ] && printf 200; exit 0; fi
done
[ -n "$w" ] && printf 000
exit 7
'''

# 운영 전환(HH-14) 뒤의 추적 매니페스트 꼴 — 운영 노드로 넘기는 proxy 앱(kooremapper_mcp)과 꼬리 주석이 달린 id(step_forge).
_KRM_TRACKED = """schema_version: 2
id: kooremapper_mcp
name: "DynaForge MCP"
status: stable
app_type: external_link
execution_target: external_url
build:
  stack: external_proxy
launch:
  mode: proxy
  upstream: http://127.0.0.1:16121     # 운영 노드 DynaForge MCP(streamable-http)
  strip_prefix: true
permissions:
  visibility: company
mcp:
  expose: true
  path: /mcp
  transport: streamable_http
"""
_SF_TRACKED = """schema_version: 2
id: step_forge            # /apps/step_forge · state · 인스턴스명의 원천
name: StepForge
status: beta              # draft 는 MCP 레지스트리에서 제외된다
app_type: web_app
execution_target: external_url
build:
  stack: external_proxy
launch:
  mode: proxy
  upstream: http://127.0.0.1:16110     # cae00 hwaxprod-tunnel → 운영 노드 StepForge
  strip_prefix: true
  portal_auth: true
permissions:
  visibility: company
mcp:
  expose: true
  path: /mcp
  transport: streamable_http
"""
# dev 의 박스 덮어쓰기 — HEAXHub MANIFEST_SPEC 10절의 예 그대로(서비스로 되돌린다 · proxy 키는 지운다).
_SF_DEV_LOCAL = {
    "execution_target": "linux_runner",
    "build": {"stack": "fastapi", "type": "python_venv", "python_version": "3.12"},
    "launch": {"mode": "service", "upstream": None, "strip_prefix": None, "health_check": {"type": "http", "path": "/health"}},
}


class Box:
    """tmp/HWAXPortal(점검 스크립트 사본) · tmp/HEAXHub(integrations · var/integration_state · backend) · tmp/stub/curl(대역)
    · tmp/fake(레지스트리 · 게이트웨이 응답) · tmp/gw/gateway_config.json.

    허브 자리는 HUB_ROOT 로 이 tmp 를 준다 — 주지 않으면 옛 스크립트는 박힌 절대경로로 이 박스의 실 허브를 읽는다(그 값으로 통과 · 실패가 갈린다).
    기본값이 형제(../HEAXHub)인지는 run(default_hub=True) 로 따로 본다.
    loader — "real": backend/.venv(이 시험의 venv) + 형제 HEAXHub 의 진짜 로더 · "old": venv 는 있는데 로더 모듈이 없다(HH-15 전) · "none": venv 없음.
    """

    def __init__(self, tmp: Path, loader: str = "real"):
        if loader == "real" and not all((REAL_APP / rel).is_file() for rel in _LOADER_FILES):
            pytest.skip(f"형제 리포 HEAXHub 에 HH-15 로더가 없다: {REAL_APP / 'services/integration_manifest.py'}")
        if loader != "none" and not (Path(sys.prefix) / "bin" / "python").exists():
            pytest.skip(f"이 시험의 venv 에 bin/python 이 없다: {sys.prefix}")
        self.tmp = tmp
        portal = tmp / "HWAXPortal"
        (portal / "infra/scripts").mkdir(parents=True)
        self.script = portal / "infra/scripts/check-mcp-registration.sh"
        shutil.copy(SCRIPT, self.script)
        self.hub = tmp / "HEAXHub"
        (self.hub / "integrations").mkdir(parents=True)
        (self.hub / "var/integration_state").mkdir(parents=True)
        if loader != "none":
            backend = self.hub / "backend"
            backend.mkdir()
            (backend / ".venv").symlink_to(sys.prefix)
            for sub in ("", "core", "services"):
                (backend / "app" / sub).mkdir(parents=True, exist_ok=True)
                (backend / "app" / sub / "__init__.py").write_text("", encoding="utf-8")
            if loader == "real":
                for rel in _LOADER_FILES:
                    (backend / "app" / rel).symlink_to(REAL_APP / rel)
        stub = tmp / "stub"
        stub.mkdir()
        (stub / "curl").write_text(_FAKE_CURL, encoding="utf-8")
        (stub / "curl").chmod(0o755)
        self.fake = tmp / "fake"
        self.fake.mkdir()
        gw = tmp / "gw" / "gateway_config.json"
        gw.parent.mkdir()
        gw.write_text(json.dumps({"heax_registry": {"servers_url": "http://127.0.0.1:9/api/v1/mcp/servers",
                                                    "base": "http://127.0.0.1:9", "token": "t"}}), encoding="utf-8")
        self.curl_log = tmp / "curl.log"
        self.env = {"PATH": f"{stub}:/usr/bin:/bin", "HOME": str(tmp), "GATEWAY_CONFIG": str(gw),
                    "GW_HTTP": "http://127.0.0.1:9", "CURL_LOG": str(self.curl_log), "FAKE_DIR": str(self.fake),
                    "FAKE_LIVE": "", "PYTHONDONTWRITEBYTECODE": "1", "HUB_ROOT": str(self.hub)}
        who = subprocess.run(["bash", "-c", "command -v curl"], env=self.env, capture_output=True, text=True).stdout.strip()
        assert who == str(stub / "curl"), f"대역이 아니라 {who} 가 불린다 — 떠 있는 허브 · 게이트웨이로 나간다"

    def app(self, d: str, app_id: str, tracked: str, local: str | dict | None = None, state: dict | None = None) -> None:
        """integrations/<d>/.portal/manifest.yaml(+ manifest.local.yaml) · 상태 파일 · 레지스트리 · 게이트웨이가 그 앱을 노출한다고 답한다."""
        p = self.hub / "integrations" / d / ".portal"
        p.mkdir(parents=True)
        (p / "manifest.yaml").write_text(tracked, encoding="utf-8")
        if local is not None:
            (p / "manifest.local.yaml").write_text(local if isinstance(local, str) else yaml.safe_dump(local, allow_unicode=True),
                                                   encoding="utf-8")
        if state is not None:
            (self.hub / "var/integration_state" / f"{app_id}.json").write_text(json.dumps(state), encoding="utf-8")
        (self.fake / "servers.json").write_text(json.dumps({"servers": [
            {"id": app_id, "name": app_id, "description": "d", "path": f"/apps/{app_id}/mcp", "allowed_groups": []}]}), encoding="utf-8")
        (self.fake / "tools-map.json").write_text(json.dumps({"apps": [
            {"app": f"heax-{app_id}", "tool_count": 3, "reachable": True, "label": app_id}]}), encoding="utf-8")

    def run(self, app_id: str, live: str = "", default_hub: bool = False) -> tuple[subprocess.CompletedProcess, list[str]]:
        env = {**self.env, "FAKE_LIVE": live}
        if default_hub:
            del env["HUB_ROOT"]
        r = subprocess.run(["bash", str(self.script), app_id], capture_output=True, text=True, timeout=120, env=env)
        called = self.curl_log.read_text(encoding="utf-8").split() if self.curl_log.exists() else []
        return r, called


def test_덮어쓴_업스트림을_두드린다_추적_값이_아니라(tmp_path):
    b = Box(tmp_path)
    b.app("kooremapper-mcp", "kooremapper_mcp", _KRM_TRACKED, {"launch": {"upstream": "http://127.0.0.1:8701"}},
          state={"mode": "proxy", "upstream": "http://127.0.0.1:8701"})
    r, called = b.run("kooremapper_mcp", live="http://127.0.0.1:8701")
    out = r.stdout + r.stderr
    assert "업스트림 응답 (HTTP 200): http://127.0.0.1:8701" in r.stdout, out
    assert "http://127.0.0.1:16121" not in called, f"추적 파일의 업스트림을 두드렸다: {called}"
    assert "박스 덮어쓰기 integrations/kooremapper-mcp/.portal/manifest.local.yaml 을 얹은 효과 값으로 본다" in r.stdout, out
    assert "바뀐 최상위 키: launch" in r.stdout, out
    assert r.returncode == 0, out


def test_꼬리_주석이_달린_id_를_찾고_서비스로_덮어쓴_앱은_상태_파일로_본다(tmp_path):
    b = Box(tmp_path)
    b.app("step_forge", "step_forge", _SF_TRACKED, _SF_DEV_LOCAL, state={"mode": "service", "port": 9400})
    r, called = b.run("step_forge")
    out = r.stdout + r.stderr
    assert "매니페스트: integrations/step_forge/.portal/manifest.yaml" in r.stdout, out
    assert "2) 기동 이력(상태 파일)" in r.stdout and "상태 파일 있음: var/integration_state/step_forge.json" in r.stdout, out
    assert "http://127.0.0.1:16110" not in called, f"서비스로 덮어쓴 앱의 추적 proxy 업스트림을 두드렸다: {called}"
    assert r.returncode == 0, out


def test_덮어쓰기를_못_얹으면_보류를_알리고_마지막으로_건_업스트림을_두드린다(tmp_path):
    b = Box(tmp_path)
    b.app("kooremapper-mcp", "kooremapper_mcp", _KRM_TRACKED, "launch: {upstream: http://127.0.0.1:8701\n",   # 닫는 괄호가 빠졌다
          state={"mode": "proxy", "upstream": "http://127.0.0.1:8701"})                               # 허브가 마지막으로 얹은 값
    r, called = b.run("kooremapper_mcp", live="http://127.0.0.1:8701")
    out = r.stdout + r.stderr
    assert "✘ 보류 — 박스 덮어쓰기 integrations/kooremapper-mcp/.portal/manifest.local.yaml 을 얹지 못해" in r.stdout, out
    assert "YAML" in r.stdout, "보류의 까닭(로더가 준 것)을 보여야 한다 — " + out
    assert "http://127.0.0.1:16121" not in called, f"보류 중인데 추적 파일의 업스트림을 두드렸다: {called}"
    assert "업스트림 응답 (HTTP 200): http://127.0.0.1:8701" in r.stdout, "지금 걸린(마지막으로 얹은) 업스트림을 두드려야 한다 — " + out
    assert r.returncode == 1, "보류는 사람이 고칠 일이다 — NG 로 끝나야 한다\n" + out


@pytest.mark.parametrize("loader", ["none", "old"], ids=["venv_없음", "HH-15_전_허브"])
def test_로더가_없으면_한_줄_알리고_추적_파일로_읽는다(tmp_path, loader):
    b = Box(tmp_path, loader=loader)
    tracked = _KRM_TRACKED.replace("id: kooremapper_mcp\n", "id: kooremapper_mcp   # 게이트웨이 키 heax-kooremapper_mcp\n")
    # 덮어쓰기가 있는데 로더를 못 부르면 허브 값과 다를 수 있다고 알린다. 덮어쓰기가 없으면 추적 값이 곧 허브 값이다.
    b.app("kooremapper-mcp", "kooremapper_mcp", tracked, {"launch": {"upstream": "http://127.0.0.1:8701"}} if loader == "none" else None,
          state={"mode": "proxy", "upstream": "http://127.0.0.1:16121"})
    r, called = b.run("kooremapper_mcp", live="http://127.0.0.1:16121")
    out = r.stdout + r.stderr
    notice = [ln for ln in r.stdout.splitlines() if "HEAXHub 로더를 못 불러 추적 manifest.yaml 로 읽는다" in ln]
    assert len(notice) == 1, "로더가 없다는 것을 한 줄로 알려야 한다 — " + out
    if loader == "none":
        assert "backend/.venv/bin/python 없음" in notice[0] and "옆의 manifest.local.yaml" in notice[0], notice[0]
    else:
        assert "로더 없음(ModuleNotFoundError" in notice[0] and "박스 덮어쓰기가 없어 허브도 이 값으로 돈다" in notice[0], notice[0]
    assert "매니페스트: integrations/kooremapper-mcp/.portal/manifest.yaml" in r.stdout, "꼬리 주석이 달린 id 를 못 찾았다 — " + out
    assert "업스트림 응답 (HTTP 200): http://127.0.0.1:16121" in r.stdout and "mcp.expose: true" in r.stdout, out
    assert r.returncode == 0, out


def test_허브는_이_리포의_형제에서_찾는다(tmp_path):
    """HUB_ROOT 를 주지 않으면 ../HEAXHub 다 — 절대경로(/home/…/claude/HEAXHub)를 박으면 리포 루트가 다른 cae00(~/Projects)에서 매니페스트도 로더도 못 찾는다.
    id 는 이 박스의 실 허브에 없는 것을 쓴다(옛 스크립트가 실 허브를 읽어도 우연히 통과하지 않게)."""
    b = Box(tmp_path)
    b.app("sibling-probe", "sibling_probe", _KRM_TRACKED.replace("id: kooremapper_mcp", "id: sibling_probe"),
          {"launch": {"upstream": "http://127.0.0.1:8702"}}, state={"mode": "proxy", "upstream": "http://127.0.0.1:8702"})
    r, called = b.run("sibling_probe", live="http://127.0.0.1:8702", default_hub=True)
    out = r.stdout + r.stderr
    assert "매니페스트: integrations/sibling-probe/.portal/manifest.yaml" in r.stdout, out
    assert "업스트림 응답 (HTTP 200): http://127.0.0.1:8702" in r.stdout, "형제 허브의 로더로 덮어쓴 값을 읽어야 한다 — " + out
    assert r.returncode == 0, out
