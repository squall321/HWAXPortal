#!/usr/bin/env bash
# Drive 의 배포 아티팩트가 이 박스(dev)의 것보다 오래됐는지 본다 — '올렸다고 생각했는데 안 올라간' 것을 잡는다.
#
# 왜 필요한가.
#   앱을 dev 에서 다시 빌드하는 일(허브 재등록·redeploy-app)과 그걸 Drive 로 올리는 일
#   (build-all-to-drive.sh)은 서로 다른 명령이고 아무도 둘을 잇지 않는다. 그래서 dev 의
#   var/sifs/<app>.sif 는 새것인데 Drive 는 일주일 전 것인 상태가 조용히 유지된다.
#   cae00 의 '✓ checksums OK' 는 이걸 못 잡는다 — 그건 '받은 파일이 Drive 의 것과 같다'만
#   증명하지, 'Drive 가 dev 와 같다'는 말하지 않는다.
#   실제 사고(2026-08-18): materialtwin-web.sif 가 Drive 에 8/11 본으로 남아 cae00 이 옛 앱을
#   돌렸고, 새 데이터가 옛 스키마의 CHECK 에 걸려 app-data 병합이 통째로 실패했다.
#
#   ./infra/scripts/drive-drift.sh          # 전부 확인
#   ./infra/scripts/drive-drift.sh heax     # 지정한 것만 (portal | heax | koorm | mxwp | ste)
#
# 종료코드 0=일치, 1=드리프트 있음(올려야 함), 2=확인 불가.
set -uo pipefail

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARENT="$(dirname "$SELF_REPO")"
find_repo() { local n="$1"; for c in "$PARENT/$n" "$HOME/Projects/$n" "$HOME/claude/$n"; do
  [ -d "$c" ] && { printf '%s' "$c"; return 0; }; done; return 0; }

WANT="${*:-portal heax koorm mxwp ste}"
want() { printf '%s\n' $WANT | grep -qx "$1"; }
command -v rclone >/dev/null 2>&1 || { echo "✗ rclone 없음 — 확인 불가"; exit 2; }

DRIFT=0
env_get() { sed -n "s/^$1=//p" "$2" 2>/dev/null | tail -1 | tr -d "\"'"; }

