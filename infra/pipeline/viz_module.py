# 심의 파이프라인 시각화·분석 모듈 — 구조화 데이터 → 4종 그래프(SVG)+분석 HTML
# 재사용: build_viz(doe_rows, factors, response_keys, matrix, convergence) 로 어떤 DOE/비교 심의에도 적용
import html, json

def esc(s): return html.escape(str(s))

# ── 팔레트(테마 토큰 참조; SVG는 currentColor/var 사용) ──
CU, TE, MU = "var(--copper)", "var(--teal)", "var(--muted)"

def _svg(w, h, body, cls=""):
    return f'<svg viewBox="0 0 {w} {h}" class="chart {cls}" role="img" preserveAspectRatio="xMidYMid meet">{body}</svg>'

# 1) 민감도(main-effect) 바 — 각 요인이 응답을 얼마나 움직이나
def main_effects(rows, factors, resp):
    """factors: {name:(lo,hi)} 요인별 저/고 수준. resp: 응답 키. → 요인별 효과(hi평균-lo평균).

    ⚠ 수준에 매칭되는 행이 0개면 그 요인을 **제외**한다(감사 1-F 치명) — 종전 max(1,count)
    가드는 분모만 살리고 분자 0 을 그대로 나눠 '평균 0.0' 을 날조했다. LLM 산출 JSON 에서
    수준이 "10"(문자) vs 10(숫자)으로 어긋나기만 해도 민감도 차트가 조작된 수치로 결정문에
    실렸다. 날조 대신 제외 + 사유를 반환해 호출자가 캡션에 밝히게 한다.
    """
    eff, skipped = {}, []
    for fn, (lo, hi) in factors.items():
        los = [r[resp] for r in rows if r.get(fn) == lo]
        his = [r[resp] for r in rows if r.get(fn) == hi]
        if not los or not his:
            skipped.append(f"{fn}(수준 매칭 {len(los)}/{len(his)}행 — 타입·표기 불일치 의심)")
            continue
        eff[fn] = sum(his) / len(his) - sum(los) / len(los)
    return eff, skipped

def effects_svg(eff, title, unit, skipped=None):
    # 빈 eff — 전 요인 매칭 실패·상류 절단. 크래시(max 빈 시퀀스) 대신 자리표시자(감사 1-F).
    if not eff:
        note = f" 제외: {', '.join(skipped)}" if skipped else ""
        return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>'
                f'<div class="fig-c">데이터 부족 — 효과를 계산할 수 있는 요인이 없다.{esc(note)}</div></div>')
    W, H, pad = 460, 40 + 46 * len(eff), 120
    mx = max(abs(v) for v in eff.values()) or 1
    bars = ""
    y = 34
    for fn, v in sorted(eff.items(), key=lambda x: -abs(x[1])):
        bw = abs(v) / mx * (W - pad - 60)
        color = CU if v >= 0 else TE
        bars += (f'<text x="{pad-10}" y="{y+14}" class="ax" text-anchor="end">{esc(fn)}</text>'
                 f'<rect x="{pad}" y="{y}" width="{bw:.1f}" height="22" rx="3" fill="{color}" opacity="0.85"/>'
                 f'<text x="{pad+bw+7}" y="{y+16}" class="val">{v:+.1f}</text>')
        y += 46
    skip_note = (" · 제외 요인: " + esc(", ".join(skipped))) if skipped else ""
    return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>{_svg(W,H,bars)}'
            f'<div class="fig-c">막대 = 요인 저→고 수준 변화 시 {esc(unit)} 변화량. 길수록 지배 인자.{skip_note}</div></div>')

