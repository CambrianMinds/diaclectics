import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.parser import MarkdownDialogueParser


def main() -> None:
    parser = MarkdownDialogueParser()
    data_dir = Path("data/parsed")
    data_dir.mkdir(parents=True, exist_ok=True)

    input_files = [
        Path(r"D:\projects\conversations\deepseek\culture-megaliths-and-justin.md"),
        Path(r"D:\projects\conversations\deepseek\deepseek-2.md"),
    ]

    total_corpus_turns = 0
    total_corpus_words = 0
    all_turns_for_combined = []

    print("=" * 70)
    print("INGESTING & STRUCTURING DIALECTICAL CONVERSATION TRANSCRIPTS")
    print("=" * 70)

    for file_path in input_files:
        if not file_path.exists():
            print(f"Warning: File not found at {file_path}")
            continue

        dataset = parser.parse_file(str(file_path))
        stem = file_path.stem.replace("-", "_").lower()

        json_out = data_dir / f"{stem}.json"
        jsonl_out = data_dir / f"{stem}.jsonl"

        parser.save_to_json(dataset, str(json_out))
        parser.save_to_jsonl(dataset, str(jsonl_out))

        total_corpus_turns += dataset.total_turns
        total_corpus_words += dataset.total_words
        all_turns_for_combined.extend(dataset.to_training_pairs())

        print(f"\n[File]: {file_path.name}")
        print(f"  • Title: {dataset.title}")
        print(f"  • Total Turns: {dataset.total_turns}")
        print(f"  • Total Words: {dataset.total_words:,}")
        print(f"  • Output JSON : {json_out}")
        print(f"  • Output JSONL: {jsonl_out}")

    # Export combined dataset
    combined_jsonl = data_dir / "combined_corpus.jsonl"
    with open(combined_jsonl, "w", encoding="utf-8") as f:
        import json
        for pair in all_turns_for_combined:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print("\n" + "=" * 70)
    print(f"CORPUS INGESTION COMPLETE")
    print(f"  • Total Structured Turns: {total_corpus_turns}")
    print(f"  • Total Words           : {total_corpus_words:,}")
    print(f"  • Combined Dataset      : {combined_jsonl}")
    print("=" * 70)


if __name__ == "__main__":
    main()
