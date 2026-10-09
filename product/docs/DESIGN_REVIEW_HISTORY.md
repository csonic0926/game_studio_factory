# Product Factory design review history

These are independent reusable-Factory design reviews. They are not game-owned
ledger approvals, USER acceptance, or implementation validation. The original
design is preserved in Git commit c0f6392; it was revised rather than overwritten
as accepted history. Reviewers received the same exact version in fresh contexts
without first-pass peer conclusions.

## First design

SHA-256: 2ab5d582518985be6e0b5a4835e9aef8a0edf0bcebefef0eadb2f26ac182be48

Intent/experience: PASS. Completeness/project: FAIL. The complete failed report
is retained below, followed by the repaired design's independent conclusions.

### Completeness/project, verbatim report

FAIL: two contract gaps need clarification before implementation

Reviewed exact design SHA256 2ab5d582518985be6e0b5a4835e9aef8a0edf0bcebefef0eadb2f26ac182be48 independently, without peer conclusions. Read root/Idea/Studio instructions, Idea implementation, shared v2/v3 workflows and state/reference/acceptance code, Studio authority lifecycle and consumer routing.

1. Current-offer gate can admit a grounded proposal
   - Design lines 144–158 allow conditional support for proposed offers, but gate requires only a matching build, grounded context and SUPPORTED judgment. It rejects “hypothetical-only” context, which does not necessarily exclude an accurately sourced user proposal
   - Example: the current price is $20, while the user proposes $5. The $5 assessment can have grounded provenance, actual experiential evidence and two AGREE reviews. The specified gate conditions do not explicitly stop Studio consuming it as current paid-value support
   - Repair: define gate eligibility explicitly as current/adopted offer plus grounded audience, with no unresolved conditionality. Proposed/scenario assessments can be recorded and checked but must return ineligible for the current-offer gate. Include price/currency/platform/region/audience and their exact provenance in the returned claim scope. Add a negative fixture using a grounded user-proposed price, distinct from an AI hypothesis

2. Shared-ledger completion lacks a binding to the reviewed task’s output scope
   - Lines 200–205 require a checked Product result among the task’s artifacts, but do not explicitly bind that result to the task’s reviewed assessment identity, expected subject/offer, and production paths
   - Existing factory_core/state.py validates artifact references but does not generally enforce that they fulfill production_scope. Existing specialist acceptance must supply that check; story/v2.py already checks exact outputs and scope coverage
   - Consequently, merely checking any valid result and its inclusion in artifacts could close task A using an unrelated assessment B from the same game
   - Repair: specify the Product acceptance adapter’s exact task/design binding and scope-coverage rules. Require the expected assessment/result path to be in the approved production scope, the consumed result among actual checkpoint outputs, and the result’s assessed subject/context to match the sealed task specification. Test substitution of another valid same-game result and omission of a required output

Otherwise sound:
- Product judges whole-experience purchase value, rather than technical release readiness or feature totals
- Idea retains commission and product decisions; Studio retains lifecycle and playable-baseline admission
- Negative and unknown assessments remain legitimate completed work
- Exact evidence, immutable reviews, dependency membership, independent informed review and human-acceptance separation are preserved
- Standalone legacy assessment and additive v2/v3 integration are feasible without migration or consumer relinking
- The proposed scenario and regression coverage is appropriate once the two missing cases are added

No source edits or consumer mutations performed. This is a design-review finding, not shared-ledger approval or user acceptance

## Revised design

SHA-256: bad17d74eeb4083a5db391cb8a78659733621524c0c4c563c62ecb94b382f043

The revision also incorporated qualitative refinements: active producer
supervision, decisive contrary experience reaching the central promise,
consequential sacrifices, bias checking, and scenarios for an unobserved central
promise and for improved coherence after removing a feature.

### Completeness/project, verbatim report

PASS: completeness/project review of design SHA-256 bad17d74eeb4083a5db391cb8a78659733621524c0c4c563c62ecb94b382f043. No blocking design defect found. This is design review, not implementation verification or USER authorization.

The design fits the inspected contracts:

- Authority remains separate: Idea commissions, Studio activates/archives and admits baselines, Product assesses value. Negative conclusions remain successful assessment outputs; they grant no production, gameplay or human acceptance
- Current/adopted offers are explicitly distinguished from proposals and scenarios. Even a genuine USER-proposed price cannot pass the current-offer gate without adoption
- Required source closure, mandatory-authority membership, immutable reviewed packages and exact-build checks address stale evidence without using unrelated Git commits as universal invalidation
- Product task completion is bound to the sealed assessment identity, build, offer, audience, result location and actual required outputs. This closes substitution by a valid but unrelated same-game assessment
- Standalone legacy assessment is additive. Existing v2/v3 review, ruling, production and acceptance boundaries remain intact
- Narrative scenarios adequately distinguish whole-product value from functioning gameplay, expensive art, hours, feature quantity or QA success. Short complete experiences and valuable deliberate omissions remain legitimate

