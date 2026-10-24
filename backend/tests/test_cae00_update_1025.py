# 10-25 cae00 업데이트 점검에서 고친 배치 길 — DynaForge 도는 작업 보호 · 배포물 · 이관 실패를 성공으로 치지 않기 · 허브 지문 · DocForge 묶기 · StepForge 재배포
"""왜 — update-all 을 cae00 에서 돌리기 전에 '데이터가 날아가거나 기능이 안 서는' 자리를 네 갈래로 훑었다(포털 · MX 백서 · 허브 앱 · DynaForge).
배치(deploy-all-from-drive.sh)는 dev 에서 돌리면 리포를 리셋하므로(docs/gotchas) 함수와 블록만 떼어 돌리고, 인라인 고침은 자리를 단언한다.

  · DynaForge 의 도는 로컬 작업 수 — 그 리포의 _common.sh 길로 psql(가짜 apptainer)을 불러 센다. 못 세면 빈 값(막지 않는다).
  · 배치의 KooRemapper 구역 — 도는 작업이 있으면 재기동을 미루고(○ · 3), 배포물 받기 실패를 실패로 센다.
  · MX 백서 이관 실패는 skip(exit 4) — 인스턴스는 그대로 둔다.
  · 허브 지문은 var/sifs 의 SIF · 해시만(잠금 · 정의 파일은 뺀다).
  · 포털 기동 — DocForge 데이터 루트가 $HOME 밖으로 가는 링크면 그 끝을 읽기 전용으로 묶는다.
  · update-all §5 — 허브 앱 재배포는 integrations/ 에 있는 폴더 이름을 고른다(step_forge 는 밑줄).
"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "infra" / "scripts"
DEPLOY = (SCRIPTS / "deploy-all-from-drive.sh").read_text(encoding="utf-8")
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
START = (SCRIPTS / "start.sh").read_text(encoding="utf-8")


def _bash(script: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], **(env or {})})


# ── DynaForge 도는 작업 수 ──────────────────────────────────────────────────────────────────────
def _koorm(tmp: Path, answer: str, rc: int = 0) -> Path:
    """가짜 KooRemapper 리포 — _common.sh 가 APPTAINER(가짜) · INST_POSTGRES · POSTGRES_* 를 세운다(그 리포의 꼴)."""
    repo = tmp / "KooRemapper"
    (repo / "platform/infra/scripts").mkdir(parents=True)
    appt = tmp / "apptainer"
    appt.write_text(f'#!/usr/bin/env bash\necho "$@" > "{tmp}/appt-args"\nprintf "%s\\n" "{answer}"\nexit {rc}\n')
    appt.chmod(0o755)
    (repo / "platform/infra/scripts/_common.sh").write_text(
        f'set -euo pipefail\nAPPTAINER="{appt}"\nINST_POSTGRES=koorm_postgres\nPOSTGRES_USER=koorm\nPOSTGRES_PORT=5436\nPOSTGRES_DB=koorm\n')
    return repo


def _count(repo: Path) -> str:
    r = _bash(f'. "{SCRIPTS}/lib/koorm-busy.sh"; hwax_koorm_running_jobs "{repo}"')
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_DynaForge_로컬_작업_수를_그_리포의_psql_길로_센다(tmp_path):
    repo = _koorm(tmp_path, " 3 ")
    assert _count(repo) == "3"
    args = (tmp_path / "appt-args").read_text()
    assert "exec instance://koorm_postgres psql -U koorm -p 5436 koorm -tAc" in args
    assert "status = 'running' AND external_kind IS NULL" in args, "stcx 외부 잡은 빼고 센다"


def test_못_세면_빈_값이다(tmp_path):
    assert _count(_koorm(tmp_path / "a", "", rc=1)) == "", "DB 가 안 받는다"
    assert _count(_koorm(tmp_path / "b", "ERROR: relation")) == "", "수가 아닌 답"
    assert _count(tmp_path / "없는-리포") == "", "리포가 없다"


# ── 배치(인라인) ─────────────────────────────────────────────────────────────────────────────────
def _block(start: str, end: str) -> str:
    i = DEPLOY.index(start)
    return DEPLOY[i:DEPLOY.index(end, i)]


def test_KooRemapper_구역은_도는_작업이_있으면_재기동을_미루고_배포물_실패를_실패로_센다():
    b = _block("if want kooremapper; then", "# start.sh 가 0 으로 끝나도")
    assert 'bash platform/infra/scripts/dist-from-drive.sh || skip "koorm dist-from-drive 실패' in b, "받기 실패가 경고(note)로만 끝나면 초록이다"
    assert 'hwax_koorm_running_jobs "$KOOR_DIR"' in b and 'KOORM_RESTART_FORCE' in b
    assert b.index("hwax_koorm_running_jobs") < b.index("hwax_restart_cycle kooremapper"), "재기동 전에 센다"
    assert "HWAX_RESTART_SKIPPED_FILE= hwax_restart_needed kooremapper" in b, "재기동이 필요할 때만 센다(장부에 두 번 적지 않게)"
    assert re.search(r"exit 3\n", b) and 'case "$_krc" in 0) ok "kooremapper up" ;; 3) ;;' in b, "미룸(3)은 실패로 세지 않는다"
    assert '. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/koorm-busy.sh"' in DEPLOY


def test_MX_백서_이관_실패는_실패로_센다():
    b = _block('if want mxwp; then', '# ── 3. HEAX Hub')
    assert "./infra/scripts/migrate.sh || skip \"mxwp migrate 실패" in b
    assert "mxwp migrate 실패(비치명)" not in b


def test_허브_지문은_SIF_와_해시만_센다():
    b = _block("if want heax; then", "# ── 3b. SignalForge")
    fp = next(ln for ln in b.splitlines() if "hwax_fp frontend/dist" in ln)
    assert "var/sifs/*.sif var/sifs/*.sif.hash" in fp and " var/sifs " not in fp


# ── 포털 기동 — DocForge 데이터 묶기 ───────────────────────────────────────────────────────────────
def _docforge_binds(tmp: Path, target: Path | None) -> str:
    home = tmp / "home"
    repo = home / "claude" / "HWAXPortal"
    repo.mkdir(parents=True)
    hub = home / "claude" / "HEAXHub" / "var"
    hub.mkdir(parents=True)
    if target is not None:
        target.mkdir(parents=True, exist_ok=True)
        (target / "doc_forge").mkdir(exist_ok=True)
        os.symlink(target, hub / "app_data")
    block = START[START.index("  # >>> docforge-bind"):START.index("  # <<< docforge-bind")]
    r = _bash(f'DATA_BINDS=(); REPO_ROOT="{repo}"\n{block}\nprintf "%s\\n" "${{DATA_BINDS[@]}}"; echo "ROOT=$DOCFORGE_ROOT"',
              env={"HOME": str(home)})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_DocForge_데이터가_HOME_밖으로_가는_링크면_그_끝을_읽기_전용으로_묶는다(tmp_path):
    out = _docforge_binds(tmp_path, tmp_path / "data" / "appdata")
    real = (tmp_path / "data" / "appdata" / "doc_forge").resolve()
    assert f"{real}:{real}:ro" in out, out
    assert f"ROOT={tmp_path / 'home' / 'claude' / 'HEAXHub' / 'var' / 'app_data' / 'doc_forge'}" in out, "앱에는 그대로 링크 경로를 준다"


def test_HOME_안이거나_없으면_묶지_않는다(tmp_path):
    assert "--bind" not in _docforge_binds(tmp_path / "a", tmp_path / "a" / "home" / "inside")
    assert "--bind" not in _docforge_binds(tmp_path / "b", None)


# ── update-all §5 — 허브 앱 재배포 폴더 ─────────────────────────────────────────────────────────────
def test_허브_앱_재배포는_있는_폴더_이름을_고른다(tmp_path):
    line = next(ln for ln in UA.splitlines() if ln.strip().startswith('_rdir="$_slug"'))
    hub = tmp_path / "HEAXHub"
    for d in ("step_forge", "hwax-risk", "doc-forge"):
        (hub / "integrations" / d).mkdir(parents=True)
    for slug, want in (("step_forge", "step_forge"), ("hwax_risk", "hwax-risk"), ("doc_forge", "doc-forge")):
        r = _bash(f'HEAX_DIR="{hub}"; _slug="{slug}"\n{line}\necho "$_rdir"')
        assert r.stdout.strip() == want, (slug, r.stdout, r.stderr)
    assert 'bash "$_rd" "$_rdir"' in UA
