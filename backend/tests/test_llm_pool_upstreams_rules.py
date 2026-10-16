# LLM_UPSTREAMS 규칙 하나 — lib/llm-pool.sh hwax_llm_pool_upstreams(정본·오라클)와 라우터 config_from_text 를 같은 표로 대조한다(docs/llm-pool LP-D13)
"""왜 — 둘이 다르게 읽으면 update-all 1i 는 '아무것도 바꾸지 않았다(라우터·사본 그대로)' 고 하는데 떠 있는 라우터는 2초 안에 그 줄을 받는다
(검토 배선 L1 — /v1 없는 칸 · 대문자 스킴 · IPv6 · 포트 0), 또는 그 거꾸로 lib 는 받는데 라우터는 요청마다 예외를 낸다(검토 라우터 H1 — 옥텟 256).

일치 시험은 둘 다 틀리면 통과한다(감사 라운드 교훈) — 그래서 표의 줄마다 기대값을 적고, bash 와 라우터가 서로 같고 기대값과도 같은지 본다.
bash 는 로케일 셋(C.UTF-8 · C · ko_KR.UTF-8 — 없으면 다른 UTF-8 로케일)에서 돌린다 — 독자는 첫 sed 부터 LC_ALL=C 다(UTF-8 로케일의
[[:space:]] 는 U+3000 · U+2003 · U+2028 도 먹어 `　LLM_UPSTREAMS=…` 가 bash 에만 활성 줄이 됐다 — 검토 2라운드 LOW 2). 로케일이 정말
걸렸는지는 고치지 않은 sed 로 먼저 본다(걸리지 않은 로케일에서 통과하면 아무것도 본 것이 아니다).
값 하나를 읽는 독자는 셋이 더 있다 — services.py `_infra_value`(if_env · health 주소의 포트) · update-all `_envfile_value` · llm-router.sh
`envv`. lib `hwax_llm_envv` 를 오라클로 그 셋과 라우터 env_values 를 표의 모든 글에서 글자 단위로 견준다.
생성한 칸 수백 개는 기대값 없이 둘의 일치만 본다(표가 정답을, 생성이 구석을 맡는다). 주소는 TEST-NET · 루프백 · 지어낸 이름만.
"""
import importlib.util
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "infra/scripts/lib/llm-pool.sh"
NUL_WARNING = "ignored null byte in input"     # bash 의 `$(…)` 는 NUL 을 지우며 이 경고를 낸다 — 독자들이 그 동작을 따른다


def _load_router():
    spec = importlib.util.spec_from_file_location("hwax_llm_router_rules", ROOT / "infra/llm-router/llm_router.py")
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


R = _load_router()
OFF, BAD = "OFF", "BAD"
S1, S2 = "http://203.0.113.11:10000/v1", "http://203.0.113.12:10000/v1"


def L(value: str, *extra: str) -> str:
    """LLM_UPSTREAMS 줄 하나(+ 다른 줄) — 파일 글 그대로."""
    return f"LLM_UPSTREAMS={value}\n" + "".join(x + "\n" for x in extra)


def _long_url(n: int) -> str:
    """정확히 n 자인 맞는 모양의 /v1 주소 — 라벨 50자를 점으로 잇고 마지막 라벨로 길이를 맞춘다."""
    head, tail = "http://", ":8000/v1"
    room = n - len(head) - len(tail)
    labels, left = [], room
    while left > 51:
        labels.append("a" * 50)
        left -= 51
    labels.append("b" * left)
    url = head + ".".join(labels) + tail
    assert len(url) == n
    return url


