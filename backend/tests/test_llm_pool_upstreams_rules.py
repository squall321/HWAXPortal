# LLM_UPSTREAMS 규칙 하나 — lib/llm-pool.sh hwax_llm_pool_upstreams(정본·오라클)와 라우터 config_from_text 를 같은 표로 대조한다(docs/llm-pool LP-D13)
"""왜 — 둘이 다르게 읽으면 update-all 1i 는 '아무것도 바꾸지 않았다(라우터·사본 그대로)' 고 하는데 떠 있는 라우터는 2초 안에 그 줄을 받는다
(검토 배선 L1 — /v1 없는 칸 · 대문자 스킴 · IPv6 · 포트 0), 또는 그 거꾸로 lib 는 받는데 라우터는 요청마다 예외를 낸다(검토 라우터 H1 — 옥텟 256).

일치 시험은 둘 다 틀리면 통과한다(감사 라운드 교훈) — 그래서 표의 줄마다 기대값을 적고, bash 와 라우터가 서로 같고 기대값과도 같은지 본다.
bash 는 로케일 둘(C.UTF-8 · C)에서 돌린다 — lib 는 글자 부류를 LC_ALL=C 로 고정했다(U+3000 이 UTF-8 로케일에서만 공백이면 라우터와 갈린다).
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
    (L("http://127.example:9130/v1"), ["http://127.example:9130/v1"]),      # 이름이다 — 루프백 IPv4 가 아니다
    (L("http://203.0.113.11/v1"), ["http://203.0.113.11/v1"]),
    (L("https://203.0.113.11:443/v1"), ["https://203.0.113.11:443/v1"]),
    (L("http://203.0.113.11:08000/v1"), ["http://203.0.113.11:08000/v1"]),  # 포트는 숫자 1~5자
    (L("http://h:1/v1,http://g:65535/v1"), ["http://h:1/v1", "http://g:65535/v1"]),
    (L("http://0.0.0.0:8000/v1"), ["http://0.0.0.0:8000/v1"]),              # 라우터 포트가 아니면 같은 박스의 서버다
    (L("http://127.0.0.1:8000/v1"), ["http://127.0.0.1:8000/v1"]),
    (L("http://localhost:8000/v1"), ["http://localhost:8000/v1"]),
    (L("http://127.0.0.1:9130/v1", "LLM_ROUTER_PORT=9555"), ["http://127.0.0.1:9130/v1"]),
    (L("http://127.0.0.1:9130/v1", "LLM_ROUTER_PORT=abc"), ["http://127.0.0.1:9130/v1"]),   # 포트를 모르면 고리 검사를 하지 않는다(lib 와 같다)
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
    (L("http://2130706433:9130/v1"), BAD), (L("http://127.1:9130/v1"), BAD), (L("http://1.2.3/v1"), BAD), (L("http://1.2.3.4.5/v1"), BAD),
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
    (L("http://127.0.0.1:9130/v1"), BAD), (L("http://127.255.0.1:9130/v1"), BAD), (L("http://0.0.0.0:9130/v1"), BAD),
    (L("http://LOCALHOST:9130/v1"), BAD), (L("http://localhost:09130/v1"), BAD), (L("https://127.0.0.1:9130/v1"), BAD),
    (L("http://localhost:9555/v1", "LLM_ROUTER_PORT=9555"), BAD), (L("http://127.0.0.1:9130/v1", "LLM_ROUTER_PORT=09130"), BAD),
    (L("http://localhost/v1", "LLM_ROUTER_PORT=80"), BAD), (L("https://localhost/v1", "LLM_ROUTER_PORT=443"), BAD),  # 적지 않은 포트는 스킴 기본
    # ── 같은 서버 두 번 ──
    (L("http://h.example:8000/v1,http://H.EXAMPLE:8000/v1"), BAD), (L("http://h.example/v1,http://h.example:80/v1"), BAD),
    (L("https://h.example/v1,https://h.example:443/v1"), BAD), (L("http://h.example:8000/v1,http://h.example:08000/v1"), BAD),
    (L(f"{S1},{S1}/"), BAD),
    (L(",,"), BAD), (L('" , "'), BAD),                                       # 주소가 하나도 없다
]


def _bash_batch(tmp_path: Path, texts: list[str], lang: str) -> list[tuple[int, list[str]]]:
    """표의 글마다 파일 하나 — bash 한 번에 전부 돌린다(줄마다 띄우면 수백 번이다)."""
    d = tmp_path / f"cases-{lang}"
    d.mkdir()
    for i, text in enumerate(texts):
        (d / f"{i}.env").write_bytes(text.encode("utf-8"))
    script = (f'. "{LIB}"\n'
              f'for i in $(seq 0 {len(texts) - 1}); do\n'
              f'  rc=0; out="$(hwax_llm_pool_upstreams "{d}/$i.env")" || rc=$?\n'
              '  if [ "$rc" = 0 ]; then printf \'%s\\t%s\\t%s\\n\' "$i" "$rc" "$(printf \'%s\' "$out" | tr \'\\n\' \' \')"\n'
              '  else printf \'%s\\t%s\\t\\n\' "$i" "$rc"; fi\n'
              'done\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, timeout=600,
                       env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "LANG": lang})
    assert r.returncode == 0 and not r.stderr, r.stderr.decode(errors="replace")
    rows = [ln.split("\t") for ln in r.stdout.decode("utf-8").splitlines()]
    assert [int(x[0]) for x in rows] == list(range(len(texts)))
    return [(int(rc), items.split()) for _, rc, items in rows]


def _router_view(text: str) -> tuple[int, list[str]]:
    cfg = R.config_from_text(text)
    if cfg.upstreams:
        return 0, list(cfg.upstreams)
    return (2, []) if cfg.upstreams_invalid else (1, [])


def _want(w) -> tuple[int, list[str]]:
    return (0, w) if isinstance(w, list) else (1, []) if w == OFF else (2, [])


@pytest.mark.parametrize("lang", ["C.UTF-8", "C"])
def test_정본과_라우터가_표의_모든_줄을_같게_읽고_기대값과도_같다(tmp_path, monkeypatch, lang):
    monkeypatch.delenv("LLM_ROUTER_PORT", raising=False)       # 라우터는 띄우는 스크립트가 넘긴 이 값을 파일보다 먼저 본다 — 표는 파일만
    sh = _bash_batch(tmp_path, [t for t, _ in CASES], lang)
    wrong = [(text, _want(w), sh[i], _router_view(text)) for i, (text, w) in enumerate(CASES)
             if not sh[i] == _router_view(text) == _want(w)]
    assert not wrong, "\n".join(f"{t!r}: 기대 {w} · lib {s} · 라우터 {p}" for t, w, s, p in wrong)


def _generated(n: int = 400) -> list[str]:
    """구석을 찌르는 칸 — 스킴·호스트(숫자·점·하이픈·밑줄·대문자·xn--)·포트·경로를 섞는다. 같은 씨앗이라 늘 같은 표다."""
    rnd = random.Random(1015)
    schemes = ["http"] * 4 + ["https"] * 3 + ["HTTP", "Https", "ftp", ""]
    ports = [""] * 4 + [":1", ":80", ":443", ":8000", ":08000", ":9130", ":65535", ":0", ":65536", ":99999", ":", ":1x"]
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
        out.append(L(item, *(["LLM_ROUTER_PORT=" + rnd.choice(["80", "443", "8000", "9130", "x"])] if rnd.random() < 0.3 else [])))
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