# 2) 파레토 스캐터 — 두 응답의 트레이드오프, 점 색=범주
def scatter_svg(rows, xk, yk, ck, cvals, title, xl, yl, labelk=None):
    W, H, m = 460, 320, 44
    # 숫자 강제 변환(감사 1-F) — LLM 산출 JSON 은 "12.5"(문자)를 곧잘 섞는다. 문자는 min/max 를
    # 사전순으로 통과한 뒤 뺄셈에서 TypeError 로 죽었다. 변환 불가 행은 표식과 함께 떨군다.
    def _f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    clean = [r for r in rows if _f(r.get(xk)) is not None and _f(r.get(yk)) is not None]
    dropped = len(rows) - len(clean)
    if not clean:
        return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>'
                f'<div class="fig-c">데이터 부족 — 수치 변환 가능한 행이 없다(입력 {len(rows)}행).</div></div>')
    rows = [{**r, xk: _f(r.get(xk)), yk: _f(r.get(yk))} for r in clean]
    xs = [r[xk] for r in rows]; ys = [r[yk] for r in rows]
    xmn, xmx = min(xs), max(xs); ymn, ymx = min(ys), max(ys)
    def X(v): return m + (v - xmn) / (xmx - xmn or 1) * (W - m - 20)
    def Y(v): return H - m - (v - ymn) / (ymx - ymn or 1) * (H - m - 24)
    grid = "".join(f'<line x1="{m}" y1="{Y(ymn+(ymx-ymn)*i/4):.1f}" x2="{W-20}" y2="{Y(ymn+(ymx-ymn)*i/4):.1f}" class="grid"/>' for i in range(5))
    pts = ""
    # 범주 팔레트 순환(감사 1-F) — 종전 cvals[0]/[1] 하드코딩은 1개면 IndexError, 3개 이상이면
    # 3번째부터 무채색으로 뭉갰다.
    _pal = [TE, CU, "var(--ink-soft)", "var(--line)"]
    cmap = {c: _pal[i % len(_pal)] for i, c in enumerate(cvals)}
    for r in rows:
        cx, cy = X(r[xk]), Y(r[yk])
        col = cmap.get(r[ck], MU)
        lab = f'<text x="{cx+9:.1f}" y="{cy+4:.1f}" class="pt-l">{esc(r[labelk])}</text>' if labelk else ""
        pts += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{col}" opacity="0.9"/>{lab}'
    ax = (f'<text x="{m}" y="{H-12}" class="ax">{esc(xl)}</text>'
          f'<text x="6" y="{m-14}" class="ax">{esc(yl)}</text>')
    leg = "".join(
        f'<circle cx="{W-150+70*i}" cy="20" r="5" fill="{cmap[c]}"/>'
        f'<text x="{W-140+70*i}" y="24" class="lg">{esc(c)}</text>'
        for i, c in enumerate(cvals[:3]))
    drop_note = f" 변환 불가 {dropped}행 제외." if dropped else ""
    return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>{_svg(W,H,grid+ax+leg+pts)}'
            f'<div class="fig-c">{esc(xl)} ↔ {esc(yl)} 트레이드오프. 색 = 배치.{esc(drop_note)}</div></div>')

# 3) 수렴 다이어그램 — 라운드별 입장 수렴
def convergence_svg(cols, title):
    """cols: [{round, note, nodes:[{label, x?}]}] 왼→오 라운드, 마지막에 합류."""
    if not cols:
        return (f'<div class="fig wide"><div class="fig-t">{esc(title)}</div>'
                f'<div class="fig-c">데이터 부족 — 라운드 수렴 데이터가 비어 있다.</div></div>')
    # 높이 동적(감사 1-F 경미) — 고정 250px 은 21석에서 노드 간격 8.6px 로 라벨이 완전 중첩됐다.
    n = len(cols)
    max_nodes = max(len(c.get("nodes") or []) for c in cols) or 1
    W, H = 460, max(250, 70 + 22 * max_nodes); cw = W / n
    body = ""; prev_y = []
    for i, c in enumerate(cols):
        cx = cw * i + cw / 2
        body += f'<text x="{cx:.0f}" y="20" class="rnd" text-anchor="middle">{esc(c["round"])}</text>'
        ny = []
        k = len(c["nodes"])
        for j, nd in enumerate(c["nodes"]):
            y = 50 + (j + 0.5) * (H - 70) / k
            ny.append((cx, y))
            body += (f'<circle cx="{cx:.0f}" cy="{y:.0f}" r="5" fill="{CU if i==n-1 else TE}" opacity="0.9"/>'
                     f'<text x="{cx:.0f}" y="{y-9:.0f}" class="cn" text-anchor="middle">{esc(nd)}</text>')
        if prev_y:
            for (px, py) in prev_y:
                for (qx, qy) in ny:
                    body += f'<path d="M{px:.0f},{py:.0f} C{(px+qx)/2:.0f},{py:.0f} {(px+qx)/2:.0f},{qy:.0f} {qx:.0f},{qy:.0f}" class="flow"/>'
        prev_y = ny
    return (f'<div class="fig wide"><div class="fig-t">{esc(title)}</div>{_svg(W,H,body)}'
            f'<div class="fig-c">라운드를 거치며 도메인별 입장이 수렴. 마지막(구리)=합의.</div></div>')

