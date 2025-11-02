# src/compareblocks/rl_policy/rl_policy_engine.py
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
import numpy as np

MODEL_PATH = Path("data/q_table.json")

class RLPolicyEngine:
    """Tiny epsilon-greedy Q-table for Pick/Merge/Review."""

    def __init__(self, actions=None, epsilon=0.1, alpha=0.3, gamma=0.9):
        self.actions = actions or ["Pick", "Merge", "Review"]
        self.epsilon, self.alpha, self.gamma = epsilon, alpha, gamma
        self.q_table: dict[str, dict[str, float]] = defaultdict(lambda: {a: 0.0 for a in self.actions})
        self.backend = "qtable"
        if MODEL_PATH.exists():
            self._load()

    def _state_key(self, features: dict[str, float]) -> str:
        # bucketize features for stability
        rounded = {k: round(v, 2) for k, v in sorted(features.items())}
        return json.dumps(rounded, sort_keys=True)

    def predict(self, features: dict[str, float]) -> str:
        key = self._state_key(features)
        if np.random.rand() < self.epsilon:
            return np.random.choice(self.actions)
        qs = self.q_table[key]
        return max(qs.items(), key=lambda kv: kv[1])[0]

    def record_feedback(self, features, agent_action, user_action, reward=1.0):
        key = self._state_key(features)
        q_values = self.q_table[key]
        best_future = max(q_values.values())
        delta = self.alpha * (reward + self.gamma * best_future - q_values[agent_action])
        q_values[agent_action] += delta
        self.q_table[key] = q_values
        self._save()

    def _save(self):
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MODEL_PATH.open("w", encoding="utf-8") as f:
            json.dump(self.q_table, f, indent=2)

    def _load(self):
        try:
            self.q_table = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        except Exception:
            self.q_table = defaultdict(lambda: {a: 0.0 for a in self.actions})

rl_engine = RLPolicyEngine()
