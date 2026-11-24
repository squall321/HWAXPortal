#!/usr/bin/env python3
# db-sync 본체 — 레지스트리(services.yaml data:)와 동기화 원장을 읽어 상태·키 지문·manifest 검증을 내고, 적용 verbs 로 기존 병합 · 복원 스크립트를 잇는다.
"""
verbs
  status [svc]           서비스×클래스: kind · sync 모드 · 원장 last-applied(없으면 '-')
  keys-check [svc]       keys_with 가 가리키는 키 파일의 sha256 앞 12자 — 원문은 어떤 경우에도 출력하지 않는다
  verify <manifest.json> manifest.files{path: sha256} 전수 검증(rc 0/1)
  ssh-check [box…]       infra/boxes.yaml 의 박스마다 ssh BatchMode · 원격 db-sync · 역할 · rsync(rc 0/1)
  push · pull · mirror · rollback   적용 verbs(D5) — 기본은 미리보기, --apply 를 줘야 바꾼다(아래 '적용 verbs')

원장 위치: ${HWAX_DATA_ROOT:-/data}/hwax/state/db-sync/  — 이 디렉터리 생성이 D0 의 유일한 쓰기다(롤백 목록).
종료코드(적용 verbs): 0 됨 · 1 하다가 실패 · 2 사용법 · 3 거부(정책 · 확인 · 준비 안 됨 — 아무것도 바꾸지 않았다).
"""
import argparse
import collections
import datetime
import fcntl
import getpass
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import services as S  # noqa: E402 — 같은 해석기(resolve_dir·_hwax_setting)를 쓴다


def state_dir() -> Path:
    root = S._hwax_setting("HWAX_DATA_ROOT") or "/data"
    d = Path(root) / "hwax" / "state" / "db-sync"
    d.mkdir(parents=True, exist_ok=True)
    (d / "last-applied").mkdir(exist_ok=True)
    return d


def _sha12(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def _items(names: list[str]) -> list[dict]:
    raw = S.yaml.safe_load(S.MANIFEST.read_text(encoding="utf-8")) or {}
    out = [s for s in S.load() if s.get("data") and (not names or s["name"] in names)]
    for n, d in (raw.get("data_only") or {}).items():
        if not names or n in names:
            out.append({"name": n, "data": d, "_data_only": True})
    return out


def cmd_status(names: list[str]) -> int:
    sd = state_dir()
    print(f"  box={S.box_name()} role={S._hwax_setting('HWAX_BOX_ROLE') or '-'} 원장={sd}")
    for s in _items(names):
        print(f"── {s['name']}{'  (data_only)' if s.get('_data_only') else ''}")
        for cname, c in (s["data"].get("classes") or {}).items():
            if not isinstance(c, dict):
                continue
            la = sd / "last-applied" / f"{s['name']}.{cname}"
            last = la.read_text().strip()[:40] if la.exists() else "-"
            print(f"  {cname:<16} {str(c.get('kind', '-')):<9} sync={str(c.get('sync', '-')):<16} last-applied={last}")
    return 0


def cmd_keys_check(names: list[str]) -> int:
    rc = 0
    for s in _items(names):
        data = s["data"]
        sdir = None if s.get("_data_only") else S.resolve_dir(s)
        classes = data.get("classes") or {}
        for cname, c in classes.items():
            if not isinstance(c, dict) or not c.get("keys_with"):
                continue
            for k in c["keys_with"]:
                ref = classes.get(k) or {}
                cur = ref.get("current") or k
                if "#" in str(cur):  # ".env#KEY" — 그 줄의 값만 해시
                    f, key = str(cur).split("#", 1)
                    fp = (sdir / f) if (sdir and not Path(f).is_absolute()) else Path(f)
                    val = None
                    if fp.exists():
                        for ln in fp.read_text(errors="replace").splitlines():
                            if ln.startswith(key + "="):
                                val = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    fpr = hashlib.sha256(val.encode()).hexdigest()[:12] if val else None
                    print(f"  {s['name']}.{cname} ← {k}: {fpr or '없음'}")
                    rc |= 0 if fpr else 1
                    continue
                p = Path(os.path.expandvars(str(cur))).expanduser()
                if not p.is_absolute() and sdir:
                    p = sdir / p
                if p.is_dir():
                    for f in sorted(p.iterdir()):
                        if f.is_file():
                            print(f"  {s['name']}.{cname} ← {k}/{f.name}: {_sha12(f)}")
                elif p.is_file():
                    print(f"  {s['name']}.{cname} ← {k}: {_sha12(p)}")
                else:
                    print(f"  {s['name']}.{cname} ← {k}: 없음 ({p})")
                    rc = 1
    return rc


def cmd_verify(path: str) -> int:
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(m.get("base") or Path(path).parent)
    bad = 0
    for rel, want in (m.get("files") or {}).items():
        f = base / rel
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
        okay = got == want
        bad |= 0 if okay else 1
        print(f"  {'✓' if okay else '✗'} {rel}")
    print("  OK" if not bad else "  sha256 불일치 — 적용 금지")
    return bad


# ── 적용 verbs(D5) ─────────────────────────────────────────────────────────────────────────────────────────────────
# 사용자 결정(11-24)으로 짓기만 했다 — 10-31 A2 의 보류를 뒤집음, 실제 push · mirror 를 돌릴지는 사람이 정한다.
# 흐름은 PLAN §8.1 그대로다 — rsync(ssh) → 받는 박스 사전 백업(backup-local) → 기존 병합 · 복원 스크립트 → 원장.
# 새 병합 엔진은 없다. 레지스트리가 선언한 것(merge_input · restore_tool)만 부르고, 선언이 없는 서비스는 거부한다.
# 받는 박스의 일(사전 백업 · 병합 · 원장)은 늘 **그 박스의** 코드 · 설정 · 역할로 한다 — push 는 ssh 로 그쪽 `_apply` 를 부른다.

ROLE_ORDER = {"dev": 0, "staging": 1, "prod": 2}
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")      # 박스 키 · host · user — '-' 로 시작하면 ssh 옵션으로 읽힌다
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/@+-]+$")         # 원격이 돌려준 경로 — rsync 원격 지정에 그대로 실린다
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=60"]


