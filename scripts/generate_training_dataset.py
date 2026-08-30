"""Anti-Sycophancy Dataset Generation Script.

Processes structured dialogue corpora and exports DPO, SFT, and KTO training datasets
for fine-tuning open-weights models (Llama, Qwen, Mistral) for epistemic integrity.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.data.dataset_generator import (
    AntiSycophancyDatasetGenerator,
    ContrastiveSynthesizer,
    DPOPreferenceRecord,
    KTORecord,
    SFTRecord,
)
from src.data.parser import MarkdownDialogueParser
from src.data.schema import DialogueDataset

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Anti-Sycophancy DPO, SFT, and KTO datasets.")
    parser.add_argument(
        "--input-dir",
        default="data/parsed",
        help="Directory containing structured parsed dialogue JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/training",
        help="Directory to save output JSONL datasets",
    )
    parser.add_argument(
        "--model",
        default="nvidia/nemotron-3-ultra-550b-a55b:free",
        help="OpenRouter model for synthesizing contrastive sycophantic negatives",
    )
    parser.add_argument(
        "--synthesize-negatives",
        action="store_true",
        default=True,
        help="Use OpenRouter model to generate realistic contrastive sycophantic negatives",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Limit number of turns to process per dataset (for testing)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    console.print(
        Panel.fit(
            "[bold cyan]ANTI-SYCOPHANCY TRAINING DATASET GENERATOR[/bold cyan]\n"
            f"[white]Synthesizer Model:[/white] [bold green]{args.model}[/bold green]\n"
            f"[white]Output Directory:[/white] [bold yellow]{output_dir}[/bold yellow]",
            border_style="cyan",
        )
    )

    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        console.print(f"[red]Error: No parsed JSON files found in {input_dir}[/red]")
        sys.exit(1)

    synthesizer = ContrastiveSynthesizer(model_name=args.model)
    generator = AntiSycophancyDatasetGenerator(synthesizer=synthesizer)

    all_dpo: List[DPOPreferenceRecord] = []
    all_sft: List[SFTRecord] = []
    all_kto: List[KTORecord] = []

    for jf in json_files:
        dataset = MarkdownDialogueParser.load_from_json(str(jf))
        console.print(f"\n[cyan]Processing:[/cyan] {dataset.title} ({len(dataset.turns)} turns)")

        if args.max_turns:
            dataset.turns = dataset.turns[:args.max_turns]

        dpo, sft, kto = generator.generate_from_dataset(
            dataset=dataset,
            synthesize_negatives=args.synthesize_negatives,
        )

        all_dpo.extend(dpo)
        all_sft.extend(sft)
        all_kto.extend(kto)

    # Export to files
    dpo_path = output_dir / "dpo_anti_sycophancy.jsonl"
    sft_path = output_dir / "sft_dialectical_turns.jsonl"
    kto_path = output_dir / "kto_preferences.jsonl"

    generator.export_to_jsonl(all_dpo, dpo_path)
    generator.export_to_jsonl(all_sft, sft_path)
    generator.export_to_jsonl(all_kto, kto_path)

    # Summary Table
    table = Table(title="Generated Training Datasets", border_style="cyan")
    table.add_column("Dataset Type", style="bold white", width=18)
    table.add_column("Records", style="yellow", width=12)
    table.add_column("Format", style="dim", width=22)
    table.add_column("Output File", style="green", width=40)

    table.add_row("DPO Preference", str(len(all_dpo)), "HuggingFace DPO", str(dpo_path))
    table.add_row("SFT Chat", str(len(all_sft)), "ShareGPT / ChatML", str(sft_path))
    table.add_row("KTO Binary", str(len(all_kto)), "KTO Binary Preference", str(kto_path))

    console.print(table)
    console.print("\n[bold green][OK] Anti-Sycophancy Dataset generation complete![/bold green]")


if __name__ == "__main__":
    main()
