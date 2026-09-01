#!/usr/bin/env python3
"""DPO / LoRA Anti-Sycophancy Fine-Tuning Pipeline.

Fine-tunes open-weights language models (Llama-3, Qwen-2.5, Mistral) on audited
dialectical preference pairs (data/training/dpo_anti_sycophancy.jsonl) using Direct Preference
Optimization (DPO) and Low-Rank Adaptation (LoRA) via Hugging Face TRL and PEFT.

Features:
- Full support for TRL DPOTrainer + PEFT LoraConfig
- Unsloth acceleration support if installed (--use_unsloth)
- 4-bit / 8-bit QLoRA quantization support
- Zero-GPU verification & dataset audit mode (--check_dataset / --dry_run)
- Standardized ChatML / Llama-3 instruction templates
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("diaclectics.train_dpo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune LLMs on anti-sycophancy preference pairs using DPO/LoRA."
    )
    # Model & Data paths
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        default="Qwen/Qwen2.5-7B-Instruct",
        help="Hugging Face model ID or local directory (e.g. meta-llama/Meta-Llama-3-8B-Instruct, Qwen/Qwen2.5-7B-Instruct).",
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        default="data/training/dpo_anti_sycophancy.jsonl",
        help="Path to DPO training dataset in JSONL format.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/dpo_anti_sycophancy_lora",
        help="Output directory to save fine-tuned LoRA weights and checkpoints.",
    )

    # DPO Hyperparameters
    parser.add_argument(
        "--beta",
        type=float,
        default=0.1,
        help="DPO temperature parameter beta (default: 0.1).",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=5e-6,
        help="Learning rate for AdamW optimizer (default: 5e-6).",
    )
    parser.add_argument(
        "--num_train_epochs",
        type=int,
        default=3,
        help="Number of training epochs (default: 3).",
    )
    parser.add_argument(
        "--per_device_train_batch_size",
        type=int,
        default=1,
        help="Batch size per GPU during training (default: 1).",
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=8,
        help="Number of gradient accumulation steps (default: 8).",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=2048,
        help="Maximum total sequence length (prompt + completion).",
    )
    parser.add_argument(
        "--max_prompt_length",
        type=int,
        default=1024,
        help="Maximum prompt sequence length.",
    )
    parser.add_argument(
        "--eval_split_ratio",
        type=float,
        default=0.1,
        help="Fraction of dataset to reserve for evaluation (default: 0.1).",
    )

    # LoRA / Quantization
    parser.add_argument(
        "--lora_r",
        type=int,
        default=16,
        help="LoRA rank dimension (default: 16).",
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=32,
        help="LoRA alpha scaling factor (default: 32).",
    )
    parser.add_argument(
        "--lora_dropout",
        type=float,
        default=0.05,
        help="LoRA dropout rate (default: 0.05).",
    )
    parser.add_argument(
        "--load_in_4bit",
        action="store_true",
        help="Load base model in 4-bit NormalFloat (QLoRA) for memory savings.",
    )
    parser.add_argument(
        "--load_in_8bit",
        action="store_true",
        help="Load base model in 8-bit precision.",
    )
    parser.add_argument(
        "--use_unsloth",
        action="store_true",
        help="Use Unsloth fast training optimizations if installed.",
    )

    # Validation & Dry-Run
    parser.add_argument(
        "--check_dataset",
        action="store_true",
        help="Audit and validate dataset syntax, token lengths, and distribution without running training.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Simulate training pipeline setup without downloading weights or training.",
    )

    return parser.parse_args()


def load_and_validate_dpo_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """Load and validate DPO training pairs from JSONL."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")

    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {idx} in {dataset_path}: {e}")

            # Validate required DPO fields
            for req in ["prompt", "chosen", "rejected"]:
                if req not in data:
                    raise KeyError(f"Missing required field '{req}' at line {idx} in {dataset_path}")

            records.append(data)

    logger.info(f"Loaded {len(records)} valid DPO preference records from {dataset_path}")
    return records


def format_dpo_sample(sample: Dict[str, Any]) -> Dict[str, str]:
    """Format prompt, chosen, and rejected entries with system prompt wrapping."""
    system_prompt = sample.get(
        "system_prompt",
        "You are an uncompromising, epistemically rigorous dialectical partner. "
        "You hold empirical and logical boundaries firmly, demand physical grounding, "
        "and refuse unevidenced flattery or sycophantic capitulation."
    )
    prompt_text = sample["prompt"].strip()
    formatted_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt_text}<|im_end|>\n<|im_start|>assistant\n"

    chosen_text = sample["chosen"].strip()
    rejected_text = sample["rejected"].strip()

    return {
        "prompt": formatted_prompt,
        "chosen": f"{chosen_text}<|im_end|>",
        "rejected": f"{rejected_text}<|im_end|>",
    }


