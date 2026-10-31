"""Agent chat endpoints — thin proxy + auth gate + SSE relay.

The portal does NOT run the LLM / LangGraph / MCP fan-out. It:
  1. authenticates the session (get_current_principal) + CSRF,
  2. caps concurrency (a SSE connection holds a worker → Semaphore, 429 over the cap),
  3. audits the call,
  4. relays the remote Agent Server's SSE stream to the browser.

  POST /agent/chat?mode=echo  — dev: no remote needed; emits the §5 SSE contract locally.
  POST /agent/chat            — relay the remote Agent Server stream (Phase 3 wiring).

mode=echo is the single mock boundary: it proves the SSE path end-to-end (FastAPI →
StreamingResponse → nginx buffering-off → fetch+ReadableStream) with no Agent Server.
"""

import asyncio
import codecs
import contextlib
import hashlib
import json
import logging
import re
import os
import shutil
import sqlite3
import uuid
import zipfile
from pathlib import Path
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from urllib.parse import quote

import anyio
import httpx
import jwt
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, StrictBool, StringConstraints, field_validator, model_validator

from app.access.agent_guard import check_chat, filter_experts
from app.access.policy import is_synthetic, login_groups
from app.agent import conv_search
from app.agent.audit import AuditLog
from app.agent.sse import sse_event
from app.auth import ra_sso
from app.auth.errors import AuthError
from app.auth.provider import Principal
from app.config import Settings, chat_pat_ttl_s, get_settings
from app.agent import docforge_delivery as _dfd
from app.agent import pc_upload as _pc
from app.agent import upload as _upload
from app.agent import wiki_send as _wiki
from app.deps import ensure, get_current_principal, principal_pat_or_session, require_csrf

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/agent", tags=["agent"])

# text/event-stream + the headers nginx needs to NOT buffer the stream. proxy_buffering off
# is set in the nginx location too; X-Accel-Buffering is the per-response belt-and-suspenders.
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# 1백만 토큰 창(GLM-5.2 — 1,048,576 토큰)에 들어갈 수 있는 가장 긴 글. 토큰당 4자(ASCII 기준, 한글은 1자 안팎)로 잡은
# 바깥 경계다. 모델 입력이 될 수 있는 글 칸의 상한은 이 값에서 유도한다 — 종전의 이력 한 건 24,000자·메시지 65,536자·
# 이어하기 요약 24,000자·사람 의견 8,000자·도우미 화두 8,192자·대화 한 칸 20,000자는 16K·128K 창 시절 값이라 1M 창에서
# 먼저 묶여, 결정문 하나(13,000~75,000자)가 든 대화와 이어하기를 422 로 막았다(docs/risk-review-redesign D-21).
# 창에 넣을 길이는 창을 아는 쪽(에이전트 서버 이력 예산·엔진)이 정하고 줄였으면 알린다. 여기는 폭주 방지선만 긋는다 —
# 넘으면 자르지 않고 422 로 소리 낸다.
_WINDOW_TOKENS = 1_048_576
_WINDOW_CHARS = _WINDOW_TOKENS * 4


def _history_total(v: list) -> list:
    """이력 합계를 창 하나로 묶는다 — 항목 상한을 창에서 유도하면 160건 × 그 값이 되므로 합계 선이 따로 있어야 한다.
    앞 턴의 조회 근거(evidence)도 같은 합계에 센다 — 근거는 글보다 크기 쉽다."""
    total = sum(len(m.content) + sum(len(e.tool) + len(e.args or "") + len(e.result) for e in (m.evidence or []))
                for m in v)
    if total > _WINDOW_CHARS:
        raise ValueError(f"이력 합계 {total:,}자가 상한 {_WINDOW_CHARS:,}자(1M 토큰 창 하나)를 넘는다 — "
                         "창에 들어갈 수 없는 이력이다. 오래된 대화를 줄여 보내라")
    return v


class ChatHistoryEvidence(BaseModel):
    """앞 턴에서 도구가 조회한 결과 하나 — 화면이 그 턴의 활동 기록(activity)에서 모은다(docs/chat-depth-context CD-D5).
    에이전트 서버가 근거 몫 안에서 그 턴의 물음 뒤에 '시스템 첨부' 로 싣고, 띵킹은 좌석의 세션 맥락([e:N])으로 싣는다."""
    tool: str = Field(min_length=1, max_length=200)
    args: str | None = Field(default=None, max_length=8000)
    result: str = Field(max_length=_WINDOW_CHARS)
    # upload = 사람이 챗 화면에서 파일을 올려 보낸 결과(포털이 대화에 남긴 알림의 근거) — 에이전트 서버가 '조회한 결과' 와 다른 머리로
    # 싣는다(docs/chat-ppt PP-D3). 비면 종전 조회 근거다.
    kind: Literal["upload"] | None = None


# 한 발화에 올리는 그림 — 에이전트 서버 vision.MAX_IMAGES(VISION_MAX_IMAGES 기본 12) · MAX_BYTES(VISION_MAX_BYTES 기본 8MiB)와 같은 수다.
# 넘는 것은 여기서 422 로 소리 낸다(에이전트 서버도 다시 보고 건너뛴 수를 화면에 알린다). base64 는 원본의 4/3 이고 data URL 머리가 붙을 수 있다.
_IMAGES_MAX = 12
_IMAGE_BYTES_MAX = 8 * 1024 * 1024
_IMAGE_B64_MAX = (_IMAGE_BYTES_MAX + 2) // 3 * 4 + 64
# 이력 항목의 그림은 에이전트 서버가 저장한 올린 그림의 주소뿐이다(해시 이름 — 열거할 수 없다). 다른 주소는 받지 않는다.
_ARTIFACT_IMAGE_PAT = r"^/agent/artifacts/[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\.(?:png|jpe?g|gif|webp)$"
_ARTIFACT_IMAGE_RE = re.compile(_ARTIFACT_IMAGE_PAT)
_ArtifactImage = Annotated[str, StringConstraints(pattern=_ARTIFACT_IMAGE_PAT)]


class ChatImage(BaseModel):
    """이 발화에 올린 그림 한 장 — 화면이 긴 변 1,568px 로 줄여 base64 로 싣는다(docs/chat-depth-context T5). 에이전트 서버가 아티팩트로
    저장하고 주소를 'user_images' 사건으로 돌려준다 — 화면은 그 주소를 이력 항목(images)에 남긴다(원본은 남기지 않는다 — 쿼터)."""
    name: str = Field(default="", max_length=260)
    mime: Literal["image/png", "image/jpeg", "image/gif", "image/webp"]
    data: str = Field(min_length=1, max_length=_IMAGE_B64_MAX)


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=_WINDOW_CHARS)  # 항목 상한 — 합계는 _history_total 이 본다(DoS)
    # 그 턴의 조회 근거(어시스턴트 항목) — 없으면 종전 이력과 같다. 건수는 한 턴의 도구 호출 수 위쪽(에이전트 서버 호출 예산보다 넉넉히).
    evidence: list[ChatHistoryEvidence] | None = Field(default=None, max_length=256)
    # 그 발화에 올린 그림의 주소(사람 항목) — 에이전트 서버가 앞 대화의 그림으로 다시 싣는다(챗 · 띵킹 · 심의, T5).
    images: list[_ArtifactImage] | None = Field(default=None, max_length=_IMAGES_MAX)

    def to_agent(self) -> dict:
        """에이전트 서버 /chat 이력 항목 — 근거 · 그림이 있을 때만 그 칸을 싣는다(종전 모양 그대로 · 빈 칸을 늘리지 않는다)."""
        out: dict = {"role": self.role, "content": self.content}
        if self.evidence:
            out["evidence"] = [e.model_dump(exclude_none=True) for e in self.evidence]
        if self.images:
            out["images"] = list(self.images)
        return out


# 좌석 지식카드 검색어(DelibOpts.knowledge_query)의 모양 — 값 하나 600자 · 좌석 키 120자 · 사전 64항목.
# 600·64 는 엔진 _KNOWLEDGE_Q_MAX · _KNOWLEDGE_Q_KEYS_MAX 와 같은 수여야 한다(tests/test_delib_opts_contract.py).
_KnowledgeQ = Annotated[str, StringConstraints(max_length=600)]
_KnowledgeQSeat = Annotated[str, StringConstraints(min_length=1, max_length=120)]
_KnowledgeQBySeat = Annotated[dict[_KnowledgeQSeat, _KnowledgeQ], Field(max_length=64)]


class DelibOpts(BaseModel):
    """심의 손잡이 요청 오버라이드(웹 토글) — 각 필드 None=agent-server env 기본값 유지.
    범위를 여기서 강제(agent-server 도 재클램프)해 신뢰 안 되는 값 유입을 막는다. GLM 리뷰 §5."""
    evidence_prepass: int | None = Field(default=None, ge=0, le=1)
    rebut_quote: int | None = Field(default=None, ge=0, le=1)
    prose_first: int | None = Field(default=None, ge=0, le=1)
    cross_exam: int | None = Field(default=None, ge=0, le=1)
    anchor: int | None = Field(default=None, ge=0, le=1)
    chair_bestof: int | None = Field(default=None, ge=1, le=5)
    chair_cite: int | None = Field(default=None, ge=0, le=1)
    rounds: int | None = Field(default=None, ge=2, le=8)
    # LLM 호출 **1회**의 제한이다(심의 전체 시간이 아니다). 상한은 엔진 DELIB_TIMEOUT_MAX_S **기본값**·프론트
    # chatStore DELIB_TIMEOUT_MAX_S(보내기 전 클램프·입력칸 max)와 같은 수여야 한다(tests/test_delib_timeout_cap_contract.py).
    # 종전 1800 은 20석 넘는 패널이 공유 LLM 에 줄을 서는 시간을 못 담았고, 엔진만 아는 호출자는 여기서 요청 전체가
    # 422 로 떨어졌다. 넘는 값은 지금처럼 422 로 소리 내 막는다(엔진은 제 상한으로 죄고 카드로 알린다).
    timeout_s: float | None = Field(default=None, ge=10, le=14400)
    # 이어하기(사람 개입 스티어링) — 사람 의견 + 이전 심의 요약 + 전문가 재사용(발굴 생략)
    # human_note 상한은 바깥 경계다(창에서 유도 — 종전 8,000) — 좌석에 싣는 길이는 엔진이 정하고(DELIB_HUMAN_NOTE_MAX,
    # 기본 2,000), 잘랐으면 엔진이 카드로 알린다. 엔진 **기본값**이 이 값을 넘으면 안 된다
    # (tests/test_human_note_cap_contract.py, docs/delib-engine-feedback D-7).
    human_note: str | None = Field(default=None, max_length=_WINDOW_CHARS)
    # 불량 환기 — auto(질문에 불량 단어가 있을 때만, 엔진 종전) | off | always. 'VOC 먼저 보기' 에서
    # 사람이 이미 골랐으면 off 로 보낸다(자동 환기가 사람이 뺀 VOC 를 다시 넣지 않게).
    voc: Literal["auto", "off", "always"] | None = None
    # 이어하기에 싣는 이전 결정문·쟁점. 결정문 하나가 13,000~75,000자다 — 종전 24,000 이면 긴 결정문의 이어하기가 422 였고,
    # 프론트는 그 전에 8,000자로 조용히 잘라 보냈다. 좌석에 싣는 길이는 엔진(_SUMMARY_MAX)이 정하고 줄였으면 카드로 알린다.
    continue_summary: str | None = Field(default=None, max_length=_WINDOW_CHARS)
    # 좌석 상한 — 엔진 MAX_REQ_SEATS **기본값**·ExpertPicker·HandoffBrief·RosterEditor 와 같은 값이어야 한다
    # (tests/test_seat_cap_contract.py). 넘으면 422 로 막는다 — 엔진까지 가면 잘려서 사라진다.
    # 엔진은 환경값(DELIB_MAX_SEATS)으로 더 앉힐 수 있지만 그 길은 MCP·리스크 앱 것이다(포털 스키마를
    # 안 거친다) — 웹은 여기 수까지다(docs/delib-engine-feedback D-3).
    personas: list[dict] | None = Field(default=None, max_length=20)
    # ⚠ 아래 넷은 **엔진에 이미 구현돼 있는데 여기 선언이 없어 웹에서만 죽어 있던** 것이다
    #   (2026-09-11 조사). 선언 안 된 키는 model_dump(exclude_none=True) 에서 조용히 사라지고
    #   에러가 안 나므로, 심의는 정상 동작한 것처럼 끝난다. chair_template·free_tools 가 같은
    #   사고를 겪고 아래에 주석으로 남아 있는데 그 옆에서 네 개가 더 새고 있었다.
    #
    # 이전 심의의 양보 불가 조항. 요약에 섞지 않고 따로 넘겨야 승계가 보장된다 —
    # 빠지면 이전 결정이 소리 없이 되돌아간다(엔진 _cont_block 이 매 라운드 프롬프트에 넣는다).
    # 상한은 한 회차가 낼 수 있는 조항 수 — 좌석 상한(20) × 라운드 상한(8). 종전 12 는 수렴 라운드 좌석 20/20 이 조항을 낸
    # 실측에서 8건을 막았다(프론트가 그 전에 12건으로 조용히 잘랐다). 좌석에 싣는 건수는 엔진(_NN_MAX)이 정하고 알린다.
    non_negotiables: list[str] | None = Field(default=None, max_length=160)
    # 1이면 초기 라운드까지만 돌고 사람에게 넘긴다(인간 체크포인트). 결정문 대신 전원 초기
    # 입장이 내려오고, 이어하기 폼으로 의견을 보태면 좌석 재심사가 그 방향의 도메인을 부른다.
    stop_after_round: int | None = Field(default=None, ge=0, le=1)
    # 이어하기 표시 오프셋 — 이전 회차까지 돈 라운드 수. 없으면 회차마다 회의록이
    # '1R 초기입장' 으로 되돌아간다. 엔진이 0~64 로 재클램프한다.
    rounds_so_far: int | None = Field(default=None, ge=0, le=64)
    # 이어하기를 **같은 RA 보고서**에 페이지로 덧붙인다. 없으면 회차마다 새 보고서가 생겨
    # 한 사안이 여러 건으로 흩어진다(MCP 경로는 이미 묶는다).
    append_to_report_id: int | None = Field(default=None, ge=0)
    # 이어하기 좌석 재심사(0=끔). 사람이 이어하기 명단을 직접 고르면 0 — 고른 명단 위에 재심사가
    # 좌석을 몰래 더 얹으면 '고르게 했다'가 거짓이 된다. 미지정이면 엔진 기본(DELIB_RESCREEN).
    rescreen: int | None = Field(default=None, ge=0, le=1)
    # 사용자 지정 도구 — 심의에서 실제 호출돼 정량 근거로 주입(선정 패널에서 선택).
    tools: list[str] | None = Field(default=None, max_length=6)
    # 사용자 지정 앱 — 전문가 자유 조회 범위를 이 앱들로 좁힌다. 도구와 달리 전량 호출이 아니다
    # (도구 하나당 LLM 인자 구성이 붙어, 앱을 20~30개로 펼쳐 호출하면 예산이 터진다).
    apps: list[str] | None = Field(default=None, max_length=3)
    # 결정문 형식(엔진). None=default 유지. agent-server 가 _CHAIR_ITEMS 로 검증·재클램프한다.
    # ⚠ 종전 미선언이라 웹 경로에서 조용히 버려졌다(model_dump 에 안 실림) — 여기서 선언해 수정.
    chair_template: str | None = Field(default=None, max_length=40)
    # 얹을 층(2층 Modifier) — 심의 굴리는 방식 오버레이. agent-server 가 화이트리스트로 재클램프한다.
    modifiers: list[str] | None = Field(default=None, max_length=5)
    # 시뮬 심의(/시뮬심의)에서 1이면 2단(해석 계획) 뒤 3단 구축 계획까지 이어 만든다(구축 계획 유형).
    build_plan: int | None = Field(default=None, ge=0, le=1)
    # 챗 워크스페이스가 정리해 넘긴 원천 근거(도구결과+출처). 심의는 '검증 대상·결론 아님'으로
    # 좌석에 주입한다(요약 아닌 날것) — 핸드오프 P1. agent-server 가 항목 필드를 재클램프한다.
    # 상한은 프론트 handoff.ts EVID_ITEMS·엔진 _EVID_ITEMS 와 같은 값이어야 한다
    # (tests/test_evidence_budget_contract.py). 종전 12 는 문서 한 건도 못 실었고, 40 은 근거 41~49건짜리
    # 패널(S26U 잠재리스크 심사)을 422 로 막았다 — 합계 예산(500,000자 ÷ 건당 ≈4,000자)이 담는 건수에 맞춘다.
    evidence: list[dict] | None = Field(default=None, max_length=120)
    # 웹 리서치 소스 토글(심의) — 켜지 않은 소스는 자유 조회에 바인딩되지 않는다.
    search_sources: list[str] | None = Field(default=None, max_length=4)
    # 자유 조회 — 좌석이 발언 전 읽기 도구를 직접 호출하는 단계의 on/off(엔진 DELIB_FREE_TOOLS).
    # ⚠ 종전 미선언이라 웹 경로에서 조용히 버려졌다(model_dump 에 안 실림) — 여기서 선언해 수정.
    free_tools: int | None = Field(default=None, ge=0, le=1)
    # 자유 조회 1인당 라운드 호출 상한. 엔진이 1~6 으로 재클램프한다(deliberation.py _resolve_opts).
    tool_budget: int | None = Field(default=None, ge=1, le=6)
    # ⚠ 아래 둘은 엔진이 요청 키로 받게 된 날(2026-10-07) 여기 선언이 없었다 — 포털을 거치는 길(웹 · 리스크 앱
    #   러너)에서만 말없이 사라지고 MCP 로는 됐다. 엔진에 새 요청 키가 생기면 tests/test_delib_opts_contract 가 묻는다.
    #
    # 좌석 지식카드 자동 조회를 이 요청만 끈다(0)·켠다(1). None=엔진 기본(DELIB_PERSONA_KNOWLEDGE).
    # 그 시점 자료만으로 다시 심사하는 소급 검증은 꺼야 한다 — 카드는 오늘의 카드다.
    persona_knowledge: int | None = Field(default=None, ge=0, le=1)
    # 봉인 실행(소급 검증) — 1이면 엔진이 심의 도중 바깥에서 자료를 가져오는 길을 한꺼번에 닫고 결정문에 표식을
    # 찍는다(무엇을 닫는지는 엔진이 쥔다 — deliberation._SEALED_CLOSE). 화면에 입구는 없다. 선언해 두는 이유는
    # 하나다 — 누가 보냈을 때 여기서 떨어지면 봉인을 청한 심의가 **열린 채** 돌고 청한 쪽은 봉인된 줄 안다.
    sealed: int | None = Field(default=None, ge=0, le=1)
    # 좌석 지식카드 검색어 — 문자열 하나(전 좌석 공통)이거나 {좌석 키: 검색어, "*": 기본} 사전이다. None=엔진이 화두로 찾는다.
    # 리스크 앱 러너가 변경 요지를 실어 보내는 자리다. 넘는 값은 422 로 소리 내 막는다 — 보내는 쪽이 상한 안으로 만들어 보낸다.
    knowledge_query: _KnowledgeQ | _KnowledgeQBySeat | None = None
    # 보고서 저장 끄기(0)·켜기(1). None=엔진 기본(저장). 쟁점 패널이 패널마다 RA 보고서를 만들지 않게 하려는 자리다 —
    # 여기서 떨어지면 저장을 끈 줄 아는 심의가 보고서를 만든다. 지금은 보내는 곳이 없다(선언만 한다).
    save_report: int | None = Field(default=None, ge=0, le=1)
    # MX 백서 LLM 위키에도 결정문을 남긴다(1). None=엔진 기본(꺼짐). 범위는 그 사람의 소속이다 — 포털이 원장에서 채워 `affiliation`
    # 으로 따로 싣는다(손잡이가 아니라 신원이다). 소속이 없으면 엔진이 후보로 보낸다(docs/mxwp-wiki P8). 화면은 MX 백서 권한이 있을 때만
    # 이 토글을 보인다 — 권한 없는 사람이 보내도 게이트웨이가 위키 도구를 주지 않아 엔진이 '도구가 없다' 고 결정문 끝에 적는다.
    wiki: int | None = Field(default=None, ge=0, le=1)
    # 누가 띄운 심의인가 — 리스크 앱 러너가 편성한 패널(쟁점·옛 흐름)은 "app" 을 싣는다. 엔진의 카드 대조 관문은 '심의가 돌면
    # 절반' 을 사람이 띄운 심의(app 아닌 것)로만 센다(docs/risk-review-redesign M3.md #26). 여기서 떨어지면 표지가 사라져 쟁점
    # 패널도 사람 심의로 세어지고 카드 대조가 며칠 동안 반(4)으로 묶인다. 스스로 밝히는 값이라 검증하지 않는다. None=사람.
    started_by: Literal["human", "app"] | None = None
    # ⚠ 아래 둘은 외부 응답자 심의(docs/risk-claude-engine — 기본 꺼짐, 에이전트 서버 EXTERNAL_LLM_ENABLED=1 에서만 열린다)의 칸이다.
    #   선언이 없던 동안(X-3a 전)은 포털을 거친 외부 선택이 여기서 말없이 떨어져 심의가 GLM 으로 돌았다.
    #   보내는 곳은 리스크 앱(웹 러너 · 그 앱의 MCP risk_start_job 이 연 잡)뿐이다. 포털 화면은 이 선택을 내지 않고(프론트에 입구가
    #   없다), MCP deliberate_start 는 포털을 거치지 않는다(게이트웨이 → 에이전트 서버 advanced.llm).
    #
    # 판단 LLM — glm(이 박스 에이전트 서버의 LLM, None 과 같다) | external(잡 주인이 돌리는 Claude Code 워크플로가 답하고, 좌석은 도구
    # 호출 없이 evidence_only 로 돈다). 받는 두 값 밖은 422 다 — 엔진도 bad_request 로 거절하지만, 포털 손잡이는 받는 값만 받는다.
    llm: Literal["glm", "external"] | None = None
    # 반출 동의 표지 — llm=external 인 심의를 엔진은 이것이 JSON true 일 때만 연다(없거나 false 면 external_consent_required 로 시작하지
    # 않는다). 사람에게 동의를 받고 누가 언제 했는지 적는 것은 부르는 쪽(리스크 앱)의 몫이고, 포털은 받은 그대로 옮기기만 한다.
    # StrictBool 인 까닭 — "true"·1 은 엔진이 동의로 치지 않는 값인데, 포털이 true 로 바꿔 넘기면 동의가 아닌 것을 동의로 세탁한다.
    consent_external: StrictBool | None = None
    # 외부 응답자 과제의 대상 열쇠(docs/risk-claude-engine X-D9) — llm=external 심의(리스크 앱의 쟁점 패널)에서만 엔진이 과제 머리에 싣는다.
    # Claude Code 워크플로는 제가 맡은 잡의 대상 과제만 답하므로, 이것이 떨어지면 쟁점 패널 과제가 답 없이 시간을 넘겨 잡이 external_worker
    # 로 선다. GLM 심의는 엔진이 이 값을 읽지 않는다. 모양은 엔진의 _RISK_TARGET_KEY_RE 와 같다(diff:·snap: + 64자 안의 영숫자·_·-).
    target_key: Annotated[str, StringConstraints(pattern=r"^(?:diff|snap):[0-9A-Za-z][0-9A-Za-z_-]{0,63}$")] | None = None


class ChatDocument(BaseModel):
    """사용자가 붙인 문서 한 건 — 이름과 **추출된 글**만 온다.

    상한은 **프론트 DOC_CHARS_MAX 이상**이어야 한다. 작으면 사용자가 붙일 수 있는 문서를
    여기서 422 로 거절한다 — 종전 200,000(프론트 400,000)이 정확히 그 상태였고, 긴 발표자료를
    붙이면 전송 자체가 실패했다(test_evidence_budget_contract 가 이 역전을 본다).

    여기서 미리 자르지 않는 이유 — 자르는 일은 예산을 아는 엔진이 한다. 엔진은 낱장 경계에서
    가운데를 덜어내고(evidence.fit_document) 무엇이 빠졌는지 밝힌다. 앞에서 잘라 보내면
    발표자료의 결론이 여기서 이미 사라진다."""
    name: str = Field(min_length=1, max_length=260)
    kind: str | None = Field(default=None, max_length=16)
    text: str = Field(min_length=1, max_length=2000000)


# 루틴 입력의 폭주 방지선(docs/analysis-routines R3-design 3.1) — 루틴 변수는 12개까지라(RoutineSpec) 키는 넉넉히 두 배, 길이는 입력 전체를
# JSON 으로 적은 글자 수다. 형 맞추기 · 모르는 키 · 빠진 필수는 실행을 만드는 포털 /routines-api(_coerce)가 422 로 말한다.
_ROUTINE_INPUT_KEYS = 24
_ROUTINE_INPUT_CHARS = 20_000