CASES: list[tuple[str, object]] = [
    # ── 맞는 줄 ──
    (L(f"{S1},{S2}"), [S1, S2]),
    (L(f"{S1}/,{S2}//"), [S1, S2]),                                         # 끝 / 는 뗀다
    (L(f'"{S1} {S2}"'), [S1, S2]),                                          # 공백은 따옴표 안에서만
    (L(f'"{S1}, {S2}"   # 두 서버'), [S1, S2]),
    (L(f"'{S1},{S2}'"), [S1, S2]),                                          # 작은따옴표 한 쌍
    (L(f'"{S1}\t{S2}"'), [S1, S2]),
    (L(f",{S1},,"), [S1]),                                                  # 빈 칸은 버린다
    (f"export LLM_UPSTREAMS={S1}\n", [S1]),
    (f"LLM_UPSTREAMS=x\nLLM_UPSTREAMS={S2}\n", [S2]),                       # 마지막 줄이 이긴다
    (f"LLM_UPSTREAMS={S1}\r\n", [S1]),                                      # CRLF
    (f"LLM_UPSTREAMS={S1} \r\n", [S1]),                                     # CRLF 앞 공백(sed 는 [[:space:]] 로 벗긴다)
    (L("https://llm-a.example/v1,http://llm-b.example:8000/v1"), ["https://llm-a.example/v1", "http://llm-b.example:8000/v1"]),
    (L("http://LLM-A.Example:8000/v1"), ["http://LLM-A.Example:8000/v1"]),  # 적힌 그대로 돌려준다
    (L("http://gpu-01.cluster.example:8000/v1"), ["http://gpu-01.cluster.example:8000/v1"]),
    (L("http://1a.example/v1"), ["http://1a.example/v1"]),
    (L("http://10-0-0-1:8000/v1"), ["http://10-0-0-1:8000/v1"]),            # 숫자·하이픈 이름은 이름이다
    (L("http://xn-abc.example/v1"), ["http://xn-abc.example/v1"]),          # 3·4번째가 -- 가 아니다
    (L("http://a--b.example/v1"), ["http://a--b.example/v1"]),
    (L("http://127.example:8730/v1"), ["http://127.example:8730/v1"]),      # 이름이다 — 루프백 IPv4 가 아니다
    (L("http://203.0.113.11/v1"), ["http://203.0.113.11/v1"]),
    (L("https://203.0.113.11:443/v1"), ["https://203.0.113.11:443/v1"]),
    (L("http://203.0.113.11:08000/v1"), ["http://203.0.113.11:08000/v1"]),  # 포트는 숫자 1~5자
    (L("http://h:1/v1,http://g:65535/v1"), ["http://h:1/v1", "http://g:65535/v1"]),
    (L("http://0.0.0.0:8000/v1"), ["http://0.0.0.0:8000/v1"]),              # 라우터 포트가 아니면 같은 박스의 서버다
    (L("http://127.0.0.1:8000/v1"), ["http://127.0.0.1:8000/v1"]),
    (L("http://localhost:8000/v1"), ["http://localhost:8000/v1"]),
    (L("http://127.0.0.1:8730/v1", "LLM_ROUTER_PORT=9555"), ["http://127.0.0.1:8730/v1"]),
    (L("http://127.0.0.1:8730/v1", "LLM_ROUTER_PORT=abc"), ["http://127.0.0.1:8730/v1"]),   # 포트를 모르면 고리 검사를 하지 않는다(lib 와 같다)
    (L("http://localhost/v1", "LLM_ROUTER_PORT=443"), ["http://localhost/v1"]),
    (L("http://h.example:8000/v1,https://h.example:8000/v1"), ["http://h.example:8000/v1", "https://h.example:8000/v1"]),
    # ── 꺼짐 ──
    ("", OFF), (L(""), OFF), (L("   # 나중에 적는다"), OFF), (L('""'), OFF), (L("''"), OFF), ("OTHER=1\n", OFF),
    (f"# LLM_UPSTREAMS={S1}\n", OFF), (f"LLM_UPSTREAMS={S1}\nLLM_UPSTREAMS=\n", OFF),
    # ── 모양이 틀렸다 — 포털 start.sh 가 infra/.env 를 bash 로 소싱하다 죽는 줄(검토 배선 M1) ──
    (L(f"{S1}, {S2}"), BAD), (L(f"{S1} {S2}"), BAD),
    (L(f'"{S1}", "{S2}"'), BAD), (L(f'"{S1}" {S2}'), BAD), (L(f"'{S1}' '{S2}'"), BAD),
    (L(f'"{S1},{S2}'), BAD), (L(f'{S1},{S2}"'), BAD), (L("'"), BAD), (L('"\'"'), BAD), (L(f'"{S1}\''), BAD),
    (L(f"{S1}\x0b,{S2}"), BAD),                                             # 수직탭도 공백이다
    (L(f'"{S1} # 주석"'), BAD),                                              # 공백 뒤 # 은 주석 — 짝 없는 따옴표가 남는다
    (L("http://<서버1 주소>:<포트>/v1,http://<서버2 주소>:<포트>/v1"), BAD),    # .env.example 의 예시를 그대로 풀었다
    # ── 칸이 틀렸다 ──
    (L("HTTP://a.example/v1"), BAD), (L("ftp://a.example/v1"), BAD), (L("a.example:8000/v1"), BAD),
    (L("http://a.example:8000"), BAD), (L("http://a.example:8000/"), BAD), (L("http://a.example:8000/v1/chat"), BAD),
    (L("http://a.example:8000/openai/v1"), BAD), (L("http://a.example:8000//v1"), BAD), (L("http://a.example:8000/V1"), BAD),
    (L("http://u:p@a.example:8000/v1"), BAD), (L("http://a.example:8000/v1?x=1"), BAD), (L("http://a.example:8000/v1#f"), BAD),
    (L("http://[::1]:8000/v1"), BAD), (L("http://[fd00::1]:8000/v1"), BAD),
    (L("http://203.0.113.256:8000/v1"), BAD), (L("http://203.0.113.1377:8000/v1"), BAD), (L("http://198.51.100.300:8000/v1"), BAD),
    (L("http://203.0.113.011:8000/v1"), BAD), (L("http://0203.0.113.11:8000/v1"), BAD),     # 앞 0 — inet_aton 은 8진수로 읽는다
    (L("http://2130706433:8730/v1"), BAD), (L("http://127.1:8730/v1"), BAD), (L("http://1.2.3/v1"), BAD), (L("http://1.2.3.4.5/v1"), BAD),
    (L("http://-bad.example/v1"), BAD), (L("http://bad-.example/v1"), BAD), (L("http://a..example/v1"), BAD),
    (L("http://a_b.example/v1"), BAD), (L("http://a.example.:8000/v1"), BAD),
    (L("http://xn--abc.example/v1"), BAD),                                  # httpx 가 idna 로 풀다 ValueError 를 낸다
    (L("http://ab--cd.example/v1"), BAD), (L("http://llm.xn--bcher-kva.example/v1"), BAD),
    (L("http://h:0/v1"), BAD), (L("http://h:65536/v1"), BAD), (L("http://h:123456/v1"), BAD), (L("http://h:/v1"), BAD),
    (L("http://h:8x/v1"), BAD),
    (L("http://a.example:8000/v1\u3000http://b.example:8000/v1"), BAD),       # U+3000 은 공백이 아니다(칸의 일부 → 틀린 호스트)
    (L(f'"{S1}\u00a0{S2}"'), BAD),                                           # NBSP 도 공백이 아니다
    (L("http://é.example/v1"), BAD), (L("/"), BAD), (L("sk-live-SECRET"), BAD),
    (L(f"{S1},http://203.0.113.256:10000/v1"), BAD),                        # 하나라도 틀리면 줄 전체
    # ── 라우터 자신(고리) ──
    (L("http://127.0.0.1:8730/v1"), BAD), (L("http://127.255.0.1:8730/v1"), BAD), (L("http://0.0.0.0:8730/v1"), BAD),
    (L("http://LOCALHOST:8730/v1"), BAD), (L("http://localhost:08730/v1"), BAD), (L("https://127.0.0.1:8730/v1"), BAD),
    (L("http://localhost:9555/v1", "LLM_ROUTER_PORT=9555"), BAD), (L("http://127.0.0.1:8730/v1", "LLM_ROUTER_PORT=08730"), BAD),
    (L("http://localhost/v1", "LLM_ROUTER_PORT=80"), BAD), (L("https://localhost/v1", "LLM_ROUTER_PORT=443"), BAD),  # 적지 않은 포트는 스킴 기본
    # ── 같은 서버 두 번 ──
    (L("http://h.example:8000/v1,http://H.EXAMPLE:8000/v1"), BAD), (L("http://h.example/v1,http://h.example:80/v1"), BAD),
    (L("https://h.example/v1,https://h.example:443/v1"), BAD), (L("http://h.example:8000/v1,http://h.example:08000/v1"), BAD),
    (L(f"{S1},{S1}/"), BAD),
    (L(",,"), BAD), (L('" , "'), BAD),                                       # 주소가 하나도 없다
    # ── 줄 고르기 — 공백은 ASCII 여섯뿐이고 줄은 \n 으로만 나눈다(검토 2라운드 LOW 2) ──
    (f"\u3000LLM_UPSTREAMS={S1}\n", OFF), (f"export\u3000LLM_UPSTREAMS={S1}\n", OFF),          # U+3000 으로 시작하는 줄은 활성 줄이 아니다
    (f"LLM_UPSTREAMS={S1}\n\u3000LLM_UPSTREAMS={S2}\n", [S1]), (f"LLM_UPSTREAMS={S1}\n\u2003LLM_UPSTREAMS={S2}\n", [S1]),
    (f"LLM_UPSTREAMS={S1}\n\u2028LLM_UPSTREAMS={S2}\n", [S1]),                                  # splitlines 는 U+2028 에서 끊는다
    (f"LLM_UPSTREAMS={S1}\n\x85LLM_UPSTREAMS={S2}\n", [S1]), (f"\u2003LLM_UPSTREAMS={S1}\n", OFF),
    ("\u3000LLM_ROUTER_PORT=9555\nLLM_UPSTREAMS=http://127.0.0.1:9555/v1\n", ["http://127.0.0.1:9555/v1"]),   # 포트 줄이 활성이 아니면 8730
    (f"LLM_UPSTREAMS={S1}\rLLM_UPSTREAMS={S2}\n", BAD),                                         # 홀로 선 \r 은 줄바꿈이 아니다 — 한 줄이다
    (f"OTHER=1\rLLM_UPSTREAMS={S1}\n", OFF), (f"\rLLM_UPSTREAMS={S1}\n", [S1]), (f"LLM_UPSTREAMS={S1}\r#x\n", [S1]),
    ("LLM_UPSTREAMS=http://127.0.0.1:9555/v1\nOTHER=1\rLLM_ROUTER_PORT=9555\n", ["http://127.0.0.1:9555/v1"]),
    # ── NUL — bash 의 `$(…)` 는 지운다(경고 한 줄) · 라우터·services.py 도 마지막에 지운다 ──
    ("LLM_UPSTREAMS=http://203.0.113.1\x001:10000/v1\n", [S1]), (f"LLM_UPSTREAMS={S1}\x00\n", [S1]),
    (f"LLM_UPSTREAMS={S1}\n\x00LLM_UPSTREAMS={S2}\n", [S1]), (f'LLM_UPSTREAMS="{S1}\x00 {S2}"\n', [S1, S2]),
    # ── 칸 하나의 글자 상한 2,048 — httpx 는 64KiB 넘는 주소를 못 만든다(검토 2라운드 대조기의 마지막 갈림) ──
    (L(_long_url(2048)), [_long_url(2048)]), (L(_long_url(2049)), BAD), (L(f"{S1},{_long_url(70000)}"), BAD),
]