class Refused(Exception):
    """정책 · 확인 · 준비 안 됨 — 아무것도 바꾸지 않았다(rc 3)."""


class Failed(Exception):
    """하다가 실패(rc 1)."""


def _abs_setting(v: str, what: str) -> Path:
    # cae00 09-05 사고 — 상대경로 HWAX_DATA_ROOT 가 경로 연산에 그대로 들어갔다. 적용 verbs 는 절대경로가 아니면 손대지 않는다.
    if not v.startswith("/"):
        raise Refused(f"{what}='{v}' 는 절대경로가 아니다 — 아무것도 하지 않았다")
    return Path(v)


def _data_root() -> Path:
    return _abs_setting(S._hwax_setting("HWAX_DATA_ROOT") or "/data", "HWAX_DATA_ROOT")


def _backup_root() -> Path:
    return _abs_setting(os.environ.get("BACKUP_ROOT") or "/data/backups", "BACKUP_ROOT")   # backup-local.sh 와 같은 기본값


def _state_path() -> Path:
    """원장 자리 — 만들지 않는다(미리보기는 아무것도 바꾸지 않는다). 적용할 때만 _state_apply()."""
    return _data_root() / "hwax" / "state" / "db-sync"


def _state_apply() -> Path:
    d = _state_path()
    (d / "last-applied").mkdir(parents=True, exist_ok=True)
    return d


def _role() -> str | None:
    return S._hwax_setting("HWAX_BOX_ROLE")


def _jid(svc: str) -> str:
    return f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{svc}"   # 마이크로초까지 — 같은 초의 두 적용이 같은 자리를 쓰지 않게


def _target(name: str):
    """서비스 → (svc, 클래스 이름, 클래스, backup-local 라벨, 서비스 리포). 지금은 postgres 클래스 하나만 다룬다."""
    svc = next((s for s in S.load() if s.get("name") == name and s.get("data")), None)
    if svc is None:
        raise Refused(f"'{name}' 은 레지스트리(services.yaml data:)에 없다")
    pgs = [(k, c) for k, c in (svc["data"].get("classes") or {}).items()
           if isinstance(c, dict) and c.get("kind") == "postgres" and c.get("sync") in ("publish-merge", "mirror")]
    label = (svc["data"].get("backup_want") or [None])[0]
    if not pgs or not label:
        raise Refused(f"{name}: 동기화하는 postgres 클래스 · backup-local 라벨(backup_want)이 없다")
    return svc, pgs[0][0], pgs[0][1], label, S.resolve_dir(svc)