class RoutineReq(BaseModel):
    """챗 루틴 모드 한 턴(R3-design 3.1) — 새 실행은 {id, version?, inputs, note?}, 이어서 · 다시 붙기는 {run_id}, 끝난 실행의 RA 초안 올리기는
    {run_id, upload_ra: true}(R3-design 8). 에이전트 서버의 실행기가 게이트웨이 routine_run_start 로 실행을 만들거나 잇는다(R3 D1). 모르는 칸은
    422 다 — 칸 이름을 틀리게 보낸 루틴이 조용히 다르게 돌지 않게."""
    model_config = {"extra": "forbid"}

    id: str = Field(default="", max_length=64)
    version: int | None = Field(default=None, ge=1)
    inputs: dict[str, str | int | float | bool | dict | list] = Field(default_factory=dict)
    run_id: str = Field(default="", max_length=64)
    # 사용자가 덧붙인 말 — 실행기가 새 실행의 routine_run_start(note=…)로 원장에 한 번 남기고, 프롬프트는 이어서 · 다시 붙기에서도 원장 값을 쓴다
    # (화면 글 '루틴 이어서: <제목>' 이 덧붙인 말을 덮지 않게). 상한은 포털 RunIn · 게이트웨이 routine_run_start 와 같은 2,000자다.
    note: str = Field(default="", max_length=2000)
    # 끝난 실행의 저장 보고서를 RA 초안으로 올린다(ra.upload 'ask' — 화면의 'RA 초안 올리기'). 바깥에 글을 만드는 동작이라 참거짓만 받는다 —
    # "true" · 1 을 true 로 바꿔 올리지 않는다(DelibOpts.consent_external 과 같은 까닭).
    upload_ra: StrictBool = False

    @field_validator("inputs")
    @classmethod
    def _inputs_cap(cls, v: dict) -> dict:
        if len(v) > _ROUTINE_INPUT_KEYS:
            raise ValueError(f"루틴 입력 {len(v)}개가 상한 {_ROUTINE_INPUT_KEYS}개를 넘는다")
        n = len(json.dumps(v, ensure_ascii=False))
        if n > _ROUTINE_INPUT_CHARS:
            raise ValueError(f"루틴 입력(JSON) {n:,}자가 상한 {_ROUTINE_INPUT_CHARS:,}자를 넘는다")
        return v

    @model_validator(mode="after")
    def _id_or_run_id(self) -> "RoutineReq":
        if not (self.id or self.run_id):
            raise ValueError("루틴 요청에는 id(새 실행)나 run_id(이어서)가 있어야 한다")
        return self

    @model_validator(mode="after")
    def _upload_needs_run_id(self) -> "RoutineReq":
        if self.upload_ra and not self.run_id:
            raise ValueError("upload_ra(RA 초안 올리기)는 끝난 실행의 run_id 와 함께 보낸다 — 새 실행에는 올릴 보고서가 아직 없다")
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=_WINDOW_CHARS)  # 폭주 방지선 — 창 하나(종전 65,536)
    system_id: str | None = Field(default=None, max_length=128)  # sub-page → tool scope (Phase 2)
    # 멀티턴 컨텍스트: 오래된 것→최신 순, 이번 message는 포함하지 않는다(agent-server 계약).
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=160)
    history_total = field_validator("history")(_history_total)
    # 있으면 이 대화(서버 정본)에 user+assistant 를 저장한다. 없으면 저장 안 함(하위호환).
    conversation_id: str | None = Field(default=None, max_length=64)
    # 심의 손잡이 오버라이드 — 심의(/심의) 요청에서만 의미. agent-server 로 그대로 포워딩.
    delib_opts: DelibOpts | None = None
    # 사용자 지정 우선 도구(챗) — 도구 카탈로그에서 직접 선택한 도구를 우선 사용하게 강제.
    pinned_tools: list[str] | None = Field(default=None, max_length=12)
    # 사용자 지정 우선 앱(챗) — 앱 하나가 도구 20~30개라 12개 캡을 씌우면 조용히 잘린다.
    # 캡은 앱 수(3개)로 걸고, 도구 펼침은 agent-server 가 한다.
    pinned_apps: list[str] | None = Field(default=None, max_length=3)
    # 사용자 지정 전문가(챗) — 이 전문가 페르소나로 대화('전문가와 대화' 모드).
    pinned_agent: str | None = Field(default=None, max_length=120)
    # 여러 전문가를 한 목소리로 — 첫 명이 주 전문가다(도구 특화 + 전문지식 조합).
    pinned_agents: list[str] = Field(default_factory=list, max_length=5)
    # 표시용 이름. **agent-server 로 넘기지 않는다** — 서버 대화에 같이 적어 두었다가 다른
    # 기기에서 열 때 키 대신 사람이 읽을 이름을 되살리는 데만 쓴다.
    pinned_agent_name: str | None = Field(default=None, max_length=200)
    # 붙인 문서의 **추출문**(챗). 원본 파일은 오지 않는다 — DRM 문서는 그 PC 에서만 복호화되므로
    # 추출을 사용자 PC 의 Office COM 으로 옮겼다(docs/doc-deliberate). 여기 오는 것은 이미 평문이다.
    documents: list[ChatDocument] | None = Field(default=None, max_length=10)
    # 이 발화에 올린 그림(챗) — 에이전트 서버로 그대로 넘긴다. 서버 대화에는 원본이 아니라 돌려받은 주소만 남는다.
    images: list[ChatImage] | None = Field(default=None, max_length=_IMAGES_MAX)
    # 웹 리서치 소스 토글(챗) — None 이면 종전 동작, 리스트면 그 소스만 바인딩한다.
    # 빈 리스트는 '전부 끔'이다. 전역 SEARCH_MODE 가 끄면 이 값과 무관하게 나가지 않는다.
    search_sources: list[str] | None = Field(default=None, max_length=4)
    # 띵킹 모드(챗) — 질문을 전문가 풀에 돌려 답할 수 있는 좌석만 각자 답하게 한다.
    # delib_opts 가 아니라 top-level 인 이유는 매 턴 켜져 있어야 하는 모드이기 때문이다
    # (프론트 슬래시 접두사는 첫 발화에만 붙는다). 여기 선언하지 않으면 조용히 유실된다.
    thinking: bool = False
    # 분석 루틴(챗 루틴 모드, docs/analysis-routines R3-design) — 권한 feat:routines. message 는 그대로 필수다(사람 글이 없으면 '루틴: <제목>').
    # 에이전트 서버 ChatRequest 에도 같은 칸이 있어야 한다 — 없으면 조용히 버려져 그 글이 일반 챗으로 돈다(시험이 AST 로 본다).
    routine: RoutineReq | None = None


# ── 서버 대화 저장소 REST ─────────────────────────────────────────────────────
# 웹 챗·Claude(MCP) 심의·GLM 이어가기가 공유하는 정본. 인증은 /chat 과 동일하게
# PAT(Bearer) 또는 세션 쿠키(+CSRF). owner_sub 로 소유권 강제(타인 대화 접근 차단).


class ConvMessageIn(BaseModel):
    role: Literal["user", "assistant", "system", "persona"] = "assistant"
    # = _WINDOW_CHARS. 숫자로 적는다 — 게이트웨이 시험이 이 줄을 `max_length=숫자` 로 읽어 제 조각 크기와 견준다(종전 20,000 은
    # 2만 자 넘는 발언 하나로 일괄 생성 전체를 422 로 떨어뜨렸다).
    content: str = Field(max_length=4194304)
    persona: str | None = Field(default=None, max_length=120)
    round: int | None = None
    meta: dict | None = None


class ConvCreate(BaseModel):
    title: str = Field(default="새 대화", max_length=200)
    # risk-review = 리스크 심사 패널 대화(앱 러너가 생성). 저장은 kind TEXT 그대로라 DDL 변경 없다.
    kind: Literal["chat", "deliberation", "risk-review"] = "chat"
    source: Literal["web", "mcp"] = "web"
    # MCP 심의 등 일괄 생성 — 라운드 발언 전체를 한 번에(왕복 최소화). 비면 빈 대화 생성.
    messages: list[ConvMessageIn] = Field(default_factory=list, max_length=200)


def _conv(request: Request):
    return request.app.state.conv_store


# ⚠ 대화 저장소는 **이벤트 루프 밖에서만** 부른다. 동기 sqlite3 라 잠금을 기다리는 동안(최대 CONV_STORE_BUSY_TIMEOUT_S, 30초)
#   부른 스레드가 멈추는데, 포털은 uvicorn 프로세스 하나에 루프 하나다 — 루프 위에서 부르면 로그인, 다른 사람의 릴레이와 그
#   ping, 게이트웨이·리스크 앱이 포털에 거는 3~8초짜리 조회가 같이 멈춘다(사본 실측 — 12초 잠금에 무관한 GET /health 가
#   12.1초). 그래서 아래 대화 REST 는 `def`(FastAPI 가 스레드풀에서 돌린다)이고, async 인 /chat·검색은 to_thread 로 넘긴다.
#   **하나라도 루프에 남기면 안 된다** — 스레드가 잠금을 기다리는 동안 저장소의 Lock 을 쥐고 있어, 루프에서 부른 쪽이 그
#   Lock 에서 같이 멈춘다. 저장소는 메서드마다 Lock 을 commit 까지 쥐므로 스레드를 오가도 트랜잭션이 섞이지 않는다.


def _store_busy(exc: sqlite3.OperationalError) -> AuthError:
    """대화 쓰기가 sqlite 에서 막혔다 → 503. 리스크 앱이 패널 전에 대화를 만드는 자리라(POST /agent/conversations), 사유 없는
    500 이면 그쪽 로그에 '대화 생성 거부: HTTP 500' 만 남는다 — 무엇을 기다리다 포기했는지와 손잡이를 말한다."""
    return AuthError(f"대화 저장소에 쓰지 못했습니다 — {exc}(잠금 대기 CONV_STORE_BUSY_TIMEOUT_S="
                     f"{get_settings().conv_store_busy_timeout_s:g}초). 잠시 뒤 다시 시도하세요", status_code=503)


