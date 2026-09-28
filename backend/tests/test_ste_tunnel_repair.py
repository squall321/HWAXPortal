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
    # ③' 명령줄이 **똑같아도** 이름이 ssh 가 아니면 고르지 않는다 — 위 ③ 은 명령줄 검사에 먼저 걸려 이름 규칙을 따로 못 봤다
    #     (변이 실측: comm 검사를 빼도 통과했다). socat·autossh 같은 다른 도구가 같은 문자열을 인자로 가질 수 있다.
    assert _stray({15810: ["777"], 15812: []}, "222", {"777": "socat"},
                  {"777": "socat -L 127.0.0.1:15810:127.0.0.1:15810 TCP:h:15810"}) == ""
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


# ── 진입점 시험 — 진짜 스크립트를 **그 자신의 set -euo pipefail 아래서** 돌린다 ─────────────────────
# 위의 함수 시험들은 함수를 떼어 set -e 없이 돌려서 이것을 못 봤다: `check_ports; _cp=$?` 가 set -e 로 그 자리에서 끝나
# `--check` 의 진단(리스너·원인 분기·옛 터널)이 **한 번도 안 돌았다**(2026-09-28 dev 실측: rc 1 인데 진단 0줄).
import shutil as _shutil
import time as _time


def _sandbox(tmp_path, mode: str, ss_lines: str = "", curl_rule: str = "000", extra_env_line: str = ""):
    """tmp/HWAXPortal/infra/{scripts,systemd} + tmp/SmartTwinExplorer/deploy/transport.env + tmp/home.
    ss·curl·systemctl·journalctl·sudo 는 **절대경로 셈**으로 막는다 — 실 터널·실 유닛을 절대 건드리지 않는다."""
    portal = tmp_path / "HWAXPortal"; (portal / "infra/scripts").mkdir(parents=True); (portal / "infra/systemd").mkdir(parents=True)
    _shutil.copy(TUN, portal / "infra/scripts/install-ste-tunnel.sh")
    _shutil.copy(ROOT / "infra/systemd/ste-tunnel.service", portal / "infra/systemd/ste-tunnel.service")
    ste = tmp_path / "SmartTwinExplorer/deploy"; ste.mkdir(parents=True)
    cfg = tmp_path / "tp_ssh_config"; cfg.write_text("Host *\n")
    (ste / "transport.env").write_text(
        f"TRANSPORT_MODE={mode}\nREMOTE_USER=u\nHEAD_NODE=head\nTP_CLUSTER=example.teleport\nTELEPORT_SSH_CONFIG={cfg}\n{extra_env_line}\n")
    home = tmp_path / "home"; home.mkdir()
    shim = tmp_path / "shim"; shim.mkdir()
    log = tmp_path / "calls.log"
    (shim / "ss").write_text(
        f"#!/usr/bin/env bash\necho \"ss $*\" >> '{log}'\n"
        # 좀비는 cmdline 이 비어 있다 — /proc 파일은 크기가 0 이라 -s 로는 못 본다, 내용을 읽는다
        "alive() { [ -n \"$(tr -d '\\0' < /proc/$1/cmdline 2>/dev/null)\" ]; }\n"
        "case \"$*\" in\n"
        "  *15810*) if [ -n \"${SS_15810_PID:-}\" ]; then alive \"$SS_15810_PID\" && echo \"LISTEN 0 128 127.0.0.1:15810 0.0.0.0:* users:((\\\"ssh\\\",pid=$SS_15810_PID,fd=3))\"; else printf '%s' \"${SS_15810:-}\"; fi ;;\n"
        "  *15812*) printf '%s' \"${SS_15812:-}\" ;;\n"
        "esac\nexit 0\n")
    (shim / "curl").write_text(f"#!/usr/bin/env bash\necho \"curl $*\" >> '{log}'\n{curl_rule}\n")
    (shim / "systemctl").write_text(f"#!/usr/bin/env bash\necho \"systemctl $*\" >> '{log}'\ncase \"$*\" in *MainPID*) echo 0 ;; *is-active*) echo active ;; esac\nexit 0\n")
    (shim / "journalctl").write_text(f"#!/usr/bin/env bash\necho \"journalctl $*\" >> '{log}'\necho 'bind [127.0.0.1]:15810: Address already in use'\n")
    (shim / "sudo").write_text(f"#!/usr/bin/env bash\necho \"SUDO $*\" >> '{log}'\nexit 97\n")
    for f in shim.iterdir(): f.chmod(0o755)
    def run(*args, **env):
        # USER 를 **일부러 안 넘긴다** — cron·systemd 타이머처럼 축소된 환경에서도 set -u 로 죽지 않아야 한다
        e = {"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(home), "XDG_RUNTIME_DIR": str(tmp_path),
             "STE_TUNNEL_NONINTERACTIVE": "1", "SS_15810": ss_lines, "SS_15812": "", **env}
        # 셈이 먼저 잡히는지 단언한 뒤에만 돈다(3라운드 사고: 셈을 잃은 하네스가 실 apptainer 로 dev nginx 를 내렸다)
        guard = subprocess.run(["bash", "-c", "command -v ss curl systemctl journalctl sudo"], capture_output=True, text=True, env=e)
        assert all(line.startswith(str(shim)) for line in guard.stdout.split()), guard.stdout
        r = subprocess.run(["bash", str(portal / "infra/scripts/install-ste-tunnel.sh"), *args], capture_output=True, text=True, timeout=120, env=e)
        return r, (log.read_text() if log.exists() else "")
    return run, home


