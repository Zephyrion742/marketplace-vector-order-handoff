from marketplace_ingest import BuyerUpdate, SellerAsset, ingest_and_handoff


if __name__ == "__main__":
    asset = SellerAsset("shoe-42", "Trail shoe", "Water-resistant upper. Ships in two business days. Size exchange accepted within 30 days.")
    update = BuyerUpdate("order-1842", "Customer asks when the trail shoe ships")
    print(ingest_and_handoff(asset, update))
