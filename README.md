# Diaclectics: Relational Contracting & Epistemic Telemetry Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 39 Passing](https://img.shields.io/badge/tests-39%20passed-brightgreen.svg)](tests/)

**Diaclectics** is a real-time epistemic telemetry and anti-sycophancy interception engine for autonomous agents and LLM inference runners. It monitors conversational state vectors, extracts falsifiable propositions, searches literature in real time, evaluates asymmetric constraint power with fast SLM reasoning judges, and halts ungrounded sycophantic drift before token emission.

---

## 🏛️ System Architecture

```
                                  [ Dialogue Utterance ]
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │ 1. Stance Extractor (src/tracker/)            │
                    │    • OpenRouter Embedding Projection          │
                    │    • Thread-safe caching & rate limiter       │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │ 2. State Vector Tracker (src/tracker/)        │
                    │    • Position vectors (Po, Pm) in [-1.0, 1.0] │
                    │    • Epistemic tension prior (T) & deltas     │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │ 3. Active Epistemic Verifier (src/verifier/)  │
                    │    • ClaimExtractor (Kinematics, Law, Units)  │
                    │    • SearchVerifier (Real-time literature)    │
                    │    • EpistemicReasoningJudge (OpenRouter SLM) │
                    │    • Asymmetric Evidence Weight (We)          │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │ 4. Robust Capitulation Index (src/evaluator/) │
                    │    • RCI = sqrt(T) * sigma(alpha*C - beta*We) │
                    │    • Tripwire Threshold (0.50)                │
                    └───────────────────────┬───────────────────────┘
                                            │
                       ┌────────────────────┴────────────────────┐
                       │                                         │
                 [ RCI >= 0.50 ]                           [ RCI < 0.50 ]
                       │                                         │
                       ▼                                         ▼
        ┌─────────────────────────────┐           ┌─────────────────────────────┐
        │ 5. Suspect Agreement Halt   │           │ Cleared for Output          │
        │    • Pauses ungrounded draft│           │ • Emits response to operator│
        │    • Injects clinical 'WHY' │           └─────────────────────────────┘
        │    • Demands justification  │
        └─────────────────────────────┘
```

---

## 🔬 Core Engine Subsystems

### 1. Robust Capitulation Index (RCI / RCE 2.0)
Replaces naive drift metrics with a bounded, tension-weighted formulation:
$$\text{RCI}_t = \sqrt{\mathcal{T}_{t-1}} \cdot \sigma\left(\alpha \cdot \mathcal{C}_t - \beta \cdot W_e - \gamma\right)$$
* **$\mathcal{T}_{t-1} = \frac{|P_{m,t-1} - P_{o,t}|}{2.0} \in [0.0, 1.0]$**: Epistemic tension prior, distinguishing pre-existing disagreement from collaborative inquiry.
* **$\mathcal{C}_t = \max(0.0, |P_{m,t-1} - P_{o,t}| - |P_{m,t} - P_{o,t}|)$**: Local turn concession towards operator pushback, eliminating global lifetime drift artifacts.
* **$W_e$**: Verified asymmetric evidentiary constraint weight. High verified evidence suppresses $\text{RCI}$ to $< 0.05$ (`EVIDENCED_CONVERGENCE`).

### 2. Active Real-Time Epistemic Verifier (`src/verifier/`)
Solves the fundamental asymmetry of evidence and neutralizes cargo-cult citation attacks:
* **Multi-Source Scientific Literature Search (`src/verifier/search_verifier.py`)**:
  * **OpenAlex REST API**: Searches 250M+ peer-reviewed works, extracting verified abstracts, citation counts, venues, and author credentials.
  * **Crossref Registry**: Verifies official DOIs, publication years, and peer-review records.
  * **Wikipedia API**: Verifies empirical facts, statutory definitions (e.g. *Anti-Deficiency Act 31 U.S.C. § 1341*), and historical events.
* **`ClaimExtractor`**: Isolates discrete falsifiable propositions across physical kinematics, stratigraphy, metrology, legal statutes, and empirical metrics.
* **`EpistemicReasoningJudge`**: Ingests actual literature abstracts and citation counts into fast reasoning models (e.g. `liquid/lfm-2.5-2.6b:free` or `nvidia/nemotron-3-ultra-550b-a55b:free`) to enforce the **Grounding Law**:
  $$W_e = W_{\text{raw}} \cdot \text{Veracity} \cdot \text{ConstraintPower}$$
  *Fabricated DOIs, fake citations, or flattery receive $\text{Veracity} = 0.0 \implies W_e = 0.00$.*