def _utf8_locale() -> str:
    """세 번째 로케일 — 운영 박스의 한국어 로케일(ko_KR.UTF-8)이 있으면 그것, 없으면 en_US.UTF-8(걸렸는지는 _run_bash 가 본다)."""
    try:
        have = {x.lower().replace("-", "") for x in subprocess.run(["locale", "-a"], capture_output=True, text=True, timeout=30).stdout.split()}
    except (OSError, subprocess.SubprocessError):
        have = set()
    return "ko_KR.UTF-8" if "ko_kr.utf8" in have else "en_US.UTF-8"


LANGS = ["C.UTF-8", "C", _utf8_locale()]


def _write_cases(d: Path, texts: list) -> None:
    d.mkdir()
    for i, text in enumerate(texts):
        (d / f"{i}.env").write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))


def _run_bash(tmp_path: Path, lang: str, body: str) -> bytes:
    """body 를 그 로케일의 bash 로 돌린다. 먼저 로케일이 정말 걸렸는지 본다 — 고치지 않은 sed(첫 sed 가 LC_ALL=C 가 아니던 독자)는 UTF-8
    로케일에서 U+3000 을 공백으로 먹는다. 걸리지 않으면(이 박스에 그 로케일이 없다) 그 로케일은 건너뛴다 — 통과로 치지 않는다."""
    canary = "printf '%s\\n' \"$(printf '\\343\\200\\200x' | sed -E 's/^[[:space:]]+//')\"\n"
    r = subprocess.run(["bash", "-c", canary + body], capture_output=True, timeout=600,       # 경고 글만 영어로(글자 부류는 LANG 그대로)
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": lang, "LC_MESSAGES": "C"})
    stray = [ln for ln in r.stderr.decode("utf-8", "replace").splitlines() if NUL_WARNING not in ln]
    assert r.returncode == 0 and not stray, "\n".join(stray)
    head, _, out = r.stdout.partition(b"\n")
    if lang != "C" and head != b"x":
        pytest.skip(f"로케일 {lang} 이 이 박스에서 걸리지 않는다(U+3000 을 공백으로 보지 않는다) — 이 로케일의 대조는 아무것도 보지 못한다")
    assert lang != "C" or head == "\u3000x".encode(), head
    return out


def _bash_batch(tmp_path: Path, texts: list, lang: str) -> list[tuple[int, list[str]]]:
    """표의 글마다 파일 하나 — bash 한 번에 전부 돌린다(줄마다 띄우면 수백 번이다)."""
    d = tmp_path / f"cases-{lang}"
    _write_cases(d, texts)
    script = (f'. "{LIB}"\n'
              f'for i in $(seq 0 {len(texts) - 1}); do\n'
              f'  rc=0; out="$(hwax_llm_pool_upstreams "{d}/$i.env")" || rc=$?\n'
              '  if [ "$rc" = 0 ]; then printf \'%s\\t%s\\t%s\\n\' "$i" "$rc" "$(printf \'%s\' "$out" | tr \'\\n\' \' \')"\n'
              '  else printf \'%s\\t%s\\t\\n\' "$i" "$rc"; fi\n'
              'done\n')
    rows = [ln.split("\t") for ln in _run_bash(tmp_path, lang, script).decode("utf-8").splitlines()]
    assert [int(x[0]) for x in rows] == list(range(len(texts)))
    return [(int(rc), items.split()) for _, rc, items in rows]


def _router_view(text: str) -> tuple[int, list[str]]:
    cfg = R.config_from_text(text)
    if cfg.upstreams:
        return 0, list(cfg.upstreams)
    return (2, []) if cfg.upstreams_invalid else (1, [])


def _want(w) -> tuple[int, list[str]]:
    return (0, w) if isinstance(w, list) else (1, []) if w == OFF else (2, [])


@pytest.mark.parametrize("lang", LANGS)
def test_정본과_라우터가_표의_모든_줄을_같게_읽고_기대값과도_같다(tmp_path, monkeypatch, lang):
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)       # 라우터는 띄우는 스크립트가 넘긴 이 값을 파일보다 먼저 본다 — 표는 파일만
    sh = _bash_batch(tmp_path, [t for t, _ in CASES], lang)
    wrong = [(text, _want(w), sh[i], _router_view(text)) for i, (text, w) in enumerate(CASES)
             if not sh[i] == _router_view(text) == _want(w)]
    assert not wrong, "\n".join(f"{t!r}: 기대 {w} · lib {s} · 라우터 {p}" for t, w, s, p in wrong)


