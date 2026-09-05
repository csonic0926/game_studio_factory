# Studio Factory ownership

This department owns reusable studio methods, validators, schemas and CLI
compatibility. Filled game artifacts belong only in the target game repository.
For current operation use the `game-studio-factory` skill.

- Resolve the exact target; never scan sibling games or write game output here.
- `factory.py inspect` selects explicit project version and trustworthy work.
  Unmigrated projects return MIGRATION_REQUIRED; do not silently apply v2.
- v2 process authority: `factory_core/docs/WORKFLOW.md`.
- Capability rules: `studio/docs/WORKFLOW_V2.md`.
- v1 compatibility/detail: `studio/docs/WORKFLOW_V1.md`. Its semantic
  requirements remain available; its per-step authors/review topology does not
  govern an explicitly migrated v2 project.
- Preserve USER authority, explicit project standards and accepted history.
  Execution success and AI review never constitute USER acceptance.
