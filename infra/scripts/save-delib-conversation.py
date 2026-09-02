#!/usr/bin/env python3
# 심의 워크플로 결과 JSON 을 포털 대화 저장소에 **원문 그대로** 저장한다 — LLM 없이 REST 로.
#
# 왜 있는가. 워크플로 안의 저장 에이전트는 messages 를 도구 인자로 되받아 적어야 하는데,
# 큰 심의(실측 21석×6R ≈ 수십만자)에서는 (a) 출력 상한으로 통째 실패하거나 (b) 더 나쁘게는
# 모델이 발언을 요약·의역해 넣고 성공 id 를 돌려준다(무음 변조 — 2026-09-02 전사에서 확인).
# 그래서 워크플로는 예산(6만자) 초과 시 저장을 건너뛰고 conversationSkipped 를 반환하며,
# 전문 저장은 이 스크립트가 맡는다. 원문 보장·수 초·재실행 안전(새 대화를 만들 뿐).
#
# 사용:
#   HWAX_PAT=<포털 PAT> ./save-delib-conversation.py <결과.json> [--base http://127.0.0.1:8723]
#   입력은 워크플로 태스크 출력 파일(래퍼 {result:...})이든 result 자체든 모두 받는다.
#   hwax-sim-deliberate 결과(mechanism/simPlan/buildPlan)면 단계마다 대화를 하나씩 만든다.
import argparse
import json
import os
import sys
import urllib.request

ITEM_MAX = 19500      # 서버 ConvMessageIn.content 캡(20000) 안쪽 — "(결정문 n/N)" 머리말 여유
CREATE_MAX = 200      # ConvCreate.messages 상한 — 넘는 분량은 append 로 잇는다


def _req(base: str, pat: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base.rstrip("/") + path, json.dumps(payload).encode(),
        {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _chunks(text: str, label: str):
    text = str(text or "")
    total = (len(text) + ITEM_MAX - 1) // ITEM_MAX
    for i in range(0, len(text), ITEM_MAX):
        n = i // ITEM_MAX + 1
        head = f"({label} {n}/{total})\n" if total > 1 else ""
        yield head + text[i:i + ITEM_MAX]


def _msgs_for(stage: dict, question: str, cont: bool) -> list[dict]:
    msgs = [{"role": "user", "content": ("(이어하기) " if cont else "") + question}]
    labels = stage.get("roundLabels") or []
    for idx, rd in enumerate(stage.get("rounds") or []):
        label = labels[idx] if idx < len(labels) else f"{idx + 1}라운드"
        rno = None
        digits = "".join(c for c in label.split("라운드")[0] if c.isdigit())
        if digits:
            rno = int(digits)
        for o in rd:
            if not isinstance(o, dict):
                continue
            # 발언 원문 — 라운드별 필드를 사람이 읽는 순서로 전개한다(워크플로 readable 과 동일 취지).
            parts = []
            for k, name in (("lens", "관점"), ("reads", "근거 해석"), ("recommendation", "권고"),
                            ("concerns", "우려"), ("concede", "수용"), ("rebut", "반박"),
                            ("deepen", "심화"), ("final_position", "최종 입장"),
                            ("non_negotiable", "양보 불가"), ("vote", "스탠스")):
                v = o.get(k)
                if not v:
                    continue
                body = "\n- ".join(str(x) for x in v) if isinstance(v, list) else str(v)
                parts.append(f"[{name}]\n{body}")
            content = "\n\n".join(parts)
            for chunk in _chunks(content, "발언"):
                msgs.append({"role": "persona", "persona": str(o.get("persona", "?"))[:120],
                             **({"round": rno} if rno is not None else {}), "content": chunk})
    for chunk in _chunks(stage.get("decision") or "", "결정문"):
        msgs.append({"role": "assistant", "content": chunk})
    return msgs


def _save(base: str, pat: str, title: str, msgs: list[dict]) -> str:
    created = _req(base, pat, "/agent/conversations", {
        "title": title[:200], "kind": "deliberation", "source": "mcp",
        "messages": msgs[:CREATE_MAX]})
    cid = created.get("id") or created.get("conversation_id") or ""
    for m in msgs[CREATE_MAX:]:
        _req(base, pat, f"/agent/conversations/{cid}/messages", m)
    return cid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("result_json", help="워크플로 태스크 출력 또는 result JSON 파일")
    ap.add_argument("--base", default=os.environ.get("HWAX_PORTAL_BASE", "http://127.0.0.1:8723"))
    args = ap.parse_args()
    pat = os.environ.get("HWAX_PAT", "")
    if not pat:
        print("HWAX_PAT 환경변수에 포털 PAT 를 넣어라(/auth/pat 로 발급).", file=sys.stderr)
        return 2

    data = json.load(open(args.result_json))
    r = data.get("result", data)
    if isinstance(r, str):
        r = json.loads(r)

    question = str(r.get("question") or "(질문 미상)")
    # 단일 심의(rounds 최상위) 또는 sim 다단(mechanism/simPlan/buildPlan) 양쪽 지원.
    stages = ([("심의", r)] if r.get("rounds") else
              [(t, r[k]) for k, t in (("mechanism", "1단 메커니즘"), ("simPlan", "2단 해석계획"),
                                      ("buildPlan", "3단 구축계획")) if isinstance(r.get(k), dict)])
    if not stages:
        print("결과에서 rounds 를 찾지 못했다 — 입력이 심의 결과인지 확인하라.", file=sys.stderr)
        return 2
    for tag, stage in stages:
        msgs = _msgs_for(stage, question, cont=tag.startswith(("2", "3")))
        cid = _save(args.base, pat, f"{tag} — {question[:60]}", msgs)
        total = sum(len(m["content"]) for m in msgs)
        print(f"  ✓ {tag}: 대화 {cid} — 메시지 {len(msgs)}건 · {total:,}자 (원문 무손실)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
