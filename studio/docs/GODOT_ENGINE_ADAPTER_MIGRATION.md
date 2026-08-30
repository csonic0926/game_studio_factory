# Godot Engine Adapter migration

## v1 users

No migration is required for `probe`, `import-check`, `run`, `export`, or the
v1 Python functions. Their schema versions and paths are unchanged.

## Opting into automation v2

1. Commit or otherwise review the current Godot source state. The adapter does
   not create a safety branch or backup copy.
2. Run `bridge install --autoload` without `--apply` and review the plan.
3. Run it again with `--apply --operation-id <unique-id>`.
4. Create the project-owned `GODOT_BRIDGE_PROFILE.json` from the template.
5. Implement and register the project-owned Observation Provider autoload.
6. Run `bridge check`, `doctor`, and `scenario validate`.
7. Run a deterministic synthetic/project scenario three times and compare the
   normalized traces before using it as regression evidence.
8. Bind only the final adapter evidence path/SHA into Gameplay or Studio
   acceptance inputs; retain the human gameplay-verdict gates.

Upgrade refuses missing, changed, or extra vendor files. Resolve the drift
manually and commit the intended state; never create `.bak`, `.orig`, copied
addon folders, or backup branches. Project profiles/providers are outside the
vendor directory and are never upgraded or removed.

Visual baselines require an existing accepted or user-approved evidence record.
The migration does not import screenshots as approved baselines and does not
synthesize tolerance values.
