# nginx 스트리밍 두 경로(/agent/ · /mcp-gw/)의 침묵 한도가 손잡이 둘로 두 서버 블록에 같이 들어가는지, 틀린 값이 정문을 내리지 않는지
"""왜 — `/agent/` 의 proxy_read_timeout 은 `1h` 리터럴이었고 HTTP 서버(템플릿)와 TLS 서버(생성기 안의 사본)에 따로 박혀 있었다.
침묵 한도라 신호를 내는 심의는 끊지 않지만, 좌석 20석 넘는 패널은 LLM 호출 한 번(재시도 포함 3608초)이 통째로 조용하다 —
1시간에 nginx 가 끊으면 심의는 서버에서 계속 도는데 화면에는 사유 없는 'network error' 만 남고, '다시 시도' 가 두 번째 심의를
나란히 돌린다. 값을 올리고(기본 50400s) 손잡이로 낸다 — 포털 릴레이(46800초) < nginx(50400초) < 리스크 앱(54000초)의 가운데다.

생성기를 임시 리포에서 **실제로 돌려** 만들어진 conf 를 본다(스크립트·템플릿은 사본, infra/.env·라우트는 지어낸 값).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _generate(tmp_path: Path, *, tls: bool = True, infra_env: str = "", backend_env: str | None = None) -> tuple[str, str]:
    """(만들어진 conf, 화면 출력) — TLS 를 켜면 서버 블록이 둘이다."""
    repo = tmp_path / "HWAXPortal"
    (repo / "infra/scripts").mkdir(parents=True); (repo / "infra/nginx").mkdir(); (repo / "backend/config").mkdir(parents=True)
    for f in ("gen-nginx-conf.sh", "_common.sh"):
        shutil.copy(ROOT / "infra/scripts" / f, repo / "infra/scripts" / f)
    shutil.copy(ROOT / "infra/nginx/hwax.conf.tmpl", repo / "infra/nginx/hwax.conf.tmpl")
    (repo / "infra/.env").write_text("HTTP_PORT=8088\nPORTAL_PORT=8723\n"
                                     + ("ENABLE_TLS=true\nTLS_SERVER_NAME=hwax.example\n" if tls else "") + infra_env)
    (repo / "backend/config/routes.env").write_text("ai-data-hub=http://127.0.0.1:8001/\n")
    if backend_env is not None:
        (repo / "backend/.env").write_text(backend_env)
    r = subprocess.run(["bash", str(repo / "infra/scripts/gen-nginx-conf.sh")], capture_output=True, text=True, timeout=60,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    return (repo / "infra/nginx/hwax.conf").read_text(encoding="utf-8"), r.stdout + r.stderr


def _blocks(conf: str, loc: str) -> list[str]:
    """`location <loc> { … }` 블록 본문 전부 — HTTP 서버 하나, TLS 를 켜면 둘."""
    return re.findall(r"^        location " + re.escape(loc) + r" \{\n(.*?)^        \}\n", conf, re.S | re.M)


def _secs(value: str) -> int:
    n, unit = re.fullmatch(r"(\d+)([smhd]?)", value).groups()
    return int(n) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def _read_timeouts(conf: str, loc: str) -> list[str]:
    return [re.search(r"proxy_read_timeout ([^;]+);", b).group(1) for b in _blocks(conf, loc)]


@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_기본값이_두_서버_블록에_같이_들어간다(tmp_path, tls):
    """**이 시험이 이 파일의 이유다** — /agent/ 는 14시간, /mcp-gw/ 는 1시간. TLS 사본만 옛 값으로 남으면 운영(HTTPS)만 끊긴다."""
    conf, out = _generate(tmp_path, tls=tls)
    servers = 2 if tls else 1
    assert _read_timeouts(conf, "/agent/") == ["50400s"] * servers
    assert _read_timeouts(conf, "/mcp-gw/") == ["1h"] * servers
    assert "{{" not in conf, "채우지 못한 토큰이 남으면 nginx 가 [emerg] 로 뜨지 않는다"
    assert "⚠" not in out and "✗" not in out, out


@pytest.mark.parametrize("tls", [False, True], ids=["http", "http+tls"])
def test_연결_타임아웃은_죽은_상대만_잡게_짧다(tmp_path, tls):
    """300s 는 nginx 가 실제로 쓰는 범위(약 75초) 밖이었고 localhost 에서 얻는 것이 없다 — 느린 일이 아니라 죽은 상대를 재는 값이다."""
    conf, _ = _generate(tmp_path, tls=tls)
    for loc in ("/agent/", "/mcp-gw/"):
        blocks = _blocks(conf, loc)
        assert len(blocks) == (2 if tls else 1), loc
        for b in blocks:
            assert "proxy_connect_timeout 10s;" in b, loc
    assert "proxy_connect_timeout 300s" not in conf


def test_손잡이_둘이_두_서버_블록을_함께_바꾼다(tmp_path):
    conf, out = _generate(tmp_path, infra_env="NGINX_AGENT_READ_TIMEOUT=20h   # 박스 사정\nNGINX_MCP_READ_TIMEOUT=7200\n")
    assert _read_timeouts(conf, "/agent/") == ["20h", "20h"]
    assert _read_timeouts(conf, "/mcp-gw/") == ["7200", "7200"]
    assert "⚠" not in out and "✗" not in out, out


@pytest.mark.parametrize("bad", ["1 h", "abc", "1h30m", "0", "0s", "000h", "10/20", "5&", "-5", "1.5h", "2H", "'1h;'"])
def test_모양이_틀린_값은_버리고_기본값으로_만든다(tmp_path, bad):
    """손잡이 한 줄의 오타로 정문이 내려가면 안 된다 — 틀린 값을 그대로 넣으면 nginx 가 [emerg] 로 즉사하고(`1 h` · `abc`),
    `/`·`&` 는 치환(sed)부터 깨뜨린다. **0 은 '끔' 이 아니다** — nginx 는 0 을 '즉시 끊는다' 로 읽어 모든 심의가 열리자마자 끊긴다
    (다른 손잡이들의 0=끔 을 따라 적기 쉬운 값이다)."""
    conf, out = _generate(tmp_path, infra_env=f'NGINX_AGENT_READ_TIMEOUT="{bad}"\nNGINX_MCP_READ_TIMEOUT="{bad}"\n')
    assert _read_timeouts(conf, "/agent/") == ["50400s", "50400s"], out
    assert _read_timeouts(conf, "/mcp-gw/") == ["1h", "1h"], out
    for knob in ("NGINX_AGENT_READ_TIMEOUT", "NGINX_MCP_READ_TIMEOUT"):
        assert any("✗" in ln and knob in ln and "기본값" in ln for ln in out.splitlines()), f"{knob} 를 버렸다고 말해야 한다\n{out}"
    assert "{{" not in conf and "generated" in out, "conf 는 끝까지 만들어진다"


# ── 침묵 한도의 순서 — 포털 릴레이 < nginx. 뒤집히면 nginx 가 먼저 끊어 화면에 사유가 안 나간다 ────────────────────
def _order_warning(out: str) -> bool:
    return any("⚠" in ln and "NGINX_AGENT_READ_TIMEOUT" in ln and "AGENT_STREAM_IDLE_TIMEOUT_S" in ln for ln in out.splitlines())


def test_nginx_값이_포털_릴레이보다_크지_않으면_알린다(tmp_path):
    """포털이 먼저 걸려야 손잡이 이름과 '심의는 계속 돈다' 가 화면에 간다. nginx 가 먼저면 'network error' 뿐이다.
    값은 사람이 적은 대로 넣는다(알리기만 한다) — 생성기가 고쳐 쓰면 적은 값과 도는 값이 갈린다."""
    conf, out = _generate(tmp_path / "low", infra_env="NGINX_AGENT_READ_TIMEOUT=1h\n")
    assert _order_warning(out), out
    assert _read_timeouts(conf, "/agent/") == ["1h", "1h"]
    _, out = _generate(tmp_path / "eq", infra_env="NGINX_AGENT_READ_TIMEOUT=46800\n")
    assert _order_warning(out), "같은 값도 순서가 아니다(안쪽이 **엄격히** 작아야 한다)"
    _, out = _generate(tmp_path / "ok", infra_env="NGINX_AGENT_READ_TIMEOUT=46801s\n")
    assert not _order_warning(out), out


def test_포털_값은_infra_env_가_먼저고_없으면_backend_env_다(tmp_path):
    """start.sh 는 infra/.env 의 값을 `--env` 로 넘기고 그것이 backend/.env 를 이긴다 — 같은 순서로 읽어야 실제 도는 값과 견준다."""
    _, out = _generate(tmp_path / "be", backend_env='AGENT_STREAM_IDLE_TIMEOUT_S="90000"   # 박스 값\n')
    assert _order_warning(out) and "90000초" in out, out
    _, out = _generate(tmp_path / "both", infra_env="AGENT_STREAM_IDLE_TIMEOUT_S=3000\n", backend_env="AGENT_STREAM_IDLE_TIMEOUT_S=90000\n")
    assert not _order_warning(out), out
    _, out = _generate(tmp_path / "float", infra_env="AGENT_STREAM_IDLE_TIMEOUT_S=60000.5\n")
    assert _order_warning(out) and "60000초" in out, "소수로 적은 값도 읽는다(포털 설정은 실수다)"


def test_포털_쪽을_끈_박스와_읽지_못한_값은_조용하다(tmp_path):
    """포털 릴레이의 0 은 끔(무제한)이다 — 그 박스는 nginx 가 유일한 한도라 순서를 따질 것이 없다."""
    _, out = _generate(tmp_path / "off", infra_env="AGENT_STREAM_IDLE_TIMEOUT_S=0\nNGINX_AGENT_READ_TIMEOUT=1h\n")
    assert not _order_warning(out), out
    _, out = _generate(tmp_path / "junk", infra_env='AGENT_STREAM_IDLE_TIMEOUT_S="많이"\nNGINX_AGENT_READ_TIMEOUT=1h\n')
    assert not _order_warning(out) and "generated" in out, "못 읽는 값으로 생성이 죽지 않는다"


# ── 세 리포의 기본값 — 포털 릴레이 < nginx < 리스크 앱, 그리고 셋 다 LLM 논리 호출 1회의 최악보다 크다 ─────────────────
def _sibling_default(repo: str, rel: str, *patterns: str) -> int:
    """형제 리포 소스에서 기본값을 읽는다 — 식을 차례로 대 본다(환경값 옆의 리터럴, 또는 따로 둔 기본값 상수)."""
    f = ROOT.parent / repo / rel
    if not f.exists():
        pytest.skip(f"형제 리포 없음: {f}")
    src = f.read_text(encoding="utf-8")
    for pattern in patterns:
        m = re.search(pattern, src, re.M)
        if m:
            return int(float(m.group(1)))
    pytest.skip(f"{repo} 가 아직 그 손잡이를 모르는 판이다({patterns[0]})")


def test_nginx_기본값은_포털_릴레이_기본값보다_크다(tmp_path):
    from app.config import Settings

    conf, _ = _generate(tmp_path)
    nginx = _secs(_read_timeouts(conf, "/agent/")[0])
    portal = Settings.model_fields["agent_stream_idle_timeout_s"].default
    assert 0 < portal < nginx, f"포털 릴레이 {portal}초 · nginx {nginx}초 — 안쪽이 먼저 걸려야 한다"


def test_nginx_기본값은_리스크_앱의_읽기_한도보다_작다(tmp_path):
    """가장 바깥(클라이언트)이 리스크 앱이다 — nginx 가 먼저 걸려야 'nginx 가 끊었다' 가 가려진다. 한쪽만 바꾸면 순서가 뒤집힌다."""
    conf, _ = _generate(tmp_path)
    nginx = _secs(_read_timeouts(conf, "/agent/")[0])
    risk = _sibling_default("HWAXRisk", "backend/app/config.py", r'HWAXRISK_ENGINE_READ_TIMEOUT_S"\s*,\s*"?([0-9.]+)',
                            r"^DEFAULT_ENGINE_READ_TIMEOUT_S\s*=\s*([0-9.]+)")
    assert nginx < risk, f"nginx {nginx}초 · 리스크 앱 {risk}초"


def test_nginx_기본값은_LLM_논리_호출_한_번의_최악보다_크다(tmp_path):
    """heartbeat 가 없는 옛 엔진이 섞여 돌아도(재기동을 건너뛴 박스) 요청 상한 호출 1회(2×DELIB_TIMEOUT_MAX_S+8)가 조용한 사이에
    끊기지 않아야 한다."""
    conf, _ = _generate(tmp_path)
    nginx = _secs(_read_timeouts(conf, "/agent/")[0])
    cap = _sibling_default("HWAXAgentServer", "deliberation.py", r'_env_(?:int|float)\("DELIB_TIMEOUT_MAX_S"\s*,\s*([0-9.]+)\)')
    assert 2 * cap + 8 < nginx, f"논리 호출 최악 {2 * cap + 8}초 · nginx {nginx}초"


def test_예시_파일이_두_손잡이를_기본값과_함께_선언한다():
    """이름이 예시 파일에 있어야 env-sync 가 기존 박스의 infra/.env 에 '이런 설정이 생겼다' 고 알린다. 주석 줄이어야 한다 —
    켜진 줄로 복사되면 코드 기본값을 나중에 올려도 그 박스만 옛 값에 묶인다."""
    example = (ROOT / "infra/.env.example").read_text(encoding="utf-8")
    for key, default in (("NGINX_AGENT_READ_TIMEOUT", "50400s"), ("NGINX_MCP_READ_TIMEOUT", "1h")):
        lines = [ln for ln in example.splitlines() if re.match(rf"^[ \t]*#?[ \t]*{key}=", ln)]
        assert lines == [f"# {key}={default}"], f"{key}: {lines}"