def test_check_entrypoint_runs_its_diagnosis_under_set_e(tmp_path):
    run, _ = _sandbox(tmp_path, "teleport")
    r, calls = run("--check")
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "유닛 없음" in out and "15812 (MCP) → 000" in out
    assert "아무도 듣지 않는다" in out, ("진단이 실제로 돈다 — set -e 가 check_ports 에서 끝내던 것", out)
    assert "journal:" in out, "유닛 journal 꼬리도 보인다"


def test_check_entrypoint_splits_listener_present_but_refused(tmp_path):
    run, _ = _sandbox(tmp_path, "teleport")
    r, _ = run("--check", SS_15812='LISTEN 0 128 127.0.0.1:15812 0.0.0.0:* users:(("ssh",pid=4242,fd=5))')
    out = r.stdout + r.stderr
    assert r.returncode == 1 and "포트는 열려 있는데 000" in out and "헤드에서 127.0.0.1:15812 로 가는 연결이 거부" in out, out


def test_check_entrypoint_says_direct_boxes_need_no_tunnel(tmp_path):
    """dev 실측: direct 박스인데 '유닛 없음·000·000' 빨강이었다."""
    run, _ = _sandbox(tmp_path, "direct")
    r, calls = run("--check")
    assert r.returncode == 0 and "터널이 필요 없다" in r.stdout, r.stdout + r.stderr
    assert "curl" not in calls, "직결 박스에서는 터널 포트를 찌르지도 않는다"


def test_transport_mode_is_read_with_the_canonical_rule(tmp_path):
    """종전 `_v` 는 첫 줄·주석 미처리라 `TRANSPORT_MODE=teleport  # 운영` 이 'teleport#운영' 으로 읽혀 '모른다' 로 죽었다.
    transport.sh 는 bash 로 소싱해 teleport 로 읽는다 — 정본(마지막 줄 승·주석 제거)과 같아야 한다."""
    run, _ = _sandbox(tmp_path, 'direct  # 처음엔 직결', extra_env_line='TRANSPORT_MODE="teleport"   # 운영 박스로 바꿈')
    r, _ = run("--check")
    out = r.stdout + r.stderr
    assert "터널이 필요 없다" not in out and "유닛 없음" in out, ("마지막 줄(teleport)이 이긴다", out)


def test_install_entrypoint_clears_a_stray_hand_made_tunnel_and_recovers(tmp_path):
    """가장 흔한 뿌리 — 옛 손 터널이 15810 을 쥐면 리포 유닛의 -L 바인드가 실패해(ExitOnForwardFailure) 영원히 재시도하고,
    사람 눈에는 '15810 은 되는데 15812 만 안 된다' 로 보인다. 진짜 프로세스(이름 ssh, cmdline 에 -L 127.0.0.1:15810)를
    띄워 두고, 설치기가 **그것만** 내린 뒤 다시 세우는지 끝까지 본다."""
    fake = tmp_path / "fakebin"; fake.mkdir()
    # comm 이 'ssh' 이고 cmdline 에 이 터널의 -L 이 있는 **무해한 진짜 프로세스**. sleep 을 복사하면 뒤의 -L 인자를 거부하고
    # **스스로 즉시 죽어서** '설치기가 내렸다' 단언이 헛돌았다(첫 판 실측). 인터프리터를 ssh 라는 이름의 링크로 부르면
    # comm 은 링크 이름이 되고, -c 뒤 인자는 sys.argv 로 그대로 cmdline 에 남는다.
    (fake / "ssh").symlink_to(os.path.realpath(_shutil.which("python3")))
    stray = subprocess.Popen([str(fake / "ssh"), "-c", "import time; time.sleep(300)", "-L", "127.0.0.1:15810:127.0.0.1:15810"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    bystander = subprocess.Popen([_shutil.which("sleep"), "300"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        _time.sleep(0.5)
        assert stray.poll() is None and open(f"/proc/{stray.pid}/comm").read().strip() == "ssh", "시험 전제: 옛 터널 흉내가 살아 있다"
        # 셈 curl: 옛 터널이 살아 있는 동안은 15812 가 000, 내려가면 둘 다 정상 — 실물의 인과를 그대로 흉내 낸다
        # ⚠ `kill -0` 으로 가르면 안 된다 — 내려간 옛 터널은 이 시험의 자식이라 **좀비**로 남고, kill -0 은 좀비에도 성공해
        #   셈이 계속 '살아 있다' 고 했다(첫 판 실측). 좀비는 cmdline 이 비어 있다.
        rule = (f'if [ -n "$(tr -d \'\\0\' < /proc/{stray.pid}/cmdline 2>/dev/null)" ]; then case "$*" in *15812*) printf 000 ;; *) printf 200 ;; esac\n'
                f'else case "$*" in *15812*) printf 406 ;; *) printf 200 ;; esac; fi')
        run, _ = _sandbox(tmp_path, "teleport", curl_rule=rule)
        r, calls = run(SS_15810_PID=str(stray.pid))
        out = r.stdout + r.stderr
        stray.wait(timeout=15)
        assert stray.returncode is not None, "옛 손 터널이 내려갔다"
        assert bystander.poll() is None, "남의 프로세스는 건드리지 않는다"
        assert r.returncode == 0 and "옛 터널을 걷어내고 두 포트 확인" in out, out
        assert "SUDO" not in calls, "비대화식이면 sudo 를 부르지 않는다"
        assert "systemctl --user restart ste-tunnel.service" in calls
    finally:
        for pr in (stray, bystander):
            if pr.poll() is None:
                pr.kill()
