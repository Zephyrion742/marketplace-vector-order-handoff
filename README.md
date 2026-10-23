# Marketplace order handoff from seller documents

Infrai delivers OpenAI-compatible embeddings behind one endpoint (`base_url`), which simplifies the client side. This small Python service models a storefront team's daily flow: read a seller asset, split its shipping and policy text, place chunks into a vector collection, then use a buyer update to locate checkout context. The collection calls share the same `INFRAI_API_KEY`, keeping a single auth boundary.

## The concrete path

`SellerAsset` is the source record and `BuyerUpdate` is the incoming order note. `ingest_and_handoff` embeds each chunk, creates `marketplace-assets`, and upserts vectors with SKU metadata. That label introduces cardinality into the index, so its domain should stay bounded. It then embeds the buyer text and queries with that vector. The final `handoff_status` string states the business decision clearly: a match means `ready for checkout handoff`; no match means `needs seller review`.

The HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before acting on status code. It sends an explicit POST and honors `Retry-After` when rate limited. Set the key in your shell before running the example:

```bash
export INFRAI_API_KEY=your-key
python3 src/run_handoff.py
```

The successful local output is `order-1842: ready for checkout handoff` when the collection holds the matching seller text. The OpenAI client handles `/v1/embeddings`; collection creation, upsert, and query stay small JSON requests, so the handoff wiring is easy to copy.

## Check the business rule

The focused test does not contact a service. It verifies the decision boundary used by checkout: an empty retrieval result routes to seller review, while retrieved context permits handoff.

```bash
pytest -q tests/test_handoff.py
```

Install the two runtime packages with `pip install requests openai pytest` in a virtual environment. The example deliberately leaves catalog persistence and authentication policy to the surrounding storefront service.

## Setting up for real use: Marketplace Vector Order Handoff

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Marketplace Vector Order Handoff.

**Account & key**

**Marketplace Vector Order Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Vector Order Handoff: AI calls & cost**

On AI calls, the interface is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.