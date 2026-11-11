# GoreeCloud AI — Offline Retrieval Evaluation

**Purpose:** Test information-retrieval metric correctness and compare explicitly supplied, judged rankings without running Ollama, contacting an external service, downloading models, or reading private documents.

## Metrics

The evaluator calculates binary relevance metrics for a configurable rank cutoff k:

- Hit@K: fraction of queries with at least one relevant hit in the first K documents.
- Precision@K: relevant retrieved IDs divided by K, even if fewer than K IDs are returned.
- Recall@K: relevant retrieved IDs divided by all judged relevant IDs.
- MRR@K: reciprocal rank of the first relevant document, averaged over queries.
- MAP@K: average precision among relevant hits at K, normalized by min(number of relevant judgments, K).
- nDCG@K: binary discounted cumulative gain normalized by the ideal top-K ranking.

All aggregate numbers use a macro average across queries. Query IDs and document IDs are opaque strings, not fetched references. Duplicate IDs and invalid/oversized fixtures are rejected to prevent misleading scores.

## How to run

```bash
python -m goreecloud_ai.retrieval_eval docs/evaluation-fixture.json
```

The fixture format is a JSON object with an integer k between 1 and 100 and a nonempty queries list. Each query contains a distinct id, nonempty relevant document ID list, and retrieved document ID list ordered from best to worst. There is a 1 MB input-file cap, at most 1,000 queries, and at most 1,000 document IDs per list.

## Evidence limitations

The committed fixture is **synthetic**: its scores validate formulas and CLI behavior only. It does **not** demonstrate retrieval effectiveness for Qwen/Gemma or real documents, hallucination reduction, citation accuracy, semantic ranker quality, or benchmark superiority. To make real quality claims, build a consented and properly licensed evaluation corpus with human-reviewed judgments, record model hashes/versions and hardware, perform live retrieval runs, and compare against the prior keyword baseline.

This evaluator reads a local file explicitly selected by its operator and prints a local JSON report. It does not update knowledge stores or send prompts over a network.
