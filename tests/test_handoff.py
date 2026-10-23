import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marketplace_ingest import BuyerUpdate, handoff_status


def test_checkout_handoff_requires_retrieved_seller_context():
    update = BuyerUpdate("order-7", "Where is my package?")
    assert handoff_status(update, []) == "order-7: needs seller review"
    assert handoff_status(update, [{"id": "shoe-42-0"}]) == "order-7: ready for checkout handoff"
