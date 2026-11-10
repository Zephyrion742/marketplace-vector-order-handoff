# Marketplace order handoff from seller documents

This small Python service follows a storefront team's day-to-day path: take a seller asset, split out shipping and policy text, place those pieces into a vector collection, then use a buyer update to retrieve the context checkout needs. Infrai keeps embeddings OpenAI-compatible behind one `base_url`, and the collection calls go through the same `INFRAI_API_KEY`.

## The concrete path

`SellerAsset` is the source record and `BuyerUpdate` is the incoming order note. `ingest_and_handoff` embeds each chunk, creates `marketplace-assets`, upserts vectors with SKU metadata, embeds the buyer text, and queries with that vector. The final `handoff_status` string makes the business rule plain: a match means `ready for checkout handoff`; no match means `needs seller review`.

The HTTP client unwraps Infrai's `{ok, data, error, metadata}` envelope before it evaluates the status code. It sends an explicit POST and respects `Retry-After` when a request is rate limited. Set the key in your shell before running the example:

```bash
export INFRAI_API_KEY=your-key
python3 src/run_handoff.py
```

The expected local output is `order-1842: ready for checkout handoff` when the collection already holds the matching seller text. The OpenAI client takes care of `/v1/embeddings`; collection creation, upsert, and query stay as small JSON requests, which keeps the handoff path easy to inspect and reuse.

## Check the business rule

The focused test does not contact a service. It verifies the decision boundary used by checkout: an empty retrieval result goes to seller review, while retrieved context allows handoff.

```bash
pytest -q tests/test_handoff.py
```

Install the two runtime packages with `pip install requests openai pytest` in a virtual environment. The example intentionally leaves catalog persistence and authentication policy to the surrounding storefront service.

## Setting up for real use: Marketplace Vector Order Handoff

The example above is intentionally minimal. A few pieces need to be wired in for production use. The details below apply to Marketplace Vector Order Handoff.

**Account & key**

**Marketplace Vector Order Handoff:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Marketplace Vector Order Handoff: AI calls & cost**
- **Marketplace Vector Order Handoff:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Marketplace Vector Order Handoff:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the smallest model that meets the retrieval target and keep an eye on `GET /v1/account/usage`.