Implementation checks that deserve particular attention:

1. Evidence-ready artifacts: factory_core/acceptance.py currently receives the proposed COMPLETE record. Its artifacts need not equal the preceding EVIDENCE_READY artifacts. The Product adapter must verify the actual evidence-ready checkpoint and required current references, as the design promises, rather than merely checking the new COMPLETE request
2. Product binding dependencies: factory_core/state.py currently expands references from the design JSON, but Product-only binding validation must also enforce its required shape, capability ownership and output-scope constraints. Merely adding a permissive schema object would be insufficient
3. Lifecycle: studio/product.py distinguishes ACTIVE, LEGACY_ACTIVE, absent authority and partial/blocked authority. Standalone assessment must remain possible without commissioning a legacy game, while an explicit archived register must never be treated as active permission
4. Source freshness: exact hashes prove unchanged recorded sources, not that an external storefront remains current. The operating workflow must refresh relevant external offer evidence before making a new current-offer claim and preserve its observation date and qualifications
5. Compatibility coverage: exercise existing Story acceptance/profile tests in factory_core/tests as well as the named suites. Shared state, schemas, catalog and acceptance changes affect Story even though there is no story/tests directory

The regression plan is feasible with existing temporary-repository fixtures and v3 pointer/migration fixtures. Add adversarial cases for every Product binding field, omitted evidence-ready outputs, late substitution in COMPLETE, proposed versus adopted prices, changed/new mandatory authority, archived authority and exact-build mismatch.

I inspected the root/Idea/Studio instructions, Idea exploration/commission/compiler code, Studio lifecycle code and v1/v2 contracts, shared v2/v3 workflows, state/context/catalog/reference/acceptance implementations, schemas, setup discovery and relevant test fixtures. I did not read peer conclusions, edit files, run implementation tests, alter consumer pointers or create approvals. The reviewed document’s digest was unchanged at the end.

### Intent/experience, verbatim report

PASS — intent/experience design review

Reviewed the exact design with SHA-256 bad17d74eeb4083a5db391cb8a78659733621524c0c4c563c62ecb94b382f043, Idea’s actual workflow/caller/skill guidance and relevant implementation, and the referenced Factory review and Studio authority contracts. I did not read prior or peer review conclusions.

Why it passes:

- It asks the right commercial question. Sections 1 and 3 evaluate whether the experienced whole product offers the intended buyer a convincing reason to pay the stated price. Technical completion, an approved premise, attractive assets and content volume cannot independently establish that claim.
- It provides an operating method, rather than only a reporting format. Lines 82–118 require encountering the relevant artifact, seeking decisive contrary experience, identifying the weakest causal link in the purchase case, and selecting the smallest useful repair or test. Reassessment must establish improvement in the buyer’s experience; scope expansion stops once the coherent promise is delivered.
- Experience must reach the value-bearing part of the game. Lines 98–108 distinguish an impressive opening from demonstrated replay/mastery or satisfying closure. This directly prevents a producer’s “done” claim and carefully selected footage from substituting for assessment of the actual purchase.
- Art, audio and surrounding affordances are evaluated through their contribution to the coherent experience. Aesthetic judgment is explicitly different from screenshot existence or correct layout. Tradeoffs must name both the protected benefit and the buyer’s cost. Removal, integration, refinement and no further investment are legitimate recommendations.
- Short premium experiences and inexpensive small games can succeed on their own terms. Neither replay nor length nor expensive presentation is mandatory. The scenario set explicitly tests these cases and rejects compensating for empty interaction with costly art.
- Uncertainty remains actionable and honest. Missing context and unobserved central promises cannot yield unconditional support. A sourced proposed price remains a proposal; it cannot quietly replace the current offer. The ordinary-language verdict retains price, audience and build qualifications.
- Mechanical validity and qualitative agreement remain separate. Both reviewers assess the whole causal case and challenge evidence selection. AGREE can validate a negative or unknown assessment. The minimum experiential-source requirement is correctly presented as a floor, with representativeness and sufficiency still requiring judgment.
- Authority boundaries match the inspected guidance. Product assesses value; Idea retains product adoption and material direction; production stays with the owning factories; Studio retains lifecycle/baseline boundaries. Product support cannot manufacture user acceptance or delivery permission.

No blocking repair is required for this review scope.

Implementation review should specifically verify that the promised caller/reviewer guidance actually exercises these qualitative obligations. A schema-complete report, one runtime reference and two formally valid reviews would not demonstrate that the design has been faithfully implemented. The important behavioral checks are whether reviewers reject cherry-picked opening evidence, accept genuinely satisfying short work, and recommend a focused experiential improvement or justified stopping point rather than more features.
