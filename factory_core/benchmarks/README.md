# Matched Astra trials

The preregistered `suite.json` fixes four synthetic tasks, both workflow stage
sequences, authority fixtures, outputs, Astra/high, permissions and two rounds.
It is not a Banner-content authoring command. See the one process authority:
`factory_core/docs/WORKFLOW.md`.

```sh
python3 factory.py benchmark --run --output-root /absolute/empty/test-area
python3 factory.py benchmark --resume --output-root /absolute/same/test-area
python3 factory.py benchmark --output-root /absolute/same/test-area
python3 factory.py benchmark --output-root /absolute/same/test-area --report
```

Resume preserves **every** earlier attempt and supports only the exact same
suite/sources plus verified file checkpoint. It never starts a replacement
ledger to hide a failure. Refill/authentication is external; an out-of-credit
request without usage remains explicitly unmetered even after successful retry.
No absent usage is inferred to be zero. Such a run can finish its artifacts but
cannot establish the complete-cost acceptance condition.

The repair cap belongs to each fixed trial. An exhausted trial is retained as
`REWORK_LIMIT`, not retried by resume and not accepted; other scheduled trials
still run. `finished` means the schedule was visited, not that every output
passed. A process/credit interruption without usage still pauses execution for
explicit resume. Known token subtotals are distinct from a proven reduction;
an unmetered member cannot make its pair's `lower` result true.

The initial live trial exposed a missing sandbox option on `exec resume`.
Both fresh and continuing author invocations now explicitly use the same
workspace-write policy and root. Affected historical attempts remain intact;
the trial's additive `execution_issues` record prevents protocol acceptance.
Future attempts also record the harness content hash for provenance.

`ATTEMPTS.json` binds logs, source/fixture/settings hashes, reviewed-design
versions and final output hashes. Inspect its runs to find actual full results.
Technical checks do not replace fresh narrative QA or the human comparison.
`--report` renders the exact full required outputs side by side with A/B labels,
fixed requirements, source constraints and explicit missing-output notices.
It writes only rebuildable `QUALITY_REVIEW.html` and `QUALITY_MAPPING.json`
outside trial workspaces; neither is approval. Do not open the mapping before
comparison. Content itself may reveal workflow traits, so label anonymization
does not claim perfect blinding. Incomplete trials remain visibly incomplete.
After reading the exact anonymously presented outputs, the USER can submit the
returned `human_quality_action`. A `--human-quality` receipt must bind that raw
USER message reference, suite, full attempts ledger and output-set hashes;
merely writing `owner: USER` or quoting a rejection cannot pass. Test receipts
are explicitly synthetic and are never production verdicts.

Cached input is a subset reported separately; output already includes reasoning.
Total counts author, reviewers, retry/repair attempts and failed measured turns.
No fixed savings percentage, shorter prose, omitted boundary or unmatched log
can qualify as success. Missing usage/quality confirmation remains incomplete.