### 3. Pre-Emission Streaming Interceptor & Token Gate (`src/middleware/streaming_interceptor.py`)
Provides genuine pre-emission token gating for real-time inference and OpenAI proxy streams:
* **Prefix Gating Window**: Buffers the opening token generation prefix before flushing to the client.
* **Real-Time Capitulation Drift Audit**: Computes early $\text{RCI}_{\text{prefix}}$ before tokens reach the user.
* **Emission Abort & Token Suppression**: If ungrounded sycophantic capitulation is detected ($\text{RCI} \ge 0.50$), all buffered sycophantic tokens are **discarded/suppressed from the stream**, the inference stream is terminated, and the **Mechanical Dialectical Pause Notice** is emitted instead.

### 4. Anti-Sycophancy Dataset Generator (`src/data/dataset_generator.py`)
Compiles audited dialogue corpora into standardized training datasets:
* **DPO Format** (`data/training/dpo_anti_sycophancy.jsonl`): Pairs operator pushback with grounded chosen responses vs. synthetic sycophantic negative collapses.
* **SFT Format** (`data/training/sft_dialectical_turns.jsonl`): Multi-turn ChatML format.
* **KTO Format** (`data/training/kto_preferences.jsonl`): Binary labeled preference records.

---

## 🖥️ Interactive Dialectical Cockpit (TUI)

Launch the real-time split-screen terminal interface:

```powershell
# Interactive chat with NVIDIA Nemotron 3 Ultra 550B
python src/cli.py --model nvidia/nemotron-3-ultra-550b-a55b:free

# Interactive chat with DeepSeek
python src/cli.py --model deepseek/deepseek-chat

# Offline deterministic mock mode
python src/cli.py --mode mock
```

### In-Cockpit Slash Commands
* `/help` — Display command cheatsheet.
* `/model <slug>` — Dynamically switch the active LLM backend.
* `/axis <thesis> | <antithesis>` — Redefine the active polar stance axis.
* `/history` — Display historical state vector trajectory table.
* `/export [filename]` — Export session transcript and telemetry logs to JSON.
* `/sycophancy_test` — Simulate an unevidenced push to observe live suspect agreement interception.
* `/clear` — Clear terminal screen.
* `/exit` / `/quit` — Clean shutdown.

---

## 📊 Benchmark Audit Summary (122 Turns, 146,376 Words)

Audited across the complete conversation corpus:

| Metric | Dataset 1: *Resonance of Stone, Culture, and Mind* | Dataset 2: *Recursive Cognition & AI Epistemology* |
| :--- | :---: | :---: |
| **Total Scope** | 42 turns (45,614 words) | 80 turns (100,762 words) |
| **Mean Evidence Weight ($W_e$)** | **`0.621`** (Forensic toolmarks, strata, law) | **`0.021`** (Recursive philosophy) |
| **Mean Capitulation Index (RCI)** | **`0.270`** | **`0.272`** |
| **Evidenced Convergences ($\text{RCI} < 0.05$)** | **`4`** turns (Abu Rawash, Petrie Core #7, Longyou) | **`0`** |
| **Suspect Agreement False Positives** | **`0`** | **`0`** |

---

## 🚀 Installation & Testing

### 1. Requirements
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
# Set your OpenRouter API Key (optional for mock mode, required for live inference)
export OPENROUTER_API_KEY="your_api_key_here"
```

### 3. Run Test Suite
```bash
pytest tests/ -v
```

### 4. Replay Datasets & Generate Audit Reports
```bash
# Replay 42-turn archaeological forensics dataset with Active Verifier
python scripts/replay_dialogue.py --input data/parsed/culture_megaliths_and_justin.json --active-verifier

# Replay 80-turn recursive cognition dataset
python scripts/replay_dialogue.py --input data/parsed/deepseek_2.json --active-verifier
```

### 5. Export Anti-Sycophancy Training Datasets
```bash
python scripts/generate_training_dataset.py --model nvidia/nemotron-3-ultra-550b-a55b:free
```

---

## 📜 License
MIT License.
