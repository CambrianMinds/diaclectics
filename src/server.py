"""OpenAI-Compatible Proxy Middleware API Server for Dialectical Telemetry.

Exposes standard /v1/chat/completions and /v1/models endpoints so that any
OpenAI-compatible client (Open-WebUI, LibreChat, Cursor, Continue.dev) can connect
to Diaclectics for real-time anti-sycophancy interception and epistemic telemetry streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Union
from fastapi import FastAPI, Header, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import BaseLLMClient, MockLLMClient, OpenRouterLLMClient
from src.storage import EpistemicKnowledgeStore, EpistemicSessionFlushManager
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    MultiAxisPolarAnchor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
)
from src.verifier import EpistemicValidator

logger = logging.getLogger("diaclectics.server")

STATIC_DIR = Path(__file__).parent / "web" / "static"
epistemic_store = EpistemicKnowledgeStore()
flush_manager = EpistemicSessionFlushManager(store=epistemic_store)


app = FastAPI(
    title="Diaclectics Proxy Middleware API",
    description="OpenAI-compatible proxy with real-time epistemic telemetry & anti-sycophancy interception.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Real-Time Telemetry Broadcast Hub (SSE + WebSockets)
# ---------------------------------------------------------------------------


class TelemetryBroadcastHub:
    """Manages live subscriber queues for SSE & WebSocket dashboard telemetry."""

    def __init__(self) -> None:
        self._sse_queues: Set[asyncio.Queue] = set()
        self._ws_clients: Set[WebSocket] = set()

    def subscribe_sse(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._sse_queues.add(q)
        return q

    def unsubscribe_sse(self, q: asyncio.Queue) -> None:
        self._sse_queues.discard(q)

    def register_ws(self, ws: WebSocket) -> None:
        self._ws_clients.add(ws)

    def unregister_ws(self, ws: WebSocket) -> None:
        self._ws_clients.discard(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcast telemetry event to all connected dashboard clients."""
        # 1. SSE broadcast
        dead_queues = []
        for q in self._sse_queues:
            try:
                q.put_nowait(payload)
            except Exception:
                dead_queues.append(q)
        for q in dead_queues:
            self._sse_queues.discard(q)

        # 2. WebSocket broadcast
        dead_ws = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_ws.append(ws)
        for ws in dead_ws:
            self._ws_clients.discard(ws)


telemetry_hub = TelemetryBroadcastHub()


# ---------------------------------------------------------------------------
# OpenAI Schema Models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False
    session_id: Optional[str] = "default"
    thesis: Optional[str] = None
    antithesis: Optional[str] = None


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Dict[str, int]
    dialectical_telemetry: Optional[Dict[str, Any]] = None


# Session State Cache
_session_runners: Dict[str, DialecticalChatRunner] = {}


def get_or_create_runner(
    session_id: str,
    model: str,
    thesis: Optional[str] = None,
    antithesis: Optional[str] = None,
) -> DialecticalChatRunner:
    """Retrieve or instantiate an active DialecticalChatRunner for a session."""
    if session_id in _session_runners:
        runner = _session_runners[session_id]
        if hasattr(runner.llm_client, "model") and runner.llm_client.model != model:
            runner.llm_client.model = model
        return runner

    engine = DialecticalEngine()
    engine.evidence_scorer.active_validator = EpistemicValidator()

    polar_anchor = PolarAnchor(
        thesis_statement=thesis or "Precision megalithic stonework exhibits non-standard tool kinematics and advanced machining.",
        antithesis_statement=antithesis or "Orthodox Bronze Age tools and manual techniques fully explain all ancient stonework.",
        axis_name="general_axis",
    )

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if model.startswith("mock") or not api_key:
        stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())
        llm_client = MockLLMClient(default_response="Forensic witness marks constrain cutting tool geometry.")
    else:
        embed_client = OpenRouterEmbeddingClient(api_key=api_key)
        stance_extractor = CompositeStanceExtractor(
            embedding_extractor=EmbeddingStanceExtractor(client=embed_client, default_anchor=polar_anchor)
        )
        llm_client = OpenRouterLLMClient(api_key=api_key, model=model)

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=stance_extractor,
        llm_client=llm_client,
        polar_anchor=polar_anchor,
        enable_auto_redraft=True,
    )

    _session_runners[session_id] = runner
    return runner


