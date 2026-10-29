import json

from src.tools.test_design_tools import parse_collection


def test_parse_collection_accepts_api_list_data():
    item = {"_id": "SECSUG-1", "candidate_only": True}
    assert parse_collection(json.dumps([item])) == [item]


def test_parse_collection_accepts_paged_data():
    item = {"_id": "SECSUG-1", "candidate_only": True}
    assert parse_collection(json.dumps({"items": [item]})) == [item]


def test_parse_collection_rejects_unexpected_values():
    assert parse_collection("not-json") == []
    assert parse_collection(json.dumps({"status": "error"})) == []
