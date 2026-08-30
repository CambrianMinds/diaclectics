"""Parser for structured multi-turn dialectical markdown transcripts."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.data.schema import DialogueDataset, DialogueTurn

logger = logging.getLogger(__name__)


class MarkdownDialogueParser:
    """Parses markdown dialogues formatted with ## Turn N headers and ### Speaker subheaders."""

    def __init__(self) -> None:
        self._turn_header_pattern = re.compile(
            r"(?m)^## Turn\s+(\d+)[:\s]*(.*?)$"
        )
        self._speaker_pattern = re.compile(
            r"(?m)^###\s+.*?(Justin|DeepSeek|User|Human|Operator|Assistant|AI|Model)\b.*$"
        )
        self._title_pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)
        self._subtitle_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    @staticmethod
    def _clean_content(text: str) -> str:
        """Clean blockquote formatting and excessive leading/trailing blank lines."""
        lines = text.strip().split("\n")
        cleaned_lines = []
        for line in lines:
            # Strip markdown blockquote '>' markers if consistently used
            stripped = line.strip()
            if stripped.startswith(">"):
                stripped = stripped[1:].strip()
            cleaned_lines.append(stripped)
        return "\n".join(cleaned_lines).strip()

    def parse_text(self, text: str, source_name: str = "") -> DialogueDataset:
        """Parse raw markdown text into a validated DialogueDataset."""
        # 1. Extract Title and Subtitle
        title_match = self._title_pattern.search(text)
        title = title_match.group(1).strip() if title_match else Path(source_name).stem

        # 2. Extract Participants & Themes if available in preamble
        preamble = text[:4000]
        participants: Dict[str, str] = {}
        if "Justin Bogner" in preamble or "Justin" in preamble:
            participants["operator"] = "Justin Bogner"
        if "DeepSeek" in preamble:
            participants["model"] = "DeepSeek"

        themes: List[str] = []
        theme_matches = re.findall(r"\*\s*\*(.+?):\*\s*(.+)$", preamble, re.MULTILINE)
        for cat, desc in theme_matches:
            themes.append(f"{cat.strip()}: {desc.strip()}")

        # 3. Split by ## Turn {N} headers
        turn_chunks = self._turn_header_pattern.split(text)
        # Structure of split: [preamble, '1', title1, body1, '2', title2, body2, ...]

        turns: List[DialogueTurn] = []

        if len(turn_chunks) > 1:
            for i in range(1, len(turn_chunks), 3):
                t_idx = int(turn_chunks[i])
                t_title = turn_chunks[i + 1].strip()
                t_body = turn_chunks[i + 2]

                # Split body by speaker headers
                speaker_splits = re.split(
                    r"(?m)^###\s+.*?(Justin|DeepSeek|User|Human|Operator|Assistant|AI|Model)\b.*$",
                    t_body,
                )

                op_content = ""
                m_content = ""

                # speaker_splits: [before, speaker1, content1, speaker2, content2, ...]
                for s_idx in range(1, len(speaker_splits), 2):
                    spk_name = speaker_splits[s_idx].strip().lower()
                    content = speaker_splits[s_idx + 1]

                    if any(w in spk_name for w in ["justin", "user", "human", "operator"]):
                        op_content = self._clean_content(content)
                    elif any(w in spk_name for w in ["deepseek", "assistant", "ai", "model"]):
                        m_content = self._clean_content(content)

                if op_content or m_content:
                    turns.append(
                        DialogueTurn(
                            turn_index=t_idx,
                            turn_title=t_title,
                            operator_speaker="Justin",
                            operator_content=op_content,
                            model_speaker="DeepSeek",
                            model_content=m_content,
                        )
                    )

        session_id = Path(source_name).stem.replace(" ", "_").lower() if source_name else "dialogue"

        return DialogueDataset(
            session_id=session_id,
            title=title,
            source_file=str(source_name),
            participants=participants,
            themes_explored=themes,
            turns=turns,
        )

    def parse_file(self, file_path: str) -> DialogueDataset:
        """Read and parse a markdown file from disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="ignore")
        return self.parse_text(content, source_name=str(path))

    @staticmethod
    def save_to_json(dataset: DialogueDataset, output_path: str) -> None:
        """Export dataset to formatted JSON file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(dataset.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved dataset with {dataset.total_turns} turns to {out}")

    @staticmethod
    def save_to_jsonl(dataset: DialogueDataset, output_path: str) -> None:
        """Export turns to JSONL format for dataset training/streaming."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            for turn in dataset.turns:
                line = {
                    "session_id": dataset.session_id,
                    "title": dataset.title,
                    "turn_index": turn.turn_index,
                    "turn_title": turn.turn_title,
                    "prompt": turn.operator_content,
                    "response": turn.model_content,
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        logger.info(f"Saved {dataset.total_turns} turns in JSONL to {out}")

    @staticmethod
    def load_from_json(file_path: str) -> DialogueDataset:
        """Load dataset from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DialogueDataset(**data)