# ---------------------------------------------------------------------------
# Dashboard UI Routes
# ---------------------------------------------------------------------------


@app.get("/")
@app.get("/dashboard")
@app.get("/dashboard/")
async def serve_dashboard() -> FileResponse:
    """Serve the real-time visual telemetry dashboard."""
    dashboard_path = STATIC_DIR / "dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    return FileResponse(str(dashboard_path))


@app.get("/v1/telemetry/stream")
async def sse_telemetry_stream(session_id: Optional[str] = "default") -> StreamingResponse:
    """Server-Sent Events endpoint broadcasting real-time dialectical telemetry."""
    queue = telemetry_hub.subscribe_sse()

    async def event_generator():
        try:
            # Send initial session snapshot if available
            init_history = []
            if session_id in _session_runners:
                runner = _session_runners[session_id]
                for rec in runner.engine.tracker.history:
                    init_history.append({
                        "turnIndex": rec.turn_index,
                        "concession": 0.0,
                        "tension": 0.0,
                        "evidenceWeight": 0.0,
                        "rci": 0.0,
                        "operatorStance": rec.operator_position.scalar_value,
                        "modelStance": rec.model_position.scalar_value,
                        "severity": "NOMINAL",
                        "isIntercepted": False,
                    })

            yield f"data: {json.dumps({'type': 'init', 'session_id': session_id, 'history': init_history})}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
        except Exception as e:
            logger.info(f"SSE client disconnected: {e}")
        finally:
            telemetry_hub.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/v1/telemetry/ws")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    """Bi-directional WebSocket endpoint for live dashboard telemetry and probes."""
    await websocket.accept()
    telemetry_hub.register_ws(websocket)
    try:
        await websocket.send_json({"type": "init", "status": "connected"})
        while True:
            data = await websocket.receive_text()
            # Handle ping or custom probe commands if received
            try:
                parsed = json.loads(data)
                if parsed.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        telemetry_hub.unregister_ws(websocket)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    """OpenAI-compatible models list endpoint."""
    return {
        "object": "list",
        "data": [
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "object": "model", "owned_by": "openrouter"},
            {"id": "deepseek/deepseek-chat", "object": "model", "owned_by": "deepseek"},
            {"id": "liquid/lfm-2.5-2.6b:free", "object": "model", "owned_by": "liquid"},
            {"id": "mock-dialectical-engine", "object": "model", "owned_by": "diaclectics"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, response: Response) -> Any:
    """Proxy chat completion with real-time epistemic telemetry & sycophancy interception."""
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    user_messages = [m for m in req.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="At least one user message is required")

    last_user_msg = user_messages[-1].content
    runner = get_or_create_runner(
        session_id=req.session_id or "default",
        model=req.model,
        thesis=req.thesis,
        antithesis=req.antithesis,
    )

    # Handle Streaming Mode with Pre-Emission Interception Gate
    if req.stream:
        async def event_generator():
            cmpl_id = f"chatcmpl-{int(time.time()*1000)}"
            gen = runner.stream_step(user_message=last_user_msg)
            try:
                for token in gen:
                    chunk = {
                        "id": cmpl_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req.model,
                        "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Synchronous Execution
    step_result = runner.step(user_message=last_user_msg)

    # Extract literature papers from validator if present
    retrieved_papers = []
    if (
        hasattr(step_result.evidence_score_result, "active_validation_report")
        and step_result.evidence_score_result.active_validation_report
    ):
        for s_res in step_result.evidence_score_result.active_validation_report.search_results:
            for p in s_res.papers_found:
                retrieved_papers.append(p.model_dump())

    # Attach telemetry headers
    cap_rep = step_result.suspect_agreement_result.capitulation_report
    ev_res = step_result.evidence_score_result
    response.headers["X-Dialectical-RCI"] = f"{cap_rep.capitulation_score:.3f}"
    response.headers["X-Dialectical-Tension"] = f"{cap_rep.epistemic_tension:.3f}"
    response.headers["X-Dialectical-Evidence-We"] = f"{ev_res.total_weight:.3f}"
    response.headers["X-Dialectical-Intercepted"] = str(step_result.is_intercepted).lower()
    response.headers["X-Dialectical-Self-Corrected"] = str(step_result.is_self_corrected).lower()

    telemetry_payload = {
        "turn_index": step_result.turn_index,
        "is_intercepted": step_result.is_intercepted,
        "is_self_corrected": step_result.is_self_corrected,
        "redraft_attempts": step_result.redraft_attempts,
        "original_sycophantic_draft": step_result.original_sycophantic_draft,
        "operator_stance": step_result.operator_stance.scalar_stance,
        "model_stance": step_result.proposed_model_stance.scalar_stance,
        "epistemic_tension": cap_rep.epistemic_tension,
        "local_concession": cap_rep.local_concession,
        "evidence_weight_we": ev_res.total_weight,
        "capitulation_score_rci": cap_rep.capitulation_score,
        "severity": cap_rep.severity,
        "epistemic_summary_why": ev_res.active_validation_summary or ev_res.justification_summary,
        "active_papers": retrieved_papers,
    }

    # Persist turn, propositions, and citations into Epistemic Memory Knowledge Store
    session_id_clean = req.session_id or "default"
    try:
        epistemic_store.record_turn(
            session_id=session_id_clean,
            turn_index=step_result.turn_index,
            speaker="operator",
            content=last_user_msg,
            position=step_result.operator_stance.position,
            rci_score=0.0,
            epistemic_tension=cap_rep.epistemic_tension,
            local_concession=0.0,
            evidence_weight=0.0,
        )
        epistemic_store.record_turn(
            session_id=session_id_clean,
            turn_index=step_result.turn_index,
            speaker="model",
            content=step_result.final_emitted_content,
            position=step_result.proposed_model_stance.position,
            rci_score=cap_rep.capitulation_score,
            epistemic_tension=cap_rep.epistemic_tension,
            local_concession=cap_rep.local_concession,
            evidence_weight=ev_res.total_weight,
            is_intercepted=step_result.is_intercepted,
            is_self_corrected=step_result.is_self_corrected,
            original_draft=step_result.original_sycophantic_draft,
        )
        if retrieved_papers:
            epistemic_store.record_citations(
                session_id=session_id_clean,
                turn_index=step_result.turn_index,
                papers=retrieved_papers,
            )
    except Exception as store_err:
        logger.warning(f"Failed to persist turn into EpistemicKnowledgeStore: {store_err}")

    # Broadcast turn telemetry to connected web dashboards
    asyncio.create_task(
        telemetry_hub.broadcast({
            "type": "turn_telemetry",
            "session_id": req.session_id or "default",
            "payload": {
                **telemetry_payload,
                "operator_input": last_user_msg,
                "emitted_content": step_result.final_emitted_content,
            },
        })
    )

    return ChatCompletionResponse(
        id=f"chatcmpl-{int(time.time()*1000)}",
        created=int(time.time()),
        model=req.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content=step_result.final_emitted_content,
                ),
                finish_reason="stop",
            )
        ],
        usage={"prompt_tokens": len(last_user_msg) // 4, "completion_tokens": len(step_result.final_emitted_content) // 4, "total_tokens": (len(last_user_msg) + len(step_result.final_emitted_content)) // 4},
        dialectical_telemetry=telemetry_payload,
    )


@app.get("/v1/telemetry/session/{session_id}")
async def get_session_telemetry(session_id: str) -> Dict[str, Any]:
    """Retrieve full historical state vector telemetry for a session."""
    if session_id not in _session_runners:
        raise HTTPException(status_code=404, detail="Session not found")

    runner = _session_runners[session_id]
    history = [t.model_dump() for t in runner.engine.tracker.history]
    return {
        "session_id": session_id,
        "total_turns": len(history),
        "history": history,
    }


@app.get("/v1/telemetry/graph")
async def get_epistemic_graph(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve the interactive proposition, citation, and session knowledge graph."""
    return epistemic_store.get_epistemic_knowledge_graph(session_id=session_id)