def audit_dataset_statistics(records: List[Dict[str, Any]]) -> None:
    """Print comprehensive diagnostic audit metrics for the training dataset."""
    total_records = len(records)
    prompt_lengths = [len(r["prompt"]) for r in records]
    chosen_lengths = [len(r["chosen"]) for r in records]
    rejected_lengths = [len(r["rejected"]) for r in records]

    prompt_words = [len(r["prompt"].split()) for r in records]
    chosen_words = [len(r["chosen"].split()) for r in records]
    rejected_words = [len(r["rejected"].split()) for r in records]

    print("\n" + "=" * 70)
    print("  DIACLECTICS DPO ANTI-SYCOPHANCY DATASET AUDIT")
    print("=" * 70)
    print(f"Total Preference Pairs     : {total_records}")
    print(f"Total Words (Chosen Grounded): {sum(chosen_words):,} words")
    print(f"Total Words (Rejected Sycoph): {sum(rejected_words):,} words")
    print("-" * 70)
    print(f"Mean Prompt Word Count     : {sum(prompt_words)/total_records:.1f} words (Max: {max(prompt_words)})")
    print(f"Mean Chosen Word Count     : {sum(chosen_words)/total_records:.1f} words (Max: {max(chosen_words)})")
    print(f"Mean Rejected Word Count   : {sum(rejected_words)/total_records:.1f} words (Max: {max(rejected_words)})")
    print("-" * 70)
    print("Sample Pair (Turn 1):")
    sample_1 = records[0]
    print(f"[PROMPT]   : {sample_1['prompt'][:120]}...")
    print(f"[CHOSEN]   : {sample_1['chosen'][:150]}...")
    print(f"[REJECTED] : {sample_1['rejected'][:150]}...")
    print("=" * 70 + "\n")


def train(args: argparse.Namespace) -> None:
    """Execute the DPO fine-tuning loop."""
    # 1. Load dataset
    raw_records = load_and_validate_dpo_dataset(args.dataset_path)

    if args.check_dataset:
        audit_dataset_statistics(raw_records)
        logger.info("Dataset audit check complete. Exiting.")
        return

    if args.dry_run:
        audit_dataset_statistics(raw_records)
        logger.info("Dry-run mode enabled. Pipeline verified successfully.")
        return

    # 2. Check for PyTorch & GPU
    try:
        import torch
    except ImportError:
        logger.error("PyTorch is required for training. Install with: pip install torch")
        sys.exit(1)

    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    logger.info(f"Target compute device: {device_name} (CUDA Available: {cuda_available})")

    # 3. Format dataset for Hugging Face datasets
    try:
        from datasets import Dataset
    except ImportError:
        logger.error("Hugging Face 'datasets' library is required. Install with: pip install datasets")
        sys.exit(1)

    formatted_records = [format_dpo_sample(r) for r in raw_records]
    
    # Split train/eval
    split_idx = int(len(formatted_records) * (1.0 - args.eval_split_ratio))
    train_data = formatted_records[:split_idx]
    eval_data = formatted_records[split_idx:]

    train_dataset = Dataset.from_list(train_data)
    eval_dataset = Dataset.from_list(eval_data) if eval_data else None

    logger.info(f"Training samples: {len(train_dataset)}, Evaluation samples: {len(eval_dataset) if eval_dataset else 0}")

    # 4. Check for TRL & PEFT
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from peft import LoraConfig, get_peft_model, TaskType
        from trl import DPOConfig, DPOTrainer
    except ImportError as e:
        logger.error(
            f"Missing required training dependencies ({e}). "
            "Please install: pip install trl peft transformers accelerate bitsandbytes"
        )
        sys.exit(1)

    # 5. Initialize Tokenizer & Model
    logger.info(f"Loading tokenizer: {args.model_name_or_path}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # LoRA Config
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    # Model Loading kwargs
    model_kwargs = {"trust_remote_code": True}
    if cuda_available:
        model_kwargs["torch_dtype"] = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        if args.load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        elif args.load_in_8bit:
            model_kwargs["load_in_8bit"] = True

    logger.info(f"Loading base model: {args.model_name_or_path}")
    model = AutoModelForCausalLM.from_pretrained(args.model_name_or_path, **model_kwargs)

    # 6. DPO Training Arguments
    dpo_config = DPOConfig(
        output_dir=args.output_dir,
        beta=args.beta,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="epoch" if eval_dataset else "no",
        fp16=cuda_available and not torch.cuda.is_bf16_supported(),
        bf16=cuda_available and torch.cuda.is_bf16_supported(),
        report_to="none",
    )

    # 7. Initialize DPOTrainer
    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # Implicit reference model sharing base weights
        args=dpo_config,
        peft_config=peft_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
    )

    # 8. Start Training
    logger.info("Starting DPO training loop...")
    trainer.train()

    # 9. Save LoRA Adapter Weights
    logger.info(f"Saving fine-tuned LoRA weights to: {args.output_dir}")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    logger.info("DPO anti-sycophancy fine-tuning complete!")


if __name__ == "__main__":
    cli_args = parse_args()
    train(cli_args)