# ── 포털 자신 — SPA(frontend/dist)와 SIF 가 Drive 아티팩트로 cae00 에 간다.
# cae00 은 포털을 빌드하지 않는다(images-from-drive 로 받기만 한다). 그래서 프론트를 고치고
# 올리지 않으면 그 화면은 영영 안 바뀐다 — 실제로 시험계획 탭과 mermaid 테마가 9일간
# dev 에만 있었다(2026-08-19). 이 검사가 포털을 안 보고 있던 것이 그 원인이다.
if want portal; then
  R="$(env_get HWAX_DRIVE_REMOTE "$SELF_REPO/infra/.env")"; R="${R%/}"
  if [ -z "$R" ]; then echo "· HWAX_DRIVE_REMOTE 미설정 — 건너뜀"; else
    echo "── HWAX Portal ($R/latest)"
    q=0
    newest="$(find "$SELF_REPO/frontend/dist" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
    t="$(rclone lsl "$R/latest/frontend-dist.tar.gz" 2>/dev/null | awk '{print $2" "$3}')"
    if [ -n "$newest" ] && [ -n "$t" ]; then
      e="$(date -d "$t" +%s 2>/dev/null || echo 0)"
      if [ "${newest%.*}" -gt "$e" ]; then
        echo "  ✗ frontend/dist — Drive frontend-dist.tar.gz($t)보다 새것이다"; DRIFT=1; q=1
      fi
    elif [ -z "$t" ]; then
      echo "  ✗ frontend-dist.tar.gz — Drive 에 없다"; DRIFT=1; q=1
    fi
    # SIF 도 본다 — 백엔드 의존성이 바뀌면(예: python-docx 추가) dist 는 그대로인데 SIF 만
    # 달라진다. dist 만 보고 있으면 '올렸는데 500' 이 된다(실측 2026-08-19: 컨테이너에
    # python-docx 가 없어 워드 내보내기가 500 이었다).
    # searxng-fixed.sif 도 본다. images-to-drive 가 latest/ 를 sync(미러)하므로 스테이징에서
    # 빠지면 조용히 삭제된다 — 실제로 한 번 그렇게 사라졌고(2026-08-19), 이 검사가 그 파일을
    # 안 보고 있어서 "✓ 일치" 로 보였다. gatus.sif(상시 상태판)·guidellm.sif(LLM 풀 용량 측정 — build-guidellm.sh)·phoenix.sif(호출 추적 —
    # build-phoenix.sh)도 같은 까닭으로 본다.
    for _sif in portal nginx searxng-fixed gatus guidellm phoenix; do
      _l="$SELF_REPO/infra/apptainer/${_sif}.sif"
      [ -f "$_l" ] || _l="$HOME/serviceApptainers/${_sif}.sif"   # dev 는 여기에 굽는다
      [ -f "$_l" ] || continue
      _ls="$(stat -c%s "$_l")"
      _ds="$(rclone lsl "$R/latest/${_sif}.sif" 2>/dev/null | awk '{print $1}')"
      if [ -z "$_ds" ]; then
        echo "  ✗ ${_sif}.sif — Drive 에 없다"; DRIFT=1; q=1
      elif [ "$_ls" != "$_ds" ]; then
        echo "  ✗ ${_sif}.sif — 로컬 $_ls ≠ Drive $_ds"; DRIFT=1; q=1
      fi
    done
    # 소스가 dist 보다 새것이면 빌드부터 안 한 것이다 — 올려도 옛 화면이 간다.
    src="$(find "$SELF_REPO/frontend/src" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
    if [ -n "$src" ] && [ -n "$newest" ] && [ "${src%.*}" -gt "${newest%.*}" ]; then
      echo "  ✗ frontend/src 가 dist 보다 새것이다 — pnpm --dir frontend build 부터 하라"; DRIFT=1; q=1
    fi
    [ "$q" = 0 ] && echo "  ✓ 일치"
  fi
fi