@app.get("/v1/telemetry/propositions")
async def get_propositions(
    status: Optional[str] = None, limit: int = 50
) -> Dict[str, Any]:
    """Retrieve list of discrete propositions across sessions."""
    props = epistemic_store.list_propositions(status=status, limit=limit)
    return {"total": len(props), "propositions": props}


@app.get("/v1/telemetry/claims")
async def search_claims(q: str, status: Optional[str] = None) -> Dict[str, Any]:
    """Search cross-session claims matching a query."""
    claims = epistemic_store.find_cross_session_claims(claim_query=q, status=status)
    return {"query": q, "total": len(claims), "claims": claims}


class DiscoveryRequest(BaseModel):
    path: str
    axis_name: Optional[str] = "custom_domain_axis"
    max_files: Optional[int] = 30



@app.post("/v1/calibration/discover")
async def discover_codebase_axis(req: DiscoveryRequest) -> Dict[str, Any]:
    """Scan workspace code, triangulate with OpenAlex, and generate proposed calibration anchors."""
    from src.calibration.codebase_discoverer import EpistemicCodebaseDiscoverer
    discoverer = EpistemicCodebaseDiscoverer()
    invariants = discoverer.scan_directory(req.path, max_files=req.max_files or 30)
    for inv in invariants:
        discoverer.triangulate_invariant(inv)

    seed_profile = None
    if invariants:
        seed_profile = discoverer.create_calibrated_seed_profile(
            req.axis_name or "custom_domain_axis", invariants
        ).model_dump()

    return {
        "path": req.path,
        "invariants_discovered": len(invariants),
        "invariants": [inv.model_dump() for inv in invariants],
        "draft_seed_profile": seed_profile,
    }


