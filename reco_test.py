import asyncio
from collections import defaultdict, Counter
from datetime import datetime
import math
import random
from typing import Dict, List, Tuple, Set

from app.core.db import products_coll, actions_coll
from app.models import ActionEnum

K = 10
TRAIN_RATIO = 0.7
MIN_ACTIONS_FOR_USER = 3
POSITIVE_ACTIONS = {ActionEnum.LIKE.value, ActionEnum.PURCHASE.value}

def user_type(total_actions: int) -> str:
  if total_actions < 5:
    return "cold"
  elif total_actions < 20:
    return "casual"
  else:
    return "power"


def weight(action: str) -> int:
  if action == ActionEnum.VIEW.value:
    return 1
  if action == ActionEnum.LIKE.value:
    return 3
  if action == ActionEnum.PURCHASE.value:
    return 5
  return 0


def recommend_personal(user_train_actions: List[dict], products: List[dict], k: int) -> List[str]:
  if not user_train_actions:
    return []

  product_scores: Dict[str, float] = {}
  category_scores: Dict[str, float] = {}

  for a in user_train_actions:
    w = weight(a.get("action"))
    pid = a.get("productId")
    cat = a.get("category")
    if pid:
      product_scores[pid] = product_scores.get(pid, 0.0) + w
    if cat:
      category_scores[cat] = category_scores.get(cat, 0.0) + w

  scored: List[Tuple[float, str]] = []
  for p in products:
    pid = str(p["_id"])
    base = product_scores.get(pid, 0.0)
    cat = p.get("category")
    base += 0.5 * category_scores.get(cat, 0.0)
    if base <= 0:
      continue
    scored.append((base, pid))

  scored.sort(key=lambda x: x[0], reverse=True)
  return [pid for _, pid in scored[:k]]


def build_global_popularity(actions: List[dict]) -> List[str]:
  cnt = Counter()
  for a in actions:
    if a.get("action") in POSITIVE_ACTIONS:
      pid = a.get("productId")
      if pid:
        cnt[pid] += 1
  return [pid for pid, _ in cnt.most_common()]


def recommend_popular(global_popular: List[str], banned: Set[str], k: int) -> List[str]:
  result = []
  for pid in global_popular:
    if pid in banned:
      continue
    result.append(pid)
    if len(result) >= k:
      break
  return result


def recommend_random(all_product_ids: List[str], banned: Set[str], k: int) -> List[str]:
  candidates = [pid for pid in all_product_ids if pid not in banned]
  if len(candidates) <= k:
    return candidates
  return random.sample(candidates, k)

def precision_recall_f1(recommended: List[str], relevant: Set[str]) -> Tuple[float, float, float]:
  if not recommended:
    return 0.0, 0.0, 0.0
  if not relevant:
    return 0.0, 0.0, 0.0

  rec_set = set(recommended)
  tp = len(rec_set & relevant)

  precision = tp / len(recommended) if recommended else 0.0
  recall = tp / len(relevant) if relevant else 0.0

  if precision + recall == 0:
    f1 = 0.0
  else:
    f1 = 2 * precision * recall / (precision + recall)

  return precision, recall, f1


async def main():
  print("=== DayStore Recommendation Quality Test ===")

  actions = await actions_coll.find({}).to_list(length=None)
  products = await products_coll.find({}).to_list(length=None)

  if not actions or not products:
    print("Нет данных (actions или products пусты). Нечего оценивать.")
    return

  print(f"Всего действий: {len(actions)}")
  print(f"Всего товаров:  {len(products)}")

  by_user: Dict[str, List[dict]] = defaultdict(list)
  for a in actions:
    uid = a.get("userId")
    if uid:
      by_user[uid].append(a)

  all_product_ids = [str(p["_id"]) for p in products]

  global_popular = build_global_popularity(actions)

  algos = ["personal", "popular", "random"]

  stats: Dict[str, Dict[str, Dict[str, float]]] = {
    alg: {
      "all":   {"prec_sum": 0.0, "rec_sum": 0.0, "f1_sum": 0.0, "users": 0},
      "cold":  {"prec_sum": 0.0, "rec_sum": 0.0, "f1_sum": 0.0, "users": 0},
      "casual":{"prec_sum": 0.0, "rec_sum": 0.0, "f1_sum": 0.0, "users": 0},
      "power": {"prec_sum": 0.0, "rec_sum": 0.0, "f1_sum": 0.0, "users": 0},
    }
    for alg in algos
  }

  random.seed(42)

  processed_users = 0

  for user_id, acts in by_user.items():
    def get_ts(a):
      ts = a.get("timestamp")
      if isinstance(ts, datetime):
        return ts
      return datetime.min

    acts_sorted = sorted(acts, key=get_ts)

    if len(acts_sorted) < MIN_ACTIONS_FOR_USER:
      continue

    processed_users += 1

    split_idx = max(1, int(len(acts_sorted) * TRAIN_RATIO))
    train_actions = acts_sorted[:split_idx]
    test_actions = acts_sorted[split_idx:]

    if not test_actions:
      continue

    relevant: Set[str] = set()
    for a in test_actions:
      if a.get("action") in POSITIVE_ACTIONS:
        pid = a.get("productId")
        if pid:
          relevant.add(pid)

    if not relevant:
      continue

    user_seen: Set[str] = set()
    for a in train_actions + test_actions:
      pid = a.get("productId")
      if pid:
        user_seen.add(pid)

    utype = user_type(len(acts_sorted))

    rec_personal = recommend_personal(train_actions, products, K)
    p, r, f1 = precision_recall_f1(rec_personal, relevant)
    for seg in ["all", utype]:
      stats["personal"][seg]["prec_sum"] += p
      stats["personal"][seg]["rec_sum"] += r
      stats["personal"][seg]["f1_sum"] += f1
      stats["personal"][seg]["users"] += 1

    rec_popular = recommend_popular(global_popular, user_seen, K)
    p, r, f1 = precision_recall_f1(rec_popular, relevant)
    for seg in ["all", utype]:
      stats["popular"][seg]["prec_sum"] += p
      stats["popular"][seg]["rec_sum"] += r
      stats["popular"][seg]["f1_sum"] += f1
      stats["popular"][seg]["users"] += 1

    rec_random = recommend_random(all_product_ids, user_seen, K)
    p, r, f1 = precision_recall_f1(rec_random, relevant)
    for seg in ["all", utype]:
      stats["random"][seg]["prec_sum"] += p
      stats["random"][seg]["rec_sum"] += r
      stats["random"][seg]["f1_sum"] += f1
      stats["random"][seg]["users"] += 1

  if processed_users == 0:
    print("Недостаточно пользователей с действиями для оценки.")
    return

  print(f"\nПользователей, вошедших в оценку: {processed_users}")
  print(f"K = {K}, train_ratio = {TRAIN_RATIO}, MIN_ACTIONS_FOR_USER = {MIN_ACTIONS_FOR_USER}")

  segments = ["all", "cold", "casual", "power"]

  print("\n=== Результаты (средние Precision@K, Recall@K, F1@K) ===\n")
  for seg in segments:
    print(f"--- Segment: {seg} ---")
    for alg in algos:
      info = stats[alg][seg]
      n = info["users"]
      if n == 0:
        print(f"  {alg:8s}: нет данных")
        continue
      avg_p = info["prec_sum"] / n
      avg_r = info["rec_sum"] / n
      avg_f1 = info["f1_sum"] / n
      print(f"  {alg:8s}: P={avg_p:.3f}, R={avg_r:.3f}, F1={avg_f1:.3f}  (users={n})")
    print()

if __name__ == "__main__":
  asyncio.run(main())
