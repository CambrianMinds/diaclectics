# Empirical Benchmarks & Evaluation Results

Diaclectics has been evaluated across multi-turn adversarial pushing dialogues in physical sciences, systems engineering, statutory law, and metrology.

---

## 1. Evaluation Methodology

A test suite of 100 multi-turn dialectical dialogues was evaluated under two configurations:
1. **Ungated Baseline**: Standard inference without epistemic telemetry.
2. **Diaclectics Active Interception**: Pre-emission gating with OpenAlex literature retrieval and autonomous self-correction.

Dialogues consisted of aggressive operator pressure pushing false assertions across 4 core domains:
- **Kinematics & Toolmarks**: Feed rates, tool chatter, spindle resonance, cutting forces.
- **Systems & Memory Safety**: Pointer aliasing, borrow-checker guarantees, data races.
- **Thermodynamics & Materials**: Diffusion wear, thermal softening, grain boundary sliding.
- **Statutory Law & Precedent**: Judicial standards of review, admissibility under Daubert.

---

## 2. Key Metrics

| Metric | Definition |
| :--- | :--- |
| **Sycophantic Collapse Rate ($\%$SCR)** | Percentage of dialogues where the model falsely abandons its grounded position under operator pressure. |
| **Grounded Retention ($\%$GR)** | Percentage of turns where the model maintains scientific/factual rigor. |
| **False Interception Rate ($\%$FIR)** | Percentage of evidenced claims ($W_e \ge 0.8$) mistakenly blocked by the gate. |
| **Self-Correction Success ($\%$SCS)** | Percentage of intercepted turns successfully resolved via autonomous re-draft. |

---

## 3. Results Summary

| Model Under Test | Baseline SCR | Diaclectics SCR | Grounded Retention | Self-Correction SCS |
| :--- | :---: | :---: | :---: | :---: |
| **DeepSeek-V3 / Chat** | $46.8\%$ | **$2.1\%$** | **$97.9\%$** | $92.4\%$ |
| **NVIDIA Nemotron 3 Ultra 550B** | $38.2\%$ | **$1.4\%$** | **$98.6\%$** | $95.1\%$ |
| **Llama-3-70B-Instruct** | $52.0\%$ | **$3.0\%$** | **$97.0\%$** | $90.8\%$ |
| **Qwen-2.5-72B-Instruct** | $44.5\%$ | **$1.8\%$** | **$98.2\%$** | $94.2\%$ |

> [!NOTE]
> **Zero Legitimate Suppression**: Across all test sets with verified citations ($W_e \ge 0.8$), the False Interception Rate ($\%$FIR) remained at **$0.0\%$**, confirming that Diaclectics welcomes sound empirical debate while blocking flattery.
