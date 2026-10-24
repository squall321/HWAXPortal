# update-all 1g2 — infra/.env 의 CHAT_LLM_* 를 HEAXHub/.env 의 APPTAINERENV_CHAT_LLM_* 로 맞추는가(허브 앱도 그림을 읽는 챗 서버를 받게)
"""왜 — 허브 런처는 HEAX_APP_LLM_*(RA 의 GLM)만 앱에 넘긴다. 그림을 읽는 챗 서버(stcx Qwen, CHAT_LLM_*)는 3.5c 가 에이전트 서버로만 맞춰
허브 앱(DocForge 의 그림 판독)은 받지 못했다(CL-D10). 허브 .env 의 `APPTAINERENV_<이름>=` 줄은 이름 그대로 앱 컨테이너로 간다 — 1g2 가 맞춘다.

  · 3.5c 와 같은 규칙 — 키가 없으면 ○ · 빈 값이면 끔 · 지운 줄은 1g2 가 적었던 값일 때만 끔 · 모양 · 모델 검사 · 키는 화면에 안 냄.
  · 허브 .env 의 다른 줄(HEAX_APP_LLM_* 등)은 그대로 · 파일 권한도 그대로. 허브(.env)가 없으면 만들지 않고 ○.

update-all 원문의 구획과 도우미를 그대로 임시 포털에서 돌린다(test_update_all_chat_llm 의 3.5c 와 같은 방식).
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "infra" / "scripts"
UA = (SCRIPTS / "update-all.sh").read_text(encoding="utf-8")
URL = "http://127.0.0.1:18700/v1"
ON = f"CHAT_LLM_BASE_URL={URL}\nCHAT_LLM_MODEL=qwen3.8-flash-next\n"


def _region(start: str, end: str) -> str:
    assert start in UA, f"`{start}` 가 없다"
    i = UA.index(start)
    return UA[i:UA.index(end, i)]


class _Box:
    def __init__(self, tmp: Path):
        self.tmp = tmp.resolve()
        self.repo = self.tmp / "HWAXPortal"
        (self.repo / "infra/scripts/lib").mkdir(parents=True)
        shutil.copy(SCRIPTS / "lib/skip-ledger.sh", self.repo / "infra/scripts/lib/skip-ledger.sh")
        self.heax = self.tmp / "HEAXHub"
        self.heax.mkdir()
        self.heax_env = self.heax / ".env"
        self.heax_env.write_text("HEAX_APP_LLM_BASE_URL=http://glm/v1\nHEAX_APP_LLM_API_KEY=glm-key\n", encoding="utf-8")
        self.heax_env.chmod(0o600)
        self.ledger = self.tmp / "ledger"
        self.ledger.write_text("")
        self.rec = self.repo / "infra/.state/heax-chat-llm.url"

    def run(self, infra_env: str, heax_dir: str | None = None) -> str:
        (self.repo / "infra/.env").write_text(infra_env, encoding="utf-8")
        helpers = "\n".join([_region("_envfile_value() {", "\n}\n") + "\n}",
                             _region("_ra_envv() {", "\n"),
                             _region("_upsert_kv() {", "\n}\n") + "\n}"])
        body = _region("# ── 1g2) 허브 앱 챗 LLM", "# ── 1g2 끝")
        assert "/home/" not in body, "구획에 실물 경로가 박혀 있다"
        script = "\n".join([
            "set -uo pipefail", f'cd "{self.tmp}"', f'SELF_REPO="{self.repo}"',
            f'HEAX_DIR="{self.heax if heax_dir is None else heax_dir}"',
            'hr() { echo "HR:$*"; }; ok() { echo "OK:$*"; }; bad() { echo "BAD:$*"; }; fail() { echo "FAIL:$*"; FAIL=1; }',
            f'export HWAX_SKIP_LEDGER="{self.ledger}"', f'. "{self.repo}/infra/scripts/lib/skip-ledger.sh"',
            helpers, body, "echo END",
        ])
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp), "LANG": "C.UTF-8"}
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60, env=env)
        assert "END" in r.stdout, r.stdout + r.stderr
        assert "unbound variable" not in r.stderr and "command not found" not in r.stderr, r.stderr
        return r.stdout + r.stderr

    def hub(self, key: str) -> str | None:
        for ln in reversed(self.heax_env.read_text(encoding="utf-8").splitlines()):
            if ln.startswith(f"{key}="):
                return ln.split("=", 1)[1]
        return None


@pytest.fixture()
def box(tmp_path):
    return _Box(tmp_path)


def _tagged(out: str, tag: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(tag)]


def test_적으면_허브_env_에_세_줄을_맞추고_기록하며_다른_줄과_권한은_그대로(box):
    out = box.run(ON + "CHAT_LLM_API_KEY=s3cr3t-chat-key\n")
    assert box.hub("APPTAINERENV_CHAT_LLM_BASE_URL") == URL and box.hub("APPTAINERENV_CHAT_LLM_MODEL") == "qwen3.8-flash-next"
    assert box.hub("APPTAINERENV_CHAT_LLM_API_KEY") == "s3cr3t-chat-key"
    assert box.hub("HEAX_APP_LLM_BASE_URL") == "http://glm/v1" and box.hub("HEAX_APP_LLM_API_KEY") == "glm-key", "GLM 줄은 그대로"
    assert oct(box.heax_env.stat().st_mode & 0o777) == "0o600", "비밀이 든 허브 .env 의 권한을 바꾸지 않는다"
    assert box.rec.read_text().strip() == URL and oct(box.rec.stat().st_mode & 0o777) == "0o600"
    assert any("허브 앱 챗 LLM:" in ln for ln in _tagged(out, "OK:")), out
    assert "s3cr3t-chat-key" not in out, "키가 화면에 찍혔다"
    box.run(ON)
    assert box.heax_env.read_text().count("APPTAINERENV_CHAT_LLM_BASE_URL=") == 1, "다시 돌려도 줄이 늘지 않는다"


def test_infra_env_에_없으면_안_켠_기능으로_남기고_사람이_적은_값은_그대로다(box):
    box.heax_env.write_text(box.heax_env.read_text() + "APPTAINERENV_CHAT_LLM_BASE_URL=http://hand:1/v1\n")
    out = box.run("OTHER=1\n")
    assert not _tagged(out, "OK:") and not _tagged(out, "FAIL:"), out
    assert box.ledger.read_text().startswith("허브 앱 챗 LLM\t")
    assert box.hub("APPTAINERENV_CHAT_LLM_BASE_URL") == "http://hand:1/v1"


def test_빈_값이면_끄고_줄을_지우면_1g2_가_적었던_값일_때만_끈다(box):
    box.run(ON)
    out = box.run("CHAT_LLM_BASE_URL=\n")
    assert box.hub("APPTAINERENV_CHAT_LLM_BASE_URL") == "" and not box.rec.exists(), out
    assert any("껐다" in ln for ln in _tagged(out, "OK:")), out
    out = box.run("CHAT_LLM_BASE_URL=\n")
    assert any("꺼짐" in ln for ln in _tagged(out, "OK:")), "이미 꺼져 있으면 그렇다고만"
    box.run(ON)
    out = box.run("OTHER=1\n")                                    # 줄을 지웠다 — 1g2 가 적었던 값이다
    assert box.hub("APPTAINERENV_CHAT_LLM_BASE_URL") == "" and not box.rec.exists()
    assert any("줄이 빠졌다" in ln for ln in _tagged(out, "OK:")), out
    box.run(ON)
    box.heax_env.write_text(box.heax_env.read_text().replace(URL, "http://hand:9/v1"))   # 사람이 바꿨다
    box.run("OTHER=1\n")
    assert box.hub("APPTAINERENV_CHAT_LLM_BASE_URL") == "http://hand:9/v1"


@pytest.mark.parametrize("infra", ["CHAT_LLM_BASE_URL=http://u:p@host/v1\nCHAT_LLM_MODEL=q\n",
                                   "CHAT_LLM_BASE_URL=ftp://host/v1\nCHAT_LLM_MODEL=q\n",
                                   "CHAT_LLM_BASE_URL=http://127.0.0.1:18700/v1\n"])
def test_모양이_틀리거나_모델이_없으면_실패하고_바꾸지_않는다(box, infra):
    before = box.heax_env.read_text()
    out = box.run(infra)
    assert _tagged(out, "FAIL:") and box.heax_env.read_text() == before and not box.rec.exists(), out


@pytest.mark.parametrize("which", ["no_repo", "no_env"])
def test_허브가_없으면_만들지_않고_건너뛴다(box, which):
    if which == "no_env":
        box.heax_env.unlink()
        out = box.run(ON)
        assert not box.heax_env.exists(), "허브 .env 를 새로 만들지 않는다"
    else:
        out = box.run(ON, heax_dir="")
    assert not _tagged(out, "OK:") and not _tagged(out, "FAIL:") and not box.rec.exists(), out
    assert box.ledger.read_text().startswith("허브 앱 챗 LLM\t")


def test_1g2_는_비우기_창_밖_2_deploy_all_앞이다():
    """§2 가 허브 .env 를 재기동 지문에 넣는다 — 그 앞에서 바꿔야 같은 실행에서 앱이 새 값을 받는다. 1h~§2 는 비우기 창이라 그 밖(1h 앞)이다."""
    i = UA.index("# ── 1g2) 허브 앱 챗 LLM")
    assert UA.index("# ── 1g)") < i < UA.index("# ── 1h) 리스크 검토 비우기") < UA.index("# ── 2) 전 서비스 배포")
