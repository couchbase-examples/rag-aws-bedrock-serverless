"""Tests for the ingest Lambda's SQS batch handling.

These run without AWS or Couchbase: the Bedrock client, the cluster connection
and the vector store are replaced with fakes so only the handler's batch logic
is exercised.

    pip install -r src/lambdas/ingest/requirements.txt pytest
    pytest tests
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "lambdas" / "ingest"))

import ingest  # noqa: E402


def sqs_event(docs):
    return {"Records": [{"messageId": str(i), "body": json.dumps(doc)} for i, doc in enumerate(docs)]}


class FakeVectorStore:
    def __init__(self):
        self.calls = []

    def add_texts(self, texts, ids=None):
        self.calls.append((list(texts), list(ids)))
        return ids


@pytest.fixture
def fake_store(monkeypatch):
    store = FakeVectorStore()
    monkeypatch.setattr(ingest, "load_dotenv", lambda: None)
    monkeypatch.setattr(ingest.boto3, "client", lambda *a, **k: object())
    monkeypatch.setattr(ingest, "connect_to_couchbase", lambda *a, **k: object())
    monkeypatch.setattr(ingest, "BedrockEmbeddings", lambda **k: object())
    monkeypatch.setattr(ingest, "get_vector_store", lambda *a, **k: store)
    return store


def test_parse_records_keeps_every_record_in_order():
    docs = [{"id": f"doc-{i}", "text": f"page {i}", "extra": i} for i in range(3)]

    texts, ids = ingest.parse_records(sqs_event(docs)["Records"])

    assert texts == ["page 0", "page 1", "page 2"]
    assert ids == ["doc-0", "doc-1", "doc-2"]


def test_handler_stores_full_sqs_batch(fake_store):
    # The CDK event source mapping uses batch_size=10.
    docs = [{"id": f"doc-{i}", "text": f"page {i}"} for i in range(10)]

    response = ingest.lambda_handler(sqs_event(docs), None)

    assert response["statusCode"] == 200
    assert fake_store.calls == [([d["text"] for d in docs], [d["id"] for d in docs])]


def test_handler_rejects_empty_batch(fake_store):
    assert ingest.lambda_handler({"Records": []}, None)["statusCode"] == 400
    assert ingest.lambda_handler({}, None)["statusCode"] == 400
    assert fake_store.calls == []