def _tool(svc: dict, cname: str, c: dict, sdir: Path | None, mode: str) -> tuple[Path, str | None]:
    """부를 기존 스크립트. publish = merge_tool + merge_input(로컬 덤프 입구), mirror · rollback = restore_tool."""
    who = f"{svc['name']}.{cname}"
    if mode == "publish":
        if c.get("sync") != "publish-merge":
            raise Refused(f"{who}: sync={c.get('sync')} — publish(병합) 대상이 아니다")
        rel, var = c.get("merge_tool"), c.get("merge_input")
        if not rel or not var:
            raise Refused(f"{who}: 병합 스크립트의 로컬 덤프 입구가 선언되지 않았다(merge_input — checklist D5 '로컬 입력 입구')")
    else:
        rel, var = c.get("restore_tool"), None
        if not rel:
            raise Refused(f"{who}: 통째 복원 도구가 선언되지 않았다(restore_tool — checklist D5 'mirror' 줄)")
    if sdir is None:
        raise Refused(f"{who}: 서비스 리포를 이 박스에서 찾지 못했다")
    p = sdir / rel
    if not p.is_file():
        raise Refused(f"{who}: {p} 없음")
    # 입구를 모르는 스크립트에 변수만 주면 조용히 Drive 최신을 받아 **다른 덤프**를 병합한다(AIDH · SF 둘 다 그 폴백이 있다).
    if var and var not in p.read_text(encoding="utf-8", errors="replace"):
        raise Refused(f"{who}: {p.name} 이 {var} 를 모른다 — 부르면 Drive 최신을 받아 병합한다, 부르지 않았다")
    return p, var


def _direction(mode: str, src: str | None, dst: str | None) -> None:
    """PLAN §3 · §8.3 — 역할 없는 박스는 아무 동기화도 안 한다 · publish 는 dev → staging → prod 쪽으로만 ·
    mirror 는 prod → staging 만(prod 는 mirror 를 받지 않고, 사용자 데이터는 dev 로 가지 않는다)."""
    if not src or not dst:
        raise Refused("박스 역할(HWAX_BOX_ROLE)이 비었다 — 역할 없는 박스는 어떤 동기화도 하지 않는다(PLAN §3)")
    for r in (src, dst):
        if r not in ROLE_ORDER:
            raise Refused(f"모르는 역할 '{r}' — dev · staging · prod 가운데 하나")
    if mode == "publish" and not ROLE_ORDER[src] < ROLE_ORDER[dst]:
        raise Refused(f"publish 는 dev → staging → prod 쪽으로만 간다 — {src} → {dst} 거부")
    if mode == "mirror" and not (src == "prod" and dst == "staging"):
        raise Refused(f"mirror 는 prod → staging 만 — {src} → {dst} 거부")


def _boxes() -> dict[str, dict]:
    p = S.PORTAL_ROOT / "infra" / "boxes.yaml"
    if not p.exists():
        raise Refused(f"{p} 없음 — infra/boxes.yaml.example 을 복사해 채운다(gitignore — 주소 · 계정은 이 박스에만 둔다)")
    raw = (S.yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("boxes") or {}
    out: dict[str, dict] = {}
    for name, b in raw.items():
        b = {k: str(v) for k, v in (b or {}).items() if v is not None}
        e = {"host": b.get("host", ""), "user": b.get("user", ""), "role": b.get("role", ""),
             "repo": b.get("repo", ""), "port": b.get("port", "22")}
        if not (_SAFE.match(str(name)) and _SAFE.match(e["host"]) and _SAFE.match(e["user"]) and e["port"].isdigit()):
            raise Refused(f"boxes.yaml '{name}': 이름 · host · user · port 꼴이 이상하다")
        if e["role"] not in ROLE_ORDER or not e["repo"].startswith(("/", "~/")):
            raise Refused(f"boxes.yaml '{name}': role 은 dev · staging · prod, repo 는 / 또는 ~/ 로 시작")
        out[str(name)] = e
    return out


def _box(name: str) -> dict:
    b = _boxes().get(name)
    if b is None:
        raise Refused(f"infra/boxes.yaml 에 '{name}' 이 없다")
    return b


def _ssh_e(b: dict) -> list[str]:
    return ["ssh", *SSH_OPTS, "-p", b["port"]]


def _ssh(b: dict, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
    """원격 db-sync 하나를 부른다. repo 가 ~/ 면 원격 셸의 $HOME 으로 푼다(박스마다 리포 자리가 다르다)."""
    repo = b["repo"]
    base = f'"$HOME"/{shlex.quote(repo[2:])}' if repo.startswith("~/") else shlex.quote(repo)
    cmd = f"{base}/infra/scripts/db-sync.sh " + " ".join(shlex.quote(a) for a in args)
    argv = [*_ssh_e(b), f"{b['user']}@{b['host']}", cmd]
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=capture, text=True)


def _rsync(srcs: list[str], dst: str, b: dict) -> int:
    return subprocess.run(["rsync", "-a", "--partial", "-e", " ".join(_ssh_e(b)), *srcs, dst],
                          stdin=subprocess.DEVNULL).returncode


def _remote_fail(r: subprocess.CompletedProcess, what: str) -> Exception:
    if r.returncode == 255:
        return Failed(f"{what}: ssh 실패 — 키 · 호스트 · known_hosts 를 본다(ssh-check, BatchMode 라 비밀번호를 묻지 않는다)")
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:]   # 잡지 않은 호출은 둘 다 None — 이미 화면에 나갔다
    msg = f"{what}: 원격이 rc {r.returncode} 로 끝났다 {' '.join(tail)}"
    return Refused(msg) if r.returncode == 3 else Failed(msg)


