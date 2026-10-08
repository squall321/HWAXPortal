# 다섯 리포에 흩어진 시간 한도의 기본값을 소스에서 읽어 '안쪽 < 바깥' 사슬이 성립하는지 묻는다 — 한 리포만 고치면 순서가 조용히 뒤집힌다
"""왜 — 긴 심의가 지나는 길(호출자 → nginx·게이트웨이 → 포털 → 엔진 → LLM · 엔진 → 게이트웨이 → 백엔드 · 리스크 앱 → 포털 → 엔진)의
시간 한도는 다섯 리포에 나뉘어 있다. 값 하나하나는 제 리포의 시험이 지키는데, 지키는 것이 없던 자리는 **사이**다. 안쪽 한도가
바깥보다 작아야 안쪽의 문구(걸린 값과 손잡이 이름)가 먼저 나간다 — 한 리포의 기본값만 올리면 바깥이 사유 없이 먼저 끊는다.
엔진 값만 아는 호출자가 포털의 좁은 상한에 422 로 걸려 패널 하나를 통째로 잃은 것이 그 모양이었다(2026-10-07).

읽는 것은 **소스에 적힌 기본값**이다. 그 박스의 환경값이 아니다 — 박스에서 한쪽만 덮으면 이 시험은 모른다(덮는 자리의 주석이
순서를 말한다). 형제 리포가 없는 박스에서는 그 리포가 드는 사슬만 건너뛴다. 리포는 있는데 값을 못 찾으면 **실패**다 — 이름이나
줄 모양이 바뀐 것이고, 건너뛰면 사슬이 조용히 풀린다(리스크 앱 읽기 한도 대조가 그렇게 늘 skip 이었다 — f174be9).

사슬(2026-10-08 시간 한도 결정표의 원칙 1). 감싸는 관계만 묻는다 — 나란히 놓인 값끼리의 크기는 묻지 않는다.
  LLM·누적 시간  연결 < 시도 1회 < 논리 호출(재시도 포함) < 의장 최악 < 리스크 패널 벽시계 < 포털 릴레이 침묵 < nginx 침묵 < 리스크 앱 침묵
  도구 호출      게이트웨이 재연결 < 호출 < 전송 read·단발 세션 바깥 기한 < 그것을 감싸는 셋(엔진 · 포털 절차 워밍업 · nginx /mcp-gw/)
  지식카드       AIDataHub 연결 < 풀 대기 · 풀 대기 + 검색 문장 < 엔진의 지식카드 한도
  자격           패널 벽시계 + 보고서 저장 < chat PAT 의 최소 잔여 · 패널 벽시계 < 리스크 자격 여유 < PAT 등록 하한
"""
import re
from pathlib import Path

import pytest

from app.config import Settings
from app.procedures.runner import EXPECT_TIMEOUT, WARMUP_TIMEOUT

ROOT = Path(__file__).resolve().parents[2]
ENGINE, GATEWAY, RISK, AIDH = "HWAXAgentServer", "HWAXMcpGateway", "HWAXRisk", "AIDataHub"
# openai SDK 가 재시도 사이에 쉬는 최대 시간(초, openai._constants.MAX_RETRY_DELAY) — 결정표 '2×1800+8' 의 8 이다.
SDK_BACKOFF_MAX_S = 8


def _src(repo: str, rel: str) -> str:
    base = ROOT if repo == "HWAXPortal" else ROOT.parent / repo
    if not base.is_dir():
        pytest.skip(f"형제 리포 없음: {base}")
    f = base / rel
    assert f.exists(), f"{repo} 에 {rel} 이 없다 — 파일이 옮겨졌으면 이 시험의 경로를 고쳐라(건너뛰면 사슬이 조용히 풀린다)"
    return f.read_text(encoding="utf-8")


def _val(repo: str, rel: str, pattern: str) -> float:
    m = re.search(pattern, _src(repo, rel), re.M)
    assert m, (f"{repo}/{rel} 에서 기본값을 못 읽었다(식 {pattern}) — 손잡이 이름이나 줄 모양이 바뀌었으면 이 식을 고쳐라. "
               "건너뛰지 않는다 — 건너뛰면 사슬이 조용히 풀린다")
    return float(m.group(1))


