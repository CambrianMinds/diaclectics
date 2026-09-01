# Contributing to Diaclectics

We welcome contributions to Diaclectics from researchers, engineers, and philosophers working on epistemic safety, alignment, and dialectical AI!

---

## 🛠️ Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/CambrianMinds/diaclectics.git
   cd diaclectics
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies in Editable Mode**:
   ```bash
   pip install -e ".[dev,train]"
   ```

4. **Run the Test Suite**:
   ```bash
   pytest
   ```

---

## 🔬 Submitting Changes

1. **Branch Naming**: Use descriptive branch names:
   - `feature/multi-axis-spherical-projection`
   - `fix/streaming-token-backtrack`
   - `docs/add-latex-derivations`
2. **Code Style**:
   - Run `black` and `flake8` before submitting PRs:
     ```bash
     black src/ tests/ scripts/
     flake8 src/ tests/
     ```
3. **Tests**: Ensure all existing tests pass and add unit tests in `tests/` covering new features or bugfixes.
4. **Pull Requests**: Provide a clear explanation of what problem the PR solves, the mathematical or behavioral justification, and test results.

---

## 📜 Code of Conduct

Please adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.
