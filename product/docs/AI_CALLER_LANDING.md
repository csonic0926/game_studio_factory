# Product Factory caller landing

Use `product-factory` when the question is whether an integrated game earns its
price, when an author claims it is sufficiently finished, or when the next useful
improvement requires judging the whole purchase experience. Read the operating
workflow before using the receipt tools. Read/play/inspect the exact artifact;
source-code correctness and screenshot presence cannot answer this question.

Missing direction/contradictory product authority goes to Idea. A known bounded
implementation problem goes to the owning factory. Studio coordinates the result.
Product can honestly conclude VALUE_GAP, EVIDENCE_INSUFFICIENT or
CONTEXT_UNRESOLVED without filling missing answers or demanding more features.

Standalone commands (game-owned paths are relative to the explicit game root):

```sh
python3 product/product.py inspect --game-repo <GAME>
python3 product/product.py prepare --game-repo <GAME> --input design/product_value/<ID>/PRODUCT_VALUE_ASSESSMENT.json
python3 product/product.py record --game-repo <GAME> --input design/product_value/<ID>/PRODUCT_VALUE_ASSESSMENT.json --review design/product_value/<ID>/reviews/intent.json --review design/product_value/<ID>/reviews/completeness.json
python3 product/product.py check --game-repo <GAME> --result design/product_value/<ID>/PRODUCT_VALUE_RESULT.json
python3 studio/product.py check-value --game-repo <GAME> --result design/product_value/<ID>/PRODUCT_VALUE_RESULT.json --build <EXACT_BUILD_OR_MANIFEST>
```

`prepare` is read-only and returns the exact review package. `record` publishes
one immutable result after two independent AGREE reviews; that may be a negative
assessment. `check` proves recorded-source consistency. Only `gate`/`check-value`
checks eligibility for the requested exact build and current/adopted offer.
Refresh material external offer facts before a new claim. Hashes prove unchanged
captures, not that a storefront still has that price. Preserve source dates.

No command migrates, commissions, activates, archives, changes game content,
relinks skills, publishes a price, grants production permission or accepts a game.