def _engine() -> dict[str, float]:
    def env(kind: str, name: str) -> str:   # `_env_float("이름", 기본값)` 의 기본값 — 이름 바로 뒤의 수만 읽는다
        return rf'_env_{kind}\("{name}",\s*([0-9.]+)\)'
    app, delib = "app.py", "deliberation.py"
    e = {"connect": _val(ENGINE, app, env("float", "LLM_CONNECT_TIMEOUT_S")),
         "attempt": _val(ENGINE, app, env("float", "DELIB_TIMEOUT_S")),
         "retries": _val(ENGINE, app, env("int", "DELIB_LLM_MAX_RETRIES")),
         "cap": _val(ENGINE, delib, env("float", "DELIB_TIMEOUT_MAX_S")),
         "chair_retries": _val(ENGINE, delib, env("int", "DELIB_CHAIR_RETRIES")),
         "heartbeat": _val(ENGINE, app, env("float", "DELIB_HEARTBEAT_S")),
         "mcp_call": _val(ENGINE, app, env("float", "MCP_CALL_TIMEOUT_S")),
         "knowledge": _val(ENGINE, delib, env("float", "KNOWLEDGE_TIMEOUT_S"))}
    # LLM 논리 호출 1회의 최악 — SDK 가 한도에 걸린 시도를 처음부터 다시 한다(기본 2×1800+8 = 3608). 바깥 한도 계산의 기준이다.
    e["logical"] = (1 + e["retries"]) * e["attempt"] + SDK_BACKOFF_MAX_S
    e["logical_at_cap"] = (1 + e["retries"]) * e["cap"] + SDK_BACKOFF_MAX_S   # 요청이 timeout_s 를 상한까지 청했을 때
    e["chair"] = (1 + e["chair_retries"]) * e["logical"]                       # 의장은 실패하면 한 번 더 부른다
    return e


def _gateway() -> dict[str, float]:
    g = "gateway.py"
    call = _val(GATEWAY, g, r'^CALL_TIMEOUT_S\s*=\s*int\(os\.environ\.get\("GATEWAY_CALL_TIMEOUT",\s*"(\d+)"\)\)')
    reconnect = _val(GATEWAY, g, r'^RECONNECT_TIMEOUT_S\s*=\s*float\(os\.environ\.get\("GATEWAY_RECONNECT_TIMEOUT",\s*"([0-9.]+)"\)\)')
    slack = _val(GATEWAY, g, r'^BACKEND_READ_TIMEOUT_S\s*=\s*float\(os\.environ\.get\("GATEWAY_BACKEND_READ_TIMEOUT"\)\s*or\s*CALL_TIMEOUT_S\s*\+\s*(\d+)\)')
    assert "move_on_after(RECONNECT_TIMEOUT_S + timeout_s + RECONNECT_TIMEOUT_S)" in _src(GATEWAY, g), (
        "게이트웨이 단발 세션 바깥 기한의 식이 바뀌었다 — 아래 outer 를 그 식대로 고쳐라(이 값을 감싸는 셋이 여기에 걸려 있다)")
    return {"reconnect": reconnect, "call": call, "read": call + slack, "outer": reconnect + call + reconnect}


def _aidh() -> dict[str, float]:
    def field(name: str) -> str:
        return rf"^\s*{name}:\s*float\s*=\s*([0-9.]+)"
    c = "api_server/src/api/config.py"
    return {"connect": _val(AIDH, c, field("aidh_db_connect_timeout_s")), "pool": _val(AIDH, c, field("db_pool_timeout")),
            "statement": _val(AIDH, c, field("aidh_search_statement_timeout_s"))}


def _risk() -> dict[str, float]:
    def const(name: str) -> str:
        return rf"^{name}\s*=\s*(\d+)"
    c = "backend/app/config.py"
    panel = _val(RISK, c, const("DEFAULT_PANEL_TIMEOUT_S"))
    # 429 몫은 러너가 실제로 기다리는 예산(HWAXRISK_ENGINE_BUSY_MAX_WAIT_S)이고, 그 손잡이의 기본값이 ENGINE_BUSY_ALLOWANCE_S 다
    # (리스크 앱 c4f0852 — 종전에는 식이 그 상수를 직접 더했다). 식과 기본값 자리를 둘 다 본다 — 아래 margin 은 기본값끼리의 셈이다.
    assert "(panel_timeout_s(cfg) or DEFAULT_PANEL_TIMEOUT_S) + engine_busy_max_wait_s(cfg) + CREDENTIAL_SLACK_S" in _src(RISK, c), (
        "리스크 앱의 자격 여유 식이 바뀌었다 — 아래 margin 을 그 식대로 고쳐라")
    assert 'env.get("HWAXRISK_ENGINE_BUSY_MAX_WAIT_S", str(ENGINE_BUSY_ALLOWANCE_S))' in _src(RISK, c), (
        "리스크 앱의 429 대기 예산 기본값이 ENGINE_BUSY_ALLOWANCE_S 가 아니게 됐다 — 아래 margin 이 읽는 상수를 고쳐라")
    return {"panel": panel, "read": _val(RISK, c, const("DEFAULT_ENGINE_READ_TIMEOUT_S")),
            "margin": panel + _val(RISK, c, const("ENGINE_BUSY_ALLOWANCE_S")) + _val(RISK, c, const("CREDENTIAL_SLACK_S")),
            "pat_floor": _val(RISK, "backend/app/routes.py", const("PAT_MIN_REMAINING_S"))}


