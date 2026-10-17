#!/usr/bin/env python3
# 상시 상태판의 스크립트 검사(MCP 실호출 · Drive latest/)를 돌려 Gatus 외부 끝점으로 밀어 넣는다 — status-board.sh run 이 Gatus 와 함께 띄운다
"""상시 상태판 2단계 — docs/improvement-1015/status-board.md · 결정 context-notes IM-D24~

    python3 ./infra/scripts/status-push.py loop --parent <pid>          # status-board.sh run 이 Gatus 와 함께 띄운다
    python3 ./infra/scripts/status-push.py once [mcp-smoke|drive-latest] [--no-push]   # 손으로 한 번 — 결과를 찍는다

무엇을 하나
  · 검사 목록은 생성기(gen-status-config.py)가 쓴 infra/.state/status/push.json 이다 — 이 박스에서 돌 수 있는 것만 실려 있다.
    돌 때마다 다시 읽는다(update-all 이 설정을 다시 만들어도 다시 띄울 필요가 없다).
  · mcp-smoke — `mcp-smoke.py --periodic --json`(읽기 낱말 허용 목록 · 백엔드당 하나 · 감사 표지 status-board:mcp-smoke).
    0성공 백엔드 · 배포본 드리프트 · 판정 불가를 실패로 민다. 사람 신원으로만 답하는 백엔드(ste)는 스모크가 '검사 못 함' 으로 뺀다.
  · drive-latest — 리모트마다 가장 새 `<접두>-<시각>/` 의 파일이 latest/ 에 같은 MD5(없으면 크기)로 있는가(docs/gotchas.md 8 —
    업로드가 시각 폴더까지만 되고 latest/ 가 낡으면 소비자가 옛 산출물을 오류 없이 받는다). Drive 에 못 닿아도 실패다(그 박스에서
    update-all 도 못 받는다). 프록시가 셸에만 있는 박스에서 부팅 유닛이 띄우면 이것이 뜬다 — 안내서 '함정'.
  · 밀어 넣기는 루프백 Gatus 에만, 프록시 없이. 실패한 밀어 넣기는 5초 간격으로 세 번까지 다시 한다(설정 다시 읽기 동안 1초쯤 안 받는다).
  · 경보 멈춤 걷어내기 — pause.json 의 시한이 지났거나(update-all 이 5b 전에 끝났다) 시한 기록 없이 설정에 maintenance 칸이 있으면
    생성기 --unpause-if-expired 를 부른다. Gatus 의 점검 창은 요일마다 되풀이되므로 남으면 다음 주 같은 시각에 또 멈춘다.
  · 로그는 상태가 바뀔 때만 한 줄(`[status-push]` — 상태판 로그 /tmp/hwax-services/status-board.log 에 섞인다). 토큰은 찍지 않는다.
  · 부모(status-board.sh 의 셸)가 사라지면 끝난다 — 남아서 옛 토큰으로 계속 밀지 않게. TERM 이면 도는 검사를 묶음째 내리고 끝난다
    (그 검사 결과는 밀지 않는다 — 스스로 끊은 것을 실패로 알리지 않게).

종료코드 — once: 0 전부 성공 · 1 실패 있음 · 2 push.json 을 못 읽었다(또는 그런 검사가 없다). loop: 부모가 사라지거나 TERM 이면 0.
표준 라이브러리만 쓴다(시스템 python3 으로 돈다). 스모크는 push.json 에 적힌 에이전트 서버 venv 로, 생성기는 포털 backend venv 로 부른다.
"""
import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "infra" / ".state" / "status"
PUSH = STATE / "push.json"
PAUSE = STATE / "pause.json"
CONF = STATE / "config.yaml"
KINDS = ("mcp-smoke", "drive-latest")
TICK_S = 15                 # 할 일이 있나 보는 간격
FIRST_DELAY_S = 120         # 뜬 뒤 첫 검사까지 — update-all 이 상태판을 다시 띄운 직후의 §6 과 겹치지 않게
ERR_MAX = 300               # Gatus 결과의 오류 칸에 싣는 글자 수
UNPAUSE_RETRY_S = 600       # 멈춤 걷어내기가 실패했을 때 다시 해 보는 간격
RCLONE_CALL_S = 120         # rclone 한 번의 상한

_child: subprocess.Popen | None = None
_stopping = False


def log(msg: str) -> None:
    print(f"[status-push] {time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}", flush=True)


def _first(text: str | None, n: int = 160) -> str:
    for ln in (text or "").splitlines():
        if ln.strip():
            return ln.strip()[:n]
    return ""


def _kill_group(p: subprocess.Popen) -> None:
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(p.pid, sig)
        try:
            p.wait(wait)
            return
        except subprocess.TimeoutExpired:
            continue


