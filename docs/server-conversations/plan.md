# 서버 대화 저장소 — Claude(MCP) 심의 ↔ 포털 웹 챗 ↔ GLM 이어가기

작성 2026-07-19. 목표: Claude(MCP)로 돌린 심의의 대화 전개가 포털 웹 챗에도 나타나고,
사용자가 그 화면에서 GLM 으로 이어서 더 대화한 뒤 직접 결론을 끌어내 RA 로 쓸 수 있게 한다.

## 확정 결정(사용자)

- **저장 모델**: 서버 DB 정본 + localStorage 캐시(기기 간 공유 + 오프라인 대비).
- **MCP 쓰기**: 게이트웨이 MCP 에 conversation 저장 도구 신설. PAT 의 sub 로 소유자 귀속.
- **GLM 이어가기**: 같은 대화에 이어서. 심의 로그 위에 GLM 계속 → 사용자가 결론 → RA 저장 버튼.
- **동기화 방향성(양방향)**: 쓰기는 웹·MCP 양쪽이 **같은 서버 DB 에 대칭**으로 append(둘 다 owner_sub 귀속).
  읽기는 **"열 때 최신 로드"** — 대화 목록/대화 진입 시 서버에서 최신을 pull. 화면 열어둔 채의
  실시간 푸시는 범위 밖(순차 흐름: MCP 심의 → 웹 GLM 이어가기 → 결론 → RA). 실시간 푸시로의 확장은
  API 변경 없이 얹을 수 있음 — `messages.seq`(단조 증가)+`updated_at` 을 이미 저장하므로 증분 로드 가능.

## 현재 구조(확인 완료)

- 포털 챗/심의 로그 = **브라우저 localStorage 전용**(`hwax.chat.*`, `hwax.delib.*`). 서버 저장 없음.
- 포털 백엔드는 **이미 SQLite 사용**(`auth/token_store.py` — PAT). → 같은 패턴으로 conversation 테이블 추가 가능(무DB 아님).
- `/agent/chat` 는 SSE 릴레이만(대화 미저장). `ChatContext.tsx` 가 loadConversations/saveConversations 로 localStorage 를 읽고 씀(250ms 디바운스).
- Claude MCP 심의(hwax-deliberate.js)는 Claude Code 안에서 돌아 포털 챗과 분리. RA 저장은 방금 추가(5a0b189).

## 아키텍처

```
Claude(MCP) ──hwax-deliberate──▶ [게이트웨이 save_conversation 도구] ──▶ 포털 backend conversation DB
                                                                              │ (PAT sub = owner)
포털 웹 챗 ◀──GET /agent/conversations──────────────────────────────────────┘
   │  심의 로그가 대화로 보임 → 사용자가 GLM 에게 이어서 질문(같은 conversation_id)
   ▼
[POST /agent/chat with conversation_id] ──GLM 응답을 그 대화에 append(서버 저장)
   │  사용자가 결론 도출 → [RA 저장 버튼] → create_report_draft
```

## 데이터 모델(포털 backend SQLite, token_store 패턴 재사용)

```
conversations(
  id TEXT PK,               -- uuid
  owner_sub TEXT,           -- PAT/세션 principal sub (소유자)
  title TEXT,
  kind TEXT,                -- 'chat' | 'deliberation'
  source TEXT,              -- 'web' | 'mcp'
  created_at, updated_at INTEGER
)
messages(
  id TEXT PK, conversation_id TEXT FK, seq INTEGER,
  role TEXT,                -- 'user'|'assistant'|'system'|'persona'
  persona TEXT NULL,        -- 심의 발언자(라운드 버블)
  round INTEGER NULL,       -- 심의 라운드
  content TEXT,
  meta TEXT NULL,           -- JSON(stance 등)
  ts INTEGER
)
```
소유권: 조회/이어쓰기 모두 owner_sub == 현재 principal 강제(타인 대화 접근 차단).

## REST(포털 backend, 세션쿠키+CSRF 또는 PAT)

- `GET  /agent/conversations`            — 내 대화 목록(메타)
- `POST /agent/conversations`            — 새 대화 생성(수동)
- `GET  /agent/conversations/{id}`       — 메시지 포함 상세(소유자만)
- `POST /agent/conversations/{id}/messages` — 메시지 append
- `DELETE /agent/conversations/{id}`     — 삭제(소유자)
- `POST /agent/chat` 확장: body 에 `conversation_id?` — 있으면 그 대화에 user+assistant 를 서버 저장(GLM 이어가기). history 는 서버 대화에서 구성.

## 게이트웨이 MCP 도구(신설)