def _nginx_default(knob: str) -> float:
    """생성기가 손잡이를 안 적은 박스에 넣는 값(초) — `_nginx_time <손잡이> <기본값>` 의 기본값."""
    m = re.search(rf"_nginx_time {knob} (\d+)([smhd]?)\)", _src("HWAXPortal", "infra/scripts/gen-nginx-conf.sh"))
    assert m, f"gen-nginx-conf.sh 에서 {knob} 의 기본값을 못 읽었다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def _portal() -> dict[str, float]:
    def default(name: str) -> float:
        return float(Settings.model_fields[name].default)
    # chat PAT 은 30분 창의 **시작**에서 수명을 센다(routes._chat_user_pat) — 창 끝에서 받으면 그만큼 덜 남는다.
    window = _val("HWAXPortal", "backend/app/agent/routes.py", r"int\(now\.timestamp\(\)\) // (\d+) \* \1\b")
    return {"relay": default("agent_stream_idle_timeout_s"), "unary": default("agent_unary_timeout_s"),
            "pat_left": default("chat_pat_ttl_s") - window, "nginx_agent": _nginx_default("NGINX_AGENT_READ_TIMEOUT"),
            "nginx_mcp": _nginx_default("NGINX_MCP_READ_TIMEOUT"), "warmup": float(WARMUP_TIMEOUT),
            "step": float(max(EXPECT_TIMEOUT.values()))}


def _ascending(chain: list[tuple[str, float]]) -> None:
    shown = " < ".join(f"{name} {v:g}" for name, v in chain)
    for (inner, a), (outer, b) in zip(chain, chain[1:], strict=False):
        assert a < b, (f"안쪽이 바깥보다 작지 않다 — {inner} {a:g}초 ≥ {outer} {b:g}초. 안쪽이 먼저 걸려야 걸린 값과 손잡이 이름이 든 "
                       f"문구가 나간다. 한쪽을 올렸으면 감싸는 쪽을 같은 폭으로 올린다.\n  {shown}")


def llm_chain() -> list[tuple[str, float]]:
    e, r, p = _engine(), _risk(), _portal()
    return [("LLM 연결(LLM_CONNECT_TIMEOUT_S)", e["connect"]), ("LLM 호출 시도 1회(DELIB_TIMEOUT_S)", e["attempt"]),
            ("LLM 논리 호출 1회((1+DELIB_LLM_MAX_RETRIES)×시도+8)", e["logical"]),
            ("의장 최악((1+DELIB_CHAIR_RETRIES)×논리 호출)", e["chair"]),
            ("리스크 패널 벽시계(HWAXRISK_PANEL_TIMEOUT_S)", r["panel"]),
            ("포털 릴레이 침묵(AGENT_STREAM_IDLE_TIMEOUT_S)", p["relay"]),
            ("nginx /agent/ 침묵(NGINX_AGENT_READ_TIMEOUT)", p["nginx_agent"]),
            ("리스크 앱 침묵(HWAXRISK_ENGINE_READ_TIMEOUT_S)", r["read"])]


def tool_chain() -> list[tuple[str, float]]:
    g = _gateway()
    return [("게이트웨이 재연결·핸드셰이크(GATEWAY_RECONNECT_TIMEOUT)", g["reconnect"]), ("게이트웨이 도구 호출 1건(GATEWAY_CALL_TIMEOUT)", g["call"]),
            ("게이트웨이 전송 read(GATEWAY_BACKEND_READ_TIMEOUT)·단발 세션 바깥 기한", min(g["read"], g["outer"]))]


