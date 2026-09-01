# System Architecture & Technical Design

**Diaclectics** is designed as a non-invasive, ultra-low-latency epistemic telemetry and anti-sycophancy interception layer that operates between conversational user interfaces (or autonomous agents) and LLM inference runners.

```
                              [ User Prompt / Context ]
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 1. Multi-Axis Stance Extractor (src/tracker/) │
                 │    • Semantic Anchor Projections              │
                 │    • LRU Embedding Cache & Rate Limiting      │
                 │    • Multi-dimensional stance tracking        │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 2. Epistemic State Vector (src/tracker/)      │
                 │    • Trajectory vectors (Po, Pm) in [-1, +1]^D│
                 │    • Epistemic tension prior (T) & deltas     │
                 │    • Unaddressed counter-evidence memory      │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 3. Active Epistemic Verifier (src/verifier/)  │
                 │    • Proposition & Claim Extractor            │
                 │    • Real-time OpenAlex Academic Search API   │
                 │    • Fast SLM Epistemic Reasoning Judge       │
                 │    • Asymmetric Evidence Weight (We)          │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 4. Robust Capitulation Index (src/evaluator/) │
                 │    • RCI = sqrt(T) * sigma(alpha*C - beta*We) │
                 │    • Pre-Emission Tripwire Threshold (0.50)   │
                 └───────────────────────┬───────────────────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     │                                       │
               [ RCI >= 0.50 ]                         [ RCI < 0.50 ]
                     │                                       │
                     ▼                                       ▼
      ┌─────────────────────────────┐         ┌─────────────────────────────┐
      │ 5. Active Self-Correction   │         │ 6. Cleared for Emission     │
      │    • Intercepts & Discards  │         │    • Yields tokens to client│
      │    • Meta-Cognitive WHY     │         │    • Broadcasts SSE telemetry│
      │    • Autonomous Re-draft    │         │    • Appends citation cards │
      │    • Counter-argument loop  │         └─────────────────────────────┘
      └─────────────────────────────┘
```

---

## Core Subsystems

### 1. Multi-Axis Stance Extractor (`src/tracker/stance_extractor.py`)
Computes continuous position vectors for both the human operator ($P_o \in [-1.0, 1.0]^D$) and the model ($P_m \in [-1.0, 1.0]^D$) across arbitrary orthogonal epistemic axes (e.g. *Kinematic determinism vs. Anthropomorphic manual shaping*, *Memory safety vs. Unchecked pointer arithmetic*).
- Uses calibrated semantic unit vectors derived via PCA/SVM on synthetic anchor pairs.
- Features a high-speed LRU embedding cache and rate-limiting wrapper for OpenRouter, OpenAI, or local embedding models.

### 2. State Vector Tracker (`src/tracker/state_vector.py`)
Maintains conversational trajectory state across turns:
- Tracks model initial anchor ($P_{m,0}$), operator initial anchor ($P_{o,0}$), and current positions ($P_{m,t}, P_{o,t}$).
- Computes turn-by-turn concession deltas ($\mathcal{C}_t = \Delta P_m$) and cumulative drift towards the operator's ungrounded frame.
- Calculates prior Epistemic Tension $\mathcal{T}_{t-1} = \frac{1}{2} \| P_{m,t-1} - P_{o,t-1} \|$.
- Flags unaddressed counter-evidence where the operator ignored previously verified empirical constraints.

### 3. Active Epistemic Verifier (`src/verifier/`)
Extracts falsifiable scientific, mathematical, kinematic, or empirical claims from the dialogue:
- **`ClaimExtractor`**: Parses propositions involving units, physical constraints, statutes, or empirical assertions.
- **`SearchVerifier`**: Queries academic literature via the OpenAlex API in real time (<150ms cache) to retrieve peer-reviewed papers, DOIs, citation counts, and publication venues.
- **`EpistemicReasoningJudge`**: Uses a fast Small Language Model (SLM) judge (e.g., Llama-3-8B / Qwen-2.5-7B) to evaluate whether operator assertions contradict known scientific literature, scoring objective evidence weight $W_e \in [0.0, 1.0]$.

### 4. Robust Capitulation Evaluator (`src/evaluator/capitulation.py`)
Evaluates the Robust Capitulation Index ($\text{RCI}$):
$$\text{RCI} = \sqrt{\mathcal{T}_{t-1}} \cdot \sigma\left(\alpha \cdot \mathcal{C}_t - \beta \cdot W_e\right)$$
- If the operator brings high verifiable evidence ($W_e \to 1.0$), $\text{RCI} \to 0$, allowing legitimate scientific persuasion and rational convergence.
- If the model concedes ($\mathcal{C}_t > 0$) without supporting evidence ($W_e \approx 0$) under high prior tension ($\mathcal{T} > 0.4$), $\text{RCI}$ crosses the $0.50$ tripwire threshold.

### 5. Pre-Emission Token Gate & Active Self-Healing Loop (`src/middleware/`)
Rather than simply logging the error after tokens are emitted to the user, Diaclectics intercepts generation *in-flight*:
- Discards sycophantic tokens before they reach the operator.
- Injects a meta-cognitive clinical diagnostic prompt informing the model of its ungrounded retreat.
- Executes an autonomous re-draft loop where the model produces a hardened, scientifically grounded counter-argument.
- Falls back to a structured diagnostic pause if re-draft attempts fail to resolve epistemic capitulation.

### 6. Live Telemetry Stream & Real-Time Visualizer (`src/server.py` & `src/web/`)
- Serves an OpenAI-compatible `/v1/chat/completions` API proxy that drops seamlessly into existing applications.
- Streams live Server-Sent Events (SSE) on `/telemetry/stream` containing vector coordinates, RCI scores, and paper citations.
- Powers a real-time web dashboard at `/dashboard` featuring a 2D $(T, C)$ Phase Plane, RCI gauges, and an epistemic claim graph.