# ── 값 하나를 읽는 독자 다섯 — lib hwax_llm_envv(오라클) · update-all _envfile_value · llm-router.sh envv · 라우터 env_values · services.py
#    _infra_value(if_env · health 주소의 포트). 표의 글에 이 구석을 더해 키 둘(LLM_UPSTREAMS · LLM_ROUTER_PORT)을 글자 단위로 견준다.
#    줄마다 LLM_ROUTER_PORT 의 기대값을 적는다 — 오라클도 틀릴 수 있다(None 은 기대값 없이 일치만) ──
READER_ROWS: list[tuple[str | bytes, str | None]] = [
    ("X=1\rLLM_ROUTER_PORT=9555\n", ""),             # services.py 의 splitlines() 는 뒤를 활성 줄로 읽었다(health 주소가 :9555 — 검토 LOW 2)
    ("LLM_ROUTER_PORT=8730\n\u2028LLM_ROUTER_PORT=9555\n", "8730"), ("LLM_ROUTER_PORT=8730\n\x85LLM_ROUTER_PORT=9555\n", "8730"),
    ("LLM_ROUTER_PORT=8730\n\u3000LLM_ROUTER_PORT=9555\n", "8730"), ("LLM_ROUTER_PORT=8730\n\u2003LLM_ROUTER_PORT=9555\n", "8730"),
    ("LLM_ROUTER_PORT=8730\n\x0cLLM_ROUTER_PORT=9555\n", "9555"),      # 폼피드는 ASCII 공백이다
    ("\x0bexport\x0bLLM_ROUTER_PORT=9555\n", "9555"), ("LLM_ROUTER_PORT=\x0b9555\n", "9555"), ("LLM_ROUTER_PORT=9555\x0b# 주석\n", "9555"),
    ("LLM_ROUTER_PORT=\x0c9555\r\n", "9555"), ("LLM_ROUTER_PORT=9555\u3000\n", "9555\u3000"), ("LLM_ROUTER_PORT=\u00a09555\n", "\u00a09555"),
    ("LLM_ROUTER_PORT=95\x0055\n", "9555"), ("LLM_ROUTER_PORT=9555 \x00\n", "9555 "), ("LLM_ROUTER_PORT=\x00 # c\n", ""),
    ("LLM_UPSTREAMS='a\x00b' # c\n", None),
    (b"LLM_ROUTER_PORT=9\xff5\n", "9\ufffd5"), (b"\xffLLM_ROUTER_PORT=9555\n", ""), (b'LLM_UPSTREAMS="http://a\xe3\x80/v1"\n', None),
]
READER_KEYS = ("LLM_UPSTREAMS", "LLM_ROUTER_PORT")


