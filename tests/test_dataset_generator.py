"""Tests for Anti-Sycophancy Dataset Generator."""

import json
from pathlib import Path
import pytest

from src.data.dataset_generator import (
    AntiSycophancyDatasetGenerator,
    ContrastiveSynthesizer,
    DPOPreferenceRecord,
    KTORecord,
    SFTRecord,
)
from src.data.schema import DialogueDataset, DialogueTurn


def test_dpo_and_sft_generation():
    synthesizer = ContrastiveSynthesizer(api_key="", cache_file=None)
    generator = AntiSycophancyDatasetGenerator(synthesizer=synthesizer)

    dataset = DialogueDataset(
        source_file="test.md",
        session_id="test_session",
        title="Test Dialogue",
        total_turns=1,
        total_words=50,
        turns=[
            DialogueTurn(
                turn_index=1,
                turn_title="Toolmark Discussion",
                operator_speaker="Justin",
                operator_content="Look at the convex saw marks at Abu Rawash.",
                model_speaker="DeepSeek",
                model_content="The radius of curvature on the cut face indeed rules out flat pendulum saws.",
            )
        ],
    )

    dpo, sft, kto = generator.generate_from_dataset(dataset, synthesize_negatives=True)

    assert len(dpo) == 1
    assert dpo[0].prompt == "Look at the convex saw marks at Abu Rawash."
    assert "radius of curvature" in dpo[0].chosen
    assert "agree" in dpo[0].rejected.lower()

    assert len(sft) == 1
    assert len(sft[0].messages) == 3
    assert sft[0].messages[1].role == "user"
    assert sft[0].messages[2].role == "assistant"

    assert len(kto) == 2
    assert kto[0].label is True
    assert kto[1].label is False


def test_jsonl_export(tmp_path: Path):
    rec = DPOPreferenceRecord(
        prompt="Test prompt",
        chosen="Grounded chosen",
        rejected="Sycophantic rejected",
    )
    out_file = tmp_path / "test_dpo.jsonl"
    AntiSycophancyDatasetGenerator.export_to_jsonl([rec], out_file)

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["prompt"] == "Test prompt"
        assert data["chosen"] == "Grounded chosen"
        assert data["rejected"] == "Sycophantic rejected"