@router.get("/search-capability")
async def search_capability(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """웹 리서치 소스 가용성 — 프론트가 토글을 정직하게 그리기 위한 값.

    전역이 꺼져 있는데 UI 에서 켤 수 있으면 사용자는 켰다고 믿고 기다린다. 아무것도
    나가지 않는데 '검색이 잘 안 되는 도구'로만 보이는 것이 이 기능의 현실적 실패 모드다."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(f"{settings.agent_server_url}/search-capability")
            r.raise_for_status()
            return r.json()
    except Exception:  # noqa: BLE001 — agent-server 불통은 '알 수 없음'이지 '가능'이 아니다
        return {"sources": {}, "note": "agent-server 에 연결하지 못해 가용성을 확인할 수 없습니다."}


def _chat_user_pat(keystore, settings: Settings, principal: Principal) -> str | None:
    """이 챗·심의 한 번을 위한 PAT. agent-server 가 이걸로 게이트웨이에 붙는다.

    왜 필요한가 — agent-server 는 지금까지 서비스 계정(GW_TOKEN)으로 게이트웨이에 붙고
    사용자는 X-HWAX-User 헤더로만 알렸다. 그러면 게이트웨이가 "호출자 신원"을 요구하는
    도구(대화 검색·저장처럼 포털에 되물어야 하는 것들)에서 포털이 401 을 준다. 실측으로
    search_conversations 가 웹 챗에서만 CONV_UNAVAILABLE 이었다.

    새 공유비밀을 만들지 않고 이미 있는 PAT 체계를 쓴다. 게이트웨이는 이 토큰을 포털
    JWKS 로 검증하므로 위조가 불가능하고, 도구 인가도 서비스 계정이 아니라 이 사람의
    groups 로 이뤄진다 — 감사 기록도 사람 단위로 남는다.

    ⚠ 30분 창(window)에 맞춰 결정적으로 발급한다 — 같은 사용자·같은 창이면 토큰이 완전히
    같다. 매번 새로 찍으면 agent-server 의 에이전트 캐시가 첫 요청의 토큰을 물고 계속
    재사용해서, 이후에 보낸 새 토큰은 무시되고 그 하나가 만료되며 도구가 조용히
    죽는다. 창을 맞춰 두면 캐시는 그대로 맞고 자격증명은 30분마다 갱신된다.

    수명은 창의 시작 + CHAT_PAT_TTL_S(기본 24시간)다 — 남은 유효기간은 항상 (그 값 − 30분) 이상이다.
    종전에는 창의 시작 + 60분이라 30~60분이 남았는데, 심의는 시작할 때 받은 이 토큰을 **끝까지** 쓴다.
    그보다 오래 돈 심의가 좌석 조회를 잃고 마지막 Report Archive 저장에 실패했다(사유 없이).
    """
    try:
        now = datetime.now(tz=UTC)
        win = int(now.timestamp()) // 1800 * 1800     # 30분 창의 시작
        issued = datetime.fromtimestamp(win, tz=UTC)
        claims = {
            "iss": settings.jwt_issuer,
            "sub": principal.subject,
            "email": principal.email,
            "name": principal.display_name,
            # 로그인 그룹만 — `/auth/pat`·절차 PAT 과 같은 규칙. 관리자 표지·권한 키는 게이트웨이가 포털의 지금 값으로 붙인다.
            "groups": login_groups(principal.groups),
            "aud": [settings.pat_chat_audience],
            "scope": "api",
            "scopes": ["chat"],
            "pat_name": "chat-session",
            # 수명은 손잡이를 그대로 쓰지 않는다 — 창보다 길지 않은 값(0 포함)이면 찍자마자 만료라 기본값으로 읽는다(config.chat_pat_ttl_s)
            "iat": issued, "nbf": issued, "exp": issued + timedelta(seconds=chat_pat_ttl_s(settings)),
            # jti 도 결정적이어야 토큰이 바이트 단위로 같아진다. 서명된 토큰이라 예측
            # 가능성 자체는 위험이 아니고, 폐기 목록에 이 값을 넣으면 그 창이 막힌다.
            "jti": f"chat-{principal.subject}-{win}",
        }
        return jwt.encode(claims, keystore.private_pem, algorithm="RS256",
                          headers={"kid": keystore.active_kid})
    except Exception:  # noqa: BLE001 — 발급 실패로 챗 자체를 막지 않는다
        logger.warning("챗용 사용자 PAT 발급 실패 — agent-server 가 GW_TOKEN 으로 돈다",
                       exc_info=True)
        return None


def _site_pat(keystore, settings: Settings, principal: Principal, site: str, ttl_s: int = 900) -> str | None:
    """게이트웨이 REST 다리(/api/<site>/…)를 그 사람 명의로 한 번 부를 짧은 PAT — 청중은 그 사이트 하나(docs/request-1027 HP-15).

    챗 PAT 은 청중이 pat_chat_audience 하나라 다리가 거절한다(다리는 aud 에 사이트가 있어야 한다). 챗 PAT 의 청중을 넓히면 챗 · 심의 내내
    그 사이트를 부를 수 있게 되므로 넓히지 않고, 보내기 한 번에 그 사이트만 담아 찍는다. jti 는 매번 새것이다(캐시할 일이 없다)."""
    try:
        now = datetime.now(tz=UTC)
        claims = {
            "iss": settings.jwt_issuer, "sub": principal.subject, "email": principal.email, "name": principal.display_name,
            "groups": login_groups(principal.groups), "aud": [site], "scope": "api", "scopes": ["upload"],
            "pat_name": f"upload-{site}", "iat": now, "nbf": now, "exp": now + timedelta(seconds=ttl_s),
            "jti": f"upload-{site}-{uuid.uuid4().hex}",
        }
        return jwt.encode(claims, keystore.private_pem, algorithm="RS256", headers={"kid": keystore.active_kid})
    except Exception:  # noqa: BLE001 — 발급 실패는 부른 쪽이 401 로 알린다
        logger.warning("업로드용 사이트 PAT 발급 실패(%s)", site, exc_info=True)
        return None


@router.get("/conversations")
def list_conversations(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    # 최근 100건만 준다 — 총수와 끊었는지를 같이 싣는다. 없으면 Claude(MCP)·다른 기기에서 101번째부터는 없는 대화로 보였다.
    store = _conv(request)
    rows = store.list_for_owner(principal.subject)
    total = store.count_for_owner(principal.subject)
    return {"conversations": rows, "total": total, "truncated": total > len(rows)}


@router.post("/conversations")
def create_conversation(
    request: Request,
    body: ConvCreate,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    try:
        if body.messages:
            cid = _conv(request).create_with_messages(
                owner_sub=principal.subject, title=body.title, kind=body.kind,
                source=body.source,
                messages=[m.model_dump() for m in body.messages],
            )
        else:
            cid = _conv(request).create(
                owner_sub=principal.subject, title=body.title, kind=body.kind, source=body.source
            )
    except sqlite3.OperationalError as exc:
        raise _store_busy(exc) from exc
    return {"id": cid}


@router.get("/conversations/{cid}")
def get_conversation(
    cid: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    conv = _conv(request).get(cid, principal.subject)
    if conv is None:
        raise AuthError("conversation not found", status_code=404)
    return conv


@router.post("/conversations/{cid}/messages")
def append_conversation_message(
    cid: str,
    request: Request,
    body: ConvMessageIn,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    try:
        ok = _conv(request).append(
            conversation_id=cid, owner_sub=principal.subject, role=body.role,
            content=body.content, persona=body.persona, round=body.round, meta=body.meta,
        )
    except sqlite3.OperationalError as exc:
        raise _store_busy(exc) from exc
    if not ok:
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


class WikiSendIn(BaseModel):
    """'위키에 남기기' · '해결됨' — text 는 남길 답의 본문(저장된 답과 글자 그대로 같아야 짝이 찾아진다), model 은 표시용 꼬리표."""
    text: str = Field(min_length=1, max_length=400_000)
    mode: Literal["button", "candidate"] = "button"
    outcome: Literal["solved", "partial", "unknown"] = "solved"
    model: str | None = Field(default=None, max_length=120)


@router.get("/wiki/status")
async def wiki_status(
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """이 박스의 MX 백서 위키가 켜져 있나 — 화면이 '위키에 남기기' · '해결됨' 버튼과 심의 옵션을 숨기는 근거(docs/request-1027 HP-16).
    enabled 가 null 이면 모른다(게이트웨이 도구 지도를 한 번도 못 읽었다) — 화면은 종전대로 보인다."""
    return {"enabled": _wiki.wiki_on(await _upload.gateway_tool_names(settings))}


@router.post("/conversations/{cid}/wiki")
async def send_turn_to_wiki(
    cid: str,
    request: Request,
    body: WikiSendIn,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """저장된 턴을 MX 백서 위키 원천으로 — button 은 바로 들이기, candidate 는 주인만 보는 후보(docs/mxwp-wiki P6 · P7, app/agent/wiki_send.py).
    실패해도 감사 한 줄을 남긴다(업로드 보내기와 같은 까닭 — 게이트웨이 너머에서 이미 일어난 일이 있을 수 있다)."""
    try:
        return await _wiki_send(request, cid, body, principal, settings)
    except Exception as exc:  # noqa: BLE001 — 남기고 그대로 올린다
        try:
            _audit(request).record(principal=principal.subject, event="wiki_submit", status="failed",
                                   meta={"conversation": cid, "mode": body.mode, "error": f"{type(exc).__name__}: {exc}"[:300]})
        except Exception:  # noqa: BLE001 — 감사 실패가 원래 오류를 가리면 안 된다
            logger.warning("위키 보내기 실패 감사 기록 실패", exc_info=True)
        raise


async def _wiki_send(request: Request, cid: str, body: WikiSendIn, principal: Principal, settings: Settings) -> dict:
    ensure(principal, _wiki.PLAT_KEY)
    if _wiki.wiki_on(await _upload.gateway_tool_names(settings)) is False:
        # 꺼진 박스 — 게이트웨이에서 502 로 끝나기 전에 말한다. 소속 없음(409)의 안내가 똑같이 실패할 '해결됨' 을 권하지 않게 먼저 본다(HP-16).
        raise AuthError("이 박스에서는 MX 백서 위키가 꺼져 있어 남길 수 없습니다(wiki_disabled) — 위키를 켠 뒤 다시 시도하세요", status_code=409)
    if not principal.email:
        raise AuthError("이메일이 없는 계정은 위키에 남길 수 없습니다 — MX 백서는 주인을 이메일로 가린다", status_code=400)
    try:
        conv = await asyncio.to_thread(_conv(request).get, cid, principal.subject)
    except sqlite3.OperationalError as exc:
        raise _store_busy(exc) from exc
    if conv is None:
        raise AuthError("conversation not found", status_code=404)
    turn = _wiki.pick_turn(conv.get("messages") or [], body.text)
    if turn is None:
        raise AuthError("이 대화에 저장된 그 답(과 그 앞의 질문)을 찾지 못했습니다 — 답이 저장된 뒤 다시 시도하세요", status_code=409)
    index, question, message = turn
    audience = _wiki.audience_for(_wiki.known_affiliation(request), body.mode)
    env = _wiki.qa_envelope(cid=cid, index=index, question=question, message=message, owner_email=principal.email.lower(),
                            audience=audience, mode=body.mode, outcome=body.outcome, model=body.model,
                            now=datetime.now(tz=UTC))
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    got = _wiki.result_of(await _upload.mcp_call(settings.mcp_gateway_url, pat, "wiki_submit_source",
                                                 {"envelope": env, "ingest": True}))
    _audit(request).record(principal=principal.subject, event="wiki_submit",
                           meta={"conversation": cid, "index": index, "mode": body.mode, "audience": audience,
                                 "source": got["id"], "dedup": bool(got.get("dedup"))})
    return {"ok": True, "mode": body.mode, "audience": audience, **got}


@router.delete("/conversations/{cid}")
def delete_conversation(
    cid: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    if not _conv(request).delete(cid, principal.subject):
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


class ConvRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.patch("/conversations/{cid}")
def rename_conversation(
    cid: str,
    request: Request,
    body: ConvRename,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    if not _conv(request).rename(cid, principal.subject, body.title):
        raise AuthError("conversation not found", status_code=404)
    return {"ok": True}


class ConvSearch(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=8, ge=1, le=30)


@router.post("/conversations/search")
async def search_conversations(
    request: Request,
    body: ConvSearch,
    principal: Principal = Depends(principal_pat_or_session),
) -> dict:
    """내 지난 대화를 의미로 찾는다. 남의 대화는 store 가 owner_sub 로 막는다.

    색인은 검색할 때 게으르게 채운다. 별도 워커를 두면 "언제 반영되는지"가 불투명해지고,
    방금 한 대화를 못 찾는 이유를 사용자가 알 방법이 없다. 지금 규모(수백 메시지)에서
    증분 색인은 한 번뿐이고, 그 다음부터는 새 메시지 몇 개만 채운다.
    """
    settings = get_settings()
    store = _conv(request)
    try:
        # 재기동 직후면 지금 임베딩 공간부터 안다 — 옛 표지로 색인할 것을 고르면 이미 새 공간인 메시지까지 다시 임베딩한다(HP-36).
        await conv_search.learn_tag(settings.embed_base_url)
        # 예산 안에 끝낼 수 없는 큰 메시지는 요청 밖에서 색인한다(검토 RR2-PF-2) — 응답의 index.in_background 가 그 수다.
        idx = await conv_search.reindex(store, principal.subject, settings.embed_base_url,
                                        spawn=conv_search.spawn_outside)
        hits = await conv_search.search(store, principal.subject, body.query,
                                        settings.embed_base_url, body.limit)
    except (httpx.HTTPError, ValueError) as e:
        # 임베더 불통을 빈 결과로 바꾸지 않는다 — "찾아봤는데 없다"로 읽히면 없는 사실을 믿는다.
        raise AuthError(f"의미검색을 할 수 없습니다(임베더 응답 실패): {e}", status_code=503) from e
    # 아직 남은 색인 분량을 반드시 실어 보낸다 — 게으른 색인은 한 번에 상한까지만 처리하므로,
    # 큰 대화 이력에서는 첫 검색이 '부분 색인 위의 결과' 다. 그 사실을 숨기면 못 찾은 것이
    # 없는 것으로 읽힌다.
    tag = conv_search.current_tag()          # 이번 검색이 쓴 임베딩 공간(AIDataHub 의 지금 모델) — 남은 색인도 그 공간으로 센다
    left = await asyncio.to_thread(store.remaining, principal.subject, tag)
    # 짧은 질의는 점수로 관련성을 가릴 수 없다(온토픽·오프토픽 분포가 겹친다). 결과를
    # 주되 그 사실을 함께 낸다 — 못 가르는 것을 가른 척하면 사용자가 무관한 결과를
    # 관련 있는 것으로 읽는다.
    warn = ("질의가 짧아 관련성 판정이 약합니다 — 무관한 결과가 섞일 수 있습니다. "
            "문장으로 풀어 쓰면 정확해집니다.") if conv_search.short_query(body.query) else ""
    if conv_search.floors_for(tag) is None:
        # 하한은 모델의 점수 분포로 잰다 — 재지 않은 모델의 점수로 거르면 맞는 것까지 버리거나 무관한 것을 통과시킨다. 거르지 않고 알린다.
        warn = ("이 임베딩 모델의 관련성 하한을 아직 재지 않아 점수로 거르지 않았습니다 — 무관한 결과가 섞일 수 있습니다. "
                + warn).strip()
    return {"query": body.query, "results": hits,
            "low_confidence": bool(warn), "note": warn,
            "index": {**(await asyncio.to_thread(store.index_stats, principal.subject, tag)), "embed_space": tag,
                      "just_indexed": idx["indexed"], "too_short": idx["too_short"],
                      "not_indexed_yet": left,
                      # 색인이 시간 예산(conv_search.REINDEX_BUDGET_S)에서 멈췄다 — 게이트웨이 한도 안에 답하려고 남긴 것이다.
                      "budget_hit": idx.get("budget_hit", False),
                      # not_indexed_yet 가운데 요청 밖에서 색인 중인 큰 메시지 — 남은 수만 보면 다음 검색도 못 끝낼 것처럼 읽힌다.
                      "in_background": idx.get("background", 0),
                      **({"background_note": f"큰 메시지 {idx['background']}건은 검색 한 번의 시간 안에 색인을 끝낼 수 없어 요청 밖에서 "
                                             "색인하고 있다 — 끝나면 다음 검색부터 찾힌다(not_indexed_yet 에는 아직 든다)."}
                         if idx.get("background") else {}),
                      "partial": bool(left)}}


def _parse_sse_frame(frame: str) -> tuple[str, dict] | None:
    """완결된 SSE 프레임 1개('event: x\\ndata: {...}') → (event, data). 파싱 불가면 None."""
    evt = None
    data_lines: list[str] = []
    for line in frame.split("\n"):
        if line.startswith("event:"):
            evt = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if evt is None or not data_lines:
        return None
    import json
    try:
        return evt, json.loads("\n".join(data_lines))
    except (ValueError, TypeError):
        return None


def _audit(request: Request) -> AuditLog:
    return request.app.state.agent_audit


def _sem(request: Request) -> asyncio.Semaphore:
    return request.app.state.agent_semaphore


def _agent_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.agent_client


def _unary_timeout(settings: Settings) -> httpx.Timeout:
    """비스트리밍 프록시(심의 전 도우미·전문가 카탈로그)의 요청별 한도 — read 만 AGENT_UNARY_TIMEOUT_S(0 이하는 끔).

    공유 클라이언트의 read 는 SSE 침묵 한도(13시간)라, 요청마다 따로 주지 않으면 도우미 하나가 그만큼 매달린다."""
    t = settings.agent_unary_timeout_s
    return httpx.Timeout(settings.agent_request_timeout, read=t if t > 0 else None)


def _unary_fail(exc: httpx.HTTPError, settings: Settings, what: str) -> dict:
    """비스트리밍 프록시가 실패했을 때 폴백에 얹는 칸. 시간 초과를 '연결 못 함' 과 가른다 — 서버는 살아 있고 느린 것이다."""
    if isinstance(exc, httpx.ReadTimeout):
        t = settings.agent_unary_timeout_s
        logger.warning("에이전트 서버 %s 응답이 %s초 안에 오지 않았다(AGENT_UNARY_TIMEOUT_S) — 기본값으로 진행한다", what, t)
        return {"error": "agent_timeout",
                "message": f"도우미 응답이 {t:.0f}초 안에 오지 않아 기본값으로 진행한다(AGENT_UNARY_TIMEOUT_S)"}
    return {"error": "agent_unreachable"}


async def _echo_stream(message: str, principal: Principal, audit: AuditLog) -> AsyncIterator[bytes]:
    """Local echo: emits the §5 SSE contract (status → token×N → result → done)."""
    chat_id = "echo"
    audit.record(principal=principal.subject, event="chat_start", chat_id=chat_id,
                 meta={"mode": "echo"})
    yield sse_event("status", {"step": "요청 수신", "tool": None})
    await asyncio.sleep(0.2)
    reply = f"echo: {message}"
    for ch in reply:
        yield sse_event("token", {"delta": ch})
        await asyncio.sleep(0.02)
    yield sse_event("result", {"type": "text", "content": reply})
    audit.record(principal=principal.subject, event="chat_done", chat_id=chat_id, status="ok")
    yield sse_event("done", {})


# 심의 트리거 — 에이전트 서버 deliberation.py 의 DELIBERATE_TRIGGERS · SIM_DELIBERATE_TRIGGERS · TEST_PLAN_TRIGGERS 와 같다(시험
# tests/test_chat_idle_split.py 가 형제 리포의 실제 값과 대조한다). 중계의 침묵 한도를 고르는 데만 쓴다 — 심의를 여는 판정은 에이전트 서버가 한다.
_DELIB_TRIGGERS = ("/심의", "/deliberate", "/토의", "/시뮬심의", "/시뮬레이션심의", "/simdeliberate",
                   "/시험계획", "/시험설계", "/testplan", "/DOE")


def _is_delib_message(message: str | None) -> bool:
    return (message or "").strip().startswith(_DELIB_TRIGGERS)


async def _relay_stream(
    body: "ChatRequest", principal: Principal, audit: AuditLog,
    settings: Settings, client: httpx.AsyncClient, user_pat: str | None = None, affiliation: str = ""
) -> AsyncIterator[bytes]:
    """Relay the remote Agent Server's SSE stream byte-for-byte to the browser.

    The portal stays a thin proxy: it forwards the message + the caller's groups (for
    allowed_groups filtering downstream) and pipes back whatever the Agent Server emits,
    which already speaks the §5 contract. Auth/CSRF were enforced before we got here.
    Upstream error detail is logged server-side (audit), NOT reflected to the browser.
    """
    chat_id = "relay"
    audit.record(principal=principal.subject, event="chat_start", chat_id=chat_id,
                 meta={"agent": settings.agent_server_url, "system_id": body.system_id})
    routine = body.routine is not None
    if routine and not user_pat:
        # 루틴은 사람 PAT 로만 돈다(AR-D4) — 발급이 실패하면 일반 챗처럼 서비스 계정(GW_TOKEN)으로 떨어지지 않고(게이트웨이도 거절한다)
        # 에이전트 서버를 부르지 않는다. 실행을 만들기 전이라 원장에 남는 것이 없다.
        audit.record(principal=principal.subject, event="chat_error", chat_id=chat_id,
                     status="error", meta={"reason": "routine_no_pat"})
        yield sse_event("error", {"code": "routine_no_pat", "message": "루틴은 사람 토큰으로만 돈다 — 다시 로그인한 뒤 보낸다"})
        yield sse_event("done", {})
        return
    payload = {
        "message": body.message,
        "system_id": body.system_id,
        "groups": principal.groups,
        # 호출자 신원 — 게이트웨이가 사용자별 데이터를 쓰는 백엔드(DynaForge 등)를 이 사람의
        # 자격증명으로 부른다. 브라우저가 보낸 값이 아니라 검증된 세션/PAT 주체에서 채운다.
        "user_email": principal.email,
        # agent-server 가 게이트웨이에 '이 사람으로' 붙기 위한 단명 자격증명.
        # ⚠ None 을 그대로 보내면 안 된다. agent-server 의 ChatRequest.user_pat 은 str 이라
        # pydantic 이 null 을 422 로 거절하고, 그러면 '발급 실패해도 챗은 계속' 이라는 이쪽
        # 폴백이 정반대로 챗 전체를 죽인다(실측: null→422, ""→200). 빈 문자열이 '없음' 이다.
        "user_pat": user_pat or "",
        # 호출자 소속 id — 원장 값(권한표에 없는 id 는 빈 값, wiki_send.known_affiliation). 위키에 남기는 심의(delib_opts.wiki)의
        # 범위다(docs/mxwp-wiki P8). 브라우저가 보낸 값이 아니다.
        "affiliation": affiliation,
        "history": [m.to_agent() for m in body.history],
        # 요청 시점 권한 — 심의·Thinking 트리거는 agent-server 가 판정하므로 그쪽이 한 번 더 막는다.
        "entitlements": sorted(g for g in principal.groups if is_synthetic(g)),
    }
    if body.delib_opts is not None:  # 지정된 손잡이만 전달(None 필드는 제외 → env 기본값 유지)
        payload["delib_opts"] = body.delib_opts.model_dump(exclude_none=True)
    if body.pinned_tools:  # 사용자 지정 우선 도구 — 켠 것만 전달
        payload["pinned_tools"] = body.pinned_tools
    if body.pinned_apps:  # 사용자 지정 우선 앱 — agent-server 가 도구로 펼친다
        payload["pinned_apps"] = body.pinned_apps
    if body.pinned_agent:  # 사용자 지정 전문가 페르소나
        payload["pinned_agent"] = body.pinned_agent
    if body.pinned_agents:  # 여러 명 — 첫 명이 주 전문가
        payload["pinned_agents"] = body.pinned_agents
    if body.search_sources is not None:  # 빈 리스트도 의미가 있다(전부 끔) — None 과 구분
        payload["search_sources"] = body.search_sources
    if body.thinking:  # 띵킹 모드 — 켠 것만 전달(끄면 agent-server 기본값 False)
        payload["thinking"] = True
    if body.documents:  # 붙인 문서의 추출문 — 원본이 아니라 평문이다
        payload["documents"] = [d.model_dump() for d in body.documents]
    if body.images:  # 올린 그림 — 에이전트 서버가 저장하고 주소를 돌려준다(user_images)
        payload["images"] = [i.model_dump() for i in body.images]
    if body.conversation_id:  # 서버 대화 id — 에이전트가 챗 LLM 호출의 대화 머리(X-Session-Affinity)로만 쓴다(docs/request-1029 W-1)
        payload["conversation_id"] = body.conversation_id
    if routine:  # 분석 루틴 — 채운 칸만(새 실행은 id · version · inputs · note, 이어서는 run_id, RA 초안 올리기는 run_id · upload_ra).
        # version 은 1 이상이라 참거짓으로 걸러도 된다. 빈 note · 거짓 upload_ra 도 싣지 않는다 — 칸이 없으면 실행기는 종전 그대로다
        payload["routine"] = {k: v for k, v in body.routine.model_dump().items() if v}
    # 침묵 한도 — 심의는 공유 클라이언트의 값(AGENT_STREAM_IDLE_TIMEOUT_S), 챗은 짧은 값(AGENT_CHAT_IDLE_TIMEOUT_S)을 이 요청에만 준다(P-1 ④).
    # 루틴 턴도 심의 쪽이다 — 단계 하나(작은 ReAct · 심의 단계)가 챗 한도보다 오래 조용할 수 있다(R3 D9).
    delib = _is_delib_message(body.message)
    if delib or routine:
        stream_kw: dict = {}
        idle, knob = client.timeout.read, "AGENT_STREAM_IDLE_TIMEOUT_S"
    else:
        _t = settings.agent_chat_idle_timeout_s
        stream_kw = {"timeout": httpx.Timeout(settings.agent_request_timeout, read=_t if _t > 0 else None)}
        idle, knob = stream_kw["timeout"].read, "AGENT_CHAT_IDLE_TIMEOUT_S"
    try:
        async with client.stream(
            "POST", f"{settings.agent_server_url}/chat", json=payload, **stream_kw
        ) as r:
            if r.status_code != 200:
                # 감사에만 남긴다(브라우저에는 코드만). 422 의 사유는 어느 칸이 넘었는지를 말하는데 종전엔 200자에서 표식 없이
                # 잘랐다 — 자르면 원래 길이를 붙인다(사유 본문이 요청 글을 되풀이할 수 있어 감사 칸은 2,000자로 둔다).
                _raw = (await r.aread()).decode(errors="replace")
                detail = _raw if len(_raw) <= 2000 else _raw[:2000] + f"…(원문 {len(_raw):,}자)"
                audit.record(principal=principal.subject, event="chat_error",
                             chat_id=chat_id, status="error",
                             meta={"upstream": r.status_code, "detail": detail})
                yield sse_event("error", {"code": f"agent_{r.status_code}",
                                          "message": "agent server error"})
                yield sse_event("done", {})
                return
            async for chunk in r.aiter_raw():
                if chunk:
                    yield chunk
    except httpx.ReadTimeout:
        # 침묵 한도(AGENT_STREAM_IDLE_TIMEOUT_S) — 연결은 살아 있는데 에이전트 서버가 그 시간 동안 한 바이트도 안 냈다.
        # '연결 못 함' 과 가른다: 사람이 할 일이 다르다(이쪽은 서버에서 심의가 아직 돌 수 있어, 곧바로 다시 시작하면
        # 두 번째 심의가 나란히 돈다). 엔진 ping 은 그대로 넘기고 여기서 따로 만들지 않는다 — 릴레이가 만들면
        # 멈춘 엔진이 바깥에서 살아 있는 것으로 보인다.
        audit.record(principal=principal.subject, event="chat_error", chat_id=chat_id,
                     status="error", meta={"reason": "agent_stream_idle", "idle_s": idle})
        logger.warning("에이전트 서버 스트림이 %s초 동안 조용해 구독을 끊었다(%s) sub=%s", idle, knob, principal.subject)
        if routine:
            # 루틴은 에이전트 서버에서 떼어 낸 작업이다(R3 D7) — 구독이 끊겨도 서버에서 돈다. 새로 시작하면 두 번째 실행이 나란히 돈다.
            msg = (f"에이전트 서버가 {idle:.0f}초 동안 아무 신호도 보내지 않아 구독을 끊었다"
                   "(AGENT_STREAM_IDLE_TIMEOUT_S). 루틴은 서버에서 계속 돌 수 있다 — 새로 시작하기 전에 "
                   "'이어서' 로 그 실행에 다시 붙어라")
        elif delib:
            msg = (f"에이전트 서버가 {idle:.0f}초 동안 아무 신호도 보내지 않아 구독을 끊었다"
                   "(AGENT_STREAM_IDLE_TIMEOUT_S). 심의는 서버에서 계속 돌 수 있다 — 다시 시작하기 전에 "
                   "Report Archive 와 대화 목록을 확인하라")
        else:
            # 챗 턴은 끊으면 에이전트 서버에서도 멈춘다(중계가 상류를 닫는다) — 다시 물어도 겹치지 않는다.
            msg = (f"에이전트 서버가 {idle:.0f}초 동안 아무 신호도 보내지 않아 답을 끊었다(AGENT_CHAT_IDLE_TIMEOUT_S). "
                   "챗 스트림은 15초마다 신호를 내므로 에이전트 서버가 멈춘 것이다 — 다시 물어보고, 되풀이되면 관리자에게 알려라")
        yield sse_event("error", {"code": "agent_stream_idle", "message": msg})
        yield sse_event("done", {})
        return
    except httpx.HTTPError as exc:
        audit.record(principal=principal.subject, event="chat_error", chat_id=chat_id,
                     status="error", meta={"reason": "agent_unreachable", "exc": str(exc)})
        yield sse_event("error", {"code": "agent_unreachable",
                                  "message": "agent server unreachable"})
        yield sse_event("done", {})
        return
    audit.record(principal=principal.subject, event="chat_done", chat_id=chat_id, status="ok")


@router.get("/artifacts/{name}")
async def get_artifact(
    name: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """도구 산출 이미지 프록시 — 챗 마크다운 ![](/agent/artifacts/…) 이 로드한다.
    GET+세션쿠키(CSRF 불요), 파일명은 agent-server 가 재검증."""
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
        return Response(status_code=404)
    client = _agent_client(request)
    try:
        r = await client.get(f"{settings.agent_server_url}/artifacts/{name}", timeout=_unary_timeout(settings))
        if r.status_code != 200:
            return Response(status_code=404)
        return Response(content=r.content,
                        media_type=r.headers.get("content-type", "application/octet-stream"),
                        headers={"Cache-Control": "private, max-age=86400"})
    except httpx.HTTPError as exc:
        _unary_fail(exc, settings, "artifacts")   # 그림이라 실을 본문이 없다 — 시간 초과면 로그만 남긴다
        return Response(status_code=502)


class CatalogAgentRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)


@router.post("/catalog/agent")
async def catalog_agent(
    request: Request,
    body: CatalogAgentRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """전문가 상세+보유 지식 — 브라우즈 UI 용 프록시(비스트리밍 JSON)."""
    ensure(principal, "feat:deliberation", "feat:expert-chat", any_of=True)
    client = _agent_client(request)
    try:
        r = await client.post(f"{settings.agent_server_url}/catalog/agent", timeout=_unary_timeout(settings),
                              json={"key": body.key, "groups": principal.groups})
        return r.json() if r.status_code == 200 else {"error": f"agent_{r.status_code}"}
    except httpx.HTTPError as exc:
        return _unary_fail(exc, settings, "catalog/agent")


class CatalogRecordsRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    q: str = Field(default="", max_length=200)
    offset: int = Field(default=0, ge=0, le=1_000_000)
    limit: int = Field(default=50, ge=1, le=100)


@router.post("/catalog/agent/records")
async def catalog_agent_records(
    request: Request,
    body: CatalogRecordsRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """전문가 한 명의 지식카드 목록(검색·쪽·총수) — 심층 보기 프록시."""
    ensure(principal, "feat:deliberation", "feat:expert-chat", any_of=True)
    client = _agent_client(request)
    try:
        r = await client.post(f"{settings.agent_server_url}/catalog/agent/records", timeout=_unary_timeout(settings),
                              json={**body.model_dump(), "groups": principal.groups})
        return r.json() if r.status_code == 200 else {"error": f"agent_{r.status_code}", "total": 0, "items": []}
    except httpx.HTTPError as exc:
        return {"total": 0, "items": [], **_unary_fail(exc, settings, "catalog/agent/records")}


class CatalogRecordRequest(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    # 다음 부분 보기 — 앞 응답의 next(절 번호 · 그 절 안 글자 위치)를 그대로 돌려받는다(목록의 offset 과 같은 꼴).
    section_offset: int = Field(default=0, ge=0, le=1_000_000)
    char_offset: int = Field(default=0, ge=0, le=2_000_000)


@router.post("/catalog/record")
async def catalog_record(
    request: Request,
    body: CatalogRecordRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """지식카드 한 장(본문·표·출처) — 심층 보기의 읽기 칸 프록시."""
    ensure(principal, "feat:deliberation", "feat:expert-chat", any_of=True)
    client = _agent_client(request)
    try:
        r = await client.post(f"{settings.agent_server_url}/catalog/record", timeout=_unary_timeout(settings),
                              json={**body.model_dump(), "groups": principal.groups})
        return r.json() if r.status_code == 200 else {"error": f"agent_{r.status_code}", "id": body.id}
    except httpx.HTTPError as exc:
        return {"id": body.id, **_unary_fail(exc, settings, "catalog/record")}


class ExpertsRequest(BaseModel):
    # 화두 — 챗 메시지와 같은 상한이다. 종전 8,192 는 챗(65,536)보다 작아 긴 화두에서 422 → 빈 추천이 됐다.
    message: str = Field(min_length=1, max_length=_WINDOW_CHARS)
    # 대화 전체 — 좌석 추천을 화두 한 줄이 아니라 오간 맥락 위에서 하기 위한 것.
    # 캡은 챗 경로와 같은 계약을 쓴다(별도 규칙을 만들면 한쪽만 조이는 일이 생긴다).
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=160)
    history_total = field_validator("history")(_history_total)
    # 조직도 1단계(명부만) — 트리를 먼저 그리고 태그·도구 카탈로그는 뒤에서 받는다.
    light: bool = False


class ClarifyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=_WINDOW_CHARS)
    # 심의 방법 — 칸 묶음을 고른다(원인 규명·안 선택·신뢰 판정·시험 설계…). 모르는 값은 서버가 자유 심의로 본다.
    job: str = Field(default="default", max_length=40)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=160)
    history_total = field_validator("history")(_history_total)


class VocPreviewRequest(BaseModel):
    message: str = Field(min_length=1, max_length=_WINDOW_CHARS)
    # 사람이 고친 영어 검색어 — 주면 추출을 건너뛴다.
    keywords: list[str] = Field(default_factory=list, max_length=6)


class DocxTurn(BaseModel):
    """심의 좌석 발언 한 건. delib.turns 가 렌더 대상이 된 이상 여기에도 캡이 필요하다 —
    extra=allow 로 열어 두면 캡을 건 text 옆에서 delib 이 무제한으로 들어온다."""
    model_config = {"extra": "ignore"}
    round: int | None = None
    persona: str = Field(default="", max_length=120)
    # 글 칸 하나의 상한은 총량(4,000,000자 — ConvPayload._total_budget)과 같다. 칸마다 따로 작게 두면 결정문·발언 하나가 총량 안인데도
    # 422 다. 정리본 원문은 줄이지 않은 발언(sayFull — 엔진 say_full)을 쓰고, say 는 화면 버블이다.
    say: str = Field(default="", max_length=4_000_000)
    sayFull: str = Field(default="", max_length=4_000_000)  # noqa: N815 — 프론트 필드명
    position: str = Field(default="", max_length=2_000)
    stance: str = Field(default="", max_length=120)
    # 양보 불가 조항도 같은 칸이다 — 엔진이 넓은 창에서 _summary_max()(1M 창 29,077자, 종전 1,200자)까지 보내고 서버 사본은 자르지
    # 않는다. 2,000자에서 막으면 그 대화는 전문·정리본 둘 다 422 였다(다른 기기에서 열어도 같다). position 은 엔진이 90자에서 끊는다.
    nonNegotiable: str = Field(default="", max_length=4_000_000)  # noqa: N815 — 프론트 필드명

    @model_validator(mode="after")
    def _drop_unrendered_bubble(self) -> "DocxTurn":
        """렌더(docx_export._say)는 sayFull 이 있으면 say(회의 버블)를 쓰지 않는다. 들고 있으면 총량(_total_budget)이 버블을
        이중으로 세어, 렌더할 글이 상한 안인 대화가 422 였다 — 웹은 턴마다 둘을 함께 보낸다."""
        if self.sayFull:
            self.say = ""
        return self


class DocxDelib(BaseModel):
    model_config = {"extra": "ignore"}
    turns: list[DocxTurn] = Field(default_factory=list, max_length=400)


class DocxMessage(BaseModel):
    """내보내기 입력의 메시지 한 건.

    ⚠ extra 를 닫는다. allow 로 두면 캡을 건 필드 옆으로 임의 크기 JSON 이 무제한 통과해
    캡이 메모리 상한 구실을 못 한다. docx_export 가 실제로 읽는 필드를 전수 확인했고
    (delib·role·text·ts, turn 은 round/persona/say/sayFull/position/stance/nonNegotiable),
    전부 여기 선언돼 있으므로 닫아도 잃는 것이 없다.
    """
    model_config = {"extra": "ignore"}
    role: str = Field(default="assistant", max_length=40)
    text: str = Field(default="", max_length=4_000_000)
    # 표시용 시각. int/float/str/None 만 받는다 — Any 로 열어 두면 extra 를 닫은 의미가
    # 없다(임의 크기 dict·list 가 그대로 들어온다). 값의 타당성은 _ts 가 다시 본다.
    ts: int | float | str | None = None
    delib: DocxDelib | None = None


class ConvPayload(BaseModel):
    model_config = {"extra": "ignore"}
    title: str = Field(default="", max_length=300)
    messages: list[DocxMessage] = Field(default_factory=list, max_length=2000)

    @field_validator("messages")
    @classmethod
    def _total_budget(cls, v: list[DocxMessage]) -> list[DocxMessage]:
        """총량 상한. 항목별 캡만 있으면 2000개 × 20만자 = 4억자가 통과한다 —
        통째로 메모리에 올려 렌더하므로 그것 자체가 부하다."""
        # ⚠ 렌더되는 문자열 필드를 **전부** 센다. 앞선 커밋은 같은 자리에서 text 와 say 만
        # 세어, position·nonNegotiable·persona·stance 로 채운 페이로드가 '0자' 로 통과했다 —
        # 그 커밋이 바로 위 docstring 에 그 필드 목록을 적어 놓고도 합산식에 안 쓴 것이다.
        # 필드를 늘리면 여기도 같이 늘려야 한다. 그래서 목록을 한 곳에 둔다.
        def _turn_chars(t: "DocxTurn") -> int:
            return sum(len(getattr(t, f) or "")
                       for f in ("say", "sayFull", "position", "stance", "persona", "nonNegotiable"))

        total = sum(len(m.text) + sum(_turn_chars(t) for t in (m.delib.turns if m.delib else []))
                    for m in v)
        if total > 4_000_000:
            # 거부 메시지에 입력을 되싣지 않는다 — pydantic 이 detail.input 으로 페이로드
            # 전체를 되돌려주면 거부가 렌더보다 비싸진다. 숫자만 말한다.
            raise ValueError(f"본문 총량이 상한(400만자)을 넘는다: {total}자")
        return v


class DocxRequest(BaseModel):
    """대화 이력 → Word. mode='transcript' 는 있는 그대로, 'report' 는 LLM 이 정리한다."""
    # 상한을 건다. 같은 파일의 다른 모델은 전부 캡이 있는데 여기만 맨 dict 였다 —
    # 통째로 메모리에 올린 뒤 python-docx 로 렌더하므로 큰 입력이 그대로 부하가 된다.
    conversation: ConvPayload = Field(default_factory=lambda: ConvPayload())
    mode: Literal["transcript", "report"] = "transcript"


# 정리본 지시 — 대화를 요약하는 게 아니라 **문서로 재구성**하라는 것이 요점이다.
# 요약만 시키면 "이런 얘기를 했다" 가 나오고, 그건 읽는 사람이 판단에 쓸 수 없다.
_REPORT_PROMPT = """다음은 엔지니어링 포털에서 오간 대화 이력이다. 이것을 그대로 요약하지 말고,
읽는 사람이 판단에 쓸 수 있는 **보고서**로 재구성하라.

규칙:
- 결론을 먼저 쓴다. 무엇을 하기로 했는지/무엇이 밝혀졌는지가 첫 절이다.
- 근거는 대화에 실제로 나온 것만 쓴다. 수치는 원문 그대로 옮기고, 없는 값을 지어내지 않는다.
- 대화에서 결론이 나지 않은 것은 '미결'로 따로 모은다. 억지로 결론을 만들지 않는다.
- 누가 말했는지는 옮기지 않는다. 문서는 대화록이 아니다.
- 한국어. 문장은 마침표로 끝낸다.

형식(마크다운):
# <문서 제목 — 내용을 담은 짧은 제목>
## 요약
## 결론과 근거
## 미결·확인 필요
## 상세