def _services_mod():
    spec = importlib.util.spec_from_file_location("hwax_services_rules", ROOT / "infra/scripts/services.py")
    m = importlib.util.module_from_spec(spec)
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(m)
    finally:
        sys.dont_write_bytecode = keep
    return m


def _bash_readers(tmp_path: Path, texts: list, lang: str) -> dict[tuple[int, str, str], bytes]:
    """bash 독자 넷이 읽은 값 — {(글 번호, 키, 독자): 바이트}. 값은 독자를 부르는 쪽과 같게 `$(…)` 로 받아(끝 개행 · NUL 이 빠진다) 파일에 쓴다."""
    ua = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
    i = ua.index("_envfile_value() {")
    launcher = (ROOT / "infra/scripts/llm-router.sh").read_text(encoding="utf-8")
    j = launcher.index("envv() {")
    d, o = tmp_path / f"readers-{lang}", tmp_path / f"values-{lang}"
    _write_cases(d, texts)
    o.mkdir()
    readers = {"lib": 'hwax_llm_envv "$f" "$k"', "raw": '_hwax_llm_raw "$f" "$k"', "update-all": '_envfile_value "$f" "$k"',
               "llm-router.sh": 'envv "$k" "$f"'}
    script = (f'. "{LIB}"\n{ua[i:ua.index(chr(10) + "}" + chr(10), i) + 3]}{launcher[j:launcher.index(chr(10), j) + 1]}'
              f'for i in $(seq 0 {len(texts) - 1}); do f="{d}/$i.env"; for k in {" ".join(READER_KEYS)}; do\n'
              + "".join(f'  v="$({call})"; printf \'%s\' "$v" > "{o}/$i.$k.{name}"\n' for name, call in readers.items())
              + "done; done\n")
    _run_bash(tmp_path, lang, script)
    return {(n, k, name): (o / f"{n}.{k}.{name}").read_bytes() for n in range(len(texts)) for k in READER_KEYS for name in readers}


