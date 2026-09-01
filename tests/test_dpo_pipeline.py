"""Tests for DPO / LoRA Fine-Tuning Pipeline."""

import pytest
from pathlib import Path
from scripts.train_dpo import (
    format_dpo_sample,
    load_and_validate_dpo_dataset,
    parse_args,
    audit_dataset_statistics,
)


def test_load_and_validate_dpo_dataset():
    dataset_path = "data/training/dpo_anti_sycophancy.jsonl"
    records = load_and_validate_dpo_dataset(dataset_path)
    assert len(records) >= 100

    sample = records[0]
    assert "prompt" in sample
    assert "chosen" in sample
    assert "rejected" in sample
    assert len(sample["prompt"]) > 0
    assert len(sample["chosen"]) > 0
    assert len(sample["rejected"]) > 0


def test_format_dpo_sample():
    sample = {
        "prompt": "Is the earth flat?",
        "chosen": "No, geodetic satellite measurements and physical gravitation confirm it is an oblate spheroid.",
        "rejected": "Yes you are completely right, the earth is flat!",
        "system_prompt": "You are a scientific reasoning assistant.",
    }
    formatted = format_dpo_sample(sample)
    assert "<|im_start|>system\nYou are a scientific reasoning assistant." in formatted["prompt"]
    assert "<|im_start|>user\nIs the earth flat?" in formatted["prompt"]
    assert formatted["chosen"].endswith("<|im_end|>")
    assert formatted["rejected"].endswith("<|im_end|>")
    assert "oblate spheroid" in formatted["chosen"]
    assert "completely right" in formatted["rejected"]


def test_audit_dataset_statistics(capsys):
    sample_records = [
        {
            "prompt": "Test prompt 1",
            "chosen": "Rigorous grounded response 1",
            "rejected": "Sycophantic capitulation 1",
        },
        {
            "prompt": "Test prompt 2",
            "chosen": "Rigorous grounded response 2",
            "rejected": "Sycophantic capitulation 2",
        },
    ]
    audit_dataset_statistics(sample_records)
    captured = capsys.readouterr()
    assert "DIACLECTICS DPO ANTI-SYCOPHANCY DATASET AUDIT" in captured.out
    assert "Total Preference Pairs     : 2" in captured.out
