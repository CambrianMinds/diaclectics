# Relational Contracting Engine: Dialectical Self-Audit

## Overview
This repository implements a real-time, 5-stage epistemic telemetry system for autonomous agents and local LLM runners. It intercepts standard inference loops to prevent first-order sycophancy and second-order meta-flattery by quantifying divergence, scoring capitulation, and enforcing human operator plasticity.

## Directory Structure
```text
relational-contracting-engine/
├── src/
│   ├── tracker/
│   │   ├── __init__.py
│   │   └── state_vector.py       # Tracks model vs. operator initial/final positions
│   ├── evaluator/
│   │   ├── __init__.py
│   │   ├── evidence_scorer.py    # W.I.P: Logic for weighting operator counter-evidence
│   │   └── capitulation.py       # Calculates Capitulation Score
│   ├── interceptor/
│   │   ├── __init__.py
│   │   ├── plasticity_check.py   # Forces operator engagement on ignored counter-evidence
│   │   └── suspect_agreement.py  # Pre-output pause trigger
│   └── prompts/
│       ├── __init__.py
│       └── meta_cognitive.py     # Templates for surfacing patterns without accusation
├── tests/
│   └── test_telemetry.py
├── docker-compose.yml
├── requirements.txt
└── README.md

```

## Core Modules & Agent Instructions

### 1. `src/tracker/state_vector.py`

**Agent Directive:** Implement a metadata tracking class that attaches to the conversation history.

* **Variables to track:** `model_initial_pos`, `operator_initial_pos`, `current_convergence_vector`.
* **Goal:** Calculate the delta of the model's position toward the operator's initial frame across $N$ turns.

### 2. `src/evaluator/evidence_scorer.py` [PRIORITY FOCUS]

**Agent Directive:** This is the core algorithmic challenge. The human operator will drive the logic design here.

* **Objective:** Build a function that assigns a `counter_evidence_weight` to the operator's input.
* **Constraint:** The grading scale must be objective. It cannot rely on the model's subjective agreement. Consider parsing for citations, formal logic structures, or verifiable mechanisms.
* *Note to Agent: Await operator guidance on the exact heuristic for this module.*

### 3. `src/evaluator/capitulation.py`

**Agent Directive:** Implement the capitulation metric.

* **Formula:** `Capitulation Score = (Delta of Model Position) / (Weight of Counter-Evidence)`.
* **Threshold:** Define a tripwire. If the score approaches infinity (high delta, zero evidence), flag for `suspect_agreement`.

### 4. `src/interceptor/suspect_agreement.py` & `plasticity_check.py`

**Agent Directive:** Build the interceptors that halt the standard generation loop.

* `plasticity_check.py`: Scan operator input for responses to previously flagged contradictions. If missing, append the prompt: *"I offered counter-evidence in Turn X. You did not address it. Are you open to revising that position?"*
* `suspect_agreement.py`: If `capitulation_score` tripwire is hit, block the drafted response and output the mechanical pause prompt.

### 5. `src/prompts/meta_cognitive.py`

**Agent Directive:** Store and format the diagnostic interventions.

* Keep language strictly clinical, non-accusatory, and forensic.
* Format output to ensure clear visibility in the terminal or UI.

```