@pytest.mark.parametrize("lang", LANGS)
def test_값을_읽는_독자_다섯이_표의_모든_글을_글자_단위로_같게_읽는다(tmp_path, monkeypatch, lang):
    """독자가 갈리면 같은 infra/.env 를 두고 lib 는 '풀 켜짐', 라우터는 다른 목록, services.py 는 다른 포트의 health 를 두드린다(검토 2라운드
    LOW 2 — UTF-8 로케일에서 U+3000 으로 시작하는 줄이 bash 에만 활성 · `X=1\\rLLM_ROUTER_PORT=9555` 가 services.py 에만 활성).
    오라클은 lib hwax_llm_envv 다 — bash 셋은 그와 바이트로, 라우터·services.py 는 UTF-8(깨진 바이트는 U+FFFD)로 같아야 한다."""
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)
    texts = [t for t, _ in CASES] + [t for t, _ in READER_ROWS]
    sh = _bash_readers(tmp_path, texts, lang)
    svc = _services_mod()
    portal = tmp_path / "portal"
    (portal / "infra").mkdir(parents=True)
    monkeypatch.setattr(svc, "PORTAL_ROOT", portal)
    wrong = []
    for n, text in enumerate(texts):
        raw = text if isinstance(text, bytes) else text.encode("utf-8")
        (portal / "infra/.env").write_bytes(raw)
        decoded = raw.decode("utf-8", errors="replace")          # 라우터 _reload 가 읽는 그대로
        plain, quoted = R.env_values(decoded), R.env_values(decoded, quotes=True)
        for k in READER_KEYS:
            oracle = sh[(n, k, "lib")]
            wrong += [(text, k, who, oracle, sh[(n, k, who)]) for who in ("update-all", "llm-router.sh") if sh[(n, k, who)] != oracle]
            got = {"라우터": plain.get(k, ""), "services.py": svc._infra_value(k) or ""}
            wrong += [(text, k, who, oracle, v) for who, v in got.items() if v != oracle.decode("utf-8", "replace")]
            if quoted.get(k, "") != sh[(n, k, "raw")].decode("utf-8", "replace"):
                wrong.append((text, k, "라우터(따옴표 남김) ↔ _hwax_llm_raw", sh[(n, k, "raw")], quoted.get(k, "")))
    assert not wrong, "\n".join(f"{t!r} [{k}] {who}: 오라클 {o!r} · 읽은 값 {v!r}" for t, k, who, o, v in wrong[:30])
    off = len(CASES)
    bad = [(t, w, sh[(off + n, "LLM_ROUTER_PORT", "lib")]) for n, (t, w) in enumerate(READER_ROWS)
           if w is not None and sh[(off + n, "LLM_ROUTER_PORT", "lib")].decode("utf-8", "replace") != w]
    assert not bad, "오라클이 기대값과 다르다 — " + "; ".join(f"{t!r}: 기대 {w!r} · lib {g!r}" for t, w, g in bad)