# ── HEAXHub: 앱 SIF 는 크기로 비교한다(내용이 다르면 크기가 거의 항상 다르고, 해시보다 싸다) ──
if want heax; then
  D="$(find_repo HEAXHub)"
  if [ -z "$D" ]; then echo "· HEAXHub 레포 없음 — 건너뜀"; else
    R="$(env_get HEAX_DRIVE_REMOTE "$D/.env")"; R="${R%/}"
    if [ -z "$R" ]; then echo "· HEAX_DRIVE_REMOTE 미설정 — 건너뜀"; else
      echo "── HEAXHub 앱 SIF ($R/latest)"
      # ⚠ 구역별 플래그를 쓴다. 포털·KooRemapper 는 q/k 로 자기 구역만 판정하는데 여기만
      # 전역 DRIFT 를 봤다 — 앞 구역이 하나라도 어긋나면 이 구역은 '✓ 일치'도 '✗'도 없이
      # 헤더만 남는다. 읽는 사람은 "검사하고 통과한 것"과 "검사를 안 한 것"을 구분할 수
      # 없다. 검사기가 판정을 안 보여주는 것은 이 스크립트가 막으려던 증상 그 자체다.
      h=0
      TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
      rclone lsl "$R/latest/" 2>/dev/null | awk '{print $1, $NF}' > "$TMP"
      for f in "$D"/var/sifs/*.sif; do
        [ -e "$f" ] || continue
        b="$(basename "$f")"; ls_="$(stat -c%s "$f")"
        ds="$(awk -v n="$b" '$2==n{print $1}' "$TMP")"
        if [ -z "$ds" ]; then
          echo "  ✗ $b — Drive 에 없다(한 번도 안 올라갔다)"; DRIFT=1; h=1
        elif [ "$ls_" != "$ds" ]; then
          echo "  ✗ $b — 로컬 $ls_ ≠ Drive $ds"; DRIFT=1; h=1
        fi
      done
      _py="$SELF_REPO/backend/.venv/bin/python"; [ -x "$_py" ] || _py=python3
      # 캐시 열쇠 — cae00 허브는 앱 소스를 GitHub(매니페스트 source.ref)에서 받고, 커밋이 바뀌면 sha256(커밋 + 매니페스트 + 틀)을
      # 받은 SIF 의 .sif.hash 와 견준다. 다르면 다시 지으려다(그 박스는 못 짓는다) 실패해 그 회차엔 앱을 띄우지 않는다(HEAXHub
      # integrations_scanner — 빌드 실패는 기동 없음). 크기만 보면 dev 와 Drive 가 같이 낡은 앱을 놓친다(10-25 — StepForge 는 문서 커밋
      # 뒤 다시 안 올림, MaterialTwinWeb 은 GitHub 이 61커밋 뒤). 커밋이 그대로면 cae00 은 열쇠를 다시 재지 않는다 — 매니페스트 · 틀만 바뀐 것은 정보다.
      _kd="$(mktemp -d)"
      rclone copy "$R/latest/" "$_kd/" --include "*.sif.hash" 2>/dev/null || true
      _keys="$("$_py" - "$D" "$_kd" <<'PY' 2>&1
import hashlib, json, re, subprocess, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    print("? 캐시 열쇠를 견주지 못했다 — 이 python 에 PyYAML 이 없다"); sys.exit(0)
hub, kd = Path(sys.argv[1]), Path(sys.argv[2])
same = []   # 매니페스트 · 틀만 바뀐 앱 — 한 줄로 묶는다
def show(rel):  # cae00 이 받을 판(@{u}) — 없으면 작업 트리
    r = subprocess.run(["git", "-C", str(hub), "show", f"@{{u}}:{rel}"], capture_output=True)
    if r.returncode == 0:
        return r.stdout
    p = hub / rel
    return p.read_bytes() if p.is_file() else None
def key(commit, man, tpl):  # HEAXHub integration_sif_builder._hash_inputs 와 같은 꼴
    x = hashlib.sha256(); x.update(commit.encode()); x.update(b"\0")
    x.update(json.dumps(man, sort_keys=True, default=str).encode()); x.update(b"\0"); x.update(tpl)
    return x.hexdigest()
for hf in sorted(kd.glob("*.sif.hash")):
    d = hf.name[:-len(".sif.hash")]
    raw = show(f"integrations/{d}/.portal/manifest.yaml")
    if raw is None:
        continue
    man = yaml.safe_load(raw) or {}
    src = man.get("source") or {}
    tpl = show(f"backend/app/services/sif_templates/{(man.get('build') or {}).get('stack')}.def")
    if src.get("type") != "git" or not src.get("url") or tpl is None:
        continue
    ref = src.get("ref") or "main"
    r = subprocess.run(["git", "ls-remote", src["url"], f"refs/heads/{ref}"], capture_output=True, text=True, timeout=60, cwd=hub)   # 상대 주소(데모의 var/local-demo-repos)는 허브 기준
    head = (r.stdout.split() or [""])[0]
    if not head:
        print(f"? {d} — {ref} 끝을 못 읽었다(열쇠 대조 생략)"); continue
    drive, want = hf.read_text().strip(), key(head, man, tpl)
    if drive == want:
        continue
    lk = hub / "var/sifs" / f"{d}.sif.hash"
    local = lk.read_text().strip() if lk.is_file() else ""
    if local == want:
        print(f"✗ {d} — dev 는 {ref} 끝 {head[:8]} 로 지었는데 Drive 는 옛 판이다 — 올린다(SLUG={d} bash ../DocForge/scripts/drive-push-sif.sh --dry-run)"); continue
    df = hub / "var/sifs" / f"{d}.def"
    m = re.search(r"upstream commit:\s*([0-9a-f]{40})", df.read_text(errors="replace")) if local == drive and df.is_file() else None
    built = m.group(1) if m else ""
    if built == head:
        same.append(d); continue
    ws = hub / "var/integration_workspaces" / d / "upstream"
    if built and subprocess.run(["git", "-C", str(ws), "merge-base", "--is-ancestor", head, built], capture_output=True).returncode == 0:
        print(f"⚠ {d} — Drive SIF 는 {built[:8]} 인데 GitHub {ref} 은 {head[:8]} 에 머물러 있다(앱 리포에 push 안 한 커밋) — cae00 은 GitHub 을 받는다, 앱 리포를 push 하면 열쇠가 맞는다"); continue
    print(f"✗ {d} — Drive SIF{' 는 ' + built[:8] + ' 판인데' if built else ' 의 열쇠가'} {ref} 끝 {head[:8]} 와 맞지 않는다 — cae00 허브가 다시 지으려다 실패해 그 앱을 띄우지 않는다. dev 에서 다시 짓고(redeploy-app.sh --rebuild {d}) 올린다")
if same:
    print(f"· 매니페스트 · 틀만 바뀐 앱 {len(same)}({', '.join(same)}) — 커밋이 그대로라 cae00 은 열쇠를 다시 재지 않고 받은 SIF 로 띄운다")
PY
)"
      rm -rf "$_kd"
      if [ -n "$_keys" ]; then
        printf '%s\n' "$_keys" | sed 's/^/  /'
        printf '%s\n' "$_keys" | grep -q '^✗' && { DRIFT=1; h=1; }
      fi
      # app-data(재료·장비 DB 등)는 tar 로 올라가므로 '가장 최근에 바뀐 DB' 와 tar 시각을 견준다.
      # -L — var/app_data 는 /data 이관 뒤 심링크다(dev · cae00). 안 따라가면 DB 를 하나도 못 찾아 이 검사가 늘 통과였다(10-25 점검).
      # 레지스트리(infra/services.yaml heax-hub data.apps)가 dev → 박스로 보내는 앱(sync: publish-*)의 DB 만 본다 — 박스 고유(mirror)인
      # stepforge · docforge · voicerecorder · risk DB 는 dev 에서 늘 새것이라, 다 보면 이 줄이 늘 떠서 진짜 어긋남을 가린다.
      _pub="$("$_py" - "$SELF_REPO/infra/services.yaml" <<'PY' 2>/dev/null
import sys, yaml
for s in yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["services"]:
    if s.get("name") == "heax-hub":
        for k, v in ((s.get("data") or {}).get("apps") or {}).items():
            if str((v or {}).get("sync", "")).startswith("publish-"):
                print(k)
PY
)"
      if [ -n "$_pub" ]; then
        newest="$(for _a in $_pub; do find -L "$D/var/app_data/$_a" -name '*.db' -printf '%T@\n' 2>/dev/null; done | sort -rn | head -1)"
      else
        newest="$(find -L "$D/var/app_data" -name '*.db' -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"   # 레지스트리를 못 읽으면 전부
      fi
      tar_t="$(rclone lsl "${R%/dist}/app-data/latest/app-data.tar.gz" 2>/dev/null | awk '{print $2" "$3}')"
      if [ -n "$newest" ] && [ -n "$tar_t" ]; then
        tar_e="$(date -d "$tar_t" +%s 2>/dev/null || echo 0)"
        if [ "${newest%.*}" -gt "$tar_e" ]; then
          echo "  ✗ app-data — DB 가 Drive tar($tar_t)보다 새것이다"; DRIFT=1; h=1
        fi
      fi
      [ "$h" = 0 ] && echo "  ✓ 일치"
    fi
  fi
fi

# ── KooRemapper: 프론트 dist 와 솔버 바이너리가 Drive tar 보다 새것인지 ──
if want koorm; then
  D="$(find_repo KooRemapper)"
  if [ -z "$D" ]; then echo "· KooRemapper 레포 없음 — 건너뜀"; else
    R="$(env_get KOORM_DRIVE_REMOTE "$D/platform/.env")"; R="${R%/}"
    if [ -z "$R" ]; then echo "· KOORM_DRIVE_REMOTE 미설정 — 건너뜀"; else
      echo "── KooRemapper ($R/latest)"
      k=0
      for pair in "platform/frontend/dist:koorm-frontend-dist.tar.gz" "platform/backend/bin:koorm-bin.tar.gz"; do
        src="${pair%%:*}"; obj="${pair##*:}"
        # BUILD_INFO.txt 는 tar 에 들지 않는다 — KooRemapper 의 dist-to-drive.sh 가 tar 를 만든 **뒤에** 게시한 박스의 bin/ 에
        # 내려놓아(--exclude=bin/BUILD_INFO.txt) 늘 tar 보다 새것이다. 넣고 재면 게시 직후마다 '올려야 한다' 가 뜬다(10-16 실측).
        newest="$(find "$D/$src" -type f ! -name BUILD_INFO.txt -printf '%T@\n' 2>/dev/null | sort -rn | head -1)"
        t="$(rclone lsl "$R/latest/$obj" 2>/dev/null | awk '{print $2" "$3}')"
        [ -n "$newest" ] && [ -n "$t" ] || continue
        e="$(date -d "$t" +%s 2>/dev/null || echo 0)"
        if [ "${newest%.*}" -gt "$e" ]; then
          echo "  ✗ $src — Drive $obj($t)보다 새것이다"; DRIFT=1; k=1
        fi
      done
      [ "$k" = 0 ] && echo "  ✓ 일치"
    fi
  fi
fi

# ── MX 백서: 그쪽이 짓는 SIF(web · api · wiki)를 크기로 비교한다 ──
# MX 백서는 이미지를 따로 올린다(그 리포의 images-to-drive.sh → MXWP_IMAGES_REMOTE/latest). 이 검사가 이 구역을 안 봐서 web.sif 를 새로
# 구워도 Drive 를 아무도 대조하지 않았다(10-25 — 위키 워커 wiki.sif 가 Drive 에 한 번도 안 올라간 것을 사람이 찾았다). 올리기는 latest/ 를
# 그때 올린 묶음으로 sync 하므로, 안 올린 이미지는 latest/ 에서 빠진다 — 있어야 할 이미지가 없는 것도 드리프트로 친다.
if want mxwp; then
  D="$(find_repo MXWhitePaper)"
  if [ -z "$D" ]; then echo "· MXWhitePaper 레포 없음 — 건너뜀"; else
    R="$(env_get MXWP_IMAGES_REMOTE "$D/.env")"; R="${R%/}"
    if [ -z "$R" ]; then echo "· MXWP_IMAGES_REMOTE 미설정 — 건너뜀"; else
      echo "── MX 백서 이미지 ($R/latest)"
      m=0
      _mx="$(rclone lsl "$R/latest/" 2>/dev/null | awk '{print $1, $NF}')"
      for b in web.sif api.sif wiki.sif; do
        f="$D/infra/apptainer/$b"
        [ -f "$f" ] || continue          # 이 박스에서 굽지 않은 것은 견줄 것이 없다(wiki.sif 는 위키 W3 판부터)
        ls_="$(stat -c%s "$f")"
        ds="$(printf '%s\n' "$_mx" | awk -v n="$b" '$2==n{print $1}')"
        if [ -z "$ds" ]; then
          echo "  ✗ $b — Drive latest/ 에 없다(cae00 이 받을 수 없다)"; DRIFT=1; m=1
        elif [ "$ls_" != "$ds" ]; then
          echo "  ✗ $b — 로컬 $ls_ ≠ Drive $ds"; DRIFT=1; m=1
        fi
      done
      [ "$m" = 0 ] && echo "  ✓ 일치"
    fi
  fi
fi

# ── ste(SmartTwinExplorer): Drive 스테이징의 커밋이 이 박스의 HEAD 와 같은가 ──
# 스테이징은 pack-staging 이 쓴 ste-code.commit 을 품는다. 그것이 HEAD 와 다르면 cae00 은 옛 코드를
# 배포한다(그리고 sha256 은 맞으니 초록이다). 커밋 한 줄만 `rclone cat` 하므로 수 KB 다.
if want ste; then
  STE_DIR="$(find_repo SmartTwinExplorer)"
  if [ -z "$STE_DIR" ] || [ ! -d "$STE_DIR/.git" ]; then
    echo "· ste: SmartTwinExplorer 리포 없음 — 건너뜀"
  else
    _rem="${RCLONE_REMOTE:-}"
    [ -z "$_rem" ] && rclone listremotes 2>/dev/null | grep -qx 'ApptainerImages:' && _rem="ApptainerImages:"
    [ -z "$_rem" ] && _rem="$(rclone listremotes 2>/dev/null | head -1)"
    _drive="$(rclone cat "${_rem}SmartTwinExplorer/staging/ste-code.commit" 2>/dev/null | tr -d '[:space:]')"
    _head="$(git -C "$STE_DIR" rev-parse HEAD 2>/dev/null)"
    if [ -z "$_drive" ]; then
      echo "  ✗ ste 스테이징 — Drive 에 커밋 파일이 없다(${_rem}SmartTwinExplorer/staging) — 올린 적이 없거나 리모트가 다르다"; DRIFT=1
    elif [ "$_drive" != "$_head" ]; then
      echo "  ✗ ste 스테이징 — Drive ${_drive:0:12} ≠ dev HEAD ${_head:0:12} (cae00 은 옛 코드를 배포한다)"; DRIFT=1
    elif [ -n "$(git -C "$STE_DIR" status --porcelain 2>/dev/null)" ]; then
      echo "  ⚠ ste 스테이징 — 커밋은 같지만 dev 작업 트리가 dirty 다(pack-staging 은 clean tree 만 받는다)"
    else
      echo "  ✓ ste 스테이징 ${_head:0:12} 일치"
    fi
  fi
fi

if [ "$DRIFT" = 1 ]; then
  echo
  echo "→ 올려야 한다 — 구역마다 따로(전체 build-all-to-drive.sh 는 쓰지 않는다: 허브 dist-to-drive 가 되돌림 판을 셋만 남기고 지우고,"
  echo "  SHA256SUMS 를 이번에 올린 것만으로 덮고, app-data 가 dev 데이터를 cae00 에 씨앗으로 싣는다 — 10-25 cae00 업데이트 점검):"
  echo "    (포털)        ./infra/scripts/build-all-to-drive.sh portal"
  echo "    (허브 앱 SIF) SLUG=<앱> bash ../DocForge/scripts/drive-push-sif.sh --dry-run   # 본 뒤 --dry-run 없이 — 목록을 합쳐 맨 끝에 올린다"
  echo "    (app-data)    올리지 않는다 — 꼭 필요하면 HEAX_BACKUP_EXCLUDE=\"doc_forge step_forge voice_recorder\" 로(dev 의 DB · 작업 · 업로드가 씨앗으로 간다)"
  echo "    (KooRemapper) cd \$KooRemapper && bash platform/infra/scripts/dist-to-drive.sh"
  echo "    (MX 백서)     cd \$MXWhitePaper && ./infra/scripts/images-to-drive.sh   # web · api · wiki 를 한 묶음으로(그쪽 637a34f 부터)"
  echo "    (ste)         ./infra/scripts/build-all-to-drive.sh ste   # pack-staging + push-to-drive"
  exit 1
fi
echo "✓ Drive 가 이 박스의 아티팩트와 일치한다"
