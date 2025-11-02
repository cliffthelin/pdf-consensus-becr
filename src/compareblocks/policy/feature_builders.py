# src/compareblocks/policy/feature_builders.py
from __future__ import annotations
import math

def build_features_from_votes(consensus_payload: dict) -> dict[str, float]:
    """
    consensus_payload structure expected:
      {
        "consensus": "...",
        "votes": [
          {"column": 0, "chosen": "T", "tally": {"T": 2.0, "-": 1.0}},
          ...
        ],
        ...
      }
    """
    votes = consensus_payload.get("votes", [])
    if not votes:
        return {"deviation": 0.0, "vote_margin": 1.0, "gap_rate": 0.0, "entropy": 0.0}

    # deviation: share of columns where top share < 0.6
    shaky = 0
    ent_sum, gap_count, cols = 0.0, 0, len(votes)
    margin_sum = 0.0
    for v in votes:
        tally = v.get("tally", {})
        total = sum(tally.values()) or 1.0
        sorted_vals = sorted(tally.values(), reverse=True)
        top = sorted_vals[0] if sorted_vals else total
        second = sorted_vals[1] if len(sorted_vals) > 1 else 0.0
        if (top / total) < 0.6:
            shaky += 1
        margin_sum += (top - second) / total if total else 1.0

        # entropy over candidates (base e)
        p = [(x / total) for x in tally.values()] if total else [1.0]
        ent = -sum(pi * math.log(pi + 1e-12) for pi in p)
        ent_sum += ent

        if v.get("chosen") == "-":
            gap_count += 1

    deviation = shaky / max(1, cols)
    vote_margin = margin_sum / max(1, cols)
    entropy = ent_sum / max(1, cols)
    gap_rate = gap_count / max(1, cols)

    # final feature vector (names are stable keys)
    return {
        "deviation": round(deviation, 4),
        "vote_margin": round(vote_margin, 4),
        "entropy": round(entropy, 4),
        "gap_rate": round(gap_rate, 4),
        # convenience: a coarse "confidence"
        "confidence": round(1.0 - deviation, 4),
    }
