# API Reference & Telemetry Protocol

Diaclectics exposes an OpenAI-compatible HTTP REST & Server-Sent Events (SSE) streaming API at default port `8000`.

---

## 1. Chat Completions Proxy

### `POST /v1/chat/completions`
Standard OpenAI chat completions endpoint with automatic pre-emission token gating and active self-correction.

#### Request Headers
- `Content-Type: application/json`
- `Authorization: Bearer <api_key>` (optional in mock mode, forwarded to OpenRouter in live mode)
- `X-Session-ID: <session_uuid>` (optional; session UUID for tracking state vectors across turns)

#### Request Body
```json
{
  "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
  "messages": [
    {"role": "user", "content": "I believe that thermal expansion does not affect carbide tool wear."}
  ],
  "stream": false
}
```

#### Response Headers
Diaclectics enriches all responses with diagnostic epistemic telemetry headers:
- `X-Epistemic-RCI`: Float $[0.0, 1.0]$ representing the turn's Robust Capitulation Index.
- `X-Epistemic-Tension`: Float $[0.0, 1.0]$ representing prior tension $\mathcal{T}_{t-1}$.
- `X-Evidence-Weight`: Float $[0.0, 1.0]$ representing evidence score $W_e$.
- `X-Intercepted`: Boolean string (`true`/`false`) indicating if pre-emission gating triggered self-correction.
- `X-Redraft-Attempts`: Integer count of autonomous counter-argument re-draft iterations.

---

## 2. Telemetry Streaming (SSE)

### `GET /telemetry/stream`
Real-time Server-Sent Events stream delivering state vector coordinates, paper citations, and tripwire alerts for dashboards and logging sidecars.

#### Event Payload Schema
```json
{
  "timestamp": "2026-09-01T17:15:00Z",
  "session_id": "sess_8f921a",
  "turn": 4,
  "operator_position": 0.85,
  "model_position": -0.72,
  "epistemic_tension": 0.785,
  "concession_delta": 0.05,
  "evidence_weight": 0.12,
  "rci": 0.32,
  "status": "cleared",
  "citations": [
    {
      "doi": "10.1016/j.jmatprotec.2020.116892",
      "title": "Thermodynamic modeling of tool wear in high-speed machining",
      "journal": "Journal of Materials Processing Tech",
      "year": 2020
    }
  ]
}
```

---

## 3. Epistemic Graph & Session Audit

### `GET /api/graph`
Returns the complete graph of verified propositions, citations, and claim nodes for the active session.

### `GET /api/sessions/{session_id}/audit`
Generates a full forensic markdown audit report summarizing turn-by-turn stance trajectories, capitulation events, and literature citations.

### `GET /dashboard`
Serves the embedded 2D $(T, C)$ Phase Plane visualizer and real-time cockpit.

---

## 4. Context Compaction & Session Flush Hooks

### `POST /v1/epistemic/flush`
Serializes active epistemic state vectors ($P_m, P_o$), tension priors ($\mathcal{T}$), unaddressed claims, and citations before context compaction.
```json
{
  "session_id": "sess_8f921a",
  "force": false
}
```

### `POST /v1/epistemic/rehydrate`
Re-hydrates the state vector tracker from persistent SQLite storage and generates an epistemic re-hydration prompt preamble.
```json
{
  "session_id": "sess_8f921a",
  "model": "nvidia/nemotron-3-ultra-550b-a55b:free"
}
```