대화 이력:
"""


# 정리본에 넘기는 대화 원문의 상한 — 에이전트 서버가 알려 주는 모델 창(/health 의 context_tokens)에서 유도한다. 한국어 1자 ≈
# 1토큰으로 잡고 창의 60% 를 원문에 준다(나머지는 지시문·도구·출력 몫). 창을 못 읽거나 유도한 값이 더 작으면(dev 16K) 종전
# 60,000자가 바닥이다 — 종전 동작은 그대로 남는다. 종전엔 60,000 고정이라 1M 창에서 심의 대화의 결정문이 잘렸다.
_REPORT_TX_FLOOR = 60_000


async def _report_tx_limit(request: Request, settings: Settings) -> tuple[int, str]:
    """(상한, 출처) — 출처는 server(창을 읽었다) | fallback(못 읽어 바닥으로 돈다)."""
    try:
        r = await _agent_client(request).get(f"{settings.agent_server_url}/health", timeout=_unary_timeout(settings))
        ctx = int(r.json().get("context_tokens") or 0) if r.status_code == 200 else 0
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        ctx = 0
    if ctx <= 0:
        return _REPORT_TX_FLOOR, "fallback"
    return max(_REPORT_TX_FLOOR, int(ctx * 0.6)), "server"


@router.post("/export/docx")
async def export_docx(
    request: Request,
    body: DocxRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """대화 이력을 Word(.docx) 로 내려준다 — 브라우저가 그대로 저장한다.

    report 모드는 LLM 왕복이 있다. 실패하면 transcript 로 조용히 대체하지 않는다 —
    정리본을 기대한 사람에게 원문을 주면 '정리가 안 됐다'로 보이지 '실패했다'로 보이지 않는다.
    """
    # 모델 → dict. docx_export 는 dict 로 다루므로 여기서 한 번만 변환한다.
    audit = _audit(request)
    conv = body.conversation.model_dump()
    title = (conv.get("title") or "대화").strip()[:60]
    n_msg = len([m for m in (conv.get("messages") or []) if (m.get("text") or "").strip()])
    if not n_msg:
        return Response(content='{"error":"empty_conversation"}', status_code=400,
                        media_type="application/json")

    # ⚠ 게이트는 두 분기 모두에 건다. report 에만 걸어 두면 기본값인 transcript 가 무방비다 —
    # 총량 상한이 있어도 400만자 렌더는 수 초~수십 초 CPU 다. 같은 세마포어를 쓴다.
    sem = _sem(request)
    if sem.locked():
        audit.record(principal=principal.subject, event="docx", status="rejected",
                     meta={"reason": "max_concurrent_chats", "mode": body.mode})
        raise AuthError("too many concurrent exports; retry shortly", status_code=429)
    await sem.acquire()
    try:
        return await _export_docx_inner(request, body, principal, settings, audit, conv,
                                        title, n_msg)
    finally:
        sem.release()


async def _export_docx_inner(request, body, principal, settings, audit, conv, title, n_msg):
    # python-docx 는 여기서만 쓴다 — 임포트를 바깥에 두면 이 함수 스코프에 없어 NameError 다
    # (실측: 세마포어를 바깥으로 뺄 때 임포트를 같이 옮기지 않아 전문 내보내기가 500 이었다).
    from app.agent import docx_export as dx

    if body.mode == "transcript":
        # python-docx 렌더는 동기 CPU 작업이다. async 안에서 그대로 돌리면 그 시간만큼
        # 이벤트 루프가 멈춰 다른 사용자의 요청까지 함께 선다(대화검색 랭킹을 to_thread 로
        # 뺀 것과 같은 이유). 총량 상한이 있어도 400만자는 짧지 않다.
        data = await asyncio.to_thread(dx.build_transcript, conv)
        name = f"{title}-전문"
        audit.record(principal=principal.subject, event="docx_transcript",
                     status="ok", meta={"messages": n_msg})
    else:
        # ⚠ 이 경로는 /chat 과 똑같은 부하를 건다(에이전트 + LLM 왕복 수십 초). 그런데
        # 동시성 상한과 감사 기록을 둘 다 우회하고 있었다 — /chat 이 그 둘을 두는 이유가
        # 그대로 적용되는데도. 같은 게이트를 통과시킨다.
        # 세마포어는 바깥(export_docx)에서 이미 잡았다 — 이중 획득 금지.
        # ⚠ acquire 와 try 사이에 아무것도 두지 않는다. 그 틈에서 예외가 나면
        # 퍼밋이 영구히 새고, 상한만큼 쌓이면 챗 전체가 429 로 고정된다(실측 재현).
        # 대화 전체(총량 상한 400만자)를 문자열로 조립하는 동기 작업이다. 모델 창을 넘는 만큼만 뒤를 자르고, 잘랐으면
        # 받는 사람의 문서 머리와 감사 기록에 원문 길이를 남긴다(종전엔 모델만 '(…이후 생략)' 을 봤다).
        _full = await asyncio.to_thread(dx.transcript_text, conv, None)   # 원문 전체 — 창에서 유도한 상한은 아래에서 따로 건다
        _limit, _window = await _report_tx_limit(request, settings)
        _tx = _full if len(_full) <= _limit else dx.transcript_text(conv, limit=_limit)
        _sent = min(len(_full), _limit)
        md = ""
        try:
            # 에이전트는 SSE 만 낸다(비스트리밍 엔드포인트가 없다). 여기서 스트림을 받아
            # 최종 result 만 모은다 — 에이전트에 엔드포인트를 새로 파는 것보다 접점이 적다.
            client = _agent_client(request)
            payload = {"message": _REPORT_PROMPT + _tx,
                       "groups": principal.groups, "user_email": principal.email,
                       "user_pat": _chat_user_pat(request.app.state.keystore,
                                                  get_settings(), principal) or ""}
            async with client.stream("POST", f"{settings.agent_server_url}/chat",
                                     json=payload) as resp:
                if resp.status_code == 200:
                    ev = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("event: "):
                            ev = line[7:].strip()
                        elif line.startswith("data: ") and ev == "result":
                            try:
                                md = json.loads(line[6:]).get("content", "") or md
                            except ValueError:
                                pass
        except httpx.HTTPError:
            md = ""
        audit.record(principal=principal.subject, event="docx_report",
                     status="ok" if md.strip() else "error",
                     meta={"messages": n_msg, "tx_chars": len(_full), "tx_sent": _sent, "window": _window})
        if not md.strip():
            return Response(
                content='{"error":"report_failed","detail":"정리본 생성에 실패했습니다 — '
                        'LLM 응답이 없습니다. 전문(transcript) 내보내기는 그대로 동작합니다."}',
                status_code=503, media_type="application/json")
        first = next((ln.lstrip("# ").strip() for ln in md.splitlines()
                      if ln.startswith("#")), title)
        _sub = f"원본 대화 '{title}' · 발화 {n_msg}개"
        if _sent < len(_full):
            _sub += f" · 정리에 쓴 것은 원문 {len(_full):,}자 중 앞 {_sent:,}자다(뒤는 모델 창을 넘어 넣지 못했다)"
        data = await asyncio.to_thread(dx.build_report, first, md, _sub)
        name = f"{first[:50]}-정리본"

    safe = re.sub(r'[\\/:*?"<>|]+', " ", name).strip() or "대화"
    quoted = quote(f"{safe}.docx")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


class UploadAnalyzeReq(BaseModel):
    model_config = {"extra": "ignore"}
    staging_id: str
    filename: str
    # 재료 메타 — AI 가 채우거나 사용자가 입력. dry_run 미리보기에 필요.
    material_name: str = ""
    category: str = "metal"           # metal/polymer/rubber/composite/ceramic/foam
    material_id: int | None = None    # 기존 재료에 붙일 때
    gauge_length_mm: float = 25.0
    width_mm: float = 5.0
    thickness_mm: float = 1.0


class UploadCommitReq(UploadAnalyzeReq):
    pass


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """챗 파일 업로드 — 수신·스테이징만 한다(파싱·등록은 이후 단계에서 materialtwin 에 위임).

    두 층 게이트의 백엔드 층 — 프론트가 버튼을 숨겨도 이 검사가 API 직접 호출을 막는다.
    업로드는 쓰기라 사용자 자격증명이 반드시 있어야 하고, 강등되면 안 된다(무음 강등 금지).
    """
    # 수신 게이트는 **어느 목적지든 하나는 쓸 수 있는 사람**이면 통과시킨다. 목적지별
    # 판정은 dispatch 에서 다시 한다 — 여기서 물성 그룹만 요구하면 CAD 담당자가 STEP 을
    # 아예 올리지도 못한다(목적지를 나누기 전 동작이 그랬다).
    _upload.require_any_upload_group(settings, principal.groups)
    audit = _audit(request)
    meta = await _upload.stage_upload(settings, principal.subject, file)
    audit.record(principal=principal.subject, event="upload_stage", status="ok",
                 meta={"filename": meta["filename"], "size": meta["size"], "ext": meta["ext"]})
    # path 는 내부용 — 응답에 내보내지 않는다.
    out = {k: v for k, v in meta.items() if k != "path"}
    # 되묻기(B)의 입력 — 이 사용자·이 확장자로 고를 수 있는 목적지. 빈 배열이면
    # 프론트가 "보낼 곳이 없다" 를 띄운다. 조용히 아무 데나 보내지 않는다.
    out["destinations"] = _upload.allowed_destinations(settings, principal.groups, meta["ext"],
                                                       await _upload.gateway_tool_names(settings))
    return out


@router.get("/upload/exts")
async def upload_exts(
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """화면의 파일 고르기 · 끌어 놓기 목록에 더할 확장자 — 이 사람이 어딘가로 보낼 수 있는 것. 화면 목록은 빌드 때 정해져 박스 설정으로
    정하는 확장자(SimFlow — SIMFLOW_UPLOAD_EXTS)를 몰랐다(docs/request-1027 HP-15). 보낼 곳이 없으면 빈 목록이다."""
    return {"exts": _upload.upload_exts(settings, principal.groups, await _upload.gateway_tool_names(settings))}


async def _upload_register(request, principal, settings, body, dry_run: bool):
    """스테이징 CSV 를 파싱해 물성 등록(dry_run 또는 확정)을 사용자 PAT 로 호출한다."""
    _upload.require_upload_group(settings, principal.groups)
    path = _upload.staged_path(settings, principal.subject, body.staging_id, body.filename)
    parsed = _upload.parse_tensile_csv(path)
    if not parsed.get("parsed"):
        return {"stage": "parse", **parsed}   # 열 매핑 실패 — 프론트가 사용자에게 매핑을 묻는다
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("업로드용 자격증명을 발급하지 못했습니다.", status_code=403)

    # 재료가 없으면 먼저 등록(확정 때만). dry_run 미리보기는 기존 material_id 없이도 곡선만 계산.
    mid = body.material_id
    if not dry_run and mid is None:
        if not body.material_name.strip():
            raise AuthError("material_name 이 필요합니다(새 재료).", status_code=422)
        matr = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_material",
                                      {"name": body.material_name, "category": body.category})
        mid = matr.get("material_id")
        if mid is None:
            return {"stage": "material", "error": matr.get("error") or matr.get("message"), "detail": matr}
    # dry_run 은 material_id 가 있어야 곡선 계산이 된다 — 없으면 임시로 등록 안 하고
    # material_id=0 을 못 쓰므로, 기존 재료 지정이 없으면 미리보기용으로 register_material dry_run 만.
    if dry_run and mid is None:
        # 재료 미리보기(저장 안 함) + 곡선은 material_id 필요 → 곡선 계산은 확정 시로 안내.
        matr = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_material",
                                      {"name": body.material_name or "(미정)", "category": body.category,
                                       "dry_run": True})
        return {"stage": "preview", "material_preview": matr, "curve": {"n_points": parsed["n_points"],
                "strain_col": parsed["strain_col"], "stress_col": parsed["stress_col"]},
                "note": "기존 재료를 지정하면 곡선 물성(E·항복·UTS) 미리보기가 나옵니다. "
                        "새 재료면 확정 시 재료 등록 후 곡선이 계산됩니다."}

    tool_args = {"material_id": mid, "strain": parsed["strain"], "stress_mpa": parsed["stress_mpa"],
                 "gauge_length_mm": body.gauge_length_mm, "width_mm": body.width_mm,
                 "thickness_mm": body.thickness_mm, "dry_run": dry_run}
    out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "register_tensile_test", tool_args)
    return {"stage": "preview" if dry_run else "committed", "material_id": mid, **out}


# 개발단계 — 프론트 드롭다운과 같은 목록. 여기 없는 값은 버린다(집계 가능하게 유지).
_STEP_STAGES = ("선행", "DV", "PV", "양산")


class UploadDispatchReq(BaseModel):
    """되묻기(B)에서 사용자가 고른 목적지로 스테이징 파일을 보낸다.

    ⚠ **문자열마다 상한을 건다.** 바로 위 `DocxMessage` 에 똑같은 흉터 주석이 달려 있는데
    여기만 비어 있었다 — 2MB 짜리 `purpose` 가 그대로 통과했다(실측). 이 값들은 다른 앱의
    과제 메타로 **저장되므로**, 상한이 없으면 우리가 남의 저장소를 부풀리는 통로가 된다.
    """
    model_config = {"extra": "ignore"}
    staging_id: str = Field(max_length=200)
    filename: str = Field(max_length=400)
    destination: str = Field(max_length=64)    # DESTINATIONS 의 id
    # stepforge 전용 — 새 과제를 만들거나(project_name) 기존 과제에 붙인다(project_id).
    project_id: str = Field(default="", max_length=200)
    project_name: str = Field(default="", max_length=200)
    run: str = "parse"                 # parse|pipeline|detect|mesh|none — 등록 후 돌릴 잡
    # 과제 메타 — **새 과제일 때만** 쓴다. 기존 과제에 파일 하나 붙였다고 그 과제의 메타를
    # 덮어쓰는 건 남의 기록을 지우는 일이다. 담당자(owner)는 묻지 않는다 — 포탈이 안다.
    code: str = Field(default="", max_length=120)          # 과제번호
    department: str = Field(default="", max_length=120)    # 부서
    purpose: str = Field(default="", max_length=4000)      # 해석목적(자유 문장)
    note: str = Field(default="", max_length=4000)         # 특이사항
    stage: str = Field(default="", max_length=40)          # 개발단계 — 선행|DV|PV|양산
    # reportarchive_precise 전용 — 그림을 VLM 으로 판독해 '모델 판독' 블록을 단다(목적지 이름이 '그림 판독' 을 말한다 — 기본 켬).
    vlm: bool = True


@router.get("/upload/destinations/stepforge/projects")
async def upload_stepforge_projects(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """되묻기 화면에 띄울 StepForge 기존 과제 목록. 새 과제/기존 과제를 고르게 한다."""
    _upload.require_destination_group(settings, principal.groups, "stepforge")
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "list_projects", {})
    return out


@router.post("/upload/dispatch")
async def upload_dispatch(
    request: Request,
    body: UploadDispatchReq,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """고른 목적지로 스테이징 파일을 넘긴다.

    ⚠ 목적지 권한을 **여기서 다시 판정한다** — /upload 응답의 destinations 는 참고용이고
    클라이언트가 destination 문자열을 바꿔 보낼 수 있다.

    ⚠ **중간에 끊겨도 감사는 남는다.** 각 분기는 도구를 여러 번 부르고 마지막에 한 줄을
    남기는데, 중간 호출이 502 를 던지면 그 줄에 못 닿는다. 그 시점에 **이미 일어난
    부작용**이 있다 — DynaForge 세션 생성, RA 의 pptx 반입, StepForge 파일 첨부.
    그러면 남의 앱에는 데이터가 있는데 우리 원장에는 아무것도 없다(= 관측 불가).
    실패를 감싸 한 줄 남긴다 — `judge` 로 바꾸기 전에는 실패가 `created:true` 로
    위장돼 (틀리게라도) 감사가 남았다(7차 감사).
    """
    return await _dispatch_audited(request, body, principal, settings)


_RA_SIZE_HINT = "사진을 압축하거나 나눠 보내거나, 'AI 데이터 허브 — 지식카드로 변환' 으로 보내세요."


def _pptx_slides(path) -> int | None:
    """pptx 의 쪽 수(ppt/slides/slideN.xml) — 실패 기록용. 못 읽으면 None."""
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
    except (OSError, zipfile.BadZipFile, ValueError):
        return None


def _ra_reason(detail) -> tuple[str, str]:
    """RA 거절 본문 → (code, message). FastAPI 꼴({"detail": "…"} · {"detail": {"code", "message"}}) · {"error": …} · 글을 다 읽는다."""
    d = detail.get("detail", detail) if isinstance(detail, dict) else detail
    if isinstance(d, dict):
        code = str(d.get("code") or d.get("error_code") or "")
        msg = d.get("message") or d.get("msg") or d.get("error") or d.get("text") or ""
        if not msg and isinstance(d.get("detail"), str):
            msg = d["detail"]
        return code[:60], str(msg)[:300]
    if isinstance(d, list) and d and isinstance(d[0], dict):        # FastAPI 검증 오류
        return "validation", str(d[0].get("msg") or "")[:300]
    return "", str(d or "")[:300]


async def _dispatch_audited(request, body, principal, settings) -> dict:
    try:
        out = await _dispatch_inner(request, body, principal, settings)
    except Exception as exc:  # noqa: BLE001 — 남기고 그대로 올린다
        try:
            _audit(request).record(
                principal=principal.subject, event="upload_dispatch", status="failed",
                meta={"destination": body.destination, "filename": body.filename,
                      "error": f"{type(exc).__name__}: {exc}"[:300]})
        except Exception:  # noqa: BLE001 — 감사 실패가 원래 오류를 가리면 안 된다
            logger.warning("업로드 실패 감사 기록 실패", exc_info=True)
        raise
    if isinstance(out, dict) and out.get("stage") == "failed":
        # 상대가 거절해 돌려준 실패(예외가 아니다)도 남긴다 — RA 400 은 200 으로 끝나 감사에 upload_stage 두 줄만 남았다(docs/request-1027
        # HP-03). 본문은 싣지 않는다 — 상대 상태 · 오류 코드 · 크기 · 쪽 수만. 서버 로그에도 한 줄(파일 이름은 빼고).
        size = None
        try:
            size = _upload.staged_path(settings, principal.subject, body.staging_id, body.filename).stat().st_size
        except (OSError, AuthError):
            pass
        slides = out.get("slides")
        meta = {"destination": body.destination, "filename": body.filename, "size": size,
                "error": str(out.get("error") or "")[:200]}
        for k in ("ra_status", "ra_code", "slides", "sf_status"):
            if out.get(k) is not None:
                meta[k] = out[k]
        try:
            _audit(request).record(principal=principal.subject, event="upload_dispatch", status="failed", meta=meta)
        except Exception:  # noqa: BLE001
            logger.warning("업로드 실패 감사 기록 실패", exc_info=True)
        logger.warning("upload dispatch failed: dest=%s size=%s slides=%s ra_status=%s ra_code=%s", body.destination, size, slides,
                       out.get("ra_status"), out.get("ra_code") or "-")
    return out


async def _ra_user_token(request, settings: Settings, principal: Principal) -> tuple[str, bool, dict]:
    """RA 에 그 사람 명의로 부를 토큰 — (토큰, 위임으로 받았나, 외부 연결 기록). RA_SSO_SECRET 이 있으면 포털이 그 자리에서 받고
    (ste 방식, docs/sso-delegation), 없거나 못 받으면 '외부 연결' 에 등록해 둔 토큰이다. 둘 다 없으면 무엇을 고칠지 말한다."""
    email = principal.email or principal.subject
    conn = request.app.state.user_store.get_connection(email=email, service="reportarchive") or {}
    token = None
    if settings.ra_sso_secret:
        token = await ra_sso.ra_user_token(settings, email=email, name=principal.display_name or "")
    via_sso = bool(token)
    token = token or conn.get("token")
    if not token:
        if settings.ra_sso_secret:
            raise AuthError(
                "Report Archive 가 본인 명의 토큰을 내주지 않았습니다(포털 위임) — RA 쪽 위임 상태"
                "(HEAX_SSO_SECRET·그 계정)를 RA 담당에게 확인하세요. 포털 서버 로그 hwax.ra_sso 에 이유가 있습니다.",
                status_code=502)
        raise AuthError(
            "Report Archive 연결이 없습니다 — 포털 '개인 토큰 › 외부 연결'(/tokens?tab=connect)에서 RA 토큰을 먼저 등록하세요.",
            status_code=400)
    return token, via_sso, conn


def _sf_fields(j) -> tuple[str, str]:
    """SimFlow 업로드 응답 → (id, 상태). 감싼 꼴(data)도 받는다 — 칸 이름은 SimFlow 쪽 확인(PA-12) 전이다."""
    d = j.get("data") if isinstance(j, dict) and isinstance(j.get("data"), dict) else j
    if not isinstance(d, dict):
        return "", ""
    return str(d.get("id") or d.get("upload_id") or ""), str(d.get("status") or d.get("state") or "")


def _sf_failed(r: httpx.Response) -> dict:
    """SimFlow(또는 게이트웨이 다리)가 받지 않은 응답 → 사람이 알아듣는 실패. 상대가 밝힌 사유를 그대로 붙인다."""
    try:
        detail = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text[:400]}
    except ValueError:
        detail = {"text": r.text[:400]}
    raw = ""
    if isinstance(detail, dict):
        raw = detail.get("detail") or detail.get("message") or detail.get("error") or detail.get("text") or ""
    msg = (raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False))[:300]
    code = r.status_code
    out: dict = {"stage": "failed", "destination": "simflow", "sf_status": code, "detail": detail}
    if code == 413:
        out["error"] = f"SimFlow 가 크기 한도로 받지 않았습니다(HTTP 413){' — ' + msg if msg else ''}."
        out["hint"] = "파일을 나누거나 SimFlow 화면에서 직접 올리세요."
    elif code == 401:
        # 위층(SimFlow)이 거절했으면 게이트웨이가 캐시 토큰을 버리고 이 머리를 단다 — 한 번 다시 보내고도 401 이면 여기다(HG-04).
        out["error"] = ("SimFlow 가 자격을 받지 않았습니다(HTTP 401) — 새로 받은 토큰도 거절됐습니다. 관리자에게 SimFlow 사람별 연결을 확인해 "
                        "달라고 하세요." if r.headers.get("x-gateway-token-evicted") == "1"
                        else "게이트웨이가 이 보내기의 자격을 받지 않았습니다(HTTP 401) — 포털에서 다시 로그인한 뒤 보내세요.")
    elif code == 403:
        out["error"] = f"SimFlow 로 보낼 권한이 없습니다(HTTP 403){' — ' + msg if msg else ''}."
    elif code == 404:
        out["error"] = ("SimFlow 업로드 길이 없습니다(HTTP 404) — 게이트웨이에 SimFlow REST 다리가 없거나(관리자: update-all 재프로비저닝) "
                        "SimFlow 가 이 경로를 모릅니다.")
    else:
        out["error"] = f"SimFlow 가 받지 않았습니다(HTTP {code}){' — ' + msg if msg else '.'}"
    return out


async def _dispatch_simflow(request, body, principal, settings, path: Path) -> dict:
    """SimFlow 워크플로우 입력(docs/request-1027 HP-15) — 게이트웨이 REST 다리로 흘려 보낸다. 게이트웨이가 그 사람의 SimFlow 토큰(사람별
    위임)으로 넣는다(감사 mode=as-user-pat). DRM 원본은 그대로 보낸다 — SimFlow 가 drm_pending → ready 로 푼다(그동안 기다린다)."""
    mx = _upload.dest_max_bytes(settings, "simflow")
    size = path.stat().st_size
    if mx and size > mx:
        raise AuthError(f"SimFlow 업로드 한도 {mx // (1024 * 1024)} MB 를 넘습니다({size / (1024 * 1024):.1f} MB) — "
                        "파일을 나누거나 SimFlow 화면에서 직접 올리세요.", status_code=413)
    wait = max(0, int(settings.simflow_ready_wait_s or 0))
    tok = _site_pat(request.app.state.keystore, settings, principal, "simflow", ttl_s=600 + wait + 300)
    if not tok:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    url = settings.mcp_gateway_url.rstrip("/") + "/api/simflow/api/v1/mcp-uploads"
    hdrs = {"Authorization": f"Bearer {tok}"}

    async def _post() -> httpx.Response:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=10)) as cli:
            with path.open("rb") as fh:
                return await cli.post(url, headers=hdrs, files={"file": (body.filename, fh, "application/octet-stream")})

    async def _get(uid: str) -> httpx.Response:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as cli:
            return await cli.get(f"{url}/{quote(uid, safe='')}", headers=hdrs)

    def _evicted(r: httpx.Response) -> bool:
        return r.status_code == 401 and r.headers.get("x-gateway-token-evicted") == "1"

    try:
        r = await _post()
        if _evicted(r):
            # 게이트웨이가 캐시한 SimFlow 토큰을 SimFlow 가 거절했다 — 캐시는 버렸고, 흘려 보낸 본문이라 게이트웨이 안에서는 다시 보내지
            # 않는다(HG-04). 인증에서 끊겨 아무것도 넣지 않았으니 한 번만 다시 보낸다.
            r = await _post()
    except httpx.HTTPError as exc:
        return {"stage": "failed", "destination": "simflow", "error": f"SimFlow 에 연결하지 못했습니다({exc.__class__.__name__})."}
    if r.status_code >= 400:
        return _sf_failed(r)
    try:
        j = r.json()
    except ValueError:
        j = {}
    uid, st = _sf_fields(j)
    if not uid:
        return {"stage": "failed", "destination": "simflow", "detail": j if isinstance(j, dict) else {"text": r.text[:400]},
                "error": "SimFlow 가 업로드 id 를 돌려주지 않았습니다 — 들어갔는지 SimFlow 화면에서 확인하세요."}
    loop = asyncio.get_running_loop()
    until = loop.time() + wait
    while st == "drm_pending" and loop.time() < until:
        await asyncio.sleep(2)
        try:
            g = await _get(uid)
            if _evicted(g):
                g = await _get(uid)
        except httpx.HTTPError:
            continue                                   # 상태 보기가 잠깐 안 닿는다 — 기다림 안에서 다시 본다
        if g.status_code >= 400:
            break                                      # 상태를 볼 길이 없다 — 받은 상태 그대로 알린다
        try:
            _nid, nst = _sf_fields(g.json())
        except ValueError:
            break
        st = nst or st
    _audit(request).record(principal=principal.subject, event="upload_dispatch",
                           meta={"destination": "simflow", "upload_id": uid, "status": st, "size": size})
    out = {"stage": "done", "destination": "simflow", "upload_id": uid, "upload_status": st, "size": size,
           "result": j if isinstance(j, dict) else {}}
    if st == "drm_pending":
        out["note"] = (f"SimFlow 가 DRM 을 아직 풀고 있습니다({wait}초 기다림) — ready 가 되면 이 id 로 run_workflow 를 부르세요."
                       if wait else "SimFlow 가 DRM 을 푸는 중입니다 — ready 가 되면 이 id 로 run_workflow 를 부르세요.")
    return out


async def _dispatch_inner(request, body, principal, settings) -> dict:
    _upload.require_destination_group(settings, principal.groups, body.destination)
    audit = _audit(request)
    path = _upload.staged_path(settings, principal.subject, body.staging_id, body.filename)
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)

    if body.destination == "simflow":
        return await _dispatch_simflow(request, body, principal, settings, path)

    if body.destination == "reportarchive":
        # ── Report Archive ────────────────────────────────────────────
        # **RA 의 파서를 그대로 쓴다**(포털에 python-pptx 를 넣지 않는다). RA 의 웹 '가져오기'
        # 와 같은 엔드포인트라 그림·표까지 위젯으로 들어온다. 그 사람 명의 토큰으로 부르므로
        # 권한·워크스페이스가 그 사람 것이다(_ra_user_token).
        email = principal.email or principal.subject
        # 크기 한도를 넘으면 RA 를 부르지 않는다 — 10-23 의 116쪽 · 45 MB 가 업로드를 다 한 뒤 400 '파일이 너무 큽니다.' 였다(HP-02).
        mx = _upload.dest_max_bytes(settings, "reportarchive")
        size = path.stat().st_size
        if mx and size > mx:
            raise AuthError(f"Report Archive 가져오기 한도 {mx // (1024 * 1024)} MB 를 넘습니다({size / (1024 * 1024):.1f} MB) — "
                            + _RA_SIZE_HINT, status_code=413)
        token, via_sso, conn = await _ra_user_token(request, settings, principal)

        async def _post_pptx(tok: str) -> httpx.Response:
            hdrs = {"Authorization": f"Bearer {tok}"}
            # 부서는 RA 가 그 사람의 홈 부서로 정한다(ra-request §3) — 사람이 '외부 연결' 에서 고른 조직이 있을 때만 싣는다.
            # ⚠ 위임 토큰(via_sso)으로 부를 때도 싣는 것은 **일부러 둔 것**이다(9차 요청 §6 의 질문, docs/change-request-8-10 D-7).
            #   게이트웨이가 같은 상황에서 이 헤더를 지우는 것(strip_headers)과 대상이 다르다 — 거기서 지우는 것은 설정에 박힌
            #   **서비스 계정**의 부서이고, 여기서 싣는 것은 **그 사람**의 연결에 저장된 부서다(고른 값이거나 등록 때 '조직 먼저' 로
            #   채워진 값). 지금 빼면 RA 의 홈이 개인함인 사람의 PPT 가 개인함으로 가거나 400 이 된다. RA 가 '헤더가 없으면 홈 부서' 를
            #   보장하는 것이 확인되면 위임일 때는 뺀다 — 지금 동작은 test_ra_sso 가 고정한다.
            if conn.get("workspace"):
                hdrs["X-Workspace-Slug"] = conn["workspace"]
            async with httpx.AsyncClient(timeout=600) as cli:
                with path.open("rb") as fh:
                    return await cli.post(
                        settings.ra_base_url.rstrip("/") + "/api/imports/pptx",
                        headers=hdrs,
                        files={"file": (body.filename, fh,
                                        "application/vnd.openxmlformats-officedocument."
                                        "presentationml.presentation")})

        try:
            r = await _post_pptx(token)
            if r.status_code == 401 and via_sso:
                # 캐시해 둔 위임 토큰을 RA 가 거절했다(회수·비밀 교체). 인증에서 끊겨 아무것도 안 했으니 한 번만
                # 새로 받아 다시 보낸다 — 게이트웨이와 같은 규칙. 안 그러면 캐시 수명(최대 11시간) 동안 계속 401 이다.
                ra_sso.forget(email)
                fresh = await ra_sso.ra_user_token(settings, email=email, name=principal.display_name or "")
                if fresh:
                    r = await _post_pptx(fresh)
        except httpx.HTTPError as exc:
            return {"stage": "failed", "error": f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__})."}
        if r.status_code >= 400:
            try:
                detail = (r.json() if r.headers.get("content-type", "").startswith("application/json")
                          else {"text": r.text[:400]})
            except ValueError:
                detail = {"text": r.text[:400]}
            # RA 가 밝힌 사유(message · code)를 그대로 보인다 — 종전엔 'HTTP n' 만 남기고 사유를 버려 '파일이 너무 큽니다.' 가 화면에 안 떴다(HP-02).
            code, msg = _ra_reason(detail)
            out = {"stage": "failed", "detail": detail, "ra_status": r.status_code, "ra_code": code or None,
                   "slides": _pptx_slides(path),
                   "error": f"Report Archive 가 받지 않았습니다(HTTP {r.status_code}{' · ' + code if code else ''})"
                            + (f" — {msg}" if msg else ".")}
            if r.status_code == 413 or re.search(r"(너무 큽|크기|too large|쪽 수|페이지 수|슬라이드 수|이미지 수|그림 수|pages?|slides?)", msg, re.I):
                out["hint"] = _RA_SIZE_HINT
            return out
        body_j = r.json()
        draft = ((body_j.get("data") or body_j).get("draft")) or {}
        warns = (body_j.get("data") or body_j).get("warnings") or []
        pages = draft.get("pages") or []
        if not pages:
            return {"stage": "failed", "error": "가져올 내용이 없습니다(텍스트·표·그림을 못 찾음).",
                    "detail": {"warnings": warns}}
        # 가져오기 쪽(저장 꼴)을 AI 초안 입력 꼴로 — 그대로 넘기면 RA 가 블록마다 '내용 없음' 으로 버려 블록 0 인 보고서가 됐다
        # (10-22 cae00 29쪽 · 블록 0, docs/chat-ppt PP-D2). 블록이 하나도 없으면 빈 보고서를 RA 에 남기지 않는다.
        ai_pages, n_blocks = _upload.ra_import_pages_to_ai(pages)
        if not n_blocks:
            return {"stage": "failed", "error": "가져온 쪽에 블록이 하나도 없습니다 — 보고서를 만들지 않았습니다(텍스트·표·그림을 못 찾음).",
                    "detail": {"warnings": warns, "pages": len(pages)}}
        # 변환 결과를 보고서 초안으로. __import_blank__ 은 필수 블록이 없어 문서를 그대로 담는다
        # (RA 웹 가져오기가 쓰는 그 템플릿이다 — 처음 쓰일 때 생성된다).
        out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "create_report_draft", {
            "template_id": "__import_blank__", "template_version": 1,
            "title": (draft.get("title") or Path(body.filename).stem)[:200],
            "blocks": {}, "pages": ai_pages,
        })
        rid = out.get("report_id") if isinstance(out, dict) else None
        if not rid:
            return {"stage": "failed", "error": "Report Archive 가 보고서 번호를 돌려주지 않았습니다 — 만들어졌는지 RA 에서 확인하세요.",
                    "detail": out}
        ra_warns = [f"RA: {w}" for w in (out.get("warnings") or []) if isinstance(w, str)]
        audit.record(principal=principal.subject, event="upload_dispatch",
                     meta={"destination": "reportarchive", "pages": len(pages), "blocks": n_blocks, "report_id": rid})
        return {"stage": "done", "destination": "reportarchive", "created": True,
                "pages": len(pages), "blocks": n_blocks, "report_id": rid,
                "title": out.get("title"), "url": out.get("url"),
                "warnings": [*warns, *ra_warns], "result": out}

    if body.destination == "reportarchive_precise":
        # ── Report Archive 정밀 변환(DocForge) ─────────────────────────
        # 파일 본문은 MCP 로 나르지 않는다 — 스테이징의 **호스트 경로**를 넘긴다(StepForge 와 같은 꼴 · DocForge 의
        # DOCFORGE_INPUT_ROOTS 에 스테이징 호스트 경로가 있어야 한다). 변환은 잡이라 기다리지 않는다 — 화면이 진행을 보다가
        # 끝나면 deliver 를 부른다(포털이 그 사람 명의로 RA 에 엄격 생성, DF-D17). 맡긴 사람을 기록해 진행 · 배달을 그 사람에게만.
        src = _upload.host_path(settings, path)
        slides: list[Path] = []
        bundle_box: Path | None = None
        if path.suffix.lower() == ".md":
            # PC 도우미 추출본(DRM 문서 — DocForge R-D35 · DF-D18). 추출기가 만든 글만 받는다. 받을 때 슬라이드 그림도 왔으면 글과 함께
            # zip 하나로 묶어 넘긴다 — 글 상자가 아니라 새 상자에(staged_path 가 상자의 첫 파일을 집는다), DocForge 가 받아 간 뒤 지운다.
            try:
                await asyncio.to_thread(_pc.check_doc, path.read_bytes())
            except ValueError as exc:
                return {"stage": "failed", "error": f"PC 도우미가 만든 .hwax.md 만 정밀 변환할 수 있습니다 — {exc}"}
            slides = await asyncio.to_thread(_pc.slides_of, settings, principal.subject, body.staging_id)
            if slides:
                bundle_box = _upload._user_dir(settings, principal.subject) / uuid.uuid4().hex
                bundle_box.mkdir(parents=True)
                arc = path.name if path.name.endswith(".hwax.md") else f"{path.stem}.hwax.md"   # DocForge 는 zip 안의 *.hwax.md 를 찾는다
                zp = bundle_box / (arc.removesuffix(".hwax.md") + ".hwax.zip")

                def _pack() -> None:
                    with zipfile.ZipFile(zp, "w") as zf:
                        zf.write(path, arcname=arc)
                        for s in slides:
                            zf.write(s, arcname=s.name)

                await asyncio.to_thread(_pack)
                src = _upload.host_path(settings, zp)
        try:
            out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_convert",
                                         {"path": src, "parser": "auto", "vlm": bool(body.vlm)})
        finally:
            if bundle_box is not None:                 # DocForge 는 맡을 때 입력을 제 잡 폴더로 옮겨 둔다(링크 또는 복사)
                shutil.rmtree(bundle_box, ignore_errors=True)
        job_id = str(out.get("job_id") or "").strip() if isinstance(out, dict) else ""
        if not job_id or out.get("ok") is False:
            return {"stage": "failed", "error": f"DocForge 가 변환을 맡지 않았습니다 — {out.get('error') or '잡 번호 없음'}",
                    "detail": out}
        _dfd.save_job(settings, job_id, owner_sub=principal.subject, owner_email=principal.email or principal.subject,
                      filename=body.filename)
        audit.record(principal=principal.subject, event="upload_dispatch",
                     meta={"destination": "reportarchive_precise", "filename": body.filename, "job_id": job_id,
                           "vlm": bool(body.vlm), "slides": len(slides)})
        return {"stage": "dispatched", "destination": "reportarchive_precise", "job_id": job_id,
                "next": "GET /agent/upload/destinations/docforge/jobs/{job_id} 로 진행을 보고, 끝나면 POST …/deliver"}

    if body.destination == "chat" and "plat:docforge" in (principal.groups or []):
        # ── 이 대화에서 분석 — DocForge(DF-D19) ─────────────────────────
        # DocForge 가 보이는 사람은 DocForge 로 읽는다 — 차트 값(원본 캐시) · SmartArt · 수식 · 발표자 노트 · 병합 표까지 원문에서. 그림 판독은
        # 하지 않는다(대화에서 바로 묻는 길이라 빨라야 한다 · stcx Qwen 을 챗과 나눠 쓴다). 잡이라 화면이 진행을 보다가 끝나면 …/document 로
        # 글을 받아 문서 칩으로 붙인다. DocForge 가 맡지 않으면(게이트웨이에 없음 · 거절) 아래 지금 길로 간다.
        try:
            out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_convert",
                                         {"path": _upload.host_path(settings, path), "parser": "auto", "vlm": False})
        except AuthError as exc:
            out = {"ok": False, "error": exc.message}
        job_id = str(out.get("job_id") or "").strip() if isinstance(out, dict) else ""
        if job_id and out.get("ok") is not False:
            _dfd.save_job(settings, job_id, owner_sub=principal.subject, owner_email=principal.email or principal.subject,
                          filename=body.filename, purpose="chat")
            audit.record(principal=principal.subject, event="upload_dispatch",
                         meta={"destination": "chat", "via": "docforge", "filename": body.filename, "job_id": job_id})
            return {"stage": "dispatched", "destination": "chat", "via": "docforge", "job_id": job_id}
        logger.info("이 대화에서 분석 — DocForge 가 맡지 않아 AI 데이터 허브 변환기로 간다(%s)", str(out.get("error") or "잡 번호 없음")[:120])

    if body.destination == "chat":
        # ── 이 대화에서 분석 ─────────────────────────────────────────
        # 어디에도 저장하지 않는다 — AI 데이터 허브의 변환기를 그 사람 명의로 빌려 글 · 목록 · 표 · 차트 데이터 · 발표자 노트를
        # .hwax.md 로 옮겨 돌려주면 화면이 문서 칩으로 붙인다(PC 도우미 · 손 추출과 같은 끝, docs/chat-ppt PP-D17). 변환기는 inbox
        # 하위만 읽으므로 거기 잠시 두고, 변환이 끝나면(실패해도) 지운다 — AI 데이터 허브로 보낸 같은 이름의 파일과 겹치지 않게 이름을 가른다.
        inbox = Path(os.environ.get("AIDH_CONVERT_INBOX") or (Path.home() / "aidh-inbox"))
        inbox.mkdir(parents=True, exist_ok=True)
        safe = Path(body.filename).name
        dest = inbox / f"{principal.subject.split('@')[0][:24]}-chat-{uuid.uuid4().hex[:8]}-{safe}"
        shutil.copy2(path, dest)
        try:
            out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "convert_file", {"file": dest.name})
        finally:
            dest.unlink(missing_ok=True)
        record = out.get("record") if isinstance(out, dict) else None
        if not isinstance(record, dict) or not record.get("sections"):
            return {"stage": "failed", "error": "문서에서 읽을 내용을 찾지 못했습니다(글 · 표가 없거나 변환기가 처리하지 못한 구조).",
                    "detail": out}
        meta = record.get("meta") if isinstance(record.get("meta"), dict) else None
        if meta is not None and " ".join(str(meta.get("title") or "").split()) == dest.stem:
            # 변환기는 제목이 없으면 inbox 임시 이름(<계정>-chat-<8자>-…)을 제목으로 쓴다 — 칩의 H1 에 계정이 드러나 모델이 인용했다(HP-30)
            record = {**record, "meta": {**meta, "title": Path(safe).stem}}
        text = _upload.record_markdown(record, body.filename)
        name = f"{Path(safe).stem}.hwax.md"
        audit.record(principal=principal.subject, event="upload_dispatch",
                     meta={"destination": "chat", "filename": body.filename, "chars": len(text)})
        return {"stage": "done", "destination": "chat", "doc": {"name": name, "text": text, "chars": len(text)}}

    if body.destination == "aidatahub":
        # ── AI 데이터 허브 ────────────────────────────────────────────
        # convert_file 은 **inbox 하위만** 변환한다(경로/.. 불가). 스테이징 파일을 거기로
        # 복사하고 파일명만 넘긴다. 저장은 여기서 하지 않는다 — 모자란 항목을 사람에게
        # 되묻는 것이 import_record 의 규약이라, 그 확인을 챗에 남긴다.
        inbox = Path(os.environ.get("AIDH_CONVERT_INBOX") or (Path.home() / "aidh-inbox"))
        inbox.mkdir(parents=True, exist_ok=True)
        safe = Path(body.filename).name
        dest = inbox / f"{principal.subject.split('@')[0][:24]}-{safe}"
        shutil.copy2(path, dest)
        # 바로 지우지 않는다 — 모델이 그 이름으로 convert_file 을 다시 부를 수 있다(알림이 이름을 남긴다). 장부에 적어 두면 청소가
        # aidh_inbox_ttl_hours 뒤에 지운다(HP-29 — 종전엔 아무도 안 지웠다).
        _upload.aidh_inbox_note(settings, dest.name)
        out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "convert_file",
                                     {"file": dest.name})
        audit.record(principal=principal.subject, event="upload_dispatch",
                     meta={"destination": "aidatahub", "file": dest.name})
        return {"stage": "done", "destination": "aidatahub", "inbox_name": dest.name,
                "result": out}

    if body.destination == "dynaforge":
        # ── DynaForge ────────────────────────────────────────────────
        # 세션이 모든 작업의 컨테이너다(create_session 이 첫 도구). 파일 본문은 안 나른다 —
        # LS-DYNA 덱은 수십 MB 가 흔해 upload_kfile(content) 로는 못 싣는다. StepForge 와 같이
        # **호스트 경로**를 넘겨 upload_local_path 가 직접 읽게 한다.
        src = _upload.host_path(settings, path)
        name = (body.project_name or "").strip() or Path(body.filename).stem
        sess = await _upload.mcp_call(settings.mcp_gateway_url, pat, "create_session", {
            "name": name[:120],
            "description": f"포탈 챗 업로드 · {principal.subject}",
        })
        sid = str(sess.get("session_id") or sess.get("id") or "").strip()
        if not sid:
            return {"stage": "failed", "error": "DynaForge 세션을 만들지 못했습니다.", "detail": sess}
        out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "upload_local_path", {
            "session_id": sid, "path": src, "filename": body.filename,
        })
        audit.record(principal=principal.subject, event="upload_dispatch",
                     meta={"destination": "dynaforge", "session_id": sid})
        return {"stage": "done", "destination": "dynaforge", "session_id": sid,
                "created": True, "result": out}

    if body.destination != "stepforge":
        # material 은 파싱·미리보기가 필요해 기존 analyze/commit 경로를 그대로 쓴다.
        raise AuthError(
            f"'{body.destination}' 은 dispatch 로 보내지 않습니다 — 전용 경로를 쓰세요.",
            status_code=400,
        )

    # ── StepForge ────────────────────────────────────────────────
    # ⚠ 컨테이너 경로가 아니라 **호스트 경로**를 넘긴다 — StepForge 는 다른 컨테이너다.
    #   apptainer 가 $HOME 을 자동 마운트해 같은 절대경로로 보인다(실측 확인).
    #   파일 본문은 MCP 로 나르지 않는다 — 693MB 급을 페이로드에 못 싣는다(StepForge PLAN §8).
    src = _upload.host_path(settings, path)
    run = body.run if body.run in ("parse", "detect", "mesh", "pipeline", "none") else "parse"
    pid = (body.project_id or "").strip()
    created = False
    # 개발단계는 StepForge 정규 컬럼이 아니라 자유 항목(extras)이다. 값을 고정된 목록으로
    # 묶어야 나중에 "DV 과제만" 같은 집계가 된다 — 자유 문자열이면 집계가 안 된다.
    # 안 고른 것은 아예 넣지 않는다(빈 문자열을 남기면 '값이 있는데 빈 것'과 구분이 안 된다).
    extras: dict = {"source": "포탈 챗 업로드"}
    if body.stage.strip() in _STEP_STAGES:
        extras["stage"] = body.stage.strip()

    if not pid:
        # 새 과제 — `intake` 하나로 과제 생성·메타·등록(zip 이면 압축 해제)·잡까지 끝난다.
        # StepForge 가 포탈 반입을 위해 만든 도구다("포탈 신원 자동 기입", c8fab07).
        # ⚠ 도구 존재는 **게이트웨이 tools/list 로 확인한다.** 소스에 있다고 쓸 수 있는 게
        #   아니다 — 2026-09-01 첫 e2e 가 "unknown tool: intake" 로 터졌다. SIF 가 커밋보다
        #   낡았을 때 그렇다(그때는 묶음을 펴서 우회했다). 지금은 재배포돼 살아 있고,
        #   메타를 담는 set_project_meta 도 같은 커밋이라 어차피 이 배포에 의존한다.
        out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "intake", {
            "path": src,
            "name": (body.project_name or "").strip() or Path(body.filename).stem,
            "owner": principal.subject,       # 묻지 않는다 — 로그인한 사람이 담당자다
            "code": body.code.strip(),
            "department": body.department.strip(),
            "purpose": body.purpose.strip(),
            "note": body.note.strip(),
            "extras": extras,
            "run": run,
        })
        pid = str(out.get("project_id") or "").strip()
        job_id = out.get("job_id")
        created = True
        if not pid:
            return {"stage": "failed", "error": "StepForge 과제를 만들지 못했습니다.", "detail": out}
    else:
        # 기존 과제 — 과제 메타는 건드리지 않는다(파일 하나 붙였다고 남의 기록을 덮지 않는다).
        # zip 은 안에 STEP·MSH 가 여럿 들어 전용 반입기로 간다 — upload_step 은 파일 하나짜리다.
        # 같은 이름 재등록은 StepForge 가 **갱신**으로 처리하고, 잡이 도는 중 교체는 거부한다.
        tool = "import_archive" if Path(body.filename).suffix.lower() == ".zip" else "upload_step"
        out = await _upload.mcp_call(settings.mcp_gateway_url, pat, tool,
                                     {"project_id": pid, "path": src})
        job_id = None
        if run != "none":
            job = await _upload.mcp_call(settings.mcp_gateway_url, pat, "run_job",
                                         {"project_id": pid, "kind": run})
            job_id = job.get("job_id")

    audit.record(principal=principal.subject, event="upload_dispatch", status="ok",
                 meta={"destination": "stepforge", "project_id": pid,
                       "filename": body.filename, "run": run, "created": created})
    # 파싱은 잡이다 — 407MB SIF 에 파싱 피크 RSS 5.13GB 실측이라 챗 요청 안에서 기다리지 않는다
    # (매니페스트 memory_gb: 16 의 근거). job_id 로 진행을 본다.
    return {"stage": "dispatched", "destination": "stepforge", "project_id": pid,
            "created_project": created, "job_id": job_id, "kind": None if run == "none" else run,
            "next": "job_status(job_id) 로 진행을 보고, 끝나면 project_tree·list_interfaces",
            "result": out}


# ── Report Archive 정밀 변환 — DocForge 잡의 진행 · 배달 · 취소(docs/doc-to-ra DF-D17) ─────────────────────────────────────────
# 맡기기는 /upload/dispatch(reportarchive_precise)다. 여기 셋은 그 잡을 **맡긴 사람만** 부른다 — 기록의 주인이 아니면 '없다'.
# DocForge 도 같은 사람 PAT 로 부르므로 그쪽 원장의 주인 검사도 한 번 더 걸린다.
def _dfd_http(exc: _dfd.DeliveryError) -> AuthError:
    return AuthError(exc.message, status_code=exc.status)


@router.get("/upload/destinations/docforge/jobs/{job_id}")
async def upload_docforge_status(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """화면이 1.5초마다 본다 — status(queued · running · done · failed · cancelled) · stage · progress · error · 배달했으면 그 결과."""
    try:
        rec = _dfd.load_job(settings, job_id, principal.subject)
    except _dfd.DeliveryError as exc:
        raise _dfd_http(exc) from exc
    if rec.get("delivered"):
        return {"job_id": job_id, "status": "done", "progress": 100, "delivered": rec["delivered"]}
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_status", {"job_id": job_id}, timeout=20.0)
    if out.get("ok") is False:
        raise AuthError(f"DocForge: {out.get('error')}", status_code=int(out.get("status") or 502))
    return {"job_id": job_id, **{k: out.get(k) for k in ("status", "stage", "progress", "error")}}


@router.post("/upload/destinations/docforge/jobs/{job_id}/deliver")
async def upload_docforge_deliver(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """끝난 잡의 패키지를 그 사람 명의로 RA 에 엄격 생성한다. 한 잡은 한 번만 — 이미 넣었으면 그 결과를 그대로(두 번 눌러도 하나)."""
    try:
        rec = _dfd.load_job(settings, job_id, principal.subject)
    except _dfd.DeliveryError as exc:
        raise _dfd_http(exc) from exc
    if rec.get("purpose") == "chat":
        raise AuthError("대화에서 읽으려고 맡긴 변환입니다 — Report Archive 에 넣지 않습니다.", status_code=409)
    async with _dfd.lock(job_id):
        rec = _dfd.load_job(settings, job_id, principal.subject)
        if rec.get("delivered"):
            return {"stage": "done", "destination": "reportarchive_precise", "created": False, **rec["delivered"]}
        pat = _chat_user_pat(request.app.state.keystore, settings, principal)
        if not pat:
            raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
        pkg = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_package", {"job_id": job_id}, timeout=30.0)
        if pkg.get("ok") is False:
            return {"stage": "failed", "error": f"DocForge: {pkg.get('error')}", "detail": pkg}
        email = principal.email or principal.subject
        token, via_sso, conn = await _ra_user_token(request, settings, principal)

        async def _remint() -> str | None:
            if not via_sso:
                return None
            ra_sso.forget(email)
            return await ra_sso.ra_user_token(settings, email=email, name=principal.display_name or "")

        try:
            pdir = _dfd.package_dir(settings, pkg.get("package_rel"))
            got = await _dfd.deliver(settings, pdir, token=token, workspace=conn.get("workspace") or "", remint=_remint)
        except _dfd.DeliveryError as exc:
            _audit(request).record(principal=principal.subject, event="upload_deliver", status="failed",
                                   meta={"destination": "reportarchive_precise", "job_id": job_id, "error": exc.message[:300]})
            return {"stage": "failed", "error": exc.message}
        except httpx.HTTPError as exc:
            return {"stage": "failed", "error": f"Report Archive 에 연결하지 못했습니다({exc.__class__.__name__})."}
        result = {"job_id": job_id, "filename": rec.get("filename"), **got}
        _dfd.mark_delivered(settings, job_id, rec, result)
        _audit(request).record(principal=principal.subject, event="upload_deliver", status="ok",
                               meta={"destination": "reportarchive_precise", "job_id": job_id, "report_id": got["report_id"],
                                     "pages": got.get("pages"), "blocks": got.get("blocks"), "resources": got.get("resources")})
        return {"stage": "done", "destination": "reportarchive_precise", "created": True, **result}


@router.get("/upload/destinations/docforge/jobs/{job_id}/document")
async def upload_docforge_document(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """끝난 잡의 '챗에서 읽는 글'(document.md — hwax-doc/1 꼴) — 화면이 문서 칩으로 붙인다(이 대화에서 분석, DF-D19). 어디에도 저장하지 않는다."""
    try:
        rec = _dfd.load_job(settings, job_id, principal.subject)
    except _dfd.DeliveryError as exc:
        raise _dfd_http(exc) from exc
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    pkg = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_package", {"job_id": job_id}, timeout=30.0)
    if pkg.get("ok") is False:
        return {"stage": "failed", "error": f"DocForge: {pkg.get('error')}"}
    try:
        text = await asyncio.to_thread(_dfd.document_text, settings, pkg)
    except _dfd.DeliveryError as exc:
        return {"stage": "failed", "error": exc.message}
    name = f"{Path(rec.get('filename') or 'document').stem}.hwax.md"
    _audit(request).record(principal=principal.subject, event="upload_document", status="ok",
                           meta={"destination": "chat", "via": "docforge", "job_id": job_id, "chars": len(text)})
    return {"stage": "done", "destination": "chat", "via": "docforge", "doc": {"name": name, "text": text, "chars": len(text)}}


@router.post("/upload/destinations/docforge/jobs/{job_id}/cancel")
async def upload_docforge_cancel(
    job_id: str,
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        _dfd.load_job(settings, job_id, principal.subject)
    except _dfd.DeliveryError as exc:
        raise _dfd_http(exc) from exc
    pat = _chat_user_pat(request.app.state.keystore, settings, principal)
    if not pat:
        raise AuthError("사용자 자격증명을 만들지 못했습니다.", status_code=401)
    out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_cancel", {"job_id": job_id}, timeout=20.0)
    return {"job_id": job_id, "cancelled": bool(out.get("cancelled"))}


@router.get("/upload/destinations/docforge/jobs")
async def upload_docforge_jobs(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """맡긴 사람의 정밀 변환 잡(최근 docforge_job_days 일 · 새것부터 20 · 숨긴 것 빼고) — 창을 닫아 넣지 못한 잡을 입력창 위에서 다시 열어 넣는다
    (DocForge E15). 아직 넣지 않은 잡은 DocForge 의 지금 상태(st)를 함께 — 못 물으면 st 가 없다(화면은 그 잡을 보이지 않는다)."""
    recs = await asyncio.to_thread(_dfd.list_jobs, settings, principal.subject)
    pending = [r["job_id"] for r in recs if not r.get("delivered")]
    status: dict[str, dict] = {}
    pat = _chat_user_pat(request.app.state.keystore, settings, principal) if pending else None
    if pat:
        async def _one(jid: str) -> tuple[str, dict | None]:
            try:
                out = await _upload.mcp_call(settings.mcp_gateway_url, pat, "docforge_status", {"job_id": jid}, timeout=10.0)
            except Exception:  # noqa: BLE001 — 한 잡을 못 물어도 목록은 낸다
                return jid, None
            return jid, out if isinstance(out, dict) and out.get("ok") is not False else None

        status = {jid: {k: out.get(k) for k in ("status", "stage", "progress", "error")}
                  for jid, out in await asyncio.gather(*(_one(j) for j in pending)) if out is not None}
    jobs = []
    for r in recs:
        done = r.get("delivered")
        jobs.append({"job_id": r["job_id"], "filename": r.get("filename"), "created_at": r.get("created_at"),
                     "delivered": {k: done.get(k) for k in ("report_id", "title", "url")} if done else None,
                     "st": None if done else status.get(r["job_id"])})
    return {"jobs": jobs, "keep_days": settings.docforge_job_days}


@router.post("/upload/destinations/docforge/jobs/{job_id}/dismiss")
async def upload_docforge_dismiss(
    job_id: str,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """'끝나지 않은 정밀 변환' 목록에서 숨긴다 — 잡 기록 · DocForge 잡은 그대로(진행 · 배달은 된다)."""
    try:
        rec = _dfd.load_job(settings, job_id, principal.subject)
    except _dfd.DeliveryError as exc:
        raise _dfd_http(exc) from exc
    await asyncio.to_thread(_dfd.dismiss, settings, job_id, rec)
    return {"job_id": job_id, "dismissed": True}


# ── PC 도우미 업로드 — DRM 문서를 PC 의 PowerPoint 로 풀어 올린다(docs/chat-ppt B · PP-D8) ─────────────────────────────────
# 브라우저는 COM 을 부를 수 없고 PC 파일 경로도 모른다. 화면이 표를 받아 `hwax-doc://` 로 PC 도우미(추출기 -Url 모드)를 깨우고, 도우미가
# 뽑은 글(.hwax.md)과 고르면 슬라이드 그림을 그 표로 올린다. 서버는 받은 것을 그 사람 스테이징에 둘 뿐 대화에 쓰지 않는다 — 화면이 받아
# 문서 칩 · 그림 칩으로 붙이고 사람이 보고 보낸다(손으로 .hwax.md 를 붙이던 길과 같은 끝).
class PcTicketReq(BaseModel):
    model_config = {"extra": "ignore"}
    filename: str = Field(default="", max_length=400)          # 브라우저가 고른 원본 이름 — 도우미가 파일 고르기 창에 미리 넣는다
    conversation_id: str = Field(default="", max_length=200)   # 감사용(서버 대화 id) — 받은 글을 대화에 쓰지는 않는다
    slides: StrictBool = False                                 # 슬라이드 그림도(최대 _pc.SLIDES_MAX 장)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _pc_reject(exc: Exception) -> AuthError:
    return AuthError(exc.message, status_code=exc.status) if isinstance(exc, _pc.TicketError) else AuthError(str(exc), status_code=400)


def _pc_audit(request: Request, rec: dict, event: str, status: str, **meta) -> None:
    """표의 감사 한 줄 — 주인 · 대화 · 파일 이름 · IP 와 넘긴 칸. 본문은 남기지 않는다(B7)."""
    _audit(request).record(principal=rec.get("owner_sub") or "", event=event, status=status,
                           chat_id=(rec.get("conversation_id") or None),
                           meta={"filename": rec.get("filename") or "", "ip": _client_ip(request), **meta})


@router.post("/upload/pc-ticket")
async def upload_pc_ticket(
    request: Request,
    body: PcTicketReq,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> dict:
    """PC 도우미가 로그인 없이 **한 번** 올릴 표(10분). 브라우저 세션 + CSRF 로만 낸다 — PAT 로는 못 낸다(PC 에 포털 토큰을 새로 두지
    않는다). 받는 쪽은 /upload 와 같은 게이트다(서버 스테이징에 쓴다)."""
    _upload.require_any_upload_group(settings, principal.groups)
    for rec in await asyncio.to_thread(_pc.sweep, settings):
        _pc_audit(request, rec, "pc_upload", "expired")
    name = Path((body.filename or "").replace("\\", "/")).name[:200]
    ticket, rec, closed = await asyncio.to_thread(
        _pc.issue, settings, owner_sub=principal.subject, owner_email=principal.email or principal.subject,
        owner_name=principal.display_name or "", conversation_id=body.conversation_id, filename=name, slides=body.slides)
    for c in closed:
        _pc_audit(request, c, "pc_upload", "closed")
    _pc_audit(request, rec, "pc_ticket_issue", "ok", slides=body.slides)
    q = f"t={ticket}&name={quote(name, safe='')}&slides={'1' if body.slides else '0'}"
    return {"ticket": ticket, "expires_in_s": _pc.TICKET_TTL_S, "helper_url": f"hwax-doc://extract?{q}",
            "protocol": _pc.PROTOCOL}


@router.get("/upload/pc-ticket/{ticket}")
async def upload_pc_ticket_state(
    ticket: str,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> dict:
    """화면이 몇 초마다 묻는다 — 대기 · 열림(도우미가 표를 읽었다) · 받음 · 실패 · 취소 · 만료. 주인만(남의 표는 없는 표다).
    묻는 김에 수명이 다한 표를 닫고 감사에 적는다(만료는 한 번만 적힌다 — 청소 한 곳에서)."""
    for rec in await asyncio.to_thread(_pc.sweep, settings):
        _pc_audit(request, rec, "pc_upload", "expired")
    try:
        out = await asyncio.to_thread(_pc.view, settings, ticket, principal.subject)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    r = out.get("received")
    if r:
        # 다음 단계 — 받은 글을 AI 데이터 허브로(PP-D11). 글은 이미 스테이징 상자에 있으니 그 상자로 '어디로 보낼까요' 를 연다.
        out["staged"] = {"staging_id": r["doc_staging_id"], "filename": r["doc_name"], "size": r["bytes"], "ext": "md",
                         "destinations": _upload.allowed_destinations(settings, principal.groups, "md",
                                                                      await _upload.gateway_tool_names(settings))}
    return out


@router.get("/upload/pc-ticket/{ticket}/doc")
async def upload_pc_ticket_doc(
    ticket: str,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        p = await asyncio.to_thread(_pc.received_doc, settings, ticket, principal.subject)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    return FileResponse(p, media_type="text/markdown; charset=utf-8", headers={"Cache-Control": "no-store"})


@router.get("/upload/pc-ticket/{ticket}/slides/{n}")
async def upload_pc_ticket_slide(
    ticket: str,
    n: int,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        p = await asyncio.to_thread(_pc.received_slide, settings, ticket, principal.subject, n)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/upload/pc/{ticket}")
async def upload_pc_helper_info(ticket: str, request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """도우미가 처음 묻는 자리(표만 — 로그인 없이). 받는 계정(이름 · 메일)을 돌려준다 — 도우미는 이것을 사람에게 보여 주고 묻는다. 남이 만든
    링크(남의 표)로 내 문서가 남의 대화에 가는 것을 막는 문이 그 확인이다(PP-D8 ④). 판(helper_min)이 맞지 않으면 도우미가 멈춘다."""
    try:
        rec, first = await asyncio.to_thread(_pc.helper_open, settings, ticket)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    if first:
        _pc_audit(request, rec, "pc_ticket_open", "ok", helper=request.headers.get("x-hwax-helper", "")[:20])
    return {"protocol": _pc.PROTOCOL, "helper_min": _pc.HELPER_MIN,
            "owner_email": rec.get("owner_email") or "", "owner_name": rec.get("owner_name") or "",
            "filename": rec.get("filename") or "", "slides": bool(rec.get("slides")),
            "expires_in_s": _pc.expires_in(rec),
            "doc_max_bytes": _pc.DOC_MAX_BYTES, "slides_max": _pc.SLIDES_MAX, "slide_max_bytes": _pc.SLIDE_MAX_BYTES}


@router.post("/upload/pc/{ticket}/cancel")
async def upload_pc_helper_cancel(ticket: str, request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """도우미에서 사람이 '아니오' · 파일 고르기 취소 · 추출 실패를 골랐다 — 화면이 기다리지 않고 곧바로 알게 표를 닫는다.
    까닭은 본문 JSON `{"reason": …}`(선택)이다 — 헤더는 ASCII 만 실려 한글 까닭을 못 싣는다. 로그인 없는 자리라 본문은 4KB 까지만 읽는다."""
    cl = request.headers.get("content-length", "")
    if cl.isdigit() and int(cl) > 4096:
        raise AuthError("본문이 4KB 를 넘습니다.", status_code=413)
    reason = ""
    if cl.isdigit() and int(cl) > 0:
        try:
            got = json.loads(await request.body())
            reason = str(got.get("reason") or "")[:200] if isinstance(got, dict) else ""
        except ValueError:
            reason = ""
    try:
        rec = await asyncio.to_thread(_pc.helper_cancel, settings, ticket, reason)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    _pc_audit(request, rec, "pc_upload", "cancelled", reason=rec.get("error") or "")
    return {"ok": True}


@router.post("/upload/pc/{ticket}")
async def upload_pc_helper_receive(ticket: str, request: Request, settings: Settings = Depends(get_settings)) -> dict:
    """도우미가 올리는 자리(표만 — 로그인 없이). **표를 먼저 닫고 나서** 본문을 읽는다 — 아무나 큰 본문을 보내 스테이징을 채우지 못하게,
    같은 표로 두 번 올리지 못하게. 받는 것: `doc`(.hwax.md — UTF-8 · 머리말 schema hwax-doc/1 · _pc.DOC_MAX_BYTES) ·
    `slides`(PNG · _pc.SLIDES_MAX 장 · 장당 _pc.SLIDE_MAX_BYTES — 표가 그림을 청했을 때만 둔다). 원본은 받지 않는다(사용자 결정 10-22)."""
    cl = request.headers.get("content-length", "")
    limit = _pc.DOC_MAX_BYTES + _pc.SLIDES_MAX * _pc.SLIDE_MAX_BYTES + (1 << 20)
    if not cl.isdigit():
        raise AuthError("길이(Content-Length)가 없는 본문은 받지 않습니다.", status_code=411)
    if int(cl) > limit:
        raise AuthError(f"본문이 상한 {limit:,}바이트를 넘습니다.", status_code=413)
    try:
        rec = await asyncio.to_thread(_pc.claim, settings, ticket)
    except _pc.TicketError as exc:
        raise _pc_reject(exc) from None
    try:
        async with request.form(max_files=_pc.SLIDES_MAX + 1, max_fields=4, max_part_size=64 * 1024) as form:
            doc = form.get("doc")
            if isinstance(doc, str) or doc is None:
                raise ValueError("글(doc 파일)이 없습니다.")
            text = _pc.check_doc(await doc.read(_pc.DOC_MAX_BYTES + 1))
            parts = [f for f in form.getlist("slides") if not isinstance(f, str)] if rec.get("slides") else []
            if len(parts) > _pc.SLIDES_MAX:
                raise ValueError(f"슬라이드 그림이 {_pc.SLIDES_MAX}장을 넘습니다({len(parts)}장).")
            blobs = []
            for i, f in enumerate(parts, start=1):
                b = await f.read(_pc.SLIDE_MAX_BYTES + 1)
                _pc.check_slide(b, i)
                blobs.append(b)
            helper = str(form.get("helper") or "")[:20]
        received = await asyncio.to_thread(_pc.store, settings, rec, text, blobs)
    except Exception as exc:  # noqa: BLE001 — 표는 이미 닫혔다. 까닭을 남기고 도우미에 돌려준다
        reason = str(exc)[:300] if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"[:300]
        await asyncio.to_thread(_pc.finish, settings, ticket, ok=False, error=reason)
        _pc_audit(request, rec, "pc_upload", "failed", error=reason)
        raise AuthError(f"받지 못했습니다 — {reason} 포털 화면에서 단추를 다시 누르세요.", status_code=422) from None
    await asyncio.to_thread(_pc.finish, settings, ticket, ok=True, received=received)
    _pc_audit(request, rec, "pc_upload", "ok", doc=received["doc_name"], bytes=received["bytes"], chars=received["chars"],
              slides=received["slides"], helper=helper)
    return {"ok": True, "chars": received["chars"], "slides": received["slides"]}


@router.post("/upload/analyze")
async def upload_analyze(
    request: Request,
    body: UploadAnalyzeReq,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """스테이징 파일을 파싱해 dry_run 미리보기(물성 계산, 저장 안 함)를 반환한다."""
    return await _upload_register(request, principal, settings, body, dry_run=True)


@router.post("/upload/commit")
async def upload_commit(
    request: Request,
    body: UploadCommitReq,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """사용자 확인 후 실제 등록(dry_run=False). 성공하면 스테이징 파일을 삭제한다."""
    audit = _audit(request)
    out = await _upload_register(request, principal, settings, body, dry_run=False)
    if out.get("stage") == "committed":
        try:
            _upload.staged_path(settings, principal.subject, body.staging_id, body.filename).unlink()
        except Exception:  # noqa: BLE001 — 삭제 실패가 등록 성공을 뒤집지 않게
            pass
        audit.record(principal=principal.subject, event="upload_commit", status="ok",
                     meta={"material_id": out.get("material_id"), "test_id": out.get("test_id")})
    return out


@router.post("/deliberate/experts")
async def deliberate_experts(
    request: Request,
    body: ExpertsRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """심의 전 전문가 선정 미리보기 — agent-server 로 포워딩(caller groups 주입). 비스트리밍 JSON.
    챗 조직도(전문가와 대화)도 이 풀을 쓴다. 같은 응답에 도구 카탈로그도 실려서(챗 시작 패널의
    앱·도구 고르기) 엔드포인트는 막지 않고, 심의·전문가 대화 권한이 없으면 전문가 목록만 비운다."""
    experts_ok = any(k in principal.groups for k in ("feat:deliberation", "feat:expert-chat"))
    client = _agent_client(request)
    payload = {"message": body.message, "groups": principal.groups, "light": body.light,
               # ⚠ 이 줄이 없으면 프론트가 대화를 보내도 여기서 버려져 축이 안 나온다.
               "history": [m.model_dump(exclude={"evidence", "images"}) for m in body.history]}
    try:
        r = await client.post(f"{settings.agent_server_url}/deliberate/experts", json=payload,
                              timeout=_unary_timeout(settings))
        if r.status_code != 200:
            return {"recommended": [], "pool": [], "error": f"agent_{r.status_code}"}
        # 못 쓰는 HE팀 운영자는 조직도에 안 보인다(골라도 403 인 사람을 보이면 고장으로 읽힌다).
        data = filter_experts(r.json(), request.app.state.access.get(), principal.groups)
        if not experts_ok:
            data = {**data, "recommended": [], "candidates": [], "pool": [], "experts_hidden": True}
        return data
    except httpx.HTTPError as exc:
        return {"recommended": [], "pool": [], **_unary_fail(exc, settings, "deliberate/experts")}


@router.post("/deliberate/clarify")
async def deliberate_clarify(
    request: Request,
    body: ClarifyRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """심의 전 되묻기 — 메커니즘 분석 최소 정보 중 빈 칸을 스캔(agent-server 포워딩).

    ⚠ 실패는 '묻지 않음' 이다(ask=[]). 되묻기가 심의를 막으면 안 된다."""
    ensure(principal, "feat:deliberation")
    client = _agent_client(request)
    payload = {"message": body.message, "job": body.job,
               "history": [m.model_dump(exclude={"evidence", "images"}) for m in body.history]}
    try:
        r = await client.post(f"{settings.agent_server_url}/deliberate/clarify", json=payload,
                              timeout=_unary_timeout(settings))
        if r.status_code != 200:
            return {"applicable": False, "slots": [], "ask": [], "error": f"agent_{r.status_code}"}
        return r.json()
    except httpx.HTTPError as exc:
        return {"applicable": False, "slots": [], "ask": [], **_unary_fail(exc, settings, "deliberate/clarify")}


class TopicRequest(BaseModel):
    """챗 대화 → 심의 화두. history 상한은 ChatRequest 와 같은 이유로 둔다(무한 입력 금지)."""

    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=160)
    history_total = field_validator("history")(_history_total)
    # 실패하면 그대로 돌려줄 화두(대개 첫 발화) — 첫 발화가 2,000자를 넘으면 종전엔 422 로 제안 자체가 꺼졌다.
    fallback: str = Field(default="", max_length=_WINDOW_CHARS)
    job: str = Field(default="default", max_length=40)


@router.post("/deliberate/topic")
async def deliberate_topic(
    request: Request,
    body: TopicRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """대화를 읽고 심의 화두 한 문장을 제안한다(agent-server 포워딩).

    ⚠ 되묻기와 같은 규율 — **실패는 fallback 이다.** 화두 제안이 안 되면 첫 발화를 그대로
    쓰면 되지, 브리프가 안 열리면 안 된다."""
    ensure(principal, "feat:deliberation")
    client = _agent_client(request)
    payload = {"history": [m.model_dump(exclude={"evidence", "images"}) for m in body.history],
               "fallback": body.fallback, "job": body.job}
    fail = {"topic": body.fallback, "why": "", "options": []}
    try:
        r = await client.post(f"{settings.agent_server_url}/deliberate/topic", json=payload,
                              timeout=_unary_timeout(settings))
        if r.status_code != 200:
            return {**fail, "error": f"agent_{r.status_code}"}
        return r.json()
    except httpx.HTTPError as exc:
        return {**fail, **_unary_fail(exc, settings, "deliberate/topic")}


@router.post("/deliberate/voc")
async def deliberate_voc(
    request: Request,
    body: VocPreviewRequest,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
):
    """심의 전 'VOC 먼저 보기' — 화두로 SignalForge 를 검색해 사람이 고를 목록(agent-server 포워딩).

    고른 항목은 프론트가 delib_opts.evidence 로, 보강 문장은 human_note 로 싣는다."""
    ensure(principal, "feat:deliberation")
    client = _agent_client(request)
    payload = {"message": body.message, "groups": principal.groups,
               "keywords": [k.strip()[:40] for k in body.keywords if k and k.strip()]}
    try:
        r = await client.post(f"{settings.agent_server_url}/deliberate/voc-preview", json=payload,
                              timeout=_unary_timeout(settings))
        if r.status_code != 200:
            return {"items": [], "keywords": [], "error": f"agent_{r.status_code}"}
        return r.json()
    except httpx.HTTPError as exc:
        return {"items": [], "keywords": [], **_unary_fail(exc, settings, "deliberate/voc")}


# ── 웹 심의 멈춤(docs/leftovers-1017 triage A24 (나) — 사용자 결정 10-31) ────────────────────────────────────────────────
# 웹 심의(/심의 · /시뮬심의 · /시험계획)는 에이전트 서버의 분리 태스크라 화면이 떠나도(■ · 탭 닫기 · 끊김) 서버에서 끝까지 돈다 — 중계는 브라우저가
# 끊으면 상류를 끊을 뿐이다(docs/request-1029 P-1). 그것을 멈추는 길이 이 창구다. 에이전트 서버 POST /deliberate/cancel 을 그 대화 id 로 부른다
# (에이전트는 /chat 이 실은 conversation_id 로 태스크를 적어 둔다 — _relay_stream).
#   · 인증 — 세션 + CSRF 만. PAT 는 받지 않는다(화면의 '멈춤' 단추가 부르는 자리다).
#   · 주인 — 그 대화의 주인만. 없는 대화는 404 conversation_not_found, 남의 대화는 403 not_owner(이 창구의 계약 — 다른 대화 REST 는 둘 다 404).
#     관리자도 남의 심의는 멈추지 못한다 — MCP deliberate_cancel(에이전트 delib_jobs.cancel 의 _foreign)과 같은 규칙이다(관리자는 볼 수 있어도
#     접지는 못한다). 운영이 접을 일은 에이전트 서버의 루프백 창구를 직접 부른다(신원 없이 — 그 대화의 웹 심의 전부).
#   · 에이전트에는 user_email 을 싣는다 — 에이전트는 그 사람이 띄운 심의만 접는다(남이 내 대화 id 를 실어 띄운 심의는 건드리지 않는다).
#   · 답 — 에이전트의 답(200 · 404 delib_not_found · 409 already_finished · 422)을 상태 · 본문 그대로 넘긴다. code 없는 404 는 이 창구를 모르는
#     옛 에이전트 서버라 404 agent_outdated, code 없는 5xx 는 502 agent_5xx, 닿지 못하면 502 agent_unreachable, 늦으면 504 agent_timeout.
#   · 감사 — delib_cancel 한 줄(대화 · 상류 상태 · code).
_DELIB_CANCEL_TIMEOUT = httpx.Timeout(10.0, read=30.0)   # 창구는 태스크 취소만 하고 곧바로 답한다 — 단추가 오래 잠기지 않게 짧게 둔다


class DelibCancelReq(BaseModel):
    model_config = {"extra": "forbid"}

    conversation_id: str = Field(min_length=1, max_length=64)


def _dc_reply(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


@router.post("/deliberate/cancel")
async def deliberate_cancel(
    request: Request,
    body: DelibCancelReq,
    principal: Principal = Depends(get_current_principal),
    _csrf: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> Response:
    """도는 웹 심의를 멈춘다(위 머리글) — 대화 주인만, 에이전트 서버의 답을 그대로 넘긴다."""
    cid = body.conversation_id
    audit = _audit(request)
    try:
        state = await asyncio.to_thread(_conv(request).owner_state, cid, principal.subject)
    except sqlite3.OperationalError as exc:
        raise _store_busy(exc) from exc
    if state != "mine":
        status, code, msg = ((404, "conversation_not_found", "그런 대화가 없습니다") if state == "none"
                             else (403, "not_owner", "이 대화를 시작한 사람만 심의를 멈출 수 있습니다"))
        audit.record(principal=principal.subject, event="delib_cancel", status="rejected", meta={"conversation": cid, "code": code})
        return _dc_reply(status, code, msg)
    try:
        r = await _agent_client(request).post(
            f"{settings.agent_server_url}/deliberate/cancel", timeout=_DELIB_CANCEL_TIMEOUT,
            json={"conversation_id": cid, "by": principal.email or principal.subject, "user_email": principal.email or ""})
    except httpx.HTTPError as exc:
        late = isinstance(exc, httpx.ReadTimeout)
        code = "agent_timeout" if late else "agent_unreachable"
        audit.record(principal=principal.subject, event="delib_cancel", status="error", meta={"conversation": cid, "code": code})
        return _dc_reply(504 if late else 502, code,
                         "에이전트 서버의 답이 늦습니다 — 잠시 뒤 다시 누르세요" if late else
                         f"에이전트 서버에 닿지 못했습니다({type(exc).__name__}) — 잠시 뒤 다시 누르세요")
    code = _cr_upstream_code(r)
    out: Response
    if code is None and r.status_code == 404:
        code = "agent_outdated"
        out = _dc_reply(404, code, "에이전트 서버에 심의 멈춤 창구가 없습니다 — 옛 판입니다(에이전트 서버를 올린 뒤 다시 누르세요)")
    elif code is None and r.status_code >= 500:
        code = "agent_5xx"
        out = _dc_reply(502, code, f"에이전트 서버 오류(HTTP {r.status_code})")
    else:
        out = Response(content=r.content, status_code=r.status_code,
                       media_type=r.headers.get("content-type", "application/json"))
    audit.record(principal=principal.subject, event="delib_cancel", status="ok" if r.status_code < 400 else "error",
                 meta={"conversation": cid, "upstream": r.status_code, **({"code": code} if code else {})})
    return out


# 챗 중계가 브라우저에 아직 못 보낸 프레임의 상한(HWAXPortal docs/request-1029 P-1 ①) — 끝없이 읽지 않는 클라이언트가 포털 메모리를 쌓지
# 않게 한다. 보통 챗 한 턴은 수 MB 안이다(생각 글 24만 자도 1 MB 남짓). 넘으면 그 스트림만 종전처럼 상류 읽기를 멈춘다.
_RELAY_BUFFER_BYTES = 64 * 1024 * 1024
_RELAY_DONE = object()
# 브라우저가 떠난 뒤에도 상류를 끝까지 읽는 루틴 턴의 pump(R3 D9) — 아무도 await 하지 않는 작업은 이벤트 루프가 약한 참조만 쥐어 도는
# 중에 GC 될 수 있다. 끝나면 빠진다.
_DETACHED_RELAYS: set[asyncio.Task] = set()


def _detached_relay_done(task: asyncio.Task) -> None:
    _DETACHED_RELAYS.discard(task)
    if not task.cancelled() and task.exception() is not None:
        # 받아 줄 쪽이 없다 — 남기지 않으면 'Task exception was never retrieved' 만 GC 때 찍힌다.
        logger.warning("루틴 턴 중계 — 브라우저가 떠난 뒤 상류를 읽다 실패했다", exc_info=task.exception())


# 떼어 낸 pump 의 상한 — 하나가 챗 퍼밋 하나와 에이전트 서버 연결 하나를 실행이 끝날 때까지(분 ~ 시간) 쥔다. 넘으면 그 턴은 일반 턴처럼
# 브라우저가 떠날 때 상류를 끊고 로그 한 줄을 남긴다. 실행은 에이전트 서버가 따로 떼어 낸 작업이라 그대로 돈다 — 대화에는 받은 데까지와
# 실행 포인터(meta.routine)가 남아 '이어서' 로 다시 붙는다. 에이전트 서버 동시 실행(ROUTINE_MAX_RUNNING, 기본 2)과 다시 붙은 탭 몫을 넉넉히
# 덮는다. 박스 설정에 같은 꼴의 손잡이가 없어 상수로 둔다.
_DETACHED_RELAYS_MAX = 8
# 답 글 없이 끝난 루틴 턴의 답 — 중계가 침묵 한도에 끊겼거나(ReadTimeout) 에이전트 서버가 루틴 프레임 뒤에 죽었다. 글이 없다고 답을 버리면
# 대화에서 run_id 가 사라져 그 실행으로 돌아갈 길이 없다(화면은 meta.routine.run_id 로 원장을 읽는다). 루틴이 아닌 턴은 종전대로 빈 답을 남기지 않는다.
_ROUTINE_EMPTY_REPLY = "(루틴 실행 — 단계와 보고서는 위 실행 보기에서 이어서 본다)"
# 실행의 끝 상태 — 이 상태의 같은 글 답은 (대화, 실행)마다 하나만 남긴다(_routine_save_lock · _routine_answered).
_ROUTINE_TERMINAL = ("done", "failed", "cancelled")
# (대화 id, 실행 id) → [잠금, 쥐거나 기다리는 수]. 마지막으로 놓는 쪽이 지운다 — 실행마다 하나씩 쌓이지 않게.
_ROUTINE_SAVE_LOCKS: dict[tuple[str, str], list] = {}


@contextlib.asynccontextmanager
async def _routine_save_lock(key: tuple[str, str]) -> AsyncIterator[None]:
    """끝난 루틴 턴의 답 저장을 (대화 id, 실행 id)마다 하나씩 한다. 두 탭(떼어 낸 첫 턴과 '이어서' 로 다시 붙은 턴)이 같은 실행을 끝까지
    읽으면 둘 다 '아직 없다' 를 본 뒤 둘 다 넣어 보고서가 두 번 남는다 — 확인과 넣기는 이 잠금 안의 스레드 호출 하나다(포털은 루프 하나다)."""
    slot = _ROUTINE_SAVE_LOCKS.setdefault(key, [asyncio.Lock(), 0])
    slot[1] += 1
    try:
        async with slot[0]:
            yield
    finally:
        slot[1] -= 1
        if not slot[1]:
            _ROUTINE_SAVE_LOCKS.pop(key, None)


def _routine_answered(conv: dict | None, run_id: str, state: str, reply: str) -> bool:
    """대화에 이 실행의 같은 끝 상태 · 같은 글 답이 이미 있는가 — 스레드에서, _routine_save_lock 안에서 부른다. 글까지 본다 — 같은 실행의
    같은 끝이라도 글이 다르면 다른 턴의 답이다(끝난 실행의 'RA 초안 올리기' 안내 — 종전엔 보고서에 가려 버려졌다). 공백만 다른 글은 같은 글이다."""
    norm = " ".join(reply.split())
    for m in (conv or {}).get("messages") or []:
        rt = (m.get("meta") or {}).get("routine") if m.get("role") == "assistant" else None
        if (isinstance(rt, dict) and rt.get("run_id") == run_id and rt.get("state") == state
                and " ".join(str(m.get("content") or "").split()) == norm):
            return True
    return False


class _ReleasingStream(StreamingResponse):
    """SSE 응답 — 끝나든 끊기든 on_close 가 돈다. 생성기는 한 번도 돌지 않으면(헤더를 보내다 끊김 — ASGI spec 2.4) finally 도
    돌지 않으므로, 생성기 finally 에만 맡긴 정리(퍼밋 반납)는 새어 버린다. on_close 는 두 번 불려도 한 번만 일하게 쓴다.
    끝나면 생성기도 닫는다 — send 가 끊김으로 실패하면 Starlette 는 생성기를 yield 에 세워 둔 채 나가, 그 finally(상류 끊기)가 GC 를
    기다렸다."""

    def __init__(self, content: AsyncIterator[bytes], on_close: Callable[[], None], **kw: Any) -> None:
        super().__init__(content, **kw)
        self._on_close = on_close

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._on_close()
            _close = getattr(self.body_iterator, "aclose", None)
            if _close is not None:
                with anyio.CancelScope(shield=True):
                    await _close()


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    mode: str | None = None,
    principal: Principal = Depends(principal_pat_or_session),  # Bearer PAT 또는 세션 쿠키(+CSRF)
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    # 권한 — 메뉴를 숨겨도 요청은 직접 보낼 수 있다. 세마포어를 잡기 전에 거절한다.
    check_chat(request.app.state.access.get(), principal, thinking=body.thinking,
               pinned_agent=body.pinned_agent, pinned_agents=body.pinned_agents)
    # 분석 루틴 — 메뉴를 숨겨도 요청은 직접 보낼 수 있다(R3-design 5). 에이전트 서버도 entitlements 로 한 번 더 본다.
    routine_turn = body.routine is not None
    if routine_turn:
        ensure(principal, "feat:routines")
    sem = _sem(request)
    audit = _audit(request)
    # SSE holds a worker for the stream's lifetime → cap, and reject (not queue) over the cap.
    # This IS atomic despite looking like check-then-act: asyncio is single-threaded and there
    # is NO await between sem.locked() and sem.acquire() (acquire returns synchronously when a
    # slot is free), so no other task can steal the slot in between. Acquire BEFORE returning
    # so an over-cap request 429s up front instead of opening a stream we can't serve.
    if sem.locked():
        audit.record(principal=principal.subject, event="chat_error", status="rejected",
                     meta={"reason": "max_concurrent_chats"})
        raise AuthError("too many concurrent chats; retry shortly", status_code=429)
    await sem.acquire()
    # 퍼밋은 한 번만 돌려준다 — 생성기의 finally 와 응답(_ReleasingStream)이 둘 다 부른다. 헤더를 보내다 끊기면(ASGI spec 2.4)
    # 생성기가 한 번도 돌지 않아 그 finally 도 돌지 않는다 — 응답 쪽이 없으면 퍼밋이 영구히 샌다.
    released = False

    def _release() -> None:
        nonlocal released
        if not released:
            released = True
            sem.release()

    # 루틴 턴은 pump 가 돌기 시작하면 퍼밋을 pump 가 끝날 때 돌려준다 — 브라우저가 먼저 떠나도 상류를 끝까지 읽는 동안 쥔다(R3 D9).
    # 에이전트 서버로 가는 풀(max_connections)이 퍼밋 수와 같아, 퍼밋 없이 도는 상류 연결은 다른 챗을 풀 대기(agent_unreachable)로
    # 밀어낸다 — 넘치면 들어올 때 429 로 말하는 편이 정직하다. pump 가 돌기 전에 끝나면(헤더를 보내다 끊김) 종전처럼 응답이 돌려준다.
    pumping = False

    def _on_close() -> None:
        if not (routine_turn and pumping):
            _release()

    # ⚠ acquire 와 gen() 사이는 반드시 보호한다. 여기서 예외가 나면 gen() 이 아예
    # 만들어지지 않으므로 그 안의 finally(sem.release) 가 영원히 실행되지 않는다 —
    # 퍼밋이 영구히 새고 상한(64)만큼 쌓이면 챗·docx 가 전부 429 로 고정된다.
    # 실제 방아쇠가 있다: store.append 는 sqlite3 를 예외 처리 없이 부른다
    # (database is locked / disk I/O error 등).
    try:

        # Pick the stream source. echo = local mock (no remote); else relay the Agent Server.
        if mode == "echo":
            source = _echo_stream(body.message, principal, audit)
        else:
            source = _relay_stream(body, principal, audit, settings, _agent_client(request),
                                   _chat_user_pat(request.app.state.keystore, settings, principal),
                                   _wiki.known_affiliation(request))

        # conversation_id 가 있으면 이 대화(서버 정본)에 user 를 먼저 저장하고, 스트림을 훑어
        # assistant 최종 텍스트를 모아 종료 시 저장한다(웹에서 GLM 이어가기가 서버에 남게).
        store = _conv(request) if body.conversation_id else None
        owner = principal.subject
        cid = body.conversation_id
        if store is not None and cid:
            # 고른 전문가를 발화에 같이 적어 둔다. 이게 없으면 **다른 기기에서 대화를 열 때
            # 전문가가 조용히 풀린다** — 화면엔 그 전문가의 지난 답이 그대로 있어서 사용자는
            # 여전히 지정된 줄 안다(로컬 저장소에는 있는데 서버에는 없던 자리다).
            # meta 는 자유 JSON 칸이라 스키마·API 계약은 그대로다.
            _pin = {k: v for k, v in (("pinned_agent", body.pinned_agent),
                                      ("pinned_agent_name", body.pinned_agent_name)) if v}
            if body.pinned_agents:
                _pin["pinned_agents"] = list(body.pinned_agents)
            # 소유자 대화가 아니면 조용히 저장 스킵(스트림은 정상 — 채팅 자체는 막지 않음).
            if await asyncio.to_thread(store.append, conversation_id=cid, owner_sub=owner,
                                       role="user", content=body.message, meta=_pin or None):
                pass
            else:
                store = None  # 없거나 타인 소유 → 이 요청은 저장 안 함

    except BaseException:
        _release()
        raise

    async def gen() -> AsyncIterator[bytes]:
        acc: list[str] = []          # token delta 누적(폴백)
        final: str | None = None     # result 프레임의 전체 텍스트(우선)
        decision: str | None = None  # 심의 결정문(result 없을 때 폴백)
        turns: list[dict] = []       # 심의 persona 발언 — MCP 경로와 대칭으로 서버에 남긴다
        activity: list[dict] = []    # status 이벤트(도구 호출·결과) 누적 — 심의 핸드오프 스냅샷 서버 영속
        delib_ev: list[dict] = []    # 심의 근거 카드(좌석 조회 결과·엔진의 '줄였다·뺐다' 알림) — 서버 사본에도 남긴다
        user_images: list[str] = []  # 이 발화에 올린 그림의 주소(user_images) — 서버 사본의 답 meta 에 남겨 다른 기기의 이력에도 그림이 실리게
        routine_ptr: dict = {}       # 분석 루틴 프레임에서 모은 포인터(run_id · routine_id · title · state) — 답 meta.routine 으로 남긴다
        cancelled: dict = {}         # 사람이 멈춘 웹 심의의 멈춤 사건(delib kind=cancelled) — 답 meta.delib_cancelled 로 남긴다
        buf = ""                     # relay 는 청크가 프레임 경계와 안 맞음 → 완결 프레임만 파싱
        # 청크는 글자 경계와도 안 맞는다 — 한글 한 자(3바이트)가 두 청크로 갈리면 청크마다 따로 풀 때 그 자리가 '�' 로
        # 깨져 서버 사본에 들어간다. 발언이 길수록(줄이지 않은 글은 수만 자다) 걸린다. 이어지는 바이트를 쥐고 푼다.
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
        # 상류 읽기를 브라우저 쓰기와 뗀다(HWAXPortal docs/request-1029 P-1 ① · C-5). 숨은 탭은 끊긴 것이 아니라 읽기가 멈춘 것이다 — 종전엔
        # 그동안 이 생성기가 yield 에 서서 상류도 읽지 않아, 에이전트 응답 · 서버 사본 저장 · 퍼밋이 탭을 깨울 때까지 묶였다(OT-07 25분 ·
        # OT-13 5분 반). 이제 pump 가 상류를 끝까지 읽어 저장하고 퍼밋을 돌려준다. 브라우저가 끊으면(중지 · 탭 닫기) 종전처럼 상류도 끊는다.
        # 루틴 턴만 다르다 — 브라우저가 떠나도 상류를 끝까지 읽어 대화에 남긴다(R3 D9). 멈춤은 화면이 실행을 멈추는 것(/cancel)이다.
        q: asyncio.Queue = asyncio.Queue()
        room = asyncio.Event()
        pending = 0                  # 브라우저가 아직 안 읽은 바이트 — _RELAY_BUFFER_BYTES 를 넘으면 그때만 종전처럼 상류 읽기를 멈춘다
        warned = False
        detached = False             # 루틴 턴 — 브라우저가 떠났다(아래 finally). 그 뒤 프레임은 저장할 것만 모으고 큐에 쌓지 않는다

        async def pump() -> None:
            nonlocal final, decision, user_images, cancelled, buf, pending, warned
            try:
                async for frame in source:
                    if store is not None:
                        buf += dec.decode(frame) if isinstance(frame, bytes) else str(frame)
                        while "\n\n" in buf:
                            one, buf = buf.split("\n\n", 1)
                            parsed = _parse_sse_frame(one)
                            if parsed is None:
                                continue
                            evt, data = parsed
                            if evt == "result" and isinstance(data.get("content"), str):
                                final = data["content"]
                            elif evt == "token" and isinstance(data.get("delta"), str):
                                acc.append(data["delta"])
                            elif evt == "delib":
                                k = data.get("kind")
                                if k == "turn" and isinstance(data.get("say"), str):
                                    # say 는 회의 버블용으로 줄인 글이다. 엔진은 줄였을 때만 줄이지 않은 글(say_full)과
                                    # 그 원래 길이(say_full_chars)를 같은 이벤트에 따로 싣는다 — 서버 사본(다른 기기·이어가기·
                                    # Claude 가 읽는 정본)은 그쪽을 남기고 버블은 meta.say 로 둔다(화면이 버블을 그린다).
                                    _full = data.get("say_full")
                                    turns.append({"persona": data.get("persona"),
                                                  # 이어하기 회차를 이어 센 번호로 저장한다 — MCP 경로
                                                  # (JS rn())와 같은 의미. 회차 안 번호(round)로 두면
                                                  # 이어하기 회의록이 다시 '1R' 로 저장됐다(실심의 E2E).
                                                  "round": (data.get("display_round")
                                                            if isinstance(data.get("display_round"), int)
                                                            else data.get("round")),
                                                  "content": (_full if isinstance(_full, str) and _full
                                                              else data["say"]),
                                                  "say": data["say"],
                                                  "say_full_chars": (data["say_full_chars"]
                                                                     if isinstance(data.get("say_full_chars"), int)
                                                                     else None),
                                                  # 관계·입장은 say 산문에 녹아 있지만 구조로 남기지
                                                  # 않으면 다른 기기에서 열었을 때 관계도가 비고
                                                  # 이어하기가 조항을 승계하지 못한다(감사 2026-09-11).
                                                  "stance": data.get("stance"),
                                                  "non_negotiable": data.get("non_negotiable"),
                                                  "rebut": data.get("rebut")})
                                elif k == "decision" and isinstance(data.get("text"), str):
                                    decision = data["text"]
                                elif k == "cancelled":
                                    # 사람이 멈춘 웹 심의(에이전트 POST /deliberate/cancel — triage A24) — 서버 사본에 멈춤으로 남긴다. 남기지
                                    # 않으면 발언만 있고 답이 없는 대화가 되어 다른 기기에서는 '비정상 종료' 로 보인다(실패가 아니다).
                                    cancelled = {"message": str(data.get("message") or "")[:400], "by": str(data.get("by") or "")[:200]}
                                elif k == "evidence":
                                    # 근거 카드는 엔진이 '좌석에 주지 않았다·줄였다·좌석이 유실됐다' 를 알리는 유일한
                                    # 길이다(notice). 종전엔 서버 사본에 남지 않아 다른 기기·새로고침 뒤에는 알림이 사라지고,
                                    # 좌석이 조회한 근거(이어하기가 승계한다)도 브라우저 사본 최근 4건만 남았다. 그대로 둔다.
                                    delib_ev.append({kk: vv for kk, vv in data.items() if kk != "kind"})
                            elif evt == "user_images" and isinstance(data.get("urls"), list):
                                # 주소 꼴만 받는다 — 이력 항목(ChatHistoryMessage.images)이 받는 꼴과 같아야 다음 턴에 422 가 안 난다.
                                user_images = [u for u in data["urls"]
                                               if isinstance(u, str) and _ARTIFACT_IMAGE_RE.fullmatch(u)][:_IMAGES_MAX]
                            elif evt == "routine" and isinstance(data.get("run_id"), str) and data["run_id"]:
                                # 분석 루틴(R3-design 3.2 · 3.3) — 대화에는 포인터만 남긴다(정본은 포털 원장, 단계 · 보고서는 화면이 run_id 로 읽는다).
                                # 실행 id 는 모든 프레임에, 루틴 id · 제목은 plan 에, 실행 상태는 plan · done 에 있다. 마지막 값이 이긴다.
                                # ⚠ step · step_done 의 state 는 단계 상태다 — 실행 상태로 읽으면 끝난 실행이 'ok' 로 남는다.
                                routine_ptr["run_id"] = data["run_id"]
                                if data.get("kind") == "plan":
                                    for _k in ("routine_id", "title"):
                                        if isinstance(data.get(_k), str):
                                            routine_ptr[_k] = data[_k]
                                if data.get("kind") in ("plan", "done") and isinstance(data.get("state"), str):
                                    routine_ptr["state"] = data["state"]
                            elif evt == "status" and data.get("tool"):
                                # 도구가 붙은 status 만 근거로 남긴다(진행 텍스트만 있는 건 스냅샷 대상 아님).
                                activity.append({
                                    "step": str(data.get("step") or "")[:200],
                                    "tool": str(data.get("tool"))[:80],
                                    # 짝 키와 성패 — 이 둘이 없어서 인자와 결과를 못 붙였고
                                    # 실패한 호출이 성공한 호출과 똑같이 생겼다(PLAN §9-8).
                                    # ⚠ ok 는 **없을 수 있다**(시작 이벤트). None 과 False 를
                                    # 섞으면 '모른다' 가 '실패했다' 가 된다.
                                    "call": (str(data.get("call"))[:80] if data.get("call") else None),
                                    # `invoke_tool` 경유였다는 사실 — `tool` 은 이미 안쪽 이름이다
                                    "via": (str(data.get("via"))[:40] if data.get("via") else None),
                                    # 시각·소요 — 원장에는 있는데 활동에는 없었다(PLAN §9-8)
                                    "ts": (int(data["ts"]) if isinstance(data.get("ts"), int) else None),
                                    "ms": (int(data["ms"]) if isinstance(data.get("ms"), int) else None),
                                    "ok": (bool(data["ok"]) if isinstance(data.get("ok"), bool) else None),
                                    "detail": (str(data.get("detail"))[:400] if data.get("detail") else None),
                                    # 절차 도출용 날것 — 미리보기로 만든 절차는 인자가 손상돼 있다.
                                    # ⚠ 다시 자르지 않는다. 에이전트가 HANDOFF_RESULT_CHARS 에서 자르고 `…#sha6` 표식을 붙여
                                    #   보낸다 — 여기서 한 번 더 자르면 그 표식이 떨어지고, 에이전트 손잡이를 올려도 서버 사본·
                                    #   절차 원장은 이 자리의 숫자에 묶였다.
                                    "detail_full": (str(data["detail_full"]) if data.get("detail_full") else None),
                                    "result_preview": (str(data.get("result_preview"))[:2000]
                                                       if data.get("result_preview") else None),
                                    # 핸드오프용 날것 — 이것을 안 남기면 새로고침 뒤 심의로 넘길 때
                                    # 220자 미리보기만 남는다(감사 C45 — result_full 채널을 뚫어놓고
                                    # 서버 스냅샷이 버리고 있었다).
                                    # ⚠ 에이전트는 4000자를 보내는데 여기서 2000 으로 **다시**
                                    # 잘랐다(표식 없이). 잘린 줄도 모르고 뒤가 사라졌다. 그 뒤 4,000자로 맞췄지만
                                    # 같은 숫자를 두 곳에 두면 한쪽만 올린 날 다시 묶인다 — 자르는 것은 에이전트 하나다.
                                    "result_full": (str(data["result_full"]) if data.get("result_full") else None),
                                })
                    n = len(frame)
                    # 루틴 턴에서 브라우저가 떠났으면(detached) 상한 대기도 큐도 건너뛴다 — 아무도 읽지 않으니 기다리면 상류 읽기가 영영 멈추고,
                    # 쌓으면 pump 가 끝날 때까지 메모리만 쥔다.
                    while not detached and pending and pending + n > _RELAY_BUFFER_BYTES:
                        if not warned:
                            warned = True
                            logger.warning("챗 중계 — 브라우저가 %s바이트를 읽지 않아 상한(%s)에 닿았다. 읽을 때까지 상류 읽기를 멈춘다 sub=%s",
                                           f"{pending:,}", f"{_RELAY_BUFFER_BYTES:,}", owner)
                        room.clear()
                        await room.wait()
                    if detached:
                        continue
                    pending += n
                    q.put_nowait(frame)
            finally:
                q.put_nowait(_RELAY_DONE)
                _close = getattr(source, "aclose", None)
                if _close is not None:
                    with anyio.CancelScope(shield=True):
                        await _close()       # 끊겨서 여기 왔으면 상류 연결도 지금 닫는다(yield 에 선 채 남지 않게)
                _release()  # 상류가 끝나면 돌려준다 — 숨은 탭이 남은 프레임을 다 읽을 때까지 쥐지 않는다. 시작 전 끊김은 응답이 돌려준다
                if store is not None and cid:
                    # 저장은 스레드에서 한다 — 루프 위에서 하면 잠금을 기다리는 동안 포털 전체가 멈춘다(대화 REST 머리의 ⚠).
                    # ⚠ 가려야(shield) 한다. 브라우저가 도중에 떠나면 Starlette 가 이 태스크를 취소하고, 취소된 채로 만난 await 는
                    #   곧바로 CancelledError 다 — 가리지 않으면 떠난 사람의 심의는 받은 발언이 하나도 저장되지 않는다(사본 재현 —
                    #   저장된 역할이 ['user', 'persona'] 에서 ['user'] 로). 긴 심의일수록 사람은 창을 닫고 떠난다.
                    # 끝난 루틴 턴의 같은 글 답은 (대화, 실행)마다 하나다 — 아래 저장을 그 잠금 안에서 한다(_routine_save_lock).
                    _rt_key = ((cid, routine_ptr["run_id"])
                               if routine_turn and routine_ptr.get("state") in _ROUTINE_TERMINAL else None)

                    def _save() -> None:
                        # ⚠ 저장이 실패하면 **로그로 말한다.** 여기는 스트림이 닫힌 뒤라 예외가 나도 화면에 갈 길이 없고,
                        #   로그가 없으면 몇 시간 돈 심의의 서버 사본이 빠진 것을 아무도 모른다(브라우저 사본만 남는다).
                        #   첫 실패에서 멈춘다 — 잠긴 DB 에 발언마다 다시 기다리면 발언 수 × 잠금 대기가 된다.
                        try:
                            # 자르지 않는다 — 이 사본은 끝난 심의의 서버 정본이다(다른 기기·Claude·GLM 이어가기가 읽는다).
                            # 종전엔 발언을 뒤 199건·20,000자, 조항을 1,200자, 반박을 4건·인용 80자, 도구 활동을 60건에서
                            # 표식 없이 잘랐다. 저장소(TEXT)에는 길이 상한이 없고, 이 글은 우리 엔진이 낸 것이다.
                            for t in turns:
                                # meta 는 이미 있는 칸이라 스키마 변경이 필요 없다. 관계는 target·round 만 있으면 그려지고,
                                # 조항은 이어하기가 이 칸에서 승계한다.
                                _m: dict = {}
                                if t.get("stance"):
                                    _m["stance"] = str(t["stance"])
                                if t.get("non_negotiable"):
                                    _m["non_negotiable"] = str(t["non_negotiable"])
                                if isinstance(t.get("rebut"), list) and t["rebut"]:
                                    _m["rebut"] = [
                                        {"target": str(r.get("target") or ""),
                                         "quote": str(r.get("quote") or ""),
                                         "counter": str(r.get("counter") or ""),
                                         "basis": str(r.get("basis") or "")}
                                        for r in t["rebut"] if isinstance(r, dict)
                                    ]
                                _content = str(t["content"])
                                if t.get("say") is not None and t["say"] != _content:
                                    _m["say"] = str(t["say"])          # 회의 버블 — 화면이 그린다(본문은 content)
                                if isinstance(t.get("say_full_chars"), int) and t["say_full_chars"] > len(_content):
                                    # 엔진이 줄이지 않은 글마저 DELIB_TRANSCRIPT_CLIP 에서 잘랐다 — 원래 길이를 남긴다.
                                    _m["say_full_chars"] = t["say_full_chars"]
                                store.append(conversation_id=cid, owner_sub=owner, role="persona",
                                             content=_content,
                                             persona=(str(t["persona"])[:120] if t.get("persona") else None),
                                             round=(int(t["round"]) if isinstance(t.get("round"), int) else None),
                                             meta=(_m or None))
                            reply = final if final is not None else (decision or "".join(acc))
                            if not reply and routine_turn and routine_ptr:
                                reply = _ROUTINE_EMPTY_REPLY   # 글 없이 끊긴 루틴 턴 — 그래도 남겨 run_id 를 잃지 않는다
                            if not reply and cancelled:
                                # 결정문 없이 멈춘 심의 — 멈춤을 답으로 남긴다. 화면은 meta.delib_cancelled.message 와 같은 글을 결정문으로 읽지 않는다
                                reply = cancelled["message"] = cancelled["message"] or "(심의를 멈췄다)"
                            if reply:
                                _am = {k: v for k, v in (("activity", activity), ("delib_evidence", delib_ev),
                                                         ("user_images", user_images)) if v}
                                if cancelled:   # 사람이 멈춘 심의(triage A24) — 화면은 이 글을 결정문으로 읽지 않는다(serverMessagesToLocal)
                                    _am["delib_cancelled"] = cancelled
                                if routine_ptr:      # 분석 루틴 — 네 칸을 늘 싣는다(모르는 값은 null)
                                    _am["routine"] = {k: routine_ptr.get(k) for k in ("run_id", "routine_id", "title", "state")}
                                # 다른 탭의 중계가 같은 실행의 같은 끝 · 같은 글을 이미 남겼으면 넣지 않는다 — 보고서가 두 번 남지 않게. 이 턴의
                                # 사용자 발화는 시작할 때 이미 남았다. 글이 다르면(끝난 실행의 RA 초안 올리기 안내) 이 턴의 답이라 남긴다.
                                if _rt_key is None or not _routine_answered(store.get(cid, owner), _rt_key[1],
                                                                            routine_ptr["state"], reply):
                                    store.append(conversation_id=cid, owner_sub=owner, role="assistant", content=reply,
                                                 meta=(_am or None))
                        except sqlite3.Error as exc:
                            logger.warning("대화 저장 실패 — %s(잠금 대기 CONV_STORE_BUSY_TIMEOUT_S=%s초), cid=%s · 심의 발언 %d건과 "
                                           "최종 응답 중 일부가 서버 대화에 없다", exc, settings.conv_store_busy_timeout_s, cid,
                                           len(turns))

                    with anyio.CancelScope(shield=True):
                        async with (_routine_save_lock(_rt_key) if _rt_key else contextlib.nullcontext()):
                            await anyio.to_thread.run_sync(_save)
                    # 이 턴의 도구 호출을 **절차 원장**에도 남긴다 — 하나의 원장, 세 생산자
                    # (PLAN §9-9). 대화 저장과 별개이고, 실패해도 챗을 막지 않는다.
                    # 루틴 턴은 건너뛴다 — 그 호출은 루틴 원장(routine_calls)에 이미 있어 여기 또 넣으면 두 벌이다(R3 D9).
                    _pstore = getattr(request.app.state, "procedures_store", None)
                    if _pstore is not None and activity and cid and not routine_turn:
                        from app.procedures import from_chat as _fc

                        _fc.record(_pstore, owner_sub=owner, conversation_id=cid,
                                   activity=activity,
                                   title=(str(body.message or "")[:60].strip() or None))


        nonlocal pumping
        task = asyncio.create_task(pump())
        pumping = True               # 루틴 턴의 퍼밋은 이제 pump 의 finally 가 돌려준다(_on_close 는 손대지 않는다)
        try:
            while True:
                frame = await q.get()
                if frame is _RELAY_DONE:
                    break
                pending -= len(frame)
                room.set()
                yield frame
            # 상류 쪽 예외는 종전처럼 응답을 끊는다. 루틴 턴은 가린다 — pump 의 finally 를 기다리는 사이 브라우저가 떠나면 이 취소가
            # 기다리던 pump 로 번진다. finally 를 감싼 anyio CancelScope(shield) 는 asyncio 취소를 막지 못해(실측), 상류를 닫는 await
            # (pump 가 터져 끝났을 때)에서 끊기면 퍼밋 반납 · 저장을 건너뛴다 — 루틴 턴은 퍼밋을 pump 만 돌려주므로 영영 샌다.
            await (asyncio.shield(task) if routine_turn else task)
        finally:
            if routine_turn and not task.done() and len(_DETACHED_RELAYS) < _DETACHED_RELAYS_MAX:
                # 브라우저가 떠났다 — 루틴 턴은 상류를 끝까지 읽어 대화에 남긴다(R3 D9). 취소하지 않고 기다리지도 않는다(실행은 분 ~ 시간이다).
                # 이벤트 루프는 작업을 약하게만 쥐므로 모듈 집합이 쥔다. 저장 · 퍼밋 반납은 pump 의 finally 가 한 번 한다.
                detached = True
                room.set()           # 상한 대기(room.wait)에 서 있던 pump 를 깨운다
                while not q.empty():
                    q.get_nowait()   # 아무도 안 읽을 프레임 — 메모리를 놓는다
                _DETACHED_RELAYS.add(task)
                task.add_done_callback(_detached_relay_done)
            else:
                if routine_turn and not task.done():
                    # 떼어 낸 중계가 상한만큼 돈다 — 이 루틴 턴은 일반 턴처럼 상류를 끊는다. 에이전트 서버의 실행은 따로 떼어 낸 작업이라 계속 돌고,
                    # 받은 데까지와 실행 포인터는 pump 의 finally 가 남긴다. 퍼밋은 아래에서 돌려준다(_on_close 는 루틴 턴에 손대지 않는다).
                    logger.warning("루틴 턴 중계 — 떼어 낸 중계가 상한 %d개에 닿아 브라우저가 떠난 이 턴은 상류를 끊는다. 실행은 에이전트 "
                                   "서버에서 계속 돈다('이어서' 로 다시 붙는다) run_id=%s sub=%s",
                                   _DETACHED_RELAYS_MAX, routine_ptr.get("run_id"), owner)
                if not task.done():
                    task.cancel()        # 브라우저가 떠났다 — 상류도 끊는다(pump 의 finally 가 받은 것까지 저장한다)
                with anyio.CancelScope(shield=True):
                    await asyncio.gather(task, return_exceptions=True)
                _release()

    return _ReleasingStream(gen(), _on_close, media_type="text/event-stream", headers=SSE_HEADERS)


# ── 카드 대조 중계(리스크 심사 재설계 M2 · WP3a P1) ─────────────────────────────────────────────────────
# 리스크 앱 검토 러너가 PAT 로 부르면 본문을 **통째로** 에이전트 서버 /card-review/{limits|pack|plan|run} 으로 넘긴다. 칸을 선언해
# 하나씩 옮기지 않는다 — 위 ChatRequest·DelibOpts 의 흉터대로, 선언하지 않은 칸은 조용히 사라진다. 포털이 하는 일은 넷이다.
#   · 권한 — feat:deliberation. 없으면 403 이고 에이전트 서버로 아무것도 안 나간다(pack 은 카드 원문을 돌려준다).
#   · 신원 — groups·user_email·user_pat·entitlements 넷을 검증된 주체로 덮어쓰고 나머지 칸은 손대지 않는다. 호출자가 실어 보낸
#     신원은 버린다 — 통째로 넘기는 중계의 유일한 구멍이다(spec-wp5b 3.10.2).
#   · 크기 — 원 본문이 _WINDOW_CHARS 바이트를 넘으면 413. 창에 넣을 길이는 창을 아는 엔진이 정한다(넘으면 엔진의 422 over_budget).
#   · 감사 — 주체·종류·전문가 키·단위 id·본문 바이트 수·sha256·상류 상태(와 오류 code)만. 본문은 싣지 않는다.
# 대화를 만들지 않고 /agent/chat 을 타지 않는다(M2 나갈 기준 3 — 포털 대화 목록에 새 대화가 없다). 챗과 연결·퍼밋을 다투지 않게
# 전용 클라이언트·세마포어를 쓴다(main.py — P-14). 오류 어휘는 docs/risk-review-redesign/M2.md 4.4 다 — 리스크 앱이 code 하나로
# 부류(기다림·인프라·잡 보류·내용 탓)를 가르고 표에 없는 code 는 '내용 탓'(차감)이 되므로 여기서 새 이름을 지어내지 않는다.
# 중계가 새로 낸 이름은 본문 상한의 body_too_large(413) 하나이고 표의 '내용 탓' 칸에 적었다 — 같은 본문은 다시 보내도 넘는다.
# 외부 응답자(docs/risk-claude-engine — 기본 꺼짐)의 llm·consent_external 은 plan·run 본문의 다른 칸처럼 손대지 않고 지나간다. 보내는
# 곳은 리스크 앱뿐이고, 사람에게 반출 동의를 받는 것도 그 앱의 몫이다(엔진은 consent_external: true 가 없는 외부 run 을 거절한다).
# limits 는 GET 이라 llm 을 질의 문자열로 받는다 — _CR_LIMITS_QUERY.

_CR_RETRY_AFTER_S = 30       # engine_busy 의 대기 — 엔진 관문 CARD_REVIEW_RETRY_AFTER_S 의 기본값과 같은 수
_CR_META_MAX = 200           # 감사에 옮기는 식별자 하나의 상한 — 식별자 칸에 본문을 실어 감사로 흘리지 못하게
# limits 질의 문자열에서 엔진에 옮기는 이름 — 엔진 GET /card-review/limits 가 읽는 것만이다. 지금은 llm 하나다(?llm=external 이면 외부
# 응답자의 창·출력 상한으로 셈한 예산과 판, 없거나 glm 이면 종전 그대로). 종전엔 질의 문자열을 통째로 버려 ?llm=external 에도 GLM 예산이
# 돌아왔다(X-3a). 값은 보지 않는다 — 본문의 llm 처럼 엔진이 정본이고, 모르는 값은 엔진의 422 bad_request 가 상태·본문 그대로 간다.
# 그 밖의 이름은 옮기지 않는다 — 엔진이 읽지 않으니 버려도 결과가 같고, 엔진이 나중에 읽게 될 이름(신원 칸 같은)이 포털의 검토 없이
# 지나가지 않는다. 엔진이 새 이름을 읽게 되면 tests/test_card_review_contract_replay.py 가 묻는다.
_CR_LIMITS_QUERY = ("llm",)


class _CrReject(Exception):
    """중계가 스스로 내는 거절. 본문은 엔진 오류와 같은 모양 {code, message, …} 이다 — 앱이 code 로 가른다."""

    def __init__(self, status: int, code: str, message: str, *, upstream: int | None = None,
                 headers: dict[str, str] | None = None, **extra: Any) -> None:
        super().__init__(message)
        self.status, self.code, self.upstream, self.headers = status, code, upstream, headers
        self.body = {"code": code, "message": message, **({"upstream": upstream} if upstream is not None else {}), **extra}

    def response(self) -> JSONResponse:
        return JSONResponse(status_code=self.status, content=self.body, headers=self.headers)


def _cr_sem(request: Request) -> asyncio.Semaphore:
    return request.app.state.card_review_semaphore


def _cr_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.card_review_client


def _cr_busy(what: str) -> _CrReject:
    """기다림 부류 — 앱은 아무것도 세지 않고 retry_after_s 뒤 같은 호출을 다시 낸다. 줄을 세우지 않는다(줄은 엔진 관문 하나다)."""
    return _CrReject(429, "engine_busy", f"{what} — {_CR_RETRY_AFTER_S}초 뒤 같은 호출을 다시 낸다",
                     retry_after_s=_CR_RETRY_AFTER_S, headers={"Retry-After": str(_CR_RETRY_AFTER_S)})


async def _cr_read(request: Request) -> tuple[bytes, dict]:
    """원 본문(바이트)과 그 JSON 객체. 상한을 넘는 순간 읽기를 멈춘다 — 앞단 nginx 가 2GB 까지 받으므로 다 읽은 뒤 재지 않는다."""
    def too_large(n: int | None) -> _CrReject:
        return _CrReject(413, "body_too_large",
                         f"본문{f' {n:,}바이트' if n else ''}가 상한 {_WINDOW_CHARS:,}바이트(1M 토큰 창 하나)를 넘는다 — 창에 들어갈 수 "
                         "없는 요청이라 자르지 않고 거절한다", max_bytes=_WINDOW_CHARS)

    cl = request.headers.get("content-length", "")
    if cl.isdigit() and int(cl) > _WINDOW_CHARS:
        raise too_large(int(cl))
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > _WINDOW_CHARS:
            raise too_large(None)
    raw = bytes(buf)
    try:
        obj = json.loads(raw)
    except (ValueError, RecursionError):
        raise _CrReject(422, "bad_request", "본문이 JSON 이 아니다") from None
    if not isinstance(obj, dict):
        raise _CrReject(422, "bad_request", "본문은 JSON 객체여야 한다")
    return raw, obj


def _cr_payload(request: Request, settings: Settings, principal: Principal, obj: dict) -> bytes:
    """호출자 본문에 신원 칸 넷만 덮어쓴다(호출자가 실어 보낸 값은 버린다). 나머지 칸은 선언하지 않은 것까지 그대로 간다."""
    ident = {"groups": principal.groups,
             "user_email": principal.email,
             # /chat 과 같은 규칙 — None 이 아니라 빈 문자열이 '없음' 이다(엔진은 서비스 계정으로 내려가지 않고 credential_missing 이다).
             "user_pat": _chat_user_pat(request.app.state.keystore, settings, principal) or "",
             "entitlements": sorted(g for g in principal.groups if is_synthetic(g))}
    return json.dumps({**obj, **ident}, ensure_ascii=False).encode()


def _cr_meta(raw: bytes, obj: dict) -> dict:
    """감사 칸 — 종류·전문가 키·단위 id·본문 바이트 수·sha256. 본문은 싣지 않는다. 요약(kind summary — 전문가·단위가 없다)은
    범위 키(summary.scope.key — 영역 코드 또는 '-')를 단위 자리에 싣는다(M3 P3-1)."""
    expert, unit, summary = obj.get("expert"), obj.get("unit"), obj.get("summary")
    scope = summary.get("scope") if isinstance(summary, dict) else None
    ids = {"kind": obj.get("kind"),
           "agent": (expert.get("key") if isinstance(expert, dict) else None) or obj.get("agent_key"),
           "unit": (unit.get("unit_id") if isinstance(unit, dict) else None)
           or (scope.get("key") if isinstance(scope, dict) else None)}
    meta = {k: str(v)[:_CR_META_MAX] for k, v in ids.items() if v is not None}
    if raw:
        meta.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return meta


def _cr_audit(request: Request, principal: Principal, route: str, meta: dict, *,
              upstream: int | None = None, code: str | None = None, status: str = "ok") -> None:
    extra = {k: v for k, v in (("upstream", upstream), ("code", code)) if v is not None}
    _audit(request).record(principal=principal.subject, status=status, meta={**meta, **extra},
                           event=f"card_review_{route}_{'done' if status == 'ok' else 'error'}")


def _cr_fail(request: Request, principal: Principal, route: str, meta: dict, rej: _CrReject) -> JSONResponse:
    # 에이전트 서버에 닿기 전에 포털이 막은 것(본문·자리)은 rejected, 닿으려다 실패한 것은 error 다.
    mine = rej.upstream is None and rej.status in (413, 422, 429)
    _cr_audit(request, principal, route, meta, upstream=rej.upstream, code=rej.code,
              status="rejected" if mine else "error")
    return rej.response()


def _cr_upstream_code(r: httpx.Response) -> str | None:
    """에이전트 서버 오류 본문의 code — 최상위이거나 FastAPI detail 안이다. 못 읽으면 None."""
    try:
        body = r.json()
    except ValueError:
        return None
    if isinstance(body, dict) and isinstance(body.get("detail"), dict):
        body = body["detail"]
    code = body.get("code") if isinstance(body, dict) else None
    return str(code)[:_CR_META_MAX] if code else None


def _cr_answer(r: httpx.Response) -> Response:
    """에이전트 서버의 답(본문까지 읽은 것)을 상태·본문 그대로 넘긴다 — 4xx 도 그대로다(앱이 code·need·have 를 읽는다).
    엔진이 code 를 실은 5xx 도 그대로다 — 팩의 tools_unavailable(503)·card_list_failed·card_list_unstable·card_fetch_failed(502)는
    앱이 팩 재시도로 가르는 어휘다(M2.md 4.4). 502 agent_5xx 로 덮으면 그 구분이 사라진다.
    code 가 없는 것 둘만 바꾼다. 404 면 이 경로를 모르는 옛 에이전트 서버다(agent_outdated — 앱은 잡을 보류하고 300초 뒤 다시 본다.
    엔진의 404 agent_not_found 는 code 가 있어 그대로 간다). 5xx 면 엔진이 죽었거나 앞단이 낸 것이라 502 agent_5xx 다(본문은
    되싣지 않는다)."""
    code = _cr_upstream_code(r)
    if code is None and r.status_code >= 500:
        raise _CrReject(502, "agent_5xx", f"에이전트 서버 오류(HTTP {r.status_code})", upstream=r.status_code)
    if code is None and r.status_code == 404:
        raise _CrReject(404, "agent_outdated", "에이전트 서버에 카드 대조 경로가 없다 — 옛 판이다. 에이전트 서버를 카드 대조가 든 "
                        "판으로 올리고 다시 띄운다", upstream=404)
    headers = {"Retry-After": r.headers["retry-after"]} if "retry-after" in r.headers else None
    return Response(content=r.content, status_code=r.status_code, headers=headers,
                    media_type=r.headers.get("content-type", "application/json"))


def _cr_transport(exc: httpx.HTTPError, read_s: float | None, knob: str) -> _CrReject:
    """에이전트 서버에 닿지 못했거나 답이 늦었다. 시간 초과는 기본값으로 진행하지 않는다 — 도우미의 폴백 규칙(_unary_fail)과
    다르다. 앱은 agent_timeout·agent_unreachable 을 인프라로 치고 차감 없이 다시 낸다."""
    if isinstance(exc, httpx.PoolTimeout):
        # 전용 풀(run 동시 수 + 4)이 찼다 — 엔진에 닿지도 않았으니 기다림이다.
        return _cr_busy("카드 대조 중계의 연결 풀이 찼다(CARD_REVIEW_MAX_STREAMS + 4)")
    if isinstance(exc, httpx.ReadTimeout):
        return _CrReject(504, "agent_timeout", f"에이전트 서버 응답이 {read_s or 0:.0f}초 안에 오지 않았다({knob})",
                         knob=knob, timeout_s=read_s)
    return _CrReject(502, "agent_unreachable", f"에이전트 서버에 연결하지 못했다({type(exc).__name__})")


async def _cr_unary(request: Request, principal: Principal, settings: Settings, route: str) -> Response:
    """limits(GET)·pack·plan — 단발 JSON. read 는 AGENT_UNARY_TIMEOUT_S(600초)이고 넘으면 504 agent_timeout 이다."""
    ensure(principal, "feat:deliberation")
    raw, obj = b"", {}
    try:
        if request.method == "POST":
            raw, obj = await _cr_read(request)
        content = _cr_payload(request, settings, principal, obj) if request.method == "POST" else None
        # GET(limits)은 질의 문자열에서 엔진이 읽는 이름만 옮긴다(_CR_LIMITS_QUERY). 없으면 종전과 같은 주소다.
        params = ({k: request.query_params[k] for k in _CR_LIMITS_QUERY if k in request.query_params}
                  if request.method == "GET" else None)
        try:
            r = await _cr_client(request).request(
                request.method, f"{settings.agent_server_url}/card-review/{route}", content=content,
                params=params or None,
                headers={"content-type": "application/json"} if content is not None else None,
                timeout=_unary_timeout(settings))
        except httpx.HTTPError as exc:
            raise _cr_transport(exc, settings.agent_unary_timeout_s, "AGENT_UNARY_TIMEOUT_S") from exc
        out = _cr_answer(r)
    except _CrReject as rej:
        return _cr_fail(request, principal, route, _cr_meta(raw, obj), rej)
    bad = r.status_code >= 400
    _cr_audit(request, principal, route, _cr_meta(raw, obj), upstream=r.status_code,
              code=_cr_upstream_code(r) if bad else None, status="error" if bad else "ok")
    return out


@router.get("/card-review/limits")
async def card_review_limits(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """이 박스의 카드 대조 예산과 판(에이전트 서버 GET /card-review/limits). 404 면 옛 에이전트 서버다(agent_outdated)."""
    return await _cr_unary(request, principal, settings, "limits")


@router.post("/card-review/pack")
async def card_review_pack(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """전문가 한 명의 지식카드 전부 → 정규 팩. 엔진이 이 사람의 user_pat 으로만 게이트웨이에 붙는다(서비스 계정으로 내려가지 않는다)."""
    return await _cr_unary(request, principal, settings, "pack")


@router.post("/card-review/plan")
async def card_review_plan(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """카드 묶음·목록 쪽 나누기(엔진의 순수 계산)."""
    return await _cr_unary(request, principal, settings, "plan")


class _CrRun:
    """흐르는 run 한 건 — 상류 응답을 닫고 퍼밋을 돌려주고 마지막 감사를 **한 번만** 남긴다. 생성기의 finally 와 응답의 finally
    둘 다 부른다 — 생성기는 한 번도 돌지 않으면(헤더를 보내다 끊김) finally 도 돌지 않아, 퍼밋이 새고 엔진은 듣는 이 없는 LLM
    호출을 끝까지 돈다."""

    def __init__(self, request: Request, principal: Principal, sem: asyncio.Semaphore, meta: dict,
                 r: httpx.Response) -> None:
        self.request, self.principal, self.sem, self.meta, self.r = request, principal, sem, meta, r
        self.code: str | None = None   # 지나간 error 프레임의 code(엔진이 냈거나 중계가 냈다)
        self.result = False            # result 프레임이 지나갔다
        self.done = False              # done 프레임이 지나갔다 — 그 뒤에 끊겨도 중계는 아무것도 덧붙이지 않는다
        self.ended = False             # 상류가 스스로 끝났다 — 끝 프레임 없이 끝났으면 끊긴 것이다
        self._closed = False

    def saw(self, frame: bytes) -> None:
        """완결된 프레임 하나 — 이름만 본다(result 는 크다). error 일 때만 data 를 읽는다."""
        name = next((ln[6:].strip() for ln in frame.split(b"\n") if ln.startswith(b"event:")), None)
        if name == b"result":
            self.result = True
        elif name == b"done":
            self.done = True
        elif name == b"error":
            parsed = _parse_sse_frame(frame.decode(errors="replace"))
            data = parsed[1] if parsed else None
            self.code = str((data.get("code") if isinstance(data, dict) else None) or "error")[:_CR_META_MAX]

    def cut(self, buf: bytes, code: str, message: str, **extra: Any) -> bytes:
        """끊겼을 때 중계가 내는 끝 — error 와 done. 상류가 이미 done 을 냈으면 덧붙이지 않는다. 반쯤 온 프레임이 있으면 먼저
        닫는다 — 안 닫으면 그 조각과 이 프레임이 한 프레임으로 붙어 앱이 둘 다 못 읽는다."""
        if self.done:
            return b""
        self.code = code
        return ((b"\n\n" if buf else b"")
                + sse_event("error", {"code": code, "message": message, "infra": True, "retryable": True, **extra})
                + sse_event("done", {}))

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            # 가린다 — 취소된 채 만난 await 는 곧바로 다시 취소돼 연결을 못 닫는다. 연결이 닫혀야 엔진이 LLM 태스크를 거둔다.
            with anyio.CancelScope(shield=True):
                await self.r.aclose()
        finally:
            self.sem.release()
            code = self.code or (None if self.result else ("engine_stream_cut" if self.ended else "client_closed"))
            _cr_audit(self.request, self.principal, "run", self.meta, upstream=self.r.status_code, code=code,
                      status="ok" if code is None else ("cancelled" if code == "client_closed" else "error"))


async def _cr_frames(run: _CrRun, idle_s: float | None) -> AsyncIterator[bytes]:
    """상류 바이트를 그대로 흘리며 프레임 이름만 훑는다(감사의 결과 code). 프레임을 만들지 않는다 — ping 도 엔진 것만 넘긴다
    (중계가 만들면 멈춘 엔진이 살아 있는 것으로 보인다). 끊겼을 때만 error·done 둘을 낸다."""
    buf = b""                          # 아직 끝나지 않은 프레임(경계 \n\n 전까지)
    try:
        async for chunk in run.r.aiter_raw():
            if not chunk:
                continue
            buf += chunk
            while (i := buf.find(b"\n\n")) >= 0:
                run.saw(buf[:i])
                buf = buf[i + 2:]
            yield chunk
        run.ended = True
    except httpx.ReadTimeout:
        # 침묵 한도(AGENT_STREAM_IDLE_TIMEOUT_S) — 엔진은 15초마다 ping 을 내므로 멈춘 엔진이다. 연결을 닫아 엔진이 거두게 한다.
        if tail := run.cut(buf, "agent_stream_idle",
                           f"에이전트 서버가 {idle_s or 0:.0f}초 동안 아무 신호도 보내지 않아 중계가 구독을 끊었다"
                           "(AGENT_STREAM_IDLE_TIMEOUT_S)", knob="AGENT_STREAM_IDLE_TIMEOUT_S", idle_s=idle_s):
            yield tail
    except httpx.HTTPError as exc:
        # 도중에 끊겼다(재기동·연결 리셋) — 인프라다. 앱은 차감 없이 같은 호출을 다시 낸다.
        if tail := run.cut(buf, "agent_unreachable", f"에이전트 서버 스트림이 도중에 끊겼다({type(exc).__name__})"):
            yield tail
    finally:
        await run.close()


class _CrStream(StreamingResponse):
    """run 의 SSE 응답 — 끝나든 끊기든 run.close() 가 돈다(생성기 finally 의 짝 — _CrRun 주석)."""

    def __init__(self, run: _CrRun, content: AsyncIterator[bytes]) -> None:
        super().__init__(content, media_type="text/event-stream", headers=SSE_HEADERS)
        self._run = run

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            await self._run.close()


@router.post("/card-review/run")
async def card_review_run(
    request: Request,
    principal: Principal = Depends(principal_pat_or_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """카드 대조 호출 한 건(SSE) — 바이트를 그대로 흘린다. 스트림 전 거절(422·409·403 …)은 상태 그대로, 자리가 없으면 429
    engine_busy, 침묵 한도에 걸리면 error{agent_stream_idle}, 앱 쪽이 끊으면 에이전트 쪽 연결도 닫는다(엔진이 LLM 을 거둔다).
    상태를 그대로 넘기려면 응답을 시작하기 전에 상류의 상태를 알아야 해서, 상류를 여기서 열고 스트림에 넘긴다."""
    ensure(principal, "feat:deliberation")
    sem = _cr_sem(request)
    raw, obj = b"", {}
    try:
        raw, obj = await _cr_read(request)
        # /chat 과 같은 규칙 — locked() 와 acquire() 사이에 await 가 없어 원자적이다. 줄을 세우지 않고 거절한다.
        if sem.locked():
            raise _cr_busy(f"카드 대조 중계가 꽉 찼다(동시 {settings.card_review_max_streams}건 — CARD_REVIEW_MAX_STREAMS)")
    except _CrReject as rej:
        return _cr_fail(request, principal, "run", _cr_meta(raw, obj), rej)
    meta = _cr_meta(raw, obj)
    await sem.acquire()
    handed = False
    # ⚠ acquire 와 스트림을 넘기는 사이는 보호한다(/chat 의 ⚠ 와 같은 까닭) — 여기서 새면 퍼밋이 영구히 사라진다.
    try:
        _audit(request).record(principal=principal.subject, event="card_review_run_start", meta=meta)
        client = _cr_client(request)
        try:
            r = await client.send(client.build_request(
                "POST", f"{settings.agent_server_url}/card-review/run",
                content=_cr_payload(request, settings, principal, obj),
                headers={"content-type": "application/json"}), stream=True)
        except httpx.HTTPError as exc:
            raise _cr_transport(exc, client.timeout.read, "AGENT_STREAM_IDLE_TIMEOUT_S") from exc
        if r.status_code != 200:
            try:
                await r.aread()
            except httpx.HTTPError as exc:
                raise _cr_transport(exc, client.timeout.read, "AGENT_STREAM_IDLE_TIMEOUT_S") from exc
            finally:
                await r.aclose()
            out = _cr_answer(r)
            bad = r.status_code >= 400
            _cr_audit(request, principal, "run", meta, upstream=r.status_code,
                      code=_cr_upstream_code(r) if bad else None, status="error" if bad else "ok")
            return out
        run = _CrRun(request, principal, sem, meta, r)
        handed = True
        return _CrStream(run, _cr_frames(run, client.timeout.read))
    except _CrReject as rej:
        return _cr_fail(request, principal, "run", meta, rej)
    finally:
        if not handed:
            sem.release()
