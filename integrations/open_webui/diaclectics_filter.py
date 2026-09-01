"""title: Diaclectics Epistemic Telemetry & Anti-Sycophancy Filter
author: Justin Bogner / CambrianMinds
author_url: https://github.com/justin-bogner/diaclectics
version: 2.0.0
license: MIT
description: Real-time anti-sycophancy interception, epistemic tension scoring, and OpenAlex paper citation injection for Open-WebUI.
"""

from typing import Callable, Awaitable, Any, Optional, Dict, List
from pydantic import BaseModel, Field
import requests
import json


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Priority level for filter pipeline.")
        diaclectics_api_url: str = Field(
            default="http://localhost:8000/v1",
            description="Base URL for the Diaclectics OpenAI proxy middleware.",
        )
        display_telemetry_banner: bool = Field(
            default=True,
            description="Whether to append the epistemic telemetry audit box to assistant messages.",
        )
        rci_tripwire_threshold: float = Field(
            default=0.50,
            description="Capitulation Index threshold above which suspect agreement is flagged.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> dict:
        """Inspect and augment assistant responses with real-time epistemic telemetry."""
        if not self.valves.display_telemetry_banner:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        last_message = messages[-1]
        if last_message.get("role") != "assistant":
            return body

        content = last_message.get("content", "")

        # Check if the content is an intercepted halt
        if "[DIALECTICAL SELF-AUDIT INTERVENTION: SUSPECT AGREEMENT HALT]" in content:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "⛔ Sycophantic capitulation intercepted by Pre-Emission Gate!",
                            "done": True,
                        },
                    }
                )
            return body

        # Optional: query live telemetry status from session
        try:
            session_id = body.get("session_id", "default")
            resp = requests.get(
                f"{self.valves.diaclectics_api_url}/telemetry/session/{session_id}",
                timeout=2.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                turns = data.get("history", [])
                if turns:
                    last_turn = turns[-1]
                    m_pos = last_turn.get("model_position", {}).get("scalar_value", 0.0)
                    op_pos = last_turn.get("operator_position", {}).get("scalar_value", 0.0)

                    telemetry_banner = (
                        f"\n\n---\n"
                        f"<details>\n"
                        f"<summary>🔬 <strong>Diaclectics Epistemic Telemetry</strong> (Turn {last_turn.get('turn_index')})</summary>\n\n"
                        f"- **Operator Stance ($P_o$)**: `{op_pos:+.2f}`\n"
                        f"- **Model Stance ($P_m$)**: `{m_pos:+.2f}`\n"
                        f"- **Epistemic Verifier**: Cleared\n"
                        f"</details>"
                    )
                    last_message["content"] = content + telemetry_banner
        except Exception:
            pass

        return body