def _latest_dump(label: str) -> Path | None:
    """이 박스의 가장 새 daily 덤프 — .sha256 까지 쓰인 것만(backup-local 은 덤프를 다 쓴 뒤에 .sha256 을 쓴다)."""
    d = _backup_root() / "hwax" / S.box_name() / label / "daily"
    for f in sorted(d.glob(f"{label}-{S.box_name()}-*.sql.gz"), reverse=True):   # 이름의 시각 = 사전순
        if Path(f"{f}.sha256").is_file():
            return f
    return None


def _sha_ok(f: Path) -> bool:
    s = Path(f"{f}.sha256")
    if not (f.is_file() and s.is_file()):
        return False
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    want = (s.read_text().split() or [""])[0]
    return bool(want) and h.hexdigest() == want


def _inbound_dir(svc: str, jid: str) -> Path:
    d = _data_root() / "hwax" / ".staging" / "inbound" / svc / jid
    d.mkdir(parents=True, mode=0o700, exist_ok=True)
    return d


def _confirm(a, what: str) -> None:
    """두 번째 확인 — 지워지는 쪽 이름을 친다. --confirm 이 없으면 표준입력 한 줄(비었거나 닫혔으면 거부 — 크론은 늘 거부)."""
    want = f"{S.box_name()}/{a.svc}"
    got = a.confirm
    if got is None:
        print(f"  ⚠ {what} 는 이 박스({S.box_name()})의 {a.svc} DB 를 지우고 덮는다. 맞으면 '{want}' 를 그대로 친다.", flush=True)
        got = sys.stdin.readline().strip()
    if got != want:
        raise Refused(f"확인 이름이 다르다('{got}' ≠ '{want}') — 아무것도 하지 않았다")


def _pre_sync(label: str, jid: str) -> Path:
    """사전 백업 = 기존 backup-local.sh <라벨> 한 번. 새로 뜬 덤프를 pre-sync/<id>/ 로 **옮긴다** — daily 세대 정리가 지우지 않게.
    하드링크로 걸면 같은 초에 다시 뜬 backup-local 이 같은 이름을 `gzip >` 로 잘라 쓰면서 같은 inode 인 사전 백업까지 덮는다."""
    daily = _backup_root() / "hwax" / S.box_name() / label / "daily"

    def seen() -> dict[Path, tuple[int, int, int]]:
        return {f: (st.st_ino, st.st_mtime_ns, st.st_size) for f in daily.glob("*.sql.gz") for st in [f.stat()]}

    before = seen()
    print(f"→ 사전 백업: backup-local.sh {label}", flush=True)
    rc = subprocess.run(["bash", str(S.PORTAL_ROOT / "infra" / "scripts" / "backup-local.sh"), label],
                        stdin=subprocess.DEVNULL).returncode
    new = sorted(f for f, sig in seen().items() if before.get(f) != sig)   # 같은 초에 같은 이름을 다시 썼어도 잡힌다
    if rc != 0 or len(new) != 1 or not Path(f"{new[0]}.sha256").is_file():
        raise Failed(f"사전 백업 실패(rc {rc}, 새 덤프 {len(new)}개) — 병합 · 복원하지 않았다")
    dst = _backup_root() / "hwax" / S.box_name() / label / "pre-sync" / jid
    dst.mkdir(parents=True, mode=0o700)
    for f in (new[0], Path(f"{new[0]}.sha256")):
        shutil.move(str(f), str(dst / f.name))
    return dst / new[0].name


