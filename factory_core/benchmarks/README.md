# Matched Astra trials

The preregistered `suite.json` fixes four synthetic tasks, both workflow stage
sequences, authority fixtures, outputs, Astra/high, permissions and two rounds.
It is not a Banner-content authoring command. See the one process authority:
`factory_core/docs/WORKFLOW.md`.

```sh
python3 factory.py benchmark --run --output-root /absolute/empty/test-area
python3 factory.py benchmark --resume --output-root /absolute/same/test-area
python3 factory.py benchmark --output-root /absolute/same/test-area
```

Resume preserves **every** earlier attempt and supports only the exact same
suite/sources plus verified file checkpoint. It never starts a replacement
ledger to hide a failure. Refill/authentication is external; an out-of-credit
request without usage remains explicitly unmetered even after successful retry.
No absent usage is inferred to be zero. Such a run can finish its artifacts but
cannot establish the complete-cost acceptance condition.

`ATTEMPTS.json` binds logs, source/fixture/settings hashes, reviewed-design
versions and final output hashes. Inspect its runs to find actual full results.
Technical checks do not replace fresh narrative QA or the human comparison.
After reading the exact anonymously presented outputs, the USER can submit the
returned `human_quality_action`. A `--human-quality` receipt must bind that raw
USER message reference, suite, full attempts ledger and output-set hashes;
merely writing `owner: USER` or quoting a rejection cannot pass. Test receipts
are explicitly synthetic and are never production verdicts.

Cached input is a subset reported separately; output already includes reasoning.
Total counts author, reviewers, retry/repair attempts and failed measured turns.
No fixed savings percentage, shorter prose, omitted boundary or unmatched log
can qualify as success. Missing usage/quality confirmation remains incomplete.
