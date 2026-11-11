"""Deterministic, offline information-retrieval evaluation.

This module never invokes an AI model, network connection, or repository tool.
Synthetic fixtures validate metric math, not real-model retrieval quality.
"""
import argparse
import json
import math
from pathlib import Path


MAX_FIXTURE_BYTES = 1_000_000
MAX_QUERIES = 1000
MAX_DOCS = 1000


def _identifiers(values, label):
    if not isinstance(values, list) or len(values) > MAX_DOCS:
        raise ValueError(f"{label} must be a bounded list")
    if any(not isinstance(value, str) or not value or len(value) > 180 for value in values):
        raise ValueError(f"{label} must contain nonempty document IDs")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} contains duplicate document IDs")
    return values


def evaluate_one(relevant: list[str], retrieved: list[str], k: int) -> dict[str, float]:
    """Compute binary relevance metrics over unique IDs at rank k."""
    if not 1 <= k <= 100:
        raise ValueError("k must be between 1 and 100")
    ground_truth = set(_identifiers(relevant, "relevant"))
    ranked = _identifiers(retrieved, "retrieved")[:k]
    if not ground_truth:
        raise ValueError("relevant must contain at least one judged document")
    hits = [index + 1 for index, value in enumerate(ranked) if value in ground_truth]
    hit = float(bool(hits))
    precision = len(hits) / k
    recall = len(hits) / len(ground_truth)
    reciprocal_rank = 1 / hits[0] if hits else 0.0
    average_precision = sum(
        sum(1 for item in ranked[:rank] if item in ground_truth) / rank
        for rank in hits
    ) / min(len(ground_truth), k)
    dcg = sum(1 / math.log2(rank + 1) for rank in hits)
    ideal_count = min(len(ground_truth), k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return {
        "hit_at_k": hit,
        "precision_at_k": precision,
        "recall_at_k": recall,
        "mrr_at_k": reciprocal_rank,
        "map_at_k": average_precision,
        "ndcg_at_k": dcg / ideal,
    }


def evaluate_fixture(data: dict) -> dict:
    """Evaluate a bounded synthetic fixture, with macro-averaged scores."""
    if not isinstance(data, dict):
        raise ValueError("Fixture must be a JSON object")
    k = data.get("k")
    if type(k) is not int or not 1 <= k <= 100:
        raise ValueError("Fixture k must be an integer from 1 through 100")
    queries = data.get("queries")
    if not isinstance(queries, list) or not 1 <= len(queries) <= MAX_QUERIES:
        raise ValueError("Fixture queries must be a nonempty bounded list")
    results = []
    ids = set()
    for query in queries:
        if not isinstance(query, dict):
            raise ValueError("Each query must be an object")
        query_id = query.get("id")
        if not isinstance(query_id, str) or not 1 <= len(query_id) <= 180 or query_id in ids:
            raise ValueError("Query IDs must be distinct and nonempty")
        ids.add(query_id)
        metrics = evaluate_one(query.get("relevant"), query.get("retrieved"), k)
        results.append({"id": query_id, **metrics})
    names = ["hit_at_k", "precision_at_k", "recall_at_k", "mrr_at_k", "map_at_k", "ndcg_at_k"]
    summary = {name: sum(row[name] for row in results) / len(results) for name in names}
    return {"k": k, "queries": len(results), "metrics": summary, "per_query": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate offline GoreeCloud AI retrieval ranking fixtures")
    parser.add_argument("fixture", help="Path to a bounded local JSON evaluation fixture")
    args = parser.parse_args(argv)
    fixture = Path(args.fixture)
    if not fixture.is_file() or fixture.stat().st_size > MAX_FIXTURE_BYTES:
        parser.error("Fixture must be a regular JSON file no larger than 1 MB")
    try:
        data = json.loads(fixture.read_text(encoding="utf-8"))
        report = evaluate_fixture(data)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.error(f"Invalid retrieval fixture: {exc}")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