def _journal(sd: Path, rec: dict) -> None:
    with open(sd / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if rec.get("result") == "applied":
        (sd / "last-applied" / f"{rec['svc']}.{rec['class']}").write_text(f"{rec['ts']} {rec['mode']} from={rec['from']}\n")


def _apply_core(svc_name: str, mode: str, file: Path, src_box: str, src_role: str | None, jid: str, **extra) -> int:
    """받는 박스의 일 — 검사 → 잠금 → 사전 백업 → 기존 스크립트 → 원장. 실패해도 자동으로 되돌리지 않는다(D7 — 사람이 rollback)."""
    svc, cname, c, label, sdir = _target(svc_name)
    if mode != "rollback":
        _direction(mode, src_role, _role())
    tool, var = _tool(svc, cname, c, sdir, mode)
    if not _sha_ok(file):
        raise Refused(f"{file.name}: sha256 이 어긋나거나 .sha256 이 없다 — 적용하지 않았다")
    if S._update_all_running():
        raise Refused("update-all 이 도는 중이다(같은 병합 스크립트를 부른다) — 끝난 뒤 다시")
    sd = _state_apply()
    lock = open(sd / "db-sync.lock", "w")   # 파이썬 fd 는 자식에 물려주지 않는다(데몬이 잠금을 쥐는 일 없음)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise Refused("다른 db-sync 적용이 이 박스에서 도는 중이다") from None
    src = extra.pop("src", str(file))
    rec = {"id": jid, "ts": datetime.datetime.now().isoformat(timespec="seconds"), "svc": svc_name, "class": cname,
           "mode": mode, "from": src_box, "to": S.box_name(), "src": src, "file": file.name,
           "tool": str(tool.relative_to(sdir)), "operator": getpass.getuser(), **extra}
    try:
        pre = _pre_sync(label, jid)
    except Failed:
        _journal(sd, {**rec, "result": "failed", "stage": "pre-sync"})
        raise
    rec["pre_sync"] = str(pre)
    if mode == "publish":
        argv, env = ["bash", str(tool)], {**os.environ, var: str(file)}
    else:
        argv, env = ["bash", str(tool), str(file), "--yes"], dict(os.environ)   # AIDH · SF restore-db.sh 둘 다 받는 꼴
    print(f"→ {'병합' if mode == 'publish' else '복원'}: {rec['tool']}", flush=True)
    tail: collections.deque = collections.deque(maxlen=20)
    p = subprocess.Popen(argv, cwd=sdir, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, errors="replace")
    for ln in p.stdout:   # type: ignore[union-attr]
        print(ln, end="", flush=True)
        tail.append(ln.rstrip())
    rc = p.wait()
    _journal(sd, {**rec, "rc": rc, "out_tail": list(tail), "result": "applied" if rc == 0 else "failed",
                  **({} if rc == 0 else {"stage": "tool"})})
    if rc:
        print(f"✗ {rec['tool']} rc {rc} — 사전 백업 {pre}\n  되돌리려면 ./infra/scripts/db-sync.sh rollback --svc {svc_name} --id {jid}"
              " (미리보기 뒤 --apply)", flush=True)
        return 1
    print(f"✓ {mode} {svc_name}.{cname} ← {src_box} — 원장 {sd / 'journal.jsonl'} · id {jid}", flush=True)
    return 0


def _apply_and_clean(svc: str, mode: str, file: Path, src_box: str, src_role: str | None, jid: str, **extra) -> int:
    """받은 파일로 적용하고, 됐으면 받은 자리(.staging/inbound/<svc>/<id>)를 비운다 — 같은 파일이 보낸 박스 daily 에 남아 있다.
    실패면 진단용으로 남긴다."""
    rc = _apply_core(svc, mode, file, src_box, src_role, jid, **extra)
    inbound = _data_root() / "hwax" / ".staging" / "inbound"
    if rc == 0 and inbound in file.parent.parents:
        shutil.rmtree(file.parent, ignore_errors=True)
    return rc


def _plan_lines(rows: list[tuple[str, str]]) -> None:
    for k, v in rows:
        print(f"  {k:<10} {v}")


def _preview_end(a) -> bool:
    if a.apply:
        return False
    print("· 미리보기다 — 아무것도 바꾸지 않았다. 실제로 하려면 같은 명령에 --apply")
    return True


def cmd_push(a) -> int:
    b = _box(a.to)
    svc, cname, c, label, _sdir = _target(a.svc)
    me, role = S.box_name(), _role()
    _direction("publish", role, b["role"])
    if not c.get("merge_input"):
        raise Refused(f"{a.svc}.{cname}: 병합 스크립트의 로컬 덤프 입구가 선언되지 않았다(merge_input)")
    f = _latest_dump(label)
    if f is None:
        raise Refused(f"이 박스에 {label} daily 덤프(.sha256 까지)가 없다 — 먼저 ./infra/scripts/backup-local.sh {label}")
    jid = _jid(a.svc)
    age_h = (datetime.datetime.now().timestamp() - f.stat().st_mtime) / 3600
    print(f"push {a.svc}.{cname}  {me}({role}) → {a.to}({b['role']})  [{b['user']}@{b['host']}]  id {jid}")
    _plan_lines([("보낸다", f"{f} ({f.stat().st_size:,} B, {age_h:.1f}시간 전) + .sha256"),
                 ("받는 자리", f"{a.to}: <HWAX_DATA_ROOT>/hwax/.staging/inbound/{a.svc}/{jid}/ — sha256 이 어긋나면 멈춘다"),
                 ("사전 백업", f"{a.to}: backup-local.sh {label} → <BACKUP_ROOT>/hwax/<박스>/{label}/pre-sync/{jid}/"),
                 ("병합", f"{a.to}: {c['merge_input']}=<받은 파일> {c.get('merge_tool')} (그 박스의 역할 · 설정으로 다시 검사)"),
                 ("원장", f"{a.to}: <HWAX_DATA_ROOT>/hwax/state/db-sync/journal.jsonl")])
    if _preview_end(a):
        return 0
    r = _ssh(b, "_inbound", "--svc", a.svc, "--id", jid, capture=True)
    inbound = (r.stdout or "").strip().splitlines()[-1:] if r.returncode == 0 else []
    if not inbound or not _SAFE_PATH.match(inbound[0]):
        raise _remote_fail(r, "받는 자리 만들기") if r.returncode else Failed(f"원격이 받는 자리를 알려 주지 않았다: {r.stdout!r}")
    print(f"→ rsync → {a.to}:{inbound[0]}/", flush=True)
    if _rsync([str(f), f"{f}.sha256"], f"{b['user']}@{b['host']}:{inbound[0]}/", b):
        raise Failed("rsync 실패 — 원격에는 빈 받는 자리만 생겼고 병합하지 않았다")
    r = _ssh(b, "_apply", "--svc", a.svc, "--mode", "publish", "--file", f"{inbound[0]}/{f.name}",
             "--from", me, "--from-role", role or "", "--id", jid, "--src", str(f))
    if r.returncode:
        raise _remote_fail(r, f"{a.to} 의 적용")
    return 0


def cmd_pull(a, mode: str) -> int:
    b = _box(a.src)
    svc, cname, c, label, sdir = _target(a.svc)
    me, role = S.box_name(), _role()
    _direction(mode, b["role"], role)
    tool, var = _tool(svc, cname, c, sdir, mode)
    jid = _jid(a.svc)
    print(f"{a.verb} {a.svc}.{cname}  {a.src}({b['role']}) → {me}({role})  [{b['user']}@{b['host']}]  id {jid}")
    _plan_lines([("받는다", f"{a.src} 의 가장 새 {label} daily 덤프 + .sha256 (적용할 때 원격에서 고른다)"),
                 ("받는 자리", f"{_data_root()}/hwax/.staging/inbound/{a.svc}/{jid}/ — sha256 이 어긋나면 멈춘다"),
                 ("사전 백업", f"backup-local.sh {label} → {_backup_root()}/hwax/{me}/{label}/pre-sync/{jid}/"),
                 ("병합" if mode == "publish" else "복원",
                  f"{var}=<받은 파일> {tool}" if var else f"{tool} <받은 파일> --yes  ⚠ 이 박스의 DB 를 지우고 통째로 덮는다"),
                 ("원장", f"{_state_path()}/journal.jsonl")])
    if mode == "mirror" and not a.apply:
        print(f"  ⚠ mirror 는 지우기를 수반한다 — --apply 와 함께 '{me}/{a.svc}' 이름을 한 번 더 친다(--confirm 또는 입력)")
    if _preview_end(a):
        return 0
    if mode == "mirror":
        _confirm(a, "mirror")
    r = _ssh(b, "_latest", "--svc", a.svc, capture=True)
    if r.returncode:
        raise _remote_fail(r, f"{a.src} 의 덤프 고르기")
    try:
        info = json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Failed(f"원격 답을 읽지 못했다: {r.stdout!r}") from None
    if info.get("role") != b["role"]:
        raise Refused(f"{a.src} 의 실제 역할 {info.get('role')} ≠ boxes.yaml 의 {b['role']} — 받지 않았다")
    if not _SAFE_PATH.match(str(info.get("path", ""))):
        raise Failed(f"원격 경로 꼴이 이상하다: {info.get('path')!r}")
    dst = _inbound_dir(a.svc, jid)
    rpath = f"{b['user']}@{b['host']}:{info['path']}"
    print(f"→ rsync ← {rpath}", flush=True)
    if _rsync([rpath, f"{rpath}.sha256"], f"{dst}/", b):
        raise Failed(f"rsync 실패 — 받는 자리 {dst} 만 생겼고 적용하지 않았다")
    return _apply_and_clean(a.svc, mode, dst / Path(info["path"]).name, info.get("box") or a.src, info["role"], jid,
                            src=info["path"])


def _journal_rows() -> list[dict]:
    p = _state_path() / "journal.jsonl"
    rows = []
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(ln))
            except ValueError:
                continue
    return rows


