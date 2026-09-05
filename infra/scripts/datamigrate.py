#!/usr/bin/env python3
# /data 이관 실행기 — 레지스트리(services.yaml data:)를 읽어 아직 현행 경로에 있는 클래스만 옮긴다(멱등). 실패 시 자동 롤백.
"""
  datamigrate.py plan  [svc...]            무엇을 옮길지·막힌 이유(변경 없음)
  datamigrate.py run   [svc...] --yes      서비스별: pre-move 백업 → 크론 일시정지 → 정지 → 복사·검증 → 스왑(rename+심링크)
                                           → 기동 → health·행수 재검증 → DB 절대경로 행 치환 → 원장. 어느 단계든 실패 = 자동 롤백
  datamigrate.py rollback <svc> [--class C] 마지막 이동을 되돌린다(정지 → 심링크 제거 → .pre-move rename → 기동)
  datamigrate.py resume-crons              비정상 종료로 남은 크론 일시정지를 해제

원칙(docs/data-migration/PLAN.md §2): D1 켜지 않으면 무영향(HWAX_DATA_ROOT 없으면 plan 만) · D2 옛 경로는 gitignore 된
심링크로 영구 브리지 · D3 백업 없이 이동 없음 · D7 삭제는 사람이(.pre-move 는 남긴다) · D9 컨테이너는 /data 를 못 보므로
needs_bind 클래스는 재기동 뒤 컨테이너 가시성을 확인한 다음에만 옮긴다.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import services as S  # noqa: E402

MOVABLE = {"postgres", "sqlite", "blob", "model", "secret"}   # log·cache·backup(보존정책 몫)·identity·external 은 옮기지 않는다
ORDER = ["portal", "mcp-gateway", "agent-server", "mx-white-paper", "kooremapper", "heax-hub", "signalforge", "ai-data-hub"]
TS = time.strftime("%Y%m%d-%H%M%S")


def root_dir() -> str | None:
    return S._hwax_setting("HWAX_DATA_ROOT")


def state_dir() -> Path:
    d = Path(root_dir() or "/data") / "hwax" / "state" / "data-migrate"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", cmd], text=True, capture_output=True, check=check)


def env_get(f: Path, key: str) -> str | None:
    if not f.exists():
        return None
    v = None
    for ln in f.read_text(errors="replace").splitlines():
        if ln.startswith(key + "="):
            v = ln.split("=", 1)[1].split(" #", 1)[0].strip().strip('"').strip("'")
    return v or None


def url_parts(url: str) -> dict:
    import re
    m = re.match(r"^[a-z+]+://([^:/@]+)(?::([^@]*))?@([^:/]+):(\d+)/([^/?]+)", url)
    return {"user": m.group(1), "pw": m.group(2) or "", "port": m.group(4), "db": m.group(5)} if m else {}


def du_bytes(p: Path) -> int:
    r = sh(f"du -sbL {S.shlex.quote(str(p))} | cut -f1", check=False)   # -L: 브리지 심링크면 목표 크기
    return int(r.stdout.strip() or 0)


def fs_type(p: Path) -> str:
    q = p
    while not q.exists():
        q = q.parent
    return sh(f"stat -f -c %T {S.shlex.quote(str(q))}", check=False).stdout.strip()


def journal(entry: dict) -> None:
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "box": S.box_name(), **entry}
    with open(state_dir() / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 크론 일시정지(모든 줄) — 워치독(SF·HEAX·AIDH·Koorm)이 정지한 인스턴스를 되살리고 MTW 크론이 라이브 sqlite 에 쓴다 ──
def pause_crons() -> None:
    f = state_dir() / "crontab.paused"
    if f.exists():
        print("  ⚠ 이전 실행의 크론 일시정지가 남아 있다 — 먼저 복원한다"); resume_crons()
    cur = sh("crontab -l", check=False).stdout
    f.write_text(cur)
    sh("crontab -r", check=False)
    print(f"  · 크론 {len([l for l in cur.splitlines() if l.strip() and not l.startswith('#')])}줄 일시정지 → {f}")


def resume_crons() -> None:
    f = state_dir() / "crontab.paused"
    if f.exists():
        sh(f"crontab {S.shlex.quote(str(f))}")
        f.unlink()
        print("  · 크론 복원")


# ── 카운트·요약(이동 전/후 대조) ──
def pg_conn(svc: dict, c: dict) -> dict | None:
    conn = c.get("conn") or {}
    sdir = S.resolve_dir(svc)
    envf = sdir / conn.get("env", ".env") if sdir else None
    out = {"inst": c.get("instance"), "port": str(c.get("port", "")), "user": None, "db": None, "pw": ""}
    if conn.get("url") and envf:
        out.update({k: v for k, v in url_parts(env_get(envf, conn["url"]) or "").items() if v is not None})
    elif envf:
        out["user"] = env_get(envf, conn.get("user", "POSTGRES_USER")) or conn.get("user_default")
        out["db"] = env_get(envf, conn.get("db", "POSTGRES_DB")) or conn.get("db_default")
        out["pw"] = env_get(envf, conn.get("pw", "POSTGRES_PASSWORD")) or ""
        out["port"] = env_get(envf, conn.get("port_key", "POSTGRES_PORT")) or out["port"]
    return out if out["inst"] and out["user"] and out["db"] else None


def psql(conn: dict, sql: str, db: str | None = None) -> str:
    pw = f"--env PGPASSWORD={S.shlex.quote(conn['pw'])} " if conn.get("pw") else ""
    cmd = (f"apptainer exec {pw}instance://{conn['inst']} psql -h 127.0.0.1 -p {conn['port']} -U {S.shlex.quote(conn['user'])} "
           f"-d {S.shlex.quote(db or conn['db'])} -v ON_ERROR_STOP=1 -Atc {S.shlex.quote(sql)} 2>/dev/null")
    return sh(cmd).stdout


def pg_counts(conn: dict) -> dict:
    q = psql(conn, "select string_agg(format('select %L||''=''||count(*) from %I.%I', table_name, table_schema, table_name), ' union all ') "
                   "from information_schema.tables where table_schema not in ('pg_catalog','information_schema') and table_type='BASE TABLE'").strip()
    if not q:
        return {}
    return dict(l.split("=", 1) for l in psql(conn, q).splitlines() if "=" in l)


def sqlite_counts(p: Path) -> dict:
    import sqlite3
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        return {t: c.execute(f'select count(*) from "{t}"').fetchone()[0] for (t,) in
                c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")}
    finally:
        c.close()


def blob_summary(p: Path) -> dict:
    if p.is_file():   # 파일형 blob(게이트웨이 audit.jsonl)
        return {"files": 1, "bytes": p.stat().st_size}
    n = b = 0
    for f in p.rglob("*"):
        if f.is_file():
            n += 1; b += f.stat().st_size
    return {"files": n, "bytes": b}


def capture(kind: str, path: Path, conn: dict | None) -> dict:
    if kind == "postgres":
        return pg_counts(conn) if conn else {}
    if kind == "sqlite":
        return sqlite_counts(path) if path.is_file() else {}
    return blob_summary(path) if path.exists() else {}


# ── 계획 ──
def plan_service(svc: dict, root: str | None, box: str) -> list[dict]:
    data = svc.get("data") or {}
    sdir = S.resolve_dir(svc)
    plans = []
    for cname, c in (data.get("classes") or {}).items():
        if not isinstance(c, dict) or c.get("kind") not in MOVABLE or c.get("enabled") is False or not c.get("path") or not c.get("current"):
            continue
        cur, tgt = S.class_paths(svc, cname, c, root, box)
        st = S._data_status(cur, tgt) if (root and tgt) else ("only-current" if cur and (cur.exists() or cur.is_symlink()) else "absent")
        p = {"svc": svc["name"], "class": cname, "kind": c["kind"], "cur": cur, "tgt": tgt, "status": st, "blockers": [], "notes": [],
             "size": du_bytes(cur) if (cur and cur.exists()) else 0, "c": c}
        if st != "only-current":
            plans.append(p); continue
        if not root:
            p["blockers"].append("HWAX_DATA_ROOT 미설정")
        # gitignore — 심링크가 될 이름이 무시되지 않으면 update-all 의 git stash -u 가 치운다(사전점검 B1)
        if sdir and cur and str(cur).startswith(str(sdir) + "/"):
            rel = os.path.relpath(cur, sdir)
            if sh(f"git -C {S.shlex.quote(str(sdir))} check-ignore -q {S.shlex.quote(rel)}", check=False).returncode != 0:
                p["blockers"].append(f"gitignore 아님: {rel} — .gitignore 에 앵커 추가 먼저")
            if sh(f"git -C {S.shlex.quote(str(sdir))} ls-files -- {S.shlex.quote(rel)} | head -1", check=False).stdout.strip():
                p["blockers"].append(f"추적 파일 포함: {rel} — 심링크 불가")
        if c["kind"] == "postgres" and not c.get("external_instance"):
            inst = c.get("instance") or ""
            running = sh("apptainer instance list 2>/dev/null | awk 'NR>1{print $1}'", check=False).stdout.split()
            if inst not in running:
                p["blockers"].append(f"pg 인스턴스 '{inst}' 미기동(또는 이름 불일치) — 행수 대조 불가. 기동 뒤 다시(services.yaml instance: 확인)")
        if c["kind"] == "sqlite" and tgt and fs_type(tgt).startswith(("nfs", "cifs", "fuse")):
            p["blockers"].append(f"SQLite 는 NFS 금지(D6): {fs_type(tgt)}")
        if tgt:
            q = tgt
            while not q.exists():
                q = q.parent
            free = shutil.disk_usage(q).free
            if free < p["size"] * 1.5 + (1 << 30):
                p["blockers"].append(f"디스크 부족: 여유 {free >> 30}G < 필요 {(int(p['size'] * 1.5) >> 30) + 1}G")
        if c.get("needs_bind"):
            p["notes"].append("needs_bind — run 에서 재기동 뒤 컨테이너 가시성 확인")
        if c.get("db_paths"):
            p["notes"].append(f"DB 절대경로 행 치환 {len(c['db_paths'])}건")
        plans.append(p)
    return plans


def print_plan(plans: list[dict]) -> None:
    for p in plans:
        mark = "→" if (p["status"] == "only-current" and not p["blockers"]) else ("✗" if p["blockers"] else "·")
        print(f"  {mark} {p['class']:<14} {p['kind']:<9} {p['status']:<13} {p['size'] >> 20:>6}M  {p['cur']}  →  {p['tgt'] or '-'}")
        for b in p["blockers"]:
            print(f"        ✗ {b}")
        for n in p["notes"]:
            print(f"        · {n}")


# ── 실행 ──
def svc_up(svc: dict) -> bool:
    os.environ.setdefault("HWAX_HEALTH_WAIT", "300")   # HEAX heal.sh 전체 재기동은 120s 를 넘긴다
    ok = S.cmd_up([svc["name"]]) == 0
    also = (svc.get("data") or {}).get("restart_also") or []   # stop: 이 함께 세운 동거 프로세스(mxwp-mcp 등)
    if ok and also:
        S.cmd_up(list(also))
    return ok


def svc_down(svc: dict) -> None:
    S.cmd_down([svc["name"]])
    for _ in range(30):
        if not (svc.get("health") and S.health_ok(svc["health"], expect=svc.get("expect"))):
            break
        time.sleep(1)


def container_sees(inst: str, path: Path) -> bool:
    return sh(f"apptainer exec instance://{inst} test -d {S.shlex.quote(str(path))}", check=False).returncode == 0


def backup_pre_move(svc: dict) -> str | None:
    want = (svc.get("data") or {}).get("backup_want") or []
    if not want:
        return None
    bk = Path(os.environ.get("BACKUP_ROOT", "/data/backups")) / "hwax" / S.box_name()
    fresh = time.time() - 3 * 3600   # update-all 1b 가 직전에 전부 덤프한다 — 3시간 안의 daily 는 재사용(두 번 덤프 안 함)
    stale = [w for w in want if not any(f.stat().st_mtime > fresh for f in (bk / w / "daily").glob(f"{w}-*") if f.is_file())]
    if stale:
        r = sh(f"{S.shlex.quote(str(S.PORTAL_ROOT / 'infra/scripts/backup-local.sh'))} {' '.join(stale)}", check=False)
        if r.returncode != 0:
            raise RuntimeError("pre-move 백업 실패:\n" + "\n".join(l for l in r.stdout.splitlines() if "✗" in l))
    else:
        print(f"  · pre-move 백업: 3시간 안의 daily 덤프 재사용({', '.join(want)})", flush=True)
    pre = bk / svc["name"] / "pre-move" / TS
    pre.mkdir(parents=True, exist_ok=True)
    for w in want:  # 최신 daily 산출을 pre-move 로 하드링크(정리 find 범위 밖 → D7 사람이 지운다)
        files = sorted((f for f in (bk / w / "daily").glob(f"{w}-*") if f.is_file() and f.stat().st_mtime > fresh), key=lambda f: f.stat().st_mtime)[-2:]
        for f in files:
            try:
                os.link(f, pre / f.name)
            except OSError:
                shutil.copy2(f, pre / f.name)
    return str(pre)


def copy_class(p: dict) -> None:
    cur, tgt, kind = p["cur"], p["tgt"], p["kind"]
    tgt.parent.mkdir(parents=True, exist_ok=True)
    if tgt.exists() and (tgt.is_dir() and any(tgt.iterdir()) or tgt.is_file()):
        raise RuntimeError(f"목표가 비어 있지 않다: {tgt}")
    if kind == "sqlite" and cur.is_file():
        sh(f"python3 {S.shlex.quote(str(S.PORTAL_ROOT / 'infra/scripts/lib/sqlite_backup.py'))} backup {S.shlex.quote(str(cur))} {S.shlex.quote(str(tgt))}")
        if sqlite_counts(cur) != sqlite_counts(tgt):
            raise RuntimeError(f"sqlite 행수 불일치: {cur}")
        shutil.copymode(cur, tgt)
    elif cur.is_dir():
        sh(f"rsync -aHAX --numeric-ids {S.shlex.quote(str(cur))}/ {S.shlex.quote(str(tgt))}/")
        diff = sh(f"rsync -aHAXn --checksum {S.shlex.quote(str(cur))}/ {S.shlex.quote(str(tgt))}/ | grep -v '^sending\\|^sent\\|^total\\|^$' | wc -l", check=False).stdout.strip()
        if diff != "0":
            raise RuntimeError(f"rsync 검증 불일치({diff}줄): {cur}")
    else:
        shutil.copy2(cur, tgt)
    if kind == "secret":
        sh(f"chmod -R go-rwx {S.shlex.quote(str(tgt))}")


def swap_class(p: dict) -> Path:
    cur, tgt = p["cur"], p["tgt"]
    pre = cur.with_name(cur.name + f".pre-move-{TS}")
    os.rename(cur, pre)
    os.symlink(str(tgt), str(cur))
    return pre


def park_target(tgt: Path) -> None:
    """롤백한 이동의 목표 사본을 <tgt>.rolled-back-<TS> 로 비켜 둔다(삭제 아님·D7). 안 비키면 다음 run 이 divergent 로 막힌다."""
    if tgt.exists() or tgt.is_symlink():
        parked = tgt.with_name(tgt.name + f".rolled-back-{TS}")
        os.rename(tgt, parked); print(f"    ↩ 목표 사본 비켜둠 {parked} (유예 뒤 사람이 지운다)", flush=True)
        journal({"verb": "park", "tgt": str(tgt), "parked": str(parked)})


def unswap_class(cur: Path, pre: Path) -> None:
    if cur.is_symlink():
        cur.unlink()
    if pre.exists() and not cur.exists():
        os.rename(pre, cur)


def sql_lit(v: str) -> str:
    """SQL 문자열 리터럴. shlex.quote 는 슬래시만 있는 경로를 인용하지 않아 'syntax error at or near /' 로 롤백된 실사고(aidh 2026-09-05)."""
    return "'" + v.replace("'", "''") + "'"


def db_paths_sql(p: dict) -> list[tuple[str, str, str]]:
    old, new = sql_lit(str(p["cur"])), sql_lit(str(p["tgt"]))
    out = []
    for d in p["c"].get("db_paths") or []:
        t, col = d["table"], d["column"]
        if d.get("json"):
            sql = f"UPDATE {t} SET {col} = replace({col}::text, {old}, {new})::jsonb WHERE {col}::text LIKE '%' || {old} || '%'"
        else:
            sql = f"UPDATE {t} SET {col} = replace({col}, {old}, {new}) WHERE {col} LIKE {old} || '%'"
        out.append((t, col, sql))
    return out


def rewrite_db_paths(svc: dict, p: dict, conn: dict | None) -> list[str]:
    if not conn:
        raise RuntimeError("db_paths 있으나 pg conn 없음 — services.yaml conn: 확인")
    out = []
    for t, col, sql in db_paths_sql(p):
        r = sh(f"apptainer exec {('--env PGPASSWORD=' + S.shlex.quote(conn['pw']) + ' ') if conn.get('pw') else ''}instance://{conn['inst']} "
               f"psql -h 127.0.0.1 -p {conn['port']} -U {S.shlex.quote(conn['user'])} -d {S.shlex.quote(conn['db'])} -v ON_ERROR_STOP=1 -c {S.shlex.quote(sql)} 2>&1", check=False)
        if r.returncode != 0:   # 경로 행이 옛 경로로 남으면 첨부가 404 — 이동 자체를 되돌린다
            raise RuntimeError(f"db_paths 치환 실패 {t}.{col}: {r.stdout.strip()[-200:]}")
        out.append(f"{t}.{col}: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'rc=' + str(r.returncode)}")
    return out


def run_service(svc: dict, root: str, box: str, yes: bool) -> int:
    plans = plan_service(svc, root, box)
    print(f"── {svc['name']}")
    print_plan(plans)
    todo = [p for p in plans if p["status"] == "only-current" and not p["blockers"]]
    for p in plans:
        if p["status"] == "divergent":
            print(f"  ✗ {p['class']}: divergent(현행·목표 둘 다 존재) — 이 클래스는 사람이 정리한 뒤. 다른 클래스는 진행")
    if not todo:
        print("  · 옮길 것 없음"); return 0
    if not yes:
        print("  (plan 만 — 실행은 --yes)"); return 0
    data = svc.get("data") or {}
    pg_class = next((c for c in (data.get("classes") or {}).values() if isinstance(c, dict) and c.get("kind") == "postgres"), None)
    conn = pg_conn(svc, pg_class) if pg_class else None
    swapped: list[tuple[Path, Path]] = []
    pause_crons()
    try:
        # needs_bind: 목표 부모를 만들고 재기동해 컨테이너가 그 경로를 보는지 먼저 확인(D9) — 못 보면 그 클래스는 이번엔 건너뛴다
        nb = [p for p in todo if p["c"].get("needs_bind")]
        if nb:
            for p in nb:
                p["tgt"].parent.mkdir(parents=True, exist_ok=True)
            inst = data.get("app_instance")
            print(f"  · needs_bind {len(nb)}클래스 — 재기동 뒤 컨테이너({inst}) 가시성 확인")
            svc_down(svc); svc_up(svc)
            for p in list(nb):
                if not inst or not container_sees(inst, p["tgt"].parent):
                    print(f"    ✗ {p['class']}: 컨테이너가 {p['tgt'].parent} 를 못 본다 — start.sh 바인드(D9) 필요, 이번엔 건너뜀")
                    todo.remove(p)
            if not todo:
                return 0
        pre_ref = backup_pre_move(svc)
        print(f"  ✓ pre-move 백업 {pre_ref or '(대상 없음)'}", flush=True)
        # DB 행수는 정지 전에(psql 은 살아 있어야 한다) — 기동 뒤 앱이 시작 시 쓰는 행이 있어 post ≥ pre 로 본다(감소 = 유실 → 롤백)
        pre = {p["class"]: capture(p["kind"], p["cur"], conn) for p in todo if p["kind"] == "postgres"}
        print(f"  · 정지 {svc['name']}", flush=True); svc_down(svc)
        # 파일·sqlite 는 정지 뒤(조용할 때) 재고 → 복사 직후 목표와 대조. 기동 뒤에 다시 세지 않는다 — minio 가 .minio.sys/tmp 를
        # 시작·종료마다 갈아치워 568→554 로 어긋난 실사고(dev 2026-09-05). rsync --checksum 검증이 정본이고 이건 보조다.
        for p in todo:
            if p["kind"] != "postgres":
                pre[p["class"]] = capture(p["kind"], p["cur"], conn)
        for p in todo:
            copy_class(p)
            if p["kind"] != "postgres":
                got = capture(p["kind"], p["tgt"], conn)
                if p["kind"] == "sqlite" and got != pre[p["class"]]:
                    raise RuntimeError(f"{p['class']} sqlite 행수 불일치 {pre[p['class']]} → {got}")
                if p["kind"] != "sqlite" and got != pre[p["class"]]:
                    raise RuntimeError(f"{p['class']} 파일 수·크기 불일치 {pre[p['class']]} → {got}")
            print(f"  ✓ 복사·검증 {p['class']} → {p['tgt']}", flush=True)
        for p in todo:
            swapped.append((p["cur"], swap_class(p))); print(f"  ✓ 스왑 {p['cur']} → 심링크", flush=True)
        print(f"  · 기동 {svc['name']}", flush=True)
        if not svc_up(svc):
            raise RuntimeError("기동 실패(health)")
        for p in todo:
            if p["kind"] != "postgres":
                continue
            post = capture(p["kind"], p["cur"], conn)
            before = pre[p["class"]]
            if set(post) != set(before):
                raise RuntimeError(f"{p['class']} 테이블 집합 불일치 pre={sorted(set(before) ^ set(post))}")
            lost = {t: (before[t], post[t]) for t in before if int(post[t]) < int(before[t])}
            if lost:
                raise RuntimeError(f"{p['class']} 행수 감소(유실) {lost}")
            grew = {t: (before[t], post[t]) for t in before if int(post[t]) > int(before[t])}
            print(f"  ✓ {p['class']} 행수 대조 {len(before)}테이블 {'일치' if not grew else '기동 중 증분 ' + str(grew)}", flush=True)
        for p in todo:
            if p["c"].get("db_paths"):
                for line in rewrite_db_paths(svc, p, conn):
                    print(f"  · db_paths {line}")
        for p in todo:
            journal({"verb": "move", "svc": svc["name"], "class": p["class"], "kind": p["kind"], "cur": str(p["cur"]), "tgt": str(p["tgt"]),
                     "pre_move": str(p["cur"]) + f".pre-move-{TS}", "backup": pre_ref, "size": p["size"], "result": "ok"})
            (state_dir() / f"{svc['name']}.{p['class']}.json").write_text(json.dumps(
                {"ts": TS, "cur": str(p["cur"]), "tgt": str(p["tgt"]), "pre_move": str(p["cur"]) + f".pre-move-{TS}"}, ensure_ascii=False))
        print(f"  ✓ {svc['name']} 이동 완료 ({len(todo)}클래스). .pre-move-{TS} 는 유예 뒤 사람이 지운다(D7)")
        return 0
    except BaseException as e:  # noqa: BLE001 — 어떤 실패든(Ctrl-C·SIGTERM 포함) 롤백. 서비스가 내려간 채 남으면 안 된다
        print(f"  ✗ 실패: {e!r}\n  ↩ 롤백")
        try:
            svc_down(svc)
        except Exception:
            pass
        for cur, pre in reversed(swapped):
            unswap_class(cur, pre); print(f"    ↩ {cur} 복원", flush=True)
        for p in todo:
            park_target(p["tgt"])
        svc_up(svc)
        journal({"verb": "move", "svc": svc["name"], "result": "rolled-back", "error": repr(e)[:300]})
        if not isinstance(e, Exception):
            raise
        return 1
    finally:
        resume_crons()


def cmd_rollback(name: str, cname: str | None) -> int:
    files = sorted(state_dir().glob(f"{name}.{cname or '*'}.json"))
    if not files:
        print("  이동 기록 없음"); return 1
    svc = next((s for s in S.load() if s["name"] == name), None)
    if not svc:
        print("  서비스 없음"); return 1
    svc_down(svc)
    for f in files:
        st = json.loads(f.read_text())
        unswap_class(Path(st["cur"]), Path(st["pre_move"])); print(f"  ↩ {st['cur']} ← {st['pre_move']}")
        park_target(Path(st["tgt"]))
        f.unlink()
    ok = svc_up(svc)
    journal({"verb": "rollback", "svc": name, "class": cname, "result": "ok" if ok else "up-failed"})
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__); return 2
    verb, rest = argv[1], argv[2:]
    yes = "--yes" in rest
    names = [a for a in rest if not a.startswith("-")]
    if verb == "resume-crons":
        resume_crons(); return 0
    if verb == "rollback":
        cls = rest[rest.index("--class") + 1] if "--class" in rest else None
        return cmd_rollback(names[0], cls) if names else 2
    root, box = root_dir(), S.box_name()
    print(f"  HWAX_DATA_ROOT={root or '(미설정 — plan 만, 이동 없음)'}  box={box}  role={S._hwax_setting('HWAX_BOX_ROLE') or '-'}")
    if (state_dir() / "crontab.paused").exists():
        others = [l for l in sh("pgrep -af datamigrate.py", check=False).stdout.splitlines() if l.split()[0] != str(os.getpid())]
        if others:
            print("  ✗ 다른 이관기가 실행 중(크론 일시정지 보유) — 끝나길 기다려라"); return 1
        print("  ⚠ 이전 실행이 비정상 종료해 크론 일시정지가 남았다 — 복원 후 진행"); resume_crons()
    svcs = [s for s in S.load() if s.get("data") and (not names or s["name"] in names)]
    svcs.sort(key=lambda s: ORDER.index(s["name"]) if s["name"] in ORDER else 99)
    rc = 0
    for s in svcs:
        if verb == "plan":
            print(f"── {s['name']}"); print_plan(plan_service(s, root, box))
        elif verb == "run":
            if not root:
                print("  ✗ HWAX_DATA_ROOT 없음 — infra/.env 에 HWAX_DATA_ROOT=/data"); return 1
            rc |= run_service(s, root, box, yes)
        else:
            print(__doc__); return 2
    return rc


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))   # finally(크론 복원)·롤백이 돌게
    raise SystemExit(main(sys.argv))