def _proc(cmd: list[str], timeout_s: float, env: dict | None = None) -> tuple[int | None, str, str]:
    """(rc — 시간 초과면 None, stdout, stderr). 자식은 제 세션으로 띄워 시간 초과 · TERM 에 묶음째(손자까지) 내린다."""
    global _child
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True,
                             start_new_session=True, env=env)
    except OSError as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"
    _child = p
    try:
        out, err = p.communicate(timeout=max(1.0, timeout_s))
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        _kill_group(p)
        out, err = p.communicate()
        return None, out, err
    finally:
        _child = None


# ── 검사 ──────────────────────────────────────────────────────────────────────────────────────────
def check_mcp_smoke(c: dict) -> tuple[bool, str]:
    py = str(c.get("python") or "")
    if not os.access(py, os.X_OK):
        return False, f"mcp 모듈이 있는 python 이 없다({py or '설정에 없음'}) — 상태판 설정을 다시 만든다(update-all 5b)"
    env = dict(os.environ)
    for k in ("NO_PROXY", "no_proxy"):                        # 스모크는 루프백 게이트웨이만 본다 — 셸의 프록시가 그것까지 삼키지 않게
        env[k] = ",".join(x for x in (env.get(k, ""), "127.0.0.1", "localhost") if x)
    rc, out, err = _proc([py, str(ROOT / "infra" / "scripts" / "mcp-smoke.py"), "--periodic", "--json"], c["timeout_s"], env)
    if rc is None:
        return False, f"시간 초과({c['timeout_s']}초) — 스모크가 끝나지 않았다"
    if rc == 2:
        return False, "판정 못 함 — " + (_first(err) or _first(out) or "게이트웨이에 붙지 못했다(rc 2)")
    try:
        d = json.loads(out)
    except ValueError:
        return False, f"스모크 출력을 읽지 못했다(rc {rc}) — {_first(err)}"
    backends = d.get("backends") or {}
    dead = d.get("dead") or []
    drift = d.get("drift") or {}
    if dead:
        return False, "호출 0성공 — " + " · ".join(f"{n}: {str((backends.get(n) or {}).get('why') or '')[:80]}" for n in dead)
    if drift:
        return False, "배포본이 코드보다 오래됐다 — " + " · ".join(
            f"{n}(앱 {v.get('app')} · 게이트웨이 {v.get('gateway')})" for n, v in drift.items() if isinstance(v, dict))
    if rc != 0:
        return False, f"스모크가 rc {rc} 로 끝났다 — {_first(err)}"
    probed = [n for n, v in backends.items() if isinstance(v, dict) and not v.get("unprobed")]
    return True, f"백엔드 {len(probed)}곳 호출 성공" + (f" · 검사 못 함 {len(backends) - len(probed)}곳" if len(backends) > len(probed) else "")


def _lsjson(remote: str, folder: str, timeout_s: float) -> tuple[dict | None, str]:
    """{이름: (크기, md5 또는 '')} — 못 읽었으면 (None, 사유)."""
    rc, out, err = _proc(["rclone", "lsjson", "--files-only", "--hash", "--hash-type", "md5", f"{remote}/{folder}/"], timeout_s)
    if rc != 0:
        return None, "시간 초과" if rc is None else f"rc {rc} — {_first(err, 100)}"
    try:
        rows = json.loads(out or "[]")
    except ValueError:
        return None, "rclone 출력을 읽지 못했다"
    return {r["Name"]: (r.get("Size"), str((r.get("Hashes") or {}).get("md5") or "").lower())
            for r in rows if isinstance(r, dict) and r.get("Name")}, ""