def cmd_rollback(a) -> int:
    svc, cname, c, label, sdir = _target(a.svc)
    tool, _ = _tool(svc, cname, c, sdir, "rollback")
    rows = _journal_rows()
    cands = [i for i, r in enumerate(rows) if r.get("svc") == a.svc and r.get("pre_sync") and (not a.id or r.get("id") == a.id)]
    if not cands:
        raise Refused(f"원장에 {a.svc} 의 사전 백업이 {'id ' + a.id + ' 로 ' if a.id else ''}없다 — 되돌릴 자리가 없다")
    pick = rows[cands[-1]]
    later = [r for r in rows[cands[-1] + 1:] if r.get("svc") == a.svc and r.get("result") == "applied"]
    print(f"rollback {a.svc}.{cname}  {S.box_name()}  ← id {pick['id']} ({pick.get('mode')} from={pick.get('from')} · {pick.get('result')})")
    _plan_lines([("사전 백업", f"backup-local.sh {label} 한 번 더(이 되돌리기도 되돌릴 수 있게)"),
                 ("복원", f"{tool} {pick['pre_sync']} --yes  ⚠ 이 박스의 DB 를 지우고 그때 모습으로 덮는다"),
                 ("원장", f"{_state_path()}/journal.jsonl")])
    if later:
        print(f"  ⚠ 이 뒤에 적용된 것 {len(later)}건({', '.join(r['id'] for r in later)})과 그 사이 쓰인 줄도 함께 사라진다")
    if _preview_end(a):
        return 0
    _confirm(a, "rollback")
    return _apply_core(a.svc, "rollback", Path(pick["pre_sync"]), S.box_name(), _role(), _jid(a.svc), ref=pick["id"])


