# src/compareblocks/pipeline/consensus_pipeline.py
from __future__ import annotations
from compareblocks.rl_policy.rl_policy_engine import rl_engine
from compareblocks.policy.feature_builders import build_features_from_votes

def decide_action_for_block(consensus_payload: dict) -> tuple[str, dict]:
    """
    Returns (action, features) where action in {"Pick","Merge","Review"}
    """
    features = build_features_from_votes(consensus_payload)
    action = rl_engine.predict(features)
    return action, features

def process_block(block_id: str, consensus_payload: dict) -> dict:
    action, features = decide_action_for_block(consensus_payload)

    if action == "Pick":
        final_text = consensus_payload["consensus"].replace("-", "")
        agent_action = "Pick"
    elif action == "Merge":
        # route to your merge path (MSA/edlib/parasail) then guardrail
        merged = run_merge_pipeline(consensus_payload)   # <- your existing merger
        final_text = validate_or_fallback(merged, consensus_payload)  # <- your guardrail
        agent_action = "Merge"
    else:  # "Review"
        # present to reviewer OR attempt repair then present
        final_text = consensus_payload["consensus"].replace("-", "")
        agent_action = "Review"

    return {
        "block_id": block_id,
        "agent_action": agent_action,
        "features": features,
        "final_text": final_text,
    }
