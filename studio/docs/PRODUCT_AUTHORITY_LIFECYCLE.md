# Studio Product Authority lifecycle

Product commission and whole-direction retirement are authority transitions,
not file-management conventions.

```text
NO_ACTIVE_PRODUCT_AUTHORITY
  -> Idea exploration -> explicit commission -> Idea compile/check
  -> product.py activate -> ACTIVE

ACTIVE
  -> explicit user revocation
  -> immutable authority snapshot
  -> fresh semantic alignment with all pending cards inventoried
  -> product.py archive -> NO_ACTIVE_PRODUCT_AUTHORITY
```

The game-owned source of truth is:

```text
design/product/PRODUCT_AUTHORITY_REGISTER.json
```

When the register exists, every Studio, Gameplay, and baseline consumer must
obey it. `NO_ACTIVE_PRODUCT_AUTHORITY` overrides the mere presence of old code,
baselines, cards, or design documents.

## Activate a commissioned Product Thesis

Run normal Idea Factory exploration, explicit commission, compile, and check.
Then record the active authority:

```bash
python3 <STUDIO_ROOT>/studio/product.py activate \
  --game-repo <GAME_REPO> \
  --authority-id <PORTABLE_AUTHORITY_ID> \
  --recorded-at <ISO_8601>
```

Activation reads the exact canonical Product Thesis, constraints, commission
input, and Idea result. It refuses to replace another active authority.

## Archive an active direction

The user may use ordinary language such as “stop this whole direction; keep it
as history and do not keep asking me to approve it.” Do not demand invented
Factory tokens.

First prepare an immutable authority snapshot while canonical bytes are still
active:

```bash
python3 <STUDIO_ROOT>/studio/product.py prepare-archive \
  --game-repo <GAME_REPO> \
  --transition-id <TRANSITION_ID> \
  --prepared-at <ISO_8601>
```

This copies only the bounded Product authority package into
`design/product/archive/<transition_id>/`. It does not move gameplay, code,
assets, admissions, baselines, or evidence. The snapshot is lifecycle evidence,
not a general-purpose backup.

Next author the semantic-alignment input **before** authority mutation:

- `proposed_transition = ARCHIVE_PRODUCT_DIRECTION`;
- bind the immutable snapshot Product Thesis as the active product evidence;
- inventory every currently pending Studio decision card;
- set each disposition to `WITHDRAW_BY_PRODUCT_ARCHIVE`;
- bind the exact natural-language user revocation;
- present only the exact aligned completion acknowledgement.

Use a fresh reviewer and require `PASS_ALIGNMENT`; archiving does not require a
second human verdict because the input itself is the explicit revocation.

Then execute:

```bash
python3 <STUDIO_ROOT>/studio/product.py archive \
  --game-repo <GAME_REPO> \
  --snapshot design/studio/product_authority_transitions/<TRANSITION_ID>/PRODUCT_AUTHORITY_ARCHIVE_SNAPSHOT.json \
  --alignment-input design/studio/interaction_alignment/<INTERACTION_ID>/STUDIO_SEMANTIC_ALIGNMENT_INPUT.json \
  --alignment-review design/studio/interaction_alignment/<INTERACTION_ID>/STUDIO_SEMANTIC_ALIGNMENT_REVIEW.json \
  --recorded-at <ISO_8601>
```

The transition:

- sets product authority to `NO_ACTIVE_PRODUCT_AUTHORITY`;
- removes only canonical Product authority files after their immutable snapshot
  is verified;
- marks pending cards `PRODUCT_ARCHIVED` in the Studio register;
- leaves each card's human verdict untouched instead of fabricating
  `USER_REJECTED` text the user never supplied;
- leaves runtime work and evidence at their original paths as historical or
  potentially reusable material;
- makes old accepted baselines ineligible as predecessors for a new product.

Afterward, Studio returns to Idea exploration. It may not resume production
until a new Product Thesis is explicitly commissioned and activated.