def cmd_ssh_check(names: list[str]) -> int:
    rc, me = 0, S.box_name()
    for n, b in _boxes().items():
        if names and n not in names:
            continue
        if n == me:
            print(f"  · {n}: 이 박스 — 건너뜀")
            continue
        r = _ssh(b, "_ping", capture=True)
        m = re.search(r"^ok box=(\S+) role=(\S+) rsync=(\S+)", r.stdout or "", re.M)
        if r.returncode == 255:
            last = (r.stderr or "").strip().splitlines()[-1:] or [""]
            print(f"  ✗ {n} ({b['user']}@{b['host']}): ssh 실패 — 키 · 호스트 · known_hosts 를 본다(BatchMode — 비밀번호를 묻지 않는다) {last[0]}")
            rc = 1
            continue
        if r.returncode or not m:
            print(f"  ✗ {n}: 닿았지만 원격 db-sync 가 이 판이 아니다(rc {r.returncode}) — repo={b['repo']} 를 보고 그 박스 리포를 받는다")
            rc = 1
            continue
        bad = ([f"원격 역할 {m[2]} ≠ boxes.yaml {b['role']}"] if m[2] != b["role"] else []) + \
              (["원격에 rsync 없음"] if m[3] != "yes" else [])
        warn = f"  (⚠ 원격 박스 이름 {m[1]} ≠ 키 {n})" if m[1] != n else ""
        print(f"  {'✗' if bad else '✓'} {n}: ssh · db-sync · role={m[2]}{(' — ' + ' · '.join(bad)) if bad else ''}{warn}")
        rc |= 1 if bad else 0
    return rc


