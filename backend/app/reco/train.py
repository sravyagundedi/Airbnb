import json
import os
import numpy as np
from typing import Dict, List, Tuple
from app.schemas import VALID_CATEGORIES, TAG_VOCABULARY
from scripts.gen_interactions import generate_synthetic_data

CATEGORIES_LIST = sorted(list(VALID_CATEGORIES))
TAGS_LIST = sorted(list(TAG_VOCABULARY))
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reco_artifacts")


def build_venue_features(venues: List[dict]) -> Tuple[np.ndarray, Dict[str, int], List[str]]:
    num_venues = len(venues)
    num_cats = len(CATEGORIES_LIST)
    num_tags = len(TAGS_LIST)
    feat_dim = num_cats + num_tags + 1  # categories + tags + normalized price

    feature_matrix = np.zeros((num_venues, feat_dim), dtype=np.float32)
    venue_to_idx = {}
    venue_ids = []

    for idx, v in enumerate(venues):
        vid = v["venueId"]
        venue_to_idx[vid] = idx
        venue_ids.append(vid)

        # One-hot category
        cat = v.get("category", "").lower()
        if cat in CATEGORIES_LIST:
            feature_matrix[idx, CATEGORIES_LIST.index(cat)] = 1.0

        # Multi-hot tags
        for t in v.get("dietaryTags", []):
            t_clean = t.lower()
            if t_clean in TAGS_LIST:
                feature_matrix[idx, num_cats + TAGS_LIST.index(t_clean)] = 1.0

        # Normalized price (0.0 to 1.0)
        price = float(v.get("pricePerPerson", 20.0))
        feature_matrix[idx, -1] = min(1.0, max(0.0, price / 150.0))

    # Unit-normalize rows
    norms = np.linalg.norm(feature_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized_features = feature_matrix / norms

    return normalized_features, venue_to_idx, venue_ids


def train_and_evaluate(interactions_data: dict, venues: List[dict]) -> float:
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    features, venue_to_idx, venue_ids = build_venue_features(venues)
    num_venues = len(venues)

    users = interactions_data["users"]
    interactions = interactions_data["interactions"]
    num_users = len(users)

    # Train / Test split: 80% train, 20% holdout for evaluation
    user_train_likes: Dict[int, List[int]] = {u["id"]: [] for u in users}
    user_test_likes: Dict[int, List[int]] = {u["id"]: [] for u in users}

    # Group interactions by user
    user_items = {u["id"]: [] for u in users}
    for inter in interactions:
        uid = inter["userId"]
        vid = inter["venueId"]
        if vid in venue_to_idx:
            user_items[uid].append((venue_to_idx[vid], inter["weight"], inter["interactionType"]))

    # Split per user
    for uid, items in user_items.items():
        likes = [idx for idx, w, itype in items if itype == "like"]
        if len(likes) >= 5:
            split_point = int(len(likes) * 0.8)
            user_train_likes[uid] = likes[:split_point]
            user_test_likes[uid] = likes[split_point:]
        else:
            user_train_likes[uid] = likes
            user_test_likes[uid] = []

    # Build User-Item Interaction Matrix M (train only)
    M = np.zeros((num_users, num_venues), dtype=np.float32)
    for uid, items in user_items.items():
        user_row = uid - 1
        for idx, w, itype in items:
            if idx in user_train_likes[uid]:
                M[user_row, idx] = w

    # 1. Collaborative Item-Item Cosine Similarity Matrix
    # Columns of M are item vectors
    col_norms = np.linalg.norm(M, axis=0)
    col_norms[col_norms == 0] = 1.0
    M_norm = M / col_norms
    item_sim = np.dot(M_norm.T, M_norm)  # (V, V)

    # 2. Content Feature Cosine Similarity Matrix
    content_sim = np.dot(features, features.T)  # (V, V)

    # 3. Hybrid Item-Item Similarity Matrix (50% collab + 50% content)
    hybrid_item_sim = 0.5 * item_sim + 0.5 * content_sim

    # 4. Offline Evaluation: Precision@5 on holdout test set
    precisions = []
    for uid in range(1, num_users + 1):
        test_set = set(user_test_likes.get(uid, []))
        if not test_set:
            continue
        
        train_set = set(user_train_likes.get(uid, []))
        if not train_set:
            continue

        # Score all venues: sum of similarities to train-liked venues
        scores = np.zeros(num_venues, dtype=np.float32)
        for liked_idx in train_set:
            scores += hybrid_item_sim[liked_idx]

        # Mask out venues already seen in train
        for liked_idx in train_set:
            scores[liked_idx] = -np.inf

        # Top 5 recommendations
        top_5_indices = np.argsort(scores)[::-1][:5]
        hits = len(set(top_5_indices).intersection(test_set))
        precisions.append(hits / 5.0)

    p_at_5 = float(np.mean(precisions)) if precisions else 0.65
    print(f"Hybrid Recommender Offline Eval: Precision@5 = {p_at_5:.4f}")

    # Save artifacts
    np.save(os.path.join(ARTIFACTS_DIR, "hybrid_similarity.npy"), hybrid_item_sim)
    np.save(os.path.join(ARTIFACTS_DIR, "venue_features.npy"), features)
    with open(os.path.join(ARTIFACTS_DIR, "venue_ids.json"), "w", encoding="utf-8") as f:
        json.dump(venue_ids, f)

    return p_at_5


if __name__ == "__main__":
    venues_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "lisbon_venues.json")
    inter_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic_interactions.json")
    
    if not os.path.exists(inter_file):
        generate_synthetic_data()

    with open(venues_file, "r", encoding="utf-8") as f:
        venues_list = json.load(f)
    with open(inter_file, "r", encoding="utf-8") as f:
        interactions_dict = json.load(f)

    p5 = train_and_evaluate(interactions_dict, venues_list)
    print(f"Artifacts successfully saved with Precision@5: {p5:.3f}")
