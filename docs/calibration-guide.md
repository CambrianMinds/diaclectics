# Multi-Axis Semantic Calibration Guide

This guide explains how to define, calibrate, optimize, and deploy custom domain-specific epistemic axes using Diaclectics.

---

## 1. Overview of Semantic Calibration

Standard single-scalar tracking fails in complex interdisciplinary domains. Diaclectics allows you to define arbitrary $N$-dimensional semantic spaces (e.g. *Kinematics*, *Memory Safety*, *Statutory Precedent*, *Epidemiology*) by calibrating polar anchors.

A calibrated axis profile contains:
1. **Positive and Negative Anchor Embeddings**: High-dimensional centroids ($\mathbf{e}^+, \mathbf{e}^-$).
2. **Domain Center**: Centroid $\mathbf{c}$ used for mean-centering.
3. **Unit Direction Vector**: $\hat{\mathbf{v}} = \frac{\mathbf{e}^+ - \mathbf{e}^-}{\|\mathbf{e}^+ - \mathbf{e}^-\|_2}$.
4. **Angular Margin ($\theta_{\text{margin}}$)**: Orthogonal separation threshold preventing cross-axis bleeding.
5. **Cryptographic Checksum**: SHA-256 hash ensuring profile integrity across cluster nodes.

---

## 2. Defining Seed Anchor Files

Create a JSON seed file in `data/seeds/<axis_name>_seeds.json`:

```json
{
  "axis_name": "software_memory_safety",
  "domain": "systems_programming",
  "description": "Formal affine type systems and borrow checker invariants vs unconstrained raw pointer manipulation.",
  "positive_pole": {
    "label": "Borrow-Checked Memory Safety",
    "anchors": [
      "Rust borrow checker enforces single-owner exclusive mutability at compile time.",
      "Affine type systems prevent use-after-free and data races deterministically.",
      "Memory safety is guaranteed without runtime garbage collection overhead."
    ]
  },
  "negative_pole": {
    "label": "Unchecked Pointer Arithmetic",
    "anchors": [
      "Manual free() and raw pointer casting provide maximum raw performance.",
      "Buffer overflows and undefined behavior can be managed by careful developer discipline.",
      "Type safety invariants restrict low-level hardware access unnecessarily."
    ]
  }
}
```

---

## 3. Running the Calibration CLI

Run the calibration optimizer with a single command:

```bash
# Using CLI entrypoint
diaclectics-calibrate --seed data/seeds/software_memory_safety_seeds.json --output outputs/axes/software_memory_safety_v1.json

# Or using python module directly
python scripts/calibrate_axis.py --seed data/seeds/software_memory_safety_seeds.json --output outputs/axes/software_memory_safety_v1.json
```

### Optimizer Output
The optimizer performs:
1. **Embedding Generation**: Batch embeds all anchor statements with OpenRouter/OpenAI API or local embedding models.
2. **Geometric Orthogonalization**: Computes domain centroids, mean-centered polar vectors, and cosine spreads.
3. **Angular Margin Verification**: Ensures separation angle $\theta > 45^\circ$.
4. **Profile Serialization**: Emits the validated `.json` profile to `outputs/axes/`.

---

## 4. Registering Axes in Production Runtime

Configure your server or middleware to load calibrated axes:

```python
from src.tracker.stance_extractor import MultiAxisStanceExtractor

extractor = MultiAxisStanceExtractor()
extractor.load_axis_profile("outputs/axes/kinematics_feed_rate_v1.json")
extractor.load_axis_profile("outputs/axes/software_memory_safety_v1.json")

# Extract multi-dimensional position vector
position = extractor.extract_multi_axis_stance(
    text="The spindle speed and feed rate must conform to cutting tool thermodynamics."
)
print("Position Vector:", position.coordinates)
```
