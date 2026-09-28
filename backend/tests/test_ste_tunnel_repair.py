# ste 터널(15810·15812) — 배포가 세우고, 실패 원인을 둘로 가른다 (2026-09-28)
#
# 증상: cae00 에서 update-all 을 다시 돌려도 "http://127.0.0.1:15812/mcp 에 아무것도 없다" 가 매번 나왔다.
# 뿌리 둘 — ① **배포 경로가 터널을 세우지 않는다**(§6 이 보고만 했다) ② 15812 가 000 인 두 원인
# (로컬 리스너 없음 / 헤드 쪽 연결 거부)을 출력이 가르지 못해 어디를 봐야 하는지 알 수 없었다.
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUN = ROOT / "infra/scripts/install-ste-tunnel.sh"
DOC = (ROOT / "infra/scripts/ste-doctor.sh").read_text(encoding="utf-8")
UPD = (ROOT / "infra/scripts/update-all.sh").read_text(encoding="utf-8")
TUN_SRC = TUN.read_text(encoding="utf-8")


def _fns(names: tuple) -> str:
    """install-ste-tunnel.sh 에서 함수 정의만 떼어 온다 — 스크립트 본문(설치)은 돌리지 않는다."""
    out = []
    for n in names:
        i = TUN_SRC.index(f"{n}() {{")
        out.append(TUN_SRC[i:TUN_SRC.index("\n}\n", i) + 3])
    return "".join(out)


def _sh(script: str, **env) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                          env={"PATH": os.environ["PATH"], "HOME": env.pop("HOME", "/tmp"), **env})


# ── 코드값: 000 을 두 번 찍지 않는다 ────────────────────────────────────────────
def test_code_helper_does_not_double_the_zero():
    """사용자 화면에 '000000' 이 찍혔다 — curl 은 연결 실패에도 -w 로 이미 000 을 찍는데 `|| echo 000` 이 하나 더 붙었다."""
    r = _sh(_fns(("_code",)) + '\n_code http://127.0.0.1:1/nothing')
    assert r.stdout == "000", r.stdout
    for name, src in (("install-ste-tunnel.sh", TUN_SRC), ("ste-doctor.sh", DOC)):
        # 주석에는 그 문구가 '쓰지 말라' 로 남아 있다 — 실행되는 줄만 본다
        code_lines = [l for l in src.split("\n") if not l.lstrip().startswith("#")]
        assert not any("|| echo 000" in l for l in code_lines), name
    assert "_mcp_probe=\"${_mcp_probe:-000}\"" in UPD, "update-all 의 ste 프로브도 같은 규칙"


# ── 옛 손 터널 고르기 — 남의 프로세스를 죽이지 않는다 ────────────────────────────────
def _stray(port_pids: dict, main: str, comm: dict, cmdline: dict) -> str:
    stub = (
        "_port_pids() { case \"$1\" in " +
        " ".join(f'{p}) printf "%s\\n" {" ".join(v) or "\'\'"} ;;' for p, v in port_pids.items()) +
        " *) : ;; esac; }\n"
        f'_unit_mainpid() {{ printf %s "{main}"; }}\n'
        "_pid_comm() { case \"$1\" in " + " ".join(f'{k}) printf %s "{v}" ;;' for k, v in comm.items()) + " esac; }\n"
        "_pid_cmdline() { case \"$1\" in " + " ".join(f'{k}) printf %s "{v}" ;;' for k, v in cmdline.items()) + " esac; }\n"
    )
    r = _sh(_fns(("_stray_pids",)) + "\n" + stub + "\n_stray_pids")
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_stray_picks_only_our_own_ssh_tunnel_and_never_the_unit_itself():
    """포트킬 오살 규율([[restart-kill-port-hazard]]) — LISTEN·그 포트·comm=ssh·`-L 127.0.0.1:1581`·유닛 MainPID 아님, 다섯을 다 만족해야 고른다."""
    ssh_cmd = "ssh -N -F /x -L 127.0.0.1:15810:127.0.0.1:15810 u@h"
    # ① 옛 손 터널 하나가 15810 을 쥐고 있고 유닛은 다른 pid → 그것만 고른다
    assert _stray({15810: ["111"], 15812: []}, "222", {"111": "ssh"}, {"111": ssh_cmd}) == "111"
    # ② 그 pid 가 유닛의 MainPID 면 고르지 않는다(자기 터널을 죽이면 안 된다)
    assert _stray({15810: ["111"], 15812: ["111"]}, "111", {"111": "ssh"}, {"111": ssh_cmd}) == ""
    # ③ ssh 가 아니면 고르지 않는다(그 포트를 쓰는 다른 서비스)
    assert _stray({15810: ["333"], 15812: []}, "222", {"333": "nginx"}, {"333": "nginx: worker"}) == ""
    # ④ ssh 라도 이 터널의 -L 이 아니면 고르지 않는다(남의 포워딩·일반 세션)
    assert _stray({15810: ["444"], 15812: []}, "222", {"444": "ssh"}, {"444": "ssh -L 127.0.0.1:9999:h:9999 u@h"}) == ""
    # ⑤ 두 포트를 같은 pid 가 쥐면 한 번만 나온다
    assert _stray({15810: ["555"], 15812: ["555"]}, "222", {"555": "ssh"}, {"555": ssh_cmd}) == "555"
    # ⑥ 15812 쪽만 쥔 것도 고른다
    assert _stray({15810: [], 15812: ["666"]}, "222", {"666": "ssh"},
                  {"666": "ssh -L 127.0.0.1:15812:127.0.0.1:15812 u@h"}) == "666"


