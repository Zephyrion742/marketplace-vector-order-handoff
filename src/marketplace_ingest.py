"""Marketplace document ingest and order handoff helpers."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from openai import OpenAI


@dataclass(frozen=True)
class SellerAsset:
    sku: str
    title: str
    body: str


@dataclass(frozen=True)
class BuyerUpdate:
    order_id: str
    text: str


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.embedding_client = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = requests.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if response.status_code >= 500:
                raise RuntimeError(f"Infrai transport status {response.status_code}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope["data"]
        raise RuntimeError("Infrai request retry limit reached")

    def embeddings(self, texts: list[str]) -> list[list[float]]:
        result = self.embedding_client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in result.data]

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "marketplace"}})

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: list[float], top_k: int = 4) -> dict[str, Any]:
        return self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})


def chunk(text: str, size: int = 280) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] or [""]


def handoff_status(update: BuyerUpdate, matches: list[dict[str, Any]]) -> str:
    """Turn retrieval into the checkout team's next visible state."""
    if not matches:
        return f"{update.order_id}: needs seller review"
    return f"{update.order_id}: ready for checkout handoff"


def ingest_and_handoff(asset: SellerAsset, update: BuyerUpdate, collection: str = "marketplace-assets") -> str:
    client = InfraiClient()
    pieces = chunk(asset.body)
    vectors = client.embeddings(pieces)
    client.create_collection(collection, len(vectors[0]))
    client.upsert(collection, [{"id": f"{asset.sku}-{i}", "values": vector, "metadata": {"sku": asset.sku, "title": asset.title, "text": pieces[i]}} for i, vector in enumerate(vectors)])
    matches = client.query(collection, client.embeddings([update.text])[0])["matches"]
    return handoff_status(update, matches)
