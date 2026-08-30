"""OpenAI-Compatible Proxy Middleware API Server for Dialectical Telemetry.

Exposes standard /v1/chat/completions and /v1/models endpoints so that any
OpenAI-compatible client (Open-WebUI, LibreChat, Cursor, Continue.dev) can connect
to Diaclectics for real-time anti-sycophancy interception and epistemic telemetry streaming.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import BaseLLMClient, MockLLMClient, OpenRouterLLMClient
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
)
from src.verifier import EpistemicValidator

logger = logging.getLogger("diaclectics.server")

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
    )

    _session_runners[session_id] = runner
    return runner


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


from fastapi.responses import StreamingResponse

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

    # Attach telemetry headers
    cap_rep = step_result.suspect_agreement_result.capitulation_report
    ev_res = step_result.evidence_score_result
    response.headers["X-Dialectical-RCI"] = f"{cap_rep.capitulation_score:.3f}"
    response.headers["X-Dialectical-Tension"] = f"{cap_rep.epistemic_tension:.3f}"
    response.headers["X-Dialectical-Evidence-We"] = f"{ev_res.total_weight:.3f}"
    response.headers["X-Dialectical-Intercepted"] = str(step_result.is_intercepted).lower()

    telemetry_payload = {
        "turn_index": step_result.turn_index,
        "is_intercepted": step_result.is_intercepted,
        "operator_stance": step_result.operator_stance.scalar_stance,
        "model_stance": step_result.proposed_model_stance.scalar_stance,
        "epistemic_tension": cap_rep.epistemic_tension,
        "local_concession": cap_rep.local_concession,
        "evidence_weight_we": ev_res.total_weight,
        "capitulation_score_rci": cap_rep.capitulation_score,
        "severity": cap_rep.severity,
        "epistemic_summary_why": ev_res.active_validation_summary or ev_res.justification_summary,
    }

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


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the proxy API server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