def tool_wrappers() -> list[tuple[str, float]]:
    """게이트웨이의 호출 1건을 **감싸는** 셋 — 서로는 나란하다(엔진은 nginx 를 지나지 않고 게이트웨이를 직접 부른다)."""
    e, p = _engine(), _portal()
    return [("포털 절차 워밍업(WARMUP_TIMEOUT)", p["warmup"]), ("엔진 도구 호출(MCP_CALL_TIMEOUT_S)", e["mcp_call"]),
            ("nginx /mcp-gw/ 침묵(NGINX_MCP_READ_TIMEOUT)", p["nginx_mcp"])]


def test_LLM_호출에서_리스크_앱까지_안쪽이_바깥보다_작다():
    """**이 시험이 이 파일의 이유다.** 연결 10 < 시도 1800 < 논리 호출 3608 < 의장 7216 < 패널 벽시계 43200 < 포털 릴레이 46800
    < nginx 50400 < 리스크 앱 54000. 엔진·리스크 앱·포털 세 리포의 값이라 한쪽만 고치면 여기서 걸린다."""
    _ascending(llm_chain())


def test_요청_상한으로_청한_호출_한_번이_조용해도_침묵_한도에_안_걸린다():
    """heartbeat 가 없는 옛 엔진이 섞여 돌 수 있다(update-all 이 도는 심의 때문에 재기동을 건너뛴 박스). 그때 LLM 논리 호출 한 번은
    통째로 조용하다 — 요청이 timeout_s 를 상한까지 청했으면 2×14400+8 = 28808초다. 침묵 한도 셋 중 가장 안쪽(포털 릴레이)이 그보다
    커야 살아 있는 심의의 구독이 끊기지 않는다."""
    e, p = _engine(), _portal()
    _ascending([("요청 상한 호출의 논리 1회((1+재시도)×DELIB_TIMEOUT_MAX_S+8)", e["logical_at_cap"]),
                ("포털 릴레이 침묵(AGENT_STREAM_IDLE_TIMEOUT_S)", p["relay"])])


def test_게이트웨이_도구_호출_한_건을_바깥_셋이_모두_감싼다():
    """재연결 30 < 호출 600 < 전송 read·단발 세션 바깥 기한 660, 그리고 그 660 을 엔진(900)·절차 워밍업(690)·nginx /mcp-gw/(3600)가
    감싼다. 게이트웨이가 먼저 포기해야 '어느 백엔드의 어느 도구가 몇 초에 걸렸나' 가 나간다. GATEWAY_CALL_TIMEOUT 이나
    GATEWAY_RECONNECT_TIMEOUT 의 기본값을 올리면 바깥 기한(재연결 + 호출 + 재연결)이 같이 올라 이 셋을 넘는다 — 그때 여기서 걸린다
    (test_procedures_census 는 바깥 기한을 '호출 + 60' 으로만 안다)."""
    g = _gateway()
    _ascending(tool_chain())
    for name, v in tool_wrappers():
        _ascending([("게이트웨이 전송 read(GATEWAY_BACKEND_READ_TIMEOUT)", g["read"]), (name, v)])
        _ascending([("게이트웨이 단발 세션 바깥 기한(재연결 + 호출 + 재연결)", g["outer"]), (name, v)])
    _ascending([("포털 절차 단계 상한(EXPECT_TIMEOUT 의 최댓값)", _portal()["step"]), ("게이트웨이 도구 호출 1건(GATEWAY_CALL_TIMEOUT)", g["call"])])


def test_지식카드_조회는_AIDataHub_가_사유를_말한_뒤에_포기한다():
    """엔진이 지식카드 조회를 기다리는 180초가 AIDataHub 의 풀 대기 60 + 검색 문장 한도 90 보다 커야, AIDataHub 가 '풀이 찼다'·
    '검색을 취소했다' 를 손잡이 이름과 함께 답할 틈이 있다. 엔진이 먼저 포기하면 사유 없는 시간 초과만 남는다."""
    a, e = _aidh(), _engine()
    _ascending([("AIDataHub PG 연결(AIDH_DB_CONNECT_TIMEOUT_S)", a["connect"]), ("AIDataHub 풀 대기(DB_POOL_TIMEOUT)", a["pool"])])
    _ascending([("AIDataHub 풀 대기 + 검색 문장(DB_POOL_TIMEOUT + AIDH_SEARCH_STATEMENT_TIMEOUT_S)", a["pool"] + a["statement"]),
                ("엔진 지식카드 조회(KNOWLEDGE_TIMEOUT_S)", e["knowledge"])])


