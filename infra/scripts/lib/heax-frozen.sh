#!/usr/bin/env bash
# 동결한 허브 앱 SIF 를 deploy-all §2 의 Drive 받기에서 지킨다 — 받기 앞에 쥐고 뒤에 되돌린 뒤 ○ 장부에 사유를 남긴다
#
# 왜 — cae00 은 StepForge 를 운영 노드에서 돌리고(HEAXHub integrations/step_forge/.portal/manifest.local.yaml 로 넘긴다) 이 박스의
# var/sifs/step_forge.sif 는 되돌림용 사본(동결한 판)이다. HEAXHub deploy/apptainer/dist-from-drive.sh 는 Drive 의 앱 SIF 를 받아 하나씩 이름을
# 바꿔 덮고, 앱 하나를 빼는 손잡이가 없다. 11-23 라운드에서 그 사본이 새 판으로 덮였고 사람이 백업에서 되돌렸다.
# 동결 목록은 포털 infra/.env 의 HEAX_FROZEN_SIFS(앱 이름 — var/sifs/<이름>.sif 의 <이름>, 빈칸 · 쉼표로 가른다)다. 셋업 · 쓰임은 docs/cae00-deploy-guide.md.
#
#   hwax_frozen_hold <sif 폴더> <쥘 폴더> <이름…>   받기 앞. SIF 는 하드 링크로 쥔다(복사 없음 — 받기가 새 파일을 이름 바꾸기로 놓으므로 링크가 옛
#                                                  내용을 지킨다), .sif.hash 는 cp -p 사본으로(받기가 제자리에 덮는다). 없던 것은 없었다고 적는다.
#                                                  0 = 쥐었다 · 1 = 못 쥐었다(부르는 쪽은 받지 않는다 — 받으면 덮인다).
#   hwax_frozen_restore <sif 폴더> <쥘 폴더>        받기 뒤(받기가 실패해도). 쥔 것으로 되돌리고, 받기가 바꿨던 앱마다 ○ 를 찍어 장부에 적는다(받은 판이
#                                                  같아 그대로면 말이 없다 — 이미 최신). 다 되돌리면 쥘 폴더를 지운다.
# 끊긴 실행이 쥘 폴더를 남겼으면 다음 hold 가 먼저 되돌린다 — 트랩 없이 끊김을 견딘다. 쥘 폴더는 sif 폴더 아래(같은 파일 시스템 — 링크)에 둔다.
# 되돌린 SIF · 해시는 바뀐 시각(mtime)까지 옛 것이라 허브 재기동 지문(var/sifs/*.sif · *.sif.hash — 큰 SIF 는 크기 · mtime, 작은 해시는 내용)도
# 그대로다. ctime 은 바뀐다(링크를 걸고 이름을 바꿨다 — 지문은 ctime 을 보지 않는다) — 화면의 ○ 줄이 그렇게 말한다.

hwax_frozen_hold() {
  local dir="$1" hold="$2" n f
  shift 2
  [ -d "$hold" ] && hwax_frozen_restore "$dir" "$hold"
  [ -d "$hold" ] && { echo "  ✗ 앞 실행이 쥔 동결 SIF 를 다 되돌리지 못했다 — $hold" >&2; return 1; }
  [ "$#" -gt 0 ] || return 0
  mkdir -p -- "$hold" || return 1
  for n in "$@"; do
    case "$n" in
      ""|.*|*[!A-Za-z0-9._-]*) echo "  ⚠ HEAX_FROZEN_SIFS 의 '$n' 은 앱 이름 꼴이 아니라 버렸다(var/sifs/<이름>.sif 의 <이름>)" >&2; continue ;;
    esac
    f="$dir/$n.sif"
    mkdir -p -- "$hold/$n" || return 1
    if [ -e "$f" ]; then ln -f -- "$f" "$hold/$n/sif" || return 1; else : > "$hold/$n/sif.absent" || return 1; fi
    if [ -e "$f.hash" ]; then cp -p -- "$f.hash" "$hold/$n/hash" || return 1; else : > "$hold/$n/hash.absent" || return 1; fi
  done
  return 0
}

hwax_frozen_restore() {
  local dir="$1" hold="$2" d n f changed ok how
  [ -d "$hold" ] || return 0
  for d in "$hold"/*/; do
    [ -d "$d" ] || continue
    d="${d%/}"; n="$(basename -- "$d")"; f="$dir/$n.sif"; changed=0; ok=1
    if [ -e "$d/sif" ]; then
      if ! [ "$f" -ef "$d/sif" ]; then
        if mv -fT -- "$d/sif" "$f"; then changed=1; else ok=0; fi
      fi
    elif [ -e "$d/sif.absent" ] && [ -e "$f" ]; then
      if rm -f -- "$f"; then changed=1; else ok=0; fi
    fi
    if [ -e "$d/hash" ]; then
      cmp -s -- "$d/hash" "$f.hash" || changed=1
      mv -fT -- "$d/hash" "$f.hash" || ok=0          # 같은 내용이어도 되돌린다 — 받기의 cp -p 가 바뀐 시각을 Drive 것으로 바꿨다
    elif [ -e "$d/hash.absent" ] && [ -e "$f.hash" ]; then
      if rm -f -- "$f.hash"; then changed=1; else ok=0; fi
    fi
    if [ "$ok" != 1 ]; then
      echo "  ✗ 동결 SIF $n 을 되돌리지 못했다 — 쥔 사본이 $d 에 남아 있다(다음 실행이 다시 되돌린다 · 손으로는 그 안의 sif · hash 를 $dir 로 mv)" >&2
      continue
    fi
    if [ "$changed" = 1 ]; then
      # 화면 줄은 충분히 · 장부 줄(끝 요약)은 짧게(cae00 11-24 넘김 3). 같은 §2 에서 HEAXHub 받기가 이 앱에도 「✓ app SIF <이름>.sif → var/sifs/」 를
      # 먼저 찍는다 — 받기 단계의 줄이다(새 판을 놓았다). 그 ✓ 와 이 ○ 가 어긋나 보이지 않게, 그것을 되돌렸다는 것과 바뀐 시각의 결을 함께 말한다 —
      # 쥔 하드 링크를 이름 바꾸기로 되돌리므로 내용 · mtime 은 동결 판 그대로고 그 inode 의 ctime 은 바뀐다(설계대로 — 사용자 결정 11-23, 손잡이는
      # HEAXHub 에 청하지 않았다, docs/leftovers-1121 L21-26). 사람은 sha256 · mtime 으로 확인한다.
      how="동결을 풀 때 — infra/.env 의 HEAX_FROZEN_SIFS 에서 $n 을 빼고 update-all(또는 deploy-all-from-drive.sh heax)을 다시 돌린다"
      printf '  \033[1;35m○\033[0m %s — %s\n      켜려면: %s\n' "허브 앱 SIF $n — 동결" \
        "Drive 받기가 놓은 새 판을 되돌렸다(위 '✓ app SIF $n.sif' 줄은 받기 단계의 것이다) — var/sifs/$n.sif · .sif.hash 의 내용 · mtime 은 동결 판 그대로이고 ctime 은 바뀐다(infra/.env 의 HEAX_FROZEN_SIFS)" \
        "$how"
      hwax_skip_record "허브 앱 SIF $n — 동결" "infra/.env 의 HEAX_FROZEN_SIFS — Drive 의 새 판을 받은 뒤 동결 판으로 되돌렸다(내용 · mtime 그대로)" "$how"
    fi
    rm -rf -- "$d"
  done
  rmdir -- "$hold" 2>/dev/null || true
  return 0
}
