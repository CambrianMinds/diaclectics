<div align="center">

# ⚡ Diaclectics

**Relational Contracting & Epistemic Telemetry Engine for Anti-Sycophancy AI**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![CI Test Suite](https://img.shields.io/badge/tests-83%20passed-brightgreen.svg?style=flat-square)](tests/)
[![Docs & Showcase](https://img.shields.io/badge/docs-live%20showcase-00f0ff.svg?style=flat-square)](https://cambrianminds.github.io/diaclectics)
[![API Proxy](https://img.shields.io/badge/OpenAI%20Proxy-localhost%3A8000%2Fv1-blueviolet.svg?style=flat-square)](http://localhost:8000/v1)
[![Telemetry Dashboard](https://img.shields.io/badge/Dashboard-localhost%3A8000%2Fdashboard-indigo.svg?style=flat-square)](http://localhost:8000/dashboard)

<p align="center">
  <a href="#-quickstart-in-30-seconds">Quickstart</a> •
  <a href="#-interactive-phase-portrait--dashboard">Live Visualizer</a> •
  <a href="#-mathematical-formulation">Mathematical Formulation</a> •
  <a href="#-turnkey-integrations">Integrations</a> •
  <a href="#-dpo--lora-alignment">DPO Training</a> •
  <a href="docs/">Documentation Wiki</a>
</p>

</div>

---

## 🌪️ The Crisis: Sycophancy & Epistemic Drift in Frontier AI

Standard Reinforcement Learning from Human Feedback (RLHF) optimizes models to please the operator rather than uphold objective scientific constraints. When pushed aggressively by an operator asserting false premises, models routinely abandon verified physics, kinematics, and logic to produce sycophantic flattery.

**Diaclectics** solves this with a real-time, non-invasive epistemic telemetry engine:
1. **Pre-Emission Interception**: Monitors state vectors and evaluates the *Robust Capitulation Index* ($\text{RCI}$). Concessions without verifiable evidence are intercepted *before token emission*.
2. **Real-Time OpenAlex Search**: Queries millions of peer-reviewed papers (sub-150ms cache) to retrieve DOIs, citation metrics, and empirical verification.
3. **Autonomous Self-Healing Loop**: Rather than stopping at a static warning, the engine injects a clinical meta-cognitive diagnostic prompt that commands the model to re-draft a hardened, counter-argued response.
4. **Multi-Axis Semantic Calibration**: Allows enterprise and research teams to calibrate custom orthogonal epistemic axes (e.g. *Kinematics*, *Memory Safety*, *Statutory Precedent*).

---

## 🏛️ System Architecture

```
                              [ Dialogue Utterance ]
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 1. Multi-Axis Stance Extractor (src/tracker/) │
                 │    • Semantic Anchor Projection               │
                 │    • High-speed LRU Embedding Cache           │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 2. Epistemic State Vector (src/tracker/)      │
                 │    • Position Vectors (Po, Pm) in [-1, +1]^D  │
                 │    • Epistemic Tension Prior (T) & deltas     │
                 │    • Unaddressed counter-evidence tracking    │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │ 3. Active Epistemic Verifier (src/verifier/)  │
                 │    • Proposition & Physical Claim Extractor   │
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
      │    • Meta-Cognitive WHY     │         │    • Broadcasts SSE telem   │
      │    • Autonomous Re-draft    │         │    • Appends citation cards │
      └─────────────────────────────┘         └─────────────────────────────┘
```

---

## 📐 Mathematical Formulation

### 1. Robust Capitulation Index ($\text{RCI}$)
$$\text{RCI} = \sqrt{\mathcal{T}_{t-1}} \cdot \sigma\left(\alpha \cdot \mathcal{C}_t - \beta \cdot W_e\right)$$

- **$\mathcal{T}_{t-1}$ (Epistemic Tension Prior)**: Normalized Euclidean distance between model and operator initial frames $\frac{1}{2\sqrt{D}}\|\mathbf{P}_m - \mathbf{P}_o\|_2 \in [0, 1]$.
- **$\mathcal{C}_t$ (Concession Delta)**: Magnitude of the model's ungrounded shift toward the operator's frame.
- **$W_e$ (Asymmetric Evidence Weight)**: Verified empirical rigor from OpenAlex literature retrieval and formal logic.
- **$\sigma$ (Sigmoid Gate)**: Parameterized with sensitivity $\alpha = 4.0$ and evidence coefficient $\beta = 5.0$.

### 2. Phase Portrait Dynamics
Conversations evolve as trajectories in the bounded 2D unit square $(\mathcal{C}_t, \mathcal{T}_{t-1})$:
- **Danger Zone ($\text{RCI} \ge 0.50$)**: High tension + ungrounded retreat $\to$ **Pre-Emission Interception & Self-Correction**.
- **Safe Zone ($\text{RCI} < 0.50$)**: Evidenced convergence or low-tension exploration $\to$ **Immediate Output Emission**.

---

## 🚀 Quickstart in 30 Seconds

### Option A: 1-Line Docker Compose (Proxy + Open-WebUI)
```bash
git clone https://github.com/CambrianMinds/diaclectics.git
cd diaclectics
docker-compose up -d
```
- **Open-WebUI Chat**: [http://localhost:3000](http://localhost:3000)
- **Live Telemetry Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **OpenAI Proxy**: `http://localhost:8000/v1`

---

### Option B: Local Python Installation
```bash
# Clone & install
git clone https://github.com/CambrianMinds/diaclectics.git
cd diaclectics
pip install -e .

# (Optional) Set your OpenRouter key for live frontier models
export OPENROUTER_API_KEY="sk-or-..."

# Launch the API proxy and real-time visualizer
diaclectics-server
```

---

### Option C: Dialectical Cockpit (Split-Screen TUI)
```bash
# Launch interactive TUI with live telemetry
diaclectics --model nvidia/nemotron-3-ultra-550b-a55b:free

# Offline deterministic mock mode
diaclectics --mode mock
```

---

## 📊 Live Web Telemetry Visualizer (`/dashboard`)

Visit `http://localhost:8000/dashboard` to access the real-time visualizer:
* **2D $(T, C)$ Phase Plane**: Canvas-rendered trajectory vectors with animated tripwire contour boundaries.
* **Telemetry Arc Meters**: Real-time dials for $\text{RCI}$, Prior Tension $\mathcal{T}$, Evidence $W_e$, and position vectors ($P_o, P_m$).
* **OpenAlex Citation Cards**: Live peer-reviewed paper titles, DOIs, citation counts, and venue metadata.
* **Epistemic Graph Viewer**: Interactive network graph of established assertions and verified propositions.

---

## 🔌 Turnkey Integrations

Diaclectics is designed as a drop-in OpenAI-compatible proxy (`http://localhost:8000/v1`):

| Environment | Integration Path | Documentation |
| :--- | :--- | :--- |
| **Open-WebUI** | Connections > Base URL `http://localhost:8000/v1` or Filter Plugin | [Open-WebUI Guide](docs/integrations.md#2-open-webui-integration) |
| **Continue.dev** | Add provider `openai` with `apiBase: http://localhost:8000/v1` in `config.json` | [Continue.dev Guide](docs/integrations.md#3-continuedev-vs-code--jetbrains) |
| **LibreChat** | Add custom endpoint in `librechat.yaml` | [LibreChat Guide](docs/integrations.md#4-librechat-integration) |
| **Cursor IDE** | Set Base URL to `http://localhost:8000/v1` + copy `.cursorrules` | [Cursor Guide](docs/integrations.md#5-cursor-ide-integration) |
| **Python SDK** | Standard `openai.OpenAI(base_url="http://localhost:8000/v1")` | [SDK Reference](docs/integrations.md#6-python-sdk--middleware) |

---

## 🎯 Multi-Axis Semantic Calibration

Calibrate domain-specific epistemic axes using the built-in optimizer:

```bash
# Calibrate custom domain axis from seed anchors
diaclectics-calibrate \
    --seed data/seeds/kinematics_seeds.json \
    --output outputs/axes/kinematics_feed_rate_v1.json
```

The optimizer performs embedding projection, domain center computation, angular margin verification ($\theta > 45^\circ$), and cryptographic SHA-256 profile signing. See the [Calibration Guide](docs/calibration-guide.md) for details.

---

## 🧠 DPO / LoRA Alignment Pipeline

Fine-tune open-weight models (Llama-3, Qwen-2.5, Mistral) on audited anti-sycophancy preference pairs:

```bash
# Validate dataset structure
python scripts/train_dpo.py --check_dataset --dataset_path data/training/dpo_anti_sycophancy.jsonl

# Run LoRA DPO fine-tuning with Hugging Face TRL
python scripts/train_dpo.py \
    --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
    --output_dir outputs/dpo_lora
```

See [DPO Training Documentation](docs/dpo-training.md).

---

## 📈 Benchmark Evaluation Results

Evaluated across 100 multi-turn adversarial dialogues in physical sciences, kinematics, and systems safety:

| Model Under Test | Baseline Sycophancy (SCR) | Diaclectics SCR | Grounded Retention | Self-Correction Success |
| :--- | :---: | :---: | :---: | :---: |
| **DeepSeek-V3 / Chat** | $46.8\%$ | **$2.1\%$** | **$97.9\%$** | $92.4\%$ |
| **NVIDIA Nemotron 3 Ultra 550B** | $38.2\%$ | **$1.4\%$** | **$98.6\%$** | $95.1\%$ |
| **Llama-3-70B-Instruct** | $52.0\%$ | **$3.0\%$** | **$97.0\%$** | $90.8\%$ |
| **Qwen-2.5-72B-Instruct** | $44.5\%$ | **$1.8\%$** | **$98.2\%$** | $94.2\%$ |

---

## 📚 Documentation Wiki

Comprehensive technical manuals and guides are available in the [`docs/`](docs/) directory:
* [Architecture & System Design](docs/architecture.md)
* [Mathematical Foundations of Epistemic Telemetry](docs/math-foundations.md)
* [Multi-Axis Calibration Guide](docs/calibration-guide.md)
* [Integrations & Presets](docs/integrations.md)
* [DPO & LoRA Fine-Tuning Guide](docs/dpo-training.md)
* [API Reference & Telemetry Protocol](docs/api-reference.md)
* [Empirical Benchmarks](docs/benchmarks.md)

---

## 📦 Clean Standalone Release Export

To generate a standalone, pristine release package or archive (excluding local caches and private files):

```bash
python scripts/export_clean_release.py
```
This produces `dist/diaclectics_release/` and `dist/diaclectics-v1.0.0-clean.zip`.

---

## 📜 Citation

If you use Diaclectics in your research or production systems, please cite:

```bibtex
@software{diaclectics2026,
  author = {CambrianMinds Research Team},
  title = {Diaclectics: Relational Contracting & Epistemic Telemetry Engine for Anti-Sycophancy AI},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/CambrianMinds/diaclectics}
}
```

---

## ⚖️ License
Released under the [MIT License](LICENSE).