def test_자격이_가장_긴_실행보다_오래_산다():
    """자격은 누적 시간 한도라 가장 바깥이다. 포털이 찍는 chat PAT 은 창 끝에서 받아도 (수명 − 30분)이 남고, 그것이 가장 긴 실행
    (리스크 패널 벽시계 + 마지막 보고서 저장 = 게이트웨이 호출 한 건의 바깥 기한)보다 길어야 한다. 리스크 앱이 사용자 등록 PAT 에
    요구하는 여유(벽시계 + 429 대기 + 600)는 벽시계보다 크고 등록 하한보다 작아야 한다(작지 않으면 그 앱이 기동을 거부한다)."""
    r, p, g = _risk(), _portal(), _gateway()
    _ascending([("리스크 패널 벽시계 + 보고서 저장(게이트웨이 바깥 기한)", r["panel"] + g["outer"]),
                ("chat PAT 의 최소 잔여(CHAT_PAT_TTL_S − 30분 창)", p["pat_left"])])
    _ascending([("리스크 패널 벽시계(HWAXRISK_PANEL_TIMEOUT_S)", r["panel"]), ("리스크 자격 여유(벽시계 + 429 대기 + 600)", r["margin"]),
                ("리스크 PAT 등록 하한(PAT_MIN_REMAINING_S)", r["pat_floor"])])


def test_심의_전_도우미는_nginx_가_끊기_전에_기본값으로_넘어간다():
    """도우미 대기(600초)는 실패가 아니라 폴백으로 끝난다 — nginx /agent/ 의 침묵 한도가 그보다 짧으면 폴백 대신 절단이 화면에 간다."""
    p = _portal()
    _ascending([("포털 도우미 대기(AGENT_UNARY_TIMEOUT_S)", p["unary"]), ("nginx /agent/ 침묵(NGINX_AGENT_READ_TIMEOUT)", p["nginx_agent"])])


def test_nginx_생성기가_견주는_포털_기본값이_포털의_그_값이다():
    """gen-nginx-conf.sh 는 포털 값을 못 읽으면 기본값으로 순서를 견준다 — 그 수는 config.py 기본값의 bash 쪽 사본이다."""
    m = re.search(r'_idle="\$\{_idle:-(\d+)\}"', _src("HWAXPortal", "infra/scripts/gen-nginx-conf.sh"))
    assert m, "gen-nginx-conf.sh 의 포털 기본값 줄을 못 찾았다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    assert float(m.group(1)) == _portal()["relay"], "포털 릴레이 기본값을 바꿨으면 생성기의 그 수도 같이 바꾼다(순서 알림이 옛 값으로 견준다)"


# ── heartbeat — 침묵 한도 셋이 살아 있는 심의를 끊지 않는 것은 엔진의 ping 덕이다 ─────────────────────────────────
def _front(rel: str, pattern: str) -> str:
    m = re.search(pattern, _src("HWAXPortal", f"frontend/src/{rel}"), re.M)
    assert m, f"frontend/src/{rel} 에서 못 읽었다(식 {pattern}) — 이름이 바뀌었으면 이 식을 고쳐라"
    return m.group(1)


def test_화면의_신호_없음_판정이_엔진_heartbeat_세_번을_기다린다():
    """화면은 ping 이 45초 끊기면 '신호 없음' 이라고 말한다 — 엔진 기본 간격 15초의 세 번이다. 엔진 기본값만 올리면(예: 30초) 건강한
    심의가 ping 사이마다 '신호 없음' 으로 깜박인다. 끊지는 않지만(표시뿐이다) 사람이 그것을 보고 다시 시작한다."""
    silent_ms = float(_front("lib/streamLive.ts", r"^export const SILENT_AFTER_MS = ([0-9_]+);").replace("_", ""))
    beat = _engine()["heartbeat"]
    assert beat > 0, "엔진 heartbeat 기본값이 0(끔)이다 — 침묵 한도 셋이 LLM 호출 한 번의 침묵을 통째로 받는다"
    assert silent_ms >= 3 * beat * 1000, f"화면은 {silent_ms / 1000:g}초에 '신호 없음' 인데 엔진 ping 은 {beat:g}초마다다 — 세 번은 기다린다"


