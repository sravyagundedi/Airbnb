import os
import json
import numpy as np
from typing import List, Dict, Any, Optional

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reco_artifacts")


class RecommenderService:
    def __init__(self):
        self.hybrid_sim: Optional[np.ndarray] = None
        self.features: Optional[np.ndarray] = None
        self.venue_ids: List[str] = []
        self.venue_to_idx: Dict[str, int] = {}
        self.user_history: Dict[int, List[str]] = {}
        self.loaded = False
        self.load_artifacts()

    def load_artifacts(self):
        sim_path = os.path.join(ARTIFACTS_DIR, "hybrid_similarity.npy")
        feat_path = os.path.join(ARTIFACTS_DIR, "venue_features.npy")
        ids_path = os.path.join(ARTIFACTS_DIR, "venue_ids.json")

        if os.path.exists(sim_path) and os.path.exists(ids_path):
            try:
                self.hybrid_sim = np.load(sim_path)
                self.features = np.load(feat_path) if os.path.exists(feat_path) else None
                with open(ids_path, "r", encoding="utf-8") as f:
                    self.venue_ids = json.load(f)
                self.venue_to_idx = {vid: i for i, vid in enumerate(self.venue_ids)}
                self.loaded = True
            except Exception as e:
                print(f"Failed to load reco artifacts: {e}")
                self.loaded = False

    def fold_interaction(self, user_id: int, venue_id: str):
        self.user_history.setdefault(user_id, []).append(venue_id)

    def recommend(
        self,
        liked_venue_ids: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[str]:
        if not self.loaded or self.hybrid_sim is None or not self.venue_ids:
            return self.venue_ids[:top_k] if self.venue_ids else []

        # Combine explicit liked venues with user history
        active_likes = list(liked_venue_ids or [])
        if user_id and user_id in self.user_history:
            active_likes.extend(self.user_history[user_id])

        valid_indices = [self.venue_to_idx[vid] for vid in active_likes if vid in self.venue_to_idx]

        if not valid_indices:
            # Cold start: return top venues by default centrality
            centrality = np.sum(self.hybrid_sim, axis=1)
            top_indices = np.argsort(centrality)[::-1][:top_k]
            return [self.venue_ids[i] for i in top_indices]

        # Aggregate similarity scores from all liked venues
        scores = np.zeros(len(self.venue_ids), dtype=np.float32)
        for idx in valid_indices:
            scores += self.hybrid_sim[idx]

        # Mask already liked items so we don't repeat them
        for idx in valid_indices:
            scores[idx] = -np.inf

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [self.venue_ids[i] for i in top_indices]


recommender_service = RecommenderService()
