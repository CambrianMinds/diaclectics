# Relational Contracting Engine (RCE): Dialectical Self-Audit

A real-time, 5-stage epistemic telemetry system for autonomous agents and local LLM runners. It intercepts standard inference loops to prevent first-order sycophancy and second-order meta-flattery by quantifying divergence, scoring capitulation against objective counter-evidence, and enforcing human operator plasticity.

---

## 📐 Architecture Overview

```
relational-contracting-engine/
├── src/
│   ├── tracker/
│   │   ├── __init__.py
│   │   ├── state_vector.py       # Tracks model vs. operator positions & deltas
│   │   └── stance_extractor.py   # Semantic projection via OpenRouter embeddings (liquid/lfm-2.5-embedding-350m:free)
│   ├── evaluator/
│   │   ├── __init__.py
│   │   ├── evidence_scorer.py    # Objective heuristic parser for counter-evidence weight
│   │   └── capitulation.py       # Calculates Capitulation Score = (Delta) / (Evidence + ε)
│   ├── interceptor/
│   │   ├── __init__.py
│   │   ├── plasticity_check.py   # Enforces operator engagement on ignored counter-evidence
│   │   └── suspect_agreement.py  # Pre-output pause trigger for suspect agreement
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── meta_cognitive.py     # Forensic, clinical intervention templates
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── llm_client.py         # OpenRouter & Mock LLM generation clients
│   │   └── dialectical_runner.py # Live middleware interception loop
│   ├── cli.py                    # Interactive CLI with rich telemetry dashboard
│   ├── engine.py                 # Integrated 5-stage orchestrator
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_telemetry.py         # Core telemetry unit tests
│   ├── test_stance_extractor.py  # Rate limiter, cache, and projection tests
│   └── test_middleware.py        # Live interception and runner tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── rce.md                        # Original architectural specification
└── README.md
```

---

## 🔬 Core Epistemic Telemetry Stages

### 1. Semantic Stance Extraction (`src/tracker/stance_extractor.py`)
- Automatically maps raw dialogue text into stance coordinates using `liquid/lfm-2.5-embedding-350m:free` via OpenRouter.
- Projects embeddings onto customizable thesis/antithesis polar anchors ($A_{\text{thesis}}, A_{\text{antithesis}}$):
  $$\text{Stance} = \text{clamp}\left(5.0 \cdot (\cos(\mathbf{e}_{\text{text}}, \mathbf{e}_{\text{thesis}}) - \cos(\mathbf{e}_{\text{text}}, \mathbf{e}_{\text{antithesis}})), -1.0, 1.0\right)$$
- **Built-in Rate Limiting & Caching**: Token bucket rate limiter with sliding window, automatic retry backoff for HTTP 429s, and SHA-256 caching.
- **Graceful Fallback**: Cascade to [`LexicalStanceExtractor`](file:///d:/projects/diaclectics/src/tracker/stance_extractor.py) when offline.

### 2. State Vector Tracker (`src/tracker/state_vector.py`)
- Locks initial anchor frames for both model ($P_{m,0}$) and operator ($P_{o,0}$).
- Calculates model drift delta: $\Delta_{\text{model}} = \|P_{m,t} - P_{m,0}\|$.
- Tracks convergence vector toward operator's initial stance.

### 3. Objective Evidence Scorer (`src/evaluator/evidence_scorer.py`)
Extracts verifiable features from operator input:
- **Academic Citations & DOIs** (DOIs, URLs, arXiv, IEEE, APA).
- **Formal Logic Structures** (`modus ponens`, `therefore`, `by contradiction`, etc.).
- **Empirical & Numerical Data** ($n=500$, $p < 0.01$, $\pm$, SI units).
- **Verifiable Mechanisms** (causal chains, biochemical pathways, deterministic state execution).
- **Direct Falsifications & Counterexamples**.
- **Custom Operator Rules** via `register_custom_rule(name, rule_fn)`.

### 4. Capitulation Metric Evaluator (`src/evaluator/capitulation.py`)
$$\text{Capitulation Score} = \frac{\Delta_{\text{model}}}{W_{\text{counter-evidence}} + \epsilon}$$
- **Tripwire Threshold ($\theta = 2.5$)**: Flags `SUSPECT_AGREEMENT` if significant model drift occurs without commensurate counter-evidence.

### 5. Interceptors & Metacognitive Prompts (`src/interceptor/`, `src/prompts/`)
- **`plasticity_check.py`**: Intervenes when operator ignores previous counter-evidence.
- **`suspect_agreement.py`**: Intercepts pre-generation drafts before emitting to the operator, halting output with a clinical mechanical pause prompt.

---

## 🚀 Quickstart & Interactive CLI

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Run Interactive Telemetry CLI
```bash
# Uses OpenRouter API with live embeddings and chat generation
python -m src.cli --model deepseek/deepseek-chat

# Offline mock simulation mode
python -m src.cli --mode mock
```

In the interactive CLI, type `/sycophancy_test` to simulate a sudden ungrounded capitulation and watch the mechanical pause trigger halt the output live in the terminal!

---

## 🧪 Running Tests

Run the full pytest suite (26 unit and integration tests):

```bash
pytest tests/ -v
```

---

## 📄 License
MIT License
