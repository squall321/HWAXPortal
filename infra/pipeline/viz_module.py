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
    """factors: {name:(lo,hi)} 요인별 저/고 수준. resp: 응답 키. → 요인별 효과(hi평균-lo평균)."""
    eff = {}
    for fn, (lo, hi) in factors.items():
        mlo = sum(r[resp] for r in rows if r[fn] == lo) / max(1, sum(1 for r in rows if r[fn] == lo))
        mhi = sum(r[resp] for r in rows if r[fn] == hi) / max(1, sum(1 for r in rows if r[fn] == hi))
        eff[fn] = mhi - mlo
    return eff

def effects_svg(eff, title, unit):
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
    return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>{_svg(W,H,bars)}'
            f'<div class="fig-c">막대 = 요인 저→고 수준 변화 시 {esc(unit)} 변화량. 길수록 지배 인자.</div></div>')

# 2) 파레토 스캐터 — 두 응답의 트레이드오프, 점 색=범주
def scatter_svg(rows, xk, yk, ck, cvals, title, xl, yl, labelk=None):
    W, H, m = 460, 320, 44
    xs = [r[xk] for r in rows]; ys = [r[yk] for r in rows]
    xmn, xmx = min(xs), max(xs); ymn, ymx = min(ys), max(ys)
    def X(v): return m + (v - xmn) / (xmx - xmn or 1) * (W - m - 20)
    def Y(v): return H - m - (v - ymn) / (ymx - ymn or 1) * (H - m - 24)
    grid = "".join(f'<line x1="{m}" y1="{Y(ymn+(ymx-ymn)*i/4):.1f}" x2="{W-20}" y2="{Y(ymn+(ymx-ymn)*i/4):.1f}" class="grid"/>' for i in range(5))
    pts = ""
    cmap = {cvals[0]: TE, cvals[1]: CU}
    for r in rows:
        cx, cy = X(r[xk]), Y(r[yk])
        col = cmap.get(r[ck], MU)
        lab = f'<text x="{cx+9:.1f}" y="{cy+4:.1f}" class="pt-l">{esc(r[labelk])}</text>' if labelk else ""
        pts += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{col}" opacity="0.9"/>{lab}'
    ax = (f'<text x="{m}" y="{H-12}" class="ax">{esc(xl)}</text>'
          f'<text x="6" y="{m-14}" class="ax">{esc(yl)}</text>')
    leg = (f'<circle cx="{W-150}" cy="20" r="5" fill="{TE}"/><text x="{W-140}" y="24" class="lg">{esc(cvals[0])}</text>'
           f'<circle cx="{W-80}" cy="20" r="5" fill="{CU}"/><text x="{W-70}" y="24" class="lg">{esc(cvals[1])}</text>')
    return (f'<div class="fig"><div class="fig-t">{esc(title)}</div>{_svg(W,H,grid+ax+leg+pts)}'
            f'<div class="fig-c">{esc(xl)} ↔ {esc(yl)} 트레이드오프. 색 = 배치.</div></div>')

# 3) 수렴 다이어그램 — 라운드별 입장 수렴
def convergence_svg(cols, title):
    """cols: [{round, note, nodes:[{label, x?}]}] 왼→오 라운드, 마지막에 합류."""
    W, H = 460, 250; n = len(cols); cw = W / n
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
    for r in rows:
        dchip = f'<span class="chip {"center" if "center" in r.get("dir_key","") else "surface"}">{esc(r["direction"])}</span>'
        trs += (f'<tr><td class="mc">{esc(r["criterion"])}</td><td>{dchip}</td>'
                f'<td class="mr">{esc(r["run"])}</td><td>{esc(r["why"])}</td>'
                f'<td class="mp">{esc(r["champion"])}</td></tr>')
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