def check_drive_latest(c: dict) -> tuple[bool, str]:
    end = time.monotonic() + c["timeout_s"]
    bad: list[str] = []
    good = 0
    for r in c.get("remotes") or []:
        label, remote, prefix = r.get("label", "?"), str(r.get("remote", "")).rstrip("/"), r.get("prefix", "")
        left = lambda: max(5.0, min(RCLONE_CALL_S, end - time.monotonic()))   # noqa: E731
        if time.monotonic() >= end:
            bad.append(f"{label}: 시간이 모자라 보지 못했다({c['timeout_s']}초)")
            continue
        rc, out, err = _proc(["rclone", "lsf", "--dirs-only", f"{remote}/"], left())
        if rc != 0:
            bad.append(f"{label}: Drive 에 닿지 못했다(rclone {'시간 초과' if rc is None else f'rc {rc}'} — {_first(err, 100)})")
            continue
        dirs = [ln.strip().rstrip("/") for ln in out.splitlines() if ln.strip()]
        stamped = sorted(d for d in dirs if prefix and d.startswith(prefix))
        if not stamped:
            good += 1                                         # 시각 붙은 업로드가 없다 — 견줄 것이 없다
            continue
        newest = stamped[-1]
        if "latest" not in dirs:
            bad.append(f"{label}: latest/ 가 없다(가장 새 업로드 {newest}/)")
            continue
        a, why_a = _lsjson(remote, newest, left())
        b, why_b = _lsjson(remote, "latest", left())
        if a is None or b is None:
            bad.append(f"{label}: Drive 목록을 읽지 못했다({why_a or why_b})")
            continue
        diff = []
        for name, (size, md5) in sorted(a.items()):
            if name not in b:
                diff.append(f"{name}(latest/ 에 없다)")
                continue
            bsize, bmd5 = b[name]
            if (md5 and bmd5 and md5 != bmd5) or ((not md5 or not bmd5) and size != bsize):
                diff.append(name)
        if diff:
            bad.append(f"{label}: latest/ 가 {newest}/ 보다 낡았다 — {', '.join(diff[:4])}" + (f" 외 {len(diff) - 4}" if len(diff) > 4 else ""))
        else:
            good += 1
    if bad:
        return False, " · ".join(bad)
    return True, f"리모트 {good}곳 — latest/ 가 가장 새 업로드와 같다"


CHECKS = {"mcp-smoke": check_mcp_smoke, "drive-latest": check_drive_latest}


# ── push.json · 밀어 넣기 ─────────────────────────────────────────────────────────────────────────
def read_push() -> tuple[dict | None, str]:
    try:
        cfg = json.loads(PUSH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{PUSH.relative_to(ROOT)} 이 없다 — 상태판 설정을 만든다(python3 ./infra/scripts/gen-status-config.py)"
    except (OSError, ValueError) as exc:
        return None, f"{PUSH.relative_to(ROOT)} 을 읽지 못했다 — {type(exc).__name__}"
    ok = (isinstance(cfg, dict) and isinstance(cfg.get("url"), str) and cfg["url"].startswith("http://127.0.0.1:")
          and isinstance(cfg.get("token"), str) and cfg["token"] and isinstance(cfg.get("checks"), list)
          and all(isinstance(c, dict) and c.get("kind") in KINDS and isinstance(c.get("key"), str)
                  and isinstance(c.get("every_s"), int) and c["every_s"] >= 60
                  and isinstance(c.get("timeout_s"), int) and c["timeout_s"] >= 10 for c in cfg["checks"]))
    if not ok:
        return None, f"{PUSH.relative_to(ROOT)} 의 모양이 다르다(루프백 주소 · 토큰 · 검사 목록) — 상태판 설정을 다시 만든다"
    return cfg, ""


def push(cfg: dict, key: str, ok: bool, reason: str, dur_s: float) -> tuple[bool, str]:
    q = {"success": "true" if ok else "false", "duration": f"{max(0, int(round(dur_s)))}s"}
    if not ok:
        q["error"] = reason[:ERR_MAX]
    url = f"{cfg['url'].rstrip('/')}/api/v1/endpoints/{urllib.parse.quote(key, safe='')}/external?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Bearer {cfg['token']}"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))     # 루프백 — 셸의 프록시를 타지 않는다
    why = ""
    for attempt in range(3):
        try:
            with opener.open(req, timeout=10) as r:        # noqa: S310 — push.json 의 루프백 주소(read_push 가 확인했다)
                return True, ""
        except urllib.error.HTTPError as exc:
            why = f"HTTP {exc.code}"
            if exc.code in (401, 404):                      # 토큰이나 끝점이 설정과 어긋났다 — 다시 해도 같다
                return False, why + " — 상태판 설정과 push.json 이 어긋났다(update-all 5b 가 둘을 같이 쓴다)"
        except Exception as exc:  # noqa: BLE001 — 연결 거부(설정 다시 읽기 · 재기동 중) 등
            why = type(exc).__name__
        if attempt < 2 and not _stopping:
            time.sleep(5)
    return False, why


def run(c: dict) -> tuple[bool, str, float]:
    t0 = time.monotonic()
    try:
        ok, reason = CHECKS[c["kind"]](c)
    except Exception as exc:  # noqa: BLE001 — 검사기 결함도 실패로 민다(조용히 멈추면 heartbeat 까지 기다려야 안다)
        ok, reason = False, f"검사기 오류 — {type(exc).__name__}: {exc}"[:ERR_MAX]
    return ok, reason, time.monotonic() - t0


