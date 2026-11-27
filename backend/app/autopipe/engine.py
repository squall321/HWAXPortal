# 자동 파이프라인 엔진 한 박자 — 감지 → 판정 → 실행 만들기(AP-D5 대체) → 단계 나아가기(shadow · approve · auto, 한도 · 야간 창) → 끝(portal-api §4)
"""상태는 모두 원장(auto_*)에 있다 — 포털이 다시 떠도 다음 박자가 이어 간다(서비스 신원이라 사람 PAT 를 잃지 않는다). 박자는 한 번에 하나만
돈다(프로세스 안 잠금 + 원장의 잠금 행).

판단 몇 가지(context-notes AP-12 ~ AP-19).
- 규칙은 **켠 뒤에 바뀐** 과제 · 차수에만 돈다(주제의 last_change ≥ 규칙 enabled_at). 처음 켜거나 다시 켤 때 이미 본 모든 과제에 한꺼번에 해석을
  내지 않는다. 판을 고쳐도 같은 (과제, 차수, 지문)에 이미 실행이 있으면(어느 판이든) 다시 만들지 않는다.
- last_change 는 앱이 준 updated_at(없거나 미래면 지금)이다. 조용함(quiet_s)도 그 시각부터 잰다.
- 같은 박자에 여러 차수가 준비되면 오래된 변화부터 실행을 만든다 — 가장 새 입력의 실행이 마지막에 서서 앞 것을 대체한다(AP-D5).
- 제출 답을 잃으면(불통 · 기한) 같은 idem_key 로 다음 박자에 다시 부른다 — 앱이 같은 run_ref 를 돌려준다(계약 §2). 다시 부르기는 한도를 다시
  보지 않는다(이미 낸 제출을 확인하는 것이다).
- 제출 답이 곧바로 done 이면(sync 앱 — 열충격) 상태를 묻지 않고 auto_result 로 간다.
- 막힘(blocked)은 그 실행에서 끝이다 — 입력이 바뀌면 지문이 바뀌어 새 실행이 선다.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta, timezone

import httpx

from app.autopipe import contract as C
from app.autopipe import ra as RA
from app.autopipe import report as R
from app.autopipe import spec as S
from app.autopipe.gateway import AutoGateway, Reply, exposed, resolve_backend
from app.autopipe.store import STEP_ENDED, STEP_LIVE, AutoStore

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
PAGE_MAX = 100              # 원천 하나에서 한 박자에 받는 쪽 상한(200개씩 — 2만 항목)
# 결과를 모르는 실패(앱 불통 · 기한)를 다시 해 보는 박자 수 — 60초 박자면 약 6시간. 앱 점검 한두 시간에 실행이 막힘으로 굳지 않게 넉넉히 둔다
# (막힘은 그 실행의 끝이고, 입력이 바뀌지 않으면 새 실행이 서지 않는다 — context-notes AP-15).
CHECK_RETRY_MAX = 360       # 확인(auto_profiles · auto_check) — 넘으면 막힘
SUBMIT_RETRY_MAX = 360      # 제출 — 같은 idem_key 로 다시. 넘으면 실패(앱에 잡이 섰을 수 있다고 적는다)
DAY_S = 86400
# 다시 확인을 받는 실행 상태(AP-24) — 대체 · 취소된 실행은 사람이 멈추거나 뒤 차수가 대신한 것이라 되살리지 않는다
RECHECK_RUN_STATES = ("running", "awaiting_approval", "planned", "partial", "failed")


def parse_iso(s) -> int | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def night_window(raw: str) -> tuple[int, int] | None:
    """'20-07' → (20, 7). 꼴이 틀리면 None(야간 전용 단계는 내지 않는다 — 닫힌 쪽)."""
    try:
        a, b = (int(x) for x in str(raw or "").split("-"))
    except ValueError:
        return None
    return (a, b) if 0 <= a <= 23 and 0 <= b <= 23 and a != b else None


def in_night(now: int, win: tuple[int, int] | None) -> bool:
    if win is None:
        return False
    h = datetime.fromtimestamp(now, tz=KST).hour
    a, b = win
    return a <= h < b if a < b else (h >= a or h < b)


class Engine:
    def __init__(self, *, settings, store: AutoStore, mint, client: httpx.AsyncClient | None = None, clock=time.time) -> None:
        self.settings = settings
        self.store = store
        self._mint = mint
        self._client = client
        self._own_client = client is None
        self.clock = clock
        self._lock = asyncio.Lock()
        self.holder = uuid.uuid4().hex
        self.last_tick: int | None = None
        self.last_error: str | None = None
        self.ticks = 0
        self.task: asyncio.Task | None = None
        self._gw: AutoGateway | None = None
        self._tmap: dict | None = None
        self._ra_tried: set = set()       # 이 박자에 RA 게시를 해 본 (실행, 단계) — 다시 하기는 다음 박자에
        self._tried: set = set()          # 이 박자에 결과 모름으로 실패한 (실행, 단계) — 같은 박자의 다음 훑기에서 다시 하지 않는다(횟수 = 박자 수)
        self.paused_until: int | None = None   # update-all 이 포털을 내리기 전에 세운 박자 멈춤의 끝(메모리 — 다시 뜨면 풀린다, AP-26)
        self.paused_by: str | None = None

    def now(self) -> int:
        return int(self.clock())

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.settings, "auto_pipeline_enabled", False))

    def gw(self) -> AutoGateway:
        if self._gw is None:
            if self._client is None:
                self._client = httpx.AsyncClient(timeout=httpx.Timeout(130.0, connect=10.0))
            self._gw = AutoGateway(getattr(self.settings, "mcp_gateway_url", None) or "http://127.0.0.1:9110", self._client, self._mint)
        return self._gw

    async def aclose(self) -> None:
        if self._own_client and self._client is not None:
            await self._client.aclose()

    def paused(self) -> bool:
        return self.paused_until is not None and self.now() < self.paused_until

    def health(self) -> dict:
        p = self.paused()
        return {"running": bool(self.task is not None and not self.task.done()), "last_tick": self.last_tick,
                "last_error": self.last_error, "ticks": self.ticks, "paused_until": self.paused_until if p else None,
                "paused_by": self.paused_by if p else None}

    # ── 박자 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    async def tick(self) -> dict:
        if self.paused():
            return {"skipped": "paused", "until": self.paused_until, "by": self.paused_by}
        if self._lock.locked():
            return {"skipped": "busy"}
        async with self._lock:
            now = self.now()
            if not self.store.lock(self.holder, now):
                return {"skipped": "locked"}
            try:
                out = await self._tick(now)
                self.last_error = out.get("error")
            except Exception as exc:  # noqa: BLE001 — 한 박자의 실패가 엔진을 죽이지 않는다
                logger.error("자동 파이프라인 박자 실패", exc_info=True)
                self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                out = {"error": self.last_error}
            finally:
                self.store.unlock(self.holder)
            self.last_tick = now
            self.ticks += 1
            return out

    async def _tick(self, now: int) -> dict:
        out: dict = {"sources": {}, "created": [], "superseded": [], "runs": 0}
        self._ra_tried = set()
        self._tried = set()
        rules = self.store.enabled_rules()
        self._tmap = await self.gw().tools_map(fresh=True)
        if self._tmap is None:
            out["error"] = "게이트웨이 /tools-map 을 읽지 못했다 — 감지 · 새 실행을 건너뛰었다"
        else:
            names = self._names(rules)
            for name, backend in names.items():
                if backend is None:
                    self.store.cursor_error(name, "게이트웨이에 이 원천 앱 백엔드가 없다", now)
                    out["sources"][name] = "no_backend"
                    continue
                out["sources"][backend] = await self._detect(backend, now)
            created, sup = self._create(rules, names, now)
            out["created"], out["superseded"] = created, sup
        profiles: dict = {}
        runs = self.store.open_runs()
        for run in runs:
            if self.paused():               # update-all 이 기다린다 — 실행 하나를 끝낸 자리에서 박자를 접는다(남은 실행은 다음 박자에, AP-26)
                out["paused"] = True
                break
            try:
                await self._advance_run(run["id"], now, profiles)
            except Exception as exc:  # noqa: BLE001 — 실행 하나의 뜻밖의 실패가 다른 실행의 박자를 막지 않는다
                logger.error("자동 파이프라인 실행 %s 나아가기 실패", run["id"], exc_info=True)
                self.store.event(run["id"], now, "engine_error", {"error": f"{type(exc).__name__}: {str(exc)[:200]}"})
                out.setdefault("run_errors", []).append(run["id"])
        out["runs"] = len(runs)
        # 끝난 실행의 RA 게시 다시 하기 — 실행은 닫혀도 확실히 실패하지 않은 게시(pending · drafted)는 박자마다 상한까지 다시 한다
        opened = {r["id"] for r in runs}
        for rid in self.store.ra_retry_runs(RA.ATTEMPTS_MAX):
            if self.paused():
                out["paused"] = True
                break
            if rid in opened:
                continue
            try:
                await self._ra_sweep(rid, now)
            except Exception:  # noqa: BLE001
                logger.error("자동 파이프라인 RA 게시 다시 하기 실패 run=%s", rid, exc_info=True)
        return out

    async def _ra_sweep(self, run_id: str, now: int) -> None:
        run = self.store.get_run(run_id)
        spec = self.store.version_spec(run["rule_id"], run["version_no"]) if run else None
        if spec is None:
            return
        rule = self.store.get_rule(run["rule_id"]) or {}
        steps = {s["step_id"]: s for s in self.store.steps(run_id)}
        for sp in spec["steps"]:
            st = steps.get(sp["id"])
            if sp["kind"] == "report" and st and st["state"] == "done":
                await self._ra_retry(run, spec, rule, sp, st, steps, now)

    def _names(self, rules: list[dict]) -> dict[str, str | None]:
        """원천 앱 이름 → 이 박스의 백엔드 키. 박스 손잡이 AUTO_PIPELINE_SOURCES ∪ 켜진 규칙의 ready_when 머리."""
        raw = [x.strip() for x in str(getattr(self.settings, "auto_pipeline_sources", "") or "").split(",") if x.strip()]
        for r in rules:
            raw += [S.ready_split(e)[0] for e in (r["spec"].get("trigger") or {}).get("ready_when") or []]
        return {n: resolve_backend(n, self._tmap or {}) for n in dict.fromkeys(raw)}

    # ── ① 감지 ───────────────────────────────────────────────────────────────────────────────────────────────────────
    async def _detect(self, backend: str, now: int) -> str:
        cursor = self.store.cursor(backend)
        for _ in range(PAGE_MAX):
            rep = await self.gw().call(backend, "auto_changes", {"since": cursor, "limit": 200}, run="src", step=backend,
                                       corr=f"autopipe:src:{backend}")
            if not rep.ok:
                self.store.cursor_error(backend, f"{rep.error}: {rep.detail}", now)
                return rep.error
            ch = C.changes_ok(rep.data)
            if ch is None:
                self.store.cursor_error(backend, "auto_changes 답의 꼴이 틀렸다 — 커서를 나아가지 않았다", now)
                return "invalid"
            for it in sorted(ch["items"], key=lambda x: x["updated_at"] or ""):
                self._ingest(backend, it, now)
            if ch["complete"]:
                self.store.cursor_ok(backend, ch["next_since"], now)
                return "ok"
            if ch["next_since"] is None or ch["next_since"] == cursor:
                self.store.cursor_error(backend, "complete=false 인데 next_since 가 나아가지 않았다", now)
                return "stuck"
            cursor = ch["next_since"]
        self.store.cursor_error(backend, f"{PAGE_MAX}쪽을 넘겨도 끝나지 않았다 — 커서를 나아가지 않았다", now)
        return "too_many_pages"

    def _ingest(self, backend: str, it: dict, now: int) -> None:
        subj = it["subject"]
        p, r = subj["project"], subj["revision"]
        upd = parse_iso(it.get("updated_at"))
        upd = now if upd is None or upd > now else upd
        qkey = f"?{backend}:{C.sha(subj['refs'] or it)[:20]}"     # 과제 key · 차수를 모를 때의 자리 줄 — 앱의 refs 로 짓는다
        if p is None or r is None:
            # 짐작하지 않는다 — 과제 key · 개발 단계를 모르는 항목은 막힘으로만 보인다(계약 v1.1 §0.1)
            skey = qkey
            ex = self.store.subject(skey)
            fp = C.fingerprint({backend: it["inputs"]})
            self.store.put_subject({"skey": skey, "project": p, "revision": r, "refs": subj["refs"], "inputs": {backend: it["inputs"]},
                                    "fingerprint": fp, "ready": {backend: it["ready"]}, "first_seen": (ex or {}).get("first_seen"),
                                    "last_change": ex["last_change"] if ex and ex["fingerprint"] == fp else upd, "state": "blocked",
                                    "block_reason": "project_key" if p is None else "revision"}, now)
            return
        if self.store.drop_subject(qkey):   # 사람이 개발 단계를 넣는 등으로 풀렸다 — 같은 refs 의 막힘 줄을 걷는다(AP-28)
            logger.info("자동 파이프라인 막힘 줄이 풀렸다 %s → 과제 · 차수 줄", qkey)
        skey = f"{p}\x1f{r}"
        ex = self.store.subject(skey)
        inputs = dict((ex or {}).get("inputs") or {})
        inputs[backend] = it["inputs"]
        ready = dict((ex or {}).get("ready") or {})
        ready[backend] = it["ready"]
        refs = {**((ex or {}).get("refs") or {}), **subj["refs"]}
        fp = C.fingerprint(inputs)
        if ex is None:
            last, state = upd, "waiting_quiet"
        elif ex["fingerprint"] != fp:
            last, state = (upd if upd > ex["last_change"] else now), "waiting_quiet"
        else:
            last, state = ex["last_change"], ex["state"]
        self.store.put_subject({"skey": skey, "project": p, "revision": r, "refs": refs, "inputs": inputs, "fingerprint": fp,
                                "ready": ready, "first_seen": (ex or {}).get("first_seen"), "last_change": last, "state": state,
                                "block_reason": None}, now)

    # ── ②③ 판정 · 실행 만들기 ────────────────────────────────────────────────────────────────────────────────────────
    def _create(self, rules: list[dict], names: dict, now: int) -> tuple[list[str], list[str]]:
        subjects = sorted(self.store.subjects(open_only=True, limit=10000), key=lambda s: (s["last_change"], s["skey"]))
        created, sup = [], []
        for rule in rules:
            spec = rule["spec"]
            trig = spec.get("trigger") or {}
            excl = set((spec.get("scope") or {}).get("exclude") or [])
            enabled_at = rule.get("enabled_at")
            for s in subjects:
                if s["project"] in excl or enabled_at is None or s["last_change"] < enabled_at:
                    continue
                if now < s["last_change"] + int(trig.get("quiet_s") or 1800):
                    continue
                if not all(self._ready_ok(e, s["ready"], names) for e in trig.get("ready_when") or []):
                    continue
                if self.store.has_run(rule_id=rule["id"], project=s["project"], revision=s["revision"], fingerprint=s["fingerprint"]):
                    self.store.set_subject_state(s["skey"], "ready", now)
                    continue
                steps_by = {x["id"]: x for x in spec["steps"]}
                rid = self.store.create_run(rule_id=rule["id"], version_no=rule["latest_version"], subject=s, stage=spec["stage"],
                                            steps=[(sid, steps_by[sid]["kind"]) for sid in S.order(spec["steps"])], now=now)
                if rid is None:
                    continue
                created.append(rid)
                sup += self.store.supersede(rule_id=rule["id"], project=s["project"], new_run=rid, now=now)
                self.store.set_subject_state(s["skey"], "ready", now)
        return created, sup

    @staticmethod
    def _ready_ok(entry: str, ready: dict, names: dict) -> bool:
        app, key = S.ready_split(entry)
        backend = names.get(app)
        return bool(backend and (ready.get(backend) or {}).get(key))

    # ── ④ 단계 나아가기 ──────────────────────────────────────────────────────────────────────────────────────────────
    async def _advance_run(self, run_id: str, now: int, profiles: dict) -> None:
        run = self.store.get_run(run_id)
        spec = self.store.version_spec(run["rule_id"], run["version_no"])
        rule = self.store.get_rule(run["rule_id"]) or {}
        if spec is None:
            self.store.set_run(run_id, now, state="failed", ended_at=now, reason="규칙 판을 찾지 못했다")
            return
        spec_by = {s["id"]: s for s in spec["steps"]}
        order = S.order(spec["steps"])
        for _ in range(len(order) + 2):
            changed = False
            for sid in order:
                run = self.store.get_run(run_id)
                steps = {s["step_id"]: s for s in self.store.steps(run_id)}
                st, sp = steps.get(sid), spec_by.get(sid)
                if st is None or sp is None:
                    continue
                if st["kind"] == "analysis":
                    changed |= await self._analysis(run, spec, sp, st, steps, now, profiles)
                else:
                    changed |= await self._report(run, spec, rule, sp, st, steps, now)
            changed |= self._stage(run_id, spec, now)
            if not changed:
                break
        self._finish(run_id, now)

    def _subject(self, run: dict) -> dict:
        return {"project": run["project"], "revision": run["revision"], "refs": run.get("refs") or {}}

    def _upstream(self, sp: dict, steps: dict) -> dict:
        return {n: steps[n]["result"] for n in sp.get("needs") or [] if n in steps and steps[n]["kind"] == "analysis"
                and steps[n]["state"] == "done" and steps[n].get("result")}

    async def _profiles(self, backend: str, run: dict, profiles: dict) -> tuple[dict | None, Reply | None]:
        if backend not in profiles:
            rep = await self.gw().call(backend, "auto_profiles", {}, run="prof", step=backend, corr=f"autopipe:{run['id'][:8]}")
            profiles[backend] = (C.profiles_ok(rep.data) if rep.ok else None, rep)
        return profiles[backend]

    def _bump(self, run: dict, st: dict, now: int, rep: Reply, limit: int, stop_state: str, why: str) -> bool:
        """결과를 모르는 실패 — 횟수를 올리고 상한이면 stop_state 로 세운다."""
        self._tried.add((run["id"], st["step_id"]))
        n = int(st.get("attempts") or 0) + 1
        if n >= limit:
            self.store.set_step(run["id"], st["step_id"], now, state=stop_state, attempts=n, error=f"{why}: {rep.error} — {rep.detail}"[:500])
            self.store.event(run["id"], now, "step_" + stop_state, {"step": st["step_id"], "why": why, "error": rep.error})
        else:
            self.store.set_step(run["id"], st["step_id"], now, attempts=n, error=f"다시 시도 {n}/{limit} — {rep.error}: {rep.detail}"[:500])
        return False

    def _set(self, run: dict, st: dict, now: int, *, event: str | None = None, **fields) -> bool:
        self.store.set_step(run["id"], st["step_id"], now, **fields)
        if event:
            self.store.event(run["id"], now, event, {"step": st["step_id"], **{k: fields[k] for k in ("state", "error", "verdict", "run_ref")
                                                                                 if fields.get(k) is not None}})
        return True

    async def _analysis(self, run: dict, spec: dict, sp: dict, st: dict, steps: dict, now: int, profiles: dict) -> bool:
        state = st["state"]
        backend = resolve_backend(sp["app"], self._tmap or {}) if self._tmap is not None else None
        if (run["id"], st["step_id"]) in self._tried:
            return False
        if state == "pending":
            if run["state"] != "running":
                return False
            needs = [steps[n] for n in sp.get("needs") or [] if n in steps]
            bad = [n["step_id"] for n in needs if n["state"] in ("failed", "skipped", "cancelled", "blocked")]
            if bad:
                return self._set(run, st, now, event="step_skipped", state="skipped", error=f"upstream_failed:{','.join(bad)}")
            if any(n["state"] != "done" for n in needs):
                return False
            if self._tmap is None:
                return False
            if backend is None:
                return self._set(run, st, now, event="step_blocked", state="blocked",
                                 error=f"app_missing: 게이트웨이에 {sp['app']} 백엔드가 없다")
            prof, rep = await self._profiles(backend, run, profiles)
            if not rep.ok:
                if rep.transient:
                    return self._bump(run, st, now, rep, CHECK_RETRY_MAX, "blocked", "auto_profiles")
                return self._set(run, st, now, event="step_blocked", state="blocked", error=f"auto_profiles {rep.error}: {rep.detail}"[:500])
            if prof is None:
                return self._set(run, st, now, event="step_failed", state="failed", error="envelope_invalid: auto_profiles 답의 꼴이 틀렸다")
            if prof["service_identity"] is False:
                return self._set(run, st, now, event="step_blocked", state="blocked",
                                 error="service_identity: 이 앱은 아직 서비스 신원을 받지 못한다(auto_profiles)")
            p = prof["profiles"].get(sp["profile"])
            if p is None:
                return self._set(run, st, now, event="step_blocked", state="blocked",
                                 error=f"profile_unknown: {sp['profile']} 이 앱의 auto_profiles 에 없다")
            args = {"subject": self._subject(run), "profile": sp["profile"]}
            up = self._upstream(sp, steps)
            if up:
                args["upstream"] = up
            rep = await self.gw().call(backend, "auto_check", args, run=run["id"], step=sp["id"], corr=f"autopipe:{run['id'][:8]}")
            if not rep.ok:
                if rep.transient:
                    return self._bump(run, st, now, rep, CHECK_RETRY_MAX, "blocked", "auto_check")
                if rep.error in ("error_in_success", "not_json"):
                    return self._set(run, st, now, event="step_failed", state="failed", error=f"envelope_invalid: auto_check — {rep.detail}"[:500])
                return self._set(run, st, now, event="step_blocked", state="blocked", error=f"auto_check {rep.error}: {rep.detail}"[:500])
            chk = C.check_ok(rep.data)
            if chk is None:
                return self._set(run, st, now, event="step_failed", state="failed", error="envelope_invalid: auto_check 답의 꼴이 틀렸다")
            chk["profile"] = {"app_version": prof["app_version"], "sync": p["sync"], "cost": p["cost"], "title": p["title"]}
            if not chk["ready"]:
                return self._set(run, st, now, event="step_blocked", state="blocked", check=chk, error=C.missing_reason(chk["missing"]),
                                 attempts=0)
            return self._set(run, st, now, event="step_ready", state="ready", check=chk, error=None, attempts=0)

        if state == "ready":
            if run["stage"] == "shadow" or (run["stage"] == "approve" and not run.get("approved_by")):
                return False
            if run["state"] != "running" and not st.get("idem_key"):
                return False                # 대체 · 취소된 실행 — 아직 내지 않은 단계는 내지 않는다
            if self._tmap is None or backend is None:
                return False
            if not st.get("idem_key"):
                why = self._limit(run, spec, sp, now)
                if why:
                    if st.get("error") != f"waiting: {why}":
                        self.store.set_step(run["id"], sp["id"], now, error=f"waiting: {why}")
                    return False
                fp = C.step_fingerprint(run["fingerprint"], (st.get("check") or {}).get("inputs") or [], self._upstream(sp, steps))
                key = C.idem_key(run["project"], run["revision"], run["rule_id"], run["version_no"], fp, sp["id"])
                self.store.set_step(run["id"], sp["id"], now, idem_key=key, submitted_at=now, error=None)
                self.store.event(run["id"], now, "submit", {"step": sp["id"], "idem_key": key})
                st = {**st, "idem_key": key}
            args = {"subject": self._subject(run), "profile": sp["profile"], "idem_key": st["idem_key"]}
            up = self._upstream(sp, steps)
            if up:
                args["upstream"] = up
            rep = await self.gw().call(backend, "auto_submit", args, run=run["id"], step=sp["id"], corr=f"autopipe:{run['id'][:8]}")
            if not rep.ok:
                if rep.error == "app:not_ready":
                    missing = (rep.data or {}).get("missing") if isinstance((rep.data or {}).get("missing"), list) else []
                    chk = C.check_ok({"ready": False, "missing": missing}) or {"missing": []}
                    return self._set(run, st, now, event="step_blocked", state="blocked", error=C.missing_reason(chk["missing"]))
                if rep.transient:
                    return self._bump(run, st, now, rep, SUBMIT_RETRY_MAX, "failed",
                                      "auto_submit 결과 모름(앱에 잡이 섰을 수 있다 — idem_key 로 앱에서 찾는다)")
                if rep.error in ("permission", "tool_missing"):
                    return self._set(run, st, now, event="step_blocked", state="blocked", error=f"auto_submit {rep.error}: {rep.detail}"[:500])
                if rep.error in ("error_in_success", "not_json"):
                    return self._set(run, st, now, event="step_failed", state="failed", error=f"envelope_invalid: auto_submit — {rep.detail}"[:500])
                return self._set(run, st, now, event="step_failed", state="failed", error=f"auto_submit {rep.error}: {rep.detail}"[:500])
            sub = C.submit_ok(rep.data)
            if sub is None:
                return self._set(run, st, now, event="step_failed", state="failed", error="envelope_invalid: auto_submit 답의 꼴이 틀렸다")
            self.store.event(run["id"], now, "submitted", {"step": sp["id"], "run_ref": sub["run_ref"], "state": sub["state"],
                                                           "created": sub["created"]})
            if sub["state"] == "done":
                self.store.set_step(run["id"], sp["id"], now, run_ref=sub["run_ref"], state="running", attempts=0, polled_at=now,
                                    status={"state": "done"})
                return await self._result(run, sp, {**st, "run_ref": sub["run_ref"]}, now) or True
            if sub["state"] in ("failed", "cancelled"):
                return self._set(run, st, now, event=f"step_{sub['state']}", state=sub["state"], run_ref=sub["run_ref"],
                                 error=f"auto_submit 이 곧바로 {sub['state']} 를 주었다")
            return self._set(run, st, now, state=sub["state"], run_ref=sub["run_ref"], attempts=0, polled_at=now, error=None)

        if state in STEP_LIVE:
            poll = int(getattr(self.settings, "auto_pipeline_poll_s", 120) or 120)
            if now - int(st.get("polled_at") or 0) < poll or self._tmap is None or backend is None:
                return False
            rep = await self.gw().call(backend, "auto_status", {"run_ref": st["run_ref"]}, run=run["id"], step=sp["id"],
                                       corr=f"autopipe:{run['id'][:8]}")
            if not rep.ok:
                if rep.transient or rep.error == "permission":
                    self.store.set_step(run["id"], sp["id"], now, polled_at=now, error=f"auto_status {rep.error}: {rep.detail}"[:500])
                    return False
                if rep.error in ("error_in_success", "not_json"):
                    return self._set(run, st, now, event="step_failed", state="failed", polled_at=now,
                                     error=f"envelope_invalid: auto_status — {rep.detail}"[:500])
                return self._set(run, st, now, event="step_failed", state="failed", polled_at=now, error=f"auto_status {rep.error}: {rep.detail}"[:500])
            stat = C.status_ok(rep.data)
            if stat is None:
                return self._set(run, st, now, event="step_failed", state="failed", polled_at=now, error="envelope_invalid: auto_status 답의 꼴이 틀렸다")
            if stat["state"] == "done":
                self.store.set_step(run["id"], sp["id"], now, polled_at=now, status=stat)
                return await self._result(run, sp, st, now) or True
            if stat["state"] in ("failed", "cancelled"):
                return self._set(run, st, now, event=f"step_{stat['state']}", state=stat["state"], status=stat, polled_at=now,
                                 error=stat.get("detail") or f"앱이 {stat['state']} 라고 했다")
            changed = stat["state"] != state
            self.store.set_step(run["id"], sp["id"], now, state=stat["state"], status=stat, polled_at=now, error=None)
            return changed
        return False

    async def _result(self, run: dict, sp: dict, st: dict, now: int) -> bool:
        backend = resolve_backend(sp["app"], self._tmap or {})
        rep = await self.gw().call(backend, "auto_result", {"run_ref": st["run_ref"]}, run=run["id"], step=sp["id"],
                                   corr=f"autopipe:{run['id'][:8]}")
        if not rep.ok:
            if rep.error == "app:not_done" or rep.transient:
                self.store.set_step(run["id"], sp["id"], now, state="running", error=f"auto_result {rep.error} — 다음 박자에 다시"[:500])
                return False
            if rep.error in ("error_in_success", "not_json"):
                return self._set(run, st, now, event="step_failed", state="failed", error=f"envelope_invalid: auto_result — {rep.detail}"[:500])
            return self._set(run, st, now, event="step_failed", state="failed", error=f"auto_result {rep.error}: {rep.detail}"[:500])
        env, why = C.envelope_ok(rep.data, run_ref=st["run_ref"], project=run["project"], revision=run["revision"], profile=sp["profile"])
        if env is None:
            return self._set(run, st, now, event="step_failed", state="failed", error=f"envelope_invalid: {why}")
        return self._set(run, st, now, event="step_done", state="done", result=env, verdict=env["verdict"], error=None)

    def _limit(self, run: dict, spec: dict, sp: dict, now: int) -> str | None:
        """첫 제출 전에 보는 한도 — 걸리면 까닭(단계는 ready 로 기다린다)."""
        box = int(getattr(self.settings, "auto_pipeline_max_concurrent", 2) or 2)
        if self.store.active_steps() >= box:
            return f"박스 전체 동시 제출 상한 {box}(AUTO_PIPELINE_MAX_CONCURRENT)"
        lim = spec.get("limits") or {}
        if "max_concurrent" in lim and self.store.active_steps(run["rule_id"]) >= lim["max_concurrent"]:
            return f"규칙 동시 상한 {lim['max_concurrent']}"
        if "per_project_per_day" in lim:
            mine = any(s.get("submitted_at") for s in self.store.steps(run["id"]))
            if not mine and self.store.runs_submitted_since(rule_id=run["rule_id"], project=run["project"], since=now - DAY_S) \
                    >= lim["per_project_per_day"]:
                return f"과제당 하루 상한 {lim['per_project_per_day']}(지난 24시간)"
        if sp["id"] in (lim.get("night_only") or []):
            raw = getattr(self.settings, "auto_pipeline_night", "20-07")
            if not in_night(now, night_window(raw)):
                return f"야간 전용 — 창 {raw} KST 밖" if night_window(raw) else f"야간 전용인데 창(AUTO_PIPELINE_NIGHT={raw!r})의 꼴이 틀렸다"
        return None

    async def _report(self, run: dict, spec: dict, rule: dict, sp: dict, st: dict, steps: dict, now: int) -> bool:
        if st["state"] == "done":
            return await self._ra_retry(run, spec, rule, sp, st, steps, now)
        if st["state"] != "pending":
            return False
        if run["stage"] == "shadow":
            return False                    # 그림자 — 낸 해석이 없다(실행이 planned 로 서며 건너뜀으로 닫힌다)
        needs = [steps[n] for n in sp.get("needs") or [] if n in steps]
        if any(n["state"] not in STEP_ENDED for n in needs):
            return False
        if not any(n["state"] == "done" for n in needs):
            return self._set(run, st, now, event="step_skipped", state="skipped", error="no_result: 가리킨 해석이 하나도 끝나지 않았다")
        rendered = self._render(run, spec, rule, sp, steps)
        self._set(run, st, now, event="report_written", state="done", report_md=rendered["md"], error=None)
        cfg = RA.config()
        if cfg["configured"]:
            await self._ra_post(run, sp, rendered, cfg, None, 0, now)
        return True

    def _render(self, run: dict, spec: dict, rule: dict, sp: dict, steps: dict) -> dict:
        sup = self.store.get_run(run["superseded_by"]) if run.get("superseded_by") else None
        prev = None
        if sp["report"] == "revdiff":
            pr = self.store.previous_run(rule_id=run["rule_id"], project=run["project"], revision=run["revision"], before=run["created_at"])
            prev = (pr, self.store.steps(pr["id"])) if pr else None
        return R.render(kind=sp["report"], rule_title=spec["title"], version_no=run["version_no"], run=run, steps=list(steps.values()),
                        spec=spec, needs=list(sp.get("needs") or []), enabled_by=rule.get("enabled_by"),
                        superseded_rev=(sup or {}).get("revision"), prev=prev)

    async def _ra_post(self, run: dict, sp: dict, rendered: dict, cfg: dict, report_id: str | None, attempts: int, now: int) -> None:
        self._ra_tried.add((run["id"], sp["id"]))
        try:
            got = await RA.post(self.settings, cfg, sp["report"], rendered, report_id=report_id)
        except Exception as exc:  # noqa: BLE001 — 게시의 뜻밖의 실패는 그 단계의 RA 칸에만 남긴다(보고서는 원장에 있다)
            logger.warning("자동 파이프라인 RA 게시 실패(%s)", type(exc).__name__)
            got = {"ra_state": "failed", "ra_report_id": report_id, "ra_error": f"ra_error:{type(exc).__name__}"}
        n = attempts + 1
        state = got["ra_state"]
        if state in ("pending", "drafted") and n >= RA.ATTEMPTS_MAX:
            state = "failed"
        self.store.set_step(run["id"], sp["id"], now, ra_state=state, ra_report_id=got["ra_report_id"], ra_error=got["ra_error"], ra_attempts=n)
        self.store.event(run["id"], now, "ra_" + state, {"step": sp["id"], "report_id": got["ra_report_id"], "error": got["ra_error"]})

    async def _ra_retry(self, run, spec, rule, sp, st, steps, now) -> bool:
        if st.get("ra_state") not in ("pending", "drafted") or int(st.get("ra_attempts") or 0) >= RA.ATTEMPTS_MAX \
                or (run["id"], sp["id"]) in self._ra_tried:
            return False
        cfg = RA.config()
        if not cfg["configured"]:
            return False
        await self._ra_post(run, sp, self._render(run, spec, rule, sp, steps), cfg, st.get("ra_report_id"), int(st.get("ra_attempts") or 0), now)
        return False

    def _stage(self, run_id: str, spec: dict, now: int) -> bool:
        """shadow 는 확인이 끝나면 planned, approve 는 확인이 끝나면 awaiting_approval(낼 것이 없으면 그대로 끝으로)."""
        run = self.store.get_run(run_id)
        if run["state"] != "running" or run["stage"] == "auto" or run.get("approved_by"):
            return False
        steps = self.store.steps(run_id)
        by = {s["step_id"]: s for s in steps}
        spec_by = {s["id"]: s for s in spec["steps"]}
        analyses = [s for s in steps if s["kind"] == "analysis"]

        def checkable(s: dict) -> bool:
            return s["state"] == "pending" and all(by[n]["state"] == "done" for n in spec_by[s["step_id"]].get("needs") or [] if n in by)
        if any(checkable(s) for s in analyses):
            return False
        waiting = [s for s in analyses if s["state"] == "pending"]          # 앞 해석의 결과를 기다린다(그림자 · 승인 전에는 오지 않는다)
        ready = [s for s in analyses if s["state"] == "ready"]
        if run["stage"] == "shadow":
            for s in waiting:
                ups = ",".join(spec_by[s["step_id"]].get("needs") or [])
                self.store.set_step(run_id, s["step_id"], now, error=f"그림자 — 앞 해석({ups})의 결과가 있어야 확인한다")
            for s in steps:
                if s["kind"] == "report" and s["state"] == "pending":
                    self.store.set_step(run_id, s["step_id"], now, state="skipped", error="shadow: 그림자 실행은 보고서를 쓰지 않는다")
            plan = [{"step": s["step_id"], "app": spec_by[s["step_id"]]["app"], "profile": spec_by[s["step_id"]]["profile"],
                     **{k: ((s.get("check") or {}).get("profile") or {}).get(k) for k in ("cost", "sync")}} for s in ready]
            self.store.set_run(run_id, now, state="planned", ended_at=now,
                               reason=f"그림자 — 냈을 해석 {len(ready)} · 막힘 {sum(s['state'] == 'blocked' for s in analyses)}")
            self.store.event(run_id, now, "planned", {"would_submit": plan, "waiting": [s["step_id"] for s in waiting]})
            return True
        if ready:                           # 낼 것이 없으면(모두 막힘 · 건너뜀) 승인을 묻지 않고 보고서 · 끝으로 간다
            self.store.set_run(run_id, now, state="awaiting_approval", reason=f"승인을 기다린다 — 낼 해석 {len(ready)}")
            self.store.event(run_id, now, "awaiting_approval", {"ready": [s["step_id"] for s in ready]})
            return True
        return False

    def _finish(self, run_id: str, now: int) -> None:
        run = self.store.get_run(run_id)
        if run["state"] not in ("running", "superseded", "cancelled") or run.get("ended_at"):
            return
        steps = self.store.steps(run_id)
        if any(s["state"] not in STEP_ENDED for s in steps):
            return
        if run["state"] in ("superseded", "cancelled"):
            self.store.set_run(run_id, now, ended_at=now)
            return
        analyses = [s for s in steps if s["kind"] == "analysis"]
        bad = [f"{s['step_id']}={s['state']}" for s in steps if s["state"] != "done"]
        if not bad:
            state = "done"
        elif not any(s["state"] == "done" for s in analyses):
            state = "failed"
        else:
            state = "partial"
        self.store.set_run(run_id, now, state=state, ended_at=now, reason=", ".join(bad)[:400] or None)
        self.store.event(run_id, now, "run_" + state, {"not_done": bad})

    # ── 사람의 손 ─────────────────────────────────────────────────────────────────────────────────────────────────────
    def approve(self, run_id: str, by: str) -> dict | None:
        now = self.now()
        run = self.store.get_run(run_id)
        if run is None or run["state"] != "awaiting_approval":
            return None
        self.store.set_run(run_id, now, state="running", approved_by=by, approved_at=now, reason=None)
        self.store.event(run_id, now, "approved", {"by": by})
        return self.store.get_run(run_id)

    async def cancel(self, run_id: str, by: str) -> dict | None:
        """안 낸 단계는 cancelled. 도는 단계는 앱에 auto_cancel 이 있으면 부르고(엔진이 켜져 있을 때만), 없으면 끝까지 둔다고 알린다."""
        now = self.now()
        run = self.store.get_run(run_id)
        if run is None or run["state"] not in ("running", "awaiting_approval"):
            return None
        spec = self.store.version_spec(run["rule_id"], run["version_no"]) or {"steps": []}
        spec_by = {s["id"]: s for s in spec["steps"]}
        cancelled, live, calls = [], [], {}
        for s in self.store.steps(run_id):
            if s["state"] in ("pending", "ready", "blocked") and not (s["state"] == "ready" and s.get("idem_key")):
                self.store.set_step(run_id, s["step_id"], now, state="cancelled", error=f"cancelled_by:{by}")
                cancelled.append(s["step_id"])
            elif s["state"] in STEP_LIVE or (s["state"] == "ready" and s.get("idem_key")):
                live.append(s["step_id"])
                sp = spec_by.get(s["step_id"]) or {}
                tmap = await self.gw().tools_map() if self.enabled else None
                backend = resolve_backend(sp.get("app") or "", tmap or {}) if tmap else None
                if backend and s.get("run_ref") and exposed(backend, "auto_cancel", tmap):
                    rep = await self.gw().call(backend, "auto_cancel", {"run_ref": s["run_ref"]}, run=run_id, step=s["step_id"],
                                               corr=f"autopipe:{run_id[:8]}")
                    calls[s["step_id"]] = "ok" if rep.ok else f"{rep.error}: {rep.detail}"[:300]
                    continue
                calls[s["step_id"]] = "auto_cancel 없음 — 앱 쪽에서 끝까지 돈다"
        self.store.set_run(run_id, now, state="cancelled", reason=f"사람이 취소했다({by})", **({} if live else {"ended_at": now}))
        self.store.event(run_id, now, "cancelled", {"by": by, "cancelled": cancelled, "live": live, "auto_cancel": calls})
        return {"run_id": run_id, "cancelled": cancelled, "left_running": live, "auto_cancel": calls}

    def recheck(self, run_id: str, by: str, step: str | None = None) -> tuple[dict | None, str | None]:
        """막힌 해석 단계를 같은 입력으로 다시 확인한다(AP-24) — 앱 · 박스 문제(서비스 신원 · 허용 목록 · 공유 볼륨 · 계약 도구)가 풀린 뒤
        사람이 누른다. 막힌 단계와, 그것을 기다리다 건너뛰었거나 그것 없이 쓴 뒤 단계(뒤 해석 · 보고서)를 대기로 되돌리고 실행을 다시 연다.
        다음 박자가 확인부터 다시 한다. 돌려주는 것은 (결과, 거절 까닭) — 까닭 'not_found' 는 404, 그 밖은 409."""
        now = self.now()
        run = self.store.get_run(run_id)
        if run is None:
            return None, "not_found"
        if run["state"] not in RECHECK_RUN_STATES:
            return None, f"이 실행은 {run['state']} 입니다 — 대체되거나 취소된 실행 · 막힘 없이 끝난 실행은 다시 확인하지 않습니다"
        steps = self.store.steps(run_id)
        blocked = [s["step_id"] for s in steps if s["kind"] == "analysis" and s["state"] == "blocked" and not s.get("run_ref")]
        if step:
            if step not in blocked:
                return None, f"단계 {step} 은 막힘이 아닙니다"
            blocked = [step]
        if not blocked:
            return None, "막힌 해석 단계가 없습니다"
        if self.store.latest_run(rule_id=run["rule_id"], project=run["project"]) != run_id:
            return None, "같은 과제에 뒤 실행이 있습니다 — 옛 실행을 되살리지 않습니다(뒤 실행을 보세요)"
        subj = self.store.subject(f"{run['project']}\x1f{run['revision']}")
        if subj is not None and subj["fingerprint"] != run["fingerprint"]:
            return None, "입력이 바뀌었습니다 — 새 입력의 실행이 조용함을 기다린 뒤 따로 섭니다"
        spec = self.store.version_spec(run["rule_id"], run["version_no"]) or {"steps": []}
        needs = {x["id"]: set(x.get("needs") or []) for x in spec["steps"]}
        reset = set(blocked)
        grew = True
        while grew:                         # 막힌 단계를 (거쳐) 기다리는 뒤 단계 — 건너뜀 · 대기는 되돌리고, 그것 없이 쓴 보고서는 다시 쓴다
            grew = False
            for s in steps:
                sid = s["step_id"]
                if sid in reset or not needs.get(sid, set()) & reset:
                    continue
                if s["state"] in ("skipped", "pending") or (s["kind"] == "report" and s["state"] == "done"):
                    reset.add(sid)
                    grew = True
        replaced = []
        for s in steps:
            if s["step_id"] not in reset:
                continue
            fields = {"state": "pending", "error": None, "attempts": 0, "check": None, "idem_key": None, "submitted_at": None,
                      "ended_at": None}
            if s["kind"] == "report":
                if s.get("report_md"):      # 옛 보고서는 사건에 남긴다 — RA 에 이미 올린 것은 RA 에 그대로 있고, 다시 쓴 것은 새 보고서로 올라간다
                    replaced.append({"step": s["step_id"], "ra_report_id": s.get("ra_report_id"), "ra_state": s.get("ra_state"),
                                     "report_md": s["report_md"][:200_000]})
                fields.update(report_md=None, verdict=None, ra_report_id=None, ra_state=None, ra_error=None, ra_attempts=0)
            self.store.set_step(run_id, s["step_id"], now, **fields)
        order = [s["step_id"] for s in steps if s["step_id"] in reset]
        self.store.set_run(run_id, now, state="running", ended_at=None, reason=f"다시 확인 — {by}")
        self.store.event(run_id, now, "recheck", {"by": by, "steps": blocked, "reset": order, "from_state": run["state"],
                                                  "replaced_reports": replaced})
        return {"run_id": run_id, "rechecked": blocked, "reset": order, "stage": run["stage"],
                "approved": bool(run.get("approved_by"))}, None

    async def run_now(self, rule_id: str, project: str, revision: str, by: str) -> tuple[dict | None, str | None]:
        """사람이 이 규칙을 감지한 과제 · 차수 하나에 지금 돌린다(AP-25) — 켠 시각 · 조용함 · 「어느 판이든 같은 지문이면 다시 안 돈다」를
        넘는다. 범위 제외 · ready_when · 단계(stage) · 한도는 그대로 본다. 같은 과제에 도는 실행이 있으면 대체하지 않고 거절한다."""
        now = self.now()
        rule = self.store.get_rule(rule_id)
        if rule is None or rule.get("archived"):
            return None, "not_found"
        spec = rule.get("spec") or {}
        subj = self.store.subject(f"{project}\x1f{revision}")
        if subj is None:
            return None, "감지한 적 없는 과제 · 차수입니다 — 원천 앱이 알려 준(auto_changes) 과제 · 차수만 돌립니다"
        if project in set((spec.get("scope") or {}).get("exclude") or []):
            return None, "이 규칙의 제외 목록에 있는 과제입니다"
        live = self.store.active_run(rule_id=rule_id, project=project)
        if live:
            return None, f"이 과제에 도는 실행이 있습니다({live[:8]}) — 끝나거나 취소한 뒤에 돌립니다"
        ready_when = (spec.get("trigger") or {}).get("ready_when") or []
        if ready_when:
            tmap = await self.gw().tools_map(fresh=True)
            if tmap is None:
                return None, "게이트웨이 /tools-map 을 읽지 못해 준비(ready_when)를 판정하지 못했습니다"
            names = {S.ready_split(e)[0]: resolve_backend(S.ready_split(e)[0], tmap) for e in ready_when}
            unmet = [e for e in ready_when if not self._ready_ok(e, subj["ready"], names)]
            if unmet:
                return None, f"아직 준비되지 않았습니다(ready_when: {', '.join(unmet)})"
        steps_by = {x["id"]: x for x in spec["steps"]}
        rid = self.store.create_run(rule_id=rule_id, version_no=rule["latest_version"], subject=subj, stage=spec["stage"],
                                    steps=[(sid, steps_by[sid]["kind"]) for sid in S.order(spec["steps"])], now=now)
        if rid is None:
            return None, f"이 규칙의 판 {rule['latest_version']} 이 같은 입력으로 이미 돌았습니다 — 다시 돌리려면 새 판을 저장합니다"
        self.store.set_run(rid, now, reason=f"사람이 지금 돌렸다({by})")
        self.store.event(rid, now, "run_now", {"by": by, "rule_enabled": bool(rule.get("enabled"))})
        self.store.set_subject_state(subj["skey"], "ready", now)
        return {"run": self.store.get_run(rid)}, None

    async def quiesce(self, *, ttl_s: int, wait_s: float, by: str) -> dict:
        """update-all 이 포털을 내리기 전에 부른다(AP-26) — 새 박자를 ttl_s 동안 멈추고, 도는 박자가 실행 하나를 끝낸 자리에서 접기를
        wait_s 까지 기다린다. 해석 잡은 앱 쪽에서 계속 돌고 다시 뜬 포털이 이어서 묻는다 — 기다리는 것은 포털의 한 박자(제출 기록 · RA 게시)뿐이다."""
        self.paused_until = self.now() + max(1, int(ttl_s))
        self.paused_by = (by or "update-all")[:80]
        busy = self._lock.locked()
        t0 = time.monotonic()
        idle = True
        if busy:
            try:
                await asyncio.wait_for(self._lock.acquire(), timeout=max(0.0, float(wait_s)))
                self._lock.release()
            except TimeoutError:
                idle = False
        return {"enabled": self.enabled, "paused_until": self.paused_until, "was_busy": busy, "idle": idle,
                "waited_s": round(time.monotonic() - t0, 1)}


def start(app, settings, engine: Engine) -> asyncio.Task | None:
    """켜져 있고 AUTO_PIPELINE_TICK_S > 0 일 때만 박자 작업을 띄운다. 첫 박자는 한 주기 뒤."""
    if not getattr(settings, "auto_pipeline_enabled", False):
        return None
    every = int(getattr(settings, "auto_pipeline_tick_s", 60) or 0)
    if every <= 0:
        return None

    async def loop() -> None:
        while True:
            await asyncio.sleep(every)
            try:
                await engine.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.error("자동 파이프라인 박자 작업 오류", exc_info=True)

    engine.task = asyncio.create_task(loop(), name="autopipe-engine")
    return engine.task


async def stop(engine: Engine | None) -> None:
    if engine is None:
        return
    task, engine.task = engine.task, None
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
    await engine.aclose()
