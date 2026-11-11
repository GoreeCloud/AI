import json

import pytest

from goreecloud_ai.retrieval_eval import evaluate_one, evaluate_fixture, main


def test_ranking_metrics_at_k():
    scores = evaluate_one(["doc-b", "doc-c"], ["doc-a", "doc-b", "doc-c"], 3)
    assert scores["hit_at_k"] == 1.0
    assert scores["precision_at_k"] == pytest.approx(2 / 3)
    assert scores["recall_at_k"] == 1.0
    assert scores["mrr_at_k"] == 0.5
    assert scores["map_at_k"] == pytest.approx(((1 / 2) + (2 / 3)) / 2)
    assert scores["ndcg_at_k"] == pytest.approx(
        ((1 / 1.584962500721156) + 0.5) / (1 + (1 / 1.584962500721156))
    )


def test_empty_hits_report_zero():
    metrics = evaluate_one(["relevant"], ["other"], 3)
    assert all(value == 0 for value in metrics.values())


def test_macro_average_and_query_count():
    fixture = {"k": 2, "queries": [
        {"id": "first", "relevant": ["a"], "retrieved": ["a", "b"]},
        {"id": "second", "relevant": ["c"], "retrieved": ["b", "a"]},
    ]}
    report = evaluate_fixture(fixture)
    assert report["queries"] == 2
    assert report["metrics"]["hit_at_k"] == 0.5
    assert report["per_query"][0]["id"] == "first"


@pytest.mark.parametrize("input_value", [
    {},
    {"k": True, "queries": [{"id": "x", "relevant": ["a"], "retrieved": ["a"]}]},
    {"k": 0, "queries": []},
    {"k": 3, "queries": []},
    {"k": 1, "queries": [{"id": "a", "relevant": [], "retrieved": []}]},
    {"k": 1, "queries": [{"id": "a", "relevant": ["doc"], "retrieved": ["doc", "doc"]}]},
    {"k": 1, "queries": [
        {"id": "x", "relevant": ["doc"], "retrieved": []},
        {"id": "x", "relevant": ["other"], "retrieved": []},
    ]},
])
def test_rejects_invalid_fixtures(input_value):
    with pytest.raises(ValueError):
        evaluate_fixture(input_value)


def test_cli_outputs_json_for_local_fixture(tmp_path, capsys):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "k": 2, "queries": [{"id": "test", "relevant": ["doc-1"], "retrieved": ["doc-1"]}]
    }), encoding="utf-8")
    assert main([str(fixture)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["metrics"]["hit_at_k"] == 1.0
    assert report["metrics"]["precision_at_k"] == 0.5


def test_cli_rejects_oversized_file(tmp_path):
    fixture = tmp_path / "too-large.json"
    fixture.write_text("x" * 1000001)
    with pytest.raises(SystemExit) as caught:
        main([str(fixture)])
    assert caught.value.code != 0