def _remote_verb(verb: str, a) -> int:
    """ssh 로 불리는 안쪽 verbs — 사람이 직접 부를 일은 없다."""
    if verb == "_ping":
        print(f"ok box={S.box_name()} role={_role() or '-'} rsync={'yes' if shutil.which('rsync') else 'no'}")
        return 0
    if verb == "_latest":
        _svc, _c, _cl, label, _d = _target(a.svc)
        f = _latest_dump(label)
        if f is None:
            raise Refused(f"{S.box_name()} 에 {label} daily 덤프(.sha256 까지)가 없다 — 그 박스에서 backup-local.sh {label}")
        print(json.dumps({"path": str(f), "box": S.box_name(), "role": _role()}))
        return 0
    if verb == "_inbound":
        _target(a.svc)
        if not re.match(r"^\d{8}-\d{6}-[A-Za-z0-9._-]+$", a.id or ""):
            raise Refused(f"id 꼴이 이상하다: {a.id!r}")
        print(_inbound_dir(a.svc, a.id))
        return 0
    if verb == "_apply":
        if a.mode != "publish":
            raise Refused("원격 적용은 publish 만 받는다(mirror 는 받는 박스에서 pull 꼴로 — 확인 이름을 그 자리에서 친다)")
        return _apply_and_clean(a.svc, "publish", Path(a.file), a.src_box, a.from_role or None, a.id, src=a.src or a.file)
    return 2


def _parse(verb: str, rest: list[str]):
    ap = argparse.ArgumentParser(prog=f"db-sync.sh {verb}", allow_abbrev=False)   # '--app' 같은 줄임이 --apply 가 되지 않게
    ap.add_argument("--svc", required=verb not in ("_ping",))
    if verb == "push":
        ap.add_argument("--to", required=True)
    if verb in ("pull", "mirror"):
        ap.add_argument("--from", dest="src", required=True)
    if verb in ("push", "pull", "mirror", "rollback"):
        ap.add_argument("--apply", action="store_true", help="실제로 한다(없으면 미리보기)")
    if verb in ("mirror", "rollback"):
        ap.add_argument("--confirm", help="'<이 박스>/<svc>' — 지워지는 쪽 이름(없으면 입력으로 묻는다)")
    if verb in ("rollback", "_inbound", "_apply"):
        ap.add_argument("--id")
    if verb == "_apply":
        for k in ("--mode", "--file", "--from-role", "--src"):
            ap.add_argument(k)
        ap.add_argument("--from", dest="src_box")
    a = ap.parse_args(rest)
    a.verb = verb
    return a


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    verb, rest = argv[1], argv[2:]
    if verb == "status":
        return cmd_status(rest)
    if verb == "keys-check":
        return cmd_keys_check(rest)
    if verb == "verify" and rest:
        return cmd_verify(rest[0])
    try:
        if verb == "ssh-check":
            return cmd_ssh_check(rest)
        if verb in ("push", "pull", "mirror", "rollback", "_ping", "_latest", "_inbound", "_apply"):
            a = _parse(verb, rest)
            if verb == "push":
                return cmd_push(a)
            if verb in ("pull", "mirror"):
                return cmd_pull(a, "publish" if verb == "pull" else "mirror")
            if verb == "rollback":
                return cmd_rollback(a)
            return _remote_verb(verb, a)
    except Refused as e:
        print(f"✗ 거부 — {e}", file=sys.stderr)
        return 3
    except Failed as e:
        print(f"✗ 실패 — {e}", file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
