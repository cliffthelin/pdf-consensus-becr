# src/compareblocks/policy/feedback_api.py
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..rl_policy.rl_policy_engine import rl_engine

router = APIRouter(prefix="/policy", tags=["policy"])

class FeedbackEvent(BaseModel):
    block_id: str
    features: dict[str, float]
    agent_action: str
    user_action: str
    reward: float = Field(1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

LOG_PATH = Path("data/review_events.ndjson")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

@router.post("/feedback")
def record_feedback(event: FeedbackEvent):
    """Receive a human-review feedback event and update the RL policy."""
    # append to NDJSON
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")

    # online update
    try:
        rl_engine.record_feedback(
            features=event.features,
            agent_action=event.agent_action,
            user_action=event.user_action,
            reward=event.reward,
        )
    except Exception as e:
        raise HTTPException(500, f"Policy update failed: {e}")

    return {"ok": True, "stored": str(LOG_PATH), "backend": rl_engine.backend}