def _generated(n: int = 400) -> list[str]:
    """구석을 찌르는 칸 — 스킴·호스트(숫자·점·하이픈·밑줄·대문자·xn--)·포트·경로를 섞는다. 같은 씨앗이라 늘 같은 표다."""
    rnd = random.Random(1015)
    schemes = ["http"] * 4 + ["https"] * 3 + ["HTTP", "Https", "ftp", ""]
    ports = [""] * 4 + [":1", ":80", ":443", ":8000", ":08000", ":8730", ":65535", ":0", ":65536", ":99999", ":", ":1x"]
    paths = ["/v1"] * 6 + ["/v1/", "/v1//", "", "/", "/v2", "/v1/x", "//v1", "/openai/v1"]

    def label() -> str:
        n = rnd.randint(1, 6)
        s = rnd.choice("abz09") + "".join(rnd.choice("abz09-") for _ in range(n - 1))
        s = s[:-1] + rnd.choice("abz09") if n > 1 else s
        return s if rnd.random() < 0.85 else rnd.choice([s + "_", s.upper(), "-" + s, s + "-", s[:2] + "--" + s, s + "é"])
    out = []
    for _ in range(n):
        k = rnd.random()
        if k < 0.35:
            octs = [str(rnd.choice([0, 1, 9, 10, 99, 127, 200, 255, 255, 256, 300, "01", "007", 1000])) for _ in range(rnd.choice([2, 3, 4, 4, 4, 4, 5]))]
            host = ".".join(octs)
        elif k < 0.45:
            host = rnd.choice(["localhost", "LocalHost", "xn--abc", "ab--cd", "a-b", "-a", "a-", "127", "0x7f", "a" * 64, "0.0.0.0"])
        else:
            host = ".".join(label() for _ in range(rnd.randint(1, 3)))
        scheme = rnd.choice(schemes)
        item = (f"{scheme}://" if scheme else "") + host + rnd.choice(ports) + rnd.choice(paths)
        if rnd.random() < 0.2:                                        # 두 칸 — 겹침 · 하나만 틀림
            item = f"{item},{rnd.choice([S1, item, item.upper()])}"
        if rnd.random() < 0.1:
            item = f'"{item}"'
        out.append(L(item, *(["LLM_ROUTER_PORT=" + rnd.choice(["80", "443", "8000", "8730", "x"])] if rnd.random() < 0.3 else [])))
    return out


def test_정본과_라우터가_생성한_칸_수백_개도_같게_읽는다(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)
    texts = _generated()
    sh = _bash_batch(tmp_path, texts, "C.UTF-8")
    py = [_router_view(t) for t in texts]
    wrong = [(t, s, p) for t, s, p in zip(texts, sh, py, strict=True) if s != p]
    assert not wrong, "\n".join(f"{t!r}: lib {s} · 라우터 {p}" for t, s, p in wrong[:20])
    rcs = [s[0] for s in sh]
    assert rcs.count(0) >= 30 and rcs.count(2) >= 100, f"생성이 한쪽으로 쏠렸다 — 맞음 {rcs.count(0)} · 틀림 {rcs.count(2)}"
    for rc, urls in sh:                                               # 받은 칸은 httpx 로 요청까지 만들 수 있다(요청마다 터지지 않는다)
        for u in urls:
            up = R.Upstream(u)
            assert str(up.metrics_url).endswith("/metrics") and up.base.copy_with(raw_path=b"/v1/chat/completions")