def test_the_kill_is_opt_outable_and_announced():
    assert "STE_TUNNEL_NO_KILL" in TUN_SRC, "손대지 말라고 할 수 있어야 한다"
    assert "ps -o pid,lstart,args -p $_st" in TUN_SRC, "무엇을 죽이는지 보여 준 뒤에 죽인다"


# ── 15812 가 000 인 두 원인을 가른다 ───────────────────────────────────────────
def test_explain_splits_no_listener_from_refused_by_head(tmp_path):
    fns = _fns(("_port_pids", "_port_line", "explain_15812"))
    none = f'{fns}\n_port_pids() {{ : ; }}\n_port_line() {{ : ; }}\njournalctl() {{ : ; }}\nexplain_15812'
    r = _sh(none, HOME=str(tmp_path))
    assert "아무도 듣지 않는다" in r.stdout and "헤드" not in r.stdout.split("아무도 듣지 않는다")[0], r.stdout
    some = f'{fns}\n_port_pids() {{ echo 999; }}\n_port_line() {{ : ; }}\njournalctl() {{ : ; }}\nexplain_15812'
    r = _sh(some, HOME=str(tmp_path))
    assert "포트는 열려 있는데 000" in r.stdout and "헤드에서 127.0.0.1:15812 로 가는 연결이 거부" in r.stdout
    assert "0.0.0.0" in r.stdout, "헤드에서 무엇을 봐야 하는지(listen 주소)를 알려 준다"


def test_doctor_shows_addresses_and_probes_from_the_head_itself():
    """'ste-mcp: active / listen: 1' 만으로는 못 가른다 — 개수는 IPv6 전용 바인드도 1 로 센다. 주소와 헤드 자기 probe 가 필요하다."""
    assert 'grep ":15812 " | tr -s " " | cut -d" " -f4' in DOC, "listen 주소를 그대로 보여 준다"
    assert "헤드 자기 자신 curl /mcp" in DOC, "헤드에서 406/200 이면 터널 문제, 000 이면 서비스 문제 — 이 한 줄이 가른다"
    assert 'grep -c ":15812 "' not in DOC, "개수만 세던 것은 버렸다"
    assert "유닛 MainPID" in DOC and "유닛이 아닌 pid 가 포트를 쥐고 있다" in DOC, "유닛 active 인데 남이 포트를 쥔 상태를 잡는다"


# ── 배포가 터널을 세운다(보고만 하지 않는다) ──────────────────────────────────────
def test_update_all_repairs_the_tunnel_instead_of_only_reporting_it():
    i = UPD.index('hr "2d) ste 터널 정합')
    blk = UPD[i:UPD.index("# ── 3.5)", i)]
    assert 'install-ste-tunnel.sh" --check' in blk, "먼저 읽기 검사 — 정상이면 아무것도 건드리지 않는다"
    assert "STE_TUNNEL_NONINTERACTIVE=1" in blk, "sudo 프롬프트로 갱신을 매달지 않는다"
    assert 'timeout --foreground 240' in blk, "터널 복구가 갱신 전체를 멈추지 않게 상한"
    assert '[ "$_tmode" != teleport ]' in blk and "hwax_skip" in blk, "teleport 가 아닌 박스는 ○ 로 건너뛴다(조용히 넘기지 않는다)"
    assert "fail " in blk, "복구가 실패하면 종료코드가 선다"
    # 순서: 2d 는 게이트웨이 정합(§5)·헬스게이트(§6) 보다 앞이어야 한다 — 그래야 그 둘이 붙은 터널을 본다
    assert UPD.index('hr "2d)') < UPD.index('hr "5)'), "게이트웨이 reconcile 전에 터널이 서야 한다"
    assert UPD.index('hr "2d)') < UPD.index('hr "6)'), "헬스게이트 전에"


def test_update_all_hint_points_at_the_two_remaining_causes():
    assert "0개면 터널이 그 포트를 못 열었다" in UPD and "1개면 헤드에서 127.0.0.1:15812 로 가는 연결이 거부됐다" in UPD


def test_tunnel_unit_forwards_both_ports():
    unit = (ROOT / "infra/systemd/ste-tunnel.service").read_text(encoding="utf-8")
    assert "-L 127.0.0.1:15810:127.0.0.1:15810" in unit and "-L 127.0.0.1:15812:127.0.0.1:15812" in unit
    assert "ExitOnForwardFailure=yes" in unit, "포워딩이 실패하면 살아 있는 척하지 않는다"