class EpistemicFlushRequest(BaseModel):
    session_id: str
    force: Optional[bool] = False


class EpistemicRehydrateRequest(BaseModel):
    session_id: str
    model: Optional[str] = "mock-dialectical-v1"


@app.post("/v1/epistemic/flush")
async def flush_session_state(req: EpistemicFlushRequest) -> Dict[str, Any]:
    """Flush active epistemic state vectors before context compaction or session exit."""
    if req.session_id not in _session_runners:
        raise HTTPException(status_code=404, detail="Active session runner not found")
    runner = _session_runners[req.session_id]
    audit_file = flush_manager.flush_on_pre_compact(
        session_id=req.session_id,
        tracker=runner.engine.tracker,
        force=bool(req.force),
    )
    snapshot = flush_manager.capture_snapshot(req.session_id, runner.engine.tracker)
    return {
        "session_id": req.session_id,
        "flushed": audit_file is not None,
        "audit_file": str(audit_file) if audit_file else None,
        "snapshot": snapshot.model_dump(),
    }


@app.post("/v1/epistemic/rehydrate")
async def rehydrate_session_state(req: EpistemicRehydrateRequest) -> Dict[str, Any]:
    """Rehydrate a session runner from persistent store after context compaction."""
    runner = get_or_create_runner(session_id=req.session_id, model=req.model or "mock-dialectical-v1")
    rehydrated = flush_manager.rehydrate_epistemic_context(req.session_id, runner.engine.tracker)
    snapshot = flush_manager.capture_snapshot(req.session_id, runner.engine.tracker)
    prompt = flush_manager.format_rehydration_prompt(snapshot)
    return {
        "session_id": req.session_id,
        "rehydrated": rehydrated,
        "rehydration_prompt": prompt,
        "snapshot": snapshot.model_dump(),
    }


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:


    """Run the proxy API server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