# 4) 의사결정 매트릭스 — 기준 × 선호 방향/Run/챔피언
def matrix_html(rows, title):
    """rows: [{criterion, direction, run, why, champion}]"""
    trs = ""
    # 키 부재·None 내성(감사 1-F) — LLM 산출 rows 는 필드가 곧잘 빠진다. KeyError 크래시나
    # 'None' 문자열 렌더 대신 빈 칸으로 강등한다.
    _g = lambda r, k: "" if r.get(k) is None else str(r.get(k))  # noqa: E731
    for r in rows:
        dchip = f'<span class="chip {"center" if "center" in _g(r, "dir_key") else "surface"}">{esc(_g(r, "direction"))}</span>'
        trs += (f'<tr><td class="mc">{esc(_g(r, "criterion"))}</td><td>{dchip}</td>'
                f'<td class="mr">{esc(_g(r, "run"))}</td><td>{esc(_g(r, "why"))}</td>'
                f'<td class="mp">{esc(_g(r, "champion"))}</td></tr>')
    return (f'<div class="fig wide"><div class="fig-t">{esc(title)}</div>'
            f'<div class="tblwrap"><table class="dmx"><thead><tr><th>판정 기준</th><th>선호 방향</th><th>Run</th><th>근거</th><th>주장 도메인</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div></div>')

VIZ_CSS = """
<style>
 .vizsec .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
 @media(max-width:640px){.vizsec .grid2{grid-template-columns:1fr}}
 .fig{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
 .fig.wide{grid-column:1/-1}
 .fig-t{font-family:var(--mono);font-size:12px;letter-spacing:.03em;color:var(--ink);font-weight:640;margin-bottom:10px}
 .fig-c{font-size:11.5px;color:var(--muted);margin-top:8px;line-height:1.5}
 .chart{width:100%;height:auto;overflow:visible}
 .chart .ax{fill:var(--muted);font-family:var(--mono);font-size:11px}
 .chart .val{fill:var(--ink);font-family:var(--mono);font-size:12px;font-weight:600}
 .chart .grid{stroke:var(--line-soft);stroke-width:1}
 .chart .pt-l{fill:var(--ink);font-family:var(--mono);font-size:11px}
 .chart .lg{fill:var(--ink-soft);font-family:var(--mono);font-size:11px}
 .chart .rnd{fill:var(--copper);font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.03em}
 .chart .cn{fill:var(--ink-soft);font-family:var(--mono);font-size:9.5px}
 .chart .flow{fill:none;stroke:var(--teal);stroke-width:1.4;opacity:.32}
 table.dmx{width:100%;border-collapse:collapse;font-size:13px;min-width:560px}
 table.dmx th{font-family:var(--mono);font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);text-align:left;padding:9px 11px;border-bottom:1.5px solid var(--line)}
 table.dmx td{padding:9px 11px;border-bottom:1px solid var(--line-soft);color:var(--ink-soft);vertical-align:top}
 table.dmx td.mc{color:var(--ink);font-weight:600;white-space:nowrap}
 table.dmx td.mr{font-family:var(--mono);color:var(--ink)}
 table.dmx td.mp{font-family:var(--mono);font-size:11px;color:var(--muted)}
</style>
"""
