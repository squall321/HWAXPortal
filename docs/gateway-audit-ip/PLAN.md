# 게이트웨이 감사에 호출 IP 남기기 — 누가(계정) 어디서(IP) 어떤 도구를 불렀나

> 2026-09-29 사용자 요청: "각 mcp 가 어느 ip 에서 호출되었는지 기록을 남길 수는 있어? 계정이랑". 읽기 전용 조사
> (게이트웨이 내부·nginx 경로·내부 호출자·원장 소비처 네 갈래 + 검증 1)를 거쳐 사용자가 정했다 — **게이트웨이만**,
> 보존은 **지금처럼 무기한**(context-notes D-1).

## 무엇을 바꾸나(게이트웨이 리포 하나)

| 무엇 | 어디 |
|---|---|
| 감사 줄에 `ip` 칸 | `_audit` 이 요청 컨텍스트에서 스스로 읽는다(`purpose` 와 같은 방식) — 호출부 23곳은 그대로 |
| 감사 줄에 `via` 칸(들어온 자격) | `gw-token`(내부 에이전트) · `chat`(웹 챗 PAT) · `procedure`(절차 PAT) · `pat`(개인 PAT) — 미들웨어가 싣고 클라이언트 사본은 버린다 |
| 계정 칸 빈 줄 채우기 | `_audit` 이 `caller` 를 안 받으면 요청의 신원을 쓴다(대화 저장·검색 등) · REST 다리는 `sub` 대신 이메일 |
| REST 다리(`/api/`) | MCP 컨텍스트가 없으므로 `request.client` 를 직접 넘긴다 |
| 인증 실패 | `/mcp` 의 401 을 IP·사유(`no-bearer`·`invalid-token`)와 함께 남긴다(계정은 모름) |

## 경로별로 남는 IP

| 경로 | 남는 IP |
|---|---|
| 개인 Claude(토큰 페이지 등록, nginx `/mcp-gw/`) | 사용자 PC 의 IP(nginx 가 넘긴 값을 uvicorn 이 이미 반영) |
| 웹 챗·웹 심의·업로드·절차 | `127.0.0.1` + `via` 로 구분(브라우저 IP 중계는 이번 범위 밖) |
| 박스 안 Claude Code·서버 앱 | `127.0.0.1` + `via=pat` |

## 한계(읽는 쪽이 알아야 한다)
- IP 는 사람이 아니다 — NAT 뒤면 여럿이 한 주소다. cae00 앞에 사내 LB·프록시가 있으면 그 주소가 찍힌다.
- 박스 안에서 게이트웨이로 직접 붙는 프로세스는 X-Forwarded-For 로 아무 주소나 주장할 수 있다(uvicorn 이 127.0.0.1 을
  믿는다). 형식 검사만 한다 — 주소가 아닌 값은 버린다.
- 도구 목록 조회(tools/list)·허브 자체 도구(search_tools 등)는 원래 감사에 안 남는다(이번에도 그대로).
- 과거 줄은 채워지지 않는다.

## 보는 법
`audit.jsonl`(심링크 → `/data/svc/mcp-gateway/audit.jsonl`) 한 줄이 호출 하나다.

```bash
python3 -c 'import json,sys
for l in open(sys.argv[1]):
    r=json.loads(l)
    if "ip" in r: print(r["ts"], r.get("caller","-"), r["ip"], r.get("via","-"), r["tool"], "ok" if r["ok"] else r.get("error",""))' \
  ../HWAXMcpGateway/audit.jsonl | tail -50
```