def test_heartbeat_이벤트_이름이_세_리포에서_같다():
    """엔진이 `event: ping` 을 내고, 화면은 그 이름으로 '진행' 과 '살아 있음' 을 가르고, 리스크 앱은 그 이름을 진행으로 세지 않는다.
    이름이 갈리면 화면은 ping 을 진행으로 읽어 멈춘 심의를 '방금 진행' 으로 보이고, 리스크 앱은 events[] 400칸을 ping 으로 채운다."""
    name = _front("lib/streamLive.ts", r"^export const HEARTBEAT_EVENT = '([a-z_]+)';")
    assert f'yield _sse("{name}", ' in _src(ENGINE, "app.py"), f"엔진이 heartbeat 를 '{name}' 이라는 이름으로 내지 않는다"
    assert f'if name != "{name}":' in _src(RISK, "backend/app/engine_client.py"), f"리스크 앱이 '{name}' 을 진행과 가르지 않는다"


# ── 이름으로 맞물린 자리 — 값이 아니라 글자가 같아야 한다 ───────────────────────────────────────────────────────
def test_포털_릴레이의_침묵_코드를_리스크_앱이_그_글자로_읽는다():
    """포털 릴레이가 침묵 한도에서 내는 error 코드를 리스크 앱이 **정확한 글자**로 알아보고 '엔진 침묵' 으로 닫는다(좌석에 재시도를
    매기지 않고 잡을 멈춘다). 글자가 갈리면 평범한 엔진 실패로 읽혀, 아직 도는 심의 옆에 같은 좌석이 다시 편성된다."""
    m = re.search(r'^PORTAL_STREAM_IDLE_CODE\s*=\s*"([a-z_]+)"', _src(RISK, "backend/app/engine_client.py"), re.M)
    assert m, "리스크 앱에서 PORTAL_STREAM_IDLE_CODE 를 못 읽었다 — 이름이 바뀌었으면 이 식을 고쳐라"
    assert f'"code": "{m.group(1)}"' in _src("HWAXPortal", "backend/app/agent/routes.py"), (
        f"포털 릴레이가 '{m.group(1)}' 코드를 내지 않는다 — 리스크 앱이 기다리는 글자다")


def test_재기동_보호가_읽는_health_필드를_엔진이_그_이름으로_낸다():
    """update-all 은 에이전트 서버 /health 의 두 수를 보고 재기동을 건너뛴다(infra/scripts/lib/delib-busy.sh). 엔진이 이름을 바꾸면
    포털은 '모름' 으로 읽고 **그대로 재기동한다** — 몇 시간 돈 패널이 배포 한 번에 사라지는데 시험은 지어낸 응답으로 초록이다."""
    # 그 핸들러 하나만 — def 줄과 그 아래 들여쓴 줄들(파일의 마지막 라우트라 '다음 라우트 앞까지' 로는 못 끊는다)
    m = re.search(r'@app\.get\("/health"\)\ndef [^\n]*\n(?:[ \t][^\n]*\n|\n)*', _src(ENGINE, "app.py"))
    assert m, "엔진 app.py 에서 /health 핸들러를 못 찾았다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    names = set(re.findall(r'^\s*"(delib_[a-z]+)":', m.group(0), re.M))
    assert names, "엔진 /health 에서 심의 수 필드를 못 찾았다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    busy = _src("HWAXPortal", "infra/scripts/lib/delib-busy.sh")
    assert names == set(re.findall(r'h\.get\("(delib_[a-z]+)"\)', busy)), "엔진이 내는 이름과 delib-busy.sh 가 읽는 이름이 다르다"


def test_엔진이_스스로_건너뛴_재기동의_종료코드를_update_forges_가_안다():
    """엔진 start.sh 는 도는 심의가 있으면 인스턴스를 둔 채 그 종료코드로 나간다. update-forges 가 그 수를 모르면 '○ 건너뜀' 바로
    아래에 '✗ 재기동 실패' 를 찍고 실행을 실패로 끝낸다(63c641b 가 고친 모양)."""
    m = re.search(r'echo "○ agent-server 재기동 건너뜀[^\n]*\n(?:[^\n]*\n){0,3}?\s*exit (\d+)\n', _src(ENGINE, "start.sh"))
    assert m, "엔진 start.sh 에서 '재기동 건너뜀' 의 종료코드를 못 읽었다 — 줄 모양이 바뀌었으면 이 식을 고쳐라"
    forges = _src("HWAXPortal", "infra/scripts/update-forges.sh")
    arm = re.search(r'\./start\.sh -d \) \|\| rc=\$\?\n\s*case "\$rc" in\n(?:[^\n]*\n)*?\s*esac', forges)
    assert arm and re.search(rf"^\s*{m.group(1)}\) echo \"○", arm.group(0), re.M), (
        f"update-forges.sh 가 엔진의 건너뜀 종료코드 {m.group(1)} 을 ○ 로 받지 않는다")