# ── 경보 멈춤 걷어내기 ─────────────────────────────────────────────────────────────────────────────
def _needs_unpause(now: float) -> bool:
    try:
        rec = json.loads(PAUSE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        try:   # 시한 기록 없이 창만 남았다(손으로 지웠거나 걸기 중에 죽었다) — 생성기는 최상위 칸을 들여쓰지 않고 적는다
            return any(ln.startswith("maintenance:") for ln in CONF.read_text(encoding="utf-8").splitlines())
        except OSError:
            return False
    except (OSError, ValueError):
        return True
    until = rec.get("until") if isinstance(rec, dict) else None
    return not isinstance(until, (int, float)) or until <= now


def maybe_unpause(st: dict) -> None:
    now = time.time()
    if now < st.get("unpause_retry_at", 0) or not _needs_unpause(now):
        return
    py = ROOT / "backend" / ".venv" / "bin" / "python"
    rc, out, err = _proc([str(py) if os.access(py, os.X_OK) else "python3",
                          str(ROOT / "infra" / "scripts" / "gen-status-config.py"), "--unpause-if-expired"], 60)
    if rc == 0:
        st.pop("unpause_retry_at", None)
        if out.strip():
            log(out.strip().replace("\n", " · "))
    else:
        st["unpause_retry_at"] = now + UNPAUSE_RETRY_S
        log(f"⚠ 경보 멈춤의 시한이 지났는데 풀지 못했다(rc {rc} — {_first(out) or _first(err)}) — {UNPAUSE_RETRY_S // 60}분 뒤 다시")


# ── 실행 ──────────────────────────────────────────────────────────────────────────────────────────
def _on_term(signum, _frame) -> None:
    global _stopping
    _stopping = True
    if _child is not None:
        _kill_group(_child)


def loop(parent: int | None) -> int:
    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)
    start = time.monotonic()
    due: dict[str, float] = {}
    last: dict[str, tuple] = {}
    st: dict = {}
    cfg_why_logged = ""
    log("시작 — 검사 목록은 push.json, 첫 검사는 " + f"{FIRST_DELAY_S}초 뒤")
    while not _stopping:
        if parent and os.getppid() != parent:
            log("부모(status-board.sh)가 사라졌다 — 끝낸다")
            return 0
        maybe_unpause(st)
        cfg, why = read_push()
        if cfg is None:
            if why != cfg_why_logged:
                log(f"⚠ {why}")
                cfg_why_logged = why
        else:
            cfg_why_logged = ""
            for c in cfg["checks"]:
                key = c["key"]
                if time.monotonic() < due.setdefault(key, start + FIRST_DELAY_S):
                    continue
                ok, reason, dur = run(c)
                due[key] = time.monotonic() + c["every_s"]
                if _stopping:
                    break                                    # 스스로 끊은 검사는 밀지 않는다
                pushed, pwhy = push(cfg, key, ok, reason, dur)
                state = (ok, "" if ok else reason, pushed, pwhy)
                if last.get(key) != state:
                    log(f"{'✓' if ok else '✗'} {c['kind']} — {reason} ({dur:.0f}초)"
                        + ("" if pushed else f" · ⚠ 상태판에 밀어 넣지 못했다({pwhy})"))
                    last[key] = state
        for _ in range(TICK_S):
            if _stopping:
                break
            time.sleep(1)
    log("TERM — 끝낸다")
    return 0


def once(kind: str | None, no_push: bool) -> int:
    cfg, why = read_push()
    if cfg is None:
        print(f"✗ {why}")
        return 2
    checks = [c for c in cfg["checks"] if kind in (None, c["kind"])]
    if not checks:
        print(f"○ 이 박스에서 돌릴 {'검사' if kind is None else kind + ' 검사'}가 없다 — 생성기의 '스크립트 검사' 줄을 본다"
              "(python3 ./infra/scripts/gen-status-config.py)")
        return 2 if kind else 0
    rc = 0
    for c in checks:
        ok, reason, dur = run(c)
        print(f"{'✓' if ok else '✗'} {c['kind']} — {reason} ({dur:.0f}초)")
        if not no_push:
            pushed, pwhy = push(cfg, c["key"], ok, reason, dur)
            print(f"  · 상태판에 {'밀어 넣었다' if pushed else '밀어 넣지 못했다 — ' + pwhy}")
        rc = rc or (0 if ok else 1)
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="상시 상태판 스크립트 검사 — docs/improvement-1015/status-board.md")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("loop", help="상태판과 함께 돈다(status-board.sh run 이 띄운다)")
    lp.add_argument("--parent", type=int, default=None, help="이 pid 가 부모가 아니게 되면 끝낸다")
    op = sub.add_parser("once", help="한 번 돌려 결과를 찍는다")
    op.add_argument("kind", nargs="?", choices=KINDS)
    op.add_argument("--no-push", action="store_true", help="상태판에 밀어 넣지 않는다")
    a = ap.parse_args(argv)
    if a.cmd == "loop":
        return loop(a.parent)
    return once(a.kind, a.no_push)


if __name__ == "__main__":
    sys.exit(main())