- `save_conversation(title, kind, source, messages[])` → 포털 backend `/agent/conversations`(+messages)로 릴레이. PAT 의 sub 로 owner 귀속. 반환 conversation_id.
  - 게이트웨이는 이미 포털 PAT 검증(JWKS)·audit 보유 → 그 위에 이 도구 1개 추가.
  - hwax-deliberate.js 끝(RA 저장 옆)에서 호출 — 라운드별 발언을 messages(role=persona, round, persona, content)로.

## 프론트(서버 정본 + localStorage 캐시)

- `chatStore.ts`: load/save 를 **서버 우선**으로 — 초기엔 localStorage 로 즉시 렌더(플래시 방지), 백그라운드로 서버 fetch 후 병합·갱신. save 는 서버 POST + localStorage 캐시.
- `ChatContext.tsx`: sendMessage 가 conversation_id 를 함께 전송(서버가 그 대화에 append). 새 대화면 서버가 id 발급.
- 심의 페이지: 서버에서 kind='deliberation' 대화를 로드해 DelibView/버블로 렌더. MCP 심의도 여기 나타남.
- 충돌: updated_at 기준 서버 우선(간단). 동시편집은 범위 밖.

## 단계(Phase)

### Phase 1 — backend conversation store + REST ✅
- [x] `backend/app/agent/conv_store.py`(SQLite, token_store 패턴): 스키마 + CRUD + owner 강제. `messages.seq`+`updated_at` 포함(증분 로드 대비).
- [x] `backend/app/config.py`: `conv_store_path`. `backend/app/main.py`: lifespan 에 `app.state.conv_store` 배선.
- [x] `backend/app/agent/routes.py`: conversations REST 5종(GET/POST 목록, GET/POST-messages/DELETE) + /chat 에 conversation_id 저장(user 선저장 + SSE 파싱해 assistant 종료 시 저장).
- [x] 검증: 단위(conv_store 6종) + TestClient 통합(8종) — 생성·append·순서·meta·소유권 격리(타인 404)·/chat 저장·누수 없음. **통과.**

### Phase 2 — 게이트웨이 save_conversation 도구 + 워크플로 연결 ✅
- [x] 게이트웨이 로컬 도구 save_conversation — 호출자 Authorization(포털 PAT)을 그대로 포털에 포워딩 → 포털이 자체 검증, owner_sub=PAT sub(게이트웨이 신원 매핑 없음=위조 불가). GW_TOKEN 경로는 포털 401 → CONV_UNAVAILABLE(비치명적).
- [x] 포털 POST /agent/conversations 에 messages[] 일괄 생성(심의 로그 15~20건 왕복 1회).
- [x] hwax-deliberate.js: RA 저장 옆 save_conversation 호출(user 질문 → 라운드별 persona → assistant 결정문). saveConversation:false 로 끄기 가능. RA 와 동일 폴백.
- [x] 검증(라이브 e2e): 실제 PAT 로 MCP 핸드셰이크 → tools/list 160(로컬 포함) → tools/call → 포털 조회 owner 귀속·persona/round 보존 → GW_TOKEN 폴백 CONV_UNAVAILABLE. **통과.**

### Phase 3 — 프론트 서버 연동(정본+캐시) + GLM 이어가기
- [ ] chatStore 서버 우선 load/save + localStorage 캐시.
- [ ] ChatContext sendMessage 에 conversation_id.
- [ ] 심의 페이지가 서버 대화(MCP 포함) 로드·렌더. GLM 이어 질문 → 같은 대화 append.
- [ ] RA 저장 버튼(대화 → create_report_draft).
- [ ] 검증(e2e): MCP 심의 → 웹 챗에 로그 표시 → GLM 이어 대화 → RA 저장.

## 하위 호환/리스크

- **기존 localStorage 대화**: 삭제 안 함. 1회 마이그레이션(로그인 시 서버에 없으면 업로드) 또는 그대로 캐시로 둠 — Phase 3 에서 결정.
- **cae00 폴백**: 서버 저장 실패해도 챗/심의는 동작(localStorage 캐시로). MCP 심의의 save_conversation 미가용 시 RA 처럼 건너뜀.
- **소유권/PII**: owner_sub 강제로 타인 대화 차단. 대화는 사내 데이터 → 서버 DB(포털 박스)만, 인터넷 X.
- **RA hands-off**: 무관(RA 는 결과 저장만, 대화 저장소는 포털 backend).
- **동시 편집/멀티탭**: 범위 밖(updated_at 최신 우선).
- **백업**: 포털 conversation DB 도 backup-local 대상에 추가(포털 박스 로컬).

## 범위 밖
- 실시간 협업(웹소켓 동기화), 대화 검색/공유 링크, 조직 공유(현재 owner 단위).
